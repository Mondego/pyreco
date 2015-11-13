__FILENAME__ = AboutWindow
#!/usr/bin/env python3
# vim: tabstop=8 expandtab shiftwidth=4 softtabstop=4

# WeCase -- This file implemented AboutWindow.
# Copyright (C) 2013, 2014 The WeCase Developers.
# License: GPL v3 or later.


from PyQt4 import QtGui
import version
from AboutWindow_ui import Ui_About_Dialog


class AboutWindow(QtGui.QDialog, Ui_About_Dialog):

    def __init__(self, parent=None):
        super(AboutWindow, self).__init__(parent)
        self.setupUi(self)

    def setupUi(self, widget):
        super().setupUi(widget)

        if version.pkgprovider == version.default_provider:
            vanilla = self.tr("Vanilla Version")
            widget.distLabel.setText(vanilla)
        else:
            disttext = version.pkgprovider
            widget.distLabel.setText(widget.distLabel.text() % disttext)

        widget.versionLabel.setText(widget.versionLabel.text() % version.pkgversion)
        widget.descriptionLabel.setText(widget.descriptionLabel.text() % version.bug_report_url)

########NEW FILE########
__FILENAME__ = AsyncFetcher
#!/usr/bin/env python3
# vim: tabstop=8 expandtab shiftwidth=4 softtabstop=4

# WeCase -- This file implemented an Async File Downloader.
# Copyright (C) 2013, 2014 The WeCase Developers.
# License: GPL v3 or later.


from PyQt4 import QtCore
from urllib.request import urlretrieve
from urllib.error import URLError, ContentTooShortError
from http.client import BadStatusLine
from WeHack import async, SingletonDecorator
from threading import Event
import os
from time import sleep


class SignalSender(QtCore.QObject):

    fetched = QtCore.pyqtSignal(str)

    def __init__(self, parent=None):
        super(SignalSender, self).__init__(parent)

    def emit(self, target):
        self.fetched.emit(target)

    def connect(self, target):
        self.fetched.connect(target)

    def disconnect(self, target):
        self.fetched.disconnect(target)


class _AsyncFetcher(QtCore.QObject):

    DO_NOT_HAVE = 0
    DOWNLOADED = 1
    DOWNLOADING = 2

    def __init__(self, path, parent=None):
        super(_AsyncFetcher, self).__init__(parent)

        if path[-1] != "/":
            path += "/"
        if not os.path.exists(path):
                os.makedirs(path)

        self.path = path
        self._signals = {}
        self._modified = Event()

    @staticmethod
    def _formattedFilename(url):
        url_parts = url.split('/')
        return "%s_%s" % (url_parts[-2], url_parts[-1])

    @async
    def _download(self, url, filepath):
        while 1:
            try:
                urlretrieve(url, filepath)
                break
            except (BadStatusLine, ContentTooShortError, URLError):
                sleep(1)
                continue

        self._modified.wait()
        self._process_callbacks(filepath)

    def _get_state(self, filepath):
        if self._signals.get(filepath, []):
            assert os.path.exists, "The file should exists, but it doesn't exist."
            return self.DOWNLOADING
        elif os.path.exists(filepath):
            return self.DOWNLOADED
        return self.DO_NOT_HAVE

    def _add_callback(self, filepath, callback):
        signal = SignalSender()
        signal.connect(callback)

        try:
            array = self._signals[filepath]
            array.append(signal)
        except KeyError:
            self._signals[filepath] = [signal]

    def _process_callbacks(self, filepath):
        signals = self._signals[filepath]
        for signal in signals:
            signal.emit(filepath)
        self._signals[filepath] = []

    def addTask(self, url, callback):
        filename = self._formattedFilename(url)
        filepath = "".join((self.path, filename))

        self._modified.clear()

        state = self._get_state(filepath)
        self._add_callback(filepath, callback)
        if state == self.DO_NOT_HAVE:
            self._download(url, filepath)
        elif state == self.DOWNLOADING:
            pass
        elif state == self.DOWNLOADED:
            self._process_callbacks(filepath)
        else:
            assert False, "Downloaded but downloading now?"

        self._modified.set()

AsyncFetcher = SingletonDecorator(_AsyncFetcher)

########NEW FILE########
__FILENAME__ = const
#!/usr/bin/env python3
# vim: tabstop=8 expandtab shiftwidth=4 softtabstop=4

# WeCase -- This file defined constants.
# Copyright (C) 2013, 2014 The WeCase Developers.
# License: GPL v3 or later.


APP_KEY = "1011524190"
APP_SECRET = "1898b3f668368b9f4a6f7ac8ed4a918f"
CALLBACK_URL = 'https://api.weibo.com/oauth2/default.html'
OAUTH2_PARAMETER = {'client_id': APP_KEY,
                    'response_type': 'code',
                    'redirect_uri': CALLBACK_URL,
                    'action': 'submit',
                    'userId': '',  # username
                    'passwd': '',  # password
                    'isLoginSina': 0,
                    'from': '',
                    'regCallback': '',
                    'state': '',
                    'ticket': '',
                    'withOfficalFlag': 0}
MAX_IMAGE_BYTES = 5 * 1024 * 1024  # 5 MiB

########NEW FILE########
__FILENAME__ = Face
#!/usr/bin/env python3
# vim: tabstop=8 expandtab shiftwidth=4 softtabstop=4

# WeCase -- This model implemented a model for smileies.
# Copyright (C) 2013, 2014 The WeCase Developers.
# License: GPL v3 or later.


import path
from WeHack import Singleton
from collections import OrderedDict
try:
    from xml.etree.cElementTree import ElementTree
except ImportError:
    from xml.etree.ElementTree import ElementTree


class FaceItem():
    def __init__(self, xml_node):
        super(FaceItem, self).__init__()
        self._xml_node = xml_node
        self._name = ""
        self._path = ""
        self._category = ""

    @property
    def name(self):
        if not self._name:
            self._name = self._xml_node.get("tip")
        return self._name

    @property
    def path(self):
        if not self._path:
            self._path = "%s%s" % (path.face_path, self._xml_node[0].text)
        return self._path

    @property
    def category(self):
        if not self._category:
            self._category = self._xml_node[0].text.split("/")[0]
        return self._category


class FaceModel(metaclass=Singleton):

    def __init__(self):
        self._faces = OrderedDict()
        tree = ElementTree(file=path.face_path + "face.xml")

        category = ""
        for face in tree.iterfind("./FACEINFO/"):
            assert face.tag == "FACE"
            face = FaceItem(face)

            if category != face.category:
                category = face.category
                self._faces[category] = OrderedDict()
            else:
                self._faces[category][face.name] = face

        size = tree.find("./WNDCONFIG/Align")
        self._col, self._row = int(size.get("Col")), int(size.get("Row"))

        self._all_faces_cache = []

    def categories(self):
        return self._faces.keys()

    def faces_by_category(self, category):
        return iter(self._faces[category].values())

    def _cached_all_faces(self):
        for face in self._all_faces_cache:
            yield face

    def all_faces(self):
        for faces in self._faces.values():
            for face in faces.values():
                self._all_faces_cache.append(face)
                yield face
        self.all_faces = self._cached_all_faces

    def grid_size(self):
        return self._col, self._row

########NEW FILE########
__FILENAME__ = FaceWidget
#!/usr/bin/env python3
# vim: tabstop=8 expandtab shiftwidth=4 softtabstop=4

# WeCase -- This model implemented a widget for smileies.
# Copyright (C) 2013, 2014 The WeCase Developers.
# License: GPL v3 or later.


from PyQt4 import QtCore, QtGui
from WImageLabel import WImageLabel


class WFaceListWidget(QtGui.QWidget):

    smileyClicked = QtCore.pyqtSignal(str)

    def __init__(self, parent=None):
        super(WFaceListWidget, self).__init__(parent)

    def setModel(self, model):
        self._model = model
        self._setupUi()

    def _setupTabWidget(self, faces):
        layout = QtGui.QGridLayout()
        tab = QtGui.QWidget()
        tab.setLayout(layout)

        col, row = self._model.grid_size()

        for i in range(row):
            for j in range(col):
                try:
                    face = next(faces)
                    widget = WSmileyWidget(face)
                    widget.smileyClicked.connect(self.smileyClicked)
                except StopIteration:
                    widget = QtGui.QWidget()
                layout.addWidget(widget, i, j)
        return tab

    def _setupUi(self):
        self.layout = QtGui.QVBoxLayout()
        self.tabWidget = QtGui.QTabWidget()
        self.layout.addWidget(self.tabWidget)

        for category in self._model.categories():
            faces = self._model.faces_by_category(category)
            tab = self._setupTabWidget(faces)
            self.tabWidget.addTab(tab, category)
        self.setLayout(self.layout)

        self.tabWidget.tabBar().currentChanged.connect(self.turnAnimation)

        self._lastTab = 0
        self.tabWidget.tabBar().setCurrentIndex(0)
        self.turnAnimation(0)

    def turnAnimation(self, index):
        self._turnAnimation(self._lastTab, start=False)
        self._turnAnimation(index)
        self._lastTab = index

    def _turnAnimation(self, index, start=True):
        tab = self.tabWidget.widget(index)
        for index in range(tab.layout().count()):
            widget = tab.layout().itemAt(index).widget()
            try:
                if start:
                    widget.smileyLabel.start()
                else:
                    widget.smileyLabel.stop()
            except AttributeError:
                # a spacer
                pass


class WSmileyWidget(QtGui.QWidget):

    smileyClicked = QtCore.pyqtSignal(str)

    def __init__(self, smiley, parent=None):
        super(WSmileyWidget, self).__init__(parent)
        self._smiley = smiley
        self.smileyLabel = WImageLabel(self)
        self.smileyLabel.setToolTip(smiley.name)
        self.smileyLabel.setImageFile(smiley.path, False)
        # HACK: Start and stop animation to let Qt Layout calculate
        # the size of them correctly.
        self.smileyLabel.start()
        self.smileyLabel.stop()
        self.smileyLabel.clicked.connect(self._smileyClicked)

    def _smileyClicked(self):
        self.smileyClicked.emit(self._smiley.name)

########NEW FILE########
__FILENAME__ = FaceWindow
#!/usr/bin/env python3
# vim: tabstop=8 expandtab shiftwidth=4 softtabstop=4

# WeCase -- This file implemented SmileyWindow.
# Copyright (C) 2013, 2014 The WeCase Developers.
# License: GPL v3 or later.


from PyQt4 import QtGui
from Face import FaceModel
from FaceWidget import WFaceListWidget


class FaceWindow(QtGui.QDialog):
    def __init__(self, parent=None):
        super(FaceWindow, self).__init__(parent)
        self.setupUi(self)
        self.setupModels()
        self.faceName = ""

    def setupUi(self, widget):
        self.resize(533, 288)
        self.gridLayout = QtGui.QGridLayout(self)
        self.faceView = WFaceListWidget(self)
        self.gridLayout.addWidget(self.faceView, 0, 0, 1, 1)
        self.setWindowTitle(self.tr("Choose a smiley"))

    def setupModels(self):
        self.faceModel = FaceModel(self)
        self.faceView.setModel(self.faceModel)
        self.faceView.smileyClicked.connect(self.returnSmileyName)

    def returnSmileyName(self, faceName):
        self.faceName = "[%s]" % faceName
        self.done(True)

########NEW FILE########
__FILENAME__ = FilterTable
#!/usr/bin/env python3
# vim: tabstop=8 expandtab shiftwidth=4 softtabstop=4

# WeCase -- This model implemented a table of modify the filter.
# Copyright (C) 2013, 2014 The WeCase Developers.
# License: GPL v3 or later.


from PyQt4 import QtCore, QtGui
from copy import copy


# WARNING: This is the most ugly part of WeCase


class ComboBoxDelegate(QtGui.QStyledItemDelegate):

    def __init__(self, parent=None):
        super(ComboBoxDelegate, self).__init__(parent)

    def createEditor(self, parent, option, index):
        editor = QtGui.QComboBox(parent)
        return editor

    def setEditorData(self, editor, index):
        optionsDict = index.data(FilterTableModel.OptionRole)
        if index.column() == FilterTableModel.TYPE:
            options = list(optionsDict.keys())
        elif index.column() == FilterTableModel.ACTION:
            type = index.sibling(index.row(), FilterTableModel.TYPE).data(QtCore.Qt.DisplayRole)
            if type:
                options = optionsDict[type]
            else:
                options = []
        editor.addItems(options)

    def setModelData(self, editor, model, index):
        model.setData(index, editor.currentText(), QtCore.Qt.EditRole)

        if index.column() == FilterTableModel.TYPE:
            optionsDict = index.data(FilterTableModel.OptionRole)
            type = index.sibling(index.row(), FilterTableModel.TYPE).data(QtCore.Qt.DisplayRole)
            if index.sibling(index.row(), FilterTableModel.ACTION).data(QtCore.Qt.DisplayRole) not in optionsDict[type]:
                model.setData(index.sibling(index.row(), FilterTableModel.ACTION), None, QtCore.Qt.EditRole)

    def updateEditorGeometry(self, editor, option, index):
        editor.setGeometry(option.rect)


class FilterTableModel(QtCore.QAbstractTableModel):

    OptionRole = QtCore.Qt.UserRole
    TYPE = 0
    VALUE = 1
    ACTION = 2

    def __init__(self, parent=None, rows=1, cols=3):
        super(FilterTableModel, self).__init__(parent)
        self._data = []
        self._default_cols = cols

    def parent(self, index):
        return QtCore.QModelIndex()

    def rowCount(self, parent=QtCore.QModelIndex()):
        return len(self._data)

    def columnCount(self, parent=QtCore.QModelIndex()):
        try:
            return len(self._data[0])
        except IndexError:
            return self._default_cols

    def data(self, index, role=QtCore.Qt.DisplayRole):
        if role == QtCore.Qt.DisplayRole:
            return self._data[index.row()][index.column()]
        elif role == self.OptionRole:
            return {self.tr("Keyword"): (self.tr("Block"), self.tr("Word War")),
                    self.tr("User"): (self.tr("Block"),)}

    def setData(self, index, value, role=QtCore.Qt.EditRole):
        if role != QtCore.Qt.EditRole:
            return False

        self._data[index.row()][index.column()] = value
        self.dataChanged.emit(index, index)
        # don't forget to cast
        return True

    def headerData(self, section, orientatidon, role):
        if orientatidon == QtCore.Qt.Horizontal and role == QtCore.Qt.DisplayRole:
            return (self.tr("Type"), self.tr("Value"), self.tr("Action"))[section]

    def flags(self, index):
        return QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEditable | QtCore.Qt.ItemIsEnabled

    def insertRows(self, row, count, parent=QtCore.QModelIndex()):
        assert 0 <= row <= self.rowCount()
        assert count > 0

        self.beginInsertRows(parent, row, row + count - 1)
        new_row = [None] * self.columnCount()
        for row in range(row, row + count):
            self._data.insert(row, copy(new_row))
        self.endInsertRows()

    def removeRows(self, row, count, parent=QtCore.QModelIndex()):
        assert 0 <= row <= self.rowCount()
        assert count > 0

        self.beginRemoveRows(parent, row, row + count - 1)
        for row in range(row, row + count):
            del self._data[row]
        self.endRemoveRows()

    def insertColumns(self, col, count, parent=QtCore.QModelIndex()):
        assert 0 <= col <= self.columnCount()
        assert count > 0

        self.beginInsertColumns(parent, col, col + count - 1)
        for col in range(col, col + count):
            for _col in self._data:
                _col.insert(col, None)
        self.endInsertColumns()

    def _dump(self, type, action):
        blacklist = []

        for row in self._data:
            if row[self.TYPE] == type and row[self.VALUE] and row[self.ACTION] == action:
                blacklist.append(row[self.VALUE])
        return blacklist

    def _load(self, type, action, values):
        assert len(values) >= 0

        if len(values) == 0:
            return

        # found out the first blank line
        free = 0
        try:
            while self._data[free][self.TYPE]:
                free += 1
        except IndexError:
            # no blank line, create the first one by ourself.
            self.insertRows(self.rowCount(), 1)

        # create more blank lines, exclude the blank line which we already have
        if len(values) - 1 > 0:
            self.insertRows(free, len(values) - 1)

        # fill in these blank lines
        for value in values:
            self.setData(self.index(free, self.TYPE), type)
            self.setData(self.index(free, self.VALUE), value)
            self.setData(self.index(free, self.ACTION), action)
            free += 1

    def loadKeywordsBlacklist(self, blacklist):
        self._load(self.tr("Keyword"), self.tr("Block"), blacklist)

    def dumpKeywordsBlacklist(self):
        return self._dump(self.tr("Keyword"), self.tr("Block"))

    def loadUsersBlacklist(self, blacklist):
        self._load(self.tr("User"), self.tr("Block"), blacklist)

    def dumpUsersBlacklist(self):
        return self._dump(self.tr("User"), self.tr("Block"))

    def loadWordWarKeywords(self, keywords):
        self._load(self.tr("Keyword"), self.tr("Word War"), keywords)

    def dumpWordWarKeywords(self):
        return self._dump(self.tr("Keyword"), self.tr("Word War"))


class FilterTable(QtGui.QTableView):

    def __init__(self, parent=None):
        super(FilterTable, self).__init__(parent)
        self.setItemDelegateForColumn(0, ComboBoxDelegate(self))
        self.setItemDelegateForColumn(2, ComboBoxDelegate(self))

########NEW FILE########
__FILENAME__ = LoginInfo
#!/usr/bin/env python3
# vim: tabstop=8 expandtab shiftwidth=4 softtabstop=4

# WeCase -- This model implemented a LoginInfo() class to
#           avoid login a account more than once.
# Copyright (C) 2013, 2014 The WeCase Developers.
# License: GPL v3 or later.


from sys import argv
import os
import tempfile
from WeHack import pid_running


class LoginInfo():

    FILENAME = "WeCase_ec7a4ecb-696a-41df-8b72-c2d25ce215ec"

    def __init__(self):
        self._path = "/".join((tempfile.gettempdir(), self.FILENAME))

    def _open(self):
        # a+ in Python has a different behavior from POSIX (the man page of fopen),
        # initial file position for reading is at EOF instead of BOF.
        return open(self._path, "a+")

    @property
    def accounts(self):
        accounts = []

        with self._open() as f:
            f.seek(0)
            for line in f:
                line = line[:-1]  # \n
                account, pid, argv1 = line.split(" ")
                if pid_running(int(pid)) and argv1 == argv[1]:
                    accounts.append(account)
        return accounts

    def add_account(self, account):
        with self._open() as f:
            f.write("%s %d %s\n" % (account, os.getpid(), argv[1]))

########NEW FILE########
__FILENAME__ = LoginWindow
#!/usr/bin/env python3
# vim: tabstop=8 expandtab shiftwidth=4 softtabstop=4

# WeCase -- This file implemented LoginWindow.
# Copyright (C) 2013, 2014 The WeCase Developers.
# License: GPL v3 or later.


import webbrowser
from WeHack import async
from weibos.helper import SUCCESS, PASSWORD_ERROR, NETWORK_ERROR, UBAuthorize
from PyQt4 import QtCore, QtGui
from LoginWindow_ui import Ui_frm_Login
from WeCaseWindow import WeCaseWindow
import path
from time import sleep
from WConfigParser import WConfigParser
from LoginInfo import LoginInfo


class LoginWindow(QtGui.QDialog, Ui_frm_Login):

    SUCCESS = SUCCESS
    PASSWORD_ERROR = PASSWORD_ERROR
    NETWORK_ERROR = NETWORK_ERROR
    LOGIN_ALREADY = 10

    loginReturn = QtCore.pyqtSignal(int)

    def __init__(self, allow_auto_login=True, parent=None):
        super(LoginWindow, self).__init__(parent)
        self.allow_auto_login = allow_auto_login
        self.loadConfig()
        self.setupUi(self)
        self.setupSignals()
        self.err_count = 0

    def setupSignals(self):
        # Other signals defined in Designer.
        self.loginReturn.connect(self.checkLogin)
        self.chk_Remember.clicked.connect(self.uncheckAutoLogin)

    def accept(self):
        if self.chk_Remember.isChecked():
            self.passwd[str(self.username)] = str(self.password)
            self.last_login = str(self.username)
            # Because this is a model dialog,
            # closeEvent won't emit when we accept() the window, but will
            # emit when we reject() the window.
            self.saveConfig()
            self.setParent(None)
        wecase_main = WeCaseWindow()
        wecase_main.show()
        # Maybe users will logout, so reset the status
        LoginInfo().add_account(self.username)
        self.pushButton_log.setText(self.tr("GO!"))
        self.pushButton_log.setEnabled(True)
        self.done(True)

    def reject(self, status):
        if status in (self.NETWORK_ERROR, self.PASSWORD_ERROR) and self.err_count < 5:
            self.err_count += 1
            sleep(0.5)
            self.ui_authorize()
            return
        elif status == self.PASSWORD_ERROR:
            QtGui.QMessageBox.critical(None, self.tr("Authorize Failed!"),
                                       self.tr("Check your account and password"))
            self.err_count = 0
        elif status == self.NETWORK_ERROR:
            QtGui.QMessageBox.critical(None, self.tr("Network Error"),
                                       self.tr("Something wrong with the network, please try again."))
            self.err_count = 0
        elif status == self.LOGIN_ALREADY:
            QtGui.QMessageBox.critical(None, self.tr("Already Logged in"),
                                       self.tr("This account is already logged in."))

        self.pushButton_log.setText(self.tr("GO!"))
        self.pushButton_log.setEnabled(True)

    def checkLogin(self, status):
        if status == self.SUCCESS:
            self.accept()
        else:
            self.reject(status)

    def setupUi(self, widget):
        super(LoginWindow, self).setupUi(widget)
        self.show()
        self.txt_Password.setEchoMode(QtGui.QLineEdit.Password)
        self.cmb_Users.lineEdit().setPlaceholderText(self.tr("ID/Email/Phone"))
        self.cmb_Users.addItem(self.last_login)

        for username in list(self.passwd.keys()):
            if username == self.last_login:
                continue
            self.cmb_Users.addItem(username)

        if self.cmb_Users.currentText():
            self.chk_Remember.setChecked(True)
            self.setPassword(self.cmb_Users.currentText())

        if self.auto_login:
            self.chk_AutoLogin.setChecked(self.auto_login)
            self.login()

    def loadConfig(self):
        self.login_config = WConfigParser(path.myself_path + "WMetaConfig",
                                          path.config_path, "login")
        self.passwd = self.login_config.passwd
        self.last_login = self.login_config.last_login
        self.auto_login = self.login_config.auto_login and self.allow_auto_login

    def saveConfig(self):
        self.login_config.passwd = self.passwd
        self.login_config.last_login = self.last_login
        self.login_config.auto_login = self.chk_AutoLogin.isChecked()
        self.login_config.save()

    def login(self):
        self.pushButton_log.setText(self.tr("Login, waiting..."))
        self.pushButton_log.setEnabled(False)
        self.ui_authorize()

    def ui_authorize(self):
        self.username = self.cmb_Users.currentText()
        self.password = self.txt_Password.text()
        self.authorize(self.username, self.password)

    @async
    def authorize(self, username, password):
        if username in LoginInfo().accounts:
            self.loginReturn.emit(self.LOGIN_ALREADY)
            return

        result = UBAuthorize(username, password)
        if result == SUCCESS:
            self.loginReturn.emit(self.SUCCESS)
        elif result == PASSWORD_ERROR:
            self.loginReturn.emit(self.PASSWORD_ERROR)
        elif result == NETWORK_ERROR:
            self.loginReturn.emit(self.NETWORK_ERROR)

    def setPassword(self, username):
        if username in self.passwd.keys():
            self.txt_Password.setText(self.passwd[username])

    @QtCore.pyqtSlot(bool)
    def uncheckAutoLogin(self, checked):
        if not checked:
            self.chk_AutoLogin.setChecked(False)

    def openRegisterPage(self):
        webbrowser.open("http://weibo.com/signup/signup.php")

    def closeEvent(self, event):
        # HACK: When a user want to close this window, closeEvent will emit.
        # But if we don't have closeEvent, Qt will call reject(). We use
        # reject() to show the error message, so users will see the error and
        # they can not close this window. So just do nothing there to allow
        # users to close the window.
        pass

########NEW FILE########
__FILENAME__ = NewpostWindow
#!/usr/bin/env python3
# vim: tabstop=8 expandtab shiftwidth=4 softtabstop=4

