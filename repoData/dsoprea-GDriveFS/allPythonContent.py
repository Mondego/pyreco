__FILENAME__ = test_harness
#!/usr/bin/env python2.7

import sys
sys.path.insert(0, '..')

from pprint import pprint

from gdrivefs.conf import Conf
Conf.set('auth_cache_filepath', '/var/cache/creds/gdfs')

from gdrivefs.gdfs.gdfuse import set_auth_cache_filepath
from gdrivefs.gdtool.drive import GdriveAuth

auth = GdriveAuth()
client = auth.get_client()


#from logging.handlers import StreamHandler
#
#logger = logging.getLogger()
#logger.setLevel(DEBUG)
#
#log_syslog = logging.StreamHandler()
#logger.addHandler(log_syslog)


#client.files()
#sys.exit()

#response = client.about().get().execute()
#sys.exit()

#request = client.files().media_get()
#response = client.files().list().execute()
#response = client.files().get(fileId='1xxGrmEAv4-2ZM1MYj4UXpnxUp73d2VmtI9TdFERrSbM').execute()

#pprint(response.keys())

#for entry in response['items']:
#    pprint(dir(entry))
#    sys.exit()

#pprint(dir(response))

from gdrivefs.gdtool.download_agent import get_download_agent_external,\
                                           DownloadRequest
from gdrivefs import TypedEntry
from gdrivefs.time_support import get_normal_dt_from_rfc3339_phrase

from time import sleep
from datetime import datetime
from dateutil.tz import tzutc

dae = get_download_agent_external()

dae.start()

te = TypedEntry(entry_id='0B5Ft2OXeDBqSRGxHajVMT0pob1k', 
                mime_type='application/pdf')

url='https://doc-0c-1c-docs.googleusercontent.com/docs/securesc/svig2vvms8dc5kautokn617oteonvt69/vaj2tcji2mjes3snt7t8brteu3slfqhp/1394452800000/06779401675395806531/06779401675395806531/0B5Ft2OXeDBqSRGxHajVMT0pob1k?h=16653014193614665626&e=download&gd=true'
mtime_dt = get_normal_dt_from_rfc3339_phrase('2014-03-09T19:46:25.191Z')

dr = DownloadRequest(typed_entry=te, 
                     url=url, 
                     bytes=None, 
                     expected_mtime_dt=mtime_dt)

with dae.sync_to_local(dr) as f:
    print("Yielded: %s" % (f))

try:
    while 1:
        sleep(1)
except KeyboardInterrupt:
    print("Test loop has ended.")

dae.stop()


########NEW FILE########
__FILENAME__ = cacheclient_base
import logging

from gdrivefs.cache.cache_agent import CacheAgent

class CacheClientBase(object):
    """Meant to be inherited by a class. Is used to configure a particular 
    namespace within the cache.
    """

    __log = None

    @property
    def cache(self):
        try:
            return self._cache
        except:
            pass

        self._cache = CacheAgent(self.child_type, self.max_age, 
                                 fault_handler=self.fault_handler, 
                                 cleanup_pretrigger=self.cleanup_pretrigger)

        return self._cache

    def __init__(self):
        self.__log = logging.getLogger().getChild('CacheClientBase')
        child_type = self.__class__.__bases__[0].__name__
        max_age = self.get_max_cache_age_seconds()
        
        self.__log.debug("CacheClientBase(%s,%s)" % (child_type, max_age))

        self.child_type = child_type
        self.max_age = max_age

        self.init()

    def fault_handler(self, resource_name, key):
        pass

    def cleanup_pretrigger(self, resource_name, key, force):
        pass

    def init(self):
        pass

    def get_max_cache_age_seconds(self):
        raise NotImplementedError("get_max_cache_age() must be implemented in "
                                  "the CacheClientBase child.")

    @classmethod
    def get_instance(cls):
        """A helper method to dispense a singleton of whomever is inheriting "
        from us.
        """

        class_name = cls.__name__

        try:
            CacheClientBase.__instances
        except:
            CacheClientBase.__instances = { }

        try:
            return CacheClientBase.__instances[class_name]
        except:
            CacheClientBase.__instances[class_name] = cls()
            return CacheClientBase.__instances[class_name]



########NEW FILE########
__FILENAME__ = cache_agent
import logging

from datetime import datetime

from collections import OrderedDict
from threading import Timer
from gdrivefs.timer import Timers
from gdrivefs.conf import Conf

from gdrivefs.cache.cache_registry import CacheRegistry, CacheFault
from gdrivefs.report import Report

class CacheAgent(object):
    """A particular namespace within the cache."""

    __log = None

    registry        = None
    resource_name   = None
    max_age         = None

    fault_handler       = None
    cleanup_pretrigger  = None

    report              = None
    report_source_name  = None

    def __init__(self, resource_name, max_age, fault_handler=None, 
                 cleanup_pretrigger=None):
        self.__log = logging.getLogger().getChild('CacheAgent')

        self.__log.debug("CacheAgent(%s,%s,%s,%s)" % (resource_name, max_age, 
                                                   type(fault_handler), 
                                                   cleanup_pretrigger))

        self.registry = CacheRegistry.get_instance(resource_name)
        self.resource_name = resource_name
        self.max_age = max_age

        self.fault_handler = fault_handler
        self.cleanup_pretrigger = cleanup_pretrigger

#        self.report = Report.get_instance()
#        self.report_source_name = ("cache-%s" % (self.resource_name))

        # Run a clean-up cycle to get it scheduled.
#        self.__cleanup_check()

# TODO(dustin): Currently disabled. The system doesn't rely on it, and it's 
#               just another thread that unnecessarily runs, and trips up our 
#               ability to test individual components in simple isolation. It
#               needs to be refactored.
#
#               We'd like to either refactor into a multiprocessing worker, or
#               just send to statsd (which would be kindof cool).
#        self.__post_status()

    def __del__(self):

#        if self.report.is_source(self.report_source_name):
#            self.report.remove_all_values(self.report_source_name)
        pass

    def __post_status(self):
        """Send the current status to our reporting tool."""

        try:
            num_values = self.registry.count(self.resource_name)
        except:
            self.__log.exception("Could not get count of values for resource "
                                 "with name [%s]." % (self.resource_name))
            raise

        try:
            self.report.set_values(self.report_source_name, 'count', 
                                   num_values)
        except:
            self.__log.exception("Cache could not post status for resource "
                                 "with name [%s]." % (self.resource_name))
            raise

        status_post_interval_s = Conf.get('cache_status_post_frequency_s')
        status_timer = Timer(status_post_interval_s, self.__post_status)

        Timers.get_instance().register_timer('status', status_timer)

    def __cleanup_check(self):
        """Scan the current cache and determine items old-enough to be 
        removed.
        """

        self.__log.debug("Doing clean-up for cache resource with name [%s]." % 
                      (self.resource_name))

        try:
            cache_dict = self.registry.list_raw(self.resource_name)
        except:
            self.__log.exception("Could not do clean-up check with resource-"
                                 "name [%s]." % (self.resource_name))
            raise

        total_keys = [ (key, value_tuple[1]) for key, value_tuple \
                            in cache_dict.iteritems() ]

        cleanup_keys = [ key for key, value_tuple \
                            in cache_dict.iteritems() \
                            if (datetime.now() - value_tuple[1]).seconds > \
                                    self.max_age ]

        self.__log.info("Found (%d) entries to clean-up from entry-cache." % 
                        (len(cleanup_keys)))

        if cleanup_keys:
            for key in cleanup_keys:
                self.__log.debug("Cache entry [%s] under resource-name [%s] "
                                 "will be cleaned-up." % (key, 
                                                          self.resource_name))

                if self.exists(key, no_fault_check=True) == False:
                    self.__log.debug("Entry with ID [%s] has already been "
                                     "cleaned-up." % (key))
                else:
                    try:
                        self.remove(key)
                    except:
                        self.__log.exception("Cache entry [%s] under resource-"
                                             "name [%s] could not be cleaned-"
                                             "up." % (key, self.resource_name))
                        raise

            self.__log.debug("Scheduled clean-up complete.")

        cleanup_interval_s = Conf.get('cache_cleanup_check_frequency_s')
        cleanup_timer = Timer(cleanup_interval_s, self.__cleanup_check)

        Timers.get_instance().register_timer('cleanup', cleanup_timer)

    def set(self, key, value):
        self.__log.debug("CacheAgent.set(%s,%s)" % (key, value))

        return self.registry.set(self.resource_name, key, value)

    def remove(self, key):
        self.__log.debug("CacheAgent.remove(%s)" % (key))

        return self.registry.remove(self.resource_name, 
                                    key, 
                                    cleanup_pretrigger=self.cleanup_pretrigger)

    def get(self, key, handle_fault = None):

        if handle_fault == None:
            handle_fault = True

        self.__log.debug("CacheAgent.get(%s)" % (key))

        try:
            result = self.registry.get(self.resource_name, 
                                       key, 
                                       max_age=self.max_age, 
                                       cleanup_pretrigger=self.cleanup_pretrigger)
        except CacheFault:
            self.__log.debug("There was a cache-miss while requesting item "
                             "with ID (key).")

            if self.fault_handler == None or not handle_fault:
                raise

            try:
                result = self.fault_handler(self.resource_name, key)
            except:
                self.__log.exception("There was an exception in the fault-"
                                     "handler, handling for key [%s].", key)
                raise

            if result == None:
                raise

        return result

    def exists(self, key, no_fault_check=False):
        self.__log.debug("CacheAgent.exists(%s)" % (key))

        return self.registry.exists(self.resource_name, key, 
                                    max_age=self.max_age,
                                    cleanup_pretrigger=self.cleanup_pretrigger,
                                    no_fault_check=no_fault_check)

    def __getitem__(self, key):
        return self.get(key)

    def __setitem__(self, key, value):
        return self.set(key, value)

    def __delitem__(self, key):
        return self.remove(key)


########NEW FILE########
__FILENAME__ = cache_registry
import logging

from threading import RLock
from datetime import datetime


class CacheFault(Exception):
    pass


class CacheRegistry(object):
    """The main cache container."""

    __rlock = RLock()
    __log = None

    def __init__(self):
        self.__log = logging.getLogger().getChild('CacheReg')
        self.__cache = { }

    @staticmethod
    def get_instance(resource_name):
    
        with CacheRegistry.__rlock:
            try:
                CacheRegistry.__instance;
            except:
                CacheRegistry.__instance = CacheRegistry()

            if resource_name not in CacheRegistry.__instance.__cache:
                CacheRegistry.__instance.__cache[resource_name] = { }

        return CacheRegistry.__instance

    def set(self, resource_name, key, value):

        self.__log.debug("CacheRegistry.set(%s,%s,%s)" % (resource_name, key, 
                                                          value))

        with CacheRegistry.__rlock:
            try:
                old_tuple = self.__cache[resource_name][key]
            except:
                old_tuple = None

            self.__cache[resource_name][key] = (value, datetime.now())

        return old_tuple

    def remove(self, resource_name, key, cleanup_pretrigger=None):

        self.__log.debug("CacheRegistry.remove(%s,%s,%s)" % 
                         (resource_name, key, type(cleanup_pretrigger)))

        with CacheRegistry.__rlock:
            try:
                old_tuple = self.__cache[resource_name][key]
            except:
                raise

            self.__cleanup_entry(resource_name, key, True, 
                                 cleanup_pretrigger=cleanup_pretrigger)

        return old_tuple[0]

    def get(self, resource_name, key, max_age, cleanup_pretrigger=None):
        
        trigger_given_phrase = ('None' 
                                if cleanup_pretrigger == None 
                                else '<given>')

        self.__log.debug("CacheRegistry.get(%s,%s,%s,%s)" % 
                         (resource_name, key, max_age, trigger_given_phrase))

        with CacheRegistry.__rlock:
            try:
                (value, timestamp) = self.__cache[resource_name][key]
            except:
                raise CacheFault("NonExist")

            if max_age != None and \
               (datetime.now() - timestamp).seconds > max_age:
                self.__cleanup_entry(resource_name, key, False, 
                                     cleanup_pretrigger=cleanup_pretrigger)
                raise CacheFault("Stale")

        return value

    def list_raw(self, resource_name):
        
        self.__log.debug("CacheRegistry.list(%s)" % (resource_name))

        with CacheRegistry.__rlock:
            try:
                return self.__cache[resource_name]
            except:
                self.__log.exception("Could not list raw-entries under cache "
                                  "labelled with resource-name [%s]." %
                                  (resource_name))
                raise

    def exists(self, resource_name, key, max_age, cleanup_pretrigger=None, 
               no_fault_check=False):

        self.__log.debug("CacheRegistry.exists(%s,%s,%s,%s)" % (resource_name, 
                      key, max_age, cleanup_pretrigger))
        
        with CacheRegistry.__rlock:
            try:
                (value, timestamp) = self.__cache[resource_name][key]
            except:
                return False

            if max_age != None and not no_fault_check and \
                    (datetime.now() - timestamp).seconds > max_age:
                self.__cleanup_entry(resource_name, key, False, 
                                     cleanup_pretrigger=cleanup_pretrigger)
                return False

        return True

    def count(self, resource_name):

        return len(self.__cache[resource_name])

    def __cleanup_entry(self, resource_name, key, force, 
                        cleanup_pretrigger=None):

        self.__log.debug("Doing clean-up for resource_name [%s] and key "
                         "[%s]." % (resource_name, key))

        if cleanup_pretrigger != None:
            self.__log.debug("Running pre-cleanup trigger for resource_name "
                             "[%s] and key [%s]." % (resource_name, key))

            try:
                cleanup_pretrigger(resource_name, key, force)
            except:
                self.__log.exception("Cleanup-trigger failed.")
                raise

        try:
            del self.__cache[resource_name][key]
        except:
            self.__log.exception("Could not clean-up entry with resource_name "
                              "[%s] and key [%s]." % (resource_name, key))
            raise


########NEW FILE########
__FILENAME__ = volume
import logging

from collections    import deque
from threading      import RLock
from datetime       import datetime

from gdrivefs.utility import utility
from gdrivefs.conf import Conf
from gdrivefs.gdtool.drive import drive_proxy
from gdrivefs.gdtool.account_info import AccountInfo
from gdrivefs.gdtool.normal_entry import NormalEntry
from gdrivefs.cache.cache_registry import CacheRegistry, CacheFault
from gdrivefs.cache.cacheclient_base import CacheClientBase
from gdrivefs.errors import GdNotFoundError

CLAUSE_ENTRY            = 0 # Normalized entry.
CLAUSE_PARENT           = 1 # List of parent clauses.
CLAUSE_CHILDREN         = 2 # List of 2-tuples describing children: (filename, clause)
CLAUSE_ID               = 3 # Entry ID.
CLAUSE_CHILDREN_LOADED  = 4 # All children loaded?

def path_resolver(path):
    path_relations = PathRelations.get_instance()

    parent_clause = path_relations.get_clause_from_path(path)
    if not parent_clause:
#        logging.debug("Path [%s] does not exist for split.", path)
        raise GdNotFoundError()

    return (parent_clause[CLAUSE_ENTRY], parent_clause)


class PathRelations(object):
    """Manages physical path representations of all of the entries in our "
    account.
    """

    rlock = RLock()
    __log = None

    entry_ll = { }
    path_cache = { }
    path_cache_byid = { }

    @staticmethod
    def get_instance():

        with PathRelations.rlock:
            try:
                return CacheRegistry.__instance;
            except:
                pass

            CacheRegistry.__instance = PathRelations()
            return CacheRegistry.__instance

    def __init__(self):
        self.__log = logging.getLogger().getChild('PathRelate')

    def remove_entry_recursive(self, entry_id, is_update=False):
        """Remove an entry, all children, and any newly orphaned parents."""

        self.__log.debug("Doing recursive removal of entry with ID [%s].", 
                         entry_id)

        to_remove = deque([ entry_id ])
        stat_placeholders = 0
        stat_folders = 0
        stat_files = 0
        removed = { }
        while 1:
            if not to_remove:
                break

            current_entry_id = to_remove.popleft()

#            self.__log.debug("RR: Entry with ID (%s) will be removed. (%d) "
#                             "remaining." % (current_entry_id, len(to_remove)))

            entry_clause = self.entry_ll[current_entry_id]

            # Any entry that still has children will be transformed into a 
            # placeholder, and not actually removed. Once the children are 
            # removed in this recursive process, we'll naturally clean-up the 
            # parent as a last step. Therefore, the number of placeholders will 
            # overlap with the number of folders (a placeholder must represent 
            # a folder. It is only there because the entry had children).

            if not entry_clause[0]:
                stat_placeholders += 1
            elif entry_clause[0].is_directory:
                stat_folders += 1
            else:
                stat_files += 1

            result = self.__remove_entry(current_entry_id, is_update)

            removed[current_entry_id] = True

            (current_orphan_ids, current_children_clauses) = result

#            self.__log.debug("RR: Entry removed. (%d) orphans and (%d) children "
#                             "were reported." % 
#                             (len(current_orphan_ids), 
#                              len(current_children_clauses)))

            children_ids_to_remove = [ children[3] for children 
                                                in current_children_clauses ]

            to_remove.extend(current_orphan_ids)
            to_remove.extend(children_ids_to_remove)

#        self.__log.debug("RR: Removal complete. (%d) PH, (%d) folders, (%d) "
#                         "files removed." % 
#                         (stat_placeholders, stat_folders, stat_files))

        return (removed.keys(), (stat_folders + stat_files))

    def __remove_entry(self, entry_id, is_update=False):
        """Remove an entry. Updates references from linked entries, but does 
        not remove any other entries. We return a tuple, where the first item 
        is a list of any parents that, themselves, no longer have parents or 
        children, and the second item is a list of children to this entry.
        """

        with PathRelations.rlock:
            # Ensure that the entry-ID is valid.

            entry_clause = self.entry_ll[entry_id]
            
            # Clip from path cache.

            if entry_id in self.path_cache_byid:
#                self.__log.debug("Entry found in path-cache. Removing.")

                path = self.path_cache_byid[entry_id]
                del self.path_cache[path]
                del self.path_cache_byid[entry_id]

#            else:
#                self.__log.debug("Entry with ID [%s] did not need to be removed "
#                              "from the path cache." % (entry_id))

            # Clip us from the list of children on each of our parents.

            entry_parents = entry_clause[CLAUSE_PARENT]
            entry_children_tuples = entry_clause[CLAUSE_CHILDREN]

            parents_to_remove = [ ]
            children_to_remove = [ ]
            if entry_parents:
#                self.__log.debug("Entry to be removed has (%d) parents." % (len(entry_parents)))

                for parent_clause in entry_parents:
                    # A placeholder has an entry and parents field (fields 
                    # 0, 1) of None.

                    (parent, parent_parents, parent_children, parent_id, \
                        all_children_loaded) = parent_clause

                    if all_children_loaded and not is_update:
                        all_children_loaded = False

#                    self.__log.debug("Adjusting parent with ID [%s]." % 
#                                  (parent_id))

                    # Integrity-check that the parent we're referencing is 
                    # still in the list.
                    if parent_id not in self.entry_ll:
                        self.__log.warn("Parent with ID [%s] on entry with ID "
                                        "[%s] is not valid." % (parent_id, \
                                                                entry_id))
                        continue
            
                    old_children_filenames = [ child_tuple[0] for child_tuple 
                                                in parent_children ]

#                    self.__log.debug("Old children: %s" % 
#                                     (', '.join(old_children_filenames)))

                    updated_children = [ child_tuple for child_tuple 
                                         in parent_children 
                                         if child_tuple[1] != entry_clause ]

                    if parent_children != updated_children:
                        parent_children[:] = updated_children

                    else:
                        self.__log.error("Entry with ID [%s] referenced parent "
                                      "with ID [%s], but not vice-versa." % 
                                      (entry_id, parent_id))

                    updated_children_filenames = [ child_tuple[0] 
                                                    for child_tuple
                                                    in parent_children ]

#                    self.__log.debug("Up. children: %s" % 
#                                     (', '.join(updated_children_filenames)))

                    # If the parent now has no children and is a placeholder, 
                    # advise that we remove it.
                    if not parent_children and parent == None:
                        parents_to_remove.append(parent_id)

#            else:
#                self.__log.debug("Entry to be removed either has no parents, "
#                                 "or is a placeholder.")

            # Remove/neutralize entry, now that references have been removed.

            set_placeholder = len(entry_children_tuples) > 0

            if set_placeholder:
                # Just nullify the entry information, but leave the clause. We 
                # had children that still need a parent.

#                self.__log.debug("This entry has (%d) children. We will leave a "
#                                 "placeholder behind." % 
#                                 (len(entry_children_tuples)))

                entry_clause[0] = None
                entry_clause[1] = None
            else:
#                self.__log.debug("This entry does not have any children. It "
#                                 "will be completely removed.")

                del self.entry_ll[entry_id]

#        if parents_to_remove:
#            self.__log.debug("Parents that still need to be removed: %s" % 
#                             (', '.join(parents_to_remove)))

        children_entry_clauses = [ child_tuple[1] for child_tuple 
                                    in entry_children_tuples ]

#        self.__log.debug("Remove complete. (%d) entries were orphaned. There "
#                         "were (%d) children." % 
#                         (len(parents_to_remove), len(children_entry_clauses)))
        
        return (parents_to_remove, children_entry_clauses)

    def remove_entry_all(self, entry_id, is_update=False):
        """Remove the the entry from both caches. EntryCache is more of an 
        entity look-up, whereas this (PathRelations) has a bunch of expanded 
        data regarding relationships and paths. This call will first remove the 
        relationships from here, and then the entry from the EntryCache.

        We do it in this order because if we were to remove entry from the core
        library (EntryCache) first, then all of the relationships here will 
        suddenly become invalid, and although the entry will be disregistered,
        because it has references from this linked-list, those objects will be
        very much alive. On the other hand, if we remove the entry from 
        PathRelations first, then, because of the locks, PathRelations will not
        be able to touch the relationships until after we're done, here. Ergo, 
        the only thing that can happen is that something may look at the entry
        in the library.
        """

#        self.__log.debug("Doing complete removal of entry with ID [%s]." % 
#                     (entry_id))

        with PathRelations.rlock:
#            self.__log.debug("Clipping entry with ID [%s] from PathRelations and "
#                             "EntryCache." % (entry_id))

            cache = EntryCache.get_instance().cache

            removed_ids = [ entry_id ]
            if self.is_cached(entry_id):
#                self.__log.debug("Removing found PathRelations entries.")

                try:
                    removed_tuple = self.remove_entry_recursive(entry_id, \
                                                               is_update)
                except:
                    self.__log.exception("Could not remove entry-ID from "
                                         "PathRelations. Still continuing, "
                                         "though.")

                (removed_ids, number_removed) = removed_tuple

#            self.__log.debug("(%d) entries will now be removed from the core-"
#                             "cache." % (len(removed_ids)))
            for removed_id in removed_ids:
                if cache.exists(removed_id):
#                    self.__log.debug("Removing core EntryCache entry with ID "
#                                     "[%s]." % (removed_id))

                    try:
                        cache.remove(removed_id)
                    except:
                        self.__log.exception("Could not remove entry-ID from "
                                             "the core cache. Still "
                                             "continuing, though.")

#            self.__log.debug("All traces of entry with ID [%s] are gone." % 
#                             (entry_id))

    def get_proper_filenames(self, entry_clause):
        """Return what was determined to be the unique filename for this "
        particular entry for each of its respective parents. This will return 
        the standard 'title' value as a scalar when the root entry, and a 
        dictionary of parent-IDs to unique-filenames when not.

        This call is necessary because GD allows duplicate filenames until any 
        one folder. Note that a consequence of both this and the fact that GD 
        allows the same file to be listed under multiple folders means that a 
        file may look like "filename" under one and "filename (2)" under 
        another.
        """

        with PathRelations.rlock:
            found = { }
            parents = entry_clause[1]
            if not parents:
                return entry_clause[0].title_fs

            else:
                for parent_clause in parents:
                    matching_children = [filename for filename, child_clause 
                                                  in parent_clause[2] 
                                                  if child_clause == entry_clause]
                    if not matching_children:
                        self.__log.error("No matching entry-ID [%s] was not "
                                         "found among children of entry's "
                                         "parent with ID [%s] for proper-"
                                         "filename lookup." % 
                                         (entry_clause[3], parent_clause[3]))

                    else:
                        found[parent_clause[3]] = matching_children[0]

        return found

    def register_entry(self, normalized_entry):

#        self.__log.debug("We're registering entry with ID [%s] [%s]." % 
#                         (normalized_entry.id, normalized_entry.title))

        with PathRelations.rlock:
            if not normalized_entry.is_visible:
#                self.__log.debug("We will not register entry with ID [%s] "
#                                 "because it's not visible." % 
#                                 (normalized_entry.id))
                return None

            if normalized_entry.__class__ is not NormalEntry:
                raise Exception("PathRelations expects to register an object "
                                "of type NormalEntry, not [%s]." % 
                                (type(normalized_entry)))

            entry_id = normalized_entry.id

#            self.__log.debug("Registering entry with ID [%s] within path-"
#                             "relations.", entry_id)

            if self.is_cached(entry_id, include_placeholders=False):
#                self.__log.debug("Entry to register with ID [%s] already "
#                                 "exists within path-relations, and will be "
#                                 "removed in lieu of update." % (entry_id))

#                self.__log.debug("Removing existing entries.")

                self.remove_entry_recursive(entry_id, True)

#            self.__log.debug("Doing add of entry with ID [%s]." % (entry_id))

            cache = EntryCache.get_instance().cache

            cache.set(normalized_entry.id, normalized_entry)

            # We do a linked list using object references.
            # (
            #   normalized_entry, 
            #   [ parent clause, ... ], 
            #   [ child clause, ... ], 
            #   entry-ID,
            #   < boolean indicating that we know about all children >
            # )

            if self.is_cached(entry_id, include_placeholders=True):
#                self.__log.debug("Placeholder exists for entry-to-register "
#                                 "with ID [%s]." % (entry_id))

                entry_clause = self.entry_ll[entry_id]
                entry_clause[CLAUSE_ENTRY] = normalized_entry
                entry_clause[CLAUSE_PARENT] = [ ]
            else:
#                self.__log.debug("Entry does not yet exist in LL.")

                entry_clause = [normalized_entry, [ ], [ ], entry_id, False]
                self.entry_ll[entry_id] = entry_clause

            entry_parents = entry_clause[CLAUSE_PARENT]
            title_fs = normalized_entry.title_fs

#            self.__log.debug("Registering entry with title [%s]." % (title_fs))

            parent_ids = normalized_entry.parents if normalized_entry.parents \
                                                  is not None else []

#            self.__log.debug("Parents are: %s" % (', '.join(parent_ids)))

            for parent_id in parent_ids:
#                self.__log.debug("Processing parent with ID [%s] of entry "
#                                 "with ID [%s]." % (parent_id, entry_id))

                # If the parent hasn't yet been loaded, install a placeholder.
                if self.is_cached(parent_id, include_placeholders=True):
#                    self.__log.debug("Parent has an existing entry.")

                    parent_clause = self.entry_ll[parent_id]
                else:
#                    self.__log.debug("Parent is not yet registered.")

                    parent_clause = [None, None, [ ], parent_id, False]
                    self.entry_ll[parent_id] = parent_clause

                if parent_clause not in entry_parents:
                    entry_parents.append(parent_clause)

                parent_children = parent_clause[CLAUSE_CHILDREN]
                filename_base = title_fs

                # Register among the children of this parent, but make sure we 
                # have a unique filename among siblings.

                i = 0
                current_variation = filename_base
                elected_variation = None
                while i <= 255:
                    if not [ child_name_tuple 
                             for child_name_tuple 
                             in parent_children 
                             if child_name_tuple[0] == current_variation ]:
                        elected_variation = current_variation
                        break
                        
                    i += 1
                    current_variation = filename_base + \
                                        utility.translate_filename_charset(
                                            ' (%d)' % (i))

                if elected_variation == None:
                    self.__log.error("Could not register entry with ID [%s]. "
                                     "There are too many duplicate names in "
                                     "that directory." % (entry_id))
                    return

#                self.__log.debug("Final filename is [%s]." % 
#                                 (current_variation))

                # Register us in the list of children on this parents 
                # child-tuple list.
                parent_children.append((elected_variation, entry_clause))

#        self.__log.debug("Entry registration complete.")

        return entry_clause

    def __load_all_children(self, parent_id):
#        self.__log.debug("Loading children under parent with ID [%s].",
#                         parent_id)

        with PathRelations.rlock:
            children = drive_proxy('list_files', parent_id=parent_id)

            child_ids = [ ]
            if children:
#                self.__log.debug("(%d) children returned and will be "
#                                 "registered.", len(children))

                for child in children:
                        self.register_entry(child)

