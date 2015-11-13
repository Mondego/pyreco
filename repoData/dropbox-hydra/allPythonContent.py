__FILENAME__ = cluster_cop
#! /usr/bin/env python

import pymongo
from pymongo.read_preferences import ReadPreference
import sys
import time
import utils

shard_clients = {}


def syntax():
    print >>sys.stderr, "syntax:  %s mongos_host[:port]" % sys.argv[0]
    print >>sys.stderr, "purpose: monitor cluster for changes that might affect copy_collection.py"


def get_cluster_state(mongos):
    """
    returns a dictionary that contains the subset of cluster state we care about
    """
    global shard_clients

    # this won't work well with a large (thousands?) number of shards
    shards_collection = client['config']['shards']
    shards = [shard for shard in shards_collection.find()]

    state = {}
    state['shard_names'] = [shard['_id'] for shard in shards]
    state['shard_names'].sort()

    members = {}
    oplog_positions = {}
    for shard in shards:
        # get statuses for all replica set members
        try:
            repl_set, host = shard['host'].split('/')
        except ValueError:
            print >>sys.stderr, "ERROR: can't get replica set status for %s" % shard['_id']
            sys.exit(1)

        # get cached connection, if one exists
        if repl_set in shard_clients:
            shard_client = shard_clients[repl_set]
        else:
            shard_client = pymongo.MongoClient(host, replicaSet=repl_set,
                                               read_preference=ReadPreference.PRIMARY,
                                               socketTimeoutMS=120000)
            shard_clients[repl_set] = shard_client

        rs_status = shard_client.admin.command('replSetGetStatus')
        for member in rs_status['members']:
            members[member['name']] = member['stateStr']

        # get last oplog positions
        last_oplog_entry = utils.get_last_oplog_entry(shard_client)
        oplog_positions[repl_set] = last_oplog_entry['ts']


    state['members'] = members
    state['oplog_positions'] = oplog_positions

    return state


if __name__ == '__main__':
    errors = 0

    # parse command-line parameters
    log = utils.get_logger('cluster_cop')
    if len(sys.argv) != 2:
        syntax()
        sys.exit(1)

    host_tokens = sys.argv[1].split(':')
    if len(host_tokens) == 2:
        host, port = host_tokens
        port = int(port)
    else:
        host = host_tokens[0]
        port = 27017

    # connect to mongo
    log.info("connecting to %s:%d", host, port)
    client = pymongo.MongoClient(host, port, max_pool_size=1)
    shards_collection = client['config']['shards']
    log.info("connected")

    # take initial snapshot of cluster state
    prev_state = get_cluster_state(client)
    while True:
        time.sleep(10)
        curr_state = get_cluster_state(client)

        # ensure balancer is off
        settings = client['config']['settings']
        balancer_setting = settings.find_one({'_id': 'balancer'})
        if not balancer_setting['stopped']:
            log.error("chunk balancer is ON; this can be catastrophic!")
            sys.exit(1)

        # ensure primaries stay primaries and secondaries stay secondaries
        if prev_state['members'] != curr_state['members']:
            errors += 1
            log.error("previous member state (%r) doesn't match current state(%r)",
                      prev_state, curr_state)

        # figure out most recent op
        latest_ts = None
        latest_repl_set = None
        for repl_set, op_ts in curr_state['oplog_positions'].iteritems():
            if (not latest_ts or latest_ts.time < op_ts.time or 
                (latest_ts.time == op_ts.time and latest_ts.inc < op_ts.inc)):
                latest_ts = op_ts
                latest_repl_set = repl_set

        secs_ago = int(time.time() - latest_ts.time)
        log.info("%d errors | last op was %d secs ago on %s", errors, secs_ago, latest_repl_set)

        prev_state = curr_state
########NEW FILE########
__FILENAME__ = compare_collections
#! /usr/bin/env python
import base64
from bson import Binary
import gevent
import gevent.monkey
import gevent.pool
import json
import multiprocessing
from multiprocessing import Process
import os.path
from oplog_applier import _op_id
import pymongo
import random
import time
import utils
from utils import squelch_keyboard_interrupt

log = utils.get_logger(__name__)

POOL_SIZE = 20
READ_SIZE = 100 # documents


class CompareStats(object):
    def __init__(self):
        self.total_docs = None
        self.compared = 0
        self.retries = 0
        self.mismatches = 0
        self.start_time = time.time()


    def log(self):
        pct = int(float(self.compared) / self.total_docs * 100.0)
        qps = int(float(self.compared) / (time.time() - self.start_time))
        log.info("%d%% | %d / %d compared | %s/sec | %d retries | %d mismatches" %
                 (pct, self.compared, self.total_docs, qps, self.retries, self.mismatches))


class MismatchLogger(object):
    _mismatches_file = None
    collection_name = None

    @classmethod
    def log_mismatch(cls, doc, _id):
        if not cls._mismatches_file:
            proc_name = multiprocessing.current_process().name
            proc_name = proc_name.replace(':', '_')
            if cls.collection_name:
                filename = '%s_mismatches.txt' % cls.collection_name
            else:
                filename = 'mismatches.txt' 
            cls._mismatches_file = open(filename, 'a', 0)
        entry = {'_id': base64.b64encode(_id)}
        cls._mismatches_file.write('%s\n' % json.dumps(entry))


    @classmethod
    def decode_mismatch_id(cls, _json):
        doc = json.loads(_json)
        return Binary(base64.b64decode(doc['_id']), 0)


def _stats_worker(stats):
    while True:
        stats.log()
        gevent.sleep(1)


def _retry_id_worker(_id, source_collection, dest_collection, retries, retry_delay, stats):
    """
    Compares the source and destination's versions of the document with the given _id.
    For each data inconsistency, we retry the fetches and compare a fixed number of times
    to check if the data is eventually consistent. We perform an exponential backoff between
    each retry.

    @param _id                 _id of document to compare
    @param source_collection   source for data
    @param dest_collection     copied data to verify
    @param retries             number of times to retry comparison
    @param retry_delay         how many seconds to wait between retries (used as a starting point)
    @param stats               instance of CompareStats
    """
    backoff_factor = random.uniform(1.2, 1.4)

    for i in xrange(retries):
        # back off aggressively on successive retries, to reduce chances of false mismatches
        gevent.sleep(retry_delay * backoff_factor**(i+1))
        stats.retries += 1

        source_doc = source_collection.find_one({'_id': _id})
        dest_doc = dest_collection.find_one({'_id': _id})

        # doc was deleted from both places -- great
        if source_doc is None and dest_doc is None:
            stats.compared += 1
            return

        # docs match! we're done
        if source_doc == dest_doc:
            stats.compared += 1
            return

    # we've exhausted our retries, bail...
    stats.compared += 1
    stats.mismatches += 1
    id_base64 = base64.b64encode(_id)
    log.error("MISMATCH: _id = %s", id_base64)
    MismatchLogger.log_mismatch(source_doc, _id)