# WeCase -- This file implemented NewpostWindow.
# Copyright (C) 2013, 2014 The WeCase Developers.
# License: GPL v3 or later.


from os.path import getsize
from WeHack import async
from PyQt4 import QtCore, QtGui
from weibo3 import APIError
from Tweet import TweetItem, UserItem, TweetUnderCommentModel, TweetRetweetModel
from Notify import Notify
from TweetUtils import tweetLength
from NewpostWindow_ui import Ui_NewPostWindow
from FaceWindow import FaceWindow
from TweetListWidget import TweetListWidget, SingleTweetWidget
from WeiboErrorHandler import APIErrorWindow
import const


class NewpostWindow(QtGui.QDialog, Ui_NewPostWindow):
    image = None
    apiError = QtCore.pyqtSignal(Exception)
    commonError = QtCore.pyqtSignal(str, str)
    sendSuccessful = QtCore.pyqtSignal()
    userClicked = QtCore.pyqtSignal(UserItem, bool)
    tagClicked = QtCore.pyqtSignal(str, bool)
    tweetRefreshed = QtCore.pyqtSignal()
    tweetRejected = QtCore.pyqtSignal()

    def __init__(self, action="new", tweet=None, parent=None):
        super(NewpostWindow, self).__init__(parent)
        self.setAttribute(QtCore.Qt.WA_QuitOnClose, False)
        self.client = const.client
        self.tweet = tweet
        self.action = action
        self.setupUi(self)
        self.textEdit.callback = self.mentions_suggest
        self.textEdit.mention_flag = "@"
        self.notify = Notify(timeout=1)
        self._sent = False
        self.apiError.connect(self.showException)
        self.sendSuccessful.connect(self.sent)
        self.commonError.connect(self.showErrorMessage)
        self.errorWindow = APIErrorWindow(self)

        if self.action not in ["new", "reply"]:
            self.tweetRefreshed.connect(self._create_tweetWidget)
            self.tweetRejected.connect(lambda: self.pushButton_send.setEnabled(False))
            self._refresh()

    def setupUi(self, widget):
        super(NewpostWindow, self).setupUi(widget)
        self.sendAction = QtGui.QAction(self)
        self.sendAction.triggered.connect(self.send)
        self.sendAction.setShortcut(QtGui.QKeySequence("Ctrl+Return"))
        self.addAction(self.sendAction)

        self.checkChars()
        self.setupButtons()

    def setupButtons(self):
        # Disabled is the default state of buttons
        self.pushButton_picture.setEnabled(False)
        self.chk_repost.setEnabled(False)
        self.chk_comment.setEnabled(False)
        self.chk_comment_original.setEnabled(False)

        if self.action == "new":
            assert (not self.tweet)  # Shouldn't have a tweet object.
            self.pushButton_picture.setEnabled(True)
        elif self.action == "retweet":
            self.chk_comment.setEnabled(True)
            if self.tweet.type == TweetItem.RETWEET:
                self.textEdit.setText(self.tweet.append_existing_replies())
                self.chk_comment_original.setEnabled(True)
        elif self.action == "comment":
            self.chk_repost.setEnabled(True)
            if self.tweet.type == TweetItem.RETWEET:
                self.chk_comment_original.setEnabled(True)
        elif self.action == "reply":
            self.chk_repost.setEnabled(True)
            if self.tweet.original.type == TweetItem.RETWEET:
                self.chk_comment_original.setEnabled(True)
        else:
            assert False

    @async
    def _refresh(self):
        # The read count is not a real-time value. So refresh it now.
        try:
            self.tweet.refresh()
        except APIError as e:
            self.errorWindow.raiseException.emit(e)
            self.tweetRejected.emit()
            return
        self.tweetRefreshed.emit()

    def _create_tweetWidget(self):
        if self.action == "comment" and self.tweet.comments_count:
            self.tweetWidget = SingleTweetWidget(self.tweet, ["image", "original"], self)
            self.replyModel = TweetUnderCommentModel(self.client.comments.show, self.tweet.id, self)
        elif self.action == "retweet" and self.tweet.retweets_count:
            if self.tweet:
                self.tweetWidget = SingleTweetWidget(self.tweet, ["image", "original"], self)
            elif self.tweet.original:
                self.tweetWidget = SingleTweetWidget(self.tweet.original, ["image", "original"], self)
            self.replyModel = TweetRetweetModel(self.client.statuses.repost_timeline, self.tweet.id, self)
        else:
            return
        self.replyModel.load()

        self.splitter = QtGui.QSplitter(self)
        self.splitter.setOrientation(QtCore.Qt.Vertical)
        self.verticalLayout.insertWidget(0, self.splitter)
        self.tweetWidget.setSizePolicy(QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Expanding)
        self.splitter.addWidget(self.tweetWidget)

        self.commentsWidget = TweetListWidget(self, ["image", "original"])
        self.commentsWidget.setModel(self.replyModel)
        self.commentsWidget.scrollArea.setMinimumSize(20, 200)
        self.commentsWidget.userClicked.connect(self.userClicked)
        self.commentsWidget.tagClicked.connect(self.tagClicked)
        self.splitter.addWidget(self.commentsWidget)
        self.splitter.addWidget(self.textEdit)

    def mentions_suggest(self, text):
        ret_users = []
        try:
            word = text.split(' ')[-1]
            word = word.split('@')[-1]
        except IndexError:
            return []
        if not word.strip():
            return []
        users = self.client.search.suggestions.at_users.get(q=word, type=0)
        for user in users:
            ret_users.append("@" + user['nickname'])
        return ret_users

    def sent(self):
        self._sent = True
        self.close()

    def send(self):
        self.pushButton_send.setEnabled(False)
        if self.action == "new":
            self.new()
        elif self.action == "retweet":
            self.retweet()
        elif self.action == "comment":
            self.comment()
        elif self.action == "reply":
            self.reply()
        else:
            # If action is in other types, it must be a mistake.
            assert False

    @async
    def retweet(self):
        text = str(self.textEdit.toPlainText())
        comment = int(self.chk_comment.isChecked())
        comment_ori = int(self.chk_comment_original.isChecked())
        try:
            self.tweet.retweet(text, comment, comment_ori)
        except APIError as e:
            self.apiError.emit(e)
            return
        self.notify.showMessage(self.tr("WeCase"), self.tr("Retweet Success!"))
        self.sendSuccessful.emit()

    @async
    def comment(self):
        text = str(self.textEdit.toPlainText())
        retweet = int(self.chk_repost.isChecked())
        comment_ori = int(self.chk_comment_original.isChecked())
        try:
            self.tweet.comment(text, comment_ori, retweet)
        except APIError as e:
            self.apiError.emit(e)
            return
        self.notify.showMessage(self.tr("WeCase"), self.tr("Comment Success!"))
        self.sendSuccessful.emit()

    @async
    def reply(self):
        text = str(self.textEdit.toPlainText())
        comment_ori = int(self.chk_comment_original.isChecked())
        retweet = int(self.chk_repost.isChecked())
        try:
            self.tweet.reply(text, comment_ori, retweet)
        except APIError as e:
            self.apiError.emit(e)
            return
        self.notify.showMessage(self.tr("WeCase"), self.tr("Reply Success!"))
        self.sendSuccessful.emit()

    @async
    def new(self):
        text = str(self.textEdit.toPlainText())

        try:
            if self.image:
                try:
                    if getsize(self.image) > const.MAX_IMAGE_BYTES:
                        raise ValueError
                    with open(self.image, "rb") as image:
                        self.client.statuses.upload.post(status=text, pic=image)
                except (OSError, IOError):
                    self.commonError.emit(self.tr("File not found"),
                                          self.tr("No such file: %s")
                                          % self.image)
                    self.addImage()  # In fact, remove image...
                    return
                except ValueError:
                    self.commonError.emit(self.tr("Too large size"),
                                          self.tr("This image is too large to upload: %s")
                                          % self.image)
                    self.addImage()  # In fact, remove image...
                    return
            else:
                self.client.statuses.update.post(status=text)

            self.notify.showMessage(self.tr("WeCase"),
                                    self.tr("Tweet Success!"))
            self.sendSuccessful.emit()
        except APIError as e:
            self.apiError.emit(e)
            return

        self.image = None

    def addImage(self):
        ACCEPT_TYPE = self.tr("Images") + "(*.png *.jpg *.jpeg *.bmp *.gif)"
        if self.image:
            self.image = None
            self.pushButton_picture.setText(self.tr("&Picture"))
        else:
            self.image = QtGui.QFileDialog.getOpenFileName(self,
                                                           self.tr("Choose a"
                                                                   " image"),
                                                           filter=ACCEPT_TYPE)
            # user may cancel the dialog, so check again
            if self.image:
                self.pushButton_picture.setText(self.tr("Remove the picture"))
        self.textEdit.setFocus()

    def showException(self, e):
        if "Text too long" in str(e):
            QtGui.QMessageBox.warning(None, self.tr("Text too long!"),
                                      self.tr("Please remove some text."))
        else:
            self.errorWindow.raiseException.emit(e)
        self.pushButton_send.setEnabled(True)

    def showErrorMessage(self, title, text):
        QtGui.QMessageBox.warning(self, title, text)

    def showSmiley(self):
        wecase_smiley = FaceWindow()
        if wecase_smiley.exec_():
            self.textEdit.textCursor().insertText(wecase_smiley.faceName)
        self.textEdit.setFocus()

    def checkChars(self):
        """Check textEdit's characters.
        If it larger than 140, Send Button will be disabled
        and label will show red chars."""

        text = self.textEdit.toPlainText()
        numLens = 140 - tweetLength(text)
        if numLens == 140 and (not self.action == "retweet"):
            # you can not send empty tweet, except retweet
            self.pushButton_send.setEnabled(False)
        elif numLens >= 0:
            # length is okay
            self.label.setStyleSheet("color:black;")
            self.pushButton_send.setEnabled(True)
        else:
            # text is too long
            self.label.setStyleSheet("color:red;")
            self.pushButton_send.setEnabled(False)
        self.label.setText(str(numLens))

    def reject(self):
        self.close()

    def closeEvent(self, event):
        # We have unsend text.
        if (not self._sent) and (self.textEdit.toPlainText()):
            choice = QtGui.QMessageBox.question(
                self, self.tr("Close?"),
                self.tr("All unpost text will lost."),
                QtGui.QMessageBox.Yes,
                QtGui.QMessageBox.No)
            if choice == QtGui.QMessageBox.No:
                event.ignore()
            else:
                self.setParent(None)

########NEW FILE########
__FILENAME__ = Notify
#!/usr/bin/env python3
# vim: tabstop=8 expandtab shiftwidth=4 softtabstop=4

# WeCase -- This file implemented Notify.
# Copyright (C) 2013, 2014 The WeCase Developers.
# License: GPL v3 or later.


from PyQt4 import QtCore
import path

try:
    import notify2 as pynotify
    from dbus.exceptions import DBusException
    pynotify.init("WeCase")
except ImportError:
    import nullNotify as pynotify
except DBusException:
    import nullNotify as pynotify


class Notify(QtCore.QObject):
    image = path.icon_path

    def __init__(self, appname=QtCore.QObject().tr("WeCase"), timeout=5):
        super(Notify, self).__init__()

        pynotify.init(appname)
        self.timeout = timeout
        self.n = pynotify.Notification(appname)

    def showMessage(self, title, text):
        try:
            self.n.update(title, text, self.image)
            self.n.set_timeout(self.timeout * 1000)
            self.n.show()
        except DBusException:
            return False
        return True

########NEW FILE########
__FILENAME__ = nullNotify
#!/usr/bin/env python3
# vim: tabstop=8 expandtab shiftwidth=4 softtabstop=4

# WeCase -- This model implemented a dummy notification interface for
#           unsupperted platforms.
# Copyright (C) 2013, 2014 The WeCase Developers.
# License: GPL v3 or later.


from WeHack import UNUSED


def init(*args):
    UNUSED(args)
    return True


class Notification():
    def __init__(self, *args):
        pass

    def update(self, *args):
        pass

    def set_timeout(self, *args):
        pass

    def show(self):
        pass

########NEW FILE########
__FILENAME__ = SettingWindow
#!/usr/bin/env python3
# vim: tabstop=8 expandtab shiftwidth=4 softtabstop=4

# WeCase -- This file implemented SettingWindow.
# Copyright (C) 2013, 2014 The WeCase Developers.
# License: GPL v3 or later.


from PyQt4 import QtCore, QtGui
from SettingWindow_ui import Ui_SettingWindow
from FilterTable import FilterTableModel
import path
from WConfigParser import WConfigParser
from WeHack import async, start, getDirSize, clearDir


class WeSettingsWindow(QtGui.QDialog, Ui_SettingWindow):

    cacheCleared = QtCore.pyqtSignal()

    def __init__(self, parent=None):
        super(WeSettingsWindow, self).__init__(parent)
        self.setupUi(self)
        self.setupModel()
        self.setupSignal()
        self.loadConfig()
        self.cacheCleared.connect(self.showSize)
        self.needRestart = False

    def setupUi(self, widget):
        super(WeSettingsWindow, self).setupUi(widget)
        self.filterTable.horizontalHeader().setResizeMode(QtGui.QHeaderView.Stretch)
        self.showSize()

    def setupModel(self):
        self.filterModel = FilterTableModel(self.filterTable)
        self.filterTable.setModel(self.filterModel)

    def setupSignal(self):
        self.addRuleButton.clicked.connect(self.addRule)
        self.removeRuleButton.clicked.connect(self.removeRule)

    def addRule(self):
        self.needRestart = True
        self.filterModel.insertRows(self.filterModel.rowCount(), 1)

    def removeRule(self):
        self.needRestart = True
        row = self.filterTable.currentIndex().row()
        if row >= 0:
            self.filterModel.removeRows(row, 1)

    def showSize(self):
        self.cacheSizeLabel.setText(self.getHumanReadableCacheSize())

    def getHumanReadableCacheSize(self):
        raw_bytes = getDirSize(path.cache_path)
        megabytes_str = "%.1f MiB" % (raw_bytes / 1000000)
        return megabytes_str

    def transformInterval(self, sliderValue):
        return sliderValue // 60, sliderValue % 60

    def setIntervalText(self, sliderValue):
        self.intervalLabel.setText(self.tr("%i min %i sec") %
                                   (self.transformInterval(sliderValue)))

    def setTimeoutText(self, sliderValue):
        self.timeoutLabel.setText(self.tr("%i sec") % sliderValue)

    def loadConfig(self):
        self.config = WConfigParser(path.myself_path + "WMetaConfig",
                                    path.config_path, "main")

        self.intervalSlider.setValue(self.config.notify_interval)
        self.setIntervalText(self.intervalSlider.value())
        self.timeoutSlider.setValue(self.config.notify_timeout)
        self.setTimeoutText(self.timeoutSlider.value())
        self.commentsChk.setChecked(self.config.remind_comments)
        self.mentionsChk.setChecked(self.config.remind_mentions)
        self.filterModel.loadKeywordsBlacklist(self.config.tweetsKeywordsBlacklist)
        self.filterModel.loadUsersBlacklist(self.config.usersBlacklist)
        self.filterModel.loadWordWarKeywords(self.config.wordWarKeywords)
        self.blockWordwarsCheckBox.setChecked(self.config.blockWordwars)
        self.maxRetweetsCheckBox.setChecked(self.config.maxRetweets != -1)
        self.maxRetweetsLimitLineEdit.setText("" if self.config.maxRetweets == -1 else str(self.config.maxRetweets))
        self.maxTweetsPerUserCheckBox.setChecked(self.config.maxTweetsPerUser != -1)
        self.maxTweetsPerUserLimitLineEdit.setText("" if self.config.maxTweetsPerUser == -1 else str(self.config.maxTweetsPerUser))
        self.regexCheckbox.setChecked(self.config.keywordsAsRegex)

    def saveConfig(self):
        self.config.notify_interval = str(self.intervalSlider.value())
        self.config.notify_timeout = str(self.timeoutSlider.value())
        self.config.remind_comments = str(self.commentsChk.isChecked())
        self.config.remind_mentions = str(self.mentionsChk.isChecked())
        self.config.tweetsKeywordsBlacklist = self.filterModel.dumpKeywordsBlacklist()
        self.config.usersBlacklist = self.filterModel.dumpUsersBlacklist()
        self.config.wordWarKeywords = self.filterModel.dumpWordWarKeywords()
        self.config.blockWordwars = str(self.blockWordwarsCheckBox.isChecked())
        self.config.maxRetweets = str(-1 if not self.maxRetweetsCheckBox.isChecked() else int(self.maxRetweetsLimitLineEdit.text()))
        self.config.maxTweetsPerUser = str(-1 if not self.maxTweetsPerUserCheckBox.isChecked() else int(self.maxTweetsPerUserLimitLineEdit.text()))
        self.config.keywordsAsRegex = str(self.regexCheckbox.isChecked())
        self.config.save()

    def accept(self):
        self.saveConfig()
        if self.needRestart:
            QtGui.QMessageBox.information(
                self, self.tr("Restart"),
                self.tr("Settings need to restart WeCase to take effect."))
        self.done(True)

    def reject(self):
        self.done(False)

    @async
    def clearCache(self):
        clearDir(path.cache_path)
        self.needRestart = True
        self.cacheCleared.emit()

    def viewCache(self):
        start(path.cache_path)

########NEW FILE########
__FILENAME__ = SimpleLabel
#!/usr/bin/env python3
# vim: tabstop=8 expandtab shiftwidth=4 softtabstop=4

# WeCase -- This file implemented a very simple QLabel-like label.
#
#           The label designed as the time label in SingleTweetWidget,
#           which needs to create many instance and update very often.
#           Therefore, we made it as simple as possible,
#           there were hardcoded values and depends on overmuch assertion
#           condition to work correctly. It can reduce ~5 MB of memory usage
#           when WeCase just started.
#
#           DO NOT FOLLOW THIS PRACTICE in your code or IN THE OTHER PARTS
#           OF WeCase. FOREVER!
# Copyright: (C) 2013, 2014 The WeCase Developers.
# License: GPL v3 or later.


from PyQt4 import QtCore, QtGui
from WeHack import openLink


class SimpleLabel(QtGui.QWidget):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMouseTracking(True)

        self._link = ""

        self._doc = QtGui.QTextDocument()
        self._doc.setIndentWidth(0)
        self._doc.setDocumentMargin(0)

        self._ctx = QtGui.QAbstractTextDocumentLayout.PaintContext()

    def mousePressEvent(self, e):
        openLink(self._link)

    def mouseMoveEvent(self, e):
        if self.rect().contains(e.pos()):
            self.setCursor(QtCore.Qt.PointingHandCursor)
        else:
            self.setCursor(QtCore.Qt.ArrowCursor)

    def setText(self, html):
        # Assert:
        # The text is an html tag: <a href='$0'>$1</a>,
        # $0 never changes, because it is the link of a tweet,
        # $1 changes very often, because it is a timer which is counts since
        # the creation time.
        self._doc.setHtml(html)
        self.adjustSize()
        self.repaint()

        if self._link:
            # $0 never changes, don't spend CPU time on re-counting.
            return

        # len("<a href='") == 9
        # 9 + len("http://weibo.com/") == 26
        end = 26
        rest = html[end:]
        for char in rest:
            if char == "'":
                break
            end += 1
        self._link = html[9:end]

    def paintEvent(self, e):
        # parent paintEvent() will hide current tooltip, don't let it happens.
        # super().paintEvent(e)
        painter = QtGui.QPainter(self)
        self._doc.documentLayout().draw(painter, self._ctx)

    def sizeHint(self):
        return QtCore.QSize(self._doc.size().width(), self._doc.size().height())

########NEW FILE########
__FILENAME__ = Tweet
#!/usr/bin/env python3
# vim: tabstop=8 expandtab shiftwidth=4 softtabstop=4

# WeCase -- This model implemented Model and Item for tweets
# Copyright (C) 2013, 2014 The WeCase Developers.
# License: GPL v3 or later.


from PyQt4 import QtCore
from datetime import datetime
from TweetUtils import get_mid
from WTimeParser import WTimeParser as time_parser
from WeHack import async, UNUSED
from TweetUtils import tweetLength
import re
import const


class TweetSimpleModel(QtCore.QAbstractListModel):
    rowInserted = QtCore.pyqtSignal(int)

    def __init__(self, parent=None):
        super(TweetSimpleModel, self).__init__(parent)
        self._tweets = []
        self._tweetKeywordBlacklist = []
        self._usersBlackList = []

    def appendRow(self, item):
        self.insertRow(self.rowCount(), item)

    def appendRows(self, items):
        self.beginInsertRows(QtCore.QModelIndex(), self.rowCount(), self.rowCount() + len(items) - 1)
        for item in items:
            self._tweets.insert(self.rowCount(), TweetItem(item))
            self.rowInserted.emit(self.rowCount())
        self.endInsertRows()

    def clear(self):
        self._tweets = []

    def data(self, index, role):
        return self._tweets[index.row()].data(role)

    def get_item(self, row):
        return self._tweets[row]

    def insertRow(self, row, item):
        self.beginInsertRows(QtCore.QModelIndex(), row, row)
        self._tweets.insert(row, item)
        self.rowInserted.emit(row)
        self.endInsertRows()

    def insertRows(self, row, items):
        self.beginInsertRows(QtCore.QModelIndex(), row, row + len(items) - 1)
        for item in items:
            self._tweets.insert(row, TweetItem(item))
            self.rowInserted.emit(row)
        self.endInsertRows()

    def rowCount(self, parent=QtCore.QModelIndex()):
        return len(self._tweets)


class TweetTimelineBaseModel(TweetSimpleModel):

    timelineLoaded = QtCore.pyqtSignal()
    nothingLoaded = QtCore.pyqtSignal()

    def __init__(self, timeline=None, parent=None):
        super(TweetTimelineBaseModel, self).__init__(parent)
        self.timeline = timeline
        self.lock = False

    def timeline_get(self):
        raise NotImplementedError

    def timeline_new(self):
        raise NotImplementedError

    def timeline_old(self):
        raise NotImplementedError

    def first_id(self):
        assert self._tweets
        return int(self._tweets[0].id)

    def last_id(self):
        assert self._tweets
        return int(self._tweets[-1].id)

    @async
    def _common_get(self, timeline_func, pos):
        if self.lock:
            return
        self.lock = True

        # timeline is just a pointer to the method.
        # We are in another thread now, call it. UI won't freeze.
        timeline = timeline_func()

        if not timeline:
            self.nothingLoaded.emit()

        if pos == -1:
            self.appendRows(timeline)
        else:
            self.insertRows(pos, timeline)
        self.lock = False

    def load(self):
        self.page = 1
        timeline = self.timeline_get
        self._common_get(timeline, -1)

    def new(self):
        if self._tweets:
            timeline = self.timeline_new
            self._common_get(timeline, 0)
            self.timelineLoaded.emit()
        else:
            self.load()

    def next(self):
        if self._tweets:
            timeline = self.timeline_old
            self._common_get(timeline, -1)
        else:
            self.load()


class TweetCommonModel(TweetTimelineBaseModel):

    def __init__(self, timeline=None, parent=None):
        super(TweetCommonModel, self).__init__(timeline, parent)

    def timeline_get(self, page=1):
        timeline = self.timeline.get(page=page).statuses
        return timeline

    def timeline_new(self):
        timeline = self.timeline.get(since_id=self.first_id()).statuses[::-1]
        return timeline

    def timeline_old(self):
        timeline = self.timeline.get(max_id=self.last_id()).statuses
        timeline = timeline[1::]
        return timeline


class TweetUserModel(TweetTimelineBaseModel):

    def __init__(self, timeline, uid, parent=None):
        super(TweetUserModel, self).__init__(timeline, parent)
        self._uid = uid

    def timeline_get(self, page=1):
        timeline = self.timeline.get(page=page, uid=self._uid).statuses
        return timeline

    def timeline_new(self):
        timeline = self.timeline.get(since_id=self.first_id(),
                                     uid=self._uid).statuses[::-1]
        return timeline

    def timeline_old(self):
        timeline = self.timeline.get(max_id=self.last_id(), uid=self._uid).statuses
        timeline = timeline[1::]
        return timeline

    def uid(self):
        return self._uid


