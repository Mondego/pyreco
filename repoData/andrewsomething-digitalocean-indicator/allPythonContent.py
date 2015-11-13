__FILENAME__ = DoIndicator
# -*- Mode: Python; coding: utf-8; indent-tabs-mode: nil; tab-width: 4 -*-
### BEGIN LICENSE
# This program is free software: you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 3, as published
# by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranties of
# MERCHANTABILITY, SATISFACTORY QUALITY, or FITNESS FOR A PARTICULAR
# PURPOSE.  See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program.  If not, see <http://www.gnu.org/licenses/>.
### END LICENSE

import os
import time
import digitalocean

from gi.repository import Gtk, GLib, Gio, Gdk  # pylint: disable=E0611
from gi.repository import AppIndicator3  # pylint: disable=E0611
from gi.repository import Notify

from digitalocean_indicator.DoPreferencesDialog import DoPreferencesDialog
from digitalocean_indicator_lib.helpers import get_media_file

import gettext
from gettext import gettext as _
gettext.textdomain('digitalocean-indicator')


class Indicator:
    def __init__(self):
        self.indicator = AppIndicator3.Indicator.new('digitalocean-indicator',
                         '',
                         AppIndicator3.IndicatorCategory.APPLICATION_STATUS)
        self.indicator.set_status(AppIndicator3.IndicatorStatus.ACTIVE)
        icon_uri = get_media_file("digitalocean-indicator.svg")
        icon_path = icon_uri.replace("file:///", '')
        self.indicator.set_icon(icon_path)

        Notify.init('DigitalOcean Indicator')

        self.PreferencesDialog = DoPreferencesDialog
        self.settings = Gio.Settings(
            "com.andrewsomething.digitalocean-indicator")
        self.settings.connect('changed', self.on_preferences_changed)
        self.preferences_dialog = None
        self.preferences_changed = False

        # If the key/id aren't set, take them from the environment.
        self.do_api_key = self.settings.get_string("do-api-key")
        if not self.do_api_key:
            try:
                self.settings.set_string("do-api-key",
                                         os.environ["DO_API_KEY"])
            except KeyError:
                pass

        self.do_client_id = self.settings.get_string("do-client-id")
        if not self.do_client_id:
            try:
                self.settings.set_string("do-client-id",
                                         os.environ["DO_CLIENT_ID"])
            except KeyError:
                pass

        self.menu = Gtk.Menu()

        # Add items to Menu and connect signals.
        self.build_menu()
        # Refresh menu every 10 min by default
        self.change_timeout = False
        self.interval = self.settings.get_int("refresh-interval")
        GLib.timeout_add_seconds(self.interval*60, self.timeout_set)

    def build_menu(self):
        self.add_droplets()

        self.seperator = Gtk.SeparatorMenuItem.new()
        self.seperator.show()
        self.menu.append(self.seperator)

        self.preferences = Gtk.MenuItem("Preferences")
        self.preferences.connect("activate", self.on_preferences_activate)
        self.preferences.show()
        self.menu.append(self.preferences)

        self.quit = Gtk.MenuItem("Refresh")
        self.quit.connect("activate", self.on_refresh_activate)
        self.quit.show()
        self.menu.append(self.quit)

        self.quit = Gtk.MenuItem("Quit")
        self.quit.connect("activate", self.on_exit_activate)
        self.quit.show()
        self.menu.append(self.quit)

        self.menu.show()
        self.indicator.set_menu(self.menu)

    def add_droplets(self):
        try:
            manager = digitalocean.Manager(client_id=self.do_client_id,
                                           api_key=self.do_api_key)
            my_droplets = manager.get_all_droplets()
            for droplet in my_droplets:
                droplet_item = Gtk.ImageMenuItem.new_with_label(droplet.name)
                droplet_item.set_always_show_image(True)
                if droplet.status == "active":
                    img = Gtk.Image.new_from_icon_name("gtk-ok",
                                                       Gtk.IconSize.MENU)
                    droplet_item.set_image(img)
                else:
                    img = Gtk.Image.new_from_icon_name("gtk-stop",
                                                       Gtk.IconSize.MENU)
                    droplet_item.set_image(img)
                droplet_item.show()
                sub_menu = Gtk.Menu.new()

                ip = Gtk.MenuItem.new()
                ip.set_label(_("IP: ") + str(droplet.ip_address))
                ip.connect('activate', self.on_ip_clicked)
                ip.show()
                sub_menu.append(ip)

                images = manager.get_all_images()
                for i in images:
                    if i.id == droplet.image_id:
                        image = i.name
                        image_id = Gtk.MenuItem.new()
                        image_id.set_label(_("Type: ") + image)
                        image_id.show()
                        sub_menu.append(image_id)
                        break

                regions = manager.get_all_regions()
                for r in regions:
                    if r.id == droplet.region_id:
                        region = r.name
                        region_id = Gtk.MenuItem.new()
                        region_id.set_label(_("Region: ") + region)
                        region_id.show()
                        sub_menu.append(region_id)
                        break

                sizes = manager.get_all_sizes()
                for s in sizes:
                    if s.id == droplet.size_id:
                        size = s.name
                        size_id = Gtk.MenuItem.new()
                        size_id.set_label(_("Size: ") + size)
                        size_id.show()
                        sub_menu.append(size_id)
                        break

                seperator = Gtk.SeparatorMenuItem.new()
                seperator.show()
                sub_menu.append(seperator)

                web = Gtk.MenuItem.new()
                web.set_label(_("View on web..."))
                droplet_url = "https://cloud.digitalocean.com/droplets/%s" % droplet.id
                web.connect('activate', self.open_web_link, droplet_url)
                web.show()
                sub_menu.append(web)

                if droplet.status == "active":
                    power_off = Gtk.ImageMenuItem.new_with_label(
                        _("Power off..."))
                    power_off.set_always_show_image(True)
                    img = Gtk.Image.new_from_icon_name("system-shutdown",
                                                       Gtk.IconSize.MENU)
                    power_off.set_image(img)
                    power_off.connect('activate',
                                      self.on_power_toggled,
                                      droplet,
                                      'off')
                    power_off.show()
                    sub_menu.append(power_off)

                    reboot = Gtk.ImageMenuItem.new_with_label(_("Reboot..."))
                    reboot.set_always_show_image(True)
                    img = Gtk.Image.new_from_icon_name("system-reboot",
                                                       Gtk.IconSize.MENU)
                    reboot.set_image(img)
                    reboot.connect('activate',
                                   self.on_power_toggled,
                                   droplet,
                                   'reboot')
                    reboot.show()
                    sub_menu.append(reboot)

                else:
                    power_on = Gtk.ImageMenuItem.new_with_label(
                        _("Power on..."))
                    power_on.set_always_show_image(True)
                    img = Gtk.Image.new_from_icon_name("gtk-ok",
                                                       Gtk.IconSize.MENU)
                    power_on.set_image(img)
                    power_on.connect('activate',
                                     self.on_power_toggled,
                                     droplet,
                                     'on')
                    power_on.show()
                    sub_menu.append(power_on)

                sub_menu.show()
                droplet_item.set_submenu(sub_menu)
                self.menu.append(droplet_item)
        except Exception, e:
            if e.message:
                print("Error: ", e.message)
            if "Access Denied" in e.message:
                error_indicator = Gtk.ImageMenuItem.new_with_label(
                    _("Error logging in. Please check your credentials."))
            else:
                error_indicator = Gtk.ImageMenuItem.new_with_label(
                    _("No network connection."))
            img = Gtk.Image.new_from_icon_name("error", Gtk.IconSize.MENU)
            error_indicator.set_always_show_image(True)
            error_indicator.set_image(img)
            error_indicator.show()
            self.menu.append(error_indicator)

    def timeout_set(self):
        self.rebuild_menu()
        if self.change_timeout:
            GLib.timeout_add_seconds(self.interval*60, self.timeout_set)
            return False
        return True

    def on_ip_clicked(self, widget):
        address = widget.get_label().replace("IP: ", '')
        clipboard = Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD)
        clipboard.set_text(address, -1)
        message = 'IP address %s copied to clipboard' % address
        notification = Notify.Notification.new(
            'DigitalOcean Indicator',
            message,
            'digitalocean-indicator'
        )
        notification.show()

    def open_web_link(self, widget, url):
        Gtk.show_uri(None, url, Gdk.CURRENT_TIME)

    def on_power_toggled(self, widget, droplet, action):
        if action is "on":
            droplet.power_on()
        elif action is "reboot":
            droplet.reboot()
        else:
            droplet.power_off()
        events = droplet.get_events()
        loading = True
        while loading:
            for event in events:
                event.load()
                try:
                    if int(event.percentage) < 100:
                        time.sleep(2)
                    else:
                        loading = False
                        break
                except TypeError:  # Not yet reporting any percentage
                    pass
        self.rebuild_menu()

    def on_preferences_changed(self, settings, key, data=None):
        if key == "refresh-interval":
            self.change_timeout = True
            self.interval = settings.get_int(key)
            GLib.timeout_add_seconds(self.interval*60, self.timeout_set)
        else:
            self.preferences_changed = True

    def on_preferences_activate(self, widget):
        """Display the preferences window for digitalocean-indicator."""
        if self.preferences_dialog is None:
            self.preferences_dialog = self.PreferencesDialog()  # pylint: disable=E1102
            self.preferences_dialog.connect('destroy',
                                            self.on_preferences_dialog_destroyed)
            self.preferences_dialog.show()
        if self.preferences_dialog is not None:
            self.preferences_dialog.present()

    def on_refresh_activate(self, widget):
        self.rebuild_menu()

    def rebuild_menu(self):
        for i in self.menu.get_children():
            self.menu.remove(i)
        self.build_menu()
        return True

    def on_preferences_dialog_destroyed(self, widget, data=None):
        self.preferences_dialog = None
        if self.preferences_changed is True:
            self.do_api_key = self.settings.get_string("do-api-key")
            self.do_client_id = self.settings.get_string("do-client-id")
            self.rebuild_menu()
        self.preferences_changed = False

    def on_exit_activate(self, widget):
        self.on_destroy(widget)

    def on_destroy(self, widget, data=None):
        Gtk.main_quit()

