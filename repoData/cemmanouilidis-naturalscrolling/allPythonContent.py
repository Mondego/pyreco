__FILENAME__ = indicator
### BEGIN LICENSE
# Copyright (C) 2011 Guillaume Hain <zedtux@zedroot.org>
#
# This program is free software: you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 3, as published
# by the Free Software Foundation
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranties of
# MERCHANTABILITY, SATISFACTORY QUALITY, or FITNESS FOR A PARTICULAR
# PURPOSE.  See the GNU General Public License for more details
#
# You should have received a copy of the GNU General Public License along
# with this program.  If not, see <http://www.gnu.org/licenses/>
### END LICENSE

import gtk
import appindicator

from naturalscrolling_lib import naturalscrollingconfig
from naturalscrolling_lib.gconfsettings import GConfSettings
from naturalscrolling_lib.udevobservator import UDevObservator
from naturalscrolling.indicatormenu import IndicatorMenu


class Indicator(object):
    # Singleton
    _instance = None
    _init_done = False

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(Indicator, cls).__new__(cls, *args,
                                                          **kwargs)
        return cls._instance

    def __init__(self):
        # Initialize a new AppIndicator
        self.indicator = appindicator.Indicator(
            "natural-scrolling-indicator",
            "natural-scrolling-status-not-activated",
            appindicator.CATEGORY_APPLICATION_STATUS)
        media_path = "%s/media/" % naturalscrollingconfig.get_data_path()
        self.indicator.set_icon_theme_path(media_path)
        self.indicator.set_attention_icon(
            "natural-scrolling-status-activated")

        menu = IndicatorMenu()
        self.indicator.set_menu(menu)

        # Initialize the UDev client
        udev_observator = UDevObservator()
        udev_observator.on_update_execute(menu.refresh)
        udev_observator.start()

        # Force the first refresh of the menu in order to populate it.
        menu.refresh(udev_observator.gather_devices())

        # When something change in GConf, push it to the Indicator menu
        # in order to update the status of the device as checked or unchecked
        GConfSettings().server().on_update_fire(menu.update_check_menu_item)

        # Initialize GConf in order to be up-to-date with existing devices
        GConfSettings().initialize(udev_observator.gather_devices())

    def status_attention(self):
        self.set_status(appindicator.STATUS_ATTENTION)

    def status_active(self):
        self.set_status(appindicator.STATUS_ACTIVE)

    def isreversed(self):
        return True

    def check_scrolling(self):
        if self.isreversed():
            self.indicator.set_status(appindicator.STATUS_ATTENTION)
        else:
            self.indicator.set_status(appindicator.STATUS_ACTIVE)
        return True

    def start(self):
        self.check_scrolling()
        try:
            gtk.main()
        except KeyboardInterrupt:
            pass

########NEW FILE########
__FILENAME__ = indicatormenu
# -*- coding: utf-8 -*-
### BEGIN LICENSE
# Copyright (C) 2011 Guillaume Hain <zedtux@zedroot.org>
#
# This program is free software: you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 3, as published
# by the Free Software Foundation
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranties of
# MERCHANTABILITY, SATISFACTORY QUALITY, or FITNESS FOR A PARTICULAR
# PURPOSE.  See the GNU General Public License for more details
#
# You should have received a copy of the GNU General Public License along
# with this program.  If not, see <http://www.gnu.org/licenses/>
### END LICENSE

import os
import gtk
import webbrowser
from naturalscrolling_lib.naturalscrollingconfig import *
from naturalscrolling_lib.gconfsettings import GConfSettings
from naturalscrolling.xinputwarper import XinputWarper