class TweetCommentModel(TweetTimelineBaseModel):

    def __init__(self, timeline=None, parent=None):
        super(TweetCommentModel, self).__init__(timeline, parent)
        self.page = 0

    def timeline_get(self, page=1):
        timeline = self.timeline.get(page=page).comments
        return timeline

    def timeline_new(self):
        timeline = self.timeline.get(since_id=self.first_id()).comments[::-1]
        return timeline

    def timeline_old(self):
        timeline = self.timeline.get(max_id=self.last_id()).comments
        timeline = timeline[1::]
        return timeline


class TweetUnderCommentModel(TweetTimelineBaseModel):
    def __init__(self, timeline=None, id=0, parent=None):
        super(TweetUnderCommentModel, self).__init__(timeline, parent)
        self.id = id

    def timeline_get(self, page=1):
        timeline = self.timeline.get(id=self.id, page=page).comments
        return timeline

    def timeline_new(self):
        timeline = self.timeline.get(id=self.id, since_id=self.first_id()).comments[::-1]
        return timeline

    def timeline_old(self):
        timeline = self.timeline.get(id=self.id, max_id=self.last_id()).comments
        timeline = timeline[1::]
        return timeline


class TweetRetweetModel(TweetTimelineBaseModel):
    def __init__(self, timeline=None, id=0, parent=None):
        super(TweetRetweetModel, self).__init__(timeline, parent)
        self.id = id

    def timeline_get(self, page=1):
        try:
            timeline = self.timeline.get(id=self.id, page=page).reposts
        except AttributeError:
            # Issue 115: So the censorship, fuck you!
            timeline = []
        return timeline

    def timeline_new(self):
        timeline = self.timeline.get(id=self.id, since_id=self.first_id()).reposts[::-1]
        return timeline

    def timeline_old(self):
        timeline = self.timeline.get(id=self.id, max_id=self.last_id()).reposts
        timeline = timeline[1::]
        return timeline


class TweetTopicModel(TweetTimelineBaseModel):

    def __init__(self, timeline, topic, parent=None):
        super(TweetTopicModel, self).__init__(timeline, parent)
        self._topic = topic.replace("#", "")
        self.page = 1

    def timeline_get(self):
        timeline = self.timeline.get(q=self._topic, page=self.page).statuses
        return timeline

    def timeline_new(self):
        timeline = self.timeline.get(q=self._topic, page=1).statuses
        for tweet in timeline:
            if TweetItem(tweet).id == self.first_id():
                return list(reversed(timeline[:timeline.index(tweet)]))
        return timeline

    def timeline_old(self):
        self.page += 1
        return self.timeline_get()

    def topic(self):
        return self._topic


class TweetFilterModel(QtCore.QAbstractListModel):

    rowInserted = QtCore.pyqtSignal(int)
    timelineLoaded = QtCore.pyqtSignal()
    nothingLoaded = QtCore.pyqtSignal()

    def __init__(self, parent=None):
        super(TweetFilterModel, self).__init__(parent)
        self._model = None
        self._appearInfo = {}
        self._userInfo = {}
        self._tweets = []
        self._wordWarKeywords = []
        self._blockWordwars = False
        self._maxTweetsPerUser = -1
        self._maxRetweets = -1
        self._keywordsAsRegexs = False

    def model(self):
        return self._model

    def setModel(self, model):
        self._model = model
        self._model.timelineLoaded.connect(self.timelineLoaded)
        self._model.nothingLoaded.connect(self.nothingLoaded)
        self._model.rowsInserted.connect(self._rowsInserted)

    def get_item(self, index):
        return self._tweets[index]

    def setKeywordsAsRegexs(self, state):
        self._keywordsAsRegexs = bool(state)

    def setTweetsKeywordsBlacklist(self, blacklist):
        self._tweetKeywordBlacklist = blacklist

    def setWordWarKeywords(self, blacklist):
        self._wordWarKeywords = blacklist

    def setUsersBlacklist(self, blacklist):
        self._usersBlackList = blacklist

    def setBlockWordwars(self, state):
        self._blockWordwars = bool(state)

    def setMaxTweetsPerUser(self, max):
        self._maxTweetsPerUser = max

    def setMaxRetweets(self, max):
        self._maxRetweets = max

    def _inBlacklist(self, tweet):
        if not tweet:
            return False
        elif self._inBlacklist(tweet.original):
            return True

        # Put all your statements at here
        if tweet.withKeywords(self._tweetKeywordBlacklist, self._keywordsAsRegexs):
            return True
        if tweet.author and (tweet.author.name in self._usersBlackList):
            return True
        return False

    def maxTweetsPerUserFilter(self, items):
        new_items = []

        for item in items:
            if not item.author.id in self._userInfo:
                self._userInfo[item.author.id] = 0

            if self._userInfo[item.author.id] > self._maxTweetsPerUser:
                continue
            else:
                self._userInfo[item.author.id] += 1
                new_items.append(item)

        return new_items

    def maxRetweetsFilter(self, items):
        new_items = []

        for item in items:
            if not item.original:
                continue

            if not item.original.id in self._appearInfo:
                self._appearInfo[item.original.id] = {"count": 0, "wordWarKeywords": 0}

            if self._appearInfo[item.original.id]["count"] > self._maxRetweets:
                continue
            else:
                self._appearInfo[item.original.id]["count"] += 1
                new_items.append(item)

        return new_items

    def wordWarFilter(self, items):
        # If a same tweet retweeted more than 3 times, and
        # there are three retweets include insulting keywords,
        # then it is a word-war-tweet. Block it and it's retweets.
        new_items = []

        for item in items:
            if not item.original:
                continue

            if not item.original.id in self._appearInfo:
                self._appearInfo[item.original.id] = {"count": 0, "wordWarKeywords": 0}
            info = self._appearInfo[item.original.id]
            info["count"] += 1
            if item.withKeywords(self._wordWarKeywords, self._keywordsAsRegexs):
                info["wordWarKeywords"] += 1
            self._appearInfo[item.original.id] = info

        for item in items:
            if item.original:
                id = item.original.id
            else:
                id = item.id

            try:
                info = self._appearInfo[id]
            except KeyError:
                new_items.append(item)
                continue

            if info["count"] >= 3 and info["wordWarKeywords"] >= 3:
                continue
            else:
                new_items.append(item)

        return new_items

    def filter(self, items):
        new_items = []
        for item in items:
            if self._inBlacklist(item):
                continue
            else:
                new_items.append(item)

        if self._blockWordwars:
            new_items = self.wordWarFilter(new_items)
        if self._maxRetweets != -1:
            new_items = self.maxRetweetsFilter(new_items)
        if self._maxTweetsPerUser != -1:
            new_items = self.maxTweetsPerUserFilter(new_items)

        return new_items

    def _rowsInserted(self, parent, start, end):
        tweets = []
        for index in range(start, end + 1):
            item = self._model.get_item(index)
            tweets.append(item)

        filteredTweets = self.filter(tweets)
        while start != 0 and tweets and not filteredTweets:
            self._model.next()
            return

        if start == 0:
            row = 0
        else:
            row = self.rowCount()

        self.beginInsertRows(QtCore.QModelIndex(), row, row + len(filteredTweets) - 1)
        for index, tweet in enumerate(filteredTweets):
            if start == 0:
                self._tweets.insert(index, tweet)
            else:
                self._tweets.append(tweet)
        self.endInsertRows()

    def rowCount(self, parent=QtCore.QModelIndex()):
        return len(self._tweets)

    def __getattr__(self, attr):
        return eval("self._model.%s" % attr)


class UserItem(QtCore.QObject):
    def __init__(self, item, parent=None):
        UNUSED(parent)
        # HACK: Ignore parent, can't create a child with different thread.
        # Where is the thread? I don't know...
        super(UserItem, self).__init__()
        self._data = item
        self.client = const.client

        if self._data.get('id') and self._data.get('name'):
            return
        else:
            self._loadCompleteInfo()

    def _loadCompleteInfo(self):
        if self._data.get('id'):
            self._data = self.client.users.show.get(uid=self._data.get('id'))
        elif self._data.get('name'):
            self._data = self.client.users.show.get(screen_name=self._data.get('name'))

    @QtCore.pyqtProperty(int, constant=True)
    def id(self):
        return self._data.get('id')

    @QtCore.pyqtProperty(str, constant=True)
    def name(self):
        return self._data.get('name')

    @QtCore.pyqtProperty(str, constant=True)
    def avatar(self):
        return self._data.get('profile_image_url')

    @QtCore.pyqtProperty(str, constant=True)
    def verify_type(self):
        typ = self._data.get("verified_type")
        if typ == 0:
            return "personal"
        elif typ in [1, 2, 3, 4, 5, 6, 7]:
            return "organization"
        else:
            return None

    @QtCore.pyqtProperty(str, constant=True)
    def verify_reason(self):
        return self._data.get("verified_reason")


class TweetItem(QtCore.QObject):
    TWEET = 0
    RETWEET = 1
    COMMENT = 2

    def __init__(self, data={}, parent=None):
        super(TweetItem, self).__init__(parent)
        self._data = data
        self.client = const.client
        self.__isFavorite = False

    @QtCore.pyqtProperty(int, constant=True)
    def type(self):
        if "retweeted_status" in self._data:
            return self.RETWEET
        elif "status" in self._data:
            return self.COMMENT
        else:
            return self.TWEET

    @QtCore.pyqtProperty(int, constant=True)
    def id(self):
        return self._data.get('id')

    @QtCore.pyqtProperty(str, constant=True)
    def mid(self):
        decimal_mid = str(self._data.get('mid'))
        encode_mid = get_mid(decimal_mid)
        return encode_mid

    @QtCore.pyqtProperty(str, constant=True)
    def url(self):
        try:
            uid = self._data['user']['id']
            mid = get_mid(self._data['mid'])
        except KeyError:
            # Sometimes Sina's API doesn't return user
            # when our tweet is deeply nested. Just forgot it.
            return ""
        return 'http://weibo.com/%s/%s' % (uid, mid)

    @QtCore.pyqtProperty(QtCore.QObject, constant=True)
    def author(self):
        if "user" in self._data:
            self._user = UserItem(self._data.get('user'), self)
            return self._user
        else:
            return None

    @QtCore.pyqtProperty(str, constant=True)
    def time(self):
        if not self.timestamp:
            return

        passedSeconds = self.passedSeconds
        if passedSeconds < 0:
            return self.tr("Future!")
        elif passedSeconds < 60:
            return self.tr("%.0fs ago") % passedSeconds
        elif passedSeconds < 3600:
            return self.tr("%.0fm ago") % (passedSeconds / 60)
        elif passedSeconds < 86400:
            return self.tr("%.0fh ago") % (passedSeconds / 3600)
        else:
            return self.tr("%.0fd ago") % (passedSeconds / 86400)

    @QtCore.pyqtProperty(str, constant=True)
    def timestamp(self):
        return self._data.get('created_at')

    @QtCore.pyqtProperty(str, constant=True)
    def text(self):
        return self._data.get('text')

    @QtCore.pyqtProperty(QtCore.QObject, constant=True)
    def original(self):
        try:
            return self._original
        except AttributeError:
            pass

        if self.type == self.RETWEET:
            self._original = TweetItem(self._data.get('retweeted_status'))
            return self._original
        elif self.type == self.COMMENT:
            self._original = TweetItem(self._data.get('status'))
            return self._original
        else:
            return None

    @QtCore.pyqtProperty(list, constant=True)
    def thumbnail_pic(self):
        # Checkout Issue #101.
        results = []

        pic_urls = self._data.get("pic_urls")
        if pic_urls:
            for url in pic_urls:
                results.append(url['thumbnail_pic'])
            return results

        pic_ids = self._data.get("pic_ids")
        if pic_ids:
            for id in pic_ids:
                results.append("http://ww1.sinaimg.cn/thumbnail/%s" % id)
            return results

        pic_fallback = self._data.get("thumbnail_pic")
        if pic_fallback:
            results.append(results)
            return results

        return None

    @QtCore.pyqtProperty(str, constant=True)
    def original_pic(self):
        return self._data.get('original_pic')

    @QtCore.pyqtProperty(str, constant=True)
    def source(self):
        return self._data.get('source')

    @QtCore.pyqtProperty(int, constant=True)
    def retweets_count(self):
        return self._data.get('reposts_count', 0)

    @QtCore.pyqtProperty(int, constant=True)
    def comments_count(self):
        return self._data.get('comments_count', 0)

    @QtCore.pyqtProperty(int, constant=True)
    def passedSeconds(self):
        create = time_parser().parse(self.timestamp)
        create_utc = (create - create.utcoffset()).replace(tzinfo=None)
        now_utc = datetime.utcnow()

        # Always compare UTC time, do NOT compare LOCAL time.
        # See http://coolshell.cn/articles/5075.html for more details.
        if now_utc < create_utc:
            # datetime do not support negative numbers
            return -1
        else:
            passedSeconds = (now_utc - create_utc).total_seconds()
            return passedSeconds

    def isFavorite(self):
        return self.__isFavorite

    def _cut_off(self, text):
        cut_text = ""
        for char in text:
            if tweetLength(cut_text) >= 140:
                break
            else:
                cut_text += char
        return cut_text

    def append_existing_replies(self, text=""):
        if self.original.original:
            text += "//@%s:%s//@%s:%s" % (
                    self.author.name, self.text,
                    self.original.author.name, self.original.text)
        else:
            text += "//@%s:%s" % (self.author.name, self.text)
        return text

    def reply(self, text, comment_ori=False, retweet=False):
        self.client.comments.reply.post(id=self.original.id, cid=self.id,
                                        comment=text, comment_ori=int(comment_ori))
        if retweet:
            text = self.append_existing_replies(text)
            text = self._cut_off(text)
            self.original.retweet(text)

    def retweet(self, text, comment=False, comment_ori=False):
        self.client.statuses.repost.post(id=self.id, status=text,
                                         is_comment=int(comment + comment_ori * 2))

    def comment(self, text, comment_ori=False, retweet=False):
        self.client.comments.create.post(id=self.id, comment=text,
                                         comment_ori=int(comment_ori))
        if retweet:
            self.retweet(text)

    def delete(self):
        if self.type in [self.TWEET, self.RETWEET]:
            self.client.statuses.destroy.post(id=self.id)
        elif self.type == self.COMMENT:
            self.client.comments.destroy.post(cid=self.id)

    def setFavorite(self, state):
        if self.type not in [self.TWEET, self.RETWEET]:
            raise TypeError

        if state:
            assert(not self.__isFavorite)
            self.client.favorites.create.post(id=self.id)
            self.__isFavorite = True
        else:
            assert(self.__isFavorite)
            self.client.favorites.destroy.post(id=self.id)
            self.__isFavorite = False

    def setFavoriteForce(self, state):
        self.__isFavorite = bool(state)

    def refresh(self):
        if self.type in [self.TWEET, self.RETWEET]:
            self._data = self.client.statuses.show.get(id=self.id)

    def _withKeyword(self, keyword):
        if keyword in self.text:
            return True
        else:
            return False

    def _withKeywords(self, keywords):
        for keyword in keywords:
            if self._withKeyword(keyword):
                return True
        return False

    def _withRegex(self, pattern):
        try:
            result = re.match(pattern, self.text)
        except (ValueError, TypeError):
            return False

        if result:
            return True
        else:
            return False

    def _withRegexs(self, patterns):
        for pattern in patterns:
            if self._withRegex(pattern):
                return True
        return False

    def withKeyword(self, pattern, regex=False):
        if regex:
            return self._withRegex(pattern)
        else:
            return self._withKeyword(pattern)

    def withKeywords(self, patterns, regex=False):
        if regex:
            return self._withRegexs(patterns)
        else:
            return self._withKeywords(patterns)

########NEW FILE########
__FILENAME__ = TweetListWidget
#!/usr/bin/env python3
# vim: tabstop=8 expandtab shiftwidth=4 softtabstop=4

# WeCase -- This file implemented the most widgets for viewing tweets.
# Copyright (C) 2013, 2014 The WeCase Developers.
# License: GPL v3 or later.


import re
from time import sleep
from WeHack import async, start, UNUSED, openLink
from weibo3 import APIError
from PyQt4 import QtCore, QtGui
from Tweet import TweetItem, UserItem
from WIconLabel import WIconLabel
from WTweetLabel import WTweetLabel
from WAvatarLabel import WAvatarLabel
from WImageLabel import WImageLabel
from WSwitchLabel import WSwitchLabel
from SimpleLabel import SimpleLabel
import const
from path import cache_path
from WeRuntimeInfo import WeRuntimeInfo
from WObjectCache import WObjectCache
from AsyncFetcher import AsyncFetcher
from Face import FaceModel
from WeiboErrorHandler import APIErrorWindow


class TweetListWidget(QtGui.QWidget):

    userClicked = QtCore.pyqtSignal(UserItem, bool)
    tagClicked = QtCore.pyqtSignal(str, bool)

    def __init__(self, parent=None, without=[]):
        super(TweetListWidget, self).__init__(parent)
        self.tweetListWidget = SimpleTweetListWidget(parent, without)
        self.tweetListWidget.userClicked.connect(self.userClicked)
        self.tweetListWidget.tagClicked.connect(self.tagClicked)
        self.setupUi()

    def setupUi(self):
        self.layout = QtGui.QVBoxLayout()
        self.scrollArea = QtGui.QScrollArea()
        self.scrollArea.setWidgetResizable(True)
        self.scrollArea.setWidget(self.tweetListWidget)
        self.layout.addWidget(self.scrollArea)
        self.layout.setMargin(0)
        self.layout.setSpacing(0)
        self.setLayout(self.layout)
        self.scrollArea.verticalScrollBar().valueChanged.connect(self.loadMore)

    def setModel(self, model):
        self.tweetListWidget.setModel(model)

    def loadMore(self, value):
        if value == self.scrollArea.verticalScrollBar().maximum():
            self.setBusy(True, SimpleTweetListWidget.BOTTOM)
            model = self.tweetListWidget.model
            model.next()

    def moveToTop(self):
        self.scrollArea.verticalScrollBar().setSliderPosition(0)

    def setBusy(self, busy, pos):
        self.tweetListWidget.setBusy(busy, pos)

    def model(self):
        return self.tweetListWidget.model

    def refresh(self):
        self.setBusy(True, SimpleTweetListWidget.TOP)
        self.tweetListWidget.model.new()


class SimpleTweetListWidget(QtGui.QWidget):

    TOP = 1
    BOTTOM = 2
    userClicked = QtCore.pyqtSignal(UserItem, bool)
    tagClicked = QtCore.pyqtSignal(str, bool)

    def __init__(self, parent=None, without=[]):
        super(SimpleTweetListWidget, self).__init__(parent)
        self.client = const.client
        self.without = without
        self.setupUi()

    def setupUi(self):
        self.layout = QtGui.QVBoxLayout(self)
        self.setLayout(self.layout)
        self.busyMovie = WObjectCache().open(QtGui.QMovie,
                                             ":/IMG/img/busy.gif")

    def setModel(self, model):
        self.model = model
        self.model.rowsInserted.connect(self._rowsInserted)
        self.model.nothingLoaded.connect(self._hideBusyIcon)

    def _hideBusyIcon(self):
        self.setBusy(False, self.BOTTOM)

    def _rowsInserted(self, parent, start, end):
        UNUSED(parent)  # parent is useless

        self.setBusy(False, self.TOP)
        self.setBusy(False, self.BOTTOM)
        for index in range(start, end + 1):
            item = self.model.get_item(index)
            widget = SingleTweetWidget(item, self.without, self)
            widget.userClicked.connect(self.userClicked)
            widget.tagClicked.connect(self.tagClicked)
            self.layout.insertWidget(index, widget)

    def setupBusyIcon(self):
        busyWidget = QtGui.QWidget()
        layout = QtGui.QVBoxLayout(busyWidget)
        busy = WImageLabel()
        busy.setMovie(self.busyMovie)
        layout.addWidget(busy)
        layout.setAlignment(QtCore.Qt.AlignCenter)
        busyWidget.setLayout(layout)
        return busyWidget

    def busy(self):
        top_widget = self.layout.itemAt(0)
        if top_widget:
            top_widget = top_widget.widget()

        bottom_widget = self.layout.itemAt(self.layout.count() - 1)
        if bottom_widget:
            bottom_widget = bottom_widget.widget()

        if top_widget and top_widget.objectName() == "busyIcon":
            return self.TOP
        elif bottom_widget and bottom_widget.objectName() == "busyIcon":
            return self.BOTTOM
        else:
            return False

    def setBusy(self, busy, pos):
        if pos == self.TOP:
            self._setTopBusy(busy)
        elif pos == self.BOTTOM:
            self._setBottomBusy(busy)

    def _setTopBusy(self, busy):
        if busy and self.busy() != self.TOP:
            busy_widget = self.setupBusyIcon()
            busy_widget.setObjectName("busyIcon")
            self.layout.insertWidget(0, busy_widget)
        elif not busy and self.busy() == self.TOP:
            top_widget = self.layout.itemAt(0).widget()
            self.layout.removeWidget(top_widget)
            top_widget.setParent(None)

    def _setBottomBusy(self, busy):
        if busy and self.busy() != self.BOTTOM:
            busy_widget = self.setupBusyIcon()
            busy_widget.setObjectName("busyIcon")
            self.layout.addWidget(busy_widget)
        elif not busy and self.busy() == self.BOTTOM:
            bottom_widget = self.layout.itemAt(self.layout.count() - 1).widget()
            self.layout.removeWidget(bottom_widget)
            bottom_widget.setParent(None)