#                self.__log.debug("Looking up parent with ID [%s] for all-"
#                                 "children update.", parent_id)

                parent_clause = self.__get_entry_clause_by_id(parent_id)

                parent_clause[4] = True

#                self.__log.debug("All children have been loaded.")

        return children

    def get_children_from_entry_id(self, entry_id):
        """Return the filenames contained in the folder with the given 
        entry-ID.
        """

#        self.__log.debug("Getting children under entry with ID [%s].",entry_id)

        with PathRelations.rlock:
            entry_clause = self.__get_entry_clause_by_id(entry_id)
            if not entry_clause:
                message = ("Can not list the children for an unavailable entry "
                           "with ID [%s]." % (entry_id))

                self.__log.error(message)
                raise Exception(message)

            if not entry_clause[4]:
#                self.__log.debug("Not all children have been loaded for "
#                                 "parent with ID [%s]. Loading them now." % 
#                                 (entry_id))

                self.__load_all_children(entry_id)

#            else:
#                self.__log.debug("All children for [%s] have already been "
#                                 "loaded." % (entry_id))

            if not entry_clause[0].is_directory:
                message = ("Could not get child filenames for non-directory with "
                           "entry-ID [%s]." % (entry_id))

                self.__log.error(message)
                raise Exception(message)

#            self.__log.debug("(%d) children found.",
#                             len(entry_clause[CLAUSE_CHILDREN]))

            return entry_clause[CLAUSE_CHILDREN]

    def get_children_entries_from_entry_id(self, entry_id):

        children_tuples = self.get_children_from_entry_id(entry_id)

        children_entries = [(child_tuple[0], child_tuple[1][CLAUSE_ENTRY]) 
                                for child_tuple 
                                in children_tuples]

        return children_entries

    def get_clause_from_path(self, filepath):

#        self.__log.debug("Getting clause for path [%s].", filepath)

        with PathRelations.rlock:
            path_results = self.find_path_components_goandget(filepath)

            (entry_ids, path_parts, success) = path_results
            if not success:
                return None

            entry_id = path_results[0][-1]
#            self.__log.debug("Found entry with ID [%s].", entry_id)

            # Make sure the entry is more than a placeholder.
            self.__get_entry_clause_by_id(entry_id)

            return self.entry_ll[entry_id]

    def find_path_components_goandget(self, path):
        """Do the same thing that find_path_components() does, except that 
        when we don't have record of a path-component, try to go and find it 
        among the children of the previous path component, and then try again.
        """

        with PathRelations.rlock:
            previous_results = []
            i = 0
            while 1:
#                self.__log.debug("Attempting to find path-components (go and "
#                                 "get) for path [%s].  CYCLE= (%d)", path, i)

                # See how many components can be found in our current cache.

                result = self.__find_path_components(path)

#                self.__log.debug("Path resolution cycle (%d) results: %s" % 
#                                 (i, result))

                # If we could resolve the entire path, return success.

#                self.__log.debug("Found within current cache? %s" % 
#                                 (result[2]))

                if result[2] == True:
                    return result

                # If we could not resolve the entire path, and we're no more 
                # successful than a prior attempt, we'll just have to return a 
                # partial.

                num_results = len(result[0])
                if num_results in previous_results:
#                    self.__log.debug("We couldn't improve our results. This "
#                                     "path most likely does not exist.")
                    return result

                previous_results.append(num_results)

#                self.__log.debug("(%d) path-components were found, but not "
#                                 "all." % (num_results))

                # Else, we've encountered a component/depth of the path that we 
                # don't currently know about.
# TODO: This is going to be the general area that we'd have to adjust to 
#        support multiple, identical entries. This currently only considers the 
#        first result. We should rewrite this to be recursive in order to make 
#        it easier to keep track of a list of results.
                # The parent is the last one found, or the root if none.
                parent_id = result[0][num_results - 1] \
                                if num_results \
                                else AccountInfo.get_instance().root_id

                # The child will be the first part that was not found.
                child_name = result[1][num_results]

#                self.__log.debug("Trying to reconcile child named [%s] under "
#                                 "folder with entry-ID [%s]." % (child_name, 
#                                                                 parent_id))

                children = drive_proxy('list_files', parent_id=parent_id, 
                                       query_is_string=child_name)
                
                for child in children:
                    self.register_entry(child)

                filenames_phrase = ', '.join([ candidate.id for candidate
                                                            in children ])

#                self.__log.debug("(%d) candidate children were found: %s",
#                                 len(children), filenames_phrase)

                i += 1

    def __find_path_components(self, path):
        """Given a path, return a list of all Google Drive entries that 
        comprise each component, or as many as can be found. As we've ensured 
        that all sibling filenames are unique, there can not be multiple 
        matches.
        """

#        self.__log.debug("Searching for path components of [%s]. Now "
#                         "resolving entry_clause." % (path))

        if path[0] == '/':
            path = path[1:]

        if len(path) and path[-1] == '/':
            path = path[:-1]

        if path in self.path_cache:
            return self.path_cache[path]

        with PathRelations.rlock:
#            self.__log.debug("Locating entry information for path [%s].", path)
            root_id = AccountInfo.get_instance().root_id

            # Ensure that the root node is loaded.
            self.__get_entry_clause_by_id(root_id)

            path_parts = path.split('/')

            entry_ptr = root_id
            parent_id = None
            i = 0
            num_parts = len(path_parts)
            results = [ ]
            while i < num_parts:
                child_filename_to_search_fs = utility. \
                    translate_filename_charset(path_parts[i])

#                self.__log.debug("Checking for part (%d) [%s] under parent "
#                                 "with ID [%s].",
#                                 i, child_filename_to_search_fs, entry_ptr)

                current_clause = self.entry_ll[entry_ptr]
            
                # Search this entry's children for the next filename further down 
                # in the path among this entry's children. Any duplicates should've 
                # already beeen handled as entries were stored. We name the variable 
                # just to emphasize that no ambiguity -as well as- no error will 
                # occur in the traversal process.
                first_matching_child_clause = None
                children = current_clause[2]
            
                # If they just wanted the "" path (root), return the root-ID.
                if path == "":
                    found = [ root_id ]
                else:
#                    self.__log.debug("Looking for child [%s] among (%d): %s" % 
#                                  (child_filename_to_search_fs, len(children),
#                                   [ child_tuple[0] for child_tuple 
#                                     in children ]))

                    found = [ child_tuple[1][3] 
                              for child_tuple 
                              in children 
                              if child_tuple[0] == child_filename_to_search_fs ]

                if found:
#                    self.__log.debug("Found matching child with ID [%s]." % (found[0]))
                    results.append(found[0])
                else:
#                    self.__log.debug("Did not find matching child.")
                    return (results, path_parts, False)

                # Have we traveled far enough into the linked list?
                if (i + 1) >= num_parts:
#                    self.__log.debug("Path has been completely resolved: %s" % (', '.join(results)))

                    self.path_cache[path] = (results, path_parts, True)
                    final_entry_id = results[-1]
                    self.path_cache_byid[final_entry_id] = path

                    return self.path_cache[path]

                parent_id = entry_ptr
                entry_ptr = found[0]
                i += 1

    def __get_entry_clause_by_id(self, entry_id):
        """We may keep a linked-list of GD entries, but what we have may just 
        be placeholders. This function will make sure the data is actually here.
        """

        with PathRelations.rlock:
            if self.is_cached(entry_id):
                return self.entry_ll[entry_id]

            else:
                cache = EntryCache.get_instance().cache
                normalized_entry = cache.get(entry_id)
                return self.register_entry(normalized_entry)

    def is_cached(self, entry_id, include_placeholders=False):

        return (entry_id in self.entry_ll and (include_placeholders or \
                                               self.entry_ll[entry_id][0]))

class EntryCache(CacheClientBase):
    """Manages our knowledge of file entries."""

    __log = None
    about = AccountInfo.get_instance()

    def __init__(self):
        self.__log = logging.getLogger().getChild('EntryCache')
        CacheClientBase.__init__(self)

    def __get_entries_to_update(self, requested_entry_id):
        # Get more entries than just what was requested, while we're at it.

        parent_ids = drive_proxy('get_parents_containing_id', 
                                 child_id=requested_entry_id)

#        self.__log.debug("Found (%d) parents.", len(parent_ids))

        affected_entries = [ requested_entry_id ]
        considered_entries = { }
        max_readahead_entries = Conf.get('max_readahead_entries')
        for parent_id in parent_ids:
#            self.__log.debug("Retrieving children for parent with ID [%s].",
#                             parent_id)

            child_ids = drive_proxy('get_children_under_parent_id', 
                                    parent_id=parent_id)

#            self.__log.debug("(%d) children found under parent with ID [%s].",
#                             len(child_ids), parent_id)

            for child_id in child_ids:
                if child_id == requested_entry_id:
                    continue

                # We've already looked into this entry.

                try:
                    considered_entries[child_id]
                    continue
                except:
                    pass

                considered_entries[child_id] = True

                # Is it already cached?

                if self.cache.exists(child_id):
                    continue

                affected_entries.append(child_id)

                if len(affected_entries) >= max_readahead_entries:
                    break

        return affected_entries

    def __do_update_for_missing_entry(self, requested_entry_id):

        # Get the entries to update.

        affected_entries = self.__get_entries_to_update(requested_entry_id)

        # Read the entries, now.

#        self.__log.debug("(%d) primary and secondary entry/entries will be "
#                        "updated." % (len(affected_entries)))

        # TODO: We have to determine when this is called, and either remove it 
        # (if it's not), or find another way to not have to load them 
        # individually.

        retrieved = drive_proxy('get_entries', entry_ids=affected_entries)

        # Update the cache.

        path_relations = PathRelations.get_instance()

        for entry_id, entry in retrieved.iteritems():
            path_relations.register_entry(entry)

#        self.__log.debug("(%d) entries were loaded.", len(retrieved))

        return retrieved

    def fault_handler(self, resource_name, requested_entry_id):
        """A requested entry wasn't stored."""

#        self.__log.debug("EntryCache has faulted on entry with ID [%s].",
#                         requested_entry_id)

        retrieved = self.__do_update_for_missing_entry(requested_entry_id)

        # Return the requested entry.
        return retrieved[requested_entry_id]

    def cleanup_pretrigger(self, resource_name, entry_id, force):
        """The core entry cache has a clean-up process that will remove old "
        entries. This is called just before any record is removed.
        """

        # Now that the local cache-item has been removed, remove the same from
        # the PathRelations cache.

        path_relations = PathRelations.get_instance()

        if path_relations.is_cached(entry_id):
#            self.__log.debug("Removing PathRelations entry for cleaned-up entry "
#                             "with ID [%s]." % (entry_id))

            path_relations.remove_entry_recursive(entry_id)

    def get_max_cache_age_seconds(self):
        return Conf.get('cache_entries_max_age')


########NEW FILE########
__FILENAME__ = change
import logging

from threading import Lock, Timer

from gdrivefs.conf import Conf
from gdrivefs.timer import Timers
from gdrivefs.gdtool.account_info import AccountInfo
from gdrivefs.gdtool.drive import drive_proxy
from gdrivefs.cache.volume import PathRelations, EntryCache

_logger = logging.getLogger(__name__)

def _sched_check_changes():
    logging.debug("Doing scheduled check for changes.")

    try:
        get_change_manager().process_updates()
        logging.debug("Updates have been processed. Rescheduling.")

        # Schedule next invocation.
        t = Timer(Conf.get('change_check_frequency_s'), _sched_check_changes)

        Timers.get_instance().register_timer('change', t)
    except:
        _logger.exception("Exception while managing changes.")
        raise

class _ChangeManager(object):
    def __init__(self):
        self.at_change_id = AccountInfo.get_instance().largest_change_id
        _logger.debug("Latest change-ID at startup is (%d)." % 
                      (self.at_change_id))

    def mount_init(self):
        """Called when filesystem is first mounted."""

        _logger.debug("Scheduling change monitor.")
        _sched_check_changes()

    def mount_destroy(self):
        """Called when the filesystem is unmounted."""

        _logger.debug("Change destroy.")

    def process_updates(self):
        """Process any changes to our files. Return True if everything is up to
        date or False if we need to be run again.
        """
# TODO(dustin): Is there any way that we can block on this call?
        start_at_id = (self.at_change_id + 1)

        _logger.debug("Requesting changes.")
        result = drive_proxy('list_changes', start_change_id=start_at_id)
        (largest_change_id, next_page_token, changes) = result

        _logger.debug("The latest reported change-ID is (%d) and we're "
                      "currently at change-ID (%d)." % 
                      (largest_change_id, self.at_change_id))

        if largest_change_id == self.at_change_id:
            _logger.debug("No entries have changed.")
            return True

        _logger.info("(%d) changes will now be applied." % (len(changes)))

        for change_id, change_tuple in changes.iteritems():
            # Apply the changes. We expect to be running them from oldest to 
            # newest.

            _logger.info("========== Change with ID (%d) will now be applied. ==========" %
                            (change_id))

            try:
                self.__apply_change(change_id, change_tuple)
            except:
                _logger.exception("There was a problem while processing change"
                                  " with ID (%d). No more changes will be "
                                  "applied." % (change_id))
                return False

            self.at_change_id = change_id

        return (next_page_token == None)

    def __apply_change(self, change_id, change_tuple):
        """Apply changes to our filesystem reported by GD. All we do is remove 
        the current record components, if it's valid, and then reload it with 
        what we were given. Note that since we don't necessarily know
        about the entries that have been changed, this also allows us to slowly
        increase our knowledge of the filesystem (of, obviously, only those 
        things that change).
        """

        (entry_id, was_deleted, entry) = change_tuple
        
        is_visible = entry.is_visible if entry else None

        _logger.info("Applying change with change-ID (%d), entry-ID [%s], "
                        "and is-visible of [%s]" % 
                        (change_id, entry_id, is_visible))

        # First, remove any current knowledge from the system.

        _logger.debug("Removing all trace of entry with ID [%s] "
                         "(apply_change)." % (entry_id))

        try:
            PathRelations.get_instance().remove_entry_all(entry_id)
        except:
            _logger.exception("There was a problem remove entry with ID "
                                 "[%s] from the caches." % (entry_id))
            raise

        # If it wasn't deleted, add it back.

        _logger.debug("Registering changed entry with ID [%s]." % 
                         (entry_id))

        if is_visible:
            path_relations = PathRelations.get_instance()

            try:
                path_relations.register_entry(entry)
            except:
                _logger.exception("Could not register changed entry with "
                                     "ID [%s] with path-relations cache." % 
                                     (entry_id))
                raise

def get_change_manager():
    with get_change_manager.lock:
        if not get_change_manager.instance:
            get_change_manager.instance = _ChangeManager()

        return get_change_manager.instance

get_change_manager.instance = None
get_change_manager.lock = Lock()


########NEW FILE########
__FILENAME__ = conf
import logging
from apiclient.discovery import DISCOVERY_URI

class Conf(object):
    """Manages options."""

    api_credentials = {
        "web": { "client_id": "1056816309698.apps.googleusercontent.com",
                 "client_secret": "R7FJFlbtWXgUoG3ZjIAWUAzv",
                 "redirect_uris": [],
                 "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                 "token_uri": "https://accounts.google.com/o/oauth2/token"
               }}
    
    auth_cache_filepath                 = None
    gd_to_normal_mapping_filepath       = '/etc/gdfs/mime_mapping.json'
    extension_mapping_filepath          = '/etc/gdfs/extension_mapping.json'
    query_decay_intermed_prefix_length  = 7
    file_jobthread_max_idle_time        = 60
    file_chunk_size_kb                  = 1024
    file_download_temp_path             = '/tmp/gdrivefs'
    file_download_temp_max_age_s        = 86400
    file_default_mime_type              = 'application/octet-stream'
    change_check_frequency_s            = 10
    hidden_flags_list_local             = [u'trashed', u'restricted']
    hidden_flags_list_remote            = [u'trashed']
    cache_cleanup_check_frequency_s     = 60
    cache_entries_max_age               = 8 * 60 * 60
    cache_status_post_frequency_s       = 10
    report_emit_frequency_s             = 60
    google_discovery_service_url        = DISCOVERY_URI
    default_buffer_read_blocksize       = 65536
    default_mimetype                    = 'application/octet-stream'
    directory_mimetype                  = u'application/vnd.google-apps.folder'
    default_perm_folder                 = '777'
    default_perm_file_editable          = '666'
    default_perm_file_noneditable       = '444'

    # How many extra entries to retrieve when an entry is accessed that is not
    # currently cached.
    max_readahead_entries = 10

    @staticmethod
    def get(key):
        try:
            return Conf.__dict__[key]
        except:
            logging.exception("Could not retrieve config value with key "
                              "[%s]." % (key))
            raise

    @staticmethod
    def set(key, value):
        if key not in Conf.__dict__:
            raise KeyError(key)

        setattr(Conf, key, value)


########NEW FILE########
__FILENAME__ = download_agent
REQUEST_QUEUE_TIMEOUT_S = 1
NUM_WORKERS = 10
GRACEFUL_WORKER_EXIT_WAIT_S = 10

# This must be larger than GRACEFUL_WORKER_EXIT_WAIT_S, since this one subsumes 
# the other.
GRACEFUL_AGENT_EXIT_WAIT_S = 15

HTTP_POOL_SIZE = 10
REQUEST_WAIT_PERIOD_S = 1
DOWNLOAD_PATH = '/tmp/gdrivefs/downloads'
CHUNK_SIZE = 1024*1024

FILE_STATE_STAMP_SUFFIX_DOWNLOADING = 'partial'


########NEW FILE########
__FILENAME__ = errors
class GdFsError(Exception):
    pass

class AuthorizationError(GdFsError):
    """All authorization-related errors inherit from this."""
    pass

class AuthorizationFailureError(AuthorizationError):
    """There was a general authorization failure."""
    pass
        
class AuthorizationFaultError(AuthorizationError):
    """Our authorization is not available or has expired."""
    pass

class MustIgnoreFileError(GdFsError):
    """An error requiring us to ignore the file."""
    pass

class FilenameQuantityError(MustIgnoreFileError):
    """Too many filenames share the same name in a single directory."""
    pass

class ExportFormatError(GdFsError):
    """A format was not available for export."""
    pass

class GdNotFoundError(GdFsError):
    """A file/path was not found."""
    pass

# TODO: Not used?
class EntryNoLongerCachedError(GdFsError):
    pass


########NEW FILE########
__FILENAME__ = displaced_file
import logging
import json

from os import makedirs
from os.path import isdir

from gdrivefs.gdtool.drive import drive_proxy
from gdrivefs.gdtool.normal_entry import NormalEntry
from gdrivefs.conf import Conf

temp_path = ("%s/displaced" % (Conf.get('file_download_temp_path')))
if isdir(temp_path) is False:
    makedirs(temp_path)


class DisplacedFile(object):
    __log = None
    normalized_entry = None
    file_size = 1000

    def __init__(self, normalized_entry):
        self.__log = logging.getLogger().getChild('DisFile')
    
        if normalized_entry.__class__ != NormalEntry:
            raise Exception("_DisplacedFile can not wrap a non-NormalEntry "
                            "object.")

        self.__normalized_entry = normalized_entry

    def deposit_file(self, mime_type):
        """Write the file to a temporary path, and present a stub (JSON) to the 
        user. This is the only way of getting files that don't have a 
        well-defined filesize without providing a type, ahead of time.
        """

        temp_path = Conf.get('file_download_temp_path')
        file_path = ("%s/displaced/%s.%s" % (temp_path, 
                                             self.__normalized_entry.title, 
                                             mime_type.replace('/', '+')))

        try:
            result = drive_proxy('download_to_local', 
                                 output_file_path=file_path, 
                                 normalized_entry=self.__normalized_entry,
                                 mime_type=mime_type)
            (length, cache_fault) = result
        except:
            self.__log.exception("Could not localize displaced file with "
                                 "entry having ID [%s]." % 
                                 (self.__normalized_entry.id))
            raise

        self.__log.debug("Displaced entry [%s] deposited to [%s] with length "
                         "(%d)." % 
                         (self.__normalized_entry, file_path, length)) 

        try:
            return self.get_stub(mime_type, length, file_path)
        except:
            self.__log.exception("Could not build stub for [%s]." % 
                                 (self.__normalized_entry))
            raise

    def get_stub(self, mime_type, file_size=0, file_path=None):
        """Return the content for an info ("stub") file."""

        if file_size == 0 and \
           self.__normalized_entry.requires_displaceable is False:
            file_size = self.__normalized_entry.file_size

        stub_data = {
                'EntryId':              self.__normalized_entry.id,
                'OriginalMimeType':     self.__normalized_entry.mime_type,
                'ExportTypes':          self.__normalized_entry.download_types,
                'Title':                self.__normalized_entry.title,
                'Labels':               self.__normalized_entry.labels,
                'FinalMimeType':        mime_type,
                'Length':               file_size,
                'RequiresMimeType':     self.__normalized_entry.requires_mimetype,
                'ImageMediaMetadata':   self.__normalized_entry.image_media_metadata
            }

        if file_path:
            stub_data['FilePath'] = file_path

        try:
            result = json.dumps(stub_data)
            padding = (' ' * (self.file_size - len(result) - 1))

            return ("%s%s\n" % (result, padding))
        except:
            self.__log.exception("Could not serialize stub-data.")
            raise


########NEW FILE########
__FILENAME__ = fsutility
import logging
import re
import fuse

from os.path import split
from fuse import FuseOSError, fuse_get_context

from gdrivefs.errors import GdNotFoundError

log = logging.getLogger('FsUtility')

def dec_hint(argument_names=[], excluded=[], prefix='', otherdata_cb=None):
    """A decorator for the calling of functions to be emphasized in the 
    logging. Displays prefix and suffix information in the logs.
    """

#    try:
#        log = dec_hint.log
#    except:
#        log = log.getLogger().getChild('VfsAction')
#        dec_hint.log = log
    dec_hint.log = log

    # We use a serial-number so that we can eyeball corresponding pairs of
    # beginning and ending statements in the logs.
    sn = getattr(dec_hint, 'sn', 0) + 1
    dec_hint.sn = sn

    prefix = ("%s: " % (prefix)) if prefix else ''

    def real_decorator(f):
        def wrapper(*args, **kwargs):
        
            try:
                pid = fuse_get_context()[2]
            except:
                # Just in case.
                pid = 0
        
            if not prefix:
                log.debug('--------------------------------------------------')

            log.debug("%s>>>>>>>>>> %s(%d) >>>>>>>>>> (%d)" % 
                      (prefix, f.__name__, sn, pid))
        
            if args or kwargs:
                condensed = {}
                for i in xrange(len(args)):
                    # Skip the 'self' argument.
                    if i == 0:
                        continue
                
                    if i - 1 >= len(argument_names):
                        break

                    condensed[argument_names[i - 1]] = args[i]

                for k, v in kwargs.iteritems():
                    condensed[k] = v

                values_nice = [("%s= [%s]" % (k, v)) for k, v \
                                                     in condensed.iteritems() \
                                                     if k not in excluded]
                
                if otherdata_cb:
                    data = otherdata_cb(*args, **kwargs)
                    for k, v in data.iteritems():
                        values_nice[k] = v
                
                if values_nice:
                    values_string = '  '.join(values_nice)
                    log.debug("DATA: %s" % (values_string))

            suffix = ''

            try:
                result = f(*args, **kwargs)
            except FuseOSError as e:
                if e.errno not in (fuse.ENOENT,):
                    log.error("FUSE error [%s] (%s) will be forwarded back to "
                              "GDFS from [%s]: %s", 
                              e.__class__.__name__, e.errno, f.__name__, 
                              str(e))
                raise
            except Exception as e:
                log.exception("There was an exception in [%s]" % (f.__name__))
                suffix = (' (E(%s): "%s")', e.__class__.__name__, str(e))
                raise
            finally:
                log.debug("%s<<<<<<<<<< %s(%d) (%d)%s", 
                          prefix, f.__name__, sn, pid, suffix)
            
            return result
        return wrapper
    return real_decorator

def strip_export_type(path):

    matched = re.search('#([a-zA-Z0-9\-]+\\+[a-zA-Z0-9\-]+)?$', 
                       path.encode('ASCII'))

    mime_type = None

    if matched:
        fragment = matched.group(0)
        mime_type = matched.group(1)
        
        if mime_type is not None:
            mime_type = mime_type.replace('+', '/')

        path = path[:-len(fragment)]

    return (path, mime_type)

def split_path(filepath_original, pathresolver_cb):
    """Completely process and distill the requested file-path. The filename can"
    be padded to adjust what's being requested. This will remove all such 
    information, and return the actual file-path along with the extra meta-
    information. pathresolver_cb should expect a single parameter of a path,
    and return a NormalEntry object. This can be used for both directories and 
    files.
    """

    # Remove any export-type that this file-path might've been tagged with.

    try:
        (filepath, mime_type) = strip_export_type(filepath_original)
    except:
        log.exception("Could not process path [%s] for export-type." % 
                      (filepath_original))
        raise

#    log.debug("File-path [%s] split into filepath [%s] and mime_type "
#              "[%s]." % (filepath_original, filepath, mime_type))

    # Split the file-path into a path and a filename.

    (path, filename) = split(filepath)

    # Lookup the file, as it was listed, in our cache.

    try:
        path_resolution = pathresolver_cb(path)
# TODO(dustin): We need to specify the exception for when a file doesn't exist.
    except:
        log.exception("Exception while getting entry from path [%s]." % (path))
        raise GdNotFoundError()

    if not path_resolution:
#        log.debug("Path [%s] does not exist for split." % (path))
        raise GdNotFoundError()

    (parent_entry, parent_clause) = path_resolution

    is_hidden = (filename[0] == '.') if filename else False

#    log.debug("File-path [%s] split into parent with ID [%s], path [%s], "
#              "unverified filename [%s], mime-type [%s], and is_hidden [%s]." % 
#              (filepath_original, parent_entry.id, path, filename, 
#               mime_type, is_hidden))

    return (parent_clause, path, filename, mime_type, is_hidden)

def split_path_nolookups(filepath_original):
    """This allows us to get the is-hidden flag, mimetype info, path, and 
    filename, without doing the [time consuming] lookup if unnecessary.
    """

    # Remove any export-type that this file-path might've been tagged with.

    try:
        (filepath, mime_type) = strip_export_type(filepath_original)
    except:
        log.exception("Could not process path [%s] for export-type." % 
                      (filepath_original))
        raise

    # Split the file-path into a path and a filename.

    (path, filename) = split(filepath)

    # We don't remove the period, if we will mark it as hidden, as appropriate.
    is_hidden = (filename[0] == '.') if filename else False

    return (path, filename, mime_type, is_hidden)

def build_filepath(path, filename):
    separator = '/' if path != '/' else ''

    return ('%s%s%s' % (path, separator, filename))

def escape_filename_for_query(filename):
    return filename.replace("\\", "\\\\").replace("'", "\\'")


########NEW FILE########
__FILENAME__ = gdfuse
import stat
import logging
import dateutil.parser
import re
import json
import os
import atexit
import resource
import os.path

from errno import ENOENT, EIO, ENOTDIR, ENOTEMPTY, EPERM, EEXIST
from fuse import FUSE, Operations, FuseOSError, c_statvfs, fuse_get_context, \
                 LoggingMixIn
from time import mktime, time
from sys import argv, exit, excepthook
from mimetypes import guess_type
from datetime import datetime
from os.path import split

import gdrivefs.gdfs.fsutility

from gdrivefs.utility import utility
from gdrivefs.change import get_change_manager
from gdrivefs.timer import Timers
from gdrivefs.cache.volume import PathRelations, EntryCache, \
                                  CLAUSE_ENTRY, CLAUSE_PARENT, \
                                  CLAUSE_CHILDREN, CLAUSE_ID, \
                                  CLAUSE_CHILDREN_LOADED
from gdrivefs.conf import Conf
from gdrivefs.gdtool.oauth_authorize import get_auth
from gdrivefs.gdtool.drive import drive_proxy
from gdrivefs.gdtool.account_info import AccountInfo
from gdrivefs.general.buffer_segments import BufferSegments
from gdrivefs.gdfs.opened_file import OpenedManager, OpenedFile
from gdrivefs.gdfs.fsutility import strip_export_type, split_path,\
                                    build_filepath, dec_hint
from gdrivefs.gdfs.displaced_file import DisplacedFile
from gdrivefs.cache.volume import path_resolver
from gdrivefs.errors import GdNotFoundError
from gdrivefs.time_support import get_flat_normal_fs_time_from_epoch

_logger = logging.getLogger().getChild(__name__)


