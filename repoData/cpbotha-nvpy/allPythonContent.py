__FILENAME__ = bindings
description = '''\
========== ==========
Key combo  Action
========== ==========
Ctrl-?     Display these key-bindings.
Ctrl-A     Select all text when in the note editor.
Ctrl-D     Move note to trash. This can be easily recovered using the
           simplenote webapp.
Ctrl-F     Start real-time incremental regular expression search. As you type,
           notes list is filtered. Up / down cursor keys go to
           previous / next note.
Ctrl-G     Edit tags for currently selected note. Press ESC to return to note
           editing.
Ctrl-M     Render Markdown note to HTML and open browser window.
Ctrl-N     Create new note.
Ctrl-Q     Exit nvPY.
Ctrl-R     Render reStructuredText (reST) note to HTML and open browser window.
Ctrl-S     Force sync of current note with simplenote server. Saving to disc
           and syncing to server also happen continuously in the background.
Ctrl-Y     Redo note edits.
Ctrl-Z     Undo note edits.
Ctrl-+/-   Increase or decrease the font size.
ESC        Go from edit mode to notes list.
ENTER      Start editing currently selected note. If there's a search string but
           no notes in the list, ENTER creates a new note with that search
           string as its title.
'''

########NEW FILE########
__FILENAME__ = notes_db
# nvPY: cross-platform note-taking app with simplenote syncing
# copyright 2012 by Charl P. Botha <cpbotha@vxlabs.com>
# new BSD license

import codecs
import copy
import glob
import os
import json
import logging
from Queue import Queue, Empty
import re
import simplenote
simplenote.NOTE_FETCH_LENGTH=100
from simplenote import Simplenote

from threading import Thread
import time
import utils

ACTION_SAVE = 0
ACTION_SYNC_PARTIAL_TO_SERVER = 1
ACTION_SYNC_PARTIAL_FROM_SERVER = 2 # UNUSED.

class SyncError(RuntimeError):
    pass

class ReadError(RuntimeError):
    pass

class WriteError(RuntimeError):
    pass