class SingleTweetWidget(QtGui.QFrame):

    userClicked = QtCore.pyqtSignal(UserItem, bool)
    tagClicked = QtCore.pyqtSignal(str, bool)

    MENTIONS_RE = re.compile('(@[-a-zA-Z0-9_\u4e00-\u9fa5]+)')
    SINA_URL_RE = re.compile(r"(http://t.cn/\w{5,7})")
    HASHTAG_RE = re.compile("(#.*?#)")

    def __init__(self, tweet=None, without=[], parent=None):
        super(SingleTweetWidget, self).__init__(parent)
        self.errorWindow = APIErrorWindow(self)
        self.tweet = tweet
        self.client = const.client
        self.without = without
        self.setObjectName("SingleTweetWidget")
        self.setupUi()
        self.fetcher = AsyncFetcher("".join((cache_path, str(WeRuntimeInfo()["uid"]))))
        self.download_lock = False
        self.__favorite_queue = []

    def setupUi(self):
        self.horizontalLayout = QtGui.QHBoxLayout(self)
        self.horizontalLayout.setMargin(0)
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.verticalLayout_2 = QtGui.QVBoxLayout()
        self.verticalLayout_2.setObjectName("verticalLayout_2")

        reason = self.tweet.author.verify_reason
        if self.tweet.author.verify_type == "personal":
            self.avatar = WAvatarLabel(WAvatarLabel.PERSONAL_VERIFY, reason)
        elif self.tweet.author.verify_type == "organization":
            self.avatar = WAvatarLabel(WAvatarLabel.ORGANIZATION_VERIFY, reason)
        else:
            self.avatar = WAvatarLabel(WAvatarLabel.NO_VERIFY)
        self.avatar.setObjectName("avatar")
        self.avatar.setPixmap(self.tweet.author.avatar)
        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Fixed, QtGui.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.avatar.sizePolicy().hasHeightForWidth())
        self.avatar.setSizePolicy(sizePolicy)
        self.avatar.setAlignment(QtCore.Qt.AlignTop)
        self.avatar.clicked.connect(self._userClicked)
        self.verticalLayout_2.addWidget(self.avatar)

        self.time = SimpleLabel()
        self.time.setObjectName("time")
        sizePolicy = QtGui.QSizePolicy(QtGui.QSizePolicy.Fixed, QtGui.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.time.sizePolicy().hasHeightForWidth())
        self.time.setSizePolicy(sizePolicy)
        self.verticalLayout_2.addWidget(self.time)
        self.verticalLayout_2.setAlignment(QtCore.Qt.AlignTop)

        self.horizontalLayout.addLayout(self.verticalLayout_2)
        self.verticalLayout = QtGui.QVBoxLayout()
        self.verticalLayout.setObjectName("verticalLayout")

        self.username = QtGui.QLabel(self)
        self.username.setObjectName("username")
        self.username.setAlignment(QtCore.Qt.AlignTop)
        self.username.setTextInteractionFlags(QtCore.Qt.TextSelectableByMouse)
        self.verticalLayout.addWidget(self.username)

        self.tweetText = WTweetLabel(self)
        self.tweetText.setObjectName("tweetText")
        self.tweetText.setAlignment(QtCore.Qt.AlignTop)
        self.tweetText.userClicked.connect(self._userTextClicked)
        self.tweetText.tagClicked.connect(self._tagClicked)
        self.verticalLayout.addWidget(self.tweetText)

        if self.tweet.thumbnail_pic and (not "image" in self.without):
            self.imageWidget = self._createImageLabel(self.tweet.thumbnail_pic)
            self.verticalLayout.addWidget(self.imageWidget)

        if self.tweet.original and (not "original" in self.without):
            self.originalLabel = self._createOriginalLabel()
            self.verticalLayout.addWidget(self.originalLabel)

        self.horizontalLayout.setStretch(1, 1)
        self.horizontalLayout.setStretch(2, 10)

        self.counterHorizontalLayout = QtGui.QHBoxLayout()
        self.counterHorizontalLayout.setObjectName("counterhorizontalLayout")
        self.horizontalSpacer = QtGui.QSpacerItem(40, 20,
                                                  QtGui.QSizePolicy.Expanding,
                                                  QtGui.QSizePolicy.Minimum)
        self.counterHorizontalLayout.addItem(self.horizontalSpacer)

        if WeRuntimeInfo().get("uid") == self.tweet.author.id:
            self.delete = self._createDeleteLabel()
            self.counterHorizontalLayout.addWidget(self.delete)

        if not (self.tweet.type == TweetItem.COMMENT):
            self.client = QtGui.QLabel()
            self.client.setText(self.tr("From: %s") % self.tweet.source)
            self.client.linkActivated.connect(lambda link: openLink(link))
            self.counterHorizontalLayout.addWidget(self.client)

            self.retweet = self._createRetweetLabel()
            self.counterHorizontalLayout.addWidget(self.retweet)

            self.comment = self._createCommentLabel()
            self.counterHorizontalLayout.addWidget(self.comment)

            self.favorite = self._createFavoriteLabel()
            self.counterHorizontalLayout.addWidget(self.favorite)

            self.counterHorizontalLayout.setAlignment(QtCore.Qt.AlignTop)
        elif self.tweet.type == TweetItem.COMMENT:
            self.reply = self._createReplyLabel()
            self.counterHorizontalLayout.addWidget(self.reply)

        self.verticalLayout.addLayout(self.counterHorizontalLayout)
        self.horizontalLayout.addLayout(self.verticalLayout)

        self.setStyleSheet("""
            QFrame#SingleTweetWidget {
                border-bottom: 2px solid palette(highlight);
                border-radius: 0px;
                padding: 2px;
            }
        """)

        self.username.setText(" " + self.tweet.author.name)
        text = QtCore.Qt.escape(self.tweet.text)
        text = self._create_mentions(text)
        text = self._create_html_url(text)
        text = self._create_hashtag(text)
        text = self._create_smiles(text)
        self.tweetText.setHtml(text)
        self.timer = QtCore.QTimer(self)
        self.timer.timeout.connect(self._update_time)
        self._update_time()

    def _setup_timer(self):
        self.timer.stop()
        passedSeconds = self.tweet.passedSeconds
        if passedSeconds < 60:
            self.timer.start(1 * 1000)
        elif passedSeconds < 3600:
            self.timer.start(60 * 1000)
        elif passedSeconds < 86400:
            self.timer.start(60 * 60 * 1000)
        else:
            self.timer.start(60 * 60 * 24 * 1000)

    def _update_time(self):
        try:
            if not self.time.visibleRegion() and self.timer.isActive():
                # Skip update only when timer is active, insure
                # at least run once time.
                return

            if not self.time.toolTip():
                self.time.setToolTip(self.tweet.timestamp)

            if self.tweet.type != TweetItem.COMMENT:
                self.time.setText("<a href='%s'>%s</a>" %
                                  (self.tweet.url, self.tweet.time))
            else:
                self.time.setText("<a href='%s'>%s</a>" %
                                  (self.tweet.original.url, self.tweet.time))
            self._setup_timer()
        except:
            # Sometimes, user closed the window and the window
            # has been garbage collected already, but
            # the timer is still running. It will cause a runtime error
            pass

    def _createOriginalLabel(self):
        widget = QtGui.QWidget(self)
        widget.setObjectName("originalWidget")
        widgetLayout = QtGui.QVBoxLayout(widget)
        widgetLayout.setSpacing(0)
        widgetLayout.setMargin(0)
        widgetLayout.setAlignment(QtCore.Qt.AlignCenter | QtCore.Qt.AlignTop)

        frame = QtGui.QFrame()
        frame.setObjectName("originalFrame")
        widgetLayout.addWidget(frame)
        layout = QtGui.QVBoxLayout(frame)
        layout.setObjectName("originalLayout")
        layout.setAlignment(QtCore.Qt.AlignTop)
        textLabel = WTweetLabel()
        textLabel.setAlignment(QtCore.Qt.AlignCenter | QtCore.Qt.AlignTop)
        textLabel.userClicked.connect(self._userTextClicked)
        textLabel.tagClicked.connect(self._tagClicked)
        self.textLabel = textLabel  # Hack: save a reference
        originalItem = self.tweet.original

        text = QtCore.Qt.escape(originalItem.text)
        text = self._create_mentions(text)
        text = self._create_html_url(text)
        text = self._create_hashtag(text)
        text = self._create_smiles(text)
        try:
            authorName = self._create_mentions("@" + originalItem.author.name)
            textLabel.setHtml("%s: %s" % (authorName, text))
        except:
            # originalItem.text == This tweet deleted by author
            textLabel.setHtml(text)
        layout.addWidget(textLabel)

        if originalItem.thumbnail_pic:
            layout.addWidget(self._createImageLabel(originalItem.thumbnail_pic))

        counterHorizontalLayout = QtGui.QHBoxLayout()
        counterHorizontalLayout.setObjectName("counterhorizontalLayout")
        horizontalSpacer = QtGui.QSpacerItem(40, 20,
                                             QtGui.QSizePolicy.Expanding,
                                             QtGui.QSizePolicy.Minimum)
        counterHorizontalLayout.addItem(horizontalSpacer)
        retweet = WIconLabel(widget)
        retweet.setObjectName("retweet")
        retweet.setText(str(originalItem.retweets_count))
        retweet.setIcon(":/IMG/img/retweets.png")
        retweet.clicked.connect(self._original_retweet)
        counterHorizontalLayout.addWidget(retweet)
        comment = WIconLabel(widget)
        comment.setObjectName("comment")
        comment.setIcon(":/IMG/img/comments.png")
        comment.setText(str(originalItem.comments_count))
        comment.clicked.connect(self._original_comment)
        counterHorizontalLayout.addWidget(comment)
        counterHorizontalLayout.setSpacing(6)
        layout.setMargin(8)
        layout.setSpacing(0)
        layout.addLayout(counterHorizontalLayout)

        frame.setStyleSheet("""
            QFrame#originalFrame {
                border: 2px solid palette(highlight);
                border-radius: 4px;
                padding: 2px;
            }
        """)

        return widget

    def _createImageLabel(self, thumbnail_pic):
        widget = QtGui.QWidget(self)
        widget.setObjectName("imageLabel")
        widgetLayout = QtGui.QVBoxLayout(widget)
        widgetLayout.setSpacing(0)
        widgetLayout.setMargin(0)
        widgetLayout.setAlignment(QtCore.Qt.AlignCenter)

        frame = QtGui.QFrame()
        frame.setObjectName("imageFrame")
        widgetLayout.addWidget(frame)
        layout = QtGui.QVBoxLayout(frame)
        layout.setObjectName("imageLayout")

        self.imageLabel = WSwitchLabel(widget)
        self.imageLabel.setImagesUrls(thumbnail_pic)
        self.imageLabel.clicked.connect(self._showFullImage)

        layout.addWidget(self.imageLabel)
        widgetLayout.addWidget(frame)

        return widget

    def _createFavoriteLabel(self):
        favorite = WIconLabel(self)
        favorite.setIcon(":/IMG/img/no_favorites.png")
        favorite.clicked.connect(self._favorite)
        return favorite

    def _createRetweetLabel(self):
        retweet = WIconLabel(self)
        retweet.setObjectName("retweet")
        retweet.setText(str(self.tweet.retweets_count))
        retweet.setIcon(":/IMG/img/retweets.png")
        retweet.clicked.connect(self._retweet)
        return retweet

    def _createCommentLabel(self):
        comment = WIconLabel(self)
        comment.setObjectName("comment")
        comment.setIcon(":/IMG/img/comments.png")
        comment.setText(str(self.tweet.comments_count))
        comment.clicked.connect(self._comment)
        return comment

    def _createReplyLabel(self):
        reply = WIconLabel(self)
        reply.setObjectName("reply")
        reply.setIcon(":/IMG/img/retweets.png")
        reply.clicked.connect(self._reply)
        return reply

    def _createDeleteLabel(self):
        delete = WIconLabel(self)
        delete.setObjectName("delete")
        delete.setIcon(":/IMG/img/deletes.png")
        delete.clicked.connect(self._delete)
        return delete

    def fetch_open_original_pic(self, thumbnail_pic):
        """Fetch and open original pic from thumbnail pic url.
           Pictures will stored in cache directory. If we already have a same
           name in cache directory, just open it. If we don't, then download it
           first."""

        def open_pic(localfile):
            start(localfile)
            self.download_lock = False
            self.imageLabel.setBusy(False)

        if self.download_lock:
            return

        self.download_lock = True
        self.imageLabel.setBusy(True)
        original_pic = thumbnail_pic.replace("thumbnail",
                                             "large")  # A simple trick ... ^_^
        self.fetcher.addTask(original_pic, open_pic)

    def _showFullImage(self):
        self.fetch_open_original_pic(self.imageLabel.url())

    def _favorite(self):
        needWorker = False

        if not self.__favorite_queue:
            state = not self.tweet.isFavorite()
            needWorker = True
        elif not self.__favorite_queue[-1]:
            state = True
        else:
            state = False

        self.__favorite_queue.append(state)
        if state:
            self.favorite.setIcon(":/IMG/img/favorites.png")
        else:
            self.favorite.setIcon(":/IMG/img/no_favorites.png")

        if needWorker:
            self.__favorite_worker()

    @async
    def __favorite_worker(self):
        while self.__favorite_queue:
            state = self.__favorite_queue[0]

            try:
                self.tweet.setFavorite(state)
                sleep(0.5)
                self.__favorite_queue.pop(0)
            except APIError as e:
                if e.error_code == 20101:
                    self.tweet.setFavoriteForce(True)
                elif e.error_code == 20704:
                    self.tweet.setFavoriteForce(True)
                self._e = e
                self.__favorite_queue = []
                self.commonSignal.emit(lambda: self.errorWindow.raiseException.emit(self._e))
                return

    def _retweet(self, tweet=None):
        if not tweet:
            tweet = self.tweet

        self.exec_newpost_window("retweet", tweet)

    def _comment(self, tweet=None):
        if not tweet:
            tweet = self.tweet
        if tweet.type == TweetItem.COMMENT:
            self._reply(tweet)
            return

        self.exec_newpost_window("comment", tweet)

    def _reply(self, tweet=None):
        if not tweet:
            tweet = self.tweet
        self.exec_newpost_window("reply", tweet)

    def _delete(self):
        questionDialog = QtGui.QMessageBox.question
        choice = questionDialog(self, self.tr("Delete?"),
                                self.tr("You can't undo your deletion."),
                                QtGui.QMessageBox.Yes, QtGui.QMessageBox.No)
        if choice == QtGui.QMessageBox.No:
            return

        try:
            self.tweet.delete()
        except APIError as e:
            self.errorWindow.raiseException.emit(e)
        self.timer.stop()
        self.hide()

    def _original_retweet(self):
        self._retweet(self.tweet.original)

    def _original_comment(self):
        self._comment(self.tweet.original)

    def _create_html_url(self, text):
        return self.SINA_URL_RE.sub(r"""<a href='\1'>\1</a>""", text)

    def _create_smiles(self, text):
        faceModel = FaceModel()
        for face in faceModel.all_faces():
            new_text = text.replace("[%s]" % face.name, '<img src="%s" />' % face.path)
            if new_text != text:
                self._create_animation(face.path)
                text = new_text
        return text

    def _create_mentions(self, text):
        return self.MENTIONS_RE.sub(r"""<a href='mentions:///\1'>\1</a>""", text)

    def _create_hashtag(self, text):
        return self.HASHTAG_RE.sub(r"""<a href='hashtag:///\1'>\1</a>""", text)

    def _create_animation(self, path):
        movie = WObjectCache().open(QtGui.QMovie, path)
        movie.frameChanged.connect(self.drawAnimate)
        movie.start()

    def drawAnimate(self):
        sender = self.sender()

        if (not isinstance(sender, QtGui.QMovie)) or (not self.tweetText.visibleRegion()):
            return

        movie = sender

        self._addSingleFrame(movie, self.tweetText)
        if self.tweet.original and (not "original" in self.without):
            self._addSingleFrame(movie, self.textLabel)

    def _addSingleFrame(self, movie, textBrowser):
        document = textBrowser.document()
        document.addResource(QtGui.QTextDocument.ImageResource,
                             QtCore.QUrl(movie.fileName()),
                             movie.currentPixmap())
        # Cause a force refresh
        textBrowser.update()

    def exec_newpost_window(self, action, tweet):
        from NewpostWindow import NewpostWindow
        try:
            self.wecase_new = NewpostWindow(action, tweet)
            self.wecase_new.userClicked.connect(self.userClicked)
            self.wecase_new.tagClicked.connect(self.tagClicked)
            self.wecase_new.show()
        except APIError as e:
            self.errorWindow.raiseException.emit(e)

    def _userClicked(self, button):
        openAtBackend = False
        if button == QtCore.Qt.MiddleButton:
            openAtBackend = True
        self.userClicked.emit(self.tweet.author, openAtBackend)

    @async
    def _userTextClicked(self, user, button):
        openAtBackend = False
        if button == QtCore.Qt.MiddleButton:
            openAtBackend = True

        try:
            self.__userItem = UserItem({"name": user})
        except APIError as e:
            self.errorWindow.raiseException.emit(e)
            return
        self.userClicked.emit(self.__userItem, openAtBackend)

    def _tagClicked(self, tag, button):
        openAtBackend = False
        if button == QtCore.Qt.MiddleButton:
            openAtBackend = True
        self.tagClicked.emit(tag, openAtBackend)

########NEW FILE########
__FILENAME__ = TweetUtils
#!/usr/bin/env python3
# vim: tabstop=8 expandtab shiftwidth=4 softtabstop=4

# WeCase -- This model implemented a bug-for-bug compatible
#           strings' length counter with Sina's
# Copyright (C) 2013, 2014 The WeCase Developers.
# License: GPL v3 or later.


import re
from math import ceil
import const


def tweetLength(text):
    """
    This function implemented a strings' length counter, the result of
    this function should be bug-for-bug compatible with Sina's.

    >>> tweetLength("Test")
    2
    """

    def findall(regex, text):
        """ re.findall() sometimes output unexpected results. This function
        is a special version of findall() """

        results = []

        re_obj = re.compile(regex)
        for match in re_obj.finditer(text):
            results.append(match.group())
        return results

    TWEET_MIN = 41
    TWEET_MAX = 140
    TWEET_URL_LEN = 20

    total = 0
    n = text
    if len(text) > 0:
        # please improve it if you can fully understand it
        r = findall(r"http://[a-zA-Z0-9]+(\.[a-zA-Z0-9]+)+([-A-Z0-9a-z_$.+!*()/\\\,:@&=?~#%]*)", text)

        for item in r:
            url = item
            byteLen = len(url) + len(re.findall(r"[^\x00-\x80]", url))

            if re.search(r"^(http://t.cn)", url):
                continue
            elif re.search(r"^(http:\/\/)+(weibo.com|weibo.cn)", url):
                total += (byteLen if byteLen <= TWEET_MIN else
                          (TWEET_URL_LEN
                           if byteLen <= TWEET_MAX
                           else byteLen - TWEET_MAX + TWEET_URL_LEN))
            else:
                total += (TWEET_URL_LEN if byteLen <= TWEET_MAX else
                          (byteLen - TWEET_MAX + TWEET_URL_LEN))
            n = n.replace(url, "")
    return ceil((total + len(n) + len(re.findall(r"[^\x00-\x80]", n))) / 2)


