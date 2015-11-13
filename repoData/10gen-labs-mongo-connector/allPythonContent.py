__FILENAME__ = compat
"""Utilities for maintaining portability between various Python versions"""

import sys

PY3 = (sys.version_info[0] == 3)

if PY3:
    def reraise(exctype, value, trace=None):
        raise exctype(str(value)).with_traceback(trace)
else:
    exec("""def reraise(exctype, value, trace=None):
    raise exctype, str(value), trace
""")

########NEW FILE########
__FILENAME__ = connector
# Copyright 2013-2014 MongoDB, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Discovers the mongo cluster and starts the connector.
"""

import json
import logging
import logging.handlers
import optparse
import os
import pymongo
import re
import shutil
import sys
import threading
import time
import imp
from mongo_connector import constants, errors, util
from mongo_connector.locking_dict import LockingDict
from mongo_connector.oplog_manager import OplogThread
from mongo_connector.doc_managers import doc_manager_simulator as simulator

from pymongo import MongoClient


class Connector(threading.Thread):
    """Checks the cluster for shards to tail.
    """
    def __init__(self, address, oplog_checkpoint, target_url, ns_set,
                 u_key, auth_key, doc_manager=None, auth_username=None,
                 collection_dump=True, batch_size=constants.DEFAULT_BATCH_SIZE,
                 fields=None, dest_mapping={},
                 auto_commit_interval=constants.DEFAULT_COMMIT_INTERVAL):

        if target_url and not doc_manager:
            raise errors.ConnectorError("Cannot create a Connector with a "
                                        "target URL but no doc manager!")

        def is_string(s):
            try:
                return isinstance(s, basestring)
            except NameError:
                return isinstance(s, str)

        def load_doc_manager(path):
            name, _ = os.path.splitext(os.path.basename(path))
            try:
                import importlib.machinery
                loader = importlib.machinery.SourceFileLoader(name, path)
                module = loader.load_module(name)
            except ImportError:
                module = imp.load_source(name, path)
            return module

        doc_manager_modules = None

        if doc_manager is not None:
            # backwards compatilibity: doc_manager may be a string
            if is_string(doc_manager):
                doc_manager_modules = [load_doc_manager(doc_manager)]
            # doc_manager is a list
            else:
                doc_manager_modules = []
                for dm in doc_manager:
                    doc_manager_modules.append(load_doc_manager(dm))

        super(Connector, self).__init__()

        #can_run is set to false when we join the thread
        self.can_run = True

        #The name of the file that stores the progress of the OplogThreads
        self.oplog_checkpoint = oplog_checkpoint

        #main address - either mongos for sharded setups or a primary otherwise
        self.address = address

        #The URLs of each target system, respectively
        if is_string(target_url):
            self.target_urls = [target_url]
        elif target_url:
            self.target_urls = list(target_url)
        else:
            self.target_urls = None

        #The set of relevant namespaces to consider
        self.ns_set = ns_set

        #The dict of source namespace to destination namespace
        self.dest_mapping = dest_mapping

        #The key that is a unique document identifier for the target system.
        #Not necessarily the mongo unique key.
        self.u_key = u_key

        #Password for authentication
        self.auth_key = auth_key

        #Username for authentication
        self.auth_username = auth_username

        #The set of OplogThreads created
        self.shard_set = {}

        #Boolean chooses whether to dump the entire collection if no timestamp
        # is present in the config file
        self.collection_dump = collection_dump

        #Num entries to process before updating config file with current pos
        self.batch_size = batch_size

        #Dict of OplogThread/timestamp pairs to record progress
        self.oplog_progress = LockingDict()

        # List of fields to export
        self.fields = fields

        try:
            docman_kwargs = {"unique_key": u_key,
                             "namespace_set": ns_set,
                             "auto_commit_interval": auto_commit_interval}

            # No doc managers specified, using simulator
            if doc_manager is None:
                self.doc_managers = [simulator.DocManager(**docman_kwargs)]
            else:
                self.doc_managers = []
                for i, d in enumerate(doc_manager_modules):
                    # self.target_urls may be shorter than
                    # self.doc_managers, or left as None
                    if self.target_urls and i < len(self.target_urls):
                        target_url = self.target_urls[i]
                    else:
                        target_url = None

                    if target_url:
                        self.doc_managers.append(
                            d.DocManager(self.target_urls[i],
                                         **docman_kwargs))
                    else:
                        self.doc_managers.append(
                            d.DocManager(**docman_kwargs))
                # If more target URLs were given than doc managers, may need
                # to create additional doc managers
                for url in self.target_urls[i + 1:]:
                    self.doc_managers.append(
                        doc_manager_modules[-1].DocManager(url,
                                                           **docman_kwargs))
        except errors.ConnectionFailed:
            err_msg = "MongoConnector: Could not connect to target system"
            logging.critical(err_msg)
            self.can_run = False
            return

        if self.oplog_checkpoint is not None:
            if not os.path.exists(self.oplog_checkpoint):
                info_str = ("MongoConnector: Can't find %s, "
                            "attempting to create an empty progress log" %
                            self.oplog_checkpoint)
                logging.info(info_str)
                try:
                    # Create oplog progress file
                    open(self.oplog_checkpoint, "w").close()
                except IOError as e:
                    logging.critical("MongoConnector: Could not "
                                     "create a progress log: %s" %
                                     str(e))
                    sys.exit(2)
            else:
                if (not os.access(self.oplog_checkpoint, os.W_OK)
                        and not os.access(self.oplog_checkpoint, os.R_OK)):
                    logging.critical("Invalid permissions on %s! Exiting" %
                                     (self.oplog_checkpoint))
                    sys.exit(2)

    def join(self):
        """ Joins thread, stops it from running
        """
        self.can_run = False
        for dm in self.doc_managers:
            dm.stop()
        threading.Thread.join(self)

    def write_oplog_progress(self):
        """ Writes oplog progress to file provided by user
        """

        if self.oplog_checkpoint is None:
            return None

        # write to temp file
        backup_file = self.oplog_checkpoint + '.backup'
        os.rename(self.oplog_checkpoint, backup_file)

        # for each of the threads write to file
        with open(self.oplog_checkpoint, 'w') as dest:
            with self.oplog_progress as oplog_prog:

                oplog_dict = oplog_prog.get_dict()
                for oplog, time_stamp in oplog_dict.items():
                    oplog_str = str(oplog)
                    timestamp = util.bson_ts_to_long(time_stamp)
                    json_str = json.dumps([oplog_str, timestamp])
                    try:
                        dest.write(json_str)
                    except IOError:
                        # Basically wipe the file, copy from backup
                        dest.truncate()
                        with open(backup_file, 'r') as backup:
                            shutil.copyfile(backup, dest)
                        break

        os.remove(self.oplog_checkpoint + '.backup')

    def read_oplog_progress(self):
        """Reads oplog progress from file provided by user.
        This method is only called once before any threads are spanwed.
        """

        if self.oplog_checkpoint is None:
            return None

        # Check for empty file
        try:
            if os.stat(self.oplog_checkpoint).st_size == 0:
                logging.info("MongoConnector: Empty oplog progress file.")
                return None
        except OSError:
            return None

        source = open(self.oplog_checkpoint, 'r')
        try:
            data = json.load(source)
        except ValueError:       # empty file
            reason = "It may be empty or corrupt."
            logging.info("MongoConnector: Can't read oplog progress file. %s" %
                         (reason))
            source.close()
            return None

        source.close()

        count = 0
        oplog_dict = self.oplog_progress.get_dict()
        for count in range(0, len(data), 2):
            oplog_str = data[count]
            time_stamp = data[count + 1]
            oplog_dict[oplog_str] = util.long_to_bson_ts(time_stamp)
            #stored as bson_ts

    def run(self):
        """Discovers the mongo cluster and creates a thread for each primary.
        """
        main_conn = MongoClient(self.address)
        if self.auth_key is not None:
            main_conn['admin'].authenticate(self.auth_username, self.auth_key)
        self.read_oplog_progress()
        conn_type = None

        try:
            main_conn.admin.command("isdbgrid")
        except pymongo.errors.OperationFailure:
            conn_type = "REPLSET"

        if conn_type == "REPLSET":
            # Make sure we are connected to a replica set
            is_master = main_conn.admin.command("isMaster")
            if not "setName" in is_master:
                logging.error(
                    'No replica set at "%s"! A replica set is required '
                    'to run mongo-connector. Shutting down...' % self.address
                )
                return

            # Establish a connection to the replica set as a whole
            main_conn.disconnect()
            main_conn = MongoClient(self.address,
                                    replicaSet=is_master['setName'])
            if self.auth_key is not None:
                main_conn.admin.authenticate(self.auth_username, self.auth_key)

            #non sharded configuration
            oplog_coll = main_conn['local']['oplog.rs']

            oplog = OplogThread(
                primary_conn=main_conn,
                main_address=self.address,
                oplog_coll=oplog_coll,
                is_sharded=False,
                doc_manager=self.doc_managers,
                oplog_progress_dict=self.oplog_progress,
                namespace_set=self.ns_set,
                auth_key=self.auth_key,
                auth_username=self.auth_username,
                repl_set=is_master['setName'],
                collection_dump=self.collection_dump,
                batch_size=self.batch_size,
                fields=self.fields,
                dest_mapping=self.dest_mapping
            )
            self.shard_set[0] = oplog
            logging.info('MongoConnector: Starting connection thread %s' %
                         main_conn)
            oplog.start()

            while self.can_run:
                if not self.shard_set[0].running:
                    logging.error("MongoConnector: OplogThread"
                                  " %s unexpectedly stopped! Shutting down" %
                                  (str(self.shard_set[0])))
                    self.oplog_thread_join()
                    for dm in self.doc_managers:
                        dm.stop()
                    return

                self.write_oplog_progress()
                time.sleep(1)

        else:       # sharded cluster
            while self.can_run is True:

                for shard_doc in main_conn['config']['shards'].find():
                    shard_id = shard_doc['_id']
                    if shard_id in self.shard_set:
                        if not self.shard_set[shard_id].running:
                            logging.error("MongoConnector: OplogThread "
                                          "%s unexpectedly stopped! Shutting "
                                          "down" %
                                          (str(self.shard_set[shard_id])))
                            self.oplog_thread_join()
                            for dm in self.doc_managers:
                                dm.stop()
                            return

                        self.write_oplog_progress()
                        time.sleep(1)
                        continue
                    try:
                        repl_set, hosts = shard_doc['host'].split('/')
                    except ValueError:
                        cause = "The system only uses replica sets!"
                        logging.error("MongoConnector: %s", cause)
                        self.oplog_thread_join()
                        for dm in self.doc_managers:
                            dm.stop()
                        return

                    shard_conn = MongoClient(hosts, replicaSet=repl_set)
                    oplog_coll = shard_conn['local']['oplog.rs']

                    oplog = OplogThread(
                        primary_conn=shard_conn,
                        main_address=self.address,
                        oplog_coll=oplog_coll,
                        is_sharded=True,
                        doc_manager=self.doc_managers,
                        oplog_progress_dict=self.oplog_progress,
                        namespace_set=self.ns_set,
                        auth_key=self.auth_key,
                        auth_username=self.auth_username,
                        collection_dump=self.collection_dump,
                        batch_size=self.batch_size,
                        fields=self.fields,
                        dest_mapping=self.dest_mapping
                    )
                    self.shard_set[shard_id] = oplog
                    msg = "Starting connection thread"
                    logging.info("MongoConnector: %s %s" % (msg, shard_conn))
                    oplog.start()

        self.oplog_thread_join()
        self.write_oplog_progress()

    def oplog_thread_join(self):
        """Stops all the OplogThreads
        """
        logging.info('MongoConnector: Stopping all OplogThreads')
        for thread in self.shard_set.values():
            thread.join()


def main():
    """ Starts the mongo connector (assuming CLI)
    """
    parser = optparse.OptionParser()

    #-m is for the main address, which is a host:port pair, ideally of the
    #mongos. For non sharded clusters, it can be the primary.
    parser.add_option("-m", "--main", action="store", type="string",
                      dest="main_addr", default="localhost:27217",
                      help="""Specify the main address, which is a"""
                      """ host:port pair. For sharded clusters, this"""
                      """ should be the mongos address. For individual"""
                      """ replica sets, supply the address of the"""
                      """ primary. For example, `-m localhost:27217`"""
                      """ would be a valid argument to `-m`. Don't use"""
                      """ quotes around the address.""")

    #-o is to specify the oplog-config file. This file is used by the system
    #to store the last timestamp read on a specific oplog. This allows for
    #quick recovery from failure.
    parser.add_option("-o", "--oplog-ts", action="store", type="string",
                      dest="oplog_config", default="config.txt",
                      help="""Specify the name of the file that stores the """
                      """oplog progress timestamps. """
                      """This file is used by the system to store the last """
                      """timestamp read on a specific oplog. This allows """
                      """for quick recovery from failure. By default this """
                      """is `config.txt`, which starts off empty. An empty """
                      """file causes the system to go through all the mongo """
                      """oplog and sync all the documents. Whenever the """
                      """cluster is restarted, it is essential that the """
                      """oplog-timestamp config file be emptied - otherwise """
                      """the connector will miss some documents and behave """
                      """incorrectly.""")

    #--no-dump specifies whether we should read an entire collection from
    #scratch if no timestamp is found in the oplog_config.
    parser.add_option("--no-dump", action="store_true", default=False, help=
                      "If specified, this flag will ensure that "
                      "mongo_connector won't read the entire contents of a "
                      "namespace iff --oplog-ts points to an empty file.")

    #--batch-size specifies num docs to read from oplog before updating the
    #--oplog-ts config file with current oplog position
    parser.add_option("--batch-size", action="store",
                      default=constants.DEFAULT_BATCH_SIZE, type="int",
                      help="Specify an int to update the --oplog-ts "
                      "config file with latest position of oplog every "
                      "N documents. By default, the oplog config isn't "
                      "updated until we've read through the entire oplog. "
                      "You may want more frequent updates if you are at risk "
                      "of falling behind the earliest timestamp in the oplog")

    #-t is to specify the URL to the target system being used.
    parser.add_option("-t", "--target-url", "--target-urls", action="store",
                      type="string", dest="urls", default=None, help=
                      """Specify the URL to each target system being """
                      """used. For example, if you were using Solr out of """
                      """the box, you could use '-t """
                      """http://localhost:8080/solr' with the """
                      """SolrDocManager to establish a proper connection. """
                      """URLs should be specified in the same order as """
                      """their respective doc managers in the """
                      """--doc-managers option.  URLs are assigned to doc """
                      """managers respectively. Additional doc managers """
                      """are implied to have no target URL. Additional """
                      """URLs are implied to have the same doc manager """
                      """type as the last doc manager for which a URL was """
                      """specified. """
                      """Don't use quotes around addresses. """)

    #-n is to specify the namespaces we want to consider. The default
    #considers all the namespaces
    parser.add_option("-n", "--namespace-set", action="store", type="string",
                      dest="ns_set", default=None, help=
                      """Used to specify the namespaces we want to """
                      """consider. For example, if we wished to store all """
                      """documents from the test.test and alpha.foo """
                      """namespaces, we could use `-n test.test,alpha.foo`. """
                      """The default is to consider all the namespaces, """
                      """excluding the system and config databases, and """
                      """also ignoring the "system.indexes" collection in """
                      """any database.""")

    #-u is to specify the mongoDB field that will serve as the unique key
    #for the target system,
    parser.add_option("-u", "--unique-key", action="store", type="string",
                      dest="u_key", default="_id", help=
                      """Used to specify the mongoDB field that will serve """
                      """as the unique key for the target system. """
                      """The default is "_id", which can be noted by """
                      """'-u _id'""")

    #-f is to specify the authentication key file. This file is used by mongos
    #to authenticate connections to the shards, and we'll use it in the oplog
    #threads.
    parser.add_option("-f", "--password-file", action="store", type="string",
                      dest="auth_file", default=None, help=
                      """Used to store the password for authentication."""
                      """ Use this option if you wish to specify a"""
                      """ username and password but don't want to"""
                      """ type in the password. The contents of this"""
                      """ file should be the password for the admin user.""")

    #-p is to specify the password used for authentication.
    parser.add_option("-p", "--password", action="store", type="string",
                      dest="password", default=None, help=
                      """Used to specify the password."""
                      """ This is used by mongos to authenticate"""
                      """ connections to the shards, and in the"""
                      """ oplog threads. If authentication is not used, then"""
                      """ this field can be left empty as the default """)

    #-a is to specify the username for authentication.
    parser.add_option("-a", "--admin-username", action="store", type="string",
                      dest="admin_name", default="__system", help=
                      """Used to specify the username of an admin user to """
                      """authenticate with. To use authentication, the user """
                      """must specify both an admin username and a keyFile. """
                      """The default username is '__system'""")

    #-d is to specify the doc manager file.
    parser.add_option("-d", "--docManager", "--doc-managers", action="store",
                      type="string", dest="doc_managers", default=None, help=
                      """Used to specify the path to each doc manager """
                      """file that will be used. DocManagers should be """
                      """specified in the same order as their respective """
                      """target addresses in the --target-urls option. """
                      """URLs are assigned to doc managers """
                      """respectively. Additional doc managers are """
                      """implied to have no target URL. Additional URLs """
                      """are implied to have the same doc manager type as """
                      """the last doc manager for which a URL was """
                      """specified. By default, Mongo Connector will use """
                      """'doc_manager_simulator.py'.  It is recommended """
                      """that all doc manager files be kept in the """
                      """doc_managers folder in mongo-connector. For """
                      """more information about making your own doc """
                      """manager, see 'Writing Your Own DocManager' """
                      """section of the wiki""")

    #-g is the destination namespace
    parser.add_option("-g", "--dest-namespace-set", action="store",
                      type="string", dest="dest_ns_set", default=None, help=
                      """Specify a destination namespace mapping. Each """
                      """namespace provided in the --namespace-set option """
                      """will be mapped respectively according to this """
                      """comma-separated list. These lists must have """
                      """equal length. The default is to use the identity """
                      """mapping. This is currently only implemented """
                      """for mongo-to-mongo connections.""")

    #-s is to enable syslog logging.
    parser.add_option("-s", "--enable-syslog", action="store_true",
                      dest="enable_syslog", default=False, help=
                      """Used to enable logging to syslog."""
                      """ Use -l to specify syslog host.""")

    #--syslog-host is to specify the syslog host.
    parser.add_option("--syslog-host", action="store", type="string",
                      dest="syslog_host", default="localhost:514", help=
                      """Used to specify the syslog host."""
                      """ The default is 'localhost:514'""")

    #--syslog-facility is to specify the syslog facility.
    parser.add_option("--syslog-facility", action="store", type="string",
                      dest="syslog_facility", default="user", help=
                      """Used to specify the syslog facility."""
                      """ The default is 'user'""")

    #-i to specify the list of fields to export
    parser.add_option("-i", "--fields", action="store", type="string",
                      dest="fields", default=None, help=
                      """Used to specify the list of fields to export. """
                      """Specify a field or fields to include in the export. """
                      """Use a comma separated list of fields to specify multiple """
                      """fields. The '_id', 'ns' and '_ts' fields are always """
                      """exported.""")

    #--auto-commit-interval to specify auto commit time interval
    parser.add_option("--auto-commit-interval", action="store",
                      dest="commit_interval", type="int",
                      default=constants.DEFAULT_COMMIT_INTERVAL,
                      help="""Seconds in-between calls for the Doc Manager"""
                      """ to commit changes to the target system. A value of"""
                      """ 0 means to commit after every write operation."""
                      """ When left unset, Mongo Connector will not make"""
                      """ explicit commits. Some systems have"""
                      """ their own mechanism for adjusting a commit"""
                      """ interval, which should be preferred to this"""
                      """ option.""")

    #-v enables vebose logging
    parser.add_option("-v", "--verbose", action="store_true",
                      dest="verbose", default=False,
                      help="Sets verbose logging to be on.")

    #-w enable logging to a file
    parser.add_option("-w", "--logfile", dest="logfile",
                      help=("Log all output to a file rather than stream to "
                            "stderr.   Omit to stream to stderr."))

    (options, args) = parser.parse_args()

    logger = logging.getLogger()
    loglevel = logging.INFO
    if options.verbose:
        loglevel = logging.DEBUG
    logger.setLevel(loglevel)

    if options.enable_syslog and options.logfile:
        print ("You cannot specify syslog and a logfile simultaneously, please"
               " choose the logging method you would prefer.")
        sys.exit(1)

    if options.enable_syslog:
        syslog_info = options.syslog_host.split(":")
        syslog_host = logging.handlers.SysLogHandler(
            address=(syslog_info[0], int(syslog_info[1])),
            facility=options.syslog_facility
        )
        syslog_host.setLevel(loglevel)
        logger.addHandler(syslog_host)
    elif options.logfile is not None:
        log_out = logging.FileHandler(options.logfile)
        log_out.setLevel(loglevel)
        log_out.setFormatter(logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s'))
        logger.addHandler(log_out)
    else:
        log_out = logging.StreamHandler()
        log_out.setLevel(loglevel)
        log_out.setFormatter(logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s'))
        logger.addHandler(log_out)

    logger.info('Beginning Mongo Connector')

    # Get DocManagers and target URLs
    # Each DocManager is assigned the respective (same-index) target URL
    # Additional DocManagers may be specified that take no target URL
    doc_managers = options.doc_managers
    doc_managers = doc_managers.split(",") if doc_managers else doc_managers
    target_urls = options.urls.split(",") if options.urls else None

    if options.doc_managers is None:
        logger.info('No doc managers specified, using simulator.')

    if options.ns_set is None:
        ns_set = []
    else:
        ns_set = options.ns_set.split(',')

    if options.dest_ns_set is None:
        dest_ns_set = ns_set
    else:
        dest_ns_set = options.dest_ns_set.split(',')

    if len(dest_ns_set) != len(ns_set):
        logger.error("Destination namespace must be the same length as the "
                     "origin namespace!")
        sys.exit(1)
    elif len(set(ns_set)) + len(set(dest_ns_set)) != 2 * len(ns_set):
        logger.error("Namespace set and destination namespace set should not "
                     "contain any duplicates!")
        sys.exit(1)
    else:
        ## Create a mapping of source ns to dest ns as a dict
        dest_mapping = dict(zip(ns_set, dest_ns_set))

    fields = options.fields
    if fields is not None:
        fields = options.fields.split(',')

    key = None
    if options.auth_file is not None:
        try:
            key = open(options.auth_file).read()
            re.sub(r'\s', '', key)
        except IOError:
            logger.error('Could not parse password authentication file!')
            sys.exit(1)

    if options.password is not None:
        key = options.password

    if key is None and options.admin_name != "__system":
        logger.error("Admin username specified without password!")
        sys.exit(1)

    if options.commit_interval is not None and options.commit_interval < 0:
        raise ValueError("--auto-commit-interval must be non-negative")

    connector = Connector(
        address=options.main_addr,
        oplog_checkpoint=options.oplog_config,
        target_url=target_urls,
        ns_set=ns_set,
        u_key=options.u_key,
        auth_key=key,
        doc_manager=doc_managers,
        auth_username=options.admin_name,
        collection_dump=(not options.no_dump),
        batch_size=options.batch_size,
        fields=fields,
        dest_mapping=dest_mapping,
        auto_commit_interval=options.commit_interval
    )
    connector.start()

    while True:
        try:
            time.sleep(3)
            if not connector.is_alive():
                break
        except KeyboardInterrupt:
            logging.info("Caught keyboard interrupt, exiting!")
            connector.join()
            break

if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = constants
# Copyright 2013-2014 MongoDB, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# Maximum # of documents to process before recording timestamp
# default = -1 (no maximum)
DEFAULT_BATCH_SIZE = -1
# Interval in seconds between doc manager flushes (i.e. auto commit)
# default = None (never auto commit)
DEFAULT_COMMIT_INTERVAL = None
# Maximum # of documents to send in a single bulk request through a
# DocManager. This only affects DocManagers that cannot stream their
# requests.
DEFAULT_MAX_BULK = 500

########NEW FILE########
__FILENAME__ = doc_manager_simulator
# Copyright 2013-2014 MongoDB, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""A class to serve as proxy for the target engine for testing.

Receives documents from the oplog worker threads and indexes them
into the backend.

Please look at the Solr and ElasticSearch doc manager classes for a sample
implementation with real systems.
"""

from mongo_connector.errors import OperationFailed
from mongo_connector.doc_managers import DocManagerBase


class DocManager(DocManagerBase):
    """BackendSimulator emulates both a target DocManager and a server.

    The DocManager class creates a connection to the backend engine and
    adds/removes documents, and in the case of rollback, searches for them.

    The reason for storing id/doc pairs as opposed to doc's is so that multiple
    updates to the same doc reflect the most up to date version as opposed to
    multiple, slightly different versions of a doc.
    """

    def __init__(self, url=None, unique_key='_id', **kwargs):
        """Creates a dictionary to hold document id keys mapped to the
        documents as values.
        """
        self.unique_key = unique_key
        self.doc_dict = {}
        self.url = url

    def stop(self):
        """Stops any running threads in the DocManager.
        """
        pass

    def update(self, doc, update_spec):
        """Apply updates given in update_spec to the document whose id
        matches that of doc.

        """
        document = self.doc_dict[doc["_id"]]
        updated = self.apply_update(document, update_spec)
        self.upsert(updated)
        return updated

    def upsert(self, doc):
        """Adds a document to the doc dict.
        """

        self.doc_dict[doc[self.unique_key]] = doc

    def remove(self, doc):
        """Removes the document from the doc dict.
        """
        doc_id = doc[self.unique_key]
        try:
            del self.doc_dict[doc_id]
        except KeyError:
            raise OperationFailed("Document does not exist: %s" % str(doc))

    def search(self, start_ts, end_ts):
        """Searches through all documents and finds all documents within the
        range.

        Since we have very few documents in the doc dict when this is called,
        linear search is fine. This method is only used by rollbacks to query
        all the documents in the target engine within a certain timestamp
        window. The input will be two longs (converted from Bson timestamp)
        which specify the time range. The start_ts refers to the timestamp
        of the last oplog entry after a rollback. The end_ts is the timestamp
        of the last document committed to the backend.
        """
        ret_list = []
        for stored_doc in self.doc_dict.values():
            time_stamp = stored_doc['_ts']
            if time_stamp <= end_ts or time_stamp >= start_ts:
                ret_list.append(stored_doc)

        return ret_list

    def commit(self):
        """Simply passes since we're not using an engine that needs commiting.
        """
        pass

    def get_last_doc(self):
        """Searches through the doc dict to find the document with the latest
            timestamp.
        """

        last_doc = None
        last_ts = None

        for stored_doc in self.doc_dict.values():
            time_stamp = stored_doc['_ts']
            if last_ts is None or time_stamp >= last_ts:
                last_doc = stored_doc
                last_ts = time_stamp

        return last_doc

    def _search(self):
        """Returns all documents in the doc dict.

        This function is not a part of the DocManager API, and is only used
        to simulate searching all documents from a backend.
        """

        ret_list = []
        for doc in self.doc_dict.values():
            ret_list.append(doc)

        return ret_list

    def _delete(self):
        """Deletes all documents.

        This function is not a part of the DocManager API, and is only used
        to simulate deleting all documents from a backend.
        """
        self.doc_dict = {}

########NEW FILE########
__FILENAME__ = elastic_doc_manager
# Copyright 2013-2014 MongoDB, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Receives documents from the oplog worker threads and indexes them
    into the backend.

    This file is a document manager for the Elastic search engine, but the
    intent is that this file can be used as an example to add on different
    backends. To extend this to other systems, simply implement the exact
    same class and replace the method definitions with API calls for the
    desired backend.
    """
import logging
from threading import Timer

import bson.json_util as bsjson
from elasticsearch import Elasticsearch, exceptions as es_exceptions
from elasticsearch.helpers import scan, streaming_bulk

from mongo_connector import errors
from mongo_connector.constants import (DEFAULT_COMMIT_INTERVAL,
                                       DEFAULT_MAX_BULK)
from mongo_connector.util import retry_until_ok
from mongo_connector.doc_managers import DocManagerBase, exception_wrapper


wrap_exceptions = exception_wrapper({
    es_exceptions.ConnectionError: errors.ConnectionFailed,
    es_exceptions.TransportError: errors.OperationFailed})


class DocManager(DocManagerBase):
    """The DocManager class creates a connection to the backend engine and
        adds/removes documents, and in the case of rollback, searches for them.

        The reason for storing id/doc pairs as opposed to doc's is so that
        multiple updates to the same doc reflect the most up to date version as
        opposed to multiple, slightly different versions of a doc.

        We are using elastic native fields for _id and ns, but we also store
        them as fields in the document, due to compatibility issues.
        """

    def __init__(self, url, auto_commit_interval=DEFAULT_COMMIT_INTERVAL,
                 unique_key='_id', chunk_size=DEFAULT_MAX_BULK, **kwargs):
        """ Establish a connection to Elastic
        """
        self.elastic = Elasticsearch(hosts=[url])
        self.auto_commit_interval = auto_commit_interval
        self.doc_type = 'string'  # default type is string, change if needed
        self.unique_key = unique_key
        self.chunk_size = chunk_size
        if self.auto_commit_interval not in [None, 0]:
            self.run_auto_commit()

    def stop(self):
        """ Stops the instance
        """
        self.auto_commit_interval = None

    @wrap_exceptions
    def update(self, doc, update_spec):
        """Apply updates given in update_spec to the document whose id
        matches that of doc.

        """
        document = self.elastic.get(index=doc['ns'],
                                    id=str(doc['_id']))
        updated = self.apply_update(document['_source'], update_spec)
        self.upsert(updated)
        return updated

    @wrap_exceptions
    def upsert(self, doc):
        """Update or insert a document into Elastic

        If you'd like to have different types of document in your database,
        you can store the doc type as a field in Mongo and set doc_type to
        that field. (e.g. doc_type = doc['_type'])

        """
        doc_type = self.doc_type
        index = doc['ns']
        doc[self.unique_key] = str(doc["_id"])
        doc_id = doc[self.unique_key]
        self.elastic.index(index=index, doc_type=doc_type,
                           body=bsjson.dumps(doc), id=doc_id,
                           refresh=(self.auto_commit_interval == 0))

    @wrap_exceptions
    def bulk_upsert(self, docs):
        """Update or insert multiple documents into Elastic

        docs may be any iterable
        """
        def docs_to_upsert():
            doc = None
            for doc in docs:
                index = doc["ns"]
                doc[self.unique_key] = str(doc[self.unique_key])
                doc_id = doc[self.unique_key]
                yield {
                    "_index": index,
                    "_type": self.doc_type,
                    "_id": doc_id,
                    "_source": doc
                }
            if not doc:
                raise errors.EmptyDocsError(
                    "Cannot upsert an empty sequence of "
                    "documents into Elastic Search")
        try:
            kw = {}
            if self.chunk_size > 0:
                kw['chunk_size'] = self.chunk_size

            responses = streaming_bulk(client=self.elastic,
                                       actions=docs_to_upsert(),
                                       **kw)

            for ok, resp in responses:
                if not ok:
                    logging.error(
                        "Could not bulk-upsert document "
                        "into ElasticSearch: %r" % resp)
            if self.auto_commit_interval == 0:
                self.commit()
        except errors.EmptyDocsError:
            # This can happen when mongo-connector starts up, there is no
            # config file, but nothing to dump
            pass

    @wrap_exceptions
    def remove(self, doc):
        """Removes documents from Elastic

        The input is a python dictionary that represents a mongo document.
        """
        self.elastic.delete(index=doc['ns'], doc_type=self.doc_type,
                            id=str(doc[self.unique_key]),
                            refresh=(self.auto_commit_interval == 0))

    @wrap_exceptions
    def _stream_search(self, *args, **kwargs):
        """Helper method for iterating over ES search results"""
        for hit in scan(self.elastic, query=kwargs.pop('body', None),
                        scroll='10m', **kwargs):
            yield hit['_source']

    def search(self, start_ts, end_ts):
        """Called to query Elastic for documents in a time range.
        """
        return self._stream_search(
            index="_all",
            body={
                "query": {
                    "filtered": {
                        "filter": {
                            "range": {
                                "_ts": {"gte": start_ts, "lte": end_ts}
                            }
                        }
                    }
                }
            })

    def commit(self):
        """This function is used to force a refresh/commit.
        """
        retry_until_ok(self.elastic.indices.refresh, index="")

    def run_auto_commit(self):
        """Periodically commits to the Elastic server.
        """
        self.elastic.indices.refresh()
        if self.auto_commit_interval not in [None, 0]:
            Timer(self.auto_commit_interval, self.run_auto_commit).start()

    @wrap_exceptions
    def get_last_doc(self):
        """Returns the last document stored in the Elastic engine.
        """
        try:
            result = self.elastic.search(
                index="_all",
                body={
                    "query": {"match_all": {}},
                    "sort": [{"_ts": "desc"}]
                },
                size=1
            )["hits"]["hits"]
            return result[0]["_source"] if len(result) > 0 else None
        except es_exceptions.RequestError:
            # no documents so ES returns 400 because of undefined _ts mapping
            return None

########NEW FILE########
__FILENAME__ = mongo_doc_manager
# Copyright 2013-2014 MongoDB, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Receives documents from the oplog worker threads and indexes them
    into the backend.

    This file is a document manager for MongoDB, but the intent
    is that this file can be used as an example to add on different backends.
    To extend this to other systems, simply implement the exact same class and
    replace the method definitions with API calls for the desired backend.
    """

import logging
import pymongo

from mongo_connector import errors
from mongo_connector.doc_managers import DocManagerBase, exception_wrapper


wrap_exceptions = exception_wrapper({
    pymongo.errors.ConnectionFailure: errors.ConnectionFailed,
    pymongo.errors.OperationFailure: errors.OperationFailed})


class DocManager(DocManagerBase):
    """The DocManager class creates a connection to the backend engine and
        adds/removes documents, and in the case of rollback, searches for them.

        The reason for storing id/doc pairs as opposed to doc's is so that
        multiple updates to the same doc reflect the most up to date version as
        opposed to multiple, slightly different versions of a doc.

        We are using MongoDB native fields for _id and ns, but we also store
        them as fields in the document, due to compatibility issues.
        """

    def __init__(self, url, unique_key='_id', **kwargs):
        """ Verify URL and establish a connection.
        """
        try:
            self.mongo = pymongo.MongoClient(url)
        except pymongo.errors.InvalidURI:
            raise errors.ConnectionFailed("Invalid URI for MongoDB")
        except pymongo.errors.ConnectionFailure:
            raise errors.ConnectionFailed("Failed to connect to MongoDB")
        self.unique_key = unique_key
        self.namespace_set = kwargs.get("namespace_set")
        for namespace in self._namespaces():
            self.mongo["__mongo_connector"][namespace].create_index("_ts")

    @wrap_exceptions
    def _namespaces(self):
        """Provides the list of namespaces being replicated to MongoDB
        """
        if self.namespace_set:
            return self.namespace_set

        user_namespaces = []
        db_list = self.mongo.database_names()
        for database in db_list:
            if database == "config" or database == "local":
                continue
            coll_list = self.mongo[database].collection_names()
            for coll in coll_list:
                if coll.startswith("system"):
                    continue
                namespace = "%s.%s" % (database, coll)
                user_namespaces.append(namespace)
        return user_namespaces

    def stop(self):
        """Stops any running threads
        """
        logging.info(
            "Mongo DocManager Stopped: If you will not target this system "
            "again with mongo-connector then please drop the database "
            "__mongo_connector in order to return resources to the OS."
        )

    @wrap_exceptions
    def update(self, doc, update_spec):
        """Apply updates given in update_spec to the document whose id
        matches that of doc.

        """
        db, coll = doc['ns'].split('.', 1)
        updated = self.mongo[db][coll].find_and_modify(
            {self.unique_key: doc['_id']},
            update_spec,
            new=True
        )
        return updated

    @wrap_exceptions
    def upsert(self, doc):
        """Update or insert a document into Mongo
        """
        database, coll = doc['ns'].split('.', 1)
        ts = doc.pop("_ts")
        ns = doc.pop("ns")

        self.mongo["__mongo_connector"][ns].save({
            self.unique_key: doc[self.unique_key],
            "_ts": ts,
            "ns": ns
        })
        self.mongo[database][coll].save(doc)

    @wrap_exceptions
    def remove(self, doc):
        """Removes document from Mongo

        The input is a python dictionary that represents a mongo document.
        The documents has ns and _ts fields.
        """
        database, coll = doc['ns'].split('.', 1)
        self.mongo[database][coll].remove(
            {self.unique_key: doc[self.unique_key]})
        self.mongo["__mongo_connector"][doc['ns']].remove(
            {self.unique_key: doc[self.unique_key]})

    @wrap_exceptions
    def search(self, start_ts, end_ts):
        """Called to query Mongo for documents in a time range.
        """
        for namespace in self._namespaces():
            database, coll = namespace.split('.', 1)
            for ts_ns_doc in self.mongo["__mongo_connector"][namespace].find(
                {'_ts': {'$lte': end_ts,
                         '$gte': start_ts}}
            ):
                yield ts_ns_doc

    def commit(self):
        """ Performs a commit
        """
        return

    @wrap_exceptions
    def get_last_doc(self):
        """Returns the last document stored in Mongo.
        """
        def docs_by_ts():
            for namespace in self._namespaces():
                database, coll = namespace.split('.', 1)
                mc_coll = self.mongo["__mongo_connector"][namespace]
                for ts_ns_doc in mc_coll.find(limit=1).sort('_ts', -1):
                    yield ts_ns_doc

        return max(docs_by_ts(), key=lambda x: x["_ts"])

    @wrap_exceptions
    def _remove(self):
        """For test purposes only. Removes all documents in test.test
        """
        self.mongo['test']['test'].remove()

    @wrap_exceptions
    def _search(self):
        """For test purposes only. Performs search on MongoDB with empty query.
        Does not have to be implemented.
        """
        return self.mongo['test']['test'].find()

########NEW FILE########
__FILENAME__ = sample_doc_manager
# Copyright 2013-2014 MongoDB, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Receives documents from the oplog worker threads and indexes them
    into the backend.

    This file is a starting point for a doc manager. The intent is
    that this file can be used as an example to add on different backends.
    To extend this to other systems, simply implement the exact same class and
    replace the method definitions with API calls for the desired backend.
    Each method is detailed to describe the desired behavior.
"""

import exceptions
from mongo_connector.constants import DEFAULT_COMMIT_INTERVAL


class DocManager():
    """The DocManager class creates a connection to the backend engine and
    adds/removes documents, and in the case of rollback, searches for them.

    The reason for storing id/doc pairs as opposed to doc's is so that
    multiple updates to the same doc reflect the most up to date version as
    opposed to multiple, slightly different versions of a doc.
    """

    def __init__(self, url=None, auto_commit_interval=DEFAULT_COMMIT_INTERVAL,
                 unique_key='_id', **kwargs):
        """Verify URL and establish a connection.

        This method should, if necessarity, verify the url to the backend
        and return None if that fails.
        It should also create the connection to the backend, and start a
        periodic committer if necessary.
        The unique_key should default to '_id' and it is an obligatory
        parameter.
        It requires a url parameter iff connector.py is called with
        the -b parameter. Otherwise, it doesn't require any other parameter
        (e.g. if the target engine doesn't need a URL)
        It should raise ConnectionFailed if the URL is not valid.
        """
        raise exceptions.NotImplementedError

    def stop(self):

        """This method must stop any threads running from the DocManager.
        In some cases this simply stops a timer thread, whereas in other
        DocManagers it does nothing because the manager doesn't use any
        threads. This method is only called when the MongoConnector is
        forced to terminate, either due to errors or as part of normal
        procedure.
        """
        raise exceptions.NotImplementedError

    def upsert(self, doc):
        """Update or insert a document into engine.
        The documents has ns and _ts fields.

        This method should call whatever add/insert/update method exists for
        the backend engine and add the document in there. The input will
        always be one mongo document, represented as a Python dictionary.
        This document will be the current mongo version of the document,
        not necessarily the version at the time the upsert was made; the
        doc manager will be responsible to track the changes if necessary.
        Note this is not necessary to ensure consistency.
        It is possible to get two inserts for the same document with the same
        contents if there is considerable delay in trailing the oplog.
        We have only one function for update and insert because incremental
        updates are not supported, so there is no update option.
        """
        raise exceptions.NotImplementedError

    def remove(self, doc):
        """Removes documents from engine

        The input is a python dictionary that represents a mongo document.
        """
        raise exceptions.NotImplementedError

    def search(self, start_ts, end_ts):
        """Called to query engine for documents in a time range,
        including start_ts and end_ts

        This method is only used by rollbacks to query all the documents in
        engine within a certain timestamp window. The input will be two longs
        (converted from Bson timestamp) which specify the time range.
        The 32 most significant bits are the Unix Epoch Time, and the other
        bits are the increment. For all purposes, the function should just
        do a simple search for timestamps between these values
        treating them as simple longs. The return value should be an iterable
        set of documents.
        """
        raise exceptions.NotImplementedError

    def commit(self):
        """This function is used to force a refresh/commit.

        It is used only in the beginning of rollbacks and in test cases, and is
        not meant to be called in other circumstances. The body should commit
        all documents to the backend engine (like auto_commit), but not have
        any timers or run itself again (unlike auto_commit). In the event of
        too many engine searchers, the commit can be wrapped in a
        retry_until_ok to keep trying until the commit goes through.
        """
        raise exceptions.NotImplementedError

    def run_auto_commit(self):
        """Periodically commits to the engine server, if needed.

        This function commits all changes to the engine, and then
        starts a timer that calls this function again in
        self.auto_commit_interval seconds. The reason for this
        function is to prevent overloading engine from other
        searchers. This function may be modified based on the backend
        engine and how commits are handled, as timers may not be
        necessary in all instances. It does not have to be implemented
        if commits are not necessary
        """
        raise exceptions.NotImplementedError

    def get_last_doc(self):
        """Returns the last document stored in the engine.

        This method is used for rollbacks to establish the rollback window,
        which is the gap between the last document on a mongo shard and the
        last document in engine. If there are no documents, this functions
        returns None. Otherwise, it returns the first document.
        """
        raise exceptions.NotImplementedError

########NEW FILE########
__FILENAME__ = solr_doc_manager
# Copyright 2013-2014 MongoDB, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Receives documents from the oplog worker threads and indexes them
into the backend.

This file is a document manager for the Solr search engine, but the intent
is that this file can be used as an example to add on different backends.
To extend this to other systems, simply implement the exact same class and
replace the method definitions with API calls for the desired backend.
"""
import re
import json

import bson.json_util as bsjson
from pysolr import Solr, SolrError

from mongo_connector import errors
from mongo_connector.constants import (DEFAULT_COMMIT_INTERVAL,
                                       DEFAULT_MAX_BULK)
from mongo_connector.util import retry_until_ok
from mongo_connector.doc_managers import DocManagerBase, exception_wrapper


# pysolr only has 1 exception: SolrError
wrap_exceptions = exception_wrapper({
    SolrError: errors.OperationFailed})

ADMIN_URL = 'admin/luke?show=schema&wt=json'

decoder = json.JSONDecoder()


class DocManager(DocManagerBase):
    """The DocManager class creates a connection to the backend engine and
    adds/removes documents, and in the case of rollback, searches for them.

    The reason for storing id/doc pairs as opposed to doc's is so that multiple
    updates to the same doc reflect the most up to date version as opposed to
    multiple, slightly different versions of a doc.
    """

    def __init__(self, url, auto_commit_interval=DEFAULT_COMMIT_INTERVAL,
                 unique_key='_id', chunk_size=DEFAULT_MAX_BULK, **kwargs):
        """Verify Solr URL and establish a connection.
        """
        self.solr = Solr(url)
        self.unique_key = unique_key
        # pysolr does things in milliseconds
        if auto_commit_interval is not None:
            self.auto_commit_interval = auto_commit_interval * 1000
        else:
            self.auto_commit_interval = None
        self.chunk_size = chunk_size
        self.field_list = []
        self._build_fields()

    def _parse_fields(self, result, field_name):
        """ If Schema access, parse fields and build respective lists
        """
        field_list = []
        for key, value in result.get('schema', {}).get(field_name, {}).items():
            if key not in field_list:
                field_list.append(key)
        return field_list

    @wrap_exceptions
    def _build_fields(self):
        """ Builds a list of valid fields
        """
        declared_fields = self.solr._send_request('get', ADMIN_URL)
        result = decoder.decode(declared_fields)
        self.field_list = self._parse_fields(result, 'fields')

        # Build regular expressions to match dynamic fields.
        # dynamic field names may have exactly one wildcard, either at
        # the beginning or the end of the name
        self._dynamic_field_regexes = []
        for wc_pattern in self._parse_fields(result, 'dynamicFields'):
            if wc_pattern[0] == "*":
                self._dynamic_field_regexes.append(
                    re.compile(".*%s\Z" % wc_pattern[1:]))
            elif wc_pattern[-1] == "*":
                self._dynamic_field_regexes.append(
                    re.compile("\A%s.*" % wc_pattern[:-1]))

    def _clean_doc(self, doc):
        """Reformats the given document before insertion into Solr.

        This method reformats the document in the following ways:
          - removes extraneous fields that aren't defined in schema.xml
          - unwinds arrays in order to find and later flatten sub-documents
          - flattens the document so that there are no sub-documents, and every
            value is associated with its dot-separated path of keys

        An example:
          {"a": 2,
           "b": {
             "c": {
               "d": 5
             }
           },
           "e": [6, 7, 8]
          }

        becomes:
          {"a": 2, "b.c.d": 5, "e.0": 6, "e.1": 7, "e.2": 8}

        """
        # SOLR cannot index fields within sub-documents, so flatten documents
        # with the dot-separated path to each value as the respective key
        def flattened(doc):
            def flattened_kernel(doc, path):
                for k, v in doc.items():
                    path.append(k)
                    if isinstance(v, dict):
                        for inner_k, inner_v in flattened_kernel(v, path):
                            yield inner_k, inner_v
                    elif isinstance(v, list):
                        for li, lv in enumerate(v):
                            path.append(str(li))
                            if isinstance(lv, dict):
                                for dk, dv in flattened_kernel(lv, path):
                                    yield dk, dv
                            else:
                                yield ".".join(path), lv
                            path.pop()
                    else:
                        yield ".".join(path), v
                    path.pop()
            return dict(flattened_kernel(doc, []))

        # Translate the _id field to whatever unique key we're using
        doc[self.unique_key] = doc["_id"]
        flat_doc = flattened(doc)

        # Only include fields that are explicitly provided in the
        # schema or match one of the dynamic field patterns, if
        # we were able to retrieve the schema
        if len(self.field_list) + len(self._dynamic_field_regexes) > 0:
            def include_field(field):
                return field in self.field_list or any(
                    regex.match(field) for regex in self._dynamic_field_regexes
                )
            return dict((k, v) for k, v in flat_doc.items() if include_field(k))
        return flat_doc

    def stop(self):
        """ Stops the instance
        """
        pass

    @wrap_exceptions
    def update(self, doc, update_spec):
        """Apply updates given in update_spec to the document whose id
        matches that of doc.

        """
        query = "%s:%s" % (self.unique_key, str(doc['_id']))
        results = self.solr.search(query)
        # Results is a lazy iterable containing only 1 result
        for doc in results:
            updated = self.apply_update(doc, update_spec)
            self.upsert(updated)
        return updated

    @wrap_exceptions
    def upsert(self, doc):
        """Update or insert a document into Solr

        This method should call whatever add/insert/update method exists for
        the backend engine and add the document in there. The input will
        always be one mongo document, represented as a Python dictionary.
        """
        if self.auto_commit_interval is not None:
            self.solr.add([self._clean_doc(doc)],
                          commit=(self.auto_commit_interval == 0),
                          commitWithin=str(self.auto_commit_interval))
        else:
            self.solr.add([self._clean_doc(doc)], commit=False)

    @wrap_exceptions
    def bulk_upsert(self, docs):
        """Update or insert multiple documents into Solr

        docs may be any iterable
        """
        if self.auto_commit_interval is not None:
            add_kwargs = {
                "commit": (self.auto_commit_interval == 0),
                "commitWithin": self.auto_commit_interval
            }
        else:
            add_kwargs = {"commit": False}

        cleaned = (self._clean_doc(d) for d in docs)
        if self.chunk_size > 0:
            batch = list(next(cleaned) for i in range(self.chunk_size))
            while batch:
                self.solr.add(batch, **add_kwargs)
                batch = list(next(cleaned)
                             for i in range(self.chunk_size))
        else:
            self.solr.add(cleaned, **add_kwargs)

    @wrap_exceptions
    def remove(self, doc):
        """Removes documents from Solr

        The input is a python dictionary that represents a mongo document.
        """
        self.solr.delete(id=str(doc[self.unique_key]),
                         commit=(self.auto_commit_interval == 0))

    @wrap_exceptions
    def _remove(self):
        """Removes everything
        """
        self.solr.delete(q='*:*', commit=(self.auto_commit_interval == 0))

    @wrap_exceptions
    def search(self, start_ts, end_ts):
        """Called to query Solr for documents in a time range.
        """
        query = '_ts: [%s TO %s]' % (start_ts, end_ts)
        return self.solr.search(query, rows=100000000)

    @wrap_exceptions
    def _search(self, query):
        """For test purposes only. Performs search on Solr with given query
            Does not have to be implemented.
        """
        return self.solr.search(query, rows=200)

    def commit(self):
        """This function is used to force a commit.
        """
        retry_until_ok(self.solr.commit)

    @wrap_exceptions
    def get_last_doc(self):
        """Returns the last document stored in the Solr engine.
        """
        #search everything, sort by descending timestamp, return 1 row
        try:
            result = self.solr.search('*:*', sort='_ts desc', rows=1)
        except ValueError:
            return None

        if len(result) == 0:
            return None

        return result.docs[0]

########NEW FILE########
__FILENAME__ = errors
# Copyright 2013-2014 MongoDB, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Exceptions raised by the mongo_connector package."""


class MongoConnectorError(Exception):
    """Base class for all exceptions in the mongo_connector package
    """


class ConnectionFailed(MongoConnectorError):
    """Raised when mongo-connector can't connect to target system
    """


class OperationFailed(MongoConnectorError):
    """Raised for failed commands on the destination database
    """


class EmptyDocsError(MongoConnectorError):
    """Raised on attempts to upsert empty sequences of documents
    """


class ConnectorError(MongoConnectorError):
    """Raised when creating a mongo_connector.Connector object with
    nonsensical parameters
    """

########NEW FILE########
__FILENAME__ = locking_dict
import threading


class LockingDict():

    def __init__(self):

        self.dict = {}
        self.lock = threading.Lock()

    def __enter__(self):
        self.acquire_lock()
        return self

    def __exit__(self, type, value, traceback):
        self.release_lock()

    def get_dict(self):
        return self.dict

    def acquire_lock(self):
        self.lock.acquire()

    def release_lock(self):
        self.lock.release()

########NEW FILE########
__FILENAME__ = oplog_manager
# Copyright 2013-2014 MongoDB, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Tails the oplog of a shard and returns entries
"""

import bson
import logging
try:
    import Queue as queue
except ImportError:
    import queue
import pymongo
import sys
import time
import threading
import traceback
from mongo_connector import errors, util
from mongo_connector.constants import DEFAULT_BATCH_SIZE
from mongo_connector.util import retry_until_ok

from pymongo import MongoClient


class OplogThread(threading.Thread):
    """OplogThread gathers the updates for a single oplog.
    """
    def __init__(self, primary_conn, main_address, oplog_coll, is_sharded,
                 doc_manager, oplog_progress_dict, namespace_set, auth_key,
                 auth_username, repl_set=None, collection_dump=True,
                 batch_size=DEFAULT_BATCH_SIZE, fields=None,
                 dest_mapping={}):
        """Initialize the oplog thread.
        """
        super(OplogThread, self).__init__()

        self.batch_size = batch_size

        #The connection to the primary for this replicaSet.
        self.primary_connection = primary_conn

        #Boolean chooses whether to dump the entire collection if no timestamp
        # is present in the config file
        self.collection_dump = collection_dump

        #The mongos for sharded setups
        #Otherwise the same as primary_connection.
        #The value is set later on.
        self.main_connection = None

        #The connection to the oplog collection
        self.oplog = oplog_coll

        #Boolean describing whether the cluster is sharded or not
        self.is_sharded = is_sharded

        #A document manager for each target system.
        #These are the same for all threads.
        if type(doc_manager) == list:
            self.doc_managers = doc_manager
        else:
            self.doc_managers = [doc_manager]

        #Boolean describing whether or not the thread is running.
        self.running = True

        #Stores the timestamp of the last oplog entry read.
        self.checkpoint = None

        #A dictionary that stores OplogThread/timestamp pairs.
        #Represents the last checkpoint for a OplogThread.
        self.oplog_progress = oplog_progress_dict

        #The set of namespaces to process from the mongo cluster.
        self.namespace_set = namespace_set

        #The dict of source namespaces to destination namespaces
        self.dest_mapping = dest_mapping

        #If authentication is used, this is an admin password.
        self.auth_key = auth_key

        #This is the username used for authentication.
        self.auth_username = auth_username

        # Set of fields to export
        self._fields = set(fields) if fields else None

        logging.info('OplogThread: Initializing oplog thread')

        if is_sharded:
            self.main_connection = MongoClient(main_address)
        else:
            self.main_connection = MongoClient(main_address,
                                               replicaSet=repl_set)
            self.oplog = self.main_connection['local']['oplog.rs']

        if auth_key is not None:
            #Authenticate for the whole system
            self.primary_connection['admin'].authenticate(
                auth_username, auth_key)
            self.main_connection['admin'].authenticate(
                auth_username, auth_key)
        if not self.oplog.find_one():
            err_msg = 'OplogThread: No oplog for thread:'
            logging.warning('%s %s' % (err_msg, self.primary_connection))

    @property
    def fields(self):
        return self._fields

    @fields.setter
    def fields(self, value):
        if value:
            self._fields = set(value)
            # Always include _id field
            self._fields.add('_id')
        else:
            self._fields = None

    def run(self):
        """Start the oplog worker.
        """
        logging.debug("OplogThread: Run thread started")
        while self.running is True:
            logging.debug("OplogThread: Getting cursor")
            cursor = self.init_cursor()
            logging.debug("OplogThread: Got the cursor, go go go!")

            # we've fallen too far behind
            if cursor is None and self.checkpoint is not None:
                err_msg = "OplogThread: Last entry no longer in oplog"
                effect = "cannot recover!"
                logging.error('%s %s %s' % (err_msg, effect, self.oplog))
                self.running = False
                continue

            #The only entry is the last one we processed
            if cursor is None or util.retry_until_ok(cursor.count) == 1:
                logging.debug("OplogThread: Last entry is the one we "
                              "already processed.  Up to date.  Sleeping.")
                time.sleep(1)
                continue

            last_ts = None
            err = False
            remove_inc = 0
            upsert_inc = 0
            update_inc = 0
            try:
                logging.debug("OplogThread: about to process new oplog "
                              "entries")
                while cursor.alive and self.running:
                    logging.debug("OplogThread: Cursor is still"
                                  " alive and thread is still running.")
                    for n, entry in enumerate(cursor):

                        logging.debug("OplogThread: Iterating through cursor,"
                                      " document number in this cursor is %d"
                                      % n)
                        # Break out if this thread should stop
                        if not self.running:
                            break

                        # Don't replicate entries resulting from chunk moves
                        if entry.get("fromMigrate"):
                            continue

                        # Take fields out of the oplog entry that
                        # shouldn't be replicated. This may nullify
                        # the document if there's nothing to do.
                        if not self.filter_oplog_entry(entry):
                            continue

                        #sync the current oplog operation
                        operation = entry['op']
                        ns = entry['ns']

                        # use namespace mapping if one exists
                        ns = self.dest_mapping.get(entry['ns'], ns)

                        for docman in self.doc_managers:
                            try:
                                logging.debug("OplogThread: Operation for this "
                                              "entry is %s" % str(operation))

                                # Remove
                                if operation == 'd':
                                    entry['_id'] = entry['o']['_id']
                                    docman.remove(entry)
                                    remove_inc += 1
                                # Insert
                                elif operation == 'i':  # Insert
                                    # Retrieve inserted document from
                                    # 'o' field in oplog record
                                    doc = entry.get('o')
                                    # Extract timestamp and namespace
                                    doc['_ts'] = util.bson_ts_to_long(
                                        entry['ts'])
                                    doc['ns'] = ns
                                    docman.upsert(doc)
                                    upsert_inc += 1
                                # Update
                                elif operation == 'u':
                                    doc = {"_id": entry['o2']['_id'],
                                           "_ts": util.bson_ts_to_long(
                                               entry['ts']),
                                           "ns": ns}
                                    # 'o' field contains the update spec
                                    docman.update(doc, entry.get('o', {}))
                                    update_inc += 1
                            except errors.OperationFailed:
                                logging.exception(
                                    "Unable to process oplog document %r"
                                    % entry)
                            except errors.ConnectionFailed:
                                logging.exception(
                                    "Connection failed while processing oplog "
                                    "document %r" % entry)

                        if (remove_inc + upsert_inc + update_inc) % 1000 == 0:
                            logging.debug(
                                "OplogThread: Documents removed: %d, "
                                "inserted: %d, updated: %d so far" % (
                                    remove_inc, upsert_inc, update_inc))

                        logging.debug("OplogThread: Doc is processed.")

                        last_ts = entry['ts']

                        # update timestamp per batch size
                        # n % -1 (default for self.batch_size) == 0 for all n
                        if n % self.batch_size == 1 and last_ts is not None:
                            self.checkpoint = last_ts
                            self.update_checkpoint()

                    # update timestamp after running through oplog
                    if last_ts is not None:
                        logging.debug("OplogThread: updating checkpoint after"
                                      "processing new oplog entries")
                        self.checkpoint = last_ts
                        self.update_checkpoint()

            except (pymongo.errors.AutoReconnect,
                    pymongo.errors.OperationFailure,
                    pymongo.errors.ConfigurationError):
                logging.exception(
                    "Cursor closed due to an exception. "
                    "Will attempt to reconnect.")
                err = True

            if err is True and self.auth_key is not None:
                self.primary_connection['admin'].authenticate(
                    self.auth_username, self.auth_key)
                self.main_connection['admin'].authenticate(
                    self.auth_username, self.auth_key)
                err = False

            # update timestamp before attempting to reconnect to MongoDB,
            # after being join()'ed, or if the cursor closes
            if last_ts is not None:
                logging.debug("OplogThread: updating checkpoint after an "
                              "Exception, cursor closing, or join() on this"
                              "thread.")
                self.checkpoint = last_ts
                self.update_checkpoint()

            logging.debug("OplogThread: Sleeping. Documents removed: %d, "
                          "upserted: %d, updated: %d"
                          % (remove_inc, upsert_inc, update_inc))
            time.sleep(2)

    def join(self):
        """Stop this thread from managing the oplog.
        """
        logging.debug("OplogThread: exiting due to join call.")
        self.running = False
        threading.Thread.join(self)

    def filter_oplog_entry(self, entry):
        """Remove fields from an oplog entry that should not be replicated."""
        if not self._fields:
            return entry

        def pop_excluded_fields(doc):
            for key in set(doc) - self._fields:
                doc.pop(key)

        # 'i' indicates an insert. 'o' field is the doc to be inserted.
        if entry['op'] == 'i':
            pop_excluded_fields(entry['o'])
        # 'u' indicates an update. 'o' field is the update spec.
        elif entry['op'] == 'u':
            pop_excluded_fields(entry['o'].get("$set", {}))
            pop_excluded_fields(entry['o'].get("$unset", {}))
            # not allowed to have empty $set/$unset, so remove if empty
            if "$set" in entry['o'] and not entry['o']['$set']:
                entry['o'].pop("$set")
            if "$unset" in entry['o'] and not entry['o']['$unset']:
                entry['o'].pop("$unset")
            if not entry['o']:
                return None

        return entry

    def get_oplog_cursor(self, timestamp):
        """Move cursor to the proper place in the oplog.
        """

        logging.debug("OplogThread: Getting the oplog cursor and moving it "
                      "to the proper place in the oplog.")

        if timestamp is None:
            return None

        cursor, cursor_len = None, 0
        while (True):
            try:
                logging.debug("OplogThread: Getting the oplog cursor "
                              "in the while true loop for get_oplog_cursor")
                if not self.namespace_set:
                    cursor = self.oplog.find(
                        {'ts': {'$gte': timestamp}},
                        tailable=True, await_data=True
                    )
                else:
                    cursor = self.oplog.find(
                        {'ts': {'$gte': timestamp},
                         'ns': {'$in': self.namespace_set}},
                        tailable=True, await_data=True
                    )
                # Applying 8 as the mask to the cursor enables OplogReplay
                cursor.add_option(8)
                logging.debug("OplogThread: Cursor created, getting a count.")
                cursor_len = cursor.count()
                logging.debug("OplogThread: Count is %d" % cursor_len)
                break
            except (pymongo.errors.AutoReconnect,
                    pymongo.errors.OperationFailure,
                    pymongo.errors.ConfigurationError):
                pass
        if cursor_len == 0:
            logging.debug("OplogThread: Initiating rollback from "
                          "get_oplog_cursor")
            #rollback, we are past the last element in the oplog
            timestamp = self.rollback()

            logging.info('Finished rollback')
            return self.get_oplog_cursor(timestamp)
        first_oplog_entry = retry_until_ok(lambda: cursor[0])
        cursor_ts_long = util.bson_ts_to_long(first_oplog_entry.get("ts"))
        given_ts_long = util.bson_ts_to_long(timestamp)
        if cursor_ts_long > given_ts_long:
            # first entry in oplog is beyond timestamp, we've fallen behind!
            return None
        elif cursor_len == 1:     # means we are the end of the oplog
            self.checkpoint = timestamp
            #to commit new TS after rollbacks

            return cursor
        elif cursor_len > 1:
            doc = retry_until_ok(next, cursor)
            if timestamp == doc['ts']:
                return cursor
            else:               # error condition
                logging.error('OplogThread: %s Bad timestamp in config file'
                              % self.oplog)
                return None

    def dump_collection(self):
        """Dumps collection into the target system.

        This method is called when we're initializing the cursor and have no
        configs i.e. when we're starting for the first time.
        """

        dump_set = self.namespace_set or []
        logging.debug("OplogThread: Dumping set of collections %s " % dump_set)

        #no namespaces specified
        if not self.namespace_set:
            db_list = retry_until_ok(self.main_connection.database_names)
            for database in db_list:
                if database == "config" or database == "local":
                    continue
                coll_list = retry_until_ok(
                    self.main_connection[database].collection_names)
                for coll in coll_list:
                    if coll.startswith("system"):
                        continue
                    namespace = "%s.%s" % (database, coll)
                    dump_set.append(namespace)

        timestamp = util.retry_until_ok(self.get_last_oplog_timestamp)
        if timestamp is None:
            return None
        long_ts = util.bson_ts_to_long(timestamp)

        def docs_to_dump():
            for namespace in dump_set:
                logging.info("OplogThread: dumping collection %s"
                             % namespace)
                database, coll = namespace.split('.', 1)
                last_id = None
                attempts = 0

                # Loop to handle possible AutoReconnect
                while attempts < 60:
                    target_coll = self.main_connection[database][coll]
                    if not last_id:
                        cursor = util.retry_until_ok(
                            target_coll.find,
                            fields=self._fields,
                            sort=[("_id", pymongo.ASCENDING)]
                        )
                    else:
                        cursor = util.retry_until_ok(
                            target_coll.find,
                            {"_id": {"$gt": last_id}},
                            fields=self._fields,
                            sort=[("_id", pymongo.ASCENDING)]
                        )
                    try:
                        for doc in cursor:
                            if not self.running:
                                raise StopIteration
                            doc["ns"] = self.dest_mapping.get(
                                namespace, namespace)
                            doc["_ts"] = long_ts
                            last_id = doc["_id"]
                            yield doc
                        break
                    except pymongo.errors.AutoReconnect:
                        attempts += 1
                        time.sleep(1)

        # Extra threads (if any) that assist with collection dumps
        dumping_threads = []
        # Did the dump succeed for all target systems?
        dump_success = True
        # Holds any exceptions we can't recover from
        errors = queue.Queue()
        try:
            for dm in self.doc_managers:
                # Bulk upsert if possible
                if hasattr(dm, "bulk_upsert"):
                    logging.debug("OplogThread: Using bulk upsert function for"
                                  "collection dump")
                    # Slight performance gain breaking dump into separate
                    # threads, only if > 1 replication target
                    if len(self.doc_managers) == 1:
                        dm.bulk_upsert(docs_to_dump())
                    else:
                        def do_dump(error_queue):
                            all_docs = docs_to_dump()
                            try:
                                dm.bulk_upsert(all_docs)
                            except Exception:
                                # Likely exceptions:
                                # pymongo.errors.OperationFailure,
                                # mongo_connector.errors.ConnectionFailed
                                # mongo_connector.errors.OperationFailed
                                error_queue.put(sys.exc_info())

                        t = threading.Thread(target=do_dump, args=(errors,))
                        dumping_threads.append(t)
                        t.start()
                else:
                    logging.debug("OplogThread: DocManager %s has not"
                                  "bulk_upsert method.  Upserting documents "
                                  "serially for collection dump." % str(dm))
                    num = 0
                    for num, doc in enumerate(docs_to_dump()):
                        if num % 10000 == 0:
                            logging.debug("Upserted %d docs." % num)
                        dm.upsert(doc)
                    logging.debug("Upserted %d docs" % num)

            # cleanup
            for t in dumping_threads:
                t.join()

        except Exception:
            # See "likely exceptions" comment above
            errors.put(sys.exc_info())

        # Print caught exceptions
        try:
            while True:
                klass, value, trace = errors.get_nowait()
                dump_success = False
                traceback.print_exception(klass, value, trace)
        except queue.Empty:
            pass

        if not dump_success:
            err_msg = "OplogThread: Failed during dump collection"
            effect = "cannot recover!"
            logging.error('%s %s %s' % (err_msg, effect, self.oplog))
            self.running = False
            return None

        return timestamp

    def get_last_oplog_timestamp(self):
        """Return the timestamp of the latest entry in the oplog.
        """
        if not self.namespace_set:
            curr = self.oplog.find().sort(
                '$natural', pymongo.DESCENDING
            ).limit(1)
        else:
            curr = self.oplog.find(
                {'ns': {'$in': self.namespace_set}}
            ).sort('$natural', pymongo.DESCENDING).limit(1)

        if curr.count(with_limit_and_skip=True) == 0:
            return None

        logging.debug("OplogThread: Last oplog entry has timestamp %d."
                      % curr[0]['ts'].time)
        return curr[0]['ts']

    def init_cursor(self):
        """Position the cursor appropriately.

        The cursor is set to either the beginning of the oplog, or
        wherever it was last left off.
        """
        logging.debug("OplogThread: Initializing the oplog cursor.")
        timestamp = self.read_last_checkpoint()

        if timestamp is None and self.collection_dump:
            timestamp = self.dump_collection()
            if timestamp:
                msg = "Dumped collection into target system"
                logging.info('OplogThread: %s %s'
                             % (self.oplog, msg))
        elif timestamp is None:
            # set timestamp to top of oplog
            timestamp = retry_until_ok(self.get_last_oplog_timestamp)

        self.checkpoint = timestamp
        cursor = self.get_oplog_cursor(timestamp)
        if cursor is not None:
            self.update_checkpoint()

        return cursor

    def update_checkpoint(self):
        """Store the current checkpoint in the oplog progress dictionary.
        """
        with self.oplog_progress as oplog_prog:
            oplog_dict = oplog_prog.get_dict()
            oplog_dict[str(self.oplog)] = self.checkpoint
            logging.debug("OplogThread: oplog checkpoint updated to %s" %
                          str(self.checkpoint))

    def read_last_checkpoint(self):
        """Read the last checkpoint from the oplog progress dictionary.
        """
        oplog_str = str(self.oplog)
        ret_val = None

        with self.oplog_progress as oplog_prog:
            oplog_dict = oplog_prog.get_dict()
            if oplog_str in oplog_dict.keys():
                ret_val = oplog_dict[oplog_str]

        logging.debug("OplogThread: reading last checkpoint as %s " %
                      str(ret_val))
        return ret_val

    def rollback(self):
        """Rollback target system to consistent state.

        The strategy is to find the latest timestamp in the target system and
        the largest timestamp in the oplog less than the latest target system
        timestamp. This defines the rollback window and we just roll these
        back until the oplog and target system are in consistent states.
        """
        # Find the most recently inserted document in each target system
        logging.debug("OplogThread: Initiating rollback sequence to bring "
                      "system into a consistent state.")
        last_docs = []
        for dm in self.doc_managers:
            dm.commit()
            last_docs.append(dm.get_last_doc())

        # Of these documents, which is the most recent?
        last_inserted_doc = max(last_docs,
                                key=lambda x: x["_ts"] if x else float("-inf"))

        # Nothing has been replicated. No need to rollback target systems
        if last_inserted_doc is None:
            return None

        # Find the oplog entry that touched the most recent document.
        # We'll use this to figure where to pick up the oplog later.
        target_ts = util.long_to_bson_ts(last_inserted_doc['_ts'])
        last_oplog_entry = util.retry_until_ok(
            self.oplog.find_one,
            {'ts': {'$lte': target_ts}},
            sort=[('$natural', pymongo.DESCENDING)]
        )

        logging.debug("OplogThread: last oplog entry is %s"
                      % str(last_oplog_entry))

        # The oplog entry for the most recent document doesn't exist anymore.
        # If we've fallen behind in the oplog, this will be caught later
        if last_oplog_entry is None:
            return None

        # rollback_cutoff_ts happened *before* the rollback
        rollback_cutoff_ts = last_oplog_entry['ts']
        start_ts = util.bson_ts_to_long(rollback_cutoff_ts)
        # timestamp of the most recent document on any target system
        end_ts = last_inserted_doc['_ts']

        for dm in self.doc_managers:
            rollback_set = {}   # this is a dictionary of ns:list of docs

            # group potentially conflicted documents by namespace
            for doc in dm.search(start_ts, end_ts):
                if doc['ns'] in rollback_set:
                    rollback_set[doc['ns']].append(doc)
                else:
                    rollback_set[doc['ns']] = [doc]

            # retrieve these documents from MongoDB, either updating
            # or removing them in each target system
            for namespace, doc_list in rollback_set.items():
                # Get the original namespace
                original_namespace = namespace
                for source_name, dest_name in self.dest_mapping.items():
                    if dest_name == namespace:
                        original_namespace = source_name

                database, coll = original_namespace.split('.', 1)
                obj_id = bson.objectid.ObjectId
                bson_obj_id_list = [obj_id(doc['_id']) for doc in doc_list]

                to_update = util.retry_until_ok(
                    self.main_connection[database][coll].find,
                    {'_id': {'$in': bson_obj_id_list}},
                    fields=self._fields
                )
                #doc list are docs in target system, to_update are
                #docs in mongo
                doc_hash = {}  # hash by _id
                for doc in doc_list:
                    doc_hash[bson.objectid.ObjectId(doc['_id'])] = doc

                to_index = []

                def collect_existing_docs():
                    for doc in to_update:
                        if doc['_id'] in doc_hash:
                            del doc_hash[doc['_id']]
                            to_index.append(doc)
                retry_until_ok(collect_existing_docs)

                #delete the inconsistent documents
                logging.debug("OplogThread: Rollback, removing inconsistent "
                              "docs.")
                remov_inc = 0
                for doc in doc_hash.values():
                    try:
                        dm.remove(doc)
                        remov_inc += 1
                        logging.debug("OplogThread: Rollback, removed %s " %
                                      str(doc))
                    except errors.OperationFailed:
                        logging.warning(
                            "Could not delete document during rollback: %s "
                            "This can happen if this document was already "
                            "removed by another rollback happening at the "
                            "same time." % str(doc)
                        )

                logging.debug("OplogThread: Rollback, removed %d docs." %
                              remov_inc)

                #insert the ones from mongo
                logging.debug("OplogThread: Rollback, inserting documents "
                              "from mongo.")
                insert_inc = 0
                fail_insert_inc = 0
                for doc in to_index:
                    doc['_ts'] = util.bson_ts_to_long(rollback_cutoff_ts)
                    doc['ns'] = self.dest_mapping.get(namespace, namespace)
                    try:
                        insert_inc += 1
                        dm.upsert(doc)
                    except errors.OperationFailed as e:
                        fail_insert_inc += 1
                        logging.error("OplogThread: Rollback, Unable to "
                                      "insert %s with exception %s"
                                      % (doc, str(e)))

        logging.debug("OplogThread: Rollback, Successfully inserted %d "
                      " documents and failed to insert %d"
                      " documents.  Returning a rollback cutoff time of %s "
                      % (insert_inc, fail_insert_inc, str(rollback_cutoff_ts)))

        return rollback_cutoff_ts

########NEW FILE########
__FILENAME__ = util
# Copyright 2013-2014 MongoDB, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""A set of utilities used throughout the mongo-connector
"""

import time
import logging

from bson.timestamp import Timestamp


def bson_ts_to_long(timestamp):
    """Convert BSON timestamp into integer.

    Conversion rule is based from the specs
    (http://bsonspec.org/#/specification).
    """
    return ((timestamp.time << 32) + timestamp.inc)


def long_to_bson_ts(val):
    """Convert integer into BSON timestamp.
    """
    seconds = val >> 32
    increment = val & 0xffffffff

    return Timestamp(seconds, increment)


def retry_until_ok(func, *args, **kwargs):
    """Retry code block until it succeeds.

    If it does not succeed in 60 attempts, the function re-raises any
    error the function raised on its last attempt.

    """

    count = 0
    while True:
        try:
            return func(*args, **kwargs)
        except:
            count += 1
            if count > 60:
                logging.error('Call to %s failed too many times in '
                              'retry_until_ok', func)
                raise
            time.sleep(1)

########NEW FILE########
__FILENAME__ = test_elastic
# Copyright 2013-2014 MongoDB, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Test elastic search using the synchronizer, i.e. as it would be used by an
    user
"""
import time
import os
import sys
if sys.version_info[:2] == (2, 6):
    import unittest2 as unittest
else:
    import unittest

sys.path[0:0] = [""]

from elasticsearch import Elasticsearch
from pymongo import MongoClient

from tests import elastic_pair, mongo_host, STRESS_COUNT
from tests.setup_cluster import (start_replica_set,
                                 kill_replica_set,
                                 restart_mongo_proc,
                                 kill_mongo_proc)
from mongo_connector.doc_managers.elastic_doc_manager import DocManager
from mongo_connector.connector import Connector
from mongo_connector.util import retry_until_ok
from pymongo.errors import OperationFailure, AutoReconnect
from tests.util import assert_soon


class ElasticsearchTestCase(unittest.TestCase):
    """Base class for all ES TestCases."""

    @classmethod
    def setUpClass(cls):
        cls.elastic_conn = Elasticsearch(hosts=[elastic_pair])
        cls.elastic_doc = DocManager(elastic_pair,
                                     auto_commit_interval=0)

    def setUp(self):
        # Create target index in elasticsearch
        self.elastic_conn.indices.create(index='test.test')
        self.elastic_conn.cluster.health(wait_for_status='yellow',
                                         index='test.test')

    def tearDown(self):
        self.elastic_conn.indices.delete(index='test.test', ignore=404)

    def _search(self):
        return self.elastic_doc._stream_search(
            index="test.test",
            body={"query": {"match_all": {}}}
        )

    def _count(self):
        return self.elastic_conn.count(index='test.test')['count']

    def _remove(self):
        self.elastic_conn.indices.delete_mapping(
            index="test.test",
            doc_type=self.elastic_doc.doc_type
        )
        self.elastic_conn.indices.refresh(index="test.test")


class TestElastic(ElasticsearchTestCase):
    """ Tests the Elastic instance
    """

    @classmethod
    def setUpClass(cls):
        """ Starts the cluster
        """
        super(TestElastic, cls).setUpClass()
        _, cls.secondary_p, cls.primary_p = start_replica_set('test-elastic')
        cls.conn = MongoClient(mongo_host, cls.primary_p,
                               replicaSet='test-elastic')

    @classmethod
    def tearDownClass(cls):
        """ Kills cluster instance
        """
        kill_replica_set('test-elastic')

    def tearDown(self):
        """ Ends the connector
        """
        super(TestElastic, self).tearDown()
        self.connector.join()

    def setUp(self):
        """ Starts a new connector for every test
        """
        super(TestElastic, self).setUp()
        try:
            os.unlink("config.txt")
        except OSError:
            pass
        open("config.txt", "w").close()
        self.connector = Connector(
            address='%s:%s' % (mongo_host, self.primary_p),
            oplog_checkpoint='config.txt',
            target_url=elastic_pair,
            ns_set=['test.test'],
            u_key='_id',
            auth_key=None,
            doc_manager='mongo_connector/doc_managers/elastic_doc_manager.py',
            auto_commit_interval=0
        )

        self.conn.test.test.drop()
        self.connector.start()
        assert_soon(lambda: len(self.connector.shard_set) > 0)
        assert_soon(lambda: self._count() == 0)

    def test_shard_length(self):
        """Tests the shard_length to see if the shard set was recognized
            properly
        """

        self.assertEqual(len(self.connector.shard_set), 1)

    def test_insert(self):
        """Tests insert
        """

        self.conn['test']['test'].insert({'name': 'paulie'})
        assert_soon(lambda: self._count() > 0)
        result_set_1 = list(self._search())
        self.assertEqual(len(result_set_1), 1)
        result_set_2 = self.conn['test']['test'].find_one()
        for item in result_set_1:
            self.assertEqual(item['_id'], str(result_set_2['_id']))
            self.assertEqual(item['name'], result_set_2['name'])

    def test_remove(self):
        """Tests remove
        """

        self.conn['test']['test'].insert({'name': 'paulie'})
        assert_soon(lambda: self._count() == 1)
        self.conn['test']['test'].remove({'name': 'paulie'})
        assert_soon(lambda: self._count() != 1)
        self.assertEqual(self._count(), 0)

    def test_rollback(self):
        """Tests rollback. We force a rollback by adding a doc, killing the
            primary, adding another doc, killing the new primary, and then
            restarting both.
        """

        primary_conn = MongoClient(mongo_host, self.primary_p)

        self.conn['test']['test'].insert({'name': 'paul'})
        condition1 = lambda: self.conn['test']['test'].find(
            {'name': 'paul'}).count() == 1
        condition2 = lambda: self._count() == 1
        assert_soon(condition1)
        assert_soon(condition2)

        kill_mongo_proc(self.primary_p, destroy=False)

        new_primary_conn = MongoClient(mongo_host, self.secondary_p)

        admin = new_primary_conn['admin']
        assert_soon(lambda: admin.command("isMaster")['ismaster'])
        time.sleep(5)
        retry_until_ok(self.conn.test.test.insert,
                       {'name': 'pauline'})
        assert_soon(lambda: self._count() == 2)
        result_set_1 = list(self._search())
        result_set_2 = self.conn['test']['test'].find_one({'name': 'pauline'})
        self.assertEqual(len(result_set_1), 2)
        #make sure pauline is there
        for item in result_set_1:
            if item['name'] == 'pauline':
                self.assertEqual(item['_id'], str(result_set_2['_id']))
        kill_mongo_proc(self.secondary_p, destroy=False)

        restart_mongo_proc(self.primary_p)
        while primary_conn['admin'].command("isMaster")['ismaster'] is False:
            time.sleep(1)

        restart_mongo_proc(self.secondary_p)

        time.sleep(2)
        result_set_1 = list(self._search())
        self.assertEqual(len(result_set_1), 1)
        for item in result_set_1:
            self.assertEqual(item['name'], 'paul')
        find_cursor = retry_until_ok(self.conn['test']['test'].find)
        self.assertEqual(retry_until_ok(find_cursor.count), 1)

    def test_stress(self):
        """Test stress by inserting and removing a large number of documents"""

        for i in range(0, STRESS_COUNT):
            self.conn['test']['test'].insert({'name': 'Paul ' + str(i)})
        time.sleep(5)
        condition = lambda: self._count() == STRESS_COUNT
        assert_soon(condition)
        self.assertEqual(
            set('Paul ' + str(i) for i in range(STRESS_COUNT)),
            set(item['name'] for item in self._search())
        )

    def test_stressed_rollback(self):
        """Test stressed rollback with number of documents equal to specified
            in global variable. Strategy for rollback is the same as before.
        """

        for i in range(0, STRESS_COUNT):
            self.conn['test']['test'].insert({'name': 'Paul ' + str(i)})

        condition = lambda: self._count() == STRESS_COUNT
        assert_soon(condition)
        primary_conn = MongoClient(mongo_host, self.primary_p)
        kill_mongo_proc(self.primary_p, destroy=False)

        new_primary_conn = MongoClient(mongo_host, self.secondary_p)

        admin = new_primary_conn['admin']
        assert_soon(lambda: admin.command("isMaster")['ismaster'])

        time.sleep(5)
        count = -1
        while count + 1 < STRESS_COUNT:
            try:
                count += 1
                self.conn['test']['test'].insert(
                    {'name': 'Pauline ' + str(count)})
            except (OperationFailure, AutoReconnect):
                time.sleep(1)
        assert_soon(lambda: self._count()
                    == self.conn['test']['test'].find().count())
        result_set_1 = self._search()
        for item in result_set_1:
            if 'Pauline' in item['name']:
                result_set_2 = self.conn['test']['test'].find_one(
                    {'name': item['name']})
                self.assertEqual(item['_id'], str(result_set_2['_id']))

        kill_mongo_proc(self.secondary_p, destroy=False)

        restart_mongo_proc(self.primary_p)
        db_admin = primary_conn["admin"]
        assert_soon(lambda: db_admin.command("isMaster")['ismaster'])
        restart_mongo_proc(self.secondary_p)

        search = self._search
        condition = lambda: sum(1 for _ in search()) == STRESS_COUNT
        assert_soon(condition)

        result_set_1 = list(self._search())
        self.assertEqual(len(result_set_1), STRESS_COUNT)
        for item in result_set_1:
            self.assertTrue('Paul' in item['name'])
        find_cursor = retry_until_ok(self.conn['test']['test'].find)
        self.assertEqual(retry_until_ok(find_cursor.count), STRESS_COUNT)


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_elastic_doc_manager
# Copyright 2013-2014 MongoDB, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Tests each of the functions in elastic_doc_manager
"""

import time
import sys
if sys.version_info[:2] == (2, 6):
    import unittest2 as unittest
else:
    import unittest
from tests import elastic_pair
from tests.test_elastic import ElasticsearchTestCase

sys.path[0:0] = [""]

from mongo_connector.doc_managers.elastic_doc_manager import DocManager


class ElasticDocManagerTester(ElasticsearchTestCase):
    """Test class for elastic_docManager
    """

    def test_update(self):
        doc = {"_id": '1', "ns": "test.test", "_ts": 1,
               "a": 1, "b": 2}
        self.elastic_doc.upsert(doc)
        # $set only
        update_spec = {"$set": {"a": 1, "b": 2}}
        doc = self.elastic_doc.update(doc, update_spec)
        self.assertEqual(doc, {"_id": '1', "ns": "test.test", "_ts": 1,
                               "a": 1, "b": 2})
        # $unset only
        update_spec = {"$unset": {"a": True}}
        doc = self.elastic_doc.update(doc, update_spec)
        self.assertEqual(doc, {"_id": '1', "ns": "test.test", "_ts": 1,
                               "b": 2})
        # mixed $set/$unset
        update_spec = {"$unset": {"b": True}, "$set": {"c": 3}}
        doc = self.elastic_doc.update(doc, update_spec)
        self.assertEqual(doc, {"_id": '1', "ns": "test.test", "_ts": 1,
                               "c": 3})

    def test_upsert(self):
        """Ensure we can properly insert into ElasticSearch via DocManager.
        """

        docc = {'_id': '1', 'name': 'John', 'ns': 'test.test'}
        self.elastic_doc.upsert(docc)
        res = self.elastic_conn.search(
            index="test.test",
            body={"query": {"match_all": {}}}
        )["hits"]["hits"]
        for doc in res:
            doc = doc["_source"]
            self.assertTrue(doc['_id'] == '1' and doc['name'] == 'John')

    def test_bulk_upsert(self):
        """Ensure we can properly insert many documents at once into
        ElasticSearch via DocManager.

        """
        self.elastic_doc.bulk_upsert([])

        docs = ({"_id": i, "ns": "test.test"} for i in range(1000))
        self.elastic_doc.bulk_upsert(docs)
        res = self.elastic_conn.search(
            index="test.test",
            body={"query": {"match_all": {}}},
            size=1001
        )["hits"]["hits"]
        returned_ids = sorted(int(doc["_source"]["_id"]) for doc in res)
        self.assertEqual(len(returned_ids), 1000)
        for i, r in enumerate(returned_ids):
            self.assertEqual(r, i)

        docs = ({"_id": i, "weight": 2*i,
                 "ns": "test.test"} for i in range(1000))
        self.elastic_doc.bulk_upsert(docs)

        res = self.elastic_conn.search(
            index="test.test",
            body={"query": {"match_all": {}}},
            size=1001
        )["hits"]["hits"]
        returned_ids = sorted(int(doc["_source"]["weight"]) for doc in res)
        self.assertEqual(len(returned_ids), 1000)
        for i, r in enumerate(returned_ids):
            self.assertEqual(r, 2*i)

    def test_remove(self):
        """Ensure we can properly delete from ElasticSearch via DocManager.
        """

        docc = {'_id': '1', 'name': 'John', 'ns': 'test.test'}
        self.elastic_doc.upsert(docc)
        res = self.elastic_conn.search(
            index="test.test",
            body={"query": {"match_all": {}}}
        )["hits"]["hits"]
        res = [x["_source"] for x in res]
        self.assertEqual(len(res), 1)

        self.elastic_doc.remove(docc)
        res = self.elastic_conn.search(
            index="test.test",
            body={"query": {"match_all": {}}}
        )["hits"]["hits"]
        res = [x["_source"] for x in res]
        self.assertEqual(len(res), 0)

    def test_full_search(self):
        """Query ElasticSearch for all docs via API and via DocManager's
            _search(), compare.
        """

        docc = {'_id': '1', 'name': 'John', 'ns': 'test.test'}
        self.elastic_doc.upsert(docc)
        docc = {'_id': '2', 'name': 'Paul', 'ns': 'test.test'}
        self.elastic_doc.upsert(docc)
        search = list(self._search())
        search2 = self.elastic_conn.search(
            index="test.test",
            body={"query": {"match_all": {}}}
        )["hits"]["hits"]
        search2 = [x["_source"] for x in search2]
        self.assertEqual(len(search), len(search2))
        self.assertTrue(len(search) != 0)
        self.assertTrue(all(x in search for x in search2) and
                        all(y in search2 for y in search))

    def test_search(self):
        """Query ElasticSearch for docs in a timestamp range.

        We use API and DocManager's search(start_ts,end_ts), and then compare.
        """

        docc = {'_id': '1', 'name': 'John', '_ts': 5767301236327972865,
                'ns': 'test.test'}
        self.elastic_doc.upsert(docc)
        docc2 = {'_id': '2', 'name': 'John Paul', '_ts': 5767301236327972866,
                 'ns': 'test.test'}
        self.elastic_doc.upsert(docc2)
        docc3 = {'_id': '3', 'name': 'Paul', '_ts': 5767301236327972870,
                 'ns': 'test.test'}
        self.elastic_doc.upsert(docc3)
        search = list(self.elastic_doc.search(5767301236327972865,
                                              5767301236327972866))
        self.assertEqual(len(search), 2)
        result_names = [result.get("name") for result in search]
        self.assertIn('John', result_names)
        self.assertIn('John Paul', result_names)

    def test_elastic_commit(self):
        """Test that documents get properly added to ElasticSearch.
        """

        docc = {'_id': '3', 'name': 'Waldo', 'ns': 'test.test'}
        docman = DocManager(elastic_pair)
        # test cases:
        # -1 = no autocommit
        # 0 = commit immediately
        # x > 0 = commit within x seconds
        for autocommit_interval in [None, 0, 1, 2]:
            docman.auto_commit_interval = autocommit_interval
            docman.upsert(docc)
            if autocommit_interval is None:
                docman.commit()
            else:
                # Allow just a little extra time
                time.sleep(autocommit_interval + 1)
            results = list(self._search())
            self.assertEqual(len(results), 1,
                             "should commit document with "
                             "auto_commit_interval = %s" % str(
                                 autocommit_interval))
            self.assertEqual(results[0]["name"], "Waldo")
            self._remove()
        docman.stop()

    def test_get_last_doc(self):
        """Insert documents, verify that get_last_doc() returns the one with
            the latest timestamp.
        """
        base = self.elastic_doc.get_last_doc()
        ts = base.get("_ts", 0) if base else 0
        docc = {'_id': '4', 'name': 'Hare', '_ts': ts+3, 'ns': 'test.test'}
        self.elastic_doc.upsert(docc)
        docc = {'_id': '5', 'name': 'Tortoise', '_ts': ts+2, 'ns': 'test.test'}
        self.elastic_doc.upsert(docc)
        docc = {'_id': '6', 'name': 'Mr T.', '_ts': ts+1, 'ns': 'test.test'}
        self.elastic_doc.upsert(docc)

        self.assertEqual(
            self.elastic_doc.elastic.count(index="test.test")['count'], 3)
        doc = self.elastic_doc.get_last_doc()
        self.assertEqual(doc['_id'], '4')

        docc = {'_id': '6', 'name': 'HareTwin', '_ts': ts+4, 'ns': 'test.test'}
        self.elastic_doc.upsert(docc)
        doc = self.elastic_doc.get_last_doc()
        self.assertEqual(doc['_id'], '6')
        self.assertEqual(
            self.elastic_doc.elastic.count(index="test.test")['count'], 3)

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_mongo
# Copyright 2013-2014 MongoDB, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Test mongo using the synchronizer, i.e. as it would be used by an
    user
"""
import time
import os
import sys
if sys.version_info[:2] == (2, 6):
    import unittest2 as unittest
else:
    import unittest

sys.path[0:0] = [""]

from pymongo import MongoClient
from tests import mongo_host, STRESS_COUNT
from tests.setup_cluster import (start_replica_set,
                                 kill_replica_set,
                                 start_mongo_proc,
                                 restart_mongo_proc,
                                 kill_mongo_proc)
from mongo_connector.doc_managers.mongo_doc_manager import DocManager
from mongo_connector.connector import Connector
from mongo_connector.util import retry_until_ok
from pymongo.errors import OperationFailure, AutoReconnect
from tests.util import assert_soon


class TestSynchronizer(unittest.TestCase):
    """ Tests the mongo instance
    """

    @classmethod
    def setUpClass(cls):
        try:
            os.unlink("config.txt")
        except OSError:
            pass
        open("config.txt", "w").close()
        cls.standalone_port = start_mongo_proc(options=['--nojournal',
                                                        '--noprealloc'])
        cls.mongo_doc = DocManager('%s:%d' % (mongo_host, cls.standalone_port))
        cls.mongo_doc._remove()
        _, cls.secondary_p, cls.primary_p = start_replica_set('test-mongo')
        cls.conn = MongoClient(mongo_host, cls.primary_p,
                               replicaSet='test-mongo')

    @classmethod
    def tearDownClass(cls):
        """ Kills cluster instance
        """
        kill_mongo_proc(cls.standalone_port)
        kill_replica_set('test-mongo')

    def tearDown(self):
        self.connector.join()

    def setUp(self):
        self.connector = Connector(
            address='%s:%s' % (mongo_host, self.primary_p),
            oplog_checkpoint="config.txt",
            target_url='%s:%d' % (mongo_host, self.standalone_port),
            ns_set=['test.test'],
            u_key='_id',
            auth_key=None,
            doc_manager='mongo_connector/doc_managers/mongo_doc_manager.py'
        )
        self.connector.start()
        assert_soon(lambda: len(self.connector.shard_set) > 0)
        self.conn['test']['test'].remove()
        assert_soon(lambda: sum(1 for _ in self.mongo_doc._search()) == 0)

    def test_shard_length(self):
        """Tests the shard_length to see if the shard set was recognized
            properly
        """

        self.assertEqual(len(self.connector.shard_set), 1)

    def test_insert(self):
        """Tests insert
        """

        self.conn['test']['test'].insert({'name': 'paulie'})
        assert_soon(lambda: sum(1 for _ in self.mongo_doc._search()) == 1)
        result_set_1 = self.mongo_doc._search()
        self.assertEqual(sum(1 for _ in result_set_1), 1)
        result_set_2 = self.conn['test']['test'].find_one()
        for item in result_set_1:
            self.assertEqual(item['_id'], result_set_2['_id'])
            self.assertEqual(item['name'], result_set_2['name'])

    def test_remove(self):
        """Tests remove
        """

        self.conn['test']['test'].insert({'name': 'paulie'})
        assert_soon(lambda: sum(1 for _ in self.mongo_doc._search()) == 1)
        self.conn['test']['test'].remove({'name': 'paulie'})
        assert_soon(lambda: sum(1 for _ in self.mongo_doc._search()) != 1)
        self.assertEqual(sum(1 for _ in self.mongo_doc._search()), 0)

    def test_rollback(self):
        """Tests rollback. We force a rollback by adding a doc, killing the
            primary, adding another doc, killing the new primary, and then
            restarting both.
        """
        primary_conn = MongoClient(mongo_host, self.primary_p)
        self.conn['test']['test'].insert({'name': 'paul'})
        condition = lambda: self.conn['test']['test'].find_one(
            {'name': 'paul'}) is not None
        assert_soon(condition)
        assert_soon(lambda: sum(1 for _ in self.mongo_doc._search()) == 1)

        kill_mongo_proc(self.primary_p, destroy=False)
        new_primary_conn = MongoClient(mongo_host, self.secondary_p)
        admin = new_primary_conn['admin']
        condition = lambda: admin.command("isMaster")['ismaster']
        assert_soon(lambda: retry_until_ok(condition))

        retry_until_ok(self.conn.test.test.insert,
                       {'name': 'pauline'})
        assert_soon(lambda: sum(1 for _ in self.mongo_doc._search()) == 2)
        result_set_1 = list(self.mongo_doc._search())
        result_set_2 = self.conn['test']['test'].find_one({'name': 'pauline'})
        self.assertEqual(len(result_set_1), 2)
        #make sure pauline is there
        for item in result_set_1:
            if item['name'] == 'pauline':
                self.assertEqual(item['_id'], result_set_2['_id'])
        kill_mongo_proc(self.secondary_p, destroy=False)

        restart_mongo_proc(self.primary_p)
        assert_soon(
            lambda: primary_conn['admin'].command("isMaster")['ismaster'])

        restart_mongo_proc(self.secondary_p)

        time.sleep(2)
        result_set_1 = list(self.mongo_doc._search())
        self.assertEqual(len(result_set_1), 1)
        for item in result_set_1:
            self.assertEqual(item['name'], 'paul')
        find_cursor = retry_until_ok(self.conn['test']['test'].find)
        self.assertEqual(retry_until_ok(find_cursor.count), 1)

    def test_stress(self):
        """Test stress by inserting and removing the number of documents
            specified in global
            variable
        """

        for i in range(0, STRESS_COUNT):
            self.conn['test']['test'].insert({'name': 'Paul ' + str(i)})
        time.sleep(5)
        search = self.mongo_doc._search
        condition = lambda: sum(1 for _ in search()) == STRESS_COUNT
        assert_soon(condition)
        for i in range(0, STRESS_COUNT):
            result_set_1 = self.mongo_doc._search()
            for item in result_set_1:
                if(item['name'] == 'Paul' + str(i)):
                    self.assertEqual(item['_id'], item['_id'])

    def test_stressed_rollback(self):
        """Test stressed rollback with number of documents equal to specified
            in global variable. Strategy for rollback is the same as before.
        """

        for i in range(0, STRESS_COUNT):
            self.conn['test']['test'].insert({'name': 'Paul ' + str(i)})

        search = self.mongo_doc._search
        condition = lambda: sum(1 for _ in search()) == STRESS_COUNT
        assert_soon(condition)
        primary_conn = MongoClient(mongo_host, self.primary_p)

        kill_mongo_proc(self.primary_p, destroy=False)

        new_primary_conn = MongoClient(mongo_host, self.secondary_p)

        admin = new_primary_conn['admin']
        assert_soon(lambda: admin.command("isMaster")['ismaster'])

        time.sleep(5)
        count = -1
        while count + 1 < STRESS_COUNT:
            try:
                count += 1
                self.conn['test']['test'].insert(
                    {'name': 'Pauline ' + str(count)})
            except (OperationFailure, AutoReconnect):
                time.sleep(1)
        assert_soon(lambda: sum(1 for _ in self.mongo_doc._search())
                    == self.conn['test']['test'].find().count())
        result_set_1 = self.mongo_doc._search()
        for item in result_set_1:
            if 'Pauline' in item['name']:
                result_set_2 = self.conn['test']['test'].find_one(
                    {'name': item['name']})
                self.assertEqual(item['_id'], result_set_2['_id'])

        kill_mongo_proc(self.secondary_p, destroy=False)

        restart_mongo_proc(self.primary_p)
        db_admin = primary_conn['admin']
        assert_soon(lambda: db_admin.command("isMaster")['ismaster'])
        restart_mongo_proc(self.secondary_p)

        search = self.mongo_doc._search
        condition = lambda: sum(1 for _ in search()) == STRESS_COUNT
        assert_soon(condition)

        result_set_1 = list(self.mongo_doc._search())
        self.assertEqual(len(result_set_1), STRESS_COUNT)
        for item in result_set_1:
            self.assertTrue('Paul' in item['name'])
        find_cursor = retry_until_ok(self.conn['test']['test'].find)
        self.assertEqual(retry_until_ok(find_cursor.count), STRESS_COUNT)


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_mongo_connector
# Copyright 2013-2014 MongoDB, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Tests methods for mongo_connector
"""

import os
import sys

sys.path[0:0] = [""]


if sys.version_info[:2] == (2, 6):
    import unittest2 as unittest
else:
    import unittest
import time
import json

from mongo_connector.connector import Connector
from tests import mongo_host
from tests.setup_cluster import start_replica_set, kill_replica_set
from bson.timestamp import Timestamp
from mongo_connector import errors
from mongo_connector.doc_managers import (
    doc_manager_simulator
)
from mongo_connector.util import long_to_bson_ts


class TestMongoConnector(unittest.TestCase):
    """ Test Class for the Mongo Connector
    """

    @classmethod
    def setUpClass(cls):
        """ Initializes the cluster
        """
        try:
            os.unlink("config.txt")
        except OSError:
            pass
        open("config.txt", "w").close()
        _, _, cls.primary_p = start_replica_set('test-mongo-connector')

    @classmethod
    def tearDownClass(cls):
        """ Kills cluster instance
        """
        kill_replica_set('test-mongo-connector')

    def test_connector(self):
        """Test whether the connector initiates properly
        """
        conn = Connector(
            address='%s:%d' % (mongo_host, self.primary_p),
            oplog_checkpoint='config.txt',
            target_url=None,
            ns_set=['test.test'],
            u_key='_id',
            auth_key=None
        )
        conn.start()

        while len(conn.shard_set) != 1:
            time.sleep(2)
        conn.join()

        self.assertFalse(conn.can_run)
        time.sleep(5)
        for thread in conn.shard_set.values():
            self.assertFalse(thread.running)

    def test_write_oplog_progress(self):
        """Test write_oplog_progress under several circumstances
        """
        try:
            os.unlink("temp_config.txt")
        except OSError:
            pass
        open("temp_config.txt", "w").close()
        conn = Connector(
            address='%s:%d' % (mongo_host, self.primary_p),
            oplog_checkpoint="temp_config.txt",
            target_url=None,
            ns_set=['test.test'],
            u_key='_id',
            auth_key=None
        )

        #test that None is returned if there is no config file specified.
        self.assertEqual(conn.write_oplog_progress(), None)

        conn.oplog_progress.get_dict()[1] = Timestamp(12, 34)
        #pretend to insert a thread/timestamp pair
        conn.write_oplog_progress()

        data = json.load(open("temp_config.txt", 'r'))
        self.assertEqual(1, int(data[0]))
        self.assertEqual(long_to_bson_ts(int(data[1])), Timestamp(12, 34))

        #ensure the temp file was deleted
        self.assertFalse(os.path.exists("temp_config.txt" + '~'))

        #ensure that updates work properly
        conn.oplog_progress.get_dict()[1] = Timestamp(44, 22)
        conn.write_oplog_progress()

        config_file = open("temp_config.txt", 'r')
        data = json.load(config_file)
        self.assertEqual(1, int(data[0]))
        self.assertEqual(long_to_bson_ts(int(data[1])), Timestamp(44, 22))

        config_file.close()
        os.unlink("temp_config.txt")

    def test_read_oplog_progress(self):
        """Test read_oplog_progress
        """

        conn = Connector(
            address='%s:%d' % (mongo_host, self.primary_p),
            oplog_checkpoint=None,
            target_url=None,
            ns_set=['test.test'],
            u_key='_id',
            auth_key=None
        )

        #testing with no file
        self.assertEqual(conn.read_oplog_progress(), None)

        try:
            os.unlink("temp_config.txt")
        except OSError:
            pass
        open("temp_config.txt", "w").close()

        conn.oplog_checkpoint = "temp_config.txt"

        #testing with empty file
        self.assertEqual(conn.read_oplog_progress(), None)

        oplog_dict = conn.oplog_progress.get_dict()

        #add a value to the file, delete the dict, and then read in the value
        oplog_dict['oplog1'] = Timestamp(12, 34)
        conn.write_oplog_progress()
        del oplog_dict['oplog1']

        self.assertEqual(len(oplog_dict), 0)

        conn.read_oplog_progress()

        self.assertTrue('oplog1' in oplog_dict.keys())
        self.assertTrue(oplog_dict['oplog1'], Timestamp(12, 34))

        oplog_dict['oplog1'] = Timestamp(55, 11)

        #see if oplog progress dict is properly updated
        conn.read_oplog_progress()
        self.assertTrue(oplog_dict['oplog1'], Timestamp(55, 11))

        os.unlink("temp_config.txt")

    def test_many_targets(self):
        """Test that DocManagers are created and assigned to target URLs
        correctly when instantiating a Connector object with multiple target
        URLs
        """

        # no doc manager or target URLs
        connector_kwargs = {
            "address": '%s:%d' % (mongo_host, self.primary_p),
            "oplog_checkpoint": None,
            "ns_set": None,
            "u_key": None,
            "auth_key": None
        }
        c = Connector(target_url=None, **connector_kwargs)
        self.assertEqual(len(c.doc_managers), 1)
        self.assertIsInstance(c.doc_managers[0],
                              doc_manager_simulator.DocManager)

        # N.B. This assumes we're in mongo-connector/tests
        def get_docman(name):
            return os.path.join(
                os.path.dirname(os.path.abspath(__file__)),
                os.pardir,
                "mongo_connector",
                "doc_managers",
                "%s.py" % name
            )

        # only target URL provided
        with self.assertRaises(errors.ConnectorError):
            Connector(target_url="localhost:9200", **connector_kwargs)

        # one doc manager taking a target URL, no URL provided
        with self.assertRaises(TypeError):
            c = Connector(doc_manager=get_docman("mongo_doc_manager"),
                          **connector_kwargs)

        # 1:1 target URLs and doc managers
        c = Connector(
            doc_manager=[
                get_docman("elastic_doc_manager"),
                get_docman("doc_manager_simulator"),
                get_docman("elastic_doc_manager")
            ],
            target_url=[
                '%s:%d' % (mongo_host, self.primary_p),
                "foobar",
                "bazbaz"
            ],
            **connector_kwargs
        )
        self.assertEqual(len(c.doc_managers), 3)
        # Connector uses doc manager filename as module name
        self.assertEqual(c.doc_managers[0].__module__,
                         "elastic_doc_manager")
        self.assertEqual(c.doc_managers[1].__module__,
                         "doc_manager_simulator")
        self.assertEqual(c.doc_managers[2].__module__,
                         "elastic_doc_manager")

        # more target URLs than doc managers
        c = Connector(
            doc_manager=[
                get_docman("doc_manager_simulator")
            ],
            target_url=[
                '%s:%d' % (mongo_host, self.primary_p),
                "foobar",
                "bazbaz"
            ],
            **connector_kwargs
        )
        self.assertEqual(len(c.doc_managers), 3)
        self.assertEqual(c.doc_managers[0].__module__,
                         "doc_manager_simulator")
        self.assertEqual(c.doc_managers[1].__module__,
                         "doc_manager_simulator")
        self.assertEqual(c.doc_managers[2].__module__,
                         "doc_manager_simulator")
        self.assertEqual(c.doc_managers[0].url,
                         '%s:%d' % (mongo_host, self.primary_p))
        self.assertEqual(c.doc_managers[1].url, "foobar")
        self.assertEqual(c.doc_managers[2].url, "bazbaz")

        # more doc managers than target URLs
        c = Connector(
            doc_manager=[
                get_docman("elastic_doc_manager"),
                get_docman("doc_manager_simulator"),
                get_docman("doc_manager_simulator")
            ],
            target_url=[
                '%s:%d' % (mongo_host, self.primary_p)
            ],
            **connector_kwargs
        )
        self.assertEqual(len(c.doc_managers), 3)
        self.assertEqual(c.doc_managers[0].__module__,
                         "elastic_doc_manager")
        self.assertEqual(c.doc_managers[1].__module__,
                         "doc_manager_simulator")
        self.assertEqual(c.doc_managers[2].__module__,
                         "doc_manager_simulator")
        # extra doc managers should have None as target URL
        self.assertEqual(c.doc_managers[1].url, None)
        self.assertEqual(c.doc_managers[2].url, None)

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_mongo_doc_manager
# Copyright 2013-2014 MongoDB, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Tests each of the functions in mongo_doc_manager
"""

import time
import sys
if sys.version_info[:2] == (2, 6):
    import unittest2 as unittest
else:
    import unittest

sys.path[0:0] = [""]

from mongo_connector.doc_managers.mongo_doc_manager import DocManager
from pymongo import MongoClient

from tests import mongo_host
from tests.setup_cluster import start_mongo_proc, kill_mongo_proc


class MongoDocManagerTester(unittest.TestCase):
    """Test class for MongoDocManager
    """

    @classmethod
    def setUpClass(cls):
        cls.standalone_port = start_mongo_proc(options=['--nojournal',
                                                        '--noprealloc'])
        cls.standalone_pair = '%s:%d' % (mongo_host, cls.standalone_port)
        cls.MongoDoc = DocManager(cls.standalone_pair)
        cls.mongo_conn = MongoClient(cls.standalone_pair)
        cls.mongo = cls.mongo_conn['test']['test']

        cls.namespaces_inc = ["test.test_include1", "test.test_include2"]
        cls.namespaces_exc = ["test.test_exclude1", "test.test_exclude2"]
        cls.choosy_docman = DocManager(
            cls.standalone_pair,
            namespace_set=MongoDocManagerTester.namespaces_inc
        )

    @classmethod
    def tearDownClass(cls):
        kill_mongo_proc(cls.standalone_port)

    def setUp(self):
        """Empty Mongo at the start of every test
        """

        self.mongo_conn.drop_database("__mongo_connector")
        self.mongo.remove()

        conn = MongoClient('%s:%d' % (mongo_host, self.standalone_port))
        for ns in self.namespaces_inc + self.namespaces_exc:
            db, coll = ns.split('.', 1)
            conn[db][coll].remove()

    def test_namespaces(self):
        """Ensure that a DocManager instantiated with a namespace set
        has the correct namespaces
        """

        self.assertEqual(set(self.namespaces_inc),
                         set(self.choosy_docman._namespaces()))

    def test_update(self):
        doc = {"_id": '1', "ns": "test.test", "_ts": 1,
               "a": 1, "b": 2}
        self.mongo.insert(doc)
        # $set only
        update_spec = {"$set": {"a": 1, "b": 2}}
        doc = self.choosy_docman.update(doc, update_spec)
        self.assertEqual(doc, {"_id": '1', "ns": "test.test", "_ts": 1,
                               "a": 1, "b": 2})
        # $unset only
        update_spec = {"$unset": {"a": True}}
        doc = self.choosy_docman.update(doc, update_spec)
        self.assertEqual(doc, {"_id": '1', "ns": "test.test", "_ts": 1,
                               "b": 2})
        # mixed $set/$unset
        update_spec = {"$unset": {"b": True}, "$set": {"c": 3}}
        doc = self.choosy_docman.update(doc, update_spec)
        self.assertEqual(doc, {"_id": '1', "ns": "test.test", "_ts": 1,
                               "c": 3})

    def test_upsert(self):
        """Ensure we can properly insert into Mongo via DocManager.
        """

        docc = {'_id': '1', 'name': 'John', 'ns': 'test.test',
                '_ts': 5767301236327972865}
        self.MongoDoc.upsert(docc)
        time.sleep(3)
        res = self.mongo.find()
        self.assertTrue(res.count() == 1)
        for doc in res:
            self.assertTrue(doc['_id'] == '1' and doc['name'] == 'John')

        docc = {'_id': '1', 'name': 'Paul', 'ns': 'test.test',
                '_ts': 5767301236327972865}
        self.MongoDoc.upsert(docc)
        time.sleep(1)
        res = self.mongo.find()
        self.assertTrue(res.count() == 1)
        for doc in res:
            self.assertTrue(doc['_id'] == '1' and doc['name'] == 'Paul')

    def test_remove(self):
        """Ensure we can properly delete from Mongo via DocManager.
        """

        docc = {'_id': '1', 'name': 'John', 'ns': 'test.test',
                '_ts': 5767301236327972865}
        self.MongoDoc.upsert(docc)
        time.sleep(3)
        res = self.mongo.find()
        self.assertTrue(res.count() == 1)
        if "ns" not in docc:
            docc["ns"] = 'test.test'

        self.MongoDoc.remove(docc)
        time.sleep(1)
        res = self.mongo.find()
        self.assertTrue(res.count() == 0)

    def test_full_search(self):
        """Query Mongo for all docs via API and via DocManager's
        _search(), compare.
        """

        docc = {'_id': '1', 'name': 'John', 'ns': 'test.test',
                '_ts': 5767301236327972865}
        self.MongoDoc.upsert(docc)
        docc = {'_id': '2', 'name': 'Paul', 'ns': 'test.test',
                '_ts': 5767301236327972865}
        self.MongoDoc.upsert(docc)
        self.MongoDoc.commit()
        search = list(self.MongoDoc._search())
        search2 = list(self.mongo.find())
        self.assertTrue(len(search) == len(search2))
        self.assertTrue(len(search) != 0)
        self.assertTrue(all(x in search for x in search2) and
                        all(y in search2 for y in search))

    def test_search(self):
        """Query Mongo for docs in a timestamp range.

        We use API and DocManager's search(start_ts,end_ts), and then compare.
        """

        docc = {'_id': '1', 'name': 'John', '_ts': 5767301236327972865,
                'ns': 'test.test'}
        self.MongoDoc.upsert(docc)
        docc2 = {'_id': '2', 'name': 'John Paul', '_ts': 5767301236327972866,
                 'ns': 'test.test'}
        self.MongoDoc.upsert(docc2)
        docc3 = {'_id': '3', 'name': 'Paul', '_ts': 5767301236327972870,
                 'ns': 'test.test'}
        self.MongoDoc.upsert(docc3)
        search = list(self.MongoDoc.search(5767301236327972865,
                                           5767301236327972866))
        self.assertTrue(len(search) == 2)
        result_id = [result.get("_id") for result in search]
        self.assertIn('1', result_id)
        self.assertIn('2', result_id)

    def test_search_namespaces(self):
        """Test search within timestamp range with a given namespace set
        """

        for ns in self.namespaces_inc + self.namespaces_exc:
            for i in range(100):
                self.choosy_docman.upsert({"_id": i, "ns": ns, "_ts": i})

        results = list(self.choosy_docman.search(0, 49))
        self.assertEqual(len(results), 100)
        for r in results:
            self.assertIn(r["ns"], self.namespaces_inc)

    def test_get_last_doc(self):
        """Insert documents, verify that get_last_doc() returns the one with
            the latest timestamp.
        """
        docc = {'_id': '4', 'name': 'Hare', '_ts': 3, 'ns': 'test.test'}
        self.MongoDoc.upsert(docc)
        docc = {'_id': '5', 'name': 'Tortoise', '_ts': 2, 'ns': 'test.test'}
        self.MongoDoc.upsert(docc)
        docc = {'_id': '6', 'name': 'Mr T.', '_ts': 1, 'ns': 'test.test'}
        self.MongoDoc.upsert(docc)
        time.sleep(1)
        doc = self.MongoDoc.get_last_doc()
        self.assertTrue(doc['_id'] == '4')
        docc = {'_id': '6', 'name': 'HareTwin', '_ts': 4, 'ns': 'test.test'}
        self.MongoDoc.upsert(docc)
        time.sleep(3)
        doc = self.MongoDoc.get_last_doc()
        self.assertTrue(doc['_id'] == '6')

    def test_get_last_doc_namespaces(self):
        """Ensure that get_last_doc returns the latest document in one of
        the given namespaces
        """

        # latest document is not in included namespace
        for i in range(100):
            ns = (self.namespaces_inc, self.namespaces_exc)[i % 2][0]
            self.choosy_docman.upsert({
                "_id": i,
                "ns": ns,
                "_ts": i
            })
        last_doc = self.choosy_docman.get_last_doc()
        self.assertEqual(last_doc["ns"], self.namespaces_inc[0])
        self.assertEqual(last_doc["_id"], 98)

        # remove latest document so last doc is in included namespace,
        # shouldn't change result
        db, coll = self.namespaces_inc[0].split(".", 1)
        MongoClient(self.standalone_pair)[db][coll].remove({"_id": 99})
        last_doc = self.choosy_docman.get_last_doc()
        self.assertEqual(last_doc["ns"], self.namespaces_inc[0])
        self.assertEqual(last_doc["_id"], 98)

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_oplog_manager
# Copyright 2013-2014 MongoDB, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Test oplog manager methods
"""

import time
import sys
if sys.version_info[:2] == (2, 6):
    import unittest2 as unittest
else:
    import unittest

import bson
import pymongo

from mongo_connector.doc_managers.doc_manager_simulator import DocManager
from mongo_connector.locking_dict import LockingDict
from mongo_connector.oplog_manager import OplogThread
from tests import mongo_host
from tests.setup_cluster import (start_replica_set,
                                 kill_replica_set)
from tests.util import assert_soon


class TestOplogManager(unittest.TestCase):
    """Defines all the testing methods, as well as a method that sets up the
        cluster
    """

    def setUp(self):
        _, _, self.primary_p = start_replica_set('test-oplog-manager')
        self.primary_conn = pymongo.MongoClient(mongo_host, self.primary_p)
        self.oplog_coll = self.primary_conn.local['oplog.rs']
        self.opman = OplogThread(
            primary_conn=self.primary_conn,
            main_address='%s:%d' % (mongo_host, self.primary_p),
            oplog_coll=self.oplog_coll,
            is_sharded=False,
            doc_manager=DocManager(),
            oplog_progress_dict=LockingDict(),
            namespace_set=None,
            auth_key=None,
            auth_username=None,
            repl_set='test-oplog-manager'
        )

    def tearDown(self):
        try:
            self.opman.join()
        except RuntimeError:
            pass                # OplogThread may not have been started
        self.primary_conn.close()
        kill_replica_set('test-oplog-manager')

    def test_get_oplog_cursor(self):
        '''Test the get_oplog_cursor method'''

        # Trivial case: timestamp is None
        self.assertEqual(self.opman.get_oplog_cursor(None), None)

        # earliest entry is after given timestamp
        doc = {"ts": bson.Timestamp(1000, 0), "i": 1}
        self.primary_conn["test"]["test"].insert(doc)
        self.assertEqual(self.opman.get_oplog_cursor(
            bson.Timestamp(1, 0)), None)

        # earliest entry is the only one at/after timestamp
        latest_timestamp = self.opman.get_last_oplog_timestamp()
        cursor = self.opman.get_oplog_cursor(latest_timestamp)
        self.assertNotEqual(cursor, None)
        self.assertEqual(cursor.count(), 1)
        next_entry_id = next(cursor)['o']['_id']
        retrieved = self.primary_conn.test.test.find_one(next_entry_id)
        self.assertEqual(retrieved, doc)

        # many entries before and after timestamp
        self.primary_conn["test"]["test"].insert(
            {"i": i} for i in range(2, 1002))
        oplog_cursor = self.oplog_coll.find(
            sort=[("ts", pymongo.ASCENDING)]
        )

        # startup + insert + 1000 inserts
        self.assertEqual(oplog_cursor.count(), 2 + 1000)
        pivot = oplog_cursor.skip(400).limit(1)[0]

        goc_cursor = self.opman.get_oplog_cursor(pivot["ts"])
        self.assertEqual(goc_cursor.count(), 2 + 1000 - 400)

        # get_oplog_cursor fast-forwards *one doc beyond* the given timestamp
        doc = self.primary_conn["test"]["test"].find_one(
            {"_id": next(goc_cursor)["o"]["_id"]})
        retrieved = self.primary_conn.test.test.find_one(pivot['o']['_id'])
        self.assertEqual(doc["i"], retrieved["i"] + 1)

    def test_get_last_oplog_timestamp(self):
        """Test the get_last_oplog_timestamp method"""

        # "empty" the oplog
        self.opman.oplog = self.primary_conn["test"]["emptycollection"]
        self.assertEqual(self.opman.get_last_oplog_timestamp(), None)

        # Test non-empty oplog
        self.opman.oplog = self.primary_conn["local"]["oplog.rs"]
        for i in range(1000):
            self.primary_conn["test"]["test"].insert({
                "i": i + 500
            })
        oplog = self.primary_conn["local"]["oplog.rs"]
        oplog = oplog.find().sort("$natural", pymongo.DESCENDING).limit(1)[0]
        self.assertEqual(self.opman.get_last_oplog_timestamp(),
                         oplog["ts"])

    def test_dump_collection(self):
        """Test the dump_collection method

        Cases:

        1. empty oplog
        2. non-empty oplog
        """

        # Test with empty oplog
        self.opman.oplog = self.primary_conn["test"]["emptycollection"]
        last_ts = self.opman.dump_collection()
        self.assertEqual(last_ts, None)

        # Test with non-empty oplog
        self.opman.oplog = self.primary_conn["local"]["oplog.rs"]
        for i in range(1000):
            self.primary_conn["test"]["test"].insert({
                "i": i + 500
            })
        last_ts = self.opman.get_last_oplog_timestamp()
        self.assertEqual(last_ts, self.opman.dump_collection())
        self.assertEqual(len(self.opman.doc_managers[0]._search()), 1000)

    def test_init_cursor(self):
        """Test the init_cursor method

        Cases:

        1. no last checkpoint, no collection dump
        2. no last checkpoint, collection dump ok and stuff to dump
        3. no last checkpoint, nothing to dump, stuff in oplog
        4. no last checkpoint, nothing to dump, nothing in oplog
        5. last checkpoint exists
        """

        # N.B. these sub-cases build off of each other and cannot be re-ordered
        # without side-effects

        # No last checkpoint, no collection dump, nothing in oplog
        # "change oplog collection" to put nothing in oplog
        self.opman.oplog = self.primary_conn["test"]["emptycollection"]
        self.opman.collection_dump = False
        self.assertEqual(self.opman.init_cursor(), None)
        self.assertEqual(self.opman.checkpoint, None)

        # No last checkpoint, empty collections, nothing in oplog
        self.opman.collection_dump = True
        self.assertEqual(self.opman.init_cursor(), None)
        self.assertEqual(self.opman.checkpoint, None)

        # No last checkpoint, empty collections, something in oplog
        self.opman.oplog = self.primary_conn['local']['oplog.rs']
        collection = self.primary_conn["test"]["test"]
        collection.insert({"i": 1})
        collection.remove({"i": 1})
        time.sleep(3)
        last_ts = self.opman.get_last_oplog_timestamp()
        self.assertEqual(next(self.opman.init_cursor())["ts"], last_ts)
        self.assertEqual(self.opman.checkpoint, last_ts)
        with self.opman.oplog_progress as prog:
            self.assertEqual(prog.get_dict()[str(self.opman.oplog)], last_ts)

        # No last checkpoint, non-empty collections, stuff in oplog
        self.opman.oplog_progress = LockingDict()
        self.assertEqual(next(self.opman.init_cursor())["ts"], last_ts)
        self.assertEqual(self.opman.checkpoint, last_ts)
        with self.opman.oplog_progress as prog:
            self.assertEqual(prog.get_dict()[str(self.opman.oplog)], last_ts)

        # Last checkpoint exists
        progress = LockingDict()
        self.opman.oplog_progress = progress
        for i in range(1000):
            collection.insert({"i": i + 500})
        entry = list(
            self.primary_conn["local"]["oplog.rs"].find(skip=200, limit=2))
        progress.get_dict()[str(self.opman.oplog)] = entry[0]["ts"]
        self.opman.oplog_progress = progress
        self.opman.checkpoint = None
        cursor = self.opman.init_cursor()
        self.assertEqual(entry[1]["ts"], next(cursor)["ts"])
        self.assertEqual(self.opman.checkpoint, entry[0]["ts"])
        with self.opman.oplog_progress as prog:
            self.assertEqual(prog.get_dict()[str(self.opman.oplog)],
                             entry[0]["ts"])

    def test_filter_fields(self):
        docman = self.opman.doc_managers[0]
        conn = self.opman.main_connection

        include_fields = ["a", "b", "c"]
        exclude_fields = ["d", "e", "f"]

        # Set fields to care about
        self.opman.fields = include_fields
        # Documents have more than just these fields
        doc = {
            "a": 1, "b": 2, "c": 3,
            "d": 4, "e": 5, "f": 6,
            "_id": 1
        }
        db = conn['test']['test']
        db.insert(doc)
        assert_soon(lambda: db.count() == 1)
        self.opman.dump_collection()

        result = docman._search()[0]
        keys = result.keys()
        for inc, exc in zip(include_fields, exclude_fields):
            self.assertIn(inc, keys)
            self.assertNotIn(exc, keys)

    def test_namespace_mapping(self):
        """Test mapping of namespaces
        Cases:

        upsert/delete/update of documents:
        1. in namespace set, mapping provided
        2. outside of namespace set, mapping provided
        """

        source_ns = ["test.test1", "test.test2"]
        phony_ns = ["test.phony1", "test.phony2"]
        dest_mapping = {"test.test1": "test.test1_dest",
                        "test.test2": "test.test2_dest"}
        self.opman.dest_mapping = dest_mapping
        self.opman.namespace_set = source_ns
        docman = self.opman.doc_managers[0]
        # start replicating
        self.opman.start()

        base_doc = {"_id": 1, "name": "superman"}

        # doc in namespace set
        for ns in source_ns:
            db, coll = ns.split(".", 1)

            # test insert
            self.primary_conn[db][coll].insert(base_doc)

            assert_soon(lambda: len(docman._search()) == 1)
            self.assertEqual(docman._search()[0]["ns"], dest_mapping[ns])
            bad = [d for d in docman._search() if d["ns"] == ns]
            self.assertEqual(len(bad), 0)

            # test update
            self.primary_conn[db][coll].update(
                {"_id": 1},
                {"$set": {"weakness": "kryptonite"}}
            )

            def update_complete():
                docs = docman._search()
                for d in docs:
                    if d.get("weakness") == "kryptonite":
                        return True
                    return False
            assert_soon(update_complete)
            self.assertEqual(docman._search()[0]["ns"], dest_mapping[ns])
            bad = [d for d in docman._search() if d["ns"] == ns]
            self.assertEqual(len(bad), 0)

            # test delete
            self.primary_conn[db][coll].remove({"_id": 1})
            assert_soon(lambda: len(docman._search()) == 0)
            bad = [d for d in docman._search()
                   if d["ns"] == dest_mapping[ns]]
            self.assertEqual(len(bad), 0)

            # cleanup
            self.primary_conn[db][coll].remove()
            self.opman.doc_managers[0]._delete()

        # doc not in namespace set
        for ns in phony_ns:
            db, coll = ns.split(".", 1)

            # test insert
            self.primary_conn[db][coll].insert(base_doc)
            time.sleep(1)
            self.assertEqual(len(docman._search()), 0)
            # test update
            self.primary_conn[db][coll].update(
                {"_id": 1},
                {"$set": {"weakness": "kryptonite"}}
            )
            time.sleep(1)
            self.assertEqual(len(docman._search()), 0)

    def test_many_targets(self):
        """Test that one OplogThread is capable of replicating to more than
        one target.
        """
        doc_managers = [DocManager(), DocManager(), DocManager()]
        self.opman.doc_managers = doc_managers

        # start replicating
        self.opman.start()
        self.primary_conn["test"]["test"].insert({
            "name": "kermit",
            "color": "green"
        })
        self.primary_conn["test"]["test"].insert({
            "name": "elmo",
            "color": "firetruck red"
        })

        assert_soon(
            lambda: sum(len(d._search()) for d in doc_managers) == 6,
            "OplogThread should be able to replicate to multiple targets"
        )

        self.primary_conn["test"]["test"].remove({"name": "elmo"})

        assert_soon(
            lambda: sum(len(d._search()) for d in doc_managers) == 3,
            "OplogThread should be able to replicate to multiple targets"
        )
        for d in doc_managers:
            self.assertEqual(d._search()[0]["name"], "kermit")

    def test_filter_oplog_entry(self):
        # Test oplog entries: these are callables, since
        # filter_oplog_entry modifies the oplog entry in-place
        insert_op = lambda: {
            "op": "i",
            "o": {
                "_id": 0,
                "a": 1,
                "b": 2,
                "c": 3
            }
        }
        update_op = lambda: {
            "op": "u",
            "o": {
                "$set": {
                    "a": 4,
                    "b": 5
                },
                "$unset": {
                    "c": True
                }
            },
            "o2": {
                "_id": 1
            }
        }

        # Case 0: insert op, no fields provided
        self.opman.fields = None
        filtered = self.opman.filter_oplog_entry(insert_op())
        self.assertEqual(filtered, insert_op())

        # Case 1: insert op, fields provided
        self.opman.fields = ['a', 'b']
        filtered = self.opman.filter_oplog_entry(insert_op())
        self.assertEqual(filtered['o'], {'_id': 0, 'a': 1, 'b': 2})

        # Case 2: insert op, fields provided, doc becomes empty except for _id
        self.opman.fields = ['d', 'e', 'f']
        filtered = self.opman.filter_oplog_entry(insert_op())
        self.assertEqual(filtered['o'], {'_id': 0})

        # Case 3: update op, no fields provided
        self.opman.fields = None
        filtered = self.opman.filter_oplog_entry(update_op())
        self.assertEqual(filtered, update_op())

        # Case 4: update op, fields provided
        self.opman.fields = ['a', 'c']
        filtered = self.opman.filter_oplog_entry(update_op())
        self.assertNotIn('b', filtered['o']['$set'])
        self.assertIn('a', filtered['o']['$set'])
        self.assertEqual(filtered['o']['$unset'], update_op()['o']['$unset'])

        # Case 5: update op, fields provided, empty $set
        self.opman.fields = ['c']
        filtered = self.opman.filter_oplog_entry(update_op())
        self.assertNotIn('$set', filtered['o'])
        self.assertEqual(filtered['o']['$unset'], update_op()['o']['$unset'])

        # Case 6: update op, fields provided, empty $unset
        self.opman.fields = ['a', 'b']
        filtered = self.opman.filter_oplog_entry(update_op())
        self.assertNotIn('$unset', filtered['o'])
        self.assertEqual(filtered['o']['$set'], update_op()['o']['$set'])

        # Case 7: update op, fields provided, entry is nullified
        self.opman.fields = ['d', 'e', 'f']
        filtered = self.opman.filter_oplog_entry(update_op())
        self.assertEqual(filtered, None)

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_oplog_manager_sharded
# Copyright 2013-2014 MongoDB, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import threading
import time
import os
import sys
if sys.version_info[:2] == (2, 6):
    import unittest2 as unittest
else:
    import unittest

from pymongo import MongoClient
import bson
import pymongo
from pymongo.read_preferences import ReadPreference

from mongo_connector.doc_managers.doc_manager_simulator import DocManager
from mongo_connector.locking_dict import LockingDict
from mongo_connector.oplog_manager import OplogThread
from mongo_connector.util import retry_until_ok
from tests import mongo_host
from tests.setup_cluster import (
    kill_mongo_proc,
    restart_mongo_proc,
    start_cluster,
    get_shard,
    kill_all
)
from tests.util import assert_soon


class TestOplogManagerSharded(unittest.TestCase):
    """Defines all test cases for OplogThreads running on a sharded
    cluster
    """

    def setUp(self):
        """ Initialize the cluster:

        Clean out the databases used by the tests
        Make connections to mongos, mongods
        Create and shard test collections
        Create OplogThreads
        """
        # Start the cluster with a mongos on port 27217
        self.mongos_p = start_cluster()

        # Connection to mongos
        mongos_address = '%s:%d' % (mongo_host, self.mongos_p)
        self.mongos_conn = MongoClient(mongos_address)

        # Connections to the shards
        shard1_ports = get_shard(self.mongos_p, 0)
        shard2_ports = get_shard(self.mongos_p, 1)
        self.shard1_prim_p = shard1_ports['primary']
        self.shard1_scnd_p = shard1_ports['secondaries'][0]
        self.shard2_prim_p = shard2_ports['primary']
        self.shard2_scnd_p = shard2_ports['secondaries'][0]
        self.shard1_conn = MongoClient('%s:%d'
                                       % (mongo_host, self.shard1_prim_p),
                                       replicaSet="demo-set-0")
        self.shard2_conn = MongoClient('%s:%d'
                                       % (mongo_host, self.shard2_prim_p),
                                       replicaSet="demo-set-1")
        self.shard1_secondary_conn = MongoClient(
            '%s:%d' % (mongo_host, self.shard1_scnd_p),
            read_preference=ReadPreference.SECONDARY_PREFERRED
        )
        self.shard2_secondary_conn = MongoClient(
            '%s:%d' % (mongo_host, self.shard2_scnd_p),
            read_preference=ReadPreference.SECONDARY_PREFERRED
        )

        # Wipe any test data
        self.mongos_conn["test"]["mcsharded"].drop()

        # Create and shard the collection test.mcsharded on the "i" field
        self.mongos_conn["test"]["mcsharded"].ensure_index("i")
        self.mongos_conn.admin.command("enableSharding", "test")
        self.mongos_conn.admin.command("shardCollection",
                                       "test.mcsharded",
                                       key={"i": 1})

        # Pre-split the collection so that:
        # i < 1000            lives on shard1
        # i >= 1000           lives on shard2
        self.mongos_conn.admin.command(bson.SON([
            ("split", "test.mcsharded"),
            ("middle", {"i": 1000})
        ]))

        # disable the balancer
        self.mongos_conn.config.settings.update(
            {"_id": "balancer"},
            {"$set": {"stopped": True}},
            upsert=True
        )

        # Move chunks to their proper places
        try:
            self.mongos_conn["admin"].command(
                "moveChunk",
                "test.mcsharded",
                find={"i": 1},
                to="demo-set-0"
            )
        except pymongo.errors.OperationFailure:
            pass        # chunk may already be on the correct shard
        try:
            self.mongos_conn["admin"].command(
                "moveChunk",
                "test.mcsharded",
                find={"i": 1000},
                to="demo-set-1"
            )
        except pymongo.errors.OperationFailure:
            pass        # chunk may already be on the correct shard

        # Make sure chunks are distributed correctly
        self.mongos_conn["test"]["mcsharded"].insert({"i": 1})
        self.mongos_conn["test"]["mcsharded"].insert({"i": 1000})

        def chunks_moved():
            doc1 = self.shard1_conn.test.mcsharded.find_one()
            doc2 = self.shard2_conn.test.mcsharded.find_one()
            if None in (doc1, doc2):
                return False
            return doc1['i'] == 1 and doc2['i'] == 1000
        assert_soon(chunks_moved)
        self.mongos_conn.test.mcsharded.remove()

        # create a new oplog progress file
        try:
            os.unlink("config.txt")
        except OSError:
            pass
        open("config.txt", "w").close()

        # Oplog threads (oplog manager) for each shard
        doc_manager = DocManager()
        oplog_progress = LockingDict()
        self.opman1 = OplogThread(
            primary_conn=self.shard1_conn,
            main_address='%s:%d' % (mongo_host, self.mongos_p),
            oplog_coll=self.shard1_conn["local"]["oplog.rs"],
            is_sharded=True,
            doc_manager=doc_manager,
            oplog_progress_dict=oplog_progress,
            namespace_set=["test.mcsharded", "test.mcunsharded"],
            auth_key=None,
            auth_username=None
        )
        self.opman2 = OplogThread(
            primary_conn=self.shard2_conn,
            main_address='%s:%d' % (mongo_host, self.mongos_p),
            oplog_coll=self.shard2_conn["local"]["oplog.rs"],
            is_sharded=True,
            doc_manager=doc_manager,
            oplog_progress_dict=oplog_progress,
            namespace_set=["test.mcsharded", "test.mcunsharded"],
            auth_key=None,
            auth_username=None
        )

    def tearDown(self):
        try:
            self.opman1.join()
        except RuntimeError:
            pass                # thread may not have been started
        try:
            self.opman2.join()
        except RuntimeError:
            pass                # thread may not have been started
        self.mongos_conn.close()
        self.shard1_conn.close()
        self.shard2_conn.close()
        self.shard1_secondary_conn.close()
        self.shard2_secondary_conn.close()
        kill_all()

    def test_get_oplog_cursor(self):
        """Test the get_oplog_cursor method"""

        # Trivial case: timestamp is None
        self.assertEqual(self.opman1.get_oplog_cursor(None), None)

        # earliest entry is after given timestamp
        doc = {"ts": bson.Timestamp(1000, 0), "i": 1}
        self.mongos_conn["test"]["mcsharded"].insert(doc)
        self.assertEqual(self.opman1.get_oplog_cursor(
            bson.Timestamp(1, 0)), None)

        # earliest entry is the only one at/after timestamp
        latest_timestamp = self.opman1.get_last_oplog_timestamp()
        cursor = self.opman1.get_oplog_cursor(latest_timestamp)
        self.assertNotEqual(cursor, None)
        self.assertEqual(cursor.count(), 1)
        next_entry_id = cursor[0]['o']['_id']
        retrieved = self.mongos_conn.test.mcsharded.find_one(next_entry_id)
        self.assertEqual(retrieved, doc)

        # many entries before and after timestamp
        for i in range(2, 2002):
            self.mongos_conn["test"]["mcsharded"].insert({
                "i": i
            })
        oplog1 = self.shard1_conn["local"]["oplog.rs"].find(
            sort=[("ts", pymongo.ASCENDING)]
        )
        oplog2 = self.shard2_conn["local"]["oplog.rs"].find(
            sort=[("ts", pymongo.ASCENDING)]
        )

        # oplogs should have records for inserts performed, plus
        # various other messages
        oplog1_count = oplog1.count()
        oplog2_count = oplog2.count()
        self.assertGreaterEqual(oplog1_count, 998)
        self.assertGreaterEqual(oplog2_count, 1002)
        pivot1 = oplog1.skip(400).limit(1)[0]
        pivot2 = oplog2.skip(400).limit(1)[0]

        cursor1 = self.opman1.get_oplog_cursor(pivot1["ts"])
        cursor2 = self.opman2.get_oplog_cursor(pivot2["ts"])
        self.assertEqual(cursor1.count(), oplog1_count - 400)
        self.assertEqual(cursor2.count(), oplog2_count - 400)

        # get_oplog_cursor fast-forwards *one doc beyond* the given timestamp
        doc1 = self.mongos_conn["test"]["mcsharded"].find_one(
            {"_id": next(cursor1)["o"]["_id"]})
        doc2 = self.mongos_conn["test"]["mcsharded"].find_one(
            {"_id": next(cursor2)["o"]["_id"]})
        piv1id = pivot1['o']['_id']
        piv2id = pivot2['o']['_id']
        retrieved1 = self.mongos_conn.test.mcsharded.find_one(piv1id)
        retrieved2 = self.mongos_conn.test.mcsharded.find_one(piv2id)
        self.assertEqual(doc1["i"], retrieved1["i"] + 1)
        self.assertEqual(doc2["i"], retrieved2["i"] + 1)

    def test_get_last_oplog_timestamp(self):
        """Test the get_last_oplog_timestamp method"""

        # "empty" the oplog
        self.opman1.oplog = self.shard1_conn["test"]["emptycollection"]
        self.opman2.oplog = self.shard2_conn["test"]["emptycollection"]
        self.assertEqual(self.opman1.get_last_oplog_timestamp(), None)
        self.assertEqual(self.opman2.get_last_oplog_timestamp(), None)

        # Test non-empty oplog
        self.opman1.oplog = self.shard1_conn["local"]["oplog.rs"]
        self.opman2.oplog = self.shard2_conn["local"]["oplog.rs"]
        for i in range(1000):
            self.mongos_conn["test"]["mcsharded"].insert({
                "i": i + 500
            })
        oplog1 = self.shard1_conn["local"]["oplog.rs"]
        oplog1 = oplog1.find().sort("$natural", pymongo.DESCENDING).limit(1)[0]
        oplog2 = self.shard2_conn["local"]["oplog.rs"]
        oplog2 = oplog2.find().sort("$natural", pymongo.DESCENDING).limit(1)[0]
        self.assertEqual(self.opman1.get_last_oplog_timestamp(),
                         oplog1["ts"])
        self.assertEqual(self.opman2.get_last_oplog_timestamp(),
                         oplog2["ts"])

    def test_dump_collection(self):
        """Test the dump_collection method

        Cases:

        1. empty oplog
        2. non-empty oplog
        """

        # Test with empty oplog
        self.opman1.oplog = self.shard1_conn["test"]["emptycollection"]
        self.opman2.oplog = self.shard2_conn["test"]["emptycollection"]
        last_ts1 = self.opman1.dump_collection()
        last_ts2 = self.opman2.dump_collection()
        self.assertEqual(last_ts1, None)
        self.assertEqual(last_ts2, None)

        # Test with non-empty oplog
        self.opman1.oplog = self.shard1_conn["local"]["oplog.rs"]
        self.opman2.oplog = self.shard2_conn["local"]["oplog.rs"]
        for i in range(1000):
            self.mongos_conn["test"]["mcsharded"].insert({
                "i": i + 500
            })
        last_ts1 = self.opman1.get_last_oplog_timestamp()
        last_ts2 = self.opman2.get_last_oplog_timestamp()
        self.assertEqual(last_ts1, self.opman1.dump_collection())
        self.assertEqual(last_ts2, self.opman2.dump_collection())
        self.assertEqual(len(self.opman1.doc_managers[0]._search()), 1000)

    def test_init_cursor(self):
        """Test the init_cursor method

        Cases:

        1. no last checkpoint, no collection dump
        2. no last checkpoint, collection dump ok and stuff to dump
        3. no last checkpoint, nothing to dump, stuff in oplog
        4. no last checkpoint, nothing to dump, nothing in oplog
        5. last checkpoint exists
        """

        # N.B. these sub-cases build off of each other and cannot be re-ordered
        # without side-effects

        # No last checkpoint, no collection dump, nothing in oplog
        # "change oplog collection" to put nothing in oplog
        self.opman1.oplog = self.shard1_conn["test"]["emptycollection"]
        self.opman2.oplog = self.shard2_conn["test"]["emptycollection"]
        self.opman1.collection_dump = False
        self.opman2.collection_dump = False
        self.assertEqual(self.opman1.init_cursor(), None)
        self.assertEqual(self.opman1.checkpoint, None)
        self.assertEqual(self.opman2.init_cursor(), None)
        self.assertEqual(self.opman2.checkpoint, None)

        # No last checkpoint, empty collections, nothing in oplog
        self.opman1.collection_dump = True
        self.opman2.collection_dump = True
        self.assertEqual(self.opman1.init_cursor(), None)
        self.assertEqual(self.opman1.checkpoint, None)
        self.assertEqual(self.opman2.init_cursor(), None)
        self.assertEqual(self.opman2.checkpoint, None)

        # No last checkpoint, empty collections, something in oplog
        self.opman1.oplog = self.shard1_conn["local"]["oplog.rs"]
        self.opman2.oplog = self.shard2_conn["local"]["oplog.rs"]
        oplog_startup_ts = self.opman2.get_last_oplog_timestamp()
        collection = self.mongos_conn["test"]["mcsharded"]
        collection.insert({"i": 1})
        collection.remove({"i": 1})
        time.sleep(3)
        last_ts1 = self.opman1.get_last_oplog_timestamp()
        self.assertEqual(next(self.opman1.init_cursor())["ts"], last_ts1)
        self.assertEqual(self.opman1.checkpoint, last_ts1)
        with self.opman1.oplog_progress as prog:
            self.assertEqual(prog.get_dict()[str(self.opman1.oplog)], last_ts1)
        # init_cursor should point to startup message in shard2 oplog
        cursor = self.opman2.init_cursor()
        self.assertEqual(next(cursor)["ts"], oplog_startup_ts)
        self.assertEqual(self.opman2.checkpoint, oplog_startup_ts)

        # No last checkpoint, non-empty collections, stuff in oplog
        progress = LockingDict()
        self.opman1.oplog_progress = self.opman2.oplog_progress = progress
        collection.insert({"i": 1200})
        last_ts2 = self.opman2.get_last_oplog_timestamp()
        self.assertEqual(next(self.opman1.init_cursor())["ts"], last_ts1)
        self.assertEqual(self.opman1.checkpoint, last_ts1)
        with self.opman1.oplog_progress as prog:
            self.assertEqual(prog.get_dict()[str(self.opman1.oplog)], last_ts1)
        self.assertEqual(next(self.opman2.init_cursor())["ts"], last_ts2)
        self.assertEqual(self.opman2.checkpoint, last_ts2)
        with self.opman2.oplog_progress as prog:
            self.assertEqual(prog.get_dict()[str(self.opman2.oplog)], last_ts2)

        # Last checkpoint exists
        progress = LockingDict()
        self.opman1.oplog_progress = self.opman2.oplog_progress = progress
        for i in range(1000):
            collection.insert({"i": i + 500})
        entry1 = list(
            self.shard1_conn["local"]["oplog.rs"].find(skip=200, limit=2))
        entry2 = list(
            self.shard2_conn["local"]["oplog.rs"].find(skip=200, limit=2))
        progress.get_dict()[str(self.opman1.oplog)] = entry1[0]["ts"]
        progress.get_dict()[str(self.opman2.oplog)] = entry2[0]["ts"]
        self.opman1.oplog_progress = self.opman2.oplog_progress = progress
        self.opman1.checkpoint = self.opman2.checkpoint = None
        cursor1 = self.opman1.init_cursor()
        cursor2 = self.opman2.init_cursor()
        self.assertEqual(entry1[1]["ts"], next(cursor1)["ts"])
        self.assertEqual(entry2[1]["ts"], next(cursor2)["ts"])
        self.assertEqual(self.opman1.checkpoint, entry1[0]["ts"])
        self.assertEqual(self.opman2.checkpoint, entry2[0]["ts"])
        with self.opman1.oplog_progress as prog:
            self.assertEqual(prog.get_dict()[str(self.opman1.oplog)],
                             entry1[0]["ts"])
        with self.opman2.oplog_progress as prog:
            self.assertEqual(prog.get_dict()[str(self.opman2.oplog)],
                             entry2[0]["ts"])

    def test_rollback(self):
        """Test the rollback method in a sharded environment

        Cases:
        1. Documents on both shards, rollback on one shard
        2. Documents on both shards, rollback on both shards

        """

        self.opman1.start()
        self.opman2.start()

        # Insert first documents while primaries are up
        db_main = self.mongos_conn["test"]["mcsharded"]
        db_main.insert({"i": 0}, w=2)
        db_main.insert({"i": 1000}, w=2)
        self.assertEqual(self.shard1_conn["test"]["mcsharded"].count(), 1)
        self.assertEqual(self.shard2_conn["test"]["mcsharded"].count(), 1)

        # Case 1: only one primary goes down, shard1 in this case
        kill_mongo_proc(self.shard1_prim_p, destroy=False)

        # Wait for the secondary to be promoted
        shard1_secondary_admin = self.shard1_secondary_conn["admin"]
        assert_soon(
            lambda: shard1_secondary_admin.command("isMaster")["ismaster"])

        # Insert another document. This will be rolled back later
        retry_until_ok(db_main.insert, {"i": 1})
        db_secondary1 = self.shard1_secondary_conn["test"]["mcsharded"]
        db_secondary2 = self.shard2_secondary_conn["test"]["mcsharded"]
        self.assertEqual(db_secondary1.count(), 2)

        # Wait for replication on the doc manager
        # Note that both OplogThreads share the same doc manager
        c = lambda: len(self.opman1.doc_managers[0]._search()) == 3
        assert_soon(c, "not all writes were replicated to doc manager",
                    max_tries=120)

        # Kill the new primary
        kill_mongo_proc(self.shard1_scnd_p, destroy=False)

        # Start both servers back up
        restart_mongo_proc(self.shard1_prim_p)
        primary_admin = self.shard1_conn["admin"]
        c = lambda: primary_admin.command("isMaster")["ismaster"]
        assert_soon(lambda: retry_until_ok(c))
        restart_mongo_proc(self.shard1_scnd_p)
        secondary_admin = self.shard1_secondary_conn["admin"]
        c = lambda: secondary_admin.command("replSetGetStatus")["myState"] == 2
        assert_soon(c)
        query = {"i": {"$lt": 1000}}
        assert_soon(lambda: retry_until_ok(db_main.find(query).count) > 0)

        # Only first document should exist in MongoDB
        self.assertEqual(db_main.find(query).count(), 1)
        self.assertEqual(db_main.find_one(query)["i"], 0)

        # Same should hold for the doc manager
        docman_docs = [d for d in self.opman1.doc_managers[0]._search()
                       if d["i"] < 1000]
        self.assertEqual(len(docman_docs), 1)
        self.assertEqual(docman_docs[0]["i"], 0)

        # Wait for previous rollback to complete
        def rollback_done():
            secondary1_count = retry_until_ok(db_secondary1.count)
            secondary2_count = retry_until_ok(db_secondary2.count)
            return (1, 1) == (secondary1_count, secondary2_count)
        assert_soon(rollback_done,
                    "rollback never replicated to one or more secondaries")

        ##############################

        # Case 2: Primaries on both shards go down
        kill_mongo_proc(self.shard1_prim_p, destroy=False)
        kill_mongo_proc(self.shard2_prim_p, destroy=False)

        # Wait for the secondaries to be promoted
        shard1_secondary_admin = self.shard1_secondary_conn["admin"]
        shard2_secondary_admin = self.shard2_secondary_conn["admin"]
        assert_soon(
            lambda: shard1_secondary_admin.command("isMaster")["ismaster"])
        assert_soon(
            lambda: shard2_secondary_admin.command("isMaster")["ismaster"])

        # Insert another document on each shard. These will be rolled back later
        retry_until_ok(db_main.insert, {"i": 1})
        self.assertEqual(db_secondary1.count(), 2)
        retry_until_ok(db_main.insert, {"i": 1001})
        self.assertEqual(db_secondary2.count(), 2)

        # Wait for replication on the doc manager
        c = lambda: len(self.opman1.doc_managers[0]._search()) == 4
        assert_soon(c, "not all writes were replicated to doc manager")

        # Kill the new primaries
        kill_mongo_proc(self.shard1_scnd_p, destroy=False)
        kill_mongo_proc(self.shard2_scnd_p, destroy=False)

        # Start the servers back up...
        # Shard 1
        restart_mongo_proc(self.shard1_prim_p)
        c = lambda: self.shard1_conn['admin'].command("isMaster")["ismaster"]
        assert_soon(lambda: retry_until_ok(c))
        restart_mongo_proc(self.shard1_scnd_p)
        secondary_admin = self.shard1_secondary_conn["admin"]
        c = lambda: secondary_admin.command("replSetGetStatus")["myState"] == 2
        assert_soon(c)
        # Shard 2
        restart_mongo_proc(self.shard2_prim_p)
        c = lambda: self.shard2_conn['admin'].command("isMaster")["ismaster"]
        assert_soon(lambda: retry_until_ok(c))
        restart_mongo_proc(self.shard2_scnd_p)
        secondary_admin = self.shard2_secondary_conn["admin"]
        c = lambda: secondary_admin.command("replSetGetStatus")["myState"] == 2
        assert_soon(c)

        # Wait for the shards to come online
        assert_soon(lambda: retry_until_ok(db_main.find(query).count) > 0)
        query2 = {"i": {"$gte": 1000}}
        assert_soon(lambda: retry_until_ok(db_main.find(query2).count) > 0)

        # Only first documents should exist in MongoDB
        self.assertEqual(db_main.find(query).count(), 1)
        self.assertEqual(db_main.find_one(query)["i"], 0)
        self.assertEqual(db_main.find(query2).count(), 1)
        self.assertEqual(db_main.find_one(query2)["i"], 1000)

        # Same should hold for the doc manager
        i_values = [d["i"] for d in self.opman1.doc_managers[0]._search()]
        self.assertEqual(len(i_values), 2)
        self.assertIn(0, i_values)
        self.assertIn(1000, i_values)

    def test_with_chunk_migration(self):
        """Test that DocManagers have proper state after both a successful
        and an unsuccessful chunk migration
        """

        # Start replicating to dummy doc managers
        self.opman1.start()
        self.opman2.start()

        collection = self.mongos_conn["test"]["mcsharded"]
        for i in range(1000):
            collection.insert({"i": i + 500})
        # Assert current state of the mongoverse
        self.assertEqual(self.shard1_conn["test"]["mcsharded"].find().count(),
                         500)
        self.assertEqual(self.shard2_conn["test"]["mcsharded"].find().count(),
                         500)
        assert_soon(lambda: len(self.opman1.doc_managers[0]._search()) == 1000)

        # Test successful chunk move from shard 1 to shard 2
        self.mongos_conn["admin"].command(
            "moveChunk",
            "test.mcsharded",
            find={"i": 1},
            to="demo-set-1"
        )

        # doc manager should still have all docs
        all_docs = self.opman1.doc_managers[0]._search()
        self.assertEqual(len(all_docs), 1000)
        for i, doc in enumerate(sorted(all_docs, key=lambda x: x["i"])):
            self.assertEqual(doc["i"], i + 500)

        # Mark the collection as "dropped". This will cause migration to fail.
        self.mongos_conn["config"]["collections"].update(
            {"_id": "test.mcsharded"},
            {"$set": {"dropped": True}}
        )

        # Test unsuccessful chunk move from shard 2 to shard 1
        def fail_to_move_chunk():
            self.mongos_conn["admin"].command(
                "moveChunk",
                "test.mcsharded",
                find={"i": 1},
                to="demo-set-0"
            )
        self.assertRaises(pymongo.errors.OperationFailure, fail_to_move_chunk)
        # doc manager should still have all docs
        all_docs = self.opman1.doc_managers[0]._search()
        self.assertEqual(len(all_docs), 1000)
        for i, doc in enumerate(sorted(all_docs, key=lambda x: x["i"])):
            self.assertEqual(doc["i"], i + 500)

    def test_with_orphan_documents(self):
        """Test that DocManagers have proper state after a chunk migration
        that resuts in orphaned documents.
        """
        # Start replicating to dummy doc managers
        self.opman1.start()
        self.opman2.start()

        collection = self.mongos_conn["test"]["mcsharded"]
        collection.insert({"i": i + 500} for i in range(1000))
        # Assert current state of the mongoverse
        self.assertEqual(self.shard1_conn["test"]["mcsharded"].find().count(),
                         500)
        self.assertEqual(self.shard2_conn["test"]["mcsharded"].find().count(),
                         500)
        assert_soon(lambda: len(self.opman1.doc_managers[0]._search()) == 1000)

        # Stop replication using the 'rsSyncApplyStop' failpoint
        self.shard1_conn.admin.command(
            "configureFailPoint", "rsSyncApplyStop",
            mode="alwaysOn"
        )

        # Move a chunk from shard2 to shard1
        def move_chunk():
            try:
                self.mongos_conn["admin"].command(
                    "moveChunk",
                    "test.mcsharded",
                    find={"i": 1000},
                    to="demo-set-0"
                )
            except pymongo.errors.OperationFailure:
                pass

        # moveChunk will never complete, so use another thread to continue
        mover = threading.Thread(target=move_chunk)
        mover.start()

        # wait for documents to start moving to shard 1
        assert_soon(lambda: self.shard1_conn.test.mcsharded.count() > 500)

        # Get opid for moveChunk command
        operations = self.mongos_conn.test.current_op()
        opid = None
        for op in operations["inprog"]:
            if op.get("query", {}).get("moveChunk"):
                opid = op["opid"]
        self.assertNotEqual(opid, None, "could not find moveChunk operation")
        # Kill moveChunk with the opid
        self.mongos_conn["test"]["$cmd.sys.killop"].find_one({"op": opid})

        # Mongo Connector should not become confused by unsuccessful chunk move
        docs = self.opman1.doc_managers[0]._search()
        self.assertEqual(len(docs), 1000)
        self.assertEqual(sorted(d["i"] for d in docs),
                         list(range(500, 1500)))

        # cleanup
        mover.join()

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_rollbacks
"""Test Mongo Connector's behavior when its source MongoDB system is
experiencing a rollback.

"""

import os
import sys
if sys.version_info[:2] == (2, 6):
    import unittest2 as unittest
else:
    import unittest
import time

from pymongo.read_preferences import ReadPreference
from pymongo import MongoClient

from mongo_connector.util import retry_until_ok
from mongo_connector.locking_dict import LockingDict
from mongo_connector.doc_managers.doc_manager_simulator import DocManager
from mongo_connector.oplog_manager import OplogThread

from tests import mongo_host
from tests.util import assert_soon
from tests.setup_cluster import (
    start_replica_set,
    kill_all,
    kill_mongo_proc,
    restart_mongo_proc,
)


class TestRollbacks(unittest.TestCase):

    def tearDown(self):
        kill_all()

    def setUp(self):
        # Create a new oplog progress file
        try:
            os.unlink("config.txt")
        except OSError:
            pass
        open("config.txt", "w").close()

        # Start a replica set
        _, self.secondary_p, self.primary_p = start_replica_set('rollbacks')
        # Connection to the replica set as a whole
        self.main_conn = MongoClient('%s:%d' % (mongo_host, self.primary_p),
                                     replicaSet='rollbacks')
        # Connection to the primary specifically
        self.primary_conn = MongoClient('%s:%d' % (mongo_host, self.primary_p))
        # Connection to the secondary specifically
        self.secondary_conn = MongoClient(
            '%s:%d' % (mongo_host, self.secondary_p),
            read_preference=ReadPreference.SECONDARY_PREFERRED
        )

        # Wipe any test data
        self.main_conn["test"]["mc"].drop()

        # Oplog thread
        doc_manager = DocManager()
        oplog_progress = LockingDict()
        self.opman = OplogThread(
            primary_conn=self.main_conn,
            main_address='%s:%d' % (mongo_host, self.primary_p),
            oplog_coll=self.main_conn["local"]["oplog.rs"],
            is_sharded=False,
            doc_manager=doc_manager,
            oplog_progress_dict=oplog_progress,
            namespace_set=["test.mc"],
            auth_key=None,
            auth_username=None,
            repl_set="rollbacks"
        )

    def test_single_target(self):
        """Test with a single replication target"""

        self.opman.start()

        # Insert first document with primary up
        self.main_conn["test"]["mc"].insert({"i": 0})
        self.assertEqual(self.primary_conn["test"]["mc"].find().count(), 1)

        # Make sure the insert is replicated
        secondary = self.secondary_conn
        assert_soon(lambda: secondary["test"]["mc"].count() == 1,
                    "first write didn't replicate to secondary")

        # Kill the primary
        kill_mongo_proc(self.primary_p, destroy=False)

        # Wait for the secondary to be promoted
        while not secondary["admin"].command("isMaster")["ismaster"]:
            time.sleep(1)

        # Insert another document. This will be rolled back later
        retry_until_ok(self.main_conn["test"]["mc"].insert, {"i": 1})
        self.assertEqual(secondary["test"]["mc"].count(), 2)

        # Wait for replication to doc manager
        assert_soon(lambda: len(self.opman.doc_managers[0]._search()) == 2,
                    "not all writes were replicated to doc manager")

        # Kill the new primary
        kill_mongo_proc(self.secondary_p, destroy=False)

        # Start both servers back up
        restart_mongo_proc(self.primary_p)
        primary_admin = self.primary_conn["admin"]
        assert_soon(lambda: primary_admin.command("isMaster")["ismaster"],
                    "restarted primary never resumed primary status")
        restart_mongo_proc(self.secondary_p)
        assert_soon(lambda: retry_until_ok(secondary.admin.command,
                                           'replSetGetStatus')['myState'] == 2,
                    "restarted secondary never resumed secondary status")
        assert_soon(lambda:
                    retry_until_ok(self.main_conn.test.mc.find().count) > 0,
                    "documents not found after primary/secondary restarted")

        # Only first document should exist in MongoDB
        self.assertEqual(self.main_conn["test"]["mc"].count(), 1)
        self.assertEqual(self.main_conn["test"]["mc"].find_one()["i"], 0)

        # Same case should hold for the doc manager
        doc_manager = self.opman.doc_managers[0]
        self.assertEqual(len(doc_manager._search()), 1)
        self.assertEqual(doc_manager._search()[0]["i"], 0)

        # cleanup
        self.opman.join()

    def test_many_targets(self):
        """Test with several replication targets"""

        # OplogThread has multiple doc managers
        doc_managers = [DocManager(), DocManager(), DocManager()]
        self.opman.doc_managers = doc_managers

        self.opman.start()

        # Insert a document into each namespace
        self.main_conn["test"]["mc"].insert({"i": 0})
        self.assertEqual(self.primary_conn["test"]["mc"].count(), 1)

        # Make sure the insert is replicated
        secondary = self.secondary_conn
        assert_soon(lambda: secondary["test"]["mc"].count() == 1,
                    "first write didn't replicate to secondary")

        # Kill the primary
        kill_mongo_proc(self.primary_p, destroy=False)

        # Wait for the secondary to be promoted
        assert_soon(lambda: secondary.admin.command("isMaster")['ismaster'],
                    'secondary was never promoted')

        # Insert more documents. This will be rolled back later
        # Some of these documents will be manually removed from
        # certain doc managers, to emulate the effect of certain
        # target systems being ahead/behind others
        secondary_ids = []
        for i in range(1, 10):
            secondary_ids.append(
                retry_until_ok(self.main_conn["test"]["mc"].insert,
                               {"i": i}))
        self.assertEqual(self.secondary_conn["test"]["mc"].count(), 10)

        # Wait for replication to the doc managers
        def docmans_done():
            for dm in self.opman.doc_managers:
                if len(dm._search()) != 10:
                    return False
            return True
        assert_soon(docmans_done,
                    "not all writes were replicated to doc managers")

        # Remove some documents from the doc managers to simulate
        # uneven replication
        for id in secondary_ids[8:]:
            self.opman.doc_managers[1].remove({"_id": id})
        for id in secondary_ids[2:]:
            self.opman.doc_managers[2].remove({"_id": id})

        # Kill the new primary
        kill_mongo_proc(self.secondary_p, destroy=False)

        # Start both servers back up
        restart_mongo_proc(self.primary_p)
        primary_admin = self.primary_conn["admin"]
        assert_soon(lambda: primary_admin.command("isMaster")['ismaster'],
                    'restarted primary never resumed primary status')
        restart_mongo_proc(self.secondary_p)
        assert_soon(lambda: retry_until_ok(secondary.admin.command,
                                           'replSetGetStatus')['myState'] == 2,
                    "restarted secondary never resumed secondary status")
        assert_soon(lambda:
                    retry_until_ok(self.primary_conn.test.mc.find().count) > 0,
                    "documents not found after primary/secondary restarted")

        # Only first document should exist in MongoDB
        self.assertEqual(self.primary_conn["test"]["mc"].count(), 1)
        self.assertEqual(self.primary_conn["test"]["mc"].find_one()["i"], 0)

        # Give OplogThread some time to catch up
        time.sleep(10)

        # Same case should hold for the doc managers
        for dm in self.opman.doc_managers:
            self.assertEqual(len(dm._search()), 1)
            self.assertEqual(dm._search()[0]["i"], 0)

        self.opman.join()

########NEW FILE########
__FILENAME__ = test_solr
# Copyright 2013-2014 MongoDB, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Test Solr search using the synchronizer, i.e. as it would be used by an user
    """
import logging
import os
import time
import sys
if sys.version_info[:2] == (2, 6):
    import unittest2 as unittest
else:
    import unittest

sys.path[0:0] = [""]

from pymongo import MongoClient

from tests import solr_pair, mongo_host, STRESS_COUNT
from tests.setup_cluster import (start_replica_set,
                                 kill_replica_set,
                                 restart_mongo_proc,
                                 kill_mongo_proc)
from tests.util import assert_soon
from pysolr import Solr, SolrError
from mongo_connector.connector import Connector
from mongo_connector.util import retry_until_ok
from pymongo.errors import OperationFailure, AutoReconnect


class TestSynchronizer(unittest.TestCase):
    """ Tests Solr
    """

    @classmethod
    def setUpClass(cls):
        _, cls.secondary_p, cls.primary_p = start_replica_set('test-solr')
        cls.conn = MongoClient(mongo_host, cls.primary_p,
                               replicaSet='test-solr')
        cls.solr_conn = Solr('http://%s/solr' % solr_pair)
        cls.solr_conn.delete(q='*:*')

    @classmethod
    def tearDownClass(cls):
        """ Kills cluster instance
        """
        kill_replica_set('test-solr')

    def setUp(self):
        try:
            os.unlink("config.txt")
        except OSError:
            pass
        open("config.txt", "w").close()
        self.connector = Connector(
            address='%s:%s' % (mongo_host, self.primary_p),
            oplog_checkpoint='config.txt',
            target_url='http://localhost:8983/solr',
            ns_set=['test.test'],
            u_key='_id',
            auth_key=None,
            doc_manager='mongo_connector/doc_managers/solr_doc_manager.py',
            auto_commit_interval=0
        )
        self.connector.start()
        assert_soon(lambda: len(self.connector.shard_set) > 0)
        retry_until_ok(self.conn.test.test.remove)
        assert_soon(lambda: len(self.solr_conn.search('*:*')) == 0)

    def tearDown(self):
        self.connector.join()

    def test_shard_length(self):
        """Tests the shard_length to see if the shard set was recognized
        """

        self.assertEqual(len(self.connector.shard_set), 1)

    def test_insert(self):
        """Tests insert
        """

        self.conn['test']['test'].insert({'name': 'paulie'})
        while (len(self.solr_conn.search('*:*')) == 0):
            time.sleep(1)
        result_set_1 = self.solr_conn.search('paulie')
        self.assertEqual(len(result_set_1), 1)
        result_set_2 = self.conn['test']['test'].find_one()
        for item in result_set_1:
            self.assertEqual(item['_id'], str(result_set_2['_id']))
            self.assertEqual(item['name'], result_set_2['name'])

    def test_remove(self):
        """Tests remove
        """
        self.conn['test']['test'].insert({'name': 'paulie'})
        assert_soon(lambda: len(self.solr_conn.search("*:*")) == 1)
        self.conn['test']['test'].remove({'name': 'paulie'})
        assert_soon(lambda: len(self.solr_conn.search("*:*")) == 0)

    def test_rollback(self):
        """Tests rollback. We force a rollback by inserting one doc, killing
            primary, adding another doc, killing the new primary, and
            restarting both the servers.
        """

        primary_conn = MongoClient(mongo_host, self.primary_p)

        self.conn['test']['test'].insert({'name': 'paul'})
        while self.conn['test']['test'].find({'name': 'paul'}).count() != 1:
            time.sleep(1)
        while len(self.solr_conn.search('*:*')) != 1:
            time.sleep(1)
        kill_mongo_proc(self.primary_p, destroy=False)

        new_primary_conn = MongoClient(mongo_host, self.secondary_p)
        admin_db = new_primary_conn['admin']
        while admin_db.command("isMaster")['ismaster'] is False:
            time.sleep(1)
        time.sleep(5)
        retry_until_ok(self.conn.test.test.insert,
                       {'name': 'pauline'})
        while (len(self.solr_conn.search('*:*')) != 2):
            time.sleep(1)

        result_set_1 = self.solr_conn.search('pauline')
        result_set_2 = self.conn['test']['test'].find_one({'name': 'pauline'})
        self.assertEqual(len(result_set_1), 1)
        for item in result_set_1:
            self.assertEqual(item['_id'], str(result_set_2['_id']))
        kill_mongo_proc(self.secondary_p, destroy=False)

        restart_mongo_proc(self.primary_p)

        while primary_conn['admin'].command("isMaster")['ismaster'] is False:
            time.sleep(1)

        restart_mongo_proc(self.secondary_p)

        time.sleep(2)
        result_set_1 = self.solr_conn.search('pauline')
        self.assertEqual(len(result_set_1), 0)
        result_set_2 = self.solr_conn.search('paul')
        self.assertEqual(len(result_set_2), 1)

    def test_stress(self):
        """Test stress by inserting and removing a large amount of docs.
        """
        #stress test
        for i in range(0, STRESS_COUNT):
            self.conn['test']['test'].insert({'name': 'Paul ' + str(i)})
        time.sleep(5)
        while (len(self.solr_conn.search('*:*', rows=STRESS_COUNT))
                != STRESS_COUNT):
            time.sleep(5)
        for i in range(0, STRESS_COUNT):
            result_set_1 = self.solr_conn.search('Paul ' + str(i))
            for item in result_set_1:
                self.assertEqual(item['_id'], item['_id'])

    def test_stressed_rollback(self):
        """Test stressed rollback with a large number of documents"""

        for i in range(0, STRESS_COUNT):
            self.conn['test']['test'].insert(
                {'name': 'Paul ' + str(i)})

        while (len(self.solr_conn.search('*:*', rows=STRESS_COUNT))
                != STRESS_COUNT):
            time.sleep(1)
        primary_conn = MongoClient(mongo_host, self.primary_p)
        kill_mongo_proc(self.primary_p, destroy=False)

        new_primary_conn = MongoClient(mongo_host, self.secondary_p)
        admin_db = new_primary_conn['admin']

        while admin_db.command("isMaster")['ismaster'] is False:
            time.sleep(1)
        time.sleep(5)
        count = -1
        while count + 1 < STRESS_COUNT:
            try:
                count += 1
                self.conn['test']['test'].insert(
                    {'name': 'Pauline ' + str(count)})

            except (OperationFailure, AutoReconnect):
                time.sleep(1)

        while (len(self.solr_conn.search('*:*', rows=STRESS_COUNT * 2)) !=
               self.conn['test']['test'].find().count()):
            time.sleep(1)
        result_set_1 = self.solr_conn.search(
            'Pauline',
            rows=STRESS_COUNT * 2, sort='_id asc'
        )
        for item in result_set_1:
            result_set_2 = self.conn['test']['test'].find_one(
                {'name': item['name']})
            self.assertEqual(item['_id'], str(result_set_2['_id']))

        kill_mongo_proc(self.secondary_p, destroy=False)
        restart_mongo_proc(self.primary_p)

        while primary_conn['admin'].command("isMaster")['ismaster'] is False:
            time.sleep(1)

        restart_mongo_proc(self.secondary_p)

        while (len(self.solr_conn.search(
                'Pauline',
                rows=STRESS_COUNT * 2)) != 0):
            time.sleep(15)
        result_set_1 = self.solr_conn.search(
            'Pauline',
            rows=STRESS_COUNT * 2
        )
        self.assertEqual(len(result_set_1), 0)
        result_set_2 = self.solr_conn.search(
            'Paul',
            rows=STRESS_COUNT * 2
        )
        self.assertEqual(len(result_set_2), STRESS_COUNT)

    def test_valid_fields(self):
        """ Tests documents with field definitions
        """
        inserted_obj = self.conn['test']['test'].insert(
            {'name': 'test_valid'})
        self.conn['test']['test'].update(
            {'_id': inserted_obj},
            {'$set': {'popularity': 1}}
        )

        docman = self.connector.doc_managers[0]
        for _ in range(60):
            if len(docman._search("*:*")) != 0:
                break
            time.sleep(1)
        else:
            self.fail("Timeout when removing docs from Solr")

        result = docman.get_last_doc()
        self.assertIn('popularity', result)
        self.assertEqual(len(docman._search(
            "name=test_valid")), 1)

    def test_invalid_fields(self):
        """ Tests documents without field definitions
        """
        inserted_obj = self.conn['test']['test'].insert(
            {'name': 'test_invalid'})
        self.conn['test']['test'].update(
            {'_id': inserted_obj},
            {'$set': {'break_this_test': 1}}
        )

        docman = self.connector.doc_managers[0]
        for _ in range(60):
            if len(docman._search("*:*")) != 0:
                break
            time.sleep(1)
        else:
            self.fail("Timeout when removing docs from Solr")

        result = docman.get_last_doc()
        self.assertNotIn('break_this_test', result)
        self.assertEqual(len(docman._search(
            "name=test_invalid")), 1)

    def test_dynamic_fields(self):
        """ Tests dynamic field definitions

        The following fields are supplied in the provided schema.xml:
        <dynamicField name="*_i" type="int" indexed="true" stored="true"/>
        <dynamicField name="i_*" type="int" indexed="true" stored="true"/>

        Cases:
        1. Match on first definition
        2. Match on second definition
        3. No match
        """
        self.solr_conn.delete(q='*:*')

        match_first = {"_id": 0, "foo_i": 100}
        match_second = {"_id": 1, "i_foo": 200}
        match_none = {"_id": 2, "foo": 300}

        # Connector is already running
        self.conn["test"]["test"].insert(match_first)
        self.conn["test"]["test"].insert(match_second)
        self.conn["test"]["test"].insert(match_none)

        # Should have documents in Solr now
        assert_soon(lambda: len(self.solr_conn.search("*:*")) > 0,
                    "Solr doc manager should allow dynamic fields")

        # foo_i and i_foo should be indexed, foo field should not exist
        self.assertEqual(len(self.solr_conn.search("foo_i:100")), 1)
        self.assertEqual(len(self.solr_conn.search("i_foo:200")), 1)

        # SolrError: "undefined field foo"
        logger = logging.getLogger("pysolr")
        logger.error("You should see an ERROR log message from pysolr here. "
                     "This indicates success, not an error in the test.")
        with self.assertRaises(SolrError):
            self.solr_conn.search("foo:300")

    def test_nested_fields(self):
        """Test indexing fields that are sub-documents in MongoDB

        The following fields are defined in the provided schema.xml:

        <field name="person.address.street" type="string" ... />
        <field name="person.address.state" type="string" ... />
        <dynamicField name="numbers.*" type="string" ... />
        <dynamicField name="characters.*" type="string" ... />

        """

        # Connector is already running
        self.conn["test"]["test"].insert({
            "name": "Jeb",
            "billing": {
                "address": {
                    "street": "12345 Mariposa Street",
                    "state": "California"
                }
            }
        })
        self.conn["test"]["test"].insert({
            "numbers": ["one", "two", "three"],
            "characters": [
                {"name": "Big Bird",
                 "color": "yellow"},
                {"name": "Elmo",
                 "color": "red"},
                "Cookie Monster"
            ]
        })

        assert_soon(lambda: len(self.solr_conn.search("*:*")) > 0,
                    "documents should have been replicated to Solr")

        # Search for first document
        results = self.solr_conn.search(
            "billing.address.street:12345\ Mariposa\ Street")
        self.assertEqual(len(results), 1)
        self.assertEqual(next(iter(results))["billing.address.state"],
                         "California")

        # Search for second document
        results = self.solr_conn.search(
            "characters.1.color:red")
        self.assertEqual(len(results), 1)
        self.assertEqual(next(iter(results))["numbers.2"], "three")
        results = self.solr_conn.search("characters.2:Cookie\ Monster")
        self.assertEqual(len(results), 1)

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_solr_doc_manager
# Copyright 2013-2014 MongoDB, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import time
import sys
if sys.version_info[:2] == (2, 6):
    import unittest2 as unittest
else:
    import unittest

sys.path[0:0] = [""]

from mongo_connector.doc_managers.solr_doc_manager import DocManager
from pysolr import Solr


class SolrDocManagerTester(unittest.TestCase):
    """Test class for SolrDocManager
    """

    @classmethod
    def setUpClass(cls):
        """ Initializes the DocManager and a direct connection
        """
        cls.SolrDoc = DocManager("http://localhost:8983/solr/",
                                 auto_commit_interval=0)
        cls.solr = Solr("http://localhost:8983/solr/")

    def setUp(self):
        """Empty Solr at the start of every test
        """

        self.solr.delete(q='*:*')

    def test_update(self):
        doc = {"_id": '1', "ns": "test.test", "_ts": 1,
               "title": "abc", "description": "def"}
        self.SolrDoc.upsert(doc)
        # $set only
        update_spec = {"$set": {"title": "qaz", "description": "wsx"}}
        doc = self.SolrDoc.update(doc, update_spec)
        expected = {"_id": '1', "ns": "test.test", "_ts": 1,
                    "title": "qaz", "description": "wsx"}
        # We can't use assertEqual here, because Solr adds some
        # additional fields like _version_ to all documents
        for k, v in expected.items():
            self.assertEqual(doc[k], v)

        # $unset only
        update_spec = {"$unset": {"title": True}}
        doc = self.SolrDoc.update(doc, update_spec)
        expected = {"_id": '1', "ns": "test.test", "_ts": 1,
                    "description": "wsx"}
        for k, v in expected.items():
            self.assertEqual(doc[k], v)
        self.assertNotIn("title", doc)

        # mixed $set/$unset
        update_spec = {"$unset": {"description": True},
                       "$set": {"subject": "edc"}}
        doc = self.SolrDoc.update(doc, update_spec)
        expected = {"_id": '1', "ns": "test.test", "_ts": 1, "subject": "edc"}
        for k, v in expected.items():
            self.assertEqual(doc[k], v)
        self.assertNotIn("description", doc)

    def test_upsert(self):
        """Ensure we can properly insert into Solr via DocManager.
        """
        #test upsert
        docc = {'_id': '1', 'name': 'John'}
        self.SolrDoc.upsert(docc)
        res = self.solr.search('*:*')
        for doc in res:
            self.assertTrue(doc['_id'] == '1' and doc['name'] == 'John')

        docc = {'_id': '1', 'name': 'Paul'}
        self.SolrDoc.upsert(docc)
        res = self.solr.search('*:*')
        for doc in res:
            self.assertTrue(doc['_id'] == '1' and doc['name'] == 'Paul')

    def test_bulk_upsert(self):
        """Ensure we can properly insert many documents at once into
        Solr via DocManager

        """
        self.SolrDoc.bulk_upsert([])

        docs = ({"_id": i, "ns": "test.test"} for i in range(1000))
        self.SolrDoc.bulk_upsert(docs)

        res = sorted(int(x["_id"]) for x in self.solr.search("*:*", rows=1001))
        self.assertEqual(len(res), 1000)
        for i, r in enumerate(res):
            self.assertEqual(r, i)

        docs = ({"_id": i, "weight": 2*i,
                 "ns": "test.test"} for i in range(1000))
        self.SolrDoc.bulk_upsert(docs)

        res = sorted(int(x["weight"]) for x in self.solr.search("*:*", rows=1001))
        self.assertEqual(len(res), 1000)
        for i, r in enumerate(res):
            self.assertEqual(r, 2*i)

    def test_remove(self):
        """Ensure we can properly delete from Solr via DocManager.
        """
        #test remove
        docc = {'_id': '1', 'name': 'John'}
        self.SolrDoc.upsert(docc)
        res = self.solr.search('*:*')
        self.assertTrue(len(res) == 1)

        self.SolrDoc.remove(docc)
        res = self.solr.search('*:*')
        self.assertTrue(len(res) == 0)

    def test_full_search(self):
        """Query Solr for all docs via API and via DocManager's _search()
        """
        #test _search
        docc = {'_id': '1', 'name': 'John'}
        self.SolrDoc.upsert(docc)
        docc = {'_id': '2', 'name': 'Paul'}
        self.SolrDoc.upsert(docc)
        search = self.SolrDoc._search('*:*')
        search2 = self.solr.search('*:*')
        self.assertTrue(len(search) == len(search2))
        self.assertTrue(len(search) != 0)
        self.assertTrue(all(x in search for x in search2) and
                        all(y in search2 for y in search))

    def test_search(self):
        """Query Solr for docs in a timestamp range.

        We use API and DocManager's search(start_ts,end_ts), and then compare.
        """
        #test search
        docc = {'_id': '1', 'name': 'John', '_ts': 5767301236327972865}
        self.SolrDoc.upsert(docc)
        docc = {'_id': '2', 'name': 'John Paul', '_ts': 5767301236327972866}
        self.SolrDoc.upsert(docc)
        docc = {'_id': '3', 'name': 'Paul', '_ts': 5767301236327972870}
        self.SolrDoc.upsert(docc)
        search = self.SolrDoc.search(5767301236327972865, 5767301236327972866)
        search2 = self.solr.search('John')
        self.assertTrue(len(search) == len(search2))
        self.assertTrue(len(search) != 0)

        result_names = [result.get("name") for result in search]
        self.assertIn('John', result_names)
        self.assertIn('John Paul', result_names)

    def test_solr_commit(self):
        """Test that documents get properly added to Solr.
        """
        docc = {'_id': '3', 'name': 'Waldo', 'ns': 'test.test'}
        docman = DocManager("http://localhost:8983/solr")
        # test cases:
        # -1 = no autocommit
        # 0 = commit immediately
        # x > 0 = commit within x seconds
        for autocommit_interval in [None, 0, 1, 2]:
            docman.auto_commit_interval = autocommit_interval
            docman.upsert(docc)
            if autocommit_interval is None:
                docman.commit()
            else:
                # Allow just a little extra time
                time.sleep(autocommit_interval + 1)
            results = list(docman._search("Waldo"))
            self.assertEqual(len(results), 1,
                             "should commit document with "
                             "auto_commit_interval = %s" % str(
                                 autocommit_interval))
            self.assertEqual(results[0]["name"], "Waldo")
            docman._remove()
            docman.commit()

    def test_get_last_doc(self):
        """Insert documents, Verify the doc with the latest timestamp.
        """
        #test get last doc
        docc = {'_id': '4', 'name': 'Hare', '_ts': '2'}
        self.SolrDoc.upsert(docc)
        docc = {'_id': '5', 'name': 'Tortoise', '_ts': '1'}
        self.SolrDoc.upsert(docc)
        doc = self.SolrDoc.get_last_doc()
        self.assertTrue(doc['_id'] == '4')

        docc = {'_id': '6', 'name': 'HareTwin', 'ts': '2'}
        doc = self.SolrDoc.get_last_doc()
        self.assertTrue(doc['_id'] == '4' or doc['_id'] == '6')

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_synchronizer
# Copyright 2013-2014 MongoDB, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Test synchronizer using DocManagerSimulator
"""
import os
import sys

sys.path[0:0] = [""]

from pymongo import MongoClient

import time
if sys.version_info[:2] == (2, 6):
    import unittest2 as unittest
else:
    import unittest
from tests import mongo_host
from tests.setup_cluster import (start_replica_set,
                                 kill_all)
from tests.util import assert_soon
from mongo_connector.connector import Connector


class TestSynchronizer(unittest.TestCase):
    """ Tests the synchronizers
    """

    @classmethod
    def setUpClass(cls):
        """ Initializes the cluster
        """
        try:
            os.unlink("config.txt")
        except OSError:
            pass
        open("config.txt", "w").close()

        _, _, cls.primary_p = start_replica_set('test-synchronizer')
        cls.conn = MongoClient('%s:%d' % (mongo_host, cls.primary_p),
                               replicaSet='test-synchronizer')
        cls.connector = Connector(
            address='%s:%d' % (mongo_host, cls.primary_p),
            oplog_checkpoint='config.txt',
            target_url=None,
            ns_set=['test.test'],
            u_key='_id',
            auth_key=None
        )
        cls.synchronizer = cls.connector.doc_managers[0]
        cls.connector.start()
        assert_soon(lambda: len(cls.connector.shard_set) != 0)

    @classmethod
    def tearDownClass(cls):
        """ Tears down connector
        """
        cls.connector.join()
        kill_all()

    def setUp(self):
        """ Clears the db
        """
        self.conn['test']['test'].remove()
        assert_soon(lambda: len(self.synchronizer._search()) == 0)

    def test_insert(self):
        """Tests insert
        """
        self.conn['test']['test'].insert({'name': 'paulie'})
        while (len(self.synchronizer._search()) == 0):
            time.sleep(1)
        result_set_1 = self.synchronizer._search()
        self.assertEqual(len(result_set_1), 1)
        result_set_2 = self.conn['test']['test'].find_one()
        for item in result_set_1:
            self.assertEqual(item['_id'], result_set_2['_id'])
            self.assertEqual(item['name'], result_set_2['name'])

    def test_remove(self):
        """Tests remove
        """
        self.conn['test']['test'].insert({'name': 'paulie'})
        while (len(self.synchronizer._search()) != 1):
            time.sleep(1)
        self.conn['test']['test'].remove({'name': 'paulie'})

        while (len(self.synchronizer._search()) == 1):
            time.sleep(1)
        result_set_1 = self.synchronizer._search()
        self.assertEqual(len(result_set_1), 0)

    def test_update(self):
        """Test that Connector can replicate updates successfully."""
        doc = {"a": 1, "b": 2}
        self.conn.test.test.insert(doc)
        selector = {"_id": doc['_id']}

        def update_and_retrieve(update_spec):
            self.conn.test.test.update(selector, update_spec)
            # Give the connector some time to perform update
            time.sleep(1)
            return self.synchronizer._search()[0]

        # $set only
        doc = update_and_retrieve({"$set": {"b": 4}})
        self.assertEqual(doc['a'], 1)
        self.assertEqual(doc['b'], 4)

        # $unset only
        doc = update_and_retrieve({"$unset": {"a": True}})
        self.assertNotIn('a', doc)
        self.assertEqual(doc['b'], 4)

        # mixed $set/$unset
        doc = update_and_retrieve({"$unset": {"b": True}, "$set": {"c": 3}})
        self.assertEqual(doc['c'], 3)
        self.assertNotIn('b', doc)

        # ensure update works when fields are given
        opthread = self.connector.shard_set[0]
        opthread.fields = ['a', 'b', 'c']
        try:
            doc = update_and_retrieve({"$set": {"d": 10}})
            self.assertEqual(self.conn.test.test.find_one(doc['_id'])['d'], 10)
            self.assertNotIn('d', doc)
            doc = update_and_retrieve({"$set": {"a": 10}})
            self.assertEqual(doc['a'], 10)
        finally:
            # cleanup
            opthread.fields = None


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_util
# Copyright 2013-2014 MongoDB, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Tests methods in util.py
"""

import sys

sys.path[0:0] = [""]

if sys.version_info[:2] == (2, 6):
    import unittest2 as unittest
else:
    import unittest
from bson import timestamp
from mongo_connector.util import (bson_ts_to_long,
                                  long_to_bson_ts,
                                  retry_until_ok)


def err_func():
    """Helper function for retry_until_ok test
    """

    err_func.counter += 1
    if err_func.counter == 3:
        return True
    else:
        raise TypeError

err_func.counter = 0


class UtilTester(unittest.TestCase):
    """ Tests the utils
    """

    def test_bson_ts_to_long(self):
        """Test bson_ts_to_long and long_to_bson_ts
        """

        tstamp = timestamp.Timestamp(0x12345678, 0x90abcdef)

        self.assertEqual(0x1234567890abcdef,
                         bson_ts_to_long(tstamp))
        self.assertEqual(long_to_bson_ts(0x1234567890abcdef),
                         tstamp)

    def test_retry_until_ok(self):
        """Test retry_until_ok
        """

        self.assertTrue(retry_until_ok(err_func))
        self.assertEqual(err_func.counter, 3)


if __name__ == '__main__':

    unittest.main()

########NEW FILE########
__FILENAME__ = util
# Copyright 2013-2014 MongoDB, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Utilities for mongo-connector tests. There are no actual tests in here.
"""

import time


def wait_for(condition, max_tries=60):
    """Wait for a condition to be true up to a maximum number of tries
    """
    while not condition() and max_tries > 1:
        time.sleep(1)
        max_tries -= 1
    return condition()


def assert_soon(condition, message=None, max_tries=60):
    """Assert that a condition eventually evaluates to True after at most
    max_tries number of attempts

    """
    if not wait_for(condition, max_tries=max_tries):
        raise AssertionError(message or "")

########NEW FILE########
