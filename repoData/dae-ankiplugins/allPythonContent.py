__FILENAME__ = addToToolbar
# -*- coding: utf-8 -*-
# Copyright: Damien Elmes <anki@ichi2.net>
# License: GNU GPL, version 3 or later; http://www.gnu.org/copyleft/gpl.html

# Add an icon to the toolbar. Adds a separator and 'suspend card' by default.

# version 1: initial release

from PyQt4.QtCore import *
from PyQt4.QtGui import *
from ankiqt import mw

def init():
    mw.mainWin.toolBar.addSeparator()
    mw.mainWin.toolBar.addAction(mw.mainWin.actionSuspendCard)

mw.addHook("init", init)
mw.registerPlugin("Add to Toolbar", 13)

########NEW FILE########
__FILENAME__ = alwaysontop
# -*- coding: utf-8 -*-
# Copyright: Damien Elmes <anki@ichi2.net>
# License: GNU GPL, version 3 or later; http://www.gnu.org/copyleft/gpl.html
#
# This plugin keeps Anki on top of other windows.

from ankiqt import mw
from PyQt4.QtCore import *
from PyQt4.QtGui import *

mw.setWindowFlags(Qt.WindowStaysOnTopHint)
mw.show()

mw.registerPlugin("Always On Top", 9)

########NEW FILE########
__FILENAME__ = buildlatex
# -*- coding: utf-8 -*-
# Copyright: Damien Elmes <anki@ichi2.net>
# License: GNU GPL, version 3 or later; http://www.gnu.org/copyleft/gpl.html
#
# Adds an item to the tools menu to build .png files for any LaTeX in fields.
# This is normally done when you review a card; use this to do them all in
# bulk for distributing to users without LaTeX.
#

from aqt import mw
from aqt.qt import *
from aqt.utils import showInfo

def build():
    mw.progress.start()
    for cid in mw.col.db.list("select id from cards"):
        mw.col.getCard(cid).q()
    mw.progress.finish()
    showInfo("LaTeX generated.")

a = QAction(mw)
a.setText("Build LaTeX")
mw.form.menuTools.addAction(a)
mw.connect(a, SIGNAL("triggered()"), build)

########NEW FILE########
__FILENAME__ = bulkcloze
# -*- coding: utf-8 -*-
# Copyright: Damien Elmes <anki@ichi2.net>
# License: GNU GPL, version 3 or later; http://www.gnu.org/copyleft/gpl.html
#
# Automatically generate cloze deletions for all the cards in a deck. By
# default it generates a cloze from fields 1->2 and 3->4. To change this,
# adjust the FIELDS below
#

from PyQt4.QtCore import *
from PyQt4.QtGui import *
from ankiqt import mw
from ankiqt import ui
from anki.hooks import addHook
import re

# generate 1->2 and 3->4
FIELDS = (1,3)
# example: generate 2->3
#FIELDS = (2,)

def onCloze(browser):
    browser.onFirstCard()
    browser.onFact()
    l = len(browser.model.cards) - 1
    c = 0
    cont = True
    while True:
        mw.app.processEvents()
        for f in FIELDS:
            w = browser.editor.fieldsGrid.itemAtPosition(f-1, 1).widget()
            w2 = browser.editor.fieldsGrid.itemAtPosition(f, 1).widget()
            if w2.toPlainText():
                continue
            w.setFocus()
            if not browser.editor.onCloze():
                cont = False
                break
        if c == l or not cont:
            break
        c += 1
        browser.onNextCard()

# hacked to return status info
def onClozeRepl(self):
    src = self.focusedEdit()
    if not src:
        return
    re1 = "\[(?:<.+?>)?.+?(:(.+?))?\](?:</.+?>)?"
    re2 = "\[(?:<.+?>)?(.+?)(:.+?)?\](?:</.+?>)?"
    # add brackets because selected?
    cursor = src.textCursor()
    oldSrc = None
    if cursor.hasSelection():
        oldSrc = src.toHtml()
        s = cursor.selectionStart()
        e = cursor.selectionEnd()
        cursor.setPosition(e)
        cursor.insertText("]]")
        cursor.setPosition(s)
        cursor.insertText("[[")
        re1 = "\[" + re1 + "\]"
        re2 = "\[" + re2 + "\]"
    dst = None
    for field in self.fact.fields:
        w = self.fields[field.name][1]
        if w.hasFocus():
            dst = False
            continue
        if dst is False:
            dst = w
            break
    if not dst:
        dst = self.fields[self.fact.fields[0].name][1]
        if dst == w:
            return
    # check if there's alredy something there
    if not oldSrc:
        oldSrc = src.toHtml()
    oldDst = dst.toHtml()
    if unicode(dst.toPlainText()):
        if (self.lastCloze and
            self.lastCloze[1] == oldSrc and
            self.lastCloze[2] == oldDst):
            src.setHtml(self.lastCloze[0])
            dst.setHtml("")
            self.lastCloze = None
            self.saveFields()
            return
        else:
            ui.utils.showInfo(
                _("Next field must be blank."),
                help="ClozeDeletion",
                parent=self.parent)
            return
    # check if there's anything to change
    if not re.search("\[.+?\]", unicode(src.toPlainText())):
        ui.utils.showInfo(
            _("You didn't specify anything to occlude."),
            help="ClozeDeletion",
            parent=self.parent)
        return
    # create
    s = unicode(src.toHtml())
    def repl(match):
        exp = ""
        if match.group(2):
            exp = match.group(2)
        return '<font color="%s"><b>[...%s]</b></font>' % (
            ui.facteditor.clozeColour, exp)
    new = re.sub(re1, repl, s)
    old = re.sub(re2, '<font color="%s"><b>\\1</b></font>'
                 % ui.facteditor.clozeColour, s)
    src.setHtml(new)
    dst.setHtml(old)
    self.lastCloze = (oldSrc, unicode(src.toHtml()),
                      unicode(dst.toHtml()))
    self.saveFields()
    return True

def onMenuSetup(browser):
    act = QAction(mw)
    act.setText("Generate Clozes")
    browser.dialog.menuActions.addSeparator()
    browser.dialog.menuActions.addAction(act)
    browser.connect(act, SIGNAL("triggered()"), lambda b=browser: onCloze(b))

addHook("editor.setupMenus", onMenuSetup)
ui.facteditor.FactEditor.onCloze = onClozeRepl

########NEW FILE########
__FILENAME__ = bulkrecord
# -*- coding: utf-8 -*-
# Copyright: Damien Elmes <anki@ichi2.net>
# License: GNU GPL, version 3 or later; http://www.gnu.org/copyleft/gpl.html
#
# This plugin lets you record audio for a number of cards at once - very
# useful for teachers or students who have a native-speaking friend.
#
# Screenshots: http://ichi2.net/anki/plugins/bulkrecord
#
# Only Linux and Windows are currently supported - to use this plugin on
# Windows or OSX, you'll need to modify the getAudio() function
#
# On Linux, you need three programs:
# 1. mplayer (for playback)
# 2. ecasound (for recording)
# 3. sox (for noise reduction)
#
# On Windows, you need two to install two programs:
# 1. Download http://prdownloads.sourceforge.net/sox/sox-14.1.0-cygwin.zip?download
# 2. Download http://www.rarewares.org/dancer/dancer.php?f=226
# 3. Unzip each file and copy the .exe and .dll files to your windows
# directory (usually c:\windows)
# - To run the commands below, choose Start -> Run, type cmd, choose OK, then
# type the commands below without the $.
#
# version 1: initial release
# version 2: add windows support, change instructions, noise amplification
#
###############################################################################
# Build a noise profile
###############################################################################
#
# First you need to create a noise profile so that background noise will be
# cancelled.
#
# On the command line, run the following, and hit Ctrl+c after you've recorded
# 10 seconds of silence
#
# $ rec silence.wav
#
# Next, record yourself speaking and hit Ctrl+c when done. Try to include some words
# like 'put' - some sounds are naturally louder than others, and we want a
# good sample for the next section. Speak at the same volume and distance from
# the mic as you plan to when recording material later. Again, hit Ctrl+c to
# stop recording.
#
# $ rec speaking.wav
#
# Now build the noise profile
#
# $ sox silence.wav -t null /dev/null noiseprof noiseprofile
#
# Determine the optimum level of noise cancelation by putting on some
# earphones and running the following command, changing 0.1 to a value between
# 0.1 and 1.0. Higher numbers will cancel more noise, but will also probably
# cancel your voice too:
#
# $ play speaking.wav noisered noiseprofile 0.1
#
# When you've determined the optimum number, write it down for later, then run
# the following command for the next step:
#
# $ sox speaking.wav speaking2.wav noisered noiseprofile 0.1
#
# If you're on windows, you may want to move the noise profile to an easier to
# access location:
#
# $ mv noiseprofile c:\
#
###############################################################################
# Determine optimum amplification & bass
###############################################################################
#
# Next you need to find the optimum amplification level and bass boost.
#
# Run the following command. Look for the 'clip' section at the bottom right
# of the program output. Make sure that no samples are clipped (which means
# it's too loud and the audio is being distorted). When you're happy with the
# numbers, adjust them below. The bass boost compensates for the lack of bass
# response on cheap microphones. Adjust to suit.
#
# $ play speaking2.wav norm -3 bass +5
#
###############################################################################
# Win32 notes
###############################################################################
#
# If you have problems, there are two likely culprits:
#
# 1. Make sure c:\tmp exists, it's needed to store a temporary file when
# normalizing
#
# 2. Make sure you've specified the correct path to your noise profile.
#
# To stop recording, hit ctrl+c
#
###############################################################################
# Recording in Anki
###############################################################################
#
# To use the plugin, add a field called 'Audio' to your facts (or change
# AUDIO_FIELD_NAME below). Add %(Audio)s to the answer format of your cards.
# Then select some cards in the editor, click the Facts button, and choose
# "Bulk Record". You'll be prompted to record each card that has an empty
# field.
#
###############################################################################
# User variables
###############################################################################
# Adjust this section to customize amplification, path to your noise profile,
# etc.

import os

# the field in your card model
AUDIO_FIELD_NAME = "Audio"

NOISE_PROFILE_LOCATION = "/home/resolve/Lib/misc/noiseprofile"
# on win32, use something like the following (assuming you've put the
# noiseprofile file in c:\
#NOISE_PROFILE_LOCATION = "c:\\noiseprofile"

# the amount of noise to cancel
NOISE_AMOUNT = "0.1"
# the amount of amplification
NORM_AMOUNT = "-3"
# the amount of bass
BASS_AMOUNT = "+5"

###############################################################################

import subprocess, signal, re, stat, socket, sys, tempfile, traceback
from PyQt4.QtCore import *
from PyQt4.QtGui import *
from ankiqt import mw
from ankiqt.ui import cardlist
from ankiqt.ui.utils import showInfo
from anki.facts import Fact
from anki.media import copyToMedia

try:
    import hashlib
    md5 = hashlib.md5
except ImportError:
    import md5
    md5 = md5.new

audioPlayCommand = ["mplayer", "-really-quiet"]
# ecasound for recording, since sox cuts off the end
audioRecordCommand = ["ecasound", "-x", "-f:16,1,44100", "-i",
                      "alsahw,1,0", "-o", "tmp.wav"]
# sox for postprocessing
audioProcessCommand = ["sox", "tmp.wav", "tmp2.wav",
                       # noise reduction
                       "noisered", NOISE_PROFILE_LOCATION, NOISE_AMOUNT]
audioProcessCommand2 = ["sox", "tmp2.wav", "tmp3.wav",
                       "norm", NORM_AMOUNT, "bass", BASS_AMOUNT, "fade", "0.2", "0"]
audioProcessCommand3 = ["lame", "tmp3.wav", "tmp.mp3", "--noreplaygain"]

# override for different computer with different microphone & noise settings
if socket.gethostname() == "mobile":
    audioRecordCommand = ["ecasound", "-x", "-f:16,1,44100", "-i",
                          "alsahw,0,0", "-o", "tmp.wav"]
    audioProcessCommand = ["sox", "tmp.wav", "tmp2.wav",
                           # noise reduction
                           "noisered", "/home/resolve/Lib/misc/noiseprofile-mobile", NOISE_AMOUNT]

##########################################################################
# win32 compat

if sys.platform.startswith("win32"):
    # override for windows
    audioPlayCommand = [
        "c:\\program files\\windows media player\\wmplayer.exe"]
    audioRecordCommand = ["rec", "tmp.wav"]
    startupInfo = subprocess.STARTUPINFO()
    startupInfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
else:
    startupInfo = None

##########################################################################

bulkRecordAction = None
editorObj = None


(tempfd, tempname) = tempfile.mkstemp()
tmpfile = os.fdopen(tempfd, "w+")

def getAudio(string, parent):
    "Record and return filename"
    # record first
    process = subprocess.Popen(audioRecordCommand)
    if not sys.platform.startswith("win32"):
        mb2 = QMessageBox(parent)
        but = QPushButton("Stop")
        mb2.addButton(but, QMessageBox.RejectRole)
        mb2.setText(string + "<br><br>Recording..")
        mb2.exec_()
        os.kill(process.pid, signal.SIGINT)
    process.wait()
    # postprocess
    try:
        subprocess.check_call(audioProcessCommand, stdout=tmpfile, stderr=tmpfile)
        subprocess.check_call(audioProcessCommand2, stdout=tmpfile, stderr=tmpfile)
        subprocess.check_call(audioProcessCommand3, stdout=tmpfile, stderr=tmpfile)
    except:
        tmpfile.flush()
        showInfo("Error occurred:\n%s\n%s" % (
            traceback.format_exc(),
            open(tempname).read()))
    return "tmp.mp3"

def bulkRecord(parent):
    modelIds = mw.deck.s.column0("""
select distinct modelId from fieldModels
where name = :name""", name=AUDIO_FIELD_NAME)
    factIds = parent.selectedFacts()
    needed = []
    for mid in modelIds:
        ordinal = mw.deck.s.scalar(
"""select ordinal from fieldModels
where modelId = :mid and name = :name""",
name=AUDIO_FIELD_NAME, mid=mid)
        for fact in mw.deck.s.query(Fact).filter_by(modelId=mid):
            if fact.id not in factIds:
                continue
            if not fact.fields[ordinal].value:
                needed.append((fact, ordinal))
    total = len(needed)
    count = 1
    for (fact, ordinal) in needed:
        if not recordFact(parent, fact, ordinal, count, total):
            break
        count += 1

def recordFact(parent, fact, ordinal, count, total):
    recorded = False
    while 1:
        mb = QMessageBox(parent)
        mb.setWindowTitle("%d of %d" % (count, total))
        mb.setTextFormat(Qt.RichText)
        # display string
        str = ""
        for field in fact.fields:
            str += "%s: %s<br>" % (field.name, field.value)
        mb.setText(str)
        # save
        bSave = QPushButton("Save and continue")
        mb.addButton(bSave, QMessageBox.RejectRole)
        if not recorded:
            bSave.setEnabled(False)
        # replay
        bReplay = QPushButton("Replay")
        mb.addButton(bReplay, QMessageBox.RejectRole)
        if not recorded:
            bReplay.setEnabled(False)
        # record (again)
        if recorded:
            bRecord = QPushButton("Record again")
        else:
            bRecord = QPushButton("Record")
        mb.addButton(bRecord, QMessageBox.RejectRole)
        # skip
        bSkip = QPushButton("Skip this fact")
        mb.addButton(bSkip, QMessageBox.RejectRole)
        # stop
        bStop = QPushButton("Stop bulk update")
        mb.addButton(bStop, QMessageBox.RejectRole)
        mb.exec_()
        if mb.clickedButton() == bRecord:
            recorded = getAudio(str, parent)
            continue
        elif mb.clickedButton() == bReplay:
            subprocess.Popen(audioPlayCommand + [os.path.abspath("tmp.mp3")])
            continue
        elif mb.clickedButton() == bSave:
            new = copyToMedia(mw.deck, recorded)
            os.unlink("tmp.mp3")
            os.unlink("tmp.wav")
            os.unlink("tmp2.wav")
            os.unlink("tmp3.wav")
            fact.fields[ordinal].value = u"[sound:%s]" % new
            fact.setModified(textChanged=True)
            mw.deck.flushMod()
            mw.deck.save()
            editorObj.updateAfterCardChange()
            return True
        elif mb.clickedButton() == bSkip:
            return True
        elif mb.clickedButton() == bStop:
            return False

def setupMenus(parent):
    global bulkRecordAction, editorObj
    editorObj = parent
    bulkRecordAction = QAction(parent)
    bulkRecordAction.setText("Bulk record")
    parent.connect(bulkRecordAction, SIGNAL("triggered()"),
                   lambda parent=parent: bulkRecord(parent))
    parent.dialog.menuActions.addSeparator()
    parent.dialog.menuActions.addAction(bulkRecordAction)

mw.addHook("editor.setupMenus", setupMenus)

########NEW FILE########
__FILENAME__ = bulkrename
# -*- coding: utf-8 -*-
# Copyright: Damien Elmes <anki@ichi2.net>
# License: GNU GPL, version 3 or later; http://www.gnu.org/copyleft/gpl.html

# this plugin lets you apply transformations to your media files. one use for
# this is when you convert all your wav files to mp3 files, and so on. it
# will try to rename the files if they exist - if they have already been
# renamed, it will continue without problems.
#
# no checking is done to see if files already exist or your pattern is safe,
# so be sure to back your deck and media directory up first.
#
# the default replacement string takes a file in a subdirectory and moves it
# to the top level media directory - eg a path like this:
#
#   foo/bar/baz.mp3
#
# becomes
#
#   foo-bar-baz.mp3
#

# version 1: initial release

from PyQt4.QtCore import *
from PyQt4.QtGui import *
from ankiqt import mw, ui
from anki.media import mediaRefs, _modifyFields
import os, re

fromStr = "/"
toStr = "-"

