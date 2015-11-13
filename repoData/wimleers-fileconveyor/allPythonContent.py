__FILENAME__ = arbitrator
import logging
import logging.handlers
import Queue
import os
import stat
import threading
import time
import sys
import sqlite3
from UserList import UserList
import os.path
import signal


FILE_CONVEYOR_PATH = os.path.abspath(os.path.dirname(__file__))


# HACK to make sure that Django-related libraries can be loaded: include dummy
# settings if necessary.
if not 'DJANGO_SETTINGS_MODULE' in os.environ:
    os.environ['DJANGO_SETTINGS_MODULE'] = 'fileconveyor.django_settings'


from settings import *
from config import *
from persistent_queue import *
from persistent_list import *
from fsmonitor import *
from filter import *
from processors.processor import *
from transporters.transporter import Transporter, ConnectionError
from daemon_thread_runner import *


# Copied from django.utils.functional
def curry(_curried_func, *args, **kwargs):
    def _curried(*moreargs, **morekwargs):
        return _curried_func(*(args+moreargs), **dict(kwargs, **morekwargs))
    return _curried


class AdvancedQueue(UserList):
    """queue that supports peeking and jumping"""

    def peek(self):
        return self[0]

    def jump(self, item):
        self.insert(0, item)

    def put(self, item):
        self.append(item)

    def get(self):
        return self.pop(0)

    def qsize(self):
        return len(self)


# Define exceptions.
class ArbitratorError(Exception): pass
class ArbitratorInitError(ArbitratorError): pass
class ConfigError(ArbitratorInitError): pass
class ProcessorAvailabilityTestError(ArbitratorInitError): pass
class TransporterAvailabilityTestError(ArbitratorInitError): pass
class ServerConnectionTestError(ArbitratorInitError): pass
class FSMonitorInitError(ArbitratorInitError): pass