########NEW FILE########
__FILENAME__ = DoPreferencesDialog
# -*- Mode: Python; coding: utf-8; indent-tabs-mode: nil; tab-width: 4 -*-
### BEGIN LICENSE
# This program is free software: you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 3, as published
# by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranties of
# MERCHANTABILITY, SATISFACTORY QUALITY, or FITNESS FOR A PARTICULAR
# PURPOSE.  See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along
# with this program.  If not, see <http://www.gnu.org/licenses/>.
### END LICENSE

# This is your preferences dialog.
#
# Define your preferences in
# data/glib-2.0/schemas/net.launchpad.digitalocean-indicator.gschema.xml
# See http://developer.gnome.org/gio/stable/GSettings.html for more info.

from gi.repository import GLib, Gio  # pylint: disable=E0611

from locale import gettext as _

import os
import logging
logger = logging.getLogger('digitalocean_indicator')

from digitalocean_indicator_lib.PreferencesDialog import PreferencesDialog
from digitalocean_indicator_lib.helpers import get_media_file

autostart_dir = os.path.join(GLib.get_user_config_dir(), "autostart/")
autostart_template = "digitalocean-indicator-autostart.desktop"
autostart_file = get_media_file(autostart_template)
autostart_file = autostart_file.replace("file:///", '')
installed_file = os.path.join(autostart_dir, autostart_template)