def _compare_ids_worker(_ids, source_collection, dest_collection, stats, retry_pool):
    """
    compare a set of ids between source and destination, creating new greenlets if needed
    to handle retries

    @param source_collection   source for data
    @param dest_collection     copied data to verify
    @param retries             number of times to retry comparison
    @param retry_delay         how many seconds to wait between retries
    @param retry_pool          pool of greenlets with which we can retry comparisons of
                               mismatched documents
    """
    # read docs in
    source_docs = [doc for doc in source_collection.find({'_id': {'$in': _ids}})]
    source_docs_dict = {doc['_id']: doc for doc in source_docs}

    dest_docs = [doc for doc in dest_collection.find({'_id': {'$in': _ids}})]
    dest_docs_dict = {doc['_id']: doc for doc in dest_docs}

    # find mismatching docs
    for _id in _ids:
        source_doc = source_docs_dict.get(_id, None)
        dest_doc = dest_docs_dict.get(_id, None)

        # doc was deleted from both places -- ok
        if source_doc is None and dest_doc is None:
            stats.compared += 1
            continue

        # docs match! we're done
        if source_doc == dest_doc:
            stats.compared += 1
            continue

        # docs don't match, so spawn a separate greenlet to handle the retries for this
        # particular _id
        retry_pool.spawn(_retry_id_worker,
                         _id=_id,
                         source_collection=source_collection,
                         dest_collection=dest_collection,
                         retries=10,
                         retry_delay=1.0,
                         stats=stats)


def _get_all_ids(collection):
    """
    generator that yields every _id in the given collection
    """
    cursor = collection.find(fields=['_id'], timeout=False, snapshot=True)
    cursor.batch_size(5000)
    for doc in cursor:
        yield doc['_id']


def _get_ids_for_recent_ops(client, recent_ops):
    """
    generator that yields the _id's that were touched by recent ops
    """
    oplog = client['local']['oplog.rs']
    fields = ['o._id', 'o2._id', 'op']
    cursor = oplog.find(fields=fields)
    cursor.limit(recent_ops)
    cursor.sort("$natural", pymongo.DESCENDING)
    cursor.batch_size(100)
    for op in cursor:
        yield _op_id(op)


def _get_ids_in_file(filename):
    """
    generator that yields the number of lines in the file, then each document containing
    the _id to read
    """
    with open(filename, 'r') as ids_file:
        lines = ids_file.readlines()
    yield len(lines)
    for line in lines:
        yield MismatchLogger.decode_mismatch_doc(line)['_id']


@squelch_keyboard_interrupt
def compare_collections(source, dest, percent, error_bp, recent_ops, ids_file):
    """
    compares two collections, using retries to see if collections are eventually consistent

    @param source_collection   source for data
    @param dest_collection     copied data to verify
    @param percent             percentage of documents to verify
    @param ids_file            files containing querie
    """
    MismatchLogger.collection_name = source['collection']

    # setup client connections
    source_client = utils.mongo_connect(source['host'], source['port'],
                                        ensure_direct=True,
                                        max_pool_size=POOL_SIZE,
                                        slave_okay=True,
                                        document_class=dict)
    source_collection = source_client[source['db']][source['collection']]

    dest_client = utils.mongo_connect(dest['host'], dest['port'],
                                      ensure_direct=True,
                                      max_pool_size=POOL_SIZE,
                                      slave_okay=True,
                                      document_class=dict)

    dest_collection = dest_client[dest['db']][dest['collection']]

    # setup stats
    stats = CompareStats()
    compare_pool = gevent.pool.Pool(POOL_SIZE)
    retry_pool = gevent.pool.Pool(POOL_SIZE * 5)

    # get just _id's first, because long-running queries degrade significantly
    # over time; reading just _ids is fast enough (or small enough?) not to suffer
    # from this degradation
    if recent_ops:
        id_getter = _get_ids_for_recent_ops(source_client, recent_ops)
        stats.total_docs = recent_ops
        if source_client.is_mongos:
            log.error("cannot read oplogs through mongos; specify mongod instances instead")
            return
    elif ids_file:
        id_getter = _get_ids_in_file(ids_file)
        stats.total_docs = id_getter.next()
    else:
        id_getter = _get_all_ids(source_collection)
        stats.total_docs = source_collection.count()

    if percent is not None:
        stats.total_docs = int(float(stats.total_docs) * percent / 100.0)

    stats_greenlet = gevent.spawn(_stats_worker, stats)

    # read documents in batches, but perform retries individually in separate greenlets
    _ids = []
    for _id in id_getter:
        if percent is not None and not utils.id_in_subset(_id, percent):
            continue

        _ids.append(_id)
        if len(_ids) == READ_SIZE:
            _ids_to_compare = _ids
            _ids = []
            compare_pool.spawn(_compare_ids_worker,
                               _ids=_ids_to_compare,
                               source_collection=source_collection,
                               dest_collection=dest_collection,
                               stats=stats,
                               retry_pool=retry_pool)

    # compare final batch of _id's
    if _ids:
        compare_pool.spawn(_compare_ids_worker,
                           _ids=_ids,
                           source_collection=source_collection,
                           dest_collection=dest_collection,
                           stats=stats,
                           retry_pool=retry_pool)

    # wait for all greenlets to finish
    compare_pool.join()
    retry_pool.join()
    stats_greenlet.kill()
    stats.log()
    log.info("compare finished")