class Arbitrator(threading.Thread):
    """docstring for arbitrator"""


    DELETE_OLD_FILE = 0xFFFFFFFF
    PROCESSED_FOR_ANY_SERVER = None


    def __init__(self, configfile="config.xml", restart=False):
        threading.Thread.__init__(self, name="ArbitratorThread")
        self.lock = threading.Lock()
        self.die = False
        self.processorchains_running = 0
        self.transporters_running = 0
        self.last_retry = 0

        # Set up logger.
        self.logger = logging.getLogger("Arbitrator")
        self.logger.setLevel(FILE_LOGGER_LEVEL)
        # Handlers.
        fileHandler = logging.handlers.RotatingFileHandler(LOG_FILE, maxBytes=5242880, backupCount=5)
        consoleHandler = logging.StreamHandler()
        consoleHandler.setLevel(CONSOLE_LOGGER_LEVEL)
        # Formatters.
        formatter = logging.Formatter("%(asctime)s - %(name)-25s - %(levelname)-8s - %(message)s")
        fileHandler.setFormatter(formatter)
        consoleHandler.setFormatter(formatter)
        self.logger.addHandler(fileHandler)
        self.logger.addHandler(consoleHandler)
        if restart:
            self.logger.warning("File Conveyor has restarted itself!")
        self.logger.warning("File Conveyor is initializing.")

        # Load config file.
        self.configfile = configfile
        self.logger.info("Loading config file.")
        self.config = Config("Arbitrator")
        self.config_errors = self.config.load(self.configfile)
        self.logger.warning("Loaded config file.")
        if self.config_errors > 0:
            self.logger.error("Cannot continue, please fix the errors in the config file first.")
            raise ConfigError("Consult the log file for details.")

        # TRICKY: set the "symlinkWithin" setting for "symlink_or_copy"
        # transporters First calculate the value for the "symlinkWithin"
        # setting.
        source_paths = []
        for source in self.config.sources.values():
            source_paths.append(source["scan_path"])
        symlinkWithin = ":".join(source_paths)
        # Then set it for every server that uses this transporter.
        for name in self.config.servers.keys():
            if self.config.servers[name]["transporter"] == "symlink_or_copy":
                self.config.servers[name]["settings"]["symlinkWithin"] = symlinkWithin

        # Verify that all referenced processors are available.
        processors_not_found = 0
        for source in self.config.rules.keys():
            for rule in self.config.rules[source]:
                if not rule["processorChain"] is None:
                    for processor in rule["processorChain"]:
                        processor_class = self._import_processor(processor)
                        if not processor_class:
                            processors_not_found += 1
        if processors_not_found > 0:
            raise ProcessorAvailabilityTestError("Consult the log file for details")

        # Verify that all referenced transporters are available.
        transporters_not_found = 0
        for server in self.config.servers.keys():
            transporter_name = self.config.servers[server]["transporter"]
            transporter_class = self._import_transporter(transporter_name)
            if not transporter_class:
                transporters_not_found += 1
        if transporters_not_found > 0:
            raise TransporterAvailabilityTestError("Consult the log file for details")

        # Verify that each of the servers works.
        successful_server_connections = 0
        for server in self.config.servers.keys():
            transporter = self.__create_transporter(server)
            if transporter:
                successful_server_connections += 1
            del transporter
        failed_server_connections = len(self.config.servers) - successful_server_connections
        if failed_server_connections > 0:
            self.logger.error("Server connection tests: could not connect with %d servers." % (failed_server_connections))
            raise ServerConnectionTestError("Consult the log file for details.")
        else:
            self.logger.warning("Server connection tests succesful!")


    def __setup(self):
        self.processor_chain_factory = ProcessorChainFactory("Arbitrator", WORKING_DIR)

        # Create transporter (cfr. worker thread) pools for each server.
        # Create one initial transporter per pool, possible other transporters
        # will be created on-demand.
        self.transporters = {}
        for server in self.config.servers.keys():
            self.transporters[server] = []
            self.logger.warning("Setup: created transporter pool for the '%s' server." % (server))

        # Collecting all necessary metadata for each rule.
        self.rules = []
        for source in self.config.sources.values():
            # Create a function to prepend the source's scan path to another
            # path.
            prepend_scan_path = lambda path: os.path.join(source["scan_path"], path)
            if self.config.rules.has_key(source["name"]):
                for rule in self.config.rules[source["name"]]:
                    if rule["filterConditions"] is None:
                        filter = None
                    else:
                        if rule["filterConditions"].has_key("paths"):
                            # Prepend the source's scan path (effectively the
                            # "root path") for a rule to each of the paths in
                            # the "paths" condition in the filter.
                            paths = map(prepend_scan_path, rule["filterConditions"]["paths"].split(":"))
                            rule["filterConditions"]["paths"] = ":".join(paths)
                        filter = Filter(rule["filterConditions"])

                    # Store all the rule metadata.
                    self.rules.append({
                        "source"         : source["name"],
                        "label"          : rule["label"],
                        "filter"         : filter,
                        "processorChain" : rule["processorChain"],
                        "destinations"   : rule["destinations"],
                        "deletionDelay"  : rule["deletionDelay"],
                    })
                    self.logger.info("Setup: collected all metadata for rule '%s' (source: '%s')." % (rule["label"], source["name"]))

        # Initialize the the persistent 'pipeline' queue, the persistent
        # 'files in pipeline' and 'failed files' lists and the 'discover',
        # 'filter', 'process', 'transport', 'db' and 'retry' queues. Finally,
        # initialize the 'remaining transporters' dictionary of lists.
        self.pipeline_queue = PersistentQueue("pipeline_queue", PERSISTENT_DATA_DB)
        self.logger.warning("Setup: initialized 'pipeline' persistent queue, contains %d items." % (self.pipeline_queue.qsize()))
        self.files_in_pipeline =  PersistentList("pipeline_list", PERSISTENT_DATA_DB)
        num_files_in_pipeline = len(self.files_in_pipeline)
        self.logger.warning("Setup: initialized 'files_in_pipeline' persistent list, contains %d items." % (num_files_in_pipeline))
        self.failed_files = PersistentList("failed_files_list", PERSISTENT_DATA_DB)
        num_failed_files = len(self.failed_files)
        self.logger.warning("Setup: initialized 'failed_files' persistent list, contains %d items." % (num_failed_files))
        self.files_to_delete = PersistentList("files_to_delete_list", PERSISTENT_DATA_DB)
        num_files_to_delete = len(self.files_to_delete)
        self.logger.warning("Setup: initialized 'files_to_delete' persistent list, contains %d items." % (num_files_to_delete))
        self.discover_queue  = Queue.Queue()
        self.filter_queue    = Queue.Queue()
        self.process_queue   = Queue.Queue()
        self.transport_queue = {}
        for server in self.config.servers.keys():
            self.transport_queue[server] = AdvancedQueue()
        self.db_queue        = Queue.Queue()
        self.retry_queue     = Queue.Queue()
        self.remaining_transporters = {}

        # Move files from the 'files_in_pipeline' persistent list to the 
        # pipeline queue. This is what prevents files from being dropped from
        # the pipeline!
        pipelined_items = []
        for item in self.files_in_pipeline:
            pipelined_items.append(item)
            self.pipeline_queue.put(item)
        for item in pipelined_items:
            self.files_in_pipeline.remove(item)
        self.logger.warning("Setup: moved %d items from the 'files_in_pipeline' persistent list into the 'pipeline' persistent queue." % (num_files_in_pipeline))

        # Move files from the 'failed_files' persistent list to the
        # pipeline queue. This is what ensures that even problematic files
        # are not forgotten!
        self.__allow_retry()

        # Create connection to synced files DB.
        self.dbcon = sqlite3.connect(SYNCED_FILES_DB)
        self.dbcon.text_factory = unicode # This is the default, but we set it explicitly, just to be sure.
        self.dbcur = self.dbcon.cursor()
        self.dbcur.execute("CREATE TABLE IF NOT EXISTS synced_files(input_file text, transported_file_basename text, url text, server text)")
        self.dbcur.execute("CREATE UNIQUE INDEX IF NOT EXISTS file_unique_per_server ON synced_files (input_file, server)")
        self.dbcon.commit()
        self.dbcur.execute("SELECT COUNT(input_file) FROM synced_files")
        num_synced_files = self.dbcur.fetchone()[0]
        self.logger.warning("Setup: connected to the synced files DB. Contains metadata for %d previously synced files." % (num_synced_files))

        # Initialize the FSMonitor.
        fsmonitor_class = get_fsmonitor()
        self.fsmonitor = fsmonitor_class(self.fsmonitor_callback, True, True, self.config.ignored_dirs.split(":"), "fsmonitor.db", "Arbitrator")
        self.logger.warning("Setup: initialized FSMonitor.")

        # Monitor all sources' scan paths.
        for source in self.config.sources.values():
            self.logger.info("Setup: monitoring '%s' (%s)." % (source["scan_path"], source["name"]))
            self.fsmonitor.add_dir(source["scan_path"], FSMonitor.CREATED | FSMonitor.MODIFIED | FSMonitor.DELETED)


    def run(self):
        if self.config_errors > 0:
            return

        # Do all setup within the run() method to ensure all thread-bound
        # objects are created in the right thread.
        self.__setup()

        self.fsmonitor.start()

        self.clean_up_working_dir()

        self.logger.warning("Fully up and running now.")
        try:
            while not self.die:
                self.__process_discover_queue()
                self.__process_pipeline_queue()
                self.__process_filter_queue()
                self.__process_process_queue()
                self.__process_transport_queues()
                self.__process_db_queue()
                self.__process_files_to_delete()
                self.__process_retry_queue()
                self.__allow_retry()

                # Processing the queues 5 times per second is more than sufficient
                # because files are modified, processed and transported much
                # slower than that.
                time.sleep(0.2)
        except Exception, e:
            self.logger.exception("Unhandled exception of type '%s' detected, arguments: '%s'." % (e.__class__.__name__, e.args))
            self.logger.error("Stopping File Conveyor to ensure the application is stopped in a clean manner.")
            os.kill(os.getpid(), signal.SIGTERM)
        self.logger.warning("Stopping.")

        # Stop the FSMonitor and wait for its thread to end.
        self.fsmonitor.stop()
        self.fsmonitor.join()
        self.logger.warning("Stopped FSMonitor.")

        # Sync the discover queue one more time: now that the FSMonitor has
        # been stopped, no more new discoveries will be made and we can safely
        # sync the last batch of discovered files.
        self.__process_discover_queue()
        self.logger.info("Final sync of discover queue to pipeline queue made.")

        # Stop the transporters and wait for their threads to end.
        for server in self.transporters.keys():
            if len(self.transporters[server]):
                for transporter in self.transporters[server]:
                    transporter.stop()
                    transporter.join()
                self.logger.warning("Stopped transporters for the '%s' server." % (server))

        # Log information about the persistent data.
        self.logger.warning("'pipeline' persistent queue contains %d items." % (self.pipeline_queue.qsize()))
        self.logger.warning("'files_in_pipeline' persistent list contains %d items." % (len(self.files_in_pipeline)))
        self.logger.warning("'failed_files' persistent list contains %d items." % (len(self.failed_files)))
        self.logger.warning("'files_to_delete' persistent list contains %d items." % (len(self.files_to_delete)))

        # Log information about the synced files DB.
        self.dbcur.execute("SELECT COUNT(input_file) FROM synced_files")
        num_synced_files = self.dbcur.fetchone()[0]
        self.logger.warning("synced files DB contains metadata for %d synced files." % (num_synced_files))

        # Clean up working directory.
        self.clean_up_working_dir()

        # Final message, then remove all loggers.
        self.logger.warning("File Conveyor has shut down.")
        while len(self.logger.handlers):
            self.logger.removeHandler(self.logger.handlers[0])
        logging.shutdown()


    def __process_discover_queue(self):
        # No QUEUE_PROCESS_BATCH_SIZE limitation here because the data must
        # be moved to a persistent datastructure ASAP.

        self.lock.acquire()
        while self.discover_queue.qsize() > 0:

            # Discover queue -> pipeline queue.
            (input_file, event) = self.discover_queue.get()
            item = self.pipeline_queue.get_item_for_key(key=input_file)
            # If the file does not yet exist in the pipeline queue, put() it.
            if item is None:
                self.pipeline_queue.put(item=(input_file, event), key=input_file)
            # Otherwise, merge the events, to prevent unnecessary actions.
            # See https://github.com/wimleers/fileconveyor/issues/68.
            else:
                old_event = item[1]
                merged_event = FSMonitor.MERGE_EVENTS[old_event][event]
                if merged_event is not None:
                    self.pipeline_queue.update(item=(input_file, merged_event), key=input_file)
                    self.logger.info("Pipeline queue: merged events for '%s': %s + %s = %s." % (input_file, FSMonitor.EVENTNAMES[old_event], FSMonitor.EVENTNAMES[event], FSMonitor.EVENTNAMES[merged_event]))
                # The events being merged cancel each other out, thus remove
                # the file from the pipeline queue.
                else:
                    self.pipeline_queue.remove_item_for_key(key=input_file)
                    self.logger.info("Pipeline queue: merged events for '%s': %s + %s cancel each other out, thus removed this file." % (input_file, FSMonitor.EVENTNAMES[old_event], FSMonitor.EVENTNAMES[event]))
            self.logger.info("Discover queue -> pipeline queue: '%s'." % (input_file))
        self.lock.release()


    def __process_pipeline_queue(self):
        processed = 0

        # As soon as there's room in the pipeline, move the file from the
        # pipeline queue into the pipeline.
        while processed < QUEUE_PROCESS_BATCH_SIZE and self.pipeline_queue.qsize() > 0 and len(self.files_in_pipeline) < MAX_FILES_IN_PIPELINE:
            self.lock.acquire()

            # Peek the first item from the pipeline queue and store it in the
            # persistent 'files_in_pipeline' list. By peeking instead of
            # getting, ththe data can never get lost.
            self.files_in_pipeline.append(self.pipeline_queue.peek())

            # Pipeline queue -> filter queue.
            (input_file, event) = self.pipeline_queue.get()
            self.filter_queue.put((input_file, event))

            self.lock.release()
            self.logger.info("Pipeline queue -> filter queue: '%s'." % (input_file))
            processed += 1


    def __process_filter_queue(self):
        processed = 0

        while processed < QUEUE_PROCESS_BATCH_SIZE and self.filter_queue.qsize() > 0:
            # Filter queue -> process/transport queue.
            self.lock.acquire()
            (input_file, event) = self.filter_queue.get()
            self.lock.release()

            # The file may have already been deleted, e.g. when the file was
            # moved from the pipeline list into the pipeline queue after the
            # application was interrupted. When that's the case, drop the
            # file from the pipeline.
            touched = event == FSMonitor.CREATED or event == FSMonitor.MODIFIED
            if touched and not os.path.exists(input_file):
                self.lock.acquire()
                self.files_in_pipeline.remove((input_file, event))
                self.lock.release()
                self.logger.info("Filtering: dropped '%s' because it no longer exists." % (input_file))
                continue

            # Find all rules that apply to the detected file event.
            match_found = False
            file_is_deleted = event == FSMonitor.DELETED
            current_time = time.time()

            for rule in self.rules:
                # Try to find a rule that matches the file.
                if input_file.startswith(self.config.sources[rule["source"]]["scan_path"]) and \
                   (rule["filter"] is None
                   or
                   rule["filter"].matches(input_file, file_is_deleted=file_is_deleted)):
                    match_found = True
                    self.logger.info("Filtering: '%s' matches the '%s' rule for the '%s' source!" % (input_file, rule["label"], rule["source"]))

                    # If the file was deleted, and the rule that matches this
                    # file has a deletionDelay configured, then don't sync
                    # this file deletion: it was performed by File Conveyor.
                    # *Except* when the file is still scheduled for deletion:
                    # that means the file could not have been deleted by File
                    # Conveyor and hence the deletion should be synced.
                    if event == FSMonitor.DELETED and rule["deletionDelay"] is not None:
                        file_still_scheduled_for_deletion = False
                        scheduled_deletion_time = None
                        self.lock.acquire()
                        for (file_to_delete, deletion_time) in self.files_to_delete:
                            if input_file == file_to_delete:
                                file_still_scheduled_for_deletion = True
                                scheduled_deletion_time = deletion_time
                                break
                        self.lock.release()

                        # Unschedule deletion.
                        if file_still_scheduled_for_deletion:
                            self.lock.acquire()
                            self.files_to_delete.remove((input_file, scheduled_deletion_time))
                            self.logger.warning("Unscheduled '%s' for deletion." % (input_file))
                            self.lock.release()
                        else:
                        # A deletion by File Conveyor: don't sync this deletion.
                            break

                    # If the file was deleted, also delete the file on all
                    # servers.
                    self.lock.acquire()
                    servers = rule["destinations"].keys()
                    self.remaining_transporters[input_file + str(event) + repr(rule)] = servers
                    if event == FSMonitor.DELETED:
                        # Look up the transported file's base name. This might
                        # be different from the input file's base name due to
                        # processing.
                        self.dbcur.execute("SELECT transported_file_basename FROM synced_files WHERE input_file=?", (input_file, ))
                        result = self.dbcur.fetchone()

                    if event == FSMonitor.DELETED and not result is None:
                        transport_file_basename = result[0]
                        # The output file that should be transported doesn't
                        # exist anymore, because it was deleted. So we create
                        # a filename that is the same as the original, except
                        # with the different base name.
                        fake_output_file = os.path.join(os.path.dirname(input_file), transport_file_basename)
                        # Queue the transport (deletion).
                        for server in servers:
                            self.transport_queue[server].put((input_file, event, rule, Arbitrator.PROCESSED_FOR_ANY_SERVER, fake_output_file))
                            self.logger.info("Filtering: queued transporter to server '%s' for file '%s' to delete it ('%s' rule)." % (server, input_file, rule["label"]))
                    else:
                        # If a processor chain is configured, queue the file
                        # to be processed. Otherwise, immediately queue the
                        # file to be transported 
                        if not rule["processorChain"] is None:
                            # Check if there is at least one processor that
                            # will create output that is different per server.
                            per_server = False
                            for processor_classname in rule["processorChain"]:
                                # Get a reference to this processor class.
                                processor_class = self._import_processor(processor_classname)
                                if getattr(processor_class, 'different_per_server', False) == True:
                                    # This processor would create different
                                    # output per server, but will it also
                                    # process this file?
                                    if processor_class.would_process_input_file(input_file):
                                        per_server = True
                                        break

                            if per_server:
                                for server in servers:
                                    # If the event for the file is creation
                                    # and the file has been synced to this
                                    # server already, don't process it again
                                    # (which will lead to it being resynced
                                    # and reinserted into the database, which
                                    # will cause a IntegrityError).
                                    if event == FSMonitor.CREATED:
                                        self.dbcur.execute("SELECT COUNT(*) FROM synced_files WHERE input_file=? AND server=?", (input_file, server))
                                        file_is_synced = self.dbcur.fetchone()[0] == 1
                                    if event == FSMonitor.CREATED and file_is_synced:
                                        self.logger.info("Filtering: not processing '%s' for server '%s', because it has been synced already to this server (rule: '%s')." % (input_file, server, rule["label"]))
                                        self.remaining_transporters[input_file + str(event) + repr(rule)].remove(server)
                                    else:
                                        self.process_queue.put((input_file, event, rule, server))
                                        self.logger.info("Filter queue -> process queue: '%s' for server '%s' (rule: '%s')." % (input_file, server, rule["label"]))
                            else:
                                self.process_queue.put((input_file, event, rule, Arbitrator.PROCESSED_FOR_ANY_SERVER))
                                self.logger.info("Filter queue -> process queue: '%s' (rule: '%s')." % (input_file, rule["label"]))
                        else:
                            output_file = input_file
                            for server in servers:
                                self.transport_queue[server].put((input_file, event, rule, Arbitrator.PROCESSED_FOR_ANY_SERVER, output_file))
                                self.logger.info("Filter queue -> transport queue: '%s' (rule: '%s')." % (input_file, rule["label"]))
                    self.lock.release()

            # Log the lack of matches.
            if not match_found:
                self.lock.acquire()
                self.files_in_pipeline.remove((input_file, event))
                self.lock.release()
                self.logger.info("Filter queue: dropped '%s' because it doesn't match any rules." % (input_file))

            processed += 1


    def __process_process_queue(self):
        processed = 0

        while processed< QUEUE_PROCESS_BATCH_SIZE and self.process_queue.qsize() > 0 and self.processorchains_running < MAX_SIMULTANEOUS_PROCESSORCHAINS:
            # Process queue -> ProcessorChain -> processor_chain_callback -> transport/db queue.
            self.lock.acquire()
            (input_file, event, rule, processed_for_server) = self.process_queue.get()
            self.lock.release()

            # Create curried callbacks so we can pass additional data to the
            # processor chain callback without passing it to the processor
            # chain itself (which cannot handle sending additional data to its
            # callback functions).
            curried_callback = curry(self.processor_chain_callback,
                                     event=event,
                                     rule=rule,
                                     processed_for_server=processed_for_server
                                     )
            curried_error_callback = curry(self.processor_chain_error_callback,
                                           event=event
                                           )

            # Start the processor chain.
            document_root = None
            base_path     = None
            if self.config.sources[rule["source"]].has_key("document_root"):
                document_root = self.config.sources[rule["source"]]["document_root"]
            if self.config.sources[rule["source"]].has_key("base_path"):
                base_path = self.config.sources[rule["source"]]["base_path"]
            processor_chain = self.processor_chain_factory.make_chain_for(input_file,
                                                                          rule["processorChain"],
                                                                          document_root,
                                                                          base_path,
                                                                          processed_for_server,
                                                                          curried_callback,
                                                                          curried_error_callback
                                                                          )
            processor_chain.start()
            self.processorchains_running += 1

            # Log.
            processor_chain_string = "->".join(rule["processorChain"])
            if processed_for_server == Arbitrator.PROCESSED_FOR_ANY_SERVER:
                self.logger.debug("Process queue: started the '%s' processor chain for the file '%s'." % (processor_chain_string, input_file))
            else:
                self.logger.debug("Process queue: started the '%s' processor chain for the file '%s' for the server '%s'." % (processor_chain_string, input_file, processed_for_server))
            processed += 1


    def __process_transport_queues(self):
        for server in self.config.servers.keys():
            processed = 0

            while processed < QUEUE_PROCESS_BATCH_SIZE and self.transport_queue[server].qsize() > 0:
                # Peek at the first item from the queue. We cannot get the
                # item from the queue, because there may be no transporter
                # available, in which case the file should remain queued.
                self.lock.acquire()
                (input_file, event, rule, processed_for_server, output_file) = self.transport_queue[server].peek()
                self.lock.release()

                # Derive the action from the event.
                if event == FSMonitor.DELETED:
                    action = Transporter.DELETE
                elif event == FSMonitor.CREATED or event == FSMonitor.MODIFIED:
                    action = Transporter.ADD_MODIFY
                elif event == Arbitrator.DELETE_OLD_FILE:
                    # TRICKY: if the event is neither of DELETED, CREATED, nor
                    # MODIFIED, which everywhere else in the arbitrator it
                    # should be, then it must be the special case of a file
                    # that has been modified and already transported, but the
                    # old file must still be deleted. Hence we map this event
                    # to the Transporter's DELETE action.
                    action = Transporter.DELETE
                else:
                    raise Exception("Non-existing event set.")

                # Get the additional settings from the rule.
                dst_parent_path = ""
                if rule["destinations"][server].has_key("path"):
                    dst_parent_path = rule["destinations"][server]["path"]

                (id, place_in_queue, transporter) = self.__get_transporter(server)
                if not transporter is None:
                    # A transporter is available!
                    # Transport queue -> Transporter -> transporter_callback -> db queue.
                    self.lock.acquire()
                    (input_file, event, rule, processed_for_server, output_file) = self.transport_queue[server].get()
                    self.lock.release()

                    # Create curried callbacks so we can pass additional data
                    # to the transporter callback without passing it to the
                    # transporter itself (which cannot handle sending
                    # additional data to its callback functions).
                    curried_callback = curry(self.transporter_callback,
                                             input_file=input_file,
                                             event=event,
                                             rule=rule,
                                             processed_for_server=processed_for_server,
                                             server=server
                                             )
                    curried_error_callback = curry(self.transporter_error_callback,
                                                   input_file=input_file,
                                                   event=event
                                                   )


                    # Calculate src and dst for the file.
                    # - The src is the output file of the processor.
                    # - The dst is the output file, but its source parent path
                    #   (the working directory or its source root path) must
                    #   be stripped and the destination parent path must be
                    #   prepended.
                    #   e.g.:
                    #     - src                         -> dst
                    #     - /htdocs/mysite/dir/the_file -> dir/the_file
                    #     - /tmp/dir/the_file           -> dir/the_file
                    src = output_file
                    relative_paths = [WORKING_DIR, self.config.sources[rule["source"]]["scan_path"]]
                    dst = self.__calculate_transporter_dst(output_file, dst_parent_path, relative_paths)

                    # Start the transport.
                    transporter.sync_file(src, dst, action, curried_callback, curried_error_callback)

                    self.logger.info("Transport queue: '%s' to transfer to server '%s' with transporter #%d (of %d), place %d in the queue." % (output_file, server, id + 1, len(self.transporters[server]), place_in_queue))
                else:
                    self.logger.debug("Transporting: no more transporters are available for server '%s'." % (server))
                    break

                processed += 1


    def __process_db_queue(self):
        processed = 0

        while processed < QUEUE_PROCESS_BATCH_SIZE and self.db_queue.qsize() > 0:
            # DB queue -> database.
            self.lock.acquire()
            (input_file, event, rule, processed_for_server, output_file, transported_file, url, server) = self.db_queue.get()
            self.lock.release()

            # Commit the result to the database.            
            remove_server_from_remaining_transporters = True
            transported_file_basename = os.path.basename(output_file)
            if event == FSMonitor.CREATED:
                try:
                    self.dbcur.execute("INSERT INTO synced_files VALUES(?, ?, ?, ?)", (input_file, transported_file_basename, url, server))
                    self.dbcon.commit()
                except sqlite3.IntegrityError, e:
                    self.logger.critical("Database integrity error: %s. Duplicate key: input_file = '%s', server = '%s'." % (e, input_file, server))
            elif event == FSMonitor.MODIFIED:
                self.dbcur.execute("SELECT COUNT(*) FROM synced_files WHERE input_file=? AND server=?", (input_file, server))
                if self.dbcur.fetchone()[0] > 0:

                    # Look up the transported file's base name. This
                    # might be different from the input file's base
                    # name due to processing.
                    self.dbcur.execute("SELECT transported_file_basename FROM synced_files WHERE input_file=? AND server=?", (input_file, server))
                    old_transport_file_basename = self.dbcur.fetchone()[0]

                    # Update the transported_file_basename and url fields for
                    # the input_file that has been transported.
                    self.dbcur.execute("UPDATE synced_files SET transported_file_basename=?, url=? WHERE input_file=? AND server=?", (transported_file_basename, url, input_file, server))
                    self.dbcon.commit()
                    
                    # If a file was modified that had already been synced
                    # before and now has a different basename for the
                    # transported file than before, we first have to delete
                    # the old transported file before all work is done.
                    # remove_server_from_remaining_transporters is set to
                    # False for this case.
                    if old_transport_file_basename != transported_file_basename:
                        remove_server_from_remaining_transporters = False

                        # The output file that should be transported only
                        # exists on the server. So we create a filename that
                        # is the same as the old transported file.
                        fake_output_file = os.path.join(os.path.dirname(input_file), old_transport_file_basename)
                        # Change the event to Arbitrator.DELETE_OLD_FILE,
                        # which __process_transport_queues() will recognize
                        # and perform a deletion for. After the transporter
                        # callback gets called, this pseudo-event will end up
                        # in __process_db_queue() (this method) once again and
                        # will change the event back the original,
                        # FSMonitor.MODIFIED, so we can remove it from the
                        # 'files_in_pipeline' persistent list.
                        pseudo_event = Arbitrator.DELETE_OLD_FILE
                        # Queue the transport (deletion), but jump the queue!.
                        self.transport_queue[server].jump((input_file, pseudo_event, rule, Arbitrator.PROCESSED_FOR_ANY_SERVER, fake_output_file))
                        self.logger.info("DB queue -> transport queue (jumped): '%s' to delete its old transported file '%s' on server '%s'." % (input_file, old_transport_file_basename, server))
                else:
                    self.dbcur.execute("INSERT INTO synced_files VALUES(?, ?, ?, ?)", (input_file, transported_file_basename, url, server))
                    self.dbcon.commit()
            elif event == FSMonitor.DELETED:
                self.dbcur.execute("DELETE FROM synced_files WHERE input_file=? AND server=?", (input_file, server))
                self.dbcon.commit()
            elif event == Arbitrator.DELETE_OLD_FILE:
                # This is a pseudo-event. See the comments for the
                # FSMonitor.MODIFIED-branch for details.
                event = FSMonitor.MODIFIED
            else:
                raise Exception("Non-existing event set.")

            self.logger.debug("DB queue -> 'synced files' DB: '%s' (URL: '%s')." % (input_file, url))

            key = input_file + str(event) + repr(rule)

            # Remove this server from the 'remaining transporters' list for
            # this input file/event/rule.
            if remove_server_from_remaining_transporters:
                # TRICKY: This is wrapped in a try/except block because it's
                # possible that for example multiple "CREATED" and "DELETED"
                # events on the same file have been logged, which are then
                # potentially being synced at the same time. It is then
                # possible that one instance of the file syncing process has
                # already synced to one server and another instance has done
                # the same, but later. Because the key here is not universally
                # unique, but merely on the input file, event and rule,
                # collisions are possible.
                # Yes, this is a design flaw in the current version. It cannot
                # cause any problems though, merely duplicate work in highly
                # active environments.
                try:
                    self.remaining_transporters[key].remove(server)
                except ValueError, e:
                    pass

            # Only remove the file from the pipeline if no transporters are
            # remaining.
            if len(self.remaining_transporters[key]) == 0:
                # Delete the output file, but only if it's different from the
                # input file.
                touched = event == FSMonitor.CREATED or event == FSMonitor.MODIFIED
                if touched and not input_file == output_file and os.path.exists(output_file):
                    os.remove(output_file)

                # Syncing is done for this file, now check if the file should
                # be deleted from the source (except when it was a deletion
                # that has been synced, then a deletion of the source file
                # does not make sense, of course).
                for rule in self.rules:
                    if event != FSMonitor.DELETED:
                        if rule["deletionDelay"] is None:
                            self.logger.debug("Not going to delete '%s'." % (input_file))
                        elif rule["deletionDelay"] > 0:
                            self.lock.acquire()
                            self.files_to_delete.append((input_file, time.time() + rule["deletionDelay"]))
                            self.logger.warning("Scheduled '%s' for deletion in %d seconds, as per the '%s' rule." % (input_file, rule["deletionDelay"], rule["label"]))
                            self.lock.release()
                        else:
                            if os.path.exists(input_file):
                                os.remove(input_file)
                            self.logger.warning("Deleted '%s' as per the '%s' rule." % (input_file, rule["label"]))

                # The file went all the way through the pipeline, so now it's safe
                # to remove it from the persistent 'files_in_pipeline' list.
                self.lock.acquire()
                self.files_in_pipeline.remove((input_file, event))
                self.lock.release()
                self.logger.warning("Synced: '%s' (%s)." % (input_file, FSMonitor.EVENTNAMES[event]))

        processed += 1


    def __process_files_to_delete(self):
        processed = 0

        current_time = time.time()

        # Get a list of all files that can be deleted *now*
        if len(self.files_to_delete) > 0:
            files_to_delete_now = []
            self.lock.acquire()
            for (input_file, deletion_time) in self.files_to_delete:
                if deletion_time <= current_time:
                    files_to_delete_now.append((input_file, deletion_time))
                    # Stop when we reach the batch size.
                    if len(files_to_delete_now) == QUEUE_PROCESS_BATCH_SIZE:
                        break
            self.lock.release()

            # Delete files and remove them from the persistent list.
            for (input_file, deletion_time) in files_to_delete_now:
                if os.path.exists(input_file):
                    os.remove(input_file)

                self.lock.acquire()
                self.files_to_delete.remove((input_file, deletion_time))
                self.lock.release()

                self.logger.warning("Deleted '%s', which was scheduled for deletion %d seconds ago." % (input_file, current_time - deletion_time))

                processed += 1


    def __process_retry_queue(self):
        processed = 0

        while processed < QUEUE_PROCESS_BATCH_SIZE and self.retry_queue.qsize() > 0:
            # Retry queue -> failed files list.
            # And remove from files in pipeline.
            self.lock.acquire()
            (input_file, event) = self.retry_queue.get()
            # It's possible that the file is already in the failed_files
            # persistent list or in the pipeline queue (if it is being retried
            # already) if it is being processed per server and now a second
            # (or third or ...) processor is requesting a retry.
            if (input_file, event) not in self.failed_files and (input_file, event) not in self.pipeline_queue:
                self.failed_files.append((input_file, event))
                already_in_failed_files = False
            else:
                already_in_failed_files = True
            self.files_in_pipeline.remove((input_file, event))
            self.lock.release()

            # Log.
            if not already_in_failed_files:
                self.logger.warning("Retry queue -> 'failed_files' persistent list: '%s'. Retrying later." % (input_file))
            else:
                self.logger.warning("Retry queue -> 'failed_files' persistent list: '%s'. File already being retried later." % (input_file))
            processed += 1


    def __allow_retry(self):
        num_failed_files = len(self.failed_files)
        should_retry = self.last_retry + RETRY_INTERVAL < time.time()
        pipeline_queue_almost_empty = self.pipeline_queue < MAX_FILES_IN_PIPELINE
        
        if num_failed_files > 0 and (should_retry or pipeline_queue_almost_empty):
            failed_items = []

            processed = 0
            while processed < QUEUE_PROCESS_BATCH_SIZE and processed < len(self.failed_files):
                item = self.failed_files[processed]
                failed_items.append(item)
                self.pipeline_queue.put(item)
                processed += 1
            
            for item in failed_items:
                self.failed_files.remove(item)

            self.last_retry = time.time()

            # Log.
            self.logger.warning("Moved %d items from the 'failed_files' persistent list into the 'pipeline' persistent queue." % (processed))


    def __get_transporter(self, server):
        """get a transporter; if one is ready for new work, use that one,
        otherwise try to start a new transporter"""

        # Try to find a running transporter that is ready for new work.
        for id in range(0, len(self.transporters[server])):
            transporter = self.transporters[server][id]
            # Don't put more than MAX_TRANSPORTER_QUEUE_SIZE files in each
            # transporter's queue.
            if transporter.qsize() <= MAX_TRANSPORTER_QUEUE_SIZE:
                place_in_queue = transporter.qsize() + 1
                return (id, place_in_queue, transporter)

        # Don't run more than the allowed number of simultaneous transporters.
        if not self.transporters_running < MAX_SIMULTANEOUS_TRANSPORTERS:
            return (None, None, None)

        # Don't run more transporters for each server than its "maxConnections"
        # setting allows.
        num_connections = len(self.transporters[server])
        max_connections = self.config.servers[server]["maxConnections"]
        if max_connections == 0 or num_connections < max_connections:
            transporter    = self.__create_transporter(server)
            id             = len(self.transporters[server]) - 1
            # If a transporter was succesfully created, add it to the pool.
            if transporter:
                self.transporters[server].append(transporter)
                transporter.start()
                self.transporters_running += 1
                # Since this transporter was just created, it's obvious that we're
                # first in line.
                place_in_queue = 1
                return (id, 1, transporter)

        return (None, None, None)


    def __create_transporter(self, server):
        """create a transporter for the given server"""

        transporter_name = self.config.servers[server]["transporter"]
        settings = self.config.servers[server]["settings"]
        transporter_class = self._import_transporter(transporter_name)

        # Attempt to create an instance of the transporter.
        try:
            transporter = transporter_class(settings, self.transporter_callback, self.transporter_error_callback, "Arbitrator")
        except ConnectionError, e:
            self.logger.error("Could not start transporter '%s'. Error: '%s'." % (transporter_name, e))
            return False
        else:
            self.logger.warning("Created '%s' transporter for the '%s' server." % (transporter_name, server))

        return transporter


    def __calculate_transporter_dst(self, src, parent_path=None, relative_paths=[]):
        dst = src

        # Strip off any relative paths.
        for relative_path in relative_paths:
            if dst.startswith(relative_path):
                dst = dst[len(relative_path):]

        # Ensure no absolute path is returned, which would make os.path.join()
        # fail.
        dst = dst.lstrip(os.sep)

        # Prepend any possible parent path.
        if not parent_path is None:
            dst = os.path.join(parent_path, dst)

        return dst


    def fsmonitor_callback(self, monitored_path, event_path, event, discovered_through):
        # Map FSMonitor's variable names to ours.
        input_file = event_path

        if CALLBACKS_CONSOLE_OUTPUT:
            print """FSMONITOR CALLBACK FIRED:
                    input_file='%s'
                    event=%d"
                    discovered_through=%s""" % (input_file, event, discovered_through)

        # The file may have already been deleted!
        deleted = event == FSMonitor.DELETED
        touched = event == FSMonitor.CREATED or event == FSMonitor.MODIFIED
        if deleted or (touched and os.path.exists(event_path)):
            # Ignore directories (we cannot test deleted files to see if they
            # are directories, because they obviously don't exist anymore).
            if touched:
                try:
                    if stat.S_ISDIR(os.stat(event_path)[stat.ST_MODE]):
                        return
                except OSError, e:
                    # The file (or directory, we can't be sure at this point)
                    # does no longer exist (despite the os.path.exists() check
                    # above!): it must *just* have been deleted.
                    if e.errno == os.errno.ENOENT:
                        return

            # Map FSMonitor's variable names to ours.
            input_file = event_path

            # Add to discover queue.
            self.lock.acquire()
            self.discover_queue.put((input_file, event))
            self.lock.release()


    def processor_chain_callback(self, input_file, output_file, event, rule, processed_for_server):
        if CALLBACKS_CONSOLE_OUTPUT:
            print """PROCESSOR CHAIN CALLBACK FIRED:
                    input_file='%s'
                    (curried): event=%d
                    (curried): rule='%s'
                    (curried): processed_for_server='%s'
                    output_file='%s'""" % (input_file, event, rule["label"], processed_for_server, output_file)

        # Decrease number of running processor chains.
        self.lock.acquire()
        self.processorchains_running -= 1
        self.lock.release()

        # If the input file was not processed for a specific server, then it
        # should be synced to all destinations. Else, it should only be synced
        # to the server it was processed for.
        if processed_for_server == Arbitrator.PROCESSED_FOR_ANY_SERVER:
            for server in rule["destinations"].keys():
                # Add to transport queue.
                self.lock.acquire()
                self.transport_queue[server].put((input_file, event, rule, processed_for_server, output_file))
                self.lock.release()
            self.logger.info("Process queue -> transport queue: '%s'." % (input_file))
        else:
            # Add to transport queue.
            self.lock.acquire()
            self.transport_queue[processed_for_server].put((input_file, event, rule, processed_for_server, output_file))
            self.lock.release()
            self.logger.info("Process queue -> transport queue: '%s' (processed for server '%s')." % (input_file, processed_for_server))


    def processor_chain_error_callback(self, input_file, event):
        if CALLBACKS_CONSOLE_OUTPUT:
            print """PROCESSOR CHAIN ERROR CALLBACK FIRED:
                    input_file='%s'
                    (curried): event=%d""" % (input_file, event)

        # Add to retry queue.
        self.lock.acquire()
        self.retry_queue.put((input_file, event))
        self.processorchains_running -= 1
        self.lock.release()


    def transporter_callback(self, src, dst, url, action, input_file, event, rule, processed_for_server, server):
        # Map Transporter's variable names to ours.
        output_file      = src
        transported_file = dst

        if CALLBACKS_CONSOLE_OUTPUT:
            print """TRANSPORTER CALLBACK FIRED:
                    (curried): input_file='%s'
                    (curried): event=%d
                    (curried): rule='%s'
                    (curried): processed_for_server='%s'
                    output_file='%s'
                    transported_file='%s'
                    url='%s'
                    server='%s'""" % (input_file, event, rule["label"], processed_for_server, output_file, transported_file, url, server)

        # Add to db queue.
        self.lock.acquire()
        self.db_queue.put((input_file, event, rule, processed_for_server, output_file, transported_file, url, server))
        self.lock.release()

        self.logger.info("Transport queue -> DB queue: '%s' (server: '%s')." % (input_file, server))


    def transporter_error_callback(self, src, dst, action, input_file, event):
        if CALLBACKS_CONSOLE_OUTPUT:
            print """TRANSPORTER ERROR CALLBACK FIRED:
                    (curried): input_file='%s'
                    (curried): event=%d""" % (input_file, event)

        self.retry_queue.put((input_file, event))


    def stop(self):
        # Everybody dies only once.
        self.lock.acquire()
        if self.die:
            self.lock.release()
            return
        self.lock.release()

        # Die.
        self.logger.warning("Signaling to stop.")
        self.lock.acquire()
        self.die = True
        self.lock.release()


    def clean_up_working_dir(self):
        for root, dirs, files in os.walk(WORKING_DIR, topdown=False):
            for name in files:
                os.remove(os.path.join(root, name))
            for name in dirs:
                os.rmdir(os.path.join(root, name))
        self.logger.info("Cleaned up the working directory '%s'." % (WORKING_DIR))


    def _import_processor(self, processor):
        """Imports processor module and class, returns class.

        Input value can be:

        * a full/absolute class path, like
          "MyProcessorPackage.SomeProcessorClass"
        * a class path relative to fileconveyor.processors, like
          "image_optimizer.KeepFilename"
        """
        processor_class = None
        module = None
        alternatives = [processor]
        default_prefix = 'processors.' # Not 'fileconveyor.processors.'!
        if not processor.startswith(default_prefix):
            alternatives.append('%s%s' % (default_prefix, processor))
        for processor_name in alternatives:
            (modulename, classname) = processor_name.rsplit(".", 1)
            try:
                module = __import__(modulename, globals(), locals(), [classname])
            except ImportError:
                pass
        if not module:
            msg = "The processor module '%s' could not be found." % processor
            if len(alternatives) > 1:
                msg = '%s Tried (%s)' % (msg, ', '.join(alternatives))
            self.logger.error(msg)
        else:
            try:
                processor_class = getattr(module, classname)
            except AttributeError:
                self.logger.error("The Processor module '%s' was found, but its Processor class '%s' could not be found."  % (modulename, classname))
        return processor_class


    def _import_transporter(self, transporter):
        """Imports transporter module and class, returns class.

        Input value can be:

        * a full/absolute module path, like
          "MyTransporterPackage.SomeTransporterClass"
        * a module path relative to fileconveyor.transporters, like
          "symlink_or_copy"
        """
        transporter_class = None
        module = None
        alternatives = [transporter]
        default_prefix = 'transporters.transporter_' # Not 'fileconveyor.transporters.transporter_'!
        if not transporter.startswith(default_prefix):
            alternatives.append('%s%s' % (default_prefix, transporter))
        for module_name in alternatives:
            try:
                module = __import__(module_name, globals(), locals(), ["TRANSPORTER_CLASS"], -1)
            except ImportError:
                pass
        if not module:
            msg = "The transporter module '%s' could not be found." % transporter
            if len(alternatives) > 1:
                msg = '%s Tried (%s)' % (msg, ', '.join(alternatives))
            self.logger.error(msg)
        else:
            try:
                classname = module.TRANSPORTER_CLASS
                module = __import__(module_name, globals(), locals(), [classname])
                transporter_class = getattr(module, classname)
            except AttributeError:
                self.logger.error("The Transporter module '%s' was found, but its Transporter class '%s' could not be found."  % (module_name, classname))
        return transporter_class


def run_file_conveyor(restart=False):
    try:
        arbitrator = Arbitrator(os.path.join(FILE_CONVEYOR_PATH, "config.xml"), restart)
    except ArbitratorInitError, e:
        print e.__class__.__name__, e
    except ArbitratorError, e:
        print e.__class__.__name__, e
        del arbitrator
    else:
        t = DaemonThreadRunner(arbitrator, PID_FILE)
        t.start()
        del t
        del arbitrator


if __name__ == '__main__':
    if not RESTART_AFTER_UNHANDLED_EXCEPTION:
        run_file_conveyor()
    else:
        run_file_conveyor()
        # Don't restart File Conveyor, but actually quit it when it's stopped
        # by the user in the console. See DaemonThreadRunner.handle_signal()
        # for details.
        while True and not DaemonThreadRunner.stopped_in_console:
            # Make sure there's always a PID file, even when File Conveyor
            # technically isn't running.
            DaemonThreadRunner.write_pid_file(os.path.expanduser(PID_FILE))
            time.sleep(RESTART_INTERVAL)
            run_file_conveyor(restart=True)

########NEW FILE########
__FILENAME__ = config
"""config.py Parse the daemon config file"""


__author__ = "Wim Leers (work@wimleers.com)"
__version__ = "$Rev$"
__date__ = "$Date$"
__license__ = "GPL"


import os
import os.path
import xml.etree.ElementTree as etree
from xml.parsers.expat import ExpatError
import re
import logging

from filter import *


# Define exceptions.
class ConfigError(Exception): pass
class SourceDoesNotExist(ConfigError): pass