# TODO: make sure strip_extension and split_path are used when each are relevant
# TODO: make sure create path reserves a file-handle, uploads the data, and then registers the open-file with the file-handle.
# TODO: Make sure that we rely purely on the FH, whenever it is given, 
#       whereever it appears. This will be to accomodate system calls that can work either via file-path or file-handle.

def set_datetime_tz(datetime_obj, tz):
    return datetime_obj.replace(tzinfo=tz)

def get_entry_or_raise(raw_path, allow_normal_for_missing=False):
    try:
        result = split_path(raw_path, path_resolver)
        (parent_clause, path, filename, mime_type, is_hidden) = result
    except GdNotFoundError:
        _logger.exception("Could not retrieve clause for non-existent "
                          "file-path [%s] (parent does not exist)." % 
                          (raw_path))

        if allow_normal_for_missing is True:
            raise
        else:
            raise FuseOSError(ENOENT)
    except:
        _logger.exception("Could not process file-path [%s]." % 
                          (raw_path))
        raise FuseOSError(EIO)

    filepath = build_filepath(path, filename)
    path_relations = PathRelations.get_instance()

    try:
        entry_clause = path_relations.get_clause_from_path(filepath)
    except GdNotFoundError:
        _logger.exception("Could not retrieve clause for non-existent "
                          "file-path [%s] (parent exists)." % 
                          (filepath))

        if allow_normal_for_missing is True:
            raise
        else:
            raise FuseOSError(ENOENT)
    except:
        _logger.exception("Could not retrieve clause for path [%s]. " %
                          (filepath))
        raise FuseOSError(EIO)

    if not entry_clause:
        if allow_normal_for_missing is True:
            raise GdNotFoundError()
        else:
            raise FuseOSError(ENOENT)

    return (entry_clause[CLAUSE_ENTRY], path, filename)


class GDriveFS(LoggingMixIn,Operations):
    """The main filesystem class."""

    __log = None

    def __init__(self):
        Operations.__init__(self)

        _logger = logging.getLogger().getChild('GD_VFS')

    def __register_open_file(self, fh, path, entry_id):

        with self.fh_lock:
            self.open_files[fh] = (entry_id, path)

    def __deregister_open_file(self, fh):

        with self.fh_lock:
            try:
                file_info = self.open_files[fh]
            except:
                _logger.exception("Could not deregister invalid file-handle "
                                  "(%d)." % (fh))
                raise

            del self.open_files[fh]
            return file_info

    def __get_open_file(self, fh):

        with self.fh_lock:
            try:
                return self.open_files[fh]
            except:
                _logger.exception("Could not retrieve on invalid file-handle "
                                  "(%d)." % (fh))
                raise

    def __build_stat_from_entry(self, entry):
        (uid, gid, pid) = fuse_get_context()

        if entry.is_directory:
            effective_permission = int(Conf.get('default_perm_folder'), 
                                       8)
        elif entry.editable:
            effective_permission = int(Conf.get('default_perm_file_editable'), 
                                       8)
        else:
            effective_permission = int(Conf.get(
                                            'default_perm_file_noneditable'), 
                                       8)

        stat_result = { "st_mtime": entry.modified_date_epoch, # modified time.
                        "st_ctime": entry.modified_date_epoch, # changed time.
                        "st_atime": time(),
                        "st_uid":   uid,
                        "st_gid":   gid }
        
        if entry.is_directory:
            # Per http://sourceforge.net/apps/mediawiki/fuse/index.php?title=SimpleFilesystemHowto, 
            # default size should be 4K.
# TODO(dustin): Should we just make this (0), since that's what it is?
            stat_result["st_size"] = 1024 * 4
            stat_result["st_mode"] = (stat.S_IFDIR | effective_permission)
            stat_result["st_nlink"] = 2
        else:
            stat_result["st_size"] = DisplacedFile.file_size \
                                        if entry.requires_mimetype \
                                        else entry.file_size

            stat_result["st_mode"] = (stat.S_IFREG | effective_permission)
            stat_result["st_nlink"] = 1

        return stat_result

    @dec_hint(['raw_path', 'fh'])
    def getattr(self, raw_path, fh=None):
        """Return a stat() structure."""
# TODO: Implement handle.

        (entry, path, filename) = get_entry_or_raise(raw_path)
        return self.__build_stat_from_entry(entry)

    @dec_hint(['path', 'offset'])
    def readdir(self, path, offset):
        """A generator returning one base filename at a time."""

        # We expect "offset" to always be (0).
        if offset != 0:
            _logger.warning("readdir() has been invoked for path [%s] and "
                               "non-zero offset (%d). This is not allowed." % 
                               (path, offset))

# TODO: Once we start working on the cache, make sure we don't make this call, 
#       constantly.

        path_relations = PathRelations.get_instance()

        try:
            entry_clause = path_relations.get_clause_from_path(path)
        except GdNotFoundError:
            _logger.exception("Could not process [%s] (readdir).")
            raise FuseOSError(ENOENT)
        except:
            _logger.exception("Could not get clause from path [%s] "
                              "(readdir)." % (path))
            raise FuseOSError(EIO)

        if not entry_clause:
            raise FuseOSError(ENOENT)

        try:
            entry_tuples = path_relations.get_children_entries_from_entry_id \
                            (entry_clause[CLAUSE_ID])
        except:
            _logger.exception("Could not render list of filenames under path "
                                 "[%s]." % (path))
            raise FuseOSError(EIO)

        yield utility.translate_filename_charset('.')
        yield utility.translate_filename_charset('..')

        for (filename, entry) in entry_tuples:

            # Decorate any file that -requires- a mime-type (all files can 
            # merely accept a mime-type)
            if entry.requires_mimetype:
                filename += utility.translate_filename_charset('#')
        
            yield (filename,
                   self.__build_stat_from_entry(entry),
                   0)

    @dec_hint(['raw_path', 'length', 'offset', 'fh'])
    def read(self, raw_path, length, offset, fh):

        try:
            opened_file = OpenedManager.get_instance().get_by_fh(fh)
        except:
            _logger.exception("Could not retrieve OpenedFile for handle "
                                 "with ID (%d) (read)." % (fh))
            raise FuseOSError(EIO)

        try:
            return opened_file.read(offset, length)
        except:
            _logger.exception("Could not read data.")
            raise FuseOSError(EIO)

    @dec_hint(['filepath', 'mode'])
    def mkdir(self, filepath, mode):
        """Create the given directory."""

# TODO: Implement the "mode".

        try:
            result = split_path(filepath, path_resolver)
            (parent_clause, path, filename, mime_type, is_hidden) = result
        except GdNotFoundError:
            _logger.exception("Could not process [%s] (mkdir).")
            raise FuseOSError(ENOENT)
        except:
            _logger.exception("Could not split path [%s] (mkdir)." % 
                              (filepath))
            raise FuseOSError(EIO)

        parent_id = parent_clause[CLAUSE_ID]

        try:
            entry = drive_proxy('create_directory', 
                                filename=filename, 
                                parents=[parent_id], 
                                is_hidden=is_hidden)
        except:
            _logger.exception("Could not create directory with name [%s] "
                                 "and parent with ID [%s]." % 
                                 (filename, parent_clause[0].id))
            raise FuseOSError(EIO)

        _logger.info("Directory [%s] created as ID [%s] under parent with "
                        "ID [%s]." % (filepath, entry.id, parent_id))

        #parent_clause[4] = False

        path_relations = PathRelations.get_instance()

        try:
            path_relations.register_entry(entry)
        except:
            _logger.exception("Could not register new directory in cache.")
            raise FuseOSError(EIO)

# TODO: Find a way to implement or enforce 'mode'.
    def __create(self, filepath, mode=None):
        """Create a new file.
                
        We don't implement "mode" (permissions) because the model doesn't agree 
        with GD.
        """
# TODO: Fail if it already exists.

        try:
            result = split_path(filepath, path_resolver)
            (parent_clause, path, filename, mime_type, is_hidden) = result
        except GdNotFoundError:
            _logger.exception("Could not process [%s] (i-create).")
            raise FuseOSError(ENOENT)
        except:
            _logger.exception("Could not split path [%s] (i-create)." % 
                              (filepath))
            raise FuseOSError(EIO)

        distilled_filepath = build_filepath(path, filename)

        # Try to guess at a mime-type, if not otherwise given.
        if mime_type is None:
            (mimetype_guess, _) = guess_type(filename, True)
            
            if mimetype_guess is not None:
                mime_type = mimetype_guess
            else:
                mime_type = Conf.get('default_mimetype')

        try:
            entry = drive_proxy('create_file', filename=filename, 
                                data_filepath='/dev/null', 
                                parents=[parent_clause[3]], 
                                mime_type=mime_type,
                                is_hidden=is_hidden)
        except:
            _logger.exception("Could not create empty file [%s] under "
                                 "parent with ID [%s]." % (filename, 
                                                           parent_clause[3]))
            raise FuseOSError(EIO)

        path_relations = PathRelations.get_instance()

        try:
            path_relations.register_entry(entry)
        except:
            _logger.exception("Could not register created file in cache.")
            raise FuseOSError(EIO)

        _logger.info("Inner-create of [%s] completed." % 
                        (distilled_filepath))

        return (entry, path, filename, mime_type)

    @dec_hint(['filepath', 'mode'])
    def create(self, raw_filepath, mode):
        """Create a new file. This always precedes a write."""

        try:
            fh = OpenedManager.get_instance().get_new_handle()
        except:
            _logger.exception("Could not acquire file-handle for create of "
                                 "[%s]." % (raw_filepath))
            raise FuseOSError(EIO)

        (entry, path, filename, mime_type) = self.__create(raw_filepath)

        try:
            opened_file = OpenedFile(entry.id, path, filename, 
                                     not entry.is_visible, mime_type)
        except:
            _logger.exception("Could not create OpenedFile object for "
                                 "created file.")
            raise FuseOSError(EIO)

        try:
            OpenedManager.get_instance().add(opened_file, fh=fh)
        except:
            _logger.exception("Could not register OpenedFile for created "
                                 "file.")
            raise FuseOSError(EIO)

        return fh

    @dec_hint(['filepath', 'flags'])
    def open(self, filepath, flags):
# TODO: Fail if does not exist and the mode/flags is read only.

        try:
            opened_file = OpenedFile.create_for_requested_filepath(filepath)
        except GdNotFoundError:
            _logger.exception("Could not create handle for requested [%s] "
                                 "(open)." % (filepath))
            raise FuseOSError(ENOENT)
        except:
            _logger.exception("Could not create OpenedFile object for "
                                 "opened filepath [%s]." % (filepath))
            raise FuseOSError(EIO)

        try:
            fh = OpenedManager.get_instance().add(opened_file)
        except:
            _logger.exception("Could not register OpenedFile for opened "
                                 "file.")
            raise FuseOSError(EIO)

        return fh

    @dec_hint(['filepath', 'fh'])
    def release(self, filepath, fh):
        """Close a file."""

        try:
            OpenedManager.get_instance().remove_by_fh(fh)
        except:
            _logger.exception("Could not remove OpenedFile for handle with "
                                 "ID (%d) (release)." % (fh))
            raise FuseOSError(EIO)

    @dec_hint(['filepath', 'data', 'offset', 'fh'], ['data'])
    def write(self, filepath, data, offset, fh):
        try:
            opened_file = OpenedManager.get_instance().get_by_fh(fh=fh)
        except:
            _logger.exception("Could not get OpenedFile (write).")
            raise FuseOSError(EIO)

        try:
            opened_file.add_update(offset, data)
        except:
            _logger.exception("Could not queue file-update.")
            raise FuseOSError(EIO)

        return len(data)

    @dec_hint(['filepath', 'fh'])
    def flush(self, filepath, fh):
        
        try:
            opened_file = OpenedManager.get_instance().get_by_fh(fh=fh)
        except:
            _logger.exception("Could not get OpenedFile (flush).")
            raise FuseOSError(EIO)

        try:
            opened_file.flush()
        except:
            _logger.exception("Could not flush local updates.")
            raise FuseOSError(EIO)

    @dec_hint(['filepath'])
    def rmdir(self, filepath):
        """Remove a directory."""

        path_relations = PathRelations.get_instance()

        try:
            entry_clause = path_relations.get_clause_from_path(filepath)
        except GdNotFoundError:
            _logger.exception("Could not process [%s] (rmdir).")
            raise FuseOSError(ENOENT)
        except:
            _logger.exception("Could not get clause from file-path [%s] "
                              "(rmdir)." % (filepath))
            raise FuseOSError(EIO)

        if not entry_clause:
            _logger.error("Path [%s] does not exist for rmdir()." % (filepath))
            raise FuseOSError(ENOENT)

        entry_id = entry_clause[CLAUSE_ID]
        normalized_entry = entry_clause[CLAUSE_ENTRY]

        # Check if not a directory.

        if not normalized_entry.is_directory:
            _logger.error("Can not rmdir() non-directory [%s] with ID [%s].", filepath, entry_id)
            raise FuseOSError(ENOTDIR)

        # Ensure the folder is empty.

        try:
            found = drive_proxy('get_children_under_parent_id', 
                                parent_id=entry_id,
                                max_results=1)
        except:
            _logger.exception("Could not determine if directory to be removed "
                              "has children." % (entry_id))
            raise FuseOSError(EIO)

        if found:
            raise FuseOSError(ENOTEMPTY)

        try:
            drive_proxy('remove_entry', normalized_entry=normalized_entry)
        except (NameError):
            raise FuseOSError(ENOENT)
        except:
            _logger.exception("Could not remove directory [%s] with ID [%s]." % 
                              (filepath, entry_id))
            raise FuseOSError(EIO)
# TODO: Remove from cache.

    # Not supported. Google Drive doesn't fit within this model.
    @dec_hint(['filepath', 'mode'])
    def chmod(self, filepath, mode):
        # Return successfully, or rsync might have a problem.
#        raise FuseOSError(EPERM) # Operation not permitted.
        pass

    # Not supported. Google Drive doesn't fit within this model.
    @dec_hint(['filepath', 'uid', 'gid'])
    def chown(self, filepath, uid, gid):
        # Return successfully, or rsync might have a problem.
#        raise FuseOSError(EPERM) # Operation not permitted.
        pass

    # Not supported.
    @dec_hint(['target', 'source'])
    def symlink(self, target, source):

        raise FuseOSError(EPERM)

    # Not supported.
    @dec_hint(['filepath'])
    def readlink(self, filepath):

        raise FuseOSError(EPERM)

    @dec_hint(['filepath'])
    def statfs(self, filepath):
        """Return filesystem status info (for df).

        The given file-path seems to always be '/'.

        REF: http://www.ibm.com/developerworks/linux/library/l-fuse/
        REF: http://stackoverflow.com/questions/4965355/converting-statvfs-to-percentage-free-correctly
        """

        block_size = 512

        try:
            account_info = AccountInfo.get_instance()
            total = account_info.quota_bytes_total / block_size
            used = account_info.quota_bytes_used / block_size
            free = total - used
        except:
            _logger.exception("Could not get account-info.")
            raise FuseOSError(EIO)

        return {
            # Optimal transfer block size.
            'f_bsize': block_size,

            # Total data blocks in file system.
            'f_blocks': total,

            # Fragment size.
            'f_frsize': block_size,

            # Free blocks in filesystem.
            'f_bfree': free,

            # Free blocks avail to non-superuser.
            'f_bavail': free

            # Total file nodes in filesystem.
#            'f_files': 0,

            # Free file nodes in filesystem.
#            'f_ffree': 0,

            # Free inodes for unprivileged users.
#            'f_favail': 0
        }

    @dec_hint(['filepath_old', 'filepath_new'])
    def rename(self, filepath_old, filepath_new):
        # Make sure the old filepath exists.
        (entry, path, filename_old) = get_entry_or_raise(filepath_old)

        # At this point, decorations, the is-hidden prefix, etc.. haven't been
        # stripped.
        (path, filename_new_raw) = split(filepath_new)

        # Make sure the new filepath doesn't exist.

        try:
            get_entry_or_raise(filepath_new, True)
        except GdNotFoundError:
            pass

        try:
            entry = drive_proxy('rename', normalized_entry=entry, 
                                new_filename=filename_new_raw)
        except:
            _logger.exception("Could not update entry [%s] for rename." %
                                 (entry))
            raise FuseOSError(EIO)

        # Update our knowledge of the entry.

        path_relations = PathRelations.get_instance()

        try:
            path_relations.register_entry(entry)
        except:
            _logger.exception("Could not register renamed entry: %s" % 
                                 (entry))
            raise FuseOSError(EIO)

    @dec_hint(['filepath', 'length', 'fh'])
    def truncate(self, filepath, length, fh=None):
        if fh is not None:
            try:
                opened_file = OpenedManager.get_instance().get_by_fh(fh)
            except:
                _logger.exception("Could not retrieve OpenedFile for handle "
                                     "with ID (%d) (truncate)." % (fh))
                raise FuseOSError(EIO)

            opened_file.reset_state()

            entry_id = opened_file.entry_id
            cache = EntryCache.get_instance().cache

            try:
                entry = cache.get(entry_id)
            except:
                _logger.exception("Could not fetch normalized entry with "
                                     "ID [%s] for truncate with FH." % 
                                     (entry_id))
                raise
        else:
            (entry, path, filename) = get_entry_or_raise(filepath)

        try:
            entry = drive_proxy('truncate', normalized_entry=entry)
        except:
            _logger.exception("Could not truncate entry [%s]." % (entry))
            raise FuseOSError(EIO)

        # We don't need to update our internal representation of the file (just 
        # our file-handle and its related buffering).

    @dec_hint(['file_path'])
    def unlink(self, file_path):
        """Remove a file."""
# TODO: Change to simply move to "trash". Have a FUSE option to elect this
# behavior.
        path_relations = PathRelations.get_instance()

        try:
            entry_clause = path_relations.get_clause_from_path(file_path)
        except GdNotFoundError:
            _logger.exception("Could not process [%s] (unlink).")
            raise FuseOSError(ENOENT)
        except:
            _logger.exception("Could not get clause from file-path [%s] "
                                 "(unlink)." % (file_path))
            raise FuseOSError(EIO)

        if not entry_clause:
            _logger.error("Path [%s] does not exist for unlink()." % 
                             (file_path))
            raise FuseOSError(ENOENT)

        entry_id = entry_clause[CLAUSE_ID]
        normalized_entry = entry_clause[CLAUSE_ENTRY]

        # Check if a directory.

        if normalized_entry.is_directory:
            _logger.error("Can not unlink() directory [%s] with ID [%s]. "
                             "Must be file.", file_path, entry_id)
            raise FuseOSError(errno.EISDIR)

        # Remove online. Complements local removal (if not found locally, a 
        # follow-up request checks online).

        try:
            drive_proxy('remove_entry', normalized_entry=normalized_entry)
        except (NameError):
            raise FuseOSError(ENOENT)
        except:
            _logger.exception("Could not remove file [%s] with ID [%s]." % 
                                 (file_path, entry_id))
            raise FuseOSError(EIO)

        # Remove from cache. Will no longer be able to be found, locally.

        try:
            PathRelations.get_instance().remove_entry_all(entry_id)
        except:
            _logger.exception("There was a problem removing entry [%s] "
                                 "from the caches." % (normalized_entry))
            raise

        # Remove from among opened-files.

        try:
            opened_file = OpenedManager.get_instance().\
                            remove_by_filepath(file_path)
        except:
            _logger.exception("There was an error while removing all "
                                 "opened-file instances for file [%s] "
                                 "(remove)." % (file_path))
            raise FuseOSError(EIO)

    @dec_hint(['raw_path', 'times'])
    def utimens(self, raw_path, times=None):
        """Set the file times."""

        if times is not None:
            (atime, mtime) = times
        else:
            now = time()
            (atime, mtime) = (now, now)

        (entry, path, filename) = get_entry_or_raise(raw_path)

        mtime_phrase = get_flat_normal_fs_time_from_epoch(mtime)
        atime_phrase = get_flat_normal_fs_time_from_epoch(atime)

        try:
            entry = drive_proxy('update_entry', normalized_entry=entry, 
                                modified_datetime=mtime_phrase,
                                accessed_datetime=atime_phrase)
        except:
            _logger.exception("Could not update entry [%s] for times." %
                                 (entry))
            raise FuseOSError(EIO)

        return 0

    @dec_hint(['path'])
    def init(self, path):
        """Called on filesystem mount. Path is always /."""

        get_change_manager().mount_init()

    @dec_hint(['path'])
    def destroy(self, path):
        """Called on filesystem destruction. Path is always /."""

        get_change_manager().mount_destroy()

    @dec_hint(['path'])
    def listxattr(self, raw_path):
        (entry, path, filename) = get_entry_or_raise(raw_path)

        return entry.xattr_data.keys()

    @dec_hint(['path', 'name', 'position'])
    def getxattr(self, raw_path, name, position=0):
        (entry, path, filename) = get_entry_or_raise(raw_path)

        try:
            return entry.xattr_data[name] + "\n"
        except:
            return ''
        
def load_mount_parser_args(parser):
    parser.add_argument('auth_storage_file', help='Authorization storage file')
    parser.add_argument('mountpoint', help='Mount point')
    parser.add_argument('-d', '--debug', help='Debug mode',
                        action='store_true', required=False)
    parser.add_argument('-o', '--opt', help='Mount options',
                        action='store', required=False,
                        nargs=1)

def mount(auth_storage_filepath, mountpoint, debug=None, nothreads=None, 
          option_string=None):

    logging.debug("Debug: %s" % (debug))

    fuse_opts = { }
    if option_string:
        for opt_parts in [opt.split('=', 1) \
                          for opt \
                          in option_string.split(',') ]:
            k = opt_parts[0]

            # We need to present a bool type for on/off flags. Since all we
            # have are strings, we'll convert anything with a 'True' or 'False'
            # to a bool, or anything with just a key to True.
            if len(opt_parts) == 2:
                v = opt_parts[1]
                v_lower = v.lower()

                if v_lower == 'true':
                    v = True
                elif v_lower == 'false':
                    v = False
            else:
                v = True

            # We have a list of provided options. See which match against our 
            # application options.

            logging.info("Setting option [%s] to [%s]." % (k, v))

            try:
                Conf.set(k, v)
            except (KeyError) as e:
                logging.debug("Forwarding option [%s] with value [%s] to "
                              "FUSE." % (k, v))

                fuse_opts[k] = v
            except:
                logging.exception("Could not set option [%s]. It is probably "
                                  "invalid." % (k))
                raise

    logging.debug("PERMS: F=%s E=%s NE=%s" % 
                  (Conf.get('default_perm_folder'), 
                   Conf.get('default_perm_file_editable'), 
                   Conf.get('default_perm_file_noneditable')))

    # Assume that any option that wasn't an application option is a FUSE 
    # option. The Python-FUSE interface that we're using is beautiful/elegant,
    # but there's no help support. The user is just going to have to know the
    # options.

    set_auth_cache_filepath(auth_storage_filepath)

    # How we'll appear in diskfree, mtab, etc..
    name = ("gdfs(%s)" % (auth_storage_filepath))

    # Don't start any of the scheduled tasks, such as change checking, cache
    # cleaning, etc. It will minimize outside influence of the logs and state
    # to make it easier to debug.

#    atexit.register(Timers.get_instance().cancel_all)
    if debug:
        Timers.get_instance().set_autostart_default(False)

    fuse = FUSE(GDriveFS(), mountpoint, debug=debug, foreground=debug, 
                nothreads=nothreads, fsname=name, **fuse_opts)

def set_auth_cache_filepath(auth_storage_filepath):
    auth_storage_filepath = os.path.abspath(auth_storage_filepath)

    Conf.set('auth_cache_filepath', auth_storage_filepath)


########NEW FILE########
__FILENAME__ = opened_file
import logging
import resource
import re

from errno import *
from threading import Lock, RLock
from collections import deque
from fuse import FuseOSError
from tempfile import NamedTemporaryFile
from os import unlink, utime, makedirs
from os.path import isdir

from gdrivefs.conf import Conf
from gdrivefs.errors import ExportFormatError, GdNotFoundError
from gdrivefs.gdfs.fsutility import dec_hint, split_path, build_filepath
from gdrivefs.gdfs.displaced_file import DisplacedFile
from gdrivefs.cache.volume import PathRelations, EntryCache, path_resolver, \
                                  CLAUSE_ID, CLAUSE_ENTRY
from gdrivefs.gdtool.drive import drive_proxy
from gdrivefs.general.buffer_segments import BufferSegments

_static_log = logging.getLogger().getChild('(OF)')

temp_path = ("%s/local" % (Conf.get('file_download_temp_path')))
if isdir(temp_path) is False:
    makedirs(temp_path)

def get_temp_filepath(normalized_entry, mime_type):
    temp_filename = ("%s.%s" % 
                     (normalized_entry.id, mime_type.replace('/', '+'))).\
                    encode('ascii')

    temp_path = Conf.get('file_download_temp_path')
    return ("%s/local/%s" % (temp_path, temp_filename))



# TODO(dustin): LCM runs in a greenlet pool. When we open a file that needs the
#               existing data for a file (read, append), a switch is done to an
#               LCM worker. If the data is absent or faulted, download the
#               content. Then, switch back.

class LocalCopyManager(object):
    """Manages local copies of files."""
    
#    def 
    pass


class OpenedManager(object):
    """Manages all of the currently-open files."""

    __instance = None
    __singleton_lock = Lock()
    __opened_lock = RLock()
    __fh_counter = 1

    @staticmethod
    def get_instance():
        with OpenedManager.__singleton_lock:
            if OpenedManager.__instance == None:
                try:
                    OpenedManager.__instance = OpenedManager()
                except:
                    _static_log.exception("Could not create singleton "
                                          "instance of OpenedManager.")
                    raise

            return OpenedManager.__instance

    def __init__(self):
        self.__log = logging.getLogger().getChild('OpenMan')

        self.__opened = {}
        self.__opened_byfile = {}

    def __get_max_handles(self):

        return resource.getrlimit(resource.RLIMIT_NOFILE)[0]

    def get_new_handle(self):
        """Get a handle for a file that's about to be opened. Note that the 
        handles start at (1), so there are a lot of "+ 1" occurrences below.
        """

        max_handles = self.__get_max_handles()

        with OpenedManager.__opened_lock:
            if len(self.__opened) >= (max_handles + 1):
                raise FuseOSError(EMFILE)

            safety_counter = max_handles
            while safety_counter >= 1:
                OpenedManager.__fh_counter += 1

                if OpenedManager.__fh_counter >= (max_handles + 1):
                    OpenedManager.__fh_counter = 1

                if OpenedManager.__fh_counter not in self.__opened:
                    self.__log.debug("Assigning file-handle (%d)." % 
                                     (OpenedManager.__fh_counter))
                    return OpenedManager.__fh_counter
                
        message = "Could not allocate new file handle. Safety breach."

        self.__log.error(message)
        raise Exception(message)

    def add(self, opened_file, fh=None):
        """Registered an OpenedFile object."""

        if opened_file.__class__.__name__ != 'OpenedFile':
            message = "Can only register an OpenedFile as an opened-file."

            self.__log.error(message)
            raise Exception(message)

        with OpenedManager.__opened_lock:
            if not fh:
                try:
                    fh = self.get_new_handle()
                except:
                    self.__log.exception("Could not acquire handle for "
                                      "OpenedFile to be registered.")
                    raise

            elif fh in self.__opened:
                message = ("Opened-file with file-handle (%d) has already been"
                           " registered." % (opened_file.fh))

                self.__log.error(message)
                raise Exception(message)

            self.__opened[fh] = opened_file

            file_path = opened_file.file_path
            if file_path in self.__opened_byfile:
                self.__opened_byfile[file_path].append(fh)
            else:
                self.__opened_byfile[file_path] = [fh]

            return fh

    def remove_by_fh(self, fh):
        """Remove an opened-file, by the handle."""

        with OpenedManager.__opened_lock:
            self.__log.debug("Closing opened-file with handle (%d)." % (fh))

            try:
                self.__opened[fh].cleanup()
            except:
                self.__log.exception("There was an error while cleaning up "
                                     "opened file-path [%s] handle (%d)." % 
                                     (file_path, fh))
                return

            file_path = self.__opened[fh].file_path
            del self.__opened[fh]
            
            try:
                self.__opened_byfile[file_path].remove(fh)
            except ValueError:
                raise ValueError("Could not remove handle (%d) from list of "
                                 "open-handles for file-path [%s]: %s" % 
                                 (fh, file_path, 
                                  self.__opened_byfile[file_path]))

            if not self.__opened_byfile[file_path]:
                del self.__opened_byfile[file_path]

    def remove_by_filepath(self, file_path):

        self.__log.debug("Removing all open handles for file-path [%s]." % 
                         (file_path))

        count = 0

        with OpenedManager.__opened_lock:
            try:
                for fh in self.__opened_byfile[file_path]:
                    self.remove_by_fh(fh)
                    count += 1
            except KeyError:
                pass

        self.__log.debug("(%d) file-handles removed for file-path [%s]." % 
                         (count, file_path))

    def get_by_fh(self, fh):
        """Retrieve an opened-file, by the handle."""

        with OpenedManager.__opened_lock:
            if fh not in self.__opened:
                message = ("Opened-file with file-handle (%d) is not "
                          "registered (get_by_fh)." % (fh))

                self.__log.error(message)
                raise Exception(message)

            return self.__opened[fh]

            