class IndicatorMenu(gtk.Menu):

    def __init__(self):
        gtk.Menu.__init__(self)

        # "Natural Scrolling" item is now dynamic.
        # Look at refresh() method
        self.__natural_scrolling = None

        self.append(self.new_separator())

        menu_sub = gtk.Menu()
        start_at_login = gtk.CheckMenuItem(_("Start at login"))
        if os.path.isfile(get_auto_start_file_path()):
            start_at_login.set_active(True)
        start_at_login.connect("activate", self.on_start_at_login_clicked)
        menu_sub.append(start_at_login)
        start_at_login.show()

        preferences = gtk.MenuItem(_("Preferences"))
        preferences.set_submenu(menu_sub)
        self.append(preferences)
        preferences.show()

        about = gtk.MenuItem(_("About"))
        about.connect("activate", self.on_about_clicked)
        self.append(about)
        about.show()

        self.append(self.new_separator())

        quit = gtk.MenuItem(_("Quit Natural Scrolling"))
        quit.connect("activate", self.on_quit_clicked)
        self.append(quit)
        quit.show()

        self.sync_checked_items_from_gconf()

        self.show()

    def new_separator(self):
        seperator = gtk.SeparatorMenuItem()
        seperator.show()
        return seperator

    def sync_checked_items_from_gconf(self):
        """
        Check all gtk.CheckMenuItem depending on GConf keys values
        """
        for xid in GConfSettings().activated_devices_xids():
            self.update_check_menu_item(xid, True)

    def refresh(self, devices):
        """
        Fire this method with the list of devices to display in order to
        refresh the menu.
        If there is only one device, the "Natural scrolling" menu item will be
        a gtk.CheckMenuItem, but if there are more than one devcice, then
        "Natural scrolling" menu item will be a gtk.Menu of gtk.CheckMenuItem
        per device.
        """
        if self.__natural_scrolling:
            self.remove(self.__natural_scrolling)
            self.__natural_scrolling = None

        if len(devices) == 1:
            self.__natural_scrolling = gtk.CheckMenuItem("Natural Scrolling")
            self.__natural_scrolling.set_tooltip_text(devices[0].keys()[0])
            self.__natural_scrolling.connect("toggled",
                self.on_natural_scrolling_toggled)
            self.__natural_scrolling.show()
        else:
            self.__natural_scrolling = gtk.MenuItem("Natural Scrolling")
            self.__natural_scrolling.show()
            devices_menu = gtk.Menu()
            for device in devices:
                sub_item = gtk.CheckMenuItem(device.values()[0])
                sub_item.set_tooltip_text(device.keys()[0])
                devices_menu.append(sub_item)
                sub_item.connect("toggled", self.on_natural_scrolling_toggled)
                sub_item.show()

            self.__natural_scrolling.set_submenu(devices_menu)

        self.insert(self.__natural_scrolling, 0)

        self.sync_checked_items_from_gconf()

    def on_quit_clicked(self, widget):
        gtk.main_quit()

    def on_natural_scrolling_toggled(self, widget, data=None):
        """
        Fired method when user click on gtk.CheckMenuItem 'Natural Scrolling'
        """
        enabled = widget.get_active()
        natural_scrolling_or_device_name = widget.get_label()

        # When there is only one detected device
        # the label of the gtk.CheckMenuItem is "Natural Scrolling"
        if natural_scrolling_or_device_name == "Natural Scrolling":
            # So the device XID is the id of the first device
            device_xid = XinputWarper().first_xid()
        else:
            device_xid = XinputWarper().find_xid_by_name(widget.get_label())

        GConfSettings().key(device_xid).set_value(enabled)

    def update_check_menu_item(self, xid, enabled):
        """
        Retreive the gtk.CheckMenuItem with the text and set the value
        """
        if not self.__natural_scrolling:
            return

        submenu = self.__natural_scrolling.get_submenu()
        if submenu:
            for widget in self.__natural_scrolling.get_submenu():
                if widget.get_tooltip_text() == xid:
                    widget.set_active(enabled)
        else:
            self.__natural_scrolling.set_active(enabled)

    def on_start_at_login_clicked(self, widget, data=None):
        """
        Fired method when user click on gtk.CheckMenuItem 'Start at login'
        """
        if not os.path.exists(get_auto_start_path()):
            os.makedirs(get_auto_start_path())

        auto_start_file_exists = os.path.isfile(get_auto_start_file_path())
        if widget.get_active():
            if not auto_start_file_exists:
                source = open(get_auto_start_from_data_file_path(), "r")
                destination = open(get_auto_start_file_path(), "w")
                destination.write(source.read())
                destination.close() and source.close()
        else:
            if auto_start_file_exists:
                os.remove(get_auto_start_file_path())

    def click_website(self, dialog, link):
        webbrowser.open(link)

    def on_about_clicked(self, widget, data=None):
        gtk.about_dialog_set_url_hook(self.click_website)

        app_name = "Natural Scrolling"
        about = gtk.AboutDialog()
        about.set_name(app_name)
        about.set_version(appliation_version())
        about.set_icon(
            gtk.gdk.pixbuf_new_from_file(get_data_path() +
                                         "/media/naturalscrolling.svg"))
        about.set_logo(
            gtk.gdk.pixbuf_new_from_file(get_data_path() +
                                         "/media/naturalscrolling.svg"))
        about.set_website(appliation_website())
        about.set_website_label("%s Website" % app_name)
        about.set_authors(["Charalampos Emmanouilidis <chrys.emmanouilidis@mail.com>",
                           "Guillaume Hain <zedtux@zedroot.org>"])
        about.set_copyright("Copyright © 2011 Charalampos Emmanouilidis")
        about.set_wrap_license(True)
        about.set_license(("%s is free software; you can redistribute it "
            "and/or modify it under the terms of the GNU General "
            "Public License as published by the Free Software Foundation; "
            "either version 3 of the License, or (at your option) any later "
            "version.\n\n%s is distributed in the hope that it will be "
            "useful, but WITHOUT ANY WARRANTY; without even the implied "
            "warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE."
            "  See the GNU General Public License for more details.\n\n"
            "You should have received a copy of the GNU General Public "
            "License along with %s; if not, write to the Free Software "
            "Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, "
            "MA 02110-1301, USA") % (app_name, app_name, app_name))
        about.run()
        about.destroy()