class Config(object):
    def __init__(self, parent_logger):
        self.ignored_dirs = []
        self.sources      = {}
        self.servers      = {}
        self.rules        = {}
        self.logger       = logging.getLogger(".".join([parent_logger, "Config"]))
        self.errors       = 0

        self.source_name_regex = re.compile('^[a-zA-Z0-9-_]*$', re.UNICODE)


    @classmethod
    def __ensure_unicode(cls, string):
        # If the string is already in Unicode, there's nothing we need to do.
        if type(string) == type(u'.'):
            return string
        # Otherwise, decode it from UTF-8 (which is config.xml's encoding).
        elif type(string) == type('.'):
            return string.decode('utf-8')
        # Finally, we may not really be receiving a string.
        else:
            return string


    def load(self, filename):
        try:
            doc = etree.parse(filename)
            root = doc.getroot()
            self.logger.info("Parsing sources.")
            self.__parse_sources(root)
            self.logger.info("Parsing servers.")
            self.__parse_servers(root)
            self.logger.info("Parsing rules.")
            self.__parse_rules(root)
        except ExpatError, e:
            self.logger.error("The XML file is invalid; %s." % (e))
            self.errors += 1
        return self.errors


    def __parse_sources(self, root):
        sources = root.find("sources")

        # Globally ignored directories.
        self.ignored_dirs = Config.__ensure_unicode(sources.get("ignoredDirs", ""))

        # If set, validate the globally ignored directories by trying to
        # create a Filter object for it.
        if self.ignored_dirs != "":
            try:
                conditions = {"ignoredDirs" : self.ignored_dirs}
                f = Filter(conditions)
            except FilterError, e:
                message = e.message
                if message == "":
                    message = "none"
                self.logger.error("Invalid ignoredDirs attribute for the sources node: %s (details: \"%s\")." % (e.__class__.__name__, message))
                self.errors += 1

        for source in sources:
            name          = Config.__ensure_unicode(source.get("name"))
            scan_path     = Config.__ensure_unicode(source.get("scanPath"))
            document_root = Config.__ensure_unicode(source.get("documentRoot"))
            base_path     = Config.__ensure_unicode(source.get("basePath"))

            self.sources[name] = {
                "name"          : name,
                "scan_path"     : scan_path,
                "document_root" : document_root,
                "base_path"     : base_path,
            }

            # Validate.
            if not self.source_name_regex.match(name):
                self.logger.error("The name '%s' for a source is invalid. Only use alphanumeric characters, the dash and the underscore." % (name))
                self.errors += 1
            if scan_path is None:
                self.logger.error("The %s scan path is not configured." % (name))
                self.errors += 1                
            elif not os.path.exists(scan_path):
                self.logger.error("The %s scan path ('%s') does not exist." % (name, scan_path))
                self.errors += 1
            if not document_root is None and not os.path.exists(document_root):
                self.logger.error("The %s document root ('%s') does not exist." % (name, document_root))
                self.errors += 1
            if not base_path is None and (base_path[0] != "/" or base_path[-1] != "/"):
                self.logger.error("The %s base path ('%s') is invalid. It should have both leading and trailing slashes." % (name, base_path))
                self.errors += 1
            if not document_root is None and not base_path is None:
                site_path = os.path.join(document_root, base_path[1:])
                if not os.path.exists(site_path):
                    self.logger.warning("The %s site path (the base path within the document root, '%s') does not exist. It is assumed that this is a logical base path then, due to usage of symbolic links." % (name, site_path))


    def __parse_servers(self, root):
        servers_node = root.find("servers")
        for server_node in servers_node:
            settings = {}
            name           = Config.__ensure_unicode(server_node.get("name"))
            transporter    = Config.__ensure_unicode(server_node.get("transporter"))
            maxConnections = server_node.get("maxConnections", 0)
            for setting in server_node.getchildren():
                settings[setting.tag] = Config.__ensure_unicode(setting.text)
            self.servers[name] = {
                "maxConnections" : int(maxConnections),
                "transporter"    : transporter,
                "settings"       : settings,
            }


    def __parse_rules(self, root):
        rules_node = root.find("rules")
        for rule_node in rules_node:
            for_source    = Config.__ensure_unicode(rule_node.get("for"))
            label         = Config.__ensure_unicode(rule_node.get("label"))
            deletion_delay = rule_node.get("fileDeletionDelayAfterSync", None)
            if deletion_delay is not None:
                deletion_delay = int(deletion_delay)

            # 1: filter (optional)
            conditions = None
            filter_node = rule_node.find("filter")
            if not filter_node is None:
                conditions = self.__parse_filter(filter_node, label)

            # 2: processorChain (optional)
            processor_chain = None
            processor_chain_node = rule_node.find("processorChain")
            if not processor_chain_node is None:
                processor_chain = self.__parse_processor_chain(processor_chain_node, label)

            # 3: destinations (required)
            destinations = {}
            destinations_node = rule_node.find("destinations")
            if destinations_node is None or len(destinations_node) == 0:
                self.logger.error("In rule '%s': at least one destination must be configured." % (label))
                self.errors += 1
            else:
                for destination_node in destinations_node:
                    destination = self.__parse_destination(destination_node, label)
                    destinations[destination["server"]] = {"path" : destination["path"]}

            if not self.rules.has_key(for_source):
                self.rules[for_source] = []
            self.rules[for_source].append({
                "label"           : Config.__ensure_unicode(label),
                "deletionDelay"   : deletion_delay,
                "filterConditions": conditions,
                "processorChain"  : processor_chain,
                "destinations"    : destinations,
            })


    def __parse_filter(self, filter_node, rule_label):
        conditions = {}
        for condition_node in filter_node.getchildren():
            if condition_node.tag == "size":
                conditions[condition_node.tag] = {
                    "conditionType" : Config.__ensure_unicode(condition_node.get("conditionType")),
                    "treshold"      : Config.__ensure_unicode(condition_node.text),
                }
            else:
                conditions[condition_node.tag] = Config.__ensure_unicode(condition_node.text)

        # Validate the conditions by trying to create a Filter object with it.
        try:
            f = Filter(conditions)
        except FilterError, e:
            message = e.message
            if message == "":
                message = "none"
            self.logger.error("In rule '%s': invalid filter condition: %s (details: \"%s\")." % (rule_label, e.__class__.__name__, message))
            self.errors += 1

        return conditions


    def __parse_processor_chain(self, processor_chain_node, rule_label):
        processor_chain = []
        for processor_node in processor_chain_node.getchildren():
            processor_chain.append(Config.__ensure_unicode(processor_node.get("name")))
        return processor_chain


    def __parse_destination(self, destination_node, rule_label):
        destination = {}
        destination["server"] = Config.__ensure_unicode(destination_node.get("server"))
        destination["path"]   = Config.__ensure_unicode(destination_node.get("path", None))

        # Validate "server" attribute.
        if destination["server"] is None:
            self.logger.error("In rule '%s': invalid destination: 'server' attribute is missing." % (rule_label))
            self.errors += 1
        elif destination["server"] not in self.servers.keys():
            self.logger.error("In rule '%s': invalid destination: 'server' attribute references a non-existing server." % (rule_label))
            self.errors += 1

        return destination


if __name__ == '__main__':
    import logging.handlers

    # Set up logging.
    logger = logging.getLogger("test")
    logger.setLevel(logging.DEBUG)
    handler = logging.handlers.RotatingFileHandler("config.log")
    logger.addHandler(handler)

    # Use the Config class.
    config = Config("test")
    config.load("config.xml")
    print "ignoredDirs", config.ignored_dirs
    print "sources", config.sources
    print "servers", config.servers
    print "rules",   config.rules

########NEW FILE########
__FILENAME__ = daemon_thread_runner
"""transporter.py Transporter class for daemon"""


__author__ = "Wim Leers (work@wimleers.com)"
__version__ = "$Rev$"
__date__ = "$Date$"
__license__ = "GPL"


import os
import os.path
import signal
import time


class DaemonThreadRunner(object):
    """runs a thread as a daemon and provides a PID file through which you can
    kill the daemon (kill -TERM `cat pidfile`)"""

    pidfile_check_interval = 60
    pidfile_permissions    = 0600

    stopped_in_console = False

    def __init__(self, thread, pidfile):
        self.thread             = thread
        self.running            = False
        self.pidfile            = os.path.expanduser(pidfile)
        self.last_pidfile_check = 0

        # Configure signal handler.
        signal.signal(signal.SIGINT,  self.handle_signal)
        signal.signal(signal.SIGTSTP, self.handle_signal)
        signal.signal(signal.SIGTERM, self.handle_signal)


    def start(self):
        self.write_pid_file(self.pidfile)

        # Start the daemon thread.
        self.running = True
        self.thread.setDaemon(True)
        self.thread.start()

        # While running, keep the PID file updated and sleep.
        while self.running:
            self.update_pid_file()
            time.sleep(1)

        # Remove the PID file.
        if os.path.isfile(self.pidfile):
            os.remove(self.pidfile)


    def handle_signal(self, signalNumber, frame):
        # Ctrl+C = SIGINT, Ctrl+X = SIGTSTP; these are entered by the user
        # who's looking at File Conveyor's activity in the console. Hence,
        # these should definitely stop the process and not allow it to restart.
        if signalNumber != signal.SIGTERM:
            DaemonThreadRunner.stopped_in_console = True
        self.thread.stop()
        self.thread.join()
        self.running = False


    @classmethod
    def write_pid_file(cls, pidfile):
        pid = os.getpid()
        open(pidfile, 'w+').write(str(pid))
        os.chmod(pidfile, cls.pidfile_permissions)


    def update_pid_file(self):
        # Recreate the file when it is deleted.
        if not os.path.isfile(self.pidfile):
            self.write_pid_file(self.pidfile)

        # Update the file every interval.
        if self.last_pidfile_check + self.pidfile_check_interval < time.time():
            self.write_pid_file(self.pidfile)
            self.last_pidfile_check = time.time()

########NEW FILE########
__FILENAME__ = django_settings
# Dummy settings for `django-storages`.
MEDIA_URL=''
MEDIA_ROOT=''
# `backends/ftp.py`
FTP_STORAGE_LOCATION=''
# `backends/sftp.py`
SFTP_STORAGE_HOST=''
# django-cumulus
#CUMULUS['USERNAME'] = '';
#CUMULUS['CUMULUS_API_KEY'] = '';
#CUMULUS['CONTAINER'] = '';
CUMULUS_API_KEY = '';
CUMULUS_USERNAME = '';
CUMULUS_CONTAINER = '';

########NEW FILE########
__FILENAME__ = filter
"""filter.py Filter class for daemon"""


__author__ = "Wim Leers (work@wimleers.com)"
__version__ = "$Rev$"
__date__ = "$Date$"
__license__ = "GPL"


from sets import Set, ImmutableSet
import re
import types
import os
import os.path
import stat


# Define exceptions.
class FilterError(Exception): pass
class InvalidConditionError(FilterError): pass
class MissingConditionError(FilterError): pass
class InvalidPathsConditionError(InvalidConditionError): pass
class InvalidExtensionsConditionError(InvalidConditionError): pass
class InvalidIgnoredDirsConditionError(InvalidConditionError): pass
class InvalidPatternConditionError(InvalidConditionError): pass
class InvalidSizeConditionError(InvalidConditionError): pass
class MatchError(FilterError): pass


class Filter(object):
    """filter filepaths based on path, file extensions, ignored directories, file pattern and file size"""

    valid_conditions = ImmutableSet(["paths", "extensions", "ignoredDirs", "pattern", "size"])
    required_sizeconditions = ImmutableSet(["conditionType", "treshold"])
    # Prevent forbidden characters in filepaths!
    # - Mac OS X: :
    # - Linux: /
    # - Windows: * " / \ [ ] : ; | = , < >
    # It's clear that if your filepaths are valid on Windows, they're valid
    # anywhere. So we go with that.
    forbidden_characters = {
        "paths"       : '\*"\[\]:;\|=,<>',      # / and \ are allowed
        "extensions"  : '\*"/\\\[\]:;\|=,<>\.', # / and \ and . are disallowed
        "ignoredDirs" : '\*"/\\\[\]:;\|=,<>',   # / and \ are disallowed
    }
    patterns = {
        "paths"       : re.compile('^(?:([^' + forbidden_characters["paths"]       + ']+):)*[^' + forbidden_characters["paths"]       + ']+$', re.UNICODE),
        "extensions"  : re.compile('^(?:([^' + forbidden_characters["extensions"]  + ']+):)*[^' + forbidden_characters["extensions"]  + ']+$', re.UNICODE),
        "ignoredDirs" : re.compile('^(?:([^' + forbidden_characters["ignoredDirs"] + ']+):)*[^' + forbidden_characters["ignoredDirs"] + ']+$', re.UNICODE),
    }


    def __init__(self, conditions = None):
        self.initialized = False
        self.conditions = {}
        self.pattern = None
        if conditions is not None:
            self.set_conditions(conditions)


    def set_conditions(self, conditions):
        """Validate and then set the conditions of this Filter"""
        present_conditions = Set(conditions.keys())

        # Ensure all required conditions are set.
        if len(conditions) == 0:
            raise MissingConditionError("You must set at least one condition.")

        # Ensure only valid conditions are set.
        if len(present_conditions.difference(self.__class__.valid_conditions)):
            raise InvalidConditionError

        # Validate conditions. This may trigger exceptions, which should be
        # handled by the caller.
        self.__validate_conditions(conditions)
        
        # The conditions passed all validation tests: store it.
        self.conditions = conditions

        # Precompile the pattern condition, if there is one.
        if (self.conditions.has_key("pattern")):
            self.pattern = re.compile(self.conditions["pattern"], re.UNICODE)

        self.initialized = True

        return True


    def __validate_conditions(self, conditions):
        """Validate a given set of conditions"""

        # The paths condition must contain paths separated by colons.
        if conditions.has_key("paths"):
            if not self.__class__.patterns["paths"].match(conditions["paths"]):
                raise InvalidPathsConditionError

        # The extensions condition must contain extensions separated by colons.
        if conditions.has_key("extensions"):
            if not self.__class__.patterns["extensions"].match(conditions["extensions"]):
                raise InvalidExtensionsConditionError

        # The ignoredDirs condition must contain dirnames separated by colons.
        if conditions.has_key("ignoredDirs"):
            if not self.__class__.patterns["ignoredDirs"].match(conditions["ignoredDirs"]):
                raise InvalidIgnoredDirsConditionError

        # If a pattern condition is set, ensure that it's got a valid regular
        # expression.
        if conditions.has_key("pattern"):
            if conditions["pattern"] is None:
                raise InvalidPatternConditionError
            try:
                re.compile(conditions["pattern"], re.UNICODE)
            except re.error:
                raise InvalidPatternConditionError

        # If a size condition is set, ensure that it's got both a size
        # condition type and a treshold. And both of them must be valid.
        if conditions.has_key("size"):
            size = conditions["size"]
            if len(self.__class__.required_sizeconditions.difference(size.keys())):
                raise InvalidSizeConditionError, "The 'size' condition misses either of 'conditionType' and 'treshold'"
            if size["conditionType"] != "minimum" and size["conditionType"] != "maximum":
                raise InvalidSizeConditionError, "The 'size' condition has an invalid 'conditionType', valid values are 'maximum' and 'minimum'"
            try:
                size["treshold"] = int(size["treshold"])
            except ValueError:
                raise InvalidSizeConditionError, "The 'size' condition has an invalid 'treshold', only integer values are valid'"


    def matches(self, filepath, statfunc = os.stat, file_is_deleted = False):
        """Check if the given filepath matches the conditions of this Filter

        This function performs the different checks in an order that is
        optimized for speed: the conditions that are most likely to reduce
        the chance of a match are performed first.

        """

        if not self.initialized:
            return False

        match = True
        (root, ext) = os.path.splitext(filepath)

        # Step 1: apply the paths condition.
        if match and self.conditions.has_key("paths"):
            append_slash = lambda path: path + "/"
            paths = map(append_slash, self.conditions["paths"].split(":"))
            path_found = False
            for path in paths:
                if root.find(path) > -1:
                    path_found = True
                    break
            if not path_found:
                match = False
        
        # Step 2: apply the extensions condition.
        if match and self.conditions.has_key("extensions"):
            ext = ext.lstrip(".")
            if not ext in self.conditions["extensions"].split(":"):
                match = False

        # Step 3: apply the ignoredDirs condition.
        if match and self.conditions.has_key("ignoredDirs"):
            ignored_dirs = Set(self.conditions["ignoredDirs"].split(":"))
            dirs = Set(root.split(os.sep))
            if len(ignored_dirs.intersection(dirs)):
                match = False

        # Step 4: apply the pattern condition.
        if match and self.conditions.has_key("pattern"):
            if not self.pattern.match(filepath):
                match = False

        # Step 5: apply the size condition, except when file_is_deleted is
        # enabled.
        # (If a file is deleted, we can no longer check its size and therefor
        # we allow this to match.)
        if match and self.conditions.has_key("size") and not file_is_deleted:
            size = statfunc(filepath)[stat.ST_SIZE]
            condition_type = self.conditions["size"]["conditionType"]
            treshold       = self.conditions["size"]["treshold"]
            if condition_type == "minimum" and not treshold < size:
                match = False
            elif condition_type == "maximum" and not treshold > size:
                match = False

        return match

########NEW FILE########
__FILENAME__ = filtertest
"""Unit test for filter.py"""


__author__ = "Wim Leers (work@wimleers.com)"
__version__ = "$Rev$"
__date__ = "$Date$"
__license__ = "GPL"


from filter import *
import unittest


class TestConditions(unittest.TestCase):
    def setUp(self):
        self.filter = Filter()

    def testNoConditions(self):
        """Filter should fail when no settings are provided"""
        self.assertRaises(MissingConditionError, self.filter.set_conditions, {})

    def testMinimumConditions(self):
        """Filter should work with at least one condition"""
        self.assertTrue(self.filter.set_conditions, {"paths" : "foo/bar:baz"})
        self.assertTrue(self.filter.set_conditions, {"extensions" : "gif:png"})
        self.assertTrue(self.filter.set_conditions, {"ignoredDirs" : "CVS:.svn"})
        self.assertTrue(self.filter.set_conditions, {"size" : {"treshold" : 1000000}})
        self.assertTrue(self.filter.set_conditions, {"pattern" : "foo/bar"})

    def testInvalidConditions(self):
        """Filter should fail when there is an invalid setting"""
        self.assertRaises(InvalidConditionError, self.filter.set_conditions, {"extensions" : "gif:png", "paths" : "foo/bar:baz", "invalid" : "invalid"})

    def testValidConditions(self):
        """setting filter conditions should return true when all required and no invalid conditions are specified"""
        # The minimal valid filter conditions.
        self.assertTrue(self.filter.set_conditions({"extensions" : "gif:png", "paths" : "foo/bar:baz"}))
        # The maximal valid filter conditions.
        self.assertTrue(self.filter.set_conditions({"extensions" : "gif:png", "paths" : "foo/bar:baz", "ignoredDirs" : ".svn:CVS", "pattern" : "foo/bar", "size" : { "conditionType" : "minimum", "treshold" : 1000000}}))

    def testInvalidPathsCondition(self):
        """Filter should fail when setting an invalid paths filter condition"""
        self.assertRaises(InvalidPathsConditionError, self.filter.set_conditions, {"extensions" : "gif:png", "paths" : "foo:baz>"})
        # Special: / is allowed
        self.assertRaises(InvalidPathsConditionError, self.filter.set_conditions, {"extensions" : "gif:png", "paths" : "foo/bar:baz>"})
        # Special: \ is allowed
        self.assertRaises(InvalidPathsConditionError, self.filter.set_conditions, {"extensions" : "gif:png", "paths" : "foo\\bar:baz>"})

    def testInvalidExtensionsCondition(self):
        """Filter should fail when setting an invalid extensions filter condition"""
        self.assertRaises(InvalidExtensionsConditionError, self.filter.set_conditions, {"extensions" : "<gif:png", "paths" : "foo/bar:baz"})
        # Special: . is disallowed
        self.assertRaises(InvalidExtensionsConditionError, self.filter.set_conditions, {"extensions" : ".gif:png", "paths" : "foo/bar:baz"})
        # Special: / is disallowed
        self.assertRaises(InvalidExtensionsConditionError, self.filter.set_conditions, {"extensions" : "/gif:png", "paths" : "foo/bar:baz"})
        # Special: \ is disallowed
        self.assertRaises(InvalidExtensionsConditionError, self.filter.set_conditions, {"extensions" : "\\gif:png", "paths" : "foo/bar:baz"})
        
    def testInvalidIgnoredDirsCondition(self):
        """Filter should fail when setting an invalid ignoredDirs filter condition"""
        self.assertRaises(InvalidIgnoredDirsConditionError, self.filter.set_conditions, {"extensions" : "gif:png", "paths" : "foo/bar:baz", "ignoredDirs" : ".svn:CVS/"})
        # Special: / is disallowed
        self.assertRaises(InvalidIgnoredDirsConditionError, self.filter.set_conditions, {"extensions" : "gif:png", "paths" : "foo/bar:baz", "ignoredDirs" : ".svn:CVS/"})
        # Special: \ is disallowed
        self.assertRaises(InvalidIgnoredDirsConditionError, self.filter.set_conditions, {"extensions" : "gif:png", "paths" : "foo/bar:baz", "ignoredDirs" : ".svn:\\CVS"})

    def testInvalidPatternCondition(self):
        """Filter should fail when setting an invalid pattern filter condition"""
        self.assertRaises(InvalidPatternConditionError, self.filter.set_conditions, {"extensions" : "gif:png", "paths" : "foo/bar:baz", "pattern" : "foo(bar"})
        self.assertRaises(InvalidPatternConditionError, self.filter.set_conditions, {"extensions" : "gif:png", "paths" : "foo/bar:baz", "pattern" : None})

    def testInvalidSizeCondition(self):
        """Filter should fail when setting an invalid size filter condition"""
        # Missing conditionType
        self.assertRaises(InvalidSizeConditionError, self.filter.set_conditions, {"extensions" : "gif:png", "paths" : "foo/bar:baz", "size" : {"treshold" : 1000000}})
        # Missing treshold
        self.assertRaises(InvalidSizeConditionError, self.filter.set_conditions, {"extensions" : "gif:png", "paths" : "foo/bar:baz", "size" : {"conditionType" : "minimum"}})
        # Invalid conditionType
        self.assertRaises(InvalidSizeConditionError, self.filter.set_conditions, {"extensions" : "gif:png", "paths" : "foo/bar:baz", "size" : {"treshold" : 1000000, "conditionType" : "this is in an invalid condition type"}})
        # Invalid treshold
        self.assertRaises(InvalidSizeConditionError, self.filter.set_conditions, {"extensions" : "gif:png", "paths" : "foo/bar:baz", "size" : {"conditionType" : "minimum", "treshold" : "this is not numeric and therefor invalid"}})

    def testValidSizeCondition(self):
        """'maximum' and 'minimum' are the allowed conditionTypes for the size condition"""
        self.assertTrue(self.filter.set_conditions({"extensions" : "gif:png", "paths" : "foo/bar:baz", "size" : { "conditionType" : "minimum", "treshold" : 1000000}}))
        self.assertTrue(self.filter.set_conditions({"extensions" : "gif:png", "paths" : "foo/bar:baz", "size" : { "conditionType" : "maximum", "treshold" : 1000000}}))
        # Strings should also work and should be converted to integers automatically.
        self.assertTrue(self.filter.set_conditions({"extensions" : "gif:png", "paths" : "foo/bar:baz", "size" : { "conditionType" : "maximum", "treshold" : "1000000"}}))