class OpenedFile(object):
    """This class describes a single open file, and manages changes."""

    __update_lock = Lock()
    __download_lock = Lock()

    @staticmethod
    def create_for_requested_filepath(filepath):
        """Process the file/path that was requested (potential export-type 
        directive, dot-prefix, etc..), and build an opened-file object using 
        the information.
        """

        _static_log.debug("Creating OpenedFile for [%s]." % (filepath))

        # Process/distill the requested file-path.

        try:
            result = split_path(filepath, path_resolver)
            (parent_clause, path, filename, mime_type, is_hidden) = result
        except GdNotFoundError:
            _static_log.exception("Could not process [%s] "
                                  "(create_for_requested)." % (filepath))
            raise FuseOSError(ENOENT)
        except:
            _static_log.exception("Could not split path [%s] "
                                  "(create_for_requested)." % (filepath))
            raise

        distilled_filepath = build_filepath(path, filename)

        # Look-up the requested entry.

        path_relations = PathRelations.get_instance()

        try:
            entry_clause = path_relations.get_clause_from_path(distilled_filepath)
        except:
            _static_log.exception("Could not try to get clause from path [%s] "
                                  "(OpenedFile)." % (distilled_filepath))
            raise FuseOSError(EIO)

        if not entry_clause:
            _static_log.debug("Path [%s] does not exist for stat()." % (path))
            raise FuseOSError(ENOENT)

        entry = entry_clause[CLAUSE_ENTRY]

        # Normalize the mime-type by considering what's available for download. 
        # We're going to let the requests that didn't provide a mime-type fail 
        # right here. It will give us the opportunity to try a few options to 
        # get the file.

        try:
            final_mimetype = entry.normalize_download_mimetype(mime_type)
        except ExportFormatError:
            _static_log.exception("There was an export-format error "
                                  "(create_for_requested_filesystem).")
            raise FuseOSError(ENOENT)
        except:
            _static_log.exception("Could not normalize mime-type [%s] for "
                                  "entry [%s]." % (mime_type, entry))
            raise FuseOSError(EIO)

        if final_mimetype != mime_type:
            _static_log.info("Entry being opened will be opened as [%s] "
                             "rather than [%s]." % (final_mimetype, mime_type))

        # Build the object.

        try:
            return OpenedFile(entry_clause[CLAUSE_ID], path, filename, 
                              is_hidden, final_mimetype)
        except:
            _static_log.exception("Could not create OpenedFile for requested "
                                  "file [%s]." % (distilled_filepath))
            raise

    def __init__(self, entry_id, path, filename, is_hidden, mime_type):

        self.__log = logging.getLogger().getChild('OpenFile')

        self.__log.info("Opened-file object created for entry-ID [%s] and "
                        "path (%s)." % (entry_id, path))

        self.__entry_id = entry_id
        self.__path = path
        self.__filename = filename
        self.__is_hidden = is_hidden
        
        self.__mime_type = mime_type
        self.__cache = EntryCache.get_instance().cache

        self.reset_state()

    def reset_state(self):
        self.__buffer = None
        self.__is_loaded = False
        self.__is_dirty = False

    def __repr__(self):
        replacements = {'entry_id': self.__entry_id, 
                        'filename': self.__filename, 
                        'mime_type': self.__mime_type, 
                        'is_loaded': self.__is_loaded, 
                        'is_dirty': self.__is_dirty }

        return ("<OF [%(entry_id)s] F=[%(filename)s] MIME=[%(mime_type)s] "
                "LOADED=[%(is_loaded)s] DIRTY= [%(is_dirty)s]>" % replacements)

# TODO: !! Make sure the "changes" thread is still going, here.

    def cleanup(self):
        """Remove temporary files."""
    
        pass

    def __get_entry_or_raise(self):
        """We can never be sure that the entry will still be known to the 
        system. Grab it and throw an error if it's not available. 
        Simultaneously, this allows us to lazy-load the entry.
        """

        self.__log.debug("Retrieving entry for opened-file with entry-ID "
                         "[%s]." % (self.__entry_id))

        try:
            return self.__cache.get(self.__entry_id)
        except:
            self.__log.exception("Could not retrieve entry with ID [%s] for "
                                 "the opened-file." % (self.__entry_id))
            raise 

    def __load_base_from_remote(self):
        """Download the data for the entry that we represent. This is probably 
        a file, but could also be a stub for -any- entry.
        """

        try:
            entry = self.__get_entry_or_raise()
        except:
            self.__log.exception("Could not get entry with ID [%s] for "
                                 "write-flush." % (self.__entry_id))
            raise

        self.__log.debug("Ensuring local availability of [%s]." % (entry))

        temp_file_path = get_temp_filepath(entry, self.mime_type)

        self.__log.debug("__load_base_from_remote about to download.")

        with self.__class__.__download_lock:
            # Get the current version of the write-cache file, or note that we 
            # don't have it.

            self.__log.info("Attempting local cache update of file [%s] for "
                            "entry [%s] and mime-type [%s]." % 
                            (temp_file_path, entry, self.mime_type))

            if entry.requires_mimetype:
                length = DisplacedFile.file_size

                try:
                    d = DisplacedFile(entry)
                    stub_data = d.deposit_file(self.mime_type)

                    with file(temp_file_path, 'w') as f:
                        f.write(stub_data)
                except:
                    self.__log.exception("Could not deposit to file [%s] from "
                                         "entry [%s]." % (temp_file_path, 
                                                          entry))
                    raise

# TODO: Accommodate the cache for displaced-files.
                cache_fault = True

            else:
                self.__log.info("Executing the download.")
                
                try:
# TODO(dustin): We're not inheriting an existing file (same mtime, same size).
                    result = drive_proxy('download_to_local', 
                                         output_file_path=temp_file_path,
                                         normalized_entry=entry,
                                         mime_type=self.mime_type)

                    (length, cache_fault) = result
                except ExportFormatError:
                    self.__log.exception("There was an export-format error.")
                    raise FuseOSError(ENOENT)
                except:
                    self.__log.exception("Could not localize file with entry "
                                         "[%s]." % (entry))
                    raise

            self.__log.info("Download complete.  cache_fault= [%s] "
                            "__is_loaded= [%s]" % 
                            (cache_fault, self.__is_loaded))

            # We've either not loaded it, yet, or it has changed.
            if cache_fault or not self.__is_loaded:
                with self.__class__.__update_lock:
                    self.__log.info("Checking queued items for fault.")

                    if cache_fault:
                        if self.__is_dirty:
                            self.__log.error("Entry [%s] has been changed. "
                                             "Forcing buffer updates, and "
                                             "clearing uncommitted updates." % 
                                             (entry))
                        else:
                            self.__log.debug("Entry [%s] has changed. "
                                             "Updating buffers." % (entry))

                    self.__log.debug("Loading buffers.")

                    with open(temp_file_path, 'rb') as f:
                        # Read the locally cached file in.

                        try:
# TODO(dustin): This is the source of:
# 1) An enormous slowdown where we first have to write the data, and then have to read it back.
# 2) An enormous resource burden.
                            data = f.read()

                            read_blocksize = Conf.get('default_buffer_read_blocksize')
                            self.__buffer = BufferSegments(data, read_blocksize)
                        except:
                            self.__log.exception("Could not read current cached "
                                                 "file into buffer.")
                            raise

                        self.__is_dirty = False

                    self.__is_loaded = True

        self.__log.debug("__load_base_from_remote complete.")
        return cache_fault

    @dec_hint(['offset', 'data'], ['data'], 'OF')
    def add_update(self, offset, data):
        """Queue an update to this file."""

        self.__log.info("Applying update for offset (%d) and length (%d)." % 
                        (offset, len(data)))

        try:
            self.__load_base_from_remote()
        except:
            self.__log.exception("Could not load entry to local cache [%s]." % 
                                 (self.temp_file_path))
            raise

        self.__log.debug("Base loaded for add_update.")

        with self.__class__.__update_lock:
            self.__buffer.apply_update(offset, data)
            self.__is_dirty = True

    @dec_hint(prefix='OF')
    def flush(self):
        """The OS wants to effect any changes made to the file."""

        self.__log.debug("Retrieving entry for write-flush.")

        entry = self.__get_entry_or_raise()
        cache_fault = self.__load_base_from_remote()
    
        with self.__class__.__update_lock:
            if self.__is_dirty is False:
                self.__log.debug("Flush will be skipped because there are no "
                                 "changes.")
# TODO: Raise an exception?
                return

            # Write back out to the temporary file.

            self.__log.debug("Writing buffer to temporary file.")
# TODO: Make sure to uncache the temp data if self.temp_file_path is not None.

            mime_type = self.mime_type

            # If we've already opened a work file, use it. Else, use a 
            # temporary file that we'll close at the end of the method.
            if self.__is_loaded:
                is_temp = False

                temp_file_path = get_temp_filepath(entry, mime_type)
                                                   
                with file(temp_file_path, 'w') as f:
                    for block in self.__buffer.read():
                        f.write(block)
                                                   
                write_filepath = temp_file_path
            else:
                is_temp = True
            
                with NamedTemporaryFile(delete=False) as f:
                    write_filepath = f.name
                    for block in self.__buffer.read():
                        f.write(block)

            # Push to GD.

            self.__log.debug("Pushing (%d) bytes for entry with ID from [%s] "
                             "to GD for file-path [%s]." % 
                             (self.__buffer.length, entry.id, write_filepath))

#            print("Sending updates.")

# TODO: Update mtime?
            try:
                entry = drive_proxy('update_entry', 
                                    normalized_entry=entry, 
                                    filename=entry.title, 
                                    data_filepath=write_filepath, 
                                    mime_type=mime_type, 
                                    parents=entry.parents, 
                                    is_hidden=self.__is_hidden)
            except:
                self.__log.exception("Could not localize displaced file with "
                                     "entry having ID [%s]." % (entry.id))
                raise

            if not is_temp:
                unlink(write_filepath)
            else:
                # Update the write-cache file to the official mtime. We won't 
                # redownload it on the next flush if it wasn't changed, 
                # elsewhere.

                self.__log.debug("Updating local write-cache file to official "
                                 "mtime [%s]." % (entry.modified_date_epoch))

                try:
                    utime(write_filepath, (entry.modified_date_epoch, 
                                            entry.modified_date_epoch))
                except:
                    self.__log.exception("Could not update mtime of write-"
                                         "cache [%s] for entry with ID [%s], "
                                         "post-flush." % 
                                         (entry.modified_date_epoch, entry.id))
                    raise

        # Immediately update our current cached entry.

        self.__log.debug("Update successful. Updating local cache.")

        path_relations = PathRelations.get_instance()

        try:
            path_relations.register_entry(entry)
        except:
            self.__log.exception("Could not register updated file in cache.")
            raise

        self.__is_dirty = False

        self.__log.info("Update complete on entry with ID [%s]." % (entry.id))

    @dec_hint(['offset', 'length'], prefix='OF')
    def read(self, offset, length):
        
        self.__log.debug("Checking write-cache file (flush).")

        try:
            self.__load_base_from_remote()
        except:
            self.__log.exception("Could not load write-cache file.")
            raise

# TODO: Refactor this into a paging mechanism.

        buffer_len = self.__buffer.length

        # Some files may have a length of (0) untill a particular type is 
        # chosen (the download-links).
        if buffer_len > 0:
            if offset >= buffer_len:
                raise IndexError("Offset (%d) exceeds length of data (%d)." % 
                                 (offset, buffer_len))

            if (offset + length) > buffer_len:
                self.__log.debug("Requested length (%d) from offset (%d) "
                                 "exceeds file length (%d). Truncated." % 
                                 (length, offset, buffer_len)) 
                length = buffer_len

        data_blocks = [block for block in self.__buffer.read(offset, length)]
        data = ''.join(data_blocks)

        self.__log.debug("(%d) bytes retrieved from slice (%d):(%d)/(%d)." % 
                         (len(data), offset, length, self.__buffer.length))

        return data

    @property
    def mime_type(self):
        return self.__mime_type

    @property
    def entry_id(self):
        return self.__entry_id

    @property
    def file_path(self):
        return build_filepath(self.__path, self.__filename)


########NEW FILE########
__FILENAME__ = account_info
import logging

from gdrivefs.general.livereader_base import LiveReaderBase
from gdrivefs.gdtool.drive import drive_proxy


class AccountInfo(LiveReaderBase):
    """Encapsulates our account info."""

    __log = None
    __map = {'root_id': u'rootFolderId',
             'largest_change_id': (u'largestChangeId', int),
             'quota_bytes_total': (u'quotaBytesTotal', int),
             'quota_bytes_used': (u'quotaBytesUsed', int)}

    def __init__(self):
        LiveReaderBase.__init__(self)

        self.__log = logging.getLogger().getChild('AccountInfo')

    def get_data(self, key):
        try:
            return drive_proxy('get_about_info')
        except:
            self.__log.exception("get_about_info() call failed.")
            raise

    def __getattr__(self, key):
        target = AccountInfo.__map[key]
        _type = None
        
        if target.__class__ == tuple:
            (target, _type) = target

        value = self[target]
        if _type is not None:
            value = _type(value)

        return value

    @property
    def keys(self):
        return AccountInfo.__map.keys()


########NEW FILE########
__FILENAME__ = chunked_download
import logging

from time import time, sleep
from random import random

from oauth2client import util
from apiclient.http import MediaDownloadProgress
from apiclient.errors import HttpError

DEFAULT_CHUNK_SIZE = 1024 * 512

_logger = logging.getLogger(__name__)


class ChunkedDownload(object):
  """"Download an entry, chunk by chunk. This code is mostly identical to
  MediaIoBaseDownload, which couldn't be used because we have a specific URL
  that needs to be downloaded (not a request object, which doesn't apply here).
  """

  @util.positional(4)
  def __init__(self, fd, http, uri, chunksize=DEFAULT_CHUNK_SIZE, start_at=0):
    """Constructor.

    Args:
      fd: io.Base or file object, The stream in which to write the downloaded
        bytes.
      http: The httplib2 resource.
      uri: The URL to be downloaded.
      chunksize: int, File will be downloaded in chunks of this many bytes.
    """
    self._fd = fd
    self._http = http
    self._uri = uri
    self._chunksize = chunksize
    self._progress = start_at
    self._total_size = None
    self._done = False

    # Stubs for testing.
    self._sleep = sleep
    self._rand = random

  @util.positional(1)
  def next_chunk(self, num_retries=0):
    """Get the next chunk of the download.

    Args:
      num_retries: Integer, number of times to retry 500's with randomized
            exponential backoff. If all retries fail, the raised HttpError
            represents the last request. If zero (default), we attempt the
            request only once.

    Returns:
      (status, done): (MediaDownloadStatus, boolean)
         The value of 'done' will be True when the media has been fully
         downloaded.

    Raises:
      apiclient.errors.HttpError if the response was not a 2xx.
      httplib2.HttpLib2Error if a transport error has occured.
    """

    headers = {
        'range': 'bytes=%d-%d' % (
            self._progress, self._progress + self._chunksize)
        }

    for retry_num in xrange(num_retries + 1):
        if retry_num > 0:
            self._sleep(self._rand() * 2**retry_num)
            logging.warning(
                'Retry #%d for media download: GET %s, following status: %d' %
                (retry_num, self._uri, resp.status))

        resp, content = self._http.request(self._uri, headers=headers)
        if resp.status < 500:
            break

    if resp.status not in (200, 206):
        raise HttpError(resp, content, uri=self._uri)

    if 'content-location' in resp and resp['content-location'] != self._uri:
        self._uri = resp['content-location']

    self._progress += len(content)
    self._fd.write(content)

    if 'content-length' in resp:
        self._total_size = int(resp['content-length'])
    elif 'content-range' in resp:
        content_range = resp['content-range']
        length = content_range.rsplit('/', 1)[1]
        self._total_size = int(length)

    if self._progress == self._total_size:
        self._done = True

    return (MediaDownloadProgress(self._progress, self._total_size), 
            self._done,
            self._total_size)


########NEW FILE########
__FILENAME__ = download_agent
"""This file describes the communication interface to the download-worker, and
the download-worker itself. Both are singleton classes.
"""

import multiprocessing
import logging
import Queue
import time
import threading
import collections
import os
import os.path
import datetime
import glob
import contextlib
import dateutil.tz

import gevent
import gevent.lock
import gevent.pool
import gevent.monkey
import gevent.queue

from gdrivefs.config import download_agent
from gdrivefs.utility import utility
from gdrivefs.gdtool.chunked_download import ChunkedDownload
from gdrivefs.gdtool.drive import GdriveAuth

_RT_PROGRESS = 'p'
_RT_ERROR = 'e'
_RT_DONE = 'd'
_RT_THREAD_KILL = 'k'
_RT_THREAD_STOP = 's'

DownloadRegistration = collections.namedtuple(
                        'DownloadRegistration', 
                        ['typed_entry', 
                         'url', 
                         'bytes', 
                         'expected_mtime_tuple'])

DownloadRequest = collections.namedtuple(
                        'DownloadRequest', 
                        ['typed_entry', 'url', 'bytes', 'expected_mtime_dt'])


class DownloadAgentDownloadException(Exception):
    """Base exception for all user-defined functions."""

    pass


class DownloadAgentDownloadError(DownloadAgentDownloadException):
    """Base error for download errors."""

    pass


class DownloadAgentDownloadAgentError(DownloadAgentDownloadError):
    """Raised to external callers when a sync failed."""

    pass


class DownloadAgentWorkerShutdownException(DownloadAgentDownloadException):
    """Raised by download worker when it's told to shutdown."""

    pass


class DownloadAgentResourceFaultedException(DownloadAgentDownloadException):
    """Raised externally by _SyncedResourceHandle when the represented file 
    has faulted.
    """

    pass


class DownloadAgentDownloadStopException(DownloadAgentDownloadException):
    """Raised to external callers when the file being actively downloaded has 
    faulted, and must be restarted.
    """

    pass


class _DownloadedFileState(object):
    """This class is in charge of knowing where to store downloaded files, and
    how to check validness.
    """

    def __init__(self, download_reg):
        self.__typed_entry = download_reg.typed_entry
        self.__log = logging.getLogger('%s(%s)' % 
                        (self.__class__.__name__, self.__typed_entry))

        self.__file_marker_locker = threading.Lock()
        self.__file_path = self.get_stored_filepath()
        self.__stamp_file_path = self.__get_downloading_stamp_filepath()

        # The mtime should've already been adjusted to the local TZ.

        self.__expected_mtime_epoch = time.mktime(
                                        download_reg.expected_mtime_tuple)
        self.__expected_mtime_dt = datetime.datetime.fromtimestamp(
                                    self.__expected_mtime_epoch).\
                                    replace(tzinfo=dateutil.tz.tzlocal())

    def __str__(self):
        return ('<DOWN-FILE-STATE %s>' % (self.__typed_entry,))

    def is_up_to_date(self, bytes_=None):
        with self.__file_marker_locker:
            self.__log.debug('is_up_to_date()')

            # If the requested file doesn't exist, at all, we're out of luck.
            if os.path.exists(self.__file_path) is False:
                return False

            # If the mtime of the requested file matches, we have the whole
            # thing (the mtime can only be set after the file has been 
            # completely written).

            main_stat = os.stat(self.__file_path)
            mtime_dt = datetime.datetime.fromtimestamp(main_stat.st_mtime)

            if mtime_dt == self.__expected_mtime_dt:
                return True

            if mtime_dt > self.__expected_mtime_dt:
                logging.warn("The modified-time [%s] of the locally "
                             "available file is greater than the "
                             "requested file [%s].",
                             mtime_dt, self.__expected_mtime_dt)

            # If they want the whole file (not just a specific number of 
            # bytes), then we definitely don't have it.
            if bytes_ is None:
                return False

            # The file is not up to date, but check if we're, downloading it, 
            # at least.

            if os.path.exists(self.__stamp_file_path) is False:
                return False

            # Determine if we're downloading (or recently attempted to 
            # download) the same version that was requested.

            stamp_stat = os.stat(self.__stamp_file_path)
            stamp_mtime_dt = datetime.datetime.fromtimestamp(
                                stamp_stat.st_mtime)

            if stamp_mtime_dt != self.__expected_mtime_dt:
                if stamp_mtime_dt > self.__expected_mtime_dt:
                    logging.warn("The modified-time [%s] of the locally "
                                 "available file's STAMP is greater than the "
                                 "requested file [%s].",
                                 stamp_mtime_dt, self.__expected_mtime_dt)
                return False

            # We were/are downloading the right version. Did we download enough 
            # of it?
            if main_stat.st_size < bytes_:
                return False

        # We haven't downloaded the whole file, but we've downloaded enough.
        return True

    def get_partial_offset(self):
        with self.__file_marker_locker:
            self.__log.debug('get_partial_offset()')

            if os.path.exists(self.__file_path) is False:
                return 0

            main_stat = os.stat(self.__file_path)

            # Assume that if the "downloading" stamp isn't present, the file is 
            # completely downloaded.
            if os.path.exists(self.__stamp_file_path) is False:
                return None

            # Determine if we're downloading (or recently attempted to 
            # download) the same version that was requested.

            stamp_stat = os.stat(self.__stamp_file_path)
            stamp_mtime_dt = datetime.datetime.fromtimestamp(
                                stamp_stat.st_mtime)

            if stamp_mtime_dt != self.__expected_mtime_dt:
                return 0

            # If we're in the middle of downloading the right version, return 
            # the current size (being the start offset of a resumed download).
            return main_stat.st_size

    def __get_stored_filename(self):
        filename = ('%s:%s' % (
                    utility.make_safe_for_filename(
                        self.__typed_entry.entry_id), 
                    utility.make_safe_for_filename(
                        self.__typed_entry.mime_type.lower())))

        return filename

    def get_stored_filepath(self):
        filename = self.__get_stored_filename()
        return os.path.join(download_agent.DOWNLOAD_PATH, filename)

    def __get_downloading_stamp_filename(self):
        filename = self.__get_stored_filename()
        stamp_filename = ('.%s.%s' % 
                          (filename, 
                           download_agent.FILE_STATE_STAMP_SUFFIX_DOWNLOADING))

        return stamp_filename

    def __get_downloading_stamp_filepath(self):
        stamp_filename = self.__get_downloading_stamp_filename()
        return os.path.join(download_agent.DOWNLOAD_PATH, stamp_filename)

    def stage_download(self):
        """Called before a download has started."""
    
        # Initialize our start state. This ensures that any concurrent
        # requests can read partial data without having to wait for the
        # whole download.
        with self.__file_marker_locker:
            self.__log.debug('stage_download()')

            try:
                stamp_stat = os.stat(self.__stamp_file_path)
            except OSError:
                existing_mtime_epoch = None
            else:
                existing_mtime_epoch = stamp_stat.st_mtime

            # THEN create a stamp file...
            with open(self.__stamp_file_path, 'w'):
                pass

            # ...and set its mtime.
            os.utime(self.__stamp_file_path, 
                     (self.__expected_mtime_epoch,) * 2)

            # If we either didn't have a stamp file or or we did and the mtime 
            # doesn't match, create an empty download file or truncate the 
            # existing.
            if self.__expected_mtime_epoch != existing_mtime_epoch:
                with open(self.__file_path, 'w'):
                    pass

    def finish_download(self):
        """Called after a download has completed."""

        with self.__file_marker_locker:
            self.__log.debug('finish_download()')

            os.utime(self.__file_path, (self.__expected_mtime_epoch,) * 2) 
            os.unlink(self.__stamp_file_path)

    @property
    def file_path(self):
        return self.__file_path


class _DownloadAgent(object):
    """Exclusively manages downloading files from Drive within another process.
    This is a singleton class (and there's only one worker process).
    """

    def __init__(self, request_q, stop_ev):
        # This patches the socket library. Only the agent needs gevent and it 
        # might interrupt multiprocessing if we put it as the top of the 
        # module.

# TODO(dustin): Using gevent in the worker is interrupting the worker's ability 
#               to communicate with the main process. Try to send a standard 
#               Python Unix pipe to the process while still using 
#               multiprocessing to manage it. 

#        gevent.monkey.patch_socket()
#        from gdrivefs.http_pool import HttpPool

        self.__log = logging.getLogger(self.__class__.__name__)
        self.__request_q = request_q
        self.__stop_ev = stop_ev
        self.__kill_ev = gevent.event.Event()
        self.__worker_pool = gevent.pool.Pool(size=download_agent.NUM_WORKERS)
#        self.__http_pool = HttpPool(download_agent.HTTP_POOL_SIZE)
#        self.__http = GdriveAuth().get_authed_http()

        # This allows multiple green threads to communicate over the same IPC 
        # resources.
        self.__ipc_sem = gevent.lock.Semaphore()

        self.__ops = {}

    def download_worker(self, download_reg, download_id, sender, receiver):
        self.__log.info("Worker thread downloading: %s" % (download_reg,))

# TODO(dustin): We're just assuming that we can signal a multiprocessing event
#               from a green thread (the event still has value switching 
#               through green threads.

# TODO(dustin): Support reauthing, when necessary.

        # This will allow us to determine how up to date we are, as well as to
        # to resume an existing, partial download (if possible).
        dfs = _DownloadedFileState(download_reg)

        if dfs.is_up_to_date() is False:
            self.__log.info("File is not up-to-date: %s" % (str(dfs)))

            dfs.stage_download()

            with open(dfs.file_path, 'wb') as f:
                try:
                    downloader = ChunkedDownload(
                        f, 
                        self.__http, 
                        download_reg.url, 
                        chunksize=download_agent.CHUNK_SIZE,
                        start_at=dfs.get_partial_offset())

                    self.__log.info("Beginning download loop: %s" % (str(dfs)))

                    while 1:
                        try:
                            (report_type, datum) = receiver.get(False)
                        except Queue.Empty:
                            pass
                        else:
                            self.__log.debug("Worker thread [%s] received "
                                             "report: [%s]" % 
                                             (download_reg, report_type))

                            if report_type == _RT_THREAD_KILL:
                                # Stop downloading if the process is coming 
                                # down.
                                self.__log.info("Download loop has been "
                                                "terminated because we're "
                                                "shutting down.")
                                raise DownloadAgentWorkerShutdownException(
                                    "Download worker terminated.")
                            elif report_type == _RT_THREAD_STOP:
                                # Stop downloading this file, prhaps if all handles 
                                # were closed and the file is no longer needed.
                                self.__log.info("Download loop has been "
                                                "terminated because we were"
                                                "told to stop (the agent is"
                                                "still running, though).")
                                raise DownloadAgentDownloadStopException(
                                    "Download worker was told to stop "
                                    "downloading.")
                            else:
                                raise ValueError("Worker thread does not "
                                                 "understand report-type: %s" % 
                                                 (report_type))

                        status, done = downloader.next_chunk()

                        sender.put(download_id, 
                                   _RT_PROGRESS, 
                                   status.resumable_progress)

                        if done is True:
                            break

                    self.__log.info("Download finishing: %s" % (str(dfs)))

                    dfs.finish_download()
                except DownloadAgentDownloadException as e:
                    self.__log.exception("Download exception.")

                    sender.put(download_id, 
                               _RT_ERROR, 
                               (e.__class__.__name__, str(e)))
        else:
            self.__log.info("Local copy is already up-to-date: %s" % 
                            (download_reg))

        sender.put(download_id, 
                   _RT_DONE, 
                   ())

    def loop(self):
        global_receiver = gevent.queue.Queue()
        while True:
            if self.__stop_ev.is_set() is True:
                self.__log.debug("Download-agent stop-flag has been set.")
                break
            
            # Check if we've received a message from a worker thread.
            
            try:
                (id_, report_type, datum) = global_receiver.get(False)
            except Queue.Empty:
                pass
            else:
                # We have. Translate it to a message back to the request
                # interface.

                dr = self.__ops[id_][0]

                self.__log.debug("Worker received report [%s] from thread: "
                                 "%s" % (report_type, dr))

                if report_type == _RT_PROGRESS:
                    (bytes,) = datum
                    ns = dr[3]
                    ns.bytes_written = bytes
                elif report_type == _RT_ERROR:
                    (err_type, err_msg) = datum
                    ns = dr[3]
                    ns.error = (err_type, err_msg)
                elif report_type == _RT_DONE:
                    finish_ev = dr[1]
                    finish_ev.set()
                else:
                    raise ValueError("Worker process does not "
                                     "understand report-type: %s" % 
                                     (report_type))

            # Check for a kill event to be broadcast.
            if self.__kill_ev.set() is True:
                for id_, op in self.__ops.items():
                    op[1].put((_RT_THREAD_KILL, ()))

            # Check for a stop event on specific downloads.
            for id_, op in self.__ops.items():
                download_stop_ev = op[0][2]
                if download_stop_ev.is_set() is True:
                    op[1].put((_RT_THREAD_STOP, ()))

            try:
                request_info = self.__request_q.get(
                    timeout=download_agent.REQUEST_QUEUE_TIMEOUT_S)
            except Queue.Empty:
                self.__log.debug("Didn't find any new download requests.")
                continue

            sender = gevent.queue.Queue()
            id_ = len(self.__ops)
            self.__ops[id_] = (request_info, sender)

