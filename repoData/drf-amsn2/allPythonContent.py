__FILENAME__ = backend

class aMSNBackendManager(object):
    def __init__(self, core):
        self._backend = None
        self._core = core
        self.switchToBackend('nullbackend')

    def setBackendForFunc(self, funcname, backend):
        try:
            f = getattr(backend, funcname)
            self.__setattr__(funcname, f)
        except AttributeError:
            self.__setattr__(funcname, self.__missingFunc)

    def switchToBackend(self, backend):
        try:
            m = __import__(backend, globals(), locals(), [], -1)
        except ImportError:
            m = __import__('defaultbackend', globals(), locals(), [], -1)
            print 'Trying to switch to non existent backend %s, using default instead' % backend
        backend_class = getattr(m, backend)

        del self._backend
        self._backend = backend_class()
        self._backend._core = self._core
        self.current_backend = backend

        # Config management methods
        self.setBackendForFunc('saveConfig', self._backend)
        self.setBackendForFunc('loadConfig', self._backend)

        # Account management methods
        self.setBackendForFunc('loadAccount', self._backend)
        self.setBackendForFunc('loadAccounts', self._backend)
        self.setBackendForFunc('saveAccount', self._backend)
        self.setBackendForFunc('setAccount', self._backend)
        self.setBackendForFunc('removeAccount', self._backend)
        self.setBackendForFunc('clean', self._backend)

        # DP
        self.setBackendForFunc('getFileLocationDP', self._backend)

        # Logs management methods
        # MSNObjects cache methods (Smileys, DPs, ...)
        # Webcam sessions methods
        # Files received
        # ...

    def __missingFunc(*args):
        print 'Function missing for %s' % self.current_backend



########NEW FILE########
__FILENAME__ = basebackend

class basebackend():
    """
    Base backend, used as a model to implement others backends.
    It contains the functions that should be available for every backend.
    """

    def saveConfig(self, amsn_account, config):
        raise NotImplementedError

    def loadConfig(self, amsn_account):
        raise NotImplementedError

    def loadAccount(self, email):
        raise NotImplementedError

    def loadAccounts(self):
        raise NotImplementedError

    def saveAccount(self, amsn_account):
        raise NotImplementedError

    def setAccount(self, email):
        raise NotImplementedError

    def clean(self):
        """
        Delete temporary things and prepare the backend to be detached
        or to begin another session with the same backend (e.g. with nullbackend)
        """
        raise NotImplementedError


    """ DPs """
    def getFileLocationDP(self, email, uid, shaci):
        raise NotImplementedError

    def getDPs(self, email):
        raise NotImplementedError

########NEW FILE########
__FILENAME__ = defaultaccountbackend

import os
from amsn2.core.views import AccountView
import basebackend

"""ElementTree independent from the available distribution"""
try:
    from xml.etree.cElementTree import *
except ImportError:
    try:
        from cElementTree import *
    except ImportError:
        from elementtree.ElementTree import *
import os

class defaultaccountbackend(basebackend.basebackend):
    """
    Save/load the account informations, should be used from all the backends.
    """

    def __init__(self):
        if os.name == "posix":
            self.accounts_dir = os.path.join(os.environ['HOME'], ".amsn2")
        elif os.name == "nt":
            self.accounts_dir = os.path.join(os.environ['USERPROFILE'], "amsn2")
        else:
            self.accounts_dir = os.path.join(os.curdir, "amsn2_accounts")

        try :
            os.makedirs(self.accounts_dir, 0700)
        except :
            pass

    def loadAccount(self, email):
        accview = None
        self.createAccountFileTree(email)
        accpath = os.path.join(self.account_dir, "account.xml")
        accfile = file(accpath, "r")
        root_tree = ElementTree(file=accfile)
        accfile.close()
        account = root_tree.getroot()
        if account.tag == "aMSNAccount":
            #email
            emailElmt = account.find("email")
            if emailElmt is None:
                return None
            accview = AccountView(self._core, emailElmt.text)
            #nick
            nickElmt = account.find("nick")
            if nickElmt is None:
                return None
            if nickElmt.text:
                accview.nick.appendText(nickElmt.text)
            #TODO: parse...
            #psm
            psmElmt = account.find("psm")
            if psmElmt is None:
                return None
            if psmElmt.text:
                accview.psm.appendText(psmElmt.text)
            #presence
            presenceElmt = account.find("presence")
            if presenceElmt is None:
                return None
            accview.presence = presenceElmt.text
            #password
            passwordElmt = account.find("password")
            if passwordElmt is None:
                accview.password = None
            else:
                accview.password = passwordElmt.text
            #save_password
            savePassElmt = account.find("save_password")
            if savePassElmt.text == "False":
                accview.save_password = False
            else:
                accview.save_password = True
            #autoconnect
            saveAutoConnect = account.find("autoconnect")
            if saveAutoConnect.text == "False":
                accview.autologin = False
            else:
                accview.autologin = True
            #TODO: use backend & all
            #dp
            dpElmt = account.find("dp")
            #TODO

            #TODO: preferred_ui ?

            accview.save = True

        return accview

    def loadAccounts(self):
        account_dirs = []
        for root, dirs, files in os.walk(self.accounts_dir):
            account_dirs = dirs
            break
        accountviews = []
        for account_dir in account_dirs:
            accv = self.loadAccount(os.path.join(self.accounts_dir, account_dir))
            if accv:
                accountviews.append(accv)
        return accountviews

    def createAccountFileTree(self, email):
        self.account_dir = os.path.join(self.accounts_dir, self._getDir(email))
        if not os.path.isdir(self.account_dir):
                os.makedirs(self.account_dir, 0700)
        self.dps_dir = os.path.join(self.account_dir, "displaypics")
        if not os.path.isdir(self.dps_dir):
                os.makedirs(self.dps_dir, 0700)

    def setAccount(self, email):
        self.createAccountFileTree(email)

    def saveAccount(self, amsn_account):
        if amsn_account.view is None or amsn_account.view.email is None:
            return false

        self.createAccountFileTree(amsn_account.view.email)
        amsn_account.backend_manager.saveConfig(amsn_account, amsn_account.config)
        #TODO: integrate with personnalinfo
        root_section = Element("aMSNAccount")
        #email
        emailElmt = SubElement(root_section, "email")
        emailElmt.text = amsn_account.view.email
        #nick
        nick = str(amsn_account.view.nick)
        nickElmt = SubElement(root_section, "nick")
        nickElmt.text = nick
        #psm
        psm = str(amsn_account.view.psm)
        psmElmt = SubElement(root_section, "psm")
        psmElmt.text = psm
        #presence
        presenceElmt = SubElement(root_section, "presence")
        presenceElmt.text = amsn_account.view.presence
        #password
        if amsn_account.view.save_password:
            passwdElmt = SubElement(root_section, "password")
            passwdElmt.text = amsn_account.view.password
        #dp
        #TODO ask the backend
        dpElmt = SubElement(root_section, "dp")
        #TODO

        #TODO: save or not, preferred_ui
        #
        #save password
        savePassElmt = SubElement(root_section, "save_password")
        savePassElmt.text = str(amsn_account.view.save_password)
        #autologin
        autologinElmt = SubElement(root_section, "autoconnect")
        autologinElmt.text = str(amsn_account.view.autologin)
        #TODO: backend for config/logs/...

        accpath = os.path.join(self.account_dir, "account.xml")
        xml_tree = ElementTree(root_section)
        xml_tree.write(accpath, encoding='utf-8')

    def removeAccount(self, email):
        accdir = os.path.join(self.accounts_dir, self._getDir(email))
        if os.path.isdir(accdir):
            for [root, subdirs, subfiles] in os.walk(accdir, False):
                for subfile in subfiles:
                    os.remove(os.path.join(root, subfile))
                for subdir in subdirs:
                    os.rmdir(os.path.join(root, subdir))
            os.rmdir(accdir)


    def getFileLocationDP(self, email, uid, shac):
        """ 
        Get location of display picture. A SHA sum is included in the filename,
        this is converted to hex.
        @return: string with filename.
        """
        dir = os.path.join(self.dps_dir, self._getDir(email))
        if not os.path.isdir(dir):
            os.makedirs(dir, 0700)
        return os.path.join(dir, shac.encode("hex")+".img")

    def _getDir(self, email):
        return email.lower().strip().replace("@","_at_")

########NEW FILE########
__FILENAME__ = defaultbackend

from amsn2.core.config import aMSNConfig
import os
import defaultaccountbackend

"""ElementTree independent from the available distribution"""
try:
    from xml.etree.cElementTree import *
except ImportError:
    try:
        from cElementTree import *
    except ImportError:
        from elementtree.ElementTree import *

class defaultbackend(defaultaccountbackend.defaultaccountbackend):
    """
    Backend used to save the config on the home directory of the user.
    """

    def __init__(self):
        defaultaccountbackend.defaultaccountbackend.__init__(self)

    def saveConfig(self, account, config):
        #TODO: improve
        root_section = Element("aMSNConfig")
        for e in config._config:
            val = config._config[e]
            elmt = SubElement(root_section, "entry",
                              type=type(val).__name__,
                              name=str(e))
            elmt.text = str(val)

        accpath = os.path.join(self.accounts_dir, self._getDir(account.view.email),
                               "config.xml")
        xml_tree = ElementTree(root_section)
        xml_tree.write(accpath, encoding='utf-8')

    def loadConfig(self, account):
        c = aMSNConfig()
        c.setKey("ns_server", "messenger.hotmail.com")
        c.setKey("ns_port", 1863)

        configpath = os.path.join(self.accounts_dir,
                                  self._getDir(account.view.email),
                                  "config.xml")
        try:
            configfile = file(configpath, "r")
        except IOError:
            return c
        configfile = file(configpath, "r")
        root_tree = ElementTree(file=configfile)
        configfile.close()
        config = root_tree.getroot()
        if config.tag == "aMSNConfig":
            lst = config.findall("entry")
            for elmt in lst:
                if elmt.attrib['type'] == 'int':
                    c.setKey(elmt.attrib['name'], int(elmt.text))
                else:
                    c.setKey(elmt.attrib['name'], elmt.text)
        return c

    def clean(self):
        pass


########NEW FILE########
__FILENAME__ = nullbackend

from amsn2.core.config import aMSNConfig
import defaultaccountbackend

import tempfile
import os

"""ElementTree independent from the available distribution"""
try:
    from xml.etree.cElementTree import *
except ImportError:
    try:
        from cElementTree import *
    except ImportError:
        from elementtree.ElementTree import *

class nullbackend(defaultaccountbackend.defaultaccountbackend):
    """
    Backend that will not save anything permanentely, used for on-the-fly-sessions.
    """

    def __init__(self):
        defaultaccountbackend.defaultaccountbackend.__init__(self)
        self.config_dir = None

    def setAccount(self, email):
        dir = tempfile.mkdtemp()
        self.accounts_dir = dir
        defaultaccountbackend.defaultaccountbackend.accounts_dir = dir
        defaultaccountbackend.defaultaccountbackend.setAccount(self, email)

    def saveConfig(self, account, config):
        # Is it necessary to temporarily save the config?
        pass

    def loadConfig(self, account):
        c = aMSNConfig()
        c._config = {"ns_server":'messenger.hotmail.com',
                       "ns_port":1863,
                     }
        return c

    def clean(self):
        if self.config_dir is not None and os.path.isdir(self.config_dir):
            for [root, subdirs, subfiles] in os.walk(self.config_dir, False):
                for subfile in subfiles:
                    os.remove(os.path.join(root, subfile))
                for subdir in subdirs:
                    os.rmdir(os.path.join(root, subdir))

    def __del__(self):
        if self.config_dir is not None:
            self.clean()
            os.rmdir(self.config_dir)



########NEW FILE########
__FILENAME__ = account_manager
import os
import Image
import logging
import papyon
import __builtin__
from views import AccountView
from views import StringView

logger = logging.getLogger('amsn2.core.account_manager')

class aMSNAccount(object):
    """ aMSNAccount : a Class to represent an aMSN account
    This class will contain all settings relative to an account
    and will store the protocol and GUI objects
    """
    #TODO: use the personnal info stuff instead of the view
    def __init__(self, core, accountview):
        """
        @type core: aMSNCore
        @type accountview: AccountView
        @type account_dir: str
        """

        self.view = accountview
        self.personalinfoview = core._personalinfo_manager._personalinfoview
        self.do_save = accountview.save
        self.backend_manager = core._backend_manager
        self.client = None
        self.lock()
        self.load()

    def signOut(self):
        if self.do_save:
            self.save()
        self.backend_manager.clean()
        self.unlock()

    def lock(self):
        #TODO
        pass

    def unlock(self):
        #TODO
        pass

    def load(self):
        #TODO:
        self.config = self.backend_manager.loadConfig(self)

    def save(self):
        self.view.nick = self.personalinfoview.nick
        self.view.psm = self.personalinfoview.psm
        self.view.dp = self.personalinfoview.dp
        self.backend_manager.saveAccount(self)

    def set_dp(self, path):
        if path:
            try:
                im = Image.open(path)
                im.resize((96, 96), Image.BILINEAR)

                # Write the file and rename it instead of creating a tmpfile
                profile = self.client.profile
                dp_path_tmp = self.backend_manager.getFileLocationDP(self.view.email, profile.id, 'tmp')
                im.save(dp_path_tmp, "PNG")
                f = open(dp_path_tmp)
                dp_object = papyon.p2p.MSNObject(self.client.profile,
                                                 os.path.getsize(dp_path_tmp),
                                                 papyon.p2p.MSNObjectType.DISPLAY_PICTURE,
                                                 os.path.basename(path),
                                                 os.path.basename(path),
                                                 data=f)
                f.close()

                dp_path = self.backend_manager.getFileLocationDP(self.view.email, profile.id, dp_object._data_sha)
                os.rename(dp_path_tmp, dp_path)

            except OSError, e:
                # FIXME: on Windows, it's raised if dp_path already exists
                # http://docs.python.org/library/os.html#os.rename
                logger.error('Trying to overwrite a saved dp')
                return

            except IOError, e:
                logger.error(e)
                return

            else:
                self.client.msn_object_store.publish(dp_object)
                self.personalinfoview.dp = dp_object

class aMSNAccountManager(object):
    """ aMSNAccountManager : The account manager that takes care of storing
    and retreiving all the account.
    """
    def __init__(self, core, options):
        self._core = core
        self.reload()

        if options.account is not None:
            pv = [p for p in self.accountviews if p.email == options.account]
            if pv:
                pv = pv[0]
                self.accountviews.remove(pv)
            else:
                pv = AccountView(core, options.account)
                pv.password = options.password
            self.accountviews.insert(0, pv)

    def reload(self):
        self.accountviews = self._core._backend_manager.loadAccounts()

    def getAllAccountViews(self):
        return self.accountviews

    def getAvailableAccountViews(self):
        return [v for v in self.accountviews if not self.isAccountLocked(v)]

    def signinToAccount(self, accountview):
        """
        @type accountview: AccountView
        @rtype: aMSNAccount
        """

        acc = aMSNAccount(self._core, accountview)

        if accountview.save:
            self._core._backend_manager.switchToBackend(accountview.preferred_backend)
            acc.backend_manager.saveAccount(acc)
        else:
            self._core._backend_manager.removeAccount(accountview.email)
            self._core._backend_manager.switchToBackend('nullbackend')
        acc.backend_manager.setAccount(accountview.email)

        acc.lock()
        return acc

    def isAccountLocked(self, accountview):
        """
        @type accountview: AccountView
        @rtype: bool
        @return: True if accountview is locked
        """

        #TODO
        return False


########NEW FILE########
__FILENAME__ = amsn
# -*- coding: utf-8 -*-
#
# amsn - a python client for the WLM Network
#
# Copyright (C) 2008 Dario Freddi <drf54321@gmail.com>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA

from amsn2 import gui
from amsn2 import protocol
from amsn2.backend import aMSNBackendManager
from views import *
from account_manager import *
from contactlist_manager import *
from conversation_manager import *
from oim_manager import *
from theme_manager import *
from personalinfo_manager import *
from event_manager import *

import papyon
import logging

# Top-level loggers
papyon_logger = logging.getLogger("papyon")
logger = logging.getLogger("amsn2")

class aMSNCore(object):
    def __init__(self, options):
        """
        Create a new aMSN Core. It takes an options class as argument
        which has a variable for each option the core is supposed to received.
        This is easier done using optparse.
        The options supported are :
           options.account = the account's username to use
           options.password = the account's password to use
           options.front_end = the front end's name to use
           options.debug = whether or not to enable debug output
        """
        self.p2s = {papyon.Presence.ONLINE:"online",
                    papyon.Presence.BUSY:"busy",
                    papyon.Presence.IDLE:"idle",
                    papyon.Presence.AWAY:"away",
                    papyon.Presence.BE_RIGHT_BACK:"brb",
                    papyon.Presence.ON_THE_PHONE:"phone",
                    papyon.Presence.OUT_TO_LUNCH:"lunch",
                    papyon.Presence.INVISIBLE:"hidden",
                    papyon.Presence.OFFLINE:"offline"}
        self.Presence = papyon.Presence

        self._event_manager = aMSNEventManager(self)
        self._options = options

        self._gui_name = None
        self._gui = None
        self._loop = None
        self._main = None
        self._account = None
        self.loadUI(self._options.front_end)

        self._backend_manager = aMSNBackendManager(self)
        self._account_manager = aMSNAccountManager(self, options)
        self._theme_manager = aMSNThemeManager(self)
        self._contactlist_manager = aMSNContactListManager(self)
        self._oim_manager = aMSNOIMManager(self)
        self._conversation_manager = aMSNConversationManager(self)
        self._personalinfo_manager = aMSNPersonalInfoManager(self)

        # TODO: redirect the logs somewhere, something like ctrl-s ctrl-d for amsn-0.9x
        logging.basicConfig(level=logging.WARNING)

        if self._options.debug_protocol:
            papyon_logger.setLevel(logging.DEBUG)
        else:
            papyon_logger.setLevel(logging.WARNING)

        if self._options.debug_amsn2:
            logger.setLevel(logging.DEBUG)
        else:
            logger.setLevel(logging.WARNING)

    def run(self):
        self._main.show()
        self._loop.run()

    def loadUI(self, ui_name):
        """
        @type ui_name: str
        @param ui_name: The name of the User Interface
        """

        self._gui_name = ui_name
        self._gui = gui.GUIManager(self, self._gui_name)
        if not self._gui.gui:
            print "Unable to load UI %s" %(self._gui_name,)
            self.quit()
        self._loop = self._gui.gui.aMSNMainLoop(self)
        self._main = self._gui.gui.aMSNMainWindow(self)
        self._skin_manager = self._gui.gui.SkinManager(self)

    def switchToUI(self, ui_name):
        """
        @type ui_name: str
        @param ui_name: The name of the User Interface
        """

        #TODO: unloadUI + stop loops??? + loadUI + run
        pass

    def mainWindowShown(self):
        # TODO : load the accounts from disk and all settings
        # then show the login window if autoconnect is disabled

        self._main.setTitle("aMSN 2 - Loading")


        splash = self._gui.gui.aMSNSplashScreen(self, self._main)
        image = ImageView()
        image.load("Filename","/path/to/image/here")

        splash.setImage(image)
        splash.setText("Loading...")
        splash.show()

        login = self._gui.gui.aMSNLoginWindow(self, self._main)

        login.setAccounts(self._account_manager.getAvailableAccountViews())

        splash.hide()
        self._main.setTitle("aMSN 2 - Login")
        login.show()

        menu = self.createMainMenuView()
        self._main.setMenu(menu)

    def getMainWindow(self):
        return self._main

    def signinToAccount(self, login_window, accountview):
        """
        @type login_window: aMSNLoginWindow
        @type accountview: AccountView
        """

        print "Signing in to account %s" % (accountview.email)
        self._account = self._account_manager.signinToAccount(accountview)
        self._account.login = login_window
        self._account.client = protocol.Client(self, self._account)
        self._account.client.connect(accountview.email, accountview.password)

    def signOutOfAccount(self):
        self._account.client.logout()
        self._account.signOut()

    def connectionStateChanged(self, account, state):
        """
        @type account: aMSNAccount
        @type state: L{papyon.event.ClientState}
        @param state: New state of the Client.
        """

        status_str = \
        {
            papyon.event.ClientState.CONNECTING : 'Connecting to server...',
            papyon.event.ClientState.CONNECTED : 'Connected',
            papyon.event.ClientState.AUTHENTICATING : 'Authenticating...',
            papyon.event.ClientState.AUTHENTICATED : 'Password accepted',
            papyon.event.ClientState.SYNCHRONIZING : 'Please wait while your contact list\nis being downloaded...',
            papyon.event.ClientState.SYNCHRONIZED : 'Contact list downloaded successfully.\nHappy Chatting'
        }

        if state in status_str:
            account.login.onConnecting((state + 1)/ 7., status_str[state])
        elif state == papyon.event.ClientState.OPEN:
            clwin = self._gui.gui.aMSNContactListWindow(self, self._main)
            clwin.account = account
            account.clwin = clwin
            account.login.hide()
            self._main.setTitle("aMSN 2")
            account.clwin.show()
            account.login = None

            self._personalinfo_manager.setAccount(account)
            self._contactlist_manager.onCLDownloaded(account.client.address_book)

    def idlerAdd(self, func):
        """
        @type func: function
        """

        self._loop.idlerAdd(func)

    def timerAdd(self, delay, func):
        """
        @type delay: int
        @param delay: delay in seconds?
        @type func: function
        """

        self._loop.timerAdd(delay, func)

    def quit(self):
        if self._account:
            self._account.signOut()
        if self._loop:
            self._loop.quit()
        logging.shutdown()
        exit(0)

    # TODO: move to UImanager
    def addContact(self):
        def contactCB(account, invite_msg):
            if account:
                self._contactlist_manager.addContact(account, self._account.view.email,
                                                     invite_msg, [])
        self._gui.gui.aMSNContactInputWindow(('Contact to add: ', 'Invite message: '),
                                             contactCB, ())

    def removeContact(self):
        def contactCB(account):
            if account:
                try:
                    papyon_contact = self._contactlist_manager._papyon_addressbook.\
                                                    contacts.search_by('account', account)[0]
                except IndexError:
                    self._gui.gui.aMSNErrorWindow('You don\'t have the %s contact!', account)
                    return

                self._contactlist_manager.removeContact(papyon_contact.id)

        self._gui.gui.aMSNContactDeleteWindow('Contact to remove: ', contactCB, ())

    def changeDP(self):
        self._gui.gui.aMSNDPChooserWindow(self._account.set_dp ,self._backend_manager)

    def createMainMenuView(self):
        menu = MenuView()
        quitMenuItem = MenuItemView(MenuItemView.COMMAND, label="Quit",
                                    command = self.quit)
        logOutMenuItem = MenuItemView(MenuItemView.COMMAND, label="Log out",
                                      command = self.signOutOfAccount)
        mainMenu = MenuItemView(MenuItemView.CASCADE_MENU, label="Main")
        mainMenu.addItem(logOutMenuItem)
        mainMenu.addItem(quitMenuItem)

        addContactItem = MenuItemView(MenuItemView.COMMAND, label="Add Contact",
                                      command=self.addContact)
        removeContact = MenuItemView(MenuItemView.COMMAND, label='Remove contact',
                                     command=self.removeContact)

        contactsMenu = MenuItemView(MenuItemView.CASCADE_MENU, label="Contacts")
        contactsMenu.addItem(addContactItem)
        contactsMenu.addItem(removeContact)

        menu.addItem(mainMenu)
        menu.addItem(contactsMenu)

        return menu


########NEW FILE########
__FILENAME__ = config



class aMSNConfig:
    def __init__(self):
        self._config = {}

    def getKey(self, key, default = None):
        """
        Get a existing config key or a default value in any other case.

        @type key: str
        @param key: name of the config key.
        @type default: Any
        @param default: default value to return if key doesn't exist.
        @rtype: Any
        @return: config key value.
        """

        try:
            return self._config[key]
        except KeyError:
            return default

    def setKey(self, key, value):
        """
        Set a key value

        @type key: str
        @param key: name of the config key.
        @type value: Any
        @param value: value of the key to be set.
        """

        self._config[key] = value

########NEW FILE########
__FILENAME__ = contactlist_manager
from views import *
import os
import tempfile
import papyon


class aMSNContactListManager:
    def __init__(self, core):
        """
        @type core: aMSNCore
        """

        self._core = core
        self._em = core._event_manager
        self._contacts = {} #Dictionary where every contact_uid has an associated aMSNContact
        self._groups = {}
        self._papyon_addressbook = None

    #TODO: sorting contacts & groups

    ''' normal changes of a contact '''

    def onContactChanged(self, papyon_contact):
        """ Called when a contact changes either its presence, nick, psm or current media."""

        #1st/ update the aMSNContact object
        c = self.getContact(papyon_contact.id, papyon_contact)
        c.fill(papyon_contact)
        #2nd/ update the ContactView
        cv = ContactView(self._core, c)
        self._em.emit(self._em.events.CONTACTVIEW_UPDATED, cv)

        #TODO: update the group view

    def onContactDPChanged(self, papyon_contact):
        """ Called when a contact changes its Display Picture. """

        #Request the DP...
        c = self.getContact(papyon_contact.id, papyon_contact)
        if ("Theme", "dp_nopic") in c.dp.imgs:
            c.dp.load("Theme", "dp_loading")
        elif papyon_contact.msn_object is None:
            c.dp.load("Theme", "dp_nopic")
            self._em.emit(self._em.events.AMSNCONTACT_UPDATED, c)
            cv = ContactView(self._core, c)
            self._em.emit(self._em.events.CONTACTVIEW_UPDATED, cv)
            return

        if (papyon_contact.presence is not papyon.Presence.OFFLINE and
            papyon_contact.msn_object):
            self._core._account.client.msn_object_store.request(papyon_contact.msn_object,
                                                                (self.onDPdownloaded,
                                                                 papyon_contact.id))

    def onDPdownloaded(self, msn_object, uid):
        #1st/ update the aMSNContact object
        try:
            c = self.getContact(uid)
        except ValueError:
            return
        fn = self._core._backend_manager.getFileLocationDP(c.account, uid,
                                                           msn_object._data_sha)
        try:
            f = open(fn, 'w+b', 0700)
            try:
                f.write(msn_object._data.read())
            finally:
                f.close()
        except IOError:
            return
        c.dp.load("Filename", fn)
        self._em.emit(self._em.events.AMSNCONTACT_UPDATED, c)
        #2nd/ update the ContactView
        cv = ContactView(self._core, c)
        self._em.emit(self._em.events.CONTACTVIEW_UPDATED, cv)

    ''' changes to the address book '''

# actions from user: accept/decline contact invitation - block/unblock contact - add/remove/rename group - add/remove contact to/from group

    def addContact(self, account, invite_display_name='amsn2',
            invite_message='hola', groups=[]):
        self._papyon_addressbook.add_messenger_contact(account, invite_display_name)

    def onContactAdded(self, contact):
        c = self.getContact(contact.id, contact)
        gids = [ g.id for g in self.getGroups(contact.id)]
        self._addContactToGroups(contact.id, gids)
        self._core._gui.gui.aMSNNotificationWindow("Contact %s added!" % contact.account)

    def removeContact(self, uid):
        def cb_ok():
            self._papyon_addressbook.delete_contact(self._papyon_addressbook.contacts.
                                                 search_by('id', uid)[0])
        # call the UImanager for all the dialogs
        self._core._gui.gui.aMSNDialogWindow('Are you sure you want to remove the contact %s?'
                                             % self._papyon_addressbook.contacts.search_by('id', uid)[0].account,
                                             (('OK', cb_ok), ('Cancel', lambda : '')))

    def onContactRemoved(self, contact):
        self._removeContactFromGroups(contact.id)
        del self._contacts[contact.id]
        # TODO: Move to the UImanager
        self._core._gui.gui.aMSNNotificationWindow("Contact %s removed!" % contact.account)

    ''' additional methods '''

    # used when a contact is deleted, moved or change status to offline
    def _removeContactFromGroups(self, cid):
        groups = self.getGroups(cid)
        for g in groups:
            g.contacts.remove(cid)
            gv = GroupView(self._core, g.id, g.name, g.contacts)
            self._em.emit(self._em.events.GROUPVIEW_UPDATED, gv)

    def _addContactToGroups(self, cid, gids):
        for gid in gids:
            g = self.getGroup(gid)
            g.contacts.add(cid)
            gv = GroupView(self._core, g.id, g.name, g.contacts)
            self._em.emit(self._em.events.GROUPVIEW_UPDATED, gv)

        c = self.getContact(cid)
        cv = ContactView(self._core, c)
        self._em.emit(self._em.events.CONTACTVIEW_UPDATED, cv)

    def onCLDownloaded(self, address_book):
        self._papyon_addressbook = address_book
        grpviews = []
        cviews = []
        clv = ContactListView()

        for group in address_book.groups:
            contacts = address_book.contacts.search_by_groups(group)

            for contact in contacts:
                c = self.getContact(contact.id, contact)
                cv = ContactView(self._core, c)
                cviews.append(cv)

            cids = [c.id for c in contacts]
            gv = GroupView(self._core, group.id, group.name, cids)
            grpviews.append(gv)
            clv.group_ids.append(group.id)

            self.getGroup(group.id, group)

        contacts = address_book.contacts.search_by_memberships(papyon.Membership.FORWARD)
        no_group_ids= []
        for contact in contacts:
            if len(contact.groups) == 0:
                c = self.getContact(contact.id, contact)
                cv = ContactView(self._core, c)
                cviews.append(cv)
                no_group_ids.append(contact.id)

        if len(no_group_ids) > 0:
            gv = GroupView(self._core, 0, "NoGroup", no_group_ids)
            grpviews.append(gv)
            clv.group_ids.append(0)
            self.getGroup(0, None, no_group_ids)

        #Emit the events
        self._em.emit(self._em.events.CLVIEW_UPDATED, clv)
        for g in grpviews:
            self._em.emit(self._em.events.GROUPVIEW_UPDATED, g)
        for c in cviews:
            self._em.emit(self._em.events.CONTACTVIEW_UPDATED, c)

    def getContact(self, uid, papyon_contact=None):
        """
        @param uid: uid of the contact
        @type uid: str
        @param papyon_contact:
        @type papyon_contact:
        @return: aMSNContact of that contact
        @rtype: aMSNContact
        """
        #TODO: should raise UnknownContact or sthg like that
        try:
            return self._contacts[uid]
        except KeyError:
            if papyon_contact is not None:
                c = aMSNContact(self._core, papyon_contact)
                self._contacts[uid] = c
                self._em.emit(self._em.events.AMSNCONTACT_UPDATED, c)
                return c
            else:
                raise ValueError

    def getGroup(self, gid, papyon_group = None, cids=[]):
        """
        @param gid: uid of the group
        @type gid: str
        @param papyon_group:
        @type papyon_group:
        @return: aMSNGroup of that group
        @rtype: aMSNGroup
        """
        try:
            return self._groups[gid]
        except KeyError:
            if papyon_group:
                contacts = self._papyon_addressbook.contacts.search_by_groups(papyon_group)
                g = aMSNGroup([c.id for c in contacts], papyon_group)
                self._groups[gid] = g
                # is AMSNGROUP_UPDATED necessary?
            elif gid == 0:
                g = aMSNGroup(cids)
                self._groups[0] = g
            else:
                raise ValueError

    def getGroups(self, uid):
        # propagate a ValueError
        return [self.getGroup(gid) for gid in self.getContact(uid).groups]


""" A few things used to describe a contact
    They are stored in that structure so that there's no need to create them
    everytime
"""
class aMSNContact():
    def __init__(self, core, papyon_contact=None):
        """
        @type core: aMSNCore
        @param papyon_contact:
        @type papyon_contact: papyon.profile.Contact
        """
        self._core = core

        self.account  = ''
        self.groups = set()
        self.dp = ImageView()
        self.icon = ImageView()
        self.emblem = ImageView()
        self.nickname = StringView()
        self.status = StringView()
        self.personal_message = StringView()
        self.current_media = StringView()
        if papyon_contact:
            if papyon_contact.msn_object is None:
                self.dp.load("Theme", "dp_nopic")
            else:
                self.dp.load("Theme", "dp_loading")
            self.fill(papyon_contact)

        else:
            self.dp.load("Theme", "dp_nopic")
            self.uid = None

    def fill(self, papyon_contact):
        """
        Fills the aMSNContact structure.

        @type papyon_contact: papyon.profile.Contact
        """

        self.uid = papyon_contact.id
        self.account = papyon_contact.account
        self.icon.load("Theme","buddy_" + self._core.p2s[papyon_contact.presence])
        self.emblem.load("Theme", "emblem_" + self._core.p2s[papyon_contact.presence])
        #TODO: PARSE ONLY ONCE
        self.nickname.reset()
        self.nickname.appendText(papyon_contact.display_name)
        self.personal_message.reset()
        self.personal_message.appendText(papyon_contact.personal_message)
        self.current_media.reset()
        self.current_media.appendText(papyon_contact.current_media)
        self.status.reset()
        self.status.appendText(self._core.p2s[papyon_contact.presence])

        #DP:
        if papyon_contact.msn_object:
            fn = self._core._backend_manager.getFileLocationDP(
                    papyon_contact.account,
                    papyon_contact.id,
                    papyon_contact.msn_object._data_sha)
            if os.path.exists(fn):
                self.dp.load("Filename", fn)
            else:
                #TODO: request?
                pass
        # ro, can be changed indirectly with addressbook's actions
        self.memberships = papyon_contact.memberships
        self.contact_type = papyon_contact.contact_type
        for g in papyon_contact.groups:
            self.groups.add(g.id)
        if len(self.groups) == 0:
            self.groups.add(0)
        # ro
        self.capabilities = papyon_contact.client_capabilities
        self.infos = papyon_contact.infos.copy()
        #for the moment, we store the papyon_contact object, but we shouldn't have to

        #TODO: getPapyonContact(self, core...) or _papyon_contact?
        self._papyon_contact = papyon_contact

class aMSNGroup():
    def __init__(self, cids, papyon_group=None):
        self.contacts = set(cids)
        if papyon_group:
            self.name = papyon_group.name
            self.id = papyon_group.id
        else:
            self.name = 'NoGroup'
            self.id = 0


########NEW FILE########
__FILENAME__ = conversation
# -*- coding: utf-8 -*-
#
# amsn - a python client for the WLM Network
#
# Copyright (C) 2008 Dario Freddi <drf54321@gmail.com>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA

from amsn2.protocol.events import conversation
from amsn2.core.contactlist_manager import *
from amsn2.core.views import *
import papyon

class aMSNConversation:
    def __init__(self, core, conv_manager, conv = None, contacts_uid = None):
        """
        @type core: aMSNCore
        @type conv_manager: aMSNConversationManager
        @type conv: papyon.conversation.SwitchboardConversation
        @type contacts_uid: list of str
        """

        if (contacts_uid is None):
            raise ValueError, InvalidArgument

        self._core = core
        self._conversation_manager = conv_manager
        self._contacts_uid = contacts_uid
        if conv is None:
            #New conversation
            papyon_contacts = [core._contactlist_manager.getContact(uid) for uid in contacts_uid]
            papyon_contacts = [c._papyon_contact for c in papyon_contacts if c is not None]
            #if c was None.... wtf?
            self._conv = papyon.Conversation(self._core._account.client, papyon_contacts)
        else:
            #From an existing conversation
            self._conv = conv

        self._win = self._conversation_manager.getConversationWindow(self)
        self._convo_events = conversation.ConversationEvents(self)
        self._convWidget = core._gui.gui.aMSNChatWidget(self, self._win, contacts_uid)
        self._win.addChatWidget(self._convWidget)
        self._win.show()


    """ events from outside """
    def onStateChanged(self, state):
        print "state changed"

    def onError(self, type, error):
        print error

    def onUserJoined(self, contact_uid):
        c = self._core._contactlist_manager.getContact(contact_uid)
        self._convWidget.onUserJoined(c.nickname)

    def onUserLeft(self, contact_uid):
        c = self._core._contactlist_manager.getContact(contact_uid)
        self._convWidget.onUserLeft(c.nickname)

    def onUserTyping(self, contact_uid):
        c = self._core._contactlist_manager.getContact(contact_uid)
        self._convWidget.onUserTyping(c.nickname)

    def onMessageReceived(self, message, sender_uid=None, formatting=None):
        #TODO: messageView
        mv = MessageView()
        if sender_uid is None:
            mv.sender.appendStringView(self._core._personalinfo_manager._personalinfoview.nick)
        else:
            c = self._core._contactlist_manager.getContact(sender_uid)
            mv.sender_icon = c.icon
            mv.message_type = MessageView.MESSAGE_OUTGOING
            mv.sender.appendStringView(c.nickname)
        mv.msg = message
        self._convWidget.onMessageReceived(mv, formatting)

    def onNudgeReceived(self, sender_uid):
        self._convWidget.nudge()

    """ Actions from ourselves """
    def sendMessage(self, msg, formatting=None):
        """ msg is a StringView """
        # for the moment, no smiley substitution... (TODO)
        self.onMessageReceived(msg, formatting=formatting)
        message = papyon.ConversationMessage(str(msg), formatting)
        self._conv.send_text_message(message)

    def sendNudge(self):
        self._conv.send_nudge()

    def sendTypingNotification(self):
        self._conv.send_typing_notification()

    def leave(self):
        self._conv.leave()

    def inviteContact(self, contact_uid):
        """ contact_uid is the Id of the contact to invite """
        c = self._core._contactlist_manager.getContact(contact_uid)
        self._conv.invite_user(contact.papyon_contact)

    #TODO: ...