class DoPreferencesDialog(PreferencesDialog):
    __gtype_name__ = "PreferencesDigitaloceanIndicatorDialog"

    def finish_initializing(self, builder):  # pylint: disable=E1002
        """Set up the preferences dialog"""
        super(DoPreferencesDialog, self).finish_initializing(builder)

        # Bind each preference widget to gsettings
        settings = Gio.Settings("com.andrewsomething.digitalocean-indicator")
        do_api_key = self.builder.get_object('do_api_key_entry')
        settings.bind("do-api-key", do_api_key,
                      "text", Gio.SettingsBindFlags.DEFAULT)
        do_client_id = self.builder.get_object('do_client_id_entry')
        settings.bind("do-client-id", do_client_id,
                      "text", Gio.SettingsBindFlags.DEFAULT)
        refresh_interval = self.builder.get_object('refresh_interval_spin')
        settings.bind("refresh-interval", refresh_interval,
                      "value", Gio.SettingsBindFlags.DEFAULT)

        self.autostart_switch = builder.get_object("autostart_switch")
        if os.path.isfile(installed_file):
            self.autostart_switch.set_active(True)
        self.autostart_switch.connect('notify::active',
                                      self.on_autostart_switch_activate)

    def on_autostart_switch_activate(self, widget, data=None):
        if self.autostart_switch.get_active():
            if not os.path.exists(autostart_dir):
                os.mkdir(autostart_dir)
            if os.path.isdir(autostart_dir):
                os.symlink(autostart_file, installed_file)
        else:
            os.unlink(installed_file)