if __name__ == '__main__':
    # make GC perform reasonably
    utils.tune_gc()

    # setup async socket ops
    gevent.monkey.patch_socket()

    # parse command-line options 
    import argparse
    parser = argparse.ArgumentParser(description='Copies a collection from one mongod to another.')
    parser.add_argument(
        '--source', type=str, required=True, metavar='URL',
        help='source to read from; can be a file containing sources or a url like: host[:port]/db/collection; '
             'e.g. localhost:27017/test_database.source_collection')
    parser.add_argument(
        '--ids-file', type=str, default=None,
        help='read ids to compare from this file')
    parser.add_argument(
        '--dest', type=str, required=True, metavar='URL',
        help='source to read from; see --source for format of URL')
    parser.add_argument(
        '--percent', type=int, metavar='PCT', default=None,
        help='verify only PCT%% of data')
    parser.add_argument(
        '--error-bp', type=int, metavar='BP', default=None,
        help='intentionally introduce errors at a rate of BP basis points')
    parser.add_argument(
        '--recent-ops', type=int, metavar='COUNT', default=None,
        help='verify documents touched by the last N ops')

    args = parser.parse_args()

    dest = utils.parse_mongo_url(args.dest)
    if os.path.exists(args.source):
        sources = utils.parse_source_file(args.source)
    else:
        sources = [utils.parse_mongo_url(args.source)]

    if args.ids_file and args.recent_ops:
        raise ValueError("the --ids-file and --recent-ops parameters cannot be combined")

    # finally, compare stuff!
    processes = []
    for source in sources:
        name = "%s:%s" % (source['host'], source['port'])
        process = Process(target=compare_collections,
                          name=name,
                          kwargs=dict(
                            source=source,
                            dest=dest,
                            percent=args.percent,
                            error_bp=args.error_bp,
                            recent_ops=args.recent_ops,
                            ids_file=args.ids_file,
                          ))
        process.start()

    utils.wait_for_processes(processes)

########NEW FILE########
__FILENAME__ = copier
from copy_state_db import CopyStateDB
from faster_ordered_dict import FasterOrderedDict
import gevent
import gevent.monkey
from gevent.pool import Pool
from pymongo.errors import DuplicateKeyError
from pymongo.read_preferences import ReadPreference
import time
import utils
from utils import auto_retry, log_exceptions, squelch_keyboard_interrupt

log = utils.get_logger(__name__)

INSERT_SIZE = 250
INSERT_POOL_SIZE = 40

#
# Copy collection
#

class Stats(object):
    def __init__(self):
        self.start_time = self.adj_start_time = time.time()
        self.inserted = 0
        self.total_docs = None
        self.duplicates = 0 # not a true count of duplicates; just an exception count
        self.exceptions = 0
        self.retries = 0

    def log(self, adjusted=False):
        start_time = self.adj_start_time if adjusted else self.start_time
        qps = int(float(self.inserted) / (time.time() - start_time))
        pct = int(float(self.inserted)/self.total_docs*100.0)
        log.info("%d%% | %d / %d copied | %d/sec | %d dupes | %d exceptions | %d retries" % 
                 (pct, self.inserted, self.total_docs, qps, self.duplicates,
                  self.exceptions, self.retries))


@auto_retry
def _find_and_insert_batch_worker(source_collection, dest_collection, ids, stats):
    """
    greenlet responsible for copying a set of documents
    """

    # read documents from source
    cursor = source_collection.find({'_id': {'$in': ids}})
    cursor.batch_size(len(ids))
    docs = [doc for doc in cursor]

    # perform copy as a single batch
    ids_inserted = []
    try:
        ids_inserted = dest_collection.insert(docs, continue_on_error=True)
    except DuplicateKeyError:
        # this isn't an exact count, but it's more work than it's worth to get an exact
        # count of duplicate _id's
        stats.duplicates += 1
    stats.inserted += len(ids_inserted)


def _copy_stats_worker(stats):
    """
    Periodically print stats relating to the initial copy.
    """
    while True:
        stats.log()
        gevent.sleep(1)


@log_exceptions
@squelch_keyboard_interrupt
def copy_collection(source, dest, state_path, percent):
    """
    Copies all documents from source to destination collection. Inserts documents in
    batches using insert workers, which are each run in their own greenlet. Ensures that
    the destination is empty before starting the copy.

    Does no safety checks -- this is up to the caller.

    @param source      dict of (host, port, db, collection) for the source
    @param dest        dict of (host, port, db, collection) for the destination
    @param state_path  path of state database
    @param percent     percentage of documents to copy
    """
    gevent.monkey.patch_socket()

    # open state database
    state_db = CopyStateDB(state_path)

    # connect to mongo
    source_client = utils.mongo_connect(source['host'], source['port'],
                                        ensure_direct=True,
                                        max_pool_size=30,
                                        read_preference=ReadPreference.SECONDARY,
                                        document_class=FasterOrderedDict)

    source_collection = source_client[source['db']][source['collection']]
    if source_client.is_mongos:
        raise Exception("for performance reasons, sources must be mongod instances; %s:%d is not",
                        source['host'], source['port'])

    dest_client = utils.mongo_connect(dest['host'], dest['port'],
                                      max_pool_size=30,
                                      document_class=FasterOrderedDict)
    dest_collection = dest_client[dest['db']][dest['collection']]

    # record timestamp of last oplog entry, so that we know where to start applying ops
    # later
    oplog_ts = utils.get_last_oplog_entry(source_client)['ts']
    state_db.update_oplog_ts(source, dest, oplog_ts)

    # for testing copying of indices quickly
    if percent == 0:
        log.info("skipping copy because of --percent 0 parameters")
        state_db.update_state(source, dest, CopyStateDB.STATE_WAITING_FOR_INDICES)
        return

    stats = Stats()
    stats.total_docs = int(source_collection.count())
    if percent:
        # hack-ish but good enough for a testing-only feature
        stats.total_docs = int(stats.total_docs * (float(percent)/100.0))

    # get all _ids, which works around a mongo bug/feature that causes massive slowdowns
    # of long-running, large reads over time
    ids = []
    cursor = source_collection.find(fields=["_id"], snapshot=True, timeout=False)
    cursor.batch_size(5000)
    insert_pool = Pool(INSERT_POOL_SIZE)
    stats_greenlet = gevent.spawn(_copy_stats_worker, stats)
    for doc in cursor:
        _id = doc['_id']

        if percent is not None and not utils.id_in_subset(_id, percent):
            continue

        # when we've gathered enough _ids, spawn a worker greenlet to batch copy the
        # documents corresponding to them
        ids.append(_id)
        if len(ids) % INSERT_SIZE == 0:
            outgoing_ids = ids
            ids = []
            insert_pool.spawn(_find_and_insert_batch_worker,
                              source_collection=source_collection,
                              dest_collection=dest_collection,
                              ids=outgoing_ids,
                              stats=stats)
        gevent.sleep()

    # insert last batch of documents
    if len(ids) > 0:        
        _find_and_insert_batch_worker(source_collection=source_collection,
                                      dest_collection=dest_collection,
                                      ids=ids,
                                      stats=stats)
        stats.log()

    # wait until all other outstanding inserts have finished
    insert_pool.join()
    stats_greenlet.kill()
    log.info("done with initial copy")

    state_db.update_state(source, dest, CopyStateDB.STATE_WAITING_FOR_INDICES)

    # yeah, we potentially leak connections here, but that shouldn't be a big deal