########NEW FILE########
__FILENAME__ = conversation_manager
from contactlist_manager import *
from conversation import aMSNConversation

class aMSNConversationManager:
    def __init__(self, core):
        """
        @type core: aMSNCore
        """

        self._core = core
        self._convs = []
        self._wins = []

    def onInviteConversation(self, conversation):
        print "new conv"
        contacts_uid = [c.id for c in conversation.participants]
        #TODO: What if the contact_manager has not build a view for that contact?
        c = aMSNConversation(self._core, self, conversation, contacts_uid)
        self._convs.append(c)

    def newConversation(self, contacts_uid):
        """ contacts_uid is a list of contact uid """
        #TODO: check if no conversation like this one already exists
        c = aMSNConversation(self._core, self, None, contacts_uid)
        self._convs.append(c)



    def getConversationWindow(self, amsn_conversation):
        #TODO:
        #contacts should be a list of contact view
        # for the moment, always create a new win
        win = self._core._gui.gui.aMSNChatWindow(self)
        self._wins.append(win)
        return win



########NEW FILE########
__FILENAME__ = event_manager
class aMSNEvents:
    # ContactList events
    CONTACTVIEW_UPDATED = 0
    GROUPVIEW_UPDATED = 1
    CLVIEW_UPDATED = 2
    AMSNCONTACT_UPDATED = 3
    # PersonalInfo events
    PERSONALINFO_UPDATED = 4

class aMSNEventManager:
    def __init__(self, core):
        """
        @type core: aMSNCore
        """

        self._core = core
        self._events_cbs = [ [[], []] for e in dir(aMSNEvents) if e.isupper()]
        self._events_tree = [aMSNEventTree(None) for e in dir(aMSNEvents) if e.isupper()]
        self.events = aMSNEvents()

    def emit(self, event, *args):
        """ emit the event """
        # rw callback
        for cb in self._events_cbs[event][0]:
            #TODO: try except
            cb(*args)

        # ro callback
        for cb in self._events_cbs[event][1]:
            #TODO: try except
            cb(*args)

    def register(self, event, callback, type='ro', deps=[]):
        """
        Register a callback for an event:
        ro callback: doesn't need to modify the view
        rw callback: modify the view, can have dependencies which actually
                     are the names of the callbacks from which it depends
        """
        if type is 'ro':
            self._events_cbs[event][1].append(callback)

        elif type is 'rw':
            if self._events_tree[event].insert(callback, deps):
                self._events_cbs[event][0] = self._events_tree[event].getCallbacksSequence()
            else:
                print 'Failed adding callback '+callback.__name__+' to event '+event+': missing dependencies'

    def unregister(self, event, callback):
        """ unregister a callback for an event """
        if self._events_tree[event].isListed(callback):
            self._events_tree[event].remove(callback)
            self._events_cbs[event][0] = self._events_tree.getCallbacksSequence()
        else:
            self._events_cbs[event][1].remove(callback)




class aMSNEventCallback:
    def __init__(self, tree, callback_function, deps):
        self.data = callback_function
        self.id = callback_function.__name__
        self._deps = set(deps)
        self._tree = tree

    def depends(self, cb):
        for dep in self._deps:
            if cb.id == dep or (\
               cb._tree.right is not None and \
               cb._tree.right.isListed(dep)):
                return True
        return False

class aMSNEventTree:
    def __init__(self, parent):
        self.parent = parent
        self.root = None
        self.left = None
        self.right = None
        self._elements = set()

    def remove(self, callback_function):
        if self.isListed(callback_function.__name__):
            cb_obj = self._find(callback_function.__name__)

            # keep callbacks that do not depend on the one being removed
            if cb_obj._tree.parent is not None:
                if cb_obj._tree.parent.right is cb_obj._tree:
                    cb_obj._tree.parent.right = cb_obj._tree.left
                else:
                    cb_obj._tree.parent.left = cb_obj._tree.left

            else:
                # remove the root
                self.root = self.left.root
                self.right = self.left.right
                self._elements = self.left._elements
                self.left = self.left.left

        else:
            print 'Trying to remove missing callback '+callback_function.__name__

    # FIXME: what if a dependence is not yet in the tree?
    def insert(self, callback_function, deps=[]):
        cb_obj = aMSNEventCallback(self, callback_function, deps)
        if self.isListed(cb_obj.id):
            self.remove(callback_function)
            print 'Trying to add already added callback '+callback_function.__name__

        deps_satisfied = [self.isListed(dep) for dep in deps]

        # workaround if there are no dependencies
        deps_satisfied.extend([True, True])

        if reduce(lambda x, y: x and y, deps_satisfied):
            self._insert(cb_obj)
            return True
        else:
            # can't satisfy all dependencies
            return False

    def isListed(self, item):
        return item in self._elements

    def getCallbacksSequence(self):
        return self._inorder([])

    def _insert(self, cb):
        self._elements.add(cb.id)
        cb._tree = self
        if self.root is None:
            self.root = cb

        elif cb.depends(self.root):
            if self.right is None:
                self.right = aMSNEventTree(self)
            self.right._insert(cb)

        else:
            if self.left is None:
                self.left = aMSNEventTree(self)
            self.left._insert(cb)

    def _inorder(self, q):
        if self.left is not None:
            q = self.left._inorder(q)
        q.append(self.root.data)
        if self.right is not None:
            q = self.right._inorder(q)
        return q

    def _find(self, str_id):
        if self.left is not None and self.left.isListed(str_id):
            return self.left._find(str_id)
        elif self.right is not None and self.right.isListed(str_id):
            return self.right._find(str_id)
        elif self.root.id == str_id:
            return self.root
        else:
            return None



########NEW FILE########
__FILENAME__ = lang

from os import path
import re

class aMSNLang(object):
    lang_keys = {}
    lang_dirs = []
    base_lang = 'en'
    lang_code = base_lang

    default_encoding = 'utf-8'

    lineRe  = re.compile('\s*([^\s]+)\s+(.+)', re.UNICODE)  # whitespace? + key + whitespace + value
    langRe  = re.compile('(.+)-.+', re.UNICODE)             # code or code-variant

    def loadLang(self, lang_code, force_reload=False):
        if self.lang_code is lang_code and force_reload is False:
            # Don't reload the same lang unless forced.
            return

        hasVariant = (self.langRe.match(lang_code) is not None)

        # Check for lang variants.
        if hasVariant:
            root = str(self.langRe.split(lang_code)[1])
        else:
            root = lang_code

        if lang_code is self.base_lang:
            # Clear the keys if we're loading the base lang.
            self.clearKeys()

        if root is not self.base_lang:
            # If it's not the default lang, load the base first.
            self.loadLang(self.base_lang)

        if hasVariant:
            # Then we have a variant, so load the root.
            self.loadLang(root)

        # Load the langfile from each langdir.
        fileWasLoaded = False
        for dir in self.getLangDirs():
            try:
                f = file(path.join(dir, 'lang' + lang_code), 'r')
                fileWasLoaded = True
            except IOError:
                # file doesn't exist.
                continue

            line = f.readline()
            while line:
                if self.lineRe.match(line) is not None:
                    components = self.lineRe.split(line)
                    self.setKey(unicode(components[1], self.default_encoding), unicode(components[2], self.default_encoding))

                # Get the next line...
                line = f.readline()

            f.close()

        # If we've loaded a lang file, set the new lang code.
        if fileWasLoaded:
            self.lang_code = lang_code

    def addLangDir(self, lang_dir):
        self.lang_dirs.append(str(lang_dir))
        self.reloadKeys()

    def removeLangDir(self, lang_dir):
        try:
            # Remove the lang_dir from the lang_dirs list, and reload keys.
            self.lang_dirs.remove(str(lang_dir))
            self.reloadKeys()
            return True
        except ValueError:
            # Dir not in list.
            return False

    def getLangDirs(self):
        # Return a copy for them to play with.
        return self.lang_dirs[:]

    def clearLangDirs(self):
        self.lang_dirs = []
        self.clearKeys()

    def reloadKeys(self):
        self.loadLang(self.lang_code, True)

    def setKey(self, key, val):
        self.lang_keys[key] = val

    def getKey(self, key, replacements=[]):
        try:
            r = self.lang_keys[key]
        except KeyError:
            # Key doesn't exist.
            return key

        # Perform any replacements necessary.
        if type(replacements) is dict:
            # Replace from a dictionary.
            for key, val in replacements.iteritems():
                r = r.replace(key, val)
        else:
            # Replace each occurence of $i with an item from the replacements list.
            i = 1
            for replacement in replacements:
                r = r.replace('$' + str(i), replacement)
                i += 1

        return r

    def clearKeys(self):
        self.lang_keys = {}

    def printKeys(self):
        print self.lang_code
        print '{'
        for key, val in self.lang_keys.iteritems():
            print "\t[" + key + '] =>' + "\t" + '\'' + val + '\''
        print '}'

lang = aMSNLang()

########NEW FILE########
__FILENAME__ = oim_manager
# -*- coding: utf-8 -*-
#
# amsn - a python client for the WLM Network
#
# Copyright (C) 2008 Dario Freddi <drf54321@gmail.com>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA

class aMSNOIMManager:
    def __init__(self, core):
        """
        @type core: aMSNCore
        """

        self._core = core


########NEW FILE########
__FILENAME__ = personalinfo_manager
from views import *

class aMSNPersonalInfoManager:
    def __init__(self, core):
        """
        @type core: aMSNCore
        """

        self._core = core
        self._backend_manager = core._backend_manager
        self._em = core._event_manager
        self._personalinfoview = PersonalInfoView(self)
        self._papyon_profile = None

    def setAccount(self, amsn_account):
        self._papyon_profile = amsn_account.client.profile

        # set nickname at login
        # could be overriden by the one set in the saved account
        # TODO: add setting display picture
        strv = StringView()
        nick = str(amsn_account.view.nick)
        if nick and nick != amsn_account.view.email:
            strv.appendText(nick)
        else:
            strv.appendText(self._papyon_profile.display_name)
        self._personalinfoview.nick = strv

        # TODO: The psm doesn't seem to get fetched from server. Papyon issue?
        strv = StringView()
        psm = str(amsn_account.view.psm)
        if psm:
            strv.appendText(psm)
        self._personalinfoview.psm = strv

        # set login presence, from this moment the client appears to the others
        self._personalinfoview.presence = self._core.p2s[amsn_account.view.presence]

    """ Actions from ourselves """
    def _onNickChanged(self, new_nick):
        # TODO: parsing
        self._papyon_profile.display_name = str(new_nick)

    def _onPSMChanged(self, new_psm):
        # TODO: parsing
        self._papyon_profile.personal_message = str(new_psm)

    def _onPresenceChanged(self, new_presence):
        # TODO: manage custom presence
        for key in self._core.p2s:
            if self._core.p2s[key] == new_presence:
                break
        self._papyon_profile.presence = key

    def _onDPChanged(self, dp_msnobj):
        self._papyon_profile.msn_object = dp_msnobj

    """ Actions from the core """
    def _onCMChanged(self, new_media):
        self._papyon_profile.current_media = new_media

    """ Notifications from the server """
    def onNickUpdated(self, nick):
        # TODO: parse fields for smileys, format, etc
        self._personalinfoview._nickname.reset()
        self._personalinfoview._nickname.appendText(nick)
        self._em.emit(self._em.events.PERSONALINFO_UPDATED, self._personalinfoview)

    def onPSMUpdated(self, psm):
        # TODO: parse fields for smileys, format, etc
        self._personalinfoview._psm.reset()
        self._personalinfoview._psm.appendText(psm)
        self._em.emit(self._em.events.PERSONALINFO_UPDATED, self._personalinfoview)

    def onDPUpdated(self, dp_msnobj):
        self._personalinfoview._image.reset()
        path = self._backend_manager.getFileLocationDP(self._papyon_profile.account,
                                                       self._papyon_profile.id,
                                                       dp_msnobj._data_sha)
        self._personalinfoview._image.load('Filename', path)
        self._em.emit(self._em.events.PERSONALINFO_UPDATED, self._personalinfoview)

    def onPresenceUpdated(self, presence):
        self._personalinfoview._presence = self._core.p2s[presence]
        self._em.emit(self._em.events.PERSONALINFO_UPDATED, self._personalinfoview)

    def onCMUpdated(self, cm):
        self._personalinfoview._current_media.reset()
        #TODO: insert separators
        self._personalinfoview._current_media.apprndText(cm[0])
        self._personalinfoview._current_media.apprndText(cm[1])
        self._em.emit(self._em.events.PERSONALINFO_UPDATED, self._personalinfoview)

    # TODO: connect to papyon event, maybe build a mailbox_manager
    """ Actions from outside """
    def _onNewMail(self, info):
        self._em.emit(self._em.events.PERSONALINFO_UPDATED, self._personalinfoview)







########NEW FILE########
__FILENAME__ = theme_manager
# -*- coding: utf-8 -*-
#===================================================
#
# theme_manager.py - This file is part of the amsn2 package
#
# Copyright (C) 2008  Wil Alvarez <wil_alejandro@yahoo.com>
#
# This script is free software; you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free Software 
# Foundation; either version 3 of the License, or (at your option) any later
# version.
#
# This script is distributed in the hope that it will be useful, but WITHOUT 
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or 
# FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public License 
# for more details.
#
# You should have received a copy of the GNU General Public License along with 
# this script (see COPYING); if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
#
#===================================================

import os

class aMSNThemeManager:
    def __init__(self, core):
        self._core = core
        self._buttons = {}
        self._statusicons = {}
        self._displaypic = {}
        self._emblems = {}

        self.load()

    def __get(self, var, key):
        # TODO: evaluate if should be returned None when key is not valid
        if key in var.keys():
            return var[key]
        else:
            return (None, None)

    def load(self):
        # Here aMSNThemeManager should read user's files to know what theme
        # will be loaded to each aspect
        self._buttons = aMSNButtonLoader().load('default')
        self._statusicons = aMSNStatusIconLoader().load('default')
        self._displaypic = aMSNDisplayPicLoader().load('default')
        self._emblems = aMSNEmblemLoader().load('default')

    def get_value(self, key):
        if (key.startswith('button_')):
            return self.get_button(key)
        elif (key.startswith('buddy_')):
            return self.get_statusicon(key)
        elif (key.startswith('dp_')):
            return self.get_dp(key)
        elif (key.startswith('emblem_')):
            return self.get_emblem(key)
        else:
            # TODO: This should raise a exception
            return (None, None)

    def get_button(self, key):
        return self.__get(self._buttons, key)

    def get_statusicon(self, key):
        return self.__get(self._statusicons, key)

    def get_dp(self, key):
        return self.__get(self._displaypic, key)

    def get_emblem(self, key):
        return self.__get(self._emblems, key)

class aMSNGenericLoader:
    def __init__(self, basedir):
        self._theme = 'default'
        self._basedir = os.path.join("amsn2", "themes", basedir)
        self._defaultdir = os.path.join(self._basedir, "default")
        # Keys holds a pair (key,filename)
        # Should be initialized after creating the class
        self._keys = []
        self._dict = {}

    def load(self, theme='default'):
        self.theme = theme
        self._theme_dir = os.path.join(self._basedir, theme)

        for key in self._keys.keys():
            image = self._keys[key]
            filepath = os.path.join(self._theme_dir, image)

            # Verificating
            if (not os.path.isfile(filepath)):
                filepath = os.path.join(self._defaultdir, image)

            self._dict[key] = ("Filename", filepath)

        return self._dict

class aMSNButtonLoader(aMSNGenericLoader):
    def __init__(self):
        aMSNGenericLoader.__init__(self, "buttons")
        self._keys = {
            'button_nudge': 'nudge.png',
            'button_smile': 'smile.png',
        }

class aMSNStatusIconLoader(aMSNGenericLoader):
    def __init__(self):
        aMSNGenericLoader.__init__(self, "status_icons")
        self._keys = {
            'buddy_online': 'online.png',
            'buddy_away': 'away.png',
            'buddy_brb': 'away.png',
            'buddy_idle': 'away.png',
            'buddy_lunch': 'away.png',
            'buddy_busy': 'busy.png',
            'buddy_phone': 'phone.png',
            'buddy_offline': 'offline.png',
            'buddy_hidden': 'offline.png',
            'buddy_blocked': 'blocked.png',
            'buddy_blocked_off': 'blocked_off.png',
            'buddy_webmsn': 'webmsn.png',
        }

class aMSNDisplayPicLoader(aMSNGenericLoader):
    def __init__(self):
        aMSNGenericLoader.__init__(self, "displaypic")
        self._keys = {
            'dp_amsn': 'amsn.png', 
            'dp_female': 'female.png',
            'dp_loading': 'loading.png',
            'dp_male': 'male.png',
            'dp_nopic': 'nopic.png',
        }

class aMSNEmblemLoader(aMSNGenericLoader):
    def __init__(self):
        aMSNGenericLoader.__init__(self, "emblems")
        self._keys = {
            'emblem_online': 'plain_emblem.png',
            'emblem_away': 'away_emblem.png',
            'emblem_brb': 'away_emblem.png',
            'emblem_idle': 'away_emblem.png',
            'emblem_lunch': 'away_emblem.png',
            'emblem_busy': 'busy_emblem.png',
            'emblem_phone': 'busy_emblem.png',
            'emblem_offline': 'offline_emblem.png',
            'emblem_hidden': 'offline_emblem.png',
            'emblem_blocked': 'blocked_emblem.png',
        }

########NEW FILE########
__FILENAME__ = accountview

from imageview import *
from stringview import *

class AccountView:
    def __init__(self, core, email):
        self._core = core
        self.email = email
        self.password = None
        self.nick = StringView()
        self.psm = StringView()
        self.presence = core.Presence.ONLINE
        self.dp = ImageView()

        self.save = False
        self.save_password = False
        self.autologin = False

        self.preferred_ui = None
        self.preferred_backend = 'defaultbackend'

    def __str__(self):
        out = "{ email=" + str(self.email)
        out += " presence=" + self._core.p2s[self.presence]
        out += " save=" + str(self.save) + " save_password=" + str(self.save_password)
        out += " autologin=" + str(self.autologin) + " preferred_ui=" + str(self.preferred_ui)
        out += " preferred_backend=" + self.preferred_backend + " }"
        return out

########NEW FILE########
__FILENAME__ = contactlistview
from stringview import *
from imageview import *
from menuview import *

class ContactListView:
    def __init__(self):
        self.group_ids = []



class GroupView:
    def __init__(self, core, uid, name, contact_ids=[], active=0):
        self.uid = uid
        self.contact_ids = set(contact_ids)
        self.icon = ImageView() # TODO: expanded/collapsed icon
        self.name = StringView() # TODO: default color from skin/settings
        self.name.appendText(name) #TODO: parse for smileys
        active = 0 #TODO
        total = len(self.contact_ids)
        self.name.appendText("(" + str(active) + "/" + str(total) + ")")

        self.on_click = None #TODO: collapse, expand
        self.on_double_click = None
        self.on_right_click_popup_menu = GroupPopupMenu(core)
        self.tooltip = None
        self.context_menu = None


    #TODO: @roproperty: context_menu, tooltip



""" a view of a contact on the contact list """
class ContactView:
    def __init__(self, core, amsn_contact):
        """
        @type core: aMSNCore
        @type amsn_contact: aMSNContact
        """

        self.uid = amsn_contact.uid

        self.icon = amsn_contact.icon
        #TODO: apply emblem on dp
        self.dp = amsn_contact.dp.clone()
        self.dp.appendImageView(amsn_contact.emblem)
        self.name = StringView() # TODO : default colors
        self.name.openTag("nickname")
        self.name.appendStringView(amsn_contact.nickname) # TODO parse
        self.name.closeTag("nickname")
        self.name.appendText(" ")
        self.name.openTag("status")
        self.name.appendText("(")
        self.name.appendStringView(amsn_contact.status)
        self.name.appendText(")")
        self.name.closeTag("status")
        self.name.appendText(" ")
        self.name.openTag("psm")
        self.name.setItalic()
        self.name.appendStringView(amsn_contact.personal_message)
        self.name.unsetItalic()
        self.name.closeTag("psm")
        #TODO:
        def startConversation_cb(c_uid):
            core._conversation_manager.newConversation([c_uid])
        self.on_click = startConversation_cb
        self.on_double_click = None
        self.on_right_click_popup_menu = ContactPopupMenu(core, amsn_contact)
        self.tooltip = None
        self.context_menu = None

    #TODO: @roproperty: context_menu, tooltip

class ContactPopupMenu(MenuView):
    def __init__(self, core, amsncontact):
        MenuView.__init__(self)
        remove = MenuItemView(MenuItemView.COMMAND,
                              label="Remove %s" % amsncontact.account,
                              command= lambda: core._contactlist_manager.removeContact(amsncontact.uid))
        self.addItem(remove)

class GroupPopupMenu(MenuView):
    def __init__(self, core):
        MenuView.__init__(self)


########NEW FILE########
__FILENAME__ = imageview
class ImageView(object):
    """
        Known resource_type are:
            - Filename
            - Theme
            - None
    """

    FILENAME = "Filename"
    THEME = "Theme"

    def __init__(self, resource_type=None, value=None):
        self.imgs = []
        if resource_type is not None and value is not None:
            self.load(resource_type, value)

    def load(self, resource_type, value):
        self.imgs = [(resource_type, value)]

    def append(self, resource_type, value):
        self.imgs.append((resource_type, value))

    def prepend(self, resource_type, value):
        self.imgs.insert(0, (resource_type, value))

    def clone(self):
        img = ImageView()
        img.imgs = self.imgs[:]
        return img

    def appendImageView(self, iv):
        self.imgs.extend(iv.imgs)

    def prependImageView(self, iv):
        self.imgs = iv.imgs[:].extend(self.imgs)

    def reset(self):
        self.imgs = []


########NEW FILE########
__FILENAME__ = keybindingview

class KeyBindingView(object):
    BACKSPACE = "Backspace"
    TAB = "Tab"
    ENTER = "Enter"
    ESCAPE = "Escape"
    HOME = "Home"
    END = "End"
    LEFT = "Left"
    RIGHT = "Right"
    UP = "Up"
    DOWN = "Down"
    PAGEUP = "PageUp"
    PAGEDOWN = "PageDown"
    INSERT = "Insert"
    DELETE = "Delete"

    def __init__(self, key = None, control = False, alt = False, shift = False):
        self.key = key
        self.control = control
        self.alt = alt
        self.shift = shift

    def __repr__(self):
        out = ""
        if self.control:
            out += "Ctrl-"
        if self.alt:
            out += "Alt-"
        if self.shift:
            out += "Shift-"
        out += self.key

        return out


########NEW FILE########
__FILENAME__ = menuview

class MenuItemView(object):
    CASCADE_MENU = "cascade"
    CHECKBUTTON = "checkbutton"
    RADIOBUTTON = "radiobutton"
    RADIOBUTTONGROUP = "radiobuttongroup"
    SEPARATOR = "separator"
    COMMAND = "command"

    def __init__(self, type, label = None, icon = None, accelerator = None,
                 radio_value = None, checkbox_value = False, disabled = False,  command = None):
        """ Create a new MenuItemView
        @param type: the type of item, can be cascade, checkbutton, radiobutton,
        radiogroup, separator or command
        @param label: the label for the item, unused for separator items
        @param icon: an optional icon to show next to the menu item, unused for separator items
        @param accelerator: the accelerator (KeyBindingView) to access this item.
                       If None, an '&' preceding a character of the menu label will set that key with Ctrl- as an accelerator
        @param radio_value: the value to set when the radiobutton is enabled
        @type checkbox_value: bool
        @param checkbox_value: whether the checkbox/radiobutton is set or not
        @type disabled: bool
        @param disabled: true if the item's state should be disabled
        @param command: the command to call for setting the value for checkbutton and radiobutton items, or the command in case of a 'command' item

        @todo: dynamic menus (use 'command' in CASCADE_MENU)
        """

        if ((type is MenuItemView.SEPARATOR and
             (label is not None or
              icon is not None or
              accelerator is not None or
              radio_value is not None or
              checkbox_value is not False or
              disabled is True or
              command is not None)) or
            (type is MenuItemView.CHECKBUTTON and
              command is None) or
            (type is MenuItemView.RADIOBUTTON and
              command is None) or
            (type is MenuItemView.RADIOBUTTONGROUP and 
             (command is not None or
              checkbox_value is not False or
              label is not None)) or
            (type is MenuItemView.COMMAND and
             (radio_value is not None or
              checkbox_value is not False or
              command is None )) or
            (type is MenuItemView.CASCADE_MENU and
             (radio_value is not None or
              checkbox_value is not False or
              icon is not None or
              command is not None))):
            raise ValueError

        new_label = label
        if accelerator is None and label is not None:
            done = False
            idx = 0
            new_label = ""
            while not done:
                part = label.partition('&')
                new_label += part[0]
                if part[1] == '&':
                    if part[2].startswith('&'):
                        new_label += '&'
                        label = part[2][1:]
                    elif len(part[2]) > 0:
                        if accelerator is None:
                            accelerator = KeyBindingView(key = part[2][0], control = True)
                        label = part[2]
                    else:
                        done = True
                else:
                    done = True


        self.type = type
        self.label = new_label
        self.icon = icon
        self.accelerator = accelerator
        self.radio_value = radio_value
        self.disabled = disabled
        self.command = command
        self.items = []

    def addItem(self, item):
        self.items.append(item)


class MenuView(object):

    def __init__(self):
        self.items = []

    def addItem(self, item):
        self.items.append(item)


########NEW FILE########
__FILENAME__ = messageview
from stringview import *

class MessageView:
    MESSAGE_INCOMING = 0
    MESSAGE_OUTGOING = 1
    def __init__(self):
        self.msg = StringView()
        self.sender = StringView()
        self.sender_icon = None
        self.message_type = MessageView.MESSAGE_INCOMING


    #TODO: toMessageStyle or sthg like that

    def toStringView(self):
        strv = StringView()
        strv.appendStringView(self.sender)
        strv.appendText(" says:\n")
        strv.appendStringView(self.msg)
        strv.appendText("\n")

        return strv


########NEW FILE########
__FILENAME__ = personalinfoview
from stringview import *
from imageview import *

def rw_property(f):
    return property(**f())

class PersonalInfoView(object):
    def __init__(self, personalinfo_manager):
        self._personalinfo_manager = personalinfo_manager

        self._nickname = StringView()
        self._psm = StringView()
        self._current_media  = StringView()
        self._image = ImageView()
        self._presence = 'offline'

        # TODO: get more info, how to manage webcams and mail
        self._webcam = None
        self._mail_unread = None

    def onDPChangeRequest(self):
        self._personalinfo_manager._onDPChangeRequest()

    @rw_property
    def nick():
        def fget(self):
            return self._nickname
        def fset(self, nick):
            self._personalinfo_manager._onNickChanged(nick)
        return locals()

    @rw_property
    def psm():
        def fget(self):
            return self._psm
        def fset(self, psm):
            self._personalinfo_manager._onPSMChanged(psm)
        return locals()

    @rw_property
    def dp():
        def fget(self):
            return self._image
        def fset(self, dp_msnobj):
            self._personalinfo_manager._onDPChanged(dp_msnobj)
        return locals()

    @rw_property
    def current_media():
        def fget(self):
            return self._current_media
        def fset(self, artist, song):
            self._personalinfo_manager._onCMChanged((artist, song))
        return locals()

    @rw_property
    def presence():
        def fget(self):
            return self._presence
        def fset(self, presence):
            self._personalinfo_manager._onPresenceChanged(presence)
        return locals()


########NEW FILE########
__FILENAME__ = stringview
# -*- coding: utf-8 -*-
#
# amsn - a python client for the WLM Network
#
# Copyright (C) 2008 Dario Freddi <drf54321@gmail.com>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA


class StringView (object):
    TEXT_ELEMENT = "text"
    COLOR_ELEMENT = "color"
    BACKGROUND_ELEMENT = "bgcolor"
    IMAGE_ELEMENT = "image"
    OPEN_TAG_ELEMENT = "tag"
    CLOSE_TAG_ELEMENT = "-tag"
    ITALIC_ELEMENT = "italic"
    BOLD_ELEMENT = "bold"
    UNDERLINE_ELEMENT = "underline"
    FONT_ELEMENT = "font"

    # padding ? 

    class StringElement(object):
        def __init__(self, type, value):
            self._type = type
            self._value = value

        def getType(self):
            return self._type

        def getValue(self):
            return self._value

    class ColorElement(StringElement):
        def __init__(self, color):
            StringView.StringElement.__init__(self, StringView.COLOR_ELEMENT, color)
    class BackgroundColorElement(StringElement):
        def __init__(self, color):
            StringView.StringElement.__init__(self, StringView.BACKGROUND_ELEMENT, color)
    class TextElement(StringElement):
        def __init__(self, text):
            StringView.StringElement.__init__(self, StringView.TEXT_ELEMENT, text)
    class ImageElement(StringElement):
        def __init__(self, image):
            StringView.StringElement.__init__(self, StringView.IMAGE_ELEMENT, image)
    class OpenTagElement(StringElement):
        def __init__(self, tag):
            StringView.StringElement.__init__(self, StringView.OPEN_TAG_ELEMENT, tag)
    class CloseTagElement(StringElement):
        def __init__(self, tag):
            StringView.StringElement.__init__(self, StringView.CLOSE_TAG_ELEMENT, tag)
    class FontElement(StringElement):
        def __init__(self, font):
            StringView.StringElement.__init__(self, StringView.FONT_ELEMENT, font)
    class BoldElement(StringElement):
        def __init__(self, bold):
            StringView.StringElement.__init__(self, StringView.BOLD_ELEMENT, bold)
    class ItalicElement(StringElement):
        def __init__(self, italic):
            StringView.StringElement.__init__(self, StringView.ITALIC_ELEMENT, italic)
    class UnderlineElement(StringElement):
        def __init__(self, underline):
            StringView.StringElement.__init__(self, StringView.UNDERLINE_ELEMENT, underline)

    def __init__(self, default_background_color = None, default_color = None, default_font = None):
        self._elements = []

        self._default_background_color = default_background_color
        self._default_color = default_color
        self._default_font = default_font

        if default_color is not None:
            self.resetColor()
        if default_background_color is not None:
            self.resetBackgroundColor()
        if default_font is not None:
            self.resetFont()

    def append(self, type, value):
        self._elements.append(StringView.StringElement(type, value))

    def appendStringView(self, strv):
        #TODO: default (bg)color
        self._elements.extend(strv._elements)
    def appendText(self, text):
        self._elements.append(StringView.TextElement(text))
    def appendImage(self, image):
        self._elements.append(StringView.ImageElement(image))
    def setColor(self, color):
        self._elements.append(StringView.ColorElement(color))
    def setBackgroundColor(self, color):
        self._elements.append(StringView.BackgroundColorElement(color))
    def setFont(self, font):
        self._elements.append(StringView.FontElement(font))
    def openTag(self, tag):
        self._elements.append(StringView.OpenTagElement(tag))
    def closeTag(self, tag):
        self._elements.append(StringView.CloseTagElement(tag))

    def setBold(self):
        self._elements.append(StringView.BoldElement(True))
    def unsetBold(self):
        self._elements.append(StringView.BoldElement(False))
    def setItalic(self):
        self._elements.append(StringView.ItalicElement(True))
    def unsetItalic(self):
        self._elements.append(StringView.ItalicElement(False))
    def setUnderline(self):
        self._elements.append(StringView.UnderlineElement(True))
    def unsetUnderline(self):
        self._elements.append(StringView.UnderlineElement(False))

    def reset(self):
        self._elements = []
    def resetColor(self):
        self.setColor(self._default_color)
    def resetBackgroundColor(self):
        self.setBackgroundColor(self._default_background_color)
    def resetFont(self):
        self.setFont(self._default_font)


    def appendElementsFromHtml(self, string):
        """ This method should parse an HTML string and convert it to a
        StringView. It will be extremely comfortable, since most of the
        times our frontends will work with HTML stuff. """
        # TODO: Not so easy... maybe there is a python HTML parser we can use?
        pass

    def toHtmlString(self):
        """ This method returns a formatted html string with all
        the data in the stringview """
        out = ""
        for x in self._elements:
            if x.getType() == StringView.TEXT_ELEMENT:
                print "Plain text found"
                out += x.getValue()
            elif x.getType() == StringView.ITALIC_ELEMENT:
                print "Italic text found"
                if x.getValue() == True:
                    out += "<i>"
                else:
                    out += "</i>"
            elif x.getType() == StringView.BOLD_ELEMENT:
                print "Bold text found"
                if x.getValue() == True:
                    out += "<b>"
                else:
                    out += "</b>"
            elif x.getType() == StringView.IMAGE_ELEMENT:
                print "Image found"
                out += "<img src=\""+x.getValue()+"\" />"
            elif x.getType() == StringView.UNDERLINE_ELEMENT:
                if x.getValue() == True:
                    out += "<u>"
                else:
                    out += "</u>"

        print out
        return out

    def getTag(self, tagname):

        for i in range(len(self._elements)):
            e = self._elements[i]
            if e.getType() == StringView.OPEN_TAG_ELEMENT and e.getValue() == tagname:
                begin = i+1
                break

        sv = StringView()

        #if begin is None, raise exception?
        if begin is not None:
            e = self._elements[begin]

            while not (e.getType() == StringView.CLOSE_TAG_ELEMENT and e.getValue() == tagname):
                sv.append(e.getType(), e.getValue())
                begin += 1
                e = self._elements[begin]

        return sv

    def __str__(self):
        out = ""
        for x in self._elements:
            if x.getType() == StringView.TEXT_ELEMENT:
                out += x.getValue()
        return out

    def __repr__(self):
        out = "{"
        for x in self._elements:
            out += "[" + x.getType() + "=" + str(x.getValue()) + "]"

        out += "}"
        return out


########NEW FILE########
__FILENAME__ = tooltipview

class TooltipView (object):
    def __init__(self):
        self.name = None
        self.icon = None


########NEW FILE########
__FILENAME__ = chat_window

class aMSNChatWindow(object):
    """ This interface will represent a chat window of the UI
        It can have many aMSNChatWidgets"""
    def __init__(self, amsn_core):
        raise NotImplementedError

    def addChatWidget(self, chat_widget):
        """ add an aMSNChatWidget to the window """
        raise NotImplementedError

    """TODO: move, remove, detach, attach (shouldn't we use add ?), close,
        flash..."""


class aMSNChatWidget(object):
    """ This interface will present a chat widget of the UI """
    def __init__(self, amsn_conversation, parent, contacts_uid):
        """ create the chat widget for the 'parent' window, but don't attach to
        it."""
        raise NotImplementedError

    def onMessageReceived(self, messageview):
        """ Called for incoming and outgoing messages
            message: a MessageView of the message"""
        raise NotImplementedError

    def nudge(self):
        raise NotImplementedError


########NEW FILE########
__FILENAME__ = choosers

class aMSNFileChooserWindow(object):
    """
    This Interface represent a window used to choose a file,
    which could be an image for the dp, a file to send, a theme file, etc.
    """
    def __init__(self, filters, directory, callback):
        """
        @type filter: dict of tuple
        @param filter: A dict whose keys are the names of the filters,
        and the values are a tuple containing strings,
        that will represent the patterns to filter.
        @type directory: str
        @param directory: The path to start from.
        @type callback: function
        @param callback: The function called when the file has been choosed.
        Its prototype is callback(file_path)

        This will eventually call the related show() method, so the window is
        displayed when created.
        """
        raise NotImplementedError

class aMSNDPChooserWindow(object):
    """
    This Interface represent a window used to choose a display picture,
    should show a list of default dps and the possibility to catch a picture from a webcam.
    """
    def __init__(self, callback, backend_manager):
        """
        @type callback: function
        @param callback: The function called when the dp has been choosed.
        Its prototype is callback(dp_path)
        @type backend_manager: aMSNBackendManager

        This will eventually call the related show() method, so the window is
        displayed when created.
        """
        raise NotImplementedError


########NEW FILE########
__FILENAME__ = contact_list
"""TODO:
    * Let the aMSNContactListWidget be selectable to choose contacts to add to a
    conversation... each contact should have a checkbox on front of it
    * Drag contacts through groups
    * Drag groups
    ...
"""


class aMSNContactListWindow(object):
    """ This interface represents the main Contact List Window
        self._clwiget is an aMSNContactListWidget 
    """

    def __init__(self, amsn_core, parent):
        em = amsn_core._event_manager
        em.register(em.events.PERSONALINFO_UPDATED, self.myInfoUpdated)

    def show(self):
        """ Show the contact list window """
        raise NotImplementedError

    def hide(self):
        """ Hide the contact list window """
        raise NotImplementedError

    def setTitle(self, text):
        """ This will allow the core to change the current window's title
        @type text: str
        """
        raise NotImplementedError

    def setMenu(self, menu):
        """ This will allow the core to change the current window's main menu
        @type menu: MenuView
        """
        raise NotImplementedError

    def myInfoUpdated(self, view):
        """ This will allow the core to change pieces of information about
        ourself, such as DP, nick, psm, the current media being played,...
        @type view: PersonalInfoView
        @param view: the PersonalInfoView of the ourself (contains DP, nick, psm,
        currentMedia,...)"""
        raise NotImplementedError