########NEW FILE########
__FILENAME__ = Builder
# -*- Mode: Python; coding: utf-8; indent-tabs-mode: nil; tab-width: 4 -*-
### BEGIN LICENSE
# This program is free software: you can redistribute it and/or modify it 
# under the terms of the GNU General Public License version 3, as published 
# by the Free Software Foundation.
# 
# This program is distributed in the hope that it will be useful, but 
# WITHOUT ANY WARRANTY; without even the implied warranties of 
# MERCHANTABILITY, SATISFACTORY QUALITY, or FITNESS FOR A PARTICULAR 
# PURPOSE.  See the GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License along 
# with this program.  If not, see <http://www.gnu.org/licenses/>.
### END LICENSE

### DO NOT EDIT THIS FILE ###

'''Enhances builder connections, provides object to access glade objects'''

from gi.repository import GObject, Gtk # pylint: disable=E0611

import inspect
import functools
import logging
logger = logging.getLogger('digitalocean_indicator_lib')

from xml.etree.cElementTree import ElementTree

# this module is big so uses some conventional prefixes and postfixes
# *s list, except self.widgets is a dictionary
# *_dict dictionary
# *name string
# ele_* element in a ElementTree


# pylint: disable=R0904
# the many public methods is a feature of Gtk.Builder
class Builder(Gtk.Builder):
    ''' extra features
    connects glade defined handler to default_handler if necessary
    auto connects widget to handler with matching name or alias
    auto connects several widgets to a handler via multiple aliases
    allow handlers to lookup widget name
    logs every connection made, and any on_* not made
    '''

    def __init__(self):
        Gtk.Builder.__init__(self)
        self.widgets = {}
        self.glade_handler_dict = {}
        self.connections = []
        self._reverse_widget_dict = {}

# pylint: disable=R0201
# this is a method so that a subclass of Builder can redefine it
    def default_handler(self,
        handler_name, filename, *args, **kwargs):
        '''helps the apprentice guru

    glade defined handlers that do not exist come here instead.
    An apprentice guru might wonder which signal does what he wants,
    now he can define any likely candidates in glade and notice which
    ones get triggered when he plays with the project.
    this method does not appear in Gtk.Builder'''
        logger.debug('''tried to call non-existent function:%s()
        expected in %s
        args:%s
        kwargs:%s''', handler_name, filename, args, kwargs)
# pylint: enable=R0201

    def get_name(self, widget):
        ''' allows a handler to get the name (id) of a widget

        this method does not appear in Gtk.Builder'''
        return self._reverse_widget_dict.get(widget)

    def add_from_file(self, filename):
        '''parses xml file and stores wanted details'''
        Gtk.Builder.add_from_file(self, filename)

        # extract data for the extra interfaces
        tree = ElementTree()
        tree.parse(filename)

        ele_widgets = tree.getiterator("object")
        for ele_widget in ele_widgets:
            name = ele_widget.attrib['id']
            widget = self.get_object(name)

            # populate indexes - a dictionary of widgets
            self.widgets[name] = widget

            # populate a reversed dictionary
            self._reverse_widget_dict[widget] = name

            # populate connections list
            ele_signals = ele_widget.findall("signal")

            connections = [
                (name,
                ele_signal.attrib['name'],
                ele_signal.attrib['handler']) for ele_signal in ele_signals]

            if connections:
                self.connections.extend(connections)

        ele_signals = tree.getiterator("signal")
        for ele_signal in ele_signals:
            self.glade_handler_dict.update(
            {ele_signal.attrib["handler"]: None})

    def connect_signals(self, callback_obj):
        '''connect the handlers defined in glade

        reports successful and failed connections
        and logs call to missing handlers'''
        filename = inspect.getfile(callback_obj.__class__)
        callback_handler_dict = dict_from_callback_obj(callback_obj)
        connection_dict = {}
        connection_dict.update(self.glade_handler_dict)
        connection_dict.update(callback_handler_dict)
        for item in connection_dict.items():
            if item[1] is None:
                # the handler is missing so reroute to default_handler
                handler = functools.partial(
                    self.default_handler, item[0], filename)

                connection_dict[item[0]] = handler

                # replace the run time warning
                logger.warn("expected handler '%s' in %s",
                 item[0], filename)

        # connect glade define handlers
        Gtk.Builder.connect_signals(self, connection_dict)

        # let's tell the user how we applied the glade design
        for connection in self.connections:
            widget_name, signal_name, handler_name = connection
            logger.debug("connect builder by design '%s', '%s', '%s'",
             widget_name, signal_name, handler_name)

    def get_ui(self, callback_obj=None, by_name=True):
        '''Creates the ui object with widgets as attributes

        connects signals by 2 methods
        this method does not appear in Gtk.Builder'''

        result = UiFactory(self.widgets)

        # Hook up any signals the user defined in glade
        if callback_obj is not None:
            # connect glade define handlers
            self.connect_signals(callback_obj)

            if by_name:
                auto_connect_by_name(callback_obj, self)

        return result