def copy_indexes(source, dest):
    """
    Copies all indexes from source to destination, preserving options such as unique
    and sparse.
    """
    # connect to mongo instances
    source_client = utils.mongo_connect(source['host'], source['port'],
                                        ensure_direct=True,
                                        max_pool_size=1,
                                        read_preference=ReadPreference.SECONDARY)
    source_collection = source_client[source['db']][source['collection']]

    dest_client = utils.mongo_connect(dest['host'], dest['port'], max_pool_size=1)
    dest_collection = dest_client[dest['db']][dest['collection']] 

    # copy indices
    for name, index in source_collection.index_information().items():
        kwargs = { 'name': name }
        index_key = None
        for k, v in index.items():
            if k in ['unique', 'sparse']:
                kwargs[k] = v
            elif k == 'v':
                continue
            elif k == 'key':
                # sometimes, pymongo will give us floating point numbers, so let's make sure
                # they're ints instead
                index_key = [(field, int(direction)) for (field, direction) in v]
            else:
                raise NotImplementedError("don't know how to handle index info key %s" % k)
            # TODO: there are other index options that probably aren't handled here

        assert index_key is not None
        log.info("ensuring index on %s (options = %s)", index_key, kwargs)
        dest_collection.ensure_index(index_key, **kwargs)
########NEW FILE########
__FILENAME__ = copy_collection
#! /usr/bin/env python


# dependencies to handle:
# - gevent
# - pymongo
# - apt: python-dev
# - apt: libevent-dev

import copier
from copy_state_db import CopyStateDB
import multiprocessing
import oplog_applier
import os
import os.path
from pymongo.read_preferences import ReadPreference
import string
import sys
import utils

log = utils.get_logger(__name__)

PARENT_PROCESS_NAME = 'parent process'

#
# child processes
#

def die(msg):
    log.error(msg)
    sys.exit(1)


def ensure_empty_dest(dest):
    client = utils.mongo_connect(dest['host'], dest['port'],
                                 ensure_direct=True,
                                 max_pool_size=1,
                                 read_preference=ReadPreference.PRIMARY)
    collection = client[dest['db']][dest['collection']]
    if collection.count() > 0:
        die("destination must be empty!")


def copy_collection_parent(sources, dest, state_db, args):
    """
    drive the collection copying process by delegating work to a pool of worker processes
    """

    # ensure state db has rows for each source/dest pair
    for source in sources:
        state_db.add_source_and_dest(source, dest)

    # space-pad all process names so that tabular output formats line up
    process_names = {repr(source): "%s:%d" % (source['host'], source['port'])
                     for source in sources}
    process_names['parent'] = PARENT_PROCESS_NAME
    max_process_name_len = max(len(name) for name in process_names.itervalues())
    for key in process_names:
        process_names[key] = string.ljust(process_names[key], max_process_name_len)

    multiprocessing.current_process().name = process_names['parent']

    # -----------------------------------------------------------------------
    # perform initial copy, if it hasn't been done yet
    # -----------------------------------------------------------------------
    in_initial_copy = len(state_db.select_by_state(CopyStateDB.STATE_INITIAL_COPY))
    if in_initial_copy and in_initial_copy < len(sources):
        die("prior attempt at initial copy failed; rerun with --restart")
    if in_initial_copy > 0:
        ensure_empty_dest(dest)

        # each worker process copies one shard
        processes = []
        for source in sources:
            name = process_names[repr(source)]
            process = multiprocessing.Process(target=copier.copy_collection,
                                              name=name,
                                              kwargs=dict(source=source,
                                                          dest=dest,
                                                          state_path=state_db._path,
                                                          percent=args.percent))
            process.start()
            processes.append(process)


        # wait for all workers to finish
        utils.wait_for_processes(processes)

    # -----------------------------------------------------------------------
    # build indices on main process, since that only needs to be done once
    # -----------------------------------------------------------------------
    waiting_for_indices = len(state_db.select_by_state(CopyStateDB.STATE_WAITING_FOR_INDICES))
    if waiting_for_indices and waiting_for_indices < len(sources):
        die("not all initial copies have been completed; rerun with --restart")
    if waiting_for_indices > 0:
        log.info("building indices")
        copier.copy_indexes(sources[0], dest)
        for source in sources:
            state_db.update_state(source, dest, CopyStateDB.STATE_APPLYING_OPLOG)

    # -----------------------------------------------------------------------
    # apply oplogs
    # -----------------------------------------------------------------------
    applying_oplog = state_db.select_by_state(CopyStateDB.STATE_APPLYING_OPLOG)
    if len(applying_oplog) < len(sources):
        die("this shouldn't happen!")

    log.info("starting oplog apply")

    # create worker thread that prints headers for oplog stats on a regular basis;
    # we do this to prevent the visual clutter caused by multiple processes doing this
    #
    # we avoid using gevent in the parent process to avoid weirdness I've seen with fork()ed
    # gevent loops
    header_delay = max(float(20) / len(sources),10) 
    stats_name = string.ljust("stats", max_process_name_len)
    stats_proc = multiprocessing.Process(target=oplog_applier.print_header_worker,
                                         args=(header_delay,),
                                         name=stats_name)
    stats_proc.start()

    # need to isolate calls to gevent here, to avoid forking with monkey-patched modules
    # (which seems to create funkiness)
    processes = []
    for source in sources:
        name = process_names[repr(source)]
        process = multiprocessing.Process(target=oplog_applier.apply_oplog,
                                          name=name,
                                          kwargs=dict(source=source,
                                                      dest=dest,
                                                      percent=args.percent,
                                                      state_path=state_db._path))
        process.start()
        processes.append(process)

    # this should *never* finish
    processes.append(stats_proc)
    utils.wait_for_processes(processes)