#            if self.__worker_pool.free_count() == 0:
#                self.__log.warn("It looks like we'll have to wait for a "
#                                "download worker to free up.")

            self.__log.debug("Spawning download worker.")


#            self.__worker_pool.spawn(self.download_worker, 
#                                     request_info[0],
#                                     id_, 
#                                     global_receiver,
#                                     sender)

            self.__log.info("DEBUG!")

        # The download loop has exited (we were told to stop). Signal the 
        # workers to stop what they're doing.

# TODO(dustin): For some reason, this isn't making it into the log (the above 
#               it, though). Tried flushing, but didn't work.
        self.__log.info("Download agent is shutting down.")

        self.__kill_ev.set()

#        start_epoch = time.time()
#        all_exited = False
#        while (time.time() - start_epoch) < \
#                download_agent.GRACEFUL_WORKER_EXIT_WAIT_S:
#            if self.__worker_pool.size <= self.__worker_pool.free_count():
#                all_exited = True
#                break
#
#        if all_exited is False:
#            self.__.error("Not all download workers exited in time: %d != %d",
#                          self.__worker_pool.size,
#                          self.__worker_pool.free_count())

        # Kill and join the unassigned (and stubborn, still-assigned) workers.
# TODO(dustin): We're assuming this is a hard kill that will always kill all 
#               workers.
#        self.__worker_pool.kill()

        self.__log.info("Download agent is terminating. (%d) requested files "
                        "will be abandoned.", self.__request_q.qsize())

def _agent_boot(request_q, stop_ev):
    """Boots the agent once it's given its own process."""

    logging.info("Starting download agent.")

    agent = _DownloadAgent(request_q, stop_ev)
    agent.loop()

    logging.info("Download agent loop has ended.")


class _SyncedResource(object):
    """This is the singleton object stored within the external agent that is
    flagged if/when a file is faulted."""

    def __init__(self, external_download_agent, entry_id, mtime_dt, 
                 resource_key):
        self.__eda = external_download_agent
        self.__entry_id = entry_id
        self.__mtime_dt = mtime_dt
        self.__key = resource_key
        self.__handles = []

    def __str__(self):
        return ('<RES %s %s>' % (self.__entry_id, self.__mtime_dt))

    def register_handle(self, handle):
        """Indicate that one handle is ready to go."""

        self.__handles.append(handle)

    def decr_ref_count(self):
        """Indicate that one handle has been destroyed."""

        self.__eda.deregister_resource(self)

    def set_faulted(self):
        """Tell each of our handles that they're no longer looking at an 
        accurate/valid copy of the file.
        """

        for handle in self.__handles:
            handle.set_faulted()

    @property
    def entry_id(self):
        return self.__entry_id

    @property
    def key(self):
        return self.__key

def _check_resource_state(method):
    def wrap(self, *args, **kwargs):
        if self.is_faulted is True:
            raise DownloadAgentResourceFaultedException()

        return method(self, *args, **kwargs)
    
    return wrap
    

class _SyncedResourceHandle(object):
    """This object:
    
    - represents access to a synchronized file
    - will raise a DownloadAgentResourceFaultedException if the file has been 
      changed.
    - is the internal resource that will be associated with a physical file-
      handle.
    """

    def __init__(self, resource, dfs):
        self.__resource = resource
        self.__dfs = dfs
        self.__is_faulted = False
        self.__f = open(self.__dfs.get_stored_filepath(), 'rb')      

        # Start off opened.
        self.__open = True

        # We've finished initializing. Register ourselves as a handle on the 
        # resource.        
        self.__resource.register_handle(self)

    def set_faulted(self):
        """Indicate that another sync operation will have to occur in order to
        continue reading."""

        self.__is_faulted = True

    def __del__(self):
        if self.__open is True:
            self.close()

    def __enter__(self):
        return self

    def __exit__(self, type_, value, traceback):
        self.close()

    def close(self):
        self.__resource.decr_ref_count()
        self.__f.close()
        self.__open = False

    @_check_resource_state
    def __getattr__(self, name):
        return getattr(self.__f, name)

    @property
    def is_faulted(self):
        return self.__is_faulted


class _DownloadAgentExternal(object):
    """A class that runs in the same process as the rest of the application, 
    and acts as an interface to the worker process. This is a singleton.
    """

    def __init__(self):
        self.__log = logging.getLogger(self.__class__.__name__)
        self.__p = None
        self.__m = multiprocessing.Manager()

#        self.__abc = self.__m.Event()

        self.__request_q = multiprocessing.Queue()
        self.__request_loop_ev = multiprocessing.Event()
        
        self.__request_registry_context = { }
        self.__request_registry_types = { }
        self.__request_registry_locker = threading.Lock()

        # [entry_id] = [resource, counter]
        self.__accessor_resources = {}
        self.__accessor_resources_locker = threading.Lock()

        if os.path.exists(download_agent.DOWNLOAD_PATH) is False:
            os.makedirs(download_agent.DOWNLOAD_PATH)

    def deregister_resource(self, resource):
        """Called at the end of a file-resource's lifetime (on close)."""

        with self.__accessor_resources_locker:
            self.__accessor_resources[resource.key][1] -= 1
            
            if self.__accessor_resources[resource.key][1] <= 0:
                self.__log.debug("Resource is now being GC'd: %s", 
                                 str(resource))
                del self.__accessor_resources[resource.key]

    def __get_resource(self, entry_id, expected_mtime_dt):
        """Get the file resource and increment the reference count. Note that
        the resources are keyed by entry-ID -and- mtime, so the moment that
        an entry is faulted, we can fault the resource for all of the current
        handles while dispensing new handles with an entirely-new resource.
        """

        key = ('%s-%s' % (entry_id, 
                          time.mktime(expected_mtime_dt.timetuple())))

        with self.__accessor_resources_locker:
            try:
                self.__accessor_resources[key][1] += 1
                return self.__accessor_resources[key][0]
            except KeyError:
                resource = _SyncedResource(self, 
                                           entry_id, 
                                           expected_mtime_dt, 
                                           key)

                self.__accessor_resources[key] = [resource, 1]
                
                return resource

    def set_resource_faulted(self, entry_id):
        """Called when a file has changed. Will notify any open file-handle 
        that the file has faulted.
        """

        with self.__accessor_resources_locker:
            try:
                self.__accessor_resources[entry_id][0].set_faulted()
            except KeyError:
                pass

    def start(self):
        self.__log.debug("Sending start signal to download agent.")

        if self.__p is not None:
            raise ValueError("The download-worker is already started.")

        args = (self.__request_q, 
                self.__request_loop_ev)

        self.__p = multiprocessing.Process(target=_agent_boot, args=args)
        self.__p.start()

    def stop(self):
        self.__log.debug("Sending stop signal to download agent.")

        if self.__p is None:
            raise ValueError("The download-agent is already stopped.")

        self.__request_loop_ev.set()
        
        start_epoch = time.time()
        is_exited = False
        while (time.time() - start_epoch) <= \
                download_agent.GRACEFUL_WORKER_EXIT_WAIT_S:
            if self.__p.is_alive() is False:
                is_exited = True
                break

        if is_exited is True:
            self.__log.debug("Download agent exited gracefully.")
        else:
            self.__log.error("Download agent did not exit in time (%d).",
                             download_agent.GRACEFUL_WORKER_EXIT_WAIT_S)

            self.__p.terminate()

        self.__p.join()
        
        self.__log.info("Download agent joined with return-code: %d", 
                        self.__p.exitcode)
        
        self.__p = None

# TODO(dustin): We still need to consider removing faulted files (at least if
#               not being actively engaged/watched).

# TODO(dustin): We need to consider periodically pruning unaccessed, localized
#               files.
    def __find_stored_files_for_entry(self, entry_id):
        pattern = ('%s:*' % (utility.make_safe_for_filename(entry_id)))
        full_pattern = os.path.join(download_agent.DOWNLOAD_PATH, pattern)

        return [os.path.basename(file_path) 
                for file_path 
                in glob.glob(full_pattern)]

    @contextlib.contextmanager
    def sync_to_local(self, download_request):
        """Send the download request to the download-agent, and wait for it to
        finish. If the file is already found locally, and the number of request 
        bytes is up to date, a download will not be performed. All requests
        will funnel here, and all requests for the same entry/mime-type 
        combination will essentially be synchronized, while they all are given
        the discretion to render a result (a yield) as soon as the requested
        number of bytes is available.
        
        If/when notify_changed() is called, all open handles to any mime-type 
        of that entry will be faulted, and all downloads will error out in a
        way that can be caught and restarted.
        """

        if download_request.expected_mtime_dt.tzinfo is None:
            raise ValueError("expected_mtime_dt must be timezone-aware.")

        # We keep a registry/index of everything we're downloading so that all
        # subsequent attempts to download the same file will block on the same
        # request.
        #
        # We'll also rely on the separate process to tell us if the file is
        # already local and up-to-date (everything is simpler/cleaner that
        # way), but will also do a ceck, ourselves, once we've submitted an
        # official request for tracking/locking purposes.

        typed_entry = download_request.typed_entry
        expected_mtime_dt = download_request.expected_mtime_dt.astimezone(
                                dateutil.tz.tzlocal())
        bytes_ = download_request.bytes

        download_reg = DownloadRegistration(typed_entry=typed_entry,
                                            expected_mtime_tuple=\
                                                expected_mtime_dt.timetuple(),
                                            url=download_request.url,
                                            bytes=bytes_)

        dfs = _DownloadedFileState(download_reg)

        with self.__request_registry_locker:
            try:
                context = self.__request_registry_context[typed_entry]
            except KeyError:
                # This is the first download of this entry/mime-type.

                self.__log.info("Initiating a new download: %s", download_reg)

# TODO(dustin): We might need to send a semaphore in order to control access.
                finish_ev = self.__m.Event()
                download_stop_ev = self.__m.Event()
                ns = self.__m.Namespace()
                ns.bytes_written = 0
                ns.error = None

                self.__request_registry_context[typed_entry] = {
                            'watchers': 1,
                            'finish_event': finish_ev,
                            'download_stop_event': download_stop_ev,
                            'ns': ns
                        }

                # Push the request to the worker process.
                self.__request_q.put((download_reg, 
                                      finish_ev, 
                                      download_stop_ev, 
                                      ns))
            else:
                # There was already another download of this entry/mime-type.

                self.__log.info("Watching an existing download: %s",
                                download_reg)

                context['watchers'] += 1
                finish_ev = context['finish_event']
                download_stop_ev = context['download_stop_event']
                ns = context['ns']

            try:
                # We weren't already download this entry for any mime-type.
                self.__request_registry_types[typed_entry.entry_id] = \
                    set([typed_entry])
            except KeyError:
                # We were already downloading this entry. Make sure we're in 
                # the list of mime-types being downloaded.
                self.__request_registry_types[typed_entry.entry_id].add(
                    typed_entry)
        try:
            # Though we've now properly submitted a download/verification 
            # request, only wait for download progress if necessary. If we 
            # already have the whole file, the worker should just signal as 
            # much, anyways. If we're still downloading the file, it only 
            # matters if we have enough of it. If something happens and that 
            # file is no longer valid, the file-resource will still be faulted 
            # correctly.

            if dfs.is_up_to_date(bytes_) is False:
                self.__log.debug("Waiting for file to be up-to-date (enough): "
                                 "%s", str(dfs))

                while 1:
                    is_done = finish_ev.wait(
                                download_agent.REQUEST_WAIT_PERIOD_S)

                    if ns.error is not None:
                        # If the download was stopped while there was at least 
                        # one watcher (which generally means that the file has 
                        # changed and the  message has propagated from the 
                        # notifying thread, to the download worker, to us), 
                        # emit an exception so those callers can re-call us.
                        #
                        # If this error occurred when there were no watchers,
                        # the stop most likely occurred because there -were-
                        # no watchers.
                        if ns.error[0] == 'DownloadAgentDownloadStopException':
                            raise DownloadAgentDownloadStopException(
                                ns.error[1])

                        raise DownloadAgentDownloadAgentError(
                            "Download failed for [%s]: [%s] %s" % 
                            (typed_entry.entry_id, ns.error[0], ns.error[1]))

                    elif is_done is True:
                        break

                    elif bytes_ is not None and \
                         ns.bytes_received >= bytes_:
                        break

            # We've now downloaded enough bytes, or already had enough bytes 
            # available.
            #
            # There are two reference-counts at this point: 1) the number of 
            # threads that are watching/accessing a particular mime-type of the
            # given entry (allows the downloads to be synchronized), and 2) the 
            # number of threads that have handles to an entry, regardless of 
            # mime-type (can be faulted when the content changes).

            self.__log.info("Data is now available: %s", str(dfs))

            resource = self.__get_resource(typed_entry.entry_id, 
                                           expected_mtime_dt)

            with _SyncedResourceHandle(resource, dfs) as srh:
                yield srh
        finally:
            # Decrement the reference count.
            with self.__request_registry_locker:
                context = self.__request_registry_context[typed_entry]
                context['watchers'] -= 1

                # If we're the last watcher, remove the entry. Note that the 
                # file may still be downloading at the worker. This just 
                # manages request-concurrency.
                if context['watchers'] <= 0:
                    self.__log.debug("Watchers have dropped to zero: %s", 
                                     typed_entry)

                    # In the event that all of the requests weren't concerned 
                    # with getting the whole file, send a signal to stop 
                    # downloading.
                    download_stop_ev.set()

                    # Remove registration information. If the worker is still
                    # downloading the file, it'll have a reference/copy of the
                    # event above.
                    del self.__request_registry_context[typed_entry]

                    self.__request_registry_types[typed_entry.entry_id].remove(
                        typed_entry)

                    if not self.__request_registry_types[typed_entry.entry_id]:
                        del self.__request_registry_types[typed_entry.entry_id]

        self.__log.debug("Sync is complete, and reference-counts have been "
                         "decremented.")

    def notify_changed(self, entry_id, mtime_dt):
        """Invoked by another thread when a file has changed, most likely by 
        information reported by the "changes" API. At this time, we don't check 
        whether anything has actually ever accessed this entry... Just whether 
        something currently has it open. It's essentially the same, and cheap.
        """

        if mtime_dt.tzinfo is None:
            raise ValueError("mtime_dt must be timezone-aware.")

        self.set_resource_faulted(entry_id)

        with self.__request_registry_locker:
            try:
                types = self.__request_registry_types[entry_id]
            except KeyError:
                pass
            else:
                # Stop downloads of all active mime-types for the given entry.
                for typed_entry in types:
                    context = self.__request_registry_context[typed_entry]
                    
                    download_stop_ev = context['download_stop_event']
                    download_stop_ev.set()

def get_download_agent_external():
    try:
        return get_download_agent_external.__instance
    except AttributeError:
        get_download_agent_external.__instance = _DownloadAgentExternal()
        return get_download_agent_external.__instance


########NEW FILE########
__FILENAME__ = drive
import logging
import re
import dateutil.parser
import random
import json
import time
import httplib
import ssl

from apiclient.discovery import build
from apiclient.http import MediaFileUpload
from apiclient.errors import HttpError

from time import mktime, time
from datetime import datetime
from httplib2 import Http
from collections import OrderedDict
from os.path import isdir, isfile
from os import makedirs, stat, utime
from dateutil.tz import tzlocal, tzutc

import gdrivefs.gdtool.chunked_download

from gdrivefs.errors import AuthorizationFaultError, MustIgnoreFileError, \
                            FilenameQuantityError, ExportFormatError
from gdrivefs.conf import Conf
from gdrivefs.gdtool.oauth_authorize import get_auth
from gdrivefs.gdtool.normal_entry import NormalEntry
from gdrivefs.time_support import get_flat_normal_fs_time_from_dt
from gdrivefs.gdfs.fsutility import split_path_nolookups, \
                                    escape_filename_for_query

_CONF_SERVICE_NAME = 'drive'
_CONF_SERVICE_VERSION = 'v2'


class GdriveAuth(object):
    def __init__(self):
        self.__log = logging.getLogger().getChild('GdAuth')
        self.__client = None
        self.__authorize = get_auth()
        self.__check_authorization()

    def __check_authorization(self):
        self.__credentials = self.__authorize.get_credentials()

    def get_authed_http(self):
        self.__check_authorization()
        self.__log.info("Getting authorized HTTP tunnel.")
            
        http = Http()
        self.__credentials.authorize(http)

        return http

    def get_client(self):
        if self.__client is None:
            authed_http = self.get_authed_http()

            self.__log.info("Building authorized client from Http.  TYPE= [%s]" % 
                            (type(authed_http)))
        
            # Build a client from the passed discovery document path
            
            discoveryUrl = Conf.get('google_discovery_service_url')
# TODO: We should cache this, since we have, so often, having a problem 
#       retrieving it. If there's no other way, grab it directly, and then pass
#       via a file:// URI.
        
            try:
                client = build(_CONF_SERVICE_NAME, 
                               _CONF_SERVICE_VERSION, 
                               http=authed_http, 
                               discoveryServiceUrl=discoveryUrl)
            except HttpError as e:
                # We've seen situations where the discovery URL's server is down,
                # with an alternate one to be used.
                #
                # An error here shouldn't leave GDFS in an unstable state (the 
                # current command should just fail). Hoepfully, the failure is 
                # momentary, and the next command succeeds.

                logging.exception("There was an HTTP response-code of (%d) while "
                                  "building the client with discovery URL [%s]." % 
                                  (e.resp.status, discoveryUrl))
                raise

            self.__client = client

        return self.__client


class _GdriveManager(object):
    """Handles all basic communication with Google Drive. All methods should
    try to invoke only one call, or make sure they handle authentication 
    refreshing when necessary.
    """

    def __init__(self):
        self.__log = logging.getLogger().getChild('GdManager')
        self.__auth = GdriveAuth()

    def get_about_info(self):
        """Return the 'about' information for the drive."""

        client = self.__auth.get_client()
        response = client.about().get().execute()
        
        return response

    def list_changes(self, start_change_id=None, page_token=None):
        """Get a list of the most recent changes from GD, with the earliest 
        changes first. This only returns one page at a time. start_change_id 
        doesn't have to be valid.. It's just the lower limit to what you want 
        back. Change-IDs are integers, but are not necessarily sequential.
        """

        self.__log.info("Listing changes starting at ID [%s] with page_token "
                        "[%s]." % (start_change_id, page_token))

        client = self.__auth.get_client()

# TODO: We expected that this reports all changes to all files. If this is the 
#       case, than what's the point of the watch() call in Files?
        response = client.changes().list(pageToken=page_token, \
                        startChangeId=start_change_id).execute()

        items             = response[u'items']
        largest_change_id = int(response[u'largestChangeId'])
        next_page_token   = response[u'nextPageToken'] if u'nextPageToken' \
                                                       in response else None

        changes = OrderedDict()
        last_change_id = None
        for item in items:
            change_id   = int(item[u'id'])
            entry_id    = item[u'fileId']
            was_deleted = item[u'deleted']
            entry       = None if item[u'deleted'] else item[u'file']

            if last_change_id and change_id <= last_change_id:
                message = "Change-ID (%d) being processed is less-than the " \
                          "last change-ID (%d) to be processed." % \
                          (change_id, last_change_id)

                self.__log.error(message)
                raise Exception(message)

            try:
                normalized_entry = None if was_deleted \
                                        else NormalEntry('list_changes', entry)
            except:
                self.__log.exception("Could not normalize entry embedded in "
                                     "change with ID (%d)." % (change_id))
                raise

            changes[change_id] = (entry_id, was_deleted, normalized_entry)
            last_change_id = change_id

        return (largest_change_id, next_page_token, changes)

    def get_parents_containing_id(self, child_id, max_results=None):
        
        self.__log.info("Getting client for parent-listing.")

        client = self.__auth.get_client()

        self.__log.info("Listing entries over child with ID [%s]." %
                        (child_id))

        response = client.parents().list(fileId=child_id).execute()

        return [ entry[u'id'] for entry in response[u'items'] ]

    def get_children_under_parent_id(self, \
                                     parent_id, \
                                     query_contains_string=None, \
                                     query_is_string=None, \
                                     max_results=None):

        self.__log.info("Getting client for child-listing.")

        client = self.__auth.get_client()

        if query_contains_string and query_is_string:
            self.__log.exception("The query_contains_string and query_is_string "
                              "parameters are mutually exclusive.")
            raise

        if query_is_string:
            query = ("title='%s'" % 
                     (escape_filename_for_query(query_is_string)))
        elif query_contains_string:
            query = ("title contains '%s'" % 
                     (escape_filename_for_query(query_contains_string)))
        else:
            query = None

        self.__log.info("Listing entries under parent with ID [%s].  QUERY= "
                     "[%s]" % (parent_id, query))

        response = client.children().list(q=query, folderId=parent_id, \
                                          maxResults=max_results). \
                                          execute()

        return [ entry[u'id'] for entry in response[u'items'] ]

    def get_entries(self, entry_ids):

        retrieved = { }
        for entry_id in entry_ids:
            try:
                entry = drive_proxy('get_entry', entry_id=entry_id)
            except:
                self.__log.exception("Could not retrieve entry with ID [%s]." % 
                                     (entry_id))
                raise

            retrieved[entry_id] = entry

        self.__log.debug("(%d) entries were retrieved." % (len(retrieved)))

        return retrieved

    def get_entry(self, entry_id):
        client = self.__auth.get_client()

        try:
            entry_raw = client.files().get(fileId=entry_id).execute()
        except:
            self.__log.exception("Could not get the file with ID [%s]." % 
                                 (entry_id))
            raise

        try:
            entry = NormalEntry('direct_read', entry_raw)
        except:
            self.__log.exception("Could not normalize raw-data for entry with "
                                 "ID [%s]." % (entry_id))
            raise

        return entry

    def list_files(self, query_contains_string=None, query_is_string=None, 
                   parent_id=None):
        
        self.__log.info("Listing all files. CONTAINS=[%s] IS=[%s] "
                        "PARENT_ID=[%s]" % 
                        (query_contains_string 
                            if query_contains_string is not None 
                            else '<none>', 
                         query_is_string 
                            if query_is_string is not None 
                            else '<none>', 
                         parent_id if parent_id is not None 
                                   else '<none>'))

        client = self.__auth.get_client()

        query_components = []

        if parent_id:
            query_components.append("'%s' in parents" % (parent_id))

        if query_is_string:
            query_components.append("title='%s'" % 
                                    (escape_filename_for_query(query_is_string)))
        elif query_contains_string:
            query_components.append("title contains '%s'" % 
                                    (escape_filename_for_query(query_contains_string)))

        # Make sure that we don't get any entries that we would have to ignore.

        hidden_flags = Conf.get('hidden_flags_list_remote')
        if hidden_flags:
            for hidden_flag in hidden_flags:
                query_components.append("%s = false" % (hidden_flag))

        query = ' and '.join(query_components) if query_components else None

        page_token = None
        page_num = 0
        entries = []
        while 1:
            self.__log.debug("Doing request for listing of files with page-"
                             "token [%s] and page-number (%d): %s" % 
                             (page_token, page_num, query))

            result = client.files().list(q=query, pageToken=page_token).\
                        execute()

            self.__log.debug("(%d) entries were presented for page-number "
                             "(%d)." % 
                             (len(result[u'items']), page_num))

            for entry_raw in result[u'items']:
                try:
                    entry = NormalEntry('list_files', entry_raw)
                except:
                    self.__log.exception("Could not normalize raw-data for "
                                         "entry with ID [%s]." % 
                                         (entry_raw[u'id']))
                    raise

                entries.append(entry)

            if u'nextPageToken' not in result:
                self.__log.debug("No more pages in file listing.")
                break

            self.__log.debug("Next page-token in file-listing is [%s]." % (result[u'nextPageToken']))
            page_token = result[u'nextPageToken']
            page_num += 1

        return entries

    def download_to_local(self, output_file_path, normalized_entry, mime_type, 
                          allow_cache=True):
        """Download the given file. If we've cached a previous download and the 
        mtime hasn't changed, re-use. The third item returned reflects whether 
        the data has changed since any prior attempts.
        """

        self.__log.debug("Downloading entry with ID [%s] and mime-type [%s].", 
                         normalized_entry.id, mime_type)

        if mime_type != normalized_entry.mime_type and \
                mime_type not in normalized_entry.download_links:
            message = ("Entry with ID [%s] can not be exported to type [%s]. "
                       "The available types are: %s" % 
                       (normalized_entry.id, mime_type, 
                        ', '.join(normalized_entry.download_links.keys())))

            self.__log.warning(message)
            raise ExportFormatError(message)

        temp_path = Conf.get('file_download_temp_path')

        if not isdir(temp_path):
            try:
                makedirs(temp_path)
            except:
                self.__log.exception("Could not create temporary download "
                                     "path [%s]." % (temp_path))
                raise

        gd_mtime_epoch = mktime(normalized_entry.modified_date.timetuple())

        self.__log.debug("File will be downloaded to [%s].", 
                         (output_file_path))

        use_cache = False
        if allow_cache and isfile(output_file_path):
            # Determine if a local copy already exists that we can use.
            try:
                stat_info = stat(output_file_path)
            except:
                self.__log.exception("Could not retrieve stat() information "
                                     "for temp download file [%s]." % 
                                     (output_file_path))
                raise

            if gd_mtime_epoch == stat_info.st_mtime:
                use_cache = True

        if use_cache:
            # Use the cache. It's fine.

            self.__log.debug("File retrieved from the previously downloaded, "
                            "still-current file.")
            return (stat_info.st_size, False)

        # Go and get the file.

# TODO(dustin): This might establish a new connection. Not cool.
        authed_http = self.__auth.get_authed_http()

        url = normalized_entry.download_links[mime_type]