def bulkrename():
    # rename files
    deck = mw.deck
    mediaDir = deck.mediaDir()
    dirs = [mediaDir]
    renamedFiles = 0
    while 1:
        if not dirs:
            break
        dir = dirs.pop()
        for fname in os.listdir(unicode(dir)):
            path = os.path.join(dir, fname)
            if os.path.isdir(path):
                dirs.append(path)
                continue
            else:
                relpath = path[len(mediaDir)+1:]
                newrel = re.sub(fromStr, toStr, relpath)
                if relpath != newrel:
                    os.rename(os.path.join(mediaDir, relpath),
                              os.path.join(mediaDir, newrel))
                    renamedFiles += 1
    # rename fields
    modifiedFacts = {}
    updateFields = []
    for (id, fid, val) in deck.s.all(
        "select id, factId, value from fields"):
        oldval = val
        for (full, fname, repl) in mediaRefs(val):
            tmp = re.sub(fromStr, toStr, fname)
            if tmp != fname:
                val = re.sub(re.escape(full), repl % tmp, val)
        if oldval != val:
            updateFields.append({'id': id, 'val': val})
            modifiedFacts[fid] = 1
    if modifiedFacts:
        _modifyFields(deck, updateFields, modifiedFacts, True)
    ui.utils.showInfo("%d files renamed.\n%d facts modified." %
                      (renamedFiles, len(modifiedFacts)))

def init():
    q = QAction(mw)
    q.setText("Bulk Rename")
    mw.mainWin.menuAdvanced.addSeparator()
    mw.mainWin.menuAdvanced.addAction(q)
    mw.connect(q, SIGNAL("triggered()"), bulkrename)

mw.addHook("init", init)

########NEW FILE########
__FILENAME__ = cardstats
# -*- coding: utf-8 -*-
# Copyright: Damien Elmes <anki@ichi2.net>
# License: GNU GPL, version 3 or later; http://www.gnu.org/copyleft/gpl.html
#
# Show statistics about the current and previous card while reviewing.
# Activate from the tools menu.
#

from anki.hooks import addHook
from aqt import mw
from aqt.qt import *
from aqt.webview import AnkiWebView
import aqt.stats

class CardStats(object):
    def __init__(self, mw):
        self.mw = mw
        self.shown = False
        addHook("showQuestion", self._update)
        addHook("deckClosing", self.hide)
        addHook("reviewCleanup", self.hide)

    def _addDockable(self, title, w):
        class DockableWithClose(QDockWidget):
            def closeEvent(self, evt):
                self.emit(SIGNAL("closed"))
                QDockWidget.closeEvent(self, evt)
        dock = DockableWithClose(title, mw)
        dock.setObjectName(title)
        dock.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea)
        dock.setFeatures(QDockWidget.DockWidgetClosable)
        dock.setWidget(w)
        if mw.width() < 600:
            mw.resize(QSize(600, mw.height()))
        mw.addDockWidget(Qt.RightDockWidgetArea, dock)
        return dock

    def _remDockable(self, dock):
        mw.removeDockWidget(dock)

    def show(self):
        if not self.shown:
            class ThinAnkiWebView(AnkiWebView):
                def sizeHint(self):
                    return QSize(200, 100)
            self.web = ThinAnkiWebView()
            self.shown = self._addDockable(_("Card Info"), self.web)
            self.shown.connect(self.shown, SIGNAL("closed"),
                               self._onClosed)
        self._update()

    def hide(self):
        if self.shown:
            self._remDockable(self.shown)
            self.shown = None
            #actionself.mw.form.actionCstats.setChecked(False)

    def toggle(self):
        if self.shown:
            self.hide()
        else:
            self.show()

    def _onClosed(self):
        # schedule removal for after evt has finished
        self.mw.progress.timer(100, self.hide, False)

    def _update(self):
        if not self.shown:
            return
        txt = ""
        r = self.mw.reviewer
        d = self.mw.col
        if r.card:
            txt += _("<h3>Current</h3>")
            txt += d.cardStats(r.card)
        lc = r.lastCard()
        if lc:
            txt += _("<h3>Last</h3>")
            txt += d.cardStats(lc)
        if not txt:
            txt = _("No current card or last card.")
        self.web.setHtml("""
<html><head>
</head><body><center>%s</center></body></html>"""% txt)

_cs = CardStats(mw)

def cardStats(on):
    _cs.toggle()

action = QAction(mw)
action.setText("Card Stats")
action.setCheckable(True)
action.setShortcut(QKeySequence("Shift+C"))
mw.form.menuTools.addAction(action)
mw.connect(action, SIGNAL("toggled(bool)"), cardStats)

########NEW FILE########
__FILENAME__ = changecolor
# -*- coding: utf-8 -*-
# Copyright: Damien Elmes <anki@ichi2.net>
# License: GNU GPL, version 3 or later; http://www.gnu.org/copyleft/gpl.html

from PyQt4.QtCore import *
from PyQt4.QtGui import *
from ankiqt import mw
from ankiqt.ui import facteditor

def setColour(widget, colour):
    w = widget.focusedEdit()
    cursor = w.textCursor()
    new = QColor(colour)
    w.setTextColor(new)
    cursor.clearSelection()
    w.setTextCursor(cursor)

def turnBlue(self):
    setColour(self, "#0000FF")

def newFields(self):
    oldFields(self)
    b1 = QPushButton()
    b1.connect(b1, SIGNAL("clicked()"), lambda self=self: turnBlue(self))
    b1.setShortcut("F1")
    self.iconsBox.addWidget(b1)
    print "foo"

oldFields = facteditor.FactEditor.setupFields
facteditor.FactEditor.setupFields = newFields

########NEW FILE########
__FILENAME__ = changekeys
# -*- coding: utf-8 -*-
# Copyright: Damien Elmes <anki@ichi2.net>
# License: GNU GPL, version 3 or later; http://www.gnu.org/copyleft/gpl.html
#
# An example of how to override review shortcuts. Changes:
# - when '5' is pressed with the question shown, show the answer
# - when '6' is pressed with the answer shown, answer with the default button
# - when '7' is pressed, undo the last review
# - when '8' is pressed, mark the card
# You can edit the code below to customize it.

from aqt import mw
from aqt.reviewer import Reviewer
from anki.hooks import wrap

def keyHandler(self, evt, _old):
    key = unicode(evt.text())
    if key == "5" and self.state == "question":
        self._showAnswerHack()
    elif key == "6" and self.state == "answer":
        self._answerCard(self._defaultEase())
    elif key == "7":
        self.mw.onUndo()
    elif key == "8":
        self.onMark()
    else:
        return _old(self, evt)

Reviewer._keyHandler = wrap(Reviewer._keyHandler, keyHandler, "around")


########NEW FILE########
__FILENAME__ = chinese
# -*- coding: utf-8 -*-
# Copyright: Damien Elmes <anki@ichi2.net>
# License: GNU GPL, version 3 or later; http://www.gnu.org/copyleft/gpl.html
#
# This plugin adds Mandarin and Cantonese models, and implements basic reading
# generation via unihan.db. It will be obsoleted by the Mandarin and Cantonese
# toolkit in the future.
#

import sys, os, re
from anki.utils import findTag, stripHTML
from anki.hooks import addHook
from anki.db import *

cantoneseTag = "Cantonese"
mandarinTag = "Mandarin"
srcFields = ('Expression',) # works with n pairs
dstFields = ('Reading',)

# Models
##########################################################################

from anki.models import Model, CardModel, FieldModel
import anki.stdmodels

def MandarinModel():
   m = Model(_("Mandarin"))
   f = FieldModel(u'Expression')
   f.quizFontSize = 72
   m.addFieldModel(f)
   m.addFieldModel(FieldModel(u'Meaning', False, False))
   m.addFieldModel(FieldModel(u'Reading', False, False))
   m.addCardModel(CardModel(u"Recognition",
                            u"%(Expression)s",
                            u"%(Reading)s<br>%(Meaning)s"))
   m.addCardModel(CardModel(u"Recall",
                            u"%(Meaning)s",
                            u"%(Expression)s<br>%(Reading)s",
                            active=False))
   m.tags = u"Mandarin"
   return m

anki.stdmodels.models['Mandarin'] = MandarinModel

def CantoneseModel():
    m = Model(_("Cantonese"))
    f = FieldModel(u'Expression')
    f.quizFontSize = 72
    m.addFieldModel(f)
    m.addFieldModel(FieldModel(u'Meaning', False, False))
    m.addFieldModel(FieldModel(u'Reading', False, False))
    m.addCardModel(CardModel(u"Recognition",
                             u"%(Expression)s",
                             u"%(Reading)s<br>%(Meaning)s"))
    m.addCardModel(CardModel(u"Recall",
                             u"%(Meaning)s",
                             u"%(Expression)s<br>%(Reading)s",
                             active=False))
    m.tags = u"Cantonese"
    return m

anki.stdmodels.models['Cantonese'] = CantoneseModel

# Controller
##########################################################################

class UnihanController(object):

    def __init__(self, target):
        if sys.platform.startswith("win32"):
           base = unicode(os.path.dirname(os.path.abspath(__file__)),
                          "mbcs")
        else:
           base = os.path.dirname(os.path.abspath(__file__))
        self.engine = create_engine(u"sqlite:///" + os.path.abspath(
            os.path.join(base, "unihan.db")),
                                    echo=False, strategy='threadlocal')
        self.session = sessionmaker(bind=self.engine,
                                    autoflush=False,
                                    autocommit=True)
        self.type = target

    def reading(self, text):
        text = stripHTML(text)
        result = []
        s = SessionHelper(self.session())
        for c in text:
            n = ord(c)
            ret = s.scalar("select %s from unihan where id = :id"
                           % self.type, id=n)
            if ret:
                result.append(self.formatMatch(ret))
        return u" ".join(result)

    def formatMatch(self, match):
        m = match.split(" ")
        if len(m) == 1:
            return m[0]
        return "{%s}" % (",".join(m))

# Double click to remove handler
##########################################################################

from PyQt4.QtCore import *
from PyQt4.QtGui import *
from ankiqt.ui.facteditor import FactEdit

# this shouldn't be necessary if/when we move away from kakasi
def mouseDoubleClickEvent(self, evt):
    t = self.parent.fact.model.tags.lower()
    if (not "japanese" in t and
        not "mandarin" in t and
        not "cantonese" in t):
        return QTextEdit.mouseDoubleClickEvent(self,evt)
    r = QRegExp("\\{(.*[|,].*)\\}")
    r.setMinimal(True)

    mouseposition = self.textCursor().position()

    blockoffset = 0
    result = r.indexIn(self.toPlainText(), 0)

    found = ""

    while result != -1:
        if mouseposition > result and mouseposition < result + r.matchedLength():
            mouseposition -= result + 1
            frompos = 0
            topos = 0

            string = r.cap(1)
            offset = 0
            bits = re.split("[|,]", unicode(string))
            for index in range(0, len(bits)):
                offset += len(bits[index]) + 1
                if mouseposition < offset:
                    found = bits[index]
                    break
            break

        blockoffset= result + r.matchedLength()
        result = r.indexIn(self.toPlainText(), blockoffset)

    if found == "":
        return QTextEdit.mouseDoubleClickEvent(self,evt)
    self.setPlainText(self.toPlainText().replace(result, r.matchedLength(), found))

FactEdit.mouseDoubleClickEvent = mouseDoubleClickEvent

# Hooks
##########################################################################

class ChineseGenerator(object):

    def __init__(self):
        self.unihan = None

    def toReading(self, type, val):
        try:
            if not self.unihan:
                self.unihan = UnihanController(type)
            else:
                self.unihan.type = type
            return self.unihan.reading(val)
        except:
            return u""

unihan = ChineseGenerator()

def onFocusLost(fact, field):
    if field.name not in srcFields:
        return
    if findTag(cantoneseTag, fact.model.tags):
        type = "cantonese"
    elif findTag(mandarinTag, fact.model.tags):
        type = "mandarin"
    else:
        return

    idx = srcFields.index(field.name)
    dstField = dstFields[idx]

    try:
        if fact[dstField] and fact[dstField] != "<br />":
            return
    except:
        return
    fact[dstField] = unihan.toReading(type, field.value)

addHook('fact.focusLost', onFocusLost)

from ankiqt import mw
mw.registerPlugin("Basic Chinese Support", 171)

########NEW FILE########
__FILENAME__ = chineseexamples
#!/usr/bin/python
#-*- coding: utf-8 -*-
# ---------------------------------------------------------------------------
# author: aaron@lamelion.com
# tested on ubuntu linux and windows xp
# This file is a plugin for anki flashcard application http://ichi2.net/anki/
# ---------------------------------------------------------------------------

import codecs

from PyQt4.QtCore import *
from PyQt4.QtGui import *
from anki.latex import renderLatex
from anki.sound import playFromText, stripSounds
from ankiqt.ui.utils import mungeQA
from ankiqt import mw

import re
import os
import pickle
import urllib,urllib2


curIndex = 0
isOn = False
senFile = os.path.join(mw.config.configPath,'plugins', 'chineseSentences.pickle')
if os.path.exists(senFile):
    pickled = open(senFile,'rb')
    sentences = pickle.load(pickled)
    pickled.close()
else:
    errm = QErrorMessage(mw)
    errm.showMessage('ChineseExampleSentence plugin: you need to put the chinese examples data file into %s'%senFile)

#example sentence lookup & disp ######################################################################
def findChar(c):
    found = []
    for k,v in sentences.iteritems():
        if v[0].find(c)>-1:
            v.append(k)
            found.append(v)
    return found

def moveToStateCES(state):
    origMoveToState(state)
    if state=='showQuestion' or state=='getQuestion' or state=='showAnswer': buttStates(True)
    elif  state=='studyScreen' or state=='initial' or state=='noDeck': buttStates(False)
    else: buttStates(False)

def buttStates(on):
    global toggle,next
    if on:
        toggle.setEnabled(True)
        next.setEnabled(toggle.isChecked() and mw.state=='showAnswer')
    else:
        toggle.setEnabled(False)
        next.setEnabled(False)       

def cardAnsweredCES(quality):
    global curIndex
    curIndex = 0
    origCardAnswered(quality)

def drawAnswerCES():
    if not isOn:
        origDrawAnswer()
        return
    a = mw.currentCard.htmlAnswer()
    mainAns = mungeQA(mw.bodyView.main.deck, a)
    mw.bodyView.write('<span id=answer />'+mainAns)
    mw.bodyView.flush()
    currentCard = mw.currentCard
    word = currentCard.fact['Expression']
    exSens = findChar(' '+word.strip()+' ')
    displayableExSens = exSensFormat(exSens,word)
    mw.bodyView.write(displayableExSens)
    if mw.bodyView.state != mw.bodyView.oldState:
        playFromText(a)

def exSensFormat(exSens,word):
    exSens.sort(senLenCmp)
    max = 1
    hlStyle = '<span style="background-color:#FFDA44;">'
    exStyle = '<span style="font-size:15px">'
    if len(exSens)<max: max = len(exSens)
    offset = curIndex
    dif = len(exSens)-(offset+max)
    if dif<0: return "no more sentences"
    formated = ""
    if len(exSens)>0:
        for i in range(0+offset,max+offset):
            hl = exSens[i][0]
        trans = gTrans(hl)
        start = hl.find(word)
        end = len(word)+start
        numSpaces = hl[:start].count(' ')
        pySplit = exSens[i][1].split(' ')
        pySplit[numSpaces] = hlStyle.replace('44;','44;font-size:15px')+pySplit[numSpaces]+'</span>'
        hl = hl[:start]+hlStyle+hl[start:end]+'</span>'+hl[end:]
        formated += str(i+1)+') '+hl+'<br>'+exStyle+(' '.join(pySplit))+'</span><br>'+trans+'<br><br>'
    else:
        formated = "no examples found"
    return formated+"<span style='color:gray'>found "+str(len(exSens))+" examples out of "+str(len(sentences))+"</span>"

def senLenCmp(x,y):
    return cmp(len(x[0]),len(y[0]))



#gtrans ######################################################################
def gTrans(src):
    url="http://translate.google.com/translate_a/t?client=t&text=%s&sl=%s&tl=%s"%(urllib.quote(src.encode('utf-8')),'zh-CN','en')
    con=urllib2.Request(url, headers={'User-Agent':'Mozilla/5.0 (X11; U; Linux i686) Gecko/20071127 Firefox/2.0.0.11'}, origin_req_host='http://translate.google.com')
    try:
        req=urllib2.urlopen(con)
    except urllib2.HTTPError, detail:
        return '<span style="color:gray">Could not get translation: '+str(detail)+'</span>'
    except urllib2.URLError, detail:
        return '<span style="color:gray">Could not get translation: '+str(detail)+'</span>'
    ret=U''
    for line in req:
        line = line.decode('utf-8').strip()
        break
    return re.match('.+?"(.+?)"', line).group(1)