if __name__ == '__main__':
    # NOTE: we are not gevent monkey-patched here; only child processes are monkey-patched,
    #       so all ops below are synchronous

    # parse command-line options
    import argparse
    parser = argparse.ArgumentParser(description='Copies a collection from one mongod to another.')
    parser.add_argument(
        '--source', type=str, required=True, metavar='URL',
        help='source to read from; can be a file containing sources or a url like: host[:port]/db/collection; '
             'e.g. localhost:27017/prod_maestro.emails')
    parser.add_argument(
        '--dest', type=str, required=True, metavar='URL',
        help='source to read from; see --source for format')
    parser.add_argument(
        '--percent', type=int, metavar='PCT', default=None,
        help='copy only PCT%% of data')
    parser.add_argument(
        '--restart', action='store_true',
        help='restart from the beginning, ignoring any prior progress')
    parser.add_argument(
        '--state-db', type=str, metavar='PATH', default=None,
        help='path to state file (defaults to ./<source_database>.<source_collection>.db)')
    args = parser.parse_args()

    # parse source and destination
    dest = utils.parse_mongo_url(args.dest)
    if os.path.exists(args.source):
        sources = utils.parse_source_file(args.source)
    else:
        sources = [utils.parse_mongo_url(args.source)]

    # initialize sqlite database that holds our state (this may seem like overkill,
    # but it's actually needed to ensure proper synchronization of subprocesses)
    if not args.state_db:
        args.state_db = '%s.%s.db' % (sources[0]['db'], sources[0]['collection'])

    if args.state_db.startswith('/'):
        state_db_path = args.state_db
    else:
        state_db_path = os.path.join(os.path.dirname(os.path.realpath(__file__)),
                                                     args.state_db)

    log.info('using state db %s' % state_db_path)
    state_db_exists = os.path.exists(state_db_path)
    state_db = CopyStateDB(state_db_path)
    if not state_db_exists:
        state_db.drop_and_create()

    if args.restart:
        state_db.drop_and_create()

    # do the real work
    copy_collection_parent(sources, dest, state_db, args)

    log.error("shouldn't reach this point")
    sys.exit(1)

########NEW FILE########
__FILENAME__ = copy_state_db
from bson import Timestamp
import itertools
import json
import sqlite3
import time

CREATE_STATE_SQL = (
"""
CREATE TABLE {table_name}
(
    source TEXT NOT NULL,
    dest TEXT NOT NULL,
    updated_at REAL NOT NULL,
    state TEXT NOT NULL,
    oplog_ts TEXT DEFAULT NULL,
    PRIMARY KEY(source, dest)
)
""")


def _mongo_dict_to_str(d):
    if 'id_source' in d:
        return d['id_source']['shard_name']

    return "%s:%d/%s/%s" % (d['host'], d['port'], d['db'], d['collection'])


def _results_as_dicts(cursor):
    """
    given a sqlite cursor, yields results as a dictionary mapping column names to
    column values

    probably slightly overengineered
    """
    results = []
    col_names = [d[0] for d in cursor.description]
    while True:
        rows = cursor.fetchmany()
        if not rows:
            break
        for row in rows:
            results.append(dict(itertools.izip(col_names, row)))
    return results


class CopyStateDB(object):
    """
    contains state of a collection copy in a sqlite3 database, for ease of
    use in other code

    a separate state file should be used for each sharded collection being copied,
    to avoid deleting state should copy_collection.py be run with --restart; if that's
    not a concern, share away!
    """

    STATE_TABLE = 'state'

    STATE_INITIAL_COPY = 'initial copy'
    STATE_WAITING_FOR_INDICES = 'waiting for indices'
    STATE_APPLYING_OPLOG = 'applying oplog'

    def __init__(self, path):
        self._conn = sqlite3.connect(path)
        self._path = path


    def drop_and_create(self):
        with self._conn:
            cursor = self._conn.cursor()
            cursor.execute("DROP TABLE IF EXISTS %s" % self.STATE_TABLE)
            cursor.execute(CREATE_STATE_SQL.format(table_name=self.STATE_TABLE))


    def add_source_and_dest(self, source, dest):
        """
        adds a state entry for the given source and destination, not complaining
        if it already exists

        assumes source and dest are dict's with these fields: host, port, db, collection
        """
        source_str = _mongo_dict_to_str(source)
        dest_str = _mongo_dict_to_str(dest)
        with self._conn:
            cursor = self._conn.cursor()
            query  = "INSERT OR IGNORE INTO "+self.STATE_TABLE+" "
            query += "(source, dest, updated_at, state, oplog_ts) VALUES (?, ?, ?, ?, ?) "
            cursor.execute(query,
                           (source_str, dest_str, time.time(), self.STATE_INITIAL_COPY, None))


    def select_by_state(self, state):
        cursor = self._conn.cursor()
        query = "SELECT * FROM "+self.STATE_TABLE+" WHERE state=?"
        cursor.execute(query, (state,))
        return _results_as_dicts(cursor)


    def update_oplog_ts(self, source, dest, oplog_ts):
        """
        updates where we are in applying oplog entries
        """
        assert isinstance(oplog_ts, Timestamp)
        source_str = _mongo_dict_to_str(source)
        dest_str = _mongo_dict_to_str(dest)
        oplog_ts_json = json.dumps({'time': oplog_ts.time, 'inc': oplog_ts.inc})
        query  = "UPDATE "+self.STATE_TABLE+" "
        query += "SET oplog_ts = ? "
        query += "WHERE source = ? AND dest = ?"
        with self._conn:
            cursor = self._conn.cursor()
            cursor.execute(query, (oplog_ts_json, source_str, dest_str))


    def update_state(self, source, dest, state):
        source_str = _mongo_dict_to_str(source)
        dest_str = _mongo_dict_to_str(dest)
        query  = "UPDATE "+self.STATE_TABLE+" "
        query += "SET state = ? "
        query += "WHERE source = ? AND dest = ?"
        with self._conn:
            cursor = self._conn.cursor()
            cursor.execute(query, (state, source_str, dest_str))


    def get_oplog_ts(self, source, dest):
        source_str = _mongo_dict_to_str(source)
        dest_str = _mongo_dict_to_str(dest)
        query  = "SELECT oplog_ts "
        query += "FROM %s " % self.STATE_TABLE
        query += "WHERE source = ? AND dest = ?"
        with self._conn:
            cursor = self._conn.cursor()
            cursor.execute(query, (source_str, dest_str))
            result = json.loads(cursor.fetchone()[0])
            return Timestamp(time=result['time'], inc=result['inc'])
########NEW FILE########
__FILENAME__ = copy_stragglers
#! /usr/bin/env python
import argparse
from compare_collections import MismatchLogger
from faster_ordered_dict import FasterOrderedDict
import gevent
import gevent.monkey
from gevent.pool import Pool
from pymongo.read_preferences import ReadPreference
import time
import utils

log = utils.get_logger(__name__)

POOL_SIZE = 20

class Stats(object):
    def __init__(self):
        self.start_time = time.time()
        self.processed = 0
        self.not_found = 0
        self.total = None

    def log(self):
        log.info("%d / %d processed | %d not found", stats.processed, stats.total, stats.not_found)

def copy_document_worker(query_doc, source_collection, dest_collection, stats):
    """
    greenlet function that copies a document identified by the query document

    there is a *very* narrow race condition where the document might be deleted from the source
    between our find() and save(); that seems an acceptable risk
    """
    docs = [doc for doc in source_collection.find(query_doc)]
    assert len(docs) <= 1
    if len(docs) == 0:
        # if the document has been deleted from the source, we assume that the oplog applier
        # will delete from the destination in the future
        stats.not_found += 1
        stats.processed += 1
    else:
        # we have the document, so copy it
        dest_collection.save(docs[0])
        stats.processed +=1