class TestMatching(unittest.TestCase):
    def testWithoutConditions(self):
        """Ensure matching works properly even when no conditions are set"""
        filter = Filter()
        self.assertFalse(filter.matches('whatever'))

    def testPathsMatches(self):
        """Ensure paths matching works properly"""
        conditions = {
            "paths" : "foo/bar:baz"
        }
        filter = Filter(conditions)
        # Invalid paths.
        self.assertFalse(filter.matches('/a/b/c/d.gif'))
        self.assertFalse(filter.matches('/a/foo/bar.gif'))
        # Valid paths.
        self.assertTrue(filter.matches('/a/b/c/d/e/foo/bar/g.gif'))
        self.assertTrue(filter.matches('/a/baz/c.png'))

    def testExtensionsMatches(self):
        """Ensure extensions matching works properly"""
        conditions = {
            "extensions" : "gif:png",
        }
        filter = Filter(conditions)
        # Invalid extensions.
        self.assertFalse(filter.matches('/a/foo/bar/b.mov'))
        self.assertFalse(filter.matches('/a/baz/c/d/e/f.txt'))
        # Valid extensions.
        self.assertTrue(filter.matches('/a/b/c/d/e/foo/bar/g.gif'))
        self.assertTrue(filter.matches('/a/baz/c.png'))

    def testSimpleMatches(self):
        """Ensure paths/extensions matching works properly"""
        conditions = {
            "extensions" : "gif:png",
            "paths" : "foo/bar:baz"
        }
        filter = Filter(conditions)
        # Invalid extensions, valid paths
        self.assertFalse(filter.matches('/a/foo/bar/b.mov'))
        self.assertFalse(filter.matches('/a/baz/c/d/e/f.txt'))
        # Invalid paths, valid extensions
        self.assertFalse(filter.matches('/a/b.png'))
        self.assertFalse(filter.matches('/a/b/c/d/e/f.gif'))
        # Both invalid extensions and paths
        self.assertFalse(filter.matches('/a/b.rar'))
        self.assertFalse(filter.matches('/a/b/c/d/e/f.avi'))
        # Both valid extensions and paths
        self.assertTrue(filter.matches('/a/b/c/d/e/foo/bar/g.gif'))
        self.assertTrue(filter.matches('/a/baz/c.png'))
        # Tricky one: the path seems to match, but is part of the filename and
        # therefor it doesn't match!
        self.assertFalse(filter.matches('foo/bar.gif'))
        self.assertFalse(filter.matches('baz.png'))

    def testIgnoredDirsMatches(self):
        """Ensure ignoredDirs matching works properly"""
        conditions = {
            "extensions" : "gif:png",
            "paths" : "foo/bar:baz",
            "ignoredDirs" : ".svn:CVS",
        }
        filter = Filter(conditions)
        # Contains ignored dirs
        self.assertFalse(filter.matches('/a/foo/bar/.svn/b.gif'))
        self.assertFalse(filter.matches('/a/baz/CVS/d/e/f.png'))
        # Doesn't contain ignored dirs
        self.assertTrue(filter.matches('/a/b/c/d/e/foo/bar/g.gif'))
        self.assertTrue(filter.matches('/a/baz/c.png'))
    
    def testPatternMatches(self):
        """Ensure pattern matching works properly"""
        conditions = {
            "paths" : "foo/bar:baz",
            "pattern" : ".*/([a-zA-Z_])+\.[a-zA-Z0-9]{3}$",
        }
        filter = Filter(conditions)
        # Does not match pattern
        self.assertFalse(filter.matches('/a/foo/bar/.svn/b9.gif'))
        self.assertFalse(filter.matches('/a/f.png'))
        # Matches pattern
        self.assertTrue(filter.matches('/a/b/c/d/e/foo/bar/this_one_has_underscores.gif'))
        self.assertTrue(filter.matches('/a/and_this_one_too/baz/c.png'))
    
    def testSizeMatches(self):
        """Ensure size validation works properly"""

        # The matches function only looks at ST_SIZE, which is in the 7th
        # position in the tuple. This lambda function simplifies the rest of
        # this test case.
        fakestatfunc = lambda filesize: (1, 2, 3, 4, 5, 6, filesize)
        # We always use the same filepath.
        filepath = '/a/baz/c.png'

        # Minimum size
        conditions = {
            "extensions" : "gif:png",
            "paths" : "foo/bar:baz",
            "ignoredDirs" : ".svn:CVS",
            "size" : {
                "conditionType" : "minimum",
                "treshold" : 500
            }
        }
        filter = Filter(conditions)
        # Meets minimum size
        statfunc = lambda filepath: fakestatfunc(501L)
        self.assertTrue(filter.matches(filepath, statfunc))
        # Does not meet minimum size
        statfunc = lambda filepath: fakestatfunc(499L)
        self.assertFalse(filter.matches(filepath, statfunc))

        # Maximium size
        conditions["size"]["conditionType"] = "maximum"
        filter.set_conditions(conditions)
        # Meets maximum size
        statfunc = lambda filepath: fakestatfunc(499L)
        self.assertTrue(filter.matches(filepath, statfunc))
        # Does not meet maximum size
        statfunc = lambda filepath: fakestatfunc(500L)
        self.assertFalse(filter.matches(filepath, statfunc))

        # Minimium size
        conditions["size"]["conditionType"] = "minimum"
        filter.set_conditions(conditions)
        # File doesn't exist anymore: size check should be skipped.
        statfunc = lambda filepath: fakestatfunc(0)
        self.assertTrue(filter.matches(filepath, statfunc, True))


if __name__ == "__main__":
    unittest.main()

########NEW FILE########
__FILENAME__ = fsmonitor
"""fsmonitor.py Cross-platform file system monitor

How it works:
- Uses inotify on Linux (kernel 2.6.13 and higher)
- Uses FileSystemWatcher on Windows (TODO)
- Uses FSEvents on Mac OS X (10.5 and higher)
- Falls back to polling

A persistent mode is also supported, in which all metadata is stored in a
database. This allows you to even track changes when your program wasn't
running.

Only FSEvents supports looking back in time. For Linux and Windows this means
that the manual scanning procedure will be used instead until we have caught
up.

To make this class work consistently, less critical features that are only
available for specific file system monitors are abstracted away. And other
features are emulated.
It comes down to the fact that FSMonitor's API is very simple to use and only
supports 5 different events: CREATED, MODIFIED, DELETED, MONITORED_DIR_MOVED
and DROPPED_EVENTS. The last 2 events are only triggered for inotify and
FSEvents.

This implies that the following features are not available through FSMonitor:
- inotify:
  * auto_add: is always assumed to be True (FSEvents has no setting for this)
  * recursive: is always assumed to be True (FSEvents has no setting for this)
  * IN_ACCESS, IN_CLOSE_WRITE, IN_CLOSE_NOWRITE, IN_OPEN, IN_DELETE_SELF and
    IN_IGNORED event aren't supported (FSEvents doesn't support this)
  * IN_UNMOUNT is also not supported because FSEvents' equivalent
    (kFSEventStreamEventFlagUnmount) isn't supported in Python
- FSEvents:
  * sinceWhen: is always set to kFSEventStreamEventIdSinceNow (inotify has no
    setting for this)
  * kFSEventStreamEventFlagMount: is ignored (inotify doesn't support this)
And the following features are emulated:
- FSEvents:
  * inotify's mask, which allows you to listen only to certain events
"""


__author__ = "Wim Leers (work@wimleers.com)"
__version__ = "$Rev$"
__date__ = "$Date$"
__license__ = "GPL"


import platform
import sqlite3
import threading
import Queue
import os
import logging
from pathscanner import PathScanner


# Define exceptions.
class FSMonitorError(Exception): pass


class FSMonitor(threading.Thread):
    """cross-platform file system monitor"""


    # Identifiers for each event.
    EVENTS = {
        "CREATED"             : 0x00000001,
        "MODIFIED"            : 0x00000002,
        "DELETED"             : 0x00000004,
        "MONITORED_DIR_MOVED" : 0x00000008,
        "DROPPED_EVENTS"      : 0x00000016,
    }

    # Will be filled at the end of this .py file.
    EVENTNAMES = {}
    MERGE_EVENTS = {}

    def __init__(self, callback, persistent=False, trigger_events_for_initial_scan=False, ignored_dirs=[], dbfile="fsmonitor.db", parent_logger=None):
        self.persistent                      = persistent
        self.trigger_events_for_initial_scan = trigger_events_for_initial_scan
        self.monitored_paths                 = {}
        self.dbfile                          = dbfile
        self.dbcon                           = None
        self.dbcur                           = None
        self.pathscanner                     = None
        self.ignored_dirs                    = ignored_dirs
        self.callback                        = callback
        self.lock                            = threading.Lock()
        self.add_queue                       = Queue.Queue()
        self.remove_queue                    = Queue.Queue()
        self.die                             = False
        if parent_logger is None:
            parent_logger = ""
        self.logger                          = logging.getLogger(".".join([parent_logger, "FSMonitor"]))
        threading.Thread.__init__(self, name="FSMonitorThread")


    def run(self):
        """start the file system monitor (starts a separate thread)"""
        raise NotImplemented


    def add_dir(self, path, event_mask):
        """add a directory to monitor"""
        self.lock.acquire()
        self.add_queue.put((path, event_mask))
        self.lock.release()


    def __add_dir(self, path, event_mask):
        raise NotImplemented


    def remove_dir(self, path):
        """stop monitoring a directory"""
        self.lock.acquire()
        self.remove_queue.put(path)
        self.lock.release()
        self.logger.info("Queued '%s' to stop being watched.")


    def __remove_dir(self, path):
        raise NotImplemented


    def generate_missed_events(self, path, event_mask=None):
        """generate the missed events for a persistent DB"""
        self.logger.info("Generating missed events for '%s' (event mask: %s)." % (path, event_mask))
        for event_path, result in self.pathscanner.scan_tree(path):
            self.trigger_events_for_pathscanner_result(path, event_path, result, "generate_missed_events", event_mask)
        self.logger.info("Done generating missed events for '%s' (event mask: %s)." % (path, event_mask))


    def stop(self):
        """stop the file system monitor (stops the separate thread)"""
        raise NotImplemented


    def purge_dir(self, path):
        """purge the metadata for a monitored directory
        
        Only possible if this is a persistent DB.
        """
        if self.persistent:
            self.pathscanner.purge_path(path)
            self.logger.info("Purged information for monitored path '%s'." % (path))


    def trigger_event(self, monitored_path, event_path, event, discovered_through):
        """trigger one of the standardized events"""
        if callable(self.callback):
            self.logger.info("Detected '%s' event for '%s' through %s (for monitored path '%s')." % (FSMonitor.EVENTNAMES[event], event_path, discovered_through, monitored_path))
            self.callback(monitored_path, event_path, event, discovered_through)


    def setup(self):
        """set up the database and pathscanner"""
        # Database.
        if self.dbcur is None:
            self.dbcon = sqlite3.connect(self.dbfile)
            self.dbcon.text_factory = unicode # This is the default, but we set it explicitly, just to be sure.
            self.dbcur = self.dbcon.cursor()
        # PathScanner.
        if self.persistent == True and self.dbcur is not None:
            self.pathscanner = PathScanner(self.dbcon, self.ignored_dirs, "pathscanner")


    def trigger_events_for_pathscanner_result(self, monitored_path, event_path, result, discovered_through=None, event_mask=None):
        """trigger events for pathscanner result"""
        if event_mask is None:
            event_mask = self.monitored_paths[monitored_path].event_mask
        if event_mask & FSMonitor.CREATED:
            for filename in result["created"]:
                self.trigger_event(monitored_path, os.path.join(event_path, filename), self.CREATED, discovered_through)
        if event_mask & FSMonitor.MODIFIED:
            for filename in result["modified"]:
                self.trigger_event(monitored_path, os.path.join(event_path, filename), self.MODIFIED, discovered_through)
        if event_mask & FSMonitor.DELETED:
            for filename in result["deleted"]:
                self.trigger_event(monitored_path, os.path.join(event_path, filename), self.DELETED, discovered_through)


    def is_in_ignored_directory(self, path):
        """checks if the given path is in an ignored directory"""
        dirs = os.path.split(path)
        for dir in dirs:
            if dir in self.ignored_dirs:
                return True
        return False


class MonitoredPath(object):
    """A simple container for all metadata related to a monitored path"""
    def __init__(self, path, event_mask, fsmonitor_ref=None):
        self.path = path
        self.event_mask = event_mask
        self.fsmonitor_ref = fsmonitor_ref
        self.monitoring = False


def __get_class_reference(modulename, classname):
    """get a reference to a class"""
    module = __import__(modulename, globals(), locals(), [classname])
    class_reference = getattr(module, classname)
    return class_reference


def get_fsmonitor():
    """get the FSMonitor for the current platform"""
    system = platform.system()
    if system == "Linux":
        kernel = platform.release().split(".")
        # Available in Linux kernel 2.6.13 and higher.
        if int(kernel[0]) == 2 and int(kernel[1]) == 6 and kernel[2][:2] >= 13:
            return __get_class_reference("fsmonitor_inotify", "FSMonitorInotify")
    elif system == "Windows":
        # See:
        # - http://timgolden.me.uk/python/win32_how_do_i/watch_directory_for_changes.html
        # - http://code.activestate.com/recipes/156178/
        # - http://stackoverflow.com/questions/339776/asynchronous-readdirectorychangesw
        pass
    elif system == "Darwin":
        (release, version_info, machine) = platform.mac_ver()
        major = release.split(".")[1]
        # Available in Mac OS X 10.5 and higher.
        if (major >= 5):
            return __get_class_reference("fsmonitor_fsevents", "FSMonitorFSEvents")

    # Default to a polling mechanism
    return __get_class_reference("fsmonitor_polling", "FSMonitorPolling")


# Make EVENTS' members directly accessible through the class dictionary. Also
# fill the FSMonitor.EVENTNAMES dictionary.
for name, mask in FSMonitor.EVENTS.iteritems():
    setattr(FSMonitor, name, mask)
    FSMonitor.EVENTNAMES[mask] = name

# Fill the FSMonitor.MERGE_EVENTS nested dictionary.
# Key at level 1: old event. Key at level 2: new event. Value: merged event.
# A value (merged event) of None means that the events have canceled each
# other out, i.e. that nothing needs to happen (this is only the case when a
# file is deleted immediately after it has been created).
# Some of these combinations (marked with a #!) should not logically happen,
# but all possible cases are listed anyway, for maximum robustness. They may
# still happen due to bugs in the operating system's API, for example.
FSMonitor.MERGE_EVENTS[FSMonitor.CREATED] = {}
FSMonitor.MERGE_EVENTS[FSMonitor.CREATED][FSMonitor.CREATED]   = FSMonitor.CREATED  #!
FSMonitor.MERGE_EVENTS[FSMonitor.CREATED][FSMonitor.MODIFIED]  = FSMonitor.CREATED
FSMonitor.MERGE_EVENTS[FSMonitor.CREATED][FSMonitor.DELETED]   = None
FSMonitor.MERGE_EVENTS[FSMonitor.MODIFIED] = {}
FSMonitor.MERGE_EVENTS[FSMonitor.MODIFIED][FSMonitor.CREATED]  = FSMonitor.MODIFIED #!
FSMonitor.MERGE_EVENTS[FSMonitor.MODIFIED][FSMonitor.MODIFIED] = FSMonitor.MODIFIED
FSMonitor.MERGE_EVENTS[FSMonitor.MODIFIED][FSMonitor.DELETED]  = FSMonitor.DELETED
FSMonitor.MERGE_EVENTS[FSMonitor.DELETED] = {}
FSMonitor.MERGE_EVENTS[FSMonitor.DELETED][FSMonitor.CREATED]   = FSMonitor.MODIFIED
FSMonitor.MERGE_EVENTS[FSMonitor.DELETED][FSMonitor.MODIFIED]  = FSMonitor.MODIFIED #!
FSMonitor.MERGE_EVENTS[FSMonitor.DELETED][FSMonitor.DELETED]   = FSMonitor.DELETED  #!


if __name__ == "__main__":
    import time

    def callbackfunc(monitored_path, event_path, event):
        print "CALLBACK FIRED, params: monitored_path=%s', event_path='%s', event='%d'" % (monitored_path, event_path, event)

    fsmonitor_class = get_fsmonitor()
    print "Using class", fsmonitor_class
    fsmonitor = fsmonitor_class(callbackfunc, True)
    fsmonitor.start()
    fsmonitor.add_dir("/Users/wimleers/Downloads", FSMonitor.CREATED | FSMonitor.MODIFIED | FSMonitor.DELETED)
    time.sleep(30)
    fsmonitor.stop()

########NEW FILE########
__FILENAME__ = fsmonitor_fsevents
"""fsmonitor_fsevents.py FSMonitor subclass for FSEvents on Mac OS X >= 10.5

Always works in persistent mode by (FSEvent's) design.
"""


__author__ = "Wim Leers (work@wimleers.com)"
__version__ = "$Rev$"
__date__ = "$Date$"
__license__ = "GPL"


from fsmonitor import *
from FSEvents import kCFAllocatorDefault, \
                     CFRunLoopGetCurrent, \
                     kCFRunLoopDefaultMode, \
                     CFRunLoopRun, \
                     CFRunLoopStop, \
                     CFRunLoopAddTimer, \
                     CFRunLoopTimerCreate, \
                     CFAbsoluteTimeGetCurrent, \
                     NSAutoreleasePool, \
                     kFSEventStreamEventIdSinceNow, \
                     kFSEventStreamCreateFlagWatchRoot, \
                     kFSEventStreamEventFlagNone, \
                     kFSEventStreamEventFlagMustScanSubDirs, \
                     kFSEventStreamEventFlagUserDropped, \
                     kFSEventStreamEventFlagKernelDropped, \
                     kFSEventStreamEventFlagRootChanged, \
                     FSEventStreamScheduleWithRunLoop, \
                     FSEventStreamCreate, \
                     FSEventStreamStart, \
                     FSEventStreamStop, \
                     FSEventStreamInvalidate, \
                     FSEventStreamRelease, \
                     FSEventStreamShow


# Define exceptions.
class FSMonitorFSEventsError(FSMonitorError): pass
class MonitorError(FSMonitorFSEventsError): pass
class CouldNotStartError(FSMonitorFSEventsError): pass


class FSMonitorFSEvents(FSMonitor):
    """FSEvents support for FSMonitor"""


    # These 3 settings are hardcoded. See FSMonitor's documentation for an
    # explanation.
    latency = 1.0
    sinceWhen = kFSEventStreamEventIdSinceNow
    flags = kFSEventStreamCreateFlagWatchRoot


    def __init__(self, callback, persistent=True, trigger_events_for_initial_scan=False, ignored_dirs=[], dbfile="fsmonitor.db", parent_logger=None):
        FSMonitor.__init__(self, callback, True, trigger_events_for_initial_scan, ignored_dirs, dbfile, parent_logger)
        self.logger.info("FSMonitor class used: FSMonitorFSEvents.")
        self.latest_event_id = None
        self.auto_release_pool = None


    def __add_dir(self, path, event_mask):
        """override of FSMonitor.__add_dir()"""

        # Immediately start monitoring this directory.
        streamRef = FSEventStreamCreate(kCFAllocatorDefault,
                                        self.__fsevents_callback,
                                        path,
                                        [path],
                                        self.__class__.sinceWhen,
                                        self.__class__.latency,
                                        self.__class__.flags)
        # Debug output.
        #FSEventStreamShow(streamRef)
        # Verify that FSEvents is able to monitor this directory.
        if streamRef is None:
            raise MonitorError, "Could not monitor %s" % path
            return None
        else:
            self.monitored_paths[path] = MonitoredPath(path, event_mask, streamRef)
            # TRICKY: the monitoring has not yet started! This happens in
            # FSMonitorEvents.__process_queues(), which is called on every
            # runloop by FSMonitorEvents.run().
            self.monitored_paths[path].monitoring = False

        if self.persistent:
            # Generate the missed events. This implies that events that
            # occurred while File Conveyor was offline (or not yet in use)
            # will *always* be generated, whether this is the first run or the
            # thousandth.
            # TODO: use FSEvents' sinceWhen parameter instead of the current
            # inefficient scanning method.
            FSMonitor.generate_missed_events(self, path)
        else:
            # Perform an initial scan of the directory structure. If this has
            # already been done, then it will return immediately.
            self.pathscanner.initial_scan(path)

        return self.monitored_paths[path]


    def __remove_dir(self, path):
        """override of FSMonitor.__remove_dir()"""
        if path in self.monitored_paths.keys():
            streamRef = self.monitored_paths[path].fsmonitor_ref
            # Stop, unschedule, invalidate and release the stream refs.
            FSEventStreamStop(streamRef)
            # We don't use FSEventStreamUnscheduleFromRunLoop prior to
            # invalidating the stream, because invalidating the stream
            # automatically unschedules the stream from all run loops.
            FSEventStreamInvalidate(streamRef)
            FSEventStreamRelease(streamRef)

            del self.monitored_paths[path]


    def run(self):
        # Necessary because we're using PyObjC in a thread other than the main
        # thread.
        self.auto_release_pool = NSAutoreleasePool.alloc().init()

        # Setup. Ensure that this isn't interleaved with any other thread, so
        # that the DB setup continues as expected.
        self.lock.acquire()
        FSMonitor.setup(self)
        self.lock.release()

        # Set up a callback to a function that process the queues frequently.
        CFRunLoopAddTimer(
           CFRunLoopGetCurrent(),
           CFRunLoopTimerCreate(None, CFAbsoluteTimeGetCurrent(), 0.5, 0, 0, self.__process_queues, None),
           kCFRunLoopDefaultMode
        )

        # Start the run loop.
        CFRunLoopRun()


    def stop(self):
        """override of FSMonitor.stop()"""

        # Let the thread know it should die.
        self.lock.acquire()
        self.die = True
        self.lock.release()

        # Stop monitoring each monitored path.
        for path in self.monitored_paths.keys():
            self.__remove_dir(path)

        # Store the latest event ID so we know where we left off.
        # TODO: separate table in DB to store this?

        # Delete the auto release pool.
        del self.auto_release_pool


    def __process_queues(self, timer, context):
        # Die when asked to.
        self.lock.acquire()
        if self.die:
            CFRunLoopStop(CFRunLoopGetCurrent())
        self.lock.release()


        # Process add queue.
        self.lock.acquire()
        if not self.add_queue.empty():
            (path, event_mask) = self.add_queue.get()
            self.lock.release()
            self.__add_dir(path, event_mask)
        else:
            self.lock.release()

        # Process remove queue.
        self.lock.acquire()
        if not self.remove_queue.empty():
            path = self.add_queue.get()
            self.lock.release()
            self.__remove_dir(path)
        else:
            self.lock.release()

        # Ensure all monitored paths are actually being monitored. If they're
        # not yet being monitored, start doing so.
        for path in self.monitored_paths.keys():
            if self.monitored_paths[path].monitoring:
                continue
            streamRef = self.monitored_paths[path].fsmonitor_ref
            
            # Schedule stream on a loop.
            FSEventStreamScheduleWithRunLoop(streamRef, CFRunLoopGetCurrent(), kCFRunLoopDefaultMode)

            # Register with the FS Events service to receive events.
            started = FSEventStreamStart(streamRef)
            if not started:
                raise CouldNotStartError
            else:
                self.monitored_paths[path].monitoring = True


    def __fsevents_callback(self, streamRef, clientCallBackInfo, numEvents, eventPaths, eventFlags, eventIDs):
        """private callback function for use with FSEventStreamCreate"""
        discovered_through = "FSEvents"
        # Details of the used flags can be found in FSEvents.h.
        monitored_path = clientCallBackInfo

        for i in range(numEvents):
            event_path = eventPaths[i].decode('utf-8')
            self.latest_event_id = eventIDs[i]

            # Strip trailing slash
            if event_path[-1] == '/':
                event_path = event_path[:-1]

            if FSMonitor.is_in_ignored_directory(self, event_path):
                self.logger.debug("Event occurred at '%s', but is inside ignored directory." % (event_path))
                return

            # Trigger the appropriate events.
            if eventFlags[i] & kFSEventStreamEventFlagUserDropped:
                self.logger.debug("FSEvents in user space  dropped events for monitored path '%s'." % (monitored_path))
                FSMonitor.trigger_event(self, monitored_path, None, FSMonitor.DROPPED_EVENTS, discovered_through)

            elif eventFlags[i] & kFSEventStreamEventFlagKernelDropped:
                self.logger.debug("FSEvents in kernel space  dropped events for monitored path '%s'." % (monitored_path))
                FSMonitor.trigger_event(self, monitored_path, None, FSMonitor.DROPPED_EVENTS, discovered_through)

            elif eventFlags[i] & kFSEventStreamEventFlagRootChanged:
                self.logger.debug("FSEvents reports that the monitored directory '%s' has been moved." % (monitored_path))
                FSMonitor.trigger_event(self, monitored_path, event_path, FSMonitor.MONITORED_DIR_MOVED, discovered_through)

            elif eventFlags[i] == kFSEventStreamEventFlagNone:
                # There was some change in the directory at the specific path
                # supplied in this event.
                result = self.pathscanner.scan(event_path)
                self.logger.debug("FSEvents reports that event(s) have occurred inside '%s'. Starting the scan to trigger the corresponding file-specific events." % (event_path))
                FSMonitor.trigger_events_for_pathscanner_result(self, monitored_path, event_path, result, discovered_through)

            elif eventFlags[i] & kFSEventStreamEventFlagMustScanSubDirs:
                # There was some change in the directory and one of its
                # subdirectories supplied in this event.                
                # This call to PathScanner is what ensures that FSMonitor.db
                # remains up-to-date.
                result = self.pathscanner.scan_tree(event_path)
                self.logger.debug("FSEvents reports that event(s) have occurred inside subdirectories of '%s'. Starting the scan to trigger the corresponding file-specific events." % (event_path))
                FSMonitor.trigger_events_for_pathscanner_result(self, monitored_path, event_path, result, discovered_through)

            else:
                # This call to PathScanner is what ensures that FSMonitor.db
                # remains up-to-date.
                result = self.pathscanner.scan(event_path)
                self.logger.debug("FSEvents reports that some non-standard event(s) have occurred inside '%s'. Starting the scan to trigger the corresponding file-specific events." % (event_path))
                FSMonitor.trigger_events_for_pathscanner_result(self, monitored_path, event_path, result, discovered_through)