def get_mid(mid):
    """
    Convert a id string of a tweet to a mid string.
    You'll need a mid to generate an URL for a single tweet page.

    >>> get_mid("3591268992667779")
    'zCik3bc0H'
    """

    def baseN(num, base):
        """Convert the base of a decimal."""
        CHAR = "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
        return ((num == 0) and "0") or \
               (baseN(num // base, base).lstrip("0") + CHAR[num % base])

    url = ""

    i = len(mid) - 7
    while i > -7:
        offset_1 = 0 if i < 0 else i
        offset_2 = i + 7
        num = mid[offset_1:offset_2]
        num = baseN(int(num), 62)

        if not len(num) == 1:
            # if it isn't the first char of the mid, and it's length less than
            # four chars, add zero at left for spacing
            num = num.rjust(4, "0")

        url = num + url

        i -= 7
    return url

########NEW FILE########
__FILENAME__ = TweetUtils_test
#!/usr/bin/env python3
# vim: tabstop=8 expandtab shiftwidth=4 softtabstop=4

# WeCase -- This file implemented the unit tests for TweetUtils.
# Copyright (C) 2013, 2014 The WeCase Developers.
# License: GPL v3 or later.


import unittest
from TweetUtils import tweetLength, get_mid


class TweetUtilsTest(unittest.TestCase):

    def test_tweetLength(self):
        self.assertEqual(tweetLength("【转基因"), 4)
        self.assertEqual(tweetLength("我司CEO！"), 5)
        self.assertEqual(tweetLength("8@&*%&b"), 4)
        self.assertEqual(tweetLength(" Test"), 3)
        self.assertEqual(tweetLength("   Test   "), 5)
        self.assertEqual(tweetLength("　　　Ｔｅｓｔｉｎｇ　　　　"), 14)

    def test_get_mid(self):
        self.assertEqual(get_mid("3591268992667779"), 'zCik3bc0H')
        self.assertEqual(get_mid("3591370117495972"), 'zCkX9vs2M')
        self.assertEqual(get_mid("3591291856713634"), 'zCiUVsawq')


if __name__ == "__main__":
    unittest.main()

########NEW FILE########
__FILENAME__ = WAsyncLabel
#!/usr/bin/env python3
# vim: tabstop=8 expandtab shiftwidth=4 softtabstop=4

# WeCase -- This file implemented a Label for fetching the images async.
# Copyright (C) 2013, 2014 The WeCase Developers.
# License: GPL v3 or later.


from PyQt4 import QtCore, QtGui
from WImageLabel import WImageLabel
from path import cache_path as down_path
from WObjectCache import WObjectCache
from AsyncFetcher import AsyncFetcher
from WeRuntimeInfo import WeRuntimeInfo


class WAsyncLabel(WImageLabel):

    clicked = QtCore.pyqtSignal(int)

    def __init__(self, parent=None):
        super(WAsyncLabel, self).__init__(parent)
        self._url = ""
        self._image = None

        self.fetcher = AsyncFetcher("".join((down_path, str(WeRuntimeInfo()["uid"]))))

        busyIconPixmap = WObjectCache().open(QtGui.QPixmap, ":/IMG/img/busy.gif")
        self.minimumImageHeight = busyIconPixmap.height()
        self.minimumImageWidth = busyIconPixmap.width()

        self.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.contextMenu)

    def url(self):
        return self._url

    def setBusy(self, busy):
        if busy:
            # XXX: # Issue #74.
            # What's wrong with the busyMovie()? To save the memory,
            # We use a single busyMovie() in the whole program.
            # If the image downloaded here, we'll stop the movie and the
            # busyIcon will disappear. But it may start from somewhere else.
            # The the busyIcon appear again unexpectedly.
            # The quick fix is disconnecting the signal/slot connection
            # when we stop the movie.
            self.animation = WObjectCache().open(QtGui.QMovie, ":/IMG/img/busy.gif")
            self.animation.start()
            self.animation.frameChanged.connect(self.drawBusyIcon)
        else:
            self.clearBusyIcon()

    @QtCore.pyqtSlot()
    def drawBusyIcon(self):
        image = QtGui.QPixmap(self._image)
        icon = self.animation.currentPixmap()

        height = (image.height() - icon.height()) / 2
        width = (image.width() - icon.width()) / 2
        painter = QtGui.QPainter(image)
        painter.drawPixmap(width, height, icon)
        painter.end()
        super(WAsyncLabel, self).setPixmap(image)

    def clearBusyIcon(self):
        self.animation.stop()
        self.animation.frameChanged.disconnect(self.drawBusyIcon)
        super(WAsyncLabel, self).setPixmap(self._image)

    def _setPixmap(self, path):
        _image = QtGui.QPixmap(path)
        minimalHeight = self.minimumImageHeight
        minimalWidth = self.minimumImageWidth

        if _image.height() < minimalHeight or _image.width() < minimalWidth:
            if _image.height() > minimalHeight:
                height = _image.height()
            else:
                height = minimalHeight

            if _image.width() > minimalWidth:
                width = _image.width()
            else:
                width = minimalWidth

            image = QtGui.QPixmap(width, height)
            painter = QtGui.QPainter(image)
            path = QtGui.QPainterPath()
            path.addRect(0, 0, width, height)
            painter.fillPath(path, QtGui.QBrush(QtCore.Qt.gray))
            painter.drawPixmap((width - _image.width()) / 2,
                               (height - _image.height()) / 2,
                               _image)
            painter.end()
        else:
            image = _image

        self._image = image
        super(WAsyncLabel, self).setPixmap(image)

    def setPixmap(self, url):
        super(WAsyncLabel, self).setMovie(
            WObjectCache().open(QtGui.QMovie, ":/IMG/img/busy.gif")
        )
        self.start()
        if not ("http" in url):
            self._setPixmap(url)
            return
        self._url = url
        self._fetch()

    def _fetch(self):
        self.fetcher.addTask(self._url, self.setPixmap)

    def mouseReleaseEvent(self, e):
        if e.button() == QtCore.Qt.LeftButton and self._image:
            self.clicked.emit(QtCore.Qt.LeftButton)
        elif e.button() == QtCore.Qt.MiddleButton and self._image:
            self.clicked.emit(QtCore.Qt.MiddleButton)

    def contextMenu(self, pos):
        if not self._image:
            return
        saveAction = QtGui.QAction(self)
        saveAction.setText(self.tr("&Save"))
        saveAction.triggered.connect(self.save)
        menu = QtGui.QMenu()
        menu.addAction(saveAction)
        menu.exec(self.mapToGlobal(pos))

    def save(self):
        file = QtGui.QFileDialog.getOpenFileName(self,
                                                 self.tr("Choose a path"))
        self._image.save(file)

########NEW FILE########
__FILENAME__ = WAvatarLabel
#!/usr/bin/env python3
# vim: tabstop=8 expandtab shiftwidth=4 softtabstop=4

# WeCase -- This file implemented a Label for displaying the avatars with
#           the verify icon.
# Copyright (C) 2013, 2014 The WeCase Developers.
# License: GPL v3 or later.


from PyQt4 import QtCore, QtGui
from WAsyncLabel import WAsyncLabel


class WAvatarLabel(WAsyncLabel):

    NO_VERIFY = 0
    PERSONAL_VERIFY = 1
    ORGANIZATION_VERIFY = 2

    def __init__(self, verify_type, reason="", parent=None):
        super(WAvatarLabel, self).__init__(parent)
        self.__verity_type = verify_type
        self.setToolTip(reason)

    def _setPixmap(self, path):
        super(WAvatarLabel, self)._setPixmap(path)

        if self.__verity_type == self.NO_VERIFY:
            return
        elif self.__verity_type == self.PERSONAL_VERIFY:
            newPixmap = self.__draw_verify_icon(self._image, QtGui.QPixmap(":/IMG/img/verify_personal.png"))
        elif self.__verity_type == self.ORGANIZATION_VERIFY:
            newPixmap = self.__draw_verify_icon(self._image, QtGui.QPixmap(":/IMG/img/verify_organization.png"))
        super(WAsyncLabel, self).setPixmap(newPixmap)

    def __draw_verify_icon(self, pixmap, verify_pixmap):
        newPixmap = pixmap.copy()
        verify_pixmap = verify_pixmap.scaledToHeight(20, QtCore.Qt.SmoothTransformation)
        painter = QtGui.QPainter()
        painter.begin(newPixmap)
        painter.drawPixmap(self._image.height() - verify_pixmap.height(),
                           self._image.width() - verify_pixmap.width(),
                           verify_pixmap)
        painter.end()
        return newPixmap

########NEW FILE########
__FILENAME__ = WCompleteLineEdit
#!/usr/bin/env python3
# vim: tabstop=8 expandtab shiftwidth=4 softtabstop=4

# WeCase -- This model implemented a general QTextEdit
#           with flexible auto-complete.
# Copyright (C) 2013, 2014 The WeCase Developers.
# License: GPL v3 or later.


from PyQt4 import QtGui, QtCore
from WeHack import async


class WAbstractCompleteLineEdit(QtGui.QTextEdit):
    fetchListFinished = QtCore.pyqtSignal(list)

    def __init__(self, parent=None):
        super(WAbstractCompleteLineEdit, self).__init__(parent)
        self.cursor = self.textCursor()

        self.setupUi()
        self.setupSignals()

    def setupUi(self):
        self.listView = QtGui.QListView(self)
        self.model = QtGui.QStringListModel(self)
        self.listView.setEditTriggers(QtGui.QAbstractItemView.NoEditTriggers)
        self.listView.setWindowFlags(QtCore.Qt.ToolTip)
        self.setLineWrapMode(self.WidgetWidth)

    def setupSignals(self):
        self.textChanged.connect(self.needComplete)
        self.textChanged.connect(self.setCompleter)
        self.listView.clicked.connect(self.mouseCompleteText)
        self.fetchListFinished.connect(self.showCompleter)

    def getLine(self):
        # 获得折行后屏幕上实际的行数
        cursor = self.textCursor()
        cursor.movePosition(QtGui.QTextCursor.StartOfLine)

        lines = 1
        while cursor.positionInBlock() > 0:
            cursor.movePosition(QtGui.QTextCursor.Up)
            lines += 1
        block = cursor.block().previous()

        while block.isValid():
            lines += block.lineCount()
            block = block.previous()
        return lines

    def getCompleteList(self):
        raise NotImplementedError

    def getNewText(self, original_text, new_text):
        raise NotImplementedError

    def focusOutEvent(self, event):
        self.listView.hide()

    def selectedText(self):
        self.cursor.setPosition(0)
        self.cursor.setPosition(self.textCursor().position(), QtGui.QTextCursor.KeepAnchor)
        return self.cursor.selectedText()

    def keyPressEvent(self, event):
        if not self.listView.isHidden():
            key = event.key()
            rowCount = self.listView.model().rowCount()
            currentIndex = self.listView.currentIndex()

            if key == QtCore.Qt.Key_Down:
                # 向下移动列表，越界回到顶部
                row = (currentIndex.row() + 1) % rowCount
                index = self.listView.model().index(row, 0)
                self.listView.setCurrentIndex(index)

            elif key == QtCore.Qt.Key_Up:
                # 向上移动列表，越界回到底部
                row = (currentIndex.row() - 1) % rowCount
                index = self.listView.model().index(row, 0)
                self.listView.setCurrentIndex(index)

            elif key == QtCore.Qt.Key_Escape:
                # 退出菜单
                self.listView.hide()

            elif key == QtCore.Qt.Key_Return or key == QtCore.Qt.Key_Enter:
                # 补全单词
                if currentIndex.isValid():
                    text = self.getNewText(
                        self.cursor.selectedText(),
                        self.listView.currentIndex().data())
                    self.cursor.insertText(text)
                self.textChanged.emit()
                self.listView.hide()

            else:
                # 什么都不做，调用父类 LineEdit 的按键事件
                self.listView.hide()
                super(WAbstractCompleteLineEdit, self).keyPressEvent(event)
        else:
            super(WAbstractCompleteLineEdit, self).keyPressEvent(event)

    def needComplete(self):
        raise NotImplementedError

    def setCompleter(self):
        text = self.selectedText()
        text = text.split(self.separator)[-1]

        if not text:
            self.listView.hide()
            return
        if not self.needComplete():
            return
        if (len(text) > 1) and (not self.listView.isHidden()):
            return

        self.getCompleteList()
        self.showCompleter(["Loading..."])

    def showCompleter(self, lst):
        self.listView.hide()
        self.model.setStringList(lst)
        self.listView.setModel(self.model)

        if self.model.rowCount() == 0:
            return

        self.listView.setMinimumWidth(self.width())
        self.listView.setMaximumWidth(self.width())

        # 10 是一个幻数，它不因字体大小的改变而改变，代表弹框与当前行的间隔
        p = QtCore.QPoint(0, self.cursorRect().height() * self.getLine() + 10)
        x = self.mapToGlobal(p).x()
        y = self.mapToGlobal(p).y()
        self.listView.move(x, y)
        self.listView.show()

    def mouseCompleteText(self, index):
        text = self.getNewText(self.selectedText(), index.data())
        self.cursor.insertText(text)
        self.textChanged.emit()
        self.listView.hide()


class WCompleteLineEdit(WAbstractCompleteLineEdit):
    mentionFlag = "@"
    separator = " "

    def __init__(self, parent):
        super(WCompleteLineEdit, self).__init__(parent)
        self._needComplete = False
        self.callback = None
        self.setAcceptRichText(False)  # 禁用富文本，微博很穷的

    @async
    def getCompleteList(self):
        result = self.callback(self.cursor.selectedText())
        self.fetchListFinished.emit(result)

    def getNewText(self, original_text, new_text):
        for index, value in enumerate(original_text):
            if value == self.mentionFlag:
                pos = index
        return original_text[:pos] + new_text + self.separator

    def needComplete(self):
        if not self.selectedText():
            return False
        elif self.selectedText()[-1] == self.mentionFlag:
            self._needComplete = True
            return self._needComplete
        elif self.selectedText()[-1] == self.separator:
            self._needComplete = False
            return self._needComplete
        else:
            return self._needComplete

########NEW FILE########
__FILENAME__ = WConfigParser
#!/usr/bin/env python3
# vim: tabstop=8 expandtab shiftwidth=4 softtabstop=4

# WeCase -- This file implemented a flexible config parser
#           using meta config.
# Copyright (C) 2013, 2014 The WeCase Developers.
# License: GPL v3 or later.


from sys import stderr
from copy import deepcopy
from configparser import ConfigParser


class WConfigParser():

    ITEM = {
        "section": "", "type": None,
        "name": "", "alias": "",
        "default": None
    }

    def __init__(self, schema, config, section=""):
        self._section = section
        self._config_path = config
        self._options = []
        self._config = ConfigParser()
        self._config.read(config)
        self.__parse__(schema)
        self.__setattr__impl = self.__setattr__postload

    def __parse__(self, schema):
        with open(schema) as schema_file:
            schema = schema_file.readlines()

        config_item = deepcopy(self.ITEM)

        lineno = 0
        for line in schema:
            lineno += 1
            if line.strip() == "":
                if config_item:
                    self._options.append(config_item)
                    config_item = deepcopy(self.ITEM)
                continue

            name, value = line.replace("\n", "").split("=")
            name = name.strip()
            value = value.strip()

            try:
                config_item[name] = value
            except KeyError:
                print("Invaild line: %s" % line, file=stderr)

            if lineno == len(schema):
                if config_item:
                    self._options.append(config_item)
                    config_item = deepcopy(self.ITEM)
                continue

    def _get_option(self, name):
        for i in self._options:
            if i["name"] == name or i["alias"] == name:
                return i

    def __setattr__preload(self, attr, value):
        super(WConfigParser, self).__setattr__(attr, value)

    def __setattr__postload(self, attr, value):
        if not self._config.has_section(self._section):
            self._config[self._section] = {}
        try:
            # convert alias to realname
            option = self._get_option(attr)
            attr = option["name"]
        except Exception:
            pass
        self._config[self._section][attr] = str(value)

    __setattr__impl = __setattr__preload

    def __setattr__(self, attr, value):
        self.__setattr__impl(attr, value)

    def __getattr__(self, attr):
        option = self._get_option(attr)
        attr = option["name"]  # convert alias to realname

        if not option:
            raise AttributeError("WConfigParser object has no attribute '%s'" % attr)

        type = eval(option["type"])
        try:
            value = self._config[self._section][attr]
        except KeyError:
            value = option["default"]

        if type is str:
            return value
        else:
            return type(eval(value))

    def save(self):
        # TODO: Create and check the lock file during writing
        with open(self._config_path, "w+") as config_file:
            config_file.seek(0)
            config_file.write("# WeCase Configuration File, by WeCase Project.\n")
            config_file.write("# DO NOT EDIT ON NORMAL PURPOSE.\n\n")
            self._config.write(config_file)

########NEW FILE########
__FILENAME__ = WeCaseWindow
#!/usr/bin/env python3
# vim: tabstop=8 expandtab shiftwidth=4 softtabstop=4

# WeCase -- This file implemented WeCaseWindow, the mainWindow of WeCase.
# Copyright (C) 2013, 2014 The WeCase Developers.
# License: GPL v3 or later.


import os
import platform
from WTimer import WTimer
from PyQt4 import QtCore, QtGui
from Tweet import TweetCommonModel, TweetCommentModel, TweetUserModel, TweetTopicModel, TweetFilterModel
from Notify import Notify
from NewpostWindow import NewpostWindow
from SettingWindow import WeSettingsWindow
from AboutWindow import AboutWindow
import const
import path
from WConfigParser import WConfigParser
from WeHack import async, setGeometry, getGeometry, UNUSED
from WObjectCache import WObjectCache
from WeRuntimeInfo import WeRuntimeInfo
from TweetListWidget import TweetListWidget
from AsyncFetcher import AsyncFetcher
from weibo3 import APIError
from WeiboErrorHandler import APIErrorWindow
import logging
import wecase_rc


UNUSED(wecase_rc)


class WeCaseWindow(QtGui.QMainWindow):

    client = None
    uid = None
    timelineLoaded = QtCore.pyqtSignal(int)
    imageLoaded = QtCore.pyqtSignal(str)
    tabBadgeChanged = QtCore.pyqtSignal(int, int)
    tabAvatarFetched = QtCore.pyqtSignal(str)

    def __init__(self, parent=None):
        super(WeCaseWindow, self).__init__(parent)
        self.errorWindow = APIErrorWindow(self)
        self.setAttribute(QtCore.Qt.WA_QuitOnClose, True)
        self._iconPixmap = {}
        self.setupUi(self)
        self._setupSysTray()
        self.tweetViews = [self.homeView, self.mentionsView, self.commentsView, self.commentsMentionsTab]
        self.info = WeRuntimeInfo()
        self.client = const.client
        self.loadConfig()
        self.init_account()
        self.setupModels()
        self.IMG_AVATAR = -2
        self.IMG_THUMB = -1
        self.notify = Notify(timeout=self.notify_timeout)
        self.applyConfig()
        self.download_lock = []
        self._last_reminds_count = 0
        self._setupUserTab(self.uid(), False, True)

    def _setupTab(self, view):
        tab = QtGui.QWidget()
        layout = QtGui.QGridLayout(tab)
        layout.addWidget(view)
        view.setParent(tab)
        return tab

    def _setupCommonTab(self, timeline, view, switch=True, protect=False):
        self._prepareTimeline(timeline)
        view.setModel(timeline)
        view.userClicked.connect(self.userClicked)
        view.tagClicked.connect(self.tagClicked)
        tab = self._setupTab(view)
        self.tabWidget.addTab(tab, "")
        if switch:
            self.tabWidget.setCurrentWidget(tab)
        if protect:
            self.tabWidget.tabBar().setProtectTab(tab, True)
        return tab

    def _getSameTab(self, attr, value):
        for i in range(self.tabWidget.count()):
            try:
                tab = self.tabWidget.widget(i).layout().itemAt(0).widget()
                _value = getattr(tab.model(), attr)()
                if _value == value:
                    return i
            except AttributeError:
                pass
        return False

    def _setupUserTab(self, uid, switch=True, myself=False):
        index = self._getSameTab("uid", uid)
        if index:
            if switch:
                self.tabWidget.setCurrentIndex(index)
            return

        view = TweetListWidget()
        _timeline = TweetUserModel(self.client.statuses.user_timeline, uid,
                                   view)
        timeline = TweetFilterModel(_timeline)
        timeline.setModel(_timeline)
        tab = self._setupCommonTab(timeline, view, switch, myself)

        def setAvatar(f):
            self._setTabIcon(tab, WObjectCache().open(QtGui.QPixmap, f))

        fetcher = AsyncFetcher("".join((path.cache_path, str(self.info["uid"]))))
        fetcher.addTask(self.client.users.show.get(uid=uid)["profile_image_url"], setAvatar)

    def _setupTopicTab(self, topic, switch=True):
        index = self._getSameTab("topic", topic)
        if index:
            if switch:
                self.tabWidget.setCurrentIndex(index)
            return

        view = TweetListWidget()
        timeline = TweetTopicModel(self.client.search.topics, topic, view)
        tab = self._setupCommonTab(timeline, view, switch, protect=False)
        self._setTabIcon(tab, WObjectCache().open(
            QtGui.QPixmap, ":/IMG/img/topic.jpg"
        ))

    def userClicked(self, userItem, openAtBackend):
        try:
            self._setupUserTab(userItem.id, switch=(not openAtBackend))
        except APIError as e:
            self.errorWindow.raiseException.emit(e)

    def tagClicked(self, str, openAtBackend):
        try:
            self._setupTopicTab(str, switch=(not openAtBackend))
        except APIError as e:
            self.errorWindow.raiseException.emit(e)

    def setupUi(self, mainWindow):
        mainWindow.setWindowIcon(QtGui.QIcon(":/IMG/img/WeCase.svg"))
        mainWindow.setDocumentMode(False)
        mainWindow.setDockOptions(QtGui.QMainWindow.AllowTabbedDocks |
                                  QtGui.QMainWindow.AnimatedDocks)

        self.centralwidget = QtGui.QWidget(mainWindow)
        self.verticalLayout = QtGui.QVBoxLayout(self.centralwidget)

        self.tabWidget = QtGui.QTabWidget(self.centralwidget)
        self.tabWidget.setTabBar(WTabBar(self.tabWidget))
        self.tabWidget.setTabPosition(QtGui.QTabWidget.West)
        self.tabWidget.setTabShape(QtGui.QTabWidget.Rounded)
        self.tabWidget.setDocumentMode(False)
        self.tabWidget.setMovable(True)
        self.tabWidget.tabCloseRequested.connect(self.closeTab)

        self.homeView = TweetListWidget()
        self.homeView.userClicked.connect(self.userClicked)
        self.homeView.tagClicked.connect(self.tagClicked)
        self.homeTab = self._setupTab(self.homeView)
        self.tabWidget.addTab(self.homeTab, "")
        self.tabWidget.tabBar().setProtectTab(self.homeTab, True)

        self.mentionsView = TweetListWidget()
        self.mentionsView.userClicked.connect(self.userClicked)
        self.mentionsView.tagClicked.connect(self.tagClicked)
        self.mentionsTab = self._setupTab(self.mentionsView)
        self.tabWidget.addTab(self.mentionsTab, "")
        self.tabWidget.tabBar().setProtectTab(self.mentionsTab, True)

        self.commentsView = TweetListWidget()
        self.commentsView.userClicked.connect(self.userClicked)
        self.commentsView.tagClicked.connect(self.tagClicked)
        self.commentsTab = self._setupTab(self.commentsView)
        self.tabWidget.addTab(self.commentsTab, "")
        self.tabWidget.tabBar().setProtectTab(self.commentsTab, True)

        self.commentsMentionsView = TweetListWidget()
        self.commentsMentionsView.userClicked.connect(self.userClicked)
        self.commentsMentionsView.tagClicked.connect(self.tagClicked)
        self.commentsMentionsTab = self._setupTab(self.commentsMentionsView)
        self.tabWidget.addTab(self.commentsMentionsTab, "")
        self.tabWidget.tabBar().setProtectTab(self.commentsMentionsTab, True)

        self.verticalLayout.addWidget(self.tabWidget)

        self.widget = QtGui.QWidget(self.centralwidget)
        self.verticalLayout.addWidget(self.widget)

        mainWindow.setCentralWidget(self.centralwidget)

        self.aboutAction = QtGui.QAction(mainWindow)
        self.refreshAction = QtGui.QAction(mainWindow)
        self.logoutAction = QtGui.QAction(mainWindow)
        self.exitAction = QtGui.QAction(mainWindow)
        self.settingsAction = QtGui.QAction(mainWindow)

        self.aboutAction.setIcon(QtGui.QIcon(QtGui.QPixmap("./IMG/img/where_s_my_weibo.svg")))
        self.exitAction.setIcon(QtGui.QIcon(QtGui.QPixmap(":/IMG/img/application-exit.svg")))
        self.settingsAction.setIcon(QtGui.QIcon(QtGui.QPixmap(":/IMG/img/preferences-other.png")))
        self.refreshAction.setIcon(QtGui.QIcon(QtGui.QPixmap(":/IMG/img/refresh.png")))

        self.menubar = QtGui.QMenuBar(mainWindow)
        self.menubar.setEnabled(True)
        self.menubar.setDefaultUp(False)
        mainWindow.setMenuBar(self.menubar)

        self.mainMenu = QtGui.QMenu(self.menubar)
        self.helpMenu = QtGui.QMenu(self.menubar)
        self.optionsMenu = QtGui.QMenu(self.menubar)

        self.mainMenu.addAction(self.refreshAction)
        self.mainMenu.addSeparator()
        self.mainMenu.addAction(self.logoutAction)
        self.mainMenu.addAction(self.exitAction)
        self.helpMenu.addAction(self.aboutAction)
        self.optionsMenu.addAction(self.settingsAction)
        self.menubar.addAction(self.mainMenu.menuAction())
        self.menubar.addAction(self.optionsMenu.menuAction())
        self.menubar.addAction(self.helpMenu.menuAction())

        self.exitAction.triggered.connect(mainWindow.close)
        self.aboutAction.triggered.connect(mainWindow.showAbout)
        self.settingsAction.triggered.connect(mainWindow.showSettings)
        self.logoutAction.triggered.connect(mainWindow.logout)
        self.refreshAction.triggered.connect(mainWindow.refresh)

        self.pushButton_refresh = QtGui.QPushButton(self.widget)
        self.pushButton_new = QtGui.QPushButton(self.widget)
        self.pushButton_refresh.clicked.connect(mainWindow.refresh)
        self.pushButton_new.clicked.connect(mainWindow.postTweet)
        self.timelineLoaded.connect(self.moveToTop)
        self.tabBadgeChanged.connect(self.drawNotifyBadge)

        self.refreshAction.setShortcut(QtGui.QKeySequence("F5"))
        self.pushButton_refresh.setIcon(QtGui.QIcon(":/IMG/img/refresh.png"))
        self.pushButton_new.setIcon(QtGui.QIcon(":/IMG/img/new.png"))

        if self.isGlobalMenu():
            self._setupToolBar()
        else:
            self._setupButtonWidget()

        self._setTabIcon(self.homeTab, QtGui.QPixmap(":/IMG/img/sina.png"))
        self._setTabIcon(self.mentionsTab, QtGui.QPixmap(":/IMG/img/mentions.png"))
        self._setTabIcon(self.commentsTab, QtGui.QPixmap(":/IMG/img/comments2.png"))
        self._setTabIcon(self.commentsMentionsTab, QtGui.QPixmap(":/IMG/img/mentions_comments.svg"))

        self.retranslateUi(mainWindow)

    def isGlobalMenu(self):
        if os.environ.get("TOOLBAR") == "1":
            return True
        elif os.environ.get("TOOLBAR") == "0":
            return False
        elif os.environ.get('DESKTOP_SESSION') in ["ubuntu", "ubuntu-2d"]:
            if not os.environ.get("UBUNTU_MENUPROXY"):
                return False
            elif os.environ.get("APPMENU_DISPLAY_BOTH"):
                return False
            else:
                return True
        elif os.environ.get("DESKTOP_SESSION") == "kde-plasma" and platform.linux_distribution()[0] == "Ubuntu":
            return True
        elif platform.system() == "Darwin":
            return True
        return False

    def _setupToolBar(self):
        self.toolBar = QtGui.QToolBar()
        self.toolBar.setToolButtonStyle(QtCore.Qt.ToolButtonTextBesideIcon)
        empty = QtGui.QWidget()
        empty.setSizePolicy(QtGui.QSizePolicy.Expanding,
                            QtGui.QSizePolicy.Preferred)
        self.toolBar.addWidget(empty)
        self.toolBar.addAction(self.refreshAction)
        newAction = self.toolBar.addAction(QtGui.QIcon(":/IMG/img/new.png"),
                                           "New")
        newAction.triggered.connect(self.pushButton_new.clicked)
        self.addToolBar(self.toolBar)

    def _setupButtonWidget(self):
        self.buttonWidget = QtGui.QWidget(self)
        self.buttonLayout = QtGui.QHBoxLayout(self.buttonWidget)
        self.horizontalSpacer = QtGui.QSpacerItem(40, 20,
                                                  QtGui.QSizePolicy.Expanding,
                                                  QtGui.QSizePolicy.Minimum)
        self.buttonLayout.addSpacerItem(self.horizontalSpacer)
        self.buttonLayout.addWidget(self.pushButton_refresh)
        self.buttonLayout.addWidget(self.pushButton_new)

    def resizeEvent(self, event):
        # This is a hack!!!
        if self.isGlobalMenu():
            return
        self.buttonWidget.resize(self.menubar.sizeHint().width(),
                                 self.menubar.sizeHint().height() + 12)
        self.buttonWidget.move(self.width() - self.buttonWidget.width(),
                               self.menubar.geometry().topRight().y() - 5)

    def retranslateUi(self, frm_MainWindow):
        frm_MainWindow.setWindowTitle(self.tr("WeCase"))
        self.mainMenu.setTitle(self.tr("&WeCase"))
        self.helpMenu.setTitle(self.tr("&Help"))
        self.optionsMenu.setTitle(self.tr("&Options"))
        self.aboutAction.setText(self.tr("&About..."))
        self.refreshAction.setText(self.tr("Refresh"))
        self.logoutAction.setText(self.tr("&Log out"))
        self.exitAction.setText(self.tr("&Exit"))
        self.settingsAction.setText(self.tr("&Settings"))

    def _setupSysTray(self):
        self.systray = QtGui.QSystemTrayIcon()
        self.systray.activated.connect(self.clickedSystray)
        self.systray.setToolTip("WeCase")
        self.systray.setIcon(QtGui.QIcon(":/IMG/img/WeCase.svg"))
        self.systray.show()

        self.visibleAction = QtGui.QAction(self)
        self.visibleAction.setText(self.tr("&Hide"))
        self.visibleAction.triggered.connect(self._switchVisibility)

        self.sysMenu = QtGui.QMenu(self)
        self.sysMenu.addAction(self.visibleAction)
        self.sysMenu.addAction(self.logoutAction)
        self.sysMenu.addAction(self.exitAction)

        self.systray.setContextMenu(self.sysMenu)

    def clickedSystray(self, reason):
        if reason == QtGui.QSystemTrayIcon.Trigger:
            self._switchVisibility()
        elif reason == QtGui.QSystemTrayIcon.Context:
            pass

    def _switchVisibility(self):
        if self.isVisible():
            self.hide()
            self.visibleAction.setText(self.tr("&Show"))
        else:
            self.show()
            self.visibleAction.setText(self.tr("&Hide"))

    def _setTabIcon(self, tab, icon):
        pixmap = icon.transformed(QtGui.QTransform().rotate(90))
        icon = QtGui.QIcon(pixmap)
        self._iconPixmap[icon.cacheKey()] = pixmap
        self.tabWidget.setTabIcon(self.tabWidget.indexOf(tab), icon)
        self.tabWidget.setIconSize(QtCore.QSize(24, 24))

    def _prepareTimeline(self, timeline):
        try:
            timeline.setUsersBlacklist(self.usersBlacklist)
            timeline.setTweetsKeywordsBlacklist(self.tweetKeywordsBlacklist)
            timeline.setWordWarKeywords(self.wordWarKeywords)
            timeline.setBlockWordwars(self.blockWordwars)
            timeline.setKeywordsAsRegexs(self.keywordsAsRegex)
        except AttributeError:
            pass
        timeline.load()

    def closeTab(self, index):
        widget = self.tabWidget.widget(index)
        self.tabWidget.removeTab(index)
        widget.deleteLater()

    def init_account(self):
        self.uid()

    def loadConfig(self):
        self.config = WConfigParser(path.myself_path + "WMetaConfig",
                                    path.config_path, "main")
        self.notify_interval = self.config.notify_interval
        self.notify_timeout = self.config.notify_timeout
        self.usersBlacklist = self.config.usersBlacklist
        self.tweetKeywordsBlacklist = self.config.tweetsKeywordsBlacklist
        self.remindMentions = self.config.remind_mentions
        self.remindComments = self.config.remind_comments
        self.wordWarKeywords = self.config.wordWarKeywords
        self.blockWordwars = self.config.blockWordwars
        self.maxRetweets = self.config.maxRetweets
        self.maxTweetsPerUser = self.config.maxTweetsPerUser
        self.mainWindow_geometry = self.config.mainwindow_geometry
        self.keywordsAsRegex = self.config.keywordsAsRegex

    def applyConfig(self):
        try:
            self.timer.stop()
        except AttributeError:
            pass

        self.timer = WTimer(self.show_notify, self.notify_interval)
        self.timer.start()
        self.notify.timeout = self.notify_timeout
        setGeometry(self, self.mainWindow_geometry)

    def setupModels(self):
        self._all_timeline = TweetCommonModel(self.client.statuses.home_timeline, self)
        self.all_timeline = TweetFilterModel(self._all_timeline)
        self.all_timeline.setModel(self._all_timeline)
        self._prepareTimeline(self.all_timeline)

        # extra rules
        self.all_timeline.setMaxRetweets(self.maxRetweets)
        self.all_timeline.setMaxTweetsPerUser(self.maxTweetsPerUser)

        self.homeView.setModel(self.all_timeline)

        self._mentions = TweetCommonModel(self.client.statuses.mentions, self)
        self.mentions = TweetFilterModel(self._mentions)
        self.mentions.setModel(self._mentions)
        self._prepareTimeline(self.mentions)
        self.mentionsView.setModel(self.mentions)

        self._comment_to_me = TweetCommentModel(self.client.comments.to_me, self)
        self.comment_to_me = TweetFilterModel(self._comment_to_me)
        self.comment_to_me.setModel(self._comment_to_me)
        self._prepareTimeline(self.comment_to_me)
        self.commentsView.setModel(self.comment_to_me)

        self._comment_mentions = TweetCommentModel(self.client.comments.mentions, self)
        self.comment_mentions = TweetFilterModel(self._comment_mentions)
        self.comment_mentions.setModel(self._comment_mentions)
        self._prepareTimeline(self.comment_mentions)
        self.commentsMentionsView.setModel(self.comment_mentions)

    @async
    def reset_remind(self):
        typ = ""
        if self.currentTweetView() == self.homeView:
            self.tabBadgeChanged.emit(self.tabWidget.currentIndex(), 0)
        elif self.currentTweetView() == self.mentionsView:
            typ = "mention_status"
            self.tabBadgeChanged.emit(self.tabWidget.currentIndex(), 0)
        elif self.currentTweetView() == self.commentsView:
            typ = "cmt"
            self.tabBadgeChanged.emit(self.tabWidget.currentIndex(), 0)
        elif self.currentTweetView() == self.commentsMentionsView:
            typ = "mention_cmt"
            self.tabBadgeChanged.emit(self.tabWidget.currentIndex(), 0)

        if typ:
            self.client.remind.set_count.post(type=typ)

    def get_remind(self, uid):
        """this function is used to get unread_count
        from Weibo API. uid is necessary."""

        reminds = self.client.remind.unread_count.get(uid=uid)
        return reminds

    def uid(self):
        """How can I get my uid? here it is"""
        if not self.info.get("uid"):
            self.info["uid"] = self.client.account.get_uid.get().uid
        return self.info["uid"]

    def show_notify(self):
        # This function is run in another thread by WTimer.
        # Do not modify UI directly. Send signal and react it in a slot only.
        # We use SIGNAL self.tabTextChanged and SLOT self.setTabText()
        # to display unread count

        reminds = self.get_remind(self.uid())
        msg = self.tr("You have:") + "\n"
        reminds_count = 0

        if reminds['status'] != 0:
            # Note: do NOT send notify here, or users will crazy.
            self.tabBadgeChanged.emit(self.tabWidget.indexOf(self.homeTab),
                                      reminds['status'])

        if reminds['mention_status'] and self.remindMentions:
            msg += self.tr("%d unread @ME") % reminds['mention_status'] + "\n"
            self.tabBadgeChanged.emit(self.tabWidget.indexOf(self.mentionsTab),
                                      reminds['mention_status'])
            reminds_count += 1
        else:
            self.tabBadgeChanged.emit(self.tabWidget.indexOf(self.mentionsTab), 0)

        if reminds['cmt'] and self.remindComments:
            msg += self.tr("%d unread comment(s)") % reminds['cmt'] + "\n"
            self.tabBadgeChanged.emit(self.tabWidget.indexOf(self.commentsTab),
                                      reminds['cmt'])
            reminds_count += 1
        else:
            self.tabBadgeChanged.emit(self.tabWidget.indexOf(self.commentsTab), 0)

        if reminds["mention_cmt"] and self.remindMentions:
            msg += self.tr("%d unread @ME comment(s)") % reminds["mention_cmt"] + "\n"
            self.tabBadgeChanged.emit(self.tabWidget.indexOf(self.commentsMentionsTab),
                                      reminds["mention_cmt"])
            reminds_count += 1
        else:
            self.tabBadgeChanged.emit(self.tabWidget.indexOf(self.commentsMentionsTab), 0)

        if reminds_count and reminds_count != self._last_reminds_count:
            self.notify.showMessage(self.tr("WeCase"), msg)
            self._last_reminds_count = reminds_count

    def drawNotifyBadge(self, index, count):
        tabIcon = self.tabWidget.tabIcon(index)
        _tabPixmap = self._iconPixmap[tabIcon.cacheKey()]
        tabPixmap = _tabPixmap.transformed(QtGui.QTransform().rotate(-90))
        icon = NotifyBadgeDrawer().draw(tabPixmap, str(count))
        icon = icon.transformed(QtGui.QTransform().rotate(90))
        icon = QtGui.QIcon(icon)
        self._iconPixmap[icon.cacheKey()] = _tabPixmap
        self.tabWidget.setTabIcon(index, icon)

    def moveToTop(self):
        self.currentTweetView().moveToTop()

    def showSettings(self):
        wecase_settings = WeSettingsWindow()
        if wecase_settings.exec_():
            self.loadConfig()
            self.applyConfig()

    def showAbout(self):
        wecase_about = AboutWindow()
        wecase_about.exec_()

    def logout(self):
        self.close()
        # This is a model dialog, if we exec it before we close MainWindow
        # MainWindow won't close
        from LoginWindow import LoginWindow
        wecase_login = LoginWindow(allow_auto_login=False)
        wecase_login.exec_()

    def postTweet(self):
        self.wecase_new = NewpostWindow()
        self.wecase_new.userClicked.connect(self.userClicked)
        self.wecase_new.tagClicked.connect(self.tagClicked)
        self.wecase_new.show()

    def refresh(self):
        tweetView = self.currentTweetView()
        tweetView.model().timelineLoaded.connect(self.moveToTop)
        tweetView.refresh()
        self.reset_remind()

    def currentTweetView(self):
        # The most tricky part of MainWindow.
        return self.tabWidget.currentWidget().layout().itemAt(0).widget()

    def saveConfig(self):
        self.config.mainwindow_geometry = getGeometry(self)
        self.config.save()

    def closeEvent(self, event):
        self.systray.hide()
        self.hide()
        self.saveConfig()
        self.timer.stop(True)
        # Reset uid when the thread exited.
        self.info["uid"] = None
        logging.info("Die")


class NotifyBadgeDrawer():

    def fillEllipse(self, p, x, y, size, extra, brush):
        path = QtGui.QPainterPath()
        path.addEllipse(x, y, size + extra, size)
        p.fillPath(path, brush)

    def drawBadge(self, p, x, y, size, text, brush):
        p.setFont(QtGui.QFont(QtGui.QWidget().font().family(), size * 1 / 2,
                              QtGui.QFont.Bold))

        # Method 1:
        #while (size - p.fontMetrics().width(text) < 6):
        #    pointSize = p.font().pointSize() - 1
        #    if pointSize < 6:
        #        weight = QtGui.QFont.Normal
        #    else:
        #        weight = QtGui.QFont.Bold
        #    p.setFont(QtGui.QFont(p.font().family(), p.font().pointSize() - 1, weight))
        # Method 2:
        extra = (len(text) - 1) * 10
        x -= extra

        shadowColor = QtGui.QColor(0, 0, 0, size)
        self.fillEllipse(p, x + 1, y, size, extra, shadowColor)
        self.fillEllipse(p, x - 1, y, size, extra, shadowColor)
        self.fillEllipse(p, x, y + 1, size, extra, shadowColor)
        self.fillEllipse(p, x, y - 1, size, extra, shadowColor)

        p.setPen(QtGui.QPen(QtCore.Qt.white, 2))
        self.fillEllipse(p, x, y, size - 3, extra, brush)
        p.drawEllipse(x, y, size - 3 + extra, size - 3)

        p.setPen(QtGui.QPen(QtCore.Qt.white, 1))
        p.drawText(x, y, size - 3 + extra, size - 3, QtCore.Qt.AlignCenter, text)

    def draw(self, _pixmap, text):
        pixmap = QtGui.QPixmap(_pixmap)
        if text == "0":
            return pixmap
        if len(text) > 2:
            text = "N"

        size = 15
        redGradient = QtGui.QRadialGradient(0.0, 0.0, 17.0, size - 3, size - 3)
        redGradient.setColorAt(0.0, QtGui.QColor(0xe0, 0x84, 0x9b))
        redGradient.setColorAt(0.5, QtGui.QColor(0xe9, 0x34, 0x43))
        redGradient.setColorAt(1.0, QtGui.QColor(0xec, 0x0c, 0x00))

        topRight = pixmap.rect().topRight()
        # magic, don't touch
        offset = topRight.x() - size / 2 - size / 4 - size / 7.5

        p = QtGui.QPainter(pixmap)
        p.setRenderHint(QtGui.QPainter.TextAntialiasing)
        p.setRenderHint(QtGui.QPainter.Antialiasing)
        self.drawBadge(p, offset, 0, size, text, QtGui.QBrush(redGradient))
        p.end()

        return pixmap


class WTabBar(QtGui.QTabBar):

    def __init__(self, parent=None):
        super(WTabBar, self).__init__(parent)
        self.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.contextMenu)
        self.__protect = []

    def mouseReleaseEvent(self, e):
        if e.button() == QtCore.Qt.MiddleButton:
            self.closeTab(e.pos())
        super(WTabBar, self).mouseReleaseEvent(e)

    def contextMenu(self, pos):
        if self.isProtected(pos):
            return

        closeAction = QtGui.QAction(self)
        closeAction.setText(self.tr("&Close"))
        closeAction.triggered.connect(lambda: self.closeTab(pos))

        menu = QtGui.QMenu()
        menu.addAction(closeAction)
        menu.exec(self.mapToGlobal(pos))

    def isProtected(self, pos):
        if self.parent().widget(self.tabAt(pos)) in self.__protect:
            return True
        return False

    def closeTab(self, pos):
        if self.isProtected(pos):
            return False
        self.parent().tabCloseRequested.emit(self.tabAt(pos))
        return True

    def setProtectTab(self, tabWidget, state):
        if state and tabWidget not in self.__protect:
            self.__protect.append(tabWidget)
        elif not state:
            self.__protect.remove(tabWidget)

    def protectTab(self, tabWidget):
        return (tabWidget in self.__protect)