#        self.__log.debug("Downloading file from [%s]." % (url))
#
#        try:
#            data_tuple = authed_http.request(url)
#        except:
#            self.__log.exception("Could not download entry with ID [%s], type "
#                              "[%s], and URL [%s]." % (normalized_entry.id, 
#                                                       mime_type, url))
#            raise
#
#        (response_headers, data) = data_tuple
#
#        # Throw a log-item if we see any "Range" response-headers. If GD ever
#        # starts supporting "Range" headers, we'll be able to write smarter 
#        # download mechanics (resume, etc..).
#
#        r = re.compile('Range')
#        range_found = [("%s: %s" % (k, v)) for k, v 
#                                           in response_headers.iteritems() 
#                                           if r.match(k)]
#        if range_found:
#            self.__log.info("GD has returned Range-related headers: %s" % 
#                            (", ".join(found)))
#
#        self.__log.info("Downloaded file is (%d) bytes. Writing to [%s]." % 
#                        (len(data), output_file_path))
#
#        try:
#            with open(output_file_path, 'wb') as f:
#                f.write(data)
#        except:
#            self.__log.exception("Could not cached downloaded file. Skipped.")
#
#        else:
#            self.__log.info("File written to cache successfully.")

        with open(output_file_path, 'wb') as f:
            downloader = gdrivefs.gdtool.chunked_download.ChunkedDownload(
                            f, 
                            authed_http, 
                            url)

            while 1:
                status, done, total_size = downloader.next_chunk()
                if done is True:
                    break

        try:
            utime(output_file_path, (time(), gd_mtime_epoch))
        except:
            self.__log.exception("Could not set time on [%s]." % 
                                 (output_file_path))
            raise

        return (total_size, True)

    def __insert_entry(self, filename, mime_type, parents, data_filepath=None, 
                       modified_datetime=None, accessed_datetime=None, 
                       is_hidden=False, description=None):

        if parents is None:
            parents = []

        now_phrase = get_flat_normal_fs_time_from_dt()

        if modified_datetime is None:
            modified_datetime = now_phrase 
    
        if accessed_datetime is None:
            accessed_datetime = now_phrase 

        self.__log.info("Creating file with filename [%s] under parent(s) "
                        "[%s] with mime-type [%s], mtime= [%s], atime= [%s]." % 
                        (filename, ', '.join(parents), mime_type, 
                         modified_datetime, accessed_datetime))

        client = self.__auth.get_client()

        body = { 
                'title': filename, 
                'parents': [dict(id=parent) for parent in parents], 
                'mimeType': mime_type, 
                'labels': { "hidden": is_hidden }, 
                'description': description 
            }

        if modified_datetime is not None:
            body['modifiedDate'] = modified_datetime

        if accessed_datetime is not None:
            body['lastViewedByMeDate'] = accessed_datetime

        args = { 'body': body }

        if data_filepath:
            args['media_body'] = MediaFileUpload(filename=data_filepath, \
                                                 mimetype=mime_type)

        self.__log.debug("Doing file-insert with:\n%s" % (args))

        try:
            result = client.files().insert(**args).execute()
        except:
            self.__log.exception("Could not insert file [%s]." % (filename))
            raise

        normalized_entry = NormalEntry('insert_entry', result)
            
        self.__log.info("New entry created with ID [%s]." % 
                        (normalized_entry.id))

        return normalized_entry

    def truncate(self, normalized_entry):

        self.__log.info("Truncating entry [%s]." % (normalized_entry.id))

        try:
            entry = self.update_entry(normalized_entry, data_filepath='/dev/null')
        except:
            self.__log.exception("Could not truncate entry with ID [%s]." % 
                                 (normalized_entry.id))
            raise

    def update_entry(self, normalized_entry, filename=None, data_filepath=None, 
                     mime_type=None, parents=None, modified_datetime=None, 
                     accessed_datetime=None, is_hidden=False, 
                     description=None):

        if not mime_type:
            mime_type = normalized_entry.mime_type

        self.__log.debug("Updating entry [%s].", normalized_entry)

        client = self.__auth.get_client()

        body = { 'mimeType': mime_type }

        if filename is not None:
            body['title'] = filename
        
        if parents is not None:
            body['parents'] = parents

        if is_hidden is not None:
            body['labels'] = { "hidden": is_hidden }

        if description is not None:
            body['description'] = description

        set_mtime = True
        if modified_datetime is not None:
            body['modifiedDate'] = modified_datetime
        else:
            body['modifiedDate'] = get_flat_normal_fs_time_from_dt()

        if accessed_datetime is not None:
            set_atime = 1
            body['lastViewedByMeDate'] = accessed_datetime
        else:
            set_atime = 0

        args = { 'fileId': normalized_entry.id, 
                 'body': body, 
                 'setModifiedDate': set_mtime, 
                 'updateViewedDate': set_atime 
                 }

        if data_filepath:
            args['media_body'] = MediaFileUpload(data_filepath, 
                                                 mimetype=mime_type)

        result = client.files().update(**args).execute()
        normalized_entry = NormalEntry('update_entry', result)

        self.__log.debug("Entry with ID [%s] updated." % (normalized_entry.id))

        return normalized_entry

    def create_directory(self, filename, parents, **kwargs):

        mimetype_directory = Conf.get('directory_mimetype')
        return self.__insert_entry(filename, mimetype_directory, parents, 
                                   **kwargs)

    def create_file(self, filename, data_filepath, parents, mime_type=None, 
                    **kwargs):
# TODO: It doesn't seem as if the created file is being registered.
        # Even though we're supposed to provide an extension, we can get away 
        # without having one. We don't want to impose this when acting like a 
        # normal FS.

        # If no data and no mime-type was given, default it.
        if mime_type == None:
            mime_type = Conf.get('file_default_mime_type')
            self.__log.debug("No mime-type was presented for file "
                             "create/update. Defaulting to [%s]." % 
                             (mime_type))

        return self.__insert_entry(filename,
                                   mime_type,
                                   parents,
                                   data_filepath,
                                   **kwargs)

    def rename(self, normalized_entry, new_filename):

        result = split_path_nolookups(new_filename)
        (path, filename_stripped, mime_type, is_hidden) = result

        self.__log.debug("Renaming entry [%s] to [%s]. IS_HIDDEN=[%s]" % 
                         (normalized_entry, filename_stripped, is_hidden))

        return self.update_entry(normalized_entry, filename=filename_stripped, 
                                 is_hidden=is_hidden)

    def remove_entry(self, normalized_entry):

        self.__log.info("Removing entry with ID [%s]." % (normalized_entry.id))

        client = self.__auth.get_client()

        args = { 'fileId': normalized_entry.id }

        try:
            result = client.files().delete(**args).execute()
        except (Exception) as e:
            if e.__class__.__name__ == 'HttpError' and \
               str(e).find('File not found') != -1:
                raise NameError(normalized_entry.id)

            self.__log.exception("Could not send delete for entry with ID "
                                 "[%s]." %
                                 (normalized_entry.id))
            raise

        self.__log.info("Entry deleted successfully.")

class _GoogleProxy(object):
    """A proxy class that invokes the specified Google Drive call. It will 
    automatically refresh our authorization credentials when the need arises. 
    Nothing inside the Google Drive wrapper class should call this. In general, 
    only external logic should invoke us.
    """
    
    def __init__(self):
        self.__log = logging.getLogger().getChild('GoogleProxy')
        self.authorize      = get_auth()
        self.gdrive_wrapper = _GdriveManager()

    def __getattr__(self, action):
        self.__log.debug("Proxied action [%s] requested." % (action))
    
        try:
            method = getattr(self.gdrive_wrapper, action)
        except (AttributeError):
            self.__log.exception("Action [%s] can not be proxied to Drive. "
                              "Action is not valid." % (action))
            raise

        def proxied_method(auto_refresh=True, **kwargs):
            # Now, try to invoke the mechanism. If we succeed, return 
            # immediately. If we get an authorization-fault (a resolvable 
            # authorization problem), fall through and attempt to fix it. Allow 
            # any other error to bubble up.
            
            self.__log.debug("Attempting to invoke method for action [%s]." % 
                             (action))

            for n in range(0, 5):
                try:
                    return method(**kwargs)
                except (ssl.SSLError, httplib.BadStatusLine) as e:
                    # These happen sporadically. Use backoff.
                    self.__log.exception("There was a transient connection "
                                         "error (%s). Trying again (%s): %d" %
                                         (e.__class__.__name__, str(e), n))

                    time.sleep((2 ** n) + random.randint(0, 1000) / 1000)
                except HttpError as e:
                    try:
                        error = json.loads(e.content)
                    except ValueError:
                        _logger.error("Non-JSON error while doing chunked "
                                      "download: %s", e.content) 
                    
                    if error.get('code') == 403 and \
                       error.get('errors')[0].get('reason') \
                       in ['rateLimitExceeded', 'userRateLimitExceeded']:
                        # Apply exponential backoff.
                        self.__log.exception("There was a transient HTTP "
                                             "error (%s). Trying again (%d): "
                                             "%s" %
                                             (e.__class__.__name__, str(e), n))

                        time.sleep((2 ** n) + random.randint(0, 1000) / 1000)
                    else:
                        # Other error, re-raise.
                        raise
                except AuthorizationFaultError:
                    # If we're not allowed to refresh the token, or we've
                    # already done it in the last attempt.
                    if not auto_refresh or n == 1:
                        raise

                    # We had a resolvable authorization problem.

                    self.__log.info("There was an authorization fault under "
                                    "action [%s]. Attempting refresh." % 
                                    (action))
                    
                    authorize = get_auth()
                    authorize.check_credential_state()

                    # Re-attempt the action.

                    self.__log.info("Refresh seemed successful. Reattempting "
                                    "action [%s]." % (action))
                        
        return proxied_method
                
def drive_proxy(action, auto_refresh=True, **kwargs):
    if drive_proxy.gp == None:
        drive_proxy.gp = _GoogleProxy()

    method = getattr(drive_proxy.gp, action)
    return method(auto_refresh, **kwargs)
    
drive_proxy.gp = None


########NEW FILE########
__FILENAME__ = normal_entry
import logging
import re
import dateutil.parser
import json
import time

from time import mktime
from mimetypes import guess_type
from numbers import Number
from datetime import datetime

from gdrivefs.conf import Conf
from gdrivefs.utility import utility
from gdrivefs.errors import ExportFormatError
from gdrivefs.time_support import get_flat_normal_fs_time_from_dt


class NormalEntry(object):
    __default_general_mime_type = Conf.get('default_mimetype')
    __properties_extra = ('is_directory', 
                          'is_visible', 
                          'parents', 
                          'download_types',
                          'modified_date',
                          'modified_date_epoch',
                          'mtime_byme_date',
                          'mtime_byme_date_epoch',
                          'atime_byme_date',
                          'atime_byme_date_epoch')
    __directory_mimetype = Conf.get('directory_mimetype')

    def __init__(self, gd_resource_type, raw_data):
        # LESSONLEARNED: We had these set as properties, but CPython was 
        #                reusing the reference between objects.

        self.__log = logging.getLogger().getChild('NormalEntry')

        self.__info = {}
        self.__parents = []
        self.__raw_data = raw_data
        self.__cache_data = None
        self.__cache_mimetypes = None
        self.__cache_dict = {}

        """Return True if reading from this file should return info and deposit 
        the data elsewhere. This is predominantly determined by whether we can
        get a file-size up-front, or we have to decide on a specific mime-type 
        in order to do so.
        """
        requires_mimetype = (u'fileSize' not in self.__raw_data and \
                             raw_data[u'mimeType'] != self.__directory_mimetype)

        try:
            self.__info['requires_mimetype']          = requires_mimetype
            self.__info['title']                      = raw_data[u'title']
            self.__info['mime_type']                  = raw_data[u'mimeType']
            self.__info['labels']                     = raw_data[u'labels']
            self.__info['id']                         = raw_data[u'id']
            self.__info['last_modifying_user_name']   = raw_data[u'lastModifyingUserName']
            self.__info['writers_can_share']          = raw_data[u'writersCanShare']
            self.__info['owner_names']                = raw_data[u'ownerNames']
            self.__info['editable']                   = raw_data[u'editable']
            self.__info['user_permission']            = raw_data[u'userPermission']

            self.__info['download_links']         = raw_data[u'exportLinks']          if u'exportLinks'           in raw_data else { }
            self.__info['link']                   = raw_data[u'embedLink']            if u'embedLink'             in raw_data else None
            self.__info['file_size']              = int(raw_data[u'fileSize'])        if u'fileSize'              in raw_data else 0
            self.__info['file_extension']         = raw_data[u'fileExtension']        if u'fileExtension'         in raw_data else None
            self.__info['md5_checksum']           = raw_data[u'md5Checksum']          if u'md5Checksum'           in raw_data else None
            self.__info['image_media_metadata']   = raw_data[u'imageMediaMetadata']   if u'imageMediaMetadata'    in raw_data else None

            if u'downloadUrl' in raw_data:
                self.__info['download_links'][self.__info['mime_type']] = raw_data[u'downloadUrl']

            self.__update_display_name()

            for parent in raw_data[u'parents']:
                self.__parents.append(parent[u'id'])

        except (KeyError) as e:
            self.__log.exception("Could not normalize entry on raw key [%s]. Does not exist in source." % (str(e)))
            raise

    def __getattr__(self, key):
        return self.__info[key]

    def __str__(self):
        return ("<NORMAL ID= [%s] MIME= [%s] NAME= [%s] URIS= (%d)>" % 
                (self.id, self.mime_type, self.title, 
                 len(self.download_links)))

    def __repr__(self):
        return str(self)

    def __update_display_name(self):
        # This is encoded for displaying locally.
        self.__info['title_fs'] = utility.translate_filename_charset(self.__info['title'])

    def temp_rename(self, new_filename):
        """Set the name to something else, here, while we, most likely, wait 
        for the change at the server to propogate.
        """
    
        self.__info['title'] = new_filename
        self.__update_display_name()

    def normalize_download_mimetype(self, specific_mimetype=None):
        """If a mimetype is given, return it if there is a download-URL 
        available for it, or fail. Else, determine if a copy can downloaded 
        with the default mime-type (application/octet-stream, or something 
        similar), or return the only mime-type in the event that there's only 
        one download format.
        """

        if self.__cache_mimetypes is None:
            self.__cache_mimetypes = [[], None]
        
        if specific_mimetype is not None:
            if specific_mimetype not in self.__cache_mimetypes[0]:
                self.__log.debug("Normalizing mime-type [%s] for download.  "
                                 "Options: %s" % (specific_mimetype, 
                                                  self.download_types))

                if specific_mimetype not in self.download_links:
                    raise ExportFormatError("Mime-type [%s] is not available for "
                                            "download. Options: %s" % 
                                            (self.download_types))

                self.__cache_mimetypes[0].append(specific_mimetype)

            return specific_mimetype

        if self.__cache_mimetypes[1] is None:
            # Try to derive a mimetype from the filename, and see if it matches
            # against available export types.
            (mimetype_candidate, _) = guess_type(self.title_fs, True)
            if mimetype_candidate is not None and \
               mimetype_candidate in self.download_links:
                mime_type = mimetype_candidate

            elif NormalEntry.__default_general_mime_type in self.download_links:
                mime_type = NormalEntry.__default_general_mime_type

            # If there's only one download link, resort to using it (perhaps it was 
            # an uploaded file, assigned only one type).
            elif len(self.download_links) == 1:
                mime_type = self.download_links.keys()[0]

            else:
                raise ExportFormatError("A correct mime-type needs to be "
                                        "specified. Options: %s" % 
                                        (self.download_types))

            self.__cache_mimetypes[1] = mime_type

        return self.__cache_mimetypes[1]

    def __convert(self, data):
        if isinstance(data, dict):
            list_ = [("K(%s)=V(%s)" % (self.__convert(key), 
                                  self.__convert(value))) \
                     for key, value \
                     in data.iteritems()]

            final = '; '.join(list_)
            return final
        elif isinstance(data, list):
            final = ', '.join([('LI(%s)' % (self.__convert(element))) \
                               for element \
                               in data])
            return final
        elif isinstance(data, unicode):
            return utility.translate_filename_charset(data)
        elif isinstance(data, Number):
            return str(data)
        elif isinstance(data, datetime):
            return get_flat_normal_fs_time_from_dt(data)
        else:
            return data

    def get_data(self):
            original = dict([(key.encode('ASCII'), value) 
                                for key, value 
                                in self.__raw_data.iteritems()])

            distilled = self.__info

            extra = dict([(key, getattr(self, key)) 
                                for key 
                                in self.__properties_extra])

            data_dict = {'original': original,
                         #'distilled': distilled,
                         'extra': extra}

            return data_dict

    @property
    def xattr_data(self):
        if self.__cache_data is None:
            data_dict = self.get_data()
            
            attrs = {}
            for a_type, a_dict in data_dict.iteritems():
#                self.__log.debug("Setting [%s]." % (a_type))
                for key, value in a_dict.iteritems():
                    fqkey = ('user.%s.%s' % (a_type, key))
                    attrs[fqkey] = self.__convert(value)
 
            self.__cache_data = attrs

        return self.__cache_data

    @property
    def is_directory(self):
        """Return True if we represent a directory."""
        return (self.__info['mime_type'] == self.__directory_mimetype)

    @property
    def is_visible(self):
        if [ flag 
             for flag, value 
             in self.labels.items() 
             if flag in Conf.get('hidden_flags_list_local') and value ]:
            return False
        else:
            return True

    @property
    def parents(self):
        return self.__parents

    @property
    def download_types(self):
        return self.download_links.keys()

    @property
    def modified_date(self):
        if 'modified_date' not in self.__cache_dict:
            self.__cache_dict['modified_date'] = \
                dateutil.parser.parse(self.__raw_data[u'modifiedDate'])

        return self.__cache_dict['modified_date']

    @property
    def modified_date_epoch(self):
        # mktime() only works in terms of the local timezone, so compensate 
        # (this works with DST, too).
        return mktime(self.modified_date.timetuple()) - time.timezone
        
    @property  
    def mtime_byme_date(self):
        if 'modified_byme_date' not in self.__cache_dict:
            self.__cache_dict['modified_byme_date'] = \
                dateutil.parser.parse(self.__raw_data[u'modifiedByMeDate'])

        return self.__cache_dict['modified_byme_date']

    @property
    def mtime_byme_date_epoch(self):
        return mktime(self.mtime_byme_date.timetuple()) - time.timezone

    @property
    def atime_byme_date(self):
        if 'viewed_byme_date' not in self.__cache_dict:
            self.__cache_dict['viewed_byme_date'] = \
                dateutil.parser.parse(self.__raw_data[u'lastViewedByMeDate']) \
                if u'lastViewedByMeDate' in self.__raw_data \
                else None

        return self.__cache_dict['viewed_byme_date']

    @property
    def atime_byme_date_epoch(self):
        return mktime(self.atime_byme_date.timetuple()) - time.timezone \
                if self.atime_byme_date \
                else None


########NEW FILE########
__FILENAME__ = oauth_authorize
import logging
import pickle
import json

from oauth2client.client import flow_from_clientsecrets
from oauth2client.client import OOB_CALLBACK_URN

from datetime import datetime
from httplib2 import Http
from tempfile import NamedTemporaryFile
from os import remove

from gdrivefs.errors import AuthorizationFailureError, AuthorizationFaultError
from gdrivefs.conf import Conf

_logger = logging.getLogger(__name__)


class _OauthAuthorize(object):
    """Manages authorization process."""

    __log = None

    flow            = None
    credentials     = None
    cache_filepath  = None
    
    def __init__(self):
        self.__log = logging.getLogger().getChild('OauthAuth')

        cache_filepath  = Conf.get('auth_cache_filepath')
        api_credentials = Conf.get('api_credentials')

        self.cache_filepath = cache_filepath
        self.credentials = None

        with NamedTemporaryFile() as f:
            json.dump(api_credentials, f)
            f.flush()

            self.flow = flow_from_clientsecrets(f.name, 
                                                scope=self.__get_scopes(), 
                                                redirect_uri=OOB_CALLBACK_URN)
        
        #self.flow.scope = self.__get_scopes()
        #self.flow.redirect_uri = OOB_CALLBACK_URN

    def __get_scopes(self):
        scopes = "https://www.googleapis.com/auth/drive "\
                 "https://www.googleapis.com/auth/drive.file"
               #'https://www.googleapis.com/auth/userinfo.email '
               #'https://www.googleapis.com/auth/userinfo.profile')
        return scopes

    def step1_get_auth_url(self):
        return self.flow.step1_get_authorize_url()

    def __clear_cache(self):
        if self.cache_filepath is not None:
            try:
                remove(self.cache_filepath)
            except:
                pass
    
    def __refresh_credentials(self):
        self.__log.info("Doing credentials refresh.")

        http = Http()

        try:
            self.credentials.refresh(http)
        except (Exception) as e:
            message = "Could not refresh credentials."
            raise AuthorizationFailureError(message)

        self.__update_cache(self.credentials)
            
        self.__log.info("Credentials have been refreshed.")
            
    def __step2_check_auth_cache(self):
        # Attempt to read cached credentials.

        if self.cache_filepath is None:
            raise ValueError("Credentials file-path is not set.")

        if self.credentials is None:
            self.__log.info("Checking for cached credentials: %s" % 
                            (self.cache_filepath))

            with open(self.cache_filepath) as cache:
                credentials_serialized = cache.read()

            # If we're here, we have serialized credentials information.

            self.__log.info("Raw credentials retrieved from cache.")
            
            try:
                credentials = pickle.loads(credentials_serialized)
            except:
                # We couldn't decode the credentials. Kill the cache.
                self.__clear_cache()
                raise

            self.credentials = credentials
                
            # Credentials restored. Check expiration date.

            expiry_phrase = self.credentials.token_expiry.strftime(
                                '%Y%m%d-%H%M%S')
                
            self.__log.info("Cached credentials found with expire-date [%s]." % 
                            (expiry_phrase))
            
            self.check_credential_state()

        return self.credentials

    def check_credential_state(self):
        """Do all of the regular checks necessary to keep our access going, 
        such as refreshing when we expire.
        """
        if(datetime.today() >= self.credentials.token_expiry):
            self.__log.info("Credentials have expired. Attempting to refresh "
                         "them.")
            
            self.__refresh_credentials()
            return self.credentials

    def get_credentials(self):
        return self.__step2_check_auth_cache()
    
    def __update_cache(self, credentials):
        if self.cache_filepath is None:
            raise ValueError("Credentials file-path is not set.")

        # Serialize credentials.

        self.__log.info("Serializing credentials for cache.")

        credentials_serialized = pickle.dumps(credentials)

        # Write cache file.

        self.__log.info("Writing credentials to cache.")

        with open(self.cache_filepath, 'w') as cache:
            cache.write(credentials_serialized)

    def step2_doexchange(self, auth_code):
        # Do exchange.

        self.__log.info("Doing exchange.")
        
        try:
            credentials = self.flow.step2_exchange(auth_code)
        except Exception as e:
            message = ("Could not do auth-exchange (this was either a "\
                       "legitimate error, or the auth-exchange was attempted "\
                       "when not necessary): %s" % (e))

            raise AuthorizationFailureError(message)
        
        self.__log.info("Credentials established.")

        self.__update_cache(credentials)
        self.credentials = credentials

oauth = None
def get_auth():
    global oauth
    if oauth is None:
        _logger.debug("Creating OauthAuthorize.")
        oauth = _OauthAuthorize()
    
    return oauth


########NEW FILE########
__FILENAME__ = buffer_segments
import logging

from threading import Lock

class BufferSegments(object):
    """Describe a series of strings that, when concatenated, represent the 
    whole file. This is used to try and contain the amount of the data that has
    the be copied as updates are applied to the file.
    """

    __locker = Lock()

    def __init__(self, data, block_size):
        # An array of 2-tuples: (offset, string). We should allow data to be 
        # empty. Thus, we should allow a segment to be empty (useful, in 
        # general).
        self.__segments = [(0, data)]

        self.__block_size = block_size
        self.__log = logging.getLogger().getChild('BufferSeg')

    def __repr__(self):
        return ("<BSEGS  SEGS= (%(segs)d) BLKSIZE= (%(block_size)d)>" % 
                { 'segs': len(self.__segments), 
                  'block_size': self.__block_size })

    def dump(self):
        pprint(self.__segments)

    def __find_segment(self, offset):

        # Locate where to insert the data.
        seg_index = 0
        while seg_index < len(self.__segments):
            seg_offset = self.__segments[seg_index][0]

            # If the current segment starts after the point of insertion.        
            if seg_offset > offset:
                return (seg_index - 1)

            # If the insertion point is at the beginning of this segment.
            elif seg_offset == offset:
                return seg_index

            seg_index += 1

        # If we get here, we never ran into a segment with an offset greater 
        # that the insertion offset.
        return (seg_index - 1)

    def __split(self, seg_index, offset):
        """Split the given segment at the given offset. Offset is relative to 
        the particular segment (an offset of '0' refers to the beginning of the 
        segment). At finish, seg_index will represent the segment containing 
        the first half of the original data (and segment with index 
        (seg_index + 1) will contain the second).
        """
    
        (seg_offset, seg_data) = self.__segments[seg_index]

        first_half = seg_data[0:offset]
        firsthalf_segment = (seg_offset, first_half)
        self.__segments.insert(seg_index, firsthalf_segment)

        second_half = seg_data[offset:]
        if second_half == '':
            raise IndexError("Can not use offset (%d) to split segment (%d) "
                             "of length (%d)." % 
                             (offset, seg_index, len(seg_data)))
        
        secondhalf_segment = (seg_offset + offset, second_half)
        self.__segments[seg_index + 1] = secondhalf_segment

        return (firsthalf_segment, secondhalf_segment)

    def apply_update(self, offset, data):
        """Find the correct place to insert the data, splitting existing data 
        segments into managable fragments ("segments"), overwriting a number of 
        bytes equal in size to the incoming data. If the incoming data will
        overflow the end of the list, grow the list.
        """

        with self.__locker:
            data_len = len(data)

            if len(self.__segments) == 1 and self.__segments[0][1] == '':
                self.__segments = []
                simple_append = True
            else:
                simple_append = (offset >= self.length)

            self.__log.debug("Applying update of (%d) bytes at offset (%d). "
                             "Current segment count is (%d). Total length is "
                             "(%d). APPEND= [%s]" % 
                             (data_len, offset, len(self.__segments), 
                              self.length, simple_append))

            if not simple_append:
                seg_index = self.__find_segment(offset)

                # Split the existing segment(s) rather than doing any 
                # concatenation. Theoretically, the effort of writing to an 
                # existing file should shrink over time.

                (seg_offset, seg_data) = self.__segments[seg_index]
                seg_len = len(seg_data)
                
                # If our data is to be written into the middle of the segment, 
                # split the segment such that the unnecessary prefixing bytes are 
                # moved to a new segment preceding the current.
                if seg_offset < offset:
                    prefix_len = offset - seg_offset
                    self.__log.debug("Splitting-of PREFIX of segment (%d). Prefix "
                                     "length is (%d). Segment offset is (%d) and "
                                     "length is (%d)." % 
                                     (seg_index, prefix_len, seg_offset, 
                                      len(seg_data)))

                    (_, (seg_offset, seg_data)) = self.__split(seg_index, 
                                                               prefix_len)

                    seg_len = prefix_len
                    seg_index += 1

                # Now, apply the update. Collect the number of segments that will 
                # be affected, and reduce to two (at most): the data that we're 
                # applying, and the second part of the last affected one (if 
                # applicable). If the incoming data exceeds the length of the 
                # existing data, it is a trivial consideration.

                stop_offset = offset + data_len
                seg_stop = seg_index
                while 1:
                    # Since the insertion offset must be within the given data 
                    # (otherwise it'd be an append, above), it looks like we're 
                    # inserting into the last segment.
                    if seg_stop >= len(self.__segments):
                        break
                
                    # If our offset is within the current set of data, this is not
                    # going to be an append operation.
                    if self.__segments[seg_stop][0] >= stop_offset:
                        break
                    
                    seg_stop += 1

                seg_stop -= 1

# TODO: Make sure that updates applied at the front of a segment are correct.

                self.__log.debug("Replacement interval is [%d, %d]. Current "
                                 "segments= (%d)" % 
                                 (seg_index, seg_stop, len(self.__segments)))

                # How much of the last segment that we touch will be affected?
                (lastseg_offset, lastseg_data) = self.__segments[seg_stop] 

                lastseg_len = len(lastseg_data)
                affected_len = (offset + data_len) - lastseg_offset
                if affected_len > 0 and affected_len < lastseg_len:
                    self.__log.debug("Splitting-of suffix of segment (%d). "
                                     "Suffix length is (%d). Segment offset "
                                     "is (%d) and length is (%d)." % 
                                     (seg_stop, lastseg_len - affected_len, 
                                      lastseg_offset, lastseg_len))
                    self.__split(seg_stop, affected_len)

                # We now have a distinct range of segments to replace with the new 
                # data. We are implicitly accounting for the situation in which our
                # data is longer than the remaining number of bytes in the file.

                self.__log.debug("Replacing segment(s) (%d)->(%d) with new "
                                 "segment having offset (%d) and length "
                                 "(%d)." % (seg_index, seg_stop + 1, 
                                            seg_offset, len(data)))

                self.__segments[seg_index:seg_stop + 1] = [(seg_offset, data)]
            else:
                self.__segments.append((offset, data))

    def read(self, offset=0, length=None):
        """A generator that returns data from the given offset in blocks no
        greater than the block size.
        """

        with self.__locker:
            self.__log.debug("Reading at offset (%d) for length [%s]. Total "
                             "length is [%s]."  % 
                             (offset, length, self.length))

            if length is None:
                length = self.length

            current_segindex = self.__find_segment(offset)
            current_offset = offset

            boundary_offset = offset + length

            # The WHILE condition should only catch if the given length exceeds 
            # the actual length. Else, the BREAK should always be sufficient.
            last_segindex = None
            (seg_offset, seg_data, seg_len) = (None, None, None)
            while current_segindex < len(self.__segments):
                if current_segindex != last_segindex:
                    (seg_offset, seg_data) = self.__segments[current_segindex]
                    seg_len = len(seg_data)
                    last_segindex = current_segindex

                grab_at = current_offset - seg_offset
                remaining_bytes = boundary_offset - current_offset

                # Determine how many bytes we're looking for, and how many we 
                # can get from this segment.

                grab_len = min(remaining_bytes,                         # Number of remaining, requested bytes.
                               seg_len - (current_offset - seg_offset), # Number of available bytes in segment.
                               self.__block_size)                       # Maximum block size.

                grabbed = seg_data[grab_at:grab_at + grab_len]
                current_offset += grab_len
                yield grabbed

                # current_offset should never exceed boundary_offset.
                if current_offset >= boundary_offset:
                    break

                # Are we going to have to read from the next segment, next 
                # time?
                if current_offset >= (seg_offset + seg_len):
                    current_segindex += 1

    @property
    def length(self):
        if not self.__segments:
            return 0

        last_segment = self.__segments[-1]
        return last_segment[0] + len(last_segment[1])