########NEW FILE########
__FILENAME__ = fsmonitor_inotify
"""fsmonitor_inotify.py FSMonitor subclass for inotify on Linux kernel >= 2.6.13"""


__author__ = "Wim Leers (work@wimleers.com)"
__version__ = "$Rev$"
__date__ = "$Date$"
__license__ = "GPL"


from fsmonitor import *
import pyinotify
from pyinotify import WatchManager, \
                      ThreadedNotifier, \
                      ProcessEvent, \
                      WatchManagerError
import time
import os
import stat
import sys



# Define exceptions.
class FSMonitorInotifyError(FSMonitorError): pass


class FSMonitorInotify(FSMonitor):
    """inotify support for FSMonitor"""


    EVENTMAPPING = {
        FSMonitor.CREATED             : pyinotify.IN_CREATE,
        FSMonitor.MODIFIED            : pyinotify.IN_MODIFY | pyinotify.IN_ATTRIB,
        FSMonitor.DELETED             : pyinotify.IN_DELETE,
        FSMonitor.MONITORED_DIR_MOVED : pyinotify.IN_MOVE_SELF,
        FSMonitor.DROPPED_EVENTS      : pyinotify.IN_Q_OVERFLOW,
    }


    def __init__(self, callback, persistent=False, trigger_events_for_initial_scan=False, ignored_dirs=[], dbfile="fsmonitor.db", parent_logger=None):
        FSMonitor.__init__(self, callback, persistent, trigger_events_for_initial_scan, ignored_dirs, dbfile, parent_logger)
        self.logger.info("FSMonitor class used: FSMonitorInotify.")
        self.wm             = None
        self.notifier       = None
        self.pathscanner_files_created  = []
        self.pathscanner_files_modified = []
        self.pathscanner_files_deleted  = []


    def __fsmonitor_event_to_inotify_event(self, event_mask):
        """map an FSMonitor event to an inotify event"""
        inotify_event_mask = 0
        for fsmonitor_event_mask in self.__class__.EVENTMAPPING.keys():
            if event_mask & fsmonitor_event_mask:
                inotify_event_mask = inotify_event_mask | self.__class__.EVENTMAPPING[fsmonitor_event_mask]
        return inotify_event_mask


    def inotify_path_to_monitored_path(self, path):
        """map a pathname (as received in an inotify event) to its
        corresponding monitored path
        """
        for monitored_path in self.monitored_paths.keys():
            if os.path.commonprefix([path, monitored_path]) == monitored_path:
                return monitored_path


    def __add_dir(self, path, event_mask):
        """override of FSMonitor.__add_dir()"""

        # Immediately start monitoring this directory.
        event_mask_inotify = self.__fsmonitor_event_to_inotify_event(event_mask)
        try:
            wdd = self.wm.add_watch(path, event_mask_inotify, proc_fun=self.process_event, rec=True, auto_add=True, quiet=False)
        except WatchManagerError, e:
            raise FSMonitorError, "Could not monitor '%s', reason: %s" % (path, e)
        # Verify that inotify is able to monitor this directory and all of its
        # subdirectories.
        for monitored_path in wdd:
            if wdd[monitored_path] < 0:
                code = wdd[monitored_path]
                raise FSMonitorError, "Could not monitor %s (%d)" % (monitored_path, code)
        self.monitored_paths[path] = MonitoredPath(path, event_mask, wdd)
        self.monitored_paths[path].monitoring = True

        if self.persistent:
            # Generate the missed events. This implies that events that
            # occurred while File Conveyor was offline (or not yet in use)
            # will *always* be generated, whether this is the first run or the
            # thousandth.
            FSMonitor.generate_missed_events(self, path)
        else:
            # Perform an initial scan of the directory structure. If this has
            # already been done, then it will return immediately.
            self.pathscanner.initial_scan(path)

        return self.monitored_paths[path]


    def __remove_dir(self, path):
        """override of FSMonitor.__remove_dir()"""
        if path in self.monitored_paths.keys():
            self.wm.rm_watch(path, rec=True, quiet=True)
            del self.monitored_paths[path]


    def run(self):
        # Setup. Ensure that this isn't interleaved with any other thread, so
        # that the DB setup continues as expected.
        self.lock.acquire()
        FSMonitor.setup(self)
        self.process_event = FSMonitorInotifyProcessEvent(self)
        self.lock.release()

        # Set up inotify.
        self.wm = WatchManager()
        self.notifier = ThreadedNotifier(self.wm, self.process_event)

        self.notifier.start()

        while not self.die:
            self.__process_queues()
            time.sleep(0.5)

        self.notifier.stop()


    def stop(self):
        """override of FSMonitor.stop()"""

        # Let the thread know it should die.
        self.lock.acquire()
        self.die = True
        self.lock.release()

        # Stop monitoring each monitored path.
        for path in self.monitored_paths.keys():
            self.__remove_dir(path)


    def __process_pathscanner_updates(self, update_list, callback):
        self.lock.acquire()
        if len(update_list) > 0:
            callback(update_list)
            del update_list[:] # Clear the list with updates.
        self.lock.release()


    def __process_queues(self):
        # Process "add monitored path" queue.
        self.lock.acquire()
        if not self.add_queue.empty():
            (path, event_mask) = self.add_queue.get()
            self.lock.release()
            self.__add_dir(path, event_mask)
        else:
            self.lock.release()

        # Process "remove monitored path" queue.
        self.lock.acquire()
        if not self.remove_queue.empty():
            path = self.add_queue.get()
            self.lock.release()
            self.__remove_dir(path)
        else:
            self.lock.release()

        # These calls to PathScanner is what ensures that FSMonitor.db
        # remains up-to-date. (These lists of files to add, update and delete
        # from the DB are applied to PathScanner.)
        self.__process_pathscanner_updates(self.pathscanner_files_created,  self.pathscanner.add_files   )
        self.__process_pathscanner_updates(self.pathscanner_files_modified, self.pathscanner.update_files)
        self.__process_pathscanner_updates(self.pathscanner_files_deleted,  self.pathscanner.delete_files)




class FSMonitorInotifyProcessEvent(ProcessEvent):


    # On Linux, you can choose which encoding is used for your file system's
    # file names. Hence, we better detect the file system's encoding so we
    # know what to decode from in __ensure_unicode(). 
    encoding = sys.getfilesystemencoding()


    def __init__(self, fsmonitor):
        ProcessEvent.__init__(self)
        self.fsmonitor_ref      = fsmonitor
        self.discovered_through = "inotify"


    def __update_pathscanner_db(self, pathname, event_type):
        """use PathScanner.(add|update|delete)_files() to queue updates for
        PathScanner's DB
        """
        (path, filename) = os.path.split(pathname)
        if event_type == FSMonitor.DELETED:
            # Build tuple for deletion of row in PathScanner's DB.
            t = (path, filename)
            self.fsmonitor_ref.pathscanner_files_deleted.append(t)
        else:
            # Build tuple for PathScanner's DB of the form (path, filename,
            # mtime), with mtime = -1 when it's a directory.
            st = os.stat(pathname)
            is_dir = stat.S_ISDIR(st.st_mode)
            if not is_dir:
                mtime = st[stat.ST_MTIME]
                t = (path, filename, mtime)
            else:
                t = (path, filename, -1)

            # Update PathScanner's DB.
            if event_type == FSMonitor.CREATED:
                self.fsmonitor_ref.pathscanner_files_created.append(t)
            else:
                self.fsmonitor_ref.pathscanner_files_modified.append(t)


    @classmethod
    def __ensure_unicode(cls, event):
        event.path = event.path.decode(cls.encoding)
        event.pathname = event.pathname.decode(cls.encoding)
        return event


    def process_IN_CREATE(self, event):
        event = self.__ensure_unicode(event)
        if FSMonitor.is_in_ignored_directory(self.fsmonitor_ref, event.path):
            return
        monitored_path = self.fsmonitor_ref.inotify_path_to_monitored_path(event.path)
        self.fsmonitor_ref.logger.debug("inotify reports that an IN_CREATE event has occurred for '%s'." % (event.pathname))
        self.__update_pathscanner_db(event.pathname, FSMonitor.CREATED)
        FSMonitor.trigger_event(self.fsmonitor_ref, monitored_path, event.pathname, FSMonitor.CREATED, self.discovered_through)


    def process_IN_DELETE(self, event):
        event = self.__ensure_unicode(event)
        if FSMonitor.is_in_ignored_directory(self.fsmonitor_ref, event.path):
            return
        monitored_path = self.fsmonitor_ref.inotify_path_to_monitored_path(event.path)
        self.fsmonitor_ref.logger.debug("inotify reports that an IN_DELETE event has occurred for '%s'." % (event.pathname))
        self.__update_pathscanner_db(event.pathname, FSMonitor.DELETED)
        FSMonitor.trigger_event(self.fsmonitor_ref, monitored_path, event.pathname, FSMonitor.DELETED, self.discovered_through)


    def process_IN_MODIFY(self, event):
        event = self.__ensure_unicode(event)
        if FSMonitor.is_in_ignored_directory(self.fsmonitor_ref, event.path):
            return
        monitored_path = self.fsmonitor_ref.inotify_path_to_monitored_path(event.path)
        self.fsmonitor_ref.logger.debug("inotify reports that an IN_MODIFY event has occurred for '%s'." % (event.pathname))
        self.__update_pathscanner_db(event.pathname, FSMonitor.MODIFIED)
        FSMonitor.trigger_event(self.fsmonitor_ref, monitored_path, event.pathname, FSMonitor.MODIFIED, self.discovered_through)


    def process_IN_ATTRIB(self, event):
        event = self.__ensure_unicode(event)
        if FSMonitor.is_in_ignored_directory(self.fsmonitor_ref, event.path):
            return
        monitored_path = self.fsmonitor_ref.inotify_path_to_monitored_path(event.path)
        self.fsmonitor_ref.logger.debug("inotify reports that an IN_ATTRIB event has occurred for '%s'." % (event.pathname))
        self.__update_pathscanner_db(event.pathname, FSMonitor.MODIFIED)
        FSMonitor.trigger_event(self.fsmonitor_ref, monitored_path, event.pathname, FSMonitor.MODIFIED, self.discovered_through)


    def process_IN_MOVE_SELF(self, event):
        event = self.__ensure_unicode(event)
        if FSMonitor.is_in_ignored_directory(self.fsmonitor_ref, event.path):
            return
        self.fsmonitor_ref.logger.debug("inotify reports that an IN_MOVE_SELF event has occurred for '%s'." % (event.pathname))
        monitored_path = self.fsmonitor_ref.inotify_path_to_monitored_path(event.path)
        FSMonitor.trigger_event(self.fsmonitor_ref, monitored_path, event.pathname, FSMonitor.MONITORED_DIR_MOVED, self.discovered_through)


    def process_IN_Q_OVERFLOW(self, event):
        event = self.__ensure_unicode(event)
        if FSMonitor.is_in_ignored_directory(self.fsmonitor_ref, event.path):
            return
        self.fsmonitor_ref.logger.debug("inotify reports that an IN_Q_OVERFLOW event has occurred for '%s'." % (event.pathname))
        monitored_path = self.fsmonitor_ref.inotify_path_to_monitored_path(event.path)
        FSMonitor.trigger_event(self.fsmonitor_ref, monitored_path, event.pathname, FSMonitor.DROPPED_EVENTS, self.discovered_through)


    def process_default(self, event):
        # Event not supported!
        self.fsmonitor_ref.logger.debug("inotify reports that an unsupported event (mask: %d, %s) has occurred for '%s'." % (event.mask, event.maskname, event.pathname))
        pass

########NEW FILE########
__FILENAME__ = fsmonitor_polling
"""fsmonitor_polling.py FSMonitor subclass that uses polling

Always works in persistent mode by design.
"""


__author__ = "Wim Leers (work@wimleers.com)"
__version__ = "$Rev$"
__date__ = "$Date$"
__license__ = "GPL"


from fsmonitor import *
import time


# Define exceptions.
class FSMonitorPollingError(FSMonitorError): pass


class FSMonitorPolling(FSMonitor):
    """polling support for FSMonitor"""


    interval = 10


    def __init__(self, callback, persistent=True, trigger_events_for_initial_scan=False, ignored_dirs=[], dbfile="fsmonitor.db", parent_logger=None):
        FSMonitor.__init__(self, callback, True, trigger_events_for_initial_scan, ignored_dirs, dbfile, parent_logger)
        self.logger.info("FSMonitor class used: FSMonitorPolling.")


    def __add_dir(self, path, event_mask):
        """override of FSMonitor.__add_dir()"""

        # Immediately start monitoring this directory.
        self.monitored_paths[path] = MonitoredPath(path, event_mask, None)
        self.monitored_paths[path].monitoring = True

        if self.persistent:
            # Generate the missed events. This implies that events that
            # occurred while File Conveyor was offline (or not yet in use)
            # will *always* be generated, whether this is the first run or the
            # thousandth.
            FSMonitor.generate_missed_events(self, path)
        else:
            # Perform an initial scan of the directory structure. If this has
            # already been done, then it will return immediately.
            self.pathscanner.initial_scan(path)

        return self.monitored_paths[path]


    def __remove_dir(self, path):
        """override of FSMonitor.__remove_dir()"""
        if path in self.monitored_paths.keys():
            del self.monitored_paths[path]


    def run(self):
        # Setup. Ensure that this isn't interleaved with any other thread, so
        # that the DB setup continues as expected.
        self.lock.acquire()
        FSMonitor.setup(self)
        self.lock.release()

        while not self.die:
            self.__process_queues()
            # Sleep some time.
            # TODO: make this configurable!
            time.sleep(self.__class__.interval)


    def stop(self):
        """override of FSMonitor.stop()"""

        # Let the thread know it should die.
        self.lock.acquire()
        self.die = True
        self.lock.release()

        # Stop monitoring each monitored path.
        for path in self.monitored_paths.keys():
            self.__remove_dir(path)


    def __process_queues(self):
        # Die when asked to.
        self.lock.acquire()
        if self.die:
            self.notifier.stop()
        self.lock.release()

        # Process add queue.
        self.lock.acquire()
        if not self.add_queue.empty():
            (path, event_mask) = self.add_queue.get()
            self.lock.release()
            self.__add_dir(path, event_mask)
        else:
            self.lock.release()

        # Process remove queue.
        self.lock.acquire()
        if not self.remove_queue.empty():
            path = self.add_queue.get()
            self.lock.release()
            self.__remove_dir(path)
        else:
            self.lock.release()

        # Scan all paths.
        discovered_through = "polling"
        for monitored_path in self.monitored_paths.keys():
            # These calls to PathScanner is what ensures that FSMonitor.db
            # remains up-to-date.
            for event_path, result in self.pathscanner.scan_tree(monitored_path):
                FSMonitor.trigger_events_for_pathscanner_result(self, monitored_path, event_path, result, discovered_through)

########NEW FILE########
__FILENAME__ = pathscanner
"""pathscanner.py Scans paths and stores them in a sqlite3 database

You can use PathScanner to detect changes in a directory structure. For
efficiency, only creations, deletions and modifications are detected, not
moves.

Modified files are detected by looking at the mtime.

Instructions:
- Use initial_scan() to build the initial database.
- Use scan() afterwards, to get the changes.
- Use scan_tree() (which uses scan()) to get the changes in an entire
  directory structure.
- Use purge_path() to purge all the metadata for a path from the database.
- Use (add|update|remove)_files() to add/update/remove files manually (useful
  when your application has more/faster knowledge of changes)

TODO: unit tests (with *many* mock functions). Stable enough without them.
"""


__author__ = "Wim Leers (work@wimleers.com)"
__version__ = "$Rev$"
__date__ = "$Date$"
__license__ = "GPL"


import os
import stat
import sqlite3
from sets import Set


class PathScanner(object):
    """scan paths for changes, persistent storage using SQLite"""
    def __init__(self, dbcon, ignored_dirs=[], table="pathscanner", commit_interval=50):
        self.dbcon                  = dbcon
        self.dbcur                  = dbcon.cursor()
        self.ignored_dirs           = ignored_dirs
        self.table                  = table
        self.uncommitted_statements = 0
        self.commit_interval        = commit_interval
        self.__prepare_db()


    def __prepare_db(self):
        """prepare the database (create the table structure)"""

        self.dbcur.execute("CREATE TABLE IF NOT EXISTS %s(path text, filename text, mtime integer)" % (self.table))
        self.dbcur.execute("CREATE UNIQUE INDEX IF NOT EXISTS file_unique_per_path ON %s (path, filename)" % (self.table))
        self.dbcon.commit()


    def __walktree(self, path):
        rows = []
        for path, filename, mtime, is_dir in self.__listdir(path):
            rows.append((path, filename, mtime if not is_dir else -1))
            if is_dir:
                for childrows in self.__walktree(os.path.join(path, filename)):
                    yield childrows
        yield rows


    def __listdir(self, path):
        """list all the files in a directory
        
        Returns (path, filename, mtime, is_dir) tuples.
        """

        try:
            filenames = os.listdir(path)
        except os.error:
            return

        for filename in filenames:
            try:
                path_to_file = os.path.join(path, filename)
                st = os.stat(path_to_file)
                mtime = st[stat.ST_MTIME]
                if stat.S_ISDIR(st.st_mode):
                    # If this is one of the ignored directories, skip it.
                    if filename in self.ignored_dirs:
                        continue
                    # This is not an ignored directory, but if it's a symlink,
                    # we will prevent walking the directory tree below it by
                    # pretending it's just a file.
                    else:
                        is_dir = not os.path.islink(path_to_file)
                else:
                    is_dir = False
                row = (path, filename, mtime, is_dir)
            except os.error:
                continue
            yield row


    def initial_scan(self, path):
        """perform the initial scan
        
        Returns False if there is already data available for this path.
        """
        assert type(path) == type(u'.')

        # Check if there really isn't any data available for this path.
        self.dbcur.execute("SELECT COUNT(filename) FROM %s WHERE path=?" % (self.table), (path,))
        if self.dbcur.fetchone()[0] > 0:
            return False
        
        for files in self.__walktree(path):
            self.add_files(files)


    def purge_path(self, path):
        """purge the metadata for a given path and all its subdirectories"""
        assert type(path) == type(u'.')

        self.dbcur.execute("DELETE FROM %s WHERE path LIKE ?" % (self.table), (path + "%",))
        self.dbcur.execute("VACUUM %s" % (self.table))
        self.dbcon.commit()


    def add_files(self, files):
        """add file metadata to the database
        
        Expected format: a set of (path, filename, mtime) tuples.
        """
        self.update_files(files)


    def update_files(self, files):
        """update file metadata in the database

        Expected format: a set of (path, filename, mtime) tuples.
        """

        for row in files:
            # Use INSERT OR REPLACE to let the OS's native file system monitor
            # (inotify on Linux, FSEvents on OS X) run *while* missed events
            # are being generated.
            # See https://github.com/wimleers/fileconveyor/issues/69.
            self.dbcur.execute("INSERT OR REPLACE INTO %s VALUES(?, ?, ?)" % (self.table), row)
            self.__db_batched_commit()
        # Commit the remaining rows.
        self.__db_batched_commit(True)


    def delete_files(self, files):
        """delete file metadata from the database

        Expected format: a set of (path, filename) tuples.
        """

        for row in files:
            self.dbcur.execute("DELETE FROM %s WHERE path=? AND filename=?" % (self.table), row)
            self.__db_batched_commit()
        # Commit the remaining rows.
        self.__db_batched_commit(True)


    def __db_batched_commit(self, force=False):
        """docstring for __db_commit"""
        # Commit to the database in batches, to reduce concurrency: collect
        # self.commit_interval rows, then commit.
        
        self.uncommitted_statements += 1
        if force == True or self.uncommitted_statements == self.commit_interval:
            self.dbcon.commit()
            self.uncommitted_rows = 0
            

    def scan(self, path):
        """scan a directory (without recursion!) for changes
        
        The database is also updated to reflect the new situation, of course.

        By design, so that this function can be used by scan_tree():
        - Cannot detect newly created directory trees.
        - Can detect deleted directory trees.
        """

        assert type(path) == type(u'.')
        # Fetch the old metadata from the DB.
        self.dbcur.execute("SELECT filename, mtime FROM %s WHERE path=?" % (self.table), (path, ))
        old_files = {}
        for filename, mtime in self.dbcur.fetchall():
            old_files[filename] = (filename, mtime)

        # Get the current metadata.
        new_files = {}
        for path, filename, mtime, is_dir in self.__listdir(path):
            new_files[filename] = (filename, mtime if not is_dir else -1)

        scan_result = self.__scanhelper(path, old_files, new_files)

        # Add the created files to the DB.
        files = Set()
        for filename in scan_result["created"]:
            (filename, mtime) = new_files[filename]
            files.add((path, filename, mtime))
        self.add_files(files)
        # Update the modified files in the DB.
        files = Set()
        for filename in scan_result["modified"]:
            (filename, mtime) = new_files[filename]
            files.add((path, filename, mtime))
        self.update_files(files)
        # Remove the deleted files from the DB.
        files = Set()
        for filename in scan_result["deleted"]:
            if len(os.path.dirname(filename)):
                realpath = path + os.sep + os.path.dirname(filename)
            else:
                realpath = path
            realfilename = os.path.basename(filename)
            files.add((realpath, realfilename))
        self.delete_files(files)

        return scan_result


    def scan_tree(self, path):
        """scan a directory tree for changes"""
        assert type(path) == type(u'.')

        # Scan the current directory for changes.
        result = self.scan(path)

        # Prepend the current path.
        for key in result.keys():
            tmp = Set()
            for filename in result[key]:
                tmp.add(path + os.sep + filename)
            result[key] = tmp
        yield (path, result)

        # Also scan each subdirectory.
        for path, filename, mtime, is_dir in self.__listdir(path):
            if is_dir:
                for subpath, subresult in self.scan_tree(os.path.join(path, filename)):
                    yield (subpath, subresult)


    def __scanhelper(self, path, old_files, new_files):
        """helper function for scan()

        old_files and new_files should be dictionaries of (filename, mtime)
        tuples, keyed by filename

        Returns a dictionary of sets of filenames with the keys "created",
        "deleted" and "modified".
        """

        # The dictionary that will be returned.
        result = {}
        result["created"] = Set()
        result["deleted"] = Set()
        result["modified"] = Set()

        # Create some sets that will make our work easier.
        old_filenames = Set(old_files.keys())
        new_filenames = Set(new_files.keys())

        # Step 1: find newly created files.
        result["created"] = new_filenames.difference(old_filenames)

        # Step 2: find deleted files.
        result["deleted"] = old_filenames.difference(new_filenames)

        # Step 3: find modified files.
        # Only files that are not created and not deleted can be modified!
        possibly_modified_files = new_filenames.union(old_filenames)
        possibly_modified_files = possibly_modified_files.symmetric_difference(result["created"])
        possibly_modified_files = possibly_modified_files.symmetric_difference(result["deleted"])
        for filename in possibly_modified_files:
            (filename, old_mtime) = old_files[filename]
            (filename, new_mtime) = new_files[filename]
            if old_mtime != new_mtime:
                result["modified"].add(filename)

        # Step 4
        # If a directory was deleted, we also need to retrieve the filenames
        # and paths of the files within that subtree.
        deleted_tree = Set()
        for deleted_file in result["deleted"]:
            (filename, mtime) = old_files[deleted_file]
            # An mtime of -1 means that this is a directory.
            if mtime == -1:
                dirpath = path + os.sep + filename
                self.dbcur.execute("SELECT * FROM %s WHERE path LIKE ?" % (self.table), (dirpath + "%",))
                files_in_dir = self.dbcur.fetchall()
                # Mark all files below the deleted directory also as deleted.
                for (subpath, subfilename, submtime) in files_in_dir:
                    deleted_tree.add(os.path.join(subpath, subfilename)[len(path) + 1:])
        result["deleted"] = result["deleted"].union(deleted_tree)
        
        return result