########NEW FILE########
__FILENAME__ = xinputwarper
# -*- coding: utf-8 -*-
### BEGIN LICENSE
# Copyright (C) 2011 Guillaume Hain <zedtux@zedroot.org>
#
# This program is free software: you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 3, as published
# by the Free Software Foundation
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranties of
# MERCHANTABILITY, SATISFACTORY QUALITY, or FITNESS FOR A PARTICULAR
# PURPOSE.  See the GNU General Public License for more details
#
# You should have received a copy of the GNU General Public License along
# with this program.  If not, see <http://www.gnu.org/licenses/>
### END LICENSE

import os
import re


class XinputWarper(object):
    # Singleton
    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(XinputWarper, cls).__new__(cls, *args,
                                                                 **kwargs)
            cls._instance.__xinput_list_pattern = re.compile(
                r'\s+([A-z0-9\s\-\(\)\/\.\:\'®]+)\s+id=(\d+)\s+\[slave\s+pointer.*\]')
            cls._instance.__xinput_list = None
        return cls._instance

    def get_xinput_list(self):
        return self.__xinput_list
    xinput_list = property(get_xinput_list)

    def enable_natural_scrolling(self, devise_xid, enabled):
        """
        Global method to apply or not Natural Scrolling
        """
        map = os.popen("xinput get-button-map \"%s\"" %
                       devise_xid).read().strip()

        if enabled == True:
            map = map.replace("4 5", "5 4")
            map = map.replace("6 7", "7 6")
        else:
            map = map.replace("5 4", "4 5")
            map = map.replace("7 6", "6 7")

        os.system("xinput set-button-map \"%s\" %s" % (devise_xid, map))

    def find_xid_by_name(self, name):
        """
        Extract from the xinput list the id of the given device name
        """
        xinput_list = self._xinput_list(name)
        for device_info in self.__xinput_list_pattern.findall(xinput_list):
            if device_info[0].strip() == name:
                return device_info[1]
        return None

    def first_xid(self):
        """
        Extract from the xinput list the id of the first detected device
        """
        xinput_list = self._xinput_list()
        return self.__xinput_list_pattern.findall(xinput_list)[0][1]

    def reset_cache(self):
        """
        Clear xinput cache in order to force refresh
        """
        self.__xinput_list = None

    def _xinput_list(self, name=None):
        """
        Refresh cache and/or search in cached xinput list
        """
        if not self.__xinput_list:
            self.__xinput_list = os.popen(("xinput list | grep -v 'XTEST' "
                                           "| grep -v '\[master '")).read()

        if name:
            res = re.search(r'(.*%s.*)' % re.escape(name), self.__xinput_list)
            if res:
                return res.group(1)
        return self.__xinput_list