# pylint: disable=R0903
# this class deliberately does not provide any public interfaces
# apart from the glade widgets
class UiFactory():
    ''' provides an object with attributes as glade widgets'''
    def __init__(self, widget_dict):
        self._widget_dict = widget_dict
        for (widget_name, widget) in widget_dict.items():
            setattr(self, widget_name, widget)

        # Mangle any non-usable names (like with spaces or dashes)
        # into pythonic ones
        cannot_message = """cannot bind ui.%s, name already exists
        consider using a pythonic name instead of design name '%s'"""
        consider_message = """consider using a pythonic name instead of design name '%s'"""
        
        for (widget_name, widget) in widget_dict.items():
            pyname = make_pyname(widget_name)
            if pyname != widget_name:
                if hasattr(self, pyname):
                    logger.debug(cannot_message, pyname, widget_name)
                else:
                    logger.debug(consider_message, widget_name)
                    setattr(self, pyname, widget)

        def iterator():
            '''Support 'for o in self' '''
            return iter(widget_dict.values())
        setattr(self, '__iter__', iterator)

    def __getitem__(self, name):
        'access as dictionary where name might be non-pythonic'
        return self._widget_dict[name]
# pylint: enable=R0903


def make_pyname(name):
    ''' mangles non-pythonic names into pythonic ones'''
    pyname = ''
    for character in name:
        if (character.isalpha() or character == '_' or
            (pyname and character.isdigit())):
            pyname += character
        else:
            pyname += '_'
    return pyname


# Until bug https://bugzilla.gnome.org/show_bug.cgi?id=652127 is fixed, we 
# need to reimplement inspect.getmembers.  GObject introspection doesn't
# play nice with it.
def getmembers(obj, check):
    members = []
    for k in dir(obj):
        try:
            attr = getattr(obj, k)
        except:
            continue
        if check(attr):
            members.append((k, attr))
    members.sort()
    return members


def dict_from_callback_obj(callback_obj):
    '''a dictionary interface to callback_obj'''
    methods = getmembers(callback_obj, inspect.ismethod)

    aliased_methods = [x[1] for x in methods if hasattr(x[1], 'aliases')]

    # a method may have several aliases
    #~ @alias('on_btn_foo_clicked')
    #~ @alias('on_tool_foo_activate')
    #~ on_menu_foo_activate():
        #~ pass
    alias_groups = [(x.aliases, x) for x in aliased_methods]

    aliases = []
    for item in alias_groups:
        for alias in item[0]:
            aliases.append((alias, item[1]))

    dict_methods = dict(methods)
    dict_aliases = dict(aliases)

    results = {}
    results.update(dict_methods)
    results.update(dict_aliases)

    return results