if __name__ == "__main__":
    # Sample usage
    path = "/Users/wimleers/Downloads"
    db = sqlite3.connect("pathscanner.db")
    db.text_factory = unicode # This is the default, but we set it explicitly, just to be sure.
    ignored_dirs = ["CVS", ".svn"]
    scanner = PathScanner(db, ignored_dirs)
    # Force a rescan
    #scanner.purge_path(path)
    scanner.initial_scan(path)

    # Detect changes in a single directory
    #print scanner.scan(path)

    # Detect changes in the entire tree
    report = {}
    report["created"] = Set()
    report["deleted"] = Set()
    report["modified"] = Set()
    for path, result in scanner.scan_tree(path):
        report["created"] = report["created"].union(result["created"])
        report["deleted"] = report["deleted"].union(result["deleted"])
        report["modified"] = report["modified"].union(result["modified"])
    print report
########NEW FILE########
__FILENAME__ = persistent_list
"""persistent_list.py An infinite persistent list that uses sqlite for storage and a list for a complete in-memory cache"""


__author__ = "Wim Leers (work@wimleers.com)"
__version__ = "$Rev$"
__date__ = "$Date$"
__license__ = "GPL"


import sqlite3
import cPickle


# Define exceptions.
class PersistentListError(Exception): pass


class PersistentList(object):
    """a persistent queue with sqlite back-end designed for finite lists"""

    def __init__(self, table, dbfile="persistent_list.db"):
        # Initialize the database.
        self.dbcon = None
        self.dbcur = None
        self.table = table
        self.__prepare_db(dbfile)

        # Initialize the memory list: load its contents from the database.
        self.memory_list = {}
        self.dbcur.execute("SELECT id, item FROM %s ORDER BY id ASC" % (self.table))
        resultList = self.dbcur.fetchall()
        for id, item in resultList:
            self.memory_list[item] = id


    def __prepare_db(self, dbfile):
        sqlite3.register_converter("pickle", cPickle.loads)
        self.dbcon = sqlite3.connect(dbfile, detect_types=sqlite3.PARSE_DECLTYPES|sqlite3.PARSE_COLNAMES)
        self.dbcon.text_factory = unicode # This is the default, but we set it explicitly, just to be sure.
        self.dbcur = self.dbcon.cursor()
        self.dbcur.execute("CREATE TABLE IF NOT EXISTS %s(id INTEGER PRIMARY KEY AUTOINCREMENT, item pickle)" % (self.table))
        self.dbcon.commit()


    def __contains__(self, item):
        return item in self.memory_list.keys()


    def __iter__(self):
        return self.memory_list.__iter__()


    def __len__(self):
        return len(self.memory_list)


    def __getitem__(self, index):
        keys = self.memory_list.keys()
        return keys[index]


    def append(self, item):
        # Insert the item into the database.
        pickled_item = cPickle.dumps(item, cPickle.HIGHEST_PROTOCOL)
        self.dbcur.execute("INSERT INTO %s (item) VALUES(?)" % (self.table), (sqlite3.Binary(pickled_item), ))
        self.dbcon.commit()
        id = self.dbcur.lastrowid
        # Insert the item into the in-memory list.
        self.memory_list[item] = id


    def remove(self, item):
        # Delete from the database.
        if self.memory_list.has_key(item):
            id = self.memory_list[item]
            self.dbcur.execute("DELETE FROM %s WHERE id = ?" % (self.table), (id, ))
            self.dbcon.commit()        
            # Delete from the in-memory list.
            del self.memory_list[item]

########NEW FILE########
__FILENAME__ = persistent_list_test
"""Unit test for persistent_list.py"""


__author__ = "Wim Leers (work@wimleers.com)"
__version__ = "$Rev$"
__date__ = "$Date$"
__license__ = "GPL"


from persistent_list import *
import os
import os.path
import unittest


class TestConditions(unittest.TestCase):
    def setUp(self):
        self.table = "persistent_list_test"
        self.db = "persistent_list_test.db"
        if os.path.exists(self.db):
            os.remove(self.db)


    def tearDown(self):
        if os.path.exists(self.db):
            os.remove(self.db)


    def testEmpty(self):
        pl = PersistentList(self.table, self.db)
        self.assertEqual(0, len(pl))


    def testBasicUsage(self):
        pl = PersistentList(self.table, self.db)
        items = ["abc", 99, "xyz", 123]
        received_items = []
    
        # Add the items to the persistent list.
        for item in items:
            pl.append(item)
        self.assertEqual(len(items), len(pl), "The size of the original list matches the size of the persistent list.")

        # Ensure persistency is really working, by deleting the PersistentList
        # and then loading it again.
        del pl
        pl = PersistentList(self.table, self.db)

        # Get the items from the persistent list.
        for item in pl:
            received_items.append(item)
        # The order doesn't matter.
        items.sort()
        received_items.sort()
        self.assertEqual(items, received_items, "The original list and the list that was retrieved from the persistent list are equal")

        # A second persistent list that uses the same table should get the
        # same data.
        pl2 = PersistentList(self.table, self.db)
        for item in pl2:
            self.assertEqual(True, item in pl)
        del pl2

        # Remove items from the persistent list.
        for item in items:
            len_before = len(pl)
            pl.remove(item)
            len_after = len(pl)
            self.assertEqual(len_before - 1, len_after, "removing")
        self.assertEqual(0, len(pl), "The persistent list is empty.")


if __name__ == "__main__":
    unittest.main()

########NEW FILE########
__FILENAME__ = persistent_queue
"""persistent_queue.py Infinite persistent queue with in-place updates.

An infinite persistent queue that uses SQLite for storage and a in-memory list
for a partial in-memory cache (to allow for peeking).

Each item in the queue is assigned a key of your choosing (if none is given,
the item itself becomes the key). By using this key, one can then later update
the item in the queue (i.e. without changing the order of the queue), remove
the item from the queue, or even just get the item from the queue to perform
"smart" updates (i.e. based on the current value of the item corresponding to
the key).

This class is thread-safe.
"""


__author__ = "Wim Leers (work@wimleers.com)"
__version__ = "$Rev$"
__date__ = "$Date$"
__license__ = "GPL"


import sqlite3
import cPickle
import hashlib
import types
import threading


# Define exceptions.
class PersistentQueueError(Exception): pass
class Empty(PersistentQueueError): pass
class AlreadyExists(PersistentQueueError): pass
class UpdateForNonExistingKey(PersistentQueueError): pass


class PersistentQueue(object):
    """a persistent queue with sqlite back-end designed for infinite queues"""

    def __init__(self, table, dbfile="persistent_queue.db", max_in_memory=100, min_in_memory=50):
        self.size = 0

        # Initialize the database.
        self.dbcon = None
        self.dbcur = None
        self.table = table
        self.__prepare_db(dbfile)

        # Initialize the memory queue.
        self.max_in_memory = max_in_memory
        self.min_in_memory = min_in_memory
        self.memory_queue = []
        self.lowest_id_in_queue  = 0
        self.highest_id_in_queue = 0
        self.has_new_data = False

        # Locking is necessary to prevent a get() or peek() while an update()
        # is in progress.
        self.lock = threading.Lock()

        # Update the size property.
        self.dbcur.execute("SELECT COUNT(id) FROM %s" % (self.table))
        self.size = self.dbcur.fetchone()[0]


    def __prepare_db(self, dbfile):
        sqlite3.register_converter("pickle", cPickle.loads)
        self.dbcon = sqlite3.connect(dbfile, detect_types=sqlite3.PARSE_DECLTYPES|sqlite3.PARSE_COLNAMES)
        self.dbcon.text_factory = unicode # This is the default, but we set it explicitly, just to be sure.
        self.dbcur = self.dbcon.cursor()
        self.dbcur.execute("CREATE TABLE IF NOT EXISTS %s(id INTEGER PRIMARY KEY AUTOINCREMENT, item pickle, key CHAR(32))" % (self.table))
        self.dbcur.execute("CREATE UNIQUE INDEX IF NOT EXISTS unique_key ON %s (key)" % (self.table))
        self.dbcon.commit()


    def __contains__(self, item):
        return self.dbcur.execute("SELECT COUNT(item) FROM %s WHERE item=?" % (self.table), (cPickle.dumps(item), )).fetchone()[0]


    def qsize(self):
        return self.size


    def empty(self):
        return self.size == 0


    def full(self):
        # We've got infinite storage.
        return False


    def put(self, item, key=None):
        # If no key is given, default to the item itself.
        if key is None:
            key = item

        # Insert the item into the database.
        md5 = PersistentQueue.__hash_key(key)
        self.lock.acquire()
        try:
            pickled_item = cPickle.dumps(item, cPickle.HIGHEST_PROTOCOL)
            self.dbcur.execute("INSERT INTO %s (item, key) VALUES(?, ?)" % (self.table), (sqlite3.Binary(pickled_item), md5))
        except sqlite3.IntegrityError:
            self.lock.release()
            raise AlreadyExists
        self.dbcon.commit()
        self.size += 1

        self.has_new_data = True

        self.lock.release()


    def peek(self):
        self.lock.acquire()
        if self.empty():
            self.lock.release()
            raise Empty
        else:
            self.__update_memory_queue()
            (id, item) = self.memory_queue[0]

            self.lock.release()

            return item


    def get(self):
        self.lock.acquire()
        
        if self.empty():
            self.lock.release()
            raise Empty
        else:
            self.__update_memory_queue()
            # Get the item from the memory queue and immediately delete it
            # from the database.
            (id, item) = self.memory_queue.pop(0)
            self.dbcur.execute("DELETE FROM %s WHERE id = ?" % (self.table), (id, ))
            self.dbcon.commit()
            self.size -= 1

            self.lock.release()

            return item


    def get_item_for_key(self, key):
        """necessary to be able to do smart update()s"""
        md5 = PersistentQueue.__hash_key(key)
        self.lock.acquire()
        self.dbcur.execute("SELECT item FROM %s WHERE key = ?" % (self.table), (md5, ))
        self.lock.release()

        result = self.dbcur.fetchone()
        if result is None:
            return None
        else:
            return result[0]


    def remove_item_for_key(self, key):
        """necessary to be able to do smart update()s"""
        md5 = PersistentQueue.__hash_key(key)
        self.lock.acquire()
        self.dbcur.execute("SELECT id FROM %s WHERE key = ?" % (self.table), (md5, ))
        result = self.dbcur.fetchone()
        if result is None:
            self.lock.release()
        else:
            id = result[0]
            self.dbcur.execute("DELETE FROM %s WHERE key = ?" % (self.table), (md5, ))
            self.dbcon.commit()
            self.size -= 1
            if id >= self.lowest_id_in_queue and id <= self.highest_id_in_queue:
                # Refresh the memory queue, because the updated item was in the
                # memory queue.
                self.__update_memory_queue(refresh=True)
            self.lock.release()


    def update(self, item, key):
        """update an item in the queue"""
        md5 = PersistentQueue.__hash_key(key)
        self.lock.acquire()
        self.dbcur.execute("SELECT id FROM %s WHERE key = ?" % (self.table), (md5, ))
        result = self.dbcur.fetchone()

        if result is None:
            self.lock.release()
            raise UpdateForNonExistingKey
        else:
            id = result[0]
            pickled_item = cPickle.dumps(item, cPickle.HIGHEST_PROTOCOL)
            self.dbcur.execute("UPDATE %s SET item = ? WHERE key = ?" % (self.table), (sqlite3.Binary(pickled_item), md5))
            self.dbcon.commit()

        if result is not None and id >= self.lowest_id_in_queue and id <= self.highest_id_in_queue:
            # Refresh the memory queue, because the updated item was in the
            # memory queue.
            self.__update_memory_queue(refresh=True)

        self.lock.release()


    @classmethod
    def __hash_key(cls, key):
        """calculate the md5 hash of the key"""
        if not isinstance(key, types.StringTypes):
            key = str(key)
        md5 = hashlib.md5(key.encode('utf-8')).hexdigest().decode('ascii')
        return md5


    def __update_memory_queue(self, refresh=False):
        if refresh:
            del self.memory_queue[:]

        # If the memory queue is too small, update it using the database.
        if self.has_new_data or len(self.memory_queue) < self.min_in_memory:
            # Store the lowest id that's in the memory queue (i.e. the id of
            # the first item). This is needed to be able to do refreshes.
            if len(self.memory_queue) == 0:
                self.lowest_id_in_queue = -1
            else:
                self.lowest_id_in_queue = self.memory_queue[0][0]

            # By default, we try to fetch additional items. If refresh=True,
            # however, we simply rebuild the memory queue as it was (possibly
            # with some additional items).
            if not refresh:
                min_id = self.highest_id_in_queue
            else:
                min_id = self.lowest_id_in_queue - 1

            # Do the actual update.
            self.dbcur.execute("SELECT id, item FROM %s WHERE id > ? ORDER BY id ASC LIMIT 0,%d " % (self.table, self.max_in_memory - len(self.memory_queue)), (min_id, ))
            resultList = self.dbcur.fetchall()
            for id, item in resultList:
                self.memory_queue.append((id, item))
                self.highest_id_in_queue = id

        # Now that we've updated, it's impossible that we've missed new data.
        self.has_new_data = False


class PersistentDataManager(object):
    def __init__(self, dbfile="persistent_queue.db"):
        # Initialize the database.
        self.dbcon = None
        self.dbcur = None
        self.__prepare_db(dbfile)


    def __prepare_db(self, dbfile):
        self.dbcon = sqlite3.connect(dbfile)
        self.dbcon.text_factory = unicode # This is the default, but we set it explicitly, just to be sure.
        self.dbcur = self.dbcon.cursor()


    def list(self, table):
        self.dbcur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE ?", (table, ))
        resultList = self.dbcur.fetchall()
        tables = []
        for row in resultList:
            tables.append(row[0])
        return tables


    def delete(self, table):
        self.dbcur.execute("DROP TABLE '%s'" % (table))
        self.dbcon.commit()

########NEW FILE########
__FILENAME__ = persistent_queue_test
"""Unit test for persistent_queue.py"""


__author__ = "Wim Leers (work@wimleers.com)"
__version__ = "$Rev$"
__date__ = "$Date$"
__license__ = "GPL"


from persistent_queue import *
import os
import os.path
import unittest


class TestConditions(unittest.TestCase):
    def setUp(self):
        self.table = "persistent_queue_test"
        self.db = "persistent_queue_test.db"
        if os.path.exists(self.db):
            os.remove(self.db)


    def tearDown(self):
        if os.path.exists(self.db):
            os.remove(self.db)


    def testEmpty(self):
        pq = PersistentQueue(self.table, self.db)
        self.assertRaises(Empty, pq.get)


    def testBasicUsage(self):
        pq = PersistentQueue(self.table, self.db)
        items = ["abc", 99, "xyz", 123]
        received_items = []

        # Queue the items.
        for item in items:
            pq.put(item)
        self.assertEqual(len(items), pq.qsize(), "The size of the original list matches the size of the queue.")

        # Dequeue the items.
        while not pq.empty():
            item = pq.get()
            received_items.append(item)
        self.assertEqual(items, received_items, "The original list and the list that was retrieved from the queue are equal")


    def testAdvancedUsage(self):
        pq = PersistentQueue(self.table, self.db, max_in_memory=5, min_in_memory=2)
        items = range(1, 100)
        received_items = []

        # Queue the items.
        for item in items:
            pq.put(item)
        self.assertEqual(len(items), pq.qsize(), "The size of the original list matches the size of the queue.")

        # Peeking should not affect the queue.
        size_before = pq.qsize()
        first_item = pq.peek()
        self.assertEqual(first_item, items[0], "Peeking works correctly.")
        size_after = pq.qsize()
        self.assertEqual(size_before, size_after, "Peeking should not affect the queue.")

        # Dequeue the items.
        while not pq.empty():
            item = pq.get()
            received_items.append(item)
        self.assertEqual(items, received_items, "The original list and the list that was retrieved from the queue are equal")


    def testUniquenessAndUpdating(self):
        # Inserting the same item twice should not be allowed
        pq = PersistentQueue(self.table, self.db)
        item = "some item"
        pq.put(item)
        pq.put("some other item")
        self.assertRaises(AlreadyExists, pq.put, item)

        # Empty the queue again.
        while not pq.empty():
            pq.get()

        # Inserting the same item twice but with different keys should be
        # allowed.
        pq = PersistentQueue(self.table, self.db)
        pq.put(item, "some key")
        pq.put(item, "some other key")

        # It should be impossible to update when a non-existing key is given.
        self.assertRaises(UpdateForNonExistingKey, pq.update, "new value", "some key that does not exist")

        # It should be possible to update an item in the queue, given its
        # key.
        pq.update("yarhar", "some key")
        self.assertEquals(pq.qsize(), 2)
        self.assertEquals(pq.get(), "yarhar")
        self.assertEquals(pq.get(), item)


    def testFileConveyorUseCase(self):
        pq = PersistentQueue(self.table)
        events = [
            ('/foo/bar', 'CREATED'),
            ('/foo/baz', 'CREATED'),
            ('/foo/bar', 'MODIFIED'),
            ('/yar/har', 'CREATED'),
            ('/foo/bar', 'DELETED'),
            ('/foo/baz', 'DELETED')
        ]

        for i in xrange(len(events)):
            item = pq.get_item_for_key(events[i][0])
            if item is None:
                pq.put(events[i], events[i][0])
            else:
                if item[1] == 'CREATED' and events[i][1] == 'DELETED':
                    pq.remove_item_for_key(events[i][0])
                else:
                    pq.update(events[i], events[i][0])

        self.assertEquals(pq.qsize(), 2)
        self.assertEquals(pq.get(), events[4])
        self.assertEquals(pq.get(), events[3])


if __name__ == "__main__":
    unittest.main()

########NEW FILE########
__FILENAME__ = filename
__author__ = "Wim Leers (work@wimleers.com)"
__version__ = "$Rev$"
__date__ = "$Date$"
__license__ = "GPL"


from processor import *
import os.path
import shutil
import hashlib


class Base(Processor):
    """replaces one set of strings with another set"""


    valid_extensions = () # Any extension is valid.


    def __init__(self, input_file, original_file, document_root, base_path, process_for_server, parent_logger, working_dir="/tmp", search=[], replace=[]):
        Processor.__init__(self, input_file, original_file, document_root, base_path, process_for_server, parent_logger, working_dir)
        self.search  = search
        self.replace = replace


    def run(self):
        # Get the parts of the original file.
        (path, basename, name, extension) = self.get_path_parts(self.original_file)

        # Update the file's base name.
        new_filename = basename
        for i in range(0, len(self.search)):
            new_filename = new_filename.replace(self.search[i], self.replace[i])

        # Set the output file base name.
        self.set_output_file_basename(new_filename)

        # Copy the file.
        shutil.copyfile(self.input_file, self.output_file)

        return self.output_file


class SpacesToUnderscores(Base):
  """replaces spaces in the filename with underscores ("_")"""

  def __init__(self, input_file, original_file, document_root, base_path, process_for_server, parent_logger, working_dir="/tmp", search=[], replace=[]):
      Base.__init__(self,
                    input_file,
                    original_file,
                    document_root,
                    base_path,
                    process_for_server,
                    parent_logger,
                    working_dir,
                    [" "],
                    ["_"]
                    )


class SpacesToDashes(Base):
    """replaces spaces in the filename with dashes ("-")"""

    def __init__(self, input_file, original_file, document_root, base_path, process_for_server, parent_logger, working_dir="/tmp", search=[], replace=[]):
        Base.__init__(self,
                      input_file,
                      original_file,
                      document_root,
                      base_path,
                      process_for_server,
                      parent_logger,
                      working_dir,
                      [" "],
                      ["-"]
                      )


if __name__ == "__main__":
    import time

    p = SpacesToUnderscores("test this.txt")
    print p.run()
    p = SpacesToDashes("test this.txt")
    print p.run()

########NEW FILE########
__FILENAME__ = google_closure_compiler
__author__ = "Wim Leers (work@wimleers.com)"
__version__ = "$Rev$"
__date__ = "$Date$"
__license__ = "GPL"


from processor import *
import os
import os.path


class GoogleClosureCompiler(Processor):
    """compresses .js files with Google Closure Compiler"""


    valid_extensions = (".js")


    def run(self):
        # We don't rename the file, so we can use the default output file.

        # Run Google Closure Compiler on the file.
        compiler_path = os.path.join(self.processors_path, "compiler.jar")
        (stdout, stderr) = self.run_command("java -jar %s --js %s --js_output_file %s" % (compiler_path, self.input_file, self.output_file))

        # Raise an exception if an error occurred.
        if not stderr == "":
            raise ProcessorError(stderr)

        return self.output_file

########NEW FILE########
__FILENAME__ = image_optimizer
__author__ = "Wim Leers (work@wimleers.com)"
__version__ = "$Rev$"
__date__ = "$Date$"
__license__ = "GPL"


from processor import *
import os
import stat


COPY_METADATA_NONE = "none"
COPY_METADATA_ALL  = "all"
FILENAME_MUTABLE   = True
FILENAME_IMMUTABLE = False