#LOGO ######################################################################
logo = '\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00 \x00\x00\x00\x0f\x08\x06\x00\x00\x00\x85\x80\xcd\x17\x00\x00\x00\x04gAMA\x00\x00\xaf\xc87\x05\x8a\xe9\x00\x00\x00\x19tEXtSoftware\x00Adobe ImageReadyq\xc9e<\x00\x00\x02\xe2IDATx\xdabd\xc0\x0f\x18\x81\x98\x15\x88\xd9\xa1\xf4? \xfe\t\xc4\xbf\x80\xf8/\x03\x15\x00@\x001\x12\x90\xe3\x06b\t V\x00bA\xa8\xe5\x8f\xa1\xf8\x03\x10\xff\xa1\xd4\x01\x00\x01\x04s\x00\x13\x10\xb3@13\x12_\x1a\x88M\x81\xd8\x15\x88\xd5\x80\xf8\x0b\x10\x1f\x05\xe2\x83@|\r\x88\xdf\x02\xf1\x7f\xa8ZV\xa8Y\xbf\xa0\xf8?\xd4,Fhh\xfd\x83\xca\xb3 \x89\xfd\x01\x08 Fh\xf0\n\x01\xb1\x14\x10\x8b\x021\x0f\xd4\x01 \x03U\x80\xd8\xcd\x85\x81\xc1\xca\x18\xaa\xbb\x13B\xad\x85:\xe2.\xd42PH\xf1A\x95\xbc\x85\xe2?P\xb3X\xa1j\xbeA\xcd\x85\x99\xff\t\x88\x9f\x01\x04\x10\xc8\x01\x92@\xac\x07\xc4\x8e@l\x08\xe5\xb3@\x15\xc9\x011g9\x90\xe8\xc0\x8c\xb3w@|\x15j0(z\xc4\xa0\xe2 G\xdd\x83\x8a\x83\xa2\x8f\x17\x1au\xef\xa0!"\n\xf5\xfd- \xde\x0b\x10@ \x8b\xc4\x81\xd8\x16hB\x811$4P\xc0\x1e4\xbe\x12\x10\x87B\x98B\xb3\x80\xfa\xde\x03\x19...\x0c\xc6\xc6\x900:{\xf6\xac\xc2\x9e={\x9c\x19\xa0\xe2 p\xef\xde=0F\x16{\xf0\xe0\xc1\xc7;w\xee|\x00\x08 \x10\xdb\n\x88\x17\x02\x85\xff\xff\xc7\x82AqY\x8e\xc4\x7f\x87\xc4^\x05\xc43g\xce\xfc\x8f\x0e@b`}\xe5\xe5`\xfe\xbbw\xef\xfe\x03\x1d\x88\xc2\x17\x14\x14\x04\xa9\xe9\x00\x08 \x06h"\x9b\r\x0c\x81\xff G\x84"Y2\x13\x8b\x03\xca\xa1\x16\x83\xf9..pK\x81>\x03c\x18\x00Y\x08\xd2\xbb{\xf7n0\xff\xcc\x993p\xb9\xd0\xd0\xd0\xff\xd0DY\n\x10@ \x07\xe8B\xd3\x16D\x03\xd4\xf0\xddP>\xba\x03P\xf8P\x1f\x81\x00\xc8"\x98e \x00\xf2-H-\xc8\xa7\xc8`\xd5\xaaU0sAi \x06 \x80@i\x80\x03\x88\x05@.\x99\t\x8a#P<\x02q\x18\x89\xf9\x19\x18\xef(40-\xa0\xc49\x0c\x80\xf8@G1\xbc\x7f\xff\x1e\x94\xf3\x04\x00\x02\x08\x94\xd2\xf9AY\x10\x94\xb0\xd2\xa0\x8a\xeeA\xd9\xe5\xd0D\x87\x13\xac^\x8d!\x04\xb3\x10\xe4\x00\x90E\xc0\xf4\x00\xe6WTT\x80\x1d\x87$&\x0c\xc4\xf2\x00\x01\xc4\x00-d6\x94\xe3H\x84.\xf8\xa2\x00\x88\xd3\xd2\xd20\x12!H\x0c\xa4\x0e\x14\xdc\xb0\xf8\x07\xf1\x95\x94\x94\xc0\t\x10)\x8af\x00\x04\x10([\xeb\x03\xb1/\x10\'\x00\xb129\xc5)\xc8WH\xd9\x10\x14\xbc\xc4h\xbb\x04\xca}\x00\x01\x04r\x80\x08\xb4\xc43\x00buhA\x01*\xbd~\x03\xf1Wh\x81\xc2\x80T\xd4\xfeF\xe2\x83\xca\r6h\x1a\x12\x80\x8a?\x05es \x06\xb9\x82\x13\x8aA)\xfe;T\x0f7\xb4\x94\xbc\x0f\xc4\x17\x01\x02\x88\x11Z\xeaqA\r\xe0\x87&Jfhi\xf5\x1b\xc9Bf(\xfd\x17\x89\xcf\x8c\xa4\x9f\x0b*\xfe\tj\xf9w\xa8<\xac\x16\xfd\x83T\xc4\xff\x87z\xee\x03@\x80\x01\x00Zh\x9a\x0e\x10\xa1\xc4l\x00\x00\x00\x00IEND\xaeB`\x82'
nextLogo='\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00 \x00\x00\x00\x0f\x08\x06\x00\x00\x00\x85\x80\xcd\x17\x00\x00\x00\x04gAMA\x00\x00\xaf\xc87\x05\x8a\xe9\x00\x00\x00\x19tEXtSoftware\x00Adobe ImageReadyq\xc9e<\x00\x00\x02GIDATx\xdab\xfc\xff\xff?\x035\x00###\x13\x90b\x03b^ \xe6\x07b. \xfe\x0b\xc4\x9f\x80\xf8\x03\x10\x7f\x03\xda\xf5\x17]\x1f@\x00\xb1\x90h\tH=;\x10\xb3B\x85~\x02\xf1/ \xfe\x07\xc4\x9c@,\x05\xc4\x9a@\xac\re\x7f\x05\xe2\x9b@|\x16\x88\xef\x03\xf1gt3\x01\x02\x88\x85\x04\xcbA\x16\x88\x02\xb1<\x10\x8b\x00\xf1\x1f ~\n\xc4/\xa1>\x95\x03b+ \xf6\x03bG$\xad\xa7\x81x:\x10\xbf\xc7\xe6\x00\x80\x00b!\xc2bF\xa8\x8f%\x80\xd8\x08\x88=\xa0>\xfc\x01\xc4\xa7\x80\xf8\x02\x10\x83\xe2\xd1\x04\x88CA\x0e\xdc\xbd{7\x83\x8b\x8b\x0bL\xbf)\x90:\x04\xc4g\x80\xf81\xba\xf9\x00\x01\xc4\x00J\x03\xb80\x100\x03\xb1\x00\x10k\x01q2\x10oU\x02ZV\x0e\xc5P\x8b\x8fA\x1d\xf2_II\xe9\xff\xaaU\xab\xfe#\x03\xa8\x9a%@l\x8a\xcd\x0e\x80\x00"\xe4\x00P\x822\x06\xe2" >\x012\x0c\xe8/\x886\x84\x03\xc0x\xe6\xcc\x99\xff\xb1\x01\xa8\xfcJ \xb6\xc0f\x07@\x00\x11r\x80\x0c\x10\'\x82\x82\xd9\x05jy9\x92\x03`b\xc6 >\x10\xbc{\xf7\xee\x7fyy9I\x0e\x00\x08 B\x0eP\x05\xe2\x1a\x06$K\xb1\xe1\xdd@\x9c\x96\x96\xf6_PP\x10l!)\x0e\x00\x08 B\x89\x10\x94\xba\xbf\x81\xb2\xd3\x1e\x06\x06n\x90\x80 4N@`\x0f\x94\x06\xe5\xb1Y\xb3f\x91U~\x00\x04\x10\xa1\x10\x00e;o ^\n\x8bk\x1ci\x00\x94\xbd\xceA\xcb\x04\x92B\x00 \x80\x08\x85\x00\xc8\xe0\xab@\xbc\x02Z\x9a\xc5\x001\x1f\x9a\x9a[@\xbc\x18Z\xe2\x81\xca\x00g,\xe6\xfc\x86\x86&\x06\x00\x08 B\x0e\x00\xf9\xe8\x05\x10\x7f\x87Z\xf0\x1e\x18\xec\xd1\xc0\x82A\x01*\x7f\x03\x88\xe7Cc\x83\x03\x88\x95q8\xe0\x05\xb4\xdc\xc0\x00\x00\x01\xc4B z@E\xec\x0f`a\xf2\x13Z\xec~\x01\xe2\x07@\xac\x02\r\xda[H\xc5\xac\x00\xb4P:\r-|\x90K\xc2\xab\xd0\x10\xc4\x00\x00\x01\xc4Hle\x044\x94\x19Z\xc1\x08@\xcb\x07X\x14}\x80&T\x90\x9c"4\x8d\x82JJa ~\x0b\xb5\x1c\xecH\xa0]\x18E1@\x001R\xb16Dv\xa0\x00\xb4f\xfc\x05u \xce\xda\x10 \xc0\x00\xfd9\xc0iRg\xb6\x02\x00\x00\x00\x00IEND\xaeB`\x82'
def getLogoFile(name,data):
    logoFile = os.path.join(mw.config.configPath,'plugins',name)
    if not os.path.exists(logoFile):
        lf = open(logoFile,'wb')
        lf.write(data)
        lf.close()
    return logoFile

#anki ######################################################################
def doToggle():
    global isOn,curIndex,next
    curIndex = 0
    isOn = not isOn
    next.setEnabled(isOn and mw.state=='showAnswer')
    mw.bodyView.redisplay()

def doNext():
    global curIndex,isOn
    if isOn:
        curIndex += 1
        mw.bodyView.redisplay()
    
def initChineseExampleSentence():
    global origDrawAnswer,origCardAnswered,origMoveToState,toggle,next
    try: pickled
    except NameError: return
    origDrawAnswer = mw.bodyView.drawAnswer
    origCardAnswered = mw.cardAnswered
    origMoveToState = mw.moveToState
    mw.moveToState = moveToStateCES
    mw.cardAnswered = cardAnsweredCES
    mw.bodyView.drawAnswer = drawAnswerCES
    mw.mainWin.toolBar.addSeparator()
    toggle = QAction(mw)
    icon = QIcon()
    icon.addPixmap(QPixmap(getLogoFile('zhexsen_logo.png',logo)),QIcon.Normal,QIcon.Off)
    toggle.setIcon(icon)
    toggle.setIconText('zhex')
    toggle.setCheckable(True)
    toggle.setEnabled(False)
    mw.connect(toggle,SIGNAL("toggled(bool)"),doToggle)
    mw.mainWin.toolBar.addAction(toggle)
    next = QAction(mw)
    icon = QIcon()
    icon.addPixmap(QPixmap(getLogoFile('zhexsen_logo_next.png',nextLogo)),QIcon.Normal,QIcon.Off)
    next.setIcon(icon)
    next.setIconText('zhex:next')
    next.setEnabled(False)
    mw.connect(next,SIGNAL("triggered()"),doNext)
    mw.mainWin.toolBar.addAction(next)

mw.addHook("init", initChineseExampleSentence)





########NEW FILE########
__FILENAME__ = customfont
# -*- coding: utf-8 -*-
# Copyright: Damien Elmes <anki@ichi2.net>
# License: GNU GPL, version 3 or later; http://www.gnu.org/copyleft/gpl.html

FONT = "Times New Roman"

from aqt import mw
from aqt.qt import *

def changeFont():
    f = QFontInfo(QFont(FONT))
    ws = QWebSettings.globalSettings()
    mw.fontHeight = f.pixelSize()
    mw.fontFamily = f.family()
    mw.fontHeightDelta = max(0, mw.fontHeight - 13)
    ws.setFontFamily(QWebSettings.StandardFont, mw.fontFamily)
    ws.setFontSize(QWebSettings.DefaultFontSize, mw.fontHeight)
    mw.reset()

changeFont()

########NEW FILE########
__FILENAME__ = customMediaDir
# -*- coding: utf-8 -*-
# ------------------
# Media Custom Directory
# Written by Marcus Andrén (wildclaw@gmail.com)
# Modified by Damien Elmes (anki@ichi2.net) to make it easier to use
# ------------------
# Allows for storing of media directories separate from the anki deck

from PyQt4 import *
from PyQt4.QtCore import *
from PyQt4.QtGui import *
from ankiqt.ui.utils import getText
from anki.hooks import wrap,addHook
from anki.deck import Deck
from ankiqt import mw, ui
import os,re

CONFIG_CUSTOM_MEDIA_DIR = "MediaCustomDirectory.Directory"

def newMediaDir(self,_old,create=False):
    if not self.path or not CONFIG_CUSTOM_MEDIA_DIR in mw.config:
        return _old(self,create) #Let the original method handle the temp dir case
    else:
        (originalDirectory,filename) = os.path.split(self.path)

        mediaDirName = re.sub("(?i)\.(anki)$", ".media", filename)

        dir = os.path.join(mw.config[CONFIG_CUSTOM_MEDIA_DIR],mediaDirName)

        if create == None:
            return dir
        elif not os.path.exists(dir):
            if create:
                try:
                    os.mkdir(dir)
                    # change to the current dir
                    os.chdir(dir)
                except OSError:
                    # permission denied
                    return None
            else:
                return None
        return dir

def configureDirectory():
    if mw.config.get(CONFIG_CUSTOM_MEDIA_DIR, ""):
        return
    dir = QFileDialog.getExistingDirectory(
        mw, _("Choose Media Directory"), mw.documentDir,
        QFileDialog.ShowDirsOnly)
    dir = unicode(dir)
    if not dir:
        return
    mw.config[CONFIG_CUSTOM_MEDIA_DIR] = dir
    mw.config.save()

def reconfigureDirectory():
    mw.config[CONFIG_CUSTOM_MEDIA_DIR] = ""
    configureDirectory()

Deck.mediaDir = wrap(Deck.mediaDir,newMediaDir,"")

# Setup menu entries
menu1 = QAction(mw)
menu1.setText("Change Media Directory")
mw.connect(menu1, SIGNAL("triggered()"),reconfigureDirectory)
mw.mainWin.menuAdvanced.addSeparator()
mw.mainWin.menuAdvanced.addAction(menu1)

addHook("init", configureDirectory)

########NEW FILE########
__FILENAME__ = customPlayer
# -*- coding: utf-8 -*-
# Copyright: Damien Elmes <anki@ichi2.net>
# License: GNU GPL, version 3 or later; http://www.gnu.org/copyleft/gpl.html
#
# This plugin allows you to customize the default media player to use a
# program of your choice. It will be used for any files with [sound:..] tags -
# this includes movies you specify with that tag.
#
# If you're on OSX, you'll probably need to specify a full path, like
# "/Applications/MyProgram.app/Contents/MacOS/myprogram". You can find out the
# path by going to your applications folder, right clicking on the app, and
# choosing to show the contents of the package.
#

##########################################################################

# change 'customPlayer' to the player you want
#externalPlayer = ["mplayer", "-really-quiet"]
externalPlayer = ["customPlayer"]

##########################################################################

externalManager = None
queue = []

import threading, subprocess, sys, time
import anki.sound as s

class QueueMonitor(threading.Thread):

    def run(self):
        while 1:
            if queue:
                path = queue.pop(0)
                try:
                    s.retryWait(subprocess.Popen(
                        externalPlayer + [path], startupinfo=s.si))
                except OSError:
                    raise Exception("Audio player not found")
            else:
                return
            time.sleep(0.1)

def queueExternal(path):
    global externalManager
    path = path.encode(sys.getfilesystemencoding())
    queue.append(path)
    if not externalManager or not externalManager.isAlive():
        externalManager = QueueMonitor()
        externalManager.start()

def clearExternalQueue():
    global queue
    queue = []

s._player = queueExternal
s._queueEraser = clearExternalQueue

########NEW FILE########
__FILENAME__ = customRecorder
# -*- coding: utf-8 -*-
# Copyright: Damien Elmes <anki@ichi2.net>
# License: GNU GPL, version 3 or later; http://www.gnu.org/copyleft/gpl.html
#
# Lets you customize the settings used for the recorder

from anki import sound as s
import pyaudio

s.PYAU_FORMAT = pyaudio.paInt16
s.PYAU_CHANNELS = 1
s.PYAU_RATE = 44100
# change the input index to a different number to match your device
# try 1, 2, etc.
s.PYAU_INPUT_INDEX = 0

# if you can't guess the number, uncomment the following lines, and then
# restart Anki. An error will pop up, listing each of your devices. Then
# update the number above and comment the lines below again.

# import sys
# p = pyaudio.PyAudio()
# for x in range(p.get_device_count()):
#     sys.stderr.write("%d %s\n" % (x, p.get_device_info_by_index(x)))

########NEW FILE########
__FILENAME__ = defaultbuttons
# -*- coding: utf-8 -*-
# Copyright: Damien Elmes <anki@ichi2.net>
# License: GNU GPL, version 3 or later; http://www.gnu.org/copyleft/gpl.html
#
# Allows you to change the default buttons. Replace '2' and '3' with what you
# like.
#

from ankiqt import ui

def defaultEaseButton(self):
    if self.currentCard.successive:
        # card was answered correctly previously
        return 3
    if self.currentCard.reps:
        # card has been answered before, but not successfully
        return 2
    # card hasn't been seen before
    return 2

ui.main.AnkiQt.defaultEaseButton = defaultEaseButton

########NEW FILE########
__FILENAME__ = deurl-files
# -*- coding: utf-8 -*-
# Copyright: Damien Elmes <anki@ichi2.net>
# License: GNU GPL, version 3 or later; http://www.gnu.org/copyleft/gpl.html
#
# Convert percent escapes in files and sound: references
#

import re, os, urllib
from aqt import mw
from aqt.qt import *
from aqt.utils import showInfo, askUser
from anki.utils import ids2str

def fix():
    if not askUser("Have you backed up your collection and media folder?"):
        return
    mw.progress.start(immediate=True)
    # media folder
    for file in os.listdir(mw.col.media.dir()):
        ok = False
        if "%" not in file:
            continue
        for type in "mp3", "wav", "ogg":
            if file.endswith(type):
                ok = True
                break
        if not ok:
            continue
        os.rename(file, file.replace("%", ""))
    # sound fields
    nids = mw.col.db.list(
        "select distinct(nid) from cards where id in "+
        ids2str(mw.col.findCards("[sound \%")))
    def repl(match):
        old = match.group(2)
        if "%" not in old:
            return match.group(0)
        return "[sound:%s]" % old.replace("%", "")
    for nid in nids:
        n = mw.col.getNote(nid)
        dirty = False
        for (name, value) in n.items():
            new = re.sub(mw.col.media.regexps[0], repl, value)
            if new != value:
                n[name] = new
                dirty = True
        if dirty:
            n.flush()
    mw.progress.finish()
    showInfo("Success.")

a = QAction(mw)
a.setText("Fix Encoded Media")
mw.form.menuTools.addAction(a)
mw.connect(a, SIGNAL("triggered()"), fix)

########NEW FILE########
__FILENAME__ = disable_update_count
# -*- coding: utf-8 -*-
# Copyright: Damien Elmes <anki@ichi2.net>
# License: GNU GPL, version 3 or later; http://www.gnu.org/copyleft/gpl.html
#
# The count update timer can fire during long-running DB operations in 1.2.8,
# which causes bugs. This plugin disables updating.
#

import sys
from ankiqt import mw
mw.statusView.countTimer.stop()

########NEW FILE########
__FILENAME__ = dumpkeys
# -*- coding: utf-8 -*-
# Copyright: Damien Elmes <anki@ichi2.net>
# License: GNU GPL, version 3 or later; http://www.gnu.org/copyleft/gpl.html

from anki.hooks import wrap
import sys
from aqt.editor import EditorWebView
from aqt.qt import *

def repl(self, evt, _old):
    if evt.key() == Qt.Key_Delete:
        evt = QKeyEvent(QEvent.KeyPress, Qt.Key_Delete, Qt.NoModifier)
        QCoreApplication.postEvent(self, evt)
        return
    _old(self, evt)

EditorWebView.keyPressEvent = wrap(EditorWebView.keyPressEvent, repl, "around")