class aMSNContactListWidget(object):
    """ This interface implements the contact list of the UI """
    def __init__(self, amsn_core, parent):
        em = amsn_core._event_manager
        em.register(em.events.CLVIEW_UPDATED, self.contactListUpdated)
        em.register(em.events.GROUPVIEW_UPDATED, self.groupUpdated)
        em.register(em.events.CONTACTVIEW_UPDATED, self.contactUpdated)

    def show(self):
        """ Show the contact list widget """
        raise NotImplementedError

    def hide(self):
        """ Hide the contact list widget """
        raise NotImplementedError

    def contactListUpdated(self, clView):
        """ This method will be called when the core wants to notify
        the contact list of the groups that it contains, and where they
        should be drawn a group should be drawn.
        It will be called initially to feed the contact list with the groups
        that the CL should contain.
        It will also be called to remove any group that needs to be removed.

        @type clView: ContactListView
        @param clView : contains the list of groups contained in
        the contact list which will contain the list of ContactViews
        for all the contacts to show in the group."""
        raise NotImplementedError

    def groupUpdated(self, groupView):
        """ This method will be called to notify the contact list
        that a group has been updated.
        The contact list should update its icon and name
        but also its content (the ContactViews). The order of the contacts
        may be changed, in which case the UI should update itself accordingly.
        A contact can also be added or removed from a group using this method
        """
        raise NotImplementedError

    def contactUpdated(self, contactView):
        """ This method will be called to notify the contact list
        that a contact has been updated.
        The contact can be in any group drawn and his icon,
        name or DP should be updated accordingly.
        The position of the contact will not be changed by a call
        to this function. If the position was changed, a groupUpdated
        call will be made with the new order of the contacts
        in the affects groups.
        """
        raise NotImplementedError


########NEW FILE########
__FILENAME__ = login

class aMSNLoginWindow(object):
    """ This interface will represent the login window of the UI"""
    def __init__(self, amsn_core, parent):
        """Initialize the interface. You should store the reference to the core in here """
        raise NotImplementedError

    def show(self):
        """ Draw the login window """
        raise NotImplementedError

    def hide(self):
        """ Hide the login window """
        raise NotImplementedError

    def setAccounts(self, accountviews):
        """ This method will be called when the core needs the login window to
        let the user select among some accounts.

        @param accountviews: list of accountviews describing accounts
        The first one in the list
        should be considered as default. """
        raise NotImplementedError

    def signin(self):
        """ This method will be called when the core needs the login window to start the signin process """
        raise NotImplementedError

    def onConnecting(self, progress, message):
        """ This method will be called to notify the UI that we are connecting.

        @type progress: float
        @param progress: the current progress of the connexion (to be
        exploited as a progress bar, for example)
        @param message: the message to show while loging in """
        raise NotImplementedError

    def getAccountViewFromEmail(self, email):
        """
        Search in the list self._account_views and return the view of the given email

        @type email: str
        @param email: email to find
        @rtype: AccountView
        @return: Returns AccountView if it was found, otherwise return None
        """

        accv = [accv for accv in self._account_views if accv.email == email]

        if len(accv) == 0:
            return None
        else:
            return accv[0]


########NEW FILE########
__FILENAME__ = main

class aMSNMainWindow(object):
    """ This Interface represents the main window of the application. Everything will be done from here 
    When the window is shown, it should call: amsn_core.mainWindowShown()
    When the user wants to close that window, amsn_core.quit() should be called.
    """

    def __init__(self, amsn_core):
        """
        @type amsn_core: aMSNCore
        """

        pass

    def show(self):
        raise NotImplementedError

    def hide(self):
        raise NotImplementedError

    def setTitle(self,title):
        raise NotImplementedError

    def setMenu(self,menu):
        raise NotImplementedError

########NEW FILE########
__FILENAME__ = main_loop

class aMSNMainLoop(object):
    """ This Interface represents the main loop abstraction of the application.
    Everythin related to the main loop will be delegates here """
    def __init__(self, amsn_core):
        """
        @type amsn_core: aMSNCore
        """

        raise NotImplementedError

    def run(self):
        """ This will run the the main loop"""
        raise NotImplementedError

    def idlerAdd(self, func):
        """
        This will add an idler function into the main loop's idler

        @type func: function
        """
        raise NotImplementedError

    def timerAdd(self, delay, func):
        """
        This will add a timer into the main loop which will call a function

        @type delay:
        @type func: function
        """
        raise NotImplementedError

    def quit(self):
        """ This will be called when the core wants to exit """
        raise NotImplementedError


########NEW FILE########
__FILENAME__ = skins
import os.path

class Skin(object):
    def __init__(self, core, path):
        """
        @type core: aMSNCore
        @type path:
        """

        self._path = path
        pass

    def getKey(self, key, default):
        pass

    def setKey(self, key, value):
        pass



class SkinManager(object):
    def __init__(self, core):
        """
        @type core: aMSNCore
        """
        self._core = core
        self.skin = Skin(core, "skins")

    def setSkin(self, name):
        self.skin = Skin(self._core, os.path.join("skins", name))

    def listSkins(self, path):
        pass

########NEW FILE########
__FILENAME__ = splash

class aMSNSplashScreen(object):
    """ This interface will represent the splashscreen of the UI"""
    def __init__(self, amsn_core, parent):
        """Initialize the interface. You should store the reference to the core in here
        as well as a reference to the window where you will show the splash screen
        """
        raise NotImplementedError

    def show(self):
        """ Draw the splashscreen """
        raise NotImplementedError

    def hide(self):
        """ Hide the splashscreen """
        raise NotImplementedError

    def setText(self, text):
        """ Shows a different text inside the splashscreen """
        raise NotImplementedError

    def setImage(self, image):
        """ Set the image to show in the splashscreen. This is an ImageView object """

        raise NotImplementedError




########NEW FILE########
__FILENAME__ = utility

class aMSNErrorWindow(object):
    """ This Interface represent an error window """
    def __init__(self, error_text):
        """
        @type error_text: str

        This will eventually call the related show() method, so the window is
        displayed when created.
        """
        raise NotImplementedError

class aMSNNotificationWindow(object):
    """
    This Interface represent a window used to display a notification message,
    generally when an operation has finished succesfully.
    """
    def __init__(self, notification_text):
        """
        @type notification_text: str

        This will eventually call the related show() method, so the window is
        displayed when created.
        """
        raise NotImplementedError

class aMSNDialogWindow(object):
    """
    This Interface represent a dialog window, used to ask the user
    about something to do.
    """
    def __init__(self, message, actions):
        """
        @type message: str
        @type actions: tuple
        @param actions: A tuple containing the options between
        which the user can choose. Every option is a tuple itself, of the form (name, callback),
        where callback is the function that will be called if the option is selected.

        This will eventually call the related show() method, so the window is
        displayed when created.
        """
        raise NotImplementedError

class aMSNContactInputWindow(object): 
    """
    This Interface represent a window used to get a new contact.
    """
    def __init__(self, message, callback, groups):
        """
        @type message: tuple
        @param message: A tuple with the messages to be shown in the input window,
        of the form (account_string, invite_string).
        @type callback: function
        @param callback: The function that will be called when the contact info has been filled.
        The prototype is callback(email, invite_message, groups).
        @type groups: tuple
        @param groups: a list of existing groups
        """
        raise notImplementedError

class aMSNGroupInputWindow(object): 
    """
    This Interface represent a window used to get a new group.
    """
    def __init__(self, message, callback, contacts):
        """
        @type message: tuple
        @param message: A tuple with the messages to be shown in the input window.
        @type callback: function
        @param callback: The function that will be called when the group info has been filled.
        The prototype is callback(name_group, contacts).
        @type contacts: tuple
        @param contacts: a list of existing contacts
        """
        raise notImplementedError

class aMSNContactDeleteWindow(object): 
    """
    This Interface represent a window used to delete a contact.
    """
    def __init__(self, message, callback, contacts):
        """
        @type message: tuple
        @param message: A tuple with the messages to be shown in the window.
        @type callback: function
        @param callback: The function that will be called when the account has been entered.
        The prototype is callback(account), where account is the email of the account to delete.
        @type contacts: tuple
        @param contacts: a tuple with all the contacts that can be removed in the AddressBook.
        """
        raise notImplementedError

class aMSNGroupDeleteWindow(object): 
    """
    This Interface represent a window used to delete a group.
    """
    def __init__(self, message, callback, groups):
        """
        @type message: tuple
        @param message: A tuple with the messages to be shown in the window.
        @type callback: function
        @param callback: The function that will be called when the group has been entered.
        The prototype is callback(group), where group is the group name.
        @type groups: tuple
        @param groups: a tuple with all the groups that can be deleted.
        """
        raise notImplementedError


########NEW FILE########
__FILENAME__ = window

class aMSNWindow(object):
    """ This Interface represents a window of the application. Everything will be done from here """
    def __init__(self, amsn_core):
        """
        @type amsn_core: aMSNCore
        """

        raise NotImplementedError

    def show(self):
        """ This launches the window, creates it, etc.."""
        raise NotImplementedError

    def hide(self):
        """ This should hide the window"""
        raise NotImplementedError

    def setTitle(self, text):
        """
        This will allow the core to change the current window's title

        @type text: str
        """

        raise NotImplementedError

    def setMenu(self, menu):
        """
        This will allow the core to change the current window's main menu

        @type menu: MenuView
        """

        raise NotImplementedError

########NEW FILE########
__FILENAME__ = cocoa

from main_loop import *
from image import *
from menu import *

from main import *
from contact_list import *
from login import *
from splash import *
from skins import *
########NEW FILE########
__FILENAME__ = contact_list

from amsn2.gui import base

from amsn2.core.views import StringView
from amsn2.core.views import GroupView
from amsn2.core.views import ContactView


class aMSNContactList(base.aMSNContactListWindow):
    def __init__(self, amsn_core, parent):
        pass

    def show(self):
        pass

    def hide(self):
        pass

    def contactStateChange(self, contact):
        pass

    def contactNickChange(self, contact):
        pass

    def contactPSMChange(self, contact):
        pass

    def contactAlarmChange(self, contact):
        pass

    def contactDisplayPictureChange(self, contact):
        pass

    def contactSpaceChange(self, contact):
        pass

    def contactSpaceFetched(self, contact):
        pass

    def contactBlocked(self, contact):
        pass

    def contactUnblocked(self, contact):
        pass

    def contactMoved(self, from_group, to_group, contact):
        pass

    def contactAdded(self, group, contact):
        pass

    def contactRemoved(self, group, contact):
        pass

    def contactRenamed(self, contact):
        pass

    def groupRenamed(self, group):
        pass

    def groupAdded(self, group):
        pass

    def groupRemoved(self, group):
        pass

    def configure(self, option, value):
        pass

    def cget(self, option, value):
        pass

########NEW FILE########
__FILENAME__ = image

from AppKit import *
from amsn2.gui import base

class Image(object):
    """ This interface will represent an image to be used by the UI"""
    def __init__(self, amsn_core, parent):
        """Initialize the interface. You should store the reference to the core in here """
        self._img = NSImage.alloc().initWithSize_((1,1))

    def load(self, resource_name, value):
        """ This method is used to load an image using the name of a resource and a value for that resource
            resource_name can be :
                - 'File', value is the filename
                - 'Skin', value is the skin key
                - some more :)
        """
        self._img.release()

        if (resource_name == 'File'):
            self._img = NSImage.alloc().initWithContentsOfFile_(str(value))

    def append(self, resource_name, value):
        """ This method is used to overlap an image on the current image
            Have a look at the documentation of the 'load' method for the meanings of 'resource_name' and 'value'
        """
        raise NotImplementedError

    def prepend(self, resource_name, value):
        """ This method is used to underlap an image under the current image
            Have a look at the documentation of the 'load' method for the meanings of 'resource_name' and 'value'
        """
        raise NotImplementedError

########NEW FILE########
__FILENAME__ = login

from nibs import CocoaLoginView, CocoaLoggingInView
import main

class aMSNLoginWindow(object):
    loginView = None
    loggingInView = None

    def __init__(self, amsn_core, parent):
        self.amsn_core = amsn_core
        self.parent = parent

        self.switch_to_profile(None)

        # Save the cocoa views that can be loaded in the main window.
        self.loginView = CocoaLoginView.getView()
        self.loggingInView = CocoaLoggingInView.getView()

        # Save a call back method for when the cocoa login: message is sent.
        self.loginView.setParent(self)
        self.loggingInView.setParent(self)

    def show(self):
        # Load the login view into the main window.
        self.parent._loadView(self.loginView)

    # Call back method.
    def login(self, username, password):
        self._username = username
        self._password = password

        # Load loggingInView into main window.
        self.parent._loadView(self.loggingInView)
        self.signin()

    def hide(self):
        pass

    def switch_to_profile(self, profile):
        self.current_profile = profile
        if self.current_profile is not None:
            self._username = self.current_profile.username
            self._password = self.current_profile.password

    def signin(self):
        self.current_profile.username = self._username
        self.current_profile.email = self._username
        self.current_profile.password = self._password
        self.amsn_core.signinToAccount(self, self.current_profile)

    # Set the status message in the login window.
    def onConnecting(self, progress, message):
        self.loggingInView.setStatus(message)


########NEW FILE########
__FILENAME__ = main

from nibs import CocoaMainWindow
from amsn2.gui import base

class aMSNMainWindow(base.aMSNMainWindow):
    cocoaWin = None

    def __init__(self, amsn_core):
        self._amsn_core = amsn_core

        # Load our window.
        self.cocoaWin = CocoaMainWindow.aMSNCocoaMainWindow.alloc().init()

    def setMenu(self, menu_view):
        pass

    def setTitle(self, title):
        self.cocoaWin.setTitle_(title)

    def show(self):
        self.cocoaWin.makeKeyAndOrderFront_(self.cocoaWin)
        self._amsn_core.idlerAdd(self.__on_show)

    def hide(self):
        self.cocoaWin.orderOut_(self.cocoaWin)

    def _loadView(self, view, resize=False):
        prevFrame = self.cocoaWin.frame()
        frame = self.cocoaWin.frameRectForContentRect_(view.frame())
        self.cocoaWin.setFrame_display_animate_((prevFrame.origin, frame.size), True, bool(resize))
        self.cocoaWin.setContentView_(view)
        self.cocoaWin.orderFront_(self.cocoaWin)

    def __on_show(self):
        self._amsn_core.mainWindowShown()

########NEW FILE########
__FILENAME__ = main_loop

import objc
from Foundation import *
from AppKit import *
import sys
from amsn2.gui import base
import gobject

class aMSNMainLoop(base.aMSNMainLoop):
    nsapp = None
    def __init__(self, amsn_core):
        pass

    def run(self):
        self._mainloop = gobject.MainLoop(is_running=True)
        self._context = self._mainloop.get_context()

        self._app = aMSNCocoaNSApplication.sharedApplication()
        self._app.finishLaunching()

        def glib_context_iterate():
            iters = 0
            while iters < 10 and self._context.pending():
                self._context.iteration()
            return True

        while True:
            try:
                # This hangs for at most 100ms, or until an event is fired.
                # More events == less hang.
                self._app.processEvents(100)
                glib_context_iterate()
            except KeyboardInterrupt:
                self.quit()


    def idlerAdd(self, func):
        gobject.idle_add(func)

    def timerAdd(self, delay, func):
        gobject.timeout_add(delay, func)

    def quit(self):
        self._mainloop.quit()
        sys.exit()

class aMSNCocoaNSApplication(NSApplication):
    def init(self):
        super(aMSNCocoaNSApplication, self).init()
        self.setDelegate_(self)
        return self

    # Override run so that it doesn't hang. We'll process events ourself thanks!
    def run(self):
        return Null

    # Looks at the events stack and processes the topmost.
    # return:   True    - An event was processed.
    #           False   - No events in queue.
    def processEvents(self, timeout=100):
        # Get the next event from the queue.
        if timeout < 0:
            eventTimeout = NSDate.distantPast()
        elif timeout == 0:
            eventTimeout = NSDate.distantFuture()
        else:
            eventTimeout = NSDate.dateWithTimeIntervalSinceNow_(float(timeout/1000.0))

        # NSAnyEventMask = 0xffffffff - http://osdir.com/ml/python.pyobjc.devel/2003-10/msg00130.html
        event = self.nextEventMatchingMask_untilDate_inMode_dequeue_( \
            0xffffffff, \
            eventTimeout, \
            NSDefaultRunLoopMode , \
            True)

        # Process event if we have one. (python None == cocoa nil)
        if event != None:
            self.sendEvent_(event)
            return True

        return False

# We call this so that the if someone calls NSApplication.sharedApplication again, they get an aMSNCocoaNSApplication instance rather than a new NSApplication.
aMSNCocoaNSApplication.sharedApplication()

########NEW FILE########
__FILENAME__ = menu

########NEW FILE########
__FILENAME__ = CocoaLoggingInView

from objc import *
from Foundation import *
from AppKit import *

view = None
def getView():
    global view
    return view

# This is a view that we can load into the main window.
class aMSNCocoaLoggingInView(NSView):
    statusText =        IBOutlet('statusText')          # Text field with status text.
    progressIndicator = IBOutlet('progressIndicator')   # Spinner.

    def setParent(self, parent):
        self.parent = parent

    def awakeFromNib(self):
        global view
        view = self
        self.progressIndicator.startAnimation_(self)

    def setStatus(self, newText):
        self.statusText.setStringValue_(newText)

NSBundle.loadNibNamed_owner_('aMSNCocoaLoggingInView', NSApplication.sharedApplication())

########NEW FILE########
__FILENAME__ = CocoaLoginView

import os
from objc import *
from Foundation import *
from AppKit import *

loginView = None
def getView():
    global loginView
    return loginView

# This is a view that we can load into the main window.
class aMSNCocoaLoginView(NSView):
    loginButton =       IBOutlet('loginButton')         # loginButton fires the login: action.
    usernameField =     IBOutlet('usernameField')       # Text field with user/profile name.
    usernameLabel =     IBOutlet('usernameLabel')       # Text label next to usernameField.
    passwordField =     IBOutlet('passwordField')       # Secure text field with password.
    passwordLabel =     IBOutlet('passwordLabel')       # Text label next to passwordField.
    rememberMe =        IBOutlet('rememberMe')          # Check box for save profile.
    rememberPassword =  IBOutlet('rememberPassword')    # Check box for save password.

    def awakeFromNib(self):
        global loginView
        loginView = self

    def setParent(self, parent):
        self.parent = parent

    def login_(self):
        username = str(self.usernameField.stringValue())
        password = str(self.passwordField.stringValue())
        self.parent.login(username, password)


NSBundle.loadNibNamed_owner_('aMSNCocoaLoginView', NSApplication.sharedApplication())

########NEW FILE########
__FILENAME__ = CocoaMainWindow

# NB. This is a NIBless utility class. It may be extended in the future..

# http://kickingkittens.com/wiki/doku.php?id=windowlessnibtutorial
# Code not using NibClassBuilder
#https://develop.participatoryculture.org/trac/democracy/changeset/5711/trunk/tv/platform/osx/frontend/VideoDisplay.py?format=diff&new=5711

import os
from objc import *
from Foundation import *
from AppKit import *

class aMSNCocoaMainWindow(NSWindow):
    def init(self):
        super(aMSNCocoaMainWindow, self).init()
        self.setDelegate_(self)
        return self


########NEW FILE########
__FILENAME__ = CocoaSplashScreenView

from objc import *
from Foundation import *
from AppKit import *

view = None
def getView():
    global view
    return view

class aMSNCocoaSplashScreenView(NSView):
    statusText = IBOutlet('statusText')  # Text field with status text.

    def awakeFromNib(self):
        global view
        view = self

    def setStatus(self, text):
        self.statusText.setStringValue_(text)

NSBundle.loadNibNamed_owner_('aMSNCocoaSplashScreenView', NSApplication.sharedApplication())

########NEW FILE########
__FILENAME__ = CocoaLoginWindow

from amsn2.gui.front_ends.cocoa import main_loop

import os
from objc import *
from Foundation import *
from AppKit import *

#import

#NibClassBuilder.extractClasses('aMSNCocoaMainWindow')

# NibClassBuilder.AutoBaseClass doesn't work for some reason...
class aMSNCocoaMainWindow(NSWindow):
    def test_(self):
        pass

    def awakeFromNib_(self):
        print 'hello world'

NSBundle.loadNibNamed_owner_('aMSNCocoaMainWindow.nib', currentBundle())

########NEW FILE########
__FILENAME__ = skins
# -*- coding: utf-8 -*-
#
# amsn - a python client for the WLM Network
#
# Copyright (C) 2008 Dario Freddi <drf54321@gmail.com>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA

import os.path
from amsn2.gui import base

class Skin(base.Skin):
    def __init__(self, core, path):
        self._path = path
        pass

    def getKey(self, key, default):
        pass

    def setKey(self, key, value):
        pass



class SkinManager(base.SkinManager):
    def __init__(self, core):
        self._core = core
        self.skin = Skin(core, "skins")

    def setSkin(self, name):
        self.skin = Skin(self._core, os.path.join("skins", name))

    def listSkins(self, path):
        pass

########NEW FILE########
__FILENAME__ = splash

from nibs import CocoaSplashScreenView
from amsn2.gui import base

class aMSNSplashScreen(base.aMSNSplashScreen):
    def __init__(self, amsn_core, parent):
        self.parent = parent
        self.view = CocoaSplashScreenView.getView()

    def show(self):
        self.parent._loadView(self.view)

    def hide(self):
        pass

    def setText(self, text):
        self.view.setStatus(text)

    def setImage(self, image):
        pass


########NEW FILE########
__FILENAME__ = command
# -*- encoding: utf-8 -*-
from __future__ import with_statement
import curses
import sys
from threading import Thread
from threading import Condition
import locale

class CommandLine(object):
    def __init__(self, screen, ch_cb):
        self._stdscr = screen
        self._on_char_cb = ch_cb
        self._cb_cond = Condition()
        self._thread = Thread(target=self._get_key)
        self._thread.daemon = True
        self._thread.setDaemon(True)
        self._thread.start()

    def setCharCb(self, ch_cb):
        with self._cb_cond:
            self._on_char_cb = ch_cb
            if ch_cb is not None:
                self._cb_cond.notify()

    def _get_key(self):
        while( True ):
            with self._cb_cond:
                if self._on_char_cb is None:
                    self._cb_cond.wait()
                print >> sys.stderr, "Waiting for char"
                ch = self._stdscr.getkey()
                first = True
                while True:
                    try:
                        ch = ch.decode(locale.getpreferredencoding())
                        self._stdscr.nodelay(0)
                        break
                    except (UnicodeEncodeError, UnicodeDecodeError), e:
                        self._stdscr.nodelay(1)
                        try:
                            ch += self._stdscr.getkey()
                        except:
                            if not first:
                                ch = None
                                self._stdscr.nodelay(0)
                                break
                if ch is not None:
                    self._on_char_cb(ch)

########NEW FILE########
__FILENAME__ = contact_list
from __future__ import with_statement
from amsn2.gui import base
import curses
from threading import Thread
from threading import Condition
import time

class aMSNContactListWindow(base.aMSNContactListWindow):
    def __init__(self, amsn_core, parent):
        self._amsn_core = amsn_core
        self._stdscr = parent._stdscr
        parent.setFocusedWindow(self)
        (y,x) = self._stdscr.getmaxyx()
        # TODO: Use a pad instead
        self._win = curses.newwin(y, int(0.25*x), 0, 0)
        self._win.bkgd(curses.color_pair(0))
        self._win.border()
        self._clwidget = aMSNContactListWidget(amsn_core, self)

    def show(self):
        self._win.refresh()

    def hide(self):
        self._stdscr.clear()
        self._stdscr.refresh()

    def _on_char_cb(self, ch):
        import sys
        print >> sys.stderr, "Length is %d" % len(ch)
        print >> sys.stderr, "Received %s in Contact List" % ch.encode("UTF-8")
        if ch == "KEY_UP":
            self._clwidget.move(-1)
        elif ch == "KEY_DOWN":
            self._clwidget.move(1)
        elif ch == "KEY_NPAGE":
            self._clwidget.move(10)
        elif ch == "KEY_PPAGE":
            self._clwidget.move(-10)

class aMSNContactListWidget(base.aMSNContactListWidget):

    def __init__(self, amsn_core, parent):
        super(aMSNContactListWidget, self).__init__(amsn_core, parent)
        self._groups_order = []
        self._groups = {}
        self._contacts = {}
        self._win = parent._win
        self._stdscr = parent._stdscr
        self._mod_lock = Condition()
        self._modified = False
        self._thread = Thread(target=self.__thread_run)
        self._thread.daemon = True
        self._thread.setDaemon(True)
        self._thread.start()
        self._selected = 1

    def move(self, num):
        self._selected += num
        if self._selected < 1:
            self._selected = 1
        self.__repaint()


    def contactListUpdated(self, clView):
        # Acquire the lock to do modifications
        with self._mod_lock:
            # TODO: Implement it to sort groups
            for g in self._groups_order:
                if g not in clView.group_ids:
                    self._groups.delete(g)
            for g in clView.group_ids:
                if not g in self._groups_order:
                    self._groups[g] = None
            self._groups_order = clView.group_ids
            self._modified = True

            # Notify waiting threads that we modified something
            self._mod_lock.notify()

    def groupUpdated(self, gView):
        # Acquire the lock to do modifications
        with self._mod_lock:
            if self._groups.has_key(gView.uid):
                if self._groups[gView.uid] is not None:
                    #Delete contacts
                    for c in self._groups[gView.uid].contact_ids:
                        if c not in gView.contact_ids:
                            if self._contacts[c]['refs'] == 1:
                                self._contacts.delete(c)
                            else:
                                self._contacts[c]['refs'] -= 1
                #Add contacts
                for c in gView.contact_ids:
                    if not self._contacts.has_key(c):
                        self._contacts[c] = {'cView': None, 'refs': 1}
                        continue
                    #If contact wasn't already there, increment reference count
                    if self._groups[gView.uid] is None or c not in self._groups[gView.uid].contact_ids:
                        self._contacts[c]['refs'] += 1
                self._groups[gView.uid] = gView
                self._modified = True

                # Notify waiting threads that we modified something
                self._mod_lock.notify()

    def contactUpdated(self, cView):
        # Acquire the lock to do modifications
        with self._mod_lock:
            if self._contacts.has_key(cView.uid):
                self._contacts[cView.uid]['cView'] = cView
                self._modified = True

                # Notify waiting threads that we modified something
                self._mod_lock.notify()

    def __repaint(self):
        # Acquire the lock to do modifications
        with self._mod_lock:
            self._win.clear()
            (y, x) = self._stdscr.getmaxyx()
            self._win.move(0,1)
            available = y
            gso = []
            for g in self._groups_order:
                available -= 1
                available -= len(self._groups[g].contact_ids)
                gso.append(g)
                if available <= 0:
                    break
            gso.reverse()
            available = y
            i = 0
            for g in gso:
                if self._groups[g] is not None:
                    available -= 1
                    cids = self._groups[g].contact_ids
                    cids = cids[:available]
                    cids.reverse()
                    for c in cids:
                        if self._contacts.has_key(c) and self._contacts[c]['cView'] is not None:
                            if i == y - self._selected:
                                self._win.bkgdset(curses.color_pair(1))
                            self._win.insstr(str(self._contacts[c]['cView'].name))
                            self._win.bkgdset(curses.color_pair(0))
                            self._win.insch(' ')
                            self._win.insch(curses.ACS_HLINE)
                            self._win.insch(curses.ACS_HLINE)
                            self._win.insch(curses.ACS_LLCORNER)
                            self._win.insertln()
                            self._win.bkgdset(curses.color_pair(0))
                            i += 1
                    if i == y - self._selected:
                        self._win.bkgdset(curses.color_pair(1))
                    self._win.insstr(str(self._groups[g].name))
                    self._win.bkgdset(curses.color_pair(0))
                    self._win.insch(' ')
                    self._win.insch(curses.ACS_LLCORNER)
                    self._win.insertln()
                    i += 1
            self._win.border()
            self._win.refresh()
            self._modified = False


    def __thread_run(self):
        while True:
            # We don't want to repaint too often, once every half second is cool
            time.sleep(0.5)
            with self._mod_lock:
                while not self._modified:
                    self._mod_lock.wait(timeout=1)
                self.__repaint()

########NEW FILE########
__FILENAME__ = curses_
from main_loop import *
from main import *
from contact_list import *
from login import *
from amsn2.gui.base import SkinManager
from splash import *

########NEW FILE########
__FILENAME__ = login
import curses
import curses.textpad


class TextBox(object):
    def __init__(self, win, y, x, txt):
        self._win = win.derwin(1, 30, y, x)
        self._win.bkgd(' ', curses.color_pair(0))
        self._win.clear()
        self._txtbox = curses.textpad.Textbox(self._win)
        self._txtbox.stripspaces = True

        if txt is not None:
            self._insert(txt)

    def edit(self):
        return self._txtbox.edit()

    def value(self):
        return self._txtbox.gather()

    def _insert(self, txt):
        for ch in txt:
            self._txtbox.do_command(ch)

class PasswordBox(TextBox):
    def __init__(self, win, y, x, txt):
        self._password = ''
        super(PasswordBox, self).__init__(win, y, x, txt)

    def edit(self, cb=None):
        return self._txtbox.edit(self._validateInput)

    def value(self):
        return self._password

    def _validateInput(self, ch):
        if ch in (curses.KEY_BACKSPACE, curses.ascii.BS):
            self._password = self._password[0:-1]
            return ch
        elif curses.ascii.isprint(ch):
            self._password += chr(ch)
            return '*'
        else:
            return ch

    def _insert(self, str):
        for ch in str:
            self._password += ch
            self._txtbox.do_command('*')

class aMSNLoginWindow(object):
    def __init__(self, amsn_core, parent):
        self._amsn_core = amsn_core
        self.switch_to_profile(None)
        self._stdscr = parent._stdscr

        (y, x) = self._stdscr.getmaxyx()
        wy = int(y * 0.8)
        wx = int(x * 0.8)
        sy = int((y - wy)/2)
        sx = int((x - wx)/2)
        self._win = curses.newwin(wy, wx, sy, sx)

    def show(self):
        self._win.border()
        self._win.bkgd(' ', curses.color_pair(1))
        self._win.addstr(5, 5, "Account : ", curses.A_BOLD)
        self._username_t = TextBox(self._win, 5, 17, self._username)

        self._win.addstr(8, 5, "Password : ", curses.A_BOLD)
        self._password_t = PasswordBox(self._win, 8, 17, self._password)

        self._win.refresh()

        self._username_t.edit()
        self._password_t.edit()

        curses.curs_set(0)
        self.signin()

    def hide(self):
        self._username_t = None
        self._password_t = None
        self._win = None
        self._stdscr.clear()
        self._stdscr.refresh()

    def switch_to_profile(self, profile):
        self.current_profile = profile
        if self.current_profile is not None:
            self._username = self.current_profile.username
            self._password = self.current_profile.password

    def signin(self):
        self.current_profile.username = self._username_t.value()
        self.current_profile.email = self._username_t.value()
        self.current_profile.password = self._password_t.value()
        self._amsn_core.signinToAccount(self, self.current_profile)


    def onConnecting(self, progress, message):
        self._username_t = None
        self._password_t = None
        self._win.clear()

        self._win.addstr(10, 25, message, curses.A_BOLD | curses.A_STANDOUT)
        self._win.refresh()

########NEW FILE########
__FILENAME__ = main

from amsn2.gui import base
import command

import curses
class aMSNMainWindow(base.aMSNMainWindow):
    def __init__(self, amsn_core):
        self._amsn_core = amsn_core

    def show(self):
        self._stdscr = curses.initscr()
        self._command_line = command.CommandLine(self._stdscr, None)
        self.__init_colors()
        curses.noecho()
        curses.cbreak()
        self._stdscr.keypad(1)
        self._stdscr.box()
        self._stdscr.refresh()
        self._amsn_core.idlerAdd(self.__on_show)

    def hide(self):
        curses.nocbreak()
        self._stdscr.keypad(0)
        curses.echo()
        curses.endwin()

    def __on_show(self):
        self._amsn_core.mainWindowShown()

    def setTitle(self,title):
        self._title = title

    def setMenu(self,menu):
        pass

    def setFocusedWindow(self, window):
        self._command_line.setCharCb(window._on_char_cb)

    def __init_colors(self):
        curses.start_color()
        curses.init_pair(1, curses.COLOR_YELLOW, curses.COLOR_WHITE)
        curses.init_pair(2, curses.COLOR_BLACK, curses.COLOR_BLUE)


########NEW FILE########
__FILENAME__ = main_loop

from amsn2.gui import base
import gobject
gobject.threads_init()

class aMSNMainLoop(base.aMSNMainLoop):
    def __init__(self, amsn_core):
        self._amsn_core = amsn_core

    def run(self):
        self._mainloop = gobject.MainLoop(is_running=True)

        while self._mainloop.is_running():
            try:
                self._mainloop.run()
            except KeyboardInterrupt:
                self.quit()

    def idlerAdd(self, func):
        gobject.idle_add(func)

    def timerAdd(self, delay, func):
        gobject.timeout_add(delay, func)

    def quit(self):
        import curses
        stdscr = self._amsn_core.getMainWindow()._stdscr
        curses.nocbreak()
        stdscr.keypad(0)
        curses.echo()
        curses.endwin()
        self._mainloop.quit()


########NEW FILE########
__FILENAME__ = splash
from amsn2.gui import base

class aMSNSplashScreen(base.aMSNSplashScreen):
    """This is the splashscreen for ncurses"""
    def __init__(self, amsn_core, parent):
        """Initialize the interface. You should store the reference to the core in here
        as well as a reference to the window where you will show the splash screen
        """
        # Is it needed in ncurses?
        pass

    def show(self):
        """ Draw the splashscreen """
        pass

    def hide(self):
        """ Hide the splashscreen """
        pass

    def setText(self, text):
        """ Shows a different text inside the splashscreen """
        pass

    def setImage(self, image):
        """ Set the image to show in the splashscreen. This is an ImageView object """
        pass

########NEW FILE########
__FILENAME__ = chat_window
from constants import *
import evas
import ecore
import elementary
import skins
import window
from amsn2.gui import base
from amsn2.core.views import ContactView, StringView
from constants import *

class aMSNChatWindow(window.aMSNWindow, base.aMSNChatWindow):
    def __init__(self, conversation_manager):
        self._conversation_manager = conversation_manager
        window.aMSNWindow.__init__(self, conversation_manager._core)
        self._container = aMSNChatWidgetContainer()
        self.setTitle(TITLE + " - Chatwindow")
        self.resize(CW_WIDTH, CW_HEIGHT)

        self.autodel_set(True)

    def addChatWidget(self, chat_widget):
        self.resize_object_add(chat_widget)
        chat_widget.show()
        print chat_widget.ine.geometry
        print chat_widget.insc.geometry

#TODO: ChatWidgetContainer
class aMSNChatWidgetContainer:
    pass




class aMSNChatWidget(elementary.Box, base.aMSNChatWidget):
    def __init__(self, amsn_conversation, parent, contacts_uid):
        self._parent = parent
        elementary.Box.__init__(self, parent)
        self.size_hint_weight_set(evas.EVAS_HINT_EXPAND, evas.EVAS_HINT_EXPAND)
        self.size_hint_align_set(evas.EVAS_HINT_FILL, evas.EVAS_HINT_FILL)
        self.homogenous_set(False)
        self._parent.resize_object_add(self)
        self.show()
        self._amsn_conversation = amsn_conversation

        self.outsc = elementary.Scroller(parent)
        self.outsc.size_hint_weight_set(evas.EVAS_HINT_EXPAND,
                                        evas.EVAS_HINT_EXPAND)
        self.outsc.size_hint_align_set(evas.EVAS_HINT_FILL,
                                       evas.EVAS_HINT_FILL)
        self.outsc.policy_set(elementary.ELM_SCROLLER_POLICY_AUTO,
                      elementary.ELM_SCROLLER_POLICY_AUTO)
        self.outsc.bounce_set(False, True)
        self.pack_end(self.outsc)

        self.outbx = elementary.Box(parent)
        self.outsc.content_set(self.outbx)
        self.outbx.show()
        self.outsc.show()

        self.inbx = elementary.Box(parent)
        self.inbx.horizontal_set(True)
        self.inbx.homogenous_set(False)
        self.inbx.size_hint_weight_set(evas.EVAS_HINT_EXPAND,
                                       0.0)
        self.inbx.size_hint_align_set(evas.EVAS_HINT_FILL,
                                      0.5)
        self.pack_end(self.inbx)

        self.insc = elementary.Scroller(parent)
        self.insc.content_min_limit(0, 1)
        self.insc.policy_set(elementary.ELM_SCROLLER_POLICY_OFF,
                             elementary.ELM_SCROLLER_POLICY_OFF)
        self.insc.size_hint_weight_set(evas.EVAS_HINT_EXPAND,
                                       evas.EVAS_HINT_EXPAND)
        self.insc.size_hint_align_set(evas.EVAS_HINT_FILL, evas.EVAS_HINT_FILL)
        self.inbx.pack_end(self.insc)

        self.ine = elementary.Entry(parent)
        self.ine.size_hint_weight_set(evas.EVAS_HINT_EXPAND,
                                      evas.EVAS_HINT_EXPAND)
        self.ine.size_hint_align_set(evas.EVAS_HINT_FILL, evas.EVAS_HINT_FILL)
        self.insc.content_set(self.ine)
        self.ine.show()
        self.insc.show()

        self.inb = elementary.Button(parent)
        self.inb.label_set("Send")
        self.inb.callback_clicked_add(self.__sendButton_cb, self.ine)
        self.inbx.pack_end(self.inb)
        self.inb.show()
        self.inbx.show()

        self.show()

    def __sendButton_cb(self, button, entry):
        pass
        """
        msg = self.__input_tb.text_get(0)
        self.__input_tb.clear()
        strv = StringView()
        strv.appendText(msg)
        self._amsn_conversation.sendMessage(strv)
        """

    def __outputAppendMsg(self, msg):
        pass
        """
        self.__output_tb.insert(self.__iter_out, msg)
        """


    def onUserJoined(self, contact):
        print "%s joined the conversation" % (contact,)

    def onUserLeft(self, contact):
        print "%s left the conversation" % (contact,)

    def onUserTyping(self, contact):
        print "%s is typing" % (contact,)

    def onMessageReceived(self, messageview, formatting=None):
        pass
        """
        self.__outputAppendMsg(str(messageview.toStringView()))
        """

    def nudge(self):
        #TODO
        print "Nudge received!!!"