def auto_connect_by_name(callback_obj, builder):
    '''finds handlers like on_<widget_name>_<signal> and connects them

    i.e. find widget,signal pair in builder and call
    widget.connect(signal, on_<widget_name>_<signal>)'''

    callback_handler_dict = dict_from_callback_obj(callback_obj)

    for item in builder.widgets.items():
        (widget_name, widget) = item
        signal_ids = []
        try:
            widget_type = type(widget)
            while widget_type:
                signal_ids.extend(GObject.signal_list_ids(widget_type))
                widget_type = GObject.type_parent(widget_type)
        except RuntimeError:  # pylint wants a specific error
            pass
        signal_names = [GObject.signal_name(sid) for sid in signal_ids]

        # Now, automatically find any the user didn't specify in glade
        for sig in signal_names:
            # using convention suggested by glade
            sig = sig.replace("-", "_")
            handler_names = ["on_%s_%s" % (widget_name, sig)]

            # Using the convention that the top level window is not
            # specified in the handler name. That is use
            # on_destroy() instead of on_windowname_destroy()
            if widget is callback_obj:
                handler_names.append("on_%s" % sig)

            do_connect(item, sig, handler_names,
             callback_handler_dict, builder.connections)

    log_unconnected_functions(callback_handler_dict, builder.connections)


def do_connect(item, signal_name, handler_names,
        callback_handler_dict, connections):
    '''connect this signal to an unused handler'''
    widget_name, widget = item

    for handler_name in handler_names:
        target = handler_name in callback_handler_dict.keys()
        connection = (widget_name, signal_name, handler_name)
        duplicate = connection in connections
        if target and not duplicate:
            widget.connect(signal_name, callback_handler_dict[handler_name])
            connections.append(connection)

            logger.debug("connect builder by name '%s','%s', '%s'",
             widget_name, signal_name, handler_name)


def log_unconnected_functions(callback_handler_dict, connections):
    '''log functions like on_* that we could not connect'''

    connected_functions = [x[2] for x in connections]

    handler_names = callback_handler_dict.keys()
    unconnected = [x for x in handler_names if x.startswith('on_')]

    for handler_name in connected_functions:
        try:
            unconnected.remove(handler_name)
        except ValueError:
            pass

    for handler_name in unconnected:
        logger.debug("Not connected to builder '%s'", handler_name)

########NEW FILE########
__FILENAME__ = digitalocean_indicatorconfig
# -*- Mode: Python; coding: utf-8; indent-tabs-mode: nil; tab-width: 4 -*-
### BEGIN LICENSE
# This program is free software: you can redistribute it and/or modify it 
# under the terms of the GNU General Public License version 3, as published 
# by the Free Software Foundation.
# 
# This program is distributed in the hope that it will be useful, but 
# WITHOUT ANY WARRANTY; without even the implied warranties of 
# MERCHANTABILITY, SATISFACTORY QUALITY, or FITNESS FOR A PARTICULAR 
# PURPOSE.  See the GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License along 
# with this program.  If not, see <http://www.gnu.org/licenses/>.
### END LICENSE

### DO NOT EDIT THIS FILE ###

__all__ = [
    'project_path_not_found',
    'get_data_file',
    'get_data_path',
    ]

# Where your project will look for your data (for instance, images and ui
# files). By default, this is ../data, relative your trunk layout
__digitalocean_indicator_data_directory__ = '../data/'
__license__ = 'GPL-3'
__version__ = 'VERSION'

import os

from locale import gettext as _

class project_path_not_found(Exception):
    """Raised when we can't find the project directory."""


def get_data_file(*path_segments):
    """Get the full path to a data file.

    Returns the path to a file underneath the data directory (as defined by
    `get_data_path`). Equivalent to os.path.join(get_data_path(),
    *path_segments).
    """
    return os.path.join(get_data_path(), *path_segments)


def get_data_path():
    """Retrieve digitalocean-indicator data path

    This path is by default <digitalocean_indicator_lib_path>/../data/ in trunk
    and /usr/share/digitalocean-indicator in an installed version but this path
    is specified at installation time.
    """

    # Get pathname absolute or relative.
    path = os.path.join(
        os.path.dirname(__file__), __digitalocean_indicator_data_directory__)

    abs_data_path = os.path.abspath(path)
    if not os.path.exists(abs_data_path):
        raise project_path_not_found

    return abs_data_path


def get_version():
    return __version__

########NEW FILE########
__FILENAME__ = helpers
# -*- Mode: Python; coding: utf-8; indent-tabs-mode: nil; tab-width: 4 -*-
### BEGIN LICENSE
# This program is free software: you can redistribute it and/or modify it 
# under the terms of the GNU General Public License version 3, as published 
# by the Free Software Foundation.
# 
# This program is distributed in the hope that it will be useful, but 
# WITHOUT ANY WARRANTY; without even the implied warranties of 
# MERCHANTABILITY, SATISFACTORY QUALITY, or FITNESS FOR A PARTICULAR 
# PURPOSE.  See the GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License along 
# with this program.  If not, see <http://www.gnu.org/licenses/>.
### END LICENSE