########NEW FILE########
__FILENAME__ = livereader_base
import logging


class LiveReaderBase(object):
    """A base object for data that can be retrieved on demand."""

    __log = None
    __data = None

    def __getitem__(self, key):
        self.__log = logging.getLogger().getChild('LiveReaderBase')
        child_name = self.__class__.__name__

        self.__log.debug("Key [%s] requested on LiveReaderBase type [%s]." % 
                         (key, child_name))

        try:
            return self.__data[key]
        except:
            pass

        try:
            self.__data = self.get_data(key)
        except:
            self.__log.exception("Could not retrieve data for live-updater "
                                 "wrapping [%s]." % (child_name))
            raise

        try:
            return self.__data[key]
        except:
            self.__log.exception("We just updated live-updater wrapping [%s], "
                                 "but we must've not been able to find entry "
                                 "[%s]." % (child_name, key))
            raise

    def get_data(self, key):
        raise NotImplementedError("get_data() method must be implemented in "
                                  "the LiveReaderBase child.")

    @classmethod
    def get_instance(cls):
        """A helper method to dispense a singleton of whomever is inheriting "
        from us.
        """

        class_name = cls.__name__

        try:
            LiveReaderBase.__instances
        except:
            LiveReaderBase.__instances = { }

        try:
            return LiveReaderBase.__instances[class_name]
        except:
            LiveReaderBase.__instances[class_name] = cls()
            return LiveReaderBase.__instances[class_name]



########NEW FILE########
__FILENAME__ = http_pool
from contextlib import contextmanager
from gevent.queue import Queue

from gevent import monkey; 
monkey.patch_socket()

from httplib2 import Http


class HttpPool(object):
    def __init__(self, size, factory=Http):
        self.__size = size
        self.__factory = factory
        self.__pool = Queue()

        for i in xrange(self.__size):
            self.__pool.put(self.__factory())

    @contextmanager
    def reserve(self):
        http = self.__pool.get()
        yield http
        self.__pool.put(http)

    def request(self, *args, **kwargs):
        with self.reserve() as http:
            return http.request(*args, **kwargs)


########NEW FILE########
__FILENAME__ = log_config
import logging

from logging import getLogger, Formatter
from logging.handlers import SysLogHandler, TimedRotatingFileHandler
from os.path import exists
from sys import platform

default_logger = getLogger()
default_logger.setLevel(logging.WARNING)
#default_logger.setLevel(logging.DEBUG)

# Log to syslog.

if platform == "darwin":
    # Apple made 10.5 more secure by disabling network syslog:
    address = "/var/run/syslog"
elif exists('/dev/log'):
    address = '/dev/log'
else:
    address = ('localhost', 514)

log_syslog = SysLogHandler(address, facility=SysLogHandler.LOG_LOCAL0)
log_format = 'GD: %(name)-12s %(levelname)-7s %(message)s'
log_syslog.setFormatter(Formatter(log_format))
default_logger.addHandler(log_syslog)

# Log to physical file.

log_filepath = '/tmp/gdrivefs.log'
log_file = TimedRotatingFileHandler(log_filepath, 'D', backupCount=5)
log_file.setFormatter(Formatter('%(asctime)s [%(name)s %(levelname)s] %(message)s'))
default_logger.addHandler(log_file)


########NEW FILE########
__FILENAME__ = path_config
import sys

sys.path.insert(0, '.')


########NEW FILE########
__FILENAME__ = report
import logging

from threading import Timer

from gdrivefs.conf import Conf
from gdrivefs.timer import Timers

class Report(object):
    """A tool for gathering statistics and emitting them to the log."""

    data = { }

    def __init__(self):
        logging.debug("Initializing Report singleton.")

        self.__emit_log()

    @staticmethod
    def get_instance():
        if not Report.instance:
            try:
                Report.instance = Report()
            except:
                logging.exception("Could not create Report.")
                raise

        return Report.instance

    def __emit_log(self):
        for source_name, source_data in self.data.iteritems():
            pairs = [ ("%s= [%s]" % (k, v)) 
                        for k, v 
                        in source_data.iteritems() ]
            logging.info("RPT EMIT(%s): %s" % (source_name, ', '.join(pairs)))

        report_emit_interval_s = Conf.get('report_emit_frequency_s')
        emit_timer = Timer(report_emit_interval_s, self.__emit_log)

        Timers.get_instance().register_timer('emit', emit_timer)

    def remove_all_values(self, source_name):

        del self.data[source_name]

    def get_values(self, source_name):

        return self.data[source_name]

    def is_source(self, source_name):

        return source_name in self.data

    def set_values(self, source_name, key, value):
    
        logging.debug("Setting reporting key [%s] with source [%s]." % 
                      (key, source_name))

        if source_name not in self.data:
            self.data[source_name] = { }

        self.data[source_name][key] = value

Report.instance = None




########NEW FILE########
__FILENAME__ = timer
from threading import Timer, Lock

import logging

_logger = logging.getLogger(__name__)


class Timers(object):
    timers = None
    lock = Lock()
    autostart_default = True

    def __init__(self):
        with self.lock:
            self.timers = {}

    @staticmethod
    def get_instance():
        with Timers.singleton_lock:
            if not Timers.instance:
                Timers.instance = Timers()

        return Timers.instance

    def set_autostart_default(self, flag):
        """This can be set to keep the timers from actually starting, if we
        don't want to spawn off new threads."""

        Timers.autostart_default = flag

    def register_timer(self, name, timer, autostart=None):
        if autostart is None:
            autostart = Timers.autostart_default

        with self.lock:
            if name not in self.timers:
                self.timers[name] = timer

        if autostart:
            timer.start()

    def cancel_all(self):
        """Cancelling all timer threads. This might be called multiple times 
        depending on how we're terminated.
        """

        with self.lock:
            for name, timer in self.timers.items():
                _logging.debug("Cancelling timer: [%s]", name)
                timer.cancel()

                del self.timers[name]

Timers.instance = None
Timers.singleton_lock = Lock()


########NEW FILE########
__FILENAME__ = time_support
from math import floor
from datetime import datetime
from dateutil.tz import tzlocal, tzutc

DTF_DATETIME = '%Y%m%d-%H%M%S'
DTF_DATETIMET = '%Y-%m-%dT%H:%M:%S'
DTF_DATE = '%Y%m%d'
DTF_TIME = '%H%M%S'

def get_normal_dt_from_rfc3339_phrase(phrase):
    stripped = phrase[:phrase.rindex('.')]
    dt = datetime.strptime(stripped, DTF_DATETIMET).replace(tzinfo=tzutc())

    print("get_normal_dt_from_rfc3339_phrase(%s) => %s" % (phrase, dt))

    return dt

def build_rfc3339_phrase(datetime_obj):
    datetime_phrase = datetime_obj.strftime(DTF_DATETIMET)
    us = datetime_obj.strftime('%f')

    seconds = datetime_obj.utcoffset().total_seconds()

    if seconds is None:
        datetime_phrase += 'Z'
    else:
        # Append: decimal, 6-digit uS, -/+, hours, minutes
        datetime_phrase += ('.%.6s%s%02d:%02d' % (
                            us.zfill(6),
                            ('-' if seconds < 0 else '+'),
                            abs(int(floor(seconds / 3600))),
                            abs(seconds % 3600)
                            ))

    print("build_rfc3339_phrase(%s) => %s" % (datetime_obj, datetime_phrase))
    return datetime_phrase

def get_normal_dt_from_epoch(epoch):
    dt = datetime.fromtimestamp(epoch, tzlocal())
    normal_dt = normalize_dt(dt)

    print("get_normal_dt_from_epoch(%s) => %s" % (epoch, normal_dt))
    return normal_dt

def normalize_dt(dt=None):
    if dt is None:
        dt = datetime.now()

    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=tzlocal())

    normal_dt = dt.astimezone(tzutc())

    print("normalize_dt(%s) => %s" % (dt, normal_dt))
    return normal_dt

def get_flat_normal_fs_time_from_dt(dt=None):
    if dt is None:
        dt = datetime.now()

    dt_normal = normalize_dt(dt)
    flat_normal = build_rfc3339_phrase(dt_normal)

    print("get_flat_normal_fs_time_from_dt(%s) => %s" % (dt, flat_normal))
    return flat_normal

def get_flat_normal_fs_time_from_epoch(epoch):
    dt_normal = get_normal_dt_from_epoch(epoch)
    flat_normal = build_rfc3339_phrase(dt_normal)

    print("get_flat_normal_fs_time_from_epoch(%s) => %s" % (epoch, flat_normal))
    return flat_normal


########NEW FILE########
__FILENAME__ = utility
import json
import logging
import re
import sys

from sys import getfilesystemencoding

from gdrivefs.conf import Conf

# TODO(dustin): Make these individual functions.


class _DriveUtility(object):
    """General utility functions loosely related to GD."""

    # Mime-types to translate to, if they appear within the "exportLinks" list.
    gd_to_normal_mime_mappings = {
            'application/vnd.google-apps.document':        
                'text/plain',
            'application/vnd.google-apps.spreadsheet':     
                'application/vnd.ms-excel',
            'application/vnd.google-apps.presentation':    
                'application/vnd.ms-powerpoint',
            'application/vnd.google-apps.drawing':         
                'application/pdf',
            'application/vnd.google-apps.audio':           
                'audio/mpeg',
            'application/vnd.google-apps.photo':           
                'image/png',
            'application/vnd.google-apps.video':           
                'video/x-flv'
        }

    # Default extensions for mime-types.
    default_extensions = { 
            'text/plain':                       'txt',
            'application/vnd.ms-excel':         'xls',
            'application/vnd.ms-powerpoint':    'ppt',
            'application/pdf':                  'pdf',
            'audio/mpeg':                       'mp3',
            'image/png':                        'png',
            'video/x-flv':                      'flv'
        }

    local_character_set = getfilesystemencoding()

    def __init__(self):
        self.__load_mappings()

    def __load_mappings(self):
        # Allow someone to override our default mappings of the GD types.

        gd_to_normal_mapping_filepath = \
            Conf.get('gd_to_normal_mapping_filepath')

        try:
            with open(gd_to_normal_mapping_filepath, 'r') as f:
                self.gd_to_normal_mime_mappings.extend(json.load(f))
        except:
            logging.info("No mime-mapping was found.")

        # Allow someone to set file-extensions for mime-types, and not rely on 
        # Python's educated guesses.

        extension_mapping_filepath = Conf.get('extension_mapping_filepath')

        try:
            with open(extension_mapping_filepath, 'r') as f:
                self.default_extensions.extend(json.load(f))
        except:
            logging.info("No extension-mapping was found.")

    def get_first_mime_type_by_extension(self, extension):

        found = [ mime_type 
                    for mime_type, temp_extension 
                    in self.default_extensions.iteritems()
                    if temp_extension == extension ]

        if not found:
            return None

        return found[0]

    def translate_filename_charset(self, original_filename):
        """Convert the given filename to the correct character set."""

        # fusepy doesn't support the Python 2.x Unicode type. Expect a native
        # string (anything but a byte string).
        return original_filename
       
#        # If we're in an older version of Python that still defines the Unicode
#        # class and the filename isn't unicode, translate it.
#
#        try:
#            sys.modules['__builtin__'].unicode
#        except AttributeError:
#            pass
#        else:
#            if issubclass(original_filename.__class__, unicode) is False:
#                return unicode(original_filename)#original_filename.decode(self.local_character_set)
#
#        # It's already unicode. Don't do anything.
#        return original_filename

    def make_safe_for_filename(self, text):
        """Remove any filename-invalid characters."""
    
        return re.sub('[^a-z0-9\-_\.]+', '', text)

utility = _DriveUtility()


########NEW FILE########
__FILENAME__ = _version

# This file helps to compute a version number in source trees obtained from
# git-archive tarball (such as those provided by githubs download-from-tag
# feature). Distribution tarballs (build by setup.py sdist) and build
# directories (produced by setup.py build) will contain a much shorter file
# that just contains the computed version number.

# This file is released into the public domain. Generated by
# versioneer-0.10 (https://github.com/warner/python-versioneer)

# these strings will be replaced by git during git-archive
git_refnames = "$Format:%d$"
git_full = "$Format:%H$"


import subprocess
import sys
import errno


def run_command(commands, args, cwd=None, verbose=False, hide_stderr=False):
    assert isinstance(commands, list)
    p = None
    for c in commands:
        try:
            # remember shell=False, so use git.cmd on windows, not just git
            p = subprocess.Popen([c] + args, cwd=cwd, stdout=subprocess.PIPE,
                                 stderr=(subprocess.PIPE if hide_stderr
                                         else None))
            break
        except EnvironmentError:
            e = sys.exc_info()[1]
            if e.errno == errno.ENOENT:
                continue
            if verbose:
                print("unable to run %s" % args[0])
                print(e)
            return None
    else:
        if verbose:
            print("unable to find command, tried %s" % (commands,))
        return None
    stdout = p.communicate()[0].strip()
    if sys.version >= '3':
        stdout = stdout.decode()
    if p.returncode != 0:
        if verbose:
            print("unable to run %s (error)" % args[0])
        return None
    return stdout


import sys
import re
import os.path

def get_expanded_variables(versionfile_abs):
    # the code embedded in _version.py can just fetch the value of these
    # variables. When used from setup.py, we don't want to import
    # _version.py, so we do it with a regexp instead. This function is not
    # used from _version.py.
    variables = {}
    try:
        f = open(versionfile_abs,"r")
        for line in f.readlines():
            if line.strip().startswith("git_refnames ="):
                mo = re.search(r'=\s*"(.*)"', line)
                if mo:
                    variables["refnames"] = mo.group(1)
            if line.strip().startswith("git_full ="):
                mo = re.search(r'=\s*"(.*)"', line)
                if mo:
                    variables["full"] = mo.group(1)
        f.close()
    except EnvironmentError:
        pass
    return variables

def versions_from_expanded_variables(variables, tag_prefix, verbose=False):
    refnames = variables["refnames"].strip()
    if refnames.startswith("$Format"):
        if verbose:
            print("variables are unexpanded, not using")
        return {} # unexpanded, so not in an unpacked git-archive tarball
    refs = set([r.strip() for r in refnames.strip("()").split(",")])
    # starting in git-1.8.3, tags are listed as "tag: foo-1.0" instead of
    # just "foo-1.0". If we see a "tag: " prefix, prefer those.
    TAG = "tag: "
    tags = set([r[len(TAG):] for r in refs if r.startswith(TAG)])
    if not tags:
        # Either we're using git < 1.8.3, or there really are no tags. We use
        # a heuristic: assume all version tags have a digit. The old git %d
        # expansion behaves like git log --decorate=short and strips out the
        # refs/heads/ and refs/tags/ prefixes that would let us distinguish
        # between branches and tags. By ignoring refnames without digits, we
        # filter out many common branch names like "release" and
        # "stabilization", as well as "HEAD" and "master".
        tags = set([r for r in refs if re.search(r'\d', r)])
        if verbose:
            print("discarding '%s', no digits" % ",".join(refs-tags))
    if verbose:
        print("likely tags: %s" % ",".join(sorted(tags)))
    for ref in sorted(tags):
        # sorting will prefer e.g. "2.0" over "2.0rc1"
        if ref.startswith(tag_prefix):
            r = ref[len(tag_prefix):]
            if verbose:
                print("picking %s" % r)
            return { "version": r,
                     "full": variables["full"].strip() }
    # no suitable tags, so we use the full revision id
    if verbose:
        print("no suitable tags, using full revision id")
    return { "version": variables["full"].strip(),
             "full": variables["full"].strip() }

def versions_from_vcs(tag_prefix, root, verbose=False):
    # this runs 'git' from the root of the source tree. This only gets called
    # if the git-archive 'subst' variables were *not* expanded, and
    # _version.py hasn't already been rewritten with a short version string,
    # meaning we're inside a checked out source tree.

    if not os.path.exists(os.path.join(root, ".git")):
        if verbose:
            print("no .git in %s" % root)
        return {}

    GITS = ["git"]
    if sys.platform == "win32":
        GITS = ["git.cmd", "git.exe"]
    stdout = run_command(GITS, ["describe", "--tags", "--dirty", "--always"],
                         cwd=root)
    if stdout is None:
        return {}
    if not stdout.startswith(tag_prefix):
        if verbose:
            print("tag '%s' doesn't start with prefix '%s'" % (stdout, tag_prefix))
        return {}
    tag = stdout[len(tag_prefix):]
    stdout = run_command(GITS, ["rev-parse", "HEAD"], cwd=root)
    if stdout is None:
        return {}
    full = stdout.strip()
    if tag.endswith("-dirty"):
        full += "-dirty"
    return {"version": tag, "full": full}


def versions_from_parentdir(parentdir_prefix, root, verbose=False):
    # Source tarballs conventionally unpack into a directory that includes
    # both the project name and a version string.
    dirname = os.path.basename(root)
    if not dirname.startswith(parentdir_prefix):
        if verbose:
            print("guessing rootdir is '%s', but '%s' doesn't start with prefix '%s'" %
                  (root, dirname, parentdir_prefix))
        return None
    return {"version": dirname[len(parentdir_prefix):], "full": ""}

tag_prefix = ""
parentdir_prefix = "gdrivefs-"
versionfile_source = "gdrivefs/_version.py"

def get_versions(default={"version": "unknown", "full": ""}, verbose=False):
    # I am in _version.py, which lives at ROOT/VERSIONFILE_SOURCE. If we have
    # __file__, we can work backwards from there to the root. Some
    # py2exe/bbfreeze/non-CPython implementations don't do __file__, in which
    # case we can only use expanded variables.

    variables = { "refnames": git_refnames, "full": git_full }
    ver = versions_from_expanded_variables(variables, tag_prefix, verbose)
    if ver:
        return ver

    try:
        root = os.path.abspath(__file__)
        # versionfile_source is the relative path from the top of the source
        # tree (where the .git directory might live) to this file. Invert
        # this to find the root from __file__.
        for i in range(len(versionfile_source.split("/"))):
            root = os.path.dirname(root)
    except NameError:
        return default

    return (versions_from_vcs(tag_prefix, root, verbose)
            or versions_from_parentdir(parentdir_prefix, root, verbose)
            or default)


########NEW FILE########
__FILENAME__ = Conf
from unittest import TestCase, main

from gdrivefs.gdtool import Conf

class ConfTestCase(TestCase):
    """Test the Conf class."""

    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_config(self):
        """Test for the existence of all configuration keys."""

        keys = [ 'auth_temp_path',
                 'auth_cache_filename',
                 'auth_secrets_filepath',
                 'change_check_interval_s']
        try:
            for key in keys:
                Conf.get(key)
        except (Exception) as e:
            self.fail("Could not retrieve value for configuration key [%s]." % 
                      (key))

if __name__ == '__main__':
    main()


########NEW FILE########
__FILENAME__ = drive_proxy
from unittest import TestCase, main

from gdrivefs.gdtool import drive_proxy, AccountInfo
from gdrivefs.cache import EntryCache, PathRelations
from gdrivefs.utility import get_utility

class GetDriveTestCase(TestCase):
    """Test the _GdriveManager class via _GoogleProxy via get_drive()."""

    drive_proxy = None

    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_list_files(self):
        """Test the list_files() call on the Drive object."""

#        files = drive_proxy('list_files')

#        print(files)

    def test_list_files_by_parent_id(self):

        return

        entries = drive_proxy('list_files')

        from pprint import pprint
        import json
        with open('/tmp/entries', 'w') as f:
            for entry in entries:
                f.write("%s\n" % (json.dumps(entry.info)))

    def test_get_changes(self):

        from gdrivefs.change import get_change_manager
        get_change_manager().process_updates()

        import sys
        sys.exit()

        (largest_change_id, next_page_token, changes) = drive_proxy('list_changes')

        print("Largest Change ID: [%s]" % (largest_change_id))
        print("Next Page Token: [%s]" % (next_page_token))

        from pprint import pprint
        pprint(len(changes))
        print

        for change_id, (entry_id, was_deleted, entry) in changes.iteritems():
            print("%d> [%s] D:[%s] [%s]" % (change_id, entry_id, was_deleted, entry.title if entry else '<deleted>'))

#            pprint(change_id)
#            pprint(change_info)

#            import sys
#            sys.exit()
#            pprint("%s, %s, %s" % (type(change[0]), type(change[1]), type(change[2])))

    def test_get_parents_containing_id(self):

        return
        
        entry_id = u'11EIs1ZxCykme0FnAdY8Xm_ktUCQ9y5lHC3EwAKFsiFk'

        try:
            parent_ids = drive_proxy('get_parents_containing_id', 
                                     child_id=entry_id)
        except:
            logging.exception("Could not retrieve parents for child with ID "
                              "[%s]." % (entry_id))
            raise

        from pprint import pprint
        pprint(parent_ids)

    def test_download_file(self):

        return

        from gdrivefs.gdtool import drive_proxy
        http = drive_proxy('get_authed_http')

        normalized_entry = EntryCache.get_instance().cache.get('1DcIWAjj-pnSCXBQa3kHJQuL-QMRoopx8Yx_LVhfRigk')
        mime_type = 'text/plain'

        files = drive_proxy('download_to_local', normalized_entry=normalized_entry, mime_type=mime_type)

        return

        from pprint import pprint
        url = files[16].download_links[u'text/plain']
        pprint(url)

        data = http.request(url)
        response_headers = data[0]

        import re
        r = re.compile('Range')
        found = [("%s: %s" % (k, v)) for k, v in response_headers.iteritems() if r.match(k)]
        if found:
            print("Found: %s" % (", ".join(found)))

        print(">>>===============================================")
#        print(data[1][:200])
        print("<<<===============================================")

    def test_get_about(self):

        return

        entry_id_1 = u'11EIs1ZxCykme0FnAdY8Xm_ktUCQ9y5lHC3EwAKFsiFk'
        entry1 = EntryCache.get_instance().cache.get(entry_id_1)
#        result = PathRelations.get_instance().register_entry(entry1)

        entry_id_2 = u'0AJFt2OXeDBqSUk9PVA'
#        entry2 = EntryCache.get_instance().cache.get(entry_id_2)
#        result = PathRelations.get_instance().register_entry(entry2)

        path_relations = PathRelations.get_instance()

        #print(len(entry.parents))
#        path_relations.dump_ll()

#        print(AccountInfo().root_id)

#        path_relations.dump_entry_clause('0AJFt2OXeDBqSUk9PVA')
#        PathRelations.get_instance().dump_entry_clause('0B5Ft2OXeDBqSSmdIek1aajZtVDA')
#        return
#        entry_clause = path_relations.get_entry_clause_by_id(entry_id_1)
        #result = path_relations.find_path_components_goandget('/')

        result = path_relations.get_child_filenames_from_entry_id(entry_id_2)

        from pprint import pprint
        pprint(result)

#        result = EntryCache.get_instance().cache.get(u'11EIs1ZxCykme0FnAdY8Xm_ktUCQ9y5lHC3EwAKFsiFk')
#        result = EntryCache.get_instance().cache.get(u'11EIs1ZxCykme0FnAdY8Xm_ktUCQ9y5lHC3EwAKFsiFk')
#        result = EntryCache.get_instance().cache.get(u'11EIs1ZxCykme0FnAdY8Xm_ktUCQ9y5lHC3EwAKFsiFk')
#        result = EntryCache.get_instance().cache.get(u'11EIs1ZxCykme0FnAdY8Xm_ktUCQ9y5lHC3EwAKFsiFk')
#        print(result)
        return
        

#        result = AccountInfo().root_id

        #about = drive_proxy('get_about_info')

#        entries = drive_proxy('get_children_under_parent_id', parent_id=about.root_id)
        #entries = drive_proxy('get_parents_over_child_id', child_id=u'11EIs1ZxCykme0FnAdY8Xm_ktUCQ9y5lHC3EwAKFsiFk')


#        print(response[u'rootFolderId'])
        import pprint
#        pprint.pprint(response[u'importFormats'])
        pprint.pprint(result)

    def test_remove_entry(self):

        return

        from gdrivefs.cache import PathRelations

        path_relations = PathRelations.get_instance()
        entry_clause = path_relations.get_clause_from_path('HelloFax')

        filenames = path_relations.get_child_filenames_from_entry_id(entry_clause[3])
        
        root_id = u'0AJFt2OXeDBqSUk9PVA'
        middle_id = entry_clause[3]
        child_id = u'0B5Ft2OXeDBqSTmpjSHlVbEV5ajg'

#        from pprint import pprint
#        pprint(filenames)

#        path_relations.dump_entry_clause(middle_id)

        print("1: =============================")
        path_relations.dump_ll()
        print("2: =============================")
#        print("middle: %s" % (middle_id))
#        return

        path_relations.remove_entry_recursive(middle_id)
#        path_relations.remove_entry(middle_id)

        print("3: =============================")
        path_relations.dump_ll()

        return

        try:
            path_relations.dump_entry_clause(root_id)
        except:
            print("<No root.>")

        try:
            path_relations.dump_entry_clause(middle_id)
        except:
            print("<No middle.>")

        try:
            path_relations.dump_entry_clause(child_id)
        except:
            print("<No child.>")

    def test_insert_entry(self):

        import datetime
#        filename = ("NewFolder_%s" % (datetime.datetime.now().strftime("%H%M%S")))
#        entry = drive_proxy('create_directory', filename=filename)

        filename = ("NewFile_%s.txt" % (datetime.datetime.now().strftime("%H%M%S")))
        entry = drive_proxy('create_file', filename=filename, data_filepath='/tmp/tmpdata.txt', parents=[])

        print(entry.id)

if __name__ == '__main__':
    main()



########NEW FILE########
__FILENAME__ = get_cache
from unittest import TestCase, main

from gdrivefs.gdtool import get_cache, drive_proxy

class GetCacheTestCase(TestCase):
    """Test the _FileCache class via the get_cache() call."""

    file_cache  = None
    drive_proxy = None

    def setUp(self):
        self.file_cache = get_cache()

    def tearDown(self):

        # Clear the singletons.
        get_cache.file_cache    = None
        drive_proxy.gp          = None

        # Clear our reference.
        self.file_cache = None

#    def test_config(self):
#        files = drive_proxy('list_files')
#
#        for file_tuple in files:
#            (entry, filename)

if __name__ == '__main__':
    main()



########NEW FILE########
__FILENAME__ = versioneer

# Version: 0.10