class NotesDB(utils.SubjectMixin):
    """NotesDB will take care of the local notes database and syncing with SN.
    """
    def __init__(self, config):
        utils.SubjectMixin.__init__(self)
        
        self.config = config
        
        # create db dir if it does not exist
        if not os.path.exists(config.db_path):
            os.mkdir(config.db_path)
            
        self.db_path = config.db_path

        # create txt Notes dir if it does not exist
        if self.config.notes_as_txt and not os.path.exists(config.txt_path):
            os.mkdir(config.txt_path)
        
        now = time.time()    
        # now read all .json files from disk
        fnlist = glob.glob(self.helper_key_to_fname('*'))
        txtlist = glob.glob(unicode(self.config.txt_path + '/*.txt', 'utf-8'))
        txtlist += glob.glob(unicode(self.config.txt_path + '/*.mkdn', 'utf-8'))

        # removing json files and force full full sync if using text files
        # and none exists and json files are there
        if self.config.notes_as_txt and not txtlist and fnlist:
            logging.debug('Forcing resync: using text notes, first usage')
            for fn in fnlist:
                os.unlink(fn)
            fnlist = []

        self.notes = {}
        if self.config.notes_as_txt:
            self.titlelist = {}

        for fn in fnlist:
            try:
                n = json.load(open(fn, 'rb'))
                if self.config.notes_as_txt:
                    nt = utils.get_note_title_file(n)
                    tfn = os.path.join(self.config.txt_path, nt)
                    if os.path.isfile(tfn):
                        self.titlelist[n.get('key')] = nt
                        txtlist.remove(tfn)
                        if os.path.getmtime(tfn) > os.path.getmtime(fn):
                            logging.debug('Text note was changed: %s' % (fn,))
                            with codecs.open(tfn, mode='rb', encoding='utf-8') as f:  
                                c = f.read()

                            n['content'] = c
                            n['modifydate'] = os.path.getmtime(tfn)
                    else:
                        logging.debug('Deleting note : %s' % (fn,))
                        if not self.config.simplenote_sync:
                            os.unlink(fn)
                            continue
                        else:
                            n['deleted'] = 1
                            n['modifydate'] = now

            except IOError, e:
                logging.error('NotesDB_init: Error opening %s: %s' % (fn, str(e)))
                raise ReadError ('Error opening note file')

            except ValueError, e:
                logging.error('NotesDB_init: Error reading %s: %s' % (fn, str(e)))
                raise ReadError ('Error reading note file')

            else:
                # we always have a localkey, also when we don't have a note['key'] yet (no sync)
                localkey = os.path.splitext(os.path.basename(fn))[0]
                self.notes[localkey] = n
                # we maintain in memory a timestamp of the last save
                # these notes have just been read, so at this moment
                # they're in sync with the disc.
                n['savedate'] = now
        
        if self.config.notes_as_txt:
            for fn in txtlist:
                logging.debug('New text note found : %s' % (fn),)
                tfn = os.path.join(self.config.txt_path, fn)
                try:
                    with codecs.open(tfn, mode='rb', encoding='utf-8') as f:  
                        c = f.read()

                except IOError, e:
                    logging.error('NotesDB_init: Error opening %s: %s' % (fn, str(e)))
                    raise ReadError ('Error opening note file')

                except ValueError, e:
                    logging.error('NotesDB_init: Error reading %s: %s' % (fn, str(e)))
                    raise ReadError ('Error reading note file')

                else:
                    nk = self.create_note(c)
                    nn = os.path.splitext(os.path.basename(fn))[0]
                    if nn != utils.get_note_title(self.notes[nk]):
                        self.notes[nk]['content'] = nn + "\n\n" + c

                    os.unlink(tfn)


        # save and sync queue
        self.q_save = Queue()
        self.q_save_res = Queue()

        thread_save = Thread(target=self.worker_save)
        thread_save.setDaemon(True)
        thread_save.start()

        # initialise the simplenote instance we're going to use
        # this does not yet need network access
        if self.config.simplenote_sync:
            self.simplenote = Simplenote(config.sn_username, config.sn_password)
        
            # we'll use this to store which notes are currently being synced by
            # the background thread, so we don't add them anew if they're still
            # in progress. This variable is only used by the background thread.
            self.threaded_syncing_keys = {}
        
            # reading a variable or setting this variable is atomic
            # so sync thread will write to it, main thread will only
            # check it sometimes.
            self.waiting_for_simplenote = False

            self.q_sync = Queue()
            self.q_sync_res = Queue()
        
            thread_sync = Thread(target=self.worker_sync)
            thread_sync.setDaemon(True)
            thread_sync.start()
        
    def create_note(self, title):
        # need to get a key unique to this database. not really important
        # what it is, as long as it's unique.
        new_key = utils.generate_random_key()
        while new_key in self.notes:
            new_key = utils.generate_random_key()
            
        timestamp = time.time()
            
        # note has no internal key yet.
        new_note = {
                    'content' : title,
                    'modifydate' : timestamp,
                    'createdate' : timestamp,
                    'savedate' : 0, # never been written to disc
                    'syncdate' : 0, # never been synced with server
                    'tags' : []
                    }
        
        self.notes[new_key] = new_note
        
        return new_key
    
    def delete_note(self, key):
        n = self.notes[key]
        n['deleted'] = 1
        n['modifydate'] = time.time()

    def filter_notes(self, search_string=None):
        """Return list of notes filtered with search string.

        Based on the search mode that has been selected in self.config,
        this method will call the appropriate helper method to do the
        actual work of filtering the notes.

        @param search_string: String that will be used for searching.
         Different meaning depending on the search mode.
        @return: notes filtered with selected search mode and sorted according
        to configuration. Two more elements in tuple: a regular expression
        that can be used for highlighting strings in the text widget; the
        total number of notes in memory.
        """

        if self.config.search_mode == 'regexp':
            filtered_notes, match_regexp, active_notes = self.filter_notes_regexp(search_string)
        else:
            filtered_notes, match_regexp, active_notes = self.filter_notes_gstyle(search_string)

        if self.config.sort_mode == 0:
            if self.config.pinned_ontop == 0:
                # sort alphabetically on title
                filtered_notes.sort(key=lambda o: utils.get_note_title(o.note))
            else:
                filtered_notes.sort(utils.sort_by_title_pinned)

        else:
            if self.config.pinned_ontop == 0:
                # last modified on top
                filtered_notes.sort(key=lambda o: -float(o.note.get('modifydate', 0)))
            else:
                filtered_notes.sort(utils.sort_by_modify_date_pinned, reverse=True)

        return filtered_notes, match_regexp, active_notes

    def _helper_gstyle_tagmatch(self, tag_pats, note):
        if tag_pats:
            tags = note.get('tags')

            # tag: patterns specified, but note has no tags, so no match
            if not tags:
                return 0

            # for each tag_pat, we have to find a matching tag
            for tp in tag_pats:
                # at the first match between tp and a tag:
                if next((tag for tag in tags if tag.startswith(tp)), None) is not None:
                    # we found a tag that matches current tagpat, so we move to the next tagpat
                    continue

                else:
                    # we found no tag that matches current tagpat, so we break out of for loop
                    break

            else:
                # for loop never broke out due to no match for tagpat, so:
                # all tag_pats could be matched, so note is a go.
                return 1


            # break out of for loop will have us end up here
            # for one of the tag_pats we found no matching tag
            return 0


        else:
            # match because no tag: patterns were specified
            return 2

    def _helper_gstyle_mswordmatch(self, msword_pats, content):
        """If all words / multi-words in msword_pats are found in the content,
        the note goes through, otherwise not.

        @param msword_pats:
        @param content:
        @return:
        """

        # no search patterns, so note goes through
        if not msword_pats:
            return True

        # search for the first p that does NOT occur in content
        if next((p for p in msword_pats if p not in content), None) is None:
            # we only found pats that DO occur in content so note goes through
            return True

        else:
            # we found the first p that does not occur in content
            return False



    def filter_notes_gstyle(self, search_string=None):

        filtered_notes = []
        # total number of notes, excluding deleted
        active_notes = 0

        if not search_string:
            for k in self.notes:
                n = self.notes[k]
                if not n.get('deleted'):
                    active_notes += 1
                    filtered_notes.append(utils.KeyValueObject(key=k, note=n, tagfound=0))

            return filtered_notes, [], active_notes

        # group0: ag - not used
        # group1: t(ag)?:([^\s]+)
        # group2: multiple words in quotes
        # group3: single words
        # example result for 't:tag1 t:tag2 word1 "word2 word3" tag:tag3' ==
        # [('', 'tag1', '', ''), ('', 'tag2', '', ''), ('', '', '', 'word1'), ('', '', 'word2 word3', ''), ('ag', 'tag3', '', '')]

        groups = re.findall('t(ag)?:([^\s]+)|"([^"]+)"|([^\s]+)', search_string)
        tms_pats = [[] for _ in range(3)]

        # we end up with [[tag_pats],[multi_word_pats],[single_word_pats]]
        for gi in groups:
            for mi in range(1,4):
                if gi[mi]:
                    tms_pats[mi-1].append(gi[mi])

        for k in self.notes:
            n = self.notes[k]

            if not n.get('deleted'):
                active_notes += 1
                c = n.get('content')

                # case insensitive mode: WARNING - SLOW!
                if not self.config.case_sensitive and c:
                    c = c.lower()

                tagmatch = self._helper_gstyle_tagmatch(tms_pats[0], n)
                # case insensitive mode: WARNING - SLOW!
                msword_pats = tms_pats[1] + tms_pats[2] if self.config.case_sensitive else [p.lower() for p in tms_pats[1] + tms_pats[2]]
                if tagmatch and self._helper_gstyle_mswordmatch(msword_pats, c):
                    # we have a note that can go through!

                    # tagmatch == 1 if a tag was specced and found
                    # tagmatch == 2 if no tag was specced (so all notes go through)
                    tagfound = 1 if tagmatch == 1 else 0
                    # we have to store our local key also
                    filtered_notes.append(utils.KeyValueObject(key=k, note=n, tagfound=tagfound))

        return filtered_notes, '|'.join(tms_pats[1] + tms_pats[2]), active_notes


    def filter_notes_regexp(self, search_string=None):
        """Return list of notes filtered with search_string, 
        a regular expression, each a tuple with (local_key, note). 
        """

        if search_string:
            try:
                if self.config.case_sensitive == 0:
                    sspat = re.compile(search_string, re.I)
                else:
                    sspat = re.compile(search_string)
            except re.error:
                sspat = None
            
        else:
            sspat = None

        filtered_notes = []
        # total number of notes, excluding deleted ones
        active_notes = 0
        for k in self.notes:
            n = self.notes[k]
            # we don't do anything with deleted notes (yet)
            if n.get('deleted'):
                continue

            active_notes += 1

            c = n.get('content')
            if self.config.search_tags == 1:
                t = n.get('tags')
                if sspat:
                    # this used to use a filter(), but that would by definition
                    # test all elements, whereas we can stop when the first
                    # matching element is found
                    # now I'm using this awesome trick by Alex Martelli on
                    # http://stackoverflow.com/a/2748753/532513
                    # first parameter of next is a generator
                    # next() executes one step, but due to the if, this will
                    # either be first matching element or None (second param)
                    if t and next((ti for ti in t if sspat.search(ti)), None) is not None:
                        # we have to store our local key also
                        filtered_notes.append(utils.KeyValueObject(key=k, note=n, tagfound=1))

                    elif sspat.search(c):
                        # we have to store our local key also
                        filtered_notes.append(utils.KeyValueObject(key=k, note=n, tagfound=0))

                else:
                    # we have to store our local key also
                    filtered_notes.append(utils.KeyValueObject(key=k, note=n, tagfound=0))
            else:
                if (not sspat or sspat.search(c)):
                    # we have to store our local key also
                    filtered_notes.append(utils.KeyValueObject(key=k, note=n, tagfound=0))

        match_regexp = search_string if sspat else ''

        return filtered_notes, match_regexp, active_notes

    def get_note(self, key):
        return self.notes[key]

    def get_note_content(self, key):
        return self.notes[key].get('content')
    
    def get_note_status(self, key):
        n = self.notes[key]
        o = utils.KeyValueObject(saved=False, synced=False, modified=False)
        modifydate = float(n['modifydate'])
        savedate = float(n['savedate'])
        
        if savedate > modifydate:
            o.saved = True
        else:
            o.modified = True
            
        if float(n['syncdate']) > modifydate:
            o.synced = True
            
        return o

    def get_save_queue_len(self):
        return self.q_save.qsize()

            
    def get_sync_queue_len(self):
        return self.q_sync.qsize()
        
    def helper_key_to_fname(self, k):
            return os.path.join(self.db_path, k) + '.json'
    
    def helper_save_note(self, k, note):
        """Save a single note to disc.
        
        """

        if self.config.notes_as_txt:
            t = utils.get_note_title_file(note)
            if t and not note.get('deleted'):
                if k in self.titlelist:
                    logging.debug('Writing note : %s %s' % (t,self.titlelist[k] ))
                    if self.titlelist[k] != t:
                        dfn = os.path.join(self.config.txt_path, self.titlelist[k])
                        if os.path.isfile(dfn):
                            logging.debug('Delete file %s ' % (dfn, ))
                            os.unlink(dfn)
                        else:
                            logging.debug('File not exits %s ' % (dfn, ))
                else:
                    logging.debug('Key not in list %s ' % (k, ))

                self.titlelist[k] = t
                fn = os.path.join(self.config.txt_path, t)
                try:
                    with codecs.open(fn, mode='wb', encoding='utf-8') as f:  
                        c = note.get('content')
                        if isinstance(c, str):
                            c = unicode(c, 'utf-8')
                        else:
                            c = unicode(c)
                        
                        f.write(c)
                except IOError, e:
                    logging.error('NotesDB_save: Error opening %s: %s' % (fn, str(e)))
                    raise WriteError ('Error opening note file')

                except ValueError, e:
                    logging.error('NotesDB_save: Error writing %s: %s' % (fn, str(e)))
                    raise WriteError ('Error writing note file')

            elif t and note.get('deleted') and k in self.titlelist:
                dfn = os.path.join(self.config.txt_path, self.titlelist[k])
                if os.path.isfile(dfn):
                    logging.debug('Delete file %s ' % (dfn, ))
                    os.unlink(dfn)
        
        fn = self.helper_key_to_fname(k)
        if not self.config.simplenote_sync and note.get('deleted'):
            if os.path.isfile(fn):
                os.unlink(fn)
        else:
            json.dump(note, open(fn, 'wb'), indent=2)

        # record that we saved this to disc.
        note['savedate'] = time.time()
        
    def sync_note_unthreaded(self, k):
        """Sync a single note with the server.

        Update existing note in memory with the returned data.  
        This is a sychronous (blocking) call.
        """

        note = self.notes[k]
        
        if not note.get('key') or float(note.get('modifydate')) > float(note.get('syncdate')):
            # if has no key, or it has been modified sync last sync, 
            # update to server
            uret = self.simplenote.update_note(note)

            if uret[1] == 0:
                # success!
                n = uret[0]
        
                # if content was unchanged, there'll be no content sent back!
                if n.get('content', None):
                    new_content = True
        
                else:
                    new_content = False
                    
                now = time.time()
                # 1. store when we've synced
                n['syncdate'] = now
                
                # update our existing note in-place!
                note.update(n)
        
                # return the key
                return (k, new_content)
                
            else:
                return None

            
        else:
            # our note is synced up, but we check if server has something new for us
            gret = self.simplenote.get_note(note['key'])
            
            if gret[1] == 0:
                n = gret[0]
                
                if int(n.get('syncnum')) > int(note.get('syncnum')):
                    n['syncdate'] = time.time()
                    note.update(n)
                    return (k, True)
                
                else:
                    return (k, False)

            else:
                return None

        
    def save_threaded(self):
        for k,n in self.notes.items():
            savedate = float(n.get('savedate'))
            if float(n.get('modifydate')) > savedate or \
               float(n.get('syncdate')) > savedate:
                cn = copy.deepcopy(n)
                # put it on my queue as a save
                o = utils.KeyValueObject(action=ACTION_SAVE, key=k, note=cn)
                self.q_save.put(o)
                
        # in this same call, we process stuff that might have been put on the result queue
        nsaved = 0
        something_in_queue = True
        while something_in_queue:
            try:
                o = self.q_save_res.get_nowait()
                
            except Empty:
                something_in_queue = False
                
            else:
                # o (.action, .key, .note) is something that was written to disk
                # we only record the savedate.
                self.notes[o.key]['savedate'] = o.note['savedate']
                self.notify_observers('change:note-status', utils.KeyValueObject(what='savedate',key=o.key))
                nsaved += 1
                
        return nsaved
        
    
    def sync_to_server_threaded(self, wait_for_idle=True):
        """Only sync notes that have been changed / created locally since previous sync.
        
        This function is called by the housekeeping handler, so once every
        few seconds.
        
        @param wait_for_idle: Usually, last modification date has to be more
        than a few seconds ago before a sync to server is attempted. If
        wait_for_idle is set to False, no waiting is applied. Used by exit
        cleanup in controller.
        
        """
        
        # this many seconds of idle time (i.e. modification this long ago)
        # before we try to sync.
        if wait_for_idle:
            lastmod = 3
        else:
            lastmod = 0
        
        now = time.time()
        for k,n in self.notes.items():
            # if note has been modified sinc the sync, we need to sync.
            # only do so if note hasn't been touched for 3 seconds
            # and if this note isn't still in the queue to be processed by the
            # worker (this last one very important)
            modifydate = float(n.get('modifydate', -1))
            syncdate = float(n.get('syncdate', -1))
            if modifydate > syncdate and \
               now - modifydate > lastmod and \
               k not in self.threaded_syncing_keys:
                # record that we've requested a sync on this note,
                # so that we don't keep on putting stuff on the queue.
                self.threaded_syncing_keys[k] = True
                cn = copy.deepcopy(n)
                # we store the timestamp when this copy was made as the syncdate
                cn['syncdate'] = time.time()
                # put it on my queue as a sync
                o = utils.KeyValueObject(action=ACTION_SYNC_PARTIAL_TO_SERVER, key=k, note=cn)
                self.q_sync.put(o)
                
        # in this same call, we read out the result queue
        nsynced = 0
        nerrored = 0
        something_in_queue = True
        while something_in_queue:
            try:
                o = self.q_sync_res.get_nowait()
                
            except Empty:
                something_in_queue = False
                
            else:
                okey = o.key

                if o.error:
                    nerrored += 1
                    
                else:
                    # o (.action, .key, .note) is something that was synced

                    # we only apply the changes if the syncdate is newer than
                    # what we already have, since the main thread could be
                    # running a full sync whilst the worker thread is putting
                    # results in the queue.
                    if float(o.note['syncdate']) > float(self.notes[okey]['syncdate']):
                                        
                        if float(o.note['syncdate']) > float(self.notes[okey]['modifydate']):
                            # note was synced AFTER the last modification to our local version
                            # do an in-place update of the existing note
                            # this could be with or without new content.
                            old_note = copy.deepcopy(self.notes[okey])
                            self.notes[okey].update(o.note)
                            # notify anyone (probably nvPY) that this note has been changed
                            self.notify_observers('synced:note', utils.KeyValueObject(lkey=okey, old_note=old_note))
                            
                        else:
                            # the user has changed stuff since the version that got synced
                            # just record syncnum and version that we got from simplenote
                            # if we don't do this, merging problems start happening.
                            # VERY importantly: also store the key. It
                            # could be that we've just created the
                            # note, but that the user continued
                            # typing. We need to store the new server
                            # key, else we'll keep on sending new
                            # notes.
                            tkeys = ['syncnum', 'version', 'syncdate', 'key']
                            for tk in tkeys:
                                self.notes[okey][tk] = o.note[tk]
                            
                        nsynced += 1
                        self.notify_observers('change:note-status', utils.KeyValueObject(what='syncdate',key=okey))
                    
                # after having handled the note that just came back,
                # we can take it from this blocker dict
                del self.threaded_syncing_keys[okey]

        return (nsynced, nerrored)
    
    
    def sync_full(self):
        """Perform a full bi-directional sync with server.
        
        This follows the recipe in the SimpleNote 2.0 API documentation.
        After this, it could be that local keys have been changed, so
        reset any views that you might have.
        """
        
        local_updates = {}
        local_deletes = {}
        now = time.time()

        self.notify_observers('progress:sync_full', utils.KeyValueObject(msg='Starting full sync.'))
        # 1. go through local notes, if anything changed or new, update to server
        for ni,lk in enumerate(self.notes.keys()):
            n = self.notes[lk]
            if not n.get('key') or float(n.get('modifydate')) > float(n.get('syncdate')):
                uret = self.simplenote.update_note(n)
                if uret[1] == 0:
                    # replace n with uret[0]
                    # if this was a new note, our local key is not valid anymore
                    del self.notes[lk]
                    # in either case (new or existing note), save note at assigned key
                    k = uret[0].get('key')
                    # we merge the note we got back (content coud be empty!)
                    n.update(uret[0])
                    # and put it at the new key slot
                    self.notes[k] = n
                    
                    # record that we just synced
                    uret[0]['syncdate'] = now
                    
                    # whatever the case may be, k is now updated
                    local_updates[k] = True
                    if lk != k:
                        # if lk was a different (purely local) key, should be deleted
                        local_deletes[lk] = True
                        
                    self.notify_observers('progress:sync_full', utils.KeyValueObject(msg='Synced modified note %d to server.' % (ni,)))
                        
                else:
                    raise SyncError("Sync step 1 error - Could not update note to server")
             
        # 2. if remote syncnum > local syncnum, update our note; if key is new, add note to local.
        # this gets the FULL note list, even if multiple gets are required
        self.notify_observers('progress:sync_full', utils.KeyValueObject(msg='Retrieving full note list from server, could take a while.'))       
        nl = self.simplenote.get_note_list()
        if nl[1] == 0:
            nl = nl[0]
            self.notify_observers('progress:sync_full', utils.KeyValueObject(msg='Retrieved full note list from server.'))
            
        else:
            raise SyncError('Could not get note list from server.')
        
        server_keys = {}
        lennl = len(nl)
        sync_from_server_errors = 0
        for ni,n in enumerate(nl):
            k = n.get('key')
            server_keys[k] = True
            # this works, only because in phase 1 we rewrite local keys to
            # server keys when we get an updated not back from the server
            if k in self.notes:
                # we already have this
                # check if server n has a newer syncnum than mine
                if int(n.get('syncnum')) > int(self.notes[k].get('syncnum', -1)):
                    # and the server is newer
                    ret = self.simplenote.get_note(k)
                    if ret[1] == 0:
                        self.notes[k].update(ret[0])
                        local_updates[k] = True
                        # in both cases, new or newer note, syncdate is now.
                        self.notes[k]['syncdate'] = now
                        self.notify_observers('progress:sync_full', utils.KeyValueObject(msg='Synced newer note %d (%d) from server.' % (ni,lennl)))

                    else:
                        logging.error('Error syncing newer note %s from server: %s' % (k, ret[0]))
                        sync_from_server_errors+=1

            else:
                # new note
                ret = self.simplenote.get_note(k)
                if ret[1] == 0:
                    self.notes[k] = ret[0]
                    local_updates[k] = True
                    # in both cases, new or newer note, syncdate is now.
                    self.notes[k]['syncdate'] = now
                    self.notify_observers('progress:sync_full', utils.KeyValueObject(msg='Synced new note %d (%d) from server.' % (ni,lennl)))

                else:
                    logging.error('Error syncing new note %s from server: %s' % (k, ret[0]))
                    sync_from_server_errors+=1

        # 3. for each local note not in server index, remove.     
        for lk in self.notes.keys():
            if lk not in server_keys:
                if self.config.notes_as_txt:
                    tfn = os.path.join(self.config.txt_path, utils.get_note_title_file(self.notes[lk]))
                    if os.path.isfile(tfn):
                        os.unlink(tfn)
                del self.notes[lk]
                local_deletes[lk] = True
                
        # sync done, now write changes to db_path
        for uk in local_updates.keys():
            try:
                self.helper_save_note(uk, self.notes[uk])

            except WriteError, e:
                raise WriteError(e)
            
        for dk in local_deletes.keys():
            fn = self.helper_key_to_fname(dk)
            if os.path.exists(fn):
                os.unlink(fn)

        self.notify_observers('progress:sync_full', utils.KeyValueObject(msg='Full sync complete.'))

        return sync_from_server_errors
        
    def set_note_content(self, key, content):
        n = self.notes[key]
        old_content = n.get('content')
        if content != old_content:
            n['content'] = content
            n['modifydate'] = time.time()
            self.notify_observers('change:note-status', utils.KeyValueObject(what='modifydate', key=key))

    def set_note_tags(self, key, tags):
        n = self.notes[key]
        old_tags = n.get('tags')
        tags = utils.sanitise_tags(tags)
        if tags != old_tags:
            n['tags'] = tags
            n['modifydate'] = time.time()
            self.notify_observers('change:note-status', utils.KeyValueObject(what='modifydate', key=key))

    def set_note_pinned(self, key, pinned):
        n = self.notes[key]
        old_pinned = utils.note_pinned(n)
        if pinned != old_pinned:
            if 'systemtags' not in n:
                n['systemtags'] = []

            systemtags = n['systemtags']

            if pinned:
                # which by definition means that it was NOT pinned
                systemtags.append('pinned')

            else:
                systemtags.remove('pinned')

            n['modifydate'] = time.time()
            self.notify_observers('change:note-status', utils.KeyValueObject(what='modifydate', key=key))


    def worker_save(self):
        while True:
            o = self.q_save.get()

            if o.action == ACTION_SAVE:
                # this will write the savedate into o.note
                # with filename o.key.json
                try:
                    self.helper_save_note(o.key, o.note)

                except WriteError, e:
                    logging.error('FATAL ERROR in access to file system')
                    print "FATAL ERROR: Check the nvpy.log"
                    os._exit(1) 

                else:
                    # put the whole thing back into the result q
                    # now we don't have to copy, because this thread
                    # is never going to use o again.
                    # somebody has to read out the queue...
                    self.q_save_res.put(o)
                
    def worker_sync(self):
        while True:
            o = self.q_sync.get()
            
            if o.action == ACTION_SYNC_PARTIAL_TO_SERVER:
                self.waiting_for_simplenote = True
                if 'key' in o.note:
                    logging.debug('Updating note %s (local key %s) to server.' % (o.note['key'], o.key))

                else:
                    logging.debug('Sending new note (local key %s) to server.' % (o.key,))
                    
                uret = self.simplenote.update_note(o.note)
                self.waiting_for_simplenote = False
                
                if uret[1] == 0:
                    # success!
                    n = uret[0]

                    if not n.get('content', None):
                        # if note has not been changed, we don't get content back
                        # delete our own copy too.
                        del o.note['content']
                        
                    logging.debug('Server replies with updated note ' + n['key'])
                        
                    # syncdate was set when the note was copied into our queue
                    # we rely on that to determine when a returned note should
                    # overwrite a note in the main list.
                        
                    # store the actual note back into o
                    # in-place update of our existing note copy
                    o.note.update(n)

                    # success!
                    o.error = 0
                    
                    # and put it on the result queue
                    self.q_sync_res.put(o)
                    
                else:
                    o.error = 1
                    self.q_sync_res.put(o)
                    

########NEW FILE########
__FILENAME__ = nvpy
#!/usr/bin/env python

# nvPY: cross-platform note-taking app with simplenote syncing
# copyright 2012 by Charl P. Botha <cpbotha@vxlabs.com>
# new BSD license

# inspired by notational velocity and nvALT, neither of which I've used,
# and ResophNotes, which I have used.

# full width horizontal bar at top to search
# left column with current results: name, mod date, summary, tags
# right column with text of currently selected note

# * typing in the search bar:
# - press enter: focus jumps to note if ANYTHING is selected. if nothing is
# selected, enter creates a new note with the current string as its name.
# - esc clears the search entry, esc again jumps to list
# - up and down changes currently selected list
# * in note conten area
# - esc goes back to notes list.

# http://www.scribd.com/doc/91277952/Simple-Note-API-v2-1-3
# this also has a sync algorithm!

# 1. finish implementing search
# 1.5. think about other storage formats. What if we want to store more? (cursor position and so on. sqlite?)
# 2. note editing
#   a) saving to disc: remember lmodified or whatever.
#   b) syncing with simplenote

# to check if we're online

import codecs
import ConfigParser
import logging
from logging.handlers import RotatingFileHandler
from notes_db import NotesDB, SyncError, ReadError, WriteError
import os
import sys
import time

from utils import KeyValueObject, SubjectMixin
import view
import webbrowser