########NEW FILE########
__FILENAME__ = constants

WIDTH = 400
HEIGHT = 600
MIN_WIDTH = 100
MIN_HEIGHT = 150

CW_WIDTH = 450
CW_HEIGHT = 450
CW_IN_MIN_WIDTH = 180
CW_IN_MIN_HEIGHT = 100
CW_OUT_MIN_WIDTH = 200
CW_OUT_MIN_HEIGHT = 100

THEME_FILE = "amsn2/themes/default.edj"
TITLE = "aMSN 2"
WM_NAME = "aMSN2"
WM_CLASS = "main"

DP_IN_CL = True

########NEW FILE########
__FILENAME__ = contact_list

from constants import *
import evas
import edje
import ecore
import ecore.evas
import elementary

from image import *

from amsn2.core.views import StringView
from amsn2.gui import base
import papyon

class aMSNContactListWindow(elementary.Box, base.aMSNContactListWindow):
    def __init__(self, core, parent):
        base.aMSNContactListWindow.__init__(self, core, parent)
        self._core = core
        self._evas = parent._evas
        self._parent = parent
        self._skin = core._skin_manager.skin
        elementary.Box.__init__(self, parent)
        self.size_hint_weight_set(1.0, 1.0)
        self.size_hint_align_set(-1.0, -1.0)
        self.homogenous_set(False)
        self._parent.resize_object_add(self)
        self.show()

        """ Personal Info """
        self._personal_info = PersonalInfoWidget(self._core, self._parent)
        self._personal_info.size_hint_weight_set(1.0, 0.0)
        self._personal_info.size_hint_align_set(-1.0, 1.0)
        self.pack_start(self._personal_info)
        self._personal_info.show()

        """ ContactList Widget """
        self._clwidget = aMSNContactListWidget(self._core, self._parent)
        self._clwidget.size_hint_weight_set(1.0, 1.0)
        self._clwidget.size_hint_align_set(-1.0, -1.0)
        self.pack_end(self._clwidget)
        self._clwidget.show()

        self._parent.show()

    def setTitle(self, text):
        self._parent.setTitle(text)

    def setMenu(self, menu):
        self._parent.setMenu(menu)

    def myInfoUpdated(self, view):
        self._personal_info.myInfoUpdated(view)


class PersonalInfoWidget(elementary.Layout):
    def __init__(self, amsn_core, parent):
        self._core = amsn_core
        self._parent = parent
        self._personal_info_view = None
        elementary.Layout.__init__(self, self._parent)
        self.file_set(THEME_FILE, "personal_info")

        self._dp = elementary.Button(self._parent)
        self._dp.label_set("pouet")
        self._dp.size_hint_weight_set(1.0, 1.0)
        self.content_set("dp", self._dp);
        self._dp.show()

        self._presence = elementary.Hoversel(self._parent)
        self._presence.hover_parent_set(self._parent)
        for key in self._core.p2s:
            name = self._core.p2s[key]
            _, path = self._core._theme_manager.get_statusicon("buddy_%s" % name)
            if name == 'offline': continue
            def cb(hoversel, it, key):
                hoversel.label_set(it.label_get())
                (icon_file, icon_group, icon_type) = it.icon_get()
                ic = elementary.Icon(hoversel)
                ic.scale_set(0, 1)
                if icon_type == elementary.ELM_ICON_FILE:
                    ic.file_set(icon_file, icon_group)
                else:
                    ic.standart_set(icon_file)
                hoversel.icon_set(ic)
                ic.show()
                #TODO
            self._presence.item_add(name, path, elementary.ELM_ICON_FILE, cb,
                                   key)
        self.content_set("presence", self._presence);
        self._presence.show()

        sc = elementary.Scroller(self._parent)
        sc.content_min_limit(0, 1)
        sc.policy_set(elementary.ELM_SCROLLER_POLICY_OFF,
                      elementary.ELM_SCROLLER_POLICY_OFF);
        sc.size_hint_weight_set(1.0, 0.0)
        sc.size_hint_align_set(-1.0, 0.0)
        self.content_set("nick", sc)
        self._nick = elementary.Entry(self._parent)
        self._nick.single_line_set(True)
        self._nick.size_hint_weight_set(1.0, 0.0)
        self._nick.size_hint_align_set(-1.0, 0.0)
        sc.content_set(self._nick)
        self._nick.show()
        sc.show()

        sc = elementary.Scroller(self._parent)
        sc.content_min_limit(0, 1)
        sc.policy_set(elementary.ELM_SCROLLER_POLICY_OFF,
                      elementary.ELM_SCROLLER_POLICY_OFF);
        sc.size_hint_weight_set(1.0, 0.0)
        sc.size_hint_align_set(-1.0, -1.0)
        self.content_set("psm", sc);
        self._psm = elementary.Entry(self._parent)
        self._psm.single_line_set(True)
        self._psm.size_hint_weight_set(1.0, 0.0)
        self._psm.size_hint_align_set(-1.0, -1.0)
        sc.content_set(self._psm)
        self._psm.show()
        sc.show()

        sc = elementary.Scroller(self._parent)
        sc.content_min_limit(0, 1)
        sc.policy_set(elementary.ELM_SCROLLER_POLICY_OFF,
                      elementary.ELM_SCROLLER_POLICY_OFF)
        sc.size_hint_weight_set(1.0, 0.0)
        sc.size_hint_align_set(-1.0, -1.0)
        self.content_set("current_media", sc)
        self._cm = elementary.Entry(self._parent)
        self._cm.single_line_set(True)
        self._cm.size_hint_weight_set(1.0, 0.0)
        self._cm.size_hint_align_set(-1.0, -1.0)
        sc.content_set(self._cm)
        self._cm.show()
        sc.show()

    def myInfoUpdated(self, view):
        print "myInfoUpdated: view=%s" %(view,)
        self._personal_info_view = view

        #TODO
        self._dp.show()
        self._presence.show()

        self._nick.entry_set("nick is"+str(view.nick));
        self._nick.show()

        self._psm.entry_set("psm is "+str(view.psm));
        self._psm.show()

        self._cm.entry_set("cm is "+str(view.current_media));
        self._cm.show()

        self.show()

class aMSNContactListWidget(elementary.Box, base.aMSNContactListWidget):
    def __init__(self, core, parent):
        base.aMSNContactListWidget.__init__(self, core, parent)
        elementary.Box.__init__(self, parent)
        self._core = core
        self._evas = parent._evas
        self._skin = core._skin_manager.skin

        self.homogenous_set(False)
        self.size_hint_weight_set(1.0, 1.0)
        self.size_hint_align_set(-1.0, -1.0)
        self.show()

        self._sc = elementary.Scroller(parent)
        self._sc.size_hint_weight_set(1.0, 1.0)
        self._sc.size_hint_align_set(-1.0, -1.0)
        self._sc.policy_set(elementary.ELM_SCROLLER_POLICY_OFF,
                            elementary.ELM_SCROLLER_POLICY_AUTO)
        self.pack_start(self._sc)
        self._sc.show()

        self.group_holder = GroupHolder(self._evas, self, self._skin)
        self._sc.content_set(self.group_holder)
        self.group_holder.show()


    def contactUpdated(self, contact):
        for gi in self.group_holder.group_items_list:
            if contact.uid in gi.contact_holder.contacts_dict:
                gi.contact_holder.contact_updated(contact)

    def groupUpdated(self, group):
        if group.uid in self.group_holder.group_items_dict:
            self.group_holder.group_items_dict[group.uid].group_updated(group)


    def contactListUpdated(self, clview):
        self.group_holder.viewUpdated(clview)


class ContactHolder(elementary.Box):
    def __init__(self, parent):
        elementary.Box.__init__(self, parent)
        self.contacts_dict = {}
        self.contacts_list = []
        self._skin = parent._skin
        self._parent = parent
        self.size_hint_weight_set(1.0, 1.0)
        self.size_hint_align_set(-1.0, -1.0)

    def contact_updated(self, contactview):
        #TODO : clean :)
        try:
            c = self.contacts_dict[contactview.uid]
        except KeyError:
            return
        c.edje_get().part_text_set("contact_data", str(contactview.name))

        if DP_IN_CL:
            # add the dp
            dp = Image(self._skin, self.evas_get(), contactview.dp)
            c.content_set("buddy_icon", dp)
        else:
            # add the buddy icon
            # Remove the current icon
            icon = Image(self._skin, self.evas_get(), contactview.icon)
            c.content_set("buddy_icon", icon)

        if contactview.on_click is not None:
            def cb_(obj,event):
                contactview.on_click(obj.data['uid'])
            if c.data['on_click'] is not None:
                c.on_mouse_down_del(c.data['on_click'])
            c.data['on_click'] = cb_
            c.on_mouse_down_add(cb_)
        else:
            if c.data['on_click'] is not None:
                c.on_mouse_down_del(c.data['on_click'])
                c.data['on_click'] = None
        c.size_hint_min_set(26, 26)
        c.show()
        print c.size_hint_min_get()


    def groupViewUpdated(self, groupview):
        contact_items = self.contacts_list
        cuids = [c.uid for g in contact_items]
        self.contact_items = []
        for cid in groupview.contact_ids:
            if cid in cuids:
                self.contacts_list.append(self.contacts_dict[gid])
            else:
                #New contact
                self.add_contact(cid)

        #Remove unused contacts
        for cid in cuids:
            if cid not in self.contacts_dict:
                self.remove_contact(cid)

    def add_contact(self, uid):
        new_contact = elementary.Layout(self)
        new_contact.file_set(THEME_FILE, "contact_item")
        new_contact.data['uid'] = uid
        new_contact.data['on_click'] = None
        self.contacts_list.append(new_contact)
        self.contacts_dict[uid] = new_contact
        self.pack_end(new_contact)
        new_contact.size_hint_min_set(26, 26)
        new_contact.size_hint_weight_set(1.0, 1.0)
        new_contact.size_hint_align_set(-1.0, -1.0)
        print new_contact.size_hint_min_get()


    def remove_contact(self, uid):
        #TODO: remove from box
        try:
            ci = self.contacts_dict[uid]
            del self.contacts_dict[uid]
            try:
                self.contacts_list.remove(ci)
            except ValueError:
                pass
            del ci
        except KeyError:
            pass

    def num_contacts(self):
        return len(self.contacts_list)

class GroupItem(elementary.Layout):
    def __init__(self, parent, uid):
        elementary.Layout.__init__(self, parent)
        self.file_set(THEME_FILE, "group_item")
        self._parent = parent
        self._skin = parent._skin
        self.expanded = True
        self.uid = uid
        self.contact_holder = ContactHolder(self)
        self.content_set("contacts", self.contact_holder);
        self.contact_holder.show()

        self.edj = self.edje_get()
        self.edj.signal_callback_add("collapsed", "*", self.__collapsed_cb)
        self.edj.signal_callback_add("expanded", "*", self.__expanded_cb)

        self.size_hint_weight_set(1.0, 0.0)
        self.size_hint_align_set(-1.0, 0.0)

    def num_contacts(self):
        if self.expanded == False:
            return 0
        else:
            return self.contact_holder.num_contacts()

    def group_updated(self, groupview):
        self.edj.part_text_set("group_name", str(groupview.name))
        self.contact_holder.groupViewUpdated(groupview)

    # Private methods
    def __expanded_cb(self, edje_obj, signal, source):
        self.expanded = True
        print "expand"
        print self.size_hint_min_get()
        print self.contact_holder.size_hint_min_get()
        for c in self.contact_holder.contacts_list:
            print c.size_hint_min_get()
        self.contact_holder.hide()

    def __collapsed_cb(self, edje_obj, signal, source):
        self.expanded = False
        print "collapse"
        print self.size_hint_min_get()
        print self.contact_holder.size_hint_min_get()
        for c in self.contact_holder.contacts_list:
            print c.size_hint_min_get()
        self.contact_holder.show()

class GroupHolder(elementary.Box):
    def __init__(self, ecanvas, parent, skin):
        elementary.Box.__init__(self, parent)
        self.group_items_list = []
        self.group_items_dict = {}
        self._parent = parent
        self._skin = skin
        self.size_hint_weight_set(1.0, 0.0)
        self.size_hint_align_set(-1.0, 0.0)

    def add_group(self, uid):
        new_group = GroupItem(self, uid)
        self.group_items_list.append(new_group)
        self.group_items_dict[uid] = new_group
        self.pack_end(new_group)
        new_group.show()

    def remove_group(self, uid):
        #TODO: remove from box
        try:
            gi = self.group_items_dict[uid]
            del self.group_items_dict[uid]
            try:
                self.group_items_list.remove(gi)
            except ValueError:
                pass
            del gi
        except KeyError:
            pass

    def viewUpdated(self, clview):
        group_items = self.group_items_list
        guids = [g.uid for g in group_items]
        self.group_items = []
        for gid in clview.group_ids:
            if gid in guids:
                self.group_items_list.append(self.group_items_dict[gid])
            else:
                #New group
                self.add_group(gid)

        #Remove unused groups
        for gid in guids:
            if gid not in self.group_items_dict:
                self.remove_group(gid)


########NEW FILE########
__FILENAME__ = efl
from main_loop import *
from main import *
from login import *
from contact_list import *
from image import *
from splash import *
from skins import *
from chat_window import *

########NEW FILE########
__FILENAME__ = image

import evas
import ecore
import ecore.evas

import tempfile
import os

from amsn2.core.views import imageview

class Image(evas.SmartObject):
    def __init__(self, skin, canvas, view):
        self._evas = canvas
        evas.SmartObject.__init__(self, self._evas)

        self._skin = skin
        self._imgs = []
        self.propagate_events = True

        self.load(view)

    #######################################################
    #Public method
    def load(self, view):
        for img in self._imgs:
            self.member_del(img)

        self._imgs = []
        i = 0
        for (resource_type, value) in view.imgs:
            self._imgs.append(self._evas.Image())
            self.member_add(self._imgs[-1])
            try:
                loadMethod = getattr(self, "_loadFrom%s" % resource_type)
            except AttributeError, e:
                print "From load in efl/image.py:\n\t(resource_type, value) = (%s, %s)\n\tAttributeError: %s" % (resource_type, value, e)
            else:
                loadMethod(value, -1, view, i)
                i += 1



    def _loadFromFilename(self, filename, pos=0, view=None, i=0):
        try:
            self._imgs[pos].file_set(filename)
        except evas.EvasLoadError, e:
            print "EvasLoadError: %s" % (e,)

    def _loadFromEET(self, (eetfile, key), pos=0, view=None, i=0):
        try:
            self._imgs[pos].file_set(eetfile, key)
        except evas.EvasLoadError, e:
            print "EvasLoadError: %s" % (e,)

    def _loadFromFileObject(self, fileobject, pos=0, view=None, i=0):
        (fno, tf) = tempfile.mkstemp()
        f = os.fdopen(fno, 'w+b')
        f.write(fileobject.read())
        f.close()
        if view is not None:
            view.imgs[i] = ("Filename", tf)
        self._loadFromFilename(tf, pos, view, i)


    def _loadFromTheme(self, resource_name, pos=0, view=None, i=0):
        res = self._skin.getKey(resource_name)
        if res is not None:
            (type, value) = res
            try:
                loadMethod = getattr(self, "_loadFrom%s" % type)
            except AttributeError, e:
                print "From _loadFromSkin in efl/image.py:\n\t(type, value) = (%s, %s)\n\tAttributeError: %s" % (type, value, e)
            else:
                loadMethod(value, pos, view, i)

    def _loadFromNone(self, r, pos=0):
        pass

    #######################################################
    # Need to overwritre some evas.SmartObject methods:

    def show(self):
        for img in self._imgs:
            img.show()

    def hide(self):
        for img in self._imgs:
            img.hide()

    def resize(self, w, h):
        for img in self._imgs:
            img.size_set(w, h)
            img.fill_set(0,0,w,h)

    def clip_set(self, obj):
        for img in self._imgs:
            img.clip_set(obj)

    def clip_unset(self):
        for img in self._imgs:
            img.clip_unset()

    def move(self, x, y):
        for img in self._imgs:
            img.move(x ,y)



########NEW FILE########
__FILENAME__ = login
from constants import *
import edje
import ecore
import ecore.x
import elementary

from amsn2.gui import base
from amsn2.core.views import accountview

#TODO: del
#TODO: switch to elm_layout?
class aMSNLoginWindow(base.aMSNLoginWindow):
    def __init__(self, amsn_core, parent):
        self._core = amsn_core
        self._evas = parent._evas
        self._parent = parent
        self._account_views = []

        edje.frametime_set(1.0 / 30)

        try:
            self._edje = edje.Edje(self._evas, file=THEME_FILE,
                                group="login_screen")
        except edje.EdjeLoadError, e:
            raise SystemExit("error loading %s: %s" % (THEME_FILE, e))

        self._parent.resize_object_add(self._edje)
        self._edje.size_hint_weight_set(1.0, 1.0)
        self.show()

        sc = elementary.Scroller(self._edje)
        sc.content_min_limit(0, 1)
        sc.policy_set(elementary.ELM_SCROLLER_POLICY_OFF,
                      elementary.ELM_SCROLLER_POLICY_OFF);
        sc.size_hint_weight_set(1.0, 0.0)
        sc.size_hint_align_set(-1.0, -1.0)
        self._edje.part_swallow("login_screen.username", sc)
        self.username = elementary.Entry(self._edje)
        self.username.single_line_set(1)
        self.username.size_hint_weight_set(1.0, 0.0)
        self.username.size_hint_align_set(-1.0, -1.0)
        sc.content_set(self.username)
        self.username.show()
        sc.show()

        sc = elementary.Scroller(self._edje)
        sc.content_min_limit(0, 1)
        sc.policy_set(elementary.ELM_SCROLLER_POLICY_OFF,
                      elementary.ELM_SCROLLER_POLICY_OFF);
        sc.size_hint_weight_set(1.0, 0.0)
        sc.size_hint_align_set(-1.0, -1.0)
        self._edje.part_swallow("login_screen.password", sc)
        self.password = elementary.Entry(self._edje)
        self.password.single_line_set(1)
        self.password.password_set(1)
        self.password.size_hint_weight_set(1.0, 1.0)
        self.password.size_hint_align_set(-1.0, -1.0)
        sc.content_set(self.password)
        self.password.show()
        sc.show()

        self.presence = elementary.Hoversel(self._edje)
        self.presence.hover_parent_set(self._parent)
        for key in self._core.p2s:
            name = self._core.p2s[key]
            _, path = self._core._theme_manager.get_statusicon("buddy_%s" % name)
            if name == 'offline': continue
            def cb(hoversel, it, key):
                hoversel.label_set(it.label_get())
                (icon_file, icon_group, icon_type) = it.icon_get()
                ic = elementary.Icon(hoversel)
                ic.scale_set(0, 1)
                if icon_type == elementary.ELM_ICON_FILE:
                    ic.file_set(icon_file, icon_group)
                else:
                    ic.standart_set(icon_file)
                hoversel.icon_set(ic)
                ic.show()
                self.presence_key = data

            self.presence.item_add(name, path, elementary.ELM_ICON_FILE, cb,
                                   key)

        self.presence_key = self._core.Presence.ONLINE
        self.presence.label_set(self._core.p2s[self.presence_key])
        ic = elementary.Icon(self.presence)
        ic.scale_set(0, 1)
        _, path = self._core._theme_manager.get_statusicon("buddy_%s" %
                            self._core.p2s[self.presence_key])
        ic.file_set(path)
        self.presence.icon_set(ic)
        ic.show()
        self.presence.size_hint_weight_set(0.0, 0.0)
        self.presence.size_hint_align_set(0.5, 0.5)
        self._edje.part_swallow("login_screen.presence", self.presence)
        self.presence.show()

        self.save = elementary.Check(self._edje)
        self.save.label_set("Remember Me")
        def cb(obj):
            if obj.state_get():
                self.save_password.disabled_set(False)
            else:
                self.save_password.disabled_set(True)
                self.save_password.state_set(False)
                self.autologin.disabled_set(True)
                self.autologin.state_set(False)
        self.save.callback_changed_add(cb)
        self._edje.part_swallow("login_screen.remember_me", self.save)
        self.save.show()

        self.save_password = elementary.Check(self._edje)
        self.save_password.label_set("Remember Password")
        self.save_password.disabled_set(True)
        def cb(obj):
            if obj.state_get():
                self.autologin.disabled_set(False)
            else:
                self.autologin.disabled_set(True)
                self.autologin.state_set(False)
        self.save_password.callback_changed_add(cb)
        self._edje.part_swallow("login_screen.remember_password",
                                self.save_password)
        self.save_password.show()

        self.autologin = elementary.Check(self._edje)
        self.autologin.label_set("Auto Login")
        self.autologin.disabled_set(True)
        self._edje.part_swallow("login_screen.auto_login", self.autologin)
        self.autologin.show()

        if self._edje.part_exists("login_screen.signin"):
           self.signin_b = elementary.Button(self._edje)
           self.signin_b.label_set("Sign in")
           self.signin_b.callback_clicked_add(self.__signin_button_cb)
           self.signin_b.show()
           self._edje.part_swallow("login_screen.signin", self.signin_b)
        else:
           self._edje.signal_callback_add("signin", "*", self.__signin_cb)


    def show(self):
        self._parent.resize_object_add(self._edje)
        self._edje.show()

    def hide(self):
        self._parent.resize_object_del(self._edje)
        self._edje.hide()
        #FIXME: those are not hidden by self._edje.hide()
        self.password.hide()
        self.username.hide()
        try:
            getattr(self, "signin_b")
        except AttributeError:
            pass
        else:
            self.signin_b.hide()


    def setAccounts(self, accountviews):
        #TODO: support more than just 1 account...
        self._account_views = accountviews
        if accountviews:
            #Only select the first one
            acc = accountviews[0]
            self.username.entry_set(acc.email)
            self.password.entry_set(acc.password)

            self.presence_key = acc.presence
            self.presence.label_set(self._core.p2s[self.presence_key])
            ic = elementary.Icon(self.presence)
            ic.scale_set(0, 1)
            _, path = self._core._theme_manager.get_statusicon("buddy_%s" %
                                self._core.p2s[self.presence_key])
            ic.file_set(path)
            self.presence.icon_set(ic)
            ic.show()

            self.save.state_set(acc.save)
            if acc.save:
                self.save_password.disabled_set(False)
            else:
                self.save_password.disabled_set(True)
            self.save_password.state_set(acc.save_password)
            if acc.save_password:
                self.autologin.disabled_set(False)
            else:
                self.autologin.disabled_set(True)
            self.autologin.state_set(acc.autologin)


    def signin(self):
        email = elementary.Entry.markup_to_utf8(self.username.entry_get()).strip()
        password = elementary.Entry.markup_to_utf8(self.password.entry_get()).strip()

        accv = [accv for accv in self._account_views if accv.email == email]
        if not accv:
            accv = AccountView(self._amsn_core, email)
        else:
            accv = accv[0]
        accv.password = password

        accv.presence = self.presence_key

        accv.save = self.save.state_get()
        accv.save_password = self.save_password.state_get()
        accv.autologin = self.autologin.state_get()

        self._core.signinToAccount(self, accv)

    def onConnecting(self, progress, message):
        self._edje.signal_emit("connecting", "")
        msg1 = ""
        msg2 = ""
        try:
            msg1 = message.split("\n")[0]
        except IndexError:
            pass

        try:
            msg2 = message.split("\n")[1]
        except IndexError:
            pass
        self._edje.part_text_set("connection_status", msg1)
        self._edje.part_text_set("connection_status2", msg2)


    def __signin_cb(self, edje_obj, signal, source):
        self.signin()

    def __signin_button_cb(self, bt):
        self.signin()

########NEW FILE########
__FILENAME__ = main
from constants import *
import ecore
import ecore.evas
import ecore.x
import skins
import window
from amsn2.gui import base
from amsn2.core.views import MenuView, MenuItemView

class aMSNMainWindow(window.aMSNWindow, base.aMSNMainWindow):
    def __init__(self, amsn_core):
        window.aMSNWindow.__init__(self, amsn_core)
        self.callback_destroy_add(self.__on_delete_request)
        self.on_show_add(self.__on_show)
        self.on_key_down_add(self.__on_key_down)

    """ Private methods
        thoses methods shouldn't be called by outside or by an inherited class
        since that class shouldn't be herited
    """
    def __on_show(self, evas_obj):
        self._amsn_core.mainWindowShown()

    def __on_delete_request(self, win):
        self._amsn_core.quit()

    def __on_key_down(self, obj, event):
        if event.keyname == "Escape":
            self._amsn_core.quit()
        else:
            window.aMSNWindow._on_key_down(self,obj, event)

########NEW FILE########
__FILENAME__ = main_loop

from amsn2.gui import base
import gobject
import ecore
import elementary

class aMSNMainLoop(base.aMSNMainLoop):
    def __init__(self, amsn_core):
        elementary.init()

    def run(self):
        #ecore.main_loop_glib_integrate()
        mainloop = gobject.MainLoop(is_running=True)
        context = mainloop.get_context()

        def glib_context_iterate():
            iters = 0
            while iters < 10 and context.pending():
                context.iteration()
                iters += 1
            return True

        # Every 100ms, call an iteration of the glib main context loop
        # to allow the protocol context loop to work
        ecore.timer_add(0.1, glib_context_iterate)

        #equals elementary.run()
        ecore.main_loop_begin()

    def idlerAdd(self, func):
        ecore.idler_add(func)

    def timerAdd(self, delay, func):
        ecore.timer_add(delay, func)

    def quit(self):
        ecore.main_loop_quit()


########NEW FILE########
__FILENAME__ = skins
import os.path
from amsn2.gui import base

class Skin(base.Skin):
    def __init__(self, core, path):
        self._path = path
        self._dict = {}
        #TODO : remove, it's just here for test purpose
        #TODO : explain a bit :D
        self.setKey("buddy_online", ("Filename", "amsn2/themes/default/images/online.png"))
        self.setKey("emblem_online", ("Filename", "amsn2/themes/default/images/contact_list/plain_emblem.png"))

        self.setKey("buddy_away", ("Filename", "amsn2/themes/default/images/away.png"))
        self.setKey("emblem_away", ("Filename", "amsn2/themes/default/images/contact_list/away_emblem.png"))
        self.setKey("buddy_brb", ("Filename", "amsn2/themes/default/images/away.png"))
        self.setKey("emblem_brb", ("Filename", "amsn2/themes/default/images/contact_list/away_emblem.png"))
        self.setKey("buddy_idle", ("Filename", "amsn2/themes/default/images/away.png"))
        self.setKey("emblem_idle", ("Filename", "amsn2/themes/default/images/contact_list/away_emblem.png"))
        self.setKey("buddy_lunch", ("Filename", "amsn2/themes/default/images/away.png"))
        self.setKey("emblem_lunch", ("Filename", "amsn2/themes/default/images/contact_list/away_emblem.png"))

        # Just to show you can use an image from the edj file
        self.setKey("buddy_busy", ("EET", ("amsn2/themes/default.edj", "images/0")))
        self.setKey("emblem_busy", ("Filename", "amsn2/themes/default/images/contact_list/busy_emblem.png"))
        self.setKey("buddy_phone", ("EET", ("amsn2/themes/default.edj", "images/0")))
        self.setKey("emblem_phone", ("Filename", "amsn2/themes/default/images/contact_list/busy_emblem.png"))

        self.setKey("buddy_offline", ("Filename", "amsn2/themes/default/images/offline.png"))
        self.setKey("emblem_offline", ("Filename", "amsn2/themes/default/images/contact_list/offline_emblem.png"))
        self.setKey("buddy_hidden", ("Filename", "amsn2/themes/default/images/offline.png"))
        self.setKey("emblem_hidden", ("Filename", "amsn2/themes/default/images/contact_list/offline_emblem.png"))

        self.setKey("default_dp", ("Filename", "amsn2/themes/default/images/contact_list/nopic.png"))



    def getKey(self, key, default=None):
        try:
            return self._dict[key]
        except KeyError:
            return default

    def setKey(self, key, value):
        self._dict[key] = value




class SkinManager(base.SkinManager):
    def __init__(self, core):
        self._core = core
        self.skin = Skin(core, "skins")

    def setSkin(self, name):
        self.skin = Skin(self._core, os.path.join("skins", name))

    def listSkins(self, path):
        pass

########NEW FILE########
__FILENAME__ = splash
from amsn2.gui import base

class aMSNSplashScreen(base.aMSNSplashScreen):

    def __init__(self, amsn_core, parent):
        pass

    def show(self):
        pass

    def hide(self):
        pass

    def setText(self, text):
        pass

    def setImage(self, image):
        pass

########NEW FILE########
__FILENAME__ = window

from constants import *
import ecore
import ecore.evas
import ecore.x
import elementary

from amsn2.gui import base
from amsn2.core.views import MenuView, MenuItemView

class aMSNWindow(elementary.Window, base.aMSNWindow):
    def __init__(self, amsn_core):
        self._amsn_core = amsn_core
        elementary.Window.__init__(self, "aMSN", elementary.ELM_WIN_BASIC)
        self.resize(WIDTH, HEIGHT)
        self.on_key_down_add(self._on_key_down)
        self.fullscreen = False
        self.name_class_set = (WM_NAME, WM_CLASS)
        #self._has_menu = False

        self._bg = elementary.Background(self)
        self.resize_object_add(self._bg)
        self._bg.size_hint_weight_set(1.0, 1.0)
        self._bg.show()

    @property
    def _evas(self):
        return self.evas_get()

    def hide(self):
        pass

    def setTitle(self, text):
        self.title_set(text)

    def setMenu(self, menu):
        pass

    def toggleMenu(self):
        pass

    def _on_key_down(self, obj, event):
        pass


########NEW FILE########
__FILENAME__ = chat_window
# -*- coding: utf-8 -*-
#===================================================
# 
# chat_window.py - This file is part of the amsn2 package
#
# Copyright (C) 2008  Wil Alvarez <wil_alejandro@yahoo.com>
#
# This script is free software; you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free Software 
# Foundation; either version 3 of the License, or (at your option) any later
# version.
#
# This script is distributed in the hope that it will be useful, but WITHOUT 
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or 
# FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public License 
# for more details.
#
# You should have received a copy of the GNU General Public License along with 
# this script (see COPYING); if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
#
#===================================================

import gc
import gtk
import cgi
import time
import pango
from htmltextview import *
from amsn2.gui import base
from amsn2.core.views import ContactView, StringView
import gtk_extras
import papyon
import gobject
import os
from image import Image
import common

class aMSNChatWindow(base.aMSNChatWindow, gtk.Window):
    def __init__(self, amsn_core):
        gtk.Window.__init__(self, gtk.WINDOW_TOPLEVEL)
        self._amsn_core = amsn_core
        self.child = None
        self.showed = False
        self.set_default_size(550, 450)
        self.set_position(gtk.WIN_POS_CENTER)
        self._theme_manager = amsn_core._core._theme_manager

        self.set_title("aMSN - Chatwindow")
        #leave

    def addChatWidget(self, chat_widget):
        print 'addedChatWidget'
        #if self.child is not None: self.remove(self.child)
        #if self.child is not None:
        #    self.show_all()
        #    return
        if self.child is None: self.add(chat_widget)
        self.child = chat_widget

        self.show_all()
        self.child.entry.grab_focus()


