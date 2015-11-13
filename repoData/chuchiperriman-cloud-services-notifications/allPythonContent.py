__FILENAME__ = cloudsn
#!/usr/bin/python

from . import logger
from core import config, utils, notification
from core.controller import Controller
from os.path import join, abspath
import gettext
import locale
from const import *

def setup_locale_and_gettext():
    #Set up localization with gettext
    localedir = join (config.get_base_data_prefix(),"locale")
    # Install _() builtin for gettext; always returning unicode objects
    # also install ngettext()
    gettext.install(APP_NAME, localedir=localedir, unicode=True,
            names=("ngettext",))
    # For Gtk.Builder, we need to call the C library gettext functions
    # As well as set the codeset to avoid locale-dependent translation
    # of the message catalog
    locale.bindtextdomain(APP_NAME, localedir)
    locale.bind_textdomain_codeset(APP_NAME, "UTF-8")
    # to load in current locale properly for sorting etc
    try:
        locale.setlocale(locale.LC_ALL, "")
    except locale.Error, e:
        pass

def start ():
    logger.info("1")
    try:
        setup_locale_and_gettext()
    except Exception, e:
        logger.exception("Error loading the internationalitation: %s", e)
    
    try:
        cr = Controller.get_instance()
        cr.start()
    except Exception, e:
        logger.exception("Error starting cloudsn: %s", e)
        #We not traduce this notification because the problem can be gettext
        notification.notify ("Error starting cloudsn",
                            str(e),
                            utils.get_error_pixbuf())

if __name__ == "__main__":
    logger.debug("0")
    start()



########NEW FILE########
__FILENAME__ = const
#encoding: utf-8
APP_NAME="cloudsn"
APP_VERSION="0.10.2"
APP_LONG_NAME="Cloud Services Notifications"
APP_COPYRIGHT="Copyright © 2009-2011 Jesús Barbero Rodríguez"
APP_DESCRIPTION="Notify when new mail (POP3/IMAP/Gmail), feed items, tweets or items from other cloud services arrive."
APP_WEBSITE="http://chuchiperriman.github.com/cloud-services-notifications"

########NEW FILE########
__FILENAME__ = account
# -*- mode: python; tab-width: 4; indent-tabs-mode: nil -*-
from cloudsn.core import config, utils, keyring
from cloudsn import logger
from cloudsn.core.keyring import Credentials
from gi.repository import GObject
from datetime import datetime
import gettext

class Notification:
    def __init__(self, id = None, message = None, sender = None, icon = None):
        self.id = id
        self.sender = sender
        self.message = message
        self.icon = icon

class Account:
    def __init__ (self, properties, provider):
        if 'name' not in properties:
            raise Exception(_("Error loading account configuration: The name property is mandatory, check your configuration"))
        self.properties = properties
        self.properties["provider_name"] = provider.get_name()
        self.provider = provider
        self.total_unread = 0
        self.last_update = None
        self.error_notified = False
        self.credentials = None
        if 'active' not in self.properties:
            self.properties["active"] = True
        if 'show_notifications' not in self.properties:
            self.properties["show_notifications"] = True

    def __getitem__(self, key):
        return self.properties[key]

    def __setitem__(self, key, value):
        self.properties[key] = value

    def __contains__(self, key):
        return key in self.properties

    def __delitem__(self, key):
        del(self.properties[key])

    def get_properties(self):
        return self.properties

    def get_name (self):
        return self.properties["name"]

    def get_provider (self):
        return self.provider

    def can_mark_read(self):
        return False

    def mark_read(self):
        raise Exception("The mark_read method has not been implemented")

    def has_credentials(self):
        """False if the account doesn't need credentials"""
        return True

    def get_credentials(self):
        if not self.credentials:
            raise Exception (_("The credentials have not been loaded for the account %s") % (self.get_name()))

        return self.credentials

    #TODO change to get_credentials_safe
    def get_credentials_save(self):
        if not self.credentials:
            return keyring.Credentials("","")

        return self.credentials

    def set_credentials(self, credentials):
        self.credentials = credentials

    def get_show_notifications(self):
        return utils.get_boolean(self.properties["show_notifications"])

    def set_show_notifications(self, show_notifications):
        self.properties["show_notifications"] = utils.get_boolean(show_notifications)

    def get_active (self):
        return utils.get_boolean(self.properties["active"])

    def set_active(self, active):
        self.properties["active"] = utils.get_boolean(active)

    def get_activate_command(self):
        if "activate_command" in self.properties:
            return self.properties["activate_command"]
        return ""

    def set_activate_command(self, command):
        self.properties["activate_command"] = command

    def get_last_update (self):
        return self.last_update

    def get_total_unread (self):
        return self.total_unread

    def get_new_unread_notifications(self):
        return []

    def activate (self):
        if "activate_command" in self.properties and self.properties["activate_command"] != "":
            logger.debug ("Executing the activate command")
            utils.execute_command (self, self.properties["activate_command"])
        elif "activate_url" in self.properties :
            utils.show_url (self.properties["activate_url"])
        else:
            logger.warn('This account type has not an activate action')

    def get_icon (self):
        if self.error_notified:
            return utils.get_account_error_pixbuf(self)
        else:
            return self.get_provider().get_icon()
            
    def get_gicon (self):
        if self.error_notified:
            return utils.get_account_error_gicon(self)
        else:
            return self.get_provider().get_gicon()

class AccountCacheMails (Account):

    def __init__(self, properties, provider):
        Account.__init__(self, properties, provider)
        self.notifications = {}
        self.new_unread = []

    def get_total_unread (self):
        if self.notifications:
            return len(self.notifications)
        else:
            return self.total_unread

    def get_new_unread_notifications(self):
        return self.new_unread

class AccountManager (GObject.Object):

    __default = None

    __gtype_name__ = "AccountManager"

    __gsignals__ = { "account-added" : (GObject.SIGNAL_RUN_LAST, GObject.TYPE_NONE, (GObject.TYPE_PYOBJECT,)),
                     "account-deleted" : (GObject.SIGNAL_RUN_LAST, GObject.TYPE_NONE, (GObject.TYPE_PYOBJECT,)),
                     "account-changed" : (GObject.SIGNAL_RUN_LAST, GObject.TYPE_NONE, (GObject.TYPE_PYOBJECT,)),
                     "account-active-changed" : (GObject.SIGNAL_RUN_LAST, GObject.TYPE_NONE, (GObject.TYPE_PYOBJECT,))}

    def __init__(self):
        if AccountManager.__default:
           raise AccountManager.__default
        GObject.Object.__init__(self)
        from cloudsn.core.provider import ProviderManager
        self.accounts = {}
        self.sc = config.SettingsController.get_instance()
        self.pm = ProviderManager.get_instance()

    @staticmethod
    def get_instance():
        if not AccountManager.__default:
            AccountManager.__default = AccountManager()
        return AccountManager.__default

    def load_accounts(self):
        accs_conf = self.sc.get_accounts_config()
        for conf in accs_conf.values():
            provider = self.pm.get_provider(conf['provider_name'])
            if provider:
                try:
                    acc = provider.load_account (conf)
                    if acc.has_credentials():
                        credentials = Credentials("","")
                        try:
                            credentials = keyring.get_keyring().get_credentials(acc)
                        except Exception, e:
                            logger.exception("Cannot load credentials for account "+conf["name"]+": %s", e)
                        acc.set_credentials (credentials)
                    self.add_account(acc)
                except Exception, e:
                    logger.exception("Cannot load the account "+conf["name"]+": %s", e)

            else:
                logger.error("Error in account %s: The provider %s doesn't exists" % (conf['name'], conf['provider_name']))

    def validate_account(self, account_name):
        if account_name in self.accounts:
            error = _('The account %s already exists' % (account_name))
            raise Exception(error)

    def add_account(self, acc):
        self.validate_account(acc.get_name())
        self.accounts[acc.get_name()] = acc

        self.emit("account-added", acc)

    def set_account_active (self, acc, active):
        if acc.get_active() != active:
            acc.error_notified = False
            acc.set_active(active)
            self.emit("account-active-changed", acc)
            self.save_account(acc)

    def get_account(self, account_name):
        return self.accounts[account_name]

    def get_accounts(self):
        return self.accounts.values()

    def del_account(self, account, complete=True):
        del self.accounts[account.get_name()]
        if complete:
            self.sc.del_account_config(account.get_name())
            if account.has_credentials():
                keyring.get_keyring().remove_credentials(account)
            self.sc.save_accounts()

        self.emit("account-deleted", account)

    def update_account (self, acc):
        if acc.get_active():
            acc.provider.update_account (acc)
            acc.last_update = datetime.now()

    def save_account(self, acc):
        acc.error_notified = False
        self.sc.set_account_config (acc)
        if acc.has_credentials():
            keyring.get_keyring().store_credentials(acc, acc.get_credentials())
        self.sc.save_accounts()
        self.emit("account-changed", acc)

    def save_accounts(self, store_credentials = True):
        if store_credentials and acc.has_credentials():
            keyring.get_keyring().store_credentials(acc, acc.get_credentials())
        self.sc.save_accounts()

def get_account_manager():
    return AccountManager.get_instance()


########NEW FILE########
__FILENAME__ = config
#For the with statement in python 2.5
from __future__ import with_statement

import ConfigParser
import xdg.BaseDirectory as bd
import os
import sys
from os import mkdir
from os.path import isdir, join, dirname, abspath
from gi.repository import GObject, Gtk, GdkPixbuf
import gettext


#Test if it is the tar/git
if os.path.exists(join (dirname (__file__), "../../../setup.py")):
    _base_prefix = abspath(join (dirname (__file__), "../../.."))
    _prefix = abspath (join (dirname (__file__), "../../../data"))
    _installed = False
else:
    for pre in ("site-packages", "dist-packages", sys.prefix):
        # Test if we are installed on the system
        for sub in ("share", "local/share"):
            _prefix = join (sys.prefix, sub, "cloudsn")
            _base_prefix = join (sys.prefix, sub)
            if isdir(_prefix):
                _installed = True
                break
        else:
            raise Exception(_("Can't find the cloudsn data directory"))

def get_base_data_prefix ():
    return abspath (_base_prefix)

def get_data_prefix ():
    return abspath (_prefix)

def add_data_prefix (subpath):
    return abspath (join (_prefix, subpath))

def is_installed ():
    return _installed

def get_apps_prefix():
    if is_installed():
        return abspath (join (_base_prefix, "applications"))
    else:
        return get_data_prefix()

def get_cache_path ():
    return bd.xdg_cache_home + '/cloud-services-notifications'

def get_ensure_cache_path():
    path = get_cache_path()
    if not os.path.exists (path):
        os.makedirs (path)
    return path

def add_apps_prefix(subpath):
    return join (get_apps_prefix(), subpath)

class SettingsController(GObject.Object):

    __default = None

    __gtype_name__ = "SettingsController"

    # Section, Key, Value
    __gsignals__ = { "value-changed" : (GObject.SIGNAL_RUN_LAST, GObject.TYPE_BOOLEAN,
                                        (GObject.TYPE_STRING, GObject.TYPE_STRING, GObject.TYPE_PYOBJECT))}

    CONFIG_HOME = bd.xdg_config_home + '/cloud-services-notifications'
    CONFIG_PREFERENCES = CONFIG_HOME + '/preferences'
    CONFIG_ACCOUNTS = CONFIG_HOME + '/accounts'

    __default_prefs = {
        "preferences" : {
            "minutes" : 10,
            "indicator" : '',
            "max_notifications" : 3,
            "keyring" : '',
            "enable_sounds" : "True"
            }
    }

    def __init__(self):
        if SettingsController.__default:
           raise SettingsController.__default
        GObject.Object.__init__(self)
        self.ensure_config()
        self.prefs = self.config_to_dict(self.config_prefs)
        self.accounts = self.config_to_dict(self.config_accs)

    @staticmethod
    def get_instance():
        if not SettingsController.__default:
            SettingsController.__default = SettingsController()
        return SettingsController.__default

    def dict_to_config (self, config, dic):
        for sec, data in dic.iteritems():
            if not config.has_section(sec):
                config.add_section (sec)
            for key, value in data.iteritems():
                config.set(sec, key, value)

    def config_to_dict (self, config):
        res = {}
        for sec in config.sections():
            res[sec] = {}
            for key in config.options(sec):
                res[sec][key] = config.get(sec, key)
        return res

    def ensure_config (self):
        if not os.path.exists (self.CONFIG_HOME):
            os.makedirs (self.CONFIG_HOME)

        if not os.path.exists (self.CONFIG_ACCOUNTS):
            f = open(self.CONFIG_ACCOUNTS, "w")
            f.close()

        if not os.path.exists (self.CONFIG_PREFERENCES):
            f = open(self.CONFIG_PREFERENCES, "w")
            f.close()

        self.config_prefs = ConfigParser.ConfigParser()
        self.config_prefs.read (self.CONFIG_PREFERENCES)
        self.config_accs = ConfigParser.ConfigParser()
        self.config_accs.read (self.CONFIG_ACCOUNTS)

        def fill_parser(parser, defaults):
            for secname, section in defaults.iteritems():
                if not parser.has_section(secname):
                    parser.add_section(secname)
                for key, default in section.iteritems():
                    if isinstance(default, int):
                        default = str(default)
                    if not parser.has_option(secname, key):
                        parser.set(secname, key, default)

        fill_parser(self.config_prefs, self.__default_prefs)

    def get_account_list (self):
        return self.accounts.keys ()

    def get_accounts_config (self):
        return self.accounts

    def get_account_list_by_provider (self, provider):
        res = []
        for sec in self.accounts.keys():
            if "provider_name" in self.accounts[sec]:
                if self.accounts[sec]["provider_name"] == provider.get_name():
                    res.append (sec)
            else:
                logger.error("The account " + sec + " has not a provider_name property")

        return res

    def get_account_config (self, account_name):
        return self.accounts[account_name]

    def set_account_config(self, account):
        if account.get_name() in self.accounts:
            del self.accounts[account.get_name()]
        self.accounts[account.get_name()] = account.get_properties()

    def del_account_config (self, account_name):
        del self.accounts[account_name]

    def get_prefs (self):
        return self.prefs["preferences"]

    def set_pref (self, key, value):
        self.prefs["preferences"][key] = value
        self.emit("value-changed", "preferences", key, value)

    def save_prefs (self):
        self.dict_to_config(self.config_prefs, self.prefs)
        with open(self.CONFIG_PREFERENCES, 'wb') as configfile:
            self.config_prefs.write(configfile)

    def save_accounts (self):
        self.config_accs = ConfigParser.ConfigParser()
        self.dict_to_config(self.config_accs, self.accounts)
        with open(self.CONFIG_ACCOUNTS, 'wb') as configfile:
            self.config_accs.write(configfile)

__cloudsn_icon = None
def get_cloudsn_icon():
    global __cloudsn_icon
    if not __cloudsn_icon:
        __cloudsn_icon = GdkPixbuf.Pixbuf.new_from_file(add_data_prefix('cloudsn.png'))
    return __cloudsn_icon

def get_startup_file_dir():
    return abspath(join(bd.xdg_config_home, "autostart"))

def get_startup_file_path():
    return abspath(join(get_startup_file_dir(), "cloudsn.desktop"))


########NEW FILE########
__FILENAME__ = controller
# -*- mode: python; tab-width: 4; indent-tabs-mode: nil -*-
from cloudsn.core.provider import Provider, ProviderManager
from cloudsn.core import account, config, networkmanager, notification, utils, indicator
from cloudsn.ui import window
from cloudsn import logger
from cloudsn.ui.authwarning import check_auth_configuration
from time import time
from gi.repository import Gtk, GObject
import gettext
import thread