########NEW FILE########
__FILENAME__ = embedfont
# -*- coding: utf-8 -*-
# Copyright: Damien Elmes <anki@ichi2.net>
# License: GNU GPL, version 3 or later; http://www.gnu.org/copyleft/gpl.html
#

from PyQt4.QtCore import *
from PyQt4.QtGui import *
from ankiqt import mw, ui
import os,re

def onEdit():
    diag = QDialog(mw.app.activeWindow())
    diag.setWindowTitle("Edit Fonts")
    layout = QVBoxLayout(diag)
    diag.setLayout(layout)

    label = QLabel("""\
See <a href="http://ichi2.net/anki/wiki/EmbeddingFonts">the documentation</a>.
<p>
Paste your font CSS below.
""")
    label.setTextInteractionFlags = Qt.TextSelectableByMouse | Qt.LinksAccessibleByMouse

    layout.addWidget(label)

    text = QTextEdit()
    text.setPlainText(mw.deck.getVar("fontCSS") or "")
    layout.addWidget(text)

    box = QDialogButtonBox(QDialogButtonBox.Close)
    layout.addWidget(box)
    box.connect(box, SIGNAL("rejected()"), diag, SLOT("reject()"))

    def onClose():
        mw.deck.setVar("fontCSS", unicode(text.toPlainText()))
        ui.utils.showInfo("""\
Settings saved. Please see the documentation for the next step.""")

    diag.connect(diag, SIGNAL("rejected()"), onClose)

    diag.setMinimumHeight(400)
    diag.setMinimumWidth(500)
    diag.exec_()

# Setup menu entries
menu1 = QAction(mw)
menu1.setText("Embedded Fonts...")
mw.connect(menu1, SIGNAL("triggered()"),onEdit)
mw.mainWin.menuTools.addSeparator()
mw.mainWin.menuTools.addAction(menu1)

########NEW FILE########
__FILENAME__ = embedpad
# -*- coding: utf-8 -*-
# Copyright: Damien Elmes <anki@ichi2.net>
# License: GNU GPL, version 3 or later; http://www.gnu.org/copyleft/gpl.html
#
# This plugin inserts a canvas in your deck for use with AnkiMobile. The
# canvas code is copyright the Tegaki project, and its integration with
# AnkiMobile copyright Shawn Moore - I just wrote a plugin to make using it
# easier.
#
# Shawn's work on this is at http://github.com/sartak/ankimobile-canvas
#
# This code will clobber mobileJS and mobileCSS deck variables, so if you've
# customized them, back up your local content first.
#
# changes by HS 2010-10-26:
#
# Starting with the Embed scratchpad plugin I removed everything that
# is not needed, in my oppion.  So, now you can only draw and clear.
# You cannot redraw you strokes, undo single strokes and so an.  I
# think it is much more responsive now.
#
# changed by Damien 2011-02-05:
#
# - work around serious webkit memory leaks, so using this won't cause lowmem
# crashes after 60-100 cards anymore
# - resize to 90% of width and 40% of screen size and remove retina
# display-specific code
# - don't setup new handlers each time a deck is opened, which lead to slower
# and slower performance
# - add a margin to the clear link to make it difficult to accidentally show
# the answer
# - support the iPad as well
#
# 2011-02-09:
#
# - patch from HS to improve appearance or retina display and display as a
# square
# - modified by Damien to default to the old rectangle which fits on the
# screen in both orientations and isn't biased towards kanji. If you want a
# square display, search for (0) and change it to (1)
#
# 2011-02-16:
#
# - patch from Shawn to remove code for IE and mouse support since this is iOS
# specific
#
# 2012-10-01:
#
# - update for Anki 2.0
#

from aqt.qt import *
from aqt import mw
from aqt.utils import showInfo
import os,re

def onEdit():
    if not mw.reviewer.card:
        return showInfo("Please run this when a card is shown")
    m = mw.reviewer.card.model()
    t = mw.reviewer.card.template()
    if "canvas" in t['qfmt']:
        return
    mw.checkpoint("Embed Scratchpad")
    t['qfmt'] += '\n<br><div id="canvas"></div>' + "\n<script>%s</script>" % JS
    m['css'] += CSS
    mw.col.models.save(m)
    mw.col.setMod()
    mw.reset()
    showInfo("Scratchpad embedded.")

# Setup menu entries
menu1 = QAction(mw)
menu1.setText("Embed Scratchpad")
mw.connect(menu1, SIGNAL("triggered()"), onEdit)
mw.form.menuTools.addSeparator()
mw.form.menuTools.addAction(menu1)

#
# 3rd party code below
#
CSS = """
canvas {
    border: 2px solid black;
}
.cvlink {
    padding: 0.3em 1em;
    border: 1px solid #000;
    background: #aaa;
    border-radius: 5px;
    text-decoration: none;
    color: #000;
}
"""

JS = r'''
/* webcanvas.js */
WebCanvas = function(canvas) {
    this.canvas = canvas;
    this.ctx = canvas.getContext("2d");

    if (document.all) {
        /* For Internet Explorer */
        this.canvas.unselectable = "on";
        this.canvas.onselectstart = function() { return false };
        this.canvas.style.cursor = "default";
    }

    this.buttonPressed = false;

    this.adjustSize();
    this._initListeners();
}

WebCanvas.prototype.adjustSize = function() {
    this.w = 1.0*this.canvas.getAttribute('width');
    this.h = 1.0*this.canvas.getAttribute('height');

    this.lw = 2 // linewidth
    this.scale = 1;
}

WebCanvas.prototype._withHandwritingLine = function() {
    this.ctx.strokeStyle = "rgb(0, 0, 0)";
    this.ctx.lineWidth = this.lw;
    this.ctx.lineCap = "round";
    this.ctx.lineJoin = "round";
}


WebCanvas.prototype._withAxisLine = function() {
    this.ctx.strokeStyle = "rgba(0, 0, 0, 0.1)";
    this.ctx.lineWidth = this.lw;
    this.ctx.lineCap = "butt";
}

WebCanvas.prototype._clear = function() {
    this.canvas.width = this.canvas.width; // clears the canvas
}

WebCanvas.prototype._drawAxis = function() {
    this._withAxisLine();

    this.ctx.beginPath();
    this.ctx.moveTo(this.w/2, 0);
    this.ctx.lineTo(this.w/2, this.h);
    this.ctx.moveTo(0, this.h/2);
    this.ctx.lineTo(this.w, this.h/2);

    this.ctx.stroke();
}

WebCanvas.prototype._initListeners = function() {

    function callback(webcanvas, func) {
        /* Without this trick, "this" in the callback refers to the canvas HTML object.
                          With this trick, "this" refers to the WebCanvas object! */
        return function(event) {
            func.apply(webcanvas, [event]);
        }
    }

    if (this.canvas.attachEvent) {
        this.canvas.attachEvent("onmousemove",      callback(this, this._onMove));
        this.canvas.attachEvent("onmousedown",      callback(this, this._onButtonPressed));
        this.canvas.attachEvent("onmouseup",        callback(this, this._onButtonReleased));
        this.canvas.attachEvent("onmouseout",       callback(this, this._onButtonReleased));
    }
    else if (this.canvas.addEventListener) {
        // Browser sniffing is evil, but I can't figure out a good way to ask in
        // advance if this browser will send touch or mouse events.
        // If we generate both touch and mouse events, the canvas gets confused
        // on iPhone/iTouch with the "revert stroke" command
        if (navigator.userAgent.toLowerCase().indexOf('iphone')!=-1 ||
            navigator.userAgent.toLowerCase().indexOf('ipad')!=-1) {
            // iPhone/iTouch events
            this.canvas.addEventListener("touchstart",  callback(this, this._onButtonPressed),  false);
            this.canvas.addEventListener("touchend",    callback(this, this._onButtonReleased), false);
            this.canvas.addEventListener("touchcancel", callback(this, this._onButtonReleased), false);
            this.canvas.addEventListener("touchmove",   callback(this, this._onMove),           false);

            // Disable page scrolling via dragging inside the canvas
            this.canvas.addEventListener("touchmove", function(e){e.preventDefault();}, false);
        }
        else {
            this.canvas.addEventListener("mousemove",  callback(this, this._onMove),           false);
            this.canvas.addEventListener("mousedown",  callback(this, this._onButtonPressed),  false);
            this.canvas.addEventListener("mouseup",    callback(this, this._onButtonReleased), false);
            this.canvas.addEventListener("mouseout",   callback(this, this._onButtonReleased), false);
        }
    }
    else alert("Your browser does not support interaction.");
}

WebCanvas.prototype._onButtonPressed = function(event) {
    window.event.stopPropagation();
    // this can occur with an iPhone/iTouch when we try to drag two fingers
    // on the canvas, causing a second smaller canvas to appear
    if (this.buttonPressed) return;

    this.buttonPressed = true;

    this.ctx.beginPath();
    this._withHandwritingLine();

    var position = this._getRelativePosition(event);
    this.ctx.moveTo(position.x, position.y);
}

WebCanvas.prototype._onMove = function(event) {

    if (this.buttonPressed) {
        var position = this._getRelativePosition(event);
        this.ctx.lineTo(position.x, position.y);
        this.ctx.stroke();
    }
}

WebCanvas.prototype._onButtonReleased = function(event) {
    window.event.stopPropagation();
    if (this.buttonPressed) {
        this.buttonPressed = false;
    }
}

WebCanvas.prototype._getRelativePosition = function(event) {
    var t = this.canvas;

    var x, y;
    // targetTouches is iPhone/iTouch-specific; it's a list of finger drags
    if (event.targetTouches) {
       var e = event.targetTouches[0];

       x = e.pageX;
       y = e.pageY;
    }
    else {
        x = event.clientX + (window.pageXOffset || 0);
        y = event.clientY + (window.pageYOffset || 0);
    }

    do
        x -= t.offsetLeft + parseInt(t.style.borderLeftWidth || 0),
        y -= t.offsetTop + parseInt(t.style.borderTopWidth || 0);
    while (t = t.offsetParent);

    x *= this.scale;
    y *= this.scale;

    return {"x":x,"y":y};
}

WebCanvas.prototype.clear = function() {
    this._clear();
    this._drawAxis();
}

/* ankimobile.js */
function setupCanvas () {
    var cv;
    // create a reusable canvas to avoid webkit leaks
    if (!document.webcanvas) {
        cv = document.createElement("canvas");
        document.webcanvas = new WebCanvas(cv);
    } else {
        cv = document.webcanvas.canvas;
    }
    var w = window.innerWidth;
    var h = window.innerHeight;
    if (1) {
        // square
        h = w = Math.min(w,h) * 0.7;
    } else {
        // rectangle
        w *= 0.9;
        h *= 0.4;
    }
    cv.setAttribute("width" , w);
    cv.setAttribute("height", h);
    cv.style.width = w;             // set CSS width  (important for Retina display)
    cv.style.height = h;            // set CSS height (important for Retina display)
    document.webcanvas.adjustSize();
    document.webcanvas.clear();
    // put the canvas in the holder
    var holder = document.getElementById("canvas");
    if (!holder) {
        return;
    }
    holder.appendChild(cv);
    // and the clear link
    holder.appendChild(document.createElement("br"));
    var clear = document.createElement("a");
    clear.className = "cvlink";
    clear.appendChild(document.createTextNode("Clear"));
    clear.setAttribute("href", "#");
    clear.onclick = function () { document.webcanvas.clear(); return false; }
    holder.appendChild(clear);
}

setupCanvas();
'''

########NEW FILE########
__FILENAME__ = epwing
from PyQt4.QtCore import *
from PyQt4.QtGui import *
from subprocess import Popen
from ankiqt import mw
import sys

# add my own dictionary lookup tool
def epwingLookup(text):
    Popen(["lookup", text.encode("utf-8")])

def lookupQ():
    mw.initLookup()
    epwingLookup(mw.currentCard.fact['Expression'])

def lookupA():
    mw.initLookup()
    epwingLookup(mw.currentCard.fact['Meaning'])

def lookupS():
    mw.initLookup()
    mw.lookup.selection(epwingLookup)

# remove the standard lookup links
ml = mw.mainWin.menu_Lookup
for i in ("expr", "mean", "as", "es", "esk"):
    ml.removeAction(getattr(mw.mainWin,
                            "actionLookup_" + i))
# add custom links
q = QAction(mw)
q.setText("..question")
q.setShortcut(_("Ctrl+1"))
ml.addAction(q)
mw.connect(q, SIGNAL("triggered()"), lookupQ)
a = QAction(mw)
a.setText("..answer")
a.setShortcut(_("Ctrl+2"))
ml.addAction(a)
mw.connect(a, SIGNAL("triggered()"), lookupA)
s = QAction(mw)
s.setText("..selection")
s.setShortcut(_("Ctrl+3"))
ml.addAction(s)
mw.connect(s, SIGNAL("triggered()"), lookupS)

mw.registerPlugin("Custom Dictionary Lookup", 5)

########NEW FILE########
__FILENAME__ = fixassert
# -*- coding: utf-8 -*-
# Copyright: Damien Elmes <anki@ichi2.net>
# License: GNU GPL, version 3 or later; http://www.gnu.org/copyleft/gpl.html
#

from aqt import mw
from aqt.qt import *
from aqt.utils import showInfo

def fix():
    mw.col.modSchema()
    mw.col.db.execute(
        "update cards set odue = 0 where (type = 1 or queue = 2) and not odid")
    showInfo("Fixed. If you get errors after running this, please let me know.")

a = QAction(mw)
a.setText("Fix Assertion Error")
mw.form.menuTools.addAction(a)
mw.connect(a, SIGNAL("triggered()"), fix)

########NEW FILE########
__FILENAME__ = fixdropbox
# -*- coding: utf-8 -*-
# Copyright: Damien Elmes <anki@ichi2.net>
# License: GNU GPL, version 3 or later; http://www.gnu.org/copyleft/gpl.html

from ankiqt import mw

def fixedDropboxFolder():
    folder = orig()
    # Dropbox changed the folder name from "My Dropbox" to "Dropbox".
    folder = folder.replace("My Dropbox", "Dropbox")
    # If you want to use a custom location, uncomment the following line
    # and edit it to match the actual path. Note that you need to use two
    # backslash characters instead of one.
    #return "c:\\users\\bob\\documents\\dropbox"
    return folder

orig = mw.dropboxFolder
mw.dropboxFolder = fixedDropboxFolder


########NEW FILE########
__FILENAME__ = fixdue
# -*- coding: utf-8 -*-
# Copyright: Damien Elmes <anki@ichi2.net>
# License: GNU GPL, version 3 or later; http://www.gnu.org/copyleft/gpl.html
#
# Fix floast in the DB which have been mistakenly turned into strings due to
# string concatenation.
#

from ankiqt import mw
from ankiqt import ui
from PyQt4.QtCore import *
from PyQt4.QtGui import *

def onFix():
    for col in ("created", "due", "combinedDue", "spaceUntil"):
        mw.deck.s.execute(
            "update cards set %s = cast (%s as float)" % (
            col, col))
    mw.deck.setModified()
    ui.utils.showInfo("Fixed.")

act = QAction(mw)
act.setText("Fix Floats")
mw.connect(act, SIGNAL("triggered()"), onFix)

mw.mainWin.menuTools.addAction(act)

########NEW FILE########
__FILENAME__ = fixmark
# -*- coding: utf-8 -*-
# Copyright: Damien Elmes <anki@ichi2.net>
# License: GNU GPL, version 3 or later; http://www.gnu.org/copyleft/gpl.html
#
# Fix the mark command while reviewing in beta5. Please remove for future
# betas.
#

from aqt import mw
from aqt.reviewer import Reviewer
from anki.hooks import wrap
def fixMark(self):
    self.card.note().flush()
Reviewer.onMark = wrap(Reviewer.onMark, fixMark)

########NEW FILE########
__FILENAME__ = fixorder
# -*- coding: utf-8 -*-
# Copyright: Damien Elmes <anki@ichi2.net>
# License: GNU GPL, version 3 or later; http://www.gnu.org/copyleft/gpl.html
#
# Fix the ordering of cards so that different templates are shown one after
# another if the minimum spacing is 0. You only need this if a previous bug in
# Anki (now fixed) didn't set the order right.
#

from ankiqt import mw
from ankiqt import ui
from PyQt4.QtCore import *
from PyQt4.QtGui import *

def onFix():
    mw.deck.s.execute("""
update cards set created = (select created from facts
where cards.factId = facts.id) + cards.ordinal * 0.000001""")
    mw.deck.s.execute("""
update cards set due = created, combinedDue =
max(created,spaceUntil) where type = 2""")
    ui.utils.showInfo("Ordering fixed.")

act = QAction(mw)
act.setText("Fix Ordering")
mw.connect(act, SIGNAL("triggered()"), onFix)

mw.mainWin.menuTools.addAction(act)

########NEW FILE########
__FILENAME__ = fullscreen
# -*- coding: utf-8 -*-
# Copyright: Damien Elmes <anki@ichi2.net>
# License: GNU GPL, version 3 or later; http://www.gnu.org/copyleft/gpl.html
#
# This plugin adds the ability to toggle full screen mode. It adds an item to
# the tools menu.
#

from PyQt4.QtGui import *
from PyQt4.QtCore import *
from ankiqt import mw

def onFullScreen():
    mw.setWindowState(mw.windowState() ^ Qt.WindowFullScreen)

a = QAction(mw)
a.setText("Toggle Full Screen")
a.setShortcut("F11")
mw.mainWin.menuTools.addAction(a)
mw.connect(a, SIGNAL("triggered()"), onFullScreen)

########NEW FILE########
__FILENAME__ = furigana
# -*- coding: utf-8 -*-
# Copyright: Damien Elmes <anki@ichi2.net>
# License: GNU GPL, version 3 or later; http://www.gnu.org/copyleft/gpl.html
#
# This plugin is a hack that overrides the default question/answer format for
# Japanese models to show furigana above the kanji. It will only work on
# Japanese which has been added after Anki 0.9.9.8.
#
# Version 2: use CSS. Much more robust, and a candidate for inclusion in Anki
# in the future.

import re
from ankiqt import mw
from anki.hooks import addHook
from anki.utils import hexifyID