class aMSNChatWidget(base.aMSNChatWidget, gtk.VBox):
    def __init__(self, amsn_conversation, parent, contacts_uid):
        gtk.VBox.__init__(self, False, 0)

        self._parent = parent
        self._amsn_conversation = amsn_conversation
        self._amsn_core = amsn_conversation._core
        self._theme_manager = self._amsn_core._theme_manager
        self._contactlist_manager = self._amsn_core._contactlist_manager
        self.padding = 4
        self.lastmsg = ''
        self.last_sender = ''
        self.nickstyle = "color:#555555; margin-left:2px"
        self.msgstyle = "margin-left:15px"
        self.infostyle = "margin-left:2px; font-style:italic; color:#6d6d6d"

        amsncontacts = [self._contactlist_manager.getContact(uid) for uid in contacts_uid]
        cviews = [ContactView(self._amsn_core, c) for c in amsncontacts]
        self.chatheader = aMSNChatHeader(self._theme_manager, cviews)

        # Titlebar
        parent.set_title("aMSN2 - " + str(cviews[0].name.getTag("nickname")))

        # Middle
        self.textview = HtmlTextView()
        tscroll = gtk.ScrolledWindow()
        tscroll.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
        tscroll.set_shadow_type(gtk.SHADOW_ETCHED_IN)
        tscroll.add(self.textview)

        #self.chat_roster = ChatRoster()

        self.middle_box = gtk.HPaned()
        self.middle_box.pack1(tscroll, True, True)

        # Bottom
        self.entry = MessageTextView()

        # Tags for entry
        tag = self.entry.get_buffer().create_tag("bold")
        tag.set_property("weight", pango.WEIGHT_BOLD)
        tag = self.entry.get_buffer().create_tag("italic")
        tag.set_property("style", pango.STYLE_ITALIC)
        tag = self.entry.get_buffer().create_tag("underline")
        tag.set_property("underline", pango.UNDERLINE_SINGLE)
        tag = self.entry.get_buffer().create_tag("strikethrough")
        tag.set_property("strikethrough", True)
        tag = self.entry.get_buffer().create_tag("foreground")
        tag.set_property("foreground_gdk", gtk.gdk.Color(0,0,0))
        tag = self.entry.get_buffer().create_tag("family")
        tag.set_property("family", "MS Sans Serif")

        escroll = gtk.ScrolledWindow()
        escroll.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
        escroll.set_placement(gtk.CORNER_TOP_LEFT)
        escroll.set_shadow_type(gtk.SHADOW_IN)
        escroll.set_size_request(-1, 40)
        escroll.add(self.entry)

        # Register button icons as stock icons
        iconfactory = gtk.IconFactory()
        icons = ['button_smile', 'button_nudge']
        for key in icons:
            type, path = self._theme_manager.get_button(key)
            pixbuf = gtk.gdk.pixbuf_new_from_file(path)
            iconset = gtk.IconSet(pixbuf)
            iconfactory.add(key, iconset)
            iconfactory.add_default()
            del pixbuf
            gc.collect()

        self.button1 = gtk.ToolButton('button_smile')
        self.button2 = gtk.ToolButton('button_nudge')
        self.button_bold = gtk.ToggleToolButton(gtk.STOCK_BOLD)
        self.button_italic = gtk.ToggleToolButton(gtk.STOCK_ITALIC)
        self.button_underline = gtk.ToggleToolButton(gtk.STOCK_UNDERLINE)
        self.button_strikethrough = gtk.ToggleToolButton(gtk.STOCK_STRIKETHROUGH)
        self.button_color = gtk_extras.ColorToolButton()
        self.button_font = gtk_extras.FontToolButton()
        self.button8 = gtk.ToolButton(gtk.STOCK_CLEAR)

        self.button_font.set_show_size(0)
        self.button_font.set_show_style(0)

        bbox = gtk.Toolbar()
        bbox.set_style(gtk.TOOLBAR_ICONS)
        bbox.insert(self.button1, -1)
        bbox.insert(self.button2, -1)
        bbox.insert(gtk.SeparatorToolItem(), -1)
        bbox.insert(self.button_font, -1)
        bbox.insert(self.button_color, -1)
        bbox.insert(self.button_bold, -1)
        bbox.insert(self.button_italic, -1)
        bbox.insert(self.button_underline, -1)
        bbox.insert(self.button_strikethrough, -1)
        bbox.insert(gtk.SeparatorToolItem(), -1)
        bbox.insert(self.button8, -1)

        bottom_box = gtk.VBox(False, 0)
        bottom_box.pack_start(bbox, False, False, 0)
        bottom_box.pack_start(escroll, True,True, 0)

        self.statusbar = gtk.Statusbar()
        self.statusbar.set_has_resize_grip(False)
        self.statusbar.set_spacing(0)

        self.__set_statusbar_text('Welcome to aMSN2')

        vpaned = gtk.VPaned()
        vpaned.pack1(self.middle_box, True, True)
        vpaned.pack2(bottom_box, False, True)

        self.pack_start(self.chatheader, False, False, self.padding)
        self.pack_start(vpaned, True, True, self.padding)
        self.pack_start(self.statusbar, False, False)

        #Connections
        #========
        '''
        self.entrytextview.connect('focus-in-event', self.chatman.setUrgencyHint, False)
        self.entrytextview.get_buffer().connect("changed",self.__updateTextFormat)
        self.textview.connect("button-press-event", self.__rightClick)

        '''
        '''
        self.textview.connect("url-clicked", self.__on_url_clicked)

        self.button1.connect("clicked", self.__create_smiles_window)
        self.button3.connect("clicked",
            self.__on_changed_text_effect, 'bold')
        self.button4.connect("clicked",
            self.__on_changed_text_effect, 'italic')
        self.button5.connect("clicked",
            self.__on_changed_text_effect, 'underline')
        self.button6.connect("clicked",
            self.__on_changed_text_effect, 'strikethrough')
        self.button7.connect("clicked", self.__on_changed_text_color)
        '''
        self.entry.get_buffer().connect("changed", self.__updateTextFormat)
        self.button_bold.connect("toggled", self.__on_changed_text_effect, "bold")
        self.button_italic.connect("toggled", self.__on_changed_text_effect, "italic")
        self.button_underline.connect("toggled", self.__on_changed_text_effect, "underline")
        self.button_strikethrough.connect("toggled", self.__on_changed_text_effect, "strikethrough")
        self.button_color.connect("color_set", self.__on_changed_text_color)
        self.button_font.connect("font_set", self.__on_changed_text_font)
        self.button2.connect("clicked", self.__on_nudge_send)
        self.button8.connect("clicked", self.__on_clear_textview)
        self.entry.connect('mykeypress', self.__on_chat_send)
        self.entry.connect('key-press-event', self.__on_typing_event)

        # timer to display if a user is typing
        self.typingTimer = None

    def __updateTextFormat(self, textbuffer):
        self.reapply_text_effects()
        self.__on_changed_text_color(self.button_color)
        self.__on_changed_text_font(self.button_font)

    def __on_changed_text_effect(self, button, tag_type):
        buffer = self.entry.get_buffer()
        if button.get_active():
            buffer.apply_tag_by_name(tag_type, buffer.get_start_iter(), buffer.get_end_iter())
        else:
            buffer.remove_tag_by_name(tag_type, buffer.get_start_iter(), buffer.get_end_iter())

    def reapply_text_effects(self):
        self.__on_changed_text_effect(self.button_bold, "bold")
        self.__on_changed_text_effect(self.button_italic, "italic")
        self.__on_changed_text_effect(self.button_underline, "underline")
        self.__on_changed_text_effect(self.button_strikethrough, "strikethrough")

    def __on_changed_text_color(self, button):
        buffer = self.entry.get_buffer()
        tag = buffer.get_tag_table().lookup("foreground")
        tag.set_property("foreground_gdk", button.get_color())
        buffer.apply_tag_by_name("foreground", buffer.get_start_iter(), buffer.get_end_iter())

    def __on_changed_text_font(self, button):
        buffer = self.entry.get_buffer()
        font_name = self.button_font.get_font_name()
        font_family = pango.FontDescription(font_name).get_family()
        tag = buffer.get_tag_table().lookup("family")
        tag.set_property("family", font_family)
        buffer.apply_tag_by_name("family", buffer.get_start_iter(), buffer.get_end_iter())

    def __clean_string(self, str):
        return cgi.escape(str)

    def __on_chat_send(self, entry, event_keyval, event_keymod):
        if (event_keyval == gtk.keysyms.Return):
            buffer = entry.get_buffer()
            start, end = buffer.get_bounds()
            msg = buffer.get_text(start, end)
            entry.clear()
            entry.grab_focus()
            if (msg == ''): return False

            color = self.button_color.get_color()
            hex8 = "%.2x%.2x%.2x" % ((color.red/0x101), (color.green/0x101), (color.blue/0x101))
            style = papyon.TextFormat.NO_EFFECT
            if self.button_bold.get_active(): style |= papyon.TextFormat.BOLD
            if self.button_italic.get_active():  style |= papyon.TextFormat.ITALIC
            if self.button_underline.get_active(): style |= papyon.TextFormat.UNDERLINE
            if self.button_strikethrough.get_active(): style |= papyon.TextFormat.STRIKETHROUGH
            font_name = self.button_font.get_font_name()
            font_family = pango.FontDescription(font_name).get_family()
            format = papyon.TextFormat(font=font_family, color=hex8, style=style)
            strv = StringView()
            strv.appendText(msg)
            self._amsn_conversation.sendMessage(strv, format)

        elif event_keyval == gtk.keysyms.Escape:
            self._parent.destroy()

    def __on_clear_textview(self, widget):
        buffer = self.textview.get_buffer()
        start = buffer.get_start_iter()
        end = buffer.get_end_iter()
        buffer.delete(start, end)

    def __on_typing_event(self, widget, event):
        self._amsn_conversation.sendTypingNotification()

    def __on_nudge_send(self, widget):
        self.__print_info('Nudge sent')
        self._amsn_conversation.sendNudge()

    def __print_chat(self, nick, msg, sender):
        html = '<div>'
        # TODO: If we have the same nick as our chat buddy, this doesn't work
        if (self.last_sender != sender):
            html += '<span style="%s">%s</span><br/>' % (self.nickstyle,
                nick)
        html += '<span style="%s">[%s] %s</span></div>' % (self.msgstyle,
            time.strftime('%X'), msg)

        self.textview.display_html(html)
        self.textview.scroll_to_bottom()

    def __print_info(self, msg):
        html = '<div><span style="%s">%s</span></div>' % (self.infostyle, msg)
        self.textview.display_html(html)
        self.textview.scroll_to_bottom()

    def __set_statusbar_text(self, msg):
        context = self.statusbar.get_context_id('msg')
        self.statusbar.pop(context)
        self.statusbar.push(context, msg)

    def __typingStopped(self):
        self.__set_statusbar_text("")
        return False # To stop gobject timer

    def onMessageReceived(self, messageview, formatting=None):
        text = messageview.toStringView().toHtmlString()
        text = self.__clean_string(text)
        nick, msg = text.split('\n', 1)
        nick = str(nick.replace('\n', '<br/>'))
        msg = str(msg.replace('\n', '<br/>'))
        sender = str(messageview.sender)

        # peacey: Check formatting of styles and perform the required changes
        if formatting:
            fmsg = '''<span style="'''
            if formatting.font:
                fmsg += "font-family: %s;" % formatting.font
            if formatting.color:
                fmsg += "color: %s;" % ("#"+formatting.color)
            if formatting.style & papyon.TextFormat.BOLD == papyon.TextFormat.BOLD:
                fmsg += "font-weight: bold;"
            if formatting.style & papyon.TextFormat.ITALIC == papyon.TextFormat.ITALIC:
                fmsg += "font-style: italic;"
            if formatting.style & papyon.TextFormat.UNDERLINE == papyon.TextFormat.UNDERLINE:
                fmsg += "text-decoration: underline;"
            if formatting.style & papyon.TextFormat.STRIKETHROUGH == papyon.TextFormat.STRIKETHROUGH:
                fmsg += "text-decoration: line-through;"
            if formatting.right_alignment:
                fmsg += "text-align: right;"
            fmsg = fmsg.rstrip(";")
            fmsg += '''">'''
            fmsg += msg
            fmsg += "</span>"
        else:
            fmsg = msg

        self.__print_chat(nick, fmsg, sender)

        self.last_sender = sender
        self.__typingStopped()

    def onUserJoined(self, contact):
        print "%s joined the conversation" % (contact,)
        self.__print_info("%s joined the conversation" % (contact,))
        self.__set_statusbar_text("%s joined the conversation" % (contact,))

    def onUserLeft(self, contact):
        print "%s left the conversation" % (contact,)
        self.__print_info("%s left the conversation" % (contact,))
        self.__set_statusbar_text("%s left the conversation" % (contact,))
        self.__typingStopped()

    def onUserTyping(self, contact):
        """ Set a timer for 6 sec every time a user types. If the user
        continues typing during these 10 sec, kill the timer and start over with
        10 sec. If the user stops typing; call __typingStopped """

        print "%s is typing" % (contact,)
        self.__set_statusbar_text("%s is typing" % (contact,))
        if self.typingTimer != None:
            gobject.source_remove(self.typingTimer)
            self.typingTimer = None
        self.typingTimer = gobject.timeout_add(6000, self.__typingStopped)

    def nudge(self):
        self.__print_info('Nudge received')


class aMSNChatHeader(gtk.EventBox):
    def __init__(self, theme_manager, cviews=None):
        gtk.EventBox.__init__(self)

        self.buddy_icon = gtk.Image()
        self.title = gtk.Label()
        self.dp = gtk.Image()
        self.title_color = gtk.gdk.color_parse('#dadada')
        self.psm_color = '#999999'
        self.theme_manager = theme_manager
        self.cviews = cviews

        self.title.set_use_markup(True)
        self.title.set_justify(gtk.JUSTIFY_LEFT)
        self.title.set_ellipsize(pango.ELLIPSIZE_END)
        self.title.set_alignment(xalign=0, yalign=0.5)
        self.title.set_padding(xpad=2, ypad=2)

        # Load default dp's size from common
        self.dp.set_size_request(common.DP_MINI[0],
                                 common.DP_MINI[1])

        hbox = gtk.HBox(False,0)
        hbox.pack_start(self.buddy_icon, False,False,0)
        hbox.pack_start(self.title, True,True,0)
        hbox.pack_start(self.dp, False,False,0)

        self.modify_bg(gtk.STATE_NORMAL, self.title_color)
        self.add(hbox)

        self.connect("button-release-event", self.__dpClicked)
        self.update(cviews)

    def update(self, cviews):
        """
        @param cviews: list contacts participating in the conversation.
        @type cviews: list of ContactView's
        """
        #FIXME: Show all users in a multiconversation
        nickname = cviews[0].name.getTag("nickname")
        psm = cviews[0].name.getTag("psm")
        status = cviews[0].name.getTag("status")

        #FIXME: Which user do we show in a multiconversation?
        img = Image(self.theme_manager, cviews[0].dp)
        size = self.dp.get_size_request()
        self.dp.set_from_pixbuf(img.to_pixbuf(size[0],size[1]))

        title = '<span size="large"><b>%s</b></span>' % (nickname, )
        title += '<span size="medium">  %s</span>' % (status, )

        if(psm != ''):
            title += '\n<span size="small" foreground="%s">%s</span>' % (
            self.psm_color, psm)

        self.title.set_markup(title)

    def __dpClicked(self, source, event):
        # Called when the display picture of the other person is clicked
        if source.dp.get_size_request() == common.DP_MINI:
            source.dp.set_size_request(common.DP_LARGE[0],common.DP_LARGE[1])
            self.title.set_alignment(xalign = 0, yalign = 0.09)
        else:
            source.dp.set_size_request(common.DP_MINI[0],common.DP_MINI[1])
            self.title.set_alignment(xalign = 0, yalign = 0.5)

        self.update(self.cviews)

########NEW FILE########
__FILENAME__ = choosers

from amsn2.gui import base
import image
import gtk

class aMSNFileChooserWindow(base.aMSNFileChooserWindow, gtk.FileChooserDialog):
    def __init__(self, filters, directory, callback):
        gtk.FileChooserDialog.__init__(self, title='aMSN2 -Choose a file',
                                    action=gtk.FILE_CHOOSER_ACTION_OPEN,
                                    buttons=(gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL,
                                             gtk.STOCK_OPEN, gtk.RESPONSE_OK))

        if filters:
            for name in filters.keys():
                filefilter = gtk.FileFilter()
                filefilter.set_name(name)
                for ext in filters[name]:
                    filefilter.add_pattern(ext)
                self.add_filter(filefilter)

        toggle = gtk.CheckButton("Show hidden files")
        toggle.show()
        toggle.connect('toggled', lambda toggle: self.set_show_hidden(toggle.get_active()))
        self.set_extra_widget(toggle)

        self.preview = gtk.Image()
        self.set_preview_widget(self.preview)
        self.set_use_preview_label(False)

        self.callback = callback
        #self.set_size_request(500, 400)
        if directory:
            self.set_current_folder_uri(directory)

        self.connect('selection-changed', self.activatePreview)
        self.connect('response', self.onResponse)

        self.run()

    def activatePreview(self, chooser):
        filename = self.get_preview_filename()
        if filename:
            info = gtk.gdk.pixbuf_get_file_info(filename)
            if info:
                pixbuf = gtk.gdk.pixbuf_new_from_file_at_size(filename, -1, 96)
                self.preview.set_from_pixbuf(pixbuf)
                self.set_preview_widget_active(True)
                return

        self.set_preview_widget_active(False)

    def onResponse(self, chooser, id):
        if id ==gtk.RESPONSE_OK:
            self.callback(self.get_filename())
        elif id == gtk.RESPONSE_CANCEL:
            pass
        self.destroy()
        

class aMSNDPChooserWindow(base.aMSNDPChooserWindow, gtk.Window):
    def __init__(self, callback, backend_manager):
        gtk.Window.__init__(self, gtk.WINDOW_TOPLEVEL)
        self.showed = False
        self.set_default_size(550, 450)
        self.set_position(gtk.WIN_POS_CENTER)
        self.set_title("aMSN - Choose a Display Picture")
        self.callback = callback
        self.view = None
        self.child = None

        actions = (('Open file', self._open_file), )
        default_dps = []
        self._setup_boxes(actions)
        for dp in default_dps:
            self._update_dp_list(default_dps)

        self.show()
        self.show_all()

    def _open_file(self):
        filters = {'Image files':("*.png", "*.jpeg", "*.jpg", "*.gif", "*.bmp"),
                   'All files':('*.*')}
        aMSNFileChooserWindow(filters, None, self._update_dp_list)

    def _setup_boxes(self, actions):
        tscroll = gtk.ScrolledWindow()
        tscroll.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
        tscroll.set_shadow_type(gtk.SHADOW_ETCHED_IN)
        self.iconview = gtk.IconView()
        self._model = gtk.ListStore(gtk.gdk.Pixbuf, object)
        self.iconview.set_model(self._model)
        self.iconview.set_pixbuf_column(0)
        self.iconview.set_selection_mode(gtk.SELECTION_SINGLE)
        self.iconview.connect("item-activated", self.__on_dp_dblclick)
        self.iconview.connect("button-press-event", self.__on_dp_click)
        tscroll.add(self.iconview)
        dpsbox = gtk.VBox()
        dpsbox.pack_start(tscroll)

        buttonbox = gtk.VBox(False)
        buttonbox.set_size_request(100, 450)
        currentdp = gtk.Image()
        buttonbox.pack_start(currentdp, False)
        cancel_button = gtk.Button('Cancel', gtk.STOCK_CANCEL)
        cancel_button.connect('clicked', lambda button: self.destroy())
        ok_button = gtk.Button('Ok', gtk.STOCK_OK)
        ok_button.connect('clicked', self._dp_chosen)
        buttonbox.pack_start(ok_button, False)
        buttonbox.pack_start(cancel_button, False)
        for name, cb in actions:
            button = gtk.Button(name)
            def callback(cb):
                return lambda button: cb()
            button.connect('clicked', callback(cb))
            buttonbox.pack_start(button, False)

        hbox = gtk.HBox()
        hbox.pack_start(dpsbox)
        hbox.pack_start(buttonbox, False)
        self.add(hbox)

    def _dp_chosen(self, button):
        self.callback(self.view)
        self.destroy()

    def __on_dp_dblclick(self, widget, path):
        if path:
            iter = self._model.get_iter(path)
            self.view = self._model.get_value(iter, 1)
            self._dp_chosen(None)
            return True

        else:
            return False

    def __on_dp_click(self, source, event):
        if event.type == gtk.gdk.BUTTON_PRESS and event.button == 1:
            treepath = self.iconview.get_path_at_pos(int(event.x), int(event.y))

            if treepath:
                iter = self._model.get_iter(treepath)
                self.view = self._model.get_value(iter, 1)

            # Let the double click callback be called
            return False
        else:
            return False

    def _update_dp_list(self, dp_path):
        im = gtk.Image()
        try:
            im.set_from_file(dp_path)
        except:
            return
        self._model.prepend((gtk.gdk.pixbuf_new_from_file_at_size(dp_path, 96, 96), dp_path))
        path = self._model.get_path(self._model.get_iter_first())
        self.iconview.select_path(path)
        iter = self._model.get_iter(path)
        self.view = self._model.get_value(iter, 1)


########NEW FILE########
__FILENAME__ = common

from amsn2.core.views import StringView, MenuItemView

import gobject
import pango
import gtk

GUI_FONT = pango.FontDescription('normal 8')

# Sizes of the contacts' display images in different states
DP_MINI = (50, 50)
DP_LARGE = (100, 100)

def stringvToHtml(stringv):
    out = ''
    for x in stringv._elements:
        if x.getType() == StringView.TEXT_ELEMENT:
            out += x.getValue()
        elif x.getType() == StringView.ITALIC_ELEMENT:
            if x.getValue():
                out += '<i>'
            else:
                out += '</i>'
    return out

def escape_pango(str):
    str = gobject.markup_escape_text(str)
    str = str.replace('\n',' ')
    return str

def createMenuItemsFromView(menu, items):
    # TODO: images & radio groups, for now only basic representation
    for item in items:
        if item.type is MenuItemView.COMMAND:
            it = gtk.MenuItem(item.label)
            it.connect("activate", lambda i, item: item.command(), item )
            it.show()
            menu.append(it)
        elif item.type is MenuItemView.CASCADE_MENU:
            men = gtk.Menu()
            it = gtk.MenuItem(item.label)
            createMenuItemsFromView(men, item.items)
            it.set_submenu(men)
            it.show()
            menu.append(it)
        elif item.type is MenuItemView.SEPARATOR:
            it = gtk.SeperatorMenuItem()
            it.show()
            menu.append(it)
        elif item.type is MenuItemView.CHECKBUTTON:
            it = gtk.CheckMenuItem(item.label)
            if item.checkbox:
                it.set_active()
            it.show()
            menu.append(it)
        elif item.type is MenuItemView.RADIOBUTTON:
            it = gtk.RadioMenuItem(item.label)
            it.show()
            menu.append(it)
        elif item.type is MenuItemView.RADIOBUTTONGROUP:
            pass


########NEW FILE########
__FILENAME__ = contact_list
# -*- coding: utf-8 -*-
#===================================================
#
# contact_list.py - This file is part of the amsn2 package
#
# Copyright (C) 2008  Wil Alvarez <wil_alejandro@yahoo.com>
#
# This script is free software; you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free Software
# Foundation; either version 3 of the License, or (at your option) any later
# version.
#
# This script is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
# FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public License
# for more details.
#
# You should have received a copy of the GNU General Public License along with
# this script (see COPYING); if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
#
#===================================================

import gc
import os
import gtk
import pango
import gobject

#import papyon
from image import *
from amsn2.core.views import StringView
from amsn2.core.views import GroupView
from amsn2.core.views import ContactView
from amsn2.core.views import ImageView
from amsn2.core.views import PersonalInfoView
from amsn2.gui import base

import common

class aMSNContactListWindow(base.aMSNContactListWindow, gtk.VBox):
    '''GTK contactlist'''
    def __init__(self, amsn_core, parent):
        '''Constructor'''
        gtk.VBox.__init__(self)
        base.aMSNContactListWindow.__init__(self, amsn_core, parent)

        self._amsn_core = amsn_core
        self._main_win = parent
        self._skin = amsn_core._skin_manager.skin
        self._theme_manager = self._amsn_core._theme_manager
        self._myview = amsn_core._personalinfo_manager._personalinfoview

        self._clwidget = aMSNContactListWidget(amsn_core, self)

        self.__create_controls()
        self.__create_box()

        self._main_win.set_view(self)

        self.show_all()
        self.__setup_window()

    def __create_controls(self):
        ###self.psmlabel.modify_font(common.GUI_FONT)
        # Main Controls
        self.display = gtk.Image()
        self.display.set_size_request(64,64)
        
        self.btnDisplay = gtk.Button()
        self.btnDisplay.set_relief(gtk.RELIEF_NONE)
        self.btnDisplay.add(self.display)
        self.btnDisplay.set_alignment(0,0)
        self.btnDisplay.connect("clicked", self.__onDisplayClicked)
        
        self.nicklabel = gtk.Label()
        self.nicklabel.set_alignment(0, 0)
        self.nicklabel.set_use_markup(True)
        self.nicklabel.set_ellipsize(pango.ELLIPSIZE_END)
        self.nicklabel.set_markup('Loading...')

        self.btnNickname = gtk.Button()
        self.btnNickname.set_relief(gtk.RELIEF_NONE)
        self.btnNickname.add(self.nicklabel)
        self.btnNickname.set_alignment(0,0)
        self.btnNickname.connect("clicked",self.__on_btnNicknameClicked)

        self.psmlabel = gtk.Label()
        self.psmlabel.set_alignment(0, 0)
        self.psmlabel.set_use_markup(True)
        self.psmlabel.set_ellipsize(pango.ELLIPSIZE_END)
        self.psmlabel.set_markup('<i>&lt;Personal message&gt;</i>')

        self.btnPsm = gtk.Button()
        self.btnPsm.add(self.psmlabel)
        self.btnPsm.set_relief(gtk.RELIEF_NONE)
        self.btnPsm.set_alignment(0,0)
        self.btnPsm.connect("clicked", self.__on_btnPsmClicked)

        # status list
        self.status_values = {}
        status_list = gtk.ListStore(gtk.gdk.Pixbuf, str, str)
        for key in self._amsn_core.p2s:
            name = self._amsn_core.p2s[key]
            self.status_values[name] = self._amsn_core.p2s.values().index(name)
            _, path = self._theme_manager.get_statusicon("buddy_%s" % name)
            #if (name == 'offline'): continue
            #iv = ImageView("Skin", "buddy_%s" % name)
            #img = Image(self._skin, iv)
            #icon = img.to_pixbuf(28)
            icon = gtk.gdk.pixbuf_new_from_file(path)
            status_list.append([icon, name, key])
            del icon
            gc.collect()

        iconCell = gtk.CellRendererPixbuf()
        iconCell.set_property('xalign', 0.0)
        txtCell = gtk.CellRendererText()
        txtCell.set_property('xalign', 0.0)

        self.status = gtk.ComboBox()
        self.status.set_model(status_list)
        self.status.set_active(0)
        self.status.pack_start(iconCell, False)
        self.status.pack_start(txtCell, False)
        self.status.add_attribute(iconCell, 'pixbuf',0)
        self.status.add_attribute(txtCell, 'markup',1)
        self.status.connect('changed', self.onStatusChanged)

    def __create_box(self):
        frameDisplay = gtk.Frame()
        frameDisplay.add(self.btnDisplay)
        self.evdisplay = gtk.EventBox()
        self.evdisplay.add(frameDisplay)

        headerLeft = gtk.VBox(False, 0)
        headerLeft.pack_start(self.evdisplay, True, False)

        # Header Right
        boxNick = gtk.HBox(False, 0)
        boxNick.pack_start(self.btnNickname, True, True)

        boxPsm = gtk.HBox(False, 0)
        boxPsm.pack_start(self.btnPsm, True, True)

        headerRight = gtk.VBox(False, 0)
        headerRight.pack_start(boxNick, False, False)
        headerRight.pack_start(boxPsm, False, False)

        # Header pack
        header = gtk.HBox(False, 1)
        header.pack_start(headerLeft, False, False, 0)
        header.pack_start(headerRight, True, True, 0)

        scrollwindow = gtk.ScrolledWindow()
        scrollwindow.set_shadow_type(gtk.SHADOW_ETCHED_IN)
        scrollwindow.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)	
        scrollwindow.add(self._clwidget)

        bottom = gtk.HBox(False, 0)
        bottom.pack_start(self.status, True, True, 0)

        self.pack_start(header, False, False, 2)
        self.pack_start(scrollwindow, True, True, 2)
        self.pack_start(bottom, False, False, 2)

    def __setup_window(self):
        _, filename = self._theme_manager.get_dp('dp_nopic')
        pixbuf = gtk.gdk.pixbuf_new_from_file_at_size(filename, 64, 64)
        self.display.set_from_pixbuf(pixbuf)
        del pixbuf
        gc.collect()

    def __on_btnNicknameClicked(self, source):
        self.__switchToInput(source)

    def __on_btnPsmClicked(self, source):
        self.__switchToInput(source)
        
    def __switchToInput(self, source):
        """ Switches the nick and psm buttons into a text area for editing them."""
        source.remove(source.get_child())
        entry = gtk.Entry()

        if source is self.btnNickname:
            entry.set_text(str(self._myview.nick))
        elif source is self.btnPsm:
            entry.set_text(str(self._myview.psm))

        source.add(entry)
        entry.show()
        entry.grab_focus()
        source.set_relief(gtk.RELIEF_NORMAL) # Add cool elevated effect
        entry.connect("activate", self.__switchFromInput, True)
        entry.connect("key-press-event", self.__handleInput)
        self.focusOutId = entry.connect("focus-out-event", self.__handleInput)
        
    def __handleInput(self, source, event):
        """ Handle various inputs from the nicknameEntry-box """
        if(event.type == gtk.gdk.FOCUS_CHANGE): #user clicked outside textfield
            self.__switchFromInput(source, True)
        elif (event.type == gtk.gdk.KEY_PRESS): #user wrote something, esc perhaps?
            if event.keyval == gtk.keysyms.Escape:
                self.__switchFromInput(source, False)

    def __switchFromInput(self, source, isNew):
        """ When in the editing state of nickname and psm, change back
        to the uneditable label state.
        """
        if(isNew):
            if source is self.btnNickname.get_child():
                newText = source.get_text()
                strv = StringView()
                strv.appendText(newText)
                self._myview.nick = strv
            elif source is self.btnPsm.get_child():
                newText = source.get_text()
                strv = StringView()
                strv.appendText(newText)
                self._myview.psm = strv
        else:
            if source is self.btnNickname.get_child():  # User discards input
                newText = self.nicklabel.get_text()     # Old nickname
            elif source is self.btnPsm.get_child():
                newText = self.psmlabel.get_text()

        parentWidget    = source.get_parent()
        currWidget      = parentWidget.get_child()
        currWidget.disconnect(self.focusOutId)          # Else we trigger focus-out-event; segfault.

        parentWidget.remove(currWidget)
        entry = gtk.Label()
        entry.set_markup(newText)

        parentWidget.add(entry)
        entry.show()
        parentWidget.set_relief(gtk.RELIEF_NONE)        # remove cool elevated effect
        
    def __onDisplayClicked(self, source):
        self._amsn_core.changeDP()

    def show(self):
        pass

    def hide(self):
        pass

    def setTitle(self, text):
        self._main_win.set_title(text)

    def setMenu(self, menu):
        """ This will allow the core to change the current window's main menu
        @type menu: MenuView
        """
        pass

    def myInfoUpdated(self, view):
        """ This will allow the core to change pieces of information about
        ourself, such as DP, nick, psm, the current media being played,...
        @type view: PersonalInfoView
        @param view: ourself (contains DP, nick, psm, currentMedia,...)
        """
        # TODO: image, ...
        self._myview = view
        nk = view.nick
        self.nicklabel.set_markup(str(nk))
        psm = view.psm
        cm = view.current_media
        message = str(psm)+' '+str(cm)
        self.psmlabel.set_markup('<i>'+message+'</i>')
        self.status.set_active(self.status_values[view.presence])
        imview = self._myview.dp
        if len(imview.imgs) > 0:
            pixbuf = gtk.gdk.pixbuf_new_from_file_at_size(imview.imgs[0][1], 64, 64)
            self.display.set_from_pixbuf(pixbuf)

    def onStatusChanged(self, combobox):
        status = combobox.get_active()
        for key in self.status_values:
            if self.status_values[key] == status:
                break
        # FIXME: changing status to 'offline' will disconnect, so return to login window
        if key != self._myview.presence:
            self._myview.presence = key

class aMSNContactListWidget(base.aMSNContactListWidget, gtk.TreeView):
    def __init__(self, amsn_core, parent):
        """Constructor"""
        base.aMSNContactListWidget.__init__(self, amsn_core, parent)
        gtk.TreeView.__init__(self)

        self._amsn_core = amsn_core
        self._cwin = parent
        self.groups = []
        self.contacts = {}

        nick = gtk.CellRendererText()
        nick.set_property('ellipsize-set',True)
        nick.set_property('ellipsize', pango.ELLIPSIZE_END)
        pix = gtk.CellRendererPixbuf()

        column = gtk.TreeViewColumn()
        column.set_expand(True)
        column.set_alignment(0.0)
        column.pack_start(pix, False)
        column.pack_start(nick, True)

        #column.add_attribute(pix, 'pixbuf', 0)
        column.set_attributes(pix, pixbuf=0, visible=4)
        column.add_attribute(nick, 'markup', 2)

        exp_column = gtk.TreeViewColumn()
        exp_column.set_max_width(16)

        self.append_column(exp_column)
        self.append_column(column)
        self.set_expander_column(exp_column)

        self.set_search_column(2)
        self.set_headers_visible(False)
        self.set_level_indentation(0)

        # the image (None for groups) the object (group or contact) and
        # the string to display
        self._model = gtk.TreeStore(gtk.gdk.Pixbuf, object, str, str, bool)
        self.model = self._model.filter_new(root=None)
        #self.model.set_visible_func(self._visible_func)

        self.set_model(self.model)
        self.connect("row-activated", self.__on_contact_dblclick)
        self.connect("button-press-event", self.__on_button_click)

    def __on_button_click(self, source, event):
        # Detect a single right-click
        if event.type == gtk.gdk.BUTTON_PRESS and event.button == 3:
            treepath = self.get_path_at_pos(event.x, event.y)

            if treepath:
                path, tree_column, x, y = treepath
                iter = self._model.get_iter(path)
                view = self._model.get_value(iter, 1)

                if isinstance(view, ContactView) or isinstance(view, GroupView):
                    self.grab_focus()
                    self.set_cursor(path, tree_column, 0)
                    menu = gtk.Menu()
                    common.createMenuItemsFromView(menu,
                                view.on_right_click_popup_menu.items)
                    menu.popup(None, None, None, event.button, event.time)

            return True

        # Detect a single left-click, but it is called even when a double-click occours,
        # so should we detect them or is there a simpler way?
        #elif event.type == gtk.gdk.BUTTON_PRESS and event.button == 1:
        #    return False

        else:
            return False

    def __on_contact_dblclick(self, widget, path, column):
        model, row = widget.get_selection().get_selected()
        if (row is None): return False
        if not (model.get_value(row, 4)): return False

        contactview = model.get_value(row, 1)
        contactview.on_click(contactview.uid)

    def __search_by_id(self, id):
        parent = self._model.get_iter_first()

        while (parent is not None):
            obj = self._model.get_value(parent, 3)
            if (obj == id): return parent
            child = self._model.iter_children(parent)
            while (child is not None):
                cobj = self._model.get_value(child, 3)
                if (cobj == id): return child
                child = self._model.iter_next(child)
            parent = self._model.iter_next(parent)

        return None

    def show(self):
        pass

    def hide(self):
        pass

    def contactListUpdated(self, clview):
        guids = self.groups
        self.groups = []

        # New groups
        for gid in clview.group_ids:
            if (gid == 0): gid = '0'
            if gid not in guids:
                self.groups.append(gid)
                self._model.append(None, [None, None, gid, gid, False])

        # Remove unused groups
        for gid in guids:
            if gid not in self.groups:
                giter = self.__search_by_id(gid)
                self._model.remove(giter)
                self.groups.remove(gid)

    def groupUpdated(self, groupview):
        if (groupview.uid == 0): groupview.uid = '0'
        if groupview.uid not in self.groups: return

        giter = self.__search_by_id(groupview.uid)
        self._model.set_value(giter, 1, groupview)
        self._model.set_value(giter, 2, '<b>%s</b>' % common.escape_pango(
            str(groupview.name)))

        try:
            cuids = self.contacts[groupview.uid]
        except:
            cuids = []
        self.contacts[groupview.uid] = groupview.contact_ids.copy()

        for cid in groupview.contact_ids:
            if cid not in cuids:
                giter = self.__search_by_id(groupview.uid)
                self._model.append(giter, [None, None, cid, cid, True])

        # Remove unused contacts
        for cid in cuids:
            if cid not in self.contacts[groupview.uid]:
                citer = self.__search_by_id(cid)
                self._model.remove(citer)

    def contactUpdated(self, contactview):
        """
        @type contactview: ContactView
        """

        citer = self.__search_by_id(contactview.uid)
        if citer is None: return

        img = Image(self._cwin._theme_manager, contactview.dp)
        #img = Image(self._cwin._theme_manager, contactview.icon)
        dp = img.to_pixbuf(28, 28)

        self._model.set_value(citer, 0, dp)
        self._model.set_value(citer, 1, contactview)
        self._model.set_value(citer, 2, common.escape_pango(
            str(contactview.name)))
        del dp
        gc.collect()



########NEW FILE########
__FILENAME__ = gtk_
from main_loop import *
from main import *
from contact_list import *
from login import *
from image import *
from splash import *
from skins import *
from chat_window import *
from utility import *
from choosers import *


########NEW FILE########
__FILENAME__ = gtk_extras
# Additional helper classes
# ColorToolButton class copied from the sugar project under the GNU LGPL license
# http://sugarlabs.org

import gtk
import gobject

# This not ideal. It would be better to subclass gtk.ToolButton, however
# the python bindings do not seem to be powerfull enough for that.
# (As we need to change a variable in the class structure.)
class ColorToolButton(gtk.ToolItem):
    __gtype_name__ = 'ColorToolButton'
    __gsignals__ = { 'color-set' : (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE,  tuple())}

    def __init__(self, icon_name='color-preview', **kwargs):
        self._accelerator = None
        self._tooltip = None
        #self._palette_invoker = ToolInvoker()
        self._palette = None
        gobject.GObject.__init__(self, **kwargs)
        # The gtk.ToolButton has already added a normal button.
        # Replace it with a ColorButton
        color_button = gtk.ColorButton()
        self.add(color_button)
        # The following is so that the behaviour on the toolbar is correct.
        color_button.set_relief(gtk.RELIEF_NONE)
        color_button.icon_size = gtk.ICON_SIZE_LARGE_TOOLBAR
        #self._palette_invoker.attach_tool(self)
        # This widget just proxies the following properties to the colorbutton
        color_button.connect('notify::color', self.__notify_change)
        color_button.connect('notify::icon-name', self.__notify_change)
        color_button.connect('notify::icon-size', self.__notify_change)
        color_button.connect('notify::title', self.__notify_change)
        color_button.connect('color-set', self.__color_set_cb)
        color_button.connect('can-activate-accel',  self.__button_can_activate_accel_cb)

    def __button_can_activate_accel_cb(self, button, signal_id):
        # Accept activation via accelerators regardless of this widget's state
        return True

    def set_accelerator(self, accelerator):
        self._accelerator = accelerator
        setup_accelerator(self)

    def get_accelerator(self):
        return self._accelerator

    accelerator = gobject.property(type=str, setter=set_accelerator,  getter=get_accelerator)

    def create_palette(self):
        self._palette = self.get_child().create_palette()
        return self._palette

    #def get_palette_invoker(self):
     #   return self._palette_invoker

    #def set_palette_invoker(self, palette_invoker):
      #  self._palette_invoker.detach()
     #   self._palette_invoker = palette_invoker
    #palette_invoker = gobject.property(  type=object, setter=set_palette_invoker, getter=get_palette_invoker)

    def set_color(self, color):
        self.get_child().props.color = color

    def get_color(self):
        return self.get_child().props.color

    color = gobject.property(type=object, getter=get_color, setter=set_color)

    def set_icon_name(self, icon_name):
        self.get_child().props.icon_name = icon_name

    def get_icon_name(self):
        return self.get_child().props.icon_name

    icon_name = gobject.property(type=str,  getter=get_icon_name, setter=set_icon_name)

    def set_icon_size(self, icon_size):
        self.get_child().props.icon_size = icon_size

    def get_icon_size(self):
        return self.get_child().props.icon_size

    icon_size = gobject.property(type=int,  getter=get_icon_size, setter=set_icon_size)

    def set_title(self, title):
        self.get_child().props.title = title

    def get_title(self):
        return self.get_child().props.title

    title = gobject.property(type=str, getter=get_title, setter=set_title)

    def do_expose_event(self, event):
        child = self.get_child()
        allocation = self.get_allocation()
        if self._palette and self._palette.is_up():
            invoker = self._palette.props.invoker
            invoker.draw_rectangle(event, self._palette)
        elif child.state == gtk.STATE_PRELIGHT:
            child.style.paint_box(event.window, gtk.STATE_PRELIGHT,  gtk.SHADOW_NONE, event.area,  child, 'toolbutton-prelight',  allocation.x, allocation.y,  allocation.width, allocation.height)

        gtk.ToolButton.do_expose_event(self, event)

    def __notify_change(self, widget, pspec):
        self.notify(pspec.name)

    def __color_set_cb(self, widget):
        self.emit('color-set')