try:
    import markdown
except ImportError:
    HAVE_MARKDOWN = False
else:
    HAVE_MARKDOWN = True

try:
    import docutils
    import docutils.core
except ImportError:
    HAVE_DOCUTILS = False
else:
    HAVE_DOCUTILS = True

VERSION = "0.9.4"

class Config:
    """
    @ivar files_read: list of config files that were parsed.
    @ivar ok: True if config files had a default section, False otherwise.
    """
    def __init__(self, app_dir):
        """
        @param app_dir: the directory containing nvpy.py
        """

        self.app_dir = app_dir
        # cross-platform way of getting home dir!
        # http://stackoverflow.com/a/4028943/532513
        home = os.path.abspath(os.path.expanduser('~'))
        defaults = {'app_dir' : app_dir,
                    'appdir' : app_dir,
                    'home' : home,
                    'notes_as_txt' : '0',
                    'housekeeping_interval' : '2',
                    'search_mode' : 'gstyle',
                    'case_sensitive' : '1',
                    'search_tags' : '1',
                    'sort_mode' : '1',
                    'pinned_ontop' : '1',
                    'db_path' : os.path.join(home, '.nvpy'),
                    'txt_path' : os.path.join(home, '.nvpy/notes'),
                    'font_family' : 'Courier', # monospaced on all platforms
                    'font_size' : '10',
                    'list_font_family' : 'Helvetica', # sans on all platforms
                    'list_font_family_fixed' : 'Courier', # monospace on all platforms
                    'list_font_size' : '10',
                    'layout' : 'horizontal',
                    'print_columns' : '0',
                    'background_color' : 'white',
                    'sn_username' : '',
                    'sn_password' : '',
                    'simplenote_sync' : '1',
                    # Filename or filepath to a css file used style the rendered
                    # output; e.g. nvpy.css or /path/to/my.css
                    'rest_css_path': None,
                   }

        cp = ConfigParser.SafeConfigParser(defaults)
        # later config files overwrite earlier files
        # try a number of alternatives
        self.files_read = cp.read([os.path.join(app_dir, 'nvpy.cfg'),
                                   os.path.join(home, 'nvpy.cfg'),
                                   os.path.join(home, '.nvpy.cfg'),
                                   os.path.join(home, '.nvpy'),
                                   os.path.join(home, '.nvpyrc')])

        cfg_sec = 'nvpy'

        if not cp.has_section(cfg_sec):
            cp.add_section(cfg_sec)
            self.ok = False

        else:
            self.ok = True

        # for the username and password, we don't want interpolation,
        # hence the raw parameter. Fixes
        # https://github.com/cpbotha/nvpy/issues/9
        self.sn_username = cp.get(cfg_sec, 'sn_username', raw=True)
        self.sn_password = cp.get(cfg_sec, 'sn_password', raw=True)
        self.simplenote_sync = cp.getint(cfg_sec, 'simplenote_sync')
        # make logic to find in $HOME if not set
        self.db_path = cp.get(cfg_sec, 'db_path')
        #  0 = alpha sort, 1 = last modified first
        self.notes_as_txt = cp.getint(cfg_sec, 'notes_as_txt')
        self.txt_path = os.path.join(home, cp.get(cfg_sec, 'txt_path'))
        self.search_mode = cp.get(cfg_sec, 'search_mode')
        self.case_sensitive = cp.getint(cfg_sec, 'case_sensitive')
        self.search_tags = cp.getint(cfg_sec, 'search_tags')
        self.sort_mode = cp.getint(cfg_sec, 'sort_mode')
        self.pinned_ontop = cp.getint(cfg_sec, 'pinned_ontop')
        self.housekeeping_interval = cp.getint(cfg_sec, 'housekeeping_interval')
        self.housekeeping_interval_ms = self.housekeeping_interval * 1000

        self.font_family = cp.get(cfg_sec, 'font_family')
        self.font_size = cp.getint(cfg_sec, 'font_size')

        self.list_font_family = cp.get(cfg_sec, 'list_font_family')
        self.list_font_family_fixed = cp.get(cfg_sec, 'list_font_family_fixed')
        self.list_font_size = cp.getint(cfg_sec, 'list_font_size')

        self.layout = cp.get(cfg_sec, 'layout')
        self.print_columns = cp.getint(cfg_sec, 'print_columns')

        self.background_color = cp.get(cfg_sec, 'background_color')

        self.rest_css_path = cp.get(cfg_sec, 'rest_css_path')


class NotesListModel(SubjectMixin):
    """
    @ivar list: List of (str key, dict note) objects.
    """
    def __init__(self):
        # call mixin ctor
        SubjectMixin.__init__(self)

        self.list = []
        self.match_regexps = []

    def set_list(self, alist):
        self.list = alist
        self.notify_observers('set:list', None)

    def get_idx(self, key):
        """Find idx for passed LOCAL key.
        """
        found = [i for i,e in enumerate(self.list) if e.key == key]
        if found:
            return found[0]

        else:
            return -1

class Controller:
    """Main application class.
    """

    def __init__(self):
        # setup appdir
        if hasattr(sys, 'frozen') and sys.frozen:
            self.appdir, _ = os.path.split(sys.executable)

        else:
            dirname = os.path.dirname(__file__)
            if dirname and dirname != os.curdir:
                self.appdir = dirname
            else:
                self.appdir = os.getcwd()

        # make sure it's the full path
        self.appdir = os.path.abspath(self.appdir)

        # should probably also look in $HOME
        self.config = Config(self.appdir)
        self.config.app_version = VERSION

        # configure logging module
        #############################

        # first create db directory if it doesn't exist yet.
        if not os.path.exists(self.config.db_path):
            os.mkdir(self.config.db_path)

        log_filename = os.path.join(self.config.db_path, 'nvpy.log')
        # file will get nuked when it reaches 100kB
        lhandler = RotatingFileHandler(log_filename, maxBytes=100000, backupCount=1)
        lhandler.setLevel(logging.DEBUG)
        lhandler.setFormatter(logging.Formatter(fmt='%(asctime)s - %(levelname)s - %(message)s'))
        # we get the root logger and configure it
        logger = logging.getLogger()
        logger.setLevel(logging.DEBUG)
        logger.addHandler(lhandler)
        # this will go to the root logger
        logging.debug('nvpy logging initialized')

        logging.debug('config read from %s' % (str(self.config.files_read),))

        if self.config.sn_username == '':
            self.config.simplenote_sync = 0

        css = self.config.rest_css_path
        if css:
            if css.startswith("~/"):
                # On Mac, paths that start with '~/' aren't found by path.exists
                css = css.replace(
                    "~", os.path.abspath(os.path.expanduser('~')), 1)
                self.config.rest_css_path = css
            if not os.path.exists(css):
                # Couldn't find the user-defined css file. Use docutils css instead.
                self.config.rest_css_path = None

        self.notes_list_model = NotesListModel()
        # create the interface
        self.view = view.View(self.config, self.notes_list_model)

        # read our database of notes into memory
        # and sync with simplenote.
        try:
           self.notes_db = NotesDB(self.config)

        except ReadError, e:
            emsg = "Please check nvpy.log.\n" + str(e)
            self.view.show_error('Sync error', emsg)
            exit(1)


        self.notes_db.add_observer('synced:note', self.observer_notes_db_synced_note)
        self.notes_db.add_observer('change:note-status', self.observer_notes_db_change_note_status)

        if self.config.simplenote_sync:
            self.notes_db.add_observer('progress:sync_full', self.observer_notes_db_sync_full)
            self.sync_full()

        # we want to be notified when the user does stuff
        self.view.add_observer('click:notelink',
                self.observer_view_click_notelink)
        self.view.add_observer('delete:note', self.observer_view_delete_note)
        self.view.add_observer('select:note', self.observer_view_select_note)
        self.view.add_observer('change:entry', self.observer_view_change_entry)
        self.view.add_observer('change:text', self.observer_view_change_text)
        self.view.add_observer('change:tags', self.observer_view_change_tags)
        self.view.add_observer('change:pinned', self.observer_view_change_pinned)
        self.view.add_observer('create:note', self.observer_view_create_note)
        self.view.add_observer('keep:house', self.observer_view_keep_house)
        self.view.add_observer('command:markdown',
                self.observer_view_markdown)
        self.view.add_observer('command:rest',
                self.observer_view_rest)

        if self.config.simplenote_sync:
            self.view.add_observer('command:sync_full', lambda v, et, e: self.sync_full())
            self.view.add_observer('command:sync_current_note', self.observer_view_sync_current_note)

        self.view.add_observer('close', self.observer_view_close)

        # setup UI to reflect our search mode and case sensitivity
        self.view.set_cs(self.config.case_sensitive, silent=True)
        self.view.set_search_mode(self.config.search_mode, silent=True)

        self.view.add_observer('change:cs', self.observer_view_change_cs)
        self.view.add_observer('change:search_mode', self.observer_view_change_search_mode)

        # nn is a list of (key, note) objects
        nn, match_regexp, active_notes = self.notes_db.filter_notes()
        # this will trigger the list_change event
        self.notes_list_model.set_list(nn)
        self.notes_list_model.match_regexp = match_regexp
        self.view.set_note_tally(len(nn), active_notes, len(self.notes_db.notes))

        # we'll use this to keep track of the currently selected note
        # we only use idx, because key could change from right under us.
        self.selected_note_idx = -1
        self.view.select_note(0)

    def get_selected_note_key(self):
        if self.selected_note_idx >= 0:
            return self.notes_list_model.list[self.selected_note_idx].key
        else:
            return None

    def main_loop(self):
        if not self.config.files_read:
            self.view.show_warning('No config file',
                                  'Could not read any configuration files. See https://github.com/cpbotha/nvpy for details.')

        elif not self.config.ok:
            wmsg = ('Please rename [default] to [nvpy] in %s. ' + \
                    'Config file format changed after nvPY 0.8.') % \
            (str(self.config.files_read),)
            self.view.show_warning('Rename config section', wmsg)

        self.view.main_loop()

    def observer_notes_db_change_note_status(self, notes_db, evt_type, evt):
        skey = self.get_selected_note_key()
        if skey == evt.key:
            self.view.set_note_status(self.notes_db.get_note_status(skey))

    def observer_notes_db_sync_full(self, notes_db, evt_type, evt):
        logging.debug(evt.msg)
        self.view.set_status_text(evt.msg)

    def observer_notes_db_synced_note(self, notes_db, evt_type, evt):
        """This observer gets called only when a note returns from
        a sync that's more recent than our most recent mod to that note.
        """

        selected_note_o = self.notes_list_model.list[self.selected_note_idx]
        # if the note synced back matches our currently selected note,
        # we overwrite.

        if selected_note_o.key == evt.lkey:
            if selected_note_o.note['content'] != evt.old_note['content']:
                self.view.mute_note_data_changes()
                # in this case, we want to keep the user's undo buffer so that they
                # can undo synced back changes if they would want to.
                self.view.set_note_data(selected_note_o.note, reset_undo=False)
                self.view.unmute_note_data_changes()

    def observer_view_click_notelink(self, view, evt_type, note_name):
        # find note_name in titles, try to jump to that note
        # if not in current list, change search string in case
        # it's somewhere else
        # FIXME: implement find_note_by_name
        idx = self.view.select_note_by_name(note_name)

        if idx < 0:
            # this means a note with that name was not found
            # because nvpy kicks ass, it then assumes the contents of [[]]
            # to be a new regular expression to search for in the notes db.
            self.view.set_search_entry_text(note_name)

    def observer_view_delete_note(self, view, evt_type, evt):
        # delete note from notes_db
        # remove the note from the notes_list_model.list

        # if these two are not equal, something is not kosher.
        assert(evt.sel == self.selected_note_idx)

        # first get key of note that is to be deleted
        key = self.get_selected_note_key()

        # then try to select after the one that is to be deleted
        nidx = evt.sel + 1
        if nidx >= 0 and nidx < self.view.get_number_of_notes():
            self.view.select_note(nidx)

        # finally delete the note
        self.notes_db.delete_note(key)

        # easiest now is just to regenerate the list by resetting search string
        # if the note after the deleted one is already selected, this will
        # simply keep that selection!
        self.view.set_search_entry_text(self.view.get_search_entry_text())


    def helper_markdown_to_html(self):
        if self.selected_note_idx >= 0:
            key = self.notes_list_model.list[self.selected_note_idx].key
            c = self.notes_db.get_note_content(key)
            logging.debug("Trying to convert %s to html." % (key,))
            if HAVE_MARKDOWN:
                logging.debug("Convert note %s to html." % (key,))
                html = markdown.markdown(c)
                logging.debug("Convert done.")

            else:
                logging.debug("Markdown not installed.")
                html = "<p>python markdown not installed, required for rendering to HTML.</p>"
                html += "<p>Please install with \"pip install markdown\".</p>"

            # create filename based on key
            fn = os.path.join(self.config.db_path, key + '.html')
            f = codecs.open(fn, mode='wb', encoding='utf-8')
            s = u"""
<html>
<head>
<meta http-equiv="Content-Type" content="text/html; charset=UTF-8"/>
<meta http-equiv="refresh" content="5">
</head>
<body>
%s
</body>
</html>
            """ % (html,)
            f.write(s)
            f.close()
            return fn

    def helper_rest_to_html(self):
        if self.selected_note_idx >= 0:
            key = self.notes_list_model.list[self.selected_note_idx].key
            c = self.notes_db.get_note_content(key)
            if HAVE_DOCUTILS:
                settings = {}
                if self.config.rest_css_path:
                    settings['stylesheet_path'] = self.config.rest_css_path
                # this gives the whole document
                html = docutils.core.publish_string(
                    c, writer_name='html', settings_overrides=settings)
                # publish_parts("*anurag*",writer_name='html')['body']
                # gives just the desired part of the tree

            else:
                html = "<p>python docutils not installed, required for rendering reST to HTML.</p>"
                html += "<p>Please install with \"pip install docutils\".</p>"

            # create filename based on key
            fn = os.path.join(self.config.db_path, key + '_rest.html')
            f = codecs.open(fn, mode='wb', encoding='utf-8')

            # explicit decode from utf8 into unicode object. If we don't
            # specify utf8, python falls back to default ascii and then we get
            # "'ascii' codec can't decode byte" error
            s = u"""
%s
            """ % (unicode(html, 'utf8'),)

            f.write(s)
            f.close()
            return fn

    def observer_view_markdown(self, view, evt_type, evt):
        fn = self.helper_markdown_to_html()
        # turn filename into URI (mac wants this)
        fn_uri = 'file://' + os.path.abspath(fn)
        webbrowser.open(fn_uri)

    def observer_view_rest(self, view, evt_type, evt):
        fn = self.helper_rest_to_html()
        # turn filename into URI (mac wants this)
        fn_uri = 'file://' + os.path.abspath(fn)
        webbrowser.open(fn_uri)

    def helper_save_sync_msg(self):

        # Saving 2 notes. Syncing 3 notes, waiting for simplenote server.
        # All notes saved. All notes synced.

        saven = self.notes_db.get_save_queue_len()

        if self.config.simplenote_sync:
            syncn = self.notes_db.get_sync_queue_len()
            wfsn = self.notes_db.waiting_for_simplenote
        else:
            syncn = wfsn = 0

        savet = 'Saving %d notes.' % (saven,) if saven > 0 else '';
        synct = 'Waiting to sync %d notes.' % (syncn,) if syncn > 0 else '';
        wfsnt = 'Syncing with simplenote server.' if wfsn else '';

        return ' '.join([i for i in [savet, synct, wfsnt] if i])


    def observer_view_keep_house(self, view, evt_type, evt):
        # queue up all notes that need to be saved
        nsaved = self.notes_db.save_threaded()
        msg = self.helper_save_sync_msg()

        if self.config.simplenote_sync:
            nsynced, sync_errors = self.notes_db.sync_to_server_threaded()
            if sync_errors:
                msg = ' '.join([i for i in [msg, 'Could not connect to simplenote server.'] if i])

        self.view.set_status_text(msg)

        # in continous rendering mode, we also generate a new HTML
        # the browser, if open, will refresh!
        if self.view.get_continuous_rendering():
            self.helper_markdown_to_html()

    def observer_view_select_note(self, view, evt_type, evt):
        self.select_note(evt.sel)

    def observer_view_sync_current_note(self, view, evt_type, evt):
        if self.selected_note_idx >= 0:
            key = self.notes_list_model.list[self.selected_note_idx].key
            # this call will update our in-memory version if necessary
            ret = self.notes_db.sync_note_unthreaded(key)
            if ret and ret[1] == True:
                self.view.update_selected_note_data(
                        self.notes_db.notes[key])
                self.view.set_status_text(
                'Synced updated note from server.')

            elif ret[1] == False:
                self.view.set_status_text(
                        'Server had nothing newer for this note.')

            elif ret is None:
                self.view.set_status_text(
                        'Unable to sync with server. Offline?')

    def observer_view_change_cs(self, view, evt_type, evt):
        # evt.value is the new value
        # only do something if user has really toggled
        if evt.value != self.config.case_sensitive:
            self.config.case_sensitive = evt.value
            self.view.refresh_notes_list()

    def observer_view_change_search_mode(self, view, evt_type, evt):
        if evt.value != self.config.search_mode:
            self.config.search_mode = evt.value
            self.view.refresh_notes_list()

    def observer_view_change_entry(self, view, evt_type, evt):
        # store the currently selected note key
        k = self.get_selected_note_key()
        # for each new evt.value coming in, get a new list from the notes_db
        # and set it in the notes_list_model
        nn, match_regexp, active_notes = self.notes_db.filter_notes(evt.value)
        self.notes_list_model.set_list(nn)
        self.notes_list_model.match_regexp = match_regexp
        self.view.set_note_tally(len(nn), active_notes, len(self.notes_db.notes))

        idx = self.notes_list_model.get_idx(k)

        if idx < 0:
            self.view.select_note(0)
            # the user is typing, but her previously selected note is
            # not in the new filtered list. as a convenience, we move
            # the text in the text widget so it's on the first
            # occurrence of the search string, IF there's such an
            # occurrence.
            self.view.see_first_search_instance()

        else:
            # we don't want new text to be implanted (YET) so we keep this silent
            # if it does turn out to be new note content, this will be handled
            # a few lines down.
            self.view.select_note(idx, silent=True)
            # but of course we DO have to record the possibly new IDX!!
            self.selected_note_idx = idx

            # see if the note has been updated (content, tags, pin)
            new_note = self.notes_db.get_note(k)

            # check if the currently selected note is different from the one
            # currently being displayed. this could happen if a sync gets
            # a new note of the server to replace the currently displayed one.
            if self.view.is_note_different(new_note):
                logging.debug("Currently selected note %s replaced by newer from server." % (k,))
                # carefully update currently selected note
                # restore cursor position, search and link highlights
                self.view.update_selected_note_data(new_note)

            else:
                # we have a new search string, but did not make any text changes
                # so we have to update the search highlighting here. (usually
                # text changes trigger this)
                self.view.activate_search_string_highlights()




    def observer_view_change_text(self, view, evt_type, evt):
        # get new text and update our database
        # need local key of currently selected note for this
        if self.selected_note_idx >= 0:
            key = self.notes_list_model.list[self.selected_note_idx].key
            self.notes_db.set_note_content(key,
                                           self.view.get_text())

    def observer_view_change_tags(self, view, evt_type, evt):
        # get new text and update our database
        # need local key of currently selected note for this
        if self.selected_note_idx >= 0:
            key = self.notes_list_model.list[self.selected_note_idx].key
            self.notes_db.set_note_tags(key, evt.value)

    def observer_view_change_pinned(self, view, evt_type, evt):
        # get new text and update our database
        # need local key of currently selected note for this
        if self.selected_note_idx >= 0:
            key = self.notes_list_model.list[self.selected_note_idx].key
            self.notes_db.set_note_pinned(key, evt.value)

    def observer_view_close(self, view, evt_type, evt):
        # check that everything has been saved and synced before exiting

        # first make sure all our queues are up to date
        self.notes_db.save_threaded()
        if self.config.simplenote_sync:
            self.notes_db.sync_to_server_threaded(wait_for_idle=False)
            syncn = self.notes_db.get_sync_queue_len()
            wfsn = self.notes_db.waiting_for_simplenote
        else:
            syncn = wfsn = 0

        # then check all queues
        saven = self.notes_db.get_save_queue_len()

        # if there's still something to do, warn the user.
        if saven or syncn or wfsn:
            msg = "Are you sure you want to exit? I'm still busy: " + self.helper_save_sync_msg()
            really_want_to_exit = self.view.askyesno("Confirm exit", msg)

            if really_want_to_exit:
                self.view.close()

        else:
            self.view.close()

    def observer_view_create_note(self, view, evt_type, evt):
        # create the note
        new_key = self.notes_db.create_note(evt.title)
        # clear the search entry, this should trigger a new list being returned
        self.view.set_search_entry_text('')
        # we should focus on our thingy
        idx = self.notes_list_model.get_idx(new_key)
        self.view.select_note(idx)

    def select_note(self, idx):
        """Called whenever user selects a different note via the UI.

        This sets all machinery in motion to put the now note's data in all
        the right places.

        @param idx:
        @return:
        """

        if idx >= 0:
            key = self.notes_list_model.list[idx].key
            note = self.notes_db.get_note(key)
            # valid note, so note editing should be enabled
            self.view.set_note_editing(True)

        else:
            key = None
            note = None
            idx = -1
            # no note selected, so we clear the UI (and display a clear
            # message that no note is selected) and we disable note
            # editing controls.
            self.view.clear_note_ui()
            self.view.set_note_editing(False)


        self.selected_note_idx = idx

        # when we do this, we don't want the change:{text,tags,pinned} events
        # because those should only fire when they are changed through the UI
        self.view.mute_note_data_changes()
        self.view.set_note_data(note)
        if key:
            self.view.set_note_status(self.notes_db.get_note_status(key))

        self.view.unmute_note_data_changes()

    def sync_full(self):
        try:
            sync_from_server_errors = self.notes_db.sync_full()

        except SyncError, e:
            self.view.show_error('Sync error', e)
        except WriteError, e:
            emsg = "Please check nvpy.log.\n" + str(e)
            self.view.show_error('Sync error', emsg)
            exit(1)

        else:
            # regenerate display list
            # reselect old selection
            # put cursor where it used to be.
            self.view.refresh_notes_list()

            if sync_from_server_errors > 0:
                self.view.show_error('Error syncing notes from server', 'Error syncing %d notes from server. Please check nvpy.log for details.' % (sync_from_server_errors,))