def filterAnswer(txt):
    if (not "Japanese" in mw.currentCard.fact.model.tags and
        not "Mandarin" in mw.currentCard.fact.model.tags and
        not "Cantonese" in mw.currentCard.fact.model.tags):
        return txt
    if not "[" in mw.currentCard.fact.get('Reading', ""):
        return txt
    # get the reading field
    read = [x.id for x in mw.currentCard.fact.model.fieldModels
            if x.name == "Reading"]
    if not read:
        return txt
    read = '<span class="fm%s">' % hexifyID(read[0])
    # replace
    def repl(match):
        return read + rubify(match.group(1)) + "</span>"
    txt = re.sub("%s(.*?)</span>" % read, repl, txt)
    return txt

def rubify(txt):
    expr = '<span class="fm%s">' % hexifyID(
        [x.id for x in mw.currentCard.fact.model.fieldModels
         if x.name == "Expression"][0])
    read = '<span class="fm%s">' % hexifyID(
        [x.id for x in mw.currentCard.fact.model.fieldModels
         if x.name == "Reading"][0])
    txt = re.sub("([^ >]+?)\[(.+?)\]", """\
<span class="ezRuby" title="\\2">\\1</span>""", txt)
    txt = re.sub("> +", ">", txt)
    txt = re.sub(" +<", "<", txt)
    return txt

def addCss():
    # based on http://welkin.s60.xrea.com/css_labo/Ruby-CSS_DEMO3.html
    mw.bodyView.buffer += """
<style>
/* Ruby Base */
html>/* */body .ezRuby {
  line-height: 1;
  text-align: center;
  white-space: nowrap;
  vertical-align: baseline;
  margin: 0;
  padding: 0;
  border: none;
  display: inline-block;
}

/* Ruby Text */
html>/* */body .ezRuby:before {
  font-size: 0.64em;
  font-weight: normal;
  line-height: 1.2;
  text-decoration: none;
  display: block;
  content: attr(title);
}

/* Adapt to your site's CSS */
html>/* */body .ezRuby:hover{
  color: #000000;
  background-color: #FFFFCC;
}

html>/* */body .ezRuby:hover:before{
  background-color: #FFCC66;
}
</style>"""

addHook('drawAnswer', filterAnswer)
addHook('preFlushHook', addCss)

########NEW FILE########
__FILENAME__ = graphcolours
# -*- coding: utf-8 -*-
# Copyright: Damien Elmes <anki@ichi2.net>
# License: GNU GPL, version 3 or later; http://www.gnu.org/copyleft/gpl.html
#
# This plugin lets you change the graph colours.
#

from ankiqt import mw
from anki import graphs as g
mw.registerPlugin("Graph Colours", 11)

# These are the standard graph colours. Uncomment the lines you want to
# customize the colours.
#
# g.dueYoungC = "#ffb380"
# g.dueMatureC = "#ff5555"
# g.dueCumulC = "#ff8080"
#
# g.reviewNewC = "#80b3ff"
# g.reviewYoungC = "#5555ff"
# g.reviewMatureC = "#0f5aff"
# g.reviewTimeC = "#0fcaff"
#
# g.easesNewC = "#80b3ff"
# g.easesYoungC = "#5555ff"
# g.easesMatureC = "#0f5aff"
#
# g.addedC = "#b3ff80"
# g.firstC = "#b380ff"
# g.intervC = "#80e5ff"

########NEW FILE########
__FILENAME__ = hardest
# -*- coding: utf-8 -*-
# Copyright: Damien Elmes <anki@ichi2.net>
# License: GNU GPL, version 3 or later; http://www.gnu.org/copyleft/gpl.html
#
# This simple plugin shows you the hardest cards in the defined time (default
# last 30 minutes).
#

from PyQt4.QtGui import *
from PyQt4.QtCore import *
from ankiqt import mw
import time

# last 30 minutes
MINUTES = 30
# limit to maximum of 10 cards
MAXCARDS = 10

def onHardest():
    data = mw.deck.s.all("""
select question, cnt from (
select cardId, count() as cnt from reviewHistory where time > :t
and ease = 1 group by cardId), cards where cardId = id order by cnt desc limit :d""",
                         t=time.time() - 60*MINUTES, d=MAXCARDS)

    s = "<h1>Hardest Cards</h1><table>"
    for (q, cnt) in data:
        s += "<tr><td>%s</td><td>failed %d times</td></tr>" % (q, cnt)
    # show dialog
    diag = QDialog(mw.app.activeWindow())
    diag.setWindowTitle("Anki")
    layout = QVBoxLayout(diag)
    diag.setLayout(layout)
    text = QTextEdit()
    text.setReadOnly(True)
    text.setHtml(s)
    layout.addWidget(text)
    box = QDialogButtonBox(QDialogButtonBox.Close)
    layout.addWidget(box)
    mw.connect(box, SIGNAL("rejected()"), diag, SLOT("reject()"))
    diag.setMinimumHeight(400)
    diag.setMinimumWidth(500)
    diag.exec_()

a = QAction(mw)
a.setText("Show Hardest Cards")
mw.mainWin.menuTools.addAction(a)
mw.connect(a, SIGNAL("triggered()"), onHardest)

########NEW FILE########
__FILENAME__ = bulkreading
# -*- coding: utf-8 -*-
# Copyright: Damien Elmes <anki@ichi2.net>
# License: GNU GPL, version 3 or later; http://www.gnu.org/copyleft/gpl.html
#
# Bulk update of readings.
#

from PyQt4.QtCore import *
from PyQt4.QtGui import *
from anki.hooks import addHook
from japanese.reading import mecab, srcFields, dstFields
from aqt import mw

# Bulk updates
##########################################################################

def regenerateReadings(nids):
    global mecab
    mw.checkpoint("Bulk-add Readings")
    mw.progress.start()
    for nid in nids:
        note = mw.col.getNote(nid)
        if "japanese" not in note.model()['name'].lower():
            continue
        src = None
        for fld in srcFields:
            if fld in note:
                src = fld
                break
        if not src:
            # no src field
            continue
        dst = None
        for fld in dstFields:
            if fld in note:
                dst = fld
                break
        if not dst:
            # no dst field
            continue
        if note[dst]:
            # already contains data, skip
            continue
        srcTxt = mw.col.media.strip(note[src])
        if not srcTxt.strip():
            continue
        try:
            note[dst] = mecab.reading(srcTxt)
        except Exception, e:
            mecab = None
            raise
        note.flush()
    mw.progress.finish()
    mw.reset()

def setupMenu(browser):
    a = QAction("Bulk-add Readings", browser)
    browser.connect(a, SIGNAL("triggered()"), lambda e=browser: onRegenerate(e))
    browser.form.menuEdit.addSeparator()
    browser.form.menuEdit.addAction(a)

def onRegenerate(browser):
    regenerateReadings(browser.selectedNotes())

addHook("browser.setupMenus", setupMenu)

########NEW FILE########
__FILENAME__ = lookup
# -*- coding: utf-8 -*-
# Copyright: Damien Elmes <anki@ichi2.net>
# License: GNU GPL, version 3 or later; http://www.gnu.org/copyleft/gpl.html
#
# Dictionary lookup support.
#

import urllib, re
from anki.hooks import addHook
from aqt import mw
from aqt.qt import *
from aqt.utils import showInfo

class Lookup(object):

    def __init__(self):
        pass

    def selection(self, function):
        "Get the selected text and look it up with FUNCTION."
        # lazily acquire selection by copying it into clipboard
        mw.web.triggerPageAction(QWebPage.Copy)
        text = mw.app.clipboard().mimeData().text()
        text = text.strip()
        if not text:
            showInfo(_("Empty selection."))
            return
        if "\n" in text:
            showInfo(_("Can't look up a selection with a newline."))
            return
        function(text)

    def edictKanji(self, text):
        self.edict(text, True)

    def edict(self, text, kanji=False):
        "Look up TEXT with edict."
        if kanji:
            x="M"
        else:
            x="U"
        baseUrl="http://www.csse.monash.edu.au/~jwb/cgi-bin/wwwjdic.cgi?1M" + x
        if self.isJapaneseText(text):
            baseUrl += "J"
        else:
            baseUrl += "E"
        url = baseUrl + urllib.quote(text.encode("utf-8"))
        qurl = QUrl()
        qurl.setEncodedUrl(url)
        QDesktopServices.openUrl(qurl)

    def jishoKanji(self, text):
        self.jisho(text, True)

    def jisho(self, text, kanji=False):
        "Look up TEXT with jisho."
        if kanji:
            baseUrl="http://jisho.org/kanji/details/"
        else:
            baseUrl="http://jisho.org/words?"
            if self.isJapaneseText(text):
                baseUrl+="jap="
            else:
                baseUrl+="eng="
        url = baseUrl + urllib.quote(text.encode("utf-8"))
        qurl = QUrl()
        qurl.setEncodedUrl(url)
        QDesktopServices.openUrl(qurl)

    def alc(self, text):
        "Look up TEXT with ALC."
        newText = urllib.quote(text.encode("utf-8"))
        url = (
            "http://eow.alc.co.jp/" +
            newText +
            "/UTF-8/?ref=sa")
        qurl = QUrl()
        qurl.setEncodedUrl(url)
        QDesktopServices.openUrl(qurl)

    def isJapaneseText(self, text):
        "True if 70% of text is a Japanese character."
        total = len(text)
        if total == 0:
            return True
        jp = 0
        en = 0
        for c in text:
            if ord(c) >= 0x2E00 and ord(c) <= 0x9FFF:
                jp += 1
            if re.match("[A-Za-z]", c):
                en += 1
        if not jp:
            return False
        return ((jp + 1) / float(en + 1)) >= 1.0

def initLookup():
    if not getattr(mw, "lookup", None):
        mw.lookup = Lookup()

def _field(name):
    try:
        return mw.reviewer.card.note()[name]
    except:
        return

def onLookupExpression(name="Expression"):
    initLookup()
    txt = _field(name)
    if not txt:
        return showInfo("No %s in current note." % name)
    mw.lookup.alc(txt)

def onLookupMeaning():
    onLookupExpression("Meaning")

def onLookupEdictSelection():
    initLookup()
    mw.lookup.selection(mw.lookup.edict)

def onLookupEdictKanjiSelection():
    initLookup()
    mw.lookup.selection(mw.lookup.edictKanji)

def onLookupJishoSelection():
    initLookup()
    mw.lookup.selection(mw.lookup.jisho)

def onLookupJishoKanjiSelection():
    initLookup()
    mw.lookup.selection(mw.lookup.jishoKanji)

def onLookupAlcSelection():
    initLookup()
    mw.lookup.selection(mw.lookup.alc)

def createMenu():
    ml = QMenu()
    ml.setTitle("Lookup")
    mw.form.menuTools.addAction(ml.menuAction())
    # make it easier for other plugins to add to the menu
    mw.form.menuLookup = ml
    # add actions
    a = QAction(mw)
    a.setText("...expression on alc")
    a.setShortcut("Ctrl+1")
    ml.addAction(a)
    mw.connect(a, SIGNAL("triggered()"), onLookupExpression)
    a = QAction(mw)
    a.setText("...meaning on alc")
    a.setShortcut("Ctrl+2")
    ml.addAction(a)
    mw.connect(a, SIGNAL("triggered()"), onLookupMeaning)
    a = QAction(mw)
    a.setText("...selection on alc")
    a.setShortcut("Ctrl+3")
    ml.addAction(a)
    ml.addSeparator()
    mw.connect(a, SIGNAL("triggered()"), onLookupAlcSelection)
    a = QAction(mw)
    a.setText("...word selection on edict")
    a.setShortcut("Ctrl+4")
    ml.addAction(a)
    mw.connect(a, SIGNAL("triggered()"), onLookupEdictSelection)
    a = QAction(mw)
    a.setText("...kanji selection on edict")
    a.setShortcut("Ctrl+5")
    ml.addAction(a)
    mw.connect(a, SIGNAL("triggered()"), onLookupEdictKanjiSelection)
    ml.addSeparator()
    a = QAction(mw)
    a.setText("...word selection on jisho")
    a.setShortcut("Ctrl+6")
    ml.addAction(a)
    mw.connect(a, SIGNAL("triggered()"), onLookupJishoSelection)
    a = QAction(mw)
    a.setText("...kanji selection on jisho")
    a.setShortcut("Ctrl+7")
    ml.addAction(a)
    mw.connect(a, SIGNAL("triggered()"), onLookupJishoKanjiSelection)

# def disableMenu():
#     mw.mainWin.menuLookup.setEnabled(False)

# def enableMenu():
#     mw.mainWin.menuLookup.setEnabled(True)

# addHook('disableCardMenuItems', disableMenu)
# addHook('enableCardMenuItems', enableMenu)

createMenu()

########NEW FILE########
__FILENAME__ = model
# -*- coding: utf-8 -*-
# Copyright: Damien Elmes <anki@ichi2.net>
# License: GNU GPL, version 3 or later; http://www.gnu.org/copyleft/gpl.html
#
# Standard Japanese model.
#

import anki.stdmodels

def addJapaneseModel(col):
    mm = col.models
    m = mm.new(_("Japanese (recognition)"))
    fm = mm.newField(_("Expression"))
    mm.addField(m, fm)
    fm = mm.newField(_("Meaning"))
    mm.addField(m, fm)
    fm = mm.newField(_("Reading"))
    mm.addField(m, fm)
    t = mm.newTemplate(_("Recognition"))
    # css
    m['css'] += u"""\
.jp { font-size: 30px }
.win .jp { font-family: "MS Mincho", "ＭＳ 明朝"; }
.mac .jp { font-family: "Hiragino Mincho Pro", "ヒラギノ明朝 Pro"; }
.linux .jp { font-family: "Kochi Mincho", "東風明朝"; }
.mobile .jp { font-family: "Hiragino Mincho ProN"; }"""
    # recognition card
    t['qfmt'] = "<div class=jp> {{Expression}} </div>"
    t['afmt'] = """{{FrontSide}}\n\n<hr id=answer>\n\n\
<div class=jp> {{furigana:Reading}} </div><br>\n\
{{Meaning}}"""
    mm.addTemplate(m, t)
    mm.add(m)
    return m

def addDoubleJapaneseModel(col):
    mm = col.models
    m = addJapaneseModel(col)
    m['name'] = "Japanese (recognition&recall)"
    rev = mm.newTemplate(_("Recall"))
    rev['qfmt'] = "{{Meaning}}"
    rev['afmt'] = """{{FrontSide}}

<hr id=answer>

<div class=jp> {{Expression}} </div>
<div class=jp> {{furigana:Reading}} </div>"""
    mm.addTemplate(m, rev)
    return m

def addOptionalJapaneseModel(col):
    mm = col.models
    m = addDoubleJapaneseModel(col)
    m['name'] = "Japanese (optional recall)"
    rev = m['tmpls'][1]
    rev['qfmt'] = "{{#Add Recall}}\n"+rev['qfmt']+"\n{{/Add Recall}}"
    fm = mm.newField("Add Recall")
    mm.addField(m, fm)
    return m

anki.stdmodels.models.append((_("Japanese (recognition)"), addJapaneseModel))
anki.stdmodels.models.append((_("Japanese (recognition&recall)"), addDoubleJapaneseModel))
anki.stdmodels.models.append((_("Japanese (optional recall)"), addOptionalJapaneseModel))

########NEW FILE########
__FILENAME__ = reading
# -*- coding: utf-8 -*-
# Copyright: Damien Elmes <anki@ichi2.net>
# License: GNU GPL, version 3 or later; http://www.gnu.org/copyleft/gpl.html
#
# Automatic reading generation with kakasi and mecab.
# See http://ichi2.net/anki/wiki/JapaneseSupport
#

import sys, os, platform, re, subprocess
from anki.utils import stripHTML, isWin, isMac
from anki.hooks import addHook

srcFields = ['Expression']
dstFields = ['Reading']

kakasiArgs = ["-isjis", "-osjis", "-u", "-JH", "-KH"]
mecabArgs = ['--node-format=%m[%f[7]] ', '--eos-format=\n',
            '--unk-format=%m[] ']

def escapeText(text):
    # strip characters that trip up kakasi/mecab
    text = text.replace("\n", " ")
    text = text.replace(u'\uff5e', "~")
    text = re.sub("<br( /)?>", "---newline---", text)
    text = stripHTML(text)
    text = text.replace("---newline---", "<br>")
    return text

if sys.platform == "win32":
    si = subprocess.STARTUPINFO()
    try:
        si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    except:
        si.dwFlags |= subprocess._subprocess.STARTF_USESHOWWINDOW
else:
    si = None

# Mecab
##########################################################################

def mungeForPlatform(popen):
    if isWin:
        popen = [os.path.normpath(x) for x in popen]
        popen[0] += ".exe"
    elif not isMac:
        popen[0] += ".lin"
    return popen

class MecabController(object):

    def __init__(self):
        self.mecab = None

    def setup(self):
        base = "../../addons/japanese/support/"
        self.mecabCmd = mungeForPlatform(
            [base + "mecab"] + mecabArgs + [
                '-d', base, '-r', base + "mecabrc"])
        os.environ['DYLD_LIBRARY_PATH'] = base
        os.environ['LD_LIBRARY_PATH'] = base
        if not isWin:
            os.chmod(self.mecabCmd[0], 0755)

    def ensureOpen(self):
        if not self.mecab:
            self.setup()
            try:
                self.mecab = subprocess.Popen(
                    self.mecabCmd, bufsize=-1, stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                    startupinfo=si)
            except OSError:
                raise Exception("Please ensure your Linux system has 32 bit binary support.")

    def reading(self, expr):
        self.ensureOpen()
        expr = escapeText(expr)
        self.mecab.stdin.write(expr.encode("euc-jp", "ignore")+'\n')
        self.mecab.stdin.flush()
        expr = unicode(self.mecab.stdout.readline().rstrip('\r\n'), "euc-jp")
        out = []
        for node in expr.split(" "):
            if not node:
                break
            (kanji, reading) = re.match("(.+)\[(.*)\]", node).groups()
            # hiragana, punctuation, not japanese, or lacking a reading
            if kanji == reading or not reading:
                out.append(kanji)
                continue
            # katakana
            if kanji == kakasi.reading(reading):
                out.append(kanji)
                continue
            # convert to hiragana
            reading = kakasi.reading(reading)
            # ended up the same
            if reading == kanji:
                out.append(kanji)
                continue
            # don't add readings of numbers
            if kanji in u"一二三四五六七八九十０１２３４５６７８９":
                out.append(kanji)
                continue
            # strip matching characters and beginning and end of reading and kanji
            # reading should always be at least as long as the kanji
            placeL = 0
            placeR = 0
            for i in range(1,len(kanji)):
                if kanji[-i] != reading[-i]:
                    break
                placeR = i
            for i in range(0,len(kanji)-1):
                if kanji[i] != reading[i]:
                    break
                placeL = i+1
            if placeL == 0:
                if placeR == 0:
                    out.append(" %s[%s]" % (kanji, reading))
                else:
                    out.append(" %s[%s]%s" % (
                        kanji[:-placeR], reading[:-placeR], reading[-placeR:]))
            else:
                if placeR == 0:
                    out.append("%s %s[%s]" % (
                        reading[:placeL], kanji[placeL:], reading[placeL:]))
                else:
                    out.append("%s %s[%s]%s" % (
                        reading[:placeL], kanji[placeL:-placeR],
                        reading[placeL:-placeR], reading[-placeR:]))
        fin = u""
        for c, s in enumerate(out):
            if c < len(out) - 1 and re.match("^[A-Za-z0-9]+$", out[c+1]):
                s += " "
            fin += s
        return fin.strip().replace("< br>", "<br>")