########NEW FILE########
__FILENAME__ = debugger
import pyudev
from naturalscrolling_lib.udevobservator import UDevObservator
from naturalscrolling.xinputwarper import XinputWarper
from naturalscrolling_lib.gconfsettings import GConfSettings, GConfKey


class Debugger(object):

    def execute(self):
        print " * PyUDev\n"
        print "\n\tInput devices:\n\t=============="
        devices = pyudev.Context().list_devices(subsystem="input")
        for device in devices:
            if device.sys_name.startswith("event"):
                print "\t\t", device.sys_name, device.parent["NAME"][1:-1]

        print "\n\tInput devices keys:\n\t=============="
        for device in devices:
            device_keys = ""
            if device.sys_name.startswith("event"):
                if device.parent.keys():
                    for key in device.parent.keys():
                        device_keys += "{%s: %s}," % (key, device.parent[key])
                    print "%s => %s" % (device.sys_name, device_keys)

        print "\n\n * XinputWarper\n"
        print "\t- First XID: %s\n" % XinputWarper().first_xid()

        print "\t- Devices:\n\t=========="
        devices = UDevObservator().gather_devices()
        print "\n\t%d device(s) found\n" % len(devices)
        for device in devices:
            print "\t\tDevice \"%s\" has XID %s" % (device.values()[0],
                                                device.keys()[0])

        print "\n\t- Xinput list:\n\t=========="
        for xinput in XinputWarper().xinput_list.split("\n"):
            print "\t\t", xinput

        print "\n\n * GConfSettings\n"
        print "\t- All Keys:\n\t==========="
        for entry in GConfSettings().keys():
            gconf_key = GConfKey(entry.key, entry.value.type)
            print "\t\tKey \"%s\" has value \"%s\"" % (gconf_key.name,
                                                   gconf_key.get_value())

########NEW FILE########
__FILENAME__ = gconfsettings
### BEGIN LICENSE
# Copyright (C) 2011 Guillaume Hain <zedtux@zedroot.org>
#
# This program is free software: you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 3, as published
# by the Free Software Foundation
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranties of
# MERCHANTABILITY, SATISFACTORY QUALITY, or FITNESS FOR A PARTICULAR
# PURPOSE.  See the GNU General Public License for more details
#
# You should have received a copy of the GNU General Public License along
# with this program.  If not, see <http://www.gnu.org/licenses/>
### END LICENSE

import re
import gconf

## GConf setup

# GConf root path
GCONF_ROOT_DIR = "/apps/naturalscrolling"


class InvalidKey(Exception):
    """ Raised class when key is unknown """


class InvalidKeyType(Exception):
    """ Raised class when key type is unknown """


class GConfServer(object):
    # Singleton
    _instance = None
    _init_done = False

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(GConfServer, cls).__new__(cls, *args,
                                                                 **kwargs)
        return cls._instance

    def __init__(self):
        """
        Open connection to GConf
        and connect to callback on naturalscrolling keys updates
        """
        if self._init_done:
            return

        if not hasattr(self, "__key_update_observators"):
            self.__key_update_observators = {}

        if not hasattr(self, "__keys_update_observators"):
            self.__keys_update_observators = []

        if not hasattr(self, "client"):
            # Get GConf client:
            self.client = gconf.client_get_default()

            # Add the root directory to the list of directories that our GConf
            # client will watch for changes:
            self.client.add_dir(GCONF_ROOT_DIR, gconf.CLIENT_PRELOAD_NONE)

            # Assign a callback function for when changes are made to keys in
            # the root directory namespace:
            self.client.notify_add(GCONF_ROOT_DIR, self.on_settings_changed)

        self._init_done = True

    def fire_me_when_update_on_key(self, key, method):
        """
        Register a Class instance method to fire
        swhen the given an update on the given key have been catched
        """
        self.__key_update_observators[key] = method

    def on_update_fire(self, method):
        """
        Register method to fire when a key of the GConf root path
        has been updated
        """
        self.__keys_update_observators.append(method)

    def on_settings_changed(self, client, timestamp, entry, *extra):
        """
        This is the callback function that is called when the keys in our
        namespace change (such as editing them with gconf-editor).
        """
        # Do nothing when the key has been removed
        if not entry.value:
            return

        key = entry.key
        gconf_key = GConfKey(key, entry.value.type)
        self.execute_callback_on_observers(key, gconf_key)

    def execute_callback_on_observers(self, key, gconf_key):
        if key in self.__key_update_observators:
            # Execute observer's method passing GConf key value as parameter
            self.__key_update_observators[key](gconf_key.get_value())

        if self.__keys_update_observators:
            for observator in self.__keys_update_observators:
                observator(gconf_key.name, gconf_key.get_value())

    def entries(self):
        """
        Return a list of all entries from naturalscrolling root path
        """
        return self.client.all_entries("/apps/naturalscrolling")