### DO NOT EDIT THIS FILE ###

"""Helpers for an Ubuntu application."""
import logging
import os

from . digitalocean_indicatorconfig import get_data_file
from . Builder import Builder

from locale import gettext as _

def get_builder(builder_file_name):
    """Return a fully-instantiated Gtk.Builder instance from specified ui 
    file
    
    :param builder_file_name: The name of the builder file, without extension.
        Assumed to be in the 'ui' directory under the data path.
    """
    # Look for the ui file that describes the user interface.
    ui_filename = get_data_file('ui', '%s.ui' % (builder_file_name,))
    if not os.path.exists(ui_filename):
        ui_filename = None

    builder = Builder()
    builder.set_translation_domain('digitalocean-indicator')
    builder.add_from_file(ui_filename)
    return builder


# Owais Lone : To get quick access to icons and stuff.
def get_media_file(media_file_name):
    media_filename = get_data_file('media', '%s' % (media_file_name,))
    if not os.path.exists(media_filename):
        media_filename = None

    return "file:///"+media_filename

class NullHandler(logging.Handler):
    def emit(self, record):
        pass

def set_up_logging(opts):
    # add a handler to prevent basicConfig
    root = logging.getLogger()
    null_handler = NullHandler()
    root.addHandler(null_handler)

    formatter = logging.Formatter("%(levelname)s:%(name)s: %(funcName)s() '%(message)s'")

    logger = logging.getLogger('digitalocean_indicator')
    logger_sh = logging.StreamHandler()
    logger_sh.setFormatter(formatter)
    logger.addHandler(logger_sh)

    lib_logger = logging.getLogger('digitalocean_indicator_lib')
    lib_logger_sh = logging.StreamHandler()
    lib_logger_sh.setFormatter(formatter)
    lib_logger.addHandler(lib_logger_sh)

    # Set the logging level to show debug messages.
    if opts.verbose:
        logger.setLevel(logging.DEBUG)
        logger.debug('logging enabled')
    if opts.verbose > 1:
        lib_logger.setLevel(logging.DEBUG)

def get_help_uri(page=None):
    # help_uri from source tree - default language
    here = os.path.dirname(__file__)
    help_uri = os.path.abspath(os.path.join(here, '..', 'help', 'C'))

    if not os.path.exists(help_uri):
        # installed so use gnome help tree - user's language
        help_uri = 'digitalocean-indicator'

    # unspecified page is the index.page
    if page is not None:
        help_uri = '%s#%s' % (help_uri, page)

    return help_uri

def show_uri(parent, link):
    from gi.repository import Gtk # pylint: disable=E0611
    screen = parent.get_screen()
    Gtk.show_uri(screen, link, Gtk.get_current_event_time())

def alias(alternative_function_name):
    '''see http://www.drdobbs.com/web-development/184406073#l9'''
    def decorator(function):
        '''attach alternative_function_name(s) to function'''
        if not hasattr(function, 'aliases'):
            function.aliases = []
        function.aliases.append(alternative_function_name)
        return function
    return decorator

########NEW FILE########
__FILENAME__ = PreferencesDialog
# -*- Mode: Python; coding: utf-8; indent-tabs-mode: nil; tab-width: 4 -*-
### BEGIN LICENSE
# This program is free software: you can redistribute it and/or modify it 
# under the terms of the GNU General Public License version 3, as published 
# by the Free Software Foundation.
# 
# This program is distributed in the hope that it will be useful, but 
# WITHOUT ANY WARRANTY; without even the implied warranties of 
# MERCHANTABILITY, SATISFACTORY QUALITY, or FITNESS FOR A PARTICULAR 
# PURPOSE.  See the GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License along 
# with this program.  If not, see <http://www.gnu.org/licenses/>.
### END LICENSE

### DO NOT EDIT THIS FILE ###

"""this dialog adjusts values in gsettings
"""

from gi.repository import Gtk # pylint: disable=E0611
import logging
logger = logging.getLogger('digitalocean_indicator_lib')