# Kakasi
##########################################################################

class KakasiController(object):

    def __init__(self):
        self.kakasi = None

    def setup(self):
        base = "../../addons/japanese/support/"
        self.kakasiCmd = mungeForPlatform(
            [base + "kakasi"] + kakasiArgs)
        os.environ['ITAIJIDICT'] = base + "itaijidict"
        os.environ['KANWADICT'] = base + "kanwadict"
        if not isWin:
            os.chmod(self.kakasiCmd[0], 0755)

    def ensureOpen(self):
        if not self.kakasi:
            self.setup()
            try:
                self.kakasi = subprocess.Popen(
                    self.kakasiCmd, bufsize=-1, stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                    startupinfo=si)
            except OSError:
                raise Exception("Please install kakasi")

    def reading(self, expr):
        self.ensureOpen()
        expr = escapeText(expr)
        self.kakasi.stdin.write(expr.encode("sjis", "ignore")+'\n')
        self.kakasi.stdin.flush()
        res = unicode(self.kakasi.stdout.readline().rstrip('\r\n'), "sjis")
        return res

# Focus lost hook
##########################################################################

def onFocusLost(flag, n, fidx):
    global mecab
    from aqt import mw
    if not mecab:
        return flag
    src = None
    dst = None
    # japanese model?
    if "japanese" not in n.model()['name'].lower():
        return flag
    # have src and dst fields?
    for c, name in enumerate(mw.col.models.fieldNames(n.model())):
        for f in srcFields:
            if name == f:
                src = f
                srcIdx = c
        for f in dstFields:
            if name == f:
                dst = f
    if not src or not dst:
        return flag
    # dst field already filled?
    if n[dst]:
        return flag
    # event coming from src field?
    if fidx != srcIdx:
        return flag
    # grab source text
    srcTxt = mw.col.media.strip(n[src])
    if not srcTxt:
        return flag
    # update field
    try:
        n[dst] = mecab.reading(srcTxt)
    except Exception, e:
        mecab = None
        raise
    return True

# Init
##########################################################################

kakasi = KakasiController()
mecab = MecabController()

addHook('editFocusLost', onFocusLost)

# Tests
##########################################################################

if __name__ == "__main__":
    expr = u"カリン、自分でまいた種は自分で刈り取れ"
    print mecab.reading(expr).encode("utf-8")
    expr = u"昨日、林檎を2個買った。"
    print mecab.reading(expr).encode("utf-8")
    expr = u"真莉、大好きだよん＾＾"
    print mecab.reading(expr).encode("utf-8")
    expr = u"彼２０００万も使った。"
    print mecab.reading(expr).encode("utf-8")
    expr = u"彼二千三百六十円も使った。"
    print mecab.reading(expr).encode("utf-8")
    expr = u"千葉"
    print mecab.reading(expr).encode("utf-8")

########NEW FILE########
__FILENAME__ = stats
# -*- coding: utf-8 -*-
# Copyright: Damien Elmes <anki@ichi2.net>
# Used/unused kanji list code originally by 'LaC'
# License: GNU GPL, version 3 or later; http://www.gnu.org/copyleft/gpl.html

import unicodedata
from anki.hooks import addHook
from anki.utils import ids2str, splitFields
from aqt import mw
from aqt.webview import AnkiWebView
from aqt.qt import *
from aqt.utils import restoreGeom, saveGeom

# look for kanji in these fields
srcFields = ["Expression", "Kanji"]

def isKanji(unichar):
    try:
        return unicodedata.name(unichar).find('CJK UNIFIED IDEOGRAPH') >= 0
    except ValueError:
        # a control character
        return False

class KanjiStats(object):

    def __init__(self, col, wholeCollection):
        self.col = col
        if wholeCollection:
            self.lim = ""
        else:
            self.lim = " and c.did in %s" % ids2str(self.col.decks.active())
        self._gradeHash = dict()
        for (name, chars), grade in zip(self.kanjiGrades,
                                        xrange(len(self.kanjiGrades))):
            for c in chars:
                self._gradeHash[c] = grade

    def kanjiGrade(self, unichar):
        return self._gradeHash.get(unichar, 0)

    # FIXME: as it's html, the width doesn't matter
    def kanjiCountStr(self, gradename, count, total=0, width=0):
        d = {'count': self.rjustfig(count, width), 'gradename': gradename}
        if total:
            d['total'] = self.rjustfig(total, width)
            d['percent'] = float(count)/total*100
            return _("%(gradename)s: %(count)s of %(total)s (%(percent)0.1f%%).") % d
        else:
            return _("%(count)s %(gradename)s kanji.") % d

    def rjustfig(self, n, width):
        n = unicode(n)
        return n + "&nbsp;" * (width - len(n))

    def genKanjiSets(self):
        self.kanjiSets = [set([]) for g in self.kanjiGrades]
        chars = set()
        for m in self.col.models.all():
            if "japanese" not in m['name'].lower():
                continue
            idxs = []
            for c, name in enumerate(self.col.models.fieldNames(m)):
                for f in srcFields:
                    if name == f:
                        idxs.append(c)
            for row in self.col.db.execute("""
select flds from notes where id in (
select n.id from cards c, notes n
where c.nid = n.id and mid = ? and c.queue > 0
%s) """ % self.lim, m['id']):
                flds = splitFields(row[0])
                for idx in idxs:
                    chars.update(flds[idx])
        for c in chars:
            if isKanji(c):
                self.kanjiSets[self.kanjiGrade(c)].add(c)

    def report(self):
        self.genKanjiSets()
        counts = [(name, len(found), len(all)) \
                  for (name, all), found in zip(self.kanjiGrades, self.kanjiSets)]
        out = ((_("<h1>Kanji statistics</h1>The seen cards in this %s "
                 "contain:") % (self.lim and "deck" or "collection")) +
               "<ul>" +
               # total kanji
               _("<li>%d total unique kanji.</li>") %
               sum([c[1] for c in counts]) +
               # total joyo
               "<li>%s</li>" % self.kanjiCountStr(
            u'Old jouyou',sum([c[1] for c in counts[1:8]]),
            sum([c[2] for c in counts[1:8]])) +
               # total new joyo
               "<li>%s</li>" % self.kanjiCountStr(*counts[8]) +
               # total jinmei (reg)
               "<li>%s</li>" % self.kanjiCountStr(*counts[9]) +
               # total jinmei (var)
               "<li>%s</li>" % self.kanjiCountStr(*counts[10]) +
               # total non-joyo
               "<li>%s</li>" % self.kanjiCountStr(*counts[0]))

        out += "</ul><p/>" + _(u"Jouyou levels:") + "<p/><ul>"
        L = ["<li>" + self.kanjiCountStr(c[0],c[1],c[2], width=3) + "</li>"
             for c in counts[1:8]]
        out += "".join(L)
        out += "</ul>"
        return out

    def missingReport(self, check=None):
        if not check:
            check = lambda x, y: x not in y
            out = _("<h1>Missing</h1>")
        else:
            out = _("<h1>Seen</h1>")
        for grade in range(1, len(self.kanjiGrades)):
            missing = "".join(self.missingInGrade(grade, check))
            if not missing:
                continue
            out += "<h2>" + self.kanjiGrades[grade][0] + "</h2>"
            out += "<font size=+2>"
            out += self.mkEdict(missing)
            out += "</font>"
        return out + "<br/>"

    def mkEdict(self, kanji):
        out = "<font size=+2>"
        while 1:
            if not kanji:
                out += "</font>"
                return out
            # edict will take up to about 10 kanji at once
            out += self.edictKanjiLink(kanji[0:10])
            kanji = kanji[10:]

    def seenReport(self):
        return self.missingReport(lambda x, y: x in y)

    def nonJouyouReport(self):
        out = _("<h1>Non-Jouyou</h1>")
        out += self.mkEdict("".join(self.kanjiSets[0]))
        return out + "<br/>"

    def edictKanjiLink(self, kanji):
        base="http://www.csse.monash.edu.au/~jwb/cgi-bin/wwwjdic.cgi?1MMJ"
        url=base + kanji
        return '<a href="%s">%s</a>' % (url, kanji)

    def missingInGrade(self, gradeNum, check):
        existingKanji = self.kanjiSets[gradeNum]
        totalKanji = self.kanjiGrades[gradeNum][1]
        return [k for k in totalKanji if check(k, existingKanji)]

    kanjiGrades = [
        (u'non-jouyou', ''),
        (u'Grade 1', u'一右雨円王音下火花貝学気休玉金九空月犬見五口校左三山四子糸字耳七車手十出女小上森人水正生青石赤先千川早草足村大男竹中虫町天田土二日入年白八百文本名木目夕立力林六'),
        (u'Grade 2', u'引羽雲園遠黄何夏家科歌画会回海絵外角楽活間丸岩顔帰汽記弓牛魚京強教近兄形計元原言古戸午後語交光公工広考行高合国黒今才細作算姉市思止紙寺時自室社弱首秋週春書少場色食心新親図数星晴声西切雪線船前組走多太体台谷知地池茶昼朝長鳥直通弟店点電冬刀東当答頭同道読内南肉馬買売麦半番父風分聞米歩母方北妹毎万明鳴毛門夜野矢友曜用来理里話'),
        (u'Grade 3', u'悪安暗委意医育員飲院運泳駅央横屋温化荷界開階寒感漢館岸期起客宮急球究級去橋業局曲銀区苦具君係軽決血研県庫湖向幸港号根祭坂皿仕使始指死詩歯事持次式実写者主取守酒受州拾終習集住重宿所暑助勝商昭消章乗植深申真神身進世整昔全想相送息速族他打対待代第題炭短談着柱注丁帳調追定庭笛鉄転登都度島投湯等豆動童農波配倍箱畑発反板悲皮美鼻筆氷表病秒品負部服福物平返勉放味命面問役薬油有由遊予様洋羊葉陽落流旅両緑礼列練路和'),
        (u'Grade 4', u'愛案以位囲胃衣印栄英塩億加果課貨芽改械害街各覚完官管観関願喜器希旗機季紀議救求泣給挙漁競共協鏡極訓軍郡型径景芸欠結健建験固候功好康航告差最菜材昨刷察札殺参散産残司史士氏試児治辞失借種周祝順初唱松焼照省笑象賞信臣成清静席積折節説戦浅選然倉巣争側束続卒孫帯隊達単置仲貯兆腸低停底的典伝徒努灯働堂得特毒熱念敗梅博飯費飛必標票不付夫府副粉兵別変辺便包法望牧末満未脈民無約勇要養浴利陸料良量輪類令例冷歴連労老録'),
        (u'Grade 5', u'圧易移因営永衛液益演往応恩仮価可河過賀解快格確額刊幹慣眼基寄規技義逆久旧居許境興均禁句群経潔件券検険減現限個故護効厚構耕講鉱混査再妻採災際在罪財桜雑賛酸師志支枝資飼似示識質舎謝授修術述準序承招証常情条状織職制勢性政精製税績責接設絶舌銭祖素総像増造則測属損態貸退団断築張提程敵適統導銅徳独任燃能破判版犯比肥非備俵評貧婦富布武復複仏編弁保墓報豊暴貿防務夢迷綿輸余預容率略留領'),
        (u'Grade 6', u'異遺域宇映延沿我灰拡閣革割株巻干看簡危揮机貴疑吸供胸郷勤筋敬系警劇激穴憲権絹厳源呼己誤后孝皇紅鋼降刻穀骨困砂座済裁策冊蚕姿私至視詞誌磁射捨尺若樹収宗就衆従縦縮熟純処署諸除傷将障城蒸針仁垂推寸盛聖誠宣専泉洗染善創奏層操窓装臓蔵存尊宅担探誕暖段値宙忠著庁潮頂賃痛展党糖討届難乳認納脳派俳拝背肺班晩否批秘腹奮並閉陛片補暮宝訪亡忘棒枚幕密盟模訳優郵幼欲翌乱卵覧裏律臨朗論'),
        (u'JuniorHS', u'亜哀握扱依偉威尉慰為維緯違井壱逸稲芋姻陰隠韻渦浦影詠鋭疫悦謁越閲宴援炎煙猿縁鉛汚凹奥押欧殴翁沖憶乙卸穏佳嫁寡暇架禍稼箇華菓蚊雅餓介塊壊怪悔懐戒拐皆劾慨概涯該垣嚇核殻獲穫較郭隔岳掛潟喝括渇滑褐轄且刈乾冠勘勧喚堪寛患憾換敢棺款歓汗環甘監緩缶肝艦貫還鑑閑陥含頑企奇岐幾忌既棋棄祈軌輝飢騎鬼偽儀宜戯擬欺犠菊吉喫詰却脚虐丘及朽窮糾巨拒拠虚距享凶叫峡恐恭挟況狂狭矯脅響驚仰凝暁斤琴緊菌襟謹吟駆愚虞偶遇隅屈掘靴繰桑勲薫傾刑啓契恵慶憩掲携渓継茎蛍鶏迎鯨撃傑倹兼剣圏堅嫌懸献肩謙賢軒遣顕幻弦玄孤弧枯誇雇顧鼓互呉娯御悟碁侯坑孔巧恒慌抗拘控攻更江洪溝甲硬稿絞綱肯荒衡貢購郊酵項香剛拷豪克酷獄腰込墾婚恨懇昆紺魂佐唆詐鎖債催宰彩栽歳砕斎載剤咲崎削搾索錯撮擦傘惨桟暫伺刺嗣施旨祉紫肢脂諮賜雌侍慈滋璽軸執湿漆疾芝赦斜煮遮蛇邪爵酌釈寂朱殊狩珠趣儒寿需囚愁秀臭舟襲酬醜充柔汁渋獣銃叔淑粛塾俊瞬准循旬殉潤盾巡遵庶緒叙徐償匠升召奨宵尚床彰抄掌昇晶沼渉焦症硝礁祥称粧紹肖衝訟詔詳鐘丈冗剰壌嬢浄畳譲醸錠嘱飾殖触辱伸侵唇娠寝審慎振浸紳薪診辛震刃尋甚尽迅陣酢吹帥炊睡粋衰遂酔随髄崇枢据杉澄瀬畝是姓征牲誓請逝斉隻惜斥析籍跡拙摂窃仙占扇栓潜旋繊薦践遷鮮漸禅繕塑措疎礎租粗訴阻僧双喪壮捜掃挿曹槽燥荘葬藻遭霜騒憎贈促即俗賊堕妥惰駄耐怠替泰滞胎袋逮滝卓択拓沢濯託濁諾但奪脱棚丹嘆淡端胆鍛壇弾恥痴稚致遅畜蓄逐秩窒嫡抽衷鋳駐弔彫徴懲挑眺聴超跳勅朕沈珍鎮陳津墜塚漬坪釣亭偵貞呈堤帝廷抵締艇訂逓邸泥摘滴哲徹撤迭添殿吐塗斗渡途奴怒倒凍唐塔悼搭桃棟盗痘筒到謄踏逃透陶騰闘洞胴峠匿督篤凸突屯豚曇鈍縄軟尼弐如尿妊忍寧猫粘悩濃把覇婆廃排杯輩培媒賠陪伯拍泊舶薄迫漠爆縛肌鉢髪伐罰抜閥伴帆搬畔繁般藩販範煩頒盤蛮卑妃彼扉披泌疲碑罷被避尾微匹姫漂描苗浜賓頻敏瓶怖扶敷普浮符腐膚譜賦赴附侮舞封伏幅覆払沸噴墳憤紛雰丙併塀幣弊柄壁癖偏遍舗捕穂募慕簿倣俸奉峰崩抱泡砲縫胞芳褒邦飽乏傍剖坊妨帽忙房某冒紡肪膨謀僕墨撲朴没堀奔翻凡盆摩磨魔麻埋膜又抹繭慢漫魅岬妙眠矛霧婿娘銘滅免茂妄猛盲網耗黙戻紋厄躍柳愉癒諭唯幽悠憂猶裕誘雄融与誉庸揚揺擁溶窯謡踊抑翼羅裸頼雷絡酪欄濫吏履痢離硫粒隆竜慮虜了僚寮涼猟療糧陵倫厘隣塁涙累励鈴隷零霊麗齢暦劣烈裂廉恋錬炉露廊楼浪漏郎賄惑枠湾腕'),
        (u'New jouyou', u'挨宛闇椅畏萎茨咽淫臼唄餌怨艶旺岡臆俺苛牙崖蓋骸柿顎葛釜鎌瓦韓玩伎畿亀僅巾錦駒串窟熊稽詣隙桁拳鍵舷股虎乞勾喉梗頃痕沙挫塞采阪埼柵拶斬鹿叱嫉腫呪蹴拭尻芯腎須裾凄醒戚脊煎羨腺詮膳曽狙遡爽痩捉袖遜汰唾堆戴誰旦綻酎捗椎潰爪鶴諦溺填貼妬賭藤憧瞳栃頓奈那謎鍋匂虹捻罵剥箸斑氾汎眉膝肘媛阜蔽蔑蜂貌頬睦勃昧枕蜜冥麺餅冶弥湧妖沃嵐藍梨璃侶瞭瑠呂賂弄麓脇丼傲刹哺喩嗅嘲毀彙恣惧慄憬拉摯曖楷鬱璧瘍箋籠緻羞訃諧貪踪辣錮'),
        (u'Jinmeiyou (regular)', u'丑丞乃之乎也云亘亙些亦亥亨亮仔伊伍伽佃佑伶侃侑俄俠俣俐倭俱倦倖偲傭儲允兎兜其冴凌凜凛凧凪凰凱函劉劫勁勿匡廿卜卯卿厨厩叉叡叢叶只吾吞吻哉啄哩喬喧喰喋嘩嘉嘗噌噂圃圭坐尭堯坦埴堰堺堵塙塡壕壬夷奄奎套娃姪姥娩嬉孟宏宋宕宥寅寓寵尖尤屑峨峻崚嵯嵩嶺巌巖已巳巴巷巽帖幌幡庄庇庚庵廟廻弘弛彌彗彦彪彬徠忽怜恢恰恕悌惟惚悉惇惹惺惣慧憐戊或戟托按挺挽掬捲捷捺捧掠揃摑摺撒撰撞播撫擢孜敦斐斡斧斯於旭昂昊昏昌昴晏晃晄晒晋晟晦晨智暉暢曙曝曳曾朋朔杏杖杜李杭杵杷枇柑柴柘柊柏柾柚桧檜栞桔桂栖桐栗梧梓梢梛梯桶梶椛梁棲椋椀楯楚楕椿楠楓椰楢楊榎樺榊榛槙槇槍槌樫槻樟樋橘樽橙檎檀櫂櫛櫓欣欽歎此殆毅毘毬汀汝汐汲沌沓沫洸洲洵洛浩浬淵淳渚淀淋渥湘湊湛溢滉溜漱漕漣澪濡瀕灘灸灼烏焰焚煌煤煉熙燕燎燦燭燿爾牒牟牡牽犀狼猪獅玖珂珈珊珀玲琢琉瑛琥琶琵琳瑚瑞瑶瑳瓜瓢甥甫畠畢疋疏瘦皐皓眸瞥矩砦砥砧硯碓碗碩碧磐磯祇祢禰祐禄祿禎禱禽禾秦秤稀稔稟稜穣穰穿窄窪窺竣竪竺竿笈笹笙笠筈筑箕箔篇篠簞簾籾粥粟糊紘紗紐絃紬絆絢綺綜綴緋綾綸縞徽繫繡纂纏羚翔翠耀而耶耽聡肇肋肴胤胡脩腔膏臥舜舵芥芹芭芙芦苑茄苔苺茅茉茸茜莞荻莫莉菅菫菖萄菩萌萠萊菱葦葵萱葺萩董葡蓑蒔蒐蒼蒲蒙蓉蓮蔭蔣蔦蓬蔓蕎蕨蕉蕃蕪薙蕾蕗藁薩蘇蘭蝦蝶螺蟬蟹蠟衿袈袴裡裟裳襖訊訣註詢詫誼諏諄諒謂諺讃豹貰賑赳跨蹄蹟輔輯輿轟辰辻迂迄辿迪迦這逞逗逢遥遙遁遼邑祁郁鄭酉醇醐醍醬釉釘釧鋒鋸錐錆錫鍬鎧閃閏閤阿陀隈隼雀雁雛雫霞靖鞄鞍鞘鞠鞭頁頌頗頰顚颯饗馨馴馳駕駿驍魁魯鮎鯉鯛鰯鱒鱗鳩鳶鳳鴨鴻鵜鵬鷗鷲鷺鷹麒麟麿黎黛鼎'),
        (u'Jinmeiyou (variant)', u'亞惡爲衞谒緣應櫻奧橫溫價祸壞懷樂渴卷陷寬氣僞戲虛峽狹曉勳薰惠揭鷄藝擊縣儉劍險圈檢顯驗嚴廣恆黃國黑碎雜兒濕壽收從澁獸縱緖敍將涉燒獎條狀乘淨剩疊孃讓釀眞寢愼盡粹醉穗瀨齊靜攝專戰纖禪壯爭莊搜巢裝騷增藏臟卽帶滯單團彈晝鑄廳徵聽鎭轉傳燈盜稻德拜賣髮拔晚祕拂佛步飜每默藥與搖樣謠來賴覽龍綠淚壘曆歷鍊郞錄')
        ]