def main():
    controller = Controller()
    controller.main_loop()


if __name__ == '__main__':
    main()


########NEW FILE########
__FILENAME__ = search_entry
# pretty style for entry widget, adapted from 
# http://python-ttk.googlecode.com/svn/trunk/pyttk-samples/mac_searchentry.py

"""Mac style search widget

Translated from Tcl code by Schelte Bron, http://wiki.tcl.tk/18188"""

try:
    import Tkinter
except ImportError:
    import tkinter as Tkinter

import ttk

data = """
R0lGODlhKgAaAOfnAFdZVllbWFpcWVtdWlxeW11fXF9hXmBiX2ZnZWhpZ2lraGxua25wbXJ0
cXR2c3V3dHZ4dXh6d3x+e31/fH6AfYSGg4eJhoiKh4qMiYuNio2PjHmUqnqVq3yXrZGTkJKU
kX+asJSWk32cuJWXlIGcs5aYlX6euZeZloOetZial4SftpqbmIWgt4GhvYahuIKivpudmYei
uYOjv5yem4ijuoSkwIWlwYmlu56gnYamwp+hnoenw4unvaCin4ioxJCnuZykrImpxZmlsoaq
zI2pv6KkoZGouoqqxpqms4erzaOloo6qwYurx5Kqu5untIiszqSmo5CrwoysyJeqtpOrvJyo
tZGsw42typSsvaaopZKtxJWtvp6qt4+uy6epppOuxZCvzKiqp5quuZSvxoyx06mrqJWwx42y
1JKxzpmwwaqsqZaxyI6z1ZqxwqutqpOzz4+01qyuq56yvpizypS00Jm0y5W10Zq1zJa20rCy
rpu3zqizwbGzr6C3yZy4z7K0saG4yp250LO1sqK5y5660Z+70qO7zKy4xaC806S8zba4taG9
1KW9zq66x6+7yLi6t6S/1rC8yrm7uLO8xLG9y7q8ubS9xabB2anB07K+zLW+xrO/za7CzrTA
zrjAyLXBz77BvbbC0K/G2LjD0bnE0rLK28TGw8bIxcLL07vP28HN28rMycvOyr/T38DU4cnR
2s/RztHT0NLU0cTY5MrW5MvX5dHX2c3Z59bY1dPb5Nbb3dLe7Nvd2t3f3NXh797g3d3j5dnl
9OPl4eTm4+Ln6tzo9uXn5Obo5eDp8efp5uHq8uXq7ejq5+nr6OPs9Ovu6unu8O3v6+vw8+7w
7ezx9O/x7vDy7/Hz8O/19/P18vT38/L3+fb49Pf59vX6/fj69/b7/vn7+Pr8+ff9//v9+vz/
+/7//P//////////////////////////////////////////////////////////////////
/////////////////////////////////yH/C05FVFNDQVBFMi4wAwEAAAAh+QQJZAD/ACwC
AAIAKAAWAAAI/gD/CRz4bwUGCg8eQFjIsGHDBw4iTLAQgqBFgisuePCiyJOpUyBDihRpypMi
Lx8qaLhIMIyGFZ5sAUsmjZrNmzhzWpO2DJgtTysqfGDpxoMbW8ekeQsXzty4p1CjRjUXrps3
asJsuclQ4uKKSbamMR3n1JzZs2jRkh1HzuxVXX8y4CDYAwqua+DInVrRwMGJU2kDp31KThy1
XGWGDlxhi1rTPAUICBBAoEAesoIzn6Vm68MKgVAUHftmzhOCBCtQwQKSoABgzZnJdSMmyIPA
FbCotdUQAIhNa9B6DPCAGbZac+SowVIMRVe4pwkA4GpqDlwuAAmMZx4nTtfnf1mO5JEDNy46
MHJkxQEDgKC49rPjwC0bqGaZuOoZAKjBPE4NgAzUvYcWOc0QZF91imAnCDHJ5JFAAJN0I2Ba
4iRDUC/gOEVNDwIUcEABCAgAAATUTIgWOMBYRFp80ghiAQIIVAAEAwJIYI2JZnUji0XSYAYO
NcsQA8wy0hCTwAASXGOiONFcxAtpTokTHznfiLMNMAkcAMuE43jDC0vLeGOWe2R5o4sn1LgH
GzkWsvTPMgEOaA433Ag4TjjMuDkQMNi0tZ12sqWoJ0HATMPNffAZZ6U0wLAyqJ62RGoLLrhI
aqmlpzwaEAAh+QQJZAD/ACwAAAAAKgAaAAAI/gD/CRw40JEhQoEC+fGjcOHCMRAjRkxDsKLF
f5YcAcID582ZjyBDJhmZZIjJIUySEDHiBMhFghrtdNnRAgSHmzhz6sTZQcSLITx+CHn5bxSk
Nz5MCMGy55CjTVCjbuJEtSrVQ3uwqDBRQwrFi476SHHxow8qXcemVbPGtm21t3CnTaP27Jgu
VHtuiIjBsuImQkRiiEEFTNo2cOTMKV7MuLE5cN68QUOGSgwKG1EqJqJDY8+rZt8UjxtNunTj
cY3DgZOWS46KIFgGjiI0ZIsqaqNNjWjgYMUpx8Adc3v2aosNMAI1DbqyI9WycOb4IAggQEAB
A3lQBxet/TG4cMpI/tHwYeSfIzxM0uTKNs7UgAQrYL1akaDA7+3bueVqY4NJlUhIcQLNYx8E
AIQ01mwjTQ8DeNAdfouNA8440GBCQxJY3MEGD6p4Y844CQCAizcSgpMLAAlAuJ03qOyQRBR3
nEHEK+BMGKIui4kDDAAIPKiiYuSYSMQQRCDCxhiziPMYBgDkEaEaAGQA3Y+MjUPOLFoMoUUh
cKxRC4ngeILiH8Qkk0cCAUzSDZWpzbLEE1EwggcYqWCj2DNADFDAAQUgIAAAEFDDJmPYqNJF
F1s4cscTmCDjDTjdSPOHBQggUAEQDAgggTWDPoYMJkFoUdRmddyyjWLeULMMMcAsIw0x4wkM
IME1g25zyxpHxFYUHmyIggw4H4ojITnfiLMNMAkcAAub4BQjihRdDGTJHmvc4Qo1wD6Imje6
eILbj+BQ4wqu5Q3ECSJ0FOKKMtv4mBg33Pw4zjbKuBIIE1xYpIkhdQQiyi7OtAucj6dt48wu
otQhBRa6VvSJIRwhIkotvgRTzMUYZ6xxMcj4QkspeKDxxRhEmUfIHWjAgQcijEDissuXvCyz
zH7Q8YQURxDhUsn/bCInR3AELfTQZBRt9BBJkCGFFVhMwTNBlnBCSCGEIJQQIAklZMXWRBAR
RRRWENHwRQEBADs="""

def make_style():
    # need to keep bindings for s1 and s2 around, else the get eaten by GC
    global s1, s2
    s1 = Tkinter.PhotoImage("search1", data=data, format="gif -index 0")
    s2 = Tkinter.PhotoImage("search2", data=data, format="gif -index 1")
    
    style = ttk.Style()
    
    style.element_create("Search.field", "image", "search1",
        ("focus", "search2"), border=[22, 7, 14], sticky="ew")
    
    style.layout("Search.entry", [
        ("Search.field", {"sticky": "nswe", "border": 1, "children":
            [("Entry.padding", {"sticky": "nswe", "children":
                [("Entry.textarea", {"sticky": "nswe"})]
            })]
        })]
    )
    
    #style.configure("Search.entry", background="#b2b2b2")
    

########NEW FILE########
__FILENAME__ = simplenote
# -*- coding: utf-8 -*-
"""
    simplenote.py
    ~~~~~~~~~~~~~~

    Python library for accessing the Simplenote API

    :copyright: (c) 2011 by Daniel Schauenberg
    :license: MIT, see LICENSE for more details.
"""

import urllib
import urllib2
from urllib2 import HTTPError
import base64
try:
    import json
except ImportError:
    try:
        import simplejson as json
    except ImportError:
        # For Google AppEngine
        from django.utils import simplejson as json

AUTH_URL = 'https://simple-note.appspot.com/api/login'
DATA_URL = 'https://simple-note.appspot.com/api2/data'
INDX_URL = 'https://simple-note.appspot.com/api2/index?'
NOTE_FETCH_LENGTH = 20