from . helpers import get_builder, show_uri, get_help_uri

class PreferencesDialog(Gtk.Dialog):
    __gtype_name__ = "PreferencesDialog"

    def __new__(cls):
        """Special static method that's automatically called by Python when 
        constructing a new instance of this class.
        
        Returns a fully instantiated PreferencesDialog object.
        """
        builder = get_builder('PreferencesDigitaloceanIndicatorDialog')
        new_object = builder.get_object("preferences_digitalocean_indicator_dialog")
        new_object.finish_initializing(builder)
        return new_object

    def finish_initializing(self, builder):
        """Called while initializing this instance in __new__

        finish_initalizing should be called after parsing the ui definition
        and creating a PreferencesDialog object with it in order to
        finish initializing the start of the new PerferencesDigitaloceanIndicatorDialog
        instance.
        
        Put your initialization code in here and leave __init__ undefined.
        """

        # Get a reference to the builder and set up the signals.
        self.builder = builder
        self.ui = builder.get_ui(self, True)

        # code for other initialization actions should be added here

    def on_btn_close_clicked(self, widget, data=None):
        self.destroy()


########NEW FILE########
__FILENAME__ = test_example
#!/usr/bin/python
# -*- Mode: Python; coding: utf-8; indent-tabs-mode: nil; tab-width: 4 -*-
### BEGIN LICENSE
# This program is free software: you can redistribute it and/or modify it 
# under the terms of the GNU General Public License version 3, as published 
# by the Free Software Foundation.
# 
# This program is distributed in the hope that it will be useful, but 
# WITHOUT ANY WARRANTY; without even the implied warranties of 
# MERCHANTABILITY, SATISFACTORY QUALITY, or FITNESS FOR A PARTICULAR 
# PURPOSE.  See the GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License along 
# with this program.  If not, see <http://www.gnu.org/licenses/>.
### END LICENSE

import sys
import os.path
import unittest
sys.path.insert(0, os.path.realpath(os.path.join(os.path.dirname(__file__), "..")))

from digitalocean_indicator import AboutDigitaloceanIndicatorDialog

class TestExample(unittest.TestCase):
    def setUp(self):
        self.AboutDigitaloceanIndicatorDialog_members = [
        'AboutDialog', 'AboutDigitaloceanIndicatorDialog', 'gettext', 'logger', 'logging']

    def test_AboutDigitaloceanIndicatorDialog_members(self):
        all_members = dir(AboutDigitaloceanIndicatorDialog)
        public_members = [x for x in all_members if not x.startswith('_')]
        public_members.sort()
        self.assertEqual(self.AboutDigitaloceanIndicatorDialog_members, public_members)

if __name__ == '__main__':    
    unittest.main()

########NEW FILE########
__FILENAME__ = test_lint
#!/usr/bin/python
# -*- Mode: Python; coding: utf-8; indent-tabs-mode: nil; tab-width: 4 -*-
### BEGIN LICENSE
# This program is free software: you can redistribute it and/or modify it 
# under the terms of the GNU General Public License version 3, as published 
# by the Free Software Foundation.
# 
# This program is distributed in the hope that it will be useful, but 
# WITHOUT ANY WARRANTY; without even the implied warranties of 
# MERCHANTABILITY, SATISFACTORY QUALITY, or FITNESS FOR A PARTICULAR 
# PURPOSE.  See the GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License along 
# with this program.  If not, see <http://www.gnu.org/licenses/>.
### END LICENSE

import unittest
import subprocess

class TestPylint(unittest.TestCase):
    def test_project_errors_only(self):
        '''run pylint in error only mode
        
        your code may well work even with pylint errors
        but have some unusual code'''
        return_code = subprocess.call(["pylint", '-E', 'digitalocean_indicator'])
        # not needed because nosetests displays pylint console output
        #self.assertEqual(return_code, 0)

    # un-comment the following for loads of diagnostics   
    #~ def test_project_full_report(self):
        #~ '''Only for the brave
#~ 
        #~ you will have to make judgement calls about your code standards
        #~ that differ from the norm'''
        #~ return_code = subprocess.call(["pylint", 'digitalocean_indicator'])

if __name__ == '__main__':
    'you will get better results with nosetests'
    unittest.main()

########NEW FILE########