def genKanjiStats():
    wholeCollection = mw.state == "deckBrowser"
    s = KanjiStats(mw.col, wholeCollection)
    rep = s.report()
    rep += s.seenReport()
    rep += s.missingReport()
    rep += s.nonJouyouReport()
    return rep

def onKanjiStats():
    mw.progress.start(immediate=True)
    rep = genKanjiStats()
    d = QDialog(mw)
    l = QVBoxLayout()
    l.setMargin(0)
    w = AnkiWebView()
    l.addWidget(w)
    w.stdHtml(rep)
    bb = QDialogButtonBox(QDialogButtonBox.Close)
    l.addWidget(bb)
    bb.connect(bb, SIGNAL("rejected()"), d, SLOT("reject()"))
    d.setLayout(l)
    d.resize(500, 400)
    restoreGeom(d, "kanjistats")
    mw.progress.finish()
    d.exec_()
    saveGeom(d, "kanjistats")

def createMenu():
    a = QAction(mw)
    a.setText("Kanji Stats")
    mw.form.menuTools.addAction(a)
    mw.connect(a, SIGNAL("triggered()"), onKanjiStats)

createMenu()

########NEW FILE########
__FILENAME__ = jp
# -*- coding: utf-8 -*-
# Copyright: Damien Elmes <anki@ichi2.net>
# License: GNU GPL, version 3 or later; http://www.gnu.org/copyleft/gpl.html

import japanese.model
import japanese.reading
import japanese.lookup
import japanese.stats
import japanese.bulkreading

########NEW FILE########
__FILENAME__ = keys
from ankiqt import mw

mw.mainWin.actionUndo.setShortcut("9")
mw.mainWin.actionMarkCard.setShortcut("8")

def newEventHandler(evt):
    key = unicode(evt.text())
    if mw.state == "showQuestion" and key == "0":
        evt.accept()
        return mw.mainWin.showAnswerButton.click()
    elif mw.state == "showAnswer" and key == "0":
        evt.accept()
        return getattr(mw.mainWin, "easeButton%d" %
                       mw.defaultEaseButton()).animateClick()
    return oldEventHandler(evt)

oldEventHandler = mw.keyPressEvent
mw.keyPressEvent = newEventHandler

########NEW FILE########
__FILENAME__ = latexcloze
# -*- coding: utf-8 -*-
# Copyright: Damien Elmes <anki@ichi2.net>
# License: GNU GPL, version 3 or later; http://www.gnu.org/copyleft/gpl.html
#
# Fixes cloze generation in LaTeX. This code is a hack. :-)
#

from PyQt4.QtCore import *
from PyQt4.QtGui import *
from ankiqt import ui
from anki.utils import tidyHTML
import re

clozeColour = "#0000ff"

def onClozeRepl(self):
    src = self.focusedEdit()
    if not src:
        return
    re1 = "\[(?:<.+?>)?.+?(:(.+?))?\](?:</.+?>)?"
    re2 = "\[(?:<.+?>)?(.+?)(:.+?)?\](?:</.+?>)?"
    # add brackets because selected?
    cursor = src.textCursor()
    oldSrc = None
    if cursor.hasSelection():
        oldSrc = src.toHtml()
        s = cursor.selectionStart()
        e = cursor.selectionEnd()
        cursor.setPosition(e)
        cursor.insertText("]]")
        cursor.setPosition(s)
        cursor.insertText("[[")
        re1 = "\[" + re1 + "\]"
        re2 = "\[" + re2 + "\]"
    dst = None
    for field in self.fact.fields:
        w = self.fields[field.name][1]
        if w.hasFocus():
            dst = False
            continue
        if dst is False:
            dst = w
            break
    if not dst:
        dst = self.fields[self.fact.fields[0].name][1]
        if dst == w:
            return
    # check if there's alredy something there
    if not oldSrc:
        oldSrc = src.toHtml()
    oldDst = dst.toHtml()
    if unicode(dst.toPlainText()):
        if (self.lastCloze and
            self.lastCloze[1] == oldSrc and
            self.lastCloze[2] == oldDst):
            src.setHtml(self.lastCloze[0])
            dst.setHtml("")
            self.lastCloze = None
            self.saveFields()
            return
        else:
            ui.utils.showInfo(
                _("Next field must be blank."),
                help="ClozeDeletion",
                parent=self.parent)
            return
    # escape known
    oldtxt = unicode(src.toPlainText())
    html = unicode(src.toHtml())
    reg = "\[(/?(latex|\$|\$\$))\]"
    repl = "{\\1}"
    txt = re.sub(reg, repl, oldtxt)
    html = re.sub(reg, repl, html)
    haveLatex = txt != oldtxt
    # check if there's anything to change
    if not re.search("\[.+?\]", txt):
        ui.utils.showInfo(
            _("You didn't specify anything to occlude."),
            help="ClozeDeletion",
            parent=self.parent)
        return
    # create
    ses = tidyHTML(html).split("<br>")
    news = []
    olds = []
    for s in ses:
        haveLatex = ("latex" in s or "{$}" in s or "{$$}" in s)
        def repl(match):
            exp = ""
            if match.group(2):
                exp = match.group(2)
            if haveLatex:
                return "\\textbf{[...%s]}" % (exp)
            else:
                return '<font color="%s"><b>[...%s]</b></font>' % (
                    clozeColour, exp)
        new = re.sub(re1, repl, s)
        if haveLatex:
            old = re.sub(re2, "{\\\\bf{}\\1\\\\rm{}}", s)
        else:
            old = re.sub(re2, '<font color="%s"><b>\\1</b></font>'
                         % clozeColour, s)
        reg = "\{(/?(latex|\$|\$\$))\}"
        repl = "[\\1]"
        new = re.sub(reg, repl, new)
        old = re.sub(reg, repl, old)
        news.append(new)
        olds.append(old)
    src.setHtml("<br>".join(news))
    dst.setHtml("<br>".join(olds))
    self.lastCloze = (oldSrc, unicode(src.toHtml()),
                      unicode(dst.toHtml()))
    self.saveFields()

ui.facteditor.FactEditor.onCloze = onClozeRepl

########NEW FILE########
__FILENAME__ = makecardsunique
# -*- coding: utf-8 -*-
# Copyright: Damien Elmes <anki@ichi2.net>
# License: GNU GPL, version 3 or later; http://www.gnu.org/copyleft/gpl.html
#
# Fix decks with consecutive card/fact/field IDs generated by misbehaving
# plugins
#

from PyQt4.QtGui import *
from PyQt4.QtCore import *
from ankiqt import mw
from anki.utils import genID
from ankiqt.ui.utils import showInfo

def run():
    db = mw.deck.s
    mw.startProgress()
    # gather old ids
    data = []
    for id in db.column0("select id from facts"):
        data.append(dict(new=genID(), old=id))
    # update facts
    db.statements("update facts set id = :new where id = :old", data)
    # fields
    db.statements(
        "update fields set id = random(), factId = :new where factId = :old",
        data)
    # cards
    db.statements(
        "update cards set id = random(), factId = :new where factId = :old",
        data)
    mw.finishProgress()
    mw.deck.setModified()
    mw.deck.save()
    showInfo("Done.")

a = QAction(mw)
a.setText("Make Cards Unique")
mw.mainWin.menuTools.addAction(a)
mw.connect(a, SIGNAL("triggered()"), run)

########NEW FILE########
__FILENAME__ = markdelete
# -*- coding: utf-8 -*-
# Copyright: Damien Elmes <anki@ichi2.net>
# License: GNU GPL, version 3 or later; http://www.gnu.org/copyleft/gpl.html
#
# This plugin replaces the standard 'delete card' option in the edit menu with
# one that marks the fact first. This is useful for finding facts missing
# certain cards later.
#
# If you have already deleted cards and want them to be included:
#
# 1. Open the editor, select all of your cards
# 2. Choose Actions>Generate Cards, and select the card type you deleted
# 3. Sort the deck by created date, and find all the newly added cards.
# 4. Select them, choose Actions>Add Tag, and add the tag "MarkDelete"
# 5. Remove the cards again.

from PyQt4.QtCore import *
from PyQt4.QtGui import *
from ankiqt import mw
from anki.utils import canonifyTags

def markAndDelete():
    undo = _("MarkDelete")
    mw.deck.setUndoStart(undo)
    mw.currentCard.fact.tags = canonifyTags(mw.currentCard.fact.tags +
                                            "," + "MarkDelete")
    mw.currentCard.fact.setModified()
    mw.deck.updateFactTags([mw.currentCard.fact.id])
    mw.deck.deleteCard(mw.currentCard.id)
    mw.reset()
    mw.deck.setUndoEnd(undo)

act = QAction(mw)
act.setText("Mark and &Delete")
icon = QIcon()
icon.addPixmap(QPixmap(":/icons/editdelete.png"))
act.setIcon(icon)
mw.connect(act, SIGNAL("triggered()"),
           markAndDelete)

old = mw.mainWin.actionDelete
act.setEnabled(old.isEnabled())

mw.mainWin.menuEdit.removeAction(mw.mainWin.actionDelete)
mw.mainWin.menuEdit.addAction(act)

# make sure it's enabled/disabled
mw.mainWin.actionDelete = act

mw.registerPlugin("Mark and Delete", 8)

########NEW FILE########
__FILENAME__ = mergechilddecks
#!/usr/bin/python
# Copyright Andreas Klauer 2013
#-*- coding: utf-8 -*-

import aqt
from aqt.utils import askUser
from anki.hooks import addHook
from anki.utils import intTime, ids2str

def profileLoaded():
    col = aqt.mw.col
    dm = col.decks

    leafdecks = []

    for deck in dm.all():
        if 'terms' in deck:
            # ignore dynamic decks
            continue
        if not dm.parents(deck['id']):
            # ignore decks without parents
            continue
        if dm.children(deck['id']):
            # ignore decks with children
            continue

        leafdecks.append(deck)

    if not askUser("Merge decks?"):
        return

    for deck in leafdecks:
        # deck.parent()?
        parent="::".join(deck['name'].split("::")[:-1])
        parent = dm.get(dm.id(parent))

        print "merging", deck['name'], "into", parent['name']

        cids = dm.cids(deck['id'])

        # inspired from aqt.browser.setDeck
        mod = intTime()
        usn = col.usn()
        scids = ids2str(cids)
        col.sched.remFromDyn(cids)
        col.db.execute("""
update cards set usn=?, mod=?, did=? where id in """ + scids,
                            usn, mod, parent['id'])

        # delete the deck
        dm.rem(deck['id'])

        # add original deck name to deckmerge field (if present and empty)
        nids = list(set([col.getCard(i).nid for i in cids]))
        col.findReplace(nids, "^$", deck['name'], regex=True, field='deckmerge')


addHook("profileLoaded", profileLoaded)

########NEW FILE########
__FILENAME__ = movetags
# -*- coding: utf-8 -*-
# Copyright: Damien Elmes <anki@ichi2.net>
# License: GNU GPL, version 3 or later; http://www.gnu.org/copyleft/gpl.html

# put in your plugins directory, open deck, run 'move tags' from the plugins
# menu. after that, you can remove the plugin again.
#
# since it will mark all facts modified, run it after syncing with the server

from PyQt4.QtCore import *
from PyQt4.QtGui import *
from ankiqt import mw
from anki.facts import Fact
from anki.utils import canonifyTags

def moveTags():
    for fact in mw.deck.s.query(Fact).all():
        old = fact.tags
        fact.tags = canonifyTags(fact.tags + "," + ",".join(
                                 [c.tags for c in fact.cards]))
        fact.setModified()
    mw.deck.setModified()
    mw.reset()

def init():
    q = QAction(mw)
    q.setText("Move Tags")
    mw.mainWin.menuPlugins.addAction(q)
    mw.connect(q, SIGNAL("triggered()"), moveTags)

mw.addHook("init", init)

########NEW FILE########
__FILENAME__ = mplayerlog
import subprocess, os
from aqt import mw
import anki.sound as s

file = None
s.mplayerCmd.remove("-really-quiet")

def sp(self):
    global file
    if not file:
        file = open(os.path.join(mw.pm.addonFolder(), "mplayerlog.txt"), "w")
    cmd = s.mplayerCmd + ["-slave", "-idle"]
    self.mplayer = subprocess.Popen(
        cmd, startupinfo=s.si, stdin=subprocess.PIPE,
        stdout=file, stderr=file)

s.MplayerMonitor.startProcess = sp

########NEW FILE########
__FILENAME__ = nodefaultanswer
# -*- coding: utf-8 -*-
# Copyright: Damien Elmes <anki@ichi2.net>
# License: GNU GPL, version 3 or later; http://www.gnu.org/copyleft/gpl.html
#
# Set focus to middle area when answer shown, so space does not trigger the
# answer buttons.
#

from aqt.qt import *
from aqt import mw
import aqt.reviewer
from anki.hooks import addHook, wrap

def noAnswer():
    mw.reviewer.web.setFocus()

addHook("showAnswer", noAnswer)

def keyHandler(self, evt, _old):
    key = unicode(evt.text())
    if (key == " " or evt.key() in (Qt.Key_Return, Qt.Key_Enter)):
        if self.state == "answer":
            return
    _old(self, evt)

aqt.reviewer.Reviewer._keyHandler = wrap(
    aqt.reviewer.Reviewer._keyHandler, keyHandler, "around")

########NEW FILE########
__FILENAME__ = oldshortcuts
# -*- coding: utf-8 -*-
# Copyright: Damien Elmes <anki@ichi2.net>
# License: GNU GPL, version 3 or later; http://www.gnu.org/copyleft/gpl.html
#
# Emulate some Anki 1.2 shortcuts.

from aqt import mw
from aqt.qt import *

mw.otherDeck = QShortcut(QKeySequence("Ctrl+w"), mw)
mw.otherAdd = QShortcut(QKeySequence("Ctrl+d"), mw)
mw.otherBrowse = QShortcut(QKeySequence("Ctrl+f"), mw)

mw.connect(
    mw.otherDeck, SIGNAL("activated()"), lambda: mw.moveToState("deckBrowser"))
mw.connect(
    mw.otherAdd, SIGNAL("activated()"), lambda: mw.onAddCard())
mw.connect(
    mw.otherBrowse, SIGNAL("activated()"), lambda: mw.onBrowse())

########NEW FILE########
__FILENAME__ = order
from ankiqt import mw
from operator import attrgetter
import re