class FontToolButton(gtk.ToolItem):
    __gtype_name__ = 'FontToolButton'
    __gsignals__ = { 'font-set' : (gobject.SIGNAL_RUN_FIRST, gobject.TYPE_NONE,  tuple())}

    def __init__(self, icon_name='font-preview', **kwargs):
        self._accelerator = None
        self._tooltip = None
        #self._palette_invoker = ToolInvoker()
        self._palette = None
        gobject.GObject.__init__(self, **kwargs)
        # The gtk.ToolButton has already added a normal button.
        # Replace it with a ColorButton
        font_button = gtk.FontButton()
        self.add(font_button)
        # The following is so that the behaviour on the toolbar is correct.
        font_button.set_relief(gtk.RELIEF_NONE)
        font_button.icon_size = gtk.ICON_SIZE_LARGE_TOOLBAR
        #self._palette_invoker.attach_tool(self)
        # This widget just proxies the following properties to the colorbutton
        font_button.connect('notify::font-name', self.__notify_change)
        font_button.connect('notify::show-style', self.__notify_change)
        font_button.connect('notify::show-size', self.__notify_change)
        font_button.connect('notify::icon-name', self.__notify_change)
        font_button.connect('notify::icon-size', self.__notify_change)
        font_button.connect('notify::title', self.__notify_change)
        font_button.connect('font-set', self.__font_set_cb)
        font_button.connect('can-activate-accel',  self.__button_can_activate_accel_cb)

    def __button_can_activate_accel_cb(self, button, signal_id):
        # Accept activation via accelerators regardless of this widget's state
        return True

    def set_accelerator(self, accelerator):
        self._accelerator = accelerator
        setup_accelerator(self)

    def get_accelerator(self):
        return self._accelerator

    accelerator = gobject.property(type=str, setter=set_accelerator,  getter=get_accelerator)

    def create_palette(self):
        self._palette = self.get_child().create_palette()
        return self._palette

    def set_font_name(self, font_name):
        self.get_child().props.font_name = font_name

    def get_font_name(self):
        return self.get_child().props.font_name

    font_name = gobject.property(type=object, getter=get_font_name, setter=set_font_name)

    def set_show_size(self, show_size):
        self.get_child().props.show_size = show_size

    def get_show_size(self):
        return self.get_child().props.show_size

    show_size = gobject.property(type=object, getter=get_show_size, setter=set_show_size)

    def set_show_style(self, show_style):
        self.get_child().props.show_style = show_style

    def get_show_style(self):
        return self.get_child().props.show_style

    show_style = gobject.property(type=object, getter=get_show_style, setter=set_show_style)


    def set_icon_name(self, icon_name):
        self.get_child().props.icon_name = icon_name

    def get_icon_name(self):
        return self.get_child().props.icon_name

    icon_name = gobject.property(type=str,  getter=get_icon_name, setter=set_icon_name)

    def set_icon_size(self, icon_size):
        self.get_child().props.icon_size = icon_size

    def get_icon_size(self):
        return self.get_child().props.icon_size

    icon_size = gobject.property(type=int,  getter=get_icon_size, setter=set_icon_size)

    def set_title(self, title):
        self.get_child().props.title = title

    def get_title(self):
        return self.get_child().props.title

    title = gobject.property(type=str, getter=get_title, setter=set_title)

    def do_expose_event(self, event):
        child = self.get_child()
        allocation = self.get_allocation()
        if self._palette and self._palette.is_up():
            invoker = self._palette.props.invoker
            invoker.draw_rectangle(event, self._palette)
        elif child.state == gtk.STATE_PRELIGHT:
            child.style.paint_box(event.window, gtk.STATE_PRELIGHT,  gtk.SHADOW_NONE, event.area,  child, 'toolbutton-prelight',  allocation.x, allocation.y,  allocation.width, allocation.height)

        gtk.ToolButton.do_expose_event(self, event)

    def __notify_change(self, widget, pspec):
        self.notify(pspec.name)

    def __font_set_cb(self, widget):
        self.emit('font-set')


########NEW FILE########
__FILENAME__ = htmltextview
### Copyright (C) 2005 Gustavo J. A. M. Carneiro
###
### This library is free software; you can redistribute it and/or
### modify it under the terms of the GNU Lesser General Public
### License as published by the Free Software Foundation; either
### version 2 of the License, or (at your option) any later version.
###
### This library is distributed in the hope that it will be useful,
### but WITHOUT ANY WARRANTY; without even the implied warranty of
### MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
### Lesser General Public License for more details.
###
### You should have received a copy of the GNU Lesser General Public
### License along with this library; if not, write to the
### Free Software Foundation, Inc., 59 Temple Place - Suite 330,
### Boston, MA 02111-1307, USA.

'''A gtk.TextView-based renderer for XHTML-IM, as described in: http://www.jabber.org/jeps/jep-0071.html'''
import gobject
import pango
import gtk
import xml.sax, xml.sax.handler
import re
import warnings
from cStringIO import StringIO
import urllib2
import operator

__all__ = ['HtmlTextView', 'MessageTextView']

whitespace_rx = re.compile("\\s+")
allwhitespace_rx = re.compile("^\\s*$")

## pixels = points * display_resolution
display_resolution = 0.3514598*(gtk.gdk.screen_height() /
                    float(gtk.gdk.screen_height_mm()))


def _parse_css_color(color):
    '''_parse_css_color(css_color) -> gtk.gdk.Color'''
    if color.startswith("rgb(") and color.endswith(')'):
        r, g, b = [int(c)*257 for c in color[4:-1].split(',')]
        return gtk.gdk.Color(r, g, b)
    else:
        return gtk.gdk.color_parse(color)


class HtmlHandler(xml.sax.handler.ContentHandler):

    def __init__(self, textview, startiter):
        xml.sax.handler.ContentHandler.__init__(self)
        self.textbuf = textview.get_buffer()
        self.textview = textview
        self.iter = startiter
        self.text = ''
        self.styles = [] # a gtk.TextTag or None, for each span level
        self.list_counters = [] # stack (top at head) of list
                                # counters, or None for unordered list

    def _parse_style_color(self, tag, value):
        color = _parse_css_color(value)
        tag.set_property("foreground-gdk", color)

    def _parse_style_background_color(self, tag, value):
        color = _parse_css_color(value)
        tag.set_property("background-gdk", color)
        if gtk.gtk_version >= (2, 8):
            tag.set_property("paragraph-background-gdk", color)


    if gtk.gtk_version >= (2, 8, 5) or gobject.pygtk_version >= (2, 8, 1):

        def _get_current_attributes(self):
            attrs = self.textview.get_default_attributes()
            self.iter.backward_char()
            self.iter.get_attributes(attrs)
            self.iter.forward_char()
            return attrs

    else:

        ## Workaround http://bugzilla.gnome.org/show_bug.cgi?id=317455
        def _get_current_style_attr(self, propname, comb_oper=None):
            tags = [tag for tag in self.styles if tag is not None]
            tags.reverse()
            is_set_name = propname + "-set"
            value = None
            for tag in tags:
                if tag.get_property(is_set_name):
                    if value is None:
                        value = tag.get_property(propname)
                        if comb_oper is None:
                            return value
                    else:
                        value = comb_oper(value, tag.get_property(propname))
            return value

        class _FakeAttrs(object):
            __slots__ = ("font", "font_scale")

        def _get_current_attributes(self):
            attrs = self._FakeAttrs()
            attrs.font_scale = self._get_current_style_attr("scale",
                                                            operator.mul)
            if attrs.font_scale is None:
                attrs.font_scale = 1.0
            attrs.font = self._get_current_style_attr("font-desc")
            if attrs.font is None:
                attrs.font = self.textview.style.font_desc
            return attrs


    def __parse_length_frac_size_allocate(self, textview, allocation,
                                          frac, callback, args):
        callback(allocation.width*frac, *args)

    def _parse_length(self, value, font_relative, callback, *args):
        '''Parse/calc length, converting to pixels, calls callback(length, *args)
        when the length is first computed or changes'''
        if value.endswith('%'):
            frac = float(value[:-1])/100
            if font_relative:
                attrs = self._get_current_attributes()
                font_size = attrs.font.get_size() / pango.SCALE
                callback(frac*display_resolution*font_size, *args)
            else:
                ## CSS says "Percentage values: refer to width of the closest
                ##           block-level ancestor"
                ## This is difficult/impossible to implement, so we use
                ## textview width instead; a reasonable approximation..
                alloc = self.textview.get_allocation()
                self.__parse_length_frac_size_allocate(self.textview, alloc,
                                                       frac, callback, args)
                self.textview.connect("size-allocate",
                                      self.__parse_length_frac_size_allocate,
                                      frac, callback, args)

        elif value.endswith('pt'): # points
            callback(float(value[:-2])*display_resolution, *args)

        elif value.endswith('em'): # ems, the height of the element's font
            attrs = self._get_current_attributes()
            font_size = attrs.font.get_size() / pango.SCALE
            callback(float(value[:-2])*display_resolution*font_size, *args)

        elif value.endswith('ex'): # x-height, ~ the height of the letter 'x'
            ## FIXME: figure out how to calculate this correctly
            ##        for now 'em' size is used as approximation
            attrs = self._get_current_attributes()
            font_size = attrs.font.get_size() / pango.SCALE
            callback(float(value[:-2])*display_resolution*font_size, *args)

        elif value.endswith('px'): # pixels
            callback(int(value[:-2]), *args)

        else:
            warnings.warn("Unable to parse length value '%s'" % value)

    def __parse_font_size_cb(length, tag):
        tag.set_property("size-points", length/display_resolution)
    __parse_font_size_cb = staticmethod(__parse_font_size_cb)

    def _parse_style_font_size(self, tag, value):
        try:
            scale = {
                "xx-small": pango.SCALE_XX_SMALL,
                "x-small": pango.SCALE_X_SMALL,
                "small": pango.SCALE_SMALL,
                "medium": pango.SCALE_MEDIUM,
                "large": pango.SCALE_LARGE,
                "x-large": pango.SCALE_X_LARGE,
                "xx-large": pango.SCALE_XX_LARGE,
                } [value]
        except KeyError:
            pass
        else:
            attrs = self._get_current_attributes()
            tag.set_property("scale", scale / attrs.font_scale)
            return
        if value == 'smaller':
            tag.set_property("scale", pango.SCALE_SMALL)
            return
        if value == 'larger':
            tag.set_property("scale", pango.SCALE_LARGE)
            return
        self._parse_length(value, True, self.__parse_font_size_cb, tag)

    def _parse_style_font_style(self, tag, value):
        try:
            style = {
                "normal": pango.STYLE_NORMAL,
                "italic": pango.STYLE_ITALIC,
                "oblique": pango.STYLE_OBLIQUE,
                } [value]
        except KeyError:
            warnings.warn("unknown font-style %s" % value)
        else:
            tag.set_property("style", style)

    def __frac_length_tag_cb(length, tag, propname):
        tag.set_property(propname, length)
    __frac_length_tag_cb = staticmethod(__frac_length_tag_cb)

    def _parse_style_margin_left(self, tag, value):
        self._parse_length(value, False, self.__frac_length_tag_cb,
                           tag, "left-margin")

    def _parse_style_margin_right(self, tag, value):
        self._parse_length(value, False, self.__frac_length_tag_cb,
                           tag, "right-margin")

    def _parse_style_font_weight(self, tag, value):
        ## TODO: missing 'bolder' and 'lighter'
        try:
            weight = {
                '100': pango.WEIGHT_ULTRALIGHT,
                '200': pango.WEIGHT_ULTRALIGHT,
                '300': pango.WEIGHT_LIGHT,
                '400': pango.WEIGHT_NORMAL,
                '500': pango.WEIGHT_NORMAL,
                '600': pango.WEIGHT_BOLD,
                '700': pango.WEIGHT_BOLD,
                '800': pango.WEIGHT_ULTRABOLD,
                '900': pango.WEIGHT_HEAVY,
                'normal': pango.WEIGHT_NORMAL,
                'bold': pango.WEIGHT_BOLD,
                } [value]
        except KeyError:
            warnings.warn("unknown font-style %s" % value)
        else:
            tag.set_property("weight", weight)

    def _parse_style_font_family(self, tag, value):
        tag.set_property("family", value)

    def _parse_style_text_align(self, tag, value):
        try:
            align = {
                'left': gtk.JUSTIFY_LEFT,
                'right': gtk.JUSTIFY_RIGHT,
                'center': gtk.JUSTIFY_CENTER,
                'justify': gtk.JUSTIFY_FILL,
                } [value]
        except KeyError:
            warnings.warn("Invalid text-align:%s requested" % value)
        else:
            tag.set_property("justification", align)

    def _parse_style_text_decoration(self, tag, value):
        if value == "none":
            tag.set_property("underline", pango.UNDERLINE_NONE)
            tag.set_property("strikethrough", False)
        elif value == "underline":
            tag.set_property("underline", pango.UNDERLINE_SINGLE)
            # peacey: Commented out the removal of strikethrough so we could enable 
            # both underline and strikethrough at the same time
            #tag.set_property("strikethrough", False)
        elif value == "overline":
            warnings.warn("text-decoration:overline not implemented")
            tag.set_property("underline", pango.UNDERLINE_NONE)
            tag.set_property("strikethrough", False)
        elif value == "line-through":
            # peacey: Commented out the removal of underline so we could enable 
            # both underline and strikethrough at the same time
            #tag.set_property("underline", pango.UNDERLINE_NONE)
            tag.set_property("strikethrough", True)
        elif value == "blink":
            warnings.warn("text-decoration:blink not implemented")
        else:
            warnings.warn("text-decoration:%s not implemented" % value)


    ## build a dictionary mapping styles to methods, for greater speed
    __style_methods = dict()
    for style in ["background-color", "color", "font-family", "font-size",
                  "font-style", "font-weight", "margin-left", "margin-right",
                  "text-align", "text-decoration"]:
        try:
            method = locals()["_parse_style_%s" % style.replace('-', '_')]
        except KeyError:
            warnings.warn("Style attribute '%s' not yet implemented" % style)
        else:
            __style_methods[style] = method
    del style
    ## --

    def _get_style_tags(self):
        return [tag for tag in self.styles if tag is not None]


    def _begin_span(self, style, tag=None):
        if style is None:
            self.styles.append(tag)
            return None
        if tag is None:
            tag = self.textbuf.create_tag()
        for attr, val in [item.split(':', 1) for item in style.split(';')]:
            attr = attr.strip().lower()
            val = val.strip()
            try:
                method = self.__style_methods[attr]
            except KeyError:
                warnings.warn("Style attribute '%s' requested "
                              "but not yet implemented" % attr)
            else:
                method(self, tag, val)
        self.styles.append(tag)

    def _end_span(self):
        self.styles.pop(-1)

    def _insert_text(self, text):
        tags = self._get_style_tags()
        if tags:
            self.textbuf.insert_with_tags(self.iter, text, *tags)
        else:
            self.textbuf.insert(self.iter, text)

    def _flush_text(self):
        if not self.text: return
        self._insert_text(self.text.replace('\n', ''))
        self.text = ''

    def _anchor_event(self, tag, textview, event, iter, href, type_):
        if event.type == gtk.gdk.BUTTON_PRESS and event.button == 1:
            self.textview.emit("url-clicked", href, type_)
            return True
        return False

    def characters(self, content):
        if allwhitespace_rx.match(content) is not None:
            return
        if self.text: self.text += ' '
        self.text += whitespace_rx.sub(' ', content)

    def startElement(self, name, attrs):
        self._flush_text()
        try:
            style = attrs['style']
        except KeyError:
            style = None

        tag = None
        if name == 'a':
            tag = self.textbuf.create_tag()
            tag.set_property('foreground', '#0000ff')
            tag.set_property('underline', pango.UNDERLINE_SINGLE)
            try:
                type_ = attrs['type']
            except KeyError:
                type_ = None
            tag.connect('event', self._anchor_event, attrs['href'], type_)
            tag.is_anchor = True

        self._begin_span(style, tag)

        if name == 'br':
            pass # handled in endElement
        elif name == 'p':
            if not self.iter.starts_line():
                self._insert_text("\n")
        elif name == 'div':
            if not self.iter.starts_line():
                self._insert_text("\n")
        elif name == 'span':
            pass
        elif name == 'ul':
            if not self.iter.starts_line():
                self._insert_text("\n")
            self.list_counters.insert(0, None)
        elif name == 'ol':
            if not self.iter.starts_line():
                self._insert_text("\n")
            self.list_counters.insert(0, 0)
        elif name == 'li':
            if self.list_counters[0] is None:
                li_head = unichr(0x2022)
            else:
                self.list_counters[0] += 1
                li_head = "%i." % self.list_counters[0]
            self.text = ' '*len(self.list_counters)*4 + li_head + ' '
        elif name == 'img':
            print "ENCOUNTERED IMAAGEEEEE"
            try:
                ## Max image size = 10 MB (to try to prevent DoS)
                mem = urllib2.urlopen(attrs['src']).read(10*1024*1024)
                ## Caveat: GdkPixbuf is known not to be safe to load
                ## images from network... this program is now potentially
                ## hackable ;)
                loader = gtk.gdk.PixbufLoader()
                loader.write(mem); loader.close()
                pixbuf = loader.get_pixbuf()
            except Exception, ex:
                pixbuf = None
                try:
                    alt = attrs['alt']
                except KeyError:
                    alt = "Broken image"
            if pixbuf is not None:
                tags = self._get_style_tags()
                if tags:
                    tmpmark = self.textbuf.create_mark(None, self.iter, True)

                self.textbuf.insert_pixbuf(self.iter, pixbuf)

                if tags:
                    start = self.textbuf.get_iter_at_mark(tmpmark)
                    for tag in tags:
                        self.textbuf.apply_tag(tag, start, self.iter)
                    self.textbuf.delete_mark(tmpmark)
            else:
                self._insert_text("[IMG: %s]" % alt)
        elif name == 'body':
            pass
        elif name == 'a':
            pass
        else:
            warnings.warn("Unhandled element '%s'" % name)

    def endElement(self, name):
        self._flush_text()
        if name == 'p':
            if not self.iter.starts_line():
                self._insert_text("\n")
        elif name == 'div':
            if not self.iter.starts_line():
                self._insert_text("\n")
        elif name == 'span':
            pass
        elif name == 'br':
            self._insert_text("\n")
        elif name == 'ul':
            self.list_counters.pop()
        elif name == 'ol':
            self.list_counters.pop()
        elif name == 'li':
            self._insert_text("\n")
        elif name == 'img':
            pass
        elif name == 'body':
            pass
        elif name == 'a':
            pass
        else:
            warnings.warn("Unhandled element '%s'" % name)
        self._end_span()


class HtmlTextView(gtk.TextView):
    __gtype_name__ = 'HtmlTextView'
    __gsignals__ = {
        'url-clicked': (gobject.SIGNAL_RUN_LAST, None, (str, str)), # href, type
    }

    def __init__(self):
        gtk.TextView.__init__(self)
        self.set_wrap_mode(gtk.WRAP_CHAR)
        self.set_overwrite(False)
        self.set_accepts_tab(True)
        self.set_justification(gtk.JUSTIFY_LEFT)
        self.set_cursor_visible(False)
        self.set_editable(False)
        self._changed_cursor = False
        self.connect("motion-notify-event", self.__motion_notify_event)
        self.connect("leave-notify-event", self.__leave_event)
        self.connect("enter-notify-event", self.__motion_notify_event)
        self.set_pixels_above_lines(3)
        self.set_pixels_below_lines(3)

    def __leave_event(self, widget, event):
        if self._changed_cursor:
            window = widget.get_window(gtk.TEXT_WINDOW_TEXT)
            window.set_cursor(gtk.gdk.Cursor(gtk.gdk.XTERM))
            self._changed_cursor = False

    def __motion_notify_event(self, widget, event):
        x, y, _ = widget.window.get_pointer()
        x, y = widget.window_to_buffer_coords(gtk.TEXT_WINDOW_TEXT, x, y)
        tags = widget.get_iter_at_location(x, y).get_tags()
        for tag in tags:
            if getattr(tag, 'is_anchor', False):
                is_over_anchor = True
                break
        else:
            is_over_anchor = False
        if not self._changed_cursor and is_over_anchor:
            window = widget.get_window(gtk.TEXT_WINDOW_TEXT)
            window.set_cursor(gtk.gdk.Cursor(gtk.gdk.HAND2))
            self._changed_cursor = True
        elif self._changed_cursor and not is_over_anchor:
            window = widget.get_window(gtk.TEXT_WINDOW_TEXT)
            window.set_cursor(gtk.gdk.Cursor(gtk.gdk.XTERM))
            self._changed_cursor = False
        return False

    def display_html(self, html):
        buffer = self.get_buffer()
        eob = buffer.get_end_iter()
        ## this works too if libxml2 is not available
        parser = xml.sax.make_parser(['drv_libxml2'])
        # parser.setFeature(xml.sax.handler.feature_validation, True)
        parser.setContentHandler(HtmlHandler(self, eob))
        parser.parse(StringIO(html))

        if not eob.starts_line():
            buffer.insert(eob, "\n")

    def scroll_to_bottom(self):
        textbuffer = self.get_buffer()
        textiter = textbuffer.get_end_iter()
        mark = textbuffer.create_mark("end", textiter, False)
        self.scroll_to_mark(mark, 0.05, True, 0.0, 1.0)
        textbuffer.place_cursor(textiter)
        return False

class MessageTextView(gtk.TextView):
    '''Class for the message textview (where user writes new messages)
    for chat/groupchat windows'''
    __gtype_name__ = 'MessageTextView'
    __gsignals__ = dict(mykeypress = (gobject.SIGNAL_RUN_LAST | gobject.SIGNAL_ACTION, None, (int, gtk.gdk.ModifierType )))

    def __init__(self):
        gtk.TextView.__init__(self)

        # set properties
        self.set_overwrite(False)
        self.set_justification(gtk.JUSTIFY_LEFT)
        self.set_border_width(1)
        self.set_accepts_tab(True)
        self.set_editable(True)
        self.set_cursor_visible(True)
        self.set_wrap_mode(gtk.WRAP_WORD_CHAR)
        self.set_left_margin(2)
        self.set_right_margin(2)
        self.set_pixels_above_lines(2)
        self.set_pixels_below_lines(2)

    def destroy(self):
        import gc
        gobject.idle_add(lambda:gc.collect())

    def clear(self, widget = None):
        '''clear text in the textview'''
        buffer = self.get_buffer()
        start, end = buffer.get_bounds()
        buffer.delete(start, end)

gtk.binding_entry_add_signal(MessageTextView, gtk.keysyms.Return, 0, 'mykeypress', int, gtk.keysyms.Return, gtk.gdk.ModifierType, 0)
gtk.binding_entry_add_signal(MessageTextView, gtk.keysyms.Escape, 0, 'mykeypress', int, gtk.keysyms.Escape, gtk.gdk.ModifierType, 0)

if gobject.pygtk_version < (2, 8):
    gobject.type_register(MessageTextView)
    gobject.type_register(HtmlTextView)


########NEW FILE########
__FILENAME__ = image
# -*- coding: utf-8 -*-
#===================================================
#
# image.py - This file is part of the amsn2 package
#
# Copyright (C) 2008  Wil Alvarez <wil_alejandro@yahoo.com>
#
# This script is free software; you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free Software
# Foundation; either version 3 of the License, or (at your option) any later
# version.
#
# This script is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
# FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public License
# for more details.
#
# You should have received a copy of the GNU General Public License along with
# this script (see COPYING); if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
#
#===================================================

import gtk
from amsn2.gui import base
from amsn2.core.views import imageview
import logging

logger = logging.getLogger("amsn2.gtk.image")

class Image(gtk.Image):
    def __init__(self, theme_manager, view):
        gtk.Image.__init__(self)
        self._theme_manager = theme_manager
        self._filename = None
        self.load(view)

    def load(self, view):
        i = 0
        for (resource_type, value) in view.imgs:
            try:
                loadMethod = getattr(self, "_loadFrom%s" % resource_type)
            except AttributeError, e:
                logger.error("Unable to find the method to load %s image from %s" % (value, resource_type))
            else:
                loadMethod(value, view, i)
                i += 1

    def _loadFromFilename(self, filename, view, index):
        # TODO: Implement support for emblems and other embedded images
        if (index != 0): return

        try:
            self.set_from_file(filename)
            self._filename = filename
        except Exception, e:
            logger.error("Error loading image %s" % filename)

    def _loadFromTheme(self, resource_name, view, index):
        # TODO: Implement support for emblems and other embedded images
        if (index != 0): return

        _, filename = self._theme_manager.get_value(resource_name)

        if filename is not None:
            self._loadFromFilename(filename, view, index)
        else:
            logger.error('Error loading image %s from theme' %resource_name)

    def to_pixbuf(self, width, height):
        #print 'image.py -> to_pixbuf: filename=%s' % self._filename
        try:
            pix = gtk.gdk.pixbuf_new_from_file_at_size(self._filename, 
                width, height)
            return pix
        except:
            logger.error('Error converting to pixbuf image %s' % self._filename)
            return None


########NEW FILE########
__FILENAME__ = login
# -*- coding: utf-8 -*-
#===================================================
#
# login.py - This file is part of the amsn2 package
#
# Copyright (C) 2008  Wil Alvarez <wil_alejandro@yahoo.com>
#
# This script is free software; you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free Software
# Foundation; either version 3 of the License, or (at your option) any later
# version.
#
# This script is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
# FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public License
# for more details.
#
# You should have received a copy of the GNU General Public License along with
# this script (see COPYING); if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
#
#===================================================

import os
import gtk
import gobject
import string
import logging

from image import *
from amsn2.core.views import AccountView, ImageView

logger = logging.getLogger('amsn2.gtk.login')

class aMSNLoginWindow(gtk.VBox, base.aMSNLoginWindow):

    def __init__(self, amsn_core, parent):

        gtk.VBox.__init__(self, spacing=10)

        self._amsn_core = amsn_core
        self._main_win = parent
        self._skin = amsn_core._skin_manager.skin
        self._theme_manager = self._amsn_core._theme_manager
        self.timer = None
        self.anim_phase = 1
        self.last_img = None

        # language selector
        path = os.path.join("amsn2", "themes", "default", "images",
        "login_screen", "language_icon.png")
        langImg = gtk.Image()
        langImg.set_from_file(path)

        self.langBtn = gtk.Button("Change Language")
        self.langBtn.set_relief(gtk.RELIEF_NONE)
        self.langBtn.set_image(langImg)
        self.langBtn.set_alignment(0,0)
        self.langBtn.connect("clicked", self.__on_change_language_request)

        langbox = gtk.HBox()
        langbox.pack_start(self.langBtn, False, False)

        # dp
        _, filename = self._theme_manager.get_dp("dp_amsn")
        dpbox = gtk.HBox()
        self.dp = gtk.Image()
        self.dp.set_from_file(filename)
        dpbox.pack_start(self.dp, True, False)

        # user
        userbox = gtk.VBox()
        userlabel = gtk.Label('User:')
        userlabel.set_alignment(0.0, 0.5)
        self.user = gtk.combo_box_entry_new_text()
        self.userListStore = gtk.ListStore(gobject.TYPE_STRING, gtk.gdk.Pixbuf)

        userCompletion = gtk.EntryCompletion()
        self.user.get_children()[0].set_completion(userCompletion)
        userCompletion.set_model(self.userListStore)

        userPixbufCell = gtk.CellRendererPixbuf()
        userCompletion.pack_start(userPixbufCell)

        userCompletion.add_attribute(userPixbufCell, 'pixbuf', 1)
        userCompletion.set_text_column(0)
        #userCompletion.connect('match-selected', self.matchSelected)
        self.user.connect("key-press-event", self.__on_user_comboxEntry_changed)
        #FIXME: focus-out-event not working, i don't know why
        self.user.connect("focus-out-event", self.__on_user_comboxEntry_changed)
        #self.user.connect("key-release-event", self.on_comboxEntry_keyrelease)
        userbox.pack_start(userlabel, False, False)
        userbox.pack_start(self.user, False, False)

        # password
        passbox = gtk.VBox()
        passlabel = gtk.Label('Password:')
        passlabel.set_alignment(0.0, 0.5)
        self.password = gtk.Entry(128)
        self.password.set_visibility(False)
        self.password.connect('activate' , self.__login_clicked)
        self.password.connect("changed", self.__on_passwd_comboxEntry_changed)
        passbox.pack_start(passlabel, False, False)
        passbox.pack_start(self.password, False, False)

        # status list
        self.status_values = {}
        status_n = 0
        status_list = gtk.ListStore(gtk.gdk.Pixbuf, str, str)
        for key in self._amsn_core.p2s:
            name = self._amsn_core.p2s[key]
            _, path = self._theme_manager.get_statusicon("buddy_%s" % name)
            if (key == self._amsn_core.Presence.OFFLINE): continue
            self.status_values[key] = status_n
            status_n = status_n +1
            icon = gtk.gdk.pixbuf_new_from_file(path)
            status_list.append([icon, name, key])


        iconCell = gtk.CellRendererPixbuf()
        iconCell.set_property('xalign', 0.0)
        txtCell = gtk.CellRendererText()
        txtCell.set_property('xalign', 0.0)

        # status combobox
        self.statusCombo = gtk.ComboBox()
        self.statusCombo.set_model(status_list)
        self.statusCombo.set_active(7) # Set status to 'online'
        self.statusCombo.pack_start(iconCell, False)
        self.statusCombo.pack_start(txtCell, False)
        self.statusCombo.add_attribute(iconCell, 'pixbuf',0)
        self.statusCombo.add_attribute(txtCell, 'markup',1)

        statuslabel = gtk.Label('Status:')
        statuslabel.set_alignment(0.0, 0.5)

        statusbox = gtk.VBox()
        statusbox.pack_start(statuslabel, False, False)
        statusbox.pack_start(self.statusCombo, False, False)

        # container for user, password and status widgets
        fields = gtk.VBox(True, 5)
        fields.pack_start(userbox, False, False)
        fields.pack_start(passbox, False, False)
        fields.pack_start(statusbox, False, False)

        fields_align = gtk.Alignment(0.5, 0.5, 0.0, 0.0)
        fields_align.add(fields)

        # checkboxes
        checkboxes = gtk.VBox()
        self.rememberMe = gtk.CheckButton('Remember me', True)
        self.rememberPass = gtk.CheckButton('Remember password', True)
        self.autoLogin = gtk.CheckButton('Auto-Login', True)

        self.rememberMe.connect("toggled", self.__on_toggled_cb)
        self.rememberPass.connect("toggled", self.__on_toggled_cb)
        self.autoLogin.connect("toggled", self.__on_toggled_cb)

        checkboxes.pack_start(self.rememberMe, False, False)
        checkboxes.pack_start(self.rememberPass, False, False)
        checkboxes.pack_start(self.autoLogin, False, False)

        # align checkboxes
        checkAlign = gtk.Alignment(0.5, 0.5)
        checkAlign.add(checkboxes)

        # login button
        button_box = gtk.HButtonBox()
        self.login_button = gtk.Button('Login', gtk.STOCK_CONNECT)
        self.login_button.connect('clicked', self.__login_clicked)
        button_box.pack_start(self.login_button, False, False)
        self.login = False

        self.pack_start(langbox, True, False)
        self.pack_start(dpbox, True, False)
        self.pack_start(fields_align, True, False)
        self.pack_start(checkAlign, True, False)
        self.pack_start(button_box, True, False)

        # temporarily not used
        self.status = gtk.Label('')
        self.pgbar = gtk.ProgressBar()
        pgAlign = gtk.Alignment(0.5, 0.5)
        pgAlign.add(self.pgbar)

        self.input_boxes = [langbox, fields_align, checkAlign]
        self.fixed_boxes = [dpbox, button_box]
        self.connecting_boxes = [self.status, pgAlign]

        self._main_win.set_view(self)
        

    def __animation(self):
        path = os.path.join("amsn2", "themes", "default", "images",
        "login_screen", "cube")
        name = "cube_%03d.png" % self.anim_phase
        filename = os.path.join(path, name)

        if (os.path.isfile(filename)):
            self.last_img = filename
        else:
            filename = self.last_img

        pix = gtk.gdk.pixbuf_new_from_file_at_size(filename, 96, 96)
        self.dp.set_from_pixbuf(pix)
        self.anim_phase += 1
        del pix

        return True

    def __login_clicked(self, *args):
        if self.login:
            self.signout()
        else:
            self.signin()

    def show(self):
        if self.user.get_active_text() == "":
            self.user.grab_focus()
        elif self.password.get_text() == "":
            self.password.grab_focus()

        self.show_all()

    def hide(self):
        if self.timer is not None:
            gobject.source_remove(self.timer)

    def __switch_to_account(self, email):
        logger.info("Switching to account %s", email)

        accv = self.getAccountViewFromEmail(email)

        if accv is None:
            accv = AccountView(self._amsn_core, email)

        self.user.get_children()[0].set_text(accv.email)
        if accv.password:
            self.password.set_text(accv.password)

        self.statusCombo.set_active(self.status_values[accv.presence])

        self.rememberMe.set_active(accv.save)
        self.rememberPass.set_active(accv.save_password)
        self.autoLogin.set_active(accv.autologin)

    def setAccounts(self, accountviews):
        self._account_views = accountviews

        for accv in self._account_views:
            self.user.append_text(accv.email)

        if len(accountviews)>0 :
            # first in the list, default
            self.__switch_to_account(self._account_views[0].email)

            if self._account_views[0].autologin:
                self.signin()

    def signout(self):
        self.remove(self.connecting_boxes[0])
        self.remove(self.connecting_boxes[1])
        for box in self.input_boxes:
            self.pack_start(box, True, False)

        self.reorder_child(self.fixed_boxes[1], -1)
        self.reorder_child(self.fixed_boxes[0], 1)

        self.login = False
        self.login_button.set_label(gtk.STOCK_CONNECT)

        if self.timer is not None:
            gobject.source_remove(self.timer)
        # TODO: set the account's dp
        _, filename = self._theme_manager.get_dp("dp_amsn")
        self.dp.set_from_file(filename)

        self._amsn_core.signOutOfAccount()

    def signin(self):

        if self.user.get_active_text() == "":
            self.user.grab_focus()
            return
        elif self.password.get_text() == "":
            self.password.grab_focus()
            return

        email = self.user.get_active_text()
        accv = self.getAccountViewFromEmail(email)

        if accv is None:
            accv = AccountView(self._amsn_core, email)

        accv.password = self.password.get_text()
        iter = self.statusCombo.get_active_iter()
        model = self.statusCombo.get_model()
        status = model.get_value(iter, 2)
        accv.presence = status

        accv.save = self.rememberMe.get_active()
        accv.save_password = self.rememberPass.get_active()
        accv.autologin = self.autoLogin.get_active()

        for box in self.input_boxes:
            self.remove(box)

        self.login = True
        self.status.show()
        pgAlign = self.pgbar.get_parent()
        pgAlign.show()
        self.pgbar.show()
        self.pack_start(pgAlign, False, False)
        self.pack_start(self.status, False, False)
        self.login_button.set_label(gtk.STOCK_DISCONNECT)
        self.reorder_child(self.fixed_boxes[1], -1)
        self.set_child_packing(self.fixed_boxes[1], True, False, 0, gtk.PACK_START)

        self._amsn_core.signinToAccount(self, accv)
        self.timer = gobject.timeout_add(40, self.__animation)

    def onConnecting(self, progress, message):
        self.status.set_text(message)
        self.pgbar.set_fraction(progress)

    def __on_user_comboxEntry_changed(self, entry, event):
        if event.type == gtk.gdk.FOCUS_CHANGE or \
            (event.type == gtk.gdk.KEY_PRESS and event.keyval == gtk.keysyms.Tab):
            self.__switch_to_account(entry.get_active_text())

    def __on_passwd_comboxEntry_changed(self, entry):
        if len(entry.get_text()) == 0:
            self.rememberPass.set_sensitive(False)
            self.autoLogin.set_sensitive(False)
        else:
            self.rememberPass.set_sensitive(True)
            self.autoLogin.set_sensitive(True)

    def __on_toggled_cb(self, source):

        email = self.user.get_active_text()
        accv = self.getAccountViewFromEmail(email)

        if accv is None:
            accv = AccountView(self._amsn_core, email)

        if source is self.rememberMe:
            accv.save = source.get_active()
            self.rememberPass.set_sensitive(source.get_active())
            self.autoLogin.set_sensitive(source.get_active())
        elif source is self.rememberPass:
            accv.save_password = source.get_active()
            self.autoLogin.set_sensitive(source.get_active())
        elif source is self.autoLogin:
            accv.autologin = source.get_active()

    def __on_change_language_request(self, source):
        pass


########NEW FILE########
__FILENAME__ = main

from amsn2.gui import base

import common
import skins
import gtk

class aMSNMainWindow(base.aMSNMainWindow):
    """
    @ivar main_win:
    @type main_win: gtk.Window
    """
    main_win = None

    def __init__(self, amsn_core):
        self._amsn_core = amsn_core
        self.main_win = gtk.Window()
        self.main_win.set_default_size(250, 500)
        self.main_win.connect('delete-event', self.__on_close)
        self.main_menu = gtk.MenuBar()
        inner = gtk.VBox()
        inner.pack_start(self.main_menu, False, False)
        self.main_win.add(inner)
        self.view = None

    def __on_show(self):
        self._amsn_core.mainWindowShown()

    def __on_close(self, widget, event):
        self._amsn_core.quit()

    def show(self):
        self.main_win.show()
        self._amsn_core.idlerAdd(self.__on_show)

    def setTitle(self, title):
        self.main_win.set_title(title)

    def hide(self):
        self.main_win.hide()

    def setMenu(self, menu):
        """ This will allow the core to change the current window's main menu
        @type menu: MenuView
        """
        chldn = self.main_menu.get_children()
        if len(chldn) is not 0:
            for chl in chldn:
                self.main_menu.remove(chl)
        common.createMenuItemsFromView(self.main_menu, menu.items)
        self.main_menu.show()

    def set_view(self, view):
        inner = self.main_win.get_child()
        chldn = inner.get_children()
        for c in chldn:
            if isinstance(c, base.aMSNLoginWindow) or isinstance(c, base.aMSNContactListWindow):
                inner.remove(c)

        inner.pack_start(view)
        self.main_win.show_all()