def stats_worker(stats):
    """
    prints stats periodically
    """
    while True:
        gevent.sleep(3)
        stats.log()


if __name__ == '__main__':
    utils.tune_gc()
    gevent.monkey.patch_socket()

    parser = argparse.ArgumentParser(description='Through stdin, reads JSON documents containing _ids and shark keys for mismatching documents and re-copies those documents.')
    parser.add_argument(
        '--source', type=str, required=True, metavar='URL',
        help='source to read from; e.g. localhost:27017/prod_maestro.emails')
    parser.add_argument(
        '--dest', type=str, required=True, metavar='URL',
        help='destination to copy to; e.g. localhost:27017/destination_db.emails')
    parser.add_argument(
        '--mismatches-file', type=str, default=None, required=True, metavar='FILENAME',
        help='read ids to copy from this file, which is generated by compare_collections.py')
    args = parser.parse_args()

    # connect to source and destination
    source = utils.parse_mongo_url(args.source)
    source_client = utils.mongo_connect(source['host'], source['port'],
                                        ensure_direct=True,
                                        max_pool_size=POOL_SIZE,
                                        read_preference=ReadPreference.SECONDARY_PREFERRED,
                                        document_class=FasterOrderedDict)
    source_collection = source_client[source['db']][source['collection']]
    if not source_client.is_mongos or source_client.is_primary:
        raise Exception("source must be a mongos instance or a primary")


    dest = utils.parse_mongo_url(args.dest)
    dest_client = utils.mongo_connect(dest['host'], dest['port'],
                                      max_pool_size=POOL_SIZE,
                                      document_class=FasterOrderedDict)
    dest_collection = dest_client[dest['db']][dest['collection']]

    if source == dest:
        raise ValueError("source and destination cannot be the same!")

    # periodically print stats
    stats = Stats()
    stats_greenlet = gevent.spawn(stats_worker, stats)

    # copy documents!
    pool = Pool(POOL_SIZE)
    with open(args.mismatches_file) as mismatches_file:
        lines = mismatches_file.readlines()  # copy everything into memory -- hopefully that isn't huge
    stats.total = len(lines)
    for line in lines:
        query_doc = {'_id': MismatchLogger.decode_mismatch_id(line)}
        pool.spawn(copy_document_worker,
                   query_doc=query_doc,
                   source_collection=source_collection,
                   dest_collection=dest_collection,
                   stats=stats)

    # wait for everythng to finish
    gevent.sleep()
    pool.join()
    stats_greenlet.kill()
    stats.log()
    log.info('done')

########NEW FILE########
__FILENAME__ = faster_ordered_dict
from collections import deque

class FasterOrderedDict(dict):
    """
    Faster than using the standard library class collections.OrderedDict,
    because OrderedDict is pure Python. This class delegates every
    operation to dict/deque, which are both C-based.

    This handles only the operations that matter to the rest of Hydra and probably
    won't work for other use cases without modification.
    """
    def __init__(self):
        dict.__init__(self)
        self._elems = deque()

    def __delitem__(self, key):
        """
        slow but should be uncommon for our uses
        """
        dict.__delitem__(self, key)
        self._elems.remove(key)

    def __setitem__(self, key, data):
        if key in self:
            dict.__setitem__(self, key, data)
        else:
            self._elems.append(key)
            dict.__setitem__(self, key, data)

    def __repr__(self):
        elems = ', '.join(["'%s': %s" % (elem, self[elem])
                           for elem in self._elems])
        return '{%s}' % elems

    def __iter__(self):
        return iter(self._elems)

    def iteritems(self):
        for elem in self._elems:
            yield elem, self[elem]

    def iterkeys(self):
        return iter(self._elems)

    def itervalues(self):
        for elem in self._elems:
            yield self[elem]

    def keys(self):
        return list(self._elems)

    def values(self):
        return [self[elem] for elem in self._elems]

    def items(self):
        return [(elem, self[elem]) for elem in self._elems]
########NEW FILE########
__FILENAME__ = oplog_applier
import bson
from copy_state_db import CopyStateDB
import gevent
from faster_ordered_dict import FasterOrderedDict
from gevent.pool import Pool
import pymongo
from pymongo.errors import DuplicateKeyError
from pymongo.read_preferences import ReadPreference
import time
import utils
from utils import auto_retry, log_exceptions, squelch_keyboard_interrupt

log = utils.get_logger(__name__)

TS_REWIND = 30 # seconds
HEADER_INTERVAL = 15 # entries

#
# Apply oplogs
#

class ApplyStats(object):
    def __init__(self):
        self.ops_retrieved = 0
        self.inserts = 0
        self.insert_warnings = 0
        self.deletes = 0
        self.delete_warnings = 0
        self.updates = 0
        self.update_warnings = 0
        self.last_ts = bson.Timestamp(int(time.time()), 0)
        self.sleeps = 0
        self.exceptions = 0
        self.retries = 0

        self.paused = False
        self.pending_ids = set()

    def log(self):
        # we record warnings but don't print them, because they haven't been that useful
        #
        # that said, we track them just in case 
        lag = int(time.time() - self.last_ts.time)
        log.info(FMT, self.ops_retrieved, lag, 
                 self.inserts, self.deletes, self.updates,
                 self.sleeps, self.exceptions, self.retries)

SH1 = "OPS APPLIED                                    | WARNINGS"
SH2 = "total     lag    inserts   removes   updates   | sleeps    exceptions retries"
FMT = "%-9d %-6d %-9d %-9d %-9d | %-9d %-10d %d"

def _op_id(op):
    if op['op'] == 'u':
        return op['o2']['_id']
    else:
        return op['o']['_id']

def print_header_worker(sleep_interval):
    while True:
        log.info(SH1)
        log.info(SH2)
        time.sleep(sleep_interval)


@log_exceptions
def oplog_stats_worker(stats):
    """
    Greenlet for printing state for oplog applies
    """
    while True:
        if not stats.paused:
            stats.log()
        gevent.sleep(3)


def oplog_checkpoint_worker(stats, source, dest, state_db):
    """
    Greenlet for persisting oplog position to disk. This only has to do work periodically,
    because it's ok if the recorded position is behind the position of the last applied 
    op. Oplog entries are idempotent, so we don't worry about applying an op twice.
    """
    while True:
        state_db.update_oplog_ts(source, dest, stats.last_ts)
        gevent.sleep(3)