class Base(Processor):
    """optimizes image files losslessly (GIF, PNG, JPEG, animated GIF)"""


    valid_extensions = (".gif", ".png", ".jpg", ".jpeg")


    def __init__(self, input_file, original_file, document_root, base_path, process_for_server, parent_logger, working_dir="/tmp", copy_metadata=COPY_METADATA_NONE, filename_mutable=FILENAME_MUTABLE):
        Processor.__init__(self, input_file, original_file, document_root, base_path, process_for_server, parent_logger, working_dir)
        self.copy_metadata    = copy_metadata
        self.filename_mutable = filename_mutable
        self.devnull = open(os.devnull, 'w')


    def run(self):
        # Get the parts of the original file.
        (path, basename, name, extension) = self.get_path_parts(self.original_file)

        format = self.identify_format(self.input_file)

        if format == "GIF":
            if self.filename_mutable == FILENAME_MUTABLE:
                tmp_file = os.path.join(self.working_dir, path, name + ".tmp.png")
                self.set_output_file_basename(name + ".png")
                self.optimize_GIF(self.input_file, tmp_file, self.output_file)
            else:
                # Don't do any processing at all: return the input file.
                self.set_output_file_basename(self.input_file)

        elif format == "PNG":
            self.optimize_PNG(self.input_file, self.output_file)

        elif format == "JPEG":
            self.optimize_JPEG(self.input_file, self.output_file, self.copy_metadata)

        # Animated GIF
        elif len(format) >= 6 and format[0:6] == "GIFGIF":
            self.optimize_animated_GIF(self.input_file, self.output_file)

        else:
            # This should never happen, but in case there's a file with an extension
            # that matches one of the supported file types, but is in fact not such
            # an image, we return the input file to ensure the chain can continue.
            self.set_output_file_basename(self.input_file)
        
        # Clean up things.
        self.devnull.close()

        return self.output_file


    def identify_format(self, filename):
        (stdout, stderr) = self.run_command("identify -format %%m \"%s\"" % (filename))
        return stdout


    def optimize_GIF(self, input_file, tmp_file, output_file):
        # Convert to temporary PNG.
        self.run_command("convert %s %s" % (input_file, tmp_file))
        # Optimize temporary PNG.
        self.run_command("pngcrush -rem alla -reduce \"%s\" \"%s\"" % (tmp_file, output_file))
        # Remove temporary PNG.
        os.remove(tmp_file)


    def optimize_PNG(self, input_file, output_file):
        self.run_command("pngcrush -rem alla -reduce \"%s\" \"%s\"" % (input_file, output_file))


    def optimize_JPEG(self, input_file, output_file, copy_metadata):
        filesize = os.stat(input_file)[stat.ST_SIZE]
        # If the file is 10 KB or larger, JPEG's progressive mode
        # typically results in a higher compression ratio.
        if filesize < 10 * 1024:
            self.run_command("jpegtran -copy %s -optimize \"%s\" > \"%s\"" % (copy_metadata, input_file, output_file))
        else:
            self.run_command("jpegtran -copy %s -progressive -optimize \"%s\" > \"%s\"" % (copy_metadata, input_file, output_file))


    def optimize_animated_GIF(self, input_file, output_file):
        self.run_command("gifsicle -O2 \"%s\" > \"%s\"" % (input_file, output_file))


class Max(Base):
    """optimizes image files losslessly (GIF, PNG, JPEG, animated GIF)"""

    def __init__(self, input_file, original_file, document_root, base_path, process_for_server, parent_logger, working_dir="/tmp"):
        Base.__init__(self,
                      input_file,
                      original_file,
                      document_root,
                      base_path,
                      process_for_server,
                      parent_logger,
                      working_dir,
                      copy_metadata=COPY_METADATA_NONE, # Don't keep metadata
                      filename_mutable=FILENAME_MUTABLE # Do change filenames
                      )


class KeepMetadata(Base):
    """same as Max, but keeps JPEG metadata"""

    def __init__(self, input_file, original_file, document_root, base_path, process_for_server, parent_logger, working_dir="/tmp"):
        Base.__init__(self,
                      input_file,
                      original_file,
                      document_root,
                      base_path,
                      process_for_server,
                      parent_logger,
                      working_dir,
                      copy_metadata=COPY_METADATA_ALL,  # Do keep metadata
                      filename_mutable=FILENAME_MUTABLE # Don't change filenames
                      )


class KeepFilename(Base):
    """same as Max, but keeps the original filename (no GIF optimization)"""

    def __init__(self, input_file, original_file, document_root, base_path, process_for_server, parent_logger, working_dir="/tmp"):
        Base.__init__(self,
                      input_file,
                      original_file,
                      document_root,
                      base_path,
                      process_for_server,
                      parent_logger,
                      working_dir,
                      copy_metadata=COPY_METADATA_NONE,   # Don't keep metadata
                      filename_mutable=FILENAME_IMMUTABLE # Do keep filenames
                      )


class KeepMetadataAndFilename(Base):
    """same as Max, but keeps JPEG metadata and the original filename (no GIF optimization)"""

    def __init__(self, input_file, original_file, document_root, base_path, process_for_server, parent_logger, working_dir="/tmp"):
        Base.__init__(self,
                      input_file,
                      original_file,
                      document_root,
                      base_path,
                      process_for_server,
                      parent_logger,
                      working_dir,
                      copy_metadata=COPY_METADATA_ALL,    # Do keep metadata
                      filename_mutable=FILENAME_IMMUTABLE # Do keep filenames
                      )


if __name__ == "__main__":
    import time

    p = Max("logo.gif")
    print p.run()
    p = Max("test.png")
    print p.run()
    p = Max("test.jpg")
    print p.run()
    p = Max("animated.gif")
    print p.run()
    p = Max("processor.pyc")
    print p.run()

    # Should result in a JPEG file that contains all original metadata.
    p = KeepMetadata("test.jpg", "/tmp/KeepMetadata")
    print p.run()

    # Should keep the original GIF file, as the only possible optimizaton is
    # to convert it from GIF to PNG, but that would change the filename.
    p = KeepFilename("test.gif", "/tmp/KeepFilename")
    print p.run()

    # Should act as the combination of the two above
    p = KeepMetadataAndFilename("test.jpg", "/tmp/KeepMetadataAndFilename")
    print p.run()
    p = KeepMetadataAndFilename("test.gif", "/tmp/KeepMetadataAndFilename")
    print p.run()

########NEW FILE########
__FILENAME__ = link_updater
__author__ = "Wim Leers (work@wimleers.com)"
__version__ = "$Rev$"
__date__ = "$Date$"
__license__ = "GPL"


from processor import *
import os
import os.path
from cssutils import CSSParser
from cssutils.css import CSSStyleSheet
from cssutils import getUrls
from cssutils import replaceUrls

import logging
import sys
import sqlite3
from urlparse import urljoin
from settings import SYNCED_FILES_DB


class CSSURLUpdater(Processor):
    """replaces URLs in .css files with their counterparts on the CDN"""


    different_per_server = True
    valid_extensions = (".css")


    def run(self):
        # Step 0: ensure that the document_root and base_path variables are
        # set. If the file that's being processed was inside a source that has
        # either one or both not set, then this processor can't run.
        if self.document_root is None or self.base_path is None:
            raise DocumentRootAndBasePathRequiredException

        # We don't rename the file, so we can use the default output file.

        parser = CSSParser(log=None, loglevel=logging.CRITICAL)
        sheet = parser.parseFile(self.input_file)

        # Step 1: ensure the file has URLs. If it doesn't, we can stop the
        # processing.
        url_count = 0
        for url in getUrls(sheet):
            url_count +=1
            break
        if url_count == 0:
            return self.input_file

        # Step 2: resolve the relative URLs to absolute paths.
        replaceUrls(sheet, self.resolveToAbsolutePath)

        # Step 3: verify that each of these files has been synced.
        synced_files_db = urljoin(sys.path[0] + os.sep, SYNCED_FILES_DB)
        self.dbcon = sqlite3.connect(synced_files_db)
        self.dbcon.text_factory = unicode # This is the default, but we set it explicitly, just to be sure.
        self.dbcur = self.dbcon.cursor()
        all_synced = True
        for urlstring in getUrls(sheet):
            # Skip absolute URLs.
            if urlstring.startswith("http://") or urlstring.startswith("https://"):
                continue

            # Skip broken references in the CSS file. This would otherwise
            # prevent this CSS file from ever passing through this processor.
            if not os.path.exists(urlstring):
                continue

            # Get the CDN URL for the given absolute path.
            self.dbcur.execute("SELECT url FROM synced_files WHERE input_file=?", (urlstring, ))
            result = self.dbcur.fetchone()

            if result == None:
                raise RequestToRequeueException("The file '%s' has not yet been synced to the server '%s'" % (urlstring, self.process_for_server))
            else:
                cdn_url = result[0]

        # Step 4: resolve the absolute paths to CDN URLs.
        replaceUrls(sheet, self.resolveToCDNURL)

        # Step 5: write the updated CSS to the output file.
        f = open(self.output_file, 'w')
        f.write(sheet.cssText)
        f.close()

        return self.output_file


    def resolveToAbsolutePath(self, urlstring):
        """rewrite relative URLs (which are also relative paths, relative to
        the CSS file's path or to the document root) to absolute paths.
        Absolute URLs are returned unchanged."""

        # Skip absolute URLs.
        if urlstring.startswith("http://") or urlstring.startswith("https://"):
            return urlstring

        # Resolve paths that are relative to the document root.
        if urlstring.startswith(self.base_path):
            base_path_exists = os.path.exists(os.path.join(self.document_root, self.base_path[1:]))

            if not base_path_exists:
                # Strip the entire base path: this is a logical base path,
                # that is, it only exists in the URL (through a symbolic link)
                # and are not present in the path to the actual file.
                relative_path = urlstring[len(self.base_path):]
            else:
                # Strip the leading slash.
                relative_path = urlstring[1:]

            # Prepend the document root.
            absolute_path = os.path.join(self.document_root, relative_path)

            # Resolve any symbolic links in the absolute path.
            absolute_path = os.path.realpath(absolute_path)

            return absolute_path

        # Resolve paths that are relative to the CSS file's path.
        return urljoin(self.original_file, urlstring)


    def resolveToCDNURL(self, urlstring):
        """rewrite absolute paths to CDN URLs"""
        
        # Skip broken references in the CSS file. This would otherwise
        # prevent this CSS file from ever passing through this processor.
        if not os.path.exists(urlstring):
            return urlstring

        # Get the CDN URL for the given absolute file path.
        self.dbcur.execute("SELECT url FROM synced_files WHERE input_file=? AND server=?", (urlstring, self.process_for_server))
        return self.dbcur.fetchone()[0]

########NEW FILE########
__FILENAME__ = processor
__author__ = "Wim Leers (work@wimleers.com)"
__version__ = "$Rev$"
__date__ = "$Date$"
__license__ = "GPL"


# Define exceptions.
class ProcessorError(Exception): pass
class InvalidCallbackError(ProcessorError): pass
class FileIOError(ProcessorError): pass
class RequestToRequeueException(ProcessorError): pass
class DocumentRootAndBasePathRequiredException(ProcessorError): pass


import threading
import os
import os.path
import logging
import copy
import subprocess


class Processor(object):
    """base class for file processors"""


    def __init__(self, input_file, original_file, document_root, base_path, process_for_server, parent_logger, working_dir="/tmp"):
        self.input_file         = input_file
        self.original_file      = original_file
        self.document_root      = document_root
        self.base_path          = base_path
        self.process_for_server = process_for_server
        self.working_dir        = working_dir
        self.parent_logger      = parent_logger

        # Get the parts of the input file.
        (path, basename, name, extension) = self.get_path_parts(self.original_file)

        # The file will end up in the working directory, in its relative path.
        # It doesn't hurt to have empty directory trees, so create this
        # already here to simplify the processors themselves.
        output_file_path = os.path.join(self.working_dir, path)
        if not os.path.exists(output_file_path):
            os.makedirs(output_file_path)

        # Set the default output file: the input file's base name.
        self.set_output_file_basename(basename)

        # Calculate the path to the processors in the Processor class so
        # subclasses don't have to.
        self.processors_path = os.path.dirname(os.path.realpath(__file__))


    def run(self):
        raise NotImplemented


    def get_path_parts(self, path):
        """get the different parts of the file's path"""

        (path, basename) = os.path.split(path)
        (name, extension) = os.path.splitext(basename)

        # Return the original relative path instead of the absolute path,
        # which may be inside the working directory because the file has been
        # processed by one processor already.
        if path.startswith(self.working_dir):
            path = path[len(self.working_dir):]

        # Ensure no absolute path is returned, which would make os.path.join()
        # fail.
        path = path.lstrip(os.sep)

        return (path, basename, name, extension)


    def would_process_input_file(cls, input_file):
        """check if a given input file would be processed by this processor"""

        (path, extension) = os.path.splitext(input_file)

        # Get some variables "as if it were magic", i.e., from subclasses of
        # this class.
        valid_extensions = getattr(cls, "valid_extensions", ())

        # Does the input file have one of the valid extensions?
        if len(valid_extensions) > 0 and extension.lower() not in valid_extensions:
            return False

        return True
    would_process_input_file = classmethod(would_process_input_file)


    def validate_settings(self):
        """validate the input file and its extensions"""

        if not os.path.exists(self.input_file):
            return False
        if not self.__class__.would_process_input_file(self.input_file):
            return False
        return True


    def run_command(self, command):
        """run a command and get (stdout, stderr) back"""

        p = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        (stdout, stderr) = p.communicate()
        (stdout, stderr) = (stdout.rstrip(), stderr.rstrip())
        return (stdout, stderr)


    def set_output_file_basename(self, output_file_basename):
        """set the output file's basename (changing the path is not allowed)"""

        # Get the parts of the input file.
        (path, basename, name, extension) = self.get_path_parts(self.input_file)

        self.output_file = os.path.join(self.working_dir, path, output_file_basename)


class ProcessorChain(threading.Thread):
    """chains the given file processors (runs them in sequence)"""


    def __init__(self, processors, input_file, document_root, base_path, process_for_server, callback, error_callback, parent_logger, working_dir="/tmp"):
        if not callable(callback):
            raise InvalidCallbackError("callback function is not callable")
        if not callable(error_callback):
            raise InvalidCallbackError("error_callback function is not callable")

        self.processors         = processors
        self.input_file         = input_file
        self.output_file        = None
        self.document_root      = document_root
        self.base_path          = base_path
        self.process_for_server = process_for_server
        self.callback           = callback
        self.error_callback     = error_callback
        self.working_dir        = working_dir
        self.logger             = logging.getLogger(".".join([parent_logger, "ProcessorChain"]))

        self.parent_logger_for_processor = ".".join([parent_logger, "ProcessorChain"]);

        threading.Thread.__init__(self, name="ProcessorChainThread")


    def run(self):
        self.output_file = self.input_file

        # Run all processors in the chain.
        while len(self.processors):
            # Get next processor.
            processor_classname = self.processors.pop(0)

            # Get a reference to that class.
            (modulename, classname) = processor_classname.rsplit(".", 1)
            module = __import__(modulename, globals(), locals(), [classname])
            processor_class = getattr(module, classname)

            # Run the processor.
            old_output_file = self.output_file
            processor = processor_class(            
                input_file         = self.output_file,
                original_file      = self.input_file,
                document_root      = self.document_root,
                base_path          = self.base_path,
                process_for_server = self.process_for_server,
                parent_logger      = self.parent_logger_for_processor,
                working_dir        = self.working_dir,
            )
            if processor.validate_settings():
                self.logger.debug("Running the processor '%s' on the file '%s'." % (processor_classname, self.output_file))
                try:
                    self.output_file = processor.run()
                except RequestToRequeueException, e:
                    self.logger.warning("The processor '%s' has requested to requeue the file '%s'. Message: %s." % (processor_classname, self.input_file, e))
                    self.error_callback(self.input_file)
                    return
                except DocumentRootAndBasePathRequiredException, e:
                    self.logger.warning("The processor '%s' has skipped processing the file '%s' because the document root and/or base path are not set for the source associated with the file." % (processor_classname, self.input_file))
                except Exception, e:
                    self.logger.error("The processsor '%s' has failed while processing the file '%s'. Exception class: %s. Message: %s." % (processor_classname, self.input_file, e.__class__, e))
                    self.error_callback(self.input_file)
                    return
                else:
                    self.logger.debug("The processor '%s' has finished processing the file '%s', the output file is '%s'." % (processor_classname, self.input_file, self.output_file))

            # Delete the old output file if applicable. But never ever remove
            # the input file!
            if old_output_file != self.output_file and old_output_file != self.input_file:
                os.remove(old_output_file)

        # All done, call the callback!
        self.callback(self.input_file, self.output_file)


class ProcessorChainFactory(object):
    """produces ProcessorChain objects whenever requested"""


    def __init__(self, parent_logger, working_dir="/tmp"):
        self.parent_logger = parent_logger
        self.working_dir   = working_dir


    def make_chain_for(self, input_file, processors, document_root, base_path, process_for_server, callback, error_callback):
        return ProcessorChain(copy.copy(processors), input_file, document_root, base_path, process_for_server, callback, error_callback, self.parent_logger, self.working_dir)

########NEW FILE########
__FILENAME__ = processor_sample
import sys
import os
import os.path
import time
import logging.handlers
sys.path.append(os.path.abspath('..'))


from processor import *
import filename
import image_optimizer
import link_updater
import unique_filename
import yui_compressor


if __name__ == "__main__":
    # Set up a logger.
    logger = logging.getLogger("test")
    logger.setLevel(logging.DEBUG)
    handler = logging.handlers.RotatingFileHandler("processor.log")
    logger.addHandler(handler)

    def callback(input_file, output_file):
        print """"CALLBACK FIRED:
                   input_file='%s'
                   output_file='%s'""" % (input_file, output_file)

    def error_callback(input_file):
       print """"ERROR_CALLBACK FIRED:
                  input_file='%s'""" % (input_file)

    # Use a ProcessorChainFactory.
    document_root = "/htdocs/example.com/subsite"
    base_path = "/subsite/"
    processors = [
        "image_optimizer.KeepFilename",
        "unique_filename.Mtime",
        "link_updater.CSSURLUpdater",
        "yui_compressor.YUICompressor"
    ]
    factory = ProcessorChainFactory("test")
    chain = factory.make_chain_for("test.jpg", processors, document_root, base_path, callback, error_callback)
    chain.run()
    chain = factory.make_chain_for("test.png", processors, document_root, base_path, callback, error_callback)
    chain.run()
    chain = factory.make_chain_for("test.css", processors, document_root, base_path, callback, error_callback)
    chain.run()
    chain = factory.make_chain_for("test.js", processors, document_root, base_path, callback, error_callback)
    chain.run()

########NEW FILE########
__FILENAME__ = unique_filename
__author__ = "Wim Leers (work@wimleers.com)"
__version__ = "$Rev$"
__date__ = "$Date$"
__license__ = "GPL"


from processor import *
import stat
import shutil
import hashlib


class Mtime(Processor):
    """gives the file a unique filename based on its mtime"""


    valid_extensions = () # Any extension is valid.


    def run(self):
        # Get the parts of the input file.
        (path, basename, name, extension) = self.get_path_parts(self.original_file)

        # Calculate the mtime on the original file, not the input file.
        mtime = os.stat(self.original_file)[stat.ST_MTIME]

        # Set the output file base name.
        self.set_output_file_basename(name + "_" + str(mtime) + extension)

        # Copy the input file to the output file.
        shutil.copyfile(self.input_file, self.output_file)

        return self.output_file


class MD5(Processor):
    """gives the file a unique filename based on its MD5 hash"""


    valid_extensions = () # Any extension is valid.


    def run(self):
        # Get the parts of the input file.
        (path, basename, name, extension) = self.get_path_parts(self.original_file)

        # Calculate the MD5 hash on the original file, not the input file.
        md5 = self.md5(self.original_file)

        # Set the output file base name.
        self.set_output_file_basename(name + "_" + md5 + extension)

        # Copy the input file to the output file.
        shutil.copyfile(self.input_file, self.output_file)

        return self.output_file


    def md5(self, filename):
        """compute the md5 hash of the specified file"""
        m = hashlib.md5()
        try:
            f = open(filename, "rb")
        except IOError:
            raise FileIOError("Unable to open the file in readmode: %s" % (filename))

        line = f.readline()
        while line:
            m.update(line)
            line = f.readline()
        f.close()
        return m.hexdigest()


if __name__ == "__main__":
    import time

    p = Mtime("logo.gif")
    print p.run()
    p = MD5("logo.gif")
    print p.run()

########NEW FILE########
__FILENAME__ = yui_compressor
__author__ = "Wim Leers (work@wimleers.com)"
__version__ = "$Rev$"
__date__ = "$Date$"
__license__ = "GPL"


from processor import *
import os
import os.path
import shutil


class YUICompressor(Processor):
    """compresses .css and .js files with YUI Compressor"""


    valid_extensions = (".css", ".js")


    def run(self):
        # We don't rename the file, so we can use the default output file.

        # The YUI Compressor crashes if the output file already exists.
        # Therefor, we're using a temporary output file and copying that to
        # the final output file afterwards.
        tmp_file = self.output_file + ".tmp"
        if os.path.exists(tmp_file):
            os.remove(tmp_file)

        # Run YUI Compressor on the file.
        yuicompressor_path = os.path.join(self.processors_path, "yuicompressor.jar")
        (stdout, stderr) = self.run_command("java -jar %s %s -o %s" % (yuicompressor_path, self.input_file, tmp_file))

        # Copy the temporary output file to the final output file and remove
        # the temporary output file.
        shutil.copy(tmp_file, self.output_file)
        os.remove(tmp_file)

        # Raise an exception if an error occurred.
        if not stderr == "":
            raise ProcessorError(stderr)

        return self.output_file

########NEW FILE########
__FILENAME__ = settings
__author__ = "Wim Leers (work@wimleers.com)"
__version__ = "$Rev$"
__date__ = "$Date$"
__license__ = "GPL"


import logging


RESTART_AFTER_UNHANDLED_EXCEPTION = True
RESTART_INTERVAL = 10
LOG_FILE = './fileconveyor.log'
PID_FILE = '~/.fileconveyor.pid'
PERSISTENT_DATA_DB = './persistent_data.db'
SYNCED_FILES_DB = './synced_files.db'
WORKING_DIR = '/tmp/fileconveyor'
MAX_FILES_IN_PIPELINE = 50
MAX_SIMULTANEOUS_PROCESSORCHAINS = 1
MAX_SIMULTANEOUS_TRANSPORTERS = 10
MAX_TRANSPORTER_QUEUE_SIZE = 1
QUEUE_PROCESS_BATCH_SIZE = 20
CALLBACKS_CONSOLE_OUTPUT = False
CONSOLE_LOGGER_LEVEL = logging.WARNING
FILE_LOGGER_LEVEL = logging.INFO
RETRY_INTERVAL = 30

########NEW FILE########
__FILENAME__ = transporter
"""transporter.py Transporter class for daemon"""


__author__ = "Wim Leers (work@wimleers.com)"
__version__ = "$Rev$"
__date__ = "$Date$"
__license__ = "GPL"


from django.core.files.storage import Storage
from django.core.files import File


# Define exceptions.
class TransporterError(Exception): pass
class InvalidSettingError(TransporterError): pass
class MissingSettingError(TransporterError): pass
class InvalidCallbackError(TransporterError): pass
class ConnectionError(TransporterError): pass
class InvalidActionError(TransporterError): pass


import threading
import Queue
import time
import os.path
import logging
from sets import Set, ImmutableSet