########NEW FILE########
__FILENAME__ = WeHack
#!/usr/bin/env python3
# vim: tabstop=8 expandtab shiftwidth=4 softtabstop=4

# WeCase -- This file implemented
#           "The Hackable Utils Library" - many useful small functions.
# Copyright (C) 2013, 2014 The WeCase Developers.
# License: GPL v3 or later.


from threading import Thread
import sys
import os
import platform
import webbrowser


def workaround_excepthook_bug():
    # HACK: Python Exception Hook doesn't work in other threads.
    # There is a workaround.
    # See: http://bugs.python.org/issue1230540
    init_old = Thread.__init__

    # insert dirty hack
    def init(self, *args, **kwargs):
        init_old(self, *args, **kwargs)
        run_old = self.run

        def run_with_except_hook(*args, **kw):
            try:
                run_old(*args, **kw)
            except (KeyboardInterrupt, SystemExit):
                raise
            except:
                sys.excepthook(*sys.exc_info())

        self.run = run_with_except_hook

    # Monkey patching Thread
    Thread.__init__ = init


def async(func):
    def exec_thread(*args):
        return Thread(group=None, target=func, args=args).start()
    return exec_thread


class Singleton(type):
    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(Singleton, cls).__call__(*args, **kwargs)
        return cls._instances[cls]


class SingletonDecorator():

    def __init__(self, cls):
        self.cls = cls
        self.instance = None

    def __call__(self, *args, **kwargs):
        if self.instance is None:
            self.instance = self.cls(*args, **kwargs)
        return self.instance


@async
def start(filename):
    if platform.system() == "Linux":
        os.system('xdg-open "%s" > /dev/null' % filename)
    elif platform.system() == "Darwin":
        os.system('open "%s"' % filename)
    elif platform.system().startswith("CYGWIN"):
        os.system('cygstart "%s"' % filename)
    elif platform.system() == "Windows":
        os.system('start "" "%s"' % filename)
    else:
        assert False


def pid_running(pid):
    if platform.system() == "Windows":
        return _windows_pid_running(pid)
    else:
        try:
            return _unix_pid_running(pid)
        except Exception:
            assert False, "Unsupported platform."


def _windows_pid_running(pid):
    import ctypes
    kernel32 = ctypes.windll.kernel32
    SYNCHRONIZE = 0x100000

    process = kernel32.OpenProcess(SYNCHRONIZE, 0, pid)
    if process:
        kernel32.CloseHandle(process)
        return True
    else:
        return False


def _unix_pid_running(pid):
    try:
        # pretend to kill it
        os.kill(pid, 0)
    except OSError as e:
        # we don't have the permission to kill it, confirms the pid is exist.
        return e.errno == os.errno.EPERM
    return True


def getDirSize(path):
    total_size = 0
    for dirpath, dirnames, filenames in os.walk(path):
        for f in filenames:
            fp = os.path.join(dirpath, f)
            total_size += os.path.getsize(fp)
    return total_size


def clearDir(folder):
    for the_file in os.listdir(folder):
        file_path = os.path.join(folder, the_file)
        try:
            if os.path.isfile(file_path):
                os.unlink(file_path)
            elif os.path.isdir(file_path):
                try:
                    clearDir(file_path)
                except RuntimeError:
                    # but WHO creating dirs with more than sys.getrecursionlimit() subdirs?
                    return
        except OSError:
            pass


def UNUSED(var):
    return var


def getGeometry(qWidget):
    return {"height": qWidget.height(),
            "width": qWidget.width(),
            "x": qWidget.x(),
            "y": qWidget.y()}


def setGeometry(qWidget, geometry_dic):
    width = geometry_dic.get("width")
    height = geometry_dic.get("height")
    if width and height:
        qWidget.resize(width, height)

    x = geometry_dic.get("x")
    y = geometry_dic.get("y")
    if x and y:
        qWidget.move(x, y)


def openLink(link):
    if not link:
        # not a link
        pass
    elif not "://" in link:
        # no protocol
        link = "http://" + link
        webbrowser.open(link)
    elif "http://" in link:
        webbrowser.open(link)

########NEW FILE########
__FILENAME__ = WeiboErrorHandler
#!/usr/bin/env python3
# vim: tabstop=8 expandtab shiftwidth=4 softtabstop=4

# WeCase -- This file implemented an Error handler for Sina's API.
# Copyright (C) 2013, 2014 The WeCase Developers.
# License: GPL v3 or later.


from PyQt4 import QtCore, QtGui


class APIErrorWindow(QtCore.QObject):

    raiseException = QtCore.pyqtSignal(Exception)

    def __init__(self, parent=None):
        super(APIErrorWindow, self).__init__(parent)
        self.raiseException.connect(self.showAPIException)

        self.ERRORS = {
            20101: self.tr("This tweet have been deleted."),
            20704: self.tr("This tweet have been collected already."),
            20003: self.tr("User doesn't exists."),
            20006: self.tr("Image is too large."),
            20012: self.tr("Text is too long."),
            20016: self.tr("Your send too many tweets in a short time."),
            20019: self.tr("Don't send reperted tweet."),
            20018: self.tr("Your tweet contains illegal website."),
            20020: self.tr("Your tweet contains ads."),
            20021: self.tr("Your tweet contains illegal text."),
            20022: self.tr("Your IP address is in the blacklist."),
            20032: self.tr("Send successful, but your tweet won't display immediately, please wait for a minute."),
            20101: self.tr("The tweet does not exist."),
            20111: self.tr("Don't send reperted tweet.")}

    @QtCore.pyqtSlot(Exception)
    def showAPIException(self, exception):
        try:
            error_message = self.ERRORS[exception.error_code]
        except KeyError:
            error_message = "%d: %s" % (exception.error_code, exception.error)
        QtGui.QMessageBox.warning(None, self.tr("Error"), error_message)

########NEW FILE########
__FILENAME__ = client
#!/usr/bin/env python3
# vim: tabstop=8 expandtab shiftwidth=4 softtabstop=4

# WeCase -- This file implemented a wrapper of sinaweibopy3
#           with enhanced error handling.
# Copyright (C) 2013, 2014 The WeCase Developers.
# License: GPL v3 or later.


from weibo3 import APIClient, APIError, _Callable, _Executable
from http.client import BadStatusLine
from urllib.error import URLError, ContentTooShortError


class UBClient(APIClient):

    def __init__(self, *args, **kwargs):
        super(UBClient, self).__init__(*args, **kwargs)

    def __getattr__(self, attr):
        if "__" in attr:
            return super(UBClient, self).__getattr__(attr)
        return _UBCallable(self, attr)


class _UBCallable(_Callable):

    def __init__(self, *args, **kwargs):
        super(_UBCallable, self).__init__(*args, **kwargs)

    def __getattr__(self, attr):
        if attr == "get":
            return _UBExecutable(self._client, "GET", self._name)
        elif attr == "post":
            return _UBExecutable(self._client, "POST", self._name)
        else:
            name = "%s/%s" % (self._name, attr)
            return _UBCallable(self._client, name)


class _UBExecutable(_Executable):

    # if you find out more, add the error code to the tuple
    UNREASONABLE_ERRORS = (21321, )

    def __init__(self, *args, **kwargs):
        super(_UBExecutable, self).__init__(*args, **kwargs)

    def __call__(self, **kw):
        while 1:
            try:
                return super(_UBExecutable, self).__call__(**kw)
            except (BadStatusLine, ContentTooShortError, URLError, OSError, IOError):
                # these are common networking problems:
                # note: OSError/IOError = Bad CRC32 Checksum
                continue
            except APIError as e:
                # these are unreasonable API Errors:
                # note: May caused by bugs on Sina's server
                if e.error_code in self.UNREASONABLE_ERRORS:
                    continue
                else:
                    raise

########NEW FILE########
__FILENAME__ = helper
#!/usr/bin/env python3
# vim: tabstop=8 expandtab shiftwidth=4 softtabstop=4

# WeCase -- This file implemented a wrapper of sinaweibopy3
#           with helper functions.
# Copyright (C) 2013, 2014 The WeCase Developers.
# License: GPL v3 or later.


import sys
sys.path.append("..")
from weibos.client import UBClient
import const


SUCCESS = 1
PASSWORD_ERROR = -1
NETWORK_ERROR = -2


def UBAuthorize(username, password):
    client = UBClient(app_key=const.APP_KEY,
                      app_secret=const.APP_SECRET,
                      redirect_uri=const.CALLBACK_URL)

    try:
        # Step 1: Get the authorize url from Sina
        authorize_url = client.get_authorize_url()

        # Step 2: Send the authorize info to Sina and get the authorize_code
        authorize_code = _authorize(authorize_url, username, password)
        if not authorize_code:
            return PASSWORD_ERROR

        # Step 3: Get the access token by authorize_code
        r = client.request_access_token(authorize_code)

        # Step 4: Setup the access token of SDK
        client.set_access_token(r.access_token, r.expires_in)
        const.client = client
        return SUCCESS
    except Exception:
        return NETWORK_ERROR


def _authorize(authorize_url, username, password):
    """Send the authorize info to Sina and get the authorize_code"""
    import urllib.request
    import urllib.parse
    import urllib.error
    import http.client
    import ssl
    import socket

    oauth2 = const.OAUTH2_PARAMETER
    oauth2['userId'] = username
    oauth2['passwd'] = password
    postdata = urllib.parse.urlencode(oauth2)

    conn = http.client.HTTPSConnection('api.weibo.com')
    sock = socket.create_connection((conn.host, conn.port), conn.timeout, conn.source_address)
    conn.sock = ssl.wrap_socket(sock, conn.key_file, conn.cert_file, ssl_version=ssl.PROTOCOL_TLSv1)

    conn.request('POST', '/oauth2/authorize', postdata,
                 {'Referer': authorize_url,
                  'Content-Type': 'application/x-www-form-urlencoded'})

    res = conn.getresponse()
    location = res.getheader('location')

    if not location:
        return False

    authorize_code = location.split('=')[1]
    conn.close()
    return authorize_code

########NEW FILE########
__FILENAME__ = WeRuntimeInfo
#!/usr/bin/env python3
# vim: tabstop=8 expandtab shiftwidth=4 softtabstop=4

# WeCase -- This file implemented a dict wrapper allowing to save and read
#           the global shared data.
# Copyright (C) 2013, 2014 The WeCase Developers.
# License: GPL v3 or later.


from WeHack import Singleton


class WeRuntimeInfo(dict, metaclass=Singleton):
    def __init__(self, *args):
        dict.__init__(self, args)

########NEW FILE########
__FILENAME__ = WIconLabel
#!/usr/bin/env python3
# vim: tabstop=8 expandtab shiftwidth=4 softtabstop=4

# WeCase -- This file implemented a label with a icon.
# Copyright (C) 2013, 2014 The WeCase Developers.
# License: GPL v3 or later.


from PyQt4 import QtCore, QtGui


class WIconLabel(QtGui.QLabel):

    clicked = QtCore.pyqtSignal()
    imageAtLeft = 1
    imageAtRight = 2
    imageAtTop = 3
    imageAtBottom = 4

    def __init__(self, parent=None):
        super(WIconLabel, self).__init__(parent)
        self._icon = ""
        self._icon_code = ""
        self._text = ""
        self._position = self.imageAtLeft

    def text(self):
        return self._text

    def setText(self, text):
        self._text = text
        if self._position != self.imageAtBottom:
            text = "<center>" + self._icon_code + text + "</center>"
        else:
            text = "<center>" + text + self._icon_code + "</center>"
        super(WIconLabel, self).setText(text)

    def icon(self):
        return self._icon

    def setIcon(self, icon):
        self._icon = icon
        if self._position == self.imageAtLeft:
            self._icon_code = "<img src=\"%s\" />" % icon
        elif self._position == self.imageAtRight:
            self._icon_code = "<img src=\"%s\" />" % icon
        elif self._position == self.imageAtTop:
            self._icon_code = "<img src=\"%s\" />" % icon + "<br />"
        elif self._position == self.imageAtBottom:
            self._icon_code = "<br />" + "<img src=\"%s\" />" % icon
        self.setText(self._text)

    def position(self):
        return self._position

    def setPosition(self, pos):
        self._position = pos
        self.setIcon(self._icon)

    def mouseReleaseEvent(self, e):
        self.clicked.emit()

########NEW FILE########
__FILENAME__ = WImageLabel
#!/usr/bin/env python3
# vim: tabstop=8 expandtab shiftwidth=4 softtabstop=4

# WeCase -- This file implemented WImageLabel.
# Copyright (C) 2013, 2014 The WeCase Developers.
# License: GPL v3 or later.


from PyQt4 import QtCore, QtGui


