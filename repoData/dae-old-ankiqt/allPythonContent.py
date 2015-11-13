__FILENAME__ = about
# Copyright: Damien Elmes <anki@ichi2.net>
# -*- coding: utf-8 -*-
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

from aqt.qt import *
import aqt.forms
from aqt import appVersion

def show(parent):
    dialog = QDialog(parent)
    abt = aqt.forms.about.Ui_About()
    abt.setupUi(dialog)
    abouttext = "<center><img src=':/icons/anki-logo-thin.png'></center>"
    abouttext += '<p>' + _("Anki is a friendly, intelligent spaced learning \
system. It's free and open source.")
    abouttext += '<p>' + _("Version %s") % appVersion + '<br>'
    abouttext += (_("<a href='%s'>Visit website</a>") % aqt.appWebsite) + \
"</span>"
    abouttext += '<p>' + _("Written by Damien Elmes, with patches, translation,\
 testing and design from:<p>%(cont)s") % {'cont': u"""Aaron Harsh, Ádám Szegi,
Alex Fraser, Andreas Klauer, Andrew Wright, Bernhard Ibertsberger, Charlene Barina,
Christian Krause, Christian Rusche, David Smith, Dave Druelinger, Dotan Cohen,
Emilio Wuerges, Emmanuel Jarri, Frank Harper, Gregor Skumavc, H. Mijail,
Ian Lewis, Immanuel Asmus, Iroiro, Jarvik7,
Jin Eun-Deok, Jo Nakashima, Johanna Lindh, Kieran Clancy, LaC, Laurent Steffan,
Luca Ban, Luciano Esposito, Marco Giancotti, Marcus Rubeus, Mari Egami, Michael Jürges, Mark Wilbur,
Matthew Duggan, Matthew Holtz, Meelis Vasser, Michael Keppler, Michael
Montague, Michael Penkov, Michal Čadil, Nathanael Law, Nick Cook, Niklas
Laxström, Nguyễn Hào Khôi, Norbert Nagold, Ole Guldberg,
Pcsl88, Petr Michalec, Piotr Kubowicz, Richard Colley, Roland Sieker,
Samson Melamed, Stefaan De Pooter, Susanna Björverud, Sylvain Durand,
Tacutu, Timm Preetz, Timo Paulssen, Ursus, Victor Suba, %s
Xtru."""% _("<!--about diag--> and")}
    abouttext += '<p>' + _("""\
The icons were obtained from various sources; please see the Anki source
for credits.""")
    abouttext += '<p>' + _("If you have contributed and are not on this list, \
please get in touch.")
    abouttext += '<p>' + _("A big thanks to all the people who have provided \
suggestions, bug reports and donations.")
    abt.label.setText(abouttext)
    dialog.adjustSize()
    dialog.show()
    dialog.exec_()

########NEW FILE########
__FILENAME__ = addcards
# Copyright: Damien Elmes <anki@ichi2.net>
# -*- coding: utf-8 -*-
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

from aqt.qt import *
import sys, re
import aqt.forms
import anki
from anki.errors import *
from anki.utils import stripHTML
from aqt.utils import saveGeom, restoreGeom, showWarning, askUser, shortcut, \
    tooltip, openHelp
from anki.sound import clearAudioQueue
from anki.hooks import addHook, remHook
from anki.utils import stripHTMLMedia, isMac
import aqt.editor, aqt.modelchooser, aqt.deckchooser

class AddCards(QDialog):

    def __init__(self, mw):
        QDialog.__init__(self, None, Qt.Window)
        self.mw = mw
        self.form = aqt.forms.addcards.Ui_Dialog()
        self.form.setupUi(self)
        self.setWindowTitle(_("Add"))
        self.setMinimumHeight(300)
        self.setMinimumWidth(400)
        self.setupChoosers()
        self.setupEditor()
        self.setupButtons()
        self.onReset()
        self.history = []
        self.forceClose = False
        restoreGeom(self, "add")
        addHook('reset', self.onReset)
        addHook('currentModelChanged', self.onReset)
        self.show()
        self.setupNewNote()

    def setupEditor(self):
        self.editor = aqt.editor.Editor(
            self.mw, self.form.fieldsArea, self, True)

    def setupChoosers(self):
        self.modelChooser = aqt.modelchooser.ModelChooser(
            self.mw, self.form.modelArea)
        self.deckChooser = aqt.deckchooser.DeckChooser(
            self.mw, self.form.deckArea)

    def helpRequested(self):
        openHelp("addingnotes")

    def setupButtons(self):
        bb = self.form.buttonBox
        ar = QDialogButtonBox.ActionRole
        # add
        self.addButton = bb.addButton(_("Add"), ar)
        self.addButton.setShortcut(QKeySequence("Ctrl+Return"))
        self.addButton.setToolTip(shortcut(_("Add (shortcut: ctrl+enter)")))
        self.connect(self.addButton, SIGNAL("clicked()"), self.addCards)
        # close
        self.closeButton = QPushButton(_("Close"))
        self.closeButton.setAutoDefault(False)
        bb.addButton(self.closeButton,
                                        QDialogButtonBox.RejectRole)
        # help
        self.helpButton = QPushButton(_("Help"))
        self.helpButton.setAutoDefault(False)
        bb.addButton(self.helpButton,
                                        QDialogButtonBox.HelpRole)
        self.connect(self.helpButton, SIGNAL("clicked()"), self.helpRequested)
        # history
        b = bb.addButton(
            _("History")+ u" ▾", ar)
        self.connect(b, SIGNAL("clicked()"), self.onHistory)
        b.setEnabled(False)
        self.historyButton = b

    def setupNewNote(self, set=True):
        f = self.mw.col.newNote()
        f.tags = f.model()['tags']
        if set:
            self.editor.setNote(f)
        return f

    def onReset(self, model=None, keep=False):
        oldNote = self.editor.note
        note = self.setupNewNote(set=False)
        flds = note.model()['flds']
        # copy fields from old note
        if oldNote:
            if not keep:
                self.removeTempNote(oldNote)
            for n in range(len(note.fields)):
                try:
                    if not keep or flds[n]['sticky']:
                        note.fields[n] = oldNote.fields[n]
                    else:
                        note.fields[n] = ""
                except IndexError:
                    break
        self.editor.currentField = 0
        self.editor.setNote(note)

    def removeTempNote(self, note):
        if not note or not note.id:
            return
        # we don't have to worry about cards; just the note
        self.mw.col._remNotes([note.id])

    def addHistory(self, note):
        txt = stripHTMLMedia(",".join(note.fields))[:30]
        self.history.insert(0, (note.id, txt))
        self.history = self.history[:15]
        self.historyButton.setEnabled(True)

    def onHistory(self):
        m = QMenu(self)
        for nid, txt in self.history:
            a = m.addAction(_("Edit %s") % txt)
            a.connect(a, SIGNAL("triggered()"),
                      lambda nid=nid: self.editHistory(nid))
        m.exec_(self.historyButton.mapToGlobal(QPoint(0,0)))

    def editHistory(self, nid):
        browser = aqt.dialogs.open("Browser", self.mw)
        browser.form.searchEdit.lineEdit().setText("nid:%d" % nid)
        browser.onSearch()

    def addNote(self, note):
        note.model()['did'] = self.deckChooser.selectedId()
        ret = note.dupeOrEmpty()
        if ret == 1:
            showWarning(_(
                "The first field is empty."),
                help="AddItems#AddError")
            return
        cards = self.mw.col.addNote(note)
        if not cards:
            showWarning(_("""\
The input you have provided would make an empty \
question on all cards."""), help="AddItems")
            return
        self.addHistory(note)
        self.mw.requireReset()
        return note

    def addCards(self):
        self.editor.saveNow()
        self.editor.saveAddModeVars()
        note = self.editor.note
        note = self.addNote(note)
        if not note:
            return
        tooltip(_("Added"), period=500)
        # stop anything playing
        clearAudioQueue()
        self.onReset(keep=True)
        self.mw.col.autosave()

    def keyPressEvent(self, evt):
        "Show answer on RET or register answer."
        if (evt.key() in (Qt.Key_Enter, Qt.Key_Return)
            and self.editor.tags.hasFocus()):
            evt.accept()
            return
        return QDialog.keyPressEvent(self, evt)

    def reject(self):
        if not self.canClose():
            return
        remHook('reset', self.onReset)
        remHook('currentModelChanged', self.onReset)
        clearAudioQueue()
        self.removeTempNote(self.editor.note)
        self.editor.setNote(None)
        self.modelChooser.cleanup()
        self.deckChooser.cleanup()
        self.mw.maybeReset()
        saveGeom(self, "add")
        aqt.dialogs.close("AddCards")
        QDialog.reject(self)

    def canClose(self):
        if (self.forceClose or self.editor.fieldsAreBlank() or
            askUser(_("Close and lose current input?"))):
            return True
        return False

########NEW FILE########
__FILENAME__ = addons
# Copyright: Damien Elmes <anki@ichi2.net>
# -*- coding: utf-8 -*-
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

import sys, os, re, traceback, time
from cStringIO import StringIO
from aqt.qt import *
from aqt.utils import showInfo, showWarning, openFolder, isWin, openLink, \
    askUser
from anki.hooks import runHook, addHook, remHook
from aqt.webview import AnkiWebView
from zipfile import ZipFile
import aqt.forms
import aqt
from anki.sync import httpCon
import aqt.sync # monkey-patches httplib2
from aqt.downloader import download

# in the future, it would be nice to save the addon id and unzippped file list
# to the config so that we can clear up all files and check for updates

class AddonManager(object):

    def __init__(self, mw):
        self.mw = mw
        f = self.mw.form; s = SIGNAL("triggered()")
        self.mw.connect(f.actionOpenPluginFolder, s, self.onOpenAddonFolder)
        self.mw.connect(f.actionDownloadSharedPlugin, s, self.onGetAddons)
        self._menus = []
        if isWin:
            self.clearAddonCache()
        sys.path.insert(0, self.addonsFolder())
        self.loadAddons()

    def files(self):
        return [f for f in os.listdir(self.addonsFolder())
                if f.endswith(".py")]

    def loadAddons(self):
        for file in self.files():
            try:
                __import__(file.replace(".py", ""))
            except:
                traceback.print_exc()
        self.rebuildAddonsMenu()

    # Menus
    ######################################################################

    def onOpenAddonFolder(self, path=None):
        if path is None:
            path = self.addonsFolder()
        openFolder(path)

    def rebuildAddonsMenu(self):
        for m in self._menus:
            self.mw.form.menuPlugins.removeAction(m.menuAction())
        for file in self.files():
            m = self.mw.form.menuPlugins.addMenu(
                os.path.splitext(file)[0])
            self._menus.append(m)
            a = QAction(_("Edit..."), self.mw)
            p = os.path.join(self.addonsFolder(), file)
            self.mw.connect(a, SIGNAL("triggered()"),
                            lambda p=p: self.onEdit(p))
            m.addAction(a)
            a = QAction(_("Delete..."), self.mw)
            self.mw.connect(a, SIGNAL("triggered()"),
                            lambda p=p: self.onRem(p))
            m.addAction(a)

    def onEdit(self, path):
        d = QDialog(self.mw)
        frm = aqt.forms.editaddon.Ui_Dialog()
        frm.setupUi(d)
        d.setWindowTitle(os.path.basename(path))
        frm.text.setPlainText(unicode(open(path).read(), "utf8"))
        d.connect(frm.buttonBox, SIGNAL("accepted()"),
                  lambda: self.onAcceptEdit(path, frm))
        d.exec_()

    def onAcceptEdit(self, path, frm):
        open(path, "w").write(frm.text.toPlainText().encode("utf8"))
        showInfo(_("Edits saved. Please restart Anki."))

    def onRem(self, path):
        if not askUser(_("Delete %s?") % os.path.basename(path)):
            return
        os.unlink(path)
        self.rebuildAddonsMenu()
        showInfo(_("Deleted. Please restart Anki."))

    # Tools
    ######################################################################

    def addonsFolder(self):
        dir = self.mw.pm.addonFolder()
        if isWin:
            dir = dir.encode(sys.getfilesystemencoding())
        return dir

    def clearAddonCache(self):
        "Clear .pyc files which may cause crashes if Python version updated."
        dir = self.addonsFolder()
        for curdir, dirs, files in os.walk(dir):
            for f in files:
                if not f.endswith(".pyc"):
                    continue
                os.unlink(os.path.join(curdir, f))

    def registerAddon(self, name, updateId):
        # not currently used
        return

    # Installing add-ons
    ######################################################################

    def onGetAddons(self):
        GetAddons(self.mw)

    def install(self, data, fname):
        if fname.endswith(".py"):
            # .py files go directly into the addon folder
            path = os.path.join(self.addonsFolder(), fname)
            open(path, "w").write(data)
            return
        # .zip file
        z = ZipFile(StringIO(data))
        base = self.addonsFolder()
        for n in z.namelist():
            if n.endswith("/"):
                # folder; ignore
                continue
            # write
            z.extract(n, base)

class GetAddons(QDialog):

    def __init__(self, mw):
        QDialog.__init__(self, mw)
        self.mw = mw
        self.form = aqt.forms.getaddons.Ui_Dialog()
        self.form.setupUi(self)
        b = self.form.buttonBox.addButton(
            _("Browse"), QDialogButtonBox.ActionRole)
        self.connect(b, SIGNAL("clicked()"), self.onBrowse)
        self.exec_()

    def onBrowse(self):
        openLink(aqt.appShared + "addons/")

    def accept(self):
        QDialog.accept(self)
        # create downloader thread
        ret = download(self.mw, self.form.code.text())
        if not ret:
            return
        data, fname = ret
        self.mw.addonManager.install(data, fname)
        self.mw.progress.finish()
        showInfo(_("Download successful. Please restart Anki."))

########NEW FILE########
__FILENAME__ = browser
# -*- coding: utf-8 -*-
# Copyright: Damien Elmes <anki@ichi2.net>
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

import sre_constants, cgi
from aqt.qt import *
import time, types, sys, re
from operator import attrgetter, itemgetter
import anki, anki.utils, aqt.forms
from anki.utils import fmtTimeSpan, ids2str, stripHTMLMedia, isWin, intTime, isMac
from aqt.utils import saveGeom, restoreGeom, saveSplitter, restoreSplitter, \
    saveHeader, restoreHeader, saveState, restoreState, applyStyles, getTag, \
    showInfo, askUser, tooltip, openHelp, showWarning, shortcut
from anki.errors import *
from anki.db import *
from anki.hooks import runHook, addHook, remHook
from aqt.webview import AnkiWebView
from aqt.toolbar import Toolbar
from anki.consts import *

COLOUR_SUSPENDED = "#FFFFB2"
COLOUR_MARKED = "#D9B2E9"

# fixme: need to refresh after undo

# Data model
##########################################################################

class DataModel(QAbstractTableModel):

    def __init__(self, browser):
        QAbstractTableModel.__init__(self)
        self.browser = browser
        self.col = browser.col
        self.sortKey = None
        self.activeCols = self.col.conf.get(
            "activeCols", ["noteFld", "template", "cardDue", "deck"])
        self.cards = []
        self.cardObjs = {}

    def getCard(self, index):
        id = self.cards[index.row()]
        if not id in self.cardObjs:
            self.cardObjs[id] = self.col.getCard(id)
        return self.cardObjs[id]

    def refreshNote(self, note):
        refresh = False
        for c in note.cards():
            if c.id in self.cardObjs:
                del self.cardObjs[c.id]
                refresh = True
        if refresh:
            self.emit(SIGNAL("layoutChanged()"))

    # Model interface
    ######################################################################

    def rowCount(self, index):
        return len(self.cards)

    def columnCount(self, index):
        return len(self.activeCols)

    def data(self, index, role):
        if not index.isValid():
            return
        if role == Qt.FontRole:
            return
        if role == Qt.TextAlignmentRole:
            align = Qt.AlignVCenter
            if self.activeCols[index.column()] not in ("question", "answer",
               "template", "deck", "noteFld", "note"):
                align |= Qt.AlignHCenter
            return align
        elif role == Qt.DisplayRole or role == Qt.EditRole:
            return self.columnData(index)
        else:
            return

    def headerData(self, section, orientation, role):
        if orientation == Qt.Vertical:
            return
        elif role == Qt.DisplayRole and section < len(self.activeCols):
            type = self.columnType(section)
            for stype, name in self.browser.columns:
                if type == stype:
                    txt = name
                    break
            return txt
        else:
            return

    def flags(self, index):
        return Qt.ItemFlag(Qt.ItemIsEnabled |
                           Qt.ItemIsSelectable)

    # Filtering
    ######################################################################

    def search(self, txt, reset=True):
        if reset:
            self.beginReset()
        t = time.time()
        # the db progress handler may cause a refresh, so we need to zero out
        # old data first
        self.cards = []
        self.cards = self.col.findCards(txt, order=True)
        #self.browser.mw.pm.profile['fullSearch'])
        #print "fetch cards in %dms" % ((time.time() - t)*1000)
        if reset:
            self.endReset()

    def reset(self):
        self.beginReset()
        self.endReset()

    def beginReset(self):
        self.browser.editor.saveNow()
        self.browser.editor.setNote(None, hide=False)
        self.browser.mw.progress.start()
        self.saveSelection()
        self.beginResetModel()
        self.cardObjs = {}

    def endReset(self):
        t = time.time()
        self.endResetModel()
        self.restoreSelection()
        self.browser.mw.progress.finish()

    def reverse(self):
        self.beginReset()
        self.cards.reverse()
        self.endReset()

    def saveSelection(self):
        cards = self.browser.selectedCards()
        self.selectedCards = dict([(id, True) for id in cards])
        if getattr(self.browser, 'card', None):
            self.focusedCard = self.browser.card.id
        else:
            self.focusedCard = None

    def restoreSelection(self):
        if not self.cards:
            return
        sm = self.browser.form.tableView.selectionModel()
        sm.clear()
        # restore selection
        items = QItemSelection()
        count = 0
        firstIdx = None
        focusedIdx = None
        for row, id in enumerate(self.cards):
            # if the id matches the focused card, note the index
            if self.focusedCard == id:
                focusedIdx = self.index(row, 0)
                items.select(focusedIdx, focusedIdx)
                self.focusedCard = None
            # if the card was previously selected, select again
            if id in self.selectedCards:
                count += 1
                idx = self.index(row, 0)
                items.select(idx, idx)
                # note down the first card of the selection, in case we don't
                # have a focused card
                if not firstIdx:
                    firstIdx = idx
        # focus previously focused or first in selection
        idx = focusedIdx or firstIdx
        tv = self.browser.form.tableView
        if idx:
            tv.selectRow(idx.row())
            tv.scrollTo(idx, tv.PositionAtCenter)
            if count < 500:
                # discard large selections; they're too slow
                sm.select(items, QItemSelectionModel.SelectCurrent |
                          QItemSelectionModel.Rows)
        else:
            tv.selectRow(0)

    # Column data
    ######################################################################

    def columnType(self, column):
        return self.activeCols[column]

    def columnData(self, index):
        row = index.row()
        col = index.column()
        type = self.columnType(col)
        c = self.getCard(index)
        if type == "question":
            return self.question(c)
        elif type == "answer":
            return self.answer(c)
        elif type == "noteFld":
            f = c.note()
            return self.formatQA(f.fields[self.col.models.sortIdx(f.model())])
        elif type == "template":
            t = c.template()['name']
            if c.model()['type'] == MODEL_CLOZE:
                t += " %d" % (c.ord+1)
            return t
        elif type == "cardDue":
            # catch invalid dates
            try:
                t = self.nextDue(c, index)
            except:
                t = ""
            if c.queue < 0:
                t = "(" + t + ")"
            return t
        elif type == "noteCrt":
            return time.strftime("%Y-%m-%d", time.localtime(c.note().id/1000))
        elif type == "noteMod":
            return time.strftime("%Y-%m-%d", time.localtime(c.note().mod))
        elif type == "cardMod":
            return time.strftime("%Y-%m-%d", time.localtime(c.mod))
        elif type == "cardReps":
            return str(c.reps)
        elif type == "cardLapses":
            return str(c.lapses)
        elif type == "note":
            return c.model()['name']
        elif type == "cardIvl":
            if c.type == 0:
                return _("(new)")
            elif c.type == 1:
                return _("(learning)")
            return fmtTimeSpan(c.ivl*86400)
        elif type == "cardEase":
            if c.type == 0:
                return _("(new)")
            return "%d%%" % (c.factor/10)
        elif type == "deck":
            if c.odid:
                # in a cram deck
                return "%s (%s)" % (
                    self.browser.mw.col.decks.name(c.did),
                    self.browser.mw.col.decks.name(c.odid))
            # normal deck
            return self.browser.mw.col.decks.name(c.did)

    def question(self, c):
        return self.formatQA(c.q(browser=True))

    def answer(self, c):
        if c.template().get('bafmt'):
            # they have provided a template, use it verbatim
            c.q(browser=True)
            return self.formatQA(c.a())
        # need to strip question from answer
        q = self.question(c)
        a = self.formatQA(c.a())
        if a.startswith(q):
            return a[len(q):].strip()
        return a

    def formatQA(self, txt):
        s = txt.replace("<br>", u" ")
        s = s.replace("<br />", u" ")
        s = s.replace("<div>", u" ")
        s = s.replace("\n", u" ")
        s = re.sub("\[sound:[^]]+\]", "", s)
        s = re.sub("\[\[type:[^]]+\]\]", "", s)
        s = stripHTMLMedia(s)
        s = s.strip()
        return s

    def nextDue(self, c, index):
        if c.odid:
            return _("(filtered)")
        elif c.queue == 1:
            date = c.due
        elif c.queue == 0 or c.type == 0:
            return str(c.due)
        elif c.queue in (2,3) or (c.type == 2 and c.queue < 0):
            date = time.time() + ((c.due - self.col.sched.today)*86400)
        else:
            return ""
        return time.strftime("%Y-%m-%d", time.localtime(date))

# Line painter
######################################################################

class StatusDelegate(QItemDelegate):

    def __init__(self, browser, model):
        QItemDelegate.__init__(self, browser)
        self.model = model

    def paint(self, painter, option, index):
        try:
            c = self.model.getCard(index)
        except:
            # in the the middle of a reset; return nothing so this row is not
            # rendered until we have a chance to reset the model
            return
        col = None
        if c.note().hasTag("Marked"):
            col = COLOUR_MARKED
        elif c.queue == -1:
            col = COLOUR_SUSPENDED
        if col:
            brush = QBrush(QColor(col))
            painter.save()
            painter.fillRect(option.rect, brush)
            painter.restore()
        return QItemDelegate.paint(self, painter, option, index)

# Browser window
######################################################################

# fixme: respond to reset+edit hooks

class Browser(QMainWindow):

    def __init__(self, mw):
        QMainWindow.__init__(self, None, Qt.Window)
        applyStyles(self)
        self.mw = mw
        self.col = self.mw.col
        self.lastFilter = ""
        self.form = aqt.forms.browser.Ui_Dialog()
        self.form.setupUi(self)
        restoreGeom(self, "editor", 0)
        restoreState(self, "editor")
        restoreSplitter(self.form.splitter_2, "editor2")
        restoreSplitter(self.form.splitter, "editor3")
        self.form.splitter_2.setChildrenCollapsible(False)
        self.form.splitter.setChildrenCollapsible(False)
        self.card = None
        self.setupToolbar()
        self.setupColumns()
        self.setupTable()
        self.setupMenus()
        self.setupSearch()
        self.setupTree()
        self.setupHeaders()
        self.setupHooks()
        self.setupEditor()
        self.updateFont()
        self.onUndoState(self.mw.form.actionUndo.isEnabled())
        self.form.searchEdit.setFocus()
        self.form.searchEdit.lineEdit().setText("is:current")
        self.form.searchEdit.lineEdit().selectAll()
        self.onSearch()
        self.show()

    def setupToolbar(self):
        self.toolbarWeb = AnkiWebView()
        self.toolbarWeb.setFixedHeight(32 + self.mw.fontHeightDelta)
        self.toolbar = BrowserToolbar(self.mw, self.toolbarWeb, self)
        self.form.verticalLayout_3.insertWidget(0, self.toolbarWeb)
        self.toolbar.draw()

    def setupMenus(self):
        # actions
        c = self.connect; f = self.form; s = SIGNAL("triggered()")
        c(f.actionReposition, s, self.reposition)
        c(f.actionReschedule, s, self.reschedule)
        c(f.actionCram, s, self.cram)
        c(f.actionChangeModel, s, self.onChangeModel)
        # edit
        c(f.actionUndo, s, self.mw.onUndo)
        c(f.actionInvertSelection, s, self.invertSelection)
        c(f.actionSelectNotes, s, self.selectNotes)
        c(f.actionFindReplace, s, self.onFindReplace)
        c(f.actionFindDuplicates, s, self.onFindDupes)
        # jumps
        c(f.actionPreviousCard, s, self.onPreviousCard)
        c(f.actionNextCard, s, self.onNextCard)
        c(f.actionFirstCard, s, self.onFirstCard)
        c(f.actionLastCard, s, self.onLastCard)
        c(f.actionFind, s, self.onFind)
        c(f.actionNote, s, self.onNote)
        c(f.actionTags, s, self.onTags)
        c(f.actionCardList, s, self.onCardList)
        # help
        c(f.actionGuide, s, self.onHelp)
        # keyboard shortcut for shift+home/end
        self.pgUpCut = QShortcut(QKeySequence("Shift+Home"), self)
        c(self.pgUpCut, SIGNAL("activated()"), self.onFirstCard)
        self.pgDownCut = QShortcut(QKeySequence("Shift+End"), self)
        c(self.pgDownCut, SIGNAL("activated()"), self.onLastCard)
        # card info
        self.infoCut = QShortcut(QKeySequence("Ctrl+Shift+I"), self)
        c(self.infoCut, SIGNAL("activated()"), self.showCardInfo)
        # set deck
        self.changeDeckCut = QShortcut(QKeySequence("Ctrl+D"), self)
        c(self.changeDeckCut, SIGNAL("activated()"), self.setDeck)
        # add/remove tags
        self.tagCut1 = QShortcut(QKeySequence("Ctrl+Shift+T"), self)
        c(self.tagCut1, SIGNAL("activated()"), self.addTags)
        self.tagCut2 = QShortcut(QKeySequence("Ctrl+Alt+T"), self)
        c(self.tagCut2, SIGNAL("activated()"), self.deleteTags)
        self.tagCut3 = QShortcut(QKeySequence("Ctrl+K"), self)
        c(self.tagCut3, SIGNAL("activated()"), self.onMark)
        # deletion
        self.delCut1 = QShortcut(QKeySequence("Delete"), self)
        self.delCut1.setAutoRepeat(False)
        c(self.delCut1, SIGNAL("activated()"), self.deleteNotes)
        if isMac:
            self.delCut2 = QShortcut(QKeySequence("Backspace"), self)
            self.delCut2.setAutoRepeat(False)
            c(self.delCut2, SIGNAL("activated()"), self.deleteNotes)
        # add-on hook
        runHook('browser.setupMenus', self)
        self.mw.maybeHideAccelerators(self)

    def updateFont(self):
        self.form.tableView.verticalHeader().setDefaultSectionSize(
            max(16, self.mw.fontHeight * 1.4))

    def closeEvent(self, evt):
        saveSplitter(self.form.splitter_2, "editor2")
        saveSplitter(self.form.splitter, "editor3")
        self.editor.saveNow()
        self.editor.setNote(None)
        saveGeom(self, "editor")
        saveState(self, "editor")
        saveHeader(self.form.tableView.horizontalHeader(), "editor")
        self.col.conf['activeCols'] = self.model.activeCols
        self.col.setMod()
        self.hide()
        aqt.dialogs.close("Browser")
        self.teardownHooks()
        self.mw.maybeReset()
        evt.accept()

    def keyPressEvent(self, evt):
        "Show answer on RET or register answer."
        if evt.key() == Qt.Key_Escape:
            self.close()
        elif self.mw.app.focusWidget() == self.form.tree:
            if evt.key() in (Qt.Key_Return, Qt.Key_Enter):
                item = self.form.tree.currentItem()
                self.onTreeClick(item, 0)

    def setupColumns(self):
        self.columns = [
            ('question', _("Front")),
            ('answer', _("Back")),
            ('template', _("Card")),
            ('deck', _("Deck")),
            ('noteFld', _("Sort Field")),
            ('noteCrt', _("Created")),
            ('noteMod', _("Edited")),
            ('cardMod', _("Changed")),
            ('cardDue', _("Due")),
            ('cardIvl', _("Interval")),
            ('cardEase', _("Ease")),
            ('cardReps', _("Reviews")),
            ('cardLapses', _("Lapses")),
            ('note', _("Note")),
        ]
        self.columns.sort(key=itemgetter(1))

    # Searching
    ######################################################################

    def setupSearch(self):
        self.filterTimer = None
        self.connect(self.form.searchButton,
                     SIGNAL("clicked()"),
                     self.onSearch)
        self.connect(self.form.searchEdit.lineEdit(),
                     SIGNAL("returnPressed()"),
                     self.onSearch)
        self.setTabOrder(self.form.searchEdit, self.form.tableView)
        self.form.searchEdit.setCompleter(None)
        self.form.searchEdit.addItems(self.mw.pm.profile['searchHistory'])

    def onSearch(self, reset=True):
        "Careful: if reset is true, the current note is saved."
        txt = unicode(self.form.searchEdit.lineEdit().text()).strip()
        prompt = _("<type here to search; hit enter to show current deck>")
        sh = self.mw.pm.profile['searchHistory']
        # update search history
        if txt in sh:
            sh.remove(txt)
        sh.insert(0, txt)
        sh = sh[:30]
        self.form.searchEdit.clear()
        self.form.searchEdit.addItems(sh)
        self.mw.pm.profile['searchHistory'] = sh
        if self.mw.state == "review" and "is:current" in txt:
            # search for current card, but set search to easily display whole
            # deck
            if reset:
                self.model.beginReset()
                self.model.focusedCard = self.mw.reviewer.card.id
            self.model.search("nid:%d"%self.mw.reviewer.card.nid, False)
            if reset:
                self.model.endReset()
            self.form.searchEdit.lineEdit().setText(prompt)
            self.form.searchEdit.lineEdit().selectAll()
            return
        elif "is:current" in txt:
            self.form.searchEdit.lineEdit().setText(prompt)
            self.form.searchEdit.lineEdit().selectAll()
        elif txt == prompt:
            self.form.searchEdit.lineEdit().setText("deck:current ")
            txt = "deck:current "
        self.model.search(txt, reset)
        if not self.model.cards:
            # no row change will fire
            self.onRowChanged(None, None)
        elif self.mw.state == "review":
            self.focusCid(self.mw.reviewer.card.id)

    def updateTitle(self):
        selected = len(self.form.tableView.selectionModel().selectedRows())
        cur = len(self.model.cards)
        self.setWindowTitle(ngettext("Browser (%(cur)d card shown; %(sel)s)",
                                     "Browser (%(cur)d cards shown; %(sel)s)",
                                 cur) % {
            "cur": cur,
            "sel": ngettext("%d selected", "%d selected", selected) % selected
            })
        return selected

    def onReset(self):
        self.editor.setNote(None)
        self.onSearch()

    # Table view & editor
    ######################################################################

    def setupTable(self):
        self.model = DataModel(self)
        self.form.tableView.setSortingEnabled(True)
        self.form.tableView.setModel(self.model)
        self.form.tableView.selectionModel()
        self.form.tableView.setItemDelegate(StatusDelegate(self, self.model))
        self.connect(self.form.tableView.selectionModel(),
                     SIGNAL("selectionChanged(QItemSelection,QItemSelection)"),
                     self.onRowChanged)

    def setupEditor(self):
        self.editor = aqt.editor.Editor(
            self.mw, self.form.fieldsArea, self)
        self.editor.stealFocus = False

    def onRowChanged(self, current, previous):
        "Update current note and hide/show editor."
        update = self.updateTitle()
        show = self.model.cards and update == 1
        self.form.splitter.widget(1).setShown(not not show)
        if not show:
            self.editor.setNote(None)
        else:
            self.card = self.model.getCard(
                self.form.tableView.selectionModel().currentIndex())
            self.editor.setNote(self.card.note(reload=True))
            self.editor.card = self.card
        self.toolbar.draw()

    def refreshCurrentCard(self, note):
        self.model.refreshNote(note)

    def refreshCurrentCardFilter(self, flag, note, fidx):
        self.refreshCurrentCard(note)
        return flag

    # Headers & sorting
    ######################################################################

    def setupHeaders(self):
        vh = self.form.tableView.verticalHeader()
        hh = self.form.tableView.horizontalHeader()
        if not isWin:
            vh.hide()
            hh.show()
        restoreHeader(hh, "editor")
        hh.setHighlightSections(False)
        hh.setMinimumSectionSize(50)
        hh.setMovable(True)
        self.setColumnSizes()
        hh.setContextMenuPolicy(Qt.CustomContextMenu)
        hh.connect(hh, SIGNAL("customContextMenuRequested(QPoint)"),
                   self.onHeaderContext)
        self.setSortIndicator()
        hh.connect(hh, SIGNAL("sortIndicatorChanged(int, Qt::SortOrder)"),
                   self.onSortChanged)
        hh.connect(hh, SIGNAL("sectionMoved(int,int,int)"),
                   self.onColumnMoved)

    def onSortChanged(self, idx, ord):
        type = self.model.activeCols[idx]
        noSort = ("question", "answer", "template", "deck", "note")
        if type in noSort:
            if type == "template":
                showInfo(_("""\
This column can't be sorted on, but you can search for individual card types,
such as 'card:Card 1'."""))
            elif type == "deck":
                showInfo(_("""\
This column can't be sorted on, but you can search for specific decks
by clicking on one on the left."""))
            else:
                showInfo(_("Sorting on this column is not supported. Please "
                           "choose another."))
            type = self.col.conf['sortType']
        if self.col.conf['sortType'] != type:
            self.col.conf['sortType'] = type
            # default to descending for non-text fields
            if type == "noteFld":
                ord = not ord
            self.col.conf['sortBackwards'] = ord
            self.onSearch()
        else:
            if self.col.conf['sortBackwards'] != ord:
                self.col.conf['sortBackwards'] = ord
                self.model.reverse()
        self.setSortIndicator()

    def setSortIndicator(self):
        hh = self.form.tableView.horizontalHeader()
        type = self.col.conf['sortType']
        if type not in self.model.activeCols:
            hh.setSortIndicatorShown(False)
            return
        idx = self.model.activeCols.index(type)
        if self.col.conf['sortBackwards']:
            ord = Qt.DescendingOrder
        else:
            ord = Qt.AscendingOrder
        hh.blockSignals(True)
        hh.setSortIndicator(idx, ord)
        hh.blockSignals(False)
        hh.setSortIndicatorShown(True)

    def onHeaderContext(self, pos):
        gpos = self.form.tableView.mapToGlobal(pos)
        m = QMenu()
        for type, name in self.columns:
            a = m.addAction(name)
            a.setCheckable(True)
            a.setChecked(type in self.model.activeCols)
            a.connect(a, SIGNAL("toggled(bool)"),
                      lambda b, t=type: self.toggleField(t))
        m.exec_(gpos)

    def toggleField(self, type):
        self.model.beginReset()
        if type in self.model.activeCols:
            if len(self.model.activeCols) < 2:
                return showInfo(_("You must have at least one column."))
            self.model.activeCols.remove(type)
        else:
            self.model.activeCols.append(type)
        # sorted field may have been hidden
        self.setSortIndicator()
        self.setColumnSizes()
        self.model.endReset()

    def setColumnSizes(self):
        hh = self.form.tableView.horizontalHeader()
        for i in range(len(self.model.activeCols)):
            if hh.visualIndex(i) == len(self.model.activeCols) - 1:
                hh.setResizeMode(i, QHeaderView.Stretch)
            else:
                hh.setResizeMode(i, QHeaderView.Interactive)

    def onColumnMoved(self, a, b, c):
        self.setColumnSizes()

    # Filter tree
    ######################################################################

    class CallbackItem(QTreeWidgetItem):
        def __init__(self, name, onclick):
            QTreeWidgetItem.__init__(self, [name])
            self.onclick = onclick

    def setupTree(self):
        self.connect(
            self.form.tree, SIGNAL("itemClicked(QTreeWidgetItem*,int)"),
            self.onTreeClick)
        p = QPalette()
        p.setColor(QPalette.Base, QColor("#d6dde0"))
        self.form.tree.setPalette(p)
        self.buildTree()

    def buildTree(self):
        self.form.tree.clear()
        root = self.form.tree.invisibleRootItem()
        self._systemTagTree(root)
        self._decksTree(root)
        self._modelTree(root)
        self._userTagTree(root)
        self.form.tree.expandAll()
        self.form.tree.setItemsExpandable(False)
        self.form.tree.setIndentation(15)

    def onTreeClick(self, item, col):
        if getattr(item, 'onclick', None):
            item.onclick()

    def setFilter(self, *args):
        if len(args) == 1:
            txt = args[0]
        else:
            txt = ""
            items = []
            for c, a in enumerate(args):
                if c % 2 == 0:
                    txt += a + ":"
                else:
                    txt += a
                    if " " in txt or "(" in txt or ")" in txt:
                        txt = "'%s'" % txt
                    items.append(txt)
                    txt = ""
            txt = " ".join(items)
        if self.mw.app.keyboardModifiers() & Qt.AltModifier:
            txt = "-"+txt
        if self.mw.app.keyboardModifiers() & Qt.ControlModifier:
            cur = unicode(self.form.searchEdit.lineEdit().text())
            if cur:
                txt = cur + " " + txt
        self.form.searchEdit.lineEdit().setText(txt)
        self.onSearch()

    def _systemTagTree(self, root):
        tags = (
            (_("Whole Collection"), "ankibw", ""),
            (_("Current Deck"), "deck16", "deck:current"),
            (_("Added Today"), "view-pim-calendar.png", "added:1"),
            (_("Studied Today"), "view-pim-calendar.png", "rated:1"),
            (_("Again Today"), "view-pim-calendar.png", "rated:1:1"),
            (_("New"), "plus16.png", "is:new"),
            (_("Learning"), "stock_new_template_red.png", "is:learn"),
            (_("Review"), "clock16.png", "is:review"),
            (_("Due"), "clock16.png", "is:due"),
            (_("Marked"), "star16.png", "tag:marked"),
            (_("Suspended"), "media-playback-pause.png", "is:suspended"),
            (_("Leech"), "emblem-important.png", "tag:leech"))
        for name, icon, cmd in tags:
            item = self.CallbackItem(
                name, lambda c=cmd: self.setFilter(c))
            item.setIcon(0, QIcon(":/icons/" + icon))
            root.addChild(item)
        return root

    def _userTagTree(self, root):
        for t in sorted(self.col.tags.all()):
            if t.lower() == "marked":
                continue
            item = self.CallbackItem(
                t, lambda t=t: self.setFilter("tag", t))
            item.setIcon(0, QIcon(":/icons/anki-tag.png"))
            root.addChild(item)

    def _decksTree(self, root):
        grps = self.col.sched.deckDueTree()
        def fillGroups(root, grps, head=""):
            for g in grps:
                item = self.CallbackItem(
                g[0], lambda g=g: self.setFilter(
                    "deck", head+g[0]))
                item.setIcon(0, QIcon(":/icons/deck16.png"))
                root.addChild(item)
                newhead = head + g[0]+"::"
                fillGroups(item, g[5], newhead)
        fillGroups(root, grps)

    def _modelTree(self, root):
        for m in sorted(self.col.models.all(), key=itemgetter("name")):
            mitem = self.CallbackItem(
                m['name'], lambda m=m: self.setFilter("note", m['name']))
            mitem.setIcon(0, QIcon(":/icons/product_design.png"))
            root.addChild(mitem)
            # for t in m['tmpls']:
            #     titem = self.CallbackItem(
            #     t['name'], lambda m=m, t=t: self.setFilter(
            #         "model", m['name'], "card", t['name']))
            #     titem.setIcon(0, QIcon(":/icons/stock_new_template.png"))
            #     mitem.addChild(titem)

    # Info
    ######################################################################

    def showCardInfo(self):
        if not self.card:
            return
        info, cs = self._cardInfoData()
        reps = self._revlogData(cs)
        d = QDialog(self)
        l = QVBoxLayout()
        l.setMargin(0)
        w = AnkiWebView()
        l.addWidget(w)
        w.stdHtml(info + "<p>" + reps)
        bb = QDialogButtonBox(QDialogButtonBox.Close)
        l.addWidget(bb)
        bb.connect(bb, SIGNAL("rejected()"), d, SLOT("reject()"))
        d.setLayout(l)
        d.setWindowModality(Qt.WindowModal)
        d.resize(500, 400)
        restoreGeom(d, "revlog")
        d.exec_()
        saveGeom(d, "revlog")

    def _cardInfoData(self):
        from anki.stats import CardStats
        cs = CardStats(self.col, self.card)
        rep = cs.report()
        m = self.card.model()
        rep = """
<div style='width: 400px; margin: 0 auto 0;
border: 1px solid #000; padding: 3px; '>%s</div>""" % rep
        return rep, cs

    def onRevlog(self):
        data = self._revlogData()
        d = QDialog(self)
        l = QVBoxLayout()
        l.setMargin(0)
        w = AnkiWebView()
        l.addWidget(w)
        w.stdHtml(data)
        bb = QDialogButtonBox(QDialogButtonBox.Close)
        l.addWidget(bb)
        bb.connect(bb, SIGNAL("rejected()"), d, SLOT("reject()"))
        d.setLayout(l)
        d.setWindowModality(Qt.WindowModal)
        d.resize(500, 400)
        restoreGeom(d, "revlog")
        d.exec_()
        saveGeom(d, "revlog")

    def _revlogData(self, cs):
        entries = self.mw.col.db.all(
            "select id/1000.0, ease, ivl, factor, time/1000.0, type "
            "from revlog where cid = ?", self.card.id)
        if not entries:
            return ""
        s = "<table width=100%%><tr><th align=left>%s</th>" % _("Date")
        s += ("<th align=right>%s</th>" * 5) % (
            _("Type"), _("Rating"), _("Interval"), _("Ease"), _("Time"))
        cnt = 0
        for (date, ease, ivl, factor, taken, type) in reversed(entries):
            cnt += 1
            s += "<tr><td>%s</td>" % time.strftime(_("<b>%Y-%m-%d</b> @ %H:%M"),
                                                   time.localtime(date))
            tstr = [_("Learn"), _("Review"), _("Relearn"), _("Filtered"),
                    _("Resched")][type]
            import anki.stats as st
            fmt = "<span style='color:%s'>%s</span>"
            if type == 0:
                tstr = fmt % (st.colLearn, tstr)
            elif type == 1:
                tstr = fmt % (st.colMature, tstr)
            elif type == 2:
                tstr = fmt % (st.colRelearn, tstr)
            elif type == 3:
                tstr = fmt % (st.colCram, tstr)
            else:
                tstr = fmt % ("#000", tstr)
            if ease == 1:
                ease = fmt % (st.colRelearn, ease)
            if ivl == 0:
                ivl = _("0d")
            elif ivl > 0:
                ivl = fmtTimeSpan(ivl*86400, short=True)
            else:
                ivl = cs.time(-ivl)
            s += ("<td align=right>%s</td>" * 5) % (
                tstr,
                ease, ivl,
                "%d%%" % (factor/10) if factor else "",
                cs.time(taken)) + "</tr>"
        s += "</table>"
        if cnt < self.card.reps:
            s += _("""\
Note: Some of the history is missing. For more information, \
please see the browser documentation.""")
        return s

    # Menu helpers
    ######################################################################

    def selectedCards(self):
        return [self.model.cards[idx.row()] for idx in
                self.form.tableView.selectionModel().selectedRows()]

    def selectedNotes(self):
        return self.col.db.list("""
select distinct nid from cards
where id in %s""" % ids2str(
    [self.model.cards[idx.row()] for idx in
    self.form.tableView.selectionModel().selectedRows()]))

    def selectedNotesAsCards(self):
        return self.col.db.list(
            "select id from cards where nid in (%s)" %
            ",".join([str(s) for s in self.selectedNotes()]))

    def oneModelNotes(self):
        sf = self.selectedNotes()
        if not sf:
            return
        mods = self.col.db.scalar("""
select count(distinct mid) from notes
where id in %s""" % ids2str(sf))
        if mods > 1:
            showInfo(_("Please select cards from only one note type."))
            return
        return sf

    def onHelp(self):
        openHelp("browser")

    # Misc menu options
    ######################################################################

    def onChangeModel(self):
        nids = self.oneModelNotes()
        if nids:
            ChangeModel(self, nids)

    def cram(self):
        return showInfo("not yet implemented")
        self.close()
        self.mw.onCram(self.selectedCards())

    # Card deletion
    ######################################################################

    def deleteNotes(self):
        nids = self.selectedNotes()
        if not nids:
            return
        self.mw.checkpoint(_("Delete Notes"))
        self.model.beginReset()
        oldRow = self.form.tableView.selectionModel().currentIndex().row()
        self.col.remNotes(nids)
        self.onSearch(reset=False)
        if len(self.model.cards):
            new = min(oldRow, len(self.model.cards) - 1)
            self.model.focusedCard = self.model.cards[new]
        self.model.endReset()
        self.mw.requireReset()
        tooltip(_("%s deleted.") % (ngettext("%d note", "%d notes", len(nids)) % len(nids)))

    # Deck change
    ######################################################################

    def setDeck(self):
        from aqt.studydeck import StudyDeck
        ret = StudyDeck(
            self.mw, current=None, accept=_("Move Cards"),
            title=_("Change Deck"), help="browse", parent=self)
        if not ret.name:
            return
        did = self.col.decks.id(ret.name)
        deck = self.col.decks.get(did)
        if deck['dyn']:
            showWarning(_("Cards can't be manually moved into a filtered deck."))
            return
        self.model.beginReset()
        self.mw.checkpoint(_("Change Deck"))
        mod = intTime()
        usn = self.col.usn()
        # normal cards
        cids = self.selectedCards()
        scids = ids2str(cids)
        # remove any cards from filtered deck first
        self.col.sched.remFromDyn(cids)
        # then move into new deck
        self.col.db.execute("""
update cards set usn=?, mod=?, did=? where id in """ + scids,
                            usn, mod, did)
        self.onSearch(reset=False)
        self.mw.requireReset()
        self.model.endReset()

    # Tags
    ######################################################################

    def addTags(self, tags=None, label=None, prompt=None, func=None):
        if prompt is None:
            prompt = _("Enter tags to add:")
        if tags is None:
            (tags, r) = getTag(self, self.col, prompt)
        else:
            r = True
        if not r:
            return
        if func is None:
            func = self.col.tags.bulkAdd
        if label is None:
            label = _("Add Tags")
        if label:
            self.mw.checkpoint(label)
        self.model.beginReset()
        func(self.selectedNotes(), tags)
        self.model.endReset()
        self.mw.requireReset()

    def deleteTags(self, tags=None, label=None):
        if label is None:
            label = _("Delete Tags")
        self.addTags(tags, label, _("Enter tags to delete:"),
                     func=self.col.tags.bulkRem)

    # Suspending and marking
    ######################################################################

    def isSuspended(self):
        return not not (self.card and self.card.queue == -1)

    def onSuspend(self, sus=None):
        if sus is None:
            sus = not self.isSuspended()
        # focus lost hook may not have chance to fire
        self.editor.saveNow()
        c = self.selectedCards()
        if sus:
            self.col.sched.suspendCards(c)
        else:
            self.col.sched.unsuspendCards(c)
        self.model.reset()
        self.mw.requireReset()

    def isMarked(self):
        return not not (self.card and self.card.note().hasTag("Marked"))

    def onMark(self, mark=None):
        if mark is None:
            mark = not self.isMarked()
        if mark:
            self.addTags(tags="marked", label=False)
        else:
            self.deleteTags(tags="marked", label=False)

    # Repositioning
    ######################################################################

    def reposition(self):
        cids = self.selectedCards()
        cids2 = self.col.db.list(
            "select id from cards where type = 0 and id in " + ids2str(cids))
        if not cids2:
            return showInfo(_("Only new cards can be repositioned."))
        d = QDialog(self)
        d.setWindowModality(Qt.WindowModal)
        frm = aqt.forms.reposition.Ui_Dialog()
        frm.setupUi(d)
        (pmin, pmax) = self.col.db.first(
            "select min(due), max(due) from cards where type=0")
        txt = _("Queue top: %d") % pmin
        txt += "\n" + _("Queue bottom: %d") % pmax
        frm.label.setText(txt)
        if not d.exec_():
            return
        self.model.beginReset()
        self.mw.checkpoint(_("Reposition"))
        self.col.sched.sortCards(
            cids, start=frm.start.value(), step=frm.step.value(),
            shuffle=frm.randomize.isChecked(), shift=frm.shift.isChecked())
        self.onSearch(reset=False)
        self.mw.requireReset()
        self.model.endReset()

    # Rescheduling
    ######################################################################

    def reschedule(self):
        d = QDialog(self)
        d.setWindowModality(Qt.WindowModal)
        frm = aqt.forms.reschedule.Ui_Dialog()
        frm.setupUi(d)
        if not d.exec_():
            return
        self.model.beginReset()
        self.mw.checkpoint(_("Reschedule"))
        if frm.asNew.isChecked():
            self.col.sched.forgetCards(self.selectedCards())
        else:
            self.col.sched.reschedCards(
                self.selectedCards(), frm.min.value(), frm.max.value())
        self.onSearch(reset=False)
        self.mw.requireReset()
        self.model.endReset()

    # Edit: selection
    ######################################################################

    def selectNotes(self):
        nids = self.selectedNotes()
        self.form.searchEdit.lineEdit().setText("nid:"+",".join([str(x) for x in nids]))
        # clear the selection so we don't waste energy preserving it
        tv = self.form.tableView
        tv.selectionModel().clear()
        self.onSearch()
        tv.selectAll()

    def invertSelection(self):
        sm = self.form.tableView.selectionModel()
        items = sm.selection()
        self.form.tableView.selectAll()
        sm.select(items, QItemSelectionModel.Deselect | QItemSelectionModel.Rows)

    # Edit: undo
    ######################################################################

    def setupHooks(self):
        addHook("undoState", self.onUndoState)
        addHook("reset", self.onReset)
        addHook("editTimer", self.refreshCurrentCard)
        addHook("editFocusLost", self.refreshCurrentCardFilter)
        for t in "newTag", "newModel", "newDeck":
            addHook(t, self.buildTree)

    def teardownHooks(self):
        remHook("reset", self.onReset)
        remHook("editTimer", self.refreshCurrentCard)
        remHook("editFocusLost", self.refreshCurrentCard)
        remHook("undoState", self.onUndoState)
        for t in "newTag", "newModel", "newDeck":
            remHook(t, self.buildTree)

    def onUndoState(self, on):
        self.form.actionUndo.setEnabled(on)
        if on:
            self.form.actionUndo.setText(self.mw.form.actionUndo.text())

    # Edit: replacing
    ######################################################################

    def onFindReplace(self):
        sf = self.selectedNotes()
        if not sf:
            return
        import anki.find
        fields = sorted(anki.find.fieldNames(self.col, downcase=False))
        d = QDialog(self)
        frm = aqt.forms.findreplace.Ui_Dialog()
        frm.setupUi(d)
        d.setWindowModality(Qt.WindowModal)
        frm.field.addItems([_("All Fields")] + fields)
        self.connect(frm.buttonBox, SIGNAL("helpRequested()"),
                     self.onFindReplaceHelp)
        if not d.exec_():
            return
        if frm.field.currentIndex() == 0:
            field = None
        else:
            field = fields[frm.field.currentIndex()-1]
        self.mw.checkpoint(_("Find and Replace"))
        self.mw.progress.start()
        self.model.beginReset()
        try:
            changed = self.col.findReplace(sf,
                                            unicode(frm.find.text()),
                                            unicode(frm.replace.text()),
                                            frm.re.isChecked(),
                                            field,
                                            frm.ignoreCase.isChecked())
        except sre_constants.error:
            showInfo(_("Invalid regular expression."), parent=self)
            return
        else:
            self.onSearch()
            self.mw.requireReset()
        finally:
            self.model.endReset()
            self.mw.progress.finish()
        showInfo(ngettext(
            "%(a)d of %(b)d note updated",
            "%(a)d of %(b)d notes updated", len(sf)) % {
                'a': changed,
                'b': len(sf),
            })

    def onFindReplaceHelp(self):
        openHelp("findreplace")

    # Edit: finding dupes
    ######################################################################

    def onFindDupes(self):
        d = QDialog(self)
        frm = aqt.forms.finddupes.Ui_Dialog()
        frm.setupUi(d)
        restoreGeom(d, "findDupes")
        fields = sorted(anki.find.fieldNames(self.col, downcase=False))
        frm.fields.addItems(fields)
        # links
        frm.webView.page().setLinkDelegationPolicy(
            QWebPage.DelegateAllLinks)
        self.connect(frm.webView,
                     SIGNAL("linkClicked(QUrl)"),
                     self.dupeLinkClicked)
        def onFin(code):
            saveGeom(d, "findDupes")
        self.connect(d, SIGNAL("finished(int)"), onFin)
        def onClick():
            field = fields[frm.fields.currentIndex()]
            self.duplicatesReport(frm.webView, field, frm.search.text())
        search = frm.buttonBox.addButton(
            _("Search"), QDialogButtonBox.ActionRole)
        self.connect(search, SIGNAL("clicked()"), onClick)
        d.show()

    def duplicatesReport(self, web, fname, search):
        self.mw.progress.start()
        res = self.mw.col.findDupes(fname, search)
        t = "<html><body>"
        groups = len(res)
        notes = sum(len(r[1]) for r in res)
        part1 = ngettext("%d group", "%d groups", groups) % groups
        part2 = ngettext("%d note", "%d notes", notes) % notes
        t += _("Found %(a)s across %(b)s.") % dict(a=part1, b=part2)
        t += "<p><ol>"
        for val, nids in res:
            t += '<li><a href="%s">%s</a>: %s</a>' % (
                "nid:" + ",".join(str(id) for id in nids),
                ngettext("%d note", "%d notes", len(nids)) % len(nids),
                cgi.escape(val))
        t += "</ol>"
        t += "</body></html>"
        web.setHtml(t)
        self.mw.progress.finish()

    def dupeLinkClicked(self, link):
        self.form.searchEdit.lineEdit().setText(link.toString())
        self.onSearch()
        self.onNote()

    # Jumping
    ######################################################################

    def _moveCur(self, dir=None, idx=None):
        if not self.model.cards:
            return
        self.editor.saveNow()
        tv = self.form.tableView
        if idx is None:
            idx = tv.moveCursor(dir, self.mw.app.keyboardModifiers())
        tv.selectionModel().clear()
        tv.setCurrentIndex(idx)

    def onPreviousCard(self):
        f = self.editor.currentField
        self._moveCur(QAbstractItemView.MoveUp)
        self.editor.web.setFocus()
        self.editor.web.eval("focusField(%d)" % f)

    def onNextCard(self):
        f = self.editor.currentField
        self._moveCur(QAbstractItemView.MoveDown)
        self.editor.web.setFocus()
        self.editor.web.eval("focusField(%d)" % f)

    def onFirstCard(self):
        sm = self.form.tableView.selectionModel()
        idx = sm.currentIndex()
        self._moveCur(None, self.model.index(0, 0))
        if not self.mw.app.keyboardModifiers() & Qt.ShiftModifier:
            return
        idx2 = sm.currentIndex()
        item = QItemSelection(idx2, idx)
        sm.select(item, QItemSelectionModel.SelectCurrent|
                  QItemSelectionModel.Rows)

    def onLastCard(self):
        sm = self.form.tableView.selectionModel()
        idx = sm.currentIndex()
        self._moveCur(
            None, self.model.index(len(self.model.cards) - 1, 0))
        if not self.mw.app.keyboardModifiers() & Qt.ShiftModifier:
            return
        idx2 = sm.currentIndex()
        item = QItemSelection(idx, idx2)
        sm.select(item, QItemSelectionModel.SelectCurrent|
                  QItemSelectionModel.Rows)

    def onFind(self):
        self.form.searchEdit.setFocus()
        self.form.searchEdit.lineEdit().selectAll()

    def onNote(self):
        self.editor.focus()

    def onTags(self):
        self.form.tree.setFocus()

    def onCardList(self):
        self.form.tableView.setFocus()

    def focusCid(self, cid):
        try:
            row = self.model.cards.index(cid)
        except:
            return
        self.form.tableView.selectRow(row)

# Change model dialog
######################################################################

class ChangeModel(QDialog):

    def __init__(self, browser, nids):
        QDialog.__init__(self, browser)
        self.browser = browser
        self.nids = nids
        self.oldModel = browser.card.note().model()
        self.form = aqt.forms.changemodel.Ui_Dialog()
        self.form.setupUi(self)
        self.setWindowModality(Qt.WindowModal)
        self.setup()
        restoreGeom(self, "changeModel")
        addHook("reset", self.onReset)
        addHook("currentModelChanged", self.onReset)
        self.exec_()

    def setup(self):
        # maps
        self.flayout = QHBoxLayout()
        self.flayout.setMargin(0)
        self.fwidg = None
        self.form.fieldMap.setLayout(self.flayout)
        self.tlayout = QHBoxLayout()
        self.tlayout.setMargin(0)
        self.twidg = None
        self.form.templateMap.setLayout(self.tlayout)
        if self.style().objectName() == "gtk+":
            # gtk+ requires margins in inner layout
            self.form.verticalLayout_2.setContentsMargins(0, 11, 0, 0)
            self.form.verticalLayout_3.setContentsMargins(0, 11, 0, 0)
        # model chooser
        import aqt.modelchooser
        self.oldModel = self.browser.col.models.get(
            self.browser.col.db.scalar(
                "select mid from notes where id = ?", self.nids[0]))
        self.form.oldModelLabel.setText(self.oldModel['name'])
        self.modelChooser = aqt.modelchooser.ModelChooser(
            self.browser.mw, self.form.modelChooserWidget, label=False)
        self.modelChooser.models.setFocus()
        self.connect(self.form.buttonBox, SIGNAL("helpRequested()"),
                     self.onHelp)
        self.modelChanged(self.browser.mw.col.models.current())
        self.pauseUpdate = False

    def onReset(self):
        self.modelChanged(self.browser.col.models.current())

    def modelChanged(self, model):
        self.targetModel = model
        self.rebuildTemplateMap()
        self.rebuildFieldMap()

    def rebuildTemplateMap(self, key=None, attr=None):
        if not key:
            key = "t"
            attr = "tmpls"
        map = getattr(self, key + "widg")
        lay = getattr(self, key + "layout")
        src = self.oldModel[attr]
        dst = self.targetModel[attr]
        if map:
            lay.removeWidget(map)
            map.deleteLater()
            setattr(self, key + "MapWidget", None)
        map = QWidget()
        l = QGridLayout()
        combos = []
        targets = [x['name'] for x in dst] + [_("Nothing")]
        indices = {}
        for i, x in enumerate(src):
            l.addWidget(QLabel(_("Change %s to:") % x['name']), i, 0)
            cb = QComboBox()
            cb.addItems(targets)
            idx = min(i, len(targets)-1)
            cb.setCurrentIndex(idx)
            indices[cb] = idx
            self.connect(cb, SIGNAL("currentIndexChanged(int)"),
                         lambda i, cb=cb, key=key: self.onComboChanged(i, cb, key))
            combos.append(cb)
            l.addWidget(cb, i, 1)
        map.setLayout(l)
        lay.addWidget(map)
        setattr(self, key + "widg", map)
        setattr(self, key + "layout", lay)
        setattr(self, key + "combos", combos)
        setattr(self, key + "indices", indices)

    def rebuildFieldMap(self):
        return self.rebuildTemplateMap(key="f", attr="flds")

    def onComboChanged(self, i, cb, key):
        indices = getattr(self, key + "indices")
        if self.pauseUpdate:
            indices[cb] = i
            return
        combos = getattr(self, key + "combos")
        if i == cb.count() - 1:
            # set to 'nothing'
            return
        # find another combo with same index
        for c in combos:
            if c == cb:
                continue
            if c.currentIndex() == i:
                self.pauseUpdate = True
                c.setCurrentIndex(indices[cb])
                self.pauseUpdate = False
                break
        indices[cb] = i

    def getTemplateMap(self, old=None, combos=None, new=None):
        if not old:
            old = self.oldModel['tmpls']
            combos = self.tcombos
            new = self.targetModel['tmpls']
        map = {}
        for i, f in enumerate(old):
            idx = combos[i].currentIndex()
            if idx == len(new):
                # ignore
                map[f['ord']] = None
            else:
                f2 = new[idx]
                map[f['ord']] = f2['ord']
        return map

    def getFieldMap(self):
        return self.getTemplateMap(
            old=self.oldModel['flds'],
            combos=self.fcombos,
            new=self.targetModel['flds'])

    def cleanup(self):
        remHook("reset", self.onReset)
        remHook("currentModelChanged", self.onReset)
        self.modelChooser.cleanup()
        saveGeom(self, "changeModel")

    def reject(self):
        self.cleanup()
        return QDialog.reject(self)

    def accept(self):
        # check maps
        fmap = self.getFieldMap()
        cmap = self.getTemplateMap()
        if any(True for c in cmap.values() if c is None):
            if not askUser(_("""\
Any cards mapped to nothing will be deleted. \
If a note has no remaining cards, it will be lost. \
Are you sure you want to continue?""")):
                return
        QDialog.accept(self)
        self.browser.mw.checkpoint(_("Change Note Type"))
        b = self.browser
        b.mw.progress.start()
        b.model.beginReset()
        mm = b.mw.col.models
        mm.change(self.oldModel, self.nids, self.targetModel, fmap, cmap)
        b.onSearch(reset=False)
        b.model.endReset()
        b.mw.progress.finish()
        b.mw.reset()
        self.cleanup()

    def onHelp(self):
        openHelp("browsermisc")

# Toolbar
######################################################################

class BrowserToolbar(Toolbar):

    def __init__(self, mw, web, browser):
        self.browser = browser
        Toolbar.__init__(self, mw, web)

    def draw(self):
        mark = self.browser.isMarked()
        pause = self.browser.isSuspended()
        def borderImg(link, icon, on, title, tooltip=None):
            if on:
                fmt = '''\
<a class=hitem title="%s" href="%s">\
<img valign=bottom style='border: 1px solid #aaa;' src="qrc:/icons/%s.png"> %s</a>'''
            else:
                fmt = '''\
<a class=hitem title="%s" href="%s"><img style="padding: 1px;" valign=bottom src="qrc:/icons/%s.png"> %s</a>'''
            return fmt % (tooltip or title, link, icon, title)
        right = "<div>"
        right += borderImg("add", "add16", False, _("Add"))
        right += borderImg("info", "info", False, _("Info"),
                       shortcut(_("Card Info (Ctrl+Shift+I)")))
        right += borderImg("mark", "star16", mark, _("Mark"),
                       shortcut(_("Mark Note (Ctrl+K)")))
        right += borderImg("pause", "pause16", pause, _("Suspend"))
        right += borderImg("setDeck", "deck16", False, _("Change Deck"),
                           shortcut(_("Move To Deck (Ctrl+D)")))
        right += borderImg("addtag", "addtag16", False, _("Add Tags"),
                       shortcut(_("Bulk Add Tags (Ctrl+Shift+T)")))
        right += borderImg("deletetag", "deletetag16", False,
                           _("Remove Tags"), shortcut(_(
                               "Bulk Remove Tags (Ctrl+Alt+T)")))
        right += borderImg("delete", "delete16", False, _("Delete"))
        right += "</div>"
        self.web.page().currentFrame().setScrollBarPolicy(
            Qt.Horizontal, Qt.ScrollBarAlwaysOff)
        self.web.stdHtml(self._body % (
            "", #<span style='display:inline-block; width: 100px;'></span>",
            #self._centerLinks(),
            right, ""), self._css + """
#header { font-weight: normal; }
a { margin-right: 1em; }
.hitem { overflow: hidden; white-space: nowrap;}
""")

    # Link handling
    ######################################################################

    def _linkHandler(self, l):
        if l == "anki":
            self.showMenu()
        elif l  == "add":
            self.browser.mw.onAddCard()
        elif l  == "delete":
            self.browser.deleteNotes()
        elif l  == "setDeck":
            self.browser.setDeck()
        # icons
        elif l  == "info":
            self.browser.showCardInfo()
        elif l == "mark":
            self.browser.onMark()
        elif l == "pause":
            self.browser.onSuspend()
        elif l == "addtag":
            self.browser.addTags()
        elif l == "deletetag":
            self.browser.deleteTags()

########NEW FILE########
__FILENAME__ = clayout
# -*- coding: utf-8 -*-
# Copyright: Damien Elmes <anki@ichi2.net>
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

from aqt.qt import *
import re
from anki.consts import *
import aqt
from anki.sound import playFromText, clearAudioQueue
from aqt.utils import saveGeom, restoreGeom, getBase, mungeQA, \
     saveSplitter, restoreSplitter, showInfo, askUser, getOnlyText, \
     showWarning, openHelp, openLink
from anki.utils import isMac, isWin, joinFields
from aqt.webview import AnkiWebView
import anki.js

class CardLayout(QDialog):

    def __init__(self, mw, note, ord=0, parent=None, addMode=False):
        QDialog.__init__(self, parent or mw, Qt.Window)
        self.mw = aqt.mw
        self.parent = parent or mw
        self.note = note
        self.ord = ord
        self.col = self.mw.col
        self.mm = self.mw.col.models
        self.model = note.model()
        self.mw.checkpoint(_("Card Types"))
        self.addMode = addMode
        if addMode:
            # save it to DB temporarily
            self.emptyFields = []
            for name, val in note.items():
                if val.strip():
                    continue
                self.emptyFields.append(name)
                note[name] = "(%s)" % name
            note.flush()
        self.setupTabs()
        self.setupButtons()
        self.setWindowTitle(_("Card Types for %s") % self.model['name'])
        v1 = QVBoxLayout()
        v1.addWidget(self.tabs)
        v1.addLayout(self.buttons)
        self.setLayout(v1)
        self.redraw()
        restoreGeom(self, "CardLayout")
        self.exec_()

    def redraw(self):
        self.cards = self.col.previewCards(self.note, 2)
        self.redrawing = True
        self.updateTabs()
        self.redrawing = False
        self.selectCard(self.ord)

    def setupTabs(self):
        c = self.connect
        cloze = self.model['type'] == MODEL_CLOZE
        self.tabs = QTabWidget()
        self.tabs.setUsesScrollButtons(True)
        if not cloze:
            add = QPushButton("+")
            add.setFixedWidth(30)
            add.setToolTip(_("Add new card"))
            c(add, SIGNAL("clicked()"), self.onAddCard)
            self.tabs.setCornerWidget(add)
        c(self.tabs, SIGNAL("currentChanged(int)"), self.selectCard)

    def updateTabs(self):
        self.forms = []
        self.tabs.clear()
        for t in self.model['tmpls']:
            self.addTab(t)

    def addTab(self, t):
        c = self.connect
        w = QWidget()
        l = QHBoxLayout()
        l.setMargin(0)
        l.setSpacing(3)
        left = QWidget()
        # template area
        tform = aqt.forms.template.Ui_Form()
        tform.setupUi(left)
        tform.label1.setText(u" →")
        tform.label2.setText(u" →")
        tform.labelc1.setText(u" ↗")
        tform.labelc2.setText(u" ↘")
        if self.style().objectName() == "gtk+":
            # gtk+ requires margins in inner layout
            tform.tlayout1.setContentsMargins(0, 11, 0, 0)
            tform.tlayout2.setContentsMargins(0, 11, 0, 0)
            tform.tlayout3.setContentsMargins(0, 11, 0, 0)
        if len(self.cards) > 1:
            tform.groupBox_3.setTitle(_(
                "Styling (shared between cards)"))
        c(tform.front, SIGNAL("textChanged()"), self.saveCard)
        c(tform.css, SIGNAL("textChanged()"), self.saveCard)
        c(tform.back, SIGNAL("textChanged()"), self.saveCard)
        l.addWidget(left, 5)
        # preview area
        right = QWidget()
        pform = aqt.forms.preview.Ui_Form()
        pform.setupUi(right)
        if self.style().objectName() == "gtk+":
            # gtk+ requires margins in inner layout
            pform.frontPrevBox.setContentsMargins(0, 11, 0, 0)
            pform.backPrevBox.setContentsMargins(0, 11, 0, 0)
        # for cloze notes, show that it's one of n cards
        if self.model['type'] == MODEL_CLOZE:
            cnt = len(self.mm.availOrds(
                self.model, joinFields(self.note.fields)))
            for g in pform.groupBox, pform.groupBox_2:
                g.setTitle(g.title() + _(" (1 of %d)") % max(cnt, 1))
        pform.frontWeb = AnkiWebView()
        pform.frontPrevBox.addWidget(pform.frontWeb)
        pform.backWeb = AnkiWebView()
        pform.backPrevBox.addWidget(pform.backWeb)
        def linkClicked(url):
            openLink(url)
        for wig in pform.frontWeb, pform.backWeb:
            wig.page().setLinkDelegationPolicy(
                QWebPage.DelegateExternalLinks)
            c(wig, SIGNAL("linkClicked(QUrl)"), linkClicked)
        l.addWidget(right, 5)
        w.setLayout(l)
        self.forms.append({'tform': tform, 'pform': pform})
        self.tabs.addTab(w, t['name'])

    def onRemoveTab(self, idx):
        if len(self.model['tmpls']) < 2:
            return showInfo(_("At least one card is required."))
        if not askUser(_("Remove all cards of this type?")):
            return
        if not self.mm.remTemplate(self.model, self.cards[idx].template()):
            return showWarning(_("""\
Removing this card type would cause one or more notes to be deleted. \
Please create a new card type first."""))
        self.redraw()

    # Buttons
    ##########################################################################

    def setupButtons(self):
        c = self.connect
        l = self.buttons = QHBoxLayout()
        help = QPushButton(_("Help"))
        help.setAutoDefault(False)
        l.addWidget(help)
        c(help, SIGNAL("clicked()"), self.onHelp)
        l.addStretch()
        addField = QPushButton(_("Add Field"))
        addField.setAutoDefault(False)
        l.addWidget(addField)
        c(addField, SIGNAL("clicked()"), self.onAddField)
        if self.model['type'] != MODEL_CLOZE:
            flip = QPushButton(_("Flip"))
            flip.setAutoDefault(False)
            l.addWidget(flip)
            c(flip, SIGNAL("clicked()"), self.onFlip)
        more = QPushButton(_("More") + u" ▾")
        more.setAutoDefault(False)
        l.addWidget(more)
        c(more, SIGNAL("clicked()"), lambda: self.onMore(more))
        l.addStretch()
        close = QPushButton(_("Close"))
        close.setAutoDefault(False)
        l.addWidget(close)
        c(close, SIGNAL("clicked()"), self.accept)

    # Cards
    ##########################################################################

    def selectCard(self, idx):
        if self.redrawing:
            return
        self.ord = idx
        if idx >= len(self.cards):
            idx = len(self.cards) - 1
        self.card = self.cards[idx]
        self.tab = self.forms[idx]
        self.tabs.setCurrentIndex(idx)
        self.playedAudio = {}
        self.readCard()
        self.renderPreview()

    def readCard(self):
        t = self.card.template()
        self.redrawing = True
        self.tab['tform'].front.setPlainText(t['qfmt'])
        self.tab['tform'].css.setPlainText(self.model['css'])
        self.tab['tform'].back.setPlainText(t['afmt'])
        self.redrawing = False

    def saveCard(self):
        if self.redrawing:
            return
        text = self.tab['tform'].front.toPlainText()
        self.card.template()['qfmt'] = text
        text = self.tab['tform'].css.toPlainText()
        self.card.model()['css'] = text
        text = self.tab['tform'].back.toPlainText()
        self.card.template()['afmt'] = text
        self.renderPreview()

    # Preview
    ##########################################################################

    def renderPreview(self):
        c = self.card
        ti = self.maybeTextInput
        base = getBase(self.mw.col)
        self.tab['pform'].frontWeb.stdHtml(
            ti(mungeQA(c.q(reload=True))), self.mw.reviewer._styles(),
            bodyClass="card card%d" % (c.ord+1), head=base,
            js=anki.js.browserSel)
        self.tab['pform'].backWeb.stdHtml(
            ti(mungeQA(c.a()), type='a'), self.mw.reviewer._styles(),
            bodyClass="card card%d" % (c.ord+1), head=base,
            js=anki.js.browserSel)
        clearAudioQueue()
        if c.id not in self.playedAudio:
            playFromText(c.q())
            playFromText(c.a())
            self.playedAudio[c.id] = True

    def maybeTextInput(self, txt, type='q'):
        if type == 'q':
            repl = "<center><input type=text value=''></center>"
        else:
            repl = _("(typing comparison appears here)")
        repl = "<center>%s</center>" % repl
        return re.sub("\[\[type:.+?\]\]", repl, txt)

    # Card operations
    ######################################################################

    def onRename(self):
        name = getOnlyText(_("New name:"),
                           default=self.card.template()['name'])
        if not name:
            return
        if name in [c.template()['name'] for c in self.cards
                    if c.template()['ord'] != self.ord]:
            return showWarning(_("That name is already used."))
        self.card.template()['name'] = name
        self.tabs.setTabText(self.tabs.currentIndex(), name)

    def onReorder(self):
        n = len(self.cards)
        cur = self.card.template()['ord']+1
        pos = getOnlyText(
            _("Enter new card position (1...%s):") % n,
            default=str(cur))
        if not pos:
            return
        try:
            pos = int(pos)
        except ValueError:
            return
        if pos < 1 or pos > n:
            return
        if pos == cur:
            return
        pos -= 1
        self.mm.moveTemplate(self.model, self.card.template(), pos)
        self.ord = pos
        self.redraw()

    def _newCardName(self):
        n = len(self.cards) + 1
        while 1:
            name = _("Card %d") % n
            if name not in [c.template()['name'] for c in self.cards]:
                break
            n += 1
        return name

    def onAddCard(self):
        name = self._newCardName()
        t = self.mm.newTemplate(name)
        old = self.card.template()
        t['qfmt'] = "%s<br>\n%s" % (_("Edit to customize"), old['qfmt'])
        t['afmt'] = old['afmt']
        self.mm.addTemplate(self.model, t)
        self.redraw()
        self.selectCard(t['ord'])

    def onFlip(self):
        old = self.card.template()
        self._flipQA(old, old)
        self.redraw()

    def _flipQA(self, src, dst):
        m = re.match("(?s)(.+)<hr id=answer>(.+)", src['afmt'])
        if not m:
            showInfo(_("""\
Anki couldn't find the line between the question and answer. Please \
adjust the template manually to switch the question and answer."""))
            return
        dst['afmt'] = "{{FrontSide}}\n\n<hr id=answer>\n\n%s" % src['qfmt']
        dst['qfmt'] = m.group(2).strip()
        return True

    def onMore(self, button):
        m = QMenu(self)
        a = m.addAction(_("Rename"))
        a.connect(a, SIGNAL("triggered()"),
                  self.onRename)
        if self.model['type'] != MODEL_CLOZE:
            a = m.addAction(_("Reposition"))
            a.connect(a, SIGNAL("triggered()"),
                      self.onReorder)
            t = self.card.template()
            if t['did']:
                s = _(" (on)")
            else:
                s = _(" (off)")
            a = m.addAction(_("Deck Override") + s)
            a.connect(a, SIGNAL("triggered()"),
                      self.onTargetDeck)
        a = m.addAction(_("Column Templates"))
        a.connect(a, SIGNAL("triggered()"),
                  self.onBrowserDisplay)
        if self.model['type'] != MODEL_CLOZE:
            a = m.addAction(_("Delete"))
            a.connect(a, SIGNAL("triggered()"),
                      lambda: self.onRemoveTab(self.tabs.currentIndex()))
        m.exec_(button.mapToGlobal(QPoint(0,0)))

    def onBrowserDisplay(self):
        d = QDialog()
        f = aqt.forms.browserdisp.Ui_Dialog()
        f.setupUi(d)
        t = self.card.template()
        f.qfmt.setText(t.get('bqfmt', ""))
        f.afmt.setText(t.get('bafmt', ""))
        d.connect(f.buttonBox, SIGNAL("accepted()"),
                  lambda: self.onBrowserDisplayOk(f))
        d.exec_()

    def onBrowserDisplayOk(self, f):
        t = self.card.template()
        t['bqfmt'] = f.qfmt.text().strip()
        t['bafmt'] = f.afmt.text().strip()

    def onTargetDeck(self):
        from aqt.tagedit import TagEdit
        t = self.card.template()
        d = QDialog(self)
        d.setWindowTitle("Anki")
        d.setMinimumWidth(400)
        l = QVBoxLayout()
        lab = QLabel(_("""\
Enter deck to place new %s cards in, or leave blank:""") %
                           self.card.template()['name'])
        lab.setWordWrap(True)
        l.addWidget(lab)
        te = TagEdit(d, type=1)
        te.setCol(self.col)
        l.addWidget(te)
        if t['did']:
            te.setText(self.col.decks.get(t['did'])['name'])
            te.selectAll()
        bb = QDialogButtonBox(QDialogButtonBox.Close)
        self.connect(bb, SIGNAL("rejected()"), d, SLOT("close()"))
        l.addWidget(bb)
        d.setLayout(l)
        d.exec_()
        if not te.text().strip():
            t['did'] = None
        else:
            t['did'] = self.col.decks.id(te.text())

    def onAddField(self):
        diag = QDialog(self)
        form = aqt.forms.addfield.Ui_Dialog()
        form.setupUi(diag)
        fields = [f['name'] for f in self.model['flds']]
        form.fields.addItems(fields)
        form.font.setCurrentFont(QFont("Arial"))
        form.size.setValue(20)
        diag.show()
        # Work around a Qt bug,
        # https://bugreports.qt-project.org/browse/QTBUG-1894
        if isMac or isWin:
            # No problems on Macs or Windows.
            form.fields.showPopup()
        else:
            # Delay showing the pop-up.
            self.mw.progress.timer(200, form.fields.showPopup, False)
        if not diag.exec_():
            return
        if form.radioQ.isChecked():
            obj = self.tab['tform'].front
        else:
            obj = self.tab['tform'].back
        self._addField(obj,
                       fields[form.fields.currentIndex()],
                       form.font.currentFont().family(),
                       form.size.value())

    def _addField(self, widg, field, font, size):
        t = widg.toPlainText()
        t +="\n<div style='font-family: %s; font-size: %spx;'>{{%s}}</div>\n" % (
            font, size, field)
        widg.setPlainText(t)
        self.saveCard()

    # Closing & Help
    ######################################################################

    def accept(self):
        self.reject()

    def reject(self):
        clearAudioQueue()
        if self.addMode:
            # remove the filler fields we added
            for name in self.emptyFields:
                self.note[name] = ""
            self.mw.col.db.execute("delete from notes where id = ?",
                                   self.note.id)
        self.mm.save(self.model, templates=True)
        self.mw.reset()
        saveGeom(self, "CardLayout")
        return QDialog.reject(self)

    def onHelp(self):
        openHelp("templates")

########NEW FILE########
__FILENAME__ = customstudy
# Copyright: Damien Elmes <anki@ichi2.net>
# -*- coding: utf-8 -*-
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

from aqt.qt import *
import aqt
from anki.utils import ids2str, isWin, isMac
from aqt.utils import showInfo, showWarning, openHelp, getOnlyText, askUser
from operator import itemgetter
from anki.consts import *

RADIO_NEW = 1
RADIO_REV = 2
RADIO_FORGOT = 3
RADIO_AHEAD = 4
RADIO_RANDOM = 5
RADIO_PREVIEW = 6
RADIO_TAGS = 7

class CustomStudy(QDialog):
    def __init__(self, mw):
        QDialog.__init__(self, mw)
        self.mw = mw
        self.deck = self.mw.col.decks.current()
        self.form = f = aqt.forms.customstudy.Ui_Dialog()
        f.setupUi(self)
        self.setWindowModality(Qt.WindowModal)
        self.setupSignals()
        f.radio1.click()
        self.exec_()

    def setupSignals(self):
        f = self.form; c = self.connect; s = SIGNAL("clicked()")
        c(f.radio1, s, lambda: self.onRadioChange(1))
        c(f.radio2, s, lambda: self.onRadioChange(2))
        c(f.radio3, s, lambda: self.onRadioChange(3))
        c(f.radio4, s, lambda: self.onRadioChange(4))
        c(f.radio5, s, lambda: self.onRadioChange(5))
        c(f.radio6, s, lambda: self.onRadioChange(6))
        c(f.radio7, s, lambda: self.onRadioChange(7))

    def onRadioChange(self, idx):
        f = self.form; sp = f.spin
        smin = 1; smax = 9999; sval = 1
        post = _("cards")
        tit = ""
        spShow = True
        def plus(num):
            if num == 1000:
                num = "1000+"
            return "<b>"+str(num)+"</b>"
        if idx == RADIO_NEW:
            new = self.mw.col.sched.totalNewForCurrentDeck()
            self.deck['newToday']
            tit = _("New cards in deck: %s") % plus(new)
            pre = _("Increase today's new card limit by")
            sval = min(new, self.deck.get('extendNew', 10))
            smax = new
        elif idx == RADIO_REV:
            rev = self.mw.col.sched.totalRevForCurrentDeck()
            tit = _("Reviews due in deck: %s") % plus(rev)
            pre = _("Increase today's review limit by")
            sval = min(rev, self.deck.get('extendRev', 10))
        elif idx == RADIO_FORGOT:
            pre = _("Review cards forgotten in last")
            post = _("days")
            smax = 30
        elif idx == RADIO_AHEAD:
            pre = _("Review ahead by")
            post = _("days")
        elif idx == RADIO_RANDOM:
            pre = _("Select")
            post = _("cards randomly from the deck")
            sval = 100
        elif idx == RADIO_PREVIEW:
            pre = _("Preview new cards added in the last")
            post = _("days")
            sval = 1
        elif idx == RADIO_TAGS:
            tit = _("Press OK to choose tags.")
            sval = 100
            spShow = False
            pre = post = ""
        sp.setShown(spShow)
        f.title.setText(tit)
        f.title.setShown(not not tit)
        f.spin.setMinimum(smin)
        f.spin.setMaximum(smax)
        f.spin.setValue(sval)
        f.preSpin.setText(pre)
        f.postSpin.setText(post)
        self.radioIdx = idx

    def accept(self):
        f = self.form; i = self.radioIdx; spin = f.spin.value()
        if i == RADIO_NEW:
            self.deck['extendNew'] = spin
            self.mw.col.decks.save(self.deck)
            self.mw.col.sched.extendLimits(spin, 0)
            self.mw.reset()
            return QDialog.accept(self)
        elif i == RADIO_REV:
            self.deck['extendRev'] = spin
            self.mw.col.decks.save(self.deck)
            self.mw.col.sched.extendLimits(0, spin)
            self.mw.reset()
            return QDialog.accept(self)
        elif i == RADIO_TAGS:
            tags = self._getTags()
            if not tags:
                return
        # the rest create a filtered deck
        cur = self.mw.col.decks.byName(_("Custom Study Session"))
        if cur:
            if not cur['dyn']:
                showInfo("Please rename the existing Custom Study deck first.")
                return QDialog.accept(self)
            else:
                # safe to empty
                self.mw.col.sched.emptyDyn(cur['id'])
                # reuse; don't delete as it may have children
                dyn = cur
                self.mw.col.decks.select(cur['id'])
        else:
            did = self.mw.col.decks.newDyn(_("Custom Study Session"))
            dyn = self.mw.col.decks.get(did)
        # and then set various options
        if i == RADIO_FORGOT:
            dyn['delays'] = [1]
            dyn['terms'][0] = ['rated:%d:1' % spin, 9999, DYN_RANDOM]
            dyn['resched'] = False
        elif i == RADIO_AHEAD:
            dyn['delays'] = None
            dyn['terms'][0] = ['prop:due<=%d' % spin, 9999, DYN_DUE]
            dyn['resched'] = True
        elif i == RADIO_RANDOM:
            dyn['delays'] = None
            dyn['terms'][0] = ['', spin, DYN_RANDOM]
            dyn['resched'] = True
        elif i == RADIO_PREVIEW:
            dyn['delays'] = None
            dyn['terms'][0] = ['is:new added:%s'%spin, 9999, DYN_OLDEST]
            dyn['resched'] = False
        elif i == RADIO_TAGS:
            dyn['delays'] = None
            dyn['terms'][0] = ["(is:new or is:due) "+tags, 9999, DYN_RANDOM]
            dyn['resched'] = True
        # add deck limit
        dyn['terms'][0][0] = "deck:\"%s\" %s " % (self.deck['name'], dyn['terms'][0][0])
        # generate cards
        if not self.mw.col.sched.rebuildDyn():
            return showWarning(_("No cards matched the criteria you provided."))
        self.mw.moveToState("overview")
        QDialog.accept(self)

    def _getTags(self):
        from aqt.taglimit import TagLimit
        t = TagLimit(self.mw, self)
        return t.tags

########NEW FILE########
__FILENAME__ = deckbrowser
# Copyright: Damien Elmes <anki@ichi2.net>
# -*- coding: utf-8 -*-
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

from aqt.qt import *
from aqt.utils import askUser, getOnlyText, openLink, showWarning, showInfo, \
    shortcut
from anki.utils import isMac, ids2str, fmtTimeSpan
import anki.js
from anki.errors import DeckRenameError
import aqt
from anki.sound import clearAudioQueue

class DeckBrowser(object):

    def __init__(self, mw):
        self.mw = mw
        self.web = mw.web
        self.bottom = aqt.toolbar.BottomBar(mw, mw.bottomWeb)

    def show(self):
        clearAudioQueue()
        self.web.setLinkHandler(self._linkHandler)
        self.web.setKeyHandler(None)
        self.mw.keyHandler = self._keyHandler
        self._renderPage()

    def refresh(self):
        self._renderPage()

    # Event handlers
    ##########################################################################

    def _linkHandler(self, url):
        if ":" in url:
            (cmd, arg) = url.split(":")
        else:
            cmd = url
        if cmd == "open":
            self._selDeck(arg)
        elif cmd == "opts":
            self._showOptions(arg)
        elif cmd == "shared":
            self._onShared()
        elif cmd == "import":
            self.mw.onImport()
        elif cmd == "create":
            deck = getOnlyText(_("New deck name:"))
            if deck:
                self.mw.col.decks.id(deck)
                self.refresh()
        elif cmd == "drag":
            draggedDeckDid, ontoDeckDid = arg.split(',')
            self._dragDeckOnto(draggedDeckDid, ontoDeckDid)
        elif cmd == "collapse":
            self._collapse(arg)

    def _keyHandler(self, evt):
        # currently does nothing
        key = unicode(evt.text())

    def _selDeck(self, did):
        self.mw.col.decks.select(did)
        self.mw.onOverview()

    # HTML generation
    ##########################################################################

    _dragIndicatorBorderWidth = "1px"

    _css = """
a.deck { color: #000; text-decoration: none; min-width: 5em;
         display:inline-block; }
a.deck:hover { text-decoration: underline; }
tr.deck td { border-bottom: %(width)s solid #e7e7e7; }
tr.top-level-drag-row td { border-bottom: %(width)s solid transparent; }
td { white-space: nowrap; }
tr.drag-hover td { border-bottom: %(width)s solid #aaa; }
body { margin: 1em; -webkit-user-select: none; }
.current { background-color: #e7e7e7; }
.decktd { min-width: 15em; }
.count { width: 6em; text-align: right; }
.collapse { color: #000; text-decoration:none; display:inline-block;
    width: 1em; }
.filtered { color: #00a !important; }
""" % dict(width=_dragIndicatorBorderWidth)

    _body = """
<center>
<table cellspacing=0 cellpading=3>
%(tree)s
</table>

<br>
%(stats)s
</center>
<script>
    $( init );

    function init() {

        $("tr.deck").draggable({
            scroll: false,

            // can't use "helper: 'clone'" because of a bug in jQuery 1.5
            helper: function (event) {
                return $(this).clone(false);
            },
            delay: 200,
            opacity: 0.7
        });
        $("tr.deck").droppable({
            drop: handleDropEvent,
            hoverClass: 'drag-hover',
        });
        $("tr.top-level-drag-row").droppable({
            drop: handleDropEvent,
            hoverClass: 'drag-hover',
        });
    }

    function handleDropEvent(event, ui) {
        var draggedDeckId = ui.draggable.attr('id');
        var ontoDeckId = $(this).attr('id');

        py.link("drag:" + draggedDeckId + "," + ontoDeckId);
    }
</script>
"""

    def _renderPage(self, reuse=False):
        css = self.mw.sharedCSS + self._css
        if not reuse:
            self._dueTree = self.mw.col.sched.deckDueTree()
        tree = self._renderDeckTree(self._dueTree)
        stats = self._renderStats()
        op = self._oldPos()
        self.web.stdHtml(self._body%dict(tree=tree, stats=stats), css=css,
                         js=anki.js.jquery+anki.js.ui, loadCB=lambda ok:\
                         self.web.page().mainFrame().setScrollPosition(op))
        self.web.key = "deckBrowser"
        self._drawButtons()

    def _oldPos(self):
        if self.web.key == "deckBrowser":
            return self.web.page().mainFrame().scrollPosition()
        else:
            return QPoint(0,0)

    def _renderStats(self):
        cards, thetime = self.mw.col.db.first("""
select count(), sum(time)/1000 from revlog
where id > ?""", (self.mw.col.sched.dayCutoff-86400)*1000)
        cards = cards or 0
        thetime = thetime or 0
        msgp1 = ngettext("%d card", "%d cards", cards) % cards
        buf = _("Studied %(a)s in %(b)s today.") % dict(a=msgp1,
                                                        b=fmtTimeSpan(thetime, unit=1))
        return buf

    def _renderDeckTree(self, nodes, depth=0):
        if not nodes:
            return ""
        if depth == 0:
            buf = """
<tr><th colspan=5 align=left>%s</th><th class=count>%s</th>
<th class=count>%s</th><th class=count></th></tr>""" % (
            _("Deck"), _("Due"), _("New"))
            buf += self._topLevelDragRow()
        else:
            buf = ""
        for node in nodes:
            buf += self._deckRow(node, depth, len(nodes))
        if depth == 0:
            buf += self._topLevelDragRow()
        return buf

    def _deckRow(self, node, depth, cnt):
        name, did, due, lrn, new, children = node
        deck = self.mw.col.decks.get(did)
        if did == 1 and cnt > 1 and not children:
            # if the default deck is empty, hide it
            if not self.mw.col.db.scalar("select 1 from cards where did = 1"):
                return ""
        # parent toggled for collapsing
        for parent in self.mw.col.decks.parents(did):
            if parent['collapsed']:
                buff = ""
                return buff
        prefix = "-"
        if self.mw.col.decks.get(did)['collapsed']:
            prefix = "+"
        due += lrn
        def indent():
            return "&nbsp;"*6*depth
        if did == self.mw.col.conf['curDeck']:
            klass = 'deck current'
        else:
            klass = 'deck'
        buf = "<tr class='%s' id='%d'>" % (klass, did)
        # deck link
        if children:
            collapse = "<a class=collapse href='collapse:%d'>%s</a>" % (did, prefix)
        else:
            collapse = "<span class=collapse></span>"
        if deck['dyn']:
            extraclass = "filtered"
        else:
            extraclass = ""
        buf += """

        <td class=decktd colspan=5>%s%s<a class="deck %s" href='open:%d'>%s</a></td>"""% (
            indent(), collapse, extraclass, did, name)
        # due counts
        def nonzeroColour(cnt, colour):
            if not cnt:
                colour = "#e0e0e0"
            if cnt >= 1000:
                cnt = "1000+"
            return "<font color='%s'>%s</font>" % (colour, cnt)
        buf += "<td align=right>%s</td><td align=right>%s</td>" % (
            nonzeroColour(due, "#007700"),
            nonzeroColour(new, "#000099"))
        # options
        buf += "<td align=right class=opts>%s</td></tr>" % self.mw.button(
            link="opts:%d"%did, name="<img valign=bottom src='qrc:/icons/gears.png'>&#9662;")
        # children
        buf += self._renderDeckTree(children, depth+1)
        return buf

    def _topLevelDragRow(self):
        return "<tr class='top-level-drag-row'><td colspan='6'>&nbsp;</td></tr>"

    def _dueImg(self, due, new):
        if due:
            i = "clock-icon"
        elif new:
            i = "plus-circle"
        else:
            i = "none"
        return '<img valign=bottom src="qrc:/icons/%s.png">' % i

    # Options
    ##########################################################################

    def _showOptions(self, did):
        m = QMenu(self.mw)
        a = m.addAction(_("Rename"))
        a.connect(a, SIGNAL("triggered()"), lambda did=did: self._rename(did))
        a = m.addAction(_("Options"))
        a.connect(a, SIGNAL("triggered()"), lambda did=did: self._options(did))
        a = m.addAction(_("Delete"))
        a.connect(a, SIGNAL("triggered()"), lambda did=did: self._delete(did))
        m.exec_(QCursor.pos())

    def _rename(self, did):
        self.mw.checkpoint(_("Rename Deck"))
        deck = self.mw.col.decks.get(did)
        oldName = deck['name']
        newName = getOnlyText(_("New deck name:"), default=oldName)
        newName = newName.replace("'", "").replace('"', "")
        if not newName or newName == oldName:
            return
        try:
            self.mw.col.decks.rename(deck, newName)
        except DeckRenameError, e:
            return showWarning(e.description)
        self.show()

    def _options(self, did):
        # select the deck first, because the dyn deck conf assumes the deck
        # we're editing is the current one
        self.mw.col.decks.select(did)
        self.mw.onDeckConf()

    def _collapse(self, did):
        self.mw.col.decks.collapse(did)
        self._renderPage(reuse=True)

    def _dragDeckOnto(self, draggedDeckDid, ontoDeckDid):
        try:
            self.mw.col.decks.renameForDragAndDrop(draggedDeckDid, ontoDeckDid)
        except DeckRenameError, e:
            return showWarning(e.description)

        self.show()

    def _delete(self, did):
        if str(did) == '1':
            return showWarning(_("The default deck can't be deleted."))
        self.mw.checkpoint(_("Delete Deck"))
        deck = self.mw.col.decks.get(did)
        if not deck['dyn']:
            dids = [did] + [r[1] for r in self.mw.col.decks.children(did)]
            cnt = self.mw.col.db.scalar(
                "select count() from cards where did in {0} or "
                "odid in {0}".format(ids2str(dids)))
            if cnt:
                extra = ngettext(" It has %d card.", " It has %d cards.", cnt) % cnt
            else:
                extra = None
        if deck['dyn'] or not extra or askUser(
            (_("Are you sure you wish to delete %s?") % deck['name']) +
            extra):
            self.mw.progress.start(immediate=True)
            self.mw.col.decks.rem(did, True)
            self.mw.progress.finish()
            self.show()

    # Top buttons
    ######################################################################

    def _drawButtons(self):
        links = [
            ["", "shared", _("Get Shared")],
            ["", "create", _("Create Deck")],
            ["Ctrl+I", "import", _("Import File")],
        ]
        buf = ""
        for b in links:
            if b[0]:
                b[0] = _("Shortcut key: %s") % shortcut(b[0])
            buf += """
<button title='%s' onclick='py.link(\"%s\");'>%s</button>""" % tuple(b)
        self.bottom.draw(buf)
        if isMac:
            size = 28
        else:
            size = 36 + self.mw.fontHeightDelta*3
        self.bottom.web.setFixedHeight(size)
        self.bottom.web.setLinkHandler(self._linkHandler)

    def _onShared(self):
        openLink(aqt.appShared+"decks/")

########NEW FILE########
__FILENAME__ = deckchooser
# -*- coding: utf-8 -*-
# Copyright: Damien Elmes <anki@ichi2.net>
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

from aqt.qt import *
from operator import itemgetter
from anki.hooks import addHook, remHook, runHook
from aqt.utils import isMac, shortcut
import aqt

class DeckChooser(QHBoxLayout):

    def __init__(self, mw, widget, label=True, start=None):
        QHBoxLayout.__init__(self)
        self.widget = widget
        self.mw = mw
        self.deck = mw.col
        self.label = label
        self.setMargin(0)
        self.setSpacing(8)
        self.setupDecks()
        self.widget.setLayout(self)
        addHook('currentModelChanged', self.onModelChange)

    def setupDecks(self):
        if self.label:
            self.deckLabel = QLabel(_("Deck"))
            self.addWidget(self.deckLabel)
        # decks box
        self.deck = QPushButton()
        self.deck.setToolTip(shortcut(_("Target Deck (Ctrl+D)")))
        s = QShortcut(QKeySequence(_("Ctrl+D")), self.widget)
        s.connect(s, SIGNAL("activated()"), self.onDeckChange)
        self.addWidget(self.deck)
        self.connect(self.deck, SIGNAL("clicked()"), self.onDeckChange)
        # starting label
        if self.mw.col.conf.get("addToCur", True):
            col = self.mw.col
            did = col.conf['curDeck']
            if col.decks.isDyn(did):
                did = 1
            self.deck.setText(self.mw.col.decks.nameOrNone(
                did) or _("Default"))
        else:
            self.deck.setText(self.mw.col.decks.nameOrNone(
                self.mw.col.models.current()['did']) or _("Default"))
        # layout
        sizePolicy = QSizePolicy(
            QSizePolicy.Policy(7),
            QSizePolicy.Policy(0))
        self.deck.setSizePolicy(sizePolicy)

    def show(self):
        self.widget.show()

    def hide(self):
        self.widget.hide()

    def cleanup(self):
        remHook('currentModelChanged', self.onModelChange)

    def onModelChange(self):
        if not self.mw.col.conf.get("addToCur", True):
            self.deck.setText(self.mw.col.decks.nameOrNone(
                self.mw.col.models.current()['did']) or _("Default"))

    def onDeckChange(self):
        from aqt.studydeck import StudyDeck
        current = self.deck.text()
        ret = StudyDeck(
            self.mw, current=current, accept=_("Choose"),
            title=_("Choose Deck"), help="addingnotes",
            cancel=False, parent=self.widget)
        self.deck.setText(ret.name)

    def selectedId(self):
        # save deck name
        name = self.deck.text()
        if not name.strip():
            did = 1
        else:
            did = self.mw.col.decks.id(name)
        return did

########NEW FILE########
__FILENAME__ = deckconf
# Copyright: Damien Elmes <anki@ichi2.net>
# -*- coding: utf-8 -*-
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

from aqt.qt import *
import aqt
from anki.utils import ids2str
from aqt.utils import showInfo, showWarning, openHelp, getOnlyText, askUser, \
    tooltip
from operator import itemgetter

class DeckConf(QDialog):
    def __init__(self, mw, deck):
        QDialog.__init__(self, mw)
        self.mw = mw
        self.deck = deck
        self.childDids = [
            d[1] for d in self.mw.col.decks.children(self.deck['id'])]
        self.form = aqt.forms.dconf.Ui_Dialog()
        self.form.setupUi(self)
        self.mw.checkpoint(_("Options"))
        self.setupCombos()
        self.setupConfs()
        self.setWindowModality(Qt.WindowModal)
        self.connect(self.form.buttonBox,
                     SIGNAL("helpRequested()"),
                     lambda: openHelp("deckoptions"))
        self.connect(self.form.confOpts, SIGNAL("clicked()"), self.confOpts)
        self.form.confOpts.setText(u"▾")
        self.connect(self.form.buttonBox.button(QDialogButtonBox.RestoreDefaults),
                     SIGNAL("clicked()"),
                     self.onRestore)
        self.setWindowTitle(_("Options for %s") % self.deck['name'])
        self.exec_()

    def setupCombos(self):
        import anki.consts as cs
        f = self.form
        f.newOrder.addItems(cs.newCardOrderLabels().values())
        self.connect(f.newOrder, SIGNAL("currentIndexChanged(int)"),
                     self.onNewOrderChanged)

    # Conf list
    ######################################################################

    def setupConfs(self):
        self.connect(self.form.dconf, SIGNAL("currentIndexChanged(int)"),
                     self.onConfChange)
        self.conf = None
        self.loadConfs()

    def loadConfs(self):
        current = self.deck['conf']
        self.confList = self.mw.col.decks.allConf()
        self.confList.sort(key=itemgetter('name'))
        startOn = 0
        self.ignoreConfChange = True
        self.form.dconf.clear()
        for idx, conf in enumerate(self.confList):
            self.form.dconf.addItem(conf['name'])
            if str(conf['id']) == str(current):
                startOn = idx
        self.ignoreConfChange = False
        self.form.dconf.setCurrentIndex(startOn)
        self.onConfChange(startOn)

    def confOpts(self):
        m = QMenu(self.mw)
        a = m.addAction(_("Add"))
        a.connect(a, SIGNAL("triggered()"), self.addGroup)
        a = m.addAction(_("Delete"))
        a.connect(a, SIGNAL("triggered()"), self.remGroup)
        a = m.addAction(_("Rename"))
        a.connect(a, SIGNAL("triggered()"), self.renameGroup)
        a = m.addAction(_("Set for all subdecks"))
        a.connect(a, SIGNAL("triggered()"), self.setChildren)
        if not self.childDids:
            a.setEnabled(False)
        m.exec_(QCursor.pos())

    def onConfChange(self, idx):
        if self.ignoreConfChange:
            return
        if self.conf:
            self.saveConf()
        conf = self.confList[idx]
        self.deck['conf'] = conf['id']
        self.loadConf()
        cnt = 0
        for d in self.mw.col.decks.all():
            if d['dyn']:
                continue
            if d['conf'] == conf['id']:
                cnt += 1
        self.form.count.setText(ngettext("%d deck uses this options group", \
                "%d decks use this options group", cnt) % cnt)

    def addGroup(self):
        name = getOnlyText(_("New options group name:"))
        if not name:
            return
        # first, save currently entered data to current conf
        self.saveConf()
        # then clone the conf
        id = self.mw.col.decks.confId(name, cloneFrom=self.conf)
        # set the deck to the new conf
        self.deck['conf'] = id
        # then reload the conf list
        self.loadConfs()

    def remGroup(self):
        if self.conf['id'] == 1:
            showInfo(_("The default configuration can't be removed."), self)
        else:
            self.mw.col.decks.remConf(self.conf['id'])
            self.deck['conf'] = 1
            self.loadConfs()

    def renameGroup(self):
        old = self.conf['name']
        name = getOnlyText(_("New name:"), default=old)
        if not name or name == old:
            return
        self.conf['name'] = name
        self.loadConfs()

    def setChildren(self):
        if not askUser(
            _("Set all decks below %s to this option group?") %
            self.deck['name']):
            return
        for did in self.childDids:
            deck = self.mw.col.decks.get(did)
            deck['conf'] = self.deck['conf']
            self.mw.col.decks.save(deck)
        tooltip(ngettext("%d deck updated.", "%d decks updated.", \
                        len(self.childDids)) % len(self.childDids))

    # Loading
    ##################################################

    def listToUser(self, l):
        return " ".join([str(x) for x in l])

    def parentLimText(self, type="new"):
        # top level?
        if "::" not in self.deck['name']:
            return ""
        lim = -1
        for d in self.mw.col.decks.parents(self.deck['id']):
            c = self.mw.col.decks.confForDid(d['id'])
            x = c[type]['perDay']
            if lim == -1:
                lim = x
            else:
                lim = min(x, lim)
        return _("(parent limit: %d)") % lim

    def loadConf(self):
        self.conf = self.mw.col.decks.confForDid(self.deck['id'])
        # new
        c = self.conf['new']
        f = self.form
        f.lrnSteps.setText(self.listToUser(c['delays']))
        f.lrnGradInt.setValue(c['ints'][0])
        f.lrnEasyInt.setValue(c['ints'][1])
        f.lrnEasyInt.setValue(c['ints'][1])
        f.lrnFactor.setValue(c['initialFactor']/10.0)
        f.newOrder.setCurrentIndex(c['order'])
        f.newPerDay.setValue(c['perDay'])
        f.separate.setChecked(c['separate'])
        f.newplim.setText(self.parentLimText('new'))
        # rev
        c = self.conf['rev']
        f.revPerDay.setValue(c['perDay'])
        f.revSpace.setValue(c['fuzz']*100)
        f.revMinSpace.setValue(c['minSpace'])
        f.easyBonus.setValue(c['ease4']*100)
        f.fi1.setValue(c['ivlFct']*100)
        f.maxIvl.setValue(c['maxIvl'])
        f.revplim.setText(self.parentLimText('rev'))
        # lapse
        c = self.conf['lapse']
        f.lapSteps.setText(self.listToUser(c['delays']))
        f.lapMult.setValue(c['mult']*100)
        f.lapMinInt.setValue(c['minInt'])
        f.leechThreshold.setValue(c['leechFails'])
        f.leechAction.setCurrentIndex(c['leechAction'])
        # general
        c = self.conf
        f.maxTaken.setValue(c['maxTaken'])
        f.showTimer.setChecked(c.get('timer', 0))
        f.autoplaySounds.setChecked(c['autoplay'])
        f.replayQuestion.setChecked(c.get('replayq', True))
        # description
        f.desc.setPlainText(self.deck['desc'])

    def onRestore(self):
        self.mw.progress.start()
        self.mw.col.decks.restoreToDefault(self.conf)
        self.mw.progress.finish()
        self.loadConf()

    # New order
    ##################################################

    def onNewOrderChanged(self, new):
        old = self.conf['new']['order']
        if old == new:
            return
        self.conf['new']['order'] = new
        self.mw.progress.start()
        self.mw.col.sched.resortConf(self.conf)
        self.mw.progress.finish()

    # Saving
    ##################################################

    def updateList(self, conf, key, w, minSize=1):
        items = unicode(w.text()).split(" ")
        ret = []
        for i in items:
            if not i:
                continue
            try:
                i = float(i)
                assert i > 0
                if i == int(i):
                    i = int(i)
                ret.append(i)
            except:
                # invalid, don't update
                showWarning(_("Steps must be numbers."))
                return
        if len(ret) < minSize:
            showWarning(_("At least one step is required."))
            return
        conf[key] = ret

    def saveConf(self):
        # new
        c = self.conf['new']
        f = self.form
        self.updateList(c, 'delays', f.lrnSteps)
        c['ints'][0] = f.lrnGradInt.value()
        c['ints'][1] = f.lrnEasyInt.value()
        c['initialFactor'] = f.lrnFactor.value()*10
        c['order'] = f.newOrder.currentIndex()
        c['perDay'] = f.newPerDay.value()
        c['separate'] = f.separate.isChecked()
        # rev
        c = self.conf['rev']
        c['perDay'] = f.revPerDay.value()
        c['fuzz'] = f.revSpace.value()/100.0
        c['minSpace'] = f.revMinSpace.value()
        c['ease4'] = f.easyBonus.value()/100.0
        c['ivlFct'] = f.fi1.value()/100.0
        c['maxIvl'] = f.maxIvl.value()
        # lapse
        c = self.conf['lapse']
        self.updateList(c, 'delays', f.lapSteps, minSize=0)
        c['mult'] = f.lapMult.value()/100.0
        c['minInt'] = f.lapMinInt.value()
        c['leechFails'] = f.leechThreshold.value()
        c['leechAction'] = f.leechAction.currentIndex()
        # general
        c = self.conf
        c['maxTaken'] = f.maxTaken.value()
        c['timer'] = f.showTimer.isChecked() and 1 or 0
        c['autoplay'] = f.autoplaySounds.isChecked()
        c['replayq'] = f.replayQuestion.isChecked()
        # description
        self.deck['desc'] = f.desc.toPlainText()
        self.mw.col.decks.save(self.deck)
        self.mw.col.decks.save(self.conf)

    def reject(self):
        self.accept()

    def accept(self):
        self.saveConf()
        self.mw.reset()
        QDialog.accept(self)

########NEW FILE########
__FILENAME__ = downloader
# Copyright: Damien Elmes <anki@ichi2.net>
# -*- coding: utf-8 -*-
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

import time, re, traceback
from aqt.qt import *
from anki.sync import httpCon
from aqt.utils import showWarning
from anki.hooks import addHook, remHook
import aqt.sync # monkey-patches httplib2

def download(mw, code):
    "Download addon/deck from AnkiWeb. On success caller must stop progress diag."
    # check code is valid
    try:
        code = int(code)
    except ValueError:
        showWarning(_("Invalid code."))
        return
    # create downloading thread
    thread = Downloader(code)
    def onRecv():
        mw.progress.update(label="%dKB downloaded" % (thread.recvTotal/1024))
    mw.connect(thread, SIGNAL("recv"), onRecv)
    thread.start()
    mw.progress.start(immediate=True)
    while not thread.isFinished():
        mw.app.processEvents()
        thread.wait(100)
    if not thread.error:
        # success
        return thread.data, thread.fname
    else:
        mw.progress.finish()
        showWarning(_("Download failed: %s") % thread.error)

class Downloader(QThread):

    def __init__(self, code):
        QThread.__init__(self)
        self.code = code
        self.error = None

    def run(self):
        # setup progress handler
        self.byteUpdate = time.time()
        self.recvTotal = 0
        def canPost():
            if (time.time() - self.byteUpdate) > 0.1:
                self.byteUpdate = time.time()
                return True
        def recvEvent(bytes):
            self.recvTotal += bytes
            if canPost():
                self.emit(SIGNAL("recv"))
        addHook("httpRecv", recvEvent)
        con =  httpCon()
        try:
            resp, cont = con.request(
                aqt.appShared + "download/%d" % self.code)
        except Exception, e:
            exc = traceback.format_exc()
            try:
                self.error = unicode(e[0], "utf8", "ignore")
            except:
                self.error = exc
            return
        finally:
            remHook("httpRecv", recvEvent)
        if resp['status'] == '200':
            self.error = None
            self.fname = re.match("attachment; filename=(.+)",
                                  resp['content-disposition']).group(1)
            self.data = cont
        elif resp['status'] == '403':
            self.error = _("Invalid code.")
        else:
            self.error = _("Error downloading: %s") % resp['status']

########NEW FILE########
__FILENAME__ = dyndeckconf
# Copyright: Damien Elmes <anki@ichi2.net>
# -*- coding: utf-8 -*-
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

from aqt.qt import *
import aqt
from anki.utils import ids2str, isWin, isMac
from aqt.utils import showInfo, showWarning, openHelp, getOnlyText, askUser
from operator import itemgetter

class DeckConf(QDialog):
    def __init__(self, mw, first=False, search="", deck=None):
        QDialog.__init__(self, mw)
        self.mw = mw
        self.deck = deck or self.mw.col.decks.current()
        self.search = search
        self.form = aqt.forms.dyndconf.Ui_Dialog()
        self.form.setupUi(self)
        if first:
            label = _("Build")
        else:
            label = _("Rebuild")
        self.ok = self.form.buttonBox.addButton(
            label, QDialogButtonBox.AcceptRole)
        self.mw.checkpoint(_("Options"))
        self.setWindowModality(Qt.WindowModal)
        self.connect(self.form.buttonBox,
                     SIGNAL("helpRequested()"),
                     lambda: openHelp("filtered"))
        self.setWindowTitle(_("Options for %s") % self.deck['name'])
        self.setupOrder()
        self.loadConf()
        if search:
            self.form.search.setText(search)
        self.form.search.selectAll()
        self.show()
        self.exec_()

    def setupOrder(self):
        import anki.consts as cs
        self.form.order.addItems(cs.dynOrderLabels().values())

    def loadConf(self):
        f = self.form
        d = self.deck
        search, limit, order = d['terms'][0]
        f.search.setText(search)
        if d['delays']:
            f.steps.setText(self.listToUser(d['delays']))
            f.stepsOn.setChecked(True)
        else:
            f.steps.setText("1 10")
            f.stepsOn.setChecked(False)
        f.resched.setChecked(d['resched'])
        f.order.setCurrentIndex(order)
        f.limit.setValue(limit)

    def saveConf(self):
        f = self.form
        d = self.deck
        d['delays'] = None
        if f.stepsOn.isChecked():
            steps = self.userToList(f.steps)
            if steps:
                d['delays'] = steps
        else:
            d['delays'] = None
        d['terms'][0] = [f.search.text(),
                         f.limit.value(),
                         f.order.currentIndex()]
        d['resched'] = f.resched.isChecked()
        self.mw.col.decks.save(d)
        return True

    def reject(self):
        self.ok = False
        QDialog.reject(self)

    def accept(self):
        if not self.saveConf():
            return
        if not self.mw.col.sched.rebuildDyn():
            if askUser(_("""\
The provided search did not match any cards. Would you like to revise \
it?""")):
                return
        self.mw.reset()
        QDialog.accept(self)

    # Step load/save - fixme: share with std options screen
    ########################################################

    def listToUser(self, l):
        return " ".join([str(x) for x in l])

    def userToList(self, w, minSize=1):
        items = unicode(w.text()).split(" ")
        ret = []
        for i in items:
            if not i:
                continue
            try:
                i = float(i)
                assert i > 0
                if i == int(i):
                    i = int(i)
                ret.append(i)
            except:
                # invalid, don't update
                showWarning(_("Steps must be numbers."))
                return
        if len(ret) < minSize:
            showWarning(_("At least one step is required."))
            return
        return ret

########NEW FILE########
__FILENAME__ = editcurrent
# Copyright: Damien Elmes <anki@ichi2.net>
# -*- coding: utf-8 -*-
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

from aqt.qt import *
import aqt.editor
from aqt.utils import saveGeom, restoreGeom
from anki.hooks import addHook, remHook
from anki.utils import isMac

class EditCurrent(QDialog):

    def __init__(self, mw):
        if isMac:
            # use a separate window on os x so we can a clean menu
            QDialog.__init__(self, None, Qt.Window)
        else:
            QDialog.__init__(self, mw)
        QDialog.__init__(self, None, Qt.Window)
        self.mw = mw
        self.form = aqt.forms.editcurrent.Ui_Dialog()
        self.form.setupUi(self)
        self.setWindowTitle(_("Edit Current"))
        self.setMinimumHeight(400)
        self.setMinimumWidth(500)
        self.connect(self,
                     SIGNAL("rejected()"),
                     self.onSave)
        self.editor = aqt.editor.Editor(self.mw, self.form.fieldsArea, self)
        self.editor.setNote(self.mw.reviewer.card.note())
        restoreGeom(self, "editcurrent")
        addHook("reset", self.onReset)
        self.mw.requireReset()
        self.show()
        # reset focus after open
        self.editor.web.setFocus()

    def onReset(self):
        # lazy approach for now: throw away edits
        try:
            n = self.mw.reviewer.card.note()
            n.load()
        except:
            # card's been deleted
            remHook("reset", self.onReset)
            self.editor.setNote(None)
            self.mw.reset()
            aqt.dialogs.close("EditCurrent")
            self.close()
            return
        self.editor.setNote(n)

    def onSave(self):
        remHook("reset", self.onReset)
        self.editor.saveNow()
        r = self.mw.reviewer
        try:
            r.card.load()
        except:
            # card was removed by clayout
            pass
        else:
            self.mw.reviewer.cardQueue.append(self.mw.reviewer.card)
        self.mw.moveToState("review")
        saveGeom(self, "editcurrent")
        aqt.dialogs.close("EditCurrent")

########NEW FILE########
__FILENAME__ = editor
# -*- coding: utf-8 -*-
# Copyright: Damien Elmes <anki@ichi2.net>
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

from aqt.qt import *
import re, os, sys, urllib2, ctypes, traceback
from anki.utils import stripHTML, isWin, isMac, namedtmp, json
from anki.sound import play
from anki.hooks import runHook, runFilter
from aqt.sound import getAudio
from aqt.webview import AnkiWebView
from aqt.utils import shortcut, showInfo, showWarning, getBase, getFile, \
    openHelp
import aqt
import anki.js
from BeautifulSoup import BeautifulSoup

# fixme: when tab order returns to the webview, the previously focused field
# is focused, which is not good when the user is tabbing through the dialog
# fixme: set rtl in div css

# fixme: commit from tag area causes error

pics = ("jpg", "jpeg", "png", "tif", "tiff", "gif", "svg")
audio =  ("wav", "mp3", "ogg", "flac")

_html = """
<html><head>%s<style>
.field {
  border: 1px solid #aaa; background:#fff; color:#000; padding: 5px;
}
/* prevent floated images from being displayed outside field */
.field:after {
    content: ".";
    display: block;
    height: 0;
    clear: both;
    visibility: hidden;
}
.fname { vertical-align: middle; padding: 0; }
img { max-width: 90%%; }
body { margin: 5px; }
</style><script>
%s

var currentField = null;
var changeTimer = null;
var dropTarget = null;

String.prototype.format = function() {
    var args = arguments;
    return this.replace(/\{\d+\}/g, function(m){
            return args[m.match(/\d+/)]; });
};

function onKey() {
    // esc clears focus, allowing dialog to close
    if (window.event.which == 27) {
        currentField.blur();
        return;
    }
    clearChangeTimer();
    if (currentField.innerHTML == "<div><br></div>") {
        // fix empty div bug. slight flicker, but must be done in a timer
        changeTimer = setTimeout(function () {
            currentField.innerHTML = "<br>";
            sendState();
            saveField("key"); }, 1);
    } else {
        changeTimer = setTimeout(function () {
            sendState();
            saveField("key"); }, 600);
    }
};

function sendState() {
    var r = {
        'bold': document.queryCommandState("bold"),
        'italic': document.queryCommandState("italic"),
        'under': document.queryCommandState("underline"),
        'super': document.queryCommandState("superscript"),
        'sub': document.queryCommandState("subscript"),
        'col': document.queryCommandValue("forecolor")
    };
    py.run("state:" + JSON.stringify(r));
};

function setFormat(cmd, arg, nosave) {
    document.execCommand(cmd, false, arg);
    if (!nosave) {
        saveField('key');
    }
};

function clearChangeTimer() {
    if (changeTimer) {
        clearTimeout(changeTimer);
        changeTimer = null;
    }
};

function onFocus(elem) {
    currentField = elem;
    py.run("focus:" + currentField.id.substring(1));
    // don't adjust cursor on mouse clicks
    if (mouseDown) { return; }
    // do this twice so that there's no flicker on newer versions
    caretToEnd();
    // need to do this in a timeout for older qt versions
    setTimeout(function () { caretToEnd() }, 1);
    // scroll if bottom of element off the screen
    function pos(obj) {
    	var cur = 0;
        do {
          cur += obj.offsetTop;
         } while (obj = obj.offsetParent);
    	return cur;
    }
    var y = pos(elem);
    if ((window.pageYOffset+window.innerHeight) < (y+elem.offsetHeight) ||
        window.pageYOffset > y) {
        window.scroll(0,y+elem.offsetHeight-window.innerHeight);
    }
}

function focusField(n) {
    $("#f"+n).focus();
}

function onDragOver(elem) {
    // if we focus the target element immediately, the drag&drop turns into a
    // copy, so note it down for later instead
    dropTarget = elem;
}

function caretToEnd() {
    var r = document.createRange()
    r.selectNodeContents(currentField);
    r.collapse(false);
    var s = document.getSelection();
    s.removeAllRanges();
    s.addRange(r);
};

function onBlur() {
    if (currentField) {
        saveField("blur");
    }
    clearChangeTimer();
    // if we lose focus, assume the last field is still targeted
    //currentField = null;
};

function saveField(type) {
    if (!currentField) {
        // no field has been focused yet
        return;
    }
    // type is either 'blur' or 'key'
    py.run(type + ":" + currentField.innerHTML);
    clearChangeTimer();
};

function wrappedExceptForWhitespace(text, front, back) {
    var match = text.match(/^(\s*)([^]*?)(\s*)$/);
    return match[1] + front + match[2] + back + match[3];
};

function wrap(front, back) {
    var s = window.getSelection();
    var r = s.getRangeAt(0);
    var content = r.cloneContents();
    var span = document.createElement("span")
    span.appendChild(content);
    var new_ = wrappedExceptForWhitespace(span.innerHTML, front, back);
    setFormat("inserthtml", new_);
    if (!span.innerHTML) {
        // run with an empty selection; move cursor back past postfix
        r = s.getRangeAt(0);
        r.setStart(r.startContainer, r.startOffset - back.length);
        r.collapse(true);
        s.removeAllRanges();
        s.addRange(r);
    }
};

function setFields(fields, focusTo) {
    var txt = "";
    for (var i=0; i<fields.length; i++) {
        var n = fields[i][0];
        var f = fields[i][1];
        if (!f) {
            f = "<br>";
        }
        txt += "<tr><td class=fname>{0}</td></tr><tr><td width=100%%>".format(n);
        txt += "<div id=f{0} onkeydown='onKey();' onmouseup='onKey();'".format(i);
        txt += " onfocus='onFocus(this);' onblur='onBlur();' class=field ";
        txt += "ondragover='onDragOver(this);' ";
        txt += "contentEditable=true class=field>{0}</div>".format(f);
        txt += "</td></tr>";
    }
    $("#fields").html("<table cellpadding=0 width=100%%>"+txt+"</table>");
    if (!focusTo) {
        focusTo = 0;
    }
    if (focusTo >= 0) {
        $("#f"+focusTo).focus();
    }
};

function setBackgrounds(cols) {
    for (var i=0; i<cols.length; i++) {
        $("#f"+i).css("background", cols[i]);
    }
}

function setFonts(fonts) {
    for (var i=0; i<fonts.length; i++) {
        $("#f"+i).css("font-family", fonts[i][0]);
        $("#f"+i).css("font-size", fonts[i][1]);
        $("#f"+i)[0].dir = fonts[i][2] ? "rtl" : "ltr";
    }
}

function showDupes() {
    $("#dupes").show();
}

function hideDupes() {
    $("#dupes").hide();
}

var mouseDown = 0;

$(function () {
document.body.onmousedown = function () {
    mouseDown++;
}

document.body.onmouseup = function () {
    mouseDown--;
}

document.onclick = function (evt) {
    var src = window.event.srcElement;
    if (src.tagName == "IMG") {
        // image clicked; find contenteditable parent
        var p = src;
        while (p = p.parentNode) {
            if (p.className == "field") {
                $("#"+p.id).focus();
                break;
            }
        }
    }
}

});

</script></head><body>
<div id="fields"></div>
<div id="dupes"><a href="#" onclick="py.run('dupes');return false;">%s</a></div>
</body></html>
"""

def _filterHTML(html):
    doc = BeautifulSoup(html)
    # filter out implicit formatting from webkit
    for tag in doc("span", "Apple-style-span"):
        preserve = ""
        for item in tag['style'].split(";"):
            try:
                k, v = item.split(":")
            except ValueError:
                continue
            if k.strip() == "color" and not v.strip() == "rgb(0, 0, 0)":
                preserve += "color:%s;" % v
        if preserve:
            # preserve colour attribute, delete implicit class
            tag.attrs = ((u"style", preserve),)
            del tag['class']
        else:
            # strip completely
            tag.replaceWithChildren()
    for tag in doc("font", "Apple-style-span"):
        # strip all but colour attr from implicit font tags
        if 'color' in dict(tag.attrs):
            tag.attrs = ((u"color", tag['color']),)
            # and apple class
            del tag['class']
        else:
            # remove completely
            tag.replaceWithChildren()
    # turn file:/// links into relative ones
    for tag in doc("img"):
        try:
            if tag['src'].lower().startswith("file://"):
                tag['src'] = os.path.basename(tag['src'])
        except KeyError:
            # for some bizarre reason, mnemosyne removes src elements
            # from missing media
            pass
    # strip superfluous elements
    for elem in "html", "head", "body", "meta":
        for tag in doc(elem):
            tag.replaceWithChildren()
    html = unicode(doc)
    return html

# caller is responsible for resetting note on reset
class Editor(object):
    def __init__(self, mw, widget, parentWindow, addMode=False):
        self.mw = mw
        self.widget = widget
        self.parentWindow = parentWindow
        self.note = None
        self.stealFocus = True
        self.addMode = addMode
        self._loaded = False
        self.currentField = 0
        # current card, for card layout
        self.card = None
        self.setupOuter()
        self.setupButtons()
        self.setupWeb()
        self.setupTags()
        self.setupKeyboard()

    # Initial setup
    ############################################################

    def setupOuter(self):
        l = QVBoxLayout()
        l.setMargin(0)
        l.setSpacing(0)
        self.widget.setLayout(l)
        self.outerLayout = l

    def setupWeb(self):
        self.web = EditorWebView(self.widget, self)
        self.web.allowDrops = True
        self.web.setBridge(self.bridge)
        self.outerLayout.addWidget(self.web, 1)
        # pick up the window colour
        p = self.web.palette()
        p.setBrush(QPalette.Base, Qt.transparent)
        self.web.page().setPalette(p)
        self.web.setAttribute(Qt.WA_OpaquePaintEvent, False)

    # Top buttons
    ######################################################################

    def _addButton(self, name, func, key=None, tip=None, size=True, text="",
                   check=False, native=False, canDisable=True):
        b = QPushButton(text)
        if check:
            b.connect(b, SIGNAL("clicked(bool)"), func)
        else:
            b.connect(b, SIGNAL("clicked()"), func)
        if size:
            b.setFixedHeight(20)
            b.setFixedWidth(20)
        if not native:
            b.setStyle(self.plastiqueStyle)
            b.setFocusPolicy(Qt.NoFocus)
        else:
            b.setAutoDefault(False)
        if not text:
            b.setIcon(QIcon(":/icons/%s.png" % name))
        if key:
            b.setShortcut(QKeySequence(key))
        if tip:
            b.setToolTip(shortcut(tip))
        if check:
            b.setCheckable(True)
        self.iconsBox.addWidget(b)
        if canDisable:
            self._buttons[name] = b
        return b

    def setupButtons(self):
        self._buttons = {}
        # button styles for mac
        self.plastiqueStyle = QStyleFactory.create("plastique")
        self.widget.setStyle(self.plastiqueStyle)
        # icons
        self.iconsBox = QHBoxLayout()
        if not isMac:
            self.iconsBox.setMargin(6)
        else:
            self.iconsBox.setMargin(0)
        self.iconsBox.setSpacing(0)
        self.outerLayout.addLayout(self.iconsBox)
        b = self._addButton
        b("fields", self.onFields, "",
          shortcut(_("Customize Fields")), size=False, text=_("Fields..."),
          native=True, canDisable=False)
        self.iconsBox.addItem(QSpacerItem(6,1, QSizePolicy.Fixed))
        b("layout", self.onCardLayout, _("Ctrl+L"),
          shortcut(_("Customize Cards (Ctrl+L)")),
          size=False, text=_("Cards..."), native=True, canDisable=False)
        # align to right
        self.iconsBox.addItem(QSpacerItem(20,1, QSizePolicy.Expanding))
        b("text_bold", self.toggleBold, _("Ctrl+B"), _("Bold text (Ctrl+B)"),
          check=True)
        b("text_italic", self.toggleItalic, _("Ctrl+I"), _("Italic text (Ctrl+I)"),
          check=True)
        b("text_under", self.toggleUnderline, _("Ctrl+U"),
          _("Underline text (Ctrl+U)"), check=True)
        b("text_super", self.toggleSuper, _("Ctrl+="),
          _("Superscript (Ctrl+=)"), check=True)
        b("text_sub", self.toggleSub, _("Ctrl+Shift+="),
          _("Subscript (Ctrl+Shift+=)"), check=True)
        b("text_clear", self.removeFormat, _("Ctrl+R"),
          _("Remove formatting (Ctrl+R)"))
        but = b("foreground", self.onForeground, _("F7"), text=" ")
        but.setToolTip(_("Set foreground colour (F7)"))
        self.setupForegroundButton(but)
        but = b("change_colour", self.onChangeCol, _("F8"),
          _("Change colour (F8)"), text=u"▾")
        but.setFixedWidth(12)
        but = b("cloze", self.onCloze, _("Ctrl+Shift+C"),
                _("Cloze deletion (Ctrl+Shift+C)"), text="[...]")
        but.setFixedWidth(24)
        s = self.clozeShortcut2 = QShortcut(
            QKeySequence(_("Ctrl+Alt+Shift+C")), self.parentWindow)
        s.connect(s, SIGNAL("activated()"), self.onCloze)
        # fixme: better image names
        b("mail-attachment", self.onAddMedia, _("F3"),
          _("Attach pictures/audio/video (F3)"))
        b("media-record", self.onRecSound, _("F5"), _("Record audio (F5)"))
        b("adv", self.onAdvanced, text=u"▾")
        s = QShortcut(QKeySequence("Ctrl+T, T"), self.widget)
        s.connect(s, SIGNAL("activated()"), self.insertLatex)
        s = QShortcut(QKeySequence("Ctrl+T, E"), self.widget)
        s.connect(s, SIGNAL("activated()"), self.insertLatexEqn)
        s = QShortcut(QKeySequence("Ctrl+T, M"), self.widget)
        s.connect(s, SIGNAL("activated()"), self.insertLatexMathEnv)
        s = QShortcut(QKeySequence("Ctrl+Shift+X"), self.widget)
        s.connect(s, SIGNAL("activated()"), self.onHtmlEdit)
        runHook("setupEditorButtons", self)

    def enableButtons(self, val=True):
        for b in self._buttons.values():
            b.setEnabled(val)

    def disableButtons(self):
        self.enableButtons(False)

    def onFields(self):
        from aqt.fields import FieldDialog
        self.saveNow()
        FieldDialog(self.mw, self.note, parent=self.parentWindow)

    def onCardLayout(self):
        from aqt.clayout import CardLayout
        self.saveNow()
        if self.card:
            ord = self.card.ord
        else:
            ord = 0
        CardLayout(self.mw, self.note, ord=ord, parent=self.parentWindow,
               addMode=self.addMode)
        self.loadNote()

    # JS->Python bridge
    ######################################################################

    def bridge(self, str):
        if not self.note or not runHook:
            # shutdown
            return
        # focus lost or key/button pressed?
        if str.startswith("blur") or str.startswith("key"):
            (type, txt) = str.split(":", 1)
            txt = self.mungeHTML(txt)
            # misbehaving apps may include a null byte in the text
            txt = txt.replace("\x00", "")
            # reverse the url quoting we added to get images to display
            txt = unicode(urllib2.unquote(
                txt.encode("utf8")), "utf8", "replace")
            self.note.fields[self.currentField] = txt
            if not self.addMode:
                self.note.flush()
                self.mw.requireReset()
            if type == "blur":
                self.disableButtons()
                # run any filters
                if runFilter(
                    "editFocusLost", False, self.note, self.currentField):
                    # something updated the note; schedule reload
                    def onUpdate():
                        self.loadNote()
                        self.checkValid()
                    self.mw.progress.timer(100, onUpdate, False)
                else:
                    self.checkValid()
            else:
                runHook("editTimer", self.note)
                self.checkValid()
        # focused into field?
        elif str.startswith("focus"):
            (type, num) = str.split(":", 1)
            self.enableButtons()
            self.currentField = int(num)
        # state buttons changed?
        elif str.startswith("state"):
            (cmd, txt) = str.split(":", 1)
            r = json.loads(txt)
            self._buttons['text_bold'].setChecked(r['bold'])
            self._buttons['text_italic'].setChecked(r['italic'])
            self._buttons['text_under'].setChecked(r['under'])
            self._buttons['text_super'].setChecked(r['super'])
            self._buttons['text_sub'].setChecked(r['sub'])
        elif str.startswith("dupes"):
            self.showDupes()
        else:
            print str

    def mungeHTML(self, txt):
        if txt == "<br>":
            txt = ""
        return _filterHTML(txt)

    # Setting/unsetting the current note
    ######################################################################

    def _loadFinished(self, w):
        self._loaded = True
        if self.note:
            self.loadNote()

    def setNote(self, note, hide=True, focus=False):
        "Make NOTE the current note."
        self.note = note
        self.currentField = 0
        # change timer
        if self.note:
            self.web.setHtml(_html % (
                getBase(self.mw.col), anki.js.jquery,
                _("Show Duplicates")), loadCB=self._loadFinished)
            self.updateTags()
            self.updateKeyboard()
        else:
            self.hideCompleters()
            if hide:
                self.widget.hide()

    def loadNote(self):
        if not self.note:
            return
        if self.stealFocus:
            field = self.currentField
        else:
            field = -1
        if not self._loaded:
            # will be loaded when page is ready
            return
        data = []
        for fld, val in self.note.items():
            data.append((fld, self.mw.col.media.escapeImages(val)))
        self.web.eval("setFields(%s, %d);" % (
            json.dumps(data), field))
        self.web.eval("setFonts(%s);" % (
            json.dumps(self.fonts())))
        self.checkValid()
        self.widget.show()
        if self.stealFocus:
            self.web.setFocus()

    def focus(self):
        self.web.setFocus()

    def fonts(self):
        return [(f['font'], f['size'], f['rtl'])
                for f in self.note.model()['flds']]

    def saveNow(self):
        "Must call this before adding cards, closing dialog, etc."
        if not self.note:
            return
        self.saveTags()
        if self.mw.app.focusWidget() != self.web:
            # if no fields are focused, there's nothing to save
            return
        # move focus out of fields and save tags
        self.parentWindow.setFocus()
        # and process events so any focus-lost hooks fire
        self.mw.app.processEvents()

    def checkValid(self):
        cols = []
        err = None
        for f in self.note.fields:
            cols.append("#fff")
        err = self.note.dupeOrEmpty()
        if err == 2:
            cols[0] = "#fcc"
            self.web.eval("showDupes();")
        else:
            self.web.eval("hideDupes();")
        self.web.eval("setBackgrounds(%s);" % json.dumps(cols))

    def showDupes(self):
        contents = self.note.fields[0]
        browser = aqt.dialogs.open("Browser", self.mw)
        browser.form.searchEdit.lineEdit().setText(
            "'note:%s' '%s:%s'" % (
                self.note.model()['name'],
                self.note.model()['flds'][0]['name'],
                contents))
        browser.onSearch()

    def fieldsAreBlank(self):
        if not self.note:
            return True
        for f in self.note.fields:
            if f:
                return False
        return True

    # HTML editing
    ######################################################################

    def onHtmlEdit(self):
        self.saveNow()
        d = QDialog(self.widget)
        form = aqt.forms.edithtml.Ui_Dialog()
        form.setupUi(d)
        d.connect(form.buttonBox, SIGNAL("helpRequested()"),
                 lambda: openHelp("editor"))
        form.textEdit.setPlainText(self.note.fields[self.currentField])
        form.textEdit.moveCursor(QTextCursor.End)
        d.exec_()
        html = form.textEdit.toPlainText()
        # filter html through beautifulsoup so we can strip out things like a
        # leading </div>
        html = unicode(BeautifulSoup(html))
        self.note.fields[self.currentField] = html
        self.loadNote()
        # focus field so it's saved
        self.web.setFocus()
        self.web.eval("focusField(%d);" % self.currentField)

    # Tag handling
    ######################################################################

    def setupTags(self):
        import aqt.tagedit
        g = QGroupBox(self.widget)
        g.setFlat(True)
        tb = QGridLayout()
        tb.setSpacing(12)
        tb.setMargin(6)
        # tags
        l = QLabel(_("Tags"))
        tb.addWidget(l, 1, 0)
        self.tags = aqt.tagedit.TagEdit(self.widget)
        self.tags.connect(self.tags, SIGNAL("lostFocus"),
                          self.saveTags)
        tb.addWidget(self.tags, 1, 1)
        g.setLayout(tb)
        self.outerLayout.addWidget(g)

    def updateTags(self):
        if self.tags.col != self.mw.col:
            self.tags.setCol(self.mw.col)
        if not self.tags.text() or not self.addMode:
            self.tags.setText(self.note.stringTags().strip())

    def saveTags(self):
        if not self.note:
            return
        self.note.tags = self.mw.col.tags.split(self.tags.text())
        if not self.addMode:
            self.note.flush()
        runHook("tagsUpdated", self.note)

    def saveAddModeVars(self):
        if self.addMode:
            # save tags to model
            m = self.note.model()
            m['tags'] = self.note.tags
            self.mw.col.models.save(m)

    def hideCompleters(self):
        self.tags.hideCompleter()

    # Format buttons
    ######################################################################

    def toggleBold(self, bool):
        self.web.eval("setFormat('bold');")

    def toggleItalic(self, bool):
        self.web.eval("setFormat('italic');")

    def toggleUnderline(self, bool):
        self.web.eval("setFormat('underline');")

    def toggleSuper(self, bool):
        self.web.eval("setFormat('superscript');")

    def toggleSub(self, bool):
        self.web.eval("setFormat('subscript');")

    def removeFormat(self):
        self.web.eval("setFormat('removeFormat');")

    def onCloze(self):
        # check that the model is set up for cloze deletion
        if '{{cloze:' not in self.note.model()['tmpls'][0]['qfmt']:
            if self.addMode:
                showInfo(_("""\
To use this button, please select the Cloze note type. To learn more, \
please click the help button."""), help="cloze")
            else:
                showInfo(_("""\
To make a cloze deletion on an existing note, you need to change it \
to a cloze type first, via Edit>Change Note Type."""))
            return
        # find the highest existing cloze
        highest = 0
        for name, val in self.note.items():
            m = re.findall("\{\{c(\d+)::", val)
            if m:
                highest = max(highest, sorted([int(x) for x in m])[-1])
        # reuse last?
        if not self.mw.app.keyboardModifiers() & Qt.AltModifier:
            highest += 1
        # must start at 1
        highest = max(1, highest)
        self.web.eval("wrap('{{c%d::', '}}');" % highest)

    # Foreground colour
    ######################################################################

    def setupForegroundButton(self, but):
        self.foregroundFrame = QFrame()
        self.foregroundFrame.setAutoFillBackground(True)
        self.foregroundFrame.setFocusPolicy(Qt.NoFocus)
        self.fcolour = self.mw.pm.profile.get("lastColour", "#00f")
        self.onColourChanged()
        hbox = QHBoxLayout()
        hbox.addWidget(self.foregroundFrame)
        hbox.setMargin(5)
        but.setLayout(hbox)

    # use last colour
    def onForeground(self):
        self._wrapWithColour(self.fcolour)

    # choose new colour
    def onChangeCol(self):
        new = QColorDialog.getColor(QColor(self.fcolour), None)
        # native dialog doesn't refocus us for some reason
        self.parentWindow.activateWindow()
        if new.isValid():
            self.fcolour = new.name()
            self.onColourChanged()
            self._wrapWithColour(self.fcolour)

    def _updateForegroundButton(self):
        self.foregroundFrame.setPalette(QPalette(QColor(self.fcolour)))

    def onColourChanged(self):
        self._updateForegroundButton()
        self.mw.pm.profile['lastColour'] = self.fcolour

    def _wrapWithColour(self, colour):
        self.web.eval("setFormat('forecolor', '%s')" % colour)

    # Audio/video/images
    ######################################################################

    def onAddMedia(self):
        key = (_("Media") +
               " (*.jpg *.png *.gif *.tiff *.svg *.tif *.jpeg "+
               "*.mp3 *.ogg *.wav *.avi *.ogv *.mpg *.mpeg *.mov *.mp4 " +
               "*.mkv *.ogx *.ogv *.oga *.flv *.swf *.flac)")
        def accept(file):
            self.addMedia(file, canDelete=True)
        file = getFile(self.widget, _("Add Media"), accept, key, key="media")
        self.parentWindow.activateWindow()

    def addMedia(self, path, canDelete=False):
        html = self._addMedia(path, canDelete)
        self.web.eval("setFormat('inserthtml', %s);" % json.dumps(html))

    def _addMedia(self, path, canDelete=False):
        "Add to media folder and return basename."
        # copy to media folder
        name = self.mw.col.media.addFile(path)
        # remove original?
        if canDelete and self.mw.pm.profile['deleteMedia']:
            if os.path.abspath(name) != os.path.abspath(path):
                try:
                    os.unlink(path)
                except:
                    pass
        # return a local html link
        ext = name.split(".")[-1].lower()
        if ext in pics:
            return '<img src="%s">' % name
        else:
            anki.sound.play(name)
            return '[sound:%s]' % name

    def onRecSound(self):
        try:
            file = getAudio(self.widget)
        except Exception, e:
            showWarning(_(
                "Couldn't record audio. Have you installed lame and sox?") +
                        "\n\n" + unicode(e))
            return
        self.addMedia(file)

    # Advanced menu
    ######################################################################

    def onAdvanced(self):
        m = QMenu(self.mw)
        a = m.addAction(_("LaTeX"))
        a.setShortcut(QKeySequence("Ctrl+T, T"))
        a.connect(a, SIGNAL("triggered()"), self.insertLatex)
        a = m.addAction(_("LaTeX equation"))
        a.setShortcut(QKeySequence("Ctrl+T, E"))
        a.connect(a, SIGNAL("triggered()"), self.insertLatexEqn)
        a = m.addAction(_("LaTeX math env."))
        a.setShortcut(QKeySequence("Ctrl+T, M"))
        a.connect(a, SIGNAL("triggered()"), self.insertLatexMathEnv)
        a = m.addAction(_("Edit HTML"))
        a.setShortcut(QKeySequence("Ctrl+Shift+X"))
        a.connect(a, SIGNAL("triggered()"), self.onHtmlEdit)
        m.exec_(QCursor.pos())

    # LaTeX
    ######################################################################

    def insertLatex(self):
        self.web.eval("wrap('[latex]', '[/latex]');")

    def insertLatexEqn(self):
        self.web.eval("wrap('[$]', '[/$]');")

    def insertLatexMathEnv(self):
        self.web.eval("wrap('[$$]', '[/$$]');")

    # Keyboard layout
    ######################################################################

    def setupKeyboard(self):
        if isWin and self.mw.pm.profile['preserveKeyboard']:
            a = ctypes.windll.user32.ActivateKeyboardLayout
            a.restype = ctypes.c_void_p
            a.argtypes = [ctypes.c_void_p, ctypes.c_uint]
            g = ctypes.windll.user32.GetKeyboardLayout
            g.restype = ctypes.c_void_p
            g.argtypes = [ctypes.c_uint]
        else:
            a = g = None
        self.activateKeyboard = a
        self.getKeyboard = g

    def updateKeyboard(self):
        self.keyboardLayouts = {}

    def saveKeyboard(self):
        if not self.getKeyboard:
            return
        self.keyboardLayouts[self.currentField] = self.getKeyboard(0)

    def restoreKeyboard(self):
        if not self.getKeyboard:
            return
        if self.currentField in self.keyboardLayouts:
            self.activateKeyboard(self.keyboardLayouts[self.currentField], 0)

# Pasting, drag & drop, and keyboard layouts
######################################################################

class EditorWebView(AnkiWebView):

    def __init__(self, parent, editor):
        AnkiWebView.__init__(self)
        self.editor = editor
        self.errtxt = _("An error occured while opening %s")
        self.strip = self.editor.mw.pm.profile['stripHTML']

    def keyPressEvent(self, evt):
        if evt.matches(QKeySequence.Paste):
            self.onPaste()
            return evt.accept()
        elif evt.matches(QKeySequence.Copy):
            self.onCopy()
            return evt.accept()
        elif evt.matches(QKeySequence.Cut):
            self.onCut()
            return evt.accept()
        QWebView.keyPressEvent(self, evt)

    def onCut(self):
        self.triggerPageAction(QWebPage.Cut)
        self._flagAnkiText()

    def onCopy(self):
        self.triggerPageAction(QWebPage.Copy)
        self._flagAnkiText()

    def onPaste(self):
        mime = self.prepareClip()
        self.triggerPageAction(QWebPage.Paste)
        self.restoreClip(mime)

    def mouseReleaseEvent(self, evt):
        if not isMac and not isWin and evt.button() == Qt.MidButton:
            # middle click on x11; munge the clipboard before standard
            # handling
            mime = self.prepareClip(mode=QClipboard.Selection)
            AnkiWebView.mouseReleaseEvent(self, evt)
            self.restoreClip(mime, mode=QClipboard.Selection)
        else:
            AnkiWebView.mouseReleaseEvent(self, evt)

    def focusInEvent(self, evt):
        window = False
        if evt.reason() in (Qt.ActiveWindowFocusReason, Qt.PopupFocusReason):
            # editor area got focus again; need to tell js not to adjust cursor
            self.eval("mouseDown++;")
            window = True
        AnkiWebView.focusInEvent(self, evt)
        if evt.reason() == Qt.TabFocusReason:
            self.eval("focusField(0);")
        elif evt.reason() == Qt.BacktabFocusReason:
            n = len(self.editor.note.fields) - 1
            self.eval("focusField(%d);" % n)
        elif window:
            self.eval("mouseDown--;")

    def dropEvent(self, evt):
        oldmime = evt.mimeData()
        # coming from this program?
        if evt.source():
            if oldmime.hasHtml():
                mime = QMimeData()
                mime.setHtml(_filterHTML(oldmime.html()))
            else:
                # old qt on linux won't give us html when dragging an image;
                # in that case just do the default action (which is to ignore
                # the drag)
                return AnkiWebView.dropEvent(self, evt)
        else:
            mime = self._processMime(oldmime)
        # create a new event with the new mime data and run it
        new = QDropEvent(evt.pos(), evt.possibleActions(), mime,
                         evt.mouseButtons(), evt.keyboardModifiers())
        evt.accept()
        QWebView.dropEvent(self, new)
        # tell the drop target to take focus so the drop contents are saved
        self.eval("dropTarget.focus();")
        self.setFocus()

    def prepareClip(self, mode=QClipboard.Clipboard):
        clip = self.editor.mw.app.clipboard()
        mime = clip.mimeData(mode=mode)
        if mime.hasHtml() and mime.html().startswith("<!--anki-->"):
            # pasting from another field, filter extraneous webkit formatting
            html = mime.html()[11:]
            html = _filterHTML(html)
            mime.setHtml(html)
            return
        self.saveClip(mode=mode)
        mime = self._processMime(mime)
        clip.setMimeData(mime, mode=mode)

    def restoreClip(self, mime, mode=QClipboard.Clipboard):
        if not mime:
            return
        clip = self.editor.mw.app.clipboard()
        clip.setMimeData(mime, mode=mode)

    def saveClip(self, mode):
        # we don't own the clipboard object, so we need to copy it
        mime = self.editor.mw.app.clipboard().mimeData(mode=mode)
        n = QMimeData()
        if mime.hasText():
            n.setText(mime.text())
        if mime.hasHtml():
            n.setHtml(mime.html())
        if mime.hasUrls():
            n.setUrls(mime.urls())
        if mime.hasImage():
            n.setImageData(mime.imageData())
        return n

    def _processMime(self, mime):
        # print "html=%s image=%s urls=%s txt=%s" % (
        #     mime.hasHtml(), mime.hasImage(), mime.hasUrls(), mime.hasText())
        # print "html", mime.html()
        # print "urls", mime.urls()
        # print "text", mime.text()
        if mime.hasImage():
            return self._processImage(mime)
        elif mime.hasUrls():
            return self._processUrls(mime)
        elif mime.hasText() and (self.strip or not mime.hasHtml()):
            return self._processText(mime)
        elif mime.hasHtml():
            return self._processHtml(mime)
        else:
            # nothing
            return QMimeData()

    def _processUrls(self, mime):
        url = mime.urls()[0].toString()
        link = self._localizedMediaLink(url)
        mime = QMimeData()
        mime.setHtml(link)
        return mime

    def _localizedMediaLink(self, url):
        l = url.lower()
        for suffix in pics+audio:
            if l.endswith(suffix):
                return self._retrieveURL(url)
        # not a supported type; return link verbatim
        return url

    def _processText(self, mime):
        txt = unicode(mime.text())
        l = txt.lower()
        html = None
        # if the user is pasting an image or sound link, convert it to local
        if l.startswith("http://") or l.startswith("https://") or l.startswith("file://"):
            txt = txt.split("\r\n")[0]
            html = self._localizedMediaLink(txt)
            if html == txt:
                # wasn't of a supported media type; don't change
                html = None
        new = QMimeData()
        if html:
            new.setHtml(html)
        else:
            new.setText(mime.text())
        return new

    def _processHtml(self, mime):
        html = mime.html()
        if self.strip:
            html = stripHTML(html)
        else:
            html = _filterHTML(html)
        mime = QMimeData()
        mime.setHtml(html)
        return mime

    def _processImage(self, mime):
        im = QImage(mime.imageData())
        uname = namedtmp("paste-%d" % im.cacheKey())
        if self.editor.mw.pm.profile.get("pastePNG", False):
            ext = ".png"
            im.save(uname+ext, None, 50)
        else:
            ext = ".jpg"
            im.save(uname+ext, None, 80)
        # invalid image?
        if not os.path.exists(uname+ext):
            return QMimeData()
        mime = QMimeData()
        mime.setHtml(self.editor._addMedia(uname+ext))
        return mime

    def _retrieveURL(self, url):
        # is it media?
        ext = url.split(".")[-1].lower()
        if ext not in pics and ext not in audio:
            return
        # fetch it into a temporary folder
        self.editor.mw.progress.start(immediate=True)
        try:
            req = urllib2.Request(url, None, {
                'User-Agent': 'Mozilla/5.0 (compatible; Anki)'})
            filecontents = urllib2.urlopen(req).read()
        except urllib2.URLError, e:
            showWarning(self.errtxt % e)
            return
        path = namedtmp(os.path.basename(url))
        file = open(path, "wb")
        file.write(filecontents)
        file.close()
        self.editor.mw.progress.finish()
        return self.editor._addMedia(path)

    def _flagAnkiText(self):
        # add a comment in the clipboard html so we can tell text is copied
        # from us and doesn't need to be stripped
        clip = self.editor.mw.app.clipboard()
        mime = clip.mimeData()
        if not mime.hasHtml():
            return
        html = mime.html()
        mime.setHtml("<!--anki-->" + mime.html())

    def contextMenuEvent(self, evt):
        m = QMenu(self)
        a = m.addAction(_("Cut"))
        a.connect(a, SIGNAL("activated()"), self.onCut)
        a = m.addAction(_("Copy"))
        a.connect(a, SIGNAL("activated()"), self.onCopy)
        a = m.addAction(_("Paste"))
        a.connect(a, SIGNAL("activated()"), self.onPaste)
        m.popup(QCursor.pos())

########NEW FILE########
__FILENAME__ = errors
# Copyright: Damien Elmes <anki@ichi2.net>
# -*- coding: utf-8 -*-
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

from aqt.qt import *
import sys
from aqt.utils import showText, showWarning

class ErrorHandler(QObject):
    "Catch stderr and write into buffer."
    ivl = 100

    def __init__(self, mw):
        QObject.__init__(self, mw)
        self.mw = mw
        self.timer = None
        self.connect(self, SIGNAL("errorTimer"), self._setTimer)
        self.pool = ""
        sys.stderr = self

    def write(self, data):
        # make sure we have unicode
        if not isinstance(data, unicode):
            data = unicode(data, "utf8", "replace")
        # dump to stdout
        sys.stdout.write(data.encode("utf-8"))
        # save in buffer
        self.pool += data
        # and update timer
        self.setTimer()

    def setTimer(self):
        # we can't create a timer from a different thread, so we post a
        # message to the object on the main thread
        self.emit(SIGNAL("errorTimer"))

    def _setTimer(self):
        if not self.timer:
            self.timer = QTimer(self.mw)
            self.mw.connect(self.timer, SIGNAL("timeout()"), self.onTimeout)
        self.timer.setInterval(self.ivl)
        self.timer.setSingleShot(True)
        self.timer.start()

    def onTimeout(self):
        error = self.pool
        self.pool = ""
        self.mw.progress.clear()
        if "abortSchemaMod" in error:
            return
        if "Pyaudio not" in error:
            return showWarning(_("Please install PyAudio"))
        if "install mplayer" in error:
            return showWarning(_("Please install mplayer"))
        if "no default output" in error:
            return showWarning(_("Please connect a microphone."))
        stdText = _("""\
An error occurred. It may have been caused by a harmless bug, <br>
or your deck may have a problem.
<p>To confirm it's not a problem with your deck, please run
<b>Tools > Maintenance > Check Database</b>.
<p>If that doesn't fix the problem, please copy the following<br>
into a bug report:""")
        pluginText = _("""\
An error occurred in an add-on. Please contact the add-on author.<br>""")
        if "addon" in error:
            txt = pluginText
        else:
            txt = stdText
        # show dialog
        txt = txt + "<div style='white-space: pre-wrap'>" + error + "</div>"
        showText(txt, type="html")

########NEW FILE########
__FILENAME__ = exporting
# Copyright: Damien Elmes <anki@ichi2.net>
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

import os
from aqt.qt import *
import anki, aqt, aqt.tagedit
from aqt.utils import getSaveFile, tooltip, showWarning, askUser
from anki.exporting import exporters

class ExportDialog(QDialog):

    def __init__(self, mw):
        QDialog.__init__(self, mw, Qt.Window)
        self.mw = mw
        self.col = mw.col
        self.frm = aqt.forms.exporting.Ui_ExportDialog()
        self.frm.setupUi(self)
        self.exporter = None
        self.setup()
        self.exec_()

    def setup(self):
        self.frm.format.insertItems(0, list(zip(*exporters())[0]))
        self.connect(self.frm.format, SIGNAL("activated(int)"),
                     self.exporterChanged)
        self.exporterChanged(0)
        self.decks = [_("All Decks")] + sorted(self.col.decks.allNames())
        self.frm.deck.addItems(self.decks)
        # save button
        b = QPushButton(_("Export..."))
        self.frm.buttonBox.addButton(b, QDialogButtonBox.AcceptRole)

    def exporterChanged(self, idx):
        self.exporter = exporters()[idx][1](self.col)
        self.isApkg = hasattr(self.exporter, "includeSched")
        self.frm.includeSched.setShown(self.isApkg)
        self.frm.includeMedia.setShown(self.isApkg)
        self.frm.includeTags.setShown(not self.isApkg)

    def accept(self):
        self.exporter.includeSched = (
            self.frm.includeSched.isChecked())
        self.exporter.includeMedia = (
            self.frm.includeMedia.isChecked())
        self.exporter.includeTags = (
            self.frm.includeTags.isChecked())
        if not self.frm.deck.currentIndex():
            self.exporter.did = None
        else:
            name = self.decks[self.frm.deck.currentIndex()]
            self.exporter.did = self.col.decks.id(name)
        if (self.isApkg and self.exporter.includeSched and not
            self.exporter.did):
            verbatim = True
            # it's a verbatim apkg export, so place on desktop instead of
            # choosing file
            file = os.path.join(QDesktopServices.storageLocation(
                QDesktopServices.DesktopLocation), "collection.apkg")
            if os.path.exists(file):
                if not askUser(
                    _("%s already exists on your desktop. Overwrite it?")%
                    "collection.apkg"):
                    return
        else:
            verbatim = False
            file = getSaveFile(
                self, _("Export"), "export",
                self.exporter.key, self.exporter.ext)
            if not file:
                return
        self.hide()
        if file:
            self.mw.progress.start(immediate=True)
            try:
                f = open(file, "wb")
                f.close()
            except (OSError, IOError), e:
                showWarning(_("Couldn't save file: %s") % unicode(e))
            else:
                os.unlink(file)
                self.exporter.exportInto(file)
                if verbatim:
                    msg = _("A file called collection.apkg was saved on your desktop.")
                    period = 5000
                else:
                    period = 3000
                    msg = ngettext("%d card exported.", "%d cards exported.", \
                                self.exporter.count) % self.exporter.count
                tooltip(msg, period=period)
            finally:
                self.mw.progress.finish()
        QDialog.accept(self)

########NEW FILE########
__FILENAME__ = fields
# Copyright: Damien Elmes <anki@ichi2.net>
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

from aqt.qt import *
import re
from anki.consts import *
import aqt
from aqt.utils import showWarning, openHelp, getOnlyText, askUser

class FieldDialog(QDialog):

    def __init__(self, mw, note, ord=0, parent=None):
        QDialog.__init__(self, parent or mw) #, Qt.Window)
        self.mw = aqt.mw
        self.parent = parent or mw
        self.note = note
        self.col = self.mw.col
        self.mm = self.mw.col.models
        self.model = note.model()
        self.mw.checkpoint(_("Fields"))
        self.form = aqt.forms.fields.Ui_Dialog()
        self.form.setupUi(self)
        self.setWindowTitle(_("Fields for %s") % self.model['name'])
        self.form.buttonBox.button(QDialogButtonBox.Help).setAutoDefault(False)
        self.form.buttonBox.button(QDialogButtonBox.Close).setAutoDefault(False)
        self.currentIdx = None
        self.oldSortField = self.model['sortf']
        self.fillFields()
        self.setupSignals()
        self.form.fieldList.setCurrentRow(0)
        self.exec_()

    ##########################################################################

    def fillFields(self):
        self.currentIdx = None
        self.form.fieldList.clear()
        for f in self.model['flds']:
            self.form.fieldList.addItem(f['name'])

    def setupSignals(self):
        c = self.connect
        s = SIGNAL
        f = self.form
        c(f.fieldList, s("currentRowChanged(int)"), self.onRowChange)
        c(f.fieldAdd, s("clicked()"), self.onAdd)
        c(f.fieldDelete, s("clicked()"), self.onDelete)
        c(f.fieldRename, s("clicked()"), self.onRename)
        c(f.fieldPosition, s("clicked()"), self.onPosition)
        c(f.sortField, s("clicked()"), self.onSortField)
        c(f.buttonBox, s("helpRequested()"), self.onHelp)

    def onRowChange(self, idx):
        if idx == -1:
            return
        self.saveField()
        self.loadField(idx)

    def _uniqueName(self, prompt, ignoreOrd=None, old=""):
        txt = getOnlyText(prompt, default=old)
        if not txt:
            return
        for f in self.model['flds']:
            if ignoreOrd is not None and f['ord'] == ignoreOrd:
                continue
            if f['name'] == txt:
                showWarning(_("That field name is already used."))
                return
        return txt

    def onRename(self):
        idx = self.currentIdx
        f = self.model['flds'][idx]
        name = self._uniqueName(_("New name:"), self.currentIdx, f['name'])
        if not name:
            return
        self.mm.renameField(self.model, f, name)
        self.saveField()
        self.fillFields()
        self.form.fieldList.setCurrentRow(idx)

    def onAdd(self):
        name = self._uniqueName(_("Field name:"))
        if not name:
            return
        self.saveField()
        self.mw.progress.start()
        f = self.mm.newField(name)
        self.mm.addField(self.model, f)
        self.mw.progress.finish()
        self.fillFields()
        self.form.fieldList.setCurrentRow(len(self.model['flds'])-1)

    def onDelete(self):
        if len(self.model['flds']) < 2:
            return showWarning(_("Notes require at least one field."))
        c = self.mm.useCount(self.model)
        c = ngettext("%d note", "%d notes", c) % c
        if not askUser(_("Delete field from %s?") % c):
            return
        f = self.model['flds'][self.form.fieldList.currentRow()]
        self.mw.progress.start()
        self.mm.remField(self.model, f)
        self.mw.progress.finish()
        self.fillFields()
        self.form.fieldList.setCurrentRow(0)

    def onPosition(self, delta=-1):
        idx = self.currentIdx
        l = len(self.model['flds'])
        txt = getOnlyText(_("New position (1...%d):") % l, default=str(idx+1))
        if not txt:
            return
        try:
            pos = int(txt)
        except ValueError:
            return
        if not 0 < pos <= l:
            return
        self.saveField()
        f = self.model['flds'][self.currentIdx]
        self.mw.progress.start()
        self.mm.moveField(self.model, f, pos-1)
        self.mw.progress.finish()
        self.fillFields()
        self.form.fieldList.setCurrentRow(pos-1)

    def onSortField(self):
        # don't allow user to disable; it makes no sense
        self.form.sortField.setChecked(True)
        self.model['sortf'] = self.form.fieldList.currentRow()

    def loadField(self, idx):
        self.currentIdx = idx
        fld = self.model['flds'][idx]
        f = self.form
        f.fontFamily.setCurrentFont(QFont(fld['font']))
        f.fontSize.setValue(fld['size'])
        f.sticky.setChecked(fld['sticky'])
        f.sortField.setChecked(self.model['sortf'] == fld['ord'])
        f.rtl.setChecked(fld['rtl'])

    def saveField(self):
        # not initialized yet?
        if self.currentIdx is None:
            return
        idx = self.currentIdx
        fld = self.model['flds'][idx]
        f = self.form
        fld['font'] = f.fontFamily.currentFont().family()
        fld['size'] = f.fontSize.value()
        fld['sticky'] = f.sticky.isChecked()
        fld['rtl'] = f.rtl.isChecked()

    def reject(self):
        self.saveField()
        if self.oldSortField != self.model['sortf']:
            self.mw.progress.start()
            self.mw.col.updateFieldCache(self.mm.nids(self.model))
            self.mw.progress.finish()
        self.mm.save(self.model)
        self.mw.reset()
        QDialog.reject(self)

    def accept(self):
        self.reject()

    def onHelp(self):
        openHelp("fields")

########NEW FILE########
__FILENAME__ = importing
# Copyright: Damien Elmes <anki@ichi2.net>
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

import os, copy, time, sys, re, traceback, zipfile, json
from aqt.qt import *
import anki
import anki.importing as importing
from aqt.utils import getOnlyText, getFile, showText, showWarning, openHelp, \
    askUserDialog, askUser, tooltip
from anki.errors import *
from anki.hooks import addHook, remHook
import aqt.forms, aqt.modelchooser, aqt.deckchooser

class ChangeMap(QDialog):
    def __init__(self, mw, model, current):
        QDialog.__init__(self, mw, Qt.Window)
        self.mw = mw
        self.model = model
        self.frm = aqt.forms.changemap.Ui_ChangeMap()
        self.frm.setupUi(self)
        n = 0
        setCurrent = False
        for field in self.model['flds']:
            item = QListWidgetItem(_("Map to %s") % field['name'])
            self.frm.fields.addItem(item)
            if current == field['name']:
                setCurrent = True
                self.frm.fields.setCurrentRow(n)
            n += 1
        self.frm.fields.addItem(QListWidgetItem(_("Map to Tags")))
        self.frm.fields.addItem(QListWidgetItem(_("Discard field")))
        if not setCurrent:
            if current == "_tags":
                self.frm.fields.setCurrentRow(n)
            else:
                self.frm.fields.setCurrentRow(n+1)
        self.field = None

    def getField(self):
        self.exec_()
        return self.field

    def accept(self):
        row = self.frm.fields.currentRow()
        if row < len(self.model['flds']):
            self.field = self.model['flds'][row]['name']
        elif row == self.frm.fields.count() - 2:
            self.field = "_tags"
        else:
            self.field = None
        QDialog.accept(self)

    def reject(self):
        self.accept()

class ImportDialog(QDialog):

    def __init__(self, mw, importer):
        QDialog.__init__(self, mw, Qt.Window)
        self.mw = mw
        self.importer = importer
        self.frm = aqt.forms.importing.Ui_ImportDialog()
        self.frm.setupUi(self)
        from aqt.tagedit import TagEdit
        self.connect(self.frm.buttonBox.button(QDialogButtonBox.Help),
                     SIGNAL("clicked()"), self.helpRequested)
        self.setupMappingFrame()
        self.setupOptions()
        self.modelChanged()
        self.frm.autoDetect.setShown(self.importer.needDelimiter)
        addHook("currentModelChanged", self.modelChanged)
        self.connect(self.frm.autoDetect, SIGNAL("clicked()"),
                     self.onDelimiter)
        self.updateDelimiterButtonText()
        self.exec_()

    def setupOptions(self):
        self.model = self.mw.col.models.current()
        self.modelChooser = aqt.modelchooser.ModelChooser(
            self.mw, self.frm.modelArea, label=False)
        self.deck = aqt.deckchooser.DeckChooser(
            self.mw, self.frm.deckArea, label=False)
        self.connect(self.frm.importButton, SIGNAL("clicked()"),
                     self.doImport)

    def modelChanged(self):
        self.importer.model = self.mw.col.models.current()
        self.importer.initMapping()
        self.showMapping()
        if self.mw.col.conf.get("addToCur", True):
            did = self.mw.col.conf['curDeck']
            if self.mw.col.decks.isDyn(did):
                did = 1
        else:
            did = self.importer.model['did']
        #self.deck.setText(self.mw.col.decks.name(did))

    def onDelimiter(self):
        str = getOnlyText(_("""\
By default, Anki will detect the character between fields, such as
a tab, comma, and so on. If Anki is detecting the character incorrectly,
you can enter it here. Use \\t to represent tab."""),
                self, help="importing") or "\t"
        str = str.replace("\\t", "\t")
        str = str.encode("ascii")
        self.hideMapping()
        def updateDelim():
            self.importer.delimiter = str
            self.importer.updateDelimiter()
        self.showMapping(hook=updateDelim)
        self.updateDelimiterButtonText()

    def updateDelimiterButtonText(self):
        if not self.importer.needDelimiter:
            return
        if self.importer.delimiter:
            d = self.importer.delimiter
        else:
            d = self.importer.dialect.delimiter
        if d == "\t":
            d = _("Tab")
        elif d == ",":
            d = _("Comma")
        elif d == " ":
            d = _("Space")
        elif d == ";":
            d = _("Semicolon")
        elif d == ":":
            d = _("Colon")
        else:
            d = `d`
        txt = _("Fields separated by: %s") % d
        self.frm.autoDetect.setText(txt)

    def doImport(self, update=False):
        self.importer.mapping = self.mapping
        if not self.importer.mappingOk():
            showWarning(
                _("The first field of the note type must be mapped."))
            return
        self.importer.importMode = self.frm.importMode.currentIndex()
        self.importer.allowHTML = self.frm.allowHTML.isChecked()
        did = self.deck.selectedId()
        if did != self.importer.model['did']:
            self.importer.model['did'] = did
            self.mw.col.models.save(self.importer.model)
        self.mw.progress.start(immediate=True)
        self.mw.checkpoint(_("Import"))
        try:
            self.importer.run()
        except Exception, e:
            msg = _("Import failed.\n")
            err = unicode(e)
            if "1-character string" in err:
                msg += err
            else:
                msg += unicode(traceback.format_exc(), "ascii", "replace")
            showText(msg)
            return
        finally:
            self.mw.progress.finish()
        txt = _("Importing complete.") + "\n"
        if self.importer.log:
            txt += "\n".join(self.importer.log)
        self.close()
        showText(txt)
        self.mw.reset()

    def setupMappingFrame(self):
        # qt seems to have a bug with adding/removing from a grid, so we add
        # to a separate object and add/remove that instead
        self.frame = QFrame(self.frm.mappingArea)
        self.frm.mappingArea.setWidget(self.frame)
        self.mapbox = QVBoxLayout(self.frame)
        self.mapbox.setContentsMargins(0,0,0,0)
        self.mapwidget = None

    def hideMapping(self):
        self.frm.mappingGroup.hide()

    def showMapping(self, keepMapping=False, hook=None):
        if hook:
            hook()
        if not keepMapping:
            self.mapping = self.importer.mapping
        self.frm.mappingGroup.show()
        assert self.importer.fields()
        # set up the mapping grid
        if self.mapwidget:
            self.mapbox.removeWidget(self.mapwidget)
            self.mapwidget.deleteLater()
        self.mapwidget = QWidget()
        self.mapbox.addWidget(self.mapwidget)
        self.grid = QGridLayout(self.mapwidget)
        self.mapwidget.setLayout(self.grid)
        self.grid.setMargin(3)
        self.grid.setSpacing(6)
        fields = self.importer.fields()
        for num in range(len(self.mapping)):
            text = _("Field <b>%d</b> of file is:") % (num + 1)
            self.grid.addWidget(QLabel(text), num, 0)
            if self.mapping[num] == "_tags":
                text = _("mapped to <b>Tags</b>")
            elif self.mapping[num]:
                text = _("mapped to <b>%s</b>") % self.mapping[num]
            else:
                text = _("<ignored>")
            self.grid.addWidget(QLabel(text), num, 1)
            button = QPushButton(_("Change"))
            self.grid.addWidget(button, num, 2)
            self.connect(button, SIGNAL("clicked()"),
                         lambda s=self,n=num: s.changeMappingNum(n))

    def changeMappingNum(self, n):
        f = ChangeMap(self.mw, self.importer.model, self.mapping[n]).getField()
        try:
            # make sure we don't have it twice
            index = self.mapping.index(f)
            self.mapping[index] = None
        except ValueError:
            pass
        self.mapping[n] = f
        if getattr(self.importer, "delimiter", False):
            self.savedDelimiter = self.importer.delimiter
            def updateDelim():
                self.importer.delimiter = self.savedDelimiter
            self.showMapping(hook=updateDelim, keepMapping=True)
        else:
            self.showMapping(keepMapping=True)

    def reject(self):
        self.modelChooser.cleanup()
        remHook("currentModelChanged", self.modelChanged)
        QDialog.reject(self)

    def helpRequested(self):
        openHelp("FileImport")

def onImport(mw):
    filt = ";;".join([x[0] for x in importing.Importers])
    file = getFile(mw, _("Import"), None, key="import",
                   filter=filt)
    if not file:
        return
    file = unicode(file)
    importFile(mw, file)

def importFile(mw, file):
    ext = os.path.splitext(file)[1]
    importer = None
    done = False
    for i in importing.Importers:
        if done:
            break
        for mext in re.findall("[( ]?\*\.(.+?)[) ]", i[0]):
            if ext == "." + mext:
                importer = i[1]
                done = True
                break
    if not importer:
        # if no matches, assume TSV
        importer = importing.Importers[0][1]
    importer = importer(mw.col, file)
    # need to show import dialog?
    if importer.needMapper:
        # make sure we can load the file first
        mw.progress.start(immediate=True)
        try:
            importer.open()
        except UnicodeDecodeError:
            showWarning(_("Selected file was not in UTF-8 format."))
            return
        except Exception, e:
            msg = unicode(e)
            if msg == "unknownFormat":
                if ext == ".anki2":
                    showWarning(_("""\
.anki2 files are not designed for importing. If you're trying to restore from a \
backup, please see the 'Backups' section of the user manual."""))
                else:
                    showWarning(_("Unknown file format."))
            else:
                msg = _("Import failed. Debugging info:\n")
                msg += unicode(traceback.format_exc(), "ascii", "replace")
                showText(msg)
            return
        finally:
            mw.progress.finish()
        diag = ImportDialog(mw, importer)
    else:
        # if it's an apkg, we need to ask whether to import/replace
        if importer.__class__.__name__ == "AnkiPackageImporter":
            if not setupApkgImport(mw, importer):
                return
        mw.progress.start(immediate=True)
        try:
            importer.run()
        except Exception, e:
            if "invalidFile" in unicode(e):
                msg = _("""\
Invalid file. Please run a DB check in Anki 1.2 and try again.""")
                msg += _(""" \
Even if the DB check reports 'no problems found', a subsequent import should work.""")
                showWarning(msg)
            elif "readonly" in unicode(e):
                showWarning(_("""\
Unable to import from a read-only file."""))
            else:
                msg = _("Import failed.\n")
                msg += unicode(traceback.format_exc(), "ascii", "replace")
                showText(msg)
        else:
            log = "\n".join(importer.log)
            if "\n" not in log:
                tooltip(log)
            else:
                showText(log)
        finally:
            mw.progress.finish()
        mw.reset()

def setupApkgImport(mw, importer):
    base = os.path.basename(importer.file).lower()
    full = (base == "collection.apkg") or re.match("backup-.*\\.apkg", base)
    if not full:
        # adding
        return True
    if not askUser(_("""\
This will delete your existing collection and replace it with the data in \
the file you're importing. Are you sure?"""), msgfunc=QMessageBox.warning):
        return False
    # schedule replacement; don't do it immediately as we may have been
    # called as part of the startup routine
    mw.progress.start(immediate=True)
    mw.progress.timer(
        100, lambda mw=mw, f=importer.file: replaceWithApkg(mw, f), False)

def replaceWithApkg(mw, file):
    # unload collection, which will also trigger a backup
    mw.unloadCollection()
    # overwrite collection
    z = zipfile.ZipFile(file)
    z.extract("collection.anki2", mw.pm.profileFolder())
    # because users don't have a backup of media, it's safer to import new
    # data and rely on them running a media db check to get rid of any
    # unwanted media. in the future we might also want to deduplicate this
    # step
    d = os.path.join(mw.pm.profileFolder(), "collection.media")
    for c, file in json.loads(z.read("media")).items():
        open(os.path.join(d, file), "wb").write(z.read(str(c)))
    z.close()
    # reload
    mw.loadCollection()
    mw.progress.finish()

########NEW FILE########
__FILENAME__ = main
# Copyright: Damien Elmes <anki@ichi2.net>
# -*- coding: utf-8 -*-
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

import os, sys, re, stat, traceback, signal
import shutil, time, zipfile
from operator import itemgetter

from aqt.qt import *
QtConfig = pyqtconfig.Configuration()

from anki import Collection
from anki.utils import stripHTML, checksum, isWin, isMac, intTime, json
from anki.hooks import runHook, addHook, remHook
import anki.consts

import aqt, aqt.progress, aqt.webview, aqt.toolbar, aqt.stats
from aqt.utils import saveGeom, restoreGeom, showInfo, showWarning, \
    saveState, restoreState, getOnlyText, askUser, GetTextDialog, \
    askUserDialog, applyStyles, getText, showText, showCritical, getFile, \
    tooltip, openHelp, openLink

class AnkiQt(QMainWindow):
    def __init__(self, app, profileManager, args):
        QMainWindow.__init__(self)
        self.state = "startup"
        aqt.mw = self
        self.app = app
        if isWin:
            self._xpstyle = QStyleFactory.create("WindowsXP")
            self.app.setStyle(self._xpstyle)
        self.pm = profileManager
        # running 2.0 for the first time?
        if self.pm.meta['firstRun']:
            # load the new deck user profile
            self.pm.load(self.pm.profiles()[0])
            # upgrade if necessary
            from aqt.upgrade import Upgrader
            u = Upgrader(self)
            u.maybeUpgrade()
            self.pm.meta['firstRun'] = False
            self.pm.save()
        # init rest of app
        try:
            self.setupUI()
            self.setupAddons()
        except:
            showInfo(_("Error during startup:\n%s") % traceback.format_exc())
            sys.exit(1)
        # were we given a file to import?
        if args and args[0]:
            self.onAppMsg(unicode(args[0], "utf8", "ignore"))
        # Load profile in a timer so we can let the window finish init and not
        # close on profile load error.
        self.progress.timer(10, self.setupProfile, False)

    def setupUI(self):
        self.col = None
        self.hideSchemaMsg = False
        self.setupAppMsg()
        self.setupKeys()
        self.setupThreads()
        self.setupFonts()
        self.setupMainWindow()
        self.setupSystemSpecific()
        self.setupStyle()
        self.setupMenus()
        self.setupProgress()
        self.setupErrorHandler()
        self.setupSignals()
        self.setupAutoUpdate()
        self.setupSchema()
        self.setupRefreshTimer()
        self.updateTitleBar()
        # screens
        self.setupDeckBrowser()
        self.setupOverview()
        self.setupReviewer()

    # Profiles
    ##########################################################################

    def setupProfile(self):
        self.pendingImport = None
        # profile not provided on command line?
        if not self.pm.name:
            # if there's a single profile, load it automatically
            profs = self.pm.profiles()
            if len(profs) == 1:
                try:
                    self.pm.load(profs[0])
                except:
                    # password protected
                    pass
        if not self.pm.name:
            self.showProfileManager()
        else:
            self.loadProfile()

    def showProfileManager(self):
        self.state = "profileManager"
        d = self.profileDiag = QDialog()
        f = self.profileForm = aqt.forms.profiles.Ui_Dialog()
        f.setupUi(d)
        d.connect(f.login, SIGNAL("clicked()"), self.onOpenProfile)
        d.connect(f.profiles, SIGNAL("itemDoubleClicked(QListWidgetItem*)"),
                  self.onOpenProfile)
        d.connect(f.quit, SIGNAL("clicked()"), lambda: sys.exit(0))
        d.connect(f.add, SIGNAL("clicked()"), self.onAddProfile)
        d.connect(f.rename, SIGNAL("clicked()"), self.onRenameProfile)
        d.connect(f.delete_2, SIGNAL("clicked()"), self.onRemProfile)
        d.connect(d, SIGNAL("rejected()"), lambda: d.close())
        d.connect(f.profiles, SIGNAL("currentRowChanged(int)"),
                  self.onProfileRowChange)
        self.refreshProfilesList()
        # raise first, for osx testing
        d.show()
        d.activateWindow()
        d.raise_()
        d.exec_()

    def refreshProfilesList(self):
        f = self.profileForm
        f.profiles.clear()
        profs = self.pm.profiles()
        f.profiles.addItems(profs)
        try:
            idx = profs.index(self.pm.name)
        except:
            idx = 0
        f.profiles.setCurrentRow(idx)

    def onProfileRowChange(self, n):
        if n < 0:
            # called on .clear()
            return
        name = self.pm.profiles()[n]
        f = self.profileForm
        passwd = not self.pm.load(name)
        f.passEdit.setShown(passwd)
        f.passLabel.setShown(passwd)

    def openProfile(self):
        name = self.pm.profiles()[self.profileForm.profiles.currentRow()]
        passwd = self.profileForm.passEdit.text()
        return self.pm.load(name, passwd)

    def onOpenProfile(self):
        if not self.openProfile():
            showWarning(_("Invalid password."))
            return
        self.profileDiag.close()
        self.loadProfile()
        return True

    def profileNameOk(self, str):
        from anki.utils import invalidFilename, invalidFilenameChars
        if invalidFilename(str):
            showWarning(
                _("A profile name cannot contain these characters: %s") %
                " ".join(invalidFilenameChars))
            return
        return True

    def onAddProfile(self):
        name = getOnlyText(_("Name:"))
        if name:
            name = name.strip()
            if name in self.pm.profiles():
                return showWarning(_("Name exists."))
            if not self.profileNameOk(name):
                return
            self.pm.create(name)
            self.pm.name = name
            self.refreshProfilesList()

    def onRenameProfile(self):
        name = getOnlyText(_("New name:"), default=self.pm.name)
        if not self.openProfile():
            return showWarning(_("Invalid password."))
        if not name:
            return
        if name == self.pm.name:
            return
        if name in self.pm.profiles():
            return showWarning(_("Name exists."))
        if not self.profileNameOk(name):
            return
        self.pm.rename(name)
        self.refreshProfilesList()

    def onRemProfile(self):
        profs = self.pm.profiles()
        if len(profs) < 2:
            return showWarning(_("There must be at least one profile."))
        # password correct?
        if not self.openProfile():
            return
        # sure?
        if not askUser(_("""\
All cards, notes, and media for this profile will be deleted. \
Are you sure?""")):
            return
        self.pm.remove(self.pm.name)
        self.refreshProfilesList()

    def loadProfile(self):
        # show main window
        if self.pm.profile['mainWindowState']:
            restoreGeom(self, "mainWindow")
            restoreState(self, "mainWindow")
        else:
            self.resize(500, 400)
        # toolbar needs to be retranslated
        self.toolbar.draw()
        # show and raise window for osx
        self.show()
        self.activateWindow()
        self.raise_()
        # maybe sync (will load DB)
        self.onSync(auto=True)
        # import pending?
        if self.pendingImport:
            if self.pm.profile['key']:
                showInfo(_("""\
To import into a password protected profile, please open the profile before attempting to import."""))
            else:
                import aqt.importing
                aqt.importing.importFile(self, self.pendingImport)
            self.pendingImport = None
        runHook("profileLoaded")

    def unloadProfile(self, browser=True):
        if not self.pm.profile:
            # already unloaded
            return
        self.state = "profileManager"
        runHook("unloadProfile")
        self.unloadCollection()
        self.onSync(auto=True, reload=False)
        self.pm.profile['mainWindowGeom'] = self.saveGeometry()
        self.pm.profile['mainWindowState'] = self.saveState()
        self.pm.save()
        self.pm.profile = None
        self.hide()
        if browser:
            self.showProfileManager()

    # Collection load/unload
    ##########################################################################

    def loadCollection(self):
        self.hideSchemaMsg = True
        try:
            self.col = Collection(self.pm.collectionPath())
        except:
            # move back to profile manager
            showWarning("""\
Your collection is corrupt. Please see the manual for \
how to restore from a backup.""")
            return self.unloadProfile()
        self.hideSchemaMsg = False
        self.progress.setupDB(self.col.db)
        self.moveToState("deckBrowser")

    def unloadCollection(self):
        if self.col:
            self.closeAllCollectionWindows()
            self.maybeOptimize()
            self.col.close()
            self.col = None
            self.progress.start(immediate=True)
            self.backup()
            self.progress.finish()

    # Backup and auto-optimize
    ##########################################################################

    def backup(self):
        nbacks = self.pm.profile['numBackups']
        if not nbacks:
            return
        dir = self.pm.backupFolder()
        path = self.pm.collectionPath()
        # find existing backups
        backups = []
        for file in os.listdir(dir):
            m = re.search("backup-(\d+).apkg", file)
            if not m:
                # unknown file
                continue
            backups.append((int(m.group(1)), file))
        backups.sort()
        # get next num
        if not backups:
            n = 1
        else:
            n = backups[-1][0] + 1
        # do backup
        newpath = os.path.join(dir, "backup-%d.apkg" % n)
        z = zipfile.ZipFile(newpath, "w", zipfile.ZIP_DEFLATED)
        z.write(path, "collection.anki2")
        z.writestr("media", "{}")
        z.close()
        # remove if over
        if len(backups) + 1 > nbacks:
            delete = len(backups) + 1 - nbacks
            delete = backups[:delete]
            for file in delete:
                os.unlink(os.path.join(dir, file[1]))

    def maybeOptimize(self):
        # has two weeks passed?
        if (intTime() - self.pm.profile['lastOptimize']) < 86400*14:
            return
        self.progress.start(label=_("Optimizing..."), immediate=True)
        self.col.optimize()
        self.pm.profile['lastOptimize'] = intTime()
        self.pm.save()
        self.progress.finish()

    # State machine
    ##########################################################################

    def moveToState(self, state, *args):
        #print "-> move from", self.state, "to", state
        oldState = self.state or "dummy"
        cleanup = getattr(self, "_"+oldState+"Cleanup", None)
        if cleanup:
            cleanup(state)
        self.state = state
        getattr(self, "_"+state+"State")(oldState, *args)

    def _deckBrowserState(self, oldState):
        self.deckBrowser.show()

    def _colLoadingState(self, oldState):
        "Run once, when col is loaded."
        self.enableColMenuItems()
        # ensure cwd is set if media dir exists
        self.col.media.dir()
        runHook("colLoading", self.col)
        self.moveToState("overview")

    def _selectedDeck(self):
        did = self.col.decks.selected()
        if not self.col.decks.nameOrNone(did):
            showInfo(_("Please select a deck."))
            return
        return self.col.decks.get(did)

    def _overviewState(self, oldState):
        if not self._selectedDeck():
            return self.moveToState("deckBrowser")
        self.col.reset()
        self.overview.show()

    def _reviewState(self, oldState):
        self.reviewer.show()

    def _reviewCleanup(self, newState):
        if newState != "resetRequired" and newState != "review":
            self.reviewer.cleanup()

    def noteChanged(self, nid):
        "Called when a card or note is edited (but not deleted)."
        runHook("noteChanged", nid)

    # Resetting state
    ##########################################################################

    def reset(self, guiOnly=False):
        "Called for non-trivial edits. Rebuilds queue and updates UI."
        if self.col:
            if not guiOnly:
                self.col.reset()
            runHook("reset")
            self.maybeEnableUndo()
            self.moveToState(self.state)

    def requireReset(self, modal=False):
        "Signal queue needs to be rebuilt when edits are finished or by user."
        self.autosave()
        self.resetModal = modal
        if self.interactiveState():
            self.moveToState("resetRequired")

    def interactiveState(self):
        "True if not in profile manager, syncing, etc."
        return self.state in ("overview", "review", "deckBrowser")

    def maybeReset(self):
        self.autosave()
        if self.state == "resetRequired":
            self.state = self.returnState
            self.reset()

    def delayedMaybeReset(self):
        # if we redraw the page in a button click event it will often crash on
        # windows
        self.progress.timer(100, self.maybeReset, False)

    def _resetRequiredState(self, oldState):
        if oldState != "resetRequired":
            self.returnState = oldState
        if self.resetModal:
            # we don't have to change the webview, as we have a covering window
            return
        self.web.setLinkHandler(lambda url: self.delayedMaybeReset())
        i = _("Waiting for editing to finish.")
        b = self.button("refresh", _("Resume Now"), id="resume")
        self.web.stdHtml("""
<center><div style="height: 100%%">
<div style="position:relative; vertical-align: middle;">
%s<br>
%s</div></div></center>
""" % (i, b), css=self.sharedCSS)
        self.bottomWeb.hide()
        self.web.setFocus()
        self.web.eval("$('#resume').focus()")

    # HTML helpers
    ##########################################################################

    sharedCSS = """
body {
background: #f3f3f3;
margin: 2em;
}
h1 { margin-bottom: 0.2em; }
"""

    def button(self, link, name, key=None, class_="", id=""):
        class_ = "but "+ class_
        if key:
            key = _("Shortcut key: %s") % key
        else:
            key = ""
        return '''
<button id="%s" class="%s" onclick="py.link('%s');return false;"
title="%s">%s</button>''' % (
            id, class_, link, key, name)

    # Main window setup
    ##########################################################################

    def setupMainWindow(self):
        # main window
        self.form = aqt.forms.main.Ui_MainWindow()
        self.form.setupUi(self)
        # toolbar
        tweb = aqt.webview.AnkiWebView()
        tweb.setObjectName("toolbarWeb")
        tweb.setFocusPolicy(Qt.WheelFocus)
        tweb.setFixedHeight(32+self.fontHeightDelta)
        self.toolbar = aqt.toolbar.Toolbar(self, tweb)
        self.toolbar.draw()
        # main area
        self.web = aqt.webview.AnkiWebView()
        self.web.setObjectName("mainText")
        self.web.setFocusPolicy(Qt.WheelFocus)
        self.web.setMinimumWidth(400)
        # bottom area
        sweb = self.bottomWeb = aqt.webview.AnkiWebView()
        #sweb.hide()
        sweb.setFixedHeight(100)
        sweb.setObjectName("bottomWeb")
        sweb.setFocusPolicy(Qt.WheelFocus)
        # add in a layout
        self.mainLayout = QVBoxLayout()
        self.mainLayout.setContentsMargins(0,0,0,0)
        self.mainLayout.setSpacing(0)
        self.mainLayout.addWidget(tweb)
        self.mainLayout.addWidget(self.web)
        self.mainLayout.addWidget(sweb)
        self.form.centralwidget.setLayout(self.mainLayout)

    def closeAllCollectionWindows(self):
        aqt.dialogs.closeAll()

    # Components
    ##########################################################################

    def setupSignals(self):
        signal.signal(signal.SIGINT, self.onSigInt)

    def onSigInt(self, signum, frame):
        # interrupt any current transaction and schedule a rollback & quit
        self.col.db.interrupt()
        def quit():
            self.col.db.rollback()
            self.close()
        self.progress.timer(100, quit, False)

    def setupProgress(self):
        self.progress = aqt.progress.ProgressManager(self)

    def setupErrorHandler(self):
        import aqt.errors
        self.errorHandler = aqt.errors.ErrorHandler(self)

    def setupAddons(self):
        import aqt.addons
        self.addonManager = aqt.addons.AddonManager(self)

    def setupThreads(self):
        self._mainThread = QThread.currentThread()

    def inMainThread(self):
        return self._mainThread == QThread.currentThread()

    def setupDeckBrowser(self):
        from aqt.deckbrowser import DeckBrowser
        self.deckBrowser = DeckBrowser(self)

    def setupOverview(self):
        from aqt.overview import Overview
        self.overview = Overview(self)

    def setupReviewer(self):
        from aqt.reviewer import Reviewer
        self.reviewer = Reviewer(self)

    # Syncing
    ##########################################################################

    def onSync(self, auto=False, reload=True):
        if not auto or (self.pm.profile['syncKey'] and
                        self.pm.profile['autoSync']):
            from aqt.sync import SyncManager
            self.unloadCollection()
            # set a sync state so the refresh timer doesn't fire while deck
            # unloaded
            self.state = "sync"
            self.syncer = SyncManager(self, self.pm)
            self.syncer.sync()
        if reload:
            if not self.col:
                self.loadCollection()

    def onFullSync(self):
        if not askUser(_("""\
If you proceed, you will need to choose between a full download or full \
upload, overwriting any changes either here or on AnkiWeb. Proceed?""")):
            return
        self.hideSchemaMsg = True
        self.col.modSchema()
        self.col.setMod()
        self.hideSchemaMsg = False
        self.onSync()

    # Tools
    ##########################################################################

    def raiseMain(self):
        if not self.app.activeWindow():
            # make sure window is shown
            self.setWindowState(self.windowState() & ~Qt.WindowMinimized)
        return True

    def setStatus(self, text, timeout=3000):
        self.form.statusbar.showMessage(text, timeout)

    def setupStyle(self):
        applyStyles(self)

    # Key handling
    ##########################################################################

    def setupKeys(self):
        self.keyHandler = None
        # debug shortcut
        self.debugShortcut = QShortcut(QKeySequence("Ctrl+:"), self)
        self.connect(
            self.debugShortcut, SIGNAL("activated()"), self.onDebug)

    def keyPressEvent(self, evt):
        # do we have a delegate?
        if self.keyHandler:
            # did it eat the key?
            if self.keyHandler(evt):
                return
        # run standard handler
        QMainWindow.keyPressEvent(self, evt)
        # check global keys
        key = unicode(evt.text())
        if key == "d":
            self.moveToState("deckBrowser")
        elif key == "s":
            if self.state == "overview":
                self.col.startTimebox()
                self.moveToState("review")
            else:
                self.moveToState("overview")
        elif key == "a":
            self.onAddCard()
        elif key == "b":
            self.onBrowse()
        elif key == "S":
            self.onStats()
        elif key == "y":
            self.onSync()

    # App exit
    ##########################################################################

    def closeEvent(self, event):
        "User hit the X button, etc."
        event.accept()
        self.onClose()

    def onClose(self):
        "Called from a shortcut key. Close current active window."
        aw = self.app.activeWindow()
        if not aw or aw == self:
            self.unloadProfile(browser=False)
            self.app.closeAllWindows()
        else:
            aw.close()

    # Undo & autosave
    ##########################################################################

    def onUndo(self):
        cid = self.col.undo()
        if cid and self.state == "review":
            card = self.col.getCard(cid)
            self.reviewer.cardQueue.append(card)
        self.reset()
        self.maybeEnableUndo()

    def maybeEnableUndo(self):
        if self.col and self.col.undoName():
            self.form.actionUndo.setText(_("Undo %s") %
                                            self.col.undoName())
            self.form.actionUndo.setEnabled(True)
            runHook("undoState", True)
        else:
            self.form.actionUndo.setText(_("Undo"))
            self.form.actionUndo.setEnabled(False)
            runHook("undoState", False)

    def checkpoint(self, name):
        self.col.save(name)
        self.maybeEnableUndo()

    def autosave(self):
        self.col.autosave()
        self.maybeEnableUndo()

    # Other menu operations
    ##########################################################################

    def onAddCard(self):
        aqt.dialogs.open("AddCards", self)

    def onBrowse(self):
        aqt.dialogs.open("Browser", self)

    def onEditCurrent(self):
        aqt.dialogs.open("EditCurrent", self)

    def onDeckConf(self, deck=None):
        if not deck:
            deck = self.col.decks.current()
        if deck['dyn']:
            import aqt.dyndeckconf
            aqt.dyndeckconf.DeckConf(self, deck=deck)
        else:
            import aqt.deckconf
            aqt.deckconf.DeckConf(self, deck)

    def onOverview(self):
        self.col.reset()
        self.moveToState("overview")

    def onStats(self):
        deck = self._selectedDeck()
        if not deck:
            return
        if deck['dyn']:
            showWarning(_("""\
As cards are removed from a filtered deck as they are answered, viewing the \
statistics of a filtered deck will only show you reviews for cards with \
multiple steps. To get an accurate report, please empty the filtered deck \
and check the statistics for a home deck instead."""))
            return
        aqt.stats.DeckStats(self)

    def onPrefs(self):
        import aqt.preferences
        aqt.preferences.Preferences(self)

    def onAbout(self):
        import aqt.about
        aqt.about.show(self)

    def onDonate(self):
        openLink(aqt.appDonate)

    def onDocumentation(self):
        openHelp("")

    # Importing & exporting
    ##########################################################################

    def onImport(self):
        import aqt.importing
        aqt.importing.onImport(self)

    def onExport(self):
        import aqt.exporting
        aqt.exporting.ExportDialog(self)

    # Cramming
    ##########################################################################

    def onCram(self, search=""):
        import aqt.dyndeckconf
        n = 1
        if not search:
            deck = self.col.decks.current()
            if not deck['dyn']:
                search = 'deck:%s ' % deck['name']
        decks = self.col.decks.allNames()
        while _("Filtered Deck %d") % n in decks:
            n += 1
        name = _("Filtered Deck %d") % n
        did = self.col.decks.newDyn(name)
        diag = aqt.dyndeckconf.DeckConf(self, first=True, search=search)
        if not diag.ok:
            # user cancelled first config
            self.col.decks.rem(did)
        else:
            self.moveToState("overview")

    # Menu, title bar & status
    ##########################################################################

    def setupMenus(self):
        m = self.form
        s = SIGNAL("triggered()")
        #self.connect(m.actionDownloadSharedPlugin, s, self.onGetSharedPlugin)
        self.connect(m.actionSwitchProfile, s, self.unloadProfile)
        self.connect(m.actionImport, s, self.onImport)
        self.connect(m.actionExport, s, self.onExport)
        self.connect(m.actionExit, s, self, SLOT("close()"))
        self.connect(m.actionPreferences, s, self.onPrefs)
        self.connect(m.actionAbout, s, self.onAbout)
        self.connect(m.actionUndo, s, self.onUndo)
        self.connect(m.actionFullDatabaseCheck, s, self.onCheckDB)
        self.connect(m.actionCheckMediaDatabase, s, self.onCheckMediaDB)
        self.connect(m.actionDocumentation, s, self.onDocumentation)
        self.connect(m.actionDonate, s, self.onDonate)
        self.connect(m.actionFullSync, s, self.onFullSync)
        self.connect(m.actionStudyDeck, s, self.onStudyDeck)
        self.connect(m.actionCreateFiltered, s, self.onCram)
        self.connect(m.actionEmptyCards, s, self.onEmptyCards)

    def updateTitleBar(self):
        self.setWindowTitle("Anki")

    # Auto update
    ##########################################################################

    def setupAutoUpdate(self):
        import aqt.update
        self.autoUpdate = aqt.update.LatestVersionFinder(self)
        self.connect(self.autoUpdate, SIGNAL("newVerAvail"), self.newVerAvail)
        self.connect(self.autoUpdate, SIGNAL("newMsg"), self.newMsg)
        self.connect(self.autoUpdate, SIGNAL("clockIsOff"), self.clockIsOff)
        self.autoUpdate.start()

    def newVerAvail(self, ver):
        if self.pm.meta['suppressUpdate'] != ver:
            aqt.update.askAndUpdate(self, ver)

    def newMsg(self, data):
        aqt.update.showMessages(self, data)

    def clockIsOff(self):
        showWarning("""\
In order to ensure your collection works correctly when moved between \
devices, Anki requires the system clock to be set correctly. Your system \
clock appears to be wrong by more than 5 minutes.

This can be because the \
clock is slow or fast, because the date is set incorrectly, or because \
the timezone or daylight savings information is incorrect. Please correct \
the problem and restart Anki.""")
        self.app.closeAllWindows()

    # Count refreshing
    ##########################################################################

    def setupRefreshTimer(self):
        # every 10 minutes
        self.progress.timer(10*60*1000, self.onRefreshTimer, True)

    def onRefreshTimer(self):
        if self.state == "deckBrowser":
            self.deckBrowser.refresh()
        elif self.state == "overview":
            self.overview.refresh()

    # Schema modifications
    ##########################################################################

    def setupSchema(self):
        addHook("modSchema", self.onSchemaMod)

    def onSchemaMod(self, arg):
        # if triggered in sync, make sure we don't use the gui
        if not self.inMainThread():
            return True
        # if from the full sync menu, ignore
        if self.hideSchemaMsg:
            return True
        return askUser(_("""\
The requested change will require a full upload of the database when \
you next synchronize your collection. If you have reviews or other changes \
waiting on another device that haven't been synchronized here yet, they \
will be lost. Continue?"""))

    # Advanced features
    ##########################################################################

    def onCheckDB(self):
        "True if no problems"
        self.progress.start(immediate=True)
        ret, ok = self.col.fixIntegrity()
        self.progress.finish()
        if not ok:
            showText(ret)
        else:
            tooltip(ret)
        self.reset()
        return ret

    def onCheckMediaDB(self):
        self.progress.start(immediate=True)
        (nohave, unused) = self.col.media.check()
        self.progress.finish()
        # generate report
        report = ""
        if unused:
            report += _(
                "In media folder but not used by any cards:")
            report += "\n" + "\n".join(unused)
        if nohave:
            if report:
                report += "\n\n\n"
            report += _(
                "Used on cards but missing from media folder:")
            report += "\n" + "\n".join(nohave)
        if not report:
            report = _("No unused or missing files found.")
        # show report and offer to delete
        diag = QDialog(self)
        diag.setWindowTitle("Anki")
        layout = QVBoxLayout(diag)
        diag.setLayout(layout)
        text = QTextEdit()
        text.setReadOnly(True)
        text.setPlainText(report)
        layout.addWidget(text)
        box = QDialogButtonBox(QDialogButtonBox.Close)
        layout.addWidget(box)
        b = QPushButton(_("Delete Unused"))
        b.setAutoDefault(False)
        box.addButton(b, QDialogButtonBox.ActionRole)
        b.connect(
            b, SIGNAL("clicked()"), lambda u=unused, d=diag: self.deleteUnused(u, d))
        diag.connect(box, SIGNAL("rejected()"), diag, SLOT("reject()"))
        diag.setMinimumHeight(400)
        diag.setMinimumWidth(500)
        diag.exec_()

    def deleteUnused(self, unused, diag):
        if not askUser(
            _("Delete unused media? This operation can not be undone.")):
            return
        mdir = self.col.media.dir()
        for f in unused:
            path = os.path.join(mdir, f)
            os.unlink(path)
        tooltip(_("Deleted."))
        diag.close()

    def onStudyDeck(self):
        from aqt.studydeck import StudyDeck
        ret = StudyDeck(self, dyn=True)
        if ret.name:
            self.col.decks.select(self.col.decks.id(ret.name))
            self.moveToState("overview")

    def onEmptyCards(self):
        self.progress.start(immediate=True)
        cids = self.col.emptyCids()
        if not cids:
            self.progress.finish()
            tooltip(_("No empty cards."))
            return
        report = self.col.emptyCardReport(cids)
        self.progress.finish()
        part1 = ngettext("%d card", "%d cards", len(cids)) % len(cids)
        part1 = _("%s to delete:") % part1
        diag, box = showText(part1 + "\n\n" + report, run=False)
        box.addButton(_("Delete Cards"), QDialogButtonBox.AcceptRole)
        box.button(QDialogButtonBox.Close).setDefault(True)
        def onDelete():
            QDialog.accept(diag)
            self.checkpoint(_("Delete Empty"))
            self.col.remCards(cids)
            tooltip(ngettext("%d card deleted.", "%d cards deleted.", len(cids)) % len(cids))
            self.reset()
        diag.connect(box, SIGNAL("accepted()"), onDelete)
        diag.show()

    # Debugging
    ######################################################################

    def onDebug(self):
        d = self.debugDiag = QDialog()
        frm = aqt.forms.debug.Ui_Dialog()
        frm.setupUi(d)
        s = self.debugDiagShort = QShortcut(QKeySequence("ctrl+return"), d)
        self.connect(s, SIGNAL("activated()"),
                     lambda: self.onDebugRet(frm))
        s = self.debugDiagShort = QShortcut(
            QKeySequence("ctrl+shift+return"), d)
        self.connect(s, SIGNAL("activated()"),
                     lambda: self.onDebugPrint(frm))
        d.show()

    def _captureOutput(self, on):
        mw = self
        class Stream(object):
            def write(self, data):
                mw._output += data
        if on:
            self._output = ""
            self._oldStderr = sys.stderr
            self._oldStdout = sys.stdout
            s = Stream()
            sys.stderr = s
            sys.stdout = s
        else:
            sys.stderr = self._oldStderr
            sys.stdout = self._oldStdout

    def _debugCard(self):
        return self.reviewer.card.__dict__

    def _debugBrowserCard(self):
        return aqt.dialogs._dialogs['Browser'][1].card.__dict__

    def onDebugPrint(self, frm):
        frm.text.setPlainText("pp(%s)" % frm.text.toPlainText())
        self.onDebugRet(frm)

    def onDebugRet(self, frm):
        import pprint, traceback
        text = frm.text.toPlainText()
        card = self._debugCard
        bcard = self._debugBrowserCard
        mw = self
        pp = pprint.pprint
        self._captureOutput(True)
        try:
            exec text
        except:
            self._output += traceback.format_exc()
        self._captureOutput(False)
        buf = ""
        for c, line in enumerate(text.strip().split("\n")):
            if c == 0:
                buf += ">>> %s\n" % line
            else:
                buf += "... %s\n" % line
        frm.log.appendPlainText(buf + (self._output or "<no output>"))
        frm.log.ensureCursorVisible()

    # System specific code
    ##########################################################################

    def setupFonts(self):
        f = QFontInfo(self.font())
        ws = QWebSettings.globalSettings()
        self.fontHeight = f.pixelSize()
        self.fontFamily = f.family()
        self.fontHeightDelta = max(0, self.fontHeight - 13)
        ws.setFontFamily(QWebSettings.StandardFont, self.fontFamily)
        ws.setFontSize(QWebSettings.DefaultFontSize, self.fontHeight)

    def setupSystemSpecific(self):
        self.hideMenuAccels = False
        if isMac:
            qt_mac_set_menubar_icons(False)
            # mac users expect a minimize option
            self.minimizeShortcut = QShortcut("Ctrl+M", self)
            self.connect(self.minimizeShortcut, SIGNAL("activated()"),
                         self.onMacMinimize)
            self.hideMenuAccels = True
            self.maybeHideAccelerators()
            self.hideStatusTips()
        elif isWin:
            # make sure ctypes is bundled
            from ctypes import windll, wintypes

    def maybeHideAccelerators(self, tgt=None):
        if not self.hideMenuAccels:
            return
        tgt = tgt or self
        for action in tgt.findChildren(QAction):
            txt = unicode(action.text())
            m = re.match("^(.+)\(&.+\)(.+)?", txt)
            if m:
                action.setText(m.group(1) + (m.group(2) or ""))

    def hideStatusTips(self):
        for action in self.findChildren(QAction):
            action.setStatusTip("")

    def onMacMinimize(self):
        self.setWindowState(self.windowState() | Qt.WindowMinimized)

    # Single instance support
    ##########################################################################

    def setupAppMsg(self):
        self.connect(self.app, SIGNAL("appMsg"), self.onAppMsg)

    def onAppMsg(self, buf):
        if self.state == "startup":
            # try again in a second
            return self.progress.timer(1000, lambda: self.onAppMsg(buf), False)
        elif self.state == "profileManager":
            # can't raise window while in profile manager
            if buf == "raise":
                return
            self.pendingImport = buf
            return tooltip(_("Deck will be imported when a profile is opened."))
        if not self.interactiveState() or self.progress.busy():
            # we can't raise the main window while in profile dialog, syncing, etc
            if buf != "raise":
                showInfo(_("""\
Please ensure a profile is open and Anki is not busy, then try again."""),
                     parent=None)
            return
        # raise window
        if isWin:
            # on windows we can raise the window by minimizing and restoring
            self.showMinimized()
            self.setWindowState(Qt.WindowActive)
            self.showNormal()
        else:
            # on osx we can raise the window. on unity the icon in the tray will just flash.
            self.activateWindow()
            self.raise_()
        if buf == "raise":
            return
        # import
        if not isinstance(buf, unicode):
            buf = unicode(buf, "utf8", "ignore")
        if not os.path.exists(buf):
            return showInfo(_("Please use File>Import to import this file."))
        import aqt.importing
        aqt.importing.importFile(self, buf)

########NEW FILE########
__FILENAME__ = modelchooser
# -*- coding: utf-8 -*-
# Copyright: Damien Elmes <anki@ichi2.net>
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

from aqt.qt import *
from operator import itemgetter
from anki.hooks import addHook, remHook, runHook
from aqt.utils import isMac, shortcut
import aqt

class ModelChooser(QHBoxLayout):

    def __init__(self, mw, widget, label=True):
        QHBoxLayout.__init__(self)
        self.widget = widget
        self.mw = mw
        self.deck = mw.col
        self.label = label
        self.setMargin(0)
        self.setSpacing(8)
        self.setupModels()
        addHook('reset', self.onReset)
        self.widget.setLayout(self)

    def setupModels(self):
        if self.label:
            self.modelLabel = QLabel(_("Type"))
            self.addWidget(self.modelLabel)
        # models box
        self.models = QPushButton()
        #self.models.setStyleSheet("* { text-align: left; }")
        self.models.setToolTip(shortcut(_("Change Note Type (Ctrl+N)")))
        s = QShortcut(QKeySequence(_("Ctrl+N")), self.widget)
        s.connect(s, SIGNAL("activated()"), self.onModelChange)
        self.addWidget(self.models)
        self.connect(self.models, SIGNAL("clicked()"), self.onModelChange)
        # layout
        sizePolicy = QSizePolicy(
            QSizePolicy.Policy(7),
            QSizePolicy.Policy(0))
        self.models.setSizePolicy(sizePolicy)
        self.updateModels()

    def cleanup(self):
        remHook('reset', self.onReset)

    def onReset(self):
        self.updateModels()

    def show(self):
        self.widget.show()

    def hide(self):
        self.widget.hide()

    def onEdit(self):
        import aqt.models
        aqt.models.Models(self.mw, self.widget)

    def onModelChange(self):
        from aqt.studydeck import StudyDeck
        current = self.deck.models.current()['name']
        # edit button
        edit = QPushButton(_("Manage"))
        self.connect(edit, SIGNAL("clicked()"), self.onEdit)
        def nameFunc():
            return sorted(self.deck.models.allNames())
        ret = StudyDeck(
            self.mw, names=nameFunc,
            accept=_("Choose"), title=_("Choose Note Type"),
            help="_notes", current=current, parent=self.widget,
            buttons=[edit], cancel=False)
        if not ret.name:
            return
        m = self.deck.models.byName(ret.name)
        self.deck.conf['curModel'] = m['id']
        cdeck = self.deck.decks.current()
        cdeck['mid'] = m['id']
        self.deck.decks.save(cdeck)
        runHook("currentModelChanged")
        self.mw.reset()

    def updateModels(self):
        self.models.setText(self.deck.models.current()['name'])

########NEW FILE########
__FILENAME__ = models
# Copyright: Damien Elmes <anki@ichi2.net>
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

from aqt.qt import *
from operator import itemgetter
from aqt.utils import showInfo, askUser, getText, maybeHideClose, openHelp
import aqt.modelchooser, aqt.clayout
from anki import stdmodels
from aqt.utils import saveGeom, restoreGeom

class Models(QDialog):
    def __init__(self, mw, parent=None):
        self.mw = mw
        self.parent = parent or mw
        QDialog.__init__(self, self.parent, Qt.Window)
        self.col = mw.col
        self.mm = self.col.models
        self.mw.checkpoint(_("Note Types"))
        self.form = aqt.forms.models.Ui_Dialog()
        self.form.setupUi(self)
        self.connect(self.form.buttonBox, SIGNAL("helpRequested()"),
                     lambda: openHelp("notetypes"))
        self.setupModels()
        restoreGeom(self, "models")
        self.exec_()

    # Models
    ##########################################################################

    def setupModels(self):
        self.model = None
        c = self.connect; f = self.form; box = f.buttonBox
        s = SIGNAL("clicked()")
        t = QDialogButtonBox.ActionRole
        b = box.addButton(_("Add"), t)
        c(b, s, self.onAdd)
        b = box.addButton(_("Rename"), t)
        c(b, s, self.onRename)
        b = box.addButton(_("Delete"), t)
        c(b, s, self.onDelete)
        b = box.addButton(_("Options..."), t)
        c(b, s, self.onAdvanced)
        c(f.modelsList, SIGNAL("currentRowChanged(int)"), self.modelChanged)
        c(f.modelsList, SIGNAL("itemDoubleClicked(QListWidgetItem*)"),
          self.onRename)
        self.updateModelsList()
        f.modelsList.setCurrentRow(0)
        maybeHideClose(box)

    def onRename(self):
        txt = getText(_("New name:"), default=self.model['name'])
        if txt[0]:
            self.model['name'] = txt[0]
            self.mm.save(self.model)
        self.updateModelsList()

    def updateModelsList(self):
        row = self.form.modelsList.currentRow()
        if row == -1:
            row = 0
        self.models = self.col.models.all()
        self.models.sort(key=itemgetter("name"))
        self.form.modelsList.clear()
        for m in self.models:
            mUse = self.mm.useCount(m)
            mUse = ngettext("%d note", "%d notes", mUse) % mUse
            item = QListWidgetItem("%s [%s]" % (m['name'], mUse))
            self.form.modelsList.addItem(item)
        self.form.modelsList.setCurrentRow(row)

    def modelChanged(self):
        if self.model:
            self.saveModel()
        idx = self.form.modelsList.currentRow()
        self.model = self.models[idx]

    def onAdd(self):
        m = AddModel(self.mw, self).get()
        if m:
            txt = getText(_("Name:"), default=m['name'])[0]
            if txt:
                m['name'] = txt
            self.mm.save(m)
            self.updateModelsList()

    def onDelete(self):
        if len(self.models) < 2:
            showInfo(_("Please add another note type first."),
                     parent=self)
            return
        if self.mm.useCount(self.model):
            msg = _("Delete this note type and all its cards?")
        else:
            msg = _("Delete this unused note type?")
        if not askUser(msg, parent=self):
            return
        self.mm.rem(self.model)
        self.model = None
        self.updateModelsList()

    def onAdvanced(self):
        d = QDialog(self)
        frm = aqt.forms.modelopts.Ui_Dialog()
        frm.setupUi(d)
        frm.latexHeader.setText(self.model['latexPre'])
        frm.latexFooter.setText(self.model['latexPost'])
        d.setWindowTitle(_("Options for %s") % self.model['name'])
        self.connect(
            frm.buttonBox, SIGNAL("helpRequested()"),
            lambda: openHelp("latex"))
        d.exec_()
        self.model['latexPre'] = unicode(frm.latexHeader.toPlainText())
        self.model['latexPost'] = unicode(frm.latexFooter.toPlainText())

    def saveModel(self):
        self.mm.save(self.model)

    # Cleanup
    ##########################################################################

    # need to flush model on change or reject

    def reject(self):
        self.saveModel()
        self.mw.reset()
        saveGeom(self, "models")
        QDialog.reject(self)

class AddModel(QDialog):

    def __init__(self, mw, parent=None):
        self.parent = parent or mw
        self.mw = mw
        self.col = mw.col
        QDialog.__init__(self, self.parent, Qt.Window)
        self.model = None
        self.dialog = aqt.forms.addmodel.Ui_Dialog()
        self.dialog.setupUi(self)
        # standard models
        self.models = []
        for (name, func) in stdmodels.models:
            if callable(name):
                name = name()
            item = QListWidgetItem(_("Add: %s") % name)
            self.dialog.models.addItem(item)
            self.models.append((True, func))
        # add copies
        for m in self.col.models.all():
            item = QListWidgetItem(_("Clone: %s") % m['name'])
            self.dialog.models.addItem(item)
            self.models.append((False, m))
        self.dialog.models.setCurrentRow(0)
        # the list widget will swallow the enter key
        s = QShortcut(QKeySequence("Return"), self)
        self.connect(s, SIGNAL("activated()"), self.accept)
        # help
        self.connect(self.dialog.buttonBox, SIGNAL("helpRequested()"), self.onHelp)

    def get(self):
        self.exec_()
        return self.model

    def reject(self):
        QDialog.reject(self)

    def accept(self):
        (isStd, model) = self.models[self.dialog.models.currentRow()]
        if isStd:
            # create
            self.model = model(self.col)
        else:
            # add copy to deck
            self.model = self.mw.col.models.copy(model)
            self.mw.col.models.setCurrent(self.model)
        QDialog.accept(self)

    def onHelp(self):
        openHelp("notetypes")

########NEW FILE########
__FILENAME__ = overview
# -*- coding: utf-8 -*-
# Copyright: Damien Elmes <anki@ichi2.net>
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

from aqt.qt import *
from anki.consts import NEW_CARDS_RANDOM, dynOrderLabels
from anki.hooks import addHook
from aqt.utils import showInfo, openLink, shortcut
from anki.utils import isMac
import aqt
from anki.sound import clearAudioQueue

class Overview(object):
    "Deck overview."

    def __init__(self, mw):
        self.mw = mw
        self.web = mw.web
        self.bottom = aqt.toolbar.BottomBar(mw, mw.bottomWeb)

    def show(self):
        clearAudioQueue()
        self.web.setLinkHandler(self._linkHandler)
        self.web.setKeyHandler(None)
        self.mw.keyHandler = self._keyHandler
        self.mw.web.setFocus()
        self.refresh()

    def refresh(self):
        self.mw.col.reset()
        self._renderPage()
        self._renderBottom()

    # Handlers
    ############################################################

    def _linkHandler(self, url):
        if url == "study":
            self.mw.col.startTimebox()
            self.mw.moveToState("review")
        elif url == "anki":
            print "anki menu"
        elif url == "opts":
            self.mw.onDeckConf()
        elif url == "cram":
            deck = self.mw.col.decks.current()
            self.mw.onCram("'deck:%s'" % deck['name'])
        elif url == "refresh":
            self.mw.col.sched.rebuildDyn()
            self.mw.reset()
        elif url == "empty":
            self.mw.col.sched.emptyDyn(self.mw.col.decks.selected())
            self.mw.reset()
        elif url == "decks":
            self.mw.moveToState("deckBrowser")
        elif url == "review":
            openLink(aqt.appShared+"info/%s?v=%s"%(self.sid, self.sidVer))
        elif url == "studymore":
            self.onStudyMore()
        else:
            openLink(url)

    def _keyHandler(self, evt):
        cram = self.mw.col.decks.current()['dyn']
        key = unicode(evt.text())
        if key == "o":
            self.mw.onDeckConf()
        if key == "r" and cram:
            self.mw.col.sched.rebuildDyn()
            self.mw.reset()
        if key == "e" and cram:
            self.mw.col.sched.emptyDyn(self.mw.col.decks.selected())
            self.mw.reset()
        if key == "c" and not cram:
            self.onStudyMore()

    # HTML
    ############################################################

    def _renderPage(self):
        but = self.mw.button
        deck = self.mw.col.decks.current()
        self.sid = deck.get("sharedFrom")
        if self.sid:
            self.sidVer = deck.get("ver", None)
            shareLink = '<a class=smallLink href="review">Reviews and Updates</a>'
        else:
            shareLink = ""
        self.web.stdHtml(self._body % dict(
            deck=deck['name'],
            shareLink=shareLink,
            desc=self._desc(deck),
            table=self._table()
            ), self.mw.sharedCSS + self._css)

    def _desc(self, deck):
        if deck['dyn']:
            desc = _("""\
This is a special deck for studying outside of the normal schedule.""")
            desc += " " + _("""\
Cards will be automatically returned to their original decks after you review \
them.""")
            desc += " " + _("""\
Deleting this deck from the deck list will return all remaining cards \
to their original deck.""")
        else:
            desc = deck.get("desc", "")
        if not desc:
            return "<p>"
        if deck['dyn']:
            dyn = "dyn"
        else:
            dyn = ""
        if len(desc) < 160 or dyn:
            return '<div class="descfont descmid description %s">%s</div>' % (
                dyn, desc)
        else:
            return '''
<div class="descfont description descmid" id=shortdesc>%s\
 <a class=smallLink href=# onclick="$('#shortdesc').hide();$('#fulldesc').show();">...More</a></div>
<div class="descfont description descmid" id=fulldesc>%s</div>''' % (
                 desc[:160], desc)

    def _table(self):
        counts = list(self.mw.col.sched.counts())
        finished = not sum(counts)
        for n in range(len(counts)):
            if counts[n] == 1000:
                counts[n] = "1000+"
        but = self.mw.button
        if finished:
            return '<div style="white-space: pre-wrap;">%s</div>' % (
                self.mw.col.sched.finishedMsg())
        else:
            return '''
<table width=300 cellpadding=5>
<tr><td align=center valign=top>
<table cellspacing=5>
<tr><td>%s:</td><td><b><font color=#00a>%s</font></b></td></tr>
<tr><td>%s:</td><td><b><font color=#C35617>%s</font></b></td></tr>
<tr><td>%s:</td><td><b><font color=#0a0>%s</font></b></td></tr>
</table>
</td><td align=center>
%s</td></tr></table>''' % (
    _("New"), counts[0],
    _("Learning"), counts[1],
    _("To Review"), counts[2],
    but("study", _("Study Now"), id="study"))


    _body = """
<center>
<h3>%(deck)s</h3>
%(shareLink)s
%(desc)s
%(table)s
</center>
<script>$(function () { $("#study").focus(); });</script>
"""

    _css = """
.smallLink { font-size: 10px; }
h3 { margin-bottom: 0; }
.descfont {
padding: 1em; color: #333;
}
.description {
white-space: pre-wrap;
}
#fulldesc {
display:none;
}
.descmid {
width: 70%;
margin: 0 auto 0;
text-align: left;
}
.dyn {
text-align: center;
}
"""

    # Bottom area
    ######################################################################

    def _renderBottom(self):
        links = [
            ["o", "opts", _("Options")],
        ]
        if self.mw.col.decks.current()['dyn']:
            links.append(["R", "refresh", _("Rebuild")])
            links.append(["E", "empty", _("Empty")])
        else:
            links.append(["C", "studymore", _("Custom Study")])
            #links.append(["F", "cram", _("Filter/Cram")])
        buf = ""
        for b in links:
            if b[0]:
                b[0] = _("Shortcut key: %s") % shortcut(b[0])
            buf += """
<button title="%s" onclick='py.link(\"%s\");'>%s</button>""" % tuple(b)
        self.bottom.draw(buf)
        if isMac:
            size = 28
        else:
            size = 36 + self.mw.fontHeightDelta*3
        self.bottom.web.setFixedHeight(size)
        self.bottom.web.setLinkHandler(self._linkHandler)

    # Studying more
    ######################################################################

    def onStudyMore(self):
        import aqt.customstudy
        aqt.customstudy.CustomStudy(self.mw)

########NEW FILE########
__FILENAME__ = preferences
# -*- coding: utf-8 -*-
# Copyright: Damien Elmes <anki@ichi2.net>
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

import datetime, time, os
from aqt.qt import *
from aqt.utils import openFolder, showWarning, getText, openHelp, showInfo
import aqt

class Preferences(QDialog):

    def __init__(self, mw):
        if not mw.col:
            showInfo(_("Please open a profile first."))
            return
        QDialog.__init__(self, mw, Qt.Window)
        self.mw = mw
        self.prof = self.mw.pm.profile
        self.form = aqt.forms.preferences.Ui_Preferences()
        self.form.setupUi(self)
        self.connect(self.form.buttonBox, SIGNAL("helpRequested()"),
                     lambda: openHelp("profileprefs"))
        self.setupCollection()
        self.setupNetwork()
        self.setupBackup()
        self.setupOptions()
        self.show()

    def accept(self):
        self.updateCollection()
        self.updateNetwork()
        self.updateBackup()
        self.updateOptions()
        self.mw.pm.save()
        self.mw.reset()
        self.done(0)

    def reject(self):
        self.accept()

    # Collection options
    ######################################################################

    def setupCollection(self):
        import anki.consts as c
        f = self.form
        qc = self.mw.col.conf
        self.startDate = datetime.datetime.fromtimestamp(self.mw.col.crt)
        f.dayOffset.setValue(self.startDate.hour)
        f.lrnCutoff.setValue(qc['collapseTime']/60.0)
        f.timeLimit.setValue(qc['timeLim']/60.0)
        f.showEstimates.setChecked(qc['estTimes'])
        f.showProgress.setChecked(qc['dueCounts'])
        f.newSpread.addItems(c.newCardSchedulingLabels().values())
        f.newSpread.setCurrentIndex(qc['newSpread'])
        f.useCurrent.setCurrentIndex(int(not qc.get("addToCur", True)))

    def updateCollection(self):
        f = self.form
        d = self.mw.col
        qc = d.conf
        qc['dueCounts'] = f.showProgress.isChecked()
        qc['estTimes'] = f.showEstimates.isChecked()
        qc['newSpread'] = f.newSpread.currentIndex()
        qc['timeLim'] = f.timeLimit.value()*60
        qc['collapseTime'] = f.lrnCutoff.value()*60
        qc['addToCur'] = not f.useCurrent.currentIndex()
        hrs = f.dayOffset.value()
        old = self.startDate
        date = datetime.datetime(
            old.year, old.month, old.day, hrs)
        d.crt = int(time.mktime(date.timetuple()))
        d.setMod()

    # Network
    ######################################################################

    def setupNetwork(self):
        self.form.syncOnProgramOpen.setChecked(
            self.prof['autoSync'])
        self.form.syncMedia.setChecked(
            self.prof['syncMedia'])
        if not self.prof['syncKey']:
            self._hideAuth()
        else:
            self.connect(self.form.syncDeauth, SIGNAL("clicked()"),
                         self.onSyncDeauth)

    def _hideAuth(self):
        self.form.syncDeauth.setShown(False)
        self.form.syncLabel.setText(_("""\
<b>Synchronization</b><br>
Not currently enabled; click the sync button in the main window to enable."""))

    def onSyncDeauth(self):
        self.prof['syncKey'] = None
        self._hideAuth()

    def updateNetwork(self):
        self.prof['autoSync'] = self.form.syncOnProgramOpen.isChecked()
        self.prof['syncMedia'] = self.form.syncMedia.isChecked()

    # Backup
    ######################################################################

    def setupBackup(self):
        self.form.numBackups.setValue(self.prof['numBackups'])
        self.connect(self.form.openBackupFolder,
                     SIGNAL("linkActivated(QString)"),
                     self.onOpenBackup)

    def onOpenBackup(self):
        openFolder(self.mw.pm.backupFolder())

    def updateBackup(self):
        self.prof['numBackups'] = self.form.numBackups.value()

    # Basic & Advanced Options
    ######################################################################

    def setupOptions(self):
        self.form.stripHTML.setChecked(self.prof['stripHTML'])
        self.form.pastePNG.setChecked(self.prof.get("pastePNG", False))
        self.connect(
            self.form.profilePass, SIGNAL("clicked()"),
            self.onProfilePass)

    def updateOptions(self):
        self.prof['stripHTML'] = self.form.stripHTML.isChecked()
        self.prof['pastePNG'] = self.form.pastePNG.isChecked()

    def onProfilePass(self):
        pw, ret = getText(_("""\
Lock account with password, or leave blank:"""))
        if not ret:
            return
        if not pw:
            self.prof['key'] = None
            return
        pw2, ret = getText(_("Confirm password:"))
        if not ret:
            return
        if pw != pw2:
            showWarning(_("Passwords didn't match"))
        self.prof['key'] = self.mw.pm._pwhash(pw)

########NEW FILE########
__FILENAME__ = profiles
# Copyright: Damien Elmes <anki@ichi2.net>
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

# Profile handling
##########################################################################
# - Saves in pickles rather than json to easily store Qt window state.
# - Saves in sqlite rather than a flat file so the config can't be corrupted

from aqt.qt import *
import os, sys, time, random, cPickle, shutil, locale, re, atexit, urllib
from anki.db import DB
from anki.utils import isMac, isWin, intTime, checksum
from anki.lang import langs
from aqt.utils import showWarning
from aqt import appHelpSite
import anki.sync
import aqt.forms

metaConf = dict(
    ver=0,
    updates=True,
    created=intTime(),
    id=random.randrange(0, 2**63),
    lastMsg=-1,
    suppressUpdate=False,
    firstRun=True,
    defaultLang=None,
    disabledAddons=[],
)

profileConf = dict(
    # profile
    key=None,
    mainWindowGeom=None,
    mainWindowState=None,
    numBackups=30,
    lastOptimize=intTime(),

    # editing
    fullSearch=False,
    searchHistory=[],
    lastColour="#00f",
    stripHTML=True,
    pastePNG=False,
    # not exposed in gui
    deleteMedia=False,
    preserveKeyboard=True,

    # syncing
    syncKey=None,
    syncMedia=True,
    autoSync=True,
)

class ProfileManager(object):

    def __init__(self, base=None, profile=None):
        self.name = None
        # instantiate base folder
        self.base = base or self._defaultBase()
        self.ensureLocalFS()
        self.ensureBaseExists()
        # load metadata
        self.firstRun = self._loadMeta()
        # did the user request a profile to start up with?
        if profile:
            try:
                self.load(profile)
            except TypeError:
                raise Exception("Provided profile does not exist.")

    # Base creation
    ######################################################################

    def ensureLocalFS(self):
        if self.base.startswith("\\\\"):
            QMessageBox.critical(
                None, "Error", """\
To use Anki on a network share, the share must be mapped to a local drive \
letter. Please see the 'File Locations' section of the manual for more \
information.""")
            raise Exception("unc")

    def ensureBaseExists(self):
        try:
            self._ensureExists(self.base)
        except:
            # can't translate, as lang not initialized
            QMessageBox.critical(
                None, "Error", """\
Anki can't write to the harddisk. Please see the \
documentation for information on using a flash drive.""")
            raise

    # Profile load/save
    ######################################################################

    def profiles(self):
        return sorted(
            unicode(x, "utf8") for x in
            self.db.list("select name from profiles")
            if x != "_global")

    def load(self, name, passwd=None):
        prof = cPickle.loads(
            self.db.scalar("select data from profiles where name = ?",
                           name.encode("utf8")))
        if prof['key'] and prof['key'] != self._pwhash(passwd):
            self.name = None
            return False
        if name != "_global":
            self.name = name
            self.profile = prof
        return True

    def save(self):
        sql = "update profiles set data = ? where name = ?"
        self.db.execute(sql, cPickle.dumps(self.profile),
                        self.name.encode("utf8"))
        self.db.execute(sql, cPickle.dumps(self.meta), "_global")
        self.db.commit()

    def create(self, name):
        prof = profileConf.copy()
        self.db.execute("insert into profiles values (?, ?)",
                        name.encode("utf8"), cPickle.dumps(prof))
        self.db.commit()

    def remove(self, name):
        shutil.rmtree(self.profileFolder())
        self.db.execute("delete from profiles where name = ?",
                        name.encode("utf8"))
        self.db.commit()

    def rename(self, name):
        oldName = self.name
        oldFolder = self.profileFolder()
        self.name = name
        newFolder = self.profileFolder(create=False)
        if os.path.exists(newFolder):
            showWarning(_("Folder already exists."))
            self.name = oldName
            return
        # update name
        self.db.execute("update profiles set name = ? where name = ?",
                        name.encode("utf8"), oldName.encode("utf-8"))
        # rename folder
        os.rename(oldFolder, newFolder)
        self.db.commit()

    # Folder handling
    ######################################################################

    def profileFolder(self, create=True):
        path = os.path.join(self.base, self.name)
        if create:
            self._ensureExists(path)
        return path

    def addonFolder(self):
        return self._ensureExists(os.path.join(self.base, "addons"))

    def backupFolder(self):
        return self._ensureExists(
            os.path.join(self.profileFolder(), "backups"))

    def collectionPath(self):
        return os.path.join(self.profileFolder(), "collection.anki2")

    # Helpers
    ######################################################################

    def _ensureExists(self, path):
        if not os.path.exists(path):
            os.makedirs(path)
        return path

    def _defaultBase(self):
        if isWin:
            s = QSettings(QSettings.UserScope, "Microsoft", "Windows")
            s.beginGroup("CurrentVersion/Explorer/Shell Folders")
            d = s.value("Personal")
            return os.path.join(d, "Anki")
        elif isMac:
            return os.path.expanduser("~/Documents/Anki")
        else:
            return os.path.expanduser("~/Anki")

    def _loadMeta(self):
        path = os.path.join(self.base, "prefs.db")
        new = not os.path.exists(path)
        self.db = DB(path, text=str)
        self.db.execute("""
create table if not exists profiles
(name text primary key, data text not null);""")
        if new:
            # create a default global profile
            self.meta = metaConf.copy()
            self.db.execute("insert into profiles values ('_global', ?)",
                            cPickle.dumps(metaConf))
            self._setDefaultLang()
            return True
        else:
            # load previously created
            self.meta = cPickle.loads(
                self.db.scalar(
                    "select data from profiles where name = '_global'"))

    def ensureProfile(self):
        "Create a new profile if none exists."
        if self.firstRun:
            self.create(_("User 1"))
            p = os.path.join(self.base, "README.txt")
            open(p, "w").write((_("""\
This folder stores all of your Anki data in a single location,
to make backups easy. To tell Anki to use a different location,
please see:

%s
""") % (appHelpSite +  "#startupopts")).encode("utf8"))

    def _pwhash(self, passwd):
        return checksum(unicode(self.meta['id'])+unicode(passwd))

    # Default language
    ######################################################################
    # On first run, allow the user to choose the default language

    def _setDefaultLang(self):
        # the dialog expects _ to be defined, but we're running before
        # setupLang() has been called. so we create a dummy op for now
        import __builtin__
        __builtin__.__dict__['_'] = lambda x: x
        # create dialog
        class NoCloseDiag(QDialog):
            def reject(self):
                pass
        d = self.langDiag = NoCloseDiag()
        f = self.langForm = aqt.forms.setlang.Ui_Dialog()
        f.setupUi(d)
        d.connect(d, SIGNAL("accepted()"), self._onLangSelected)
        d.connect(d, SIGNAL("rejected()"), lambda: True)
        # default to the system language
        try:
            (lang, enc) = locale.getdefaultlocale()
        except:
            # fails on osx
            lang = "en"
        if lang and lang not in ("pt_BR", "zh_CN", "zh_TW"):
            lang = re.sub("(.*)_.*", "\\1", lang)
        # find index
        idx = None
        en = None
        for c, (name, code) in enumerate(langs):
            if code == "en":
                en = c
            if code == lang:
                idx = c
        # if the system language isn't available, revert to english
        if idx is None:
            idx = en
        # update list
        f.lang.addItems([x[0] for x in langs])
        f.lang.setCurrentRow(idx)
        d.exec_()

    def _onLangSelected(self):
        f = self.langForm
        code = langs[f.lang.currentRow()][1]
        self.meta['defaultLang'] = code
        sql = "update profiles set data = ? where name = ?"
        self.db.execute(sql, cPickle.dumps(self.meta), "_global")
        self.db.commit()

########NEW FILE########
__FILENAME__ = progress
# Copyright: Damien Elmes <anki@ichi2.net>
# -*- coding: utf-8 -*-
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

import time
from aqt.qt import *

# fixme: if mw->subwindow opens a progress dialog with mw as the parent, mw
# gets raised on finish on compiz. perhaps we should be using the progress
# dialog as the parent?

# Progress info
##########################################################################

class ProgressManager(object):

    def __init__(self, mw):
        self.mw = mw
        self.app = QApplication.instance()
        self.inDB = False
        self._win = None
        self._levels = 0

    # SQLite progress handler
    ##########################################################################

    def setupDB(self, db):
        "Install a handler in the current DB."
        self.lastDbProgress = 0
        self.inDB = False
        try:
            db.set_progress_handler(self._dbProgress, 10000)
        except:
            print """\
Your pysqlite2 is too old. Anki will appear frozen during long operations."""

    def _dbProgress(self):
        "Called from SQLite."
        # do nothing if we don't have a progress window
        if not self._win:
            return
        # make sure we're not executing too frequently
        if (time.time() - self.lastDbProgress) < 0.01:
            return
        self.lastDbProgress = time.time()
        # and we're in the main thread
        if not self.mw.inMainThread():
            return
        # ensure timers don't fire
        self.inDB = True
        # handle GUI events
        self._maybeShow()
        self.app.processEvents(QEventLoop.ExcludeUserInputEvents)
        self.inDB = False

    # DB-safe timers
    ##########################################################################
    # QTimer may fire in processEvents(). We provide a custom timer which
    # automatically defers until the DB is not busy.

    def timer(self, ms, func, repeat):
        def handler():
            if self.inDB:
                # retry in 100ms
                self.timer(100, func, repeat)
            else:
                func()
        t = QTimer(self.mw)
        if not repeat:
            t.setSingleShot(True)
        t.connect(t, SIGNAL("timeout()"), handler)
        t.start(ms)
        return t

    # Creating progress dialogs
    ##########################################################################

    class ProgressNoCancel(QProgressDialog):
        def closeEvent(self, evt):
            evt.ignore()
        def keyPressEvent(self, evt):
            if evt.key() == Qt.Key_Escape:
                evt.ignore()

    def start(self, max=0, min=0, label=None, parent=None, immediate=False):
        self._levels += 1
        if self._levels > 1:
            return
        # setup window
        parent = parent or self.app.activeWindow() or self.mw
        label = label or _("Processing...")
        self._win = self.ProgressNoCancel(label, "", min, max, parent)
        self._win.setWindowTitle("Anki")
        self._win.setCancelButton(None)
        self._win.setAutoClose(False)
        self._win.setAutoReset(False)
        self._win.setWindowModality(Qt.ApplicationModal)
        # we need to manually manage minimum time to show, as qt gets confused
        # by the db handler
        self._win.setMinimumDuration(100000)
        if immediate:
            self._shown = True
            self._win.show()
            self.app.processEvents()
        else:
            self._shown = False
        self._counter = min
        self._min = min
        self._max = max
        self._firstTime = time.time()
        self._lastTime = time.time()
        self._disabled = False

    def update(self, label=None, value=None, process=True, maybeShow=True):
        #print self._min, self._counter, self._max, label, time.time() - self._lastTime
        if maybeShow:
            self._maybeShow()
        self._lastTime = time.time()
        if label:
            self._win.setLabelText(label)
        if self._max and self._shown:
            self._counter = value or (self._counter+1)
            self._win.setValue(self._counter)
        if process:
            self.app.processEvents(QEventLoop.ExcludeUserInputEvents)

    def finish(self):
        self._levels -= 1
        self._levels = max(0, self._levels)
        if self._levels == 0 and self._win:
            self._win.cancel()
            self._unsetBusy()

    def clear(self):
        "Restore the interface after an error."
        if self._levels:
            self._levels = 1
            self.finish()

    def _maybeShow(self):
        if not self._levels:
            return
        if self._shown:
            self.update(maybeShow=False)
            return
        delta = time.time() - self._firstTime
        if delta > 0.5:
            self._shown = True
            self._win.show()
            self._setBusy()

    def _setBusy(self):
        self._disabled = True
        self.mw.app.setOverrideCursor(QCursor(Qt.WaitCursor))

    def _unsetBusy(self):
        self._disabled = False
        self.app.restoreOverrideCursor()

    def busy(self):
        "True if processing."
        return self._levels

########NEW FILE########
__FILENAME__ = qt
# Copyright: Damien Elmes <anki@ichi2.net>
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

# imports are all in this file to make moving to pyside easier in the future

import sip, os
sip.setapi('QString', 2)
sip.setapi('QVariant', 2)
sip.setapi('QUrl', 2)
from PyQt4.QtCore import *
from PyQt4.QtGui import *
from PyQt4.QtWebKit import QWebPage, QWebView, QWebSettings
from PyQt4.QtNetwork import QLocalServer, QLocalSocket
from PyQt4 import pyqtconfig

def debug():
  from PyQt4.QtCore import pyqtRemoveInputHook
  from pdb import set_trace
  pyqtRemoveInputHook()
  set_trace()

if os.environ.get("DEBUG"):
    import sys, traceback
    def info(type, value, tb):
        from PyQt4.QtCore import pyqtRemoveInputHook
        for line in traceback.format_exception(type, value, tb):
            sys.stdout.write(line)
        pyqtRemoveInputHook()
        from pdb import pm
        pm()
    sys.excepthook = info

qtconf = pyqtconfig.Configuration()
qtmajor = (qtconf.qt_version & 0xff0000) >> 16
qtminor = (qtconf.qt_version & 0x00ff00) >> 8


########NEW FILE########
__FILENAME__ = reviewer
# -*- coding: utf-8 -*-
# Copyright: Damien Elmes <anki@ichi2.net>
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

import time, os, stat, shutil, difflib, re, cgi
import unicodedata as ucd
import HTMLParser
from aqt.qt import *
from anki.utils import fmtTimeSpan, stripHTML, isMac, json
from anki.hooks import addHook, runHook, runFilter
from anki.sound import playFromText, clearAudioQueue, hasSound, play
from aqt.utils import mungeQA, getBase, shortcut, openLink, tooltip
from aqt.sound import getAudio
import aqt

class Reviewer(object):
    "Manage reviews.  Maintains a separate state."

    def __init__(self, mw):
        self.mw = mw
        self.web = mw.web
        self.card = None
        self.cardQueue = []
        self.hadCardQueue = False
        self._answeredIds = []
        self._recordedAudio = None
        self.typeCorrect = None # web init happens before this is set
        self.state = None
        self.bottom = aqt.toolbar.BottomBar(mw, mw.bottomWeb)
        addHook("leech", self.onLeech)

    def show(self):
        self.mw.col.reset()
        self.mw.keyHandler = self._keyHandler
        self.web.setLinkHandler(self._linkHandler)
        self.web.setKeyHandler(self._catchEsc)
        if isMac:
            self.bottom.web.setFixedHeight(46)
        else:
            self.bottom.web.setFixedHeight(52+self.mw.fontHeightDelta*4)
        self.bottom.web.setLinkHandler(self._linkHandler)
        self._reps = None
        self.nextCard()

    def lastCard(self):
        if self._answeredIds:
            if not self.card or self._answeredIds[-1] != self.card.id:
                try:
                    return self.mw.col.getCard(self._answeredIds[-1])
                except TypeError:
                    # id was deleted
                    return

    def cleanup(self):
        runHook("reviewCleanup")

    # Fetching a card
    ##########################################################################

    def nextCard(self):
        elapsed = self.mw.col.timeboxReached()
        if elapsed:
            part1 = ngettext("%d card studied in", "%d cards studied in", elapsed[1]) % elapsed[1]
            part2 = ngettext("%s minute.", "%s minutes.", elapsed[0]/60) % (elapsed[0]/60)
            tooltip("%s %s" % (part1, part2), period=5000)
            self.mw.col.startTimebox()
        if self.cardQueue:
            # undone/edited cards to show
            c = self.cardQueue.pop()
            c.startTimer()
            self.hadCardQueue = True
        else:
            if self.hadCardQueue:
                # the undone/edited cards may be sitting in the regular queue;
                # need to reset
                self.mw.col.reset()
                self.hadCardQueue = False
            c = self.mw.col.sched.getCard()
        self.card = c
        clearAudioQueue()
        if not c:
            self.mw.moveToState("overview")
            return
        if self._reps is None or self._reps % 100 == 0:
            # we recycle the webview periodically so webkit can free memory
            self._initWeb()
        else:
            self._showQuestion()

    # Audio
    ##########################################################################

    def replayAudio(self):
        clearAudioQueue()
        c = self.card
        if self.state == "question":
            playFromText(c.q())
        elif self.state == "answer":
            txt = ""
            if self._replayq(c):
                txt = c.q()
            txt += c.a()
            playFromText(txt)

    # Initializing the webview
    ##########################################################################

    _revHtml = """
<img src="qrc:/icons/rating.png" class=marked>
<div id=qa></div>
<script>
var ankiPlatform = "desktop";
var typeans;
function _updateQA (q, answerMode, klass) {
    $("#qa").html(q);
    typeans = document.getElementById("typeans");
    if (typeans) {
        typeans.focus();
    }
    if (answerMode) {
        window.location = "#answer";
    } else {
        window.scrollTo(0, 0);
    }
    if (klass) {
        document.body.className = klass;
    }
};

function _toggleStar (show) {
    if (show) {
        $(".marked").show();
    } else {
        $(".marked").hide();
    }
}

function _getTypedText () {
    if (typeans) {
        py.link("typeans:"+typeans.value);
    }
};
function _typeAnsPress() {
    if (window.event.keyCode === 13) {
        py.link("ansHack");
    }
}
</script>
"""

    def _initWeb(self):
        self._reps = 0
        self._bottomReady = False
        base = getBase(self.mw.col)
        # main window
        self.web.stdHtml(self._revHtml, self._styles(),
            loadCB=lambda x: self._showQuestion(),
            head=base)
        # show answer / ease buttons
        self.bottom.web.show()
        self.bottom.web.stdHtml(
            self._bottomHTML(),
            self.bottom._css + self._bottomCSS,
        loadCB=lambda x: self._showAnswerButton())

    # Showing the question
    ##########################################################################

    def _mungeQA(self, buf):
        return self.mw.col.media.escapeImages(
            self.typeAnsFilter(mungeQA(buf)))

    def _showQuestion(self):
        self._reps += 1
        self.state = "question"
        self.typedAnswer = None
        c = self.card
        # grab the question and play audio
        if c.isEmpty():
            q = _("""\
The front of this card is empty. Please run Tools>Maintenance>Empty Cards.""")
        else:
            q = c.q()
        if self._autoplay(c):
            playFromText(q)
        # render & update bottom
        q = self._mungeQA(q)
        klass = "card card%d" % (c.ord+1)
        self.web.eval("_updateQA(%s, false, '%s');" % (json.dumps(q), klass))
        self._toggleStar()
        if self._bottomReady:
            self._showAnswerButton()
        # if we have a type answer field, focus main web
        if self.typeCorrect:
            self.mw.web.setFocus()
        # user hook
        runHook('showQuestion')

    def _autoplay(self, card):
        return self.mw.col.decks.confForDid(
            self.card.odid or self.card.did)['autoplay']

    def _replayq(self, card):
        return self.mw.col.decks.confForDid(
            self.card.odid or self.card.did).get('replayq', True)

    def _toggleStar(self):
        self.web.eval("_toggleStar(%s);" % json.dumps(
            self.card.note().hasTag("marked")))

    # Showing the answer
    ##########################################################################

    def _showAnswer(self):
        if self.mw.state != "review":
            # showing resetRequired screen; ignore space
            return
        self.state = "answer"
        c = self.card
        a = c.a()
        # play audio?
        if self._autoplay(c):
            playFromText(a)
        # render and update bottom
        a = self._mungeQA(a)
        self.web.eval("_updateQA(%s, true);" % json.dumps(a))
        self._showEaseButtons()
        # user hook
        runHook('showAnswer')

    # Answering a card
    ############################################################

    def _answerCard(self, ease):
        "Reschedule card and show next."
        if self.mw.state != "review":
            # showing resetRequired screen; ignore key
            return
        if self.state != "answer":
            return
        if self.mw.col.sched.answerButtons(self.card) < ease:
            return
        self.mw.col.sched.answerCard(self.card, ease)
        self._answeredIds.append(self.card.id)
        self.mw.autosave()
        self.nextCard()

    # Handlers
    ############################################################

    def _catchEsc(self, evt):
        if evt.key() == Qt.Key_Escape:
            self.web.eval("$('#typeans').blur();")
            return True

    def _showAnswerHack(self):
        # on <qt4.8, calling _showAnswer() directly fails to show images on
        # the answer side. But if we trigger it via the bottom web's python
        # link, it inexplicably works.
        self.bottom.web.eval("py.link('ans');")

    def _keyHandler(self, evt):
        key = unicode(evt.text())
        if key == "e":
            self.mw.onEditCurrent()
        elif (key == " " or evt.key() in (Qt.Key_Return, Qt.Key_Enter)):
            if self.state == "question":
                self._showAnswerHack()
            elif self.state == "answer":
                self._answerCard(self._defaultEase())
        elif key == "r" or evt.key() == Qt.Key_F5:
            self.replayAudio()
        elif key == "*":
            self.onMark()
        elif key == "-":
            self.onBuryNote()
        elif key == "!":
            self.onSuspend()
        elif key == "V":
            self.onRecordVoice()
        elif key == "o":
            self.onOptions()
        elif key in ("1", "2", "3", "4"):
            self._answerCard(int(key))
        elif key == "v":
            self.onReplayRecorded()
        elif evt.key() == Qt.Key_Delete:
            self.onDelete()

    def _linkHandler(self, url):
        if url == "ans":
            self._showAnswer()
        elif url == "ansHack":
            self.mw.progress.timer(100, self._showAnswerHack, False)
        elif url.startswith("ease"):
            self._answerCard(int(url[4:]))
        elif url == "edit":
            self.mw.onEditCurrent()
        elif url == "more":
            self.showContextMenu()
        elif url.startswith("typeans:"):
            (cmd, arg) = url.split(":", 1)
            self.typedAnswer = arg
        else:
            openLink(url)

    # CSS
    ##########################################################################

    _css = """
hr { background-color:#ccc; margin: 1em; }
body { margin:1.5em; }
img { max-width: 95%; max-height: 95%; }
.marked { position:absolute; right: 7px; top: 7px; display: none; }
#typeans { width: 100%; }
"""

    def _styles(self):
        return self._css

    # Type in the answer
    ##########################################################################

    failedCharColour = "#FF0000"
    passedCharColour = "#00FF00"
    typeAnsPat = "\[\[type:(.+?)\]\]"

    def typeAnsFilter(self, buf):
        if self.state == "question":
            return self.typeAnsQuestionFilter(buf)
        else:
            return self.typeAnsAnswerFilter(buf)

    def typeAnsQuestionFilter(self, buf):
        self.typeCorrect = None
        clozeIdx = None
        m = re.search(self.typeAnsPat, buf)
        if not m:
            return buf
        fld = m.group(1)
        # if it's a cloze, extract data
        if fld.startswith("cloze:"):
            # get field and cloze position
            clozeIdx = self.card.ord + 1
            fld = fld.split(":")[1]
        # loop through fields for a match
        for f in self.card.model()['flds']:
            if f['name'] == fld:
                self.typeCorrect = self.card.note()[f['name']]
                if clozeIdx:
                    # narrow to cloze
                    self.typeCorrect = self._contentForCloze(
                        self.typeCorrect, clozeIdx)
                self.typeFont = f['font']
                self.typeSize = f['size']
                break
        if not self.typeCorrect:
            if self.typeCorrect is None:
                if clozeIdx:
                    warn = _("""\
Please run Tools>Maintenance>Empty Cards""")
                else:
                    warn = _("Type answer: unknown field %s") % fld
                return re.sub(self.typeAnsPat, warn, buf)
            else:
                # empty field, remove type answer pattern
                return re.sub(self.typeAnsPat, "", buf)
        return re.sub(self.typeAnsPat, """
<center>
<input type=text id=typeans onkeypress="_typeAnsPress();"
   style="font-family: '%s'; font-size: %spx;">
</center>
""" % (self.typeFont, self.typeSize), buf)

    def typeAnsAnswerFilter(self, buf):
        if not self.typeCorrect:
            return re.sub(self.typeAnsPat, "", buf)
        # tell webview to call us back with the input content
        self.web.eval("_getTypedText();")
        # munge correct value
        parser = HTMLParser.HTMLParser()
        cor = stripHTML(self.mw.col.media.strip(self.typeCorrect))
        cor = parser.unescape(cor)
        given = self.typedAnswer
        # compare with typed answer
        res = self.correct(cor, given)
        if cor != given:
            # Wrap the extra text in an id-ed span.
            res += u"<span id=rightanswer><br> {0} <br> {1} </span>".format(
                _(u"Correct answer was:"), cor)
        # and update the type answer area
        def repl(match):
            # can't pass a string in directly, and can't use re.escape as it
            # escapes too much
            return """
<span style="font-family: '%s'; font-size: %spx">%s</span>""" % (
                self.typeFont, self.typeSize, res)
        return re.sub(self.typeAnsPat, repl, buf)

    def _contentForCloze(self, txt, idx):
        matches = re.findall("\{\{c%s::(.+?)\}\}"%idx, txt)
        if not matches:
            return None
        def noHint(txt):
            if "::" in txt:
                return txt.split("::")[0]
            return txt
        matches = [noHint(txt) for txt in matches]
        if len(matches) > 1:
            txt = ", ".join(matches)
        else:
            txt = matches[0]
        return txt

    # following type answer functions thanks to Bernhard
    def calculateOkBadStyle(self):
        "Precalculates styles for correct and incorrect part of answer"
        st = "background: %s; color: #000;"
        self.styleOk  = st % self.passedCharColour
        self.styleBad = st % self.failedCharColour

    def ok(self, a):
        "returns given sring in style correct (green)"
        if len(a) == 0:
            return ""
        return "<span style='%s'>%s</span>" % (self.styleOk, cgi.escape(a))

    def bad(self, a):
        "returns given sring in style incorrect (red)"
        if len(a) == 0:
            return ""
        return "<span style='%s'>%s</span>" % (self.styleBad, cgi.escape(a))

    def applyStyle(self, testChar, correct, wrong):
        "Calculates answer fragment depending on testChar's unicode category"
        ZERO_SIZE = 'Mn'
        def head(a):
            return a[:len(a) - 1]
        def tail(a):
            return a[len(a) - 1:]
        if ucd.category(testChar) == ZERO_SIZE:
            return self.ok(head(correct)) + self.bad(tail(correct) + wrong)
        return self.ok(correct) + self.bad(wrong)

    def correct(self, a, b):
        "Diff-corrects the typed-in answer."
        if b == "":
            return "";
        self.calculateOkBadStyle()
        ret = ""
        lastEqual = ""
        s = difflib.SequenceMatcher(None, b, a)
        for tag, i1, i2, j1, j2 in s.get_opcodes():
            if tag == "equal":
                lastEqual = b[i1:i2]
            elif tag == "replace":
                ret += self.applyStyle(b[i1], lastEqual,
                                 b[i1:i2] + ("-" * ((j2 - j1) - (i2 - i1))))
                lastEqual = ""
            elif tag == "delete":
                ret += self.applyStyle(b[i1], lastEqual, b[i1:i2])
                lastEqual = ""
            elif tag == "insert":
                if ucd.category(a[j1]) != 'Mn':
                    dashNum = (j2 - j1)
                else:
                    dashNum = ((j2 - j1) - 1)
                ret += self.applyStyle(a[j1], lastEqual, "-" * dashNum)
                lastEqual = ""
        return ret + self.ok(lastEqual)

    # Bottom bar
    ##########################################################################

    _bottomCSS = """
body {
background: -webkit-gradient(linear, left top, left bottom,
from(#fff), to(#ddd));
border-bottom: 0;
border-top: 1px solid #aaa;
margin: 0;
padding: 0px;
padding-left: 5px; padding-right: 5px;
}
button {
min-width: 60px; white-space: nowrap;
}
.hitem { margin-top: 2px; }
.stat { padding-top: 5px; }
.stat2 { padding-top: 3px; font-weight: normal; }
.stattxt { padding-left: 5px; padding-right: 5px; white-space: nowrap; }
.nobold { font-weight: normal; display: inline-block; padding-top: 4px; }
.spacer { height: 18px; }
.spacer2 { height: 16px; }
"""

    def _bottomHTML(self):
        return """
<table width=100%% cellspacing=0 cellpadding=0>
<tr>
<td align=left width=50 valign=top class=stat>
<br>
<button title="%(editkey)s" onclick="py.link('edit');">%(edit)s</button></td>
<td align=center valign=top id=middle>
</td>
<td width=50 align=right valign=top class=stat><span id=time class=stattxt>
</span><br>
<button onclick="py.link('more');">%(more)s &#9662;</button>
</td>
</tr>
</table>
<script>
var time = %(time)d;
var maxTime = 0;
$(function () {
$("#ansbut").focus();
updateTime();
setInterval(function () { time += 1; updateTime() }, 1000);
});

var updateTime = function () {
    if (!maxTime) {
        $("#time").text("");
        return;
    }
    time = Math.min(maxTime, time);
    var m = Math.floor(time / 60);
    var s = time %% 60;
    if (s < 10) {
        s = "0" + s;
    }
    var e = $("#time");
    if (maxTime == time) {
        e.html("<font color=red>" + m + ":" + s + "</font>");
    } else {
        e.text(m + ":" + s);
    }
}

function showQuestion(txt, maxTime_) {
  // much faster than jquery's .html()
  $("#middle")[0].innerHTML = txt;
  $("#ansbut").focus();
  time = 0;
  maxTime = maxTime_;
}

function showAnswer(txt) {
  $("#middle")[0].innerHTML = txt;
  $("#defease").focus();
}

</script>
""" % dict(rem=self._remaining(), edit=_("Edit"),
           editkey=_("Shortcut key: %s") % "E",
           more=_("More"), time=self.card.timeTaken()/1000)

    def _showAnswerButton(self):
        self._bottomReady = True
        if not self.typeCorrect:
            self.bottom.web.setFocus()
        middle = '''
<span class=stattxt>%s</span><br>
<button title="%s" id=ansbut onclick='py.link(\"ans\");'>%s</button>''' % (
        self._remaining(), _("Shortcut key: %s") % _("Space"), _("Show Answer"))
        # wrap it in a table so it has the same top margin as the ease buttons
        middle = "<table cellpadding=0><tr><td class=stat2 align=center>%s</td></tr></table>" % middle
        if self.card.shouldShowTimer():
            maxTime = self.card.timeLimit() / 1000
        else:
            maxTime = 0
        self.bottom.web.eval("showQuestion(%s,%d);" % (
            json.dumps(middle), maxTime))

    def _showEaseButtons(self):
        self.bottom.web.setFocus()
        middle = self._answerButtons()
        self.bottom.web.eval("showAnswer(%s);" % json.dumps(middle))

    def _remaining(self):
        if not self.mw.col.conf['dueCounts']:
            return ""
        if self.hadCardQueue:
            # if it's come from the undo queue, don't count it separately
            counts = list(self.mw.col.sched.counts())
        else:
            counts = list(self.mw.col.sched.counts(self.card))
        idx = self.mw.col.sched.countIdx(self.card)
        counts[idx] = "<u>%s</u>" % (counts[idx])
        space = " + "
        ctxt = '<font color="#000099">%s</font>' % counts[0]
        ctxt += space + '<font color="#C35617">%s</font>' % counts[1]
        ctxt += space + '<font color="#007700">%s</font>' % counts[2]
        return ctxt

    def _defaultEase(self):
        if self.mw.col.sched.answerButtons(self.card) == 4:
            return 3
        else:
            return 2

    def _answerButtonList(self):
        l = ((1, _("Again")),)
        cnt = self.mw.col.sched.answerButtons(self.card)
        if cnt == 2:
            return l + ((2, _("Good")),)
        elif cnt == 3:
            return l + ((2, _("Good")), (3, _("Easy")))
        else:
            return l + ((2, _("Hard")), (3, _("Good")), (4, _("Easy")))

    def _answerButtons(self):
        times = []
        default = self._defaultEase()
        def but(i, label):
            if i == default:
                extra = "id=defease"
            else:
                extra = ""
            due = self._buttonTime(i)
            return '''
<td align=center>%s<button %s title="%s" onclick='py.link("ease%d");'>\
%s</button></td>''' % (due, extra, _("Shortcut key: %s") % i, i, label)
        buf = "<center><table cellpading=0 cellspacing=0><tr>"
        for ease, label in self._answerButtonList():
            buf += but(ease, label)
        buf += "</tr></table>"
        script = """
<script>$(function () { $("#defease").focus(); });</script>"""
        return buf + script

    def _buttonTime(self, i):
        if not self.mw.col.conf['estTimes']:
            return "<div class=spacer></div>"
        txt = self.mw.col.sched.nextIvlStr(self.card, i, True) or "&nbsp;"
        return '<span class=nobold>%s</span><br>' % txt

    # Leeches
    ##########################################################################

    def onLeech(self, card):
        # for now
        s = _("Card was a leech.")
        if card.queue < 0:
            s += " " + _("It has been suspended.")
        tooltip(s)

    # Context menu
    ##########################################################################

    # note the shortcuts listed here also need to be defined above
    def showContextMenu(self):
        opts = [
            [_("Mark Note"), "*", self.onMark],
            [_("Bury Note"), "-", self.onBuryNote],
            [_("Suspend Note"), "!", self.onSuspend],
            [_("Delete Note"), "Delete", self.onDelete],
            [_("Options"), "O", self.onOptions],
            None,
            [_("Replay Audio"), "R", self.replayAudio],
            [_("Record Own Voice"), "Shift+V", self.onRecordVoice],
            [_("Replay Own Voice"), "V", self.onReplayRecorded],
        ]
        m = QMenu(self.mw)
        for row in opts:
            if not row:
                m.addSeparator()
                continue
            label, scut, func = row
            a = m.addAction(label)
            a.setShortcut(QKeySequence(scut))
            a.connect(a, SIGNAL("triggered()"), func)
        m.exec_(QCursor.pos())

    def onOptions(self):
        self.mw.onDeckConf(self.mw.col.decks.get(
            self.card.odid or self.card.did))

    def onMark(self):
        f = self.card.note()
        if f.hasTag("marked"):
            f.delTag("marked")
        else:
            f.addTag("marked")
        f.flush()
        self._toggleStar()

    def onSuspend(self):
        self.mw.checkpoint(_("Suspend"))
        self.mw.col.sched.suspendCards(
            [c.id for c in self.card.note().cards()])
        tooltip(_("Note suspended."))
        self.mw.reset()

    def onDelete(self):
        self.mw.checkpoint(_("Delete"))
        cnt = len(self.card.note().cards())
        self.mw.col.remNotes([self.card.note().id])
        self.mw.reset()
        tooltip(ngettext(
            "Note and its %d card deleted.",
            "Note and its %d cards deleted.",
            cnt) % cnt)

    def onBuryNote(self):
        self.mw.checkpoint(_("Bury"))
        self.mw.col.sched.buryNote(self.card.nid)
        self.mw.reset()
        tooltip(_("Note buried."))

    def onRecordVoice(self):
        self._recordedAudio = getAudio(self.mw, encode=False)
        self.onReplayRecorded()

    def onReplayRecorded(self):
        if not self._recordedAudio:
            return tooltip(_("You haven't recorded your voice yet."))
        clearAudioQueue()
        play(self._recordedAudio)

########NEW FILE########
__FILENAME__ = sound
# Copyright: Damien Elmes <anki@ichi2.net>
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

from aqt.qt import *

import time
from anki.sound import Recorder, play
from aqt.utils import saveGeom, restoreGeom

def getAudio(parent, encode=True):
    "Record and return filename"
    # record first
    r = Recorder()
    mb = QMessageBox(parent)
    restoreGeom(mb, "audioRecorder")
    mb.setWindowTitle("Anki")
    mb.setIconPixmap(QPixmap(":/icons/media-record.png"))
    but = QPushButton(_("  Stop"))
    but.setIcon(QIcon(":/icons/media-playback-stop.png"))
    #but.setIconSize(QSize(32, 32))
    mb.addButton(but, QMessageBox.RejectRole)
    t = time.time()
    r.start()
    QApplication.instance().processEvents()
    while not mb.clickedButton():
        txt =_("Recording...<br>Time: %0.1f")
        mb.setText(txt % (time.time() - t))
        mb.show()
        QApplication.instance().processEvents()
    saveGeom(mb, "audioRecorder")
    # ensure at least a second captured
    while time.time() - t < 1:
        time.sleep(0.1)
    r.stop()
    # process
    r.postprocess(encode)
    return r.file()

########NEW FILE########
__FILENAME__ = stats
# Copyright: Damien Elmes <anki@ichi2.net>
# -*- coding: utf-8 -*-
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

from aqt.qt import *
import os, time
from aqt.webview import AnkiWebView
from aqt.utils import saveGeom, restoreGeom, maybeHideClose, openFolder, \
    showInfo
from anki.utils import namedtmp
from anki.hooks import addHook
import aqt

# Deck Stats
######################################################################

class DeckStats(QDialog):

    def __init__(self, mw):
        QDialog.__init__(self, mw, Qt.Window)
        self.mw = mw
        self.name = "deckStats"
        self.period = 0
        self.form = aqt.forms.stats.Ui_Dialog()
        self.oldPos = None
        self.wholeCollection = False
        self.setMinimumWidth(700)
        f = self.form
        f.setupUi(self)
        restoreGeom(self, self.name)
        b = f.buttonBox.addButton(_("Save Image"),
                                          QDialogButtonBox.ActionRole)
        b.connect(b, SIGNAL("clicked()"), self.browser)
        b.setAutoDefault(False)
        c = self.connect
        s = SIGNAL("clicked()")
        c(f.groups, s, lambda: self.changeScope("deck"))
        f.groups.setShortcut("g")
        c(f.all, s, lambda: self.changeScope("collection"))
        c(f.month, s, lambda: self.changePeriod(0))
        c(f.year, s, lambda: self.changePeriod(1))
        c(f.life, s, lambda: self.changePeriod(2))
        c(f.web, SIGNAL("loadFinished(bool)"), self.loadFin)
        maybeHideClose(self.form.buttonBox)
        self.refresh()
        self.exec_()

    def reject(self):
        saveGeom(self, self.name)
        QDialog.reject(self)

    def browser(self):
        name = time.strftime("-%Y-%m-%d@%H-%M-%S.png",
                             time.localtime(time.time()))
        name = "anki-"+_("stats")+name
        path = os.path.join(
            QDesktopServices.storageLocation(QDesktopServices.DesktopLocation),
            name)
        p = self.form.web.page()
        oldsize = p.viewportSize()
        p.setViewportSize(p.mainFrame().contentsSize())
        image = QImage(p.viewportSize(), QImage.Format_ARGB32)
        painter = QPainter(image)
        p.mainFrame().render(painter)
        painter.end()
        image.save(path, "png")
        p.setViewportSize(oldsize)
        showInfo(_("An image was saved to your desktop."))

    def changePeriod(self, n):
        self.period = n
        self.refresh()

    def changeScope(self, type):
        self.wholeCollection = type == "collection"
        self.refresh()

    def loadFin(self, b):
        self.form.web.page().mainFrame().setScrollPosition(self.oldPos)

    def refresh(self):
        self.mw.progress.start(immediate=True)
        self.oldPos = self.form.web.page().mainFrame().scrollPosition()
        stats = self.mw.col.stats()
        stats.wholeCollection = self.wholeCollection
        self.report = stats.report(type=self.period)
        self.form.web.setHtml(self.report)
        self.mw.progress.finish()

########NEW FILE########
__FILENAME__ = studydeck
# Copyright: Damien Elmes <anki@ichi2.net>
# -*- coding: utf-8 -*-
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

from aqt.qt import *
import aqt
from anki.utils import ids2str
from aqt.utils import showInfo, showWarning, openHelp, getOnlyText, shortcut
from operator import itemgetter
from anki.hooks import addHook, remHook

class StudyDeck(QDialog):
    def __init__(self, mw, names=None, accept=None, title=None,
                 help="studydeck", current=None, cancel=True,
                 parent=None, dyn=False, buttons=[]):
        QDialog.__init__(self, parent or mw)
        self.mw = mw
        self.form = aqt.forms.studydeck.Ui_Dialog()
        self.form.setupUi(self)
        self.form.filter.installEventFilter(self)
        self.cancel = cancel
        addHook('reset', self.onReset)
        if not cancel:
            self.form.buttonBox.removeButton(
                self.form.buttonBox.button(QDialogButtonBox.Cancel))
        if buttons:
            for b in buttons:
                self.form.buttonBox.addButton(b, QDialogButtonBox.ActionRole)
        else:
            b = QPushButton(_("Add"))
            b.setShortcut(QKeySequence("Ctrl+N"))
            b.setToolTip(shortcut(_("Add New Deck (Ctrl+N)")))
            self.form.buttonBox.addButton(b, QDialogButtonBox.ActionRole)
            b.connect(b, SIGNAL("clicked()"), self.onAddDeck)
        if title:
            self.setWindowTitle(title)
        if not names:
            names = sorted(self.mw.col.decks.allNames(dyn=dyn))
            self.nameFunc = None
            self.origNames = names
        else:
            self.nameFunc = names
            self.origNames = names()
        self.name = None
        self.ok = self.form.buttonBox.addButton(
            accept or _("Study"), QDialogButtonBox.AcceptRole)
        self.setWindowModality(Qt.WindowModal)
        self.connect(self.form.buttonBox,
                     SIGNAL("helpRequested()"),
                     lambda: openHelp(help))
        self.connect(self.form.filter,
                     SIGNAL("textEdited(QString)"),
                     self.redraw)
        self.connect(self.form.list,
                     SIGNAL("itemDoubleClicked(QListWidgetItem*)"),
                     self.accept)
        self.show()
        # redraw after show so position at center correct
        self.redraw("", current)
        self.exec_()

    def eventFilter(self, obj, evt):
        if evt.type() == QEvent.KeyPress:
            if evt.key() == Qt.Key_Up:
                c = self.form.list.count()
                row = self.form.list.currentRow() - 1
                if row < 0:
                    row = c - 1
                self.form.list.setCurrentRow(row)
                return True
            elif evt.key() == Qt.Key_Down:
                c = self.form.list.count()
                row = self.form.list.currentRow() + 1
                if row == c:
                    row = 0
                self.form.list.setCurrentRow(row)
                return True
        return False

    def redraw(self, filt, focus=None):
        self.filt = filt
        self.focus = focus
        self.names = [n for n in self.origNames if self._matches(n, filt)]
        l = self.form.list
        l.clear()
        l.addItems(self.names)
        if focus in self.names:
            idx = self.names.index(focus)
        else:
            idx = 0
        l.setCurrentRow(idx)
        l.scrollToItem(l.item(idx), QAbstractItemView.PositionAtCenter)

    def _matches(self, name, filt):
        name = name.lower()
        filt = filt.lower()
        if not filt:
            return True
        for c in filt:
            if c not in name:
                return False
            name = name[name.index(c)+1:]
        return True

    def onReset(self):
        # model updated?
        if self.nameFunc:
            self.origNames = self.nameFunc()
        self.redraw(self.filt, self.focus)

    def accept(self):
        remHook('reset', self.onReset)
        row = self.form.list.currentRow()
        if row < 0:
            showInfo(_("Please select something."))
            return
        self.name = self.names[self.form.list.currentRow()]
        QDialog.accept(self)

    def reject(self):
        remHook('reset', self.onReset)
        if not self.cancel:
            return self.accept()
        QDialog.reject(self)

    def onAddDeck(self):
        row = self.form.list.currentRow()
        if row < 0:
            default = self.form.filter.text()
        else:
            default = self.names[self.form.list.currentRow()]
        n = getOnlyText(_("New deck name:"), default=default)
        if n:
            self.mw.col.decks.id(n)
            self.name = n
            # make sure we clean up reset hook when manually exiting
            remHook('reset', self.onReset)
            QDialog.accept(self)

########NEW FILE########
__FILENAME__ = sync
# Copyright: Damien Elmes <anki@ichi2.net>
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

from aqt.qt import *
import os, types, socket, time, traceback, gc
import aqt
from anki import Collection
from anki.sync import Syncer, RemoteServer, FullSyncer, MediaSyncer, \
    RemoteMediaServer
from anki.hooks import addHook, remHook
from aqt.utils import tooltip, askUserDialog, showWarning, showText

# Sync manager
######################################################################

class SyncManager(QObject):

    def __init__(self, mw, pm):
        QObject.__init__(self, mw)
        self.mw = mw
        self.pm = pm

    def sync(self):
        if not self.pm.profile['syncKey']:
            auth = self._getUserPass()
            if not auth:
                return
            self._sync(auth)
        else:
            self._sync()

    def _sync(self, auth=None):
        # to avoid gui widgets being garbage collected in the worker thread,
        # run gc in advance
        gc.collect()
        # create the thread, setup signals and start running
        t = self.thread = SyncThread(
            self.pm.collectionPath(), self.pm.profile['syncKey'],
            auth=auth, media=self.pm.profile['syncMedia'])
        self.connect(t, SIGNAL("event"), self.onEvent)
        self.label = _("Connecting...")
        self.mw.progress.start(immediate=True, label=self.label)
        self.sentBytes = self.recvBytes = 0
        self._updateLabel()
        self.thread.start()
        while not self.thread.isFinished():
            self.mw.app.processEvents()
            self.thread.wait(100)
        self.mw.progress.finish()

    def _updateLabel(self):
        self.mw.progress.update(label="%s\n%s" % (
            self.label,
            _("%(a)dkB up, %(b)dkB down") % dict(
                a=self.sentBytes/1024,
                b=self.recvBytes/1024)))

    def onEvent(self, evt, *args):
        pu = self.mw.progress.update
        if evt == "badAuth":
            tooltip(
                _("AnkiWeb ID or password was incorrect; please try again."),
                parent=self.mw)
            # blank the key so we prompt user again
            self.pm.profile['syncKey'] = None
            self.pm.save()
        elif evt == "corrupt":
            pass
        elif evt == "newKey":
            self.pm.profile['syncKey'] = args[0]
            self.pm.save()
        elif evt == "offline":
            tooltip(_("Syncing failed; internet offline."))
        elif evt == "sync":
            m = None; t = args[0]
            if t == "login":
                m = _("Syncing...")
            elif t == "upload":
                m = _("Uploading to AnkiWeb...")
            elif t == "download":
                m = _("Downloading from AnkiWeb...")
            elif t == "sanity":
                m = _("Checking...")
            elif t == "findMedia":
                m = _("Syncing Media...")
            elif t == "upgradeRequired":
                showText(_("""\
Please visit AnkiWeb, upgrade your deck, then try again."""))
            if m:
                self.label = m
                self._updateLabel()
        elif evt == "error":
            showText(_("Syncing failed:\n%s")%
                     self._rewriteError(args[0]))
        elif evt == "clockOff":
            self._clockOff()
        elif evt == "noChanges":
            pass
        elif evt == "fullSync":
            self._confirmFullSync()
        elif evt == "send":
            # posted events not guaranteed to arrive in order
            self.sentBytes = max(self.sentBytes, args[0])
            self._updateLabel()
        elif evt == "recv":
            self.recvBytes = max(self.recvBytes, args[0])
            self._updateLabel()

    def _rewriteError(self, err):
        if "Errno 61" in err:
            return _("""\
Couldn't connect to AnkiWeb. Please check your network connection \
and try again.""")
        elif "timed out" in err or "10060" in err:
            return _("""\
The connection to AnkiWeb timed out. Please check your network \
connection and try again.""")
        elif "500" in err:
            return _("""\
AnkiWeb encountered an error. Please try again in a few minutes, and if \
the problem persists, please file a bug report.""")
        elif "501" in err:
            return _("""\
Please upgrade to the latest version of Anki.""")
        # 502 is technically due to the server restarting, but we reuse the
        # error message
        elif "502" in err or "503" in err or "504" in err:
            return _("""\
AnkiWeb is too busy at the moment. Please try again in a few minutes.""")
        elif "409" in err:
            return _("A previous sync failed; please try again in a few minutes.")
        elif "10061" in err:
            return _(
                "Antivirus or firewall software is preventing Anki from connecting to the internet.")
        elif "407" in err:
            return _("Proxy authentication required.")
        return err

    def _getUserPass(self):
        d = QDialog(self.mw)
        d.setWindowTitle("Anki")
        vbox = QVBoxLayout()
        l = QLabel(_("""\
<h1>Account Required</h1>
A free account is required to keep your collection synchronized. Please \
<a href="%s">sign up</a> for an account, then \
enter your details below.""") %
                   "https://ankiweb.net/account/login")
        l.setOpenExternalLinks(True)
        l.setWordWrap(True)
        vbox.addWidget(l)
        vbox.addSpacing(20)
        g = QGridLayout()
        l1 = QLabel(_("AnkiWeb ID:"))
        g.addWidget(l1, 0, 0)
        user = QLineEdit()
        g.addWidget(user, 0, 1)
        l2 = QLabel(_("Password:"))
        g.addWidget(l2, 1, 0)
        passwd = QLineEdit()
        passwd.setEchoMode(QLineEdit.Password)
        g.addWidget(passwd, 1, 1)
        vbox.addLayout(g)
        bb = QDialogButtonBox(QDialogButtonBox.Ok|QDialogButtonBox.Cancel)
        bb.button(QDialogButtonBox.Ok).setAutoDefault(True)
        self.connect(bb, SIGNAL("accepted()"), d.accept)
        self.connect(bb, SIGNAL("rejected()"), d.reject)
        vbox.addWidget(bb)
        d.setLayout(vbox)
        d.show()
        d.exec_()
        u = user.text()
        p = passwd.text()
        if not u or not p:
            return
        return (u, p)

    def _confirmFullSync(self):
        diag = askUserDialog(_("""\
Your decks here and on AnkiWeb differ in such a way that they can't \
be merged together, so it's necessary to overwrite the decks on one \
side with the decks from the other.

Do you want to upload the decks from here, or download the decks \
from AnkiWeb?"""),
                [_("Upload to AnkiWeb"),
                 _("Download from AnkiWeb"),
                 _("Cancel")])
        diag.setDefault(2)
        ret = diag.run()
        if ret == _("Upload to AnkiWeb"):
            self.thread.fullSyncChoice = "upload"
        elif ret == _("Download from AnkiWeb"):
            self.thread.fullSyncChoice = "download"
        else:
            self.thread.fullSyncChoice = "cancel"

    def _clockOff(self):
        showWarning(_("""\
Syncing requires the clock on your computer to be set correctly. Please \
fix the clock and try again."""))

    def badUserPass(self):
        aqt.preferences.Preferences(self, self.pm.profile).dialog.tabWidget.\
                                         setCurrentIndex(1)

# Sync thread
######################################################################

class SyncThread(QThread):

    def __init__(self, path, hkey, auth=None, media=True):
        QThread.__init__(self)
        self.path = path
        self.hkey = hkey
        self.auth = auth
        self.media = media

    def run(self):
        try:
            self.col = Collection(self.path)
        except:
            self.fireEvent("corrupt")
            return
        self.server = RemoteServer(self.hkey)
        self.client = Syncer(self.col, self.server)
        self.sentTotal = 0
        self.recvTotal = 0
        # throttle updates; qt doesn't handle lots of posted events well
        self.byteUpdate = time.time()
        def syncEvent(type):
            self.fireEvent("sync", type)
        def canPost():
            if (time.time() - self.byteUpdate) > 0.1:
                self.byteUpdate = time.time()
                return True
        def sendEvent(bytes):
            self.sentTotal += bytes
            if canPost():
                self.fireEvent("send", self.sentTotal)
        def recvEvent(bytes):
            self.recvTotal += bytes
            if canPost():
                self.fireEvent("recv", self.recvTotal)
        addHook("sync", syncEvent)
        addHook("httpSend", sendEvent)
        addHook("httpRecv", recvEvent)
        # run sync and catch any errors
        try:
            self._sync()
        except:
            err = traceback.format_exc()
            if not isinstance(err, unicode):
                err = unicode(err, "utf8", "replace")
            self.fireEvent("error", err)
        finally:
            # don't bump mod time unless we explicitly save
            self.col.close(save=False)
            remHook("sync", syncEvent)
            remHook("httpSend", sendEvent)
            remHook("httpRecv", recvEvent)

    def _sync(self):
        if self.auth:
            # need to authenticate and obtain host key
            self.hkey = self.server.hostKey(*self.auth)
            if not self.hkey:
                # provided details were invalid
                return self.fireEvent("badAuth")
            else:
                # write new details and tell calling thread to save
                self.fireEvent("newKey", self.hkey)
        # run sync and check state
        try:
            ret = self.client.sync()
        except Exception, e:
            log = traceback.format_exc()
            try:
                err = unicode(e[0], "utf8", "ignore")
            except:
                # number, exception with no args, etc
                err = ""
            if "Unable to find the server" in err:
                self.fireEvent("offline")
            else:
                if not isinstance(log, unicode):
                    err = unicode(log, "utf8", "replace")
                self.fireEvent("error", log)
            return
        if ret == "badAuth":
            return self.fireEvent("badAuth")
        elif ret == "clockOff":
            return self.fireEvent("clockOff")
        # note mediaUSN for later
        self.mediaUsn = self.client.mediaUsn
        # full sync?
        if ret == "fullSync":
            return self._fullSync()
        # save and note success state
        if ret == "noChanges":
            self.fireEvent("noChanges")
        else:
            self.fireEvent("success")
        # then move on to media sync
        self._syncMedia()

    def _fullSync(self):
        # if the local deck is empty, assume user is trying to download
        if self.col.isEmpty():
            f = "download"
        else:
            # tell the calling thread we need a decision on sync direction, and
            # wait for a reply
            self.fullSyncChoice = False
            self.fireEvent("fullSync")
            while not self.fullSyncChoice:
                time.sleep(0.1)
            f = self.fullSyncChoice
        if f == "cancel":
            return
        self.client = FullSyncer(self.col, self.hkey, self.server.con)
        if f == "upload":
            self.client.upload()
        else:
            self.client.download()
        # reopen db and move on to media sync
        self.col.reopen()
        self._syncMedia()

    def _syncMedia(self):
        if not self.media:
            return
        self.server = RemoteMediaServer(self.hkey, self.server.con)
        self.client = MediaSyncer(self.col, self.server)
        ret = self.client.sync(self.mediaUsn)
        if ret == "noChanges":
            self.fireEvent("noMediaChanges")
        else:
            self.fireEvent("mediaSuccess")

    def fireEvent(self, *args):
        self.emit(SIGNAL("event"), *args)


# Monkey-patch httplib & httplib2 so we can get progress info
######################################################################

CHUNK_SIZE = 65536
import httplib, httplib2, socket, errno
from cStringIO import StringIO
from anki.hooks import runHook

# sending in httplib
def _incrementalSend(self, data):
    """Send `data' to the server."""
    if self.sock is None:
        if self.auto_open:
            self.connect()
        else:
            raise httplib.NotConnected()
    # if it's not a file object, make it one
    if not hasattr(data, 'read'):
        data = StringIO(data)
    while 1:
        block = data.read(CHUNK_SIZE)
        if not block:
            break
        self.sock.sendall(block)
        runHook("httpSend", len(block))

httplib.HTTPConnection.send = _incrementalSend

# receiving in httplib2
def _conn_request(self, conn, request_uri, method, body, headers):
    for i in range(2):
        try:
            if conn.sock is None:
              conn.connect()
            conn.request(method, request_uri, body, headers)
        except socket.timeout:
            raise
        except socket.gaierror:
            conn.close()
            raise httplib2.ServerNotFoundError(
                "Unable to find the server at %s" % conn.host)
        except httplib2.ssl_SSLError:
            conn.close()
            raise
        except socket.error, e:
            err = 0
            if hasattr(e, 'args'):
                err = getattr(e, 'args')[0]
            else:
                err = e.errno
            if err == errno.ECONNREFUSED: # Connection refused
                raise
        except httplib.HTTPException:
            # Just because the server closed the connection doesn't apparently mean
            # that the server didn't send a response.
            if conn.sock is None:
                if i == 0:
                    conn.close()
                    conn.connect()
                    continue
                else:
                    conn.close()
                    raise
            if i == 0:
                conn.close()
                conn.connect()
                continue
            pass
        try:
            response = conn.getresponse()
        except (socket.error, httplib.HTTPException):
            if i == 0:
                conn.close()
                conn.connect()
                continue
            else:
                raise
        else:
            content = ""
            if method == "HEAD":
                response.close()
            else:
                buf = StringIO()
                while 1:
                    data = response.read(CHUNK_SIZE)
                    if not data:
                        break
                    buf.write(data)
                    runHook("httpRecv", len(data))
                content = buf.getvalue()
            response = httplib2.Response(response)
            if method != "HEAD":
                content = httplib2._decompressContent(response, content)
        break
    return (response, content)

httplib2.Http._conn_request = _conn_request

########NEW FILE########
__FILENAME__ = tagedit
# Copyright: Damien Elmes <anki@ichi2.net>
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

from aqt.qt import *
import re, sys

class TagEdit(QLineEdit):

    # 0 = tags, 1 = decks
    def __init__(self, parent, type=0):
        QLineEdit.__init__(self, parent)
        self.col = None
        self.model = QStringListModel()
        self.type = type
        if type == 0:
            self.completer = TagCompleter(self.model, parent, self)
        else:
            self.completer = QCompleter(self.model, parent)
        self.completer.setCompletionMode(QCompleter.PopupCompletion)
        self.completer.setCaseSensitivity(Qt.CaseInsensitive)
        self.setCompleter(self.completer)

    def setCol(self, col):
        "Set the current col, updating list of available tags."
        self.col = col
        if self.type == 0:
            l = sorted(self.col.tags.all())
        else:
            l = sorted(self.col.decks.allNames())
        self.model.setStringList(l)

    def focusInEvent(self, evt):
        QLineEdit.focusInEvent(self, evt)
        self.showCompleter()

    def keyPressEvent(self, evt):
        QLineEdit.keyPressEvent(self, evt)
        if not evt.text():
            # if it's a modifier, don't show
            return
        if evt.key() not in (
            Qt.Key_Enter, Qt.Key_Return, Qt.Key_Escape, Qt.Key_Space,
            Qt.Key_Tab, Qt.Key_Backspace, Qt.Key_Delete):
            self.showCompleter()

    def showCompleter(self):
        self.completer.setCompletionPrefix(self.text())
        self.completer.complete()

    def focusOutEvent(self, evt):
        QLineEdit.focusOutEvent(self, evt)
        self.emit(SIGNAL("lostFocus"))
        self.completer.popup().hide()

    def hideCompleter(self):
        self.completer.popup().hide()

class TagCompleter(QCompleter):

    def __init__(self, model, parent, edit, *args):
        QCompleter.__init__(self, model, parent)
        self.tags = []
        self.edit = edit
        self.cursor = None

    def splitPath(self, str):
        str = unicode(str).strip()
        str = re.sub("  +", " ", str)
        self.tags = self.edit.col.tags.split(str)
        self.tags.append(u"")
        p = self.edit.cursorPosition()
        self.cursor = str.count(" ", 0, p)
        return [self.tags[self.cursor]]

    def pathFromIndex(self, idx):
        if self.cursor is None:
            return self.edit.text()
        ret = QCompleter.pathFromIndex(self, idx)
        self.tags[self.cursor] = unicode(ret)
        try:
            self.tags.remove(u"")
        except ValueError:
            pass
        return " ".join(self.tags)

########NEW FILE########
__FILENAME__ = taglimit
# Copyright: Damien Elmes <anki@ichi2.net>
# License: GNU GPL, version 3 or later; http://www.gnu.org/copyleft/gpl.html

import aqt
from aqt.qt import *
from aqt.utils import saveGeom, restoreGeom

class TagLimit(QDialog):

    def __init__(self, mw, parent):
        QDialog.__init__(self, parent, Qt.Window)
        self.mw = mw
        self.parent = parent
        self.deck = self.parent.deck
        self.dialog = aqt.forms.taglimit.Ui_Dialog()
        self.dialog.setupUi(self)
        self.rebuildTagList()
        restoreGeom(self, "tagLimit")
        self.exec_()

    def rebuildTagList(self):
        usertags = self.mw.col.tags.all()
        yes = self.deck.get("activeTags", [])
        no = self.deck.get("inactiveTags", [])
        yesHash = {}
        noHash = {}
        for y in yes:
            yesHash[y] = True
        for n in no:
            noHash[n] = True
        groupedTags = []
        usertags.sort()
        icon = QIcon(":/icons/Anki_Fact.png")
        groupedTags.append([icon, usertags])
        self.tags = []
        for (icon, tags) in groupedTags:
            for t in tags:
                self.tags.append(t)
                item = QListWidgetItem(icon, t.replace("_", " "))
                self.dialog.activeList.addItem(item)
                if t in yesHash:
                    mode = QItemSelectionModel.Select
                    self.dialog.activeCheck.setChecked(True)
                else:
                    mode = QItemSelectionModel.Deselect
                idx = self.dialog.activeList.indexFromItem(item)
                self.dialog.activeList.selectionModel().select(idx, mode)
                # inactive
                item = QListWidgetItem(icon, t.replace("_", " "))
                self.dialog.inactiveList.addItem(item)
                if t in noHash:
                    mode = QItemSelectionModel.Select
                else:
                    mode = QItemSelectionModel.Deselect
                idx = self.dialog.inactiveList.indexFromItem(item)
                self.dialog.inactiveList.selectionModel().select(idx, mode)

    def reject(self):
        self.tags = ""
        QDialog.reject(self)

    def accept(self):
        self.hide()
        n = 0
        # gather yes/no tags
        yes = []
        no = []
        for c in range(self.dialog.activeList.count()):
            # active
            if self.dialog.activeCheck.isChecked():
                item = self.dialog.activeList.item(c)
                idx = self.dialog.activeList.indexFromItem(item)
                if self.dialog.activeList.selectionModel().isSelected(idx):
                    yes.append(self.tags[c])
            # inactive
            item = self.dialog.inactiveList.item(c)
            idx = self.dialog.inactiveList.indexFromItem(item)
            if self.dialog.inactiveList.selectionModel().isSelected(idx):
                no.append(self.tags[c])
        # save in the deck for future invocations
        self.deck['activeTags'] = yes
        self.deck['inactiveTags'] = no
        self.mw.col.decks.save(self.deck)
        # build query string
        self.tags = ""
        if yes:
            arr = []
            for req in yes:
                arr.append("tag:'%s'" % req)
            self.tags += "(" + " or ".join(arr) + ")"
        if no:
            arr = []
            for req in no:
                arr.append("-tag:'%s'" % req)
            self.tags += " " + " ".join(arr)
        saveGeom(self, "tagLimit")
        QDialog.accept(self)

########NEW FILE########
__FILENAME__ = toolbar
# Copyright: Damien Elmes <anki@ichi2.net>
# -*- coding: utf-8 -*-
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

from aqt.qt import *

class Toolbar(object):

    def __init__(self, mw, web):
        self.mw = mw
        self.web = web
        self.web.page().mainFrame().setScrollBarPolicy(
            Qt.Vertical, Qt.ScrollBarAlwaysOff)
        self.web.setLinkHandler(self._linkHandler)
        self.link_handlers = {
            "decks": self._deckLinkHandler,
            "study": self._studyLinkHandler,
            "add": self._addLinkHandler,
            "browse": self._browseLinkHandler,
            "stats": self._studyLinkHandler,
            "sync": self._syncLinkHandler,
        }

    def draw(self):
        self.web.stdHtml(self._body % (
            # may want a context menu here in the future
            '&nbsp;'*20,
            self._centerLinks(),
            self._rightIcons()),
                         self._css)

    # Available links
    ######################################################################

    def _rightIconsList(self):
        return [
            ["stats", "qrc:/icons/view-statistics.png",
             _("Show statistics. Shortcut key: %s") % "Shift+S"],
            ["sync", "qrc:/icons/view-refresh.png",
             _("Synchronize with AnkiWeb. Shortcut key: %s") % "Y"],
        ]

    def _centerLinks(self):
        links = [
            ["decks", _("Decks"), _("Shortcut key: %s") % "D"],
            ["add", _("Add"), _("Shortcut key: %s") % "A"],
            ["browse", _("Browse"), _("Shortcut key: %s") % "B"],
        ]
        return self._linkHTML(links)

    def _linkHTML(self, links):
        buf = ""
        for ln, name, title in links:
            buf += '<a class=hitem title="%s" href="%s">%s</a>' % (
                title, ln, name)
            buf += "&nbsp;"*3
        return buf

    def _rightIcons(self):
        buf = ""
        for ln, icon, title in self._rightIconsList():
            buf += '<a class=hitem title="%s" href="%s"><img width="16px" height="16px" src="%s"></a>' % (
                title, ln, icon)
        return buf

    # Link handling
    ######################################################################

    def _linkHandler(self, link):
        # first set focus back to main window, or we're left with an ugly
        # focus ring around the clicked item
        self.mw.web.setFocus()
        if link in self.link_handlers:
          self.link_handlers[link]()

    def _deckLinkHandler(self):
      self.mw.moveToState("deckBrowser")

    def _studyLinkHandler(self):
      # if overview already shown, switch to review
      if self.mw.state == "overview":
          self.mw.col.startTimebox()
          self.mw.moveToState("review")
      else:
          self.mw.onOverview()

    def _addLinkHandler(self):
      self.mw.onAddCard()

    def _browseLinkHandler(self):
      self.mw.onBrowse()

    def _statsLinkHandler(self):
      self.mw.onStats()

    def _syncLinkHandler(self):
      self.mw.onSync()

    # HTML & CSS
    ######################################################################

    _body = """
<table id=header width=100%%>
<tr>
<td width=16%% align=left>%s</td>
<td align=center>%s</td>
<td width=15%% align=right>%s</td>
</tr></table>
"""

    _css = """
#header {
margin:0;
margin-top: 4px;
font-weight: bold;
}

body {
background: -webkit-gradient(linear, left top, left bottom,
  from(#ddd), to(#fff));
margin: 0; padding: 0;
-webkit-user-select: none;
border-bottom: 1px solid #aaa;
}

* { -webkit-user-drag: none; }

.hitem {
padding-right: 6px;
text-decoration: none;
color: #000;
}
.hitem:hover {
text-decoration: underline;
}
"""

class BottomBar(Toolbar):

    _css = Toolbar._css + """
#header {
background: -webkit-gradient(linear, left top, left bottom,
from(#fff), to(#ddd));
border-bottom: 0;
border-top: 1px solid #aaa;
margin-bottom: 6px;
margin-top: 0;
}
"""

    _centerBody = """
<center><table width=100%% height=100%% id=header><tr><td align=center>
%s</td></tr></table></center>
"""

    def draw(self, buf):
        self.web.show()
        self.web.stdHtml(
            self._centerBody % buf,
            self._css)

########NEW FILE########
__FILENAME__ = update
# Copyright: Damien Elmes <anki@ichi2.net>
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

from aqt.qt import *
import urllib, urllib2, os, sys, time, httplib
import anki, anki.utils, anki.lang, anki.stats
import aqt
import platform
from aqt.utils import openLink
from anki.utils import json, isWin, isMac
from aqt.utils import showText

class LatestVersionFinder(QThread):

    def __init__(self, main):
        QThread.__init__(self)
        self.main = main
        self.config = main.pm.meta

    def _data(self):
        # we may get an interrupted system call, so try this in a loop
        n = 0
        theos = "unknown"
        while n < 100:
            n += 1
            try:
                system = platform.system()
                if isMac:
                    theos = "mac:%s" % (platform.mac_ver()[0])
                elif isWin:
                    theos = "win:%s" % (platform.win32_ver()[0])
                elif system == "Linux":
                    dist = platform.dist()
                    theos = "lin:%s:%s" % (dist[0], dist[1])
                else:
                    theos = system
                break
            except:
                continue
        d = {"ver": aqt.appVersion,
             "os": theos,
             "id": self.config['id'],
             "lm": self.config['lastMsg'],
             "crt": self.config['created']}
        return d

    def run(self):
        if not self.config['updates']:
            return
        d = self._data()
        d['proto'] = 1
        d = urllib.urlencode(d)
        try:
            f = urllib2.urlopen(aqt.appUpdate, d)
            resp = f.read()
            if not resp:
                return
            resp = json.loads(resp)
        except:
            # behind proxy, corrupt message, etc
            return
        if resp['msg']:
            self.emit(SIGNAL("newMsg"), resp)
        if resp['ver']:
            self.emit(SIGNAL("newVerAvail"), resp['ver'])
        diff = resp['time'] - time.time()
        if abs(diff) > 300:
            self.emit(SIGNAL("clockIsOff"))

def askAndUpdate(mw, ver):
    baseStr = (
        _('''<h1>Anki Updated</h1>Anki %s has been released.<br><br>''') %
        ver)
    msg = QMessageBox(mw)
    msg.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
    msg.setIcon(QMessageBox.Information)
    msg.setText(baseStr + _("Would you like to download it now?"))
    button = QPushButton(_("Ignore this update"))
    msg.addButton(button, QMessageBox.RejectRole)
    msg.setDefaultButton(QMessageBox.Yes)
    ret = msg.exec_()
    if msg.clickedButton() == button:
        # ignore this update
        mw.pm.meta['suppressUpdate'] = ver
    elif ret == QMessageBox.Yes:
        openLink(aqt.appWebsite)

def showMessages(mw, data):
    showText(data['msg'], parent=mw, type="html")
    mw.pm.meta['lastMsg'] = data['msgId']

########NEW FILE########
__FILENAME__ = upgrade
# Copyright: Damien Elmes <anki@ichi2.net>
# -*- coding: utf-8 -*-
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

import os, cPickle, ctypes, shutil
from aqt.qt import *
from anki.utils import isMac, isWin
from anki import Collection
from anki.importing import Anki1Importer
from anki.db import DB
from aqt.utils import showWarning
import aqt

class Upgrader(object):

    def __init__(self, mw):
        self.mw = mw

    def maybeUpgrade(self):
        p = self._oldConfigPath()
        # does an old config file exist?
        if not os.path.exists(p):
            return
        # load old settings and copy over
        try:
            self._loadConf(p)
        except:
            showWarning(_("""\
Anki wasn't able to load your old config file. Please use File>Import \
to import your decks from previous Anki versions."""))
            return
        if not self._copySettings():
            return
        # and show the wizard
        self._showWizard()

    # Settings
    ######################################################################

    def _oldConfigPath(self):
        if isWin:
            os.environ['HOME'] = os.environ['APPDATA']
            p = "~/.anki/config.db"
        elif isMac:
            p = "~/Library/Application Support/Anki/config.db"
        else:
            p = "~/.anki/config.db"
        return os.path.expanduser(p)

    def _loadConf(self, path):
        self.conf = cPickle.load(open(path))

    def _copySettings(self):
        p = self.mw.pm.profile
        for k in (
            "recentColours", "stripHTML", "editFontFamily", "editFontSize",
            "editLineSize", "deleteMedia", "preserveKeyboard", "numBackups",
            "proxyHost", "proxyPass", "proxyPort", "proxyUser"):
            try:
                p[k] = self.conf[k]
            except:
                showWarning(_("""\
Anki 2.0 only supports automatic upgrading from Anki 1.2. To load old \
decks, please open them in Anki 1.2 to upgrade them, and then import them \
into Anki 2.0."""))
                return
        return True

    # Wizard
    ######################################################################

    def _showWizard(self):
        if not self.conf['recentDeckPaths']:
            # if there are no decks to upgrade, don't show wizard
            return
        class Wizard(QWizard):
            def reject(self):
                pass
        self.wizard = w = Wizard()
        w.addPage(self._welcomePage())
        w.addPage(self._decksPage())
        w.addPage(self._mediaPage())
        w.addPage(self._readyPage())
        w.addPage(self._upgradePage())
        w.addPage(self._finishedPage())
        w.setWindowTitle(_("Upgrade Wizard"))
        w.setWizardStyle(QWizard.ModernStyle)
        w.setOptions(QWizard.NoCancelButton)
        w.exec_()

    def _labelPage(self, title, txt):
        p = QWizardPage()
        p.setTitle(title)
        l = QLabel(txt)
        l.setTextFormat(Qt.RichText)
        l.setTextInteractionFlags(Qt.TextSelectableByMouse)
        l.setWordWrap(True)
        v = QVBoxLayout()
        v.addWidget(l)
        p.setLayout(v)
        return p

    def _welcomePage(self):
        return self._labelPage(_("Welcome"), _("""\
This wizard will guide you through the Anki 2.0 upgrade process.
For a smooth upgrade, please read the following pages carefully.
"""))

    def _decksPage(self):
        return self._labelPage(_("Your Decks"), _("""\
Anki 2 stores your decks in a new format. This wizard will automatically
convert your decks to that format. Your decks will be backed up before
the upgrade, so if you need to revert to the previous version of Anki, your
decks will still be usable."""))

    def _mediaPage(self):
        return self._labelPage(_("Sounds & Images"), _("""\
When your decks are upgraded, Anki will attempt to copy any sounds and images
from the old decks. If you were using a custom DropBox folder or custom media
folder, the upgrade process may not be able to locate your media. Later on, a
report of the upgrade will be presented to you. If you notice media was not
copied when it should have been, please see the upgrade guide for more
instructions.
<p>
AnkiWeb now supports media syncing directly. No special setup is required, and
media will be synchronized along with your cards when you sync to AnkiWeb."""))

    def _readyPage(self):
        class ReadyPage(QWizardPage):
            def initializePage(self):
                self.setTitle(_("Ready to Upgrade"))
                self.setCommitPage(True)
                l = QLabel(_("""\
When you're ready to upgrade, click the commit button to continue. The upgrade
guide will open in your browser while the upgrade proceeds. Please read it
carefully, as a lot has changed since the previous Anki version."""))
                l.setTextFormat(Qt.RichText)
                l.setTextInteractionFlags(Qt.TextSelectableByMouse)
                l.setWordWrap(True)
                v = QVBoxLayout()
                v.addWidget(l)
                self.setLayout(v)
        return ReadyPage()

    def _upgradePage(self):
        decks = self.conf['recentDeckPaths']
        colpath = self.mw.pm.collectionPath()
        upgrader = self
        class UpgradePage(QWizardPage):
            def isComplete(self):
                return False
            def initializePage(self):
                # can't use openLink; gui not ready for tooltips
                QDesktopServices.openUrl(QUrl(aqt.appChanges))
                self.setCommitPage(True)
                self.setTitle(_("Upgrading"))
                self.label = l = QLabel()
                l.setTextInteractionFlags(Qt.TextSelectableByMouse)
                l.setWordWrap(True)
                v = QVBoxLayout()
                v.addWidget(l)
                prog = QProgressBar()
                prog.setMaximum(0)
                v.addWidget(prog)
                l2 = QLabel(_("Please be patient; this can take a while."))
                l2.setTextInteractionFlags(Qt.TextSelectableByMouse)
                l2.setWordWrap(True)
                v.addWidget(l2)
                self.setLayout(v)
                # run the upgrade in a different thread
                self.thread = UpgradeThread(decks, colpath, upgrader.conf)
                self.thread.start()
                # and periodically update the GUI
                self.timer = QTimer(self)
                self.timer.connect(self.timer, SIGNAL("timeout()"), self.onTimer)
                self.timer.start(1000)
                self.onTimer()
            def onTimer(self):
                prog = self.thread.progress()
                if not prog:
                    self.timer.stop()
                    upgrader.log = self.thread.log
                    upgrader.wizard.next()
                self.label.setText(prog)
        return UpgradePage()

    def _finishedPage(self):
        upgrader = self
        class FinishedPage(QWizardPage):
            def initializePage(self):
                buf = ""
                for file in upgrader.log:
                    buf += "<b>%s</b>" % file[0]
                    buf += "<ul><li>" + "<li>".join(file[1]) + "</ul><p>"
                self.setTitle(_("Upgrade Complete"))
                l = QLabel(_("""\
The upgrade has finished, and you're ready to start using Anki 2.0.
<p>
Below is a log of the update:
<p>
%s<br><br>""") % buf)
                l.setTextFormat(Qt.RichText)
                l.setTextInteractionFlags(Qt.TextSelectableByMouse)
                l.setWordWrap(True)
                l.setMaximumWidth(400)
                a = QScrollArea()
                a.setWidget(l)
                v = QVBoxLayout()
                v.addWidget(a)
                self.setLayout(v)
        return FinishedPage()

class UpgradeThread(QThread):

    def __init__(self, paths, colpath, oldprefs):
        QThread.__init__(self)
        self.paths = paths
        self.max = len(paths)
        self.current = 1
        self.finished = False
        self.colpath = colpath
        self.oldprefs = oldprefs
        self.name = ""
        self.log = []

    def run(self):
        # open profile deck
        self.col = Collection(self.colpath)
        # loop through paths
        while True:
            path = self.paths.pop()
            self.name = os.path.basename(path)
            self.upgrade(path)
            # abort if finished
            if not self.paths:
                break
            self.current += 1
        self.col.close()
        self.finished = True

    def progress(self):
        if self.finished:
            return
        return _("Upgrading deck %(a)s of %(b)s...\n%(c)s") % \
            dict(a=self.current, b=self.max, c=self.name)

    def upgrade(self, path):
        log = self._upgrade(path)
        self.log.append((self.name, log))

    def _upgrade(self, path):
        if not os.path.exists(path):
            return [_("File was missing.")]
        imp = Anki1Importer(self.col, path)
        # try to copy over dropbox media first
        try:
            self.maybeCopyFromCustomFolder(path)
        except Exception, e:
            imp.log.append(unicode(e))
        # then run the import
        try:
            imp.run()
        except Exception, e:
            if unicode(e) == "invalidFile":
                # already logged
                pass
            else:
                imp.log.append(unicode(e))
        self.col.save()
        return imp.log

    def maybeCopyFromCustomFolder(self, path):
        folder = os.path.basename(path).replace(".anki", ".media")
        loc = self.oldprefs.get("mediaLocation")
        if not loc:
            # no prefix; user had media next to deck
            return
        elif loc == "dropbox":
            # dropbox no longer exports the folder location; try default
            if isWin:
                dll = ctypes.windll.shell32
                buf = ctypes.create_string_buffer(300)
                dll.SHGetSpecialFolderPathA(None, buf, 0x0005, False)
                loc = os.path.join(buf.value, 'Dropbox')
            else:
                loc = os.path.expanduser("~/Dropbox")
            loc = os.path.join(loc, "Public", "Anki")
        # no media folder in custom location?
        mfolder = os.path.join(loc, folder)
        if not os.path.exists(mfolder):
            return
        # folder exists; copy data next to the deck. leave a copy in the
        # custom location so users can revert easily.
        mdir = self.col.media.dir()
        for f in os.listdir(mfolder):
            src = os.path.join(mfolder, f)
            dst = os.path.join(mdir, f)
            if not os.path.exists(dst):
                shutil.copyfile(src, dst)

########NEW FILE########
__FILENAME__ = utils
# Copyright: Damien Elmes <anki@ichi2.net>
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

from aqt.qt import *
import re, os, sys, urllib, time, subprocess
import aqt
from anki.sound import playFromText, stripSounds
from anki.utils import call, isWin, isMac

def openHelp(section):
    link = aqt.appHelpSite
    if section:
        link += "#%s" % section
    openLink(link)

def openLink(link):
    tooltip(_("Loading..."), period=1000)
    QDesktopServices.openUrl(QUrl(link))

def showWarning(text, parent=None, help=""):
    "Show a small warning with an OK button."
    return showInfo(text, parent, help, "warning")

def showCritical(text, parent=None, help=""):
    "Show a small critical error with an OK button."
    return showInfo(text, parent, help, "critical")

def showInfo(text, parent=False, help="", type="info"):
    "Show a small info window with an OK button."
    if parent is False:
        parent = aqt.mw.app.activeWindow() or aqt.mw
    if type == "warning":
        icon = QMessageBox.Warning
    elif type == "critical":
        icon = QMessageBox.Critical
    else:
        icon = QMessageBox.Information
    mb = QMessageBox(parent)
    mb.setText(text)
    mb.setIcon(icon)
    mb.setWindowModality(Qt.WindowModal)
    b = mb.addButton(QMessageBox.Ok)
    b.setDefault(True)
    if help:
        b = mb.addButton(QMessageBox.Help)
        b.connect(b, SIGNAL("clicked()"), lambda: openHelp(help))
        b.setAutoDefault(False)
    return mb.exec_()

def showText(txt, parent=None, type="text", run=True):
    if not parent:
        parent = aqt.mw.app.activeWindow() or aqt.mw
    diag = QDialog(parent)
    diag.setWindowTitle("Anki")
    layout = QVBoxLayout(diag)
    diag.setLayout(layout)
    text = QTextEdit()
    text.setReadOnly(True)
    if type == "text":
        text.setPlainText(txt)
    else:
        text.setHtml(txt)
    layout.addWidget(text)
    box = QDialogButtonBox(QDialogButtonBox.Close)
    layout.addWidget(box)
    diag.connect(box, SIGNAL("rejected()"), diag, SLOT("reject()"))
    diag.setMinimumHeight(400)
    diag.setMinimumWidth(500)
    if run:
        diag.exec_()
    else:
        return diag, box

def askUser(text, parent=None, help="", defaultno=False, msgfunc=None):
    "Show a yes/no question. Return true if yes."
    if not parent:
        parent = aqt.mw.app.activeWindow()
    if not msgfunc:
        msgfunc = QMessageBox.question
    sb = QMessageBox.Yes | QMessageBox.No
    if help:
        sb |= QMessageBox.Help
    while 1:
        if defaultno:
            default = QMessageBox.No
        else:
            default = QMessageBox.Yes
        r = msgfunc(parent, "Anki", text, sb,
                                 default)
        if r == QMessageBox.Help:

            openHelp(help)
        else:
            break
    return r == QMessageBox.Yes

class ButtonedDialog(QMessageBox):

    def __init__(self, text, buttons, parent=None, help=""):
        QDialog.__init__(self, parent)
        self.buttons = []
        self.setWindowTitle("Anki")
        self.help = help
        self.setIcon(QMessageBox.Warning)
        self.setText(text)
        # v = QVBoxLayout()
        # v.addWidget(QLabel(text))
        # box = QDialogButtonBox()
        # v.addWidget(box)
        for b in buttons:
            self.buttons.append(
                self.addButton(b, QMessageBox.AcceptRole))
        if help:
            self.addButton(_("Help"), QMessageBox.HelpRole)
            buttons.append(_("Help"))
        #self.setLayout(v)

    def run(self):
        self.exec_()
        but = self.clickedButton().text()
        if but == "Help":
            # FIXME stop dialog closing?
            openHelp(self.help)
        return self.clickedButton().text()

    def setDefault(self, idx):
        self.setDefaultButton(self.buttons[idx])

def askUserDialog(text, buttons, parent=None, help=""):
    if not parent:
        parent = aqt.mw
    diag = ButtonedDialog(text, buttons, parent, help)
    return diag

class GetTextDialog(QDialog):

    def __init__(self, parent, question, help=None, edit=None, default=u"",
                 title="Anki"):
        QDialog.__init__(self, parent)
        self.setWindowTitle(title)
        self.question = question
        self.help = help
        self.qlabel = QLabel(question)
        self.setMinimumWidth(400)
        v = QVBoxLayout()
        v.addWidget(self.qlabel)
        if not edit:
            edit = QLineEdit()
        self.l = edit
        if default:
            self.l.setText(default)
            self.l.selectAll()
        v.addWidget(self.l)
        buts = QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        if help:
            buts |= QDialogButtonBox.Help
        b = QDialogButtonBox(buts)
        v.addWidget(b)
        self.setLayout(v)
        self.connect(b.button(QDialogButtonBox.Ok),
                     SIGNAL("clicked()"), self.accept)
        self.connect(b.button(QDialogButtonBox.Cancel),
                     SIGNAL("clicked()"), self.reject)
        if help:
            self.connect(b.button(QDialogButtonBox.Help),
                         SIGNAL("clicked()"), self.helpRequested)

    def accept(self):
        return QDialog.accept(self)

    def reject(self):
        return QDialog.reject(self)

    def helpRequested(self):
        openHelp(self.help)

def getText(prompt, parent=None, help=None, edit=None, default=u"", title="Anki"):
    if not parent:
        parent = aqt.mw.app.activeWindow() or aqt.mw
    d = GetTextDialog(parent, prompt, help=help, edit=edit,
                      default=default, title=title)
    d.setWindowModality(Qt.WindowModal)
    ret = d.exec_()
    return (unicode(d.l.text()), ret)

def getOnlyText(*args, **kwargs):
    (s, r) = getText(*args, **kwargs)
    if r:
        return s
    else:
        return u""

# fixme: these utilities could be combined into a single base class
def chooseList(prompt, choices, startrow=0, parent=None):
    if not parent:
        parent = aqt.mw.app.activeWindow()
    d = QDialog(parent)
    d.setWindowModality(Qt.WindowModal)
    l = QVBoxLayout()
    d.setLayout(l)
    t = QLabel(prompt)
    l.addWidget(t)
    c = QListWidget()
    c.addItems(choices)
    c.setCurrentRow(startrow)
    l.addWidget(c)
    bb = QDialogButtonBox(QDialogButtonBox.Ok)
    bb.connect(bb, SIGNAL("accepted()"), d, SLOT("accept()"))
    l.addWidget(bb)
    d.exec_()
    return c.currentRow()

def getTag(parent, deck, question, tags="user", **kwargs):
    from aqt.tagedit import TagEdit
    te = TagEdit(parent)
    te.setCol(deck)
    ret = getText(question, parent, edit=te, **kwargs)
    te.hideCompleter()
    return ret

# File handling
######################################################################

def getFile(parent, title, cb, filter="*.*", dir=None, key=None):
    "Ask the user for a file."
    assert not dir or not key
    if not dir:
        dirkey = key+"Directory"
        dir = aqt.mw.pm.profile.get(dirkey, "")
    else:
        dirkey = None
    d = QFileDialog(parent)
    # fix #233 crash
    if isMac:
        d.setOptions(QFileDialog.DontUseNativeDialog)
    d.setFileMode(QFileDialog.ExistingFile)
    d.setDirectory(dir)
    d.setWindowTitle(title)
    d.setNameFilter(filter)
    ret = []
    def accept():
        # work around an osx crash
        aqt.mw.app.processEvents()
        file = unicode(list(d.selectedFiles())[0])
        if dirkey:
            dir = os.path.dirname(file)
            aqt.mw.pm.profile[dirkey] = dir
        if cb:
            cb(file)
        ret.append(file)
    d.connect(d, SIGNAL("accepted()"), accept)
    d.exec_()
    return ret and ret[0]

def getSaveFile(parent, title, dir, key, ext):
    "Ask the user for a file to save. Use DIR as config variable."
    dirkey = dir+"Directory"
    file = unicode(QFileDialog.getSaveFileName(
        parent, title, aqt.mw.pm.base, key,
        options=QFileDialog.DontConfirmOverwrite))
    if file:
        # add extension
        if not file.lower().endswith(ext):
            file += ext
        # save new default
        dir = os.path.dirname(file)
        aqt.mw.pm.profile[dirkey] = dir
        # check if it exists
        if os.path.exists(file):
            if not askUser(
                _("This file exists. Are you sure you want to overwrite it?"),
                parent):
                return None
    return file

def saveGeom(widget, key):
    key += "Geom"
    aqt.mw.pm.profile[key] = widget.saveGeometry()

def restoreGeom(widget, key, offset=None):
    key += "Geom"
    if aqt.mw.pm.profile.get(key):
        widget.restoreGeometry(aqt.mw.pm.profile[key])
        if isMac and offset:
            from aqt.main import QtConfig as q
            minor = (q.qt_version & 0x00ff00) >> 8
            if minor > 6:
                # bug in osx toolkit
                s = widget.size()
                widget.resize(s.width(), s.height()+offset*2)

def saveState(widget, key):
    key += "State"
    aqt.mw.pm.profile[key] = widget.saveState()

def restoreState(widget, key):
    key += "State"
    if aqt.mw.pm.profile.get(key):
        widget.restoreState(aqt.mw.pm.profile[key])

def saveSplitter(widget, key):
    key += "Splitter"
    aqt.mw.pm.profile[key] = widget.saveState()

def restoreSplitter(widget, key):
    key += "Splitter"
    if aqt.mw.pm.profile.get(key):
        widget.restoreState(aqt.mw.pm.profile[key])

def saveHeader(widget, key):
    key += "Header"
    aqt.mw.pm.profile[key] = widget.saveState()

def restoreHeader(widget, key):
    key += "Header"
    if aqt.mw.pm.profile.get(key):
        widget.restoreState(aqt.mw.pm.profile[key])

def mungeQA(txt):
    txt = stripSounds(txt)
    # osx webkit doesn't understand font weight 600
    txt = re.sub("font-weight: *600", "font-weight:bold", txt)
    return txt

def applyStyles(widget):
    p = os.path.join(aqt.mw.pm.base, "style.css")
    if os.path.exists(p):
        widget.setStyleSheet(open(p).read())

def getBase(col):
    base = None
    mdir = col.media.dir()
    if isWin:
        prefix = u"file:///"
    else:
        prefix = u"file://"
    base = prefix + unicode(
        urllib.quote(mdir.encode("utf-8")),
        "utf-8") + "/"
    return '<base href="%s">' % base

def openFolder(path):
    if isWin:
        if isinstance(path, unicode):
            path = path.encode(sys.getfilesystemencoding())
        subprocess.Popen(["explorer", path])
    else:
        QDesktopServices.openUrl(QUrl("file://" + path))

def shortcut(key):
    if isMac:
        return re.sub("(?i)ctrl", "Command", key)
    return key

def maybeHideClose(bbox):
    if isMac:
        b = bbox.button(QDialogButtonBox.Close)
        if b:
            bbox.removeButton(b)

# Tooltips
######################################################################

_tooltipTimer = None
_tooltipLabel = None

def tooltip(msg, period=3000, parent=None):
    global _tooltipTimer, _tooltipLabel
    class CustomLabel(QLabel):
        def mousePressEvent(self, evt):
            evt.accept()
            self.hide()
    closeTooltip()
    aw = parent or aqt.mw.app.activeWindow() or aqt.mw
    lab = CustomLabel("""\
<table cellpadding=10>
<tr>
<td><img src=":/icons/help-hint.png"></td>
<td>%s</td>
</tr>
</table>""" % msg, aw)
    lab.setFrameStyle(QFrame.Panel)
    lab.setLineWidth(2)
    lab.setWindowFlags(Qt.ToolTip)
    p = QPalette()
    p.setColor(QPalette.Window, QColor("#feffc4"))
    lab.setPalette(p)
    lab.move(
        aw.mapToGlobal(QPoint(0, -100 + aw.height())))
    lab.show()
    _tooltipTimer = aqt.mw.progress.timer(
        period, closeTooltip, False)
    _tooltipLabel = lab

def closeTooltip():
    global _tooltipLabel, _tooltipTimer
    if _tooltipLabel:
        try:
            _tooltipLabel.deleteLater()
        except:
            # already deleted as parent window closed
            pass
        _tooltipLabel = None
    if _tooltipTimer:
        _tooltipTimer.stop()
        _tooltipTimer = None

########NEW FILE########
__FILENAME__ = webview
# Copyright: Damien Elmes <anki@ichi2.net>
# -*- coding: utf-8 -*-
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

import sys
from aqt.qt import *
from aqt.utils import openLink
from anki.utils import isMac, isWin
import anki.js
QtConfig = pyqtconfig.Configuration()

# Bridge for Qt<->JS
##########################################################################

class Bridge(QObject):
    @pyqtSlot(str, result=str)
    def run(self, str):
        return unicode(self._bridge(unicode(str)))
    @pyqtSlot(str)
    def link(self, str):
        self._linkHandler(unicode(str))
    def setBridge(self, func):
        self._bridge = func
    def setLinkHandler(self, func):
        self._linkHandler = func

# Page for debug messages
##########################################################################

class AnkiWebPage(QWebPage):

    def __init__(self, jsErr):
        QWebPage.__init__(self)
        self._jsErr = jsErr
    def javaScriptConsoleMessage(self, msg, line, srcID):
        self._jsErr(msg, line, srcID)

# Main web view
##########################################################################

class AnkiWebView(QWebView):

    def __init__(self):
        QWebView.__init__(self)
        self.setRenderHints(
            QPainter.TextAntialiasing |
            QPainter.SmoothPixmapTransform |
            QPainter.HighQualityAntialiasing)
        self.setObjectName("mainText")
        self._bridge = Bridge()
        self._page = AnkiWebPage(self._jsErr)
        self._loadFinishedCB = None
        self.setPage(self._page)
        self.page().setLinkDelegationPolicy(QWebPage.DelegateAllLinks)
        self.setLinkHandler()
        self.setKeyHandler()
        self.connect(self, SIGNAL("linkClicked(QUrl)"), self._linkHandler)
        self.connect(self, SIGNAL("loadFinished(bool)"), self._loadFinished)
        self.allowDrops = False
        # reset each time new html is set; used to detect if still in same state
        self.key = None

    def keyPressEvent(self, evt):
        if evt.matches(QKeySequence.Copy):
            self.triggerPageAction(QWebPage.Copy)
            evt.accept()
        # work around a bug with windows qt where shift triggers buttons
        if isWin and evt.modifiers() == Qt.ShiftModifier and not evt.text():
            evt.accept()
            return
        QWebView.keyPressEvent(self, evt)

    def keyReleaseEvent(self, evt):
        if self._keyHandler:
            if self._keyHandler(evt):
                evt.accept()
                return
        QWebView.keyReleaseEvent(self, evt)

    def contextMenuEvent(self, evt):
        # lazy: only run in reviewer
        import aqt
        if aqt.mw.state != "review":
            return
        m = QMenu(self)
        a = m.addAction(_("Copy"))
        a.connect(a, SIGNAL("activated()"),
                  lambda: self.triggerPageAction(QWebPage.Copy))
        m.popup(QCursor.pos())

    def dropEvent(self, evt):
        pass

    def setLinkHandler(self, handler=None):
        if handler:
            self.linkHandler = handler
        else:
            self.linkHandler = self._openLinksExternally
        self._bridge.setLinkHandler(self.linkHandler)

    def setKeyHandler(self, handler=None):
        # handler should return true if event should be swallowed
        self._keyHandler = handler

    def setHtml(self, html, loadCB=None):
        self.key = None
        self._loadFinishedCB = loadCB
        QWebView.setHtml(self, html)

    def stdHtml(self, body, css="", bodyClass="", loadCB=None, js=None, head=""):
        if isMac:
            button = "font-weight: bold; height: 24px;"
        else:
            button = "font-weight: normal;"
        self.setHtml("""
<!doctype html>
<html><head><style>
button {
%s
}
%s</style>
<script>%s</script>
%s

</head>
<body class="%s">%s</body></html>""" % (
    button, css, js or anki.js.jquery+anki.js.browserSel,
    head, bodyClass, body), loadCB)

    def setBridge(self, bridge):
        self._bridge.setBridge(bridge)

    def eval(self, js):
        self.page().mainFrame().evaluateJavaScript(js)

    def _openLinksExternally(self, url):
        openLink(url)

    def _jsErr(self, msg, line, srcID):
        sys.stdout.write(
            (_("JS error on line %(a)d: %(b)s") %
              dict(a=line, b=msg+"\n")).encode("utf8"))

    def _linkHandler(self, url):
        self.linkHandler(url.toString())

    def _loadFinished(self):
        self.page().mainFrame().addToJavaScriptWindowObject("py", self._bridge)
        if self._loadFinishedCB:
            self._loadFinishedCB(self)
            self._loadFinishedCB = None

########NEW FILE########
