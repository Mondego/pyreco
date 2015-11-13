__FILENAME__ = cards
# -*- coding: utf-8 -*-
# Copyright: Damien Elmes <anki@ichi2.net>
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

import time
from anki.utils import intTime, hexifyID, timestampID, joinFields
from anki.consts import *

# temporary
_warned = False
def warn():
    global _warned
    if _warned:
        return
    import sys
    sys.stderr.write("Ignore the above, please download the fix assertion addon.")
    _warned = True

# Cards
##########################################################################

# Type: 0=new, 1=learning, 2=due
# Queue: same as above, and:
#        -1=suspended, -2=user buried, -3=sched buried
# Due is used differently for different queues.
# - new queue: note id or random int
# - rev queue: integer day
# - lrn queue: integer timestamp

class Card(object):

    def __init__(self, col, id=None):
        self.col = col
        self.timerStarted = None
        self._qa = None
        self._note = None
        if id:
            self.id = id
            self.load()
        else:
            # to flush, set nid, ord, and due
            self.id = timestampID(col.db, "cards")
            self.did = 1
            self.crt = intTime()
            self.type = 0
            self.queue = 0
            self.ivl = 0
            self.factor = 0
            self.reps = 0
            self.lapses = 0
            self.left = 0
            self.odue = 0
            self.odid = 0
            self.flags = 0
            self.data = ""

    def load(self):
        (self.id,
         self.nid,
         self.did,
         self.ord,
         self.mod,
         self.usn,
         self.type,
         self.queue,
         self.due,
         self.ivl,
         self.factor,
         self.reps,
         self.lapses,
         self.left,
         self.odue,
         self.odid,
         self.flags,
         self.data) = self.col.db.first(
             "select * from cards where id = ?", self.id)
        self._qa = None
        self._note = None

    def flush(self):
        self.mod = intTime()
        self.usn = self.col.usn()
        # bug check
        if self.queue == 2 and self.odue and not self.col.decks.isDyn(self.did):
            warn()
        assert self.due < 4294967296
        self.col.db.execute(
            """
insert or replace into cards values
(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            self.id,
            self.nid,
            self.did,
            self.ord,
            self.mod,
            self.usn,
            self.type,
            self.queue,
            self.due,
            self.ivl,
            self.factor,
            self.reps,
            self.lapses,
            self.left,
            self.odue,
            self.odid,
            self.flags,
            self.data)

    def flushSched(self):
        self.mod = intTime()
        self.usn = self.col.usn()
        # bug checks
        if self.queue == 2 and self.odue and not self.col.decks.isDyn(self.did):
            warn()
        assert self.due < 4294967296
        self.col.db.execute(
            """update cards set
mod=?, usn=?, type=?, queue=?, due=?, ivl=?, factor=?, reps=?,
lapses=?, left=?, odue=?, odid=?, did=? where id = ?""",
            self.mod, self.usn, self.type, self.queue, self.due, self.ivl,
            self.factor, self.reps, self.lapses,
            self.left, self.odue, self.odid, self.did, self.id)

    def q(self, reload=False, browser=False):
        return self.css() + self._getQA(reload, browser)['q']

    def a(self):
        return self.css() + self._getQA()['a']

    def css(self):
        return "<style>%s</style>" % self.model()['css']

    def _getQA(self, reload=False, browser=False):
        if not self._qa or reload:
            f = self.note(reload); m = self.model(); t = self.template()
            data = [self.id, f.id, m['id'], self.odid or self.did, self.ord,
                    f.stringTags(), f.joinedFields()]
            if browser:
                args = (t.get('bqfmt'), t.get('bafmt'))
            else:
                args = tuple()
            self._qa = self.col._renderQA(data, *args)
        return self._qa

    def note(self, reload=False):
        if not self._note or reload:
            self._note = self.col.getNote(self.nid)
        return self._note

    def model(self):
        return self.col.models.get(self.note().mid)

    def template(self):
        m = self.model()
        if m['type'] == MODEL_STD:
            return self.model()['tmpls'][self.ord]
        else:
            return self.model()['tmpls'][0]

    def startTimer(self):
        self.timerStarted = time.time()

    def timeLimit(self):
        "Time limit for answering in milliseconds."
        conf = self.col.decks.confForDid(self.odid or self.did)
        return conf['maxTaken']*1000

    def shouldShowTimer(self):
        conf = self.col.decks.confForDid(self.odid or self.did)
        return conf['timer']

    def timeTaken(self):
        "Time taken to answer card, in integer MS."
        total = int((time.time() - self.timerStarted)*1000)
        return min(total, self.timeLimit())

    def isEmpty(self):
        ords = self.col.models.availOrds(
            self.model(), joinFields(self.note().fields))
        if self.ord not in ords:
            return True

########NEW FILE########
__FILENAME__ = collection
# -*- coding: utf-8 -*-
# Copyright: Damien Elmes <anki@ichi2.net>
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

import time, os, random, re, stat, datetime, copy, shutil, sys
from anki.lang import _, ngettext
from anki.utils import ids2str, hexifyID, checksum, fieldChecksum, stripHTML, \
    intTime, splitFields, joinFields, maxID, json
from anki.hooks import runHook, runFilter
from anki.sched import Scheduler
from anki.models import ModelManager
from anki.media import MediaManager
from anki.decks import DeckManager
from anki.tags import TagManager
from anki.consts import *
from anki.errors import AnkiError
from anki.sound import stripSounds

import anki.latex # sets up hook
import anki.cards, anki.notes, anki.template, anki.find

defaultConf = {
    # review options
    'activeDecks': [1],
    'curDeck': 1,
    'newSpread': NEW_CARDS_DISTRIBUTE,
    'collapseTime': 1200,
    'timeLim': 0,
    'estTimes': True,
    'dueCounts': True,
    # other config
    'curModel': None,
    'nextPos': 1,
    'sortType': "noteFld",
    'sortBackwards': False,
    'addToCur': True, # add new to currently selected deck?
}

# this is initialized by storage.Collection
class _Collection(object):

    def __init__(self, db, server=False):
        self.db = db
        self.path = db._path
        self.server = server
        self._lastSave = time.time()
        self.clearUndo()
        self.media = MediaManager(self, server)
        self.models = ModelManager(self)
        self.decks = DeckManager(self)
        self.tags = TagManager(self)
        self.load()
        if not self.crt:
            d = datetime.datetime.today()
            d -= datetime.timedelta(hours=4)
            d = datetime.datetime(d.year, d.month, d.day)
            d += datetime.timedelta(hours=4)
            self.crt = int(time.mktime(d.timetuple()))
        self.sched = Scheduler(self)
        # check for improper shutdown
        self.cleanup()

    def name(self):
        n = os.path.splitext(os.path.basename(self.path))[0]
        return n

    # DB-related
    ##########################################################################

    def load(self):
        (self.crt,
         self.mod,
         self.scm,
         self.dty,
         self._usn,
         self.ls,
         self.conf,
         models,
         decks,
         dconf,
         tags) = self.db.first("""
select crt, mod, scm, dty, usn, ls,
conf, models, decks, dconf, tags from col""")
        self.conf = json.loads(self.conf)
        self.models.load(models)
        self.decks.load(decks, dconf)
        self.tags.load(tags)

    def setMod(self):
        """Mark DB modified.

DB operations and the deck/tag/model managers do this automatically, so this
is only necessary if you modify properties of this object or the conf dict."""
        self.db.mod = True

    def flush(self, mod=None):
        "Flush state to DB, updating mod time."
        self.mod = intTime(1000) if mod is None else mod
        self.db.execute(
            """update col set
crt=?, mod=?, scm=?, dty=?, usn=?, ls=?, conf=?""",
            self.crt, self.mod, self.scm, self.dty,
            self._usn, self.ls, json.dumps(self.conf))

    def save(self, name=None, mod=None):
        "Flush, commit DB, and take out another write lock."
        # let the managers conditionally flush
        self.models.flush()
        self.decks.flush()
        self.tags.flush()
        # and flush deck + bump mod if db has been changed
        if self.db.mod:
            self.flush(mod=mod)
            self.db.commit()
            self.lock()
            self.db.mod = False
        self._markOp(name)
        self._lastSave = time.time()

    def autosave(self):
        "Save if 5 minutes has passed since last save."
        if time.time() - self._lastSave > 300:
            self.save()

    def lock(self):
        # make sure we don't accidentally bump mod time
        mod = self.db.mod
        self.db.execute("update col set mod=mod")
        self.db.mod = mod

    def close(self, save=True):
        "Disconnect from DB."
        if self.db:
            self.cleanup()
            if save:
                self.save()
            else:
                self.rollback()
            if not self.server:
                self.db.execute("pragma journal_mode = delete")
            self.db.close()
            self.db = None
            self.media.close()

    def reopen(self):
        "Reconnect to DB (after changing threads, etc)."
        import anki.db
        if not self.db:
            self.db = anki.db.DB(self.path)
            self.media.connect()

    def rollback(self):
        self.db.rollback()
        self.load()
        self.lock()

    def modSchema(self, check=True):
        "Mark schema modified. Call this first so user can abort if necessary."
        if not self.schemaChanged():
            if check and not runFilter("modSchema", True):
                raise AnkiError("abortSchemaMod")
        self.scm = intTime(1000)

    def schemaChanged(self):
        "True if schema changed since last sync."
        return self.scm > self.ls

    def setDirty(self):
        "Signal there are temp. suspended cards that need cleaning up on close."
        self.dty = True

    def cleanup(self):
        "Unsuspend any temporarily suspended cards."
        if self.dty:
            self.sched.unburyCards()
            self.dty = False

    def usn(self):
        return self._usn if self.server else -1

    def beforeUpload(self):
        "Called before a full upload."
        tbls = "notes", "cards", "revlog", "graves"
        for t in tbls:
            self.db.execute("update %s set usn=0 where usn=-1" % t)
        self._usn += 1
        self.models.beforeUpload()
        self.tags.beforeUpload()
        self.decks.beforeUpload()
        self.modSchema()
        self.ls = self.scm
        self.close()

    # Object creation helpers
    ##########################################################################

    def getCard(self, id):
        return anki.cards.Card(self, id)

    def getNote(self, id):
        return anki.notes.Note(self, id=id)

    # Utils
    ##########################################################################

    def nextID(self, type, inc=True):
        type = "next"+type.capitalize()
        id = self.conf.get(type, 1)
        if inc:
            self.conf[type] = id+1
        return id

    def reset(self):
        "Rebuild the queue and reload data after DB modified."
        self.sched.reset()

    # Deletion logging
    ##########################################################################

    def _logRem(self, ids, type):
        self.db.executemany("insert into graves values (%d, ?, %d)" % (
            self.usn(), type), ([x] for x in ids))

    # Notes
    ##########################################################################

    def noteCount(self):
        return self.db.scalar("select count() from notes")

    def newNote(self):
        "Return a new note with the current model."
        return anki.notes.Note(self, self.models.current())

    def addNote(self, note):
        "Add a note to the collection. Return number of new cards."
        # check we have card models available, then save
        cms = self.findTemplates(note)
        if not cms:
            return 0
        note.flush()
        # deck conf governs which of these are used
        due = self.nextID("pos")
        # add cards
        ncards = 0
        for template in cms:
            self._newCard(note, template, due)
            ncards += 1
        return ncards

    def remNotes(self, ids):
        self.remCards(self.db.list("select id from cards where nid in "+
                                   ids2str(ids)))

    def _remNotes(self, ids):
        "Bulk delete notes by ID. Don't call this directly."
        if not ids:
            return
        strids = ids2str(ids)
        # we need to log these independently of cards, as one side may have
        # more card templates
        self._logRem(ids, REM_NOTE)
        self.db.execute("delete from notes where id in %s" % strids)

    # Card creation
    ##########################################################################

    def findTemplates(self, note):
        "Return (active), non-empty templates."
        model = note.model()
        avail = self.models.availOrds(model, joinFields(note.fields))
        return self._tmplsFromOrds(model, avail)

    def _tmplsFromOrds(self, model, avail):
        ok = []
        if model['type'] == MODEL_STD:
            for t in model['tmpls']:
                if t['ord'] in avail:
                    ok.append(t)
        else:
            # cloze - generate temporary templates from first
            for ord in avail:
                t = copy.copy(model['tmpls'][0])
                t['ord'] = ord
                ok.append(t)
        return ok

    def genCards(self, nids):
        "Generate cards for non-empty templates, return ids to remove."
        # build map of (nid,ord) so we don't create dupes
        snids = ids2str(nids)
        have = {}
        dids = {}
        for id, nid, ord, did in self.db.execute(
            "select id, nid, ord, did from cards where nid in "+snids):
            # existing cards
            if nid not in have:
                have[nid] = {}
            have[nid][ord] = id
            # and their dids
            if nid in dids:
                if dids[nid] and dids[nid] != did:
                    # cards are in two or more different decks; revert to
                    # model default
                    dids[nid] = None
            else:
                # first card or multiple cards in same deck
                dids[nid] = did
        # build cards for each note
        data = []
        ts = maxID(self.db)
        now = intTime()
        rem = []
        usn = self.usn()
        for nid, mid, flds in self.db.execute(
            "select id, mid, flds from notes where id in "+snids):
            model = self.models.get(mid)
            avail = self.models.availOrds(model, flds)
            did = dids.get(nid) or model['did']
            # add any missing cards
            for t in self._tmplsFromOrds(model, avail):
                doHave = nid in have and t['ord'] in have[nid]
                if not doHave:
                    # check deck is not a cram deck
                    did = t['did'] or did
                    if self.decks.isDyn(did):
                        did = 1
                    # if the deck doesn't exist, use default instead
                    did = self.decks.get(did)['id']
                    # we'd like to use the same due# as sibling cards, but we
                    # can't retrieve that quickly, so we give it a new id
                    # instead
                    data.append((ts, nid, did, t['ord'],
                                 now, usn, self.nextID("pos")))
                    ts += 1
            # note any cards that need removing
            if nid in have:
                for ord, id in have[nid].items():
                    if ord not in avail:
                        rem.append(id)
        # bulk update
        self.db.executemany("""
insert into cards values (?,?,?,?,?,?,0,0,?,0,0,0,0,0,0,0,0,"")""",
                            data)
        return rem

    # type 0 - when previewing in add dialog, only non-empty
    # type 1 - when previewing edit, only existing
    # type 2 - when previewing in models dialog, all templates
    def previewCards(self, note, type=0):
        if type == 0:
            cms = self.findTemplates(note)
        elif type == 1:
            cms = [c.template() for c in note.cards()]
        else:
            cms = note.model()['tmpls']
        if not cms:
            return []
        cards = []
        for template in cms:
            cards.append(self._newCard(note, template, 1, flush=False))
        return cards

    def _newCard(self, note, template, due, flush=True):
        "Create a new card."
        card = anki.cards.Card(self)
        card.nid = note.id
        card.ord = template['ord']
        card.did = template['did'] or note.model()['did']
        # if invalid did, use default instead
        deck = self.decks.get(card.did)
        if deck['dyn']:
            # must not be a filtered deck
            card.did = 1
        else:
            card.did = deck['id']
        card.due = self._dueForDid(card.did, due)
        if flush:
            card.flush()
        return card

    def _dueForDid(self, did, due):
        conf = self.decks.confForDid(did)
        # in order due?
        if conf['new']['order'] == NEW_CARDS_DUE:
            return due
        else:
            # random mode; seed with note ts so all cards of this note get the
            # same random number
            r = random.Random()
            r.seed(due)
            return r.randrange(1, max(due, 1000))

    # Cards
    ##########################################################################

    def isEmpty(self):
        return not self.db.scalar("select 1 from cards limit 1")

    def cardCount(self):
        return self.db.scalar("select count() from cards")

    def remCards(self, ids, notes=True):
        "Bulk delete cards by ID."
        if not ids:
            return
        sids = ids2str(ids)
        nids = self.db.list("select nid from cards where id in "+sids)
        # remove cards
        self._logRem(ids, REM_CARD)
        self.db.execute("delete from cards where id in "+sids)
        # then notes
        if not notes:
            return
        nids = self.db.list("""
select id from notes where id in %s and id not in (select nid from cards)""" %
                     ids2str(nids))
        self._remNotes(nids)

    def emptyCids(self):
        rem = []
        for m in self.models.all():
            rem += self.genCards(self.models.nids(m))
        return rem

    def emptyCardReport(self, cids):
        rep = ""
        for ords, cnt, flds in self.db.all("""
select group_concat(ord+1), count(), flds from cards c, notes n
where c.nid = n.id and c.id in %s group by nid""" % ids2str(cids)):
            rep += _("Empty card numbers: %(c)s\nFields: %(f)s\n\n") % dict(
                c=ords, f=flds.replace("\x1f", " / "))
        return rep

    # Field checksums and sorting fields
    ##########################################################################

    def _fieldData(self, snids):
        return self.db.execute(
            "select id, mid, flds from notes where id in "+snids)

    def updateFieldCache(self, nids):
        "Update field checksums and sort cache, after find&replace, etc."
        snids = ids2str(nids)
        r = []
        for (nid, mid, flds) in self._fieldData(snids):
            fields = splitFields(flds)
            model = self.models.get(mid)
            if not model:
                # note points to invalid model
                continue
            r.append((stripHTML(fields[self.models.sortIdx(model)]),
                      fieldChecksum(fields[0]),
                      nid))
        # apply, relying on calling code to bump usn+mod
        self.db.executemany("update notes set sfld=?, csum=? where id=?", r)

    # Q/A generation
    ##########################################################################

    def renderQA(self, ids=None, type="card"):
        # gather metadata
        if type == "card":
            where = "and c.id in " + ids2str(ids)
        elif type == "note":
            where = "and f.id in " + ids2str(ids)
        elif type == "model":
            where = "and m.id in " + ids2str(ids)
        elif type == "all":
            where = ""
        else:
            raise Exception()
        return [self._renderQA(row)
                for row in self._qaData(where)]

    def _renderQA(self, data, qfmt=None, afmt=None):
        "Returns hash of id, question, answer."
        # data is [cid, nid, mid, did, ord, tags, flds]
        # unpack fields and create dict
        flist = splitFields(data[6])
        fields = {}
        model = self.models.get(data[2])
        for (name, (idx, conf)) in self.models.fieldMap(model).items():
            fields[name] = flist[idx]
        fields['Tags'] = data[5]
        fields['Type'] = model['name']
        fields['Deck'] = self.decks.name(data[3])
        if model['type'] == MODEL_STD:
            template = model['tmpls'][data[4]]
        else:
            template = model['tmpls'][0]
        fields['Card'] = template['name']
        fields['c%d' % (data[4]+1)] = "1"
        # render q & a
        d = dict(id=data[0])
        qfmt = qfmt or template['qfmt']
        afmt = afmt or template['afmt']
        for (type, format) in (("q", qfmt), ("a", afmt)):
            if type == "q":
                format = format.replace("{{cloze:", "{{cq:%d:" % (
                    data[4]+1))
            else:
                format = format.replace("{{cloze:", "{{ca:%d:" % (
                    data[4]+1))
                fields['FrontSide'] = stripSounds(d['q'])
            fields = runFilter("mungeFields", fields, model, data, self)
            html = anki.template.render(format, fields)
            d[type] = runFilter(
                "mungeQA", html, type, fields, model, data, self)
            # empty cloze?
            if type == 'q' and model['type'] == MODEL_CLOZE:
                if not self.models._availClozeOrds(model, data[6], False):
                    d['q'] += ("<p>" + _(
                "Please edit this note and add some cloze deletions. (%s)") % (
                "<a href=%s#cloze>%s</a>" % (HELP_SITE, _("help"))))
        return d

    def _qaData(self, where=""):
        "Return [cid, nid, mid, did, ord, tags, flds] db query"
        return self.db.execute("""
select c.id, f.id, f.mid, c.did, c.ord, f.tags, f.flds
from cards c, notes f
where c.nid == f.id
%s""" % where)

    # Finding cards
    ##########################################################################

    def findCards(self, query, order=False):
        return anki.find.Finder(self).findCards(query, order)

    def findNotes(self, query):
        return anki.find.Finder(self).findNotes(query)

    def findReplace(self, nids, src, dst, regex=None, field=None, fold=True):
        return anki.find.findReplace(self, nids, src, dst, regex, field, fold)

    def findDupes(self, fieldName, search=""):
        return anki.find.findDupes(self, fieldName, search)

    # Stats
    ##########################################################################

    def cardStats(self, card):
        from anki.stats import CardStats
        return CardStats(self, card).report()

    def stats(self):
        from anki.stats import CollectionStats
        return CollectionStats(self)

    # Timeboxing
    ##########################################################################

    def startTimebox(self):
        self._startTime = time.time()
        self._startReps = self.sched.reps

    def timeboxReached(self):
        "Return (elapsedTime, reps) if timebox reached, or False."
        if not self.conf['timeLim']:
            # timeboxing disabled
            return False
        elapsed = time.time() - self._startTime
        if elapsed > self.conf['timeLim']:
            return (self.conf['timeLim'], self.sched.reps - self._startReps)

    # Undo
    ##########################################################################

    def clearUndo(self):
        # [type, undoName, data]
        # type 1 = review; type 2 = checkpoint
        self._undo = None

    def undoName(self):
        "Undo menu item name, or None if undo unavailable."
        if not self._undo:
            return None
        return self._undo[1]

    def undo(self):
        if self._undo[0] == 1:
            return self._undoReview()
        else:
            self._undoOp()

    def markReview(self, card):
        old = []
        if self._undo:
            if self._undo[0] == 1:
                old = self._undo[2]
            self.clearUndo()
        self._undo = [1, _("Review"), old + [copy.copy(card)]]

    def _undoReview(self):
        data = self._undo[2]
        c = data.pop()
        if not data:
            self.clearUndo()
        # write old data
        c.flush()
        # and delete revlog entry
        last = self.db.scalar(
            "select id from revlog where cid = ? "
            "order by id desc limit 1", c.id)
        self.db.execute("delete from revlog where id = ?", last)
        # and finally, update daily counts
        n = 1 if c.queue == 3 else c.queue
        type = ("new", "lrn", "rev")[n]
        self.sched._updateStats(c, type, -1)
        self.sched.reps -= 1
        return c.id

    def _markOp(self, name):
        "Call via .save()"
        if name:
            self._undo = [2, name]
        else:
            # saving disables old checkpoint, but not review undo
            if self._undo and self._undo[0] == 2:
                self.clearUndo()

    def _undoOp(self):
        self.rollback()
        self.clearUndo()

    # DB maintenance
    ##########################################################################

    def fixIntegrity(self):
        "Fix possible problems and rebuild caches."
        problems = []
        self.save()
        oldSize = os.stat(self.path)[stat.ST_SIZE]
        if self.db.scalar("pragma integrity_check") != "ok":
            return (_("Collection is corrupt. Please see the manual."), False)
        # note types with a missing model
        ids = self.db.list("""
select id from notes where mid not in """ + ids2str(self.models.ids()))
        if ids:
            problems.append(
                ngettext("Deleted %d note with missing note type.",
                         "Deleted %d notes with missing note type.", len(ids))
                         % len(ids))
            self.remNotes(ids)
        # cards with invalid ordinal
        for m in self.models.all():
            # ignore clozes
            if m['type'] != MODEL_STD:
                continue
            ids = self.db.list("""
select id from cards where ord not in %s and nid in (
select id from notes where mid = ?)""" %
                               ids2str([t['ord'] for t in m['tmpls']]),
                               m['id'])
            if ids:
                problems.append(
                    ngettext("Deleted %d card with missing template.",
                             "Deleted %d cards with missing template.",
                             len(ids)) % len(ids))
                self.remCards(ids)
        # delete any notes with missing cards
        ids = self.db.list("""
select id from notes where id not in (select distinct nid from cards)""")
        if ids:
            cnt = len(ids)
            problems.append(
                ngettext("Deleted %d note with no cards.",
                         "Deleted %d notes with no cards.", cnt) % cnt)
            self._remNotes(ids)
        # cards with missing notes
        ids = self.db.list("""
select id from cards where nid not in (select id from notes)""")
        if ids:
            cnt = len(ids)
            problems.append(
                ngettext("Deleted %d card with missing note.",
                         "Deleted %d cards with missing note.", cnt) % cnt)
            self.remCards(ids)
        # tags
        self.tags.registerNotes()
        # field cache
        for m in self.models.all():
            self.updateFieldCache(self.models.nids(m))
        # new cards can't have a due position > 32 bits
        self.db.execute("""
update cards set due = 1000000, mod = ?, usn = ? where due > 1000000
and queue = 0""", intTime(), self.usn())
        # new card position
        self.conf['nextPos'] = self.db.scalar(
            "select max(due)+1 from cards where type = 0") or 0
        # reviews should have a reasonable due #
        ids = self.db.list(
            "select id from cards where queue = 2 and due > 10000")
        if ids:
            problems.append("Reviews had incorrect due date.")
            self.db.execute(
                "update cards set due = 0, mod = ?, usn = ? where id in %s"
                % ids2str(ids), intTime(), self.usn())
        # and finally, optimize
        self.optimize()
        newSize = os.stat(self.path)[stat.ST_SIZE]
        txt = _("Database rebuilt and optimized.")
        ok = not problems
        problems.append(txt)
        # if any problems were found, force a full sync
        if problems:
            self.modSchema()
        self.save()
        return ("\n".join(problems), ok)

    def optimize(self):
        self.db.execute("vacuum")
        self.db.execute("analyze")
        self.lock()

########NEW FILE########
__FILENAME__ = consts
# -*- coding: utf-8 -*-
# Copyright: Damien Elmes <anki@ichi2.net>
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

import os
from anki.lang import _

# whether new cards should be mixed with reviews, or shown first or last
NEW_CARDS_DISTRIBUTE = 0
NEW_CARDS_LAST = 1
NEW_CARDS_FIRST = 2

# new card insertion order
NEW_CARDS_RANDOM = 0
NEW_CARDS_DUE = 1

# removal types
REM_CARD = 0
REM_NOTE = 1
REM_DECK = 2

# count display
COUNT_ANSWERED = 0
COUNT_REMAINING = 1

# media log
MEDIA_ADD = 0
MEDIA_REM = 1

# dynamic deck order
DYN_OLDEST = 0
DYN_RANDOM = 1
DYN_SMALLINT = 2
DYN_BIGINT = 3
DYN_LAPSES = 4
DYN_ADDED = 5
DYN_DUE = 6
DYN_REVADDED = 7

# model types
MODEL_STD = 0
MODEL_CLOZE = 1

# deck schema & syncing vars
SCHEMA_VERSION = 11
SYNC_ZIP_SIZE = int(2.5*1024*1024)
SYNC_URL = os.environ.get("SYNC_URL") or "https://ankiweb.net/sync/"
SYNC_VER = 5

HELP_SITE="http://ankisrs.net/docs/dev/manual.html"

# Labels
##########################################################################

def newCardOrderLabels():
    return {
        0: _("Show new cards in random order"),
        1: _("Show new cards in order added")
        }

def newCardSchedulingLabels():
    return {
        0: _("Mix new cards and reviews"),
        1: _("Show new cards after reviews"),
        2: _("Show new cards before reviews"),
        }

def alignmentLabels():
    return {
        0: _("Center"),
        1: _("Left"),
        2: _("Right"),
        }

def dynOrderLabels():
    return {
        0: _("Oldest seen first"),
        1: _("Random"),
        2: _("Increasing intervals"),
        3: _("Decreasing intervals"),
        4: _("Most lapses"),
        5: _("Order added"),
        6: _("Order due"),
        7: _("Latest added first"),
        }

########NEW FILE########
__FILENAME__ = db
# -*- coding: utf-8 -*-
# Copyright: Damien Elmes <anki@ichi2.net>
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

import os, time
try:
    from pysqlite2 import dbapi2 as sqlite
except ImportError:
    from sqlite3 import dbapi2 as sqlite

from anki.hooks import runHook

class DB(object):
    def __init__(self, path, text=None, timeout=0):
        encpath = path
        if isinstance(encpath, unicode):
            encpath = path.encode("utf-8")
        self._db = sqlite.connect(encpath, timeout=timeout)
        if text:
            self._db.text_factory = text
        self._path = path
        self.echo = os.environ.get("DBECHO")
        self.mod = False

    def execute(self, sql, *a, **ka):
        s = sql.strip().lower()
        # mark modified?
        for stmt in "insert", "update", "delete":
            if s.startswith(stmt):
                self.mod = True
        t = time.time()
        if ka:
            # execute("...where id = :id", id=5)
            res = self._db.execute(sql, ka)
        else:
            # execute("...where id = ?", 5)
            res = self._db.execute(sql, a)
        if self.echo:
            #print a, ka
            print sql, "%0.3fms" % ((time.time() - t)*1000)
            if self.echo == "2":
                print a, ka
        return res

    def executemany(self, sql, l):
        self.mod = True
        t = time.time()
        self._db.executemany(sql, l)
        if self.echo:
            print sql, "%0.3fms" % ((time.time() - t)*1000)
            if self.echo == "2":
                print l

    def commit(self):
        t = time.time()
        self._db.commit()
        if self.echo:
            print "commit %0.3fms" % ((time.time() - t)*1000)

    def executescript(self, sql):
        self.mod = True
        if self.echo:
            print sql
        self._db.executescript(sql)

    def rollback(self):
        self._db.rollback()

    def scalar(self, *a, **kw):
        res = self.execute(*a, **kw).fetchone()
        if res:
            return res[0]
        return None

    def all(self, *a, **kw):
        return self.execute(*a, **kw).fetchall()

    def first(self, *a, **kw):
        c = self.execute(*a, **kw)
        res = c.fetchone()
        c.close()
        return res

    def list(self, *a, **kw):
        return [x[0] for x in self.execute(*a, **kw)]

    def close(self):
        self._db.close()

    def set_progress_handler(self, *args):
        self._db.set_progress_handler(*args)

    def __enter__(self):
        self._db.execute("begin")
        return self

    def __exit__(self, exc_type, *args):
        self._db.close()

    def totalChanges(self):
        return self._db.total_changes

    def interrupt(self):
        self._db.interrupt()

########NEW FILE########
__FILENAME__ = decks
# -*- coding: utf-8 -*-
# Copyright: Damien Elmes <anki@ichi2.net>
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

import copy
from anki.utils import intTime, ids2str, json
from anki.hooks import runHook
from anki.consts import *
from anki.lang import _
from anki.errors import DeckRenameError

# fixmes:
# - make sure users can't set grad interval < 1

defaultDeck = {
    'newToday': [0, 0], # currentDay, count
    'revToday': [0, 0],
    'lrnToday': [0, 0],
    'timeToday': [0, 0], # time in ms
    'conf': 1,
    'usn': 0,
    'desc': "",
    'dyn': 0,
    'collapsed': False,
    # added in beta11
    'extendNew': 10,
    'extendRev': 50,
}

defaultDynamicDeck = {
    'newToday': [0, 0],
    'revToday': [0, 0],
    'lrnToday': [0, 0],
    'timeToday': [0, 0],
    'collapsed': False,
    'dyn': 1,
    'desc': "",
    'usn': 0,
    'delays': None,
    'separate': True,
     # list of (search, limit, order); we only use first element for now
    'terms': [["", 100, 0]],
    'resched': True,
    'return': True, # currently unused
}

defaultConf = {
    'name': _("Default"),
    'new': {
        'delays': [1, 10],
        'ints': [1, 4, 7], # 7 is not currently used
        'initialFactor': 2500,
        'separate': True,
        'order': NEW_CARDS_DUE,
        'perDay': 20,
    },
    'lapse': {
        'delays': [10],
        'mult': 0,
        'minInt': 1,
        'leechFails': 8,
        # type 0=suspend, 1=tagonly
        'leechAction': 0,
    },
    'rev': {
        'perDay': 100,
        'ease4': 1.3,
        'fuzz': 0.05,
        'minSpace': 1,
        'ivlFct': 1,
        'maxIvl': 36500,
    },
    'maxTaken': 60,
    'timer': 0,
    'autoplay': True,
    'replayq': True,
    'mod': 0,
    'usn': 0,
}

class DeckManager(object):

    # Registry save/load
    #############################################################

    def __init__(self, col):
        self.col = col

    def load(self, decks, dconf):
        self.decks = json.loads(decks)
        self.dconf = json.loads(dconf)
        self.changed = False

    def save(self, g=None):
        "Can be called with either a deck or a deck configuration."
        if g:
            g['mod'] = intTime()
            g['usn'] = self.col.usn()
        self.changed = True

    def flush(self):
        if self.changed:
            self.col.db.execute("update col set decks=?, dconf=?",
                                 json.dumps(self.decks),
                                 json.dumps(self.dconf))
            self.changed = False

    # Deck save/load
    #############################################################

    def id(self, name, create=True, type=defaultDeck):
        "Add a deck with NAME. Reuse deck if already exists. Return id as int."
        name = name.replace("'", "").replace('"', '')
        for id, g in self.decks.items():
            if g['name'].lower() == name.lower():
                return int(id)
        if not create:
            return None
        g = copy.deepcopy(type)
        if "::" in name:
            # not top level; ensure all parents exist
            name = self._ensureParents(name)
        g['name'] = name
        while 1:
            id = intTime(1000)
            if str(id) not in self.decks:
                break
        g['id'] = id
        self.decks[str(id)] = g
        self.save(g)
        self.maybeAddToActive()
        runHook("newDeck")
        return int(id)

    def rem(self, did, cardsToo=False, childrenToo=True):
        "Remove the deck. If cardsToo, delete any cards inside."
        if str(did) == '1':
            # we won't allow the default deck to be deleted, but if it's a
            # child of an existing deck then it needs to be renamed
            deck = self.get(did)
            if '::' in deck['name']:
                deck['name'] = _("Default")
                self.save(deck)
            return
        # log the removal regardless of whether we have the deck or not
        self.col._logRem([did], REM_DECK)
        # do nothing else if doesn't exist
        if not str(did) in self.decks:
            return
        deck = self.get(did)
        if deck['dyn']:
            # deleting a cramming deck returns cards to their previous deck
            # rather than deleting the cards
            self.col.sched.emptyDyn(did)
            if childrenToo:
                for name, id in self.children(did):
                    self.rem(id, cardsToo)
        else:
            # delete children first
            if childrenToo:
                # we don't want to delete children when syncing
                for name, id in self.children(did):
                    self.rem(id, cardsToo)
            # delete cards too?
            if cardsToo:
                # don't use cids(), as we want cards in cram decks too
                cids = self.col.db.list(
                    "select id from cards where did=? or odid=?", did, did)
                self.col.remCards(cids)
        # delete the deck and add a grave
        del self.decks[str(did)]
        # ensure we have an active deck
        if did in self.active():
            self.select(int(self.decks.keys()[0]))
        self.save()

    def allNames(self, dyn=True):
        "An unsorted list of all deck names."
        if dyn:
            return [x['name'] for x in self.decks.values()]
        else:
            return [x['name'] for x in self.decks.values() if not x['dyn']]

    def all(self):
        "A list of all decks."
        return self.decks.values()

    def allIds(self):
        return self.decks.keys()

    def collapse(self, did):
        deck = self.get(did)
        deck['collapsed'] = not deck['collapsed']
        self.save(deck)

    def count(self):
        return len(self.decks)

    def get(self, did, default=True):
        id = str(did)
        if id in self.decks:
            return self.decks[id]
        elif default:
            return self.decks['1']

    def byName(self, name):
        "Get deck with NAME."
        for m in self.decks.values():
            if m['name'] == name:
                return m

    def update(self, g):
        "Add or update an existing deck. Used for syncing and merging."
        self.decks[str(g['id'])] = g
        self.maybeAddToActive()
        # mark registry changed, but don't bump mod time
        self.save()

    def rename(self, g, newName):
        "Rename deck prefix to NAME if not exists. Updates children."
        # make sure target node doesn't already exist
        if newName in self.allNames():
            raise DeckRenameError(_("That deck already exists."))
        # ensure we have parents
        newName = self._ensureParents(newName)
        # rename children
        for grp in self.all():
            if grp['name'].startswith(g['name'] + "::"):
                grp['name'] = grp['name'].replace(g['name']+ "::",
                                                  newName + "::", 1)
                self.save(grp)
        # adjust name
        g['name'] = newName
        # ensure we have parents again, as we may have renamed parent->child
        newName = self._ensureParents(newName)
        self.save(g)
        # renaming may have altered active did order
        self.maybeAddToActive()

    def renameForDragAndDrop(self, draggedDeckDid, ontoDeckDid):
        draggedDeck = self.get(draggedDeckDid)
        draggedDeckName = draggedDeck['name']
        ontoDeckName = self.get(ontoDeckDid)['name']

        if ontoDeckDid == None or ontoDeckDid == '':
            if len(self._path(draggedDeckName)) > 1:
                self.rename(draggedDeck, self._basename(draggedDeckName))
        elif self._canDragAndDrop(draggedDeckName, ontoDeckName):
            draggedDeck = self.get(draggedDeckDid)
            draggedDeckName = draggedDeck['name']
            ontoDeckName = self.get(ontoDeckDid)['name']
            self.rename(draggedDeck, ontoDeckName + "::" + self._basename(draggedDeckName))

    def _canDragAndDrop(self, draggedDeckName, ontoDeckName):
        return draggedDeckName <> ontoDeckName \
                and not self._isParent(ontoDeckName, draggedDeckName) \
                and not self._isAncestor(draggedDeckName, ontoDeckName)

    def _isParent(self, parentDeckName, childDeckName):
        return self._path(childDeckName) == self._path(parentDeckName) + [ self._basename(childDeckName) ]

    def _isAncestor(self, ancestorDeckName, descendantDeckName):
        ancestorPath = self._path(ancestorDeckName)
        return ancestorPath == self._path(descendantDeckName)[0:len(ancestorPath)]

    def _path(self, name):
        return name.split("::")
    def _basename(self, name):
        return self._path(name)[-1]

    def _ensureParents(self, name):
        "Ensure parents exist, and return name with case matching parents."
        s = ""
        path = self._path(name)
        if len(path) < 2:
            return name
        for p in path[:-1]:
            if not s:
                s += p
            else:
                s += "::" + p
            # fetch or create
            did = self.id(s)
            # get original case
            s = self.name(did)
        name = s + "::" + path[-1]
        return name

    # Deck configurations
    #############################################################

    def allConf(self):
        "A list of all deck config."
        return self.dconf.values()

    def confForDid(self, did):
        deck = self.get(did, default=False)
        assert deck
        if 'conf' in deck:
            conf = self.getConf(deck['conf'])
            conf['dyn'] = False
            return conf
        # dynamic decks have embedded conf
        return deck

    def getConf(self, confId):
        return self.dconf[str(confId)]

    def updateConf(self, g):
        self.dconf[str(g['id'])] = g
        self.save()

    def confId(self, name, cloneFrom=defaultConf):
        "Create a new configuration and return id."
        c = copy.deepcopy(cloneFrom)
        while 1:
            id = intTime(1000)
            if str(id) not in self.dconf:
                break
        c['id'] = id
        c['name'] = name
        self.dconf[str(id)] = c
        self.save(c)
        return id

    def remConf(self, id):
        "Remove a configuration and update all decks using it."
        assert int(id) != 1
        self.col.modSchema()
        del self.dconf[str(id)]
        for g in self.all():
            # ignore cram decks
            if 'conf' not in g:
                continue
            if str(g['conf']) == str(id):
                g['conf'] = 1
                self.save(g)

    def setConf(self, grp, id):
        grp['conf'] = id
        self.save(grp)

    def didsForConf(self, conf):
        dids = []
        for deck in self.decks.values():
            if 'conf' in deck and deck['conf'] == conf['id']:
                dids.append(deck['id'])
        return dids

    def restoreToDefault(self, conf):
        oldOrder = conf['new']['order']
        new = copy.deepcopy(defaultConf)
        new['id'] = conf['id']
        new['name'] = conf['name']
        self.dconf[str(conf['id'])] = new
        self.save(new)
        # if it was previously randomized, resort
        if not oldOrder:
            self.col.sched.resortConf(new)

    # Deck utils
    #############################################################

    def name(self, did, default=False):
        deck = self.get(did, default=default)
        if deck:
            return deck['name']
        return _("[no deck]")

    def nameOrNone(self, did):
        deck = self.get(did, default=False)
        if deck:
            return deck['name']
        return None

    def setDeck(self, cids, did):
        self.col.db.execute(
            "update cards set did=?,usn=?,mod=? where id in "+
            ids2str(cids), did, self.col.usn(), intTime())

    def maybeAddToActive(self):
        # reselect current deck, or default if current has disappeared
        c = self.current()
        self.select(c['id'])

    def cids(self, did, children=False):
        if not children:
            return self.col.db.list("select id from cards where did=?", did)
        dids = [did]
        for name, id in self.children(did):
            dids.append(id)
        return self.col.db.list("select id from cards where did in "+
                                ids2str(dids))

    def recoverOrphans(self):
        dids = self.decks.keys()
        mod = self.col.db.mod
        self.col.db.execute("update cards set did = 1 where did not in "+
                            ids2str(dids))
        self.col.db.mod = mod

    # Deck selection
    #############################################################

    def active(self):
        "The currrently active dids. Make sure to copy before modifying."
        return self.col.conf['activeDecks']

    def selected(self):
        "The currently selected did."
        return self.col.conf['curDeck']

    def current(self):
        return self.get(self.selected())

    def select(self, did):
        "Select a new branch."
        # make sure arg is an int
        did = int(did)
        # current deck
        self.col.conf['curDeck'] = did
        # and active decks (current + all children)
        actv = self.children(did)
        actv.sort()
        self.col.conf['activeDecks'] = [did] + [a[1] for a in actv]
        self.changed = True

    def children(self, did):
        "All children of did, as (name, id)."
        name = self.get(did)['name']
        actv = []
        for g in self.all():
            if g['name'].startswith(name + "::"):
                actv.append((g['name'], g['id']))
        return actv

    def parents(self, did):
        "All parents of did."
        # get parent and grandparent names
        parents = []
        for part in self.get(did)['name'].split("::")[:-1]:
            if not parents:
                parents.append(part)
            else:
                parents.append(parents[-1] + "::" + part)
        # convert to objects
        for c, p in enumerate(parents):
            parents[c] = self.get(self.id(p))
        return parents

    # Sync handling
    ##########################################################################

    def beforeUpload(self):
        for d in self.all():
            d['usn'] = 0
        for c in self.allConf():
            c['usn'] = 0
        self.save()

    # Dynamic decks
    ##########################################################################

    def newDyn(self, name):
        "Return a new dynamic deck and set it as the current deck."
        did = self.id(name, type=defaultDynamicDeck)
        self.select(did)
        return did

    def isDyn(self, did):
        return self.get(did)['dyn']

########NEW FILE########
__FILENAME__ = errors
# -*- coding: utf-8 -*-
# Copyright: Damien Elmes <anki@ichi2.net>
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

class AnkiError(Exception):
    def __init__(self, type, **data):
        self.type = type
        self.data = data
    def __str__(self):
        m = self.type
        if self.data:
            m += ": %s" % repr(self.data)
        return m

class DeckRenameError(Exception):
    def __init__(self, description):
        self.description = description
    def __str__(self):
        return "Couldn't rename deck: " + self.description

########NEW FILE########
__FILENAME__ = exporting
# -*- coding: utf-8 -*-
# Copyright: Damien Elmes <anki@ichi2.net>
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

import itertools, time, re, os, HTMLParser, zipfile, shutil
from operator import itemgetter
from anki.cards import Card
from anki.lang import _
from anki.utils import stripHTML, ids2str, splitFields, json
from anki.hooks import runHook
from anki import Collection

class Exporter(object):
    def __init__(self, col, did=None):
        self.col = col
        self.did = did

    def exportInto(self, path):
        self._escapeCount = 0
        file = open(path, "wb")
        self.doExport(file)
        file.close()

    def escapeText(self, text):
        "Escape newlines and tabs, and strip Anki HTML."
        text = text.replace("\n", "<br>")
        text = text.replace("\t", " " * 8)
        return text

    def cardIds(self):
        if not self.did:
            cids = self.col.db.list("select id from cards")
        else:
            cids = self.col.decks.cids(self.did, children=True)
        self.count = len(cids)
        return cids

# Cards as TSV
######################################################################

class TextCardExporter(Exporter):
    pass

#     key = _("Text files (*.txt)")
#     ext = ".txt"

#     def __init__(self, col):
#         Exporter.__init__(self, col)

#     def doExport(self, file):
#         ids = self.cardIds()
#         strids = ids2str(ids)
#         cards = self.col.db.all("""
# select cards.question, cards.answer, cards.id from cards
# where cards.id in %s
# order by cards.created""" % strids)
#         self.cardTags = dict(self.col.db.all("""
# select cards.id, notes.tags from cards, notes
# where cards.noteId = notes.id
# and cards.id in %s
# order by cards.created""" % strids))
#         out = u"\n".join(["%s\t%s%s" % (
#             self.escapeText(c[0], removeFields=True),
#             self.escapeText(c[1], removeFields=True),
#             self.tags(c[2]))
#                           for c in cards])
#         if out:
#             out += "\n"
#         file.write(out.encode("utf-8"))

#     def tags(self, id):
#         return "\t" + ", ".join(parseTags(self.cardTags[id]))

# Notes as TSV
######################################################################

class TextNoteExporter(Exporter):

    key = _("Notes in Plain Text")
    ext = ".txt"

    def __init__(self, col):
        Exporter.__init__(self, col)
        self.includeID = False
        self.includeTags = True

    def doExport(self, file):
        cardIds = self.cardIds()
        data = []
        for id, flds, tags in self.col.db.execute("""
select guid, flds, tags from notes
where id in
(select nid from cards
where cards.id in %s)""" % ids2str(cardIds)):
            row = []
            # note id
            if self.includeID:
                row.append(str(id))
            # fields
            row.extend([self.escapeText(f) for f in splitFields(flds)])
            # tags
            if self.includeTags:
                row.append(tags.strip())
            data.append("\t".join(row))
        self.count = len(data)
        out = "\n".join(data)
        file.write(out.encode("utf-8"))

# Anki decks
######################################################################
# media files are stored in self.mediaFiles, but not exported.

class AnkiExporter(Exporter):

    key = _("Anki 2.0 Deck")
    ext = ".anki2"

    def __init__(self, col):
        Exporter.__init__(self, col)
        self.includeSched = False
        self.includeMedia = True

    def exportInto(self, path):
        # create a new collection at the target
        try:
            os.unlink(path)
        except (IOError, OSError):
            pass
        self.dst = Collection(path)
        self.src = self.col
        # find cards
        if not self.did:
            cids = self.src.db.list("select id from cards")
        else:
            cids = self.src.decks.cids(self.did, children=True)
        # copy cards, noting used nids
        nids = {}
        data = []
        for row in self.src.db.execute(
            "select * from cards where id in "+ids2str(cids)):
            nids[row[1]] = True
            data.append(row)
        self.dst.db.executemany(
            "insert into cards values (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            data)
        # notes
        strnids = ids2str(nids.keys())
        notedata = self.src.db.all("select * from notes where id in "+
                               strnids)
        self.dst.db.executemany(
            "insert into notes values (?,?,?,?,?,?,?,?,?,?,?)",
            notedata)
        # models used by the notes
        mids = self.dst.db.list("select distinct mid from notes where id in "+
                                strnids)
        # card history and revlog
        if self.includeSched:
            data = self.src.db.all(
                "select * from revlog where cid in "+ids2str(cids))
            self.dst.db.executemany(
                "insert into revlog values (?,?,?,?,?,?,?,?,?)",
                data)
        else:
            # need to reset card state
            self.dst.sched.resetCards(cids)
        # models
        for m in self.src.models.all():
            if int(m['id']) in mids:
                self.dst.models.update(m)
        # decks
        if not self.did:
            dids = []
        else:
            dids = [self.did] + [
                x[1] for x in self.src.decks.children(self.did)]
        dconfs = {}
        for d in self.src.decks.all():
            if str(d['id']) == "1":
                continue
            if dids and d['id'] not in dids:
                continue
            if not d['dyn'] and d['conf'] != 1:
                if self.includeSched:
                    dconfs[d['conf']] = True
            if not self.includeSched:
                # scheduling not included, so reset deck settings to default
                d = dict(d)
                d['conf'] = 1
            self.dst.decks.update(d)
        # copy used deck confs
        for dc in self.src.decks.allConf():
            if dc['id'] in dconfs:
                self.dst.decks.updateConf(dc)
        # find used media
        media = {}
        self.mediaDir = self.src.media.dir()
        if self.includeMedia:
            for row in notedata:
                flds = row[6]
                mid = row[2]
                for file in self.src.media.filesInStr(mid, flds):
                    media[file] = True
            if self.mediaDir:
                for fname in os.listdir(self.mediaDir):
                    if fname.startswith("_"):
                        media[fname] = True
        self.mediaFiles = media.keys()
        self.dst.crt = self.src.crt
        # todo: tags?
        self.count = self.dst.cardCount()
        self.dst.setMod()
        self.postExport()
        self.dst.close()

    def postExport(self):
        # overwrite to apply customizations to the deck before it's closed,
        # such as update the deck description
        pass

# Packaged Anki decks
######################################################################

class AnkiPackageExporter(AnkiExporter):

    key = _("Anki Deck Package")
    ext = ".apkg"

    def __init__(self, col):
        AnkiExporter.__init__(self, col)

    def exportInto(self, path):
        # open a zip file
        z = zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED)
        # if all decks and scheduling included, full export
        if self.includeSched and not self.did:
            media = self.exportVerbatim(z)
        else:
            # otherwise, filter
            media = self.exportFiltered(z, path)
        # media map
        z.writestr("media", json.dumps(media))
        z.close()

    def exportFiltered(self, z, path):
        # export into the anki2 file
        colfile = path.replace(".apkg", ".anki2")
        AnkiExporter.exportInto(self, colfile)
        z.write(colfile, "collection.anki2")
        # and media
        self.prepareMedia()
        media = {}
        for c, file in enumerate(self.mediaFiles):
            c = str(c)
            mpath = os.path.join(self.mediaDir, file)
            if os.path.exists(mpath):
                z.write(mpath, c)
                media[c] = file
        # tidy up intermediate files
        os.unlink(colfile)
        os.unlink(path.replace(".apkg", ".media.db"))
        shutil.rmtree(path.replace(".apkg", ".media"))
        return media

    def exportVerbatim(self, z):
        # close our deck & write it into the zip file, and reopen
        self.count = self.col.cardCount()
        self.col.close()
        z.write(self.col.path, "collection.anki2")
        self.col.reopen()
        # copy all media
        if not self.includeMedia:
            return {}
        media = {}
        mdir = self.col.media.dir()
        for c, file in enumerate(os.listdir(mdir)):
            c = str(c)
            mpath = os.path.join(mdir, file)
            if os.path.exists(mpath):
                z.write(mpath, c)
                media[c] = file
        return media

    def prepareMedia(self):
        # chance to move each file in self.mediaFiles into place before media
        # is zipped up
        pass

# Export modules
##########################################################################

def exporters():
    def id(obj):
        return ("%s (*%s)" % (obj.key, obj.ext), obj)
    exps = [
        id(AnkiPackageExporter),
        id(TextNoteExporter),
    ]
    runHook("exportersList", exps)
    return exps

########NEW FILE########
__FILENAME__ = find
# -*- coding: utf-8 -*-
# Copyright: Damien Elmes <anki@ichi2.net>
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

import re
from anki.utils import ids2str, splitFields, joinFields, stripHTML, intTime
from anki.consts import *
import sre_constants

# Find
##########################################################################

class Finder(object):

    def __init__(self, col):
        self.col = col

    def findCards(self, query, order=False):
        "Return a list of card ids for QUERY."
        tokens = self._tokenize(query)
        preds, args = self._where(tokens)
        if preds is None:
            return []
        order, rev = self._order(order)
        sql = self._query(preds, order)
        try:
            res = self.col.db.list(sql, *args)
        except:
            # invalid grouping
            return []
        if rev:
            res.reverse()
        return res

    def findNotes(self, query):
        tokens = self._tokenize(query)
        preds, args = self._where(tokens)
        if preds is None:
            return []
        if preds:
            preds = "(" + preds + ")"
        else:
            preds = "1"
        sql = """
select distinct(n.id) from cards c, notes n where c.nid=n.id and """+preds
        try:
            res = self.col.db.list(sql, *args)
        except:
            # invalid grouping
            return []
        return res

    # Tokenizing
    ######################################################################

    def _tokenize(self, query):
        inQuote = False
        tokens = []
        token = ""
        for c in query:
            # quoted text
            if c in ("'", '"'):
                if inQuote:
                    if c == inQuote:
                        inQuote = False
                    else:
                        token += c
                elif token:
                    # quotes are allowed to start directly after a :
                    if token[-1] == ":":
                        inQuote = c
                    else:
                        token += c
                else:
                    inQuote = c
            # separator
            elif c == " ":
                if inQuote:
                    token += c
                elif token:
                    # space marks token finished
                    tokens.append(token)
                    token = ""
            # nesting
            elif c in ("(", ")"):
                if inQuote:
                    token += c
                else:
                    if c == ")" and token:
                        tokens.append(token)
                        token = ""
                    tokens.append(c)
            # negation
            elif c == "-":
                if token:
                    token += c
                elif not tokens or tokens[-1] != "-":
                    tokens.append("-")
            # normal character
            else:
                token += c
        # if we finished in a token, add it
        if token:
            tokens.append(token)
        return tokens

    # Query building
    ######################################################################

    def _where(self, tokens):
        # state and query
        s = dict(isnot=False, isor=False, join=False, q="", bad=False)
        args = []
        def add(txt, wrap=True):
            # failed command?
            if not txt:
                # if it was to be negated then we can just ignore it
                if s['isnot']:
                    s['isnot'] = False
                    return
                else:
                    s['bad'] = True
                    return
            elif txt == "skip":
                return
            # do we need a conjunction?
            if s['join']:
                if s['isor']:
                    s['q'] += " or "
                    s['isor'] = False
                else:
                    s['q'] += " and "
            if s['isnot']:
                s['q'] += " not "
                s['isnot'] = False
            if wrap:
                txt = "(" + txt + ")"
            s['q'] += txt
            s['join'] = True
        for token in tokens:
            if s['bad']:
                return None, None
            # special tokens
            if token == "-":
                s['isnot'] = True
            elif token.lower() == "or":
                s['isor'] = True
            elif token == "(":
                add(token, wrap=False)
                s['join'] = False
            elif token == ")":
                s['q'] += ")"
            # commands
            elif ":" in token:
                cmd, val = token.split(":", 1)
                cmd = cmd.lower()
                if cmd == "tag":
                    add(self._findTag(val, args))
                elif cmd == "is":
                    add(self._findCardState(val))
                elif cmd == "nid":
                    add(self._findNids(val))
                elif cmd == "card":
                    add(self._findTemplate(val))
                elif cmd == "note":
                    add(self._findModel(val))
                elif cmd == "deck":
                    add(self._findDeck(val))
                elif cmd == "prop":
                    add(self._findProp(val))
                elif cmd == "rated":
                    add(self._findRated(val))
                elif cmd == "added":
                    add(self._findAdded(val))
                else:
                    add(self._findField(cmd, val))
            # normal text search
            else:
                add(self._findText(token, args))
        if s['bad']:
            return None, None
        return s['q'], args

    def _query(self, preds, order):
        # can we skip the note table?
        if "n." not in preds and "n." not in order:
            sql = "select c.id from cards c where "
        else:
            sql = "select c.id from cards c, notes n where c.nid=n.id and "
        # combine with preds
        if preds:
            sql += "(" + preds + ")"
        else:
            sql += "1"
        # order
        if order:
            sql += " " + order
        return sql

    # Ordering
    ######################################################################

    def _order(self, order):
        if not order:
            return "", False
        elif order is not True:
            # custom order string provided
            return " order by " + order, False
        # use deck default
        type = self.col.conf['sortType']
        sort = None
        if type.startswith("note"):
            if type == "noteCrt":
                sort = "n.id, c.ord"
            elif type == "noteMod":
                sort = "n.mod, c.ord"
            elif type == "noteFld":
                sort = "n.sfld collate nocase, c.ord"
        elif type.startswith("card"):
            if type == "cardMod":
                sort = "c.mod"
            elif type == "cardReps":
                sort = "c.reps"
            elif type == "cardDue":
                sort = "c.type, c.due"
            elif type == "cardEase":
                sort = "c.factor"
            elif type == "cardLapses":
                sort = "c.lapses"
            elif type == "cardIvl":
                sort = "c.ivl"
        if not sort:
            # deck has invalid sort order; revert to noteCrt
            sort = "n.id, c.ord"
        return " order by " + sort, self.col.conf['sortBackwards']

    # Commands
    ######################################################################

    def _findTag(self, val, args):
        if val == "none":
            return 'n.tags = ""'
        val = val.replace("*", "%")
        if not val.startswith("%"):
            val = "% " + val
        if not val.endswith("%"):
            val += " %"
        args.append(val)
        return "n.tags like ?"

    def _findCardState(self, val):
        if val in ("review", "new", "learn"):
            if val == "review":
                n = 2
            elif val == "new":
                n = 0
            else:
                return "queue in (1, 3)"
            return "type = %d" % n
        elif val == "suspended":
            return "c.queue = -1"
        elif val == "due":
            return """
(c.queue in (2,3) and c.due <= %d) or
(c.queue = 1 and c.due <= %d)""" % (
    self.col.sched.today, self.col.sched.dayCutoff)

    def _findRated(self, val):
        # days(:optional_ease)
        r = val.split(":")
        try:
            days = int(r[0])
        except ValueError:
            return
        days = min(days, 31)
        # ease
        ease = ""
        if len(r) > 1:
            if r[1] not in ("1", "2", "3", "4"):
                return
            ease = "and ease=%s" % r[1]
        cutoff = (self.col.sched.dayCutoff - 86400*days)*1000
        return ("c.id in (select cid from revlog where id>%d %s)" %
                (cutoff, ease))

    def _findAdded(self, val):
        try:
            days = int(val)
        except ValueError:
            return
        cutoff = (self.col.sched.dayCutoff - 86400*days)*1000
        return "c.id > %d" % cutoff

    def _findProp(self, val):
        # extract
        m = re.match("(^.+?)(<=|>=|!=|=|<|>)(.+?$)", val)
        if not m:
            return
        prop, cmp, val = m.groups()
        prop = prop.lower()
        # is val valid?
        try:
            if prop == "ease":
                val = float(val)
            else:
                val = int(val)
        except ValueError:
            return
        # is prop valid?
        if prop not in ("due", "ivl", "reps", "lapses", "ease"):
            return
        # query
        q = []
        if prop == "due":
            val += self.col.sched.today
            # only valid for review/daily learning
            q.append("(c.queue in (2,3))")
        elif prop == "ease":
            prop = "factor"
            val = int(val*1000)
        q.append("(%s %s %s)" % (prop, cmp, val))
        return " and ".join(q)

    def _findText(self, val, args):
        val = val.replace("*", "%")
        args.append("%"+val+"%")
        args.append("%"+val+"%")
        return "(n.sfld like ? escape '\\' or n.flds like ? escape '\\')"

    def _findNids(self, val):
        if re.search("[^0-9,]", val):
            return
        return "n.id in (%s)" % val

    def _findModel(self, val):
        ids = []
        val = val.lower()
        for m in self.col.models.all():
            if m['name'].lower() == val:
                ids.append(m['id'])
        return "n.mid in %s" % ids2str(ids)

    def _findDeck(self, val):
        # if searching for all decks, skip
        if val == "*":
            return "skip"
        # deck types
        elif val == "filtered":
            return "c.odid"
        def dids(did):
            if not did:
                return None
            return [did] + [a[1] for a in self.col.decks.children(did)]
        # current deck?
        ids = None
        if val.lower() == "current":
            ids = dids(self.col.decks.current()['id'])
        elif "*" not in val:
            # single deck
            ids = dids(self.col.decks.id(val, create=False))
        else:
            # wildcard
            ids = set()
            val = val.replace("*", ".*")
            for d in self.col.decks.all():
                if re.match("(?i)"+val, d['name']):
                    ids.update(dids(d['id']))
        if not ids:
            return
        sids = ids2str(ids)
        return "c.did in %s or c.odid in %s" % (sids, sids)

    def _findTemplate(self, val):
        # were we given an ordinal number?
        try:
            num = int(val) - 1
        except:
            num = None
        if num is not None:
            return "c.ord = %d" % num
        # search for template names
        lims = []
        for m in self.col.models.all():
            for t in m['tmpls']:
                if t['name'].lower() == val.lower():
                    if m['type'] == MODEL_CLOZE:
                        # if the user has asked for a cloze card, we want
                        # to give all ordinals, so we just limit to the
                        # model instead
                        lims.append("(n.mid = %s)" % m['id'])
                    else:
                        lims.append("(n.mid = %s and c.ord = %s)" % (
                            m['id'], t['ord']))
        return " or ".join(lims)

    def _findField(self, field, val):
        field = field.lower()
        val = val.replace("*", "%")
        # find models that have that field
        mods = {}
        for m in self.col.models.all():
            for f in m['flds']:
                if f['name'].lower() == field:
                    mods[str(m['id'])] = (m, f['ord'])
        if not mods:
            # nothing has that field
            return
        # gather nids
        regex = re.escape(val).replace("\\_", ".").replace("\\%", ".*")
        nids = []
        for (id,mid,flds) in self.col.db.execute("""
select id, mid, flds from notes
where mid in %s and flds like ? escape '\\'""" % (
                         ids2str(mods.keys())),
                         "%"+val+"%"):
            flds = splitFields(flds)
            ord = mods[str(mid)][1]
            strg = flds[ord]
            try:
                if re.search("(?i)^"+regex+"$", strg):
                    nids.append(id)
            except sre_constants.error:
                return
        if not nids:
            return
        return "n.id in %s" % ids2str(nids)

# Find and replace
##########################################################################

def findReplace(col, nids, src, dst, regex=False, field=None, fold=True):
    "Find and replace fields in a note."
    mmap = {}
    if field:
        for m in col.models.all():
            for f in m['flds']:
                if f['name'] == field:
                    mmap[str(m['id'])] = f['ord']
        if not mmap:
            return 0
    # find and gather replacements
    if not regex:
        src = re.escape(src)
    if fold:
        src = "(?i)"+src
    regex = re.compile(src)
    def repl(str):
        return re.sub(regex, dst, str)
    d = []
    snids = ids2str(nids)
    nids = []
    for nid, mid, flds in col.db.execute(
        "select id, mid, flds from notes where id in "+snids):
        origFlds = flds
        # does it match?
        sflds = splitFields(flds)
        if field:
            try:
                ord = mmap[str(mid)]
                sflds[ord] = repl(sflds[ord])
            except KeyError:
                # note doesn't have that field
                continue
        else:
            for c in range(len(sflds)):
                sflds[c] = repl(sflds[c])
        flds = joinFields(sflds)
        if flds != origFlds:
            nids.append(nid)
            d.append(dict(nid=nid,flds=flds,u=col.usn(),m=intTime()))
    if not d:
        return 0
    # replace
    col.db.executemany(
        "update notes set flds=:flds,mod=:m,usn=:u where id=:nid", d)
    col.updateFieldCache(nids)
    col.genCards(nids)
    return len(d)

def fieldNames(col, downcase=True):
    fields = set()
    names = []
    for m in col.models.all():
        for f in m['flds']:
            if f['name'].lower() not in fields:
                names.append(f['name'])
                fields.add(f['name'].lower())
    if downcase:
        return list(fields)
    return names

# Find duplicates
##########################################################################

def findDupes(col, fieldName, search=""):
    # limit search to notes with applicable field name
    if search:
        search = "("+search+") "
    search += "'%s:*'" % fieldName
    # go through notes
    vals = {}
    dupes = []
    fields = {}
    def ordForMid(mid):
        if mid not in fields:
            model = col.models.get(mid)
            fields[mid] = col.models.fieldMap(model)[fieldName][0]
        return fields[mid]
    for nid, mid, flds in col.db.all(
        "select id, mid, flds from notes where id in "+ids2str(
            col.findNotes(search))):
        flds = splitFields(flds)
        val = flds[ordForMid(mid)]
        # empty does not count as duplicate
        if not val:
            continue
        if val not in vals:
            vals[val] = []
        vals[val].append(nid)
        if len(vals[val]) == 2:
            dupes.append((val, vals[val]))
    return dupes

########NEW FILE########
__FILENAME__ = hooks
# -*- coding: utf-8 -*-
# Copyright: Damien Elmes <anki@ichi2.net>
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

"""\
Hooks - hook management and tools for extending Anki
==============================================================================

To find available hooks, grep for runHook and runFilter in the source code.

Instrumenting allows you to modify functions that don't have hooks available.
If you call wrap() with pos='around', the original function will not be called
automatically but can be called with _old().
"""

# Hooks
##############################################################################

_hooks = {}

def runHook(hook, *args):
    "Run all functions on hook."
    hook = _hooks.get(hook, None)
    if hook:
        for func in hook:
            func(*args)

def runFilter(hook, arg, *args):
    hook = _hooks.get(hook, None)
    if hook:
        for func in hook:
            arg = func(arg, *args)
    return arg

def addHook(hook, func):
    "Add a function to hook. Ignore if already on hook."
    if not _hooks.get(hook, None):
        _hooks[hook] = []
    if func not in _hooks[hook]:
        _hooks[hook].append(func)

def remHook(hook, func):
    "Remove a function if is on hook."
    hook = _hooks.get(hook, [])
    if func in hook:
        hook.remove(func)

# Instrumenting
##############################################################################

def wrap(old, new, pos="after"):
    "Override an existing function."
    def repl(*args, **kwargs):
        if pos == "after":
            old(*args, **kwargs)
            return new(*args, **kwargs)
        elif pos == "before":
            new(*args, **kwargs)
            return old(*args, **kwargs)
        else:
            return new(_old=old, *args, **kwargs)
    return repl

########NEW FILE########
__FILENAME__ = anki1
# -*- coding: utf-8 -*-
# Copyright: Damien Elmes <anki@ichi2.net>
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

import traceback, os, re
from anki.lang import _
from anki.upgrade import Upgrader
from anki.importing.anki2 import Anki2Importer

class Anki1Importer(Anki2Importer):

    def run(self):
        u = Upgrader()
        # check
        if not u.check(self.file):
            self.log.append(_(
                "File is old or damaged; please run Tools>Advanced>Check DB "
                "in Anki 1.2 first."))
            raise Exception("invalidFile")
        # upgrade
        try:
            deck = u.upgrade(self.file)
        except:
            traceback.print_exc()
            self.log.append(traceback.format_exc())
            return
        # save the conf for later
        conf = deck.decks.confForDid(1)
        # merge
        deck.close()
        mdir = re.sub(r"\.anki2?$", ".media",  self.file)
        self.deckPrefix = re.sub(r"\.anki$", "", os.path.basename(self.file))
        self.file = deck.path
        Anki2Importer.run(self, mdir)
        # set imported deck to saved conf
        id = self.col.decks.confId(self.deckPrefix)
        conf['id'] = id
        conf['name'] = self.deckPrefix
        conf['usn'] = self.col.usn()
        self.col.decks.updateConf(conf)
        did = self.col.decks.id(self.deckPrefix)
        d = self.col.decks.get(did)
        self.col.decks.setConf(d, id)

########NEW FILE########
__FILENAME__ = anki2
# -*- coding: utf-8 -*-
# Copyright: Damien Elmes <anki@ichi2.net>
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

import os
from anki import Collection
from anki.utils import intTime, splitFields, joinFields, checksum, guid64, \
    incGuid
from anki.importing.base import Importer
from anki.lang import _
from anki.lang import ngettext

MID = 2
GUID = 1

class Anki2Importer(Importer):

    needMapper = False
    deckPrefix = None
    allowUpdate = True

    def run(self, media=None):
        self._prepareFiles()
        if media is not None:
            # Anki1 importer has provided us with a custom media folder
            self.src.media._dir = media
        try:
            self._import()
        finally:
            self.src.close(save=False)

    def _prepareFiles(self):
        self.dst = self.col
        self.src = Collection(self.file)

    def _import(self):
        self._decks = {}
        if self.deckPrefix:
            id = self.dst.decks.id(self.deckPrefix)
            self.dst.decks.select(id)
        self._prepareTS()
        self._prepareModels()
        self._importNotes()
        self._importCards()
        self._importStaticMedia()
        self._postImport()
        self.dst.db.execute("vacuum")
        self.dst.db.execute("analyze")

    # Notes
    ######################################################################

    def _importNotes(self):
        # build guid -> (id,mod,mid) hash & map of existing note ids
        self._notes = {}
        existing = {}
        for id, guid, mod, mid in self.dst.db.execute(
            "select id, guid, mod, mid from notes"):
            self._notes[guid] = (id, mod, mid)
            existing[id] = True
        # we may need to rewrite the guid if the model schemas don't match,
        # so we need to keep track of the changes for the card import stage
        self._changedGuids = {}
        # iterate over source collection
        add = []
        dirty = []
        usn = self.dst.usn()
        dupes = 0
        for note in self.src.db.execute(
            "select * from notes"):
            # turn the db result into a mutable list
            note = list(note)
            shouldAdd = self._uniquifyNote(note)
            if shouldAdd:
                # ensure id is unique
                while note[0] in existing:
                    note[0] += 999
                existing[note[0]] = True
                # bump usn
                note[4] = usn
                # update media references in case of dupes
                note[6] = self._mungeMedia(note[MID], note[6])
                add.append(note)
                dirty.append(note[0])
                # note we have the added the guid
                self._notes[note[GUID]] = (note[0], note[3], note[MID])
            else:
                dupes += 1
                ## update existing note - not yet tested; for post 2.0
                # newer = note[3] > mod
                # if self.allowUpdate and self._mid(mid) == mid and newer:
                #     localNid = self._notes[guid][0]
                #     note[0] = localNid
                #     note[4] = usn
                #     add.append(note)
                #     dirty.append(note[0])
        if dupes:
            self.log.append(_("Already in collection: %s.") % (ngettext(
                "%d note", "%d notes", dupes) % dupes))
        # add to col
        self.dst.db.executemany(
            "insert or replace into notes values (?,?,?,?,?,?,?,?,?,?,?)",
            add)
        self.dst.updateFieldCache(dirty)
        self.dst.tags.registerNotes(dirty)

    # determine if note is a duplicate, and adjust mid and/or guid as required
    # returns true if note should be added
    def _uniquifyNote(self, note):
        origGuid = note[GUID]
        srcMid = note[MID]
        dstMid = self._mid(srcMid)
        # duplicate schemas?
        if srcMid == dstMid:
            return origGuid not in self._notes
        # differing schemas
        note[MID] = dstMid
        if origGuid not in self._notes:
            return True
        # as the schemas differ and we already have a note with a different
        # note type, this note needs a new guid
        while True:
            note[GUID] = incGuid(note[GUID])
            self._changedGuids[origGuid] = note[GUID]
            # if we don't have an existing guid, we can add
            if note[GUID] not in self._notes:
                return True
            # if the existing guid shares the same mid, we can reuse
            if dstMid == self._notes[note[GUID]][MID]:
                return False

    # Models
    ######################################################################
    # Models in the two decks may share an ID but not a schema, so we need to
    # compare the field & template signature rather than just rely on ID. If
    # the schemas don't match, we increment the mid and try again, creating a
    # new model if necessary.

    def _prepareModels(self):
        "Prepare index of schema hashes."
        self._modelMap = {}

    def _mid(self, srcMid):
        "Return local id for remote MID."
        # already processed this mid?
        if srcMid in self._modelMap:
            return self._modelMap[srcMid]
        mid = srcMid
        srcModel = self.src.models.get(srcMid)
        srcScm = self.src.models.scmhash(srcModel)
        while True:
            # missing from target col?
            if not self.dst.models.have(mid):
                # copy it over
                model = srcModel.copy()
                model['id'] = mid
                model['mod'] = intTime()
                model['usn'] = self.col.usn()
                self.dst.models.update(model)
                break
            # there's an existing model; do the schemas match?
            dstModel = self.dst.models.get(mid)
            dstScm = self.dst.models.scmhash(dstModel)
            if srcScm == dstScm:
                # they do; we can reuse this mid
                break
            # as they don't match, try next id
            mid += 1
        # save map and return new mid
        self._modelMap[srcMid] = mid
        return mid

    # Decks
    ######################################################################

    def _did(self, did):
        "Given did in src col, return local id."
        # already converted?
        if did in self._decks:
            return self._decks[did]
        # get the name in src
        g = self.src.decks.get(did)
        name = g['name']
        # if there's a prefix, replace the top level deck
        if self.deckPrefix:
            tmpname = "::".join(name.split("::")[1:])
            name = self.deckPrefix
            if tmpname:
                name += "::" + tmpname
        # create in local
        newid = self.dst.decks.id(name)
        # pull conf over
        if 'conf' in g and g['conf'] != 1:
            self.dst.decks.updateConf(self.src.decks.getConf(g['conf']))
            g2 = self.dst.decks.get(newid)
            g2['conf'] = g['conf']
            self.dst.decks.save(g2)
        # save desc
        deck = self.dst.decks.get(newid)
        deck['desc'] = g['desc']
        self.dst.decks.save(deck)
        # add to deck map and return
        self._decks[did] = newid
        return newid

    # Cards
    ######################################################################

    def _importCards(self):
        # build map of (guid, ord) -> cid and used id cache
        self._cards = {}
        existing = {}
        for guid, ord, cid in self.dst.db.execute(
            "select f.guid, c.ord, c.id from cards c, notes f "
            "where c.nid = f.id"):
            existing[cid] = True
            self._cards[(guid, ord)] = cid
        # loop through src
        cards = []
        revlog = []
        cnt = 0
        usn = self.dst.usn()
        aheadBy = self.src.sched.today - self.dst.sched.today
        for card in self.src.db.execute(
            "select f.guid, f.mid, c.* from cards c, notes f "
            "where c.nid = f.id"):
            guid = card[0]
            if guid in self._changedGuids:
                guid = self._changedGuids[guid]
            # does the card's note exist in dst col?
            if guid not in self._notes:
                continue
            dnid = self._notes[guid]
            # does the card already exist in the dst col?
            ord = card[5]
            if (guid, ord) in self._cards:
                # fixme: in future, could update if newer mod time
                continue
            # doesn't exist. strip off note info, and save src id for later
            card = list(card[2:])
            scid = card[0]
            # ensure the card id is unique
            while card[0] in existing:
                card[0] += 999
            existing[card[0]] = True
            # update cid, nid, etc
            card[1] = self._notes[guid][0]
            card[2] = self._did(card[2])
            card[4] = intTime()
            card[5] = usn
            # review cards have a due date relative to collection
            if card[7] in (2, 3):
                card[8] -= aheadBy
            # if odid true, convert card from filtered to normal
            if card[15]:
                # odid
                card[15] = 0
                # odue
                card[8] = card[14]
                card[14] = 0
                # queue
                if card[6] == 1: # type
                    card[7] = 0
                else:
                    card[7] = card[6]
                # type
                if card[6] == 1:
                    card[6] = 0
            cards.append(card)
            # we need to import revlog, rewriting card ids and bumping usn
            for rev in self.src.db.execute(
                "select * from revlog where cid = ?", scid):
                rev = list(rev)
                rev[1] = card[0]
                rev[2] = self.dst.usn()
                revlog.append(rev)
            cnt += 1
        # apply
        self.dst.db.executemany("""
insert or ignore into cards values (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""", cards)
        self.dst.db.executemany("""
insert or ignore into revlog values (?,?,?,?,?,?,?,?,?)""", revlog)
        self.log.append(ngettext("%d card imported.", "%d cards imported.", cnt) % cnt)

    # Media
    ######################################################################

    # note: this func only applies to imports of .anki2. for .apkg files, the
    # apkg importer does the copying
    def _importStaticMedia(self):
        # Import any '_foo' prefixed media files regardless of whether
        # they're used on notes or not
        dir = self.src.media.dir()
        if not os.path.exists(dir):
            return
        for fname in os.listdir(dir):
            if fname.startswith("_") and not self.dst.media.have(fname):
                self._writeDstMedia(fname, self._srcMediaData(fname))

    def _mediaData(self, fname, dir=None):
        if not dir:
            dir = self.src.media.dir()
        path = os.path.join(dir, fname)
        try:
            return open(path, "rb").read()
        except (IOError, OSError):
            return

    def _srcMediaData(self, fname):
        "Data for FNAME in src collection."
        return self._mediaData(fname, self.src.media.dir())

    def _dstMediaData(self, fname):
        "Data for FNAME in dst collection."
        return self._mediaData(fname, self.dst.media.dir())

    def _writeDstMedia(self, fname, data):
        path = os.path.join(self.dst.media.dir(), fname)
        open(path, "wb").write(data)

    def _mungeMedia(self, mid, fields):
        fields = splitFields(fields)
        def repl(match):
            fname = match.group(2)
            srcData = self._srcMediaData(fname)
            dstData = self._dstMediaData(fname)
            if not srcData:
                # file was not in source, ignore
                return match.group(0)
            # if model-local file exists from a previous import, use that
            name, ext = os.path.splitext(fname)
            lname = "%s_%s%s" % (name, mid, ext)
            if self.dst.media.have(lname):
                return match.group(0).replace(fname, lname)
            # if missing or the same, pass unmodified
            elif not dstData or srcData == dstData:
                # need to copy?
                if not dstData:
                    self._writeDstMedia(fname, srcData)
                return match.group(0)
            # exists but does not match, so we need to dedupe
            self._writeDstMedia(lname, srcData)
            return match.group(0).replace(fname, lname)
        for i in range(len(fields)):
            fields[i] = self.dst.media.transformNames(fields[i], repl)
        return joinFields(fields)

    # Post-import cleanup
    ######################################################################
    # fixme: we could be handling new card order more elegantly on import

    def _postImport(self):
        # make sure new position is correct
        self.dst.conf['nextPos'] = self.dst.db.scalar(
            "select max(due)+1 from cards where type = 0") or 0
        self.dst.save()

########NEW FILE########
__FILENAME__ = apkg
# -*- coding: utf-8 -*-
# Copyright: Damien Elmes <anki@ichi2.net>
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

import zipfile, os
from anki.utils import tmpfile, json
from anki.importing.anki2 import Anki2Importer

class AnkiPackageImporter(Anki2Importer):

    def run(self):
        # extract the deck from the zip file
        self.zip = z = zipfile.ZipFile(self.file)
        col = z.read("collection.anki2")
        colpath = tmpfile(suffix=".anki2")
        open(colpath, "wb").write(col)
        self.file = colpath
        # we need the media dict in advance, and we'll need a map of fname ->
        # number to use during the import
        self.nameToNum = {}
        for k, v in json.loads(z.read("media")).items():
            self.nameToNum[v] = k
        # run anki2 importer
        Anki2Importer.run(self)
        # import static media
        for file, c in self.nameToNum.items():
            if not file.startswith("_") and not file.startswith("latex-"):
                continue
            path = os.path.join(self.col.media.dir(), file)
            if not os.path.exists(path):
                open(path, "wb").write(z.read(c))

    def _srcMediaData(self, fname):
        if fname in self.nameToNum:
            return self.zip.read(self.nameToNum[fname])
        return None

########NEW FILE########
__FILENAME__ = base
# -*- coding: utf-8 -*-
# Copyright: Damien Elmes <anki@ichi2.net>
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

from anki.utils import intTime, maxID

# Base importer
##########################################################################

class Importer(object):

    needMapper = False
    needDelimiter = False

    def __init__(self, col, file):
        self.file = file
        self.log = []
        self.col = col
        self.total = 0

    def run(self):
        pass

    # Timestamps
    ######################################################################
    # It's too inefficient to check for existing ids on every object,
    # and a previous import may have created timestamps in the future, so we
    # need to make sure our starting point is safe.

    def _prepareTS(self):
        self._ts = maxID(self.dst.db)

    def ts(self):
        self._ts += 1
        return self._ts

########NEW FILE########
__FILENAME__ = csvfile
# -*- coding: utf-8 -*-
# Copyright: Damien Elmes <anki@ichi2.net>
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

import codecs, csv, re
from anki.importing.noteimp import NoteImporter, ForeignNote
from anki.lang import _
from anki.errors import *

class TextImporter(NoteImporter):

    needDelimiter = True
    patterns = ("\t", ";")

    def __init__(self, *args):
        NoteImporter.__init__(self, *args)
        self.lines = None
        self.fileobj = None
        self.delimiter = None
        self.tagsToAdd = []

    def foreignNotes(self):
        self.open()
        # process all lines
        log = []
        notes = []
        lineNum = 0
        ignored = 0
        if self.delimiter:
            reader = csv.reader(self.data, delimiter=self.delimiter, doublequote=True)
        else:
            reader = csv.reader(self.data, self.dialect, doublequote=True)
        for row in reader:
            row = [unicode(x, "utf-8") for x in row]
            if len(row) != self.numFields:
                log.append(_(
                    "'%(row)s' had %(num1)d fields, "
                    "expected %(num2)d") % {
                    "row": u" ".join(row),
                    "num1": len(row),
                    "num2": self.numFields,
                    })
                ignored += 1
                continue
            note = self.noteFromFields(row)
            notes.append(note)
        self.log = log
        self.ignored = ignored
        self.fileobj.close()
        return notes

    def open(self):
        "Parse the top line and determine the pattern and number of fields."
        # load & look for the right pattern
        self.cacheFile()

    def cacheFile(self):
        "Read file into self.lines if not already there."
        if not self.fileobj:
            self.openFile()

    def openFile(self):
        self.dialect = None
        self.fileobj = open(self.file, "rbU")
        self.data = self.fileobj.read()
        if self.data.startswith(codecs.BOM_UTF8):
            self.data = self.data[len(codecs.BOM_UTF8):]
        def sub(s):
            return re.sub("^\#.*", "", s)
        self.data = [sub(x)+"\n" for x in self.data.split("\n") if sub(x)]
        if self.data:
            if self.data[0].startswith("tags:"):
                tags = unicode(self.data[0][5:], "utf8").strip()
                self.tagsToAdd = tags.split(" ")
                del self.data[0]
            self.updateDelimiter()
        if not self.dialect and not self.delimiter:
            raise Exception("unknownFormat")

    def updateDelimiter(self):
        def err():
            raise Exception("unknownFormat")
        self.dialect = None
        sniffer = csv.Sniffer()
        delims = [',', '\t', ';', ':']
        if not self.delimiter:
            try:
                self.dialect = sniffer.sniff("\n".join(self.data[:10]),
                                             delims)
            except:
                try:
                    self.dialect = sniffer.sniff(self.data[0], delims)
                except:
                    pass
        if self.dialect:
            try:
                reader = csv.reader(self.data, self.dialect, doublequote=True)
            except:
                err()
        else:
            if not self.delimiter:
                if "\t" in self.data[0]:
                    self.delimiter = "\t"
                elif ";" in self.data[0]:
                    self.delimiter = ";"
                elif "," in self.data[0]:
                    self.delimiter = ","
                else:
                    self.delimiter = " "
            reader = csv.reader(self.data, delimiter=self.delimiter, doublequote=True)
        try:
            self.numFields = len(reader.next())
        except:
            err()
        self.initMapping()

    def fields(self):
        "Number of fields."
        self.open()
        return self.numFields

    def noteFromFields(self, fields):
        note = ForeignNote()
        note.fields.extend([x.strip().replace("\n", "<br>") for x in fields])
        note.tags.extend(self.tagsToAdd)
        return note

########NEW FILE########
__FILENAME__ = mnemo
# -*- coding: utf-8 -*-
# Copyright: Damien Elmes <anki@ichi2.net>
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

import time, re
from anki.db import DB
from anki.importing.base import Importer
from anki.importing.noteimp import NoteImporter, ForeignNote, ForeignCard
from anki.utils import checksum, base91
from anki.stdmodels import addBasicModel
from anki.lang import _
from anki.lang import ngettext

class MnemosyneImporter(NoteImporter):

    needMapper = False
    update = False

    def run(self):
        db = DB(self.file)
        ver = db.scalar(
            "select value from global_variables where key='version'")
        assert ver.startswith('Mnemosyne SQL 1')
        # gather facts into temp objects
        curid = None
        notes = {}
        note = None
        for _id, id, k, v in db.execute("""
select _id, id, key, value from facts f, data_for_fact d where
f._id=d._fact_id"""):
            if id != curid:
                if note:
                    notes[note['_id']] = note
                note = {'_id': _id}
                curid = id
            note[k] = v
        if note:
            notes[note['_id']] = note
        # gather cards
        front = []
        frontback = []
        vocabulary = []
        for row in db.execute("""
select _fact_id, fact_view_id, tags, next_rep, last_rep, easiness,
acq_reps+ret_reps, lapses from cards"""):
            # categorize note
            note = notes[row[0]]
            if row[1] == "1.1":
                front.append(note)
            elif row[1] == "2.1":
                frontback.append(note)
            elif row[1] == "3.1":
                vocabulary.append(note)
            # merge tags into note
            tags = row[2].replace(", ", "\x1f").replace(" ", "_")
            tags = tags.replace("\x1f", " ")
            if "tags" not in note:
                note['tags'] = []
            note['tags'] += self.col.tags.split(tags)
            note['tags'] = self.col.tags.canonify(note['tags'])
            # if it's a new card we can go with the defaults
            if row[3] == -1:
                continue
            # add the card
            c = ForeignCard()
            c.factor = int(row[5]*1000)
            c.reps = row[6]
            c.lapses = row[7]
            # ivl is inferred in mnemosyne
            next, prev = row[3:5]
            c.ivl = max(1, (next - prev)/86400)
            # work out how long we've got left
            rem = int((next - time.time())/86400)
            c.due = self.col.sched.today+rem
            # get ord
            m = re.match("\d+\.(\d+)", row[1])
            ord = int(m.group(1))-1
            if 'cards' not in note:
                note['cards'] = {}
            note['cards'][ord] = c
        self._addFronts(front)
        total = self.total
        self._addFrontBacks(frontback)
        total += self.total
        self._addVocabulary(vocabulary)
        self.total += total
        self.log.append(ngettext("%d note imported.", "%d notes imported.", self.total) % self.total)

    def fields(self):
        return self._fields

    def _addFronts(self, notes, model=None, fields=("f", "b")):
        data = []
        for orig in notes:
            # create a foreign note object
            n = ForeignNote()
            n.fields = []
            for f in fields:
                n.fields.append(orig.get(f, ''))
            n.tags = orig['tags']
            n.cards = orig.get('cards', {})
            data.append(n)
        # add a basic model
        if not model:
            model = addBasicModel(self.col)
        model['name'] = "Mnemosyne-FrontOnly"
        mm = self.col.models
        mm.save(model)
        mm.setCurrent(model)
        self.model = model
        self._fields = len(model['flds'])
        self.initMapping()
        # import
        self.importNotes(data)

    def _addFrontBacks(self, notes):
        m = addBasicModel(self.col)
        m['name'] = "Mnemosyne-FrontBack"
        mm = self.col.models
        t = mm.newTemplate("Back")
        t['qfmt'] = "{{Back}}"
        t['afmt'] = t['qfmt'] + "\n\n<hr id=answer>\n\n{{Front}}"
        mm.addTemplate(m, t)
        self._addFronts(notes, m)

    def _addVocabulary(self, notes):
        mm = self.col.models
        m = mm.new("Mnemosyne-Vocabulary")
        for f in "Expression", "Pronunciation", "Meaning", "Notes":
            fm = mm.newField(f)
            mm.addField(m, fm)
        t = mm.newTemplate("Recognition")
        t['qfmt'] = "{{Expression}}"
        t['afmt'] = t['qfmt'] + """\n\n<hr id=answer>\n\n\
{{Pronunciation}}<br>\n{{Meaning}}<br>\n{{Notes}}"""
        mm.addTemplate(m, t)
        t = mm.newTemplate("Production")
        t['qfmt'] = "{{Meaning}}"
        t['afmt'] = t['qfmt'] + """\n\n<hr id=answer>\n\n\
{{Expression}}<br>\n{{Pronunciation}}<br>\n{{Notes}}"""
        mm.addTemplate(m, t)
        mm.add(m)
        self._addFronts(notes, m, fields=("f", "p_1", "m_1", "n"))

########NEW FILE########
__FILENAME__ = noteimp
# -*- coding: utf-8 -*-
# Copyright: Damien Elmes <anki@ichi2.net>
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

import time, cgi
from anki.lang import _
from anki.utils import fieldChecksum, ids2str, guid64, timestampID, \
    joinFields, intTime, splitFields
from anki.errors import *
from anki.importing.base import Importer
from anki.lang import ngettext

# Stores a list of fields, tags and deck
######################################################################

class ForeignNote(object):
    "An temporary object storing fields and attributes."
    def __init__(self):
        self.fields = []
        self.tags = []
        self.deck = None
        self.cards = {} # map of ord -> card

class ForeignCard(object):
    def __init__(self):
        self.due = 0
        self.ivl = 1
        self.factor = 2500
        self.reps = 0
        self.lapses = 0

# Base class for CSV and similar text-based imports
######################################################################

# The mapping is list of input fields, like:
# ['Expression', 'Reading', '_tags', None]
# - None means that the input should be discarded
# - _tags maps to note tags
# If the first field of the model is not in the map, the map is invalid.

# The import mode is one of:
# 0: update if first field matches existing note
# 1: ignore if first field matches existing note
# 2: import even if first field matches existing note

class NoteImporter(Importer):

    needMapper = True
    needDelimiter = False
    allowHTML = False
    importMode = 0

    def __init__(self, col, file):
        Importer.__init__(self, col, file)
        self.model = col.models.current()
        self.mapping = None
        self._deckMap = {}

    def run(self):
        "Import."
        assert self.mapping
        c = self.foreignNotes()
        self.importNotes(c)

    def fields(self):
        "The number of fields."
        return 0

    def initMapping(self):
        flds = [f['name'] for f in self.model['flds']]
        # truncate to provided count
        flds = flds[0:self.fields()]
        # if there's room left, add tags
        if self.fields() > len(flds):
            flds.append("_tags")
        # and if there's still room left, pad
        flds = flds + [None] * (self.fields() - len(flds))
        self.mapping = flds

    def mappingOk(self):
        return self.model['flds'][0]['name'] in self.mapping

    def foreignNotes(self):
        "Return a list of foreign notes for importing."
        assert 0

    def open(self):
        "Open file and ensure it's in the right format."
        return

    def importNotes(self, notes):
        "Convert each card into a note, apply attributes and add to col."
        assert self.mappingOk()
        # note whether tags are mapped
        self._tagsMapped = False
        for f in self.mapping:
            if f == "_tags":
                self._tagsMapped = True
        # gather checks for duplicate comparison
        csums = {}
        for csum, id in self.col.db.execute(
            "select csum, id from notes where mid = ?", self.model['id']):
            if csum in csums:
                csums[csum].append(id)
            else:
                csums[csum] = [id]
        firsts = {}
        fld0idx = self.mapping.index(self.model['flds'][0]['name'])
        self._fmap = self.col.models.fieldMap(self.model)
        self._nextID = timestampID(self.col.db, "notes")
        # loop through the notes
        updates = []
        new = []
        self._ids = []
        self._cards = []
        self._emptyNotes = False
        for n in notes:
            if not self.allowHTML:
                for c in range(len(n.fields)):
                    n.fields[c] = cgi.escape(n.fields[c])
            fld0 = n.fields[fld0idx]
            csum = fieldChecksum(fld0)
            # first field must exist
            if not fld0:
                self.log.append(_("Empty first field: %s") %
                                " ".join(n.fields))
                continue
            # earlier in import?
            if fld0 in firsts and self.importMode != 2:
                # duplicates in source file; log and ignore
                self.log.append(_("Appeared twice in file: %s") %
                                fld0)
                continue
            firsts[fld0] = True
            # already exists?
            found = False
            if csum in csums:
                # csum is not a guarantee; have to check
                for id in csums[csum]:
                    flds = self.col.db.scalar(
                        "select flds from notes where id = ?", id)
                    sflds = splitFields(flds)
                    if fld0 == sflds[0]:
                        # duplicate
                        found = True
                        if self.importMode == 0:
                            data = self.updateData(n, id, sflds)
                            if data:
                                updates.append(data)
                                found = True
                            break
                        elif self.importMode == 2:
                            # allow duplicates in this case
                            found = False
            # newly add
            if not found:
                data = self.newData(n)
                if data:
                    new.append(data)
                    # note that we've seen this note once already
                    firsts[fld0] = True
        self.addNew(new)
        self.addUpdates(updates)
        self.col.updateFieldCache(self._ids)
        # generate cards
        if self.col.genCards(self._ids):
            self.log.insert(0, _(
                "Empty cards found. Please run Tools>Maintenance>Empty Cards."))
        # apply scheduling updates
        self.updateCards()
        # make sure to update sflds, etc
        part1 = ngettext("%d note added", "%d notes added", len(new)) % len(new)
        part2 = ngettext("%d note updated", "%d notes updated", self.updateCount) % self.updateCount
        self.log.append("%s, %s." % (part1, part2))
        if self._emptyNotes:
            self.log.append(_("""\
One or more notes were not imported, because they didn't generate any cards. \
This can happen when you have empty fields or when you have not mapped the \
content in the text file to the correct fields."""))
        self.total = len(self._ids)

    def newData(self, n):
        id = self._nextID
        self._nextID += 1
        self._ids.append(id)
        if not self.processFields(n):
            return
        # note id for card updates later
        for ord, c in n.cards.items():
            self._cards.append((id, ord, c))
        self.col.tags.register(n.tags)
        return [id, guid64(), self.model['id'],
                intTime(), self.col.usn(), self.col.tags.join(n.tags),
                n.fieldsStr, "", "", 0, ""]

    def addNew(self, rows):
        self.col.db.executemany(
            "insert or replace into notes values (?,?,?,?,?,?,?,?,?,?,?)",
            rows)

    # need to document that deck is ignored in this case
    def updateData(self, n, id, sflds):
        self._ids.append(id)
        if not self.processFields(n, sflds):
            return
        if self._tagsMapped:
            self.col.tags.register(n.tags)
            tags = self.col.tags.join(n.tags)
            return [intTime(), self.col.usn(), n.fieldsStr, tags,
                    id, n.fieldsStr, tags]
        else:
            return [intTime(), self.col.usn(), n.fieldsStr,
                    id, n.fieldsStr]

    def addUpdates(self, rows):
        old = self.col.db.totalChanges()
        if self._tagsMapped:
            self.col.db.executemany("""
update notes set mod = ?, usn = ?, flds = ?, tags = ?
where id = ? and (flds != ? or tags != ?)""", rows)
        else:
            self.col.db.executemany("""
update notes set mod = ?, usn = ?, flds = ?
where id = ? and flds != ?""", rows)
        self.updateCount = self.col.db.totalChanges() - old

    def processFields(self, note, fields=None):
        if not fields:
            fields = [""]*len(self.model['flds'])
        for c, f in enumerate(self.mapping):
            if not f:
                continue
            elif f == "_tags":
                note.tags.extend(self.col.tags.split(note.fields[c]))
            else:
                sidx = self._fmap[f][0]
                fields[sidx] = note.fields[c]
        note.fieldsStr = joinFields(fields)
        ords = self.col.models.availOrds(self.model, note.fieldsStr)
        if not ords:
            self._emptyNotes = True
        return ords

    def updateCards(self):
        data = []
        for nid, ord, c in self._cards:
            data.append((c.ivl, c.due, c.factor, c.reps, c.lapses, nid, ord))
        # we assume any updated cards are reviews
        self.col.db.executemany("""
update cards set type = 2, queue = 2, ivl = ?, due = ?,
factor = ?, reps = ?, lapses = ? where nid = ? and ord = ?""", data)

########NEW FILE########
__FILENAME__ = supermemo_xml
# -*- coding: utf-8 -*-
# Copyright: petr.michalec@gmail.com
# License: GNU GPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

import sys

from anki.stdmodels import addBasicModel
from anki.importing.noteimp import NoteImporter, ForeignNote, ForeignCard
from anki.lang import _
from anki.lang import ngettext
from anki.errors import *

from xml.dom import minidom, Node
from types import DictType, InstanceType
from string import capwords, maketrans
import re, unicodedata, time

class SmartDict(dict):
    """
    See http://www.peterbe.com/plog/SmartDict
    Copyright 2005, Peter Bengtsson, peter@fry-it.com

    A smart dict can be instanciated either from a pythonic dict
    or an instance object (eg. SQL recordsets) but it ensures that you can
    do all the convenient lookups such as x.first_name, x['first_name'] or
    x.get('first_name').
    """

    def __init__(self, *a, **kw):
        if a:
            if type(a[0]) is DictType:
                kw.update(a[0])
            elif type(a[0]) is InstanceType:
                kw.update(a[0].__dict__)
            elif hasattr(a[0], '__class__') and a[0].__class__.__name__=='SmartDict':
                kw.update(a[0].__dict__)

        dict.__init__(self, **kw)
        self.__dict__ = self

class SuperMemoElement(SmartDict):
  "SmartDict wrapper to store SM Element data"

  def __init__(self, *a, **kw):
    SmartDict.__init__(self, *a, **kw)
    #default content
    self.__dict__['lTitle'] = None
    self.__dict__['Title'] = None
    self.__dict__['Question'] = None
    self.__dict__['Answer'] = None
    self.__dict__['Count'] = None
    self.__dict__['Type'] = None
    self.__dict__['ID'] = None
    self.__dict__['Interval'] = None
    self.__dict__['Lapses'] = None
    self.__dict__['Repetitions'] = None
    self.__dict__['LastRepetiton'] = None
    self.__dict__['AFactor'] = None
    self.__dict__['UFactor'] = None



# This is an AnkiImporter
class SupermemoXmlImporter(NoteImporter):

    needMapper = False

    """
    Supermemo XML export's to Anki parser.
    Goes through a SM collection and fetch all elements.

    My SM collection was a big mess where topics and items were mixed.
    I was unable to parse my content in a regular way like for loop on
    minidom.getElementsByTagName() etc. My collection had also an
    limitation, topics were splited into branches with max 100 items
    on each. Learning themes were in deep structure. I wanted to have
    full title on each element to be stored in tags.

    Code should be upgrade to support importing of SM2006 exports.
    """

    def __init__(self, *args):
        """Initialize internal varables.
        Pameters to be exposed to GUI are stored in self.META"""
        NoteImporter.__init__(self, *args)
        m = addBasicModel(self.col)
        m['name'] = "Supermemo"
        self.col.models.save(m)
        self.initMapping()

        self.lines = None
        self.numFields=int(2)

        # SmXmlParse VARIABLES
        self.xmldoc = None
        self.pieces = []
        self.cntBuf = [] #to store last parsed data
        self.cntElm = [] #to store SM Elements data
        self.cntCol = [] #to store SM Colections data

        # store some meta info related to parse algorithm
        # SmartDict works like dict / class wrapper
        self.cntMeta = SmartDict()
        self.cntMeta.popTitles = False
        self.cntMeta.title     = []

        # META stores controls of import scritp, should be
        # exposed to import dialog. These are default values.
        self.META = SmartDict()
        self.META.resetLearningData  = False            # implemented
        self.META.onlyMemorizedItems = False            # implemented
        self.META.loggerLevel = 2                       # implemented 0no,1info,2error,3debug
        self.META.tagAllTopics = True
        self.META.pathsToBeTagged = ['English for begginers', 'Advanced English 97', 'Phrasal Verbs']                # path patterns to be tagged - in gui entered like 'Advanced English 97|My Vocablary'
        self.META.tagMemorizedItems = True              # implemented
        self.META.logToStdOutput   = False              # implemented

        self.notes = []

## TOOLS

    def _fudgeText(self, text):
        "Replace sm syntax to Anki syntax"
        text = text.replace("\n\r", u"<br>")
        text = text.replace("\n", u"<br>")
        return text

    def _unicode2ascii(self,str):
        "Remove diacritic punctuation from strings (titles)"
        return u"".join([ c for c in unicodedata.normalize('NFKD', str) if not unicodedata.combining(c)])

    def _decode_htmlescapes(self,s):
        """Unescape HTML code."""
        #In case of bad formated html you can import MinimalSoup etc.. see btflsoup source code
        from BeautifulSoup import BeautifulStoneSoup as btflsoup

        #my sm2004 also ecaped & char in escaped sequences.
        s = re.sub(u'&amp;',u'&',s)
        #unescaped solitary chars < or > that were ok for minidom confuse btfl soup
        s = re.sub(u'>',u'&gt;',s)
        s = re.sub(u'<',u'&lt;',s)

        return unicode(btflsoup(s,convertEntities=btflsoup.HTML_ENTITIES ))


    def _unescape(self,s,initilize):
        """Note: This method is not used, BeautifulSoup does better job.
        """

        if self._unescape_trtable == None:
            self._unescape_trtable = (
              ('&euro;',u'€'), ('&#32;',u' '), ('&#33;',u'!'), ('&#34;',u'"'), ('&#35;',u'#'), ('&#36;',u'$'), ('&#37;',u'%'), ('&#38;',u'&'), ('&#39;',u"'"),
              ('&#40;',u'('), ('&#41;',u')'), ('&#42;',u'*'), ('&#43;',u'+'), ('&#44;',u','), ('&#45;',u'-'), ('&#46;',u'.'), ('&#47;',u'/'), ('&#48;',u'0'),
              ('&#49;',u'1'), ('&#50;',u'2'), ('&#51;',u'3'), ('&#52;',u'4'), ('&#53;',u'5'), ('&#54;',u'6'), ('&#55;',u'7'), ('&#56;',u'8'), ('&#57;',u'9'),
              ('&#58;',u':'), ('&#59;',u';'), ('&#60;',u'<'), ('&#61;',u'='), ('&#62;',u'>'), ('&#63;',u'?'), ('&#64;',u'@'), ('&#65;',u'A'), ('&#66;',u'B'),
              ('&#67;',u'C'), ('&#68;',u'D'), ('&#69;',u'E'), ('&#70;',u'F'), ('&#71;',u'G'), ('&#72;',u'H'), ('&#73;',u'I'), ('&#74;',u'J'), ('&#75;',u'K'),
              ('&#76;',u'L'), ('&#77;',u'M'), ('&#78;',u'N'), ('&#79;',u'O'), ('&#80;',u'P'), ('&#81;',u'Q'), ('&#82;',u'R'), ('&#83;',u'S'), ('&#84;',u'T'),
              ('&#85;',u'U'), ('&#86;',u'V'), ('&#87;',u'W'), ('&#88;',u'X'), ('&#89;',u'Y'), ('&#90;',u'Z'), ('&#91;',u'['), ('&#92;',u'\\'), ('&#93;',u']'),
              ('&#94;',u'^'), ('&#95;',u'_'), ('&#96;',u'`'), ('&#97;',u'a'), ('&#98;',u'b'), ('&#99;',u'c'), ('&#100;',u'd'), ('&#101;',u'e'), ('&#102;',u'f'),
              ('&#103;',u'g'), ('&#104;',u'h'), ('&#105;',u'i'), ('&#106;',u'j'), ('&#107;',u'k'), ('&#108;',u'l'), ('&#109;',u'm'), ('&#110;',u'n'),
              ('&#111;',u'o'), ('&#112;',u'p'), ('&#113;',u'q'), ('&#114;',u'r'), ('&#115;',u's'), ('&#116;',u't'), ('&#117;',u'u'), ('&#118;',u'v'),
              ('&#119;',u'w'), ('&#120;',u'x'), ('&#121;',u'y'), ('&#122;',u'z'), ('&#123;',u'{'), ('&#124;',u'|'), ('&#125;',u'}'), ('&#126;',u'~'),
              ('&#160;',u' '), ('&#161;',u'¡'), ('&#162;',u'¢'), ('&#163;',u'£'), ('&#164;',u'¤'), ('&#165;',u'¥'), ('&#166;',u'¦'), ('&#167;',u'§'),
              ('&#168;',u'¨'), ('&#169;',u'©'), ('&#170;',u'ª'), ('&#171;',u'«'), ('&#172;',u'¬'), ('&#173;',u'­'), ('&#174;',u'®'), ('&#175;',u'¯'),
              ('&#176;',u'°'), ('&#177;',u'±'), ('&#178;',u'²'), ('&#179;',u'³'), ('&#180;',u'´'), ('&#181;',u'µ'), ('&#182;',u'¶'), ('&#183;',u'·'),
              ('&#184;',u'¸'), ('&#185;',u'¹'), ('&#186;',u'º'), ('&#187;',u'»'), ('&#188;',u'¼'), ('&#189;',u'½'), ('&#190;',u'¾'), ('&#191;',u'¿'),
              ('&#192;',u'À'), ('&#193;',u'Á'), ('&#194;',u'Â'), ('&#195;',u'Ã'), ('&#196;',u'Ä'), ('&Aring;',u'Å'), ('&#197;',u'Å'), ('&#198;',u'Æ'),
              ('&#199;',u'Ç'), ('&#200;',u'È'), ('&#201;',u'É'), ('&#202;',u'Ê'), ('&#203;',u'Ë'), ('&#204;',u'Ì'), ('&#205;',u'Í'), ('&#206;',u'Î'),
              ('&#207;',u'Ï'), ('&#208;',u'Ð'), ('&#209;',u'Ñ'), ('&#210;',u'Ò'), ('&#211;',u'Ó'), ('&#212;',u'Ô'), ('&#213;',u'Õ'), ('&#214;',u'Ö'),
              ('&#215;',u'×'), ('&#216;',u'Ø'), ('&#217;',u'Ù'), ('&#218;',u'Ú'), ('&#219;',u'Û'), ('&#220;',u'Ü'), ('&#221;',u'Ý'), ('&#222;',u'Þ'),
              ('&#223;',u'ß'), ('&#224;',u'à'), ('&#225;',u'á'), ('&#226;',u'â'), ('&#227;',u'ã'), ('&#228;',u'ä'), ('&#229;',u'å'), ('&#230;',u'æ'),
              ('&#231;',u'ç'), ('&#232;',u'è'), ('&#233;',u'é'), ('&#234;',u'ê'), ('&#235;',u'ë'), ('&#236;',u'ì'), ('&iacute;',u'í'), ('&#237;',u'í'),
              ('&#238;',u'î'), ('&#239;',u'ï'), ('&#240;',u'ð'), ('&#241;',u'ñ'), ('&#242;',u'ò'), ('&#243;',u'ó'), ('&#244;',u'ô'), ('&#245;',u'õ'),
              ('&#246;',u'ö'), ('&#247;',u'÷'), ('&#248;',u'ø'), ('&#249;',u'ù'), ('&#250;',u'ú'), ('&#251;',u'û'), ('&#252;',u'ü'), ('&#253;',u'ý'),
              ('&#254;',u'þ'), ('&#255;',u'ÿ'), ('&#256;',u'Ā'), ('&#257;',u'ā'), ('&#258;',u'Ă'), ('&#259;',u'ă'), ('&#260;',u'Ą'), ('&#261;',u'ą'),
              ('&#262;',u'Ć'), ('&#263;',u'ć'), ('&#264;',u'Ĉ'), ('&#265;',u'ĉ'), ('&#266;',u'Ċ'), ('&#267;',u'ċ'), ('&#268;',u'Č'), ('&#269;',u'č'),
              ('&#270;',u'Ď'), ('&#271;',u'ď'), ('&#272;',u'Đ'), ('&#273;',u'đ'), ('&#274;',u'Ē'), ('&#275;',u'ē'), ('&#276;',u'Ĕ'), ('&#277;',u'ĕ'),
              ('&#278;',u'Ė'), ('&#279;',u'ė'), ('&#280;',u'Ę'), ('&#281;',u'ę'), ('&#282;',u'Ě'), ('&#283;',u'ě'), ('&#284;',u'Ĝ'), ('&#285;',u'ĝ'),
              ('&#286;',u'Ğ'), ('&#287;',u'ğ'), ('&#288;',u'Ġ'), ('&#289;',u'ġ'), ('&#290;',u'Ģ'), ('&#291;',u'ģ'), ('&#292;',u'Ĥ'), ('&#293;',u'ĥ'),
              ('&#294;',u'Ħ'), ('&#295;',u'ħ'), ('&#296;',u'Ĩ'), ('&#297;',u'ĩ'), ('&#298;',u'Ī'), ('&#299;',u'ī'), ('&#300;',u'Ĭ'), ('&#301;',u'ĭ'),
              ('&#302;',u'Į'), ('&#303;',u'į'), ('&#304;',u'İ'), ('&#305;',u'ı'), ('&#306;',u'Ĳ'), ('&#307;',u'ĳ'), ('&#308;',u'Ĵ'), ('&#309;',u'ĵ'),
              ('&#310;',u'Ķ'), ('&#311;',u'ķ'), ('&#312;',u'ĸ'), ('&#313;',u'Ĺ'), ('&#314;',u'ĺ'), ('&#315;',u'Ļ'), ('&#316;',u'ļ'), ('&#317;',u'Ľ'),
              ('&#318;',u'ľ'), ('&#319;',u'Ŀ'), ('&#320;',u'ŀ'), ('&#321;',u'Ł'), ('&#322;',u'ł'), ('&#323;',u'Ń'), ('&#324;',u'ń'), ('&#325;',u'Ņ'),
              ('&#326;',u'ņ'), ('&#327;',u'Ň'), ('&#328;',u'ň'), ('&#329;',u'ŉ'), ('&#330;',u'Ŋ'), ('&#331;',u'ŋ'), ('&#332;',u'Ō'), ('&#333;',u'ō'),
              ('&#334;',u'Ŏ'), ('&#335;',u'ŏ'), ('&#336;',u'Ő'), ('&#337;',u'ő'), ('&#338;',u'Œ'), ('&#339;',u'œ'), ('&#340;',u'Ŕ'), ('&#341;',u'ŕ'),
              ('&#342;',u'Ŗ'), ('&#343;',u'ŗ'), ('&#344;',u'Ř'), ('&#345;',u'ř'), ('&#346;',u'Ś'), ('&#347;',u'ś'), ('&#348;',u'Ŝ'), ('&#349;',u'ŝ'),
              ('&#350;',u'Ş'), ('&#351;',u'ş'), ('&#352;',u'Š'), ('&#353;',u'š'), ('&#354;',u'Ţ'), ('&#355;',u'ţ'), ('&#356;',u'Ť'), ('&#357;',u'ť'),
              ('&#358;',u'Ŧ'), ('&#359;',u'ŧ'), ('&#360;',u'Ũ'), ('&#361;',u'ũ'), ('&#362;',u'Ū'), ('&#363;',u'ū'), ('&#364;',u'Ŭ'), ('&#365;',u'ŭ'),
              ('&#366;',u'Ů'), ('&#367;',u'ů'), ('&#368;',u'Ű'), ('&#369;',u'ű'), ('&#370;',u'Ų'), ('&#371;',u'ų'), ('&#372;',u'Ŵ'), ('&#373;',u'ŵ'),
              ('&#374;',u'Ŷ'), ('&#375;',u'ŷ'), ('&#376;',u'Ÿ'), ('&#377;',u'Ź'), ('&#378;',u'ź'), ('&#379;',u'Ż'), ('&#380;',u'ż'), ('&#381;',u'Ž'),
              ('&#382;',u'ž'), ('&#383;',u'ſ'), ('&#340;',u'Ŕ'), ('&#341;',u'ŕ'), ('&#342;',u'Ŗ'), ('&#343;',u'ŗ'), ('&#344;',u'Ř'), ('&#345;',u'ř'),
              ('&#346;',u'Ś'), ('&#347;',u'ś'), ('&#348;',u'Ŝ'), ('&#349;',u'ŝ'), ('&#350;',u'Ş'), ('&#351;',u'ş'), ('&#352;',u'Š'), ('&#353;',u'š'),
              ('&#354;',u'Ţ'), ('&#355;',u'ţ'), ('&#356;',u'Ť'), ('&#577;',u'ť'), ('&#358;',u'Ŧ'), ('&#359;',u'ŧ'), ('&#360;',u'Ũ'), ('&#361;',u'ũ'),
              ('&#362;',u'Ū'), ('&#363;',u'ū'), ('&#364;',u'Ŭ'), ('&#365;',u'ŭ'), ('&#366;',u'Ů'), ('&#367;',u'ů'), ('&#368;',u'Ű'), ('&#369;',u'ű'),
              ('&#370;',u'Ų'), ('&#371;',u'ų'), ('&#372;',u'Ŵ'), ('&#373;',u'ŵ'), ('&#374;',u'Ŷ'), ('&#375;',u'ŷ'), ('&#376;',u'Ÿ'), ('&#377;',u'Ź'),
              ('&#378;',u'ź'), ('&#379;',u'Ż'), ('&#380;',u'ż'), ('&#381;',u'Ž'), ('&#382;',u'ž'), ('&#383;',u'ſ'),
          )


      #m = re.match()
      #s = s.replace(code[0], code[1])

## DEFAULT IMPORTER METHODS

    def foreignNotes(self):

        # Load file and parse it by minidom
        self.loadSource(self.file)

        # Migrating content / time consuming part
        # addItemToCards is called for each sm element
        self.logger(u'Parsing started.')
        self.parse()
        self.logger(u'Parsing done.')

        # Return imported cards
        self.total = len(self.notes)
        self.log.append(ngettext("%d card imported.", "%d cards imported.", self.total) % self.total)
        return self.notes

    def fields(self):
        return 2

## PARSER METHODS

    def addItemToCards(self,item):
        "This method actually do conversion"

        # new anki card
        note = ForeignNote()

        # clean Q and A
        note.fields.append(self._fudgeText(self._decode_htmlescapes(item.Question)))
        note.fields.append(self._fudgeText(self._decode_htmlescapes(item.Answer)))
        note.tags = []

        # pre-process scheduling data
        # convert learning data
        if (not self.META.resetLearningData
            and item.Interval >= 1
            and getattr(item, "LastRepetition", None)):
            # migration of LearningData algorithm
            tLastrep = time.mktime(time.strptime(item.LastRepetition, '%d.%m.%Y'))
            tToday = time.time()
            card = ForeignCard()
            card.ivl = int(item.Interval)
            card.lapses = int(item.Lapses)
            card.reps = int(item.Repetitions) + int(item.Lapses)
            nextDue = tLastrep + (float(item.Interval) * 86400.0)
            remDays = int((nextDue - time.time())/86400)
            card.due = self.col.sched.today+remDays
            card.factor = int(float(item.AFactor.replace(',','.'))*1000)
            note.cards[0] = card

        # categories & tags
        # it's worth to have every theme (tree structure of sm collection) stored in tags, but sometimes not
        # you can deceide if you are going to tag all toppics or just that containing some pattern
        tTaggTitle = False
        for pattern in self.META.pathsToBeTagged:
            if item.lTitle != None and pattern.lower() in u" ".join(item.lTitle).lower():
              tTaggTitle = True
              break
        if tTaggTitle or self.META.tagAllTopics:
          # normalize - remove diacritic punctuation from unicode chars to ascii
          item.lTitle = [ self._unicode2ascii(topic) for topic in item.lTitle]

          # Transfrom xyz / aaa / bbb / ccc on Title path to Tag  xyzAaaBbbCcc
          #  clean things like [999] or [111-2222] from title path, example: xyz / [1000-1200] zyx / xyz
          #  clean whitespaces
          #  set Capital letters for first char of the word
          tmp = list(set([ re.sub('(\[[0-9]+\])'   , ' ' , i ).replace('_',' ')  for i in item.lTitle ]))
          tmp = list(set([ re.sub('(\W)',' ', i )  for i in tmp ]))
          tmp = list(set([ re.sub( '^[0-9 ]+$','',i)  for i in tmp ]))
          tmp = list(set([ capwords(i).replace(' ','')  for i in tmp ]))
          tags = [ j[0].lower() + j[1:] for j in tmp if j.strip() <> '']

          note.tags += tags

          if self.META.tagMemorizedItems and item.Interval >0:
            note.tags.append("Memorized")

          self.logger(u'Element tags\t- ' + `note.tags`, level=3)

        self.notes.append(note)

    def logger(self,text,level=1):
        "Wrapper for Anki logger"

        dLevels={0:'',1:u'Info',2:u'Verbose',3:u'Debug'}
        if level<=self.META.loggerLevel:
          #self.deck.updateProgress(_(text))

          if self.META.logToStdOutput:
            print self.__class__.__name__+ u" - " + dLevels[level].ljust(9) +u' -\t'+ _(text)


    # OPEN AND LOAD
    def openAnything(self,source):
        "Open any source / actually only openig of files is used"

        if source == "-":
            return sys.stdin

        # try to open with urllib (if source is http, ftp, or file URL)
        import urllib
        try:
            return urllib.urlopen(source)
        except (IOError, OSError):
            pass

        # try to open with native open function (if source is pathname)
        try:
            return open(source)
        except (IOError, OSError):
            pass

        # treat source as string
        import StringIO
        return StringIO.StringIO(str(source))

    def loadSource(self, source):
        """Load source file and parse with xml.dom.minidom"""
        self.source = source
        self.logger(u'Load started...')
        sock = open(self.source)
        self.xmldoc = minidom.parse(sock).documentElement
        sock.close()
        self.logger(u'Load done.')


    # PARSE
    def parse(self, node=None):
        "Parse method - parses document elements"

        if node==None and self.xmldoc<>None:
          node = self.xmldoc

        _method = "parse_%s" % node.__class__.__name__
        if hasattr(self,_method):
          parseMethod = getattr(self, _method)
          parseMethod(node)
        else:
          self.logger(u'No handler for method %s' % _method, level=3)

    def parse_Document(self, node):
        "Parse XML document"

        self.parse(node.documentElement)

    def parse_Element(self, node):
        "Parse XML element"

        _method = "do_%s" % node.tagName
        if hasattr(self,_method):
          handlerMethod = getattr(self, _method)
          handlerMethod(node)
        else:
          self.logger(u'No handler for method %s' % _method, level=3)
          #print traceback.print_exc()

    def parse_Text(self, node):
        "Parse text inside elements. Text is stored into local buffer."

        text = node.data
        self.cntBuf.append(text)

    #def parse_Comment(self, node):
    #    """
    #    Source can contain XML comments, but we ignore them
    #    """
    #    pass


    # DO
    def do_SuperMemoCollection(self, node):
        "Process SM Collection"

        for child in node.childNodes: self.parse(child)

    def do_SuperMemoElement(self, node):
        "Process SM Element (Type - Title,Topics)"

        self.logger('='*45, level=3)

        self.cntElm.append(SuperMemoElement())
        self.cntElm[-1]['lTitle'] = self.cntMeta['title']

        #parse all child elements
        for child in node.childNodes: self.parse(child)

        #strip all saved strings, just for sure
        for key in self.cntElm[-1].keys():
          if hasattr(self.cntElm[-1][key], 'strip'):
            self.cntElm[-1][key]=self.cntElm[-1][key].strip()

        #pop current element
        smel = self.cntElm.pop()

        # Process cntElm if is valid Item (and not an Topic etc..)
        # if smel.Lapses != None and smel.Interval != None and smel.Question != None and smel.Answer != None:
        if smel.Title == None and smel.Question != None and smel.Answer != None:
          if smel.Answer.strip() !='' and smel.Question.strip() !='':

            # migrate only memorized otherway skip/continue
            if self.META.onlyMemorizedItems and not(int(smel.Interval) > 0):
              self.logger(u'Element skiped  \t- not memorized ...', level=3)
            else:
              #import sm element data to Anki
              self.addItemToCards(smel)
              self.logger(u"Import element \t- " + smel['Question'], level=3)

              #print element
              self.logger('-'*45, level=3)
              for key in smel.keys():
                self.logger('\t%s %s' % ((key+':').ljust(15),smel[key]), level=3 )
          else:
            self.logger(u'Element skiped  \t- no valid Q and A ...', level=3)


        else:
          # now we know that item was topic
          # parseing of whole node is now finished

          # test if it's really topic
          if smel.Title != None:
            # remove topic from title list
            t = self.cntMeta['title'].pop()
            self.logger(u'End of topic \t- %s' % (t), level=2)

    def do_Content(self, node):
        "Process SM element Content"

        for child in node.childNodes:
          if hasattr(child,'tagName') and child.firstChild != None:
            self.cntElm[-1][child.tagName]=child.firstChild.data

    def do_LearningData(self, node):
        "Process SM element LearningData"

        for child in node.childNodes:
          if hasattr(child,'tagName') and child.firstChild != None:
            self.cntElm[-1][child.tagName]=child.firstChild.data

    # It's being processed in do_Content now
    #def do_Question(self, node):
    #    for child in node.childNodes: self.parse(child)
    #    self.cntElm[-1][node.tagName]=self.cntBuf.pop()

    # It's being processed in do_Content now
    #def do_Answer(self, node):
    #    for child in node.childNodes: self.parse(child)
    #    self.cntElm[-1][node.tagName]=self.cntBuf.pop()

    def do_Title(self, node):
        "Process SM element Title"

        t = self._decode_htmlescapes(node.firstChild.data)
        self.cntElm[-1][node.tagName] = t
        self.cntMeta['title'].append(t)
        self.cntElm[-1]['lTitle'] = self.cntMeta['title']
        self.logger(u'Start of topic \t- ' + u" / ".join(self.cntMeta['title']), level=2)


    def do_Type(self, node):
        "Process SM element Type"

        if len(self.cntBuf) >=1 :
          self.cntElm[-1][node.tagName]=self.cntBuf.pop()


if __name__ == '__main__':

  # for testing you can start it standalone

  #file = u'/home/epcim/hg2g/dev/python/sm2anki/ADVENG2EXP.xxe.esc.zaloha_FINAL.xml'
  #file = u'/home/epcim/hg2g/dev/python/anki/libanki/tests/importing/supermemo/original_ENGLISHFORBEGGINERS_noOEM.xml'
  #file = u'/home/epcim/hg2g/dev/python/anki/libanki/tests/importing/supermemo/original_ENGLISHFORBEGGINERS_oem_1250.xml'
  file = str(sys.argv[1])
  impo = SupermemoXmlImporter(Deck(),file)
  impo.foreignCards()

  sys.exit(1)

# vim: ts=4 sts=2 ft=python

########NEW FILE########
__FILENAME__ = js
# Inlined js so we don't have to wrestle with packaging systems.
# jquery = jquery 1.5
# plot = flot 0.7 and the stack plugin
# ui = jquery ui 1.8.9
jquery = '''
/*\n * jQuery JavaScript Library v1.5\n * http://jquery.com/\n *\n * Copyright 2011, John Resig\n * Dual licensed under the MIT or GPL Version 2 licenses.\n * http://jquery.org/license\n *\n * Includes Sizzle.js\n * http://sizzlejs.com/\n * Copyright 2011, The Dojo Foundation\n * Released under the MIT, BSD, and GPL Licenses.\n *\n * Date: Mon Jan 31 08:31:29 2011 -0500\n */\n(function(aR,G){var ag=aR.document;var a=(function(){var bh=function(bC,bD){return new bh.fn.init(bC,bD,bf)},bx=aR.jQuery,bj=aR.$,bf,bB=/^(?:[^<]*(<[\\w\\W]+>)[^>]*$|#([\\w\\-]+)$)/,bp=/\\S/,bl=/^\\s+/,bg=/\\s+$/,bk=/\\d/,bd=/^<(\\w+)\\s*\\/?>(?:<\\/\\1>)?$/,bq=/^[\\],:{}\\s]*$/,bz=/\\\\(?:["\\\\\\/bfnrt]|u[0-9a-fA-F]{4})/g,bs=/"[^"\\\\\\n\\r]*"|true|false|null|-?\\d+(?:\\.\\d*)?(?:[eE][+\\-]?\\d+)?/g,bm=/(?:^|:|,)(?:\\s*\\[)+/g,bb=/(webkit)[ \\/]([\\w.]+)/,bu=/(opera)(?:.*version)?[ \\/]([\\w.]+)/,bt=/(msie) ([\\w.]+)/,bv=/(mozilla)(?:.*? rv:([\\w.]+))?/,bA=navigator.userAgent,by,bw=false,be,a6="then done fail isResolved isRejected promise".split(" "),a7,bo=Object.prototype.toString,bi=Object.prototype.hasOwnProperty,bc=Array.prototype.push,bn=Array.prototype.slice,br=String.prototype.trim,a8=Array.prototype.indexOf,ba={};bh.fn=bh.prototype={constructor:bh,init:function(bC,bG,bF){var bE,bH,bD,bI;if(!bC){return this}if(bC.nodeType){this.context=this[0]=bC;this.length=1;return this}if(bC==="body"&&!bG&&ag.body){this.context=ag;this[0]=ag.body;this.selector="body";this.length=1;return this}if(typeof bC==="string"){bE=bB.exec(bC);if(bE&&(bE[1]||!bG)){if(bE[1]){bG=bG instanceof bh?bG[0]:bG;bI=(bG?bG.ownerDocument||bG:ag);bD=bd.exec(bC);if(bD){if(bh.isPlainObject(bG)){bC=[ag.createElement(bD[1])];bh.fn.attr.call(bC,bG,true)}else{bC=[bI.createElement(bD[1])]}}else{bD=bh.buildFragment([bE[1]],[bI]);bC=(bD.cacheable?bh.clone(bD.fragment):bD.fragment).childNodes}return bh.merge(this,bC)}else{bH=ag.getElementById(bE[2]);if(bH&&bH.parentNode){if(bH.id!==bE[2]){return bF.find(bC)}this.length=1;this[0]=bH}this.context=ag;this.selector=bC;return this}}else{if(!bG||bG.jquery){return(bG||bF).find(bC)}else{return this.constructor(bG).find(bC)}}}else{if(bh.isFunction(bC)){return bF.ready(bC)}}if(bC.selector!==G){this.selector=bC.selector;this.context=bC.context}return bh.makeArray(bC,this)},selector:"",jquery:"1.5",length:0,size:function(){return this.length},toArray:function(){return bn.call(this,0)},get:function(bC){return bC==null?this.toArray():(bC<0?this[this.length+bC]:this[bC])},pushStack:function(bD,bF,bC){var bE=this.constructor();if(bh.isArray(bD)){bc.apply(bE,bD)}else{bh.merge(bE,bD)}bE.prevObject=this;bE.context=this.context;if(bF==="find"){bE.selector=this.selector+(this.selector?" ":"")+bC}else{if(bF){bE.selector=this.selector+"."+bF+"("+bC+")"}}return bE},each:function(bD,bC){return bh.each(this,bD,bC)},ready:function(bC){bh.bindReady();be.done(bC);return this},eq:function(bC){return bC===-1?this.slice(bC):this.slice(bC,+bC+1)},first:function(){return this.eq(0)},last:function(){return this.eq(-1)},slice:function(){return this.pushStack(bn.apply(this,arguments),"slice",bn.call(arguments).join(","))},map:function(bC){return this.pushStack(bh.map(this,function(bE,bD){return bC.call(bE,bD,bE)}))},end:function(){return this.prevObject||this.constructor(null)},push:bc,sort:[].sort,splice:[].splice};bh.fn.init.prototype=bh.fn;bh.extend=bh.fn.extend=function(){var bL,bE,bC,bD,bI,bJ,bH=arguments[0]||{},bG=1,bF=arguments.length,bK=false;if(typeof bH==="boolean"){bK=bH;bH=arguments[1]||{};bG=2}if(typeof bH!=="object"&&!bh.isFunction(bH)){bH={}}if(bF===bG){bH=this;--bG}for(;bG<bF;bG++){if((bL=arguments[bG])!=null){for(bE in bL){bC=bH[bE];bD=bL[bE];if(bH===bD){continue}if(bK&&bD&&(bh.isPlainObject(bD)||(bI=bh.isArray(bD)))){if(bI){bI=false;bJ=bC&&bh.isArray(bC)?bC:[]}else{bJ=bC&&bh.isPlainObject(bC)?bC:{}}bH[bE]=bh.extend(bK,bJ,bD)}else{if(bD!==G){bH[bE]=bD}}}}}return bH};bh.extend({noConflict:function(bC){aR.$=bj;if(bC){aR.jQuery=bx}return bh},isReady:false,readyWait:1,ready:function(bC){if(bC===true){bh.readyWait--}if(!bh.readyWait||(bC!==true&&!bh.isReady)){if(!ag.body){return setTimeout(bh.ready,1)}bh.isReady=true;if(bC!==true&&--bh.readyWait>0){return}be.resolveWith(ag,[bh]);if(bh.fn.trigger){bh(ag).trigger("ready").unbind("ready")}}},bindReady:function(){if(bw){return}bw=true;if(ag.readyState==="complete"){return setTimeout(bh.ready,1)}if(ag.addEventListener){ag.addEventListener("DOMContentLoaded",a7,false);aR.addEventListener("load",bh.ready,false)}else{if(ag.attachEvent){ag.attachEvent("onreadystatechange",a7);aR.attachEvent("onload",bh.ready);var bC=false;try{bC=aR.frameElement==null}catch(bD){}if(ag.documentElement.doScroll&&bC){a9()}}}},isFunction:function(bC){return bh.type(bC)==="function"},isArray:Array.isArray||function(bC){return bh.type(bC)==="array"},isWindow:function(bC){return bC&&typeof bC==="object"&&"setInterval" in bC},isNaN:function(bC){return bC==null||!bk.test(bC)||isNaN(bC)},type:function(bC){return bC==null?String(bC):ba[bo.call(bC)]||"object"},isPlainObject:function(bD){if(!bD||bh.type(bD)!=="object"||bD.nodeType||bh.isWindow(bD)){return false}if(bD.constructor&&!bi.call(bD,"constructor")&&!bi.call(bD.constructor.prototype,"isPrototypeOf")){return false}var bC;for(bC in bD){}return bC===G||bi.call(bD,bC)},isEmptyObject:function(bD){for(var bC in bD){return false}return true},error:function(bC){throw bC},parseJSON:function(bC){if(typeof bC!=="string"||!bC){return null}bC=bh.trim(bC);if(bq.test(bC.replace(bz,"@").replace(bs,"]").replace(bm,""))){return aR.JSON&&aR.JSON.parse?aR.JSON.parse(bC):(new Function("return "+bC))()}else{bh.error("Invalid JSON: "+bC)}},parseXML:function(bE,bC,bD){if(aR.DOMParser){bD=new DOMParser();bC=bD.parseFromString(bE,"text/xml")}else{bC=new ActiveXObject("Microsoft.XMLDOM");bC.async="false";bC.loadXML(bE)}bD=bC.documentElement;if(!bD||!bD.nodeName||bD.nodeName==="parsererror"){bh.error("Invalid XML: "+bE)}return bC},noop:function(){},globalEval:function(bE){if(bE&&bp.test(bE)){var bD=ag.getElementsByTagName("head")[0]||ag.documentElement,bC=ag.createElement("script");bC.type="text/javascript";if(bh.support.scriptEval()){bC.appendChild(ag.createTextNode(bE))}else{bC.text=bE}bD.insertBefore(bC,bD.firstChild);bD.removeChild(bC)}},nodeName:function(bD,bC){return bD.nodeName&&bD.nodeName.toUpperCase()===bC.toUpperCase()},each:function(bF,bJ,bE){var bD,bG=0,bH=bF.length,bC=bH===G||bh.isFunction(bF);if(bE){if(bC){for(bD in bF){if(bJ.apply(bF[bD],bE)===false){break}}}else{for(;bG<bH;){if(bJ.apply(bF[bG++],bE)===false){break}}}}else{if(bC){for(bD in bF){if(bJ.call(bF[bD],bD,bF[bD])===false){break}}}else{for(var bI=bF[0];bG<bH&&bJ.call(bI,bG,bI)!==false;bI=bF[++bG]){}}}return bF},trim:br?function(bC){return bC==null?"":br.call(bC)}:function(bC){return bC==null?"":bC.toString().replace(bl,"").replace(bg,"")},makeArray:function(bF,bD){var bC=bD||[];if(bF!=null){var bE=bh.type(bF);if(bF.length==null||bE==="string"||bE==="function"||bE==="regexp"||bh.isWindow(bF)){bc.call(bC,bF)}else{bh.merge(bC,bF)}}return bC},inArray:function(bE,bF){if(bF.indexOf){return bF.indexOf(bE)}for(var bC=0,bD=bF.length;bC<bD;bC++){if(bF[bC]===bE){return bC}}return -1},merge:function(bG,bE){var bF=bG.length,bD=0;if(typeof bE.length==="number"){for(var bC=bE.length;bD<bC;bD++){bG[bF++]=bE[bD]}}else{while(bE[bD]!==G){bG[bF++]=bE[bD++]}}bG.length=bF;return bG},grep:function(bD,bI,bC){var bE=[],bH;bC=!!bC;for(var bF=0,bG=bD.length;bF<bG;bF++){bH=!!bI(bD[bF],bF);if(bC!==bH){bE.push(bD[bF])}}return bE},map:function(bD,bI,bC){var bE=[],bH;for(var bF=0,bG=bD.length;bF<bG;bF++){bH=bI(bD[bF],bF,bC);if(bH!=null){bE[bE.length]=bH}}return bE.concat.apply([],bE)},guid:1,proxy:function(bE,bD,bC){if(arguments.length===2){if(typeof bD==="string"){bC=bE;bE=bC[bD];bD=G}else{if(bD&&!bh.isFunction(bD)){bC=bD;bD=G}}}if(!bD&&bE){bD=function(){return bE.apply(bC||this,arguments)}}if(bE){bD.guid=bE.guid=bE.guid||bD.guid||bh.guid++}return bD},access:function(bC,bK,bI,bE,bH,bJ){var bD=bC.length;if(typeof bK==="object"){for(var bF in bK){bh.access(bC,bF,bK[bF],bE,bH,bI)}return bC}if(bI!==G){bE=!bJ&&bE&&bh.isFunction(bI);for(var bG=0;bG<bD;bG++){bH(bC[bG],bK,bE?bI.call(bC[bG],bG,bH(bC[bG],bK)):bI,bJ)}return bC}return bD?bH(bC[0],bK):G},now:function(){return(new Date()).getTime()},_Deferred:function(){var bF=[],bG,bD,bE,bC={done:function(){if(!bE){var bI=arguments,bJ,bM,bL,bK,bH;if(bG){bH=bG;bG=0}for(bJ=0,bM=bI.length;bJ<bM;bJ++){bL=bI[bJ];bK=bh.type(bL);if(bK==="array"){bC.done.apply(bC,bL)}else{if(bK==="function"){bF.push(bL)}}}if(bH){bC.resolveWith(bH[0],bH[1])}}return this},resolveWith:function(bI,bH){if(!bE&&!bG&&!bD){bD=1;try{while(bF[0]){bF.shift().apply(bI,bH)}}finally{bG=[bI,bH];bD=0}}return this},resolve:function(){bC.resolveWith(bh.isFunction(this.promise)?this.promise():this,arguments);return this},isResolved:function(){return !!(bD||bG)},cancel:function(){bE=1;bF=[];return this}};return bC},Deferred:function(bD){var bC=bh._Deferred(),bF=bh._Deferred(),bE;bh.extend(bC,{then:function(bH,bG){bC.done(bH).fail(bG);return this},fail:bF.done,rejectWith:bF.resolveWith,reject:bF.resolve,isRejected:bF.isResolved,promise:function(bH,bG){if(bH==null){if(bE){return bE}bE=bH={}}bG=a6.length;while(bG--){bH[a6[bG]]=bC[a6[bG]]}return bH}});bC.then(bF.cancel,bC.cancel);delete bC.cancel;if(bD){bD.call(bC,bC)}return bC},when:function(bF){var bE=arguments,bG=bE.length,bD=bG<=1&&bF&&bh.isFunction(bF.promise)?bF:bh.Deferred(),bH=bD.promise(),bC;if(bG>1){bC=new Array(bG);bh.each(bE,function(bI,bJ){bh.when(bJ).then(function(bK){bC[bI]=arguments.length>1?bn.call(arguments,0):bK;if(!--bG){bD.resolveWith(bH,bC)}},bD.reject)})}else{if(bD!==bF){bD.resolve(bF)}}return bH},uaMatch:function(bD){bD=bD.toLowerCase();var bC=bb.exec(bD)||bu.exec(bD)||bt.exec(bD)||bD.indexOf("compatible")<0&&bv.exec(bD)||[];return{browser:bC[1]||"",version:bC[2]||"0"}},sub:function(){function bD(bF,bG){return new bD.fn.init(bF,bG)}bh.extend(true,bD,this);bD.superclass=this;bD.fn=bD.prototype=this();bD.fn.constructor=bD;bD.subclass=this.subclass;bD.fn.init=function bE(bF,bG){if(bG&&bG instanceof bh&&!(bG instanceof bD)){bG=bD(bG)}return bh.fn.init.call(this,bF,bG,bC)};bD.fn.init.prototype=bD.fn;var bC=bD(ag);return bD},browser:{}});be=bh._Deferred();bh.each("Boolean Number String Function Array Date RegExp Object".split(" "),function(bD,bC){ba["[object "+bC+"]"]=bC.toLowerCase()});by=bh.uaMatch(bA);if(by.browser){bh.browser[by.browser]=true;bh.browser.version=by.version}if(bh.browser.webkit){bh.browser.safari=true}if(a8){bh.inArray=function(bC,bD){return a8.call(bD,bC)}}bf=bh(ag);if(ag.addEventListener){a7=function(){ag.removeEventListener("DOMContentLoaded",a7,false);bh.ready()}}else{if(ag.attachEvent){a7=function(){if(ag.readyState==="complete"){ag.detachEvent("onreadystatechange",a7);bh.ready()}}}}function a9(){if(bh.isReady){return}try{ag.documentElement.doScroll("left")}catch(bC){setTimeout(a9,1);return}bh.ready()}return(aR.jQuery=aR.$=bh)})();(function(){a.support={};var a6=ag.createElement("div");a6.style.display="none";a6.innerHTML="   <link/><table></table><a href=\'/a\' style=\'color:red;float:left;opacity:.55;\'>a</a><input type=\'checkbox\'/>";var bd=a6.getElementsByTagName("*"),bb=a6.getElementsByTagName("a")[0],bc=ag.createElement("select"),a7=bc.appendChild(ag.createElement("option"));if(!bd||!bd.length||!bb){return}a.support={leadingWhitespace:a6.firstChild.nodeType===3,tbody:!a6.getElementsByTagName("tbody").length,htmlSerialize:!!a6.getElementsByTagName("link").length,style:/red/.test(bb.getAttribute("style")),hrefNormalized:bb.getAttribute("href")==="/a",opacity:/^0.55$/.test(bb.style.opacity),cssFloat:!!bb.style.cssFloat,checkOn:a6.getElementsByTagName("input")[0].value==="on",optSelected:a7.selected,deleteExpando:true,optDisabled:false,checkClone:false,_scriptEval:null,noCloneEvent:true,boxModel:null,inlineBlockNeedsLayout:false,shrinkWrapBlocks:false,reliableHiddenOffsets:true};bc.disabled=true;a.support.optDisabled=!a7.disabled;a.support.scriptEval=function(){if(a.support._scriptEval===null){var bf=ag.documentElement,bg=ag.createElement("script"),bi="script"+a.now();bg.type="text/javascript";try{bg.appendChild(ag.createTextNode("window."+bi+"=1;"))}catch(bh){}bf.insertBefore(bg,bf.firstChild);if(aR[bi]){a.support._scriptEval=true;delete aR[bi]}else{a.support._scriptEval=false}bf.removeChild(bg);bf=bg=bi=null}return a.support._scriptEval};try{delete a6.test}catch(a8){a.support.deleteExpando=false}if(a6.attachEvent&&a6.fireEvent){a6.attachEvent("onclick",function be(){a.support.noCloneEvent=false;a6.detachEvent("onclick",be)});a6.cloneNode(true).fireEvent("onclick")}a6=ag.createElement("div");a6.innerHTML="<input type=\'radio\' name=\'radiotest\' checked=\'checked\'/>";var a9=ag.createDocumentFragment();a9.appendChild(a6.firstChild);a.support.checkClone=a9.cloneNode(true).cloneNode(true).lastChild.checked;a(function(){var bh=ag.createElement("div"),bf=ag.getElementsByTagName("body")[0];if(!bf){return}bh.style.width=bh.style.paddingLeft="1px";bf.appendChild(bh);a.boxModel=a.support.boxModel=bh.offsetWidth===2;if("zoom" in bh.style){bh.style.display="inline";bh.style.zoom=1;a.support.inlineBlockNeedsLayout=bh.offsetWidth===2;bh.style.display="";bh.innerHTML="<div style=\'width:4px;\'></div>";a.support.shrinkWrapBlocks=bh.offsetWidth!==2}bh.innerHTML="<table><tr><td style=\'padding:0;border:0;display:none\'></td><td>t</td></tr></table>";var bg=bh.getElementsByTagName("td");a.support.reliableHiddenOffsets=bg[0].offsetHeight===0;bg[0].style.display="";bg[1].style.display="none";a.support.reliableHiddenOffsets=a.support.reliableHiddenOffsets&&bg[0].offsetHeight===0;bh.innerHTML="";bf.removeChild(bh).style.display="none";bh=bg=null});var ba=function(bf){var bh=ag.createElement("div");bf="on"+bf;if(!bh.attachEvent){return true}var bg=(bf in bh);if(!bg){bh.setAttribute(bf,"return;");bg=typeof bh[bf]==="function"}bh=null;return bg};a.support.submitBubbles=ba("submit");a.support.changeBubbles=ba("change");a6=bd=bb=null})();var av=/^(?:\\{.*\\}|\\[.*\\])$/;a.extend({cache:{},uuid:0,expando:"jQuery"+(a.fn.jquery+Math.random()).replace(/\\D/g,""),noData:{embed:true,object:"clsid:D27CDB6E-AE6D-11cf-96B8-444553540000",applet:true},hasData:function(a6){a6=a6.nodeType?a.cache[a6[a.expando]]:a6[a.expando];return !!a6&&!a.isEmptyObject(a6)},data:function(a9,a7,bb,ba){if(!a.acceptData(a9)){return}var be=a.expando,bd=typeof a7==="string",bc,bf=a9.nodeType,a6=bf?a.cache:a9,a8=bf?a9[a.expando]:a9[a.expando]&&a.expando;if((!a8||(ba&&a8&&!a6[a8][be]))&&bd&&bb===G){return}if(!a8){if(bf){a9[a.expando]=a8=++a.uuid}else{a8=a.expando}}if(!a6[a8]){a6[a8]={}}if(typeof a7==="object"){if(ba){a6[a8][be]=a.extend(a6[a8][be],a7)}else{a6[a8]=a.extend(a6[a8],a7)}}bc=a6[a8];if(ba){if(!bc[be]){bc[be]={}}bc=bc[be]}if(bb!==G){bc[a7]=bb}if(a7==="events"&&!bc[a7]){return bc[be]&&bc[be].events}return bd?bc[a7]:bc},removeData:function(ba,a8,bb){if(!a.acceptData(ba)){return}var bd=a.expando,be=ba.nodeType,a7=be?a.cache:ba,a9=be?ba[a.expando]:a.expando;if(!a7[a9]){return}if(a8){var bc=bb?a7[a9][bd]:a7[a9];if(bc){delete bc[a8];if(!a.isEmptyObject(bc)){return}}}if(bb){delete a7[a9][bd];if(!a.isEmptyObject(a7[a9])){return}}var a6=a7[a9][bd];if(a.support.deleteExpando||a7!=aR){delete a7[a9]}else{a7[a9]=null}if(a6){a7[a9]={};a7[a9][bd]=a6}else{if(be){if(a.support.deleteExpando){delete ba[a.expando]}else{if(ba.removeAttribute){ba.removeAttribute(a.expando)}else{ba[a.expando]=null}}}}},_data:function(a7,a6,a8){return a.data(a7,a6,a8,true)},acceptData:function(a7){if(a7.nodeName){var a6=a.noData[a7.nodeName.toLowerCase()];if(a6){return !(a6===true||a7.getAttribute("classid")!==a6)}}return true}});a.fn.extend({data:function(ba,bc){var bb=null;if(typeof ba==="undefined"){if(this.length){bb=a.data(this[0]);if(this[0].nodeType===1){var a6=this[0].attributes,a8;for(var a9=0,a7=a6.length;a9<a7;a9++){a8=a6[a9].name;if(a8.indexOf("data-")===0){a8=a8.substr(5);aM(this[0],a8,bb[a8])}}}}return bb}else{if(typeof ba==="object"){return this.each(function(){a.data(this,ba)})}}var bd=ba.split(".");bd[1]=bd[1]?"."+bd[1]:"";if(bc===G){bb=this.triggerHandler("getData"+bd[1]+"!",[bd[0]]);if(bb===G&&this.length){bb=a.data(this[0],ba);bb=aM(this[0],ba,bb)}return bb===G&&bd[1]?this.data(bd[0]):bb}else{return this.each(function(){var bf=a(this),be=[bd[0],bc];bf.triggerHandler("setData"+bd[1]+"!",be);a.data(this,ba,bc);bf.triggerHandler("changeData"+bd[1]+"!",be)})}},removeData:function(a6){return this.each(function(){a.removeData(this,a6)})}});function aM(a7,a6,a8){if(a8===G&&a7.nodeType===1){a8=a7.getAttribute("data-"+a6);if(typeof a8==="string"){try{a8=a8==="true"?true:a8==="false"?false:a8==="null"?null:!a.isNaN(a8)?parseFloat(a8):av.test(a8)?a.parseJSON(a8):a8}catch(a9){}a.data(a7,a6,a8)}else{a8=G}}return a8}a.extend({queue:function(a7,a6,a9){if(!a7){return}a6=(a6||"fx")+"queue";var a8=a._data(a7,a6);if(!a9){return a8||[]}if(!a8||a.isArray(a9)){a8=a._data(a7,a6,a.makeArray(a9))}else{a8.push(a9)}return a8},dequeue:function(a9,a8){a8=a8||"fx";var a6=a.queue(a9,a8),a7=a6.shift();if(a7==="inprogress"){a7=a6.shift()}if(a7){if(a8==="fx"){a6.unshift("inprogress")}a7.call(a9,function(){a.dequeue(a9,a8)})}if(!a6.length){a.removeData(a9,a8+"queue",true)}}});a.fn.extend({queue:function(a6,a7){if(typeof a6!=="string"){a7=a6;a6="fx"}if(a7===G){return a.queue(this[0],a6)}return this.each(function(a9){var a8=a.queue(this,a6,a7);if(a6==="fx"&&a8[0]!=="inprogress"){a.dequeue(this,a6)}})},dequeue:function(a6){return this.each(function(){a.dequeue(this,a6)})},delay:function(a7,a6){a7=a.fx?a.fx.speeds[a7]||a7:a7;a6=a6||"fx";return this.queue(a6,function(){var a8=this;setTimeout(function(){a.dequeue(a8,a6)},a7)})},clearQueue:function(a6){return this.queue(a6||"fx",[])}});var at=/[\\n\\t\\r]/g,aV=/\\s+/,ax=/\\r/g,aU=/^(?:href|src|style)$/,e=/^(?:button|input)$/i,B=/^(?:button|input|object|select|textarea)$/i,k=/^a(?:rea)?$/i,N=/^(?:radio|checkbox)$/i;a.props={"for":"htmlFor","class":"className",readonly:"readOnly",maxlength:"maxLength",cellspacing:"cellSpacing",rowspan:"rowSpan",colspan:"colSpan",tabindex:"tabIndex",usemap:"useMap",frameborder:"frameBorder"};a.fn.extend({attr:function(a6,a7){return a.access(this,a6,a7,true,a.attr)},removeAttr:function(a6,a7){return this.each(function(){a.attr(this,a6,"");if(this.nodeType===1){this.removeAttribute(a6)}})},addClass:function(bd){if(a.isFunction(bd)){return this.each(function(bg){var bf=a(this);bf.addClass(bd.call(this,bg,bf.attr("class")))})}if(bd&&typeof bd==="string"){var a6=(bd||"").split(aV);for(var a9=0,a8=this.length;a9<a8;a9++){var a7=this[a9];if(a7.nodeType===1){if(!a7.className){a7.className=bd}else{var ba=" "+a7.className+" ",bc=a7.className;for(var bb=0,be=a6.length;bb<be;bb++){if(ba.indexOf(" "+a6[bb]+" ")<0){bc+=" "+a6[bb]}}a7.className=a.trim(bc)}}}}return this},removeClass:function(bb){if(a.isFunction(bb)){return this.each(function(bf){var be=a(this);be.removeClass(bb.call(this,bf,be.attr("class")))})}if((bb&&typeof bb==="string")||bb===G){var bc=(bb||"").split(aV);for(var a8=0,a7=this.length;a8<a7;a8++){var ba=this[a8];if(ba.nodeType===1&&ba.className){if(bb){var a9=(" "+ba.className+" ").replace(at," ");for(var bd=0,a6=bc.length;bd<a6;bd++){a9=a9.replace(" "+bc[bd]+" "," ")}ba.className=a.trim(a9)}else{ba.className=""}}}}return this},toggleClass:function(a9,a7){var a8=typeof a9,a6=typeof a7==="boolean";if(a.isFunction(a9)){return this.each(function(bb){var ba=a(this);ba.toggleClass(a9.call(this,bb,ba.attr("class"),a7),a7)})}return this.each(function(){if(a8==="string"){var bc,bb=0,ba=a(this),bd=a7,be=a9.split(aV);while((bc=be[bb++])){bd=a6?bd:!ba.hasClass(bc);ba[bd?"addClass":"removeClass"](bc)}}else{if(a8==="undefined"||a8==="boolean"){if(this.className){a._data(this,"__className__",this.className)}this.className=this.className||a9===false?"":a._data(this,"__className__")||""}}})},hasClass:function(a6){var a9=" "+a6+" ";for(var a8=0,a7=this.length;a8<a7;a8++){if((" "+this[a8].className+" ").replace(at," ").indexOf(a9)>-1){return true}}return false},val:function(be){if(!arguments.length){var a8=this[0];if(a8){if(a.nodeName(a8,"option")){var a7=a8.attributes.value;return !a7||a7.specified?a8.value:a8.text}if(a.nodeName(a8,"select")){var bc=a8.selectedIndex,bf=[],bg=a8.options,bb=a8.type==="select-one";if(bc<0){return null}for(var a9=bb?bc:0,bd=bb?bc+1:bg.length;a9<bd;a9++){var ba=bg[a9];if(ba.selected&&(a.support.optDisabled?!ba.disabled:ba.getAttribute("disabled")===null)&&(!ba.parentNode.disabled||!a.nodeName(ba.parentNode,"optgroup"))){be=a(ba).val();if(bb){return be}bf.push(be)}}return bf}if(N.test(a8.type)&&!a.support.checkOn){return a8.getAttribute("value")===null?"on":a8.value}return(a8.value||"").replace(ax,"")}return G}var a6=a.isFunction(be);return this.each(function(bj){var bi=a(this),bk=be;if(this.nodeType!==1){return}if(a6){bk=be.call(this,bj,bi.val())}if(bk==null){bk=""}else{if(typeof bk==="number"){bk+=""}else{if(a.isArray(bk)){bk=a.map(bk,function(bl){return bl==null?"":bl+""})}}}if(a.isArray(bk)&&N.test(this.type)){this.checked=a.inArray(bi.val(),bk)>=0}else{if(a.nodeName(this,"select")){var bh=a.makeArray(bk);a("option",this).each(function(){this.selected=a.inArray(a(this).val(),bh)>=0});if(!bh.length){this.selectedIndex=-1}}else{this.value=bk}}})}});a.extend({attrFn:{val:true,css:true,html:true,text:true,data:true,width:true,height:true,offset:true},attr:function(a7,a6,bc,bf){if(!a7||a7.nodeType===3||a7.nodeType===8||a7.nodeType===2){return G}if(bf&&a6 in a.attrFn){return a(a7)[a6](bc)}var a8=a7.nodeType!==1||!a.isXMLDoc(a7),bb=bc!==G;a6=a8&&a.props[a6]||a6;if(a7.nodeType===1){var ba=aU.test(a6);if(a6==="selected"&&!a.support.optSelected){var bd=a7.parentNode;if(bd){bd.selectedIndex;if(bd.parentNode){bd.parentNode.selectedIndex}}}if((a6 in a7||a7[a6]!==G)&&a8&&!ba){if(bb){if(a6==="type"&&e.test(a7.nodeName)&&a7.parentNode){a.error("type property can\'t be changed")}if(bc===null){if(a7.nodeType===1){a7.removeAttribute(a6)}}else{a7[a6]=bc}}if(a.nodeName(a7,"form")&&a7.getAttributeNode(a6)){return a7.getAttributeNode(a6).nodeValue}if(a6==="tabIndex"){var be=a7.getAttributeNode("tabIndex");return be&&be.specified?be.value:B.test(a7.nodeName)||k.test(a7.nodeName)&&a7.href?0:G}return a7[a6]}if(!a.support.style&&a8&&a6==="style"){if(bb){a7.style.cssText=""+bc}return a7.style.cssText}if(bb){a7.setAttribute(a6,""+bc)}if(!a7.attributes[a6]&&(a7.hasAttribute&&!a7.hasAttribute(a6))){return G}var a9=!a.support.hrefNormalized&&a8&&ba?a7.getAttribute(a6,2):a7.getAttribute(a6);return a9===null?G:a9}if(bb){a7[a6]=bc}return a7[a6]}});var aI=/\\.(.*)$/,aT=/^(?:textarea|input|select)$/i,I=/\\./g,W=/ /g,ao=/[^\\w\\s.|`]/g,D=function(a6){return a6.replace(ao,"\\\\$&")},aA="events";a.event={add:function(a9,bd,bi,bb){if(a9.nodeType===3||a9.nodeType===8){return}if(a.isWindow(a9)&&(a9!==aR&&!a9.frameElement)){a9=aR}if(bi===false){bi=aX}else{if(!bi){return}}var a7,bh;if(bi.handler){a7=bi;bi=a7.handler}if(!bi.guid){bi.guid=a.guid++}var be=a._data(a9);if(!be){return}var bj=be[aA],bc=be.handle;if(typeof bj==="function"){bc=bj.handle;bj=bj.events}else{if(!bj){if(!a9.nodeType){be[aA]=be=function(){}}be.events=bj={}}}if(!bc){be.handle=bc=function(){return typeof a!=="undefined"&&!a.event.triggered?a.event.handle.apply(bc.elem,arguments):G}}bc.elem=a9;bd=bd.split(" ");var bg,ba=0,a6;while((bg=bd[ba++])){bh=a7?a.extend({},a7):{handler:bi,data:bb};if(bg.indexOf(".")>-1){a6=bg.split(".");bg=a6.shift();bh.namespace=a6.slice(0).sort().join(".")}else{a6=[];bh.namespace=""}bh.type=bg;if(!bh.guid){bh.guid=bi.guid}var a8=bj[bg],bf=a.event.special[bg]||{};if(!a8){a8=bj[bg]=[];if(!bf.setup||bf.setup.call(a9,bb,a6,bc)===false){if(a9.addEventListener){a9.addEventListener(bg,bc,false)}else{if(a9.attachEvent){a9.attachEvent("on"+bg,bc)}}}}if(bf.add){bf.add.call(a9,bh);if(!bh.handler.guid){bh.handler.guid=bi.guid}}a8.push(bh);a.event.global[bg]=true}a9=null},global:{},remove:function(bl,bg,a8,bc){if(bl.nodeType===3||bl.nodeType===8){return}if(a8===false){a8=aX}var bo,bb,bd,bi,bj=0,a9,be,bh,ba,bf,a6,bn,bk=a.hasData(bl)&&a._data(bl),a7=bk&&bk[aA];if(!bk||!a7){return}if(typeof a7==="function"){bk=a7;a7=a7.events}if(bg&&bg.type){a8=bg.handler;bg=bg.type}if(!bg||typeof bg==="string"&&bg.charAt(0)==="."){bg=bg||"";for(bb in a7){a.event.remove(bl,bb+bg)}return}bg=bg.split(" ");while((bb=bg[bj++])){bn=bb;a6=null;a9=bb.indexOf(".")<0;be=[];if(!a9){be=bb.split(".");bb=be.shift();bh=new RegExp("(^|\\\\.)"+a.map(be.slice(0).sort(),D).join("\\\\.(?:.*\\\\.)?")+"(\\\\.|$)")}bf=a7[bb];if(!bf){continue}if(!a8){for(bi=0;bi<bf.length;bi++){a6=bf[bi];if(a9||bh.test(a6.namespace)){a.event.remove(bl,bn,a6.handler,bi);bf.splice(bi--,1)}}continue}ba=a.event.special[bb]||{};for(bi=bc||0;bi<bf.length;bi++){a6=bf[bi];if(a8.guid===a6.guid){if(a9||bh.test(a6.namespace)){if(bc==null){bf.splice(bi--,1)}if(ba.remove){ba.remove.call(bl,a6)}}if(bc!=null){break}}}if(bf.length===0||bc!=null&&bf.length===1){if(!ba.teardown||ba.teardown.call(bl,be)===false){a.removeEvent(bl,bb,bk.handle)}bo=null;delete a7[bb]}}if(a.isEmptyObject(a7)){var bm=bk.handle;if(bm){bm.elem=null}delete bk.events;delete bk.handle;if(typeof bk==="function"){a.removeData(bl,aA,true)}else{if(a.isEmptyObject(bk)){a.removeData(bl,G,true)}}}},trigger:function(a7,bc,a9){var bg=a7.type||a7,bb=arguments[3];if(!bb){a7=typeof a7==="object"?a7[a.expando]?a7:a.extend(a.Event(bg),a7):a.Event(bg);if(bg.indexOf("!")>=0){a7.type=bg=bg.slice(0,-1);a7.exclusive=true}if(!a9){a7.stopPropagation();if(a.event.global[bg]){a.each(a.cache,function(){var bl=a.expando,bk=this[bl];if(bk&&bk.events&&bk.events[bg]){a.event.trigger(a7,bc,bk.handle.elem)}})}}if(!a9||a9.nodeType===3||a9.nodeType===8){return G}a7.result=G;a7.target=a9;bc=a.makeArray(bc);bc.unshift(a7)}a7.currentTarget=a9;var bd=a9.nodeType?a._data(a9,"handle"):(a._data(a9,aA)||{}).handle;if(bd){bd.apply(a9,bc)}var bi=a9.parentNode||a9.ownerDocument;try{if(!(a9&&a9.nodeName&&a.noData[a9.nodeName.toLowerCase()])){if(a9["on"+bg]&&a9["on"+bg].apply(a9,bc)===false){a7.result=false;a7.preventDefault()}}}catch(bh){}if(!a7.isPropagationStopped()&&bi){a.event.trigger(a7,bc,bi,true)}else{if(!a7.isDefaultPrevented()){var a8,be=a7.target,a6=bg.replace(aI,""),bj=a.nodeName(be,"a")&&a6==="click",bf=a.event.special[a6]||{};if((!bf._default||bf._default.call(a9,a7)===false)&&!bj&&!(be&&be.nodeName&&a.noData[be.nodeName.toLowerCase()])){try{if(be[a6]){a8=be["on"+a6];if(a8){be["on"+a6]=null}a.event.triggered=true;be[a6]()}}catch(ba){}if(a8){be["on"+a6]=a8}a.event.triggered=false}}}},handle:function(a6){var bf,a8,a7,bh,bg,bb=[],bd=a.makeArray(arguments);a6=bd[0]=a.event.fix(a6||aR.event);a6.currentTarget=this;bf=a6.type.indexOf(".")<0&&!a6.exclusive;if(!bf){a7=a6.type.split(".");a6.type=a7.shift();bb=a7.slice(0).sort();bh=new RegExp("(^|\\\\.)"+bb.join("\\\\.(?:.*\\\\.)?")+"(\\\\.|$)")}a6.namespace=a6.namespace||bb.join(".");bg=a._data(this,aA);if(typeof bg==="function"){bg=bg.events}a8=(bg||{})[a6.type];if(bg&&a8){a8=a8.slice(0);for(var ba=0,a9=a8.length;ba<a9;ba++){var be=a8[ba];if(bf||bh.test(be.namespace)){a6.handler=be.handler;a6.data=be.data;a6.handleObj=be;var bc=be.handler.apply(this,bd);if(bc!==G){a6.result=bc;if(bc===false){a6.preventDefault();a6.stopPropagation()}}if(a6.isImmediatePropagationStopped()){break}}}}return a6.result},props:"altKey attrChange attrName bubbles button cancelable charCode clientX clientY ctrlKey currentTarget data detail eventPhase fromElement handler keyCode layerX layerY metaKey newValue offsetX offsetY pageX pageY prevValue relatedNode relatedTarget screenX screenY shiftKey srcElement target toElement view wheelDelta which".split(" "),fix:function(a9){if(a9[a.expando]){return a9}var a7=a9;a9=a.Event(a7);for(var a8=this.props.length,bb;a8;){bb=this.props[--a8];a9[bb]=a7[bb]}if(!a9.target){a9.target=a9.srcElement||ag}if(a9.target.nodeType===3){a9.target=a9.target.parentNode}if(!a9.relatedTarget&&a9.fromElement){a9.relatedTarget=a9.fromElement===a9.target?a9.toElement:a9.fromElement}if(a9.pageX==null&&a9.clientX!=null){var ba=ag.documentElement,a6=ag.body;a9.pageX=a9.clientX+(ba&&ba.scrollLeft||a6&&a6.scrollLeft||0)-(ba&&ba.clientLeft||a6&&a6.clientLeft||0);a9.pageY=a9.clientY+(ba&&ba.scrollTop||a6&&a6.scrollTop||0)-(ba&&ba.clientTop||a6&&a6.clientTop||0)}if(a9.which==null&&(a9.charCode!=null||a9.keyCode!=null)){a9.which=a9.charCode!=null?a9.charCode:a9.keyCode}if(!a9.metaKey&&a9.ctrlKey){a9.metaKey=a9.ctrlKey}if(!a9.which&&a9.button!==G){a9.which=(a9.button&1?1:(a9.button&2?3:(a9.button&4?2:0)))}return a9},guid:100000000,proxy:a.proxy,special:{ready:{setup:a.bindReady,teardown:a.noop},live:{add:function(a6){a.event.add(this,o(a6.origType,a6.selector),a.extend({},a6,{handler:aa,guid:a6.handler.guid}))},remove:function(a6){a.event.remove(this,o(a6.origType,a6.selector),a6)}},beforeunload:{setup:function(a8,a7,a6){if(a.isWindow(this)){this.onbeforeunload=a6}},teardown:function(a7,a6){if(this.onbeforeunload===a6){this.onbeforeunload=null}}}}};a.removeEvent=ag.removeEventListener?function(a7,a6,a8){if(a7.removeEventListener){a7.removeEventListener(a6,a8,false)}}:function(a7,a6,a8){if(a7.detachEvent){a7.detachEvent("on"+a6,a8)}};a.Event=function(a6){if(!this.preventDefault){return new a.Event(a6)}if(a6&&a6.type){this.originalEvent=a6;this.type=a6.type;this.isDefaultPrevented=(a6.defaultPrevented||a6.returnValue===false||a6.getPreventDefault&&a6.getPreventDefault())?g:aX}else{this.type=a6}this.timeStamp=a.now();this[a.expando]=true};function aX(){return false}function g(){return true}a.Event.prototype={preventDefault:function(){this.isDefaultPrevented=g;var a6=this.originalEvent;if(!a6){return}if(a6.preventDefault){a6.preventDefault()}else{a6.returnValue=false}},stopPropagation:function(){this.isPropagationStopped=g;var a6=this.originalEvent;if(!a6){return}if(a6.stopPropagation){a6.stopPropagation()}a6.cancelBubble=true},stopImmediatePropagation:function(){this.isImmediatePropagationStopped=g;this.stopPropagation()},isDefaultPrevented:aX,isPropagationStopped:aX,isImmediatePropagationStopped:aX};var V=function(a7){var a6=a7.relatedTarget;try{while(a6&&a6!==this){a6=a6.parentNode}if(a6!==this){a7.type=a7.data;a.event.handle.apply(this,arguments)}}catch(a8){}},aB=function(a6){a6.type=a6.data;a.event.handle.apply(this,arguments)};a.each({mouseenter:"mouseover",mouseleave:"mouseout"},function(a7,a6){a.event.special[a7]={setup:function(a8){a.event.add(this,a6,a8&&a8.selector?aB:V,a7)},teardown:function(a8){a.event.remove(this,a6,a8&&a8.selector?aB:V)}}});if(!a.support.submitBubbles){a.event.special.submit={setup:function(a7,a6){if(this.nodeName&&this.nodeName.toLowerCase()!=="form"){a.event.add(this,"click.specialSubmit",function(ba){var a9=ba.target,a8=a9.type;if((a8==="submit"||a8==="image")&&a(a9).closest("form").length){ba.liveFired=G;return aF("submit",this,arguments)}});a.event.add(this,"keypress.specialSubmit",function(ba){var a9=ba.target,a8=a9.type;if((a8==="text"||a8==="password")&&a(a9).closest("form").length&&ba.keyCode===13){ba.liveFired=G;return aF("submit",this,arguments)}})}else{return false}},teardown:function(a6){a.event.remove(this,".specialSubmit")}}}if(!a.support.changeBubbles){var aY,j=function(a7){var a6=a7.type,a8=a7.value;if(a6==="radio"||a6==="checkbox"){a8=a7.checked}else{if(a6==="select-multiple"){a8=a7.selectedIndex>-1?a.map(a7.options,function(a9){return a9.selected}).join("-"):""}else{if(a7.nodeName.toLowerCase()==="select"){a8=a7.selectedIndex}}}return a8},T=function T(a8){var a6=a8.target,a7,a9;if(!aT.test(a6.nodeName)||a6.readOnly){return}a7=a._data(a6,"_change_data");a9=j(a6);if(a8.type!=="focusout"||a6.type!=="radio"){a._data(a6,"_change_data",a9)}if(a7===G||a9===a7){return}if(a7!=null||a9){a8.type="change";a8.liveFired=G;return a.event.trigger(a8,arguments[1],a6)}};a.event.special.change={filters:{focusout:T,beforedeactivate:T,click:function(a8){var a7=a8.target,a6=a7.type;if(a6==="radio"||a6==="checkbox"||a7.nodeName.toLowerCase()==="select"){return T.call(this,a8)}},keydown:function(a8){var a7=a8.target,a6=a7.type;if((a8.keyCode===13&&a7.nodeName.toLowerCase()!=="textarea")||(a8.keyCode===32&&(a6==="checkbox"||a6==="radio"))||a6==="select-multiple"){return T.call(this,a8)}},beforeactivate:function(a7){var a6=a7.target;a._data(a6,"_change_data",j(a6))}},setup:function(a8,a7){if(this.type==="file"){return false}for(var a6 in aY){a.event.add(this,a6+".specialChange",aY[a6])}return aT.test(this.nodeName)},teardown:function(a6){a.event.remove(this,".specialChange");return aT.test(this.nodeName)}};aY=a.event.special.change.filters;aY.focus=aY.beforeactivate}function aF(a7,a8,a6){a6[0].type=a7;return a.event.handle.apply(a8,a6)}if(ag.addEventListener){a.each({focus:"focusin",blur:"focusout"},function(a8,a6){a.event.special[a6]={setup:function(){this.addEventListener(a8,a7,true)},teardown:function(){this.removeEventListener(a8,a7,true)}};function a7(a9){a9=a.event.fix(a9);a9.type=a6;return a.event.handle.call(this,a9)}})}a.each(["bind","one"],function(a7,a6){a.fn[a6]=function(bd,be,bc){if(typeof bd==="object"){for(var ba in bd){this[a6](ba,be,bd[ba],bc)}return this}if(a.isFunction(be)||be===false){bc=be;be=G}var bb=a6==="one"?a.proxy(bc,function(bf){a(this).unbind(bf,bb);return bc.apply(this,arguments)}):bc;if(bd==="unload"&&a6!=="one"){this.one(bd,be,bc)}else{for(var a9=0,a8=this.length;a9<a8;a9++){a.event.add(this[a9],bd,bb,be)}}return this}});a.fn.extend({unbind:function(ba,a9){if(typeof ba==="object"&&!ba.preventDefault){for(var a8 in ba){this.unbind(a8,ba[a8])}}else{for(var a7=0,a6=this.length;a7<a6;a7++){a.event.remove(this[a7],ba,a9)}}return this},delegate:function(a6,a7,a9,a8){return this.live(a7,a9,a8,a6)},undelegate:function(a6,a7,a8){if(arguments.length===0){return this.unbind("live")}else{return this.die(a7,null,a8,a6)}},trigger:function(a6,a7){return this.each(function(){a.event.trigger(a6,a7,this)})},triggerHandler:function(a6,a8){if(this[0]){var a7=a.Event(a6);a7.preventDefault();a7.stopPropagation();a.event.trigger(a7,a8,this[0]);return a7.result}},toggle:function(a8){var a6=arguments,a7=1;while(a7<a6.length){a.proxy(a8,a6[a7++])}return this.click(a.proxy(a8,function(a9){var ba=(a._data(this,"lastToggle"+a8.guid)||0)%a7;a._data(this,"lastToggle"+a8.guid,ba+1);a9.preventDefault();return a6[ba].apply(this,arguments)||false}))},hover:function(a6,a7){return this.mouseenter(a6).mouseleave(a7||a6)}});var ay={focus:"focusin",blur:"focusout",mouseenter:"mouseover",mouseleave:"mouseout"};a.each(["live","die"],function(a7,a6){a.fn[a6]=function(bh,be,bj,ba){var bi,bf=0,bg,a9,bl,bc=ba||this.selector,a8=ba?this:a(this.context);if(typeof bh==="object"&&!bh.preventDefault){for(var bk in bh){a8[a6](bk,be,bh[bk],bc)}return this}if(a.isFunction(be)){bj=be;be=G}bh=(bh||"").split(" ");while((bi=bh[bf++])!=null){bg=aI.exec(bi);a9="";if(bg){a9=bg[0];bi=bi.replace(aI,"")}if(bi==="hover"){bh.push("mouseenter"+a9,"mouseleave"+a9);continue}bl=bi;if(bi==="focus"||bi==="blur"){bh.push(ay[bi]+a9);bi=bi+a9}else{bi=(ay[bi]||bi)+a9}if(a6==="live"){for(var bd=0,bb=a8.length;bd<bb;bd++){a.event.add(a8[bd],"live."+o(bi,bc),{data:be,selector:bc,handler:bj,origType:bi,origHandler:bj,preType:bl})}}else{a8.unbind("live."+o(bi,bc),bj)}}return this}});function aa(bh){var be,a9,bn,bb,a6,bj,bg,bi,bf,bm,bd,bc,bl,bk=[],ba=[],a7=a._data(this,aA);if(typeof a7==="function"){a7=a7.events}if(bh.liveFired===this||!a7||!a7.live||bh.target.disabled||bh.button&&bh.type==="click"){return}if(bh.namespace){bc=new RegExp("(^|\\\\.)"+bh.namespace.split(".").join("\\\\.(?:.*\\\\.)?")+"(\\\\.|$)")}bh.liveFired=this;var a8=a7.live.slice(0);for(bg=0;bg<a8.length;bg++){a6=a8[bg];if(a6.origType.replace(aI,"")===bh.type){ba.push(a6.selector)}else{a8.splice(bg--,1)}}bb=a(bh.target).closest(ba,bh.currentTarget);for(bi=0,bf=bb.length;bi<bf;bi++){bd=bb[bi];for(bg=0;bg<a8.length;bg++){a6=a8[bg];if(bd.selector===a6.selector&&(!bc||bc.test(a6.namespace))){bj=bd.elem;bn=null;if(a6.preType==="mouseenter"||a6.preType==="mouseleave"){bh.type=a6.preType;bn=a(bh.relatedTarget).closest(a6.selector)[0]}if(!bn||bn!==bj){bk.push({elem:bj,handleObj:a6,level:bd.level})}}}}for(bi=0,bf=bk.length;bi<bf;bi++){bb=bk[bi];if(a9&&bb.level>a9){break}bh.currentTarget=bb.elem;bh.data=bb.handleObj.data;bh.handleObj=bb.handleObj;bl=bb.handleObj.origHandler.apply(bb.elem,arguments);if(bl===false||bh.isPropagationStopped()){a9=bb.level;if(bl===false){be=false}if(bh.isImmediatePropagationStopped()){break}}}return be}function o(a7,a6){return(a7&&a7!=="*"?a7+".":"")+a6.replace(I,"`").replace(W,"&")}a.each(("blur focus focusin focusout load resize scroll unload click dblclick mousedown mouseup mousemove mouseover mouseout mouseenter mouseleave change select submit keydown keypress keyup error").split(" "),function(a7,a6){a.fn[a6]=function(a9,a8){if(a8==null){a8=a9;a9=null}return arguments.length>0?this.bind(a6,a9,a8):this.trigger(a6)};if(a.attrFn){a.attrFn[a6]=true}});\n/*\n * Sizzle CSS Selector Engine\n *  Copyright 2011, The Dojo Foundation\n *  Released under the MIT, BSD, and GPL Licenses.\n *  More information: http://sizzlejs.com/\n */\n(function(){var bl=/((?:\\((?:\\([^()]+\\)|[^()]+)+\\)|\\[(?:\\[[^\\[\\]]*\\]|[\'"][^\'"]*[\'"]|[^\\[\\]\'"]+)+\\]|\\\\.|[^ >+~,(\\[\\\\]+)+|[>+~])(\\s*,\\s*)?((?:.|\\r|\\n)*)/g,be=0,a9=Object.prototype.toString,bk=false,bd=true;[0,0].sort(function(){bd=false;return 0});var a7=function(bs,bn,bv,bw){bv=bv||[];bn=bn||ag;var by=bn;if(bn.nodeType!==1&&bn.nodeType!==9){return[]}if(!bs||typeof bs!=="string"){return bv}var bp,bA,bD,bo,bz,bC,bB,bu,br=true,bq=a7.isXML(bn),bt=[],bx=bs;do{bl.exec("");bp=bl.exec(bx);if(bp){bx=bp[3];bt.push(bp[1]);if(bp[2]){bo=bp[3];break}}}while(bp);if(bt.length>1&&bf.exec(bs)){if(bt.length===2&&ba.relative[bt[0]]){bA=bc(bt[0]+bt[1],bn)}else{bA=ba.relative[bt[0]]?[bn]:a7(bt.shift(),bn);while(bt.length){bs=bt.shift();if(ba.relative[bs]){bs+=bt.shift()}bA=bc(bs,bA)}}}else{if(!bw&&bt.length>1&&bn.nodeType===9&&!bq&&ba.match.ID.test(bt[0])&&!ba.match.ID.test(bt[bt.length-1])){bz=a7.find(bt.shift(),bn,bq);bn=bz.expr?a7.filter(bz.expr,bz.set)[0]:bz.set[0]}if(bn){bz=bw?{expr:bt.pop(),set:a6(bw)}:a7.find(bt.pop(),bt.length===1&&(bt[0]==="~"||bt[0]==="+")&&bn.parentNode?bn.parentNode:bn,bq);bA=bz.expr?a7.filter(bz.expr,bz.set):bz.set;if(bt.length>0){bD=a6(bA)}else{br=false}while(bt.length){bC=bt.pop();bB=bC;if(!ba.relative[bC]){bC=""}else{bB=bt.pop()}if(bB==null){bB=bn}ba.relative[bC](bD,bB,bq)}}else{bD=bt=[]}}if(!bD){bD=bA}if(!bD){a7.error(bC||bs)}if(a9.call(bD)==="[object Array]"){if(!br){bv.push.apply(bv,bD)}else{if(bn&&bn.nodeType===1){for(bu=0;bD[bu]!=null;bu++){if(bD[bu]&&(bD[bu]===true||bD[bu].nodeType===1&&a7.contains(bn,bD[bu]))){bv.push(bA[bu])}}}else{for(bu=0;bD[bu]!=null;bu++){if(bD[bu]&&bD[bu].nodeType===1){bv.push(bA[bu])}}}}}else{a6(bD,bv)}if(bo){a7(bo,by,bv,bw);a7.uniqueSort(bv)}return bv};a7.uniqueSort=function(bo){if(a8){bk=bd;bo.sort(a8);if(bk){for(var bn=1;bn<bo.length;bn++){if(bo[bn]===bo[bn-1]){bo.splice(bn--,1)}}}}return bo};a7.matches=function(bn,bo){return a7(bn,null,null,bo)};a7.matchesSelector=function(bn,bo){return a7(bo,null,null,[bn]).length>0};a7.find=function(bu,bn,bv){var bt;if(!bu){return[]}for(var bq=0,bp=ba.order.length;bq<bp;bq++){var br,bs=ba.order[bq];if((br=ba.leftMatch[bs].exec(bu))){var bo=br[1];br.splice(1,1);if(bo.substr(bo.length-1)!=="\\\\"){br[1]=(br[1]||"").replace(/\\\\/g,"");bt=ba.find[bs](br,bn,bv);if(bt!=null){bu=bu.replace(ba.match[bs],"");break}}}}if(!bt){bt=typeof bn.getElementsByTagName!=="undefined"?bn.getElementsByTagName("*"):[]}return{set:bt,expr:bu}};a7.filter=function(by,bx,bB,br){var bt,bn,bp=by,bD=[],bv=bx,bu=bx&&bx[0]&&a7.isXML(bx[0]);while(by&&bx.length){for(var bw in ba.filter){if((bt=ba.leftMatch[bw].exec(by))!=null&&bt[2]){var bC,bA,bo=ba.filter[bw],bq=bt[1];bn=false;bt.splice(1,1);if(bq.substr(bq.length-1)==="\\\\"){continue}if(bv===bD){bD=[]}if(ba.preFilter[bw]){bt=ba.preFilter[bw](bt,bv,bB,bD,br,bu);if(!bt){bn=bC=true}else{if(bt===true){continue}}}if(bt){for(var bs=0;(bA=bv[bs])!=null;bs++){if(bA){bC=bo(bA,bt,bs,bv);var bz=br^!!bC;if(bB&&bC!=null){if(bz){bn=true}else{bv[bs]=false}}else{if(bz){bD.push(bA);bn=true}}}}}if(bC!==G){if(!bB){bv=bD}by=by.replace(ba.match[bw],"");if(!bn){return[]}break}}}if(by===bp){if(bn==null){a7.error(by)}else{break}}bp=by}return bv};a7.error=function(bn){throw"Syntax error, unrecognized expression: "+bn};var ba=a7.selectors={order:["ID","NAME","TAG"],match:{ID:/#((?:[\\w\\u00c0-\\uFFFF\\-]|\\\\.)+)/,CLASS:/\\.((?:[\\w\\u00c0-\\uFFFF\\-]|\\\\.)+)/,NAME:/\\[name=[\'"]*((?:[\\w\\u00c0-\\uFFFF\\-]|\\\\.)+)[\'"]*\\]/,ATTR:/\\[\\s*((?:[\\w\\u00c0-\\uFFFF\\-]|\\\\.)+)\\s*(?:(\\S?=)\\s*(?:([\'"])(.*?)\\3|(#?(?:[\\w\\u00c0-\\uFFFF\\-]|\\\\.)*)|)|)\\s*\\]/,TAG:/^((?:[\\w\\u00c0-\\uFFFF\\*\\-]|\\\\.)+)/,CHILD:/:(only|nth|last|first)-child(?:\\(\\s*(even|odd|(?:[+\\-]?\\d+|(?:[+\\-]?\\d*)?n\\s*(?:[+\\-]\\s*\\d+)?))\\s*\\))?/,POS:/:(nth|eq|gt|lt|first|last|even|odd)(?:\\((\\d*)\\))?(?=[^\\-]|$)/,PSEUDO:/:((?:[\\w\\u00c0-\\uFFFF\\-]|\\\\.)+)(?:\\(([\'"]?)((?:\\([^\\)]+\\)|[^\\(\\)]*)+)\\2\\))?/},leftMatch:{},attrMap:{"class":"className","for":"htmlFor"},attrHandle:{href:function(bn){return bn.getAttribute("href")}},relative:{"+":function(bt,bo){var bq=typeof bo==="string",bs=bq&&!/\\W/.test(bo),bu=bq&&!bs;if(bs){bo=bo.toLowerCase()}for(var bp=0,bn=bt.length,br;bp<bn;bp++){if((br=bt[bp])){while((br=br.previousSibling)&&br.nodeType!==1){}bt[bp]=bu||br&&br.nodeName.toLowerCase()===bo?br||false:br===bo}}if(bu){a7.filter(bo,bt,true)}},">":function(bt,bo){var bs,br=typeof bo==="string",bp=0,bn=bt.length;if(br&&!/\\W/.test(bo)){bo=bo.toLowerCase();for(;bp<bn;bp++){bs=bt[bp];if(bs){var bq=bs.parentNode;bt[bp]=bq.nodeName.toLowerCase()===bo?bq:false}}}else{for(;bp<bn;bp++){bs=bt[bp];if(bs){bt[bp]=br?bs.parentNode:bs.parentNode===bo}}if(br){a7.filter(bo,bt,true)}}},"":function(bq,bo,bs){var br,bp=be++,bn=bm;if(typeof bo==="string"&&!/\\W/.test(bo)){bo=bo.toLowerCase();br=bo;bn=bj}bn("parentNode",bo,bp,bq,br,bs)},"~":function(bq,bo,bs){var br,bp=be++,bn=bm;if(typeof bo==="string"&&!/\\W/.test(bo)){bo=bo.toLowerCase();br=bo;bn=bj}bn("previousSibling",bo,bp,bq,br,bs)}},find:{ID:function(bo,bp,bq){if(typeof bp.getElementById!=="undefined"&&!bq){var bn=bp.getElementById(bo[1]);return bn&&bn.parentNode?[bn]:[]}},NAME:function(bp,bs){if(typeof bs.getElementsByName!=="undefined"){var bo=[],br=bs.getElementsByName(bp[1]);for(var bq=0,bn=br.length;bq<bn;bq++){if(br[bq].getAttribute("name")===bp[1]){bo.push(br[bq])}}return bo.length===0?null:bo}},TAG:function(bn,bo){if(typeof bo.getElementsByTagName!=="undefined"){return bo.getElementsByTagName(bn[1])}}},preFilter:{CLASS:function(bq,bo,bp,bn,bt,bu){bq=" "+bq[1].replace(/\\\\/g,"")+" ";if(bu){return bq}for(var br=0,bs;(bs=bo[br])!=null;br++){if(bs){if(bt^(bs.className&&(" "+bs.className+" ").replace(/[\\t\\n\\r]/g," ").indexOf(bq)>=0)){if(!bp){bn.push(bs)}}else{if(bp){bo[br]=false}}}}return false},ID:function(bn){return bn[1].replace(/\\\\/g,"")},TAG:function(bo,bn){return bo[1].toLowerCase()},CHILD:function(bn){if(bn[1]==="nth"){if(!bn[2]){a7.error(bn[0])}bn[2]=bn[2].replace(/^\\+|\\s*/g,"");var bo=/(-?)(\\d*)(?:n([+\\-]?\\d*))?/.exec(bn[2]==="even"&&"2n"||bn[2]==="odd"&&"2n+1"||!/\\D/.test(bn[2])&&"0n+"+bn[2]||bn[2]);bn[2]=(bo[1]+(bo[2]||1))-0;bn[3]=bo[3]-0}else{if(bn[2]){a7.error(bn[0])}}bn[0]=be++;return bn},ATTR:function(br,bo,bp,bn,bs,bt){var bq=br[1]=br[1].replace(/\\\\/g,"");if(!bt&&ba.attrMap[bq]){br[1]=ba.attrMap[bq]}br[4]=(br[4]||br[5]||"").replace(/\\\\/g,"");if(br[2]==="~="){br[4]=" "+br[4]+" "}return br},PSEUDO:function(br,bo,bp,bn,bs){if(br[1]==="not"){if((bl.exec(br[3])||"").length>1||/^\\w/.test(br[3])){br[3]=a7(br[3],null,null,bo)}else{var bq=a7.filter(br[3],bo,bp,true^bs);if(!bp){bn.push.apply(bn,bq)}return false}}else{if(ba.match.POS.test(br[0])||ba.match.CHILD.test(br[0])){return true}}return br},POS:function(bn){bn.unshift(true);return bn}},filters:{enabled:function(bn){return bn.disabled===false&&bn.type!=="hidden"},disabled:function(bn){return bn.disabled===true},checked:function(bn){return bn.checked===true},selected:function(bn){bn.parentNode.selectedIndex;return bn.selected===true},parent:function(bn){return !!bn.firstChild},empty:function(bn){return !bn.firstChild},has:function(bp,bo,bn){return !!a7(bn[3],bp).length},header:function(bn){return(/h\\d/i).test(bn.nodeName)},text:function(bn){return"text"===bn.type},radio:function(bn){return"radio"===bn.type},checkbox:function(bn){return"checkbox"===bn.type},file:function(bn){return"file"===bn.type},password:function(bn){return"password"===bn.type},submit:function(bn){return"submit"===bn.type},image:function(bn){return"image"===bn.type},reset:function(bn){return"reset"===bn.type},button:function(bn){return"button"===bn.type||bn.nodeName.toLowerCase()==="button"},input:function(bn){return(/input|select|textarea|button/i).test(bn.nodeName)}},setFilters:{first:function(bo,bn){return bn===0},last:function(bp,bo,bn,bq){return bo===bq.length-1},even:function(bo,bn){return bn%2===0},odd:function(bo,bn){return bn%2===1},lt:function(bp,bo,bn){return bo<bn[3]-0},gt:function(bp,bo,bn){return bo>bn[3]-0},nth:function(bp,bo,bn){return bn[3]-0===bo},eq:function(bp,bo,bn){return bn[3]-0===bo}},filter:{PSEUDO:function(bp,bu,bt,bv){var bn=bu[1],bo=ba.filters[bn];if(bo){return bo(bp,bt,bu,bv)}else{if(bn==="contains"){return(bp.textContent||bp.innerText||a7.getText([bp])||"").indexOf(bu[3])>=0}else{if(bn==="not"){var bq=bu[3];for(var bs=0,br=bq.length;bs<br;bs++){if(bq[bs]===bp){return false}}return true}else{a7.error(bn)}}}},CHILD:function(bn,bq){var bt=bq[1],bo=bn;switch(bt){case"only":case"first":while((bo=bo.previousSibling)){if(bo.nodeType===1){return false}}if(bt==="first"){return true}bo=bn;case"last":while((bo=bo.nextSibling)){if(bo.nodeType===1){return false}}return true;case"nth":var bp=bq[2],bw=bq[3];if(bp===1&&bw===0){return true}var bs=bq[0],bv=bn.parentNode;if(bv&&(bv.sizcache!==bs||!bn.nodeIndex)){var br=0;for(bo=bv.firstChild;bo;bo=bo.nextSibling){if(bo.nodeType===1){bo.nodeIndex=++br}}bv.sizcache=bs}var bu=bn.nodeIndex-bw;if(bp===0){return bu===0}else{return(bu%bp===0&&bu/bp>=0)}}},ID:function(bo,bn){return bo.nodeType===1&&bo.getAttribute("id")===bn},TAG:function(bo,bn){return(bn==="*"&&bo.nodeType===1)||bo.nodeName.toLowerCase()===bn},CLASS:function(bo,bn){return(" "+(bo.className||bo.getAttribute("class"))+" ").indexOf(bn)>-1},ATTR:function(bs,bq){var bp=bq[1],bn=ba.attrHandle[bp]?ba.attrHandle[bp](bs):bs[bp]!=null?bs[bp]:bs.getAttribute(bp),bt=bn+"",br=bq[2],bo=bq[4];return bn==null?br==="!=":br==="="?bt===bo:br==="*="?bt.indexOf(bo)>=0:br==="~="?(" "+bt+" ").indexOf(bo)>=0:!bo?bt&&bn!==false:br==="!="?bt!==bo:br==="^="?bt.indexOf(bo)===0:br==="$="?bt.substr(bt.length-bo.length)===bo:br==="|="?bt===bo||bt.substr(0,bo.length+1)===bo+"-":false},POS:function(br,bo,bp,bs){var bn=bo[2],bq=ba.setFilters[bn];if(bq){return bq(br,bp,bo,bs)}}}};var bf=ba.match.POS,bb=function(bo,bn){return"\\\\"+(bn-0+1)};for(var bi in ba.match){ba.match[bi]=new RegExp(ba.match[bi].source+(/(?![^\\[]*\\])(?![^\\(]*\\))/.source));ba.leftMatch[bi]=new RegExp(/(^(?:.|\\r|\\n)*?)/.source+ba.match[bi].source.replace(/\\\\(\\d+)/g,bb))}var a6=function(bo,bn){bo=Array.prototype.slice.call(bo,0);if(bn){bn.push.apply(bn,bo);return bn}return bo};try{Array.prototype.slice.call(ag.documentElement.childNodes,0)[0].nodeType}catch(bg){a6=function(br,bq){var bp=0,bo=bq||[];if(a9.call(br)==="[object Array]"){Array.prototype.push.apply(bo,br)}else{if(typeof br.length==="number"){for(var bn=br.length;bp<bn;bp++){bo.push(br[bp])}}else{for(;br[bp];bp++){bo.push(br[bp])}}}return bo}}var a8,bh;if(ag.documentElement.compareDocumentPosition){a8=function(bo,bn){if(bo===bn){bk=true;return 0}if(!bo.compareDocumentPosition||!bn.compareDocumentPosition){return bo.compareDocumentPosition?-1:1}return bo.compareDocumentPosition(bn)&4?-1:1}}else{a8=function(bw,bv){var bt,bo,bq=[],bn=[],bs=bw.parentNode,bu=bv.parentNode,bx=bs;if(bw===bv){bk=true;return 0}else{if(bs===bu){return bh(bw,bv)}else{if(!bs){return -1}else{if(!bu){return 1}}}}while(bx){bq.unshift(bx);bx=bx.parentNode}bx=bu;while(bx){bn.unshift(bx);bx=bx.parentNode}bt=bq.length;bo=bn.length;for(var br=0;br<bt&&br<bo;br++){if(bq[br]!==bn[br]){return bh(bq[br],bn[br])}}return br===bt?bh(bw,bn[br],-1):bh(bq[br],bv,1)};bh=function(bo,bn,bp){if(bo===bn){return bp}var bq=bo.nextSibling;while(bq){if(bq===bn){return -1}bq=bq.nextSibling}return 1}}a7.getText=function(bn){var bo="",bq;for(var bp=0;bn[bp];bp++){bq=bn[bp];if(bq.nodeType===3||bq.nodeType===4){bo+=bq.nodeValue}else{if(bq.nodeType!==8){bo+=a7.getText(bq.childNodes)}}}return bo};(function(){var bo=ag.createElement("div"),bp="script"+(new Date()).getTime(),bn=ag.documentElement;bo.innerHTML="<a name=\'"+bp+"\'/>";bn.insertBefore(bo,bn.firstChild);if(ag.getElementById(bp)){ba.find.ID=function(br,bs,bt){if(typeof bs.getElementById!=="undefined"&&!bt){var bq=bs.getElementById(br[1]);return bq?bq.id===br[1]||typeof bq.getAttributeNode!=="undefined"&&bq.getAttributeNode("id").nodeValue===br[1]?[bq]:G:[]}};ba.filter.ID=function(bs,bq){var br=typeof bs.getAttributeNode!=="undefined"&&bs.getAttributeNode("id");return bs.nodeType===1&&br&&br.nodeValue===bq}}bn.removeChild(bo);bn=bo=null})();(function(){var bn=ag.createElement("div");bn.appendChild(ag.createComment(""));if(bn.getElementsByTagName("*").length>0){ba.find.TAG=function(bo,bs){var br=bs.getElementsByTagName(bo[1]);if(bo[1]==="*"){var bq=[];for(var bp=0;br[bp];bp++){if(br[bp].nodeType===1){bq.push(br[bp])}}br=bq}return br}}bn.innerHTML="<a href=\'#\'></a>";if(bn.firstChild&&typeof bn.firstChild.getAttribute!=="undefined"&&bn.firstChild.getAttribute("href")!=="#"){ba.attrHandle.href=function(bo){return bo.getAttribute("href",2)}}bn=null})();if(ag.querySelectorAll){(function(){var bn=a7,bq=ag.createElement("div"),bp="__sizzle__";bq.innerHTML="<p class=\'TEST\'></p>";if(bq.querySelectorAll&&bq.querySelectorAll(".TEST").length===0){return}a7=function(bA,bs,bv,bz){bs=bs||ag;if(!bz&&!a7.isXML(bs)){var by=/^(\\w+$)|^\\.([\\w\\-]+$)|^#([\\w\\-]+$)/.exec(bA);if(by&&(bs.nodeType===1||bs.nodeType===9)){if(by[1]){return a6(bs.getElementsByTagName(bA),bv)}else{if(by[2]&&ba.find.CLASS&&bs.getElementsByClassName){return a6(bs.getElementsByClassName(by[2]),bv)}}}if(bs.nodeType===9){if(bA==="body"&&bs.body){return a6([bs.body],bv)}else{if(by&&by[3]){var bu=bs.getElementById(by[3]);if(bu&&bu.parentNode){if(bu.id===by[3]){return a6([bu],bv)}}else{return a6([],bv)}}}try{return a6(bs.querySelectorAll(bA),bv)}catch(bw){}}else{if(bs.nodeType===1&&bs.nodeName.toLowerCase()!=="object"){var bt=bs.getAttribute("id"),br=bt||bp,bC=bs.parentNode,bB=/^\\s*[+~]/.test(bA);if(!bt){bs.setAttribute("id",br)}else{br=br.replace(/\'/g,"\\\\$&")}if(bB&&bC){bs=bs.parentNode}try{if(!bB||bC){return a6(bs.querySelectorAll("[id=\'"+br+"\'] "+bA),bv)}}catch(bx){}finally{if(!bt){bs.removeAttribute("id")}}}}}return bn(bA,bs,bv,bz)};for(var bo in bn){a7[bo]=bn[bo]}bq=null})()}(function(){var bn=ag.documentElement,bp=bn.matchesSelector||bn.mozMatchesSelector||bn.webkitMatchesSelector||bn.msMatchesSelector,bo=false;try{bp.call(ag.documentElement,"[test!=\'\']:sizzle")}catch(bq){bo=true}if(bp){a7.matchesSelector=function(br,bt){bt=bt.replace(/\\=\\s*([^\'"\\]]*)\\s*\\]/g,"=\'$1\']");if(!a7.isXML(br)){try{if(bo||!ba.match.PSEUDO.test(bt)&&!/!=/.test(bt)){return bp.call(br,bt)}}catch(bs){}}return a7(bt,null,null,[br]).length>0}}})();(function(){var bn=ag.createElement("div");bn.innerHTML="<div class=\'test e\'></div><div class=\'test\'></div>";if(!bn.getElementsByClassName||bn.getElementsByClassName("e").length===0){return}bn.lastChild.className="e";if(bn.getElementsByClassName("e").length===1){return}ba.order.splice(1,0,"CLASS");ba.find.CLASS=function(bo,bp,bq){if(typeof bp.getElementsByClassName!=="undefined"&&!bq){return bp.getElementsByClassName(bo[1])}};bn=null})();function bj(bo,bt,bs,bw,bu,bv){for(var bq=0,bp=bw.length;bq<bp;bq++){var bn=bw[bq];if(bn){var br=false;bn=bn[bo];while(bn){if(bn.sizcache===bs){br=bw[bn.sizset];break}if(bn.nodeType===1&&!bv){bn.sizcache=bs;bn.sizset=bq}if(bn.nodeName.toLowerCase()===bt){br=bn;break}bn=bn[bo]}bw[bq]=br}}}function bm(bo,bt,bs,bw,bu,bv){for(var bq=0,bp=bw.length;bq<bp;bq++){var bn=bw[bq];if(bn){var br=false;bn=bn[bo];while(bn){if(bn.sizcache===bs){br=bw[bn.sizset];break}if(bn.nodeType===1){if(!bv){bn.sizcache=bs;bn.sizset=bq}if(typeof bt!=="string"){if(bn===bt){br=true;break}}else{if(a7.filter(bt,[bn]).length>0){br=bn;break}}}bn=bn[bo]}bw[bq]=br}}}if(ag.documentElement.contains){a7.contains=function(bo,bn){return bo!==bn&&(bo.contains?bo.contains(bn):true)}}else{if(ag.documentElement.compareDocumentPosition){a7.contains=function(bo,bn){return !!(bo.compareDocumentPosition(bn)&16)}}else{a7.contains=function(){return false}}}a7.isXML=function(bn){var bo=(bn?bn.ownerDocument||bn:0).documentElement;return bo?bo.nodeName!=="HTML":false};var bc=function(bn,bu){var bs,bq=[],br="",bp=bu.nodeType?[bu]:bu;while((bs=ba.match.PSEUDO.exec(bn))){br+=bs[0];bn=bn.replace(ba.match.PSEUDO,"")}bn=ba.relative[bn]?bn+"*":bn;for(var bt=0,bo=bp.length;bt<bo;bt++){a7(bn,bp[bt],bq)}return a7.filter(br,bq)};a.find=a7;a.expr=a7.selectors;a.expr[":"]=a.expr.filters;a.unique=a7.uniqueSort;a.text=a7.getText;a.isXMLDoc=a7.isXML;a.contains=a7.contains})();var S=/Until$/,ad=/^(?:parents|prevUntil|prevAll)/,aP=/,/,a1=/^.[^:#\\[\\.,]*$/,K=Array.prototype.slice,E=a.expr.match.POS,ai={children:true,contents:true,next:true,prev:true};a.fn.extend({find:function(a6){var a8=this.pushStack("","find",a6),bb=0;for(var a9=0,a7=this.length;a9<a7;a9++){bb=a8.length;a.find(a6,this[a9],a8);if(a9>0){for(var bc=bb;bc<a8.length;bc++){for(var ba=0;ba<bb;ba++){if(a8[ba]===a8[bc]){a8.splice(bc--,1);break}}}}}return a8},has:function(a7){var a6=a(a7);return this.filter(function(){for(var a9=0,a8=a6.length;a9<a8;a9++){if(a.contains(this,a6[a9])){return true}}})},not:function(a6){return this.pushStack(an(this,a6,false),"not",a6)},filter:function(a6){return this.pushStack(an(this,a6,true),"filter",a6)},is:function(a6){return !!a6&&a.filter(a6,this).length>0},closest:function(bg,a7){var bd=[],ba,a8,bf=this[0];if(a.isArray(bg)){var bc,a9,bb={},a6=1;if(bf&&bg.length){for(ba=0,a8=bg.length;ba<a8;ba++){a9=bg[ba];if(!bb[a9]){bb[a9]=a.expr.match.POS.test(a9)?a(a9,a7||this.context):a9}}while(bf&&bf.ownerDocument&&bf!==a7){for(a9 in bb){bc=bb[a9];if(bc.jquery?bc.index(bf)>-1:a(bf).is(bc)){bd.push({selector:a9,elem:bf,level:a6})}}bf=bf.parentNode;a6++}}return bd}var be=E.test(bg)?a(bg,a7||this.context):null;for(ba=0,a8=this.length;ba<a8;ba++){bf=this[ba];while(bf){if(be?be.index(bf)>-1:a.find.matchesSelector(bf,bg)){bd.push(bf);break}else{bf=bf.parentNode;if(!bf||!bf.ownerDocument||bf===a7){break}}}}bd=bd.length>1?a.unique(bd):bd;return this.pushStack(bd,"closest",bg)},index:function(a6){if(!a6||typeof a6==="string"){return a.inArray(this[0],a6?a(a6):this.parent().children())}return a.inArray(a6.jquery?a6[0]:a6,this)},add:function(a6,a7){var a9=typeof a6==="string"?a(a6,a7):a.makeArray(a6),a8=a.merge(this.get(),a9);return this.pushStack(A(a9[0])||A(a8[0])?a8:a.unique(a8))},andSelf:function(){return this.add(this.prevObject)}});function A(a6){return !a6||!a6.parentNode||a6.parentNode.nodeType===11}a.each({parent:function(a7){var a6=a7.parentNode;return a6&&a6.nodeType!==11?a6:null},parents:function(a6){return a.dir(a6,"parentNode")},parentsUntil:function(a7,a6,a8){return a.dir(a7,"parentNode",a8)},next:function(a6){return a.nth(a6,2,"nextSibling")},prev:function(a6){return a.nth(a6,2,"previousSibling")},nextAll:function(a6){return a.dir(a6,"nextSibling")},prevAll:function(a6){return a.dir(a6,"previousSibling")},nextUntil:function(a7,a6,a8){return a.dir(a7,"nextSibling",a8)},prevUntil:function(a7,a6,a8){return a.dir(a7,"previousSibling",a8)},siblings:function(a6){return a.sibling(a6.parentNode.firstChild,a6)},children:function(a6){return a.sibling(a6.firstChild)},contents:function(a6){return a.nodeName(a6,"iframe")?a6.contentDocument||a6.contentWindow.document:a.makeArray(a6.childNodes)}},function(a6,a7){a.fn[a6]=function(bb,a8){var ba=a.map(this,a7,bb),a9=K.call(arguments);if(!S.test(a6)){a8=bb}if(a8&&typeof a8==="string"){ba=a.filter(a8,ba)}ba=this.length>1&&!ai[a6]?a.unique(ba):ba;if((this.length>1||aP.test(a8))&&ad.test(a6)){ba=ba.reverse()}return this.pushStack(ba,a6,a9.join(","))}});a.extend({filter:function(a8,a6,a7){if(a7){a8=":not("+a8+")"}return a6.length===1?a.find.matchesSelector(a6[0],a8)?[a6[0]]:[]:a.find.matches(a8,a6)},dir:function(a8,a7,ba){var a6=[],a9=a8[a7];while(a9&&a9.nodeType!==9&&(ba===G||a9.nodeType!==1||!a(a9).is(ba))){if(a9.nodeType===1){a6.push(a9)}a9=a9[a7]}return a6},nth:function(ba,a6,a8,a9){a6=a6||1;var a7=0;for(;ba;ba=ba[a8]){if(ba.nodeType===1&&++a7===a6){break}}return ba},sibling:function(a8,a7){var a6=[];for(;a8;a8=a8.nextSibling){if(a8.nodeType===1&&a8!==a7){a6.push(a8)}}return a6}});function an(a9,a8,a6){if(a.isFunction(a8)){return a.grep(a9,function(bb,ba){var bc=!!a8.call(bb,ba,bb);return bc===a6})}else{if(a8.nodeType){return a.grep(a9,function(bb,ba){return(bb===a8)===a6})}else{if(typeof a8==="string"){var a7=a.grep(a9,function(ba){return ba.nodeType===1});if(a1.test(a8)){return a.filter(a8,a7,!a6)}else{a8=a.filter(a8,a7)}}}}return a.grep(a9,function(bb,ba){return(a.inArray(bb,a8)>=0)===a6})}var X=/ jQuery\\d+="(?:\\d+|null)"/g,ae=/^\\s+/,M=/<(?!area|br|col|embed|hr|img|input|link|meta|param)(([\\w:]+)[^>]*)\\/>/ig,c=/<([\\w:]+)/,v=/<tbody/i,P=/<|&#?\\w+;/,J=/<(?:script|object|embed|option|style)/i,n=/checked\\s*(?:[^=]|=\\s*.checked.)/i,ah={option:[1,"<select multiple=\'multiple\'>","</select>"],legend:[1,"<fieldset>","</fieldset>"],thead:[1,"<table>","</table>"],tr:[2,"<table><tbody>","</tbody></table>"],td:[3,"<table><tbody><tr>","</tr></tbody></table>"],col:[2,"<table><tbody></tbody><colgroup>","</colgroup></table>"],area:[1,"<map>","</map>"],_default:[0,"",""]};ah.optgroup=ah.option;ah.tbody=ah.tfoot=ah.colgroup=ah.caption=ah.thead;ah.th=ah.td;if(!a.support.htmlSerialize){ah._default=[1,"div<div>","</div>"]}a.fn.extend({text:function(a6){if(a.isFunction(a6)){return this.each(function(a8){var a7=a(this);a7.text(a6.call(this,a8,a7.text()))})}if(typeof a6!=="object"&&a6!==G){return this.empty().append((this[0]&&this[0].ownerDocument||ag).createTextNode(a6))}return a.text(this)},wrapAll:function(a6){if(a.isFunction(a6)){return this.each(function(a8){a(this).wrapAll(a6.call(this,a8))})}if(this[0]){var a7=a(a6,this[0].ownerDocument).eq(0).clone(true);if(this[0].parentNode){a7.insertBefore(this[0])}a7.map(function(){var a8=this;while(a8.firstChild&&a8.firstChild.nodeType===1){a8=a8.firstChild}return a8}).append(this)}return this},wrapInner:function(a6){if(a.isFunction(a6)){return this.each(function(a7){a(this).wrapInner(a6.call(this,a7))})}return this.each(function(){var a7=a(this),a8=a7.contents();if(a8.length){a8.wrapAll(a6)}else{a7.append(a6)}})},wrap:function(a6){return this.each(function(){a(this).wrapAll(a6)})},unwrap:function(){return this.parent().each(function(){if(!a.nodeName(this,"body")){a(this).replaceWith(this.childNodes)}}).end()},append:function(){return this.domManip(arguments,true,function(a6){if(this.nodeType===1){this.appendChild(a6)}})},prepend:function(){return this.domManip(arguments,true,function(a6){if(this.nodeType===1){this.insertBefore(a6,this.firstChild)}})},before:function(){if(this[0]&&this[0].parentNode){return this.domManip(arguments,false,function(a7){this.parentNode.insertBefore(a7,this)})}else{if(arguments.length){var a6=a(arguments[0]);a6.push.apply(a6,this.toArray());return this.pushStack(a6,"before",arguments)}}},after:function(){if(this[0]&&this[0].parentNode){return this.domManip(arguments,false,function(a7){this.parentNode.insertBefore(a7,this.nextSibling)})}else{if(arguments.length){var a6=this.pushStack(this,"after",arguments);a6.push.apply(a6,a(arguments[0]).toArray());return a6}}},remove:function(a6,a9){for(var a7=0,a8;(a8=this[a7])!=null;a7++){if(!a6||a.filter(a6,[a8]).length){if(!a9&&a8.nodeType===1){a.cleanData(a8.getElementsByTagName("*"));a.cleanData([a8])}if(a8.parentNode){a8.parentNode.removeChild(a8)}}}return this},empty:function(){for(var a6=0,a7;(a7=this[a6])!=null;a6++){if(a7.nodeType===1){a.cleanData(a7.getElementsByTagName("*"))}while(a7.firstChild){a7.removeChild(a7.firstChild)}}return this},clone:function(a7,a6){a7=a7==null?true:a7;a6=a6==null?a7:a6;return this.map(function(){return a.clone(this,a7,a6)})},html:function(a8){if(a8===G){return this[0]&&this[0].nodeType===1?this[0].innerHTML.replace(X,""):null}else{if(typeof a8==="string"&&!J.test(a8)&&(a.support.leadingWhitespace||!ae.test(a8))&&!ah[(c.exec(a8)||["",""])[1].toLowerCase()]){a8=a8.replace(M,"<$1></$2>");try{for(var a7=0,a6=this.length;a7<a6;a7++){if(this[a7].nodeType===1){a.cleanData(this[a7].getElementsByTagName("*"));this[a7].innerHTML=a8}}}catch(a9){this.empty().append(a8)}}else{if(a.isFunction(a8)){this.each(function(bb){var ba=a(this);ba.html(a8.call(this,bb,ba.html()))})}else{this.empty().append(a8)}}}return this},replaceWith:function(a6){if(this[0]&&this[0].parentNode){if(a.isFunction(a6)){return this.each(function(a9){var a8=a(this),a7=a8.html();a8.replaceWith(a6.call(this,a9,a7))})}if(typeof a6!=="string"){a6=a(a6).detach()}return this.each(function(){var a8=this.nextSibling,a7=this.parentNode;a(this).remove();if(a8){a(a8).before(a6)}else{a(a7).append(a6)}})}else{return this.pushStack(a(a.isFunction(a6)?a6():a6),"replaceWith",a6)}},detach:function(a6){return this.remove(a6,true)},domManip:function(bd,bh,bg){var a9,ba,bc,bf,be=bd[0],a7=[];if(!a.support.checkClone&&arguments.length===3&&typeof be==="string"&&n.test(be)){return this.each(function(){a(this).domManip(bd,bh,bg,true)})}if(a.isFunction(be)){return this.each(function(bj){var bi=a(this);bd[0]=be.call(this,bj,bh?bi.html():G);bi.domManip(bd,bh,bg)})}if(this[0]){bf=be&&be.parentNode;if(a.support.parentNode&&bf&&bf.nodeType===11&&bf.childNodes.length===this.length){a9={fragment:bf}}else{a9=a.buildFragment(bd,this,a7)}bc=a9.fragment;if(bc.childNodes.length===1){ba=bc=bc.firstChild}else{ba=bc.firstChild}if(ba){bh=bh&&a.nodeName(ba,"tr");for(var a8=0,a6=this.length,bb=a6-1;a8<a6;a8++){bg.call(bh?aQ(this[a8],ba):this[a8],a9.cacheable||(a6>1&&a8<bb)?a.clone(bc,true,true):bc)}}if(a7.length){a.each(a7,a0)}}return this}});function aQ(a6,a7){return a.nodeName(a6,"table")?(a6.getElementsByTagName("tbody")[0]||a6.appendChild(a6.ownerDocument.createElement("tbody"))):a6}function s(a6,bd){if(bd.nodeType!==1||!a.hasData(a6)){return}var bc=a.expando,a9=a.data(a6),ba=a.data(bd,a9);if((a9=a9[bc])){var be=a9.events;ba=ba[bc]=a.extend({},a9);if(be){delete ba.handle;ba.events={};for(var bb in be){for(var a8=0,a7=be[bb].length;a8<a7;a8++){a.event.add(bd,bb,be[bb][a8],be[bb][a8].data)}}}}}function Y(a7,a6){if(a6.nodeType!==1){return}var a8=a6.nodeName.toLowerCase();a6.clearAttributes();a6.mergeAttributes(a7);if(a8==="object"){a6.outerHTML=a7.outerHTML}else{if(a8==="input"&&(a7.type==="checkbox"||a7.type==="radio")){if(a7.checked){a6.defaultChecked=a6.checked=a7.checked}if(a6.value!==a7.value){a6.value=a7.value}}else{if(a8==="option"){a6.selected=a7.defaultSelected}else{if(a8==="input"||a8==="textarea"){a6.defaultValue=a7.defaultValue}}}}a6.removeAttribute(a.expando)}a.buildFragment=function(bb,a9,a7){var ba,a6,a8,bc=(a9&&a9[0]?a9[0].ownerDocument||a9[0]:ag);if(bb.length===1&&typeof bb[0]==="string"&&bb[0].length<512&&bc===ag&&bb[0].charAt(0)==="<"&&!J.test(bb[0])&&(a.support.checkClone||!n.test(bb[0]))){a6=true;a8=a.fragments[bb[0]];if(a8){if(a8!==1){ba=a8}}}if(!ba){ba=bc.createDocumentFragment();a.clean(bb,bc,ba,a7)}if(a6){a.fragments[bb[0]]=a8?ba:1}return{fragment:ba,cacheable:a6}};a.fragments={};a.each({appendTo:"append",prependTo:"prepend",insertBefore:"before",insertAfter:"after",replaceAll:"replaceWith"},function(a6,a7){a.fn[a6]=function(a8){var bb=[],be=a(a8),bd=this.length===1&&this[0].parentNode;if(bd&&bd.nodeType===11&&bd.childNodes.length===1&&be.length===1){be[a7](this[0]);return this}else{for(var bc=0,a9=be.length;bc<a9;bc++){var ba=(bc>0?this.clone(true):this).get();a(be[bc])[a7](ba);bb=bb.concat(ba)}return this.pushStack(bb,a6,be.selector)}}});a.extend({clone:function(ba,bc,a8){var bb=ba.cloneNode(true),a6,a7,a9;if(!a.support.noCloneEvent&&(ba.nodeType===1||ba.nodeType===11)&&!a.isXMLDoc(ba)){a6=ba.getElementsByTagName("*");a7=bb.getElementsByTagName("*");for(a9=0;a6[a9];++a9){Y(a6[a9],a7[a9])}Y(ba,bb)}if(bc){s(ba,bb);if(a8&&"getElementsByTagName" in ba){a6=ba.getElementsByTagName("*");a7=bb.getElementsByTagName("*");if(a6.length){for(a9=0;a6[a9];++a9){s(a6[a9],a7[a9])}}}}return bb},clean:function(a8,ba,bh,bc){ba=ba||ag;if(typeof ba.createElement==="undefined"){ba=ba.ownerDocument||ba[0]&&ba[0].ownerDocument||ag}var bi=[];for(var bg=0,bb;(bb=a8[bg])!=null;bg++){if(typeof bb==="number"){bb+=""}if(!bb){continue}if(typeof bb==="string"&&!P.test(bb)){bb=ba.createTextNode(bb)}else{if(typeof bb==="string"){bb=bb.replace(M,"<$1></$2>");var bj=(c.exec(bb)||["",""])[1].toLowerCase(),a9=ah[bj]||ah._default,bf=a9[0],a7=ba.createElement("div");a7.innerHTML=a9[1]+bb+a9[2];while(bf--){a7=a7.lastChild}if(!a.support.tbody){var a6=v.test(bb),be=bj==="table"&&!a6?a7.firstChild&&a7.firstChild.childNodes:a9[1]==="<table>"&&!a6?a7.childNodes:[];for(var bd=be.length-1;bd>=0;--bd){if(a.nodeName(be[bd],"tbody")&&!be[bd].childNodes.length){be[bd].parentNode.removeChild(be[bd])}}}if(!a.support.leadingWhitespace&&ae.test(bb)){a7.insertBefore(ba.createTextNode(ae.exec(bb)[0]),a7.firstChild)}bb=a7.childNodes}}if(bb.nodeType){bi.push(bb)}else{bi=a.merge(bi,bb)}}if(bh){for(bg=0;bi[bg];bg++){if(bc&&a.nodeName(bi[bg],"script")&&(!bi[bg].type||bi[bg].type.toLowerCase()==="text/javascript")){bc.push(bi[bg].parentNode?bi[bg].parentNode.removeChild(bi[bg]):bi[bg])}else{if(bi[bg].nodeType===1){bi.splice.apply(bi,[bg+1,0].concat(a.makeArray(bi[bg].getElementsByTagName("script"))))}bh.appendChild(bi[bg])}}}return bi},cleanData:function(a7){var ba,a8,a6=a.cache,bf=a.expando,bd=a.event.special,bc=a.support.deleteExpando;for(var bb=0,a9;(a9=a7[bb])!=null;bb++){if(a9.nodeName&&a.noData[a9.nodeName.toLowerCase()]){continue}a8=a9[a.expando];if(a8){ba=a6[a8]&&a6[a8][bf];if(ba&&ba.events){for(var be in ba.events){if(bd[be]){a.event.remove(a9,be)}else{a.removeEvent(a9,be,ba.handle)}}if(ba.handle){ba.handle.elem=null}}if(bc){delete a9[a.expando]}else{if(a9.removeAttribute){a9.removeAttribute(a.expando)}}delete a6[a8]}}}});function a0(a6,a7){if(a7.src){a.ajax({url:a7.src,async:false,dataType:"script"})}else{a.globalEval(a7.text||a7.textContent||a7.innerHTML||"")}if(a7.parentNode){a7.parentNode.removeChild(a7)}}var Z=/alpha\\([^)]*\\)/i,af=/opacity=([^)]*)/,aD=/-([a-z])/ig,y=/([A-Z])/g,aS=/^-?\\d+(?:px)?$/i,aZ=/^-?\\d/,aO={position:"absolute",visibility:"hidden",display:"block"},ab=["Left","Right"],aK=["Top","Bottom"],Q,aq,aC,l=function(a6,a7){return a7.toUpperCase()};a.fn.css=function(a6,a7){if(arguments.length===2&&a7===G){return this}return a.access(this,a6,a7,true,function(a9,a8,ba){return ba!==G?a.style(a9,a8,ba):a.css(a9,a8)})};a.extend({cssHooks:{opacity:{get:function(a8,a7){if(a7){var a6=Q(a8,"opacity","opacity");return a6===""?"1":a6}else{return a8.style.opacity}}}},cssNumber:{zIndex:true,fontWeight:true,opacity:true,zoom:true,lineHeight:true},cssProps:{"float":a.support.cssFloat?"cssFloat":"styleFloat"},style:function(a8,a7,bd,a9){if(!a8||a8.nodeType===3||a8.nodeType===8||!a8.style){return}var bc,ba=a.camelCase(a7),a6=a8.style,be=a.cssHooks[ba];a7=a.cssProps[ba]||ba;if(bd!==G){if(typeof bd==="number"&&isNaN(bd)||bd==null){return}if(typeof bd==="number"&&!a.cssNumber[ba]){bd+="px"}if(!be||!("set" in be)||(bd=be.set(a8,bd))!==G){try{a6[a7]=bd}catch(bb){}}}else{if(be&&"get" in be&&(bc=be.get(a8,false,a9))!==G){return bc}return a6[a7]}},css:function(bb,ba,a7){var a9,a8=a.camelCase(ba),a6=a.cssHooks[a8];ba=a.cssProps[a8]||a8;if(a6&&"get" in a6&&(a9=a6.get(bb,true,a7))!==G){return a9}else{if(Q){return Q(bb,ba,a8)}}},swap:function(a9,a8,ba){var a6={};for(var a7 in a8){a6[a7]=a9.style[a7];a9.style[a7]=a8[a7]}ba.call(a9);for(a7 in a8){a9.style[a7]=a6[a7]}},camelCase:function(a6){return a6.replace(aD,l)}});a.curCSS=a.css;a.each(["height","width"],function(a7,a6){a.cssHooks[a6]={get:function(ba,a9,a8){var bb;if(a9){if(ba.offsetWidth!==0){bb=p(ba,a6,a8)}else{a.swap(ba,aO,function(){bb=p(ba,a6,a8)})}if(bb<=0){bb=Q(ba,a6,a6);if(bb==="0px"&&aC){bb=aC(ba,a6,a6)}if(bb!=null){return bb===""||bb==="auto"?"0px":bb}}if(bb<0||bb==null){bb=ba.style[a6];return bb===""||bb==="auto"?"0px":bb}return typeof bb==="string"?bb:bb+"px"}},set:function(a8,a9){if(aS.test(a9)){a9=parseFloat(a9);if(a9>=0){return a9+"px"}}else{return a9}}}});if(!a.support.opacity){a.cssHooks.opacity={get:function(a7,a6){return af.test((a6&&a7.currentStyle?a7.currentStyle.filter:a7.style.filter)||"")?(parseFloat(RegExp.$1)/100)+"":a6?"1":""},set:function(a9,ba){var a8=a9.style;a8.zoom=1;var a6=a.isNaN(ba)?"":"alpha(opacity="+ba*100+")",a7=a8.filter||"";a8.filter=Z.test(a7)?a7.replace(Z,a6):a8.filter+" "+a6}}}if(ag.defaultView&&ag.defaultView.getComputedStyle){aq=function(bb,a6,a9){var a8,ba,a7;a9=a9.replace(y,"-$1").toLowerCase();if(!(ba=bb.ownerDocument.defaultView)){return G}if((a7=ba.getComputedStyle(bb,null))){a8=a7.getPropertyValue(a9);if(a8===""&&!a.contains(bb.ownerDocument.documentElement,bb)){a8=a.style(bb,a9)}}return a8}}if(ag.documentElement.currentStyle){aC=function(ba,a8){var bb,a7=ba.currentStyle&&ba.currentStyle[a8],a6=ba.runtimeStyle&&ba.runtimeStyle[a8],a9=ba.style;if(!aS.test(a7)&&aZ.test(a7)){bb=a9.left;if(a6){ba.runtimeStyle.left=ba.currentStyle.left}a9.left=a8==="fontSize"?"1em":(a7||0);a7=a9.pixelLeft+"px";a9.left=bb;if(a6){ba.runtimeStyle.left=a6}}return a7===""?"auto":a7}}Q=aq||aC;function p(a8,a7,a6){var ba=a7==="width"?ab:aK,a9=a7==="width"?a8.offsetWidth:a8.offsetHeight;if(a6==="border"){return a9}a.each(ba,function(){if(!a6){a9-=parseFloat(a.css(a8,"padding"+this))||0}if(a6==="margin"){a9+=parseFloat(a.css(a8,"margin"+this))||0}else{a9-=parseFloat(a.css(a8,"border"+this+"Width"))||0}});return a9}if(a.expr&&a.expr.filters){a.expr.filters.hidden=function(a8){var a7=a8.offsetWidth,a6=a8.offsetHeight;return(a7===0&&a6===0)||(!a.support.reliableHiddenOffsets&&(a8.style.display||a.css(a8,"display"))==="none")};a.expr.filters.visible=function(a6){return !a.expr.filters.hidden(a6)}}var h=/%20/g,ac=/\\[\\]$/,a5=/\\r?\\n/g,a2=/#.*$/,al=/^(.*?):\\s*(.*?)\\r?$/mg,aG=/^(?:color|date|datetime|email|hidden|month|number|password|range|search|tel|text|time|url|week)$/i,au=/^(?:GET|HEAD)$/,b=/^\\/\\//,H=/\\?/,aN=/<script\\b[^<]*(?:(?!<\\/script>)<[^<]*)*<\\/script>/gi,q=/^(?:select|textarea)/i,f=/\\s+/,a4=/([?&])_=[^&]*/,F=/^(\\w+:)\\/\\/([^\\/?#:]+)(?::(\\d+))?/,z=a.fn.load,R={},r={};function d(a6){return function(ba,bc){if(typeof ba!=="string"){bc=ba;ba="*"}if(a.isFunction(bc)){var a9=ba.toLowerCase().split(f),a8=0,bb=a9.length,a7,bd,be;for(;a8<bb;a8++){a7=a9[a8];be=/^\\+/.test(a7);if(be){a7=a7.substr(1)||"*"}bd=a6[a7]=a6[a7]||[];bd[be?"unshift":"push"](bc)}}}}function az(a7,bg,bb,bf,bd,a9){bd=bd||bg.dataTypes[0];a9=a9||{};a9[bd]=true;var bc=a7[bd],a8=0,a6=bc?bc.length:0,ba=(a7===R),be;for(;a8<a6&&(ba||!be);a8++){be=bc[a8](bg,bb,bf);if(typeof be==="string"){if(a9[be]){be=G}else{bg.dataTypes.unshift(be);be=az(a7,bg,bb,bf,be,a9)}}}if((ba||!be)&&!a9["*"]){be=az(a7,bg,bb,bf,"*",a9)}return be}a.fn.extend({load:function(a8,bb,bc){if(typeof a8!=="string"&&z){return z.apply(this,arguments)}else{if(!this.length){return this}}var ba=a8.indexOf(" ");if(ba>=0){var a6=a8.slice(ba,a8.length);a8=a8.slice(0,ba)}var a9="GET";if(bb){if(a.isFunction(bb)){bc=bb;bb=null}else{if(typeof bb==="object"){bb=a.param(bb,a.ajaxSettings.traditional);a9="POST"}}}var a7=this;a.ajax({url:a8,type:a9,dataType:"html",data:bb,complete:function(bf,bd,be){be=bf.responseText;if(bf.isResolved()){bf.done(function(bg){be=bg});a7.html(a6?a("<div>").append(be.replace(aN,"")).find(a6):be)}if(bc){a7.each(bc,[be,bd,bf])}}});return this},serialize:function(){return a.param(this.serializeArray())},serializeArray:function(){return this.map(function(){return this.elements?a.makeArray(this.elements):this}).filter(function(){return this.name&&!this.disabled&&(this.checked||q.test(this.nodeName)||aG.test(this.type))}).map(function(a6,a7){var a8=a(this).val();return a8==null?null:a.isArray(a8)?a.map(a8,function(ba,a9){return{name:a7.name,value:ba.replace(a5,"\\r\\n")}}):{name:a7.name,value:a8.replace(a5,"\\r\\n")}}).get()}});a.each("ajaxStart ajaxStop ajaxComplete ajaxError ajaxSuccess ajaxSend".split(" "),function(a6,a7){a.fn[a7]=function(a8){return this.bind(a7,a8)}});a.each(["get","post"],function(a6,a7){a[a7]=function(a8,ba,bb,a9){if(a.isFunction(ba)){a9=a9||bb;bb=ba;ba=null}return a.ajax({type:a7,url:a8,data:ba,success:bb,dataType:a9})}});a.extend({getScript:function(a6,a7){return a.get(a6,null,a7,"script")},getJSON:function(a6,a7,a8){return a.get(a6,a7,a8,"json")},ajaxSetup:function(a6){a.extend(true,a.ajaxSettings,a6);if(a6.context){a.ajaxSettings.context=a6.context}},ajaxSettings:{url:location.href,global:true,type:"GET",contentType:"application/x-www-form-urlencoded",processData:true,async:true,accepts:{xml:"application/xml, text/xml",html:"text/html",text:"text/plain",json:"application/json, text/javascript","*":"*/*"},contents:{xml:/xml/,html:/html/,json:/json/},responseFields:{xml:"responseXML",text:"responseText"},converters:{"* text":aR.String,"text html":true,"text json":a.parseJSON,"text xml":a.parseXML}},ajaxPrefilter:d(R),ajaxTransport:d(r),ajax:function(ba,a7){if(typeof a7!=="object"){a7=ba;ba=G}a7=a7||{};var be=a.extend(true,{},a.ajaxSettings,a7),bs=(be.context=("context" in a7?a7:a.ajaxSettings).context)||be,bi=bs===be?a.event:a(bs),br=a.Deferred(),bo=a._Deferred(),bc=be.statusCode||{},bj={},bq,a8,bm,bg,bd=ag.location,bf=bd.protocol||"http:",bk,bb=0,bl,a9={readyState:0,setRequestHeader:function(bt,bu){if(bb===0){bj[bt.toLowerCase()]=bu}return this},getAllResponseHeaders:function(){return bb===2?bq:null},getResponseHeader:function(bu){var bt;if(bb===2){if(!a8){a8={};while((bt=al.exec(bq))){a8[bt[1].toLowerCase()]=bt[2]}}bt=a8[bu.toLowerCase()]}return bt||null},abort:function(bt){bt=bt||"abort";if(bm){bm.abort(bt)}bh(0,bt);return this}};function bh(by,bw,bz,bv){if(bb===2){return}bb=2;if(bg){clearTimeout(bg)}bm=G;bq=bv||"";a9.readyState=by?4:0;var bt,bD,bC,bx=bz?aW(be,a9,bz):G,bu,bB;if(by>=200&&by<300||by===304){if(be.ifModified){if((bu=a9.getResponseHeader("Last-Modified"))){a.lastModified[be.url]=bu}if((bB=a9.getResponseHeader("Etag"))){a.etag[be.url]=bB}}if(by===304){bw="notmodified";bt=true}else{try{bD=C(be,bx);bw="success";bt=true}catch(bA){bw="parsererror";bC=bA}}}else{bC=bw;if(by){bw="error";if(by<0){by=0}}}a9.status=by;a9.statusText=bw;if(bt){br.resolveWith(bs,[bD,bw,a9])}else{br.rejectWith(bs,[a9,bw,bC])}a9.statusCode(bc);bc=G;if(be.global){bi.trigger("ajax"+(bt?"Success":"Error"),[a9,be,bt?bD:bC])}bo.resolveWith(bs,[a9,bw]);if(be.global){bi.trigger("ajaxComplete",[a9,be]);if(!(--a.active)){a.event.trigger("ajaxStop")}}}br.promise(a9);a9.success=a9.done;a9.error=a9.fail;a9.complete=bo.done;a9.statusCode=function(bu){if(bu){var bt;if(bb<2){for(bt in bu){bc[bt]=[bc[bt],bu[bt]]}}else{bt=bu[a9.status];a9.then(bt,bt)}}return this};be.url=(""+(ba||be.url)).replace(a2,"").replace(b,bf+"//");be.dataTypes=a.trim(be.dataType||"*").toLowerCase().split(f);if(!be.crossDomain){bk=F.exec(be.url.toLowerCase());be.crossDomain=!!(bk&&(bk[1]!=bf||bk[2]!=bd.hostname||(bk[3]||(bk[1]==="http:"?80:443))!=(bd.port||(bf==="http:"?80:443))))}if(be.data&&be.processData&&typeof be.data!=="string"){be.data=a.param(be.data,be.traditional)}az(R,be,a7,a9);be.type=be.type.toUpperCase();be.hasContent=!au.test(be.type);if(be.global&&a.active++===0){a.event.trigger("ajaxStart")}if(!be.hasContent){if(be.data){be.url+=(H.test(be.url)?"&":"?")+be.data}if(be.cache===false){var a6=a.now(),bp=be.url.replace(a4,"$1_="+a6);be.url=bp+((bp===be.url)?(H.test(be.url)?"&":"?")+"_="+a6:"")}}if(be.data&&be.hasContent&&be.contentType!==false||a7.contentType){bj["content-type"]=be.contentType}if(be.ifModified){if(a.lastModified[be.url]){bj["if-modified-since"]=a.lastModified[be.url]}if(a.etag[be.url]){bj["if-none-match"]=a.etag[be.url]}}bj.accept=be.dataTypes[0]&&be.accepts[be.dataTypes[0]]?be.accepts[be.dataTypes[0]]+(be.dataTypes[0]!=="*"?", */*; q=0.01":""):be.accepts["*"];for(bl in be.headers){bj[bl.toLowerCase()]=be.headers[bl]}if(be.beforeSend&&(be.beforeSend.call(bs,a9,be)===false||bb===2)){bh(0,"abort");a9=false}else{for(bl in {success:1,error:1,complete:1}){a9[bl](be[bl])}bm=az(r,be,a7,a9);if(!bm){bh(-1,"No Transport")}else{bb=a9.readyState=1;if(be.global){bi.trigger("ajaxSend",[a9,be])}if(be.async&&be.timeout>0){bg=setTimeout(function(){a9.abort("timeout")},be.timeout)}try{bm.send(bj,bh)}catch(bn){if(status<2){bh(-1,bn)}else{a.error(bn)}}}}return a9},param:function(a6,a8){var a7=[],ba=function(bb,bc){bc=a.isFunction(bc)?bc():bc;a7[a7.length]=encodeURIComponent(bb)+"="+encodeURIComponent(bc)};if(a8===G){a8=a.ajaxSettings.traditional}if(a.isArray(a6)||a6.jquery){a.each(a6,function(){ba(this.name,this.value)})}else{for(var a9 in a6){u(a9,a6[a9],a8,ba)}}return a7.join("&").replace(h,"+")}});function u(a7,a9,a6,a8){if(a.isArray(a9)&&a9.length){a.each(a9,function(bb,ba){if(a6||ac.test(a7)){a8(a7,ba)}else{u(a7+"["+(typeof ba==="object"||a.isArray(ba)?bb:"")+"]",ba,a6,a8)}})}else{if(!a6&&a9!=null&&typeof a9==="object"){if(a.isArray(a9)||a.isEmptyObject(a9)){a8(a7,"")}else{a.each(a9,function(bb,ba){u(a7+"["+bb+"]",ba,a6,a8)})}}else{a8(a7,a9)}}}a.extend({active:0,lastModified:{},etag:{}});function aW(bf,be,bb){var a7=bf.contents,bd=bf.dataTypes,a8=bf.responseFields,ba,bc,a9,a6;for(bc in a8){if(bc in bb){be[a8[bc]]=bb[bc]}}while(bd[0]==="*"){bd.shift();if(ba===G){ba=be.getResponseHeader("content-type")}}if(ba){for(bc in a7){if(a7[bc]&&a7[bc].test(ba)){bd.unshift(bc);break}}}if(bd[0] in bb){a9=bd[0]}else{for(bc in bb){if(!bd[0]||bf.converters[bc+" "+bd[0]]){a9=bc;break}if(!a6){a6=bc}}a9=a9||a6}if(a9){if(a9!==bd[0]){bd.unshift(a9)}return bb[a9]}}function C(bi,bb){if(bi.dataFilter){bb=bi.dataFilter(bb,bi.dataType)}var bf=bi.dataTypes,bh=bi.converters,bc,a8=bf.length,bd,be=bf[0],a9,ba,bg,a7,a6;for(bc=1;bc<a8;bc++){a9=be;be=bf[bc];if(be==="*"){be=a9}else{if(a9!=="*"&&a9!==be){ba=a9+" "+be;bg=bh[ba]||bh["* "+be];if(!bg){a6=G;for(a7 in bh){bd=a7.split(" ");if(bd[0]===a9||bd[0]==="*"){a6=bh[bd[1]+" "+be];if(a6){a7=bh[a7];if(a7===true){bg=a6}else{if(a6===true){bg=a7}}break}}}}if(!(bg||a6)){a.error("No conversion from "+ba.replace(" "," to "))}if(bg!==true){bb=bg?bg(bb):a6(a7(bb))}}}}return bb}var ak=a.now(),t=/(\\=)\\?(&|$)|()\\?\\?()/i;a.ajaxSetup({jsonp:"callback",jsonpCallback:function(){return a.expando+"_"+(ak++)}});a.ajaxPrefilter("json jsonp",function(be,bb,bd){bd=(typeof be.data==="string");if(be.dataTypes[0]==="jsonp"||bb.jsonpCallback||bb.jsonp!=null||be.jsonp!==false&&(t.test(be.url)||bd&&t.test(be.data))){var bc,a8=be.jsonpCallback=a.isFunction(be.jsonpCallback)?be.jsonpCallback():be.jsonpCallback,ba=aR[a8],a6=be.url,a9=be.data,a7="$1"+a8+"$2";if(be.jsonp!==false){a6=a6.replace(t,a7);if(be.url===a6){if(bd){a9=a9.replace(t,a7)}if(be.data===a9){a6+=(/\\?/.test(a6)?"&":"?")+be.jsonp+"="+a8}}}be.url=a6;be.data=a9;aR[a8]=function(bf){bc=[bf]};be.complete=[function(){aR[a8]=ba;if(ba){if(bc&&a.isFunction(ba)){aR[a8](bc[0])}}else{try{delete aR[a8]}catch(bf){}}},be.complete];be.converters["script json"]=function(){if(!bc){a.error(a8+" was not called")}return bc[0]};be.dataTypes[0]="json";return"script"}});a.ajaxSetup({accepts:{script:"text/javascript, application/javascript"},contents:{script:/javascript/},converters:{"text script":function(a6){a.globalEval(a6);return a6}}});a.ajaxPrefilter("script",function(a6){if(a6.cache===G){a6.cache=false}if(a6.crossDomain){a6.type="GET";a6.global=false}});a.ajaxTransport("script",function(a8){if(a8.crossDomain){var a6,a7=ag.getElementsByTagName("head")[0]||ag.documentElement;return{send:function(a9,ba){a6=ag.createElement("script");a6.async="async";if(a8.scriptCharset){a6.charset=a8.scriptCharset}a6.src=a8.url;a6.onload=a6.onreadystatechange=function(bc,bb){if(!a6.readyState||/loaded|complete/.test(a6.readyState)){a6.onload=a6.onreadystatechange=null;if(a7&&a6.parentNode){a7.removeChild(a6)}a6=G;if(!bb){ba(200,"success")}}};a7.insertBefore(a6,a7.firstChild)},abort:function(){if(a6){a6.onload(0,1)}}}}});var x=a.now(),aH={},aE,am;a.ajaxSettings.xhr=aR.ActiveXObject?function(){if(aR.location.protocol!=="file:"){try{return new aR.XMLHttpRequest()}catch(a7){}}try{return new aR.ActiveXObject("Microsoft.XMLHTTP")}catch(a6){}}:function(){return new aR.XMLHttpRequest()};try{am=a.ajaxSettings.xhr()}catch(a3){}a.support.ajax=!!am;a.support.cors=am&&("withCredentials" in am);am=G;if(a.support.ajax){a.ajaxTransport(function(a6){if(!a6.crossDomain||a.support.cors){var a7;return{send:function(bc,a8){if(!aE){aE=1;a(aR).bind("unload",function(){a.each(aH,function(bd,be){if(be.onreadystatechange){be.onreadystatechange(1)}})})}var bb=a6.xhr(),ba;if(a6.username){bb.open(a6.type,a6.url,a6.async,a6.username,a6.password)}else{bb.open(a6.type,a6.url,a6.async)}if(!(a6.crossDomain&&!a6.hasContent)&&!bc["x-requested-with"]){bc["x-requested-with"]="XMLHttpRequest"}try{a.each(bc,function(bd,be){bb.setRequestHeader(bd,be)})}catch(a9){}bb.send((a6.hasContent&&a6.data)||null);a7=function(bg,be){if(a7&&(be||bb.readyState===4)){a7=0;if(ba){bb.onreadystatechange=a.noop;delete aH[ba]}if(be){if(bb.readyState!==4){bb.abort()}}else{var bd=bb.status,bk,bh=bb.getAllResponseHeaders(),bi={},bf=bb.responseXML;if(bf&&bf.documentElement){bi.xml=bf}bi.text=bb.responseText;try{bk=bb.statusText}catch(bj){bk=""}bd=bd===0?(!a6.crossDomain||bk?(bh?304:0):302):(bd==1223?204:bd);a8(bd,bk,bi,bh)}}};if(!a6.async||bb.readyState===4){a7()}else{ba=x++;aH[ba]=bb;bb.onreadystatechange=a7}},abort:function(){if(a7){a7(0,1)}}}}})}var L={},aj=/^(?:toggle|show|hide)$/,aw=/^([+\\-]=)?([\\d+.\\-]+)([a-z%]*)$/i,aL,ap=[["height","marginTop","marginBottom","paddingTop","paddingBottom"],["width","marginLeft","marginRight","paddingLeft","paddingRight"],["opacity"]];a.fn.extend({show:function(a9,bc,bb){var a8,ba;if(a9||a9===0){return this.animate(aJ("show",3),a9,bc,bb)}else{for(var a7=0,a6=this.length;a7<a6;a7++){a8=this[a7];ba=a8.style.display;if(!a._data(a8,"olddisplay")&&ba==="none"){ba=a8.style.display=""}if(ba===""&&a.css(a8,"display")==="none"){a._data(a8,"olddisplay",w(a8.nodeName))}}for(a7=0;a7<a6;a7++){a8=this[a7];ba=a8.style.display;if(ba===""||ba==="none"){a8.style.display=a._data(a8,"olddisplay")||""}}return this}},hide:function(a8,bb,ba){if(a8||a8===0){return this.animate(aJ("hide",3),a8,bb,ba)}else{for(var a7=0,a6=this.length;a7<a6;a7++){var a9=a.css(this[a7],"display");if(a9!=="none"&&!a._data(this[a7],"olddisplay")){a._data(this[a7],"olddisplay",a9)}}for(a7=0;a7<a6;a7++){this[a7].style.display="none"}return this}},_toggle:a.fn.toggle,toggle:function(a8,a7,a9){var a6=typeof a8==="boolean";if(a.isFunction(a8)&&a.isFunction(a7)){this._toggle.apply(this,arguments)}else{if(a8==null||a6){this.each(function(){var ba=a6?a8:a(this).is(":hidden");a(this)[ba?"show":"hide"]()})}else{this.animate(aJ("toggle",3),a8,a7,a9)}}return this},fadeTo:function(a6,a9,a8,a7){return this.filter(":hidden").css("opacity",0).show().end().animate({opacity:a9},a6,a8,a7)},animate:function(ba,a7,a9,a8){var a6=a.speed(a7,a9,a8);if(a.isEmptyObject(ba)){return this.each(a6.complete)}return this[a6.queue===false?"each":"queue"](function(){var bd=a.extend({},a6),bh,be=this.nodeType===1,bf=be&&a(this).is(":hidden"),bb=this;for(bh in ba){var bc=a.camelCase(bh);if(bh!==bc){ba[bc]=ba[bh];delete ba[bh];bh=bc}if(ba[bh]==="hide"&&bf||ba[bh]==="show"&&!bf){return bd.complete.call(this)}if(be&&(bh==="height"||bh==="width")){bd.overflow=[this.style.overflow,this.style.overflowX,this.style.overflowY];if(a.css(this,"display")==="inline"&&a.css(this,"float")==="none"){if(!a.support.inlineBlockNeedsLayout){this.style.display="inline-block"}else{var bg=w(this.nodeName);if(bg==="inline"){this.style.display="inline-block"}else{this.style.display="inline";this.style.zoom=1}}}}if(a.isArray(ba[bh])){(bd.specialEasing=bd.specialEasing||{})[bh]=ba[bh][1];ba[bh]=ba[bh][0]}}if(bd.overflow!=null){this.style.overflow="hidden"}bd.curAnim=a.extend({},ba);a.each(ba,function(bj,bn){var bm=new a.fx(bb,bd,bj);if(aj.test(bn)){bm[bn==="toggle"?bf?"show":"hide":bn](ba)}else{var bl=aw.exec(bn),bo=bm.cur()||0;if(bl){var bi=parseFloat(bl[2]),bk=bl[3]||"px";if(bk!=="px"){a.style(bb,bj,(bi||1)+bk);bo=((bi||1)/bm.cur())*bo;a.style(bb,bj,bo+bk)}if(bl[1]){bi=((bl[1]==="-="?-1:1)*bi)+bo}bm.custom(bo,bi,bk)}else{bm.custom(bo,bn,"")}}});return true})},stop:function(a7,a6){var a8=a.timers;if(a7){this.queue([])}this.each(function(){for(var a9=a8.length-1;a9>=0;a9--){if(a8[a9].elem===this){if(a6){a8[a9](true)}a8.splice(a9,1)}}});if(!a6){this.dequeue()}return this}});function aJ(a7,a6){var a8={};a.each(ap.concat.apply([],ap.slice(0,a6)),function(){a8[this]=a7});return a8}a.each({slideDown:aJ("show",1),slideUp:aJ("hide",1),slideToggle:aJ("toggle",1),fadeIn:{opacity:"show"},fadeOut:{opacity:"hide"},fadeToggle:{opacity:"toggle"}},function(a6,a7){a.fn[a6]=function(a8,ba,a9){return this.animate(a7,a8,ba,a9)}});a.extend({speed:function(a8,a9,a7){var a6=a8&&typeof a8==="object"?a.extend({},a8):{complete:a7||!a7&&a9||a.isFunction(a8)&&a8,duration:a8,easing:a7&&a9||a9&&!a.isFunction(a9)&&a9};a6.duration=a.fx.off?0:typeof a6.duration==="number"?a6.duration:a6.duration in a.fx.speeds?a.fx.speeds[a6.duration]:a.fx.speeds._default;a6.old=a6.complete;a6.complete=function(){if(a6.queue!==false){a(this).dequeue()}if(a.isFunction(a6.old)){a6.old.call(this)}};return a6},easing:{linear:function(a8,a9,a6,a7){return a6+a7*a8},swing:function(a8,a9,a6,a7){return((-Math.cos(a8*Math.PI)/2)+0.5)*a7+a6}},timers:[],fx:function(a7,a6,a8){this.options=a6;this.elem=a7;this.prop=a8;if(!a6.orig){a6.orig={}}}});a.fx.prototype={update:function(){if(this.options.step){this.options.step.call(this.elem,this.now,this)}(a.fx.step[this.prop]||a.fx.step._default)(this)},cur:function(){if(this.elem[this.prop]!=null&&(!this.elem.style||this.elem.style[this.prop]==null)){return this.elem[this.prop]}var a6=parseFloat(a.css(this.elem,this.prop));return a6||0},custom:function(bb,ba,a9){var a6=this,a8=a.fx;this.startTime=a.now();this.start=bb;this.end=ba;this.unit=a9||this.unit||"px";this.now=this.start;this.pos=this.state=0;function a7(bc){return a6.step(bc)}a7.elem=this.elem;if(a7()&&a.timers.push(a7)&&!aL){aL=setInterval(a8.tick,a8.interval)}},show:function(){this.options.orig[this.prop]=a.style(this.elem,this.prop);this.options.show=true;this.custom(this.prop==="width"||this.prop==="height"?1:0,this.cur());a(this.elem).show()},hide:function(){this.options.orig[this.prop]=a.style(this.elem,this.prop);this.options.hide=true;this.custom(this.cur(),0)},step:function(a9){var be=a.now(),ba=true;if(a9||be>=this.options.duration+this.startTime){this.now=this.end;this.pos=this.state=1;this.update();this.options.curAnim[this.prop]=true;for(var bb in this.options.curAnim){if(this.options.curAnim[bb]!==true){ba=false}}if(ba){if(this.options.overflow!=null&&!a.support.shrinkWrapBlocks){var a8=this.elem,bf=this.options;a.each(["","X","Y"],function(bg,bh){a8.style["overflow"+bh]=bf.overflow[bg]})}if(this.options.hide){a(this.elem).hide()}if(this.options.hide||this.options.show){for(var a6 in this.options.curAnim){a.style(this.elem,a6,this.options.orig[a6])}}this.options.complete.call(this.elem)}return false}else{var a7=be-this.startTime;this.state=a7/this.options.duration;var bc=this.options.specialEasing&&this.options.specialEasing[this.prop];var bd=this.options.easing||(a.easing.swing?"swing":"linear");this.pos=a.easing[bc||bd](this.state,a7,0,1,this.options.duration);this.now=this.start+((this.end-this.start)*this.pos);this.update()}return true}};a.extend(a.fx,{tick:function(){var a7=a.timers;for(var a6=0;a6<a7.length;a6++){if(!a7[a6]()){a7.splice(a6--,1)}}if(!a7.length){a.fx.stop()}},interval:13,stop:function(){clearInterval(aL);aL=null},speeds:{slow:600,fast:200,_default:400},step:{opacity:function(a6){a.style(a6.elem,"opacity",a6.now)},_default:function(a6){if(a6.elem.style&&a6.elem.style[a6.prop]!=null){a6.elem.style[a6.prop]=(a6.prop==="width"||a6.prop==="height"?Math.max(0,a6.now):a6.now)+a6.unit}else{a6.elem[a6.prop]=a6.now}}}});if(a.expr&&a.expr.filters){a.expr.filters.animated=function(a6){return a.grep(a.timers,function(a7){return a6===a7.elem}).length}}function w(a8){if(!L[a8]){var a6=a("<"+a8+">").appendTo("body"),a7=a6.css("display");a6.remove();if(a7==="none"||a7===""){a7="block"}L[a8]=a7}return L[a8]}var O=/^t(?:able|d|h)$/i,U=/^(?:body|html)$/i;if("getBoundingClientRect" in ag.documentElement){a.fn.offset=function(bj){var a9=this[0],bc;if(bj){return this.each(function(bk){a.offset.setOffset(this,bj,bk)})}if(!a9||!a9.ownerDocument){return null}if(a9===a9.ownerDocument.body){return a.offset.bodyOffset(a9)}try{bc=a9.getBoundingClientRect()}catch(bg){}var bi=a9.ownerDocument,a7=bi.documentElement;if(!bc||!a.contains(a7,a9)){return bc?{top:bc.top,left:bc.left}:{top:0,left:0}}var bd=bi.body,be=ar(bi),bb=a7.clientTop||bd.clientTop||0,bf=a7.clientLeft||bd.clientLeft||0,a6=(be.pageYOffset||a.support.boxModel&&a7.scrollTop||bd.scrollTop),ba=(be.pageXOffset||a.support.boxModel&&a7.scrollLeft||bd.scrollLeft),bh=bc.top+a6-bb,a8=bc.left+ba-bf;return{top:bh,left:a8}}}else{a.fn.offset=function(bh){var bb=this[0];if(bh){return this.each(function(bi){a.offset.setOffset(this,bh,bi)})}if(!bb||!bb.ownerDocument){return null}if(bb===bb.ownerDocument.body){return a.offset.bodyOffset(bb)}a.offset.initialize();var be,a8=bb.offsetParent,a7=bb,bg=bb.ownerDocument,a9=bg.documentElement,bc=bg.body,bd=bg.defaultView,a6=bd?bd.getComputedStyle(bb,null):bb.currentStyle,bf=bb.offsetTop,ba=bb.offsetLeft;while((bb=bb.parentNode)&&bb!==bc&&bb!==a9){if(a.offset.supportsFixedPosition&&a6.position==="fixed"){break}be=bd?bd.getComputedStyle(bb,null):bb.currentStyle;bf-=bb.scrollTop;ba-=bb.scrollLeft;if(bb===a8){bf+=bb.offsetTop;ba+=bb.offsetLeft;if(a.offset.doesNotAddBorder&&!(a.offset.doesAddBorderForTableAndCells&&O.test(bb.nodeName))){bf+=parseFloat(be.borderTopWidth)||0;ba+=parseFloat(be.borderLeftWidth)||0}a7=a8;a8=bb.offsetParent}if(a.offset.subtractsBorderForOverflowNotVisible&&be.overflow!=="visible"){bf+=parseFloat(be.borderTopWidth)||0;ba+=parseFloat(be.borderLeftWidth)||0}a6=be}if(a6.position==="relative"||a6.position==="static"){bf+=bc.offsetTop;ba+=bc.offsetLeft}if(a.offset.supportsFixedPosition&&a6.position==="fixed"){bf+=Math.max(a9.scrollTop,bc.scrollTop);ba+=Math.max(a9.scrollLeft,bc.scrollLeft)}return{top:bf,left:ba}}}a.offset={initialize:function(){var a6=ag.body,a7=ag.createElement("div"),ba,bc,bb,bd,a8=parseFloat(a.css(a6,"marginTop"))||0,a9="<div style=\'position:absolute;top:0;left:0;margin:0;border:5px solid #000;padding:0;width:1px;height:1px;\'><div></div></div><table style=\'position:absolute;top:0;left:0;margin:0;border:5px solid #000;padding:0;width:1px;height:1px;\' cellpadding=\'0\' cellspacing=\'0\'><tr><td></td></tr></table>";a.extend(a7.style,{position:"absolute",top:0,left:0,margin:0,border:0,width:"1px",height:"1px",visibility:"hidden"});a7.innerHTML=a9;a6.insertBefore(a7,a6.firstChild);ba=a7.firstChild;bc=ba.firstChild;bd=ba.nextSibling.firstChild.firstChild;this.doesNotAddBorder=(bc.offsetTop!==5);this.doesAddBorderForTableAndCells=(bd.offsetTop===5);bc.style.position="fixed";bc.style.top="20px";this.supportsFixedPosition=(bc.offsetTop===20||bc.offsetTop===15);bc.style.position=bc.style.top="";ba.style.overflow="hidden";ba.style.position="relative";this.subtractsBorderForOverflowNotVisible=(bc.offsetTop===-5);this.doesNotIncludeMarginInBodyOffset=(a6.offsetTop!==a8);a6.removeChild(a7);a6=a7=ba=bc=bb=bd=null;a.offset.initialize=a.noop},bodyOffset:function(a6){var a8=a6.offsetTop,a7=a6.offsetLeft;a.offset.initialize();if(a.offset.doesNotIncludeMarginInBodyOffset){a8+=parseFloat(a.css(a6,"marginTop"))||0;a7+=parseFloat(a.css(a6,"marginLeft"))||0}return{top:a8,left:a7}},setOffset:function(a9,bi,bc){var bd=a.css(a9,"position");if(bd==="static"){a9.style.position="relative"}var bb=a(a9),a7=bb.offset(),a6=a.css(a9,"top"),bg=a.css(a9,"left"),bh=(bd==="absolute"&&a.inArray("auto",[a6,bg])>-1),bf={},be={},a8,ba;if(bh){be=bb.position()}a8=bh?be.top:parseInt(a6,10)||0;ba=bh?be.left:parseInt(bg,10)||0;if(a.isFunction(bi)){bi=bi.call(a9,bc,a7)}if(bi.top!=null){bf.top=(bi.top-a7.top)+a8}if(bi.left!=null){bf.left=(bi.left-a7.left)+ba}if("using" in bi){bi.using.call(a9,bf)}else{bb.css(bf)}}};a.fn.extend({position:function(){if(!this[0]){return null}var a8=this[0],a7=this.offsetParent(),a9=this.offset(),a6=U.test(a7[0].nodeName)?{top:0,left:0}:a7.offset();a9.top-=parseFloat(a.css(a8,"marginTop"))||0;a9.left-=parseFloat(a.css(a8,"marginLeft"))||0;a6.top+=parseFloat(a.css(a7[0],"borderTopWidth"))||0;a6.left+=parseFloat(a.css(a7[0],"borderLeftWidth"))||0;return{top:a9.top-a6.top,left:a9.left-a6.left}},offsetParent:function(){return this.map(function(){var a6=this.offsetParent||ag.body;while(a6&&(!U.test(a6.nodeName)&&a.css(a6,"position")==="static")){a6=a6.offsetParent}return a6})}});a.each(["Left","Top"],function(a7,a6){var a8="scroll"+a6;a.fn[a8]=function(bb){var a9=this[0],ba;if(!a9){return null}if(bb!==G){return this.each(function(){ba=ar(this);if(ba){ba.scrollTo(!a7?bb:a(ba).scrollLeft(),a7?bb:a(ba).scrollTop())}else{this[a8]=bb}})}else{ba=ar(a9);return ba?("pageXOffset" in ba)?ba[a7?"pageYOffset":"pageXOffset"]:a.support.boxModel&&ba.document.documentElement[a8]||ba.document.body[a8]:a9[a8]}}});function ar(a6){return a.isWindow(a6)?a6:a6.nodeType===9?a6.defaultView||a6.parentWindow:false}a.each(["Height","Width"],function(a7,a6){var a8=a6.toLowerCase();a.fn["inner"+a6]=function(){return this[0]?parseFloat(a.css(this[0],a8,"padding")):null};a.fn["outer"+a6]=function(a9){return this[0]?parseFloat(a.css(this[0],a8,a9?"margin":"border")):null};a.fn[a8]=function(ba){var bb=this[0];if(!bb){return ba==null?null:this}if(a.isFunction(ba)){return this.each(function(bf){var be=a(this);be[a8](ba.call(this,bf,be[a8]()))})}if(a.isWindow(bb)){var bc=bb.document.documentElement["client"+a6];return bb.document.compatMode==="CSS1Compat"&&bc||bb.document.body["client"+a6]||bc}else{if(bb.nodeType===9){return Math.max(bb.documentElement["client"+a6],bb.body["scroll"+a6],bb.documentElement["scroll"+a6],bb.body["offset"+a6],bb.documentElement["offset"+a6])}else{if(ba===G){var bd=a.css(bb,a8),a9=parseFloat(bd);return a.isNaN(a9)?bd:a9}else{return this.css(a8,typeof ba==="string"?ba:ba+"px")}}}}})})(window);\n'''

plot = '''/* Javascript plotting library for jQuery, v. 0.7.\n *\n * Released under the MIT license by IOLA, December 2007.\n *\n */\n(function(b){b.color={};b.color.make=function(d,e,g,f){var c={};c.r=d||0;c.g=e||0;c.b=g||0;c.a=f!=null?f:1;c.add=function(h,j){for(var k=0;k<h.length;++k){c[h.charAt(k)]+=j}return c.normalize()};c.scale=function(h,j){for(var k=0;k<h.length;++k){c[h.charAt(k)]*=j}return c.normalize()};c.toString=function(){if(c.a>=1){return"rgb("+[c.r,c.g,c.b].join(",")+")"}else{return"rgba("+[c.r,c.g,c.b,c.a].join(",")+")"}};c.normalize=function(){function h(k,j,l){return j<k?k:(j>l?l:j)}c.r=h(0,parseInt(c.r),255);c.g=h(0,parseInt(c.g),255);c.b=h(0,parseInt(c.b),255);c.a=h(0,c.a,1);return c};c.clone=function(){return b.color.make(c.r,c.b,c.g,c.a)};return c.normalize()};b.color.extract=function(d,e){var c;do{c=d.css(e).toLowerCase();if(c!=""&&c!="transparent"){break}d=d.parent()}while(!b.nodeName(d.get(0),"body"));if(c=="rgba(0, 0, 0, 0)"){c="transparent"}return b.color.parse(c)};b.color.parse=function(c){var d,f=b.color.make;if(d=/rgb\\(\\s*([0-9]{1,3})\\s*,\\s*([0-9]{1,3})\\s*,\\s*([0-9]{1,3})\\s*\\)/.exec(c)){return f(parseInt(d[1],10),parseInt(d[2],10),parseInt(d[3],10))}if(d=/rgba\\(\\s*([0-9]{1,3})\\s*,\\s*([0-9]{1,3})\\s*,\\s*([0-9]{1,3})\\s*,\\s*([0-9]+(?:\\.[0-9]+)?)\\s*\\)/.exec(c)){return f(parseInt(d[1],10),parseInt(d[2],10),parseInt(d[3],10),parseFloat(d[4]))}if(d=/rgb\\(\\s*([0-9]+(?:\\.[0-9]+)?)\\%\\s*,\\s*([0-9]+(?:\\.[0-9]+)?)\\%\\s*,\\s*([0-9]+(?:\\.[0-9]+)?)\\%\\s*\\)/.exec(c)){return f(parseFloat(d[1])*2.55,parseFloat(d[2])*2.55,parseFloat(d[3])*2.55)}if(d=/rgba\\(\\s*([0-9]+(?:\\.[0-9]+)?)\\%\\s*,\\s*([0-9]+(?:\\.[0-9]+)?)\\%\\s*,\\s*([0-9]+(?:\\.[0-9]+)?)\\%\\s*,\\s*([0-9]+(?:\\.[0-9]+)?)\\s*\\)/.exec(c)){return f(parseFloat(d[1])*2.55,parseFloat(d[2])*2.55,parseFloat(d[3])*2.55,parseFloat(d[4]))}if(d=/#([a-fA-F0-9]{2})([a-fA-F0-9]{2})([a-fA-F0-9]{2})/.exec(c)){return f(parseInt(d[1],16),parseInt(d[2],16),parseInt(d[3],16))}if(d=/#([a-fA-F0-9])([a-fA-F0-9])([a-fA-F0-9])/.exec(c)){return f(parseInt(d[1]+d[1],16),parseInt(d[2]+d[2],16),parseInt(d[3]+d[3],16))}var e=b.trim(c).toLowerCase();if(e=="transparent"){return f(255,255,255,0)}else{d=a[e]||[0,0,0];return f(d[0],d[1],d[2])}};var a={aqua:[0,255,255],azure:[240,255,255],beige:[245,245,220],black:[0,0,0],blue:[0,0,255],brown:[165,42,42],cyan:[0,255,255],darkblue:[0,0,139],darkcyan:[0,139,139],darkgrey:[169,169,169],darkgreen:[0,100,0],darkkhaki:[189,183,107],darkmagenta:[139,0,139],darkolivegreen:[85,107,47],darkorange:[255,140,0],darkorchid:[153,50,204],darkred:[139,0,0],darksalmon:[233,150,122],darkviolet:[148,0,211],fuchsia:[255,0,255],gold:[255,215,0],green:[0,128,0],indigo:[75,0,130],khaki:[240,230,140],lightblue:[173,216,230],lightcyan:[224,255,255],lightgreen:[144,238,144],lightgrey:[211,211,211],lightpink:[255,182,193],lightyellow:[255,255,224],lime:[0,255,0],magenta:[255,0,255],maroon:[128,0,0],navy:[0,0,128],olive:[128,128,0],orange:[255,165,0],pink:[255,192,203],purple:[128,0,128],violet:[128,0,128],red:[255,0,0],silver:[192,192,192],white:[255,255,255],yellow:[255,255,0]}})(jQuery);(function(c){function b(aw,aj,K,ag){var R=[],P={colors:["#edc240","#afd8f8","#cb4b4b","#4da74d","#9440ed"],legend:{show:true,noColumns:1,labelFormatter:null,labelBoxBorderColor:"#ccc",container:null,position:"ne",margin:5,backgroundColor:null,backgroundOpacity:0.85},xaxis:{show:null,position:"bottom",mode:null,color:null,tickColor:null,transform:null,inverseTransform:null,min:null,max:null,autoscaleMargin:null,ticks:null,tickFormatter:null,labelWidth:null,labelHeight:null,reserveSpace:null,tickLength:null,alignTicksWithAxis:null,tickDecimals:null,tickSize:null,minTickSize:null,monthNames:null,timeformat:null,twelveHourClock:false},yaxis:{autoscaleMargin:0.02,position:"left"},xaxes:[],yaxes:[],series:{points:{show:false,radius:3,lineWidth:2,fill:true,fillColor:"#ffffff",symbol:"circle"},lines:{lineWidth:2,fill:false,fillColor:null,steps:false},bars:{show:false,lineWidth:2,barWidth:1,fill:true,fillColor:null,align:"left",horizontal:false},shadowSize:3},grid:{show:true,aboveData:false,color:"#545454",backgroundColor:null,borderColor:null,tickColor:null,labelMargin:5,axisMargin:8,borderWidth:2,minBorderMargin:null,markings:null,markingsColor:"#f4f4f4",markingsLineWidth:2,clickable:false,hoverable:false,autoHighlight:true,mouseActiveRadius:10},hooks:{}},aA=null,ae=null,z=null,I=null,B=null,q=[],ax=[],r={left:0,right:0,top:0,bottom:0},H=0,J=0,h=0,x=0,al={processOptions:[],processRawData:[],processDatapoints:[],drawSeries:[],draw:[],bindEvents:[],drawOverlay:[],shutdown:[]},ar=this;ar.setData=ak;ar.setupGrid=u;ar.draw=X;ar.getPlaceholder=function(){return aw};ar.getCanvas=function(){return aA};ar.getPlotOffset=function(){return r};ar.width=function(){return h};ar.height=function(){return x};ar.offset=function(){var aC=z.offset();aC.left+=r.left;aC.top+=r.top;return aC};ar.getData=function(){return R};ar.getAxes=function(){var aD={},aC;c.each(q.concat(ax),function(aE,aF){if(aF){aD[aF.direction+(aF.n!=1?aF.n:"")+"axis"]=aF}});return aD};ar.getXAxes=function(){return q};ar.getYAxes=function(){return ax};ar.c2p=D;ar.p2c=at;ar.getOptions=function(){return P};ar.highlight=y;ar.unhighlight=U;ar.triggerRedrawOverlay=f;ar.pointOffset=function(aC){return{left:parseInt(q[aB(aC,"x")-1].p2c(+aC.x)+r.left),top:parseInt(ax[aB(aC,"y")-1].p2c(+aC.y)+r.top)}};ar.shutdown=ah;ar.resize=function(){C();g(aA);g(ae)};ar.hooks=al;G(ar);aa(K);Y();ak(aj);u();X();ai();function ao(aE,aC){aC=[ar].concat(aC);for(var aD=0;aD<aE.length;++aD){aE[aD].apply(this,aC)}}function G(){for(var aC=0;aC<ag.length;++aC){var aD=ag[aC];aD.init(ar);if(aD.options){c.extend(true,P,aD.options)}}}function aa(aD){var aC;c.extend(true,P,aD);if(P.xaxis.color==null){P.xaxis.color=P.grid.color}if(P.yaxis.color==null){P.yaxis.color=P.grid.color}if(P.xaxis.tickColor==null){P.xaxis.tickColor=P.grid.tickColor}if(P.yaxis.tickColor==null){P.yaxis.tickColor=P.grid.tickColor}if(P.grid.borderColor==null){P.grid.borderColor=P.grid.color}if(P.grid.tickColor==null){P.grid.tickColor=c.color.parse(P.grid.color).scale("a",0.22).toString()}for(aC=0;aC<Math.max(1,P.xaxes.length);++aC){P.xaxes[aC]=c.extend(true,{},P.xaxis,P.xaxes[aC])}for(aC=0;aC<Math.max(1,P.yaxes.length);++aC){P.yaxes[aC]=c.extend(true,{},P.yaxis,P.yaxes[aC])}if(P.xaxis.noTicks&&P.xaxis.ticks==null){P.xaxis.ticks=P.xaxis.noTicks}if(P.yaxis.noTicks&&P.yaxis.ticks==null){P.yaxis.ticks=P.yaxis.noTicks}if(P.x2axis){P.xaxes[1]=c.extend(true,{},P.xaxis,P.x2axis);P.xaxes[1].position="top"}if(P.y2axis){P.yaxes[1]=c.extend(true,{},P.yaxis,P.y2axis);P.yaxes[1].position="right"}if(P.grid.coloredAreas){P.grid.markings=P.grid.coloredAreas}if(P.grid.coloredAreasColor){P.grid.markingsColor=P.grid.coloredAreasColor}if(P.lines){c.extend(true,P.series.lines,P.lines)}if(P.points){c.extend(true,P.series.points,P.points)}if(P.bars){c.extend(true,P.series.bars,P.bars)}if(P.shadowSize!=null){P.series.shadowSize=P.shadowSize}for(aC=0;aC<P.xaxes.length;++aC){W(q,aC+1).options=P.xaxes[aC]}for(aC=0;aC<P.yaxes.length;++aC){W(ax,aC+1).options=P.yaxes[aC]}for(var aE in al){if(P.hooks[aE]&&P.hooks[aE].length){al[aE]=al[aE].concat(P.hooks[aE])}}ao(al.processOptions,[P])}function ak(aC){R=Z(aC);ay();A()}function Z(aF){var aD=[];for(var aC=0;aC<aF.length;++aC){var aE=c.extend(true,{},P.series);if(aF[aC].data!=null){aE.data=aF[aC].data;delete aF[aC].data;c.extend(true,aE,aF[aC]);aF[aC].data=aE.data}else{aE.data=aF[aC]}aD.push(aE)}return aD}function aB(aD,aE){var aC=aD[aE+"axis"];if(typeof aC=="object"){aC=aC.n}if(typeof aC!="number"){aC=1}return aC}function n(){return c.grep(q.concat(ax),function(aC){return aC})}function D(aF){var aD={},aC,aE;for(aC=0;aC<q.length;++aC){aE=q[aC];if(aE&&aE.used){aD["x"+aE.n]=aE.c2p(aF.left)}}for(aC=0;aC<ax.length;++aC){aE=ax[aC];if(aE&&aE.used){aD["y"+aE.n]=aE.c2p(aF.top)}}if(aD.x1!==undefined){aD.x=aD.x1}if(aD.y1!==undefined){aD.y=aD.y1}return aD}function at(aG){var aE={},aD,aF,aC;for(aD=0;aD<q.length;++aD){aF=q[aD];if(aF&&aF.used){aC="x"+aF.n;if(aG[aC]==null&&aF.n==1){aC="x"}if(aG[aC]!=null){aE.left=aF.p2c(aG[aC]);break}}}for(aD=0;aD<ax.length;++aD){aF=ax[aD];if(aF&&aF.used){aC="y"+aF.n;if(aG[aC]==null&&aF.n==1){aC="y"}if(aG[aC]!=null){aE.top=aF.p2c(aG[aC]);break}}}return aE}function W(aD,aC){if(!aD[aC-1]){aD[aC-1]={n:aC,direction:aD==q?"x":"y",options:c.extend(true,{},aD==q?P.xaxis:P.yaxis)}}return aD[aC-1]}function ay(){var aH;var aN=R.length,aC=[],aF=[];for(aH=0;aH<R.length;++aH){var aK=R[aH].color;if(aK!=null){--aN;if(typeof aK=="number"){aF.push(aK)}else{aC.push(c.color.parse(R[aH].color))}}}for(aH=0;aH<aF.length;++aH){aN=Math.max(aN,aF[aH]+1)}var aD=[],aG=0;aH=0;while(aD.length<aN){var aJ;if(P.colors.length==aH){aJ=c.color.make(100,100,100)}else{aJ=c.color.parse(P.colors[aH])}var aE=aG%2==1?-1:1;aJ.scale("rgb",1+aE*Math.ceil(aG/2)*0.2);aD.push(aJ);++aH;if(aH>=P.colors.length){aH=0;++aG}}var aI=0,aO;for(aH=0;aH<R.length;++aH){aO=R[aH];if(aO.color==null){aO.color=aD[aI].toString();++aI}else{if(typeof aO.color=="number"){aO.color=aD[aO.color].toString()}}if(aO.lines.show==null){var aM,aL=true;for(aM in aO){if(aO[aM]&&aO[aM].show){aL=false;break}}if(aL){aO.lines.show=true}}aO.xaxis=W(q,aB(aO,"x"));aO.yaxis=W(ax,aB(aO,"y"))}}function A(){var aP=Number.POSITIVE_INFINITY,aJ=Number.NEGATIVE_INFINITY,aC=Number.MAX_VALUE,aV,aT,aS,aO,aE,aK,aU,aQ,aI,aH,aD,a1,aY,aM;function aG(a4,a3,a2){if(a3<a4.datamin&&a3!=-aC){a4.datamin=a3}if(a2>a4.datamax&&a2!=aC){a4.datamax=a2}}c.each(n(),function(a2,a3){a3.datamin=aP;a3.datamax=aJ;a3.used=false});for(aV=0;aV<R.length;++aV){aK=R[aV];aK.datapoints={points:[]};ao(al.processRawData,[aK,aK.data,aK.datapoints])}for(aV=0;aV<R.length;++aV){aK=R[aV];var a0=aK.data,aX=aK.datapoints.format;if(!aX){aX=[];aX.push({x:true,number:true,required:true});aX.push({y:true,number:true,required:true});if(aK.bars.show||(aK.lines.show&&aK.lines.fill)){aX.push({y:true,number:true,required:false,defaultValue:0});if(aK.bars.horizontal){delete aX[aX.length-1].y;aX[aX.length-1].x=true}}aK.datapoints.format=aX}if(aK.datapoints.pointsize!=null){continue}aK.datapoints.pointsize=aX.length;aQ=aK.datapoints.pointsize;aU=aK.datapoints.points;insertSteps=aK.lines.show&&aK.lines.steps;aK.xaxis.used=aK.yaxis.used=true;for(aT=aS=0;aT<a0.length;++aT,aS+=aQ){aM=a0[aT];var aF=aM==null;if(!aF){for(aO=0;aO<aQ;++aO){a1=aM[aO];aY=aX[aO];if(aY){if(aY.number&&a1!=null){a1=+a1;if(isNaN(a1)){a1=null}else{if(a1==Infinity){a1=aC}else{if(a1==-Infinity){a1=-aC}}}}if(a1==null){if(aY.required){aF=true}if(aY.defaultValue!=null){a1=aY.defaultValue}}}aU[aS+aO]=a1}}if(aF){for(aO=0;aO<aQ;++aO){a1=aU[aS+aO];if(a1!=null){aY=aX[aO];if(aY.x){aG(aK.xaxis,a1,a1)}if(aY.y){aG(aK.yaxis,a1,a1)}}aU[aS+aO]=null}}else{if(insertSteps&&aS>0&&aU[aS-aQ]!=null&&aU[aS-aQ]!=aU[aS]&&aU[aS-aQ+1]!=aU[aS+1]){for(aO=0;aO<aQ;++aO){aU[aS+aQ+aO]=aU[aS+aO]}aU[aS+1]=aU[aS-aQ+1];aS+=aQ}}}}for(aV=0;aV<R.length;++aV){aK=R[aV];ao(al.processDatapoints,[aK,aK.datapoints])}for(aV=0;aV<R.length;++aV){aK=R[aV];aU=aK.datapoints.points,aQ=aK.datapoints.pointsize;var aL=aP,aR=aP,aN=aJ,aW=aJ;for(aT=0;aT<aU.length;aT+=aQ){if(aU[aT]==null){continue}for(aO=0;aO<aQ;++aO){a1=aU[aT+aO];aY=aX[aO];if(!aY||a1==aC||a1==-aC){continue}if(aY.x){if(a1<aL){aL=a1}if(a1>aN){aN=a1}}if(aY.y){if(a1<aR){aR=a1}if(a1>aW){aW=a1}}}}if(aK.bars.show){var aZ=aK.bars.align=="left"?0:-aK.bars.barWidth/2;if(aK.bars.horizontal){aR+=aZ;aW+=aZ+aK.bars.barWidth}else{aL+=aZ;aN+=aZ+aK.bars.barWidth}}aG(aK.xaxis,aL,aN);aG(aK.yaxis,aR,aW)}c.each(n(),function(a2,a3){if(a3.datamin==aP){a3.datamin=null}if(a3.datamax==aJ){a3.datamax=null}})}function j(aC,aD){var aE=document.createElement("canvas");aE.className=aD;aE.width=H;aE.height=J;if(!aC){c(aE).css({position:"absolute",left:0,top:0})}c(aE).appendTo(aw);if(!aE.getContext){aE=window.G_vmlCanvasManager.initElement(aE)}aE.getContext("2d").save();return aE}function C(){H=aw.width();J=aw.height();if(H<=0||J<=0){throw"Invalid dimensions for plot, width = "+H+", height = "+J}}function g(aD){if(aD.width!=H){aD.width=H}if(aD.height!=J){aD.height=J}var aC=aD.getContext("2d");aC.restore();aC.save()}function Y(){var aD,aC=aw.children("canvas.base"),aE=aw.children("canvas.overlay");if(aC.length==0||aE==0){aw.html("");aw.css({padding:0});if(aw.css("position")=="static"){aw.css("position","relative")}C();aA=j(true,"base");ae=j(false,"overlay");aD=false}else{aA=aC.get(0);ae=aE.get(0);aD=true}I=aA.getContext("2d");B=ae.getContext("2d");z=c([ae,aA]);if(aD){aw.data("plot").shutdown();ar.resize();B.clearRect(0,0,H,J);z.unbind();aw.children().not([aA,ae]).remove()}aw.data("plot",ar)}function ai(){if(P.grid.hoverable){z.mousemove(ab);z.mouseleave(l)}if(P.grid.clickable){z.click(S)}ao(al.bindEvents,[z])}function ah(){if(N){clearTimeout(N)}z.unbind("mousemove",ab);z.unbind("mouseleave",l);z.unbind("click",S);ao(al.shutdown,[z])}function s(aH){function aD(aI){return aI}var aG,aC,aE=aH.options.transform||aD,aF=aH.options.inverseTransform;if(aH.direction=="x"){aG=aH.scale=h/Math.abs(aE(aH.max)-aE(aH.min));aC=Math.min(aE(aH.max),aE(aH.min))}else{aG=aH.scale=x/Math.abs(aE(aH.max)-aE(aH.min));aG=-aG;aC=Math.max(aE(aH.max),aE(aH.min))}if(aE==aD){aH.p2c=function(aI){return(aI-aC)*aG}}else{aH.p2c=function(aI){return(aE(aI)-aC)*aG}}if(!aF){aH.c2p=function(aI){return aC+aI/aG}}else{aH.c2p=function(aI){return aF(aC+aI/aG)}}}function M(aE){var aC=aE.options,aG,aK=aE.ticks||[],aJ=[],aF,aL=aC.labelWidth,aH=aC.labelHeight,aD;function aI(aN,aM){return c(\'<div style="position:absolute;top:-10000px;\'+aM+\'font-size:smaller"><div class="\'+aE.direction+"Axis "+aE.direction+aE.n+\'Axis">\'+aN.join("")+"</div></div>").appendTo(aw)}if(aE.direction=="x"){if(aL==null){aL=Math.floor(H/(aK.length>0?aK.length:1))}if(aH==null){aJ=[];for(aG=0;aG<aK.length;++aG){aF=aK[aG].label;if(aF){aJ.push(\'<div class="tickLabel" style="float:left;width:\'+aL+\'px">\'+aF+"</div>")}}if(aJ.length>0){aJ.push(\'<div style="clear:left"></div>\');aD=aI(aJ,"width:10000px;");aH=aD.height();aD.remove()}}}else{if(aL==null||aH==null){for(aG=0;aG<aK.length;++aG){aF=aK[aG].label;if(aF){aJ.push(\'<div class="tickLabel">\'+aF+"</div>")}}if(aJ.length>0){aD=aI(aJ,"");if(aL==null){aL=aD.children().width()}if(aH==null){aH=aD.find("div.tickLabel").height()}aD.remove()}}}if(aL==null){aL=0}if(aH==null){aH=0}aE.labelWidth=aL;aE.labelHeight=aH}function av(aE){var aD=aE.labelWidth,aM=aE.labelHeight,aI=aE.options.position,aG=aE.options.tickLength,aH=P.grid.axisMargin,aK=P.grid.labelMargin,aL=aE.direction=="x"?q:ax,aF;var aC=c.grep(aL,function(aO){return aO&&aO.options.position==aI&&aO.reserveSpace});if(c.inArray(aE,aC)==aC.length-1){aH=0}if(aG==null){aG="full"}var aJ=c.grep(aL,function(aO){return aO&&aO.reserveSpace});var aN=c.inArray(aE,aJ)==0;if(!aN&&aG=="full"){aG=5}if(!isNaN(+aG)){aK+=+aG}if(aE.direction=="x"){aM+=aK;if(aI=="bottom"){r.bottom+=aM+aH;aE.box={top:J-r.bottom,height:aM}}else{aE.box={top:r.top+aH,height:aM};r.top+=aM+aH}}else{aD+=aK;if(aI=="left"){aE.box={left:r.left+aH,width:aD};r.left+=aD+aH}else{r.right+=aD+aH;aE.box={left:H-r.right,width:aD}}}aE.position=aI;aE.tickLength=aG;aE.box.padding=aK;aE.innermost=aN}function V(aC){if(aC.direction=="x"){aC.box.left=r.left;aC.box.width=h}else{aC.box.top=r.top;aC.box.height=x}}function u(){var aD,aF=n();c.each(aF,function(aG,aH){aH.show=aH.options.show;if(aH.show==null){aH.show=aH.used}aH.reserveSpace=aH.show||aH.options.reserveSpace;o(aH)});allocatedAxes=c.grep(aF,function(aG){return aG.reserveSpace});r.left=r.right=r.top=r.bottom=0;if(P.grid.show){c.each(allocatedAxes,function(aG,aH){T(aH);Q(aH);aq(aH,aH.ticks);M(aH)});for(aD=allocatedAxes.length-1;aD>=0;--aD){av(allocatedAxes[aD])}var aE=P.grid.minBorderMargin;if(aE==null){aE=0;for(aD=0;aD<R.length;++aD){aE=Math.max(aE,R[aD].points.radius+R[aD].points.lineWidth/2)}}for(var aC in r){r[aC]+=P.grid.borderWidth;r[aC]=Math.max(aE,r[aC])}}h=H-r.left-r.right;x=J-r.bottom-r.top;c.each(aF,function(aG,aH){s(aH)});if(P.grid.show){c.each(allocatedAxes,function(aG,aH){V(aH)});k()}p()}function o(aF){var aG=aF.options,aE=+(aG.min!=null?aG.min:aF.datamin),aC=+(aG.max!=null?aG.max:aF.datamax),aI=aC-aE;if(aI==0){var aD=aC==0?1:0.01;if(aG.min==null){aE-=aD}if(aG.max==null||aG.min!=null){aC+=aD}}else{var aH=aG.autoscaleMargin;if(aH!=null){if(aG.min==null){aE-=aI*aH;if(aE<0&&aF.datamin!=null&&aF.datamin>=0){aE=0}}if(aG.max==null){aC+=aI*aH;if(aC>0&&aF.datamax!=null&&aF.datamax<=0){aC=0}}}}aF.min=aE;aF.max=aC}function T(aH){var aN=aH.options;var aI;if(typeof aN.ticks=="number"&&aN.ticks>0){aI=aN.ticks}else{aI=0.3*Math.sqrt(aH.direction=="x"?H:J)}var aU=(aH.max-aH.min)/aI,aP,aC,aO,aS,aT,aR,aJ;if(aN.mode=="time"){var aK={second:1000,minute:60*1000,hour:60*60*1000,day:24*60*60*1000,month:30*24*60*60*1000,year:365.2425*24*60*60*1000};var aL=[[1,"second"],[2,"second"],[5,"second"],[10,"second"],[30,"second"],[1,"minute"],[2,"minute"],[5,"minute"],[10,"minute"],[30,"minute"],[1,"hour"],[2,"hour"],[4,"hour"],[8,"hour"],[12,"hour"],[1,"day"],[2,"day"],[3,"day"],[0.25,"month"],[0.5,"month"],[1,"month"],[2,"month"],[3,"month"],[6,"month"],[1,"year"]];var aD=0;if(aN.minTickSize!=null){if(typeof aN.tickSize=="number"){aD=aN.tickSize}else{aD=aN.minTickSize[0]*aK[aN.minTickSize[1]]}}for(var aT=0;aT<aL.length-1;++aT){if(aU<(aL[aT][0]*aK[aL[aT][1]]+aL[aT+1][0]*aK[aL[aT+1][1]])/2&&aL[aT][0]*aK[aL[aT][1]]>=aD){break}}aP=aL[aT][0];aO=aL[aT][1];if(aO=="year"){aR=Math.pow(10,Math.floor(Math.log(aU/aK.year)/Math.LN10));aJ=(aU/aK.year)/aR;if(aJ<1.5){aP=1}else{if(aJ<3){aP=2}else{if(aJ<7.5){aP=5}else{aP=10}}}aP*=aR}aH.tickSize=aN.tickSize||[aP,aO];aC=function(aY){var a3=[],a1=aY.tickSize[0],a4=aY.tickSize[1],a2=new Date(aY.min);var aX=a1*aK[a4];if(a4=="second"){a2.setUTCSeconds(a(a2.getUTCSeconds(),a1))}if(a4=="minute"){a2.setUTCMinutes(a(a2.getUTCMinutes(),a1))}if(a4=="hour"){a2.setUTCHours(a(a2.getUTCHours(),a1))}if(a4=="month"){a2.setUTCMonth(a(a2.getUTCMonth(),a1))}if(a4=="year"){a2.setUTCFullYear(a(a2.getUTCFullYear(),a1))}a2.setUTCMilliseconds(0);if(aX>=aK.minute){a2.setUTCSeconds(0)}if(aX>=aK.hour){a2.setUTCMinutes(0)}if(aX>=aK.day){a2.setUTCHours(0)}if(aX>=aK.day*4){a2.setUTCDate(1)}if(aX>=aK.year){a2.setUTCMonth(0)}var a6=0,a5=Number.NaN,aZ;do{aZ=a5;a5=a2.getTime();a3.push(a5);if(a4=="month"){if(a1<1){a2.setUTCDate(1);var aW=a2.getTime();a2.setUTCMonth(a2.getUTCMonth()+1);var a0=a2.getTime();a2.setTime(a5+a6*aK.hour+(a0-aW)*a1);a6=a2.getUTCHours();a2.setUTCHours(0)}else{a2.setUTCMonth(a2.getUTCMonth()+a1)}}else{if(a4=="year"){a2.setUTCFullYear(a2.getUTCFullYear()+a1)}else{a2.setTime(a5+aX)}}}while(a5<aY.max&&a5!=aZ);return a3};aS=function(aW,aZ){var a1=new Date(aW);if(aN.timeformat!=null){return c.plot.formatDate(a1,aN.timeformat,aN.monthNames)}var aX=aZ.tickSize[0]*aK[aZ.tickSize[1]];var aY=aZ.max-aZ.min;var a0=(aN.twelveHourClock)?" %p":"";if(aX<aK.minute){fmt="%h:%M:%S"+a0}else{if(aX<aK.day){if(aY<2*aK.day){fmt="%h:%M"+a0}else{fmt="%b %d %h:%M"+a0}}else{if(aX<aK.month){fmt="%b %d"}else{if(aX<aK.year){if(aY<aK.year){fmt="%b"}else{fmt="%b %y"}}else{fmt="%y"}}}}return c.plot.formatDate(a1,fmt,aN.monthNames)}}else{var aV=aN.tickDecimals;var aQ=-Math.floor(Math.log(aU)/Math.LN10);if(aV!=null&&aQ>aV){aQ=aV}aR=Math.pow(10,-aQ);aJ=aU/aR;if(aJ<1.5){aP=1}else{if(aJ<3){aP=2;if(aJ>2.25&&(aV==null||aQ+1<=aV)){aP=2.5;++aQ}}else{if(aJ<7.5){aP=5}else{aP=10}}}aP*=aR;if(aN.minTickSize!=null&&aP<aN.minTickSize){aP=aN.minTickSize}aH.tickDecimals=Math.max(0,aV!=null?aV:aQ);aH.tickSize=aN.tickSize||aP;aC=function(aY){var a0=[];var a1=a(aY.min,aY.tickSize),aX=0,aW=Number.NaN,aZ;do{aZ=aW;aW=a1+aX*aY.tickSize;a0.push(aW);++aX}while(aW<aY.max&&aW!=aZ);return a0};aS=function(aW,aX){return aW.toFixed(aX.tickDecimals)}}if(aN.alignTicksWithAxis!=null){var aG=(aH.direction=="x"?q:ax)[aN.alignTicksWithAxis-1];if(aG&&aG.used&&aG!=aH){var aM=aC(aH);if(aM.length>0){if(aN.min==null){aH.min=Math.min(aH.min,aM[0])}if(aN.max==null&&aM.length>1){aH.max=Math.max(aH.max,aM[aM.length-1])}}aC=function(aY){var aZ=[],aW,aX;for(aX=0;aX<aG.ticks.length;++aX){aW=(aG.ticks[aX].v-aG.min)/(aG.max-aG.min);aW=aY.min+aW*(aY.max-aY.min);aZ.push(aW)}return aZ};if(aH.mode!="time"&&aN.tickDecimals==null){var aF=Math.max(0,-Math.floor(Math.log(aU)/Math.LN10)+1),aE=aC(aH);if(!(aE.length>1&&/\\..*0$/.test((aE[1]-aE[0]).toFixed(aF)))){aH.tickDecimals=aF}}}}aH.tickGenerator=aC;if(c.isFunction(aN.tickFormatter)){aH.tickFormatter=function(aW,aX){return""+aN.tickFormatter(aW,aX)}}else{aH.tickFormatter=aS}}function Q(aG){var aI=aG.options.ticks,aH=[];if(aI==null||(typeof aI=="number"&&aI>0)){aH=aG.tickGenerator(aG)}else{if(aI){if(c.isFunction(aI)){aH=aI({min:aG.min,max:aG.max})}else{aH=aI}}}var aF,aC;aG.ticks=[];for(aF=0;aF<aH.length;++aF){var aD=null;var aE=aH[aF];if(typeof aE=="object"){aC=+aE[0];if(aE.length>1){aD=aE[1]}}else{aC=+aE}if(aD==null){aD=aG.tickFormatter(aC,aG)}if(!isNaN(aC)){aG.ticks.push({v:aC,label:aD})}}}function aq(aC,aD){if(aC.options.autoscaleMargin&&aD.length>0){if(aC.options.min==null){aC.min=Math.min(aC.min,aD[0].v)}if(aC.options.max==null&&aD.length>1){aC.max=Math.max(aC.max,aD[aD.length-1].v)}}}function X(){I.clearRect(0,0,H,J);var aD=P.grid;if(aD.show&&aD.backgroundColor){O()}if(aD.show&&!aD.aboveData){ad()}for(var aC=0;aC<R.length;++aC){ao(al.drawSeries,[I,R[aC]]);d(R[aC])}ao(al.draw,[I]);if(aD.show&&aD.aboveData){ad()}}function E(aC,aJ){var aF,aI,aH,aE,aG=n();for(i=0;i<aG.length;++i){aF=aG[i];if(aF.direction==aJ){aE=aJ+aF.n+"axis";if(!aC[aE]&&aF.n==1){aE=aJ+"axis"}if(aC[aE]){aI=aC[aE].from;aH=aC[aE].to;break}}}if(!aC[aE]){aF=aJ=="x"?q[0]:ax[0];aI=aC[aJ+"1"];aH=aC[aJ+"2"]}if(aI!=null&&aH!=null&&aI>aH){var aD=aI;aI=aH;aH=aD}return{from:aI,to:aH,axis:aF}}function O(){I.save();I.translate(r.left,r.top);I.fillStyle=an(P.grid.backgroundColor,x,0,"rgba(255, 255, 255, 0)");I.fillRect(0,0,h,x);I.restore()}function ad(){var aG;I.save();I.translate(r.left,r.top);var aI=P.grid.markings;if(aI){if(c.isFunction(aI)){var aL=ar.getAxes();aL.xmin=aL.xaxis.min;aL.xmax=aL.xaxis.max;aL.ymin=aL.yaxis.min;aL.ymax=aL.yaxis.max;aI=aI(aL)}for(aG=0;aG<aI.length;++aG){var aE=aI[aG],aD=E(aE,"x"),aJ=E(aE,"y");if(aD.from==null){aD.from=aD.axis.min}if(aD.to==null){aD.to=aD.axis.max}if(aJ.from==null){aJ.from=aJ.axis.min}if(aJ.to==null){aJ.to=aJ.axis.max}if(aD.to<aD.axis.min||aD.from>aD.axis.max||aJ.to<aJ.axis.min||aJ.from>aJ.axis.max){continue}aD.from=Math.max(aD.from,aD.axis.min);aD.to=Math.min(aD.to,aD.axis.max);aJ.from=Math.max(aJ.from,aJ.axis.min);aJ.to=Math.min(aJ.to,aJ.axis.max);if(aD.from==aD.to&&aJ.from==aJ.to){continue}aD.from=aD.axis.p2c(aD.from);aD.to=aD.axis.p2c(aD.to);aJ.from=aJ.axis.p2c(aJ.from);aJ.to=aJ.axis.p2c(aJ.to);if(aD.from==aD.to||aJ.from==aJ.to){I.beginPath();I.strokeStyle=aE.color||P.grid.markingsColor;I.lineWidth=aE.lineWidth||P.grid.markingsLineWidth;I.moveTo(aD.from,aJ.from);I.lineTo(aD.to,aJ.to);I.stroke()}else{I.fillStyle=aE.color||P.grid.markingsColor;I.fillRect(aD.from,aJ.to,aD.to-aD.from,aJ.from-aJ.to)}}}var aL=n(),aN=P.grid.borderWidth;for(var aF=0;aF<aL.length;++aF){var aC=aL[aF],aH=aC.box,aR=aC.tickLength,aO,aM,aQ,aK;if(!aC.show||aC.ticks.length==0){continue}I.strokeStyle=aC.options.tickColor||c.color.parse(aC.options.color).scale("a",0.22).toString();I.lineWidth=1;if(aC.direction=="x"){aO=0;if(aR=="full"){aM=(aC.position=="top"?0:x)}else{aM=aH.top-r.top+(aC.position=="top"?aH.height:0)}}else{aM=0;if(aR=="full"){aO=(aC.position=="left"?0:h)}else{aO=aH.left-r.left+(aC.position=="left"?aH.width:0)}}if(!aC.innermost){I.beginPath();aQ=aK=0;if(aC.direction=="x"){aQ=h}else{aK=x}if(I.lineWidth==1){aO=Math.floor(aO)+0.5;aM=Math.floor(aM)+0.5}I.moveTo(aO,aM);I.lineTo(aO+aQ,aM+aK);I.stroke()}I.beginPath();for(aG=0;aG<aC.ticks.length;++aG){var aP=aC.ticks[aG].v;aQ=aK=0;if(aP<aC.min||aP>aC.max||(aR=="full"&&aN>0&&(aP==aC.min||aP==aC.max))){continue}if(aC.direction=="x"){aO=aC.p2c(aP);aK=aR=="full"?-x:aR;if(aC.position=="top"){aK=-aK}}else{aM=aC.p2c(aP);aQ=aR=="full"?-h:aR;if(aC.position=="left"){aQ=-aQ}}if(I.lineWidth==1){if(aC.direction=="x"){aO=Math.floor(aO)+0.5}else{aM=Math.floor(aM)+0.5}}I.moveTo(aO,aM);I.lineTo(aO+aQ,aM+aK)}I.stroke()}if(aN){I.lineWidth=aN;I.strokeStyle=P.grid.borderColor;I.strokeRect(-aN/2,-aN/2,h+aN,x+aN)}I.restore()}function k(){aw.find(".tickLabels").remove();var aH=[\'<div class="tickLabels" style="font-size:smaller">\'];var aK=n();for(var aE=0;aE<aK.length;++aE){var aD=aK[aE],aG=aD.box;if(!aD.show){continue}aH.push(\'<div class="\'+aD.direction+"Axis "+aD.direction+aD.n+\'Axis" style="color:\'+aD.options.color+\'">\');for(var aF=0;aF<aD.ticks.length;++aF){var aI=aD.ticks[aF];if(!aI.label||aI.v<aD.min||aI.v>aD.max){continue}var aL={},aJ;if(aD.direction=="x"){aJ="center";aL.left=Math.round(r.left+aD.p2c(aI.v)-aD.labelWidth/2);if(aD.position=="bottom"){aL.top=aG.top+aG.padding}else{aL.bottom=J-(aG.top+aG.height-aG.padding)}}else{aL.top=Math.round(r.top+aD.p2c(aI.v)-aD.labelHeight/2);if(aD.position=="left"){aL.right=H-(aG.left+aG.width-aG.padding);aJ="right"}else{aL.left=aG.left+aG.padding;aJ="left"}}aL.width=aD.labelWidth;var aC=["position:absolute","text-align:"+aJ];for(var aM in aL){aC.push(aM+":"+aL[aM]+"px")}aH.push(\'<div class="tickLabel" style="\'+aC.join(";")+\'">\'+aI.label+"</div>")}aH.push("</div>")}aH.push("</div>");aw.append(aH.join(""))}function d(aC){if(aC.lines.show){au(aC)}if(aC.bars.show){e(aC)}if(aC.points.show){ap(aC)}}function au(aF){function aE(aQ,aR,aJ,aV,aU){var aW=aQ.points,aK=aQ.pointsize,aO=null,aN=null;I.beginPath();for(var aP=aK;aP<aW.length;aP+=aK){var aM=aW[aP-aK],aT=aW[aP-aK+1],aL=aW[aP],aS=aW[aP+1];if(aM==null||aL==null){continue}if(aT<=aS&&aT<aU.min){if(aS<aU.min){continue}aM=(aU.min-aT)/(aS-aT)*(aL-aM)+aM;aT=aU.min}else{if(aS<=aT&&aS<aU.min){if(aT<aU.min){continue}aL=(aU.min-aT)/(aS-aT)*(aL-aM)+aM;aS=aU.min}}if(aT>=aS&&aT>aU.max){if(aS>aU.max){continue}aM=(aU.max-aT)/(aS-aT)*(aL-aM)+aM;aT=aU.max}else{if(aS>=aT&&aS>aU.max){if(aT>aU.max){continue}aL=(aU.max-aT)/(aS-aT)*(aL-aM)+aM;aS=aU.max}}if(aM<=aL&&aM<aV.min){if(aL<aV.min){continue}aT=(aV.min-aM)/(aL-aM)*(aS-aT)+aT;aM=aV.min}else{if(aL<=aM&&aL<aV.min){if(aM<aV.min){continue}aS=(aV.min-aM)/(aL-aM)*(aS-aT)+aT;aL=aV.min}}if(aM>=aL&&aM>aV.max){if(aL>aV.max){continue}aT=(aV.max-aM)/(aL-aM)*(aS-aT)+aT;aM=aV.max}else{if(aL>=aM&&aL>aV.max){if(aM>aV.max){continue}aS=(aV.max-aM)/(aL-aM)*(aS-aT)+aT;aL=aV.max}}if(aM!=aO||aT!=aN){I.moveTo(aV.p2c(aM)+aR,aU.p2c(aT)+aJ)}aO=aL;aN=aS;I.lineTo(aV.p2c(aL)+aR,aU.p2c(aS)+aJ)}I.stroke()}function aG(aJ,aR,aQ){var aX=aJ.points,aW=aJ.pointsize,aO=Math.min(Math.max(0,aQ.min),aQ.max),aY=0,aV,aU=false,aN=1,aM=0,aS=0;while(true){if(aW>0&&aY>aX.length+aW){break}aY+=aW;var a0=aX[aY-aW],aL=aX[aY-aW+aN],aZ=aX[aY],aK=aX[aY+aN];if(aU){if(aW>0&&a0!=null&&aZ==null){aS=aY;aW=-aW;aN=2;continue}if(aW<0&&aY==aM+aW){I.fill();aU=false;aW=-aW;aN=1;aY=aM=aS+aW;continue}}if(a0==null||aZ==null){continue}if(a0<=aZ&&a0<aR.min){if(aZ<aR.min){continue}aL=(aR.min-a0)/(aZ-a0)*(aK-aL)+aL;a0=aR.min}else{if(aZ<=a0&&aZ<aR.min){if(a0<aR.min){continue}aK=(aR.min-a0)/(aZ-a0)*(aK-aL)+aL;aZ=aR.min}}if(a0>=aZ&&a0>aR.max){if(aZ>aR.max){continue}aL=(aR.max-a0)/(aZ-a0)*(aK-aL)+aL;a0=aR.max}else{if(aZ>=a0&&aZ>aR.max){if(a0>aR.max){continue}aK=(aR.max-a0)/(aZ-a0)*(aK-aL)+aL;aZ=aR.max}}if(!aU){I.beginPath();I.moveTo(aR.p2c(a0),aQ.p2c(aO));aU=true}if(aL>=aQ.max&&aK>=aQ.max){I.lineTo(aR.p2c(a0),aQ.p2c(aQ.max));I.lineTo(aR.p2c(aZ),aQ.p2c(aQ.max));continue}else{if(aL<=aQ.min&&aK<=aQ.min){I.lineTo(aR.p2c(a0),aQ.p2c(aQ.min));I.lineTo(aR.p2c(aZ),aQ.p2c(aQ.min));continue}}var aP=a0,aT=aZ;if(aL<=aK&&aL<aQ.min&&aK>=aQ.min){a0=(aQ.min-aL)/(aK-aL)*(aZ-a0)+a0;aL=aQ.min}else{if(aK<=aL&&aK<aQ.min&&aL>=aQ.min){aZ=(aQ.min-aL)/(aK-aL)*(aZ-a0)+a0;aK=aQ.min}}if(aL>=aK&&aL>aQ.max&&aK<=aQ.max){a0=(aQ.max-aL)/(aK-aL)*(aZ-a0)+a0;aL=aQ.max}else{if(aK>=aL&&aK>aQ.max&&aL<=aQ.max){aZ=(aQ.max-aL)/(aK-aL)*(aZ-a0)+a0;aK=aQ.max}}if(a0!=aP){I.lineTo(aR.p2c(aP),aQ.p2c(aL))}I.lineTo(aR.p2c(a0),aQ.p2c(aL));I.lineTo(aR.p2c(aZ),aQ.p2c(aK));if(aZ!=aT){I.lineTo(aR.p2c(aZ),aQ.p2c(aK));I.lineTo(aR.p2c(aT),aQ.p2c(aK))}}}I.save();I.translate(r.left,r.top);I.lineJoin="round";var aH=aF.lines.lineWidth,aC=aF.shadowSize;if(aH>0&&aC>0){I.lineWidth=aC;I.strokeStyle="rgba(0,0,0,0.1)";var aI=Math.PI/18;aE(aF.datapoints,Math.sin(aI)*(aH/2+aC/2),Math.cos(aI)*(aH/2+aC/2),aF.xaxis,aF.yaxis);I.lineWidth=aC/2;aE(aF.datapoints,Math.sin(aI)*(aH/2+aC/4),Math.cos(aI)*(aH/2+aC/4),aF.xaxis,aF.yaxis)}I.lineWidth=aH;I.strokeStyle=aF.color;var aD=af(aF.lines,aF.color,0,x);if(aD){I.fillStyle=aD;aG(aF.datapoints,aF.xaxis,aF.yaxis)}if(aH>0){aE(aF.datapoints,0,0,aF.xaxis,aF.yaxis)}I.restore()}function ap(aF){function aI(aO,aN,aV,aL,aT,aU,aR,aK){var aS=aO.points,aJ=aO.pointsize;for(var aM=0;aM<aS.length;aM+=aJ){var aQ=aS[aM],aP=aS[aM+1];if(aQ==null||aQ<aU.min||aQ>aU.max||aP<aR.min||aP>aR.max){continue}I.beginPath();aQ=aU.p2c(aQ);aP=aR.p2c(aP)+aL;if(aK=="circle"){I.arc(aQ,aP,aN,0,aT?Math.PI:Math.PI*2,false)}else{aK(I,aQ,aP,aN,aT)}I.closePath();if(aV){I.fillStyle=aV;I.fill()}I.stroke()}}I.save();I.translate(r.left,r.top);var aH=aF.points.lineWidth,aD=aF.shadowSize,aC=aF.points.radius,aG=aF.points.symbol;if(aH>0&&aD>0){var aE=aD/2;I.lineWidth=aE;I.strokeStyle="rgba(0,0,0,0.1)";aI(aF.datapoints,aC,null,aE+aE/2,true,aF.xaxis,aF.yaxis,aG);I.strokeStyle="rgba(0,0,0,0.2)";aI(aF.datapoints,aC,null,aE/2,true,aF.xaxis,aF.yaxis,aG)}I.lineWidth=aH;I.strokeStyle=aF.color;aI(aF.datapoints,aC,af(aF.points,aF.color),0,false,aF.xaxis,aF.yaxis,aG);I.restore()}function F(aO,aN,aW,aJ,aR,aG,aE,aM,aL,aV,aS,aD){var aF,aU,aK,aQ,aH,aC,aP,aI,aT;if(aS){aI=aC=aP=true;aH=false;aF=aW;aU=aO;aQ=aN+aJ;aK=aN+aR;if(aU<aF){aT=aU;aU=aF;aF=aT;aH=true;aC=false}}else{aH=aC=aP=true;aI=false;aF=aO+aJ;aU=aO+aR;aK=aW;aQ=aN;if(aQ<aK){aT=aQ;aQ=aK;aK=aT;aI=true;aP=false}}if(aU<aM.min||aF>aM.max||aQ<aL.min||aK>aL.max){return}if(aF<aM.min){aF=aM.min;aH=false}if(aU>aM.max){aU=aM.max;aC=false}if(aK<aL.min){aK=aL.min;aI=false}if(aQ>aL.max){aQ=aL.max;aP=false}aF=aM.p2c(aF);aK=aL.p2c(aK);aU=aM.p2c(aU);aQ=aL.p2c(aQ);if(aE){aV.beginPath();aV.moveTo(aF,aK);aV.lineTo(aF,aQ);aV.lineTo(aU,aQ);aV.lineTo(aU,aK);aV.fillStyle=aE(aK,aQ);aV.fill()}if(aD>0&&(aH||aC||aP||aI)){aV.beginPath();aV.moveTo(aF,aK+aG);if(aH){aV.lineTo(aF,aQ+aG)}else{aV.moveTo(aF,aQ+aG)}if(aP){aV.lineTo(aU,aQ+aG)}else{aV.moveTo(aU,aQ+aG)}if(aC){aV.lineTo(aU,aK+aG)}else{aV.moveTo(aU,aK+aG)}if(aI){aV.lineTo(aF,aK+aG)}else{aV.moveTo(aF,aK+aG)}aV.stroke()}}function e(aE){function aD(aK,aJ,aM,aH,aL,aO,aN){var aP=aK.points,aG=aK.pointsize;for(var aI=0;aI<aP.length;aI+=aG){if(aP[aI]==null){continue}F(aP[aI],aP[aI+1],aP[aI+2],aJ,aM,aH,aL,aO,aN,I,aE.bars.horizontal,aE.bars.lineWidth)}}I.save();I.translate(r.left,r.top);I.lineWidth=aE.bars.lineWidth;I.strokeStyle=aE.color;var aC=aE.bars.align=="left"?0:-aE.bars.barWidth/2;var aF=aE.bars.fill?function(aG,aH){return af(aE.bars,aE.color,aG,aH)}:null;aD(aE.datapoints,aC,aC+aE.bars.barWidth,0,aF,aE.xaxis,aE.yaxis);I.restore()}function af(aE,aC,aD,aG){var aF=aE.fill;if(!aF){return null}if(aE.fillColor){return an(aE.fillColor,aD,aG,aC)}var aH=c.color.parse(aC);aH.a=typeof aF=="number"?aF:0.4;aH.normalize();return aH.toString()}function p(){aw.find(".legend").remove();if(!P.legend.show){return}var aI=[],aG=false,aO=P.legend.labelFormatter,aN,aK;for(var aF=0;aF<R.length;++aF){aN=R[aF];aK=aN.label;if(!aK){continue}if(aF%P.legend.noColumns==0){if(aG){aI.push("</tr>")}aI.push("<tr>");aG=true}if(aO){aK=aO(aK,aN)}aI.push(\'<td class="legendColorBox"><div style="border:1px solid \'+P.legend.labelBoxBorderColor+\';padding:1px"><div style="width:4px;height:0;border:5px solid \'+aN.color+\';overflow:hidden"></div></div></td><td class="legendLabel">\'+aK+"</td>")}if(aG){aI.push("</tr>")}if(aI.length==0){return}var aM=\'<table style="font-size:smaller;color:\'+P.grid.color+\'">\'+aI.join("")+"</table>";if(P.legend.container!=null){c(P.legend.container).html(aM)}else{var aJ="",aD=P.legend.position,aE=P.legend.margin;if(aE[0]==null){aE=[aE,aE]}if(aD.charAt(0)=="n"){aJ+="top:"+(aE[1]+r.top)+"px;"}else{if(aD.charAt(0)=="s"){aJ+="bottom:"+(aE[1]+r.bottom)+"px;"}}if(aD.charAt(1)=="e"){aJ+="right:"+(aE[0]+r.right)+"px;"}else{if(aD.charAt(1)=="w"){aJ+="left:"+(aE[0]+r.left)+"px;"}}var aL=c(\'<div class="legend">\'+aM.replace(\'style="\',\'style="position:absolute;\'+aJ+";")+"</div>").appendTo(aw);if(P.legend.backgroundOpacity!=0){var aH=P.legend.backgroundColor;if(aH==null){aH=P.grid.backgroundColor;if(aH&&typeof aH=="string"){aH=c.color.parse(aH)}else{aH=c.color.extract(aL,"background-color")}aH.a=1;aH=aH.toString()}var aC=aL.children();c(\'<div style="position:absolute;width:\'+aC.width()+"px;height:"+aC.height()+"px;"+aJ+"background-color:"+aH+\';"> </div>\').prependTo(aL).css("opacity",P.legend.backgroundOpacity)}}}var ac=[],N=null;function L(aJ,aH,aE){var aP=P.grid.mouseActiveRadius,a1=aP*aP+1,aZ=null,aS=false,aX,aV;for(aX=R.length-1;aX>=0;--aX){if(!aE(R[aX])){continue}var aQ=R[aX],aI=aQ.xaxis,aG=aQ.yaxis,aW=aQ.datapoints.points,aU=aQ.datapoints.pointsize,aR=aI.c2p(aJ),aO=aG.c2p(aH),aD=aP/aI.scale,aC=aP/aG.scale;if(aI.options.inverseTransform){aD=Number.MAX_VALUE}if(aG.options.inverseTransform){aC=Number.MAX_VALUE}if(aQ.lines.show||aQ.points.show){for(aV=0;aV<aW.length;aV+=aU){var aL=aW[aV],aK=aW[aV+1];if(aL==null){continue}if(aL-aR>aD||aL-aR<-aD||aK-aO>aC||aK-aO<-aC){continue}var aN=Math.abs(aI.p2c(aL)-aJ),aM=Math.abs(aG.p2c(aK)-aH),aT=aN*aN+aM*aM;if(aT<a1){a1=aT;aZ=[aX,aV/aU]}}}if(aQ.bars.show&&!aZ){var aF=aQ.bars.align=="left"?0:-aQ.bars.barWidth/2,aY=aF+aQ.bars.barWidth;for(aV=0;aV<aW.length;aV+=aU){var aL=aW[aV],aK=aW[aV+1],a0=aW[aV+2];if(aL==null){continue}if(R[aX].bars.horizontal?(aR<=Math.max(a0,aL)&&aR>=Math.min(a0,aL)&&aO>=aK+aF&&aO<=aK+aY):(aR>=aL+aF&&aR<=aL+aY&&aO>=Math.min(a0,aK)&&aO<=Math.max(a0,aK))){aZ=[aX,aV/aU]}}}}if(aZ){aX=aZ[0];aV=aZ[1];aU=R[aX].datapoints.pointsize;return{datapoint:R[aX].datapoints.points.slice(aV*aU,(aV+1)*aU),dataIndex:aV,series:R[aX],seriesIndex:aX}}return null}function ab(aC){if(P.grid.hoverable){v("plothover",aC,function(aD){return aD.hoverable!=false})}}function l(aC){if(P.grid.hoverable){v("plothover",aC,function(aD){return false})}}function S(aC){v("plotclick",aC,function(aD){return aD.clickable!=false})}function v(aD,aC,aE){var aF=z.offset(),aI=aC.pageX-aF.left-r.left,aG=aC.pageY-aF.top-r.top,aK=D({left:aI,top:aG});aK.pageX=aC.pageX;aK.pageY=aC.pageY;var aL=L(aI,aG,aE);if(aL){aL.pageX=parseInt(aL.series.xaxis.p2c(aL.datapoint[0])+aF.left+r.left);aL.pageY=parseInt(aL.series.yaxis.p2c(aL.datapoint[1])+aF.top+r.top)}if(P.grid.autoHighlight){for(var aH=0;aH<ac.length;++aH){var aJ=ac[aH];if(aJ.auto==aD&&!(aL&&aJ.series==aL.series&&aJ.point[0]==aL.datapoint[0]&&aJ.point[1]==aL.datapoint[1])){U(aJ.series,aJ.point)}}if(aL){y(aL.series,aL.datapoint,aD)}}aw.trigger(aD,[aK,aL])}function f(){if(!N){N=setTimeout(t,30)}}function t(){N=null;B.save();B.clearRect(0,0,H,J);B.translate(r.left,r.top);var aD,aC;for(aD=0;aD<ac.length;++aD){aC=ac[aD];if(aC.series.bars.show){w(aC.series,aC.point)}else{az(aC.series,aC.point)}}B.restore();ao(al.drawOverlay,[B])}function y(aE,aC,aG){if(typeof aE=="number"){aE=R[aE]}if(typeof aC=="number"){var aF=aE.datapoints.pointsize;aC=aE.datapoints.points.slice(aF*aC,aF*(aC+1))}var aD=am(aE,aC);if(aD==-1){ac.push({series:aE,point:aC,auto:aG});f()}else{if(!aG){ac[aD].auto=false}}}function U(aE,aC){if(aE==null&&aC==null){ac=[];f()}if(typeof aE=="number"){aE=R[aE]}if(typeof aC=="number"){aC=aE.data[aC]}var aD=am(aE,aC);if(aD!=-1){ac.splice(aD,1);f()}}function am(aE,aF){for(var aC=0;aC<ac.length;++aC){var aD=ac[aC];if(aD.series==aE&&aD.point[0]==aF[0]&&aD.point[1]==aF[1]){return aC}}return -1}function az(aF,aE){var aD=aE[0],aJ=aE[1],aI=aF.xaxis,aH=aF.yaxis;if(aD<aI.min||aD>aI.max||aJ<aH.min||aJ>aH.max){return}var aG=aF.points.radius+aF.points.lineWidth/2;B.lineWidth=aG;B.strokeStyle=c.color.parse(aF.color).scale("a",0.5).toString();var aC=1.5*aG,aD=aI.p2c(aD),aJ=aH.p2c(aJ);B.beginPath();if(aF.points.symbol=="circle"){B.arc(aD,aJ,aC,0,2*Math.PI,false)}else{aF.points.symbol(B,aD,aJ,aC,false)}B.closePath();B.stroke()}function w(aF,aC){B.lineWidth=aF.bars.lineWidth;B.strokeStyle=c.color.parse(aF.color).scale("a",0.5).toString();var aE=c.color.parse(aF.color).scale("a",0.5).toString();var aD=aF.bars.align=="left"?0:-aF.bars.barWidth/2;F(aC[0],aC[1],aC[2]||0,aD,aD+aF.bars.barWidth,0,function(){return aE},aF.xaxis,aF.yaxis,B,aF.bars.horizontal,aF.bars.lineWidth)}function an(aK,aC,aI,aD){if(typeof aK=="string"){return aK}else{var aJ=I.createLinearGradient(0,aI,0,aC);for(var aF=0,aE=aK.colors.length;aF<aE;++aF){var aG=aK.colors[aF];if(typeof aG!="string"){var aH=c.color.parse(aD);if(aG.brightness!=null){aH=aH.scale("rgb",aG.brightness)}if(aG.opacity!=null){aH.a*=aG.opacity}aG=aH.toString()}aJ.addColorStop(aF/(aE-1),aG)}return aJ}}}c.plot=function(g,e,d){var f=new b(c(g),e,d,c.plot.plugins);return f};c.plot.version="0.7";c.plot.plugins=[];c.plot.formatDate=function(l,f,h){var p=function(d){d=""+d;return d.length==1?"0"+d:d};var e=[];var q=false,j=false;var o=l.getUTCHours();var k=o<12;if(h==null){h=["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]}if(f.search(/%p|%P/)!=-1){if(o>12){o=o-12}else{if(o==0){o=12}}}for(var g=0;g<f.length;++g){var n=f.charAt(g);if(q){switch(n){case"h":n=""+o;break;case"H":n=p(o);break;case"M":n=p(l.getUTCMinutes());break;case"S":n=p(l.getUTCSeconds());break;case"d":n=""+l.getUTCDate();break;case"m":n=""+(l.getUTCMonth()+1);break;case"y":n=""+l.getUTCFullYear();break;case"b":n=""+h[l.getUTCMonth()];break;case"p":n=(k)?("am"):("pm");break;case"P":n=(k)?("AM"):("PM");break;case"0":n="";j=true;break}if(n&&j){n=p(n);j=false}e.push(n);if(!j){q=false}}else{if(n=="%"){q=true}else{e.push(n)}}}return e.join("")};function a(e,d){return d*Math.floor(e/d)}})(jQuery);(function(b){var a={series:{stack:null}};function c(f){function d(k,j){var h=null;for(var g=0;g<j.length;++g){if(k==j[g]){break}if(j[g].stack==k.stack){h=j[g]}}return h}function e(C,v,g){if(v.stack==null){return}var p=d(v,C.getData());if(!p){return}var z=g.pointsize,F=g.points,h=p.datapoints.pointsize,y=p.datapoints.points,t=[],x,w,k,J,I,r,u=v.lines.show,G=v.bars.horizontal,o=z>2&&(G?g.format[2].x:g.format[2].y),n=u&&v.lines.steps,E=true,q=G?1:0,H=G?0:1,D=0,B=0,A;while(true){if(D>=F.length){break}A=t.length;if(F[D]==null){for(m=0;m<z;++m){t.push(F[D+m])}D+=z}else{if(B>=y.length){if(!u){for(m=0;m<z;++m){t.push(F[D+m])}}D+=z}else{if(y[B]==null){for(m=0;m<z;++m){t.push(null)}E=true;B+=h}else{x=F[D+q];w=F[D+H];J=y[B+q];I=y[B+H];r=0;if(x==J){for(m=0;m<z;++m){t.push(F[D+m])}t[A+H]+=I;r=I;D+=z;B+=h}else{if(x>J){if(u&&D>0&&F[D-z]!=null){k=w+(F[D-z+H]-w)*(J-x)/(F[D-z+q]-x);t.push(J);t.push(k+I);for(m=2;m<z;++m){t.push(F[D+m])}r=I}B+=h}else{if(E&&u){D+=z;continue}for(m=0;m<z;++m){t.push(F[D+m])}if(u&&B>0&&y[B-h]!=null){r=I+(y[B-h+H]-I)*(x-J)/(y[B-h+q]-J)}t[A+H]+=r;D+=z}}E=false;if(A!=t.length&&o){t[A+2]+=r}}}}if(n&&A!=t.length&&A>0&&t[A]!=null&&t[A]!=t[A-z]&&t[A+1]!=t[A-z+1]){for(m=0;m<z;++m){t[A+z+m]=t[A+m]}t[A+1]=t[A-z+1]}}g.points=t}f.hooks.processDatapoints.push(e)}b.plot.plugins.push({init:c,options:a,name:"stack",version:"1.2"})})(jQuery);
(function(b){function c(D){var h=null;var L=null;var n=null;var B=null;var p=null;var M=0;var F=true;var o=10;var w=0.95;var A=0;var d=false;var z=false;var j=[];D.hooks.processOptions.push(g);D.hooks.bindEvents.push(e);function g(O,N){if(N.series.pie.show){N.grid.show=false;if(N.series.pie.label.show=="auto"){if(N.legend.show){N.series.pie.label.show=false}else{N.series.pie.label.show=true}}if(N.series.pie.radius=="auto"){if(N.series.pie.label.show){N.series.pie.radius=3/4}else{N.series.pie.radius=1}}if(N.series.pie.tilt>1){N.series.pie.tilt=1}if(N.series.pie.tilt<0){N.series.pie.tilt=0}O.hooks.processDatapoints.push(E);O.hooks.drawOverlay.push(H);O.hooks.draw.push(r)}}function e(P,N){var O=P.getOptions();if(O.series.pie.show&&O.grid.hoverable){N.unbind("mousemove").mousemove(t)}if(O.series.pie.show&&O.grid.clickable){N.unbind("click").click(l)}}function G(O){var P="";function N(S,T){if(!T){T=0}for(var R=0;R<S.length;++R){for(var Q=0;Q<T;Q++){P+="\\t"}if(typeof S[R]=="object"){P+=""+R+":\\n";N(S[R],T+1)}else{P+=""+R+": "+S[R]+"\\n"}}}N(O);alert(P)}function q(P){for(var N=0;N<P.length;++N){var O=parseFloat(P[N].data[0][1]);if(O){M+=O}}}function E(Q,N,O,P){if(!d){d=true;h=Q.getCanvas();L=b(h).parent();a=Q.getOptions();Q.setData(K(Q.getData()))}}function I(){A=L.children().filter(".legend").children().width();n=Math.min(h.width,(h.height/a.series.pie.tilt))/2;p=(h.height/2)+a.series.pie.offset.top;B=(h.width/2);if(a.series.pie.offset.left=="auto"){if(a.legend.position.match("w")){B+=A/2}else{B-=A/2}}else{B+=a.series.pie.offset.left}if(B<n){B=n}else{if(B>h.width-n){B=h.width-n}}}function v(O){for(var N=0;N<O.length;++N){if(typeof(O[N].data)=="number"){O[N].data=[[1,O[N].data]]}else{if(typeof(O[N].data)=="undefined"||typeof(O[N].data[0])=="undefined"){if(typeof(O[N].data)!="undefined"&&typeof(O[N].data.label)!="undefined"){O[N].label=O[N].data.label}O[N].data=[[1,0]]}}}return O}function K(Q){Q=v(Q);q(Q);var P=0;var S=0;var N=a.series.pie.combine.color;var R=[];for(var O=0;O<Q.length;++O){Q[O].data[0][1]=parseFloat(Q[O].data[0][1]);if(!Q[O].data[0][1]){Q[O].data[0][1]=0}if(Q[O].data[0][1]/M<=a.series.pie.combine.threshold){P+=Q[O].data[0][1];S++;if(!N){N=Q[O].color}}else{R.push({data:[[1,Q[O].data[0][1]]],color:Q[O].color,label:Q[O].label,angle:(Q[O].data[0][1]*(Math.PI*2))/M,percent:(Q[O].data[0][1]/M*100)})}}if(S>0){R.push({data:[[1,P]],color:N,label:a.series.pie.combine.label,angle:(P*(Math.PI*2))/M,percent:(P/M*100)})}return R}function r(S,Q){if(!L){return}ctx=Q;I();var T=S.getData();var P=0;while(F&&P<o){F=false;if(P>0){n*=w}P+=1;N();if(a.series.pie.tilt<=0.8){O()}R()}if(P>=o){N();L.prepend(\'<div class="error">Could not draw pie with labels contained inside canvas</div>\')}if(S.setSeries&&S.insertLegend){S.setSeries(T);S.insertLegend()}function N(){ctx.clearRect(0,0,h.width,h.height);L.children().filter(".pieLabel, .pieLabelBackground").remove()}function O(){var Z=5;var Y=15;var W=10;var X=0.02;if(a.series.pie.radius>1){var U=a.series.pie.radius}else{var U=n*a.series.pie.radius}if(U>=(h.width/2)-Z||U*a.series.pie.tilt>=(h.height/2)-Y||U<=W){return}ctx.save();ctx.translate(Z,Y);ctx.globalAlpha=X;ctx.fillStyle="#000";ctx.translate(B,p);ctx.scale(1,a.series.pie.tilt);for(var V=1;V<=W;V++){ctx.beginPath();ctx.arc(0,0,U,0,Math.PI*2,false);ctx.fill();U-=V}ctx.restore()}function R(){startAngle=Math.PI*a.series.pie.startAngle;if(a.series.pie.radius>1){var U=a.series.pie.radius}else{var U=n*a.series.pie.radius}ctx.save();ctx.translate(B,p);ctx.scale(1,a.series.pie.tilt);ctx.save();var Y=startAngle;for(var W=0;W<T.length;++W){T[W].startAngle=Y;X(T[W].angle,T[W].color,true)}ctx.restore();ctx.save();ctx.lineWidth=a.series.pie.stroke.width;Y=startAngle;for(var W=0;W<T.length;++W){X(T[W].angle,a.series.pie.stroke.color,false)}ctx.restore();J(ctx);if(a.series.pie.label.show){V()}ctx.restore();function X(ab,Z,aa){if(ab<=0){return}if(aa){ctx.fillStyle=Z}else{ctx.strokeStyle=Z;ctx.lineJoin="round"}ctx.beginPath();if(Math.abs(ab-Math.PI*2)>1e-9){ctx.moveTo(0,0)}else{if(b.browser.msie){ab-=0.0001}}ctx.arc(0,0,U,Y,Y+ab,false);ctx.closePath();Y+=ab;if(aa){ctx.fill()}else{ctx.stroke()}}function V(){var ac=startAngle;if(a.series.pie.label.radius>1){var Z=a.series.pie.label.radius}else{var Z=n*a.series.pie.label.radius}for(var ab=0;ab<T.length;++ab){if(T[ab].percent>=a.series.pie.label.threshold*100){aa(T[ab],ac,ab)}ac+=T[ab].angle}function aa(ap,ai,ag){if(ap.data[0][1]==0){return}var ar=a.legend.labelFormatter,aq,ae=a.series.pie.label.formatter;if(ar){aq=ar(ap.label,ap)}else{aq=ap.label}if(ae){aq=ae(aq,ap)}var aj=((ai+ap.angle)+ai)/2;var ao=B+Math.round(Math.cos(aj)*Z);var am=p+Math.round(Math.sin(aj)*Z)*a.series.pie.tilt;var af=\'<span class="pieLabel" id="pieLabel\'+ag+\'" style="position:absolute;top:\'+am+"px;left:"+ao+\'px;">\'+aq+"</span>";L.append(af);var an=L.children("#pieLabel"+ag);var ad=(am-an.height()/2);var ah=(ao-an.width()/2);an.css("top",ad);an.css("left",ah);if(0-ad>0||0-ah>0||h.height-(ad+an.height())<0||h.width-(ah+an.width())<0){F=true}if(a.series.pie.label.background.opacity!=0){var ak=a.series.pie.label.background.color;if(ak==null){ak=ap.color}var al="top:"+ad+"px;left:"+ah+"px;";b(\'<div class="pieLabelBackground" style="position:absolute;width:\'+an.width()+"px;height:"+an.height()+"px;"+al+"background-color:"+ak+\';"> </div>\').insertBefore(an).css("opacity",a.series.pie.label.background.opacity)}}}}}function J(N){if(a.series.pie.innerRadius>0){N.save();innerRadius=a.series.pie.innerRadius>1?a.series.pie.innerRadius:n*a.series.pie.innerRadius;N.globalCompositeOperation="destination-out";N.beginPath();N.fillStyle=a.series.pie.stroke.color;N.arc(0,0,innerRadius,0,Math.PI*2,false);N.fill();N.closePath();N.restore();N.save();N.beginPath();N.strokeStyle=a.series.pie.stroke.color;N.arc(0,0,innerRadius,0,Math.PI*2,false);N.stroke();N.closePath();N.restore()}}function s(Q,R){for(var S=false,P=-1,N=Q.length,O=N-1;++P<N;O=P){((Q[P][1]<=R[1]&&R[1]<Q[O][1])||(Q[O][1]<=R[1]&&R[1]<Q[P][1]))&&(R[0]<(Q[O][0]-Q[P][0])*(R[1]-Q[P][1])/(Q[O][1]-Q[P][1])+Q[P][0])&&(S=!S)}return S}function u(R,P){var T=D.getData(),O=D.getOptions(),N=O.series.pie.radius>1?O.series.pie.radius:n*O.series.pie.radius;for(var Q=0;Q<T.length;++Q){var S=T[Q];if(S.pie.show){ctx.save();ctx.beginPath();ctx.moveTo(0,0);ctx.arc(0,0,N,S.startAngle,S.startAngle+S.angle,false);ctx.closePath();x=R-B;y=P-p;if(ctx.isPointInPath){if(ctx.isPointInPath(R-B,P-p)){ctx.restore();return{datapoint:[S.percent,S.data],dataIndex:0,series:S,seriesIndex:Q}}}else{p1X=(N*Math.cos(S.startAngle));p1Y=(N*Math.sin(S.startAngle));p2X=(N*Math.cos(S.startAngle+(S.angle/4)));p2Y=(N*Math.sin(S.startAngle+(S.angle/4)));p3X=(N*Math.cos(S.startAngle+(S.angle/2)));p3Y=(N*Math.sin(S.startAngle+(S.angle/2)));p4X=(N*Math.cos(S.startAngle+(S.angle/1.5)));p4Y=(N*Math.sin(S.startAngle+(S.angle/1.5)));p5X=(N*Math.cos(S.startAngle+S.angle));p5Y=(N*Math.sin(S.startAngle+S.angle));arrPoly=[[0,0],[p1X,p1Y],[p2X,p2Y],[p3X,p3Y],[p4X,p4Y],[p5X,p5Y]];arrPoint=[x,y];if(s(arrPoly,arrPoint)){ctx.restore();return{datapoint:[S.percent,S.data],dataIndex:0,series:S,seriesIndex:Q}}}ctx.restore()}}return null}function t(N){m("plothover",N)}function l(N){m("plotclick",N)}function m(N,T){var O=D.offset(),R=parseInt(T.pageX-O.left),P=parseInt(T.pageY-O.top),V=u(R,P);if(a.grid.autoHighlight){for(var Q=0;Q<j.length;++Q){var S=j[Q];if(S.auto==N&&!(V&&S.series==V.series)){f(S.series)}}}if(V){k(V.series,N)}var U={pageX:T.pageX,pageY:T.pageY};L.trigger(N,[U,V])}function k(O,P){if(typeof O=="number"){O=series[O]}var N=C(O);if(N==-1){j.push({series:O,auto:P});D.triggerRedrawOverlay()}else{if(!P){j[N].auto=false}}}function f(O){if(O==null){j=[];D.triggerRedrawOverlay()}if(typeof O=="number"){O=series[O]}var N=C(O);if(N!=-1){j.splice(N,1);D.triggerRedrawOverlay()}}function C(P){for(var N=0;N<j.length;++N){var O=j[N];if(O.series==P){return N}}return -1}function H(Q,R){var P=Q.getOptions();var N=P.series.pie.radius>1?P.series.pie.radius:n*P.series.pie.radius;R.save();R.translate(B,p);R.scale(1,P.series.pie.tilt);for(i=0;i<j.length;++i){O(j[i].series)}J(R);R.restore();function O(S){if(S.angle<0){return}R.fillStyle="rgba(255, 255, 255, "+P.series.pie.highlight.opacity+")";R.beginPath();if(Math.abs(S.angle-Math.PI*2)>1e-9){R.moveTo(0,0)}R.arc(0,0,N,S.startAngle,S.startAngle+S.angle,false);R.closePath();R.fill()}}}var a={series:{pie:{show:false,radius:"auto",innerRadius:0,startAngle:3/2,tilt:1,offset:{top:0,left:"auto"},stroke:{color:"#FFF",width:1},label:{show:"auto",formatter:function(d,e){return\'<div style="font-size:x-small;text-align:center;padding:2px;color:\'+e.color+\';">\'+d+"<br/>"+Math.round(e.percent)+"%</div>"},radius:1,background:{color:null,opacity:0},threshold:0},combine:{threshold:-1,color:null,label:"Other"},highlight:{opacity:0.5}}}};b.plot.plugins.push({init:c,options:a,name:"pie",version:"1.0"})})(jQuery);'''

ui = '''/*!\n * jQuery UI 1.8.9\n *\n * Copyright 2011, AUTHORS.txt (http://jqueryui.com/about)\n * Dual licensed under the MIT or GPL Version 2 licenses.\n * http://jquery.org/license\n *\n * http://docs.jquery.com/UI\n */\n(function(b,c){function f(g){return!b(g).parents().andSelf().filter(function(){return b.curCSS(this,"visibility")==="hidden"||b.expr.filters.hidden(this)}).length}b.ui=b.ui||{};if(!b.ui.version){b.extend(b.ui,{version:"1.8.9",keyCode:{ALT:18,BACKSPACE:8,CAPS_LOCK:20,COMMA:188,COMMAND:91,COMMAND_LEFT:91,COMMAND_RIGHT:93,CONTROL:17,DELETE:46,DOWN:40,END:35,ENTER:13,ESCAPE:27,HOME:36,INSERT:45,LEFT:37,MENU:93,NUMPAD_ADD:107,NUMPAD_DECIMAL:110,NUMPAD_DIVIDE:111,NUMPAD_ENTER:108,NUMPAD_MULTIPLY:106,\nNUMPAD_SUBTRACT:109,PAGE_DOWN:34,PAGE_UP:33,PERIOD:190,RIGHT:39,SHIFT:16,SPACE:32,TAB:9,UP:38,WINDOWS:91}});b.fn.extend({_focus:b.fn.focus,focus:function(g,e){return typeof g==="number"?this.each(function(){var a=this;setTimeout(function(){b(a).focus();e&&e.call(a)},g)}):this._focus.apply(this,arguments)},scrollParent:function(){var g;g=b.browser.msie&&/(static|relative)/.test(this.css("position"))||/absolute/.test(this.css("position"))?this.parents().filter(function(){return/(relative|absolute|fixed)/.test(b.curCSS(this,\n"position",1))&&/(auto|scroll)/.test(b.curCSS(this,"overflow",1)+b.curCSS(this,"overflow-y",1)+b.curCSS(this,"overflow-x",1))}).eq(0):this.parents().filter(function(){return/(auto|scroll)/.test(b.curCSS(this,"overflow",1)+b.curCSS(this,"overflow-y",1)+b.curCSS(this,"overflow-x",1))}).eq(0);return/fixed/.test(this.css("position"))||!g.length?b(document):g},zIndex:function(g){if(g!==c)return this.css("zIndex",g);if(this.length){g=b(this[0]);for(var e;g.length&&g[0]!==document;){e=g.css("position");\nif(e==="absolute"||e==="relative"||e==="fixed"){e=parseInt(g.css("zIndex"),10);if(!isNaN(e)&&e!==0)return e}g=g.parent()}}return 0},disableSelection:function(){return this.bind((b.support.selectstart?"selectstart":"mousedown")+".ui-disableSelection",function(g){g.preventDefault()})},enableSelection:function(){return this.unbind(".ui-disableSelection")}});b.each(["Width","Height"],function(g,e){function a(j,n,q,l){b.each(d,function(){n-=parseFloat(b.curCSS(j,"padding"+this,true))||0;if(q)n-=parseFloat(b.curCSS(j,\n"border"+this+"Width",true))||0;if(l)n-=parseFloat(b.curCSS(j,"margin"+this,true))||0});return n}var d=e==="Width"?["Left","Right"]:["Top","Bottom"],h=e.toLowerCase(),i={innerWidth:b.fn.innerWidth,innerHeight:b.fn.innerHeight,outerWidth:b.fn.outerWidth,outerHeight:b.fn.outerHeight};b.fn["inner"+e]=function(j){if(j===c)return i["inner"+e].call(this);return this.each(function(){b(this).css(h,a(this,j)+"px")})};b.fn["outer"+e]=function(j,n){if(typeof j!=="number")return i["outer"+e].call(this,j);return this.each(function(){b(this).css(h,\na(this,j,true,n)+"px")})}});b.extend(b.expr[":"],{data:function(g,e,a){return!!b.data(g,a[3])},focusable:function(g){var e=g.nodeName.toLowerCase(),a=b.attr(g,"tabindex");if("area"===e){e=g.parentNode;a=e.name;if(!g.href||!a||e.nodeName.toLowerCase()!=="map")return false;g=b("img[usemap=#"+a+"]")[0];return!!g&&f(g)}return(/input|select|textarea|button|object/.test(e)?!g.disabled:"a"==e?g.href||!isNaN(a):!isNaN(a))&&f(g)},tabbable:function(g){var e=b.attr(g,"tabindex");return(isNaN(e)||e>=0)&&b(g).is(":focusable")}});\nb(function(){var g=document.body,e=g.appendChild(e=document.createElement("div"));b.extend(e.style,{minHeight:"100px",height:"auto",padding:0,borderWidth:0});b.support.minHeight=e.offsetHeight===100;b.support.selectstart="onselectstart"in e;g.removeChild(e).style.display="none"});b.extend(b.ui,{plugin:{add:function(g,e,a){g=b.ui[g].prototype;for(var d in a){g.plugins[d]=g.plugins[d]||[];g.plugins[d].push([e,a[d]])}},call:function(g,e,a){if((e=g.plugins[e])&&g.element[0].parentNode)for(var d=0;d<e.length;d++)g.options[e[d][0]]&&\ne[d][1].apply(g.element,a)}},contains:function(g,e){return document.compareDocumentPosition?g.compareDocumentPosition(e)&16:g!==e&&g.contains(e)},hasScroll:function(g,e){if(b(g).css("overflow")==="hidden")return false;e=e&&e==="left"?"scrollLeft":"scrollTop";var a=false;if(g[e]>0)return true;g[e]=1;a=g[e]>0;g[e]=0;return a},isOverAxis:function(g,e,a){return g>e&&g<e+a},isOver:function(g,e,a,d,h,i){return b.ui.isOverAxis(g,a,h)&&b.ui.isOverAxis(e,d,i)}})}})(jQuery);\n(function(b,c){if(b.cleanData){var f=b.cleanData;b.cleanData=function(e){for(var a=0,d;(d=e[a])!=null;a++)b(d).triggerHandler("remove");f(e)}}else{var g=b.fn.remove;b.fn.remove=function(e,a){return this.each(function(){if(!a)if(!e||b.filter(e,[this]).length)b("*",this).add([this]).each(function(){b(this).triggerHandler("remove")});return g.call(b(this),e,a)})}}b.widget=function(e,a,d){var h=e.split(".")[0],i;e=e.split(".")[1];i=h+"-"+e;if(!d){d=a;a=b.Widget}b.expr[":"][i]=function(j){return!!b.data(j,\ne)};b[h]=b[h]||{};b[h][e]=function(j,n){arguments.length&&this._createWidget(j,n)};a=new a;a.options=b.extend(true,{},a.options);b[h][e].prototype=b.extend(true,a,{namespace:h,widgetName:e,widgetEventPrefix:b[h][e].prototype.widgetEventPrefix||e,widgetBaseClass:i},d);b.widget.bridge(e,b[h][e])};b.widget.bridge=function(e,a){b.fn[e]=function(d){var h=typeof d==="string",i=Array.prototype.slice.call(arguments,1),j=this;d=!h&&i.length?b.extend.apply(null,[true,d].concat(i)):d;if(h&&d.charAt(0)==="_")return j;\nh?this.each(function(){var n=b.data(this,e),q=n&&b.isFunction(n[d])?n[d].apply(n,i):n;if(q!==n&&q!==c){j=q;return false}}):this.each(function(){var n=b.data(this,e);n?n.option(d||{})._init():b.data(this,e,new a(d,this))});return j}};b.Widget=function(e,a){arguments.length&&this._createWidget(e,a)};b.Widget.prototype={widgetName:"widget",widgetEventPrefix:"",options:{disabled:false},_createWidget:function(e,a){b.data(a,this.widgetName,this);this.element=b(a);this.options=b.extend(true,{},this.options,\nthis._getCreateOptions(),e);var d=this;this.element.bind("remove."+this.widgetName,function(){d.destroy()});this._create();this._trigger("create");this._init()},_getCreateOptions:function(){return b.metadata&&b.metadata.get(this.element[0])[this.widgetName]},_create:function(){},_init:function(){},destroy:function(){this.element.unbind("."+this.widgetName).removeData(this.widgetName);this.widget().unbind("."+this.widgetName).removeAttr("aria-disabled").removeClass(this.widgetBaseClass+"-disabled ui-state-disabled")},\nwidget:function(){return this.element},option:function(e,a){var d=e;if(arguments.length===0)return b.extend({},this.options);if(typeof e==="string"){if(a===c)return this.options[e];d={};d[e]=a}this._setOptions(d);return this},_setOptions:function(e){var a=this;b.each(e,function(d,h){a._setOption(d,h)});return this},_setOption:function(e,a){this.options[e]=a;if(e==="disabled")this.widget()[a?"addClass":"removeClass"](this.widgetBaseClass+"-disabled ui-state-disabled").attr("aria-disabled",a);return this},\nenable:function(){return this._setOption("disabled",false)},disable:function(){return this._setOption("disabled",true)},_trigger:function(e,a,d){var h=this.options[e];a=b.Event(a);a.type=(e===this.widgetEventPrefix?e:this.widgetEventPrefix+e).toLowerCase();d=d||{};if(a.originalEvent){e=b.event.props.length;for(var i;e;){i=b.event.props[--e];a[i]=a.originalEvent[i]}}this.element.trigger(a,d);return!(b.isFunction(h)&&h.call(this.element[0],a,d)===false||a.isDefaultPrevented())}}})(jQuery);\n(function(b){b.widget("ui.mouse",{options:{cancel:":input,option",distance:1,delay:0},_mouseInit:function(){var c=this;this.element.bind("mousedown."+this.widgetName,function(f){return c._mouseDown(f)}).bind("click."+this.widgetName,function(f){if(true===b.data(f.target,c.widgetName+".preventClickEvent")){b.removeData(f.target,c.widgetName+".preventClickEvent");f.stopImmediatePropagation();return false}});this.started=false},_mouseDestroy:function(){this.element.unbind("."+this.widgetName)},_mouseDown:function(c){c.originalEvent=\nc.originalEvent||{};if(!c.originalEvent.mouseHandled){this._mouseStarted&&this._mouseUp(c);this._mouseDownEvent=c;var f=this,g=c.which==1,e=typeof this.options.cancel=="string"?b(c.target).parents().add(c.target).filter(this.options.cancel).length:false;if(!g||e||!this._mouseCapture(c))return true;this.mouseDelayMet=!this.options.delay;if(!this.mouseDelayMet)this._mouseDelayTimer=setTimeout(function(){f.mouseDelayMet=true},this.options.delay);if(this._mouseDistanceMet(c)&&this._mouseDelayMet(c)){this._mouseStarted=\nthis._mouseStart(c)!==false;if(!this._mouseStarted){c.preventDefault();return true}}this._mouseMoveDelegate=function(a){return f._mouseMove(a)};this._mouseUpDelegate=function(a){return f._mouseUp(a)};b(document).bind("mousemove."+this.widgetName,this._mouseMoveDelegate).bind("mouseup."+this.widgetName,this._mouseUpDelegate);c.preventDefault();return c.originalEvent.mouseHandled=true}},_mouseMove:function(c){if(b.browser.msie&&!(document.documentMode>=9)&&!c.button)return this._mouseUp(c);if(this._mouseStarted){this._mouseDrag(c);\nreturn c.preventDefault()}if(this._mouseDistanceMet(c)&&this._mouseDelayMet(c))(this._mouseStarted=this._mouseStart(this._mouseDownEvent,c)!==false)?this._mouseDrag(c):this._mouseUp(c);return!this._mouseStarted},_mouseUp:function(c){b(document).unbind("mousemove."+this.widgetName,this._mouseMoveDelegate).unbind("mouseup."+this.widgetName,this._mouseUpDelegate);if(this._mouseStarted){this._mouseStarted=false;c.target==this._mouseDownEvent.target&&b.data(c.target,this.widgetName+".preventClickEvent",\ntrue);this._mouseStop(c)}return false},_mouseDistanceMet:function(c){return Math.max(Math.abs(this._mouseDownEvent.pageX-c.pageX),Math.abs(this._mouseDownEvent.pageY-c.pageY))>=this.options.distance},_mouseDelayMet:function(){return this.mouseDelayMet},_mouseStart:function(){},_mouseDrag:function(){},_mouseStop:function(){},_mouseCapture:function(){return true}})})(jQuery);\n(function(b){b.widget("ui.draggable",b.ui.mouse,{widgetEventPrefix:"drag",options:{addClasses:true,appendTo:"parent",axis:false,connectToSortable:false,containment:false,cursor:"auto",cursorAt:false,grid:false,handle:false,helper:"original",iframeFix:false,opacity:false,refreshPositions:false,revert:false,revertDuration:500,scope:"default",scroll:true,scrollSensitivity:20,scrollSpeed:20,snap:false,snapMode:"both",snapTolerance:20,stack:false,zIndex:false},_create:function(){if(this.options.helper==\n"original"&&!/^(?:r|a|f)/.test(this.element.css("position")))this.element[0].style.position="relative";this.options.addClasses&&this.element.addClass("ui-draggable");this.options.disabled&&this.element.addClass("ui-draggable-disabled");this._mouseInit()},destroy:function(){if(this.element.data("draggable")){this.element.removeData("draggable").unbind(".draggable").removeClass("ui-draggable ui-draggable-dragging ui-draggable-disabled");this._mouseDestroy();return this}},_mouseCapture:function(c){var f=\nthis.options;if(this.helper||f.disabled||b(c.target).is(".ui-resizable-handle"))return false;this.handle=this._getHandle(c);if(!this.handle)return false;return true},_mouseStart:function(c){var f=this.options;this.helper=this._createHelper(c);this._cacheHelperProportions();if(b.ui.ddmanager)b.ui.ddmanager.current=this;this._cacheMargins();this.cssPosition=this.helper.css("position");this.scrollParent=this.helper.scrollParent();this.offset=this.positionAbs=this.element.offset();this.offset={top:this.offset.top-\nthis.margins.top,left:this.offset.left-this.margins.left};b.extend(this.offset,{click:{left:c.pageX-this.offset.left,top:c.pageY-this.offset.top},parent:this._getParentOffset(),relative:this._getRelativeOffset()});this.originalPosition=this.position=this._generatePosition(c);this.originalPageX=c.pageX;this.originalPageY=c.pageY;f.cursorAt&&this._adjustOffsetFromHelper(f.cursorAt);f.containment&&this._setContainment();if(this._trigger("start",c)===false){this._clear();return false}this._cacheHelperProportions();\nb.ui.ddmanager&&!f.dropBehaviour&&b.ui.ddmanager.prepareOffsets(this,c);this.helper.addClass("ui-draggable-dragging");this._mouseDrag(c,true);return true},_mouseDrag:function(c,f){this.position=this._generatePosition(c);this.positionAbs=this._convertPositionTo("absolute");if(!f){f=this._uiHash();if(this._trigger("drag",c,f)===false){this._mouseUp({});return false}this.position=f.position}if(!this.options.axis||this.options.axis!="y")this.helper[0].style.left=this.position.left+"px";if(!this.options.axis||\nthis.options.axis!="x")this.helper[0].style.top=this.position.top+"px";b.ui.ddmanager&&b.ui.ddmanager.drag(this,c);return false},_mouseStop:function(c){var f=false;if(b.ui.ddmanager&&!this.options.dropBehaviour)f=b.ui.ddmanager.drop(this,c);if(this.dropped){f=this.dropped;this.dropped=false}if((!this.element[0]||!this.element[0].parentNode)&&this.options.helper=="original")return false;if(this.options.revert=="invalid"&&!f||this.options.revert=="valid"&&f||this.options.revert===true||b.isFunction(this.options.revert)&&\nthis.options.revert.call(this.element,f)){var g=this;b(this.helper).animate(this.originalPosition,parseInt(this.options.revertDuration,10),function(){g._trigger("stop",c)!==false&&g._clear()})}else this._trigger("stop",c)!==false&&this._clear();return false},cancel:function(){this.helper.is(".ui-draggable-dragging")?this._mouseUp({}):this._clear();return this},_getHandle:function(c){var f=!this.options.handle||!b(this.options.handle,this.element).length?true:false;b(this.options.handle,this.element).find("*").andSelf().each(function(){if(this==\nc.target)f=true});return f},_createHelper:function(c){var f=this.options;c=b.isFunction(f.helper)?b(f.helper.apply(this.element[0],[c])):f.helper=="clone"?this.element.clone():this.element;c.parents("body").length||c.appendTo(f.appendTo=="parent"?this.element[0].parentNode:f.appendTo);c[0]!=this.element[0]&&!/(fixed|absolute)/.test(c.css("position"))&&c.css("position","absolute");return c},_adjustOffsetFromHelper:function(c){if(typeof c=="string")c=c.split(" ");if(b.isArray(c))c={left:+c[0],top:+c[1]||\n0};if("left"in c)this.offset.click.left=c.left+this.margins.left;if("right"in c)this.offset.click.left=this.helperProportions.width-c.right+this.margins.left;if("top"in c)this.offset.click.top=c.top+this.margins.top;if("bottom"in c)this.offset.click.top=this.helperProportions.height-c.bottom+this.margins.top},_getParentOffset:function(){this.offsetParent=this.helper.offsetParent();var c=this.offsetParent.offset();if(this.cssPosition=="absolute"&&this.scrollParent[0]!=document&&b.ui.contains(this.scrollParent[0],\nthis.offsetParent[0])){c.left+=this.scrollParent.scrollLeft();c.top+=this.scrollParent.scrollTop()}if(this.offsetParent[0]==document.body||this.offsetParent[0].tagName&&this.offsetParent[0].tagName.toLowerCase()=="html"&&b.browser.msie)c={top:0,left:0};return{top:c.top+(parseInt(this.offsetParent.css("borderTopWidth"),10)||0),left:c.left+(parseInt(this.offsetParent.css("borderLeftWidth"),10)||0)}},_getRelativeOffset:function(){if(this.cssPosition=="relative"){var c=this.element.position();return{top:c.top-\n(parseInt(this.helper.css("top"),10)||0)+this.scrollParent.scrollTop(),left:c.left-(parseInt(this.helper.css("left"),10)||0)+this.scrollParent.scrollLeft()}}else return{top:0,left:0}},_cacheMargins:function(){this.margins={left:parseInt(this.element.css("marginLeft"),10)||0,top:parseInt(this.element.css("marginTop"),10)||0}},_cacheHelperProportions:function(){this.helperProportions={width:this.helper.outerWidth(),height:this.helper.outerHeight()}},_setContainment:function(){var c=this.options;if(c.containment==\n"parent")c.containment=this.helper[0].parentNode;if(c.containment=="document"||c.containment=="window")this.containment=[(c.containment=="document"?0:b(window).scrollLeft())-this.offset.relative.left-this.offset.parent.left,(c.containment=="document"?0:b(window).scrollTop())-this.offset.relative.top-this.offset.parent.top,(c.containment=="document"?0:b(window).scrollLeft())+b(c.containment=="document"?document:window).width()-this.helperProportions.width-this.margins.left,(c.containment=="document"?\n0:b(window).scrollTop())+(b(c.containment=="document"?document:window).height()||document.body.parentNode.scrollHeight)-this.helperProportions.height-this.margins.top];if(!/^(document|window|parent)$/.test(c.containment)&&c.containment.constructor!=Array){var f=b(c.containment)[0];if(f){c=b(c.containment).offset();var g=b(f).css("overflow")!="hidden";this.containment=[c.left+(parseInt(b(f).css("borderLeftWidth"),10)||0)+(parseInt(b(f).css("paddingLeft"),10)||0)-this.margins.left,c.top+(parseInt(b(f).css("borderTopWidth"),\n10)||0)+(parseInt(b(f).css("paddingTop"),10)||0)-this.margins.top,c.left+(g?Math.max(f.scrollWidth,f.offsetWidth):f.offsetWidth)-(parseInt(b(f).css("borderLeftWidth"),10)||0)-(parseInt(b(f).css("paddingRight"),10)||0)-this.helperProportions.width-this.margins.left,c.top+(g?Math.max(f.scrollHeight,f.offsetHeight):f.offsetHeight)-(parseInt(b(f).css("borderTopWidth"),10)||0)-(parseInt(b(f).css("paddingBottom"),10)||0)-this.helperProportions.height-this.margins.top]}}else if(c.containment.constructor==\nArray)this.containment=c.containment},_convertPositionTo:function(c,f){if(!f)f=this.position;c=c=="absolute"?1:-1;var g=this.cssPosition=="absolute"&&!(this.scrollParent[0]!=document&&b.ui.contains(this.scrollParent[0],this.offsetParent[0]))?this.offsetParent:this.scrollParent,e=/(html|body)/i.test(g[0].tagName);return{top:f.top+this.offset.relative.top*c+this.offset.parent.top*c-(b.browser.safari&&b.browser.version<526&&this.cssPosition=="fixed"?0:(this.cssPosition=="fixed"?-this.scrollParent.scrollTop():\ne?0:g.scrollTop())*c),left:f.left+this.offset.relative.left*c+this.offset.parent.left*c-(b.browser.safari&&b.browser.version<526&&this.cssPosition=="fixed"?0:(this.cssPosition=="fixed"?-this.scrollParent.scrollLeft():e?0:g.scrollLeft())*c)}},_generatePosition:function(c){var f=this.options,g=this.cssPosition=="absolute"&&!(this.scrollParent[0]!=document&&b.ui.contains(this.scrollParent[0],this.offsetParent[0]))?this.offsetParent:this.scrollParent,e=/(html|body)/i.test(g[0].tagName),a=c.pageX,d=c.pageY;\nif(this.originalPosition){if(this.containment){if(c.pageX-this.offset.click.left<this.containment[0])a=this.containment[0]+this.offset.click.left;if(c.pageY-this.offset.click.top<this.containment[1])d=this.containment[1]+this.offset.click.top;if(c.pageX-this.offset.click.left>this.containment[2])a=this.containment[2]+this.offset.click.left;if(c.pageY-this.offset.click.top>this.containment[3])d=this.containment[3]+this.offset.click.top}if(f.grid){d=this.originalPageY+Math.round((d-this.originalPageY)/\nf.grid[1])*f.grid[1];d=this.containment?!(d-this.offset.click.top<this.containment[1]||d-this.offset.click.top>this.containment[3])?d:!(d-this.offset.click.top<this.containment[1])?d-f.grid[1]:d+f.grid[1]:d;a=this.originalPageX+Math.round((a-this.originalPageX)/f.grid[0])*f.grid[0];a=this.containment?!(a-this.offset.click.left<this.containment[0]||a-this.offset.click.left>this.containment[2])?a:!(a-this.offset.click.left<this.containment[0])?a-f.grid[0]:a+f.grid[0]:a}}return{top:d-this.offset.click.top-\nthis.offset.relative.top-this.offset.parent.top+(b.browser.safari&&b.browser.version<526&&this.cssPosition=="fixed"?0:this.cssPosition=="fixed"?-this.scrollParent.scrollTop():e?0:g.scrollTop()),left:a-this.offset.click.left-this.offset.relative.left-this.offset.parent.left+(b.browser.safari&&b.browser.version<526&&this.cssPosition=="fixed"?0:this.cssPosition=="fixed"?-this.scrollParent.scrollLeft():e?0:g.scrollLeft())}},_clear:function(){this.helper.removeClass("ui-draggable-dragging");this.helper[0]!=\nthis.element[0]&&!this.cancelHelperRemoval&&this.helper.remove();this.helper=null;this.cancelHelperRemoval=false},_trigger:function(c,f,g){g=g||this._uiHash();b.ui.plugin.call(this,c,[f,g]);if(c=="drag")this.positionAbs=this._convertPositionTo("absolute");return b.Widget.prototype._trigger.call(this,c,f,g)},plugins:{},_uiHash:function(){return{helper:this.helper,position:this.position,originalPosition:this.originalPosition,offset:this.positionAbs}}});b.extend(b.ui.draggable,{version:"1.8.9"});\nb.ui.plugin.add("draggable","connectToSortable",{start:function(c,f){var g=b(this).data("draggable"),e=g.options,a=b.extend({},f,{item:g.element});g.sortables=[];b(e.connectToSortable).each(function(){var d=b.data(this,"sortable");if(d&&!d.options.disabled){g.sortables.push({instance:d,shouldRevert:d.options.revert});d._refreshItems();d._trigger("activate",c,a)}})},stop:function(c,f){var g=b(this).data("draggable"),e=b.extend({},f,{item:g.element});b.each(g.sortables,function(){if(this.instance.isOver){this.instance.isOver=\n0;g.cancelHelperRemoval=true;this.instance.cancelHelperRemoval=false;if(this.shouldRevert)this.instance.options.revert=true;this.instance._mouseStop(c);this.instance.options.helper=this.instance.options._helper;g.options.helper=="original"&&this.instance.currentItem.css({top:"auto",left:"auto"})}else{this.instance.cancelHelperRemoval=false;this.instance._trigger("deactivate",c,e)}})},drag:function(c,f){var g=b(this).data("draggable"),e=this;b.each(g.sortables,function(){this.instance.positionAbs=\ng.positionAbs;this.instance.helperProportions=g.helperProportions;this.instance.offset.click=g.offset.click;if(this.instance._intersectsWith(this.instance.containerCache)){if(!this.instance.isOver){this.instance.isOver=1;this.instance.currentItem=b(e).clone().appendTo(this.instance.element).data("sortable-item",true);this.instance.options._helper=this.instance.options.helper;this.instance.options.helper=function(){return f.helper[0]};c.target=this.instance.currentItem[0];this.instance._mouseCapture(c,\ntrue);this.instance._mouseStart(c,true,true);this.instance.offset.click.top=g.offset.click.top;this.instance.offset.click.left=g.offset.click.left;this.instance.offset.parent.left-=g.offset.parent.left-this.instance.offset.parent.left;this.instance.offset.parent.top-=g.offset.parent.top-this.instance.offset.parent.top;g._trigger("toSortable",c);g.dropped=this.instance.element;g.currentItem=g.element;this.instance.fromOutside=g}this.instance.currentItem&&this.instance._mouseDrag(c)}else if(this.instance.isOver){this.instance.isOver=\n0;this.instance.cancelHelperRemoval=true;this.instance.options.revert=false;this.instance._trigger("out",c,this.instance._uiHash(this.instance));this.instance._mouseStop(c,true);this.instance.options.helper=this.instance.options._helper;this.instance.currentItem.remove();this.instance.placeholder&&this.instance.placeholder.remove();g._trigger("fromSortable",c);g.dropped=false}})}});b.ui.plugin.add("draggable","cursor",{start:function(){var c=b("body"),f=b(this).data("draggable").options;if(c.css("cursor"))f._cursor=\nc.css("cursor");c.css("cursor",f.cursor)},stop:function(){var c=b(this).data("draggable").options;c._cursor&&b("body").css("cursor",c._cursor)}});b.ui.plugin.add("draggable","iframeFix",{start:function(){var c=b(this).data("draggable").options;b(c.iframeFix===true?"iframe":c.iframeFix).each(function(){b(\'<div class="ui-draggable-iframeFix" style="background: #fff;"></div>\').css({width:this.offsetWidth+"px",height:this.offsetHeight+"px",position:"absolute",opacity:"0.001",zIndex:1E3}).css(b(this).offset()).appendTo("body")})},\nstop:function(){b("div.ui-draggable-iframeFix").each(function(){this.parentNode.removeChild(this)})}});b.ui.plugin.add("draggable","opacity",{start:function(c,f){c=b(f.helper);f=b(this).data("draggable").options;if(c.css("opacity"))f._opacity=c.css("opacity");c.css("opacity",f.opacity)},stop:function(c,f){c=b(this).data("draggable").options;c._opacity&&b(f.helper).css("opacity",c._opacity)}});b.ui.plugin.add("draggable","scroll",{start:function(){var c=b(this).data("draggable");if(c.scrollParent[0]!=\ndocument&&c.scrollParent[0].tagName!="HTML")c.overflowOffset=c.scrollParent.offset()},drag:function(c){var f=b(this).data("draggable"),g=f.options,e=false;if(f.scrollParent[0]!=document&&f.scrollParent[0].tagName!="HTML"){if(!g.axis||g.axis!="x")if(f.overflowOffset.top+f.scrollParent[0].offsetHeight-c.pageY<g.scrollSensitivity)f.scrollParent[0].scrollTop=e=f.scrollParent[0].scrollTop+g.scrollSpeed;else if(c.pageY-f.overflowOffset.top<g.scrollSensitivity)f.scrollParent[0].scrollTop=e=f.scrollParent[0].scrollTop-\ng.scrollSpeed;if(!g.axis||g.axis!="y")if(f.overflowOffset.left+f.scrollParent[0].offsetWidth-c.pageX<g.scrollSensitivity)f.scrollParent[0].scrollLeft=e=f.scrollParent[0].scrollLeft+g.scrollSpeed;else if(c.pageX-f.overflowOffset.left<g.scrollSensitivity)f.scrollParent[0].scrollLeft=e=f.scrollParent[0].scrollLeft-g.scrollSpeed}else{if(!g.axis||g.axis!="x")if(c.pageY-b(document).scrollTop()<g.scrollSensitivity)e=b(document).scrollTop(b(document).scrollTop()-g.scrollSpeed);else if(b(window).height()-\n(c.pageY-b(document).scrollTop())<g.scrollSensitivity)e=b(document).scrollTop(b(document).scrollTop()+g.scrollSpeed);if(!g.axis||g.axis!="y")if(c.pageX-b(document).scrollLeft()<g.scrollSensitivity)e=b(document).scrollLeft(b(document).scrollLeft()-g.scrollSpeed);else if(b(window).width()-(c.pageX-b(document).scrollLeft())<g.scrollSensitivity)e=b(document).scrollLeft(b(document).scrollLeft()+g.scrollSpeed)}e!==false&&b.ui.ddmanager&&!g.dropBehaviour&&b.ui.ddmanager.prepareOffsets(f,c)}});b.ui.plugin.add("draggable",\n"snap",{start:function(){var c=b(this).data("draggable"),f=c.options;c.snapElements=[];b(f.snap.constructor!=String?f.snap.items||":data(draggable)":f.snap).each(function(){var g=b(this),e=g.offset();this!=c.element[0]&&c.snapElements.push({item:this,width:g.outerWidth(),height:g.outerHeight(),top:e.top,left:e.left})})},drag:function(c,f){for(var g=b(this).data("draggable"),e=g.options,a=e.snapTolerance,d=f.offset.left,h=d+g.helperProportions.width,i=f.offset.top,j=i+g.helperProportions.height,n=\ng.snapElements.length-1;n>=0;n--){var q=g.snapElements[n].left,l=q+g.snapElements[n].width,k=g.snapElements[n].top,m=k+g.snapElements[n].height;if(q-a<d&&d<l+a&&k-a<i&&i<m+a||q-a<d&&d<l+a&&k-a<j&&j<m+a||q-a<h&&h<l+a&&k-a<i&&i<m+a||q-a<h&&h<l+a&&k-a<j&&j<m+a){if(e.snapMode!="inner"){var o=Math.abs(k-j)<=a,p=Math.abs(m-i)<=a,s=Math.abs(q-h)<=a,r=Math.abs(l-d)<=a;if(o)f.position.top=g._convertPositionTo("relative",{top:k-g.helperProportions.height,left:0}).top-g.margins.top;if(p)f.position.top=g._convertPositionTo("relative",\n{top:m,left:0}).top-g.margins.top;if(s)f.position.left=g._convertPositionTo("relative",{top:0,left:q-g.helperProportions.width}).left-g.margins.left;if(r)f.position.left=g._convertPositionTo("relative",{top:0,left:l}).left-g.margins.left}var u=o||p||s||r;if(e.snapMode!="outer"){o=Math.abs(k-i)<=a;p=Math.abs(m-j)<=a;s=Math.abs(q-d)<=a;r=Math.abs(l-h)<=a;if(o)f.position.top=g._convertPositionTo("relative",{top:k,left:0}).top-g.margins.top;if(p)f.position.top=g._convertPositionTo("relative",{top:m-g.helperProportions.height,\nleft:0}).top-g.margins.top;if(s)f.position.left=g._convertPositionTo("relative",{top:0,left:q}).left-g.margins.left;if(r)f.position.left=g._convertPositionTo("relative",{top:0,left:l-g.helperProportions.width}).left-g.margins.left}if(!g.snapElements[n].snapping&&(o||p||s||r||u))g.options.snap.snap&&g.options.snap.snap.call(g.element,c,b.extend(g._uiHash(),{snapItem:g.snapElements[n].item}));g.snapElements[n].snapping=o||p||s||r||u}else{g.snapElements[n].snapping&&g.options.snap.release&&g.options.snap.release.call(g.element,\nc,b.extend(g._uiHash(),{snapItem:g.snapElements[n].item}));g.snapElements[n].snapping=false}}}});b.ui.plugin.add("draggable","stack",{start:function(){var c=b(this).data("draggable").options;c=b.makeArray(b(c.stack)).sort(function(g,e){return(parseInt(b(g).css("zIndex"),10)||0)-(parseInt(b(e).css("zIndex"),10)||0)});if(c.length){var f=parseInt(c[0].style.zIndex)||0;b(c).each(function(g){this.style.zIndex=f+g});this[0].style.zIndex=f+c.length}}});b.ui.plugin.add("draggable","zIndex",{start:function(c,\nf){c=b(f.helper);f=b(this).data("draggable").options;if(c.css("zIndex"))f._zIndex=c.css("zIndex");c.css("zIndex",f.zIndex)},stop:function(c,f){c=b(this).data("draggable").options;c._zIndex&&b(f.helper).css("zIndex",c._zIndex)}})})(jQuery);\n(function(b){b.widget("ui.droppable",{widgetEventPrefix:"drop",options:{accept:"*",activeClass:false,addClasses:true,greedy:false,hoverClass:false,scope:"default",tolerance:"intersect"},_create:function(){var c=this.options,f=c.accept;this.isover=0;this.isout=1;this.accept=b.isFunction(f)?f:function(g){return g.is(f)};this.proportions={width:this.element[0].offsetWidth,height:this.element[0].offsetHeight};b.ui.ddmanager.droppables[c.scope]=b.ui.ddmanager.droppables[c.scope]||[];b.ui.ddmanager.droppables[c.scope].push(this);\nc.addClasses&&this.element.addClass("ui-droppable")},destroy:function(){for(var c=b.ui.ddmanager.droppables[this.options.scope],f=0;f<c.length;f++)c[f]==this&&c.splice(f,1);this.element.removeClass("ui-droppable ui-droppable-disabled").removeData("droppable").unbind(".droppable");return this},_setOption:function(c,f){if(c=="accept")this.accept=b.isFunction(f)?f:function(g){return g.is(f)};b.Widget.prototype._setOption.apply(this,arguments)},_activate:function(c){var f=b.ui.ddmanager.current;this.options.activeClass&&\nthis.element.addClass(this.options.activeClass);f&&this._trigger("activate",c,this.ui(f))},_deactivate:function(c){var f=b.ui.ddmanager.current;this.options.activeClass&&this.element.removeClass(this.options.activeClass);f&&this._trigger("deactivate",c,this.ui(f))},_over:function(c){var f=b.ui.ddmanager.current;if(!(!f||(f.currentItem||f.element)[0]==this.element[0]))if(this.accept.call(this.element[0],f.currentItem||f.element)){this.options.hoverClass&&this.element.addClass(this.options.hoverClass);\nthis._trigger("over",c,this.ui(f))}},_out:function(c){var f=b.ui.ddmanager.current;if(!(!f||(f.currentItem||f.element)[0]==this.element[0]))if(this.accept.call(this.element[0],f.currentItem||f.element)){this.options.hoverClass&&this.element.removeClass(this.options.hoverClass);this._trigger("out",c,this.ui(f))}},_drop:function(c,f){var g=f||b.ui.ddmanager.current;if(!g||(g.currentItem||g.element)[0]==this.element[0])return false;var e=false;this.element.find(":data(droppable)").not(".ui-draggable-dragging").each(function(){var a=\nb.data(this,"droppable");if(a.options.greedy&&!a.options.disabled&&a.options.scope==g.options.scope&&a.accept.call(a.element[0],g.currentItem||g.element)&&b.ui.intersect(g,b.extend(a,{offset:a.element.offset()}),a.options.tolerance)){e=true;return false}});if(e)return false;if(this.accept.call(this.element[0],g.currentItem||g.element)){this.options.activeClass&&this.element.removeClass(this.options.activeClass);this.options.hoverClass&&this.element.removeClass(this.options.hoverClass);this._trigger("drop",\nc,this.ui(g));return this.element}return false},ui:function(c){return{draggable:c.currentItem||c.element,helper:c.helper,position:c.position,offset:c.positionAbs}}});b.extend(b.ui.droppable,{version:"1.8.9"});b.ui.intersect=function(c,f,g){if(!f.offset)return false;var e=(c.positionAbs||c.position.absolute).left,a=e+c.helperProportions.width,d=(c.positionAbs||c.position.absolute).top,h=d+c.helperProportions.height,i=f.offset.left,j=i+f.proportions.width,n=f.offset.top,q=n+f.proportions.height;\nswitch(g){case "fit":return i<=e&&a<=j&&n<=d&&h<=q;case "intersect":return i<e+c.helperProportions.width/2&&a-c.helperProportions.width/2<j&&n<d+c.helperProportions.height/2&&h-c.helperProportions.height/2<q;case "pointer":return b.ui.isOver((c.positionAbs||c.position.absolute).top+(c.clickOffset||c.offset.click).top,(c.positionAbs||c.position.absolute).left+(c.clickOffset||c.offset.click).left,n,i,f.proportions.height,f.proportions.width);case "touch":return(d>=n&&d<=q||h>=n&&h<=q||d<n&&h>q)&&(e>=\ni&&e<=j||a>=i&&a<=j||e<i&&a>j);default:return false}};b.ui.ddmanager={current:null,droppables:{"default":[]},prepareOffsets:function(c,f){var g=b.ui.ddmanager.droppables[c.options.scope]||[],e=f?f.type:null,a=(c.currentItem||c.element).find(":data(droppable)").andSelf(),d=0;a:for(;d<g.length;d++)if(!(g[d].options.disabled||c&&!g[d].accept.call(g[d].element[0],c.currentItem||c.element))){for(var h=0;h<a.length;h++)if(a[h]==g[d].element[0]){g[d].proportions.height=0;continue a}g[d].visible=g[d].element.css("display")!=\n"none";if(g[d].visible){g[d].offset=g[d].element.offset();g[d].proportions={width:g[d].element[0].offsetWidth,height:g[d].element[0].offsetHeight};e=="mousedown"&&g[d]._activate.call(g[d],f)}}},drop:function(c,f){var g=false;b.each(b.ui.ddmanager.droppables[c.options.scope]||[],function(){if(this.options){if(!this.options.disabled&&this.visible&&b.ui.intersect(c,this,this.options.tolerance))g=g||this._drop.call(this,f);if(!this.options.disabled&&this.visible&&this.accept.call(this.element[0],c.currentItem||\nc.element)){this.isout=1;this.isover=0;this._deactivate.call(this,f)}}});return g},drag:function(c,f){c.options.refreshPositions&&b.ui.ddmanager.prepareOffsets(c,f);b.each(b.ui.ddmanager.droppables[c.options.scope]||[],function(){if(!(this.options.disabled||this.greedyChild||!this.visible)){var g=b.ui.intersect(c,this,this.options.tolerance);if(g=!g&&this.isover==1?"isout":g&&this.isover==0?"isover":null){var e;if(this.options.greedy){var a=this.element.parents(":data(droppable):eq(0)");if(a.length){e=\nb.data(a[0],"droppable");e.greedyChild=g=="isover"?1:0}}if(e&&g=="isover"){e.isover=0;e.isout=1;e._out.call(e,f)}this[g]=1;this[g=="isout"?"isover":"isout"]=0;this[g=="isover"?"_over":"_out"].call(this,f);if(e&&g=="isout"){e.isout=0;e.isover=1;e._over.call(e,f)}}}})}}})(jQuery);\n(function(b){b.widget("ui.resizable",b.ui.mouse,{widgetEventPrefix:"resize",options:{alsoResize:false,animate:false,animateDuration:"slow",animateEasing:"swing",aspectRatio:false,autoHide:false,containment:false,ghost:false,grid:false,handles:"e,s,se",helper:false,maxHeight:null,maxWidth:null,minHeight:10,minWidth:10,zIndex:1E3},_create:function(){var g=this,e=this.options;this.element.addClass("ui-resizable");b.extend(this,{_aspectRatio:!!e.aspectRatio,aspectRatio:e.aspectRatio,originalElement:this.element,\n_proportionallyResizeElements:[],_helper:e.helper||e.ghost||e.animate?e.helper||"ui-resizable-helper":null});if(this.element[0].nodeName.match(/canvas|textarea|input|select|button|img/i)){/relative/.test(this.element.css("position"))&&b.browser.opera&&this.element.css({position:"relative",top:"auto",left:"auto"});this.element.wrap(b(\'<div class="ui-wrapper" style="overflow: hidden;"></div>\').css({position:this.element.css("position"),width:this.element.outerWidth(),height:this.element.outerHeight(),\ntop:this.element.css("top"),left:this.element.css("left")}));this.element=this.element.parent().data("resizable",this.element.data("resizable"));this.elementIsWrapper=true;this.element.css({marginLeft:this.originalElement.css("marginLeft"),marginTop:this.originalElement.css("marginTop"),marginRight:this.originalElement.css("marginRight"),marginBottom:this.originalElement.css("marginBottom")});this.originalElement.css({marginLeft:0,marginTop:0,marginRight:0,marginBottom:0});this.originalResizeStyle=\nthis.originalElement.css("resize");this.originalElement.css("resize","none");this._proportionallyResizeElements.push(this.originalElement.css({position:"static",zoom:1,display:"block"}));this.originalElement.css({margin:this.originalElement.css("margin")});this._proportionallyResize()}this.handles=e.handles||(!b(".ui-resizable-handle",this.element).length?"e,s,se":{n:".ui-resizable-n",e:".ui-resizable-e",s:".ui-resizable-s",w:".ui-resizable-w",se:".ui-resizable-se",sw:".ui-resizable-sw",ne:".ui-resizable-ne",\nnw:".ui-resizable-nw"});if(this.handles.constructor==String){if(this.handles=="all")this.handles="n,e,s,w,se,sw,ne,nw";var a=this.handles.split(",");this.handles={};for(var d=0;d<a.length;d++){var h=b.trim(a[d]),i=b(\'<div class="ui-resizable-handle \'+("ui-resizable-"+h)+\'"></div>\');/sw|se|ne|nw/.test(h)&&i.css({zIndex:++e.zIndex});"se"==h&&i.addClass("ui-icon ui-icon-gripsmall-diagonal-se");this.handles[h]=".ui-resizable-"+h;this.element.append(i)}}this._renderAxis=function(j){j=j||this.element;for(var n in this.handles){if(this.handles[n].constructor==\nString)this.handles[n]=b(this.handles[n],this.element).show();if(this.elementIsWrapper&&this.originalElement[0].nodeName.match(/textarea|input|select|button/i)){var q=b(this.handles[n],this.element),l=0;l=/sw|ne|nw|se|n|s/.test(n)?q.outerHeight():q.outerWidth();q=["padding",/ne|nw|n/.test(n)?"Top":/se|sw|s/.test(n)?"Bottom":/^e$/.test(n)?"Right":"Left"].join("");j.css(q,l);this._proportionallyResize()}b(this.handles[n])}};this._renderAxis(this.element);this._handles=b(".ui-resizable-handle",this.element).disableSelection();\nthis._handles.mouseover(function(){if(!g.resizing){if(this.className)var j=this.className.match(/ui-resizable-(se|sw|ne|nw|n|e|s|w)/i);g.axis=j&&j[1]?j[1]:"se"}});if(e.autoHide){this._handles.hide();b(this.element).addClass("ui-resizable-autohide").hover(function(){b(this).removeClass("ui-resizable-autohide");g._handles.show()},function(){if(!g.resizing){b(this).addClass("ui-resizable-autohide");g._handles.hide()}})}this._mouseInit()},destroy:function(){this._mouseDestroy();var g=function(a){b(a).removeClass("ui-resizable ui-resizable-disabled ui-resizable-resizing").removeData("resizable").unbind(".resizable").find(".ui-resizable-handle").remove()};\nif(this.elementIsWrapper){g(this.element);var e=this.element;e.after(this.originalElement.css({position:e.css("position"),width:e.outerWidth(),height:e.outerHeight(),top:e.css("top"),left:e.css("left")})).remove()}this.originalElement.css("resize",this.originalResizeStyle);g(this.originalElement);return this},_mouseCapture:function(g){var e=false;for(var a in this.handles)if(b(this.handles[a])[0]==g.target)e=true;return!this.options.disabled&&e},_mouseStart:function(g){var e=this.options,a=this.element.position(),\nd=this.element;this.resizing=true;this.documentScroll={top:b(document).scrollTop(),left:b(document).scrollLeft()};if(d.is(".ui-draggable")||/absolute/.test(d.css("position")))d.css({position:"absolute",top:a.top,left:a.left});b.browser.opera&&/relative/.test(d.css("position"))&&d.css({position:"relative",top:"auto",left:"auto"});this._renderProxy();a=c(this.helper.css("left"));var h=c(this.helper.css("top"));if(e.containment){a+=b(e.containment).scrollLeft()||0;h+=b(e.containment).scrollTop()||0}this.offset=\nthis.helper.offset();this.position={left:a,top:h};this.size=this._helper?{width:d.outerWidth(),height:d.outerHeight()}:{width:d.width(),height:d.height()};this.originalSize=this._helper?{width:d.outerWidth(),height:d.outerHeight()}:{width:d.width(),height:d.height()};this.originalPosition={left:a,top:h};this.sizeDiff={width:d.outerWidth()-d.width(),height:d.outerHeight()-d.height()};this.originalMousePosition={left:g.pageX,top:g.pageY};this.aspectRatio=typeof e.aspectRatio=="number"?e.aspectRatio:\nthis.originalSize.width/this.originalSize.height||1;e=b(".ui-resizable-"+this.axis).css("cursor");b("body").css("cursor",e=="auto"?this.axis+"-resize":e);d.addClass("ui-resizable-resizing");this._propagate("start",g);return true},_mouseDrag:function(g){var e=this.helper,a=this.originalMousePosition,d=this._change[this.axis];if(!d)return false;a=d.apply(this,[g,g.pageX-a.left||0,g.pageY-a.top||0]);if(this._aspectRatio||g.shiftKey)a=this._updateRatio(a,g);a=this._respectSize(a,g);this._propagate("resize",\ng);e.css({top:this.position.top+"px",left:this.position.left+"px",width:this.size.width+"px",height:this.size.height+"px"});!this._helper&&this._proportionallyResizeElements.length&&this._proportionallyResize();this._updateCache(a);this._trigger("resize",g,this.ui());return false},_mouseStop:function(g){this.resizing=false;var e=this.options,a=this;if(this._helper){var d=this._proportionallyResizeElements,h=d.length&&/textarea/i.test(d[0].nodeName);d=h&&b.ui.hasScroll(d[0],"left")?0:a.sizeDiff.height;\nh={width:a.size.width-(h?0:a.sizeDiff.width),height:a.size.height-d};d=parseInt(a.element.css("left"),10)+(a.position.left-a.originalPosition.left)||null;var i=parseInt(a.element.css("top"),10)+(a.position.top-a.originalPosition.top)||null;e.animate||this.element.css(b.extend(h,{top:i,left:d}));a.helper.height(a.size.height);a.helper.width(a.size.width);this._helper&&!e.animate&&this._proportionallyResize()}b("body").css("cursor","auto");this.element.removeClass("ui-resizable-resizing");this._propagate("stop",\ng);this._helper&&this.helper.remove();return false},_updateCache:function(g){this.offset=this.helper.offset();if(f(g.left))this.position.left=g.left;if(f(g.top))this.position.top=g.top;if(f(g.height))this.size.height=g.height;if(f(g.width))this.size.width=g.width},_updateRatio:function(g){var e=this.position,a=this.size,d=this.axis;if(g.height)g.width=a.height*this.aspectRatio;else if(g.width)g.height=a.width/this.aspectRatio;if(d=="sw"){g.left=e.left+(a.width-g.width);g.top=null}if(d=="nw"){g.top=\ne.top+(a.height-g.height);g.left=e.left+(a.width-g.width)}return g},_respectSize:function(g){var e=this.options,a=this.axis,d=f(g.width)&&e.maxWidth&&e.maxWidth<g.width,h=f(g.height)&&e.maxHeight&&e.maxHeight<g.height,i=f(g.width)&&e.minWidth&&e.minWidth>g.width,j=f(g.height)&&e.minHeight&&e.minHeight>g.height;if(i)g.width=e.minWidth;if(j)g.height=e.minHeight;if(d)g.width=e.maxWidth;if(h)g.height=e.maxHeight;var n=this.originalPosition.left+this.originalSize.width,q=this.position.top+this.size.height,\nl=/sw|nw|w/.test(a);a=/nw|ne|n/.test(a);if(i&&l)g.left=n-e.minWidth;if(d&&l)g.left=n-e.maxWidth;if(j&&a)g.top=q-e.minHeight;if(h&&a)g.top=q-e.maxHeight;if((e=!g.width&&!g.height)&&!g.left&&g.top)g.top=null;else if(e&&!g.top&&g.left)g.left=null;return g},_proportionallyResize:function(){if(this._proportionallyResizeElements.length)for(var g=this.helper||this.element,e=0;e<this._proportionallyResizeElements.length;e++){var a=this._proportionallyResizeElements[e];if(!this.borderDif){var d=[a.css("borderTopWidth"),\na.css("borderRightWidth"),a.css("borderBottomWidth"),a.css("borderLeftWidth")],h=[a.css("paddingTop"),a.css("paddingRight"),a.css("paddingBottom"),a.css("paddingLeft")];this.borderDif=b.map(d,function(i,j){i=parseInt(i,10)||0;j=parseInt(h[j],10)||0;return i+j})}b.browser.msie&&(b(g).is(":hidden")||b(g).parents(":hidden").length)||a.css({height:g.height()-this.borderDif[0]-this.borderDif[2]||0,width:g.width()-this.borderDif[1]-this.borderDif[3]||0})}},_renderProxy:function(){var g=this.options;this.elementOffset=\nthis.element.offset();if(this._helper){this.helper=this.helper||b(\'<div style="overflow:hidden;"></div>\');var e=b.browser.msie&&b.browser.version<7,a=e?1:0;e=e?2:-1;this.helper.addClass(this._helper).css({width:this.element.outerWidth()+e,height:this.element.outerHeight()+e,position:"absolute",left:this.elementOffset.left-a+"px",top:this.elementOffset.top-a+"px",zIndex:++g.zIndex});this.helper.appendTo("body").disableSelection()}else this.helper=this.element},_change:{e:function(g,e){return{width:this.originalSize.width+\ne}},w:function(g,e){return{left:this.originalPosition.left+e,width:this.originalSize.width-e}},n:function(g,e,a){return{top:this.originalPosition.top+a,height:this.originalSize.height-a}},s:function(g,e,a){return{height:this.originalSize.height+a}},se:function(g,e,a){return b.extend(this._change.s.apply(this,arguments),this._change.e.apply(this,[g,e,a]))},sw:function(g,e,a){return b.extend(this._change.s.apply(this,arguments),this._change.w.apply(this,[g,e,a]))},ne:function(g,e,a){return b.extend(this._change.n.apply(this,\narguments),this._change.e.apply(this,[g,e,a]))},nw:function(g,e,a){return b.extend(this._change.n.apply(this,arguments),this._change.w.apply(this,[g,e,a]))}},_propagate:function(g,e){b.ui.plugin.call(this,g,[e,this.ui()]);g!="resize"&&this._trigger(g,e,this.ui())},plugins:{},ui:function(){return{originalElement:this.originalElement,element:this.element,helper:this.helper,position:this.position,size:this.size,originalSize:this.originalSize,originalPosition:this.originalPosition}}});b.extend(b.ui.resizable,\n{version:"1.8.9"});b.ui.plugin.add("resizable","alsoResize",{start:function(){var g=b(this).data("resizable").options,e=function(a){b(a).each(function(){var d=b(this);d.data("resizable-alsoresize",{width:parseInt(d.width(),10),height:parseInt(d.height(),10),left:parseInt(d.css("left"),10),top:parseInt(d.css("top"),10),position:d.css("position")})})};if(typeof g.alsoResize=="object"&&!g.alsoResize.parentNode)if(g.alsoResize.length){g.alsoResize=g.alsoResize[0];e(g.alsoResize)}else b.each(g.alsoResize,\nfunction(a){e(a)});else e(g.alsoResize)},resize:function(g,e){var a=b(this).data("resizable");g=a.options;var d=a.originalSize,h=a.originalPosition,i={height:a.size.height-d.height||0,width:a.size.width-d.width||0,top:a.position.top-h.top||0,left:a.position.left-h.left||0},j=function(n,q){b(n).each(function(){var l=b(this),k=b(this).data("resizable-alsoresize"),m={},o=q&&q.length?q:l.parents(e.originalElement[0]).length?["width","height"]:["width","height","top","left"];b.each(o,function(p,s){if((p=\n(k[s]||0)+(i[s]||0))&&p>=0)m[s]=p||null});if(b.browser.opera&&/relative/.test(l.css("position"))){a._revertToRelativePosition=true;l.css({position:"absolute",top:"auto",left:"auto"})}l.css(m)})};typeof g.alsoResize=="object"&&!g.alsoResize.nodeType?b.each(g.alsoResize,function(n,q){j(n,q)}):j(g.alsoResize)},stop:function(){var g=b(this).data("resizable"),e=g.options,a=function(d){b(d).each(function(){var h=b(this);h.css({position:h.data("resizable-alsoresize").position})})};if(g._revertToRelativePosition){g._revertToRelativePosition=\nfalse;typeof e.alsoResize=="object"&&!e.alsoResize.nodeType?b.each(e.alsoResize,function(d){a(d)}):a(e.alsoResize)}b(this).removeData("resizable-alsoresize")}});b.ui.plugin.add("resizable","animate",{stop:function(g){var e=b(this).data("resizable"),a=e.options,d=e._proportionallyResizeElements,h=d.length&&/textarea/i.test(d[0].nodeName),i=h&&b.ui.hasScroll(d[0],"left")?0:e.sizeDiff.height;h={width:e.size.width-(h?0:e.sizeDiff.width),height:e.size.height-i};i=parseInt(e.element.css("left"),10)+(e.position.left-\ne.originalPosition.left)||null;var j=parseInt(e.element.css("top"),10)+(e.position.top-e.originalPosition.top)||null;e.element.animate(b.extend(h,j&&i?{top:j,left:i}:{}),{duration:a.animateDuration,easing:a.animateEasing,step:function(){var n={width:parseInt(e.element.css("width"),10),height:parseInt(e.element.css("height"),10),top:parseInt(e.element.css("top"),10),left:parseInt(e.element.css("left"),10)};d&&d.length&&b(d[0]).css({width:n.width,height:n.height});e._updateCache(n);e._propagate("resize",\ng)}})}});b.ui.plugin.add("resizable","containment",{start:function(){var g=b(this).data("resizable"),e=g.element,a=g.options.containment;if(e=a instanceof b?a.get(0):/parent/.test(a)?e.parent().get(0):a){g.containerElement=b(e);if(/document/.test(a)||a==document){g.containerOffset={left:0,top:0};g.containerPosition={left:0,top:0};g.parentData={element:b(document),left:0,top:0,width:b(document).width(),height:b(document).height()||document.body.parentNode.scrollHeight}}else{var d=b(e),h=[];b(["Top",\n"Right","Left","Bottom"]).each(function(n,q){h[n]=c(d.css("padding"+q))});g.containerOffset=d.offset();g.containerPosition=d.position();g.containerSize={height:d.innerHeight()-h[3],width:d.innerWidth()-h[1]};a=g.containerOffset;var i=g.containerSize.height,j=g.containerSize.width;j=b.ui.hasScroll(e,"left")?e.scrollWidth:j;i=b.ui.hasScroll(e)?e.scrollHeight:i;g.parentData={element:e,left:a.left,top:a.top,width:j,height:i}}}},resize:function(g){var e=b(this).data("resizable"),a=e.options,d=e.containerOffset,\nh=e.position;g=e._aspectRatio||g.shiftKey;var i={top:0,left:0},j=e.containerElement;if(j[0]!=document&&/static/.test(j.css("position")))i=d;if(h.left<(e._helper?d.left:0)){e.size.width+=e._helper?e.position.left-d.left:e.position.left-i.left;if(g)e.size.height=e.size.width/a.aspectRatio;e.position.left=a.helper?d.left:0}if(h.top<(e._helper?d.top:0)){e.size.height+=e._helper?e.position.top-d.top:e.position.top;if(g)e.size.width=e.size.height*a.aspectRatio;e.position.top=e._helper?d.top:0}e.offset.left=\ne.parentData.left+e.position.left;e.offset.top=e.parentData.top+e.position.top;a=Math.abs((e._helper?e.offset.left-i.left:e.offset.left-i.left)+e.sizeDiff.width);d=Math.abs((e._helper?e.offset.top-i.top:e.offset.top-d.top)+e.sizeDiff.height);h=e.containerElement.get(0)==e.element.parent().get(0);i=/relative|absolute/.test(e.containerElement.css("position"));if(h&&i)a-=e.parentData.left;if(a+e.size.width>=e.parentData.width){e.size.width=e.parentData.width-a;if(g)e.size.height=e.size.width/e.aspectRatio}if(d+\ne.size.height>=e.parentData.height){e.size.height=e.parentData.height-d;if(g)e.size.width=e.size.height*e.aspectRatio}},stop:function(){var g=b(this).data("resizable"),e=g.options,a=g.containerOffset,d=g.containerPosition,h=g.containerElement,i=b(g.helper),j=i.offset(),n=i.outerWidth()-g.sizeDiff.width;i=i.outerHeight()-g.sizeDiff.height;g._helper&&!e.animate&&/relative/.test(h.css("position"))&&b(this).css({left:j.left-d.left-a.left,width:n,height:i});g._helper&&!e.animate&&/static/.test(h.css("position"))&&\nb(this).css({left:j.left-d.left-a.left,width:n,height:i})}});b.ui.plugin.add("resizable","ghost",{start:function(){var g=b(this).data("resizable"),e=g.options,a=g.size;g.ghost=g.originalElement.clone();g.ghost.css({opacity:0.25,display:"block",position:"relative",height:a.height,width:a.width,margin:0,left:0,top:0}).addClass("ui-resizable-ghost").addClass(typeof e.ghost=="string"?e.ghost:"");g.ghost.appendTo(g.helper)},resize:function(){var g=b(this).data("resizable");g.ghost&&g.ghost.css({position:"relative",\nheight:g.size.height,width:g.size.width})},stop:function(){var g=b(this).data("resizable");g.ghost&&g.helper&&g.helper.get(0).removeChild(g.ghost.get(0))}});b.ui.plugin.add("resizable","grid",{resize:function(){var g=b(this).data("resizable"),e=g.options,a=g.size,d=g.originalSize,h=g.originalPosition,i=g.axis;e.grid=typeof e.grid=="number"?[e.grid,e.grid]:e.grid;var j=Math.round((a.width-d.width)/(e.grid[0]||1))*(e.grid[0]||1);e=Math.round((a.height-d.height)/(e.grid[1]||1))*(e.grid[1]||1);if(/^(se|s|e)$/.test(i)){g.size.width=\nd.width+j;g.size.height=d.height+e}else if(/^(ne)$/.test(i)){g.size.width=d.width+j;g.size.height=d.height+e;g.position.top=h.top-e}else{if(/^(sw)$/.test(i)){g.size.width=d.width+j;g.size.height=d.height+e}else{g.size.width=d.width+j;g.size.height=d.height+e;g.position.top=h.top-e}g.position.left=h.left-j}}});var c=function(g){return parseInt(g,10)||0},f=function(g){return!isNaN(parseInt(g,10))}})(jQuery);\n(function(b){b.widget("ui.selectable",b.ui.mouse,{options:{appendTo:"body",autoRefresh:true,distance:0,filter:"*",tolerance:"touch"},_create:function(){var c=this;this.element.addClass("ui-selectable");this.dragged=false;var f;this.refresh=function(){f=b(c.options.filter,c.element[0]);f.each(function(){var g=b(this),e=g.offset();b.data(this,"selectable-item",{element:this,$element:g,left:e.left,top:e.top,right:e.left+g.outerWidth(),bottom:e.top+g.outerHeight(),startselected:false,selected:g.hasClass("ui-selected"),\nselecting:g.hasClass("ui-selecting"),unselecting:g.hasClass("ui-unselecting")})})};this.refresh();this.selectees=f.addClass("ui-selectee");this._mouseInit();this.helper=b("<div class=\'ui-selectable-helper\'></div>")},destroy:function(){this.selectees.removeClass("ui-selectee").removeData("selectable-item");this.element.removeClass("ui-selectable ui-selectable-disabled").removeData("selectable").unbind(".selectable");this._mouseDestroy();return this},_mouseStart:function(c){var f=this;this.opos=[c.pageX,\nc.pageY];if(!this.options.disabled){var g=this.options;this.selectees=b(g.filter,this.element[0]);this._trigger("start",c);b(g.appendTo).append(this.helper);this.helper.css({left:c.clientX,top:c.clientY,width:0,height:0});g.autoRefresh&&this.refresh();this.selectees.filter(".ui-selected").each(function(){var e=b.data(this,"selectable-item");e.startselected=true;if(!c.metaKey){e.$element.removeClass("ui-selected");e.selected=false;e.$element.addClass("ui-unselecting");e.unselecting=true;f._trigger("unselecting",\nc,{unselecting:e.element})}});b(c.target).parents().andSelf().each(function(){var e=b.data(this,"selectable-item");if(e){var a=!c.metaKey||!e.$element.hasClass("ui-selected");e.$element.removeClass(a?"ui-unselecting":"ui-selected").addClass(a?"ui-selecting":"ui-unselecting");e.unselecting=!a;e.selecting=a;(e.selected=a)?f._trigger("selecting",c,{selecting:e.element}):f._trigger("unselecting",c,{unselecting:e.element});return false}})}},_mouseDrag:function(c){var f=this;this.dragged=true;if(!this.options.disabled){var g=\nthis.options,e=this.opos[0],a=this.opos[1],d=c.pageX,h=c.pageY;if(e>d){var i=d;d=e;e=i}if(a>h){i=h;h=a;a=i}this.helper.css({left:e,top:a,width:d-e,height:h-a});this.selectees.each(function(){var j=b.data(this,"selectable-item");if(!(!j||j.element==f.element[0])){var n=false;if(g.tolerance=="touch")n=!(j.left>d||j.right<e||j.top>h||j.bottom<a);else if(g.tolerance=="fit")n=j.left>e&&j.right<d&&j.top>a&&j.bottom<h;if(n){if(j.selected){j.$element.removeClass("ui-selected");j.selected=false}if(j.unselecting){j.$element.removeClass("ui-unselecting");\nj.unselecting=false}if(!j.selecting){j.$element.addClass("ui-selecting");j.selecting=true;f._trigger("selecting",c,{selecting:j.element})}}else{if(j.selecting)if(c.metaKey&&j.startselected){j.$element.removeClass("ui-selecting");j.selecting=false;j.$element.addClass("ui-selected");j.selected=true}else{j.$element.removeClass("ui-selecting");j.selecting=false;if(j.startselected){j.$element.addClass("ui-unselecting");j.unselecting=true}f._trigger("unselecting",c,{unselecting:j.element})}if(j.selected)if(!c.metaKey&&\n!j.startselected){j.$element.removeClass("ui-selected");j.selected=false;j.$element.addClass("ui-unselecting");j.unselecting=true;f._trigger("unselecting",c,{unselecting:j.element})}}}});return false}},_mouseStop:function(c){var f=this;this.dragged=false;b(".ui-unselecting",this.element[0]).each(function(){var g=b.data(this,"selectable-item");g.$element.removeClass("ui-unselecting");g.unselecting=false;g.startselected=false;f._trigger("unselected",c,{unselected:g.element})});b(".ui-selecting",this.element[0]).each(function(){var g=\nb.data(this,"selectable-item");g.$element.removeClass("ui-selecting").addClass("ui-selected");g.selecting=false;g.selected=true;g.startselected=true;f._trigger("selected",c,{selected:g.element})});this._trigger("stop",c);this.helper.remove();return false}});b.extend(b.ui.selectable,{version:"1.8.9"})})(jQuery);\n(function(b){b.widget("ui.sortable",b.ui.mouse,{widgetEventPrefix:"sort",options:{appendTo:"parent",axis:false,connectWith:false,containment:false,cursor:"auto",cursorAt:false,dropOnEmpty:true,forcePlaceholderSize:false,forceHelperSize:false,grid:false,handle:false,helper:"original",items:"> *",opacity:false,placeholder:false,revert:false,scroll:true,scrollSensitivity:20,scrollSpeed:20,scope:"default",tolerance:"intersect",zIndex:1E3},_create:function(){this.containerCache={};this.element.addClass("ui-sortable");\nthis.refresh();this.floating=this.items.length?/left|right/.test(this.items[0].item.css("float")):false;this.offset=this.element.offset();this._mouseInit()},destroy:function(){this.element.removeClass("ui-sortable ui-sortable-disabled").removeData("sortable").unbind(".sortable");this._mouseDestroy();for(var c=this.items.length-1;c>=0;c--)this.items[c].item.removeData("sortable-item");return this},_setOption:function(c,f){if(c==="disabled"){this.options[c]=f;this.widget()[f?"addClass":"removeClass"]("ui-sortable-disabled")}else b.Widget.prototype._setOption.apply(this,\narguments)},_mouseCapture:function(c,f){if(this.reverting)return false;if(this.options.disabled||this.options.type=="static")return false;this._refreshItems(c);var g=null,e=this;b(c.target).parents().each(function(){if(b.data(this,"sortable-item")==e){g=b(this);return false}});if(b.data(c.target,"sortable-item")==e)g=b(c.target);if(!g)return false;if(this.options.handle&&!f){var a=false;b(this.options.handle,g).find("*").andSelf().each(function(){if(this==c.target)a=true});if(!a)return false}this.currentItem=\ng;this._removeCurrentsFromItems();return true},_mouseStart:function(c,f,g){f=this.options;var e=this;this.currentContainer=this;this.refreshPositions();this.helper=this._createHelper(c);this._cacheHelperProportions();this._cacheMargins();this.scrollParent=this.helper.scrollParent();this.offset=this.currentItem.offset();this.offset={top:this.offset.top-this.margins.top,left:this.offset.left-this.margins.left};this.helper.css("position","absolute");this.cssPosition=this.helper.css("position");b.extend(this.offset,\n{click:{left:c.pageX-this.offset.left,top:c.pageY-this.offset.top},parent:this._getParentOffset(),relative:this._getRelativeOffset()});this.originalPosition=this._generatePosition(c);this.originalPageX=c.pageX;this.originalPageY=c.pageY;f.cursorAt&&this._adjustOffsetFromHelper(f.cursorAt);this.domPosition={prev:this.currentItem.prev()[0],parent:this.currentItem.parent()[0]};this.helper[0]!=this.currentItem[0]&&this.currentItem.hide();this._createPlaceholder();f.containment&&this._setContainment();\nif(f.cursor){if(b("body").css("cursor"))this._storedCursor=b("body").css("cursor");b("body").css("cursor",f.cursor)}if(f.opacity){if(this.helper.css("opacity"))this._storedOpacity=this.helper.css("opacity");this.helper.css("opacity",f.opacity)}if(f.zIndex){if(this.helper.css("zIndex"))this._storedZIndex=this.helper.css("zIndex");this.helper.css("zIndex",f.zIndex)}if(this.scrollParent[0]!=document&&this.scrollParent[0].tagName!="HTML")this.overflowOffset=this.scrollParent.offset();this._trigger("start",\nc,this._uiHash());this._preserveHelperProportions||this._cacheHelperProportions();if(!g)for(g=this.containers.length-1;g>=0;g--)this.containers[g]._trigger("activate",c,e._uiHash(this));if(b.ui.ddmanager)b.ui.ddmanager.current=this;b.ui.ddmanager&&!f.dropBehaviour&&b.ui.ddmanager.prepareOffsets(this,c);this.dragging=true;this.helper.addClass("ui-sortable-helper");this._mouseDrag(c);return true},_mouseDrag:function(c){this.position=this._generatePosition(c);this.positionAbs=this._convertPositionTo("absolute");\nif(!this.lastPositionAbs)this.lastPositionAbs=this.positionAbs;if(this.options.scroll){var f=this.options,g=false;if(this.scrollParent[0]!=document&&this.scrollParent[0].tagName!="HTML"){if(this.overflowOffset.top+this.scrollParent[0].offsetHeight-c.pageY<f.scrollSensitivity)this.scrollParent[0].scrollTop=g=this.scrollParent[0].scrollTop+f.scrollSpeed;else if(c.pageY-this.overflowOffset.top<f.scrollSensitivity)this.scrollParent[0].scrollTop=g=this.scrollParent[0].scrollTop-f.scrollSpeed;if(this.overflowOffset.left+\nthis.scrollParent[0].offsetWidth-c.pageX<f.scrollSensitivity)this.scrollParent[0].scrollLeft=g=this.scrollParent[0].scrollLeft+f.scrollSpeed;else if(c.pageX-this.overflowOffset.left<f.scrollSensitivity)this.scrollParent[0].scrollLeft=g=this.scrollParent[0].scrollLeft-f.scrollSpeed}else{if(c.pageY-b(document).scrollTop()<f.scrollSensitivity)g=b(document).scrollTop(b(document).scrollTop()-f.scrollSpeed);else if(b(window).height()-(c.pageY-b(document).scrollTop())<f.scrollSensitivity)g=b(document).scrollTop(b(document).scrollTop()+\nf.scrollSpeed);if(c.pageX-b(document).scrollLeft()<f.scrollSensitivity)g=b(document).scrollLeft(b(document).scrollLeft()-f.scrollSpeed);else if(b(window).width()-(c.pageX-b(document).scrollLeft())<f.scrollSensitivity)g=b(document).scrollLeft(b(document).scrollLeft()+f.scrollSpeed)}g!==false&&b.ui.ddmanager&&!f.dropBehaviour&&b.ui.ddmanager.prepareOffsets(this,c)}this.positionAbs=this._convertPositionTo("absolute");if(!this.options.axis||this.options.axis!="y")this.helper[0].style.left=this.position.left+\n"px";if(!this.options.axis||this.options.axis!="x")this.helper[0].style.top=this.position.top+"px";for(f=this.items.length-1;f>=0;f--){g=this.items[f];var e=g.item[0],a=this._intersectsWithPointer(g);if(a)if(e!=this.currentItem[0]&&this.placeholder[a==1?"next":"prev"]()[0]!=e&&!b.ui.contains(this.placeholder[0],e)&&(this.options.type=="semi-dynamic"?!b.ui.contains(this.element[0],e):true)){this.direction=a==1?"down":"up";if(this.options.tolerance=="pointer"||this._intersectsWithSides(g))this._rearrange(c,\ng);else break;this._trigger("change",c,this._uiHash());break}}this._contactContainers(c);b.ui.ddmanager&&b.ui.ddmanager.drag(this,c);this._trigger("sort",c,this._uiHash());this.lastPositionAbs=this.positionAbs;return false},_mouseStop:function(c,f){if(c){b.ui.ddmanager&&!this.options.dropBehaviour&&b.ui.ddmanager.drop(this,c);if(this.options.revert){var g=this;f=g.placeholder.offset();g.reverting=true;b(this.helper).animate({left:f.left-this.offset.parent.left-g.margins.left+(this.offsetParent[0]==\ndocument.body?0:this.offsetParent[0].scrollLeft),top:f.top-this.offset.parent.top-g.margins.top+(this.offsetParent[0]==document.body?0:this.offsetParent[0].scrollTop)},parseInt(this.options.revert,10)||500,function(){g._clear(c)})}else this._clear(c,f);return false}},cancel:function(){var c=this;if(this.dragging){this._mouseUp({target:null});this.options.helper=="original"?this.currentItem.css(this._storedCSS).removeClass("ui-sortable-helper"):this.currentItem.show();for(var f=this.containers.length-\n1;f>=0;f--){this.containers[f]._trigger("deactivate",null,c._uiHash(this));if(this.containers[f].containerCache.over){this.containers[f]._trigger("out",null,c._uiHash(this));this.containers[f].containerCache.over=0}}}if(this.placeholder){this.placeholder[0].parentNode&&this.placeholder[0].parentNode.removeChild(this.placeholder[0]);this.options.helper!="original"&&this.helper&&this.helper[0].parentNode&&this.helper.remove();b.extend(this,{helper:null,dragging:false,reverting:false,_noFinalSort:null});\nthis.domPosition.prev?b(this.domPosition.prev).after(this.currentItem):b(this.domPosition.parent).prepend(this.currentItem)}return this},serialize:function(c){var f=this._getItemsAsjQuery(c&&c.connected),g=[];c=c||{};b(f).each(function(){var e=(b(c.item||this).attr(c.attribute||"id")||"").match(c.expression||/(.+)[-=_](.+)/);if(e)g.push((c.key||e[1]+"[]")+"="+(c.key&&c.expression?e[1]:e[2]))});!g.length&&c.key&&g.push(c.key+"=");return g.join("&")},toArray:function(c){var f=this._getItemsAsjQuery(c&&\nc.connected),g=[];c=c||{};f.each(function(){g.push(b(c.item||this).attr(c.attribute||"id")||"")});return g},_intersectsWith:function(c){var f=this.positionAbs.left,g=f+this.helperProportions.width,e=this.positionAbs.top,a=e+this.helperProportions.height,d=c.left,h=d+c.width,i=c.top,j=i+c.height,n=this.offset.click.top,q=this.offset.click.left;n=e+n>i&&e+n<j&&f+q>d&&f+q<h;return this.options.tolerance=="pointer"||this.options.forcePointerForContainers||this.options.tolerance!="pointer"&&this.helperProportions[this.floating?\n"width":"height"]>c[this.floating?"width":"height"]?n:d<f+this.helperProportions.width/2&&g-this.helperProportions.width/2<h&&i<e+this.helperProportions.height/2&&a-this.helperProportions.height/2<j},_intersectsWithPointer:function(c){var f=b.ui.isOverAxis(this.positionAbs.top+this.offset.click.top,c.top,c.height);c=b.ui.isOverAxis(this.positionAbs.left+this.offset.click.left,c.left,c.width);f=f&&c;c=this._getDragVerticalDirection();var g=this._getDragHorizontalDirection();if(!f)return false;return this.floating?\ng&&g=="right"||c=="down"?2:1:c&&(c=="down"?2:1)},_intersectsWithSides:function(c){var f=b.ui.isOverAxis(this.positionAbs.top+this.offset.click.top,c.top+c.height/2,c.height);c=b.ui.isOverAxis(this.positionAbs.left+this.offset.click.left,c.left+c.width/2,c.width);var g=this._getDragVerticalDirection(),e=this._getDragHorizontalDirection();return this.floating&&e?e=="right"&&c||e=="left"&&!c:g&&(g=="down"&&f||g=="up"&&!f)},_getDragVerticalDirection:function(){var c=this.positionAbs.top-this.lastPositionAbs.top;\nreturn c!=0&&(c>0?"down":"up")},_getDragHorizontalDirection:function(){var c=this.positionAbs.left-this.lastPositionAbs.left;return c!=0&&(c>0?"right":"left")},refresh:function(c){this._refreshItems(c);this.refreshPositions();return this},_connectWith:function(){var c=this.options;return c.connectWith.constructor==String?[c.connectWith]:c.connectWith},_getItemsAsjQuery:function(c){var f=[],g=[],e=this._connectWith();if(e&&c)for(c=e.length-1;c>=0;c--)for(var a=b(e[c]),d=a.length-1;d>=0;d--){var h=\nb.data(a[d],"sortable");if(h&&h!=this&&!h.options.disabled)g.push([b.isFunction(h.options.items)?h.options.items.call(h.element):b(h.options.items,h.element).not(".ui-sortable-helper").not(".ui-sortable-placeholder"),h])}g.push([b.isFunction(this.options.items)?this.options.items.call(this.element,null,{options:this.options,item:this.currentItem}):b(this.options.items,this.element).not(".ui-sortable-helper").not(".ui-sortable-placeholder"),this]);for(c=g.length-1;c>=0;c--)g[c][0].each(function(){f.push(this)});\nreturn b(f)},_removeCurrentsFromItems:function(){for(var c=this.currentItem.find(":data(sortable-item)"),f=0;f<this.items.length;f++)for(var g=0;g<c.length;g++)c[g]==this.items[f].item[0]&&this.items.splice(f,1)},_refreshItems:function(c){this.items=[];this.containers=[this];var f=this.items,g=[[b.isFunction(this.options.items)?this.options.items.call(this.element[0],c,{item:this.currentItem}):b(this.options.items,this.element),this]],e=this._connectWith();if(e)for(var a=e.length-1;a>=0;a--)for(var d=\nb(e[a]),h=d.length-1;h>=0;h--){var i=b.data(d[h],"sortable");if(i&&i!=this&&!i.options.disabled){g.push([b.isFunction(i.options.items)?i.options.items.call(i.element[0],c,{item:this.currentItem}):b(i.options.items,i.element),i]);this.containers.push(i)}}for(a=g.length-1;a>=0;a--){c=g[a][1];e=g[a][0];h=0;for(d=e.length;h<d;h++){i=b(e[h]);i.data("sortable-item",c);f.push({item:i,instance:c,width:0,height:0,left:0,top:0})}}},refreshPositions:function(c){if(this.offsetParent&&this.helper)this.offset.parent=\nthis._getParentOffset();for(var f=this.items.length-1;f>=0;f--){var g=this.items[f],e=this.options.toleranceElement?b(this.options.toleranceElement,g.item):g.item;if(!c){g.width=e.outerWidth();g.height=e.outerHeight()}e=e.offset();g.left=e.left;g.top=e.top}if(this.options.custom&&this.options.custom.refreshContainers)this.options.custom.refreshContainers.call(this);else for(f=this.containers.length-1;f>=0;f--){e=this.containers[f].element.offset();this.containers[f].containerCache.left=e.left;this.containers[f].containerCache.top=\ne.top;this.containers[f].containerCache.width=this.containers[f].element.outerWidth();this.containers[f].containerCache.height=this.containers[f].element.outerHeight()}return this},_createPlaceholder:function(c){var f=c||this,g=f.options;if(!g.placeholder||g.placeholder.constructor==String){var e=g.placeholder;g.placeholder={element:function(){var a=b(document.createElement(f.currentItem[0].nodeName)).addClass(e||f.currentItem[0].className+" ui-sortable-placeholder").removeClass("ui-sortable-helper")[0];\nif(!e)a.style.visibility="hidden";return a},update:function(a,d){if(!(e&&!g.forcePlaceholderSize)){d.height()||d.height(f.currentItem.innerHeight()-parseInt(f.currentItem.css("paddingTop")||0,10)-parseInt(f.currentItem.css("paddingBottom")||0,10));d.width()||d.width(f.currentItem.innerWidth()-parseInt(f.currentItem.css("paddingLeft")||0,10)-parseInt(f.currentItem.css("paddingRight")||0,10))}}}}f.placeholder=b(g.placeholder.element.call(f.element,f.currentItem));f.currentItem.after(f.placeholder);\ng.placeholder.update(f,f.placeholder)},_contactContainers:function(c){for(var f=null,g=null,e=this.containers.length-1;e>=0;e--)if(!b.ui.contains(this.currentItem[0],this.containers[e].element[0]))if(this._intersectsWith(this.containers[e].containerCache)){if(!(f&&b.ui.contains(this.containers[e].element[0],f.element[0]))){f=this.containers[e];g=e}}else if(this.containers[e].containerCache.over){this.containers[e]._trigger("out",c,this._uiHash(this));this.containers[e].containerCache.over=0}if(f)if(this.containers.length===\n1){this.containers[g]._trigger("over",c,this._uiHash(this));this.containers[g].containerCache.over=1}else if(this.currentContainer!=this.containers[g]){f=1E4;e=null;for(var a=this.positionAbs[this.containers[g].floating?"left":"top"],d=this.items.length-1;d>=0;d--)if(b.ui.contains(this.containers[g].element[0],this.items[d].item[0])){var h=this.items[d][this.containers[g].floating?"left":"top"];if(Math.abs(h-a)<f){f=Math.abs(h-a);e=this.items[d]}}if(e||this.options.dropOnEmpty){this.currentContainer=\nthis.containers[g];e?this._rearrange(c,e,null,true):this._rearrange(c,null,this.containers[g].element,true);this._trigger("change",c,this._uiHash());this.containers[g]._trigger("change",c,this._uiHash(this));this.options.placeholder.update(this.currentContainer,this.placeholder);this.containers[g]._trigger("over",c,this._uiHash(this));this.containers[g].containerCache.over=1}}},_createHelper:function(c){var f=this.options;c=b.isFunction(f.helper)?b(f.helper.apply(this.element[0],[c,this.currentItem])):\nf.helper=="clone"?this.currentItem.clone():this.currentItem;c.parents("body").length||b(f.appendTo!="parent"?f.appendTo:this.currentItem[0].parentNode)[0].appendChild(c[0]);if(c[0]==this.currentItem[0])this._storedCSS={width:this.currentItem[0].style.width,height:this.currentItem[0].style.height,position:this.currentItem.css("position"),top:this.currentItem.css("top"),left:this.currentItem.css("left")};if(c[0].style.width==""||f.forceHelperSize)c.width(this.currentItem.width());if(c[0].style.height==\n""||f.forceHelperSize)c.height(this.currentItem.height());return c},_adjustOffsetFromHelper:function(c){if(typeof c=="string")c=c.split(" ");if(b.isArray(c))c={left:+c[0],top:+c[1]||0};if("left"in c)this.offset.click.left=c.left+this.margins.left;if("right"in c)this.offset.click.left=this.helperProportions.width-c.right+this.margins.left;if("top"in c)this.offset.click.top=c.top+this.margins.top;if("bottom"in c)this.offset.click.top=this.helperProportions.height-c.bottom+this.margins.top},_getParentOffset:function(){this.offsetParent=\nthis.helper.offsetParent();var c=this.offsetParent.offset();if(this.cssPosition=="absolute"&&this.scrollParent[0]!=document&&b.ui.contains(this.scrollParent[0],this.offsetParent[0])){c.left+=this.scrollParent.scrollLeft();c.top+=this.scrollParent.scrollTop()}if(this.offsetParent[0]==document.body||this.offsetParent[0].tagName&&this.offsetParent[0].tagName.toLowerCase()=="html"&&b.browser.msie)c={top:0,left:0};return{top:c.top+(parseInt(this.offsetParent.css("borderTopWidth"),10)||0),left:c.left+(parseInt(this.offsetParent.css("borderLeftWidth"),\n10)||0)}},_getRelativeOffset:function(){if(this.cssPosition=="relative"){var c=this.currentItem.position();return{top:c.top-(parseInt(this.helper.css("top"),10)||0)+this.scrollParent.scrollTop(),left:c.left-(parseInt(this.helper.css("left"),10)||0)+this.scrollParent.scrollLeft()}}else return{top:0,left:0}},_cacheMargins:function(){this.margins={left:parseInt(this.currentItem.css("marginLeft"),10)||0,top:parseInt(this.currentItem.css("marginTop"),10)||0}},_cacheHelperProportions:function(){this.helperProportions=\n{width:this.helper.outerWidth(),height:this.helper.outerHeight()}},_setContainment:function(){var c=this.options;if(c.containment=="parent")c.containment=this.helper[0].parentNode;if(c.containment=="document"||c.containment=="window")this.containment=[0-this.offset.relative.left-this.offset.parent.left,0-this.offset.relative.top-this.offset.parent.top,b(c.containment=="document"?document:window).width()-this.helperProportions.width-this.margins.left,(b(c.containment=="document"?document:window).height()||\ndocument.body.parentNode.scrollHeight)-this.helperProportions.height-this.margins.top];if(!/^(document|window|parent)$/.test(c.containment)){var f=b(c.containment)[0];c=b(c.containment).offset();var g=b(f).css("overflow")!="hidden";this.containment=[c.left+(parseInt(b(f).css("borderLeftWidth"),10)||0)+(parseInt(b(f).css("paddingLeft"),10)||0)-this.margins.left,c.top+(parseInt(b(f).css("borderTopWidth"),10)||0)+(parseInt(b(f).css("paddingTop"),10)||0)-this.margins.top,c.left+(g?Math.max(f.scrollWidth,\nf.offsetWidth):f.offsetWidth)-(parseInt(b(f).css("borderLeftWidth"),10)||0)-(parseInt(b(f).css("paddingRight"),10)||0)-this.helperProportions.width-this.margins.left,c.top+(g?Math.max(f.scrollHeight,f.offsetHeight):f.offsetHeight)-(parseInt(b(f).css("borderTopWidth"),10)||0)-(parseInt(b(f).css("paddingBottom"),10)||0)-this.helperProportions.height-this.margins.top]}},_convertPositionTo:function(c,f){if(!f)f=this.position;c=c=="absolute"?1:-1;var g=this.cssPosition=="absolute"&&!(this.scrollParent[0]!=\ndocument&&b.ui.contains(this.scrollParent[0],this.offsetParent[0]))?this.offsetParent:this.scrollParent,e=/(html|body)/i.test(g[0].tagName);return{top:f.top+this.offset.relative.top*c+this.offset.parent.top*c-(b.browser.safari&&this.cssPosition=="fixed"?0:(this.cssPosition=="fixed"?-this.scrollParent.scrollTop():e?0:g.scrollTop())*c),left:f.left+this.offset.relative.left*c+this.offset.parent.left*c-(b.browser.safari&&this.cssPosition=="fixed"?0:(this.cssPosition=="fixed"?-this.scrollParent.scrollLeft():\ne?0:g.scrollLeft())*c)}},_generatePosition:function(c){var f=this.options,g=this.cssPosition=="absolute"&&!(this.scrollParent[0]!=document&&b.ui.contains(this.scrollParent[0],this.offsetParent[0]))?this.offsetParent:this.scrollParent,e=/(html|body)/i.test(g[0].tagName);if(this.cssPosition=="relative"&&!(this.scrollParent[0]!=document&&this.scrollParent[0]!=this.offsetParent[0]))this.offset.relative=this._getRelativeOffset();var a=c.pageX,d=c.pageY;if(this.originalPosition){if(this.containment){if(c.pageX-\nthis.offset.click.left<this.containment[0])a=this.containment[0]+this.offset.click.left;if(c.pageY-this.offset.click.top<this.containment[1])d=this.containment[1]+this.offset.click.top;if(c.pageX-this.offset.click.left>this.containment[2])a=this.containment[2]+this.offset.click.left;if(c.pageY-this.offset.click.top>this.containment[3])d=this.containment[3]+this.offset.click.top}if(f.grid){d=this.originalPageY+Math.round((d-this.originalPageY)/f.grid[1])*f.grid[1];d=this.containment?!(d-this.offset.click.top<\nthis.containment[1]||d-this.offset.click.top>this.containment[3])?d:!(d-this.offset.click.top<this.containment[1])?d-f.grid[1]:d+f.grid[1]:d;a=this.originalPageX+Math.round((a-this.originalPageX)/f.grid[0])*f.grid[0];a=this.containment?!(a-this.offset.click.left<this.containment[0]||a-this.offset.click.left>this.containment[2])?a:!(a-this.offset.click.left<this.containment[0])?a-f.grid[0]:a+f.grid[0]:a}}return{top:d-this.offset.click.top-this.offset.relative.top-this.offset.parent.top+(b.browser.safari&&\nthis.cssPosition=="fixed"?0:this.cssPosition=="fixed"?-this.scrollParent.scrollTop():e?0:g.scrollTop()),left:a-this.offset.click.left-this.offset.relative.left-this.offset.parent.left+(b.browser.safari&&this.cssPosition=="fixed"?0:this.cssPosition=="fixed"?-this.scrollParent.scrollLeft():e?0:g.scrollLeft())}},_rearrange:function(c,f,g,e){g?g[0].appendChild(this.placeholder[0]):f.item[0].parentNode.insertBefore(this.placeholder[0],this.direction=="down"?f.item[0]:f.item[0].nextSibling);this.counter=\nthis.counter?++this.counter:1;var a=this,d=this.counter;window.setTimeout(function(){d==a.counter&&a.refreshPositions(!e)},0)},_clear:function(c,f){this.reverting=false;var g=[];!this._noFinalSort&&this.currentItem[0].parentNode&&this.placeholder.before(this.currentItem);this._noFinalSort=null;if(this.helper[0]==this.currentItem[0]){for(var e in this._storedCSS)if(this._storedCSS[e]=="auto"||this._storedCSS[e]=="static")this._storedCSS[e]="";this.currentItem.css(this._storedCSS).removeClass("ui-sortable-helper")}else this.currentItem.show();\nthis.fromOutside&&!f&&g.push(function(a){this._trigger("receive",a,this._uiHash(this.fromOutside))});if((this.fromOutside||this.domPosition.prev!=this.currentItem.prev().not(".ui-sortable-helper")[0]||this.domPosition.parent!=this.currentItem.parent()[0])&&!f)g.push(function(a){this._trigger("update",a,this._uiHash())});if(!b.ui.contains(this.element[0],this.currentItem[0])){f||g.push(function(a){this._trigger("remove",a,this._uiHash())});for(e=this.containers.length-1;e>=0;e--)if(b.ui.contains(this.containers[e].element[0],\nthis.currentItem[0])&&!f){g.push(function(a){return function(d){a._trigger("receive",d,this._uiHash(this))}}.call(this,this.containers[e]));g.push(function(a){return function(d){a._trigger("update",d,this._uiHash(this))}}.call(this,this.containers[e]))}}for(e=this.containers.length-1;e>=0;e--){f||g.push(function(a){return function(d){a._trigger("deactivate",d,this._uiHash(this))}}.call(this,this.containers[e]));if(this.containers[e].containerCache.over){g.push(function(a){return function(d){a._trigger("out",\nd,this._uiHash(this))}}.call(this,this.containers[e]));this.containers[e].containerCache.over=0}}this._storedCursor&&b("body").css("cursor",this._storedCursor);this._storedOpacity&&this.helper.css("opacity",this._storedOpacity);if(this._storedZIndex)this.helper.css("zIndex",this._storedZIndex=="auto"?"":this._storedZIndex);this.dragging=false;if(this.cancelHelperRemoval){if(!f){this._trigger("beforeStop",c,this._uiHash());for(e=0;e<g.length;e++)g[e].call(this,c);this._trigger("stop",c,this._uiHash())}return false}f||\nthis._trigger("beforeStop",c,this._uiHash());this.placeholder[0].parentNode.removeChild(this.placeholder[0]);this.helper[0]!=this.currentItem[0]&&this.helper.remove();this.helper=null;if(!f){for(e=0;e<g.length;e++)g[e].call(this,c);this._trigger("stop",c,this._uiHash())}this.fromOutside=false;return true},_trigger:function(){b.Widget.prototype._trigger.apply(this,arguments)===false&&this.cancel()},_uiHash:function(c){var f=c||this;return{helper:f.helper,placeholder:f.placeholder||b([]),position:f.position,\noriginalPosition:f.originalPosition,offset:f.positionAbs,item:f.currentItem,sender:c?c.element:null}}});b.extend(b.ui.sortable,{version:"1.8.9"})})(jQuery);\njQuery.effects||function(b,c){function f(l){var k;if(l&&l.constructor==Array&&l.length==3)return l;if(k=/rgb\\(\\s*([0-9]{1,3})\\s*,\\s*([0-9]{1,3})\\s*,\\s*([0-9]{1,3})\\s*\\)/.exec(l))return[parseInt(k[1],10),parseInt(k[2],10),parseInt(k[3],10)];if(k=/rgb\\(\\s*([0-9]+(?:\\.[0-9]+)?)\\%\\s*,\\s*([0-9]+(?:\\.[0-9]+)?)\\%\\s*,\\s*([0-9]+(?:\\.[0-9]+)?)\\%\\s*\\)/.exec(l))return[parseFloat(k[1])*2.55,parseFloat(k[2])*2.55,parseFloat(k[3])*2.55];if(k=/#([a-fA-F0-9]{2})([a-fA-F0-9]{2})([a-fA-F0-9]{2})/.exec(l))return[parseInt(k[1],\n16),parseInt(k[2],16),parseInt(k[3],16)];if(k=/#([a-fA-F0-9])([a-fA-F0-9])([a-fA-F0-9])/.exec(l))return[parseInt(k[1]+k[1],16),parseInt(k[2]+k[2],16),parseInt(k[3]+k[3],16)];if(/rgba\\(0, 0, 0, 0\\)/.exec(l))return j.transparent;return j[b.trim(l).toLowerCase()]}function g(l,k){var m;do{m=b.curCSS(l,k);if(m!=""&&m!="transparent"||b.nodeName(l,"body"))break;k="backgroundColor"}while(l=l.parentNode);return f(m)}function e(){var l=document.defaultView?document.defaultView.getComputedStyle(this,null):this.currentStyle,\nk={},m,o;if(l&&l.length&&l[0]&&l[l[0]])for(var p=l.length;p--;){m=l[p];if(typeof l[m]=="string"){o=m.replace(/\\-(\\w)/g,function(s,r){return r.toUpperCase()});k[o]=l[m]}}else for(m in l)if(typeof l[m]==="string")k[m]=l[m];return k}function a(l){var k,m;for(k in l){m=l[k];if(m==null||b.isFunction(m)||k in q||/scrollbar/.test(k)||!/color/i.test(k)&&isNaN(parseFloat(m)))delete l[k]}return l}function d(l,k){var m={_:0},o;for(o in k)if(l[o]!=k[o])m[o]=k[o];return m}function h(l,k,m,o){if(typeof l=="object"){o=\nk;m=null;k=l;l=k.effect}if(b.isFunction(k)){o=k;m=null;k={}}if(typeof k=="number"||b.fx.speeds[k]){o=m;m=k;k={}}if(b.isFunction(m)){o=m;m=null}k=k||{};m=m||k.duration;m=b.fx.off?0:typeof m=="number"?m:m in b.fx.speeds?b.fx.speeds[m]:b.fx.speeds._default;o=o||k.complete;return[l,k,m,o]}function i(l){if(!l||typeof l==="number"||b.fx.speeds[l])return true;if(typeof l==="string"&&!b.effects[l])return true;return false}b.effects={};b.each(["backgroundColor","borderBottomColor","borderLeftColor","borderRightColor",\n"borderTopColor","borderColor","color","outlineColor"],function(l,k){b.fx.step[k]=function(m){if(!m.colorInit){m.start=g(m.elem,k);m.end=f(m.end);m.colorInit=true}m.elem.style[k]="rgb("+Math.max(Math.min(parseInt(m.pos*(m.end[0]-m.start[0])+m.start[0],10),255),0)+","+Math.max(Math.min(parseInt(m.pos*(m.end[1]-m.start[1])+m.start[1],10),255),0)+","+Math.max(Math.min(parseInt(m.pos*(m.end[2]-m.start[2])+m.start[2],10),255),0)+")"}});var j={aqua:[0,255,255],azure:[240,255,255],beige:[245,245,220],black:[0,\n0,0],blue:[0,0,255],brown:[165,42,42],cyan:[0,255,255],darkblue:[0,0,139],darkcyan:[0,139,139],darkgrey:[169,169,169],darkgreen:[0,100,0],darkkhaki:[189,183,107],darkmagenta:[139,0,139],darkolivegreen:[85,107,47],darkorange:[255,140,0],darkorchid:[153,50,204],darkred:[139,0,0],darksalmon:[233,150,122],darkviolet:[148,0,211],fuchsia:[255,0,255],gold:[255,215,0],green:[0,128,0],indigo:[75,0,130],khaki:[240,230,140],lightblue:[173,216,230],lightcyan:[224,255,255],lightgreen:[144,238,144],lightgrey:[211,\n211,211],lightpink:[255,182,193],lightyellow:[255,255,224],lime:[0,255,0],magenta:[255,0,255],maroon:[128,0,0],navy:[0,0,128],olive:[128,128,0],orange:[255,165,0],pink:[255,192,203],purple:[128,0,128],violet:[128,0,128],red:[255,0,0],silver:[192,192,192],white:[255,255,255],yellow:[255,255,0],transparent:[255,255,255]},n=["add","remove","toggle"],q={border:1,borderBottom:1,borderColor:1,borderLeft:1,borderRight:1,borderTop:1,borderWidth:1,margin:1,padding:1};b.effects.animateClass=function(l,k,m,\no){if(b.isFunction(m)){o=m;m=null}return this.queue("fx",function(){var p=b(this),s=p.attr("style")||" ",r=a(e.call(this)),u,v=p.attr("className");b.each(n,function(w,y){l[y]&&p[y+"Class"](l[y])});u=a(e.call(this));p.attr("className",v);p.animate(d(r,u),k,m,function(){b.each(n,function(w,y){l[y]&&p[y+"Class"](l[y])});if(typeof p.attr("style")=="object"){p.attr("style").cssText="";p.attr("style").cssText=s}else p.attr("style",s);o&&o.apply(this,arguments)});r=b.queue(this);u=r.splice(r.length-1,1)[0];\nr.splice(1,0,u);b.dequeue(this)})};b.fn.extend({_addClass:b.fn.addClass,addClass:function(l,k,m,o){return k?b.effects.animateClass.apply(this,[{add:l},k,m,o]):this._addClass(l)},_removeClass:b.fn.removeClass,removeClass:function(l,k,m,o){return k?b.effects.animateClass.apply(this,[{remove:l},k,m,o]):this._removeClass(l)},_toggleClass:b.fn.toggleClass,toggleClass:function(l,k,m,o,p){return typeof k=="boolean"||k===c?m?b.effects.animateClass.apply(this,[k?{add:l}:{remove:l},m,o,p]):this._toggleClass(l,\nk):b.effects.animateClass.apply(this,[{toggle:l},k,m,o])},switchClass:function(l,k,m,o,p){return b.effects.animateClass.apply(this,[{add:k,remove:l},m,o,p])}});b.extend(b.effects,{version:"1.8.9",save:function(l,k){for(var m=0;m<k.length;m++)k[m]!==null&&l.data("ec.storage."+k[m],l[0].style[k[m]])},restore:function(l,k){for(var m=0;m<k.length;m++)k[m]!==null&&l.css(k[m],l.data("ec.storage."+k[m]))},setMode:function(l,k){if(k=="toggle")k=l.is(":hidden")?"show":"hide";return k},getBaseline:function(l,\nk){var m;switch(l[0]){case "top":m=0;break;case "middle":m=0.5;break;case "bottom":m=1;break;default:m=l[0]/k.height}switch(l[1]){case "left":l=0;break;case "center":l=0.5;break;case "right":l=1;break;default:l=l[1]/k.width}return{x:l,y:m}},createWrapper:function(l){if(l.parent().is(".ui-effects-wrapper"))return l.parent();var k={width:l.outerWidth(true),height:l.outerHeight(true),"float":l.css("float")},m=b("<div></div>").addClass("ui-effects-wrapper").css({fontSize:"100%",background:"transparent",\nborder:"none",margin:0,padding:0});l.wrap(m);m=l.parent();if(l.css("position")=="static"){m.css({position:"relative"});l.css({position:"relative"})}else{b.extend(k,{position:l.css("position"),zIndex:l.css("z-index")});b.each(["top","left","bottom","right"],function(o,p){k[p]=l.css(p);if(isNaN(parseInt(k[p],10)))k[p]="auto"});l.css({position:"relative",top:0,left:0,right:"auto",bottom:"auto"})}return m.css(k).show()},removeWrapper:function(l){if(l.parent().is(".ui-effects-wrapper"))return l.parent().replaceWith(l);\nreturn l},setTransition:function(l,k,m,o){o=o||{};b.each(k,function(p,s){unit=l.cssUnit(s);if(unit[0]>0)o[s]=unit[0]*m+unit[1]});return o}});b.fn.extend({effect:function(l){var k=h.apply(this,arguments),m={options:k[1],duration:k[2],callback:k[3]};k=m.options.mode;var o=b.effects[l];if(b.fx.off||!o)return k?this[k](m.duration,m.callback):this.each(function(){m.callback&&m.callback.call(this)});return o.call(this,m)},_show:b.fn.show,show:function(l){if(i(l))return this._show.apply(this,arguments);\nelse{var k=h.apply(this,arguments);k[1].mode="show";return this.effect.apply(this,k)}},_hide:b.fn.hide,hide:function(l){if(i(l))return this._hide.apply(this,arguments);else{var k=h.apply(this,arguments);k[1].mode="hide";return this.effect.apply(this,k)}},__toggle:b.fn.toggle,toggle:function(l){if(i(l)||typeof l==="boolean"||b.isFunction(l))return this.__toggle.apply(this,arguments);else{var k=h.apply(this,arguments);k[1].mode="toggle";return this.effect.apply(this,k)}},cssUnit:function(l){var k=this.css(l),\nm=[];b.each(["em","px","%","pt"],function(o,p){if(k.indexOf(p)>0)m=[parseFloat(k),p]});return m}});b.easing.jswing=b.easing.swing;b.extend(b.easing,{def:"easeOutQuad",swing:function(l,k,m,o,p){return b.easing[b.easing.def](l,k,m,o,p)},easeInQuad:function(l,k,m,o,p){return o*(k/=p)*k+m},easeOutQuad:function(l,k,m,o,p){return-o*(k/=p)*(k-2)+m},easeInOutQuad:function(l,k,m,o,p){if((k/=p/2)<1)return o/2*k*k+m;return-o/2*(--k*(k-2)-1)+m},easeInCubic:function(l,k,m,o,p){return o*(k/=p)*k*k+m},easeOutCubic:function(l,\nk,m,o,p){return o*((k=k/p-1)*k*k+1)+m},easeInOutCubic:function(l,k,m,o,p){if((k/=p/2)<1)return o/2*k*k*k+m;return o/2*((k-=2)*k*k+2)+m},easeInQuart:function(l,k,m,o,p){return o*(k/=p)*k*k*k+m},easeOutQuart:function(l,k,m,o,p){return-o*((k=k/p-1)*k*k*k-1)+m},easeInOutQuart:function(l,k,m,o,p){if((k/=p/2)<1)return o/2*k*k*k*k+m;return-o/2*((k-=2)*k*k*k-2)+m},easeInQuint:function(l,k,m,o,p){return o*(k/=p)*k*k*k*k+m},easeOutQuint:function(l,k,m,o,p){return o*((k=k/p-1)*k*k*k*k+1)+m},easeInOutQuint:function(l,\nk,m,o,p){if((k/=p/2)<1)return o/2*k*k*k*k*k+m;return o/2*((k-=2)*k*k*k*k+2)+m},easeInSine:function(l,k,m,o,p){return-o*Math.cos(k/p*(Math.PI/2))+o+m},easeOutSine:function(l,k,m,o,p){return o*Math.sin(k/p*(Math.PI/2))+m},easeInOutSine:function(l,k,m,o,p){return-o/2*(Math.cos(Math.PI*k/p)-1)+m},easeInExpo:function(l,k,m,o,p){return k==0?m:o*Math.pow(2,10*(k/p-1))+m},easeOutExpo:function(l,k,m,o,p){return k==p?m+o:o*(-Math.pow(2,-10*k/p)+1)+m},easeInOutExpo:function(l,k,m,o,p){if(k==0)return m;if(k==\np)return m+o;if((k/=p/2)<1)return o/2*Math.pow(2,10*(k-1))+m;return o/2*(-Math.pow(2,-10*--k)+2)+m},easeInCirc:function(l,k,m,o,p){return-o*(Math.sqrt(1-(k/=p)*k)-1)+m},easeOutCirc:function(l,k,m,o,p){return o*Math.sqrt(1-(k=k/p-1)*k)+m},easeInOutCirc:function(l,k,m,o,p){if((k/=p/2)<1)return-o/2*(Math.sqrt(1-k*k)-1)+m;return o/2*(Math.sqrt(1-(k-=2)*k)+1)+m},easeInElastic:function(l,k,m,o,p){l=1.70158;var s=0,r=o;if(k==0)return m;if((k/=p)==1)return m+o;s||(s=p*0.3);if(r<Math.abs(o)){r=o;l=s/4}else l=\ns/(2*Math.PI)*Math.asin(o/r);return-(r*Math.pow(2,10*(k-=1))*Math.sin((k*p-l)*2*Math.PI/s))+m},easeOutElastic:function(l,k,m,o,p){l=1.70158;var s=0,r=o;if(k==0)return m;if((k/=p)==1)return m+o;s||(s=p*0.3);if(r<Math.abs(o)){r=o;l=s/4}else l=s/(2*Math.PI)*Math.asin(o/r);return r*Math.pow(2,-10*k)*Math.sin((k*p-l)*2*Math.PI/s)+o+m},easeInOutElastic:function(l,k,m,o,p){l=1.70158;var s=0,r=o;if(k==0)return m;if((k/=p/2)==2)return m+o;s||(s=p*0.3*1.5);if(r<Math.abs(o)){r=o;l=s/4}else l=s/(2*Math.PI)*Math.asin(o/\nr);if(k<1)return-0.5*r*Math.pow(2,10*(k-=1))*Math.sin((k*p-l)*2*Math.PI/s)+m;return r*Math.pow(2,-10*(k-=1))*Math.sin((k*p-l)*2*Math.PI/s)*0.5+o+m},easeInBack:function(l,k,m,o,p,s){if(s==c)s=1.70158;return o*(k/=p)*k*((s+1)*k-s)+m},easeOutBack:function(l,k,m,o,p,s){if(s==c)s=1.70158;return o*((k=k/p-1)*k*((s+1)*k+s)+1)+m},easeInOutBack:function(l,k,m,o,p,s){if(s==c)s=1.70158;if((k/=p/2)<1)return o/2*k*k*(((s*=1.525)+1)*k-s)+m;return o/2*((k-=2)*k*(((s*=1.525)+1)*k+s)+2)+m},easeInBounce:function(l,\nk,m,o,p){return o-b.easing.easeOutBounce(l,p-k,0,o,p)+m},easeOutBounce:function(l,k,m,o,p){return(k/=p)<1/2.75?o*7.5625*k*k+m:k<2/2.75?o*(7.5625*(k-=1.5/2.75)*k+0.75)+m:k<2.5/2.75?o*(7.5625*(k-=2.25/2.75)*k+0.9375)+m:o*(7.5625*(k-=2.625/2.75)*k+0.984375)+m},easeInOutBounce:function(l,k,m,o,p){if(k<p/2)return b.easing.easeInBounce(l,k*2,0,o,p)*0.5+m;return b.easing.easeOutBounce(l,k*2-p,0,o,p)*0.5+o*0.5+m}})}(jQuery);\n(function(b){b.effects.blind=function(c){return this.queue(function(){var f=b(this),g=["position","top","bottom","left","right"],e=b.effects.setMode(f,c.options.mode||"hide"),a=c.options.direction||"vertical";b.effects.save(f,g);f.show();var d=b.effects.createWrapper(f).css({overflow:"hidden"}),h=a=="vertical"?"height":"width";a=a=="vertical"?d.height():d.width();e=="show"&&d.css(h,0);var i={};i[h]=e=="show"?a:0;d.animate(i,c.duration,c.options.easing,function(){e=="hide"&&f.hide();b.effects.restore(f,\ng);b.effects.removeWrapper(f);c.callback&&c.callback.apply(f[0],arguments);f.dequeue()})})}})(jQuery);\n(function(b){b.effects.bounce=function(c){return this.queue(function(){var f=b(this),g=["position","top","bottom","left","right"],e=b.effects.setMode(f,c.options.mode||"effect"),a=c.options.direction||"up",d=c.options.distance||20,h=c.options.times||5,i=c.duration||250;/show|hide/.test(e)&&g.push("opacity");b.effects.save(f,g);f.show();b.effects.createWrapper(f);var j=a=="up"||a=="down"?"top":"left";a=a=="up"||a=="left"?"pos":"neg";d=c.options.distance||(j=="top"?f.outerHeight({margin:true})/3:f.outerWidth({margin:true})/\n3);if(e=="show")f.css("opacity",0).css(j,a=="pos"?-d:d);if(e=="hide")d/=h*2;e!="hide"&&h--;if(e=="show"){var n={opacity:1};n[j]=(a=="pos"?"+=":"-=")+d;f.animate(n,i/2,c.options.easing);d/=2;h--}for(n=0;n<h;n++){var q={},l={};q[j]=(a=="pos"?"-=":"+=")+d;l[j]=(a=="pos"?"+=":"-=")+d;f.animate(q,i/2,c.options.easing).animate(l,i/2,c.options.easing);d=e=="hide"?d*2:d/2}if(e=="hide"){n={opacity:0};n[j]=(a=="pos"?"-=":"+=")+d;f.animate(n,i/2,c.options.easing,function(){f.hide();b.effects.restore(f,g);b.effects.removeWrapper(f);\nc.callback&&c.callback.apply(this,arguments)})}else{q={};l={};q[j]=(a=="pos"?"-=":"+=")+d;l[j]=(a=="pos"?"+=":"-=")+d;f.animate(q,i/2,c.options.easing).animate(l,i/2,c.options.easing,function(){b.effects.restore(f,g);b.effects.removeWrapper(f);c.callback&&c.callback.apply(this,arguments)})}f.queue("fx",function(){f.dequeue()});f.dequeue()})}})(jQuery);\n(function(b){b.effects.clip=function(c){return this.queue(function(){var f=b(this),g=["position","top","bottom","left","right","height","width"],e=b.effects.setMode(f,c.options.mode||"hide"),a=c.options.direction||"vertical";b.effects.save(f,g);f.show();var d=b.effects.createWrapper(f).css({overflow:"hidden"});d=f[0].tagName=="IMG"?d:f;var h={size:a=="vertical"?"height":"width",position:a=="vertical"?"top":"left"};a=a=="vertical"?d.height():d.width();if(e=="show"){d.css(h.size,0);d.css(h.position,\na/2)}var i={};i[h.size]=e=="show"?a:0;i[h.position]=e=="show"?0:a/2;d.animate(i,{queue:false,duration:c.duration,easing:c.options.easing,complete:function(){e=="hide"&&f.hide();b.effects.restore(f,g);b.effects.removeWrapper(f);c.callback&&c.callback.apply(f[0],arguments);f.dequeue()}})})}})(jQuery);\n(function(b){b.effects.drop=function(c){return this.queue(function(){var f=b(this),g=["position","top","bottom","left","right","opacity"],e=b.effects.setMode(f,c.options.mode||"hide"),a=c.options.direction||"left";b.effects.save(f,g);f.show();b.effects.createWrapper(f);var d=a=="up"||a=="down"?"top":"left";a=a=="up"||a=="left"?"pos":"neg";var h=c.options.distance||(d=="top"?f.outerHeight({margin:true})/2:f.outerWidth({margin:true})/2);if(e=="show")f.css("opacity",0).css(d,a=="pos"?-h:h);var i={opacity:e==\n"show"?1:0};i[d]=(e=="show"?a=="pos"?"+=":"-=":a=="pos"?"-=":"+=")+h;f.animate(i,{queue:false,duration:c.duration,easing:c.options.easing,complete:function(){e=="hide"&&f.hide();b.effects.restore(f,g);b.effects.removeWrapper(f);c.callback&&c.callback.apply(this,arguments);f.dequeue()}})})}})(jQuery);\n(function(b){b.effects.explode=function(c){return this.queue(function(){var f=c.options.pieces?Math.round(Math.sqrt(c.options.pieces)):3,g=c.options.pieces?Math.round(Math.sqrt(c.options.pieces)):3;c.options.mode=c.options.mode=="toggle"?b(this).is(":visible")?"hide":"show":c.options.mode;var e=b(this).show().css("visibility","hidden"),a=e.offset();a.top-=parseInt(e.css("marginTop"),10)||0;a.left-=parseInt(e.css("marginLeft"),10)||0;for(var d=e.outerWidth(true),h=e.outerHeight(true),i=0;i<f;i++)for(var j=\n0;j<g;j++)e.clone().appendTo("body").wrap("<div></div>").css({position:"absolute",visibility:"visible",left:-j*(d/g),top:-i*(h/f)}).parent().addClass("ui-effects-explode").css({position:"absolute",overflow:"hidden",width:d/g,height:h/f,left:a.left+j*(d/g)+(c.options.mode=="show"?(j-Math.floor(g/2))*(d/g):0),top:a.top+i*(h/f)+(c.options.mode=="show"?(i-Math.floor(f/2))*(h/f):0),opacity:c.options.mode=="show"?0:1}).animate({left:a.left+j*(d/g)+(c.options.mode=="show"?0:(j-Math.floor(g/2))*(d/g)),top:a.top+\ni*(h/f)+(c.options.mode=="show"?0:(i-Math.floor(f/2))*(h/f)),opacity:c.options.mode=="show"?1:0},c.duration||500);setTimeout(function(){c.options.mode=="show"?e.css({visibility:"visible"}):e.css({visibility:"visible"}).hide();c.callback&&c.callback.apply(e[0]);e.dequeue();b("div.ui-effects-explode").remove()},c.duration||500)})}})(jQuery);\n(function(b){b.effects.fade=function(c){return this.queue(function(){var f=b(this),g=b.effects.setMode(f,c.options.mode||"hide");f.animate({opacity:g},{queue:false,duration:c.duration,easing:c.options.easing,complete:function(){c.callback&&c.callback.apply(this,arguments);f.dequeue()}})})}})(jQuery);\n(function(b){b.effects.fold=function(c){return this.queue(function(){var f=b(this),g=["position","top","bottom","left","right"],e=b.effects.setMode(f,c.options.mode||"hide"),a=c.options.size||15,d=!!c.options.horizFirst,h=c.duration?c.duration/2:b.fx.speeds._default/2;b.effects.save(f,g);f.show();var i=b.effects.createWrapper(f).css({overflow:"hidden"}),j=e=="show"!=d,n=j?["width","height"]:["height","width"];j=j?[i.width(),i.height()]:[i.height(),i.width()];var q=/([0-9]+)%/.exec(a);if(q)a=parseInt(q[1],\n10)/100*j[e=="hide"?0:1];if(e=="show")i.css(d?{height:0,width:a}:{height:a,width:0});d={};q={};d[n[0]]=e=="show"?j[0]:a;q[n[1]]=e=="show"?j[1]:0;i.animate(d,h,c.options.easing).animate(q,h,c.options.easing,function(){e=="hide"&&f.hide();b.effects.restore(f,g);b.effects.removeWrapper(f);c.callback&&c.callback.apply(f[0],arguments);f.dequeue()})})}})(jQuery);\n(function(b){b.effects.highlight=function(c){return this.queue(function(){var f=b(this),g=["backgroundImage","backgroundColor","opacity"],e=b.effects.setMode(f,c.options.mode||"show"),a={backgroundColor:f.css("backgroundColor")};if(e=="hide")a.opacity=0;b.effects.save(f,g);f.show().css({backgroundImage:"none",backgroundColor:c.options.color||"#ffff99"}).animate(a,{queue:false,duration:c.duration,easing:c.options.easing,complete:function(){e=="hide"&&f.hide();b.effects.restore(f,g);e=="show"&&!b.support.opacity&&\nthis.style.removeAttribute("filter");c.callback&&c.callback.apply(this,arguments);f.dequeue()}})})}})(jQuery);\n(function(b){b.effects.pulsate=function(c){return this.queue(function(){var f=b(this),g=b.effects.setMode(f,c.options.mode||"show");times=(c.options.times||5)*2-1;duration=c.duration?c.duration/2:b.fx.speeds._default/2;isVisible=f.is(":visible");animateTo=0;if(!isVisible){f.css("opacity",0).show();animateTo=1}if(g=="hide"&&isVisible||g=="show"&&!isVisible)times--;for(g=0;g<times;g++){f.animate({opacity:animateTo},duration,c.options.easing);animateTo=(animateTo+1)%2}f.animate({opacity:animateTo},duration,\nc.options.easing,function(){animateTo==0&&f.hide();c.callback&&c.callback.apply(this,arguments)});f.queue("fx",function(){f.dequeue()}).dequeue()})}})(jQuery);\n(function(b){b.effects.puff=function(c){return this.queue(function(){var f=b(this),g=b.effects.setMode(f,c.options.mode||"hide"),e=parseInt(c.options.percent,10)||150,a=e/100,d={height:f.height(),width:f.width()};b.extend(c.options,{fade:true,mode:g,percent:g=="hide"?e:100,from:g=="hide"?d:{height:d.height*a,width:d.width*a}});f.effect("scale",c.options,c.duration,c.callback);f.dequeue()})};b.effects.scale=function(c){return this.queue(function(){var f=b(this),g=b.extend(true,{},c.options),e=b.effects.setMode(f,\nc.options.mode||"effect"),a=parseInt(c.options.percent,10)||(parseInt(c.options.percent,10)==0?0:e=="hide"?0:100),d=c.options.direction||"both",h=c.options.origin;if(e!="effect"){g.origin=h||["middle","center"];g.restore=true}h={height:f.height(),width:f.width()};f.from=c.options.from||(e=="show"?{height:0,width:0}:h);a={y:d!="horizontal"?a/100:1,x:d!="vertical"?a/100:1};f.to={height:h.height*a.y,width:h.width*a.x};if(c.options.fade){if(e=="show"){f.from.opacity=0;f.to.opacity=1}if(e=="hide"){f.from.opacity=\n1;f.to.opacity=0}}g.from=f.from;g.to=f.to;g.mode=e;f.effect("size",g,c.duration,c.callback);f.dequeue()})};b.effects.size=function(c){return this.queue(function(){var f=b(this),g=["position","top","bottom","left","right","width","height","overflow","opacity"],e=["position","top","bottom","left","right","overflow","opacity"],a=["width","height","overflow"],d=["fontSize"],h=["borderTopWidth","borderBottomWidth","paddingTop","paddingBottom"],i=["borderLeftWidth","borderRightWidth","paddingLeft","paddingRight"],\nj=b.effects.setMode(f,c.options.mode||"effect"),n=c.options.restore||false,q=c.options.scale||"both",l=c.options.origin,k={height:f.height(),width:f.width()};f.from=c.options.from||k;f.to=c.options.to||k;if(l){l=b.effects.getBaseline(l,k);f.from.top=(k.height-f.from.height)*l.y;f.from.left=(k.width-f.from.width)*l.x;f.to.top=(k.height-f.to.height)*l.y;f.to.left=(k.width-f.to.width)*l.x}var m={from:{y:f.from.height/k.height,x:f.from.width/k.width},to:{y:f.to.height/k.height,x:f.to.width/k.width}};\nif(q=="box"||q=="both"){if(m.from.y!=m.to.y){g=g.concat(h);f.from=b.effects.setTransition(f,h,m.from.y,f.from);f.to=b.effects.setTransition(f,h,m.to.y,f.to)}if(m.from.x!=m.to.x){g=g.concat(i);f.from=b.effects.setTransition(f,i,m.from.x,f.from);f.to=b.effects.setTransition(f,i,m.to.x,f.to)}}if(q=="content"||q=="both")if(m.from.y!=m.to.y){g=g.concat(d);f.from=b.effects.setTransition(f,d,m.from.y,f.from);f.to=b.effects.setTransition(f,d,m.to.y,f.to)}b.effects.save(f,n?g:e);f.show();b.effects.createWrapper(f);\nf.css("overflow","hidden").css(f.from);if(q=="content"||q=="both"){h=h.concat(["marginTop","marginBottom"]).concat(d);i=i.concat(["marginLeft","marginRight"]);a=g.concat(h).concat(i);f.find("*[width]").each(function(){child=b(this);n&&b.effects.save(child,a);var o={height:child.height(),width:child.width()};child.from={height:o.height*m.from.y,width:o.width*m.from.x};child.to={height:o.height*m.to.y,width:o.width*m.to.x};if(m.from.y!=m.to.y){child.from=b.effects.setTransition(child,h,m.from.y,child.from);\nchild.to=b.effects.setTransition(child,h,m.to.y,child.to)}if(m.from.x!=m.to.x){child.from=b.effects.setTransition(child,i,m.from.x,child.from);child.to=b.effects.setTransition(child,i,m.to.x,child.to)}child.css(child.from);child.animate(child.to,c.duration,c.options.easing,function(){n&&b.effects.restore(child,a)})})}f.animate(f.to,{queue:false,duration:c.duration,easing:c.options.easing,complete:function(){f.to.opacity===0&&f.css("opacity",f.from.opacity);j=="hide"&&f.hide();b.effects.restore(f,\nn?g:e);b.effects.removeWrapper(f);c.callback&&c.callback.apply(this,arguments);f.dequeue()}})})}})(jQuery);\n(function(b){b.effects.shake=function(c){return this.queue(function(){var f=b(this),g=["position","top","bottom","left","right"];b.effects.setMode(f,c.options.mode||"effect");var e=c.options.direction||"left",a=c.options.distance||20,d=c.options.times||3,h=c.duration||c.options.duration||140;b.effects.save(f,g);f.show();b.effects.createWrapper(f);var i=e=="up"||e=="down"?"top":"left",j=e=="up"||e=="left"?"pos":"neg";e={};var n={},q={};e[i]=(j=="pos"?"-=":"+=")+a;n[i]=(j=="pos"?"+=":"-=")+a*2;q[i]=\n(j=="pos"?"-=":"+=")+a*2;f.animate(e,h,c.options.easing);for(a=1;a<d;a++)f.animate(n,h,c.options.easing).animate(q,h,c.options.easing);f.animate(n,h,c.options.easing).animate(e,h/2,c.options.easing,function(){b.effects.restore(f,g);b.effects.removeWrapper(f);c.callback&&c.callback.apply(this,arguments)});f.queue("fx",function(){f.dequeue()});f.dequeue()})}})(jQuery);\n(function(b){b.effects.slide=function(c){return this.queue(function(){var f=b(this),g=["position","top","bottom","left","right"],e=b.effects.setMode(f,c.options.mode||"show"),a=c.options.direction||"left";b.effects.save(f,g);f.show();b.effects.createWrapper(f).css({overflow:"hidden"});var d=a=="up"||a=="down"?"top":"left";a=a=="up"||a=="left"?"pos":"neg";var h=c.options.distance||(d=="top"?f.outerHeight({margin:true}):f.outerWidth({margin:true}));if(e=="show")f.css(d,a=="pos"?isNaN(h)?"-"+h:-h:h);\nvar i={};i[d]=(e=="show"?a=="pos"?"+=":"-=":a=="pos"?"-=":"+=")+h;f.animate(i,{queue:false,duration:c.duration,easing:c.options.easing,complete:function(){e=="hide"&&f.hide();b.effects.restore(f,g);b.effects.removeWrapper(f);c.callback&&c.callback.apply(this,arguments);f.dequeue()}})})}})(jQuery);\n(function(b){b.effects.transfer=function(c){return this.queue(function(){var f=b(this),g=b(c.options.to),e=g.offset();g={top:e.top,left:e.left,height:g.innerHeight(),width:g.innerWidth()};e=f.offset();var a=b(\'<div class="ui-effects-transfer"></div>\').appendTo(document.body).addClass(c.options.className).css({top:e.top,left:e.left,height:f.innerHeight(),width:f.innerWidth(),position:"absolute"}).animate(g,c.duration,c.options.easing,function(){a.remove();c.callback&&c.callback.apply(f[0],arguments);\nf.dequeue()})})}})(jQuery);\n(function(b){b.widget("ui.accordion",{options:{active:0,animated:"slide",autoHeight:true,clearStyle:false,collapsible:false,event:"click",fillSpace:false,header:"> li > :first-child,> :not(li):even",icons:{header:"ui-icon-triangle-1-e",headerSelected:"ui-icon-triangle-1-s"},navigation:false,navigationFilter:function(){return this.href.toLowerCase()===location.href.toLowerCase()}},_create:function(){var c=this,f=c.options;c.running=0;c.element.addClass("ui-accordion ui-widget ui-helper-reset").children("li").addClass("ui-accordion-li-fix");c.headers=\nc.element.find(f.header).addClass("ui-accordion-header ui-helper-reset ui-state-default ui-corner-all").bind("mouseenter.accordion",function(){f.disabled||b(this).addClass("ui-state-hover")}).bind("mouseleave.accordion",function(){f.disabled||b(this).removeClass("ui-state-hover")}).bind("focus.accordion",function(){f.disabled||b(this).addClass("ui-state-focus")}).bind("blur.accordion",function(){f.disabled||b(this).removeClass("ui-state-focus")});c.headers.next().addClass("ui-accordion-content ui-helper-reset ui-widget-content ui-corner-bottom");\nif(f.navigation){var g=c.element.find("a").filter(f.navigationFilter).eq(0);if(g.length){var e=g.closest(".ui-accordion-header");c.active=e.length?e:g.closest(".ui-accordion-content").prev()}}c.active=c._findActive(c.active||f.active).addClass("ui-state-default ui-state-active").toggleClass("ui-corner-all").toggleClass("ui-corner-top");c.active.next().addClass("ui-accordion-content-active");c._createIcons();c.resize();c.element.attr("role","tablist");c.headers.attr("role","tab").bind("keydown.accordion",\nfunction(a){return c._keydown(a)}).next().attr("role","tabpanel");c.headers.not(c.active||"").attr({"aria-expanded":"false",tabIndex:-1}).next().hide();c.active.length?c.active.attr({"aria-expanded":"true",tabIndex:0}):c.headers.eq(0).attr("tabIndex",0);b.browser.safari||c.headers.find("a").attr("tabIndex",-1);f.event&&c.headers.bind(f.event.split(" ").join(".accordion ")+".accordion",function(a){c._clickHandler.call(c,a,this);a.preventDefault()})},_createIcons:function(){var c=this.options;if(c.icons){b("<span></span>").addClass("ui-icon "+\nc.icons.header).prependTo(this.headers);this.active.children(".ui-icon").toggleClass(c.icons.header).toggleClass(c.icons.headerSelected);this.element.addClass("ui-accordion-icons")}},_destroyIcons:function(){this.headers.children(".ui-icon").remove();this.element.removeClass("ui-accordion-icons")},destroy:function(){var c=this.options;this.element.removeClass("ui-accordion ui-widget ui-helper-reset").removeAttr("role");this.headers.unbind(".accordion").removeClass("ui-accordion-header ui-accordion-disabled ui-helper-reset ui-state-default ui-corner-all ui-state-active ui-state-disabled ui-corner-top").removeAttr("role").removeAttr("aria-expanded").removeAttr("tabIndex");\nthis.headers.find("a").removeAttr("tabIndex");this._destroyIcons();var f=this.headers.next().css("display","").removeAttr("role").removeClass("ui-helper-reset ui-widget-content ui-corner-bottom ui-accordion-content ui-accordion-content-active ui-accordion-disabled ui-state-disabled");if(c.autoHeight||c.fillHeight)f.css("height","");return b.Widget.prototype.destroy.call(this)},_setOption:function(c,f){b.Widget.prototype._setOption.apply(this,arguments);c=="active"&&this.activate(f);if(c=="icons"){this._destroyIcons();\nf&&this._createIcons()}if(c=="disabled")this.headers.add(this.headers.next())[f?"addClass":"removeClass"]("ui-accordion-disabled ui-state-disabled")},_keydown:function(c){if(!(this.options.disabled||c.altKey||c.ctrlKey)){var f=b.ui.keyCode,g=this.headers.length,e=this.headers.index(c.target),a=false;switch(c.keyCode){case f.RIGHT:case f.DOWN:a=this.headers[(e+1)%g];break;case f.LEFT:case f.UP:a=this.headers[(e-1+g)%g];break;case f.SPACE:case f.ENTER:this._clickHandler({target:c.target},c.target);\nc.preventDefault()}if(a){b(c.target).attr("tabIndex",-1);b(a).attr("tabIndex",0);a.focus();return false}return true}},resize:function(){var c=this.options,f;if(c.fillSpace){if(b.browser.msie){var g=this.element.parent().css("overflow");this.element.parent().css("overflow","hidden")}f=this.element.parent().height();b.browser.msie&&this.element.parent().css("overflow",g);this.headers.each(function(){f-=b(this).outerHeight(true)});this.headers.next().each(function(){b(this).height(Math.max(0,f-b(this).innerHeight()+\nb(this).height()))}).css("overflow","auto")}else if(c.autoHeight){f=0;this.headers.next().each(function(){f=Math.max(f,b(this).height("").height())}).height(f)}return this},activate:function(c){this.options.active=c;c=this._findActive(c)[0];this._clickHandler({target:c},c);return this},_findActive:function(c){return c?typeof c==="number"?this.headers.filter(":eq("+c+")"):this.headers.not(this.headers.not(c)):c===false?b([]):this.headers.filter(":eq(0)")},_clickHandler:function(c,f){var g=this.options;\nif(!g.disabled)if(c.target){c=b(c.currentTarget||f);f=c[0]===this.active[0];g.active=g.collapsible&&f?false:this.headers.index(c);if(!(this.running||!g.collapsible&&f)){var e=this.active;i=c.next();d=this.active.next();h={options:g,newHeader:f&&g.collapsible?b([]):c,oldHeader:this.active,newContent:f&&g.collapsible?b([]):i,oldContent:d};var a=this.headers.index(this.active[0])>this.headers.index(c[0]);this.active=f?b([]):c;this._toggle(i,d,h,f,a);e.removeClass("ui-state-active ui-corner-top").addClass("ui-state-default ui-corner-all").children(".ui-icon").removeClass(g.icons.headerSelected).addClass(g.icons.header);\nif(!f){c.removeClass("ui-state-default ui-corner-all").addClass("ui-state-active ui-corner-top").children(".ui-icon").removeClass(g.icons.header).addClass(g.icons.headerSelected);c.next().addClass("ui-accordion-content-active")}}}else if(g.collapsible){this.active.removeClass("ui-state-active ui-corner-top").addClass("ui-state-default ui-corner-all").children(".ui-icon").removeClass(g.icons.headerSelected).addClass(g.icons.header);this.active.next().addClass("ui-accordion-content-active");var d=this.active.next(),\nh={options:g,newHeader:b([]),oldHeader:g.active,newContent:b([]),oldContent:d},i=this.active=b([]);this._toggle(i,d,h)}},_toggle:function(c,f,g,e,a){var d=this,h=d.options;d.toShow=c;d.toHide=f;d.data=g;var i=function(){if(d)return d._completed.apply(d,arguments)};d._trigger("changestart",null,d.data);d.running=f.size()===0?c.size():f.size();if(h.animated){g={};g=h.collapsible&&e?{toShow:b([]),toHide:f,complete:i,down:a,autoHeight:h.autoHeight||h.fillSpace}:{toShow:c,toHide:f,complete:i,down:a,autoHeight:h.autoHeight||\nh.fillSpace};if(!h.proxied)h.proxied=h.animated;if(!h.proxiedDuration)h.proxiedDuration=h.duration;h.animated=b.isFunction(h.proxied)?h.proxied(g):h.proxied;h.duration=b.isFunction(h.proxiedDuration)?h.proxiedDuration(g):h.proxiedDuration;e=b.ui.accordion.animations;var j=h.duration,n=h.animated;if(n&&!e[n]&&!b.easing[n])n="slide";e[n]||(e[n]=function(q){this.slide(q,{easing:n,duration:j||700})});e[n](g)}else{if(h.collapsible&&e)c.toggle();else{f.hide();c.show()}i(true)}f.prev().attr({"aria-expanded":"false",\ntabIndex:-1}).blur();c.prev().attr({"aria-expanded":"true",tabIndex:0}).focus()},_completed:function(c){this.running=c?0:--this.running;if(!this.running){this.options.clearStyle&&this.toShow.add(this.toHide).css({height:"",overflow:""});this.toHide.removeClass("ui-accordion-content-active");if(this.toHide.length)this.toHide.parent()[0].className=this.toHide.parent()[0].className;this._trigger("change",null,this.data)}}});b.extend(b.ui.accordion,{version:"1.8.9",animations:{slide:function(c,f){c=\nb.extend({easing:"swing",duration:300},c,f);if(c.toHide.size())if(c.toShow.size()){var g=c.toShow.css("overflow"),e=0,a={},d={},h;f=c.toShow;h=f[0].style.width;f.width(parseInt(f.parent().width(),10)-parseInt(f.css("paddingLeft"),10)-parseInt(f.css("paddingRight"),10)-(parseInt(f.css("borderLeftWidth"),10)||0)-(parseInt(f.css("borderRightWidth"),10)||0));b.each(["height","paddingTop","paddingBottom"],function(i,j){d[j]="hide";i=(""+b.css(c.toShow[0],j)).match(/^([\\d+-.]+)(.*)$/);a[j]={value:i[1],\nunit:i[2]||"px"}});c.toShow.css({height:0,overflow:"hidden"}).show();c.toHide.filter(":hidden").each(c.complete).end().filter(":visible").animate(d,{step:function(i,j){if(j.prop=="height")e=j.end-j.start===0?0:(j.now-j.start)/(j.end-j.start);c.toShow[0].style[j.prop]=e*a[j.prop].value+a[j.prop].unit},duration:c.duration,easing:c.easing,complete:function(){c.autoHeight||c.toShow.css("height","");c.toShow.css({width:h,overflow:g});c.complete()}})}else c.toHide.animate({height:"hide",paddingTop:"hide",\npaddingBottom:"hide"},c);else c.toShow.animate({height:"show",paddingTop:"show",paddingBottom:"show"},c)},bounceslide:function(c){this.slide(c,{easing:c.down?"easeOutBounce":"swing",duration:c.down?1E3:200})}}})})(jQuery);\n(function(b){b.widget("ui.autocomplete",{options:{appendTo:"body",delay:300,minLength:1,position:{my:"left top",at:"left bottom",collision:"none"},source:null},pending:0,_create:function(){var c=this,f=this.element[0].ownerDocument,g;this.element.addClass("ui-autocomplete-input").attr("autocomplete","off").attr({role:"textbox","aria-autocomplete":"list","aria-haspopup":"true"}).bind("keydown.autocomplete",function(e){if(!(c.options.disabled||c.element.attr("readonly"))){g=false;var a=b.ui.keyCode;\nswitch(e.keyCode){case a.PAGE_UP:c._move("previousPage",e);break;case a.PAGE_DOWN:c._move("nextPage",e);break;case a.UP:c._move("previous",e);e.preventDefault();break;case a.DOWN:c._move("next",e);e.preventDefault();break;case a.ENTER:case a.NUMPAD_ENTER:if(c.menu.active){g=true;e.preventDefault()}case a.TAB:if(!c.menu.active)return;c.menu.select(e);break;case a.ESCAPE:c.element.val(c.term);c.close(e);break;default:clearTimeout(c.searching);c.searching=setTimeout(function(){if(c.term!=c.element.val()){c.selectedItem=\nnull;c.search(null,e)}},c.options.delay);break}}}).bind("keypress.autocomplete",function(e){if(g){g=false;e.preventDefault()}}).bind("focus.autocomplete",function(){if(!c.options.disabled){c.selectedItem=null;c.previous=c.element.val()}}).bind("blur.autocomplete",function(e){if(!c.options.disabled){clearTimeout(c.searching);c.closing=setTimeout(function(){c.close(e);c._change(e)},150)}});this._initSource();this.response=function(){return c._response.apply(c,arguments)};this.menu=b("<ul></ul>").addClass("ui-autocomplete").appendTo(b(this.options.appendTo||\n"body",f)[0]).mousedown(function(e){var a=c.menu.element[0];b(e.target).closest(".ui-menu-item").length||setTimeout(function(){b(document).one("mousedown",function(d){d.target!==c.element[0]&&d.target!==a&&!b.ui.contains(a,d.target)&&c.close()})},1);setTimeout(function(){clearTimeout(c.closing)},13)}).menu({focus:function(e,a){a=a.item.data("item.autocomplete");false!==c._trigger("focus",e,{item:a})&&/^key/.test(e.originalEvent.type)&&c.element.val(a.value)},selected:function(e,a){var d=a.item.data("item.autocomplete"),\nh=c.previous;if(c.element[0]!==f.activeElement){c.element.focus();c.previous=h;setTimeout(function(){c.previous=h;c.selectedItem=d},1)}false!==c._trigger("select",e,{item:d})&&c.element.val(d.value);c.term=c.element.val();c.close(e);c.selectedItem=d},blur:function(){c.menu.element.is(":visible")&&c.element.val()!==c.term&&c.element.val(c.term)}}).zIndex(this.element.zIndex()+1).css({top:0,left:0}).hide().data("menu");b.fn.bgiframe&&this.menu.element.bgiframe()},destroy:function(){this.element.removeClass("ui-autocomplete-input").removeAttr("autocomplete").removeAttr("role").removeAttr("aria-autocomplete").removeAttr("aria-haspopup");\nthis.menu.element.remove();b.Widget.prototype.destroy.call(this)},_setOption:function(c,f){b.Widget.prototype._setOption.apply(this,arguments);c==="source"&&this._initSource();if(c==="appendTo")this.menu.element.appendTo(b(f||"body",this.element[0].ownerDocument)[0]);c==="disabled"&&f&&this.xhr&&this.xhr.abort()},_initSource:function(){var c=this,f,g;if(b.isArray(this.options.source)){f=this.options.source;this.source=function(e,a){a(b.ui.autocomplete.filter(f,e.term))}}else if(typeof this.options.source===\n"string"){g=this.options.source;this.source=function(e,a){c.xhr&&c.xhr.abort();c.xhr=b.ajax({url:g,data:e,dataType:"json",success:function(d,h,i){i===c.xhr&&a(d);c.xhr=null},error:function(d){d===c.xhr&&a([]);c.xhr=null}})}}else this.source=this.options.source},search:function(c,f){c=c!=null?c:this.element.val();this.term=this.element.val();if(c.length<this.options.minLength)return this.close(f);clearTimeout(this.closing);if(this._trigger("search",f)!==false)return this._search(c)},_search:function(c){this.pending++;\nthis.element.addClass("ui-autocomplete-loading");this.source({term:c},this.response)},_response:function(c){if(!this.options.disabled&&c&&c.length){c=this._normalize(c);this._suggest(c);this._trigger("open")}else this.close();this.pending--;this.pending||this.element.removeClass("ui-autocomplete-loading")},close:function(c){clearTimeout(this.closing);if(this.menu.element.is(":visible")){this.menu.element.hide();this.menu.deactivate();this._trigger("close",c)}},_change:function(c){this.previous!==\nthis.element.val()&&this._trigger("change",c,{item:this.selectedItem})},_normalize:function(c){if(c.length&&c[0].label&&c[0].value)return c;return b.map(c,function(f){if(typeof f==="string")return{label:f,value:f};return b.extend({label:f.label||f.value,value:f.value||f.label},f)})},_suggest:function(c){var f=this.menu.element.empty().zIndex(this.element.zIndex()+1);this._renderMenu(f,c);this.menu.deactivate();this.menu.refresh();f.show();this._resizeMenu();f.position(b.extend({of:this.element},this.options.position))},\n_resizeMenu:function(){var c=this.menu.element;c.outerWidth(Math.max(c.width("").outerWidth(),this.element.outerWidth()))},_renderMenu:function(c,f){var g=this;b.each(f,function(e,a){g._renderItem(c,a)})},_renderItem:function(c,f){return b("<li></li>").data("item.autocomplete",f).append(b("<a></a>").text(f.label)).appendTo(c)},_move:function(c,f){if(this.menu.element.is(":visible"))if(this.menu.first()&&/^previous/.test(c)||this.menu.last()&&/^next/.test(c)){this.element.val(this.term);this.menu.deactivate()}else this.menu[c](f);\nelse this.search(null,f)},widget:function(){return this.menu.element}});b.extend(b.ui.autocomplete,{escapeRegex:function(c){return c.replace(/[-[\\]{}()*+?.,\\\\^$|#\\s]/g,"\\\\$&")},filter:function(c,f){var g=new RegExp(b.ui.autocomplete.escapeRegex(f),"i");return b.grep(c,function(e){return g.test(e.label||e.value||e)})}})})(jQuery);\n(function(b){b.widget("ui.menu",{_create:function(){var c=this;this.element.addClass("ui-menu ui-widget ui-widget-content ui-corner-all").attr({role:"listbox","aria-activedescendant":"ui-active-menuitem"}).click(function(f){if(b(f.target).closest(".ui-menu-item a").length){f.preventDefault();c.select(f)}});this.refresh()},refresh:function(){var c=this;this.element.children("li:not(.ui-menu-item):has(a)").addClass("ui-menu-item").attr("role","menuitem").children("a").addClass("ui-corner-all").attr("tabindex",\n-1).mouseenter(function(f){c.activate(f,b(this).parent())}).mouseleave(function(){c.deactivate()})},activate:function(c,f){this.deactivate();if(this.hasScroll()){var g=f.offset().top-this.element.offset().top,e=this.element.attr("scrollTop"),a=this.element.height();if(g<0)this.element.attr("scrollTop",e+g);else g>=a&&this.element.attr("scrollTop",e+g-a+f.height())}this.active=f.eq(0).children("a").addClass("ui-state-hover").attr("id","ui-active-menuitem").end();this._trigger("focus",c,{item:f})},\ndeactivate:function(){if(this.active){this.active.children("a").removeClass("ui-state-hover").removeAttr("id");this._trigger("blur");this.active=null}},next:function(c){this.move("next",".ui-menu-item:first",c)},previous:function(c){this.move("prev",".ui-menu-item:last",c)},first:function(){return this.active&&!this.active.prevAll(".ui-menu-item").length},last:function(){return this.active&&!this.active.nextAll(".ui-menu-item").length},move:function(c,f,g){if(this.active){c=this.active[c+"All"](".ui-menu-item").eq(0);\nc.length?this.activate(g,c):this.activate(g,this.element.children(f))}else this.activate(g,this.element.children(f))},nextPage:function(c){if(this.hasScroll())if(!this.active||this.last())this.activate(c,this.element.children(".ui-menu-item:first"));else{var f=this.active.offset().top,g=this.element.height(),e=this.element.children(".ui-menu-item").filter(function(){var a=b(this).offset().top-f-g+b(this).height();return a<10&&a>-10});e.length||(e=this.element.children(".ui-menu-item:last"));this.activate(c,\ne)}else this.activate(c,this.element.children(".ui-menu-item").filter(!this.active||this.last()?":first":":last"))},previousPage:function(c){if(this.hasScroll())if(!this.active||this.first())this.activate(c,this.element.children(".ui-menu-item:last"));else{var f=this.active.offset().top,g=this.element.height();result=this.element.children(".ui-menu-item").filter(function(){var e=b(this).offset().top-f+g-b(this).height();return e<10&&e>-10});result.length||(result=this.element.children(".ui-menu-item:first"));\nthis.activate(c,result)}else this.activate(c,this.element.children(".ui-menu-item").filter(!this.active||this.first()?":last":":first"))},hasScroll:function(){return this.element.height()<this.element.attr("scrollHeight")},select:function(c){this._trigger("selected",c,{item:this.active})}})})(jQuery);\n(function(b){var c,f=function(e){b(":ui-button",e.target.form).each(function(){var a=b(this).data("button");setTimeout(function(){a.refresh()},1)})},g=function(e){var a=e.name,d=e.form,h=b([]);if(a)h=d?b(d).find("[name=\'"+a+"\']"):b("[name=\'"+a+"\']",e.ownerDocument).filter(function(){return!this.form});return h};b.widget("ui.button",{options:{disabled:null,text:true,label:null,icons:{primary:null,secondary:null}},_create:function(){this.element.closest("form").unbind("reset.button").bind("reset.button",\nf);if(typeof this.options.disabled!=="boolean")this.options.disabled=this.element.attr("disabled");this._determineButtonType();this.hasTitle=!!this.buttonElement.attr("title");var e=this,a=this.options,d=this.type==="checkbox"||this.type==="radio",h="ui-state-hover"+(!d?" ui-state-active":"");if(a.label===null)a.label=this.buttonElement.html();if(this.element.is(":disabled"))a.disabled=true;this.buttonElement.addClass("ui-button ui-widget ui-state-default ui-corner-all").attr("role","button").bind("mouseenter.button",\nfunction(){if(!a.disabled){b(this).addClass("ui-state-hover");this===c&&b(this).addClass("ui-state-active")}}).bind("mouseleave.button",function(){a.disabled||b(this).removeClass(h)}).bind("focus.button",function(){b(this).addClass("ui-state-focus")}).bind("blur.button",function(){b(this).removeClass("ui-state-focus")});d&&this.element.bind("change.button",function(){e.refresh()});if(this.type==="checkbox")this.buttonElement.bind("click.button",function(){if(a.disabled)return false;b(this).toggleClass("ui-state-active");\ne.buttonElement.attr("aria-pressed",e.element[0].checked)});else if(this.type==="radio")this.buttonElement.bind("click.button",function(){if(a.disabled)return false;b(this).addClass("ui-state-active");e.buttonElement.attr("aria-pressed",true);var i=e.element[0];g(i).not(i).map(function(){return b(this).button("widget")[0]}).removeClass("ui-state-active").attr("aria-pressed",false)});else{this.buttonElement.bind("mousedown.button",function(){if(a.disabled)return false;b(this).addClass("ui-state-active");\nc=this;b(document).one("mouseup",function(){c=null})}).bind("mouseup.button",function(){if(a.disabled)return false;b(this).removeClass("ui-state-active")}).bind("keydown.button",function(i){if(a.disabled)return false;if(i.keyCode==b.ui.keyCode.SPACE||i.keyCode==b.ui.keyCode.ENTER)b(this).addClass("ui-state-active")}).bind("keyup.button",function(){b(this).removeClass("ui-state-active")});this.buttonElement.is("a")&&this.buttonElement.keyup(function(i){i.keyCode===b.ui.keyCode.SPACE&&b(this).click()})}this._setOption("disabled",\na.disabled)},_determineButtonType:function(){this.type=this.element.is(":checkbox")?"checkbox":this.element.is(":radio")?"radio":this.element.is("input")?"input":"button";if(this.type==="checkbox"||this.type==="radio"){this.buttonElement=this.element.parents().last().find("label[for="+this.element.attr("id")+"]");this.element.addClass("ui-helper-hidden-accessible");var e=this.element.is(":checked");e&&this.buttonElement.addClass("ui-state-active");this.buttonElement.attr("aria-pressed",e)}else this.buttonElement=\nthis.element},widget:function(){return this.buttonElement},destroy:function(){this.element.removeClass("ui-helper-hidden-accessible");this.buttonElement.removeClass("ui-button ui-widget ui-state-default ui-corner-all ui-state-hover ui-state-active  ui-button-icons-only ui-button-icon-only ui-button-text-icons ui-button-text-icon-primary ui-button-text-icon-secondary ui-button-text-only").removeAttr("role").removeAttr("aria-pressed").html(this.buttonElement.find(".ui-button-text").html());this.hasTitle||\nthis.buttonElement.removeAttr("title");b.Widget.prototype.destroy.call(this)},_setOption:function(e,a){b.Widget.prototype._setOption.apply(this,arguments);if(e==="disabled")a?this.element.attr("disabled",true):this.element.removeAttr("disabled");this._resetButton()},refresh:function(){var e=this.element.is(":disabled");e!==this.options.disabled&&this._setOption("disabled",e);if(this.type==="radio")g(this.element[0]).each(function(){b(this).is(":checked")?b(this).button("widget").addClass("ui-state-active").attr("aria-pressed",\ntrue):b(this).button("widget").removeClass("ui-state-active").attr("aria-pressed",false)});else if(this.type==="checkbox")this.element.is(":checked")?this.buttonElement.addClass("ui-state-active").attr("aria-pressed",true):this.buttonElement.removeClass("ui-state-active").attr("aria-pressed",false)},_resetButton:function(){if(this.type==="input")this.options.label&&this.element.val(this.options.label);else{var e=this.buttonElement.removeClass("ui-button-icons-only ui-button-icon-only ui-button-text-icons ui-button-text-icon-primary ui-button-text-icon-secondary ui-button-text-only"),\na=b("<span></span>").addClass("ui-button-text").html(this.options.label).appendTo(e.empty()).text(),d=this.options.icons,h=d.primary&&d.secondary;if(d.primary||d.secondary){e.addClass("ui-button-text-icon"+(h?"s":d.primary?"-primary":"-secondary"));d.primary&&e.prepend("<span class=\'ui-button-icon-primary ui-icon "+d.primary+"\'></span>");d.secondary&&e.append("<span class=\'ui-button-icon-secondary ui-icon "+d.secondary+"\'></span>");if(!this.options.text){e.addClass(h?"ui-button-icons-only":"ui-button-icon-only").removeClass("ui-button-text-icons ui-button-text-icon-primary ui-button-text-icon-secondary");\nthis.hasTitle||e.attr("title",a)}}else e.addClass("ui-button-text-only")}}});b.widget("ui.buttonset",{options:{items:":button, :submit, :reset, :checkbox, :radio, a, :data(button)"},_create:function(){this.element.addClass("ui-buttonset")},_init:function(){this.refresh()},_setOption:function(e,a){e==="disabled"&&this.buttons.button("option",e,a);b.Widget.prototype._setOption.apply(this,arguments)},refresh:function(){this.buttons=this.element.find(this.options.items).filter(":ui-button").button("refresh").end().not(":ui-button").button().end().map(function(){return b(this).button("widget")[0]}).removeClass("ui-corner-all ui-corner-left ui-corner-right").filter(":first").addClass("ui-corner-left").end().filter(":last").addClass("ui-corner-right").end().end()},\ndestroy:function(){this.element.removeClass("ui-buttonset");this.buttons.map(function(){return b(this).button("widget")[0]}).removeClass("ui-corner-left ui-corner-right").end().button("destroy");b.Widget.prototype.destroy.call(this)}})})(jQuery);\n(function(b,c){function f(){this.debug=false;this._curInst=null;this._keyEvent=false;this._disabledInputs=[];this._inDialog=this._datepickerShowing=false;this._mainDivId="ui-datepicker-div";this._inlineClass="ui-datepicker-inline";this._appendClass="ui-datepicker-append";this._triggerClass="ui-datepicker-trigger";this._dialogClass="ui-datepicker-dialog";this._disableClass="ui-datepicker-disabled";this._unselectableClass="ui-datepicker-unselectable";this._currentClass="ui-datepicker-current-day";this._dayOverClass=\n"ui-datepicker-days-cell-over";this.regional=[];this.regional[""]={closeText:"Done",prevText:"Prev",nextText:"Next",currentText:"Today",monthNames:["January","February","March","April","May","June","July","August","September","October","November","December"],monthNamesShort:["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"],dayNames:["Sunday","Monday","Tuesday","Wednesday","Thursday","Friday","Saturday"],dayNamesShort:["Sun","Mon","Tue","Wed","Thu","Fri","Sat"],dayNamesMin:["Su",\n"Mo","Tu","We","Th","Fr","Sa"],weekHeader:"Wk",dateFormat:"mm/dd/yy",firstDay:0,isRTL:false,showMonthAfterYear:false,yearSuffix:""};this._defaults={showOn:"focus",showAnim:"fadeIn",showOptions:{},defaultDate:null,appendText:"",buttonText:"...",buttonImage:"",buttonImageOnly:false,hideIfNoPrevNext:false,navigationAsDateFormat:false,gotoCurrent:false,changeMonth:false,changeYear:false,yearRange:"c-10:c+10",showOtherMonths:false,selectOtherMonths:false,showWeek:false,calculateWeek:this.iso8601Week,shortYearCutoff:"+10",\nminDate:null,maxDate:null,duration:"fast",beforeShowDay:null,beforeShow:null,onSelect:null,onChangeMonthYear:null,onClose:null,numberOfMonths:1,showCurrentAtPos:0,stepMonths:1,stepBigMonths:12,altField:"",altFormat:"",constrainInput:true,showButtonPanel:false,autoSize:false};b.extend(this._defaults,this.regional[""]);this.dpDiv=b(\'<div id="\'+this._mainDivId+\'" class="ui-datepicker ui-widget ui-widget-content ui-helper-clearfix ui-corner-all"></div>\')}function g(a,d){b.extend(a,d);for(var h in d)if(d[h]==\nnull||d[h]==c)a[h]=d[h];return a}b.extend(b.ui,{datepicker:{version:"1.8.9"}});var e=(new Date).getTime();b.extend(f.prototype,{markerClassName:"hasDatepicker",log:function(){this.debug&&console.log.apply("",arguments)},_widgetDatepicker:function(){return this.dpDiv},setDefaults:function(a){g(this._defaults,a||{});return this},_attachDatepicker:function(a,d){var h=null;for(var i in this._defaults){var j=a.getAttribute("date:"+i);if(j){h=h||{};try{h[i]=eval(j)}catch(n){h[i]=j}}}i=a.nodeName.toLowerCase();\nj=i=="div"||i=="span";if(!a.id){this.uuid+=1;a.id="dp"+this.uuid}var q=this._newInst(b(a),j);q.settings=b.extend({},d||{},h||{});if(i=="input")this._connectDatepicker(a,q);else j&&this._inlineDatepicker(a,q)},_newInst:function(a,d){return{id:a[0].id.replace(/([^A-Za-z0-9_-])/g,"\\\\\\\\$1"),input:a,selectedDay:0,selectedMonth:0,selectedYear:0,drawMonth:0,drawYear:0,inline:d,dpDiv:!d?this.dpDiv:b(\'<div class="\'+this._inlineClass+\' ui-datepicker ui-widget ui-widget-content ui-helper-clearfix ui-corner-all"></div>\')}},\n_connectDatepicker:function(a,d){var h=b(a);d.append=b([]);d.trigger=b([]);if(!h.hasClass(this.markerClassName)){this._attachments(h,d);h.addClass(this.markerClassName).keydown(this._doKeyDown).keypress(this._doKeyPress).keyup(this._doKeyUp).bind("setData.datepicker",function(i,j,n){d.settings[j]=n}).bind("getData.datepicker",function(i,j){return this._get(d,j)});this._autoSize(d);b.data(a,"datepicker",d)}},_attachments:function(a,d){var h=this._get(d,"appendText"),i=this._get(d,"isRTL");d.append&&\nd.append.remove();if(h){d.append=b(\'<span class="\'+this._appendClass+\'">\'+h+"</span>");a[i?"before":"after"](d.append)}a.unbind("focus",this._showDatepicker);d.trigger&&d.trigger.remove();h=this._get(d,"showOn");if(h=="focus"||h=="both")a.focus(this._showDatepicker);if(h=="button"||h=="both"){h=this._get(d,"buttonText");var j=this._get(d,"buttonImage");d.trigger=b(this._get(d,"buttonImageOnly")?b("<img/>").addClass(this._triggerClass).attr({src:j,alt:h,title:h}):b(\'<button type="button"></button>\').addClass(this._triggerClass).html(j==\n""?h:b("<img/>").attr({src:j,alt:h,title:h})));a[i?"before":"after"](d.trigger);d.trigger.click(function(){b.datepicker._datepickerShowing&&b.datepicker._lastInput==a[0]?b.datepicker._hideDatepicker():b.datepicker._showDatepicker(a[0]);return false})}},_autoSize:function(a){if(this._get(a,"autoSize")&&!a.inline){var d=new Date(2009,11,20),h=this._get(a,"dateFormat");if(h.match(/[DM]/)){var i=function(j){for(var n=0,q=0,l=0;l<j.length;l++)if(j[l].length>n){n=j[l].length;q=l}return q};d.setMonth(i(this._get(a,\nh.match(/MM/)?"monthNames":"monthNamesShort")));d.setDate(i(this._get(a,h.match(/DD/)?"dayNames":"dayNamesShort"))+20-d.getDay())}a.input.attr("size",this._formatDate(a,d).length)}},_inlineDatepicker:function(a,d){var h=b(a);if(!h.hasClass(this.markerClassName)){h.addClass(this.markerClassName).append(d.dpDiv).bind("setData.datepicker",function(i,j,n){d.settings[j]=n}).bind("getData.datepicker",function(i,j){return this._get(d,j)});b.data(a,"datepicker",d);this._setDate(d,this._getDefaultDate(d),\ntrue);this._updateDatepicker(d);this._updateAlternate(d);d.dpDiv.show()}},_dialogDatepicker:function(a,d,h,i,j){a=this._dialogInst;if(!a){this.uuid+=1;this._dialogInput=b(\'<input type="text" id="\'+("dp"+this.uuid)+\'" style="position: absolute; top: -100px; width: 0px; z-index: -10;"/>\');this._dialogInput.keydown(this._doKeyDown);b("body").append(this._dialogInput);a=this._dialogInst=this._newInst(this._dialogInput,false);a.settings={};b.data(this._dialogInput[0],"datepicker",a)}g(a.settings,i||{});\nd=d&&d.constructor==Date?this._formatDate(a,d):d;this._dialogInput.val(d);this._pos=j?j.length?j:[j.pageX,j.pageY]:null;if(!this._pos)this._pos=[document.documentElement.clientWidth/2-100+(document.documentElement.scrollLeft||document.body.scrollLeft),document.documentElement.clientHeight/2-150+(document.documentElement.scrollTop||document.body.scrollTop)];this._dialogInput.css("left",this._pos[0]+20+"px").css("top",this._pos[1]+"px");a.settings.onSelect=h;this._inDialog=true;this.dpDiv.addClass(this._dialogClass);\nthis._showDatepicker(this._dialogInput[0]);b.blockUI&&b.blockUI(this.dpDiv);b.data(this._dialogInput[0],"datepicker",a);return this},_destroyDatepicker:function(a){var d=b(a),h=b.data(a,"datepicker");if(d.hasClass(this.markerClassName)){var i=a.nodeName.toLowerCase();b.removeData(a,"datepicker");if(i=="input"){h.append.remove();h.trigger.remove();d.removeClass(this.markerClassName).unbind("focus",this._showDatepicker).unbind("keydown",this._doKeyDown).unbind("keypress",this._doKeyPress).unbind("keyup",\nthis._doKeyUp)}else if(i=="div"||i=="span")d.removeClass(this.markerClassName).empty()}},_enableDatepicker:function(a){var d=b(a),h=b.data(a,"datepicker");if(d.hasClass(this.markerClassName)){var i=a.nodeName.toLowerCase();if(i=="input"){a.disabled=false;h.trigger.filter("button").each(function(){this.disabled=false}).end().filter("img").css({opacity:"1.0",cursor:""})}else if(i=="div"||i=="span")d.children("."+this._inlineClass).children().removeClass("ui-state-disabled");this._disabledInputs=b.map(this._disabledInputs,\nfunction(j){return j==a?null:j})}},_disableDatepicker:function(a){var d=b(a),h=b.data(a,"datepicker");if(d.hasClass(this.markerClassName)){var i=a.nodeName.toLowerCase();if(i=="input"){a.disabled=true;h.trigger.filter("button").each(function(){this.disabled=true}).end().filter("img").css({opacity:"0.5",cursor:"default"})}else if(i=="div"||i=="span")d.children("."+this._inlineClass).children().addClass("ui-state-disabled");this._disabledInputs=b.map(this._disabledInputs,function(j){return j==a?null:\nj});this._disabledInputs[this._disabledInputs.length]=a}},_isDisabledDatepicker:function(a){if(!a)return false;for(var d=0;d<this._disabledInputs.length;d++)if(this._disabledInputs[d]==a)return true;return false},_getInst:function(a){try{return b.data(a,"datepicker")}catch(d){throw"Missing instance data for this datepicker";}},_optionDatepicker:function(a,d,h){var i=this._getInst(a);if(arguments.length==2&&typeof d=="string")return d=="defaults"?b.extend({},b.datepicker._defaults):i?d=="all"?b.extend({},\ni.settings):this._get(i,d):null;var j=d||{};if(typeof d=="string"){j={};j[d]=h}if(i){this._curInst==i&&this._hideDatepicker();var n=this._getDateDatepicker(a,true);g(i.settings,j);this._attachments(b(a),i);this._autoSize(i);this._setDateDatepicker(a,n);this._updateDatepicker(i)}},_changeDatepicker:function(a,d,h){this._optionDatepicker(a,d,h)},_refreshDatepicker:function(a){(a=this._getInst(a))&&this._updateDatepicker(a)},_setDateDatepicker:function(a,d){if(a=this._getInst(a)){this._setDate(a,d);\nthis._updateDatepicker(a);this._updateAlternate(a)}},_getDateDatepicker:function(a,d){(a=this._getInst(a))&&!a.inline&&this._setDateFromField(a,d);return a?this._getDate(a):null},_doKeyDown:function(a){var d=b.datepicker._getInst(a.target),h=true,i=d.dpDiv.is(".ui-datepicker-rtl");d._keyEvent=true;if(b.datepicker._datepickerShowing)switch(a.keyCode){case 9:b.datepicker._hideDatepicker();h=false;break;case 13:h=b("td."+b.datepicker._dayOverClass+":not(."+b.datepicker._currentClass+")",d.dpDiv);h[0]?\nb.datepicker._selectDay(a.target,d.selectedMonth,d.selectedYear,h[0]):b.datepicker._hideDatepicker();return false;case 27:b.datepicker._hideDatepicker();break;case 33:b.datepicker._adjustDate(a.target,a.ctrlKey?-b.datepicker._get(d,"stepBigMonths"):-b.datepicker._get(d,"stepMonths"),"M");break;case 34:b.datepicker._adjustDate(a.target,a.ctrlKey?+b.datepicker._get(d,"stepBigMonths"):+b.datepicker._get(d,"stepMonths"),"M");break;case 35:if(a.ctrlKey||a.metaKey)b.datepicker._clearDate(a.target);h=a.ctrlKey||\na.metaKey;break;case 36:if(a.ctrlKey||a.metaKey)b.datepicker._gotoToday(a.target);h=a.ctrlKey||a.metaKey;break;case 37:if(a.ctrlKey||a.metaKey)b.datepicker._adjustDate(a.target,i?+1:-1,"D");h=a.ctrlKey||a.metaKey;if(a.originalEvent.altKey)b.datepicker._adjustDate(a.target,a.ctrlKey?-b.datepicker._get(d,"stepBigMonths"):-b.datepicker._get(d,"stepMonths"),"M");break;case 38:if(a.ctrlKey||a.metaKey)b.datepicker._adjustDate(a.target,-7,"D");h=a.ctrlKey||a.metaKey;break;case 39:if(a.ctrlKey||a.metaKey)b.datepicker._adjustDate(a.target,\ni?-1:+1,"D");h=a.ctrlKey||a.metaKey;if(a.originalEvent.altKey)b.datepicker._adjustDate(a.target,a.ctrlKey?+b.datepicker._get(d,"stepBigMonths"):+b.datepicker._get(d,"stepMonths"),"M");break;case 40:if(a.ctrlKey||a.metaKey)b.datepicker._adjustDate(a.target,+7,"D");h=a.ctrlKey||a.metaKey;break;default:h=false}else if(a.keyCode==36&&a.ctrlKey)b.datepicker._showDatepicker(this);else h=false;if(h){a.preventDefault();a.stopPropagation()}},_doKeyPress:function(a){var d=b.datepicker._getInst(a.target);if(b.datepicker._get(d,\n"constrainInput")){d=b.datepicker._possibleChars(b.datepicker._get(d,"dateFormat"));var h=String.fromCharCode(a.charCode==c?a.keyCode:a.charCode);return a.ctrlKey||a.metaKey||h<" "||!d||d.indexOf(h)>-1}},_doKeyUp:function(a){a=b.datepicker._getInst(a.target);if(a.input.val()!=a.lastVal)try{if(b.datepicker.parseDate(b.datepicker._get(a,"dateFormat"),a.input?a.input.val():null,b.datepicker._getFormatConfig(a))){b.datepicker._setDateFromField(a);b.datepicker._updateAlternate(a);b.datepicker._updateDatepicker(a)}}catch(d){b.datepicker.log(d)}return true},\n_showDatepicker:function(a){a=a.target||a;if(a.nodeName.toLowerCase()!="input")a=b("input",a.parentNode)[0];if(!(b.datepicker._isDisabledDatepicker(a)||b.datepicker._lastInput==a)){var d=b.datepicker._getInst(a);b.datepicker._curInst&&b.datepicker._curInst!=d&&b.datepicker._curInst.dpDiv.stop(true,true);var h=b.datepicker._get(d,"beforeShow");g(d.settings,h?h.apply(a,[a,d]):{});d.lastVal=null;b.datepicker._lastInput=a;b.datepicker._setDateFromField(d);if(b.datepicker._inDialog)a.value="";if(!b.datepicker._pos){b.datepicker._pos=\nb.datepicker._findPos(a);b.datepicker._pos[1]+=a.offsetHeight}var i=false;b(a).parents().each(function(){i|=b(this).css("position")=="fixed";return!i});if(i&&b.browser.opera){b.datepicker._pos[0]-=document.documentElement.scrollLeft;b.datepicker._pos[1]-=document.documentElement.scrollTop}h={left:b.datepicker._pos[0],top:b.datepicker._pos[1]};b.datepicker._pos=null;d.dpDiv.empty();d.dpDiv.css({position:"absolute",display:"block",top:"-1000px"});b.datepicker._updateDatepicker(d);h=b.datepicker._checkOffset(d,\nh,i);d.dpDiv.css({position:b.datepicker._inDialog&&b.blockUI?"static":i?"fixed":"absolute",display:"none",left:h.left+"px",top:h.top+"px"});if(!d.inline){h=b.datepicker._get(d,"showAnim");var j=b.datepicker._get(d,"duration"),n=function(){b.datepicker._datepickerShowing=true;var q=d.dpDiv.find("iframe.ui-datepicker-cover");if(q.length){var l=b.datepicker._getBorders(d.dpDiv);q.css({left:-l[0],top:-l[1],width:d.dpDiv.outerWidth(),height:d.dpDiv.outerHeight()})}};d.dpDiv.zIndex(b(a).zIndex()+1);b.effects&&\nb.effects[h]?d.dpDiv.show(h,b.datepicker._get(d,"showOptions"),j,n):d.dpDiv[h||"show"](h?j:null,n);if(!h||!j)n();d.input.is(":visible")&&!d.input.is(":disabled")&&d.input.focus();b.datepicker._curInst=d}}},_updateDatepicker:function(a){var d=this,h=b.datepicker._getBorders(a.dpDiv);a.dpDiv.empty().append(this._generateHTML(a));var i=a.dpDiv.find("iframe.ui-datepicker-cover");i.length&&i.css({left:-h[0],top:-h[1],width:a.dpDiv.outerWidth(),height:a.dpDiv.outerHeight()});a.dpDiv.find("button, .ui-datepicker-prev, .ui-datepicker-next, .ui-datepicker-calendar td a").bind("mouseout",\nfunction(){b(this).removeClass("ui-state-hover");this.className.indexOf("ui-datepicker-prev")!=-1&&b(this).removeClass("ui-datepicker-prev-hover");this.className.indexOf("ui-datepicker-next")!=-1&&b(this).removeClass("ui-datepicker-next-hover")}).bind("mouseover",function(){if(!d._isDisabledDatepicker(a.inline?a.dpDiv.parent()[0]:a.input[0])){b(this).parents(".ui-datepicker-calendar").find("a").removeClass("ui-state-hover");b(this).addClass("ui-state-hover");this.className.indexOf("ui-datepicker-prev")!=\n-1&&b(this).addClass("ui-datepicker-prev-hover");this.className.indexOf("ui-datepicker-next")!=-1&&b(this).addClass("ui-datepicker-next-hover")}}).end().find("."+this._dayOverClass+" a").trigger("mouseover").end();h=this._getNumberOfMonths(a);i=h[1];i>1?a.dpDiv.addClass("ui-datepicker-multi-"+i).css("width",17*i+"em"):a.dpDiv.removeClass("ui-datepicker-multi-2 ui-datepicker-multi-3 ui-datepicker-multi-4").width("");a.dpDiv[(h[0]!=1||h[1]!=1?"add":"remove")+"Class"]("ui-datepicker-multi");a.dpDiv[(this._get(a,\n"isRTL")?"add":"remove")+"Class"]("ui-datepicker-rtl");a==b.datepicker._curInst&&b.datepicker._datepickerShowing&&a.input&&a.input.is(":visible")&&!a.input.is(":disabled")&&a.input.focus();if(a.yearshtml){var j=a.yearshtml;setTimeout(function(){j===a.yearshtml&&a.dpDiv.find("select.ui-datepicker-year:first").replaceWith(a.yearshtml);j=a.yearshtml=null},0)}},_getBorders:function(a){var d=function(h){return{thin:1,medium:2,thick:3}[h]||h};return[parseFloat(d(a.css("border-left-width"))),parseFloat(d(a.css("border-top-width")))]},\n_checkOffset:function(a,d,h){var i=a.dpDiv.outerWidth(),j=a.dpDiv.outerHeight(),n=a.input?a.input.outerWidth():0,q=a.input?a.input.outerHeight():0,l=document.documentElement.clientWidth+b(document).scrollLeft(),k=document.documentElement.clientHeight+b(document).scrollTop();d.left-=this._get(a,"isRTL")?i-n:0;d.left-=h&&d.left==a.input.offset().left?b(document).scrollLeft():0;d.top-=h&&d.top==a.input.offset().top+q?b(document).scrollTop():0;d.left-=Math.min(d.left,d.left+i>l&&l>i?Math.abs(d.left+i-\nl):0);d.top-=Math.min(d.top,d.top+j>k&&k>j?Math.abs(j+q):0);return d},_findPos:function(a){for(var d=this._get(this._getInst(a),"isRTL");a&&(a.type=="hidden"||a.nodeType!=1);)a=a[d?"previousSibling":"nextSibling"];a=b(a).offset();return[a.left,a.top]},_hideDatepicker:function(a){var d=this._curInst;if(!(!d||a&&d!=b.data(a,"datepicker")))if(this._datepickerShowing){a=this._get(d,"showAnim");var h=this._get(d,"duration"),i=function(){b.datepicker._tidyDialog(d);this._curInst=null};b.effects&&b.effects[a]?\nd.dpDiv.hide(a,b.datepicker._get(d,"showOptions"),h,i):d.dpDiv[a=="slideDown"?"slideUp":a=="fadeIn"?"fadeOut":"hide"](a?h:null,i);a||i();if(a=this._get(d,"onClose"))a.apply(d.input?d.input[0]:null,[d.input?d.input.val():"",d]);this._datepickerShowing=false;this._lastInput=null;if(this._inDialog){this._dialogInput.css({position:"absolute",left:"0",top:"-100px"});if(b.blockUI){b.unblockUI();b("body").append(this.dpDiv)}}this._inDialog=false}},_tidyDialog:function(a){a.dpDiv.removeClass(this._dialogClass).unbind(".ui-datepicker-calendar")},\n_checkExternalClick:function(a){if(b.datepicker._curInst){a=b(a.target);a[0].id!=b.datepicker._mainDivId&&a.parents("#"+b.datepicker._mainDivId).length==0&&!a.hasClass(b.datepicker.markerClassName)&&!a.hasClass(b.datepicker._triggerClass)&&b.datepicker._datepickerShowing&&!(b.datepicker._inDialog&&b.blockUI)&&b.datepicker._hideDatepicker()}},_adjustDate:function(a,d,h){a=b(a);var i=this._getInst(a[0]);if(!this._isDisabledDatepicker(a[0])){this._adjustInstDate(i,d+(h=="M"?this._get(i,"showCurrentAtPos"):\n0),h);this._updateDatepicker(i)}},_gotoToday:function(a){a=b(a);var d=this._getInst(a[0]);if(this._get(d,"gotoCurrent")&&d.currentDay){d.selectedDay=d.currentDay;d.drawMonth=d.selectedMonth=d.currentMonth;d.drawYear=d.selectedYear=d.currentYear}else{var h=new Date;d.selectedDay=h.getDate();d.drawMonth=d.selectedMonth=h.getMonth();d.drawYear=d.selectedYear=h.getFullYear()}this._notifyChange(d);this._adjustDate(a)},_selectMonthYear:function(a,d,h){a=b(a);var i=this._getInst(a[0]);i._selectingMonthYear=\nfalse;i["selected"+(h=="M"?"Month":"Year")]=i["draw"+(h=="M"?"Month":"Year")]=parseInt(d.options[d.selectedIndex].value,10);this._notifyChange(i);this._adjustDate(a)},_clickMonthYear:function(a){var d=this._getInst(b(a)[0]);d.input&&d._selectingMonthYear&&setTimeout(function(){d.input.focus()},0);d._selectingMonthYear=!d._selectingMonthYear},_selectDay:function(a,d,h,i){var j=b(a);if(!(b(i).hasClass(this._unselectableClass)||this._isDisabledDatepicker(j[0]))){j=this._getInst(j[0]);j.selectedDay=j.currentDay=\nb("a",i).html();j.selectedMonth=j.currentMonth=d;j.selectedYear=j.currentYear=h;this._selectDate(a,this._formatDate(j,j.currentDay,j.currentMonth,j.currentYear))}},_clearDate:function(a){a=b(a);this._getInst(a[0]);this._selectDate(a,"")},_selectDate:function(a,d){a=this._getInst(b(a)[0]);d=d!=null?d:this._formatDate(a);a.input&&a.input.val(d);this._updateAlternate(a);var h=this._get(a,"onSelect");if(h)h.apply(a.input?a.input[0]:null,[d,a]);else a.input&&a.input.trigger("change");if(a.inline)this._updateDatepicker(a);\nelse{this._hideDatepicker();this._lastInput=a.input[0];typeof a.input[0]!="object"&&a.input.focus();this._lastInput=null}},_updateAlternate:function(a){var d=this._get(a,"altField");if(d){var h=this._get(a,"altFormat")||this._get(a,"dateFormat"),i=this._getDate(a),j=this.formatDate(h,i,this._getFormatConfig(a));b(d).each(function(){b(this).val(j)})}},noWeekends:function(a){a=a.getDay();return[a>0&&a<6,""]},iso8601Week:function(a){a=new Date(a.getTime());a.setDate(a.getDate()+4-(a.getDay()||7));var d=\na.getTime();a.setMonth(0);a.setDate(1);return Math.floor(Math.round((d-a)/864E5)/7)+1},parseDate:function(a,d,h){if(a==null||d==null)throw"Invalid arguments";d=typeof d=="object"?d.toString():d+"";if(d=="")return null;var i=(h?h.shortYearCutoff:null)||this._defaults.shortYearCutoff;i=typeof i!="string"?i:(new Date).getFullYear()%100+parseInt(i,10);for(var j=(h?h.dayNamesShort:null)||this._defaults.dayNamesShort,n=(h?h.dayNames:null)||this._defaults.dayNames,q=(h?h.monthNamesShort:null)||this._defaults.monthNamesShort,\nl=(h?h.monthNames:null)||this._defaults.monthNames,k=h=-1,m=-1,o=-1,p=false,s=function(x){(x=y+1<a.length&&a.charAt(y+1)==x)&&y++;return x},r=function(x){var C=s(x);x=new RegExp("^\\\\d{1,"+(x=="@"?14:x=="!"?20:x=="y"&&C?4:x=="o"?3:2)+"}");x=d.substring(w).match(x);if(!x)throw"Missing number at position "+w;w+=x[0].length;return parseInt(x[0],10)},u=function(x,C,J){x=s(x)?J:C;for(C=0;C<x.length;C++)if(d.substr(w,x[C].length).toLowerCase()==x[C].toLowerCase()){w+=x[C].length;return C+1}throw"Unknown name at position "+\nw;},v=function(){if(d.charAt(w)!=a.charAt(y))throw"Unexpected literal at position "+w;w++},w=0,y=0;y<a.length;y++)if(p)if(a.charAt(y)=="\'"&&!s("\'"))p=false;else v();else switch(a.charAt(y)){case "d":m=r("d");break;case "D":u("D",j,n);break;case "o":o=r("o");break;case "m":k=r("m");break;case "M":k=u("M",q,l);break;case "y":h=r("y");break;case "@":var B=new Date(r("@"));h=B.getFullYear();k=B.getMonth()+1;m=B.getDate();break;case "!":B=new Date((r("!")-this._ticksTo1970)/1E4);h=B.getFullYear();k=B.getMonth()+\n1;m=B.getDate();break;case "\'":if(s("\'"))v();else p=true;break;default:v()}if(h==-1)h=(new Date).getFullYear();else if(h<100)h+=(new Date).getFullYear()-(new Date).getFullYear()%100+(h<=i?0:-100);if(o>-1){k=1;m=o;do{i=this._getDaysInMonth(h,k-1);if(m<=i)break;k++;m-=i}while(1)}B=this._daylightSavingAdjust(new Date(h,k-1,m));if(B.getFullYear()!=h||B.getMonth()+1!=k||B.getDate()!=m)throw"Invalid date";return B},ATOM:"yy-mm-dd",COOKIE:"D, dd M yy",ISO_8601:"yy-mm-dd",RFC_822:"D, d M y",RFC_850:"DD, dd-M-y",\nRFC_1036:"D, d M y",RFC_1123:"D, d M yy",RFC_2822:"D, d M yy",RSS:"D, d M y",TICKS:"!",TIMESTAMP:"@",W3C:"yy-mm-dd",_ticksTo1970:(718685+Math.floor(492.5)-Math.floor(19.7)+Math.floor(4.925))*24*60*60*1E7,formatDate:function(a,d,h){if(!d)return"";var i=(h?h.dayNamesShort:null)||this._defaults.dayNamesShort,j=(h?h.dayNames:null)||this._defaults.dayNames,n=(h?h.monthNamesShort:null)||this._defaults.monthNamesShort;h=(h?h.monthNames:null)||this._defaults.monthNames;var q=function(s){(s=p+1<a.length&&\na.charAt(p+1)==s)&&p++;return s},l=function(s,r,u){r=""+r;if(q(s))for(;r.length<u;)r="0"+r;return r},k=function(s,r,u,v){return q(s)?v[r]:u[r]},m="",o=false;if(d)for(var p=0;p<a.length;p++)if(o)if(a.charAt(p)=="\'"&&!q("\'"))o=false;else m+=a.charAt(p);else switch(a.charAt(p)){case "d":m+=l("d",d.getDate(),2);break;case "D":m+=k("D",d.getDay(),i,j);break;case "o":m+=l("o",(d.getTime()-(new Date(d.getFullYear(),0,0)).getTime())/864E5,3);break;case "m":m+=l("m",d.getMonth()+1,2);break;case "M":m+=k("M",\nd.getMonth(),n,h);break;case "y":m+=q("y")?d.getFullYear():(d.getYear()%100<10?"0":"")+d.getYear()%100;break;case "@":m+=d.getTime();break;case "!":m+=d.getTime()*1E4+this._ticksTo1970;break;case "\'":if(q("\'"))m+="\'";else o=true;break;default:m+=a.charAt(p)}return m},_possibleChars:function(a){for(var d="",h=false,i=function(n){(n=j+1<a.length&&a.charAt(j+1)==n)&&j++;return n},j=0;j<a.length;j++)if(h)if(a.charAt(j)=="\'"&&!i("\'"))h=false;else d+=a.charAt(j);else switch(a.charAt(j)){case "d":case "m":case "y":case "@":d+=\n"0123456789";break;case "D":case "M":return null;case "\'":if(i("\'"))d+="\'";else h=true;break;default:d+=a.charAt(j)}return d},_get:function(a,d){return a.settings[d]!==c?a.settings[d]:this._defaults[d]},_setDateFromField:function(a,d){if(a.input.val()!=a.lastVal){var h=this._get(a,"dateFormat"),i=a.lastVal=a.input?a.input.val():null,j,n;j=n=this._getDefaultDate(a);var q=this._getFormatConfig(a);try{j=this.parseDate(h,i,q)||n}catch(l){this.log(l);i=d?"":i}a.selectedDay=j.getDate();a.drawMonth=a.selectedMonth=\nj.getMonth();a.drawYear=a.selectedYear=j.getFullYear();a.currentDay=i?j.getDate():0;a.currentMonth=i?j.getMonth():0;a.currentYear=i?j.getFullYear():0;this._adjustInstDate(a)}},_getDefaultDate:function(a){return this._restrictMinMax(a,this._determineDate(a,this._get(a,"defaultDate"),new Date))},_determineDate:function(a,d,h){var i=function(n){var q=new Date;q.setDate(q.getDate()+n);return q},j=function(n){try{return b.datepicker.parseDate(b.datepicker._get(a,"dateFormat"),n,b.datepicker._getFormatConfig(a))}catch(q){}var l=\n(n.toLowerCase().match(/^c/)?b.datepicker._getDate(a):null)||new Date,k=l.getFullYear(),m=l.getMonth();l=l.getDate();for(var o=/([+-]?[0-9]+)\\s*(d|D|w|W|m|M|y|Y)?/g,p=o.exec(n);p;){switch(p[2]||"d"){case "d":case "D":l+=parseInt(p[1],10);break;case "w":case "W":l+=parseInt(p[1],10)*7;break;case "m":case "M":m+=parseInt(p[1],10);l=Math.min(l,b.datepicker._getDaysInMonth(k,m));break;case "y":case "Y":k+=parseInt(p[1],10);l=Math.min(l,b.datepicker._getDaysInMonth(k,m));break}p=o.exec(n)}return new Date(k,\nm,l)};if(d=(d=d==null||d===""?h:typeof d=="string"?j(d):typeof d=="number"?isNaN(d)?h:i(d):new Date(d.getTime()))&&d.toString()=="Invalid Date"?h:d){d.setHours(0);d.setMinutes(0);d.setSeconds(0);d.setMilliseconds(0)}return this._daylightSavingAdjust(d)},_daylightSavingAdjust:function(a){if(!a)return null;a.setHours(a.getHours()>12?a.getHours()+2:0);return a},_setDate:function(a,d,h){var i=!d,j=a.selectedMonth,n=a.selectedYear;d=this._restrictMinMax(a,this._determineDate(a,d,new Date));a.selectedDay=\na.currentDay=d.getDate();a.drawMonth=a.selectedMonth=a.currentMonth=d.getMonth();a.drawYear=a.selectedYear=a.currentYear=d.getFullYear();if((j!=a.selectedMonth||n!=a.selectedYear)&&!h)this._notifyChange(a);this._adjustInstDate(a);if(a.input)a.input.val(i?"":this._formatDate(a))},_getDate:function(a){return!a.currentYear||a.input&&a.input.val()==""?null:this._daylightSavingAdjust(new Date(a.currentYear,a.currentMonth,a.currentDay))},_generateHTML:function(a){var d=new Date;d=this._daylightSavingAdjust(new Date(d.getFullYear(),\nd.getMonth(),d.getDate()));var h=this._get(a,"isRTL"),i=this._get(a,"showButtonPanel"),j=this._get(a,"hideIfNoPrevNext"),n=this._get(a,"navigationAsDateFormat"),q=this._getNumberOfMonths(a),l=this._get(a,"showCurrentAtPos"),k=this._get(a,"stepMonths"),m=q[0]!=1||q[1]!=1,o=this._daylightSavingAdjust(!a.currentDay?new Date(9999,9,9):new Date(a.currentYear,a.currentMonth,a.currentDay)),p=this._getMinMaxDate(a,"min"),s=this._getMinMaxDate(a,"max");l=a.drawMonth-l;var r=a.drawYear;if(l<0){l+=12;r--}if(s){var u=\nthis._daylightSavingAdjust(new Date(s.getFullYear(),s.getMonth()-q[0]*q[1]+1,s.getDate()));for(u=p&&u<p?p:u;this._daylightSavingAdjust(new Date(r,l,1))>u;){l--;if(l<0){l=11;r--}}}a.drawMonth=l;a.drawYear=r;u=this._get(a,"prevText");u=!n?u:this.formatDate(u,this._daylightSavingAdjust(new Date(r,l-k,1)),this._getFormatConfig(a));u=this._canAdjustMonth(a,-1,r,l)?\'<a class="ui-datepicker-prev ui-corner-all" onclick="DP_jQuery_\'+e+".datepicker._adjustDate(\'#"+a.id+"\', -"+k+", \'M\');\\" title=\\""+u+\'"><span class="ui-icon ui-icon-circle-triangle-\'+\n(h?"e":"w")+\'">\'+u+"</span></a>":j?"":\'<a class="ui-datepicker-prev ui-corner-all ui-state-disabled" title="\'+u+\'"><span class="ui-icon ui-icon-circle-triangle-\'+(h?"e":"w")+\'">\'+u+"</span></a>";var v=this._get(a,"nextText");v=!n?v:this.formatDate(v,this._daylightSavingAdjust(new Date(r,l+k,1)),this._getFormatConfig(a));j=this._canAdjustMonth(a,+1,r,l)?\'<a class="ui-datepicker-next ui-corner-all" onclick="DP_jQuery_\'+e+".datepicker._adjustDate(\'#"+a.id+"\', +"+k+", \'M\');\\" title=\\""+v+\'"><span class="ui-icon ui-icon-circle-triangle-\'+\n(h?"w":"e")+\'">\'+v+"</span></a>":j?"":\'<a class="ui-datepicker-next ui-corner-all ui-state-disabled" title="\'+v+\'"><span class="ui-icon ui-icon-circle-triangle-\'+(h?"w":"e")+\'">\'+v+"</span></a>";k=this._get(a,"currentText");v=this._get(a,"gotoCurrent")&&a.currentDay?o:d;k=!n?k:this.formatDate(k,v,this._getFormatConfig(a));n=!a.inline?\'<button type="button" class="ui-datepicker-close ui-state-default ui-priority-primary ui-corner-all" onclick="DP_jQuery_\'+e+\'.datepicker._hideDatepicker();">\'+this._get(a,\n"closeText")+"</button>":"";i=i?\'<div class="ui-datepicker-buttonpane ui-widget-content">\'+(h?n:"")+(this._isInRange(a,v)?\'<button type="button" class="ui-datepicker-current ui-state-default ui-priority-secondary ui-corner-all" onclick="DP_jQuery_\'+e+".datepicker._gotoToday(\'#"+a.id+"\');\\">"+k+"</button>":"")+(h?"":n)+"</div>":"";n=parseInt(this._get(a,"firstDay"),10);n=isNaN(n)?0:n;k=this._get(a,"showWeek");v=this._get(a,"dayNames");this._get(a,"dayNamesShort");var w=this._get(a,"dayNamesMin"),y=\nthis._get(a,"monthNames"),B=this._get(a,"monthNamesShort"),x=this._get(a,"beforeShowDay"),C=this._get(a,"showOtherMonths"),J=this._get(a,"selectOtherMonths");this._get(a,"calculateWeek");for(var M=this._getDefaultDate(a),K="",G=0;G<q[0];G++){for(var N="",H=0;H<q[1];H++){var O=this._daylightSavingAdjust(new Date(r,l,a.selectedDay)),A=" ui-corner-all",D="";if(m){D+=\'<div class="ui-datepicker-group\';if(q[1]>1)switch(H){case 0:D+=" ui-datepicker-group-first";A=" ui-corner-"+(h?"right":"left");break;case q[1]-\n1:D+=" ui-datepicker-group-last";A=" ui-corner-"+(h?"left":"right");break;default:D+=" ui-datepicker-group-middle";A="";break}D+=\'">\'}D+=\'<div class="ui-datepicker-header ui-widget-header ui-helper-clearfix\'+A+\'">\'+(/all|left/.test(A)&&G==0?h?j:u:"")+(/all|right/.test(A)&&G==0?h?u:j:"")+this._generateMonthYearHeader(a,l,r,p,s,G>0||H>0,y,B)+\'</div><table class="ui-datepicker-calendar"><thead><tr>\';var E=k?\'<th class="ui-datepicker-week-col">\'+this._get(a,"weekHeader")+"</th>":"";for(A=0;A<7;A++){var z=\n(A+n)%7;E+="<th"+((A+n+6)%7>=5?\' class="ui-datepicker-week-end"\':"")+\'><span title="\'+v[z]+\'">\'+w[z]+"</span></th>"}D+=E+"</tr></thead><tbody>";E=this._getDaysInMonth(r,l);if(r==a.selectedYear&&l==a.selectedMonth)a.selectedDay=Math.min(a.selectedDay,E);A=(this._getFirstDayOfMonth(r,l)-n+7)%7;E=m?6:Math.ceil((A+E)/7);z=this._daylightSavingAdjust(new Date(r,l,1-A));for(var P=0;P<E;P++){D+="<tr>";var Q=!k?"":\'<td class="ui-datepicker-week-col">\'+this._get(a,"calculateWeek")(z)+"</td>";for(A=0;A<7;A++){var I=\nx?x.apply(a.input?a.input[0]:null,[z]):[true,""],F=z.getMonth()!=l,L=F&&!J||!I[0]||p&&z<p||s&&z>s;Q+=\'<td class="\'+((A+n+6)%7>=5?" ui-datepicker-week-end":"")+(F?" ui-datepicker-other-month":"")+(z.getTime()==O.getTime()&&l==a.selectedMonth&&a._keyEvent||M.getTime()==z.getTime()&&M.getTime()==O.getTime()?" "+this._dayOverClass:"")+(L?" "+this._unselectableClass+" ui-state-disabled":"")+(F&&!C?"":" "+I[1]+(z.getTime()==o.getTime()?" "+this._currentClass:"")+(z.getTime()==d.getTime()?" ui-datepicker-today":\n""))+\'"\'+((!F||C)&&I[2]?\' title="\'+I[2]+\'"\':"")+(L?"":\' onclick="DP_jQuery_\'+e+".datepicker._selectDay(\'#"+a.id+"\',"+z.getMonth()+","+z.getFullYear()+\', this);return false;"\')+">"+(F&&!C?"&#xa0;":L?\'<span class="ui-state-default">\'+z.getDate()+"</span>":\'<a class="ui-state-default\'+(z.getTime()==d.getTime()?" ui-state-highlight":"")+(z.getTime()==o.getTime()?" ui-state-active":"")+(F?" ui-priority-secondary":"")+\'" href="#">\'+z.getDate()+"</a>")+"</td>";z.setDate(z.getDate()+1);z=this._daylightSavingAdjust(z)}D+=\nQ+"</tr>"}l++;if(l>11){l=0;r++}D+="</tbody></table>"+(m?"</div>"+(q[0]>0&&H==q[1]-1?\'<div class="ui-datepicker-row-break"></div>\':""):"");N+=D}K+=N}K+=i+(b.browser.msie&&parseInt(b.browser.version,10)<7&&!a.inline?\'<iframe src="javascript:false;" class="ui-datepicker-cover" frameborder="0"></iframe>\':"");a._keyEvent=false;return K},_generateMonthYearHeader:function(a,d,h,i,j,n,q,l){var k=this._get(a,"changeMonth"),m=this._get(a,"changeYear"),o=this._get(a,"showMonthAfterYear"),p=\'<div class="ui-datepicker-title">\',\ns="";if(n||!k)s+=\'<span class="ui-datepicker-month">\'+q[d]+"</span>";else{q=i&&i.getFullYear()==h;var r=j&&j.getFullYear()==h;s+=\'<select class="ui-datepicker-month" onchange="DP_jQuery_\'+e+".datepicker._selectMonthYear(\'#"+a.id+"\', this, \'M\');\\" onclick=\\"DP_jQuery_"+e+".datepicker._clickMonthYear(\'#"+a.id+"\');\\">";for(var u=0;u<12;u++)if((!q||u>=i.getMonth())&&(!r||u<=j.getMonth()))s+=\'<option value="\'+u+\'"\'+(u==d?\' selected="selected"\':"")+">"+l[u]+"</option>";s+="</select>"}o||(p+=s+(n||!(k&&\nm)?"&#xa0;":""));a.yearshtml="";if(n||!m)p+=\'<span class="ui-datepicker-year">\'+h+"</span>";else{l=this._get(a,"yearRange").split(":");var v=(new Date).getFullYear();q=function(w){w=w.match(/c[+-].*/)?h+parseInt(w.substring(1),10):w.match(/[+-].*/)?v+parseInt(w,10):parseInt(w,10);return isNaN(w)?v:w};d=q(l[0]);l=Math.max(d,q(l[1]||""));d=i?Math.max(d,i.getFullYear()):d;l=j?Math.min(l,j.getFullYear()):l;for(a.yearshtml+=\'<select class="ui-datepicker-year" onchange="DP_jQuery_\'+e+".datepicker._selectMonthYear(\'#"+\na.id+"\', this, \'Y\');\\" onclick=\\"DP_jQuery_"+e+".datepicker._clickMonthYear(\'#"+a.id+"\');\\">";d<=l;d++)a.yearshtml+=\'<option value="\'+d+\'"\'+(d==h?\' selected="selected"\':"")+">"+d+"</option>";a.yearshtml+="</select>";if(b.browser.mozilla)p+=\'<select class="ui-datepicker-year"><option value="\'+h+\'" selected="selected">\'+h+"</option></select>";else{p+=a.yearshtml;a.yearshtml=null}}p+=this._get(a,"yearSuffix");if(o)p+=(n||!(k&&m)?"&#xa0;":"")+s;p+="</div>";return p},_adjustInstDate:function(a,d,h){var i=\na.drawYear+(h=="Y"?d:0),j=a.drawMonth+(h=="M"?d:0);d=Math.min(a.selectedDay,this._getDaysInMonth(i,j))+(h=="D"?d:0);i=this._restrictMinMax(a,this._daylightSavingAdjust(new Date(i,j,d)));a.selectedDay=i.getDate();a.drawMonth=a.selectedMonth=i.getMonth();a.drawYear=a.selectedYear=i.getFullYear();if(h=="M"||h=="Y")this._notifyChange(a)},_restrictMinMax:function(a,d){var h=this._getMinMaxDate(a,"min");a=this._getMinMaxDate(a,"max");d=h&&d<h?h:d;return d=a&&d>a?a:d},_notifyChange:function(a){var d=this._get(a,\n"onChangeMonthYear");if(d)d.apply(a.input?a.input[0]:null,[a.selectedYear,a.selectedMonth+1,a])},_getNumberOfMonths:function(a){a=this._get(a,"numberOfMonths");return a==null?[1,1]:typeof a=="number"?[1,a]:a},_getMinMaxDate:function(a,d){return this._determineDate(a,this._get(a,d+"Date"),null)},_getDaysInMonth:function(a,d){return 32-(new Date(a,d,32)).getDate()},_getFirstDayOfMonth:function(a,d){return(new Date(a,d,1)).getDay()},_canAdjustMonth:function(a,d,h,i){var j=this._getNumberOfMonths(a);\nh=this._daylightSavingAdjust(new Date(h,i+(d<0?d:j[0]*j[1]),1));d<0&&h.setDate(this._getDaysInMonth(h.getFullYear(),h.getMonth()));return this._isInRange(a,h)},_isInRange:function(a,d){var h=this._getMinMaxDate(a,"min");a=this._getMinMaxDate(a,"max");return(!h||d.getTime()>=h.getTime())&&(!a||d.getTime()<=a.getTime())},_getFormatConfig:function(a){var d=this._get(a,"shortYearCutoff");d=typeof d!="string"?d:(new Date).getFullYear()%100+parseInt(d,10);return{shortYearCutoff:d,dayNamesShort:this._get(a,\n"dayNamesShort"),dayNames:this._get(a,"dayNames"),monthNamesShort:this._get(a,"monthNamesShort"),monthNames:this._get(a,"monthNames")}},_formatDate:function(a,d,h,i){if(!d){a.currentDay=a.selectedDay;a.currentMonth=a.selectedMonth;a.currentYear=a.selectedYear}d=d?typeof d=="object"?d:this._daylightSavingAdjust(new Date(i,h,d)):this._daylightSavingAdjust(new Date(a.currentYear,a.currentMonth,a.currentDay));return this.formatDate(this._get(a,"dateFormat"),d,this._getFormatConfig(a))}});b.fn.datepicker=\nfunction(a){if(!b.datepicker.initialized){b(document).mousedown(b.datepicker._checkExternalClick).find("body").append(b.datepicker.dpDiv);b.datepicker.initialized=true}var d=Array.prototype.slice.call(arguments,1);if(typeof a=="string"&&(a=="isDisabled"||a=="getDate"||a=="widget"))return b.datepicker["_"+a+"Datepicker"].apply(b.datepicker,[this[0]].concat(d));if(a=="option"&&arguments.length==2&&typeof arguments[1]=="string")return b.datepicker["_"+a+"Datepicker"].apply(b.datepicker,[this[0]].concat(d));\nreturn this.each(function(){typeof a=="string"?b.datepicker["_"+a+"Datepicker"].apply(b.datepicker,[this].concat(d)):b.datepicker._attachDatepicker(this,a)})};b.datepicker=new f;b.datepicker.initialized=false;b.datepicker.uuid=(new Date).getTime();b.datepicker.version="1.8.9";window["DP_jQuery_"+e]=b})(jQuery);\n(function(b,c){var f={buttons:true,height:true,maxHeight:true,maxWidth:true,minHeight:true,minWidth:true,width:true},g={maxHeight:true,maxWidth:true,minHeight:true,minWidth:true};b.widget("ui.dialog",{options:{autoOpen:true,buttons:{},closeOnEscape:true,closeText:"close",dialogClass:"",draggable:true,hide:null,height:"auto",maxHeight:false,maxWidth:false,minHeight:150,minWidth:150,modal:false,position:{my:"center",at:"center",collision:"fit",using:function(e){var a=b(this).css(e).offset().top;a<0&&\nb(this).css("top",e.top-a)}},resizable:true,show:null,stack:true,title:"",width:300,zIndex:1E3},_create:function(){this.originalTitle=this.element.attr("title");if(typeof this.originalTitle!=="string")this.originalTitle="";this.options.title=this.options.title||this.originalTitle;var e=this,a=e.options,d=a.title||"&#160;",h=b.ui.dialog.getTitleId(e.element),i=(e.uiDialog=b("<div></div>")).appendTo(document.body).hide().addClass("ui-dialog ui-widget ui-widget-content ui-corner-all "+a.dialogClass).css({zIndex:a.zIndex}).attr("tabIndex",\n-1).css("outline",0).keydown(function(q){if(a.closeOnEscape&&q.keyCode&&q.keyCode===b.ui.keyCode.ESCAPE){e.close(q);q.preventDefault()}}).attr({role:"dialog","aria-labelledby":h}).mousedown(function(q){e.moveToTop(false,q)});e.element.show().removeAttr("title").addClass("ui-dialog-content ui-widget-content").appendTo(i);var j=(e.uiDialogTitlebar=b("<div></div>")).addClass("ui-dialog-titlebar ui-widget-header ui-corner-all ui-helper-clearfix").prependTo(i),n=b(\'<a href="#"></a>\').addClass("ui-dialog-titlebar-close ui-corner-all").attr("role",\n"button").hover(function(){n.addClass("ui-state-hover")},function(){n.removeClass("ui-state-hover")}).focus(function(){n.addClass("ui-state-focus")}).blur(function(){n.removeClass("ui-state-focus")}).click(function(q){e.close(q);return false}).appendTo(j);(e.uiDialogTitlebarCloseText=b("<span></span>")).addClass("ui-icon ui-icon-closethick").text(a.closeText).appendTo(n);b("<span></span>").addClass("ui-dialog-title").attr("id",h).html(d).prependTo(j);if(b.isFunction(a.beforeclose)&&!b.isFunction(a.beforeClose))a.beforeClose=\na.beforeclose;j.find("*").add(j).disableSelection();a.draggable&&b.fn.draggable&&e._makeDraggable();a.resizable&&b.fn.resizable&&e._makeResizable();e._createButtons(a.buttons);e._isOpen=false;b.fn.bgiframe&&i.bgiframe()},_init:function(){this.options.autoOpen&&this.open()},destroy:function(){var e=this;e.overlay&&e.overlay.destroy();e.uiDialog.hide();e.element.unbind(".dialog").removeData("dialog").removeClass("ui-dialog-content ui-widget-content").hide().appendTo("body");e.uiDialog.remove();e.originalTitle&&\ne.element.attr("title",e.originalTitle);return e},widget:function(){return this.uiDialog},close:function(e){var a=this,d,h;if(false!==a._trigger("beforeClose",e)){a.overlay&&a.overlay.destroy();a.uiDialog.unbind("keypress.ui-dialog");a._isOpen=false;if(a.options.hide)a.uiDialog.hide(a.options.hide,function(){a._trigger("close",e)});else{a.uiDialog.hide();a._trigger("close",e)}b.ui.dialog.overlay.resize();if(a.options.modal){d=0;b(".ui-dialog").each(function(){if(this!==a.uiDialog[0]){h=b(this).css("z-index");\nisNaN(h)||(d=Math.max(d,h))}});b.ui.dialog.maxZ=d}return a}},isOpen:function(){return this._isOpen},moveToTop:function(e,a){var d=this,h=d.options;if(h.modal&&!e||!h.stack&&!h.modal)return d._trigger("focus",a);if(h.zIndex>b.ui.dialog.maxZ)b.ui.dialog.maxZ=h.zIndex;if(d.overlay){b.ui.dialog.maxZ+=1;d.overlay.$el.css("z-index",b.ui.dialog.overlay.maxZ=b.ui.dialog.maxZ)}e={scrollTop:d.element.attr("scrollTop"),scrollLeft:d.element.attr("scrollLeft")};b.ui.dialog.maxZ+=1;d.uiDialog.css("z-index",b.ui.dialog.maxZ);\nd.element.attr(e);d._trigger("focus",a);return d},open:function(){if(!this._isOpen){var e=this,a=e.options,d=e.uiDialog;e.overlay=a.modal?new b.ui.dialog.overlay(e):null;e._size();e._position(a.position);d.show(a.show);e.moveToTop(true);a.modal&&d.bind("keypress.ui-dialog",function(h){if(h.keyCode===b.ui.keyCode.TAB){var i=b(":tabbable",this),j=i.filter(":first");i=i.filter(":last");if(h.target===i[0]&&!h.shiftKey){j.focus(1);return false}else if(h.target===j[0]&&h.shiftKey){i.focus(1);return false}}});\nb(e.element.find(":tabbable").get().concat(d.find(".ui-dialog-buttonpane :tabbable").get().concat(d.get()))).eq(0).focus();e._isOpen=true;e._trigger("open");return e}},_createButtons:function(e){var a=this,d=false,h=b("<div></div>").addClass("ui-dialog-buttonpane ui-widget-content ui-helper-clearfix"),i=b("<div></div>").addClass("ui-dialog-buttonset").appendTo(h);a.uiDialog.find(".ui-dialog-buttonpane").remove();typeof e==="object"&&e!==null&&b.each(e,function(){return!(d=true)});if(d){b.each(e,function(j,\nn){n=b.isFunction(n)?{click:n,text:j}:n;j=b(\'<button type="button"></button>\').attr(n,true).unbind("click").click(function(){n.click.apply(a.element[0],arguments)}).appendTo(i);b.fn.button&&j.button()});h.appendTo(a.uiDialog)}},_makeDraggable:function(){function e(j){return{position:j.position,offset:j.offset}}var a=this,d=a.options,h=b(document),i;a.uiDialog.draggable({cancel:".ui-dialog-content, .ui-dialog-titlebar-close",handle:".ui-dialog-titlebar",containment:"document",start:function(j,n){i=\nd.height==="auto"?"auto":b(this).height();b(this).height(b(this).height()).addClass("ui-dialog-dragging");a._trigger("dragStart",j,e(n))},drag:function(j,n){a._trigger("drag",j,e(n))},stop:function(j,n){d.position=[n.position.left-h.scrollLeft(),n.position.top-h.scrollTop()];b(this).removeClass("ui-dialog-dragging").height(i);a._trigger("dragStop",j,e(n));b.ui.dialog.overlay.resize()}})},_makeResizable:function(e){function a(j){return{originalPosition:j.originalPosition,originalSize:j.originalSize,\nposition:j.position,size:j.size}}e=e===c?this.options.resizable:e;var d=this,h=d.options,i=d.uiDialog.css("position");e=typeof e==="string"?e:"n,e,s,w,se,sw,ne,nw";d.uiDialog.resizable({cancel:".ui-dialog-content",containment:"document",alsoResize:d.element,maxWidth:h.maxWidth,maxHeight:h.maxHeight,minWidth:h.minWidth,minHeight:d._minHeight(),handles:e,start:function(j,n){b(this).addClass("ui-dialog-resizing");d._trigger("resizeStart",j,a(n))},resize:function(j,n){d._trigger("resize",j,a(n))},stop:function(j,\nn){b(this).removeClass("ui-dialog-resizing");h.height=b(this).height();h.width=b(this).width();d._trigger("resizeStop",j,a(n));b.ui.dialog.overlay.resize()}}).css("position",i).find(".ui-resizable-se").addClass("ui-icon ui-icon-grip-diagonal-se")},_minHeight:function(){var e=this.options;return e.height==="auto"?e.minHeight:Math.min(e.minHeight,e.height)},_position:function(e){var a=[],d=[0,0],h;if(e){if(typeof e==="string"||typeof e==="object"&&"0"in e){a=e.split?e.split(" "):[e[0],e[1]];if(a.length===\n1)a[1]=a[0];b.each(["left","top"],function(i,j){if(+a[i]===a[i]){d[i]=a[i];a[i]=j}});e={my:a.join(" "),at:a.join(" "),offset:d.join(" ")}}e=b.extend({},b.ui.dialog.prototype.options.position,e)}else e=b.ui.dialog.prototype.options.position;(h=this.uiDialog.is(":visible"))||this.uiDialog.show();this.uiDialog.css({top:0,left:0}).position(b.extend({of:window},e));h||this.uiDialog.hide()},_setOptions:function(e){var a=this,d={},h=false;b.each(e,function(i,j){a._setOption(i,j);if(i in f)h=true;if(i in\ng)d[i]=j});h&&this._size();this.uiDialog.is(":data(resizable)")&&this.uiDialog.resizable("option",d)},_setOption:function(e,a){var d=this,h=d.uiDialog;switch(e){case "beforeclose":e="beforeClose";break;case "buttons":d._createButtons(a);break;case "closeText":d.uiDialogTitlebarCloseText.text(""+a);break;case "dialogClass":h.removeClass(d.options.dialogClass).addClass("ui-dialog ui-widget ui-widget-content ui-corner-all "+a);break;case "disabled":a?h.addClass("ui-dialog-disabled"):h.removeClass("ui-dialog-disabled");\nbreak;case "draggable":var i=h.is(":data(draggable)");i&&!a&&h.draggable("destroy");!i&&a&&d._makeDraggable();break;case "position":d._position(a);break;case "resizable":(i=h.is(":data(resizable)"))&&!a&&h.resizable("destroy");i&&typeof a==="string"&&h.resizable("option","handles",a);!i&&a!==false&&d._makeResizable(a);break;case "title":b(".ui-dialog-title",d.uiDialogTitlebar).html(""+(a||"&#160;"));break}b.Widget.prototype._setOption.apply(d,arguments)},_size:function(){var e=this.options,a,d,h=\nthis.uiDialog.is(":visible");this.element.show().css({width:"auto",minHeight:0,height:0});if(e.minWidth>e.width)e.width=e.minWidth;a=this.uiDialog.css({height:"auto",width:e.width}).height();d=Math.max(0,e.minHeight-a);if(e.height==="auto")if(b.support.minHeight)this.element.css({minHeight:d,height:"auto"});else{this.uiDialog.show();e=this.element.css("height","auto").height();h||this.uiDialog.hide();this.element.height(Math.max(e,d))}else this.element.height(Math.max(e.height-a,0));this.uiDialog.is(":data(resizable)")&&\nthis.uiDialog.resizable("option","minHeight",this._minHeight())}});b.extend(b.ui.dialog,{version:"1.8.9",uuid:0,maxZ:0,getTitleId:function(e){e=e.attr("id");if(!e){this.uuid+=1;e=this.uuid}return"ui-dialog-title-"+e},overlay:function(e){this.$el=b.ui.dialog.overlay.create(e)}});b.extend(b.ui.dialog.overlay,{instances:[],oldInstances:[],maxZ:0,events:b.map("focus,mousedown,mouseup,keydown,keypress,click".split(","),function(e){return e+".dialog-overlay"}).join(" "),create:function(e){if(this.instances.length===\n0){setTimeout(function(){b.ui.dialog.overlay.instances.length&&b(document).bind(b.ui.dialog.overlay.events,function(d){if(b(d.target).zIndex()<b.ui.dialog.overlay.maxZ)return false})},1);b(document).bind("keydown.dialog-overlay",function(d){if(e.options.closeOnEscape&&d.keyCode&&d.keyCode===b.ui.keyCode.ESCAPE){e.close(d);d.preventDefault()}});b(window).bind("resize.dialog-overlay",b.ui.dialog.overlay.resize)}var a=(this.oldInstances.pop()||b("<div></div>").addClass("ui-widget-overlay")).appendTo(document.body).css({width:this.width(),\nheight:this.height()});b.fn.bgiframe&&a.bgiframe();this.instances.push(a);return a},destroy:function(e){var a=b.inArray(e,this.instances);a!=-1&&this.oldInstances.push(this.instances.splice(a,1)[0]);this.instances.length===0&&b([document,window]).unbind(".dialog-overlay");e.remove();var d=0;b.each(this.instances,function(){d=Math.max(d,this.css("z-index"))});this.maxZ=d},height:function(){var e,a;if(b.browser.msie&&b.browser.version<7){e=Math.max(document.documentElement.scrollHeight,document.body.scrollHeight);\na=Math.max(document.documentElement.offsetHeight,document.body.offsetHeight);return e<a?b(window).height()+"px":e+"px"}else return b(document).height()+"px"},width:function(){var e,a;if(b.browser.msie&&b.browser.version<7){e=Math.max(document.documentElement.scrollWidth,document.body.scrollWidth);a=Math.max(document.documentElement.offsetWidth,document.body.offsetWidth);return e<a?b(window).width()+"px":e+"px"}else return b(document).width()+"px"},resize:function(){var e=b([]);b.each(b.ui.dialog.overlay.instances,\nfunction(){e=e.add(this)});e.css({width:0,height:0}).css({width:b.ui.dialog.overlay.width(),height:b.ui.dialog.overlay.height()})}});b.extend(b.ui.dialog.overlay.prototype,{destroy:function(){b.ui.dialog.overlay.destroy(this.$el)}})})(jQuery);\n(function(b){b.ui=b.ui||{};var c=/left|center|right/,f=/top|center|bottom/,g=b.fn.position,e=b.fn.offset;b.fn.position=function(a){if(!a||!a.of)return g.apply(this,arguments);a=b.extend({},a);var d=b(a.of),h=d[0],i=(a.collision||"flip").split(" "),j=a.offset?a.offset.split(" "):[0,0],n,q,l;if(h.nodeType===9){n=d.width();q=d.height();l={top:0,left:0}}else if(h.setTimeout){n=d.width();q=d.height();l={top:d.scrollTop(),left:d.scrollLeft()}}else if(h.preventDefault){a.at="left top";n=q=0;l={top:a.of.pageY,\nleft:a.of.pageX}}else{n=d.outerWidth();q=d.outerHeight();l=d.offset()}b.each(["my","at"],function(){var k=(a[this]||"").split(" ");if(k.length===1)k=c.test(k[0])?k.concat(["center"]):f.test(k[0])?["center"].concat(k):["center","center"];k[0]=c.test(k[0])?k[0]:"center";k[1]=f.test(k[1])?k[1]:"center";a[this]=k});if(i.length===1)i[1]=i[0];j[0]=parseInt(j[0],10)||0;if(j.length===1)j[1]=j[0];j[1]=parseInt(j[1],10)||0;if(a.at[0]==="right")l.left+=n;else if(a.at[0]==="center")l.left+=n/2;if(a.at[1]==="bottom")l.top+=\nq;else if(a.at[1]==="center")l.top+=q/2;l.left+=j[0];l.top+=j[1];return this.each(function(){var k=b(this),m=k.outerWidth(),o=k.outerHeight(),p=parseInt(b.curCSS(this,"marginLeft",true))||0,s=parseInt(b.curCSS(this,"marginTop",true))||0,r=m+p+(parseInt(b.curCSS(this,"marginRight",true))||0),u=o+s+(parseInt(b.curCSS(this,"marginBottom",true))||0),v=b.extend({},l),w;if(a.my[0]==="right")v.left-=m;else if(a.my[0]==="center")v.left-=m/2;if(a.my[1]==="bottom")v.top-=o;else if(a.my[1]==="center")v.top-=\no/2;v.left=Math.round(v.left);v.top=Math.round(v.top);w={left:v.left-p,top:v.top-s};b.each(["left","top"],function(y,B){b.ui.position[i[y]]&&b.ui.position[i[y]][B](v,{targetWidth:n,targetHeight:q,elemWidth:m,elemHeight:o,collisionPosition:w,collisionWidth:r,collisionHeight:u,offset:j,my:a.my,at:a.at})});b.fn.bgiframe&&k.bgiframe();k.offset(b.extend(v,{using:a.using}))})};b.ui.position={fit:{left:function(a,d){var h=b(window);h=d.collisionPosition.left+d.collisionWidth-h.width()-h.scrollLeft();a.left=\nh>0?a.left-h:Math.max(a.left-d.collisionPosition.left,a.left)},top:function(a,d){var h=b(window);h=d.collisionPosition.top+d.collisionHeight-h.height()-h.scrollTop();a.top=h>0?a.top-h:Math.max(a.top-d.collisionPosition.top,a.top)}},flip:{left:function(a,d){if(d.at[0]!=="center"){var h=b(window);h=d.collisionPosition.left+d.collisionWidth-h.width()-h.scrollLeft();var i=d.my[0]==="left"?-d.elemWidth:d.my[0]==="right"?d.elemWidth:0,j=d.at[0]==="left"?d.targetWidth:-d.targetWidth,n=-2*d.offset[0];a.left+=\nd.collisionPosition.left<0?i+j+n:h>0?i+j+n:0}},top:function(a,d){if(d.at[1]!=="center"){var h=b(window);h=d.collisionPosition.top+d.collisionHeight-h.height()-h.scrollTop();var i=d.my[1]==="top"?-d.elemHeight:d.my[1]==="bottom"?d.elemHeight:0,j=d.at[1]==="top"?d.targetHeight:-d.targetHeight,n=-2*d.offset[1];a.top+=d.collisionPosition.top<0?i+j+n:h>0?i+j+n:0}}}};if(!b.offset.setOffset){b.offset.setOffset=function(a,d){if(/static/.test(b.curCSS(a,"position")))a.style.position="relative";var h=b(a),\ni=h.offset(),j=parseInt(b.curCSS(a,"top",true),10)||0,n=parseInt(b.curCSS(a,"left",true),10)||0;i={top:d.top-i.top+j,left:d.left-i.left+n};"using"in d?d.using.call(a,i):h.css(i)};b.fn.offset=function(a){var d=this[0];if(!d||!d.ownerDocument)return null;if(a)return this.each(function(){b.offset.setOffset(this,a)});return e.call(this)}}})(jQuery);\n(function(b,c){b.widget("ui.progressbar",{options:{value:0,max:100},min:0,_create:function(){this.element.addClass("ui-progressbar ui-widget ui-widget-content ui-corner-all").attr({role:"progressbar","aria-valuemin":this.min,"aria-valuemax":this.options.max,"aria-valuenow":this._value()});this.valueDiv=b("<div class=\'ui-progressbar-value ui-widget-header ui-corner-left\'></div>").appendTo(this.element);this.oldValue=this._value();this._refreshValue()},destroy:function(){this.element.removeClass("ui-progressbar ui-widget ui-widget-content ui-corner-all").removeAttr("role").removeAttr("aria-valuemin").removeAttr("aria-valuemax").removeAttr("aria-valuenow");\nthis.valueDiv.remove();b.Widget.prototype.destroy.apply(this,arguments)},value:function(f){if(f===c)return this._value();this._setOption("value",f);return this},_setOption:function(f,g){if(f==="value"){this.options.value=g;this._refreshValue();this._value()===this.options.max&&this._trigger("complete")}b.Widget.prototype._setOption.apply(this,arguments)},_value:function(){var f=this.options.value;if(typeof f!=="number")f=0;return Math.min(this.options.max,Math.max(this.min,f))},_percentage:function(){return 100*\nthis._value()/this.options.max},_refreshValue:function(){var f=this.value(),g=this._percentage();if(this.oldValue!==f){this.oldValue=f;this._trigger("change")}this.valueDiv.toggleClass("ui-corner-right",f===this.options.max).width(g.toFixed(0)+"%");this.element.attr("aria-valuenow",f)}});b.extend(b.ui.progressbar,{version:"1.8.9"})})(jQuery);\n(function(b){b.widget("ui.slider",b.ui.mouse,{widgetEventPrefix:"slide",options:{animate:false,distance:0,max:100,min:0,orientation:"horizontal",range:false,step:1,value:0,values:null},_create:function(){var c=this,f=this.options;this._mouseSliding=this._keySliding=false;this._animateOff=true;this._handleIndex=null;this._detectOrientation();this._mouseInit();this.element.addClass("ui-slider ui-slider-"+this.orientation+" ui-widget ui-widget-content ui-corner-all");f.disabled&&this.element.addClass("ui-slider-disabled ui-disabled");\nthis.range=b([]);if(f.range){if(f.range===true){this.range=b("<div></div>");if(!f.values)f.values=[this._valueMin(),this._valueMin()];if(f.values.length&&f.values.length!==2)f.values=[f.values[0],f.values[0]]}else this.range=b("<div></div>");this.range.appendTo(this.element).addClass("ui-slider-range");if(f.range==="min"||f.range==="max")this.range.addClass("ui-slider-range-"+f.range);this.range.addClass("ui-widget-header")}b(".ui-slider-handle",this.element).length===0&&b("<a href=\'#\'></a>").appendTo(this.element).addClass("ui-slider-handle");\nif(f.values&&f.values.length)for(;b(".ui-slider-handle",this.element).length<f.values.length;)b("<a href=\'#\'></a>").appendTo(this.element).addClass("ui-slider-handle");this.handles=b(".ui-slider-handle",this.element).addClass("ui-state-default ui-corner-all");this.handle=this.handles.eq(0);this.handles.add(this.range).filter("a").click(function(g){g.preventDefault()}).hover(function(){f.disabled||b(this).addClass("ui-state-hover")},function(){b(this).removeClass("ui-state-hover")}).focus(function(){if(f.disabled)b(this).blur();\nelse{b(".ui-slider .ui-state-focus").removeClass("ui-state-focus");b(this).addClass("ui-state-focus")}}).blur(function(){b(this).removeClass("ui-state-focus")});this.handles.each(function(g){b(this).data("index.ui-slider-handle",g)});this.handles.keydown(function(g){var e=true,a=b(this).data("index.ui-slider-handle"),d,h,i;if(!c.options.disabled){switch(g.keyCode){case b.ui.keyCode.HOME:case b.ui.keyCode.END:case b.ui.keyCode.PAGE_UP:case b.ui.keyCode.PAGE_DOWN:case b.ui.keyCode.UP:case b.ui.keyCode.RIGHT:case b.ui.keyCode.DOWN:case b.ui.keyCode.LEFT:e=\nfalse;if(!c._keySliding){c._keySliding=true;b(this).addClass("ui-state-active");d=c._start(g,a);if(d===false)return}break}i=c.options.step;d=c.options.values&&c.options.values.length?(h=c.values(a)):(h=c.value());switch(g.keyCode){case b.ui.keyCode.HOME:h=c._valueMin();break;case b.ui.keyCode.END:h=c._valueMax();break;case b.ui.keyCode.PAGE_UP:h=c._trimAlignValue(d+(c._valueMax()-c._valueMin())/5);break;case b.ui.keyCode.PAGE_DOWN:h=c._trimAlignValue(d-(c._valueMax()-c._valueMin())/5);break;case b.ui.keyCode.UP:case b.ui.keyCode.RIGHT:if(d===\nc._valueMax())return;h=c._trimAlignValue(d+i);break;case b.ui.keyCode.DOWN:case b.ui.keyCode.LEFT:if(d===c._valueMin())return;h=c._trimAlignValue(d-i);break}c._slide(g,a,h);return e}}).keyup(function(g){var e=b(this).data("index.ui-slider-handle");if(c._keySliding){c._keySliding=false;c._stop(g,e);c._change(g,e);b(this).removeClass("ui-state-active")}});this._refreshValue();this._animateOff=false},destroy:function(){this.handles.remove();this.range.remove();this.element.removeClass("ui-slider ui-slider-horizontal ui-slider-vertical ui-slider-disabled ui-widget ui-widget-content ui-corner-all").removeData("slider").unbind(".slider");\nthis._mouseDestroy();return this},_mouseCapture:function(c){var f=this.options,g,e,a,d,h;if(f.disabled)return false;this.elementSize={width:this.element.outerWidth(),height:this.element.outerHeight()};this.elementOffset=this.element.offset();g=this._normValueFromMouse({x:c.pageX,y:c.pageY});e=this._valueMax()-this._valueMin()+1;d=this;this.handles.each(function(i){var j=Math.abs(g-d.values(i));if(e>j){e=j;a=b(this);h=i}});if(f.range===true&&this.values(1)===f.min){h+=1;a=b(this.handles[h])}if(this._start(c,\nh)===false)return false;this._mouseSliding=true;d._handleIndex=h;a.addClass("ui-state-active").focus();f=a.offset();this._clickOffset=!b(c.target).parents().andSelf().is(".ui-slider-handle")?{left:0,top:0}:{left:c.pageX-f.left-a.width()/2,top:c.pageY-f.top-a.height()/2-(parseInt(a.css("borderTopWidth"),10)||0)-(parseInt(a.css("borderBottomWidth"),10)||0)+(parseInt(a.css("marginTop"),10)||0)};this.handles.hasClass("ui-state-hover")||this._slide(c,h,g);return this._animateOff=true},_mouseStart:function(){return true},\n_mouseDrag:function(c){var f=this._normValueFromMouse({x:c.pageX,y:c.pageY});this._slide(c,this._handleIndex,f);return false},_mouseStop:function(c){this.handles.removeClass("ui-state-active");this._mouseSliding=false;this._stop(c,this._handleIndex);this._change(c,this._handleIndex);this._clickOffset=this._handleIndex=null;return this._animateOff=false},_detectOrientation:function(){this.orientation=this.options.orientation==="vertical"?"vertical":"horizontal"},_normValueFromMouse:function(c){var f;\nif(this.orientation==="horizontal"){f=this.elementSize.width;c=c.x-this.elementOffset.left-(this._clickOffset?this._clickOffset.left:0)}else{f=this.elementSize.height;c=c.y-this.elementOffset.top-(this._clickOffset?this._clickOffset.top:0)}f=c/f;if(f>1)f=1;if(f<0)f=0;if(this.orientation==="vertical")f=1-f;c=this._valueMax()-this._valueMin();return this._trimAlignValue(this._valueMin()+f*c)},_start:function(c,f){var g={handle:this.handles[f],value:this.value()};if(this.options.values&&this.options.values.length){g.value=\nthis.values(f);g.values=this.values()}return this._trigger("start",c,g)},_slide:function(c,f,g){var e;if(this.options.values&&this.options.values.length){e=this.values(f?0:1);if(this.options.values.length===2&&this.options.range===true&&(f===0&&g>e||f===1&&g<e))g=e;if(g!==this.values(f)){e=this.values();e[f]=g;c=this._trigger("slide",c,{handle:this.handles[f],value:g,values:e});this.values(f?0:1);c!==false&&this.values(f,g,true)}}else if(g!==this.value()){c=this._trigger("slide",c,{handle:this.handles[f],\nvalue:g});c!==false&&this.value(g)}},_stop:function(c,f){var g={handle:this.handles[f],value:this.value()};if(this.options.values&&this.options.values.length){g.value=this.values(f);g.values=this.values()}this._trigger("stop",c,g)},_change:function(c,f){if(!this._keySliding&&!this._mouseSliding){var g={handle:this.handles[f],value:this.value()};if(this.options.values&&this.options.values.length){g.value=this.values(f);g.values=this.values()}this._trigger("change",c,g)}},value:function(c){if(arguments.length){this.options.value=\nthis._trimAlignValue(c);this._refreshValue();this._change(null,0)}return this._value()},values:function(c,f){var g,e,a;if(arguments.length>1){this.options.values[c]=this._trimAlignValue(f);this._refreshValue();this._change(null,c)}if(arguments.length)if(b.isArray(arguments[0])){g=this.options.values;e=arguments[0];for(a=0;a<g.length;a+=1){g[a]=this._trimAlignValue(e[a]);this._change(null,a)}this._refreshValue()}else return this.options.values&&this.options.values.length?this._values(c):this.value();\nelse return this._values()},_setOption:function(c,f){var g,e=0;if(b.isArray(this.options.values))e=this.options.values.length;b.Widget.prototype._setOption.apply(this,arguments);switch(c){case "disabled":if(f){this.handles.filter(".ui-state-focus").blur();this.handles.removeClass("ui-state-hover");this.handles.attr("disabled","disabled");this.element.addClass("ui-disabled")}else{this.handles.removeAttr("disabled");this.element.removeClass("ui-disabled")}break;case "orientation":this._detectOrientation();\nthis.element.removeClass("ui-slider-horizontal ui-slider-vertical").addClass("ui-slider-"+this.orientation);this._refreshValue();break;case "value":this._animateOff=true;this._refreshValue();this._change(null,0);this._animateOff=false;break;case "values":this._animateOff=true;this._refreshValue();for(g=0;g<e;g+=1)this._change(null,g);this._animateOff=false;break}},_value:function(){var c=this.options.value;return c=this._trimAlignValue(c)},_values:function(c){var f,g;if(arguments.length){f=this.options.values[c];\nreturn f=this._trimAlignValue(f)}else{f=this.options.values.slice();for(g=0;g<f.length;g+=1)f[g]=this._trimAlignValue(f[g]);return f}},_trimAlignValue:function(c){if(c<=this._valueMin())return this._valueMin();if(c>=this._valueMax())return this._valueMax();var f=this.options.step>0?this.options.step:1,g=(c-this._valueMin())%f;alignValue=c-g;if(Math.abs(g)*2>=f)alignValue+=g>0?f:-f;return parseFloat(alignValue.toFixed(5))},_valueMin:function(){return this.options.min},_valueMax:function(){return this.options.max},\n_refreshValue:function(){var c=this.options.range,f=this.options,g=this,e=!this._animateOff?f.animate:false,a,d={},h,i,j,n;if(this.options.values&&this.options.values.length)this.handles.each(function(q){a=(g.values(q)-g._valueMin())/(g._valueMax()-g._valueMin())*100;d[g.orientation==="horizontal"?"left":"bottom"]=a+"%";b(this).stop(1,1)[e?"animate":"css"](d,f.animate);if(g.options.range===true)if(g.orientation==="horizontal"){if(q===0)g.range.stop(1,1)[e?"animate":"css"]({left:a+"%"},f.animate);\nif(q===1)g.range[e?"animate":"css"]({width:a-h+"%"},{queue:false,duration:f.animate})}else{if(q===0)g.range.stop(1,1)[e?"animate":"css"]({bottom:a+"%"},f.animate);if(q===1)g.range[e?"animate":"css"]({height:a-h+"%"},{queue:false,duration:f.animate})}h=a});else{i=this.value();j=this._valueMin();n=this._valueMax();a=n!==j?(i-j)/(n-j)*100:0;d[g.orientation==="horizontal"?"left":"bottom"]=a+"%";this.handle.stop(1,1)[e?"animate":"css"](d,f.animate);if(c==="min"&&this.orientation==="horizontal")this.range.stop(1,\n1)[e?"animate":"css"]({width:a+"%"},f.animate);if(c==="max"&&this.orientation==="horizontal")this.range[e?"animate":"css"]({width:100-a+"%"},{queue:false,duration:f.animate});if(c==="min"&&this.orientation==="vertical")this.range.stop(1,1)[e?"animate":"css"]({height:a+"%"},f.animate);if(c==="max"&&this.orientation==="vertical")this.range[e?"animate":"css"]({height:100-a+"%"},{queue:false,duration:f.animate})}}});b.extend(b.ui.slider,{version:"1.8.9"})})(jQuery);\n(function(b,c){function f(){return++e}function g(){return++a}var e=0,a=0;b.widget("ui.tabs",{options:{add:null,ajaxOptions:null,cache:false,cookie:null,collapsible:false,disable:null,disabled:[],enable:null,event:"click",fx:null,idPrefix:"ui-tabs-",load:null,panelTemplate:"<div></div>",remove:null,select:null,show:null,spinner:"<em>Loading&#8230;</em>",tabTemplate:"<li><a href=\'#{href}\'><span>#{label}</span></a></li>"},_create:function(){this._tabify(true)},_setOption:function(d,h){if(d=="selected")this.options.collapsible&&\nh==this.options.selected||this.select(h);else{this.options[d]=h;this._tabify()}},_tabId:function(d){return d.title&&d.title.replace(/\\s/g,"_").replace(/[^\\w\\u00c0-\\uFFFF-]/g,"")||this.options.idPrefix+f()},_sanitizeSelector:function(d){return d.replace(/:/g,"\\\\:")},_cookie:function(){var d=this.cookie||(this.cookie=this.options.cookie.name||"ui-tabs-"+g());return b.cookie.apply(null,[d].concat(b.makeArray(arguments)))},_ui:function(d,h){return{tab:d,panel:h,index:this.anchors.index(d)}},_cleanup:function(){this.lis.filter(".ui-state-processing").removeClass("ui-state-processing").find("span:data(label.tabs)").each(function(){var d=\nb(this);d.html(d.data("label.tabs")).removeData("label.tabs")})},_tabify:function(d){function h(r,u){r.css("display","");!b.support.opacity&&u.opacity&&r[0].style.removeAttribute("filter")}var i=this,j=this.options,n=/^#.+/;this.list=this.element.find("ol,ul").eq(0);this.lis=b(" > li:has(a[href])",this.list);this.anchors=this.lis.map(function(){return b("a",this)[0]});this.panels=b([]);this.anchors.each(function(r,u){var v=b(u).attr("href"),w=v.split("#")[0],y;if(w&&(w===location.toString().split("#")[0]||\n(y=b("base")[0])&&w===y.href)){v=u.hash;u.href=v}if(n.test(v))i.panels=i.panels.add(i.element.find(i._sanitizeSelector(v)));else if(v&&v!=="#"){b.data(u,"href.tabs",v);b.data(u,"load.tabs",v.replace(/#.*$/,""));v=i._tabId(u);u.href="#"+v;u=i.element.find("#"+v);if(!u.length){u=b(j.panelTemplate).attr("id",v).addClass("ui-tabs-panel ui-widget-content ui-corner-bottom").insertAfter(i.panels[r-1]||i.list);u.data("destroy.tabs",true)}i.panels=i.panels.add(u)}else j.disabled.push(r)});if(d){this.element.addClass("ui-tabs ui-widget ui-widget-content ui-corner-all");\nthis.list.addClass("ui-tabs-nav ui-helper-reset ui-helper-clearfix ui-widget-header ui-corner-all");this.lis.addClass("ui-state-default ui-corner-top");this.panels.addClass("ui-tabs-panel ui-widget-content ui-corner-bottom");if(j.selected===c){location.hash&&this.anchors.each(function(r,u){if(u.hash==location.hash){j.selected=r;return false}});if(typeof j.selected!=="number"&&j.cookie)j.selected=parseInt(i._cookie(),10);if(typeof j.selected!=="number"&&this.lis.filter(".ui-tabs-selected").length)j.selected=\nthis.lis.index(this.lis.filter(".ui-tabs-selected"));j.selected=j.selected||(this.lis.length?0:-1)}else if(j.selected===null)j.selected=-1;j.selected=j.selected>=0&&this.anchors[j.selected]||j.selected<0?j.selected:0;j.disabled=b.unique(j.disabled.concat(b.map(this.lis.filter(".ui-state-disabled"),function(r){return i.lis.index(r)}))).sort();b.inArray(j.selected,j.disabled)!=-1&&j.disabled.splice(b.inArray(j.selected,j.disabled),1);this.panels.addClass("ui-tabs-hide");this.lis.removeClass("ui-tabs-selected ui-state-active");\nif(j.selected>=0&&this.anchors.length){i.element.find(i._sanitizeSelector(i.anchors[j.selected].hash)).removeClass("ui-tabs-hide");this.lis.eq(j.selected).addClass("ui-tabs-selected ui-state-active");i.element.queue("tabs",function(){i._trigger("show",null,i._ui(i.anchors[j.selected],i.element.find(i._sanitizeSelector(i.anchors[j.selected].hash))[0]))});this.load(j.selected)}b(window).bind("unload",function(){i.lis.add(i.anchors).unbind(".tabs");i.lis=i.anchors=i.panels=null})}else j.selected=this.lis.index(this.lis.filter(".ui-tabs-selected"));\nthis.element[j.collapsible?"addClass":"removeClass"]("ui-tabs-collapsible");j.cookie&&this._cookie(j.selected,j.cookie);d=0;for(var q;q=this.lis[d];d++)b(q)[b.inArray(d,j.disabled)!=-1&&!b(q).hasClass("ui-tabs-selected")?"addClass":"removeClass"]("ui-state-disabled");j.cache===false&&this.anchors.removeData("cache.tabs");this.lis.add(this.anchors).unbind(".tabs");if(j.event!=="mouseover"){var l=function(r,u){u.is(":not(.ui-state-disabled)")&&u.addClass("ui-state-"+r)},k=function(r,u){u.removeClass("ui-state-"+\nr)};this.lis.bind("mouseover.tabs",function(){l("hover",b(this))});this.lis.bind("mouseout.tabs",function(){k("hover",b(this))});this.anchors.bind("focus.tabs",function(){l("focus",b(this).closest("li"))});this.anchors.bind("blur.tabs",function(){k("focus",b(this).closest("li"))})}var m,o;if(j.fx)if(b.isArray(j.fx)){m=j.fx[0];o=j.fx[1]}else m=o=j.fx;var p=o?function(r,u){b(r).closest("li").addClass("ui-tabs-selected ui-state-active");u.hide().removeClass("ui-tabs-hide").animate(o,o.duration||"normal",\nfunction(){h(u,o);i._trigger("show",null,i._ui(r,u[0]))})}:function(r,u){b(r).closest("li").addClass("ui-tabs-selected ui-state-active");u.removeClass("ui-tabs-hide");i._trigger("show",null,i._ui(r,u[0]))},s=m?function(r,u){u.animate(m,m.duration||"normal",function(){i.lis.removeClass("ui-tabs-selected ui-state-active");u.addClass("ui-tabs-hide");h(u,m);i.element.dequeue("tabs")})}:function(r,u){i.lis.removeClass("ui-tabs-selected ui-state-active");u.addClass("ui-tabs-hide");i.element.dequeue("tabs")};\nthis.anchors.bind(j.event+".tabs",function(){var r=this,u=b(r).closest("li"),v=i.panels.filter(":not(.ui-tabs-hide)"),w=i.element.find(i._sanitizeSelector(r.hash));if(u.hasClass("ui-tabs-selected")&&!j.collapsible||u.hasClass("ui-state-disabled")||u.hasClass("ui-state-processing")||i.panels.filter(":animated").length||i._trigger("select",null,i._ui(this,w[0]))===false){this.blur();return false}j.selected=i.anchors.index(this);i.abort();if(j.collapsible)if(u.hasClass("ui-tabs-selected")){j.selected=\n-1;j.cookie&&i._cookie(j.selected,j.cookie);i.element.queue("tabs",function(){s(r,v)}).dequeue("tabs");this.blur();return false}else if(!v.length){j.cookie&&i._cookie(j.selected,j.cookie);i.element.queue("tabs",function(){p(r,w)});i.load(i.anchors.index(this));this.blur();return false}j.cookie&&i._cookie(j.selected,j.cookie);if(w.length){v.length&&i.element.queue("tabs",function(){s(r,v)});i.element.queue("tabs",function(){p(r,w)});i.load(i.anchors.index(this))}else throw"jQuery UI Tabs: Mismatching fragment identifier.";\nb.browser.msie&&this.blur()});this.anchors.bind("click.tabs",function(){return false})},_getIndex:function(d){if(typeof d=="string")d=this.anchors.index(this.anchors.filter("[href$="+d+"]"));return d},destroy:function(){var d=this.options;this.abort();this.element.unbind(".tabs").removeClass("ui-tabs ui-widget ui-widget-content ui-corner-all ui-tabs-collapsible").removeData("tabs");this.list.removeClass("ui-tabs-nav ui-helper-reset ui-helper-clearfix ui-widget-header ui-corner-all");this.anchors.each(function(){var h=\nb.data(this,"href.tabs");if(h)this.href=h;var i=b(this).unbind(".tabs");b.each(["href","load","cache"],function(j,n){i.removeData(n+".tabs")})});this.lis.unbind(".tabs").add(this.panels).each(function(){b.data(this,"destroy.tabs")?b(this).remove():b(this).removeClass("ui-state-default ui-corner-top ui-tabs-selected ui-state-active ui-state-hover ui-state-focus ui-state-disabled ui-tabs-panel ui-widget-content ui-corner-bottom ui-tabs-hide")});d.cookie&&this._cookie(null,d.cookie);return this},add:function(d,\nh,i){if(i===c)i=this.anchors.length;var j=this,n=this.options;h=b(n.tabTemplate.replace(/#\\{href\\}/g,d).replace(/#\\{label\\}/g,h));d=!d.indexOf("#")?d.replace("#",""):this._tabId(b("a",h)[0]);h.addClass("ui-state-default ui-corner-top").data("destroy.tabs",true);var q=j.element.find("#"+d);q.length||(q=b(n.panelTemplate).attr("id",d).data("destroy.tabs",true));q.addClass("ui-tabs-panel ui-widget-content ui-corner-bottom ui-tabs-hide");if(i>=this.lis.length){h.appendTo(this.list);q.appendTo(this.list[0].parentNode)}else{h.insertBefore(this.lis[i]);\nq.insertBefore(this.panels[i])}n.disabled=b.map(n.disabled,function(l){return l>=i?++l:l});this._tabify();if(this.anchors.length==1){n.selected=0;h.addClass("ui-tabs-selected ui-state-active");q.removeClass("ui-tabs-hide");this.element.queue("tabs",function(){j._trigger("show",null,j._ui(j.anchors[0],j.panels[0]))});this.load(0)}this._trigger("add",null,this._ui(this.anchors[i],this.panels[i]));return this},remove:function(d){d=this._getIndex(d);var h=this.options,i=this.lis.eq(d).remove(),j=this.panels.eq(d).remove();\nif(i.hasClass("ui-tabs-selected")&&this.anchors.length>1)this.select(d+(d+1<this.anchors.length?1:-1));h.disabled=b.map(b.grep(h.disabled,function(n){return n!=d}),function(n){return n>=d?--n:n});this._tabify();this._trigger("remove",null,this._ui(i.find("a")[0],j[0]));return this},enable:function(d){d=this._getIndex(d);var h=this.options;if(b.inArray(d,h.disabled)!=-1){this.lis.eq(d).removeClass("ui-state-disabled");h.disabled=b.grep(h.disabled,function(i){return i!=d});this._trigger("enable",null,\nthis._ui(this.anchors[d],this.panels[d]));return this}},disable:function(d){d=this._getIndex(d);var h=this.options;if(d!=h.selected){this.lis.eq(d).addClass("ui-state-disabled");h.disabled.push(d);h.disabled.sort();this._trigger("disable",null,this._ui(this.anchors[d],this.panels[d]))}return this},select:function(d){d=this._getIndex(d);if(d==-1)if(this.options.collapsible&&this.options.selected!=-1)d=this.options.selected;else return this;this.anchors.eq(d).trigger(this.options.event+".tabs");return this},\nload:function(d){d=this._getIndex(d);var h=this,i=this.options,j=this.anchors.eq(d)[0],n=b.data(j,"load.tabs");this.abort();if(!n||this.element.queue("tabs").length!==0&&b.data(j,"cache.tabs"))this.element.dequeue("tabs");else{this.lis.eq(d).addClass("ui-state-processing");if(i.spinner){var q=b("span",j);q.data("label.tabs",q.html()).html(i.spinner)}this.xhr=b.ajax(b.extend({},i.ajaxOptions,{url:n,success:function(l,k){h.element.find(h._sanitizeSelector(j.hash)).html(l);h._cleanup();i.cache&&b.data(j,\n"cache.tabs",true);h._trigger("load",null,h._ui(h.anchors[d],h.panels[d]));try{i.ajaxOptions.success(l,k)}catch(m){}},error:function(l,k){h._cleanup();h._trigger("load",null,h._ui(h.anchors[d],h.panels[d]));try{i.ajaxOptions.error(l,k,d,j)}catch(m){}}}));h.element.dequeue("tabs");return this}},abort:function(){this.element.queue([]);this.panels.stop(false,true);this.element.queue("tabs",this.element.queue("tabs").splice(-2,2));if(this.xhr){this.xhr.abort();delete this.xhr}this._cleanup();return this},\nurl:function(d,h){this.anchors.eq(d).removeData("cache.tabs").data("load.tabs",h);return this},length:function(){return this.anchors.length}});b.extend(b.ui.tabs,{version:"1.8.9"});b.extend(b.ui.tabs.prototype,{rotation:null,rotate:function(d,h){var i=this,j=this.options,n=i._rotate||(i._rotate=function(q){clearTimeout(i.rotation);i.rotation=setTimeout(function(){var l=j.selected;i.select(++l<i.anchors.length?l:0)},d);q&&q.stopPropagation()});h=i._unrotate||(i._unrotate=!h?function(q){q.clientX&&\ni.rotate(null)}:function(){t=j.selected;n()});if(d){this.element.bind("tabsshow",n);this.anchors.bind(j.event+".tabs",h);n()}else{clearTimeout(i.rotation);this.element.unbind("tabsshow",n);this.anchors.unbind(j.event+".tabs",h);delete this._rotate;delete this._unrotate}return this}})})(jQuery);\n
'''

browserSel = '''/* CSS Browser Selector v0.4.0 (Nov 02, 2010) Rafael Lima (http://rafael.adm.br) */function css_browser_selector(u){var ua=u.toLowerCase(),is=function(t){return ua.indexOf(t)>-1},g='gecko',w='webkit',s='safari',o='opera',m='mobile',h=document.documentElement,b=[(!(/opera|webtv/i.test(ua))&&/msie\s(\d)/.test(ua))?('ie ie'+RegExp.$1):is('firefox/2')?g+' ff2':is('firefox/3.5')?g+' ff3 ff3_5':is('firefox/3.6')?g+' ff3 ff3_6':is('firefox/3')?g+' ff3':is('gecko/')?g:is('opera')?o+(/version\/(\d+)/.test(ua)?' '+o+RegExp.$1:(/opera(\s|\/)(\d+)/.test(ua)?' '+o+RegExp.$2:'')):is('konqueror')?'konqueror':is('blackberry')?m+' blackberry':is('android')?m+' android':is('chrome')?w+' chrome':is('iron')?w+' iron':is('applewebkit/')?w+' '+s+(/version\/(\d+)/.test(ua)?' '+s+RegExp.$1:''):is('mozilla/')?g:'',is('j2me')?m+' j2me':is('iphone')?m+' iphone':is('ipod')?m+' ipod':is('ipad')?m+' ipad':is('mac')?'mac':is('darwin')?'mac':is('webtv')?'webtv':is('win')?'win'+(is('windows nt 6.0')?' vista':''):is('freebsd')?'freebsd':(is('x11')||is('linux'))?'linux':'','js']; c = b.join(' '); h.className += ' '+c; return c;}; css_browser_selector(navigator.userAgent);'''

########NEW FILE########
__FILENAME__ = lang
# -*- coding: utf-8 -*-
# Copyright: Damien Elmes <anki@ichi2.net>
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

import os, sys, re
import gettext
import threading

langs = [
    (u"Afrikaans", "af"),
    (u"Bahasa Melayu", "ms"),
    (u"Dansk", "da"),
    (u"Deutsch", "de"),
    (u"Eesti", "et"),
    (u"English", "en"),
    (u"Español", "es"),
    (u"Esperanto", "eo"),
    (u"Français", "fr"),
    (u"Italiano", "it"),
    (u"Lenga d'òc", "oc"),
    (u"Magyar", "hu"),
    (u"Nederlands","nl"),
    (u"Norsk","nb"),
    (u"Occitan","oc"),
    (u"Plattdüütsch", "nds"),
    (u"Polski", "pl"),
    (u"Português Brasileiro", "pt_BR"),
    (u"Português", "pt"),
    (u"Româneşte", "ro"),
    (u"Slovenščina", "sl"),
    (u"Suomi", "fi"),
    (u"Svenska", "sv"),
    (u"Tiếng Việt", "vi"),
    (u"Türkçe", "tr"),
    (u"Čeština", "cs"),
    (u"Ελληνικά", "el"),
    (u"босански", "bs"),
    (u"Български", "bg"),
    (u"Монгол хэл","mn"),
    (u"русский язык", "ru"),
    (u"українська мова", "uk"),
    (u"עִבְרִית", "he"),
    (u"العربية", "ar"),
    (u"فارسی", "fa"),
    (u"ภาษาไทย", "th"),
    (u"日本語", "ja"),
    (u"简体中文", "zh_CN"),
    (u"繁體中文", "zh_TW"),
    (u"한국어", "ko"),
]

threadLocal = threading.local()

# global defaults
currentLang = None
currentTranslation = None

def localTranslation():
    "Return the translation local to this thread, or the default."
    if getattr(threadLocal, 'currentTranslation', None):
        return threadLocal.currentTranslation
    else:
        return currentTranslation

def _(str):
    return localTranslation().ugettext(str)

def ngettext(single, plural, n):
    return localTranslation().ungettext(single, plural, n)

def langDir():
    dir = os.path.join(os.path.dirname(
        os.path.abspath(__file__)), "locale")
    if not os.path.exists(dir):
        dir = os.path.join(os.path.dirname(sys.argv[0]), "locale")
    return dir

def setLang(lang, local=True):
    trans = gettext.translation(
        'libanki', langDir(), languages=[lang], fallback=True)
    if local:
        threadLocal.currentLang = lang
        threadLocal.currentTranslation = trans
    else:
        global currentLang, currentTranslation
        currentLang = lang
        currentTranslation = trans

def getLang():
    "Return the language local to this thread, or the default."
    if getattr(threadLocal, 'currentLang', None):
        return threadLocal.currentLang
    else:
        return currentLang

def noHint(str):
    "Remove translation hint from end of string."
    return re.sub("(^.*?)( ?\(.+?\))?$", "\\1", str)

if not currentTranslation:
    setLang("en_US", local=False)

########NEW FILE########
__FILENAME__ = latex
# -*- coding: utf-8 -*-
# Copyright: Damien Elmes <anki@ichi2.net>
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

import re, os, sys, shutil, cgi, subprocess
from anki.utils import checksum, call, namedtmp, tmpdir, isMac, stripHTML
from anki.hooks import addHook
from htmlentitydefs import entitydefs
from anki.lang import _

latexCmd = ["latex", "-interaction=nonstopmode"]
latexDviPngCmd = ["dvipng", "-D", "200", "-T", "tight"]
build = True # if off, use existing media but don't create new
regexps = {
    "standard": re.compile(r"\[latex\](.+?)\[/latex\]", re.DOTALL | re.IGNORECASE),
    "expression": re.compile(r"\[\$\](.+?)\[/\$\]", re.DOTALL | re.IGNORECASE),
    "math": re.compile(r"\[\$\$\](.+?)\[/\$\$\]", re.DOTALL | re.IGNORECASE),
    }

# add standard tex install location to osx
if isMac:
    os.environ['PATH'] += ":/usr/texbin"

def stripLatex(text):
    for match in regexps['standard'].finditer(text):
        text = text.replace(match.group(), "")
    for match in regexps['expression'].finditer(text):
        text = text.replace(match.group(), "")
    for match in regexps['math'].finditer(text):
        text = text.replace(match.group(), "")
    return text

def mungeQA(html, type, fields, model, data, col):
    "Convert TEXT with embedded latex tags to image links."
    for match in regexps['standard'].finditer(html):
        html = html.replace(match.group(), _imgLink(col, match.group(1), model))
    for match in regexps['expression'].finditer(html):
        html = html.replace(match.group(), _imgLink(
            col, "$" + match.group(1) + "$", model))
    for match in regexps['math'].finditer(html):
        html = html.replace(match.group(), _imgLink(
            col,
            "\\begin{displaymath}" + match.group(1) + "\\end{displaymath}", model))
    return html

def _imgLink(col, latex, model):
    "Return an img link for LATEX, creating if necesssary."
    txt = _latexFromHtml(col, latex)
    fname = "latex-%s.png" % checksum(txt.encode("utf8"))
    link = '<img src="%s">' % fname
    if os.path.exists(fname):
        return link
    elif not build:
        return u"[latex]%s[/latex]" % latex
    else:
        err = _buildImg(col, txt, fname, model)
        if err:
            return err
        else:
            return link

def _latexFromHtml(col, latex):
    "Convert entities and fix newlines."
    # entitydefs defines nbsp as \xa0 instead of a standard space, so we
    # replace it first
    latex = latex.replace("&nbsp;", " ")
    latex = re.sub("<br( /)?>|<div>", "\n", latex)
    # replace <div> etc with spaces
    latex = re.sub("<.+?>", " ", latex)
    latex = stripHTML(latex)
    return latex

def _buildImg(col, latex, fname, model):
    # add header/footer & convert to utf8
    latex = (model["latexPre"] + "\n" +
             latex + "\n" +
             model["latexPost"])
    latex = latex.encode("utf8")
    # it's only really secure if run in a jail, but these are the most common
    for bad in ("write18", "\\readline", "\\input", "\\include", "\\catcode",
                "\\openout", "\\write", "\\loop", "\\def", "\\shipout"):
        if bad in latex:
            return _("""\
For security reasons, '%s' is not allowed on cards. You can still use \
it by placing the command in a different package, and importing that \
package in the LaTeX header instead.""") % bad
    # write into a temp file
    log = open(namedtmp("latex_log.txt"), "w")
    texpath = namedtmp("tmp.tex")
    texfile = file(texpath, "w")
    texfile.write(latex)
    texfile.close()
    mdir = col.media.dir()
    oldcwd = os.getcwd()
    png = namedtmp("tmp.png")
    try:
        # generate dvi
        os.chdir(tmpdir())
        if call(latexCmd + ["tmp.tex"], stdout=log, stderr=log):
            return _errMsg("latex", texpath)
        # and png
        if call(latexDviPngCmd + ["tmp.dvi", "-o", "tmp.png"],
                stdout=log, stderr=log):
            return _errMsg("dvipng", texpath)
        # add to media
        shutil.copyfile(png, os.path.join(mdir, fname))
        return
    finally:
        os.chdir(oldcwd)

def _errMsg(type, texpath):
    msg = (_("Error executing %s.") % type) + "<br>"
    msg += (_("Generated file: %s") % texpath) + "<br>"
    try:
        log = open(namedtmp("latex_log.txt", rm=False)).read()
        if not log:
            raise Exception()
        msg += "<small><pre>" + cgi.escape(log) + "</pre></small>"
    except:
        msg += _("Have you installed latex and dvipng?")
        pass
    return msg

# setup q/a filter
addHook("mungeQA", mungeQA)

########NEW FILE########
__FILENAME__ = media
# -*- coding: utf-8 -*-
# Copyright: Damien Elmes <anki@ichi2.net>
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

import os, shutil, re, urllib, urllib2, time, unicodedata, \
    sys, zipfile
from cStringIO import StringIO
from anki.utils import checksum, intTime, namedtmp, isWin, isMac, json
from anki.lang import _
from anki.db import DB
from anki.consts import *
from anki.latex import mungeQA

class MediaManager(object):

    # other code depends on this order, so don't reorder
    regexps = ("(?i)(\[sound:([^]]+)\])",
               "(?i)(<img[^>]+src=[\"']?([^\"'>]+)[\"']?[^>]*>)")

    def __init__(self, col, server):
        self.col = col
        if server:
            self._dir = None
            return
        # media directory
        self._dir = re.sub("(?i)\.(anki2)$", ".media", self.col.path)
        # convert dir to unicode if it's not already
        if isinstance(self._dir, str):
            self._dir = unicode(self._dir, sys.getfilesystemencoding())
        if not os.path.exists(self._dir):
            os.makedirs(self._dir)
        try:
            self._oldcwd = os.getcwd()
        except OSError:
            # cwd doesn't exist
            self._oldcwd = None
        os.chdir(self._dir)
        # change database
        self.connect()

    def connect(self):
        if self.col.server:
            return
        path = self.dir()+".db"
        create = not os.path.exists(path)
        os.chdir(self._dir)
        self.db = DB(path)
        if create:
            self._initDB()

    def close(self):
        if self.col.server:
            return
        self.db.close()
        self.db = None
        # change cwd back to old location
        if self._oldcwd:
            try:
                os.chdir(self._oldcwd)
            except:
                # may have been deleted
                pass

    def dir(self):
        return self._dir

    # Adding media
    ##########################################################################

    def addFile(self, opath):
        """Copy PATH to MEDIADIR, and return new filename.
If the same name exists, compare checksums."""
        mdir = self.dir()
        # remove any dangerous characters
        base = re.sub(r"[][<>:/\\&?\"\|]", "", os.path.basename(opath))
        dst = os.path.join(mdir, base)
        # if it doesn't exist, copy it directly
        if not os.path.exists(dst):
            shutil.copyfile(opath, dst)
            return base
        # if it's identical, reuse
        if self.filesIdentical(opath, dst):
            return base
        # otherwise, find a unique name
        (root, ext) = os.path.splitext(base)
        def repl(match):
            n = int(match.group(1))
            return " (%d)" % (n+1)
        while True:
            path = os.path.join(mdir, root + ext)
            if not os.path.exists(path):
                break
            reg = " \((\d+)\)$"
            if not re.search(reg, root):
                root = root + " (1)"
            else:
                root = re.sub(reg, repl, root)
        # copy and return
        shutil.copyfile(opath, path)
        return os.path.basename(os.path.basename(path))

    def filesIdentical(self, path1, path2):
        "True if files are the same."
        return (checksum(open(path1, "rb").read()) ==
                checksum(open(path2, "rb").read()))

    # String manipulation
    ##########################################################################

    def filesInStr(self, mid, string, includeRemote=False):
        l = []
        # convert latex first
        model = self.col.models.get(mid)
        string = mungeQA(string, None, None, model, None, self.col)
        # extract filenames
        for reg in self.regexps:
            for (full, fname) in re.findall(reg, string):
                isLocal = not re.match("(https?|ftp)://", fname.lower())
                if isLocal or includeRemote:
                    l.append(fname)
        return l

    def transformNames(self, txt, func):
        for reg in self.regexps:
            txt = re.sub(reg, func, txt)
        return txt

    def strip(self, txt):
        for reg in self.regexps:
            txt = re.sub(reg, "", txt)
        return txt

    def escapeImages(self, string):
        # Feeding webkit unicode can result in it not finding images, so on
        # linux/osx we percent escape the image paths as utf8. On Windows the
        # problem is more complicated - if we percent-escape as utf8 it fixes
        # some images but breaks others. When filenames are normalized by
        # dropbox they become unreadable if we escape them.
        if isWin:
            return string
        def repl(match):
            tag = match.group(1)
            fname = match.group(2)
            if re.match("(https?|ftp)://", fname):
                return tag
            return tag.replace(
                fname, urllib.quote(fname.encode("utf-8")))
        return re.sub(self.regexps[1], repl, string)

    # Rebuilding DB
    ##########################################################################

    def check(self, local=None):
        "Return (missingFiles, unusedFiles)."
        mdir = self.dir()
        # generate card q/a and look through all references
        normrefs = {}
        def norm(s):
            if isinstance(s, unicode):
                return unicodedata.normalize('NFD', s)
            return s
        for f in self.allMedia():
            normrefs[norm(f)] = True
        # loop through directory and find unused & missing media
        unused = []
        if local is None:
            files = os.listdir(mdir)
        else:
            files = local
        for file in files:
            if not local:
                path = os.path.join(mdir, file)
                if not os.path.isfile(path):
                    # ignore directories
                    continue
                if file.startswith("_"):
                    # leading _ says to ignore file
                    continue
            nfile = norm(file)
            if nfile not in normrefs:
                unused.append(file)
            else:
                del normrefs[nfile]
        nohave = normrefs.keys()
        return (nohave, unused)

    def allMedia(self):
        "Return a set of all referenced filenames."
        files = set()
        for mid, flds in self.col.db.execute("select mid, flds from notes"):
            for f in self.filesInStr(mid, flds):
                files.add(f)
        return files

    # Copying on import
    ##########################################################################

    def have(self, fname):
        return os.path.exists(os.path.join(self.dir(), fname))

    # Media syncing - changes and removal
    ##########################################################################

    def hasChanged(self):
        return self.db.scalar("select 1 from log limit 1")

    def removed(self):
        return self.db.list("select * from log where type = ?", MEDIA_REM)

    def syncRemove(self, fnames):
        # remove provided deletions
        for f in fnames:
            if os.path.exists(f):
                os.unlink(f)
            self.db.execute("delete from log where fname = ?", f)
            self.db.execute("delete from media where fname = ?", f)
        # and all locally-logged deletions, as server has acked them
        self.db.execute("delete from log where type = ?", MEDIA_REM)
        self.db.commit()

    # Media syncing - unbundling zip files from server
    ##########################################################################

    def syncAdd(self, zipData):
        "Extract zip data; true if finished."
        f = StringIO(zipData)
        z = zipfile.ZipFile(f, "r")
        finished = False
        meta = None
        media = []
        sizecnt = 0
        # get meta info first
        assert z.getinfo("_meta").file_size < 100000
        meta = json.loads(z.read("_meta"))
        nextUsn = int(z.read("_usn"))
        # then loop through all files
        for i in z.infolist():
            # check for zip bombs
            sizecnt += i.file_size
            assert sizecnt < 100*1024*1024
            if i.filename == "_meta" or i.filename == "_usn":
                # ignore previously-retrieved meta
                continue
            elif i.filename == "_finished":
                # last zip in set
                finished = True
            else:
                data = z.read(i)
                csum = checksum(data)
                name = meta[i.filename]
                # can we store the file on this system?
                if self.illegal(name):
                    continue
                # save file
                open(name, "wb").write(data)
                # update db
                media.append((name, csum, self._mtime(name)))
                # remove entries from local log
                self.db.execute("delete from log where fname = ?", name)
        # update media db and note new starting usn
        if media:
            self.db.executemany(
                "insert or replace into media values (?,?,?)", media)
        self.setUsn(nextUsn) # commits
        # if we have finished adding, we need to record the new folder mtime
        # so that we don't trigger a needless scan
        if finished:
            self.syncMod()
        return finished

    def illegal(self, f):
        if isWin:
            for c in f:
                if c in "<>:\"/\\|?*^":
                    return True
        elif isMac:
            for c in f:
                if c in ":\\/":
                    return True

    # Media syncing - bundling zip files to send to server
    ##########################################################################
    # Because there's no standard filename encoding for zips, and because not
    # all zip clients support retrieving mtime, we store the files as ascii
    # and place a json file in the zip with the necessary information.

    def zipAdded(self):
        "Add files to a zip until over SYNC_ZIP_SIZE. Return zip data."
        f = StringIO()
        z = zipfile.ZipFile(f, "w", compression=zipfile.ZIP_DEFLATED)
        sz = 0
        cnt = 0
        files = {}
        cur = self.db.execute(
            "select fname from log where type = ?", MEDIA_ADD)
        fnames = []
        while 1:
            fname = cur.fetchone()
            if not fname:
                # add a flag so the server knows it can clean up
                z.writestr("_finished", "")
                break
            fname = fname[0]
            fnames.append([fname])
            z.write(fname, str(cnt))
            files[str(cnt)] = fname
            sz += os.path.getsize(fname)
            if sz > SYNC_ZIP_SIZE:
                break
            cnt += 1
        z.writestr("_meta", json.dumps(files))
        z.close()
        return f.getvalue(), fnames

    def forgetAdded(self, fnames):
        if not fnames:
            return
        self.db.executemany("delete from log where fname = ?", fnames)
        self.db.commit()

    # Tracking changes (private)
    ##########################################################################

    def _initDB(self):
        self.db.executescript("""
create table media (fname text primary key, csum text, mod int);
create table meta (dirMod int, usn int); insert into meta values (0, 0);
create table log (fname text primary key, type int);
""")

    def _mtime(self, path):
        return int(os.stat(path).st_mtime)

    def _checksum(self, path):
        return checksum(open(path, "rb").read())

    def usn(self):
        return self.db.scalar("select usn from meta")

    def setUsn(self, usn):
        self.db.execute("update meta set usn = ?", usn)
        self.db.commit()

    def syncMod(self):
        self.db.execute("update meta set dirMod = ?", self._mtime(self.dir()))
        self.db.commit()

    def _changed(self):
        "Return dir mtime if it has changed since the last findChanges()"
        # doesn't track edits, but user can add or remove a file to update
        mod = self.db.scalar("select dirMod from meta")
        mtime = self._mtime(self.dir())
        if mod and mod == mtime:
            return False
        return mtime

    def findChanges(self):
        "Scan the media folder if it's changed, and note any changes."
        if self._changed():
            self._logChanges()

    def _logChanges(self):
        (added, removed) = self._changes()
        log = []
        media = []
        mediaRem = []
        for f in added:
            mt = self._mtime(f)
            media.append((f, self._checksum(f), mt))
            log.append((f, MEDIA_ADD))
        for f in removed:
            mediaRem.append((f,))
            log.append((f, MEDIA_REM))
        # update media db
        self.db.executemany("insert or replace into media values (?,?,?)",
                            media)
        if mediaRem:
            self.db.executemany("delete from media where fname = ?",
                                mediaRem)
        self.db.execute("update meta set dirMod = ?", self._mtime(self.dir()))
        # and logs
        self.db.executemany("insert or replace into log values (?,?)", log)
        self.db.commit()

    def _changes(self):
        self.cache = {}
        for (name, csum, mod) in self.db.execute(
            "select * from media"):
            self.cache[name] = [csum, mod, False]
        added = []
        removed = []
        # loop through on-disk files
        for f in os.listdir(self.dir()):
            # ignore folders and thumbs.db
            if os.path.isdir(f):
                continue
            if f.lower() == "thumbs.db":
                continue
            # and files with invalid chars
            bad = False
            for c in "\0", "/", "\\", ":":
                if c in f:
                    bad = True
                    break
            if bad:
                continue
            # empty files are invalid; clean them up and continue
            if not os.path.getsize(f):
                os.unlink(f)
                continue
            # newly added?
            if f not in self.cache:
                added.append(f)
            else:
                # modified since last time?
                if self._mtime(f) != self.cache[f][1]:
                    # and has different checksum?
                    if self._checksum(f) != self.cache[f][0]:
                        added.append(f)
                # mark as used
                self.cache[f][2] = True
        # look for any entries in the cache that no longer exist on disk
        for (k, v) in self.cache.items():
            if not v[2]:
                removed.append(k)
        return added, removed

    def sanityCheck(self):
        assert not self.db.scalar("select count() from log")
        cnt = self.db.scalar("select count() from media")
        return cnt

########NEW FILE########
__FILENAME__ = models
# -*- coding: utf-8 -*-
# Copyright: Damien Elmes <anki@ichi2.net>
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

import copy, re
from anki.utils import intTime, hexifyID, joinFields, splitFields, ids2str, \
    timestampID, fieldChecksum, json
from anki.lang import _
from anki.consts import *
from anki.hooks import runHook

# Models
##########################################################################

# - careful not to add any lists/dicts/etc here, as they aren't deep copied

defaultModel = {
    'sortf': 0,
    'did': 1,
    'latexPre': """\
\\documentclass[12pt]{article}
\\special{papersize=3in,5in}
\\usepackage{amssymb,amsmath}
\\pagestyle{empty}
\\setlength{\\parindent}{0in}
\\begin{document}
""",
    'latexPost': "\\end{document}",
    'mod': 0,
    'usn': 0,
    'vers': [], # FIXME: remove when other clients have caught up
    'type': MODEL_STD,
    'css': """\
.card {
 font-family: arial;
 font-size: 20px;
 text-align: center;
 color: black;
 background-color: white;
}
"""
}

defaultField = {
    'name': "",
    'ord': None,
    'sticky': False,
    # the following alter editing, and are used as defaults for the
    # template wizard
    'rtl': False,
    'font': "Arial",
    'size': 20,
    # reserved for future use
    'media': [],
}

defaultTemplate = {
    'name': "",
    'ord': None,
    'qfmt': "",
    'afmt': "",
    'did': None,
    'bqfmt': "",
    'bafmt': "",
}

class ModelManager(object):

    # Saving/loading registry
    #############################################################

    def __init__(self, col):
        self.col = col

    def load(self, json_):
        "Load registry from JSON."
        self.changed = False
        self.models = json.loads(json_)

    def save(self, m=None, templates=False):
        "Mark M modified if provided, and schedule registry flush."
        if m and m['id']:
            m['mod'] = intTime()
            m['usn'] = self.col.usn()
            self._updateRequired(m)
            if templates:
                self._syncTemplates(m)
        self.changed = True
        runHook("newModel")

    def flush(self):
        "Flush the registry if any models were changed."
        if self.changed:
            self.col.db.execute("update col set models = ?",
                                 json.dumps(self.models))
            self.changed = False

    # Retrieving and creating models
    #############################################################

    def current(self):
        "Get current model."
        m = self.get(self.col.decks.current().get('mid'))
        if not m:
            m = self.get(self.col.conf['curModel'])
        return m or self.models.values()[0]

    def setCurrent(self, m):
        self.col.conf['curModel'] = m['id']
        self.col.setMod()

    def get(self, id):
        "Get model with ID, or None."
        id = str(id)
        if id in self.models:
            return self.models[id]

    def all(self):
        "Get all models."
        return self.models.values()

    def allNames(self):
        return [m['name'] for m in self.all()]

    def byName(self, name):
        "Get model with NAME."
        for m in self.models.values():
            if m['name'] == name:
                return m

    def new(self, name):
        "Create a new model, save it in the registry, and return it."
        # caller should call save() after modifying
        m = defaultModel.copy()
        m['name'] = name
        m['mod'] = intTime()
        m['flds'] = []
        m['tmpls'] = []
        m['tags'] = []
        m['id'] = None
        return m

    def rem(self, m):
        "Delete model, and all its cards/notes."
        self.col.modSchema()
        current = self.current()['id'] == m['id']
        # delete notes/cards
        self.col.remCards(self.col.db.list("""
select id from cards where nid in (select id from notes where mid = ?)""",
                                      m['id']))
        # then the model
        del self.models[str(m['id'])]
        self.save()
        # GUI should ensure last model is not deleted
        if current:
            self.setCurrent(self.models.values()[0])

    def add(self, m):
        self._setID(m)
        self.update(m)
        self.setCurrent(m)
        self.save(m)

    def update(self, m):
        "Add or update an existing model. Used for syncing and merging."
        self.models[str(m['id'])] = m
        # mark registry changed, but don't bump mod time
        self.save()

    def _setID(self, m):
        while 1:
            id = str(intTime(1000))
            if id not in self.models:
                break
        m['id'] = id

    def have(self, id):
        return str(id) in self.models

    def ids(self):
        return self.models.keys()

    # Tools
    ##################################################

    def nids(self, m):
        "Note ids for M."
        return self.col.db.list(
            "select id from notes where mid = ?", m['id'])

    def useCount(self, m):
        "Number of note using M."
        return self.col.db.scalar(
            "select count() from notes where mid = ?", m['id'])

    # Copying
    ##################################################

    def copy(self, m):
        "Copy, save and return."
        m2 = copy.deepcopy(m)
        m2['name'] = _("%s copy") % m2['name']
        self.add(m2)
        return m2

    # Fields
    ##################################################

    def newField(self, name):
        f = defaultField.copy()
        f['name'] = name
        return f

    def fieldMap(self, m):
        "Mapping of field name -> (ord, field)."
        return dict((f['name'], (f['ord'], f)) for f in m['flds'])

    def fieldNames(self, m):
        return [f['name'] for f in m['flds']]

    def sortIdx(self, m):
        return m['sortf']

    def setSortIdx(self, m, idx):
        assert idx >= 0 and idx < len(m['flds'])
        self.col.modSchema()
        m['sortf'] = idx
        self.col.updateFieldCache(self.nids(m))
        self.save(m)

    def addField(self, m, field):
        # only mod schema if model isn't new
        if m['id']:
            self.col.modSchema()
        m['flds'].append(field)
        self._updateFieldOrds(m)
        self.save(m)
        def add(fields):
            fields.append("")
            return fields
        self._transformFields(m, add)

    def remField(self, m, field):
        self.col.modSchema()
        idx = m['flds'].index(field)
        m['flds'].remove(field)
        if m['sortf'] >= len(m['flds']):
            m['sortf'] -= 1
        self._updateFieldOrds(m)
        def delete(fields):
            del fields[idx]
            return fields
        self._transformFields(m, delete)
        if idx == self.sortIdx(m):
            # need to rebuild
            self.col.updateFieldCache(self.nids(m))
        # saves
        self.renameField(m, field, None)

    def moveField(self, m, field, idx):
        self.col.modSchema()
        oldidx = m['flds'].index(field)
        if oldidx == idx:
            return
        # remember old sort field
        sortf = m['flds'][m['sortf']]
        # move
        m['flds'].remove(field)
        m['flds'].insert(idx, field)
        # restore sort field
        m['sortf'] = m['flds'].index(sortf)
        self._updateFieldOrds(m)
        self.save(m)
        def move(fields, oldidx=oldidx):
            val = fields[oldidx]
            del fields[oldidx]
            fields.insert(idx, val)
            return fields
        self._transformFields(m, move)

    def renameField(self, m, field, newName):
        self.col.modSchema()
        pat = r'{{([:#^/]|[^:#/^}][^:}]*?:|)%s}}'
        def wrap(txt):
            def repl(match):
                return '{{' + match.group(1) + txt +  '}}'
            return repl
        for t in m['tmpls']:
            for fmt in ('qfmt', 'afmt'):
                if newName:
                    t[fmt] = re.sub(
                        pat % re.escape(field['name']), wrap(newName), t[fmt])
                else:
                    t[fmt] = re.sub(
                        pat  % re.escape(field['name']), "", t[fmt])
        field['name'] = newName
        self.save(m)

    def _updateFieldOrds(self, m):
        for c, f in enumerate(m['flds']):
            f['ord'] = c

    def _transformFields(self, m, fn):
        # model hasn't been added yet?
        if not m['id']:
            return
        r = []
        for (id, flds) in self.col.db.execute(
            "select id, flds from notes where mid = ?", m['id']):
            r.append((joinFields(fn(splitFields(flds))),
                      intTime(), self.col.usn(), id))
        self.col.db.executemany(
            "update notes set flds=?,mod=?,usn=? where id = ?", r)

    # Templates
    ##################################################

    def newTemplate(self, name):
        t = defaultTemplate.copy()
        t['name'] = name
        return t

    def addTemplate(self, m, template):
        "Note: should col.genCards() afterwards."
        if m['id']:
            self.col.modSchema()
        m['tmpls'].append(template)
        self._updateTemplOrds(m)
        self.save(m)

    def remTemplate(self, m, template):
        "False if removing template would leave orphan notes."
        assert len(m['tmpls']) > 1
        # find cards using this template
        ord = m['tmpls'].index(template)
        cids = self.col.db.list("""
select c.id from cards c, notes f where c.nid=f.id and mid = ? and ord = ?""",
                                 m['id'], ord)
        # all notes with this template must have at least two cards, or we
        # could end up creating orphaned notes
        if self.col.db.scalar("""
select nid, count() from cards where
nid in (select nid from cards where id in %s)
group by nid
having count() < 2
limit 1""" % ids2str(cids)):
            return False
        # ok to proceed; remove cards
        self.col.modSchema()
        self.col.remCards(cids)
        # shift ordinals
        self.col.db.execute("""
update cards set ord = ord - 1, usn = ?, mod = ?
 where nid in (select id from notes where mid = ?) and ord > ?""",
                             self.col.usn(), intTime(), m['id'], ord)
        m['tmpls'].remove(template)
        self._updateTemplOrds(m)
        self.save(m)
        return True

    def _updateTemplOrds(self, m):
        for c, t in enumerate(m['tmpls']):
            t['ord'] = c

    def moveTemplate(self, m, template, idx):
        oldidx = m['tmpls'].index(template)
        if oldidx == idx:
            return
        oldidxs = dict((id(t), t['ord']) for t in m['tmpls'])
        m['tmpls'].remove(template)
        m['tmpls'].insert(idx, template)
        self._updateTemplOrds(m)
        # generate change map
        map = []
        for t in m['tmpls']:
            map.append("when ord = %d then %d" % (oldidxs[id(t)], t['ord']))
        # apply
        self.save(m)
        self.col.db.execute("""
update cards set ord = (case %s end),usn=?,mod=? where nid in (
select id from notes where mid = ?)""" % " ".join(map),
                             self.col.usn(), intTime(), m['id'])

    def _syncTemplates(self, m):
        rem = self.col.genCards(self.nids(m))

    # Model changing
    ##########################################################################
    # - maps are ord->ord, and there should not be duplicate targets
    # - newModel should be self if model is not changing

    def change(self, m, nids, newModel, fmap, cmap):
        self.col.modSchema()
        assert newModel['id'] == m['id'] or (fmap and cmap)
        if fmap:
            self._changeNotes(nids, newModel, fmap)
        if cmap:
            self._changeCards(nids, m, newModel, cmap)
        self.col.genCards(nids)

    def _changeNotes(self, nids, newModel, map):
        d = []
        nfields = len(newModel['flds'])
        for (nid, flds) in self.col.db.execute(
            "select id, flds from notes where id in "+ids2str(nids)):
            newflds = {}
            flds = splitFields(flds)
            for old, new in map.items():
                newflds[new] = flds[old]
            flds = []
            for c in range(nfields):
                flds.append(newflds.get(c, ""))
            flds = joinFields(flds)
            d.append(dict(nid=nid, flds=flds, mid=newModel['id'],
                      m=intTime(),u=self.col.usn()))
        self.col.db.executemany(
            "update notes set flds=:flds,mid=:mid,mod=:m,usn=:u where id = :nid", d)
        self.col.updateFieldCache(nids)

    def _changeCards(self, nids, oldModel, newModel, map):
        d = []
        deleted = []
        for (cid, ord) in self.col.db.execute(
            "select id, ord from cards where nid in "+ids2str(nids)):
            # if the src model is a cloze, we ignore the map, as the gui
            # doesn't currently support mapping them
            if oldModel['type'] == MODEL_CLOZE:
                new = ord
                if newModel['type'] != MODEL_CLOZE:
                    # if we're mapping to a regular note, we need to check if
                    # the destination ord is valid
                    if len(newModel['tmpls']) <= ord:
                        new = None
            else:
                # mapping from a regular note, so the map should be valid
                new = map[ord]
            if new is not None:
                d.append(dict(
                    cid=cid,new=new,u=self.col.usn(),m=intTime()))
            else:
                deleted.append(cid)
        self.col.db.executemany(
            "update cards set ord=:new,usn=:u,mod=:m where id=:cid",
            d)
        self.col.remCards(deleted)

    # Schema hash
    ##########################################################################

    def scmhash(self, m):
        "Return a hash of the schema, to see if models are compatible."
        s = ""
        for f in m['flds']:
            s += f['name']
        for t in m['tmpls']:
            s += t['name']
            s += t['qfmt']
            s += t['afmt']
        return fieldChecksum(s)

    # Required field/text cache
    ##########################################################################

    def _updateRequired(self, m):
        if m['type'] == MODEL_CLOZE:
            # nothing to do
            return
        req = []
        flds = [f['name'] for f in m['flds']]
        for t in m['tmpls']:
            ret = self._reqForTemplate(m, flds, t)
            req.append((t['ord'], ret[0], ret[1]))
        m['req'] = req

    def _reqForTemplate(self, m, flds, t):
        a = []
        b = []
        for f in flds:
            a.append("ankiflag")
            b.append("")
        data = [1, 1, m['id'], 1, t['ord'], "", joinFields(a)]
        full = self.col._renderQA(data)['q']
        data = [1, 1, m['id'], 1, t['ord'], "", joinFields(b)]
        empty = self.col._renderQA(data)['q']
        # if full and empty are the same, the template is invalid and there is
        # no way to satisfy it
        if full == empty:
            return "none", [], []
        type = 'all'
        req = []
        for i in range(len(flds)):
            tmp = a[:]
            tmp[i] = ""
            data[6] = joinFields(tmp)
            # if no field content appeared, field is required
            if "ankiflag" not in self.col._renderQA(data)['q']:
                req.append(i)
        if req:
            return type, req
        # if there are no required fields, switch to any mode
        type = 'any'
        req = []
        for i in range(len(flds)):
            tmp = b[:]
            tmp[i] = "1"
            data[6] = joinFields(tmp)
            # if not the same as empty, this field can make the card non-blank
            if self.col._renderQA(data)['q'] != empty:
                req.append(i)
        return type, req

    def availOrds(self, m, flds):
        "Given a joined field string, return available template ordinals."
        if m['type'] == MODEL_CLOZE:
            return self._availClozeOrds(m, flds)
        fields = {}
        for c, f in enumerate(splitFields(flds)):
            fields[c] = f.strip()
        avail = []
        for ord, type, req in m['req']:
            # unsatisfiable template
            if type == "none":
                continue
            # AND requirement?
            elif type == "all":
                ok = True
                for idx in req:
                    if not fields[idx]:
                        # missing and was required
                        ok = False
                        break
                if not ok:
                    continue
            # OR requirement?
            elif type == "any":
                ok = False
                for idx in req:
                    if fields[idx]:
                        ok = True
                        break
                if not ok:
                    continue
            avail.append(ord)
        return avail

    def _availClozeOrds(self, m, flds, allowEmpty=True):
        sflds = splitFields(flds)
        map = self.fieldMap(m)
        ords = set()
        for fname in re.findall("{{cloze:(.+?)}}", m['tmpls'][0]['qfmt']):
            if fname not in map:
                continue
            ord = map[fname][0]
            ords.update([int(m)-1 for m in re.findall(
                "{{c(\d+)::.+?}}", sflds[ord])])
        if -1 in ords:
            ords.remove(-1)
        if not ords and allowEmpty:
            # empty clozes use first ord
            return [0]
        return list(ords)

    # Sync handling
    ##########################################################################

    def beforeUpload(self):
        for m in self.all():
            m['usn'] = 0
        self.save()

########NEW FILE########
__FILENAME__ = notes
# -*- coding: utf-8 -*-
# Copyright: Damien Elmes <anki@ichi2.net>
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

import time
from anki.errors import AnkiError
from anki.utils import fieldChecksum, intTime, \
    joinFields, splitFields, ids2str, stripHTML, timestampID, guid64

class Note(object):

    def __init__(self, col, model=None, id=None):
        assert not (model and id)
        self.col = col
        if id:
            self.id = id
            self.load()
        else:
            self.id = timestampID(col.db, "notes")
            self.guid = guid64()
            self._model = model
            self.mid = model['id']
            self.tags = []
            self.fields = [""] * len(self._model['flds'])
            self.flags = 0
            self.data = ""
            self._fmap = self.col.models.fieldMap(self._model)
            self.scm = self.col.scm

    def load(self):
        (self.guid,
         self.mid,
         self.mod,
         self.usn,
         self.tags,
         self.fields,
         self.flags,
         self.data) = self.col.db.first("""
select guid, mid, mod, usn, tags, flds, flags, data
from notes where id = ?""", self.id)
        self.fields = splitFields(self.fields)
        self.tags = self.col.tags.split(self.tags)
        self._model = self.col.models.get(self.mid)
        self._fmap = self.col.models.fieldMap(self._model)
        self.scm = self.col.scm

    def flush(self, mod=None):
        assert self.scm == self.col.scm
        self._preFlush()
        self.mod = mod if mod else intTime()
        self.usn = self.col.usn()
        sfld = stripHTML(self.fields[self.col.models.sortIdx(self._model)])
        tags = self.stringTags()
        csum = fieldChecksum(self.fields[0])
        res = self.col.db.execute("""
insert or replace into notes values (?,?,?,?,?,?,?,?,?,?,?)""",
                            self.id, self.guid, self.mid,
                            self.mod, self.usn, tags,
                            self.joinedFields(), sfld, csum, self.flags,
                            self.data)
        self.col.tags.register(self.tags)
        self._postFlush()

    def joinedFields(self):
        return joinFields(self.fields)

    def cards(self):
        return [self.col.getCard(id) for id in self.col.db.list(
            "select id from cards where nid = ? order by ord", self.id)]

    def model(self):
        return self._model

    # Dict interface
    ##################################################

    def keys(self):
        return self._fmap.keys()

    def values(self):
        return self.fields

    def items(self):
        return [(f['name'], self.fields[ord])
                for ord, f in sorted(self._fmap.values())]

    def _fieldOrd(self, key):
        try:
            return self._fmap[key][0]
        except:
            raise KeyError(key)

    def __getitem__(self, key):
        return self.fields[self._fieldOrd(key)]

    def __setitem__(self, key, value):
        self.fields[self._fieldOrd(key)] = value

    def __contains__(self, key):
        return key in self._fmap.keys()

    # Tags
    ##################################################

    def hasTag(self, tag):
        return self.col.tags.inList(tag, self.tags)

    def stringTags(self):
        return self.col.tags.join(self.col.tags.canonify(self.tags))

    def setTagsFromStr(self, str):
        self.tags = self.col.tags.split(str)

    def delTag(self, tag):
        rem = []
        for t in self.tags:
            if t.lower() == tag.lower():
                rem.append(t)
        for r in rem:
            self.tags.remove(r)

    def addTag(self, tag):
        # duplicates will be stripped on save
        self.tags.append(tag)

    # Unique/duplicate check
    ##################################################

    def dupeOrEmpty(self):
        "1 if first is empty; 2 if first is a duplicate, False otherwise."
        val = self.fields[0]
        if not val.strip():
            return 1
        csum = fieldChecksum(val)
        # find any matching csums and compare
        for flds in self.col.db.list(
            "select flds from notes where csum = ? and id != ? and mid = ?",
            csum, self.id or 0, self.mid):
            if splitFields(flds)[0] == self.fields[0]:
                return 2
        return False

    # Flushing cloze notes
    ##################################################

    def _preFlush(self):
        # have we been added yet?
        self.newlyAdded = not self.col.db.scalar(
            "select 1 from cards where nid = ?", self.id)

    def _postFlush(self):
        # generate missing cards
        if not self.newlyAdded:
            rem = self.col.genCards([self.id])
            # popping up a dialog while editing is confusing; instead we can
            # document that the user should open the templates window to
            # garbage collect empty cards
            #self.col.remEmptyCards(ids)

########NEW FILE########
__FILENAME__ = sched
# -*- coding: utf-8 -*-
# Copyright: Damien Elmes <anki@ichi2.net>
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

import time, datetime, random, itertools, math
from operator import itemgetter
from heapq import *
#from anki.cards import Card
from anki.utils import ids2str, intTime, fmtTimeSpan
from anki.lang import _, ngettext
from anki.consts import *
from anki.hooks import runHook

# queue types: 0=new/cram, 1=lrn, 2=rev, 3=day lrn, -1=suspended, -2=buried
# revlog types: 0=lrn, 1=rev, 2=relrn, 3=cram
# positive revlog intervals are in days (rev), negative in seconds (lrn)

class Scheduler(object):
    name = "std"
    haveCustomStudy = True

    def __init__(self, col):
        self.col = col
        self.queueLimit = 50
        self.reportLimit = 1000
        self.reps = 0
        self._haveQueues = False
        self._updateCutoff()

    def getCard(self):
        "Pop the next card from the queue. None if finished."
        self._checkDay()
        if not self._haveQueues:
            self.reset()
        card = self._getCard()
        if card:
            self.reps += 1
            card.startTimer()
            return card

    def reset(self):
        deck = self.col.decks.current()
        self._updateCutoff()
        self._resetLrn()
        self._resetRev()
        self._resetNew()
        self._haveQueues = True

    def answerCard(self, card, ease):
        assert ease >= 1 and ease <= 4
        self.col.markReview(card)
        card.reps += 1
        card.wasNew = card.queue == 0
        if card.wasNew:
            # came from the new queue, move to learning
            card.queue = 1
            # if it was a new card, it's now a learning card
            if card.type == 0:
                card.type = 1
            # init reps to graduation
            card.left = self._startingLeft(card)
            # dynamic?
            if card.odid and card.type == 2:
                if self._resched(card):
                    # reviews get their ivl boosted on first sight
                    card.ivl = self._dynIvlBoost(card)
                    card.odue = self.today + card.ivl
            self._updateStats(card, 'new')
        if card.queue in (1, 3):
            self._answerLrnCard(card, ease)
            if not card.wasNew:
                self._updateStats(card, 'lrn')
        elif card.queue == 2:
            self._answerRevCard(card, ease)
            self._updateStats(card, 'rev')
        else:
            raise Exception("Invalid queue")
        self._updateStats(card, 'time', card.timeTaken())
        card.mod = intTime()
        card.usn = self.col.usn()
        card.flushSched()

    def counts(self, card=None):
        counts = [self.newCount, self.lrnCount, self.revCount]
        if card:
            idx = self.countIdx(card)
            if idx == 1:
                counts[1] += card.left/1000
            else:
                counts[idx] += 1
        return tuple(counts)

    def dueForecast(self, days=7):
        "Return counts over next DAYS. Includes today."
        daysd = dict(self.col.db.all("""
select due, count() from cards
where did in %s and queue = 2
and due between ? and ?
group by due
order by due""" % self._deckLimit(),
                            self.today,
                            self.today+days-1))
        for d in range(days):
            d = self.today+d
            if d not in daysd:
                daysd[d] = 0
        # return in sorted order
        ret = [x[1] for x in sorted(daysd.items())]
        return ret

    def countIdx(self, card):
        if card.queue == 3:
            return 1
        return card.queue

    def answerButtons(self, card):
        if card.odue:
            # normal review in dyn deck?
            if card.odid and card.queue == 2:
                return 4
            conf = self._lapseConf(card)
            if card.type == 0 or len(conf['delays']) > 1:
                return 3
            return 2
        elif card.queue == 2:
            return 4
        else:
            return 3

    def unburyCards(self):
        "Unbury cards when closing."
        mod = self.col.db.mod
        self.col.db.execute(
            "update cards set queue = type where queue = -2")
        self.col.db.mod = mod

    # Rev/lrn/time daily stats
    ##########################################################################

    def _updateStats(self, card, type, cnt=1):
        key = type+"Today"
        for g in ([self.col.decks.get(card.did)] +
                  self.col.decks.parents(card.did)):
            # add
            g[key][1] += cnt
            self.col.decks.save(g)

    def extendLimits(self, new, rev):
        cur = self.col.decks.current()
        parents = self.col.decks.parents(cur['id'])
        children = [self.col.decks.get(did) for (name, did) in
                    self.col.decks.children(cur['id'])]
        for g in [cur] + parents + children:
            # add
            g['newToday'][1] -= new
            g['revToday'][1] -= rev
            self.col.decks.save(g)

    def _walkingCount(self, limFn=None, cntFn=None):
        tot = 0
        pcounts = {}
        # for each of the active decks
        for did in self.col.decks.active():
            # early alphas were setting the active ids as a str
            did = int(did)
            # get the individual deck's limit
            lim = limFn(self.col.decks.get(did))
            if not lim:
                continue
            # check the parents
            parents = self.col.decks.parents(did)
            for p in parents:
                # add if missing
                if p['id'] not in pcounts:
                    pcounts[p['id']] = limFn(p)
                # take minimum of child and parent
                lim = min(pcounts[p['id']], lim)
            # see how many cards we actually have
            cnt = cntFn(did, lim)
            # if non-zero, decrement from parent counts
            for p in parents:
                pcounts[p['id']] -= cnt
            # we may also be a parent
            pcounts[did] = lim - cnt
            # and add to running total
            tot += cnt
        return tot

    # Deck list
    ##########################################################################

    def deckDueList(self):
        "Returns [deckname, did, rev, lrn, new]"
        self._checkDay()
        self.col.decks.recoverOrphans()
        self.unburyCards()
        decks = self.col.decks.all()
        decks.sort(key=itemgetter('name'))
        lims = {}
        data = []
        def parent(name):
            parts = name.split("::")
            if len(parts) < 2:
                return None
            parts = parts[:-1]
            return "::".join(parts)
        for deck in decks:
            # if we've already seen the exact same deck name, remove the
            # invalid duplicate and reload
            if deck['name'] in lims:
                self.col.decks.rem(deck['id'], cardsToo=False, childrenToo=True)
                return self.deckDueList()
            p = parent(deck['name'])
            # new
            nlim = self._deckNewLimitSingle(deck)
            if p:
                if p not in lims:
                    # if parent was missing, this deck is invalid, and we
                    # need to reload the deck list
                    self.col.decks.rem(deck['id'], cardsToo=False, childrenToo=True)
                    return self.deckDueList()
                nlim = min(nlim, lims[p][0])
            new = self._newForDeck(deck['id'], nlim)
            # learning
            lrn = self._lrnForDeck(deck['id'])
            # reviews
            rlim = self._deckRevLimitSingle(deck)
            if p:
                rlim = min(rlim, lims[p][1])
            rev = self._revForDeck(deck['id'], rlim)
            # save to list
            data.append([deck['name'], deck['id'], rev, lrn, new])
            # add deck as a parent
            lims[deck['name']] = [nlim, rlim]
        return data

    def deckDueTree(self):
        return self._groupChildren(self.deckDueList())

    def _groupChildren(self, grps):
        # first, split the group names into components
        for g in grps:
            g[0] = g[0].split("::")
        # and sort based on those components
        grps.sort(key=itemgetter(0))
        # then run main function
        return self._groupChildrenMain(grps)

    def _groupChildrenMain(self, grps):
        tree = []
        # group and recurse
        def key(grp):
            return grp[0][0]
        for (head, tail) in itertools.groupby(grps, key=key):
            tail = list(tail)
            did = None
            rev = 0
            new = 0
            lrn = 0
            children = []
            for c in tail:
                if len(c[0]) == 1:
                    # current node
                    did = c[1]
                    rev += c[2]
                    lrn += c[3]
                    new += c[4]
                else:
                    # set new string to tail
                    c[0] = c[0][1:]
                    children.append(c)
            children = self._groupChildrenMain(children)
            # tally up children counts
            for ch in children:
                rev += ch[2]
                lrn += ch[3]
                new += ch[4]
            # limit the counts to the deck's limits
            conf = self.col.decks.confForDid(did)
            deck = self.col.decks.get(did)
            if not conf['dyn']:
                rev = max(0, min(rev, conf['rev']['perDay']-deck['revToday'][1]))
                new = max(0, min(new, conf['new']['perDay']-deck['newToday'][1]))
            tree.append((head, did, rev, lrn, new, children))
        return tuple(tree)

    # Getting the next card
    ##########################################################################

    def _getCard(self):
        "Return the next due card id, or None."
        # learning card due?
        c = self._getLrnCard()
        if c:
            return c
        # new first, or time for one?
        if self._timeForNewCard():
            return self._getNewCard()
        # card due for review?
        c = self._getRevCard()
        if c:
            return c
        # day learning card due?
        c = self._getLrnDayCard()
        if c:
            return c
        # new cards left?
        c = self._getNewCard()
        if c:
            return c
        # collapse or finish
        return self._getLrnCard(collapse=True)

    # New cards
    ##########################################################################

    def _resetNewCount(self):
        cntFn = lambda did, lim: self.col.db.scalar("""
select count() from (select 1 from cards where
did = ? and queue = 0 limit ?)""", did, lim)
        self.newCount = self._walkingCount(self._deckNewLimitSingle, cntFn)

    def _resetNew(self):
        self._resetNewCount()
        self._newDids = self.col.decks.active()[:]
        self._newQueue = []
        self._updateNewCardRatio()

    def _fillNew(self):
        if self._newQueue:
            return True
        if not self.newCount:
            return False
        while self._newDids:
            did = self._newDids[0]
            lim = min(self.queueLimit, self._deckNewLimit(did))
            if lim:
                # fill the queue with the current did
                self._newQueue = self.col.db.all("""
select id, due from cards where did = ? and queue = 0 limit ?""", did, lim)
                if self._newQueue:
                    self._newQueue.reverse()
                    return True
            # nothing left in the deck; move to next
            self._newDids.pop(0)

    def _getNewCard(self):
        if not self._fillNew():
            return
        (id, due) = self._newQueue.pop()
        # move any siblings to the end?
        conf = self.col.decks.confForDid(self._newDids[0])
        if conf['dyn'] or conf['new']['separate']:
            n = len(self._newQueue)
            while self._newQueue and self._newQueue[-1][1] == due:
                self._newQueue.insert(0, self._newQueue.pop())
                n -= 1
                if not n:
                    # we only have one note in the queue; stop rotating
                    break
        self.newCount -= 1
        return self.col.getCard(id)

    def _updateNewCardRatio(self):
        if self.col.conf['newSpread'] == NEW_CARDS_DISTRIBUTE:
            if self.newCount:
                self.newCardModulus = (
                    (self.newCount + self.revCount) / self.newCount)
                # if there are cards to review, ensure modulo >= 2
                if self.revCount:
                    self.newCardModulus = max(2, self.newCardModulus)
                return
        self.newCardModulus = 0

    def _timeForNewCard(self):
        "True if it's time to display a new card when distributing."
        if not self.newCount:
            return False
        if self.col.conf['newSpread'] == NEW_CARDS_LAST:
            return False
        elif self.col.conf['newSpread'] == NEW_CARDS_FIRST:
            return True
        elif self.newCardModulus:
            return self.reps and self.reps % self.newCardModulus == 0

    def _deckNewLimit(self, did, fn=None):
        if not fn:
            fn = self._deckNewLimitSingle
        sel = self.col.decks.get(did)
        lim = -1
        # for the deck and each of its parents
        for g in [sel] + self.col.decks.parents(did):
            rem = fn(g)
            if lim == -1:
                lim = rem
            else:
                lim = min(rem, lim)
        return lim

    def _newForDeck(self, did, lim):
        "New count for a single deck."
        if not lim:
            return 0
        lim = min(lim, self.reportLimit)
        return self.col.db.scalar("""
select count() from
(select 1 from cards where did = ? and queue = 0 limit ?)""", did, lim)

    def _deckNewLimitSingle(self, g):
        "Limit for deck without parent limits."
        if g['dyn']:
            return self.reportLimit
        c = self.col.decks.confForDid(g['id'])
        return max(0, c['new']['perDay'] - g['newToday'][1])

    def totalNewForCurrentDeck(self):
        return self.col.db.scalar(
            """
select count() from cards where id in (
select id from cards where did in %s and queue = 0 limit ?)"""
            % ids2str(self.col.decks.active()), self.reportLimit)

    # Learning queues
    ##########################################################################

    def _resetLrnCount(self):
        # sub-day
        self.lrnCount = self.col.db.scalar("""
select sum(left/1000) from (select left from cards where
did in %s and queue = 1 and due < ? limit %d)""" % (
            self._deckLimit(), self.reportLimit),
            self.dayCutoff) or 0
        # day
        self.lrnCount += self.col.db.scalar("""
select count() from cards where did in %s and queue = 3
and due <= ? limit %d""" % (self._deckLimit(), self.reportLimit),
                                            self.today)

    def _resetLrn(self):
        self._resetLrnCount()
        self._lrnQueue = []
        self._lrnDayQueue = []
        self._lrnDids = self.col.decks.active()[:]

    # sub-day learning
    def _fillLrn(self):
        if not self.lrnCount:
            return False
        if self._lrnQueue:
            return True
        self._lrnQueue = self.col.db.all("""
select due, id from cards where
did in %s and queue = 1 and due < :lim
limit %d""" % (self._deckLimit(), self.reportLimit), lim=self.dayCutoff)
        # as it arrives sorted by did first, we need to sort it
        self._lrnQueue.sort()
        return self._lrnQueue

    def _getLrnCard(self, collapse=False):
        if self._fillLrn():
            cutoff = time.time()
            if collapse:
                cutoff += self.col.conf['collapseTime']
            if self._lrnQueue[0][0] < cutoff:
                id = heappop(self._lrnQueue)[1]
                card = self.col.getCard(id)
                self.lrnCount -= card.left/1000
                return card

    # daily learning
    def _fillLrnDay(self):
        if not self.lrnCount:
            return False
        if self._lrnDayQueue:
            return True
        while self._lrnDids:
            did = self._lrnDids[0]
            # fill the queue with the current did
            self._lrnDayQueue = self.col.db.list("""
select id from cards where
did = ? and queue = 3 and due <= ? limit ?""",
                                    did, self.today, self.queueLimit)
            if self._lrnDayQueue:
                # order
                r = random.Random()
                r.seed(self.today)
                r.shuffle(self._lrnDayQueue)
                # is the current did empty?
                if len(self._lrnDayQueue) < self.queueLimit:
                    self._lrnDids.pop(0)
                return True
            # nothing left in the deck; move to next
            self._lrnDids.pop(0)

    def _getLrnDayCard(self):
        if self._fillLrnDay():
            self.lrnCount -= 1
            return self.col.getCard(self._lrnDayQueue.pop())

    def _answerLrnCard(self, card, ease):
        # ease 1=no, 2=yes, 3=remove
        conf = self._lrnConf(card)
        if card.odid and not card.wasNew:
            type = 3
        elif card.type == 2:
            type = 2
        else:
            type = 0
        leaving = False
        # lrnCount was decremented once when card was fetched
        lastLeft = card.left
        # immediate graduate?
        if ease == 3:
            self._rescheduleAsRev(card, conf, True)
            leaving = True
        # graduation time?
        elif ease == 2 and (card.left%1000)-1 <= 0:
            self._rescheduleAsRev(card, conf, False)
            leaving = True
        else:
            # one step towards graduation
            if ease == 2:
                # decrement real left count and recalculate left today
                left = (card.left % 1000) - 1
                card.left = self._leftToday(conf['delays'], left)*1000 + left
            # failed
            else:
                card.left = self._startingLeft(card)
                if card.odid:
                    resched = self._resched(card)
                    if 'mult' in conf and resched:
                        # review that's lapsed
                        card.ivl = max(1, card.ivl*conf['mult'])
                    else:
                        # new card; no ivl adjustment
                        pass
                    if resched:
                        card.odue = self.today + 1
            delay = self._delayForGrade(conf, card.left)
            if card.due < time.time():
                # not collapsed; add some randomness
                delay *= random.uniform(1, 1.25)
            card.due = int(time.time() + delay)
            # due today?
            if card.due < self.dayCutoff:
                self.lrnCount += card.left/1000
                # if the queue is not empty and there's nothing else to do, make
                # sure we don't put it at the head of the queue and end up showing
                # it twice in a row
                card.queue = 1
                if self._lrnQueue and not self.revCount and not self.newCount:
                    smallestDue = self._lrnQueue[0][0]
                    card.due = max(card.due, smallestDue+1)
                heappush(self._lrnQueue, (card.due, card.id))
            else:
                # the card is due in one or more days, so we need to use the
                # day learn queue
                ahead = ((card.due - self.dayCutoff) / 86400) + 1
                card.due = self.today + ahead
                card.queue = 3
        self._logLrn(card, ease, conf, leaving, type, lastLeft)

    def _delayForGrade(self, conf, left):
        left = left % 1000
        try:
            delay = conf['delays'][-left]
        except IndexError:
            if conf['delays']:
                delay = conf['delays'][0]
            else:
                # user deleted final step; use dummy value
                delay = 1
        return delay*60

    def _lrnConf(self, card):
        if card.type == 2:
            return self._lapseConf(card)
        else:
            return self._newConf(card)

    def _rescheduleAsRev(self, card, conf, early):
        lapse = card.type == 2
        if lapse:
            if self._resched(card):
                card.due = max(self.today+1, card.odue)
            else:
                card.due = card.odue
            card.odue = 0
        else:
            self._rescheduleNew(card, conf, early)
        card.queue = 2
        card.type = 2
        # if we were dynamic, graduating means moving back to the old deck
        resched = self._resched(card)
        if card.odid:
            card.did = card.odid
            card.odue = 0
            card.odid = 0
            # if rescheduling is off, it needs to be set back to a new card
            if not resched and not lapse:
                card.queue = card.type = 0
                card.due = self.col.nextID("pos")

    def _startingLeft(self, card):
        if card.type == 2:
            conf = self._lapseConf(card)
        else:
            conf = self._lrnConf(card)
        tot = len(conf['delays'])
        tod = self._leftToday(conf['delays'], tot)
        return tot + tod*1000

    def _leftToday(self, delays, left, now=None):
        "The number of steps that can be completed by the day cutoff."
        if not now:
            now = intTime()
        delays = delays[-left:]
        ok = 0
        for i in range(len(delays)):
            now += delays[i]*60
            if now > self.dayCutoff:
                break
            ok = i
        return ok+1

    def _graduatingIvl(self, card, conf, early, adj=True):
        if card.type == 2:
            # lapsed card being relearnt
            if card.odid:
                if conf['resched']:
                    return self._dynIvlBoost(card)
            return card.ivl
        if not early:
            # graduate
            ideal =  conf['ints'][0]
        else:
            # early remove
            ideal = conf['ints'][1]
        if adj:
            return self._adjRevIvl(card, ideal)
        else:
            return ideal

    def _rescheduleNew(self, card, conf, early):
        "Reschedule a new card that's graduated for the first time."
        card.ivl = self._graduatingIvl(card, conf, early)
        card.due = self.today+card.ivl
        card.factor = conf['initialFactor']

    def _logLrn(self, card, ease, conf, leaving, type, lastLeft):
        lastIvl = -(self._delayForGrade(conf, lastLeft))
        ivl = card.ivl if leaving else -(self._delayForGrade(conf, card.left))
        def log():
            self.col.db.execute(
                "insert into revlog values (?,?,?,?,?,?,?,?,?)",
                int(time.time()*1000), card.id, self.col.usn(), ease,
                ivl, lastIvl, card.factor, card.timeTaken(), type)
        try:
            log()
        except:
            # duplicate pk; retry in 10ms
            time.sleep(0.01)
            log()

    def removeLrn(self, ids=None):
        "Remove cards from the learning queues."
        if ids:
            extra = " and id in "+ids2str(ids)
        else:
            # benchmarks indicate it's about 10x faster to search all decks
            # with the index than scan the table
            extra = " and did in "+ids2str(self.col.decks.allIds())
        # review cards in relearning
        self.col.db.execute("""
update cards set
due = odue, queue = 2, mod = %d, usn = %d, odue = 0
where queue in (1,3) and type = 2
%s
""" % (intTime(), self.col.usn(), extra))
        # new cards in learning
        self.forgetCards(self.col.db.list(
            "select id from cards where queue in (1,3) %s" % extra))

    def _lrnForDeck(self, did):
        cnt = self.col.db.scalar(
            """
select sum(left/1000) from
(select left from cards where did = ? and queue = 1 and due < ? limit ?)""",
            did, intTime() + self.col.conf['collapseTime'], self.reportLimit) or 0
        return cnt + self.col.db.scalar(
            """
select count() from
(select 1 from cards where did = ? and queue = 3
and due <= ? limit ?)""",
            did, self.today, self.reportLimit)

    # Reviews
    ##########################################################################

    def _deckRevLimit(self, did):
        return self._deckNewLimit(did, self._deckRevLimitSingle)

    def _deckRevLimitSingle(self, d):
        if d['dyn']:
            return self.reportLimit
        c = self.col.decks.confForDid(d['id'])
        return max(0, c['rev']['perDay'] - d['revToday'][1])

    def _revForDeck(self, did, lim):
        lim = min(lim, self.reportLimit)
        return self.col.db.scalar(
            """
select count() from
(select 1 from cards where did = ? and queue = 2
and due <= ? limit ?)""",
            did, self.today, lim)

    def _resetRevCount(self):
        def cntFn(did, lim):
            return self.col.db.scalar("""
select count() from (select id from cards where
did = ? and queue = 2 and due <= ? limit %d)""" % lim,
                                      did, self.today)
        self.revCount = self._walkingCount(
            self._deckRevLimitSingle, cntFn)

    def _resetRev(self):
        self._resetRevCount()
        self._revQueue = []
        self._revDids = self.col.decks.active()[:]

    def _fillRev(self):
        if self._revQueue:
            return True
        if not self.revCount:
            return False
        while self._revDids:
            did = self._revDids[0]
            lim = min(self.queueLimit, self._deckRevLimit(did))
            if lim:
                # fill the queue with the current did
                self._revQueue = self.col.db.list("""
select id from cards where
did = ? and queue = 2 and due <= ? limit ?""",
                                                  did, self.today, lim)
                if self._revQueue:
                    # ordering
                    if self.col.decks.get(did)['dyn']:
                        # dynamic decks need due order preserved
                        self._revQueue.reverse()
                    else:
                        # random order for regular reviews
                        r = random.Random()
                        r.seed(self.today)
                        r.shuffle(self._revQueue)
                    # is the current did empty?
                    if len(self._revQueue) < lim:
                        self._revDids.pop(0)
                    return True
            # nothing left in the deck; move to next
            self._revDids.pop(0)

    def _getRevCard(self):
        if self._fillRev():
            self.revCount -= 1
            return self.col.getCard(self._revQueue.pop())

    def totalRevForCurrentDeck(self):
        return self.col.db.scalar(
            """
select count() from cards where id in (
select id from cards where did in %s and queue = 2 and due <= ? limit ?)"""
            % ids2str(self.col.decks.active()), self.today, self.reportLimit)

    # Answering a review card
    ##########################################################################

    def _answerRevCard(self, card, ease):
        delay = 0
        if ease == 1:
            delay = self._rescheduleLapse(card)
        else:
            self._rescheduleRev(card, ease)
        self._logRev(card, ease, delay)

    def _rescheduleLapse(self, card):
        conf = self._lapseConf(card)
        card.lastIvl = card.ivl
        if self._resched(card):
            card.lapses += 1
            card.ivl = self._nextLapseIvl(card, conf)
            card.factor = max(1300, card.factor-200)
            card.due = self.today + card.ivl
            # if it's a filtered deck, update odue as well
            if card.odid:
                card.odue = card.due
        # if suspended as a leech, nothing to do
        delay = 0
        if self._checkLeech(card, conf) and card.queue == -1:
            return delay
        # if no relearning steps, nothing to do
        if not conf['delays']:
            return delay
        # record rev due date for later
        if not card.odue:
            card.odue = card.due
        delay = self._delayForGrade(conf, 0)
        card.due = int(delay + time.time())
        card.left = self._startingLeft(card)
        # queue 1
        if card.due < self.dayCutoff:
            self.lrnCount += card.left/1000
            card.queue = 1
            heappush(self._lrnQueue, (card.due, card.id))
        else:
            # day learn queue
            ahead = ((card.due - self.dayCutoff) / 86400) + 1
            card.due = self.today + ahead
            card.queue = 3
        return delay

    def _nextLapseIvl(self, card, conf):
        return max(conf['minInt'], int(card.ivl*conf['mult']))

    def _rescheduleRev(self, card, ease):
        # update interval
        card.lastIvl = card.ivl
        if self._resched(card):
            self._updateRevIvl(card, ease)
            # then the rest
            card.factor = max(1300, card.factor+[-150, 0, 150][ease-2])
            card.due = self.today + card.ivl
        else:
            card.due = card.odue
        if card.odid:
            card.did = card.odid
            card.odid = 0
            card.odue = 0

    def _logRev(self, card, ease, delay):
        def log():
            self.col.db.execute(
                "insert into revlog values (?,?,?,?,?,?,?,?,?)",
                int(time.time()*1000), card.id, self.col.usn(), ease,
                -delay or card.ivl, card.lastIvl, card.factor, card.timeTaken(),
                1)
        try:
            log()
        except:
            # duplicate pk; retry in 10ms
            time.sleep(0.01)
            log()

    # Interval management
    ##########################################################################

    def _nextRevIvl(self, card, ease):
        "Ideal next interval for CARD, given EASE."
        delay = self._daysLate(card)
        conf = self._revConf(card)
        fct = card.factor / 1000.0
        ivl2 = self._constrainedIvl((card.ivl + delay/4) * 1.2, conf, card.ivl)
        ivl3 = self._constrainedIvl((card.ivl + delay/2) * fct, conf, ivl2)
        ivl4 = self._constrainedIvl(
            (card.ivl + delay) * fct * conf['ease4'], conf, ivl3)
        if ease == 2:
            interval = ivl2
        elif ease == 3:
            interval = ivl3
        elif ease == 4:
            interval = ivl4
        # interval capped?
        return min(interval, conf['maxIvl'])

    def _constrainedIvl(self, ivl, conf, prev):
        "Integer interval after interval factor and prev+1 constraints applied."
        new = ivl * conf.get('ivlFct', 1)
        return int(max(new, prev+1))

    def _daysLate(self, card):
        "Number of days later than scheduled."
        due = card.odue if card.odid else card.due
        return max(0, self.today - due)

    def _updateRevIvl(self, card, ease):
        "Update CARD's interval, trying to avoid siblings."
        idealIvl = self._nextRevIvl(card, ease)
        card.ivl = self._adjRevIvl(card, idealIvl)

    def _adjRevIvl(self, card, idealIvl):
        "Given IDEALIVL, return an IVL away from siblings."
        idealDue = self.today + idealIvl
        conf = self._revConf(card)
        # find sibling positions
        dues = self.col.db.list(
            "select due from cards where nid = ? and type = 2"
            " and id != ?", card.nid, card.id)
        if not dues or idealDue not in dues:
            return idealIvl
        else:
            leeway = max(conf['minSpace'], int(idealIvl * conf['fuzz']))
            fudge = 0
            # do we have any room to adjust the interval?
            if leeway:
                # loop through possible due dates for an empty one
                for diff in range(1, leeway+1):
                    # ensure we're due at least tomorrow
                    if idealIvl - diff >= 1 and (idealDue - diff) not in dues:
                        fudge = -diff
                        break
                    elif (idealDue + diff) not in dues:
                        fudge = diff
                        break
            return idealIvl + fudge

    # Dynamic deck handling
    ##########################################################################

    def rebuildDyn(self, did=None):
        "Rebuild a dynamic deck."
        did = did or self.col.decks.selected()
        deck = self.col.decks.get(did)
        assert deck['dyn']
        # move any existing cards back first, then fill
        self.emptyDyn(did)
        ids = self._fillDyn(deck)
        if not ids:
            return
        # and change to our new deck
        self.col.decks.select(did)
        return ids

    def _fillDyn(self, deck):
        search, limit, order = deck['terms'][0]
        orderlimit = self._dynOrder(order, limit)
        search += " -is:suspended -deck:filtered"
        try:
            ids = self.col.findCards(search, order=orderlimit)
        except:
            ids = []
            return ids
        # move the cards over
        self._moveToDyn(deck['id'], ids)
        return ids

    def emptyDyn(self, did, lim=None):
        if not lim:
            lim = "did = %s" % did
        # move out of cram queue
        self.col.db.execute("""
update cards set did = odid, queue = (case when type = 1 then 0
else type end), type = (case when type = 1 then 0 else type end),
due = odue, odue = 0, odid = 0, usn = ?, mod = ? where %s""" % lim,
                            self.col.usn(), intTime())

    def remFromDyn(self, cids):
        self.emptyDyn(None, "id in %s and odid" % ids2str(cids))

    def _dynOrder(self, o, l):
        if o == DYN_OLDEST:
            t = "c.mod"
        elif o == DYN_RANDOM:
            t = "random()"
        elif o == DYN_SMALLINT:
            t = "ivl"
        elif o == DYN_BIGINT:
            t = "ivl desc"
        elif o == DYN_LAPSES:
            t = "lapses desc"
        elif o == DYN_ADDED:
            t = "n.id"
        elif o == DYN_REVADDED:
            t = "n.id desc"
        elif o == DYN_DUE:
            t = "c.due"
        else:
            # if we don't understand the term, default to due order
            t = "c.due"
        return t + " limit %d" % l

    def _moveToDyn(self, did, ids):
        deck = self.col.decks.get(did)
        data = []
        t = intTime(); u = self.col.usn()
        for c, id in enumerate(ids):
            # start at -100000 so that reviews are all due
            data.append((did, -100000+c, t, u, id))
        # due reviews stay in the review queue. careful: can't use
        # "odid or did", as sqlite converts to boolean
        queue = """
(case when type=2 and (case when odue then odue <= %d else due <= %d end)
 then 2 else 0 end)"""
        queue %= (self.today, self.today)
        self.col.db.executemany("""
update cards set
odid = (case when odid then odid else did end),
odue = (case when odue then odue else due end),
did = ?, queue = %s, due = ?, mod = ?, usn = ? where id = ?""" % queue, data)

    def _dynIvlBoost(self, card):
        assert card.odid and card.type == 2
        assert card.factor
        elapsed = card.ivl - (card.odue - self.today)
        factor = ((card.factor/1000.0)+1.2)/2.0
        ivl = int(max(card.ivl, elapsed * factor, 1))
        conf = self._revConf(card)
        return min(conf['maxIvl'], ivl)

    # Leeches
    ##########################################################################

    def _checkLeech(self, card, conf):
        "Leech handler. True if card was a leech."
        lf = conf['leechFails']
        if not lf:
            return
        # if over threshold or every half threshold reps after that
        if (card.lapses >= lf and
            (card.lapses-lf) % (max(lf/2, 1)) == 0):
            # add a leech tag
            f = card.note()
            f.addTag("leech")
            f.flush()
            # handle
            a = conf['leechAction']
            if a == 0:
                # if it has an old due, remove it from cram/relearning
                if card.odue:
                    card.due = card.odue
                if card.odid:
                    card.did = card.odid
                card.odue = card.odid = 0
                card.queue = -1
            # notify UI
            runHook("leech", card)
            return True

    # Tools
    ##########################################################################

    def _cardConf(self, card):
        return self.col.decks.confForDid(card.did)

    def _newConf(self, card):
        conf = self._cardConf(card)
        # normal deck
        if not card.odid:
            return conf['new']
        # dynamic deck; override some attributes, use original deck for others
        oconf = self.col.decks.confForDid(card.odid)
        delays = conf['delays'] or oconf['new']['delays']
        return dict(
            # original deck
            ints=oconf['new']['ints'],
            initialFactor=oconf['new']['initialFactor'],
            # overrides
            delays=delays,
            separate=conf['separate'],
            order=NEW_CARDS_DUE,
            perDay=self.reportLimit
        )

    def _lapseConf(self, card):
        conf = self._cardConf(card)
        # normal deck
        if not card.odid:
            return conf['lapse']
        # dynamic deck; override some attributes, use original deck for others
        oconf = self.col.decks.confForDid(card.odid)
        delays = conf['delays'] or oconf['lapse']['delays']
        return dict(
            # original deck
            minInt=oconf['lapse']['minInt'],
            leechFails=oconf['lapse']['leechFails'],
            leechAction=oconf['lapse']['leechAction'],
            mult=oconf['lapse']['mult'],
            # overrides
            delays=delays,
            resched=conf['resched'],
        )

    def _revConf(self, card):
        conf = self._cardConf(card)
        # normal deck
        if not card.odid:
            return conf['rev']
        # dynamic deck
        return self.col.decks.confForDid(card.odid)['rev']

    def _deckLimit(self):
        return ids2str(self.col.decks.active())

    def _resched(self, card):
        conf = self._cardConf(card)
        if not conf['dyn']:
            return True
        return conf['resched']

    # Daily cutoff
    ##########################################################################

    def _updateCutoff(self):
        # days since col created
        self.today = int((time.time() - self.col.crt) / 86400)
        # end of day cutoff
        self.dayCutoff = self.col.crt + (self.today+1)*86400
        # update all daily counts, but don't save decks to prevent needless
        # conflicts. we'll save on card answer instead
        def update(g):
            for t in "new", "rev", "lrn", "time":
                key = t+"Today"
                if g[key][0] != self.today:
                    g[key] = [self.today, 0]
        for deck in self.col.decks.all():
            update(deck)

    def _checkDay(self):
        # check if the day has rolled over
        if time.time() > self.dayCutoff:
            self.reset()

    # Deck finished state
    ##########################################################################

    def finishedMsg(self):
        return ("<b>"+_(
            "Congratulations! You have finished this deck for now.")+
            "</b><br><br>" + self._nextDueMsg())

    def _nextDueMsg(self):
        line = []
        if self.revDue():
            line.append(_("""\
Today's review limit has been reached, but there are still cards
waiting to be reviewed. For optimum memory, consider increasing
the daily limit in the options."""))
        if self.newDue():
            line.append(_("""\
There are more new cards available, but the daily limit has been
reached. You can increase the limit in the options, but please
bear in mind that the more new cards you introduce, the higher
your short-term review workload will become."""))
        if self.haveCustomStudy and not self.col.decks.current()['dyn']:
            line.append(_("""\
To study outside of the normal schedule, click the Custom Study button below."""))
        return "<p>".join(line)

    def revDue(self):
        "True if there are any rev cards due."
        return self.col.db.scalar(
            ("select 1 from cards where did in %s and queue = 2 "
             "and due <= ? limit 1") % self._deckLimit(),
            self.today)

    def newDue(self):
        "True if there are any new cards due."
        return self.col.db.scalar(
            ("select 1 from cards where did in %s and queue = 0 "
             "limit 1") % self._deckLimit())

    # Next time reports
    ##########################################################################

    def nextIvlStr(self, card, ease, short=False):
        "Return the next interval for CARD as a string."
        ivl = self.nextIvl(card, ease)
        if not ivl:
            return ""
        s = fmtTimeSpan(ivl, short=short)
        if ivl < self.col.conf['collapseTime']:
            s = "<"+s
        return s

    def nextIvl(self, card, ease):
        "Return the next interval for CARD, in seconds."
        if card.queue in (0,1,3):
            return self._nextLrnIvl(card, ease)
        elif ease == 1:
            # lapsed
            conf = self._lapseConf(card)
            if conf['delays']:
                return conf['delays'][0]*60
            return self._nextLapseIvl(card, conf)*86400
        else:
            # review
            return self._nextRevIvl(card, ease)*86400

    # this isn't easily extracted from the learn code
    def _nextLrnIvl(self, card, ease):
        if card.queue == 0:
            card.left = self._startingLeft(card)
        conf = self._lrnConf(card)
        if ease == 1:
            # fail
            return self._delayForGrade(conf, len(conf['delays']))
        elif ease == 3:
            # early removal
            if not self._resched(card):
                return 0
            return self._graduatingIvl(card, conf, True, adj=False) * 86400
        else:
            left = card.left%1000 - 1
            if left <= 0:
                # graduate
                if not self._resched(card):
                    return 0
                return self._graduatingIvl(card, conf, False, adj=False) * 86400
            else:
                return self._delayForGrade(conf, left)

    # Suspending
    ##########################################################################

    def suspendCards(self, ids):
        "Suspend cards."
        self.remFromDyn(ids)
        self.removeLrn(ids)
        self.col.db.execute(
            "update cards set queue=-1,mod=?,usn=? where id in "+
            ids2str(ids), intTime(), self.col.usn())

    def unsuspendCards(self, ids):
        "Unsuspend cards."
        self.col.db.execute(
            "update cards set queue=type,mod=?,usn=? "
            "where queue = -1 and id in "+ ids2str(ids),
            intTime(), self.col.usn())

    def buryNote(self, nid):
        "Bury all cards for note until next session."
        self.col.setDirty()
        cids = self.col.db.list(
            "select id from cards where nid = ? and queue >= 0", nid)
        self.col.db.execute("update cards set queue = -2 where id in "+ids2str(cids))

    # Resetting
    ##########################################################################

    def forgetCards(self, ids):
        "Put cards at the end of the new queue."
        self.col.db.execute(
            "update cards set type=0,queue=0,ivl=0,factor=? where id in "+
            ids2str(ids), 2500)
        pmax = self.col.db.scalar(
            "select max(due) from cards where type=0") or 0
        # takes care of mod + usn
        self.sortCards(ids, start=pmax+1)

    def reschedCards(self, ids, imin, imax):
        "Put cards in review queue with a new interval in days (min, max)."
        d = []
        t = self.today
        mod = intTime()
        for id in ids:
            r = random.randint(imin, imax)
            d.append(dict(id=id, due=r+t, ivl=max(1, r), mod=mod,
                          usn=self.col.usn(), fact=2500))
        self.col.db.executemany("""
update cards set type=2,queue=2,ivl=:ivl,due=:due,
usn=:usn, mod=:mod, factor=:fact where id=:id and odid=0""",
                                d)

    def resetCards(self, ids):
        "Completely reset cards for export."
        self.col.db.execute(
            "update cards set reps=0, lapses=0 where id in " + ids2str(ids))
        self.forgetCards(ids)

    # Repositioning new cards
    ##########################################################################

    def sortCards(self, cids, start=1, step=1, shuffle=False, shift=False):
        scids = ids2str(cids)
        now = intTime()
        nids = []
        nidsSet = set()
        for id in cids:
            nid = self.col.db.scalar("select nid from cards where id = ?", id)
            if nid not in nidsSet:
                nids.append(nid)
                nidsSet.add(nid)
        if not nids:
            # no new cards
            return
        # determine nid ordering
        due = {}
        if shuffle:
            random.shuffle(nids)
        for c, nid in enumerate(nids):
            due[nid] = start+c*step
        high = start+c*step
        # shift?
        if shift:
            low = self.col.db.scalar(
                "select min(due) from cards where due >= ? and type = 0 "
                "and id not in %s" % scids,
                start)
            if low is not None:
                shiftby = high - low + 1
                self.col.db.execute("""
update cards set mod=?, usn=?, due=due+? where id not in %s
and due >= ? and queue = 0""" % scids, now, self.col.usn(), shiftby, low)
        # reorder cards
        d = []
        for id, nid in self.col.db.execute(
            "select id, nid from cards where type = 0 and id in "+scids):
            d.append(dict(now=now, due=due[nid], usn=self.col.usn(), cid=id))
        self.col.db.executemany(
            "update cards set due=:due,mod=:now,usn=:usn where id = :cid", d)

    def randomizeCards(self, did):
        cids = self.col.db.list("select id from cards where did = ?", did)
        self.sortCards(cids, shuffle=True)

    def orderCards(self, did):
        cids = self.col.db.list("select id from cards where did = ? order by id", did)
        self.sortCards(cids)

    def resortConf(self, conf):
        for did in self.col.decks.didsForConf(conf):
            if conf['new']['order'] == 0:
                self.randomizeCards(did)
            else:
                self.orderCards(did)

########NEW FILE########
__FILENAME__ = sound
# -*- coding: utf-8 -*-
# Copyright: Damien Elmes <anki@ichi2.net>
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

import re, sys, threading, time, subprocess, os, signal, errno, atexit
import shutil, random
from anki.hooks import addHook, runHook
from anki.utils import namedtmp, tmpdir, isWin, isMac

# Shared utils
##########################################################################

_soundReg = "\[sound:(.*?)\]"

def playFromText(text):
    for match in re.findall(_soundReg, text):
        play(match)

def stripSounds(text):
    return re.sub(_soundReg, "", text)

def hasSound(text):
    return re.search(_soundReg, text) is not None

##########################################################################

processingSrc = "rec.wav"
processingDst = "rec.mp3"
processingChain = []
recFiles = []

processingChain = [
    ["lame", "rec.wav", processingDst, "--noreplaygain", "--quiet"],
    ]

# don't show box on windows
if isWin:
    si = subprocess.STARTUPINFO()
    try:
        si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    except:
        # python2.7+
        si.dwFlags |= subprocess._subprocess.STARTF_USESHOWWINDOW
else:
    si = None

if isMac:
    # make sure lame, which is installed in /usr/local/bin, is in the path
    os.environ['PATH'] += ":" + "/usr/local/bin"
    dir = os.path.dirname(os.path.abspath(__file__))
    dir = os.path.abspath(dir + "/../../../..")
    os.environ['PATH'] += ":" + dir + "/audio"

def retryWait(proc):
    # osx throws interrupted system call errors frequently
    while 1:
        try:
            return proc.wait()
        except OSError:
            continue

# Mplayer settings
##########################################################################

if isWin:
    mplayerCmd = ["mplayer.exe", "-ao", "win32"]
    dir = os.path.dirname(os.path.abspath(sys.argv[0]))
    os.environ['PATH'] += ";" + dir
    os.environ['PATH'] += ";" + dir + "\\..\\win\\top" # for testing
else:
    mplayerCmd = ["mplayer"]
mplayerCmd += ["-really-quiet", "-noautosub"]

# Mplayer in slave mode
##########################################################################

mplayerQueue = []
mplayerManager = None
mplayerReader = None
mplayerEvt = threading.Event()
mplayerClear = False

class MplayerMonitor(threading.Thread):

    def run(self):
        global mplayerClear
        self.mplayer = None
        self.deadPlayers = []
        while 1:
            mplayerEvt.wait()
            mplayerEvt.clear()
            # clearing queue?
            if mplayerClear and self.mplayer:
                try:
                    self.mplayer.stdin.write("stop\n")
                except:
                    # mplayer quit by user (likely video)
                    self.deadPlayers.append(self.mplayer)
                    self.mplayer = None
            # loop through files to play
            while mplayerQueue:
                # ensure started
                if not self.mplayer:
                    self.startProcess()
                # pop a file
                try:
                    item = mplayerQueue.pop(0)
                except IndexError:
                    # queue was cleared by main thread
                    continue
                if mplayerClear:
                    mplayerClear = False
                    extra = ""
                else:
                    extra = " 1"
                cmd = 'loadfile "%s"%s\n' % (item, extra)
                try:
                    self.mplayer.stdin.write(cmd)
                except:
                    # mplayer has quit and needs restarting
                    self.deadPlayers.append(self.mplayer)
                    self.mplayer = None
                    self.startProcess()
                    self.mplayer.stdin.write(cmd)
                # if we feed mplayer too fast it loses files
                time.sleep(1)
            # wait() on finished processes. we don't want to block on the
            # wait, so we keep trying each time we're reactivated
            def clean(pl):
                if pl.poll() is not None:
                    pl.wait()
                    return False
                else:
                    return True
            self.deadPlayers = [pl for pl in self.deadPlayers if clean(pl)]

    def kill(self):
        if not self.mplayer:
            return
        try:
            self.mplayer.stdin.write("quit\n")
            self.deadPlayers.append(self.mplayer)
        except:
            pass
        self.mplayer = None

    def startProcess(self):
        try:
            cmd = mplayerCmd + ["-slave", "-idle"]
            devnull = file(os.devnull, "w")
            self.mplayer = subprocess.Popen(
                cmd, startupinfo=si, stdin=subprocess.PIPE,
                stdout=devnull, stderr=devnull)
        except OSError:
            mplayerEvt.clear()
            raise Exception("Did you install mplayer?")

def queueMplayer(path):
    ensureMplayerThreads()
    if isWin and os.path.exists(path):
        # mplayer on windows doesn't like the encoding, so we create a
        # temporary file instead. oddly, foreign characters in the dirname
        # don't seem to matter.
        dir = tmpdir()
        name = os.path.join(dir, "audio%s%s" % (
            random.randrange(0, 1000000), os.path.splitext(path)[1]))
        f = open(name, "wb")
        f.write(open(path, "rb").read())
        f.close()
        # it wants unix paths, too!
        path = name.replace("\\", "/")
        path = path.encode(sys.getfilesystemencoding())
    else:
        path = path.encode("utf-8")
    mplayerQueue.append(path)
    mplayerEvt.set()

def clearMplayerQueue():
    global mplayerClear, mplayerQueue
    mplayerQueue = []
    mplayerClear = True
    mplayerEvt.set()

def ensureMplayerThreads():
    global mplayerManager
    if not mplayerManager:
        mplayerManager = MplayerMonitor()
        mplayerManager.daemon = True
        mplayerManager.start()
        # ensure the tmpdir() exit handler is registered first so it runs
        # after the mplayer exit
        tmpdir()
        # clean up mplayer on exit
        atexit.register(stopMplayer)

def stopMplayer(*args):
    if not mplayerManager:
        return
    mplayerManager.kill()

addHook("unloadProfile", stopMplayer)

# PyAudio recording
##########################################################################

try:
    import pyaudio
    import wave

    PYAU_FORMAT = pyaudio.paInt16
    PYAU_CHANNELS = 1
    PYAU_RATE = 44100
    PYAU_INPUT_INDEX = None
except:
    pass

class _Recorder(object):

    def postprocess(self, encode=True):
        self.encode = encode
        for c in processingChain:
            #print c
            if not self.encode and c[0] == 'lame':
                continue
            try:
                ret = retryWait(subprocess.Popen(c, startupinfo=si))
            except:
                ret = True
            if ret:
                raise Exception(_(
                    "Error running %s") %
                                u" ".join(c))

class PyAudioThreadedRecorder(threading.Thread):

    def __init__(self):
        threading.Thread.__init__(self)
        self.finish = False

    def run(self):
        chunk = 1024
        try:
            p = pyaudio.PyAudio()
        except NameError:
            raise Exception(
                "Pyaudio not installed (recording not supported on OSX10.3)")
        stream = p.open(format=PYAU_FORMAT,
                        channels=PYAU_CHANNELS,
                        rate=PYAU_RATE,
                        input=True,
                        input_device_index=PYAU_INPUT_INDEX,
                        frames_per_buffer=chunk)
        all = []
        while not self.finish:
            try:
                data = stream.read(chunk)
            except IOError, e:
                if e[1] == pyaudio.paInputOverflowed:
                    data = None
                else:
                    raise
            if data:
                all.append(data)
        stream.close()
        p.terminate()
        data = ''.join(all)
        wf = wave.open(processingSrc, 'wb')
        wf.setnchannels(PYAU_CHANNELS)
        wf.setsampwidth(p.get_sample_size(PYAU_FORMAT))
        wf.setframerate(PYAU_RATE)
        wf.writeframes(data)
        wf.close()

class PyAudioRecorder(_Recorder):

    def __init__(self):
        for t in recFiles + [processingSrc, processingDst]:
            try:
                os.unlink(t)
            except OSError:
                pass
        self.encode = False

    def start(self):
        self.thread = PyAudioThreadedRecorder()
        self.thread.start()

    def stop(self):
        self.thread.finish = True
        self.thread.join()

    def file(self):
        if self.encode:
            tgt = "rec%d.mp3" % time.time()
            os.rename(processingDst, tgt)
            return tgt
        else:
            return processingSrc

# Audio interface
##########################################################################

_player = queueMplayer
_queueEraser = clearMplayerQueue

def play(path):
    _player(path)

def clearAudioQueue():
    _queueEraser()

Recorder = PyAudioRecorder

########NEW FILE########
__FILENAME__ = stats
# -*- coding: utf-8 -*-
# Copyright: Damien Elmes <anki@ichi2.net>
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

import time, sys, os, datetime, json
import anki.js
from anki.utils import fmtTimeSpan, fmtFloat, ids2str
from anki.consts import *
from anki.lang import _, ngettext
from anki.hooks import runFilter

# Card stats
##########################################################################

class CardStats(object):

    def __init__(self, col, card):
        self.col = col
        self.card = card

    def report(self):
        c = self.card
        fmt = lambda x, **kwargs: fmtTimeSpan(x, short=True, **kwargs)
        self.txt = "<table width=100%>"
        self.addLine(_("Added"), self.date(c.id/1000))
        first = self.col.db.scalar(
            "select min(id) from revlog where cid = ?", c.id)
        last = self.col.db.scalar(
            "select max(id) from revlog where cid = ?", c.id)
        if first:
            self.addLine(_("First Review"), self.date(first/1000))
            self.addLine(_("Latest Review"), self.date(last/1000))
        if c.type in (1,2):
            if c.odid or c.queue < 0:
                next = None
            else:
                if c.queue in (2,3):
                    next = time.time()+((c.due - self.col.sched.today)*86400)
                else:
                    next = c.due
                next = self.date(next)
            if next:
                self.addLine(_("Due"), next)
            if c.queue == 2:
                self.addLine(_("Interval"), fmt(c.ivl * 86400))
            self.addLine(_("Ease"), "%d%%" % (c.factor/10.0))
            self.addLine(_("Reviews"), "%d" % c.reps)
            self.addLine(_("Lapses"), "%d" % c.lapses)
            (cnt, total) = self.col.db.first(
                "select count(), sum(time)/1000 from revlog where cid = :id",
                id=c.id)
            if cnt:
                self.addLine(_("Average Time"), self.time(total / float(cnt)))
                self.addLine(_("Total Time"), self.time(total))
        elif c.queue == 0:
            self.addLine(_("Position"), c.due)
        self.addLine(_("Card Type"), c.template()['name'])
        self.addLine(_("Note Type"), c.model()['name'])
        self.addLine(_("Deck"), self.col.decks.name(c.did))
        self.txt += "</table>"
        return self.txt

    def addLine(self, k, v):
        self.txt += self.makeLine(k, v)

    def makeLine(self, k, v):
        txt = "<tr><td align=left style='padding-right: 3px;'>"
        txt += "<b>%s</b></td><td>%s</td></tr>" % (k, v)
        return txt

    def date(self, tm):
        return time.strftime("%Y-%m-%d", time.localtime(tm))

    def time(self, tm):
        str = ""
        if tm >= 60:
            str = fmtTimeSpan((tm/60)*60, short=True, point=-1, unit=1)
        if tm%60 != 0 or not str:
            str += fmtTimeSpan(tm%60, point=2 if not str else -1, short=True)
        return str

# Collection stats
##########################################################################

colYoung = "#7c7"
colMature = "#070"
colCum = "rgba(0,0,0,0.9)"
colLearn = "#00F"
colRelearn = "#c00"
colCram = "#ff0"
colIvl = "#077"
colHour = "#ccc"
colTime = "#770"
colUnseen = "#000"
colSusp = "#ff0"

class CollectionStats(object):

    def __init__(self, col):
        self.col = col
        self._stats = None
        self.type = 0
        self.width = 600
        self.height = 200
        self.wholeCollection = False

    def report(self, type=0):
        # 0=days, 1=weeks, 2=months
        self.type = type
        from statsbg import bg
        txt = self.css % bg
        txt += self.todayStats()
        txt += self.dueGraph()
        txt += self.repsGraph()
        txt += self.ivlGraph()
        txt += self.hourGraph()
        txt += self.easeGraph()
        txt += self.cardGraph()
        txt += self.footer()
        return "<script>%s\n</script><center>%s</center>" % (
            anki.js.jquery+anki.js.plot, txt)

    css = """
<style>
h1 { margin-bottom: 0; margin-top: 1em; }
.pielabel { text-align:center; padding:0px; color:white; }
body {background-image: url(data:image/png;base64,%s); }
</style>
"""

    # Today stats
    ######################################################################

    def todayStats(self):
        b = self._title(_("Today"))
        # studied today
        lim = self._revlogLimit()
        if lim:
            lim = " and " + lim
        cards, thetime, failed, lrn, rev, relrn, filt = self.col.db.first("""
select count(), sum(time)/1000,
sum(case when ease = 1 then 1 else 0 end), /* failed */
sum(case when type = 0 then 1 else 0 end), /* learning */
sum(case when type = 1 then 1 else 0 end), /* review */
sum(case when type = 2 then 1 else 0 end), /* relearn */
sum(case when type = 3 then 1 else 0 end) /* filter */
from revlog where id > ? """+lim, (self.col.sched.dayCutoff-86400)*1000)
        cards = cards or 0
        thetime = thetime or 0
        failed = failed or 0
        lrn = lrn or 0
        rev = rev or 0
        relrn = relrn or 0
        filt = filt or 0
        # studied
        def bold(s):
            return "<b>"+unicode(s)+"</b>"
        msgp1 = ngettext("%d card", "%d cards", cards) % cards
        b += _("Studied %(a)s in %(b)s today.") % dict(
            a=bold(msgp1), b=bold(fmtTimeSpan(thetime, unit=1)))
        # again/pass count
        b += "<br>" + _("Again count: %s") % bold(failed)
        if cards:
            b += " " + _("(%s correct)") % bold(
                "%0.1f%%" %((1-failed/float(cards))*100))
        # type breakdown
        b += "<br>"
        b += (_("Learn: %(a)s, Review: %(b)s, Relearn: %(c)s, Filtered: %(d)s")
              % dict(a=bold(lrn), b=bold(rev), c=bold(relrn), d=bold(filt)))
        return b

    # Due and cumulative due
    ######################################################################

    def dueGraph(self):
        if self.type == 0:
            start = 0; end = 31; chunk = 1;
        elif self.type == 1:
            start = 0; end = 52; chunk = 7
        elif self.type == 2:
            start = 0; end = None; chunk = 30
        d = self._due(start, end, chunk)
        yng = []
        mtr = []
        tot = 0
        totd = []
        for day in d:
            yng.append((day[0], day[1]))
            mtr.append((day[0], day[2]))
            tot += day[1]+day[2]
            totd.append((day[0], tot))
        data = [
            dict(data=mtr, color=colMature, label=_("Mature")),
            dict(data=yng, color=colYoung, label=_("Young")),
        ]
        if len(totd) > 1:
            data.append(
                dict(data=totd, color=colCum, label=_("Cumulative"), yaxis=2,
                     bars={'show': False}, lines=dict(show=True), stack=False))
        txt = self._title(
            _("Forecast"),
            _("The number of reviews due in the future."))
        xaxis = dict(tickDecimals=0, min=-0.5)
        if end is not None:
            xaxis['max'] = end-0.5
        txt += self._graph(id="due", data=data,
                           ylabel2=_("Cumulative Cards"), conf=dict(
                xaxis=xaxis, yaxes=[dict(), dict(
                    tickDecimals=0, position="right")]))
        txt += self._dueInfo(tot, len(totd)*chunk)
        return txt

    def _dueInfo(self, tot, num):
        i = []
        self._line(i, _("Total"), ngettext("%d review", "%d reviews", tot) % tot)
        self._line(i, _("Average"), self._avgDay(
            tot, num, _("reviews")))
        tomorrow = self.col.db.scalar("""
select count() from cards where did in %s and queue in (2,3)
and due = ?""" % self._limit(), self.col.sched.today+1)
        tomorrow = ngettext("%d card", "%d cards", tomorrow) % tomorrow
        self._line(i, _("Due tomorrow"), tomorrow)
        return self._lineTbl(i)

    def _due(self, start=None, end=None, chunk=1):
        lim = ""
        if start is not None:
            lim += " and due-:today >= %d" % start
        if end is not None:
            lim += " and day < %d" % end
        return self.col.db.all("""
select (due-:today)/:chunk as day,
sum(case when ivl < 21 then 1 else 0 end), -- yng
sum(case when ivl >= 21 then 1 else 0 end) -- mtr
from cards
where did in %s and queue in (2,3)
%s
group by day order by day""" % (self._limit(), lim),
                            today=self.col.sched.today,
                            chunk=chunk)

    # Reps and time spent
    ######################################################################

    def repsGraph(self):
        if self.type == 0:
            days = 30; chunk = 1
        elif self.type == 1:
            days = 52; chunk = 7
        else:
            days = None; chunk = 30
        return self._repsGraph(self._done(days, chunk),
                               days,
                               _("Review Count"),
                               _("Review Time"))

    def _repsGraph(self, data, days, reptitle, timetitle):
        if not data:
            return ""
        d = data
        conf = dict(
            xaxis=dict(tickDecimals=0, max=0.5),
            yaxes=[dict(), dict(position="right")])
        if days is not None:
            conf['xaxis']['min'] = -days+0.5
        def plot(id, data, ylabel, ylabel2):
            return self._graph(
                id, data=data, conf=conf, ylabel=ylabel, ylabel2=ylabel2)
        # reps
        (repdata, repsum) = self._splitRepData(d, (
            (3, colMature, _("Mature")),
            (2, colYoung, _("Young")),
            (4, colRelearn, _("Relearn")),
            (1, colLearn, _("Learn")),
            (5, colCram, _("Cram"))))
        txt = self._title(
            reptitle, _("The number of questions you have answered."))
        txt += plot("reps", repdata, ylabel=_("Answers"), ylabel2=_(
            "Cumulative Answers"))
        (daysStud, fstDay) = self._daysStudied()
        rep, tot = self._ansInfo(repsum, daysStud, fstDay, _("reviews"))
        txt += rep
        # time
        (timdata, timsum) = self._splitRepData(d, (
            (8, colMature, _("Mature")),
            (7, colYoung, _("Young")),
            (9, colRelearn, _("Relearn")),
            (6, colLearn, _("Learn")),
            (10, colCram, _("Cram"))))
        if self.type == 0:
            t = _("Minutes")
            convHours = False
        else:
            t = _("Hours")
            convHours = True
        txt += self._title(timetitle, _("The time taken to answer the questions."))
        txt += plot("time", timdata, ylabel=t, ylabel2=_("Cumulative %s") % t)
        rep, tot2 = self._ansInfo(
            timsum, daysStud, fstDay, _("minutes"), convHours, total=tot)
        txt += rep
        return txt

    def _ansInfo(self, totd, studied, first, unit, convHours=False, total=None):
        if not totd:
            return
        tot = totd[-1][1]
        period = self._periodDays()
        if not period:
            # base off earliest repetition date
            lim = self._revlogLimit()
            if lim:
                lim = " where " + lim
            t = self.col.db.scalar("select id from revlog %s order by id limit 1" % lim)
            if not t:
                period = 1
            else:
                period = max(
                    1, (self.col.sched.dayCutoff - (t/1000)) / 86400)
        i = []
        self._line(i, _("Days studied"),
                   _("<b>%(pct)d%%</b> (%(x)s of %(y)s)") % dict(
                       x=studied, y=period, pct=studied/float(period)*100),
                   bold=False)
        if convHours:
            tunit = _("hours")
        else:
            tunit = unit
        self._line(i, _("Total"), _("%(tot)s %(unit)s") % dict(
            unit=tunit, tot=int(tot)))
        if convHours:
            # convert to minutes
            tot *= 60
        self._line(i, _("Average for days studied"), self._avgDay(
            tot, studied, unit))
        self._line(i, _("If you studied every day"), self._avgDay(
            tot, period, unit))
        if total and tot:
            perMin = total / float(tot)
            perMin = ngettext("%d card/minute", "%d cards/minute", perMin) % perMin
            self._line(
                i, _("Average answer time"),
                "%0.1fs (%s)" % ((tot*60)/total, perMin))
        return self._lineTbl(i), int(tot)

    def _splitRepData(self, data, spec):
        sep = {}
        totcnt = {}
        totd = {}
        alltot = []
        allcnt = 0
        for (n, col, lab) in spec:
            totcnt[n] = 0
            totd[n] = []
        sum = []
        for row in data:
            for (n, col, lab) in spec:
                if n not in sep:
                    sep[n] = []
                sep[n].append((row[0], row[n]))
                totcnt[n] += row[n]
                allcnt += row[n]
                totd[n].append((row[0], totcnt[n]))
            alltot.append((row[0], allcnt))
        ret = []
        for (n, col, lab) in spec:
            if len(totd[n]) and totcnt[n]:
                # bars
                ret.append(dict(data=sep[n], color=col, label=lab))
                # lines
                ret.append(dict(
                    data=totd[n], color=col, label=None, yaxis=2,
                bars={'show': False}, lines=dict(show=True), stack=-n))
        return (ret, alltot)

    def _done(self, num=7, chunk=1):
        lims = []
        if num is not None:
            lims.append("id > %d" % (
                (self.col.sched.dayCutoff-(num*chunk*86400))*1000))
        lim = self._revlogLimit()
        if lim:
            lims.append(lim)
        if lims:
            lim = "where " + " and ".join(lims)
        else:
            lim = ""
        if self.type == 0:
            tf = 60.0 # minutes
        else:
            tf = 3600.0 # hours
        return self.col.db.all("""
select
(cast((id/1000.0 - :cut) / 86400.0 as int))/:chunk as day,
sum(case when type = 0 then 1 else 0 end), -- lrn count
sum(case when type = 1 and lastIvl < 21 then 1 else 0 end), -- yng count
sum(case when type = 1 and lastIvl >= 21 then 1 else 0 end), -- mtr count
sum(case when type = 2 then 1 else 0 end), -- lapse count
sum(case when type = 3 then 1 else 0 end), -- cram count
sum(case when type = 0 then time/1000.0 else 0 end)/:tf, -- lrn time
-- yng + mtr time
sum(case when type = 1 and lastIvl < 21 then time/1000.0 else 0 end)/:tf,
sum(case when type = 1 and lastIvl >= 21 then time/1000.0 else 0 end)/:tf,
sum(case when type = 2 then time/1000.0 else 0 end)/:tf, -- lapse time
sum(case when type = 3 then time/1000.0 else 0 end)/:tf -- cram time
from revlog %s
group by day order by day""" % lim,
                            cut=self.col.sched.dayCutoff,
                            tf=tf,
                            chunk=chunk)

    def _daysStudied(self):
        lims = []
        num = self._periodDays()
        if num:
            lims.append(
                "id > %d" %
                ((self.col.sched.dayCutoff-(num*86400))*1000))
        rlim = self._revlogLimit()
        if rlim:
            lims.append(rlim)
        if lims:
            lim = "where " + " and ".join(lims)
        else:
            lim = ""
        return self.col.db.first("""
select count(), abs(min(day)) from (select
(cast((id/1000 - :cut) / 86400.0 as int)+1) as day
from revlog %s
group by day order by day)""" % lim,
                                   cut=self.col.sched.dayCutoff)

    # Intervals
    ######################################################################

    def ivlGraph(self):
        (ivls, all, avg, max_) = self._ivls()
        tot = 0
        totd = []
        if not ivls or not all:
            return ""
        for (grp, cnt) in ivls:
            tot += cnt
            totd.append((grp, tot/float(all)*100))
        if self.type == 0:
            ivlmax = 31
        elif self.type == 1:
            ivlmax = 52
        else:
            ivlmax = max(5, ivls[-1][0])
        txt = self._title(_("Intervals"),
                          _("Delays until reviews are shown again."))
        txt += self._graph(id="ivl", ylabel2=_("Percentage"), data=[
            dict(data=ivls, color=colIvl),
            dict(data=totd, color=colCum, yaxis=2,
             bars={'show': False}, lines=dict(show=True), stack=False)
            ], conf=dict(
                xaxis=dict(min=-0.5, max=ivlmax+0.5),
                yaxes=[dict(), dict(position="right", max=105)]))
        i = []
        self._line(i, _("Average interval"), fmtTimeSpan(avg*86400))
        self._line(i, _("Longest interval"), fmtTimeSpan(max_*86400))
        return txt + self._lineTbl(i)

    def _ivls(self):
        if self.type == 0:
            chunk = 1; lim = " and grp <= 30"
        elif self.type == 1:
            chunk = 7; lim = " and grp <= 52"
        else:
            chunk = 30; lim = ""
        data = [self.col.db.all("""
select ivl / :chunk as grp, count() from cards
where did in %s and queue = 2 %s
group by grp
order by grp""" % (self._limit(), lim), chunk=chunk)]
        return data + list(self.col.db.first("""
select count(), avg(ivl), max(ivl) from cards where did in %s and queue = 2""" %
                                         self._limit()))

    # Eases
    ######################################################################

    def easeGraph(self):
        # 3 + 4 + 4 + spaces on sides and middle = 15
        # yng starts at 1+3+1 = 5
        # mtr starts at 5+4+1 = 10
        d = {'lrn':[], 'yng':[], 'mtr':[]}
        types = ("lrn", "yng", "mtr")
        eases = self._eases()
        for (type, ease, cnt) in eases:
            if type == 1:
                ease += 5
            elif type == 2:
                ease += 10
            n = types[type]
            d[n].append((ease, cnt))
        ticks = [[1,1],[2,2],[3,3],
                 [6,1],[7,2],[8,3],[9,4],
                 [11, 1],[12,2],[13,3],[14,4]]
        txt = self._title(_("Answer Buttons"),
                          _("The number of times you have pressed each button."))
        txt += self._graph(id="ease", data=[
            dict(data=d['lrn'], color=colLearn, label=_("Learning")),
            dict(data=d['yng'], color=colYoung, label=_("Young")),
            dict(data=d['mtr'], color=colMature, label=_("Mature")),
            ], type="barsLine", conf=dict(
                xaxis=dict(ticks=ticks, min=0, max=15)),
            ylabel=_("Answers"))
        txt += self._easeInfo(eases)
        return txt

    def _easeInfo(self, eases):
        types = {0: [0, 0], 1: [0, 0], 2: [0,0]}
        for (type, ease, cnt) in eases:
            if ease == 1:
                types[type][0] += cnt
            else:
                types[type][1] += cnt
        i = []
        for type in range(3):
            (bad, good) = types[type]
            tot = bad + good
            try:
                pct = good / float(tot) * 100
            except:
                pct = 0
            i.append(_(
                "Correct: <b>%(pct)0.2f%%</b><br>(%(good)d of %(tot)d)") % dict(
                pct=pct, good=good, tot=tot))
        return ("""
<center><table width=%dpx><tr><td width=50></td><td align=center>""" % self.width +
                "</td><td align=center>".join(i) +
                "</td></tr></table></center>")

    def _eases(self):
        lims = []
        lim = self._revlogLimit()
        if lim:
            lims.append(lim)
        if self.type == 0:
            days = 30
        elif self.type == 1:
            days = 365
        else:
            days = None
        if days is not None:
            lims.append("id > %d" % (
                (self.col.sched.dayCutoff-(days*86400))*1000))
        if lims:
            lim = "where " + " and ".join(lims)
        else:
            lim = ""
        return self.col.db.all("""
select (case
when type in (0,2) then 0
when lastIvl < 21 then 1
else 2 end) as thetype,
(case when type in (0,2) and ease = 4 then 3 else ease end), count() from revlog %s
group by thetype, ease
order by thetype, ease""" % lim)

    # Hourly retention
    ######################################################################

    def hourGraph(self):
        data = self._hourRet()
        if not data:
            return ""
        shifted = []
        counts = []
        mcount = 0
        trend = []
        peak = 0
        for d in data:
            hour = (d[0] - 4) % 24
            pct = d[1]
            if pct > peak:
                peak = pct
            shifted.append((hour, pct))
            counts.append((hour, d[2]))
            if d[2] > mcount:
                mcount = d[2]
        shifted.sort()
        counts.sort()
        if len(counts) < 4:
            return ""
        for d in shifted:
            hour = d[0]
            pct = d[1]
            if not trend:
                trend.append((hour, pct))
            else:
                prev = trend[-1][1]
                diff = pct-prev
                diff /= 3.0
                diff = round(diff, 1)
                trend.append((hour, prev+diff))
        txt = self._title(_("Hourly Breakdown"),
                          _("Review success rate for each hour of the day."))
        txt += self._graph(id="hour", data=[
            dict(data=shifted, color=colCum, label=_("% Correct")),
            dict(data=counts, color=colHour, label=_("Answers"), yaxis=2,
             bars=dict(barWidth=0.2), stack=False)
        ], conf=dict(
            xaxis=dict(ticks=[[0, _("4AM")], [6, _("10AM")],
                           [12, _("4PM")], [18, _("10PM")], [23, _("3AM")]]),
            yaxes=[dict(max=peak), dict(position="right", max=mcount)]),
        ylabel=_("% Correct"), ylabel2=_("Reviews"))
        txt += _("Hours with less than 30 reviews are not shown.")
        return txt

    def _hourRet(self):
        lim = self._revlogLimit()
        if lim:
            lim = " and " + lim
        sd = datetime.datetime.fromtimestamp(self.col.crt)
        pd = self._periodDays()
        if pd:
            lim += " and id > %d" % ((self.col.sched.dayCutoff-(86400*pd))*1000)
        return self.col.db.all("""
select
23 - ((cast((:cut - id/1000) / 3600.0 as int)) %% 24) as hour,
sum(case when ease = 1 then 0 else 1 end) /
cast(count() as float) * 100,
count()
from revlog where type in (0,1,2) %s
group by hour having count() > 30 order by hour""" % lim,
                            cut=self.col.sched.dayCutoff-(sd.hour*3600))

    # Cards
    ######################################################################

    def cardGraph(self):
        # graph data
        div = self._cards()
        d = []
        for c, (t, col) in enumerate((
            (_("Mature"), colMature),
            (_("Young+Learn"), colYoung),
            (_("Unseen"), colUnseen),
            (_("Suspended"), colSusp))):
            d.append(dict(data=div[c], label="%s: %s" % (t, div[c]), color=col))
        # text data
        i = []
        (c, f) = self.col.db.first("""
select count(id), count(distinct nid) from cards
where did in %s """ % self._limit())
        self._line(i, _("Total cards"), c)
        self._line(i, _("Total notes"), f)
        (low, avg, high) = self._factors()
        if low:
            self._line(i, _("Lowest ease"), "%d%%" % low)
            self._line(i, _("Average ease"), "%d%%" % avg)
            self._line(i, _("Highest ease"), "%d%%" % high)
        info = "<table width=100%>" + "".join(i) + "</table><p>"
        info += _('''\
A card's <i>ease</i> is the size of the next interval \
when you answer "good" on a review.''')
        txt = self._title(_("Cards Types"),
                          _("The division of cards in your deck(s)."))
        txt += "<table width=%d><tr><td>%s</td><td>%s</td></table>" % (
            self.width,
            self._graph(id="cards", data=d, type="pie"),
            info)
        return txt

    def _line(self, i, a, b, bold=True):
        colon = _(":")
        if bold:
            i.append(("<tr><td width=200 align=right>%s%s</td><td><b>%s</b></td></tr>") % (a,colon,b))
        else:
            i.append(("<tr><td width=200 align=right>%s%s</td><td>%s</td></tr>") % (a,colon,b))

    def _lineTbl(self, i):
        return "<table width=400>" + "".join(i) + "</table>"

    def _factors(self):
        return self.col.db.first("""
select
min(factor) / 10.0,
avg(factor) / 10.0,
max(factor) / 10.0
from cards where did in %s and queue = 2""" % self._limit())

    def _cards(self):
        return self.col.db.first("""
select
sum(case when queue=2 and ivl >= 21 then 1 else 0 end), -- mtr
sum(case when queue in (1,3) or (queue=2 and ivl < 21) then 1 else 0 end), -- yng/lrn
sum(case when queue=0 then 1 else 0 end), -- new
sum(case when queue=-1 then 1 else 0 end) -- susp
from cards where did in %s""" % self._limit())

    # Footer
    ######################################################################

    def footer(self):
        b = "<br><br><font size=1>"
        b += _("Generated on %s") % time.asctime(time.localtime(time.time()))
        b += "<br>"
        if self.wholeCollection:
            deck = _("whole collection")
        else:
            deck = self.col.decks.current()['name']
        b += _("Scope: %s") % deck
        b += "<br>"
        b += _("Period: %s") % [
            _("1 month"),
            _("1 year"),
            _("deck life")
            ][self.type]
        return b

    # Tools
    ######################################################################

    def _graph(self, id, data, conf={},
               type="bars", ylabel=_("Cards"), timeTicks=True, ylabel2=""):
        # display settings
        if type == "pie":
            conf['legend'] = {'container': "#%sLegend" % id, 'noColumns':2}
        else:
            conf['legend'] = {'container': "#%sLegend" % id, 'noColumns':10}
        conf['series'] = dict(stack=True)
        if not 'yaxis' in conf:
            conf['yaxis'] = {}
        conf['yaxis']['labelWidth'] = 40
        if 'xaxis' not in conf:
            conf['xaxis'] = {}
        if timeTicks:
            conf['timeTicks'] = (_("d"), _("w"), _("mo"))[self.type]
        # types
        width = self.width
        height = self.height
        if type == "bars":
            conf['series']['bars'] = dict(
                show=True, barWidth=0.8, align="center", fill=0.7, lineWidth=0)
        elif type == "barsLine":
            conf['series']['bars'] = dict(
                show=True, barWidth=0.8, align="center", fill=0.7, lineWidth=3)
        elif type == "fill":
            conf['series']['lines'] = dict(show=True, fill=True)
        elif type == "pie":
            width /= 2.3
            height *= 1.5
            ylabel = ""
            conf['series']['pie'] = dict(
                show=True,
                radius=1,
                stroke=dict(color="#fff", width=5),
                label=dict(
                    show=True,
                    radius=0.8,
                    threshold=0.01,
                    background=dict(
                        opacity=0.5,
                        color="#000"
                    )))

            #conf['legend'] = dict(show=False)
        return (
"""
<table cellpadding=0 cellspacing=10>
<tr>

<td><div style="width: 150px; text-align: center; position:absolute;
 -webkit-transform: rotate(-90deg) translateY(-85px);
font-weight: bold;
">%(ylab)s</div></td>

<td>
<center><div id=%(id)sLegend></div></center>
<div id="%(id)s" style="width:%(w)s; height:%(h)s;"></div>
</td>

<td><div style="width: 150px; text-align: center; position:absolute;
 -webkit-transform: rotate(90deg) translateY(65px);
font-weight: bold;
">%(ylab2)s</div></td>

</tr></table>
<script>
$(function () {
    var conf = %(conf)s;
    if (conf.timeTicks) {
        conf.xaxis.tickFormatter = function (val, axis) {
            return val.toFixed(0)+conf.timeTicks;
        }
    }
    conf.yaxis.minTickSize = 1;
    conf.yaxis.tickFormatter = function (val, axis) {
            return val.toFixed(0);
    }
    if (conf.series.pie) {
        conf.series.pie.label.formatter = function(label, series){
            return '<div class=pielabel>'+Math.round(series.percent)+'%%</div>';
        };
    }
    $.plot($("#%(id)s"), %(data)s, conf);
});
</script>""" % dict(
    id=id, w=width, h=height,
    ylab=ylabel, ylab2=ylabel2,
    data=json.dumps(data), conf=json.dumps(conf)))

    def _limit(self):
        if self.wholeCollection:
            return ids2str([d['id'] for d in self.col.decks.all()])
        return self.col.sched._deckLimit()

    def _revlogLimit(self):
        if self.wholeCollection:
            return ""
        return ("cid in (select id from cards where did in %s)" %
                ids2str(self.col.decks.active()))

    def _title(self, title, subtitle=""):
        return '<h1>%s</h1>%s' % (title, subtitle)

    def _periodDays(self):
        if self.type == 0:
            return 30
        elif self.type == 1:
            return 365
        else:
            return None

    def _avgDay(self, tot, num, unit):
        vals = []
        try:
            vals.append(_("%(a)0.1f %(b)s/day") % dict(a=tot/float(num), b=unit))
            return ", ".join(vals)
        except ZeroDivisionError:
            return ""

########NEW FILE########
__FILENAME__ = statsbg
# from subtlepatterns.com
bg = """\
iVBORw0KGgoAAAANSUhEUgAAABIAAAANCAMAAACTkM4rAAAAM1BMVEXy8vLz8/P5+fn19fXt7e329vb4+Pj09PTv7+/u7u739/fw8PD7+/vx8fHr6+v6+vrs7Oz2LjW2AAAAkUlEQVR42g3KyXHAQAwDQYAQj12ItvOP1qqZZwMMPVnd06XToQvz4L2HDQ2iRgkvA7yPPB+JD+OUPnfzZ0JNZh6kkQus5NUmR7g4Jpxv5XN6nYWNmtlq9o3zuK6w3XRsE1pQIEGPIsdtTP3m2cYwlPv6MbL8/QASsKppZefyDmJPbxvxa/NrX1TJ1yp20fhj9D+SiAWWLU8myQAAAABJRU5ErkJggg==
"""

########NEW FILE########
__FILENAME__ = stdmodels
# -*- coding: utf-8 -*-
# Copyright: Damien Elmes <anki@ichi2.net>
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

from anki.lang import _
from anki.consts import MODEL_CLOZE

models = []

# Basic
##########################################################################

def addBasicModel(col):
    mm = col.models
    m = mm.new(_("Basic"))
    fm = mm.newField(_("Front"))
    mm.addField(m, fm)
    fm = mm.newField(_("Back"))
    mm.addField(m, fm)
    t = mm.newTemplate(_("Card 1"))
    t['qfmt'] = "{{"+_("Front")+"}}"
    t['afmt'] = "{{FrontSide}}\n\n<hr id=answer>\n\n"+"{{"+_("Back")+"}}"
    mm.addTemplate(m, t)
    mm.add(m)
    return m

models.append((lambda: _("Basic"), addBasicModel))

# Forward & Reverse
##########################################################################

def addForwardReverse(col):
    mm = col.models
    m = addBasicModel(col)
    m['name'] = _("Basic (and reversed card)")
    t = mm.newTemplate(_("Card 2"))
    t['qfmt'] = "{{"+_("Back")+"}}"
    t['afmt'] = "{{FrontSide}}\n\n<hr id=answer>\n\n"+"{{"+_("Front")+"}}"
    mm.addTemplate(m, t)
    return m

models.append((lambda: _("Forward & Reverse"), addForwardReverse))

# Forward & Optional Reverse
##########################################################################

def addForwardOptionalReverse(col):
    mm = col.models
    m = addBasicModel(col)
    m['name'] = _("Basic (optional reversed card)")
    fm = mm.newField(_("Add Reverse"))
    mm.addField(m, fm)
    t = mm.newTemplate(_("Card 2"))
    t['qfmt'] = "{{#Add Reverse}}{{"+_("Back")+"}}{{/Add Reverse}}"
    t['afmt'] = "{{FrontSide}}\n\n<hr id=answer>\n\n"+"{{"+_("Front")+"}}"
    mm.addTemplate(m, t)
    return m

models.append((lambda: _("Forward & Optional Reverse"), addForwardOptionalReverse))

# Cloze
##########################################################################

def addClozeModel(col):
    mm = col.models
    m = mm.new(_("Cloze"))
    m['type'] = MODEL_CLOZE
    txt = _("Text")
    fm = mm.newField(txt)
    mm.addField(m, fm)
    fm = mm.newField(_("Extra"))
    mm.addField(m, fm)
    t = mm.newTemplate(_("Cloze"))
    fmt = "{{cloze:%s}}" % txt
    m['css'] += """
.cloze {
 font-weight: bold;
 color: blue;
}"""
    t['qfmt'] = fmt
    t['afmt'] = fmt + "<br>\n{{%s}}" % _("Extra")
    mm.addTemplate(m, t)
    mm.add(m)
    return m

models.append((lambda: _("Cloze"), addClozeModel))

########NEW FILE########
__FILENAME__ = storage
# -*- coding: utf-8 -*-
# Copyright: Damien Elmes <anki@ichi2.net>
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

import os, copy, re
from anki.lang import _
from anki.utils import intTime, ids2str, json
from anki.db import DB
from anki.collection import _Collection
from anki.consts import *
from anki.stdmodels import addBasicModel, addClozeModel, addForwardReverse, \
    addForwardOptionalReverse

def Collection(path, lock=True, server=False, sync=True):
    "Open a new or existing collection. Path must be unicode."
    assert path.endswith(".anki2")
    path = os.path.abspath(path)
    create = not os.path.exists(path)
    if create:
        base = os.path.basename(path)
        for c in ("/", ":", "\\"):
            assert c not in base
    # connect
    db = DB(path)
    if create:
        ver = _createDB(db)
    else:
        ver = _upgradeSchema(db)
    db.execute("pragma temp_store = memory")
    if sync:
        db.execute("pragma cache_size = 10000")
        db.execute("pragma journal_mode = wal")
    else:
        db.execute("pragma synchronous = off")
    # add db to col and do any remaining upgrades
    col = _Collection(db, server)
    if ver < SCHEMA_VERSION:
        _upgrade(col, ver)
    elif create:
        # add in reverse order so basic is default
        addClozeModel(col)
        addForwardOptionalReverse(col)
        addForwardReverse(col)
        addBasicModel(col)
        col.save()
    if lock:
        col.lock()
    return col

def _upgradeSchema(db):
    ver = db.scalar("select ver from col")
    if ver == SCHEMA_VERSION:
        return ver
    # add odid to cards, edue->odue
    ######################################################################
    if db.scalar("select ver from col") == 1:
        db.execute("alter table cards rename to cards2")
        _addSchema(db, setColConf=False)
        db.execute("""
insert into cards select
id, nid, did, ord, mod, usn, type, queue, due, ivl, factor, reps, lapses,
left, edue, 0, flags, data from cards2""")
        db.execute("drop table cards2")
        db.execute("update col set ver = 2")
        _updateIndices(db)
    # remove did from notes
    ######################################################################
    if db.scalar("select ver from col") == 2:
        db.execute("alter table notes rename to notes2")
        _addSchema(db, setColConf=False)
        db.execute("""
insert into notes select
id, guid, mid, mod, usn, tags, flds, sfld, csum, flags, data from notes2""")
        db.execute("drop table notes2")
        db.execute("update col set ver = 3")
        _updateIndices(db)
    return ver

def _upgrade(col, ver):
    if ver < 3:
        # new deck properties
        for d in col.decks.all():
            d['dyn'] = 0
            d['collapsed'] = False
            col.decks.save(d)
    if ver < 4:
        col.modSchema()
        clozes = []
        for m in col.models.all():
            if not "{{cloze:" in m['tmpls'][0]['qfmt']:
                m['type'] = MODEL_STD
                col.models.save(m)
            else:
                clozes.append(m)
        for m in clozes:
            _upgradeClozeModel(col, m)
        col.db.execute("update col set ver = 4")
    if ver < 5:
        col.db.execute("update cards set odue = 0 where queue = 2")
        col.db.execute("update col set ver = 5")
    if ver < 6:
        col.modSchema()
        import anki.models
        for m in col.models.all():
            m['css'] = anki.models.defaultModel['css']
            for t in m['tmpls']:
                if 'css' not in t:
                    # ankidroid didn't bump version
                    continue
                m['css'] += "\n" + t['css'].replace(
                    ".card ", ".card%d "%(t['ord']+1))
                del t['css']
            col.models.save(m)
        col.db.execute("update col set ver = 6")
    if ver < 7:
        col.modSchema()
        col.db.execute(
            "update cards set odue = 0 where (type = 1 or queue = 2) "
            "and not odid")
        col.db.execute("update col set ver = 7")
    if ver < 8:
        col.modSchema()
        col.db.execute(
            "update cards set due = due / 1000 where due > 4294967296")
        col.db.execute("update col set ver = 8")
    if ver < 9:
        # adding an empty file to a zip makes python's zip code think it's a
        # folder, so remove any empty files
        changed = False
        dir = col.media.dir()
        if dir:
            for f in os.listdir(col.media.dir()):
                if os.path.isfile(f) and not os.path.getsize(f):
                    os.unlink(f)
                    col.media.db.execute(
                        "delete from log where fname = ?", f)
                    col.media.db.execute(
                        "delete from media where fname = ?", f)
                    changed = True
            if changed:
                col.media.db.commit()
        col.db.execute("update col set ver = 9")
    if ver < 10:
        col.db.execute("""
update cards set left = left + left*1000 where queue = 1""")
        col.db.execute("update col set ver = 10")
    if ver < 11:
        col.modSchema()
        for d in col.decks.all():
            if d['dyn']:
                order = d['order']
                # failed order was removed
                if order >= 5:
                    order -= 1
                d['terms'] = [[d['search'], d['limit'], order]]
                del d['search']
                del d['limit']
                del d['order']
                d['resched'] = True
                d['return'] = True
            else:
                if 'extendNew' not in d:
                    d['extendNew'] = 10
                    d['extendRev'] = 50
            col.decks.save(d)
        for c in col.decks.allConf():
            r = c['rev']
            r['ivlFct'] = r.get("ivlfct", 1)
            if 'ivlfct' in r:
                del r['ivlfct']
            r['maxIvl'] = 36500
            col.decks.save(c)
        for m in col.models.all():
            for t in m['tmpls']:
                t['bqfmt'] = ''
                t['bafmt'] = ''
            col.models.save(m)
        col.db.execute("update col set ver = 11")

def _upgradeClozeModel(col, m):
    m['type'] = MODEL_CLOZE
    # convert first template
    t = m['tmpls'][0]
    for type in 'qfmt', 'afmt':
        t[type] = re.sub("{{cloze:1:(.+?)}}", r"{{cloze:\1}}", t[type])
    t['name'] = _("Cloze")
    # delete non-cloze cards for the model
    rem = []
    for t in m['tmpls'][1:]:
        if "{{cloze:" not in t['qfmt']:
            rem.append(t)
    for r in rem:
        col.models.remTemplate(m, r)
    del m['tmpls'][1:]
    col.models._updateTemplOrds(m)
    col.models.save(m)

# Creating a new collection
######################################################################

def _createDB(db):
    db.execute("pragma page_size = 4096")
    db.execute("pragma legacy_file_format = 0")
    db.execute("vacuum")
    _addSchema(db)
    _updateIndices(db)
    db.execute("analyze")
    return SCHEMA_VERSION

def _addSchema(db, setColConf=True):
    db.executescript("""
create table if not exists col (
    id              integer primary key,
    crt             integer not null,
    mod             integer not null,
    scm             integer not null,
    ver             integer not null,
    dty             integer not null,
    usn             integer not null,
    ls              integer not null,
    conf            text not null,
    models          text not null,
    decks           text not null,
    dconf           text not null,
    tags            text not null
);

create table if not exists notes (
    id              integer primary key,   /* 0 */
    guid            text not null,         /* 1 */
    mid             integer not null,      /* 2 */
    mod             integer not null,      /* 3 */
    usn             integer not null,      /* 4 */
    tags            text not null,         /* 5 */
    flds            text not null,         /* 6 */
    sfld            integer not null,      /* 7 */
    csum            integer not null,      /* 8 */
    flags           integer not null,      /* 9 */
    data            text not null          /* 10 */
);

create table if not exists cards (
    id              integer primary key,   /* 0 */
    nid             integer not null,      /* 1 */
    did             integer not null,      /* 2 */
    ord             integer not null,      /* 3 */
    mod             integer not null,      /* 4 */
    usn             integer not null,      /* 5 */
    type            integer not null,      /* 6 */
    queue           integer not null,      /* 7 */
    due             integer not null,      /* 8 */
    ivl             integer not null,      /* 9 */
    factor          integer not null,      /* 10 */
    reps            integer not null,      /* 11 */
    lapses          integer not null,      /* 12 */
    left            integer not null,      /* 13 */
    odue            integer not null,      /* 14 */
    odid            integer not null,      /* 15 */
    flags           integer not null,      /* 16 */
    data            text not null          /* 17 */
);

create table if not exists revlog (
    id              integer primary key,
    cid             integer not null,
    usn             integer not null,
    ease            integer not null,
    ivl             integer not null,
    lastIvl         integer not null,
    factor          integer not null,
    time            integer not null,
    type            integer not null
);

create table if not exists graves (
    usn             integer not null,
    oid             integer not null,
    type            integer not null
);

insert or ignore into col
values(1,0,0,%(s)s,%(v)s,0,0,0,'','{}','','','{}');
""" % ({'v':SCHEMA_VERSION, 's':intTime(1000)}))
    if setColConf:
        _addColVars(db, *_getColVars(db))

def _getColVars(db):
    import anki.collection
    import anki.decks
    g = copy.deepcopy(anki.decks.defaultDeck)
    g['id'] = 1
    g['name'] = _("Default")
    g['conf'] = 1
    g['mod'] = intTime()
    gc = copy.deepcopy(anki.decks.defaultConf)
    gc['id'] = 1
    return g, gc, anki.collection.defaultConf.copy()

def _addColVars(db, g, gc, c):
    db.execute("""
update col set conf = ?, decks = ?, dconf = ?""",
                   json.dumps(c),
                   json.dumps({'1': g}),
                   json.dumps({'1': gc}))

def _updateIndices(db):
    "Add indices to the DB."
    db.executescript("""
-- syncing
create index if not exists ix_notes_usn on notes (usn);
create index if not exists ix_cards_usn on cards (usn);
create index if not exists ix_revlog_usn on revlog (usn);
-- card spacing, etc
create index if not exists ix_cards_nid on cards (nid);
-- scheduling and deck limiting
create index if not exists ix_cards_sched on cards (did, queue, due);
-- revlog by card
create index if not exists ix_revlog_cid on revlog (cid);
-- field uniqueness
create index if not exists ix_notes_csum on notes (csum);
""")

########NEW FILE########
__FILENAME__ = sync
# -*- coding: utf-8 -*-
# Copyright: Damien Elmes <anki@ichi2.net>
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

import urllib, os, sys, httplib2, gzip
from cStringIO import StringIO
from datetime import date
from anki.db import DB
from anki.errors import *
from anki.utils import ids2str, checksum, intTime, json, isWin, isMac
from anki.consts import *
from anki.lang import _
from hooks import runHook

# syncing vars
HTTP_TIMEOUT = 30
HTTP_PROXY = None

# Httplib2 connection object
######################################################################

def httpCon():
    certs = os.path.join(os.path.dirname(__file__), "ankiweb.certs")
    if not os.path.exists(certs):
        if isWin:
            certs = os.path.join(
                os.path.dirname(os.path.abspath(sys.argv[0])),
                "ankiweb.certs")
        elif isMac:
            certs = os.path.join(
                os.path.dirname(os.path.abspath(sys.argv[0])),
                "../Resources/ankiweb.certs")
        else:
            assert 0
    return httplib2.Http(
        timeout=HTTP_TIMEOUT, ca_certs=certs,
        proxy_info=HTTP_PROXY)

# Proxy handling
######################################################################

def _setupProxy():
    global HTTP_PROXY
    # set in env?
    p = httplib2.ProxyInfo.from_environment()
    if not p:
        # platform-specific fetch
        url = None
        if isWin:
            r = urllib.getproxies_registry()
            if 'https' in r:
                url = r['https']
            elif 'http' in r:
                url = r['http']
        elif isMac:
            r = urllib.getproxies_macosx_sysconf()
            if 'https' in r:
                url = r['https']
            elif 'http' in r:
                url = r['http']
        if url:
            p = httplib2.ProxyInfo.from_url(url, _proxyMethod(url))
    HTTP_PROXY = p

def _proxyMethod(url):
    if url.lower().startswith("https"):
        return "https"
    else:
        return "http"

_setupProxy()

# Incremental syncing
##########################################################################

from anki.consts import *

class Syncer(object):

    def __init__(self, col, server=None):
        self.col = col
        self.server = server

    def sync(self):
        "Returns 'noChanges', 'fullSync', or 'success'."
        # if the deck has any pending changes, flush them first and bump mod
        # time
        self.col.save()
        # step 1: login & metadata
        runHook("sync", "login")
        ret = self.server.meta()
        if not ret:
            return "badAuth"
        self.rmod, rscm, self.maxUsn, rts, self.mediaUsn = ret
        self.lmod, lscm, self.minUsn, lts, dummy = self.meta()
        if abs(rts - lts) > 300:
            return "clockOff"
        if self.lmod == self.rmod:
            return "noChanges"
        elif lscm != rscm:
            return "fullSync"
        self.lnewer = self.lmod > self.rmod
        # step 2: deletions
        runHook("sync", "meta")
        lrem = self.removed()
        rrem = self.server.start(
            minUsn=self.minUsn, lnewer=self.lnewer, graves=lrem)
        self.remove(rrem)
        # ...and small objects
        lchg = self.changes()
        rchg = self.server.applyChanges(changes=lchg)
        self.mergeChanges(lchg, rchg)
        # step 3: stream large tables from server
        runHook("sync", "server")
        while 1:
            runHook("sync", "stream")
            chunk = self.server.chunk()
            self.applyChunk(chunk=chunk)
            if chunk['done']:
                break
        # step 4: stream to server
        runHook("sync", "client")
        while 1:
            runHook("sync", "stream")
            chunk = self.chunk()
            self.server.applyChunk(chunk=chunk)
            if chunk['done']:
                break
        # step 5: sanity check during beta testing
        runHook("sync", "sanity")
        c = self.sanityCheck()
        s = self.server.sanityCheck()
        if c != s:
            raise Exception("""\
Sanity check failed. Please copy and paste the text below:\n%s\n%s""" % (c, s))
        # finalize
        runHook("sync", "finalize")
        mod = self.server.finish()
        self.finish(mod)
        return "success"

    def meta(self):
        return (self.col.mod, self.col.scm, self.col._usn, intTime(), None)

    def changes(self):
        "Bundle up small objects."
        d = dict(models=self.getModels(),
                 decks=self.getDecks(),
                 tags=self.getTags())
        if self.lnewer:
            d['conf'] = self.getConf()
            d['crt'] = self.col.crt
        return d

    def applyChanges(self, changes):
        self.rchg = changes
        lchg = self.changes()
        # merge our side before returning
        self.mergeChanges(lchg, self.rchg)
        return lchg

    def mergeChanges(self, lchg, rchg):
        # then the other objects
        self.mergeModels(rchg['models'])
        self.mergeDecks(rchg['decks'])
        self.mergeTags(rchg['tags'])
        if 'conf' in rchg:
            self.mergeConf(rchg['conf'])
        # this was left out of earlier betas
        if 'crt' in rchg:
            self.col.crt = rchg['crt']
        self.prepareToChunk()

    def sanityCheck(self):
        # some basic checks to ensure the sync went ok. this is slow, so will
        # be removed before official release
        assert not self.col.db.scalar("""
select count() from cards where nid not in (select id from notes)""")
        assert not self.col.db.scalar("""
select count() from notes where id not in (select distinct nid from cards)""")
        for t in "cards", "notes", "revlog", "graves":
            assert not self.col.db.scalar(
                "select count() from %s where usn = -1" % t)
        for g in self.col.decks.all():
            assert g['usn'] != -1
        for t, usn in self.col.tags.allItems():
            assert usn != -1
        found = False
        for m in self.col.models.all():
            if self.col.server:
                # the web upgrade was mistakenly setting usn
                if m['usn'] < 0:
                    m['usn'] = 0
                    found = True
            else:
                assert m['usn'] != -1
        if found:
            self.col.models.save()
        self.col.sched.reset()
        # check for missing parent decks
        self.col.sched.deckDueList()
        # return summary of deck
        return [
            list(self.col.sched.counts()),
            self.col.db.scalar("select count() from cards"),
            self.col.db.scalar("select count() from notes"),
            self.col.db.scalar("select count() from revlog"),
            self.col.db.scalar("select count() from graves"),
            len(self.col.models.all()),
            len(self.col.decks.all()),
            len(self.col.decks.allConf()),
        ]

    def usnLim(self):
        if self.col.server:
            return "usn >= %d" % self.minUsn
        else:
            return "usn = -1"

    def finish(self, mod=None):
        if not mod:
            # server side; we decide new mod time
            mod = intTime(1000)
        self.col.ls = mod
        self.col._usn = self.maxUsn + 1
        # ensure we save the mod time even if no changes made
        self.col.db.mod = True
        self.col.save(mod=mod)
        return mod

    # Chunked syncing
    ##########################################################################

    def prepareToChunk(self):
        self.tablesLeft = ["revlog", "cards", "notes"]
        self.cursor = None

    def cursorForTable(self, table):
        lim = self.usnLim()
        x = self.col.db.execute
        d = (self.maxUsn, lim)
        if table == "revlog":
            return x("""
select id, cid, %d, ease, ivl, lastIvl, factor, time, type
from revlog where %s""" % d)
        elif table == "cards":
            return x("""
select id, nid, did, ord, mod, %d, type, queue, due, ivl, factor, reps,
lapses, left, odue, odid, flags, data from cards where %s""" % d)
        else:
            return x("""
select id, guid, mid, mod, %d, tags, flds, '', '', flags, data
from notes where %s""" % d)

    def chunk(self):
        buf = dict(done=False)
        lim = 2500
        while self.tablesLeft and lim:
            curTable = self.tablesLeft[0]
            if not self.cursor:
                self.cursor = self.cursorForTable(curTable)
            rows = self.cursor.fetchmany(lim)
            fetched = len(rows)
            if fetched != lim:
                # table is empty
                self.tablesLeft.pop(0)
                self.cursor = None
                # if we're the client, mark the objects as having been sent
                if not self.col.server:
                    self.col.db.execute(
                        "update %s set usn=? where usn=-1"%curTable,
                        self.maxUsn)
            buf[curTable] = rows
            lim -= fetched
        if not self.tablesLeft:
            buf['done'] = True
        return buf

    def applyChunk(self, chunk):
        if "revlog" in chunk:
            self.mergeRevlog(chunk['revlog'])
        if "cards" in chunk:
            self.mergeCards(chunk['cards'])
        if "notes" in chunk:
            self.mergeNotes(chunk['notes'])

    # Deletions
    ##########################################################################

    def removed(self):
        cards = []
        notes = []
        decks = []
        if self.col.server:
            curs = self.col.db.execute(
                "select oid, type from graves where usn >= ?", self.minUsn)
        else:
            curs = self.col.db.execute(
                "select oid, type from graves where usn = -1")
        for oid, type in curs:
            if type == REM_CARD:
                cards.append(oid)
            elif type == REM_NOTE:
                notes.append(oid)
            else:
                decks.append(oid)
        if not self.col.server:
            self.col.db.execute("update graves set usn=? where usn=-1",
                                 self.maxUsn)
        return dict(cards=cards, notes=notes, decks=decks)

    def start(self, minUsn, lnewer, graves):
        self.maxUsn = self.col._usn
        self.minUsn = minUsn
        self.lnewer = not lnewer
        lgraves = self.removed()
        self.remove(graves)
        return lgraves

    def remove(self, graves):
        # pretend to be the server so we don't set usn = -1
        wasServer = self.col.server
        self.col.server = True
        # notes first, so we don't end up with duplicate graves
        self.col._remNotes(graves['notes'])
        # then cards
        self.col.remCards(graves['cards'], notes=False)
        # and decks
        for oid in graves['decks']:
            self.col.decks.rem(oid, childrenToo=False)
        self.col.server = wasServer

    # Models
    ##########################################################################

    def getModels(self):
        if self.col.server:
            return [m for m in self.col.models.all() if m['usn'] >= self.minUsn]
        else:
            mods = [m for m in self.col.models.all() if m['usn'] == -1]
            for m in mods:
                m['usn'] = self.maxUsn
            self.col.models.save()
            return mods

    def mergeModels(self, rchg):
        for r in rchg:
            l = self.col.models.get(r['id'])
            # if missing locally or server is newer, update
            if not l or r['mod'] > l['mod']:
                self.col.models.update(r)

    # Decks
    ##########################################################################

    def getDecks(self):
        if self.col.server:
            return [
                [g for g in self.col.decks.all() if g['usn'] >= self.minUsn],
                [g for g in self.col.decks.allConf() if g['usn'] >= self.minUsn]
            ]
        else:
            decks = [g for g in self.col.decks.all() if g['usn'] == -1]
            for g in decks:
                g['usn'] = self.maxUsn
            dconf = [g for g in self.col.decks.allConf() if g['usn'] == -1]
            for g in dconf:
                g['usn'] = self.maxUsn
            self.col.decks.save()
            return [decks, dconf]

    def mergeDecks(self, rchg):
        for r in rchg[0]:
            l = self.col.decks.get(r['id'], False)
            # if missing locally or server is newer, update
            if not l or r['mod'] > l['mod']:
                self.col.decks.update(r)
        for r in rchg[1]:
            try:
                l = self.col.decks.getConf(r['id'])
            except KeyError:
                l = None
            # if missing locally or server is newer, update
            if not l or r['mod'] > l['mod']:
                self.col.decks.updateConf(r)

    # Tags
    ##########################################################################

    def getTags(self):
        if self.col.server:
            return [t for t, usn in self.col.tags.allItems()
                    if usn >= self.minUsn]
        else:
            tags = []
            for t, usn in self.col.tags.allItems():
                if usn == -1:
                    self.col.tags.tags[t] = self.maxUsn
                    tags.append(t)
            self.col.tags.save()
            return tags

    def mergeTags(self, tags):
        self.col.tags.register(tags, usn=self.maxUsn)

    # Cards/notes/revlog
    ##########################################################################

    def mergeRevlog(self, logs):
        self.col.db.executemany(
            "insert or ignore into revlog values (?,?,?,?,?,?,?,?,?)",
            logs)

    def newerRows(self, data, table, modIdx):
        ids = (r[0] for r in data)
        lmods = {}
        for id, mod in self.col.db.execute(
            "select id, mod from %s where id in %s and %s" % (
                table, ids2str(ids), self.usnLim())):
            lmods[id] = mod
        update = []
        for r in data:
            if r[0] not in lmods or lmods[r[0]] < r[modIdx]:
                update.append(r)
        return update

    def mergeCards(self, cards):
        self.col.db.executemany(
            "insert or replace into cards values "
            "(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            self.newerRows(cards, "cards", 4))

    def mergeNotes(self, notes):
        rows = self.newerRows(notes, "notes", 4)
        self.col.db.executemany(
            "insert or replace into notes values (?,?,?,?,?,?,?,?,?,?,?)",
            rows)
        self.col.updateFieldCache([f[0] for f in rows])

    # Col config
    ##########################################################################

    def getConf(self):
        return self.col.conf

    def mergeConf(self, conf):
        self.col.conf = conf

# Local syncing for unit tests
##########################################################################

class LocalServer(Syncer):

    # serialize/deserialize payload, so we don't end up sharing objects
    # between cols
    def applyChanges(self, changes):
        l = json.loads; d = json.dumps
        return l(d(Syncer.applyChanges(self, l(d(changes)))))

# HTTP syncing tools
##########################################################################

# Calling code should catch the following codes:
# - 501: client needs upgrade
# - 502: ankiweb down
# - 503/504: server too busy

class HttpSyncer(object):

    def __init__(self, hkey=None, con=None):
        self.hkey = hkey
        self.con = con or httpCon()

    def assertOk(self, resp):
        if resp['status'] != '200':
            raise Exception("Unknown response code: %s" % resp['status'])

    # Posting data as a file
    ######################################################################
    # We don't want to post the payload as a form var, as the percent-encoding is
    # costly. We could send it as a raw post, but more HTTP clients seem to
    # support file uploading, so this is the more compatible choice.

    def req(self, method, fobj=None, comp=6,
                 badAuthRaises=True, hkey=True):
        BOUNDARY="Anki-sync-boundary"
        bdry = "--"+BOUNDARY
        buf = StringIO()
        # compression flag and session key as post vars
        vars = {}
        vars['c'] = 1 if comp else 0
        if hkey:
            vars['k'] = self.hkey
        for (key, value) in vars.items():
            buf.write(bdry + "\r\n")
            buf.write(
                'Content-Disposition: form-data; name="%s"\r\n\r\n%s\r\n' %
                (key, value))
        # payload as raw data or json
        if fobj:
            # header
            buf.write(bdry + "\r\n")
            buf.write("""\
Content-Disposition: form-data; name="data"; filename="data"\r\n\
Content-Type: application/octet-stream\r\n\r\n""")
            # write file into buffer, optionally compressing
            if comp:
                tgt = gzip.GzipFile(mode="wb", fileobj=buf, compresslevel=comp)
            else:
                tgt = buf
            while 1:
                data = fobj.read(65536)
                if not data:
                    if comp:
                        tgt.close()
                    break
                tgt.write(data)
            buf.write('\r\n' + bdry + '--\r\n')
        size = buf.tell()
        # connection headers
        headers = {
            'Content-Type': 'multipart/form-data; boundary=%s' % BOUNDARY,
            'Content-Length': str(size),
        }
        body = buf.getvalue()
        buf.close()
        resp, cont = self.con.request(
            SYNC_URL+method, "POST", headers=headers, body=body)
        if not badAuthRaises:
            # return false if bad auth instead of raising
            if resp['status'] == '403':
                return False
        self.assertOk(resp)
        return cont

# Incremental sync over HTTP
######################################################################

class RemoteServer(HttpSyncer):

    def __init__(self, hkey):
        HttpSyncer.__init__(self, hkey)

    def hostKey(self, user, pw):
        "Returns hkey or none if user/pw incorrect."
        ret = self.req(
            "hostKey", StringIO(json.dumps(dict(u=user, p=pw))),
            badAuthRaises=False, hkey=False)
        if not ret:
            # invalid auth
            return
        self.hkey = json.loads(ret)['key']
        return self.hkey

    def meta(self):
        ret = self.req(
            "meta", StringIO(json.dumps(dict(v=SYNC_VER))),
            badAuthRaises=False)
        if not ret:
            # invalid auth
            return
        return json.loads(ret)

    def applyChanges(self, **kw):
        return self._run("applyChanges", kw)

    def start(self, **kw):
        return self._run("start", kw)

    def chunk(self, **kw):
        return self._run("chunk", kw)

    def applyChunk(self, **kw):
        return self._run("applyChunk", kw)

    def sanityCheck(self, **kw):
        return self._run("sanityCheck", kw)

    def finish(self, **kw):
        return self._run("finish", kw)

    def _run(self, cmd, data):
        return json.loads(
            self.req(cmd, StringIO(json.dumps(data))))

# Full syncing
##########################################################################

class FullSyncer(HttpSyncer):

    def __init__(self, col, hkey, con):
        HttpSyncer.__init__(self, hkey, con)
        self.col = col

    def download(self):
        runHook("sync", "download")
        self.col.close()
        cont = self.req("download")
        tpath = self.col.path + ".tmp"
        if cont == "upgradeRequired":
            runHook("sync", "upgradeRequired")
            return
        open(tpath, "wb").write(cont)
        # check the received file is ok
        d = DB(tpath)
        assert d.scalar("pragma integrity_check") == "ok"
        d.close()
        # overwrite existing collection
        os.unlink(self.col.path)
        os.rename(tpath, self.col.path)
        self.col = None

    def upload(self):
        runHook("sync", "upload")
        # make sure it's ok before we try to upload
        assert self.col.db.scalar("pragma integrity_check") == "ok"
        # apply some adjustments, then upload
        self.col.beforeUpload()
        assert self.req("upload", open(self.col.path, "rb")) == "OK"

# Media syncing
##########################################################################

class MediaSyncer(object):

    def __init__(self, col, server=None):
        self.col = col
        self.server = server
        self.added = None

    def sync(self, mediaUsn):
        # step 1: check if there have been any changes
        runHook("sync", "findMedia")
        self.col.media.findChanges()
        lusn = self.col.media.usn()
        if lusn == mediaUsn and not self.col.media.hasChanged():
            return "noChanges"
        # step 2: send/recv deletions
        runHook("sync", "removeMedia")
        lrem = self.removed()
        rrem = self.server.remove(fnames=lrem, minUsn=lusn)
        self.remove(rrem)
        # step 3: stream files from server
        runHook("sync", "server")
        while 1:
            runHook("sync", "streamMedia")
            usn = self.col.media.usn()
            zip = self.server.files(minUsn=usn)
            if self.addFiles(zip=zip):
                break
        # step 4: stream files to the server
        runHook("sync", "client")
        while 1:
            runHook("sync", "streamMedia")
            zip, fnames = self.files()
            if not fnames:
                # finished
                break
            usn = self.server.addFiles(zip=zip)
            # after server has replied, safe to remove from log
            self.col.media.forgetAdded(fnames)
            self.col.media.setUsn(usn)
        # step 5: sanity check during beta testing
        # NOTE: when removing this, need to move server tidyup
        # back from sanity check to addFiles
        s = self.server.mediaSanity()
        c = self.mediaSanity()
        if c != s:
            raise Exception("""\
Media sanity check failed. Please copy and paste the text below:\n%s\n%s""" %
                            (c, s))
        return "success"

    def removed(self):
        return self.col.media.removed()

    def remove(self, fnames, minUsn=None):
        self.col.media.syncRemove(fnames)
        if minUsn is not None:
            # we're the server
            return self.col.media.removed()

    def files(self):
        return self.col.media.zipAdded()

    def addFiles(self, zip):
        "True if zip is the last in set. Server returns new usn instead."
        return self.col.media.syncAdd(zip)

    def mediaSanity(self):
        return self.col.media.sanityCheck()

# Remote media syncing
##########################################################################

class RemoteMediaServer(HttpSyncer):

    def __init__(self, hkey, con):
        HttpSyncer.__init__(self, hkey, con)

    def remove(self, **kw):
        return json.loads(
            self.req("remove", StringIO(json.dumps(kw))))

    def files(self, **kw):
        return self.req("files", StringIO(json.dumps(kw)))

    def addFiles(self, zip):
        # no compression, as we compress the zip file instead
        return json.loads(
            self.req("addFiles", StringIO(zip), comp=0))

    def mediaSanity(self):
        return json.loads(
            self.req("mediaSanity"))

    # only for unit tests
    def mediatest(self, n):
        return json.loads(
            self.req("mediatest", StringIO(
                json.dumps(dict(n=n)))))

########NEW FILE########
__FILENAME__ = tags
# -*- coding: utf-8 -*-
# Copyright: Damien Elmes <anki@ichi2.net>
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

from anki.utils import intTime, ids2str, json
from anki.hooks import runHook

"""
Anki maintains a cache of used tags so it can quickly present a list of tags
for autocomplete and in the browser. For efficiency, deletions are not
tracked, so unused tags can only be removed from the list with a DB check.

This module manages the tag cache and tags for notes.
"""

class TagManager(object):

    # Registry save/load
    #############################################################

    def __init__(self, col):
        self.col = col

    def load(self, json_):
        self.tags = json.loads(json_)
        self.changed = False

    def flush(self):
        if self.changed:
            self.col.db.execute("update col set tags=?",
                                 json.dumps(self.tags))
            self.changed = False

    # Registering and fetching tags
    #############################################################

    def register(self, tags, usn=None):
        "Given a list of tags, add any missing ones to tag registry."
        # case is stored as received, so user can create different case
        # versions of the same tag if they ignore the qt autocomplete.
        found = False
        for t in tags:
            if t not in self.tags:
                found = True
                self.tags[t] = self.col.usn() if usn is None else usn
                self.changed = True
        if found:
            runHook("newTag")

    def all(self):
        return self.tags.keys()

    def registerNotes(self, nids=None):
        "Add any missing tags from notes to the tags list."
        # when called without an argument, the old list is cleared first.
        if nids:
            lim = " where id in " + ids2str(nids)
        else:
            lim = ""
            self.tags = {}
            self.changed = True
        self.register(set(self.split(
            " ".join(self.col.db.list("select distinct tags from notes"+lim)))))

    def allItems(self):
        return self.tags.items()

    def save(self):
        self.changed = True

    # Bulk addition/removal from notes
    #############################################################

    def bulkAdd(self, ids, tags, add=True):
        "Add tags in bulk. TAGS is space-separated."
        newTags = self.split(tags)
        if not newTags:
            return
        # cache tag names
        self.register(newTags)
        # find notes missing the tags
        if add:
            l = "tags not "
            fn = self.addToStr
        else:
            l = "tags "
            fn = self.remFromStr
        lim = " or ".join(
            [l+"like :_%d" % c for c, t in enumerate(newTags)])
        res = self.col.db.all(
            "select id, tags from notes where id in %s and (%s)" % (
                ids2str(ids), lim),
            **dict([("_%d" % x, '%% %s %%' % y)
                    for x, y in enumerate(newTags)]))
        # update tags
        nids = []
        def fix(row):
            nids.append(row[0])
            return {'id': row[0], 't': fn(tags, row[1]), 'n':intTime(),
                'u':self.col.usn()}
        self.col.db.executemany(
            "update notes set tags=:t,mod=:n,usn=:u where id = :id",
            [fix(row) for row in res])

    def bulkRem(self, ids, tags):
        self.bulkAdd(ids, tags, False)

    # String-based utilities
    ##########################################################################

    def split(self, tags):
        "Parse a string and return a list of tags."
        return [t for t in tags.split(" ") if t]

    def join(self, tags):
        "Join tags into a single string, with leading and trailing spaces."
        if not tags:
            return u""
        return u" %s " % u" ".join(tags)

    def addToStr(self, addtags, tags):
        "Add tags if they don't exist, and canonify."
        currentTags = self.split(tags)
        for tag in self.split(addtags):
            if not self.inList(tag, currentTags):
                currentTags.append(tag)
        return self.join(self.canonify(currentTags))

    def remFromStr(self, deltags, tags):
        "Delete tags if they don't exists."
        currentTags = self.split(tags)
        for tag in self.split(deltags):
            # find tags, ignoring case
            remove = []
            for tx in currentTags:
                if tag.lower() == tx.lower():
                    remove.append(tx)
            # remove them
            for r in remove:
                currentTags.remove(r)
        return self.join(currentTags)

    # List-based utilities
    ##########################################################################

    def canonify(self, tagList):
        "Strip duplicates and sort."
        return sorted(set(tagList))

    def inList(self, tag, tags):
        "True if TAG is in TAGS. Ignore case."
        return tag.lower() in [t.lower() for t in tags]

    # Sync handling
    ##########################################################################

    def beforeUpload(self):
        for k in self.tags.keys():
            self.tags[k] = 0
        self.save()

########NEW FILE########
__FILENAME__ = furigana
# -*- coding: utf-8 -*-
# Copyright: Damien Elmes <anki@ichi2.net>
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html
# Based off Kieran Clancy's initial implementation.

import re
from anki.hooks import addHook

r = r' ?([^ >]+?)\[(.+?)\]'
ruby = r'<ruby><rb>\1</rb><rt>\2</rt></ruby>'

def noSound(repl):
    def func(match):
        if match.group(2).startswith("sound:"):
            # return without modification
            return match.group(0)
        else:
            return re.sub(r, repl, match.group(0))
    return func

def kanji(txt, *args):
    return re.sub(r, noSound(r'\1'), txt)

def kana(txt, *args):
    return re.sub(r, noSound(r'\2'), txt)

def furigana(txt, *args):
    return re.sub(r, noSound(ruby), txt)

def install():
    addHook('fmod_kanji', kanji)
    addHook('fmod_kana', kana)
    addHook('fmod_furigana', furigana)

########NEW FILE########
__FILENAME__ = hint
# -*- coding: utf-8 -*-
# Copyright: Damien Elmes <anki@ichi2.net>
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

import re
from anki.hooks import addHook
from anki.lang import _

def hint(txt, extra, context, tag, fullname):
    if not txt.strip():
        return ""
    # random id
    domid = "hint%d" % id(txt)
    return """
<a class=hint href="#"
onclick="this.style.display='none';document.getElementById('%s').style.display='block';return false;">
%s</a><div id="%s" class=hint style="display: none">%s</div>
""" % (domid, _("Show %s") % tag, domid, txt)

def install():
    addHook('fmod_hint', hint)

########NEW FILE########
__FILENAME__ = template
import re
import cgi
import collections
from anki.utils import stripHTML
from anki.hooks import runFilter
from anki.template import furigana; furigana.install()
from anki.template import hint; hint.install()
from anki.lang import _

clozeReg = r"\{\{c%s::(.*?)(::(.*?))?\}\}"

modifiers = {}
def modifier(symbol):
    """Decorator for associating a function with a Mustache tag modifier.

    @modifier('P')
    def render_tongue(self, tag_name=None, context=None):
        return ":P %s" % tag_name

    {{P yo }} => :P yo
    """
    def set_modifier(func):
        modifiers[symbol] = func
        return func
    return set_modifier


def get_or_attr(obj, name, default=None):
    try:
        return obj[name]
    except KeyError:
        return default
    except:
        try:
            return getattr(obj, name)
        except AttributeError:
            return default


class Template(object):
    # The regular expression used to find a #section
    section_re = None

    # The regular expression used to find a tag.
    tag_re = None

    # Opening tag delimiter
    otag = '{{'

    # Closing tag delimiter
    ctag = '}}'

    def __init__(self, template, context=None):
        self.template = template
        self.context = context or {}
        self.compile_regexps()

    def render(self, template=None, context=None, encoding=None):
        """Turns a Mustache template into something wonderful."""
        template = template or self.template
        context = context or self.context

        template = self.render_sections(template, context)
        result = self.render_tags(template, context)
        if encoding is not None:
            result = result.encode(encoding)
        return result

    def compile_regexps(self):
        """Compiles our section and tag regular expressions."""
        tags = { 'otag': re.escape(self.otag), 'ctag': re.escape(self.ctag) }

        section = r"%(otag)s[\#|^]([^\}]*)%(ctag)s(.+?)%(otag)s/\1%(ctag)s"
        self.section_re = re.compile(section % tags, re.M|re.S)

        tag = r"%(otag)s(#|=|&|!|>|\{)?(.+?)\1?%(ctag)s+"
        self.tag_re = re.compile(tag % tags)

    def render_sections(self, template, context):
        """Expands sections."""
        while 1:
            match = self.section_re.search(template)
            if match is None:
                break

            section, section_name, inner = match.group(0, 1, 2)
            section_name = section_name.strip()

            # check for cloze
            m = re.match("c[qa]:(\d+):(.+)", section_name)
            if m:
                # get full field text
                txt = get_or_attr(context, m.group(2), None)
                m = re.search(clozeReg%m.group(1), txt)
                if m:
                    it = m.group(1)
                else:
                    it = None
            else:
                it = get_or_attr(context, section_name, None)

            replacer = ''
            # if it and isinstance(it, collections.Callable):
            #     replacer = it(inner)
            if it and not hasattr(it, '__iter__'):
                if section[2] != '^':
                    replacer = inner
            elif it and hasattr(it, 'keys') and hasattr(it, '__getitem__'):
                if section[2] != '^':
                    replacer = self.render(inner, it)
            elif it:
                insides = []
                for item in it:
                    insides.append(self.render(inner, item))
                replacer = ''.join(insides)
            elif not it and section[2] == '^':
                replacer = inner

            template = template.replace(section, replacer)

        return template

    def render_tags(self, template, context):
        """Renders all the tags in a template for a context."""
        while 1:
            match = self.tag_re.search(template)
            if match is None:
                break

            tag, tag_type, tag_name = match.group(0, 1, 2)
            tag_name = tag_name.strip()
            try:
                func = modifiers[tag_type]
                replacement = func(self, tag_name, context)
                template = template.replace(tag, replacement)
            except (SyntaxError, KeyError):
                return u"{{invalid template}}"

        return template

    # {{{ functions just like {{ in anki
    @modifier('{')
    def render_tag(self, tag_name, context):
        return self.render_unescaped(tag_name, context)

    @modifier('!')
    def render_comment(self, tag_name=None, context=None):
        """Rendering a comment always returns nothing."""
        return ''

    @modifier(None)
    def render_unescaped(self, tag_name=None, context=None):
        """Render a tag without escaping it."""
        txt = get_or_attr(context, tag_name)
        if txt is not None:
            # some field names could have colons in them
            # avoid interpreting these as field modifiers
            # better would probably be to put some restrictions on field names
            return txt

        # field modifiers
        parts = tag_name.split(':',2)
        extra = None
        if len(parts) == 1 or parts[0] == '':
            return '{unknown field %s}' % tag_name
        elif len(parts) == 2:
            (mod, tag) = parts
        elif len(parts) == 3:
            (mod, extra, tag) = parts

        txt = get_or_attr(context, tag)

        # built-in modifiers
        if mod == 'text':
            # strip html
            if txt:
                return stripHTML(txt)
            return ""
        elif mod == 'type':
            # type answer field; convert it to [[type:...]] for the gui code
            # to process
            return "[[%s]]" % tag_name
        elif mod == 'cq' or mod == 'ca':
            # cloze deletion
            if txt and extra:
                return self.clozeText(txt, extra, mod[1])
            else:
                return ""
        else:
            # hook-based field modifier
            txt = runFilter('fmod_' + mod, txt or '', extra, context,
                            tag, tag_name);
            if txt is None:
                return '{unknown field %s}' % tag_name
            return txt

    def clozeText(self, txt, ord, type):
        reg = clozeReg
        if not re.search(reg%ord, txt):
            return ""
        def repl(m):
            # replace chosen cloze with type
            if type == "q":
                if m.group(3):
                    return "<span class=cloze>[%s]</span>" % m.group(3)
                else:
                    return "<span class=cloze>[...]</span>"
            else:
                return "<span class=cloze>%s</span>" % m.group(1)
        txt = re.sub(reg%ord, repl, txt)
        # and display other clozes normally
        return re.sub(reg%".*?", "\\1", txt)

    @modifier('=')
    def render_delimiter(self, tag_name=None, context=None):
        """Changes the Mustache delimiter."""
        try:
            self.otag, self.ctag = tag_name.split(' ')
        except ValueError:
            # invalid
            return
        self.compile_regexps()
        return ''

########NEW FILE########
__FILENAME__ = view
from anki.template import Template
import os.path
import re

class View(object):
    # Path where this view's template(s) live
    template_path = '.'

    # Extension for templates
    template_extension = 'mustache'

    # The name of this template. If none is given the View will try
    # to infer it based on the class name.
    template_name = None

    # Absolute path to the template itself. Pystache will try to guess
    # if it's not provided.
    template_file = None

    # Contents of the template.
    template = None

    # Character encoding of the template file. If None, Pystache will not
    # do any decoding of the template.
    template_encoding = None

    def __init__(self, template=None, context=None, **kwargs):
        self.template = template
        self.context = context or {}

        # If the context we're handed is a View, we want to inherit
        # its settings.
        if isinstance(context, View):
            self.inherit_settings(context)

        if kwargs:
            self.context.update(kwargs)

    def inherit_settings(self, view):
        """Given another View, copies its settings."""
        if view.template_path:
            self.template_path = view.template_path

        if view.template_name:
            self.template_name = view.template_name

    def load_template(self):
        if self.template:
            return self.template

        if self.template_file:
            return self._load_template()

        name = self.get_template_name() + '.' + self.template_extension

        if isinstance(self.template_path, basestring):
            self.template_file = os.path.join(self.template_path, name)
            return self._load_template()

        for path in self.template_path:
            self.template_file = os.path.join(path, name)
            if os.path.exists(self.template_file):
                return self._load_template()

        raise IOError('"%s" not found in "%s"' % (name, ':'.join(self.template_path),))


    def _load_template(self):
        f = open(self.template_file, 'r')
        try:
            template = f.read()
            if self.template_encoding:
                template = unicode(template, self.template_encoding)
        finally:
            f.close()
        return template

    def get_template_name(self, name=None):
        """TemplatePartial => template_partial
        Takes a string but defaults to using the current class' name or
        the `template_name` attribute
        """
        if self.template_name:
            return self.template_name

        if not name:
            name = self.__class__.__name__

        def repl(match):
            return '_' + match.group(0).lower()

        return re.sub('[A-Z]', repl, name)[1:]

    def __contains__(self, needle):
        return needle in self.context or hasattr(self, needle)

    def __getitem__(self, attr):
        val = self.get(attr, None)
        if not val:
            raise KeyError("No such key.")
        return val

    def get(self, attr, default):
        attr = self.context.get(attr, getattr(self, attr, default))

        if hasattr(attr, '__call__'):
            return attr()
        else:
            return attr

    def render(self, encoding=None):
        template = self.load_template()
        return Template(template, self).render(encoding=encoding)

    def __str__(self):
        return self.render()

########NEW FILE########
__FILENAME__ = upgrade
# -*- coding: utf-8 -*-
# Copyright: Damien Elmes <anki@ichi2.net>
# License: GNU AGPL, version 3 or later; http://www.gnu.org/copyleft/agpl.html

import os, time, re, datetime, shutil
from anki.lang import _
from anki.utils import intTime, tmpfile, ids2str, splitFields, base91, json
from anki.db import DB
from anki.collection import _Collection
from anki.consts import *
from anki.storage import _addSchema, _getColVars, _addColVars, \
    _updateIndices

#
# Upgrading is the first step in migrating to 2.0.
# Caller should have called check() on path before calling upgrade().
#

class Upgrader(object):

    def __init__(self):
        pass

    # Upgrading
    ######################################################################

    def upgrade(self, path):
        self.path = path
        self._openDB(path)
        self._upgradeSchema()
        self._openCol()
        self._upgradeRest()
        return self.col

    # Integrity checking
    ######################################################################

    def check(self, path):
        "True if deck looks ok."
        with DB(path) as db:
            return self._check(db)

    def _check(self, db):
        # corrupt?
        try:
            if db.scalar("pragma integrity_check") != "ok":
                return
        except:
            return
        # old version?
        if db.scalar("select version from decks") < 65:
            return
        # ensure we have indices for checks below
        db.executescript("""
create index if not exists ix_cards_factId on cards (factId);
create index if not exists ix_fields_factId on fieldModels (factId);
analyze;""")
        # fields missing a field model?
        if db.list("""
select id from fields where fieldModelId not in (
select distinct id from fieldModels)"""):
            return
        # facts missing a field?
        if db.list("""
select distinct facts.id from facts, fieldModels where
facts.modelId = fieldModels.modelId and fieldModels.id not in
(select fieldModelId from fields where factId = facts.id)"""):
            return
        # cards missing a fact?
        if db.list("""
select id from cards where factId not in (select id from facts)"""):
            return
        # cards missing a card model?
        if db.list("""
select id from cards where cardModelId not in
(select id from cardModels)"""):
            return
        # cards with a card model from the wrong model?
        if db.list("""
select id from cards where cardModelId not in (select cm.id from
cardModels cm, facts f where cm.modelId = f.modelId and
f.id = cards.factId)"""):
            return
        # facts missing a card?
        if db.list("""
    select facts.id from facts
    where facts.id not in (select distinct factId from cards)"""):
            return
        # dangling fields?
        if db.list("""
    select id from fields where factId not in (select id from facts)"""):
            return
        # incorrect types
        if db.list("""
    select id from cards where relativeDelay != (case
    when successive then 1 when reps then 0 else 2 end)"""):
            return
        if db.list("""
    select id from cards where type != (case
    when type >= 0 then relativeDelay else relativeDelay - 3 end)"""):
            return
        return True

    # DB/Deck opening
    ######################################################################

    def _openDB(self, path):
        self.tmppath = tmpfile(suffix=".anki2")
        shutil.copy(path, self.tmppath)
        self.db = DB(self.tmppath)

    def _openCol(self):
        self.col = _Collection(self.db)

    # Schema upgrade
    ######################################################################

    def _upgradeSchema(self):
        "Alter tables prior to ORM initialization."
        db = self.db
        # speed up the upgrade
        db.execute("pragma temp_store = memory")
        db.execute("pragma cache_size = 10000")
        db.execute("pragma synchronous = off")
        # these weren't always correctly set
        db.execute("pragma page_size = 4096")
        db.execute("pragma legacy_file_format = 0")

        for mid in db.list("select id from models"):
            # ensure the ordinals are correct for each cardModel
            for c, cmid in enumerate(db.list(
                "select id from cardModels where modelId = ? order by ordinal",
                mid)):
                db.execute("update cardModels set ordinal = ? where id = ?",
                           c, cmid)
            # and fieldModel
            for c, fmid in enumerate(db.list(
                "select id from fieldModels where modelId = ? order by ordinal",
                mid)):
                db.execute("update fieldModels set ordinal = ? where id = ?",
                           c, fmid)
        # then fix ordinals numbers on cards & fields
        db.execute("""update cards set ordinal = (select ordinal from
cardModels where cardModels.id = cardModelId)""")
        db.execute("""update fields set ordinal = (select ordinal from
fieldModels where id = fieldModelId)""")

        # notes
        ###########
        # tags should have a leading and trailing space if not empty, and not
        # use commas
        db.execute("""
update facts set tags = (case
when trim(tags) == "" then ""
else " " || replace(replace(trim(tags), ",", " "), "  ", " ") || " "
end)
""")
        # pull facts into memory, so we can merge them with fields efficiently
        facts = db.all("""
select id, id, modelId, cast(created*1000 as int), cast(modified as int),
0, tags from facts order by created""")
        # build field hash
        fields = {}
        for (fid, ord, val) in db.execute(
            "select factId, ordinal, value from fields order by factId, ordinal"):
            if fid not in fields:
                fields[fid] = []
            val = self._mungeField(val)
            fields[fid].append((ord, val))
        # build insert data and transform ids, and minimize qt's
        # bold/italics/underline cruft.
        map = {}
        data = []
        factidmap = {}
        from anki.utils import minimizeHTML
        highest = 0
        for c, row in enumerate(facts):
            oldid = row[0]
            row = list(row)
            if row[3] <= highest:
                highest = max(highest, row[3]) + 1
                row[3] = highest
            else:
                highest = row[3]
            factidmap[row[0]] = row[3]
            row[0] = row[3]
            del row[3]
            map[oldid] = row[0]
            # convert old 64bit id into a string, discarding sign bit
            row[1] = base91(abs(row[1]))
            row.append(minimizeHTML("\x1f".join([x[1] for x in sorted(fields[oldid])])))
            data.append(row)
        # and put the facts into the new table
        db.execute("drop table facts")
        _addSchema(db, False)
        db.executemany("insert into notes values (?,?,?,?,?,?,?,'','',0,'')", data)
        db.execute("drop table fields")

        # cards
        ###########
        # we need to pull this into memory, to rewrite the creation time if
        # it's not unique and update the fact id
        rows = []
        cardidmap = {}
        highest = 0
        for row in db.execute("""
select id, cast(created*1000 as int), factId, ordinal,
cast(modified as int), 0,
(case relativeDelay
when 0 then 1
when 1 then 2
when 2 then 0 end),
(case type
when 0 then 1
when 1 then 2
when 2 then 0
else type end),
cast(due as int), cast(interval as int),
cast(factor*1000 as int), reps, noCount from cards
order by created"""):
            # find an unused time
            row = list(row)
            if row[1] <= highest:
                highest = max(highest, row[1]) + 1
                row[1] = highest
            else:
                highest = row[1]
            # rewrite fact id
            row[2] = factidmap[row[2]]
            # note id change and save all but old id
            cardidmap[row[0]] = row[1]
            rows.append(row[1:])
        # drop old table and rewrite
        db.execute("drop table cards")
        _addSchema(db, False)
        db.executemany("""
insert into cards values (?,?,1,?,?,?,?,?,?,?,?,?,?,0,0,0,0,"")""",
                       rows)

        # reviewHistory -> revlog
        ###########
        # fetch the data so we can rewrite ids quickly
        r = []
        for row in db.execute("""
select
cast(time*1000 as int), cardId, 0, ease,
cast(nextInterval as int), cast(lastInterval as int),
cast(nextFactor*1000 as int), cast(min(thinkingTime, 60)*1000 as int),
yesCount from reviewHistory"""):
            row = list(row)
            # new card ids
            try:
                row[1] = cardidmap[row[1]]
            except:
                # id doesn't exist
                continue
            # no ease 0 anymore
            row[3] = row[3] or 1
            # determine type, overwriting yesCount
            newInt = row[4]
            oldInt = row[5]
            yesCnt = row[8]
            # yesCnt included the current answer
            if row[3] > 1:
                yesCnt -= 1
            if oldInt < 1:
                # new or failed
                if yesCnt:
                    # type=relrn
                    row[8] = 2
                else:
                    # type=lrn
                    row[8] = 0
            else:
                # type=rev
                row[8] = 1
            r.append(row)
        db.executemany(
            "insert or ignore into revlog values (?,?,?,?,?,?,?,?,?)", r)
        db.execute("drop table reviewHistory")

        # deck
        ###########
        self._migrateDeckTbl()

        # tags
        ###########
        tags = {}
        for t in db.list("select tag from tags"):
            tags[t] = intTime()
        db.execute("update col set tags = ?", json.dumps(tags))
        db.execute("drop table tags")
        db.execute("drop table cardTags")

        # the rest
        ###########
        db.execute("drop table media")
        db.execute("drop table sources")
        self._migrateModels()
        _updateIndices(db)

    def _migrateDeckTbl(self):
        db = self.db
        db.execute("delete from col")
        db.execute("""
insert or replace into col select id, cast(created as int), :t,
:t, 99, 0, 0, cast(lastSync as int),
"", "", "", "", "" from decks""", t=intTime())
        # prepare a deck to store the old deck options
        g, gc, conf = _getColVars(db)
        # delete old selective study settings, which we can't auto-upgrade easily
        keys = ("newActive", "newInactive", "revActive", "revInactive")
        for k in keys:
            db.execute("delete from deckVars where key=:k", k=k)
        # copy other settings, ignoring deck order as there's a new default
        gc['new']['perDay'] = db.scalar("select newCardsPerDay from decks")
        gc['new']['order'] = min(1, db.scalar("select newCardOrder from decks"))
        # these are collection level, and can't be imported on a per-deck basis
        # conf['newSpread'] = db.scalar("select newCardSpacing from decks")
        # conf['timeLim'] = db.scalar("select sessionTimeLimit from decks")
        # add any deck vars and save
        for (k, v) in db.execute("select * from deckVars").fetchall():
            if k in ("hexCache", "cssCache"):
                # ignore
                pass
            elif k == "leechFails":
                gc['lapse']['leechFails'] = int(v)
            else:
                conf[k] = v
        # don't use a learning mode for upgrading users
        #gc['new']['delays'] = [10]
        _addColVars(db, g, gc, conf)
        # clean up
        db.execute("drop table decks")
        db.execute("drop table deckVars")

    def _migrateModels(self):
        import anki.models
        db = self.db
        times = {}
        mods = {}
        for row in db.all(
            "select id, name from models"):
            # use only first 31 bits if not old anki id
            t = abs(row[0])
            if t > 4294967296:
                t >>= 32
            assert t > 0
            m = anki.models.defaultModel.copy()
            m['id'] = t
            m['name'] = row[1]
            m['mod'] = intTime()
            m['tags'] = []
            m['flds'] = self._fieldsForModel(row[0])
            m['tmpls'] = self._templatesForModel(row[0], m['flds'])
            mods[m['id']] = m
            db.execute("update notes set mid = ? where mid = ?", t, row[0])
        # save and clean up
        db.execute("update col set models = ?", json.dumps(mods))
        db.execute("drop table fieldModels")
        db.execute("drop table cardModels")
        db.execute("drop table models")

    def _fieldsForModel(self, mid):
        import anki.models
        db = self.db
        dconf = anki.models.defaultField
        flds = []
        # note: qsize & qcol are used in upgrade then discarded
        for c, row in enumerate(db.all("""
select name, features, quizFontFamily, quizFontSize, quizFontColour,
editFontSize from fieldModels where modelId = ?
order by ordinal""", mid)):
            conf = dconf.copy()
            (conf['name'],
             conf['rtl'],
             conf['font'],
             conf['qsize'],
             conf['qcol'],
             conf['size']) = row
            conf['ord'] = c
            # ensure data is good
            conf['rtl'] = not not conf['rtl']
            conf['font'] = conf['font'] or "Arial"
            conf['size'] = 12
            # will be removed later in upgrade
            conf['qcol'] = conf['qcol'] or "#000"
            conf['qsize'] = conf['qsize'] or 20
            flds.append(conf)
        return flds

    def _templatesForModel(self, mid, flds):
        import anki.models
        db = self.db
        dconf = anki.models.defaultTemplate
        tmpls = []
        for c, row in enumerate(db.all("""
select name, active, qformat, aformat, questionInAnswer,
questionAlign, lastFontColour, typeAnswer from cardModels
where modelId = ?
order by ordinal""", mid)):
            conf = dconf.copy()
            (conf['name'],
             conf['actv'],
             conf['qfmt'],
             conf['afmt'],
             # the following are used in upgrade then discarded
             hideq,
             conf['align'],
             conf['bg'],
             typeAns) = row
            conf['ord'] = c
            for type in ("qfmt", "afmt"):
                # ensure the new style field format
                conf[type] = re.sub("%\((.+?)\)s", "{{\\1}}", conf[type])
                # some special names have changed
                conf[type] = re.sub(
                    "(?i){{tags}}", "{{Tags}}", conf[type])
                conf[type] = re.sub(
                    "(?i){{cardModel}}", "{{Card}}", conf[type])
                conf[type] = re.sub(
                    "(?i){{modelTags}}", "{{Type}}", conf[type])
                # type answer is now embedded in the format
                if typeAns:
                    if type == "qfmt" or hideq:
                        conf[type] += '<br>{{type:%s}}' % typeAns
            # q fields now in a
            if not hideq:
                conf['afmt'] = (
                    "{{FrontSide}}\n\n<hr id=answer>\n\n" + conf['afmt'])
            tmpls.append(conf)
        return tmpls

    # Field munging
    ######################################################################

    def _mungeField(self, val):
        # we no longer wrap fields in white-space: pre-wrap, so we need to
        # convert previous whitespace into non-breaking spaces
        def repl(match):
            return match.group(1).replace(" ", "&nbsp;")
        return re.sub("(  +)", repl, val)

    # Template upgrading
    ######################################################################
    # - {{field}} no longer inserts an implicit span, so we make the span
    #   explicit on upgrade.
    # - likewise with alignment and background color
    def _upgradeTemplates(self):
        d = self.col
        for m in d.models.all():
            # cache field styles
            styles = {}
            for f in m['flds']:
                attrs = []
                if f['font'].lower() != 'arial':
                    attrs.append("font-family: %s" % f['font'])
                if f['qsize'] != 20:
                    attrs.append("font-size: %spx" % f['qsize'])
                if f['qcol'] not in ("black", "#000"):
                    attrs.append("color: %s" % f['qcol'])
                if f['rtl']:
                    attrs.append("direction: rtl; unicode-bidi: embed")
                if attrs:
                    styles[f['name']] = '<span style="%s">{{%s}}</span>' % (
                        "; ".join(attrs), f['name'])
                # obsolete
                del f['qcol']
                del f['qsize']
            # then for each template
            for t in m['tmpls']:
                def repl(match):
                    field = match.group(2)
                    if field in styles:
                        return match.group(1) + styles[field]
                    # special or non-existant field; leave alone
                    return match.group(0)
                for k in 'qfmt', 'afmt':
                    # replace old field references
                    t[k] = re.sub("(^|[^{]){{([^{}]+)?}}", repl, t[k])
                    # then strip extra {}s from other fields
                    t[k] = t[k].replace("{{{", "{{").replace("}}}", "}}")
                    # remove superfluous formatting from 1.0 -> 1.2 upgrade
                    t[k] = re.sub("font-size: ?20px;?", "", t[k])
                    t[k] = re.sub("(?i)font-family: ?arial;?", "", t[k])
                    t[k] = re.sub("color: ?#000(000)?;?", "", t[k])
                    t[k] = re.sub("white-space: ?pre-wrap;?", "", t[k])
                    # new furigana handling
                    if "japanese" in m['name'].lower():
                        if k == 'qfmt':
                            t[k] = t[k].replace(
                                "{{Reading}}", "{{kana:Reading}}")
                        else:
                            t[k] = t[k].replace(
                                "{{Reading}}", "{{furigana:Reading}}")
                # adjust css
                css = ""
                if t['bg'] != "white" and t['bg'].lower() != "#ffffff":
                    css = "background-color: %s;" % t['bg']
                if t['align']:
                    css += "text-align: %s" % ("left", "right")[t['align']-1]
                if css:
                    css = '\n.card%d { %s }' % (t['ord']+1, css)
                m['css'] += css
                # remove obsolete
                del t['bg']
                del t['align']
            # save model
            d.models.save(m)

    # Media references
    ######################################################################
    # In 2.0 we drop support for media and latex references in the template,
    # since they require generating card templates to see what media a note
    # uses, and are confusing for shared deck users. To ease the upgrade
    # process, we automatically convert the references to new fields.

    def _rewriteMediaRefs(self):
        col = self.col
        def rewriteRef(key):
            all, fname = match
            if all in state['mflds']:
                # we've converted this field before
                new = state['mflds'][all]
            else:
                # get field name and any prefix/suffix
                m2 = re.match(
                    "([^{]*)\{\{\{?(?:text:)?([^}]+)\}\}\}?(.*)",
                    fname)
                # not a field reference?
                if not m2:
                    return
                pre, ofld, suf = m2.groups()
                # get index of field name
                try:
                    idx = col.models.fieldMap(m)[ofld][0]
                except:
                    # invalid field or tag reference; don't rewrite
                    return
                # find a free field name
                while 1:
                    state['fields'] += 1
                    fld = "Media %d" % state['fields']
                    if fld not in col.models.fieldMap(m).keys():
                        break
                # add the new field
                f = col.models.newField(fld)
                f['qsize'] = 20
                f['qcol'] = '#000'
                col.models.addField(m, f)
                # loop through notes and write reference into new field
                data = []
                for id, flds in self.col.db.execute(
                    "select id, flds from notes where id in "+
                    ids2str(col.models.nids(m))):
                    sflds = splitFields(flds)
                    ref = all.replace(fname, pre+sflds[idx]+suf)
                    data.append((flds+ref, id))
                # update notes
                col.db.executemany("update notes set flds=? where id=?",
                                    data)
                # note field for future
                state['mflds'][fname] = fld
                new = fld
            # rewrite reference in template
            t[key] = t[key].replace(all, "{{{%s}}}" % new)
        regexps = col.media.regexps + (
            r"(\[latex\](.+?)\[/latex\])",
            r"(\[\$\](.+?)\[/\$\])",
            r"(\[\$\$\](.+?)\[/\$\$\])")
        # process each model
        for m in col.models.all():
            state = dict(mflds={}, fields=0)
            for t in m['tmpls']:
                for r in regexps:
                    for match in re.findall(r, t['qfmt']):
                        rewriteRef('qfmt')
                    for match in re.findall(r, t['afmt']):
                        rewriteRef('afmt')
            if state['fields']:
                col.models.save(m)

    # Inactive templates
    ######################################################################
    # Templates can't be declared as inactive anymore. Remove any that are
    # marked inactive and have no dependent cards.

    def _removeInactive(self):
        d = self.col
        for m in d.models.all():
            remove = []
            for t in m['tmpls']:
                if not t['actv']:
                    if not d.db.scalar("""
select 1 from cards where nid in (select id from notes where mid = ?)
and ord = ? limit 1""", m['id'], t['ord']):
                        remove.append(t)
                del t['actv']
            for r in remove:
                try:
                    d.models.remTemplate(m, r)
                except AssertionError:
                    # if the model was unused this could result in all
                    # templates being removed; ignore error
                    pass
            d.models.save(m)

    # Conditional templates
    ######################################################################
    # For models that don't use a given template in all cards, we'll need to
    # add a new field to notes to indicate if the card should be generated or not

    def _addFlagFields(self):
        for m in self.col.models.all():
            nids = self.col.models.nids(m)
            changed = False
            for tmpl in m['tmpls']:
                if self._addFlagFieldsForTemplate(m, nids, tmpl):
                    changed = True
            if changed:
                # save model
                self.col.models.save(m, templates=True)

    def _addFlagFieldsForTemplate(self, m, nids, tmpl):
        cids = self.col.db.list(
            "select id from cards where nid in %s and ord = ?" %
            ids2str(nids), tmpl['ord'])
        if len(cids) == len(nids):
            # not selectively used
            return
        # add a flag field
        name = tmpl['name']
        have = [f['name'] for f in m['flds']]
        while name in have:
            name += "_"
        f = self.col.models.newField(name)
        self.col.models.addField(m, f)
        # find the notes that have that card
        haveNids = self.col.db.list(
            "select nid from cards where id in "+ids2str(cids))
        # add "y" to the appended field for those notes
        self.col.db.execute(
            "update notes set flds = flds || 'y' where id in "+ids2str(
                haveNids))
        # wrap the template in a conditional
        tmpl['qfmt'] = "{{#%s}}\n%s\n{{/%s}}" % (
            f['name'], tmpl['qfmt'], f['name'])
        return True

    # Post-schema upgrade
    ######################################################################

    def _upgradeRest(self):
        "Handle the rest of the upgrade to 2.0."
        col = self.col
        # make sure we have a current model id
        col.models.setCurrent(col.models.models.values()[0])
        # remove unused templates that were marked inactive
        self._removeInactive()
        # rewrite media references in card template
        self._rewriteMediaRefs()
        # template handling has changed
        self._upgradeTemplates()
        # add fields for selectively used templates
        self._addFlagFields()
        # fix creation time
        col.sched._updateCutoff()
        d = datetime.datetime.today()
        d -= datetime.timedelta(hours=4)
        d = datetime.datetime(d.year, d.month, d.day)
        d += datetime.timedelta(hours=4)
        d -= datetime.timedelta(days=1+int((time.time()-col.crt)/86400))
        col.crt = int(time.mktime(d.timetuple()))
        col.sched._updateCutoff()
        # update uniq cache
        col.updateFieldCache(col.db.list("select id from notes"))
        # remove old views
        for v in ("failedCards", "revCardsOld", "revCardsNew",
                  "revCardsDue", "revCardsRandom", "acqCardsRandom",
                  "acqCardsOld", "acqCardsNew"):
            col.db.execute("drop view if exists %s" % v)
        # remove stats, as it's all in the revlog now
        col.db.execute("drop table if exists stats")
        # suspended cards don't use ranges anymore
        col.db.execute("update cards set queue=-1 where queue between -3 and -1")
        col.db.execute("update cards set queue=-2 where queue between 3 and 5")
        col.db.execute("update cards set queue=type where queue between 6 and 8")
        # remove old deleted tables
        for t in ("cards", "notes", "models", "media"):
            col.db.execute("drop table if exists %sDeleted" % t)
        # and failed cards
        left = len(col.decks.confForDid(1)['lapse']['delays'])*1001
        col.db.execute("""
update cards set left=?,type=1,queue=1,ivl=1 where type=1 and ivl <= 1
and queue>=0""", left)
        col.db.execute("""
update cards set odue=?,left=?,type=2 where type=1 and ivl > 1 and queue>=0""",
                       col.sched.today+1, left)
        # and due cards
        col.db.execute("""
update cards set due = cast(
(case when due < :stamp then 0 else 1 end) +
((due-:stamp)/86400) as int)+:today where type = 2
""", stamp=col.sched.dayCutoff, today=col.sched.today)
        # lapses were counted differently in 1.0, so we should have a higher
        # default lapse threshold
        for d in col.decks.allConf():
            d['lapse']['leechFails'] = 16
            col.decks.save(d)
        # possibly re-randomize
        conf = col.decks.allConf()[0]
        if not conf['new']['order']:
            col.sched.randomizeCards(1)
        else:
            col.sched.orderCards(1)
        # optimize and finish
        col.db.commit()
        col.db.execute("vacuum")
        col.db.execute("analyze")
        col.db.execute("update col set ver = ?", SCHEMA_VERSION)
        col.save()

########NEW FILE########
__FILENAME__ = utils
# -*- coding: utf-8 -*-
# Copyright: Damien Elmes <anki@ichi2.net>
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

import re, os, random, time, types, math, htmlentitydefs, subprocess, \
    tempfile, shutil, string, httplib2, sys, locale
from hashlib import sha1
from anki.lang import _, ngettext
from anki.consts import *

if sys.version_info[1] < 5:
    def format_string(a, b):
        return a % b
    locale.format_string = format_string

try:
    import simplejson as json
except ImportError:
    import json

# Time handling
##############################################################################

def intTime(scale=1):
    "The time in integer seconds. Pass scale=1000 to get milliseconds."
    return int(time.time()*scale)

timeTable = {
    "years": lambda n: ngettext("%s year", "%s years", n),
    "months": lambda n: ngettext("%s month", "%s months", n),
    "days": lambda n: ngettext("%s day", "%s days", n),
    "hours": lambda n: ngettext("%s hour", "%s hours", n),
    "minutes": lambda n: ngettext("%s minute", "%s minutes", n),
    "seconds": lambda n: ngettext("%s second", "%s seconds", n),
    }

afterTimeTable = {
    "years": lambda n: ngettext("%s year<!--after-->", "%s years<!--after-->", n),
    "months": lambda n: ngettext("%s month<!--after-->", "%s months<!--after-->", n),
    "days": lambda n: ngettext("%s day<!--after-->", "%s days<!--after-->", n),
    "hours": lambda n: ngettext("%s hour<!--after-->", "%s hours<!--after-->", n),
    "minutes": lambda n: ngettext("%s minute<!--after-->", "%s minutes<!--after-->", n),
    "seconds": lambda n: ngettext("%s second<!--after-->", "%s seconds<!--after-->", n),
    }

def shortTimeFmt(type):
    return {
    "years": _("%sy"),
    "months": _("%smo"),
    "days": _("%sd"),
    "hours": _("%sh"),
    "minutes": _("%sm"),
    "seconds": _("%ss"),
    }[type]

def fmtTimeSpan(time, pad=0, point=0, short=False, after=False, unit=99):
    "Return a string representing a time span (eg '2 days')."
    (type, point) = optimalPeriod(time, point, unit)
    time = convertSecondsTo(time, type)
    if not point:
        time = math.floor(time)
    if short:
        fmt = shortTimeFmt(type)
    else:
        if after:
            fmt = afterTimeTable[type](_pluralCount(time, point))
        else:
            fmt = timeTable[type](_pluralCount(time, point))
    timestr = "%(a)d.%(b)df" % {'a': pad, 'b': point}
    return locale.format_string("%" + (fmt % timestr), time)

def optimalPeriod(time, point, unit):
    if abs(time) < 60 or unit < 1:
        type = "seconds"
        point -= 1
    elif abs(time) < 3600 or unit < 2:
        type = "minutes"
    elif abs(time) < 60 * 60 * 24 or unit < 3:
        type = "hours"
    elif abs(time) < 60 * 60 * 24 * 30 or unit < 4:
        type = "days"
    elif abs(time) < 60 * 60 * 24 * 365 or unit < 5:
        type = "months"
        point += 1
    else:
        type = "years"
        point += 1
    return (type, max(point, 0))

def convertSecondsTo(seconds, type):
    if type == "seconds":
        return seconds
    elif type == "minutes":
        return seconds / 60.0
    elif type == "hours":
        return seconds / 3600.0
    elif type == "days":
        return seconds / 86400.0
    elif type == "months":
        return seconds / 2592000.0
    elif type == "years":
        return seconds / 31536000.0
    assert False

def _pluralCount(time, point):
    if point:
        return 2
    return math.floor(time)

# Locale
##############################################################################

def fmtPercentage(float_value, point=1):
    "Return float with percentage sign"
    fmt = '%' + "0.%(b)df" % {'b': point}
    return locale.format_string(fmt, float_value) + "%"

def fmtFloat(float_value, point=1):
    "Return a string with decimal separator according to current locale"
    fmt = '%' + "0.%(b)df" % {'b': point}
    return locale.format_string(fmt, float_value)

# HTML
##############################################################################

def stripHTML(s):
    s = re.sub("(?s)<style.*?>.*?</style>", "", s)
    s = re.sub("(?s)<script.*?>.*?</script>", "", s)
    s = re.sub("<.*?>", "", s)
    s = entsToTxt(s)
    return s

def stripHTMLMedia(s):
    "Strip HTML but keep media filenames"
    s = re.sub("<img src=[\"']?([^\"'>]+)[\"']? ?/?>", " \\1 ", s)
    return stripHTML(s)

def minimizeHTML(s):
    "Correct Qt's verbose bold/underline/etc."
    s = re.sub('<span style="font-weight:600;">(.*?)</span>', '<b>\\1</b>',
               s)
    s = re.sub('<span style="font-style:italic;">(.*?)</span>', '<i>\\1</i>',
               s)
    s = re.sub('<span style="text-decoration: underline;">(.*?)</span>',
               '<u>\\1</u>', s)
    return s

def entsToTxt(html):
    def fixup(m):
        text = m.group(0)
        if text[:2] == "&#":
            # character reference
            try:
                if text[:3] == "&#x":
                    return unichr(int(text[3:-1], 16))
                else:
                    return unichr(int(text[2:-1]))
            except ValueError:
                pass
        else:
            # named entity
            try:
                text = unichr(htmlentitydefs.name2codepoint[text[1:-1]])
            except KeyError:
                pass
        return text # leave as is
    return re.sub("&#?\w+;", fixup, html)

# IDs
##############################################################################

def hexifyID(id):
    return "%x" % int(id)

def dehexifyID(id):
    return int(id, 16)

def ids2str(ids):
    """Given a list of integers, return a string '(int1,int2,...)'."""
    return "(%s)" % ",".join(str(i) for i in ids)

def timestampID(db, table):
    "Return a non-conflicting timestamp for table."
    # be careful not to create multiple objects without flushing them, or they
    # may share an ID.
    t = intTime(1000)
    while db.scalar("select id from %s where id = ?" % table, t):
        t += 1
    return t

def maxID(db):
    "Return the first safe ID to use."
    now = intTime(1000)
    for tbl in "cards", "notes":
        now = max(now, db.scalar(
                "select max(id) from %s" % tbl))
    return now + 1

# used in ankiweb
def base62(num, extra=""):
    s = string; table = s.ascii_letters + s.digits + extra
    buf = ""
    while num:
        num, i = divmod(num, len(table))
        buf = table[i] + buf
    return buf

_base91_extra_chars = "!#$%&()*+,-./:;<=>?@[]^_`{|}~"
def base91(num):
    # all printable characters minus quotes, backslash and separators
    return base62(num, _base91_extra_chars)

def guid64():
    "Return a base91-encoded 64bit random number."
    return base91(random.randint(0, 2**64-1))

# increment a guid by one, for note type conflicts
def incGuid(guid):
    return _incGuid(guid[::-1])[::-1]

def _incGuid(guid):
    s = string; table = s.ascii_letters + s.digits + _base91_extra_chars
    idx = table.index(guid[0])
    if idx + 1 == len(table):
        # overflow
        guid = table[0] + _incGuid(guid[1:])
    else:
        guid = table[idx+1] + guid[1:]
    return guid

# Fields
##############################################################################

def joinFields(list):
    return "\x1f".join(list)

def splitFields(string):
    return string.split("\x1f")

# Checksums
##############################################################################

def checksum(data):
    return sha1(data).hexdigest()

def fieldChecksum(data):
    # 32 bit unsigned number from first 8 digits of sha1 hash
    return int(checksum(data.encode("utf-8"))[:8], 16)

# Temp files
##############################################################################

_tmpdir = None

def tmpdir():
    "A reusable temp folder which we clean out on each program invocation."
    global _tmpdir
    if not _tmpdir:
        def cleanup():
            shutil.rmtree(_tmpdir)
        import atexit
        atexit.register(cleanup)
        _tmpdir = unicode(os.path.join(tempfile.gettempdir(), "anki_temp"), sys.getfilesystemencoding())
        if not os.path.exists(_tmpdir):
            os.mkdir(_tmpdir)
    return _tmpdir

def tmpfile(prefix="", suffix=""):
    (fd, name) = tempfile.mkstemp(dir=tmpdir(), prefix=prefix, suffix=suffix)
    os.close(fd)
    return name

def namedtmp(name, rm=True):
    "Return tmpdir+name. Deletes any existing file."
    path = os.path.join(tmpdir(), name)
    if rm:
        try:
            os.unlink(path)
        except (OSError, IOError):
            pass
    return path

# Cmd invocation
##############################################################################

def call(argv, wait=True, **kwargs):
    "Execute a command. If WAIT, return exit code."
    # ensure we don't open a separate window for forking process on windows
    if isWin:
        si = subprocess.STARTUPINFO()
        try:
            si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        except:
            si.dwFlags |= subprocess._subprocess.STARTF_USESHOWWINDOW
    else:
        si = None
    # run
    try:
        o = subprocess.Popen(argv, startupinfo=si, **kwargs)
    except OSError:
        # command not found
        return -1
    # wait for command to finish
    if wait:
        while 1:
            try:
                ret = o.wait()
            except OSError:
                # interrupted system call
                continue
            break
    else:
        ret = 0
    return ret

# OS helpers
##############################################################################

isMac = sys.platform.startswith("darwin")
isWin = sys.platform.startswith("win32")

invalidFilenameChars = "\\/:*?\"<>|"

def invalidFilename(str):
    for c in invalidFilenameChars:
        if c in str:
            return True

########NEW FILE########
__FILENAME__ = shared
import tempfile, os, shutil
from anki import Collection as aopen

def assertException(exception, func):
    found = False
    try:
        func()
    except exception:
        found = True
    assert found

def getEmptyDeck(**kwargs):
    (fd, nam) = tempfile.mkstemp(suffix=".anki2")
    os.unlink(nam)
    return aopen(nam, **kwargs)

def getUpgradeDeckPath(name="anki12.anki"):
    src = os.path.join(testDir, "support", name)
    (fd, dst) = tempfile.mkstemp(suffix=".anki2")
    shutil.copy(src, dst)
    return dst

testDir = os.path.dirname(__file__)

########NEW FILE########
__FILENAME__ = test_cards
# coding: utf-8

import time
from anki.db import DB
from anki.consts import *
from anki.utils import hexifyID
from tests.shared import getEmptyDeck
from anki.hooks import addHook, remHook

def test_previewCards():
    deck = getEmptyDeck()
    f = deck.newNote()
    f['Front'] = u'1'
    f['Back'] = u'2'
    # non-empty and active
    cards = deck.previewCards(f, 0)
    assert len(cards) == 1
    assert cards[0].ord == 0
    # all templates
    cards = deck.previewCards(f, 2)
    assert len(cards) == 1
    # add the note, and test existing preview
    deck.addNote(f)
    cards = deck.previewCards(f, 1)
    assert len(cards) == 1
    assert cards[0].ord == 0
    # make sure we haven't accidentally added cards to the db
    assert deck.cardCount() == 1

def test_delete():
    deck = getEmptyDeck()
    f = deck.newNote()
    f['Front'] = u'1'
    f['Back'] = u'2'
    deck.addNote(f)
    cid = f.cards()[0].id
    deck.reset()
    deck.sched.answerCard(deck.sched.getCard(), 2)
    deck.remCards([cid])
    assert deck.cardCount() == 0
    assert deck.noteCount() == 0
    assert deck.db.scalar("select count() from notes") == 0
    assert deck.db.scalar("select count() from cards") == 0
    assert deck.db.scalar("select count() from graves") == 2

def test_misc():
    d = getEmptyDeck()
    f = d.newNote()
    f['Front'] = u'1'
    f['Back'] = u'2'
    d.addNote(f)
    c = f.cards()[0]
    id = d.models.current()['id']
    assert c.template()['ord'] == 0

def test_genrem():
    d = getEmptyDeck()
    f = d.newNote()
    f['Front'] = u'1'
    f['Back'] = u''
    d.addNote(f)
    assert len(f.cards()) == 1
    m = d.models.current()
    mm = d.models
    # adding a new template should automatically create cards
    t = mm.newTemplate("rev")
    t['qfmt'] = '{{Front}}'
    t['afmt'] = ""
    mm.addTemplate(m, t)
    mm.save(m, templates=True)
    assert len(f.cards()) == 2
    # if the template is changed to remove cards, they'll be removed
    t['qfmt'] = "{{Back}}"
    mm.save(m, templates=True)
    d.remCards(d.emptyCids())
    assert len(f.cards()) == 1
    # if we add to the note, a card should be automatically generated
    f.load()
    f['Back'] = "1"
    f.flush()
    assert len(f.cards()) == 2

def test_gendeck():
    d = getEmptyDeck()
    cloze = d.models.byName("Cloze")
    d.models.setCurrent(cloze)
    f = d.newNote()
    f['Text'] = u'{{c1::one}}'
    d.addNote(f)
    assert d.cardCount() == 1
    assert f.cards()[0].did == 1
    # set the model to a new default deck
    newId = d.decks.id("new")
    cloze['did'] = newId
    d.models.save(cloze)
    # a newly generated card should share the first card's deck
    f['Text'] += u'{{c2::two}}'
    f.flush()
    assert f.cards()[1].did == 1
    # and same with multiple cards
    f['Text'] += u'{{c3::three}}'
    f.flush()
    assert f.cards()[2].did == 1
    # if one of the cards is in a different deck, it should revert to the
    # model default
    c = f.cards()[1]
    c.did = newId
    c.flush()
    f['Text'] += u'{{c4::four}}'
    f.flush()
    assert f.cards()[3].did == newId




########NEW FILE########
__FILENAME__ = test_collection
# coding: utf-8

import os, re, datetime
from tests.shared import assertException, getEmptyDeck, testDir, \
    getUpgradeDeckPath
from anki.stdmodels import addBasicModel
from anki.consts import *

from anki import Collection as aopen

newPath = None
newMod = None

def test_create():
    global newPath, newMod
    path = "/tmp/test_attachNew.anki2"
    try:
        os.unlink(path)
    except OSError:
        pass
    deck = aopen(path)
    # for open()
    newPath = deck.path
    deck.close()
    newMod = deck.mod
    del deck

def test_open():
    deck = aopen(newPath)
    assert deck.mod == newMod
    deck.close()

def test_openReadOnly():
    # non-writeable dir
    assertException(Exception,
                    lambda: aopen("/attachroot.anki2"))
    # reuse tmp file from before, test non-writeable file
    os.chmod(newPath, 0)
    assertException(Exception,
                    lambda: aopen(newPath))
    os.chmod(newPath, 0666)
    os.unlink(newPath)

def test_noteAddDelete():
    deck = getEmptyDeck()
    # add a note
    f = deck.newNote()
    f['Front'] = u"one"; f['Back'] = u"two"
    n = deck.addNote(f)
    assert n == 1
    # test multiple cards - add another template
    m = deck.models.current(); mm = deck.models
    t = mm.newTemplate("Reverse")
    t['qfmt'] = "{{Back}}"
    t['afmt'] = "{{Front}}"
    mm.addTemplate(m, t)
    mm.save(m)
    # the default save doesn't generate cards
    assert deck.cardCount() == 1
    # but when templates are edited such as in the card layout screen, it
    # should generate cards on close
    mm.save(m, templates=True)
    assert deck.cardCount() == 2
    # creating new notes should use both cards
    f = deck.newNote()
    f['Front'] = u"three"; f['Back'] = u"four"
    n = deck.addNote(f)
    assert n == 2
    assert deck.cardCount() == 4
    # check q/a generation
    c0 = f.cards()[0]
    assert "three" in c0.q()
    # it should not be a duplicate
    assert not f.dupeOrEmpty()
    # now let's make a duplicate
    f2 = deck.newNote()
    f2['Front'] = u"one"; f2['Back'] = u""
    assert f2.dupeOrEmpty()
    # empty first field should not be permitted either
    f2['Front'] = " "
    assert f2.dupeOrEmpty()

def test_fieldChecksum():
    deck = getEmptyDeck()
    f = deck.newNote()
    f['Front'] = u"new"; f['Back'] = u"new2"
    deck.addNote(f)
    assert deck.db.scalar(
        "select csum from notes") == int("c2a6b03f", 16)
    # changing the val should change the checksum
    f['Front'] = u"newx"
    f.flush()
    assert deck.db.scalar(
        "select csum from notes") == int("302811ae", 16)

def test_addDelTags():
    deck = getEmptyDeck()
    f = deck.newNote()
    f['Front'] = u"1"
    deck.addNote(f)
    f2 = deck.newNote()
    f2['Front'] = u"2"
    deck.addNote(f2)
    # adding for a given id
    deck.tags.bulkAdd([f.id], "foo")
    f.load(); f2.load()
    assert "foo" in f.tags
    assert "foo" not in f2.tags
    # should be canonified
    deck.tags.bulkAdd([f.id], "foo aaa")
    f.load()
    assert f.tags[0] == "aaa"
    assert len(f.tags) == 2

def test_timestamps():
    deck = getEmptyDeck()
    assert len(deck.models.models) == 4
    for i in range(100):
        addBasicModel(deck)
    assert len(deck.models.models) == 104

def test_furigana():
    deck = getEmptyDeck()
    mm = deck.models
    m = mm.current()
    # filter should work
    m['tmpls'][0]['qfmt'] = '{{kana:Front}}'
    mm.save(m)
    n = deck.newNote()
    n['Front'] = 'foo[abc]'
    deck.addNote(n)
    c = n.cards()[0]
    assert c.q().endswith("abc")
    # and should avoid sound
    n['Front'] = 'foo[sound:abc.mp3]'
    n.flush()
    assert "sound:" in c.q(reload=True)
    # it shouldn't throw an error while people are editing
    m['tmpls'][0]['qfmt'] = '{{kana:}}'
    mm.save(m)
    c.q(reload=True)

########NEW FILE########
__FILENAME__ = test_decks
# coding: utf-8

from tests.shared import assertException, getEmptyDeck, testDir

def test_basic():
    deck = getEmptyDeck()
    # we start with a standard deck
    assert len(deck.decks.decks) == 1
    # it should have an id of 1
    assert deck.decks.name(1)
    # create a new deck
    parentId = deck.decks.id("new deck")
    assert parentId
    assert len(deck.decks.decks) == 2
    # should get the same id
    assert deck.decks.id("new deck") == parentId
    # we start with the default deck selected
    assert deck.decks.selected() == 1
    assert deck.decks.active() == [1]
    # we can select a different deck
    deck.decks.select(parentId)
    assert deck.decks.selected() == parentId
    assert deck.decks.active() == [parentId]
    # let's create a child
    childId = deck.decks.id("new deck::child")
    # it should have been added to the active list
    assert deck.decks.selected() == parentId
    assert deck.decks.active() == [parentId, childId]
    # we can select the child individually too
    deck.decks.select(childId)
    assert deck.decks.selected() == childId
    assert deck.decks.active() == [childId]
    # parents with a different case should be handled correctly
    deck.decks.id("ONE")
    m = deck.models.current()
    m['did'] = deck.decks.id("one::two")
    deck.models.save(m)
    n = deck.newNote()
    n['Front'] = "abc"
    deck.addNote(n)
    # this will error if child and parent case don't match
    deck.sched.deckDueList()

def test_remove():
    deck = getEmptyDeck()
    # create a new deck, and add a note/card to it
    g1 = deck.decks.id("g1")
    f = deck.newNote()
    f['Front'] = u"1"
    f.model()['did'] = g1
    deck.addNote(f)
    c = f.cards()[0]
    assert c.did == g1
    # by default deleting the deck leaves the cards with an invalid did
    assert deck.cardCount() == 1
    deck.decks.rem(g1)
    assert deck.cardCount() == 1
    c.load()
    assert c.did == g1
    # but if we try to get it, we get the default
    assert deck.decks.name(c.did) == "[no deck]"
    # let's create another deck and explicitly set the card to it
    g2 = deck.decks.id("g2")
    c.did = g2; c.flush()
    # this time we'll delete the card/note too
    deck.decks.rem(g2, cardsToo=True)
    assert deck.cardCount() == 0
    assert deck.noteCount() == 0

def test_rename():
    d = getEmptyDeck()
    id = d.decks.id("hello::world")
    # should be able to rename into a completely different branch, creating
    # parents as necessary
    d.decks.rename(d.decks.get(id), "foo::bar")
    assert "foo" in d.decks.allNames()
    assert "foo::bar" in d.decks.allNames()
    assert "hello::world" not in d.decks.allNames()
    # create another deck
    id = d.decks.id("tmp")
    # we can't rename it if it conflicts
    assertException(
        Exception, lambda: d.decks.rename(d.decks.get(id), "foo"))
    # when renaming, the children should be renamed too
    d.decks.id("one::two::three")
    id = d.decks.id("one")
    d.decks.rename(d.decks.get(id), "yo")
    for n in "yo", "yo::two", "yo::two::three":
        assert n in d.decks.allNames()

def test_renameForDragAndDrop():
    d = getEmptyDeck()

    def deckNames():
        return [ name for name in sorted(d.decks.allNames()) if name <> u'Default' ]

    languages_did = d.decks.id('Languages')
    chinese_did = d.decks.id('Chinese')
    hsk_did = d.decks.id('Chinese::HSK')

    # Renaming also renames children
    d.decks.renameForDragAndDrop(chinese_did, languages_did)
    assert deckNames() == [ 'Languages', 'Languages::Chinese', 'Languages::Chinese::HSK' ]

    # Dragging a deck onto itself is a no-op
    d.decks.renameForDragAndDrop(languages_did, languages_did)
    assert deckNames() == [ 'Languages', 'Languages::Chinese', 'Languages::Chinese::HSK' ]

    # Dragging a deck onto its parent is a no-op
    d.decks.renameForDragAndDrop(hsk_did, chinese_did)
    assert deckNames() == [ 'Languages', 'Languages::Chinese', 'Languages::Chinese::HSK' ]

    # Dragging a deck onto a descendant is a no-op
    d.decks.renameForDragAndDrop(languages_did, hsk_did)
    assert deckNames() == [ 'Languages', 'Languages::Chinese', 'Languages::Chinese::HSK' ]

    # Can drag a grandchild onto its grandparent.  It becomes a child
    d.decks.renameForDragAndDrop(hsk_did, languages_did)
    assert deckNames() == [ 'Languages', 'Languages::Chinese', 'Languages::HSK' ]

    # Can drag a deck onto its sibling
    d.decks.renameForDragAndDrop(hsk_did, chinese_did)
    assert deckNames() == [ 'Languages', 'Languages::Chinese', 'Languages::Chinese::HSK' ]

    # Can drag a deck back to the top level
    d.decks.renameForDragAndDrop(chinese_did, None)
    assert deckNames() == [ 'Chinese', 'Chinese::HSK', 'Languages' ]

    # Dragging a top level deck to the top level is a no-op
    d.decks.renameForDragAndDrop(chinese_did, None)
    assert deckNames() == [ 'Chinese', 'Chinese::HSK', 'Languages' ]

    # '' is a convenient alias for the top level DID
    d.decks.renameForDragAndDrop(hsk_did, '')
    assert deckNames() == [ 'Chinese', 'HSK', 'Languages' ]

########NEW FILE########
__FILENAME__ = test_exporting
# coding: utf-8

import nose, os, tempfile
import anki
from anki import Collection as aopen
from anki.exporting import *
from anki.importing import Anki2Importer
from anki.stdmodels import *
from shared import getEmptyDeck

deck = None
ds = None
testDir = os.path.dirname(__file__)

def setup1():
    global deck
    deck = getEmptyDeck()
    f = deck.newNote()
    f['Front'] = u"foo"; f['Back'] = u"bar"; f.tags = ["tag", "tag2"]
    deck.addNote(f)
    # with a different deck
    f = deck.newNote()
    f['Front'] = u"baz"; f['Back'] = u"qux"
    f.model()['did'] = deck.decks.id("new deck")
    deck.addNote(f)

##########################################################################

@nose.with_setup(setup1)
def test_export_anki():
    # create a new deck with its own conf to test conf copying
    did = deck.decks.id("test")
    dobj = deck.decks.get(did)
    confId = deck.decks.confId("newconf")
    conf = deck.decks.getConf(confId)
    conf['new']['perDay'] = 5
    deck.decks.save(conf)
    deck.decks.setConf(dobj, confId)
    # export
    e = AnkiExporter(deck)
    newname = unicode(tempfile.mkstemp(prefix="ankitest", suffix=".anki2")[1])
    os.unlink(newname)
    e.exportInto(newname)
    # exporting should not have changed conf for original deck
    conf = deck.decks.confForDid(did)
    assert conf['id'] != 1
    # connect to new deck
    d2 = aopen(newname)
    assert d2.cardCount() == 2
    # as scheduling was reset, should also revert decks to default conf
    did = d2.decks.id("test", create=False)
    assert did
    conf2 = d2.decks.confForDid(did)
    assert conf2['new']['perDay'] == 20
    dobj = d2.decks.get(did)
    # conf should be 1
    assert dobj['conf'] == 1
    # try again, limited to a deck
    newname = unicode(tempfile.mkstemp(prefix="ankitest", suffix=".anki2")[1])
    os.unlink(newname)
    e.did = 1
    e.exportInto(newname)
    d2 = aopen(newname)
    assert d2.cardCount() == 1

@nose.with_setup(setup1)
def test_export_ankipkg():
    # add a test file to the media folder
    open(os.path.join(deck.media.dir(), u"今日.mp3"), "w").write("test")
    n = deck.newNote()
    n['Front'] = u'[sound:今日.mp3]'
    deck.addNote(n)
    e = AnkiPackageExporter(deck)
    newname = unicode(tempfile.mkstemp(prefix="ankitest", suffix=".apkg")[1])
    os.unlink(newname)
    e.exportInto(newname)

@nose.with_setup(setup1)
def test_export_anki_due():
    deck = getEmptyDeck()
    f = deck.newNote()
    f['Front'] = u"foo"
    deck.addNote(f)
    deck.crt -= 86400*10
    deck.sched.reset()
    c = deck.sched.getCard()
    deck.sched.answerCard(c, 2)
    deck.sched.answerCard(c, 2)
    # should have ivl of 1, due on day 11
    assert c.ivl == 1
    assert c.due == 11
    assert deck.sched.today == 10
    assert c.due - deck.sched.today == 1
    # export
    e = AnkiExporter(deck)
    e.includeSched = True
    newname = unicode(tempfile.mkstemp(prefix="ankitest", suffix=".anki2")[1])
    os.unlink(newname)
    e.exportInto(newname)
    # importing into a new deck, the due date should be equivalent
    deck2 = getEmptyDeck()
    imp = Anki2Importer(deck2, newname)
    imp.run()
    c = deck2.getCard(c.id)
    deck2.sched.reset()
    assert c.due - deck2.sched.today == 1

# @nose.with_setup(setup1)
# def test_export_textcard():
#     e = TextCardExporter(deck)
#     f = unicode(tempfile.mkstemp(prefix="ankitest")[1])
#     os.unlink(f)
#     e.exportInto(f)
#     e.includeTags = True
#     e.exportInto(f)

@nose.with_setup(setup1)
def test_export_textnote():
    e = TextNoteExporter(deck)
    f = unicode(tempfile.mkstemp(prefix="ankitest")[1])
    os.unlink(f)
    e.exportInto(f)
    e.includeTags = True
    e.exportInto(f)

def test_exporters():
    assert "*.apkg" in str(exporters())

########NEW FILE########
__FILENAME__ = test_find
# coding: utf-8

from anki.find import Finder
from tests.shared import getEmptyDeck

def test_parse():
    f = Finder(None)
    assert f._tokenize("hello world") == ["hello", "world"]
    assert f._tokenize("hello  world") == ["hello", "world"]
    assert f._tokenize("one -two") == ["one", "-", "two"]
    assert f._tokenize("one --two") == ["one", "-", "two"]
    assert f._tokenize("one - two") == ["one", "-", "two"]
    assert f._tokenize("one or -two") == ["one", "or", "-", "two"]
    assert f._tokenize("'hello \"world\"'") == ["hello \"world\""]
    assert f._tokenize('"hello world"') == ["hello world"]
    assert f._tokenize("one (two or ( three or four))") == [
        "one", "(", "two", "or", "(", "three", "or", "four",
        ")", ")"]
    assert f._tokenize("embedded'string") == ["embedded'string"]
    assert f._tokenize("deck:'two words'") == ["deck:two words"]

def test_findCards():
    deck = getEmptyDeck()
    f = deck.newNote()
    f['Front'] = u'dog'
    f['Back'] = u'cat'
    f.tags.append(u"monkey")
    f1id = f.id
    deck.addNote(f)
    firstCardId = f.cards()[0].id
    f = deck.newNote()
    f['Front'] = u'goats are fun'
    f['Back'] = u'sheep'
    f.tags.append(u"sheep goat horse")
    deck.addNote(f)
    f2id = f.id
    f = deck.newNote()
    f['Front'] = u'cat'
    f['Back'] = u'sheep'
    deck.addNote(f)
    catCard = f.cards()[0]
    m = deck.models.current(); mm = deck.models
    t = mm.newTemplate("Reverse")
    t['qfmt'] = "{{Back}}"
    t['afmt'] = "{{Front}}"
    mm.addTemplate(m, t)
    mm.save(m)
    f = deck.newNote()
    f['Front'] = u'test'
    f['Back'] = u'foo bar'
    deck.addNote(f)
    latestCardIds = [c.id for c in f.cards()]
    # tag searches
    assert not deck.findCards("tag:donkey")
    assert len(deck.findCards("tag:sheep")) == 1
    assert len(deck.findCards("tag:sheep tag:goat")) == 1
    assert len(deck.findCards("tag:sheep tag:monkey")) == 0
    assert len(deck.findCards("tag:monkey")) == 1
    assert len(deck.findCards("tag:sheep -tag:monkey")) == 1
    assert len(deck.findCards("-tag:sheep")) == 4
    deck.tags.bulkAdd(deck.db.list("select id from notes"), "foo bar")
    assert (len(deck.findCards("tag:foo")) ==
            len(deck.findCards("tag:bar")) ==
            5)
    deck.tags.bulkRem(deck.db.list("select id from notes"), "foo")
    assert len(deck.findCards("tag:foo")) == 0
    assert len(deck.findCards("tag:bar")) == 5
    # text searches
    assert len(deck.findCards("cat")) == 2
    assert len(deck.findCards("cat -dog")) == 1
    assert len(deck.findCards("cat -dog")) == 1
    assert len(deck.findCards("are goats")) == 1
    assert len(deck.findCards('"are goats"')) == 0
    assert len(deck.findCards('"goats are"')) == 1
    # card states
    c = f.cards()[0]
    c.queue = c.type = 2
    assert deck.findCards("is:review") == []
    c.flush()
    assert deck.findCards("is:review") == [c.id]
    assert deck.findCards("is:due") == []
    c.due = 0; c.queue = 2
    c.flush()
    assert deck.findCards("is:due") == [c.id]
    assert len(deck.findCards("-is:due")) == 4
    c.queue = -1
    # ensure this card gets a later mod time
    c.flush()
    deck.db.execute("update cards set mod = mod + 1 where id = ?", c.id)
    assert deck.findCards("is:suspended") == [c.id]
    # nids
    assert deck.findCards("nid:54321") == []
    assert len(deck.findCards("nid:%d"%f.id)) == 2
    assert len(deck.findCards("nid:%d,%d" % (f1id, f2id))) == 2
    # templates
    assert len(deck.findCards("card:foo")) == 0
    assert len(deck.findCards("'card:card 1'")) == 4
    assert len(deck.findCards("card:reverse")) == 1
    assert len(deck.findCards("card:1")) == 4
    assert len(deck.findCards("card:2")) == 1
    # fields
    assert len(deck.findCards("front:dog")) == 1
    assert len(deck.findCards("-front:dog")) == 4
    assert len(deck.findCards("front:sheep")) == 0
    assert len(deck.findCards("back:sheep")) == 2
    assert len(deck.findCards("-back:sheep")) == 3
    assert len(deck.findCards("front:do")) == 0
    assert len(deck.findCards("front:*")) == 5
    # ordering
    deck.conf['sortType'] = "noteCrt"
    assert deck.findCards("front:*", order=True)[-1] in latestCardIds
    assert deck.findCards("", order=True)[-1] in latestCardIds
    deck.conf['sortType'] = "noteFld"
    assert deck.findCards("", order=True)[0] == catCard.id
    assert deck.findCards("", order=True)[-1] in latestCardIds
    deck.conf['sortType'] = "cardMod"
    assert deck.findCards("", order=True)[-1] in latestCardIds
    assert deck.findCards("", order=True)[0] == firstCardId
    deck.conf['sortBackwards'] = True
    assert deck.findCards("", order=True)[0] in latestCardIds
    # model
    assert len(deck.findCards("note:basic")) == 5
    assert len(deck.findCards("-note:basic")) == 0
    assert len(deck.findCards("-note:foo")) == 5
    # deck
    assert len(deck.findCards("deck:default")) == 5
    assert len(deck.findCards("-deck:default")) == 0
    assert len(deck.findCards("-deck:foo")) == 5
    assert len(deck.findCards("deck:def*")) == 5
    assert len(deck.findCards("deck:*EFAULT")) == 5
    assert len(deck.findCards("deck:*cefault")) == 0
    # full search
    f = deck.newNote()
    f['Front'] = u'hello<b>world</b>'
    f['Back'] = u'abc'
    deck.addNote(f)
    # as it's the sort field, it matches
    assert len(deck.findCards("helloworld")) == 2
    #assert len(deck.findCards("helloworld", full=True)) == 2
    # if we put it on the back, it won't
    (f['Front'], f['Back']) = (f['Back'], f['Front'])
    f.flush()
    assert len(deck.findCards("helloworld")) == 0
    #assert len(deck.findCards("helloworld", full=True)) == 2
    #assert len(deck.findCards("back:helloworld", full=True)) == 2
    # searching for an invalid special tag should not error
    assert len(deck.findCards("is:invalid")) == 0
    # should be able to limit to parent deck, no children
    id = deck.db.scalar("select id from cards limit 1")
    deck.db.execute("update cards set did = ? where id = ?",
                    deck.decks.id("Default::Child"), id)
    assert len(deck.findCards("deck:default")) == 7
    assert len(deck.findCards("deck:default::child")) == 1
    assert len(deck.findCards("deck:default -deck:default::*")) == 6
    # properties
    id = deck.db.scalar("select id from cards limit 1")
    deck.db.execute(
        "update cards set queue=2, ivl=10, reps=20, due=30, factor=2200 "
        "where id = ?", id)
    assert len(deck.findCards("prop:ivl>5")) == 1
    assert len(deck.findCards("prop:ivl<5")) > 1
    assert len(deck.findCards("prop:ivl>=5")) == 1
    assert len(deck.findCards("prop:ivl=9")) == 0
    assert len(deck.findCards("prop:ivl=10")) == 1
    assert len(deck.findCards("prop:ivl!=10")) > 1
    assert len(deck.findCards("prop:due>0")) == 1
    # due dates should work
    deck.sched.today = 15
    assert len(deck.findCards("prop:due=14")) == 0
    assert len(deck.findCards("prop:due=15")) == 1
    assert len(deck.findCards("prop:due=16")) == 0
    # including negatives
    deck.sched.today = 32
    assert len(deck.findCards("prop:due=-1")) == 0
    assert len(deck.findCards("prop:due=-2")) == 1
    # ease factors
    assert len(deck.findCards("prop:ease=2.3")) == 0
    assert len(deck.findCards("prop:ease=2.2")) == 1
    assert len(deck.findCards("prop:ease>2")) == 1
    assert len(deck.findCards("-prop:ease>2")) > 1
    # recently failed
    assert len(deck.findCards("rated:1:1")) == 0
    assert len(deck.findCards("rated:1:2")) == 0
    c = deck.sched.getCard()
    deck.sched.answerCard(c, 2)
    assert len(deck.findCards("rated:1:1")) == 0
    assert len(deck.findCards("rated:1:2")) == 1
    c = deck.sched.getCard()
    deck.sched.answerCard(c, 1)
    assert len(deck.findCards("rated:1:1")) == 1
    assert len(deck.findCards("rated:1:2")) == 1
    assert len(deck.findCards("rated:1")) == 2
    assert len(deck.findCards("rated:0:2")) == 0
    assert len(deck.findCards("rated:2:2")) == 1
    # empty field
    assert len(deck.findCards("front:")) == 0
    f = deck.newNote()
    f['Front'] = u''
    f['Back'] = u'abc2'
    assert deck.addNote(f) == 1
    assert len(deck.findCards("front:")) == 1
    # OR searches and nesting
    assert len(deck.findCards("tag:monkey or tag:sheep")) == 2
    assert len(deck.findCards("(tag:monkey OR tag:sheep)")) == 2
    assert len(deck.findCards("-(tag:monkey OR tag:sheep)")) == 6
    assert len(deck.findCards("tag:monkey or (tag:sheep sheep)")) == 2
    assert len(deck.findCards("tag:monkey or (tag:sheep octopus)")) == 1
    # invalid grouping shouldn't error
    assert len(deck.findCards(")")) == 0
    assert len(deck.findCards("(()")) == 0
    # added
    assert len(deck.findCards("added:0")) == 0
    deck.db.execute("update cards set id = id - 86400*1000 where id = ?",
                    id)
    assert len(deck.findCards("added:1")) == deck.cardCount() - 1
    assert len(deck.findCards("added:2")) == deck.cardCount()

def test_findReplace():
    deck = getEmptyDeck()
    f = deck.newNote()
    f['Front'] = u'foo'
    f['Back'] = u'bar'
    deck.addNote(f)
    f2 = deck.newNote()
    f2['Front'] = u'baz'
    f2['Back'] = u'foo'
    deck.addNote(f2)
    nids = [f.id, f2.id]
    # should do nothing
    assert deck.findReplace(nids, "abc", "123") == 0
    # global replace
    assert deck.findReplace(nids, "foo", "qux") == 2
    f.load(); assert f['Front'] == "qux"
    f2.load(); assert f2['Back'] == "qux"
    # single field replace
    assert deck.findReplace(nids, "qux", "foo", field="Front") == 1
    f.load(); assert f['Front'] == "foo"
    f2.load(); assert f2['Back'] == "qux"
    # regex replace
    assert deck.findReplace(nids, "B.r", "reg") == 0
    f.load(); assert f['Back'] != "reg"
    assert deck.findReplace(nids, "B.r", "reg", regex=True) == 1
    f.load(); assert f['Back'] == "reg"

def test_findDupes():
    deck = getEmptyDeck()
    f = deck.newNote()
    f['Front'] = u'foo'
    f['Back'] = u'bar'
    deck.addNote(f)
    f2 = deck.newNote()
    f2['Front'] = u'baz'
    f2['Back'] = u'bar'
    deck.addNote(f2)
    f3 = deck.newNote()
    f3['Front'] = u'quux'
    f3['Back'] = u'bar'
    deck.addNote(f3)
    f4 = deck.newNote()
    f4['Front'] = u'quuux'
    f4['Back'] = u'nope'
    deck.addNote(f4)
    r = deck.findDupes("Back")
    assert r[0][0] == "bar"
    assert len(r[0][1]) == 3
    # valid search
    r = deck.findDupes("Back", "bar")
    assert r[0][0] == "bar"
    assert len(r[0][1]) == 3
    # excludes everything
    r = deck.findDupes("Back", "invalid")
    assert not r
    # front isn't dupe
    assert deck.findDupes("Front") == []

########NEW FILE########
__FILENAME__ = test_importing
# coding: utf-8

import nose, os, shutil
from tests.shared import assertException, getUpgradeDeckPath, getEmptyDeck
from anki.upgrade import Upgrader
from anki.utils import ids2str
from anki.errors import *
from anki.importing import Anki1Importer, Anki2Importer, TextImporter, \
    SupermemoXmlImporter, MnemosyneImporter, AnkiPackageImporter
from anki.notes import Note
from anki.db import *

testDir = os.path.dirname(__file__)

srcNotes=None
srcCards=None

def test_anki2():
    global srcNotes, srcCards
    # get the deck to import
    tmp = getUpgradeDeckPath()
    u = Upgrader()
    src = u.upgrade(tmp)
    srcpath = src.path
    srcNotes = src.noteCount()
    srcCards = src.cardCount()
    srcRev = src.db.scalar("select count() from revlog")
    # add a media file for testing
    open(os.path.join(src.media.dir(), "_foo.jpg"), "w").write("foo")
    src.close()
    # create a new empty deck
    dst = getEmptyDeck()
    # import src into dst
    imp = Anki2Importer(dst, srcpath)
    imp.run()
    def check():
        assert dst.noteCount() == srcNotes
        assert dst.cardCount() == srcCards
        assert srcRev == dst.db.scalar("select count() from revlog")
        mids = [int(x) for x in dst.models.models.keys()]
        assert not dst.db.scalar(
            "select count() from notes where mid not in "+ids2str(mids))
        assert not dst.db.scalar(
            "select count() from cards where nid not in (select id from notes)")
        assert not dst.db.scalar(
            "select count() from revlog where cid not in (select id from cards)")
        assert dst.fixIntegrity()[0].startswith("Database rebuilt")
    check()
    # importing should be idempotent
    imp.run()
    check()
    assert len(os.listdir(dst.media.dir())) == 1

def test_anki2_mediadupes():
    tmp = getEmptyDeck()
    # add a note that references a sound
    n = tmp.newNote()
    n['Front'] = "[sound:foo.mp3]"
    mid = n.model()['id']
    tmp.addNote(n)
    # add that sound to media folder
    open(os.path.join(tmp.media.dir(), "foo.mp3"), "w").write("foo")
    tmp.close()
    # it should be imported correctly into an empty deck
    empty = getEmptyDeck()
    imp = Anki2Importer(empty, tmp.path)
    imp.run()
    assert os.listdir(empty.media.dir()) == ["foo.mp3"]
    # and importing again will not duplicate, as the file content matches
    empty.remCards(empty.db.list("select id from cards"))
    imp = Anki2Importer(empty, tmp.path)
    imp.run()
    assert os.listdir(empty.media.dir()) == ["foo.mp3"]
    n = empty.getNote(empty.db.scalar("select id from notes"))
    assert "foo.mp3" in n.fields[0]
    # if the local file content is different, and import should trigger a
    # rename
    empty.remCards(empty.db.list("select id from cards"))
    open(os.path.join(empty.media.dir(), "foo.mp3"), "w").write("bar")
    imp = Anki2Importer(empty, tmp.path)
    imp.run()
    assert sorted(os.listdir(empty.media.dir())) == [
        "foo.mp3", "foo_%s.mp3" % mid]
    n = empty.getNote(empty.db.scalar("select id from notes"))
    assert "_" in n.fields[0]
    # if the localized media file already exists, we rewrite the note and
    # media
    empty.remCards(empty.db.list("select id from cards"))
    open(os.path.join(empty.media.dir(), "foo.mp3"), "w").write("bar")
    imp = Anki2Importer(empty, tmp.path)
    imp.run()
    assert sorted(os.listdir(empty.media.dir())) == [
        "foo.mp3", "foo_%s.mp3" % mid]
    assert sorted(os.listdir(empty.media.dir())) == [
        "foo.mp3", "foo_%s.mp3" % mid]
    n = empty.getNote(empty.db.scalar("select id from notes"))
    assert "_" in n.fields[0]

def test_apkg():
    tmp = getEmptyDeck()
    apkg = unicode(os.path.join(testDir, "support/media.apkg"))
    imp = AnkiPackageImporter(tmp, apkg)
    assert os.listdir(tmp.media.dir()) == []
    imp.run()
    assert os.listdir(tmp.media.dir()) == ['foo.wav']
    # importing again should be idempotent in terms of media
    tmp.remCards(tmp.db.list("select id from cards"))
    imp = AnkiPackageImporter(tmp, apkg)
    imp.run()
    assert os.listdir(tmp.media.dir()) == ['foo.wav']
    # but if the local file has different data, it will rename
    tmp.remCards(tmp.db.list("select id from cards"))
    open(os.path.join(tmp.media.dir(), "foo.wav"), "w").write("xyz")
    imp = AnkiPackageImporter(tmp, apkg)
    imp.run()
    assert len(os.listdir(tmp.media.dir())) == 2

def test_anki1():
    # get the deck path to import
    tmp = getUpgradeDeckPath()
    # make sure media is imported properly through the upgrade
    mdir = tmp.replace(".anki2", ".media")
    if not os.path.exists(mdir):
        os.mkdir(mdir)
    open(os.path.join(mdir, "_foo.jpg"), "w").write("foo")
    # create a new empty deck
    dst = getEmptyDeck()
    # import src into dst
    imp = Anki1Importer(dst, tmp)
    imp.run()
    def check():
        assert dst.noteCount() == srcNotes
        assert dst.cardCount() == srcCards
        assert len(os.listdir(dst.media.dir())) == 1
    check()
    # importing should be idempotent
    imp = Anki1Importer(dst, tmp)
    imp.run()
    check()

def test_anki1_diffmodels():
    # create a new empty deck
    dst = getEmptyDeck()
    # import the 1 card version of the model
    tmp = getUpgradeDeckPath("diffmodels1.anki")
    imp = Anki1Importer(dst, tmp)
    imp.run()
    before = dst.noteCount()
    # repeating the process should do nothing
    imp = Anki1Importer(dst, tmp)
    imp.run()
    assert before == dst.noteCount()
    # then the 2 card version
    tmp = getUpgradeDeckPath("diffmodels2.anki")
    imp = Anki1Importer(dst, tmp)
    imp.run()
    after = dst.noteCount()
    # as the model schemas differ, should have been imported as new model
    assert after == before + 1
    # repeating the process should do nothing
    beforeModels = len(dst.models.all())
    imp = Anki1Importer(dst, tmp)
    imp.run()
    after = dst.noteCount()
    assert after == before + 1
    assert beforeModels == len(dst.models.all())

def test_anki2_diffmodels():
    # create a new empty deck
    dst = getEmptyDeck()
    # import the 1 card version of the model
    tmp = getUpgradeDeckPath("diffmodels2-1.apkg")
    imp = AnkiPackageImporter(dst, tmp)
    imp.run()
    before = dst.noteCount()
    # repeating the process should do nothing
    imp = AnkiPackageImporter(dst, tmp)
    imp.run()
    assert before == dst.noteCount()
    # then the 2 card version
    tmp = getUpgradeDeckPath("diffmodels2-2.apkg")
    imp = AnkiPackageImporter(dst, tmp)
    imp.run()
    after = dst.noteCount()
    # as the model schemas differ, should have been imported as new model
    assert after == before + 1
    # and the new model should have both cards
    assert dst.cardCount() == 3
    # repeating the process should do nothing
    imp = AnkiPackageImporter(dst, tmp)
    imp.run()
    after = dst.noteCount()
    assert after == before + 1
    assert dst.cardCount() == 3

def test_csv():
    deck = getEmptyDeck()
    file = unicode(os.path.join(testDir, "support/text-2fields.txt"))
    i = TextImporter(deck, file)
    i.initMapping()
    i.run()
    # four problems - too many & too few fields, a missing front, and a
    # duplicate entry
    assert len(i.log) == 5
    assert i.total == 5
    # if we run the import again, it should update instead
    i.run()
    assert len(i.log) == 5
    assert i.total == 5
    # but importing should not clobber tags if they're unmapped
    n = deck.getNote(deck.db.scalar("select id from notes"))
    n.addTag("test")
    n.flush()
    i.run()
    n.load()
    assert n.tags == ['test']
    # if add-only mode, count will be 0
    i.importMode = 1
    i.run()
    assert i.total == 0
    # and if dupes mode, will reimport everything
    assert deck.cardCount() == 5
    i.importMode = 2
    i.run()
    # includes repeated field
    assert i.total == 6
    assert deck.cardCount() == 11
    deck.close()

def test_csv2():
    deck = getEmptyDeck()
    mm = deck.models
    m = mm.current()
    f = mm.newField("Three")
    mm.addField(m, f)
    mm.save(m)
    n = deck.newNote()
    n['Front'] = "1"
    n['Back'] = "2"
    n['Three'] = "3"
    deck.addNote(n)
    # an update with unmapped fields should not clobber those fields
    file = unicode(os.path.join(testDir, "support/text-update.txt"))
    i = TextImporter(deck, file)
    i.initMapping()
    i.run()
    n.load()
    assert n['Front'] == "1"
    assert n['Back'] == "x"
    assert n['Three'] == "3"
    deck.close()

def test_supermemo_xml_01_unicode():
    deck = getEmptyDeck()
    file = unicode(os.path.join(testDir, "support/supermemo1.xml"))
    i = SupermemoXmlImporter(deck, file)
    #i.META.logToStdOutput = True
    i.run()
    assert i.total == 1
    cid = deck.db.scalar("select id from cards")
    c = deck.getCard(cid)
    assert c.factor == 5701
    assert c.reps == 7
    deck.close()

def test_mnemo():
    deck = getEmptyDeck()
    file = unicode(os.path.join(testDir, "support/mnemo.db"))
    i = MnemosyneImporter(deck, file)
    i.run()
    assert deck.cardCount() == 7
    assert "a_longer_tag" in deck.tags.all()
    assert deck.db.scalar("select count() from cards where type = 0") == 1
    deck.close()

########NEW FILE########
__FILENAME__ = test_latex
# coding: utf-8

import os
from tests.shared import assertException, getEmptyDeck
from anki.utils import stripHTML, intTime
from anki.hooks import addHook

def test_latex():
    d = getEmptyDeck()
    # change latex cmd to simulate broken build
    import anki.latex
    anki.latex.latexCmd[0] = "nolatex"
    # add a note with latex
    f = d.newNote()
    f['Front'] = u"[latex]hello[/latex]"
    d.addNote(f)
    # but since latex couldn't run, there's nothing there
    assert len(os.listdir(d.media.dir())) == 0
    # check the error message
    msg = f.cards()[0].q()
    assert "executing latex" in msg
    assert "installed" in msg
    # check if we have latex installed, and abort test if we don't
    if (not os.path.exists("/usr/bin/latex") and
        not os.path.exists("/usr/texbin/latex")):
        print "aborting test; latex is not installed"
        return
    # fix path
    anki.latex.latexCmd[0] = "latex"
    # check media db should cause latex to be generated
    d.media.check()
    assert len(os.listdir(d.media.dir())) == 1
    assert ".png" in f.cards()[0].q()
    # adding new notes should cause generation on question display
    f = d.newNote()
    f['Front'] = u"[latex]world[/latex]"
    d.addNote(f)
    f.cards()[0].q()
    assert len(os.listdir(d.media.dir())) == 2
    # another note with the same media should reuse
    f = d.newNote()
    f['Front'] = u" [latex]world[/latex]"
    d.addNote(f)
    assert len(os.listdir(d.media.dir())) == 2
    oldcard = f.cards()[0]
    assert ".png" in oldcard.q()
    # if we turn off building, then previous cards should work, but cards with
    # missing media will show the latex
    anki.latex.build = False
    f = d.newNote()
    f['Front'] = u"[latex]foo[/latex]"
    d.addNote(f)
    assert len(os.listdir(d.media.dir())) == 2
    assert stripHTML(f.cards()[0].q()) == "[latex]foo[/latex]"
    assert ".png" in oldcard.q()

########NEW FILE########
__FILENAME__ = test_media
# coding: utf-8

import tempfile, os, time
from anki.utils import checksum
from shared import getEmptyDeck, testDir

# copying files to media folder
def test_add():
    d = getEmptyDeck()
    dir = tempfile.mkdtemp(prefix="anki")
    path = os.path.join(dir, "foo.jpg")
    open(path, "w").write("hello")
    # new file, should preserve name
    assert d.media.addFile(path) == "foo.jpg"
    # adding the same file again should not create a duplicate
    assert d.media.addFile(path) == "foo.jpg"
    # but if it has a different md5, it should
    open(path, "w").write("world")
    assert d.media.addFile(path) == "foo (1).jpg"

def test_strings():
    d = getEmptyDeck()
    mf = d.media.filesInStr
    mid = d.models.models.keys()[0]
    assert mf(mid, "aoeu") == []
    assert mf(mid, "aoeu<img src='foo.jpg'>ao") == ["foo.jpg"]
    assert mf(mid, "aoeu<img src=foo bar.jpg>ao") == ["foo bar.jpg"]
    assert mf(mid, "aoeu<img src=\"foo.jpg\">ao") == ["foo.jpg"]
    assert mf(mid, "aoeu<img src=\"foo.jpg\"><img class=yo src=fo>ao") == [
            "foo.jpg", "fo"]
    assert mf(mid, "aou[sound:foo.mp3]aou") == ["foo.mp3"]
    sp = d.media.strip
    assert sp("aoeu") == "aoeu"
    assert sp("aoeu[sound:foo.mp3]aoeu") == "aoeuaoeu"
    assert sp("a<img src=yo>oeu") == "aoeu"
    es = d.media.escapeImages
    assert es("aoeu") == "aoeu"
    assert es("<img src='http://foo.com'>") == "<img src='http://foo.com'>"
    assert es('<img src="foo bar.jpg">') == '<img src="foo%20bar.jpg">'

def test_deckIntegration():
    d = getEmptyDeck()
    # create a media dir
    d.media.dir()
    # put a file into it
    file = unicode(os.path.join(testDir, "support/fake.png"))
    d.media.addFile(file)
    # add a note which references it
    f = d.newNote()
    f['Front'] = u"one"; f['Back'] = u"<img src='fake.png'>"
    d.addNote(f)
    # and one which references a non-existent file
    f = d.newNote()
    f['Front'] = u"one"; f['Back'] = u"<img src='fake2.png'>"
    d.addNote(f)
    # and add another file which isn't used
    open(os.path.join(d.media.dir(), "foo.jpg"), "wb").write("test")
    # check media
    ret = d.media.check()
    assert ret[0] == ["fake2.png"]
    assert ret[1] == ["foo.jpg"]

def test_changes():
    d = getEmptyDeck()
    assert d.media._changed()
    def added():
        return d.media.db.execute("select fname from log where type = 0")
    assert not list(added())
    assert not list(d.media.removed())
    # add a file
    dir = tempfile.mkdtemp(prefix="anki")
    path = os.path.join(dir, "foo.jpg")
    open(path, "w").write("hello")
    time.sleep(1)
    path = d.media.addFile(path)
    # should have been logged
    d.media.findChanges()
    assert list(added())
    assert not list(d.media.removed())
    # if we modify it, the cache won't notice
    time.sleep(1)
    open(path, "w").write("world")
    assert len(list(added())) == 1
    assert not list(d.media.removed())
    # but if we add another file, it will
    time.sleep(1)
    open(path+"2", "w").write("yo")
    d.media.findChanges()
    assert len(list(added())) == 2
    assert not list(d.media.removed())
    # deletions should get noticed too
    time.sleep(1)
    os.unlink(path+"2")
    d.media.findChanges()
    assert len(list(added())) == 1
    assert len(list(d.media.removed())) == 1

########NEW FILE########
__FILENAME__ = test_models
# coding: utf-8

from tests.shared import getEmptyDeck, assertException
from anki.utils import stripHTML, joinFields

def test_modelDelete():
    deck = getEmptyDeck()
    f = deck.newNote()
    f['Front'] = u'1'
    f['Back'] = u'2'
    deck.addNote(f)
    assert deck.cardCount() == 1
    deck.models.rem(deck.models.current())
    assert deck.cardCount() == 0

def test_modelCopy():
    deck = getEmptyDeck()
    m = deck.models.current()
    m2 = deck.models.copy(m)
    assert m2['name'] == "Basic copy"
    assert m2['id'] != m['id']
    assert len(m2['flds']) == 2
    assert len(m['flds']) == 2
    assert len(m2['flds']) == len(m['flds'])
    assert len(m['tmpls']) == 1
    assert len(m2['tmpls']) == 1
    assert deck.models.scmhash(m) == deck.models.scmhash(m2)

def test_fields():
    d = getEmptyDeck()
    f = d.newNote()
    f['Front'] = u'1'
    f['Back'] = u'2'
    d.addNote(f)
    m = d.models.current()
    # make sure renaming a field updates the templates
    d.models.renameField(m, m['flds'][0], "NewFront")
    assert "{{NewFront}}" in m['tmpls'][0]['qfmt']
    h = d.models.scmhash(m)
    # add a field
    f = d.models.newField(m)
    f['name'] = "foo"
    d.models.addField(m, f)
    assert d.getNote(d.models.nids(m)[0]).fields == ["1", "2", ""]
    assert d.models.scmhash(m) != h
    # rename it
    d.models.renameField(m, f, "bar")
    assert d.getNote(d.models.nids(m)[0])['bar'] == ''
    # delete back
    d.models.remField(m, m['flds'][1])
    assert d.getNote(d.models.nids(m)[0]).fields == ["1", ""]
    # move 0 -> 1
    d.models.moveField(m, m['flds'][0], 1)
    assert d.getNote(d.models.nids(m)[0]).fields == ["", "1"]
    # move 1 -> 0
    d.models.moveField(m, m['flds'][1], 0)
    assert d.getNote(d.models.nids(m)[0]).fields == ["1", ""]
    # add another and put in middle
    f = d.models.newField(m)
    f['name'] = "baz"
    d.models.addField(m, f)
    f = d.getNote(d.models.nids(m)[0])
    f['baz'] = "2"
    f.flush()
    assert d.getNote(d.models.nids(m)[0]).fields == ["1", "", "2"]
    # move 2 -> 1
    d.models.moveField(m, m['flds'][2], 1)
    assert d.getNote(d.models.nids(m)[0]).fields == ["1", "2", ""]
    # move 0 -> 2
    d.models.moveField(m, m['flds'][0], 2)
    assert d.getNote(d.models.nids(m)[0]).fields == ["2", "", "1"]
    # move 0 -> 1
    d.models.moveField(m, m['flds'][0], 1)
    assert d.getNote(d.models.nids(m)[0]).fields == ["", "2", "1"]

def test_templates():
    d = getEmptyDeck()
    m = d.models.current(); mm = d.models
    t = mm.newTemplate("Reverse")
    t['qfmt'] = "{{Back}}"
    t['afmt'] = "{{Front}}"
    mm.addTemplate(m, t)
    mm.save(m)
    f = d.newNote()
    f['Front'] = u'1'
    f['Back'] = u'2'
    d.addNote(f)
    assert d.cardCount() == 2
    (c, c2) = f.cards()
    # first card should have first ord
    assert c.ord == 0
    assert c2.ord == 1
    # switch templates
    d.models.moveTemplate(m, c.template(), 1)
    c.load(); c2.load()
    assert c.ord == 1
    assert c2.ord == 0
    # removing a template should delete its cards
    assert d.models.remTemplate(m, m['tmpls'][0])
    assert d.cardCount() == 1
    # and should have updated the other cards' ordinals
    c = f.cards()[0]
    assert c.ord == 0
    assert stripHTML(c.q()) == "1"
    # it shouldn't be possible to orphan notes by removing templates
    t = mm.newTemplate(m)
    mm.addTemplate(m, t)
    assert not d.models.remTemplate(m, m['tmpls'][0])

def test_text():
    d = getEmptyDeck()
    m = d.models.current()
    m['tmpls'][0]['qfmt'] = "{{text:Front}}"
    d.models.save(m)
    f = d.newNote()
    f['Front'] = u'hello<b>world'
    d.addNote(f)
    assert "helloworld" in f.cards()[0].q()

def test_cloze():
    d = getEmptyDeck()
    d.models.setCurrent(d.models.byName("Cloze"))
    f = d.newNote()
    assert f.model()['name'] == "Cloze"
    # a cloze model with no clozes is not empty
    f['Text'] = u'nothing'
    assert d.addNote(f)
    # try with one cloze
    f = d.newNote()
    f['Text'] = "hello {{c1::world}}"
    assert d.addNote(f) == 1
    assert "hello <span class=cloze>[...]</span>" in f.cards()[0].q()
    assert "hello <span class=cloze>world</span>" in f.cards()[0].a()
    # and with a comment
    f = d.newNote()
    f['Text'] = "hello {{c1::world::typical}}"
    assert d.addNote(f) == 1
    assert "<span class=cloze>[typical]</span>" in f.cards()[0].q()
    assert "<span class=cloze>world</span>" in f.cards()[0].a()
    # and with 2 clozes
    f = d.newNote()
    f['Text'] = "hello {{c1::world}} {{c2::bar}}"
    assert d.addNote(f) == 2
    (c1, c2) = f.cards()
    assert "<span class=cloze>[...]</span> bar" in c1.q()
    assert "<span class=cloze>world</span> bar" in c1.a()
    assert "world <span class=cloze>[...]</span>" in c2.q()
    assert "world <span class=cloze>bar</span>" in c2.a()
    # if there are multiple answers for a single cloze, they are given in a
    # list
    f = d.newNote()
    f['Text'] = "a {{c1::b}} {{c1::c}}"
    assert d.addNote(f) == 1
    assert "<span class=cloze>b</span> <span class=cloze>c</span>" in (
        f.cards()[0].a())
    # if we add another cloze, a card should be generated
    cnt = d.cardCount()
    f['Text'] = "{{c2::hello}} {{c1::foo}}"
    f.flush()
    assert d.cardCount() == cnt + 1
    # 0 or negative indices are not supported
    f['Text'] += "{{c0::zero}} {{c-1:foo}}"
    f.flush()
    assert len(f.cards()) == 2

def test_modelChange():
    deck = getEmptyDeck()
    basic = deck.models.byName("Basic")
    cloze = deck.models.byName("Cloze")
    # enable second template and add a note
    m = deck.models.current(); mm = deck.models
    t = mm.newTemplate("Reverse")
    t['qfmt'] = "{{Back}}"
    t['afmt'] = "{{Front}}"
    mm.addTemplate(m, t)
    mm.save(m)
    f = deck.newNote()
    f['Front'] = u'f'
    f['Back'] = u'b123'
    deck.addNote(f)
    # switch fields
    map = {0: 1, 1: 0}
    deck.models.change(basic, [f.id], basic, map, None)
    f.load()
    assert f['Front'] == 'b123'
    assert f['Back'] == 'f'
    # switch cards
    c0 = f.cards()[0]
    c1 = f.cards()[1]
    assert "b123" in c0.q()
    assert "f" in c1.q()
    assert c0.ord == 0
    assert c1.ord == 1
    deck.models.change(basic, [f.id], basic, None, map)
    f.load(); c0.load(); c1.load()
    assert "f" in c0.q()
    assert "b123" in c1.q()
    assert c0.ord == 1
    assert c1.ord == 0
    # .cards() returns cards in order
    assert f.cards()[0].id == c1.id
    # delete first card
    map = {0: None, 1: 1}
    deck.models.change(basic, [f.id], basic, None, map)
    f.load()
    c0.load()
    # the card was deleted
    try:
        c1.load()
        assert 0
    except TypeError:
        pass
    # but we have two cards, as a new one was generated
    assert len(f.cards()) == 2
    # an unmapped field becomes blank
    assert f['Front'] == 'b123'
    assert f['Back'] == 'f'
    deck.models.change(basic, [f.id], basic, map, None)
    f.load()
    assert f['Front'] == ''
    assert f['Back'] == 'f'
    # another note to try model conversion
    f = deck.newNote()
    f['Front'] = u'f2'
    f['Back'] = u'b2'
    deck.addNote(f)
    assert deck.models.useCount(basic) == 2
    assert deck.models.useCount(cloze) == 0
    map = {0: 0, 1: 1}
    deck.models.change(basic, [f.id], cloze, map, map)
    f.load()
    assert f['Text'] == "f2"
    assert len(f.cards()) == 2
    # back the other way, with deletion of second ord
    deck.models.remTemplate(basic, basic['tmpls'][1])
    assert deck.db.scalar("select count() from cards where nid = ?", f.id) == 2
    deck.models.change(cloze, [f.id], basic, map, map)
    assert deck.db.scalar("select count() from cards where nid = ?", f.id) == 1

def test_availOrds():
    d = getEmptyDeck()
    m = d.models.current(); mm = d.models
    t = m['tmpls'][0]
    f = d.newNote()
    f['Front'] = "1"
    # simple templates
    assert mm.availOrds(m, joinFields(f.fields)) == [0]
    t['qfmt'] = "{{Back}}"
    mm.save(m, templates=True)
    assert not mm.availOrds(m, joinFields(f.fields))
    # AND
    t['qfmt'] = "{{#Front}}{{#Back}}{{Front}}{{/Back}}{{/Front}}"
    mm.save(m, templates=True)
    assert not mm.availOrds(m, joinFields(f.fields))
    t['qfmt'] = "{{#Front}}\n{{#Back}}\n{{Front}}\n{{/Back}}\n{{/Front}}"
    mm.save(m, templates=True)
    assert not mm.availOrds(m, joinFields(f.fields))
    # OR
    t['qfmt'] = "{{Front}}\n{{Back}}"
    mm.save(m, templates=True)
    assert mm.availOrds(m, joinFields(f.fields)) == [0]
    t['Front'] = ""
    t['Back'] = "1"
    assert mm.availOrds(m, joinFields(f.fields)) == [0]

########NEW FILE########
__FILENAME__ = test_remote_sync
# coding: utf-8

import nose, os, tempfile, shutil, time
from tests.shared import assertException

from anki.errors import *
from anki.utils import intTime
from anki.sync import Syncer, FullSyncer, LocalServer, RemoteServer, \
    MediaSyncer, RemoteMediaServer, httpCon
from anki.notes import Note
from anki.cards import Card
from tests.shared import getEmptyDeck
from anki import Collection as aopen

deck1=None
deck2=None
client=None
server=None
server2=None

# Remote tests
##########################################################################

import tests.test_sync as ts
from tests.test_sync import setup_basic
import anki.sync
anki.sync.SYNC_URL = "http://localhost:6543/sync/"
TEST_USER = "synctest@ichi2.net"
TEST_PASS = "synctest"
TEST_HKEY = "tG5CD9eZbWOru3Yw"
TEST_REMOTE = True

def setup_remote():
    setup_basic()
    # mark deck1 as changed
    ts.deck1.save()
    ts.server = RemoteServer(TEST_HKEY)
    ts.client.server = ts.server

@nose.with_setup(setup_remote)
def test_meta():
    global TEST_REMOTE
    try:
        # if the key is wrong, meta returns nothing
        ts.server.hkey = "abc"
        assert not ts.server.meta()
    except Exception, e:
        if e.errno == 61:
            TEST_REMOTE = False
            print "aborting; server offline"
            return
    ts.server.hkey = TEST_HKEY
    (mod, scm, usn, tstamp, mediaUSN) = ts.server.meta()
    assert mod
    assert scm
    assert mod != ts.client.col.mod
    assert abs(tstamp - time.time()) < 3

@nose.with_setup(setup_remote)
def test_hkey():
    if not TEST_REMOTE:
        return
    assert not ts.server.hostKey(TEST_USER, "wrongpass")
    ts.server.hkey = "willchange"
    k = ts.server.hostKey(TEST_USER, TEST_PASS)
    assert k == ts.server.hkey == TEST_HKEY

@nose.with_setup(setup_remote)
def test_download():
    if not TEST_REMOTE:
        return
    f = FullSyncer(ts.client.col, "abc", ts.server.con)
    assertException(Exception, f.download)
    f.hkey = TEST_HKEY
    f.download()

@nose.with_setup(setup_remote)
def test_remoteSync():
    if not TEST_REMOTE:
        return
    # not yet associated, so will require a full sync
    assert ts.client.sync() == "fullSync"
    # upload
    f = FullSyncer(ts.client.col, TEST_HKEY, ts.server.con)
    f.upload()
    ts.client.col.reopen()
    # should report no changes
    assert ts.client.sync() == "noChanges"
    # bump local col
    ts.client.col.setMod()
    ts.client.col.save()
    assert ts.client.sync() == "success"
    # again, no changes
    assert ts.client.sync() == "noChanges"
    # downloading the remote col should give us the same mod
    lmod = ts.client.col.mod
    f = FullSyncer(ts.client.col, TEST_HKEY, ts.server.con)
    f.download()
    d = aopen(ts.client.col.path)
    assert d.mod == lmod

# Remote　media tests
##########################################################################
# We can't run useful tests for local media, because the desktop code assumes
# the current directory is the media folder.

def setup_remoteMedia():
    setup_basic()
    con = httpCon()
    ts.server = RemoteMediaServer(TEST_HKEY, con)
    ts.server2 = RemoteServer(TEST_HKEY)
    ts.client = MediaSyncer(ts.deck1, ts.server)

@nose.with_setup(setup_remoteMedia)
def test_media():
    if not TEST_REMOTE:
        return
    ts.server.mediatest("reset")
    assert len(os.listdir(ts.deck1.media.dir())) == 0
    assert ts.server.mediatest("count") == 0
    # initially, nothing to do
    assert ts.client.sync(ts.server2.meta()[4]) == "noChanges"
    # add a file
    time.sleep(1)
    os.chdir(ts.deck1.media.dir())
    p = os.path.join(ts.deck1.media.dir(), "foo.jpg")
    open(p, "wb").write("foo")
    assert len(os.listdir(ts.deck1.media.dir())) == 1
    assert ts.server.mediatest("count") == 0
    assert ts.client.sync(ts.server2.meta()[4]) == "success"
    assert ts.client.sync(ts.server2.meta()[4]) == "noChanges"
    time.sleep(1)
    # should have been synced
    assert len(os.listdir(ts.deck1.media.dir())) == 1
    assert ts.server.mediatest("count") == 1
    # if we remove the file, should be removed
    os.unlink(p)
    assert ts.client.sync(ts.server2.meta()[4]) == "success"
    assert ts.client.sync(ts.server2.meta()[4]) == "noChanges"
    assert len(os.listdir(ts.deck1.media.dir())) == 0
    assert ts.server.mediatest("count") == 0
    # we should be able to add it again
    time.sleep(1)
    open(p, "wb").write("foo")
    assert ts.client.sync(ts.server2.meta()[4]) == "success"
    assert ts.client.sync(ts.server2.meta()[4]) == "noChanges"
    assert len(os.listdir(ts.deck1.media.dir())) == 1
    assert ts.server.mediatest("count") == 1
    # if we modify it, it should get sent too. also we set the zip size very
    # low here, so that we can test splitting into multiple zips
    import anki.media; anki.media.SYNC_ZIP_SIZE = 1
    time.sleep(1)
    open(p, "wb").write("bar")
    open(p+"2", "wb").write("baz")
    assert len(os.listdir(ts.deck1.media.dir())) == 2
    assert ts.client.sync(ts.server2.meta()[4]) == "success"
    assert ts.client.sync(ts.server2.meta()[4]) == "noChanges"
    assert len(os.listdir(ts.deck1.media.dir())) == 2
    assert ts.server.mediatest("count") == 2
    # if we lose our media db, we should be able to bring it back in sync
    time.sleep(1)
    ts.deck1.media.close()
    os.unlink(ts.deck1.media.dir()+".db")
    ts.deck1.media.connect()
    assert ts.client.sync(ts.server2.meta()[4]) == "success"
    assert ts.client.sync(ts.server2.meta()[4]) == "noChanges"
    assert len(os.listdir(ts.deck1.media.dir())) == 2
    assert ts.server.mediatest("count") == 2
    # if we send an unchanged file, the server should cope
    time.sleep(1)
    ts.deck1.media.db.execute("insert into log values ('foo.jpg', 0)")
    assert ts.client.sync(ts.server2.meta()[4]) == "success"
    assert ts.client.sync(ts.server2.meta()[4]) == "noChanges"
    assert len(os.listdir(ts.deck1.media.dir())) == 2
    assert ts.server.mediatest("count") == 2
    # if we remove foo.jpg on the ts.server, the removal should be synced
    assert ts.server.mediatest("removefoo") == "OK"
    assert ts.client.sync(ts.server2.meta()[4]) == "success"
    assert len(os.listdir(ts.deck1.media.dir())) == 1
    assert ts.server.mediatest("count") == 1

########NEW FILE########
__FILENAME__ = test_sched
# coding: utf-8

import time, copy
from tests.shared import assertException, getEmptyDeck
from anki.utils import stripHTML, intTime
from anki.hooks import addHook
from anki.consts import *

def test_basics():
    d = getEmptyDeck()
    d.reset()
    assert not d.sched.getCard()

def test_new():
    d = getEmptyDeck()
    d.reset()
    assert d.sched.newCount == 0
    # add a note
    f = d.newNote()
    f['Front'] = u"one"; f['Back'] = u"two"
    d.addNote(f)
    d.reset()
    assert d.sched.newCount == 1
    # fetch it
    c = d.sched.getCard()
    assert c
    assert c.queue == 0
    assert c.type == 0
    # if we answer it, it should become a learn card
    t = intTime()
    d.sched.answerCard(c, 1)
    assert c.queue == 1
    assert c.type == 1
    assert c.due >= t
    # the default order should ensure siblings are not seen together, and
    # should show all cards
    m = d.models.current(); mm = d.models
    t = mm.newTemplate("Reverse")
    t['qfmt'] = "{{Back}}"
    t['afmt'] = "{{Front}}"
    mm.addTemplate(m, t)
    mm.save(m)
    f = d.newNote()
    f['Front'] = u"2"; f['Back'] = u"2"
    d.addNote(f)
    f = d.newNote()
    f['Front'] = u"3"; f['Back'] = u"3"
    d.addNote(f)
    d.reset()
    qs = ("2", "3", "2", "3")
    for n in range(4):
        c = d.sched.getCard()
        assert qs[n] in c.q()
        d.sched.answerCard(c, 2)

def test_newLimits():
    d = getEmptyDeck()
    # add some notes
    g2 = d.decks.id("Default::foo")
    for i in range(30):
        f = d.newNote()
        f['Front'] = str(i)
        if i > 4:
            f.model()['did'] = g2
        d.addNote(f)
    # give the child deck a different configuration
    c2 = d.decks.confId("new conf")
    d.decks.setConf(d.decks.get(g2), c2)
    d.reset()
    # both confs have defaulted to a limit of 20
    assert d.sched.newCount == 20
    # first card we get comes from parent
    c = d.sched.getCard()
    assert c.did == 1
    # limit the parent to 10 cards, meaning we get 10 in total
    conf1 = d.decks.confForDid(1)
    conf1['new']['perDay'] = 10
    d.reset()
    assert d.sched.newCount == 10
    # if we limit child to 4, we should get 9
    conf2 = d.decks.confForDid(g2)
    conf2['new']['perDay'] = 4
    d.reset()
    assert d.sched.newCount == 9

def test_newBoxes():
    d = getEmptyDeck()
    f = d.newNote()
    f['Front'] = u"one"
    d.addNote(f)
    d.reset()
    c = d.sched.getCard()
    d.sched._cardConf(c)['new']['delays'] = [1,2,3,4,5]
    d.sched.answerCard(c, 2)
    # should handle gracefully
    d.sched._cardConf(c)['new']['delays'] = [1]
    d.sched.answerCard(c, 2)

def test_learn():
    d = getEmptyDeck()
    # add a note
    f = d.newNote()
    f['Front'] = u"one"; f['Back'] = u"two"
    f = d.addNote(f)
    # set as a learn card and rebuild queues
    d.db.execute("update cards set queue=0, type=0")
    d.reset()
    # sched.getCard should return it, since it's due in the past
    c = d.sched.getCard()
    assert c
    d.sched._cardConf(c)['new']['delays'] = [0.5, 3, 10]
    # fail it
    d.sched.answerCard(c, 1)
    # it should have three reps left to graduation
    assert c.left%1000 == 3
    assert c.left/1000 == 3
    # it should by due in 30 seconds
    t = round(c.due - time.time())
    assert t >= 25 and t <= 40
    # pass it once
    d.sched.answerCard(c, 2)
    # it should by due in 3 minutes
    assert round(c.due - time.time()) in (179, 180)
    assert c.left%1000 == 2
    assert c.left/1000 == 2
    # check log is accurate
    log = d.db.first("select * from revlog order by id desc")
    assert log[3] == 2
    assert log[4] == -180
    assert log[5] == -30
    # pass again
    d.sched.answerCard(c, 2)
    # it should by due in 10 minutes
    assert round(c.due - time.time()) in (599, 600)
    assert c.left%1000 == 1
    assert c.left/1000 == 1
    # the next pass should graduate the card
    assert c.queue == 1
    assert c.type == 1
    d.sched.answerCard(c, 2)
    assert c.queue == 2
    assert c.type == 2
    # should be due tomorrow, with an interval of 1
    assert c.due == d.sched.today+1
    assert c.ivl == 1
    # or normal removal
    c.type = 0
    c.queue = 1
    d.sched.answerCard(c, 3)
    assert c.type == 2
    assert c.queue == 2
    assert c.ivl == 4
    # revlog should have been updated each time
    assert d.db.scalar("select count() from revlog where type = 0") == 5
    # now failed card handling
    c.type = 2
    c.queue = 1
    c.odue = 123
    d.sched.answerCard(c, 3)
    assert c.due == 123
    assert c.type == 2
    assert c.queue == 2
    # we should be able to remove manually, too
    c.type = 2
    c.queue = 1
    c.odue = 321
    c.flush()
    d.sched.removeLrn()
    c.load()
    assert c.queue == 2
    assert c.due == 321

def test_learn_collapsed():
    d = getEmptyDeck()
    # add 2 notes
    f = d.newNote()
    f['Front'] = u"1"
    f = d.addNote(f)
    f = d.newNote()
    f['Front'] = u"2"
    f = d.addNote(f)
    # set as a learn card and rebuild queues
    d.db.execute("update cards set queue=0, type=0")
    d.reset()
    # should get '1' first
    c = d.sched.getCard()
    assert c.q().endswith("1")
    # pass it so it's due in 10 minutes
    d.sched.answerCard(c, 2)
    # get the other card
    c = d.sched.getCard()
    assert c.q().endswith("2")
    # fail it so it's due in 1 minute
    d.sched.answerCard(c, 1)
    # we shouldn't get the same card again
    c = d.sched.getCard()
    assert not c.q().endswith("2")

def test_learn_day():
    d = getEmptyDeck()
    # add a note
    f = d.newNote()
    f['Front'] = u"one"
    f = d.addNote(f)
    d.sched.reset()
    c = d.sched.getCard()
    d.sched._cardConf(c)['new']['delays'] = [1, 10, 1440, 2880]
    # pass it
    d.sched.answerCard(c, 2)
    # two reps to graduate, 1 more today
    assert c.left%1000 == 3
    assert c.left/1000 == 1
    assert d.sched.counts() == (0, 1, 0)
    c = d.sched.getCard()
    ni = d.sched.nextIvl
    assert ni(c, 2) == 86400
    # answering it will place it in queue 3
    d.sched.answerCard(c, 2)
    assert c.due == d.sched.today+1
    assert c.queue == 3
    assert not d.sched.getCard()
    # for testing, move it back a day
    c.due -= 1
    c.flush()
    d.reset()
    assert d.sched.counts() == (0, 1, 0)
    c = d.sched.getCard()
    # nextIvl should work
    assert ni(c, 2) == 86400*2
    # if we fail it, it should be back in the correct queue
    d.sched.answerCard(c, 1)
    assert c.queue == 1
    d.undo()
    d.reset()
    c = d.sched.getCard()
    d.sched.answerCard(c, 2)
    # simulate the passing of another two days
    c.due -= 2
    c.flush()
    d.reset()
    # the last pass should graduate it into a review card
    assert ni(c, 2) == 86400
    d.sched.answerCard(c, 2)
    assert c.queue == c.type == 2
    # if the lapse step is tomorrow, failing it should handle the counts
    # correctly
    c.due = 0
    c.flush()
    d.reset()
    assert d.sched.counts() == (0, 0, 1)
    d.sched._cardConf(c)['lapse']['delays'] = [1440]
    c = d.sched.getCard()
    d.sched.answerCard(c, 1)
    assert c.queue == 3
    assert d.sched.counts() == (0, 0, 0)

def test_reviews():
    d = getEmptyDeck()
    # add a note
    f = d.newNote()
    f['Front'] = u"one"; f['Back'] = u"two"
    d.addNote(f)
    # set the card up as a review card, due 8 days ago
    c = f.cards()[0]
    c.type = 2
    c.queue = 2
    c.due = d.sched.today - 8
    c.factor = 2500
    c.reps = 3
    c.lapses = 1
    c.ivl = 100
    c.startTimer()
    c.flush()
    # save it for later use as well
    cardcopy = copy.copy(c)
    # failing it should put it in the learn queue with the default options
    ##################################################
    # different delay to new
    d.reset()
    d.sched._cardConf(c)['lapse']['delays'] = [2, 20]
    d.sched.answerCard(c, 1)
    assert c.queue == 1
    # it should be due tomorrow, with an interval of 1
    assert c.odue == d.sched.today + 1
    assert c.ivl == 1
    # but because it's in the learn queue, its current due time should be in
    # the future
    assert c.due >= time.time()
    assert (c.due - time.time()) > 119
    # factor should have been decremented
    assert c.factor == 2300
    # check counters
    assert c.lapses == 2
    assert c.reps == 4
    # check ests.
    ni = d.sched.nextIvl
    assert ni(c, 1) == 120
    assert ni(c, 2) == 20*60
    # try again with an ease of 2 instead
    ##################################################
    c = copy.copy(cardcopy)
    c.flush()
    d.sched.answerCard(c, 2)
    assert c.queue == 2
    # the new interval should be (100 + 8/4) * 1.2 = 122
    assert c.ivl == 122
    assert c.due == d.sched.today + 122
    # factor should have been decremented
    assert c.factor == 2350
    # check counters
    assert c.lapses == 1
    assert c.reps == 4
    # ease 3
    ##################################################
    c = copy.copy(cardcopy)
    c.flush()
    d.sched.answerCard(c, 3)
    # the new interval should be (100 + 8/2) * 2.5 = 260
    assert c.ivl == 260
    assert c.due == d.sched.today + 260
    # factor should have been left alone
    assert c.factor == 2500
    # ease 4
    ##################################################
    c = copy.copy(cardcopy)
    c.flush()
    d.sched.answerCard(c, 4)
    # the new interval should be (100 + 8) * 2.5 * 1.3 = 351
    assert c.ivl == 351
    assert c.due == d.sched.today + 351
    # factor should have been increased
    assert c.factor == 2650
    # leech handling
    ##################################################
    c = copy.copy(cardcopy)
    c.lapses = 7
    c.flush()
    # steup hook
    hooked = []
    def onLeech(card):
        hooked.append(1)
    addHook("leech", onLeech)
    d.sched.answerCard(c, 1)
    assert hooked
    assert c.queue == -1
    c.load()
    assert c.queue == -1

def test_button_spacing():
    d = getEmptyDeck()
    f = d.newNote()
    f['Front'] = u"one"
    d.addNote(f)
    # 1 day ivl review card due now
    c = f.cards()[0]
    c.type = 2
    c.queue = 2
    c.due = d.sched.today
    c.reps = 1
    c.ivl = 1
    c.startTimer()
    c.flush()
    d.reset()
    ni = d.sched.nextIvlStr
    assert ni(c, 2) == "2 days"
    assert ni(c, 3) == "3 days"
    assert ni(c, 4) == "4 days"

def test_overdue_lapse():
    # disabled in commit 3069729776990980f34c25be66410e947e9d51a2
    return
    d = getEmptyDeck()
    # add a note
    f = d.newNote()
    f['Front'] = u"one"
    d.addNote(f)
    # simulate a review that was lapsed and is now due for its normal review
    c = f.cards()[0]
    c.type = 2
    c.queue = 1
    c.due = -1
    c.odue = -1
    c.factor = 2500
    c.left = 2002
    c.ivl = 0
    c.flush()
    d.sched._clearOverdue = False
    # checkpoint
    d.save()
    d.sched.reset()
    assert d.sched.counts() == (0, 2, 0)
    c = d.sched.getCard()
    d.sched.answerCard(c, 3)
    # it should be due tomorrow
    assert c.due == d.sched.today + 1
    # revert to before
    d.rollback()
    d.sched._clearOverdue = True
    # with the default settings, the overdue card should be removed from the
    # learning queue
    d.sched.reset()
    assert d.sched.counts() == (0, 0, 1)

def test_finished():
    d = getEmptyDeck()
    # nothing due
    assert "Congratulations" in d.sched.finishedMsg()
    assert "limit" not in d.sched.finishedMsg()
    f = d.newNote()
    f['Front'] = u"one"; f['Back'] = u"two"
    d.addNote(f)
    # have a new card
    assert "new cards available" in d.sched.finishedMsg()
    # turn it into a review
    d.reset()
    c = f.cards()[0]
    c.startTimer()
    d.sched.answerCard(c, 3)
    # nothing should be due tomorrow, as it's due in a week
    assert "Congratulations" in d.sched.finishedMsg()
    assert "limit" not in d.sched.finishedMsg()

def test_nextIvl():
    d = getEmptyDeck()
    f = d.newNote()
    f['Front'] = u"one"; f['Back'] = u"two"
    d.addNote(f)
    d.reset()
    conf = d.decks.confForDid(1)
    conf['new']['delays'] = [0.5, 3, 10]
    conf['lapse']['delays'] = [1, 5, 9]
    c = d.sched.getCard()
    # new cards
    ##################################################
    ni = d.sched.nextIvl
    assert ni(c, 1) == 30
    assert ni(c, 2) == 180
    assert ni(c, 3) == 4*86400
    d.sched.answerCard(c, 1)
    # cards in learning
    ##################################################
    assert ni(c, 1) == 30
    assert ni(c, 2) == 180
    assert ni(c, 3) == 4*86400
    d.sched.answerCard(c, 2)
    assert ni(c, 1) == 30
    assert ni(c, 2) == 600
    assert ni(c, 3) == 4*86400
    d.sched.answerCard(c, 2)
    # normal graduation is tomorrow
    assert ni(c, 2) == 1*86400
    assert ni(c, 3) == 4*86400
    # lapsed cards
    ##################################################
    c.type = 2
    c.ivl = 100
    c.factor = 2500
    assert ni(c, 1) == 60
    assert ni(c, 2) == 100*86400
    assert ni(c, 3) == 100*86400
    # review cards
    ##################################################
    c.queue = 2
    c.ivl = 100
    c.factor = 2500
    # failing it should put it at 60s
    assert ni(c, 1) == 60
    # or 1 day if relearn is false
    d.sched._cardConf(c)['lapse']['delays']=[]
    assert ni(c, 1) == 1*86400
    # (* 100 1.2 86400)10368000.0
    assert ni(c, 2) == 10368000
    # (* 100 2.5 86400)21600000.0
    assert ni(c, 3) == 21600000
    # (* 100 2.5 1.3 86400)28080000.0
    assert ni(c, 4) == 28080000
    assert d.sched.nextIvlStr(c, 4) == "10.8 months"

def test_misc():
    d = getEmptyDeck()
    f = d.newNote()
    f['Front'] = u"one"
    d.addNote(f)
    c = f.cards()[0]
    # burying
    d.sched.buryNote(c.nid)
    d.reset()
    assert not d.sched.getCard()
    d.sched.unburyCards()
    d.reset()
    assert d.sched.getCard()

def test_suspend():
    d = getEmptyDeck()
    f = d.newNote()
    f['Front'] = u"one"
    d.addNote(f)
    c = f.cards()[0]
    # suspending
    d.reset()
    assert d.sched.getCard()
    d.sched.suspendCards([c.id])
    d.reset()
    assert not d.sched.getCard()
    # unsuspending
    d.sched.unsuspendCards([c.id])
    d.reset()
    assert d.sched.getCard()
    # should cope with rev cards being relearnt
    c.due = 0; c.ivl = 100; c.type = 2; c.queue = 2; c.flush()
    d.reset()
    c = d.sched.getCard()
    d.sched.answerCard(c, 1)
    assert c.due >= time.time()
    assert c.queue == 1
    assert c.type == 2
    d.sched.suspendCards([c.id])
    d.sched.unsuspendCards([c.id])
    c.load()
    assert c.queue == 2
    assert c.type == 2
    assert c.due == 1
    # should cope with cards in cram decks
    c.due = 1
    c.flush()
    cram = d.decks.newDyn("tmp")
    d.sched.rebuildDyn()
    c.load()
    assert c.due != 1
    assert c.did != 1
    d.sched.suspendCards([c.id])
    c.load()
    assert c.due == 1
    assert c.did == 1

def test_cram():
    d = getEmptyDeck()
    f = d.newNote()
    f['Front'] = u"one"
    d.addNote(f)
    c = f.cards()[0]
    c.ivl = 100
    c.type = c.queue = 2
    # due in 25 days, so it's been waiting 75 days
    c.due = d.sched.today + 25
    c.mod = 1
    c.factor = 2500
    c.startTimer()
    c.flush()
    d.reset()
    assert d.sched.counts() == (0,0,0)
    cardcopy = copy.copy(c)
    # create a dynamic deck and refresh it
    did = d.decks.newDyn("Cram")
    d.sched.rebuildDyn(did)
    d.reset()
    # should appear as new in the deck list
    assert sorted(d.sched.deckDueList())[0][4] == 1
    # and should appear in the counts
    assert d.sched.counts() == (1,0,0)
    # grab it and check estimates
    c = d.sched.getCard()
    assert d.sched.answerButtons(c) == 2
    assert d.sched.nextIvl(c, 1) == 600
    assert d.sched.nextIvl(c, 2) == 138*60*60*24
    cram = d.decks.get(did)
    cram['delays'] = [1, 10]
    assert d.sched.answerButtons(c) == 3
    assert d.sched.nextIvl(c, 1) == 60
    assert d.sched.nextIvl(c, 2) == 600
    assert d.sched.nextIvl(c, 3) == 138*60*60*24
    d.sched.answerCard(c, 2)
    # elapsed time was 75 days
    # factor = 2.5+1.2/2 = 1.85
    # int(75*1.85) = 138
    assert c.ivl == 138
    assert c.odue == 138
    assert c.queue == 1
    # should be logged as a cram rep
    assert d.db.scalar(
        "select type from revlog order by id desc limit 1") == 3
    # check ivls again
    assert d.sched.nextIvl(c, 1) == 60
    assert d.sched.nextIvl(c, 2) == 138*60*60*24
    assert d.sched.nextIvl(c, 3) == 138*60*60*24
    # when it graduates, due is updated
    c = d.sched.getCard()
    d.sched.answerCard(c, 2)
    assert c.ivl == 138
    assert c.due == 138
    assert c.queue == 2
    # and it will have moved back to the previous deck
    assert c.did == 1
    # cram the deck again
    d.sched.rebuildDyn(did)
    d.reset()
    c = d.sched.getCard()
    # check ivls again - passing should be idempotent
    assert d.sched.nextIvl(c, 1) == 60
    assert d.sched.nextIvl(c, 2) == 600
    assert d.sched.nextIvl(c, 3) == 138*60*60*24
    d.sched.answerCard(c, 2)
    assert c.ivl == 138
    assert c.odue == 138
    # fail
    d.sched.answerCard(c, 1)
    assert d.sched.nextIvl(c, 1) == 60
    assert d.sched.nextIvl(c, 2) == 600
    assert d.sched.nextIvl(c, 3) == 86400
    # delete the deck, returning the card mid-study
    d.decks.rem(d.decks.selected())
    assert len(d.sched.deckDueList()) == 1
    c.load()
    assert c.ivl == 1
    assert c.due == d.sched.today+1
    # make it due
    d.reset()
    assert d.sched.counts() == (0,0,0)
    c.due = -5
    c.ivl = 100
    c.flush()
    d.reset()
    assert d.sched.counts() == (0,0,1)
    # cram again
    did = d.decks.newDyn("Cram")
    d.sched.rebuildDyn(did)
    d.reset()
    assert d.sched.counts() == (0,0,1)
    c.load()
    assert d.sched.answerButtons(c) == 4
    # add a sibling so we can test minSpace, etc
    c2 = copy.deepcopy(c)
    c2.id = 123
    c2.ord = 1
    c2.due = 325
    c2.col = c.col
    c2.flush()
    # should be able to answer it
    c = d.sched.getCard()
    d.sched.answerCard(c, 4)
    # it should have been moved back to the original deck
    assert c.did == 1

def test_cram_rem():
    d = getEmptyDeck()
    f = d.newNote()
    f['Front'] = u"one"
    d.addNote(f)
    oldDue = f.cards()[0].due
    did = d.decks.newDyn("Cram")
    d.sched.rebuildDyn(did)
    d.reset()
    c = d.sched.getCard()
    d.sched.answerCard(c, 2)
    # answering the card will put it in the learning queue
    assert c.type == c.queue == 1
    assert c.due != oldDue
    # if we terminate cramming prematurely it should be set back to new
    d.sched.emptyDyn(did)
    c.load()
    assert c.type == c.queue == 0
    assert c.due == oldDue

def test_cram_resched():
    # add card
    d = getEmptyDeck()
    f = d.newNote()
    f['Front'] = u"one"
    d.addNote(f)
    # cram deck
    did = d.decks.newDyn("Cram")
    cram = d.decks.get(did)
    cram['resched'] = False
    d.sched.rebuildDyn(did)
    d.reset()
    # graduate should return it to new
    c = d.sched.getCard()
    ni = d.sched.nextIvl
    assert ni(c, 1) == 60
    assert ni(c, 2) == 600
    assert ni(c, 3) == 0
    assert d.sched.nextIvlStr(c, 3) == ""
    d.sched.answerCard(c, 3)
    assert c.queue == c.type == 0
    # undue reviews should also be unaffected
    c.ivl = 100
    c.type = c.queue = 2
    c.due = d.sched.today + 25
    c.factor = 2500
    c.flush()
    cardcopy = copy.copy(c)
    d.sched.rebuildDyn(did)
    d.reset()
    c = d.sched.getCard()
    assert ni(c, 1) == 600
    assert ni(c, 2) == 0
    assert ni(c, 3) == 0
    d.sched.answerCard(c, 2)
    assert c.ivl == 100
    assert c.due == d.sched.today + 25
    # check failure too
    c = cardcopy
    c.flush()
    d.sched.rebuildDyn(did)
    d.reset()
    c = d.sched.getCard()
    d.sched.answerCard(c, 1)
    d.sched.emptyDyn(did)
    c.load()
    assert c.ivl == 100
    assert c.due == d.sched.today + 25
    # fail+grad early
    c = cardcopy
    c.flush()
    d.sched.rebuildDyn(did)
    d.reset()
    c = d.sched.getCard()
    d.sched.answerCard(c, 1)
    d.sched.answerCard(c, 3)
    d.sched.emptyDyn(did)
    c.load()
    assert c.ivl == 100
    assert c.due == d.sched.today + 25
    # due cards - pass
    c = cardcopy
    c.due = -25
    c.flush()
    d.sched.rebuildDyn(did)
    d.reset()
    c = d.sched.getCard()
    d.sched.answerCard(c, 3)
    d.sched.emptyDyn(did)
    c.load()
    assert c.ivl == 100
    assert c.due == -25
    # fail
    c = cardcopy
    c.due = -25
    c.flush()
    d.sched.rebuildDyn(did)
    d.reset()
    c = d.sched.getCard()
    d.sched.answerCard(c, 1)
    d.sched.emptyDyn(did)
    c.load()
    assert c.ivl == 100
    assert c.due == -25
    # fail with normal grad
    c = cardcopy
    c.due = -25
    c.flush()
    d.sched.rebuildDyn(did)
    d.reset()
    c = d.sched.getCard()
    d.sched.answerCard(c, 1)
    d.sched.answerCard(c, 3)
    c.load()
    assert c.ivl == 100
    assert c.due == -25
    # lapsed card pulled into cram
    # d.sched._cardConf(c)['lapse']['mult']=0.5
    # d.sched.answerCard(c, 1)
    # d.sched.rebuildDyn(did)
    # d.reset()
    # c = d.sched.getCard()
    # d.sched.answerCard(c, 2)
    # print c.__dict__

def test_adjIvl():
    d = getEmptyDeck()
    # add two more templates and set second active
    m = d.models.current(); mm = d.models
    t = mm.newTemplate("Reverse")
    t['qfmt'] = "{{Back}}"
    t['afmt'] = "{{Front}}"
    mm.addTemplate(m, t)
    mm.save(m)
    t = d.models.newTemplate(m)
    t['name'] = "f2"
    t['qfmt'] = "{{Front}}"
    t['afmt'] = "{{Back}}"
    d.models.addTemplate(m, t)
    t = d.models.newTemplate(m)
    t['name'] = "f3"
    t['qfmt'] = "{{Front}}"
    t['afmt'] = "{{Back}}"
    d.models.addTemplate(m, t)
    d.models.save(m)
    # create a new note; it should have 4 cards
    f = d.newNote()
    f['Front'] = "1"; f['Back'] = "1"
    d.addNote(f)
    assert d.cardCount() == 4
    d.reset()
    # immediately remove first; it should get ideal ivl
    c = d.sched.getCard()
    d.sched.answerCard(c, 3)
    assert c.ivl == 4
    # with the default settings, second card should be -1
    c = d.sched.getCard()
    d.sched.answerCard(c, 3)
    assert c.ivl == 3
    # and third +1
    c = d.sched.getCard()
    d.sched.answerCard(c, 3)
    assert c.ivl == 5
    # fourth exceeds default settings, so gets ideal again
    c = d.sched.getCard()
    d.sched.answerCard(c, 3)
    assert c.ivl == 4
    # try again with another note
    f = d.newNote()
    f['Front'] = "2"; f['Back'] = "2"
    d.addNote(f)
    d.reset()
    # set a minSpacing of 0
    conf = d.sched._cardConf(c)
    conf['rev']['minSpace'] = 0
    # first card gets ideal
    c = d.sched.getCard()
    d.sched.answerCard(c, 3)
    assert c.ivl == 4
    # and second too, because it's below the threshold
    c = d.sched.getCard()
    d.sched.answerCard(c, 3)
    assert c.ivl == 4
    # if we increase the ivl minSpace isn't needed
    conf['new']['ints'][1] = 20
    # ideal..
    c = d.sched.getCard()
    d.sched.answerCard(c, 3)
    assert c.ivl == 20
    # adjusted
    c = d.sched.getCard()
    d.sched.answerCard(c, 3)
    assert c.ivl == 19

def test_ordcycle():
    d = getEmptyDeck()
    # add two more templates and set second active
    m = d.models.current(); mm = d.models
    t = mm.newTemplate("Reverse")
    t['qfmt'] = "{{Back}}"
    t['afmt'] = "{{Front}}"
    mm.addTemplate(m, t)
    t = mm.newTemplate("f2")
    t['qfmt'] = "{{Front}}"
    t['afmt'] = "{{Back}}"
    mm.addTemplate(m, t)
    mm.save(m)
    # create a new note; it should have 3 cards
    f = d.newNote()
    f['Front'] = "1"; f['Back'] = "1"
    d.addNote(f)
    assert d.cardCount() == 3
    d.reset()
    # ordinals should arrive in order
    assert d.sched.getCard().ord == 0
    assert d.sched.getCard().ord == 1
    assert d.sched.getCard().ord == 2

def test_counts_idx():
    d = getEmptyDeck()
    f = d.newNote()
    f['Front'] = u"one"; f['Back'] = u"two"
    d.addNote(f)
    d.reset()
    assert d.sched.counts() == (1, 0, 0)
    c = d.sched.getCard()
    # counter's been decremented but idx indicates 1
    assert d.sched.counts() == (0, 0, 0)
    assert d.sched.countIdx(c) == 0
    # answer to move to learn queue
    d.sched.answerCard(c, 1)
    assert d.sched.counts() == (0, 2, 0)
    # fetching again will decrement the count
    c = d.sched.getCard()
    assert d.sched.counts() == (0, 0, 0)
    assert d.sched.countIdx(c) == 1
    # answering should add it back again
    d.sched.answerCard(c, 1)
    assert d.sched.counts() == (0, 2, 0)

def test_repCounts():
    d = getEmptyDeck()
    f = d.newNote()
    f['Front'] = u"one"
    d.addNote(f)
    d.reset()
    # lrnReps should be accurate on pass/fail
    assert d.sched.counts() == (1, 0, 0)
    d.sched.answerCard(d.sched.getCard(), 1)
    assert d.sched.counts() == (0, 2, 0)
    d.sched.answerCard(d.sched.getCard(), 1)
    assert d.sched.counts() == (0, 2, 0)
    d.sched.answerCard(d.sched.getCard(), 2)
    assert d.sched.counts() == (0, 1, 0)
    d.sched.answerCard(d.sched.getCard(), 1)
    assert d.sched.counts() == (0, 2, 0)
    d.sched.answerCard(d.sched.getCard(), 2)
    assert d.sched.counts() == (0, 1, 0)
    d.sched.answerCard(d.sched.getCard(), 2)
    assert d.sched.counts() == (0, 0, 0)
    f = d.newNote()
    f['Front'] = u"two"
    d.addNote(f)
    d.reset()
    # initial pass should be correct too
    d.sched.answerCard(d.sched.getCard(), 2)
    assert d.sched.counts() == (0, 1, 0)
    d.sched.answerCard(d.sched.getCard(), 1)
    assert d.sched.counts() == (0, 2, 0)
    d.sched.answerCard(d.sched.getCard(), 3)
    assert d.sched.counts() == (0, 0, 0)
    # immediate graduate should work
    f = d.newNote()
    f['Front'] = u"three"
    d.addNote(f)
    d.reset()
    d.sched.answerCard(d.sched.getCard(), 3)
    assert d.sched.counts() == (0, 0, 0)
    # and failing a review should too
    f = d.newNote()
    f['Front'] = u"three"
    d.addNote(f)
    c = f.cards()[0]
    c.type = 2
    c.queue = 2
    c.due = d.sched.today
    c.flush()
    d.reset()
    assert d.sched.counts() == (0, 0, 1)
    d.sched.answerCard(d.sched.getCard(), 1)
    assert d.sched.counts() == (0, 1, 0)

def test_timing():
    d = getEmptyDeck()
    # add a few review cards, due today
    for i in range(5):
        f = d.newNote()
        f['Front'] = "num"+str(i)
        d.addNote(f)
        c = f.cards()[0]
        c.type = 2
        c.queue = 2
        c.due = 0
        c.flush()
    # fail the first one
    d.reset()
    c = d.sched.getCard()
    # set a a fail delay of 1 second so we don't have to wait
    d.sched._cardConf(c)['lapse']['delays'][0] = 1/60.0
    d.sched.answerCard(c, 1)
    # the next card should be another review
    c = d.sched.getCard()
    assert c.queue == 2
    # but if we wait for a second, the failed card should come back
    time.sleep(1)
    c = d.sched.getCard()
    assert c.queue == 1

def test_collapse():
    d = getEmptyDeck()
    # add a note
    f = d.newNote()
    f['Front'] = u"one"
    d.addNote(f)
    d.reset()
    # test collapsing
    c = d.sched.getCard()
    d.sched.answerCard(c, 1)
    c = d.sched.getCard()
    d.sched.answerCard(c, 3)
    assert not d.sched.getCard()

def test_deckDue():
    d = getEmptyDeck()
    # add a note with default deck
    f = d.newNote()
    f['Front'] = u"one"
    d.addNote(f)
    # and one that's a child
    f = d.newNote()
    f['Front'] = u"two"
    default1 = f.model()['did'] = d.decks.id("Default::1")
    d.addNote(f)
    # make it a review card
    c = f.cards()[0]
    c.queue = 2
    c.due = 0
    c.flush()
    # add one more with a new deck
    f = d.newNote()
    f['Front'] = u"two"
    foobar = f.model()['did'] = d.decks.id("foo::bar")
    d.addNote(f)
    # and one that's a sibling
    f = d.newNote()
    f['Front'] = u"three"
    foobaz = f.model()['did'] = d.decks.id("foo::baz")
    d.addNote(f)
    d.reset()
    assert len(d.decks.decks) == 5
    cnts = d.sched.deckDueList()
    assert cnts[0] == ["Default", 1, 0, 0, 1]
    assert cnts[1] == ["Default::1", default1, 1, 0, 0]
    assert cnts[2] == ["foo", d.decks.id("foo"), 0, 0, 0]
    assert cnts[3] == ["foo::bar", foobar, 0, 0, 1]
    assert cnts[4] == ["foo::baz", foobaz, 0, 0, 1]
    tree = d.sched.deckDueTree()
    assert tree[0][0] == "Default"
    # sum of child and parent
    assert tree[0][1] == 1
    assert tree[0][2] == 1
    assert tree[0][4] == 1
    # child count is just review
    assert tree[0][5][0][0] == "1"
    assert tree[0][5][0][1] == default1
    assert tree[0][5][0][2] == 1
    assert tree[0][5][0][4] == 0
    # code should not fail if a card has an invalid deck
    c.did = 12345; c.flush()
    d.sched.deckDueList()
    d.sched.deckDueTree()

def test_deckTree():
    d = getEmptyDeck()
    d.decks.id("new::b::c")
    d.decks.id("new2")
    # new should not appear twice in tree
    names = [x[0] for x in d.sched.deckDueTree()]
    names.remove("new")
    assert "new" not in names

def test_deckFlow():
    d = getEmptyDeck()
    # add a note with default deck
    f = d.newNote()
    f['Front'] = u"one"
    d.addNote(f)
    # and one that's a child
    f = d.newNote()
    f['Front'] = u"two"
    default1 = f.model()['did'] = d.decks.id("Default::2")
    d.addNote(f)
    # and another that's higher up
    f = d.newNote()
    f['Front'] = u"three"
    default1 = f.model()['did'] = d.decks.id("Default::1")
    d.addNote(f)
    # should get top level one first, then ::1, then ::2
    d.reset()
    assert d.sched.counts() == (3,0,0)
    for i in "one", "three", "two":
        c = d.sched.getCard()
        assert c.note()['Front'] == i
        d.sched.answerCard(c, 2)

def test_reorder():
    d = getEmptyDeck()
    # add a note with default deck
    f = d.newNote()
    f['Front'] = u"one"
    d.addNote(f)
    f2 = d.newNote()
    f2['Front'] = u"two"
    d.addNote(f2)
    assert f2.cards()[0].due == 2
    found=False
    # 50/50 chance of being reordered
    for i in range(20):
        d.sched.randomizeCards(1)
        if f.cards()[0].due != f.id:
            found=True
            break
    assert found
    d.sched.orderCards(1)
    assert f.cards()[0].due == 1
    # shifting
    f3 = d.newNote()
    f3['Front'] = u"three"
    d.addNote(f3)
    f4 = d.newNote()
    f4['Front'] = u"four"
    d.addNote(f4)
    assert f.cards()[0].due == 1
    assert f2.cards()[0].due == 2
    assert f3.cards()[0].due == 3
    assert f4.cards()[0].due == 4
    d.sched.sortCards([
        f3.cards()[0].id, f4.cards()[0].id], start=1, shift=True)
    assert f.cards()[0].due == 3
    assert f2.cards()[0].due == 4
    assert f3.cards()[0].due == 1
    assert f4.cards()[0].due == 2

def test_forget():
    d = getEmptyDeck()
    f = d.newNote()
    f['Front'] = u"one"
    d.addNote(f)
    c = f.cards()[0]
    c.queue = 2; c.type = 2; c.ivl = 100; c.due = 0
    c.flush()
    d.reset()
    assert d.sched.counts() == (0, 0, 1)
    d.sched.forgetCards([c.id])
    d.reset()
    assert d.sched.counts() == (1, 0, 0)

def test_resched():
    d = getEmptyDeck()
    f = d.newNote()
    f['Front'] = u"one"
    d.addNote(f)
    c = f.cards()[0]
    d.sched.reschedCards([c.id], 0, 0)
    c.load()
    assert c.due == d.sched.today
    assert c.ivl == 1
    assert c.queue == c.type == 2
    d.sched.reschedCards([c.id], 1, 1)
    c.load()
    assert c.due == d.sched.today+1
    assert c.ivl == +1

def test_norelearn():
    d = getEmptyDeck()
    # add a note
    f = d.newNote()
    f['Front'] = u"one"
    d.addNote(f)
    c = f.cards()[0]
    c.type = 2
    c.queue = 2
    c.due = 0
    c.factor = 2500
    c.reps = 3
    c.lapses = 1
    c.ivl = 100
    c.startTimer()
    c.flush()
    d.reset()
    d.sched.answerCard(c, 1)
    d.sched._cardConf(c)['lapse']['delays'] = []
    d.sched.answerCard(c, 1)

########NEW FILE########
__FILENAME__ = test_stats
# coding: utf-8

import time, copy, os
from tests.shared import assertException, getEmptyDeck
from anki.utils import stripHTML, intTime
from anki.hooks import addHook

def test_stats():
    d = getEmptyDeck()
    f = d.newNote()
    f['Front'] = "foo"
    d.addNote(f)
    c = f.cards()[0]
    # card stats
    assert d.cardStats(c)
    d.reset()
    c = d.sched.getCard()
    d.sched.answerCard(c, 3)
    d.sched.answerCard(c, 2)
    assert d.cardStats(c)

def test_graphs_empty():
    d = getEmptyDeck()
    assert d.stats().report()

def test_graphs():
    from anki import Collection as aopen
    d = aopen(os.path.expanduser("~/test.anki2"))
    g = d.stats()
    rep = g.report()
    open(os.path.expanduser("~/test.html"), "w").write(rep)
    return

########NEW FILE########
__FILENAME__ = test_sync
# coding: utf-8

import nose, os, tempfile, shutil, time
from tests.shared import assertException

from anki.errors import *
from anki import Collection as aopen
from anki.utils import intTime
from anki.sync import Syncer, FullSyncer, LocalServer, RemoteServer, \
    MediaSyncer, RemoteMediaServer
from anki.notes import Note
from anki.cards import Card
from tests.shared import getEmptyDeck

# Local tests
##########################################################################

deck1=None
deck2=None
client=None
server=None
server2=None

def setup_basic():
    global deck1, deck2, client, server
    deck1 = getEmptyDeck()
    # add a note to deck 1
    f = deck1.newNote()
    f['Front'] = u"foo"; f['Back'] = u"bar"; f.tags = [u"foo"]
    deck1.addNote(f)
    # answer it
    deck1.reset(); deck1.sched.answerCard(deck1.sched.getCard(), 4)
    # repeat for deck2
    deck2 = getEmptyDeck(server=True)
    f = deck2.newNote()
    f['Front'] = u"bar"; f['Back'] = u"bar"; f.tags = [u"bar"]
    deck2.addNote(f)
    deck2.reset(); deck2.sched.answerCard(deck2.sched.getCard(), 4)
    # start with same schema and sync time
    deck1.scm = deck2.scm = 0
    # and same mod time, so sync does nothing
    t = intTime(1000)
    deck1.save(mod=t); deck2.save(mod=t)
    server = LocalServer(deck2)
    client = Syncer(deck1, server)

def setup_modified():
    setup_basic()
    # mark deck1 as changed
    time.sleep(0.1)
    deck1.setMod()
    deck1.save()

@nose.with_setup(setup_basic)
def test_nochange():
    assert client.sync() == "noChanges"

@nose.with_setup(setup_modified)
def test_changedSchema():
    deck1.scm += 1
    deck1.setMod()
    assert client.sync() == "fullSync"

@nose.with_setup(setup_modified)
def test_sync():
    def check(num):
        for d in deck1, deck2:
            for t in ("revlog", "notes", "cards"):
                assert d.db.scalar("select count() from %s" % t) == num
            assert len(d.models.all()) == num*4
            # the default deck and config have an id of 1, so always 1
            assert len(d.decks.all()) == 1
            assert len(d.decks.dconf) == 1
            assert len(d.tags.all()) == num
    check(1)
    origUsn = deck1.usn()
    assert client.sync() == "success"
    # last sync times and mod times should agree
    assert deck1.mod == deck2.mod
    assert deck1._usn == deck2._usn
    assert deck1.mod == deck1.ls
    assert deck1._usn != origUsn
    # because everything was created separately it will be merged in. in
    # actual use, we use a full sync to ensure a common starting point.
    check(2)
    # repeating it does nothing
    assert client.sync() == "noChanges"
    # if we bump mod time, the decks will sync but should remain the same.
    deck1.setMod()
    deck1.save()
    assert client.sync() == "success"
    check(2)
    # crt should be synced
    deck1.crt = 123
    deck1.setMod()
    assert client.sync() == "success"
    assert deck1.crt == deck2.crt

@nose.with_setup(setup_modified)
def test_models():
    test_sync()
    # update model one
    cm = deck1.models.current()
    cm['name'] = "new"
    time.sleep(1)
    deck1.models.save(cm)
    deck1.save()
    assert deck2.models.get(cm['id'])['name'] == "Basic"
    assert client.sync() == "success"
    assert deck2.models.get(cm['id'])['name'] == "new"
    # deleting triggers a full sync
    deck1.scm = deck2.scm = 0
    deck1.models.rem(cm)
    deck1.save()
    assert client.sync() == "fullSync"

@nose.with_setup(setup_modified)
def test_notes():
    test_sync()
    # modifications should be synced
    nid = deck1.db.scalar("select id from notes")
    note = deck1.getNote(nid)
    assert note['Front'] != "abc"
    note['Front'] = "abc"
    note.flush()
    deck1.save()
    assert client.sync() == "success"
    assert deck2.getNote(nid)['Front'] == "abc"
    # deletions too
    assert deck1.db.scalar("select 1 from notes where id = ?", nid)
    deck1.remNotes([nid])
    deck1.save()
    assert client.sync() == "success"
    assert not deck1.db.scalar("select 1 from notes where id = ?", nid)
    assert not deck2.db.scalar("select 1 from notes where id = ?", nid)

@nose.with_setup(setup_modified)
def test_cards():
    test_sync()
    nid = deck1.db.scalar("select id from notes")
    note = deck1.getNote(nid)
    card = note.cards()[0]
    # answer the card locally
    card.startTimer()
    deck1.sched.answerCard(card, 4)
    assert card.reps == 2
    deck1.save()
    assert deck2.getCard(card.id).reps == 1
    assert client.sync() == "success"
    assert deck2.getCard(card.id).reps == 2
    # if it's modified on both sides , later mod time should win
    for test in ((deck1, deck2), (deck2, deck1)):
        time.sleep(1)
        c = test[0].getCard(card.id)
        c.reps = 5; c.flush()
        test[0].save()
        time.sleep(1)
        c = test[1].getCard(card.id)
        c.reps = 3; c.flush()
        test[1].save()
        assert client.sync() == "success"
        assert test[1].getCard(card.id).reps == 3
        assert test[0].getCard(card.id).reps == 3
    # removals should work too
    deck1.remCards([card.id])
    deck1.save()
    assert deck2.db.scalar("select 1 from cards where id = ?", card.id)
    assert client.sync() == "success"
    assert not deck2.db.scalar("select 1 from cards where id = ?", card.id)

@nose.with_setup(setup_modified)
def test_tags():
    test_sync()
    assert deck1.tags.all() == deck2.tags.all()
    deck1.tags.register(["abc"])
    deck2.tags.register(["xyz"])
    assert deck1.tags.all() != deck2.tags.all()
    deck1.save()
    time.sleep(0.1)
    deck2.save()
    assert client.sync() == "success"
    assert deck1.tags.all() == deck2.tags.all()

@nose.with_setup(setup_modified)
def test_decks():
    test_sync()
    assert len(deck1.decks.all()) == 1
    assert len(deck1.decks.all()) == len(deck2.decks.all())
    deck1.decks.id("new")
    assert len(deck1.decks.all()) != len(deck2.decks.all())
    time.sleep(0.1)
    deck2.decks.id("new2")
    deck1.save()
    time.sleep(0.1)
    deck2.save()
    assert client.sync() == "success"
    assert deck1.tags.all() == deck2.tags.all()
    assert len(deck1.decks.all()) == len(deck2.decks.all())
    assert len(deck1.decks.all()) == 3
    assert deck1.decks.confForDid(1)['maxTaken'] == 60
    deck2.decks.confForDid(1)['maxTaken'] = 30
    deck2.decks.save(deck2.decks.confForDid(1))
    deck2.save()
    assert client.sync() == "success"
    assert deck1.decks.confForDid(1)['maxTaken'] == 30

@nose.with_setup(setup_modified)
def test_conf():
    test_sync()
    assert deck2.conf['curDeck'] == 1
    deck1.conf['curDeck'] = 2
    time.sleep(0.1)
    deck1.setMod()
    deck1.save()
    assert client.sync() == "success"
    assert deck2.conf['curDeck'] == 2

@nose.with_setup(setup_modified)
def test_threeway():
    test_sync()
    deck1.close(save=False)
    d3path = deck1.path.replace(".anki", "2.anki")
    shutil.copy2(deck1.path, d3path)
    deck1.reopen()
    deck3 = aopen(d3path)
    client2 = Syncer(deck3, server)
    assert client2.sync() == "noChanges"
    # client 1 adds a card at time 1
    time.sleep(1)
    f = deck1.newNote()
    f['Front'] = u"1";
    deck1.addNote(f)
    deck1.save()
    # at time 2, client 2 syncs to server
    time.sleep(1)
    deck3.setMod()
    deck3.save()
    assert client2.sync() == "success"
    # at time 3, client 1 syncs, adding the older note
    time.sleep(1)
    assert client.sync() == "success"
    assert deck1.noteCount() == deck2.noteCount()
    # syncing client2 should pick it up
    assert client2.sync() == "success"
    assert deck1.noteCount() == deck2.noteCount() == deck3.noteCount()

def _test_speed():
    t = time.time()
    deck1 = aopen(os.path.expanduser("~/rapid.anki"))
    for tbl in "revlog", "cards", "notes", "graves":
        deck1.db.execute("update %s set usn = -1 where usn != -1"%tbl)
    for m in deck1.models.all():
        m['usn'] = -1
    for tx in deck1.tags.all():
        deck1.tags.tags[tx] = -1
    deck1._usn = -1
    deck1.save()
    deck2 = getEmptyDeck(server=True)
    deck1.scm = deck2.scm = 0
    server = LocalServer(deck2)
    client = Syncer(deck1, server)
    print "load %d" % ((time.time() - t)*1000); t = time.time()
    assert client.sync() == "success"
    print "sync %d" % ((time.time() - t)*1000); t = time.time()

########NEW FILE########
__FILENAME__ = test_undo
# coding: utf-8

import time
from tests.shared import assertException, getEmptyDeck
from anki.consts import *

def test_op():
    d = getEmptyDeck()
    # should have no undo by default
    assert not d.undoName()
    # let's adjust a study option
    d.save("studyopts")
    d.conf['abc'] = 5
    # it should be listed as undoable
    assert d.undoName() == "studyopts"
    # with about 5 minutes until it's clobbered
    assert time.time() - d._lastSave < 1
    # undoing should restore the old value
    d.undo()
    assert not d.undoName()
    assert 'abc' not in d.conf
    # an (auto)save will clear the undo
    d.save("foo")
    assert d.undoName() == "foo"
    d.save()
    assert not d.undoName()
    # and a review will, too
    d.save("add")
    f = d.newNote()
    f['Front'] = u"one"
    d.addNote(f)
    d.reset()
    assert d.undoName() == "add"
    c = d.sched.getCard()
    d.sched.answerCard(c, 2)
    assert d.undoName() == "Review"

def test_review():
    d = getEmptyDeck()
    d.conf['counts'] = COUNT_REMAINING
    f = d.newNote()
    f['Front'] = u"one"
    d.addNote(f)
    d.reset()
    assert not d.undoName()
    # answer
    assert d.sched.counts() == (1, 0, 0)
    c = d.sched.getCard()
    assert c.queue == 0
    d.sched.answerCard(c, 2)
    assert c.left == 1001
    assert d.sched.counts() == (0, 1, 0)
    assert c.queue == 1
    # undo
    assert d.undoName()
    d.undo()
    d.reset()
    assert d.sched.counts() == (1, 0, 0)
    c.load()
    assert c.queue == 0
    assert c.left != 1001
    assert not d.undoName()
    # we should be able to undo multiple answers too
    f['Front'] = u"two"
    d.addNote(f)
    d.reset()
    assert d.sched.counts() == (2, 0, 0)
    c = d.sched.getCard()
    d.sched.answerCard(c, 2)
    c = d.sched.getCard()
    d.sched.answerCard(c, 2)
    assert d.sched.counts() == (0, 2, 0)
    d.undo()
    d.reset()
    assert d.sched.counts() == (1, 1, 0)
    d.undo()
    d.reset()
    assert d.sched.counts() == (2, 0, 0)
    # performing a normal op will clear the review queue
    c = d.sched.getCard()
    d.sched.answerCard(c, 2)
    assert d.undoName() == "Review"
    d.save("foo")
    assert d.undoName() == "foo"
    d.undo()
    assert not d.undoName()



########NEW FILE########
__FILENAME__ = test_upgrade
# coding: utf-8

import datetime, shutil
from anki import Collection
from anki.consts import *
from shared import getUpgradeDeckPath, getEmptyDeck, testDir
from anki.upgrade import Upgrader
from anki.importing import Anki2Importer
from anki.utils import ids2str, checksum

def test_check():
    dst = getUpgradeDeckPath()
    u = Upgrader()
    assert u.check(dst)
    # if it's corrupted, will fail
    open(dst, "w+").write("foo")
    assert not u.check(dst)

def test_upgrade1():
    dst = getUpgradeDeckPath()
    csum = checksum(open(dst).read())
    u = Upgrader()
    deck = u.upgrade(dst)
    # src file must not have changed
    assert csum == checksum(open(dst).read())
    # creation time should have been adjusted
    d = datetime.datetime.fromtimestamp(deck.crt)
    assert d.hour == 4 and d.minute == 0
    # 3 new, 2 failed, 1 due
    deck.reset()
    deck.conf['counts'] = COUNT_REMAINING
    assert deck.sched.counts() == (3,2,1)
    # modifying each note should not cause new cards to be generated
    assert deck.cardCount() == 6
    for nid in deck.db.list("select id from notes"):
        note = deck.getNote(nid)
        note.flush()
    assert deck.cardCount() == 6
    # now's a good time to test the integrity check too
    deck.fixIntegrity()
    # c = deck.sched.getCard()
    # print "--q", c.q()
    # print
    # print "--a", c.a()

def test_upgrade1_due():
    dst = getUpgradeDeckPath("anki12-due.anki")
    u = Upgrader()
    deck = u.upgrade(dst)
    assert not deck.db.scalar("select 1 from cards where due != 1")

def test_invalid_ords():
    dst = getUpgradeDeckPath("invalid-ords.anki")
    u = Upgrader()
    u.check(dst)
    deck = u.upgrade(dst)
    assert deck.db.scalar("select count() from cards where ord = 0") == 1
    assert deck.db.scalar("select count() from cards where ord = 1") == 1

def test_upgrade2():
    p = "/tmp/alpha-upgrade.anki2"
    if os.path.exists(p):
        os.unlink(p)
    shutil.copy2(os.path.join(testDir, "support/anki2-alpha.anki2"), p)
    col = Collection(p)
    assert col.db.scalar("select ver from col") == SCHEMA_VERSION

########NEW FILE########
__FILENAME__ = BeautifulSoup
"""Beautiful Soup
Elixir and Tonic
"The Screen-Scraper's Friend"
http://www.crummy.com/software/BeautifulSoup/

Beautiful Soup parses a (possibly invalid) XML or HTML document into a
tree representation. It provides methods and Pythonic idioms that make
it easy to navigate, search, and modify the tree.

A well-formed XML/HTML document yields a well-formed data
structure. An ill-formed XML/HTML document yields a correspondingly
ill-formed data structure. If your document is only locally
well-formed, you can use this library to find and process the
well-formed part of it.

Beautiful Soup works with Python 2.2 and up. It has no external
dependencies, but you'll have more success at converting data to UTF-8
if you also install these three packages:

* chardet, for auto-detecting character encodings
  http://chardet.feedparser.org/
* cjkcodecs and iconv_codec, which add more encodings to the ones supported
  by stock Python.
  http://cjkpython.i18n.org/

Beautiful Soup defines classes for two main parsing strategies:

 * BeautifulStoneSoup, for parsing XML, SGML, or your domain-specific
   language that kind of looks like XML.

 * BeautifulSoup, for parsing run-of-the-mill HTML code, be it valid
   or invalid. This class has web browser-like heuristics for
   obtaining a sensible parse tree in the face of common HTML errors.

Beautiful Soup also defines a class (UnicodeDammit) for autodetecting
the encoding of an HTML or XML document, and converting it to
Unicode. Much of this code is taken from Mark Pilgrim's Universal Feed Parser.

For more than you ever wanted to know about Beautiful Soup, see the
documentation:
http://www.crummy.com/software/BeautifulSoup/documentation.html

Here, have some legalese:

Copyright (c) 2004-2010, Leonard Richardson

All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are
met:

  * Redistributions of source code must retain the above copyright
    notice, this list of conditions and the following disclaimer.

  * Redistributions in binary form must reproduce the above
    copyright notice, this list of conditions and the following
    disclaimer in the documentation and/or other materials provided
    with the distribution.

  * Neither the name of the the Beautiful Soup Consortium and All
    Night Kosher Bakery nor the names of its contributors may be
    used to endorse or promote products derived from this software
    without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
"AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR
CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL,
EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO,
PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR
PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF
LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING
NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE, DAMMIT.

"""
from __future__ import generators

__author__ = "Leonard Richardson (leonardr@segfault.org)"
__version__ = "3.2.1"
__copyright__ = "Copyright (c) 2004-2012 Leonard Richardson"
__license__ = "New-style BSD"

from sgmllib import SGMLParser, SGMLParseError
import codecs
import markupbase
import types
import re
import sgmllib
try:
  from htmlentitydefs import name2codepoint
except ImportError:
  name2codepoint = {}
try:
    set
except NameError:
    from sets import Set as set

#These hacks make Beautiful Soup able to parse XML with namespaces
sgmllib.tagfind = re.compile('[a-zA-Z][-_.:a-zA-Z0-9]*')
markupbase._declname_match = re.compile(r'[a-zA-Z][-_.:a-zA-Z0-9]*\s*').match

DEFAULT_OUTPUT_ENCODING = "utf-8"

def _match_css_class(str):
    """Build a RE to match the given CSS class."""
    return re.compile(r"(^|.*\s)%s($|\s)" % str)

# First, the classes that represent markup elements.

class PageElement(object):
    """Contains the navigational information for some part of the page
    (either a tag or a piece of text)"""

    def _invert(h):
        "Cheap function to invert a hash."
        i = {}
        for k,v in h.items():
            i[v] = k
        return i

    XML_ENTITIES_TO_SPECIAL_CHARS = { "apos" : "'",
                                      "quot" : '"',
                                      "amp" : "&",
                                      "lt" : "<",
                                      "gt" : ">" }

    XML_SPECIAL_CHARS_TO_ENTITIES = _invert(XML_ENTITIES_TO_SPECIAL_CHARS)

    def setup(self, parent=None, previous=None):
        """Sets up the initial relations between this element and
        other elements."""
        self.parent = parent
        self.previous = previous
        self.next = None
        self.previousSibling = None
        self.nextSibling = None
        if self.parent and self.parent.contents:
            self.previousSibling = self.parent.contents[-1]
            self.previousSibling.nextSibling = self

    def replaceWith(self, replaceWith):
        oldParent = self.parent
        myIndex = self.parent.index(self)
        if hasattr(replaceWith, "parent")\
                  and replaceWith.parent is self.parent:
            # We're replacing this element with one of its siblings.
            index = replaceWith.parent.index(replaceWith)
            if index and index < myIndex:
                # Furthermore, it comes before this element. That
                # means that when we extract it, the index of this
                # element will change.
                myIndex = myIndex - 1
        self.extract()
        oldParent.insert(myIndex, replaceWith)

    def replaceWithChildren(self):
        myParent = self.parent
        myIndex = self.parent.index(self)
        self.extract()
        reversedChildren = list(self.contents)
        reversedChildren.reverse()
        for child in reversedChildren:
            myParent.insert(myIndex, child)

    def extract(self):
        """Destructively rips this element out of the tree."""
        if self.parent:
            try:
                del self.parent.contents[self.parent.index(self)]
            except ValueError:
                pass

        #Find the two elements that would be next to each other if
        #this element (and any children) hadn't been parsed. Connect
        #the two.
        lastChild = self._lastRecursiveChild()
        nextElement = lastChild.next

        if self.previous:
            self.previous.next = nextElement
        if nextElement:
            nextElement.previous = self.previous
        self.previous = None
        lastChild.next = None

        self.parent = None
        if self.previousSibling:
            self.previousSibling.nextSibling = self.nextSibling
        if self.nextSibling:
            self.nextSibling.previousSibling = self.previousSibling
        self.previousSibling = self.nextSibling = None
        return self

    def _lastRecursiveChild(self):
        "Finds the last element beneath this object to be parsed."
        lastChild = self
        while hasattr(lastChild, 'contents') and lastChild.contents:
            lastChild = lastChild.contents[-1]
        return lastChild

    def insert(self, position, newChild):
        if isinstance(newChild, basestring) \
            and not isinstance(newChild, NavigableString):
            newChild = NavigableString(newChild)

        position =  min(position, len(self.contents))
        if hasattr(newChild, 'parent') and newChild.parent is not None:
            # We're 'inserting' an element that's already one
            # of this object's children.
            if newChild.parent is self:
                index = self.index(newChild)
                if index > position:
                    # Furthermore we're moving it further down the
                    # list of this object's children. That means that
                    # when we extract this element, our target index
                    # will jump down one.
                    position = position - 1
            newChild.extract()

        newChild.parent = self
        previousChild = None
        if position == 0:
            newChild.previousSibling = None
            newChild.previous = self
        else:
            previousChild = self.contents[position-1]
            newChild.previousSibling = previousChild
            newChild.previousSibling.nextSibling = newChild
            newChild.previous = previousChild._lastRecursiveChild()
        if newChild.previous:
            newChild.previous.next = newChild

        newChildsLastElement = newChild._lastRecursiveChild()

        if position >= len(self.contents):
            newChild.nextSibling = None

            parent = self
            parentsNextSibling = None
            while not parentsNextSibling:
                parentsNextSibling = parent.nextSibling
                parent = parent.parent
                if not parent: # This is the last element in the document.
                    break
            if parentsNextSibling:
                newChildsLastElement.next = parentsNextSibling
            else:
                newChildsLastElement.next = None
        else:
            nextChild = self.contents[position]
            newChild.nextSibling = nextChild
            if newChild.nextSibling:
                newChild.nextSibling.previousSibling = newChild
            newChildsLastElement.next = nextChild

        if newChildsLastElement.next:
            newChildsLastElement.next.previous = newChildsLastElement
        self.contents.insert(position, newChild)

    def append(self, tag):
        """Appends the given tag to the contents of this tag."""
        self.insert(len(self.contents), tag)

    def findNext(self, name=None, attrs={}, text=None, **kwargs):
        """Returns the first item that matches the given criteria and
        appears after this Tag in the document."""
        return self._findOne(self.findAllNext, name, attrs, text, **kwargs)

    def findAllNext(self, name=None, attrs={}, text=None, limit=None,
                    **kwargs):
        """Returns all items that match the given criteria and appear
        after this Tag in the document."""
        return self._findAll(name, attrs, text, limit, self.nextGenerator,
                             **kwargs)

    def findNextSibling(self, name=None, attrs={}, text=None, **kwargs):
        """Returns the closest sibling to this Tag that matches the
        given criteria and appears after this Tag in the document."""
        return self._findOne(self.findNextSiblings, name, attrs, text,
                             **kwargs)

    def findNextSiblings(self, name=None, attrs={}, text=None, limit=None,
                         **kwargs):
        """Returns the siblings of this Tag that match the given
        criteria and appear after this Tag in the document."""
        return self._findAll(name, attrs, text, limit,
                             self.nextSiblingGenerator, **kwargs)
    fetchNextSiblings = findNextSiblings # Compatibility with pre-3.x

    def findPrevious(self, name=None, attrs={}, text=None, **kwargs):
        """Returns the first item that matches the given criteria and
        appears before this Tag in the document."""
        return self._findOne(self.findAllPrevious, name, attrs, text, **kwargs)

    def findAllPrevious(self, name=None, attrs={}, text=None, limit=None,
                        **kwargs):
        """Returns all items that match the given criteria and appear
        before this Tag in the document."""
        return self._findAll(name, attrs, text, limit, self.previousGenerator,
                           **kwargs)
    fetchPrevious = findAllPrevious # Compatibility with pre-3.x

    def findPreviousSibling(self, name=None, attrs={}, text=None, **kwargs):
        """Returns the closest sibling to this Tag that matches the
        given criteria and appears before this Tag in the document."""
        return self._findOne(self.findPreviousSiblings, name, attrs, text,
                             **kwargs)

    def findPreviousSiblings(self, name=None, attrs={}, text=None,
                             limit=None, **kwargs):
        """Returns the siblings of this Tag that match the given
        criteria and appear before this Tag in the document."""
        return self._findAll(name, attrs, text, limit,
                             self.previousSiblingGenerator, **kwargs)
    fetchPreviousSiblings = findPreviousSiblings # Compatibility with pre-3.x

    def findParent(self, name=None, attrs={}, **kwargs):
        """Returns the closest parent of this Tag that matches the given
        criteria."""
        # NOTE: We can't use _findOne because findParents takes a different
        # set of arguments.
        r = None
        l = self.findParents(name, attrs, 1)
        if l:
            r = l[0]
        return r

    def findParents(self, name=None, attrs={}, limit=None, **kwargs):
        """Returns the parents of this Tag that match the given
        criteria."""

        return self._findAll(name, attrs, None, limit, self.parentGenerator,
                             **kwargs)
    fetchParents = findParents # Compatibility with pre-3.x

    #These methods do the real heavy lifting.

    def _findOne(self, method, name, attrs, text, **kwargs):
        r = None
        l = method(name, attrs, text, 1, **kwargs)
        if l:
            r = l[0]
        return r

    def _findAll(self, name, attrs, text, limit, generator, **kwargs):
        "Iterates over a generator looking for things that match."

        if isinstance(name, SoupStrainer):
            strainer = name
        # (Possibly) special case some findAll*(...) searches
        elif text is None and not limit and not attrs and not kwargs:
            # findAll*(True)
            if name is True:
                return [element for element in generator()
                        if isinstance(element, Tag)]
            # findAll*('tag-name')
            elif isinstance(name, basestring):
                return [element for element in generator()
                        if isinstance(element, Tag) and
                        element.name == name]
            else:
                strainer = SoupStrainer(name, attrs, text, **kwargs)
        # Build a SoupStrainer
        else:
            strainer = SoupStrainer(name, attrs, text, **kwargs)
        results = ResultSet(strainer)
        g = generator()
        while True:
            try:
                i = g.next()
            except StopIteration:
                break
            if i:
                found = strainer.search(i)
                if found:
                    results.append(found)
                    if limit and len(results) >= limit:
                        break
        return results

    #These Generators can be used to navigate starting from both
    #NavigableStrings and Tags.
    def nextGenerator(self):
        i = self
        while i is not None:
            i = i.next
            yield i

    def nextSiblingGenerator(self):
        i = self
        while i is not None:
            i = i.nextSibling
            yield i

    def previousGenerator(self):
        i = self
        while i is not None:
            i = i.previous
            yield i

    def previousSiblingGenerator(self):
        i = self
        while i is not None:
            i = i.previousSibling
            yield i

    def parentGenerator(self):
        i = self
        while i is not None:
            i = i.parent
            yield i

    # Utility methods
    def substituteEncoding(self, str, encoding=None):
        encoding = encoding or "utf-8"
        return str.replace("%SOUP-ENCODING%", encoding)

    def toEncoding(self, s, encoding=None):
        """Encodes an object to a string in some encoding, or to Unicode.
        ."""
        if isinstance(s, unicode):
            if encoding:
                s = s.encode(encoding)
        elif isinstance(s, str):
            if encoding:
                s = s.encode(encoding)
            else:
                s = unicode(s)
        else:
            if encoding:
                s  = self.toEncoding(str(s), encoding)
            else:
                s = unicode(s)
        return s

    BARE_AMPERSAND_OR_BRACKET = re.compile("([<>]|"
                                           + "&(?!#\d+;|#x[0-9a-fA-F]+;|\w+;)"
                                           + ")")

    def _sub_entity(self, x):
        """Used with a regular expression to substitute the
        appropriate XML entity for an XML special character."""
        return "&" + self.XML_SPECIAL_CHARS_TO_ENTITIES[x.group(0)[0]] + ";"


class NavigableString(unicode, PageElement):

    def __new__(cls, value):
        """Create a new NavigableString.

        When unpickling a NavigableString, this method is called with
        the string in DEFAULT_OUTPUT_ENCODING. That encoding needs to be
        passed in to the superclass's __new__ or the superclass won't know
        how to handle non-ASCII characters.
        """
        if isinstance(value, unicode):
            return unicode.__new__(cls, value)
        return unicode.__new__(cls, value, DEFAULT_OUTPUT_ENCODING)

    def __getnewargs__(self):
        return (NavigableString.__str__(self),)

    def __getattr__(self, attr):
        """text.string gives you text. This is for backwards
        compatibility for Navigable*String, but for CData* it lets you
        get the string without the CData wrapper."""
        if attr == 'string':
            return self
        else:
            raise AttributeError, "'%s' object has no attribute '%s'" % (self.__class__.__name__, attr)

    def __unicode__(self):
        return str(self).decode(DEFAULT_OUTPUT_ENCODING)

    def __str__(self, encoding=DEFAULT_OUTPUT_ENCODING):
        # Substitute outgoing XML entities.
        data = self.BARE_AMPERSAND_OR_BRACKET.sub(self._sub_entity, self)
        if encoding:
            return data.encode(encoding)
        else:
            return data

class CData(NavigableString):

    def __str__(self, encoding=DEFAULT_OUTPUT_ENCODING):
        return "<![CDATA[%s]]>" % NavigableString.__str__(self, encoding)

class ProcessingInstruction(NavigableString):
    def __str__(self, encoding=DEFAULT_OUTPUT_ENCODING):
        output = self
        if "%SOUP-ENCODING%" in output:
            output = self.substituteEncoding(output, encoding)
        return "<?%s?>" % self.toEncoding(output, encoding)

class Comment(NavigableString):
    def __str__(self, encoding=DEFAULT_OUTPUT_ENCODING):
        return "<!--%s-->" % NavigableString.__str__(self, encoding)

class Declaration(NavigableString):
    def __str__(self, encoding=DEFAULT_OUTPUT_ENCODING):
        return "<!%s>" % NavigableString.__str__(self, encoding)

class Tag(PageElement):

    """Represents a found HTML tag with its attributes and contents."""

    def _convertEntities(self, match):
        """Used in a call to re.sub to replace HTML, XML, and numeric
        entities with the appropriate Unicode characters. If HTML
        entities are being converted, any unrecognized entities are
        escaped."""
        x = match.group(1)
        if self.convertHTMLEntities and x in name2codepoint:
            return unichr(name2codepoint[x])
        elif x in self.XML_ENTITIES_TO_SPECIAL_CHARS:
            if self.convertXMLEntities:
                return self.XML_ENTITIES_TO_SPECIAL_CHARS[x]
            else:
                return u'&%s;' % x
        elif len(x) > 0 and x[0] == '#':
            # Handle numeric entities
            if len(x) > 1 and x[1] == 'x':
                return unichr(int(x[2:], 16))
            else:
                return unichr(int(x[1:]))

        elif self.escapeUnrecognizedEntities:
            return u'&amp;%s;' % x
        else:
            return u'&%s;' % x

    def __init__(self, parser, name, attrs=None, parent=None,
                 previous=None):
        "Basic constructor."

        # We don't actually store the parser object: that lets extracted
        # chunks be garbage-collected
        self.parserClass = parser.__class__
        self.isSelfClosing = parser.isSelfClosingTag(name)
        self.name = name
        if attrs is None:
            attrs = []
        elif isinstance(attrs, dict):
            attrs = attrs.items()
        self.attrs = attrs
        self.contents = []
        self.setup(parent, previous)
        self.hidden = False
        self.containsSubstitutions = False
        self.convertHTMLEntities = parser.convertHTMLEntities
        self.convertXMLEntities = parser.convertXMLEntities
        self.escapeUnrecognizedEntities = parser.escapeUnrecognizedEntities

        # Convert any HTML, XML, or numeric entities in the attribute values.
        convert = lambda(k, val): (k,
                                   re.sub("&(#\d+|#x[0-9a-fA-F]+|\w+);",
                                          self._convertEntities,
                                          val))
        self.attrs = map(convert, self.attrs)

    def getString(self):
        if (len(self.contents) == 1
            and isinstance(self.contents[0], NavigableString)):
            return self.contents[0]

    def setString(self, string):
        """Replace the contents of the tag with a string"""
        self.clear()
        self.append(string)

    string = property(getString, setString)

    def getText(self, separator=u""):
        if not len(self.contents):
            return u""
        stopNode = self._lastRecursiveChild().next
        strings = []
        current = self.contents[0]
        while current is not stopNode:
            if isinstance(current, NavigableString):
                strings.append(current.strip())
            current = current.next
        return separator.join(strings)

    text = property(getText)

    def get(self, key, default=None):
        """Returns the value of the 'key' attribute for the tag, or
        the value given for 'default' if it doesn't have that
        attribute."""
        return self._getAttrMap().get(key, default)

    def clear(self):
        """Extract all children."""
        for child in self.contents[:]:
            child.extract()

    def index(self, element):
        for i, child in enumerate(self.contents):
            if child is element:
                return i
        raise ValueError("Tag.index: element not in tag")

    def has_key(self, key):
        return self._getAttrMap().has_key(key)

    def __getitem__(self, key):
        """tag[key] returns the value of the 'key' attribute for the tag,
        and throws an exception if it's not there."""
        return self._getAttrMap()[key]

    def __iter__(self):
        "Iterating over a tag iterates over its contents."
        return iter(self.contents)

    def __len__(self):
        "The length of a tag is the length of its list of contents."
        return len(self.contents)

    def __contains__(self, x):
        return x in self.contents

    def __nonzero__(self):
        "A tag is non-None even if it has no contents."
        return True

    def __setitem__(self, key, value):
        """Setting tag[key] sets the value of the 'key' attribute for the
        tag."""
        self._getAttrMap()
        self.attrMap[key] = value
        found = False
        for i in range(0, len(self.attrs)):
            if self.attrs[i][0] == key:
                self.attrs[i] = (key, value)
                found = True
        if not found:
            self.attrs.append((key, value))
        self._getAttrMap()[key] = value

    def __delitem__(self, key):
        "Deleting tag[key] deletes all 'key' attributes for the tag."
        for item in self.attrs:
            if item[0] == key:
                self.attrs.remove(item)
                #We don't break because bad HTML can define the same
                #attribute multiple times.
            self._getAttrMap()
            if self.attrMap.has_key(key):
                del self.attrMap[key]

    def __call__(self, *args, **kwargs):
        """Calling a tag like a function is the same as calling its
        findAll() method. Eg. tag('a') returns a list of all the A tags
        found within this tag."""
        return apply(self.findAll, args, kwargs)

    def __getattr__(self, tag):
        #print "Getattr %s.%s" % (self.__class__, tag)
        if len(tag) > 3 and tag.rfind('Tag') == len(tag)-3:
            return self.find(tag[:-3])
        elif tag.find('__') != 0:
            return self.find(tag)
        raise AttributeError, "'%s' object has no attribute '%s'" % (self.__class__, tag)

    def __eq__(self, other):
        """Returns true iff this tag has the same name, the same attributes,
        and the same contents (recursively) as the given tag.

        NOTE: right now this will return false if two tags have the
        same attributes in a different order. Should this be fixed?"""
        if other is self:
            return True
        if not hasattr(other, 'name') or not hasattr(other, 'attrs') or not hasattr(other, 'contents') or self.name != other.name or self.attrs != other.attrs or len(self) != len(other):
            return False
        for i in range(0, len(self.contents)):
            if self.contents[i] != other.contents[i]:
                return False
        return True

    def __ne__(self, other):
        """Returns true iff this tag is not identical to the other tag,
        as defined in __eq__."""
        return not self == other

    def __repr__(self, encoding=DEFAULT_OUTPUT_ENCODING):
        """Renders this tag as a string."""
        return self.__str__(encoding)

    def __unicode__(self):
        return self.__str__(None)

    def __str__(self, encoding=DEFAULT_OUTPUT_ENCODING,
                prettyPrint=False, indentLevel=0):
        """Returns a string or Unicode representation of this tag and
        its contents. To get Unicode, pass None for encoding.

        NOTE: since Python's HTML parser consumes whitespace, this
        method is not certain to reproduce the whitespace present in
        the original string."""

        encodedName = self.toEncoding(self.name, encoding)

        attrs = []
        if self.attrs:
            for key, val in self.attrs:
                fmt = '%s="%s"'
                if isinstance(val, basestring):
                    if self.containsSubstitutions and '%SOUP-ENCODING%' in val:
                        val = self.substituteEncoding(val, encoding)

                    # The attribute value either:
                    #
                    # * Contains no embedded double quotes or single quotes.
                    #   No problem: we enclose it in double quotes.
                    # * Contains embedded single quotes. No problem:
                    #   double quotes work here too.
                    # * Contains embedded double quotes. No problem:
                    #   we enclose it in single quotes.
                    # * Embeds both single _and_ double quotes. This
                    #   can't happen naturally, but it can happen if
                    #   you modify an attribute value after parsing
                    #   the document. Now we have a bit of a
                    #   problem. We solve it by enclosing the
                    #   attribute in single quotes, and escaping any
                    #   embedded single quotes to XML entities.
                    if '"' in val:
                        fmt = "%s='%s'"
                        if "'" in val:
                            # TODO: replace with apos when
                            # appropriate.
                            val = val.replace("'", "&squot;")

                    # Now we're okay w/r/t quotes. But the attribute
                    # value might also contain angle brackets, or
                    # ampersands that aren't part of entities. We need
                    # to escape those to XML entities too.
                    val = self.BARE_AMPERSAND_OR_BRACKET.sub(self._sub_entity, val)

                attrs.append(fmt % (self.toEncoding(key, encoding),
                                    self.toEncoding(val, encoding)))
        close = ''
        closeTag = ''
        if self.isSelfClosing:
            close = ' /'
        else:
            closeTag = '</%s>' % encodedName

        indentTag, indentContents = 0, 0
        if prettyPrint:
            indentTag = indentLevel
            space = (' ' * (indentTag-1))
            indentContents = indentTag + 1
        contents = self.renderContents(encoding, prettyPrint, indentContents)
        if self.hidden:
            s = contents
        else:
            s = []
            attributeString = ''
            if attrs:
                attributeString = ' ' + ' '.join(attrs)
            if prettyPrint:
                s.append(space)
            s.append('<%s%s%s>' % (encodedName, attributeString, close))
            if prettyPrint:
                s.append("\n")
            s.append(contents)
            if prettyPrint and contents and contents[-1] != "\n":
                s.append("\n")
            if prettyPrint and closeTag:
                s.append(space)
            s.append(closeTag)
            if prettyPrint and closeTag and self.nextSibling:
                s.append("\n")
            s = ''.join(s)
        return s

    def decompose(self):
        """Recursively destroys the contents of this tree."""
        self.extract()
        if len(self.contents) == 0:
            return
        current = self.contents[0]
        while current is not None:
            next = current.next
            if isinstance(current, Tag):
                del current.contents[:]
            current.parent = None
            current.previous = None
            current.previousSibling = None
            current.next = None
            current.nextSibling = None
            current = next

    def prettify(self, encoding=DEFAULT_OUTPUT_ENCODING):
        return self.__str__(encoding, True)

    def renderContents(self, encoding=DEFAULT_OUTPUT_ENCODING,
                       prettyPrint=False, indentLevel=0):
        """Renders the contents of this tag as a string in the given
        encoding. If encoding is None, returns a Unicode string.."""
        s=[]
        for c in self:
            text = None
            if isinstance(c, NavigableString):
                text = c.__str__(encoding)
            elif isinstance(c, Tag):
                s.append(c.__str__(encoding, prettyPrint, indentLevel))
            if text and prettyPrint:
                text = text.strip()
            if text:
                if prettyPrint:
                    s.append(" " * (indentLevel-1))
                s.append(text)
                if prettyPrint:
                    s.append("\n")
        return ''.join(s)

    #Soup methods

    def find(self, name=None, attrs={}, recursive=True, text=None,
             **kwargs):
        """Return only the first child of this Tag matching the given
        criteria."""
        r = None
        l = self.findAll(name, attrs, recursive, text, 1, **kwargs)
        if l:
            r = l[0]
        return r
    findChild = find

    def findAll(self, name=None, attrs={}, recursive=True, text=None,
                limit=None, **kwargs):
        """Extracts a list of Tag objects that match the given
        criteria.  You can specify the name of the Tag and any
        attributes you want the Tag to have.

        The value of a key-value pair in the 'attrs' map can be a
        string, a list of strings, a regular expression object, or a
        callable that takes a string and returns whether or not the
        string matches for some custom definition of 'matches'. The
        same is true of the tag name."""
        generator = self.recursiveChildGenerator
        if not recursive:
            generator = self.childGenerator
        return self._findAll(name, attrs, text, limit, generator, **kwargs)
    findChildren = findAll

    # Pre-3.x compatibility methods
    first = find
    fetch = findAll

    def fetchText(self, text=None, recursive=True, limit=None):
        return self.findAll(text=text, recursive=recursive, limit=limit)

    def firstText(self, text=None, recursive=True):
        return self.find(text=text, recursive=recursive)

    #Private methods

    def _getAttrMap(self):
        """Initializes a map representation of this tag's attributes,
        if not already initialized."""
        if not getattr(self, 'attrMap'):
            self.attrMap = {}
            for (key, value) in self.attrs:
                self.attrMap[key] = value
        return self.attrMap

    #Generator methods
    def childGenerator(self):
        # Just use the iterator from the contents
        return iter(self.contents)

    def recursiveChildGenerator(self):
        if not len(self.contents):
            raise StopIteration
        stopNode = self._lastRecursiveChild().next
        current = self.contents[0]
        while current is not stopNode:
            yield current
            current = current.next


# Next, a couple classes to represent queries and their results.
class SoupStrainer:
    """Encapsulates a number of ways of matching a markup element (tag or
    text)."""

    def __init__(self, name=None, attrs={}, text=None, **kwargs):
        self.name = name
        if isinstance(attrs, basestring):
            kwargs['class'] = _match_css_class(attrs)
            attrs = None
        if kwargs:
            if attrs:
                attrs = attrs.copy()
                attrs.update(kwargs)
            else:
                attrs = kwargs
        self.attrs = attrs
        self.text = text

    def __str__(self):
        if self.text:
            return self.text
        else:
            return "%s|%s" % (self.name, self.attrs)

    def searchTag(self, markupName=None, markupAttrs={}):
        found = None
        markup = None
        if isinstance(markupName, Tag):
            markup = markupName
            markupAttrs = markup
        callFunctionWithTagData = callable(self.name) \
                                and not isinstance(markupName, Tag)

        if (not self.name) \
               or callFunctionWithTagData \
               or (markup and self._matches(markup, self.name)) \
               or (not markup and self._matches(markupName, self.name)):
            if callFunctionWithTagData:
                match = self.name(markupName, markupAttrs)
            else:
                match = True
                markupAttrMap = None
                for attr, matchAgainst in self.attrs.items():
                    if not markupAttrMap:
                         if hasattr(markupAttrs, 'get'):
                            markupAttrMap = markupAttrs
                         else:
                            markupAttrMap = {}
                            for k,v in markupAttrs:
                                markupAttrMap[k] = v
                    attrValue = markupAttrMap.get(attr)
                    if not self._matches(attrValue, matchAgainst):
                        match = False
                        break
            if match:
                if markup:
                    found = markup
                else:
                    found = markupName
        return found

    def search(self, markup):
        #print 'looking for %s in %s' % (self, markup)
        found = None
        # If given a list of items, scan it for a text element that
        # matches.
        if hasattr(markup, "__iter__") \
                and not isinstance(markup, Tag):
            for element in markup:
                if isinstance(element, NavigableString) \
                       and self.search(element):
                    found = element
                    break
        # If it's a Tag, make sure its name or attributes match.
        # Don't bother with Tags if we're searching for text.
        elif isinstance(markup, Tag):
            if not self.text:
                found = self.searchTag(markup)
        # If it's text, make sure the text matches.
        elif isinstance(markup, NavigableString) or \
                 isinstance(markup, basestring):
            if self._matches(markup, self.text):
                found = markup
        else:
            raise Exception, "I don't know how to match against a %s" \
                  % markup.__class__
        return found

    def _matches(self, markup, matchAgainst):
        #print "Matching %s against %s" % (markup, matchAgainst)
        result = False
        if matchAgainst is True:
            result = markup is not None
        elif callable(matchAgainst):
            result = matchAgainst(markup)
        else:
            #Custom match methods take the tag as an argument, but all
            #other ways of matching match the tag name as a string.
            if isinstance(markup, Tag):
                markup = markup.name
            if markup and not isinstance(markup, basestring):
                markup = unicode(markup)
            #Now we know that chunk is either a string, or None.
            if hasattr(matchAgainst, 'match'):
                # It's a regexp object.
                result = markup and matchAgainst.search(markup)
            elif hasattr(matchAgainst, '__iter__'): # list-like
                result = markup in matchAgainst
            elif hasattr(matchAgainst, 'items'):
                result = markup.has_key(matchAgainst)
            elif matchAgainst and isinstance(markup, basestring):
                if isinstance(markup, unicode):
                    matchAgainst = unicode(matchAgainst)
                else:
                    matchAgainst = str(matchAgainst)

            if not result:
                result = matchAgainst == markup
        return result

class ResultSet(list):
    """A ResultSet is just a list that keeps track of the SoupStrainer
    that created it."""
    def __init__(self, source):
        list.__init__([])
        self.source = source

# Now, some helper functions.

def buildTagMap(default, *args):
    """Turns a list of maps, lists, or scalars into a single map.
    Used to build the SELF_CLOSING_TAGS, NESTABLE_TAGS, and
    NESTING_RESET_TAGS maps out of lists and partial maps."""
    built = {}
    for portion in args:
        if hasattr(portion, 'items'):
            #It's a map. Merge it.
            for k,v in portion.items():
                built[k] = v
        elif hasattr(portion, '__iter__'): # is a list
            #It's a list. Map each item to the default.
            for k in portion:
                built[k] = default
        else:
            #It's a scalar. Map it to the default.
            built[portion] = default
    return built

# Now, the parser classes.

class BeautifulStoneSoup(Tag, SGMLParser):

    """This class contains the basic parser and search code. It defines
    a parser that knows nothing about tag behavior except for the
    following:

      You can't close a tag without closing all the tags it encloses.
      That is, "<foo><bar></foo>" actually means
      "<foo><bar></bar></foo>".

    [Another possible explanation is "<foo><bar /></foo>", but since
    this class defines no SELF_CLOSING_TAGS, it will never use that
    explanation.]

    This class is useful for parsing XML or made-up markup languages,
    or when BeautifulSoup makes an assumption counter to what you were
    expecting."""

    SELF_CLOSING_TAGS = {}
    NESTABLE_TAGS = {}
    RESET_NESTING_TAGS = {}
    QUOTE_TAGS = {}
    PRESERVE_WHITESPACE_TAGS = []

    MARKUP_MASSAGE = [(re.compile('(<[^<>]*)/>'),
                       lambda x: x.group(1) + ' />'),
                      (re.compile('<!\s+([^<>]*)>'),
                       lambda x: '<!' + x.group(1) + '>')
                      ]

    ROOT_TAG_NAME = u'[document]'

    HTML_ENTITIES = "html"
    XML_ENTITIES = "xml"
    XHTML_ENTITIES = "xhtml"
    # TODO: This only exists for backwards-compatibility
    ALL_ENTITIES = XHTML_ENTITIES

    # Used when determining whether a text node is all whitespace and
    # can be replaced with a single space. A text node that contains
    # fancy Unicode spaces (usually non-breaking) should be left
    # alone.
    STRIP_ASCII_SPACES = { 9: None, 10: None, 12: None, 13: None, 32: None, }

    def __init__(self, markup="", parseOnlyThese=None, fromEncoding=None,
                 markupMassage=True, smartQuotesTo=XML_ENTITIES,
                 convertEntities=None, selfClosingTags=None, isHTML=False):
        """The Soup object is initialized as the 'root tag', and the
        provided markup (which can be a string or a file-like object)
        is fed into the underlying parser.

        sgmllib will process most bad HTML, and the BeautifulSoup
        class has some tricks for dealing with some HTML that kills
        sgmllib, but Beautiful Soup can nonetheless choke or lose data
        if your data uses self-closing tags or declarations
        incorrectly.

        By default, Beautiful Soup uses regexes to sanitize input,
        avoiding the vast majority of these problems. If the problems
        don't apply to you, pass in False for markupMassage, and
        you'll get better performance.

        The default parser massage techniques fix the two most common
        instances of invalid HTML that choke sgmllib:

         <br/> (No space between name of closing tag and tag close)
         <! --Comment--> (Extraneous whitespace in declaration)

        You can pass in a custom list of (RE object, replace method)
        tuples to get Beautiful Soup to scrub your input the way you
        want."""

        self.parseOnlyThese = parseOnlyThese
        self.fromEncoding = fromEncoding
        self.smartQuotesTo = smartQuotesTo
        self.convertEntities = convertEntities
        # Set the rules for how we'll deal with the entities we
        # encounter
        if self.convertEntities:
            # It doesn't make sense to convert encoded characters to
            # entities even while you're converting entities to Unicode.
            # Just convert it all to Unicode.
            self.smartQuotesTo = None
            if convertEntities == self.HTML_ENTITIES:
                self.convertXMLEntities = False
                self.convertHTMLEntities = True
                self.escapeUnrecognizedEntities = True
            elif convertEntities == self.XHTML_ENTITIES:
                self.convertXMLEntities = True
                self.convertHTMLEntities = True
                self.escapeUnrecognizedEntities = False
            elif convertEntities == self.XML_ENTITIES:
                self.convertXMLEntities = True
                self.convertHTMLEntities = False
                self.escapeUnrecognizedEntities = False
        else:
            self.convertXMLEntities = False
            self.convertHTMLEntities = False
            self.escapeUnrecognizedEntities = False

        self.instanceSelfClosingTags = buildTagMap(None, selfClosingTags)
        SGMLParser.__init__(self)

        if hasattr(markup, 'read'):        # It's a file-type object.
            markup = markup.read()
        self.markup = markup
        self.markupMassage = markupMassage
        try:
            self._feed(isHTML=isHTML)
        except StopParsing:
            pass
        self.markup = None                 # The markup can now be GCed

    def convert_charref(self, name):
        """This method fixes a bug in Python's SGMLParser."""
        try:
            n = int(name)
        except ValueError:
            return
        if not 0 <= n <= 127 : # ASCII ends at 127, not 255
            return
        return self.convert_codepoint(n)

    def _feed(self, inDocumentEncoding=None, isHTML=False):
        # Convert the document to Unicode.
        markup = self.markup
        if isinstance(markup, unicode):
            if not hasattr(self, 'originalEncoding'):
                self.originalEncoding = None
        else:
            dammit = UnicodeDammit\
                     (markup, [self.fromEncoding, inDocumentEncoding],
                      smartQuotesTo=self.smartQuotesTo, isHTML=isHTML)
            markup = dammit.unicode
            self.originalEncoding = dammit.originalEncoding
            self.declaredHTMLEncoding = dammit.declaredHTMLEncoding
        if markup:
            if self.markupMassage:
                if not hasattr(self.markupMassage, "__iter__"):
                    self.markupMassage = self.MARKUP_MASSAGE
                for fix, m in self.markupMassage:
                    markup = fix.sub(m, markup)
                # TODO: We get rid of markupMassage so that the
                # soup object can be deepcopied later on. Some
                # Python installations can't copy regexes. If anyone
                # was relying on the existence of markupMassage, this
                # might cause problems.
                del(self.markupMassage)
        self.reset()

        SGMLParser.feed(self, markup)
        # Close out any unfinished strings and close all the open tags.
        self.endData()
        while self.currentTag.name != self.ROOT_TAG_NAME:
            self.popTag()

    def __getattr__(self, methodName):
        """This method routes method call requests to either the SGMLParser
        superclass or the Tag superclass, depending on the method name."""
        #print "__getattr__ called on %s.%s" % (self.__class__, methodName)

        if methodName.startswith('start_') or methodName.startswith('end_') \
               or methodName.startswith('do_'):
            return SGMLParser.__getattr__(self, methodName)
        elif not methodName.startswith('__'):
            return Tag.__getattr__(self, methodName)
        else:
            raise AttributeError

    def isSelfClosingTag(self, name):
        """Returns true iff the given string is the name of a
        self-closing tag according to this parser."""
        return self.SELF_CLOSING_TAGS.has_key(name) \
               or self.instanceSelfClosingTags.has_key(name)

    def reset(self):
        Tag.__init__(self, self, self.ROOT_TAG_NAME)
        self.hidden = 1
        SGMLParser.reset(self)
        self.currentData = []
        self.currentTag = None
        self.tagStack = []
        self.quoteStack = []
        self.pushTag(self)

    def popTag(self):
        tag = self.tagStack.pop()

        #print "Pop", tag.name
        if self.tagStack:
            self.currentTag = self.tagStack[-1]
        return self.currentTag

    def pushTag(self, tag):
        #print "Push", tag.name
        if self.currentTag:
            self.currentTag.contents.append(tag)
        self.tagStack.append(tag)
        self.currentTag = self.tagStack[-1]

    def endData(self, containerClass=NavigableString):
        if self.currentData:
            currentData = u''.join(self.currentData)
            if (currentData.translate(self.STRIP_ASCII_SPACES) == '' and
                not set([tag.name for tag in self.tagStack]).intersection(
                    self.PRESERVE_WHITESPACE_TAGS)):
                if '\n' in currentData:
                    currentData = '\n'
                else:
                    currentData = ' '
            self.currentData = []
            if self.parseOnlyThese and len(self.tagStack) <= 1 and \
                   (not self.parseOnlyThese.text or \
                    not self.parseOnlyThese.search(currentData)):
                return
            o = containerClass(currentData)
            o.setup(self.currentTag, self.previous)
            if self.previous:
                self.previous.next = o
            self.previous = o
            self.currentTag.contents.append(o)


    def _popToTag(self, name, inclusivePop=True):
        """Pops the tag stack up to and including the most recent
        instance of the given tag. If inclusivePop is false, pops the tag
        stack up to but *not* including the most recent instqance of
        the given tag."""
        #print "Popping to %s" % name
        if name == self.ROOT_TAG_NAME:
            return

        numPops = 0
        mostRecentTag = None
        for i in range(len(self.tagStack)-1, 0, -1):
            if name == self.tagStack[i].name:
                numPops = len(self.tagStack)-i
                break
        if not inclusivePop:
            numPops = numPops - 1

        for i in range(0, numPops):
            mostRecentTag = self.popTag()
        return mostRecentTag

    def _smartPop(self, name):

        """We need to pop up to the previous tag of this type, unless
        one of this tag's nesting reset triggers comes between this
        tag and the previous tag of this type, OR unless this tag is a
        generic nesting trigger and another generic nesting trigger
        comes between this tag and the previous tag of this type.

        Examples:
         <p>Foo<b>Bar *<p>* should pop to 'p', not 'b'.
         <p>Foo<table>Bar *<p>* should pop to 'table', not 'p'.
         <p>Foo<table><tr>Bar *<p>* should pop to 'tr', not 'p'.

         <li><ul><li> *<li>* should pop to 'ul', not the first 'li'.
         <tr><table><tr> *<tr>* should pop to 'table', not the first 'tr'
         <td><tr><td> *<td>* should pop to 'tr', not the first 'td'
        """

        nestingResetTriggers = self.NESTABLE_TAGS.get(name)
        isNestable = nestingResetTriggers != None
        isResetNesting = self.RESET_NESTING_TAGS.has_key(name)
        popTo = None
        inclusive = True
        for i in range(len(self.tagStack)-1, 0, -1):
            p = self.tagStack[i]
            if (not p or p.name == name) and not isNestable:
                #Non-nestable tags get popped to the top or to their
                #last occurance.
                popTo = name
                break
            if (nestingResetTriggers is not None
                and p.name in nestingResetTriggers) \
                or (nestingResetTriggers is None and isResetNesting
                    and self.RESET_NESTING_TAGS.has_key(p.name)):

                #If we encounter one of the nesting reset triggers
                #peculiar to this tag, or we encounter another tag
                #that causes nesting to reset, pop up to but not
                #including that tag.
                popTo = p.name
                inclusive = False
                break
            p = p.parent
        if popTo:
            self._popToTag(popTo, inclusive)

    def unknown_starttag(self, name, attrs, selfClosing=0):
        #print "Start tag %s: %s" % (name, attrs)
        if self.quoteStack:
            #This is not a real tag.
            #print "<%s> is not real!" % name
            attrs = ''.join([' %s="%s"' % (x, y) for x, y in attrs])
            self.handle_data('<%s%s>' % (name, attrs))
            return
        self.endData()

        if not self.isSelfClosingTag(name) and not selfClosing:
            self._smartPop(name)

        if self.parseOnlyThese and len(self.tagStack) <= 1 \
               and (self.parseOnlyThese.text or not self.parseOnlyThese.searchTag(name, attrs)):
            return

        tag = Tag(self, name, attrs, self.currentTag, self.previous)
        if self.previous:
            self.previous.next = tag
        self.previous = tag
        self.pushTag(tag)
        if selfClosing or self.isSelfClosingTag(name):
            self.popTag()
        if name in self.QUOTE_TAGS:
            #print "Beginning quote (%s)" % name
            self.quoteStack.append(name)
            self.literal = 1
        return tag

    def unknown_endtag(self, name):
        #print "End tag %s" % name
        if self.quoteStack and self.quoteStack[-1] != name:
            #This is not a real end tag.
            #print "</%s> is not real!" % name
            self.handle_data('</%s>' % name)
            return
        self.endData()
        self._popToTag(name)
        if self.quoteStack and self.quoteStack[-1] == name:
            self.quoteStack.pop()
            self.literal = (len(self.quoteStack) > 0)

    def handle_data(self, data):
        self.currentData.append(data)

    def _toStringSubclass(self, text, subclass):
        """Adds a certain piece of text to the tree as a NavigableString
        subclass."""
        self.endData()
        self.handle_data(text)
        self.endData(subclass)

    def handle_pi(self, text):
        """Handle a processing instruction as a ProcessingInstruction
        object, possibly one with a %SOUP-ENCODING% slot into which an
        encoding will be plugged later."""
        if text[:3] == "xml":
            text = u"xml version='1.0' encoding='%SOUP-ENCODING%'"
        self._toStringSubclass(text, ProcessingInstruction)

    def handle_comment(self, text):
        "Handle comments as Comment objects."
        self._toStringSubclass(text, Comment)

    def handle_charref(self, ref):
        "Handle character references as data."
        if self.convertEntities:
            data = unichr(int(ref))
        else:
            data = '&#%s;' % ref
        self.handle_data(data)

    def handle_entityref(self, ref):
        """Handle entity references as data, possibly converting known
        HTML and/or XML entity references to the corresponding Unicode
        characters."""
        data = None
        if self.convertHTMLEntities:
            try:
                data = unichr(name2codepoint[ref])
            except KeyError:
                pass

        if not data and self.convertXMLEntities:
                data = self.XML_ENTITIES_TO_SPECIAL_CHARS.get(ref)

        if not data and self.convertHTMLEntities and \
            not self.XML_ENTITIES_TO_SPECIAL_CHARS.get(ref):
                # TODO: We've got a problem here. We're told this is
                # an entity reference, but it's not an XML entity
                # reference or an HTML entity reference. Nonetheless,
                # the logical thing to do is to pass it through as an
                # unrecognized entity reference.
                #
                # Except: when the input is "&carol;" this function
                # will be called with input "carol". When the input is
                # "AT&T", this function will be called with input
                # "T". We have no way of knowing whether a semicolon
                # was present originally, so we don't know whether
                # this is an unknown entity or just a misplaced
                # ampersand.
                #
                # The more common case is a misplaced ampersand, so I
                # escape the ampersand and omit the trailing semicolon.
                data = "&amp;%s" % ref
        if not data:
            # This case is different from the one above, because we
            # haven't already gone through a supposedly comprehensive
            # mapping of entities to Unicode characters. We might not
            # have gone through any mapping at all. So the chances are
            # very high that this is a real entity, and not a
            # misplaced ampersand.
            data = "&%s;" % ref
        self.handle_data(data)

    def handle_decl(self, data):
        "Handle DOCTYPEs and the like as Declaration objects."
        self._toStringSubclass(data, Declaration)

    def parse_declaration(self, i):
        """Treat a bogus SGML declaration as raw data. Treat a CDATA
        declaration as a CData object."""
        j = None
        if self.rawdata[i:i+9] == '<![CDATA[':
             k = self.rawdata.find(']]>', i)
             if k == -1:
                 k = len(self.rawdata)
             data = self.rawdata[i+9:k]
             j = k+3
             self._toStringSubclass(data, CData)
        else:
            try:
                j = SGMLParser.parse_declaration(self, i)
            except SGMLParseError:
                toHandle = self.rawdata[i:]
                self.handle_data(toHandle)
                j = i + len(toHandle)
        return j

class BeautifulSoup(BeautifulStoneSoup):

    """This parser knows the following facts about HTML:

    * Some tags have no closing tag and should be interpreted as being
      closed as soon as they are encountered.

    * The text inside some tags (ie. 'script') may contain tags which
      are not really part of the document and which should be parsed
      as text, not tags. If you want to parse the text as tags, you can
      always fetch it and parse it explicitly.

    * Tag nesting rules:

      Most tags can't be nested at all. For instance, the occurance of
      a <p> tag should implicitly close the previous <p> tag.

       <p>Para1<p>Para2
        should be transformed into:
       <p>Para1</p><p>Para2

      Some tags can be nested arbitrarily. For instance, the occurance
      of a <blockquote> tag should _not_ implicitly close the previous
      <blockquote> tag.

       Alice said: <blockquote>Bob said: <blockquote>Blah
        should NOT be transformed into:
       Alice said: <blockquote>Bob said: </blockquote><blockquote>Blah

      Some tags can be nested, but the nesting is reset by the
      interposition of other tags. For instance, a <tr> tag should
      implicitly close the previous <tr> tag within the same <table>,
      but not close a <tr> tag in another table.

       <table><tr>Blah<tr>Blah
        should be transformed into:
       <table><tr>Blah</tr><tr>Blah
        but,
       <tr>Blah<table><tr>Blah
        should NOT be transformed into
       <tr>Blah<table></tr><tr>Blah

    Differing assumptions about tag nesting rules are a major source
    of problems with the BeautifulSoup class. If BeautifulSoup is not
    treating as nestable a tag your page author treats as nestable,
    try ICantBelieveItsBeautifulSoup, MinimalSoup, or
    BeautifulStoneSoup before writing your own subclass."""

    def __init__(self, *args, **kwargs):
        if not kwargs.has_key('smartQuotesTo'):
            kwargs['smartQuotesTo'] = self.HTML_ENTITIES
        kwargs['isHTML'] = True
        BeautifulStoneSoup.__init__(self, *args, **kwargs)

    SELF_CLOSING_TAGS = buildTagMap(None,
                                    ('br' , 'hr', 'input', 'img', 'meta',
                                    'spacer', 'link', 'frame', 'base', 'col'))

    PRESERVE_WHITESPACE_TAGS = set(['pre', 'textarea'])

    QUOTE_TAGS = {'script' : None, 'textarea' : None}

    #According to the HTML standard, each of these inline tags can
    #contain another tag of the same type. Furthermore, it's common
    #to actually use these tags this way.
    NESTABLE_INLINE_TAGS = ('span', 'font', 'q', 'object', 'bdo', 'sub', 'sup',
                            'center')

    #According to the HTML standard, these block tags can contain
    #another tag of the same type. Furthermore, it's common
    #to actually use these tags this way.
    NESTABLE_BLOCK_TAGS = ('blockquote', 'div', 'fieldset', 'ins', 'del')

    #Lists can contain other lists, but there are restrictions.
    NESTABLE_LIST_TAGS = { 'ol' : [],
                           'ul' : [],
                           'li' : ['ul', 'ol'],
                           'dl' : [],
                           'dd' : ['dl'],
                           'dt' : ['dl'] }

    #Tables can contain other tables, but there are restrictions.
    NESTABLE_TABLE_TAGS = {'table' : [],
                           'tr' : ['table', 'tbody', 'tfoot', 'thead'],
                           'td' : ['tr'],
                           'th' : ['tr'],
                           'thead' : ['table'],
                           'tbody' : ['table'],
                           'tfoot' : ['table'],
                           }

    NON_NESTABLE_BLOCK_TAGS = ('address', 'form', 'p', 'pre')

    #If one of these tags is encountered, all tags up to the next tag of
    #this type are popped.
    RESET_NESTING_TAGS = buildTagMap(None, NESTABLE_BLOCK_TAGS, 'noscript',
                                     NON_NESTABLE_BLOCK_TAGS,
                                     NESTABLE_LIST_TAGS,
                                     NESTABLE_TABLE_TAGS)

    NESTABLE_TAGS = buildTagMap([], NESTABLE_INLINE_TAGS, NESTABLE_BLOCK_TAGS,
                                NESTABLE_LIST_TAGS, NESTABLE_TABLE_TAGS)

    # Used to detect the charset in a META tag; see start_meta
    CHARSET_RE = re.compile("((^|;)\s*charset=)([^;]*)", re.M)

    def start_meta(self, attrs):
        """Beautiful Soup can detect a charset included in a META tag,
        try to convert the document to that charset, and re-parse the
        document from the beginning."""
        httpEquiv = None
        contentType = None
        contentTypeIndex = None
        tagNeedsEncodingSubstitution = False

        for i in range(0, len(attrs)):
            key, value = attrs[i]
            key = key.lower()
            if key == 'http-equiv':
                httpEquiv = value
            elif key == 'content':
                contentType = value
                contentTypeIndex = i

        if httpEquiv and contentType: # It's an interesting meta tag.
            match = self.CHARSET_RE.search(contentType)
            if match:
                if (self.declaredHTMLEncoding is not None or
                    self.originalEncoding == self.fromEncoding):
                    # An HTML encoding was sniffed while converting
                    # the document to Unicode, or an HTML encoding was
                    # sniffed during a previous pass through the
                    # document, or an encoding was specified
                    # explicitly and it worked. Rewrite the meta tag.
                    def rewrite(match):
                        return match.group(1) + "%SOUP-ENCODING%"
                    newAttr = self.CHARSET_RE.sub(rewrite, contentType)
                    attrs[contentTypeIndex] = (attrs[contentTypeIndex][0],
                                               newAttr)
                    tagNeedsEncodingSubstitution = True
                else:
                    # This is our first pass through the document.
                    # Go through it again with the encoding information.
                    newCharset = match.group(3)
                    if newCharset and newCharset != self.originalEncoding:
                        self.declaredHTMLEncoding = newCharset
                        self._feed(self.declaredHTMLEncoding)
                        raise StopParsing
                    pass
        tag = self.unknown_starttag("meta", attrs)
        if tag and tagNeedsEncodingSubstitution:
            tag.containsSubstitutions = True

class StopParsing(Exception):
    pass

class ICantBelieveItsBeautifulSoup(BeautifulSoup):

    """The BeautifulSoup class is oriented towards skipping over
    common HTML errors like unclosed tags. However, sometimes it makes
    errors of its own. For instance, consider this fragment:

     <b>Foo<b>Bar</b></b>

    This is perfectly valid (if bizarre) HTML. However, the
    BeautifulSoup class will implicitly close the first b tag when it
    encounters the second 'b'. It will think the author wrote
    "<b>Foo<b>Bar", and didn't close the first 'b' tag, because
    there's no real-world reason to bold something that's already
    bold. When it encounters '</b></b>' it will close two more 'b'
    tags, for a grand total of three tags closed instead of two. This
    can throw off the rest of your document structure. The same is
    true of a number of other tags, listed below.

    It's much more common for someone to forget to close a 'b' tag
    than to actually use nested 'b' tags, and the BeautifulSoup class
    handles the common case. This class handles the not-co-common
    case: where you can't believe someone wrote what they did, but
    it's valid HTML and BeautifulSoup screwed up by assuming it
    wouldn't be."""

    I_CANT_BELIEVE_THEYRE_NESTABLE_INLINE_TAGS = \
     ('em', 'big', 'i', 'small', 'tt', 'abbr', 'acronym', 'strong',
      'cite', 'code', 'dfn', 'kbd', 'samp', 'strong', 'var', 'b',
      'big')

    I_CANT_BELIEVE_THEYRE_NESTABLE_BLOCK_TAGS = ('noscript',)

    NESTABLE_TAGS = buildTagMap([], BeautifulSoup.NESTABLE_TAGS,
                                I_CANT_BELIEVE_THEYRE_NESTABLE_BLOCK_TAGS,
                                I_CANT_BELIEVE_THEYRE_NESTABLE_INLINE_TAGS)

class MinimalSoup(BeautifulSoup):
    """The MinimalSoup class is for parsing HTML that contains
    pathologically bad markup. It makes no assumptions about tag
    nesting, but it does know which tags are self-closing, that
    <script> tags contain Javascript and should not be parsed, that
    META tags may contain encoding information, and so on.

    This also makes it better for subclassing than BeautifulStoneSoup
    or BeautifulSoup."""

    RESET_NESTING_TAGS = buildTagMap('noscript')
    NESTABLE_TAGS = {}

class BeautifulSOAP(BeautifulStoneSoup):
    """This class will push a tag with only a single string child into
    the tag's parent as an attribute. The attribute's name is the tag
    name, and the value is the string child. An example should give
    the flavor of the change:

    <foo><bar>baz</bar></foo>
     =>
    <foo bar="baz"><bar>baz</bar></foo>

    You can then access fooTag['bar'] instead of fooTag.barTag.string.

    This is, of course, useful for scraping structures that tend to
    use subelements instead of attributes, such as SOAP messages. Note
    that it modifies its input, so don't print the modified version
    out.

    I'm not sure how many people really want to use this class; let me
    know if you do. Mainly I like the name."""

    def popTag(self):
        if len(self.tagStack) > 1:
            tag = self.tagStack[-1]
            parent = self.tagStack[-2]
            parent._getAttrMap()
            if (isinstance(tag, Tag) and len(tag.contents) == 1 and
                isinstance(tag.contents[0], NavigableString) and
                not parent.attrMap.has_key(tag.name)):
                parent[tag.name] = tag.contents[0]
        BeautifulStoneSoup.popTag(self)

#Enterprise class names! It has come to our attention that some people
#think the names of the Beautiful Soup parser classes are too silly
#and "unprofessional" for use in enterprise screen-scraping. We feel
#your pain! For such-minded folk, the Beautiful Soup Consortium And
#All-Night Kosher Bakery recommends renaming this file to
#"RobustParser.py" (or, in cases of extreme enterprisiness,
#"RobustParserBeanInterface.class") and using the following
#enterprise-friendly class aliases:
class RobustXMLParser(BeautifulStoneSoup):
    pass
class RobustHTMLParser(BeautifulSoup):
    pass
class RobustWackAssHTMLParser(ICantBelieveItsBeautifulSoup):
    pass
class RobustInsanelyWackAssHTMLParser(MinimalSoup):
    pass
class SimplifyingSOAPParser(BeautifulSOAP):
    pass

######################################################
#
# Bonus library: Unicode, Dammit
#
# This class forces XML data into a standard format (usually to UTF-8
# or Unicode).  It is heavily based on code from Mark Pilgrim's
# Universal Feed Parser. It does not rewrite the XML or HTML to
# reflect a new encoding: that happens in BeautifulStoneSoup.handle_pi
# (XML) and BeautifulSoup.start_meta (HTML).

# Autodetects character encodings.
# Download from http://chardet.feedparser.org/
try:
    import chardet
#    import chardet.constants
#    chardet.constants._debug = 1
except ImportError:
    chardet = None

# cjkcodecs and iconv_codec make Python know about more character encodings.
# Both are available from http://cjkpython.i18n.org/
# They're built in if you use Python 2.4.
try:
    import cjkcodecs.aliases
except ImportError:
    pass
try:
    import iconv_codec
except ImportError:
    pass

class UnicodeDammit:
    """A class for detecting the encoding of a *ML document and
    converting it to a Unicode string. If the source encoding is
    windows-1252, can replace MS smart quotes with their HTML or XML
    equivalents."""

    # This dictionary maps commonly seen values for "charset" in HTML
    # meta tags to the corresponding Python codec names. It only covers
    # values that aren't in Python's aliases and can't be determined
    # by the heuristics in find_codec.
    CHARSET_ALIASES = { "macintosh" : "mac-roman",
                        "x-sjis" : "shift-jis" }

    def __init__(self, markup, overrideEncodings=[],
                 smartQuotesTo='xml', isHTML=False):
        self.declaredHTMLEncoding = None
        self.markup, documentEncoding, sniffedEncoding = \
                     self._detectEncoding(markup, isHTML)
        self.smartQuotesTo = smartQuotesTo
        self.triedEncodings = []
        if markup == '' or isinstance(markup, unicode):
            self.originalEncoding = None
            self.unicode = unicode(markup)
            return

        u = None
        for proposedEncoding in overrideEncodings:
            u = self._convertFrom(proposedEncoding)
            if u: break
        if not u:
            for proposedEncoding in (documentEncoding, sniffedEncoding):
                u = self._convertFrom(proposedEncoding)
                if u: break

        # If no luck and we have auto-detection library, try that:
        if not u and chardet and not isinstance(self.markup, unicode):
            u = self._convertFrom(chardet.detect(self.markup)['encoding'])

        # As a last resort, try utf-8 and windows-1252:
        if not u:
            for proposed_encoding in ("utf-8", "windows-1252"):
                u = self._convertFrom(proposed_encoding)
                if u: break

        self.unicode = u
        if not u: self.originalEncoding = None

    def _subMSChar(self, orig):
        """Changes a MS smart quote character to an XML or HTML
        entity."""
        sub = self.MS_CHARS.get(orig)
        if isinstance(sub, tuple):
            if self.smartQuotesTo == 'xml':
                sub = '&#x%s;' % sub[1]
            else:
                sub = '&%s;' % sub[0]
        return sub

    def _convertFrom(self, proposed):
        proposed = self.find_codec(proposed)
        if not proposed or proposed in self.triedEncodings:
            return None
        self.triedEncodings.append(proposed)
        markup = self.markup

        # Convert smart quotes to HTML if coming from an encoding
        # that might have them.
        if self.smartQuotesTo and proposed.lower() in("windows-1252",
                                                      "iso-8859-1",
                                                      "iso-8859-2"):
            markup = re.compile("([\x80-\x9f])").sub \
                     (lambda(x): self._subMSChar(x.group(1)),
                      markup)

        try:
            # print "Trying to convert document to %s" % proposed
            u = self._toUnicode(markup, proposed)
            self.markup = u
            self.originalEncoding = proposed
        except Exception, e:
            # print "That didn't work!"
            # print e
            return None
        #print "Correct encoding: %s" % proposed
        return self.markup

    def _toUnicode(self, data, encoding):
        '''Given a string and its encoding, decodes the string into Unicode.
        %encoding is a string recognized by encodings.aliases'''

        # strip Byte Order Mark (if present)
        if (len(data) >= 4) and (data[:2] == '\xfe\xff') \
               and (data[2:4] != '\x00\x00'):
            encoding = 'utf-16be'
            data = data[2:]
        elif (len(data) >= 4) and (data[:2] == '\xff\xfe') \
                 and (data[2:4] != '\x00\x00'):
            encoding = 'utf-16le'
            data = data[2:]
        elif data[:3] == '\xef\xbb\xbf':
            encoding = 'utf-8'
            data = data[3:]
        elif data[:4] == '\x00\x00\xfe\xff':
            encoding = 'utf-32be'
            data = data[4:]
        elif data[:4] == '\xff\xfe\x00\x00':
            encoding = 'utf-32le'
            data = data[4:]
        newdata = unicode(data, encoding)
        return newdata

    def _detectEncoding(self, xml_data, isHTML=False):
        """Given a document, tries to detect its XML encoding."""
        xml_encoding = sniffed_xml_encoding = None
        try:
            if xml_data[:4] == '\x4c\x6f\xa7\x94':
                # EBCDIC
                xml_data = self._ebcdic_to_ascii(xml_data)
            elif xml_data[:4] == '\x00\x3c\x00\x3f':
                # UTF-16BE
                sniffed_xml_encoding = 'utf-16be'
                xml_data = unicode(xml_data, 'utf-16be').encode('utf-8')
            elif (len(xml_data) >= 4) and (xml_data[:2] == '\xfe\xff') \
                     and (xml_data[2:4] != '\x00\x00'):
                # UTF-16BE with BOM
                sniffed_xml_encoding = 'utf-16be'
                xml_data = unicode(xml_data[2:], 'utf-16be').encode('utf-8')
            elif xml_data[:4] == '\x3c\x00\x3f\x00':
                # UTF-16LE
                sniffed_xml_encoding = 'utf-16le'
                xml_data = unicode(xml_data, 'utf-16le').encode('utf-8')
            elif (len(xml_data) >= 4) and (xml_data[:2] == '\xff\xfe') and \
                     (xml_data[2:4] != '\x00\x00'):
                # UTF-16LE with BOM
                sniffed_xml_encoding = 'utf-16le'
                xml_data = unicode(xml_data[2:], 'utf-16le').encode('utf-8')
            elif xml_data[:4] == '\x00\x00\x00\x3c':
                # UTF-32BE
                sniffed_xml_encoding = 'utf-32be'
                xml_data = unicode(xml_data, 'utf-32be').encode('utf-8')
            elif xml_data[:4] == '\x3c\x00\x00\x00':
                # UTF-32LE
                sniffed_xml_encoding = 'utf-32le'
                xml_data = unicode(xml_data, 'utf-32le').encode('utf-8')
            elif xml_data[:4] == '\x00\x00\xfe\xff':
                # UTF-32BE with BOM
                sniffed_xml_encoding = 'utf-32be'
                xml_data = unicode(xml_data[4:], 'utf-32be').encode('utf-8')
            elif xml_data[:4] == '\xff\xfe\x00\x00':
                # UTF-32LE with BOM
                sniffed_xml_encoding = 'utf-32le'
                xml_data = unicode(xml_data[4:], 'utf-32le').encode('utf-8')
            elif xml_data[:3] == '\xef\xbb\xbf':
                # UTF-8 with BOM
                sniffed_xml_encoding = 'utf-8'
                xml_data = unicode(xml_data[3:], 'utf-8').encode('utf-8')
            else:
                sniffed_xml_encoding = 'ascii'
                pass
        except:
            xml_encoding_match = None
        xml_encoding_match = re.compile(
            '^<\?.*encoding=[\'"](.*?)[\'"].*\?>').match(xml_data)
        if not xml_encoding_match and isHTML:
            regexp = re.compile('<\s*meta[^>]+charset=([^>]*?)[;\'">]', re.I)
            xml_encoding_match = regexp.search(xml_data)
        if xml_encoding_match is not None:
            xml_encoding = xml_encoding_match.groups()[0].lower()
            if isHTML:
                self.declaredHTMLEncoding = xml_encoding
            if sniffed_xml_encoding and \
               (xml_encoding in ('iso-10646-ucs-2', 'ucs-2', 'csunicode',
                                 'iso-10646-ucs-4', 'ucs-4', 'csucs4',
                                 'utf-16', 'utf-32', 'utf_16', 'utf_32',
                                 'utf16', 'u16')):
                xml_encoding = sniffed_xml_encoding
        return xml_data, xml_encoding, sniffed_xml_encoding


    def find_codec(self, charset):
        return self._codec(self.CHARSET_ALIASES.get(charset, charset)) \
               or (charset and self._codec(charset.replace("-", ""))) \
               or (charset and self._codec(charset.replace("-", "_"))) \
               or charset

    def _codec(self, charset):
        if not charset: return charset
        codec = None
        try:
            codecs.lookup(charset)
            codec = charset
        except (LookupError, ValueError):
            pass
        return codec

    EBCDIC_TO_ASCII_MAP = None
    def _ebcdic_to_ascii(self, s):
        c = self.__class__
        if not c.EBCDIC_TO_ASCII_MAP:
            emap = (0,1,2,3,156,9,134,127,151,141,142,11,12,13,14,15,
                    16,17,18,19,157,133,8,135,24,25,146,143,28,29,30,31,
                    128,129,130,131,132,10,23,27,136,137,138,139,140,5,6,7,
                    144,145,22,147,148,149,150,4,152,153,154,155,20,21,158,26,
                    32,160,161,162,163,164,165,166,167,168,91,46,60,40,43,33,
                    38,169,170,171,172,173,174,175,176,177,93,36,42,41,59,94,
                    45,47,178,179,180,181,182,183,184,185,124,44,37,95,62,63,
                    186,187,188,189,190,191,192,193,194,96,58,35,64,39,61,34,
                    195,97,98,99,100,101,102,103,104,105,196,197,198,199,200,
                    201,202,106,107,108,109,110,111,112,113,114,203,204,205,
                    206,207,208,209,126,115,116,117,118,119,120,121,122,210,
                    211,212,213,214,215,216,217,218,219,220,221,222,223,224,
                    225,226,227,228,229,230,231,123,65,66,67,68,69,70,71,72,
                    73,232,233,234,235,236,237,125,74,75,76,77,78,79,80,81,
                    82,238,239,240,241,242,243,92,159,83,84,85,86,87,88,89,
                    90,244,245,246,247,248,249,48,49,50,51,52,53,54,55,56,57,
                    250,251,252,253,254,255)
            import string
            c.EBCDIC_TO_ASCII_MAP = string.maketrans( \
            ''.join(map(chr, range(256))), ''.join(map(chr, emap)))
        return s.translate(c.EBCDIC_TO_ASCII_MAP)

    MS_CHARS = { '\x80' : ('euro', '20AC'),
                 '\x81' : ' ',
                 '\x82' : ('sbquo', '201A'),
                 '\x83' : ('fnof', '192'),
                 '\x84' : ('bdquo', '201E'),
                 '\x85' : ('hellip', '2026'),
                 '\x86' : ('dagger', '2020'),
                 '\x87' : ('Dagger', '2021'),
                 '\x88' : ('circ', '2C6'),
                 '\x89' : ('permil', '2030'),
                 '\x8A' : ('Scaron', '160'),
                 '\x8B' : ('lsaquo', '2039'),
                 '\x8C' : ('OElig', '152'),
                 '\x8D' : '?',
                 '\x8E' : ('#x17D', '17D'),
                 '\x8F' : '?',
                 '\x90' : '?',
                 '\x91' : ('lsquo', '2018'),
                 '\x92' : ('rsquo', '2019'),
                 '\x93' : ('ldquo', '201C'),
                 '\x94' : ('rdquo', '201D'),
                 '\x95' : ('bull', '2022'),
                 '\x96' : ('ndash', '2013'),
                 '\x97' : ('mdash', '2014'),
                 '\x98' : ('tilde', '2DC'),
                 '\x99' : ('trade', '2122'),
                 '\x9a' : ('scaron', '161'),
                 '\x9b' : ('rsaquo', '203A'),
                 '\x9c' : ('oelig', '153'),
                 '\x9d' : '?',
                 '\x9e' : ('#x17E', '17E'),
                 '\x9f' : ('Yuml', ''),}

#######################################################################


#By default, act as an HTML pretty-printer.
if __name__ == '__main__':
    import sys
    soup = BeautifulSoup(sys.stdin)
    print soup.prettify()

########NEW FILE########
__FILENAME__ = iri2uri
"""
iri2uri

Converts an IRI to a URI.

"""
__author__ = "Joe Gregorio (joe@bitworking.org)"
__copyright__ = "Copyright 2006, Joe Gregorio"
__contributors__ = []
__version__ = "1.0.0"
__license__ = "MIT"
__history__ = """
"""

import urlparse


# Convert an IRI to a URI following the rules in RFC 3987
# 
# The characters we need to enocde and escape are defined in the spec:
#
# iprivate =  %xE000-F8FF / %xF0000-FFFFD / %x100000-10FFFD
# ucschar = %xA0-D7FF / %xF900-FDCF / %xFDF0-FFEF
#         / %x10000-1FFFD / %x20000-2FFFD / %x30000-3FFFD
#         / %x40000-4FFFD / %x50000-5FFFD / %x60000-6FFFD
#         / %x70000-7FFFD / %x80000-8FFFD / %x90000-9FFFD
#         / %xA0000-AFFFD / %xB0000-BFFFD / %xC0000-CFFFD
#         / %xD0000-DFFFD / %xE1000-EFFFD

escape_range = [
   (0xA0, 0xD7FF ),
   (0xE000, 0xF8FF ),
   (0xF900, 0xFDCF ),
   (0xFDF0, 0xFFEF),
   (0x10000, 0x1FFFD ),
   (0x20000, 0x2FFFD ),
   (0x30000, 0x3FFFD),
   (0x40000, 0x4FFFD ),
   (0x50000, 0x5FFFD ),
   (0x60000, 0x6FFFD),
   (0x70000, 0x7FFFD ),
   (0x80000, 0x8FFFD ),
   (0x90000, 0x9FFFD),
   (0xA0000, 0xAFFFD ),
   (0xB0000, 0xBFFFD ),
   (0xC0000, 0xCFFFD),
   (0xD0000, 0xDFFFD ),
   (0xE1000, 0xEFFFD),
   (0xF0000, 0xFFFFD ),
   (0x100000, 0x10FFFD)
]
 
def encode(c):
    retval = c
    i = ord(c)
    for low, high in escape_range:
        if i < low:
            break
        if i >= low and i <= high:
            retval = "".join(["%%%2X" % ord(o) for o in c.encode('utf-8')])
            break
    return retval


def iri2uri(uri):
    """Convert an IRI to a URI. Note that IRIs must be 
    passed in a unicode strings. That is, do not utf-8 encode
    the IRI before passing it into the function.""" 
    if isinstance(uri ,unicode):
        (scheme, authority, path, query, fragment) = urlparse.urlsplit(uri)
        authority = authority.encode('idna')
        # For each character in 'ucschar' or 'iprivate'
        #  1. encode as utf-8
        #  2. then %-encode each octet of that utf-8 
        uri = urlparse.urlunsplit((scheme, authority, path, query, fragment))
        uri = "".join([encode(c) for c in uri])
    return uri
        
if __name__ == "__main__":
    import unittest

    class Test(unittest.TestCase):

        def test_uris(self):
            """Test that URIs are invariant under the transformation."""
            invariant = [ 
                u"ftp://ftp.is.co.za/rfc/rfc1808.txt",
                u"http://www.ietf.org/rfc/rfc2396.txt",
                u"ldap://[2001:db8::7]/c=GB?objectClass?one",
                u"mailto:John.Doe@example.com",
                u"news:comp.infosystems.www.servers.unix",
                u"tel:+1-816-555-1212",
                u"telnet://192.0.2.16:80/",
                u"urn:oasis:names:specification:docbook:dtd:xml:4.1.2" ]
            for uri in invariant:
                self.assertEqual(uri, iri2uri(uri))
            
        def test_iri(self):
            """ Test that the right type of escaping is done for each part of the URI."""
            self.assertEqual("http://xn--o3h.com/%E2%98%84", iri2uri(u"http://\N{COMET}.com/\N{COMET}"))
            self.assertEqual("http://bitworking.org/?fred=%E2%98%84", iri2uri(u"http://bitworking.org/?fred=\N{COMET}"))
            self.assertEqual("http://bitworking.org/#%E2%98%84", iri2uri(u"http://bitworking.org/#\N{COMET}"))
            self.assertEqual("#%E2%98%84", iri2uri(u"#\N{COMET}"))
            self.assertEqual("/fred?bar=%E2%98%9A#%E2%98%84", iri2uri(u"/fred?bar=\N{BLACK LEFT POINTING INDEX}#\N{COMET}"))
            self.assertEqual("/fred?bar=%E2%98%9A#%E2%98%84", iri2uri(iri2uri(u"/fred?bar=\N{BLACK LEFT POINTING INDEX}#\N{COMET}")))
            self.assertNotEqual("/fred?bar=%E2%98%9A#%E2%98%84", iri2uri(u"/fred?bar=\N{BLACK LEFT POINTING INDEX}#\N{COMET}".encode('utf-8')))

    unittest.main()

    

########NEW FILE########
__FILENAME__ = socks
"""SocksiPy - Python SOCKS module.
Version 1.00

Copyright 2006 Dan-Haim. All rights reserved.

Redistribution and use in source and binary forms, with or without modification,
are permitted provided that the following conditions are met:
1. Redistributions of source code must retain the above copyright notice, this
   list of conditions and the following disclaimer.
2. Redistributions in binary form must reproduce the above copyright notice,
   this list of conditions and the following disclaimer in the documentation
   and/or other materials provided with the distribution.
3. Neither the name of Dan Haim nor the names of his contributors may be used
   to endorse or promote products derived from this software without specific
   prior written permission.

THIS SOFTWARE IS PROVIDED BY DAN HAIM "AS IS" AND ANY EXPRESS OR IMPLIED
WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF
MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO
EVENT SHALL DAN HAIM OR HIS CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT,
INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA
OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF
LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT
OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMANGE.


This module provides a standard socket-like interface for Python
for tunneling connections through SOCKS proxies.

"""

"""

Minor modifications made by Christopher Gilbert (http://motomastyle.com/)
for use in PyLoris (http://pyloris.sourceforge.net/)

Minor modifications made by Mario Vilas (http://breakingcode.wordpress.com/)
mainly to merge bug fixes found in Sourceforge

"""

import base64
import socket
import struct
import sys

if getattr(socket, 'socket', None) is None:
    raise ImportError('socket.socket missing, proxy support unusable')

PROXY_TYPE_SOCKS4 = 1
PROXY_TYPE_SOCKS5 = 2
PROXY_TYPE_HTTP = 3
PROXY_TYPE_HTTP_NO_TUNNEL = 4

_defaultproxy = None
_orgsocket = socket.socket

class ProxyError(Exception): pass
class GeneralProxyError(ProxyError): pass
class Socks5AuthError(ProxyError): pass
class Socks5Error(ProxyError): pass
class Socks4Error(ProxyError): pass
class HTTPError(ProxyError): pass

_generalerrors = ("success",
    "invalid data",
    "not connected",
    "not available",
    "bad proxy type",
    "bad input")

_socks5errors = ("succeeded",
    "general SOCKS server failure",
    "connection not allowed by ruleset",
    "Network unreachable",
    "Host unreachable",
    "Connection refused",
    "TTL expired",
    "Command not supported",
    "Address type not supported",
    "Unknown error")

_socks5autherrors = ("succeeded",
    "authentication is required",
    "all offered authentication methods were rejected",
    "unknown username or invalid password",
    "unknown error")

_socks4errors = ("request granted",
    "request rejected or failed",
    "request rejected because SOCKS server cannot connect to identd on the client",
    "request rejected because the client program and identd report different user-ids",
    "unknown error")

def setdefaultproxy(proxytype=None, addr=None, port=None, rdns=True, username=None, password=None):
    """setdefaultproxy(proxytype, addr[, port[, rdns[, username[, password]]]])
    Sets a default proxy which all further socksocket objects will use,
    unless explicitly changed.
    """
    global _defaultproxy
    _defaultproxy = (proxytype, addr, port, rdns, username, password)

def wrapmodule(module):
    """wrapmodule(module)
    Attempts to replace a module's socket library with a SOCKS socket. Must set
    a default proxy using setdefaultproxy(...) first.
    This will only work on modules that import socket directly into the namespace;
    most of the Python Standard Library falls into this category.
    """
    if _defaultproxy != None:
        module.socket.socket = socksocket
    else:
        raise GeneralProxyError((4, "no proxy specified"))

class socksocket(socket.socket):
    """socksocket([family[, type[, proto]]]) -> socket object
    Open a SOCKS enabled socket. The parameters are the same as
    those of the standard socket init. In order for SOCKS to work,
    you must specify family=AF_INET, type=SOCK_STREAM and proto=0.
    """

    def __init__(self, family=socket.AF_INET, type=socket.SOCK_STREAM, proto=0, _sock=None):
        _orgsocket.__init__(self, family, type, proto, _sock)
        if _defaultproxy != None:
            self.__proxy = _defaultproxy
        else:
            self.__proxy = (None, None, None, None, None, None)
        self.__proxysockname = None
        self.__proxypeername = None
        self.__httptunnel = True

    def __recvall(self, count):
        """__recvall(count) -> data
        Receive EXACTLY the number of bytes requested from the socket.
        Blocks until the required number of bytes have been received.
        """
        data = self.recv(count)
        while len(data) < count:
            d = self.recv(count-len(data))
            if not d: raise GeneralProxyError((0, "connection closed unexpectedly"))
            data = data + d
        return data

    def sendall(self, content, *args):
        """ override socket.socket.sendall method to rewrite the header
        for non-tunneling proxies if needed
        """
        if not self.__httptunnel:
            content = self.__rewriteproxy(content)
        return super(socksocket, self).sendall(content, *args)

    def __rewriteproxy(self, header):
        """ rewrite HTTP request headers to support non-tunneling proxies
        (i.e. those which do not support the CONNECT method).
        This only works for HTTP (not HTTPS) since HTTPS requires tunneling.
        """
        host, endpt = None, None
        hdrs = header.split("\r\n")
        for hdr in hdrs:
            if hdr.lower().startswith("host:"):
                host = hdr
            elif hdr.lower().startswith("get") or hdr.lower().startswith("post"):
                endpt = hdr
        if host and endpt:
            hdrs.remove(host)
            hdrs.remove(endpt)
            host = host.split(" ")[1]
            endpt = endpt.split(" ")
            if (self.__proxy[4] != None and self.__proxy[5] != None):
                hdrs.insert(0, self.__getauthheader())
            hdrs.insert(0, "Host: %s" % host)
            hdrs.insert(0, "%s http://%s%s %s" % (endpt[0], host, endpt[1], endpt[2]))
        return "\r\n".join(hdrs)

    def __getauthheader(self):
        auth = self.__proxy[4] + ":" + self.__proxy[5]
        return "Proxy-Authorization: Basic " + base64.b64encode(auth)

    def setproxy(self, proxytype=None, addr=None, port=None, rdns=True, username=None, password=None):
        """setproxy(proxytype, addr[, port[, rdns[, username[, password]]]])
        Sets the proxy to be used.
        proxytype -    The type of the proxy to be used. Three types
                are supported: PROXY_TYPE_SOCKS4 (including socks4a),
                PROXY_TYPE_SOCKS5 and PROXY_TYPE_HTTP
        addr -        The address of the server (IP or DNS).
        port -        The port of the server. Defaults to 1080 for SOCKS
                servers and 8080 for HTTP proxy servers.
        rdns -        Should DNS queries be preformed on the remote side
                (rather than the local side). The default is True.
                Note: This has no effect with SOCKS4 servers.
        username -    Username to authenticate with to the server.
                The default is no authentication.
        password -    Password to authenticate with to the server.
                Only relevant when username is also provided.
        """
        self.__proxy = (proxytype, addr, port, rdns, username, password)

    def __negotiatesocks5(self, destaddr, destport):
        """__negotiatesocks5(self,destaddr,destport)
        Negotiates a connection through a SOCKS5 server.
        """
        # First we'll send the authentication packages we support.
        if (self.__proxy[4]!=None) and (self.__proxy[5]!=None):
            # The username/password details were supplied to the
            # setproxy method so we support the USERNAME/PASSWORD
            # authentication (in addition to the standard none).
            self.sendall(struct.pack('BBBB', 0x05, 0x02, 0x00, 0x02))
        else:
            # No username/password were entered, therefore we
            # only support connections with no authentication.
            self.sendall(struct.pack('BBB', 0x05, 0x01, 0x00))
        # We'll receive the server's response to determine which
        # method was selected
        chosenauth = self.__recvall(2)
        if chosenauth[0:1] != chr(0x05).encode():
            self.close()
            raise GeneralProxyError((1, _generalerrors[1]))
        # Check the chosen authentication method
        if chosenauth[1:2] == chr(0x00).encode():
            # No authentication is required
            pass
        elif chosenauth[1:2] == chr(0x02).encode():
            # Okay, we need to perform a basic username/password
            # authentication.
            self.sendall(chr(0x01).encode() + chr(len(self.__proxy[4])) + self.__proxy[4] + chr(len(self.__proxy[5])) + self.__proxy[5])
            authstat = self.__recvall(2)
            if authstat[0:1] != chr(0x01).encode():
                # Bad response
                self.close()
                raise GeneralProxyError((1, _generalerrors[1]))
            if authstat[1:2] != chr(0x00).encode():
                # Authentication failed
                self.close()
                raise Socks5AuthError((3, _socks5autherrors[3]))
            # Authentication succeeded
        else:
            # Reaching here is always bad
            self.close()
            if chosenauth[1] == chr(0xFF).encode():
                raise Socks5AuthError((2, _socks5autherrors[2]))
            else:
                raise GeneralProxyError((1, _generalerrors[1]))
        # Now we can request the actual connection
        req = struct.pack('BBB', 0x05, 0x01, 0x00)
        # If the given destination address is an IP address, we'll
        # use the IPv4 address request even if remote resolving was specified.
        try:
            ipaddr = socket.inet_aton(destaddr)
            req = req + chr(0x01).encode() + ipaddr
        except socket.error:
            # Well it's not an IP number,  so it's probably a DNS name.
            if self.__proxy[3]:
                # Resolve remotely
                ipaddr = None
                req = req + chr(0x03).encode() + chr(len(destaddr)).encode() + destaddr
            else:
                # Resolve locally
                ipaddr = socket.inet_aton(socket.gethostbyname(destaddr))
                req = req + chr(0x01).encode() + ipaddr
        req = req + struct.pack(">H", destport)
        self.sendall(req)
        # Get the response
        resp = self.__recvall(4)
        if resp[0:1] != chr(0x05).encode():
            self.close()
            raise GeneralProxyError((1, _generalerrors[1]))
        elif resp[1:2] != chr(0x00).encode():
            # Connection failed
            self.close()
            if ord(resp[1:2])<=8:
                raise Socks5Error((ord(resp[1:2]), _socks5errors[ord(resp[1:2])]))
            else:
                raise Socks5Error((9, _socks5errors[9]))
        # Get the bound address/port
        elif resp[3:4] == chr(0x01).encode():
            boundaddr = self.__recvall(4)
        elif resp[3:4] == chr(0x03).encode():
            resp = resp + self.recv(1)
            boundaddr = self.__recvall(ord(resp[4:5]))
        else:
            self.close()
            raise GeneralProxyError((1,_generalerrors[1]))
        boundport = struct.unpack(">H", self.__recvall(2))[0]
        self.__proxysockname = (boundaddr, boundport)
        if ipaddr != None:
            self.__proxypeername = (socket.inet_ntoa(ipaddr), destport)
        else:
            self.__proxypeername = (destaddr, destport)

    def getproxysockname(self):
        """getsockname() -> address info
        Returns the bound IP address and port number at the proxy.
        """
        return self.__proxysockname

    def getproxypeername(self):
        """getproxypeername() -> address info
        Returns the IP and port number of the proxy.
        """
        return _orgsocket.getpeername(self)

    def getpeername(self):
        """getpeername() -> address info
        Returns the IP address and port number of the destination
        machine (note: getproxypeername returns the proxy)
        """
        return self.__proxypeername

    def __negotiatesocks4(self,destaddr,destport):
        """__negotiatesocks4(self,destaddr,destport)
        Negotiates a connection through a SOCKS4 server.
        """
        # Check if the destination address provided is an IP address
        rmtrslv = False
        try:
            ipaddr = socket.inet_aton(destaddr)
        except socket.error:
            # It's a DNS name. Check where it should be resolved.
            if self.__proxy[3]:
                ipaddr = struct.pack("BBBB", 0x00, 0x00, 0x00, 0x01)
                rmtrslv = True
            else:
                ipaddr = socket.inet_aton(socket.gethostbyname(destaddr))
        # Construct the request packet
        req = struct.pack(">BBH", 0x04, 0x01, destport) + ipaddr
        # The username parameter is considered userid for SOCKS4
        if self.__proxy[4] != None:
            req = req + self.__proxy[4]
        req = req + chr(0x00).encode()
        # DNS name if remote resolving is required
        # NOTE: This is actually an extension to the SOCKS4 protocol
        # called SOCKS4A and may not be supported in all cases.
        if rmtrslv:
            req = req + destaddr + chr(0x00).encode()
        self.sendall(req)
        # Get the response from the server
        resp = self.__recvall(8)
        if resp[0:1] != chr(0x00).encode():
            # Bad data
            self.close()
            raise GeneralProxyError((1,_generalerrors[1]))
        if resp[1:2] != chr(0x5A).encode():
            # Server returned an error
            self.close()
            if ord(resp[1:2]) in (91, 92, 93):
                self.close()
                raise Socks4Error((ord(resp[1:2]), _socks4errors[ord(resp[1:2]) - 90]))
            else:
                raise Socks4Error((94, _socks4errors[4]))
        # Get the bound address/port
        self.__proxysockname = (socket.inet_ntoa(resp[4:]), struct.unpack(">H", resp[2:4])[0])
        if rmtrslv != None:
            self.__proxypeername = (socket.inet_ntoa(ipaddr), destport)
        else:
            self.__proxypeername = (destaddr, destport)

    def __negotiatehttp(self, destaddr, destport):
        """__negotiatehttp(self,destaddr,destport)
        Negotiates a connection through an HTTP server.
        """
        # If we need to resolve locally, we do this now
        if not self.__proxy[3]:
            addr = socket.gethostbyname(destaddr)
        else:
            addr = destaddr
        headers =  ["CONNECT ", addr, ":", str(destport), " HTTP/1.1\r\n"]
        headers += ["Host: ", destaddr, "\r\n"]
        if (self.__proxy[4] != None and self.__proxy[5] != None):
                headers += [self.__getauthheader(), "\r\n"]
        headers.append("\r\n")
        self.sendall("".join(headers).encode())
        # We read the response until we get the string "\r\n\r\n"
        resp = self.recv(1)
        while resp.find("\r\n\r\n".encode()) == -1:
            resp = resp + self.recv(1)
        # We just need the first line to check if the connection
        # was successful
        statusline = resp.splitlines()[0].split(" ".encode(), 2)
        if statusline[0] not in ("HTTP/1.0".encode(), "HTTP/1.1".encode()):
            self.close()
            raise GeneralProxyError((1, _generalerrors[1]))
        try:
            statuscode = int(statusline[1])
        except ValueError:
            self.close()
            raise GeneralProxyError((1, _generalerrors[1]))
        if statuscode != 200:
            self.close()
            raise HTTPError((statuscode, statusline[2]))
        self.__proxysockname = ("0.0.0.0", 0)
        self.__proxypeername = (addr, destport)

    def connect(self, destpair):
        """connect(self, despair)
        Connects to the specified destination through a proxy.
        destpar - A tuple of the IP/DNS address and the port number.
        (identical to socket's connect).
        To select the proxy server use setproxy().
        """
        # Do a minimal input check first
        if (not type(destpair) in (list,tuple)) or (len(destpair) < 2) or (not isinstance(destpair[0], basestring)) or (type(destpair[1]) != int):
            raise GeneralProxyError((5, _generalerrors[5]))
        if self.__proxy[0] == PROXY_TYPE_SOCKS5:
            if self.__proxy[2] != None:
                portnum = self.__proxy[2]
            else:
                portnum = 1080
            _orgsocket.connect(self, (self.__proxy[1], portnum))
            self.__negotiatesocks5(destpair[0], destpair[1])
        elif self.__proxy[0] == PROXY_TYPE_SOCKS4:
            if self.__proxy[2] != None:
                portnum = self.__proxy[2]
            else:
                portnum = 1080
            _orgsocket.connect(self,(self.__proxy[1], portnum))
            self.__negotiatesocks4(destpair[0], destpair[1])
        elif self.__proxy[0] == PROXY_TYPE_HTTP:
            if self.__proxy[2] != None:
                portnum = self.__proxy[2]
            else:
                portnum = 8080
            _orgsocket.connect(self,(self.__proxy[1], portnum))
            self.__negotiatehttp(destpair[0], destpair[1])
        elif self.__proxy[0] == PROXY_TYPE_HTTP_NO_TUNNEL:
            if self.__proxy[2] != None:
                portnum = self.__proxy[2]
            else:
                portnum = 8080
            _orgsocket.connect(self,(self.__proxy[1],portnum))
            if destpair[1] == 443:
                self.__negotiatehttp(destpair[0],destpair[1])
            else:
                self.__httptunnel = False
        elif self.__proxy[0] == None:
            _orgsocket.connect(self, (destpair[0], destpair[1]))
        else:
            raise GeneralProxyError((4, _generalerrors[4]))

########NEW FILE########
__FILENAME__ = pyaudio
# PyAudio : Python Bindings for PortAudio.

# Copyright (c) 2006-2010 Hubert Pham

# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:

# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE
# LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
# OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION
# WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.


""" PyAudio : Python Bindings for PortAudio v19.

**These bindings only support PortAudio blocking mode.**

:var PaSampleFormat:
  A list of all PortAudio ``PaSampleFormat`` value constants.

  See: `paInt32`, `paInt24`, `paInt16`, `paInt8`, and `paUInt8`.

:var PaHostApiTypeId:
  A list of all PortAudio ``PaHostApiTypeId`` constants.

  See: `paInDevelopment`, `paDirectSound`, `paMME`, `paASIO`,
  `paSoundManager`, `paCoreAudio`, `paOSS`, `paALSA`, `paAL`, *et al...*

:var PaErrorCode:
  A list of all PortAudio ``PaErrorCode`` constants.
  Typically, error code constants are included in Python
  exception objects (as the second argument).

  See: `paNoError`, `paNotInitialized`, `paUnanticipatedHostError`,
  *et al...*

:group PortAudio Constants:
  PaSampleFormat, PaHostApiTypeId, PaErrorCode

:group PaSampleFormat Values:
  paFloat32, paInt32, paInt24, paInt16,
  paInt8, paUInt8, paCustomFormat

:group PaHostApiTypeId Values:
  paInDevelopment, paDirectSound, paMME, paASIO,
  paSoundManager, paCoreAudio, paOSS, paALSA
  paAL, paBeOS, paWDMKS, paJACK, paWASAPI, paNoDevice

:group PaErrorCode Values:
  paNoError,
  paNotInitialized, paUnanticipatedHostError,
  paInvalidChannelCount, paInvalidSampleRate,
  paInvalidDevice, paInvalidFlag,
  paSampleFormatNotSupported, paBadIODeviceCombination,
  paInsufficientMemory, paBufferTooBig,
  paBufferTooSmall, paNullCallback,
  paBadStreamPtr, paTimedOut,
  paInternalError, paDeviceUnavailable,
  paIncompatibleHostApiSpecificStreamInfo, paStreamIsStopped,
  paStreamIsNotStopped, paInputOverflowed,
  paOutputUnderflowed, paHostApiNotFound,
  paInvalidHostApi, paCanNotReadFromACallbackStream,
  paCanNotWriteToACallbackStream,
  paCanNotReadFromAnOutputOnlyStream,
  paCanNotWriteToAnInputOnlyStream,
  paIncompatibleStreamHostApi

:group Stream Conversion Convenience Functions:
  get_sample_size, get_format_from_width

:group PortAudio version:
  get_portaudio_version, get_portaudio_version_text

:sort: PaSampleFormat, PaHostApiTypeId, PaErrorCode
:sort: PortAudio Constants, PaSampleFormat Values,
       PaHostApiTypeId Values, PaErrorCode Values

"""

__author__ = "Hubert Pham"
__version__ = "0.2.4"
__docformat__ = "restructuredtext en"

import sys

# attempt to import PortAudio
try:
    import _portaudio as pa
except ImportError:
    print "Please build and install the PortAudio Python " +\
          "bindings first."
    sys.exit(-1)


# Try to use Python 2.4's built in `set'
try:
    a = set()
    del a
except NameError:
    from sets import Set as set

############################################################
# GLOBALS
############################################################

##### PaSampleFormat Sample Formats #####

paFloat32 = pa.paFloat32
paInt32 = pa.paInt32
paInt24 = pa.paInt24
paInt16 = pa.paInt16
paInt8 = pa.paInt8
paUInt8 = pa.paUInt8
paCustomFormat = pa.paCustomFormat

# group them together for epydoc
PaSampleFormat = ['paFloat32', 'paInt32', 'paInt24', 'paInt16',
                  'paInt8', 'paUInt8', 'paCustomFormat']


###### HostAPI TypeId #####

paInDevelopment = pa.paInDevelopment
paDirectSound = pa.paDirectSound
paMME = pa.paMME
paASIO = pa.paASIO
paSoundManager = pa.paSoundManager
paCoreAudio = pa.paCoreAudio
paOSS = pa.paOSS
paALSA = pa.paALSA
paAL = pa.paAL
paBeOS = pa.paBeOS
paWDMKS = pa.paWDMKS
paJACK = pa.paJACK
paWASAPI = pa.paWASAPI
paNoDevice = pa.paNoDevice

# group them together for epydoc
PaHostApiTypeId = ['paInDevelopment', 'paDirectSound', 'paMME',
                   'paASIO', 'paSoundManager', 'paCoreAudio',
                   'paOSS', 'paALSA', 'paAL', 'paBeOS',
                   'paWDMKS', 'paJACK', 'paWASAPI', 'paNoDevice']

###### portaudio error codes #####

paNoError = pa.paNoError
paNotInitialized = pa.paNotInitialized
paUnanticipatedHostError = pa.paUnanticipatedHostError
paInvalidChannelCount = pa.paInvalidChannelCount
paInvalidSampleRate = pa.paInvalidSampleRate
paInvalidDevice = pa.paInvalidDevice
paInvalidFlag = pa.paInvalidFlag
paSampleFormatNotSupported = pa.paSampleFormatNotSupported
paBadIODeviceCombination = pa.paBadIODeviceCombination
paInsufficientMemory = pa.paInsufficientMemory
paBufferTooBig = pa.paBufferTooBig
paBufferTooSmall = pa.paBufferTooSmall
paNullCallback = pa.paNullCallback
paBadStreamPtr = pa.paBadStreamPtr
paTimedOut = pa.paTimedOut
paInternalError = pa.paInternalError
paDeviceUnavailable = pa.paDeviceUnavailable
paIncompatibleHostApiSpecificStreamInfo = pa.paIncompatibleHostApiSpecificStreamInfo
paStreamIsStopped = pa.paStreamIsStopped
paStreamIsNotStopped = pa.paStreamIsNotStopped
paInputOverflowed = pa.paInputOverflowed
paOutputUnderflowed = pa.paOutputUnderflowed
paHostApiNotFound = pa.paHostApiNotFound
paInvalidHostApi = pa.paInvalidHostApi
paCanNotReadFromACallbackStream = pa.paCanNotReadFromACallbackStream
paCanNotWriteToACallbackStream = pa.paCanNotWriteToACallbackStream
paCanNotReadFromAnOutputOnlyStream = pa.paCanNotReadFromAnOutputOnlyStream
paCanNotWriteToAnInputOnlyStream = pa.paCanNotWriteToAnInputOnlyStream
paIncompatibleStreamHostApi = pa.paIncompatibleStreamHostApi

# group them together for epydoc
PaErrorCode = ['paNoError',
               'paNotInitialized', 'paUnanticipatedHostError',
               'paInvalidChannelCount', 'paInvalidSampleRate',
               'paInvalidDevice', 'paInvalidFlag',
               'paSampleFormatNotSupported', 'paBadIODeviceCombination',
               'paInsufficientMemory', 'paBufferTooBig',
               'paBufferTooSmall', 'paNullCallback',
               'paBadStreamPtr', 'paTimedOut',
               'paInternalError', 'paDeviceUnavailable',
               'paIncompatibleHostApiSpecificStreamInfo', 'paStreamIsStopped',
               'paStreamIsNotStopped', 'paInputOverflowed',
               'paOutputUnderflowed', 'paHostApiNotFound',
               'paInvalidHostApi', 'paCanNotReadFromACallbackStream',
               'paCanNotWriteToACallbackStream',
               'paCanNotReadFromAnOutputOnlyStream',
               'paCanNotWriteToAnInputOnlyStream',
               'paIncompatibleStreamHostApi']

############################################################
# Convenience Functions
############################################################

def get_sample_size(format):
    """
    Returns the size (in bytes) for the specified
    sample `format` (a `PaSampleFormat` constant).

    :param `format`:
       PortAudio sample format constant `PaSampleFormat`.

    :raises ValueError: Invalid specified `format`.

    :rtype: int
    """

    return pa.get_sample_size(format)

def get_format_from_width(width, unsigned = True):
    """
    Returns a PortAudio format constant for
    the specified `width`.

    :param `width`:
      The desired sample width in bytes (1, 2, 3, or 4)
    :param `unsigned`:
      For 1 byte width, specifies signed or unsigned
      format.

    :raises ValueError: for invalid `width`
    :rtype: `PaSampleFormat`

    """

    if width == 1:
        if unsigned:
            return paUInt8
        else:
            return paInt8
    elif width == 2:
        return paInt16
    elif width == 3:
        return paInt24
    elif width == 4:
        return paFloat32
    else:
        raise ValueError, "Invalid width: %d" % width


############################################################
# Versioning
############################################################

def get_portaudio_version():
    """
    Returns portaudio version.

    :rtype: str """

    return pa.get_version()

def get_portaudio_version_text():
    """
    Returns PortAudio version as a text string.

    :rtype: str """

    return pa.get_version_text()

############################################################
# Wrapper around _portaudio Stream (Internal)
############################################################

# Note: See PyAudio class below for main export.

class Stream:

    """
    PortAudio Stream Wrapper. Use `PyAudio.open` to make a new
    `Stream`.

    :group Opening and Closing:
      __init__, close

    :group Stream Info:
      get_input_latency, get_output_latency, get_time, get_cpu_load

    :group Stream Management:
      start_stream, stop_stream, is_active, is_stopped

    :group Input Output:
      write, read, get_read_available, get_write_available

    """

    def __init__(self,
                 PA_manager,
                 rate,
                 channels,
                 format,
                 input = False,
                 output = False,
                 input_device_index = None,
                 output_device_index = None,
                 frames_per_buffer = 1024,
                 start = True,
                 input_host_api_specific_stream_info = None,
                 output_host_api_specific_stream_info = None):
        """
        Initialize a stream; this should be called by
        `PyAudio.open`. A stream can either be input, output, or both.


        :param `PA_manager`: A reference to the managing `PyAudio` instance
        :param `rate`: Sampling rate
        :param `channels`: Number of channels
        :param `format`: Sampling size and format. See `PaSampleFormat`.
        :param `input`: Specifies whether this is an input stream.
            Defaults to False.
        :param `output`: Specifies whether this is an output stream.
            Defaults to False.
        :param `input_device_index`: Index of Input Device to use.
            Unspecified (or None) uses default device.
            Ignored if `input` is False.
        :param `output_device_index`:
            Index of Output Device to use.
            Unspecified (or None) uses the default device.
            Ignored if `output` is False.
        :param `frames_per_buffer`: Specifies the number of frames per buffer.
        :param `start`: Start the stream running immediately.
            Defaults to True. In general, there is no reason to set
            this to false.
        :param `input_host_api_specific_stream_info`: Specifies a host API
            specific stream information data structure for input.
            See `PaMacCoreStreamInfo`.
        :param `output_host_api_specific_stream_info`: Specifies a host API
            specific stream information data structure for output.
            See `PaMacCoreStreamInfo`.

        :raise ValueError: Neither input nor output
         are set True.

        """

        # no stupidity allowed
        if not (input or output):
            raise ValueError, \
                  "Must specify an input or output " +\
                  "stream."

        # remember parent
        self._parent = PA_manager

        # remember if we are an: input, output (or both)
        self._is_input = input
        self._is_output = output

        # are we running?
        self._is_running = start

        # remember some parameters
        self._rate = rate
        self._channels = channels
        self._format = format
        self._frames_per_buffer = frames_per_buffer

        arguments = {
            'rate' : rate,
            'channels' : channels,
            'format' : format,
            'input' : input,
            'output' : output,
            'input_device_index' : input_device_index,
            'output_device_index' : output_device_index,
            'frames_per_buffer' : frames_per_buffer}

        if input_host_api_specific_stream_info:
            _l = input_host_api_specific_stream_info
            arguments[
                'input_host_api_specific_stream_info'
                ] = _l._get_host_api_stream_object()

        if output_host_api_specific_stream_info:
            _l = output_host_api_specific_stream_info
            arguments[
                'output_host_api_specific_stream_info'
                ] = _l._get_host_api_stream_object()

        # calling pa.open returns a stream object
        self._stream = pa.open(**arguments)

        self._input_latency = self._stream.inputLatency
        self._output_latency = self._stream.outputLatency

        if self._is_running:
            pa.start_stream(self._stream)


    def close(self):
        """ Close the stream """

        pa.close(self._stream)

        self._is_running = False

        self._parent._remove_stream(self)


    ############################################################
    # Stream Info
    ############################################################

    def get_input_latency(self):
        """
        Return the input latency.

        :rtype: float
        """

        return self._stream.inputLatency


    def get_output_latency(self):
        """
        Return the input latency.

        :rtype: float
        """

        return self._stream.outputLatency

    def get_time(self):
        """
        Return stream time.

        :rtype: float

        """

        return pa.get_stream_time(self._stream)

    def get_cpu_load(self):
        """
        Return the CPU load.

        (Note: this is always 0.0 for the blocking API.)

        :rtype: float

        """

        return pa.get_stream_cpu_load(self._stream)


    ############################################################
    # Stream Management
    ############################################################

    def start_stream(self):
        """ Start the stream. """

        if self._is_running:
            return

        pa.start_stream(self._stream)
        self._is_running = True

    def stop_stream(self):

        """ Stop the stream. Once the stream is stopped,
        one may not call write or read. However, one may
        call start_stream to resume the stream. """

        if not self._is_running:
            return

        pa.stop_stream(self._stream)
        self._is_running = False

    def is_active(self):
        """ Returns whether the stream is active.

        :rtype: bool """

        return pa.is_stream_active(self._stream)

    def is_stopped(self):
        """ Returns whether the stream is stopped.

        :rtype: bool """

        return pa.is_stream_stopped(self._stream)


    ############################################################
    # Reading/Writing
    ############################################################

    def write(self, frames, num_frames = None,
              exception_on_underflow = False):

        """
        Write samples to the stream.


        :param `frames`:
           The frames of data.
        :param `num_frames`:
           The number of frames to write.
           Defaults to None, in which this value will be
           automatically computed.
        :param `exception_on_underflow`:
           Specifies whether an exception should be thrown
           (or silently ignored) on buffer underflow. Defaults
           to False for improved performance, especially on
           slower platforms.

        :raises IOError: if the stream is not an output stream
         or if the write operation was unsuccessful.

        :rtype: `None`

        """

        if not self._is_output:
            raise IOError("Not output stream",
                          paCanNotWriteToAnInputOnlyStream)

        if num_frames == None:
            # determine how many frames to read
            width = get_sample_size(self._format)
            num_frames = len(frames) / (self._channels * width)
            #print len(frames), self._channels, self._width, num_frames

        pa.write_stream(self._stream, frames, num_frames,
                        exception_on_underflow)


    def read(self, num_frames):
        """
        Read samples from the stream.


        :param `num_frames`:
           The number of frames to read.

        :raises IOError: if stream is not an input stream
         or if the read operation was unsuccessful.

        :rtype: str

        """

        if not self._is_input:
            raise IOError("Not input stream",
                          paCanNotReadFromAnOutputOnlyStream)

        return pa.read_stream(self._stream, num_frames)

    def get_read_available(self):
        """
        Return the number of frames that can be read
        without waiting.

        :rtype: int
        """

        return pa.get_stream_read_available(self._stream)


    def get_write_available(self):
        """
        Return the number of frames that can be written
        without waiting.

        :rtype: int

        """

        return pa.get_stream_write_available(self._stream)



############################################################
# Main Export
############################################################

class PyAudio:

    """
    Python interface to PortAudio. Provides methods to:
     - initialize and terminate PortAudio
     - open and close streams
     - query and inspect the available PortAudio Host APIs
     - query and inspect the available PortAudio audio
       devices

    Use this class to open and close streams.

    :group Stream Management:
      open, close

    :group Host API:
      get_host_api_count, get_default_host_api_info,
      get_host_api_info_by_type, get_host_api_info_by_index,
      get_device_info_by_host_api_device_index

    :group Device API:
      get_device_count, is_format_supported,
      get_default_input_device_info,
      get_default_output_device_info,
      get_device_info_by_index

    :group Stream Format Conversion:
      get_sample_size, get_format_from_width

    """

    ############################################################
    # Initialization and Termination
    ############################################################

    def __init__(self):

        """ Initialize PortAudio. """

        pa.initialize()
        self._streams = set()

    def terminate(self):

        """ Terminate PortAudio.

        :attention: Be sure to call this method for every
          instance of this object to release PortAudio resources.
        """

        for stream in self._streams:
            stream.close()

        self._streams = set()

        pa.terminate()


    ############################################################
    # Stream Format
    ############################################################

    def get_sample_size(self, format):
        """
        Returns the size (in bytes) for the specified
        sample `format` (a `PaSampleFormat` constant).


        :param `format`:
           Sample format constant (`PaSampleFormat`).

        :raises ValueError: Invalid specified `format`.

        :rtype: int
        """

        return pa.get_sample_size(format)


    def get_format_from_width(self, width, unsigned = True):
        """
        Returns a PortAudio format constant for
        the specified `width`.

        :param `width`:
            The desired sample width in bytes (1, 2, 3, or 4)
        :param `unsigned`:
            For 1 byte width, specifies signed or unsigned format.

        :raises ValueError: for invalid `width`

        :rtype: `PaSampleFormat`
        """

        if width == 1:
            if unsigned:
                return paUInt8
            else:
                return paInt8
        elif width == 2:
            return paInt16
        elif width == 3:
            return paInt24
        elif width == 4:
            return paFloat32
        else:
            raise ValueError, "Invalid width: %d" % width


    ############################################################
    # Stream Factory
    ############################################################

    def open(self, *args, **kwargs):
        """
        Open a new stream. See constructor for
        `Stream.__init__` for parameter details.

        :returns: `Stream` """

        stream = Stream(self, *args, **kwargs)
        self._streams.add(stream)
        return stream


    def close(self, stream):
        """
        Close a stream. Typically use `Stream.close` instead.

        :param `stream`:
           An instance of the `Stream` object.

        :raises ValueError: if stream does not exist.
        """

        if stream not in self._streams:
            raise ValueError, "Stream `%s' not found" % str(stream)

        stream.close()


    def _remove_stream(self, stream):
        """
        Internal method. Removes a stream.

        :param `stream`:
           An instance of the `Stream` object.

        """

        if stream in self._streams:
            self._streams.remove(stream)


    ############################################################
    # Host API Inspection
    ############################################################

    def get_host_api_count(self):
        """
        Return the number of PortAudio Host APIs.

        :rtype: int
        """

        return pa.get_host_api_count()

    def get_default_host_api_info(self):
        """
        Return a dictionary containing the default Host API
        parameters. The keys of the dictionary mirror the data fields
        of PortAudio's ``PaHostApiInfo`` structure.

        :raises IOError: if no default input device available
        :rtype: dict

        """

        defaultHostApiIndex = pa.get_default_host_api()
        return self.get_host_api_info_by_index(defaultHostApiIndex)


    def get_host_api_info_by_type(self, host_api_type):
        """
        Return a dictionary containing the Host API parameters for the
        host API specified by the `host_api_type`. The keys of the
        dictionary mirror the data fields of PortAudio's ``PaHostApiInfo``
        structure.


        :param `host_api_type`:
           The desired Host API (`PaHostApiTypeId` constant).

        :raises IOError: for invalid `host_api_type`
        :rtype: dict
        """

        index = pa.host_api_type_id_to_host_api_index(host_api_type)
        return self.get_host_api_info_by_index(index)


    def get_host_api_info_by_index(self, host_api_index):
        """
        Return a dictionary containing the Host API parameters for the
        host API specified by the `host_api_index`. The keys of the
        dictionary mirror the data fields of PortAudio's ``PaHostApiInfo``
        structure.

        :param `host_api_index`: The host api index.

        :raises IOError: for invalid `host_api_index`

        :rtype: dict
        """

        return self._make_host_api_dictionary(
            host_api_index,
            pa.get_host_api_info(host_api_index)
            )

    def get_device_info_by_host_api_device_index(self,
                                                 host_api_index,
                                                 host_api_device_index):
        """
        Return a dictionary containing the Device parameters for a
        given Host API's n'th device. The keys of the dictionary
        mirror the data fields of PortAudio's ``PaDeviceInfo`` structure.


        :param `host_api_index`:
           The Host API index number.
        :param `host_api_device_index`:
           The *n* 'th device of the host API.

        :raises IOError: for invalid indices

        :rtype: dict
        """

        long_method_name = pa.host_api_device_index_to_device_index
        device_index = long_method_name(host_api_index,
                                        host_api_device_index)
        return self.get_device_info_by_index(device_index)


    def _make_host_api_dictionary(self, index, host_api_struct):
        """
        Internal method to create Host API dictionary
        that mirrors PortAudio's ``PaHostApiInfo`` structure.

        :rtype: dict
        """

        return {'index' : index,
                'structVersion' : host_api_struct.structVersion,
                'type' : host_api_struct.type,
                'name' : host_api_struct.name,
                'deviceCount' : host_api_struct.deviceCount,
                'defaultInputDevice' : host_api_struct.defaultInputDevice,
                'defaultOutputDevice' : host_api_struct.defaultOutputDevice}

    ############################################################
    # Device Inspection
    ############################################################

    def get_device_count(self):
        """
        Return the number of PortAudio Host APIs.

        :rtype: int
        """

        return pa.get_device_count()

    def is_format_supported(self, rate,
                            input_device = None,
                            input_channels = None,
                            input_format = None,
                            output_device = None,
                            output_channels = None,
                            output_format = None):
        """
        Check to see if specified device configuration
        is supported. Returns True if the configuration
        is supported; throws a ValueError exception otherwise.

        :param `rate`:
           Specifies the desired rate (in Hz)
        :param `input_device`:
           The input device index. Specify `None` (default) for
           half-duplex output-only streams.
        :param `input_channels`:
           The desired number of input channels. Ignored if
           `input_device` is not specified (or `None`).
        :param `input_format`:
           PortAudio sample format constant defined
           in this module
        :param `output_device`:
           The output device index. Specify `None` (default) for
           half-duplex input-only streams.
        :param `output_channels`:
           The desired number of output channels. Ignored if
           `input_device` is not specified (or `None`).
        :param `output_format`:
           PortAudio sample format constant (`PaSampleFormat`).

        :rtype: bool
        :raises ValueError: tuple containing:
           (error string, PortAudio error code `PaErrorCode`).

        """

        if input_device == None and output_device == None:
            raise ValueError("must specify stream format for input, " +\
                             "output, or both", paInvalidDevice);

        kwargs = {}

        if input_device != None:
            kwargs['input_device'] = input_device
            kwargs['input_channels'] = input_channels
            kwargs['input_format'] = input_format

        if output_device != None:
            kwargs['output_device'] = output_device
            kwargs['output_channels'] = output_channels
            kwargs['output_format'] = output_format

        return pa.is_format_supported(rate, **kwargs)


    def get_default_input_device_info(self):
        """
        Return the default input Device parameters as a
        dictionary. The keys of the dictionary mirror the data fields
        of PortAudio's ``PaDeviceInfo`` structure.

        :raises IOError: No default input device available.
        :rtype: dict
        """

        device_index = pa.get_default_input_device()
        return self.get_device_info_by_index(device_index)

    def get_default_output_device_info(self):
        """
        Return the default output Device parameters as a
        dictionary. The keys of the dictionary mirror the data fields
        of PortAudio's ``PaDeviceInfo`` structure.

        :raises IOError: No default output device available.
        :rtype: dict
        """

        device_index = pa.get_default_output_device()
        return self.get_device_info_by_index(device_index)


    def get_device_info_by_index(self, device_index):
        """
        Return the Device parameters for device specified in
        `device_index` as a dictionary. The keys of the dictionary
        mirror the data fields of PortAudio's ``PaDeviceInfo``
        structure.

        :param `device_index`: The device index.
        :raises IOError: Invalid `device_index`.
        :rtype: dict
        """

        return self._make_device_info_dictionary(
            device_index,
            pa.get_device_info(device_index)
            )

    def _make_device_info_dictionary(self, index, device_info):
        """
        Internal method to create Device Info dictionary
        that mirrors PortAudio's ``PaDeviceInfo`` structure.

        :rtype: dict
        """

        return {'index' : index,
                'structVersion' : device_info.structVersion,
                'name' : device_info.name,
                'hostApi' : device_info.hostApi,
                'maxInputChannels' : device_info.maxInputChannels,
                'maxOutputChannels' : device_info.maxOutputChannels,
                'defaultLowInputLatency' :
                device_info.defaultLowInputLatency,
                'defaultLowOutputLatency' :
                device_info.defaultLowOutputLatency,
                'defaultHighInputLatency' :
                device_info.defaultHighInputLatency,
                'defaultHighOutputLatency' :
                device_info.defaultHighOutputLatency,
                'defaultSampleRate' :
                device_info.defaultSampleRate
                }

######################################################################
# Host Specific Stream Info
######################################################################

try:
    paMacCoreStreamInfo = pa.paMacCoreStreamInfo
except AttributeError:
    pass
else:
    class PaMacCoreStreamInfo:

        """
        Mac OS X-only: PaMacCoreStreamInfo is a PortAudio Host API
        Specific Stream Info data structure for specifying Mac OS
        X-only settings. Instantiate this class (if desired) and pass
        the instance as the argument in `PyAudio.open` to parameters
        ``input_host_api_specific_stream_info`` or
        ``output_host_api_specific_stream_info``. (See `Stream.__init__`.)

        :note: Mac OS X only.

        :group Flags (constants):
          paMacCoreChangeDeviceParameters, paMacCoreFailIfConversionRequired,
          paMacCoreConversionQualityMin, paMacCoreConversionQualityMedium,
          paMacCoreConversionQualityLow, paMacCoreConversionQualityHigh,
          paMacCoreConversionQualityMax, paMacCorePlayNice,
          paMacCorePro, paMacCoreMinimizeCPUButPlayNice, paMacCoreMinimizeCPU

        :group Settings:
          get_flags, get_channel_map

        """
        paMacCoreChangeDeviceParameters = pa.paMacCoreChangeDeviceParameters
        paMacCoreFailIfConversionRequired = pa.paMacCoreFailIfConversionRequired
        paMacCoreConversionQualityMin = pa.paMacCoreConversionQualityMin
        paMacCoreConversionQualityMedium = pa.paMacCoreConversionQualityMedium
        paMacCoreConversionQualityLow = pa.paMacCoreConversionQualityLow
        paMacCoreConversionQualityHigh = pa.paMacCoreConversionQualityHigh
        paMacCoreConversionQualityMax = pa.paMacCoreConversionQualityMax
        paMacCorePlayNice = pa.paMacCorePlayNice
        paMacCorePro = pa.paMacCorePro
        paMacCoreMinimizeCPUButPlayNice = pa.paMacCoreMinimizeCPUButPlayNice
        paMacCoreMinimizeCPU = pa.paMacCoreMinimizeCPU

        def __init__(self, flags = None, channel_map = None):
            """
            Initialize with flags and channel_map. See PortAudio
            documentation for more details on these parameters; they are
            passed almost verbatim to the PortAudio library.

            :param `flags`: paMacCore* flags OR'ed together.
                See `PaMacCoreStreamInfo`.
            :param `channel_map`: An array describing the channel mapping.
                See PortAudio documentation for usage.
            """

            kwargs = {"flags" : flags,
                      "channel_map" : channel_map}

            if flags == None:
                del kwargs["flags"]
            if channel_map == None:
                del kwargs["channel_map"]

            self._paMacCoreStreamInfo = paMacCoreStreamInfo(**kwargs)

        def get_flags(self):
            """
            Return the flags set at instantiation.

            :rtype: int
            """

            return self._paMacCoreStreamInfo.flags

        def get_channel_map(self):
            """
            Return the channel map set at instantiation.

            :rtype: tuple or None
            """

            return self._paMacCoreStreamInfo.channel_map

        def _get_host_api_stream_object(self):
            """ Private method. """

            return self._paMacCoreStreamInfo

########NEW FILE########