class WImageLabel(QtGui.QLabel):

    clicked = QtCore.pyqtSignal()

    def __init__(self, parent=None):
        super(WImageLabel, self).__init__(parent)

    def setImageFile(self, path, start=True):
        self.setMovie(QtGui.QMovie(path), start)

    def setMovie(self, movie, start=True):
        super(WImageLabel, self).setMovie(movie)
        start and movie.start()

    def start(self):
        self.movie().start()

    def stop(self):
        self.movie().stop()

    def mouseReleaseEvent(self, e):
        if e.button() == QtCore.Qt.LeftButton:
            self.clicked.emit()

########NEW FILE########
__FILENAME__ = WObjectCache
#!/usr/bin/env python3
# vim: tabstop=8 expandtab shiftwidth=4 softtabstop=4

# WeCase -- This file implemented a very simple object cache by
#           using dict hashes.
# Copyright (C) 2013, 2014 The WeCase Developers.
# License: GPL v3 or later.


from WeHack import Singleton


class WObjectCache(metaclass=Singleton):

    def __init__(self):
        self.__objects = {}

    def __calculate_key(self, object, key):
        return str(id(object)) + str(key)

    def open(self, object, key, *args):
        # TODO: Using LRU Cache to free memory.
        hash_key = self.__calculate_key(object, key)
        if hash_key in self.__objects.keys():
            return self.__objects[hash_key]
        obj = object(key, *args)
        self.__objects[hash_key] = obj
        return obj

########NEW FILE########
__FILENAME__ = WSwitchLabel
#!/usr/bin/env python3
# vim: tabstop=8 expandtab shiftwidth=4 softtabstop=4

# WeCase -- This file implemented a label allowing to switch
#           from multiple images.
# Copyright (C) 2013, 2014 The WeCase Developers.
# License: GPL v3 or later.


from PyQt4 import QtCore, QtGui
from WImageLabel import WImageLabel
from WAsyncLabel import WAsyncLabel


class WSwitchLabel(QtGui.QWidget):

    clicked = QtCore.pyqtSignal()

    def __init__(self, parent=None):
        super(WSwitchLabel, self).__init__(parent)
        self._imagesList = []
        self._currentImage = None

        self._layout = QtGui.QHBoxLayout(self)

        self._leftLabel = WImageLabel(self)
        self._leftLabel.setText("<-")
        self._leftLabel.clicked.connect(self._last)
        self._layout.addWidget(self._leftLabel)

        self._imageLabel = WAsyncLabel(self)
        self._imageLabel.setAlignment(QtCore.Qt.AlignCenter)
        self._imageLabel.clicked.connect(self.clicked)
        self._layout.addWidget(self._imageLabel)

        self._rightLabel = WImageLabel(self)
        self._rightLabel.setText("->")
        self._rightLabel.clicked.connect(self._next)
        self._layout.addWidget(self._rightLabel)

        self.setLayout(self._layout)

    def _last(self):
        currentIndex = self._imagesList.index(self._currentImage)
        if currentIndex >= 1:
            self.setPixmap(self._imagesList[currentIndex - 1])

    def _next(self):
        currentIndex = self._imagesList.index(self._currentImage)
        if currentIndex < len(self._imagesList) - 1:
            self.setPixmap(self._imagesList[currentIndex + 1])

    def setImagesUrls(self, urls):
        self._imagesList = urls
        self.setPixmap(self._imagesList[0])

        if len(urls) == 1:
            self._leftLabel.hide()
            self._rightLabel.hide()
        elif len(urls) >= 1:
            self._leftLabel.show()
            self._rightLabel.show()

    def setPixmap(self, pixmap):
        self._currentImage = pixmap
        self._imageLabel.setPixmap(pixmap)

    def __getattr__(self, attr):
        return eval("self._imageLabel." + attr)

########NEW FILE########
__FILENAME__ = WTimeParser
#!/usr/bin/env python3
# vim: tabstop=8 expandtab shiftwidth=4 softtabstop=4

# WeCase -- This model implemented a dateutil-compatible parser
#           for Sina's time format.
# Copyright (C) 2013, 2014 The WeCase Developers.
# License: GPL v3 or later.


from datetime import datetime, timedelta, tzinfo


class tzoffset(tzinfo):
    """Genenal Timezone without DST"""
    ZERO = timedelta(0)

    def __init__(self, tzname, utcoffset):
        super(tzoffset, self).__init__()

        self.utcoffset_value = timedelta(hours=utcoffset / 3600)
        self.tzname_value = tzname

    def utcoffset(self, dt):
        return self.utcoffset_value

    def tzname(self, dt):
        return self.tzname

    def dst(self, dt):
        return self.ZERO


class WTimeParser():
    MONTHS = {"Jan": 1, "Feb": 2, "Mar": 3, "Apr": 4,
              "May": 5, "Jun": 6, "Jul": 7, "Aug": 8,
              "Sep": 9, "Oct": 10, "Nov": 11, "Dec": 12}

    def parse(self, time_string):
        """
        Sina's time-string parser.

        >>> t.parse("Sat Apr 06 00:49:30 +0800 2013")
        datetime(2013, 4, 6, 0, 49, 30, tzinfo=tzoffset(None, 28800))
        """

        date_list = time_string.split(' ')
        year = int(date_list[5])
        month = self.MONTHS[date_list[1]]
        day = int(date_list[2])

        time = date_list[3].split(':')
        hour = int(time[0])
        minute = int(time[1])
        second = int(time[2])

        timezone_str = date_list[4]
        timezone_offset = int(timezone_str[0:3]) * 3600

        return datetime(year, month, day, hour, minute, second,
                        tzinfo=tzoffset(None, timezone_offset))

########NEW FILE########
__FILENAME__ = WTimeParser_test
#!/usr/bin/env python3
# vim: tabstop=8 expandtab shiftwidth=4 softtabstop=4

# WeCase -- This file implemented the unit tests for WTimeParser.
# Copyright (C) 2013, 2014 The WeCase Developers.
# License: GPL v3 or later.


import unittest
from datetime import datetime
from WTimeParser import WTimeParser, tzoffset


class WTimeParserTest(unittest.TestCase):

    def setUp(self):
        self.parser = WTimeParser()

    def test_parse(self):
        got_daytime = self.parser.parse("Sat Apr 06 00:49:30 +0800 2013")
        except_daytime = datetime(2013, 4, 6, 0, 49, 30, tzinfo=tzoffset(None, 28800))
        self.assertEqual(got_daytime, except_daytime)


if __name__ == "__main__":
    unittest.main()

########NEW FILE########
__FILENAME__ = WTimer
#!/usr/bin/env python3
# vim: tabstop=8 expandtab shiftwidth=4 softtabstop=4

# WeCase -- This file implemented a more flexible timer than QTimer.
# Copyright (C) 2013, 2014 The WeCase Developers.
# License: GPL v3 or later.


from threading import Thread, Event


class WTimer(Thread):

    def __init__(self, run_function, sleep_time):
        super(WTimer, self).__init__()
        self.sleep_time = sleep_time
        self.run_function = run_function
        self._stop_event = Event()

    def run(self):
        while not self._stop_event.is_set():
            self._stop_event.wait(self.sleep_time)
            self.run_function()

    def stop(self, join=False):
        self._stop_event.set()
        if join:
            self.join()

########NEW FILE########
__FILENAME__ = WTweetLabel
#!/usr/bin/env python3
# vim: tabstop=8 expandtab shiftwidth=4 softtabstop=4

# WeCase -- This file implemented a label-like QTextBrowser for
#           displaying tweets.
# Copyright (C) 2013, 2014 The WeCase Developers.
# License: GPL v3 or later.


from PyQt4 import QtCore, QtGui
from WeHack import openLink


class WTweetLabel(QtGui.QTextBrowser):

    userClicked = QtCore.pyqtSignal(str, int)
    tagClicked = QtCore.pyqtSignal(str, int)

    def __init__(self, parent=None):
        super(WTweetLabel, self).__init__(parent)
        self.setReadOnly(True)
        self.setFrameStyle(QtGui.QFrame.NoFrame)
        pal = self.palette()
        pal.setColor(QtGui.QPalette.Base, QtCore.Qt.transparent)
        self.setPalette(pal)

        self.setOpenLinks(False)
        self.setOpenExternalLinks(False)
        self.anchorClicked.connect(self.openLink)
        self.setLineWrapMode(QtGui.QTextEdit.WidgetWidth)
        self.setWordWrapMode(QtGui.QTextOption.WrapAtWordBoundaryOrAnywhere)
        self.connect(self.document().documentLayout(),
                     QtCore.SIGNAL("documentSizeChanged(QSizeF)"),
                     QtCore.SLOT("adjustMinimumSize(QSizeF)"))
        self.__mouseButton = QtCore.Qt.LeftButton

    def mouseReleaseEvent(self, e):
        self.__mouseButton = e.button()
        if e.button() == QtCore.Qt.MiddleButton:
            anchor = QtCore.QUrl(self.anchorAt(e.pos()))
            self.anchorClicked.emit(anchor)
        super(WTweetLabel, self).mouseReleaseEvent(e)

    @QtCore.pyqtSlot(QtCore.QSizeF)
    def adjustMinimumSize(self, size):
        self.setMinimumHeight(size.height() + 2 * self.frameWidth())

    def openLink(self, url):
        url = url.toString()

        if "mentions://" in url:
            self.userClicked.emit(url[13:], self.__mouseButton)
        elif "hashtag://" in url:
            self.tagClicked.emit(url[11:].replace("#", ""), self.__mouseButton)
        else:
            # common web link
            openLink(url)

        self.__mouseButton = QtCore.Qt.LeftButton

########NEW FILE########
__FILENAME__ = debug
# -*- coding: utf-8 -*-
"""
debug.py - Functions to aid in debugging
Copyright 2010  Luke Campagnola
Distributed under MIT/X11 license. See license.txt for more infomation.
"""

import sys, traceback, time, gc, re, types, weakref, inspect, os, cProfile
import ptime
from numpy import ndarray
from PyQt4 import QtCore, QtGui

__ftraceDepth = 0
def ftrace(func):
    """Decorator used for marking the beginning and end of function calls.
    Automatically indents nested calls.
    """
    def w(*args, **kargs):
        global __ftraceDepth
        pfx = "  " * __ftraceDepth
        print(pfx + func.__name__ + " start")
        __ftraceDepth += 1
        try:
            rv = func(*args, **kargs)
        finally:
            __ftraceDepth -= 1
        print(pfx + func.__name__ + " done")
        return rv
    return w

def getExc(indent=4, prefix='|  '):
    tb = traceback.format_exc()
    lines = []
    for l in tb.split('\n'):
        lines.append(" "*indent + prefix + l)
    return '\n'.join(lines)

def printExc(msg='', indent=4, prefix='|'):
    """Print an error message followed by an indented exception backtrace
    (This function is intended to be called within except: blocks)"""
    exc = getExc(indent, prefix + '  ')
    print("[%s]  %s\n" % (time.strftime("%H:%M:%S"), msg))
    print(" "*indent + prefix + '='*30 + '>>')
    print(exc)
    print(" "*indent + prefix + '='*30 + '<<')

def printTrace(msg='', indent=4, prefix='|'):
    """Print an error message followed by an indented stack trace"""
    trace = backtrace(1)
    #exc = getExc(indent, prefix + '  ')
    print("[%s]  %s\n" % (time.strftime("%H:%M:%S"), msg))
    print(" "*indent + prefix + '='*30 + '>>')
    for line in trace.split('\n'):
        print(" "*indent + prefix + " " + line)
    print(" "*indent + prefix + '='*30 + '<<')


def backtrace(skip=0):
    return ''.join(traceback.format_stack()[:-(skip+1)])


def listObjs(regex='Q', typ=None):
    """List all objects managed by python gc with class name matching regex.
    Finds 'Q...' classes by default."""
    if typ is not None:
        return [x for x in gc.get_objects() if isinstance(x, typ)]
    else:
        return [x for x in gc.get_objects() if re.match(regex, type(x).__name__)]



def findRefPath(startObj, endObj, maxLen=8, restart=True, seen={}, path=None, ignore=None):
    """Determine all paths of object references from startObj to endObj"""
    refs = []
    if path is None:
        path = [endObj]
    if ignore is None:
        ignore = {}
    ignore[id(sys._getframe())] = None
    ignore[id(path)] = None
    ignore[id(seen)] = None
    prefix = " "*(8-maxLen)
    #print prefix + str(map(type, path))
    prefix += " "
    if restart:
        #gc.collect()
        seen.clear()
    gc.collect()
    newRefs = [r for r in gc.get_referrers(endObj) if id(r) not in ignore]
    ignore[id(newRefs)] = None
    #fo = allFrameObjs()
    #newRefs = []
    #for r in gc.get_referrers(endObj):
        #try:
            #if r not in fo:
                #newRefs.append(r)
        #except:
            #newRefs.append(r)

    for r in newRefs:
        #print prefix+"->"+str(type(r))
        if type(r).__name__ in ['frame', 'function', 'listiterator']:
            #print prefix+"  FRAME"
            continue
        try:
            if any([r is x for x in  path]):
                #print prefix+"  LOOP", objChainString([r]+path)
                continue
        except:
            print(r)
            print(path)
            raise
        if r is startObj:
            refs.append([r])
            print(refPathString([startObj]+path))
            continue
        if maxLen == 0:
            #print prefix+"  END:", objChainString([r]+path)
            continue
        ## See if we have already searched this node.
        ## If not, recurse.
        tree = None
        try:
            cache = seen[id(r)]
            if cache[0] >= maxLen:
                tree = cache[1]
                for p in tree:
                    print(refPathString(p+path))
        except KeyError:
            pass

        ignore[id(tree)] = None
        if tree is None:
            tree = findRefPath(startObj, r, maxLen-1, restart=False, path=[r]+path, ignore=ignore)
            seen[id(r)] = [maxLen, tree]
        ## integrate any returned results
        if len(tree) == 0:
            #print prefix+"  EMPTY TREE"
            continue
        else:
            for p in tree:
                refs.append(p+[r])
        #seen[id(r)] = [maxLen, refs]
    return refs


def objString(obj):
    """Return a short but descriptive string for any object"""
    try:
        if type(obj) in [int, int, float]:
            return str(obj)
        elif isinstance(obj, dict):
            if len(obj) > 5:
                return "<dict {%s,...}>" % (",".join(list(obj.keys())[:5]))
            else:
                return "<dict {%s}>" % (",".join(list(obj.keys())))
        elif isinstance(obj, str):
            if len(obj) > 50:
                return '"%s..."' % obj[:50]
            else:
                return obj[:]
        elif isinstance(obj, ndarray):
            return "<ndarray %s %s>" % (str(obj.dtype), str(obj.shape))
        elif hasattr(obj, '__len__'):
            if len(obj) > 5:
                return "<%s [%s,...]>" % (type(obj).__name__, ",".join([type(o).__name__ for o in obj[:5]]))
            else:
                return "<%s [%s]>" % (type(obj).__name__, ",".join([type(o).__name__ for o in obj]))
        else:
            return "<%s %s>" % (type(obj).__name__, obj.__class__.__name__)
    except:
        return str(type(obj))

def refPathString(chain):
    """Given a list of adjacent objects in a reference path, print the 'natural' path
    names (ie, attribute names, keys, and indexes) that follow from one object to the next ."""
    s = objString(chain[0])
    i = 0
    while i < len(chain)-1:
        #print " -> ", i
        i += 1
        o1 = chain[i-1]
        o2 = chain[i]
        cont = False
        if isinstance(o1, list) or isinstance(o1, tuple):
            if any([o2 is x for x in o1]):
                s += "[%d]" % o1.index(o2)
                continue
        #print "  not list"
        if isinstance(o2, dict) and hasattr(o1, '__dict__') and o2 == o1.__dict__:
            i += 1
            if i >= len(chain):
                s += ".__dict__"
                continue
            o3 = chain[i]
            for k in o2:
                if o2[k] is o3:
                    s += '.%s' % k
                    cont = True
                    continue
        #print "  not __dict__"
        if isinstance(o1, dict):
            try:
                if o2 in o1:
                    s += "[key:%s]" % objString(o2)
                    continue
            except TypeError:
                pass
            for k in o1:
                if o1[k] is o2:
                    s += "[%s]" % objString(k)
                    cont = True
                    continue
        #print "  not dict"
        #for k in dir(o1):  ## Not safe to request attributes like this.
            #if getattr(o1, k) is o2:
                #s += ".%s" % k
                #cont = True
                #continue
        #print "  not attr"
        if cont:
            continue
        s += " ? "
        sys.stdout.flush()
    return s


def objectSize(obj, ignore=None, verbose=False, depth=0, recursive=False):
    """Guess how much memory an object is using"""
    ignoreTypes = [types.MethodType, types.UnboundMethodType, types.BuiltinMethodType, types.FunctionType, types.BuiltinFunctionType]
    ignoreRegex = re.compile('(method-wrapper|Flag|ItemChange|Option|Mode)')


    if ignore is None:
        ignore = {}

    indent = '  '*depth

    try:
        hash(obj)
        hsh = obj
    except:
        hsh = "%s:%d" % (str(type(obj)), id(obj))

    if hsh in ignore:
        return 0
    ignore[hsh] = 1

    try:
        size = sys.getsizeof(obj)
    except TypeError:
        size = 0

    if isinstance(obj, ndarray):
        try:
            size += len(obj.data)
        except:
            pass


    if recursive:
        if type(obj) in [list, tuple]:
            if verbose:
                print(indent+"list:")
            for o in obj:
                s = objectSize(o, ignore=ignore, verbose=verbose, depth=depth+1)
                if verbose:
                    print(indent+'  +', s)
                size += s
        elif isinstance(obj, dict):
            if verbose:
                print(indent+"list:")
            for k in obj:
                s = objectSize(obj[k], ignore=ignore, verbose=verbose, depth=depth+1)
                if verbose:
                    print(indent+'  +', k, s)
                size += s
        #elif isinstance(obj, QtCore.QObject):
            #try:
                #childs = obj.children()
                #if verbose:
                    #print indent+"Qt children:"
                #for ch in childs:
                    #s = objectSize(obj, ignore=ignore, verbose=verbose, depth=depth+1)
                    #size += s
                    #if verbose:
                        #print indent + '  +', ch.objectName(), s

            #except:
                #pass
    #if isinstance(obj, types.InstanceType):
        gc.collect()
        if verbose:
            print(indent+'attrs:')
        for k in dir(obj):
            if k in ['__dict__']:
                continue
            o = getattr(obj, k)
            if type(o) in ignoreTypes:
                continue
            strtyp = str(type(o))
            if ignoreRegex.search(strtyp):
                continue
            #if isinstance(o, types.ObjectType) and strtyp == "<type 'method-wrapper'>":
                #continue

            #if verbose:
                #print indent, k, '?'
            refs = [r for r in gc.get_referrers(o) if type(r) != types.FrameType]
            if len(refs) == 1:
                s = objectSize(o, ignore=ignore, verbose=verbose, depth=depth+1)
                size += s
                if verbose:
                    print(indent + "  +", k, s)
            #else:
                #if verbose:
                    #print indent + '  -', k, len(refs)
    return size

class GarbageWatcher:
    """
    Convenient dictionary for holding weak references to objects.
    Mainly used to check whether the objects have been collect yet or not.

    Example:
        gw = GarbageWatcher()
        gw['objName'] = obj
        gw['objName2'] = obj2
        gw.check()


    """
    def __init__(self):
        self.objs = weakref.WeakValueDictionary()
        self.allNames = []

    def add(self, obj, name):
        self.objs[name] = obj
        self.allNames.append(name)

    def __setitem__(self, name, obj):
        self.add(obj, name)

    def check(self):
        """Print a list of all watched objects and whether they have been collected."""
        gc.collect()
        dead = self.allNames[:]
        alive = []
        for k in self.objs:
            dead.remove(k)
            alive.append(k)
        print("Deleted objects:", dead)
        print("Live objects:", alive)

    def __getitem__(self, item):
        return self.objs[item]


class Profiler:
    """Simple profiler allowing measurement of multiple time intervals.

    Example:
        prof = Profiler('Function')
          ... do stuff ...
        prof.mark('did stuff')
          ... do other stuff ...
        prof.mark('did other stuff')
        prof.finish()
    """
    depth = 0

    def __init__(self, msg="Profiler", disabled=False):
        self.depth = Profiler.depth
        Profiler.depth += 1

        self.disabled = disabled
        if disabled:
            return
        self.t0 = ptime.time()
        self.t1 = self.t0
        self.msg = "  "*self.depth + msg
        print(self.msg, ">>> Started")

    def mark(self, msg=''):
        if self.disabled:
            return
        t1 = ptime.time()
        print("  "+self.msg, msg, "%gms" % ((t1-self.t1)*1000))
        self.t1 = t1

    def finish(self):
        if self.disabled:
            return
        t1 = ptime.time()
        print(self.msg, '<<< Finished, total time:', "%gms" % ((t1-self.t0)*1000))

    def __del__(self):
        Profiler.depth -= 1


def profile(code, name='profile_run', sort='cumulative', num=30):
    """Common-use for cProfile"""
    cProfile.run(code, name)
    stats = pstats.Stats(name)
    stats.sort_stats(sort)
    stats.print_stats(num)
    return stats



#### Code for listing (nearly) all objects in the known universe
#### http://utcc.utoronto.ca/~cks/space/blog/python/GetAllObjects
# Recursively expand slist's objects
# into olist, using seen to track
# already processed objects.
def _getr(slist, olist, first=True):
    i = 0
    for e in slist:

        oid = id(e)
        typ = type(e)
        if oid in olist or typ is int or typ is int:    ## or e in olist:     ## since we're excluding all ints, there is no longer a need to check for olist keys
            continue
        olist[oid] = e
        if first and (i%1000) == 0:
            gc.collect()
        tl = gc.get_referents(e)
        if tl:
            _getr(tl, olist, first=False)
        i += 1
# The public function.
def get_all_objects():
    """Return a list of all live Python objects (excluding int and long), not including the list itself."""
    gc.collect()
    gcl = gc.get_objects()
    olist = {}
    _getr(gcl, olist)

    del olist[id(olist)]
    del olist[id(gcl)]
    del olist[id(sys._getframe())]
    return olist


def lookup(oid, objects=None):
    """Return an object given its ID, if it exists."""
    if objects is None:
        objects = get_all_objects()
    return objects[oid]