@auto_retry
def _apply_op(op, source_collection, dest_collection, stats):
    """
    Actually applies an op. Assumes that we are the only one mutating a document with
    the _id referenced by the op.
    """
    _id = _op_id(op)
    if op['op'] == 'i':
        # insert
        try:
            inserted_id = dest_collection.insert(op['o'])
            if inserted_id:
                if inserted_id != _id:
                    raise SystemError("inserted _id doesn't match given _id") 
                stats.inserts += 1 
            else:
                stats.insert_warnings += 1
        except DuplicateKeyError:
            stats.insert_warnings += 1
    elif op['op'] == 'd':
        # delete
        result = dest_collection.remove({'_id': _id})
        if result:
            if result['n'] == 1:
                # success
                stats.deletes += 1
            else:
                # we're deleting by _id, so we should have deleted exactly one document;
                # anything else is a warning
                #log.debug("warn delete _id = %s; result = %r", base64.b64encode(_id), result)
                stats.delete_warnings += 1
                if result.get('err', None):
                    log.error("error while deleting: %r" % op['err'])
    elif op['op'] == 'u':
        # update. which involves re-reading the document from the source and updating the
        # destination with the updated contents
        doc = source_collection.find_one({'_id': _id}, slave_okay=True)
        if not doc:
            # document not found (might have been deleted in a subsequent oplog entry)
            stats.update_warnings += 1
            return
        stats.updates += 1
        dest_collection.save(doc)
    else:
        raise TypeError("unknown op type %s" % op['op'])


def _apply_op_worker(op, source_collection, dest_collection, stats):
    """
    Applies an op. Meant to be run as part of a greenlet.

    @param op                 op we're applying
    @param source_collection  collection we're reading from
    @param dest_collection    collection we're writing to
    @param stats              an ApplyStats object
    """
    _id = _op_id(op)

    # apply the op, ensuring that all ops on this _id execute serially
    try:
        _apply_op(op, source_collection, dest_collection, stats)
    finally:
        stats.pending_ids.remove(_id)


@log_exceptions
@squelch_keyboard_interrupt
def apply_oplog(source, dest, percent, state_path):
    """
    Applies oplog entries from source to destination. Since the oplog storage format
    has known and possibly unknown idiosyncracies, we take a conservative approach. For
    each insert or delete op, we can easily replay those. For updates, we do the following:

    1. Note the _id of the updated document
    2. Retrieved the updated document from the source
    3. Upsert the updated document in the destination

    @param oplog              oplog collection from the source mongod instance
    @param start_ts           timestamp at which we should start replaying oplog entries
    @param source_collection  collection we're reading from
    @param dest_collection    collection we're writing to
    @param checkpoint_ts_func function that, when called, persists oplog timestamp to disk
    @param 
    """
    gevent.monkey.patch_socket()

    stats = ApplyStats()
    apply_workers = Pool(20) 

    # connect to state db
    state_db = CopyStateDB(state_path)

    # connect to mongo
    source_client = utils.mongo_connect(source['host'], source['port'],
                                        ensure_direct=True,
                                        max_pool_size=30,
                                        read_preference=ReadPreference.SECONDARY,
                                        document_class=FasterOrderedDict)
    source_collection = source_client[source['db']][source['collection']]

    dest_client = utils.mongo_connect(dest['host'], dest['port'],
                                      max_pool_size=30,
                                      document_class=FasterOrderedDict)
    dest_collection = dest_client[dest['db']][dest['collection']] 
    oplog = source_client['local']['oplog.rs']

    # print stats periodically
    stats.paused = True
    stats_greenlet = gevent.spawn(oplog_stats_worker, stats)

    # checkpoint oplog position to disk periodically
    checkpoint_greenlet = gevent.spawn(oplog_checkpoint_worker, stats, source, dest, state_db)

    # figure out where we need to start reading oplog entries; rewind our oplog timestamp
    # a bit, to avoid issues with the user pressing Control-C while some ops are pending
    #
    # this works, because oplog entries are idempotent
    start_ts_orig = state_db.get_oplog_ts(source, dest)
    start_ts = bson.Timestamp(time=start_ts_orig.time-TS_REWIND, inc=0)
    log.info("starting apply at %s", start_ts)

    # perform tailing oplog query using the oplog_replay option to efficiently find
    # our starting position in the oplog
    query = {}
    query['ts'] = {'$gte': start_ts}
    query['ns'] = source_collection.full_name 
    cursor = oplog.find(query, timeout=False, tailable=True, slave_okay=True, await_data=True)
    cursor.add_option(pymongo.cursor._QUERY_OPTIONS['oplog_replay'])
    while True:
        for op in cursor:
            stats.paused = False

            _id = _op_id(op)
            if percent and not utils.id_in_subset(_id, percent):
                continue

            stats.ops_retrieved += 1

            # block *all* further ops from being applied if there's a pending
            # op on the current _id, to ensure serialization
            while _id in stats.pending_ids:
                gevent.sleep(0.1)
                stats.sleeps += 1

            # do the real oplog work in a greenlet from the pool
            stats.pending_ids.add(_id)
            apply_workers.spawn(_apply_op_worker,
                                op,
                                source_collection,
                                dest_collection,
                                stats)

            # update our last timestamp; this is *not* guaranteed to be the timestamp of the
            # most recent op, which is impossible because of our out-of-order execution
            #
            # this is an approximation that needs to be accurate to within TS_REWIND seconds
            stats.last_ts = op['ts']

        # while we have a tailable cursor, it can stop iteration if no more results come back
        # in a reasonable time, so sleep for a bit then try to continue iteration
        if cursor.alive:
            log.debug("replayed all oplog entries; sleeping...")
            stats.paused = True
            gevent.sleep(2)
            stats.paused = False
        else:
            log.error("cursor died on us!")
            break

    # just to silence pyflakes...
    stats_greenlet.kill()
    checkpoint_greenlet.kill()
########NEW FILE########
__FILENAME__ = utils
import functools
import gc
import gevent
import logging
import pymongo
from pymongo.errors import AutoReconnect, ConnectionFailure, OperationFailure, TimeoutError
import signal
import sys

loggers = {}
def get_logger(name):
    """
    get a logger object with reasonable defaults for formatting

    @param name used to identify the logger (though not currently useful for anything)
    """
    global loggers
    if name in loggers:
        return loggers[name]

    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)
    sh = logging.StreamHandler()
    sh.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s:%(processName)s] %(message)s",
                                      "%m-%d %H:%M:%S"))
    logger.addHandler(sh)

    loggers[name] = logger
    return logger

log = get_logger("utils")