class Transporter(threading.Thread):
    """threaded abstraction around a Django Storage subclass"""


    ACTIONS = {
        "ADD_MODIFY" : 0x00000001,
        "DELETE"     : 0x00000002,
    }


    def __init__(self, settings, callback, error_callback, parent_logger):
        if not callable(callback):
            raise InvalidCallbackError("callback function is not callable")
        if not callable(error_callback):
            raise InvalidCallbackError("error_callback function is not callable")

        self.settings       = settings
        self.storage        = None
        self.lock           = threading.Lock()
        self.queue          = Queue.Queue()
        self.callback       = callback
        self.error_callback = error_callback
        self.logger         = logging.getLogger(".".join([parent_logger, "Transporter"]))
        self.die            = False

        # Validate settings.
        self.validate_settings()

        threading.Thread.__init__(self, name="TransporterThread")


    def run(self):
        while not self.die:
            # Sleep a little bit if there's no work.
            if self.queue.qsize() == 0:
                time.sleep(0.5)
            else:
                self.lock.acquire()
                (src, dst, action, callback, error_callback) = self.queue.get()
                self.lock.release()

                self.logger.debug("Running the transporter '%s' to sync '%s'." % (self.name, src))
                try:
                    # Sync the file: either add/modify it, or delete it.
                    if action == Transporter.ADD_MODIFY:
                        # Sync the file.
                        f = File(open(src, "rb"))
                        if self.storage.exists(dst):
                            self.storage.delete(dst)
                        self.storage.save(dst, f)
                        f.close()
                        # Calculate the URL.
                        url = self.storage.url(dst)
                        url = self.alter_url(url)
                    else:
                        if self.storage.exists(dst):
                            self.storage.delete(dst)
                        url = None

                    self.logger.debug("The transporter '%s' has synced '%s'." % (self.name, src))

                    # Call the callback function. Use the callback function
                    # defined for this Transporter (self.callback), unless
                    # an alternative one was defined for this file (callback).
                    if not callback is None:
                        callback(src, dst, url, action)
                    else:
                        self.callback(src, dst, url, action)

                except Exception, e:
                    self.logger.error("The transporter '%s' has failed while transporting the file '%s' (action: %d). Error: '%s'." % (self.name, src, action, e))

                    # Call the error_callback function. Use the error_callback
                    # function defined for this Transporter
                    # (self.error_callback), unless an alternative one was
                    # defined for this file (error_callback).
                    if not callback is None:
                        error_callback(src, dst, action)
                    else:
                        self.error_callback(src, dst, action)


    def alter_url(self, url):
        """allow some classes to alter the generated URL"""
        return url


    def stop(self):
        self.lock.acquire()
        self.die = True
        self.lock.release()


    def validate_settings(self):
        # Get some variables "as if it were magic", i.e., from subclasses of
        # this class.
        valid_settings      = self.valid_settings
        required_settings   = self.required_settings
        configured_settings = Set(self.settings.keys())

        if len(configured_settings.difference(valid_settings)):
            raise InvalidSettingError

        if len(required_settings.difference(configured_settings)):
            raise MissingSettingError


    def sync_file(self, src, dst=None, action=None, callback=None, error_callback=None):
        # Set the default value here because Python won't allow it sooner.
        if dst is None:
            dst = src
        if action is None:
            action = Transporter.ADD_MODIFY
        elif action not in Transporter.ACTIONS.values():
            raise InvalidActionError

        # If dst is relative to the root, strip the leading slash.
        if dst.startswith("/"):
            dst = dst[1:]

        self.lock.acquire()
        self.queue.put((src, dst, action, callback, error_callback))
        self.lock.release()


    def qsize(self):
        self.lock.acquire()
        qsize = self.queue.qsize()
        self.lock.release()
        return qsize


# Make EVENTS' members directly accessible through the class dictionary.
for name, mask in Transporter.ACTIONS.iteritems():
    setattr(Transporter, name, mask)

########NEW FILE########
__FILENAME__ = transporter_cf
from transporter import *
from transporter_s3 import TransporterS3


TRANSPORTER_CLASS = "TransporterCF"


class TransporterCF(TransporterS3):


    name              = 'CF'
    valid_settings    = ImmutableSet(["access_key_id", "secret_access_key", "bucket_name", "distro_domain_name", "bucket_prefix"])
    required_settings = ImmutableSet(["access_key_id", "secret_access_key", "bucket_name", "distro_domain_name"])


    def __init__(self, settings, callback, error_callback, parent_logger=None):
        return TransporterS3.__init__(self, settings, callback, error_callback, parent_logger)


    def alter_url(self, url):
        return url.replace(
            self.settings["bucket_prefix"] + self.settings["bucket_name"] + ".s3.amazonaws.com",
            self.settings["distro_domain_name"]
        )


def create_distribution(access_key_id, secret_access_key, origin, comment="", cnames=None):
    import time
    from boto.cloudfront import CloudFrontConnection

    """utility function to create a new distribution"""
    c = CloudFrontConnection(
        access_key_id,
        secret_access_key
    )
    d = c.create_distribution(origin, True, '', cnames, comment)
    print """Created distribution
    - domain name: %s
    - origin: %s
    - status: %s
    - comment: %s
    - id: %s

    Over the next few minutes, the distribution will become active. This
    function will keep running until that happens.
    """ % (d.domain_name, d.config.origin, d.status, d.config.comment, d.id)

    # Keep polling CloudFront every 5 seconds until the status changes from
    # "InProgress" to (hopefully) "Deployed".
    print "\n"
    id = d.id
    while d.status == "InProgress":
        d = c.get_distribution_info(id)
        print "."
        time.sleep(5)
    print "\nThe distribution has been deployed!"

########NEW FILE########
__FILENAME__ = transporter_cloudfiles
from transporter import *
from cumulus.storage import CloudFilesStorage


TRANSPORTER_CLASS = "TransporterCloudFiles"


class TransporterCloudFiles(Transporter):

    name              = 'Cloud Files'
    valid_settings    = ImmutableSet(["username", "api_key", "container"])
    required_settings = ImmutableSet(["username", "api_key", "container"])


    def __init__(self, settings, callback, error_callback, parent_logger=None):
        Transporter.__init__(self, settings, callback, error_callback, parent_logger)

        # Raise exception when required settings have not been configured.
        configured_settings = Set(self.settings.keys())
        if not "username" in configured_settings:
            raise ImpropertlyConfigured, "username not set" 
        if not "api_key" in configured_settings:
            raise ImpropertlyConfigured, "api_key not set" 
        if not "container" in configured_settings:
            raise ImpropertlyConfigured, "container not set" 

        # Map the settings to the format expected by S3Storage.
        try:
            self.storage = CloudFilesStorage(
            self.settings["username"],
            self.settings["api_key"],
            self.settings["container"]
            )
        except Exception, e:
            if e.__class__ == cloudfiles.errors.AuthenticationFailed:
                raise ConnectionError, "Authentication failed"
            else:
                raise ConnectionError(e)

########NEW FILE########
__FILENAME__ = transporter_ftp
from transporter import *
from storages.backends.ftp import FTPStorage


TRANSPORTER_CLASS = "TransporterFTP"


class TransporterFTP(Transporter):


    name              = 'FTP'
    valid_settings    = ImmutableSet(["host", "username", "password", "url", "port", "path"])
    required_settings = ImmutableSet(["host", "username", "password", "url"])


    def __init__(self, settings, callback, error_callback, parent_logger=None):
        Transporter.__init__(self, settings, callback, error_callback, parent_logger)

        # Fill out defaults if necessary.
        configured_settings = Set(self.settings.keys())
        if not "port" in configured_settings:
            self.settings["port"] = 21
        if not "path" in configured_settings:
            self.settings["path"] = ""

        # Map the settings to the format expected by FTPStorage.
        location = "ftp://" + self.settings["username"] + ":" + self.settings["password"] + "@" + self.settings["host"] + ":" + str(self.settings["port"]) + self.settings["path"]
        self.storage = FTPStorage(location, self.settings["url"])
        try:
            self.storage._start_connection()
        except Exception, e:            
            raise ConnectionError(e)

########NEW FILE########
__FILENAME__ = transporter_s3
from transporter import *
from storages.backends.s3boto import S3BotoStorage


TRANSPORTER_CLASS = "TransporterS3"


class TransporterS3(Transporter):


    name              = 'S3'
    valid_settings    = ImmutableSet(["access_key_id", "secret_access_key", "bucket_name", "bucket_prefix"])
    required_settings = ImmutableSet(["access_key_id", "secret_access_key", "bucket_name"])
    headers = {
        'Expires':       'Tue, 20 Jan 2037 03:00:00 GMT', # UNIX timestamps will stop working somewhere in 2038.
        'Cache-Control': 'max-age=315360000',             # Cache for 10 years.
        'Vary' :         'Accept-Encoding',               # Ensure S3 content can be accessed from behind proxies.
    }


    def __init__(self, settings, callback, error_callback, parent_logger=None):
        Transporter.__init__(self, settings, callback, error_callback, parent_logger)

        # Fill out defaults if necessary.
        configured_settings = Set(self.settings.keys())
        if not "bucket_prefix" in configured_settings:
            self.settings["bucket_prefix"] = ""

        # Map the settings to the format expected by S3Storage.
        try:
            self.storage = S3BotoStorage(
                self.settings["bucket_name"].encode('utf-8'), 
                self.settings["access_key_id"].encode('utf-8'),
                self.settings["secret_access_key"].encode('utf-8'),
                "public-read",
                "public-read",
                self.__class__.headers
            )
        except Exception, e:            
            raise ConnectionError(e)

########NEW FILE########
__FILENAME__ = transporter_sample
import sys
import os
import os.path
import time
import subprocess
import tempfile


from transporter_ftp import *
from transporter_s3 import *
from transporter_cf import *
from transporter_none import *


if __name__ == "__main__":
    # Set up logger.
    logger = logging.getLogger("Test")
    logger.setLevel(logging.DEBUG)
    h = logging.StreamHandler()
    h.setLevel(logging.DEBUG)
    logger.addHandler(h)

    def callback(src, dst, url, action):
        print """CALLBACK FIRED:
                    src='%s'
                    dst='%s'
                    url='%s'
                    action=%d""" % (src, dst, url, action)

    def error_callback(src, dst, action):
        print """ERROR CALLBACK FIRED:
                    src='%s'
                    dst='%s'
                    action=%d""" % (src, dst, action)

    # FTP
    settings = {
        "host"     : "your ftp host",
        "username" : "your username",
        "password" : "your password",
        "url"      : "your base URL"
    }
    try:
        ftp = TransporterFTP(settings, callback, error_callback, "Test")
    except Exception, e:
        print "Error occurred in TransporterFTP:", e
    else:
        ftp.start()
        ftp.sync_file("transporter.py")
        ftp.sync_file("drupal-5-6.png")
        ftp.sync_file("subdir/bmi-chart.png")
        ftp.sync_file("subdir/bmi-chart.png", "subdir/bmi-chart.png", Transporter.DELETE)
        time.sleep(5)
        ftp.stop()


    # Amazon S3
    settings = {
        "access_key_id"      : "your access key id",
        "secret_access_key"  : "your secret access key",
        "bucket_name"        : "your bucket name",
    }
    try:
        s3 = TransporterS3(settings, callback, error_callback, "Test")
    except ConnectionError, e:
        print "Error occurred in TransporterS3:", e
    else:
        s3.start()
        s3.sync_file("transporter.py")
        s3.sync_file("drupal-5-6.png")
        s3.sync_file("subdir/bmi-chart.png")
        s3.sync_file("subdir/bmi-chart.png", "subdir/bmi-chart.png", Transporter.DELETE)
        time.sleep(5)
        s3.stop()


    # Amazon CloudFront
    settings = {
        "access_key_id"      : "your access key id",
        "secret_access_key"  : "your secret access key",
        "bucket_name"        : "your bucket name",
        "distro_domain_name" : "your-distro-domain-name.cloudfront.net",
    }
    try:
        cf = TransporterCF(settings, callback, error_callback, "Test")
    except ConnectionError, e:
        print "Error occurred in TransporterCF:", e
    else:
        cf.start()
        cf.sync_file("transporter.py")
        cf.sync_file("drupal-5-6.png")
        cf.sync_file("subdir/bmi-chart.png")
        cf.sync_file("subdir/bmi-chart.png", "subdir/bmi-chart.png", Transporter.DELETE)
        time.sleep(5)
        cf.stop()


    # None
    settings = {
        "location"     : "/htdocs/static.example.com/",
        "url"          : "http://static.example.com/",
        "symlinkWithin": os.path.abspath('')
    }
    try:
        none = TransporterNone(settings, callback, error_callback, "Test")
    except ConnectionError, e:
        print "Error occurred in TransporterNone:", e
    else:
        none.start()
        none.sync_file("transporter.py")
        none.sync_file("drupal-5-6.png")
        none.sync_file("subdir/bmi-chart.png")
        subprocess.call("echo yarhar > $TMPDIR/foobar.txt", shell=True, stdout=subprocess.PIPE)
        none.sync_file(os.path.join(tempfile.gettempdir(), "foobar.txt"))
        none.sync_file("subdir/bmi-chart.png", "subdir/bmi-chart.png", Transporter.DELETE)
        time.sleep(5)
        none.stop()

########NEW FILE########
__FILENAME__ = transporter_sftp
from transporter import *
from storages.backends.sftpstorage import SFTPStorage


TRANSPORTER_CLASS = "TransporterSFTP"


class TransporterSFTP(Transporter):


    name              = 'SFTP'
    valid_settings    = ImmutableSet(["host", "username", "password", "url", "port", "path", "key"])
    required_settings = ImmutableSet(["host", "username", "url"])

    def __init__(self, settings, callback, error_callback, parent_logger=None):
        Transporter.__init__(self, settings, callback, error_callback, parent_logger)

        # Fill out defaults if necessary.
        configured_settings = Set(self.settings.keys())
        if not "port" in configured_settings:
            self.settings["port"] = 22
        if not "path" in configured_settings:
            self.settings["path"] = ""

        # Map the settings to the format expected by FTPStorage.
        if "password" in configured_settings:
          location = "sftp://" + self.settings["username"] + ":" + self.settings["password"] + "@" + self.settings["host"] + ":" + str(self.settings["port"]) + self.settings["path"]
        else:
          location = "sftp://" + self.settings["username"] + "@" + self.settings["host"] + ":" + str(self.settings["port"]) + self.settings["path"]

        key = None
        if "key" in configured_settings:
            key = self.settings["key"]

        self.storage = SFTPStorage(location, self.settings["url"], key)
        self.storage._start_connection()
        try:
            self.storage._start_connection()
        except Exception, e:
            raise ConnectionError(e)

########NEW FILE########
__FILENAME__ = transporter_symlink_or_copy
from transporter import *
from storages.backends.symlinkorcopy import SymlinkOrCopyStorage


TRANSPORTER_CLASS = "TransporterSymlinkOrCopy"


class TransporterSymlinkOrCopy(Transporter):


    name              = 'SYMLINK_OR_COPY'
    valid_settings    = ImmutableSet(["location", "url", "symlinkWithin"])
    required_settings = ImmutableSet(["location", "url", "symlinkWithin"])


    def __init__(self, settings, callback, error_callback, parent_logger=None):
        Transporter.__init__(self, settings, callback, error_callback, parent_logger)

        # Map the settings to the format expected by SymlinkStorage.
        self.storage = SymlinkOrCopyStorage(self.settings["location"],
                                            self.settings["url"],
                                            self.settings["symlinkWithin"]
                                            )


########NEW FILE########
__FILENAME__ = upgrade
from settings import *
import sqlite3
import hashlib
import cPickle
import types

def upgrade_persistent_data_to_v10(db):
    sqlite3.register_converter("pickle", cPickle.loads)
    dbcon = sqlite3.connect(db, detect_types=sqlite3.PARSE_DECLTYPES|sqlite3.PARSE_COLNAMES)
    dbcon.text_factory = unicode # This is the default, but we set it explicitly, just to be sure.
    dbcur = dbcon.cursor()

    # Rename the table pipeline_queue to pipeline_queue_original.
    dbcur.execute("ALTER TABLE '%s' RENAME TO '%s'" % ("pipeline_queue", "pipeline_queue_original"))
    dbcon.commit()

    # Crete the table pipeline_queue according to the new schema.
    dbcur.execute("CREATE TABLE IF NOT EXISTS %s(id INTEGER PRIMARY KEY AUTOINCREMENT, item pickle, key CHAR(32))" % ("pipeline_queue"))
    dbcur.execute("CREATE UNIQUE INDEX IF NOT EXISTS unique_key ON %s (key)" % ("pipeline_queue"))
    dbcon.commit()

    # Provide Mock versions of FSMonitor and PersistentQueue.
    class FSMonitor(object):pass
    FSMonitor.EVENTS = {
        "CREATED"             : 0x00000001,
        "MODIFIED"            : 0x00000002,
        "DELETED"             : 0x00000004,
        "MONITORED_DIR_MOVED" : 0x00000008,
        "DROPPED_EVENTS"      : 0x00000016,
    }
    for name, mask in FSMonitor.EVENTS.iteritems():
        setattr(FSMonitor, name, mask)
    FSMonitor.MERGE_EVENTS = {}
    FSMonitor.MERGE_EVENTS[FSMonitor.CREATED] = {}
    FSMonitor.MERGE_EVENTS[FSMonitor.CREATED][FSMonitor.CREATED]   = FSMonitor.CREATED  #!
    FSMonitor.MERGE_EVENTS[FSMonitor.CREATED][FSMonitor.MODIFIED]  = FSMonitor.CREATED
    FSMonitor.MERGE_EVENTS[FSMonitor.CREATED][FSMonitor.DELETED]   = None
    FSMonitor.MERGE_EVENTS[FSMonitor.MODIFIED] = {}
    FSMonitor.MERGE_EVENTS[FSMonitor.MODIFIED][FSMonitor.CREATED]  = FSMonitor.MODIFIED #!
    FSMonitor.MERGE_EVENTS[FSMonitor.MODIFIED][FSMonitor.MODIFIED] = FSMonitor.MODIFIED
    FSMonitor.MERGE_EVENTS[FSMonitor.MODIFIED][FSMonitor.DELETED]  = FSMonitor.DELETED
    FSMonitor.MERGE_EVENTS[FSMonitor.DELETED] = {}
    FSMonitor.MERGE_EVENTS[FSMonitor.DELETED][FSMonitor.CREATED]   = FSMonitor.MODIFIED
    FSMonitor.MERGE_EVENTS[FSMonitor.DELETED][FSMonitor.MODIFIED]  = FSMonitor.MODIFIED #!
    FSMonitor.MERGE_EVENTS[FSMonitor.DELETED][FSMonitor.DELETED]   = FSMonitor.DELETED  #!

    class PersistentQueue(object):
        """Mock version of the real PersistentQueue class, to be able to reuse
        the same event merging code. This mock version only contains the
        essential code that's needed for this upgrade script.
        """
        def __init__(self, dbcon, dbcur):
            self.dbcon = dbcon
            self.dbcur = dbcur
            self.table = 'pipeline_queue'

        @classmethod
        def __hash_key(cls, key):
            if not isinstance(key, types.StringTypes):
                key = str(key)
            md5 = hashlib.md5(key.encode('utf-8')).hexdigest().decode('ascii')
            return md5

        def get_item_for_key(self, key):
            md5 = PersistentQueue.__hash_key(key)
            self.dbcur.execute("SELECT item FROM %s WHERE key = ?" % (self.table), (md5, ))
            result = self.dbcur.fetchone()
            if result is None:
                return None
            else:
                return result[0]

        def put(self, item, key=None):
            if key is None:
                key = item
            md5 = PersistentQueue.__hash_key(key)
            pickled_item = cPickle.dumps(item, cPickle.HIGHEST_PROTOCOL)
            self.dbcur.execute("INSERT INTO %s (item, key) VALUES(?, ?)" % (self.table), (sqlite3.Binary(pickled_item), md5))
            self.dbcon.commit()

        def remove_item_for_key(self, key):
            md5 = PersistentQueue.__hash_key(key)
            self.dbcur.execute("SELECT id FROM %s WHERE key = ?" % (self.table), (md5, ))
            result = self.dbcur.fetchone()
            if result is not None:
                id = result[0]
                self.dbcur.execute("DELETE FROM %s WHERE key = ?" % (self.table), (md5, ))
                self.dbcon.commit()

        def update(self, item, key):
            md5 = PersistentQueue.__hash_key(key)
            self.dbcur.execute("SELECT id FROM %s WHERE key = ?" % (self.table), (md5, ))
            result = self.dbcur.fetchone()
            if result is not None:
                id = result[0]
                pickled_item = cPickle.dumps(item, cPickle.HIGHEST_PROTOCOL)
                self.dbcur.execute("UPDATE %s SET item = ? WHERE key = ?" % (self.table), (sqlite3.Binary(pickled_item), md5))
                self.dbcon.commit()


    # Get all items from the original pipeline queue. Insert these into the
    # pipeline queue that follows the new schema, and merge their events.
    pq = PersistentQueue(dbcon, dbcur)
    dbcur.execute("SELECT id, item FROM %s ORDER BY id ASC " % ("pipeline_queue_original"))
    resultList = dbcur.fetchall()
    for id, original_item in resultList:
        (input_file, event) = original_item
        item = pq.get_item_for_key(key=input_file)
        # If the file does not yet exist in the pipeline queue, put() it.
        if item is None:
            pq.put(item=(input_file, event), key=input_file)
        # Otherwise, merge the events, to prevent unnecessary actions.
        # See https://github.com/wimleers/fileconveyor/issues/68.
        else:
            old_event = item[1]
            merged_event = FSMonitor.MERGE_EVENTS[old_event][event]
            if merged_event is not None:
                pq.update(item=(input_file, merged_event), key=input_file)
            # The events being merged cancel each other out, thus remove
            # the file from the pipeline queue.
            else:
                pq.remove_item_for_key(key=input_file)

    # Finally, remove empty pages in the SQLite database.
    dbcon.execute("DROP TABLE %s" % ("pipeline_queue_original"))
    dbcon.execute("VACUUM")
    dbcon.close()


if __name__ == '__main__':
    # TODO: only run the necessary upgrades!

    # By default, PERSISTENT_DATA_DB is used, which is defined in settings.py.
    # You're free to change this to some other path, of course.
    upgrade_persistent_data_to_v10(PERSISTENT_DATA_DB)

########NEW FILE########
__FILENAME__ = verify
import httplib
import urlparse
import sqlite3
import sys
from settings import *

num_files_checked = 0
num_files_invalid = 0

dbcon = sqlite3.connect(SYNCED_FILES_DB)
dbcon.text_factory = unicode # This is the default, but we set it explicitly, just to be sure.
dbcur = dbcon.cursor()
num_files = dbcur.execute("SELECT COUNT(*) FROM synced_files").fetchone()[0]
dbcur.execute("SELECT input_file, url, server FROM synced_files ORDER BY server")

for input_file, url, server in dbcur.fetchall():
    parsed = urlparse.urlparse(url)
    
    conn = httplib.HTTPConnection(parsed.netloc)
    conn.request("HEAD", parsed.path)
    response = conn.getresponse()
    
    if not (response.status == 200 and response.reason == 'OK'):
        print "Missing: %s, which should be available at %s (server: %s)" % (input_file, url, server)
        num_files_invalid += 1

    num_files_checked += 1

    sys.stdout.write("\r%3d%% (%d/%d)" % ((num_files_checked * 100.0 / num_files), num_files_checked, num_files))
    sys.stdout.flush()

print ""
print "Finished verifying synced files. Results:"
print " - Number of checked synced files: %d" % (num_files_checked)
print " - Number of invalid synced files: %d" % (num_files_invalid)

########NEW FILE########