"""
The Versioneer
==============

* like a rocketeer, but for versions!
* https://github.com/warner/python-versioneer
* Brian Warner
* License: Public Domain
* Compatible With: python2.6, 2.7, and 3.2, 3.3

[![Build Status](https://travis-ci.org/warner/python-versioneer.png?branch=master)](https://travis-ci.org/warner/python-versioneer)

This is a tool for managing a recorded version number in distutils-based
python projects. The goal is to remove the tedious and error-prone "update
the embedded version string" step from your release process. Making a new
release should be as easy as recording a new tag in your version-control
system, and maybe making new tarballs.


## Quick Install

* `pip install versioneer` to somewhere to your $PATH
* run `versioneer-installer` in your source tree: this installs `versioneer.py`
* follow the instructions below (also in the `versioneer.py` docstring)

## Version Identifiers

Source trees come from a variety of places:

* a version-control system checkout (mostly used by developers)
* a nightly tarball, produced by build automation
* a snapshot tarball, produced by a web-based VCS browser, like github's
  "tarball from tag" feature
* a release tarball, produced by "setup.py sdist", distributed through PyPI

Within each source tree, the version identifier (either a string or a number,
this tool is format-agnostic) can come from a variety of places:

* ask the VCS tool itself, e.g. "git describe" (for checkouts), which knows
  about recent "tags" and an absolute revision-id
* the name of the directory into which the tarball was unpacked
* an expanded VCS variable ($Id$, etc)
* a `_version.py` created by some earlier build step

For released software, the version identifier is closely related to a VCS
tag. Some projects use tag names that include more than just the version
string (e.g. "myproject-1.2" instead of just "1.2"), in which case the tool
needs to strip the tag prefix to extract the version identifier. For
unreleased software (between tags), the version identifier should provide
enough information to help developers recreate the same tree, while also
giving them an idea of roughly how old the tree is (after version 1.2, before
version 1.3). Many VCS systems can report a description that captures this,
for example 'git describe --tags --dirty --always' reports things like
"0.7-1-g574ab98-dirty" to indicate that the checkout is one revision past the
0.7 tag, has a unique revision id of "574ab98", and is "dirty" (it has
uncommitted changes.

The version identifier is used for multiple purposes:

* to allow the module to self-identify its version: `myproject.__version__`
* to choose a name and prefix for a 'setup.py sdist' tarball

## Theory of Operation

Versioneer works by adding a special `_version.py` file into your source
tree, where your `__init__.py` can import it. This `_version.py` knows how to
dynamically ask the VCS tool for version information at import time. However,
when you use "setup.py build" or "setup.py sdist", `_version.py` in the new
copy is replaced by a small static file that contains just the generated
version data.

`_version.py` also contains `$Revision$` markers, and the installation
process marks `_version.py` to have this marker rewritten with a tag name
during the "git archive" command. As a result, generated tarballs will
contain enough information to get the proper version.


## Installation

First, decide on values for the following configuration variables:

* `versionfile_source`:

  A project-relative pathname into which the generated version strings should
  be written. This is usually a `_version.py` next to your project's main
  `__init__.py` file. If your project uses `src/myproject/__init__.py`, this
  should be `src/myproject/_version.py`. This file should be checked in to
  your VCS as usual: the copy created below by `setup.py versioneer` will
  include code that parses expanded VCS keywords in generated tarballs. The
  'build' and 'sdist' commands will replace it with a copy that has just the
  calculated version string.

*  `versionfile_build`:

  Like `versionfile_source`, but relative to the build directory instead of
  the source directory. These will differ when your setup.py uses
  'package_dir='. If you have `package_dir={'myproject': 'src/myproject'}`,
  then you will probably have `versionfile_build='myproject/_version.py'` and
  `versionfile_source='src/myproject/_version.py'`.

* `tag_prefix`:

  a string, like 'PROJECTNAME-', which appears at the start of all VCS tags.
  If your tags look like 'myproject-1.2.0', then you should use
  tag_prefix='myproject-'. If you use unprefixed tags like '1.2.0', this
  should be an empty string.

* `parentdir_prefix`:

  a string, frequently the same as tag_prefix, which appears at the start of
  all unpacked tarball filenames. If your tarball unpacks into
  'myproject-1.2.0', this should be 'myproject-'.

This tool provides one script, named `versioneer-installer`. That script does
one thing: write a copy of `versioneer.py` into the current directory.

To versioneer-enable your project:

* 1: Run `versioneer-installer` to copy `versioneer.py` into the top of your
  source tree.

* 2: add the following lines to the top of your `setup.py`, with the
  configuration values you decided earlier:

        import versioneer
        versioneer.versionfile_source = 'src/myproject/_version.py'
        versioneer.versionfile_build = 'myproject/_version.py'
        versioneer.tag_prefix = '' # tags are like 1.2.0
        versioneer.parentdir_prefix = 'myproject-' # dirname like 'myproject-1.2.0'

* 3: add the following arguments to the setup() call in your setup.py:

        version=versioneer.get_version(),
        cmdclass=versioneer.get_cmdclass(),

* 4: now run `setup.py versioneer`, which will create `_version.py`, and
  will modify your `__init__.py` to define `__version__` (by calling a
  function from `_version.py`). It will also modify your `MANIFEST.in` to
  include both `versioneer.py` and the generated `_version.py` in sdist
  tarballs.

* 5: commit these changes to your VCS. To make sure you won't forget,
  `setup.py versioneer` will mark everything it touched for addition.

## Post-Installation Usage

Once established, all uses of your tree from a VCS checkout should get the
current version string. All generated tarballs should include an embedded
version string (so users who unpack them will not need a VCS tool installed).

If you distribute your project through PyPI, then the release process should
boil down to two steps:

* 1: git tag 1.0
* 2: python setup.py register sdist upload

If you distribute it through github (i.e. users use github to generate
tarballs with `git archive`), the process is:

* 1: git tag 1.0
* 2: git push; git push --tags

Currently, all version strings must be based upon a tag. Versioneer will
report "unknown" until your tree has at least one tag in its history. This
restriction will be fixed eventually (see issue #12).

## Version-String Flavors

Code which uses Versioneer can learn about its version string at runtime by
importing `_version` from your main `__init__.py` file and running the
`get_versions()` function. From the "outside" (e.g. in `setup.py`), you can
import the top-level `versioneer.py` and run `get_versions()`.

Both functions return a dictionary with different keys for different flavors
of the version string:

* `['version']`: condensed tag+distance+shortid+dirty identifier. For git,
  this uses the output of `git describe --tags --dirty --always` but strips
  the tag_prefix. For example "0.11-2-g1076c97-dirty" indicates that the tree
  is like the "1076c97" commit but has uncommitted changes ("-dirty"), and
  that this commit is two revisions ("-2-") beyond the "0.11" tag. For
  released software (exactly equal to a known tag), the identifier will only
  contain the stripped tag, e.g. "0.11".

* `['full']`: detailed revision identifier. For Git, this is the full SHA1
  commit id, followed by "-dirty" if the tree contains uncommitted changes,
  e.g. "1076c978a8d3cfc70f408fe5974aa6c092c949ac-dirty".

Some variants are more useful than others. Including `full` in a bug report
should allow developers to reconstruct the exact code being tested (or
indicate the presence of local changes that should be shared with the
developers). `version` is suitable for display in an "about" box or a CLI
`--version` output: it can be easily compared against release notes and lists
of bugs fixed in various releases.

In the future, this will also include a
[PEP-0440](http://legacy.python.org/dev/peps/pep-0440/) -compatible flavor
(e.g. `1.2.post0.dev123`). This loses a lot of information (and has no room
for a hash-based revision id), but is safe to use in a `setup.py`
"`version=`" argument. It also enables tools like *pip* to compare version
strings and evaluate compatibility constraint declarations.

The `setup.py versioneer` command adds the following text to your
`__init__.py` to place a basic version in `YOURPROJECT.__version__`:

    from ._version import get_versions
    __version = get_versions()['version']
    del get_versions

## Updating Versioneer

To upgrade your project to a new release of Versioneer, do the following:

* install the new Versioneer (`pip install -U versioneer` or equivalent)
* re-run `versioneer-installer` in your source tree to replace `versioneer.py`
* edit `setup.py`, if necessary, to include any new configuration settings indicated by the release notes
* re-run `setup.py versioneer` to replace `SRC/_version.py`
* commit any changed files

## Future Directions

This tool is designed to make it easily extended to other version-control
systems: all VCS-specific components are in separate directories like
src/git/ . The top-level `versioneer.py` script is assembled from these
components by running make-versioneer.py . In the future, make-versioneer.py
will take a VCS name as an argument, and will construct a version of
`versioneer.py` that is specific to the given VCS. It might also take the
configuration arguments that are currently provided manually during
installation by editing setup.py . Alternatively, it might go the other
direction and include code from all supported VCS systems, reducing the
number of intermediate scripts.


## License

To make Versioneer easier to embed, all its code is hereby released into the
public domain. The `_version.py` that it creates is also in the public
domain.

"""

import os, sys, re
from distutils.core import Command
from distutils.command.sdist import sdist as _sdist
from distutils.command.build import build as _build

versionfile_source = None
versionfile_build = None
tag_prefix = None
parentdir_prefix = None

VCS = "git"


LONG_VERSION_PY = '''
# This file helps to compute a version number in source trees obtained from
# git-archive tarball (such as those provided by githubs download-from-tag
# feature). Distribution tarballs (build by setup.py sdist) and build
# directories (produced by setup.py build) will contain a much shorter file
# that just contains the computed version number.

# This file is released into the public domain. Generated by
# versioneer-0.10 (https://github.com/warner/python-versioneer)

# these strings will be replaced by git during git-archive
git_refnames = "%(DOLLAR)sFormat:%%d%(DOLLAR)s"
git_full = "%(DOLLAR)sFormat:%%H%(DOLLAR)s"


import subprocess
import sys
import errno


def run_command(commands, args, cwd=None, verbose=False, hide_stderr=False):
    assert isinstance(commands, list)
    p = None
    for c in commands:
        try:
            # remember shell=False, so use git.cmd on windows, not just git
            p = subprocess.Popen([c] + args, cwd=cwd, stdout=subprocess.PIPE,
                                 stderr=(subprocess.PIPE if hide_stderr
                                         else None))
            break
        except EnvironmentError:
            e = sys.exc_info()[1]
            if e.errno == errno.ENOENT:
                continue
            if verbose:
                print("unable to run %%s" %% args[0])
                print(e)
            return None
    else:
        if verbose:
            print("unable to find command, tried %%s" %% (commands,))
        return None
    stdout = p.communicate()[0].strip()
    if sys.version >= '3':
        stdout = stdout.decode()
    if p.returncode != 0:
        if verbose:
            print("unable to run %%s (error)" %% args[0])
        return None
    return stdout


import sys
import re
import os.path

def get_expanded_variables(versionfile_abs):
    # the code embedded in _version.py can just fetch the value of these
    # variables. When used from setup.py, we don't want to import
    # _version.py, so we do it with a regexp instead. This function is not
    # used from _version.py.
    variables = {}
    try:
        f = open(versionfile_abs,"r")
        for line in f.readlines():
            if line.strip().startswith("git_refnames ="):
                mo = re.search(r'=\s*"(.*)"', line)
                if mo:
                    variables["refnames"] = mo.group(1)
            if line.strip().startswith("git_full ="):
                mo = re.search(r'=\s*"(.*)"', line)
                if mo:
                    variables["full"] = mo.group(1)
        f.close()
    except EnvironmentError:
        pass
    return variables

def versions_from_expanded_variables(variables, tag_prefix, verbose=False):
    refnames = variables["refnames"].strip()
    if refnames.startswith("$Format"):
        if verbose:
            print("variables are unexpanded, not using")
        return {} # unexpanded, so not in an unpacked git-archive tarball
    refs = set([r.strip() for r in refnames.strip("()").split(",")])
    # starting in git-1.8.3, tags are listed as "tag: foo-1.0" instead of
    # just "foo-1.0". If we see a "tag: " prefix, prefer those.
    TAG = "tag: "
    tags = set([r[len(TAG):] for r in refs if r.startswith(TAG)])
    if not tags:
        # Either we're using git < 1.8.3, or there really are no tags. We use
        # a heuristic: assume all version tags have a digit. The old git %%d
        # expansion behaves like git log --decorate=short and strips out the
        # refs/heads/ and refs/tags/ prefixes that would let us distinguish
        # between branches and tags. By ignoring refnames without digits, we
        # filter out many common branch names like "release" and
        # "stabilization", as well as "HEAD" and "master".
        tags = set([r for r in refs if re.search(r'\d', r)])
        if verbose:
            print("discarding '%%s', no digits" %% ",".join(refs-tags))
    if verbose:
        print("likely tags: %%s" %% ",".join(sorted(tags)))
    for ref in sorted(tags):
        # sorting will prefer e.g. "2.0" over "2.0rc1"
        if ref.startswith(tag_prefix):
            r = ref[len(tag_prefix):]
            if verbose:
                print("picking %%s" %% r)
            return { "version": r,
                     "full": variables["full"].strip() }
    # no suitable tags, so we use the full revision id
    if verbose:
        print("no suitable tags, using full revision id")
    return { "version": variables["full"].strip(),
             "full": variables["full"].strip() }

def versions_from_vcs(tag_prefix, root, verbose=False):
    # this runs 'git' from the root of the source tree. This only gets called
    # if the git-archive 'subst' variables were *not* expanded, and
    # _version.py hasn't already been rewritten with a short version string,
    # meaning we're inside a checked out source tree.

    if not os.path.exists(os.path.join(root, ".git")):
        if verbose:
            print("no .git in %%s" %% root)
        return {}

    GITS = ["git"]
    if sys.platform == "win32":
        GITS = ["git.cmd", "git.exe"]
    stdout = run_command(GITS, ["describe", "--tags", "--dirty", "--always"],
                         cwd=root)
    if stdout is None:
        return {}
    if not stdout.startswith(tag_prefix):
        if verbose:
            print("tag '%%s' doesn't start with prefix '%%s'" %% (stdout, tag_prefix))
        return {}
    tag = stdout[len(tag_prefix):]
    stdout = run_command(GITS, ["rev-parse", "HEAD"], cwd=root)
    if stdout is None:
        return {}
    full = stdout.strip()
    if tag.endswith("-dirty"):
        full += "-dirty"
    return {"version": tag, "full": full}


def versions_from_parentdir(parentdir_prefix, root, verbose=False):
    # Source tarballs conventionally unpack into a directory that includes
    # both the project name and a version string.
    dirname = os.path.basename(root)
    if not dirname.startswith(parentdir_prefix):
        if verbose:
            print("guessing rootdir is '%%s', but '%%s' doesn't start with prefix '%%s'" %%
                  (root, dirname, parentdir_prefix))
        return None
    return {"version": dirname[len(parentdir_prefix):], "full": ""}

tag_prefix = "%(TAG_PREFIX)s"
parentdir_prefix = "%(PARENTDIR_PREFIX)s"
versionfile_source = "%(VERSIONFILE_SOURCE)s"

def get_versions(default={"version": "unknown", "full": ""}, verbose=False):
    # I am in _version.py, which lives at ROOT/VERSIONFILE_SOURCE. If we have
    # __file__, we can work backwards from there to the root. Some
    # py2exe/bbfreeze/non-CPython implementations don't do __file__, in which
    # case we can only use expanded variables.

    variables = { "refnames": git_refnames, "full": git_full }
    ver = versions_from_expanded_variables(variables, tag_prefix, verbose)
    if ver:
        return ver

    try:
        root = os.path.abspath(__file__)
        # versionfile_source is the relative path from the top of the source
        # tree (where the .git directory might live) to this file. Invert
        # this to find the root from __file__.
        for i in range(len(versionfile_source.split("/"))):
            root = os.path.dirname(root)
    except NameError:
        return default

    return (versions_from_vcs(tag_prefix, root, verbose)
            or versions_from_parentdir(parentdir_prefix, root, verbose)
            or default)

'''


import subprocess
import sys
import errno


def run_command(commands, args, cwd=None, verbose=False, hide_stderr=False):
    assert isinstance(commands, list)
    p = None
    for c in commands:
        try:
            # remember shell=False, so use git.cmd on windows, not just git
            p = subprocess.Popen([c] + args, cwd=cwd, stdout=subprocess.PIPE,
                                 stderr=(subprocess.PIPE if hide_stderr
                                         else None))
            break
        except EnvironmentError:
            e = sys.exc_info()[1]
            if e.errno == errno.ENOENT:
                continue
            if verbose:
                print("unable to run %s" % args[0])
                print(e)
            return None
    else:
        if verbose:
            print("unable to find command, tried %s" % (commands,))
        return None
    stdout = p.communicate()[0].strip()
    if sys.version >= '3':
        stdout = stdout.decode()
    if p.returncode != 0:
        if verbose:
            print("unable to run %s (error)" % args[0])
        return None
    return stdout


import sys
import re
import os.path

def get_expanded_variables(versionfile_abs):
    # the code embedded in _version.py can just fetch the value of these
    # variables. When used from setup.py, we don't want to import
    # _version.py, so we do it with a regexp instead. This function is not
    # used from _version.py.
    variables = {}
    try:
        f = open(versionfile_abs,"r")
        for line in f.readlines():
            if line.strip().startswith("git_refnames ="):
                mo = re.search(r'=\s*"(.*)"', line)
                if mo:
                    variables["refnames"] = mo.group(1)
            if line.strip().startswith("git_full ="):
                mo = re.search(r'=\s*"(.*)"', line)
                if mo:
                    variables["full"] = mo.group(1)
        f.close()
    except EnvironmentError:
        pass
    return variables

def versions_from_expanded_variables(variables, tag_prefix, verbose=False):
    refnames = variables["refnames"].strip()
    if refnames.startswith("$Format"):
        if verbose:
            print("variables are unexpanded, not using")
        return {} # unexpanded, so not in an unpacked git-archive tarball
    refs = set([r.strip() for r in refnames.strip("()").split(",")])
    # starting in git-1.8.3, tags are listed as "tag: foo-1.0" instead of
    # just "foo-1.0". If we see a "tag: " prefix, prefer those.
    TAG = "tag: "
    tags = set([r[len(TAG):] for r in refs if r.startswith(TAG)])
    if not tags:
        # Either we're using git < 1.8.3, or there really are no tags. We use
        # a heuristic: assume all version tags have a digit. The old git %d
        # expansion behaves like git log --decorate=short and strips out the
        # refs/heads/ and refs/tags/ prefixes that would let us distinguish
        # between branches and tags. By ignoring refnames without digits, we
        # filter out many common branch names like "release" and
        # "stabilization", as well as "HEAD" and "master".
        tags = set([r for r in refs if re.search(r'\d', r)])
        if verbose:
            print("discarding '%s', no digits" % ",".join(refs-tags))
    if verbose:
        print("likely tags: %s" % ",".join(sorted(tags)))
    for ref in sorted(tags):
        # sorting will prefer e.g. "2.0" over "2.0rc1"
        if ref.startswith(tag_prefix):
            r = ref[len(tag_prefix):]
            if verbose:
                print("picking %s" % r)
            return { "version": r,
                     "full": variables["full"].strip() }
    # no suitable tags, so we use the full revision id
    if verbose:
        print("no suitable tags, using full revision id")
    return { "version": variables["full"].strip(),
             "full": variables["full"].strip() }

def versions_from_vcs(tag_prefix, root, verbose=False):
    # this runs 'git' from the root of the source tree. This only gets called
    # if the git-archive 'subst' variables were *not* expanded, and
    # _version.py hasn't already been rewritten with a short version string,
    # meaning we're inside a checked out source tree.

    if not os.path.exists(os.path.join(root, ".git")):
        if verbose:
            print("no .git in %s" % root)
        return {}

    GITS = ["git"]
    if sys.platform == "win32":
        GITS = ["git.cmd", "git.exe"]
    stdout = run_command(GITS, ["describe", "--tags", "--dirty", "--always"],
                         cwd=root)
    if stdout is None:
        return {}
    if not stdout.startswith(tag_prefix):
        if verbose:
            print("tag '%s' doesn't start with prefix '%s'" % (stdout, tag_prefix))
        return {}
    tag = stdout[len(tag_prefix):]
    stdout = run_command(GITS, ["rev-parse", "HEAD"], cwd=root)
    if stdout is None:
        return {}
    full = stdout.strip()
    if tag.endswith("-dirty"):
        full += "-dirty"
    return {"version": tag, "full": full}


def versions_from_parentdir(parentdir_prefix, root, verbose=False):
    # Source tarballs conventionally unpack into a directory that includes
    # both the project name and a version string.
    dirname = os.path.basename(root)
    if not dirname.startswith(parentdir_prefix):
        if verbose:
            print("guessing rootdir is '%s', but '%s' doesn't start with prefix '%s'" %
                  (root, dirname, parentdir_prefix))
        return None
    return {"version": dirname[len(parentdir_prefix):], "full": ""}
import os.path
import sys

# os.path.relpath only appeared in Python-2.6 . Define it here for 2.5.
def os_path_relpath(path, start=os.path.curdir):
    """Return a relative version of a path"""

    if not path:
        raise ValueError("no path specified")

    start_list = [x for x in os.path.abspath(start).split(os.path.sep) if x]
    path_list = [x for x in os.path.abspath(path).split(os.path.sep) if x]

    # Work out how much of the filepath is shared by start and path.
    i = len(os.path.commonprefix([start_list, path_list]))

    rel_list = [os.path.pardir] * (len(start_list)-i) + path_list[i:]
    if not rel_list:
        return os.path.curdir
    return os.path.join(*rel_list)

def do_vcs_install(manifest_in, versionfile_source, ipy):
    GITS = ["git"]
    if sys.platform == "win32":
        GITS = ["git.cmd", "git.exe"]
    files = [manifest_in, versionfile_source, ipy]
    try:
        me = __file__
        if me.endswith(".pyc") or me.endswith(".pyo"):
            me = os.path.splitext(me)[0] + ".py"
        versioneer_file = os_path_relpath(me)
    except NameError:
        versioneer_file = "versioneer.py"
    files.append(versioneer_file)
    present = False
    try:
        f = open(".gitattributes", "r")
        for line in f.readlines():
            if line.strip().startswith(versionfile_source):
                if "export-subst" in line.strip().split()[1:]:
                    present = True
        f.close()
    except EnvironmentError:
        pass    
    if not present:
        f = open(".gitattributes", "a+")
        f.write("%s export-subst\n" % versionfile_source)
        f.close()
        files.append(".gitattributes")
    run_command(GITS, ["add", "--"] + files)

SHORT_VERSION_PY = """
# This file was generated by 'versioneer.py' (0.10) from
# revision-control system data, or from the parent directory name of an
# unpacked source archive. Distribution tarballs contain a pre-generated copy
# of this file.

version_version = '%(version)s'
version_full = '%(full)s'
def get_versions(default={}, verbose=False):
    return {'version': version_version, 'full': version_full}

"""

DEFAULT = {"version": "unknown", "full": "unknown"}

def versions_from_file(filename):
    versions = {}
    try:
        f = open(filename)
    except EnvironmentError:
        return versions
    for line in f.readlines():
        mo = re.match("version_version = '([^']+)'", line)
        if mo:
            versions["version"] = mo.group(1)
        mo = re.match("version_full = '([^']+)'", line)
        if mo:
            versions["full"] = mo.group(1)
    f.close()
    return versions

def write_to_version_file(filename, versions):
    f = open(filename, "w")
    f.write(SHORT_VERSION_PY % versions)
    f.close()
    print("set %s to '%s'" % (filename, versions["version"]))

def get_root():
    try:
        return os.path.dirname(os.path.abspath(__file__))
    except NameError:
        return os.path.dirname(os.path.abspath(sys.argv[0]))

def get_versions(default=DEFAULT, verbose=False):
    # returns dict with two keys: 'version' and 'full'
    assert versionfile_source is not None, "please set versioneer.versionfile_source"
    assert tag_prefix is not None, "please set versioneer.tag_prefix"
    assert parentdir_prefix is not None, "please set versioneer.parentdir_prefix"
    # I am in versioneer.py, which must live at the top of the source tree,
    # which we use to compute the root directory. py2exe/bbfreeze/non-CPython
    # don't have __file__, in which case we fall back to sys.argv[0] (which
    # ought to be the setup.py script). We prefer __file__ since that's more
    # robust in cases where setup.py was invoked in some weird way (e.g. pip)
    root = get_root()
    versionfile_abs = os.path.join(root, versionfile_source)

    # extract version from first of _version.py, 'git describe', parentdir.
    # This is meant to work for developers using a source checkout, for users
    # of a tarball created by 'setup.py sdist', and for users of a
    # tarball/zipball created by 'git archive' or github's download-from-tag
    # feature.

    variables = get_expanded_variables(versionfile_abs)
    if variables:
        ver = versions_from_expanded_variables(variables, tag_prefix)
        if ver:
            if verbose: print("got version from expanded variable %s" % ver)
            return ver

    ver = versions_from_file(versionfile_abs)
    if ver:
        if verbose: print("got version from file %s %s" % (versionfile_abs,ver))
        return ver

    ver = versions_from_vcs(tag_prefix, root, verbose)
    if ver:
        if verbose: print("got version from git %s" % ver)
        return ver

    ver = versions_from_parentdir(parentdir_prefix, root, verbose)
    if ver:
        if verbose: print("got version from parentdir %s" % ver)
        return ver

    if verbose: print("got version from default %s" % ver)
    return default

def get_version(verbose=False):
    return get_versions(verbose=verbose)["version"]

class cmd_version(Command):
    description = "report generated version string"
    user_options = []
    boolean_options = []
    def initialize_options(self):
        pass
    def finalize_options(self):
        pass
    def run(self):
        ver = get_version(verbose=True)
        print("Version is currently: %s" % ver)


class cmd_build(_build):
    def run(self):
        versions = get_versions(verbose=True)
        _build.run(self)
        # now locate _version.py in the new build/ directory and replace it
        # with an updated value
        target_versionfile = os.path.join(self.build_lib, versionfile_build)
        print("UPDATING %s" % target_versionfile)
        os.unlink(target_versionfile)
        f = open(target_versionfile, "w")
        f.write(SHORT_VERSION_PY % versions)
        f.close()

if 'cx_Freeze' in sys.modules:  # cx_freeze enabled?
    from cx_Freeze.dist import build_exe as _build_exe

    class cmd_build_exe(_build_exe):
        def run(self):
            versions = get_versions(verbose=True)
            target_versionfile = versionfile_source
            print("UPDATING %s" % target_versionfile)
            os.unlink(target_versionfile)
            f = open(target_versionfile, "w")
            f.write(SHORT_VERSION_PY % versions)
            f.close()
            _build_exe.run(self)
            os.unlink(target_versionfile)
            f = open(versionfile_source, "w")
            f.write(LONG_VERSION_PY % {"DOLLAR": "$",
                                       "TAG_PREFIX": tag_prefix,
                                       "PARENTDIR_PREFIX": parentdir_prefix,
                                       "VERSIONFILE_SOURCE": versionfile_source,
                                       })
            f.close()

class cmd_sdist(_sdist):
    def run(self):
        versions = get_versions(verbose=True)
        self._versioneer_generated_versions = versions
        # unless we update this, the command will keep using the old version
        self.distribution.metadata.version = versions["version"]
        return _sdist.run(self)

    def make_release_tree(self, base_dir, files):
        _sdist.make_release_tree(self, base_dir, files)
        # now locate _version.py in the new base_dir directory (remembering
        # that it may be a hardlink) and replace it with an updated value
        target_versionfile = os.path.join(base_dir, versionfile_source)
        print("UPDATING %s" % target_versionfile)
        os.unlink(target_versionfile)
        f = open(target_versionfile, "w")
        f.write(SHORT_VERSION_PY % self._versioneer_generated_versions)
        f.close()

INIT_PY_SNIPPET = """
from ._version import get_versions
__version__ = get_versions()['version']
del get_versions
"""

class cmd_update_files(Command):
    description = "install/upgrade Versioneer files: __init__.py SRC/_version.py"
    user_options = []
    boolean_options = []
    def initialize_options(self):
        pass
    def finalize_options(self):
        pass
    def run(self):
        print(" creating %s" % versionfile_source)
        f = open(versionfile_source, "w")
        f.write(LONG_VERSION_PY % {"DOLLAR": "$",
                                   "TAG_PREFIX": tag_prefix,
                                   "PARENTDIR_PREFIX": parentdir_prefix,
                                   "VERSIONFILE_SOURCE": versionfile_source,
                                   })
        f.close()

        ipy = os.path.join(os.path.dirname(versionfile_source), "__init__.py")
        try:
            old = open(ipy, "r").read()
        except EnvironmentError:
            old = ""
        if INIT_PY_SNIPPET not in old:
            print(" appending to %s" % ipy)
            f = open(ipy, "a")
            f.write(INIT_PY_SNIPPET)
            f.close()
        else:
            print(" %s unmodified" % ipy)

        # Make sure both the top-level "versioneer.py" and versionfile_source
        # (PKG/_version.py, used by runtime code) are in MANIFEST.in, so
        # they'll be copied into source distributions. Pip won't be able to
        # install the package without this.
        manifest_in = os.path.join(get_root(), "MANIFEST.in")
        simple_includes = set()
        try:
            for line in open(manifest_in, "r").readlines():
                if line.startswith("include "):
                    for include in line.split()[1:]:
                        simple_includes.add(include)
        except EnvironmentError:
            pass
        # That doesn't cover everything MANIFEST.in can do
        # (http://docs.python.org/2/distutils/sourcedist.html#commands), so
        # it might give some false negatives. Appending redundant 'include'
        # lines is safe, though.
        if "versioneer.py" not in simple_includes:
            print(" appending 'versioneer.py' to MANIFEST.in")
            f = open(manifest_in, "a")
            f.write("include versioneer.py\n")
            f.close()
        else:
            print(" 'versioneer.py' already in MANIFEST.in")
        if versionfile_source not in simple_includes:
            print(" appending versionfile_source ('%s') to MANIFEST.in" %
                  versionfile_source)
            f = open(manifest_in, "a")
            f.write("include %s\n" % versionfile_source)
            f.close()
        else:
            print(" versionfile_source already in MANIFEST.in")

        # Make VCS-specific changes. For git, this means creating/changing
        # .gitattributes to mark _version.py for export-time keyword
        # substitution.
        do_vcs_install(manifest_in, versionfile_source, ipy)

def get_cmdclass():
    cmds = {'version': cmd_version,
            'versioneer': cmd_update_files,
            'build': cmd_build,
            'sdist': cmd_sdist,
            }
    if 'cx_Freeze' in sys.modules:  # cx_freeze enabled?
        cmds['build_exe'] = cmd_build_exe
        del cmds['build']

    return cmds

########NEW FILE########