class ObjTracker:
    """
    Tracks all objects under the sun, reporting the changes between snapshots: what objects are created, deleted, and persistent.
    This class is very useful for tracking memory leaks. The class goes to great (but not heroic) lengths to avoid tracking
    its own internal objects.

    Example:
        ot = ObjTracker()   # takes snapshot of currently existing objects
           ... do stuff ...
        ot.diff()           # prints lists of objects created and deleted since ot was initialized
           ... do stuff ...
        ot.diff()           # prints lists of objects created and deleted since last call to ot.diff()
                            # also prints list of items that were created since initialization AND have not been deleted yet
                            #   (if done correctly, this list can tell you about objects that were leaked)

        arrays = ot.findPersistent('ndarray')  ## returns all objects matching 'ndarray' (string match, not instance checking)
                                               ## that were considered persistent when the last diff() was run

        describeObj(arrays[0])    ## See if we can determine who has references to this array
    """


    allObjs = {} ## keep track of all objects created and stored within class instances
    allObjs[id(allObjs)] = None

    def __init__(self):
        self.startRefs = {}        ## list of objects that exist when the tracker is initialized {oid: weakref}
                                   ##   (If it is not possible to weakref the object, then the value is None)
        self.startCount = {}
        self.newRefs = {}          ## list of objects that have been created since initialization
        self.persistentRefs = {}   ## list of objects considered 'persistent' when the last diff() was called
        self.objTypes = {}

        ObjTracker.allObjs[id(self)] = None
        self.objs = [self.__dict__, self.startRefs, self.startCount, self.newRefs, self.persistentRefs, self.objTypes]
        self.objs.append(self.objs)
        for v in self.objs:
            ObjTracker.allObjs[id(v)] = None

        self.start()

    def findNew(self, regex):
        """Return all objects matching regex that were considered 'new' when the last diff() was run."""
        return self.findTypes(self.newRefs, regex)

    def findPersistent(self, regex):
        """Return all objects matching regex that were considered 'persistent' when the last diff() was run."""
        return self.findTypes(self.persistentRefs, regex)


    def start(self):
        """
        Remember the current set of objects as the comparison for all future calls to diff()
        Called automatically on init, but can be called manually as well.
        """
        refs, count, objs = self.collect()
        for r in self.startRefs:
            self.forgetRef(self.startRefs[r])
        self.startRefs.clear()
        self.startRefs.update(refs)
        for r in refs:
            self.rememberRef(r)
        self.startCount.clear()
        self.startCount.update(count)
        #self.newRefs.clear()
        #self.newRefs.update(refs)

    def diff(self, **kargs):
        """
        Compute all differences between the current object set and the reference set.
        Print a set of reports for created, deleted, and persistent objects
        """
        refs, count, objs = self.collect()   ## refs contains the list of ALL objects

        ## Which refs have disappeared since call to start()  (these are only displayed once, then forgotten.)
        delRefs = {}
        for i in list(self.startRefs.keys()):
            if i not in refs:
                delRefs[i] = self.startRefs[i]
                del self.startRefs[i]
                self.forgetRef(delRefs[i])
        for i in list(self.newRefs.keys()):
            if i not in refs:
                delRefs[i] = self.newRefs[i]
                del self.newRefs[i]
                self.forgetRef(delRefs[i])
        #print "deleted:", len(delRefs)

        ## Which refs have appeared since call to start() or diff()
        persistentRefs = {}      ## created since start(), but before last diff()
        createRefs = {}          ## created since last diff()
        for o in refs:
            if o not in self.startRefs:
                if o not in self.newRefs:
                    createRefs[o] = refs[o]          ## object has been created since last diff()
                else:
                    persistentRefs[o] = refs[o]      ## object has been created since start(), but before last diff() (persistent)
        #print "new:", len(newRefs)

        ## self.newRefs holds the entire set of objects created since start()
        for r in self.newRefs:
            self.forgetRef(self.newRefs[r])
        self.newRefs.clear()
        self.newRefs.update(persistentRefs)
        self.newRefs.update(createRefs)
        for r in self.newRefs:
            self.rememberRef(self.newRefs[r])
        #print "created:", len(createRefs)

        ## self.persistentRefs holds all objects considered persistent.
        self.persistentRefs.clear()
        self.persistentRefs.update(persistentRefs)


        print("----------- Count changes since start: ----------")
        c1 = count.copy()
        for k in self.startCount:
            c1[k] = c1.get(k, 0) - self.startCount[k]
        typs = list(c1.keys())
        typs.sort(lambda a,b: cmp(c1[a], c1[b]))
        for t in typs:
            if c1[t] == 0:
                continue
            num = "%d" % c1[t]
            print("  " + num + " "*(10-len(num)) + str(t))

        print("-----------  %d Deleted since last diff: ------------" % len(delRefs))
        self.report(delRefs, objs, **kargs)
        print("-----------  %d Created since last diff: ------------" % len(createRefs))
        self.report(createRefs, objs, **kargs)
        print("-----------  %d Created since start (persistent): ------------" % len(persistentRefs))
        self.report(persistentRefs, objs, **kargs)


    def __del__(self):
        self.startRefs.clear()
        self.startCount.clear()
        self.newRefs.clear()
        self.persistentRefs.clear()

        del ObjTracker.allObjs[id(self)]
        for v in self.objs:
            del ObjTracker.allObjs[id(v)]

    @classmethod
    def isObjVar(cls, o):
        return type(o) is cls or id(o) in cls.allObjs

    def collect(self):
        print("Collecting list of all objects...")
        gc.collect()
        objs = get_all_objects()
        frame = sys._getframe()
        del objs[id(frame)]  ## ignore the current frame
        del objs[id(frame.f_code)]

        ignoreTypes = [int, int]
        refs = {}
        count = {}
        for k in objs:
            o = objs[k]
            typ = type(o)
            oid = id(o)
            if ObjTracker.isObjVar(o) or typ in ignoreTypes:
                continue

            try:
                ref = weakref.ref(obj)
            except:
                ref = None
            refs[oid] = ref
            typ = type(o)
            typStr = typeStr(o)
            self.objTypes[oid] = typStr
            ObjTracker.allObjs[id(typStr)] = None
            count[typ] = count.get(typ, 0) + 1

        print("All objects: %d   Tracked objects: %d" % (len(objs), len(refs)))
        return refs, count, objs

    def forgetRef(self, ref):
        if ref is not None:
            del ObjTracker.allObjs[id(ref)]

    def rememberRef(self, ref):
        ## Record the address of the weakref object so it is not included in future object counts.
        if ref is not None:
            ObjTracker.allObjs[id(ref)] = None


    def lookup(self, oid, ref, objs=None):
        if ref is None or ref() is None:
            try:
                obj = lookup(oid, objects=objs)
            except:
                obj = None
        else:
            obj = ref()
        return obj


    def report(self, refs, allobjs=None, showIDs=False):
        if allobjs is None:
            allobjs = get_all_objects()

        count = {}
        rev = {}
        for oid in refs:
            obj = self.lookup(oid, refs[oid], allobjs)
            if obj is None:
                typ = "[del] " + self.objTypes[oid]
            else:
                typ = typeStr(obj)
            if typ not in rev:
                rev[typ] = []
            rev[typ].append(oid)
            c = count.get(typ, [0,0])
            count[typ] =  [c[0]+1, c[1]+objectSize(obj)]
        typs = list(count.keys())
        typs.sort(lambda a,b: cmp(count[a][1], count[b][1]))

        for t in typs:
            line = "  %d\t%d\t%s" % (count[t][0], count[t][1], t)
            if showIDs:
                line += "\t"+",".join(map(str,rev[t]))
            print(line)

    def findTypes(self, refs, regex):
        allObjs = get_all_objects()
        ids = {}
        objs = []
        r = re.compile(regex)
        for k in refs:
            if r.search(self.objTypes[k]):
                objs.append(self.lookup(k, refs[k], allObjs))
        return objs




def describeObj(obj, depth=4, path=None, ignore=None):
    """
    Trace all reference paths backward, printing a list of different ways this object can be accessed.
    Attempts to answer the question "who has a reference to this object"
    """
    if path is None:
        path = [obj]
    if ignore is None:
        ignore = {}   ## holds IDs of objects used within the function.
    ignore[id(sys._getframe())] = None
    ignore[id(path)] = None
    gc.collect()
    refs = gc.get_referrers(obj)
    ignore[id(refs)] = None
    printed=False
    for ref in refs:
        if id(ref) in ignore:
            continue
        if id(ref) in list(map(id, path)):
            print("Cyclic reference: " + refPathString([ref]+path))
            printed = True
            continue
        newPath = [ref]+path
        if len(newPath) >= depth:
            refStr = refPathString(newPath)
            if '[_]' not in refStr:           ## ignore '_' references generated by the interactive shell
                print(refStr)
            printed = True
        else:
            describeObj(ref, depth, newPath, ignore)
            printed = True
    if not printed:
        print("Dead end: " + refPathString(path))



def typeStr(obj):
    """Create a more useful type string by making <instance> types report their class."""
    typ = type(obj)
    if typ == types.InstanceType:
        return "<instance of %s>" % obj.__class__.__name__
    else:
        return str(typ)

def searchRefs(obj, *args):
    """Pseudo-interactive function for tracing references backward.
    Arguments:
        obj:   The initial object from which to start searching
        args:  A set of string or int arguments.
               each integer selects one of obj's referrers to be the new 'obj'
               each string indicates an action to take on the current 'obj':
                  t:  print the types of obj's referrers
                  l:  print the lengths of obj's referrers (if they have __len__)
                  i:  print the IDs of obj's referrers
                  o:  print obj
                  ro: return obj
                  rr: return list of obj's referrers

    Examples:
       searchRefs(obj, 't')                    ## Print types of all objects referring to obj
       searchRefs(obj, 't', 0, 't')            ##   ..then select the first referrer and print the types of its referrers
       searchRefs(obj, 't', 0, 't', 'l')       ##   ..also print lengths of the last set of referrers
       searchRefs(obj, 0, 1, 'ro')             ## Select index 0 from obj's referrer, then select index 1 from the next set of referrers, then return that object

    """
    ignore = {id(sys._getframe()): None}
    gc.collect()
    refs = gc.get_referrers(obj)
    ignore[id(refs)] = None
    refs = [r for r in refs if id(r) not in ignore]
    for a in args:

        #fo = allFrameObjs()
        #refs = [r for r in refs if r not in fo]

        if type(a) is int:
            obj = refs[a]
            gc.collect()
            refs = gc.get_referrers(obj)
            ignore[id(refs)] = None
            refs = [r for r in refs if id(r) not in ignore]
        elif a == 't':
            print(list(map(typeStr, refs)))
        elif a == 'i':
            print(list(map(id, refs)))
        elif a == 'l':
            def slen(o):
                if hasattr(o, '__len__'):
                    return len(o)
                else:
                    return None
            print(list(map(slen, refs)))
        elif a == 'o':
            print(obj)
        elif a == 'ro':
            return obj
        elif a == 'rr':
            return refs

def allFrameObjs():
    """Return list of frame objects in current stack. Useful if you want to ignore these objects in refernece searches"""
    f = sys._getframe()
    objs = []
    while f is not None:
        objs.append(f)
        objs.append(f.f_code)
        #objs.append(f.f_locals)
        #objs.append(f.f_globals)
        #objs.append(f.f_builtins)
        f = f.f_back
    return objs


def findObj(regex):
    """Return a list of objects whose typeStr matches regex"""
    allObjs = get_all_objects()
    objs = []
    r = re.compile(regex)
    for i in allObjs:
        obj = allObjs[i]
        if r.search(typeStr(obj)):
            objs.append(obj)
    return objs



def listRedundantModules():
    """List modules that have been imported more than once via different paths."""
    mods = {}
    for name, mod in sys.modules.items():
        if not hasattr(mod, '__file__'):
            continue
        mfile = os.path.abspath(mod.__file__)
        if mfile[-1] == 'c':
            mfile = mfile[:-1]
        if mfile in mods:
            print("module at %s has 2 names: %s, %s" % (mfile, name, mods[mfile]))
        else:
            mods[mfile] = name


def walkQObjectTree(obj, counts=None, verbose=False, depth=0):
    """
    Walk through a tree of QObjects, doing nothing to them.
    The purpose of this function is to find dead objects and generate a crash
    immediately rather than stumbling upon them later.
    Prints a count of the objects encountered, for fun. (or is it?)
    """

    if verbose:
        print("  "*depth + typeStr(obj))
    report = False
    if counts is None:
        counts = {}
        report = True
    typ = str(type(obj))
    try:
        counts[typ] += 1
    except KeyError:
        counts[typ] = 1
    for child in obj.children():
        walkQObjectTree(child, counts, verbose, depth+1)

    return counts

QObjCache = {}
def qObjectReport(verbose=False):
    """Generate a report counting all QObjects and their types"""
    global qObjCache
    count = {}
    for obj in findObj('PyQt'):
        if isinstance(obj, QtCore.QObject):
            oid = id(obj)
            if oid not in QObjCache:
                QObjCache[oid] = typeStr(obj) + "  " + obj.objectName()
                try:
                    QObjCache[oid] += "  " + obj.parent().objectName()
                    QObjCache[oid] += "  " + obj.text()
                except:
                    pass
            print("check obj", oid, str(QObjCache[oid]))
            if obj.parent() is None:
                walkQObjectTree(obj, count, verbose)

    typs = list(count.keys())
    typs.sort()
    for t in typs:
        print(count[t], "\t", t)


########NEW FILE########
__FILENAME__ = depgraph
#!/usr/bin/python3
import sys


def process_import(filename, statement):
    statement = statement.replace(",", " ")
    modules = statement.split()
    for module in modules[1:]:
        print('"%s" -> "%s"' % (filename, module))

def process_from(filename, statement):
    statement = statement.replace(",", " ")
    modules = statement.split()
    main_module = modules[1]
    for module in modules[3:]:
        print('"%s" -> "%s" -> "%s"' % (filename, main_module, module))

def print_header():
    print("digraph WeCase {")
    print("ratio=2")

def print_footer():
    print("}")

print_header()
for line in sys.stdin:
    line = line.replace("\n", "")
    if line.endswith(".py"):
        filename = line
    else:
        if line.startswith("import"):
            process_import(filename, line)
        elif line.startswith("from"):
            process_from(filename, line)
print_footer()

########NEW FILE########
__FILENAME__ = objgraph
"""
Ad-hoc tools for drawing Python object reference graphs with graphviz.

This module is more useful as a repository of sample code and ideas, than
as a finished product.  For documentation and background, read

  http://mg.pov.lt/blog/hunting-python-memleaks.html
  http://mg.pov.lt/blog/python-object-graphs.html
  http://mg.pov.lt/blog/object-graphs-with-graphviz.html

in that order.  Then use pydoc to read the docstrings, as there were
improvements made since those blog posts.

Copyright (c) 2008 Marius Gedminas <marius@pov.lt>

Released under the MIT licence.


Changes
=======

1.1dev (2008-09-05)
-------------------

New function: show_refs() for showing forward references.

New functions: typestats() and show_most_common_types().

Object boxes are less crammed with useless information (such as IDs).

Spawns xdot if it is available.
"""
# Permission is hereby granted, free of charge, to any person obtaining a
# copy of this software and associated documentation files (the "Software"),
# to deal in the Software without restriction, including without limitation
# the rights to use, copy, modify, merge, publish, distribute, sublicense,
# and/or sell copies of the Software, and to permit persons to whom the
# Software is furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
# DEALINGS IN THE SOFTWARE.

__author__ = "Marius Gedminas (marius@gedmin.as)"
__copyright__ = "Copyright (c) 2008 Marius Gedminas"
__license__ = "MIT"
__version__ = "1.1dev"
__date__ = "2008-09-05"


import gc
import inspect
import types
import weakref
import operator
import os


def count(typename):
    """Count objects tracked by the garbage collector with a given class name.

    Example:

        >>> count('dict')
        42
        >>> count('MyClass')
        3

    Note that the GC does not track simple objects like int or str.
    """
    return sum(1 for o in gc.get_objects() if type(o).__name__ == typename)


def typestats():
    """Count the number of instances for each type tracked by the GC.

    Note that the GC does not track simple objects like int or str.

    Note that classes with the same name but defined in different modules
    will be lumped together.
    """
    stats = {}
    for o in gc.get_objects():
        stats.setdefault(type(o).__name__, 0)
        stats[type(o).__name__] += 1
    return stats


def show_most_common_types(limit=10):
    """Count the names of types with the most instances.

    Note that the GC does not track simple objects like int or str.

    Note that classes with the same name but defined in different modules
    will be lumped together.
    """
    stats = sorted(list(typestats().items()), key=operator.itemgetter(1),
                   reverse=True)
    if limit:
        stats = stats[:limit]
    width = max(len(name) for name, count in stats)
    for name, count in stats[:limit]:
        print(name.ljust(width), count)


def by_type(typename):
    """Return objects tracked by the garbage collector with a given class name.

    Example:

        >>> by_type('MyClass')
        [<mymodule.MyClass object at 0x...>]

    Note that the GC does not track simple objects like int or str.
    """
    return [o for o in gc.get_objects() if type(o).__name__ == typename]


def at(addr):
    """Return an object at a given memory address.

    The reverse of id(obj):

        >>> at(id(obj)) is obj
        True

    Note that this function does not work on objects that are not tracked by
    the GC (e.g. ints or strings).
    """
    for o in gc.get_objects():
        if id(o) == addr:
            return o
    return None


def find_backref_chain(obj, predicate, max_depth=20, extra_ignore=()):
    """Find a shortest chain of references leading to obj.

    The start of the chain will be some object that matches your predicate.

    ``max_depth`` limits the search depth.

    ``extra_ignore`` can be a list of object IDs to exclude those objects from
    your search.

    Example:

        >>> find_backref_chain(obj, inspect.ismodule)
        [<module ...>, ..., obj]

    Returns None if such a chain could not be found.
    """
    queue = [obj]
    depth = {id(obj): 0}
    parent = {id(obj): None}
    ignore = set(extra_ignore)
    ignore.add(id(extra_ignore))
    ignore.add(id(queue))
    ignore.add(id(depth))
    ignore.add(id(parent))
    ignore.add(id(ignore))
    gc.collect()
    while queue:
        target = queue.pop(0)
        if predicate(target):
            chain = [target]
            while parent[id(target)] is not None:
                target = parent[id(target)]
                chain.append(target)
            return chain
        tdepth = depth[id(target)]
        if tdepth < max_depth:
            referrers = gc.get_referrers(target)
            ignore.add(id(referrers))
            for source in referrers:
                if inspect.isframe(source) or id(source) in ignore:
                    continue
                if id(source) not in depth:
                    depth[id(source)] = tdepth + 1
                    parent[id(source)] = target
                    queue.append(source)
    return None # not found


def show_backrefs(objs, max_depth=3, extra_ignore=(), filter=None, too_many=10,
                  highlight=None):
    """Generate an object reference graph ending at ``objs``

    The graph will show you what objects refer to ``objs``, directly and
    indirectly.

    ``objs`` can be a single object, or it can be a list of objects.

    Produces a Graphviz .dot file and spawns a viewer (xdot) if one is
    installed, otherwise converts the graph to a .png image.

    Use ``max_depth`` and ``too_many`` to limit the depth and breadth of the
    graph.

    Use ``filter`` (a predicate) and ``extra_ignore`` (a list of object IDs) to
    remove undesired objects from the graph.

    Use ``highlight`` (a predicate) to highlight certain graph nodes in blue.

    Examples:

        >>> show_backrefs(obj)
        >>> show_backrefs([obj1, obj2])
        >>> show_backrefs(obj, max_depth=5)
        >>> show_backrefs(obj, filter=lambda x: not inspect.isclass(x))
        >>> show_backrefs(obj, highlight=inspect.isclass)
        >>> show_backrefs(obj, extra_ignore=[id(locals())])

    """
    show_graph(objs, max_depth=max_depth, extra_ignore=extra_ignore,
               filter=filter, too_many=too_many, highlight=highlight,
               edge_func=gc.get_referrers, swap_source_target=False)


def show_refs(objs, max_depth=3, extra_ignore=(), filter=None, too_many=10,
              highlight=None):
    """Generate an object reference graph starting at ``objs``

    The graph will show you what objects are reachable from ``objs``, directly
    and indirectly.

    ``objs`` can be a single object, or it can be a list of objects.

    Produces a Graphviz .dot file and spawns a viewer (xdot) if one is
    installed, otherwise converts the graph to a .png image.

    Use ``max_depth`` and ``too_many`` to limit the depth and breadth of the
    graph.

    Use ``filter`` (a predicate) and ``extra_ignore`` (a list of object IDs) to
    remove undesired objects from the graph.

    Use ``highlight`` (a predicate) to highlight certain graph nodes in blue.

    Examples:

        >>> show_refs(obj)
        >>> show_refs([obj1, obj2])
        >>> show_refs(obj, max_depth=5)
        >>> show_refs(obj, filter=lambda x: not inspect.isclass(x))
        >>> show_refs(obj, highlight=inspect.isclass)
        >>> show_refs(obj, extra_ignore=[id(locals())])

    """
    show_graph(objs, max_depth=max_depth, extra_ignore=extra_ignore,
               filter=filter, too_many=too_many, highlight=highlight,
               edge_func=gc.get_referents, swap_source_target=True)

#
# Internal helpers
#

def show_graph(objs, edge_func, swap_source_target,
               max_depth=3, extra_ignore=(), filter=None, too_many=10,
               highlight=None):
    if not isinstance(objs, (list, tuple)):
        objs = [objs]
    f = open('objects.dot', 'w')
    print('digraph ObjectGraph {', file=f)
    print('  node[shape=box, style=filled, fillcolor=white];', file=f)
    queue = []
    depth = {}
    ignore = set(extra_ignore)
    ignore.add(id(objs))
    ignore.add(id(extra_ignore))
    ignore.add(id(queue))
    ignore.add(id(depth))
    ignore.add(id(ignore))
    for obj in objs:
        print('  %s[fontcolor=red];' % (obj_node_id(obj)), file=f)
        depth[id(obj)] = 0
        queue.append(obj)
    gc.collect()
    nodes = 0
    while queue:
        nodes += 1
        target = queue.pop(0)
        tdepth = depth[id(target)]
        print('  %s[label="%s"];' % (obj_node_id(target), obj_label(target, tdepth)), file=f)
        h, s, v = gradient((0, 0, 1), (0, 0, .3), tdepth, max_depth)
        if inspect.ismodule(target):
            h = .3
            s = 1
        if highlight and highlight(target):
            h = .6
            s = .6
            v = 0.5 + v * 0.5
        print('  %s[fillcolor="%g,%g,%g"];' % (obj_node_id(target), h, s, v), file=f)
        if v < 0.5:
            print('  %s[fontcolor=white];' % (obj_node_id(target)), file=f)
        if inspect.ismodule(target) or tdepth >= max_depth:
            continue
        neighbours = edge_func(target)
        ignore.add(id(neighbours))
        n = 0
        for source in neighbours:
            if inspect.isframe(source) or id(source) in ignore:
                continue
            if filter and not list(filter(source)):
                continue
            if swap_source_target:
                srcnode, tgtnode = target, source
            else:
                srcnode, tgtnode = source, target
            elabel = edge_label(srcnode, tgtnode)
            print('  %s -> %s%s;' % (obj_node_id(srcnode), obj_node_id(tgtnode), elabel), file=f)
            if id(source) not in depth:
                depth[id(source)] = tdepth + 1
                queue.append(source)
            n += 1
            if n >= too_many:
                print('  %s[color=red];' % obj_node_id(target), file=f)
                break
    print("}", file=f)
    f.close()
    print("Graph written to objects.dot (%d nodes)" % nodes)
    if os.system('which xdot >/dev/null') == 0:
        print("Spawning graph viewer (xdot)")
        os.system("xdot objects.dot &")
    else:
        os.system("dot -Tpng objects.dot > objects.png")
        print("Image generated as objects.png")


def obj_node_id(obj):
    if isinstance(obj, weakref.ref):
        return 'all_weakrefs_are_one'
    return ('o%d' % id(obj)).replace('-', '_')


def obj_label(obj, depth):
    return quote(type(obj).__name__ + ':\n' +
                 safe_repr(obj))


def quote(s):
    return s.replace("\\", "\\\\").replace("\"", "\\\"").replace("\n", "\\n")


def safe_repr(obj):
    try:
        return short_repr(obj)
    except:
        return '(unrepresentable)'


def short_repr(obj):
    if isinstance(obj, (type, types.ModuleType, types.BuiltinMethodType,
                        types.BuiltinFunctionType)):
        return obj.__name__
    if isinstance(obj, types.MethodType):
        if obj.__self__ is not None:
            return obj.__func__.__name__ + ' (bound)'
        else:
            return obj.__func__.__name__
    if isinstance(obj, (tuple, list, dict, set)):
        return '%d items' % len(obj)
    if isinstance(obj, weakref.ref):
        return 'all_weakrefs_are_one'
    return repr(obj)[:40]


def gradient(start_color, end_color, depth, max_depth):
    if max_depth == 0:
        # avoid division by zero
        return start_color
    h1, s1, v1 = start_color
    h2, s2, v2 = end_color
    f = float(depth) / max_depth
    h = h1 * (1-f) + h2 * f
    s = s1 * (1-f) + s2 * f
    v = v1 * (1-f) + v2 * f
    return h, s, v


def edge_label(source, target):
    if isinstance(target, dict) and target is getattr(source, '__dict__', None):
        return ' [label="__dict__",weight=10]'
    elif isinstance(source, dict):
        for k, v in source.items():
            if v is target:
                if isinstance(k, str) and k:
                    return ' [label="%s",weight=2]' % quote(k)
                else:
                    return ' [label="%s"]' % quote(safe_repr(k))
    return ''


########NEW FILE########
__FILENAME__ = ptime
# -*- coding: utf-8 -*-
"""
ptime.py -  Precision time function made os-independent (should have been taken care of by python)
Copyright 2010  Luke Campagnola
Distributed under MIT/X11 license. See license.txt for more infomation.
"""


import sys
import time as systime
START_TIME = None
time = None

def winTime():
    """Return the current time in seconds with high precision (windows version, use Manager.time() to stay platform independent)."""
    return systime.clock() + START_TIME
    #return systime.time()

def unixTime():
    """Return the current time in seconds with high precision (unix version, use Manager.time() to stay platform independent)."""
    return systime.time()

if 'win' in sys.platform:
    cstart = systime.clock()  ### Required to start the clock in windows
    START_TIME = systime.time() - cstart
    
    time = winTime
else:
    time = unixTime


########NEW FILE########