class GConfKey(object):

    class KeyDoesntExits(Exception):
        pass

    def __init__(self, key, type=None):
        self.__gconf = GConfServer().client
        self.__value = None

        if key.startswith(GCONF_ROOT_DIR):
            self.__key = key
            self.__name = self._without_root_path(key)
        else:
            self.__key = self._with_root_path(key)
            self.__name = key

        if type:
            self.__type = type
        else:
            try:
                self.__type = self.__gconf.get(self.__key).type
            except AttributeError:
                raise GConfKey.KeyDoesntExits(_("Can't find the key '%s'") %
                                              self.__key)

    def get_name(self):
        return self.__name
    name = property(get_name)

    def _without_root_path(self, key):
        return re.sub("%s/" % GCONF_ROOT_DIR, "", key)

    def _with_root_path(self, key):
        return "%s/%s" % (GCONF_ROOT_DIR, key)

    def get_value(self):
        """
        Magic method to read the value from GConf (auto cast)
        """
        if self.__type == gconf.VALUE_BOOL:
            return self.__gconf.get_bool(self.__key)
        elif self.__type == gconf.VALUE_STRING:
            return self.__gconf.get_string(self.__key)
        elif self.__type == gconf.VALUE_INT:
            return self.__gconf.get_int(self.__key)
        else:
            raise InvalidKeyType(_("Can't read the value for type '%s'") %
                                 self.__type)

    def set_value(self, value):
        """
        Magic method to write the value to GConf (auto cast)
        """
        if self.__type == gconf.VALUE_BOOL:
            self.__gconf.set_bool(self.__key, value)
        elif self.__type == gconf.VALUE_STRING:
            self.__gconf.set_string(self.__key, value)
        elif self.__type == gconf.VALUE_INT:
            self.__gconf.set_int(self.__key, value)
        else:
            raise InvalidKeyType(_("Can't write the value '%s'"
                                   " for type '%s'") % (value, self.__type))

    def is_enable(self):
        return self.__value == True

    def enable(self):
        """
        Set a boolean key value to True
        """
        self.__value = 1
        self.set_value()

    def disable(self):
        """
        Set a boolean key value to False
        """
        self.__value = 0
        self.set_value()

    def find_or_create(self):
        """
        Check if the current instance of GConfKey exists otherwise create it
        """
        if not self.__gconf.get(self.__key):
            self.set_value(False)

    def remove(self):
        """ Remove the key from GConf """
        self.__gconf.unset(self.__key)


class GConfSettings(object):

    def server(self):
        """
        Return the Singleton instance of the GConfServer
        """
        return GConfServer()

    def initialize(self, devices):
        """
        Check if all keys exists
        Create missing keys
        """
        for device in devices:
            if not device.keys()[0]:
                print (_("Warning: The XID of the device with name %s "
                       "wasn't found") % device.values()[0])
            else:
                gconf_key = GConfKey(device.keys()[0], gconf.VALUE_BOOL)
                gconf_key.find_or_create()

                # As you're in the initializing step, if there is at least one
                # observator, then fire it with all the actual configuration
                self.server().execute_callback_on_observers(device.keys()[0],
                                                            gconf_key)

    def key(self, key, type=None):
        """
        Ruby styled method to define which is the key to check
        This method return an instance of the GConfKey class
        otherwise raise a InvalidKey or InvalidKeyType
        """
        return GConfKey(key, self.python_type_to_gconf_type(type))

    def python_type_to_gconf_type(self, type):
        """
        Convert a Python type (bool, int, str, ...) to GConf type
        """
        if type == bool:
            return gconf.VALUE_BOOL
        elif type == str:
            return gconf.VALUE_STRING
        elif type == int:
            return gconf.VALUE_INT

    def keys(self):
        """
        Return a list of all keys for natural scrolling
        """
        return GConfServer().client.all_entries(GCONF_ROOT_DIR)

    def activated_devices_xids(self):
        """
        Return a list of all XIDs of devices where naturalscrolling was
        registered as activated.
        """
        activated_devices_xids = []
        for entry in self.server().entries():
            try:
                gconf_key = GConfKey(entry.key)
                if gconf_key.get_value():
                    activated_devices_xids.append(gconf_key.name)
            except GConfKey.KeyDoesntExits:
                # Pass the removed key
                pass
        return activated_devices_xids