########NEW FILE########
__FILENAME__ = main_loop

from amsn2.gui import base
import gobject

class aMSNMainLoop(base.aMSNMainLoop):
    def __init__(self, amsn_core):
        self._amsn_core = amsn_core

    def run(self):
        self._mainloop = gobject.MainLoop(is_running=True)

        while self._mainloop.is_running():
            try:
                self._mainloop.run()
            except KeyboardInterrupt:
                self.quit()


    def idlerAdd(self, func):
        gobject.idle_add(func)

    def timerAdd(self, delay, func):
        gobject.timeout_add(delay, func)

    def quit(self):
        self._mainloop.quit()


########NEW FILE########
__FILENAME__ = skins
# -*- coding: utf-8 -*-
#===================================================
#
# contact_list.py - This file is part of the amsn2 package
#
# Copyright (C) 2008  Wil Alvarez <wil_alejandro@yahoo.com>
#
# This script is free software; you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free Software
# Foundation; either version 3 of the License, or (at your option) any later
# version.
#
# This script is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
# FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public License
# for more details.
#
# You should have received a copy of the GNU General Public License along with
# this script (see COPYING); if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
#
#===================================================

from amsn2.gui import base

import os

class Skin(base.Skin):
    def __init__(self, core, path):
        self._path = path
        self._dict = {}
        #TODO : remove, it's just here for test purpose
        #TODO : explain a bit :D
        self.setKey("buddy_online", ("Filename", os.path.join("amsn2",
            "themes", "default", "images", "online.png")))
        #self.setKey("emblem_online", ("Filename", "amsn2/themes/default/images/contact_list/plain_emblem.png"))

        self.setKey("buddy_away", ("Filename", os.path.join("amsn2",
            "themes", "default", "images", "away.png")))

        #self.setKey("emblem_away", ("Filename", "amsn2/themes/default/images/contact_list/away_emblem.png"))
        self.setKey("buddy_brb", ("Filename", os.path.join("amsn2",
            "themes", "default", "images", "away.png")))
        #self.setKey("emblem_brb", ("Filename", "amsn2/themes/default/images/contact_list/away_emblem.png"))
        self.setKey("buddy_idle", ("Filename", os.path.join("amsn2",
            "themes", "default", "images", "away.png")))
        #self.setKey("emblem_idle", ("Filename", "amsn2/themes/default/images/contact_list/away_emblem.png"))
        self.setKey("buddy_lunch", ("Filename", os.path.join("amsn2",
            "themes", "default", "images", "away.png")))
        #self.setKey("emblem_lunch", ("Filename", "amsn2/themes/default/images/contact_list/away_emblem.png"))

        # Just to show you can use an image from the edj file
        self.setKey("buddy_busy", ("Filename", os.path.join("amsn2",
            "themes", "default", "images","busy.png")))
        #self.setKey("emblem_busy", ("Filename", "amsn2/themes/default/images/contact_list/busy_emblem.png"))
        self.setKey("buddy_phone", ("Filename", os.path.join("amsn2",
            "themes", "default", "images", "busy.png")))
        #self.setKey("emblem_phone", ("Filename", "amsn2/themes/default/images/contact_list/busy_emblem.png"))

        self.setKey("buddy_offline", ("Filename", os.path.join("amsn2",
            "themes", "default", "images", "offline.png")))

        #self.setKey("emblem_offline", ("Filename", "amsn2/themes/default/images/contact_list/offline_emblem.png"))
        self.setKey("buddy_hidden", ("Filename", os.path.join("amsn2",
            "themes", "default", "images", "offline.png")))
        #self.setKey("emblem_hidden", ("Filename", "amsn2/themes/default/images/contact_list/offline_emblem.png"))

        self.setKey("default_dp", ("Filename", os.path.join("amsn2", "themes",
            "default", "images", "contact_list", "nopic.png")))

    def getKey(self, key, default=None):
        try:
            return self._dict[key]
        except KeyError:
            return default

    def setKey(self, key, value):
        self._dict[key] = value


class SkinManager(base.SkinManager):
    def __init__(self, core):
        self._core = core
        self.skin = Skin(core, "skins")

    def setSkin(self, name):
        self.skin = Skin(self._core, os.path.join("skins", name))

    def listSkins(self, path):
        pass

########NEW FILE########
__FILENAME__ = splash
from amsn2.gui import base

class aMSNSplashScreen(base.aMSNSplashScreen):

    def __init__(self, amsn_core, parent):
        pass

    def show(self):
        pass

    def hide(self):
        pass

    def setText(self, text):
        pass

    def setImage(self, image):
        pass

########NEW FILE########
__FILENAME__ = utility

from amsn2.gui import base
from amsn2.core import views
import gtk
import logging

logger = logging.getLogger('amsn2.gtk.utility')

class aMSNErrorWindow(base.aMSNErrorWindow, gtk.Dialog):
    def __init__(self, error_text):
        gtk.Dialog.__init__(self, "aMSN Error", None, gtk.DIALOG_NO_SEPARATOR,
                            (gtk.STOCK_OK, gtk.RESPONSE_ACCEPT))
        label = gtk.Label(error_text)
        self.get_content_area().set_spacing(5)
        self.get_content_area().pack_start(label)
        label.show()
        self.connect("response", self.onResponse)
        self.show()

    def onResponse(self, dialog, id):
        self.destroy()

class aMSNNotificationWindow(base.aMSNNotificationWindow, gtk.Dialog):
    def __init__(self, notification_text):
        gtk.Dialog.__init__(self, "aMSN Notification", None, gtk.DIALOG_NO_SEPARATOR,
                            (gtk.STOCK_OK, gtk.RESPONSE_ACCEPT))
        label = gtk.Label(notification_text)
        self.get_content_area().set_spacing(5)
        self.get_content_area().pack_start(label)
        label.show()
        self.connect("response", self.onResponse)
        self.show()

    def onResponse(self, dialog, id):
        self.destroy()

class aMSNDialogWindow(base.aMSNDialogWindow, gtk.Dialog):
    def __init__(self, message, actions):
        gtk.Dialog.__init__(self, "aMSN Dialog", None, gtk.DIALOG_NO_SEPARATOR, None)

        label = gtk.Label(message)
        ca = self.get_content_area()
        ca.pack_start(label)

        id = -1
        self._cbs = {}
        for act in actions:
            name, cb = act
            self.add_button(name, id)
            self._cbs[id] = cb
            id = id - 1

        self.connect("response", self.onResponse)
        label.show()
        self.show()

    def onResponse(self, dialog, id):
        try:
            self._cbs[id]()
        except KeyError:
            logger.warning("Unknown dialog choice, id %s" % id)
        self.destroy()

class aMSNContactInputWindow(base.aMSNContactInputWindow, gtk.Dialog):
    def __init__(self, message, callback, groups):
        gtk.Dialog.__init__(self, "aMSN Contact Input", None, gtk.DIALOG_NO_SEPARATOR,
                            (gtk.STOCK_OK, gtk.RESPONSE_ACCEPT,
                             gtk.STOCK_CANCEL, gtk.RESPONSE_REJECT))
        self._callback = callback

        label = gtk.Label(message[0])
        self._name = gtk.Entry()
        ca = self.get_content_area()
        ca.set_spacing(5)
        ca.pack_start(label)
        ca.pack_start(self._name)

        # TODO: build list of existing groups
        label2 = gtk.Label(message[1])
        ca.pack_start(label2)
        self._message = gtk.Entry()
        ca.pack_start(self._message)
        label2.show()
        self._message.show()

        self.connect("response", self.onResponse)
        label.show()
        self._name.show()
        self.show()

    def onResponse(self, dialog, id):
        if id == gtk.RESPONSE_ACCEPT:
            name = self._name.get_text()
            msg = self._message.get_text()
            self._callback(name, msg)
        elif id == gtk.RESPONSE_REJECT:
            pass
        self.destroy()


class aMSNGroupInputWindow(base.aMSNGroupInputWindow, gtk.Dialog): 
    def __init__(self, message, callback, contacts):
        gtk.Dialog.__init__(self, "aMSN Group Input", None, gtk.DIALOG_NO_SEPARATOR,
                            (gtk.STOCK_OK, gtk.RESPONSE_ACCEPT,
                             gtk.STOCK_CANCEL, gtk.RESPONSE_REJECT))
        self._callback = callback

        label = gtk.Label(message[0])
        self._name = gtk.Entry()
        ca = self.get_content_area()
        ca.set_spacing(5)
        ca.pack_start(label)
        ca.pack_start(self._name)

        # TODO: build list of existing contacts
        label2 = gtk.Label(message[1])
        ca.pack_start(label2)
        self._message = gtk.Entry()
        ca.pack_start(self._message)
        label2.show()
        self._message.show()

        self.connect("response", self.onResponse)
        label.show()
        self._name.show()
        self.show()

    def onResponse(self, dialog, id):
        if id == gtk.RESPONSE_ACCEPT:
            name = self._name.get_text()
            self._callback(name)
        elif id == gtk.RESPONSE_REJECT:
            pass
        self.destroy()

class aMSNContactDeleteWindow(base.aMSNContactDeleteWindow, gtk.Dialog): 
    def __init__(self, message, callback, contacts):
        gtk.Dialog.__init__(self, "aMSN Contact Input", None, gtk.DIALOG_NO_SEPARATOR,
                            (gtk.STOCK_OK, gtk.RESPONSE_ACCEPT,
                             gtk.STOCK_CANCEL, gtk.RESPONSE_REJECT))
        self._callback = callback

        label = gtk.Label(message)
        self._name = gtk.Entry()
        ca = self.get_content_area()
        ca.set_spacing(5)
        ca.pack_start(label)
        ca.pack_start(self._name)

        self.connect("response", self.onResponse)
        label.show()
        self._name.show()
        self.show()

    def onResponse(self, dialog, id):
        if id == gtk.RESPONSE_ACCEPT:
            name = self._name.get_text()
            self._callback(name)
        elif id == gtk.RESPONSE_REJECT:
            pass
        self.destroy()

class aMSNGroupDeleteWindow(base.aMSNGroupDeleteWindow, gtk.Dialog): 
    def __init__(self, message, callback, groups):
        gtk.Dialog.__init__(self, "aMSN Group Input", None, gtk.DIALOG_NO_SEPARATOR,
                            (gtk.STOCK_OK, gtk.RESPONSE_ACCEPT,
                             gtk.STOCK_CANCEL, gtk.RESPONSE_REJECT))
        self._callback = callback

        label = gtk.Label(message)
        self._name = gtk.Entry()
        ca = self.get_content_area()
        ca.set_spacing(5)
        ca.pack_start(label)
        ca.pack_start(self._name)

        self.connect("response", self.onResponse)
        label.show()
        self._name.show()
        self.show()

    def onResponse(self, dialog, id):
        if id == gtk.RESPONSE_ACCEPT:
            name = self._name.get_text()
            self._callback(name)
        elif id == gtk.RESPONSE_REJECT:
            pass
        self.destroy()


########NEW FILE########
__FILENAME__ = chat_window
# -*- coding: utf-8 -*-
#
# amsn - a python client for the WLM Network
#
# Copyright (C) 2008 Dario Freddi <drf54321@gmail.com>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA

import cgi
import time
import sys
reload(sys)

import papyon
from amsn2.gui import base
from amsn2.core.views import ContactView, StringView

from PyQt4.QtCore import *
from PyQt4.QtGui import *
from PyQt4 import *
try:
    from ui_chatWindow import Ui_ChatWindow
except ImportError, e:
    # FIXME: Should do that with logging...
    print "WARNING: To use the QT4 you need to run the generateFiles.sh, check the README"
    raise e

class InputWidget(QTextEdit):
    def __init__(self, parent=None):
        QTextEdit.__init__(self, parent)
        self.setTextInteractionFlags(Qt.TextEditorInteraction)

    def keyPressEvent(self, event):
        print "key pressed:" + str(event.key())
        if event.key() == Qt.Key_Enter or event.key() == Qt.Key_Return:
            print "handle!!"
            self.emit(SIGNAL("enterKeyTriggered()"))
        else:
            QTextEdit.keyPressEvent(self, event)

class aMSNChatWindow(QTabWidget, base.aMSNChatWindow):
    def __init__(self, amsn_core, parent=None):
        QTabWidget.__init__(self, parent)

        self._core = amsn_core

    def addChatWidget(self, chat_widget):
        self.addTab(chat_widget, "test")


class aMSNChatWidget(QWidget, base.aMSNChatWidget):
    def __init__(self, amsn_conversation, parent, contacts_uid):
        QWidget.__init__(self, parent)

        self._amsn_conversation = amsn_conversation
        self.ui = Ui_ChatWindow()
        self.ui.setupUi(self)
        self.ui.inputWidget = InputWidget(self)
        self.ui.inputLayout.addWidget(self.ui.inputWidget)
        self._statusBar = QStatusBar(self)
        self.layout().addWidget(self._statusBar)
        self.last_sender = ''
        self.nickstyle = "color:#555555; margin-left:2px"
        self.msgstyle = "margin-left:15px"
        self.infostyle = "margin-left:2px; font-style:italic; color:#6d6d6d"
        self.loadEmoticonList()

        QObject.connect(self.ui.inputWidget, SIGNAL("textChanged()"), self.processInput)
        QObject.connect(self.ui.inputWidget, SIGNAL("enterKeyTriggered()"), self.__sendMessage)
        QObject.connect(self.ui.actionInsert_Emoticon, SIGNAL("triggered()"), self.showEmoticonList)
        self.enterShortcut = QShortcut(QKeySequence("Enter"), self.ui.inputWidget)
        self.nudgeShortcut = QShortcut(QKeySequence("Ctrl+G"), self)
        QObject.connect(self.enterShortcut, SIGNAL("activated()"), self.__sendMessage)
        QObject.connect(self.nudgeShortcut, SIGNAL("activated()"), self.__sendNudge)
        QObject.connect(self.ui.actionNudge, SIGNAL("triggered()"), self.__sendNudge)

        #TODO: remove this when papyon is "fixed"...
        sys.setdefaultencoding("utf8")

    def processInput(self):
        """ Here we process what is inside the widget... so showing emoticon
        and similar stuff"""

        QObject.disconnect(self.ui.inputWidget, SIGNAL("textChanged()"), self.processInput)

        self.text = QString(self.ui.inputWidget.toHtml())

        for emoticon in self.emoticonList:
            if self.text.contains(emoticon) == True:
                print emoticon
                self.text.replace(emoticon, "<img src=\"throbber.gif\" />")

        self.ui.inputWidget.setHtml(self.text)
        self.ui.inputWidget.moveCursor(QTextCursor.End)
        self.__typingNotification()

        QObject.connect(self.ui.inputWidget, SIGNAL("textChanged()"), self.processInput)

    def loadEmoticonList(self):
        self.emoticonList = QStringList()

        """ TODO: Request emoticon list from amsn core, maybe use a QMap to get the image URL? """

        """ TODO: Discuss how to handle custom emoticons. We have to provide an option
        to change the default icon theme, this includes standard emoticons too.
        Maybe qrc? """

        #self.emoticonList << ";)" << ":)" << "EmOtIcOn"
        #We want :) and ;) to work for now :p
        self.emoticonList << "EmOtIcOn"

    def showEmoticonList(self):
        """ Let's popup emoticon selection here """
        print "Guess what? No emoticons. But I'll put in a random one for you"
        self.appendImageAtCursor("throbber.gif")

    def __sendMessage(self):
        # TODO: Switch to this when implemented
        """ msg = self.ui.inputWidget.toHtml()
        self.ui.inputWidget.clear()
        strv = StringView()
        strv.appendElementsFromHtml(msg) """

        msg = QString.fromUtf8(self.ui.inputWidget.toPlainText())
        self.ui.inputWidget.clear()
        strv = StringView()
        strv.appendText(str(msg))
        ## as we send our msg to the conversation:
        self._amsn_conversation.sendMessage(strv)
        # this one will also notify us of our msg.
        # so no need to do:
        #self.ui.textEdit.append("<b>/me says:</b><br>"+unicode(msg)+"")
        
    def __sendNudge(self):
        self._amsn_conversation.sendNudge()
        self.ui.textEdit.append("<b>/me sent a nudge</b>")

    def __typingNotification(self):
        self._amsn_conversation.sendTypingNotification()

    def appendTextAtCursor(self, text):
        self.ui.inputWidget.textCursor().insertHtml(unicode(text))

    def appendImageAtCursor(self, image):
        self.ui.inputWidget.textCursor().insertHtml(QString("<img src=\"" + str(image) + "\" />"))

    def onUserJoined(self, contact):
        self.ui.textEdit.append(unicode("<b>"+QString.fromUtf8(contact.toHtmlString())+" "+self.tr("has joined the conversation")+("</b>")))
        pass

    def onUserLeft(self, contact):
        self.ui.textEdit.append(unicode("<b>"+QString.fromUtf8(contact.toHtmlString())+" "+self.tr("has left the conversation")+("</b>")))
        pass

    def onUserTyping(self, contact):
        self._statusBar.showMessage(unicode(QString.fromUtf8(contact.toHtmlString()) + " is typing"), 7000)

    def onMessageReceived(self, messageview, formatting=None):
        print "Ding!"

        text = messageview.toStringView().toHtmlString()
        text = cgi.escape(text)
        nick, msg = text.split('\n', 1)
        nick = nick.replace('\n', '<br/>')
        msg = msg.replace('\n', '<br/>')
        sender = messageview.sender.toHtmlString()

        # peacey: Check formatting of styles and perform the required changes
        if formatting:
            fmsg = '''<span style="'''
            if formatting.font:
                fmsg += "font-family: %s;" % formatting.font
            if formatting.color:
                fmsg += "color: %s;" % ("#"+formatting.color)
            if formatting.style & papyon.TextFormat.BOLD == papyon.TextFormat.BOLD:
                fmsg += "font-weight: bold;"
            if formatting.style & papyon.TextFormat.ITALIC == papyon.TextFormat.ITALIC:
                fmsg += "font-style: italic;"
            if formatting.style & papyon.TextFormat.UNDERLINE == papyon.TextFormat.UNDERLINE:
                fmsg += "text-decoration: underline;"
            if formatting.style & papyon.TextFormat.STRIKETHROUGH == papyon.TextFormat.STRIKETHROUGH:
                fmsg += "text-decoration: line-through;"
            if formatting.right_alignment:
                fmsg += "text-align: right;"
            fmsg = fmsg.rstrip(";")
            fmsg += '''">'''
            fmsg += msg
            fmsg += "</span>"
        else:
            fmsg = msg

        html = '<div>'
        if (self.last_sender != sender):
            html += '<span style="%s">%s</span><br/>' % (self.nickstyle, nick)
        html += '<span style="%s">[%s] %s</span></div>' % (self.msgstyle, time.strftime('%X'), fmsg)

        self.ui.textEdit.append(QString.fromUtf8(html))
        self.last_sender = sender

    def onNudgeReceived(self, sender):
        self.ui.textEdit.append(unicode("<b>"+QString.fromUtf8(sender.toHtmlString())+" "+self.tr("sent you a nudge!")+("</b>")))
        pass



########NEW FILE########
__FILENAME__ = contact_delegate
# -*- coding: utf-8 -*-
#
# amsn - a python client for the WLM Network
#
# Copyright (C) 2008 Dario Freddi <drf54321@gmail.com>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA 02111-1307 USA
 
from QtGui import *
from QtCore import *
 
class ContactDelegate(QItemDelegate):
    def __init__(self, parent):
        QStandardItemModel.__init__(parent) 

########NEW FILE########
__FILENAME__ = contact_list
# -*- coding: utf-8 -*-
#
# amsn - a python client for the WLM Network
#
# Copyright (C) 2008 Dario Freddi <drf54321@gmail.com>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA

from amsn2.gui import base

from PyQt4.QtCore import *
from PyQt4.QtGui import *
from ui_contactlist import Ui_ContactList
from styledwidget import StyledWidget

from image import *
from amsn2.core.views import StringView, ContactView, GroupView, ImageView, PersonalInfoView

class aMSNContactListWindow(base.aMSNContactListWindow):
    def __init__(self, amsn_core, parent):
        self._amsn_core = amsn_core
        self._parent = parent
        self._skin = amsn_core._skin_manager.skin
        self._theme_manager = self._amsn_core._theme_manager
        self._myview = amsn_core._personalinfo_manager._personalinfoview
        self._clwidget = aMSNContactListWidget(amsn_core, self)
        self._clwidget.show()
        self.__create_controls()

    def __create_controls(self):
        # TODO Create and set text/values to controls.
        #status list
        self.status_values = {}
        self.status_dict = {}
        status_n = 0
        for key in self._amsn_core.p2s:
            name = self._amsn_core.p2s[key]
            if (name == 'offline'): continue
            self.status_values[name] = status_n
            self.status_dict[str.capitalize(name)] = name
            status_n = status_n +1
        # If we add a combobox like the gtk ui, uncomment this.
        #self.ui.comboStatus.addItem(str.capitalize(name))

    def show(self):
        self._clwidget.show()

    def hide(self):
        self._clwidget.hide()

    def setTitle(self, text):
        self._parent.setTitle(text)

    def setMenu(self, menu):
        self._parent.setMenu(menu)

    def topCLUpdated(self, contactView):
        pass #TODO

    def myInfoUpdated(self, view):
        # TODO image, ...
        self._myview = view
        nk = view.nick
        self.ui.nickName.setText(str(nk))
        message = str(view.psm)+' '+str(view.current_media)
        self.ui.statusMessage.setText('<i>'+message+'</i>')
        # TODO Add a combobox like the gtk ui?
        #self.ui.statusCombo.currentIndex(self.status_values[view.presence])

class itemDelegate(QStyledItemDelegate):
    #Dooooon't touch anything here!!! Or it will break into a million pieces and you'll be really sorry!!!
    def paint(self, painter, option, index):
        if not index.isValid():
            return
        painter.translate(0, 0)
        options = QStyleOptionViewItemV4(option)
        self.initStyleOption(options, index)
        painter.save()
        painter.setRenderHint(QPainter.Antialiasing, True)
        doc = QTextDocument()
        doc.setHtml(options.text)
        options.text = ""
        options.widget.style().drawControl(QStyle.CE_ItemViewItem, options, painter, options.widget)
        painter.translate(options.rect.left() + self.sizeDp(index) + 3, options.rect.top()) #paint text right after the dp + 3pixels
        rect = QRectF(0, 0, options.rect.width(), options.rect.height())
        doc.drawContents(painter, rect)
        painter.restore()

    def sizeHint(self, option, index):
        options = QStyleOptionViewItemV4(option)
        self.initStyleOption(options, index)
        doc = QTextDocument()
        doc.setHtml(options.text)
        doc.setTextWidth(options.rect.width())

        #if group, leave as it, if contactitem, use dp height for calculating sizeHint.
        model = index.model()
        qv = QPixmap(model.data(model.index(index.row(), 0, index.parent()), Qt.DecorationRole))
        if qv.isNull():
            size = QSize(doc.idealWidth(), doc.size().height())
        else:
            size = QSize(doc.idealWidth(), qv.height() + 6)
            
        return size

    def sizeDp(self, index):
        model = index.model()
        qv = QPixmap(model.data(model.index(index.row(), 0, index.parent()), Qt.DecorationRole))
        return qv.width()

class aMSNContactListWidget(StyledWidget, base.aMSNContactListWidget):
    def __init__(self, amsn_core, parent):
        base.aMSNContactListWidget.__init__(self, amsn_core, parent)
        StyledWidget.__init__(self, parent._parent)
        self._amsn_core = amsn_core
        self.ui = Ui_ContactList()
        self.ui.setupUi(self)
        delegate = itemDelegate(self)
        self.ui.cList.setItemDelegate(delegate)
        self._parent = parent
        self._mainWindow = parent._parent
        self._model = QStandardItemModel(self)
        self._model.setColumnCount(4)
        self._proxyModel = QSortFilterProxyModel(self)
        self._proxyModel.setSourceModel(self._model)
        self.ui.cList.setModel(self._proxyModel)
        self._contactDict = dict()
        self.groups = []
        self.contacts = {}

        self._proxyModel.setFilterCaseSensitivity(Qt.CaseInsensitive)
        self._proxyModel.setFilterKeyColumn(-1)

        (self.ui.cList.header()).resizeSections(1) #auto-resize column wigth
        (self.ui.cList.header()).setSectionHidden(1, True) #hide --> (group/contact ID)
        (self.ui.cList.header()).setSectionHidden(2, True) #hide --> (boolean value. Do I really need this?)
        (self.ui.cList.header()).setSectionHidden(3, True) #hide --> (contact/group view object)

        self.connect(self.ui.searchLine, SIGNAL('textChanged(QString)'), self._proxyModel, SLOT('setFilterFixedString(QString)'))
        QObject.connect(self.ui.nickName, SIGNAL('textChanged(QString)'), self.__slotChangeNick)
        self.connect(self.ui.cList, SIGNAL('doubleClicked(QModelIndex)'), self.__slotContactCallback)

    def show(self):
        self._mainWindow.fadeIn(self)

    def hide(self):
        pass

    def __slotChangeNick(self):
        sv = StringView()
        sv.appendText(str(self.ui.nickName.text()))
        self._amsn_core._profile.client.changeNick(sv)

    def __search_by_id(self, id):
        parent = self._model.item(0)

        while (parent is not None):
            obj = str(self._model.item(self._model.indexFromItem(parent).row(), 1).text())

            if (obj == id): return parent
            child = parent.child(0)
            nc = 0
            while (child is not None):
                cobj = str(parent.child(nc, 1).text())
                if (cobj == id): return child
                nc = nc + 1
                child = self._model.item(self._model.indexFromItem(parent).row()).child(nc)
            parent = self._model.item(self._model.indexFromItem(parent).row() + 1)
            if parent is None: break

        return None

    def contactListUpdated(self, view):
        guids = self.groups
        self.groups = []

        # New groups
        for gid in view.group_ids:
            if (gid == 0): gid = '0'
            if gid not in guids:
                self.groups.append(gid)
                self._model.appendRow([QStandardItem(gid), QStandardItem(gid), QStandardItem("group"), QStandardItem()])
        
        # Remove unused groups
        for gid in guids:
            if gid not in self.groups:
                gitem = self.__search_by_id(gid)
                self._model.removeRow((self._model.indexFromItem(gitem)).row())
                self.groups.remove(gid)

    def contactUpdated(self, contact):
        
        citem = self.__search_by_id(contact.uid)
        if citem is None: return

        gitem = citem.parent()
        if gitem is None: return

        dp = Image(self._parent._theme_manager, contact.dp)
        dp = dp.to_size(28, 28)
        #icon = Image(self._parent._theme_manager, contact.icon)

        gitem.child(self._model.indexFromItem(citem).row(), 0).setData(QVariant(dp), Qt.DecorationRole)
        #gitem.child(self._model.indexFromItem(citem).row(), 0).setData(QVariant(icon), Qt.DecorationRole)

        gitem.child(self._model.indexFromItem(citem).row(), 3).setData(QVariant(contact), Qt.DisplayRole)
        cname = StringView()
        cname = contact.name.toHtmlString()
        gitem.child(self._model.indexFromItem(citem).row(), 0).setText(QString.fromUtf8(cname))

    def groupUpdated(self, group):
        if (group.uid == 0): group.uid = '0'
        if group.uid not in self.groups: return
        
        gitem = self.__search_by_id(group.uid)
        self._model.item(self._model.indexFromItem(gitem).row(), 3).setData(QVariant(group), Qt.DisplayRole)
        gname = StringView()
        gname = group.name
        self._model.item((self._model.indexFromItem(gitem)).row(), 0).setText('<b>'+QString.fromUtf8(gname.toHtmlString())+'</b>')

        try:
            cuids = self.contacts[group.uid]
        except:
            cuids = []
        self.contacts[group.uid] = group.contact_ids.copy()

        for cid in group.contact_ids:
            if cid not in cuids:
                gitem = self.__search_by_id(group.uid)
                gitem.appendRow([QStandardItem(cid), QStandardItem(cid), QStandardItem("contact"), QStandardItem()])

        # Remove unused contacts
        for cid in cuids:
            if cid not in self.contacts[group.uid]:
                citem = self.__search_by_id(cid)
                self._model.removeRow((self._model.indexFromItem(citem)).row())

    def groupRemoved(self, group):
        gid = self.__search_by_id(group.uid)
        self._model.takeRow(self._model.indexFromItem(gid))

    def configure(self, option, value):
        pass

    def cget(self, option, value):
        pass

    def size_request_set(self, w,h):
        pass

    def __slotContactCallback(self, index):

        model = index.model()
        qvart = model.data(model.index(index.row(), 2, index.parent()))
        qvarv = model.data(model.index(index.row(), 3, index.parent()))

        type = qvart.toString()
        view = qvarv.toPyObject()

        #is the doble-clicked item a contact?
        if type == "contact":
            view.on_click(view.uid)
        else:
            print "Doble click on group!"

    def setContactContextMenu(self, cb):
        #TODO:
        pass

    def groupAdded(self, group):
        pi = self._model.invisibleRootItem()

        # Adding Group Item

        groupItem = QStandardItem()
        gname = StringView()
        gname = group.name
        self._model.item(groupItem.row(), 0).setText('<b>'+QString.fromUtf8(gname.toHtmlString())+'</b>')
        self._model.item(groupItem.row(), 1).setText(QString.fromUtf8(str(group.uid)))
        pi.appendRow(groupItem)

        for contact in group.contacts:
            contactItem = QStandardItem()
            cname = StringView()
            cname = contact.name
            self._model.item(contactItem.row(), 0).setText(QString.fromUtf8(cname.toHtmlString()))
            self._model.item(contactItem.row(), 1).setText(QString.fromUtf8(str(contact.uid)))

            groupItem.appendRow(contactItem)

            self._contactDict[contact.uid] = contact
########NEW FILE########
__FILENAME__ = fadingwidget

from PyQt4.QtCore import *
from PyQt4.QtGui import *

class FadingWidget(QWidget):
    def __init__(self, bgColor, parent=None):
        QWidget.__init__(self, parent)
        self._timeLine = QTimeLine(640) # Not too fast, not too slow...
        self._opacity = 0.0
        self._bgColor = bgColor
        QObject.connect(self._timeLine, SIGNAL("valueChanged(qreal)"), self.__setOpacity)
        QObject.connect(self._timeLine, SIGNAL("finished()"), self.__animCompleted)

    def __animCompleted(self):
        if self._opacity == 0.0:
            self.emit(SIGNAL("fadeInCompleted()"))
        elif self._opacity == 1.0:
            self.emit(SIGNAL("fadeOutCompleted()"))

    def fadeIn(self):
        self._timeLine.setDirection(QTimeLine.Backward)
        if self._timeLine.state() == QTimeLine.NotRunning:
            self._timeLine.start()

    def fadeOut(self):
        self._timeLine.setDirection(QTimeLine.Forward)
        if self._timeLine.state() == QTimeLine.NotRunning:
            self._timeLine.start()

    def __setOpacity(self, newOpacity):
        self._opacity = newOpacity
        self.update()

    def paintEvent(self, event):
        if self._opacity > 0.0:
            p = QPainter()
            p.begin(self)
            p.setBrush(self._bgColor)
            p.setOpacity(self._opacity)
            p.drawRect(self.rect())
            p.end()

########NEW FILE########
__FILENAME__ = image
# -*- coding: utf-8 -*-
#
# amsn - a python client for the WLM Network
#
# Copyright (C) 2008 Dario Freddi <drf54321@gmail.com>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA 02111-1307 USA

from amsn2.gui import base

from PyQt4.QtCore import *
from PyQt4.QtGui import *
from amsn2.core.views import imageview

class Image(QPixmap):
    def __init__(self, theme_manager, view):
        QPixmap.__init__(self)
        self._filename = ""
        self._theme_manager = theme_manager
        self.loader(view)

    def loader(self, view):
        i = 0
        for (resource_type, value) in view.imgs:
            try:
                loadMethod = getattr(self, "_loadFrom%s" % resource_type)
            except AttributeError, e:
                print "From load in qt4/image.py:\n\t(resource_type, value) = (%s, %s)\n\tAttributeError: %s" % (resource_type, value, e)
            else:
                loadMethod(value, view, i)
                i += 1            

    def _loadFromFilename(self, filename, view, index):
        # TODO: Implement support for emblems and other embedded images
        if (index != 0): return

        try:
            self.load(filename)
            self._filename = filename
        except Exception, e:
            print e
            print "Error loading image %s" % filename

    def _loadFromTheme(self, resource_name, view, index):
        # TODO: Implement support for emblems and other embedded images
        if (index != 0): return

        _, filename = self._theme_manager.get_value(resource_name)

        if filename is not None:
            self._loadFromFilename(filename, view, index)
        else:
            print 'Error loading image %s from theme' %resource_name

    def to_size(self, width, height):
        #print 'image.py -> to_pixbuf: filename=%s' % self._filename
        try:
            qpix = self.scaled(width, height)
            return qpix
        except:
            print 'Error converting to qpix image %s' % self._filename
            return None
        
    def _loadFromSkin(self, skin):
        pass

    def _loadFromFileObject(self, obj):
        pass

    def getAsFilename(self):
        return self._filename

    def append(self, resource_name, value):
        """ This method is used to overlap an image on the current image
        Have a look at the documentation of the 'load' method for the meanings of 'resource_name' and 'value'
        """
        if resource_name == "File":
            self.loader(value)

    def prepend(self, resource_name, value):
        """ This method is used to underlap an image under the current image
        Have a look at the documentation of the 'load' method for the meanings of 'resource_name' and 'value'
        """
        if resource_name == "File":
            self.loader(value)
########NEW FILE########
__FILENAME__ = login
# -*- coding: utf-8 -*-
from amsn2.gui import base
from amsn2.core.views import AccountView, ImageView

from PyQt4.QtCore import *
from PyQt4.QtGui import *
try:
    from ui_login import Ui_Login
except ImportError, e:
    print " WARNING: To use the QT4 you need to run the generateFiles.sh, check the README"
    raise e
from styledwidget import StyledWidget


class LoginThrobber(StyledWidget):
    def __init__(self, parent):
        StyledWidget.__init__(self, parent)
        # Throbber
        self.plsWait = QLabel(self)
        self.plsWait.setText("<strong>Please wait...</strong>")
        self.plsWait.setAlignment(Qt.AlignCenter)
        self.status = QLabel(self)
        self.status.setText("")
        self.status.setAlignment(Qt.AlignCenter)
        self.throbber = QLabel(self)
        self.movie = QMovie(self)
        self.movie.setFileName("amsn2/gui/front_ends/qt4/throbber.gif")
        self.movie.start()
        self.throbber.setMovie(self.movie)
        # Layout, for horizontal centering
        self.hLayout = QHBoxLayout()
        self.hLayout.addStretch()
        self.hLayout.addWidget(self.throbber)
        self.hLayout.addStretch()
        # Layout, for vertical centering
        self.vLayout = QVBoxLayout()
        self.vLayout.addStretch()
        self.vLayout.addLayout(self.hLayout)
        self.vLayout.addWidget(self.plsWait)
        self.vLayout.addWidget(self.status)
        self.vLayout.addStretch()
        # Top level layout
        self.setLayout(self.vLayout)
        # Apply StyleSheet
        self.setStyleSheet("background: white;")