class Controller (GObject.Object):

    __default = None

    __gtype_name__ = "Controller"

    __gsignals__ = { "account-checked" : (GObject.SIGNAL_RUN_LAST, GObject.TYPE_NONE, (GObject.TYPE_PYOBJECT,)),
                     "account-check-error" : (GObject.SIGNAL_RUN_LAST, GObject.TYPE_NONE, (GObject.TYPE_PYOBJECT,))}

    timeout_id = -1
    interval = 60

    def __init__(self):
        if Controller.__default:
           raise Controller.__default

        #Prevent various instances
        GObject.Object.__init__(self)
        import os, fcntl, sys, tempfile, getpass
        self.lockfile = os.path.normpath(tempfile.gettempdir() + '/cloudsn-'+getpass.getuser()+'.lock')
        self.fp = open(self.lockfile, 'w')
        try:
            fcntl.lockf(self.fp, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except IOError:
            message = _("Another instance is already running, close it first.")
            logger.warn (message)
            print message.encode('utf-8')
            raise Exception (message)

        self.started = False
        self.config = config.SettingsController.get_instance()
        self.config.connect("value-changed", self._settings_changed)
        self.prov_manager = ProviderManager.get_instance()
        self.im = indicator.IndicatorManager.get_instance()
        self.am = account.AccountManager.get_instance()
        self.am.connect("account-added", self._account_added_cb)
        self.am.connect("account-deleted", self._account_deleted_cb)
        self.am.connect("account-changed", self._account_changed_cb)
        self.am.connect("account-active-changed", self._account_active_cb)
        self.am.load_accounts()
        self.accounts_checking = []
        self.nm = networkmanager.NetworkManager()

    @staticmethod
    def get_instance():
        if not Controller.__default:
            Controller.__default = Controller()
        return Controller.__default

    def _account_added_cb(self, am, acc):
        indi = self.im.get_indicator()
        if indi and acc.get_active():
            indi.create_indicator(acc)

        if self.started:
            self.update_account(acc)

    def _account_deleted_cb(self, am, acc):
        self.im.get_indicator().remove_indicator(acc)

    def _account_active_cb(self, am, acc):
        if acc.get_active():
            self.im.get_indicator().create_indicator(acc)
            self.update_account(acc)
        else:
            self.im.get_indicator().remove_indicator(acc)

    def _account_changed_cb (self, am, acc):
        self.update_account(acc)

    def _settings_changed(self, config, section, key, value):
        if section == "preferences" and key == "minutes":
            self._update_interval()

    def _update_interval(self):
        old = self.interval
        self.interval = int(float(self.config.get_prefs()["minutes"]) * 60)

        if not self.get_active():
            return

        if self.timeout_id < 0:
            logger.debug("new source: "+str(self.timeout_id))
            self.timeout_id = GObject.timeout_add_seconds(self.interval,
                                self.update_accounts, None)
        elif self.interval != old:
            logger.debug("removed source: "+str(self.timeout_id))
            GObject.source_remove(self.timeout_id)
            logger.debug("restart source: "+str(self.timeout_id))
            self.timeout_id = GObject.timeout_add_seconds(self.interval,
                                self.update_accounts, None)

    def on_nm_state_changed (self):
        if self.nm.state == networkmanager.STATE_CONNECTED:
            logger.debug("Network connected")
            #Force update
            self.update_accounts()
        else:
            logger.debug("Network disconnected")

    def set_active(self, active):
        if active and not self.get_active():
            self.timeout_id = GObject.timeout_add_seconds(self.interval,
                                self.update_accounts, None)
            logger.debug("activated source: "+str(self.timeout_id))
        elif not active and self.get_active():
            GObject.source_remove(self.timeout_id)
            logger.debug("deactivated source "+str(self.timeout_id))
            self.timeout_id = -1


    def get_active(self):
        return self.timeout_id > -1

    def update_account(self, acc):
        if not self.get_active():
            return
        """acc=None will check all accounts"""
        if self.nm.offline():
            logger.warn ("The network is not connected, the account cannot be updated")
            return

        #TODO Check if the updater is running
        if acc is None:
            for acc in self.am.get_accounts():
                thread.start_new_thread(self.__real_update_account, (acc,))
        else:
            thread.start_new_thread(self.__real_update_account, (acc,))

        #self.__real_update_account(acc)

    def __real_update_account(self, acc):
        if acc in self.accounts_checking:
            logger.warn("The account %s is being checked" % (acc.get_name()))
            return

        logger.debug("Starting checker")
        if not acc.get_active():
            logger.debug("The account %s is not active, it will not be updated" % (acc.get_name()))
            return

        self.accounts_checking.append(acc)
        max_notifications = int(float(self.config.get_prefs()["max_notifications"]))
        try:
            logger.debug('Updating account: ' + acc.get_name())

            #Process events to show the main icon
            while Gtk.events_pending():
                Gtk.main_iteration(False)

            self.am.update_account(acc)

            acc.error_notified = False

            if hasattr(acc, "indicator"):
                self.im.get_indicator().update_account(acc)


            #Process events to show the indicator menu
            while Gtk.events_pending():
                Gtk.main_iteration(False)

            if acc.get_provider().has_notifications() and \
                    acc.get_show_notifications():
                nots = acc.get_new_unread_notifications()
                message = None
                if len(nots) > max_notifications:
                    notification.notify(acc.get_name(),
                        _("New messages: ") + str(len(nots)),
                        acc.get_icon())

                if len(nots) > 0 and len(nots) <= max_notifications:
                    for n in nots:
                        if n.icon:
                            icon = n.icon
                        else:
                            icon = acc.get_icon()
                        notification.notify(acc.get_name() + ": " + n.sender,
                            n.message,
                            icon)

            self.emit("account-checked", acc)
        except notification.NotificationError, ne:
            logger.exception("Error trying to notify with libnotify: %s", e)
        except Exception, e:
            logger.exception("Error trying to update the account %s: %s", acc.get_name(), e)
            if not acc.error_notified:
                acc.error_notified = True
                notification.notify (_("Error checking account %s") % (acc.get_name()),
                    str(e),
                    acc.get_icon())
                self.im.get_indicator().update_error(acc)
            self.emit("account-check-error", acc)
        finally:
            self.accounts_checking.remove(acc)

        logger.debug("Ending checker")

    def update_accounts(self, data=None):
        if not self.get_active():
            return True
        self.update_account(None)
        #For the timeout_add_seconds
        return True

    def _start_idle(self):
        try:
            check_auth_configuration()
            self.nm.set_statechange_callback(self.on_nm_state_changed)
            self.set_active (True)
            self.update_accounts()
            self.started = True
            #if len(self.am.get_accounts()) == 0:
            win = window.MainWindow.get_instance()
            win.run()
        except Exception, e:
            logger.exception ("Error starting the application: %s", e)
            try:
                notification.notify(_("Application Error"),
                    _("Error starting the application: %s") % (str(e)),
                    utils.get_error_pixbuf())
            except Exception, e:
                logger.exception ("Error notifying the error: %s", e)

        return False

    def start(self):
        GObject.threads_init()
        GObject.idle_add(self._start_idle)
        try:
            Gtk.main()
        except KeyboardInterrupt:
            logger.info ('KeyboardInterrupt the main loop')


########NEW FILE########
__FILENAME__ = indicator
import os
from cloudsn.core import config, utils, notification
from cloudsn import logger

class Indicator:

    def get_name(self):
        return None

    def set_active(self, active):
        pass
    def create_indicator(self, acc):
        pass

    def update_account(self, acc):
        pass

    def remove_indicator(self, acc):
        pass
    
    def update_error(self, acc):
        pass

class IndicatorManager():

    __default = None

    def __init__(self):
        if IndicatorManager.__default:
           raise IndicatorManager.__default

        self.indicator= None
        self.indicators = {}
        from cloudsn.ui.indicators import statusicon
        indi_statusicon = statusicon.StatusIconIndicator()
        self.indicators[indi_statusicon.get_name()] = indi_statusicon
        indi_indicator = None
        try:
            from cloudsn.ui.indicators import indicatorapplet
            indi_indicator = indicatorapplet.IndicatorApplet()
            self.indicators[indi_indicator.get_name()] = indi_indicator
        except Exception,e:
            logger.exception("The indicator applet provider cannot be loaded: %s", e)
            
        indi_messagingmenu = None
        try:
            from cloudsn.ui.indicators import messagingmenu
            indi_messagingmenu = messagingmenu.IndicatorApplet()
            self.indicators[indi_messagingmenu.get_name()] = indi_messagingmenu
        except Exception,e:
            logger.exception("The message menu applet provider cannot be loaded: %s", e)

        self.config = config.SettingsController.get_instance()
        indicator_conf = self.config.get_prefs()["indicator"]
        if indicator_conf:
            for name in self.indicators:
                if name == indicator_conf:
                    self.indicator = self.indicators[name]
                    break
            if not self.indicator:
                logger.error("The indicator named %s is configured but it cannot be found" % (indicator_conf))
                notification.notify (_("Indicator error"),
                                    _("The indicator named %s is configured but it cannot be found") % (indicator_conf),
                                    utils.get_error_pixbuf())
        if not self.indicator:
            if "DESKTOP_SESSION" in os.environ and os.environ["DESKTOP_SESSION"] == 'ubuntu':
                indi_fin = indi_messagingmenu if indi_messagingmenu else indi_indicator
                if not indi_fin:
                    notification.notify (_("Indicator error"),
                                        _("The indicator for ubuntu cannot be loaded "),
                                        utils.get_error_pixbuf())
                    raise Error(_("The indicator for ubuntu cannot be loaded "))
                self.indicator = indi_fin
            else:
                self.indicator = indi_statusicon
            
        self.indicator.set_active(True)
        
    @staticmethod
    def get_instance():
        if not IndicatorManager.__default:
            IndicatorManager.__default = IndicatorManager()
        return IndicatorManager.__default
    
    def get_indicator(self):
        return self.indicator

    def get_indicators(self):
        return self.indicators.values()

########NEW FILE########
__FILENAME__ = keyring
# -*- mode: python; tab-width: 4; indent-tabs-mode: nil -*-
from cloudsn.core import config
from cloudsn import logger

class Credentials:
    def __init__(self, username = None, password = None):
        self.username = username
        self.password = password

class Keyring():

    def get_id(self):
        raise Exception("You must configure the keyring id")

    def get_name(self):
        return None

    def remove_credentials(self, acc):
        """ Remove the credentials from the keyring"""
        pass

    def store_credentials(self, acc, credentials):
        """ Save the credentials in the keyring"""
        pass

    def get_credentials(self, acc):
        """ Returns the credentials (Credentials) for the account """
        return None

class KeyringManager:

    __default = None

    managers = []

    current = None

    def __init__(self):
        if KeyringManager.__default:
            raise KeyringManager.__default

        #TODO control errors to disable providers
        self.config = config.SettingsController.get_instance()
        from keyrings.plainkeyring import PlainKeyring
        self.__add_manager (PlainKeyring())

        try:
            from keyrings.base64keyring import Base64Keyring
            self.__add_manager (Base64Keyring())
        except Exception, e:
            logger.exception("Cannot load base64 keyring: %s", e)
            
        try:
            from keyrings.gkeyring import GnomeKeyring
            self.__add_manager (GnomeKeyring())
        except Exception, e:
            logger.exception("Cannot load gnome keyring: %s", e)
        configured_name = self.config.get_prefs()["keyring"]
        for m in self.managers:
            if m.get_id() == configured_name:
                self.current = m
                logger.info("Current keyring: %s " % (self.current.get_name()))
                break
        if not self.current:
            #The most secure by default
            self.current = self.managers[-1]
            logger.info("No keyring configured, using %s " % (self.current.get_name()))

    @staticmethod
    def get_instance():
        if not KeyringManager.__default:
            KeyringManager.__default = KeyringManager()
        return KeyringManager.__default

    def __add_manager (self, manager):
        self.managers.append (manager)

    def get_managers (self):
        return self.managers

    def get_manager(self):
        return self.current

    def set_manager(self, manager):
        #The same manager, we don't need do nothing
        if manager == self.current:
            logger.debug("Setting the keyring manager but it is the same")
            return
        logger.info("Setting the keyring manager: %s" % (manager.get_name()))
        from cloudsn.core import account
        old = self.current
        for acc in account.AccountManager.get_instance().get_accounts():
            try:
                credentials = acc.get_credentials()
                old.remove_credentials(acc)
                manager.store_credentials(acc, credentials)
            except Exception, e:
                logger.exception("Cannot change the keyring for the account "\
                    + acc.get_name() + ": %s" , e)

        self.current = manager
        account.get_account_manager().save_accounts(False)


class KeyringException(Exception): pass

def get_keyring():
    return KeyringManager.get_instance().get_manager()


########NEW FILE########
__FILENAME__ = base64keyring
# -*- mode: python; tab-width: 4; indent-tabs-mode: nil -*-
import base64
import gettext
from cloudsn import logger
from cloudsn.core.keyring import Keyring, KeyringException, Credentials

class Base64Keyring(Keyring):

    def get_id(self):
        return "base64"
        
    def get_name(self):
        return _("Base64 encoding")

    def remove_credentials(self, acc):
        del(acc["username"])
        del(acc["password"])
        
    def store_credentials(self, acc, credentials):
        try:
            logger.debug("Storing base64 credentials for account: %s" % (acc.get_name()))
            acc["username"] = base64.encodestring(credentials.username)
            acc["password"] = base64.encodestring(credentials.password)
        except Exception, e:
            raise KeyringException("Cannot encode the base64 username password for account %s" % (acc.get_name()), e)

    def get_credentials(self, acc):
        self.__check_valid(acc)
        try:
            return Credentials(base64.decodestring(acc["username"]),
                base64.decodestring(acc["password"]))
        except Exception, e:
            raise KeyringException("Cannot decode the base64 username or password for account %s" % (acc.get_name()), e)
            
    def __check_valid(self, acc):
        if not "username" in acc or not "password" in acc:
            raise KeyringException("The account %s has not a username or password configured" % (acc.get_name()))


########NEW FILE########
__FILENAME__ = gkeyring
# -*- mode: python; tab-width: 4; indent-tabs-mode: nil -*-
from gi.repository import GnomeKeyring as gk
from cloudsn.core.keyring import Keyring, KeyringException, Credentials
from cloudsn import logger
import threading

GNOME_KEYRING_ID = "gnomekeyring"

class GnomeKeyring(Keyring):

    _KEYRING_NAME = 'cloudsn'
    
    def __init__(self):
        self._protocol = "network"
        self._key = gk.ItemType.NETWORK_PASSWORD
        if not gk.is_available():
            raise KeyringException("The Gnome keyring is not available")
        logger.debug("GnomeKeyring is available")
        self.loaded = False
        self.lock = threading.RLock()
        
        if not self.loaded:
            (result, keyring_names) = gk.list_keyring_names_sync()
            if self._KEYRING_NAME not in keyring_names:
                logger.error("Error getting the gnome keyring. We'll try to create it: %s")
                logger.debug("Creating keyring " + self._KEYRING_NAME)
                gk.create_sync(self._KEYRING_NAME, None)
            self.loaded = True
        
    def get_id(self):
        return GNOME_KEYRING_ID
        
    def get_name(self):
        return _("Gnome keyring")

    def get_credentials(self, acc):
        self.lock.acquire()
        try:
            logger.debug("Getting credentials with gnome keyring for account %s" % (acc.get_name()))
            attrs = gk.Attribute.list_new()
            gk.Attribute.list_append_string(attrs, 'account_name', acc.get_name())
            try:
                (result, items) = gk.find_items_sync(gk.ItemType.NETWORK_PASSWORD, attrs)
            except gk.NoMatchError, e:
                items = list()
                
            if len(items) < 1:
                raise KeyringException("Cannot find the keyring data for the account %s" % (acc.get_name()))
            
            logger.debug("items ok")
            
            username = ''
            for attr in gk.Attribute.list_to_glist(items[0].attributes):
                if attr.name == 'username':
                    username = attr.get_string()
            return Credentials (username, items[0].secret)
        finally:
            self.lock.release()

    def remove_credentials(self, acc):
        self.lock.acquire()
        try:
            logger.debug("Removing credentias from gnome keyring for the account: %s" % (acc.get_name()))
            if hasattr(acc, "keyringid"):
                gk.item_delete_sync(self._KEYRING_NAME, int(acc.keyringid))
                logger.debug("Credentials removed")
            else:
                logger.debug("The account has not credentials asigned, continue")
        finally:
            self.lock.release()

    def store_credentials(self, acc, credentials):
        self.lock.acquire()
        try:
            logger.debug("Storing credentials with gnome keyring for account %s" % (acc.get_name()))
            #Remove the old info and create a new item with the new info
            self.remove_credentials(acc)

            attrs = gk.Attribute.list_new()
            gk.Attribute.list_append_string(attrs, 'account_name', acc.get_name())
            gk.Attribute.list_append_string(attrs, 'username', credentials.username)
            
            (result, id) = gk.item_create_sync(self._KEYRING_NAME, \
                 gk.ItemType.NETWORK_PASSWORD, acc.get_name(), attrs, credentials.password, True)
            if result != gk.Result.OK:
                raise Exception("Gnome Keyring return the error code: %i" % result)
            logger.debug("credentials stored with id: %i" % (id))
        finally:
            self.lock.release()

########NEW FILE########
__FILENAME__ = plainkeyring
# -*- mode: python; tab-width: 4; indent-tabs-mode: nil -*-
from cloudsn.core.keyring import Keyring, KeyringException, Credentials
from cloudsn import logger
import gettext

class PlainKeyring(Keyring):
    
    def get_id(self):
        return "plain"
    
    def get_name(self):
        return _("Plain text")

    def remove_credentials(self, acc):
        del(acc["username"])
        del(acc["password"])
        
    def store_credentials(self, acc, credentials):
        logger.debug("Storing plain credentials for account: %s" % (acc.get_name()))
        acc["username"] = credentials.username
        acc["password"] = credentials.password
        
    def get_credentials(self, acc):
        self.__check_valid(acc)
        return Credentials(acc["username"], acc["password"])

    def __check_valid(self, acc):
        if "username" not in acc.get_properties() or \
            "password" not in acc.get_properties():
            raise KeyringException(_("The username or password are not configured for the account: %s") % (acc.get_name()))

########NEW FILE########
__FILENAME__ = networkmanager
# Based on invest-applet in gnome-applets


from cloudsn import logger
from dbus.mainloop.glib import DBusGMainLoop
import dbus

# possible states, see http://projects.gnome.org/NetworkManager/developers/api/09/spec.html#type-NM_STATE
STATE_UNKNOWN		= dbus.UInt32(0)
STATE_CONNECTED_GLOBAL = dbus.UInt32(70)

class NetworkManager:
	def __init__(self):
		self.state = STATE_UNKNOWN
		self.statechange_callback = None

		try:
			# get an event loop
			loop = DBusGMainLoop()

			# get the NetworkManager object from D-Bus
			logger.debug("Connecting to Network Manager via D-Bus")
			bus = dbus.SystemBus(mainloop=loop)
			nmobj = bus.get_object('org.freedesktop.NetworkManager', '/org/freedesktop/NetworkManager')
			nm = dbus.Interface(nmobj, 'org.freedesktop.NetworkManager')

			# connect the signal handler to the bus
			bus.add_signal_receiver(self.handler, None,
					'org.freedesktop.NetworkManager',
					'org.freedesktop.NetworkManager',
					'/org/freedesktop/NetworkManager')

			# get the current status of the network manager
			self.state = nm.state()
			logger.debug("Current Network Manager status is %d" % self.state)
		except Exception, msg:
			logger.error("Could not connect to the Network Manager: %s" % msg )

	def online(self):
		return self.state == STATE_UNKNOWN or self.state == STATE_CONNECTED_GLOBAL

	def offline(self):
		return not self.online()

	# the signal handler for signals from the network manager
	def handler(self,signal=None):
		if isinstance(signal, dict):
			state = signal.get('State')
			if state != None:
				logger.debug("Network Manager change state %d => %d" % (self.state, state) );
				self.state = state

				# notify about state change
				if self.statechange_callback != None:
					self.statechange_callback()

	def set_statechange_callback(self,handler):
		self.statechange_callback = handler

########NEW FILE########
__FILENAME__ = notification
#Edited by Michele Bovo <madnessmike4ever@gmail.com>
#Changed notification system for better integrating it into Gnome-shell
from cloudsn import logger
from cloudsn.core.sound import Sound
from cloudsn.core import config
from datetime import datetime

notifications = []
disable = True
notifying = False
last_notify = tstart = datetime.now()

try:
    from gi.repository import Notify
    if Notify.init("Cloud Services Notifications"):
        disable = False
    else:
        logger.error("Cannot initialize libnotify")
except Exception, e:
    logger.exception ("there was a problem initializing the Notify module: %s" % (e))


#def notify_closed_cb (n, data=None):
#    global notifications, notifying
#    notifying = False
#    if n in notifications:
#        notifications.remove (n)
#    n = None
#    notify_process()

def notify_process ():
    global notifications, notifying, last_notify

    if len(notifications) == 0:
        return;

#    if notifying == True:
#        #See Bug #622021 on gnome
#        diff = datetime.now() - last_notify
#        if diff.seconds > 30:
#            logger.debug("30 seconds from the last notification, reactivating")
#            notifying = False
#        else:
#            return
    
    if not Notify.is_initted():
        logger.warn('The notification library has not been initialized yet')
        return
    
    while len(notifications) > 0:
        n = notifications.pop(0)
        #n.connect("closed", notify_closed_cb)
        n.show()

    notifying= True
    last_notify = datetime.now()
    #TODO Do it better and configuable
    sound = Sound()
    sound.play(config.add_data_prefix("drip.ogg"))

def notify (title, message, icon = None):
    if disable == True:
        raise NotificationError ("there was a problem initializing the Notify module")

    global notifications
    n = Notify.Notification.new(title, message, None)
    n.set_urgency(Notify.Urgency.LOW)
    #n.set_timeout(3000)

    if icon:
        n.set_icon_from_pixbuf(icon)

    notifications.append(n)
    notify_process()

class NotificationError(Exception): pass

########NEW FILE########
__FILENAME__ = provider
# -*- mode: python; tab-width: 4; indent-tabs-mode: nil -*-
from cloudsn.core.account import Account

class Provider:

    def __init__ (self, name):
        self.name = name
        self.icon = None
        self.gicon = None

    def load_account(self, props):
        return Account(props, self)

    def update_account (self, account_data):
        pass
    def has_indicator(self):
        return True
    def has_notifications (self):
        return True
    def get_import_error(self):
        return None
    def get_name (self):
        return self.name
    def get_icon (self):
        return self.icon
    def get_gicon(self):
        return self.gicon
    def get_account_data_widget (self, account=None):
        """
            If account == None is a new account if not then editing
            Returns a widget and it will be inserted into the new account dialog
        """
        return None
    def set_account_data_from_widget(self, account_name, widget, account=None):
        """
            Must return the modified accont or a new one if account==None
            raise an exception if there is an error validating the data
        """
        raise NotImplementedError("The provider must implement this method!!")

class ProviderManager:

    __default = None

    providers = []

    def __init__(self):
        if ProviderManager.__default:
           raise ProviderManager.__default

    @staticmethod
    def get_instance():
        if not ProviderManager.__default:
            ProviderManager.__default = ProviderManager()
            #Default providers
            from cloudsn.providers.gmailprovider import GMailProvider
            from cloudsn.providers.greaderprovider import GReaderProvider
            from cloudsn.providers.pop3provider import Pop3Provider
            from cloudsn.providers.imapprovider import ImapProvider
            from cloudsn.providers.twitterprovider import TwitterProvider
            from cloudsn.providers.identicaprovider import IdenticaProvider
            from cloudsn.providers.feedsprovider import FeedsProvider
            ProviderManager.__default.add_provider (GMailProvider.get_instance())
            ProviderManager.__default.add_provider (GReaderProvider.get_instance())
            ProviderManager.__default.add_provider (Pop3Provider.get_instance())
            ProviderManager.__default.add_provider (ImapProvider.get_instance())
            ProviderManager.__default.add_provider (TwitterProvider.get_instance())
            ProviderManager.__default.add_provider (IdenticaProvider.get_instance())
            ProviderManager.__default.add_provider (FeedsProvider.get_instance())
        return ProviderManager.__default

    def add_provider (self, provider):
        self.providers.append (provider)
    def get_providers (self):
        return self.providers
    def get_provider(self, name):
        for prov in self.providers:
            if prov.get_name() == name:
                return prov
        return None


########NEW FILE########
__FILENAME__ = sound
# -*- coding: UTF8 -*-

# Based on:
# Specto , Unobtrusive event notifier
#
#       sound.py
#

from cloudsn import logger
from cloudsn.core import config, utils

#TODO If we import the modules but the sound is disabled, we load
#arround 1,5mb of memory

enabled = False
try:
    #TODO Disabled because I need study how to do it with gtk-3 
    raise Exception("Sound is unsuported by the moment")
    import pygst
    pygst.require("0.10")
    import gst
    enabled = True
except Exception, e:
    logger.warn("Cloudsn cannot play sounds because pygst >= 0.10 is not installed")

class Sound:
    def __init__(self):
        self.player = None
        self.playing = False

    def play(self, uri):
        global enabled
        if not enabled:
            return

        if not utils.get_boolean(config.SettingsController.get_instance().get_prefs()["enable_sounds"]):
            return

        if uri and self.playing == False:
            self.player = gst.element_factory_make("playbin", "player")
            uri =  "file://" + uri
            self.player.set_property('uri', uri)
            bus = self.player.get_bus()
            bus.add_signal_watch()
            bus.connect("message", self.on_message)

            self.player.set_state(gst.STATE_PLAYING)
            self.playing = True

    def on_message(self, bus, message):
        #remove the pipeline is the sound is finished playing
        # and allow new sounds to be played from specto
        if message.type == gst.MESSAGE_EOS:
            self.player.set_state(gst.STATE_NULL)
            self.playing = False


########NEW FILE########
__FILENAME__ = utils
#import gconf
from gi.repository import Gtk, Gio, Gdk, GdkPixbuf
import os
import subprocess
from email.header import decode_header
from cloudsn.core import config
from cloudsn import logger
import tempfile
import urllib2

def show_url(url):
    """Open any @url with default viewer"""
    #from Gtk import show_uri, get_current_event_time
    #from Gtk.gdk import screen_get_default
    #from glib import GError
    try:
        Gtk.show_uri(Gdk.Screen.get_default(), url, Gtk.get_current_event_time())
    except:
        logger.exception("Error in Gtk.show_uri: %s")

def invoke_subprocess(cmdline):
	setsid = getattr(os, 'setsid', None)
	subprocess.Popen(cmdline, close_fds = True, preexec_fn = setsid)

def get_default_mail_reader():
	#client = gconf.client_get_default()
	client = Gio.Settings.new()
	cmd  = client.get_string("/desktop/gnome/url-handlers/mailto/command")
	return cmd.split()[0]

def open_mail_reader():
	cmdline = get_default_mail_reader()
	invoke_subprocess(cmdline)

def mime_decode(str):
    strn, encoding = decode_header(str)[0]
    if encoding is None:
        return strn
    else:
        return strn.decode(encoding, "replace")

def get_boolean (value):
    if isinstance (value,bool):
        return value
    elif isinstance (value, str):
        return value.strip().lower() == 'true'
    return False

def get_error_pixbuf():
    icons = Gtk.IconTheme.get_default()
    #TODO How can I set this value with gir ? l = Gtk.ICON_LOOKUP_USE_BUILTIN
    return icons.load_icon(Gtk.STOCK_DIALOG_ERROR, 32, 0)

def get_account_error_pixbuf (acc):
    original = acc.get_provider().get_icon().copy()
    error = GdkPixbuf.Pixbuf.new_from_file(config.add_data_prefix('error.png'))
    error.composite(original, 10, 10, 22, 22, 10, 10, 1.0, 1.0, GdkPixbuf.InterpType.HYPER, 220)
    return original

def get_account_error_gicon (acc):
    return Gio.FileIcon.new(Gio.File.new_for_path(config.add_data_prefix('error.png')))

def download_image_to_tmp(url):
    filename = url.replace('http://', '0_')
    filename = filename.replace('/', '_')
    fullname = os.path.join(tempfile.gettempdir(), filename)

    if os.path.exists(fullname):
        return fullname
        
    f = urllib2.urlopen(url).read()

    fich = open(fullname, 'w+')
    fich.write(f)
    fich.close()
    
    return fullname

def download_image_to_pixbuf(url):
    path = download_image_to_tmp(url)
    return GdkPixbuf.Pixbuf.new_from_file(path)

def execute_command(acc, command):
    open_command = replace_variables(acc, command)
    if open_command != "":
        os.system(open_command + " &")
        return True
    else:
        return False
    
def replace_variables(acc, command):
    _command = command
    available_variables = {"${account_name}": "'" + acc.get_name().replace("'", "") + "'"}
    for variable in available_variables:
        _command = _command.replace(variable, available_variables[variable])
        
    return _command

def get_safe_filename(name):
    return "".join([x for x in name.lower() if x.isalpha() or x.isdigit()])
    
if __name__ == "__main__":
    print get_default_mail_reader()
    open_mail_reader()


########NEW FILE########
__FILENAME__ = feedsprovider
# -*- mode: python; tab-width: 4; indent-tabs-mode: nil -*-
from cloudsn.core.account import Account, AccountManager, Notification
from cloudsn.core.keyring import Credentials
from cloudsn.providers.providersbase import ProviderUtilsBuilder
from cloudsn.core.provider import Provider
from cloudsn.core import utils, indicator, config
from cloudsn import logger
from os.path import join
import os
from gi.repository import Gtk, GdkPixbuf
import urllib2
import csv

import_error = None

try:
    import feedparser
except Exception, e:
    logger.error("Error loading the FeedsProvider: %s", e)
    import_error = Exception(_("You need install the python-feedparser module to use this provider"))

class FeedsProvider(ProviderUtilsBuilder):

    __default = None

    def __init__(self):
        if FeedsProvider.__default:
           raise FeedsProvider.__default
        ProviderUtilsBuilder.__init__(self, _("RSS news"), 'rss')

    @staticmethod
    def get_instance():
        if not FeedsProvider.__default:
            FeedsProvider.__default = FeedsProvider()
        return FeedsProvider.__default

    def load_account(self, props):
        return FeedAccount(props, self)

    def get_import_error(self):
        return import_error

    def update_account (self, account):

        doc = feedparser.parse(account["url"])

        account.new_unread = []
        for entry in doc.entries:
            entry_id = entry.get("id", entry.title)
            if not account.has_feed(entry_id):
                account.add_feed(entry_id, False)
                n = Notification(entry_id, entry.title, doc.feed.title)
                account.new_unread.append (n)

    def get_dialog_def (self):
        return [{"label": "Url", "type" : "str"}]

    def populate_dialog(self, widget, acc):
        self._set_text_value ("Url",acc["url"])

    def set_account_data_from_widget(self, account_name, widget, account=None):
        url = self._get_text_value ("Url")
        if url=='':
            raise Exception(_("The url is mandatory"))

        #TODO check valid values
        if not account:
            props = {'name' : account_name, 'provider_name' : self.get_name(),
                'url' : url}
            account = self.load_account(props)
        else:
            account["url"] = url

        doc = feedparser.parse(account["url"])
        account["activate_url"] = doc.feed.link
        return account

class FeedAccount (Account):
    def __init__ (self, properties, provider):
        Account.__init__(self, properties, provider)
        self.total_unread = 0
        self.cache = FeedCache(self)
        self.cache.load()
        for f in self.cache.feeds.values():
            if not f.feed_read:
                self.total_unread = self.total_unread + 1

        self.new_unread = []

    def get_new_unread_notifications(self):
        return self.new_unread

    def add_feed(self, feed_id, feed_read):
        self.cache.add_feed(feed_id, feed_read);
        if not feed_read:
            self.total_unread = self.total_unread + 1
        self.cache.save()

    def has_feed(self, feed_id):
        return feed_id in self.cache.feeds

    def has_credentials(self):
        return False

    def get_total_unread (self):
        return self.total_unread

    def can_mark_read(self):
        return True

    def mark_read(self):
        for f in self.cache.feeds.values():
            f.feed_read = True
        self.cache.save()
        self.total_unread = 0
        #Update the unread items
        indicator.IndicatorManager.get_instance().get_indicator().update_account(self)

    def activate (self):
        self.mark_read()
        Account.activate(self)

class Feed:
    def __init__(self, data):
        self.feed_num = int(data[0])
        self.feed_id = data[1]
        self.feed_read = utils.get_boolean(data[2])

class FeedCache:
    def __init__(self, account):
        self.account = account

    def get_filename(self):
        return "feed-" + utils.get_safe_filename(self.account.get_name()) + ".csv"

    def get_filepath(self):
        return join(config.get_ensure_cache_path(), self.get_filename())

    def load(self):
        file_path = self.get_filepath()
        if not os.path.exists (file_path):
            f = open(file_path, "w")
            f.close()
        reader = csv.reader(open(file_path, "r+"), delimiter='\t')

        self.feeds = dict()
        self.last_num = -1
        for data in reader:
            feed_num = int(data[0])
            self.feeds[data[1]] = Feed(data)
            if feed_num > self.last_num:
                self.last_num = feed_num

    def save(self):
        rows = sorted(self.feeds.values(), key=lambda x: int(x.feed_num))
        num = len(rows)
        if num > 300:
            rows = rows[num - 300:]
        writer = csv.writer(open(self.get_filepath(), "w+"), delimiter='\t')
        num = 0
        for f in rows:
            writer.writerow((num, f.feed_id, f.feed_read))
            num = num + 1

    def add_feed(self, feed_id, feed_read):
        self.last_num = self.last_num + 1
        self.feeds[feed_id] = Feed((self.last_num, feed_id, feed_read))


########NEW FILE########
__FILENAME__ = gmailprovider
# -*- mode: python; tab-width: 4; indent-tabs-mode: nil -*-

from cloudsn import logger
from cloudsn.core.account import AccountCacheMails, AccountManager, Notification
from cloudsn.core.keyring import Credentials
from cloudsn.core import utils
from cloudsn.core import config
from cloudsn.providers.providersbase import ProviderBase
from xml.sax.handler import ContentHandler
from xml import sax
from gi.repository import Gtk, GdkPixbuf
import urllib2

class GMailProvider(ProviderBase):

    __default = None

    def __init__(self):
        if GMailProvider.__default:
           raise GMailProvider.__default
        ProviderBase.__init__(self, "GMail")

    @staticmethod
    def get_instance():
        if not GMailProvider.__default:
            GMailProvider.__default = GMailProvider()
        return GMailProvider.__default

    def load_account(self, props):
        return GMailAccount(props, self)

    def update_account (self, account):
        news = []
        notifications = {}
        labels = []
        if 'labels' in account.get_properties():
            labels += [l.strip() for l in account["labels"].split(",")]

        if 'inbox' not in labels and '' not in labels:
            labels.append('inbox')

        credentials = account.get_credentials()
        for label in labels:
            g = GmailAtom (credentials.username, credentials.password, label)
            g.refreshInfo()

            for mail in g.get_mails():
                notifications[mail.mail_id] = mail
                if mail.mail_id not in account.notifications:
                    news.append (Notification(mail.mail_id, mail.title, mail.author_name))

            account.total_unread = g.getUnreadMsgCount()

        account.new_unread = news;
        account.notifications = notifications

    def add_label_button_clicked_cb (self, widget, data=None):
        siter = self.labels_store.append()
        self.labels_store.set_value(siter, 0, _("Type the label name here"))
        selection = self.labels_treeview.get_selection()
        selection.select_iter(siter)
        model, path_list = selection.get_selected_rows()
        path = path_list[0]
        self.labels_treeview.grab_focus()
        self.labels_treeview.set_cursor(path,self.labels_treeview.get_column(0), True)


    def del_label_button_clicked_cb (self, widget, data=None):
        selection = self.labels_treeview.get_selection()
        model, path_list = selection.get_selected_rows()
        if path_list:
            path = path_list[0]
            siter = model.get_iter(path)
            self.labels_store.remove(siter)

    def label_cell_edited_cb(self, cell, path, new_text):
        siter = self.labels_store.get_iter((int(path), ))
        self.labels_store.set_value(siter, 0, new_text)

    def __get_labels(self):
        labels = []
        def add(model, path, siter, labels):
            label = model.get_value(siter, 0)
            labels.append(label)
        self.labels_store.foreach(add, labels)
        labels_string = ""
        for label in labels:
            labels_string += label + ","
        return labels_string[:len(labels_string)-1]

    def get_account_data_widget (self, account=None):
        self.builder=Gtk.Builder()
        self.builder.set_translation_domain("cloudsn")
        self.builder.add_from_file(config.add_data_prefix("gmail-account.ui"))
        box = self.builder.get_object("container")
        self.labels_store = self.builder.get_object("labels_store")
        self.labels_treeview = self.builder.get_object("labels_treeview")
        self.builder.connect_signals(self)
        if account:
            credentials = account.get_credentials_save()
            self.builder.get_object("username_entry").set_text(credentials.username)
            self.builder.get_object("password_entry").set_text(credentials.password)
            if 'labels' in account.get_properties():
                labels = [l.strip() for l in account["labels"].split(",")]
                for label in labels:
                    if label != '':
                        siter = self.labels_store.append()
                        self.labels_store.set_value(siter, 0, label)
        return box

    def set_account_data_from_widget(self, account_name, widget, account=None):
        username = self.builder.get_object("username_entry").get_text()
        password = self.builder.get_object("password_entry").get_text()
        if not account:
            props = {"name" : account_name, "provider_name" : self.get_name(),
                "labels" : self.__get_labels()}
            account = AccountCacheMails(props, self)
            account.notifications = {}
        else:
            account["labels"] = self.__get_labels()

        credentials = Credentials(username, password)
        account.set_credentials(credentials)

        return account

class GMailAccount(AccountCacheMails):
    def __init__(self, properties, provider):
        AccountCacheMails.__init__(self, properties, provider)

    def get_total_unread (self):
        return self.total_unread

    def activate (self):
        #Hack for gmail domains like mail.quiter.com
        #TODO check this when the user change the configuration too
        domain = None
        try:
            user, tmp, domain = self.get_credentials().username.partition('@')
        except Exception, e:
            logger.exception("Cannot load credentials for account "+acc.get_name()+", continue: %s", e)

        if domain and domain != "gmail.com":
            activate_url = "https://mail.google.com/a/" + domain
        else:
            activate_url = "https://mail.google.com/a/"

        self.properties["activate_url"] = activate_url

        AccountCacheMails.activate(self)

# Auxiliar structure
class Mail:
    mail_id=""
    title=""
    summary=""
    author_name=""
    author_addr=""

# Sax XML Handler
class MailHandler(ContentHandler):

	# Tags
    TAG_FEED = "feed"
    TAG_FULLCOUNT = "fullcount"
    TAG_ENTRY = "entry"
    TAG_TITLE = "title"
    TAG_SUMMARY = "summary"
    TAG_AUTHOR = "author"
    TAG_NAME = "name"
    TAG_EMAIL = "email"
    TAG_ID = "id"

    # Path the information
    PATH_FULLCOUNT = [ TAG_FEED, TAG_FULLCOUNT ]
    PATH_TITLE = [ TAG_FEED, TAG_ENTRY, TAG_TITLE ]
    PATH_ID = [ TAG_FEED, TAG_ENTRY, TAG_ID ]
    PATH_SUMMARY = [ TAG_FEED, TAG_ENTRY, TAG_SUMMARY ]
    PATH_AUTHOR_NAME = [ TAG_FEED, TAG_ENTRY, TAG_AUTHOR, TAG_NAME ]
    PATH_AUTHOR_EMAIL = [ TAG_FEED, TAG_ENTRY, TAG_AUTHOR, TAG_EMAIL ]

    def __init__(self):
        self.startDocument()

    def startDocument(self):
        self.entries=list()
        self.actual=list()
        self.mail_count="0"

    def startElement( self, name, attrs):
        # update actual path
        self.actual.append(name)

        # add a new email to the list
        if name=="entry":
            m = Mail()
            self.entries.append(m)

    def endElement( self, name):
        # update actual path
        self.actual.pop()

    def characters( self, content):
        # New messages count
        if (self.actual==self.PATH_FULLCOUNT):
            self.mail_count = self.mail_count+content

        # Message title
        if (self.actual==self.PATH_TITLE):
            temp_mail=self.entries.pop()
            temp_mail.title=temp_mail.title+content
            self.entries.append(temp_mail)

        if (self.actual==self.PATH_ID):
            temp_mail=self.entries.pop()
            temp_mail.mail_id=temp_mail.mail_id+content
            self.entries.append(temp_mail)

        # Message summary
        if (self.actual==self.PATH_SUMMARY):
            temp_mail=self.entries.pop()
            temp_mail.summary=temp_mail.summary+content
            self.entries.append(temp_mail)

        # Message author name
        if (self.actual==self.PATH_AUTHOR_NAME):
            temp_mail=self.entries.pop()
            temp_mail.author_name=temp_mail.author_name+content
            self.entries.append(temp_mail)

        # Message author email
        if (self.actual==self.PATH_AUTHOR_EMAIL):
            temp_mail=self.entries.pop()
            temp_mail.author_addr=temp_mail.author_addr+content
            self.entries.append(temp_mail)

    def getUnreadMsgCount(self):
        return int(self.mail_count)

# The mail class
class GmailAtom:

    realm = "New mail feed"
    host = "https://mail.google.com"
    url = host + "/mail/feed/atom"

    def __init__(self, user, pswd, label = None):
        self.m = MailHandler()
        self.label = label
        # initialize authorization handler
        auth_handler = urllib2.HTTPBasicAuthHandler()
        auth_handler.add_password( self.realm, self.host, user, pswd)
        self.opener = urllib2.build_opener(auth_handler)

    def sendRequest(self):
        url = self.url
        if self.label:
            url = url + "/" + self.label
        return self.opener.open(url)

    def refreshInfo(self):
        p = sax.parseString( self.sendRequest().read(), self.m)

    def getUnreadMsgCount(self):
        return self.m.getUnreadMsgCount()

    def get_mails (self):
        return self.m.entries


########NEW FILE########
__FILENAME__ = greaderprovider
# -*- mode: python; tab-width: 4; indent-tabs-mode: nil -*-
from cloudsn.core.account import AccountCacheMails, AccountManager, Notification
from cloudsn.providers.providersbase import ProviderUtilsBuilder
from cloudsn.core.keyring import Credentials
from cloudsn.core import utils
import urllib2
import re
import urllib
import xml.dom.minidom
from gi.repository import Gtk

class GReaderProvider(ProviderUtilsBuilder):

    __default = None

    def __init__(self):
        if GReaderProvider.__default:
           raise GReaderProvider.__default
        ProviderUtilsBuilder.__init__(self, "Google Reader", "greader")

    @staticmethod
    def get_instance():
        if not GReaderProvider.__default:
            GReaderProvider.__default = GReaderProvider()
        return GReaderProvider.__default

    def load_account(self, props):
        acc = AccountCacheMails(props, self)
        acc.properties["activate_url"] = "http://reader.google.com"
        return acc

    def update_account (self, account):
        credentials = account.get_credentials()
        g = GreaderAtom (credentials.username, credentials.password)
        g.refreshInfo()

        news = []
        new_count = g.getTotalUnread() - account.total_unread
        if new_count > 1:
            news.append(Notification('',
                _('%d new unread news of %i') % (new_count, g.getTotalUnread()),
                ''))
        elif new_count == 1:
            news.append(Notification('',
                _('%d new unread new of %i') % (new_count, g.getTotalUnread()),
                ''))

        account.new_unread = news;

        account.total_unread = g.getTotalUnread()

    def get_dialog_def (self):
        return [{"label": "User", "type" : "str"},
                {"label": "Password", "type" : "pwd"},
                {"label": "Show notifications", "type" : "check"}]

    def populate_dialog(self, widget, acc):
        credentials = acc.get_credentials_save()
        self._set_text_value ("User", credentials.username)
        self._set_text_value ("Password", credentials.password)
        if "show_notifications" in acc:
            show_notifications = acc["show_notifications"]
        else:
            show_notifications = True

        self._set_check_value("Show notifications", show_notifications)

    def set_account_data_from_widget(self, account_name, widget, account=None):
        username = self._get_text_value ("User")
        password = self._get_text_value ("Password")
        show_notifications = self._get_check_value("Show notifications")
        if username=='' or password=='':
            raise Exception(_("The user name and the password are mandatory"))

        if not account:
            props = {'name' : account_name, 'provider_name' : self.get_name(),
                'show_notifications' : show_notifications,
                'activate_url' : "http://reader.google.com"}
            account = self.load_account(props)
        else:
            account["show_notifications"] = show_notifications

        credentials = Credentials(username, password)
        account.set_credentials(credentials)

        return account

class GreaderAtom:

	auth_url = "https://www.google.com/accounts/ClientLogin"
	reader_url = "https://www.google.com/reader/api/0/unread-count?%s"

	def __init__(self, user, pswd):
		self.username = user
		self.password = pswd
		# initialize authorization handler
		_cproc = urllib2.HTTPCookieProcessor()
		self.opener = urllib2.build_opener(_cproc)
		urllib2.install_opener(self.opener)

	def sendRequest(self):
	    auth_req_data = urllib.urlencode({'Email': self.username,
                                  'Passwd': self.password,
                                  'service': 'reader'})
        auth_req = urllib2.Request(self.auth_url, data=auth_req_data)
        auth_resp_content = urllib2.urlopen(auth_req).read()
        auth_resp_dict = dict(x.split('=') for x in auth_resp_content.split('\n') if x)
        auth_token = auth_resp_dict["Auth"]
        
        # Create a cookie in the header using the SID 
        header = {}
        header['Authorization'] = 'GoogleLogin auth=%s' % auth_token

        reader_req_data = urllib.urlencode({'all': 'true',
                                            'output': 'xml'})
        
        reader_url = self.reader_url % (reader_req_data)
        reader_req = urllib2.Request(reader_url, None, header)
		return urllib2.urlopen(reader_req)

	def parseDocument (self, data):
		self.feeds=list()

		def processObject (ob):
			for c in ob.getElementsByTagName ("string"):
				if c.getAttribute("name") == "id":
					ftype, s, feed = c.childNodes[0].nodeValue.partition("/")
					self.feeds.append({"type" : ftype,
							   "feed" : feed})
					break

			for c in ob.getElementsByTagName ("number"):
				if c.getAttribute("name") == "count":
					self.feeds[-1]["count"] = c.childNodes[0].nodeValue
					break

		doc = xml.dom.minidom.parseString(data)
		elist = doc.childNodes[0].getElementsByTagName("list")[0]
		for e2 in elist.getElementsByTagName("object"):
			processObject (e2)

	def refreshInfo(self):
		self.parseDocument (self.sendRequest().read())

	def getTotalUnread(self):
		count = 0
		for feed in self.feeds:
			if feed["type"] == "user":
				name = feed["feed"]
				name = name[name.rfind ("/") + 1:]
				if name == "reading-list":
					count = int(feed["count"])

		return count


########NEW FILE########
__FILENAME__ = identicaprovider
from cloudsn.providers import tweepy
from providersbase import ProviderUtilsBuilder
from cloudsn import logger
from cloudsn.core.account import AccountCacheMails, AccountManager, Notification
from cloudsn.core.keyring import Credentials
from cloudsn.core.provider import Provider
from cloudsn.core import utils
from gi.repository import GObject
from gi.repository import Gtk

class IdenticaProvider(ProviderUtilsBuilder):

    __default = None

    def __init__(self, name = "Identi.ca", id_provider = "identica", activate_url = "http://identi.ca"):
        ProviderUtilsBuilder.__init__(self, name, id_provider)
        self.activate_url = activate_url
        
    @staticmethod
    def get_instance():
        if not IdenticaProvider.__default:
            IdenticaProvider.__default = IdenticaProvider()
        return IdenticaProvider.__default

    def load_account(self, props):
        acc = IdenticaAccount(props, self)
        acc.properties["activate_url"] = self.activate_url
        if not "since_id" in acc:
            acc["since_id"] = -1
        return acc

    def get_dialog_def (self):
        return [{"label": "User", "type" : "str"},
                {"label": "Password", "type" : "pwd"}]

    def populate_dialog(self, widget, acc):
        credentials = acc.get_credentials_save()
        self._set_text_value ("User",credentials.username)
        self._set_text_value ("Password", credentials.password)

    def set_account_data_from_widget(self, account_name, widget, account=None):
        username = self._get_text_value ("User")
        password = self._get_text_value ("Password")
        if username=='' or password=='':
            raise Exception(_("The user name and the password are mandatory"))

        if not account:
            props = {'name' : account_name, 'provider_name' : self.get_name(),
                'activate_url' : self.activate_url}
            account = self.load_account(props)

        account.set_credentials(Credentials(username, password))

        return account

    def get_api(self, account):
        credentials = account.get_credentials()
        auth = tweepy.BasicAuthHandler(credentials.username, credentials.password)
        api = tweepy.API(auth, "identi.ca",api_root="/api")
        return api
        
    def update_account (self, account):
        api = self.get_api(account)
        
        since_id = None
        if "since_id" in account and account["since_id"] != -1:
            since_id = account["since_id"]

        messages = api.home_timeline(since_id=since_id)

        if len(messages) < 1:
            account.new_unread = []
            return

        news = []
        if since_id:
            for m in messages:
                if m.id not in account.notifications:
                    account.notifications[m.id] = m.id
                    news.append (Notification(m.id, m.text, m.user.screen_name,
                                 self.get_message_icon(m)))
        else:
            #If it is the fist update, show the last message only
            account.notifications[messages[0].id] = messages[0].id
            news.append (Notification(messages[0].id, messages[0].text,
                         messages[0].user.screen_name,
                         self.get_message_icon(messages[0])))

        account.new_unread = news;
        account["since_id"] = messages[0].id
        GObject.idle_add(self.__save_account, account)
        
    def __save_account(self, account):
        AccountManager.get_instance().save_account(account)
        return False
        
    def get_message_icon(self,m):
        icon = None
        try:
            icon = utils.download_image_to_pixbuf(m.user.profile_image_url)
        except Exception, e:
            logger.exception("Error loading the user avatar")

        return icon

class IdenticaAccount (AccountCacheMails):

    def __init__(self, properties, provider):
        AccountCacheMails.__init__(self, properties, provider)

    def get_total_unread (self):
        return 0


########NEW FILE########
__FILENAME__ = imapprovider
# -*- mode: python; tab-width: 4; indent-tabs-mode: nil -*-
"""
Based on imap.py:

    Copyright 2009-2010 cGmail Core Team
    https://code.launchpad.net/cgmail

"""
from cloudsn.providers.providersbase import ProviderBase
from cloudsn.core.account import AccountCacheMails, AccountManager, Notification
from cloudsn.core.keyring import Credentials
from cloudsn.core import config
from cloudsn.core import utils
from cloudsn import logger
import imaplib
from email.Parser import HeaderParser
from gi.repository import Gtk, GdkPixbuf

class ImapProvider(ProviderBase):
    __default = None

    def __init__(self):
        if ImapProvider.__default:
           raise ImapProvider.__default
        ProviderBase.__init__(self, "Imap")

    @staticmethod
    def get_instance():
        if not ImapProvider.__default:
            ImapProvider.__default = ImapProvider()
        return ImapProvider.__default

    def load_account(self, props):
        return AccountCacheMails(props, self)

    def update_account (self, account):
        account.new_unread = []
        notifications = {}
        all_inbox = []
        credentials = account.get_credentials()

        #Main inbox
        all_inbox.append(ImapBox (account["host"], credentials.username,
            credentials.password, account["port"],
            utils.get_boolean(account["ssl"])))

        if 'labels' in account.get_properties():
            labels = []
            labels += [l.strip() for l in account["labels"].split(",")]
            for l in labels:
                if l != '':
                    all_inbox.append(ImapBox (account["host"], credentials.username,
                        credentials.password, account["port"],
                        utils.get_boolean(account["ssl"]),
                        False, l))

        for g in all_inbox:
            mails = g.get_mails()
            logger.debug("Checking label %s: %i" %(g.mbox_dir, len(mails)))
            for mail_id, sub, fr in mails:
                notifications[mail_id] = sub
                if mail_id not in account.notifications:
                    n = Notification(mail_id, sub, fr)
                    account.new_unread.append (n)

        account.notifications = notifications

    def get_account_data_widget (self, account=None):
        self.conf_widget = ImapPrefs(account, self)
        return self.conf_widget.load()

    def set_account_data_from_widget(self, account_name, widget, account=None):
        return self.conf_widget.set_account_data(account_name)

class ImapPrefs:

    def __init__(self, account, provider):
        self.account = account
        self.provider = provider

    def load(self):
        self.builder=Gtk.Builder()
        self.builder.set_translation_domain("cloudsn")
        self.builder.add_from_file(config.add_data_prefix("imap-account.ui"))
        self.box = self.builder.get_object("container")
        self.labels_store = self.builder.get_object("labels_store")
        self.labels_treeview = self.builder.get_object("labels_treeview")
        self.builder.connect_signals(self)
        if self.account:
            credentials = self.account.get_credentials_save()
            self.builder.get_object("host_entry").set_text(self.account["host"])
            self.builder.get_object("username_entry").set_text(credentials.username)
            self.builder.get_object("password_entry").set_text(credentials.password)
            self.builder.get_object("port_entry").set_text(str(self.account["port"]))
            self.builder.get_object("ssl_check").set_active(utils.get_boolean(self.account["ssl"]))
            if 'labels' in self.account.get_properties():
                labels = [l.strip() for l in self.account["labels"].split(",")]
                for label in labels:
                    if label != '':
                        siter = self.labels_store.append()
                        self.labels_store.set_value(siter, 0, label)
        return self.box

    def set_account_data (self, account_name):
        host = self.builder.get_object("host_entry").get_text()
        port = self.builder.get_object("port_entry").get_text()
        username = self.builder.get_object("username_entry").get_text()
        password = self.builder.get_object("password_entry").get_text()
        ssl = self.builder.get_object("ssl_check").get_active()
        if host=='' or username=='' or password=='':
            raise Exception(_("The host, user name and the password are mandatory"))

        if not self.account:
            props = {"name" : account_name, "provider_name" : self.provider.get_name(),
                "host": host, "port": port, "ssl": ssl,
                "labels" : self.__get_labels()}
            self.account = AccountCacheMails(props, self.provider)
            self.account.notifications = {}
        else:
            self.account["host"] = host
            self.account["port"] = port
            self.account["ssl"] = ssl
            self.account["labels"] = self.__get_labels()

        credentials = Credentials(username, password)
        self.account.set_credentials(credentials)

        return self.account

    def __get_labels(self):
        labels = []
        def add(model, path, siter, labels):
            label = model.get_value(siter, 0)
            labels.append(label)
        self.labels_store.foreach(add, labels)
        labels_string = ""
        for label in labels:
            labels_string += label + ","
        return labels_string[:len(labels_string)-1]

    def add_label_button_clicked_cb (self, widget, data=None):
        siter = self.labels_store.append()
        self.labels_store.set_value(siter, 0, _("Type the label name here"))
        selection = self.labels_treeview.get_selection()
        selection.select_iter(siter)
        model, path_list = selection.get_selected_rows()
        path = path_list[0]
        self.labels_treeview.grab_focus()
        self.labels_treeview.set_cursor(path,self.labels_treeview.get_column(0), True)


    def del_label_button_clicked_cb (self, widget, data=None):
        selection = self.labels_treeview.get_selection()
        model, path_list = selection.get_selected_rows()
        if path_list:
            path = path_list[0]
            siter = model.get_iter(path)
            self.labels_store.remove(siter)

    def label_cell_edited_cb(self, cell, path, new_text):
        siter = self.labels_store.get_iter((int(path), ))
        self.labels_store.set_value(siter, 0, new_text)


class ImapBoxConnectionError(Exception): pass
class ImapBoxAuthError(Exception): pass

class ImapBox:
	def __init__(self, host, user, password,
			port = 143, ssl = False,
			use_default_mbox = True,
			mbox_dir = None):
		self.user = user
		self.password = password
		self.port = int(port)
		self.host = host
		self.ssl = ssl
		self.use_default_mbox = use_default_mbox
		self.mbox_dir = mbox_dir

		self.mbox = None

	def __connect(self):
		if not self.ssl:
			self.mbox = imaplib.IMAP4(self.host, self.port)
		else:
			self.mbox = imaplib.IMAP4_SSL(self.host, self.port)

		self.mbox.login(self.user, self.password)

	def get_mails(self):

		try:
			self.__connect()
		except ImapBoxConnectionError:
			raise ImapBoxConnectionError()
		except ImapBoxAuthError:
			raise ImapBoxAuthError()

		mails = []
		try:
			if self.use_default_mbox:
				result, message = self.mbox.select(readonly=1)
			else:
				result, message = self.mbox.select(self.mbox_dir, readonly=1)
			if result != 'OK':
				raise Exception, message

			# retrieve only unseen messages
			typ, data = self.mbox.search(None, 'UNSEEN')
			for num in data[0].split():
				# fetch only needed fields
				f = self.mbox.fetch(num, '(BODY.PEEK[HEADER.FIELDS (SUBJECT FROM MESSAGE-ID)])')
				hp = HeaderParser()
				m = hp.parsestr(f[1][0][1])
				sub = utils.mime_decode(m['subject'])
				fr = utils.mime_decode(m['from'])
				mails.append([m['Message-ID'], sub, fr])
		except Exception, e:
			print str(e)

		self.mbox.logout()
		return mails


########NEW FILE########
__FILENAME__ = pop3provider
# -*- mode: python; tab-width: 4; indent-tabs-mode: nil -*-
from cloudsn.providers.providersbase import ProviderUtilsBuilder
from cloudsn.core.account import AccountCacheMails, AccountManager, Notification
from cloudsn.core.keyring import Credentials
from cloudsn.core import utils
from cloudsn.core.config import SettingsController
from cloudsn import logger

import poplib
from email.Parser import Parser as EmailParser
from email.header import decode_header
from gi.repository import Gtk

class Pop3Provider(ProviderUtilsBuilder):

    __default = None

    def __init__(self):
        if Pop3Provider.__default:
           raise Pop3Provider.__default
        ProviderUtilsBuilder.__init__(self, "Pop3")
        self.parser = EmailParser()

    @staticmethod
    def get_instance():
        if not Pop3Provider.__default:
            Pop3Provider.__default = Pop3Provider()
        return Pop3Provider.__default

    def load_account(self, props):
        acc = AccountCacheMails(props, self)
        if not "port" in acc:
            acc["port"] = 110
        if not "ssl" in acc:
            acc["ssl"] = False
        return acc
            
    def update_account (self, account):
    
        mbox = self.__connect(account)
        
        messages, new_messages = self.__get_mails(mbox, account)
        
        num_messages = len(new_messages)
        max_not = float(SettingsController.get_instance().get_prefs()["max_notifications"])
        
        account.new_unread = []
        for mail_id, mail_num in new_messages:
            account.notifications[mail_id] = mail_num
            #We only get the e-mail content if all will be shown
            if num_messages <= max_not:
                msgNum, sub, fr = self.__get_mail_content(mbox, mail_num)
                #Store the mail_id, not the msgNum
                n = Notification(mail_id, sub, fr)
            else:
                n = Notification(mail_id, "New mail", "unknow")
            account.new_unread.append (n)
        
        #Remove old unread mails not in the current list of unread mails
        #TODO Do this better!!!!!
        only_current_ids = []
        for mail_id, mail_num in messages:
            only_current_ids.append(mail_id)
        for nid in account.notifications.keys():
            if nid not in only_current_ids:
                del account.notifications[nid]
        
        mbox.quit()

    def get_dialog_def (self):
        return [{"label": "Host", "type" : "str"},
                {"label": "User", "type" : "str"},
                {"label": "Password", "type" : "pwd"},
                {"label": "Port", "type" : "str"},
                {"label": "Use SSL", "type" : "check"}]
    
    def populate_dialog(self, widget, acc):
        credentials = acc.get_credentials_save()
        self._set_text_value ("Host",acc["host"])
        self._set_text_value ("User", credentials.username)
        self._set_text_value ("Password", credentials.password)
        self._set_text_value ("Port",str(acc["port"]))
        self._set_check_value ("Use SSL",utils.get_boolean(acc["ssl"]))
    
    def set_account_data_from_widget(self, account_name, widget, account=None):
        host = self._get_text_value ("Host")
        username = self._get_text_value ("User")
        password = self._get_text_value ("Password")
        port = self._get_text_value ("Port")
        ssl = self._get_check_value("Use SSL")
        if host=='' or username=='' or password=='':
            raise Exception(_("The host, user name and the password are mandatory"))
        
        if not account:
            props = {'name' : account_name, 'provider_name' : self.get_name(),
                'host' : host, 'port' : port, 'ssl' : ssl}
            account = self.load_account(props)
        else:
            account["host"] = host
            account["port"] = int(port)
            account["ssl"] = ssl
            
        account.set_credentials(Credentials(username, password))
        return account
    
    #************** email methods **************
    def __connect(self, account):
        credentials = account.get_credentials()
        port = 110
        if "port" in account:
            port = int(float(account["port"]))
            
        if not utils.get_boolean(account["ssl"]):
            mbox = poplib.POP3(account["host"], port)
        else:
            mbox = poplib.POP3_SSL(account["host"], port)
        mbox.user(credentials.username)
        mbox.pass_(credentials.password)
        
        return mbox
        
    def __get_mails(self, mbox, account):
        """ Returns:
            [list of [msgId, msgNum] all mails, list of [msgId, msgNum] new mails"""
        
        new_messages = []
        messages = []
        ids = mbox.uidl()
        max_not = float(SettingsController.get_instance().get_prefs()["max_notifications"])
        for id_pop in ids[1]:
            msgNum = int(id_pop.split(" ")[0])
            msgId = id_pop.split(" ")[1]
            
            messages.append( [msgId, msgNum] )
            if msgId not in account.notifications:
                new_messages.append( [msgId, msgNum] )

        return [messages, new_messages]
        
    def __get_mail_content(self, mbox, msgNum):
        # retrieve only the header
        st = "\n".join(mbox.top(msgNum, 0)[1])
        #print st
        #print "----------------------------------------"
        msg = self.parser.parsestr(st, True) # header only
        sub = utils.mime_decode(msg.get("Subject"))
        fr = utils.mime_decode(msg.get("From"))
        return [msgNum, sub, fr]


########NEW FILE########
__FILENAME__ = providersbase
# -*- mode: python; tab-width: 4; indent-tabs-mode: nil -*-
from cloudsn.core.account import AccountCacheMails, AccountManager, Notification
from cloudsn.core.provider import Provider
from cloudsn.core import utils
from cloudsn.core import config
from cloudsn.ui.utils import create_provider_widget, get_widget_by_label
from xml.sax.handler import ContentHandler
from xml import sax
from gi.repository import Gtk, GdkPixbuf, Gio
import urllib2

class ProviderBase(Provider):

    def __init__(self, name, id_provider = None):
        Provider.__init__(self, name)
        self.id_provider = id_provider
        if not id_provider:
            self.id_provider = name
        self.id_provider = self.id_provider.lower()
        self.icon_path = config.add_data_prefix(self.id_provider + '.png')
        self.icon = GdkPixbuf.Pixbuf.new_from_file(self.icon_path)
        self.gicon = Gio.FileIcon.new(Gio.File.new_for_path(self.icon_path))

class ProviderGtkBuilder(ProviderBase):

    def __init__(self, name,id_provider = None):
        ProviderBase.__init__(self, name, id_provider)
        self._builder = None

    def _create_dialog(self, parent):
        self._builder=Gtk.Builder()
        self._builder.set_translation_domain("cloudsn")
        self._builder.add_from_file(config.add_data_prefix(self.id_provider + ".ui"))
        dialog = self._builder.get_object("main")
        self._builder.connect_signals(self)
        return dialog

    def populate_dialog(self, builder, acc):
        raise NotImplementedError("The provider must implement this method")

    def get_account_data_widget (self, account=None):
        box = self._create_dialog(parent).get_child()
        if account:
            self.populate_dialog(self.builder, account)

    def _get_text_value (self, widget_name):
        return self._builder.get_object(widget_name).get_text()

    def _set_text_value (self, widget_name, value):
        return self._builder.get_object(widget_name).set_text(value)


class ProviderUtilsBuilder(ProviderBase):

    def __init__(self, name,id_provider = None):
        ProviderBase.__init__(self, name, id_provider)
        self.box=None

    def get_dialog_def(self):
        raise NotImplementedError("The provider must implement this method")

    def populate_dialog(widget, account):
        raise NotImplementedError("The provider must implement this method")

    def get_account_data_widget (self, account=None):
        self.box = create_provider_widget (self.get_dialog_def())
        if account:
            self.populate_dialog(self.box, account)
        return self.box

    def _get_text_value (self, label):
        return get_widget_by_label(self.box, label).get_text()

    def _set_text_value (self, label, value):
        return get_widget_by_label(self.box, label).set_text(value)

    def _get_check_value (self, label):
        return get_widget_by_label(self.box, label).get_active()

    def _set_check_value (self, label, value):
        return get_widget_by_label(self.box, label).set_active(utils.get_boolean(value))


########NEW FILE########
__FILENAME__ = api
# Tweepy
# Copyright 2009-2010 Joshua Roesslein
# See LICENSE for details.

import os
import mimetypes

from binder import bind_api
from error import TweepError
from parsers import ModelParser
from utils import list_to_csv


class API(object):
    """Twitter API"""

    def __init__(self, auth_handler=None,
            host='api.twitter.com', search_host='search.twitter.com',
             cache=None, secure=False, api_root='/1', search_root='',
            retry_count=0, retry_delay=0, retry_errors=None,
            parser=None):
        self.auth = auth_handler
        self.host = host
        self.search_host = search_host
        self.api_root = api_root
        self.search_root = search_root
        self.cache = cache
        self.secure = secure
        self.retry_count = retry_count
        self.retry_delay = retry_delay
        self.retry_errors = retry_errors
        self.parser = parser or ModelParser()

    """ statuses/public_timeline """
    public_timeline = bind_api(
        path = '/statuses/public_timeline.json',
        payload_type = 'status', payload_list = True,
        allowed_param = []
    )

    """ statuses/home_timeline """
    home_timeline = bind_api(
        path = '/statuses/home_timeline.json',
        payload_type = 'status', payload_list = True,
        allowed_param = ['since_id', 'max_id', 'count', 'page'],
        require_auth = True
    )

    """ statuses/friends_timeline """
    friends_timeline = bind_api(
        path = '/statuses/friends_timeline.json',
        payload_type = 'status', payload_list = True,
        allowed_param = ['since_id', 'max_id', 'count', 'page'],
        require_auth = True
    )

    """ statuses/user_timeline """
    user_timeline = bind_api(
        path = '/statuses/user_timeline.json',
        payload_type = 'status', payload_list = True,
        allowed_param = ['id', 'user_id', 'screen_name', 'since_id',
                          'max_id', 'count', 'page', 'include_rts']
    )

    """ statuses/mentions """
    mentions = bind_api(
        path = '/statuses/mentions.json',
        payload_type = 'status', payload_list = True,
        allowed_param = ['since_id', 'max_id', 'count', 'page'],
        require_auth = True
    )

    """/statuses/:id/retweeted_by.format"""
    retweeted_by = bind_api(
        path = '/statuses/{id}/retweeted_by.json',
        payload_type = 'status', payload_list = True,
        allowed_param = ['id', 'count', 'page'],
        require_auth = True
    )

    """/statuses/:id/retweeted_by/ids.format"""
    retweeted_by_ids = bind_api(
        path = '/statuses/{id}/retweeted_by/ids.json',
        payload_type = 'ids',
        allowed_param = ['id', 'count', 'page'],
        require_auth = True
    )

    """ statuses/retweeted_by_me """
    retweeted_by_me = bind_api(
        path = '/statuses/retweeted_by_me.json',
        payload_type = 'status', payload_list = True,
        allowed_param = ['since_id', 'max_id', 'count', 'page'],
        require_auth = True
    )

    """ statuses/retweeted_to_me """
    retweeted_to_me = bind_api(
        path = '/statuses/retweeted_to_me.json',
        payload_type = 'status', payload_list = True,
        allowed_param = ['since_id', 'max_id', 'count', 'page'],
        require_auth = True
    )

    """ statuses/retweets_of_me """
    retweets_of_me = bind_api(
        path = '/statuses/retweets_of_me.json',
        payload_type = 'status', payload_list = True,
        allowed_param = ['since_id', 'max_id', 'count', 'page'],
        require_auth = True
    )

    """ statuses/show """
    get_status = bind_api(
        path = '/statuses/show.json',
        payload_type = 'status',
        allowed_param = ['id']
    )

    """ statuses/update """
    update_status = bind_api(
        path = '/statuses/update.json',
        method = 'POST',
        payload_type = 'status',
        allowed_param = ['status', 'in_reply_to_status_id', 'lat', 'long', 'source', 'place_id'],
        require_auth = True
    )

    """ statuses/destroy """
    destroy_status = bind_api(
        path = '/statuses/destroy.json',
        method = 'DELETE',
        payload_type = 'status',
        allowed_param = ['id'],
        require_auth = True
    )

    """ statuses/retweet """
    retweet = bind_api(
        path = '/statuses/retweet/{id}.json',
        method = 'POST',
        payload_type = 'status',
        allowed_param = ['id'],
        require_auth = True
    )

    """ statuses/retweets """
    retweets = bind_api(
        path = '/statuses/retweets/{id}.json',
        payload_type = 'status', payload_list = True,
        allowed_param = ['id', 'count'],
        require_auth = True
    )

    """ users/show """
    get_user = bind_api(
        path = '/users/show.json',
        payload_type = 'user',
        allowed_param = ['id', 'user_id', 'screen_name']
    )

    """ Perform bulk look up of users from user ID or screenname """
    def lookup_users(self, user_ids=None, screen_names=None):
        return self._lookup_users(list_to_csv(user_ids), list_to_csv(screen_names))

    _lookup_users = bind_api(
        path = '/users/lookup.json',
        payload_type = 'user', payload_list = True,
        allowed_param = ['user_id', 'screen_name'],
        require_auth = True
    )

    """ Get the authenticated user """
    def me(self):
        return self.get_user(screen_name=self.auth.get_username())

    """ users/search """
    search_users = bind_api(
        path = '/users/search.json',
        payload_type = 'user', payload_list = True,
        require_auth = True,
        allowed_param = ['q', 'per_page', 'page']
    )

    """ statuses/friends """
    friends = bind_api(
        path = '/statuses/friends.json',
        payload_type = 'user', payload_list = True,
        allowed_param = ['id', 'user_id', 'screen_name', 'page', 'cursor']
    )

    """ statuses/followers """
    followers = bind_api(
        path = '/statuses/followers.json',
        payload_type = 'user', payload_list = True,
        allowed_param = ['id', 'user_id', 'screen_name', 'page', 'cursor']
    )

    """ direct_messages """
    direct_messages = bind_api(
        path = '/direct_messages.json',
        payload_type = 'direct_message', payload_list = True,
        allowed_param = ['since_id', 'max_id', 'count', 'page'],
        require_auth = True
    )

    """ direct_messages/sent """
    sent_direct_messages = bind_api(
        path = '/direct_messages/sent.json',
        payload_type = 'direct_message', payload_list = True,
        allowed_param = ['since_id', 'max_id', 'count', 'page'],
        require_auth = True
    )

    """ direct_messages/new """
    send_direct_message = bind_api(
        path = '/direct_messages/new.json',
        method = 'POST',
        payload_type = 'direct_message',
        allowed_param = ['user', 'screen_name', 'user_id', 'text'],
        require_auth = True
    )

    """ direct_messages/destroy """
    destroy_direct_message = bind_api(
        path = '/direct_messages/destroy.json',
        method = 'DELETE',
        payload_type = 'direct_message',
        allowed_param = ['id'],
        require_auth = True
    )

    """ friendships/create """
    create_friendship = bind_api(
        path = '/friendships/create.json',
        method = 'POST',
        payload_type = 'user',
        allowed_param = ['id', 'user_id', 'screen_name', 'follow'],
        require_auth = True
    )

    """ friendships/destroy """
    destroy_friendship = bind_api(
        path = '/friendships/destroy.json',
        method = 'DELETE',
        payload_type = 'user',
        allowed_param = ['id', 'user_id', 'screen_name'],
        require_auth = True
    )

    """ friendships/exists """
    exists_friendship = bind_api(
        path = '/friendships/exists.json',
        payload_type = 'json',
        allowed_param = ['user_a', 'user_b']
    )

    """ friendships/show """
    show_friendship = bind_api(
        path = '/friendships/show.json',
        payload_type = 'friendship',
        allowed_param = ['source_id', 'source_screen_name',
                          'target_id', 'target_screen_name']
    )

    """ friends/ids """
    friends_ids = bind_api(
        path = '/friends/ids.json',
        payload_type = 'ids',
        allowed_param = ['id', 'user_id', 'screen_name', 'cursor']
    )

    """ friendships/incoming """
    friendships_incoming = bind_api(
        path = '/friendships/incoming.json',
        payload_type = 'ids',
        allowed_param = ['cursor']
    )

    """ friendships/outgoing"""
    friendships_outgoing = bind_api(
        path = '/friendships/outgoing.json',
        payload_type = 'ids',
        allowed_param = ['cursor']
    )

    """ followers/ids """
    followers_ids = bind_api(
        path = '/followers/ids.json',
        payload_type = 'ids',
        allowed_param = ['id', 'user_id', 'screen_name', 'cursor']
    )

    """ account/verify_credentials """
    def verify_credentials(self):
        try:
            return bind_api(
                path = '/account/verify_credentials.json',
                payload_type = 'user',
                require_auth = True
            )(self)
        except TweepError:
            return False

    """ account/rate_limit_status """
    rate_limit_status = bind_api(
        path = '/account/rate_limit_status.json',
        payload_type = 'json'
    )

    """ account/update_delivery_device """
    set_delivery_device = bind_api(
        path = '/account/update_delivery_device.json',
        method = 'POST',
        allowed_param = ['device'],
        payload_type = 'user',
        require_auth = True
    )

    """ account/update_profile_colors """
    update_profile_colors = bind_api(
        path = '/account/update_profile_colors.json',
        method = 'POST',
        payload_type = 'user',
        allowed_param = ['profile_background_color', 'profile_text_color',
                          'profile_link_color', 'profile_sidebar_fill_color',
                          'profile_sidebar_border_color'],
        require_auth = True
    )

    """ account/update_profile_image """
    def update_profile_image(self, filename):
        headers, post_data = API._pack_image(filename, 700)
        return bind_api(
            path = '/account/update_profile_image.json',
            method = 'POST',
            payload_type = 'user',
            require_auth = True
        )(self, post_data=post_data, headers=headers)

    """ account/update_profile_background_image """
    def update_profile_background_image(self, filename, *args, **kargs):
        headers, post_data = API._pack_image(filename, 800)
        bind_api(
            path = '/account/update_profile_background_image.json',
            method = 'POST',
            payload_type = 'user',
            allowed_param = ['tile'],
            require_auth = True
        )(self, post_data=post_data, headers=headers)

    """ account/update_profile """
    update_profile = bind_api(
        path = '/account/update_profile.json',
        method = 'POST',
        payload_type = 'user',
        allowed_param = ['name', 'url', 'location', 'description'],
        require_auth = True
    )

    """ favorites """
    favorites = bind_api(
        path = '/favorites.json',
        payload_type = 'status', payload_list = True,
        allowed_param = ['id', 'page']
    )

    """ favorites/create """
    create_favorite = bind_api(
        path = '/favorites/create/{id}.json',
        method = 'POST',
        payload_type = 'status',
        allowed_param = ['id'],
        require_auth = True
    )

    """ favorites/destroy """
    destroy_favorite = bind_api(
        path = '/favorites/destroy/{id}.json',
        method = 'DELETE',
        payload_type = 'status',
        allowed_param = ['id'],
        require_auth = True
    )

    """ notifications/follow """
    enable_notifications = bind_api(
        path = '/notifications/follow.json',
        method = 'POST',
        payload_type = 'user',
        allowed_param = ['id', 'user_id', 'screen_name'],
        require_auth = True
    )

    """ notifications/leave """
    disable_notifications = bind_api(
        path = '/notifications/leave.json',
        method = 'POST',
        payload_type = 'user',
        allowed_param = ['id', 'user_id', 'screen_name'],
        require_auth = True
    )

    """ blocks/create """
    create_block = bind_api(
        path = '/blocks/create.json',
        method = 'POST',
        payload_type = 'user',
        allowed_param = ['id', 'user_id', 'screen_name'],
        require_auth = True
    )

    """ blocks/destroy """
    destroy_block = bind_api(
        path = '/blocks/destroy.json',
        method = 'DELETE',
        payload_type = 'user',
        allowed_param = ['id', 'user_id', 'screen_name'],
        require_auth = True
    )

    """ blocks/exists """
    def exists_block(self, *args, **kargs):
        try:
            bind_api(
                path = '/blocks/exists.json',
                allowed_param = ['id', 'user_id', 'screen_name'],
                require_auth = True
            )(self, *args, **kargs)
        except TweepError:
            return False
        return True

    """ blocks/blocking """
    blocks = bind_api(
        path = '/blocks/blocking.json',
        payload_type = 'user', payload_list = True,
        allowed_param = ['page'],
        require_auth = True
    )

    """ blocks/blocking/ids """
    blocks_ids = bind_api(
        path = '/blocks/blocking/ids.json',
        payload_type = 'json',
        require_auth = True
    )

    """ report_spam """
    report_spam = bind_api(
        path = '/report_spam.json',
        method = 'POST',
        payload_type = 'user',
        allowed_param = ['id', 'user_id', 'screen_name'],
        require_auth = True
    )

    """ saved_searches """
    saved_searches = bind_api(
        path = '/saved_searches.json',
        payload_type = 'saved_search', payload_list = True,
        require_auth = True
    )

    """ saved_searches/show """
    get_saved_search = bind_api(
        path = '/saved_searches/show/{id}.json',
        payload_type = 'saved_search',
        allowed_param = ['id'],
        require_auth = True
    )

    """ saved_searches/create """
    create_saved_search = bind_api(
        path = '/saved_searches/create.json',
        method = 'POST',
        payload_type = 'saved_search',
        allowed_param = ['query'],
        require_auth = True
    )

    """ saved_searches/destroy """
    destroy_saved_search = bind_api(
        path = '/saved_searches/destroy/{id}.json',
        method = 'DELETE',
        payload_type = 'saved_search',
        allowed_param = ['id'],
        require_auth = True
    )

    """ help/test """
    def test(self):
        try:
            bind_api(
                path = '/help/test.json',
            )(self)
        except TweepError:
            return False
        return True

    def create_list(self, *args, **kargs):
        return bind_api(
            path = '/%s/lists.json' % self.auth.get_username(),
            method = 'POST',
            payload_type = 'list',
            allowed_param = ['name', 'mode', 'description'],
            require_auth = True
        )(self, *args, **kargs)

    def destroy_list(self, slug):
        return bind_api(
            path = '/%s/lists/%s.json' % (self.auth.get_username(), slug),
            method = 'DELETE',
            payload_type = 'list',
            require_auth = True
        )(self)

    def update_list(self, slug, *args, **kargs):
        return bind_api(
            path = '/%s/lists/%s.json' % (self.auth.get_username(), slug),
            method = 'POST',
            payload_type = 'list',
            allowed_param = ['name', 'mode', 'description'],
            require_auth = True
        )(self, *args, **kargs)

    lists = bind_api(
        path = '/{user}/lists.json',
        payload_type = 'list', payload_list = True,
        allowed_param = ['user', 'cursor'],
        require_auth = True
    )

    lists_memberships = bind_api(
        path = '/{user}/lists/memberships.json',
        payload_type = 'list', payload_list = True,
        allowed_param = ['user', 'cursor'],
        require_auth = True
    )

    lists_subscriptions = bind_api(
        path = '/{user}/lists/subscriptions.json',
        payload_type = 'list', payload_list = True,
        allowed_param = ['user', 'cursor'],
        require_auth = True
    )

    list_timeline = bind_api(
        path = '/{owner}/lists/{slug}/statuses.json',
        payload_type = 'status', payload_list = True,
        allowed_param = ['owner', 'slug', 'since_id', 'max_id', 'per_page', 'page']
    )

    get_list = bind_api(
        path = '/{owner}/lists/{slug}.json',
        payload_type = 'list',
        allowed_param = ['owner', 'slug']
    )

    def add_list_member(self, slug, *args, **kargs):
        return bind_api(
            path = '/%s/%s/members.json' % (self.auth.get_username(), slug),
            method = 'POST',
            payload_type = 'list',
            allowed_param = ['id'],
            require_auth = True
        )(self, *args, **kargs)

    def remove_list_member(self, slug, *args, **kargs):
        return bind_api(
            path = '/%s/%s/members.json' % (self.auth.get_username(), slug),
            method = 'DELETE',
            payload_type = 'list',
            allowed_param = ['id'],
            require_auth = True
        )(self, *args, **kargs)

    list_members = bind_api(
        path = '/{owner}/{slug}/members.json',
        payload_type = 'user', payload_list = True,
        allowed_param = ['owner', 'slug', 'cursor']
    )

    def is_list_member(self, owner, slug, user_id):
        try:
            return bind_api(
                path = '/%s/%s/members/%s.json' % (owner, slug, user_id),
                payload_type = 'user'
            )(self)
        except TweepError:
            return False

    subscribe_list = bind_api(
        path = '/{owner}/{slug}/subscribers.json',
        method = 'POST',
        payload_type = 'list',
        allowed_param = ['owner', 'slug'],
        require_auth = True
    )

    unsubscribe_list = bind_api(
        path = '/{owner}/{slug}/subscribers.json',
        method = 'DELETE',
        payload_type = 'list',
        allowed_param = ['owner', 'slug'],
        require_auth = True
    )

    list_subscribers = bind_api(
        path = '/{owner}/{slug}/subscribers.json',
        payload_type = 'user', payload_list = True,
        allowed_param = ['owner', 'slug', 'cursor']
    )

    def is_subscribed_list(self, owner, slug, user_id):
        try:
            return bind_api(
                path = '/%s/%s/subscribers/%s.json' % (owner, slug, user_id),
                payload_type = 'user'
            )(self)
        except TweepError:
            return False

    """ trends/available """
    trends_available = bind_api(
        path = '/trends/available.json',
        payload_type = 'json',
        allowed_param = ['lat', 'long']
    )

    """ trends/location """
    trends_location = bind_api(
        path = '/trends/{woeid}.json',
        payload_type = 'json',
        allowed_param = ['woeid']
    )

    """ search """
    search = bind_api(
        search_api = True,
        path = '/search.json',
        payload_type = 'search_result', payload_list = True,
        allowed_param = ['q', 'lang', 'locale', 'rpp', 'page', 'since_id', 'geocode', 'show_user', 'max_id', 'since', 'until', 'result_type']
    )
    search.pagination_mode = 'page'

    """ trends """
    trends = bind_api(
        path = '/trends.json',
        payload_type = 'json'
    )

    """ trends/current """
    trends_current = bind_api(
        path = '/trends/current.json',
        payload_type = 'json',
        allowed_param = ['exclude']
    )

    """ trends/daily """
    trends_daily = bind_api(
        path = '/trends/daily.json',
        payload_type = 'json',
        allowed_param = ['date', 'exclude']
    )

    """ trends/weekly """
    trends_weekly = bind_api(
        path = '/trends/weekly.json',
        payload_type = 'json',
        allowed_param = ['date', 'exclude']
    )

    """ geo/reverse_geocode """
    reverse_geocode = bind_api(
        path = '/geo/reverse_geocode.json',
        payload_type = 'json',
        allowed_param = ['lat', 'long', 'accuracy', 'granularity', 'max_results']
    )

    """ geo/nearby_places """
    nearby_places = bind_api(
        path = '/geo/nearby_places.json',
        payload_type = 'json',
        allowed_param = ['lat', 'long', 'ip', 'accuracy', 'granularity', 'max_results']
    )

    """ geo/id """
    geo_id = bind_api(
        path = '/geo/id/{id}.json',
        payload_type = 'json',
        allowed_param = ['id']
    )

    """ Internal use only """
    @staticmethod
    def _pack_image(filename, max_size):
        """Pack image from file into multipart-formdata post body"""
        # image must be less than 700kb in size
        try:
            if os.path.getsize(filename) > (max_size * 1024):
                raise TweepError('File is too big, must be less than 700kb.')
        except os.error, e:
            raise TweepError('Unable to access file')

        # image must be gif, jpeg, or png
        file_type = mimetypes.guess_type(filename)
        if file_type is None:
            raise TweepError('Could not determine file type')
        file_type = file_type[0]
        if file_type not in ['image/gif', 'image/jpeg', 'image/png']:
            raise TweepError('Invalid file type for image: %s' % file_type)

        # build the mulitpart-formdata body
        fp = open(filename, 'rb')
        BOUNDARY = 'Tw3ePy'
        body = []
        body.append('--' + BOUNDARY)
        body.append('Content-Disposition: form-data; name="image"; filename="%s"' % filename)
        body.append('Content-Type: %s' % file_type)
        body.append('')
        body.append(fp.read())
        body.append('--' + BOUNDARY + '--')
        body.append('')
        fp.close()
        body = '\r\n'.join(body)

        # build headers
        headers = {
            'Content-Type': 'multipart/form-data; boundary=Tw3ePy',
            'Content-Length': len(body)
        }

        return headers, body


########NEW FILE########
__FILENAME__ = auth
# Tweepy
# Copyright 2009-2010 Joshua Roesslein
# See LICENSE for details.

from urllib2 import Request, urlopen
import base64

import oauth
from error import TweepError
from api import API


class AuthHandler(object):

    def apply_auth(self, url, method, headers, parameters):
        """Apply authentication headers to request"""
        raise NotImplementedError

    def get_username(self):
        """Return the username of the authenticated user"""
        raise NotImplementedError


class BasicAuthHandler(AuthHandler):

    def __init__(self, username, password):
        self.username = username
        self._b64up = base64.b64encode('%s:%s' % (username, password))

    def apply_auth(self, url, method, headers, parameters):
        headers['Authorization'] = 'Basic %s' % self._b64up

    def get_username(self):
        return self.username


class OAuthHandler(AuthHandler):
    """OAuth authentication handler"""

    OAUTH_HOST = 'api.twitter.com'
    OAUTH_ROOT = '/oauth/'

    def __init__(self, consumer_key, consumer_secret, callback=None, secure=False):
        self._consumer = oauth.OAuthConsumer(consumer_key, consumer_secret)
        self._sigmethod = oauth.OAuthSignatureMethod_HMAC_SHA1()
        self.request_token = None
        self.access_token = None
        self.callback = callback
        self.username = None
        self.secure = secure

    def _get_oauth_url(self, endpoint, secure=False):
        if self.secure or secure:
            prefix = 'https://'
        else:
            prefix = 'http://'

        return prefix + self.OAUTH_HOST + self.OAUTH_ROOT + endpoint

    def apply_auth(self, url, method, headers, parameters):
        request = oauth.OAuthRequest.from_consumer_and_token(
            self._consumer, http_url=url, http_method=method,
            token=self.access_token, parameters=parameters
        )
        request.sign_request(self._sigmethod, self._consumer, self.access_token)
        headers.update(request.to_header())

    def _get_request_token(self):
        try:
            url = self._get_oauth_url('request_token')
            request = oauth.OAuthRequest.from_consumer_and_token(
                self._consumer, http_url=url, callback=self.callback
            )
            request.sign_request(self._sigmethod, self._consumer, None)
            resp = urlopen(Request(url, headers=request.to_header()))
            return oauth.OAuthToken.from_string(resp.read())
        except Exception, e:
            raise TweepError(e)

    def set_request_token(self, key, secret):
        self.request_token = oauth.OAuthToken(key, secret)

    def set_access_token(self, key, secret):
        self.access_token = oauth.OAuthToken(key, secret)

    def get_authorization_url(self, signin_with_twitter=False):
        """Get the authorization URL to redirect the user"""
        try:
            # get the request token
            self.request_token = self._get_request_token()

            # build auth request and return as url
            if signin_with_twitter:
                url = self._get_oauth_url('authenticate')
            else:
                url = self._get_oauth_url('authorize')
            request = oauth.OAuthRequest.from_token_and_callback(
                token=self.request_token, http_url=url
            )

            return request.to_url()
        except Exception, e:
            raise TweepError(e)

    def get_access_token(self, verifier=None):
        """
        After user has authorized the request token, get access token
        with user supplied verifier.
        """
        try:
            url = self._get_oauth_url('access_token')

            # build request
            request = oauth.OAuthRequest.from_consumer_and_token(
                self._consumer,
                token=self.request_token, http_url=url,
                verifier=str(verifier)
            )
            request.sign_request(self._sigmethod, self._consumer, self.request_token)

            # send request
            resp = urlopen(Request(url, headers=request.to_header()))
            self.access_token = oauth.OAuthToken.from_string(resp.read())
            return self.access_token
        except Exception, e:
            raise TweepError(e)

    def get_xauth_access_token(self, username, password):
        """
        Get an access token from an username and password combination.
        In order to get this working you need to create an app at
        http://twitter.com/apps, after that send a mail to api@twitter.com
        and request activation of xAuth for it.
        """
        try:
            url = self._get_oauth_url('access_token', secure=True) # must use HTTPS
            request = oauth.OAuthRequest.from_consumer_and_token(
                oauth_consumer=self._consumer,
                http_method='POST', http_url=url,
                parameters = {
		            'x_auth_mode': 'client_auth',
		            'x_auth_username': username,
		            'x_auth_password': password
                }
            )
            request.sign_request(self._sigmethod, self._consumer, None)

            resp = urlopen(Request(url, data=request.to_postdata()))
            self.access_token = oauth.OAuthToken.from_string(resp.read())
            return self.access_token
        except Exception, e:
            raise TweepError(e)

    def get_username(self):
        if self.username is None:
            api = API(self)
            user = api.verify_credentials()
            if user:
                self.username = user.screen_name
            else:
                raise TweepError("Unable to get username, invalid oauth token!")
        return self.username


########NEW FILE########
__FILENAME__ = binder
# Tweepy
# Copyright 2009-2010 Joshua Roesslein
# See LICENSE for details.

import httplib
import urllib
import time
import re

from error import TweepError
from utils import convert_to_utf8_str
from models import Model

re_path_template = re.compile('{\w+}')


def bind_api(**config):

    class APIMethod(object):

        path = config['path']
        payload_type = config.get('payload_type', None)
        payload_list = config.get('payload_list', False)
        allowed_param = config.get('allowed_param', [])
        method = config.get('method', 'GET')
        require_auth = config.get('require_auth', False)
        search_api = config.get('search_api', False)

        def __init__(self, api, args, kargs):
            # If authentication is required and no credentials
            # are provided, throw an error.
            if self.require_auth and not api.auth:
                raise TweepError('Authentication required!')

            self.api = api
            self.post_data = kargs.pop('post_data', None)
            self.retry_count = kargs.pop('retry_count', api.retry_count)
            self.retry_delay = kargs.pop('retry_delay', api.retry_delay)
            self.retry_errors = kargs.pop('retry_errors', api.retry_errors)
            self.headers = kargs.pop('headers', {})
            self.build_parameters(args, kargs)

            # Pick correct URL root to use
            if self.search_api:
                self.api_root = api.search_root
            else:
                self.api_root = api.api_root

            # Perform any path variable substitution
            self.build_path()

            if api.secure:
                self.scheme = 'https://'
            else:
                self.scheme = 'http://'

            if self.search_api:
                self.host = api.search_host
            else:
                self.host = api.host

            # Manually set Host header to fix an issue in python 2.5
            # or older where Host is set including the 443 port.
            # This causes Twitter to issue 301 redirect.
            # See Issue http://github.com/joshthecoder/tweepy/issues/#issue/12
            self.headers['Host'] = self.host

        def build_parameters(self, args, kargs):
            self.parameters = {}
            for idx, arg in enumerate(args):
                if arg is None:
                    continue

                try:
                    self.parameters[self.allowed_param[idx]] = convert_to_utf8_str(arg)
                except IndexError:
                    raise TweepError('Too many parameters supplied!')

            for k, arg in kargs.items():
                if arg is None:
                    continue
                if k in self.parameters:
                    raise TweepError('Multiple values for parameter %s supplied!' % k)

                self.parameters[k] = convert_to_utf8_str(arg)

        def build_path(self):
            for variable in re_path_template.findall(self.path):
                name = variable.strip('{}')

                if name == 'user' and 'user' not in self.parameters and self.api.auth:
                    # No 'user' parameter provided, fetch it from Auth instead.
                    value = self.api.auth.get_username()
                else:
                    try:
                        value = urllib.quote(self.parameters[name])
                    except KeyError:
                        raise TweepError('No parameter value found for path variable: %s' % name)
                    del self.parameters[name]

                self.path = self.path.replace(variable, value)

        def execute(self):
            # Build the request URL
            url = self.api_root + self.path
            if len(self.parameters):
                url = '%s?%s' % (url, urllib.urlencode(self.parameters))

            # Query the cache if one is available
            # and this request uses a GET method.
            if self.api.cache and self.method == 'GET':
                cache_result = self.api.cache.get(url)
                # if cache result found and not expired, return it
                if cache_result:
                    # must restore api reference
                    if isinstance(cache_result, list):
                        for result in cache_result:
                            if isinstance(result, Model):
                                result._api = self.api
                    else:
                        if isinstance(cache_result, Model):
                            cache_result._api = self.api
                    return cache_result

            # Continue attempting request until successful
            # or maximum number of retries is reached.
            retries_performed = 0
            while retries_performed < self.retry_count + 1:
                # Open connection
                # FIXME: add timeout
                if self.api.secure:
                    conn = httplib.HTTPSConnection(self.host)
                else:
                    conn = httplib.HTTPConnection(self.host)

                # Apply authentication
                if self.api.auth:
                    self.api.auth.apply_auth(
                            self.scheme + self.host + url,
                            self.method, self.headers, self.parameters
                    )

                # Execute request
                try:
                    conn.request(self.method, url, headers=self.headers, body=self.post_data)
                    resp = conn.getresponse()
                except Exception, e:
                    raise TweepError('Failed to send request: %s' % e)

                # Exit request loop if non-retry error code
                if self.retry_errors:
                    if resp.status not in self.retry_errors: break
                else:
                    if resp.status == 200: break

                # Sleep before retrying request again
                time.sleep(self.retry_delay)
                retries_performed += 1

            # If an error was returned, throw an exception
            self.api.last_response = resp
            if resp.status != 200:
                try:
                    error_msg = self.api.parser.parse_error(resp.read())
                except Exception:
                    error_msg = "Twitter error response: status code = %s" % resp.status
                raise TweepError(error_msg, resp)

            # Parse the response payload
            result = self.api.parser.parse(self, resp.read())

            conn.close()

            # Store result into cache if one is available.
            if self.api.cache and self.method == 'GET' and result:
                self.api.cache.store(url, result)

            return result


    def _call(api, *args, **kargs):

        method = APIMethod(api, args, kargs)
        return method.execute()


    # Set pagination mode
    if 'cursor' in APIMethod.allowed_param:
        _call.pagination_mode = 'cursor'
    elif 'page' in APIMethod.allowed_param:
        _call.pagination_mode = 'page'

    return _call


########NEW FILE########
__FILENAME__ = cache
# Tweepy
# Copyright 2009-2010 Joshua Roesslein
# See LICENSE for details.

import time
import threading
import os
import cPickle as pickle

try:
    import hashlib
except ImportError:
    # python 2.4
    import md5 as hashlib

try:
    import fcntl
except ImportError:
    # Probably on a windows system
    # TODO: use win32file
    pass


class Cache(object):
    """Cache interface"""

    def __init__(self, timeout=60):
        """Initialize the cache
            timeout: number of seconds to keep a cached entry
        """
        self.timeout = timeout

    def store(self, key, value):
        """Add new record to cache
            key: entry key
            value: data of entry
        """
        raise NotImplementedError

    def get(self, key, timeout=None):
        """Get cached entry if exists and not expired
            key: which entry to get
            timeout: override timeout with this value [optional]
        """
        raise NotImplementedError

    def count(self):
        """Get count of entries currently stored in cache"""
        raise NotImplementedError

    def cleanup(self):
        """Delete any expired entries in cache."""
        raise NotImplementedError

    def flush(self):
        """Delete all cached entries"""
        raise NotImplementedError


class MemoryCache(Cache):
    """In-memory cache"""

    def __init__(self, timeout=60):
        Cache.__init__(self, timeout)
        self._entries = {}
        self.lock = threading.Lock()

    def __getstate__(self):
        # pickle
        return {'entries': self._entries, 'timeout': self.timeout}

    def __setstate__(self, state):
        # unpickle
        self.lock = threading.Lock()
        self._entries = state['entries']
        self.timeout = state['timeout']

    def _is_expired(self, entry, timeout):
        return timeout > 0 and (time.time() - entry[0]) >= timeout

    def store(self, key, value):
        self.lock.acquire()
        self._entries[key] = (time.time(), value)
        self.lock.release()

    def get(self, key, timeout=None):
        self.lock.acquire()
        try:
            # check to see if we have this key
            entry = self._entries.get(key)
            if not entry:
                # no hit, return nothing
                return None

            # use provided timeout in arguments if provided
            # otherwise use the one provided during init.
            if timeout is None:
                timeout = self.timeout

            # make sure entry is not expired
            if self._is_expired(entry, timeout):
                # entry expired, delete and return nothing
                del self._entries[key]
                return None

            # entry found and not expired, return it
            return entry[1]
        finally:
            self.lock.release()

    def count(self):
        return len(self._entries)

    def cleanup(self):
        self.lock.acquire()
        try:
            for k, v in self._entries.items():
                if self._is_expired(v, self.timeout):
                    del self._entries[k]
        finally:
            self.lock.release()

    def flush(self):
        self.lock.acquire()
        self._entries.clear()
        self.lock.release()


class FileCache(Cache):
    """File-based cache"""

    # locks used to make cache thread-safe
    cache_locks = {}

    def __init__(self, cache_dir, timeout=60):
        Cache.__init__(self, timeout)
        if os.path.exists(cache_dir) is False:
            os.mkdir(cache_dir)
        self.cache_dir = cache_dir
        if cache_dir in FileCache.cache_locks:
            self.lock = FileCache.cache_locks[cache_dir]
        else:
            self.lock = threading.Lock()
            FileCache.cache_locks[cache_dir] = self.lock

        if os.name == 'posix':
            self._lock_file = self._lock_file_posix
            self._unlock_file = self._unlock_file_posix
        elif os.name == 'nt':
            self._lock_file = self._lock_file_win32
            self._unlock_file = self._unlock_file_win32
        else:
            print 'Warning! FileCache locking not supported on this system!'
            self._lock_file = self._lock_file_dummy
            self._unlock_file = self._unlock_file_dummy

    def _get_path(self, key):
        md5 = hashlib.md5()
        md5.update(key)
        return os.path.join(self.cache_dir, md5.hexdigest())

    def _lock_file_dummy(self, path, exclusive=True):
        return None

    def _unlock_file_dummy(self, lock):
        return

    def _lock_file_posix(self, path, exclusive=True):
        lock_path = path + '.lock'
        if exclusive is True:
            f_lock = open(lock_path, 'w')
            fcntl.lockf(f_lock, fcntl.LOCK_EX)
        else:
            f_lock = open(lock_path, 'r')
            fcntl.lockf(f_lock, fcntl.LOCK_SH)
        if os.path.exists(lock_path) is False:
            f_lock.close()
            return None
        return f_lock

    def _unlock_file_posix(self, lock):
        lock.close()

    def _lock_file_win32(self, path, exclusive=True):
        # TODO: implement
        return None

    def _unlock_file_win32(self, lock):
        # TODO: implement
        return

    def _delete_file(self, path):
        os.remove(path)
        if os.path.exists(path + '.lock'):
            os.remove(path + '.lock')

    def store(self, key, value):
        path = self._get_path(key)
        self.lock.acquire()
        try:
            # acquire lock and open file
            f_lock = self._lock_file(path)
            datafile = open(path, 'wb')

            # write data
            pickle.dump((time.time(), value), datafile)

            # close and unlock file
            datafile.close()
            self._unlock_file(f_lock)
        finally:
            self.lock.release()

    def get(self, key, timeout=None):
        return self._get(self._get_path(key), timeout)

    def _get(self, path, timeout):
        if os.path.exists(path) is False:
            # no record
            return None
        self.lock.acquire()
        try:
            # acquire lock and open
            f_lock = self._lock_file(path, False)
            datafile = open(path, 'rb')

            # read pickled object
            created_time, value = pickle.load(datafile)
            datafile.close()

            # check if value is expired
            if timeout is None:
                timeout = self.timeout
            if timeout > 0 and (time.time() - created_time) >= timeout:
                # expired! delete from cache
                value = None
                self._delete_file(path)

            # unlock and return result
            self._unlock_file(f_lock)
            return value
        finally:
            self.lock.release()

    def count(self):
        c = 0
        for entry in os.listdir(self.cache_dir):
            if entry.endswith('.lock'):
                continue
            c += 1
        return c

    def cleanup(self):
        for entry in os.listdir(self.cache_dir):
            if entry.endswith('.lock'):
                continue
            self._get(os.path.join(self.cache_dir, entry), None)

    def flush(self):
        for entry in os.listdir(self.cache_dir):
            if entry.endswith('.lock'):
                continue
            self._delete_file(os.path.join(self.cache_dir, entry))

class MemCacheCache(Cache):
    """Cache interface"""

    def __init__(self, client, timeout=60):
        """Initialize the cache
            client: The memcache client
            timeout: number of seconds to keep a cached entry
        """
        self.client = client
        self.timeout = timeout

    def store(self, key, value):
        """Add new record to cache
            key: entry key
            value: data of entry
        """
        self.client.set(key, value, time=self.timeout)

    def get(self, key, timeout=None):
        """Get cached entry if exists and not expired
            key: which entry to get
            timeout: override timeout with this value [optional]. DOES NOT WORK HERE
        """
        return self.client.get(key, key)

    def count(self):
        """Get count of entries currently stored in cache. RETURN 0"""
        return 0

    def cleanup(self):
        """Delete any expired entries in cache. NO-OP"""
        pass

    def flush(self):
        """Delete all cached entries. NO-OP"""
        pass

########NEW FILE########
__FILENAME__ = cursor
# Tweepy
# Copyright 2009-2010 Joshua Roesslein
# See LICENSE for details.

from error import TweepError

class Cursor(object):
    """Pagination helper class"""

    def __init__(self, method, *args, **kargs):
        if hasattr(method, 'pagination_mode'):
            if method.pagination_mode == 'cursor':
                self.iterator = CursorIterator(method, args, kargs)
            else:
                self.iterator = PageIterator(method, args, kargs)
        else:
            raise TweepError('This method does not perform pagination')

    def pages(self, limit=0):
        """Return iterator for pages"""
        if limit > 0:
            self.iterator.limit = limit
        return self.iterator

    def items(self, limit=0):
        """Return iterator for items in each page"""
        i = ItemIterator(self.iterator)
        i.limit = limit
        return i

class BaseIterator(object):

    def __init__(self, method, args, kargs):
        self.method = method
        self.args = args
        self.kargs = kargs
        self.limit = 0

    def next(self):
        raise NotImplementedError

    def prev(self):
        raise NotImplementedError

    def __iter__(self):
        return self

class CursorIterator(BaseIterator):

    def __init__(self, method, args, kargs):
        BaseIterator.__init__(self, method, args, kargs)
        self.next_cursor = -1
        self.prev_cursor = 0
        self.count = 0

    def next(self):
        if self.next_cursor == 0 or (self.limit and self.count == self.limit):
            raise StopIteration
        data, cursors = self.method(
                cursor=self.next_cursor, *self.args, **self.kargs
        )
        self.prev_cursor, self.next_cursor = cursors
        if len(data) == 0:
            raise StopIteration
        self.count += 1
        return data

    def prev(self):
        if self.prev_cursor == 0:
            raise TweepError('Can not page back more, at first page')
        data, self.next_cursor, self.prev_cursor = self.method(
                cursor=self.prev_cursor, *self.args, **self.kargs
        )
        self.count -= 1
        return data

class PageIterator(BaseIterator):

    def __init__(self, method, args, kargs):
        BaseIterator.__init__(self, method, args, kargs)
        self.current_page = 0

    def next(self):
        self.current_page += 1
        items = self.method(page=self.current_page, *self.args, **self.kargs)
        if len(items) == 0 or (self.limit > 0 and self.current_page > self.limit):
            raise StopIteration
        return items

    def prev(self):
        if (self.current_page == 1):
            raise TweepError('Can not page back more, at first page')
        self.current_page -= 1
        return self.method(page=self.current_page, *self.args, **self.kargs)

class ItemIterator(BaseIterator):

    def __init__(self, page_iterator):
        self.page_iterator = page_iterator
        self.limit = 0
        self.current_page = None
        self.page_index = -1
        self.count = 0

    def next(self):
        if self.limit > 0 and self.count == self.limit:
            raise StopIteration
        if self.current_page is None or self.page_index == len(self.current_page) - 1:
            # Reached end of current page, get the next page...
            self.current_page = self.page_iterator.next()
            self.page_index = -1
        self.page_index += 1
        self.count += 1
        return self.current_page[self.page_index]

    def prev(self):
        if self.current_page is None:
            raise TweepError('Can not go back more, at first page')
        if self.page_index == 0:
            # At the beginning of the current page, move to next...
            self.current_page = self.page_iterator.prev()
            self.page_index = len(self.current_page)
            if self.page_index == 0:
                raise TweepError('No more items')
        self.page_index -= 1
        self.count -= 1
        return self.current_page[self.page_index]


########NEW FILE########
__FILENAME__ = error
# Tweepy
# Copyright 2009-2010 Joshua Roesslein
# See LICENSE for details.

class TweepError(Exception):
    """Tweepy exception"""

    def __init__(self, reason, response=None):
        self.reason = unicode(reason)
        self.response = response

    def __str__(self):
        return self.reason


########NEW FILE########
__FILENAME__ = models
# Tweepy
# Copyright 2009-2010 Joshua Roesslein
# See LICENSE for details.

from error import TweepError
from utils import parse_datetime, parse_html_value, parse_a_href, \
        parse_search_datetime, unescape_html


class ResultSet(list):
    """A list like object that holds results from a Twitter API query."""


class Model(object):

    def __init__(self, api=None):
        self._api = api

    def __getstate__(self):
        # pickle
        pickle = dict(self.__dict__)
        try:
            del pickle['_api']  # do not pickle the API reference
        except KeyError:
            pass
        return pickle

    @classmethod
    def parse(cls, api, json):
        """Parse a JSON object into a model instance."""
        raise NotImplementedError

    @classmethod
    def parse_list(cls, api, json_list):
        """Parse a list of JSON objects into a result set of model instances."""
        results = ResultSet()
        for obj in json_list:
            if obj:
                results.append(cls.parse(api, obj))
        return results


class Status(Model):

    @classmethod
    def parse(cls, api, json):
        status = cls(api)
        for k, v in json.items():
            if k == 'user':
                user = User.parse(api, v)
                setattr(status, 'author', user)
                setattr(status, 'user', user)  # DEPRECIATED
            elif k == 'created_at':
                setattr(status, k, parse_datetime(v))
            elif k == 'source':
                if '<' in v:
                    setattr(status, k, parse_html_value(v))
                    setattr(status, 'source_url', parse_a_href(v))
                else:
                    setattr(status, k, v)
                    setattr(status, 'source_url', None)
            elif k == 'retweeted_status':
                setattr(status, k, Status.parse(api, v))
            else:
                setattr(status, k, v)
        return status

    def destroy(self):
        return self._api.destroy_status(self.id)

    def retweet(self):
        return self._api.retweet(self.id)

    def retweets(self):
        return self._api.retweets(self.id)

    def favorite(self):
        return self._api.create_favorite(self.id)


class User(Model):

    @classmethod
    def parse(cls, api, json):
        user = cls(api)
        for k, v in json.items():
            if k == 'created_at':
                setattr(user, k, parse_datetime(v))
            elif k == 'status':
                setattr(user, k, Status.parse(api, v))
            elif k == 'following':
                # twitter sets this to null if it is false
                if v is True:
                    setattr(user, k, True)
                else:
                    setattr(user, k, False)
            else:
                setattr(user, k, v)
        return user

    @classmethod
    def parse_list(cls, api, json_list):
        if isinstance(json_list, list):
            item_list = json_list
        else:
            item_list = json_list['users']

        results = ResultSet()
        for obj in item_list:
            results.append(cls.parse(api, obj))
        return results

    def timeline(self, **kargs):
        return self._api.user_timeline(user_id=self.id, **kargs)

    def friends(self, **kargs):
        return self._api.friends(user_id=self.id, **kargs)

    def followers(self, **kargs):
        return self._api.followers(user_id=self.id, **kargs)

    def follow(self):
        self._api.create_friendship(user_id=self.id)
        self.following = True

    def unfollow(self):
        self._api.destroy_friendship(user_id=self.id)
        self.following = False

    def lists_memberships(self, *args, **kargs):
        return self._api.lists_memberships(user=self.screen_name, *args, **kargs)

    def lists_subscriptions(self, *args, **kargs):
        return self._api.lists_subscriptions(user=self.screen_name, *args, **kargs)

    def lists(self, *args, **kargs):
        return self._api.lists(user=self.screen_name, *args, **kargs)

    def followers_ids(self, *args, **kargs):
        return self._api.followers_ids(user_id=self.id, *args, **kargs)


class DirectMessage(Model):

    @classmethod
    def parse(cls, api, json):
        dm = cls(api)
        for k, v in json.items():
            if k == 'sender' or k == 'recipient':
                setattr(dm, k, User.parse(api, v))
            elif k == 'created_at':
                setattr(dm, k, parse_datetime(v))
            else:
                setattr(dm, k, v)
        return dm

    def destroy(self):
        return self._api.destroy_direct_message(self.id)


class Friendship(Model):

    @classmethod
    def parse(cls, api, json):
        relationship = json['relationship']

        # parse source
        source = cls(api)
        for k, v in relationship['source'].items():
            setattr(source, k, v)

        # parse target
        target = cls(api)
        for k, v in relationship['target'].items():
            setattr(target, k, v)

        return source, target


class SavedSearch(Model):

    @classmethod
    def parse(cls, api, json):
        ss = cls(api)
        for k, v in json.items():
            if k == 'created_at':
                setattr(ss, k, parse_datetime(v))
            else:
                setattr(ss, k, v)
        return ss

    def destroy(self):
        return self._api.destroy_saved_search(self.id)


class SearchResult(Model):

    @classmethod
    def parse(cls, api, json):
        result = cls()
        for k, v in json.items():
            if k == 'created_at':
                setattr(result, k, parse_search_datetime(v))
            elif k == 'source':
                setattr(result, k, parse_html_value(unescape_html(v)))
            else:
                setattr(result, k, v)
        return result

    @classmethod
    def parse_list(cls, api, json_list, result_set=None):
        results = ResultSet()
        results.max_id = json_list.get('max_id')
        results.since_id = json_list.get('since_id')
        results.refresh_url = json_list.get('refresh_url')
        results.next_page = json_list.get('next_page')
        results.results_per_page = json_list.get('results_per_page')
        results.page = json_list.get('page')
        results.completed_in = json_list.get('completed_in')
        results.query = json_list.get('query')

        for obj in json_list['results']:
            results.append(cls.parse(api, obj))
        return results


class List(Model):

    @classmethod
    def parse(cls, api, json):
        lst = List(api)
        for k,v in json.items():
            if k == 'user':
                setattr(lst, k, User.parse(api, v))
            else:
                setattr(lst, k, v)
        return lst

    @classmethod
    def parse_list(cls, api, json_list, result_set=None):
        results = ResultSet()
        for obj in json_list['lists']:
            results.append(cls.parse(api, obj))
        return results

    def update(self, **kargs):
        return self._api.update_list(self.slug, **kargs)

    def destroy(self):
        return self._api.destroy_list(self.slug)

    def timeline(self, **kargs):
        return self._api.list_timeline(self.user.screen_name, self.slug, **kargs)

    def add_member(self, id):
        return self._api.add_list_member(self.slug, id)

    def remove_member(self, id):
        return self._api.remove_list_member(self.slug, id)

    def members(self, **kargs):
        return self._api.list_members(self.user.screen_name, self.slug, **kargs)

    def is_member(self, id):
        return self._api.is_list_member(self.user.screen_name, self.slug, id)

    def subscribe(self):
        return self._api.subscribe_list(self.user.screen_name, self.slug)

    def unsubscribe(self):
        return self._api.unsubscribe_list(self.user.screen_name, self.slug)

    def subscribers(self, **kargs):
        return self._api.list_subscribers(self.user.screen_name, self.slug, **kargs)

    def is_subscribed(self, id):
        return self._api.is_subscribed_list(self.user.screen_name, self.slug, id)


class JSONModel(Model):

    @classmethod
    def parse(cls, api, json):
        return json


class IDModel(Model):

    @classmethod
    def parse(cls, api, json):
        if isinstance(json, list):
            return json
        else:
            return json['ids']


class ModelFactory(object):
    """
    Used by parsers for creating instances
    of models. You may subclass this factory
    to add your own extended models.
    """

    status = Status
    user = User
    direct_message = DirectMessage
    friendship = Friendship
    saved_search = SavedSearch
    search_result = SearchResult
    list = List

    json = JSONModel
    ids = IDModel


########NEW FILE########
__FILENAME__ = oauth
"""
The MIT License

Copyright (c) 2007 Leah Culver

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
THE SOFTWARE.
"""

import cgi
import urllib
import time
import random
import urlparse
import hmac
import binascii


VERSION = '1.0' # Hi Blaine!
HTTP_METHOD = 'GET'
SIGNATURE_METHOD = 'PLAINTEXT'


class OAuthError(RuntimeError):
    """Generic exception class."""
    def __init__(self, message='OAuth error occured.'):
        self.message = message

def build_authenticate_header(realm=''):
    """Optional WWW-Authenticate header (401 error)"""
    return {'WWW-Authenticate': 'OAuth realm="%s"' % realm}

def escape(s):
    """Escape a URL including any /."""
    return urllib.quote(s, safe='~')

def _utf8_str(s):
    """Convert unicode to utf-8."""
    if isinstance(s, unicode):
        return s.encode("utf-8")
    else:
        return str(s)

def generate_timestamp():
    """Get seconds since epoch (UTC)."""
    return int(time.time())

def generate_nonce(length=8):
    """Generate pseudorandom number."""
    return ''.join([str(random.randint(0, 9)) for i in range(length)])

def generate_verifier(length=8):
    """Generate pseudorandom number."""
    return ''.join([str(random.randint(0, 9)) for i in range(length)])


class OAuthConsumer(object):
    """Consumer of OAuth authentication.

    OAuthConsumer is a data type that represents the identity of the Consumer
    via its shared secret with the Service Provider.

    """
    key = None
    secret = None

    def __init__(self, key, secret):
        self.key = key
        self.secret = secret


class OAuthToken(object):
    """OAuthToken is a data type that represents an End User via either an access
    or request token.
    
    key -- the token
    secret -- the token secret

    """
    key = None
    secret = None
    callback = None
    callback_confirmed = None
    verifier = None

    def __init__(self, key, secret):
        self.key = key
        self.secret = secret

    def set_callback(self, callback):
        self.callback = callback
        self.callback_confirmed = 'true'

    def set_verifier(self, verifier=None):
        if verifier is not None:
            self.verifier = verifier
        else:
            self.verifier = generate_verifier()

    def get_callback_url(self):
        if self.callback and self.verifier:
            # Append the oauth_verifier.
            parts = urlparse.urlparse(self.callback)
            scheme, netloc, path, params, query, fragment = parts[:6]
            if query:
                query = '%s&oauth_verifier=%s' % (query, self.verifier)
            else:
                query = 'oauth_verifier=%s' % self.verifier
            return urlparse.urlunparse((scheme, netloc, path, params,
                query, fragment))
        return self.callback

    def to_string(self):
        data = {
            'oauth_token': self.key,
            'oauth_token_secret': self.secret,
        }
        if self.callback_confirmed is not None:
            data['oauth_callback_confirmed'] = self.callback_confirmed
        return urllib.urlencode(data)
 
    def from_string(s):
        """ Returns a token from something like:
        oauth_token_secret=xxx&oauth_token=xxx
        """
        params = cgi.parse_qs(s, keep_blank_values=False)
        key = params['oauth_token'][0]
        secret = params['oauth_token_secret'][0]
        token = OAuthToken(key, secret)
        try:
            token.callback_confirmed = params['oauth_callback_confirmed'][0]
        except KeyError:
            pass # 1.0, no callback confirmed.
        return token
    from_string = staticmethod(from_string)

    def __str__(self):
        return self.to_string()


class OAuthRequest(object):
    """OAuthRequest represents the request and can be serialized.

    OAuth parameters:
        - oauth_consumer_key 
        - oauth_token
        - oauth_signature_method
        - oauth_signature 
        - oauth_timestamp 
        - oauth_nonce
        - oauth_version
        - oauth_verifier
        ... any additional parameters, as defined by the Service Provider.
    """
    parameters = None # OAuth parameters.
    http_method = HTTP_METHOD
    http_url = None
    version = VERSION

    def __init__(self, http_method=HTTP_METHOD, http_url=None, parameters=None):
        self.http_method = http_method
        self.http_url = http_url
        self.parameters = parameters or {}

    def set_parameter(self, parameter, value):
        self.parameters[parameter] = value

    def get_parameter(self, parameter):
        try:
            return self.parameters[parameter]
        except:
            raise OAuthError('Parameter not found: %s' % parameter)

    def _get_timestamp_nonce(self):
        return self.get_parameter('oauth_timestamp'), self.get_parameter(
            'oauth_nonce')

    def get_nonoauth_parameters(self):
        """Get any non-OAuth parameters."""
        parameters = {}
        for k, v in self.parameters.iteritems():
            # Ignore oauth parameters.
            if k.find('oauth_') < 0:
                parameters[k] = v
        return parameters

    def to_header(self, realm=''):
        """Serialize as a header for an HTTPAuth request."""
        auth_header = 'OAuth realm="%s"' % realm
        # Add the oauth parameters.
        if self.parameters:
            for k, v in self.parameters.iteritems():
                if k[:6] == 'oauth_':
                    auth_header += ', %s="%s"' % (k, escape(str(v)))
        return {'Authorization': auth_header}

    def to_postdata(self):
        """Serialize as post data for a POST request."""
        return '&'.join(['%s=%s' % (escape(str(k)), escape(str(v))) \
            for k, v in self.parameters.iteritems()])

    def to_url(self):
        """Serialize as a URL for a GET request."""
        return '%s?%s' % (self.get_normalized_http_url(), self.to_postdata())

    def get_normalized_parameters(self):
        """Return a string that contains the parameters that must be signed."""
        params = self.parameters
        try:
            # Exclude the signature if it exists.
            del params['oauth_signature']
        except:
            pass
        # Escape key values before sorting.
        key_values = [(escape(_utf8_str(k)), escape(_utf8_str(v))) \
            for k,v in params.items()]
        # Sort lexicographically, first after key, then after value.
        key_values.sort()
        # Combine key value pairs into a string.
        return '&'.join(['%s=%s' % (k, v) for k, v in key_values])

    def get_normalized_http_method(self):
        """Uppercases the http method."""
        return self.http_method.upper()

    def get_normalized_http_url(self):
        """Parses the URL and rebuilds it to be scheme://host/path."""
        parts = urlparse.urlparse(self.http_url)
        scheme, netloc, path = parts[:3]
        # Exclude default port numbers.
        if scheme == 'http' and netloc[-3:] == ':80':
            netloc = netloc[:-3]
        elif scheme == 'https' and netloc[-4:] == ':443':
            netloc = netloc[:-4]
        return '%s://%s%s' % (scheme, netloc, path)

    def sign_request(self, signature_method, consumer, token):
        """Set the signature parameter to the result of build_signature."""
        # Set the signature method.
        self.set_parameter('oauth_signature_method',
            signature_method.get_name())
        # Set the signature.
        self.set_parameter('oauth_signature',
            self.build_signature(signature_method, consumer, token))

    def build_signature(self, signature_method, consumer, token):
        """Calls the build signature method within the signature method."""
        return signature_method.build_signature(self, consumer, token)

    def from_request(http_method, http_url, headers=None, parameters=None,
            query_string=None):
        """Combines multiple parameter sources."""
        if parameters is None:
            parameters = {}

        # Headers
        if headers and 'Authorization' in headers:
            auth_header = headers['Authorization']
            # Check that the authorization header is OAuth.
            if auth_header[:6] == 'OAuth ':
                auth_header = auth_header[6:]
                try:
                    # Get the parameters from the header.
                    header_params = OAuthRequest._split_header(auth_header)
                    parameters.update(header_params)
                except:
                    raise OAuthError('Unable to parse OAuth parameters from '
                        'Authorization header.')

        # GET or POST query string.
        if query_string:
            query_params = OAuthRequest._split_url_string(query_string)
            parameters.update(query_params)

        # URL parameters.
        param_str = urlparse.urlparse(http_url)[4] # query
        url_params = OAuthRequest._split_url_string(param_str)
        parameters.update(url_params)

        if parameters:
            return OAuthRequest(http_method, http_url, parameters)

        return None
    from_request = staticmethod(from_request)

    def from_consumer_and_token(oauth_consumer, token=None,
            callback=None, verifier=None, http_method=HTTP_METHOD,
            http_url=None, parameters=None):
        if not parameters:
            parameters = {}

        defaults = {
            'oauth_consumer_key': oauth_consumer.key,
            'oauth_timestamp': generate_timestamp(),
            'oauth_nonce': generate_nonce(),
            'oauth_version': OAuthRequest.version,
        }

        defaults.update(parameters)
        parameters = defaults

        if token:
            parameters['oauth_token'] = token.key
            if token.callback:
                parameters['oauth_callback'] = token.callback
            # 1.0a support for verifier.
            if verifier:
                parameters['oauth_verifier'] = verifier
        elif callback:
            # 1.0a support for callback in the request token request.
            parameters['oauth_callback'] = callback

        return OAuthRequest(http_method, http_url, parameters)
    from_consumer_and_token = staticmethod(from_consumer_and_token)

    def from_token_and_callback(token, callback=None, http_method=HTTP_METHOD,
            http_url=None, parameters=None):
        if not parameters:
            parameters = {}

        parameters['oauth_token'] = token.key

        if callback:
            parameters['oauth_callback'] = callback

        return OAuthRequest(http_method, http_url, parameters)
    from_token_and_callback = staticmethod(from_token_and_callback)

    def _split_header(header):
        """Turn Authorization: header into parameters."""
        params = {}
        parts = header.split(',')
        for param in parts:
            # Ignore realm parameter.
            if param.find('realm') > -1:
                continue
            # Remove whitespace.
            param = param.strip()
            # Split key-value.
            param_parts = param.split('=', 1)
            # Remove quotes and unescape the value.
            params[param_parts[0]] = urllib.unquote(param_parts[1].strip('\"'))
        return params
    _split_header = staticmethod(_split_header)

    def _split_url_string(param_str):
        """Turn URL string into parameters."""
        parameters = cgi.parse_qs(param_str, keep_blank_values=False)
        for k, v in parameters.iteritems():
            parameters[k] = urllib.unquote(v[0])
        return parameters
    _split_url_string = staticmethod(_split_url_string)

class OAuthServer(object):
    """A worker to check the validity of a request against a data store."""
    timestamp_threshold = 300 # In seconds, five minutes.
    version = VERSION
    signature_methods = None
    data_store = None

    def __init__(self, data_store=None, signature_methods=None):
        self.data_store = data_store
        self.signature_methods = signature_methods or {}

    def set_data_store(self, data_store):
        self.data_store = data_store

    def get_data_store(self):
        return self.data_store

    def add_signature_method(self, signature_method):
        self.signature_methods[signature_method.get_name()] = signature_method
        return self.signature_methods

    def fetch_request_token(self, oauth_request):
        """Processes a request_token request and returns the
        request token on success.
        """
        try:
            # Get the request token for authorization.
            token = self._get_token(oauth_request, 'request')
        except OAuthError:
            # No token required for the initial token request.
            version = self._get_version(oauth_request)
            consumer = self._get_consumer(oauth_request)
            try:
                callback = self.get_callback(oauth_request)
            except OAuthError:
                callback = None # 1.0, no callback specified.
            self._check_signature(oauth_request, consumer, None)
            # Fetch a new token.
            token = self.data_store.fetch_request_token(consumer, callback)
        return token

    def fetch_access_token(self, oauth_request):
        """Processes an access_token request and returns the
        access token on success.
        """
        version = self._get_version(oauth_request)
        consumer = self._get_consumer(oauth_request)
        try:
            verifier = self._get_verifier(oauth_request)
        except OAuthError:
            verifier = None
        # Get the request token.
        token = self._get_token(oauth_request, 'request')
        self._check_signature(oauth_request, consumer, token)
        new_token = self.data_store.fetch_access_token(consumer, token, verifier)
        return new_token

    def verify_request(self, oauth_request):
        """Verifies an api call and checks all the parameters."""
        # -> consumer and token
        version = self._get_version(oauth_request)
        consumer = self._get_consumer(oauth_request)
        # Get the access token.
        token = self._get_token(oauth_request, 'access')
        self._check_signature(oauth_request, consumer, token)
        parameters = oauth_request.get_nonoauth_parameters()
        return consumer, token, parameters

    def authorize_token(self, token, user):
        """Authorize a request token."""
        return self.data_store.authorize_request_token(token, user)

    def get_callback(self, oauth_request):
        """Get the callback URL."""
        return oauth_request.get_parameter('oauth_callback')
 
    def build_authenticate_header(self, realm=''):
        """Optional support for the authenticate header."""
        return {'WWW-Authenticate': 'OAuth realm="%s"' % realm}

    def _get_version(self, oauth_request):
        """Verify the correct version request for this server."""
        try:
            version = oauth_request.get_parameter('oauth_version')
        except:
            version = VERSION
        if version and version != self.version:
            raise OAuthError('OAuth version %s not supported.' % str(version))
        return version

    def _get_signature_method(self, oauth_request):
        """Figure out the signature with some defaults."""
        try:
            signature_method = oauth_request.get_parameter(
                'oauth_signature_method')
        except:
            signature_method = SIGNATURE_METHOD
        try:
            # Get the signature method object.
            signature_method = self.signature_methods[signature_method]
        except:
            signature_method_names = ', '.join(self.signature_methods.keys())
            raise OAuthError('Signature method %s not supported try one of the '
                'following: %s' % (signature_method, signature_method_names))

        return signature_method

    def _get_consumer(self, oauth_request):
        consumer_key = oauth_request.get_parameter('oauth_consumer_key')
        consumer = self.data_store.lookup_consumer(consumer_key)
        if not consumer:
            raise OAuthError('Invalid consumer.')
        return consumer

    def _get_token(self, oauth_request, token_type='access'):
        """Try to find the token for the provided request token key."""
        token_field = oauth_request.get_parameter('oauth_token')
        token = self.data_store.lookup_token(token_type, token_field)
        if not token:
            raise OAuthError('Invalid %s token: %s' % (token_type, token_field))
        return token
    
    def _get_verifier(self, oauth_request):
        return oauth_request.get_parameter('oauth_verifier')

    def _check_signature(self, oauth_request, consumer, token):
        timestamp, nonce = oauth_request._get_timestamp_nonce()
        self._check_timestamp(timestamp)
        self._check_nonce(consumer, token, nonce)
        signature_method = self._get_signature_method(oauth_request)
        try:
            signature = oauth_request.get_parameter('oauth_signature')
        except:
            raise OAuthError('Missing signature.')
        # Validate the signature.
        valid_sig = signature_method.check_signature(oauth_request, consumer,
            token, signature)
        if not valid_sig:
            key, base = signature_method.build_signature_base_string(
                oauth_request, consumer, token)
            raise OAuthError('Invalid signature. Expected signature base '
                'string: %s' % base)
        built = signature_method.build_signature(oauth_request, consumer, token)

    def _check_timestamp(self, timestamp):
        """Verify that timestamp is recentish."""
        timestamp = int(timestamp)
        now = int(time.time())
        lapsed = abs(now - timestamp)
        if lapsed > self.timestamp_threshold:
            raise OAuthError('Expired timestamp: given %d and now %s has a '
                'greater difference than threshold %d' %
                (timestamp, now, self.timestamp_threshold))

    def _check_nonce(self, consumer, token, nonce):
        """Verify that the nonce is uniqueish."""
        nonce = self.data_store.lookup_nonce(consumer, token, nonce)
        if nonce:
            raise OAuthError('Nonce already used: %s' % str(nonce))


class OAuthClient(object):
    """OAuthClient is a worker to attempt to execute a request."""
    consumer = None
    token = None

    def __init__(self, oauth_consumer, oauth_token):
        self.consumer = oauth_consumer
        self.token = oauth_token

    def get_consumer(self):
        return self.consumer

    def get_token(self):
        return self.token

    def fetch_request_token(self, oauth_request):
        """-> OAuthToken."""
        raise NotImplementedError

    def fetch_access_token(self, oauth_request):
        """-> OAuthToken."""
        raise NotImplementedError

    def access_resource(self, oauth_request):
        """-> Some protected resource."""
        raise NotImplementedError


class OAuthDataStore(object):
    """A database abstraction used to lookup consumers and tokens."""

    def lookup_consumer(self, key):
        """-> OAuthConsumer."""
        raise NotImplementedError

    def lookup_token(self, oauth_consumer, token_type, token_token):
        """-> OAuthToken."""
        raise NotImplementedError

    def lookup_nonce(self, oauth_consumer, oauth_token, nonce):
        """-> OAuthToken."""
        raise NotImplementedError

    def fetch_request_token(self, oauth_consumer, oauth_callback):
        """-> OAuthToken."""
        raise NotImplementedError

    def fetch_access_token(self, oauth_consumer, oauth_token, oauth_verifier):
        """-> OAuthToken."""
        raise NotImplementedError

    def authorize_request_token(self, oauth_token, user):
        """-> OAuthToken."""
        raise NotImplementedError


class OAuthSignatureMethod(object):
    """A strategy class that implements a signature method."""
    def get_name(self):
        """-> str."""
        raise NotImplementedError

    def build_signature_base_string(self, oauth_request, oauth_consumer, oauth_token):
        """-> str key, str raw."""
        raise NotImplementedError

    def build_signature(self, oauth_request, oauth_consumer, oauth_token):
        """-> str."""
        raise NotImplementedError

    def check_signature(self, oauth_request, consumer, token, signature):
        built = self.build_signature(oauth_request, consumer, token)
        return built == signature


class OAuthSignatureMethod_HMAC_SHA1(OAuthSignatureMethod):

    def get_name(self):
        return 'HMAC-SHA1'
        
    def build_signature_base_string(self, oauth_request, consumer, token):
        sig = (
            escape(oauth_request.get_normalized_http_method()),
            escape(oauth_request.get_normalized_http_url()),
            escape(oauth_request.get_normalized_parameters()),
        )

        key = '%s&' % escape(consumer.secret)
        if token:
            key += escape(token.secret)
        raw = '&'.join(sig)
        return key, raw

    def build_signature(self, oauth_request, consumer, token):
        """Builds the base signature string."""
        key, raw = self.build_signature_base_string(oauth_request, consumer,
            token)

        # HMAC object.
        try:
            import hashlib # 2.5
            hashed = hmac.new(key, raw, hashlib.sha1)
        except:
            import sha # Deprecated
            hashed = hmac.new(key, raw, sha)

        # Calculate the digest base 64.
        return binascii.b2a_base64(hashed.digest())[:-1]


class OAuthSignatureMethod_PLAINTEXT(OAuthSignatureMethod):

    def get_name(self):
        return 'PLAINTEXT'

    def build_signature_base_string(self, oauth_request, consumer, token):
        """Concatenates the consumer key and secret."""
        sig = '%s&' % escape(consumer.secret)
        if token:
            sig = sig + escape(token.secret)
        return sig, sig

    def build_signature(self, oauth_request, consumer, token):
        key, raw = self.build_signature_base_string(oauth_request, consumer,
            token)
        return key
########NEW FILE########
__FILENAME__ = parsers
# Tweepy
# Copyright 2009-2010 Joshua Roesslein
# See LICENSE for details.

from models import ModelFactory
from utils import import_simplejson
from error import TweepError


class Parser(object):

    def parse(self, method, payload):
        """
        Parse the response payload and return the result.
        Returns a tuple that contains the result data and the cursors
        (or None if not present).
        """
        raise NotImplementedError

    def parse_error(self, payload):
        """
        Parse the error message from payload.
        If unable to parse the message, throw an exception
        and default error message will be used.
        """
        raise NotImplementedError


class JSONParser(Parser):

    payload_format = 'json'

    def __init__(self):
        self.json_lib = import_simplejson()

    def parse(self, method, payload):
        try:
            json = self.json_lib.loads(payload)
        except Exception, e:
            raise TweepError('Failed to parse JSON payload: %s' % e)

        if isinstance(json, dict) and 'previous_cursor' in json and 'next_cursor' in json:
            cursors = json['previous_cursor'], json['next_cursor']
            return json, cursors
        else:
            return json

    def parse_error(self, payload):
        error = self.json_lib.loads(payload)
        if error.has_key('error'):
            return error['error']
        else:
            return error['errors']


class ModelParser(JSONParser):

    def __init__(self, model_factory=None):
        JSONParser.__init__(self)
        self.model_factory = model_factory or ModelFactory

    def parse(self, method, payload):
        try:
            if method.payload_type is None: return
            model = getattr(self.model_factory, method.payload_type)
        except AttributeError:
            raise TweepError('No model for this payload type: %s' % method.payload_type)

        json = JSONParser.parse(self, method, payload)
        if isinstance(json, tuple):
            json, cursors = json
        else:
            cursors = None

        if method.payload_list:
            result = model.parse_list(method.api, json)
        else:
            result = model.parse(method.api, json)

        if cursors:
            return result, cursors
        else:
            return result


########NEW FILE########
__FILENAME__ = streaming
# Tweepy
# Copyright 2009-2010 Joshua Roesslein
# See LICENSE for details.

import httplib
from socket import timeout
from threading import Thread
from time import sleep
import urllib

from models import Status
from api import API
from error import TweepError

from utils import import_simplejson
json = import_simplejson()

STREAM_VERSION = 1


class StreamListener(object):

    def __init__(self, api=None):
        self.api = api or API()

    def on_data(self, data):
        """Called when raw data is received from connection.

        Override this method if you wish to manually handle
        the stream data. Return False to stop stream and close connection.
        """

        if 'in_reply_to_status_id' in data:
            status = Status.parse(self.api, json.loads(data))
            if self.on_status(status) is False:
                return False
        elif 'delete' in data:
            delete = json.loads(data)['delete']['status']
            if self.on_delete(delete['id'], delete['user_id']) is False:
                return False
        elif 'limit' in data:
            if self.on_limit(json.loads(data)['limit']['track']) is False:
                return False

    def on_status(self, status):
        """Called when a new status arrives"""
        return

    def on_delete(self, status_id, user_id):
        """Called when a delete notice arrives for a status"""
        return

    def on_limit(self, track):
        """Called when a limitation notice arrvies"""
        return

    def on_error(self, status_code):
        """Called when a non-200 status code is returned"""
        return False

    def on_timeout(self):
        """Called when stream connection times out"""
        return


class Stream(object):

    host = 'stream.twitter.com'

    def __init__(self, auth, listener, **options):
        self.auth = auth
        self.listener = listener
        self.running = False
        self.timeout = options.get("timeout") or 5.0
        self.retry_count = options.get("retry_count")
        self.retry_time = options.get("retry_time") or 10.0
        self.snooze_time = options.get("snooze_time") or 5.0
        self.buffer_size = options.get("buffer_size") or 1500
        if options.get("secure"):
            self.scheme = "https"
        else:
            self.scheme = "http"

        self.api = API()
        self.headers = options.get("headers") or {}
        self.parameters = None
        self.body = None

    def _run(self):
        # Authenticate
        url = "%s://%s%s" % (self.scheme, self.host, self.url)
        self.auth.apply_auth(url, 'POST', self.headers, self.parameters)

        # Connect and process the stream
        error_counter = 0
        conn = None
        exception = None
        while self.running:
            if self.retry_count and error_counter > self.retry_count:
                # quit if error count greater than retry count
                break
            try:
                if self.scheme == "http":
                    conn = httplib.HTTPConnection(self.host)
                else:
                    conn = httplib.HTTPSConnection(self.host)
                conn.connect()
                conn.sock.settimeout(self.timeout)
                conn.request('POST', self.url, self.body, headers=self.headers)
                resp = conn.getresponse()
                if resp.status != 200:
                    if self.listener.on_error(resp.status) is False:
                        break
                    error_counter += 1
                    sleep(self.retry_time)
                else:
                    error_counter = 0
                    self._read_loop(resp)
            except timeout:
                if self.listener.on_timeout() == False:
                    break
                if self.running is False:
                    break
                conn.close()
                sleep(self.snooze_time)
            except Exception, exception:
                # any other exception is fatal, so kill loop
                break

        # cleanup
        self.running = False
        if conn:
            conn.close()

        if exception:
            raise exception

    def _read_loop(self, resp):
        data = ''
        while self.running:
            if resp.isclosed():
                break

            # read length
            length = ''
            while True:
                c = resp.read(1)
                if c == '\n':
                    break
                length += c
            length = length.strip()
            if length.isdigit():
                length = int(length)
            else:
                continue

            # read data and pass into listener
            data = resp.read(length)
            if self.listener.on_data(data) is False:
                self.running = False

    def _start(self, async):
        self.running = True
        if async:
            Thread(target=self._run).start()
        else:
            self._run()

    def firehose(self, count=None, async=False):
        self.parameters = {'delimited': 'length'}
        if self.running:
            raise TweepError('Stream object already connected!')
        self.url = '/%i/statuses/firehose.json?delimited=length' % STREAM_VERSION
        if count:
            self.url += '&count=%s' % count
        self._start(async)

    def retweet(self, async=False):
        self.parameters = {'delimited': 'length'}
        if self.running:
            raise TweepError('Stream object already connected!')
        self.url = '/%i/statuses/retweet.json?delimited=length' % STREAM_VERSION
        self._start(async)

    def sample(self, count=None, async=False):
        self.parameters = {'delimited': 'length'}
        if self.running:
            raise TweepError('Stream object already connected!')
        self.url = '/%i/statuses/sample.json?delimited=length' % STREAM_VERSION
        if count:
            self.url += '&count=%s' % count
        self._start(async)

    def filter(self, follow=None, track=None, async=False, locations=None):
        self.parameters = {}
        self.headers['Content-type'] = "application/x-www-form-urlencoded"
        if self.running:
            raise TweepError('Stream object already connected!')
        self.url = '/%i/statuses/filter.json?delimited=length' % STREAM_VERSION
        if follow:
            self.parameters['follow'] = ','.join(map(str, follow))
        if track:
            self.parameters['track'] = ','.join(map(str, track))
        if locations and len(locations) > 0:
            assert len(locations) % 4 == 0
            self.parameters['locations'] = ','.join(['%.2f' % l for l in locations])
        self.body = urllib.urlencode(self.parameters)
        self.parameters['delimited'] = 'length'
        self._start(async)

    def disconnect(self):
        if self.running is False:
            return
        self.running = False


########NEW FILE########
__FILENAME__ = utils
# Tweepy
# Copyright 2010 Joshua Roesslein
# See LICENSE for details.

from datetime import datetime
import time
import htmlentitydefs
import re
import locale


def parse_datetime(string):
    # Set locale for date parsing
    locale.setlocale(locale.LC_TIME, 'C')

    # We must parse datetime this way to work in python 2.4
    date = datetime(*(time.strptime(string, '%a %b %d %H:%M:%S +0000 %Y')[0:6]))

    # Reset locale back to the default setting
    locale.setlocale(locale.LC_TIME, '')
    return date


def parse_html_value(html):

    return html[html.find('>')+1:html.rfind('<')]


def parse_a_href(atag):

    start = atag.find('"') + 1
    end = atag.find('"', start)
    return atag[start:end]


def parse_search_datetime(string):
    # Set locale for date parsing
    locale.setlocale(locale.LC_TIME, 'C')

    # We must parse datetime this way to work in python 2.4
    date = datetime(*(time.strptime(string, '%a, %d %b %Y %H:%M:%S +0000')[0:6]))

    # Reset locale back to the default setting
    locale.setlocale(locale.LC_TIME, '')
    return date


def unescape_html(text):
    """Created by Fredrik Lundh (http://effbot.org/zone/re-sub.htm#unescape-html)"""
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
    return re.sub("&#?\w+;", fixup, text)


def convert_to_utf8_str(arg):
    # written by Michael Norton (http://docondev.blogspot.com/)
    if isinstance(arg, unicode):
        arg = arg.encode('utf-8')
    elif not isinstance(arg, str):
        arg = str(arg)
    return arg



def import_simplejson():
    try:
        import simplejson as json
    except ImportError:
        try:
            import json  # Python 2.6+
        except ImportError:
            try:
                from django.utils import simplejson as json  # Google App Engine
            except ImportError:
                raise ImportError, "Can't load a json library"

    return json

def list_to_csv(item_list):
    if item_list:
        return ','.join([str(i) for i in item_list])


########NEW FILE########
__FILENAME__ = twitter
#!/usr/bin/python2.4
#
# Copyright 2007 Google Inc. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

'''A library that provides a python interface to the Twitter API'''

__author__ = 'dewitt@google.com'
__version__ = '0.7-devel'


import base64
import calendar
import httplib
import os
import rfc822
import simplejson
import sys
import tempfile
import textwrap
import time
import urllib
import urllib2
import urlparse

try:
  from hashlib import md5
except ImportError:
  from md5 import md5


CHARACTER_LIMIT = 140

# A singleton representing a lazily instantiated FileCache.
DEFAULT_CACHE = object()


class TwitterError(Exception):
  '''Base class for Twitter errors'''
  
  @property
  def message(self):
    '''Returns the first argument used to construct this error.'''
    return self.args[0]


class Status(object):
  '''A class representing the Status structure used by the twitter API.

  The Status structure exposes the following properties:

    status.created_at
    status.created_at_in_seconds # read only
    status.favorited
    status.in_reply_to_screen_name
    status.in_reply_to_user_id
    status.in_reply_to_status_id
    status.truncated
    status.source
    status.id
    status.text
    status.relative_created_at # read only
    status.user
  '''
  def __init__(self,
               created_at=None,
               favorited=None,
               id=None,
               text=None,
               user=None,
               in_reply_to_screen_name=None,
               in_reply_to_user_id=None,
               in_reply_to_status_id=None,
               truncated=None,
               source=None,
               now=None):
    '''An object to hold a Twitter status message.

    This class is normally instantiated by the twitter.Api class and
    returned in a sequence.

    Note: Dates are posted in the form "Sat Jan 27 04:17:38 +0000 2007"

    Args:
      created_at: The time this status message was posted
      favorited: Whether this is a favorite of the authenticated user
      id: The unique id of this status message
      text: The text of this status message
      relative_created_at:
        A human readable string representing the posting time
      user:
        A twitter.User instance representing the person posting the message
      now:
        The current time, if the client choses to set it.  Defaults to the
        wall clock time.
    '''
    self.created_at = created_at
    self.favorited = favorited
    self.id = id
    self.text = text
    self.user = user
    self.now = now
    self.in_reply_to_screen_name = in_reply_to_screen_name
    self.in_reply_to_user_id = in_reply_to_user_id
    self.in_reply_to_status_id = in_reply_to_status_id
    self.truncated = truncated
    self.source = source

  def GetCreatedAt(self):
    '''Get the time this status message was posted.

    Returns:
      The time this status message was posted
    '''
    return self._created_at

  def SetCreatedAt(self, created_at):
    '''Set the time this status message was posted.

    Args:
      created_at: The time this status message was created
    '''
    self._created_at = created_at

  created_at = property(GetCreatedAt, SetCreatedAt,
                        doc='The time this status message was posted.')

  def GetCreatedAtInSeconds(self):
    '''Get the time this status message was posted, in seconds since the epoch.

    Returns:
      The time this status message was posted, in seconds since the epoch.
    '''
    return calendar.timegm(rfc822.parsedate(self.created_at))

  created_at_in_seconds = property(GetCreatedAtInSeconds,
                                   doc="The time this status message was "
                                       "posted, in seconds since the epoch")

  def GetFavorited(self):
    '''Get the favorited setting of this status message.

    Returns:
      True if this status message is favorited; False otherwise
    '''
    return self._favorited

  def SetFavorited(self, favorited):
    '''Set the favorited state of this status message.

    Args:
      favorited: boolean True/False favorited state of this status message
    '''
    self._favorited = favorited

  favorited = property(GetFavorited, SetFavorited,
                       doc='The favorited state of this status message.')

  def GetId(self):
    '''Get the unique id of this status message.

    Returns:
      The unique id of this status message
    '''
    return self._id

  def SetId(self, id):
    '''Set the unique id of this status message.

    Args:
      id: The unique id of this status message
    '''
    self._id = id

  id = property(GetId, SetId,
                doc='The unique id of this status message.')

  def GetInReplyToScreenName(self):
    return self._in_reply_to_screen_name

  def SetInReplyToScreenName(self, in_reply_to_screen_name):
    self._in_reply_to_screen_name = in_reply_to_screen_name

  in_reply_to_screen_name = property(GetInReplyToScreenName, SetInReplyToScreenName,
                doc='')

  def GetInReplyToUserId(self):
    return self._in_reply_to_user_id

  def SetInReplyToUserId(self, in_reply_to_user_id):
    self._in_reply_to_user_id = in_reply_to_user_id

  in_reply_to_user_id = property(GetInReplyToUserId, SetInReplyToUserId,
                doc='')

  def GetInReplyToStatusId(self):
    return self._in_reply_to_status_id

  def SetInReplyToStatusId(self, in_reply_to_status_id):
    self._in_reply_to_status_id = in_reply_to_status_id

  in_reply_to_status_id = property(GetInReplyToStatusId, SetInReplyToStatusId,
                doc='')

  def GetTruncated(self):
    return self._truncated

  def SetTruncated(self, truncated):
    self._truncated = truncated

  truncated = property(GetTruncated, SetTruncated,
                doc='')

  def GetSource(self):
    return self._source

  def SetSource(self, source):
    self._source = source

  source = property(GetSource, SetSource,
                doc='')

  def GetText(self):
    '''Get the text of this status message.

    Returns:
      The text of this status message.
    '''
    return self._text

  def SetText(self, text):
    '''Set the text of this status message.

    Args:
      text: The text of this status message
    '''
    self._text = text

  text = property(GetText, SetText,
                  doc='The text of this status message')

  def GetRelativeCreatedAt(self):
    '''Get a human redable string representing the posting time

    Returns:
      A human readable string representing the posting time
    '''
    fudge = 1.25
    delta  = long(self.now) - long(self.created_at_in_seconds)

    if delta < (1 * fudge):
      return 'about a second ago'
    elif delta < (60 * (1/fudge)):
      return 'about %d seconds ago' % (delta)
    elif delta < (60 * fudge):
      return 'about a minute ago'
    elif delta < (60 * 60 * (1/fudge)):
      return 'about %d minutes ago' % (delta / 60)
    elif delta < (60 * 60 * fudge):
      return 'about an hour ago'
    elif delta < (60 * 60 * 24 * (1/fudge)):
      return 'about %d hours ago' % (delta / (60 * 60))
    elif delta < (60 * 60 * 24 * fudge):
      return 'about a day ago'
    else:
      return 'about %d days ago' % (delta / (60 * 60 * 24))

  relative_created_at = property(GetRelativeCreatedAt,
                                 doc='Get a human readable string representing'
                                     'the posting time')

  def GetUser(self):
    '''Get a twitter.User reprenting the entity posting this status message.

    Returns:
      A twitter.User reprenting the entity posting this status message
    '''
    return self._user

  def SetUser(self, user):
    '''Set a twitter.User reprenting the entity posting this status message.

    Args:
      user: A twitter.User reprenting the entity posting this status message
    '''
    self._user = user

  user = property(GetUser, SetUser,
                  doc='A twitter.User reprenting the entity posting this '
                      'status message')

  def GetNow(self):
    '''Get the wallclock time for this status message.

    Used to calculate relative_created_at.  Defaults to the time
    the object was instantiated.

    Returns:
      Whatever the status instance believes the current time to be,
      in seconds since the epoch.
    '''
    if self._now is None:
      self._now = time.time()
    return self._now

  def SetNow(self, now):
    '''Set the wallclock time for this status message.

    Used to calculate relative_created_at.  Defaults to the time
    the object was instantiated.

    Args:
      now: The wallclock time for this instance.
    '''
    self._now = now

  now = property(GetNow, SetNow,
                 doc='The wallclock time for this status instance.')


  def __ne__(self, other):
    return not self.__eq__(other)

  def __eq__(self, other):
    try:
      return other and \
             self.created_at == other.created_at and \
             self.id == other.id and \
             self.text == other.text and \
             self.user == other.user and \
             self.in_reply_to_screen_name == other.in_reply_to_screen_name and \
             self.in_reply_to_user_id == other.in_reply_to_user_id and \
             self.in_reply_to_status_id == other.in_reply_to_status_id and \
             self.truncated == other.truncated and \
             self.favorited == other.favorited and \
             self.source == other.source
    except AttributeError:
      return False

  def __str__(self):
    '''A string representation of this twitter.Status instance.

    The return value is the same as the JSON string representation.

    Returns:
      A string representation of this twitter.Status instance.
    '''
    return self.AsJsonString()

  def AsJsonString(self):
    '''A JSON string representation of this twitter.Status instance.

    Returns:
      A JSON string representation of this twitter.Status instance
   '''
    return simplejson.dumps(self.AsDict(), sort_keys=True)

  def AsDict(self):
    '''A dict representation of this twitter.Status instance.

    The return value uses the same key names as the JSON representation.

    Return:
      A dict representing this twitter.Status instance
    '''
    data = {}
    if self.created_at:
      data['created_at'] = self.created_at
    if self.favorited:
      data['favorited'] = self.favorited
    if self.id:
      data['id'] = self.id
    if self.text:
      data['text'] = self.text
    if self.user:
      data['user'] = self.user.AsDict()
    if self.in_reply_to_screen_name:
      data['in_reply_to_screen_name'] = self.in_reply_to_screen_name
    if self.in_reply_to_user_id:
      data['in_reply_to_user_id'] = self.in_reply_to_user_id
    if self.in_reply_to_status_id:
      data['in_reply_to_status_id'] = self.in_reply_to_status_id
    if self.truncated is not None:
      data['truncated'] = self.truncated
    if self.favorited is not None:
      data['favorited'] = self.favorited
    if self.source:
      data['source'] = self.source
    return data

  @staticmethod
  def NewFromJsonDict(data):
    '''Create a new instance based on a JSON dict.

    Args:
      data: A JSON dict, as converted from the JSON in the twitter API
    Returns:
      A twitter.Status instance
    '''
    if 'user' in data:
      user = User.NewFromJsonDict(data['user'])
    else:
      user = None
    return Status(created_at=data.get('created_at', None),
                  favorited=data.get('favorited', None),
                  id=data.get('id', None),
                  text=data.get('text', None),
                  in_reply_to_screen_name=data.get('in_reply_to_screen_name', None),
                  in_reply_to_user_id=data.get('in_reply_to_user_id', None),
                  in_reply_to_status_id=data.get('in_reply_to_status_id', None),
                  truncated=data.get('truncated', None),
                  source=data.get('source', None),
                  user=user)


class User(object):
  '''A class representing the User structure used by the twitter API.

  The User structure exposes the following properties:

    user.id
    user.name
    user.screen_name
    user.location
    user.description
    user.profile_image_url
    user.profile_background_tile
    user.profile_background_image_url
    user.profile_sidebar_fill_color
    user.profile_background_color
    user.profile_link_color
    user.profile_text_color
    user.protected
    user.utc_offset
    user.time_zone
    user.url
    user.status
    user.statuses_count
    user.followers_count
    user.friends_count
    user.favourites_count
  '''
  def __init__(self,
               id=None,
               name=None,
               screen_name=None,
               location=None,
               description=None,
               profile_image_url=None,
               profile_background_tile=None,
               profile_background_image_url=None,
               profile_sidebar_fill_color=None,
               profile_background_color=None,
               profile_link_color=None,
               profile_text_color=None,
               protected=None,
               utc_offset=None,
               time_zone=None,
               followers_count=None,
               friends_count=None,
               statuses_count=None,
               favourites_count=None,
               url=None,
               status=None):
    self.id = id
    self.name = name
    self.screen_name = screen_name
    self.location = location
    self.description = description
    self.profile_image_url = profile_image_url
    self.profile_background_tile = profile_background_tile
    self.profile_background_image_url = profile_background_image_url
    self.profile_sidebar_fill_color = profile_sidebar_fill_color
    self.profile_background_color = profile_background_color
    self.profile_link_color = profile_link_color
    self.profile_text_color = profile_text_color
    self.protected = protected
    self.utc_offset = utc_offset
    self.time_zone = time_zone
    self.followers_count = followers_count
    self.friends_count = friends_count
    self.statuses_count = statuses_count
    self.favourites_count = favourites_count
    self.url = url
    self.status = status


  def GetId(self):
    '''Get the unique id of this user.

    Returns:
      The unique id of this user
    '''
    return self._id

  def SetId(self, id):
    '''Set the unique id of this user.

    Args:
      id: The unique id of this user.
    '''
    self._id = id

  id = property(GetId, SetId,
                doc='The unique id of this user.')

  def GetName(self):
    '''Get the real name of this user.

    Returns:
      The real name of this user
    '''
    return self._name

  def SetName(self, name):
    '''Set the real name of this user.

    Args:
      name: The real name of this user
    '''
    self._name = name

  name = property(GetName, SetName,
                  doc='The real name of this user.')

  def GetScreenName(self):
    '''Get the short username of this user.

    Returns:
      The short username of this user
    '''
    return self._screen_name

  def SetScreenName(self, screen_name):
    '''Set the short username of this user.

    Args:
      screen_name: the short username of this user
    '''
    self._screen_name = screen_name

  screen_name = property(GetScreenName, SetScreenName,
                         doc='The short username of this user.')

  def GetLocation(self):
    '''Get the geographic location of this user.

    Returns:
      The geographic location of this user
    '''
    return self._location

  def SetLocation(self, location):
    '''Set the geographic location of this user.

    Args:
      location: The geographic location of this user
    '''
    self._location = location

  location = property(GetLocation, SetLocation,
                      doc='The geographic location of this user.')

  def GetDescription(self):
    '''Get the short text description of this user.

    Returns:
      The short text description of this user
    '''
    return self._description

  def SetDescription(self, description):
    '''Set the short text description of this user.

    Args:
      description: The short text description of this user
    '''
    self._description = description

  description = property(GetDescription, SetDescription,
                         doc='The short text description of this user.')

  def GetUrl(self):
    '''Get the homepage url of this user.

    Returns:
      The homepage url of this user
    '''
    return self._url

  def SetUrl(self, url):
    '''Set the homepage url of this user.

    Args:
      url: The homepage url of this user
    '''
    self._url = url

  url = property(GetUrl, SetUrl,
                 doc='The homepage url of this user.')

  def GetProfileImageUrl(self):
    '''Get the url of the thumbnail of this user.

    Returns:
      The url of the thumbnail of this user
    '''
    return self._profile_image_url

  def SetProfileImageUrl(self, profile_image_url):
    '''Set the url of the thumbnail of this user.

    Args:
      profile_image_url: The url of the thumbnail of this user
    '''
    self._profile_image_url = profile_image_url

  profile_image_url= property(GetProfileImageUrl, SetProfileImageUrl,
                              doc='The url of the thumbnail of this user.')

  def GetProfileBackgroundTile(self):
    '''Boolean for whether to tile the profile background image.

    Returns:
      True if the background is to be tiled, False if not, None if unset.
    '''
    return self._profile_background_tile

  def SetProfileBackgroundTile(self, profile_background_tile):
    '''Set the boolean flag for whether to tile the profile background image.

    Args:
      profile_background_tile: Boolean flag for whether to tile or not.
    '''
    self._profile_background_tile = profile_background_tile

  profile_background_tile = property(GetProfileBackgroundTile, SetProfileBackgroundTile,
                                     doc='Boolean for whether to tile the background image.')

  def GetProfileBackgroundImageUrl(self):
    return self._profile_background_image_url

  def SetProfileBackgroundImageUrl(self, profile_background_image_url):
    self._profile_background_image_url = profile_background_image_url

  profile_background_image_url = property(GetProfileBackgroundImageUrl, SetProfileBackgroundImageUrl,
                                          doc='The url of the profile background of this user.')

  def GetProfileSidebarFillColor(self):
    return self._profile_sidebar_fill_color

  def SetProfileSidebarFillColor(self, profile_sidebar_fill_color):
    self._profile_sidebar_fill_color = profile_sidebar_fill_color

  profile_sidebar_fill_color = property(GetProfileSidebarFillColor, SetProfileSidebarFillColor)

  def GetProfileBackgroundColor(self):
    return self._profile_background_color

  def SetProfileBackgroundColor(self, profile_background_color):
    self._profile_background_color = profile_background_color

  profile_background_color = property(GetProfileBackgroundColor, SetProfileBackgroundColor)

  def GetProfileLinkColor(self):
    return self._profile_link_color

  def SetProfileLinkColor(self, profile_link_color):
    self._profile_link_color = profile_link_color

  profile_link_color = property(GetProfileLinkColor, SetProfileLinkColor)

  def GetProfileTextColor(self):
    return self._profile_text_color

  def SetProfileTextColor(self, profile_text_color):
    self._profile_text_color = profile_text_color

  profile_text_color = property(GetProfileTextColor, SetProfileTextColor)

  def GetProtected(self):
    return self._protected

  def SetProtected(self, protected):
    self._protected = protected

  protected = property(GetProtected, SetProtected)

  def GetUtcOffset(self):
    return self._utc_offset

  def SetUtcOffset(self, utc_offset):
    self._utc_offset = utc_offset

  utc_offset = property(GetUtcOffset, SetUtcOffset)

  def GetTimeZone(self):
    '''Returns the current time zone string for the user.

    Returns:
      The descriptive time zone string for the user.
    '''
    return self._time_zone

  def SetTimeZone(self, time_zone):
    '''Sets the user's time zone string.

    Args:
      time_zone: The descriptive time zone to assign for the user.
    '''
    self._time_zone = time_zone

  time_zone = property(GetTimeZone, SetTimeZone)

  def GetStatus(self):
    '''Get the latest twitter.Status of this user.

    Returns:
      The latest twitter.Status of this user
    '''
    return self._status

  def SetStatus(self, status):
    '''Set the latest twitter.Status of this user.

    Args:
      status: The latest twitter.Status of this user
    '''
    self._status = status

  status = property(GetStatus, SetStatus,
                  doc='The latest twitter.Status of this user.')

  def GetFriendsCount(self):
    '''Get the friend count for this user.
    
    Returns:
      The number of users this user has befriended.
    '''
    return self._friends_count

  def SetFriendsCount(self, count):
    '''Set the friend count for this user.

    Args:
      count: The number of users this user has befriended.
    '''
    self._friends_count = count

  friends_count = property(GetFriendsCount, SetFriendsCount,
                  doc='The number of friends for this user.')

  def GetFollowersCount(self):
    '''Get the follower count for this user.
    
    Returns:
      The number of users following this user.
    '''
    return self._followers_count

  def SetFollowersCount(self, count):
    '''Set the follower count for this user.

    Args:
      count: The number of users following this user.
    '''
    self._followers_count = count

  followers_count = property(GetFollowersCount, SetFollowersCount,
                  doc='The number of users following this user.')

  def GetStatusesCount(self):
    '''Get the number of status updates for this user.
    
    Returns:
      The number of status updates for this user.
    '''
    return self._statuses_count

  def SetStatusesCount(self, count):
    '''Set the status update count for this user.

    Args:
      count: The number of updates for this user.
    '''
    self._statuses_count = count

  statuses_count = property(GetStatusesCount, SetStatusesCount,
                  doc='The number of updates for this user.')

  def GetFavouritesCount(self):
    '''Get the number of favourites for this user.
    
    Returns:
      The number of favourites for this user.
    '''
    return self._favourites_count

  def SetFavouritesCount(self, count):
    '''Set the favourite count for this user.

    Args:
      count: The number of favourites for this user.
    '''
    self._favourites_count = count

  favourites_count = property(GetFavouritesCount, SetFavouritesCount,
                  doc='The number of favourites for this user.')

  def __ne__(self, other):
    return not self.__eq__(other)

  def __eq__(self, other):
    try:
      return other and \
             self.id == other.id and \
             self.name == other.name and \
             self.screen_name == other.screen_name and \
             self.location == other.location and \
             self.description == other.description and \
             self.profile_image_url == other.profile_image_url and \
             self.profile_background_tile == other.profile_background_tile and \
             self.profile_background_image_url == other.profile_background_image_url and \
             self.profile_sidebar_fill_color == other.profile_sidebar_fill_color and \
             self.profile_background_color == other.profile_background_color and \
             self.profile_link_color == other.profile_link_color and \
             self.profile_text_color == other.profile_text_color and \
             self.protected == other.protected and \
             self.utc_offset == other.utc_offset and \
             self.time_zone == other.time_zone and \
             self.url == other.url and \
             self.statuses_count == other.statuses_count and \
             self.followers_count == other.followers_count and \
             self.favourites_count == other.favourites_count and \
             self.friends_count == other.friends_count and \
             self.status == other.status
    except AttributeError:
      return False

  def __str__(self):
    '''A string representation of this twitter.User instance.

    The return value is the same as the JSON string representation.

    Returns:
      A string representation of this twitter.User instance.
    '''
    return self.AsJsonString()

  def AsJsonString(self):
    '''A JSON string representation of this twitter.User instance.

    Returns:
      A JSON string representation of this twitter.User instance
   '''
    return simplejson.dumps(self.AsDict(), sort_keys=True)

  def AsDict(self):
    '''A dict representation of this twitter.User instance.

    The return value uses the same key names as the JSON representation.

    Return:
      A dict representing this twitter.User instance
    '''
    data = {}
    if self.id:
      data['id'] = self.id
    if self.name:
      data['name'] = self.name
    if self.screen_name:
      data['screen_name'] = self.screen_name
    if self.location:
      data['location'] = self.location
    if self.description:
      data['description'] = self.description
    if self.profile_image_url:
      data['profile_image_url'] = self.profile_image_url
    if self.profile_background_tile is not None:
      data['profile_background_tile'] = self.profile_background_tile
    if self.profile_background_image_url:
      data['profile_sidebar_fill_color'] = self.profile_background_image_url
    if self.profile_background_color:
      data['profile_background_color'] = self.profile_background_color
    if self.profile_link_color:
      data['profile_link_color'] = self.profile_link_color
    if self.profile_text_color:
      data['profile_text_color'] = self.profile_text_color
    if self.protected is not None:
      data['protected'] = self.protected
    if self.utc_offset:
      data['utc_offset'] = self.utc_offset
    if self.time_zone:
      data['time_zone'] = self.time_zone
    if self.url:
      data['url'] = self.url
    if self.status:
      data['status'] = self.status.AsDict()
    if self.friends_count:
      data['friends_count'] = self.friends_count
    if self.followers_count:
      data['followers_count'] = self.followers_count
    if self.statuses_count:
      data['statuses_count'] = self.statuses_count
    if self.favourites_count:
      data['favourites_count'] = self.favourites_count
    return data

  @staticmethod
  def NewFromJsonDict(data):
    '''Create a new instance based on a JSON dict.

    Args:
      data: A JSON dict, as converted from the JSON in the twitter API
    Returns:
      A twitter.User instance
    '''
    if 'status' in data:
      status = Status.NewFromJsonDict(data['status'])
    else:
      status = None
    return User(id=data.get('id', None),
                name=data.get('name', None),
                screen_name=data.get('screen_name', None),
                location=data.get('location', None),
                description=data.get('description', None),
                statuses_count=data.get('statuses_count', None),
                followers_count=data.get('followers_count', None),
                favourites_count=data.get('favourites_count', None),
                friends_count=data.get('friends_count', None),
                profile_image_url=data.get('profile_image_url', None),
                profile_background_tile = data.get('profile_background_tile', None),
                profile_background_image_url = data.get('profile_background_image_url', None),
                profile_sidebar_fill_color = data.get('profile_sidebar_fill_color', None),
                profile_background_color = data.get('profile_background_color', None),
                profile_link_color = data.get('profile_link_color', None),
                profile_text_color = data.get('profile_text_color', None),
                protected = data.get('protected', None),
                utc_offset = data.get('utc_offset', None),
                time_zone = data.get('time_zone', None),
                url=data.get('url', None),
                status=status)

class DirectMessage(object):
  '''A class representing the DirectMessage structure used by the twitter API.

  The DirectMessage structure exposes the following properties:

    direct_message.id
    direct_message.created_at
    direct_message.created_at_in_seconds # read only
    direct_message.sender_id
    direct_message.sender_screen_name
    direct_message.recipient_id
    direct_message.recipient_screen_name
    direct_message.text
  '''

  def __init__(self,
               id=None,
               created_at=None,
               sender_id=None,
               sender_screen_name=None,
               recipient_id=None,
               recipient_screen_name=None,
               text=None):
    '''An object to hold a Twitter direct message.

    This class is normally instantiated by the twitter.Api class and
    returned in a sequence.

    Note: Dates are posted in the form "Sat Jan 27 04:17:38 +0000 2007"

    Args:
      id: The unique id of this direct message
      created_at: The time this direct message was posted
      sender_id: The id of the twitter user that sent this message
      sender_screen_name: The name of the twitter user that sent this message
      recipient_id: The id of the twitter that received this message
      recipient_screen_name: The name of the twitter that received this message
      text: The text of this direct message
    '''
    self.id = id
    self.created_at = created_at
    self.sender_id = sender_id
    self.sender_screen_name = sender_screen_name
    self.recipient_id = recipient_id
    self.recipient_screen_name = recipient_screen_name
    self.text = text

  def GetId(self):
    '''Get the unique id of this direct message.

    Returns:
      The unique id of this direct message
    '''
    return self._id

  def SetId(self, id):
    '''Set the unique id of this direct message.

    Args:
      id: The unique id of this direct message
    '''
    self._id = id

  id = property(GetId, SetId,
                doc='The unique id of this direct message.')

  def GetCreatedAt(self):
    '''Get the time this direct message was posted.

    Returns:
      The time this direct message was posted
    '''
    return self._created_at

  def SetCreatedAt(self, created_at):
    '''Set the time this direct message was posted.

    Args:
      created_at: The time this direct message was created
    '''
    self._created_at = created_at

  created_at = property(GetCreatedAt, SetCreatedAt,
                        doc='The time this direct message was posted.')

  def GetCreatedAtInSeconds(self):
    '''Get the time this direct message was posted, in seconds since the epoch.

    Returns:
      The time this direct message was posted, in seconds since the epoch.
    '''
    return calendar.timegm(rfc822.parsedate(self.created_at))

  created_at_in_seconds = property(GetCreatedAtInSeconds,
                                   doc="The time this direct message was "
                                       "posted, in seconds since the epoch")

  def GetSenderId(self):
    '''Get the unique sender id of this direct message.

    Returns:
      The unique sender id of this direct message
    '''
    return self._sender_id

  def SetSenderId(self, sender_id):
    '''Set the unique sender id of this direct message.

    Args:
      sender id: The unique sender id of this direct message
    '''
    self._sender_id = sender_id

  sender_id = property(GetSenderId, SetSenderId,
                doc='The unique sender id of this direct message.')

  def GetSenderScreenName(self):
    '''Get the unique sender screen name of this direct message.

    Returns:
      The unique sender screen name of this direct message
    '''
    return self._sender_screen_name

  def SetSenderScreenName(self, sender_screen_name):
    '''Set the unique sender screen name of this direct message.

    Args:
      sender_screen_name: The unique sender screen name of this direct message
    '''
    self._sender_screen_name = sender_screen_name

  sender_screen_name = property(GetSenderScreenName, SetSenderScreenName,
                doc='The unique sender screen name of this direct message.')

  def GetRecipientId(self):
    '''Get the unique recipient id of this direct message.

    Returns:
      The unique recipient id of this direct message
    '''
    return self._recipient_id

  def SetRecipientId(self, recipient_id):
    '''Set the unique recipient id of this direct message.

    Args:
      recipient id: The unique recipient id of this direct message
    '''
    self._recipient_id = recipient_id

  recipient_id = property(GetRecipientId, SetRecipientId,
                doc='The unique recipient id of this direct message.')

  def GetRecipientScreenName(self):
    '''Get the unique recipient screen name of this direct message.

    Returns:
      The unique recipient screen name of this direct message
    '''
    return self._recipient_screen_name

  def SetRecipientScreenName(self, recipient_screen_name):
    '''Set the unique recipient screen name of this direct message.

    Args:
      recipient_screen_name: The unique recipient screen name of this direct message
    '''
    self._recipient_screen_name = recipient_screen_name

  recipient_screen_name = property(GetRecipientScreenName, SetRecipientScreenName,
                doc='The unique recipient screen name of this direct message.')

  def GetText(self):
    '''Get the text of this direct message.

    Returns:
      The text of this direct message.
    '''
    return self._text

  def SetText(self, text):
    '''Set the text of this direct message.

    Args:
      text: The text of this direct message
    '''
    self._text = text

  text = property(GetText, SetText,
                  doc='The text of this direct message')

  def __ne__(self, other):
    return not self.__eq__(other)

  def __eq__(self, other):
    try:
      return other and \
          self.id == other.id and \
          self.created_at == other.created_at and \
          self.sender_id == other.sender_id and \
          self.sender_screen_name == other.sender_screen_name and \
          self.recipient_id == other.recipient_id and \
          self.recipient_screen_name == other.recipient_screen_name and \
          self.text == other.text
    except AttributeError:
      return False

  def __str__(self):
    '''A string representation of this twitter.DirectMessage instance.

    The return value is the same as the JSON string representation.

    Returns:
      A string representation of this twitter.DirectMessage instance.
    '''
    return self.AsJsonString()

  def AsJsonString(self):
    '''A JSON string representation of this twitter.DirectMessage instance.

    Returns:
      A JSON string representation of this twitter.DirectMessage instance
   '''
    return simplejson.dumps(self.AsDict(), sort_keys=True)

  def AsDict(self):
    '''A dict representation of this twitter.DirectMessage instance.

    The return value uses the same key names as the JSON representation.

    Return:
      A dict representing this twitter.DirectMessage instance
    '''
    data = {}
    if self.id:
      data['id'] = self.id
    if self.created_at:
      data['created_at'] = self.created_at
    if self.sender_id:
      data['sender_id'] = self.sender_id
    if self.sender_screen_name:
      data['sender_screen_name'] = self.sender_screen_name
    if self.recipient_id:
      data['recipient_id'] = self.recipient_id
    if self.recipient_screen_name:
      data['recipient_screen_name'] = self.recipient_screen_name
    if self.text:
      data['text'] = self.text
    return data

  @staticmethod
  def NewFromJsonDict(data):
    '''Create a new instance based on a JSON dict.

    Args:
      data: A JSON dict, as converted from the JSON in the twitter API
    Returns:
      A twitter.DirectMessage instance
    '''
    return DirectMessage(created_at=data.get('created_at', None),
                         recipient_id=data.get('recipient_id', None),
                         sender_id=data.get('sender_id', None),
                         text=data.get('text', None),
                         sender_screen_name=data.get('sender_screen_name', None),
                         id=data.get('id', None),
                         recipient_screen_name=data.get('recipient_screen_name', None))

class Api(object):
  '''A python interface into the Twitter API

  By default, the Api caches results for 1 minute.

  Example usage:

    To create an instance of the twitter.Api class, with no authentication:

      >>> import twitter
      >>> api = twitter.Api()

    To fetch the most recently posted public twitter status messages:

      >>> statuses = api.GetPublicTimeline()
      >>> print [s.user.name for s in statuses]
      [u'DeWitt', u'Kesuke Miyagi', u'ev', u'Buzz Andersen', u'Biz Stone'] #...

    To fetch a single user's public status messages, where "user" is either
    a Twitter "short name" or their user id.

      >>> statuses = api.GetUserTimeline(user)
      >>> print [s.text for s in statuses]

    To use authentication, instantiate the twitter.Api class with a
    username and password:

      >>> api = twitter.Api(username='twitter user', password='twitter pass')

    To fetch your friends (after being authenticated):

      >>> users = api.GetFriends()
      >>> print [u.name for u in users]

    To post a twitter status message (after being authenticated):

      >>> status = api.PostUpdate('I love python-twitter!')
      >>> print status.text
      I love python-twitter!

    There are many other methods, including:

      >>> api.PostUpdates(status)
      >>> api.PostDirectMessage(user, text)
      >>> api.GetUser(user)
      >>> api.GetReplies()
      >>> api.GetUserTimeline(user)
      >>> api.GetStatus(id)
      >>> api.DestroyStatus(id)
      >>> api.GetFriendsTimeline(user)
      >>> api.GetFriends(user)
      >>> api.GetFollowers()
      >>> api.GetFeatured()
      >>> api.GetDirectMessages()
      >>> api.PostDirectMessage(user, text)
      >>> api.DestroyDirectMessage(id)
      >>> api.DestroyFriendship(user)
      >>> api.CreateFriendship(user)
      >>> api.GetUserByEmail(email)
  '''

  DEFAULT_CACHE_TIMEOUT = 60 # cache for 1 minute

  _API_REALM = 'Twitter API'

  def __init__(self,
               username=None,
               password=None,
               input_encoding=None,
               request_headers=None,
               cache=DEFAULT_CACHE,
               base_url='http://twitter.com'):
    '''Instantiate a new twitter.Api object.

    Args:
      username: The username of the twitter account.  [optional]
      password: The password for the twitter account. [optional]
      input_encoding: The encoding used to encode input strings. [optional]
      request_header: A dictionary of additional HTTP request headers. [optional]
      cache: 
          The cache instance to use. Defaults to DEFAULT_CACHE. Use
          None to disable caching. [optional]
    '''
    self.SetCache(cache)
    self._urllib = urllib2
    self._cache_timeout = Api.DEFAULT_CACHE_TIMEOUT
    self._InitializeRequestHeaders(request_headers)
    self._InitializeUserAgent()
    self._InitializeDefaultParameters()
    self._input_encoding = input_encoding
    self._base_url = base_url.rstrip('/')
    if -1 == self._base_url.lower().find('://'):
      self._base_url = 'http://' + self._base_url
    self.SetCredentials(username, password)

  def GetPublicTimeline(self, since_id=None):
    '''Fetch the sequnce of public twitter.Status message for all users.

    Args:
      since_id:
        Returns only public statuses with an ID greater than (that is,
        more recent than) the specified ID. [Optional]

    Returns:
      An sequence of twitter.Status instances, one for each message
    '''
    parameters = {}
    if since_id:
      parameters['since_id'] = since_id
    url = self._base_url + '/statuses/public_timeline.json'
    json = self._FetchUrl(url,  parameters=parameters)
    data = simplejson.loads(json)
    self._CheckForTwitterError(data)
    return [Status.NewFromJsonDict(x) for x in data]

  def GetFriendsTimeline(self,
                         user=None,
                         count=None,
                         since=None, 
                         since_id=None):
    '''Fetch the sequence of twitter.Status messages for a user's friends

    The twitter.Api instance must be authenticated if the user is private.

    Args:
      user:
        Specifies the ID or screen name of the user for whom to return
        the friends_timeline.  If unspecified, the username and password
        must be set in the twitter.Api instance.  [Optional]
      count: 
        Specifies the number of statuses to retrieve. May not be
        greater than 200. [Optional]
      since:
        Narrows the returned results to just those statuses created
        after the specified HTTP-formatted date. [Optional]
      since_id:
        Returns only public statuses with an ID greater than (that is,
        more recent than) the specified ID. [Optional]

    Returns:
      A sequence of twitter.Status instances, one for each message
    '''
    if not user and not self._username:
      raise TwitterError("User must be specified if API is not authenticated.")
    if user:
      url = self._base_url + '/statuses/friends_timeline/%s.json' % user
    else:
      url = self._base_url + '/statuses/friends_timeline.json'
    parameters = {}
    if count is not None:
      try:
        if int(count) > 200:
          raise TwitterError("'count' may not be greater than 200")
      except ValueError:
        raise TwitterError("'count' must be an integer")
      parameters['count'] = count
    if since:
      parameters['since'] = since
    if since_id:
      parameters['since_id'] = since_id
    json = self._FetchUrl(url, parameters=parameters)
    data = simplejson.loads(json)
    self._CheckForTwitterError(data)
    return [Status.NewFromJsonDict(x) for x in data]

  def DoTest(self):
    '''Does a query to the test serice to confirm that we have a valid
    API endpoint.
    
    Returns:
      True if everything went ok
    '''
    url = self._base_url + '/help/test.json'
    json = self._FetchUrl(url)
    data = simplejson.loads(json)
    return 'ok' == data
  
  def GetSearchResults(self, search_term):
    '''Searches twitter and returns statuses matching the query
    
    Args:
      search_term: 
        the term for which to search. You can read about the 
        accepted search operators on the Twitter API documentation page
        
    Returns:
      A sequence of twitter.Status instances, one for each message
    '''
    # small hack here: for twitter.com we must use search.twitter.com
    # while laconi.ca sites use the same base url
    url  = self._base_url
    if -1 != url.find('twitter.com'): url = 'http://search.twitter.com'
    url += '/search.json'
    parameters = {}
    parameters['q'] = search_term
    json = self._FetchUrl(url, parameters=parameters)
    data = simplejson.loads(json)
    self._CheckForTwitterError(data)
    # emulate the same user structure as for the other APIs
    for x in data['results']:
      x['user'] = {
        'id' : int(x['from_user_id']),
        'screen_name' : x['from_user'],
        'profile_image_url' : x['profile_image_url'],
      }
    return [Status.NewFromJsonDict(x) for x in data['results']]

  def GetUserTimeline(self,
                      id=None,
                      user_id=None,
                      screen_name=None,
                      since_id=None,
                      max_id=None,
                      count=None,
                      page=None):
    '''Fetch the sequence of public Status messages for a single user.

    The twitter.Api instance must be authenticated if the user is private.

    Args:
      id:
        Specifies the ID or screen name of the user for whom to return
        the user_timeline. [optional]
      user_id:
        Specfies the ID of the user for whom to return the
        user_timeline. Helpful for disambiguating when a valid user ID
        is also a valid screen name. [optional]
      screen_name:
        Specfies the screen name of the user for whom to return the
        user_timeline. Helpful for disambiguating when a valid screen
        name is also a user ID. [optional]
      since_id:
        Returns only public statuses with an ID greater than (that is,
        more recent than) the specified ID. [optional]
      max_id:
        Returns only statuses with an ID less than (that is, older
        than) or equal to the specified ID. [optional]
      count:
        Specifies the number of statuses to retrieve. May not be
        greater than 200.  [optional]
      page:
         Specifies the page of results to retrieve. Note: there are
         pagination limits. [optional]

    Returns:
      A sequence of Status instances, one for each message up to count
    '''
    parameters = {}

    if id:
      url = self._base_url + '/statuses/user_timeline/%s.json' % id
    elif user_id:
      url = self._base_url + '/statuses/user_timeline.json?user_id=%d' % user_id
    elif screen_name:
      url = (self._base_url + '/statuses/user_timeline.json?screen_name=%s' % screen_name)
    elif not self._username:
      raise TwitterError("User must be specified if API is not authenticated.")
    else:
      url = self._base_url + '/statuses/user_timeline.json'

    if since_id:
      try:
        parameters['since_id'] = long(since_id)
      except:
        raise TwitterError("since_id must be an integer")

    if max_id:
      try:
        parameters['max_id'] = long(max_id)
      except:
        raise TwitterError("max_id must be an integer")

    if count:
      try:
        parameters['count'] = int(count)
      except:
        raise TwitterError("count must be an integer")

    if page:
      try:
        parameters['page'] = int(page)
      except:
        raise TwitterError("page must be an integer")

    json = self._FetchUrl(url, parameters=parameters)
    data = simplejson.loads(json)
    self._CheckForTwitterError(data)
    return [Status.NewFromJsonDict(x) for x in data]

  def GetStatus(self, id):
    '''Returns a single status message.

    The twitter.Api instance must be authenticated if the status message is private.

    Args:
      id: The numerical ID of the status you're trying to retrieve.

    Returns:
      A twitter.Status instance representing that status message
    '''
    try:
      if id:
        long(id)
    except:
      raise TwitterError("id must be an long integer")
    url = self._base_url + '/statuses/show/%s.json' % id
    json = self._FetchUrl(url)
    data = simplejson.loads(json)
    self._CheckForTwitterError(data)
    return Status.NewFromJsonDict(data)

  def DestroyStatus(self, id):
    '''Destroys the status specified by the required ID parameter.

    The twitter.Api instance must be authenticated and thee
    authenticating user must be the author of the specified status.

    Args:
      id: The numerical ID of the status you're trying to destroy.

    Returns:
      A twitter.Status instance representing the destroyed status message
    '''
    try:
      if id:
        long(id)
    except:
      raise TwitterError("id must be an integer")
    url = self._base_url + '/statuses/destroy/%s.json' % id
    json = self._FetchUrl(url, post_data={})
    data = simplejson.loads(json)
    self._CheckForTwitterError(data)
    return Status.NewFromJsonDict(data)

  def PostUpdate(self, status, in_reply_to_status_id=None):
    '''Post a twitter status message from the authenticated user.

    The twitter.Api instance must be authenticated.

    Args:
      status:
        The message text to be posted.  Must be less than or equal to
        140 characters.
      in_reply_to_status_id:
        The ID of an existing status that the status to be posted is
        in reply to.  This implicitly sets the in_reply_to_user_id
        attribute of the resulting status to the user ID of the
        message being replied to.  Invalid/missing status IDs will be
        ignored. [Optional]
    Returns:
      A twitter.Status instance representing the message posted.
    '''
    if not self._username:
      raise TwitterError("The twitter.Api instance must be authenticated.")

    url = self._base_url + '/statuses/update.json'

    if len(status) > CHARACTER_LIMIT:
      raise TwitterError("Text must be less than or equal to %d characters. "
                         "Consider using PostUpdates." % CHARACTER_LIMIT)

    data = {'status': status}
    if in_reply_to_status_id:
      data['in_reply_to_status_id'] = in_reply_to_status_id
    json = self._FetchUrl(url, post_data=data)
    data = simplejson.loads(json)
    self._CheckForTwitterError(data)
    return Status.NewFromJsonDict(data)

  def PostUpdates(self, status, continuation=None, **kwargs):
    '''Post one or more twitter status messages from the authenticated user.

    Unlike api.PostUpdate, this method will post multiple status updates
    if the message is longer than 140 characters.

    The twitter.Api instance must be authenticated.

    Args:
      status:
        The message text to be posted.  May be longer than 140 characters.
      continuation:
        The character string, if any, to be appended to all but the
        last message.  Note that Twitter strips trailing '...' strings
        from messages.  Consider using the unicode \u2026 character
        (horizontal ellipsis) instead. [Defaults to None]
      **kwargs:
        See api.PostUpdate for a list of accepted parameters.
    Returns:
      A of list twitter.Status instance representing the messages posted.
    '''
    results = list()
    if continuation is None:
      continuation = ''
    line_length = CHARACTER_LIMIT - len(continuation)
    lines = textwrap.wrap(status, line_length)
    for line in lines[0:-1]:
      results.append(self.PostUpdate(line + continuation, **kwargs))
    results.append(self.PostUpdate(lines[-1], **kwargs))
    return results

  def GetReplies(self, since=None, since_id=None, page=None): 
    '''Get a sequence of status messages representing the 20 most recent
    replies (status updates prefixed with @username) to the authenticating
    user.

    Args:
      page: 
      since:
        Narrows the returned results to just those statuses created
        after the specified HTTP-formatted date. [optional]
      since_id:
        Returns only public statuses with an ID greater than (that is,
        more recent than) the specified ID. [Optional]

    Returns:
      A sequence of twitter.Status instances, one for each reply to the user.
    '''
    url = self._base_url + '/statuses/replies.json'
    if not self._username:
      raise TwitterError("The twitter.Api instance must be authenticated.")
    parameters = {}
    if since:
      parameters['since'] = since
    if since_id:
      parameters['since_id'] = since_id
    if page:
      parameters['page'] = page
    json = self._FetchUrl(url, parameters=parameters)
    data = simplejson.loads(json)
    self._CheckForTwitterError(data)
    return [Status.NewFromJsonDict(x) for x in data]

  def GetFriends(self, user=None, page=None):
    '''Fetch the sequence of twitter.User instances, one for each friend.

    Args:
      user: the username or id of the user whose friends you are fetching.  If
      not specified, defaults to the authenticated user. [optional]

    The twitter.Api instance must be authenticated.

    Returns:
      A sequence of twitter.User instances, one for each friend
    '''
    if not user and not self._username:
      raise TwitterError("twitter.Api instance must be authenticated")
    if user:
      url = self._base_url + '/statuses/friends/%s.json' % user 
    else:
      url = self._base_url + '/statuses/friends.json'
    parameters = {}
    if page:
      parameters['page'] = page
    json = self._FetchUrl(url, parameters=parameters)
    data = simplejson.loads(json)
    self._CheckForTwitterError(data)
    return [User.NewFromJsonDict(x) for x in data]

  def GetFollowers(self, page=None):
    '''Fetch the sequence of twitter.User instances, one for each follower

    The twitter.Api instance must be authenticated.

    Returns:
      A sequence of twitter.User instances, one for each follower
    '''
    if not self._username:
      raise TwitterError("twitter.Api instance must be authenticated")
    url = self._base_url + '/statuses/followers.json'
    parameters = {}
    if page:
      parameters['page'] = page
    json = self._FetchUrl(url, parameters=parameters)
    data = simplejson.loads(json)
    self._CheckForTwitterError(data)
    return [User.NewFromJsonDict(x) for x in data]

  def GetFeatured(self):
    '''Fetch the sequence of twitter.User instances featured on twitter.com

    The twitter.Api instance must be authenticated.

    Returns:
      A sequence of twitter.User instances
    '''
    url = self._base_url + '/statuses/featured.json'
    json = self._FetchUrl(url)
    data = simplejson.loads(json)
    self._CheckForTwitterError(data)
    return [User.NewFromJsonDict(x) for x in data]

  def GetUser(self, user):
    '''Returns a single user.

    The twitter.Api instance must be authenticated.

    Args:
      user: The username or id of the user to retrieve.

    Returns:
      A twitter.User instance representing that user
    '''
    url = self._base_url + '/users/show/%s.json' % user
    json = self._FetchUrl(url)
    data = simplejson.loads(json)
    self._CheckForTwitterError(data)
    return User.NewFromJsonDict(data)

  def GetDirectMessages(self, since=None, since_id=None, page=None):
    '''Returns a list of the direct messages sent to the authenticating user.

    The twitter.Api instance must be authenticated.

    Args:
      since:
        Narrows the returned results to just those statuses created
        after the specified HTTP-formatted date. [optional]
      since_id:
        Returns only public statuses with an ID greater than (that is,
        more recent than) the specified ID. [Optional]

    Returns:
      A sequence of twitter.DirectMessage instances
    '''
    url = self._base_url + '/direct_messages.json'
    if not self._username:
      raise TwitterError("The twitter.Api instance must be authenticated.")
    parameters = {}
    if since:
      parameters['since'] = since
    if since_id:
      parameters['since_id'] = since_id
    if page:
      parameters['page'] = page 
    json = self._FetchUrl(url, parameters=parameters)
    data = simplejson.loads(json)
    self._CheckForTwitterError(data)
    return [DirectMessage.NewFromJsonDict(x) for x in data]

  def PostDirectMessage(self, user, text):
    '''Post a twitter direct message from the authenticated user

    The twitter.Api instance must be authenticated.

    Args:
      user: The ID or screen name of the recipient user.
      text: The message text to be posted.  Must be less than 140 characters.

    Returns:
      A twitter.DirectMessage instance representing the message posted
    '''
    if not self._username:
      raise TwitterError("The twitter.Api instance must be authenticated.")
    url = self._base_url + '/direct_messages/new.json'
    data = {'text': text, 'user': user}
    json = self._FetchUrl(url, post_data=data)
    data = simplejson.loads(json)
    self._CheckForTwitterError(data)
    return DirectMessage.NewFromJsonDict(data)

  def DestroyDirectMessage(self, id):
    '''Destroys the direct message specified in the required ID parameter.

    The twitter.Api instance must be authenticated, and the
    authenticating user must be the recipient of the specified direct
    message.

    Args:
      id: The id of the direct message to be destroyed

    Returns:
      A twitter.DirectMessage instance representing the message destroyed
    '''
    url = self._base_url + '/direct_messages/destroy/%s.json' % id
    json = self._FetchUrl(url, post_data={})
    data = simplejson.loads(json)
    self._CheckForTwitterError(data)
    return DirectMessage.NewFromJsonDict(data)

  def CreateFriendship(self, user):
    '''Befriends the user specified in the user parameter as the authenticating user.

    The twitter.Api instance must be authenticated.

    Args:
      The ID or screen name of the user to befriend.
    Returns:
      A twitter.User instance representing the befriended user.
    '''
    url = self._base_url + '/friendships/create/%s.json' % user
    json = self._FetchUrl(url, post_data={})
    data = simplejson.loads(json)
    self._CheckForTwitterError(data)
    return User.NewFromJsonDict(data)

  def DestroyFriendship(self, user):
    '''Discontinues friendship with the user specified in the user parameter.

    The twitter.Api instance must be authenticated.

    Args:
      The ID or screen name of the user  with whom to discontinue friendship.
    Returns:
      A twitter.User instance representing the discontinued friend.
    '''
    url = self._base_url + '/friendships/destroy/%s.json' % user
    json = self._FetchUrl(url, post_data={})
    data = simplejson.loads(json)
    self._CheckForTwitterError(data)
    return User.NewFromJsonDict(data)

  def CreateFavorite(self, status):
    '''Favorites the status specified in the status parameter as the authenticating user.
    Returns the favorite status when successful.

    The twitter.Api instance must be authenticated.

    Args:
      The twitter.Status instance to mark as a favorite.
    Returns:
      A twitter.Status instance representing the newly-marked favorite.
    '''
    url = self._base_url + '/favorites/create/%s.json' % status.id
    json = self._FetchUrl(url, post_data={})
    data = simplejson.loads(json)
    self._CheckForTwitterError(data)
    return Status.NewFromJsonDict(data)

  def DestroyFavorite(self, status):
    '''Un-favorites the status specified in the ID parameter as the authenticating user.
    Returns the un-favorited status in the requested format when successful.

    The twitter.Api instance must be authenticated.

    Args:
      The twitter.Status to unmark as a favorite.
    Returns:
      A twitter.Status instance representing the newly-unmarked favorite.
    '''
    url = self._base_url + '/favorites/destroy/%s.json' % status.id
    json = self._FetchUrl(url, post_data={})
    data = simplejson.loads(json)
    self._CheckForTwitterError(data)
    return Status.NewFromJsonDict(data)

  def GetUserByEmail(self, email):
    '''Returns a single user by email address.

    Args:
      email: The email of the user to retrieve.
    Returns:
      A twitter.User instance representing that user
    '''
    url = self._base_url + '/users/show.json?email=%s' % email
    json = self._FetchUrl(url)
    data = simplejson.loads(json)
    self._CheckForTwitterError(data)
    return User.NewFromJsonDict(data)

  def VerifyCredentials(self):
    '''Returns a twitter.User instance if the authenticating user is valid.

    Returns: 
      A twitter.User instance representing that user if the
      credentials are valid, None otherwise.
    '''
    if not self._username:
      raise TwitterError("Api instance must first be given user credentials.")
    url = self._base_url + '/account/verify_credentials.json'
    try:
      json = self._FetchUrl(url, no_cache=True)
    except urllib2.HTTPError, http_error:
      if http_error.code == httplib.UNAUTHORIZED:
        return None
      else:
        raise http_error
    data = simplejson.loads(json)
    self._CheckForTwitterError(data)
    return User.NewFromJsonDict(data)

  def SetCredentials(self, username, password):
    '''Set the username and password for this instance

    Args:
      username: The twitter username.
      password: The twitter password.
    '''
    self._username = username
    self._password = password

  def ClearCredentials(self):
    '''Clear the username and password for this instance
    '''
    self._username = None
    self._password = None

  def SetCache(self, cache):
    '''Override the default cache.  Set to None to prevent caching.

    Args:
      cache: an instance that supports the same API as the twitter._FileCache
    '''
    if cache == DEFAULT_CACHE:
      self._cache = _FileCache()
    else:
      self._cache = cache

  def SetUrllib(self, urllib):
    '''Override the default urllib implementation.

    Args:
      urllib: an instance that supports the same API as the urllib2 module
    '''
    self._urllib = urllib

  def SetCacheTimeout(self, cache_timeout):
    '''Override the default cache timeout.

    Args:
      cache_timeout: time, in seconds, that responses should be reused.
    '''
    self._cache_timeout = cache_timeout

  def SetUserAgent(self, user_agent):
    '''Override the default user agent

    Args:
      user_agent: a string that should be send to the server as the User-agent
    '''
    self._request_headers['User-Agent'] = user_agent

  def SetXTwitterHeaders(self, client, url, version):
    '''Set the X-Twitter HTTP headers that will be sent to the server.

    Args:
      client:
         The client name as a string.  Will be sent to the server as
         the 'X-Twitter-Client' header.
      url:
         The URL of the meta.xml as a string.  Will be sent to the server
         as the 'X-Twitter-Client-URL' header.
      version:
         The client version as a string.  Will be sent to the server
         as the 'X-Twitter-Client-Version' header.
    '''
    self._request_headers['X-Twitter-Client'] = client
    self._request_headers['X-Twitter-Client-URL'] = url
    self._request_headers['X-Twitter-Client-Version'] = version

  def SetSource(self, source):
    '''Suggest the "from source" value to be displayed on the Twitter web site.

    The value of the 'source' parameter must be first recognized by
    the Twitter server.  New source values are authorized on a case by
    case basis by the Twitter development team.

    Args:
      source:
        The source name as a string.  Will be sent to the server as
        the 'source' parameter.
    '''
    self._default_params['source'] = source

  def _BuildUrl(self, url, path_elements=None, extra_params=None):
    # Break url into consituent parts
    (scheme, netloc, path, params, query, fragment) = urlparse.urlparse(url)

    # Add any additional path elements to the path
    if path_elements:
      # Filter out the path elements that have a value of None
      p = [i for i in path_elements if i]
      if not path.endswith('/'):
        path += '/'
      path += '/'.join(p)

    # Add any additional query parameters to the query string
    if extra_params and len(extra_params) > 0:
      extra_query = self._EncodeParameters(extra_params)
      # Add it to the existing query
      if query:
        query += '&' + extra_query
      else:
        query = extra_query

    # Return the rebuilt URL
    return urlparse.urlunparse((scheme, netloc, path, params, query, fragment))

  def _InitializeRequestHeaders(self, request_headers):
    if request_headers:
      self._request_headers = request_headers
    else:
      self._request_headers = {}

  def _InitializeUserAgent(self):
    user_agent = 'Python-urllib/%s (python-twitter/%s)' % \
                 (self._urllib.__version__, __version__)
    self.SetUserAgent(user_agent)

  def _InitializeDefaultParameters(self):
    self._default_params = {}

  def _AddAuthorizationHeader(self, username, password):
    if username and password:
      basic_auth = base64.encodestring('%s:%s' % (username, password))[:-1]
      self._request_headers['Authorization'] = 'Basic %s' % basic_auth

  def _RemoveAuthorizationHeader(self):
    if self._request_headers and 'Authorization' in self._request_headers:
      del self._request_headers['Authorization']

  def _GetOpener(self, url, username=None, password=None):
    if username and password:
      self._AddAuthorizationHeader(username, password)
      handler = self._urllib.HTTPBasicAuthHandler()
      (scheme, netloc, path, params, query, fragment) = urlparse.urlparse(url)
      handler.add_password(Api._API_REALM, netloc, username, password)
      opener = self._urllib.build_opener(handler)
    else:
      opener = self._urllib.build_opener()
    opener.addheaders = self._request_headers.items()
    return opener

  def _Encode(self, s):
    if self._input_encoding:
      return unicode(s, self._input_encoding).encode('utf-8')
    else:
      return unicode(s).encode('utf-8')

  def _EncodeParameters(self, parameters):
    '''Return a string in key=value&key=value form

    Values of None are not included in the output string.

    Args:
      parameters:
        A dict of (key, value) tuples, where value is encoded as
        specified by self._encoding
    Returns:
      A URL-encoded string in "key=value&key=value" form
    '''
    if parameters is None:
      return None
    else:
      return urllib.urlencode(dict([(k, self._Encode(v)) for k, v in parameters.items() if v is not None]))

  def _EncodePostData(self, post_data):
    '''Return a string in key=value&key=value form

    Values are assumed to be encoded in the format specified by self._encoding,
    and are subsequently URL encoded.

    Args:
      post_data:
        A dict of (key, value) tuples, where value is encoded as
        specified by self._encoding
    Returns:
      A URL-encoded string in "key=value&key=value" form
    '''
    if post_data is None:
      return None
    else:
      return urllib.urlencode(dict([(k, self._Encode(v)) for k, v in post_data.items()]))

  def _CheckForTwitterError(self, data):
    """Raises a TwitterError if twitter returns an error message.

    Args:
      data: A python dict created from the Twitter json response
    Raises:
      TwitterError wrapping the twitter error message if one exists.
    """
    # Twitter errors are relatively unlikely, so it is faster
    # to check first, rather than try and catch the exception
    if 'error' in data:
      raise TwitterError(data['error'])

  def _FetchUrl(self,
                url,
                post_data=None,
                parameters=None,
                no_cache=None):
    '''Fetch a URL, optionally caching for a specified time.

    Args:
      url: The URL to retrieve
      post_data: 
        A dict of (str, unicode) key/value pairs.  If set, POST will be used.
      parameters:
        A dict whose key/value pairs should encoded and added 
        to the query string. [OPTIONAL]
      no_cache: If true, overrides the cache on the current request

    Returns:
      A string containing the body of the response.
    '''
    # Build the extra parameters dict
    extra_params = {}
    if self._default_params:
      extra_params.update(self._default_params)
    if parameters:
      extra_params.update(parameters)

    # Add key/value parameters to the query string of the url
    url = self._BuildUrl(url, extra_params=extra_params)

    # Get a url opener that can handle basic auth
    opener = self._GetOpener(url, username=self._username, password=self._password)

    encoded_post_data = self._EncodePostData(post_data)

    # Open and return the URL immediately if we're not going to cache
    if encoded_post_data or no_cache or not self._cache or not self._cache_timeout:
      url_data = opener.open(url, encoded_post_data).read()
      opener.close()
    else:
      # Unique keys are a combination of the url and the username
      if self._username:
        key = self._username + ':' + url
      else:
        key = url

      # See if it has been cached before
      last_cached = self._cache.GetCachedTime(key)

      # If the cached version is outdated then fetch another and store it
      if not last_cached or time.time() >= last_cached + self._cache_timeout:
        url_data = opener.open(url, encoded_post_data).read()
        opener.close()
        self._cache.Set(key, url_data)
      else:
        url_data = self._cache.Get(key)

    # Always return the latest version
    return url_data


class _FileCacheError(Exception):
  '''Base exception class for FileCache related errors'''

class _FileCache(object):

  DEPTH = 3

  def __init__(self,root_directory=None):
    self._InitializeRootDirectory(root_directory)

  def Get(self,key):
    path = self._GetPath(key)
    if os.path.exists(path):
      return open(path).read()
    else:
      return None

  def Set(self,key,data):
    path = self._GetPath(key)
    directory = os.path.dirname(path)
    if not os.path.exists(directory):
      os.makedirs(directory)
    if not os.path.isdir(directory):
      raise _FileCacheError('%s exists but is not a directory' % directory)
    temp_fd, temp_path = tempfile.mkstemp()
    temp_fp = os.fdopen(temp_fd, 'w')
    temp_fp.write(data)
    temp_fp.close()
    if not path.startswith(self._root_directory):
      raise _FileCacheError('%s does not appear to live under %s' %
                            (path, self._root_directory))
    if os.path.exists(path):
      os.remove(path)
    os.rename(temp_path, path)

  def Remove(self,key):
    path = self._GetPath(key)
    if not path.startswith(self._root_directory):
      raise _FileCacheError('%s does not appear to live under %s' %
                            (path, self._root_directory ))
    if os.path.exists(path):
      os.remove(path)

  def GetCachedTime(self,key):
    path = self._GetPath(key)
    if os.path.exists(path):
      return os.path.getmtime(path)
    else:
      return None

  def _GetUsername(self):
    '''Attempt to find the username in a cross-platform fashion.'''
    try:
      return os.getenv('USER') or \
             os.getenv('LOGNAME') or \
             os.getenv('USERNAME') or \
             os.getlogin() or \
             'nobody'
    except (IOError, OSError), e:
      return 'nobody'

  def _GetTmpCachePath(self):
    username = self._GetUsername()
    cache_directory = 'python.cache_' + username
    return os.path.join(tempfile.gettempdir(), cache_directory)

  def _InitializeRootDirectory(self, root_directory):
    if not root_directory:
      root_directory = self._GetTmpCachePath()
    root_directory = os.path.abspath(root_directory)
    if not os.path.exists(root_directory):
      os.mkdir(root_directory)
    if not os.path.isdir(root_directory):
      raise _FileCacheError('%s exists but is not a directory' %
                            root_directory)
    self._root_directory = root_directory

  def _GetPath(self,key):
    try:
        hashed_key = md5(key).hexdigest()
    except TypeError:
        hashed_key = md5.new(key).hexdigest()
        
    return os.path.join(self._root_directory,
                        self._GetPrefix(hashed_key),
                        hashed_key)

  def _GetPrefix(self,hashed_key):
    return os.path.sep.join(hashed_key[0:_FileCache.DEPTH])


########NEW FILE########
__FILENAME__ = twitterprovider
from identicaprovider import IdenticaProvider
from cloudsn.core.keyring import Credentials
from cloudsn.core.account import AccountCacheMails
from cloudsn.core import config
from cloudsn.providers import tweepy
from gi.repository import Gtk

CONSUMER_KEY = 'uRPdgq7wqkiKmWzs9rneJA'
CONSUMER_SECRET = 'ZwwhbUl2mwdreaiGFd8IqUhfsZignBJIYknVA867Ieg'

class TwitterProvider(IdenticaProvider):

    __default = None

    def __init__(self):
        IdenticaProvider.__init__(self, "Twitter", "twitter", "http://twitter.com")

    @staticmethod
    def get_instance():
        if not TwitterProvider.__default:
            TwitterProvider.__default = TwitterProvider()
        return TwitterProvider.__default

    def get_api(self, account):
        credentials = account.get_credentials()
        ACCESS_KEY = credentials.username
        ACCESS_SECRET = credentials.password
        auth = tweepy.OAuthHandler(CONSUMER_KEY, CONSUMER_SECRET)
        auth.set_access_token(ACCESS_KEY, ACCESS_SECRET)
        return tweepy.API(auth)
        
    def get_account_data_widget (self, account=None):
        self.conf_widget = TwitterPrefs(account, self)
        return self.conf_widget.load()

    def set_account_data_from_widget(self, account_name, widget, account=None):
        return self.conf_widget.set_account_data(account_name)
        
        
class TwitterPrefs:

    def __init__(self, account, provider):
        self.account = account
        self.provider = provider

    def load(self):
        self.builder=Gtk.Builder()
        self.builder.set_translation_domain("cloudsn")
        self.builder.add_from_file(config.add_data_prefix("twitter-account.ui"))
        self.box = self.builder.get_object("container")
        self.permission_button = self.builder.get_object("permission_button")
        self.pin_entry = self.builder.get_object("pin_entry")
        
        self.auth = tweepy.OAuthHandler(CONSUMER_KEY, CONSUMER_SECRET)
        auth_url = self.auth.get_authorization_url()
        self.permission_button.set_uri(auth_url)
        
        self.builder.connect_signals(self)
        if self.account:
            #Do not support editting
            pass
        return self.box

    def set_account_data (self, account_name):
        pin = self.pin_entry.get_text()
        if pin=='':
            raise Exception(_("The PIN is mandatory to set the Twitter account"))

        self.auth.get_access_token(pin)
        access_key = self.auth.access_token.key
        access_secret = self.auth.access_token.secret
        if not self.account:
            props = {"name" : account_name, "provider_name" : self.provider.get_name()}
            self.account = AccountCacheMails(props, self.provider)
            self.account.notifications = {}

        credentials = Credentials(access_key, access_secret)
        self.account.set_credentials(credentials)

        return self.account
        

########NEW FILE########
__FILENAME__ = about
#encoding: utf-8
from gi.repository import Gtk, GdkPixbuf
from cloudsn import const
from cloudsn.core import config

def show_about_dialog():
    dialog = Gtk.AboutDialog()
    dialog.set_name(const.APP_LONG_NAME)
    dialog.set_version(const.APP_VERSION)
    dialog.set_copyright (const.APP_COPYRIGHT)
    dialog.set_comments(const.APP_DESCRIPTION)
    dialog.set_website (const.APP_WEBSITE)
    dialog.set_logo(GdkPixbuf.Pixbuf.new_from_file(config.add_data_prefix('cloudsn120.png')))
    dialog.set_authors (["Jesús Barbero Rodríguez"])
    dialog.run()
    dialog.hide()

########NEW FILE########
__FILENAME__ = authwarning
from gi.repository import Gtk
import gettext
from cloudsn import logger
from cloudsn.core.config import SettingsController, get_cloudsn_icon
from cloudsn.core.utils import get_boolean
from cloudsn.const import *
from cloudsn.core.keyring import get_keyring

AUTH_DONT_ASK_KEY = "auth_dont_ask"

def check_auth_configuration():
    try:
        import gnomekeyring as gk
        from ..core.keyrings import gkeyring
    except Exception:
        logger.debug("Gnome keyring is not available")
        return

    conf = SettingsController.get_instance()
    prefs = conf.get_prefs()
    if AUTH_DONT_ASK_KEY in prefs and get_boolean(prefs[AUTH_DONT_ASK_KEY]) == True:
        return
    
    if get_keyring().get_id() == gkeyring.GNOME_KEYRING_ID:
        return

    label = Gtk.Label()
    label.set_markup(_("""<b>Security warning</b>

You have gnome-keyring installed but your are using plain text encryption
to store your passwords. You can select the encryption method
in the preferences dialog.

"""))
    dialog = Gtk.Dialog(APP_LONG_NAME,
                       None,
                       Gtk.DialogFlags.MODAL | Gtk.DialogFlags.DESTROY_WITH_PARENT,
                       (Gtk.STOCK_OK, Gtk.ResponseType.ACCEPT))
    dialog.set_icon(get_cloudsn_icon())
    dialog.vbox.pack_start(label, False, False, 10)
    checkbox = Gtk.CheckButton(_("Don't ask me again"))
    checkbox.show()
    dialog.vbox.pack_end(checkbox, False, False, 0)
    label.show()
    response = dialog.run()
    dialog.destroy()
    if checkbox.get_active():
        conf.set_pref (AUTH_DONT_ASK_KEY, True)
        conf.save_prefs()


########NEW FILE########
__FILENAME__ = indicatorapplet
# -*- mode: python; tab-width: 4; indent-tabs-mode: nil -*-
#!/usr/bin/python
from gi.repository import Gtk, Indicate
from cloudsn.core import config, utils, account
from cloudsn.ui import window
from cloudsn.core.indicator import Indicator
from cloudsn.const import *
from cloudsn import logger

class IndicatorApplet (Indicator):

    def __init__(self):
        self.am = account.AccountManager.get_instance()
        
    def get_name(self):
        return _("Indicator Applet")

    def set_active(self, active):
        if active:
            self.server = Indicate.Server.ref_default()
            self.server.set_type("message.im")
            self.server.connect("server-display", self.on_server_display_cb)
            self.server.set_desktop_file(config.add_apps_prefix("cloudsn.desktop"))
            self.server.show()
            logger.debug("Indicator server created")
        else:
            #TODO Disable the indicators
            logger.debug("deactivate Not implemented")

    def create_indicator(self, acc):
        indicator = Indicate.Indicator()
        indicator.set_property("name", acc.get_name())
        indicator.set_property("count", str(acc.get_total_unread()))
        #TODO indicator.set_property_icon("icon", acc.get_icon())
        indicator.show()
        indicator.connect("user-display", self.on_indicator_display_cb)
        acc.indicator = indicator
        indicator.account = acc
        acc.is_error_icon = False
        logger.debug("Indicator created")

    def update_account(self, acc):
        #We had a previous error but now the update works.
        if acc.is_error_icon:
            #acc.indicator.set_property_icon("icon", acc.get_icon())
            acc.is_error_icon = False
        else:
            if len(acc.get_new_unread_notifications()) > 0:
                acc.indicator.set_property('draw-attention', 'true')

        if acc.get_total_unread() < 1:
            acc.indicator.set_property('draw-attention', 'false')
            
        acc.indicator.set_property("count", str(acc.get_total_unread()))

    def update_error(self, acc):
        if not acc.is_error_icon:
            #TODO acc.indicator.set_property_icon("icon", acc.get_icon())
            acc.is_error_icon = True
        acc.indicator.set_property("count", "0")
        
    def remove_indicator(self, acc):
        acc.indicator = None

    def on_server_display_cb(self, server, timestamp=None):
        for acc in self.am.get_accounts():
            if acc.get_active() and acc.indicator:
                acc.indicator.set_property('draw-attention', 'false')
	    win = window.MainWindow.get_instance()
        win.run()
    
    def on_indicator_display_cb(self, indicator, timestamp=None):
        indicator.set_property('draw-attention', 'false')
        indicator.account.activate ()
        

########NEW FILE########
__FILENAME__ = statusicon
from gi.repository import Gtk, Gdk, GdkPixbuf
from cloudsn import const
from cloudsn.core import config, controller, utils
from cloudsn.ui import window, about
from cloudsn.core.indicator import Indicator
from cloudsn.const import *
from cloudsn import logger
import gettext

class StatusIconIndicator (Indicator):

    def set_active(self, active):
        if active:
            self.statusIcon = Gtk.StatusIcon()
            self.statusIcon.set_from_pixbuf(config.get_cloudsn_icon())
            self.statusIcon.set_visible(True)
            self.statusIcon.set_tooltip_text(APP_LONG_NAME)
            self.statusIcon.connect('activate', self.main_cb, self.statusIcon)

            self.menu = self.create_pref_menu()
            self.indmenu = self.create_main_menu()

            self.statusIcon.connect('popup-menu', self.popup_menu_cb, self.menu)
            self.statusIcon.set_visible(1)
        else:
            #TODO Discable the indicators
            logger.debug("deactivate Not implemented")

    def get_name(self):
        return _("Status Icon")

    def create_main_menu(self):
        indmenu = Gtk.Menu()
        indmenuItem = Gtk.MenuItem("---")
        indmenuItem.get_child().set_markup("<b>%s</b>" % (APP_LONG_NAME))
        indmenuItem.connect('activate', self.preferences_cb, self.statusIcon)
        #indmenuItem.set_sensitive(False)
        indmenu.append(indmenuItem)

        return indmenu

    def create_pref_menu(self):
        menu = Gtk.Menu()
        menuItem = Gtk.ImageMenuItem.new_from_stock(Gtk.STOCK_REFRESH, None)
        menuItem.set_label(_("Update accounts"))
        menuItem.connect('activate', self.update_accounts_cb, self.statusIcon)
        menu.append(menuItem)
        menuItem = Gtk.ImageMenuItem.new_from_stock(Gtk.STOCK_PREFERENCES, None)
        menuItem.connect('activate', self.preferences_cb, self.statusIcon)
        menu.append(menuItem)
        menuItem =  Gtk.SeparatorMenuItem.new()
        menu.append(menuItem)
        menuItem = Gtk.ImageMenuItem.new_from_stock(Gtk.STOCK_ABOUT, None)
        menuItem.connect('activate', self.about_cb, self.statusIcon)
        menu.append(menuItem)
        menuItem = Gtk.ImageMenuItem.new_from_stock(Gtk.STOCK_QUIT, None)
        menuItem.connect('activate', self.quit_cb, self.statusIcon)
        menu.append(menuItem)
        return menu

    def create_indicator(self, acc):
        pix = self.scale_pixbuf(acc.get_icon())
        indmenuItem = Gtk.MenuItem.new()
        box = Gtk.HBox()
        menu_icon = Gtk.Image.new_from_pixbuf(pix)
        box.pack_start(menu_icon, False, False, 0)
        box.pack_start(Gtk.Label(acc.get_name()), False, True, 10)
        total_label = Gtk.Label(("(%i)") % (acc.get_total_unread()))
        box.pack_end(total_label, False, False, 0)
        indmenuItem.add(box)
        indmenuItem.connect('activate', self.acc_activate_cb, acc)
        self.indmenu.append(indmenuItem)
        acc.indicator = indmenuItem
        acc.total_label = total_label
        acc.menu_icon = menu_icon
        acc.is_error_icon = False

    def update_account(self, acc):
        #We had a previous error but now the update works.
        if acc.is_error_icon:
            acc.menu_icon.set_from_pixbuf(self.scale_pixbuf(acc.get_icon()))
            acc.is_error_icon = False

        acc.total_label.set_label(("(%i)") % (acc.get_total_unread()))

    def update_error(self, acc):
        if not acc.is_error_icon:
            acc.menu_icon.set_from_pixbuf(self.scale_pixbuf(acc.get_icon()))
            acc.is_error_icon = True
        acc.total_label.set_label("")

    def remove_indicator(self, acc):
        logger.debug("remove indicator")
        #If the account is disabled, there is not an indicator
        if acc.indicator:
            self.indmenu.remove(acc.indicator)
        acc.indicator = None
        acc.total_label = None

    def preferences_cb(self, widget, acc = None):
        win = window.MainWindow.get_instance()
        win.run()

    def update_accounts_cb(self, widget, acc = None):
        c = controller.Controller.get_instance()
        c.update_accounts()

    def acc_activate_cb(self, widget, acc = None):
        acc.activate()

    def main_cb(self, widget, data = None):
        self.indmenu.show_all()
        self.indmenu.popup(None, None, Gtk.StatusIcon.position_menu,
                           self.statusIcon, 1, Gtk.get_current_event_time())

    def quit_cb(self, widget, data = None):
       Gtk.main_quit()

    def about_cb (self, widget, data = None):
        about.show_about_dialog()

    def popup_menu_cb(self, widget, button, time, data = None):
        if button == 3:
            if data:
                data.show_all()
                data.popup(None, None, Gtk.StatusIcon.position_menu,
                           self.statusIcon, 3, time)
    def scale_pixbuf (self, pix):
        return pix.scale_simple(16,16,GdkPixbuf.InterpType.BILINEAR)


########NEW FILE########
__FILENAME__ = utils
# -*- mode: python; tab-width: 4; indent-tabs-mode: nil -*-
from gi.repository import Gtk

def create_provider_widget(fields):
    table = Gtk.Table(len(fields), 2)
    table.widgets = {}
    i = 0
    for f in fields:
        hbox = Gtk.HBox()
        label = Gtk.Label(f["label"])
        if f["type"] == "pwd":
            entry = Gtk.Entry()
            entry.set_visibility(False)
        elif f["type"] == "check":
            entry = Gtk.CheckButton()
        else:
            entry = Gtk.Entry()

        entry.set_name(f["label"])
        table.attach(label, 0, 1, i, i+1)
        table.attach(entry, 1, 2, i, i+1)
        i += 1
        table.widgets[f["label"]] = entry
    return table

def get_widget_by_label(table, label):
    return table.widgets[label]

########NEW FILE########
__FILENAME__ = window
# -*- mode: python; tab-width: 4; indent-tabs-mode: nil -*-
from gi.repository import Gtk
import os
import shutil
import gettext
from cloudsn.core import config, provider, account, indicator, keyring
from cloudsn import logger
import cloudsn.core.utils as coreutils

STOP_RESPONSE = 1

class MainWindow:

    __default = None

    def __init__ (self):
        if MainWindow.__default:
            raise MainWindow.__default
        self.builder = None
        self.window = None
        self.dialog_only = False
        self.pref_dialog = None
        self.config = config.SettingsController.get_instance()
        self.pm = provider.ProviderManager.get_instance()
        self.am = account.AccountManager.get_instance()
        self.im = indicator.IndicatorManager.get_instance()
        self.km = keyring.KeyringManager.get_instance()
        self.am.connect ("account-deleted", self.account_deleted_cb)

    @staticmethod
    def get_instance():
        if not MainWindow.__default:
            MainWindow.__default = MainWindow()
        return MainWindow.__default

    def get_main_account_selected (self):
        selection = self.main_account_tree.get_selection()
        if selection:
            model, paths = selection.get_selected_rows()
            for path in paths:
                citer = self.main_store.get_iter(path)
                account_name = self.main_store.get_value(citer, 1)
                acc = self.am.get_account(account_name)
                return acc, citer

        return None, None

    def __get_account_date(self, acc):
        last_update = ''
        dt = acc.get_last_update()
        if dt:
            last_update = dt.strftime("%Y-%m-%d %H:%M:%S")

        return last_update

    def select_provider_combo (self, providers_combo, name):
        #Select the provider and disable item
        i=0
        for row in providers_combo.get_model():
            if row[1] == name:
                providers_combo.set_active (i)
                break
            i += 1

    def load_window(self):
        from cloudsn.core.controller import Controller

        self.builder=Gtk.Builder()
        self.builder.set_translation_domain("cloudsn")
        self.builder.add_from_file(config.add_data_prefix("preferences.ui"))
        self.builder.connect_signals(self)
        self.window=self.builder.get_object("main_window")
        self.window.connect ("delete-event", self.window_delete_event_cb)
        self.window.set_icon(config.get_cloudsn_icon())
        self.main_account_tree = self.builder.get_object("main_account_tree");
        self.main_store = self.builder.get_object("account_store");
        self.providers_combo = self.builder.get_object("providers_combo");
        self.providers_store = self.builder.get_object("providers_store");
        self.play_button = self.builder.get_object("tool_play");
        self.read_button = self.builder.get_object("main_read_button");

        #Populate accounts
        for acc in self.am.get_accounts():
            self.main_store.append([acc.get_icon(), acc.get_name(),
                self.__get_account_date(acc), acc.get_active(),
                acc.get_total_unread()])

        #Populate providers
        for prov in self.pm.get_providers():
            self.providers_store.append([prov.get_icon(), prov.get_name()])

        #Update the last check date
        Controller.get_instance().connect ("account-checked",
            self.__on_account_checked_cb)

        Controller.get_instance().connect ("account-check-error",
            self.__on_account_check_error_cb)

        self.set_play_active (Controller.get_instance().get_active())

    def run(self):
        self.load_window()
        self.window.show()

    def set_play_active(self, active):
        self.play_button.set_active(active)
        if active:
            self.play_button.set_stock_id(Gtk.STOCK_MEDIA_PAUSE)
            self.play_button.set_tooltip_text(
                _("Press to pause the checker daemon"))
        else:
            self.play_button.set_stock_id(Gtk.STOCK_MEDIA_PLAY)
            self.play_button.set_tooltip_text(
                _("Press to start the checker daemon"))

    def preferences_action_activate_cb (self, widget, data=None):
        self.pref_dialog = self.builder.get_object("preferences_dialog")
        self.pref_dialog.set_transient_for(self.window)
        self.pref_dialog.set_destroy_with_parent (True)
        indicator_combo = self.builder.get_object("indicator_combo")
        indicators_store = self.builder.get_object("indicators_store");
        keyring_combo = self.builder.get_object("keyring_combo")
        keyring_store = self.builder.get_object("keyring_store");
        minutes=self.builder.get_object("minutes_spin")
        max_not_spin=self.builder.get_object("max_not_spin")
        startup_check = self.builder.get_object("startup_check")
        enable_sounds_check = self.builder.get_object("enable_sounds_check")

        minutes.set_value (float(self.config.get_prefs()["minutes"]))
        max_not_spin.set_value (float(self.config.get_prefs()["max_notifications"]))
        if os.path.exists(config.get_startup_file_path()):
            startup_check.set_active(True)
        else:
            startup_check.set_active(False)

        enable_sounds_check.set_active(coreutils.get_boolean(self.config.get_prefs()["enable_sounds"]))

        #Populate indicator combo
        i=0
        indicator_name = self.config.get_prefs()["indicator"]
        indicators_store.clear()
        for indi in self.im.get_indicators():
            indicators_store.append([indi.get_name()])
            if indi.get_name() == indicator_name:
                indicator_combo.set_active(i)
            i+=1
        i=0
        keyring_id = self.config.get_prefs()["keyring"]
        keyring_store.clear()
        for k in self.km.get_managers():
            keyring_store.append([k.get_name(), k.get_id()])
            if k.get_id() == keyring_id:
                keyring_combo.set_active(i)
            i+=1
        response = self.pref_dialog.run()
        self.pref_dialog.hide()
        self.config.set_pref ("minutes", minutes.get_value())
        self.config.set_pref ("max_notifications", max_not_spin.get_value())
        self.config.set_pref ("enable_sounds", enable_sounds_check.get_active())
        iiter = indicator_combo.get_active_iter()
        if iiter:
            self.config.set_pref ("indicator", indicators_store.get_value(iiter,0))
        iiter = keyring_combo.get_active_iter()

        selected = keyring_store.get_value(iiter,1)
        for m in self.km.get_managers():
            logger.debug("selected %s, current %s" % (selected, m.get_id()))
            if m.get_id() == selected:
                self.km.set_manager(m)
                break

        self.config.set_pref ("keyring", selected)

        #Check startup checkbox
        if startup_check.get_active():
            if not os.path.exists(config.get_startup_file_path()):
                if not os.path.exists(config.get_startup_file_dir()):
                    os.makedirs(config.get_startup_file_dir())
                shutil.copyfile(config.add_data_prefix("cloudsn.desktop"),
                    config.get_startup_file_path())
        else:
            if os.path.exists(config.get_startup_file_path()):
                os.remove (config.get_startup_file_path())

        self.config.save_prefs()

    def about_action_activate_cb (self, widget, data=None):
        about.show_about_dialog()

    def quit_action_activate_cb (self, widget, data=None):
        Gtk.main_quit()

    def close_action_activate_cb (self, widget, data=None):
        if self.dialog_only:
            Gtk.main_quit()
        else:
            self.window.hide()

    def main_delete_button_clicked_cb(self, widget, data=None):
        acc, citer = self.get_main_account_selected()
        if not acc:
            return

        msg = (_('Are you sure you want to delete the account %s?')) % (acc.get_name());

        dia = Gtk.MessageDialog(self.window,
                  Gtk.DialogFlags.MODAL | Gtk.DialogFlags.DESTROY_WITH_PARENT,
                  Gtk.MessageType.QUESTION,
                  Gtk.ButtonsType.YES_NO,
                  msg)
        dia.show_all()
        if dia.run() == Gtk.ResponseType.YES:
            self.am.del_account(acc, True)
        dia.hide()

    def main_update_button_clicked_cb(self, widget, data=None):
        from cloudsn.core.controller import Controller
        acc, citer = self.get_main_account_selected()
        if acc:
            Controller.get_instance().update_account(acc)

    def main_read_button_clicked_cb(self, widget, data=None):
        acc, citer = self.get_main_account_selected()
        if acc and acc.can_mark_read():
            acc.mark_read()
        self.__on_account_checked_cb(None, acc)

    def main_account_tree_cursor_changed_cb(self, widget, data=None):
        acc, citer = self.get_main_account_selected()
        if acc and acc.can_mark_read():
            self.read_button.set_sensitive(True)
        else:
            self.read_button.set_sensitive(False)

    def tool_play_toggled_cb (self, widget, data=None):
        from cloudsn.core.controller import Controller
        self.set_play_active(widget.get_active())
        Controller.get_instance().set_active(widget.get_active())

    def account_deleted_cb(self, widget, acc):
        selection = self.main_account_tree.get_selection()
        if selection:
            model, paths = selection.get_selected_rows()
            for path in paths:
                citer = self.main_store.get_iter(path)
                self.main_store.remove(citer)

    def window_delete_event_cb (self, widget, event, data=None):
        if self.dialog_only:
            Gtk.main_quit()
        else:
            self.window.hide()

    def active_cell_toggled_cb(self, cell, path, data=None):
        active = not self.main_store[path][3]
        self.main_store[path][3] = active
        account_name = self.main_store[path][1]
        acc = self.am.get_account(account_name)
        self.am.set_account_active(acc, active)

    def new_action_activate_cb(self, widget, data=None):
        self.new_dialog = self.builder.get_object("account_new_dialog")
        account_name_entry = self.builder.get_object("account_name_entry");
        self.provider_content = self.builder.get_object("provider_content")
        self.activate_command_entry = self.builder.get_object("activate_command_entry")
        self.provider_content.account = None
        self.new_dialog.set_transient_for(self.window)
        self.new_dialog.set_destroy_with_parent (True)
        account_name_entry.set_text("")
        account_name_entry.set_sensitive (True)
        self.providers_combo.set_sensitive (True)
        self.providers_combo.set_active(-1)
        for c in self.provider_content.get_children():
            if c:
                self.provider_content.remove(c)
                c.destroy()
        end = False
        while not end:
            response = self.new_dialog.run()
            if response == 0:
                try:
                    if len(self.provider_content.get_children())==0:
                        raise Exception(_("You must select a provider and fill the data"))

                    acc_name = account_name_entry.get_text()
                    if acc_name == '':
                        raise Exception(_("You must fill the account name"))

                    custom_widget = self.provider_content.get_children()[0]
                    citer = self.providers_combo.get_active_iter()
                    provider_name = self.providers_store.get_value (citer, 1)
                    provider = self.pm.get_provider(provider_name)
                    acc = provider.set_account_data_from_widget(acc_name, custom_widget)
                    acc.set_activate_command (self.activate_command_entry.get_text())
                    self.am.add_account(acc)
                    self.am.save_account(acc)
                    self.main_store.append([acc.get_icon(),
                            acc.get_name(),self.__get_account_date(acc),
                            acc.get_active(), acc.get_total_unread()])
                    end = True
                except Exception, e:
                    logger.error ('Error adding a new account: %s', e)
                    md = Gtk.MessageDialog(self.window,
                        Gtk.DialogFlags.DESTROY_WITH_PARENT, Gtk.MessageType.ERROR,
                        Gtk.ButtonsType.CLOSE,
                        _('Error adding a new account: ') + str(e))
                    md.run()
                    md.destroy()
            else:
                end = True

        self.new_dialog.hide()

    def edit_action_activate_cb(self, widget, data=None):

        acc, citer = self.get_main_account_selected()

        if not acc:
            return

        self.new_dialog = self.builder.get_object("account_new_dialog")
        account_name_entry = self.builder.get_object("account_name_entry");
        account_name_entry.set_text(acc.get_name())
        #TODO the name cannot be modified by the moment
        account_name_entry.set_sensitive (False)
        self.provider_content = self.builder.get_object("provider_content")
        self.activate_command_entry = self.builder.get_object("activate_command_entry")
        self.provider_content.account = acc
        self.new_dialog.set_transient_for(self.window)
        self.new_dialog.set_destroy_with_parent (True)

        #Select the provider and disable item
        providers_combo = self.builder.get_object("providers_combo")
        providers_combo.set_active(-1)
        self.select_provider_combo (providers_combo, acc.get_provider().get_name())

        providers_combo.set_sensitive (False)

        end = False
        while not end:
            response = self.new_dialog.run()
            if response == 0:
                try:
                    acc_name = account_name_entry.get_text()
                    if acc_name == '':
                        raise Exception(_("You must fill the account name"))

                    custom_widget = self.provider_content.get_children()[0]

                    acc = acc.get_provider().set_account_data_from_widget(acc_name, custom_widget, acc)
                    acc.set_activate_command (self.activate_command_entry.get_text())
                    self.am.save_account(acc)
                    end = True
                except Exception, e:
                    logger.exception ('Error editing the account: %s', e)
                    md = Gtk.MessageDialog(self.window,
                        Gtk.DialogFlags.DESTROY_WITH_PARENT, Gtk.MessageType.ERROR,
                        Gtk.ButtonsType.CLOSE,
                        _('Error editing the account: ') + str(e))
                    md.run()
                    md.destroy()
            else:
                end = True

        self.new_dialog.hide()

    def update_all_action_activate_cb (self, widget, data=None):
        from cloudsn.core.controller import Controller
        Controller.get_instance().update_accounts()

    def providers_combo_changed_cb(self, widget, data=None):
        ch = self.provider_content.get_children()
        for c in ch:
            self.provider_content.remove(c)
            c.destroy()

        citer = self.providers_combo.get_active_iter()
        if not citer:
            return
        provider_name = self.providers_store.get_value (citer, 1)
        provider = self.pm.get_provider(provider_name)

        if provider.get_import_error():
            md = Gtk.MessageDialog(self.window,
                Gtk.DialogFlags.DESTROY_WITH_PARENT, Gtk.MessageType.ERROR,
                Gtk.ButtonsType.CLOSE,
                _('Error loading the provider: ') + str(provider.get_import_error()))
            md.run()
            md.destroy()
            return

        box =  provider.get_account_data_widget(self.provider_content.account)
        self.provider_content.add(box)
        if self.provider_content.account:
            self.activate_command_entry.set_text(self.provider_content.account.get_activate_command())
        box.show_all()

    def __on_account_checked_cb(self, widget, acc):
        for row in self.main_store:
            if row[1] == acc.get_name():
                row[0] = acc.get_icon()
                row[2] = self.__get_account_date(acc)
                row[4] = acc.get_total_unread()

    def __on_account_check_error_cb(self, widget, acc):
        for row in self.main_store:
            if row[1] == acc.get_name():
                row[0] = acc.get_icon()
                row[2] = self.__get_account_date(acc)
                row[4] = acc.get_total_unread()

def main ():
    import cloudsn.cloudsn
    import cloudsn.core.controller
    cloudsn.cloudsn.setup_locale_and_gettext()
    #account.AccountManager.get_instance().load_accounts()
    cloudsn.core.controller.Controller.get_instance()
    win = MainWindow.get_instance()
    win.dialog_only = True
    win.run()
    Gtk.main()

if __name__ == "__main__":
    main()


########NEW FILE########
__FILENAME__ = greader
import os, sys, re

srcpath = os.path.abspath("../src")
sys.path.insert(0,srcpath)

import traceback, urllib2, httplib, urllib, simplejson
import cookielib
import webbrowser
from cloudsn.providers.greaderprovider import *


SCOPE = 'https://www.google.com/reader/api'
def main():
    #Ask for permissions and set the pin
    #password = raw_input('password: ').strip()
    cookiejar = cookielib.CookieJar()
    _cproc = urllib2.HTTPCookieProcessor(cookiejar)
    opener = urllib2.build_opener(_cproc)
    urllib2.install_opener(opener)
    url = 'https://accounts.google.com/o/oauth2/auth?client_id=%s&redirect_uri=%s&response_type=%s&scope=%s' \
            % (CLIENT_ID, REDIRECT_URI, \
               'code', SCOPE)
          
    webbrowser.open (url)
    pin = raw_input('PIN: ').strip()
    
    params = {'client_id' : CLIENT_ID,
	              'client_secret': CLIENT_SECRET,
	              'code': pin,
	              'redirect_uri': REDIRECT_URI,
	              'grant_type' : 'authorization_code',
	              'scope' : SCOPE,
	              }
    f = opener.open ('https://accounts.google.com/o/oauth2/token', urllib.urlencode(params))
    data = f.read()
    print data
    data = simplejson.loads(data)
    
    params = {'client_id' : CLIENT_ID,
	              'client_secret': CLIENT_SECRET,
	              'grant_type' : 'refresh_token',
	              'refresh_token' : data['refresh_token'],
	              }
    f = opener.open ('https://accounts.google.com/o/oauth2/token', urllib.urlencode(params))
    data = f.read()
    print data
    data = simplejson.loads(data)
    
    """
    request = urllib2.Request(r"https://www.google.com/reader/api/0/unread-count")
    request.add_header("Authorization", "Bearer " + data["access_token"])

    data = urllib2.urlopen(request).read()
    print data
    return
    """
    
    url = SCOPE + '?access_token='+ data['access_token']
    print url
    f = opener.open(url)
    data = f.read()
    print data
    return
    match_obj = re.search(r'SID=(.*)', data, re.IGNORECASE)
    sid = match_obj.group(1) if match_obj.group(1) is not None else ''
    print sid
    match_obj = re.search(r'LSID=(.*)', data, re.IGNORECASE)
    lsid = match_obj.group(1) if match_obj.group(1) is not None else ''
    print lsid
    
    cookiejar.add_cookie(req, 'cname2', 'cval2',
                {'expires':  int(time.time()) + 3600,})
    
    f = opener.open('http://www.google.com/reader/api/0/token')
    print f.read()
    
        
if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = identica2
import os, sys

srcpath = os.path.abspath("../src")
sys.path.insert(0,srcpath)

import traceback, urllib2, httplib
import webbrowser
from cloudsn.providers import tweepy

CONSUMER_KEY = 'uRPdgq7wqkiKmWzs9rneJA'
CONSUMER_SECRET = 'ZwwhbUl2mwdreaiGFd8IqUhfsZignBJIYknVA867Ieg'

def main():
    #Ask for permissions and set the pin
    password = raw_input('password: ').strip()
    auth = tweepy.BasicAuthHandler("chuchiperriman", password)
    api = tweepy.API(auth, "identi.ca",api_root="/api")
    #api.update_status("Testing cloudsn with tweety")
    tweets = api.home_timeline()
    for tweet in tweets:
        print tweet.text
        
if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = images
import Image
import gtk

path = '/home/perriman/dev/cloud-services-notifications/data'

error = Image.open(path + '/error.png')
gmail = Image.open(path + '/twitter.png')
gmail.paste (error, (10,10), error)
gmail.save ('/tmp/aaa.png')


pixbuf = gtk.gdk.pixbuf_new_from_file(path + '/twitter.png')
pixbuf2 = gtk.gdk.pixbuf_new_from_file(path + '/error.png')
pixbuf2.composite(pixbuf, 10, 10, 22, 22, 10, 10, 1.0, 1.0, gtk.gdk.INTERP_HYPER, 220)

## now pixbuf2 contains the result of the compositing operation
pixbuf.save("/tmp/zbr.png", 'png')

########NEW FILE########
__FILENAME__ = indicator
from time import time
import indicate
import gtk

server = indicate.indicate_server_ref_default()
server.set_type("message.im")
#server.connect("server-display", self.on_server_display_cb)
server.set_desktop_file("/usr/local/share/applications/cloudsn.desktop")
server.show()


inds = []

for i in range(10):
    indicator = indicate.Indicator()
    indicator.set_property("name", "Test account")
    indicator.set_property_time("time", time())
    indicator.set_property_int("count", 0)
    """
    if acc.get_provider().get_icon() is not None:
        indicator.set_property_icon("icon", acc.get_provider().get_icon())
    """ 
    indicator.show()
    inds.append(indicator)


#acc.indicator = indicator
#indicator.account = acc

#indicator.connect("user-display", self.on_indicator_display_cb)

gtk.main()

########NEW FILE########
__FILENAME__ = notifications
import pynotify
if pynotify.init("Cloud Services Notifications"):
    n = pynotify.Notification("Cloudsn", "Mensaje de notificacion")
    n.set_urgency(pynotify.URGENCY_LOW)
    n.set_timeout(4000)
#    if icon:
#        n.set_icon_from_pixbuf(icon)
    n.show()
else:
    raise NotificationError ("there was a problem initializing the pynotify module")


########NEW FILE########
__FILENAME__ = poptest
import os, sys

srcpath = os.path.abspath("../src")
sys.path.insert(0,srcpath)

import poplib
from email.Parser import Parser as EmailParser
from email.header import decode_header
from cloudsn.core import utils

class PopBox:
    def __init__(self, user, password, host, port = 110, ssl = False):
        self.user = user
        self.password = password
        self.host = host
        self.port = int(port)
        self.ssl = ssl

        self.mbox = None
        self.parser = EmailParser()

    def __connect(self):
        if not self.ssl:
            self.mbox = poplib.POP3(self.host, self.port)
        else:
            self.mbox = poplib.POP3_SSL(self.host, self.port)

        self.mbox.user(self.user)
        self.mbox.pass_(self.password)

    def get_mails(self):
        self.__connect()

        messages = []
        print "Starting reading POP messages"
        msgs = self.mbox.list()[1]
        print "POP messages readed: %i" % (len(msgs))
        for msg in msgs:
            msgNum = int(msg.split(" ")[0])
            msgSize = int(msg.split(" ")[1])

            # retrieve only the header
            st = "\n".join(self.mbox.top(msgNum, 0)[1])
            print st
            print "----------------------------------------"
            msg = self.parser.parsestr(st, True) # header only
            sub = utils.mime_decode(msg.get("Subject"))
            msgid = msg.get("Message-Id")
            if not msgid:
                msgid = hash(msg.get("Received") + sub)
            fr = utils.mime_decode(msg.get("From"))
            messages.append( [msgid, sub, fr] )

        self.mbox.quit()
        return messages

def main():
    g = PopBox ("chuchiperriman@gmail.com", , 
            "pop.gmail.com", 995, True)
    mails = g.get_mails()
    for mail_id, sub, fr in mails:
        print mail_id, sub
        notifications[mail_id] = sub
        if mail_id not in account.notifications:
            n = Notification(mail_id, sub, fr)
            account.new_unread.append (n)
    account.notifications = notifications
        
if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = testcsv
import sys
import csv

FILE = "/tmp/sample.csv"

def main():
    
    feeds = dict()
    feeds['a'] = ('1','aaa')
    feeds['b'] = ('2','bbb')
    feeds['c'] = ('5','ccc')
    feeds['d'] = ('4','ddd')
    feeds['e'] = ('3','eee')
    
    """
    data = [
        ("And Now For Something Completely Different", 1971, "Ian MacNaughton"),
        ("Monty Python And The Holy Grail", 1975, "Terry Gilliam, Terry Jones"),
        ("Monty Python's Life Of Brian", 1979, "Terry Jones"),
        ("Monty Python Live At The Hollywood Bowl", 1982, "Terry Hughes"),
        ("Monty Python's The Meaning Of Life", 1983, "Terry Jones")
    ]
    """
    rows = sorted(feeds.values(), key=lambda x: x[0])
    print rows
    print rows[2:]
    return
    writer = csv.writer(open(FILE, "a+"), delimiter='\t')

    """
    for item in data:
        writer.writerow(item)
        
    writer.writerows(data)
    """
    writer.writerows(feeds.values())
        
    
    reader = csv.reader(open(FILE), delimiter='\t')

    for feed_id, feed_title in reader:
        print feed_id, feed_title

    name="Chuchi Perriman ()-@!$%&"
    print "-" + "".join([x for x in name if x.isalpha() or x.isdigit()]) + "-"
    
if __name__ == '__main__':
    sys.exit(main())

    

########NEW FILE########
__FILENAME__ = tumblr
import urllib2
import urllib
import xml.dom.minidom

params = {'email': 'chuchiperriman@gmail.com', 'password': ''}
params = urllib.urlencode(params)
f = urllib2.urlopen('http://www.tumblr.com/api/dashboard', params, 20)
data = f.read()
print data

feeds=list()

def processPost (post):
    post_type = post.getAttribute("type")
    
    if post_type == 'link':
        print "Post link:", post.getElementsByTagName("link-text")[0].childNodes[0].nodeValue
        print "Post link url:", post.getElementsByTagName("link-url")[0].childNodes[0].nodeValue
    
    """
	for c in ob.getElementsByTagName ("post"):
		if c.getAttribute("name") == "id":
			ftype, s, feed = c.childNodes[0].nodeValue.partition("/")
			self.feeds.append({"type" : ftype,
					   "feed" : feed})
			break

	for c in ob.getElementsByTagName ("number"):
		if c.getAttribute("name") == "count":
			self.feeds[-1]["count"] = c.childNodes[0].nodeValue
			break
    """
doc = xml.dom.minidom.parseString(data)
elist = doc.childNodes[0].getElementsByTagName("posts")[0]
print 'ues'
for post in elist.getElementsByTagName("post"):
	processPost (post)



########NEW FILE########
__FILENAME__ = twitteroauth
import os, sys

srcpath = os.path.abspath("../src")
sys.path.insert(0,srcpath)

import traceback, urllib2, httplib
import webbrowser
from cloudsn.providers import tweepy

CONSUMER_KEY = 'uRPdgq7wqkiKmWzs9rneJA'
CONSUMER_SECRET = 'ZwwhbUl2mwdreaiGFd8IqUhfsZignBJIYknVA867Ieg'

def main():
    #Ask for permissions and set the pin
    auth = tweepy.OAuthHandler(CONSUMER_KEY, CONSUMER_SECRET)
    auth_url = auth.get_authorization_url()
    print 'Please authorize in your browser'
    
    webbrowser.open(auth_url)
    verifier = raw_input('PIN: ').strip()
    auth.get_access_token(verifier)
    ACCESS_KEY = auth.access_token.key
    ACCESS_SECRET = auth.access_token.secret
    print "ACCESS_KEY: " + ACCESS_KEY
    print "ACCESS_SECRET: " + ACCESS_SECRET
    #Access to twitter with the access keys
    auth = tweepy.OAuthHandler(CONSUMER_KEY, CONSUMER_SECRET)
    auth.set_access_token(ACCESS_KEY, ACCESS_SECRET)
    api = tweepy.API(auth)
    #api.update_status("Testing cloudsn with tweety")
    public_tweets = api.public_timeline()
    for tweet in public_tweets:
        print tweet.text
        
if __name__ == '__main__':
    main()

########NEW FILE########