########NEW FILE########
__FILENAME__ = naturalscrollingconfig
# -*- Mode: Python; coding: utf-8; indent-tabs-mode: nil; tab-width: 4 -*-
### BEGIN LICENSE
# Copyright (C) 2011 Charalampos Emmanouilidis,
# Charalampos Emmanouilidis <chrys.emmanouilidis@gmail.com>
#
# This program is free software: you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 3, as published
# by the Free Software Foundation
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranties of
# MERCHANTABILITY, SATISFACTORY QUALITY, or FITNESS FOR A PARTICULAR
# PURPOSE.  See the GNU General Public License for more details
#
# You should have received a copy of the GNU General Public License along
# with this program.  If not, see <http://www.gnu.org/licenses/>
### END LICENSE

# THIS IS Naturalscrolling CONFIGURATION FILE
# YOU CAN PUT THERE SOME GLOBAL VALUE
# Do not touch unless you know what you're doing.
# you're warned :)
import os


__all__ = [
    "appliation_version",
    "appliation_website",
    "get_data_file",
    "get_data_path",
    "get_locale_path",
    "get_auto_start_path",
    "get_auto_start_file_name",
    "get_auto_start_file_path",
    "get_auto_start_from_data_file_path"]

# Where your project will look for your data (for instance, images and ui
# files). By default, this is ../, relative your trunk layout
__naturalscrolling_data_directory__ = "../"
# Where your project will look for translation catalogs
__naturalscrolling_locale_directory__ = "../locales"
__version__ = "VERSION"
__website__ = "https://github.com/cemmanouilidis/naturalscrolling"


class project_path_not_found(Exception):
    """Raised when we can't find the project directory."""


def appliation_version():
    return __version__


def appliation_website():
    return __website__


def get_data_file(*path_segments):
    """Get the full path to a data file.

    Returns the path to a file underneath the data directory (as defined by
    `get_data_path`). Equivalent to os.path.join(get_data_path(),
    *path_segments).
    """
    return os.path.join(get_data_path(), *path_segments)


def get_data_path():
    """Retrieve naturalscrolling data path

    This path is by default <naturalscrolling_lib_path>/../ in trunk
    and /usr/share/naturalscrolling in an installed version but this path
    is specified at installation time.
    """

    # Get pathname absolute or relative.
    path = os.path.join(
        os.path.dirname(__file__), __naturalscrolling_data_directory__)

    abs_data_path = os.path.abspath(path)
    if not os.path.exists(abs_data_path):
        print "ERROR: Unable to access the project path: %s" % abs_data_path
        raise project_path_not_found

    return abs_data_path


def get_locale_path():
    """Retrieve naturalscrolling locale path

    This path is by default <naturalscrolling_lib_path>/../locales in trunk
    and /usr/share/locale in an installed version but this path
    is specified at installation time.
    """

    # Get pathname absolute or relative.
    path = os.path.join(
        os.path.dirname(__file__), __naturalscrolling_locale_directory__)

    return os.path.abspath(path)


def get_auto_start_path():
    """ Retrieve the autostart folder from user's HOME folder """
    return os.getenv("HOME") + "/.config/autostart/"


def get_auto_start_file_name():
    """ Return the autostart file for naturalscrolling """
    return "naturalscrolling.desktop"