class aMSNLoginWindow(StyledWidget, base.aMSNLoginWindow):
    def __init__(self, amsn_core, parent):
        StyledWidget.__init__(self, parent)
        self._amsn_core = amsn_core
        self.ui = Ui_Login()
        self.ui.setupUi(self)
        self._parent = parent
        QObject.connect(self.ui.pushSignIn, SIGNAL("clicked()"), self.signin)
        QObject.connect(self.ui.styleDesktop, SIGNAL("clicked()"), self.setTestStyle)
        QObject.connect(self.ui.styleRounded, SIGNAL("clicked()"), self.setTestStyle)
        QObject.connect(self.ui.styleWLM, SIGNAL("clicked()"), self.setTestStyle)
        QObject.connect(self.ui.checkRememberMe, SIGNAL("toggled(bool)"), self.__on_toggled_cb)
        QObject.connect(self.ui.checkRememberPass, SIGNAL("toggled(bool)"), self.__on_toggled_cb)
        QObject.connect(self.ui.checkSignInAuto, SIGNAL("toggled(bool)"), self.__on_toggled_cb)
        self.setTestStyle()

        # status list
        self.status_values = {}
        self.status_dict = {}
        status_n = 0
        for key in self._amsn_core.p2s:
            name = self._amsn_core.p2s[key]
            if (name == 'offline'): continue
            self.status_values[name] = status_n
            self.status_dict[str.capitalize(name)] = name
            status_n = status_n +1
            self.ui.comboStatus.addItem(str.capitalize(name))

    def setTestStyle(self):
        styleData = QFile()
        if self.ui.styleDesktop.isChecked() == True:
            styleData.setFileName("amsn2/gui/front_ends/qt4/style0.qss")
        elif self.ui.styleWLM.isChecked() == True:
            styleData.setFileName("amsn2/gui/front_ends/qt4/style1.qss")
        elif self.ui.styleRounded.isChecked() == True:
            styleData.setFileName("amsn2/gui/front_ends/qt4/style2.qss")
        if styleData.open(QIODevice.ReadOnly|QIODevice.Text):
            styleReader = QTextStream(styleData)
            self.setStyleSheet(styleReader.readAll())

    def show(self):
        self._parent.fadeIn(self)

    def hide(self):
        pass

    def setAccounts(self, accountviews):
        self._account_views = accountviews

        for accv in self._account_views:
            self.ui.comboAccount.addItem(accv.email)

        if len(accountviews)>0 :
            # first in the list, default
            self.__switch_to_account(self._account_views[0].email)

            if self._account_views[0].autologin:
                self.signin()


    def __switch_to_account(self, email):

        accv = self.getAccountViewFromEmail(email)

        if accv is None:
            accv = AccountView(self._amsn_core, email)

        self.ui.comboAccount.setItemText(0, accv.email)

        if accv.password:
            self.ui.linePassword.clear()
            self.ui.linePassword.insert(accv.password)

        self.ui.checkRememberMe.setChecked(accv.save)
        self.ui.checkRememberPass.setChecked(accv.save_password)
        self.ui.checkSignInAuto.setChecked(accv.autologin)

    def signin(self):
        self.loginThrobber = LoginThrobber(self)
        self._parent.fadeIn(self.loginThrobber)

        email = self.ui.comboAccount.currentText()
        accv = self.getAccountViewFromEmail(str(email))

        if accv is None:
            accv = AccountView(self._amsn_core, str(email))

        accv.password = self.ui.linePassword.text().toLatin1().data()
        accv.presence = self.status_dict[str(self.ui.comboStatus.currentText())]

        accv.save = self.ui.checkRememberMe.isChecked()
        accv.save_password = self.ui.checkRememberPass.isChecked()
        accv.autologin = self.ui.checkSignInAuto.isChecked()

        self._amsn_core.signinToAccount(self, accv)

    def onConnecting(self, progress, message):
        self.loginThrobber.status.setText(str(message))

    def __on_toggled_cb(self, bool):
        email = str(self.ui.comboAccount.currentText())
        accv = self.getAccountViewFromEmail(email)

        if accv is None:
            accv = AccountView(self._amsn_core, email)

        sender = self.sender()
        #just like wlm :)
        if sender == self.ui.checkRememberMe:
            accv.save = bool
            if not bool:
                self.ui.checkRememberPass.setChecked(False)
                self.ui.checkSignInAuto.setChecked(False)
        elif sender == self.ui.checkRememberPass:
            accv.save_password = bool
            if bool:
                self.ui.checkRememberMe.setChecked(True)
            else:
                self.ui.checkSignInAuto.setChecked(False)
        elif sender == self.ui.checkSignInAuto:
            accv.autologin = bool
            if bool:
                self.ui.checkRememberMe.setChecked(True)
                self.ui.checkRememberPass.setChecked(True)


########NEW FILE########
__FILENAME__ = main
# -*- coding: utf-8 -*-
#
# amsn - a python client for the WLM Network
#
# Copyright (C) 2008 Dario Freddi <drf54321@gmail.com>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA

from amsn2.gui import base

from PyQt4.QtCore import *
from PyQt4.QtGui import *
from fadingwidget import FadingWidget
from amsn2.core.views import MenuView, MenuItemView

class aMSNMainWindow(QMainWindow, base.aMSNMainWindow):
    def __init__(self, amsn_core, parent=None):
        QMainWindow.__init__(self, parent)
        self._amsn_core = amsn_core
        self.centralWidget = QWidget(self)
        self.stackedLayout = QStackedLayout()
        #self.stackedLayout.setStackingMode(QStackedLayout.StackAll)
        self.centralWidget.setLayout(self.stackedLayout)
        self.setCentralWidget(self.centralWidget)
        self.opaqLayer = FadingWidget(Qt.white, self)
        self.stackedLayout.addWidget(self.opaqLayer)
        QObject.connect(self.opaqLayer, SIGNAL("fadeInCompleted()"), self.__activateNewWidget)
        QObject.connect(self.opaqLayer, SIGNAL("fadeOutCompleted()"), self.__fadeIn)
        self.resize(230, 550)

    def closeEvent(self, event):
        self._amsn_core.quit()

    def fadeIn(self, widget):
        widget.setAutoFillBackground(True)
        self.stackedLayout.addWidget(widget)
        self.stackedLayout.setCurrentWidget(self.opaqLayer)
        # Is there another widget in here?
        if self.stackedLayout.count() > 2:
            self.opaqLayer.fadeOut() # Fade out current active widget
        else:
            self.__fadeIn()

    def __fadeIn(self):
        # Delete old widget(s)
        while self.stackedLayout.count() > 2:
            widget = self.stackedLayout.widget(1)
            self.stackedLayout.removeWidget(widget)
            widget.deleteLater()
        self.opaqLayer.fadeIn()

    def __activateNewWidget(self):
        self.stackedLayout.setCurrentIndex(self.stackedLayout.count()-1)

    def show(self):
        self.setVisible(True)
        self._amsn_core.mainWindowShown()

    def hide(self):
        self.setVisible(False)

    def setTitle(self, title):
        self.setWindowTitle(title)

    def set_view(self, view):
        print "set_view request"

    def setMenu(self, menu):
        mb = QMenuBar()

        for item in menu.items:
            if item.type == "cascade":
                menu = mb.addMenu(item.label)
                for subitem in item.items:
                    menu.addAction(subitem.label)

        self.setMenuBar(mb)

########NEW FILE########
__FILENAME__ = main_loop
from amsn2.gui import base
import sys

from PyQt4.QtCore import *
from PyQt4.QtGui import *
import gobject

class aMSNMainLoop(base.aMSNMainLoop):
    def __init__(self, amsn_core):
        import os
        os.putenv("QT_NO_GLIB", "1") # FIXME: Temporary workaround for segfault
                                     #        caused by GLib Event Loop integration
        self.app = QApplication(sys.argv)
        self.gmainloop = gobject.MainLoop()
        self.gcontext = self.gmainloop.get_context()

    def __del__(self):
        self.gmainloop.quit()

    def run(self):
        self.idletimer = QTimer(QApplication.instance())
        QObject.connect(self.idletimer, SIGNAL('timeout()'), self.on_idle)
        self.idletimer.start(100)
        self.app.exec_()

    def on_idle(self):
        iter = 0
        while iter < 10 and self.gcontext.pending():
            self.gcontext.iteration()
            iter += 1

    def idlerAdd(self, func):
        print "idlerAdd req"
        pass

    def timerAdd(self, delay, func):
        print "timerAdd req"
        pass

    def quit(self):
        pass

########NEW FILE########
__FILENAME__ = qt4
# -*- coding: utf-8 -*-
from main_loop import *
from main import *
from contact_list import *
from login import *
from image import *
from splash import *
from skins import *
from chat_window import *

########NEW FILE########
__FILENAME__ = skins
# -*- coding: utf-8 -*-
#
# amsn - a python client for the WLM Network
#
# Copyright (C) 2008 Dario Freddi <drf54321@gmail.com>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA

import os.path
from amsn2.gui import base

class Skin(base.Skin):
    def __init__(self, core, path):
        self._path = path
        pass

    def getKey(self, key, default):
        pass

    def setKey(self, key, value):
        pass



class SkinManager(base.SkinManager):
    def __init__(self, core):
        self._core = core
        self.skin = Skin(core, "skins")

    def setSkin(self, name):
        self.skin = Skin(self._core, os.path.join("skins", name))

    def listSkins(self, path):
        pass

########NEW FILE########
__FILENAME__ = splash
# -*- coding: utf-8 -*-
#
# amsn - a python client for the WLM Network
#
# Copyright (C) 2008 Dario Freddi <drf54321@gmail.com>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA

from amsn2.gui import base

from PyQt4.QtCore import *
from PyQt4.QtGui import *
from fadingwidget import FadingWidget
from image import *

class aMSNSplashScreen(QSplashScreen, base.aMSNSplashScreen):

    def __init__(self, amsn_core, parent):
        QSplashScreen.__init__(self, parent)
        self._theme_manager = amsn_core._theme_manager

    def show(self):
        self.setVisible(True)
        qApp.processEvents()

    def hide(self):
        self.setVisible(False)
        qApp.processEvents()

    def setText(self, text):
        self.showMessage(text)
        qApp.processEvents()

    def setImage(self, image):
        img = Image(self._theme_manager, image)
        self.setPixmap(img)
        qApp.processEvents()

########NEW FILE########
__FILENAME__ = styledwidget

from PyQt4.QtCore import *
from PyQt4.QtGui import *
from fadingwidget import FadingWidget

# Styled Widget: QWidget subclass that directly supports Qt StyleSheets
class StyledWidget(QWidget):
    def __init__(self, parent=None):
        QWidget.__init__(self, parent)

    # Needed to support StyleSheets on pure subclassed QWidgets
    # See: http://doc.trolltech.com/4.4/stylesheet-reference.html
    def paintEvent(self, event):
        opt = QStyleOption()
        opt.init(self)
        p = QPainter(self)
        self.style().drawPrimitive(QStyle.PE_Widget, opt, p, self)

########NEW FILE########
__FILENAME__ = bend

# This is the main comunication module, all comunication to the JS frontend will be issued from here

class Backend(object):
    def __init__(self,In,Out):
        self.listeners = {}
        self._in = open(In, "r+")
        self._out = open(Out,"a")

    def addListener(self,event,listener):
        # The backend sets a listener to an event
        if not self.listeners.has_key(event):
            self.listeners[event] = []
        self.listeners[event].append(listener)

    def checkEvent(self):
        # This function is called to check for events in the file
        try:
            # one event per line, divided by columns divided by tab
            # the first column is the event, the next columns are the arguments
            eventDesc=self._in.readline()
            while len(eventDesc) > 0:
                try:
                    eventDesc = eventDesc.strip().split("\t")
                    eventName = eventDesc.pop(0)
                    realValues = []
                    for value in eventDesc:
                        realValues.append(str(value).decode('string_escape'))
                    if eventName is not "":
                        self.event(eventName,realValues)
                except:
                     # event problem.. probably a badly encoded string
                     break
                eventDesc=self._in.readline()
        except:
            # problem with lines (maybe empty file)
            pass
        # Return true to continue checking events
        return True

    def event(self,event,values):
        # The JS client sent a message to the backend
        # select the function to call depending on the type of event
        if self.listeners[event] is not None:
            for func in self.listeners[event]:
                try:
                    # if the function returns false, then it means it doesnt want to be called again
                    if not func(values):
                        self.listeners[event].remove(func)
                except:
                    pass

    def send(self,event,values):
        # The backend sent a message to the JS client
        # select the JS function to call depending on the type of event
        call = event + "(["
        for value in values:
            call += "'"+str(value).encode('string_escape')+"',"
        call=call.rstrip(",")+"]);"
        try:
           self._out.write(call)
           self._out.flush()
        except:
           pass

########NEW FILE########
__FILENAME__ = chat_window
import md5
import random
from amsn2.core.views import ContactView, StringView

class aMSNChatWindow(object):
    """ This interface will represent a chat window of the UI
        It can have many aMSNChatWidgets"""
    def __init__(self, amsn_core):
        self._amsn_core = amsn_core
        self._uid = md5.new(str(random.random())).hexdigest()
        self._main = amsn_core._core._main
        self._main.send("newChatWindow",[self._uid])

    def addChatWidget(self, chat_widget):
        """ add an aMSNChatWidget to the window """
        self._main.send("addChatWidget",[self._uid,chat_widget._uid])

    def show(self):
        self._main.send("showChatWindow",[self._uid])

    def hide(self):
        self._main.send("hideChatWindow",[self._uid])

    def add(self):
        print "aMSNChatWindow.add"
        pass

    def move(self):
        print "aMSNChatWindow.move"
        pass

    def remove(self):
        print "aMSNChatWindow.remove"
        pass

    def attach(self):
        print "aMSNChatWindow.attach"
        pass

    def detach(self):
        print "aMSNChatWindow.detach"
        pass

    def close(self):
        print "aMSNChatWindow.close"
        pass

    def flash(self):
        print "aMSNChatWindow.flash"
        pass
    """TODO: move, remove, detach, attach (shouldn't we use add ?), close,
        flash..."""


class aMSNChatWidget(object):
    """ This interface will present a chat widget of the UI """
    def __init__(self, amsn_conversation, parent, contacts_uid):
        """ create the chat widget for the 'parent' window, but don't attach to
        it."""
        self._main=parent._main
        self._uid=md5.new(str(random.random())).hexdigest()
        self._main.send("newChatWidget",[self._uid])
        self._main.addListener("sendMessage",self.sendMessage)
        self._amsn_conversation=amsn_conversation

    def sendMessage(self,smL):
        if smL[0]==self._uid:
            stmess = StringView()
            stmess.appendText(smL[1])
            self._amsn_conversation.sendMessage(stmess)
        return True



    def onMessageReceived(self, messageview):
        """ Called for incoming and outgoing messages
            message: a MessageView of the message"""
        self._main.send("onMessageReceivedChatWidget", [self._uid, str(messageview.toStringView())])

    def nudge(self):
        self._main.send("nudgeChatWidget",[self._uid])


########NEW FILE########
__FILENAME__ = contact_list
"""TODO:
    * Let the aMSNContactListWidget be selectable to choose contacts to add to a
    conversation... each contact should have a checkbox on front of it
    * Drag contacts through groups
    * Drag groups
    ...
"""


class aMSNContactListWindow(object):
    """ This interface represents the main Contact List Window
        self._clwiget is an aMSNContactListWidget 
    """

    def __init__(self, amsn_core, parent):
        self._main = parent
        self._clwiget = aMSNContactListWidget(amsn_core,self)
        pass

    def show(self):
        """ Show the contact list window """
        self._main.send("showContactListWindow",[])
        pass

    def hide(self):
        """ Hide the contact list window """
        self._main.send("hideContactListWindow",[])
        pass

    def setTitle(self, text):
        """ This will allow the core to change the current window's title
        @text : a string
        """
        self._main.send("setContactListTitle",[text])
        pass

    def setMenu(self, menu):
        """ This will allow the core to change the current window's main menu
        @menu : a MenuView
        """
        self._main.send("setMenu")
        pass

    def myInfoUpdated(self, view):
        """ This will allow the core to change pieces of information about
        ourself, such as DP, nick, psm, the current media being played,...
        @view: the contactView of the ourself (contains DP, nick, psm,
        currentMedia,...)"""
        self._main.send("myInfoUpdated",[str(view.name)])
        pass

class aMSNContactListWidget(object):
    """ This interface implements the contact list of the UI """
    def __init__(self, amsn_core, parent):
        self._main = parent._main
        self.contacts = {}
        self.groups = {}
        self._main.addListener("contactClicked",self.contactClicked)
        clm = amsn_core._contactlist_manager
        clm.register(clm.CLVIEW_UPDATED, self.contactListUpdated)
        clm.register(clm.GROUPVIEW_UPDATED, self.groupUpdated)
        clm.register(clm.CONTACTVIEW_UPDATED, self.contactUpdated)
        
    def contactClicked(self,uidL):
        uid = uidL.pop()
        try:
            self.contacts[uid].on_click(uid)
        except Exception, inst:
            print inst
        return True

    def show(self):
        """ Show the contact list widget """
        self._main.send("showContactListWidget",[])
        pass

    def hide(self):
        """ Hide the contact list widget """
        self._main.send("hideContactListWidget",[])
        pass

    def contactListUpdated(self, clView):
        """ This method will be called when the core wants to notify
        the contact list of the groups that it contains, and where they
        should be drawn a group should be drawn.
        It will be called initially to feed the contact list with the groups
        that the CL should contain.
        It will also be called to remove any group that needs to be removed.
        @cl : a ContactListView containing the list of groups contained in
        the contact list which will contain the list of ContactViews
        for all the contacts to show in the group."""
        self._main.send("contactListUpdated",clView.group_ids)
        pass

    def groupUpdated(self, groupView):
        """ This method will be called to notify the contact list
        that a group has been updated.
        The contact list should update its icon and name
        but also its content (the ContactViews). The order of the contacts
        may be changed, in which case the UI should update itself accordingly.
        A contact can also be added or removed from a group using this method
        """
        self.groups[groupView.uid]=groupView
        self._main.send("groupUpdated",[groupView.uid,",".join(groupView.contact_ids),str(groupView.name)])
        pass

    def contactUpdated(self, contactView):
        """ This method will be called to notify the contact list
        that a contact has been updated.
        The contact can be in any group drawn and his icon,
        name or DP should be updated accordingly.
        The position of the contact will not be changed by a call
        to this function. If the position was changed, a groupUpdated
        call will be made with the new order of the contacts
        in the affects groups.
        """
        self.contacts[contactView.uid]=contactView
        self._main.send("contactUpdated", [contactView.uid, str(contactView.name)])
        pass


########NEW FILE########
__FILENAME__ = login
class aMSNLoginWindow(object):
    def __init__(self, amsn_core, main):
        self._main = main
        self._amsn_core = amsn_core
        self.switch_to_profile(None)

    def show(self):
        self._main.send("showLogin",[]);
        self._main.addListener("setUsername",self.setUsername)
        self._main.addListener("setPassword",self.setPassword)
        self._main.addListener("signin",self.signin)

    def hide(self):
        self._main.send("hideLogin",[]);

    def setUsername(self,listU):
        self._username = listU.pop()

    def setPassword(self,listP):
        self._password = listP.pop()

    def switch_to_profile(self, profile):
        self.current_profile = profile
        if self.current_profile is not None:
            self._username = self.current_profile.username
            self._password = self.current_profile.password

    def signin(self,listE):
        self.current_profile.username = self._username
        self.current_profile.email = self._username
        self.current_profile.password = self._password
        self._amsn_core.signinToAccount(self, self.current_profile)

    def onConnecting(self,mess):
        self._main.send("onConnecting",[mess])

########NEW FILE########
__FILENAME__ = main

from amsn2.gui import base
from bend import Backend
import os

class aMSNMainWindow(base.aMSNMainWindow,Backend):
    def __init__(self, amsn_core):
        try:
            os.remove("/tmp/test.in")
        except:
            pass
        try:
            os.remove("/tmp/test.out")
        except:
            pass
        open("/tmp/test.in","w").close()
        open("/tmp/test.out","w").close()
        os.chmod("/tmp/test.in",0666)
        os.chmod("/tmp/test.out",0666)
        Backend.__init__(self,"/tmp/test.in","/tmp/test.out")
        self._amsn_core = amsn_core
        self._amsn_core.timerAdd(1,self.checkEvent)

    def show(self):
        self.send("showMainWindow",[])
        self._amsn_core.idlerAdd(self.__on_show)

    def hide(self):
        self.send("hideMainWindow",[])
        pass

    def setTitle(self,title):
        self.send("setMainWindowTitle",[title])
        pass

    def setMenu(self,menu):
        print "aMSNMainWindow.setMenu"
        pass

    def __on_show(self):
        self._amsn_core.mainWindowShown()

########NEW FILE########
__FILENAME__ = main_loop

from amsn2.gui import base
import gobject

class aMSNMainLoop(base.aMSNMainLoop):
    def __init__(self, amsn_core):
        self._amsn_core = amsn_core

    def run(self):
        self._mainloop = gobject.MainLoop(is_running=True)
        while self._mainloop.is_running():
            try:
                self._mainloop.run()
            except KeyboardInterrupt:
                self.quit()


    def idlerAdd(self, func):
        gobject.idle_add(func)

    def timerAdd(self, delay, func):
        gobject.timeout_add(delay, func)

    def quit(self):
        self._mainloop.quit()


########NEW FILE########
__FILENAME__ = skins
import os.path
from amsn2.gui import base

class Skin(base.Skin):
    def __init__(self, core, path):
        self._path = path
        pass

    def getKey(self, key, default):
        pass

    def setKey(self, key, value):
        pass



class SkinManager(base.SkinManager):
    def __init__(self, core):
        self._core = core
        self.skin = Skin(core, "skins")

    def setSkin(self, name):
        self.skin = Skin(self._core, os.path.join("skins", name))

    def listSkins(self, path):
        pass

########NEW FILE########
__FILENAME__ = splash

class aMSNSplashScreen(object):
    """ This interface will represent the splashscreen of the UI"""
    def __init__(self, amsn_core, parent):
        """Initialize the interface. You should store the reference to the core in here
        as well as a reference to the window where you will show the splash screen
        """
        self._amsn_core=amsn_core
        self._main=parent
        pass

    def show(self):
        """ Draw the splashscreen """
        self._main.send("showSplashScreen",[])
        pass

    def hide(self):
        """ Hide the splashscreen """
        self._main.send("hideSplashScreen",[])
        pass

    def setText(self, text):
        """ Shows a different text inside the splashscreen """
        self._main.send("setTextSplashScreen",[text])
        pass

    def setImage(self, image):
        """ Set the image to show in the splashscreen. This is an ImageView object """
        self._main.send("setImageSplashScreen",["..."])
        pass




########NEW FILE########
__FILENAME__ = web
from bend import *
from main_loop import *
from main import *
from contact_list import *
from login import *
from splash import *
from skins import *
from chat_window import *

########NEW FILE########
__FILENAME__ = window

class aMSNWindow(object):
    """ This Interface represents a window of the application. Everything will be done from here """
    def __init__(self, amsn_core):
        pass

    def show(self):
        """ This launches the window, creates it, etc.."""
        print "aMSNWindow.show"
        pass

    def hide(self):
        """ This should hide the window"""
        print "aMSNWindow.hide"
        pass

    def setTitle(self, text):
        """ This will allow the core to change the current window's title
        @text : a string
        """
        print "aMSNWindow.setTitle"
        pass

    def setMenu(self, menu):
        """ This will allow the core to change the current window's main menu
        @menu : a MenuView
        """
        print "aMSNWindow.setMenu"
        pass

########NEW FILE########
__FILENAME__ = gui

class InvalidFrontEndException(Exception):
    def __init__(self, message):
        Exception.__init__(self)
        self.message = message

    def __str__(self):
        return str(self.message)


class GUIManager(object):
    front_ends = {}

    def __init__(self, core, gui_name):
        """
        @type core: aMSNCore
        @type gui_name: str
        """

        self._core = core
        self._name = gui_name
   		
        if GUIManager.frontEndExists(self._name) is False:
            raise InvalidFrontEndException("Invalid Front End. Available front ends are : " + str(GUIManager.listFrontEnds()))
        else:
            self.gui = GUIManager.front_ends[self._name]
            self.gui = self.gui.load()

    @staticmethod
    def registerFrontEnd(name, module):
        GUIManager.front_ends[name] = module

    @staticmethod
    def listFrontEnds():
        return GUIManager.front_ends.keys()

    @staticmethod
    def frontEndExists(front_end):
        return front_end in GUIManager.listFrontEnds()


########NEW FILE########
__FILENAME__ = autoupdate
# checkForUpdate(plugin_obj)
# Check's the plugin's files for any updates.
def checkForUpdate(plugin_obj): pass

########NEW FILE########
__FILENAME__ = core
# plugins module for amsn2
"""
Plugins with amsn2 will be a subclass of the aMSNPlugin() class.
When this module is initially imported it should load the plugins from the last session. Done in the init() proc.
Then the GUI should call plugins.loadPlugin(name) or plugins.unLoadPlugin(name) in order to deal with plugins.
"""

# init()
# Called when the plugins module is imported (only for the first time).
# Should find plugins and populate a list ready for getPlugins().
# Should also auto-update all plugins.
def init(): pass

# loadPlugin(plugin_name)
# Called (by the GUI or from init()) to load a plugin. plugin_name as set in plugin's XML (or from getPlugins()).
# This loads the module for the plugin. The module is then responsible for calling plugins.registerPlugin(instance).
def loadPlugin(plugin_name): pass

# unLoadPlugin(plugin_name)
# Called to unload a plugin. Name is name as set in plugin's XML.
def unLoadPlugin(plugin_name): pass

# registerPlugin(plugin_instance)
# Saves the instance of the plugin, and registers it in the loaded list.
def registerPlugin(plugin_instance): pass

# getPlugins()
# Returns a list of all available plugins, as in ['Plugin 1', 'Plugin 2']
def getPlugins(): pass

# getPluginsWithStatus()
# Returns a list with a list item for each plugin with the plugin's name, and Loaded or NotLoaded either way.
# IE: [['Plugin 1', 'Loaded'], ['Plugin 2', 'NotLoaded']]
def getPluginsWithStatus(): pass

# getLoadedPlugins()
# Returns a list of loaded plugins. as in ['Plugin 1', 'Plugin N']
def getLoadedPlugins(): pass

# findPlugin(plugin_name)
# Retruns the running instance of the plugin with name plugin_name, or None if not found.
def findPlugin(plugin_name): pass

# saveConfig(plugin_name, data)
def saveConfig(plugin_name, data): pass

# Calls the init procedure.
# Will only be called on the first import (thanks to python).
init()

########NEW FILE########
__FILENAME__ = developers
# aMSNPlugin(object)
# Plugin developers should subclass this class in order to register themselves when called by the loadPlugin(plugin_name) proc.
# that.load() will be called when the plugin has been registered by calling plugins.registerPlugin(plugin_obj).
# that.unload() will be called when the plugin is unloaded or the client quits.
# To register for an event call self.registerForEvent(event, callback)
# To de-register call self.unRegisterForEvent(event)
class aMSNPlugin(object):
    # These are called when the plugin is loaded or un-loaded.
    def load(self):
        pass
    def unload(self):
        pass

    # Used to access the _name or _dir private variables.
    def getName(self):
        return str(self._name)
    def getDir(self):
        return str(self._dir)

    # Used to log data.
    def log(self, message):
        plugins.log(self._name, message)

    # Used to register/de-register for events.
    def registerForEvent(self, event, callback):
        pass
    def unRegisterForEvent(self, event):
        pass

########NEW FILE########
__FILENAME__ = gui
import plugins

class aMSNPluginSelectorWindow(object):
    def drawWindow(self):
        pass
    def showWindow(self):
        pass
    def closeWindow(self):
        pass
    def getPlugins(self):
        return plugins.getPlugins()
    def getPluginsWithStatus(self):
        return plugins.getPluginsWithStatus()
    def loadPlugin(self, plugin_name):
        pass
    def unLoadPlugin(self, plugin_name):
        pass
    def configurePlugin(self, plugin_name):
        pass

class aMSNPluginConfigurationWindow(object):
    # __init__(self, plugin_name)
    # Calls plugins.findPlugin(plugin_name) to get a plugin.
    # If the plugin is found and is loaded then save an instance of it in self._plugin.
    # We cannot configure unloaded plugins so do not show the window if the plugin isn't found.
    # Then draw the window and show it.
    def __init__(self, plugin_name):
        pass

    # drawWindow(self)
    # Handles pre-loading the window contents before the window is shown.
    def drawWindow(self):
        pass

    # showWindow(self)
    # If the window is drawn then simply show the window.
    def showWindow(self):
        pass

    # closeWindow(self)
    # Handles closing the window. Shouldn't just hide it.
    def closeWindow(self):
        pass

    # getConfig(self)
    # Returns a copy of the plugins config as a keyed array.
    def getConfig(self):
        pass

    # saveConfig(self): pass
    # Saves the config via plugins.saveConfig(plugin_name, data)
    def saveConfig(self, config):
        pass

########NEW FILE########
__FILENAME__ = client
# -*- coding: utf-8 -*-
#
# amsn - a python client for the WLM Network
#
# Copyright (C) 2008 Dario Freddi <drf54321@gmail.com>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA

import papyon
import papyon.event
from events.client import *
from events.contact import *
from events.invite import *
from events.oim import *
from events.addressbook import *
from events.profile import *
from events.mailbox import *

class Client(papyon.Client):
    def __init__(self, amsn_core, account):
        self._amsn_account = account
        self._amsn_core = amsn_core
        server = (self._amsn_account.config.getKey("ns_server", "messenger.hotmail.com"),
                  self._amsn_account.config.getKey("ns_port", 1863))
        papyon.Client.__init__(self, server)

        self._client_events_handler = ClientEvents(self, self._amsn_core)
        self._contact_events_handler = ContactEvents(self, self._amsn_core._contactlist_manager)
        self._invite_events_handler = InviteEvents(self, self._amsn_core)
        self._oim_events_handler = OIMEvents(self, self._amsn_core._oim_manager)
        self._addressbook_events_handler = AddressBookEvents(self, self._amsn_core)
        self._profile_events_handler = ProfileEvents(self, self._amsn_core._personalinfo_manager)
        self._mailbox_events_handler = MailboxEvents(self, self._amsn_core)

    def connect(self, email, password):
        self.login(email, password)

    def changeNick(self, nick):
        self.profile.display_name = str(nick)

    def changeMessage(self, message):
        self.profile.personal_message = str(message)

########NEW FILE########
__FILENAME__ = addressbook
# -*- coding: utf-8 -*-
#
# amsn - a python client for the WLM Network
#
# Copyright (C) 2008 Dario Freddi <drf54321@gmail.com>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA

import papyon
import papyon.event

class AddressBookEvents(papyon.event.AddressBookEventInterface):
    def __init__(self, client, amsn_core):
        self._amsn_core = amsn_core
        self._contactlist_manager = amsn_core._contactlist_manager
        papyon.event.AddressBookEventInterface.__init__(self, client)

    def on_addressbook_messenger_contact_added(self, contact):
        self._contactlist_manager.onContactAdded(contact)

    def on_addressbook_contact_deleted(self, contact):
        self._contactlist_manager.onContactRemoved(contact)

    def on_addressbook_contact_blocked(self, contact):
        pass

    def on_addressbook_contact_unblocked(self, contact):
        pass

    def on_addressbook_group_added(self, group):
        pass

    def on_addressbook_group_deleted(self, group):
        pass

    def on_addressbook_group_renamed(self, group):
        pass

    def on_addressbook_group_contact_added(self, group, contact):
        pass

    def on_addressbook_group_contact_deleted(self, group, contact):
        pass


########NEW FILE########
__FILENAME__ = client

import papyon
import papyon.event


class ClientEvents(papyon.event.ClientEventInterface):
    def __init__(self, client, amsn_core):
        self._amsn_core = amsn_core
        papyon.event.ClientEventInterface.__init__(self, client)

    def on_client_state_changed(self, state):
        self._amsn_core.connectionStateChanged(self._client._amsn_account, state)

    def on_client_error(self, error_type, error):
        print "ERROR :", error_type, " ->", error



########NEW FILE########
__FILENAME__ = contact

import papyon
import papyon.event

class ContactEvents(papyon.event.ContactEventInterface):

    def __init__(self, client, contact_manager):
        self._contact_manager = contact_manager
        papyon.event.ContactEventInterface.__init__(self, client)

    def on_contact_presence_changed(self, contact):
        self._contact_manager.onContactChanged(contact)

    def on_contact_display_name_changed(self, contact):
        self._contact_manager.onContactChanged(contact)

    def on_contact_personal_message_changed(self, contact):
        self._contact_manager.onContactChanged(contact)

    def on_contact_current_media_changed(self, contact):
        self._contact_manager.onContactChanged(contact)

    def on_contact_msn_object_changed(self, contact):
        # if the msnobject has been removed, just remove the buddy's DP
        if contact.msn_object is None: 
            self._contact_manager.onContactDPChanged(contact)
            return

        # TODO: filter objects
        if contact.msn_object._type is papyon.p2p.MSNObjectType.DISPLAY_PICTURE:
            self._contact_manager.onContactDPChanged(contact)

    def on_contact_memberships_changed(self, contact):
        pass

    def on_contact_infos_changed(self, contact, infos):
        pass

    def on_contact_client_capabilities_changed(self, contact):
        pass


########NEW FILE########
__FILENAME__ = conversation
# -*- coding: utf-8 -*-
#
# amsn - a python client for the WLM Network
#
# Copyright (C) 2008 Dario Freddi <drf54321@gmail.com>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA

from amsn2.core.views import *
import papyon
import papyon.event


class ConversationEvents(papyon.event.ConversationEventInterface):
    def __init__(self, amsn_conversation):
        self._amsn_conversation = amsn_conversation
        self._conversation = amsn_conversation._conv
        papyon.event.ConversationEventInterface.__init__(self, self._conversation)

    def on_conversation_state_changed(self, state):
        self._amsn_conversation.onStateChanged(state)

    def on_conversation_error(self, type, error):
        self._amsn_conversation.onError(type, error)

    def on_conversation_user_joined(self, contact):
        self._amsn_conversation.onUserJoined(contact.id)

    def on_conversation_user_left(self, contact):
        self._amsn_conversation.onUserLeft(contact.id)

    def on_conversation_user_typing(self, contact):
        self._amsn_conversation.onUserTyping(contact.id)

    def on_conversation_message_received(self, sender, message):
        """ Powers of the stringview, here we come! We need to parse the message,
        that could actually contain some emoticons. In that case, we simply replace
        them into the stringview """
        #TODO: have Smiley object in the stringView to keep image+trigger
        strv = StringView()
        if message.content in message.msn_objects.keys():
            print "single emoticon"
            strv.appendImage(message.msn_objects[message.content]._location)
            self._amsn_conversation.onMessageReceived(strv, sender.id)
            return

        strlist = [message.content]

        for smile in message.msn_objects.keys():
            newlist = []
            for str in strlist:
                li = str.split(smile)
                for part in li:
                    newlist.append(part)
                    newlist.append(message.msn_objects[smile]._location)
                newlist.pop()

            strlist = newlist

        for str in strlist:
            if str in message.msn_objects.keys():
                strv.appendImage(str)
            else:
                strv.appendText(str)

        self._amsn_conversation.onMessageReceived(strv, sender.id, message.formatting)

    def on_conversation_nudge_received(self, sender):
        self._amsn_conversation.onNudgeReceived(sender.id)


########NEW FILE########
__FILENAME__ = invite


import papyon
import papyon.event

class InviteEvents(papyon.event.InviteEventInterface):

    def __init__(self, client, amsn_core):
        self._amsn_core = amsn_core
        papyon.event.InviteEventInterface.__init__(self, client)

    def on_invite_conversation(self, conversation):
        self._amsn_core._conversation_manager.onInviteConversation(conversation)

########NEW FILE########
__FILENAME__ = mailbox

import papyon
import papyon.event

class MailboxEvents(papyon.event.MailboxEventInterface):
    def __init__(self, client, amsn_core):
        self._amsn_core = amsn_core
        papyon.event.MailboxEventInterface.__init__(self, client)

    def on_mailbox_unread_mail_count_changed(self, unread_mail_count,
                                                   initial=False):
        """The number of unread mail messages"""
        pass

    def on_mailbox_new_mail_received(self, mail_message):
        """New mail message notification"""
        pass

########NEW FILE########
__FILENAME__ = oim
# -*- coding: utf-8 -*-
#
# amsn - a python client for the WLM Network
#
# Copyright (C) 2008 Dario Freddi <drf54321@gmail.com>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA

import papyon
import papyon.event

class OIMEvents(papyon.event.OfflineMessagesEventInterface):
    def __init__(self, client, oim_manager):
        self._oim_manager = oim_manager
        papyon.event.OfflineMessagesEventInterface.__init__(self, client)

    def on_oim_state_changed(self, state):
        pass

    def on_oim_messages_received(self, messages):
        pass

    def on_oim_messages_fetched(self, messages):
        pass

    def on_oim_messages_deleted(self):
        pass

    def on_oim_message_sent(self, recipient, message):
        pass

########NEW FILE########
__FILENAME__ = profile

import papyon
import papyon.event

class ProfileEvents(papyon.event.ProfileEventInterface):
    def __init__(self, client, personalinfo_manager):
        self._personalinfo_manager = personalinfo_manager
        papyon.event.ProfileEventInterface.__init__(self, client)

    def on_profile_presence_changed(self):
        self._personalinfo_manager.onPresenceUpdated(self._client.profile.presence)

    def on_profile_display_name_changed(self):
        self._personalinfo_manager.onNickUpdated(self._client.profile.display_name)

    def on_profile_personal_message_changed(self):
        self._personalinfo_manager.onPSMUpdated(self._client.profile.personal_message)

    def on_profile_current_media_changed(self):
        self._personalinfo_manager.onCMUpdated(self._client.profile.current_media)

    def on_profile_msn_object_changed(self):
        #TODO: filter objects
        if self._client.profile.msn_object._type is papyon.p2p.MSNObjectType.DISPLAY_PICTURE:
            self._personalinfo_manager.onDPUpdated(self._client.profile.msn_object)

########NEW FILE########
__FILENAME__ = amsn2
#!/usr/bin/env python
import sys
import os
import optparse
os.chdir(os.path.dirname(os.path.abspath(sys.argv[0])))
sys.path.insert(0, "./papyon")
import locale
locale.setlocale(locale.LC_ALL, '')

from amsn2.core import aMSNCore

if __name__ == '__main__':
    account = None
    passwd = None
    default_front_end = "gtk"

    parser = optparse.OptionParser()
    parser.add_option("-a", "--account", dest="account",
                      default=None, help="The account's username to use")
    parser.add_option("-p", "--password", dest="password",
                      default=None, help="The account's password to use")
    parser.add_option("-f", "--front-end", dest="front_end",
                      default=default_front_end, help="The frontend to use")
    parser.add_option("-d", "--debug-protocol", action="store_true", dest="debug_protocol",
                      default=False, help="Show protocol debug")
    parser.add_option("-D", "--debug-amsn2", action="store_true", dest="debug_amsn2",
                      default=False, help="Show amsn2 debug")
    (options, args) = parser.parse_args()
    
    amsn = aMSNCore(options)
    
    amsn.run()


########NEW FILE########