class Simplenote(object):
    """ Class for interacting with the simplenote web service """

    def __init__(self, username, password):
        """ object constructor """
        self.username = urllib2.quote(username)
        self.password = urllib2.quote(password)
        self.token = None

    def authenticate(self, user, password):
        """ Method to get simplenote auth token

        Arguments:
            - user (string):     simplenote email address
            - password (string): simplenote password

        Returns:
            Simplenote API token as string

        """
        auth_params = "email=%s&password=%s" % (user, password)
        values = base64.encodestring(auth_params)
        request = Request(AUTH_URL, values)
        try:
            res = urllib2.urlopen(request).read()
            token = urllib2.quote(res)
        except IOError: # no connection exception
            token = None
        return token

    def get_token(self):
        """ Method to retrieve an auth token.

        The cached global token is looked up and returned if it exists. If it
        is `None` a new one is requested and returned.

        Returns:
            Simplenote API token as string

        """
        if self.token == None:
            self.token = self.authenticate(self.username, self.password)
        return self.token


    def get_note(self, noteid):
        """ method to get a specific note

        Arguments:
            - noteid (string): ID of the note to get

        Returns:
            A tuple `(note, status)`

            - note (dict): note object
            - status (int): 0 on sucesss and -1 otherwise

        """
        # request note
        params = '/%s?auth=%s&email=%s' % (str(noteid), self.get_token(),
                                           self.username)
        request = Request(DATA_URL+params)
        try:
            response = urllib2.urlopen(request)
        except HTTPError, e:
            return e, -1
        except IOError, e:
            return e, -1
        note = json.loads(response.read())
        #use UTF-8 encoding
        if isinstance(note["content"], str):
            note["content"] = note["content"].encode('utf-8')

        if note.has_key("tags"):
            note["tags"] = [t.encode('utf-8') if isinstance(t,str) else t for t in note["tags"]]

        return note, 0

    def update_note(self, note):
        """ function to update a specific note object, if the note object does not
        have a "key" field, a new note is created

        Arguments
            - note (dict): note object to update

        Returns:
            A tuple `(note, status)`

            - note (dict): note object
            - status (int): 0 on sucesss and -1 otherwise

        """

        # use UTF-8 encoding
        # cpbotha: in both cases check if it's not unicode already
        # otherwise you get "TypeError: decoding Unicode is not supported"
        if isinstance(note["content"], str):
            note["content"] = unicode(note["content"], 'utf-8')

        if note.has_key("tags"):
            # if a tag is a string, unicode it, otherwise pass it through
            # unchanged (it's unicode already)
            # using the ternary operator, because I like it: a if test else b
            note["tags"] = [unicode(t, 'utf-8') if isinstance(t, str) else t for t in note["tags"]]

        # determine whether to create a new note or updated an existing one
        if note.has_key("key"):
            url = '%s/%s?auth=%s&email=%s' % (DATA_URL, note["key"],
                                              self.get_token(), self.username)
        else:
            url = '%s?auth=%s&email=%s' % (DATA_URL, self.get_token(), self.username)
        request = Request(url, urllib.quote(json.dumps(note)))
        response = ""
        try:
            response = urllib2.urlopen(request).read()
        except IOError, e:
            return e, -1
        return json.loads(response), 0

    def add_note(self, note):
        """wrapper function to add a note

        The function can be passed the note as a dict with the `content`
        property set, which is then directly send to the web service for
        creation. Alternatively, only the body as string can also be passed. In
        this case the parameter is used as `content` for the new note.

        Arguments:
            - note (dict or string): the note to add

        Returns:
            A tuple `(note, status)`

            - note (dict): the newly created note
            - status (int): 0 on sucesss and -1 otherwise

        """
        if type(note) == str:
            return self.update_note({"content": note})
        elif (type(note) == dict) and note.has_key("content"):
            return self.update_note(note)
        else:
            return "No string or valid note.", -1

    def get_note_list(self, qty=float("inf")):
        """ function to get the note list

        The function can be passed an optional argument to limit the
        size of the list returned. If omitted a list of all notes is
        returned.

        Arguments:
            - quantity (integer number): of notes to list

        Returns:
            An array of note objects with all properties set except
            `content`.

        """
        # initialize data
        status = 0
        ret = []
        response = {}
        notes = { "data" : [] }

        # get the note index
        if qty < NOTE_FETCH_LENGTH:
            params = 'auth=%s&email=%s&length=%s' % (self.get_token(), self.username,
                                                 qty)
        else:
            params = 'auth=%s&email=%s&length=%s' % (self.get_token(), self.username,
                                                 NOTE_FETCH_LENGTH)
        # perform initial HTTP request
        try:
            request = Request(INDX_URL+params)
            response = json.loads(urllib2.urlopen(request).read())
            notes["data"].extend(response["data"])
        except IOError:
            status = -1

        # get additional notes if bookmark was set in response
        while response.has_key("mark") and len(notes["data"]) < qty:
            if (qty - len(notes["data"])) < NOTE_FETCH_LENGTH:
                vals = (self.get_token(), self.username, response["mark"], qty - len(notes["data"]))
            else:
                vals = (self.get_token(), self.username, response["mark"], NOTE_FETCH_LENGTH)
            params = 'auth=%s&email=%s&mark=%s&length=%s' % vals

            # perform the actual HTTP request
            try:
                request = Request(INDX_URL+params)
                response = json.loads(urllib2.urlopen(request).read())
                notes["data"].extend(response["data"])
            except IOError:
                status = -1

        # parse data fields in response
        ret = notes["data"]

        return ret, status

    def trash_note(self, note_id):
        """ method to move a note to the trash

        Arguments:
            - note_id (string): key of the note to trash

        Returns:
            A tuple `(note, status)`

            - note (dict): the newly created note or an error message
            - status (int): 0 on sucesss and -1 otherwise

        """
        # get note
        note, status = self.get_note(note_id)
        if (status == -1):
            return note, status
        # set deleted property
        note["deleted"] = 1
        # update note
        return self.update_note(note)

    def delete_note(self, note_id):
        """ method to permanently delete a note

        Arguments:
            - note_id (string): key of the note to trash

        Returns:
            A tuple `(note, status)`

            - note (dict): an empty dict or an error message
            - status (int): 0 on sucesss and -1 otherwise

        """
        # notes have to be trashed before deletion
        note, status = self.trash_note(note_id)
        if (status == -1):
            return note, status

        params = '/%s?auth=%s&email=%s' % (str(note_id), self.get_token(),
                                           self.username)
        request = Request(url=DATA_URL+params, method='DELETE')
        try:
            urllib2.urlopen(request)
        except IOError, e:
            return e, -1
        return {}, 0


class Request(urllib2.Request):
    """ monkey patched version of urllib2's Request to support HTTP DELETE
        Taken from http://python-requests.org, thanks @kennethreitz
    """

    def __init__(self, url, data=None, headers={}, origin_req_host=None,
                unverifiable=False, method=None):
        urllib2.Request.__init__(self, url, data, headers, origin_req_host, unverifiable)
        self.method = method

    def get_method(self):
        if self.method:
            return self.method

        return urllib2.Request.get_method(self)



########NEW FILE########
__FILENAME__ = tk
# nvPY: cross-platform note-taking app with simplenote syncing
# copyright 2012 by Charl P. Botha <cpbotha@vxlabs.com>
# new BSD license

# Tkinter and ttk documentation recommend pulling all symbols into client 
# module namespace. I don't like that, so first pulling into this module
# tk, then can use tk.whatever in main module.

from Tkinter import *
from ttk import *

########NEW FILE########
__FILENAME__ = utils
# nvPY: cross-platform note-taking app with simplenote syncing
# copyright 2012 by Charl P. Botha <cpbotha@vxlabs.com>
# new BSD license

import datetime
import random
import re
import string
import urllib2

# first line with non-whitespace should be the title
note_title_re = re.compile('\s*(.*)\n?')
        
def generate_random_key():
    """Generate random 30 digit (15 byte) hex string.
    
    stackoverflow question 2782229
    """
    return '%030x' % (random.randrange(256**15),)

def get_note_title(note):
    mo = note_title_re.match(note.get('content', ''))
    if mo:
        return mo.groups()[0]
    else:
        return ''

def get_note_title_file(note):
    mo = note_title_re.match(note.get('content', ''))
    if mo:
        fn = mo.groups()[0]
        fn = fn.replace(' ', '_')
        fn = fn.replace('/', '_')
        if not fn:
            return ''

        if isinstance(fn, str):
            fn = unicode(fn, 'utf-8')
        else:
            fn = unicode(fn)

        if note_markdown(note):
            fn += '.mkdn'
        else:
            fn += '.txt'

        return fn
    else:
        return ''

def human_date(timestamp):
    """
    Given a timestamp, return pretty human format representation.

    For example, if timestamp is:
    * today, then do "15:11"
    * else if it is this year, then do "Aug 4"
    * else do "Dec 11, 2011"
    """

    # this will also give us timestamp in the local timezone
    dt = datetime.datetime.fromtimestamp(timestamp)
    # this returns localtime
    now = datetime.datetime.now()

    if dt.date() == now.date():
        # today: 15:11
        return dt.strftime('%H:%M')

    elif dt.year == now.year:
        # this year: Aug 6
        # format code %d unfortunately 0-pads
        return dt.strftime('%b') + ' ' + str(dt.day)

    else:
        # not today or this year, so we do "Dec 11, 2011"
        return '%s %d, %d' % (dt.strftime('%b'), dt.day, dt.year)


def note_pinned(n):
    asystags = n.get('systemtags', 0)
    # no systemtag at all
    if not asystags:
        return 0

    if 'pinned' in asystags:
        return 1
    else:
        return 0

def note_markdown(n):
    asystags = n.get('systemtags', 0)
    # no systemtag at all
    if not asystags:
        return 0

    if 'markdown' in asystags:
        return 1
    else:
        return 0

tags_illegal_chars = re.compile(r'[\s]')
def sanitise_tags(tags):
    """
    Given a string containing comma-separated tags, sanitise and return a list of string tags.

    The simplenote API doesn't allow for spaces, so we strip those out.

    @param tags: Comma-separated tags, one string.
    @returns: List of strings.
    """

    # hack out all kinds of whitespace, then split on ,
    # if you run into more illegal characters (simplenote does not want to sync them)
    # add them to the regular expression above.
    illegals_removed = tags_illegal_chars.sub('', tags)
    if len(illegals_removed) == 0:
        # special case for empty string ''
        # split turns that into [''], which is not valid
        return []

    else:
        return illegals_removed.split(',')



def sort_by_title_pinned(a, b):
    if note_pinned(a.note) and not note_pinned(b.note):
        return -1
    elif not note_pinned(a.note) and note_pinned(b.note):
        return 1
    else:
        return cmp(get_note_title(a.note), get_note_title(b.note))

def sort_by_modify_date_pinned(a, b):
    if note_pinned(a.note) and not note_pinned(b.note):
        return 1
    elif not note_pinned(a.note) and note_pinned(b.note):
        return -1
    else:
        return cmp(float(a.note.get('modifydate', 0)), float(b.note.get('modifydate', 0)))

def check_internet_on():
    """Utility method to check if we have an internet connection.
    
    slightly adapted from: http://stackoverflow.com/a/3764660/532513
    """
    try:
        urllib2.urlopen('http://74.125.228.100',timeout=1)
        return True
    
    except urllib2.URLError: 
        pass
    
    return False    

class KeyValueObject:
    """Store key=value pairs in this object and retrieve with o.key.
    
    You should also be able to do MiscObject(**your_dict) for the same effect.
    """

    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)

class SubjectMixin:
    """Maintain a list of callables for each event type.
    
    We follow the convention action:object, e.g. change:entry.
    """

    def __init__(self):
        self.observers = {}
        self.mutes = {}

    def add_observer(self, evt_type, o):
        if evt_type not in self.observers:
            self.observers[evt_type] = [o]
        
        elif o not in self.observers[evt_type]:
            self.observers[evt_type].append(o)
        
    def notify_observers(self, evt_type, evt):
        if evt_type in self.mutes or evt_type not in self.observers:
            return
        
        for o in self.observers[evt_type]:
            # invoke observers with ourselves as first param
            o(self, evt_type, evt)
            
    def mute(self, evt_type):
        self.mutes[evt_type] = True
        
    def unmute(self, evt_type):
        if evt_type in self.mutes:
            del self.mutes[evt_type]

########NEW FILE########
__FILENAME__ = view
# nvPY: cross-platform note-taking app with simplenote syncing
# copyright 2012 by Charl P. Botha <cpbotha@vxlabs.com>
# new BSD license

import copy
import logging
import os
import re
import search_entry
import sys
import tk
import tkFont
import tkMessageBox
import utils
import webbrowser

from datetime import datetime

class WidgetRedirector:

    """Support for redirecting arbitrary widget subcommands."""

    def __init__(self, widget):
        self.dict = {}
        self.widget = widget
        self.tk = tk = widget.tk
        w = widget._w
        self.orig = w + "_orig"
        tk.call("rename", w, self.orig)
        tk.createcommand(w, self.dispatch)

    def __repr__(self):
        return "WidgetRedirector(%s<%s>)" % (self.widget.__class__.__name__,
                                             self.widget._w)

    def close(self):
        for name in self.dict.keys():
            self.unregister(name)
        widget = self.widget; del self.widget
        orig = self.orig; del self.orig
        tk = widget.tk
        w = widget._w
        tk.deletecommand(w)
        tk.call("rename", orig, w)

    def register(self, name, function):
        if self.dict.has_key(name):
            previous = dict[name]
        else:
            previous = OriginalCommand(self, name)
        self.dict[name] = function
        setattr(self.widget, name, function)
        return previous

    def unregister(self, name):
        if self.dict.has_key(name):
            function = self.dict[name]
            del self.dict[name]
            if hasattr(self.widget, name):
                delattr(self.widget, name)
            return function
        else:
            return None

    def dispatch(self, cmd, *args):
        m = self.dict.get(cmd)
        try:
            if m:
                return m(*args)
            else:
                return self.tk.call((self.orig, cmd) + args)
        except tk.TclError:
            return ""


class OriginalCommand:

    def __init__(self, redir, name):
        self.redir = redir
        self.name = name
        self.tk = redir.tk
        self.orig = redir.orig
        self.tk_call = self.tk.call
        self.orig_and_name = (self.orig, self.name)

    def __repr__(self):
        return "OriginalCommand(%r, %r)" % (self.redir, self.name)

    def __call__(self, *args):
        return self.tk_call(self.orig_and_name + args)


#########################################################################
class RedirectedText(tk.Text):
    """We would like to know when the Text widget's contents change.  We can't
    just override the insert method, we have to make use of some Tk magic.
    This magic is encapsulated in the idlelib.WidgetRedirector class which
    we use here.
    """

    def __init__(self, master=None, cnf={}, **kw):
        tk.Text.__init__(self, master, cnf, **kw)

        # now attach the redirector
        self.redir = WidgetRedirector(self)
        self.orig_insert = self.redir.register("insert", self.new_insert)
        self.orig_delete = self.redir.register("delete", self.new_delete)
        self.fonts = [kw['font']]

    def new_insert(self, *args):
        self.orig_insert(*args)
        self.event_generate('<<Change>>')

    def new_delete(self, *args):
        self.orig_delete(*args)
        self.event_generate('<<Change>>')