def get_auto_start_from_data_file_path():
    """
    Return the full path of the autostart file for naturalscrolling

    The path is hardcoded as it can't be anything else.
    """
    return "/usr/share/applications/" + get_auto_start_file_name()


def get_auto_start_file_path():
    """ Return the full path of the autostart file for naturalscrolling """
    return get_auto_start_path() + "/" + get_auto_start_file_name()

########NEW FILE########
__FILENAME__ = udevobservator
### BEGIN LICENSE
# Copyright (C) 2011 Guillaume Hain <zedtux@zedroot.org>
#
# This program is free software: you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 3, as published
# by the Free Software Foundation
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranties of
# MERCHANTABILITY, SATISFACTORY QUALITY, or FITNESS FOR A PARTICULAR
# PURPOSE.  See the GNU General Public License for more details
#
# You should have received a copy of the GNU General Public License along
# with this program.  If not, see <http://www.gnu.org/licenses/>
### END LICENSE

import pyudev
from pyudev.glib import GUDevMonitorObserver
from naturalscrolling.xinputwarper import XinputWarper
from naturalscrolling_lib.gconfsettings import GConfSettings


class UDevObservator(object):

    def __init__(self):
        self.__observator = None

    def start(self):
        """ Observe added and removed events """
        monitor = pyudev.Monitor.from_netlink(pyudev.Context())
        monitor.filter_by(subsystem="input")
        observer = GUDevMonitorObserver(monitor)
        observer.connect("device-added", self.on_device_added)
        observer.connect("device-removed", self.on_device_removed)
        monitor.enable_receiving()

    def on_update_execute(self, callback):
        """ Define the observator of add and change signals """
        self.__observator = callback

    def gather_devices_names_with_xid(self):
        """ Gather and return all devices names """
        devices_names = []
        devices = pyudev.Context().list_devices(subsystem="input").__iter__()
        while True:
            try:
                device = devices.next()
                if device.sys_name.startswith("event"):
                    try:
                        device_name = device.parent["NAME"][1:-1]
                        if XinputWarper().find_xid_by_name(device_name):
                            # [1:-1] means remove double quotes
                            # at the begining and at the end
                            devices_names.append(device_name)
                    except KeyError:
                        print (_("Warning: The device parent with sys_name %s"
                               " doesn't have a NAME key.") % device.sys_name)
            except pyudev.DeviceNotFoundAtPathError:
                # next() raise this exception when we try to open a removed
                # device
                pass
            except StopIteration:
                break

        return devices_names

    def gather_devices(self):
        """ Gather and return all devices (name and XID) """
        devices = []
        for device_name in self.gather_devices_names_with_xid():
            devices.append(
                {XinputWarper().find_xid_by_name(device_name): device_name})
        return devices

    # ~~~~ Callback methods ~~~~
    def on_device_added(self, observer, device):
        """
        Fired method when a new device is added to udev
            - Create key in GConf for this new device
            - Apply natural scrolling if was enabled [issue #37]
            - Call back observators
        """
        if device.sys_name.startswith("event"):
            XinputWarper().reset_cache()
            xid = XinputWarper().find_xid_by_name(device.parent["NAME"][1:-1])
            # Continue only when an XID has been found (issue #41)
            if xid:
                # Register the device (create it if needed)
                gconf_key = GConfSettings().key(xid, bool)
                gconf_key.find_or_create()
                # Apply Natural scrolling if was enabled previously
                XinputWarper().enable_natural_scrolling(xid, gconf_key.get_value())

                self.__observator(self.gather_devices())

    def on_device_removed(self, observer, device):
        """
        Fired method when a device is removed from udev
            - Delete key from GConf of the device
            - Call back observators
        """
        if device.sys_name.startswith("event"):
            try:
                device_name = device.parent["NAME"][1:-1]
                xid = XinputWarper().find_xid_by_name(device_name)
                # Continue only when an XID has been found (issue #41)
                if xid:
                    GConfSettings().key(xid).remove()
            except KeyError:
                print (_("Warning: The device parent with sys_name %s doesn't"
                       " have a NAME key.") % device.sys_name)
            XinputWarper().reset_cache()

        self.__observator(self.gather_devices())

########NEW FILE########