def numericSort(a, b):
    vals = []
    for question in (a, b):
        # get int from start of string
        m = re.match("^(\d+). ", question)
        if m:
            vals.append(int(m.group(1)))
        else:
            vals.append(0)
    return cmp(*vals)

def sortDeck():
    # sort based on number
    mw.currentDeck.sort(cmp=numericSort, key=attrgetter("question"))
    # print the new order for confirmation
    for card in mw.currentDeck:
        print card.question
    mw.currentDeck.setModified()

mw.addHook("init", sortDeck)

########NEW FILE########
__FILENAME__ = Postpone Reviews
# -*- coding: utf-8 -*-
# Copyright: Damien Elmes <anki@ichi2.net>
# License: GNU GPL, version 3 or later; http://www.gnu.org/copyleft/gpl.html

# this plugin will reschedule the cards in the revision queue over a period of
# days. it attempts to add the delay to the interval so cards answered later
# that are remembered will get a boost, but there's no guarantee it won't
# mess up your statistics or cause other problems

from PyQt4.QtCore import *
from PyQt4.QtGui import *
from subprocess import Popen
from ankiqt import mw
import sys
from anki.cards import cardsTable
import time

def postpone():
    i = QInputDialog.getInteger(mw, _("Postpone"),
                                _("Number of days to spread repetitions over:"),
                                2, 1)
    if i[1] and i[0] > 1:
        mw.deck.s.flush()
        d = mw.deck
        q = d.s.all(
            d.cardLimit(
            "revActive", "revInactive", """
select c.id, interval, combinedDue from cards c where
type = 1 and combinedDue < :lim order by priority desc, combinedDue
"""), lim=d.dueCutoff)
        size = len(q) / i[0] + 1
        days = 0
        count = -1
        cards = []
        now = time.time()
        for item in q:
            count += 1
            if count == size:
                count = 0
                days += 1
            seconds = 86400 * days
            # determine the current delay
            delay = now - item.combinedDue
            cards.append({'id': item[0],
                          'interval': item[1] + days + (delay / 86400.0),
                          'due': now + seconds})
        # apply changes
        d.s.execute("""
update cards set
interval = :interval,
combinedDue = :due,
isDue = 0
where id = :id""", cards)
        # rebuild
        d.flushMod()
        mw.reset()

def init():
    q = QAction(mw)
    q.setText("Postpone")
    mw.mainWin.menuTools.addAction(q)
    mw.connect(q, SIGNAL("triggered()"), postpone)

mw.addHook("init", init)
mw.registerPlugin("Postpone Reviews", 6)

########NEW FILE########
__FILENAME__ = print
# -*- coding: utf-8 -*-
# Copyright: Damien Elmes <anki@ichi2.net>
# License: GNU GPL, version 3 or later; http://www.gnu.org/copyleft/gpl.html
#
# Exports the cards in the current deck to a HTML file, so they can be
# printed. Card styling is not included. Cards are printed in sort field
# order.

import re, urllib
from aqt.qt import *
from anki.utils import isWin
from anki.hooks import runHook, addHook
from aqt.utils import getBase, openLink
from aqt import mw
from anki.utils import ids2str

CARDS_PER_ROW = 3

def sortFieldOrderCids(did):
    dids = [did]
    for name, id in mw.col.decks.children(did):
        dids.append(id)
    return mw.col.db.list("""
select c.id from cards c, notes n where did in %s
and c.nid = n.id order by n.sfld""" % ids2str(dids))

def onPrint():
    path = os.path.join(mw.pm.profileFolder(), "print.html")
    ids = sortFieldOrderCids(mw.col.decks.selected())
    def esc(s):
        # strip off the repeated question in answer if exists
        #s = re.sub("(?si)^.*<hr id=answer>\n*", "", s)
        # remove type answer
        s = re.sub("\[\[type:[^]]+\]\]", "", s)
        return s
    def upath(path):
        if isWin:
            prefix = u"file:///"
        else:
            prefix = u"file://"
        return prefix + unicode(
            urllib.quote(path.encode("utf-8")), "utf-8")
    buf = open(path, "w")
    buf.write("<html>" + getBase(mw.col).encode("utf8") + "<body>")
    buf.write("""<style>
img { max-width: 100%; }
tr { page-break-after:auto; }
td { page-break-after:auto; }
td { border: 1px solid #ccc; padding: 1em; }
</style><table cellspacing=10 width=100%>""")
    first = True

    mw.progress.start(immediate=True)
    for j, cid in enumerate(ids):
        if j % CARDS_PER_ROW == 0:
            if not first:
                buf.write("</tr>")
            else:
                first = False
            buf.write("<tr>")
        c = mw.col.getCard(cid)
        cont = u"<td><center>%s</center></td>" % esc(c._getQA(True, False)['a'])
        buf.write(cont.encode("utf8"))
        if j % 50 == 0:
            mw.progress.update("Cards exported: %d" % (j+1))
    buf.write("</tr>")
    buf.write("</table></body></html>")
    mw.progress.finish()
    buf.close()
    openLink(upath(path))

q = QAction(mw)
q.setText("Print")
q.setShortcut(QKeySequence("Ctrl+P"))
mw.form.menuTools.addAction(q)
mw.connect(q, SIGNAL("triggered()"), onPrint)

########NEW FILE########
__FILENAME__ = quickcolours
# -*- coding: utf-8 -*-
# Copyright: Damien Elmes <anki@ichi2.net>
# License: GNU GPL, version 3 or later; http://www.gnu.org/copyleft/gpl.html
#
# Edit this to customize colours and shortcuts. By default, F8 will set the
# selection to red, and F9 to blue. You can use either simple colour names or
# HTML colour codes.

colours = [
    ("red", "F8"),
    ("#00f", "F9"),
]

from aqt import mw
from aqt.qt import *
from anki.hooks import addHook

def updateColour(editor, colour):
    editor.web.eval("saveSel();")
    editor.fcolour = colour
    editor.onColourChanged()
    editor._wrapWithColour(editor.fcolour)

def onSetupButtons(editor):
    # add colours
    for code, key in colours:
        s = QShortcut(QKeySequence(key), editor.parentWindow)
        s.connect(s, SIGNAL("activated()"),
                  lambda c=code: updateColour(editor, c))
    # remove the default f8 shortcut
    editor._buttons['change_colour'].setShortcut(QKeySequence())

addHook("setupEditorButtons", onSetupButtons)

########NEW FILE########
__FILENAME__ = randomdisplay
# -*- coding: utf-8 -*-
# Copyright: Damien Elmes <anki@ichi2.net>
# License: GNU GPL, version 3 or later; http://www.gnu.org/copyleft/gpl.html
#
# Alter fonts and position of text randomly

fontFaces = [u"Arial", u"Times New Roman", u"Courier"]
fontColours = ["#000", "#00f", "#0f0", "#f00"]
# start at maximum of 70% to the right
maxRight = 70
maxTop = 0
maxBottom = 30

import random
import re
from anki.hooks import addHook
from ankiqt import mw
from ankiqt import ui
from PyQt4.QtCore import *
from PyQt4.QtGui import *

saved = {}

def alter(css, card):
    if mw.state == "showQuestion":
        saved['face'] = random.choice(fontFaces)
        saved['col'] = random.choice(fontColours)
        saved['hoz'] = random.uniform(0, maxRight)
        saved['vert'] = random.uniform(maxTop, maxBottom)
    # else:
    #     saved['vert'] = 0
    css = re.sub('font-family:"(.+?)"', 'font-family:"%s"' % saved['face'], css)
    css = re.sub('color:(.+?);', 'color:%s;' % saved['col'], css)
    css = re.sub('text-align:.+?;', """
text-align: left; margin-left: %d%%; margin-top: %d%%""" %
                     (saved['hoz'], saved['vert']), css)
    return css

addHook("addStyles", alter)

########NEW FILE########
__FILENAME__ = revorder
# -*- coding: utf-8 -*-
# Copyright: Damien Elmes <anki@ichi2.net>
# License: GNU GPL, version 3 or later; http://www.gnu.org/copyleft/gpl.html
#
# Force review cards to be displayed in a particular order, at a roughly 10x
# decrease in performance.
#
# ivl desc: sort from largest interval first
# ivl asc: sort from smallest interval first

order = "ivl desc"

from anki.sched import Scheduler

def _fillRev(self):
    if self._revQueue:
        return True
    if not self.revCount:
        return False
    while self._revDids:
        did = self._revDids[0]
        lim = min(self.queueLimit, self._deckRevLimit(did))
        if lim:
            sql = """
select id from cards where
did = ? and queue = 2 and due <= ?"""
            sql2 = " limit ?"
# limit ?"""
            if self.col.decks.get(did)['dyn']:
                self._revQueue = self.col.db.list(
                    sql+sql2, did, self.today, lim)
                self._revQueue.reverse()
            else:
                self._revQueue = self.col.db.list(
                    sql+" order by "+order+sql2, did, self.today, lim)
                self._revQueue.reverse()
            if self._revQueue:
                # is the current did empty?
                if len(self._revQueue) < lim:
                    self._revDids.pop(0)
                return True
        # nothing left in the deck; move to next
        self._revDids.pop(0)

Scheduler._fillRev = _fillRev

########NEW FILE########
__FILENAME__ = searchdeck
# -*- coding: utf-8 -*-
# Copyright: Damien Elmes <anki@ichi2.net>
# License: GNU GPL, version 3 or later; http://www.gnu.org/copyleft/gpl.html
#
# Automatically prepend 'deck:current' when searching. To search the whole
# collection, include deck:* in search.
#

from aqt import mw
from aqt.browser import Browser
from anki.hooks import wrap

def onSearch(self, reset=True):
    txt = unicode(self.form.searchEdit.lineEdit().text()).strip()
    if "deck:" in txt:
        return
    if _("<type here to search; hit enter to show current deck>") in txt:
        return
    if "is:current" in txt:
        return
    if not txt.strip():
        return self.form.searchEdit.lineEdit().setText("deck:*")
    self.form.searchEdit.lineEdit().setText("deck:current " + txt)

Browser.onSearch = wrap(Browser.onSearch, onSearch, "before")

########NEW FILE########
__FILENAME__ = showlastans
# -*- coding: utf-8 -*-
# Copyright: Damien Elmes <anki@ichi2.net>
# License: GNU GPL, version 3 or later; http://www.gnu.org/copyleft/gpl.html
#
# Marks the previous answer button like '*Again*'
# Sponsored by Alan Clontz.
#

from PyQt4.QtCore import *
from PyQt4.QtGui import *
from ankiqt import mw, ui
from anki.hooks import wrap
import os,re

def showLast():
    lastEase = mw.deck.s.scalar("""
select ease from reviewHistory where cardId = :id
order by time desc limit 1""", id=mw.currentCard.id)
    # make sure ease1 is reset
    mw.mainWin.easeButton1.setText(_("Again"))
    if lastEase:
        but = getattr(mw.mainWin, "easeButton%d" % lastEase)
        but.setText("*%s*" % but.text())

mw.showEaseButtons = wrap(mw.showEaseButtons, showLast)

########NEW FILE########
__FILENAME__ = Smartfm Sentence Importer
# -*- coding: utf-8 -*-
# Copyright: Damien Elmes <anki@ichi2.net>
# License: GNU GPL, version 3 or later; http://www.gnu.org/copyleft/gpl.html
#
# This plugin lets you import smart.fm material into Anki.
#
# Many thanks to smart.fm for the material and the generous sharing policies.
#
# To use, create a new deck, then run Tools > Smart.fm Import
#
# Enter a list URL like:
# http://www.iknow.co.jp/lists/19055-japanese-core-2000-step-2
#
# Once it's finished downloading, you can add more contents, or click cancel
# to finish.
#

includeImages = False
includeSounds = True

import re, urllib, urllib2, simplejson

from PyQt4.QtCore import *
from PyQt4.QtGui import *
from ankiqt import mw
from ankiqt.ui.utils import getOnlyText
from anki.models import Model, FieldModel, CardModel
from anki.features.japanese import kakasi

def doImport():
    # add an iknow model
    if not [m for m in mw.deck.models if m.name == 'Smart.fm']:
        m = Model(u'Smart.fm')
        m.addFieldModel(FieldModel(u'Expression', False, False))
        m.addFieldModel(FieldModel(u'Meaning', False, False))
        m.addFieldModel(FieldModel(u'Reading', False, False))
        m.addFieldModel(FieldModel(u'Audio', False, False))
        m.addFieldModel(FieldModel(u'Image', False, False))
        m.addCardModel(CardModel(
            u'Listening',
            u'Listen.%(Audio)s',
            u'%(Expression)s<br>%(Reading)s<br>%(Meaning)s<br>%(Image)s'))
        mw.deck.addModel(m)
    while 1:
        mw.reset()
        url = getOnlyText("Enter list URL:")
        if not url:
            return
        id = re.search("/lists/(\d+)", url).group(1)
        # get sentences
        f = urllib2.urlopen(
            "http://api.smart.fm/lists/%s/sentences.json" % id)
        d = simplejson.load(f)
        # add facts
        diag = QProgressDialog(_("Importing..."), "", 0, 0, mw)
        diag.setCancelButton(None)
        diag.setMaximum(len(d))
        diag.setMinimumDuration(0)
        for i, sen in enumerate(d):
            diag.setValue(i)
            diag.setLabelText(sen['text'])
            mw.app.processEvents()
            f = mw.deck.newFact()
            f['Expression'] = sen['text']
            f['Meaning'] = sen['translations'] and sen['translations'][0]['text'] or u""
            try:
                f['Reading'] = sen['transliterations']['Hrkt'] or u""
                # reading is sometimes missing
                if not f['Reading'] and kakasi:
                    f['Reading'] = kakasi.toFurigana(f['Expression'])
            except KeyError:
                f['Reading'] = u""
            if includeSounds and sen['sound']:
                (file, headers) = urllib.urlretrieve(sen['sound'])
                path = mw.deck.addMedia(file)
                f['Audio'] = u'[sound:%s]' % path
            else:
                f['Audio'] = u""
            if includeImages and sen['image']:
                (file, headers) = urllib.urlretrieve(sen['image'])
                path = mw.deck.addMedia(file)
                f['Image'] = u'<img src="%s">' % path
            else:
                f['Image'] = u""
            mw.deck.addFact(f)
        diag.cancel()
        mw.deck.save()

act = QAction(mw)
act.setText("Smart.fm Import")
mw.connect(act, SIGNAL("triggered()"),
           doImport)

mw.mainWin.menuTools.addSeparator()
mw.mainWin.menuTools.addAction(act)

mw.registerPlugin("Smart.fm Sentence Importer", 1)

########NEW FILE########
__FILENAME__ = splitcloze
# -*- coding: utf-8 -*-
# Copyright: Damien Elmes <anki@ichi2.net>
# License: GNU GPL, version 3 or later; http://www.gnu.org/copyleft/gpl.html
#
# Moves non-cloze cards in cloze models to a new model. Assumes the first
# field is the cloze field.
#

import re, copy
from aqt import mw
from aqt.qt import *
from aqt.utils import showInfo
from anki.utils import ids2str, splitFields

def splitClozes():
    mw.col.modSchema()
    mw.progress.start(immediate=True)
    try:
        _splitClozes()
    finally:
        mw.progress.finish()
    showInfo("Success. Please remove this addon and upgrade.")

def _splitClozes():
    data = []
    for m in mw.col.models.all():
        # cloze model?
        if '{{cloze:' not in m['tmpls'][0]['qfmt']:
            continue
        tmpls = []
        tmap = {}
        for t in m['tmpls']:
            if '{{cloze:' not in t['qfmt']:
                tmpls.append(t)
                tmap[t['ord']] = len(tmpls) - 1
                t['afmt'] = t['afmt'].replace("{{cloze:1:", "{{")
        # any non-clozes found?
        if not tmpls:
            continue
        # create a new model
        m2 = mw.col.models.copy(m)
        # add the non-cloze templates
        m2['tmpls'] = copy.deepcopy(tmpls)
        mw.col.models._updateTemplOrds(m2)
        mw.col.models.save(m2)
        mw.col.models.setCurrent(m2)
        # copy old note data
        snids = ids2str(mw.col.models.nids(m))
        for id, flds in mw.col.db.all(
            "select id, flds from notes where id in " + snids):
            n = mw.col.newNote()
            sflds = splitFields(flds)
            for name, (ord, field) in mw.col.models.fieldMap(m2).items():
                if ord == 0:
                    sflds[0] = re.sub("{{c\d::(.+?)}}", r"\1", sflds[0])
                n[name] = sflds[ord]
            mw.col.addNote(n)
            # delete the generated cards and move the old cards over
            mw.col.db.execute(
                "delete from cards where nid = ?", n.id)
            for old, new in tmap.items():
                mw.col.db.execute("""
update cards set ord = ?, nid = ? where ord = ? and nid = ?""",
                                  new, n.id, old, id)
        # delete the templates from the old model
        for t in tmpls:
            mw.col.models.remTemplate(m, t)

a = QAction(mw)
a.setText("Split Clozes")
mw.form.menuTools.addAction(a)
mw.connect(a, SIGNAL("triggered()"), splitClozes)

########NEW FILE########
__FILENAME__ = synclatex
# -*- coding: utf-8 -*-
# Copyright: Damien Elmes <anki@ichi2.net>
# License: GNU GPL, version 3 or later; http://www.gnu.org/copyleft/gpl.html
#
# This plugin adds your LaTeX files to the media database when you run
# Tools>Advanced>Cache LaTeX. After doing this, you can use them in the iPhone
# app.

import time
from anki.utils import genID
from anki import latex as latexOrig
from anki.utils import canonifyTags
from anki.hooks import wrap

def imgLink(deck, latex, build=True):
    "Parse LATEX and return a HTML image representing the output."
    latex = latexOrig.mungeLatex(latex)
    (ok, img) = latexOrig.imageForLatex(deck, latex, build)
    if ok:
        deck.s.statement("""
    insert or replace into media values
    (:id, :fn, 0, :t, '', 'latex')""",
                         id=genID(),
                         fn=img,
                         t=time.time())
    if ok:
        return '<img src="%s">' % img
    else:
        return img

def clearDB(deck):
    deck.flushMod()
    deck.s.execute("delete from media where description = 'latex'")

latexOrig.imgLink = imgLink
latexOrig.cacheAllLatexImages = wrap(latexOrig.cacheAllLatexImages, clearDB, "before")

########NEW FILE########