class HelpBindings(tk.Toplevel):
    def __init__(self, parent=None):
        tk.Toplevel.__init__(self, parent)
        self.title("Help | Bindings")

        import bindings

        msg = tk.Text(self, width=80, wrap=tk.NONE)
        msg.insert(tk.END, bindings.description)
        msg.config(state=tk.DISABLED)
        msg.pack()

        button = tk.Button(self, text="Dismiss", command=self.destroy)
        button.pack()


#########################################################################
class StatusBar(tk.Frame):
    """Adapted from the tkinterbook.
    """
    
    # actions
    # global status
    # note status

    # http://colorbrewer2.org/index.php?type=sequential&scheme=OrRd&n=3
    # from light to dark orange; colorblind-safe scheme
    #NOTE_STATUS_COLORS = ["#FEE8C8", "#FDBB84", "#E34A33"]

    # http://colorbrewer2.org/index.php?type=diverging&scheme=RdYlBu&n=5
    # diverging red to blue; colorblind-safe scheme
    # red, lighter red, light yellow, light blue, dark blue
    NOTE_STATUS_COLORS = ["#D7191C", "#FDAE61", "#FFFFBF", "#ABD9E9", "#2C7BB6"]
    # 0 - saved and synced - light blue - 3
    # 1 - saved - light yellow - 2
    # 2 - modified - lighter red - 1
    NOTE_STATUS_LUT = {0 : 3, 1 : 2, 2 : 1}

    def __init__(self, master):
        tk.Frame.__init__(self, master)

        self.status = tk.Label(self, relief=tk.SUNKEN, anchor=tk.W, width=40)
        self.status.pack(side=tk.LEFT, fill=tk.X, expand=1)

        self.centre_status = tk.Label(self, relief=tk.SUNKEN, anchor=tk.W, width=35)
        self.centre_status.pack(side=tk.LEFT, fill=tk.X, padx=5)

        self.note_status = tk.Label(self, relief=tk.SUNKEN, anchor=tk.W, width=25)
        self.note_status.pack(side=tk.LEFT, fill=tk.X)

    def set_centre_status(self, fmt, *args):
        self.centre_status.config(text=fmt % args)
        self.centre_status.update_idletasks()

    def set_note_status(self, fmt, *args):
        """ *.. .s. .sS
        """ 
        self.note_status.config(text=fmt % args)
        self.note_status.update_idletasks()

    def set_note_status_color(self, status_idx):
        """
        @param status_idx: 0 - saved and synced; 1 - saved; 2 - modified
        """

        color_idx = self.NOTE_STATUS_LUT[status_idx]
        self.note_status.config(background=self.NOTE_STATUS_COLORS[color_idx])

    def set_status(self, fmt, *args):
        self.status.config(text=fmt % args)
        self.status.update_idletasks()

    def clear_status(self):
        self.status.config(text="")
        self.status.update_idletasks()

class NotesList(tk.Frame):
    """
    @ivar note_headers: list containing tuples with each note's title, tags,
    modified date and so forth. Always in sync with what is displayed.
    """

    TITLE_COL = 0
    TAGS_COL = 1
    MODIFYDATE_COL = 2
    PINNED_COL = 3

    def __init__(self, master, font_family, font_size, config):
        tk.Frame.__init__(self, master)

        yscrollbar = tk.Scrollbar(self)
        yscrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        f = tkFont.Font(family=font_family, size=font_size)
        # tkFont.families(root) returns list of available font family names
        # this determines the width of the complete interface (yes)
        # size=-self.config.font_size
        self.text = tk.Text(self, height=25, width=30,
            wrap=tk.NONE,
            font=f,
            yscrollcommand=yscrollbar.set,
            undo=True,
            background = config.background_color)
        # change default font at runtime with:
        #text.config(font=f)

        self.text.config(cursor="arrow")
        self.disable_text()
        self.text.pack(fill=tk.BOTH, expand=1)

        # tags for all kinds of styling ############################
        ############################################################

        self.text.tag_config("selected", background="light blue")

        self.text.tag_config("pinned", foreground="dark gray")

        # next two lines from:
        # http://stackoverflow.com/a/9901862/532513
        bold_font = tkFont.Font(self.text, self.text.cget("font"))
        bold_font.configure(weight="bold")
        self.text.tag_config("title", font=bold_font)

        italic_font = tkFont.Font(self.text, self.text.cget("font"))
        italic_font.configure(slant="italic")
        self.text.tag_config("tags", font=italic_font, foreground="dark gray")
        self.text.tag_config("found", font=italic_font, foreground="dark gray", background="lightyellow")

        self.text.tag_config("modifydate", foreground="dark gray")

        yscrollbar.config(command=self.text.yview)

        self._bind_events()

        self.selected_idx = -1
        # list containing tuples with each note's title, tags,
        self.note_headers = []

        self.layout=config.layout
        self.print_columns=config.print_columns
        if bold_font.measure(' ') > f.measure(' '):
            self.cwidth = bold_font.measure(' ')
        else:
            self.cwidth = f.measure(' ')
        self.fonts = [f, italic_font, bold_font]

    def append(self, note, config):
        """
        @param note: The complete note dictionary.
        """

        title = utils.get_note_title(note)
        tags = note.get('tags')
        modifydate = float(note.get('modifydate'))
        pinned = utils.note_pinned(note)
        self.note_headers.append((title, tags, modifydate, pinned))

        self.enable_text()

        if self.layout == "vertical" and self.print_columns == 1:
            nrchars, rem = divmod((self.text.winfo_width()), self.cwidth)
            cellwidth = (int(nrchars) - 8)/2
            
            if pinned:
                title += ' *'

            self.text.insert(tk.END, u'{0:<{w}}'.format(title[:cellwidth-1], w=cellwidth), ("title,"))

            if tags > 0:
                if config.tagfound:
                    self.text.insert(tk.END, u'{0:<{w}}'.format(','.join(tags)[:cellwidth-1], w=cellwidth), ("found",))
                else:
                    self.text.insert(tk.END, u'{0:<{w}}'.format(','.join(tags)[:cellwidth-1], w=cellwidth), ("tags",))

            self.text.insert(tk.END, ' ' + utils.human_date(modifydate), ("modifydate",))

            # tags can be None (newly created note) or [] or ['tag1', 'tag2']
        else:
            self.text.insert(tk.END, title, ("title,"))

            if pinned:
                self.text.insert(tk.END, ' *', ("pinned",))

            self.text.insert(tk.END, ' ' + utils.human_date(modifydate), ("modifydate",))

            # tags can be None (newly created note) or [] or ['tag1', 'tag2']
            if tags > 0:
                if config.tagfound:
                    self.text.insert(tk.END, ' ' + ','.join(tags), ("found",))
                else:
                    self.text.insert(tk.END, ' ' + ','.join(tags), ("tags",))

        self.text.insert(tk.END, '\n')

        self.disable_text()


    def _bind_events(self):
        # Text widget events ##########################################


        self.text.bind("<Button 1>", self.cmd_text_button1)

        # same deal as for pageup
        # we have to stop the text widget class event handler from firing
        def cmd_up(e):
            self.select_prev(silent=False)
            return "break"

        self.text.bind("<Up>", cmd_up)

        # for pageup, event handler needs to return "break" so that
        # Text widget's default class handler for pageup does not trigger.
        def cmd_pageup(e):
            self.select_prev(silent=False, delta=10)
            return "break"

        self.text.bind("<Prior>", cmd_pageup)

        def cmd_down(e):
            self.select_next(silent=False)
            return "break"

        self.text.bind("<Down>", cmd_down)

        def cmd_pagedown(e):
            self.select_next(silent=False, delta=10)
            return "break"

        self.text.bind("<Next>", cmd_pagedown)


    def cmd_text_button1(self, event):
        # find line that was clicked on
        text_index = self.text.index("@%d,%d" % (event.x, event.y))
        # go from event coordinate to tkinter text INDEX to note idx!
        idx = int(text_index.split('.')[0]) - 1
        self.select(idx, silent=False)


    def clear(self):
        """

        """
        self.enable_text()
        # clear everything from the display
        self.text.delete(1.0, tk.END)
        # and make sure our backing store is in sync
        del self.note_headers[:]
        self.disable_text()

    def disable_text(self):
        self.text.config(state=tk.DISABLED)

    def enable_text(self):
        self.text.config(state=tk.NORMAL)

    def find_note_by_title(self, title):
        """
        Find note with given title.

        @returns: Note index if found, -1 otherwise.
        """

        idx = -1
        for i, nh in enumerate(self.note_headers):
            t = nh[NotesList.TITLE_COL]
            if t == title:
                idx = i
                break

        return idx

    def get_number_of_notes(self):
        # could also have used:
        # return int(self.text.index('end-1c').split('.')[0])
        # but we have the backing store!
        return len(self.note_headers)

    def get_pinned(self, idx):
        return self.note_headers[idx][NotesList.PINNED_COL]

    def get_tags(self, idx):
        """
        @returns: raw list of tag strings, e.g. ['work', 'howto']
        """
        return self.note_headers[idx][NotesList.TAGS_COL]

    def get_title(self, idx):
        return self.note_headers[idx][NotesList.TITLE_COL]

    def get_modifydate(self, idx):
        """
        Return modifydate of idx'th note.

        @returns: modifydate as a floating point timestamp.
        """
        return self.note_headers[idx][NotesList.MODIFYDATE_COL]

    def idx_to_index_range(self, idx):
        """
        Given a note index idx, return the Tkinter text index range for
        the start and end of that note.
        """

        # tkinter text first line is 1, but first column is 0
        row = idx+1
        start = "%d.0" % (row,)
        end = "%d.end" % (row,)

        return (start, end)

    def select(self, idx, silent=True):
        """
        @param idx: index of note to select. -1 if no selection.
        """

        # remove tag selected from row 1 (first) and column 0 to the end of the buffer
        self.text.tag_remove("selected", "1.0", "end")

        if idx >= 0 and idx < self.get_number_of_notes():
            # then add it to the requested note line(s)
            start, end = self.idx_to_index_range(idx)
            self.text.tag_add("selected", start, end)
            # ensure that this is visible
            self.text.see(start)
            # and store the current idx
            self.selected_idx = idx

        else:
            self.selected_idx = -1

        if not silent:
            self.event_generate('<<NotesListSelect>>')

    def select_next(self, silent=True, delta=1):
        """
        Select note right after the current selection.
        """

        new_idx = self.selected_idx + delta
        if new_idx >= 0 and new_idx < self.get_number_of_notes():
            self.select(new_idx, silent)

        elif new_idx >= self.get_number_of_notes():
            self.select(self.get_number_of_notes() - 1, silent)

    def select_prev(self, silent=True, delta=1):
        """
        Select note right after the current selection.
        """

        new_idx = self.selected_idx - delta
        if new_idx >= 0 and new_idx <= self.get_number_of_notes():
            self.select(new_idx, silent)

        elif new_idx < 0:
            self.select(0, silent)

tkinter_umlauts=['odiaeresis', 'adiaeresis', 'udiaeresis', 'Odiaeresis', 'Adiaeresis', 'Udiaeresis', 'ssharp']

class TriggeredcompleteEntry(tk.Entry):
    """
    Subclass of tk.Entry that features triggeredcompletion.

    How this works: User types first part of tag, then triggers complete with
    ctrl-space. The first matching tag is shown. The user can either continue
    pressing ctrl-space to see more matching tags, or right arrow to select
    the current suggestion and continue typing. Backspace will delete the
    suggested part. 

    To enable triggeredcompletion use set_completion_list(list) to define 
    a list of possible strings to hit.
    To cycle through hits use CTRL <space> keys.

    @ivar cycle: if 1, then we're cycling through alternative completions.
    """

    def __init__(self, master, case_sensitive, **kw): 
        tk.Entry.__init__(self, master, **kw)
        self.case_sensitive = case_sensitive
        # make sure we're initialised, else the event handler could generate
        # exceptions checking for instance variables that don't exist yet.
        self.set_completion_list([])
        self.bind('<KeyRelease>', self.handle_keyrelease)               

    def set_completion_list(self, completion_list):
        self._completion_list = completion_list
        self._hits = []
        self._hit_index = 0
        self.wstart = 0
        self.position = 0
        self.cycle = 0

    def triggeredcomplete(self):
        """triggeredcomplete the Entry, delta may be 0/1 to cycle through possible hits"""

        if self.cycle: # need to delete selection otherwise we would fix the current position
            self.delete(self.position, tk.END)
            self._hit_index += 1
            if self._hit_index == len(self._hits):
                self._hit_index = 0

        else: # set position to end so selection starts where textentry ended
            self.position = len(self.get())
            wstartsc = self.get().rfind(':')
            wstartsp = self.get().rfind(' ')
            if wstartsc < 0 and wstartsp < 0:
                self.wstart = 0
            elif wstartsc > wstartsp:
                self.wstart = wstartsc + 1
            else:
                self.wstart = wstartsp + 1

            # collect hits
            _hits = []
            for element in self._completion_list:
                if self.case_sensitive == 0: 
                    if element.lower().startswith(self.get()[self.wstart:].lower()):
                         _hits.append(element)
                else:
                    if element.startswith(self.get()[self.wstart:]):
                         _hits.append(element)

            self._hit_index = 0
            self._hits=_hits

        # now finally perform the triggered completion
        if self._hits:
            self.delete(self.wstart,tk.END)
            self.insert(self.wstart,self._hits[self._hit_index])
            self.select_range(self.position,tk.END)

    def handle_keyrelease(self, event):
        """event handler for the keyrelease event on this widget"""
        ctrl  = ((event.state & 0x0004) != 0)

        # special case handling below only if we are in cycle mode.
        if self.cycle:
            if event.keysym == "BackSpace":
                self.cycle = 0
                self.delete(self.index(tk.INSERT), tk.END)
                self.position = self.index(tk.END)

            if event.keysym == "Right":
                self.position = self.index(tk.END) # go to end (no selection)
                self.cycle = 0

            if event.keysym == "Left":
                self.cycle = 0

        if event.keysym == "space" and ctrl:
            # cycle 
            self.triggeredcomplete()
            if self.cycle == 0:
                self.cycle = 1