def mongo_connect(host, port, ensure_direct=False, secondary_only=False, max_pool_size=1,
                  socketTimeoutMS=None, w=0, read_preference=None, document_class=dict,
                  replicaSet=None, slave_okay=None):
    """
    Same as MongoClient.connect, except that we are paranoid and ensure that cursors
    # point to what we intended to point them to. Also sets reasonable defaults for our
    needs.

    @param host            host to connect to
    @param port            port to connect to
    @param ensure_direct   do safety checks to ensure we are connected to specified mongo instance

    most other keyword arguments mirror those for pymongo.MongoClient
    """
    options = dict(
        host=host,
        port=port,
        socketTimeoutMS=socketTimeoutMS,
        use_greenlets=True,
        max_pool_size=max_pool_size,
        w=1,
        document_class=document_class)
    if replicaSet is not None:
        options['replicaSet'] = replicaSet
    if read_preference is not None:
        options['read_preference'] = read_preference
    if slave_okay is not None:
        options['slave_okay'] = slave_okay
    client = pymongo.MongoClient(**options)

    if ensure_direct:
        # make sure we are connected to mongod/mongos that was specified; mongodb drivers
        # have the tendency of doing "magical" things in terms of connecting to other boxes
        test_collection = client['local']['test']
        test_cursor = test_collection.find(slave_okay=True, limit=1)
        connection = test_cursor.collection.database.connection
        if connection.host != host or connection.port != port:
            raise ValueError("connected to %s:%d (expected %s:%d)" %
                             (connection.host, connection.port, host, port))

    return client


def parse_mongo_url(url):
    """
    Takes in pseudo-URL of form

    host[:port]/db/collection (e.g. localhost/prod_maestro/emails)

    and returns a dictionary containing elements 'host', 'port', 'db', 'collection'
    """
    try:
        host, db, collection = url.split('/')
    except ValueError:
        raise ValueError("urls be of format: host[:port]/db/collection")

    host_tokens = host.split(':')
    if len(host_tokens) == 2:
        host = host_tokens[0]
        port = int(host_tokens[1])
    elif len(host_tokens) == 1:
        port = 27017
    elif len(host_tokens) > 2:
        raise ValueError("urls be of format: host[:port]/db/collection")

    return dict(host=host, port=port, db=db, collection=collection)


def _source_file_syntax():
    print "--source files must be of the following format:"
    print "database_name.collection_name"
    print "mongo-shard-1.foo.com"
    print "mongo-shard-2.foo.com:27019"
    print "..."
    sys.exit(1)


def parse_source_file(filename):
    """
    parses an input file passed to the --source parameter as a list of dicts that contain
    these fields:

    host
    port
    db: database name
    collection
    """
    sources = []

    with open(filename, "r") as source_file:
        fullname = source_file.readline().strip()
        try:
            db, collection = fullname.split('.')
        except ValueError:
            _source_file_syntax()

        for source in [line.strip() for line in source_file]:
            tokens = source.split(':')
            if len(tokens) == 1:
                host = tokens[0]
                port = 27017
            elif len(tokens) == 2:
                host, port = tokens
                port = int(port)
            else:
                raise ValueError("%s is not a valid source", source)

            sources.append(dict(host=host, port=port, db=db, collection=collection))

    return sources


def get_last_oplog_entry(client):
    """
    gets most recent oplog entry from the given pymongo.MongoClient
    """
    oplog = client['local']['oplog.rs']
    cursor = oplog.find().sort('$natural', pymongo.DESCENDING).limit(1)
    docs = [doc for doc in cursor]
    if not docs:
        raise ValueError("oplog has no entries!")
    return docs[0]


def tune_gc():
    """
    normally, GC is too aggressive; use kmod's suggestion for tuning it
    """
    gc.set_threshold(25000, 25, 10)


def id_in_subset(_id, pct):
    """
    Returns True if _id fits in our definition of a "subset" of documents.
    Used for testing only.
    """
    return (hash(_id) % 100) < pct


def trim(s, prefixes, suffixes):
    """
    naive function that trims off prefixes and suffixes
    """
    for prefix in prefixes:
        if s.startswith(prefix):
            s = s[len(prefix):]

    for suffix in suffixes:
        if s.endswith(suffix):
            s = s[:-len(suffix)]

    return s


def log_exceptions(func):
    """
    logs exceptions using logger, which includes host:port info
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        if 'stats' in kwargs:
            # stats could be a keyword arg
            stats = kwargs['stats']
        elif len(args) > 0:
            # or the last positional arg
            stats = args[-1]
            if not hasattr(stats, 'exceptions'):
                stats = None
        else:
            # or not...
            stats = None

        try:
            return func(*args, **kwargs)
        except SystemExit:
            # just exit, don't log / catch when we're trying to exit()
            raise
        except:
            log.exception("uncaught exception")
            # increment exception counter if one is available to us
            if stats:
                stats.exceptions += 1
    return wrapper


def squelch_keyboard_interrupt(func):
    """
    suppresses KeyboardInterrupts, to avoid stack trace explosion when pressing Control-C
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except KeyboardInterrupt:
            sys.exit(1)
    return wrapper


def wait_for_processes(processes):
    try:
        [process.join() for process in processes]
    except KeyboardInterrupt:
        # prevent a frustrated user from interrupting our cleanup
        signal.signal(signal.SIGINT, signal.SIG_IGN)

        # if a user presses Control-C, we still need to terminate child processes and join()
        # them, to avoid zombie processes
        for process in processes:
            process.terminate()
            process.join()
        log.error("exiting...")
        sys.exit(1)


def auto_retry(func):
    """
    decorator that automatically retries a MongoDB operation if we get an AutoReconnect
    exception

    do not combine with @log_exceptions!!
    """
    MAX_RETRIES = 20  # yes, this is sometimes needed
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        # try to keep track of # of retries we've had to do
        if 'stats' in kwargs:
            # stats could be a keyword arg
            stats = kwargs['stats']
        elif len(args) > 0:
            # or the last positional arg
            stats = args[-1]
            if not hasattr(stats, 'retries'):
                stats = None
                log.warning("couldn't find stats")
        else:
            # or not...
            stats = None
            log.warning("couldn't find stats")

        failures = 0
        while True:
            try:
                return func(*args, **kwargs)
            except (AutoReconnect, ConnectionFailure, OperationFailure, TimeoutError):
                failures += 1
                if stats:
                    stats.retries += 1
                if failures >= MAX_RETRIES:
                    log.exception("FAILED after %d retries", MAX_RETRIES)
                    if stats:
                        stats.exceptions += 1
                    raise
                gevent.sleep(2 * failures)
                log.exception("retry %d after exception", failures)
    return wrapper
########NEW FILE########