class View(utils.SubjectMixin):
    """Main user interface class.
    """
    
    def __init__(self, config, notes_list_model):
        utils.SubjectMixin.__init__(self)
        
        self.config = config
        self.taglist = None
        
        notes_list_model.add_observer('set:list', self.observer_notes_list)
        self.notes_list_model = notes_list_model
        
        self.root = None

        self._create_ui()
        self._bind_events()

        # set default font for dialog boxes on Linux
        # on Windows, tkinter uses system dialogs in any case
        self.root.option_add('*Dialog.msg.font', 'Helvetica 12')
        
        self.text_tags_links = []
        self.text_tags_search = []

        #self._current_text = None
        #self.user_text.focus_set()

        self.search_entry.focus_set()

    def askyesno(self, title, msg):
        return tkMessageBox.askyesno(title, msg)
    
    def cmd_notes_list_select(self, evt):
        sidx = self.notes_list.selected_idx
        self.notify_observers('select:note', utils.KeyValueObject(sel=sidx))
        
    def cmd_root_delete(self, evt=None):
        sidx = self.notes_list.selected_idx
        self.notify_observers('delete:note', utils.KeyValueObject(sel=sidx))
        
    def cmd_root_new(self, evt=None):
        # this'll get caught by a controller event handler
        self.notify_observers('create:note', utils.KeyValueObject(title=self.get_search_entry_text()))
        # the note will be created synchronously, so we can focus the text area already
        self.text_note.focus()

    def cmd_select_all(self, evt=None):
        self.text_note.tag_add("sel", "1.0", "end-1c")
        # we don't want the text bind_class() handler for Ctrl-A to be fired.
        return "break"

    def set_note_editing(self, enable=True):
        """Enable or disable note editing controls.

        This is used to disable the controls when no note has been selected.
        Disables note text widget, tag entry and pinned checkbutton.

        @param enable: enable controls if True, else disable.
        @return: Nothing.
        """

        state = tk.NORMAL if enable else tk.DISABLED
        self.text_note.config(state=state)
        self.tags_entry.config(state=state)
        self.pinned_checkbutton.config(state=state)

    def get_continuous_rendering(self):
        return self.continuous_rendering.get()

    def get_selected_text(self):
        """
        Return note text that has been selected by user.
        """

        try:
            return self.text_note.selection_get()
        except tk.TclError:
            return ''

    def get_text(self):
        # err, you have to specify 1.0 to END, and NOT 0 to END like I thought.
        # also, see the comment by Bryan Oakley to
        # http://stackoverflow.com/a/3137169
        # we need to get rid of newline that text adds automatically
        # at end.
        return self.text_note.get(1.0, "end-1c")
    
    def get_search_entry_text(self):
        return self.search_entry_var.get()
    
    def refresh_notes_list(self):
        """Trigger a complete refresh notes list by resetting search entry.
        """
        # store cursor position first! returns e.g. 8.32
        #cursor_pos = self.text_note.index(tk.INSERT)
        
        # since 0.6, set_search_entry() tries to leave the currently selected
        # note untouched if it still exists in the newly returned list
        # so we don't have to do an explicit reselect.
        self.set_search_entry_text(self.get_search_entry_text())
        
        #self.text_note.mark_set(tk.INSERT, cursor_pos)

    def see_first_search_instance(self):
        """If there are instances of the search string in the current
        note, ensure that the first one is visible.
        """

        if self.text_tags_search:
            self.text_note.see(self.text_tags_search[0] + '.first')

    def select_note(self, idx, silent=False):
        """Programmatically select the note by idx

        @param silent: If this is True, don't fire an event. VERY
        IMPORTANT: if you use silent, the controller won't set the
        selected_note_idx. You should make sure that it's in sync with
        what you've just selected.
        """

        self.notes_list.select(idx, silent)

    def select_note_by_name(self, name):
        idx = self.notes_list.find_note_by_title(name)
        if idx >= 0:
            self.select_note(idx, silent=False)

        return idx

    def set_note_status(self, status):
        """status is an object with ivars modified, saved and synced.
        """
        
        if status.modified:
            s = 'modified'
            self.statusbar.set_note_status_color(2)
        elif status.saved and status.synced:
            s = 'saved + synced'
            self.statusbar.set_note_status_color(0)
        elif status.saved:
            s = 'saved'
            self.statusbar.set_note_status_color(1)
        else:
            s = 'synced'
            self.statusbar.set_note_status_color(0)
        
        self.statusbar.set_note_status('Current note %s' % (s,))

    def set_note_tally(self, filtered_notes, active_notes, total_notes):
        self.statusbar.set_centre_status('Listing %d / %d active notes (%d total)' % (filtered_notes, active_notes, total_notes))
            
    def set_search_entry_text(self, text):
        self.search_entry_var.set(text)
        
    def _bind_events(self):
        # make sure window close also goes through our handler
        self.root.protocol('WM_DELETE_WINDOW', self.handler_close)

        self.root.bind_all("<Control-g>", lambda e: self.tags_entry.focus())
        self.root.bind_all("<Control-question>", lambda e: self.cmd_help_bindings())
        self.root.bind_all("<Control-plus>", lambda e: self.cmd_font_size(+1))
        self.root.bind_all("<Control-minus>", lambda e: self.cmd_font_size(-1))

        self.notes_list.bind("<<NotesListSelect>>", self.cmd_notes_list_select)
        # same behaviour as when the user presses enter on search entry:
        # if something is selected, focus the text area
        # if nothing is selected, try to create new note with
        # search entry value as name
        self.notes_list.text.bind("<Return>", self.handler_search_enter)
        
        self.search_entry.bind("<Escape>", lambda e:
                self.search_entry.delete(0, tk.END))
        # this will either focus current content, or
        # if there's no selection, create a new note.
        self.search_entry.bind("<Return>", self.handler_search_enter)
        
        self.search_entry.bind("<Up>", lambda e:
            self.notes_list.select_prev(silent=False))
        self.search_entry.bind("<Prior>", lambda e:
            self.notes_list.select_prev(silent=False, delta=10))

        self.search_entry.bind("<Down>", lambda e:
            self.notes_list.select_next(silent=False))
        self.search_entry.bind("<Next>", lambda e:
            self.notes_list.select_next(silent=False, delta=10))

        self.text_note.bind("<<Change>>", self.handler_text_change)
        
        # user presses escape in text area, they go back to notes list
        self.text_note.bind("<Escape>", lambda e: self.notes_list.text.focus())
        # <Key>
        
        self.text_note.bind("<Control-a>", self.cmd_select_all)

        self.tags_entry_var.trace('w', self.handler_tags_entry)
        self.tags_entry.bind("<Escape>", lambda e: self.text_note.focus())

        self.pinned_checkbutton_var.trace('w', self.handler_pinned_checkbutton)

        self.root.after(self.config.housekeeping_interval_ms, self.handler_housekeeper)

    def _create_menu(self):
        """Utility function to setup main menu.

        Called by _create_ui.
        """
        
        # MAIN MENU ####################################################
        menu = tk.Menu(self.root)
        self.root.config(menu=menu)

        file_menu = tk.Menu(menu, tearoff=False)
        menu.add_cascade(label="File", underline='0', menu=file_menu)
        
        
        
        

        # FILE ##########################################################
        file_menu.add_command(label = "New note", underline=0,
                              command=self.cmd_root_new, accelerator="Ctrl+N")
        self.root.bind_all("<Control-n>", self.cmd_root_new)

        file_menu.add_command(label = "Delete note", underline=0,
                              command=self.cmd_root_delete, accelerator="Ctrl+D")        
        self.root.bind_all("<Control-d>", self.cmd_root_delete)
        
        file_menu.add_separator()
        
        file_menu.add_command(label = "Sync full", underline=5,
                              command=self.cmd_sync_full)
        file_menu.add_command(label = "Sync current note",
                underline=0, command=self.cmd_sync_current_note,
                accelerator="Ctrl+S")
        self.root.bind_all("<Control-s>", self.cmd_sync_current_note)
        
        file_menu.add_separator()

        file_menu.add_command(label = "Render Markdown to HTML", underline=7,
                command=self.cmd_markdown, accelerator="Ctrl+M")
        self.root.bind_all("<Control-m>", self.cmd_markdown)

        self.continuous_rendering = tk.BooleanVar()
        self.continuous_rendering.set(False)
        file_menu.add_checkbutton(label="Continuous Markdown to HTML rendering",
                onvalue=True, offvalue=False,
                variable=self.continuous_rendering)

        file_menu.add_command(label = "Render reST to HTML", underline=7,
                command=self.cmd_rest, accelerator="Ctrl+R")
        self.root.bind_all("<Control-r>", self.cmd_rest)
        
        file_menu.add_separator()

        file_menu.add_command(label = "Exit", underline=1,
                              command=self.handler_close, accelerator="Ctrl+Q")
        self.root.bind_all("<Control-q>", self.handler_close)

        # EDIT ##########################################################
        edit_menu = tk.Menu(menu, tearoff=False)
        menu.add_cascade(label="Edit", underline=0, menu=edit_menu)
        
        edit_menu.add_command(label="Undo", accelerator="Ctrl+Z",
                              underline=0, command=lambda: self.text_note.edit_undo())
        self.root.bind_all("<Control-z>", lambda e: self.text_note.edit_undo())
        
        edit_menu.add_command(label="Redo", accelerator="Ctrl+Y",
                              underline=0, command=lambda: self.text_note.edit_undo())
        self.root.bind_all("<Control-y>", lambda e: self.text_note.edit_redo())
                
        
        edit_menu.add_separator()
        
        edit_menu.add_command(label="Cut", accelerator="Ctrl+X",
                              underline=2, command=self.cmd_cut)
        edit_menu.add_command(label="Copy", accelerator="Ctrl+C",
                              underline=0, command=self.cmd_copy)
        edit_menu.add_command(label="Paste", accelerator="Ctrl+V",
                              underline=0, command=self.cmd_paste)

        edit_menu.add_command(label="Select All", accelerator="Ctrl+A",
                              underline=7, command=self.cmd_select_all)
        # FIXME: ctrl-a is usually bound to start-of-line. What's a
        # better binding for select all then?

        edit_menu.add_separator()
        
        edit_menu.add_command(label="Find", accelerator="Ctrl+F",
                              underline=0, command=lambda: self.search_entry.focus())
        self.root.bind_all("<Control-f>", self.search)

        # TOOLS ########################################################
        tools_menu = tk.Menu(menu, tearoff=False)
        menu.add_cascade(label="Tools", underline=0, menu=tools_menu)

        tools_menu.add_command(label="Word Count",
            underline=0, command=self.word_count)

        # the internet thinks that multiple modifiers should work, but this didn't
        # want to.
        #self.root.bind_all("<Control-Shift-c>", lambda e: self.word_count())

        # HELP ##########################################################
        help_menu = tk.Menu(menu, tearoff=False)
        menu.add_cascade(label="Help", underline='0', menu=help_menu)

        help_menu.add_command(label = "About", underline = 0,
                              command = self.cmd_help_about)
        help_menu.add_command(label = "Bindings", underline = 0,
                              command = self.cmd_help_bindings,
                              accelerator="Ctrl+?")


        # END MENU ######################################################

    def _create_ui(self):

        # these two variables determine the final dimensions of our interface
        #FRAME_HEIGHT=400
        TEXT_WIDTH=80

        # set the correct class name. this helps your desktop environment
        # to identify the nvPY window.
        self.root = tk.Tk(className="nvPY")

        self.root.title("nvPY")
        #self.root.configure(background="#b2b2b2")

        # with iconphoto we have to use gif, also on windows
        icon_fn = 'nvpy.gif'

        iconpath = os.path.join(
            self.config.app_dir, 'icons', icon_fn)

        self.icon = tk.PhotoImage(file=iconpath)
        self.root.tk.call('wm', 'iconphoto', self.root._w, self.icon)

        # create menu ###################################################
        self._create_menu()

        # separator after menu ##########################################
        #separator = tk.Frame(self.root, height=2, bd=1, relief=tk.SUNKEN)
        #separator.pack(fill=tk.X, padx=5, pady=2, side=tk.TOP)

        # setup statusbar ###############################################
        # first pack this before panedwindow, else behaviour is unexpected
        # during sash moving and resizing
        self.statusbar = StatusBar(self.root)
        self.statusbar.set_status('%s', 'Welcome to nvPY!')
        self.statusbar.pack(fill=tk.X, side=tk.BOTTOM, padx=3, pady=3)

        search_frame = tk.Frame(self.root)
        
        search_entry.make_style()
        self.search_entry_var = tk.StringVar()
        self.search_entry = TriggeredcompleteEntry(search_frame, self.config.case_sensitive, textvariable=self.search_entry_var, style="Search.entry")
        self.search_entry_var.trace('w', self.handler_search_entry)

        cs_label = tk.Label(search_frame,text="CS ")
        self.cs_checkbutton_var = tk.IntVar()
        cs_checkbutton = tk.Checkbutton(search_frame, variable=self.cs_checkbutton_var)
        self.cs_checkbutton_var.trace('w', self.handler_cs_checkbutton)

        self.search_mode_options = ("gstyle", "regexp")
        self.search_mode_var = tk.StringVar()
        # I'm working with ttk.OptionVar, which has that extra default param!
        self.search_mode_cb = tk.OptionMenu(search_frame, self.search_mode_var,
            self.search_mode_options[0], *self.search_mode_options)
        self.search_mode_cb.config(width=6)
        self.search_mode_var.trace('w', self.handler_search_mode)

        self.search_mode_cb.pack(side=tk.RIGHT, padx=5)
        cs_checkbutton.pack(side=tk.RIGHT)
        cs_label.pack(side=tk.RIGHT)
        self.search_entry.pack(fill=tk.X,padx=5, pady=5)


        search_frame.pack(side=tk.TOP, fill=tk.X)
        
        
        # the paned window ##############################################
        
        if self.config.layout == "horizontal":
            paned_window = tk.PanedWindow(self.root, orient=tk.HORIZONTAL)
            paned_window.pack(fill=tk.BOTH, expand=1)
            
            list_frame = tk.Frame(paned_window, width=100)
            paned_window.add(list_frame)

            self.notes_list = NotesList(
                list_frame,
                self.config.list_font_family,
                self.config.list_font_size,
                utils.KeyValueObject(background_color=self.config.background_color,
                    layout=self.config.layout,
                    print_columns=self.config.print_columns))
            self.notes_list.pack(fill=tk.BOTH, expand=1)

            note_frame = tk.Frame(paned_window, width=400)

        else:
            paned_window = tk.PanedWindow(self.root, orient=tk.VERTICAL)
            paned_window.pack(fill=tk.BOTH, expand=1)
            
            list_frame = tk.Frame(paned_window, height=150)
            list_frame.pack_propagate(0)
            paned_window.add(list_frame)

            if self.config.print_columns == 1:
                font_family=self.config.list_font_family_fixed

            else:
                font_family=self.config.list_font_family

            self.notes_list = NotesList(
                list_frame,
                font_family,
                self.config.list_font_size,
                utils.KeyValueObject(background_color=self.config.background_color,
                    layout=self.config.layout,
                    print_columns=self.config.print_columns))
            self.notes_list.pack(fill=tk.X, expand=1)

            note_frame = tk.Frame(paned_window)

        paned_window.add(note_frame)

        note_meta_frame = tk.Frame(note_frame)
        note_meta_frame.pack(side=tk.BOTTOM, fill=tk.X)

        pinned_label = tk.Label(note_meta_frame,text="Pinned")
        pinned_label.pack(side=tk.LEFT)
        self.pinned_checkbutton_var = tk.IntVar()
        self.pinned_checkbutton = tk.Checkbutton(note_meta_frame, variable=self.pinned_checkbutton_var)
        self.pinned_checkbutton.pack(side=tk.LEFT)

        tags_label = tk.Label(note_meta_frame, text="Tags")
        tags_label.pack(side=tk.LEFT)
        self.tags_entry_var = tk.StringVar()
        self.tags_entry = tk.Entry(note_meta_frame, textvariable=self.tags_entry_var)
        self.tags_entry.pack(side=tk.LEFT, fill=tk.X, expand=1, pady=3, padx=3)


        # we'll use this method to create the different edit boxes
        def create_scrolled_text(master):
            yscrollbar = tk.Scrollbar(master)
            yscrollbar.pack(side=tk.RIGHT, fill=tk.Y)

            #f = tkFont.nametofont('TkFixedFont')
            f = tkFont.Font(family=self.config.font_family,
                            size=self.config.font_size)
            # tkFont.families(root) returns list of available font family names
            # this determines the width of the complete interface (yes)
            text = RedirectedText(master, height=25, width=TEXT_WIDTH,
                                  wrap=tk.WORD,
                                  font=f, tabs=(4 * f.measure(0), 'left'), tabstyle='wordprocessor',
                                  yscrollcommand=yscrollbar.set,
                                  undo=True,
                                  background = self.config.background_color)
            # change default font at runtime with:
            text.config(font=f)

            # need expand=1 so that when user resizes window, text widget gets the extra space
            text.pack(fill=tk.BOTH, expand=1)


            #xscrollbar.config(command=text.xview)
            yscrollbar.config(command=text.yview)

            return text


        # setup user_text ###############################################
        self.text_note = create_scrolled_text(note_frame)
        self.fonts = self.notes_list.fonts + self.text_note.fonts

        # finish UI creation ###########################################

        # now set the minsize so that things can not disappear
        self.root.minsize(self.root.winfo_width(), self.root.winfo_height())
        
        # call update so we know that sizes are up to date
        self.root.update_idletasks()

    def get_number_of_notes(self):
        return self.notes_list.get_number_of_notes()

    def handler_close(self, evt=None):
        """Handler for exit menu command and close window event.
        """
        self.notify_observers('close', None)

    def clear_note_ui(self, silent=True):
        """Called when no note has been selected.

        Should give the user clear indication that no note has been selected,
        hence no note editing actions can be taken.

        @param silent: The default is not to fire any event handlers when
        clearing the note.
        @return:
        """

        # ascii art created with: http://patorjk.com/software/taag/

        msg = """
        No note currently selected.

        Either select a note, or press Ctrl-N to create
        a new note titled with the current search string,
        or modify the search string.

        .__   __. ____    ____ .______   ____    ____
        |  \ |  | \   \  /   / |   _  \  \   \  /   /
        |   \|  |  \   \/   /  |  |_)  |  \   \/   /
        |  . `  |   \      /   |   ___/    \_    _/
        |  |\   |    \    /    |  |          |  |
        |__| \__|     \__/     | _|          |__|


        """

        if silent:
            self.mute_note_data_changes()

        self.text_note.delete(1.0, tk.END) # clear all
        self.text_note.insert(1.0, msg)
        self.tags_entry_var.set('')

        self.statusbar.set_note_status('No note selected.')

        if silent:
            self.unmute_note_data_changes()
        
    def close(self):
        """Programmatically close application windows.
        
        Called by controller. 
        """
        self.root.destroy()

    def cmd_cut(self):
        self.text_note.event_generate('<<Cut>>')

    def cmd_copy(self):
        self.text_note.event_generate('<<Copy>>')

    def cmd_markdown(self, event=None):
        self.notify_observers('command:markdown', None)
        
    def cmd_paste(self):
        self.text_note.event_generate('<<Paste>>')


    def cmd_help_about(self):

        tkMessageBox.showinfo(
            'Help | About',
            'nvPY %s is copyright 2012 by Charl P. Botha '
            '<http://charlbotha.com/>\n\n'
            'A rather ugly but cross-platform simplenote client.' % (self.config.app_version,),
            parent = self.root)

    def cmd_help_bindings(self):
        h = HelpBindings()
        self.root.wait_window(h)

    def cmd_rest(self, event=None):
        self.notify_observers('command:rest', None)

    def cmd_sync_current_note(self, event=None):
        self.notify_observers('command:sync_current_note', None)
        
    def cmd_sync_full(self, event=None):
        self.notify_observers('command:sync_full', None)

    def cmd_font_size(self, inc_size):
        for f in self.fonts:
            f.configure(size=f['size'] + inc_size)

    def handler_cs_checkbutton(self, *args):
        self.notify_observers('change:cs',
            utils.KeyValueObject(value=self.cs_checkbutton_var.get()))

    def handler_housekeeper(self):
        # nvPY will do saving and syncing!
        self.notify_observers('keep:house', None)
        
        # check if titles need refreshing
        refresh_notes_list = False
        prev_title = None
        prev_modifydate = None
        prev_pinned = 0
        for i,o in enumerate(self.notes_list_model.list):
            # order should be the same as our listbox
            nt = utils.get_note_title(o.note)
            ot = self.notes_list.get_title(i)
            # if we strike a note with an out-of-date title, redo.
            if nt != ot:
                logging.debug('title "%s" resync' % (nt,))
                refresh_notes_list = True
                break

            # compare modifydate timestamp in our notes_list_model to what's displayed
            # if these are more than 60 seconds apart, we want to update our
            # mod-date display.
            md = float(o.note.get('modifydate', 0))
            omd = self.notes_list.get_modifydate(i)
            if abs(md - omd) > 60:
                # we log the title
                logging.debug('modifydate "%s" resync' % (nt,))
                refresh_notes_list = True
                break

            pinned = utils.note_pinned(o.note)
            old_pinned = self.notes_list.get_pinned(i)
            if pinned != old_pinned:
                # we log the title
                logging.debug('pinned "%s" resync' % (nt,))
                refresh_notes_list = True
                break

            tags = o.note.get('tags', 0)
            old_tags = self.notes_list.get_tags(i)
            if tags != old_tags:
                # we log the title
                logging.debug('tags "%s" resync' % (nt,))
                refresh_notes_list = True
                break

            if self.config.sort_mode == 0:
                # alpha
                if prev_title is not None and prev_title > nt:
                    logging.debug("alpha resort triggered")
                    refresh_notes_list = True
                    break
                
                prev_title = nt
                
            else:

                # we go from top to bottom, newest to oldest
                # this means that prev_modifydate (above) needs to be larger
                # than md (below). if it's not, re-sort.
                if prev_modifydate is not None and prev_modifydate < md and \
                   not prev_pinned:
                    logging.debug("modifydate resort triggered")
                    refresh_notes_list = True
                    break
                
                prev_modifydate = md
                if self.config.pinned_ontop:
                    prev_pinned = utils.note_pinned(o.note)
            
        if refresh_notes_list:
            self.refresh_notes_list()
        
        self.root.after(self.config.housekeeping_interval_ms, self.handler_housekeeper)
        
    def handler_pinned_checkbutton(self, *args):
        self.notify_observers('change:pinned',
            utils.KeyValueObject(value=self.pinned_checkbutton_var.get()))

    def handler_search_enter(self, evt):
        # user has pressed enter whilst searching
        # 1. if a note is selected, focus that
        # 2. if nothing is selected, create a new note with this title

        if self.notes_list.selected_idx >= 0:
            self.text_note.focus()
            self.text_note.see(tk.INSERT)
            
        else:
            # nothing selected
            self.notify_observers('create:note', utils.KeyValueObject(title=self.get_search_entry_text()))
            # the note will be created synchronously, so we can focus the text area already
            self.text_note.focus()
        
    def handler_search_entry(self, *args):
        self.notify_observers('change:entry',
                              utils.KeyValueObject(value=self.search_entry_var.get()))

    def handler_search_mode(self, *args):
        """
        Called when the user changes the search mode via the OptionMenu.

        This will also be called even if the user reselects the same option.

        @param args:
        @return:
        """

        self.notify_observers('change:search_mode',
            utils.KeyValueObject(value=self.search_mode_var.get()))


    def handler_tags_entry(self, *args):
        self.notify_observers('change:tags',
            utils.KeyValueObject(value=self.tags_entry_var.get()))

    def handler_click_link(self, link):
        if link.startswith('[['):
            link = link[2:-2]
            self.notify_observers('click:notelink', link)

        else:
            webbrowser.open(link)
            
    def activate_search_string_highlights(self):
        # no note selected, so no highlights.
        if self.notes_list.selected_idx < 0:
            return

        t = self.text_note
        
        # remove all existing tags
        for tag in self.text_tags_search:
            t.tag_remove(tag, '1.0', 'end')
        
        del self.text_tags_search[:]
        
        st = self.notes_list_model.match_regexp
        if not st:
            return
        
        # take care of invalid regular expressions...
        try:
            if self.config.case_sensitive == 0:
                pat = re.compile(st, re.I)
            else:
                pat = re.compile(st)

        except re.error:
            return
        
        for mo in pat.finditer(t.get('1.0', 'end')):

            # start creating a new tkinter text tag
            tag = 'search-%d' % (len(self.text_tags_search),)
            t.tag_config(tag, background="yellow")

            # mo.start(), mo.end() or mo.span() in one go
            t.tag_add(tag, '1.0+%dc' % (mo.start(),), '1.0+%dc' %
                    (mo.end(),))

            # record the tag name so we can delete it later
            self.text_tags_search.append(tag)
            
        

    def activate_links(self):
        """
        Also see this post on URL detection regular expressions:
        http://www.regexguru.com/2008/11/detecting-urls-in-a-block-of-text/
        (mine is slightly modified)
        """


        t = self.text_note
        # the last group matches [[bla bla]] inter-note links
        pat = \
        r"\b((https?|ftp|file)://[-A-Za-z0-9+&@#/%?=~_|!:,.;]*[A-Za-z0-9+&@#/%=~_|])|(\[\[[^][]*\]\])"

        # remove all existing tags
        for tag in self.text_tags_links:
            t.tag_remove(tag, '1.0', 'end')

        del self.text_tags_links[:]
        
        for mo in re.finditer(pat,t.get('1.0', 'end')):
            # extract the link from the match object
            if mo.groups()[2] is not None:
                link = mo.groups()[2]
                ul = 0
            else:
                link = mo.groups()[0]
                ul = 1

            # start creating a new tkinter text tag
            tag = 'web-%d' % (len(self.text_tags_links),)
            t.tag_config(tag, foreground="blue", underline=ul)
            # hovering should give us the finger (cursor) hehe
            t.tag_bind(tag, '<Enter>', 
                    lambda e: t.config(cursor="hand2"))
            t.tag_bind(tag, '<Leave>', 
                    lambda e: t.config(cursor=""))
            # and clicking on it should do something sensible
            t.tag_bind(tag, '<Button-1>', lambda e, link=link:
                    self.handler_click_link(link))

            # mo.start(), mo.end() or mo.span() in one go
            t.tag_add(tag, '1.0+%dc' % (mo.start(),), '1.0+%dc' %
                    (mo.end(),))

            # record the tag name so we can delete it later
            self.text_tags_links.append(tag)


    def handler_text_change(self, evt):
        self.notify_observers('change:text', None)
        # FIXME: consider having this called from the housekeeping
        # handler, so that the poor regexp doesn't have to do every
        # single keystroke.
        self.activate_links()
        self.activate_search_string_highlights()

    def is_note_different(self, note):
        """
        Determine if note would cause a UI update.
        """

        if self.get_text() != note.get('content'):
            return True

        tags = note.get('tags', [])
        # get list of string tags from ui
        ui_tags = utils.sanitise_tags(self.tags_entry_var.get())
        if ui_tags != tags:
            return True

        if bool(self.pinned_checkbutton_var.get()) != bool(utils.note_pinned(note)):
            return True

    def observer_notes_list(self, notes_list_model, evt_type, evt):
        if evt_type == 'set:list':
            # re-render!
            self.set_notes(notes_list_model.list)
            
    def main_loop(self):
        self.root.mainloop()

    def mute_note_data_changes(self):
        self.mute('change:text')
        self.mute('change:tags')
        self.mute('change:pinned')

    def search(self,e):
        self.search_entry.focus()
        self.search_entry.selection_range(0,tk.END)

    def set_cs(self, cs, silent=False):
        if silent:
            self.mute('change:cs')

        self.cs_checkbutton_var.set(cs)

        self.unmute('change:cs')

    def set_search_mode(self, search_mode, silent=False):
        """

        @param search_mode: the search mode, "gstyle" or "regexp"
        @param silent: Specify True if you don't want the view to trigger any events.
        @return:
        """

        if silent:
            self.mute('change:search_mode')

        self.search_mode_var.set(search_mode)

        self.unmute('change:search_mode')
        
    def set_status_text(self, txt):
        self.statusbar.set_status(txt)
        
    def set_note_data(self, note, reset_undo=True, content_unchanged=False):
        """Replace text in editor with content.
        
        This is usually called when a new note is selected (case 1), or
        when a modified note comes back from the server (case 2).
        
        @param reset_undo: Set to False if you don't want to have the undo
        buffer to reset.
        @param content_unchanged: Set to True if you know that the content
        has not changed, only the tags and pinned status.
        """

        if not content_unchanged:
            self.text_note.delete(1.0, tk.END) # clear all

        if note is not None:
            if not content_unchanged:
                self.text_note.insert(tk.END, note['content'])

            # default to an empty array for tags
            tags=note.get('tags', [])
            self.tags_entry_var.set(','.join(tags))
            self.pinned_checkbutton_var.set(utils.note_pinned(note))

        if reset_undo:
            # usually when a new note is selected, we want to reset the
            # undo buffer, so that a user can't undo right into the previously
            # selected note.
            self.text_note.edit_reset()
        
        
    def set_notes(self, notes):
        # this method is called by View.observer_notes_list()

        # clear the notes list
        self.notes_list.clear()
        taglist = []

        for o in notes:
            tags = o.note.get('tags')
            if tags:
                taglist += tags

            self.notes_list.append(o.note, utils.KeyValueObject(tagfound=o.tagfound))

        if self.taglist is None:
            # first time we get called, so we need to initialise
            self.taglist = taglist
            self.search_entry.set_completion_list(self.taglist)

        else:
            # only set completion list if the new combined taglist is larger.
            taglist = list(set(self.taglist + taglist))
            if len(taglist) > len(self.taglist):
                self.taglist=taglist
                self.search_entry.set_completion_list(self.taglist)


    def show_error(self, title, msg):
        tkMessageBox.showerror(title, msg)

    def show_info(self, title, msg):        
        tkMessageBox.showinfo(title, msg,parent = self.root)

    def show_warning(self, title, msg):
        tkMessageBox.showwarning(title, msg)

    def unmute_note_data_changes(self):
        self.unmute('change:text')
        self.unmute('change:tags')
        self.unmute('change:pinned')


    def update_selected_note_data(self, note):
        """
        Update currently selected note's data.

        This is called when the user triggers a per-note sync and a newer
        note comes back, but also when the search string changes, and the
        currently selected note gets a newer version due to background or
        foreground syncing.

        We take care only to update the note content if it has actually
        changed, to minimise visual glitches.
        """

        # the user is not changing anything, so we don't want the event to fire
        self.mute_note_data_changes()

        current_content = self.get_text()
        new_content = note.get('content', '')

        if new_content != current_content:
            # store cursor position
            cursor_pos = self.text_note.index(tk.INSERT)
            # also store visible window
            first, last = self.text_note.yview()

            # set new note contents, pinned status and tags
            # but keep user's undo buffer
            self.set_note_data(note, reset_undo=False)

            # restore visible window
            self.text_note.yview('moveto', first)
            self.text_note.mark_set(tk.INSERT, cursor_pos)
            self.activate_links()
            self.activate_search_string_highlights()

        else:
            # we know the content is the same, so we only set the rest
            # obviously keep user's undo buffer.
            self.set_note_data(note, reset_undo=False, content_unchanged=True)

        # reactivate event handlers
        self.unmute_note_data_changes()


    def word_count(self):
        """
        Display count of total words and selected words in a dialog box.
        """

        sel = self.get_selected_text()
        slen = len(sel.split())

        txt = self.get_text()
        tlen = len(txt.split())

        self.show_info('Word Count', '%d words in total\n%d words in selection' % (tlen,slen))

########NEW FILE########
__FILENAME__ = __main__
import nvpy
nvpy.main()


########NEW FILE########
