__FILENAME__ = pygtk-example
#!/usr/bin/python

import pygtk
pygtk.require('2.0')
import gtk

class HelloWorld:
    def __init__(self):
        self.window = gtk.Window(gtk.WINDOW_TOPLEVEL)
        self.window.set_border_width(10)
    
        self.window.connect("delete_event", self.delete_event)
        self.window.connect("destroy", self.destroy)
    
        self.button = gtk.Button("Hello World")
        self.button.connect("clicked", self.hello)
        self.button.connect_object("clicked", gtk.Widget.destroy, self.window)
    
        self.window.add(self.button)
        self.window.show_all()

    def hello(self, widget):
        print 'Hello World'

    def delete_event(self, widget, event, data=None):
        print "delete event occurred"

        return False

    def destroy(self, widget, data=None):
        print "destroy signal occurred"
        gtk.main_quit()

    def main(self):
        gtk.main()

if __name__ == "__main__":
    hello = HelloWorld()
    hello.main()

########NEW FILE########
__FILENAME__ = python-script
#!/usr/bin/python

print 'Hello World'

########NEW FILE########
__FILENAME__ = test_app
import os
import shutil
import unittest

from ubuntutweak.modules import ModuleLoader
from ubuntutweak.common import consts
from ubuntutweak.main import UbuntuTweakWindow

class TestApp(unittest.TestCase):
    def setUp(self):
        self.window = UbuntuTweakWindow()

    def test_app(self):
        # tweaks
        self.window.select_target_feature('tweaks')
        self.assertEqual(self.window.loaded_modules, {})
        self.assertEqual(self.window.current_feature, 'tweaks')
        self.assertEqual(self.window.feature_dict, {'overview': 0,
                                                    'apps': 1,
                                                    'tweaks': 2,
                                                    'admins': 3,
                                                    'janitor': 4,
                                                    'search': 6,
                                                    'wait': 5})
        self.assertEqual(self.window.navigation_dict, {'tweaks': (None, None)})

        # tweaks->Nautilus
        self.window._load_module('Nautilus')
        self.assertEqual(self.window.loaded_modules, {'Nautilus': 7})
        self.assertEqual(self.window.current_feature, 'tweaks')
        self.assertEqual(self.window.navigation_dict, {'tweaks': ('Nautilus', None)})
        # Nautilus->tweaks
        self.window.on_back_button_clicked(None)
        self.assertEqual(self.window.current_feature, 'tweaks')
        self.assertEqual(self.window.navigation_dict, {'tweaks': (None, 'Nautilus')})
        # tweaks->Compiz
        self.window._load_module('Window')
        self.assertEqual(self.window.current_feature, 'tweaks')
        self.assertEqual(self.window.navigation_dict, {'tweaks': ('Window', None)})

    def todo(self):
        #TODO toggled has different behavir
        # admins->DesktopRecovery
        self.window._load_module('DesktopRecovery')
        self.window.admins_button.toggled()
        self.assertEqual(self.window.current_feature, 'admins')
        self.assertEqual(self.window.navigation_dict, {'tweaks': ('Compiz', None),
                                                       'admins': ('DesktopRecovery', None)})

        # DesktopRecovery->admins
        self.window.on_back_button_clicked(None)
        self.assertEqual(self.window.current_feature, 'admins')
        self.assertEqual(self.window.navigation_dict, {'tweaks': ('Compiz', None),
                                                       'admins': (None, 'DesktopRecovery')})

        # tweaks->Compiz
        self.window.select_target_feature('tweaks')
        self.assertEqual(self.window.current_feature, 'tweaks')
        self.assertEqual(self.window.navigation_dict, {'tweaks': ('Compiz', None),
                                                       'admins': (None, 'DesktopRecovery')})

    def tearDown(self):
        del self.window

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_configsettings
import os
import tempfile
import unittest

from ubuntutweak.settings.configsettings import ConfigSetting

class TestConfigSettings(unittest.TestCase):
    def setUp(self):
        self.unity_greeter_override_file = tempfile.NamedTemporaryFile(delete=False)
        self.unity_greeter_override_file.write("[com.canonical.unity-greeter]\n"
        "draw-grid = true\n"
        "play-ready-sound = false\n"
        "background = '/usr/share/backgrounds/The_Forbidden_City_by_Daniel_Mathis.jpg'\n")
        self.unity_greeter_override_file.close()
        self.unity_greeter_override_path = self.unity_greeter_override_file.name

    def test_config_settings(self):
        # draw grid
        draw_grid_setting_key = "%s::%s#%s" % (self.unity_greeter_override_path, 'com.canonical.unity-greeter', 'draw-grid')

        self.draw_grid_setting = ConfigSetting(draw_grid_setting_key, type=bool)
        self.assertEqual(True, self.draw_grid_setting.get_value())
        self.draw_grid_setting.set_value(False)
        self.assertEqual(False, self.draw_grid_setting.get_value())

        #try again the fuzz type
        self.draw_grid_setting = ConfigSetting(draw_grid_setting_key)
        self.assertEqual(False, self.draw_grid_setting.get_value())
        self.draw_grid_setting.set_value(True)
        self.assertEqual(True, self.draw_grid_setting.get_value())

        #play sound
        play_sound_key = self.get_key('play-ready-sound')
        self.play_sound_setting = ConfigSetting(play_sound_key)
        self.assertEqual(False, self.play_sound_setting.get_value())

        #background
        background_setting = ConfigSetting(self.get_key('background'), type=str)
        self.assertEqual('/usr/share/backgrounds/The_Forbidden_City_by_Daniel_Mathis.jpg', background_setting.get_value())
        #try again the fuzz type for str
        background_setting = ConfigSetting(self.get_key('background'))
        self.assertEqual("/usr/share/backgrounds/The_Forbidden_City_by_Daniel_Mathis.jpg", background_setting.get_value())

    def get_key(self, key):
        return "%s::%s#%s" % (self.unity_greeter_override_path, 'com.canonical.unity-greeter', key)


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_factory
import unittest

from gi.repository import Gtk
from ubuntutweak.factory import WidgetFactory

class TestConfigSettings(unittest.TestCase):
    def test_widget_factory(self):
        # Normal case
        user_indicator_label, user_menu_switch, reset_button = WidgetFactory.create("Switch",
                                  label='user-indicator',
                                  enable_reset=True,
                                  backend="gsettings",
                                  key='com.canonical.indicator.session.user-show-menu')

        self.assertTrue(isinstance(user_indicator_label, Gtk.Label))
        self.assertTrue(isinstance(user_menu_switch, Gtk.Switch))
        self.assertTrue(isinstance(reset_button, Gtk.Button))

        # No reset case
        user_indicator_label, user_menu_switch = WidgetFactory.create("Switch",
                                  label='user-indicator',
                                  backend="gsettings",
                                  key='com.canonical.indicator.session.user-show-menu')
        self.assertTrue(isinstance(user_indicator_label, Gtk.Label))
        self.assertTrue(isinstance(user_menu_switch, Gtk.Switch))

        # Failed case, no reset
        user_indicator_label, user_menu_switch = WidgetFactory.create("Switch",
                                  label='user-indicator',
                                  backend="gsettings",
                                  key='org.canonical.indicator.session.user-show-menu')
        self.assertFalse(user_indicator_label)
        self.assertFalse(user_menu_switch)

        # Failed case, reset
        user_indicator_label, user_menu_switch, reset_button = WidgetFactory.create("Switch",
                                  label='user-indicator',
                                  enable_reset=True,
                                  backend="gsettings",
                                  key='org.canonical.indicator.session.user-show-menu')

        self.assertFalse(user_indicator_label)
        self.assertFalse(user_menu_switch)
        self.assertFalse(reset_button)

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_janitor
import unittest

from ubuntutweak.janitor.oldkernel_plugin import OldKernelPlugin

class TestJanitorFunctions(unittest.TestCase):
    def setUp(self):
        self.oldkernel_plugin = OldKernelPlugin()
        self.oldkernel_plugin.current_kernel_version = '2.6.38-10'

    def test_oldkernel(self):
        self.assertEqual(self.oldkernel_plugin.p_kernel_version.findall('3.6.0-030600rc3')[0], '3.6.0-030600')
        self.assertEqual(self.oldkernel_plugin.p_kernel_version.findall('3.6.0-0306rc3')[0], '3.6.0-0306')
        self.assertEqual(self.oldkernel_plugin.p_kernel_version.findall('3.6.0-03rc3')[0], '3.6.0-03')

        self.assertTrue(self.oldkernel_plugin.is_old_kernel_package('linux-headers-2.6.35-28'))
        self.assertTrue(self.oldkernel_plugin.is_old_kernel_package('linux-image-2.6.38-9-generic'))
        self.assertFalse(self.oldkernel_plugin.is_old_kernel_package('linux-image-2.6.38-10'))
        self.assertFalse(self.oldkernel_plugin.is_old_kernel_package('linux-image-2.6.38-11'))

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_janitor_plugins
import os
import unittest

from ubuntutweak.janitor.mozilla_plugin import FirefoxCachePlugin

class TestJanitorPlugin(unittest.TestCase):
    def setUp(self):
        self.firefox_plugin = FirefoxCachePlugin()

    def test_firefox_plugin(self):
        self.assertTrue(os.path.expanduser('~/.mozilla/firefox/5tzbwjwa.default'), self.firefox_plugin.get_path())

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_quicklists
import os
import unittest

from ubuntutweak.admins.quicklists import NewDesktopEntry

class TestQuicklists(unittest.TestCase):
    def setUp(self):
        os.system('cp /usr/share/applications/google-chrome.desktop %s' %os.path.join(NewDesktopEntry.user_folder, 'google-chrome.desktop'))
        self.entry = NewDesktopEntry('/usr/share/applications/ubuntu-tweak.desktop')
        self.admin_gruop = 'Admins Shortcut Group'
        self.admin_name = 'Admins'
        self.admin_exec = 'ubuntu-tweak -f admins'
        self.admin_env = 'Unity'

        self.chrome_entry = NewDesktopEntry(os.path.join(NewDesktopEntry.user_folder, 'google-chrome.desktop'))
        self.entry3 = NewDesktopEntry('/usr/share/applications/empathy.desktop')

    def test_quicklists(self):
        print self.entry3.groups()
        print self.entry3.get('Actions')
        print self.entry3.get('X-Ayatana-Desktop-Shortcuts')
        self.assertEqual(6, len(self.entry.groups()))
        self.assertEqual(5, len(self.entry.get_actions()))
        self.assertEqual(self.admin_name, self.entry.get('Name', self.admin_gruop))
        self.assertEqual(self.admin_exec, self.entry.get('Exec', self.admin_gruop))
        self.assertEqual('Unity', self.entry.get('TargetEnvironment', self.admin_gruop))
        self.assertEqual(False, self.entry.is_user_desktop_file())
        self.assertEqual(False, self.entry.can_reset())

        self.assertEqual(True, self.chrome_entry.is_user_desktop_file())
        self.assertEqual(True, self.chrome_entry.can_reset())

        #test reorder
        current_order = self.chrome_entry.get_actions()
        new_order = list(reversed(current_order))
        self.chrome_entry.reorder_actions(new_order)
        self.assertEqual(new_order, self.chrome_entry.get_actions())

        #remove action
        self.chrome_entry.remove_action('NewIncognito')
        self.assertEqual(['NewWindow'], self.chrome_entry.get_actions())
        self.chrome_entry.remove_action('NewWindow')
        self.assertEqual([], self.chrome_entry.get_actions())

        # test reset
        self.chrome_entry.reset()
        self.assertEqual(['NewWindow', 'NewIncognito'], self.chrome_entry.get_actions())


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_recently
import unittest

from ubuntutweak.main import UbuntuTweakWindow
from ubuntutweak.settings.gsettings import GSetting

class TestRecently(unittest.TestCase):
    def setUp(self):
        self.window = UbuntuTweakWindow()
        self.window.loaded_modules = {}
        self.window.modules_index = {}
        self.window.navigation_dict = {'tweaks': [None, None]}
        self.setting = GSetting('com.ubuntu-tweak.tweak.recently-used')

    def test_recently(self):
        self.setting.set_value([])
        self.assertEqual(self.setting.get_value(), [])

        self.window._load_module('Icons')
        self.assertEqual(self.setting.get_value(), ['Icons'])

        self.window._load_module('Nautilus')
        self.assertEqual(self.setting.get_value(), ['Nautilus', 'Icons'])

    def tearDown(self):
        self.setting.set_value([])
        del self.window

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_schema
import unittest

from ubuntutweak.settings.gsettings import Schema
from ubuntutweak.settings.gconfsettings import GconfSetting

class TestSchema(unittest.TestCase):
    def setUp(self):
        self.interface_schema = 'org.gnome.desktop.interface'
        self.gtk_theme_key = 'gtk-theme'

        self.light_theme = '/apps/metacity/general/button_layout'
        self.title_font = '/apps/metacity/general/titlebar_font'

    def test_schema(self):
        self.assertEqual('Ambiance', Schema.load_schema(self.interface_schema, self.gtk_theme_key))
        light_theme_setting = GconfSetting(self.light_theme)
        self.assertEqual('close,minimize,maximize:', light_theme_setting.get_schema_value())
        self.assertEqual('Ubuntu Bold 11', GconfSetting(self.title_font).get_schema_value())

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_themefile
import os
import shutil
import unittest

from ubuntutweak.utils.tar import ThemeFile

class TestThemeFile(unittest.TestCase):
    def setUp(self):
        self.icon_path1 = '/tmp/ubunu-icon.tar.gz'
        os.system('cd /usr/share/icons/ && tar zcf %s ubuntu-mono-dark' % self.icon_path1)
        self.icon_path2 = '/tmp/light.tar.gz'
        os.system('cd /usr/share/icons/ubuntu-mono-light && tar zcf %s .' % self.icon_path2)

    def test_theme_file(self):
        tf1 = ThemeFile(self.icon_path1)
        self.assertEqual(tf1.is_theme(), True)
        self.assertEqual(tf1.theme_name, 'Ubuntu-Mono-Dark')
        self.assertEqual(tf1.install_name, 'ubuntu-mono-dark')

        tf2 = ThemeFile(self.icon_path2)
        self.assertEqual(tf2.is_theme(), True)
        self.assertEqual(tf2.theme_name, 'Ubuntu-Mono-Light')
        self.assertEqual(tf2.install_name, 'light')

    def tearDown(self):
        os.system('rm %s' % self.icon_path1)
        os.system('rm %s' % self.icon_path2)

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_utils
import unittest

from ubuntutweak import modules
from ubuntutweak.utils import ppa

class TestUtilsFunctions(unittest.TestCase):
    def setUp(self):
        self.ppa_home_url = 'https://launchpad.net/~tualatrix/+archive/ppa'
        self.ppa_archive_url = 'http://ppa.launchpad.net/tualatrix/ppa/ubuntu'

    def test_ppa(self):
        self.assertTrue(ppa.is_ppa(self.ppa_archive_url))

        list_name = ppa.get_list_name(self.ppa_archive_url)
        self.failUnless(list_name == '' or list_name.startswith('/var/lib/apt/lists/'))

        self.assertEqual(ppa.get_short_name(self.ppa_archive_url), 'ppa:tualatrix/ppa')

        self.assertEqual(ppa.get_homepage(self.ppa_archive_url), self.ppa_home_url)

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = appcenter
# Ubuntu Tweak - Ubuntu Configuration Tool
#
# Copyright (C) 2007-2011 Tualatrix Chou <tualatrix@gmail.com>
#
# Ubuntu Tweak is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# Ubuntu Tweak is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Ubuntu Tweak; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA

import os
import json
import thread
import logging

from gi.repository import Gtk, GdkPixbuf
from gi.repository import GObject
from gi.repository import Pango
from xdg.DesktopEntry import DesktopEntry

from ubuntutweak.common import consts
from ubuntutweak.common.debug import log_func
from ubuntutweak.modules  import TweakModule
from ubuntutweak.gui.dialogs import ErrorDialog, InfoDialog, QuestionDialog
from ubuntutweak.gui.dialogs import ProcessDialog
from ubuntutweak.gui.gtk import post_ui, set_busy, unset_busy
from ubuntutweak.utils.parser import Parser
from ubuntutweak.network import utdata
from ubuntutweak.network.downloadmanager import DownloadDialog
from ubuntutweak.settings.gsettings import GSetting
from ubuntutweak.utils import set_label_for_stock_button, icon
from ubuntutweak.utils.package import AptWorker
from ubuntutweak.apps import CategoryView

log = logging.getLogger("AppCenter")

APPCENTER_ROOT = os.path.join(consts.CONFIG_ROOT, 'appcenter')
APP_VERSION_URL = utdata.get_version_url('/appcenter_version/')
UPDATE_SETTING = GSetting(key='com.ubuntu-tweak.tweak.appcenter-has-update', type=bool)
VERSION_SETTING = GSetting(key='com.ubuntu-tweak.tweak.appcenter-version', type=str)

def get_app_data_url():
    return utdata.get_download_url('/media/utdata/appcenter-%s.tar.gz' %
                                   VERSION_SETTING.get_value())

if not os.path.exists(APPCENTER_ROOT):
    os.mkdir(APPCENTER_ROOT)


class PackageInfo:
    DESKTOP_DIR = '/usr/share/app-install/desktop/'

    def __init__(self, name):
        self.name = name
        self.pkg = AptWorker.get_cache()[name]
        self.desktopentry = DesktopEntry(self.DESKTOP_DIR + name + '.desktop')

    def check_installed(self):
        return self.pkg.isInstalled

    def get_comment(self):
        return self.desktopentry.getComment()

    def get_name(self):
        appname = self.desktopentry.getName()
        if appname == '':
            return self.name.title()

        return appname

    def get_version(self):
        try:
            return self.pkg.versions[0].version
        except:
            return ''


class StatusProvider(object):
    def __init__(self, name):
        self._path = os.path.join(consts.CONFIG_ROOT, name)
        self._is_init = False

        try:
            self._data = json.loads(open(self._path).read())
        except:
            log.debug('No Status data available, set init to True')
            self._data = {'apps': {}, 'cates': {}}
            self._is_init = True

    def set_init(self, active):
        self._is_init = active

    def get_init(self):
        return self._is_init

    def get_data(self):
        return self._data

    def save(self):
        file = open(self._path, 'w')
        file.write(json.dumps(self._data))
        file.close()

    def load_objects_from_parser(self, parser):
        init = self.get_init()

        for key in parser.keys():
            #FIXME because of source id
            if init:
                self._data['apps'][key] = {}
                self._data['apps'][key]['read'] = True
                self._data['apps'][key]['cate'] = parser.get_category(key)
            else:
                if key not in self._data['apps']:
                    self._data['apps'][key] = {}
                    self._data['apps'][key]['read'] = False
                    self._data['apps'][key]['cate'] = parser.get_category(key)

        if init and parser.keys():
            self.set_init(False)

        self.save()

    def count_unread(self, cate):
        i = 0
        for key in self._data['apps']:
            if self._data['apps'][key]['cate'] == cate and not self._data['apps'][key]['read']:
                i += 1
        return i

    def load_category_from_parser(self, parser):
        for cate in parser.keys():
            id = parser.get_id(cate)
            if self._is_init:
                self._data['cates'][id] = 0
            else:
                self._data['cates'][id] = self.count_unread(id)

        self._is_init = False
        self.save()

    def get_cate_unread_count(self, id):
        return self.count_unread(id)

    def get_read_status(self, key):
        try:
            return self._data['apps'][key]['read']
        except:
            return True

    def set_as_read(self, key):
        try:
            self._data['apps'][key]['read'] = True
        except:
            pass
        self.save()

class AppParser(Parser):
    def __init__(self):
        app_data = os.path.join(APPCENTER_ROOT, 'apps.json')

        Parser.__init__(self, app_data, 'package')

    def get_summary(self, key):
        return self.get_by_lang(key, 'summary')

    def get_name(self, key):
        return self.get_by_lang(key, 'name')

    def get_category(self, key):
        return self[key]['category']


class AppCategoryView(CategoryView):

    def pre_update_cate_model(self):
        self.model.append(None, (-1,
                                 'installed-apps',
                                 _('Installed Apps')))


class AppView(Gtk.TreeView):
    __gsignals__ = {
        'changed': (GObject.SignalFlags.RUN_FIRST,
                    None,
                    (GObject.TYPE_INT,)),
        'select': (GObject.SignalFlags.RUN_FIRST,
                    None,
                    (GObject.TYPE_BOOLEAN,))
    }

    (COLUMN_INSTALLED,
     COLUMN_ICON,
     COLUMN_PKG,
     COLUMN_NAME,
     COLUMN_DESC,
     COLUMN_DISPLAY,
     COLUMN_CATE,
     COLUMN_TYPE,
    ) = range(8)

    def __init__(self):
        GObject.GObject.__init__(self)

        self.to_add = []
        self.to_rm = []
        self.filter = None
        self._status = None

        model = self._create_model()
        self._add_columns()
        self.set_model(model)

        self.set_rules_hint(True)
        self.set_search_column(self.COLUMN_NAME)

        self.show_all()

    def _create_model(self):
        model = Gtk.ListStore(
                        GObject.TYPE_BOOLEAN,
                        GdkPixbuf.Pixbuf,
                        GObject.TYPE_STRING,
                        GObject.TYPE_STRING,
                        GObject.TYPE_STRING,
                        GObject.TYPE_STRING,
                        GObject.TYPE_STRING,
                        GObject.TYPE_STRING)

        return model

    def sort_model(self):
        model = self.get_model()
        model.set_sort_column_id(self.COLUMN_NAME, Gtk.SortType.ASCENDING)

    def _add_columns(self):
        renderer = Gtk.CellRendererToggle()
        renderer.set_property("xpad", 6)
        renderer.connect('toggled', self.on_install_toggled)

        column = Gtk.TreeViewColumn('', renderer, active=self.COLUMN_INSTALLED)
        column.set_sort_column_id(self.COLUMN_INSTALLED)
        self.append_column(column)

        column = Gtk.TreeViewColumn('Applications')
        column.set_sort_column_id(self.COLUMN_NAME)
        column.set_spacing(5)
        renderer = Gtk.CellRendererPixbuf()
        column.pack_start(renderer, False)
        column.set_cell_data_func(renderer, self.icon_column_view_func)
        column.add_attribute(renderer, 'pixbuf', self.COLUMN_ICON)

        renderer = Gtk.CellRendererText()
        renderer.set_property("xpad", 6)
        renderer.set_property("ypad", 6)
        renderer.set_property('ellipsize', Pango.EllipsizeMode.END)
        column.pack_start(renderer, True)
        column.add_attribute(renderer, 'markup', self.COLUMN_DISPLAY)
        self.append_column(column)

    def set_as_read(self, iter, model):
        package = model.get_value(iter, self.COLUMN_PKG)
        if self._status and not self._status.get_read_status(package):
            appname = model.get_value(iter, self.COLUMN_NAME)
            desc = model.get_value(iter, self.COLUMN_DESC)
            self._status.set_as_read(package)
            model.set_value(iter, self.COLUMN_DISPLAY, '<b>%s</b>\n%s' % (appname, desc))

    def icon_column_view_func(self, tree_column, renderer, model, iter, data=None):
        pixbuf = model.get_value(iter, self.COLUMN_ICON)
        if pixbuf == None:
            renderer.set_property("visible", False)
        else:
            renderer.set_property("visible", True)

    def append_update(self, status, pkgname, summary):
        model = self.get_model()

        icontheme = Gtk.IconTheme.get_default()
        for icon_name in ['application-x-deb', 'package-x-generic', 'package']:
            icon_theme = icontheme.lookup_icon(icon_name,
                                               size=32,
                                               flags=Gtk.IconLookupFlags.NO_SVG)
            if icon_theme:
                break

        if icon_theme:
            pixbuf = icon_theme.load_icon()
        else:
            pixbuf = icon.get_from_name(size=32)

        iter = model.append()
        model.set(iter,
                  self.COLUMN_INSTALLED, status,
                  self.COLUMN_ICON, pixbuf,
                  self.COLUMN_PKG, pkgname,
                  self.COLUMN_NAME, pkgname,
                  self.COLUMN_DESC, summary,
                  self.COLUMN_DISPLAY, '<b>%s</b>\n%s' % (pkgname, summary),
                  self.COLUMN_TYPE, 'update')

    def set_status_active(self, active):
        if active:
            self._status = StatusProvider('appstatus.json')

    def get_status(self):
        return self._status

    @log_func(log)
    def update_model(self, apps=None, only_installed=False):
        '''apps is a list to iter pkgname,
        '''
        model = self.get_model()
        model.clear()

        app_parser = AppParser()

        if self._status:
            self._status.load_objects_from_parser(app_parser)

        if not apps:
            apps = app_parser.keys()

        for pkgname in apps:
            category = app_parser.get_category(pkgname)
            pixbuf = self.get_app_logo(app_parser[pkgname]['logo'])

            try:
                package = PackageInfo(pkgname)
                is_installed = package.check_installed()
                if not is_installed and only_installed:
                    continue
                appname = package.get_name()
                desc = app_parser.get_summary(pkgname)
            except Exception, e:
                # Confirm the invalid package isn't in the count
                # But in the future, Ubuntu Tweak should display the invalid package too
                if self._status and not self._status.get_read_status(pkgname):
                    self._status.set_as_read(pkgname)
                continue

            if self.filter == None or self.filter == category:
                iter = model.append()
                if pkgname in self.to_add or pkgname in self.to_rm:
                    status = not is_installed
                    display = self.__fill_changed_display(appname, desc)
                else:
                    status = is_installed
                    if self._status and not self._status.get_read_status(pkgname):
                        display = '<b>%s <span foreground="#ff0000">(New!!!)</span>\n%s</b>' % (appname, desc)
                    else:
                        display = '<b>%s</b>\n%s' % (appname, desc)

                model.set(iter,
                          self.COLUMN_INSTALLED, status,
                          self.COLUMN_ICON, pixbuf,
                          self.COLUMN_PKG, pkgname,
                          self.COLUMN_NAME, appname,
                          self.COLUMN_DESC, desc,
                          self.COLUMN_DISPLAY, display,
                          self.COLUMN_CATE, str(category),
                          self.COLUMN_TYPE, 'app')

    def __fill_changed_display(self, appname, desc):
        return '<span style="italic" weight="bold"><b>%s</b>\n%s</span>' % (appname, desc)

    def on_install_toggled(self, cell, path):
        def do_app_changed(model, iter, appname, desc):
            model.set(iter,
                      self.COLUMN_DISPLAY, self.__fill_changed_display(appname, desc))
        def do_app_unchanged(model, iter, appname, desc):
            model.set(iter,
                      self.COLUMN_DISPLAY,
                      '<b>%s</b>\n%s' % (appname, desc))

        model = self.get_model()

        iter = model.get_iter((int(path),))
        is_installed = model.get_value(iter, self.COLUMN_INSTALLED)
        pkgname = model.get_value(iter, self.COLUMN_PKG)
        appname = model.get_value(iter, self.COLUMN_NAME)
        desc = model.get_value(iter, self.COLUMN_DESC)
        type = model.get_value(iter, self.COLUMN_TYPE)

        if pkgname:
            if type == 'app':
                is_installed = not is_installed
                if is_installed:
                    if pkgname in self.to_rm:
                        self.to_rm.remove(pkgname)
                        do_app_unchanged(model, iter, appname, desc)
                    else:
                        self.to_add.append(pkgname)
                        do_app_changed(model, iter, appname, desc)
                else:
                    if pkgname in self.to_add:
                        self.to_add.remove(pkgname)
                        do_app_unchanged(model, iter, appname, desc)
                    else:
                        self.to_rm.append(pkgname)
                        do_app_changed(model, iter, appname, desc)

                model.set(iter, self.COLUMN_INSTALLED, is_installed)
            else:
                to_installed = is_installed
                to_installed = not to_installed
                if to_installed == True:
                    self.to_add.append(pkgname)
                else:
                    self.to_add.remove(pkgname)

                model.set(iter, self.COLUMN_INSTALLED, to_installed)

            self.emit('changed', len(self.to_add) + len(self.to_rm))
        else:
            model.set(iter, self.COLUMN_INSTALLED, not is_installed)
            self.emit('select', not is_installed)

    @log_func(log)
    def set_filter(self, filter):
        self.filter = filter

    def get_app_logo(self, file_name):
        path = os.path.join(APPCENTER_ROOT, file_name)
        if not os.path.exists(path) or file_name == '':
            path = os.path.join(consts.DATA_DIR, 'pixmaps/common-logo.png')

        try:
            pixbuf = GdkPixbuf.Pixbuf.new_from_file(path)
            if pixbuf.get_width() != 32 or pixbuf.get_height() != 32:
                pixbuf = pixbuf.scale_simple(32, 32, GdkPixbuf.InterpType.BILINEAR)
            return pixbuf
        except:
            return Gtk.IconTheme.get_default().load_icon(Gtk.STOCK_MISSING_IMAGE, 32, 0)

class CheckUpdateDialog(ProcessDialog):

    def __init__(self, parent, url):
        self.status = None
        self.done = False
        self.error = None
        self.user_action = False
        self.url = url

        super(CheckUpdateDialog, self).__init__(parent=parent)
        self.set_dialog_lable(_('Checking update...'))

    def run(self):
        thread.start_new_thread(self.process_data, ())
        GObject.timeout_add(100, self.on_timeout)
        return super(CheckUpdateDialog, self).run()

    def process_data(self):
        import time
        time.sleep(1)
        try:
            self.status = self.get_updatable()
        except IOError:
            self.error = True
        else:
            self.done = True

    def get_updatable(self):
        return utdata.check_update_function(self.url, APPCENTER_ROOT, \
                                            UPDATE_SETTING, VERSION_SETTING, \
                                            auto=False)

    def on_timeout(self):
        self.pulse()

        if self.error:
            self.destroy()
        elif not self.done:
            return True
        else:
            self.destroy()

class FetchingDialog(DownloadDialog):
    def __init__(self, url, parent=None):
        super(FetchingDialog, self).__init__(url=url,
                                    title=_('Fetching online data...'),
                                    parent=parent)
        log.debug("Will start to download online data from: %s", url)

class AppCenter(TweakModule):
    __title__ = _('Application Center')
    __desc__ = _('A simple but efficient way for finding and installing popular applications.')
    __icon__ = 'gnome-app-install'
    __url__ = 'http://ubuntu-tweak.com/app/'
    __urltitle__ = _('Visit Online Application Center')
    __category__ = 'application'
    __utactive__ = False

    def __init__(self):
        TweakModule.__init__(self, 'appcenter.ui')

        set_label_for_stock_button(self.sync_button, _('_Sync'))

        self.to_add = []
        self.to_rm = []

        self.url = APP_VERSION_URL

        self.appview = AppView()
        self.appview.set_status_active(True)
        self.appview.update_model()
        self.appview.sort_model()
        self.appview.connect('changed', self.on_app_status_changed)
        self.app_selection = self.appview.get_selection()
        self.app_selection.connect('changed', self.on_app_selection)
        self.right_sw.add(self.appview)

        self.cateview = AppCategoryView(os.path.join(APPCENTER_ROOT, 'cates.json'))
        self.cateview.set_status_from_view(self.appview)
        self.cateview.update_cate_model()
        self.cate_selection = self.cateview.get_selection()
        self.cate_selection.connect('changed', self.on_category_changed)
        self.left_sw.add(self.cateview)

        self.update_timestamp()
        self.show_all()

        UPDATE_SETTING.set_value(False)
        UPDATE_SETTING.connect_notify(self.on_have_update, data=None)

        thread.start_new_thread(self.check_update, ())
        GObject.timeout_add(60000, self.update_timestamp)

        self.add_start(self.main_vbox)

        self.connect('realize', self.setup_ui_tasks)

    def setup_ui_tasks(self, widget):
        self.cateview.expand_all()

    def update_timestamp(self):
        self.time_label.set_text(_('Last synced:') + ' ' + utdata.get_last_synced(APPCENTER_ROOT))
        return True

    @post_ui
    def on_have_update(self, *args):
        log.debug("on_have_update")
        if UPDATE_SETTING.get_value():
            dialog = QuestionDialog(_('New application data available, would you like to update?'))
            response = dialog.run()
            dialog.destroy()

            if response == Gtk.ResponseType.YES:
                dialog = FetchingDialog(get_app_data_url(), self.get_toplevel())
                dialog.connect('destroy', self.on_app_data_downloaded)
                dialog.run()
                dialog.destroy()

    def check_update(self):
        try:
            return utdata.check_update_function(self.url, APPCENTER_ROOT, \
                                            UPDATE_SETTING, VERSION_SETTING, \
                                            auto=True)
        except Exception, error:
            log.error(error)

    def on_app_selection(self, widget, data=None):
        model, iter = widget.get_selected()
        if iter:
            appview = widget.get_tree_view()
            appview.set_as_read(iter, model)
            self.cateview.update_selected_item()

    @log_func(log)
    def on_category_changed(self, widget, data=None):
        model, iter = widget.get_selected()
        cateview = widget.get_tree_view()

        if iter:
            path = model.get_path(iter).to_string()
            only_installed = False

            if path == '0':
                only_installed = True
                self.appview.set_filter(None)
            elif path == '1':
                self.appview.set_filter(None)
            else:
                self.appview.set_filter(model[iter][cateview.CATE_ID])

            self.appview.update_model(only_installed=only_installed)

    def deep_update(self):
        self.package_worker.update_apt_cache(True)
        self.update_app_data()

    def on_apply_button_clicked(self, widget, data=None):
        @log_func(log)
        def on_install_finished(transaction, status, kwargs):
            to_add, to_rm = kwargs['add_and_rm']
            if to_rm:
                worker = AptWorker(self.get_toplevel(),
                                   finish_handler=self.on_package_work_finished,
                                   data=kwargs)
                worker.remove_packages(to_rm)
            else:
               self.on_package_work_finished(None, None, kwargs)

        to_rm = self.appview.to_rm
        to_add = self.appview.to_add

        log.debug("on_apply_button_clicked: to_rm: %s, to_add: %s" % (to_rm, to_add))

        if to_add or to_rm:
            set_busy(self)

            if to_add:
                worker = AptWorker(self.get_toplevel(),
                                   finish_handler=on_install_finished,
                                   data={'add_and_rm': (to_add, to_rm),
                                         'parent': self})
                worker.install_packages(to_add)
            else:
                on_install_finished(None, None, 
                                   {'add_and_rm': (to_add, to_rm),
                                         'parent': self})

    @log_func(log)
    def on_package_work_finished(self, transaction, status, kwargs):
        to_add, to_rm = kwargs['add_and_rm']
        parent = kwargs['parent']

        AptWorker.update_apt_cache(init=True)

        self.emit('call', 'ubuntutweak.modules.updatemanager', 'update_list', {})

        self.appview.to_add = []
        self.appview.to_rm = []
        self.on_category_changed(self.cateview.get_selection())
        self.apply_button.set_sensitive(False)
        unset_busy(parent)

    def on_sync_button_clicked(self, widget):
        dialog = CheckUpdateDialog(widget.get_toplevel(), self.url)
        dialog.run()
        dialog.destroy()
        if dialog.status == True:
            dialog = QuestionDialog(_("Update available, would you like to update?"))
            response = dialog.run()
            dialog.destroy()
            if response == Gtk.ResponseType.YES:
                dialog = FetchingDialog(get_app_data_url(), self.get_toplevel())
                dialog.connect('destroy', self.on_app_data_downloaded)
                dialog.run()
                dialog.destroy()
        elif dialog.error == True:
            ErrorDialog(_("Network Error, please check your network connection - or the remote server may be down.")).launch()
        else:
            utdata.save_synced_timestamp(APPCENTER_ROOT)
            self.update_timestamp()
            InfoDialog(_("No update available.")).launch()

    def on_app_data_downloaded(self, widget):
        log.debug("on_app_data_downloaded")
        path = widget.get_downloaded_file()
        tarfile = utdata.create_tarfile(path)

        if tarfile.is_valid():
            tarfile.extract(consts.CONFIG_ROOT)
            self.update_app_data()
            utdata.save_synced_timestamp(APPCENTER_ROOT)
            self.update_timestamp()
        else:
            ErrorDialog(_('An error occurred while downloading the file.')).launch()

    def update_app_data(self):
        self.appview.update_model()
        self.cateview.update_cate_model()
        self.cateview.expand_all()

    def on_app_status_changed(self, widget, i):
        if i:
            self.apply_button.set_sensitive(True)
        else:
            self.apply_button.set_sensitive(False)

########NEW FILE########
__FILENAME__ = desktoprecovery
# Ubuntu Tweak - Ubuntu Configuration Tool
#
# Copyright (C) 2007-2011 Tualatrix Chou <tualatrix@gmail.com>
#
# Ubuntu Tweak is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# Ubuntu Tweak is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Ubuntu Tweak; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA

import os
import glob
import time
import logging
from subprocess import Popen, PIPE

import dbus
from gi.repository import GObject, Gtk, Gdk, GdkPixbuf

from ubuntutweak.modules import TweakModule
from ubuntutweak.utils import icon
from ubuntutweak.gui.dialogs import InfoDialog, QuestionDialog, ErrorDialog
from ubuntutweak.gui.dialogs import ProcessDialog
from ubuntutweak.gui.gtk import post_ui
from ubuntutweak.common.consts import CONFIG_ROOT

log = logging.getLogger('DesktopRecovery')

def build_backup_prefix(directory):
    name_prefix = os.path.join(CONFIG_ROOT, 'desktoprecovery', directory[1:]) + '/'

    log.debug("build_backup_prefix: %s" % name_prefix)

    if not os.path.exists(name_prefix):
        os.makedirs(name_prefix)
    return name_prefix


def build_backup_path(directory, name):
    name_prefix = build_backup_prefix(directory)
    return name_prefix + name + '.xml'


def do_backup_task(directory, name):
    backup_name = build_backup_path(directory, name)
    log.debug("the backup path is %s" % backup_name)
    backup_file = open(backup_name, 'w')
    process = Popen(['gconftool-2', '--dump', directory], stdout=backup_file)
    return process.communicate()


def do_recover_task(path):
    process = Popen(['gconftool-2', '--load', path])
    log.debug('Start setting recovery: %s' % path)
    return process.communicate()


def do_reset_task(directory):
    process = Popen(['gconftool-2', '--recursive-unset', directory])
    log.debug('Start setting reset: %s' % directory)
    return process.communicate()


class CateView(Gtk.TreeView):
    (COLUMN_ICON,
     COLUMN_DIR,
     COLUMN_TITLE
    ) = range(3)

    path_dict = {
        '/apps': _('Applications'),
        '/desktop': _('Desktop'),
        '/system': _('System'),
    }

    def __init__(self):
        GObject.GObject.__init__(self)

        self.set_rules_hint(True)
        self.model = self._create_model()
        self.set_model(self.model)
        self._add_columns()
        self.update_model()

        selection = self.get_selection()
        selection.select_iter(self.model.get_iter_first())

    def _create_model(self):
        '''The model is icon, title and the list reference'''
        model = Gtk.ListStore(
                    GdkPixbuf.Pixbuf,
                    GObject.TYPE_STRING,
                    GObject.TYPE_STRING)

        return model

    def _add_columns(self):
        column = Gtk.TreeViewColumn(_('Category'))

        renderer = Gtk.CellRendererPixbuf()
        column.pack_start(renderer, False)
        column.add_attribute(renderer, 'pixbuf', self.COLUMN_ICON)

        renderer = Gtk.CellRendererText()
        column.pack_start(renderer, True)
        column.set_sort_column_id(self.COLUMN_TITLE)
        column.add_attribute(renderer, 'text', self.COLUMN_TITLE)

        self.append_column(column)

    def update_model(self):
        for path, title in self.path_dict.items():
            pixbuf = icon.get_from_name('folder')
            self.model.append((pixbuf, path, title))


class SettingView(Gtk.TreeView):
    (COLUMN_ICON,
     COLUMN_DIR,
     COLUMN_TITLE
    ) = range(3)

    def __init__(self):
        GObject.GObject.__init__(self)

        self.model = self._create_model()
        self.set_model(self.model)
        self._add_columns()

    def _create_model(self):
        ''' The first is for icon, second is for real path, second is for title (if available)'''
        model = Gtk.ListStore(GdkPixbuf.Pixbuf,
                              GObject.TYPE_STRING,
                              GObject.TYPE_STRING)

        return model

    def _add_columns(self):
        column = Gtk.TreeViewColumn(_('Setting'))

        renderer = Gtk.CellRendererPixbuf()
        column.pack_start(renderer, False)
        column.add_attribute(renderer, 'pixbuf', self.COLUMN_ICON)

        renderer = Gtk.CellRendererText()
        column.pack_start(renderer, True)
        column.set_sort_column_id(self.COLUMN_TITLE)
        column.add_attribute(renderer, 'text', self.COLUMN_TITLE)

        self.append_column(column)

    def update_model(self, directory):
        self.model.clear()

        process = Popen(['gconftool-2', '--all-dirs', directory], stdout=PIPE)
        stdout, stderr = process.communicate()
        if stderr:
            log.error(stderr)
            #TODO raise error or others
            return

        dirlist = stdout.split()
        dirlist.sort()
        for directory in dirlist:
            title = directory.split('/')[-1]

            pixbuf = icon.get_from_name(title, alter='folder')
            self.model.append((pixbuf, directory, title))


class GetTextDialog(QuestionDialog):
    def __init__(self, title='', message='', text=''):
        super(GetTextDialog, self).__init__(title=title, message=message)

        self.text = text

        vbox = self.get_content_area()

        hbox = Gtk.HBox(spacing=12)
        label = Gtk.Label(label=_('Backup Name:'))
        hbox.pack_start(label, False, False, 0)

        self.entry = Gtk.Entry()
        if text:
            self.entry.set_text(text)
        hbox.pack_start(self.entry, True, True, 0)

        vbox.pack_start(hbox, True, True, 0)
        vbox.show_all()

    def destroy(self):
        self.text = self.entry.get_text()
        super(GetTextDialog, self).destroy()

    def set_text(self, text):
        self.entry.set_text(text)

    def get_text(self):
        return self.text


class BackupProgressDialog(ProcessDialog):
    def __init__(self, parent, name, directory):
        self.file_name = name
        self.directory = directory
        self.error = False

        super(BackupProgressDialog, self).__init__(parent=parent)
        self.set_progress_text(_('Backing up...'))

    def run(self):
        GObject.timeout_add(100, self.process_data)
        return super(ProcessDialog, self).run()

    @post_ui
    def process_data(self):
        directory = self.directory
        name = self.file_name

        process = Popen(['gconftool-2', '--all-dirs', directory], stdout=PIPE)
        stdout, stderr = process.communicate()
        if stderr:
            log.error(stderr)
            #TODO raise error or others
            self.error = True
            return

        dirlist = stdout.split()
        dirlist.sort()
        totol_backuped = []

        length = len(dirlist)
        for index, subdir in enumerate(dirlist):
            self.set_progress_text(_('Backing up...%s') % subdir)
            self.set_fraction((index + 1.0) / length)

            while Gtk.events_pending():
                Gtk.main_iteration()

            stdout, stderr = do_backup_task(subdir, name)
            if stderr is not None:
                log.error(stderr)
                self.error = True
                break
            else:
                totol_backuped.append(build_backup_path(subdir, name))

        if stderr is None:
            backup_name = build_backup_path(directory, name)
            sum_file = open(backup_name, 'w')
            sum_file.write('\n'.join(totol_backuped))
            sum_file.close()

        self.destroy()


class DesktopRecovery(TweakModule):
    __title__ = _('Desktop Recovery')
    __desc__ = _('Backup and recover your desktop and application settings with ease.\n'
                 'You can also use "Reset" to reset to the system default settings.')
    __icon__ = 'gnome-control-center'
    __category__ = 'desktop'
    __distro__ = ['precise']

    def __init__(self):
        TweakModule.__init__(self, 'desktoprecovery.ui')

        self.setup_backup_model()

        hbox = Gtk.HBox(spacing=12)
        self.add_start(hbox)

        self.cateview = CateView()
        sw = Gtk.ScrolledWindow(shadow_type=Gtk.ShadowType.IN)
        sw.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        sw.add(self.cateview)

        #FIXME it will cause two callback for cateview changed
        self.cateview.connect('button_press_event',
                              self.on_cateview_button_press_event)
        self.cate_selection = self.cateview.get_selection()
        self.cate_selection.connect('changed', self.on_cateview_changed)
        hbox.pack_start(sw, False, False, 0)

        vpaned = Gtk.VPaned()
        hbox.pack_start(vpaned, True, True, 0)

        self.settingview = SettingView()
        self.setting_selection = self.settingview.get_selection()
        self.setting_selection.connect('changed', self.on_settingview_changed)
        sw = Gtk.ScrolledWindow(shadow_type=Gtk.ShadowType.IN)
        sw.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        sw.add(self.settingview)
        vpaned.pack1(sw, True, False)

        vpaned.pack2(self.recover_box, False, False)

        self.on_cateview_changed(self.cate_selection)
        self.show_all()

    def setup_backup_model(self):
        model = Gtk.ListStore(GObject.TYPE_STRING,
                              GObject.TYPE_STRING)

        self.backup_combobox.set_model(model)

        cell = Gtk.CellRendererText()
        self.backup_combobox.pack_start(cell, True)
        self.backup_combobox.add_attribute(cell, 'text', 0)

    def update_backup_model(self, directory):
        def file_cmp(f1, f2):
            return cmp(os.stat(f1).st_ctime, os.stat(f2).st_ctime)

        model = self.backup_combobox.get_model()
        model.clear()

        name_prefix = build_backup_prefix(directory)

        file_lsit = glob.glob(name_prefix + '*.xml')
        file_lsit.sort(cmp=file_cmp, reverse=True)

        log.debug('Use glob to find the name_prefix: %s with result: %s' % (name_prefix,
                                                                            str(file_lsit)))

        if file_lsit:
            first_iter = None
            for file_path in file_lsit:
                iter = model.append((os.path.basename(file_path)[:-4],
                                     file_path))

                if first_iter == None:
                    first_iter = iter

            self.backup_combobox.set_active_iter(first_iter)
            self.delete_button.set_sensitive(True)
            self.edit_button.set_sensitive(True)
            self.recover_button.set_sensitive(True)
        else:
            iter = model.append((_('No Backup Yet'), ''))
            self.backup_combobox.set_active_iter(iter)
            self.delete_button.set_sensitive(False)
            self.edit_button.set_sensitive(False)
            self.recover_button.set_sensitive(False)

    def on_cateview_changed(self, widget):
        model, iter = widget.get_selected()
        if iter:
            directory = model.get_value(iter, self.cateview.COLUMN_DIR)
            self.settingview.update_model(directory)

            self.dir_label.set_text(directory)
            self.update_backup_model(directory)

    def on_cateview_button_press_event(self, widget, event):
        if event.type == Gdk.EventType.BUTTON_PRESS and event.button == 1:
            self.on_cateview_changed(self.cate_selection)

    def on_settingview_changed(self, widget):
        model, iter = widget.get_selected()
        if iter:
            directory = model.get_value(iter, self.settingview.COLUMN_DIR)
            self.dir_label.set_text(directory)
            self.update_backup_model(directory)

    def on_backup_button_clicked(self, widget):
        def get_time_stamp():
            return time.strftime('%Y-%m-%d-%H-%M', time.localtime(time.time()))

        directory = self.dir_label.get_text()
        log.debug("Start backing up the dir: %s" % directory)

        # if 1, then root directory
        if directory.count('/') == 1:
            dialog = GetTextDialog(message=_('Backup all settings under "<b>%s</b>"\n'
                                             'Would you like to continue?') % directory,
                                   text=get_time_stamp())

            response = dialog.run()
            dialog.destroy()
            name = dialog.get_text()

            if response == Gtk.ResponseType.YES and name:
                log.debug("Start BackupProgressDialog")
                dialog = BackupProgressDialog(self.get_toplevel(), name, directory)

                dialog.run()
                dialog.destroy()

                if dialog.error == False:
                    self.show_backup_successful_dialog()
                    self.update_backup_model(directory)
                else:
                    self.show_backup_failed_dialog()
        else:
            dialog = GetTextDialog(message=_('Backup settings under "<b>%s</b>"\n'
                                             'Would you like to continue?') % directory,
                                   text=get_time_stamp())
            response = dialog.run()
            dialog.destroy()
            name = dialog.get_text()

            if response == Gtk.ResponseType.YES and name:
                stdout, stderr = do_backup_task(directory, name)

                if stderr is None:
                    self.show_backup_successful_dialog()
                    self.update_backup_model(directory)
                else:
                    self.show_backup_failed_dialog()
                    log.debug("Backup error: %s" % stderr)

    def on_delete_button_clicked(self, widget):
        def try_remove_record_in_root_backup(directory, path):
            rootpath = build_backup_prefix('/'.join(directory.split('/')[:2])) + \
                                           os.path.basename(path)
            if os.path.exists(rootpath):
                lines = open(rootpath).read().split()
                lines.remove(path)

                if len(lines) == 0:
                    os.remove(rootpath)
                else:
                    new = open(rootpath, 'w')
                    new.write('\n'.join(lines))
                    new.close()

        def try_remove_all_subback(path):
            for line in open(path):
                os.remove(line.strip())

        iter = self.backup_combobox.get_active_iter()
        model = self.backup_combobox.get_model()

        directory = self.dir_label.get_text()

        path = model.get_value(iter, 1)
        if directory.count('/') == 2:
            dialog = QuestionDialog(message=_('Would you like to delete the backup '
                                      '"<b>%s/%s</b>"?') %
                                      (directory, os.path.basename(path)[:-4]))
        else:
            dialog = QuestionDialog(message=_('Would you like to delete the backup of'
                                      ' all "<b>%(setting_name)s</b>" settings named "<b>%(backup_name)s</b>"?') % \
                                      {'setting_name': directory,
                                       'backup_name': os.path.basename(path)[:-4]})
        response = dialog.run()
        dialog.destroy()
        if response == Gtk.ResponseType.YES:
            if directory.count('/') == 2:
                try_remove_record_in_root_backup(directory, path)
            else:
                try_remove_all_subback(path)

            os.remove(path)
            self.update_backup_model(directory)

    def on_recover_button_clicked(self, widget):
        iter = self.backup_combobox.get_active_iter()
        model = self.backup_combobox.get_model()
        directory = self.dir_label.get_text()
        path = model.get_value(iter, 1)

        if directory.count('/') == 2:
            message = _('Would you like to recover the backup "<b>%s/%s</b>"?') % (
                        directory, os.path.basename(path)[:-4])
        else:
            message = _('Would you like to recover the backup of all '
                        '"<b>%(setting_name)s</b>" settings named "<b>%(backup_name)s</b>"?') % \
                        {'setting_name': directory,
                         'backup_name': os.path.basename(path)[:-4]}

        addon_message = _('<b>NOTES</b>: While recovering, your desktop may be unresponsive for a moment.')

        dialog = QuestionDialog(message=message + '\n\n' + addon_message)
        response = dialog.run()
        dialog.destroy()

        if response == Gtk.ResponseType.YES:
            if directory.count('/') == 1:
                for line in open(path):
                    stdout, stderr = do_recover_task(line.strip())
            else:
                stdout, stderr = do_recover_task(path)

            if stderr:
                log.error(stderr)
                #TODO raise error or others
                return
            self._show_successful_dialog(title=_('Recovery Successful!'),
                 message=_('You may need to restart your desktop for changes to take effect'))

    def _show_successful_dialog(self, title, message):
        dialog = InfoDialog(title=title, message=message)

        button = Gtk.Button(_('_Logout'))
        button.set_use_underline(True)
        button.connect('clicked', self.on_logout_button_clicked, dialog)
        dialog.add_option_button(button)

        dialog.launch()

    def on_reset_button_clicked(self, widget):
        iter = self.backup_combobox.get_active_iter()
        model = self.backup_combobox.get_model()
        directory = self.dir_label.get_text()

        if directory.count('/') == 2:
            message = _('Would you like to reset settings for "<b>%s</b>"?') % directory
        else:
            message = _('Would you like to reset all settings under "<b>%s</b>"?') % directory

        addon_message = _('<b>NOTES</b>: Whilst resetting, your desktop may be unresponsive for a moment.')

        dialog = QuestionDialog(message=message + '\n\n' + addon_message)
        response = dialog.run()
        dialog.destroy()

        if response == Gtk.ResponseType.YES:
            stdout, stderr = do_reset_task(directory)

            if stderr:
                log.error(stderr)
                #TODO raise error or others
                return
            self._show_successful_dialog(title=_('Reset Successful!'),
                 message=_('You may need to restart your desktop for changes to take effect'))

    def on_logout_button_clicked(self, widget, dialog):
        bus = dbus.SessionBus()
        object = bus.get_object('org.gnome.SessionManager', '/org/gnome/SessionManager')
        object.get_dbus_method('Logout', 'org.gnome.SessionManager')(True)
        dialog.destroy()
        self.emit('call', 'mainwindow', 'destroy', {})

    def on_edit_button_clicked(self, widget):
        def try_rename_record_in_root_backup(directory, old_path, new_path):
            rootpath = build_backup_prefix('/'.join(directory.split('/')[:2])) + \
                                           os.path.basename(path)

            if os.path.exists(rootpath):
                lines = open(rootpath).read().split()
                lines.remove(old_path)
                lines.append(new_path)

                new = open(rootpath, 'w')
                new.write('\n'.join(lines))
                new.close()

        iter = self.backup_combobox.get_active_iter()
        model = self.backup_combobox.get_model()
        directory = self.dir_label.get_text()
        path = model.get_value(iter, 1)

        dialog = GetTextDialog(message=_('Please enter a new name for your backup:'))

        dialog.set_text(os.path.basename(path)[:-4])
        res = dialog.run()
        dialog.destroy()
        new_name = dialog.get_text()
        log.debug('Get the new backup name: %s' % new_name)

        if res == Gtk.ResponseType.YES and new_name:
            # If is root, try to rename all the subdir, then rename itself
            if directory.count('/') == 1:
                totol_renamed = []
                for line in open(path):
                    line = line.strip()
                    dirname = os.path.dirname(line)
                    new_path = os.path.join(dirname, new_name + '.xml')
                    log.debug('Rename backup file from "%s" to "%s"' % (line, new_path))
                    os.rename(line, new_path)
                    totol_renamed.append(new_path)
                sum_file = open(path, 'w')
                sum_file.write('\n'.join(totol_renamed))
                sum_file.close()

            dirname = os.path.dirname(path)
            new_path = os.path.join(dirname, new_name + '.xml')
            log.debug('Rename backup file from "%s" to "%s"' % (path, new_path))
            os.rename(path, new_path)
            try_rename_record_in_root_backup(directory, path, new_path)

        self.update_backup_model(directory)

    def show_backup_successful_dialog(self):
        InfoDialog(title=_("Backup Successful!")).launch()

    def show_backup_failed_dialog(self):
        ErrorDialog(title=_("Backup Failed!")).launch()

########NEW FILE########
__FILENAME__ = filetypemanager
# Ubuntu Tweak - Ubuntu Configuration Tool
#
# Copyright (C) 2007-2011 Tualatrix Chou <tualatrix@gmail.com>
#
# Ubuntu Tweak is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# Ubuntu Tweak is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Ubuntu Tweak; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA

import sys
reload(sys)
sys.setdefaultencoding('utf8')
import os
import logging

from gettext import ngettext

from gi.repository import GObject, Gio, Gtk, Pango, GdkPixbuf
from xdg.DesktopEntry import DesktopEntry

from ubuntutweak.modules  import TweakModule
from ubuntutweak.utils import icon
from ubuntutweak.gui import GuiBuilder
from ubuntutweak.gui.dialogs import ErrorDialog
from ubuntutweak.common.debug import log_func

log = logging.getLogger('FileType')


class CateView(Gtk.TreeView):
    (COLUMN_ICON,
     COLUMN_TITLE,
     COLUMN_CATE) = range(3)

    MIMETYPE = [
        (_('Audio'), 'audio', 'audio-x-generic'), 
        (_('Text'), 'text', 'text-x-generic'),
        (_('Image'), 'image', 'image-x-generic'), 
        (_('Video'), 'video', 'video-x-generic'), 
        (_('Application'), 'application', 'vcard'), 
        (_('All'), 'all', 'application-octet-stream'),
    ]

    def __init__(self):
        GObject.GObject.__init__(self)

        self.set_rules_hint(True)
        self.model = self._create_model()
        self.set_model(self.model)
        self._add_columns()
        self.update_model()

        selection = self.get_selection()
        selection.select_iter(self.model.get_iter_first())
#        self.set_size_request(80, -1)

    def _create_model(self):
        '''The model is icon, title and the list reference'''
        model = Gtk.ListStore(GdkPixbuf.Pixbuf,
                              GObject.TYPE_STRING,
                              GObject.TYPE_STRING)

        return model

    def _add_columns(self):
        column = Gtk.TreeViewColumn(title=_('Categories'))

        renderer = Gtk.CellRendererPixbuf()
        column.pack_start(renderer, False)
        column.add_attribute(renderer, 'pixbuf', self.COLUMN_ICON)

        renderer = Gtk.CellRendererText()
        column.pack_start(renderer, True)
        column.set_sort_column_id(self.COLUMN_TITLE)
        column.add_attribute(renderer, 'text', self.COLUMN_TITLE)

        self.append_column(column)

    def update_model(self):
        for title, cate, icon_name in self.MIMETYPE:
            pixbuf = icon.get_from_name(icon_name)
            self.model.append((pixbuf, title, cate))


class TypeView(Gtk.TreeView):
    update = False

    (TYPE_MIME,
     TYPE_ICON,
     TYPE_DESCRIPTION,
     TYPE_APPICON,
     TYPE_APP) = range(5)

    def __init__(self):
        GObject.GObject.__init__(self)

        self.model = self._create_model()
        self.set_search_column(self.TYPE_DESCRIPTION)
        self.set_model(self.model)
        self.set_rules_hint(True)
        self._add_columns()
        self.model.set_sort_column_id(self.TYPE_DESCRIPTION,
                                      Gtk.SortType.ASCENDING)

#        self.set_size_request(200, -1)
        self.update_model(filter='audio')

    def _create_model(self):
        '''The model is icon, title and the list reference'''
        model = Gtk.ListStore(GObject.TYPE_STRING,
                              GdkPixbuf.Pixbuf,
                              GObject.TYPE_STRING,
                              GdkPixbuf.Pixbuf,
                              GObject.TYPE_STRING)
        
        return model

    def _add_columns(self):
        column = Gtk.TreeViewColumn(_('File Type'))
        column.set_resizable(True)

        renderer = Gtk.CellRendererPixbuf()
        column.pack_start(renderer, False)
        column.add_attribute(renderer, 'pixbuf', self.TYPE_ICON)

        renderer = Gtk.CellRendererText()
        renderer.set_fixed_size(180, -1)
        renderer.set_property('ellipsize', Pango.EllipsizeMode.END)
        column.pack_start(renderer, False)
        column.add_attribute(renderer, 'text', self.TYPE_DESCRIPTION)
        column.set_sort_column_id(self.TYPE_DESCRIPTION)

        self.append_column(column)

        column = Gtk.TreeViewColumn(_('Associated Application'))

        renderer = Gtk.CellRendererPixbuf()
        column.pack_start(renderer, False)
        column.add_attribute(renderer, 'pixbuf', self.TYPE_APPICON)

        renderer = Gtk.CellRendererText()
        column.pack_start(renderer, False)
        column.set_sort_column_id(self.TYPE_APP)
        column.add_attribute(renderer, 'text', self.TYPE_APP)

        self.append_column(column)

    def update_model(self, filter=False, all=False):
        self.model.clear()

        theme = Gtk.IconTheme.get_default()

        for mime_type in Gio.content_types_get_registered():
            if filter and filter != mime_type.split('/')[0]:
                continue

#           TODO why enabling this will make ui freeze even I try to add @post_ui
#            while Gtk.events_pending ():
#                Gtk.main_iteration ()

            pixbuf = icon.get_from_mime_type(mime_type)
            description = Gio.content_type_get_description(mime_type)
            app = Gio.app_info_get_default_for_type(mime_type, False)

            if app:
                appname = app.get_name()
                applogo = icon.get_from_app(app)
            elif all and not app:
                appname = _('None')
                applogo = None
            else:
                continue

            self.model.append((mime_type, pixbuf, description, applogo, appname))

    def update_for_type(self, type):
        self.model.foreach(self.do_update_for_type, type)

    def do_update_for_type(self, model, path, iter, type):
        this_type = model.get_value(iter, self.TYPE_MIME)

        if this_type == type:
            app = Gio.app_info_get_default_for_type(type, False)

            if app:
                appname = app.get_name()
                applogo = icon.get_from_app(app)

                model.set_value(iter, self.TYPE_APPICON, applogo)
                model.set_value(iter, self.TYPE_APP, appname)
            else:
                model.set_value(self.TYPE_APPICON, None)
                model.set_value(self.TYPE_APP, _('None'))


class AddAppDialog(GObject.GObject):
    __gsignals__ = {
        'update': (GObject.SignalFlags.RUN_FIRST,
                   None,
                   (GObject.TYPE_STRING,))
    }

    (ADD_TYPE_APPINFO,
     ADD_TYPE_APPLOGO,
     ADD_TYPE_APPNAME) = range(3)

    def __init__(self, type, parent):
        super(AddAppDialog, self).__init__()

        worker = GuiBuilder('filetypemanager.ui')

        self.dialog = worker.get_object('add_app_dialog')
        self.dialog.set_modal(True)
        self.dialog.set_transient_for(parent)
        self.app_view = worker.get_object('app_view')
        self.setup_treeview()
        self.app_selection = self.app_view.get_selection()
        self.app_selection.connect('changed', self.on_app_selection_changed)

        self.info_label = worker.get_object('info_label')
        self.description_label = worker.get_object('description_label')

        self.info_label.set_markup(_('Open files of type "%s" with:') %
                                   Gio.content_type_get_description(type))

        self.add_button = worker.get_object('add_button')
        self.add_button.connect('clicked', self.on_add_app_button_clicked)

        self.command_entry = worker.get_object('command_entry')
        self.browse_button = worker.get_object('browse_button')
        self.browse_button.connect('clicked', self.on_browse_button_clicked)

    def get_command_or_appinfo(self):
        model, iter = self.app_selection.get_selected()

        if iter:
            app_info = model.get_value(iter, self.ADD_TYPE_APPINFO)
            app_command = app_info.get_executable()
        else:
            app_info = None
            app_command = None

        command = self.command_entry.get_text()

        if app_info and command == app_command:
            return app_info
        else:
            return command

    def on_browse_button_clicked(self, widget):
        dialog = Gtk.FileChooserDialog(_('Choose an application'),
                                       action=Gtk.FileChooserAction.OPEN,
                                       buttons = (Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
                                                  Gtk.STOCK_OPEN, Gtk.ResponseType.ACCEPT))
        dialog.set_current_folder('/usr/bin')

        if dialog.run() == Gtk.ResponseType.ACCEPT:
            self.command_entry.set_text(dialog.get_filename())

        dialog.destroy()

    def on_app_selection_changed(self, widget):
        model, iter = widget.get_selected()
        if iter:
            appinfo = model.get_value(iter, self.ADD_TYPE_APPINFO)
            description = appinfo.get_description()

            if description:
                self.description_label.set_label(description)
            else:
                self.description_label.set_label('')

            self.command_entry.set_text(appinfo.get_executable())

    @log_func(log)
    def on_add_app_button_clicked(self, widget):
        pass

    def setup_treeview(self):
        model = Gtk.ListStore(GObject.GObject,
                              GdkPixbuf.Pixbuf,
                              GObject.TYPE_STRING)

        self.app_view.set_model(model)
        self.app_view.set_headers_visible(False)

        column = Gtk.TreeViewColumn()
        renderer = Gtk.CellRendererPixbuf()
        column.pack_start(renderer, False)
        column.add_attribute(renderer, 'pixbuf', self.ADD_TYPE_APPLOGO)
        
        renderer = Gtk.CellRendererText()
        column.pack_start(renderer, False)
        column.add_attribute(renderer, 'text', self.ADD_TYPE_APPNAME)
        column.set_sort_column_id(self.ADD_TYPE_APPNAME)
        self.app_view.append_column(column)

        app_list = []
        for appinfo in Gio.app_info_get_all():
            if appinfo.supports_files() or appinfo.supports_uris():
                appname = appinfo.get_name()

                if appname not in app_list:
                    app_list.append(appname)
                else:
                    continue

                applogo = icon.get_from_app(appinfo)

                model.append((appinfo, applogo, appname))

    def __getattr__(self, key):
        return getattr(self.dialog, key)


class TypeEditDialog(GObject.GObject):

    __gsignals__ = {
        'update': (GObject.SignalFlags.RUN_FIRST,
                   None,
                   (GObject.TYPE_PYOBJECT,))
    }
    (EDIT_TYPE_ENABLE,
     EDIT_TYPE_TYPE,
     EDIT_TYPE_APPINFO,
     EDIT_TYPE_APPLOGO,
     EDIT_TYPE_APPNAME) = range(5)

    def __init__(self, types, parent):
        super(TypeEditDialog, self).__init__()
        self.types = types

        type_pixbuf = icon.get_from_mime_type(self.types[0], 64)
        worker = GuiBuilder('filetypemanager.ui')

        self.dialog = worker.get_object('type_edit_dialog')
        self.dialog.set_transient_for(parent)
        self.dialog.set_modal(True)
        self.dialog.connect('destroy', self.on_dialog_destroy)

        type_logo = worker.get_object('type_edit_logo')
        type_logo.set_from_pixbuf(type_pixbuf)

        type_label = worker.get_object('type_edit_label')

        if len(self.types) > 1:
            markup_text = ", ".join([Gio.content_type_get_description(filetype)
                                    for filetype in self.types])
        else:
            markup_text = self.types[0]

        type_label.set_markup(ngettext('Select an application to open files of type: <b>%s</b>',
                              'Select an application to open files for these types: <b>%s</b>',
                              len(self.types)) % markup_text)

        self.type_edit_view = worker.get_object('type_edit_view')
        self.setup_treeview()

        add_button = worker.get_object('type_edit_add_button')
        add_button.connect('clicked', self.on_add_button_clicked)

        remove_button = worker.get_object('type_edit_remove_button')
        # remove button should not available in multiple selection
        if len(self.types) > 1:
            remove_button.hide()
        remove_button.connect('clicked', self.on_remove_button_clicked)

        close_button = worker.get_object('type_edit_close_button')
        close_button.connect('clicked', self.on_dialog_destroy)

    @log_func(log)
    def on_add_button_clicked(self, widget):
        dialog = AddAppDialog(self.types[0], widget.get_toplevel())
        if dialog.run() == Gtk.ResponseType.ACCEPT:
            we = dialog.get_command_or_appinfo()

            log.debug("Get get_command_or_appinfo: %s" % we)
            if type(we) == Gio.DesktopAppInfo:
                log.debug("Get DesktopAppInfo: %s" % we)
                app = we
            else:
                desktop_id = self._create_desktop_file_from_command(we)
                app = Gio.DesktopAppInfo.new(desktop_id)

            for filetype in self.types:
                app.set_as_default_for_type(filetype)

            self.update_model()
            self.emit('update', self.types)

        dialog.destroy()

    def _create_desktop_file_from_command(self, command):
        basename = os.path.basename(command)
        path = os.path.expanduser('~/.local/share/applications/%s.desktop' % basename)

        desktop = DesktopEntry()
        desktop.addGroup('Desktop Entry')
        desktop.set('Type', 'Application')
        desktop.set('Version', '1.0')
        desktop.set('Terminal', 'false')
        desktop.set('Exec', command)
        desktop.set('Name', basename)
        desktop.set('X-Ubuntu-Tweak', 'true')
        desktop.write(path)

        return '%s.desktop' % basename

    def on_remove_button_clicked(self, widget):
        model, iter = self.type_edit_view.get_selection().get_selected()

        if iter:
            enabled, mime_type, appinfo = model.get(iter,
                                                    self.EDIT_TYPE_ENABLE,
                                                    self.EDIT_TYPE_TYPE,
                                                    self.EDIT_TYPE_APPINFO)

            log.debug("remove the type: %s for %s, status: %s" % (mime_type,
                                                                  appinfo,
                                                                  enabled))

            # first try to set mime to next app then remove
            if enabled and model.iter_next(iter):
                inner_appinfo = model[model.iter_next(iter)][self.EDIT_TYPE_APPINFO]
                inner_appinfo.set_as_default_for_type(mime_type)

            #TODO if there's only one app assoicated, it will fail
            appinfo.remove_supports_type(mime_type)

            self.update_model()

        self.emit('update', [mime_type])

    def setup_treeview(self):
        model = Gtk.ListStore(GObject.TYPE_BOOLEAN,
                              GObject.TYPE_STRING,
                              GObject.GObject,
                              GdkPixbuf.Pixbuf,
                              GObject.TYPE_STRING)

        self.type_edit_view.set_model(model)
        self.type_edit_view.set_headers_visible(False)

        self.model = model

        column = Gtk.TreeViewColumn()
        renderer = Gtk.CellRendererToggle()
        renderer.connect('toggled', self.on_renderer_toggled)
        renderer.set_radio(True)
        column.pack_start(renderer, False)
        column.add_attribute(renderer, 'active', self.EDIT_TYPE_ENABLE)
        self.type_edit_view.append_column(column)

        column = Gtk.TreeViewColumn()
        renderer = Gtk.CellRendererPixbuf()
        column.pack_start(renderer, False)
        column.add_attribute(renderer, 'pixbuf', self.EDIT_TYPE_APPLOGO)
        
        renderer = Gtk.CellRendererText()
        column.pack_start(renderer, False)
        column.add_attribute(renderer, 'text', self.EDIT_TYPE_APPNAME)
        column.set_sort_column_id(TypeView.TYPE_DESCRIPTION)
        self.type_edit_view.append_column(column)

        self.update_model()

    def update_model(self):
        self.model.clear()

        if len(self.types) > 1:
            app_dict = {}
            default_list = []
            for type in self.types:
                def_app = Gio.app_info_get_default_for_type(type, False)

                for appinfo in Gio.app_info_get_all_for_type(type):
                    appname = appinfo.get_name()
                    if (def_app.get_name() == appname and 
                        appname not in default_list):
                        default_list.append(appname)

                    if not app_dict.has_key(appname):
                        app_dict[appname] = appinfo

            for appname, appinfo in app_dict.items():
                applogo = icon.get_from_app(appinfo)

                if len(default_list) == 1 and appname in default_list:
                    enabled = True
                else:
                    enabled = False

                self.model.append((enabled, '', appinfo, applogo, appname))
        else:
            type = self.types[0]
            def_app = Gio.app_info_get_default_for_type(type, False)

            for appinfo in Gio.app_info_get_all_for_type(type):
                applogo = icon.get_from_app(appinfo)
                appname = appinfo.get_name()

                self.model.append((def_app.get_name() == appname,
                                   type,
                                   appinfo,
                                   applogo,
                                   appname))

    def on_renderer_toggled(self, widget, path):
        model = self.type_edit_view.get_model()
        iter = model.get_iter(path)

        enable, type, appinfo = model.get(iter,
                                          self.EDIT_TYPE_ENABLE,
                                          self.EDIT_TYPE_TYPE,
                                          self.EDIT_TYPE_APPINFO)
        if not enable:
            model.foreach(self.cancenl_last_toggle, None)
            for filetype in self.types:
                appinfo.set_as_default_for_type(filetype)
            model.set_value(iter, self.EDIT_TYPE_ENABLE, not enable)
            self.emit('update', self.types)

    def cancenl_last_toggle(self, model, path, iter, data=None):
        enable = model.get(iter, self.EDIT_TYPE_ENABLE)
        if enable:
            model.set_value(iter, self.EDIT_TYPE_ENABLE, not enable)

    def on_dialog_destroy(self, widget):
        self.destroy()

    def __getattr__(self, key):
        return getattr(self.dialog, key)

class FileTypeManager(TweakModule):
    __title__ = _('File Type Manager')
    __desc__ = _('Manage all registered file types')
    __icon__ = 'application-x-theme'
    __category__ = 'system'

    def __init__(self):
        TweakModule.__init__(self)

        hbox = Gtk.HBox(spacing=12)
        self.add_start(hbox)

        self.cateview = CateView()
        self.cate_selection = self.cateview.get_selection()
        self.cate_selection.connect('changed', self.on_cateview_changed)

        sw = Gtk.ScrolledWindow(shadow_type=Gtk.ShadowType.IN)
        sw.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        sw.add(self.cateview)
        hbox.pack_start(sw, False, False, 0)

        self.typeview = TypeView()
        self.typeview.connect('row-activated', self.on_row_activated)
        self.type_selection = self.typeview.get_selection()
        self.type_selection.set_mode(Gtk.SelectionMode.MULTIPLE)
        self.type_selection.connect('changed', self.on_typeview_changed)
        sw = Gtk.ScrolledWindow(shadow_type=Gtk.ShadowType.IN)
        sw.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        sw.add(self.typeview)
        hbox.pack_start(sw, True, True, 0)

        hbox = Gtk.HBox(spacing=12)
        self.add_start(hbox, False, False, 0)

        self.edit_button = Gtk.Button(stock=Gtk.STOCK_EDIT)
        self.edit_button.connect('clicked', self.on_edit_clicked)
        self.edit_button.set_sensitive(False)
        hbox.pack_end(self.edit_button, False, False, 0)

        self.reset_button = Gtk.Button(label=_('_Reset'))
        self.reset_button.set_use_underline(True)
        self.reset_button.connect('clicked', self.on_reset_clicked)
        self.reset_button.set_sensitive(False)
        hbox.pack_end(self.reset_button, False, False, 0)

        self.show_have_app = Gtk.CheckButton(_('Only show filetypes with associated applications'))
        self.show_have_app.set_active(True)
        self.show_have_app.connect('toggled', self.on_show_all_toggled)
        hbox.pack_start(self.show_have_app, False, False, 5)

        self.show_all()

    def on_row_activated(self, widget, path, col):
        self.on_edit_clicked(widget)

    def on_show_all_toggled(self, widget):
        model, iter = self.cate_selection.get_selected()
        type = False
        if iter:
            type = model.get_value(iter, CateView.COLUMN_CATE)
            self.set_update_mode(type)

    def on_cateview_changed(self, widget):
        model, iter = widget.get_selected()
        if iter:
            type = model.get_value(iter, CateView.COLUMN_CATE)
            self.set_update_mode(type)

    def on_typeview_changed(self, widget):
        model, rows = widget.get_selected_rows()
        if len(rows) > 0:
            self.edit_button.set_sensitive(True)
            self.reset_button.set_sensitive(True)
        else:
            self.edit_button.set_sensitive(False)
            self.reset_button.set_sensitive(False)

    def on_reset_clicked(self, widget):
        model, rows = self.type_selection.get_selected_rows()
        if len(rows) > 0:
            types = []
            for path in rows:
                mime_type = model[model.get_iter(path)][TypeView.TYPE_MIME]
                Gio.AppInfo.reset_type_associations(mime_type)
                types.append(mime_type)

            self.on_mime_type_update(None, types)

    def on_edit_clicked(self, widget):
        model, rows = self.type_selection.get_selected_rows()
        if len(rows) > 0:
            types = []
            for path in rows:
                iter = model.get_iter(path)
                types.append(model.get_value(iter, TypeView.TYPE_MIME))

            dialog = TypeEditDialog(types, self.get_toplevel())
            dialog.connect('update', self.on_mime_type_update)

            dialog.show()
        else:
            return

    def on_mime_type_update(self, widget, types):
        log.debug("on_mime_type_update: %s" % types)

        for filetype in types:
            self.typeview.update_for_type(filetype)

    def set_update_mode(self, type):
        if type == 'all':
            self.typeview.update_model(all=not self.show_have_app.get_active())
        else:
            self.typeview.update_model(filter=type,
                                       all=not self.show_have_app.get_active())

########NEW FILE########
__FILENAME__ = quicklists
# Ubuntu Tweak - Ubuntu Configuration Tool
#
# Copyright (C) 2012 Tualatrix Chou <tualatrix@gmail.com>
#
# Ubuntu Tweak is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# Ubuntu Tweak is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Ubuntu Tweak; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA

import os
import re
import time
import logging
import shutil

from gi.repository import GObject, Gtk
from xdg.DesktopEntry import DesktopEntry

from ubuntutweak import system
from ubuntutweak.common.debug import log_func, log_traceback
from ubuntutweak.modules  import TweakModule
from ubuntutweak.settings.gsettings import GSetting
from ubuntutweak.gui.dialogs import QuestionDialog
from ubuntutweak.utils import icon

log = logging.getLogger('QuickLists')



def save_to_user(func):
    def func_wrapper(self, *args, **kwargs):
        launcher_setting = GSetting('com.canonical.Unity.Launcher.favorites')
        is_user_desktop_file = self.is_user_desktop_file()
        if not is_user_desktop_file:
            log.debug("Copy %s to user folder, then write it" % self.filename)
            shutil.copy(self.get_system_desktop_file(),
                        self.get_user_desktop_file())
            self.filename = self.get_user_desktop_file()
            self.parse(self.filename)

        func(self, *args, **kwargs)

        if not is_user_desktop_file:
            current_list = launcher_setting.get_value()
            try:
                index = current_list.index(self.get_system_desktop_file())
            except Exception, e:
                log.debug(e)
                index = current_list.index(os.path.basename(self.get_system_desktop_file()))

            current_list[index] = self.filename

            launcher_setting.set_value(current_list)
            log.debug("current_list: %s" % current_list)
            log.debug("Now set the current list")

    return func_wrapper


class NewDesktopEntry(DesktopEntry):
    shortcuts_key = 'X-Ayatana-Desktop-Shortcuts'
    actions_key = 'Actions'
    user_folder = os.path.expanduser('~/.local/share/applications')
    system_folder = '/usr/share/applications'
    mode = ''

    def __init__(self, filename):
        DesktopEntry.__init__(self, filename)
        log.debug('NewDesktopEntry: %s' % filename)
        if self.get(self.shortcuts_key):
            self.mode = self.shortcuts_key
        else:
            self.mode = self.actions_key

    def get_actions(self):
        enabled_actions = self.get(self.mode, list=True)

        actions = self.groups()
        actions.remove(self.defaultGroup)

        for action in actions: 
            action_name = self.get_action_name(action)
            if action_name not in enabled_actions:
                enabled_actions.append(action_name)

        return enabled_actions

    def get_action_name(self, action):
        if self.mode == self.shortcuts_key:
            return action.split()[0]
        else:
            return action.split()[-1]

    def add_action_group(self, action):
        self.addGroup(self.get_action_full_name(action))

    def get_action_full_name(self, action):
        if self.mode == self.shortcuts_key:
            return u'%s Shortcut Group' % action
        else:
            return u'Desktop Action %s' % action

    @log_func(log)
    def get_name_by_action(self, action):
        return self.get('Name', self.get_action_full_name(action), locale=True)

    @log_func(log)
    def get_exec_by_action(self, action):
        return self.get('Exec', self.get_action_full_name(action))

    @log_func(log)
    @save_to_user
    def set_name_by_action(self, action, name):
        # First there's must be at least one non-locale value
        if not self.get('Name', name):
            self.set('Name', name, group=self.get_action_full_name(action))
        self.set('Name', name, group=self.get_action_full_name(action), locale=True)
        self.write()

    @log_func(log)
    @save_to_user
    def set_exec_by_action(self, action, cmd):
        self.set('Exec', cmd, group=self.get_action_full_name(action))
        self.write()

    @log_func(log)
    def is_action_visiable(self, action):
        enabled_actions = self.get(self.mode, list=True)
        log.debug('All visiable actions: %s' % enabled_actions)
        return action in enabled_actions

    @log_func(log)
    @save_to_user
    def remove_action(self, action):
        actions = self.get(self.mode, list=True)
        log.debug("remove_action %s from %s" % (action, actions))
        #TODO if not local
        if action in actions:
            actions.remove(action)
            self.set(self.mode, ";".join(actions))
        self.removeGroup(self.get_action_full_name(action))
        self.write()

    @log_func(log)
    @save_to_user
    def set_action_enabled(self, action, enabled):
        actions = self.get(self.mode, list=True)

        if action not in actions and enabled:
            log.debug("Group is not in actions and will set it to True")
            actions.append(action)
            self.set(self.mode, ";".join(actions))
            self.write()
        elif action in actions and enabled is False:
            log.debug("Group is in actions and will set it to False")
            actions.remove(action)
            self.set(self.mode, ";".join(actions))
            self.write()

    @log_func(log)
    @save_to_user
    def reorder_actions(self, actions):
        visiable_actions = []
        for action in actions:
            if self.is_action_visiable(action):
                visiable_actions.append(action)

        if visiable_actions:
            self.set(self.mode, ";".join(visiable_actions))
            self.write()

    def is_user_desktop_file(self):
        return self.filename.startswith(self.user_folder)

    def _has_system_desktop_file(self):
        return os.path.exists(os.path.join(self.system_folder, os.path.basename(self.filename)))

    def get_system_desktop_file(self):
        if self._has_system_desktop_file():
            return os.path.join(self.system_folder, os.path.basename(self.filename))
        else:
            return ''

    def get_user_desktop_file(self):
        return os.path.join(self.user_folder, os.path.basename(self.filename))

    @log_func(log)
    def can_reset(self):
        return self.is_user_desktop_file() and self._has_system_desktop_file()

    @log_func(log)
    def reset(self):
        if self.can_reset():
            shutil.copy(self.get_system_desktop_file(),
                        self.get_user_desktop_file())
            # Parse a file will not destroy the old content, so destroy manually
            self.content = dict()
            self.parse(self.filename)


class QuickLists(TweakModule):
    __title__ = _('QuickLists Editor')
    __desc__ = _('Unity Launcher QuickLists Editor')
    __icon__ = 'plugin-unityshell'
    __category__ = 'desktop'
    __desktop__ = ['ubuntu', 'ubuntu-2d']
    __utactive__ = True

    (DESKTOP_FILE,
     DESKTOP_ICON,
     DESKTOP_NAME,
     DESKTOP_ENTRY) = range(4)

    (ACTION_NAME,
     ACTION_FULLNAME,
     ACTION_EXEC,
     ACTION_ENABLED,
     ACTION_ENTRY) = range(5)

    QUANTAL_SPECIFIC_ITEMS = {
        'unity://running-apps': _('Running Apps'),
        'unity://expo-icon': _('Workspace Switcher'),
        'unity://devices': _('Devices')
    }

    UNITY_WEBAPPS_ACTION_PATTERN = re.compile('^S\d{1}$')

    def __init__(self):
        TweakModule.__init__(self, 'quicklists.ui')

        self.launcher_setting = GSetting('com.canonical.Unity.Launcher.favorites')
        self.launcher_setting.connect_notify(self.update_launch_icon_model)

        self.action_view.get_selection().connect('changed', self.on_action_selection_changed)

        self.update_launch_icon_model()

        self.add_start(self.main_paned)

    @log_func(log)
    def update_launch_icon_model(self, *args):
        self.icon_model.clear()

        for desktop_file in self.launcher_setting.get_value():
            log.debug('Processing with "%s"...' % desktop_file)
            if desktop_file.startswith('/') and os.path.exists(desktop_file):
                path = desktop_file
            else:
                if desktop_file.startswith('application://'):
                    desktop_file = desktop_file.split('application://')[1]
                    log.debug("Desktop file for quantal: %s" % desktop_file)

                user_path = os.path.join(NewDesktopEntry.user_folder, desktop_file)
                system_path = os.path.join(NewDesktopEntry.system_folder, desktop_file)

                if os.path.exists(user_path):
                    path = user_path
                elif os.path.exists(system_path):
                    path = system_path
                else:
                    path = desktop_file

            try:
                entry = NewDesktopEntry(path)

                self.icon_model.append((path,
                                        icon.get_from_name(entry.getIcon(), size=32),
                                        entry.getName(),
                                        entry))
            except Exception, e:
                log_traceback(log)
                if path in self.QUANTAL_SPECIFIC_ITEMS.keys():
                    self.icon_model.append((path,
                                            icon.get_from_name('plugin-unityshell', size=32),
                                            self.QUANTAL_SPECIFIC_ITEMS[path],
                                            None))

        first_iter = self.icon_model.get_iter_first()
        if first_iter:
            self.icon_view.get_selection().select_iter(first_iter)

    def get_current_action_and_entry(self):
        model, iter = self.action_view.get_selection().get_selected()
        if iter:
            action = model[iter][self.ACTION_NAME]
            entry = model[iter][self.ACTION_ENTRY]
            return action, entry
        else:
            return None, None

    def get_current_entry(self):
        model, iter = self.icon_view.get_selection().get_selected()
        if iter:
            return model[iter][self.DESKTOP_ENTRY]
        else:
            return None

    def on_action_selection_changed(self, widget):
        action, entry = self.get_current_action_and_entry()
        if action and entry:
            log.debug("Select the action: %s\n"
                      "\t\t\tName: %s\n"
                      "\t\t\tExec: %s\n"
                      "\t\t\tVisiable: %s" % (action,
                                          entry.get_name_by_action(action),
                                          entry.get_exec_by_action(action),
                                          entry.is_action_visiable(action)))
            self.remove_action_button.set_sensitive(True)
            self.name_entry.set_text(entry.get_name_by_action(action))
            self.cmd_entry.set_text(entry.get_exec_by_action(action))
            self.name_entry.set_sensitive(True)
            self.cmd_entry.set_sensitive(True)
        else:
            self.remove_action_button.set_sensitive(False)
            self.name_entry.set_text('')
            self.cmd_entry.set_text('')
            self.name_entry.set_sensitive(False)
            self.cmd_entry.set_sensitive(False)

    @log_func(log)
    def on_icon_view_selection_changed(self, widget, path=None):
        model, iter = widget.get_selected()
        if iter:
            self.action_model.clear()
            self.add_action_button.set_sensitive(True)

            entry = model[iter][self.DESKTOP_ENTRY]
            if entry:
                for action in entry.get_actions():
                    if not self.UNITY_WEBAPPS_ACTION_PATTERN.search(action):
                        self.action_model.append((action,
                                    entry.get_name_by_action(action),
                                    entry.get_exec_by_action(action),
                                    entry.is_action_visiable(action),
                                    entry))
                self.redo_action_button.set_sensitive(True)
                self.action_view.columns_autosize()
                if not path:
                    first_iter = self.action_model.get_iter_first()
                    if first_iter:
                        self.action_view.get_selection().select_iter(first_iter)
                else:
                    iter = self.action_model.get_iter(path)
                    if iter:
                        self.action_view.get_selection().select_iter(iter)
            else:
                self.add_action_button.set_sensitive(False)
                self.redo_action_button.set_sensitive(False)
        else:
            self.add_action_button.set_sensitive(False)
            self.redo_action_button.set_sensitive(False)

    @log_func(log)
    def on_add_action_button_clicked(self, widget):
        entry = self.get_current_entry()
        model, icon_iter = self.icon_view.get_selection().get_selected()
        icon_path = self.icon_model.get_path(icon_iter)

        if entry:
            first = not entry.is_user_desktop_file()
            # I think 99 is enough, right?
            action_names = entry.get_actions()
            for i in range(99):
                next_name = 'Action%d' % i
                if next_name in action_names:
                    continue
                else:
                    break

            entry.add_action_group(next_name)
            entry.set_action_enabled(next_name, True)
            # Because it may be not the user desktop file, so need icon_iter to select
            icon_iter = self.icon_model.get_iter(icon_path)
            if icon_iter:
                self.icon_view.get_selection().select_iter(icon_iter)

            self.select_last_action(first=first)
            self.name_entry.grab_focus()

    @log_func(log)
    def on_remove_action_button_clicked(self, widget):
        model, iter = self.action_view.get_selection().get_selected()
        if iter:
            action_name = model[iter][self.ACTION_NAME]
            entry = model[iter][self.ACTION_ENTRY]
            log.debug("Try to remove action: %s" % action_name)
            entry.remove_action(action_name)
            log.debug('Remove: %s succcessfully' % action_name)
            model.remove(iter)
            self.select_last_action(first=True)

    def select_last_action(self, first=False):
        if first:
            last_path = len(self.action_model) - 1
        else:
            last_path = len(self.action_model)

        if last_path >= 0:
            self.on_icon_view_selection_changed(self.icon_view.get_selection(), path=last_path)

    @log_func(log)
    def on_enable_action_render(self, render, path):
        model = self.action_model
        iter = model.get_iter(path)
        entry = model[iter][self.ACTION_ENTRY]
        action = model[iter][self.ACTION_NAME]
        is_enalbed = not model[iter][self.ACTION_ENABLED]
        entry.set_action_enabled(action, is_enalbed)
        model[iter][self.ACTION_ENABLED] = is_enalbed

    @log_func(log)
    def on_redo_action_button_clicked(self, widget):
        model, iter = self.icon_view.get_selection().get_selected()
        if iter:
            name = model[iter][self.DESKTOP_NAME]

            dialog = QuestionDialog(title=_('Would you like to reset "%s"?') % name,
                                    message=_('If you continue, the actions of %s will be set to default.') % name)
            response = dialog.run()
            dialog.destroy()

            if response == Gtk.ResponseType.YES:
                entry = model[iter][self.DESKTOP_ENTRY]
#                log.debug("Before reset the actions is: %s" % entry.get_actions())
                entry.reset()
                log.debug("After reset the actions is: %s" % entry.get_actions())
                self.on_icon_view_selection_changed(self.icon_view.get_selection())

    @log_func(log)
    def on_icon_reset_button_clicked(self, widget):
        dialog = QuestionDialog(title=_("Would you like to reset the launcher items?"),
                                message=_('If you continue, launcher will be set to default and all your current items will be lost.'))
        response = dialog.run()
        dialog.destroy()

        if response == Gtk.ResponseType.YES:
            self.launcher_setting.set_value(self.launcher_setting.get_schema_value())

    def on_icon_reordered(self, model, path, iter):
        GObject.idle_add(self._do_icon_reorder)

    def on_action_reordered(self, model, path, iter):
        GObject.idle_add(self._do_action_reorder)

    def _do_icon_reorder(self):
        new_order = []
        for row in self.icon_model:
            if system.CODENAME == 'precise':
                new_order.append(row[self.DESKTOP_FILE])
            else:
                if not row[self.DESKTOP_FILE].startswith('unity://'):
                    new_order.append('application://%s' % os.path.basename(row[self.DESKTOP_FILE]))
                else:
                    new_order.append(row[self.DESKTOP_FILE])

        if new_order != self.launcher_setting.get_value():
            log.debug("Order changed")
            self.launcher_setting.set_value(new_order)
        else:
            log.debug("Order is not changed, pass")

    def _do_action_reorder(self):
        new_order = []
        for row in self.action_model:
            new_order.append(row[self.ACTION_NAME])
            entry = row[self.ACTION_ENTRY]

        if new_order != entry.get_actions():
            log.debug("Action order changed")
            entry.reorder_actions(new_order)
        else:
            log.debug("Action order is not changed, pass")

    def on_name_and_entry_changed(self, widget):
        action, entry = self.get_current_action_and_entry()

        if action and entry:
            self.save_button.set_sensitive(self.name_entry.get_text() != entry.get_name_by_action(action) or \
                    self.cmd_entry.get_text() != entry.get_exec_by_action(action))
        else:
            self.save_button.set_sensitive(self.name_entry.get_text() and self.cmd_entry.get_text())

    def on_save_button_clicked(self, widget):
        action, entry = self.get_current_action_and_entry()
        if action and entry:
            entry.set_name_by_action(action, self.name_entry.get_text())
            entry.set_exec_by_action(action, self.cmd_entry.get_text())
            model, iter = self.action_view.get_selection().get_selected()
            path = self.action_model.get_path(iter)
            self.on_icon_view_selection_changed(self.icon_view.get_selection(), path)

########NEW FILE########
__FILENAME__ = scripts
# Ubuntu Tweak - Ubuntu Configuration Tool
#
# Copyright (C) 2007-2012 Tualatrix Chou <tualatrix@gmail.com>
#
# Ubuntu Tweak is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# Ubuntu Tweak is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Ubuntu Tweak; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA

import os
import stat
import shutil
import logging
import platform

from gi.repository import Gtk, GObject

from ubuntutweak.modules  import TweakModule
from ubuntutweak.utils import icon
from ubuntutweak import system
from ubuntutweak.common.consts import DATA_DIR, CONFIG_ROOT
from ubuntutweak.gui.treeviews import DirView, FlatView
from ubuntutweak.gui.dialogs import QuestionDialog

log = logging.getLogger('Script')


class AbstractScripts(object):
    system_dir = os.path.join(CONFIG_ROOT, 'scripts')

    if int(platform.dist()[1][0:2]) >= 13:
        user_dir = os.path.expanduser('~/.local/share/nautilus/scripts')
    else:
        user_dir = os.path.join(os.getenv('HOME'), '.gnome2', 'nautilus-scripts')


class DefaultScripts(AbstractScripts):
    '''This class use to create the default scripts'''
    scripts = {
            'create-launcher': _('Create Launcher ...'),
            'copy-to': _('Copy to ...'),
            'copy-to-desktop': _('Copy to Desktop'),
            'copy-to-download': _('Copy to Download'),
            'copy-to-home': _('Copy to Home'),
            'check-md5-sum': _('Check md5 sum'),
            'compress-pdf': _('Compress PDF'),
            'move-to': _('Move to ...'),
            'move-to-desktop': _('Move to Desktop'),
            'move-to-download': _('Move to Download'),
            'move-to-home': _('Move to Home'),
            'hardlink-to': _('Create hardlink to ...'),
            'link-to': _('Link to ...'),
            'link-to-desktop': _('Link to Desktop'),
            'link-to-download': _('Link to Download'),
            'link-to-home': _('Link to Home'),
            'open-with-your-favourite-text-editor': _('Open with your favourite text editor'),
            'open-with-your-favourite-text-editor-as-root': _('Open with your favourite text editor (as root)'),
            'browse-as-root': _('Browse as root'),
            'search-in-current': _('Search in current folder'),
            'convert-image-to-jpg': _('Convert image to JPG'),
            'convert-image-to-png': _('Convert image to PNG'),
            'convert-image-to-gif': _('Convert image to GIF'),
            'set-image-as-wallpaper': _('Set image as wallpaper'),
            'make-hard-shadow-to-image': _('Make hard shadow to image'),
            }

    def create(self):
        if not os.path.exists(self.system_dir):
            os.makedirs(self.system_dir)
        for file, des in self.scripts.items():
            realname = '%s' % des
            if not os.path.exists(os.path.join(self.system_dir,realname)):
                shutil.copy(os.path.join(DATA_DIR, 'scripts/%s' % file), os.path.join(self.system_dir,realname))

    def remove(self):
        if not os.path.exists(self.system_dir):
            return
        if os.path.isdir(self.system_dir):
            for root, dirs, files in os.walk(self.system_dir, topdown=False):
                for name in files:
                    os.remove(os.path.join(root, name))
                for name in dirs:
                    os.rmdir(os.path.join(root, name))
                    os.rmdir(self.system_dir)
        else:
            os.unlink(self.system_dir)
        return


class EnableScripts(DirView, AbstractScripts):
    '''The treeview to display the enable scripts'''
    type = _('Enabled Scripts')

    (COLUMN_ICON,
     COLUMN_TITLE,
     COLUMN_PATH,
     COLUMN_EDITABLE) = range(4)

    def __init__(self):
        DirView.__init__(self, self.user_dir)

    def do_update_model(self, dir, iter):
        for item in os.listdir(dir):
            fullname = os.path.join(dir, item)
            pixbuf = icon.guess_from_path(fullname)

            child_iter = self.model.append(iter,
                                           (pixbuf, os.path.basename(fullname),
                                            fullname, False))

            if os.path.isdir(fullname):
                self.do_update_model(fullname, child_iter)
            else:
                if not os.access(fullname, os.X_OK):
                    try:
                        os.chmod(fullname, stat.S_IRWXU)
                    except:
                        pass


class DisableScripts(FlatView, AbstractScripts):
    '''The treeview to display the system template'''
    type = _('Disabled Scripts')

    def __init__(self):
        FlatView.__init__(self, self.system_dir, self.user_dir)


class Scripts(TweakModule, AbstractScripts):
    __title__  = _('Scripts')
    __desc__  = _("Scripts can be used to complete all kinds of tasks.\n"
                  "You can drag and drop scripts here from File Manager.\n"
                  "'Scripts' will then be added to the context menu.")
    __icon__ = 'text-x-script'
    __utactive__ = True
    __category__ = 'personal'

    def __init__(self):
        TweakModule.__init__(self, 'templates.ui')

        self.default = DefaultScripts()
        self.config_test()

        self.enable_scripts = EnableScripts()
        self.sw1.add(self.enable_scripts)

        self.disable_scripts = DisableScripts()
        self.sw2.add(self.disable_scripts)

        self.enable_scripts.connect('drag_data_received', self.on_enable_drag_data_received)
        self.enable_scripts.connect('deleted', self.on_enable_deleted)
        self.disable_scripts.connect('drag_data_received', self.on_disable_drag_data_received)

        self.add_start(self.hbox1)

        hbox = Gtk.HBox(spacing=0)
        self.add_start(hbox, False, False, 0)

        button = Gtk.Button(_('Rebuild System Scripts'))
        button.connect('clicked', self.on_rebuild_clicked)
        hbox.pack_end(button, False, False, 5)

    def on_enable_deleted(self, widget):
        self.disable_scripts.update_model()

    def on_enable_drag_data_received(self, treeview, context, x, y, selection, info, etime):
        self.disable_scripts.update_model()

    def on_disable_drag_data_received(self, treeview, context, x, y, selection, info, etime):
        self.enable_scripts.update_model()

    def on_rebuild_clicked(self, widget):
        dialog = QuestionDialog(message=_('This will delete all disabled scripts.\nDo you wish to continue?'))
        if dialog.run() == Gtk.ResponseType.YES:
            self.default.remove()
            self.default.create()
            self.disable_scripts.update_model()
        dialog.destroy()

    def config_test(self):
        if not os.path.exists(self.system_dir):
            self.default.create()

########NEW FILE########
__FILENAME__ = shortcuts
# Ubuntu Tweak - Ubuntu Configuration Tool
#
# Copyright (C) 2007-2011 Tualatrix Chou <tualatrix@gmail.com>
#
# Ubuntu Tweak is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# Ubuntu Tweak is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Ubuntu Tweak; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA

from gi.repository import GObject, Gtk, Gdk, GConf, GdkPixbuf

from ubuntutweak.modules  import TweakModule
from ubuntutweak.settings.compizsettings import CompizPlugin
from ubuntutweak.gui.widgets import KeyGrabber, KeyModifier
from ubuntutweak.gui.cellrenderers import CellRendererButton
from ubuntutweak.utils import icon


class Shortcuts(TweakModule):
    __title__  = _("Shortcuts")
    __desc__  = _("By configuring keyboard shortcuts, you can access your favourite applications instantly.\n"
                  "Enter the command to run the application and choose a shortcut key combination.")
    __icon__ = 'preferences-desktop-keyboard-shortcuts'
    __category__ = 'personal'
    __distro__ = ['precise']

    (COLUMN_ID,
     COLUMN_LOGO,
     COLUMN_TITLE,
     COLUMN_ICON,
     COLUMN_COMMAND,
     COLUMN_KEY,
     COLUMN_EDITABLE,
    ) = range(7)

    def __init__(self):
        TweakModule.__init__(self)

        if not CompizPlugin.get_plugin_active('commands'):
            CompizPlugin.set_plugin_active('commands', True)

        sw = Gtk.ScrolledWindow(shadow_type=Gtk.ShadowType.IN)
        sw.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        self.add_start(sw)

        treeview = self.create_treeview()
        sw.add(treeview)
    
    def create_treeview(self):
        treeview = Gtk.TreeView()

        self.model = self._create_model()

        treeview.set_model(self.model)

        self._add_columns(treeview)

        return treeview

    def _create_model(self):
        model = Gtk.ListStore(GObject.TYPE_INT,
                              GdkPixbuf.Pixbuf,
                              GObject.TYPE_STRING,
                              GdkPixbuf.Pixbuf,
                              GObject.TYPE_STRING,
                              GObject.TYPE_STRING,
                              GObject.TYPE_BOOLEAN)

        client = GConf.Client.get_default()
        logo = icon.get_from_name('gnome-terminal')

        for id in range(12):
            id = id + 1

            title = _("Command %d") % id
            command = client.get_string("/apps/metacity/keybinding_commands/command_%d" % id)
            key = client.get_string("/apps/metacity/global_keybindings/run_command_%d" % id)

            if not command:
                command = _("None")

            pixbuf = icon.get_from_name(command)

            if key == "disabled":
                key = _("disabled")

            model.append((id, logo, title, pixbuf, command, key, True))

        return model

    def _add_columns(self, treeview):
        model = treeview.get_model()

        column = Gtk.TreeViewColumn(_("ID"))

        renderer = Gtk.CellRendererPixbuf()
        column.pack_start(renderer, False)
        column.add_attribute(renderer, 'pixbuf', self.COLUMN_LOGO)

        renderer = Gtk.CellRendererText()
        column.pack_start(renderer, True)
        column.add_attribute(renderer, 'text', self.COLUMN_TITLE)
        treeview.append_column(column)

        column = Gtk.TreeViewColumn(_("Command"))

        renderer = Gtk.CellRendererPixbuf()
        column.pack_start(renderer, False)
        column.add_attribute(renderer, 'pixbuf', self.COLUMN_ICON)

        renderer = Gtk.CellRendererText()
        renderer.connect("edited", self.on_cell_edited, model)
        column.pack_start(renderer, True)
        column.add_attribute(renderer, 'text', self.COLUMN_COMMAND)
        column.add_attribute(renderer, 'editable', self.COLUMN_EDITABLE)
        treeview.append_column(column)

        column = Gtk.TreeViewColumn(_("Key"))

        renderer = Gtk.CellRendererText()
        renderer.connect("editing-started", self.on_editing_started)
        renderer.connect("edited", self.on_cell_edited, model)
        column.pack_start(renderer, True)
        column.add_attribute(renderer, 'text', self.COLUMN_KEY)
        column.add_attribute(renderer, 'editable', self.COLUMN_EDITABLE)
        column.set_resizable(True)
        treeview.append_column(column)

        #TODO re-enable the clean button
#        renderer = CellRendererButton(_("Clean"))
#        renderer.connect("clicked", self.on_clean_clicked)
#        column.pack_start(renderer, False)

    def on_clean_clicked(self, cell, path):
        iter = self.model.get_iter_from_string(path)
        id = self.model.get_value(iter, self.COLUMN_ID)
        self.model.set_value(iter, self.COLUMN_KEY, _("disabled"))
        client = GConf.Client.get_default()
        client.set_string("/apps/metacity/global_keybindings/run_command_%d" % id, "disabled")

    def on_got_key(self, widget, key, mods, cell_data):
        cell, path = cell_data

        new = Gtk.accelerator_name(key, Gdk.ModifierType(mods))
        if new in ('BackSpace', 'Delete', 'Escape', ''):
            self.on_clean_clicked(cell, path)
            return True

        for mod in KeyModifier:
            if "%s_L" % mod in new:
                new = new.replace ("%s_L" % mod, "<%s>" % mod)
            if "%s_R" % mod in new:
                new = new.replace ("%s_R" % mod, "<%s>" % mod)

        widget.destroy()

        client = GConf.Client.get_default()
        column = cell.get_data("id")
        iter = self.model.get_iter_from_string(cell.get_data("path_string"))

        id = self.model.get_value(iter, self.COLUMN_ID)

        client.set_string("/apps/metacity/global_keybindings/run_command_%d" % id, new)
        self.model.set_value(iter, self.COLUMN_KEY, new)

    def on_editing_started(self, cell, editable, path):
        grabber = KeyGrabber(self.get_toplevel(), label="Grab key combination")
        cell.set_data("path_string", path)
        grabber.hide()
        grabber.set_no_show_all(True)
        grabber.connect('changed', self.on_got_key, (cell, path))
        grabber.begin_key_grab(None)

    def on_cell_edited(self, cell, path_string, new_text, model):
        iter = model.get_iter_from_string(path_string)

        client = GConf.Client.get_default()
        column = cell.get_data("id")

        id = model.get_value(iter, self.COLUMN_ID)
        old = model.get_value(iter, self.COLUMN_COMMAND)

        if old != new_text:
            client.set_string("/apps/metacity/keybinding_commands/command_%d" % id, new_text)
            if new_text:
                pixbuf = icon.get_from_name(new_text)

                model.set_value(iter, self.COLUMN_ICON, pixbuf)
                model.set_value(iter, self.COLUMN_COMMAND, new_text)
            else:
                model.set_value(iter, self.COLUMN_ICON, None)
                model.set_value(iter, self.COLUMN_COMMAND, _("None"))

########NEW FILE########
__FILENAME__ = sourcecenter
#!/usr/bin/python
# coding: utf-8

# Ubuntu Tweak - PyGTK based desktop configuration tool
#
# Copyright (C) 2007-2008 TualatriX <tualatrix@gmail.com>
#
# Ubuntu Tweak is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# Ubuntu Tweak is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Ubuntu Tweak; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA

import os
import re
import json
import time
import urllib
import thread
import apt_pkg
import logging
import gettext
import subprocess

from urllib2 import urlopen, Request, URLError
from gettext import ngettext
from aptsources.sourceslist import SourcesList

from gi.repository import Gtk, Gdk, GdkPixbuf
from gi.repository import Pango
from gi.repository import GObject
from gi.repository import Notify

from ubuntutweak import system
from ubuntutweak.common import consts
from ubuntutweak.common.debug import log_func
from ubuntutweak.modules  import TweakModule
from ubuntutweak.policykit.dbusproxy import proxy
from ubuntutweak.gui.widgets import CheckButton
from ubuntutweak.gui.dialogs import QuestionDialog, ErrorDialog, InfoDialog, WarningDialog
from ubuntutweak.gui.gtk import post_ui, set_busy, unset_busy
from ubuntutweak.utils.parser import Parser
from ubuntutweak.network import utdata
from ubuntutweak.settings.gsettings import GSetting
from ubuntutweak.utils import set_label_for_stock_button
from ubuntutweak.utils import ppa, icon
from ubuntutweak.utils.package import AptWorker
from ubuntutweak.apps import CategoryView

from ubuntutweak.admins.appcenter import AppView, AppParser, StatusProvider
from ubuntutweak.admins.appcenter import CheckUpdateDialog, FetchingDialog, PackageInfo

log = logging.getLogger("SourceCenter")

APP_PARSER = AppParser()
PPA_MIRROR = []
UNCONVERT = False
WARNING_KEY = 'com.ubuntu-tweak.apps.disable-warning'
CONFIG = GSetting(key=WARNING_KEY)
UPDATE_SETTING = GSetting(key='com.ubuntu-tweak.apps.sources-can-update', type=bool)
VERSION_SETTING = GSetting(key='com.ubuntu-tweak.apps.sources-version', type=str)

SOURCE_ROOT = os.path.join(consts.CONFIG_ROOT, 'sourcecenter')
SOURCE_VERSION_URL = utdata.get_version_url('/sourcecenter_version/')
UPGRADE_DICT = {}

def get_source_data_url():
    return utdata.get_download_url('/media/utdata/sourcecenter-%s.tar.gz' %
                                   VERSION_SETTING.get_value())

def get_source_logo_from_filename(file_name):
    path = os.path.join(SOURCE_ROOT, file_name)
    if not os.path.exists(path) or file_name == '':
        path = os.path.join(consts.DATA_DIR, 'pixmaps/ppa-logo.png')

    try:
        pixbuf = GdkPixbuf.Pixbuf.new_from_file(path)
        if pixbuf.get_width() != 32 or pixbuf.get_height() != 32:
            pixbuf = pixbuf.scale_simple(32, 32, GdkPixbuf.InterpType.BILINEAR)
        return pixbuf
    except:
        return Gtk.IconTheme.get_default().load_icon(Gtk.STOCK_MISSING_IMAGE, 32, 0)

class CheckSourceDialog(CheckUpdateDialog):
    def get_updatable(self):
        return utdata.check_update_function(self.url, SOURCE_ROOT, \
                                            UPDATE_SETTING, VERSION_SETTING, \
                                            auto=False)

class DistroParser(Parser):
    def __init__(self):
        super(DistroParser, self).__init__(os.path.join(SOURCE_ROOT, 'distros.json'), 'id')

    def get_codename(self, key):
        return self[key]['codename']

class SourceParser(Parser):
    def __init__(self):
        super(SourceParser, self).__init__(os.path.join(SOURCE_ROOT, 'sources.json'), 'id')

    def init_items(self, key):
        self.reverse_depends = {}

        distro_parser = DistroParser()

        for item in self.get_data():
            distro_values = ''

            if item['fields'].has_key('distros'):
                distros = item['fields']['distros']

                for id in distros:
                    codename = distro_parser.get_codename(id)
                    if codename in system.UBUNTU_CODENAMES:
                        if system.CODENAME == codename:
                            distro_values = codename
                            break
                    else:
                        distro_values = codename
                        break

                if distro_values == '':
                    continue

            item['fields']['id'] = item['pk']
            item['fields']['distro'] = distro_values
            self[item['fields'][key]] = item['fields']

            UPGRADE_DICT[item['fields']['url']] = distro_values

            id = item['pk']
            fields = item['fields']

            if fields.has_key('dependencies') and fields['dependencies']:
                for depend_id in fields['dependencies']:
                    if self.reverse_depends.has_key(depend_id):
                        self.reverse_depends[depend_id].append(id)
                    else:
                        self.reverse_depends[depend_id] = [id]

    def has_reverse_depends(self, id):
        if id in self.reverse_depends.keys():
            return True
        else:
            return False

    def get_reverse_depends(self, id):
        return self.reverse_depends[id]

    def get_slug(self, key):
        return self[key]['slug']

    def get_conflicts(self, key):
        if self[key].has_key('conflicts'):
            return self[key]['conflicts']
        else:
            return None

    def get_dependencies(self, key):
        if self[key].has_key('dependencies'):
            return self[key]['dependencies']
        else:
            return None

    def get_summary(self, key):
        return self.get_by_lang(key, 'summary')

    def get_name(self, key):
        return self.get_by_lang(key, 'name')

    def get_category(self, key):
        return self[key]['category']

    def get_url(self, key):
        return self[key]['url']

    def get_key(self, key):
        return self[key]['key']

    def get_key_fingerprint(self, key):
        if self[key].has_key('key_fingerprint'):
            return self[key]['key_fingerprint']
        else:
            return ''

    def get_distro(self, key):
        return self[key]['distro']

    def get_comps(self, key):
        return self[key]['component']

    def get_website(self, key):
        return self[key]['website']

    def set_enable(self, key, enable):
        # To make other module use the source enable feature, move the logical to here
        # So that other module can call
        gpg_key = self.get_key(key)
        url = self.get_url(key)
        distro = self.get_distro(key)
        comps = self.get_comps(key)
        comment = self.get_name(key)

        if ppa.is_ppa(url):
            file_name = '%s-%s' % (ppa.get_source_file_name(url), distro)
        else:
            file_name = self.get_slug(key)

        if gpg_key:
            proxy.add_apt_key_from_content(gpg_key)

        if not comps and distro:
            distro = distro + '/'
        elif not comps and not distro:
            distro = './'

        result = proxy.set_separated_entry(url, distro, comps,
                                           comment, enable, file_name)

        return str(result)

SOURCE_PARSER = SourceParser()

class SourceStatus(StatusProvider):
    def load_objects_from_parser(self, parser):
        init = self.get_init()

        for key in parser.keys():
            id = key
            slug = parser.get_slug(key)
            key = slug
            if init:
                log.debug('SourceStatus first init, set %s as read' % id)
                self.get_data()['apps'][key] = {}
                self.get_data()['apps'][key]['read'] = True
                self.get_data()['apps'][key]['cate'] = parser.get_category(id)
            else:
                if key not in self.get_data()['apps']:
                    self.get_data()['apps'][key] = {}
                    self.get_data()['apps'][key]['read'] = False
                    self.get_data()['apps'][key]['cate'] = parser.get_category(id)

        if init and parser.keys():
            log.debug('Init finish, SourceStatus set init to False')
            self.set_init(False)

        self.save()

    def get_read_status(self, key):
        try:
            return self.get_data()['apps'][key]['read']
        except:
            return True

    def set_as_read(self, key):
        try:
            self.get_data()['apps'][key]['read'] = True
        except:
            pass
        self.save()


class NoNeedDowngradeException(Exception):
    pass


class DowngradeView(Gtk.TreeView):
    __gsignals__ = {
        'checked': (GObject.SignalFlags.RUN_FIRST, None,
                    (GObject.TYPE_BOOLEAN,)),
        'cleaned': (GObject.SignalFlags.RUN_FIRST, None, ())
    }

    (COLUMN_PKG,
     COLUMN_PPA_VERSION,
     COLUMN_SYSTEM_VERSION) = range(3)

    def __init__(self, plugin):
        GObject.GObject.__init__(self)

        model = Gtk.ListStore(GObject.TYPE_STRING,
                              GObject.TYPE_STRING,
                              GObject.TYPE_STRING)
        self.set_model(model)
        model.set_sort_column_id(self.COLUMN_PKG, Gtk.SortType.ASCENDING)

        self.plugin = plugin

        self._add_column()

    def _add_column(self):
        renderer = Gtk.CellRendererText()
        column = Gtk.TreeViewColumn(_('Package'))
        column.pack_start(renderer, False)
        column.add_attribute(renderer, 'text', self.COLUMN_PKG)
        column.set_sort_column_id(self.COLUMN_PKG)
        self.append_column(column)

        renderer = Gtk.CellRendererText()
        renderer.set_property('ellipsize', Pango.EllipsizeMode.END)
        column = Gtk.TreeViewColumn(_('Previous Version'))
        column.pack_start(renderer, True)
        column.add_attribute(renderer, 'text', self.COLUMN_PPA_VERSION)
        column.set_resizable(True)
        column.set_min_width(180)
        self.append_column(column)

        renderer = Gtk.CellRendererText()
        renderer.set_property('ellipsize', Pango.EllipsizeMode.END)
        column = Gtk.TreeViewColumn(_('System Version'))
        column.pack_start(renderer, True)
        column.add_attribute(renderer, 'text', self.COLUMN_SYSTEM_VERSION)
        column.set_resizable(True)
        self.append_column(column)

    def update_downgrade_model(self, ppas):
        model = self.get_model()
        model.clear()
        pkg_dict = {}
        for ppa_url in ppas:
            path = ppa.get_list_name(ppa_url)
            log.debug('Find the PPA path name: %s', path)
            if path:
                for line in open(path):
                    if line.startswith('Package:'):
                        pkg = line.split()[1].strip()
                        if pkg in pkg_dict:
                            # Join another ppa info to the pkg dict, so that
                            # later we can know if more than two ppa provide
                            # the pkg
                            pkg_dict[pkg].extend([ppa_url])
                        else:
                            pkg_dict[pkg] = [ppa_url]

        pkg_map = self.get_downgradeable_pkgs(pkg_dict)

        if pkg_map:
            log.debug("Start insert pkg_map to model: %s\n" % str(pkg_map))
            for pkg, (p_verion, s_verion) in pkg_map.items():
                model.append((pkg, p_verion, s_verion))

    def get_downgrade_packages(self):
        model = self.get_model()
        downgrade_list = []
        for row in model:
            pkg, version = row[self.COLUMN_PKG], row[self.COLUMN_SYSTEM_VERSION]
            downgrade_list.append("%s=%s" % (pkg, version))
        log.debug("The package to downgrade is %s" % str(downgrade_list))
        return downgrade_list

    def get_downgradeable_pkgs(self, ppa_dict):
        def is_system_origin(version, urls):
            origins = [ppa.get_ppa_origin_name(url) for url in urls]
            system_version = 0
            match = False

            for origin in version.origins:
                if origin.origin:
                    if origin.origin not in origins:
                        log.debug("The origin %s is not in %s, so end the loop" % (origin.origin, str(origins)))
                        match = True
                        break

            if match:
                system_version = version.version
                log.debug("Found match url, the system_version is %s, now iter to system version" % system_version)

            return system_version

        def is_full_match_ppa_origin(pkg, version, urls):
            origins = [ppa.get_ppa_origin_name(url) for url in urls]
            ppa_version = 0
            match = True

            if version == pkg.installed:
                for origin in version.origins:
                    if origin.origin:
                        if origin.origin not in origins:
                            log.debug("The origin %s is not in %s, so end the loop" % (origin.origin, str(origins)))
                            match = False
                            break

                if match:
                    ppa_version = version.version
                    log.debug("Found match url, the ppa_version is %s, now iter to system version" % ppa_version)

            return ppa_version

        log.debug("Check downgrade information")
        downgrade_dict = {}
        for pkg, urls in ppa_dict.items():
            log.debug("The package is: %s, PPA URL is: %s" % (pkg, str(urls)))

            if pkg not in AptWorker.get_cache():
                log.debug("    package isn't available, continue next...\n")
                continue

            pkg = AptWorker.get_cache()[pkg]
            if not pkg.isInstalled:
                log.debug("    package isn't installed, continue next...\n")
                continue
            versions = pkg.versions

            ppa_version = 0
            system_version = 0
            FLAG = 'PPA'
            try:
                for version in versions:
                    try:
                        #FIXME option to remove the package
                        log.debug("Version uri is %s" % version.uri)

                        # Switch FLAG
                        if FLAG == 'PPA':
                            ppa_version = is_full_match_ppa_origin(pkg, version, urls)
                            FLAG = 'SYSTEM'
                            if ppa_version == 0:
                                raise NoNeedDowngradeException
                        else:
                            system_version = is_system_origin(version, urls)

                        if ppa_version and system_version:
                            downgrade_dict[pkg.name] = (ppa_version, system_version)
                            break
                    except StopIteration:
                        pass
            except NoNeedDowngradeException:
                log.debug("Catch NoNeedDowngradeException, so pass this package: %s" % pkg)
                continue
            log.debug("\n")
        return downgrade_dict


class UpdateView(AppView):
    def __init__(self):
        AppView.__init__(self)

        self.set_headers_visible(False)

    def update_model(self, apps):
        model = self.get_model()

        length = len(apps)
        iter = model.append()
        model.set(iter,
                  self.COLUMN_INSTALLED, False,
                  self.COLUMN_DISPLAY,
                      '<span size="large" weight="bold">%s</span>' %
                          ngettext('%d New Application Available',
                                   '%d New Applications Available', length) % length,
                  )

        super(UpdateView, self).update_model(apps)

    def update_updates(self, pkgs):
        '''apps is a list to iter pkgname,
        cates is a dict to find what the category the pkg is
        '''
        model = self.get_model()
        length = len(pkgs)

        if pkgs:
            iter = model.append()
            model.set(iter,
                      self.COLUMN_DISPLAY,
                      '<span size="large" weight="bold">%s</span>' %
                      ngettext('%d Package Update Available',
                               '%d Package Updates Available',
                               length) % length)

            apps = []
            updates = []
            for pkg in pkgs:
                if pkg in APP_PARSER:
                    apps.append(pkg)
                else:
                    updates.append(pkg)

            for pkgname in apps:
                pixbuf = self.get_app_logo(APP_PARSER[pkgname]['logo'])

                package = PackageInfo(pkgname)
                appname = package.get_name()
                desc = APP_PARSER.get_summary(pkgname)

                iter = model.append()
                model.set(iter,
                          self.COLUMN_INSTALLED, False,
                          self.COLUMN_ICON, pixbuf,
                          self.COLUMN_PKG, pkgname,
                          self.COLUMN_NAME, appname,
                          self.COLUMN_DESC, desc,
                          self.COLUMN_DISPLAY, '<b>%s</b>\n%s' % (appname, desc),
                          self.COLUMN_TYPE, 'update')

            for pkgname in updates:
                package = PACKAGE_WORKER.get_cache()[pkgname]

                self.append_update(False, package.name, package.summary)
        else:
            iter = model.append()
            model.set(iter,
                      self.COLUMN_DISPLAY,
                        '<span size="large" weight="bold">%s</span>' %
                        _('No Available Package Updates'))

    def select_all_action(self, active):
        self.to_rm = []
        self.to_add = []
        model = self.get_model()
        model.foreach(self.__select_foreach, active)
        self.emit('changed', len(self.to_add))

    def __select_foreach(self, model, path, iter, check):
        model.set(iter, self.COLUMN_INSTALLED, check)
        pkg = model.get_value(iter, self.COLUMN_PKG)
        if pkg and check:
            self.to_add.append(pkg)


class SourcesView(Gtk.TreeView):
    __gsignals__ = {
        'sourcechanged': (GObject.SignalFlags.RUN_FIRST, None, ()),
        'new_purge': (GObject.SignalFlags.RUN_FIRST, None, (GObject.TYPE_PYOBJECT,))
    }
    (COLUMN_ENABLED,
     COLUMN_ID,
     COLUMN_CATE,
     COLUMN_URL,
     COLUMN_DISTRO,
     COLUMN_COMPS,
     COLUMN_SLUG,
     COLUMN_LOGO,
     COLUMN_NAME,
     COLUMN_COMMENT,
     COLUMN_DISPLAY,
     COLUMN_HOME,
     COLUMN_KEY,
    ) = range(13)

    def __init__(self):
        GObject.GObject.__init__(self)

        self.filter = None
        self.modelfilter = None
        self._status = None
        self.view_mode = 'view'
        self.to_purge = []

        self.model = self.__create_model()
        self.model.set_sort_column_id(self.COLUMN_NAME, Gtk.SortType.ASCENDING)
        self.set_model(self.model)

        self.set_search_column(self.COLUMN_NAME)

        self._add_column()

        self.selection = self.get_selection()

    def get_sourceslist(self):
        return SourcesList()

    def __create_model(self):
        model = Gtk.ListStore(GObject.TYPE_BOOLEAN,
                              GObject.TYPE_INT,
                              GObject.TYPE_INT,
                              GObject.TYPE_STRING,
                              GObject.TYPE_STRING,
                              GObject.TYPE_STRING,
                              GObject.TYPE_STRING,
                              GdkPixbuf.Pixbuf,
                              GObject.TYPE_STRING,
                              GObject.TYPE_STRING,
                              GObject.TYPE_STRING,
                              GObject.TYPE_STRING,
                              GObject.TYPE_STRING)

        return model

    def on_visible_filter(self, model, iter, data=None):
        log.debug("on_visible_filter: %s" % self.model.get_value(iter, self.COLUMN_NAME))
        category = self.model.get_value(iter, self.COLUMN_CATE)
        if self.filter == None or self.filter == category:
            return True
        else:
            return False

    def _add_column(self):
        renderer = Gtk.CellRendererToggle()
        renderer.connect('toggled', self.on_enable_toggled)
        column = Gtk.TreeViewColumn(' ', renderer, active=self.COLUMN_ENABLED)
        column.set_sort_column_id(self.COLUMN_ENABLED)
        self.append_column(column)

        self.source_column = Gtk.TreeViewColumn(_('Third-Party Sources'))
        self.source_column.set_sort_column_id(self.COLUMN_NAME)
        self.source_column.set_spacing(5)
        renderer = Gtk.CellRendererPixbuf()
        self.source_column.pack_start(renderer, False)
        self.source_column.add_attribute(renderer, 'pixbuf', self.COLUMN_LOGO)

        renderer = Gtk.CellRendererText()
        renderer.set_property('ellipsize', Pango.EllipsizeMode.END)
        self.source_column.pack_start(renderer, True)
        self.source_column.add_attribute(renderer, 'markup', self.COLUMN_DISPLAY)

        self.append_column(self.source_column)

    def set_status_active(self, active):
        if active:
            self._status = SourceStatus('sourcestatus.json')

    def get_status(self):
        return self._status

    def update_source_model(self, find='all', limit=-1, only_enabled=False):
        self.model.clear()
        sourceslist = self.get_sourceslist()
        enabled_list = []

        for source in sourceslist.list:
            if source.type == 'deb' and not source.disabled:
                enabled_list.append(source.uri)

        if self._status:
            self._status.load_objects_from_parser(SOURCE_PARSER)

        index = 0

        for id in SOURCE_PARSER:
            enabled = False
            index = index + 1
            url = SOURCE_PARSER.get_url(id)
            enabled = url in enabled_list

            if enabled:
                enabled_list.remove(url)

            if only_enabled:
                if not enabled:
                    continue
                elif not ppa.is_ppa(url):
                    continue
                else:
                    enabled = not enabled

            slug = SOURCE_PARSER.get_slug(id)
            comps = SOURCE_PARSER.get_comps(id)
            distro = SOURCE_PARSER.get_distro(id)
            category = SOURCE_PARSER.get_category(id)
            
            if find != 'all' and category != find:
                continue

            #TODO real top-10
            if limit > 0 and index >= limit:
                break

            name = SOURCE_PARSER.get_name(id)
            comment = SOURCE_PARSER.get_summary(id)
            pixbuf = get_source_logo_from_filename(SOURCE_PARSER[id]['logo'])
            website = SOURCE_PARSER.get_website(id)
            key = SOURCE_PARSER.get_key(id)

            if self._status and not self._status.get_read_status(slug):
                display = '<b>%s <span foreground="#ff0000">(New!!!)</span>\n%s</b>' % (name, comment)
            else:
                display = '<b>%s</b>\n%s' % (name, comment)

            iter = self.model.append()
            self.model.set(iter,
                           self.COLUMN_ENABLED, enabled,
                           self.COLUMN_ID, id,
                           self.COLUMN_CATE, category,
                           self.COLUMN_URL, url,
                           self.COLUMN_DISTRO, distro,
                           self.COLUMN_COMPS, comps,
                           self.COLUMN_COMMENT, comment,
                           self.COLUMN_SLUG, slug,
                           self.COLUMN_NAME, name,
                           self.COLUMN_DISPLAY, display,
                           self.COLUMN_LOGO, pixbuf,
                           self.COLUMN_HOME, website,
                           self.COLUMN_KEY, key,
            )

        path = os.path.join(consts.DATA_DIR, 'pixmaps/ppa-logo.png')

        pixbuf = icon.get_from_file(path, size=32)

        if enabled_list and only_enabled:
            for url in enabled_list:
                if ppa.is_ppa(url):
                    iter = self.model.append()
                    self.model.set(iter,
                                   self.COLUMN_ENABLED, False,
                                   self.COLUMN_ID, 9999,
                                   self.COLUMN_CATE, -1,
                                   self.COLUMN_URL, url,
                                   self.COLUMN_DISTRO, distro,
                                   self.COLUMN_COMPS, comps,
                                   self.COLUMN_COMMENT, '',
                                   self.COLUMN_SLUG, url,
                                   self.COLUMN_NAME, ppa.get_basename(url),
                                   self.COLUMN_DISPLAY, ppa.get_long_name(url),
                                   self.COLUMN_LOGO, pixbuf,
                                   self.COLUMN_HOME, ppa.get_homepage(url),
                                   self.COLUMN_KEY, '',
                    )

    def set_as_read(self, iter, model):
        if type(model) == Gtk.TreeModelFilter:
            iter = model.convert_iter_to_child_iter(iter)
            model = model.get_model()
        id = model.get_value(iter, self.COLUMN_ID)
        slug = model.get_value(iter, self.COLUMN_SLUG)
        if self._status and not self._status.get_read_status(slug):
            name = model.get_value(iter, self.COLUMN_NAME)
            comment = model.get_value(iter, self.COLUMN_COMMENT)
            self._status.set_as_read(slug)
            model.set_value(iter,
                            self.COLUMN_DISPLAY,
                            '<b>%s</b>\n%s' % (name, comment))

    def get_sourcelist_status(self, url):
        for source in self.get_sourceslist():
            if url in source.str() and source.type == 'deb':
                return not source.disabled
        return False

    @log_func(log)
    def on_enable_toggled(self, cell, path):
        model = self.get_model()
        iter = model.get_iter((int(path),))

        id = model.get_value(iter, self.COLUMN_ID)
        name = model.get_value(iter, self.COLUMN_NAME)
        enabled = model.get_value(iter, self.COLUMN_ENABLED)
        url = model.get_value(iter, self.COLUMN_URL)

        if self.view_mode == 'view':
            conflicts = SOURCE_PARSER.get_conflicts(id)
            dependencies = SOURCE_PARSER.get_dependencies(id)

            #Convert to real model, because will involke the set method
            if type(model) == Gtk.TreeModelFilter:
                iter = model.convert_iter_to_child_iter(iter)
                model = model.get_model()

            if not enabled and conflicts:
                conflict_list = []
                conflict_name_list = []
                for conflict_id in conflicts:
                    if self.get_source_enabled(conflict_id):
                        conflict_list.append(conflict_id)
                        name_list = [r[self.COLUMN_NAME] for r in model if r[self.COLUMN_ID] == conflict_id]
                        if name_list:
                                conflict_name_list.extend(name_list)

                if conflict_list and conflict_name_list:
                    full_name = ', '.join(conflict_name_list)
                    ErrorDialog(_('You can\'t enable this Source because'
                                  '<b>"%(SOURCE)s"</b> conflicts with it.\nTo '
                                  'continue you need to disable <b>"%(SOURCE)s"</b>' \
                                  'first.') % {'SOURCE': full_name}).launch()

                    model.set(iter, self.COLUMN_ENABLED, enabled)
                    return

            if enabled is False and dependencies:
                depend_list = []
                depend_name_list = []
                for depend_id in dependencies:
                    if self.get_source_enabled(depend_id) is False:
                        depend_list.append(depend_id)
                        name_list = [r[self.COLUMN_NAME] for r in model if r[self.COLUMN_ID] == depend_id]
                        if name_list:
                                depend_name_list.extend(name_list)

                if depend_list and depend_name_list:
                    full_name = ', '.join(depend_name_list)

                    dialog = QuestionDialog(title=_('Dependency Notice'),
                                            message= _('To enable this Source, You need to enable <b>"%s"</b> at first.\nDo you wish to continue?') \
                                % full_name)
                    if dialog.run() == Gtk.ResponseType.YES:
                        for depend_id in depend_list:
                            self.set_source_enabled(depend_id)
                        self.set_source_enabled(id)
                    else:
                        model.set(iter, self.COLUMN_ENABLED, enabled)

                    dialog.destroy()
                    return

            if enabled and SOURCE_PARSER.has_reverse_depends(id):
                depend_list = []
                depend_name_list = []
                for depend_id in SOURCE_PARSER.get_reverse_depends(id):
                    if self.get_source_enabled(depend_id):
                        depend_list.append(depend_id)
                        name_list = [r[self.COLUMN_NAME] for r in model if r[self.COLUMN_ID] == depend_id]
                        if name_list:
                                depend_name_list.extend(name_list)

                if depend_list and depend_name_list:
                    full_name = ', '.join(depend_name_list)

                    ErrorDialog(_('You can\'t disable this Source because '
                                '<b>"%(SOURCE)s"</b> depends on it.\nTo continue '
                                'you need to disable <b>"%(SOURCE)s"</b> first.') \
                                     % {'SOURCE': full_name}).launch()

                    model.set(iter, self.COLUMN_ENABLED, enabled)
                    return

            self.do_source_enable(iter, not enabled)
        else:
            #TODO purge dependencies
            status = not enabled
            model.set(iter, self.COLUMN_ENABLED, status)

            if status:
                self.to_purge.append(url)
            else:
                self.to_purge.remove(url)

            self.emit('new_purge', self.to_purge)

    def on_source_foreach(self, model, path, iter, id):
        m_id = model.get_value(iter, self.COLUMN_ID)
        if m_id == id:
            if self._foreach_mode == 'get':
                self._foreach_take = model.get_value(iter, self.COLUMN_ENABLED)
            elif self._foreach_mode == 'set':
                self._foreach_take = iter

    def on_source_name_foreach(self, model, path, iter, id):
        m_id = model.get_value(iter, self.COLUMN_ID)
        if m_id == id:
            self._foreach_name_take = model.get_value(iter, self.COLUMN_NAME)

    def get_source_enabled(self, id):
        '''
        Search source by id, then get status from model
        '''
        self._foreach_mode = 'get'
        self._foreach_take = None
        self.model.foreach(self.on_source_foreach, id)
        return self._foreach_take

    def set_source_enabled(self, id):
        '''
        Search source by id, then call do_source_enable
        '''
        self._foreach_mode = 'set'
        self._foreach_status = None
        self.model.foreach(self.on_source_foreach, id)
        self.do_source_enable(self._foreach_take, True)

    def set_source_disable(self, id):
        '''
        Search source by id, then call do_source_enable
        '''
        self._foreach_mode = 'set'
        self._foreach_status = None
        self.model.foreach(self.on_source_foreach, id)
        self.do_source_enable(self._foreach_take, False)

    def do_source_enable(self, iter, enable):
        '''
        Do the really source enable or disable action by iter
        Only emmit signal when source is changed
        '''
        model = self.get_model()

        id = model.get_value(iter, self.COLUMN_ID)
        url = model.get_value(iter, self.COLUMN_URL)
        icon = model.get_value(iter, self.COLUMN_LOGO)
        comment = model.get_value(iter, self.COLUMN_NAME)
        pre_status = self.get_sourcelist_status(url)
        result = SOURCE_PARSER.set_enable(id, enable)

        log.debug("Setting source %s (%d) to %s, result is %s" % (comment, id, str(enable), result))

        if result == 'enabled':
            model.set(iter, self.COLUMN_ENABLED, True)
        else:
            model.set(iter, self.COLUMN_ENABLED, False)

        if pre_status != enable:
            self.emit('sourcechanged')

        if enable:
            notify = Notify.Notification(summary=_('New source has been enabled'),
                                         body=_('%s is enabled now, Please click the refresh button to update the application cache.') % comment)
            notify.set_icon_from_pixbuf(icon)
            notify.set_hint_string ("x-canonical-append", "")
            notify.show()

class SourceCategoryView(CategoryView):
    def pre_update_cate_model(self):
#        self.model.append(None, (-3,
#                                 'latest',
#                                 _('Latest')))

#        self.model.append(None, (-2,
#                                 'top-10',
#                                 _('Top 10')))

        self.model.append(None, (-1,
                                 'enabled-ppa',
                                 _('Enabled PPAs')))

class SourceCenter(TweakModule):
    __title__  = _('Source Center')
    __desc__ = _('A collection of software sources to ensure your applications are always up-to-date.')
    __icon__ = 'software-properties'
    __url__ = 'http://ubuntu-tweak.com/source/'
    __urltitle__ = _('Visit online Source Center')
    __category__ = 'application'
    __keywords__ = 'ppa repository app'
    __utactive__ = False

    def __init__(self):
        TweakModule.__init__(self, 'sourcecenter.ui')

        self.url = SOURCE_VERSION_URL
        set_label_for_stock_button(self.sync_button, _('_Sync'))

        self.cateview = SourceCategoryView(os.path.join(SOURCE_ROOT, 'cates.json'))
        self.cateview.update_cate_model()
        self.cateview.get_selection().connect('changed', self.on_category_changed)
        self.left_sw.add(self.cateview)

        self.sourceview = SourcesView()
        self.sourceview.set_status_active(True)
        self.sourceview.update_source_model()
        self.sourceview.connect('sourcechanged', self.on_source_changed)
        self.sourceview.connect('new_purge', self.on_purge_changed)
        self.sourceview.get_selection().connect('changed', self.on_source_selection)
        self.sourceview.set_rules_hint(True)
        self.right_sw.add(self.sourceview)
        self.cateview.set_status_from_view(self.sourceview)

        self.update_timestamp()
        UPDATE_SETTING.set_value(False)
        UPDATE_SETTING.connect_notify(self.on_have_update, data=None)

        log.debug('Start check update')
        thread.start_new_thread(self.check_update, ())
        GObject.timeout_add(60000, self.update_timestamp)

        if self.check_source_upgradable() and UPGRADE_DICT:
            GObject.idle_add(self.upgrade_sources)

        self.add_start(self.main_vbox)

        self.connect('realize', self.setup_ui_tasks)

        GObject.idle_add(self.show_warning)

    @post_ui
    def show_warning(self):
        if not CONFIG.get_value():
            dialog = WarningDialog(title=_('Warning'),
                                   message=_('It is a possible security risk to '
                'use packages from Third-Party Sources.\n'
                'Please be careful and use only sources you trust.'),
                                   buttons=Gtk.ButtonsType.OK)
            checkbutton = CheckButton(_('Never show this dialog'),
                                      key=WARNING_KEY,
                                      backend='gsettings')
            dialog.add_option_button(checkbutton)

            dialog.run()
            dialog.destroy()

    def setup_ui_tasks(self, widget):
        self.purge_ppa_button.hide()
        self.cateview.expand_all()

    def check_source_upgradable(self):
        log.debug("The check source string is: \"%s\"" % self.__get_disable_string())
        for source in SourcesList():
            if self.__get_disable_string() in source.str() and \
                    source.uri in UPGRADE_DICT and \
                    source.disabled:
                return True

        return False

    def __get_disable_string(self):
        APP="update-manager"
        DIR="/usr/share/locale"

        gettext.bindtextdomain(APP, DIR)
        gettext.textdomain(APP)

        #the "%s" is in front, some is the end, so just return the long one
        translated = gettext.gettext("disabled on upgrade to %s")
        a, b = translated.split('%s')
        return a.strip() or b.strip()

    def update_timestamp(self):
        self.time_label.set_text(_('Last synced:') + ' ' + utdata.get_last_synced(SOURCE_ROOT))
        return True

    @post_ui
    def upgrade_sources(self):
        dialog = QuestionDialog(title=_('Upgrade Third Party Sources'),
                                message=_('After a successful distribution upgrade, '
                                'any third-party sources you use will be disabled by default.\n'
                                'Would you like to re-enable any sources disabled by Update Manager?'))

        response = dialog.run()
        dialog.destroy()
        if response == Gtk.ResponseType.YES:
            proxy.upgrade_sources(self.__get_disable_string(), UPGRADE_DICT)
            if not self.check_source_upgradable():
                InfoDialog(_('Upgrade Successful!')).launch()
            else:
                ErrorDialog(_('Upgrade Failed!')).launch()
            self.emit('call', 'ubuntutweak.modules.sourceeditor', 'update_source_combo', {})
            self.update_sourceview()

    @post_ui
    def on_have_update(self, *args):
        if UPDATE_SETTING.get_value():
            dialog = QuestionDialog(_('New source data available, would you like to update?'))
            response = dialog.run()
            dialog.destroy()

            if response == Gtk.ResponseType.YES:
                dialog = FetchingDialog(get_source_data_url(),
                                        self.get_toplevel())
                dialog.connect('destroy', self.on_source_data_downloaded)
                dialog.run()
                dialog.destroy()

    def check_update(self):
        try:
            return utdata.check_update_function(self.url, SOURCE_ROOT, \
                                            UPDATE_SETTING, VERSION_SETTING, \
                                            auto=True)
        except Exception, error:
            print error

    def on_source_selection(self, widget, data=None):
        model, iter = widget.get_selected()

        if iter:
            sourceview = widget.get_tree_view()
            sourceview.set_as_read(iter, model)
            self.cateview.update_selected_item()

            home = model.get_value(iter, self.sourceview.COLUMN_HOME)
            url = model.get_value(iter, self.sourceview.COLUMN_URL)
            description = model.get_value(iter, self.sourceview.COLUMN_COMMENT)

            self.set_details(home, url, description)

    def on_category_changed(self, widget, data=None):
        self.update_sourceview()

    def update_sourceview(self):
        self.cateview.set_status_from_view(self.sourceview)
        model, iter = self.cateview.get_selection().get_selected()

        limit = -1
        only_enabled = False
        if iter:
            find = model[iter][self.cateview.CATE_ID] or 'all'
            if find == -3:
                find = 'all'
            elif find == -2:
                find = 'all'
                limit = 10
            elif find == -1:
                find = 'all'
                only_enabled = True
        else:
            find = 'all'
        log.debug("Filter for %s" % find)
        self.sourceview.update_source_model(find=find,
                                     limit=limit,
                                     only_enabled=only_enabled)
        if only_enabled:
            self.purge_ppa_button.show()
            self.purge_ppa_button.set_sensitive(False)
            self.sourceview.source_column.set_title(_('All enabled PPAs (Select and click "Purge PPA" can safely downgrade packages)'))
            self.sourceview.view_mode = 'purge'
        else:
            self.purge_ppa_button.hide()
            self.sourceview.source_column.set_title(_('Third-Party Sources'))
            self.sourceview.view_mode = 'view'

    def set_details(self,
                    homepage='http://ubuntu-tweak.com',
                    url='http://ubuntu-tweak.com',
                    description=None):
        self.homepage_button.set_label(homepage)
        self.homepage_button.set_uri(homepage)

        if ppa.is_ppa(url):
            url = ppa.get_homepage(url)
        self.url_button.set_label(url)
        self.url_button.set_uri(url)

        self.description_label.set_text(description or _('Description is here'))

    def on_source_changed(self, widget):
        self.emit('call', 'ubuntutweak.modules.sourceeditor', 'update_source_combo', {})

    @log_func(log)
    def on_purge_changed(self, widget, purge_list):
        if purge_list:
            self.purge_ppa_button.set_sensitive(True)
        else:
            self.purge_ppa_button.set_sensitive(False)

    def on_update_button_clicked(self, widget):
        @log_func(log)
        def on_update_finished(transaction, status, parent):
            log.debug("on_update_finished")
            unset_busy(parent)

        set_busy(self)
        daemon = AptWorker(widget.get_toplevel(),
                           finish_handler=on_update_finished,
                           data=self)
        daemon.update_cache()

        self.emit('call', 'ubuntutweak.modules.appcenter', 'update_app_data', {})
        self.emit('call', 'ubuntutweak.modules.updatemanager', 'update_list', {})

    def on_source_data_downloaded(self, widget):
        path = widget.get_downloaded_file()
        tarfile = utdata.create_tarfile(path)

        if tarfile.is_valid():
            tarfile.extract(consts.CONFIG_ROOT)
            self.update_source_data()
            utdata.save_synced_timestamp(SOURCE_ROOT)
            self.update_timestamp()
        else:
            ErrorDialog(_('An error occurred whilst downloading the file')).launch()

    def update_source_data(self):
        global SOURCE_PARSER
        SOURCE_PARSER = SourceParser()

        self.sourceview.model.clear()
        self.sourceview.update_source_model()
        self.cateview.update_cate_model()
        self.cateview.expand_all()

    def on_sync_button_clicked(self, widget):
        dialog = CheckSourceDialog(widget.get_toplevel(), self.url)
        dialog.run()
        dialog.destroy()
        if dialog.status == True:
            dialog = QuestionDialog(_("Update available, Would you like to update?"))
            response = dialog.run()
            dialog.destroy()
            if response == Gtk.ResponseType.YES:
                dialog = FetchingDialog(parent=self.get_toplevel(), url=get_source_data_url())
                dialog.connect('destroy', self.on_source_data_downloaded)
                dialog.run()
                dialog.destroy()
        elif dialog.error == True:
            ErrorDialog(_("Network Error, Please check your network connection or the remote server is down.")).launch()
        else:
            utdata.save_synced_timestamp(SOURCE_ROOT)
            self.update_timestamp()
            InfoDialog(_("No update available.")).launch()

    @log_func(log)
    def on_purge_ppa_button_clicked(self, widget):
        # name_list is to display the name of PPA
        # url_list is to identify the ppa
        set_busy(self)
        name_list = []
        url_list = []
        log.debug("self.sourceview.to_purge: %s" % self.sourceview.to_purge)
        for url in self.sourceview.to_purge:
            name_list.append(ppa.get_short_name(url))
            url_list.append(url)

        log.debug("PPAs to purge: url_list: %s" % url_list)

        package_view = DowngradeView(self)
        package_view.update_downgrade_model(url_list)
        sw = Gtk.ScrolledWindow(shadow_type=Gtk.ShadowType.IN)
        sw.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        select_pkgs = package_view.get_downgrade_packages()
        sw.add(package_view)

        #TODO the logic is a little ugly, need to improve the BaseMessageDialog
        if not select_pkgs:
            message = _("It's safe to purge the PPA, no packages need to be downgraded.")
            sw.hide()
        else:
            message = _("To safely purge the PPA, the following packages must be downgraded.")
            sw.show_all()
            sw.set_size_request(500, 100)

        dialog = QuestionDialog(title=_("You're going to purge \"%s\":") % ', '.join(name_list),
                                message=message)
        dialog.set_resizable(True)
        dialog.get_content_area().pack_start(sw, True, True, 0)
        dialog.show_all()

        response = dialog.run()
        dialog.destroy()
        # Workflow
        # 1. Downgrade all the PPA packages to offical packages
        #TODO Maybe not official? Because anther ppa which is enabled may have newer packages then offical
        # 2. If succeed, disable PPA, or keep it

        if response == Gtk.ResponseType.YES:
            log.debug("The select pkgs is: %s", str(select_pkgs))
            worker = AptWorker(widget.get_toplevel(),
                               finish_handler=self.on_package_work_finished,
                               data={'parent': self,
                                     'url_list': url_list})
            worker.downgrade_packages(select_pkgs)
        else:
            unset_busy(self)

    @log_func(log)
    def on_package_work_finished(self, transaction, status, kwargs):
        unset_busy(self)

        parent = kwargs['parent']
        url_list = kwargs['url_list']

        for url in url_list:
            #TODO remove vendor key
            result = proxy.purge_source(url, '')
            log.debug("Set source: %s to %s" % (url, str(result)))
        self.sourceview.to_purge = []
        self.update_sourceview()

        notify = Notify.Notification(summary=_('PPA has been purged'),
                                     body=_('It is highly recommend to do a "Refresh" source operation.'))
        notify.set_icon_from_pixbuf(self.get_pixbuf(size=48))
        notify.set_hint_string ("x-canonical-append", "")
        notify.show()

########NEW FILE########
__FILENAME__ = sourceeditor
# Ubuntu Tweak - Ubuntu Configuration Tool
#
# Copyright (C) 2007-2011 Tualatrix Chou <tualatrix@gmail.com>
#
# Ubuntu Tweak is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# Ubuntu Tweak is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Ubuntu Tweak; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA

import os
import re
import glob
import time
import thread
import socket
import gettext

from gi.repository import Gtk, Gdk, GObject, Pango

from ubuntutweak.modules  import TweakModule
from ubuntutweak.gui import GuiBuilder
from ubuntutweak.gui.dialogs import ErrorDialog, QuestionDialog
from ubuntutweak.policykit import PK_ACTION_SOURCE
from ubuntutweak.policykit.dbusproxy import proxy
from ubuntutweak.utils.package import AptWorker
from ubuntutweak.admins.desktoprecovery import GetTextDialog
from ubuntutweak.settings import GSetting


SOURCES_LIST = '/etc/apt/sources.list'


class SourceView(Gtk.TextView):
    def __init__(self, path):
        super(SourceView, self).__init__()

        self.path = path
        self.create_tags()
        self.update_content()

        buffer = self.get_buffer()
        buffer.connect('end-user-action', self.on_buffer_changed)

    def on_buffer_changed(self, widget):
        self.update_from_buffer()

    def update_from_buffer(self):
        buffer = self.get_buffer()
        content = self.get_text()

        offset = buffer.get_iter_at_mark(buffer.get_insert()).get_offset()

        buffer.delete(buffer.get_start_iter(), buffer.get_end_iter())
        iter = buffer.get_iter_at_offset(0)
        if content[-2:] == '\n\n':
            content = content[:-1]
        for i, line in enumerate(content.split('\n')):
            self.parse_and_insert(buffer, iter, line, i != content.count('\n'))

        iter = buffer.get_iter_at_offset(offset)
        buffer.place_cursor(iter)

    def update_content(self, content = None):
        buffer = self.get_buffer()
        buffer.delete(buffer.get_start_iter(), buffer.get_end_iter())
        iter = buffer.get_iter_at_offset(0)
        if content is None:
            try:
                content = open(self.path).read()

                for i, line in enumerate(content.split('\n')):
                    self.parse_and_insert(buffer, iter, line, i != content.count('\n'))

            except:
                pass

    def parse_and_insert(self, buffer, iter, line, break_line=False):
        try:
            if line.lstrip().startswith('#'):
                buffer.insert_with_tags_by_name(iter, line, 'full_comment')
                self.insert_line(buffer, iter)
            elif line.strip() == '':
                self.insert_line(buffer, iter)
            else:
                has_end_blank = line.endswith(' ')
                list = line.split()
                if list is None:
                    self.insert_line(buffer, iter)
                elif has_end_blank:
                    list[-1] = list[-1] + ' '
                if len(list) >= 4:
                    type, uri, distro, component = list[0], list[1], list[2], list[3:]

                    buffer.insert_with_tags_by_name(iter, type, 'type')
                    self.insert_blank(buffer, iter)
                    buffer.insert_with_tags_by_name(iter, uri, 'uri')
                    self.insert_blank(buffer, iter)
                    buffer.insert_with_tags_by_name(iter, distro, 'distro')
                    self.insert_blank(buffer, iter)
                    self.seprarte_component(buffer, component, iter)
                    if break_line:
                        self.insert_line(buffer, iter)
                elif len(list) == 3:
                    type, uri, distro = list[0], list[1], list[2]

                    buffer.insert_with_tags_by_name(iter, type, 'type')
                    self.insert_blank(buffer, iter)
                    buffer.insert_with_tags_by_name(iter, uri, 'uri')
                    self.insert_blank(buffer, iter)
                    buffer.insert_with_tags_by_name(iter, distro, 'distro')
                    if break_line:
                        self.insert_line(buffer, iter)
                else:
                    buffer.insert(iter, line)
        except:
            buffer.insert(iter, line)

    def create_tags(self):
        buffer = self.get_buffer()

        buffer.create_tag('full_comment', foreground="blue")
        buffer.create_tag('type', weight=Pango.Weight.BOLD)
        buffer.create_tag('uri', underline=Pango.Underline.SINGLE, foreground='blue')
        buffer.create_tag('distro', weight=Pango.Weight.BOLD)
        buffer.create_tag('component', foreground="red")
        buffer.create_tag('addon_comment', foreground="blue")

    def insert_blank(self, buffer, iter):
        buffer.insert(iter, ' ')

    def insert_line(self, buffer, iter):
        buffer.insert(iter, '\n')

    def seprarte_component(self, buffer, list, iter):
        component = []
        stop_i = -1
        has_comment = False
        for i, text in enumerate(list):
            stop_i = i
            if text[0] != '#':
                component.append(text)
            else:
                has_comment = True
                break

        buffer.insert_with_tags_by_name(iter, ' '.join(component), 'component')
        if has_comment:
            self.insert_blank(buffer, iter)
            buffer.insert_with_tags_by_name(iter, ' '.join(list[stop_i:]), 'addon_comment')

    def get_text(self):
        buffer = self.get_buffer()
        return buffer.get_text(buffer.get_start_iter(), buffer.get_end_iter(), True)

    def set_path(self, path):
        self.path = path

    def get_path(self):
        return self.path


class SourceEditor(TweakModule):
    __title__ = _('Source Editor')
    __desc__ = _('Manually edit your software sources to suit your needs.')
    __icon__ = 'system-software-update'
    __policykit__ = PK_ACTION_SOURCE
    __category__ = 'system'
    _authenticated = False

    def __init__(self):
        TweakModule.__init__(self, 'sourceeditor.ui')

        self.auto_backup_setting = GSetting('com.ubuntu-tweak.tweak.auto-backup')

        self.textview = SourceView(SOURCES_LIST)
        self.textview.set_sensitive(False)
        self.sw1.add(self.textview)
        self.textview.get_buffer().connect('changed', self.on_buffer_changed)

        self.list_selection = self.list_view.get_selection()
        self.list_selection.connect("changed", self.on_selection_changed)

        self.infobar = Gtk.InfoBar()
        self.info_label = Gtk.Label(label='Current view the list')
        self.info_label.set_alignment(0, 0.5)
        self.infobar.get_content_area().add(self.info_label)
        self.infobar.connect("response", self.on_infobar_response)
        self.infobar.add_button(Gtk.STOCK_CLOSE, Gtk.ResponseType.CLOSE)
        self.infobar.hide()
        self.text_vbox.pack_start(self.infobar, False, False, 0)

        self.connect('realize', self.on_ui_realize)
        self.add_start(self.hpaned1)

    def on_ui_realize(self, widget):
        self.infobar.hide()
        self.update_source_model()
        self.list_selection.select_iter(self.list_model.get_iter_first())
        self.auto_backup_button.set_active(self.auto_backup_setting.get_value())
        self.auto_backup_button.connect('toggled', self.on_auto_backup_button_toggled)

    def set_infobar_backup_info(self, name, list_name):
        self.info_label.set_markup(_('You\'re viewing the backup "<b>%(backup_name)s</b>" for '
                                     '"<b>%(list_name)s</b>"') % {'backup_name': name,
                                                                  'list_name': list_name})

    def on_auto_backup_button_toggled(self, widget):
        self.auto_backup_setting.set_value(widget.get_active())

    def on_infobar_response(self, widget, response_id):
        model, iter = self.list_selection.get_selected()

        if iter:
            list_path = model[iter][0]

            self.textview.set_path(list_path)
            self.textview.update_content()

            self.save_button.set_sensitive(False)
            self.redo_button.set_sensitive(False)

            self.infobar.hide()

    def on_selection_changed(self, selection):
        model, iter = selection.get_selected()

        if iter:
            self.textview.set_path(model[iter][0])
            self.update_sourceslist()
            self.update_backup_model()

    def update_source_model(self):
        model = self.list_model

        model.clear()

        model.append(('/etc/apt/sources.list', 'sources.list'))

        SOURCE_LIST_D = '/etc/apt/sources.list.d'

        if not os.path.exists(SOURCE_LIST_D):
            self.source_combo.set_active(0)
            return

        files = glob.glob(SOURCE_LIST_D + '/*.list')
        files.sort()

        for file in files:
            if os.path.isdir(file):
                continue
            model.append((file, os.path.basename(file)))

    def update_backup_model(self):
        def file_cmp(f1, f2):
            return cmp(os.stat(f1).st_ctime, os.stat(f2).st_ctime)

        model, iter = self.list_selection.get_selected()

        if iter:
            source_list = model[iter][0]

            self.backup_model.clear()

            files = glob.glob(source_list + '.*')
            files.sort(cmp=file_cmp, reverse=True)

            for path in files:
                if os.path.isdir(path):
                    continue
                self.backup_model.append((path,
                    os.path.basename(path).split('.list.')[-1].split('.save')[0]))

            if not files:
                self.backup_model.append((None, _('No backup yet')))
                self.backup_edit_button.set_sensitive(False)
                self.backup_delete_button.set_sensitive(False)
                self.recover_button.set_sensitive(False)
                self.backup_view_button.set_sensitive(False)
                self.infobar.hide()
            elif self._authenticated == True:
                self.backup_edit_button.set_sensitive(True)
                self.backup_delete_button.set_sensitive(True)
                self.recover_button.set_sensitive(True)
                self.backup_view_button.set_sensitive(True)

            self.backup_combobox.set_active(0)

    def on_source_combo_changed(self, widget):
        model = widget.get_model()
        iter = widget.get_active_iter()

        if self.has_backup_value(iter):
            self.textview.set_path(model.get_value(iter, 0))
            self.update_sourceslist()

    def on_update_button_clicked(self, widget):
        self.set_busy()
        daemon = AptWorker(widget.get_toplevel(), lambda t, s, d: self.unset_busy())
        daemon.update_cache()

    def update_sourceslist(self):
        self.textview.update_content()
        self.redo_button.set_sensitive(False)
        self.save_button.set_sensitive(False)

    def on_save_button_clicked(self, widget):
        text = self.textview.get_text().strip()

        if self.auto_backup_setting.get_value():
            proxy.backup_source(self.textview.get_path(), self.get_time_stamp())
            self.update_backup_model()

        if proxy.edit_source(self.textview.get_path(), text) == 'error':
            ErrorDialog(message=_('Please check the permission of the '
                                  'sources.list file'),
                        title=_('Save failed!')).launch()
        else:
            self.save_button.set_sensitive(False)
            self.redo_button.set_sensitive(False)

    def on_recover_button_clicked(self, widget):
        model, iter = self.list_selection.get_selected()

        if iter:
            list_path = model[iter][0]
            list_name = model[iter][1]

            backup_iter = self.backup_combobox.get_active_iter()

            if backup_iter:
                backup_path = self.backup_model[backup_iter][0]
                backup_name = self.backup_model[backup_iter][1]

                dialog = QuestionDialog(message=_('Would you like to recover the '
                                        'backup "<b>%(backup_name)s</b>" for "<b>%(list_name)s</b>"?') % \
                                                {'backup_name': backup_name,
                                                 'list_name': list_name})
                response = dialog.run()
                dialog.destroy()

                if response == Gtk.ResponseType.YES:
                    if proxy.restore_source(backup_path, list_path):
                        self.infobar.response(Gtk.ResponseType.CLOSE)
                    else:
                        ErrorDialog(title=_('Recovery Failed!'),
                                   message=_('You may need to check the permission '
                                             'of source list.')).launch()

    def on_backup_view_button_clicked(self, widget=None):
        model, iter = self.list_selection.get_selected()

        if iter:
            list_name = model[iter][1]

            iter = self.backup_combobox.get_active_iter()

            if self.has_backup_value(iter):
                name = self.backup_model[iter][1]
                self.set_infobar_backup_info(name, list_name)

                self.textview.set_path(self.backup_model[iter][0])
                self.textview.update_content()
                self.save_button.set_sensitive(False)
                self.redo_button.set_sensitive(False)

                self.infobar.show()

    def on_backup_combobox_changed(self, widget):
        if self.infobar.get_visible():
            self.on_backup_view_button_clicked()

    def on_backup_button_clicked(self, widget):
        model, iter = self.list_selection.get_selected()

        if iter:
            path = model[iter][0]

            dialog = GetTextDialog(message=_('Please enter the name for your backup:'),
                                   text=self.get_time_stamp())
            response = dialog.run()
            dialog.destroy()
            backup_name = dialog.get_text()

            if response == Gtk.ResponseType.YES and backup_name:
                if self.is_valid_backup_name(backup_name):
                    if proxy.backup_source(path, backup_name):
                        self.update_backup_model()
                    else:
                        ErrorDialog(message=_('Backup Failed!')).launch()
                else:
                    ErrorDialog(message=_('Please only use alphanumeric characters'
                                        ' and "_" and "-".'),
                                title=_('Backup name is invalid')).launch()

    def on_backup_delete_button_clicked(self, widget):
        iter = self.backup_combobox.get_active_iter()
        path = self.backup_model[iter][0]

        dialog = QuestionDialog(message=_('Would you like to delete the backup '
                                          '"<b>%s</b>"?') % os.path.basename(path))
        response = dialog.run()
        dialog.destroy()

        if response == Gtk.ResponseType.YES:
            proxy.delete_source(path)
            self.update_backup_model()

    def on_backup_edit_button_clicked(self, widget):
        iter = self.backup_combobox.get_active_iter()
        path = self.backup_model[iter][0]
        name = self.backup_model[iter][1]

        dialog = GetTextDialog(message=_('Please enter a new name for your backup:'),
                               text=name)
        response = dialog.run()
        dialog.destroy()
        new_name = dialog.get_text()

        if response == Gtk.ResponseType.YES and new_name and name != new_name:
            if self.is_valid_backup_name(new_name):
                proxy.rename_backup(path, name, new_name)
                self.update_backup_model()
            else:
                ErrorDialog(message=_('Please only use alphanumeric characters'
                                    ' and "_" and "-".'),
                            title=_('Backup name is invalid')).launch()

    def on_redo_button_clicked(self, widget):
        dialog = QuestionDialog(message=_('The current content will be lost after reloading!\nDo you wish to continue?'))
        if dialog.run() == Gtk.ResponseType.YES:
            self.textview.update_content()
            self.save_button.set_sensitive(False)
            self.redo_button.set_sensitive(False)

        dialog.destroy()

    def on_buffer_changed(self, buffer):
        if buffer.get_modified():
            self.save_button.set_sensitive(True)
            self.redo_button.set_sensitive(True)
        else:
            self.save_button.set_sensitive(False)
            self.redo_button.set_sensitive(False)

    def on_delete_button_clicked(self, widget):
        if self.textview.get_path() ==  SOURCES_LIST:
            ErrorDialog(_('You can\'t delete sources.list!')).launch()
        else:
            dialog = QuestionDialog(message=_('The "%s" will be deleted!\nDo you wish to continue?') % self.textview.get_path())
            response = dialog.run()
            dialog.destroy()
            if response == Gtk.ResponseType.YES:
                model, iter = self.list_selection.get_selected()

                if iter:
                    list_path = model[iter][0]
                    proxy.delete_source(list_path)
                    self.update_source_model()
                    self.update_backup_model()

    def on_polkit_action(self, widget):
        self._authenticated = True
        self.textview.set_sensitive(True)
        self.delete_button.set_sensitive(True)
        self.recover_button.set_sensitive(True)
        self.backup_button.set_sensitive(True)
        self.backup_edit_button.set_sensitive(True)
        self.backup_delete_button.set_sensitive(True)
        self.backup_view_button.set_sensitive(True)

    def is_valid_backup_name(self, name):
        pattern = re.compile('[\w\-]+')

        match = pattern.search(name)

        return match and name == match.group()

    def has_backup_value(self, iter):
        return iter and self.backup_model[iter][0]

    def get_time_stamp(self):
        return time.strftime('%Y-%m-%d-%H-%M', time.localtime(time.time()))

########NEW FILE########
__FILENAME__ = templates
# Ubuntu Tweak - Ubuntu Configuration Tool
#
# Copyright (C) 2007-2012 Tualatrix Chou <tualatrix@gmail.com>
#
# Ubuntu Tweak is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# Ubuntu Tweak is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Ubuntu Tweak; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA

import os
import shutil
import logging

from gi.repository import Gtk

from ubuntutweak.modules  import TweakModule
from ubuntutweak.admins.userdir import UserdirFile
from ubuntutweak.common.consts import DATA_DIR, CONFIG_ROOT
from ubuntutweak.gui.treeviews import DirView, FlatView
from ubuntutweak.gui.dialogs import ErrorDialog, QuestionDialog
from ubuntutweak.utils import set_label_for_stock_button


log = logging.getLogger("Templates")


def update_dir():
    system_dir = os.path.join(CONFIG_ROOT, 'templates')


    uf = UserdirFile()
    template_dir = uf['XDG_TEMPLATES_DIR']
    if not template_dir:
        template_dir = os.path.expanduser('~/Templates')
        if not os.path.exists(template_dir):
            os.mkdir(template_dir)
        user_dir = template_dir
    user_dir = template_dir

    return system_dir, user_dir


def is_right_path():
    if (os.path.expanduser('~').strip('/') == USER_DIR.strip('/')) or os.path.isfile(USER_DIR):
        return False
    else:
        return True


SYSTEM_DIR, USER_DIR = update_dir()


class DefaultTemplates:
    """This class use to create the default templates"""
    templates = {
            "html-document.html": _("HTML document"),
            "odb-database.odb": _("ODB Database"),
            "ods-spreadsheet.ods": _("ODS Spreadsheet"),
            "odt-document.odt": _("ODT Document"),
            "plain-text-document.txt": _("Plain text document"),
            "odp-presentation.odp": _("ODP Presentation"),
            "python-script.py": _("Python script"),
            "pygtk-example.py": _("Pygtk Example"),
            "shell-script.sh": _("Shell script")
            }

    def create(self):
        if not os.path.exists(SYSTEM_DIR):
            os.makedirs(SYSTEM_DIR)
        for path, des in self.templates.items():
            realname = "%s.%s" % (des, path.split('.')[1])
            if not os.path.exists(os.path.join(SYSTEM_DIR, realname)):
                shutil.copy(os.path.join(DATA_DIR, 'templates/%s' % path), os.path.join(SYSTEM_DIR, realname))

    def remove(self):
        if not os.path.exists(SYSTEM_DIR):
            return
        if os.path.isdir(SYSTEM_DIR):
            for root, dirs, files in os.walk(SYSTEM_DIR, topdown=False):
                for name in files:
                    os.remove(os.path.join(root, name))
                for name in dirs:
                    os.rmdir(os.path.join(root, name))
                    os.rmdir(SYSTEM_DIR)
        else:
            os.unlink(SYSTEM_DIR)
        return


class EnableTemplate(DirView):
    """The treeview to display the enable templates"""
    type = _("Enabled Templates")

    def __init__(self):
        DirView.__init__(self, USER_DIR)


class DisableTemplate(FlatView):
    """The treeview to display the system template"""
    type = _("Disabled Templates")

    def __init__(self):
        FlatView.__init__(self, SYSTEM_DIR, USER_DIR)


class Templates(TweakModule):
    __title__ = _('Templates')
    __desc__ = _('Here you can manage your document templates.\n'
                 'You can add files as templates by dragging them into this window.\n'
                 'You can then create new documents based on these templates from the Nautilus right-click menu.')
    __icon__ = 'x-office-document'
    __utactive__ = True
    __category__ = 'personal'

    def __init__(self):
        TweakModule.__init__(self, 'templates.ui')

        if not is_right_path():
            label = Gtk.Label(label=_('The templates path is incorrect! The current path points to "%s".\nPlease reset it to a location within your Home Folder.') % USER_DIR)

            hbox = Gtk.HBox()
            self.add_start(hbox, False, False, 0)

            hbox.pack_start(label, False, False, 0)

            button = Gtk.Button(stock=Gtk.STOCK_GO_FORWARD)
            button.connect('clicked', self.on_go_button_clicked)
            set_label_for_stock_button(button, _('Go And Set'))
            hbox.pack_end(button, False, False, 0)

            button = Gtk.Button(stock=Gtk.STOCK_EXECUTE)
            button.connect('clicked', self.on_restart_button_clicked)
            set_label_for_stock_button(button, _('Restart This Module'))
            hbox.pack_end(button, False, False, 0)
        else:
            self.create_interface()

    def create_interface(self):
        self.default = DefaultTemplates()
        self.config_test()

        self.add_start(self.hbox1)
        self.show_all()

        self.enable_templates = EnableTemplate()
        self.sw1.add(self.enable_templates)

        self.disable_templates = DisableTemplate()
        self.sw2.add(self.disable_templates)

        hbox = Gtk.HBox(spacing=0)
        self.add_start(hbox, False, False, 0)

        self.enable_templates.connect('drag_data_received', self.on_enable_drag_data_received)
        self.enable_templates.connect('deleted', self.on_enable_deleted)
        self.disable_templates.connect('drag_data_received', self.on_disable_drag_data_received)

        button = Gtk.Button(_("Rebuild System Templates"))
        button.connect("clicked", self.on_rebuild_clicked)
        hbox.pack_end(button, False, False, 5)

    def on_go_button_clicked(self, widget):
        #TODO emit signal to load Userdir
        pass

    def on_restart_button_clicked(self, widget):
        global SYSTEM_DIR, USER_DIR
        SYSTEM_DIR, USER_DIR = update_dir()
        if is_right_path():
            self.remove_all_children()
            self.create_interface()
        else:
            ErrorDialog(message=_('The templates path is still incorrect, please reset it!')).launch()

    def on_enable_deleted(self, widget):
        self.disable_templates.update_model()

    def on_enable_drag_data_received(self, treeview, context, x, y, selection, info, etime):
        self.disable_templates.update_model()

    def on_disable_drag_data_received(self, treeview, context, x, y, selection, info, etime):
        self.enable_templates.update_model()

    def on_rebuild_clicked(self, widget):
        dialog = QuestionDialog(message=_('This will delete all disabled templates.\n'
                                 'Do you wish to continue?'))
        if dialog.run() == Gtk.ResponseType.YES:
            self.default.remove()
            self.default.create()
            self.disable_templates.update_model()
        dialog.destroy()

    def config_test(self):
        #TODO need to test dir with os.R_OK | os.W_OK | os.X_OK
        if not os.path.exists(SYSTEM_DIR):
            self.default.create()

########NEW FILE########
__FILENAME__ = userdir
# Ubuntu Tweak - Ubuntu Configuration Tool
#
# Copyright (C) 2007-2011 Tualatrix Chou <tualatrix@gmail.com>
#
# Ubuntu Tweak is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# Ubuntu Tweak is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Ubuntu Tweak; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA

import os
import gettext

from gi.repository import GObject, Gtk, Gdk, GdkPixbuf

from ubuntutweak.modules import TweakModule
from ubuntutweak.common.inifile import IniFile
from ubuntutweak.gui.dialogs import QuestionDialog, InfoDialog
from ubuntutweak.utils import icon


class UserdirFile(IniFile):
    """Class to parse userdir file"""
    filename = os.path.join(os.path.expanduser("~"), ".config/user-dirs.dirs")
    XDG_DIRS = {
        "XDG_DESKTOP_DIR": _("Desktop"),
        "XDG_DOWNLOAD_DIR": _("Download"),
        "XDG_TEMPLATES_DIR": _("Templates"),
        "XDG_PUBLICSHARE_DIR": _("Public"),
        "XDG_DOCUMENTS_DIR": _("Document"),
        "XDG_MUSIC_DIR": _("Music"),
        "XDG_PICTURES_DIR": _("Pictures"),
        "XDG_VIDEOS_DIR": _("Videos")
    }
    XDG_ICONS = {
        "XDG_DESKTOP_DIR": "desktop",
        "XDG_DOWNLOAD_DIR": "folder-download",
        "XDG_TEMPLATES_DIR": "folder-templates",
        "XDG_PUBLICSHARE_DIR": "folder-publicshare",
        "XDG_DOCUMENTS_DIR": "folder-documents",
        "XDG_MUSIC_DIR": "folder-music",
        "XDG_PICTURES_DIR": "folder-pictures",
        "XDG_VIDEOS_DIR": "folder-videos",
    }

    def __init__(self):
        IniFile.__init__(self, self.filename)

        self.data = self.get_items()

    def __getitem__(self, key):
        return self.data[key]

    def get_items(self):
        dict = {}
        for userdir in self.XDG_DIRS.keys():
            prefix = self.get(userdir).strip('"').split("/")[0]
            if prefix:
                path = os.getenv("HOME") + "/"  + "/".join(self.get(userdir).strip('"').split("/")[1:])
            else:
                path = self.get(userdir).strip('"')

            dict[userdir] = path

        return dict

    def items(self):
        dict = {}
        for userdir in self.XDG_DIRS.keys():
            prefix = self.get(userdir).strip('"').split("/")[0]
            if prefix:
                path = os.getenv("HOME") + "/"  + "/".join(self.get(userdir).strip('"').split("/")[1:])
            else:
                path = self.get(userdir).strip('"')

            dict[userdir] = path

        return dict.items()

    def set_userdir(self, userdir, fullpath):
        dirname = '/'.join(fullpath.split('/')[:3])

        if dirname == os.getenv("HOME"):
            folder = '"$HOME/' + "/".join(fullpath.split('/')[3:]) + '"'
        else:
            folder = '"' + fullpath + '"'

        self.set(userdir, folder)
        self.write()

        if dirname == os.getenv("HOME"):
            folder = os.getenv("HOME") + "/" +  "/".join(fullpath.split('/')[3:])
        else:
            folder = folder.strip('"')

        return folder

    def get_display(self, userdir):
        return self.XDG_DIRS[userdir]

    def get_xdg_icon(self, userdir):
        return icon.get_from_name(self.XDG_ICONS[userdir])

    def get_restorename(self, userdir):
        gettext.bindtextdomain('xdg-user-dirs')
        gettext.textdomain('xdg-user-dirs')

        string = userdir.split('_')[1]
        if string.lower() in 'publicshare':
            string = 'public'

        return gettext.gettext(string.title())


class UserdirView(Gtk.TreeView):
    (COLUMN_ICON,
     COLUMN_NAME,
     COLUMN_DIR,
     COLUMN_PATH,
    ) = range(4)

    def __init__(self):
        GObject.GObject.__init__(self)

        self.uf = UserdirFile()

        self.set_rules_hint(True)
        self.model = self._create_model()
        self.set_model(self.model)
        self._add_columns()

        menu = self._create_popup_menu()
        menu.show_all()
        self.connect('button_press_event', self.button_press_event, menu)

    def button_press_event(self, widget, event, menu):
        if event.type == Gdk.EventType.BUTTON_PRESS and event.button == 3:
            #TODO Maybe pygi broken
            menu.popup(None, None, None, None, event.button, event.time)
        return False

    def on_change_directory(self, widget):
        model, iter = self.get_selection().get_selected()
        userdir = model.get_value(iter, self.COLUMN_DIR)

        dialog = Gtk.FileChooserDialog(_("Choose a folder"), 
                                       action=Gtk.FileChooserAction.SELECT_FOLDER,
                                       buttons=(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
                                                Gtk.STOCK_OPEN, Gtk.ResponseType.ACCEPT))
        dialog.set_current_folder(os.getenv("HOME"))

        if dialog.run() == Gtk.ResponseType.ACCEPT:
            fullpath = dialog.get_filename()
            folder = self.uf.set_userdir(userdir, fullpath)
            model.set_value(iter, self.COLUMN_PATH, folder)

        dialog.destroy()

    def on_restore_directory(self, widget):
        model, iter = self.get_selection().get_selected()
        userdir = model.get_value(iter, self.COLUMN_DIR)

        dialog = QuestionDialog(message=_('Ubuntu Tweak will restore the selected '
            'directory to it\'s default location.\n'
            'However, you must move your files back into place manually.\n'
            'Do you wish to continue?'))

        if dialog.run() == Gtk.ResponseType.YES:
            newdir = os.path.join(os.getenv("HOME"), self.uf.get_restorename(userdir))
            self.uf.set_userdir(userdir, newdir)
            model.set_value(iter, self.COLUMN_PATH, newdir)

            if not os.path.exists(newdir):
                os.mkdir(newdir)
            elif os.path.isfile(newdir):
                os.remove(newdir)
                os.mkdir(newdir)

        dialog.destroy()

    def _create_model(self):
        model = Gtk.ListStore(GdkPixbuf.Pixbuf,
                              GObject.TYPE_STRING,
                              GObject.TYPE_STRING,
                              GObject.TYPE_STRING)

        for dir, path in self.uf.items():
            pixbuf = self.uf.get_xdg_icon(dir)
            name = self.uf.get_display(dir)

            model.append((pixbuf, name, dir, path))

        return model

    def _add_columns(self):
        column = Gtk.TreeViewColumn(_('Directory'))
        column.set_spacing(5)
        column.set_sort_column_id(self.COLUMN_NAME)
        self.append_column(column)

        renderer = Gtk.CellRendererPixbuf()
        column.pack_start(renderer, False)
        column.add_attribute(renderer, 'pixbuf', self.COLUMN_ICON)

        renderer = Gtk.CellRendererText()
        column.pack_start(renderer, True)
        column.add_attribute(renderer, 'text', self.COLUMN_NAME)
        
        renderer = Gtk.CellRendererText()
        column = Gtk.TreeViewColumn(_('Path'), renderer, text=self.COLUMN_PATH)
        column.set_sort_column_id(self.COLUMN_PATH)
        self.append_column(column)

    def _create_popup_menu(self):
        menu = Gtk.Menu()

        change_item = Gtk.MenuItem(label=_('Change'))
        menu.append(change_item)
        change_item.connect('activate', self.on_change_directory)

        restore_item = Gtk.MenuItem(label=_('Restore to default'))
        menu.append(restore_item)
        restore_item.connect('activate', self.on_restore_directory)

        return menu


class UserDir(TweakModule):
    __title__ = _("User Folder")
    __desc__ = _("You can change the paths of default folders here.\n"
                 "Don't change the location of your desktop folder unless you know what you are doing.")
    __icon__ = ['folder-home', 'gnome-fs-home']
    __category__ = 'personal'
    __utactive__ = True

    def __init__(self):
        TweakModule.__init__(self)

        sw = Gtk.ScrolledWindow()
        sw = Gtk.ScrolledWindow(shadow_type=Gtk.ShadowType.IN)
        sw.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        self.add_start(sw, True, True, 0)

        self.dirview = UserdirView()
        self.dirview.get_selection().connect('changed', self.on_selection_changed)
        sw.add(self.dirview)

        hbuttonbox = Gtk.HButtonBox()
        hbuttonbox.set_spacing(12)
        hbuttonbox.set_layout(Gtk.ButtonBoxStyle.END)
        self.add_start(hbuttonbox, False, False, 0)

        self.restore_button = Gtk.Button(_('_Restore'))
        self.restore_button.set_use_underline(True)
        self.restore_button.set_sensitive(False)
        self.restore_button.connect('clicked', self.on_restore_button_clicked)
        hbuttonbox.pack_end(self.restore_button, False, False, 0)

        self.change_button = Gtk.Button(_('_Change'))
        self.change_button.set_use_underline(True)
        self.change_button.set_sensitive(False)
        self.change_button.connect('clicked', self.on_change_button_clicked)
        hbuttonbox.pack_end(self.change_button, False, False, 0)

    def on_change_button_clicked(self, widget):
        self.dirview.on_change_directory(widget)

    def on_restore_button_clicked(self, widget):
        self.dirview.on_restore_directory(widget)

    def on_selection_changed(self, widget):
        if widget.get_selected():
            self.change_button.set_sensitive(True)
            self.restore_button.set_sensitive(True)

########NEW FILE########
__FILENAME__ = daemon
#!/usr/bin/python

# Copyright (C) 2007-2011 Tualatrix Chou <tualatrix@gmail.com>
#
# The class AptAuth is modified from softwareproperty. Author: Michael Vogt <mvo@debian.org>
# The original file is: softwareproperties/AptAuth.py
# GPL v2+
# Copyright (c) 2004 Canonical

import sys
reload(sys)
sys.setdefaultencoding('utf8')
import os
import glob
import fcntl
import shutil
import logging
import tempfile
import subprocess

from subprocess import PIPE

import apt
import apt_pkg
import dbus
import dbus.service
import dbus.mainloop.glib
from gi.repository import GObject

from aptsources.sourceslist import SourcesList

from ubuntutweak import system
from ubuntutweak.utils import ppa
from ubuntutweak.backends import PolicyKitService
from ubuntutweak.policykit import PK_ACTION_TWEAK, PK_ACTION_CLEAN, PK_ACTION_SOURCE
from ubuntutweak.settings.configsettings import ConfigSetting

apt_pkg.init()

log = logging.getLogger('Daemon')

PPA_KEY = '''-----BEGIN PGP PUBLIC KEY BLOCK-----
Version: SKS 1.0.10

mI0ESXTUHwEEAMtdNPmcgQcoPN3JcUcRrmdm1chJSmX6gj28OamOgE3Nxp3XgkDdg/vLFPv6
Tk8zIMxQnvuSpuG1YGp3x8atcKlQAlEHncAo27Vlio6pk8jG+qipDBKq7X7FyXE6X9Peg/k7
t7eXMLwH6ZJFN6IEmvPRTsiiQEd/dXRRuIRhPHirABEBAAG0G0xhdW5jaHBhZCBQUEEgZm9y
IFR1YWxhdHJpWIi2BBMBAgAgBQJJdNQfAhsDBgsJCAcDAgQVAggDBBYCAwECHgECF4AACgkQ
avDhlAYkoiC8mAQAmaxr4Kw/R2WZKde7MfbTPy7O9YoL/NQeThYGwxX6ICVr0IZUj9nxFQ/v
tmhZ59p53bpdR8jpPXjdDwjZIIlxTf72Fky6Ri3/zsC4YRD6idS4c4L50dTy74W6IabCt8GQ
LtJy5YASlEp5OGwRNptRSFxVE59LuOPRo2kvLIAa0Dc=
=3itC
-----END PGP PUBLIC KEY BLOCK-----'''

class AptAuth:
    def __init__(self):
        self.gpg = ["/usr/bin/gpg"]
        self.base_opt = self.gpg + ["--no-options", "--no-default-keyring",
                                    "--secret-keyring", "/etc/apt/secring.gpg",
                                    "--trustdb-name", "/etc/apt/trustdb.gpg",
                                    "--keyring", "/etc/apt/trusted.gpg"]
        self.list_opt = self.base_opt + ["--with-colons", "--batch",
                                         "--list-keys"]
        self.rm_opt = self.base_opt + ["--quiet", "--batch",
                                       "--delete-key", "--yes"]
        self.add_opt = self.base_opt + ["--quiet", "--batch",
                                        "--import"]
        
       
    def list(self):
        res = []
        #print self.list_opt
        p = subprocess.Popen(self.list_opt,stdout=PIPE).stdout
        for line in p.readlines():
            fields = line.split(":")
            if fields[0] == "pub":
                name = fields[9]
                res.append("%s %s\n%s" %((fields[4])[-8:],fields[5], _(name)))
        return res

    def add(self, filename):
        #print "request to add " + filename
        cmd = self.add_opt[:]
        cmd.append(filename)
        p = subprocess.Popen(cmd)
        return (p.wait() == 0)
        
    def update(self):
        cmd = ["/usr/bin/apt-key", "update"]
        p = subprocess.Popen(cmd)
        return (p.wait() == 0)

    def rm(self, key):
        #print "request to remove " + key
        cmd = self.rm_opt[:]
        cmd.append(key)
        p = subprocess.Popen(cmd)
        return (p.wait() == 0)


INTERFACE = "com.ubuntu_tweak.daemon"
PATH = "/com/ubuntu_tweak/daemon"

class Daemon(PolicyKitService):
    #TODO use signal
    liststate = None
    list = SourcesList()
    cache = None
    stable_url = 'http://ppa.launchpad.net/tualatrix/ppa/ubuntu'
    ppa_list = []
    p = None
    SOURCES_LIST = '/etc/apt/sources.list'

    def __init__ (self, bus, mainloop):
        bus_name = dbus.service.BusName(INTERFACE, bus=bus)
        PolicyKitService.__init__(self, bus_name, PATH)
        self.mainloop = mainloop

    def get_cache(self):
        try:
            self.update_apt_cache()
        except Exception, e:
            log.error("Error happened when get_cache(): %s" % str(e))
        finally:
            return self.cache

    @dbus.service.method(INTERFACE,
                         in_signature='b', out_signature='b')
    def update_apt_cache(self, init=False):
        '''if init is true, force to update, or it will update only once'''
        if init or not getattr(self, 'cache'):
            apt_pkg.init()
            self.cache = apt.Cache()

    @dbus.service.method(INTERFACE,
                         in_signature='b', out_signature='bv')
    def check_sources_is_valid(self, convert_source):
        try:
            if not os.path.exists(self.SOURCES_LIST):
                os.system('touch %s' % self.SOURCES_LIST)
        except Exception, e:
            log.error(e)

        self.list.refresh()
        to_add_entry = []
        to_rm_entry = []
        disabled_list = ['']

        for entry in self.list:
            entry_line = entry.str().strip()
            if entry.invalid and not entry.disabled and entry_line and not entry_line.startswith('#'):
                try:
                    entry.set_enabled(False)
                except Exception, e:
                    log.error(e)
                if entry.file not in disabled_list:
                    disabled_list.append(entry.file)
                continue

            if convert_source:
                if os.path.basename(entry.file) == 'sources.list':
                    continue
                log.debug("Check for url: %s, type: %s, filename: %s" % (entry.uri, entry.type, entry.file))
                if ppa.is_ppa(entry.uri):
                    filename = '%s-%s.list' % (ppa.get_source_file_name(entry.uri), entry.dist)
                    if filename != os.path.basename(entry.file):
                        log.debug("[%s] %s need rename to %s" % (entry.type, entry.file, filename))
                        to_rm_entry.append(entry)
                        if os.path.exists(entry.file):
                            log.debug("%s is exists, so remove it" % entry.file)
                            os.remove(entry.file)
                        entry.file = os.path.join(os.path.dirname(entry.file), filename)
                        to_add_entry.append(entry)

        for entry in to_rm_entry:
            log.debug("To remove: ", entry.uri, entry.type, entry.file)
            self.list.remove(entry)


        valid = len(disabled_list) == 1
        if '' in disabled_list and not valid:
            disabled_list.remove('')

        self.list.list.extend(to_add_entry)
        self.list.save()

        return valid, disabled_list

    def _setup_non_block_io(self, io):
        outfd = io.fileno()
        file_flags = fcntl.fcntl(outfd, fcntl.F_GETFL)
        fcntl.fcntl(outfd, fcntl.F_SETFL, file_flags | os.O_NDELAY)

    @dbus.service.method(INTERFACE,
                         in_signature='sb', out_signature='b',
                         sender_keyword='sender')
    def set_source_enable(self, url, enable, sender=None):
        self._check_permission(sender, PK_ACTION_SOURCE)
        self.list.refresh()

        for source in self.list:
            if url in source.str() and source.type == 'deb':
                source.disabled = not enable

        self.list.save()

        for source in self.list:
            if url in source.str() and source.type == 'deb':
                return not source.disabled

    @dbus.service.method(INTERFACE,
                         in_signature='ss', out_signature='b',
                         sender_keyword='sender')
    def purge_source(self, url, key_fingerprint='', sender=None):
        #TODO enable
        self._check_permission(sender, PK_ACTION_SOURCE)
        self.list.refresh()
        to_remove = []

        self.set_source_enable(url, False)

        for source in self.list:
            if url in source.str() and source.type == 'deb':
                to_remove.extend(glob.glob(source.file + "*"))

        for file in to_remove:
            try:
                if file != self.SOURCES_LIST:
                    os.remove(file)
            except Exception, e:
                log.error(e)

        # Must refresh! Because the sources.list.d has been changed
        self.list.refresh()

        # Search for whether there's other source from the same owner, if exists,
        # don't remove the apt-key
        owner_url = "http://" + ppa.PPA_URL + "/" + url.split('/')[3]
        need_remove_key = True

        for source in self.list:
            if owner_url in source.str() and source.type == 'deb':
                need_remove_key = False
                break

        if key_fingerprint and need_remove_key:
            self.rm_apt_key(key_fingerprint)

        for source in self.list:
            if url in source.str() and source.type == 'deb':
                return True

        return False

    @dbus.service.method(INTERFACE,
                         in_signature='ssssb', out_signature='s',
                         sender_keyword='sender')
    def set_entry(self, url, distro, comps, comment, enabled, sender=None):
        self._check_permission(sender, PK_ACTION_SOURCE)
        self.list.refresh()

        if enabled:
            self.list.add('deb', url, distro, comps.split(' '), comment)
            self.list.save()
            return 'enabled'
        else:
            for entry in self.list:
                if url in entry.str():
                    entry.disabled = True

            self.list.save()
            return 'disabled'

    @dbus.service.method(INTERFACE,
                         in_signature='ssssbs', out_signature='s',
                         sender_keyword='sender')
    def set_separated_entry(self, url, distro,
                            comps, comment, enabled, file,
                            sender=None):
        self._check_permission(sender, PK_ACTION_SOURCE)
        self.list.refresh()

        partsdir = apt_pkg.config.find_dir("Dir::Etc::Sourceparts")
        if not os.path.exists(partsdir):
            os.mkdir(partsdir)
        file = os.path.join(partsdir, file+'.list')

        if enabled:
            self.list.add('deb', url, distro, comps.split(' '), comment, -1, file)
            self.list.save()
            return 'enabled'
        else:
            for entry in self.list:
                if url in entry.str():
                    entry.disabled = True

            self.list.save()
            return 'disabled'

    @dbus.service.method(INTERFACE,
                         in_signature='ss', out_signature='',
                         sender_keyword='sender')
    def replace_entry(self, old_url, new_url, sender=None):
        self._check_permission(sender, PK_ACTION_SOURCE)
        self.list.refresh()

        for entry in self.list:
            if old_url in entry.uri:
                entry.uri = entry.uri.replace(old_url, new_url)
            elif new_url in entry.uri and entry.disabled:
                self.list.remove(entry)

        self.list.save()

    @dbus.service.method(INTERFACE,
                         in_signature='', out_signature='')
    def disable_ppa(self):
        self.list.refresh()
        self.ppa_list = []

        for source in self.list:
            if ppa.is_ppa(source.uri) and not source.disabled:
                self.ppa_list.append(source.uri)
                source.set_enabled(False)

        self.list.save()

    @dbus.service.method(INTERFACE,
                         in_signature='', out_signature='')
    def enable_ppa(self):
        self.list.refresh()

        for source in self.list:
            url = source.uri
            if ppa.is_ppa(url) and url in self.ppa_list:
                source.set_enabled(True)

        self.list.save()

    @dbus.service.method(INTERFACE,
                         in_signature='sv', out_signature='')
    def upgrade_sources(self, check_string, source_dict):
        self.list.refresh()

        for source in self.list:
            if source.uri in source_dict:
                source.dist = source_dict[source.uri]
                source.comment = source.comment.split(check_string)[0]
                source.set_enabled(True)

        self.list.save()

    @dbus.service.method(INTERFACE,
                         in_signature='', out_signature='')
    def enable_stable_source(self):
        self.list.refresh()

        for source in self.list:
            if self.stable_url in source.str() and source.type == 'deb' and not source.disabled:
                return

        distro = system.CODENAME

        if distro:
            self.set_separated_entry(self.stable_url, distro, 'main',
                                     'Ubuntu Tweak Stable Source', True,
                                     'ubuntu-tweak-stable')
            self.add_apt_key_from_content(PPA_KEY)

    @dbus.service.method(INTERFACE,
                         in_signature='', out_signature='b')
    def get_stable_source_enabled(self):
        self.list.refresh()

        for source in self.list:
            if self.stable_url in source.str() and source.type == 'deb' and not source.disabled:
                return True

        return False

    @dbus.service.method(INTERFACE,
                         in_signature='', out_signature='s')
    def get_list_state(self):
        if self.liststate:
            return self.liststate
        else:
            return "normal"

    @dbus.service.method(INTERFACE,
                         in_signature='', out_signature='s',
                         sender_keyword='sender')
    def clean_apt_cache(self, sender=None):
        self._check_permission(sender, PK_ACTION_CLEAN)
        os.system('apt-get clean')

        return 'done'

    @dbus.service.method(INTERFACE,
                         in_signature='s', out_signature='b')
    def is_package_installed(self, package):
        try:
            pkg = self.get_cache()[package]
            return pkg.isInstalled
        except Exception, e:
            log.error(e)
        else:
            return False

    @dbus.service.method(INTERFACE,
                         in_signature='s', out_signature='b')
    def is_package_upgradable(self, package):
        try:
            pkg = self.get_cache()[package]
            return pkg.isUpgradable
        except Exception, e:
            log.error(e)
        else:
            return False

    @dbus.service.method(INTERFACE,
                         in_signature='s', out_signature='b')
    def is_package_avaiable(self, package):
        try:
            return self.get_cache().has_key(package)
        except Exception, e:
            log.error(e)
            return False
        else:
            return False

    @dbus.service.method(INTERFACE,
                         in_signature='ss', out_signature='',
                         sender_keyword='sender')
    def link_file(self, src, dst, sender=None):
        self._check_permission(sender, PK_ACTION_TWEAK)
        if not os.path.exists(dst):
            os.symlink(src, dst)

    @dbus.service.method(INTERFACE,
                         in_signature='s', out_signature='',
                         sender_keyword='sender')
    def unlink_file(self, path, sender=None):
        self._check_permission(sender, PK_ACTION_TWEAK)
        if os.path.exists(path) and os.path.islink(path):
            os.unlink(path)

    @dbus.service.method(INTERFACE,
                         in_signature='s', out_signature='',
                         sender_keyword='sender')
    def set_list_state(self, state, sender=None):
        self._check_permission(sender, PK_ACTION_SOURCE)
        self.liststate = state

    @dbus.service.method(INTERFACE,
                         in_signature='ss', out_signature='s',
                         sender_keyword='sender')
    def edit_source(self, path, content, sender=None):
        self._check_permission(sender, PK_ACTION_SOURCE)
        if path.startswith(self.SOURCES_LIST):
            try:
                file = open(path, 'w')
                file.write(content)
                file.close()
            except Exception, e:
                log.error(e)
                return 'error'
            finally:
                return 'done'
        else:
            return 'error'

    @dbus.service.method(INTERFACE,
                         in_signature='s', out_signature='s',
                         sender_keyword='sender')
    def delete_source(self, path, sender=None):
        self._check_permission(sender, PK_ACTION_SOURCE)
        if path.startswith(self.SOURCES_LIST):
            os.system('rm "%s"' % path)
            if os.path.exists(path):
                return 'error'
            else:
                return 'done'
        else:
            return 'error'

    @dbus.service.method(INTERFACE,
                         in_signature='ss', out_signature='b',
                         sender_keyword='sender')
    def backup_source(self, path, backup_name, sender=None):
        self._check_permission(sender, PK_ACTION_SOURCE)
        if path.startswith(self.SOURCES_LIST):
            new_path = path + '.' + backup_name + '.save'
            shutil.copy(path, new_path)
            return os.path.exists(new_path)
        else:
            return False

    @dbus.service.method(INTERFACE,
                         in_signature='ss', out_signature='b',
                         sender_keyword='sender')
    def restore_source(self, backup_path, restore_path, sender=None):
        self._check_permission(sender, PK_ACTION_SOURCE)
        if restore_path.startswith(self.SOURCES_LIST) and \
                restore_path in backup_path:
            shutil.copy(backup_path, restore_path)
            return True
        else:
            return False

    @dbus.service.method(INTERFACE,
                         in_signature='sss', out_signature='b',
                         sender_keyword='sender')
    def rename_backup(self, backup_path, name, new_name, sender=None):
        self._check_permission(sender, PK_ACTION_SOURCE)

        if backup_path.startswith(self.SOURCES_LIST) and name and new_name:
            os.rename(backup_path, backup_path.replace(name, new_name))
            return True
        else:
            return False

    @dbus.service.method(INTERFACE,
                         in_signature='s', out_signature='',
                         sender_keyword='sender')
    def clean_configs(self, pkg, sender=None):
        self._check_permission(sender, PK_ACTION_CLEAN)
        cmd = ['sudo', 'dpkg', '--purge']
        cmd.append(pkg)
        self.p = subprocess.Popen(cmd, stdout=PIPE)
        self._setup_non_block_io(self.p.stdout)

    @dbus.service.method(INTERFACE,
                         in_signature='as', out_signature='',
                         sender_keyword='sender')
    def install_select_pkgs(self, pkgs, sender=None):
        self._check_permission(sender, PK_ACTION_CLEAN)
        cmd = ['sudo', 'apt-get', '-y', '--force-yes', 'install']
        cmd.extend(pkgs)
        log.debug("The install command is %s" % ' '.join(cmd))
        self.p = subprocess.Popen(cmd, stdout=PIPE)
        self._setup_non_block_io(self.p.stdout)

    @dbus.service.method(INTERFACE,
                         in_signature='', out_signature='v')
    def get_cmd_pipe(self):
        if self.p:
            terminaled = self.p.poll()
            if terminaled == None:
                try:
                    return self.p.stdout.readline(), str(terminaled)
                except:
                    return '', 'None'
            else:
                strings, returncode = ''.join(self.p.stdout.readlines()), str(terminaled)
                self.p = None
                return strings, returncode
        else:
            return '', 'None'

    @dbus.service.method(INTERFACE,
                         in_signature='s', out_signature='',
                         sender_keyword='sender')
    def add_apt_key_from_content(self, content, sender=None):
        #TODO leave only one method
        self._check_permission(sender, PK_ACTION_SOURCE)

        f = tempfile.NamedTemporaryFile()
        f.write(content)
        f.flush()

        apt_key = AptAuth()
        apt_key.add(f.name)
        f.close()

    @dbus.service.method(INTERFACE,
                         in_signature='s', out_signature='',
                         sender_keyword='sender')
    def rm_apt_key(self, key_id, sender=None):
        self._check_permission(sender, PK_ACTION_SOURCE)

        apt_key = AptAuth()
        apt_key.rm(key_id)

    @dbus.service.method(INTERFACE,
                         in_signature='s', out_signature='b',
                         sender_keyword='sender')
    def delete_apt_cache_file(self, file_name, sender=None):
        self._check_permission(sender, PK_ACTION_CLEAN)

        full_path = os.path.join('/var/cache/apt/archives/', file_name)
        if os.path.exists(full_path):
            os.remove(full_path)

        return not os.path.exists(full_path)

    @dbus.service.method(INTERFACE,
                         in_signature='s', out_signature='b')
    def is_exists(self, path):
        return os.path.exists(path)

    @dbus.service.method(INTERFACE,
                         in_signature='ss', out_signature='',
                         sender_keyword='sender')
    def set_login_logo(self, src, dest, sender=None):
        '''This is called by tweaks/loginsettings.py'''
        self._check_permission(sender, PK_ACTION_TWEAK)
        if not self.is_exists(os.path.dirname(dest)):
           os.makedirs(os.path.dirname(dest))
        self._delete_old_logofile(dest)
        shutil.copy(src, dest)

    def _delete_old_logofile(self, dest):
        for old in glob.glob(os.path.splitext(dest)[0] + ".*"):
            os.remove(old)

    @dbus.service.method(INTERFACE,
                         in_signature='s', out_signature='',
                         sender_keyword='sender')
    def unset_login_logo(self, dest, sender=None):
        '''This is called by tweaks/loginsettings.py'''
        self._check_permission(sender, PK_ACTION_TWEAK)

        if dest.startswith(os.path.expanduser('~gdm/.icons')):
            self._delete_old_logofile(dest)

    @dbus.service.method(INTERFACE,
                         in_signature='s', out_signature='b')
    def is_link(self, path):
        return os.path.islink(path)

    @dbus.service.method(INTERFACE,
                         in_signature='si', out_signature='s')
    def get_as_tempfile(self, path, uid):
        f = tempfile.NamedTemporaryFile()
        new_path = f.name
        f.close()
        os.popen('cp %s %s' % (path, new_path))
        os.chown(new_path, uid, uid)
        return new_path

    @dbus.service.method(INTERFACE,
                         in_signature='ss', out_signature='s')
    def get_user_gconf(self, user, key):
        command = 'sudo -u %s gconftool-2 --get %s' % (user, key)
        cmd = os.popen(command)
        return cmd.read().strip()

    @dbus.service.method(INTERFACE,
                         in_signature='sssss', out_signature='s',
                         sender_keyword='sender')
    def set_user_gconf(self, user, key, value, type, list_type='', sender=None):
        self._check_permission(sender, PK_ACTION_TWEAK)
        command = 'sudo -u %s gconftool-2 --type %s' % (user, type)
        # Use "" to make sure the value with space will be set correctly
        if list_type == '':
            command = '%s --set %s "%s"' % (command, key, value)
        else:
            command = '%s --type %s --list-type %s --set %s "%s"' % (command,
                                                                   list_type,
                                                                   key, value)
        cmd = os.popen(command)
        return cmd.read().strip()

    @dbus.service.method(INTERFACE,
                         in_signature='s', out_signature='s')
    def get_system_gconf(self, key):
        command = 'gconftool-2 --direct --config-source xml:readwrite:/etc/gconf/gconf.xml.defaults --get %s' % key
        cmd = os.popen(command)
        output = cmd.read().strip()
        log.debug('get_system_gconf: %s is %s' % (key, output))
        return output

    @dbus.service.method(INTERFACE,
                         in_signature='ssss', out_signature='s',
                         sender_keyword='sender')
    def set_system_gconf(self, key, value, type, list_type='', sender=None):
        self._check_permission(sender, PK_ACTION_TWEAK)
        log.debug('set_system_gconf: %s to %s' % (key, value))
        if list_type == '':
            command = 'gconftool-2 --direct --config-source xml:readwrite:/etc/gconf/gconf.xml.defaults --type %s --set %s %s' % (type, key, value)
        else:
            command = 'gconftool-2 --direct --config-source xml:readwrite:/etc/gconf/gconf.xml.defaults --type %s --list-type %s --set %s %s' % (type, list_type, key, value)
        cmd = os.popen(command)
        output = cmd.read().strip()
        return output

    @dbus.service.method(INTERFACE,
                         in_signature='ss', out_signature='b',
                         sender_keyword='sender')
    def set_config_setting(self, key, value, sender=None):
        self._check_permission(sender, PK_ACTION_TWEAK)
        log.debug('set_config_setting: %s to %s' % (key, value))
        cs = ConfigSetting(key)
        cs.set_value(value)

        if cs.is_override_schema():
            os.system('glib-compile-schemas /usr/share/glib-2.0/schemas/')

        return value == cs.get_value()

    @dbus.service.method(INTERFACE,
                         in_signature='', out_signature='')
    def exit(self):
        self.mainloop.quit()

if __name__ == '__main__':
    dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
    mainloop = GObject.MainLoop()
    Daemon(dbus.SystemBus(), mainloop)
    mainloop.run()

########NEW FILE########
__FILENAME__ = cleanerinfo
import os
import glob
from gi.repository import Gtk, GLib

from ubuntutweak import system
from ubuntutweak.clips import Clip
from ubuntutweak.utils import icon

class CleanerInfo(Clip):
    __icon__  = 'computerjanitor'
    __title__ = _('Your system is clean')

    def __init__(self):
        Clip.__init__(self)

        cache_number = len(glob.glob('/var/cache/apt/archives/*.deb'))

        if cache_number:
            self.set_title(_('Some cache can be cleaned to free your disk space'))

        label = Gtk.Label(label=_('%s cache packages can be cleaned.') % cache_number)
        label.set_alignment(0, 0.5)

        self.add_content(label)

        try:
            if system.CODENAME in ['precise']:
                root_path = '~/.thumbnails'
            else:
                root_path = '~/.cache/thumbnails'

            size = int(os.popen('du -bs %s' % root_path).read().split()[0])
        except:
            size = 0

        if size:

            label = Gtk.Label(label=_('%s thumbnails cache can be cleaned.') % \
                    GLib.format_size_for_display(size))
            label.set_alignment(0, 0.5)

            self.add_content(label)

        button = Gtk.Button(label=_('Start Janitor'))
        button.connect('clicked', self.on_button_clicked)
        self.add_action_button(button)

        self.show_all()

    def on_button_clicked(self, widget):
        self.emit('load_feature', 'janitor')

########NEW FILE########
__FILENAME__ = hardwareinfo
import os
from gi.repository import Gtk, GLib

from ubuntutweak import system
from ubuntutweak.clips import Clip
from ubuntutweak.utils import icon
from ubuntutweak.gui.containers import EasyTable

class HardwareInfo(Clip):
    __icon__  = 'computer'
    __title__ = _('Hardware Information')

    def __init__(self):
        Clip.__init__(self)

        cpumodel = _('Unknown')

        if os.uname()[4][0:3] == "ppc":
            for element in file("/proc/cpuinfo"):
                if element.split(":")[0][0:3] == "cpu":
                    cpumodel = element.split(":")[1].strip()
        else:
            for element in file("/proc/cpuinfo"):
                if element.split(":")[0] == "model name\t":
                    cpumodel = element.split(":")[1].strip()

        for element in file("/proc/meminfo"):
            if element.split(" ")[0] == "MemTotal:":
                raminfo = element.split(" ")[-2]

        self.table = EasyTable(items=(
                        (Gtk.Label(label=_('CPU:')),
                         Gtk.Label(label=cpumodel)),
                        (Gtk.Label(label=_('Memory:')),
                         Gtk.Label(label=GLib.format_size_for_display(int(raminfo) * 1024))),
                        ),
                        xpadding=12, ypadding=2)
        self.add_content(self.table)

        self.show_all()

########NEW FILE########
__FILENAME__ = systeminfo
import os
from gi.repository import Gtk

from ubuntutweak import system
from ubuntutweak.clips import Clip
from ubuntutweak.utils import icon
from ubuntutweak.gui.containers import EasyTable

class SystemInfo(Clip):
    __icon__ = 'distributor-logo'
    __title__ = _('Ubuntu Desktop Information')

    def __init__(self):
        Clip.__init__(self)

        self.table = EasyTable(items=(
                        (Gtk.Label(label=_('Hostname:')),
                         Gtk.Label(label=os.uname()[1])),
                        (Gtk.Label(label=_('Platform:')),
                         Gtk.Label(label=os.uname()[-1])),
                        (Gtk.Label(label=_('Distribution:')),
                         Gtk.Label(label=system.DISTRO)),
                        (Gtk.Label(label=_('Desktop Environment:')),
                         Gtk.Label(label=system.DESKTOP_FULLNAME))),
                        xpadding=12, ypadding=2)
        self.add_content(self.table)

        self.show_all()

########NEW FILE########
__FILENAME__ = updateinfo
import os
import time
import stat
from gettext import ngettext

from gi.repository import Gtk

from ubuntutweak.clips import Clip
from ubuntutweak.utils import icon

class UpdateInfo(Clip):
    __icon__ = 'system-software-update'
    __title__ = _('Your system is up-to-date')

    NO_UPDATE_WARNING_DAYS = 7

    def __init__(self):
        Clip.__init__(self)

        label = Gtk.Label(label=self._get_last_apt_get_update_text())
        label.set_alignment(0, 0.5)

        self.add_content(label)

        self.show_all()

    # The following two function are copyed from UpdateManager/UpdateManager.py
    def _get_last_apt_get_update_hours(self):
        """
        Return the number of hours since the last successful apt-get update
      
        If the date is unknown, return "None"
        """
        if not os.path.exists("/var/lib/apt/periodic/update-success-stamp"):
            return None
        # calculate when the last apt-get update (or similar operation)
        # was performed
        mtime = os.stat("/var/lib/apt/periodic/update-success-stamp")[stat.ST_MTIME]
        ago_hours = int((time.time() - mtime) / (60*60) )
        return ago_hours

    def _get_last_apt_get_update_text(self):
        """
        return a human readable string with the information when
        the last apt-get update was run
        """
        ago_hours = self._get_last_apt_get_update_hours()
        if ago_hours is None:
            return _("It is unknown when the package information was "
                     "updated last. Please try clicking on the 'Check' "
                     "button to update the information.")
        ago_days = int( ago_hours / 24 )
        if ago_days > self.NO_UPDATE_WARNING_DAYS:
            return _("The package information was last updated %(days_ago)s "
                     "days ago.\n"
                     "Press the 'Check' button below to check for new software "
                     "updates.") % { "days_ago" : ago_days, }
        elif ago_days > 0:
            return ngettext("The package information was last updated %(days_ago)s day ago.",
                            "The package information was last updated %(days_ago)s days ago.",
                            ago_days) % { "days_ago" : ago_days, }
        elif ago_hours > 0:
            return ngettext("The package information was last updated %(hours_ago)s hour ago.",
                            "The package information was last updated %(hours_ago)s hours ago.",
                            ago_hours) % { "hours_ago" : ago_hours, }
        else:
            return _("The package information was last updated less than one hour ago.")
        return None

########NEW FILE########
__FILENAME__ = userinfo
import os
from gi.repository import Gtk, GLib

from ubuntutweak.clips import Clip
from ubuntutweak.utils import icon
from ubuntutweak.gui.containers import EasyTable

class UserInfo(Clip):
    __icon__  = 'config-users'
    __title__ = _('User Information')

    def __init__(self):
        Clip.__init__(self)

        self.table = EasyTable(items=(
                        (Gtk.Label(label=_('Current user:')),
                         Gtk.Label(label=GLib.get_user_name())),
                        (Gtk.Label(label=_('Home directory:')),
                         Gtk.Label(label=GLib.get_home_dir())),
                        (Gtk.Label(label=_('Shell:')),
                         Gtk.Label(label=GLib.getenv('SHELL'))),
                        (Gtk.Label(label=_('Language:')),
                         Gtk.Label(label=GLib.getenv('LANG')))),
                        xpadding=12, ypadding=2)

        self.add_content(self.table)

        self.show_all()

########NEW FILE########
__FILENAME__ = config
#!/usr/bin/python

# Ubuntu Tweak - PyGTK based desktop configuration tool
#
# Copyright (C) 2007-2008 TualatriX <tualatrix@gmail.com>
#
# Ubuntu Tweak is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# Ubuntu Tweak is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Ubuntu Tweak; if not, write to the Free Software Foundation, Inc.,

import os
import gtk
import gconf

from ubuntutweak.conf import GconfSetting
from ubuntutweak.common.factory import GconfKeys

class Config(GconfSetting):
    def set_value_from_key(self, key, value):
        self.set_key(key)
        self.set_value(value)

    def get_value_from_key(self, key, default=None):
        self.set_key(key)
        self.set_default(default)
        return self.get_value()

class TweakSettings:
    '''Manage the settings of ubuntu tweak'''
    config = Config()

    url = 'tweak_url'
    version = 'tweak_version'
    toolbar_size = 'toolbar_size'
    window_size= 'window_size'
    window_height = 'window_height'
    window_width = 'window_width'
    show_donate_notify = 'show_donate_notify'
    default_launch = 'default_launch'
    check_update = 'check_update'
    sync_notify = 'sync_notify'
    separated_sources = 'separated_sources'
    use_mirror_ppa = 'use_mirror_ppa'
    enable_new_item = 'enable_new_item'
    need_save = True

    @classmethod
    def get_enable_new_item(cls):
        return cls.config.get_value_from_key(cls.enable_new_item, default=True)

    @classmethod
    def set_enable_new_item(cls, bool):
        cls.config.set_value_from_key(cls.enable_new_item, bool)

    @classmethod
    def get_check_update(cls):
        return cls.config.get_value_from_key(cls.check_update, default=True)

    @classmethod
    def set_check_update(cls, bool):
        cls.config.set_value_from_key(cls.check_update, bool)

    @classmethod
    def set_default_launch(cls, id):
        cls.config.set_value_from_key(cls.default_launch, id)

    @classmethod
    def get_default_launch(cls):
        return cls.config.get_value_from_key(cls.default_launch)

    @classmethod
    def set_show_donate_notify(cls, bool):
        return cls.config.set_value_from_key(cls.show_donate_notify, bool)

    @classmethod
    def get_show_donate_notify(cls):
        return cls.config.get_value_from_key(cls.show_donate_notify, default=True)

    @classmethod
    def set_sync_notify(cls, bool):
        return cls.config.set_value_from_key(cls.sync_notify, bool)

    @classmethod
    def get_sync_notify(cls):
        return cls.config.get_value_from_key(cls.sync_notify, default=True)

    def set_use_mirror_ppa(cls, bool):
        return cls.config.set_value_from_key(cls.use_mirror_ppa, bool)

    @classmethod
    def get_use_mirror_ppa(cls):
        return cls.config.get_value_from_key(cls.use_mirror_ppa, default=False)

    @classmethod
    def set_separated_sources(cls, bool):
        return cls.config.set_value_from_key(cls.separated_sources, bool)

    @classmethod
    def get_separated_sources(cls):
        return cls.config.get_value_from_key(cls.separated_sources, default=True)

    @classmethod
    def set_url(cls, url):
        return cls.config.set_value_from_key(cls.url, url)

    @classmethod
    def get_url(cls):
        return cls.config.get_value_from_key(cls.url)

    @classmethod
    def set_version(cls, version):
        return cls.config.set_value_from_key(cls.version, version)

    @classmethod
    def get_version(cls):
        return cls.config.get_value_from_key(cls.version)

    @classmethod
    def set_paned_size(cls, size):
        cls.config.set_value_from_key(cls.toolbar_size, size)

    @classmethod
    def get_paned_size(cls):
        position = cls.config.get_value_from_key(cls.toolbar_size)

        if position:
            return position
        else:
            return 150

    @classmethod
    def set_window_size(cls, width, height):
        cls.config.set_value_from_key(cls.window_width, width)
        cls.config.set_value_from_key(cls.window_height, height)

    @classmethod
    def get_window_size(cls):
        width = cls.config.get_value_from_key(cls.window_width, default=900)
        height = cls.config.get_value_from_key(cls.window_height, default=500)

        return (width, height)

    @classmethod
    def get_icon_theme(cls):
        return cls.config.get_value_from_key('/desktop/gnome/interface/icon_theme')

if __name__ == '__main__':
    print Config().get_value_from_key('show_donate_notify')

########NEW FILE########
__FILENAME__ = consts
__all__ = (
        'APP',
        'PACKAGE',
        'VERSION',
        'DATA_DIR',
        'init_locale',
        )

import os
import glob
import gettext

from gi.repository import GLib, Notify

from ubuntutweak import __version__

def applize(package):
    return ' '.join([a.capitalize() for a in package.split('-')])

PACKAGE = 'ubuntu-tweak'
VERSION = __version__
PKG_VERSION = VERSION
IS_TESTING = False
DATA_DIR = '/usr/share/ubuntu-tweak/'
APP = applize(PACKAGE)
CONFIG_ROOT = os.path.join(GLib.get_user_config_dir(), 'ubuntu-tweak')
TEMP_ROOT = os.path.join(CONFIG_ROOT, 'temp')
IS_INSTALLED = True

if not os.path.exists(TEMP_ROOT):
    os.makedirs(TEMP_ROOT)

try:
    LANG = os.getenv('LANG').split('.')[0].lower().replace('_','-')
except:
    LANG = 'en-us'

if not __file__.startswith('/usr'):
    datadir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))
    DATA_DIR = os.path.join(datadir, 'data')
    IS_INSTALLED = False

try:
    PKG_VERSION = os.popen("dpkg-query -f '${Version}' -W %s" % PACKAGE).read()
    IS_TESTING = '+' in PKG_VERSION
    if IS_TESTING:
        VERSION = PKG_VERSION
except Exception, e:
    print(e)

def init_locale():
    global INIT
    try:
        INIT
    except:
        gettext.install(PACKAGE, unicode=True)

        INIT = True

def install_ngettext():
    #FIXME
    gettext.bindtextdomain(PACKAGE, "/usr/share/locale")
    gettext.textdomain(PACKAGE)

init_locale()

if not Notify.init('ubuntu-tweak'):
    pass

#TODO remove this in the future
OLD_CONFIG_ROOT = os.path.expanduser('~/.ubuntu-tweak/')
if not glob.glob(os.path.expanduser('~/.ubuntu-tweak/*')) and os.path.exists(OLD_CONFIG_ROOT):
    os.rmdir(OLD_CONFIG_ROOT)

########NEW FILE########
__FILENAME__ = debug
#!/usr/bin/python

# Ubuntu Tweak - PyGTK based desktop configuration tool
#
# Copyright (C) 2007-2010 TualatriX <tualatrix@gmail.com>
# The Logging System is hacked from Conduit
# Copyright (C) Conduit Authors
#
# Ubuntu Tweak is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# Ubuntu Tweak is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Ubuntu Tweak; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA

import os
import logging
import StringIO
import traceback
import webbrowser

from gi.repository import Gtk, Gdk, Notify

from ubuntutweak import system
from ubuntutweak.common.consts import CONFIG_ROOT

#The terminal has 8 colors with codes from 0 to 7
BLACK, RED, GREEN, YELLOW, BLUE, MAGENTA, CYAN, WHITE = range(8)

#These are the sequences need to get colored ouput
RESET_SEQ = "\033[0m"
COLOR_SEQ = "\033[1;%dm"
BOLD_SEQ =  "\033[1m"

#The background is set with 40 plus the number of the color,
#and the foreground with 30
COLORS = {
    'WARNING':  COLOR_SEQ % (30 + YELLOW) + 'WARNING' + RESET_SEQ,
    'INFO':     COLOR_SEQ % (30 + WHITE) + 'INFO' + RESET_SEQ,
    'DEBUG':    COLOR_SEQ % (30 + BLUE) + 'DEBUG' + RESET_SEQ,
    'CRITICAL': COLOR_SEQ % (30 + YELLOW) + 'CRITICAL' + RESET_SEQ,
    'ERROR':    COLOR_SEQ % (30 + RED) + 'ERROR' + RESET_SEQ,
}


def on_copy_button_clicked(widget, text):
    atom = Gdk.atom_intern('CLIPBOARD', True)
    clipboard = Gtk.Clipboard.get_for_display(Gdk.Display.get_default(), atom)
    clipboard.set_text(text, -1)

    notify = Notify.Notification()
    notify.update(summary=_('Error message has been copied'),
                  body=_('Now click "Report" to enter the bug '
                         'report website. Make sure to attach the '
                         'error message in "Further information".'),
                  icon='ubuntu-tweak')
    notify.show()


def run_traceback(level, textview_only=False, text_only=False):
    '''Two level: fatal and error'''
    from ubuntutweak.gui import GuiBuilder

    output = StringIO.StringIO()
    exc = traceback.print_exc(file=output)

    worker = GuiBuilder('traceback.ui')

    textview = worker.get_object('%s_view' % level)

    buffer = textview.get_buffer()
    iter = buffer.get_start_iter()
    anchor = buffer.create_child_anchor(iter)
    button = Gtk.Button(label=_('Copy Error Message'))
    button.show()

    textview.add_child_at_anchor(button, anchor)

    error_text = "\nDistribution: %s\nApplication: %s\nDesktop:%s\n\n%s" % (system.DISTRO,
                                       system.APP,
                                       system.DESKTOP,
                                       output.getvalue())

    buffer.insert(iter, error_text)
    button.connect('clicked', on_copy_button_clicked, error_text)

    if text_only:
        return error_text

    if textview_only:
        return textview
    else:
        dialog = worker.get_object('%sDialog' % level.capitalize())

        to_report = (dialog.run() == Gtk.ResponseType.YES)

        dialog.destroy()
        output.close()

        if to_report:
            open_bug_report()

def get_traceback():
    return run_traceback('error', text_only=True)

def log_traceback(log):
    log.error(get_traceback())

def open_bug_report():
    if system.is_supported():
        webbrowser.open('https://bugs.launchpad.net/ubuntu-tweak/+filebug')
    else:
        from ubuntutweak.gui.dialogs import ErrorDialog
        ErrorDialog(title=_("Sorry, your distribution is not supported by Ubuntu Tweak"),
                    message=_("You can't file bug for this issue. Please only use Ubuntu Tweak on Ubuntu. Or it may kill your cat.")).launch()


class ColoredFormatter(logging.Formatter):
    def __init__(self, msg, use_color=True):
        logging.Formatter.__init__(self, msg)
        self.use_color = use_color

    def format(self, record):
        if self.use_color:
            record.levelname = COLORS.get(record.levelname, record.levelname)
        return logging.Formatter.format(self, record)


class TweakLogger(logging.Logger):
    COLOR_FORMAT = "[" + BOLD_SEQ + "%(name)s" + RESET_SEQ + \
                   "][%(levelname)s] %(message)s (" + BOLD_SEQ + \
                   "%(filename)s" + RESET_SEQ + ":%(lineno)d)"
    NO_COLOR_FORMAT = "[%(name)s][%(levelname)s] %(message)s " \
                      "(%(filename)s:%(lineno)d)"
    LOG_FILE_HANDLER = None

    def __init__(self, name):
        logging.Logger.__init__(self, name)

        #Add two handlers, a stderr one, and a file one
        color_formatter = ColoredFormatter(TweakLogger.COLOR_FORMAT)
        no_color_formatter = ColoredFormatter(TweakLogger.NO_COLOR_FORMAT,
                                              False)

        #create the single file appending handler
        if TweakLogger.LOG_FILE_HANDLER == None:
            filename = os.path.join(CONFIG_ROOT, 'ubuntu-tweak.log')
            TweakLogger.LOG_FILE_HANDLER = logging.FileHandler(filename, 'w')
            TweakLogger.LOG_FILE_HANDLER.setFormatter(no_color_formatter)

        console = logging.StreamHandler()
        console.setFormatter(color_formatter)

        self.addHandler(TweakLogger.LOG_FILE_HANDLER)
        self.addHandler(console)
        return


def enable_debugging():
    logging.getLogger().setLevel(logging.DEBUG)


def disable_debugging():
    logging.getLogger().setLevel(logging.INFO)


def disable_logging():
    logging.getLogger().setLevel(logging.CRITICAL + 1)

logging.setLoggerClass(TweakLogger)

def log_func(log):
    def wrap(func):
        def func_wrapper(*args, **kwargs):
            log.debug("%s:" % func)
            for i, arg in enumerate(args):
                log.debug("\targs-%d: %s" % (i + 1, arg))
            for k, v in enumerate(kwargs):
                log.debug("\tdict args-%d: %s: %s" % (k, v, kwargs[v]))
            return func(*args, **kwargs)
        return func_wrapper
    return wrap

########NEW FILE########
__FILENAME__ = download
#!/usr/bin/python

import urllib

class Download:
    def __init__(self, remote_uri, local_uri):
        urllib.urlretrieve(remote_uri, local_uri, self.update_progress)

    def update_progress(self, blocks, block_size, total_size):
        percentage = float(blocks * block_size) / total_size
        print percentage

if __name__ == '__main__':
    Download('http://ubuntu.cn99.com/ubuntu/pool/main/g/gedit/gedit_2.22.3.orig.tar.gz', 'gedit_2.22.3.orig.tar.gz')

########NEW FILE########
__FILENAME__ = inifile
"""
Base Class for DesktopEntry, IconTheme and IconData
"""

import os.path
import codecs

class IniFile:
    filename = ''

    def __init__(self, filename=None):
        self.content = dict()
        if filename:
            self.parse(filename)

    def parse(self, filename):
        # for performance reasons
        content = self.content

        if not os.path.isfile(filename):
            return

        # parse file
        try:
            file(filename, 'r')
        except IOError:
            return

        for line in file(filename,'r'):
            line = line.strip()
            # empty line
            if not line:
                continue
            # comment
            elif line[0] == '#':
                continue
            # key
            else:
                index = line.find("=")
                key = line[0:index].strip()
                value = line[index+1:].strip()
                if self.hasKey(key):
                    continue
                else:
                    content[key] = value

        self.filename = filename

    def get(self, key):
        if key not in self.content.keys():
            self.set(key, "")
        return self.content[key]

    def write(self, filename = None):
        if not filename and not self.filename:
            return

        if filename:
            self.filename = filename
        else:
            filename = self.filename

        if not os.path.isdir(os.path.dirname(filename)):
            os.makedirs(os.path.dirname(filename))

        fp = codecs.open(filename, 'w')
        for (key, value) in self.content.items():
            fp.write("%s=%s\n" % (key, value))
        fp.write("\n")

    def set(self, key, value):
        self.content[key] = value

    def removeKey(self, key):
        for (name, value) in self.content.items():
            if key == name:
                del self.content[name]

    def hasKey(self, key):
        if self.content.has_key(key):
            return True
        else:
            return False

    def getFileName(self):
        return self.filename

########NEW FILE########
__FILENAME__ = sourcedata
from ubuntutweak import system

def is_ubuntu(distro):
    if type(distro) == list:
        for dis in distro:
            if system.is_supported(dis):
                return True
            return False
    else:
        if system.is_supported(distro):
            return True
        return False

def filter_sources():
    newsource = []
    for item in SOURCES_DATA:
        distro = item[1]
        if is_ubuntu(distro):
            if system.codename in distro:
                newsource.append([item[0], system.codename, item[2], item[3]])
        else:
            newsource.append(item)

    return newsource

########NEW FILE########
__FILENAME__ = factory
# Ubuntu Tweak - Ubuntu Configuration Tool
#
# Copyright (C) 2007-2011 Tualatrix Chou <tualatrix@gmail.com>
#
# Ubuntu Tweak is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# Ubuntu Tweak is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Ubuntu Tweak; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA

import logging

from gi.repository import Gtk

from ubuntutweak.gui.dialogs import *
from ubuntutweak.gui.widgets import *
from ubuntutweak.gui.containers import *
from ubuntutweak.common.debug import run_traceback

log = logging.getLogger('factory')

def on_reset_button_clicked(widget, reset_target):
    if hasattr(reset_target, 'reset'):
        log.debug("Reset value to %s by %s" % \
                  (widget.get_default_value(), reset_target))
        reset_target.reset()
    else:
        log.debug("No reset function to call for: %s" % reset_target)


class WidgetFactory:
    composite_capable = ('SpinButton', 'Entry', 'ComboBox',
                         'Scale', 'FontButton', 'ColorButton', 'Switch')

    @classmethod
    def create(cls, widget, **kwargs):
        if widget in cls.composite_capable and kwargs.has_key('label'):
            return getattr(cls, 'do_composite_create')(widget, **kwargs)
        else:
            return getattr(cls, 'do_create')(widget, **kwargs)

    @classmethod
    def do_composite_create(cls, widget, **kwargs):
        label = Gtk.Label(label=kwargs.pop('label'))
        signal_dict = kwargs.pop('signal_dict', None)
        reverse = kwargs.get('reverse', False)

        enable_reset = kwargs.has_key('enable_reset')
        if enable_reset:
            enable_reset = kwargs.pop('enable_reset')

        try:
            new_widget = globals().get(widget)(**kwargs)
        except Exception, e:
            log.error(run_traceback('error', text_only=True))

            if enable_reset:
                return [None, None, None]
            else:
                return [None, None]

        if signal_dict:
            for signal, method in signal_dict.items():
                new_widget.connect(signal, method)

        if enable_reset:
            try:
                reset_button = ResetButton(new_widget.get_setting(),
                                           reverse=reverse)
                reset_button.connect('clicked', on_reset_button_clicked, new_widget)
            except Exception, e:
                log.error(run_traceback('error', text_only=True))
                reset_button = None
            finally:
                return label, new_widget, reset_button

        return label, new_widget

    @classmethod
    def do_create(cls, widget, **kwargs):
        signal_dict = kwargs.pop('signal_dict', None)
        blank_label = kwargs.pop('blank_label', None)
        reverse = kwargs.get('reverse', False)

        enable_reset = kwargs.has_key('enable_reset')
        if enable_reset:
            kwargs.pop('enable_reset')

        new_widget = globals().get(widget)(**kwargs)

        if signal_dict:
            for signal, method in signal_dict.items():
                new_widget.connect(signal, method)

        if enable_reset:
            try:
                reset_button = ResetButton(new_widget.get_setting(),
                                           reverse=reverse)
                reset_button.connect('clicked', on_reset_button_clicked, new_widget)

                if blank_label:
                    return Gtk.Label(), new_widget, reset_button
                else:
                    return new_widget, reset_button
            except Exception, e:
                log.error(run_traceback('error', text_only=True))

        if blank_label:
            return Gtk.Label(), new_widget
        else:
            return new_widget

########NEW FILE########
__FILENAME__ = cellrenderers
#! /usr/bin/env python
#-*- encoding:utf-8 -*-
#文件名:cellrenderbutton.py
"""Test code

Description:________
"""
__version__  = "0.1"
__date__     = "2009-02-20 15:38:24"
__author__   = "Mingxi Wu <fengshenx@gmail.com> "
__license__  = "Licensed under the GPL v2, see the file LICENSE in this tarball."
__copyright__= "Copyright (C) 2009 by Mingxi Wu <fengshenx@gmail.com>."
#=================================================================================#
# ChangeLog
# 2009-11-18
# TualatriX, make it can accept text data

import cairo
from gi.repository import GObject, Gtk, Pango

class CellRendererButton(Gtk.CellRenderer):
    __gsignals__ = {
        'clicked': (GObject.SignalFlags.RUN_FIRST,
                    None,
                    (GObject.TYPE_STRING,))
    }

    __gproperties__ = {
        'text': (GObject.TYPE_STRING, 'Text',
                 'Text for button', '', GObject.PARAM_READWRITE)
    }

    def __init__(self, text=None):
        GObject.GObject.__init__(self)

        self.text = text
        self._xpad = 6
        self._ypad = 2
        self.set_property('mode', Gtk.CellRendererMode.ACTIVATABLE)

    def do_set_property(self, pspec, value):
        setattr(self, pspec.name, value)

    def do_get_property(self, pspec):
        return getattr(self, pspec.name)

    def do_get_size (self, widget, x, y, width, height, data):
        context = widget.get_pango_context()
        metrics = context.get_metrics(widget.style.font_desc, 
                                      context.get_language())
        row_height = metrics.get_ascent() + metrics.get_descent()
        height = (row_height + 512 >> 10) + self._ypad * 2

        layout = widget.create_pango_layout(self.text)
        (row_width, layout_height) = layout.get_pixel_size()
        width = row_width + self._xpad * 2
        print width, height
        
        return (0, 0, width, height)

    def do_render(self, window, widget,
                  background_area, cell_area, expose_area, flags):
        layout = widget.create_pango_layout(self.text)
        (layout_width, layout_height) = layout.get_pixel_size()
        layout_xoffset = (cell_area.width - layout_width) / 2 + cell_area.x
        layout_yoffset = (cell_area.height - layout_height) / 2 + cell_area.y

        Gtk.paint_box(widget.style, window, widget.state, Gtk.ShadowType.OUT, 
                               expose_area, widget, 'button',
                               cell_area.x, cell_area.y,
                               cell_area.width, cell_area.height)
        Gtk.paint_layout(widget.style, window, widget.state, True, expose_area,
                                  widget, "cellrenderertext", layout_xoffset,
                                  layout_yoffset, layout)

    def do_activate(self, event, widget, path,
                    background_area, cell_area, flags):
        self.emit('clicked', path)

GObject.type_register(CellRendererButton)

########NEW FILE########
__FILENAME__ = containers
import logging

from gi.repository import GObject, Gtk

log = logging.getLogger('gui.containers')

class BasePack(Gtk.VBox):
    def __init__(self, label):
        GObject.GObject.__init__(self)
        self.set_border_width(5)

        if label:
            title = Gtk.MenuItem(label=label)
            title.select()
            self.pack_start(title, False, False, 0)


class BaseListPack(BasePack):
    def __init__(self, title):
        BasePack.__init__(self, title)

        hbox = Gtk.HBox()
        hbox.set_border_width(5)
        self.pack_start(hbox, True, False, 0)

        label = Gtk.Label(label=" ")
        hbox.pack_start(label, False, False, 0)

        self.vbox = Gtk.VBox()
        hbox.pack_start(self.vbox, True, True, 0)


class SinglePack(BasePack):
    def __init__(self, title, widget):
        BasePack.__init__(self, title)

        self.pack_start(widget, True, True, 10)


class ListPack(BaseListPack):
    def __init__(self, title, widgets, padding=6):
        BaseListPack.__init__(self, title)
        self.items = []

        if widgets:
            for widget in widgets:
                if widget: 
                    if widget.get_parent():
                        widget.unparent()
                    self.vbox.pack_start(widget, False, False, padding)
                    self.items.append(widget)
        else:
            self = None


class EasyTable(Gtk.Table):
    def __init__(self, items=[], xpadding=6, ypadding=6):
        GObject.GObject.__init__(self)

        columns = 1
        for i, item in enumerate(items):
            rows = i + 1
            if len(item) > columns:
                columns = len(item)

        self.set_property('n-rows', rows)
        self.set_property('n-columns', columns)

        for item in items:
            if item is not None:
                top_attach = items.index(item)

                if issubclass(item.__class__, Gtk.Widget):
                    self.attach(item, 0, columns, top_attach,
                                top_attach + 1, ypadding=ypadding)
                else:
                    for widget in item:
                        if widget:
                            left_attch = item.index(widget)

                            if type(widget) == Gtk.Label:
                                widget.set_alignment(0, 0.5)

                            if left_attch == 1:
                                self.attach(widget, left_attch,
                                            left_attch + 1, top_attach,
                                            top_attach + 1, xpadding=xpadding,
                                            ypadding=ypadding)
                            else:
                                self.attach(widget, left_attch,
                                            left_attch + 1, top_attach,
                                            top_attach + 1, Gtk.AttachOptions.FILL,
                                            ypadding=ypadding)



class TablePack(BaseListPack):
    def __init__(self, title, items):
        BaseListPack.__init__(self, title)

        table = EasyTable(items, xpadding=12)

        self.vbox.pack_start(table, True, True, 0)

class GridPack(Gtk.Grid):
    def __init__(self, *items):
        GObject.GObject.__init__(self)

        items = self._pre_deal_items(items)

        self._column = 1
        for i, item in enumerate(items):
            rows = i + 1
            if hasattr(item, '__len__') and len(item) > self._column:
                self._column = len(item)

        log.debug("There are totally %d columns" % self._column)

        self.set_property('row-spacing', 6)
        self.set_property('column-spacing', 6)
        self.set_property('margin-left', 15)
        self.set_property('margin-right', 15)
        self.set_property('margin-top', 5)
        self._items = items

        self._insert_items()

        self.connect('size-allocate', self.on_grid_size_allocate)

    def _pre_deal_items(self, items):
        new_list = []
        for item in items:
            if type(item) == list:
                is_not_none = True

                for sub_item in item:
                    if sub_item is None:
                        is_not_none = False
                        break

                if is_not_none:
                    new_list.append(item)
            else:
                if item:
                    new_list.append(item)

        if type(new_list[0]) == Gtk.Separator:
            new_list.pop(0)

        if type(new_list[-1]) == Gtk.Separator:
            new_list.pop(-1)

        return new_list

    def on_grid_size_allocate(self, widget, allocation):
        size_list = []
        for item in self._items:
            if not issubclass(item.__class__, Gtk.Widget):
                for widget in item:
                    if widget and type(widget) != Gtk.Label and \
                        widget.get_property('hexpand') and \
                        not hasattr(widget, 'get_default_value') and \
                        not issubclass(widget.__class__, Gtk.Switch):
                            width = widget.get_allocation().width
#                            log.debug("Do width calculate for child: %s, %d" % (widget, width))
                            size_list.append(width)

        if size_list:
            max_size = max(size_list)

        if size_list and max_size * len(size_list) != sum(size_list):
            for item in self._items:
                if not issubclass(item.__class__, Gtk.Widget):
                    for widget in item:
                        if widget and type(widget) != Gtk.Label and \
                            widget.get_property('hexpand') and \
                            not hasattr(widget, 'get_default_value') and \
                            not issubclass(widget.__class__, Gtk.Switch):
#                                log.debug("Set new width for child: %s with: %d" % (widget, max_size))
                                widget.set_size_request(max_size, -1)

    def _insert_items(self):
        for top_attach, item in enumerate(self._items):
            log.debug("Found item: %s" % str(item))
            if item is not None:
                if issubclass(item.__class__, Gtk.Widget):
                    if issubclass(item.__class__, Gtk.Separator):
                        item.set_size_request(-1, 20)
                        left = 0
                        top = top_attach + 1
                        width = self._column
                        height = 1
                    elif issubclass(item.__class__, Gtk.CheckButton) or \
                         issubclass(item.__class__, Gtk.Box):
                        left = 1
                        top = top_attach + 1
                        width = 1
                        height = 1
                    else:
                        left = getattr(item, '_ut_left', 0)
                        top = top_attach + 1
                        width = self._column
                        height = 1

                    log.debug("Attach item: %s to Grid: %s,%s,%s,%s\n" % \
                              (str(item), left, top, width, height))
                    self.attach(item, left, top, width, height)
                else:
                    for left_attch, widget in enumerate(item):
                        if widget:
                            if type(widget) == Gtk.Label:
                                widget.set_property('halign', Gtk.Align.END)
                                widget.set_property('hexpand', True)
                            else:
                                if issubclass(widget.__class__, Gtk.Switch) or \
                                issubclass(widget.__class__, Gtk.CheckButton) or \
                                hasattr(widget, 'get_default_value'):
                                    #so this is reset button

                                    log.debug("Set the widget(%s) Align START" % widget)
                                    widget.set_property('halign', Gtk.Align.START)
                                else:
                                    log.debug("Set the widget(%s) width to 200" % widget)
                                    # The initial value is 200, but maybe larger in gird_size_allocate
                                    widget.set_size_request(200, -1)
                                    # If widget is not the last column, so not set the  Align START, just make it fill the space
                                    if left_attch + 1 == self._column:
                                        widget.set_property('halign', Gtk.Align.START)
                                # If widget is not the last column, so not set the  hexpand to True, so it will not take the same size of column as others
                                if left_attch + 1 == self._column:
                                    widget.set_property('hexpand', True)

                            log.debug("Attach widget: %s to Grid: %s,%s,1,1\n" % (str(widget), left_attch, top_attach + 1))
                            self.attach(widget, 
                                        left_attch,
                                        top_attach + 1,
                                        1, 1)

########NEW FILE########
__FILENAME__ = dialogs
# Ubuntu Tweak - Ubuntu Configuration Tool
#
# Copyright (C) 2007-2011 Tualatrix Chou <tualatrix@gmail.com>
#
# Ubuntu Tweak is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# Ubuntu Tweak is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Ubuntu Tweak; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA

import thread

from gi.repository import GObject, Gtk, Gdk, Pango, Vte

from ubuntutweak.gui.gtk import set_busy, unset_busy


class BaseDialog(Gtk.MessageDialog):
    def __init__(self, **kwargs):
        title = kwargs.pop('title', '')
        message = kwargs.pop('message', '')

        GObject.GObject.__init__(self, **kwargs)

        if title:
            self.set_title(title)

        if message:
            self.set_content(message)

    def set_title(self, title):
        self.set_markup('<big><b>%s</b></big>' % title)

    def set_content(self, message):
        if self.get_property('text'):
            self.format_secondary_markup(message)
        else:
            self.set_markup(message)
    
    def launch(self):
        self.run()
        self.destroy()

    def add_option_button(self, button):
        '''Add an option button to the left. It will not grab the default response.'''
        vbox = self.get_content_area()
        hbuttonbox = vbox.get_children()[-1]

        hbox = Gtk.HBox(spacing=12)
        vbox.pack_start(hbox, False, False, 0)
        vbox.remove(hbuttonbox)

        new_hbuttonbox = Gtk.HButtonBox()
        new_hbuttonbox.set_layout(Gtk.ButtonBoxStyle.START)
        new_hbuttonbox.pack_start(button, True, True, 0)

        hbox.pack_start(new_hbuttonbox, True, True, 0)
        hbox.pack_start(hbuttonbox, True, True, 0)

        hbuttonbox.get_children()[-1].grab_focus()

        vbox.show_all()


class ErrorDialog(BaseDialog):
    def __init__(self, title='', message='', parent=None,
                 type=Gtk.MessageType.ERROR, buttons=Gtk.ButtonsType.OK):
        BaseDialog.__init__(self, title=title, message=message,
                            parent=parent, message_type=type, buttons=buttons)


class InfoDialog(BaseDialog):
    def __init__(self, title='', message='', parent=None,
                 type=Gtk.MessageType.INFO, buttons=Gtk.ButtonsType.OK):
        BaseDialog.__init__(self, title=title, message=message,
                            parent=parent, message_type=type, buttons=buttons)


class WarningDialog(BaseDialog):
    def __init__(self, title='', message='', parent=None,
                 type=Gtk.MessageType.WARNING, buttons=Gtk.ButtonsType.OK):
        BaseDialog.__init__(self, title=title, message=message,
                            parent=parent, message_type=type, buttons=buttons)


class QuestionDialog(BaseDialog):
    def __init__(self, title='', message='', parent=None,
                 type=Gtk.MessageType.QUESTION, buttons=Gtk.ButtonsType.YES_NO):
        BaseDialog.__init__(self, title=title, message=message,
                            parent=parent, message_type=type, buttons=buttons)


class BusyDialog(Gtk.Dialog):
    def __init__(self, parent=None):
        GObject.GObject.__init__(self, parent=parent)

        if parent:
            self.parent_window = parent
        else:
            self.parent_window = None

    def set_busy(self):
        set_busy(self.parent_window)

    def unset_busy(self):
        unset_busy(self.parent_window)

    def run(self):
        self.set_busy()
        return super(BusyDialog, self).run()

    def destroy(self):
        self.unset_busy()
        super(BusyDialog, self).destroy()


class ProcessDialog(BusyDialog):
    __gsignals__ = {
        'error': (GObject.SignalFlags.RUN_FIRST, None, (GObject.TYPE_STRING,)),
        'done': (GObject.SignalFlags.RUN_FIRST, None, ()),
    }

    def __init__(self, parent):
        super(ProcessDialog, self).__init__(parent=parent)

        self.set_border_width(6)
        self.set_title('')
        self.set_resizable(False)
        self.set_position(Gtk.WindowPosition.CENTER_ON_PARENT)

        vbox = self.get_content_area()
        vbox.set_spacing(6)

        self._label = Gtk.Label()
        self._label.set_alignment(0, 0.5)
        vbox.pack_start(self._label, False, False, 0)

        self._progressbar = Gtk.ProgressBar()
        self._progressbar.set_ellipsize(Pango.EllipsizeMode.END)
        self._progressbar.set_size_request(320, -1)
        vbox.pack_start(self._progressbar, False, False, 0)

        self.show_all()

    def pulse(self):
        self._progressbar.pulse()

    def set_fraction(self, fraction):
        self._progressbar.set_fraction(fraction)

    def set_dialog_lable(self, text):
        self._label.set_markup('<b><big>%s</big></b>' % text)

    def set_progress_text(self, text):
        self._progressbar.set_text(text)

    def process_data(self):
        return NotImplemented


class SmartTerminal(Vte.Terminal):
    def insert(self, string):
        self.feed(string, -1)

    def future_insert(self, string):
        #TODO use this in Gtk+3.0
        column_count = self.get_column_count()
        column, row = self.get_cursor_position()
        if column == 0:
            column = column_count
        if column != column_count:
            self.feed(' ' * (column_count - column))
        space_length = column_count - len(string)
        string = string + ' ' * space_length
        self.feed(string)


class TerminalDialog(ProcessDialog):
    def __init__(self, parent):
        super(TerminalDialog, self).__init__(parent=parent)

        vbox = self.get_content_area()

        self.set_position(Gtk.WindowPosition.CENTER_ALWAYS)
        self.expendar = Gtk.Expander()
        self.expendar.set_spacing(6)
        self.expendar.set_label(_('Details'))
        vbox.pack_start(self.expendar, False, False, 6)

        self.terminal = SmartTerminal()
        self.terminal.set_size_request(562, 362)
        self.expendar.add(self.terminal)

        self.show_all()


class AuthenticateFailDialog(ErrorDialog):
    def __init__(self):
        ErrorDialog.__init__(self,
                             title=_('Could not authenticate'),
                             message=_('An unexpected error has occurred.'))


class ServerErrorDialog(ErrorDialog):
    def __init__(self):
        ErrorDialog.__init__(self,
                             title=_("Service hasn't initialized yet"),
                             message=_('You need to restart your computer.'))

########NEW FILE########
__FILENAME__ = gtk
import logging

from gi.repository import Gdk

from ubuntutweak.common.debug import log_func

log = logging.getLogger("gtk")

@log_func(log)
def set_busy(window):
    if window and window.get_parent_window():
        window.get_parent_window().set_cursor(Gdk.Cursor.new(Gdk.CursorType.WATCH))
        window.set_sensitive(False)

@log_func(log)
def unset_busy(window):
    if window and window.get_parent_window():
        window.get_parent_window().set_cursor(None)
        window.set_sensitive(True)

@log_func(log)
def post_ui(func):
    def func_wrapper(*args, **kwargs):
        Gdk.threads_enter()
        func(*args, **kwargs)
        Gdk.threads_leave()

    return func_wrapper


########NEW FILE########
__FILENAME__ = treeviews
import os
import logging
import shutil

from gi.repository import Gtk, Gdk, Gio, GObject, GdkPixbuf

from ubuntutweak.gui.dialogs import ErrorDialog
from ubuntutweak.utils import icon

log = logging.getLogger("treeviews")

def get_local_path(url):
    return Gio.file_parse_name(url.strip()).get_path()

class CommonView(object):
    TARGETS = [
            ('text/plain', 0, 1),
            ('TEXT', 0, 2),
            ('STRING', 0, 3),
            ]

    def enable_drag_and_drop(self):
        self.enable_model_drag_source(Gdk.ModifierType.BUTTON1_MASK,
                                      self.TARGETS,
                                      Gdk.DragAction.COPY)
        self.enable_model_drag_dest([], Gdk.DragAction.COPY)
        self.drag_dest_add_text_targets()
        self.drag_source_add_text_targets()

    def is_same_object(self, context):
        return context.get_source_window() is not self.get_window()


class DirView(Gtk.TreeView, CommonView):
    __gsignals__ = {
        'deleted': (GObject.SignalFlags.RUN_FIRST, None, ())
    }

    (DIR_ICON,
     DIR_TITLE,
     DIR_PATH,
     DIR_EDITABLE) = range(4)


    def __init__(self, dir):
        GObject.GObject.__init__(self)

        self.set_rules_hint(True)
        self.dir = dir
        if not os.path.exists(self.dir):
            os.makedirs(self.dir)

        self.model = self._create_model()
        self.set_model(self.model)

        iter = self._setup_root_model()
        self.do_update_model(self.dir, iter)

        self._add_columns()
        self.set_size_request(180, -1)
        self.expand_all()

        self.enable_drag_and_drop()

        self.connect('drag_data_get', self.on_drag_data_get)
        self.connect('drag_data_received', self.on_drag_data_received)

        menu = self._create_popup_menu()
        menu.show_all()
        self.connect('button_press_event', self.button_press_event, menu)
        self.connect('key-press-event', self.on_key_press_event)

    def on_key_press_event(self, widget, event):
        if event.keyval == 65535:
            self.on_delete_item(widget)

    def button_press_event(self, widget, event, menu):
        if event.type == Gdk.EventType.BUTTON_PRESS and event.button == 3:
            menu.popup(None, None, None, None, event.button, event.time)
        return False

    def _create_popup_menu(self):
        menu = Gtk.Menu()

        change_item = Gtk.MenuItem(label=_('Create folder'))
        menu.append(change_item)
        change_item.connect('activate', self.on_create_folder)

        change_item = Gtk.MenuItem(label=_('Rename'))
        menu.append(change_item)
        change_item.connect('activate', self.on_rename_item)

        change_item = Gtk.MenuItem(label=_('Delete'))
        menu.append(change_item)
        change_item.connect('activate', self.on_delete_item)

        return menu

    def create_file_name(self, filename, count):
        if filename in os.listdir(self.dir):
            if filename[-1].isdigit():
                filename = filename[:-1] + str(count)
            else:
                filename = filename + ' %d' % count
            count = count + 1
            self.create_file_name(filename, count)
        else:
            self.tempname = filename

    def on_create_folder(self, widget):
        iter = self.model.append(self.model.get_iter_first())
        column = self.get_column(0)
        path = self.model.get_path(iter)

        self.create_file_name(_('Input the dir name'), 1)
        filename = self.tempname
        del self.tempname
        newdir = os.path.join(self.dir, filename)
        os.mkdir(newdir)

        self.model.set_value(iter, self.DIR_ICON, icon.get_from_name('folder', 24))
        self.model.set_value(iter, self.DIR_TITLE, filename)
        self.model.set_value(iter, self.DIR_PATH, newdir)
        self.model.set_value(iter, self.DIR_EDITABLE, True)

        self.set_cursor(path, column, True)

    def on_rename_item(self, widget):
        model, iter = self.get_selection().get_selected()
        filepath = model.get_value(iter, self.DIR_PATH)

        if filepath != self.dir:
            model.set_value(iter, self.DIR_EDITABLE, True)

            column = self.get_column(0)
            path = self.model.get_path(iter)
            self.set_cursor(path, column, True)
        else:
            ErrorDialog(_("Can't rename the root folder")).launch()

    def on_delete_item(self, widget):
        model, iter = self.get_selection().get_selected()
        if not iter:
            return
        filepath = model.get_value(iter, self.DIR_PATH)

        if filepath != self.dir:
            if os.path.isdir(filepath):
                shutil.rmtree(filepath)
            else:
                os.remove(filepath)

            self.emit('deleted')
            self.update_model()
        else:
            ErrorDialog(_("Can't delete the root folder")).launch()

    def on_cellrenderer_edited(self, cellrenderertext, path, new_text):
        iter = self.model.get_iter_from_string(path)
        filepath = self.model.get_value(iter, self.DIR_PATH)
        old_text = self.model.get_value(iter, self.DIR_TITLE)

        if old_text == new_text or new_text not in os.listdir(os.path.dirname(filepath)):
            newpath = os.path.join(os.path.dirname(filepath), new_text)
            os.rename(filepath, newpath)
            self.model.set_value(iter, self.DIR_TITLE, new_text)
            self.model.set_value(iter, self.DIR_PATH, newpath)
            self.model.set_value(iter, self.DIR_EDITABLE, False)
        else:
            ErrorDialog(_("Can't rename!\n\nThere are files in it!")).launch()

    def on_drag_data_get(self, treeview, context, selection, target_id, etime):
        treeselection = self.get_selection()
        model, iter = treeselection.get_selected()
        data = model.get_value(iter, self.DIR_PATH)
        log.debug("on_drag_data_get: %s" % data)

        if data != self.dir:
            selection.set(selection.get_target(), 8, data)

    def on_drag_data_received(self, treeview, context, x, y, selection, info, etime):
        '''If the source is coming from internal, then move it, or copy it.'''
        source = selection.get_data()

        if source:
            try:
                path, position = treeview.get_dest_row_at_pos(x, y)
                iter = self.model.get_iter(path)
            except:
                try:
                    iter = self.model.get_iter_first()
                except:
                    iter = self.model.append(None)

            target = self.model.get_value(iter, self.DIR_PATH)

            if self.is_same_object(context):
                file_action = 'move'
                dir_action = 'move'
            else:
                file_action = 'copy'
                dir_action = 'copytree'

            if '\r\n' in source:
                file_list = source.split('\r\n')
                for file in file_list:
                    if file:
                        self.file_operate(file, dir_action, file_action, target)
            else:
                self.file_operate(source, dir_action, file_action, target)

            self.update_model()
            context.finish(True, False, etime)
        else:
            context.finish(False, False, etime)

    def file_operate(self, source, dir_action, file_action, target):
        source = get_local_path(source)

        if os.path.isdir(target) and not os.path.isdir(source):
            if os.path.dirname(source) != target:
                if os.path.isdir(source):
                    getattr(shutil, dir_action)(source, target)
                else:
                    getattr(shutil, file_action)(source, target)
        elif os.path.isdir(target) and os.path.isdir(source):
            target = os.path.join(target, os.path.basename(source))
            getattr(shutil, dir_action)(source, target)
        elif os.path.dirname(target) != os.path.dirname(source):
            if not os.path.isdir(target):
                target = os.path.dirname(target)

            if os.path.isdir(source):
                target = os.path.join(target, os.path.basename(source))
                getattr(shutil, dir_action)(source, target)
            else:
                getattr(shutil, file_action)(source, target)

    def update_model(self):
        self.model.clear()

        iter = self._setup_root_model()
        self.do_update_model(self.dir, iter)

        self.expand_all()

    def _create_model(self):
        model = Gtk.TreeStore(GdkPixbuf.Pixbuf,
                              GObject.TYPE_STRING,
                              GObject.TYPE_STRING,
                              GObject.TYPE_BOOLEAN)

        return model

    def _setup_root_model(self):
        pixbuf = icon.guess_from_path(self.dir, 24)

        iter = self.model.append(None, (pixbuf, os.path.basename(self.dir),
                                 self.dir, False))

        return iter

    def do_update_model(self, dir, iter):
        for item in os.listdir(dir):
            fullname = os.path.join(dir, item)
            pixbuf = icon.guess_from_path(fullname, 24)

            child_iter = self.model.append(iter,
                                           (pixbuf, os.path.basename(fullname),
                                            fullname, False))

            if os.path.isdir(fullname):
                self.do_update_model(fullname, child_iter)

    def _add_columns(self):
        try:
            self.type
        except:
            column = Gtk.TreeViewColumn()
        else:
            column = Gtk.TreeViewColumn(self.type)

        column.set_spacing(5)

        renderer = Gtk.CellRendererPixbuf()
        column.pack_start(renderer, False)
        column.add_attribute(renderer, 'pixbuf', self.DIR_ICON)

        renderer = Gtk.CellRendererText()
        renderer.connect('edited', self.on_cellrenderer_edited)
        column.pack_start(renderer, True)
        column.add_attribute(renderer, 'text', self.DIR_TITLE)
        column.add_attribute(renderer, 'editable', self.DIR_EDITABLE)

        self.append_column(column)


class FlatView(Gtk.TreeView, CommonView):
    (FLAT_ICON,
     FLAT_TITLE,
     FLAT_PATH) = range(3)

    def __init__(self, dir, exclude_dir=None):
        GObject.GObject.__init__(self)

        self.set_rules_hint(True)
        self.dir = dir
        self.exclude_dir = exclude_dir

        self.model = Gtk.ListStore(GdkPixbuf.Pixbuf,
                                   GObject.TYPE_STRING,
                                   GObject.TYPE_STRING)

        self.set_model(self.model)
        self.update_model()
        self._add_columns()

        self.enable_drag_and_drop()

        self.connect("drag_data_get", self.on_drag_data_get_data)
        self.connect("drag_data_received", self.on_drag_data_received_data)

    def on_drag_data_get_data(self, treeview, context, selection, target_id, etime):
        treeselection = self.get_selection()
        model, iter = treeselection.get_selected()
        data = model.get_value(iter, self.FLAT_PATH)
        log.debug("selection set data to %s with %s" % (selection.get_target(), data))
        selection.set(selection.get_target(), 8, data)

    def on_drag_data_received_data(self, treeview, context, x, y, selection, info, etime):
        source = selection.get_data()

        if self.is_same_object(context) and source:
            try:
                path, position = treeview.get_dest_row_at_pos(x, y)
                iter = self.model.get_iter(path)
            except:
                iter = self.model.append(None)

            target = self.dir
            source = get_local_path(source)
            file_action = 'move'
            dir_action = 'move'

            if source in os.listdir(self.dir):
                os.remove(source)
            elif os.path.isdir(target) and not os.path.isdir(source):
                if os.path.dirname(source) != target:
                    if os.path.isdir(source):
                        getattr(shutil, dir_action)(source, target)
                    else:
                        if file_action == 'move' and os.path.exists(os.path.join
                                (target, os.path.basename(source))):
                            os.remove(source)
                        else:
                            getattr(shutil, file_action)(source, target)
            elif os.path.isdir(target) and os.path.isdir(source):
                target = os.path.join(target, os.path.basename(source))
                getattr(shutil, dir_action)(source, target)
            elif os.path.dirname(target) != os.path.dirname(source):
                if not os.path.isdir(target):
                    target = os.path.dirname(target)

                if os.path.isdir(source):
                    target = os.path.join(target, os.path.basename(source))
                    getattr(shutil, dir_action)(source, target)
                else:
                    getattr(shutil, file_action)(source, target)

            self.update_model()
            context.finish(True, False, etime)
        else:
            context.finish(False, False, etime)

    def update_model(self):
        self.model.clear()

        dir = self.dir
        self.exist_lsit = []
        if self.exclude_dir:
            for root, dirs, files in os.walk(self.exclude_dir):
                if files:
                    self.exist_lsit.extend(files)

        for item in os.listdir(dir):
            fullname = os.path.join(dir, item)
            title = os.path.basename(fullname)
            if title in self.exist_lsit:
                continue
            pixbuf = icon.guess_from_path(fullname, 24)

            self.model.append((pixbuf, title, fullname))

    def _add_columns(self):
        try:
            self.type
        except:
            column = Gtk.TreeViewColumn()
        else:
            column = Gtk.TreeViewColumn(self.type)

        column.set_spacing(5)

        renderer = Gtk.CellRendererPixbuf()
        column.pack_start(renderer, False)
        column.add_attribute(renderer, 'pixbuf', self.FLAT_ICON)

        renderer = Gtk.CellRendererText()
        column.pack_start(renderer, True)
        column.add_attribute(renderer, 'text', self.FLAT_TITLE)

        self.append_column(column)

########NEW FILE########
__FILENAME__ = widgets
import time
import logging

from gi.repository import GObject, Gtk, Gdk

from ubuntutweak.common.debug import log_func
from ubuntutweak.settings.gsettings import GSetting
from ubuntutweak.settings.configsettings import ConfigSetting
from ubuntutweak.settings.gconfsettings import GconfSetting, UserGconfSetting
from ubuntutweak.settings.compizsettings import CompizSetting
from ubuntutweak.settings.configsettings import SystemConfigSetting

log = logging.getLogger('widgets')

class SettingWidget(object):
    def __init__(self, **kwargs):
        key = kwargs['key']
        backend = kwargs['backend']
        default = kwargs['default']
        type = kwargs['type']

        if backend == 'gconf':
            self._setting = GconfSetting(key=key, default=default, type=type)
        elif backend == 'gsettings':
            self._setting = GSetting(key=key, default=default, type=type)
        elif backend == 'config':
            self._setting = ConfigSetting(key=key, type=type)
        elif backend == 'compiz':
            self._setting = CompizSetting(key=key)
        elif backend == 'systemconfig':
            self._setting = SystemConfigSetting(key=key, default=default, type=type)

        if hasattr(self._setting, 'connect_notify') and \
                hasattr(self, 'on_value_changed'):
            log.debug("Connect the setting notify to on_value_changed: %s" % key)
            self.get_setting().connect_notify(self.on_value_changed)

    def get_setting(self):
        return self._setting


class CheckButton(Gtk.CheckButton, SettingWidget):
    def __str__(self):
        return '<CheckButton with key: %s>' % self.get_setting().key

    def __init__(self, label=None, key=None,
                 default=None, tooltip=None, backend='gconf'):
        GObject.GObject.__init__(self, label=label)
        SettingWidget.__init__(self, key=key, default=default, type=bool, backend=backend)

        self.set_active(self.get_setting().get_value())

        if tooltip:
            self.set_tooltip_text(tooltip)

        self.connect('toggled', self.on_button_toggled)

    @log_func(log)
    def on_value_changed(self, *args):
        self.set_active(self.get_setting().get_value())

    @log_func(log)
    def on_button_toggled(self, widget):
        self.get_setting().set_value(self.get_active())


class Switch(Gtk.Switch, SettingWidget):
    def __str__(self):
        return '<Switch with key: %s>' % self.get_setting().key

    def __init__(self, key=None, default=None,
                 on=True, off=False,
                 tooltip=None,
                 reverse=False,
                 backend='gconf'):
        GObject.GObject.__init__(self)
        SettingWidget.__init__(self, key=key, default=default, type=bool, backend=backend)

        self._on = on
        self._off = off
        self._reverse = reverse

        self._set_on_off()

        if tooltip:
            self.set_tooltip_text(tooltip)

        self.connect('notify::active', self.on_switch_activate)

    def _set_on_off(self):
        self.set_active(self._off != self.get_setting().get_value())

    def set_active(self, bool):
        if self._reverse:
            log.debug("The value is reversed")
            bool = not bool
        log.debug("Set the swtich to: %s" % bool)
        super(Switch, self).set_active(bool)

    def get_active(self):
        if self._reverse:
            return not super(Switch, self).get_active()
        else:
            return super(Switch, self).get_active()

    @log_func(log)
    def on_value_changed(self, *args):
        self.handler_block_by_func(self.on_switch_activate)
        self._set_on_off()
        self.handler_unblock_by_func(self.on_switch_activate)

    @log_func(log)
    def on_switch_activate(self, widget, value):
        try:
            if self.get_active():
                self.get_setting().set_value(self._on)
            else:
                self.get_setting().set_value(self._off)
        except Exception, e:
            log.error(e)
            self.on_value_changed(self, None)

    def reset(self):
        self.set_active(self._off != self.get_setting().get_schema_value())

class UserCheckButton(Gtk.CheckButton, SettingWidget):
    def __str__(self):
        return '<UserCheckButton with key: %s, with user: %s>' % (self.get_setting().key, self.user)

    def __init__(self, user=None, label=None, key=None, default=None,
                 tooltip=None, backend='gconf'):
        GObject.GObject.__init__(self, label=label)
        SettingWidget.__init__(self, key=key, default=default, type=bool, backend=backend)

        self.user = user

        self.set_active(bool(self.get_setting().get_value(self.user)))
        if tooltip:
            self.set_tooltip_text(tooltip)

        self.connect('toggled', self.button_toggled)

    def button_toggled(self, widget):
        self.get_setting().set_value(self.user, self.get_active())


class ResetButton(Gtk.Button):
    def __str__(self):
        return '<ResetButton with key: %s: reverse: %s>' % \
                (self._setting.key, self._reverse)

    def __init__(self, setting, reverse=False):
        GObject.GObject.__init__(self)

        self._setting = setting
        self._reverse = reverse

        self.set_property('image', 
                          Gtk.Image.new_from_stock(Gtk.STOCK_REVERT_TO_SAVED, Gtk.IconSize.MENU))

        self.set_tooltip_text(_('Reset setting to default value: %s') % self.get_default_value())

    def get_default_value(self):
        schema_value = self._setting.get_schema_value()
        if self._reverse and type(schema_value) == bool:
            return not schema_value
        else:
            return schema_value


class StringCheckButton(CheckButton):
    '''This class use to moniter the key with StringSetting, nothing else'''
    def __str__(self):
        return '<StringCheckButton with key: %s>' % self.get_setting().key

    def __init__(self, **kwargs):
        CheckButton.__init__(self, **kwargs)

    def on_button_toggled(self, widget):
        '''rewrite the toggled function, it do nothing with the setting'''
        pass

    def on_value_changed(self, *args):
        pass


class Entry(Gtk.Entry, SettingWidget):
    def __str__(self):
        return '<Entry with key: %s>' % self.get_setting().key

    def __init__(self, key=None, default=None, backend='gconf'):
        GObject.GObject.__init__(self)
        SettingWidget.__init__(self, key=key, default=default, type=str, backend=backend)

        string = self.get_setting().get_value()
        if string:
            self.set_text(str(string))

        text_buffer = self.get_buffer()
        text_buffer.connect('inserted-text', self.on_edit_finished_cb)
        text_buffer.connect('deleted-text', self.on_edit_finished_cb)

        self.connect('activate', self.on_edit_finished_cb)

    def is_changed(self):
        return self.get_setting().get_value() != self.get_text()

    @log_func(log)
    def on_value_changed(self, *args):
        self.handler_block_by_func(self.on_edit_finished_cb)
        self.set_text(self.get_setting().get_value())
        self.handler_unblock_by_func(self.on_edit_finished_cb)

    def get_gsetting(self):
        return self.get_setting()

    def on_edit_finished_cb(self, widget, *args):
        log.debug('Entry: on_edit_finished_cb: %s' % self.get_text())
        self.get_setting().set_value(self.get_text())


class ComboBox(Gtk.ComboBox, SettingWidget):
    def __str__(self):
        return '<ComboBox with key: %s>' % self.get_setting().key

    def __init__(self, key=None, default=None,
                 texts=None, values=None,
                 type=str, backend='gconf'):
        GObject.GObject.__init__(self)
        SettingWidget.__init__(self, key=key, default=default, type=type, backend=backend)

        if type == int:
            model = Gtk.ListStore(GObject.TYPE_STRING, GObject.TYPE_INT)
        else:
            model = Gtk.ListStore(GObject.TYPE_STRING, GObject.TYPE_STRING)
        self.set_model(model)

        cell = Gtk.CellRendererText()
        self.pack_start(cell, True)
        self.add_attribute(cell, 'text', 0)

        self.update_texts_values_pair(texts, values)

        self.connect("changed", self.value_changed_cb)

    def update_texts_values_pair(self, texts, values):
        self._texts = texts
        self._values = values

        self._set_value(self.get_setting().get_value())

    def _set_value(self, current_value):
        model = self.get_model()
        model.clear()

        for text, value in zip(self._texts, self._values):
            iter = model.append((text, value))
            if current_value == value:
                self.set_active_iter(iter)

    @log_func(log)
    def on_value_changed(self, *args):
        self.handler_block_by_func(self.value_changed_cb)
        self._set_value(self.get_setting().get_value())
        self.handler_unblock_by_func(self.value_changed_cb)

    def value_changed_cb(self, widget):
        iter = widget.get_active_iter()
        if iter:
            text = self.get_model().get_value(iter, 1)
            log.debug("ComboBox value changed to %s" % text)

            self.get_setting().set_value(text)

    def reset(self):
        self._set_value(self.get_setting().get_schema_value())


class FontButton(Gtk.FontButton, SettingWidget):
    def __str__(self):
        return '<FontButton with key: %s>' % self.get_setting().key

    def __init__(self, key=None, default=None, backend='gconf'):
        GObject.GObject.__init__(self)
        SettingWidget.__init__(self, key=key, default=default, type=str, backend=backend)

        self.set_use_font(True)
        self.set_use_size(True)

        self.on_value_changed()

        self.connect('font-set', self.on_font_set)

    def on_font_set(self, widget=None):
        self.get_setting().set_value(self.get_font_name())

    @log_func(log)
    def on_value_changed(self, *args):
        string = self.get_setting().get_value()

        if string:
            self.set_font_name(string)

    def reset(self):
        self.set_font_name(self.get_setting().get_schema_value())
        self.get_setting().set_value(self.get_font_name())


class Scale(Gtk.Scale, SettingWidget):
    def __str__(self):
        return '<Scale with key: %s>' % self.get_setting().key

    def __init__(self, key=None, default=None, min=None, max=None, step=None, type=int, digits=0,
                 reverse=False, orientation=Gtk.Orientation.HORIZONTAL, backend='gconf'):
        GObject.GObject.__init__(self,
                                 orientation=orientation)

        if digits > 0:
            type = float
        else:
            type = int

        if step:
            self.set_increments(step, step)

        SettingWidget.__init__(self, key=key, default=default, type=type, backend=backend)

        self._reverse = reverse
        self._max = max
        self._default = default

        self.set_range(min, max)
        self.set_digits(digits)
        try:
            self.add_mark(default or self.get_setting().get_schema_value(),
                          Gtk.PositionType.BOTTOM,
                          '')
        except Exception, e:
            log.error(e)

        self.set_value_pos(Gtk.PositionType.RIGHT)

        self.connect("value-changed", self.on_change_value)
        self.on_value_changed()

    @log_func(log)
    def on_value_changed(self, *args):
        self.handler_block_by_func(self.on_change_value)
        self.set_value(self.get_setting().get_value())
        self.handler_unblock_by_func(self.on_change_value)

    def set_value(self, value):
        if self._reverse:
            super(Scale, self).set_value(self._max - value)
        else:
            super(Scale, self).set_value(value)

    def get_value(self):
        if self._reverse:
            return self._max - super(Scale, self).get_value()
        else:
            return super(Scale, self).get_value()

    def on_change_value(self, widget):
        if self._reverse:
            self.get_setting().set_value(100 - widget.get_value())
        else:
            self.get_setting().set_value(widget.get_value())

    def reset(self):
        self.set_value(self._default or self.get_setting().get_schema_value())


class SpinButton(Gtk.SpinButton, SettingWidget):
    def __str__(self):
        return '<SpinButton with key: %s>' % self.get_setting().key

    def __init__(self, key, default=None, min=0, max=0, step=0, backend='gconf'):
        SettingWidget.__init__(self, key=key, default=default, type=int, backend=backend)

        adjust = Gtk.Adjustment(self.get_setting().get_value(), min, max, step)
        GObject.GObject.__init__(self, adjustment=adjust)
        self.connect('value-changed', self.on_change_value)

    def on_change_value(self, *args):
        self.set_value(self, self.get_setting().get_value())

    @log_func(log)
    def on_value_changed(self, widget):
        self.handler_block_by_func(self.on_change_value)
        self.get_setting().set_value(widget.get_value())
        self.handler_unblock_by_func(self.on_change_value)


"""Popup and KeyGrabber come from ccsm"""
KeyModifier = ["Shift", "Control", "Mod1", "Mod2", "Mod3", "Mod4",
               "Mod5", "Alt", "Meta", "Super", "Hyper", "ModeSwitch"]


class Popup(Gtk.Window):
    def __init__(self, parent, text=None, child=None,
                 decorated=True, mouse=False, modal=True):
        GObject.GObject.__init__(self, type=Gtk.WindowType.TOPLEVEL)
        self.set_type_hint(Gdk.WindowTypeHint.UTILITY)
        self.set_position(mouse and Gtk.WindowPosition.MOUSE or
                          Gtk.WindowPosition.CENTER_ALWAYS)

        if parent:
            self.set_transient_for(parent.get_toplevel())

        self.set_modal(modal)
        self.set_decorated(decorated)
        self.set_title("")

        if text:
            label = Gtk.Label(label=text)
            align = Gtk.Alignment()
            align.set_padding(20, 20, 20, 20)
            align.add(label)
            self.add(align)
        elif child:
            self.add(child)

        while Gtk.events_pending():
            Gtk.main_iteration()

    def destroy(self):
        Gtk.Window.destroy(self)
        while Gtk.events_pending():
            Gtk.main_iteration()


class KeyGrabber(Gtk.Button):
    __gsignals__ = {
        "changed": (GObject.SignalFlags.RUN_FIRST, None,
                    (GObject.TYPE_INT, GObject.TYPE_INT)),
        "current-changed": (GObject.SignalFlags.RUN_FIRST, None,
                            (GObject.TYPE_INT, Gdk.ModifierType))
    }

    key = 0
    mods = 0
    handler = None
    popup = None

    label = None

    def __init__ (self, parent=None, key=0, mods=0, label=None):
        '''Prepare widget'''
        GObject.GObject.__init__(self)

        self.main_window = parent
        self.key = key
        self.mods = mods

        self.label = label

        self.connect("clicked", self.begin_key_grab)
        self.set_label()

    def begin_key_grab(self, widget):
        self.add_events(Gdk.EventMask.KEY_PRESS_MASK)
        self.popup = Popup(self.main_window,
                           _("Please press the new key combination"))
        self.popup.show_all()

        self.handler = self.popup.connect("key-press-event",
                                          self.on_key_press_event)

        while Gdk.keyboard_grab(self.popup.get_parent_window(),
                                True,
                                Gtk.get_current_event_time()) != Gdk.GrabStatus.SUCCESS:
            time.sleep (0.1)

    def end_key_grab(self):
        Gdk.keyboard_ungrab(Gtk.get_current_event_time())
        self.popup.disconnect(self.handler)
        self.popup.destroy()

    def on_key_press_event(self, widget, event):
        #mods = event.get_state() & Gtk.accelerator_get_default_mod_mask()
        mods = event.get_state()

        if event.keyval in (Gdk.KEY_Escape, Gdk.KEY_Return) and not mods:
            if event.keyval == Gdk.KEY_Escape:
                self.emit("changed", self.key, self.mods)
            self.end_key_grab()
            self.set_label()
            return

        key = Gdk.keyval_to_lower(event.keyval)
        if (key == Gdk.KEY_ISO_Left_Tab):
            key = Gdk.KEY_Tab

        if Gtk.accelerator_valid(key, mods) or (key == Gdk.KEY_Tab and mods):
            self.set_label(key, mods)
            self.end_key_grab()
            self.key = key
            self.mods = mods
            self.emit("changed", self.key, self.mods)
            return

        self.set_label(key, mods)

    def set_label(self, key=None, mods=None):
        if self.label:
            if key != None and mods != None:
                self.emit("current-changed", key, mods)
            Gtk.Button.set_label(self, self.label)
            return
        if key == None and mods == None:
            key = self.key
            mods = self.mods
        label = Gtk.accelerator_name(key, mods)
        if not len(label):
            label = _("Disabled")
        Gtk.Button.set_label(self, label)


class ColorButton(Gtk.ColorButton, SettingWidget):
    def __str__(self):
        return '<ColorButton with key: %s>' % self.get_setting().key

    def __init__(self, key=None, default=None, backend='gconf'):
        GObject.GObject.__init__(self)
        self.set_use_alpha(True)
        SettingWidget.__init__(self, key=key, default=default, type=str, backend=backend)

        self._set_gdk_rgba()

        self.connect('color-set', self.on_color_set)

    def _set_gdk_rgba(self, new_value=None):
        color_value = new_value or self.get_setting().get_value()
        red, green, blue = color_value[:-1]
        color = Gdk.RGBA()
        color.red, color.green, color.blue = red / 65535.0, green / 65535.0, blue / 65535.0
        color.alpha = color_value[-1] / 65535.0
        self.set_rgba(color)

    @log_func(log)
    def on_color_set(self, widget=None):
        color = self.get_rgba()
        self.get_setting().set_value([color.red * 65535,
                                 color.green * 65535,
                                 color.blue * 65535,
                                 color.alpha * 65535])

    def set_value(self, value):
        self.get_setting().set_value(value)
        self.set_rgba(Gdk.RGBA(0,0,0,0))

    @log_func(log)
    def on_value_changed(self, *args):
        self.handler_block_by_func(self.on_color_set)
        self._set_gdk_rgba()
        self.handler_unblock_by_func(self.on_color_set)

    def reset(self):
        self._set_gdk_rgba(self.get_setting().get_schema_value())
        self.on_color_set()

########NEW FILE########
__FILENAME__ = aptcache_plugin
import logging

from ubuntutweak.janitor import JanitorCachePlugin
from ubuntutweak.policykit.dbusproxy import proxy

log = logging.getLogger('aptcache_plugin')


class AptCachePlugin(JanitorCachePlugin):
    __title__ = _('Apt Cache')
    __category__ = 'system'

    root_path = '/var/cache/apt/archives/'
    pattern = '*.deb'

    def clean_cruft(self, cruft_list=[], parent=None):
        for index, cruft in enumerate(cruft_list):
            log.debug('Cleaning...%s' % cruft.get_name())
            result = proxy.delete_apt_cache_file(cruft.get_name())

            if bool(result) == False:
                self.emit('clean_error', cruft.get_name())
                break
            else:
                self.emit('object_cleaned', cruft, index + 1)

        self.emit('all_cleaned', True)

########NEW FILE########
__FILENAME__ = autoremoval_plugin
import logging

from gi.repository import Gtk

from ubuntutweak.gui.gtk import set_busy, unset_busy
from ubuntutweak.janitor import JanitorPlugin, PackageObject
from ubuntutweak.utils.package import AptWorker
from ubuntutweak.utils import filesizeformat


log = logging.getLogger('AutoRemovalPlugin')

class AutoRemovalPlugin(JanitorPlugin):
    __title__ = _('Unneeded Packages')
    __category__ = 'system'

    def get_cruft(self):
        cache = AptWorker.get_cache()
        count = 0
        size = 0
        if cache:
            for pkg in cache:
                if pkg.is_auto_removable and not pkg.name.startswith('linux'):
                    count += 1
                    size += pkg.installed.size
                    self.emit('find_object',
                              PackageObject(pkg.installed.summary, pkg.name, pkg.installed.size),
                              count)

        self.emit('scan_finished', True, count, size)

    def clean_cruft(self, parent=None, cruft_list=[]):
        set_busy(parent)
        worker = AptWorker(parent,
                           finish_handler=self.on_clean_finished,
                           error_handler=self.on_error,
                           data=parent)
        worker.remove_packages([cruft.get_package_name() for cruft in cruft_list])

    def on_error(self, error):
        log.error('AptWorker error with: %s' % error)
        self.emit('clean_error', error)

    def on_clean_finished(self, transaction, status, parent):
        unset_busy(parent)
        AptWorker.update_apt_cache(True)
        self.emit('all_cleaned', True)

    def get_summary(self, count):
        if count:
            return '[%d] %s' % (count, self.__title__)
        else:
            return _('Unneeded Packages (No package to be removed)')

########NEW FILE########
__FILENAME__ = chrome_plugin
from ubuntutweak.janitor import JanitorCachePlugin

class ChromeCachePlugin(JanitorCachePlugin):
    __title__ = _('Chrome Cache')
    __category__ = 'application'

    root_path = '~/.cache/google-chrome/Default'


class ChromiumCachePlugin(JanitorCachePlugin):
    __title__ = _('Chromium Cache')
    __category__ = 'application'

    root_path = '~/.cache/chromium/Default'

########NEW FILE########
__FILENAME__ = empathy_plugin
from ubuntutweak.janitor import JanitorCachePlugin

class EmpathyCachePlugin(JanitorCachePlugin):
    __title__ = _('Empathy Cache')
    __category__ = 'application'

    root_path = '~/.cache/telepathy'

########NEW FILE########
__FILENAME__ = googleearth_plugin
from ubuntutweak.janitor import JanitorCachePlugin


class GoogleearthCachePlugin(JanitorCachePlugin):
    __title__ = _('Google Earth Cache')
    __category__ = 'application'

    root_path = '~/.googleearth'

########NEW FILE########
__FILENAME__ = gwibber_plugin
from ubuntutweak.janitor import JanitorCachePlugin

class GwibberCachePlugin(JanitorCachePlugin):
    __title__ = _('Gwibber Cache')
    __category__ = 'application'

    root_path = '~/.cache/gwibber'

########NEW FILE########
__FILENAME__ = mozilla_plugin
import os
import logging

from ubuntutweak.janitor import JanitorCachePlugin
from ubuntutweak.settings.configsettings import RawConfigSetting

log = logging.getLogger('MozillaCachePlugin')

class MozillaCachePlugin(JanitorCachePlugin):
    __category__ = 'application'

    targets = ['Cache',
               'safebrowsing',
               'startupCache',
               'thumbnails',
               'cache2',
               'OfflineCache']
    app_path = ''

    @classmethod
    def get_path(cls):
        profiles_path = os.path.expanduser('%s/profiles.ini' % cls.app_path)
        if os.path.exists(profiles_path):
            config = RawConfigSetting(profiles_path)
            try:
                profile_id = config.get_value('General', 'StartWithLastProfile')
                for section in config.sections():
                    if section.startswith('Profile'):
                        relative_id = config.get_value(section, 'IsRelative')
                        if relative_id == profile_id:
                            return os.path.expanduser('%s/%s' % (cls.cache_path, config.get_value(section, 'Path')))
            except Exception, e:
                log.error(e)
                path = config.get_value('Profile0', 'Path')
                if path:
                    return os.path.expanduser('%s/%s' % (cls.cache_path, path))
        return cls.root_path


class FirefoxCachePlugin(MozillaCachePlugin):
    __title__ = _('Firefox Cache')

    app_path = '~/.mozilla/firefox'
    cache_path = '~/.cache/mozilla/firefox'


class ThunderbirdCachePlugin(MozillaCachePlugin):
    __title__ = _('Thunderbird Cache')

    app_path = '~/.thunderbird'
    cache_path = '~/.cache/thunderbird'

########NEW FILE########
__FILENAME__ = oldkernel_plugin
import os
import re
import logging

from distutils.version import LooseVersion
from ubuntutweak.gui.gtk import set_busy, unset_busy
from ubuntutweak.janitor import JanitorPlugin, PackageObject
from ubuntutweak.utils.package import AptWorker
from ubuntutweak.common.debug import log_func, get_traceback


log = logging.getLogger('OldKernelPlugin')


class OldKernelPlugin(JanitorPlugin):
    __title__ = _('Old Kernel')
    __category__ = 'system'

    p_kernel_version = re.compile('[.\d]+-\d+')
    p_kernel_package = re.compile('linux-[a-z\-]+')

    def __init__(self):
        JanitorPlugin.__init__(self)
        try:
            self.current_kernel_version = self.p_kernel_version.findall('-'.join(os.uname()[2].split('-')[:2]))[0]
            log.debug("the current_kernel_version is %s" % self.current_kernel_version)
        except Exception, e:
            log.error(e)
            self.current_kernel_version = '3.2.0-36'

    def get_cruft(self):
        try:
            cache = AptWorker.get_cache()
            count = 0
            size = 0

            if cache:
                for pkg in cache:
                    if pkg.is_installed and self.is_old_kernel_package(pkg.name):
                        log.debug("Find old kernerl: %s" % pkg.name)
                        count += 1
                        size += pkg.installed.size
                        self.emit('find_object',
                                  PackageObject(pkg.name, pkg.name, pkg.installed.size),
                                  count)

            self.emit('scan_finished', True, count, size)
        except Exception, e:
            error = get_traceback()
            log.error(error)
            self.emit('scan_error', error)

    def clean_cruft(self, cruft_list=[], parent=None):
        set_busy(parent)
        worker = AptWorker(parent,
                           finish_handler=self.on_clean_finished,
                           error_handler=self.on_error,
                           data=parent)
        worker.remove_packages([cruft.get_package_name() for cruft in cruft_list])

    def on_error(self, error):
        log.error('AptWorker error with: %s' % error)
        self.emit('clean_error', error)

    def on_clean_finished(self, transaction, status, parent):
        unset_busy(parent)
        AptWorker.update_apt_cache(True)
        self.emit('all_cleaned', True)

    def is_old_kernel_package(self, pkg):
        basenames = ['linux-image', 'linux-image-extra', 'linux-headers',
                     'linux-image-debug', 'linux-ubuntu-modules',
                     'linux-header-lum', 'linux-backport-modules',
                     'linux-header-lbm', 'linux-restricted-modules']

        if pkg.startswith('linux'):
            package = self.p_kernel_package.findall(pkg)
            if package:
                package = package[0].rstrip('-')
            else:
                return False

            if package in basenames:
                match = self.p_kernel_version.findall(pkg)
                if match and self._compare_kernel_version(match[0]):
                    return True
        return False

    @log_func(log)
    def _compare_kernel_version(self, version):
        c1, c2 = self.current_kernel_version.split('-')
        p1, p2 = version.split('-')
        if c1 == p1:
            if int(c2) > int(p2):
                return True
            else:
                return False
        else:
            return LooseVersion(c1) > LooseVersion(p1)

    def get_summary(self, count):
        if count:
            return '[%d] %s' % (count, self.__title__)
        else:
            return _('Old Kernel Packages (No old kernel package to be removed)')

########NEW FILE########
__FILENAME__ = opera_plugin
from ubuntutweak.janitor import JanitorCachePlugin

class OperaCachePlugin(JanitorCachePlugin):
    __title__ = _('Opera Cache')
    __category__ = 'application'

    root_path = '~/.opera/cache'

########NEW FILE########
__FILENAME__ = packageconfigs_plugin
import os
import time
import logging

from gi.repository import GObject, Gtk

from ubuntutweak.gui.gtk import set_busy, unset_busy
from ubuntutweak.janitor import JanitorPlugin, PackageObject
from ubuntutweak.utils import icon, filesizeformat
from ubuntutweak.policykit.dbusproxy import proxy


log = logging.getLogger('PackageConfigsPlugin')

class PackageConfigObject(PackageObject):
    def __init__(self, name):
        self.name = name

    def get_icon(self):
        return icon.get_from_name('text-plain')

    def get_size_display(self):
        return ''

    def get_size(self):
        return 0


class PackageConfigsPlugin(JanitorPlugin):
    __title__ = _('Package Configs')
    __category__ = 'system'

    def get_cruft(self):
        count = 0

        for line in os.popen('dpkg -l'):
            try:
                temp_list = line.split()
                status, pkg = temp_list[0], temp_list[1]
                if status == 'rc':
                    des = temp_list[3:]
                    count += 1
                    self.emit('find_object',
                              PackageConfigObject(pkg),
                              count)
            except:
                pass

        self.emit('scan_finished', True, count, 0)

    def clean_cruft(self, cruft_list=[], parent=None):
        for index, cruft in enumerate(cruft_list):
            log.debug('Cleaning...%s' % cruft.get_name())
            proxy.clean_configs(cruft.get_name())
            line, returncode = proxy.get_cmd_pipe()
            while returncode == 'None':
                log.debug('output: %s, returncode: %s' % (line, returncode))
                time.sleep(0.2)
                line, returncode = proxy.get_cmd_pipe()

            if returncode != '0':
                self.emit('clean_error', returncode)
                break
            else:
                self.emit('object_cleaned', cruft, index + 1)

        self.emit('all_cleaned', True)

    def get_summary(self, count):
        if count:
            return '[%d] %s' % (count, self.__title__)
        else:
            return _('Packages Configs (No package config to be removed)')

########NEW FILE########
__FILENAME__ = softwarecenter_plugin
from ubuntutweak.janitor import JanitorCachePlugin

class SoftwareCenterCachePlugin(JanitorCachePlugin):
    __title__ = _('Software Center Cache')
    __category__ = 'application'

    root_path = '~/.cache/software-center'

########NEW FILE########
__FILENAME__ = thumbnailcache_plugin
from ubuntutweak import system
from ubuntutweak.janitor import JanitorCachePlugin

class ThumbnailCachePlugin(JanitorCachePlugin):
    __title__ = _('Thumbnail cache')
    __category__ = 'personal'

    if system.CODENAME in ['precise']:
        root_path = '~/.thumbnails'
    else:
        root_path = '~/.cache/thumbnails'

########NEW FILE########
__FILENAME__ = main
# Ubuntu Tweak - Ubuntu Configuration Tool
#
# Copyright (C) 2007-2011 Tualatrix Chou <tualatrix@gmail.com>
#
# Ubuntu Tweak is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# Ubuntu Tweak is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Ubuntu Tweak; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA

import thread
import logging

from gi.repository import GObject, Gtk, Gdk, Pango

from ubuntutweak.gui import GuiBuilder
from ubuntutweak.gui.gtk import post_ui
from ubuntutweak.policykit.widgets import PolkitButton
from ubuntutweak.utils import icon
from ubuntutweak.common.consts import VERSION
from ubuntutweak.modules import ModuleLoader, create_broken_module_class
from ubuntutweak.gui.dialogs import ErrorDialog
from ubuntutweak.clips import ClipPage
from ubuntutweak.apps import AppsPage
from ubuntutweak.janitor import JanitorPage
from ubuntutweak.policykit.dbusproxy import proxy
from ubuntutweak.settings import GSetting
from ubuntutweak.preferences import PreferencesDialog

log = logging.getLogger('app')


class ModuleButton(Gtk.Button):

    _module = None

    def __str__(self):
        return '<ModuleButton: %s>' % self._module.get_title()

    def __init__(self, module):
        GObject.GObject.__init__(self)

        log.info('Creating ModuleButton: %s' % module)

        self.set_relief(Gtk.ReliefStyle.NONE)

        self._module = module

        hbox = Gtk.HBox(spacing=6)
        self.add(hbox)

        image = Gtk.Image.new_from_pixbuf(module.get_pixbuf())
        hbox.pack_start(image, False, False, 0)

        label = Gtk.Label(label=module.get_title())
        label.set_alignment(0.0, 0.5)
        label.set_line_wrap(True)
        label.set_line_wrap_mode(Pango.WrapMode.WORD)
        label.set_size_request(120, -1)
        hbox.pack_start(label, False, False, 0)

        self.show_all()

    def get_module(self):
        return self._module


class CategoryBox(Gtk.VBox):
    _modules = None
    _buttons = None
    _current_cols = 0
    _current_modules = 0

    def __str__(self):
        return '<CategoryBox with name: %s>' % self._category_name

    def __init__(self, modules=None, category='', category_name=''):
        GObject.GObject.__init__(self)

        self._modules = modules
        #TODO is category needed?
        self._category_name = category_name

        self.set_spacing(6)

        header = Gtk.HBox()
        header.set_spacing(12)
        label = Gtk.Label()
        label.set_markup("<span color='#aaa' size='x-large' weight='640'>%s</span>" % category_name)
        header.pack_start(label, False, False, 0)

        self._table = Gtk.Table()

        self._buttons = []
        for module in self._modules:
            self._buttons.append(ModuleButton(module))

        self.pack_start(header, False, False, 0)
        self.pack_start(self._table, False, False, 0)

        self.show_all()

    def get_modules(self):
        return self._modules

    def get_buttons(self):
        return self._buttons

    def rebuild_table(self, ncols):
        self._current_cols = ncols
        self._current_modules = len(self._modules)

        children = self._table.get_children()
        if children:
            for child in children:
                self._table.remove(child)

        row = 0
        col = 0
        for button in self._buttons:
            if button.get_module() in self._modules:
                self._table.attach(button, col, col + 1, row, row + 1, 0,
                                   xpadding=4, ypadding=2)
                col += 1
                if col == ncols:
                    col = 0
                    row += 1
        self.show_all()


class FeaturePage(Gtk.ScrolledWindow):

    __gsignals__ = {
        'module_selected': (GObject.SignalFlags.RUN_FIRST,
                            None,
                            (GObject.TYPE_STRING,))
    }

    _categories = None
    _boxes = []

    def __str__(self):
        return '<FeaturePage: %s>' % self._feature

    def __init__(self, feature_name):
        GObject.GObject.__init__(self,
                                 hscrollbar_policy=Gtk.PolicyType.NEVER,
                                 vscrollbar_policy=Gtk.PolicyType.AUTOMATIC)
        self.set_property('shadow-type', Gtk.ShadowType.NONE)
        self.set_border_width(12)

        self._feature = feature_name
        self._setting = GSetting('com.ubuntu-tweak.tweak.%s' % feature_name)
        self._categories = {}
        self._boxes = []

        self._box = Gtk.VBox(spacing=6)
        viewport = Gtk.Viewport()
        viewport.set_property('shadow-type', Gtk.ShadowType.NONE)
        viewport.add(self._box)
        self.add(viewport)

        self.load_modules()

        # TODO this will cause Bug #880663 randomly, as current there's no user extension for features, just disable it
#        self._setting.connect_notify(self.load_modules)

        self.show_all()

    def load_modules(self, *args, **kwargs):
        log.debug("Loading modules...")

        loader = ModuleLoader(self._feature)

        self._boxes = []
        for child in self._box.get_children():
            self._box.remove(child)

        for category, category_name in loader.get_categories():
            modules = loader.get_modules_by_category(category)
            if modules:
                module_to_loads = self._setting.get_value()

                for module in modules:
                    if module.is_user_extension() and module.get_name() not in module_to_loads:
                        modules.remove(module)

                category_box = CategoryBox(modules=modules, category_name=category_name)

                self._connect_signals(category_box)
                self._boxes.append(category_box)
                self._box.pack_start(category_box, False, False, 0)

        self.rebuild_boxes()

    def _connect_signals(self, category_box):
        for button in category_box.get_buttons():
            button.connect('clicked', self.on_button_clicked)

    def on_button_clicked(self, widget):
        log.info('Button clicked')
        module = widget.get_module()
        self.emit('module_selected', module.get_name())

    def rebuild_boxes(self, widget=None, event=None):
        request = self.get_allocation()
        ncols = request.width / 164 # 32 + 120 + 6 + 4
        width = ncols * (164 + 2 * 4) + 40
        if width > request.width:
            ncols -= 1

        pos = 0
        children = self._box.get_children()
        for box in self._boxes:
            modules = box.get_modules()
            if len (modules) == 0:
                if box in children:
                    self._box.remove(box)
            else:
                if box not in children:
                    self._box.pack_start(box, False, False, 0)
                    self._box.reorder_child(box, pos)
                box.rebuild_table(ncols)
                pos += 1


class SearchPage(FeaturePage):
    def __str__(self):
        return '<SearchPage>'

    def __init__(self, no_result_box):
        GObject.GObject.__init__(self,
                                 hscrollbar_policy=Gtk.PolicyType.NEVER,
                                 vscrollbar_policy=Gtk.PolicyType.AUTOMATIC)
        self.set_property('shadow-type', Gtk.ShadowType.NONE)
        self.set_border_width(12)

        self._boxes = []
        self.no_result_box = no_result_box

        self._box = Gtk.VBox(spacing=6)
        viewport = Gtk.Viewport()
        viewport.set_property('shadow-type', Gtk.ShadowType.NONE)
        viewport.add(self._box)
        self.add(viewport)

        self.show_all()

    def search(self, text):
        modules = ModuleLoader.fuzz_search(text)
        self._boxes = []
        for child in self._box.get_children():
            self._box.remove(child)

        if modules:
            category_box = CategoryBox(modules=modules, category_name=_('Results'))

            self._connect_signals(category_box)
            self._boxes.append(category_box)
            self._box.pack_start(category_box, False, False, 0)

            self.rebuild_boxes()
        else:
            self.no_result_box.label.set_markup(_('Your filter "<b>%s</b>" does not match any items.') % text)
            self._box.pack_start(self.no_result_box, False, False, 0)

    def clean(self):
        self._boxes = []

        for child in self._box.get_children():
            self._box.remove(child)

class UbuntuTweakWindow(GuiBuilder):
    current_feature = 'overview'
    feature_dict = {}
    navigation_dict = {'tweaks': [None, None]}
    # the module name and page index: 'Compiz': 2
    loaded_modules = {}
    # reversed dict: 2: 'CompizClass'
    modules_index = {}

    def __init__(self, feature='', module='', splash_window=None):
        GuiBuilder.__init__(self, file_name='mainwindow.ui')

        tweaks_page = FeaturePage('tweaks')
        admins_page = FeaturePage('admins')
        self.no_result_box.label = self.result_text
        self.search_page = SearchPage(self.no_result_box)
        clip_page = ClipPage()
        self.apps_page = AppsPage(self.back_button, self.next_button)
        janitor_page = JanitorPage()
        self.preferences_dialog = PreferencesDialog(self.mainwindow)

        self.recently_used_settings = GSetting('com.ubuntu-tweak.tweak.recently-used')

        self.feature_dict['overview'] = self.notebook.append_page(clip_page, Gtk.Label('overview'))
        self.feature_dict['apps'] = self.notebook.append_page(self.apps_page, Gtk.Label())
        self.feature_dict['tweaks'] = self.notebook.append_page(tweaks_page, Gtk.Label('tweaks'))
        self.feature_dict['admins'] = self.notebook.append_page(admins_page, Gtk.Label('admins'))
        self.feature_dict['janitor'] = self.notebook.append_page(janitor_page, Gtk.Label('janitor'))
        self.feature_dict['wait'] = self.notebook.append_page(self._crete_wait_page(),
                                                           Gtk.Label('wait'))
        self.feature_dict['search'] = self.notebook.append_page(self.search_page,
                                                           Gtk.Label('search'))

        # Always show welcome page at first
        self.mainwindow.connect('realize', self._initialize_ui_states, splash_window)
        self.back_button.connect('clicked', self.on_back_button_clicked)
        self.next_button.connect('clicked', self.on_next_button_clicked)
        tweaks_page.connect('module_selected', self.on_module_selected)
        self.search_page.connect('module_selected', self.on_module_selected)
        admins_page.connect('module_selected', self.on_module_selected)
        self.apps_page.connect('loaded', self.show_apps_page)
        clip_page.connect('load_module', lambda widget, name: self.do_load_module(name))
        clip_page.connect('load_feature', lambda widget, name: self.select_target_feature(name))

        self.mainwindow.show()

        if module:
            self.do_load_module(module)
        elif feature:
            self.select_target_feature(feature)

        accel_group = Gtk.AccelGroup()
        self.search_entry.add_accelerator('activate',
                                          accel_group,
                                          Gdk.KEY_f,
                                          Gdk.ModifierType.CONTROL_MASK,
                                          Gtk.AccelFlags.VISIBLE)
        self.mainwindow.add_accel_group(accel_group)
        thread.start_new_thread(self.preload_proxy_cache, ())

    def show_apps_page(self, widget):
        self.notebook.set_current_page(self.feature_dict['apps'])

    def preload_proxy_cache(self):
        #This function just called to make sure the cache is loaded as soon as possible
        proxy.is_package_installed('ubuntu-tweak')

    def on_search_entry_activate(self, widget):
        widget.grab_focus()
        self.on_search_entry_changed(widget)

    def on_search_entry_changed(self, widget):
        text = widget.get_text()
        self.set_current_module(None, None)

        if text:
            self.notebook.set_current_page(self.feature_dict['search'])
            self.search_page.search(text)
            self.search_entry.set_property('secondary-icon-name', 'edit-clear')
        else:
            self.on_feature_button_clicked(getattr(self, '%s_button' % self.current_feature), self.current_feature)
            self.search_page.clean()
            self.search_entry.set_property('secondary-icon-name', 'edit-find')

    def on_search_entry_icon_press(self, widget, icon_pos, event):
        widget.set_text('')

    def get_module_and_index(self, name):
        index = self.loaded_modules[name]

        return self.modules_index[index], index

    def select_target_feature(self, text):
        toggle_button = getattr(self, '%s_button' % text, None)
        log.info("select_target_feature: %s" % text)
        if toggle_button:
            self.current_feature = text
            toggle_button.set_active(True)

    def _initialize_ui_states(self, widget, splash_window):
        self.window_size_setting = GSetting('com.ubuntu-tweak.tweak.window-size')
        width, height = self.window_size_setting.get_value()
        if width >= 900 and height >= 506:
            self.mainwindow.set_default_size(width, height)

        for feature_button in ('overview_button', 'apps_button', 'admins_button', \
                               'tweaks_button', 'janitor_button'):
            button = getattr(self, feature_button)

            label = button.get_child().get_label()
            button.get_child().set_markup('<b>%s</b>' % label)
            button.get_child().set_use_underline(True)
        splash_window.destroy()

    def _crete_wait_page(self):
        vbox = Gtk.VBox()

        label = Gtk.Label()
        label.set_markup("<span size=\"xx-large\">%s</span>" % \
                        _('Please wait a moment...'))
        label.set_justify(Gtk.Justification.FILL)
        vbox.pack_start(label, False, False, 50)
        hbox = Gtk.HBox()
        vbox.pack_start(hbox, False, False, 0)

        vbox.show_all()

        return vbox

    def on_mainwindow_destroy(self, widget=None):
        allocation = widget.get_allocation()
        self.window_size_setting.set_value((allocation.width, allocation.height))

        Gtk.main_quit()
        try:
            proxy.exit()
        except Exception, e:
            log.error(e)

    def on_about_button_clicked(self, widget):
        self.aboutdialog.set_version(VERSION)
        self.aboutdialog.set_transient_for(self.mainwindow)
        self.aboutdialog.run()
        self.aboutdialog.hide()

    def on_preference_button_clicked(self, widget):
        self.preferences_dialog.run(self.current_feature)
        self.preferences_dialog.hide()

    def on_module_selected(self, widget, name):
        log.debug('Select module: %s' % name)

        if name in self.loaded_modules:
            module, index = self.get_module_and_index(name)
            self._save_loaded_info(name, module, index)
            self.set_current_module(module, index)
        else:
            self.do_load_module(name)

    def do_load_module(self, name):
        self.notebook.set_current_page(self.feature_dict['wait'])
        GObject.timeout_add(5, self._load_module, name)

    def set_current_module(self, module=None, index=None):
        if index:
            self.notebook.set_current_page(index)

        if module and index:
            self.module_image.set_from_pixbuf(module.get_pixbuf(size=48))
            self.title_label.set_markup('<b><big>%s</big></b>' % module.get_title())
            self.description_label.set_text(module.get_description())
            page = self.notebook.get_nth_page(index)

            if page.__policykit__:
                if hasattr(page, 'un_lock'):
                    page.un_lock.show()
                    self._last_unlock = page.un_lock
                else:
                    page.un_lock = PolkitButton(page.__policykit__)
                    page.un_lock.connect('authenticated', page.on_polkit_action)
                    page.un_lock.show()
                    self._last_unlock = page.un_lock
                    self.right_top_box.pack_start(page.un_lock, False, False, 6)
                    self.right_top_box.reorder_child(page.un_lock, 0)

            if not module.__name__.startswith('Broken'):
                self.log_used_module(module.__name__)
            self.update_jump_buttons()
        else:
            # no module, so back to logo
            self.module_image.set_from_pixbuf(icon.get_from_name('ubuntu-tweak', size=48))
            self.title_label.set_markup('')
            self.description_label.set_text('')

            if hasattr(self, '_last_unlock'):
                self._last_unlock.hide()

    def _save_loaded_info(self, name, module, index):
        log.info('_save_loaded_info: %s, %s, %s' % (name, module, index))
        self.loaded_modules[name] = index
        self.modules_index[index] = module
        self.navigation_dict[self.current_feature] = name, None

    @post_ui
    def _load_module(self, name):
        feature, module = ModuleLoader.search_module_for_name(name)

        if module:
            self.select_target_feature(feature)

            if name in self.loaded_modules:
                module, index = self.get_module_and_index(name)
            else:
                try:
                    page = module()
                except Exception, e:
                    log.error(e)
                    module = create_broken_module_class(name)
                    page = module()

                page.show_all()
                index = self.notebook.append_page(page, Gtk.Label(label=name))

            self._save_loaded_info(name, module, index)
            self.navigation_dict[feature] = name, None
            self.set_current_module(module, index)
            self.update_jump_buttons()
        else:
            dialog = ErrorDialog(title=_('No module named "%s"') % name,
                                 message=_('Please ensure you have entered the correct module name.'))
            dialog.launch()
            self.notebook.set_current_page(self.feature_dict[self.current_feature])

    def update_jump_buttons(self, disable=False):
        if not disable:
            back, forward = self.navigation_dict[self.current_feature]
            self.back_button.set_sensitive(bool(back))
            self.next_button.set_sensitive(bool(forward))
        else:
            self.back_button.set_sensitive(False)
            self.next_button.set_sensitive(False)

    def on_back_button_clicked(self, widget):
        self.navigation_dict[self.current_feature] = tuple(reversed(self.navigation_dict[self.current_feature]))
        self.notebook.set_current_page(self.feature_dict[self.current_feature])
        self.set_current_module(None)

        self.update_jump_buttons()

    def on_next_button_clicked(self, widget):
        back, forward = self.navigation_dict[self.current_feature]
        self.navigation_dict[self.current_feature] = forward, back

        module, index = self.get_module_and_index(forward)
        log.debug("Try to forward to: %d" % index)
        self.notebook.set_current_page(index)
        self.set_current_module(module, index)

        self.update_jump_buttons()

    def on_apps_button_toggled(self, widget):
        self.on_feature_button_clicked(widget, 'apps')

    def on_apps_button_clicked(self, widget):
        self.navigation_dict['apps'] = tuple(reversed(self.navigation_dict['apps']))
        self.on_apps_button_toggled(widget)

    def on_tweaks_button_clicked(self, widget):
        self.navigation_dict['tweaks'] = tuple(reversed(self.navigation_dict['tweaks']))
        self.on_tweaks_button_toggled(widget)

    def on_tweaks_button_toggled(self, widget):
        self.on_feature_button_clicked(widget, 'tweaks')

    def on_admins_button_clicked(self, widget):
        self.navigation_dict['admins'] = tuple(reversed(self.navigation_dict['admins']))
        self.on_admins_button_toggled(widget)

    def on_admins_button_toggled(self, widget):
        self.on_feature_button_clicked(widget, 'admins')

    def on_overview_button_toggled(self, widget):
        self.on_feature_button_clicked(widget, 'overview')

    def on_janitor_button_toggled(self, widget):
        self.on_feature_button_clicked(widget, 'janitor')
        self.module_image.set_from_pixbuf(icon.get_from_name('computerjanitor', size=48))
        self.title_label.set_markup('<b><big>%s</big></b>' % _('Computer Janitor'))
        self.description_label.set_text(_("Clean up a system so it's more like a freshly installed one"))

    def on_feature_button_clicked(self, widget, feature):
        log.debug("on_%s_button_toggled and widget.active is: %s" % (feature, widget.get_active()))
        self.current_feature = feature

        if widget.get_active():
            if feature not in self.navigation_dict:
                log.debug("Feature %s is not in self.navigation_dict" % feature)
                self.navigation_dict[feature] = None, None
                self.notebook.set_current_page(self.feature_dict[feature])
                self.set_current_module(None)
            else:
                back, backwards = self.navigation_dict[feature]
                if back:
                    module, index = self.get_module_and_index(back)
                    self.set_current_module(module, index)
                    self.notebook.set_current_page(index)
                else:
                    self.notebook.set_current_page(self.feature_dict[feature])
                    self.set_current_module(None)

            if feature == 'apps':
                log.debug("handler_block_by_func by apps")
                self.back_button.handler_block_by_func(self.on_back_button_clicked)
                self.next_button.handler_block_by_func(self.on_next_button_clicked)
                if not self.apps_page.is_loaded:
                    self.notebook.set_current_page(self.feature_dict['wait'])
                    self.apps_page.load()
                self.apps_page.set_web_buttons_active(True)
            else:
                self.update_jump_buttons()
        else:
            if feature == 'apps':
                log.debug("handler_unblock_by_func by apps")
                self.apps_page.set_web_buttons_active(False)
                self.back_button.handler_unblock_by_func(self.on_back_button_clicked)
                self.next_button.handler_unblock_by_func(self.on_next_button_clicked)

    def log_used_module(self, name):
        log.debug("Log the %s to Recently Used" % name)
        used_list = self.recently_used_settings.get_value()

        if name in used_list:
            used_list.remove(name)

        used_list.insert(0, name)
        self.recently_used_settings.set_value(used_list[:15])

    def present(self):
        self.mainwindow.present()

########NEW FILE########
__FILENAME__ = autostart
#!/usr/bin/python

# Ubuntu Tweak - PyGTK based desktop configuration tool
#
# Copyright (C) 2007-2008 TualatriX <tualatrix@gmail.com>
#
# Ubuntu Tweak is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# Ubuntu Tweak is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Ubuntu Tweak; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA

import os
import gtk
import shutil
import gobject

from xdg.DesktopEntry import DesktopEntry
from ubuntutweak.modules  import TweakModule
from ubuntutweak.ui.dialogs import ErrorDialog
from ubuntutweak.utils import icon

(
    COLUMN_ACTIVE,
    COLUMN_ICON,
    COLUMN_PROGRAM,
    COLUMN_PATH,
) = range(4)

class AutoStartDialog(gtk.Dialog):
    """The dialog used to add or edit the autostart program"""
    def __init__(self, desktopentry = None, parent = None):
        """Init the dialog, if use to edit, pass the desktopentry parameter"""
        gtk.Dialog.__init__(self, parent = parent)
        self.set_default_size(400, -1)

        lbl1 = gtk.Label()
        lbl1.set_text_with_mnemonic(_("_Name:"))
        lbl1.set_alignment(0, 0)
        lbl2 = gtk.Label()
        lbl2.set_text_with_mnemonic(_("Co_mmand:"))
        lbl2.set_alignment(0, 0)
        lbl3 = gtk.Label()
        lbl3.set_text_with_mnemonic(_("Comm_ent:"))
        lbl3.set_alignment(0, 0)

        self.pm_name = gtk.Entry ();
        self.pm_name.connect("activate", self.on_entry_activate)
        self.pm_cmd = gtk.Entry ();
        self.pm_cmd.connect("activate", self.on_entry_activate)
        self.pm_comment = gtk.Entry ();
        self.pm_comment.connect("activate", self.on_entry_activate)

        if desktopentry:
            self.set_title(_("Edit Startup Program"))
            self.pm_name.set_text(desktopentry.getName())
            self.pm_cmd.set_text(desktopentry.getExec())
            self.pm_comment.set_text(desktopentry.getComment())
        else:
            self.set_title(_("New Startup Program"))

        button = gtk.Button(_("_Browse..."))
        button.connect("clicked", self.on_choose_program)
        
        hbox = gtk.HBox(False, 5)
        hbox.pack_start(self.pm_cmd)
        hbox.pack_start(button, False, False, 0)

        table = gtk.Table(3, 2)
        table.attach(lbl1, 0, 1, 0, 1, xoptions = gtk.FILL, xpadding = 10, ypadding = 10)
        table.attach(lbl2, 0, 1, 1, 2, xoptions = gtk.FILL, xpadding = 10, ypadding = 10)
        table.attach(lbl3, 0, 1, 2, 3, xoptions = gtk.FILL, xpadding = 10, ypadding = 10)
        table.attach(self.pm_name, 1, 2, 0, 1)
        table.attach(hbox, 1, 2, 1, 2, yoptions = gtk.EXPAND)
        table.attach(self.pm_comment, 1, 2, 2, 3)

        self.vbox.pack_start(table)

        self.add_button(gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL)
        self.add_button(gtk.STOCK_SAVE, gtk.RESPONSE_OK)

        self.set_default_response(gtk.RESPONSE_OK)

        self.show_all()

    def on_entry_activate(self, widget, data = None):
        self.response(gtk.RESPONSE_OK)

    def on_choose_program(self, widget, data = None):
        """The action taken by clicked the browse button"""
        dialog = gtk.FileChooserDialog(_("Choose a Program"), 
                            action = gtk.FILE_CHOOSER_ACTION_OPEN, 
                            buttons = (gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL,
                                        gtk.STOCK_OPEN, gtk.RESPONSE_ACCEPT))

        if dialog.run() == gtk.RESPONSE_ACCEPT:
            self.pm_cmd.set_text(dialog.get_filename())
        dialog.destroy()

class AutoStartItem(gtk.TreeView):
    """The autostart program list, loading from userdir and systemdir"""
    userdir = os.path.join(os.path.expanduser("~"), ".config/autostart")
    etc_dir = "/etc/xdg/autostart"
    gnome_dir = "/usr/share/gnome/autostart"

    def __init__(self):
        gtk.TreeView.__init__(self)

        self.refresh_items()

        model = gtk.ListStore(
                    gobject.TYPE_BOOLEAN,
                    gtk.gdk.Pixbuf,
                    gobject.TYPE_STRING,
                    gobject.TYPE_STRING)

        model.set_sort_column_id(COLUMN_PROGRAM, gtk.SORT_ASCENDING)

        self.set_model(model)
        self.__create_model()

        self.__add_columns()
        self.set_rules_hint(True)

        selection = self.get_selection()
        selection.connect("changed", self.selection_cb)

        menu = self.create_popup_menu()
        menu.show_all()
        self.connect("button_press_event", self.button_press_event, menu)    

    def refresh_items(self):
        if not os.path.exists(self.userdir): os.mkdir(self.userdir)

        #get the item with full-path from the dirs
        self.useritems = map(lambda path: "%s/%s" % (self.userdir, path), 
                                                    os.listdir(self.userdir))

        etc_items = []
        gnome_items = []
        if os.path.exists(self.etc_dir):
            etc_items = map(lambda path: "%s/%s" % (self.etc_dir, path),
                        filter(lambda i: i not in os.listdir(self.userdir), 
                                                    os.listdir(self.etc_dir)))

        if os.path.exists(self.gnome_dir):
            gnome_items = map(lambda path: "%s/%s" % (self.gnome_dir, path),
                        filter(lambda i: i not in os.listdir(self.userdir), 
                                                    os.listdir(self.gnome_dir)))

        self.systemitems = etc_items + gnome_items

        for item in self.useritems:
            if os.path.isdir(item): 
                self.useritems.remove(item)
        for item in self.systemitems:
            if os.path.isdir(item): 
                self.systemitems.remove(item)

    def selection_cb(self, widget, data = None):
        """If selected an item, it should set the sensitive of the remove and edit button"""
        model, iter = widget.get_selected()
        remove = self.get_data("remove")
        edit = self.get_data("edit")
        if iter:
            remove.set_sensitive(True)
            edit.set_sensitive(True)
        else:
            remove.set_sensitive(False)
            edit.set_sensitive(False)

    def button_press_event(self, widget, event, menu):
        """If right-click taken, show the popup menu"""
        if event.type == gtk.gdk.BUTTON_PRESS and event.button == 3:
            menu.popup(None, None, None, event.button, event.time)
        return False

    def create_popup_menu(self):
        menu = gtk.Menu()

        remove = gtk.MenuItem(_("Delete from Disk"))
        remove.connect("activate", self.on_delete_from_disk)
        
        menu.append(remove)
        menu.attach_to_widget(self, None)

        return menu

    def on_delete_from_disk(self, widget, data = None):
        model, iter = self.get_selection().get_selected()

        if iter:
            path = model.get_value(iter, COLUMN_PATH)
            if self.is_defaultitem(path):
                ErrorDialog(_("Can't delete system item from disk.")).launch()
            else:
                os.remove(path)

        self.update_items()

    def update_items(self, all = False, comment = False):
        """'all' parameter used to show the hide item,
        'comment' parameter used to show the comment of program"""
        self.refresh_items()
        self.__create_model(all, comment)

    def __create_model(self, all = False, comment = False):
        model = self.get_model()
        model.clear()

        allitems = []
        allitems.extend(self.useritems)
        allitems.extend(self.systemitems)

        for item in allitems:
            try:
                desktopentry = DesktopEntry(item)
            except:
                continue

            if desktopentry.get("Hidden"):
                if not all:
                    continue
            iter = model.append()
            enable = desktopentry.get("X-GNOME-Autostart-enabled")
            if enable == "false":
                enable = False
            else:
                enable = True
            
            iconname = desktopentry.get('Icon', locale = False)
            if not iconname:
               iconname = desktopentry.get('Name', locale = False)
               if not iconname:
                   iconname = desktopentry.getName()

            pixbuf = icon.get_from_name(iconname, size=32)

            try:
                name = desktopentry.getName()
            except:
                name = desktopentry.get('Name', locale=False)

            if comment:
                comment = desktopentry.getComment()
                if not comment:
                    comment = _("No description")
                description = "<b>%s</b>\n%s" % (name, comment)
            else:
                description = "<b>%s</b>" % name

            model.set(iter,
                      COLUMN_ACTIVE, enable,
                      COLUMN_ICON, pixbuf,
                      COLUMN_PROGRAM, description,
                      COLUMN_PATH, item)

    def __add_columns(self):
        model = self.get_model()

        renderer = gtk.CellRendererToggle()
        renderer.connect("toggled", self.enabled_toggled, model)
        column = gtk.TreeViewColumn("", renderer, active = COLUMN_ACTIVE)
        column.set_sort_column_id(COLUMN_ACTIVE)
        self.append_column(column)

        column = gtk.TreeViewColumn(_("Program"))
        column.set_spacing(3)

        renderer = gtk.CellRendererPixbuf()
        column.pack_start(renderer, False)
        column.set_attributes(renderer, pixbuf = COLUMN_ICON)

        renderer = gtk.CellRendererText()
        column.pack_start(renderer, True)
        column.set_attributes(renderer, markup = COLUMN_PROGRAM)
        column.set_sort_column_id(COLUMN_PROGRAM)
        self.append_column(column)

    def enabled_toggled(self, cell, path, model):
        iter = model.get_iter((int(path),))
        active = model.get_value(iter, COLUMN_ACTIVE)
        path = model.get_value(iter, COLUMN_PATH)

        if self.is_defaultitem(path):
            shutil.copy(path, self.userdir)
            path = os.path.join(self.userdir, os.path.basename(path))
            desktopentry = DesktopEntry(path)
            desktopentry.set("X-GNOME-Autostart-enabled", "false")
            desktopentry.write()
            model.set(iter, COLUMN_PATH, path)
        else:
            if active:
                desktopentry = DesktopEntry(path)
                desktopentry.set("X-GNOME-Autostart-enabled", "false")
                desktopentry.write()
            else:
                if self.is_in_systemdir(path):
                    os.remove(path)
                    path = os.path.join(self.get_systemdir(path), os.path.basename(path))
                    model.set(iter, COLUMN_PATH, path)
                else:
                    desktopentry = DesktopEntry(path)
                    desktopentry.set("X-GNOME-Autostart-enabled", "true")
                    desktopentry.set("Hidden", "false")
                    desktopentry.write()

        active =  not active

        model.set(iter, COLUMN_ACTIVE, active)

    def is_in_systemdir(self, path):
        return os.path.basename(path) in os.listdir(self.etc_dir) or \
                os.path.basename(path) in os.listdir(self.gnome_dir)

    def is_defaultitem(self, path):
        return os.path.dirname(path) in [self.etc_dir, self.gnome_dir]

    def get_systemdir(self, path):
        if os.path.basename(path) in os.listdir(self.etc_dir):
            return self.etc_dir
        elif os.path.basename(path) in os.listdir(self.gnome_dir):
            return self.gnome_dir

class AutoStart(TweakModule):
    __title__ = _('Auto Start Programs')
    __desc__ = _('Here you can manage which programs are run upon login.\n'
                'You can hide items from view by selecting them and clicking "Remove"\n'
                'To permanently delete an item, right-click and select "Delete".')
    __icon__ = 'session-properties'
    __category__ = 'startup'
    __utactive__ = False

    def __init__(self):
        TweakModule.__init__(self)

        hbox = gtk.HBox(False, 10)
        self.add_start(hbox, True, True, 0)

        #create the two checkbutton for extra options of auto run list
        self.show_comment_button = gtk.CheckButton(_("Show comments"))
        self.add_start(self.show_comment_button, False, False, 0)
        self.show_all_button = gtk.CheckButton(_("Show all runnable programs"))
        self.add_start(self.show_all_button, False, False, 0)

        self.show_all_button.connect("toggled", self.on_show_all, self.show_comment_button)
        self.show_comment_button.connect("toggled", self.on_show_comment, self.show_all_button)

        sw = gtk.ScrolledWindow()
        sw.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
        hbox.pack_start(sw)

        self.treeview = AutoStartItem()
        self.treeview.connect('row-activated', self.on_row_activated)
        sw.add(self.treeview)
        
        vbox = gtk.VBox(False, 5)
        hbox.pack_start(vbox, False, False, 0)

        button = gtk.Button(stock = gtk.STOCK_ADD)
        button.connect("clicked", self.on_add_item, self.treeview)
        vbox.pack_start(button, False, False, 0)

        button = gtk.Button(stock = gtk.STOCK_REMOVE)
        button.set_sensitive(False)
        button.connect("clicked", self.on_remove_item, self.treeview)
        vbox.pack_start(button, False, False, 0)
        self.treeview.set_data("remove", button)

        button = gtk.Button(stock = gtk.STOCK_EDIT)
        button.set_sensitive(False)
        button.connect("clicked", self.on_edit_item, self.treeview)
        vbox.pack_start(button, False, False, 0)
        self.treeview.set_data("edit", button)

    def on_row_activated(self, widget, path, col):
        self.on_edit_item(widget, widget)

    def on_show_all(self, widget, another):
        if widget.get_active():
            if another.get_active():
                self.treeview.update_items(all = True, comment = True)
            else:
                self.treeview.update_items(all = True)
        else:
            if another.get_active():
                self.treeview.update_items(comment = True)
            else:
                self.treeview.update_items()

    def on_show_comment(self, widget, another):
        if widget.get_active():
            if another.get_active():
                self.treeview.update_items(all = True, comment = True)
            else:
                self.treeview.update_items(comment = True)
        else:
            if another.get_active():
                self.treeview.update_items(all = True)
            else:
                self.treeview.update_items()

    def on_add_item(self, widget, treeview):
        dialog = AutoStartDialog(parent = widget.get_toplevel())
        if dialog.run() == gtk.RESPONSE_OK:
            name = dialog.pm_name.get_text()
            cmd = dialog.pm_cmd.get_text()
            if not name:
                ErrorDialog(_("The name of the startup program cannot be empty")).launch()
            elif not cmd:
                ErrorDialog(_("Text field was empty (or contained only whitespace)")).launch()
            else:
                path = os.path.join(treeview.userdir, os.path.basename(cmd) + ".desktop")
                desktopentry = DesktopEntry(path)
                desktopentry.set("Name", dialog.pm_name.get_text())
                desktopentry.set("Exec", dialog.pm_cmd.get_text())
                desktopentry.set("Comment", dialog.pm_comment.get_text())
                desktopentry.set("Type", "Application")
                desktopentry.set("Version", "1.0")
                desktopentry.set("X-GNOME-Autostart-enabled", "true")
                desktopentry.write()
                treeview.update_items(all = self.show_all_button.get_active(), comment = self.show_comment_button.get_active())
                dialog.destroy()
                return
        dialog.destroy()

    def on_remove_item(self, widget, treeview):
        model, iter = treeview.get_selection().get_selected()

        if iter:
            path = model.get_value(iter, COLUMN_PATH)
            if path[1:4] == "etc":
                shutil.copy(path, treeview.userdir)
                desktopentry = DesktopEntry(os.path.join(treeview.userdir, os.path.basename(path)))
            else:
                desktopentry = DesktopEntry(path)
            desktopentry.set("Hidden", "true")
            desktopentry.set("X-GNOME-Autostart-enabled", "false")
            desktopentry.write()

            treeview.update_items(all = self.show_all_button.get_active(), comment = self.show_comment_button.get_active())

    def on_edit_item(self, widget, treeview):
        model, iter = treeview.get_selection().get_selected()

        if iter:
            path = model.get_value(iter, COLUMN_PATH)
            if path[1:4] == "etc":
                shutil.copy(path, treeview.userdir)
                path = os.path.join(treeview.userdir, os.path.basename(path))
            dialog = AutoStartDialog(DesktopEntry(path), widget.get_toplevel())
            if dialog.run() == gtk.RESPONSE_OK:
                name = dialog.pm_name.get_text()
                cmd = dialog.pm_cmd.get_text()
                if not name:
                    ErrorDialog(_("The name of the startup program cannot be empty")).launch()
                elif not cmd:
                    ErrorDialog(_("Text field was empty (or contained only whitespace)")).launch()
                else:
                    desktopentry = DesktopEntry(path)
                    desktopentry.set("Name", name, locale = True)
                    desktopentry.set("Exec", cmd)
                    desktopentry.set("Comment", dialog.pm_comment.get_text(), locale = True)
                    desktopentry.write()
                    treeview.update_items(all = self.show_all_button.get_active(), comment = self.show_comment_button.get_active())
                    dialog.destroy()
                    return
            dialog.destroy()

########NEW FILE########
__FILENAME__ = taskinstall
#!/usr/bin/python

# Ubuntu Tweak - PyGTK based desktop configuration tool
#
# Copyright (C) 2007-2009 TualatriX <tualatrix@gmail.com>
#
# Ubuntu Tweak is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# Ubuntu Tweak is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Ubuntu Tweak; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA

import os
import gtk
import pango
import gobject

from ubuntutweak.modules import TweakModule
from ubuntutweak.ui import CellRendererButton
from ubuntutweak.ui.dialogs import QuestionDialog, InfoDialog, WarningDialog
from ubuntutweak.modules.sourcecenter import UpdateView
from ubuntutweak.common.package import PACKAGE_WORKER, PackageInfo

TASKS = {
    'server': (_('Basic Ubuntu server'), _('This task provides the Ubuntu server environment.')),
    'eucalyptus-simple-cluster': (_('Cloud computing cluster'), _('Combined Eucalyptus cloud and cluster controllers.')),
    'eucalyptus-node': (_('Cloud computing node'), _('Eucalyptus node controller.')),
    'dns-server': (_('DNS server'), _('Selects the BIND DNS server and its documentation.')),
    'edubuntu-server': (_('Edubuntu server'), _('This task provides the Edubuntu classroom server.')),
    'lamp-server': (_('LAMP server'), _('Selects a ready-made Linux/Apache/MySQL/PHP server.')),
    'mail-server': (_('Mail server'), _('This task selects a variety of package useful for a general purpose mail server system.')),
    'openssh-server': (_('OpenSSH server'), _('Selects packages needed for an OpenSSH server.')),
    'postgresql-server': (_('PostgreSQL database'), _('This task selects client and server packages for the PostgreSQL database. . PostgreSQL is an SQL relational database, offering increasing SQL92 compliance and some SQL3 features.  It is suitable for use with multi-user database access, through its facilities for transactions and fine-grained locking.')),
    'print-server': (_('Print server'), _('This task sets up your system to be a print server.')),
    'samba-server': (_('Samba file server'), _('This task sets up your system to be a Samba file server, which is  especially suitable in networks with both Windows and Linux systems.')),
    'tomcat-server': (_('Tomcat Java server'), _('Selects a ready-made Java Application server.')),
    'uec': (_('Ubuntu Enterprise Cloud (instance)'), _('Packages included in UEC images.')),
    'virt-host': (_('Virtual Machine host'), _('Packages necessary to host virtual machines')),
    'ubuntustudio-graphics': (_('2D/3D creation and editing suite'), _('2D/3D creation and editing suite')),
    'ubuntustudio-audio': (_('Audio creation and editing suite'), _('Audio creation and editing suite')),
    'edubuntu-desktop-kde': (_('Edubuntu KDE desktop'), _('This task provides the Edubuntu desktop environment (KDE variant).')),
    'edubuntu-desktop-gnome': (_('Edubuntu desktop'), _('This task provides the Edubuntu desktop environment.')),
    'kubuntu-desktop': (_('Kubuntu desktop'), _('This task provides the Kubuntu desktop environment.')),
    'kubuntu-netbook': (_('Kubuntu netbook'), _('This task provides the Kubuntu desktop environment optimized for netbooks.')),
    'ubuntustudio-audio-plugins': (_('LADSPA and DSSI audio plugins'), _('LADSPA and DSSI audio plugins')),
    'ubuntustudio-font-meta': (_('Large selection of font packages'), _('Large selection of font packages')),
    'mythbuntu-desktop': (_('Mythbuntu additional roles'), _('This task provides Mythbuntu roles for an existing system.')),
    'mythbuntu-frontend': (_('Mythbuntu frontend'), _('This task installs a MythTV frontend. It needs an existing master backend somewhere on your network.')),
    'mythbuntu-backend-master': (_('Mythbuntu master backend'), _('This task installs a MythTV master backend and a mysql server server system.')),
    'mythbuntu-backend-slave': (_('Mythbuntu slave backend'), _('This task installs a MythTV slave backend. It needs an existing master backend somewhere on your network.')),
    'mobile-mid': (_('Ubuntu MID edition'), _('This task provides the Ubuntu MID environment.')),
    'ubuntu-netbook-remix': (_('Ubuntu Netbook Remix'), _('This task provides the Ubuntu Netbook Remix environment.')),
    'ubuntu-desktop': (_('Ubuntu desktop'), _('This task provides the Ubuntu desktop environment.')),
    'ubuntustudio-video': (_('Video creation and editing suite'), _('Video creation and editing suite')),
    'xubuntu-desktop': (_('Xubuntu desktop'), _('This task provides the Xubuntu desktop environment.')),
    'edubuntu-dvd-live': (_('Edubuntu live DVD'), _('This task provides the extra packages installed on the Ubuntu live DVD, above and beyond those included on the Ubuntu live CD. It is neither useful nor recommended to install this task in other environments.')),
    'kubuntu-netbook-live': (_('Kubuntu Netbook Edition live CD'), _('This task provides the extra packages installed on the Kubuntu Netbook live CD. It is neither useful nor recommended to install this task in other environments.')),
    'kubuntu-live': (_('Kubuntu live CD'), _('This task provides the extra packages installed on the Kubuntu live CD. It is neither useful nor recommended to install this task in other environments.')),
    'kubuntu-dvd-live': (_('Kubuntu live DVD'), _('This task provides the extra packages installed on the Kubuntu live DVD, above and beyond those included on the Kubuntu live CD. It is neither useful nor recommended to install this task in other environments.')),
    'mythbuntu-live': (_('Mythbuntu live CD'), _('This task provides the extra packages installed on the Mythbuntu live CD. It is neither useful nor recommended to install this task in other environments.')),
    'mobile-live': (_('Ubuntu MID live environment'), _('This task provides the extra packages installed in the Ubuntu MID live environment. It is neither useful nor recommended to install this task in other environments.')),
    'unr-live': (_('Ubuntu Netbook Remix live environment'), _('This task provides the extra packages installed in the Ubuntu Netbook Remix live environment. It is neither useful nor recommended to install this task in other environments.')),
    'ubuntu-live': (_('Ubuntu live CD'), _('This task provides the extra packages installed on the Ubuntu live CD. It is neither useful nor recommended to install this task in other environments.')),
    'ubuntu-dvd-live': (_('Ubuntu live DVD'), _('This task provides the extra packages installed on the Ubuntu live DVD, above and beyond those included on the Ubuntu live CD. It is neither useful nor recommended to install this task in other environments.')),
    'xubuntu-live': (_('Xubuntu live CD'), _('This task provides the extra packages installed on the Xubuntu live CD. It is neither useful nor recommended to install this task in other environments.')),
}

class TaskView(gtk.TreeView):
    (COLUMN_ACTION,
     COLUMN_TASK,
     COLUMN_NAME,
     COLUMN_DESC,
    ) = range(4)

    def __init__(self):
        gtk.TreeView.__init__(self)

        self.set_headers_visible(False)
        self.set_rules_hint(True)
        self.model = self.__create_model()
        self.set_model(self.model)
        self.update_model()
        self.__add_columns()

        selection = self.get_selection()
        selection.select_iter(self.model.get_iter_first())

    def __create_model(self):
        '''The model is icon, title and the list reference'''
        model = gtk.ListStore(
                    gobject.TYPE_STRING, #Install status
                    gobject.TYPE_STRING,  #package name
                    gobject.TYPE_STRING,  #task name
                    gobject.TYPE_STRING,  #task description
                    )
        
        return model

    def __add_columns(self):
        column = gtk.TreeViewColumn(_('Categories'))

        renderer = gtk.CellRendererText()
        renderer.set_property('ellipsize', pango.ELLIPSIZE_END)
        renderer.set_property('mode', gtk.CELL_RENDERER_MODE_ACTIVATABLE)
        column.pack_start(renderer, True)
        column.set_sort_column_id(self.COLUMN_NAME)
        column.set_attributes(renderer, markup=self.COLUMN_DESC)
        column.set_resizable(True)
        self.append_column(column)

        renderer = CellRendererButton()
        renderer.connect("clicked", self.on_action_clicked)
        column.pack_end(renderer, False)
        column.set_attributes(renderer, text=self.COLUMN_ACTION)

    def create_task_dialog(self, title, desc, updateview):
        dialog = QuestionDialog(desc, title=title)
        vbox = dialog.vbox
        swindow = gtk.ScrolledWindow()
        swindow.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
        swindow.set_size_request(-1, 200)
        vbox.pack_start(swindow, False, False, 0)
        swindow.add(updateview)
        swindow.show_all()

        return dialog

    def filter_remove_packages(self, string):
        pkgs_list = [pkg.strip('-') for pkg in string.split() if pkg.endswith('-') and pkg != '--']

        new_list = []
        for pkg in pkgs_list:
            if PackageInfo(pkg).check_installed():
                new_list.append(pkg)

        return new_list

    def on_action_clicked(self, cell, path):
        iter = self.model.get_iter_from_string(path)
        installed = self.model.get_value(iter, self.COLUMN_ACTION)
        task = self.model.get_value(iter, self.COLUMN_TASK)
        name = self.model.get_value(iter, self.COLUMN_NAME)

        self.set_busy()
        updateview = UpdateView()
        updateview.set_headers_visible(False)

        if installed == 'Installed':
            dialog = InfoDialog(_('You\'ve installed the <b>"%s"</b> task.' % name))
            dialog.add_button(_('Remove'), gtk.RESPONSE_YES)
            res = dialog.run()
            dialog.destroy()
            if res == gtk.RESPONSE_YES:
                dialog = WarningDialog(_('It is dangerous to remove a task, it may remove the desktop related packages.\nPlease only continue when you know what you are doing.'),
                         title=_("Dangerous!"))
                res = dialog.run()
                dialog.destroy()

                if res == gtk.RESPONSE_YES:
                    data = os.popen('tasksel -t remove %s' % task).read()
                    pkgs = self.filter_remove_packages(data)
                    updateview.update_updates(pkgs)
                    updateview.select_all_action(True)

                    dialog = self.create_task_dialog(title=_('Packages will be removed'),
                            desc = _('You are going to remove the <b>"%s"</b> task.\nThe following packages will be remove.' % name),
                            updateview=updateview)

                    res = dialog.run()
                    dialog.destroy()

                    if res == gtk.RESPONSE_YES:
                        PACKAGE_WORKER.perform_action(self.get_toplevel(), [], updateview.to_add)
                        PACKAGE_WORKER.update_apt_cache(True)
                        self.update_model()
        else:
            list = os.popen('tasksel --task-packages %s' % task).read().split('\n')
            list = [pkg for pkg in list if pkg.strip() and not PackageInfo(pkg).check_installed()]

            updateview.update_updates(list)
            updateview.select_all_action(True)

            dialog = self.create_task_dialog(title=_('New packages will be installed'),
                    desc = _('You are going to install the <b>"%s"</b> task.\nThe following packager will be installed.' % name),
                    updateview=updateview)

            res = dialog.run()
            dialog.destroy()

            if res == gtk.RESPONSE_YES:
                PACKAGE_WORKER.perform_action(self.get_toplevel(), updateview.to_add, [])
                PACKAGE_WORKER.update_apt_cache(True)
                self.update_model()

        print self.model.get_value(iter, self.COLUMN_ACTION)

        self.unset_busy()

    def update_model(self):
        self.model.clear()
        data = os.popen('tasksel --list').read().strip()

        for line in data.split('\n'):
            installed = line[0] == 'i'
            task, name = line[2:].split('\t')

            if task == 'manual':
                continue

            if installed:
                installed = _('Installed')
            else:
                installed = _('Install')

            name, desc = TASKS[task]
            iter = self.model.append()
            self.model.set(iter, 
                    self.COLUMN_ACTION, installed,
                    self.COLUMN_TASK, task,
                    self.COLUMN_NAME, name,
                    self.COLUMN_DESC, '<b>%s</b>\n%s' % (name, desc))

    def set_busy(self):
        window = self.get_toplevel().window
        if window:
            window.set_cursor(gtk.gdk.Cursor(gtk.gdk.WATCH))

    def unset_busy(self):
        window = self.get_toplevel().window
        if window:
            window.set_cursor(None)

class TaskInstall(TweakModule):
    __title__ = _('Task Install')
    __desc__ = _('Setup a full-function environment with just one-click\n'
                 'If you want to remove a task, click the "Installed" button')
    __icon__ = ['application-x-deb']
    __category__ = 'system'
    #TODO Maybe set active again
    __utactive__ = False

    def __init__(self):
        TweakModule.__init__(self)

        taskview = TaskView()

        self.add_start(taskview)

########NEW FILE########
__FILENAME__ = updatemanager
#!/usr/bin/python

# Ubuntu Tweak - PyGTK based desktop configuration tool
#
# Copyright (C) 2007-2008 TualatriX <tualatrix@gmail.com>
#
# Ubuntu Tweak is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# Ubuntu Tweak is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Ubuntu Tweak; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA

from gettext import ngettext
from aptsources.sourceslist import SourcesList

from ubuntutweak.modules  import TweakModule
from ubuntutweak.ui import GconfCheckButton
from ubuntutweak.ui.dialogs import InfoDialog
from sourcecenter import UpdateView, refresh_source, UpdateCacheDialog
from ubuntutweak.policykit import proxy

from ubuntutweak.common.package import PACKAGE_WORKER

class UpdateManager(TweakModule):
    __title__ = _('Update Manager')
    __desc__ = _('A simple and easy-to-use update manager')
    __icon__ = 'system-software-update'
    __category__ = 'application'

    def __init__(self):
        TweakModule.__init__(self, 'updatemanager.ui')

        self.updateview = UpdateView()
        self.updateview.connect('changed', self.on_update_status_changed)
        self.updateview.connect('select', self.on_select_action)
        self.update_list()
        self.sw1.add(self.updateview)

        button = GconfCheckButton(label=_('Automatically run System Update Manager'), 
                                  key='/apps/update-notifier/auto_launch')
        self.vbox1.pack_start(button, False, False, 0)

        self.ppa_button = GconfCheckButton(
                            label=_('Temporarily disable third-party PPA sources whilst refreshing'),
                            key='/apps/ubuntu-tweak/disable_ppa')
        self.vbox1.pack_start(self.ppa_button, False, False, 0)

        self.reparent(self.main_vbox)

    def update_list(self):
        PACKAGE_WORKER.update_apt_cache(init=True)
        self.updateview.get_model().clear()
        self.updateview.update_updates(list(PACKAGE_WORKER.get_update_package()))
        self.install_button.set_sensitive(False)

    def on_refresh_button_clicked(self, widget):
        do_ppa_disable = False
        if self.ppa_button.get_active():
            proxy.disable_ppa()
            do_ppa_disable = True

        UpdateCacheDialog(widget.get_toplevel()).run()

        PACKAGE_WORKER.update_apt_cache(True)

        new_updates = list(PACKAGE_WORKER.get_update_package())
        if new_updates:
            self.updateview.get_model().clear()
            self.updateview.update_updates(new_updates)
        else:
            dialog = InfoDialog(_("Your system is clean and no updates are available."),
                        title=_('Software information is now up-to-date'))

            dialog.launch()

        if do_ppa_disable:
            proxy.enable_ppa()
        self.emit('call', 'ubuntutweak.modules.sourcecenter', 'update_thirdparty', {})
        self.emit('call', 'ubuntutweak.modules.sourceeditor', 'update_source_combo', {})

    def on_select_action(self, widget, active):
        self.updateview.select_all_action(active)

    def on_update_status_changed(self, widget, count):
        self.install_button.set_label(ngettext('Install Update',
                                               'Install Updates', count))
        if count:
            self.install_button.set_sensitive(True)
        else:
            self.install_button.set_sensitive(False)

    def on_install_button_clicked(self, widget):
        PACKAGE_WORKER.perform_action(widget.get_toplevel(), self.updateview.to_add, self.updateview.to_rm)

        PACKAGE_WORKER.update_apt_cache(True)

        PACKAGE_WORKER.show_installed_status(self.updateview.to_add, self.updateview.to_rm)

        self.updateview.get_model().clear()
        self.updateview.update_updates(list(PACKAGE_WORKER.get_update_package()))
        self.updateview.select_all_action(False)

########NEW FILE########
__FILENAME__ = downloadmanager
#!/usr/bin/python
# coding: utf-8

import os
import logging
import urllib
import thread
import socket

from gi.repository import Gtk
from gi.repository import GObject

from ubuntutweak.gui.dialogs import BusyDialog
from ubuntutweak.common import consts

log = logging.getLogger('downloadmanager')
socket.setdefaulttimeout(60)

class Downloader(GObject.GObject):
    __gsignals__ = {
      'downloading': (GObject.SignalFlags.RUN_FIRST, None, (GObject.TYPE_FLOAT,)),
      'downloaded': (GObject.SignalFlags.RUN_FIRST, None, ()),
      'error': (GObject.SignalFlags.RUN_FIRST, None, ()),
    }

    tempdir = os.path.join(consts.CONFIG_ROOT, 'temp')

    def __init__(self, url=None):
        if url:
            self.url = url
        super(Downloader, self).__init__()

    def create_tempdir(self):
        if not os.path.exists(self.tempdir):
            os.makedirs(self.tempdir)
        else:
            if not os.path.isdir(self.tempdir): 
                os.remove(self.tempdir)
                os.makedirs(self.tempdir)

    def clean_tempdir(self):
        for root, dirs, files in os.walk(self.tempdir, topdown=False):
            for name in files:
                os.remove(os.path.join(root, name))
            for name in dirs:
                os.rmdir(os.path.join(root, name))

    def start(self, url=None):
        if not os.path.exists(self.tempdir) or os.path.isfile(self.tempdir):
            self.create_tempdir()
        self.clean_tempdir()

        if url:
            self.url = url

        self.save_to = os.path.join(self.tempdir, os.path.basename(self.url))
        try:
            urllib.urlretrieve(self.url, self.save_to, self.update_progress)
        except socket.timeout:
            self.emit('error')

    def update_progress(self, blocks, block_size, total_size):
        percentage = float(blocks*block_size)/total_size
        if percentage >= 0:
            if percentage < 1:
                self.emit('downloading', percentage)
            elif percentage >= 1:
                self.emit('downloaded')
        else:
            self.emit('error')

    def get_downloaded_file(self):
        return self.save_to

class DownloadDialog(BusyDialog):
    time_count = 1
    downloaded = False
    error = False

    def __init__(self, url=None, title=None, parent=None):
        BusyDialog.__init__(self, parent=parent)

        self.set_size_request(320, -1)
        self.set_title('')
        self.set_resizable(False)
        self.set_border_width(8)

        vbox = self.get_child()
        vbox.set_spacing(6)

        if title:
            label = Gtk.Label()
            label.set_alignment(0, 0.5)
            label.set_markup('<big><b>%s</b></big>' % title)
            vbox.pack_start(label, False, False, 0)

        self.wait_text = _('Connecting to server')
        self.progress_bar = Gtk.ProgressBar()
        self.progress_bar.set_text(self.wait_text)
        vbox.pack_start(self.progress_bar, True, False, 0)

        if url:
            self.url = url
            self.downloader = Downloader(url)
        else:
            self.downloader = Downloader()

        self.downloader.connect('downloading', self.on_downloading)
        self.downloader.connect('downloaded', self.on_downloaded)
        self.downloader.connect('error', self.on_error_happen)

        self.add_button(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL)
        self.show_all()

        GObject.timeout_add(1000, self.on_network_connect)

    def on_network_connect(self):
        if self.time_count != -1:
            self.progress_bar.set_text(self.wait_text+'.' * self.time_count)
            if self.time_count < 3:
                self.time_count += 1
            else:
                self.time_count = 1

            return True

    def run(self):
        thread.start_new_thread(self._download_thread, ())
        return super(DownloadDialog, self).run()

    def destroy(self):
        super(DownloadDialog, self).destroy()

    def set_url(self, url):
        self.url = url

    def on_downloading(self, widget, percentage):
        log.debug("Downloading: %s" % percentage)
        if self.time_count != -1:
            self.time_count = -1

        if percentage < 1:
            self.progress_bar.set_text(_('Downloading...%d') % int(percentage * 100)+ '%')
            self.progress_bar.set_fraction(percentage)

    def on_downloaded(self, widget):
        log.debug("Downloaded")
        self.progress_bar.set_text(_('Downloaded!'))
        self.progress_bar.set_fraction(1)
        self.response(Gtk.ResponseType.DELETE_EVENT)
        self.downloaded = True

    def on_error_happen(self, widget):
        log.debug("Error happened")
        self.progress_bar.set_text(_('Error happened!'))
        self.progress_bar.set_fraction(1)
        self.response(Gtk.ResponseType.DELETE_EVENT)
        self.downloaded = False
        self.error = True

    def _download_thread(self):
        self.downloader.start(self.url)

    def get_downloaded_file(self):
        return self.downloader.get_downloaded_file()

########NEW FILE########
__FILENAME__ = utdata
import os
import random
import urllib
import time
import datetime

from gettext import ngettext
from urlparse import urljoin

from ubuntutweak.common.consts import install_ngettext
from ubuntutweak.utils.tar import TarFile

install_ngettext()

DEV_MODE = os.getenv('UT_DEV')
DATA_MIRRORS = (
    'http://ubuntu-tweak.com/',
    'http://ubuntu-tweak.lfeng.me/'
)

if DEV_MODE == 'local':
    URL_PREFIX = 'http://127.0.0.1:8000/'
else:
    URL_PREFIX = DATA_MIRRORS[random.randint(0, len(DATA_MIRRORS)-1)]

def get_version_url(version_url):
    if DEV_MODE:
        return urljoin(URL_PREFIX, '%sdev/' % version_url)
    else:
        return urljoin(URL_PREFIX, version_url)

def get_download_url(download_url):
    return urljoin(URL_PREFIX, download_url)

def get_local_timestamp(folder):
    local_timestamp = os.path.join(folder, 'timestamp')

    if os.path.exists(local_timestamp):
        local_version = open(local_timestamp).read()
    else:
        local_version = '0'

    return local_version

def get_local_time(folder):
    timestamp = get_local_timestamp(folder)
    if timestamp > '0':
        return time.strftime('%Y-%m-%d %H:%M', time.localtime(float(timestamp)))
    else:
        return _('Never')

def save_synced_timestamp(folder):
    synced = os.path.join(folder, 'synced')
    f = open(synced, 'w')
    f.write(str(int(time.time())))
    f.close()

def get_last_synced(folder):
    try:
        timestamp = open(os.path.join(folder, 'synced')).read()
        now = time.time()

        o_delta = datetime.timedelta(seconds=float(timestamp))
        n_delta = datetime.timedelta(seconds=now)

        difference = n_delta - o_delta

        weeks, days = divmod(difference.days, 7)

        minutes, seconds = divmod(difference.seconds, 60)
        hours, minutes = divmod(minutes, 60)

        if weeks:
            return ngettext('%d week ago', '%d weeks ago', weeks) % weeks
        if days:
            return ngettext('%d day ago', '%d days ago', days) % days
        if hours:
            return ngettext('%d hour ago', '%d hours ago', hours) % hours
        if minutes:
            return ngettext('%d minute ago', '%d minutes ago', minutes) % minutes
        return _('Just Now')
    except:
        return _('Never')

def check_update_function(url, folder, update_setter, version_setter, auto):
    remote_version = urllib.urlopen(url).read()
    if remote_version.isdigit():
        local_version = get_local_timestamp(folder)

        if remote_version > local_version:
            if auto:
                update_setter.set_value(True)
            version_setter.set_value(remote_version)
            return True
        else:
            return False
    else:
        return False

def create_tarfile(path):
    return TarFile(path)

########NEW FILE########
__FILENAME__ = xmlrpc
from xmlrpclib import ServerProxy, Error

proxy = ServerProxy('http://127.0.0.1:8000/xmlrpc/')

if __name__ == '__main__':
    print proxy.user.authenticate('tualatrix','123456')
    print proxy.func.test('tualatrix','123456', 'Hello World')

########NEW FILE########
__FILENAME__ = dbusproxy
# Ubuntu Tweak - Ubuntu Configuration Tool
#
# Copyright (C) 2007-2011 Tualatrix Chou <tualatrix@gmail.com>
#
# Ubuntu Tweak is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# Ubuntu Tweak is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Ubuntu Tweak; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA

import dbus
import logging

log = logging.getLogger("DbusProxy")

SHOWED = False

def show_message(*args):
    from ubuntutweak.gui.dialogs import ErrorDialog
    message = _('The Ubuntu Tweak daemon didn\'t start correctly. This means that some '
            'advanced features may not work.\n'
            'If you want to help developers debugging, try to run "<b>sudo /usr/share/ubuntu-tweak/ubuntu-tweak-daemon</b>" in a terminal.')
    ErrorDialog(message=message).launch()

def nothing(*args):
    return None

class DbusProxy:
    INTERFACE = "com.ubuntu_tweak.daemon"

    try:
        __system_bus = dbus.SystemBus()
        __object = __system_bus.get_object('com.ubuntu_tweak.daemon', '/com/ubuntu_tweak/daemon')
    except Exception, e:
        log.error(e)
        __object = None

    def __getattr__(self, name):
        global SHOWED
        try:
            return self.__object.get_dbus_method(name, dbus_interface=self.INTERFACE)
        except Exception, e:
            log.error(e)
            if not SHOWED:
                SHOWED = True
                return show_message
            else:
                return nothing

    def get_object(self):
        return self.__object

proxy = DbusProxy()

if __name__ == '__main__':
    print proxy

########NEW FILE########
__FILENAME__ = widgets
# Ubuntu Tweak - Ubuntu Configuration Tool
#
# Copyright (C) 2007-2011 Tualatrix Chou <tualatrix@gmail.com>
#
# Ubuntu Tweak is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# Ubuntu Tweak is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Ubuntu Tweak; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA

import dbus

from gi.repository import GObject, Gtk, Gio
from ubuntutweak.gui.gtk import set_busy, unset_busy

from aptdaemon import policykit1
from defer import inline_callbacks

class PolkitAction(GObject.GObject):
    """
    PolicyKit action, if changed return 0, means authenticate failed, 
    return 1, means authenticate successfully
    """

    def __init__(self, action):
        GObject.GObject.__init__(self)

        self.action = action

    @inline_callbacks
    def do_authenticate(self):
        bus = dbus.SystemBus()
        name = bus.get_unique_name()
        flags = policykit1.CHECK_AUTH_ALLOW_USER_INTERACTION

        yield policykit1.check_authorization_by_name(name, self.action, flags=flags)


class PolkitButton(Gtk.Button):
    __gsignals__ = {
        'authenticated': (GObject.SignalFlags.RUN_FIRST, None, ()),
    }

    def __init__(self, action):
        GObject.GObject.__init__(self)
        self.icon_unlock = ('changes-allow-symbolic', 'changes-allow')
        self.icon_lock = ('changes-prevent-symbolic', 'changes-prevent')

        self.hbox = Gtk.HBox(spacing=6)
        self.add(self.hbox)

        self.image = Gtk.Image.new_from_gicon(Gio.ThemedIcon.new_from_names(self.icon_lock),
                                         Gtk.IconSize.BUTTON)
        self.hbox.pack_start(self.image, False, False, 0)

        self.label = Gtk.Label(_('_Unlock'))
        self.label.set_use_underline(True)
        self.hbox.pack_start(self.label, False, False, 0)

        self._action = PolkitAction(action)
        self.connect('clicked', self.on_button_clicked)

        self.show_all()

    @inline_callbacks
    def on_button_clicked(self, widget):
        set_busy(widget.get_toplevel())
        try:
            yield self._action.do_authenticate()
        except Exception, e:
            import logging
            logging.getLogger('PolkitButton').debug(e)
            unset_busy(widget.get_toplevel())
            return

        self.emit('authenticated')
        self._change_button_state()
        unset_busy(widget.get_toplevel())

    def _change_button_state(self):
        self.image.set_from_gicon(Gio.ThemedIcon.new_from_names(self.icon_unlock), Gtk.IconSize.BUTTON)

        self.set_sensitive(False)

########NEW FILE########
__FILENAME__ = preferences
# Ubuntu Tweak - Ubuntu Configuration Tool
#
# Copyright (C) 2007-2011 Tualatrix Chou <tualatrix@gmail.com>
#
# Ubuntu Tweak is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# Ubuntu Tweak is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Ubuntu Tweak; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA

import os
import shutil
import logging
from gi.repository import Gtk, GLib

from ubuntutweak.gui import GuiBuilder
from ubuntutweak.modules import ModuleLoader, TweakModule
from ubuntutweak.janitor import JanitorPlugin
from ubuntutweak.settings import GSetting
from ubuntutweak.clips import Clip
from ubuntutweak.gui.dialogs import ErrorDialog, QuestionDialog
from ubuntutweak.utils.tar import TarFile
from ubuntutweak.common.consts import TEMP_ROOT
from ubuntutweak.factory import WidgetFactory
from ubuntutweak.gui.containers import GridPack


log = logging.getLogger('PreferencesDialog')


class PreferencesDialog(GuiBuilder):
    (CLIP_CHECK,
     CLIP_ICON,
     CLIP_NAME) = range(3)

    (TWEAKS_CHECK,
     TWEAKS_ICON,
     TWEAKS_NAME) = range(3)

    (JANITOR_CHECK,
     JANITOR_NAME) = range(2)

    page_dict = {'overview': 0,
                 'tweaks': 1,
                 'admins': 2,
                 'janitor': 3}

    def __init__(self, parent):
        GuiBuilder.__init__(self, file_name='preferences.ui')

        self.preferences_dialog.set_transient_for(parent)
        self.clips_setting = GSetting('com.ubuntu-tweak.tweak.clips')
        self.tweaks_setting = GSetting('com.ubuntu-tweak.tweak.tweaks')
        self.admins_setting = GSetting('com.ubuntu-tweak.tweak.admins')
        self.janitor_setting = GSetting('com.ubuntu-tweak.janitor.plugins')
        self.clips_location_setting = GSetting('com.ubuntu-tweak.tweak.last-clip-location')
        
        auto_scan_label, auto_scan_switch = WidgetFactory.create("Switch",
                                                label=_("Auto scan:"),
                                                key='com.ubuntu-tweak.janitor.auto-scan',
                                                backend="gsettings")
        pack = GridPack((auto_scan_label, auto_scan_switch))
        self.generic_alignment.add(pack)

        self.generic_alignment.show_all()

    def on_clip_toggle_render_toggled(self, cell, path):
        log.debug("on_clip_toggle_render_toggled")
        self.on_toggle_renderer_toggled(self.clip_model,
                                        path,
                                        self.CLIP_CHECK,
                                        self.CLIP_NAME,
                                        self.clips_setting)

    def on_tweak_toggle_renderer_toggled(self, cell, path):
        log.debug("on_tweaks_toggle_render_toggled")
        self.on_toggle_renderer_toggled(self.tweaks_model,
                                        path,
                                        self.TWEAKS_CHECK,
                                        self.TWEAKS_NAME,
                                        self.tweaks_setting)

    def on_admins_toggle_renderer_toggled(self, cell, path):
        log.debug("on_admins_toggle_render_toggled")
        self.on_toggle_renderer_toggled(self.admins_model,
                                        path,
                                        self.TWEAKS_CHECK,
                                        self.TWEAKS_NAME,
                                        self.admins_setting)

    def on_janitor_cell_renderer_toggled(self, cell, path):
        log.debug("on_admins_toggle_render_toggled")
        self.on_toggle_renderer_toggled(self.janitor_model,
                                        path,
                                        self.JANITOR_CHECK,
                                        self.JANITOR_NAME,
                                        self.janitor_setting)

    def on_toggle_renderer_toggled(self, model, path, check_id, name_id, setting):
        iter = model.get_iter(path)
        checked = not model[iter][check_id]
        model[iter][check_id] = checked

        self._do_update_model(model, check_id, name_id, setting)

    def _do_update_model(self, model, check_id, name_id, setting):
        model_list = []
        for row in model:
            if row[check_id]:
                model_list.append(row[name_id])

        log.debug("on_clip_toggle_render_toggled: %s" % model_list)
        setting.set_value(model_list)

    def run(self, feature='overview'):
        self._update_clip_model()

        for _feature in ModuleLoader.default_features:
            self._update_feature_model(_feature)

        if feature in self.page_dict:
            self.preference_notebook.set_current_page(self.page_dict[feature])

        return self.preferences_dialog.run()

    def hide(self):
        return self.preferences_dialog.hide()

    def on_move_up_button_clicked(self, widget):
        model, iter = self.clip_view.get_selection().get_selected()

        if iter:
            previous_path = str(int(model.get_string_from_iter(iter)) - 1)

            if int(previous_path) >= 0:
                previous_iter = model.get_iter_from_string(previous_path)
                model.move_before(iter, previous_iter)
                self._do_update_model(self.clip_model,
                                      self.CLIP_CHECK,
                                      self.CLIP_NAME,
                                      self.clips_setting)

    def on_move_down_button_clicked(self, widget):
        model, iter = self.clip_view.get_selection().get_selected()

        if iter:
            next_iter = model.iter_next(iter)
            model.move_after(iter, next_iter)
            self._do_update_model(self.clip_model,
                                  self.CLIP_CHECK,
                                  self.CLIP_NAME,
                                  self.clips_setting)

    def on_clip_install_button_clicked(self, widget):
        self.on_install_extension(_('Choose a clip extension'),
                                  Clip,
                                  'clips',
                                  self.clips_setting,
                                  self._update_clip_model,
                                  _('"%s" is not a Clip Extension!'))

    def on_tweaks_install_button_clicked(self, widget):
        self.on_install_extension(_('Choose a Tweaks Extension'),
                                  TweakModule,
                                  'tweaks',
                                  self.tweaks_setting,
                                  self._update_feature_model,
                                  _('"%s" is not a Tweaks Extension!'))

    def on_admins_install_button_clicked(self, widget):
        self.on_install_extension(_('Choose a Admins Extension'),
                                  TweakModule,
                                  'admins',
                                  self.admins_setting,
                                  self._update_feature_model,
                                  _('"%s" is not a Admins Extension!'))

    def on_janitor_install_button_clicked(self, widget):
        self.on_install_extension(_('Choose a Janitor Extension'),
                                  JanitorPlugin,
                                  'janitor',
                                  self.janitor_setting,
                                  self._update_feature_model,
                                  _('"%s" is not a Janitor Extension!'))

    def on_install_extension(self, dialog_label, klass, feature,
                             setting, update_func, error_message):
        dialog = Gtk.FileChooserDialog(dialog_label,
                                       action=Gtk.FileChooserAction.OPEN,
                                       buttons=(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
                                                Gtk.STOCK_OPEN, Gtk.ResponseType.ACCEPT))
        filter = Gtk.FileFilter()
        filter.set_name(_('Ubuntu Tweak Extension (*.py, *.tar.gz)'))
        filter.add_pattern('*.py')
        filter.add_pattern('*.tar.gz')
        dialog.add_filter(filter)
        dialog.set_current_folder(self.clips_location_setting.get_value() or
                                  GLib.get_home_dir())

        filename = ''
        install_done = False
        not_extension = False

        if dialog.run() == Gtk.ResponseType.ACCEPT:
            filename = dialog.get_filename()
        dialog.destroy()

        if filename:
            self.clips_location_setting.set_value(os.path.dirname(filename))

            log.debug("Start to check the class in %s" % filename)
            if filename.endswith('.tar.gz'):
                tar_file = TarFile(filename)
                if tar_file.is_valid():
                    tar_file.extract(TEMP_ROOT)
                    #TODO if multi-root
                    if tar_file.get_root_name():
                        temp_dir = os.path.join(TEMP_ROOT, tar_file.get_root_name())

                if ModuleLoader.is_target_class(temp_dir, klass):
                    target = os.path.join(ModuleLoader.get_user_extension_dir(feature), os.path.basename(temp_dir))
                    copy = True
                    if os.path.exists(target):
                        dialog = QuestionDialog(message=_("Would you like to remove it then install again?"),
                                                title=_('"%s" has already installed' % os.path.basename(target)))
                        response = dialog.run()
                        dialog.destroy()

                        if response == Gtk.ResponseType.YES:
                            shutil.rmtree(target)
                        else:
                            copy = False

                    if copy:
                        log.debug("Now copying tree...")
                        shutil.move(temp_dir, target)
                    else:
                        shutil.rmtree(temp_dir)
                else:
                    not_extension = True
            else:
                if ModuleLoader.is_target_class(filename, klass):
                    shutil.copy(filename, ModuleLoader.get_user_extension_dir(feature))
                    install_done = True
                else:
                    not_extension = True

        if install_done:
            update_func(feature)

            # To force empty the clips_setting to make load_cips
            value = setting.get_value()
            setting.set_value([''])
            setting.set_value(value)

        if not_extension:
            ErrorDialog(message=error_message % os.path.basename(filename)).launch()

    def _update_clip_model(self, feature=None):
        clips = self.clips_setting.get_value()

        loader = ModuleLoader('clips')

        self.clip_model.clear()

        for clip_name in clips:
            ClipClass = loader.get_module(clip_name)

            self.clip_model.append((True,
                                    ClipClass.get_pixbuf(),
                                    ClipClass.get_name()))

        for name, ClipClass in loader.module_table.items():
            if name not in clips:
                self.clip_model.append((False,
                                        ClipClass.get_pixbuf(),
                                        ClipClass.get_name()))

    def _update_feature_model(self, feature):
        module_list = getattr(self, '%s_setting' % feature).get_value() or []

        loader = ModuleLoader(feature, user_only=True)

        model = getattr(self, '%s_model' % feature)
        model.clear()

        for name, klass in loader.module_table.items():
            if klass.get_pixbuf():
                model.append((name in module_list,
                              klass.get_pixbuf(),
                              klass.get_name()))
            else:
                model.append((name in module_list,
                              klass.get_name()))

########NEW FILE########
__FILENAME__ = run_test
#!/usr/bin/python

# Ubuntu Tweak - PyGTK based desktop configuration tool
#
# Copyright (C) 2007-2008 TualatriX <tualatrix@gmail.com>
#
# Ubuntu Tweak is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# Ubuntu Tweak is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Ubuntu Tweak; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA

import os
import sys
import inspect
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from gi.repository import Gtk, Gdk

from ubuntutweak.common.debug import enable_debugging

class Test:
    def __init__(self, model):
        win = Gtk.Window()
        win.connect('destroy', lambda *w: Gtk.main_quit())
        win.set_position(Gtk.WindowPosition.CENTER)
        win.set_default_size(640, 400)

        if getattr(model, "__name__", None):
            win.set_title(model.__name__)
        else:
            win.set_title(str(model))

        if callable(model):
            win.add(model())
        else:
            win.add(model)
        win.show_all()

        Gtk.main()

class ManyTest:
    def __init__(self, widgets):
        win = Gtk.Window()

        win.connect('destroy', lambda *w: Gtk.main_quit())
        win.set_position(Gtk.WindowPosition.CENTER)

        win.set_title("Many test")
        
        vbox = Gtk.VBox(False, 10)
        win.add(vbox)

        for widget in widgets:
            vbox.pack_start(widget, False, False, 5)

        win.show_all()

        Gtk.main()

if __name__ == '__main__':
    enable_debugging()

    module = os.path.splitext(os.path.basename(sys.argv[1]))[0]
    folder = os.path.dirname(sys.argv[1])
    package = __import__('.'.join([folder, module]))

    for k, v in inspect.getmembers(getattr(package, module)):
        if k not in ('TweakModule', 'proxy') and hasattr(v, '__utmodule__'):
            module = v
            Test(module)

########NEW FILE########
__FILENAME__ = Conflicts
# -*- coding: UTF-8 -*-

# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful, 
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.
#
# Authors: Quinn Storm (quinn@beryl-project.org)
#          Patrick Niklaus (marex@opencompositing.org)
#          Guillaume Seguin (guillaume@segu.in)
#          Christopher Williams (christopherw@verizon.net)
# Copyright (C) 2007 Quinn Storm

from gi.repository import Gtk

from Constants import *
from Utils import *

import locale
import gettext
locale.setlocale(locale.LC_ALL, "")
gettext.bindtextdomain("ccsm", DataDir + "/locale")
gettext.textdomain("ccsm")
_ = gettext.gettext

class Conflict:
    def __init__(self, autoResolve):
        self.AutoResolve = autoResolve

    # buttons = (text, type/icon, response_id)
    def Ask(self, message, buttons, custom_widgets=None):
        if self.AutoResolve:
            return Gtk.ResponseType.YES

        dialog = Gtk.MessageDialog(flags=Gtk.DialogFlags.MODAL, type=Gtk.MessageType.WARNING)

        for text, icon, response in buttons:
            button = Gtk.Button(text)
            button.set_image(Gtk.Image.new_from_stock(icon, Gtk.IconSize.BUTTON))
            dialog.add_action_widget(button, response)

        if custom_widgets != None:
            for widget in custom_widgets:
                dialog.vbox.pack_start(widget, False, False)

        dialog.set_markup(message)
        dialog.show_all()
        answer = dialog.run()
        dialog.destroy()

        return answer

class ActionConflict (Conflict):

    ActionTypes = set(('Bell', 'Button', 'Edge', 'Key'))

    def __init__ (self, setting, settings, autoResolve):

        def ExcludeInternal (settings):
            for setting in settings:
                if not setting.Info[0]:
                    yield setting

        Conflict.__init__(self, autoResolve)
        self.Conflicts = []
        self.Name = ""
        self.Setting = setting

        if settings is None:
            settings = []

        self.Settings = settings

        # if the action is internal, include all global actions plus internal
        # actions from the same plugin. If it is global, include all actions.

        if not settings:
            for n in self.Setting.Plugin.Context.Plugins:
                plugin = self.Setting.Plugin.Context.Plugins[n]
                if plugin.Enabled:
                    pluginActions = GetSettings(plugin, types=self.ActionTypes)

                    if len(setting.Info) and setting.Info[0] and plugin is not setting.Plugin:
                        settings.extend(ExcludeInternal(pluginActions))
                    else:
                        settings.extend(pluginActions)

    def Resolve (self, updater = None):
        if len (self.Conflicts):
            for setting in self.Conflicts:
                answer = self.AskUser (self.Setting, setting)
                if answer == Gtk.ResponseType.YES:
                    setting.Value = 'Disabled'
                    if updater:
                        updater.UpdateSetting (setting)
                if answer == Gtk.ResponseType.NO:
                    return False

        return True

    def AskUser (self, setting, conflict):
        msg = _("The new value for the %(binding)s binding for the action <b>%(action)s</b> "\
              "in plugin <b>%(plugin)s</b> conflicts with the action <b>%(action_conflict)s</b> of the <b>%(plugin_conflict)s</b> plugin.\n"\
              "Do you wish to disable <b>%(action_conflict)s</b> in the <b>%(plugin_conflict)s</b> plugin?")

        msg_dict = {'binding': self.Name,
                    'action': setting.ShortDesc,
                    'plugin': setting.Plugin.ShortDesc,
                    'action_conflict': conflict.ShortDesc,
                    'plugin_conflict': conflict.Plugin.ShortDesc}

        msg = msg % protect_markup_dict (msg_dict)

        yesButton    = (_("Disable %(action_conflict)s") % msg_dict,  Gtk.STOCK_YES,  Gtk.ResponseType.YES)
        noButton     = (_("Don't set %(action)s") %  msg_dict,    Gtk.STOCK_NO,   Gtk.ResponseType.NO)
        ignoreButton = (_("Set %(action)s anyway") % msg_dict,    Gtk.STOCK_STOP, Gtk.ResponseType.REJECT)

        return self.Ask (msg, (ignoreButton, noButton, yesButton))

class KeyConflict(ActionConflict):
    def __init__(self, setting, newValue, settings=None, autoResolve=False, ignoreOld=False):
        ActionConflict.__init__(self, setting, settings, autoResolve)
        self.Name = _("key")

        if not newValue:
            return

        newValue = newValue.lower ()
        oldValue = self.Setting.Value.lower ()
        badValues = ["disabled", "none"]
        if not ignoreOld:
            badValues.append (oldValue)
        if newValue in badValues:
            return

        for s in self.Settings:
            if s is setting:
                continue
            if s.Type == 'Key':
                if s.Value.lower() == newValue:
                    self.Conflicts.append (s)

class ButtonConflict(ActionConflict):
    def __init__(self, setting, newValue, settings=None, autoResolve=False, ignoreOld=False):
        ActionConflict.__init__(self, setting, settings, autoResolve)
        self.Name = _("button")

        if not newValue:
            return

        newValue = newValue.lower ()
        oldValue = self.Setting.Value.lower ()
        badValues = ["disabled", "none"]
        if not ignoreOld:
            badValues.append (oldValue)
        if newValue in badValues:
            return

        for s in self.Settings:
            if s is setting:
                continue
            if s.Type == 'Button':
                if s.Value.lower() == newValue:
                    self.Conflicts.append (s)

class EdgeConflict(ActionConflict):
    def __init__(self, setting, newValue, settings=None, autoResolve=False, ignoreOld=False):
        ActionConflict.__init__(self, setting, settings, autoResolve)
        self.Name = _("edge")

        if not newValue:
            return

        newEdges = set(newValue.split("|"))

        if not ignoreOld:
            oldEdges = set(self.Setting.Value.split("|"))
            diff = newEdges - oldEdges
            if diff:
               newEdges = diff # no need to check edges that were already set
            else:
                return

        for s in self.Settings:
            if s is setting:
                continue
            elif s.Type == 'Edge':
                settingEdges = set(s.Value.split("|"))
                union = newEdges & settingEdges
                if union:
                    for edge in union:
                        self.Conflicts.append ((s, edge))
                        break

    def Resolve (self, updater = None):
        if len (self.Conflicts):
            for setting, edge in self.Conflicts:
                answer = self.AskUser (self.Setting, setting)
                if answer == Gtk.ResponseType.YES:
                    value = setting.Value.split ("|")
                    value.remove (edge)
                    setting.Value = "|".join (value)
                    if updater:
                        updater.UpdateSetting (setting)
                if answer == Gtk.ResponseType.NO:
                    return False

        return True

# Not used for plugin dependencies (which are handled by ccs) but own feature checking e.g. image support
class FeatureRequirement(Conflict):
    def __init__(self, context, feature, autoResolve=False):
        Conflict.__init__(self, autoResolve)
        self.Requirements = []
        self.Context = context
        self.Feature = feature

        self.Found = False
        for plugin in context.Plugins.values():
            if feature in plugin.Features:
                self.Found = True
                if not plugin.Enabled:
                    self.Requirements.append(plugin)
    
    def Resolve(self):
        if len(self.Requirements) == 0 and self.Found:
            return True
        elif not self.Found:
            answer = self.ErrorAskUser()
            if answer == Gtk.ResponseType.YES:
                return True
            else:
                return False
        
        for plugin in self.Requirements:
            answer = self.AskUser(plugin)
            if answer == Gtk.ResponseType.YES:
                plugin.Enabled = True
                self.Context.Write()
                return True

    def ErrorAskUser(self):
        msg = _("You are trying to use the feature <b>%(feature)s</b> which is <b>not</b> provided by any plugin.\n"\
                "Do you wish to use this feature anyway?")

        msg_dict = {'feature': self.Feature}

        msg = msg % protect_markup_dict (msg_dict)

        yesButton = (_("Use %(feature)s") % msg_dict,       Gtk.STOCK_YES, Gtk.ResponseType.YES)
        noButton  = (_("Don't use %(feature)s") % msg_dict, Gtk.STOCK_NO,  Gtk.ResponseType.NO)

        answer = self.Ask(msg, (noButton, yesButton))

        return answer

    def AskUser(self, plugin):
        msg = _("You are trying to use the feature <b>%(feature)s</b> which is provided by <b>%(plugin)s</b>.\n"\
                "This plugin is currently disabled.\n"\
                "Do you wish to enable <b>%(plugin)s</b> so the feature is available?")

        msg_dict = {'feature': self.Feature,
                    'plugin': plugin.ShortDesc}

        msg = msg % protect_markup_dict (msg_dict)

        yesButton = (_("Enable %(plugin)s") % msg_dict,       Gtk.STOCK_YES, Gtk.ResponseType.YES)
        noButton  = (_("Don't enable %(feature)s") % msg_dict, Gtk.STOCK_NO,  Gtk.ResponseType.NO)

        answer = self.Ask(msg, (noButton, yesButton))

        return answer

class PluginConflict(Conflict):
    def __init__(self, plugin, conflicts, autoResolve=False):
        Conflict.__init__(self, autoResolve)
        self.Conflicts = conflicts
        self.Plugin = plugin

    def Resolve(self):
        for conflict in self.Conflicts:
            if conflict[0] == 'ConflictFeature':
                answer = self.AskUser(self.Plugin, conflict)
                if answer == Gtk.ResponseType.YES:
                    disableConflicts = conflict[2][0].DisableConflicts
                    con = PluginConflict(conflict[2][0], disableConflicts,
                                         self.AutoResolve)
                    if con.Resolve():
                        conflict[2][0].Enabled = False
                    else:
                        return False
                else:
                    return False

            elif conflict[0] == 'ConflictPlugin':
                answer = self.AskUser(self.Plugin, conflict)
                if answer == Gtk.ResponseType.YES:
                    disableConflicts = conflict[2][0].DisableConflicts
                    con = PluginConflict(conflict[2][0], disableConflicts,
                                         self.AutoResolve)
                    if con.Resolve():
                        conflict[2][0].Enabled = False
                    else:
                        return False
                else:
                    return False
            
            elif conflict[0] == 'RequiresFeature':
                answer, choice = self.AskUser(self.Plugin, conflict)
                if answer == Gtk.ResponseType.YES:
                    for plg in conflict[2]:
                        if plg.ShortDesc == choice:
                            enableConflicts = plg.EnableConflicts
                            con = PluginConflict(plg, enableConflicts,
                                                 self.AutoResolve)
                            if con.Resolve():
                                plg.Enabled = True
                            else:
                                return False
                            break
                else:
                    return False

            elif conflict[0] == 'RequiresPlugin':
                answer = self.AskUser(self.Plugin, conflict)
                if answer == Gtk.ResponseType.YES:
                    enableConflicts = conflict[2][0].EnableConflicts
                    con = PluginConflict(conflict[2][0], enableConflicts,
                                         self.AutoResolve)
                    if con.Resolve():
                        conflict[2][0].Enabled = True
                    else:
                        return False
                else:
                    return False

            elif conflict[0] == 'FeatureNeeded':
                answer = self.AskUser(self.Plugin, conflict)
                if answer == Gtk.ResponseType.YES:
                    for plg in conflict[2]:
                        disableConflicts = plg.DisableConflicts
                        con = PluginConflict(plg, disableConflicts,
                                             self.AutoResolve)
                        if con.Resolve():
                            plg.Enabled = False
                        else:
                            return False
                else:
                    return False

            elif conflict[0] == 'PluginNeeded':
                answer = self.AskUser(self.Plugin, conflict)
                if answer == Gtk.ResponseType.YES:
                    for plg in conflict[2]:
                        disableConflicts = plg.DisableConflicts
                        con = PluginConflict(plg, disableConflicts,
                                             self.AutoResolve)
                        if con.Resolve():
                            plg.Enabled = False
                        else:
                            return False
                else:
                    return False

        # Only when enabling a plugin
        types = []
        actionConflicts = []
        if not self.Plugin.Enabled and not self.AutoResolve:
            for setting in GetSettings(self.Plugin):
                conflict = None
                if setting.Type == 'Key':
                    conflict = KeyConflict(setting, setting.Value, ignoreOld=True)
                elif setting.Type == 'Button':
                    conflict = ButtonConflict(setting, setting.Value, ignoreOld=True)
                elif setting.Type == 'Edge':
                    conflict = EdgeConflict(setting, setting.Value, ignoreOld=True)

                # Conflicts were found
                if conflict and conflict.Conflicts:
                    name = conflict.Name
                    if name not in types:
                        types.append(name)
                    actionConflicts.append(conflict)

        if actionConflicts:
            answer = self.AskUser(self.Plugin, ('ConflictAction', types))
            if answer == Gtk.ResponseType.YES:
                for conflict in actionConflicts:
                    conflict.Resolve()

        return True

    def AskUser(self, plugin, conflict):
        msg = ""
        okMsg = ""
        cancelMsg = ""
        widgets = []

        # CCSM custom conflict
        if conflict[0] == 'ConflictAction':
            msg = _("Some %(bindings)s bindings of Plugin <b>%(plugin)s</b> " \
					"conflict with other plugins. Do you want to resolve " \
					"these conflicts?")

            types = conflict[1]
            bindings = ", ".join(types[:-1])
            if len(types) > 1:
                bindings = "%s and %s" % (bindings, types[-1])

            msg_dict = {'plugin': plugin.ShortDesc,
                        'bindings': bindings}

            msg = msg % protect_markup_dict (msg_dict)

            okMsg     = _("Resolve conflicts") % msg_dict
            cancelMsg = _("Ignore conflicts") % msg_dict

        elif conflict[0] == 'ConflictFeature':
            msg = _("Plugin <b>%(plugin_conflict)s</b> provides feature " \
					"<b>%(feature)s</b> which is also provided by " \
					"<b>%(plugin)s</b>")
            
            msg_dict = {'plugin_conflict': conflict[2][0].ShortDesc,
                        'feature': conflict[1],
                        'plugin': plugin.ShortDesc}

            msg = msg % protect_markup_dict (msg_dict)

            okMsg     = _("Disable %(plugin_conflict)s") % msg_dict
            cancelMsg = _("Don't enable %(plugin)s") % msg_dict
        
        elif conflict[0] == 'ConflictPlugin':
            msg = _("Plugin <b>%(plugin_conflict)s</b> conflicts with " \
					"<b>%(plugin)s</b>.")
            msg = msg % protect_markup_dict (msg_dict)

            okMsg = _("Disable %(plugin_conflict)s") % msg_dict
            cancelMsg = _("Don't enable %(plugin)s") % msg_dict
        
        elif conflict[0] == 'RequiresFeature':
            pluginList = ', '.join("\"%s\"" % plugin.ShortDesc for plugin in conflict[2])
            msg = _("<b>%(plugin)s</b> requires feature <b>%(feature)s</b> " \
					"which is provided by the following " \
					"plugins:\n%(plugin_list)s")
            
            msg_dict = {'plugin': plugin.ShortDesc,
                        'feature': conflict[1],
                        'plugin_list': pluginList}

            msg = msg % protect_markup_dict (msg_dict)

            cmb = Gtk.ComboBoxText()
            for plugin in conflict[2]:
                cmb.append_text(plugin.ShortDesc)
            cmb.set_active(0)
            widgets.append(cmb)

            okMsg = _("Enable these plugins")
            cancelMsg = _("Don't enable %(plugin)s") % msg_dict
        
        elif conflict[0] == 'RequiresPlugin':
            msg = _("<b>%(plugin)s</b> requires the plugin <b>%(require)s</b>.")

            msg_dict = {'plugin': plugin.ShortDesc,
                        'require': conflict[2][0].ShortDesc}

            msg = msg % protect_markup_dict (msg_dict)

            okMsg = _("Enable %(require)s") % msg_dict
            cancelMsg = _("Don't enable %(plugin)s") % msg_dict
        
        elif conflict[0] == 'FeatureNeeded':
            pluginList = ', '.join("\"%s\"" % plugin.ShortDesc for plugin in conflict[2])
            msg = _("<b>%(plugin)s</b> provides the feature " \
					"<b>%(feature)s</b> which is required by the plugins " \
					"<b>%(plugin_list)s</b>.")
            
            msg_dict = {'plugin': plugin.ShortDesc,
                        'feature': conflict[1],
                        'plugin_list': pluginList}
            
            msg = msg % protect_markup_dict (msg_dict)

            okMsg = _("Disable these plugins")
            cancelMsg = _("Don't disable %(plugin)s") % msg_dict
        
        elif conflict[0] == 'PluginNeeded':
            pluginList = ', '.join("\"%s\"" % plugin.ShortDesc for plugin in conflict[2])
            msg = _("<b>%(plugin)s</b> is required by the plugins " \
					"<b>%(plugin_list)s</b>.")
            
            msg_dict = {'plugin': plugin.ShortDesc,
                        'plugin_list': pluginList}
            
            msg = msg % protect_markup_dict (msg_dict)

            okMsg = _("Disable these plugins")
            cancelMsg = _("Don't disable %(plugin)s") % msg_dict

        okButton     = (okMsg,     Gtk.STOCK_OK,     Gtk.ResponseType.YES)
        cancelButton = (cancelMsg, Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL)
        
        answer = self.Ask(msg, (cancelButton, okButton), widgets)
        if conflict[0] == 'RequiresFeature':
            choice = widgets[0].get_active_text()
            return answer, choice
        
        return answer
        e

########NEW FILE########
__FILENAME__ = Constants
# -*- coding: UTF-8 -*-

# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful, 
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.
#
# Authors: Quinn Storm (quinn@beryl-project.org)
#          Patrick Niklaus (marex@opencompositing.org)
#          Guillaume Seguin (guillaume@segu.in)
#          Christopher Williams (christopherw@verizon.net)
# Copyright (C) 2007 Quinn Storm

from gi.repository import Gtk, Gdk

# Current Screen
#
CurrentScreenNum = Gdk.Display.get_default().get_n_screens()

# Settings Table
#
TableDef = Gtk.AttachOptions.FILL | Gtk.AttachOptions.EXPAND
TableX   = 4
TableY   = 2

# Action Constants
#
KeyModifier = ["Shift", "Control", "Mod1", "Mod2", "Mod3", "Mod4",
               "Mod5", "Alt", "Meta", "Super", "Hyper", "ModeSwitch"]
Edges       = ["Left", "Right", "Top", "Bottom",
               "TopLeft", "TopRight", "BottomLeft", "BottomRight"]

# Label Styles
#
HeaderMarkup = "<span size='large' weight='800'>%s</span>"

# Image Types
#
ImageNone     = 0
ImagePlugin   = 1
ImageCategory = 2
ImageThemed   = 3
ImageStock    = 4

# Filter Levels
#
FilterName = 1 << 0
FilterLongDesc = 1 << 1
FilterValue = 1 << 2    # Settings Only
FilterCategory = 1 << 3 # Plugins Only
FilterAll = FilterName | FilterLongDesc | FilterValue | FilterCategory

# Paths
#
DataDir = "/usr/share"
IconDir = DataDir+"/ccsm/icons"
PixmapDir = DataDir+"/ccsm/images"

# Version
#
Version = "0.9.4"


# Translation
#
import locale
import gettext
locale.setlocale(locale.LC_ALL, "")
gettext.bindtextdomain("ccsm", DataDir + "/locale")
gettext.textdomain("ccsm")
_ = gettext.gettext

# Category Transaltion Table
# Just to get them into gettext
#
CategoryTranslation = {
"General": _("General"),
"Accessibility": _("Accessibility"),
"Desktop": _("Desktop"),
"Extras": _("Extras"),
"Window Management": _("Window Management"),
"Effects": _("Effects"),
"Image Loading": _("Image Loading"),
"Utility": _("Utility"),
"All": _("All"),
"Uncategorized": _("Uncategorized")
}

########NEW FILE########
__FILENAME__ = Utils
# -*- coding: UTF-8 -*-

# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful, 
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.
#
# Authors: Quinn Storm (quinn@beryl-project.org)
#          Patrick Niklaus (marex@opencompositing.org)
#          Guillaume Seguin (guillaume@segu.in)
#          Christopher Williams (christopherw@verizon.net)
# Copyright (C) 2007 Quinn Storm

import os
import weakref

from gi.repository import GObject, Gtk, Gdk, Pango

from Constants import *
from cgi import escape as protect_pango_markup
import operator
import itertools

import locale
import gettext
locale.setlocale(locale.LC_ALL, "")
gettext.bindtextdomain("ccsm", DataDir + "/locale")
gettext.textdomain("ccsm")
_ = gettext.gettext

IconTheme = Gtk.IconTheme.get_default()
#TODO
#if not IconDir in IconTheme.get_search_path():
#    IconTheme.prepend_search_path(IconDir)

def gtk_process_events ():
    while Gtk.events_pending ():
        Gtk.main_iteration ()

def getScreens():
    screens = []
    display = Gdk.Display.get_default()
    nScreens = display.get_n_screens()
    for i in range(nScreens):
        screens.append(i)
    return screens

def getDefaultScreen():
    display = Gdk.Display.get_default()
    return display.get_default_screen().get_number()

def protect_markup_dict (dict_):
    return dict((k, protect_pango_markup (v)) for (k, v) in dict_.items())

class Image (Gtk.Image):

    def __init__ (self, name = None, type = ImageNone, size = 32,
                  useMissingImage = False):
        GObject.GObject.__init__ (self)

        if not name:
            return

        if useMissingImage:
            self.set_from_stock (Gtk.STOCK_MISSING_IMAGE,
                                 Gtk.IconSize.LARGE_TOOLBAR)
            return

        try:
            if type in  (ImagePlugin, ImageCategory, ImageThemed):
                pixbuf = None
                
                if type == ImagePlugin:
                    name = "plugin-" + name
                    try:
                        pixbuf = IconTheme.load_icon (name, size, 0)
                    except GObject.GError:
                        pixbuf = IconTheme.load_icon ("plugin-unknown", size, 0)
                
                elif type == ImageCategory:
                    name = "plugins-" + name
                    try:
                        pixbuf = IconTheme.load_icon (name, size, 0)
                    except GObject.GError:
                        pixbuf = IconTheme.load_icon ("plugins-unknown", size, 0)
                
                else:
                    pixbuf = IconTheme.load_icon (name, size, 0)

                self.set_from_pixbuf (pixbuf)
            
            elif type == ImageStock:
                self.set_from_stock (name, size)
        except GObject.GError as e:
            self.set_from_stock (Gtk.STOCK_MISSING_IMAGE, Gtk.IconSize.BUTTON)

class ActionImage (Gtk.Alignment):

    map = {
            "keyboard"  : "input-keyboard",
            "button"    : "input-mouse",
            "edges"     : "video-display",
            "bell"      : "audio-x-generic"
          }

    def __init__ (self, action):
        GObject.GObject.__init__ (self, 0, 0.5)
        self.set_padding (0, 0, 0, 10)
        if action in self.map: action = self.map[action]
        self.add (Image (name = action, type = ImageThemed, size = 22))

class SizedButton (Gtk.Button):

    minWidth = -1
    minHeight = -1

    def __init__ (self, minWidth = -1, minHeight = -1):
        super (SizedButton, self).__init__ ()
        self.minWidth = minWidth
        self.minHeight = minHeight
        self.connect ("size-request", self.adjust_size)

    def adjust_size (self, widget, requisition):
        width, height = requisition.width, requisition.height
        newWidth = max (width, self.minWidth)
        newHeight = max (height, self.minHeight)
        self.set_size_request (newWidth, newHeight)

class PrettyButton (Gtk.Button):
    __gsignals__ = {
        'draw': 'override',
    }

    _old_toplevel = None

    def __init__ (self):
        super (PrettyButton, self).__init__ ()
        self.states = {
                        "focus"   : False,
                        "pointer" : False
                      }
        self.set_size_request (200, -1)
        self.set_relief (Gtk.ReliefStyle.NONE)
        self.connect ("focus-in-event", self.update_state_in, "focus")
        self.connect ("focus-out-event", self.update_state_out, "focus")
        self.connect ("hierarchy-changed", self.hierarchy_changed)

    def hierarchy_changed (self, widget, old_toplevel):
        if old_toplevel == self._old_toplevel:
            return

        if not old_toplevel and self.state != Gtk.StateType.NORMAL:
            self.set_state(Gtk.StateType.PRELIGHT)
            self.set_state(Gtk.StateType.NORMAL)

        self._old_toplevel = old_toplevel


    def update_state_in (self, *args):
        state = args[-1]
        self.set_state (Gtk.StateType.PRELIGHT)
        self.states[state] = True

    def update_state_out (self, *args):
        state = args[-1]
        self.states[state] = False
        if True in self.states.values ():
            self.set_state (Gtk.StateType.PRELIGHT)
        else:
            self.set_state (Gtk.StateType.NORMAL)

    def do_expose_event (self, event):
        has_focus = self.flags () & Gtk.HAS_FOCUS
        if has_focus:
            self.unset_flags (Gtk.HAS_FOCUS)

        ret = super (PrettyButton, self).do_expose_event (self, event)

        if has_focus:
            self.set_flags (Gtk.HAS_FOCUS)

        return ret

class Label(Gtk.Label):
    def __init__(self, value = "", wrap = 160):
        GObject.GObject.__init__(self, value)
        self.props.xalign = 0
        self.props.wrap_mode = Pango.WrapMode.WORD
        self.set_line_wrap(True)
        self.set_size_request(wrap, -1)

class NotFoundBox(Gtk.Alignment):
    def __init__(self, value=""):
        GObject.GObject.__init__(self, 0.5, 0.5, 0.0, 0.0)
        
        box = Gtk.HBox()
        self.Warning = Gtk.Label()
        self.Markup = _("<span size=\"large\"><b>No matches found.</b> </span><span>\n\n Your filter \"<b>%s</b>\" does not match any items.</span>")
        value = protect_pango_markup(value)
        self.Warning.set_markup(self.Markup % value)
        image = Image("face-surprise", ImageThemed, 48)
            
        box.pack_start(image, False, False, 0)
        box.pack_start(self.Warning, True, True, 15)
        self.add(box)

    def update(self, value):
        value = protect_pango_markup(value)
        self.Warning.set_markup(self.Markup % value)

class IdleSettingsParser:
    def __init__(self, context, main):
        def FilterPlugin (p):
            return not p.Initialized and p.Enabled

        self.Context = context
        self.Main = main
        self.PluginList = [p for p in self.Context.Plugins.items() if FilterPlugin(p[1])]
        nCategories = len (main.MainPage.RightWidget._boxes)
        self.CategoryLoadIconsList = list(range(3, nCategories)) # Skip the first 3
        print('Loading icons...')

        GObject.timeout_add (150, self.Wait)

    def Wait(self):
        if not self.PluginList:
            return False
        
        if len (self.CategoryLoadIconsList) == 0: # If we're done loading icons
            GObject.idle_add (self.ParseSettings)
        else:
            GObject.idle_add (self.LoadCategoryIcons)
        
        return False
    
    def ParseSettings(self):
        name, plugin = self.PluginList[0]

        if not plugin.Initialized:
            plugin.Update ()
            self.Main.RefreshPage(plugin)

        self.PluginList.remove (self.PluginList[0])

        GObject.timeout_add (200, self.Wait)

        return False

    def LoadCategoryIcons(self):
        from ccm.Widgets import PluginButton

        catIndex = self.CategoryLoadIconsList[0]
        pluginWindow = self.Main.MainPage.RightWidget
        categoryBox = pluginWindow._boxes[catIndex]
        for (pluginIndex, plugin) in \
            enumerate (categoryBox.get_unfiltered_plugins()):
            categoryBox._buttons[pluginIndex] = PluginButton (plugin)
        categoryBox.rebuild_table (categoryBox._current_cols, True)
        pluginWindow.connect_buttons (categoryBox)

        self.CategoryLoadIconsList.remove (self.CategoryLoadIconsList[0])

        GObject.timeout_add (150, self.Wait)

        return False

# Updates all registered setting when they where changed through CompizConfig
class Updater:

    def __init__ (self):
        self.VisibleSettings = {}
        self.Plugins = []
        self.Block = 0

    def SetContext (self, context):
        self.Context = context

        GObject.timeout_add (2000, self.Update)

    def Append (self, widget):
        reference = weakref.ref(widget)
        setting = widget.Setting
        self.VisibleSettings.setdefault((setting.Plugin.Name, setting.Name), []).append(reference)

    def AppendPlugin (self, plugin):
        self.Plugins.append (plugin)

    def Remove (self, widget):
        setting = widget.Setting
        l = self.VisibleSettings.get((setting.Plugin.Name, setting.Name))
        if not l:
            return
        for i, ref in enumerate(list(l)):
            if ref() is widget:
                l.remove(ref)
                break

    def UpdatePlugins(self):
        for plugin in self.Plugins:
            plugin.Read()

    def UpdateSetting (self, setting):
        widgets = self.VisibleSettings.get((setting.Plugin.Name, setting.Name))
        if not widgets:
            return
        for reference in widgets:
            widget = reference()
            if widget is not None:
                widget.Read()

    def Update (self):
        if self.Block > 0:
            return True

        if self.Context.ProcessEvents():
            changed = self.Context.ChangedSettings
            if [s for s in changed if s.Plugin.Name == "core" and s.Name == "active_plugins"]:
                self.UpdatePlugins()

            for setting in list(changed):
                widgets = self.VisibleSettings.get((setting.Plugin.Name, setting.Name))
                if widgets: 
                    for reference in widgets:
                        widget = reference()
                        if widget is not None:
                            widget.Read()
                            if widget.List:
                                widget.ListWidget.Read()
                changed.remove(setting)

            self.Context.ChangedSettings = changed

        return True

GlobalUpdater = Updater ()

class PluginSetting:

    def __init__ (self, plugin, widget, handler):
        self.Widget = widget
        self.Plugin = plugin
        self.Handler = handler
        GlobalUpdater.AppendPlugin (self)

    def Read (self):
        widget = self.Widget
        widget.handler_block(self.Handler)
        widget.set_active (self.Plugin.Enabled)
        widget.set_sensitive (self.Plugin.Context.AutoSort)
        widget.handler_unblock(self.Handler)

class PureVirtualError(Exception):
    pass

def SettingKeyFunc(value):
    return value.Plugin.Ranking[value.Name]

def CategoryKeyFunc(category):
    if 'General' == category:
        return ''
    else:
        return category or 'zzzzzzzz'

def GroupIndexKeyFunc(item):
    return item[1][0]

FirstItemKeyFunc = operator.itemgetter(0)

EnumSettingKeyFunc = operator.itemgetter(1)

PluginKeyFunc = operator.attrgetter('ShortDesc')

def HasOnlyType (settings, stype):
    return settings and not [s for s in settings if s.Type != stype]

def GetSettings(group, types=None):

    def TypeFilter (settings, types):
         for setting in settings:
            if setting.Type in types:
                yield setting

    if types:
        screen = TypeFilter(iter(group.Screen.values()), types)
    else:
        screen = iter(group.Screen.values())

    return screen

# Support python 2.4
try:
    any
    all
except NameError:
    def any(iterable):
        for element in iterable:
            if element:
                return True
        return False

    def all(iterable):
        for element in iterable:
            if not element:
                return False
        return True


########NEW FILE########
__FILENAME__ = common
import glob
import logging
import ConfigParser

from lxml import etree

log = logging.getLogger('CommonSetting')

class RawConfigSetting(object):
    '''Just pass the file path'''
    def __init__(self, path, type=type):
        self._type = type

        self._path = path

        self.init_configparser()

    def _type_convert_set(self, value):
        if type(value) == bool:
            if value == True:
                value = 'true'
            elif value == False:
                value = 'false'

        # This is a hard code str type, so return '"xxx"' instead of 'xxx'
        if self._type == str:
            value = "'%s'" % value

        return value

    def _type_convert_get(self, value):
        if value == 'false':
            value = False
        elif value == 'true':
            value = True

        # This is a hard code str type, so return '"xxx"' instead of 'xxx'
        if self._type == str or type(value) == str:
            if (value.startswith('"') and value.endswith('"')) or \
               (value.startswith("'") and value.endswith("'")):
                value = eval(value)

        return value

    def init_configparser(self):
        self._configparser = ConfigParser.ConfigParser()
        self._configparser.read(self._path)

    def sections(self):
        return self._configparser.sections()

    def options(self, section):
        return self._configparser.options(section)

    def set_value(self, section, option, value):
        value = self._type_convert_set(value)

        if not self._configparser.has_section(section):
            self._configparser.add_section(section)

        self._configparser.set(section, option, value)
        with open(self._path, 'wb') as configfile:
            self._configparser.write(configfile)

        self.init_configparser()

    def get_value(self, section, option):
        if self._type:
            if self._type == int:
                getfunc = getattr(self._configparser, 'getint')
            elif self._type == float:
                getfunc = getattr(self._configparser, 'getfloat')
            elif self._type == bool:
                getfunc = getattr(self._configparser, 'getboolean')
            else:
                getfunc = getattr(self._configparser, 'get')

            value = getfunc(section, option)
        else:
            log.debug("No type message, so use the generic get")
            value = self._configparser.get(section, option)

        value = self._type_convert_get(value)

        return value

class Schema(object):
    cached_schema = {}
    cached_schema_tree = {}
    cached_override = {}

    @classmethod
    def load_override(cls):
        log.debug("\tLoading override")
        for override in glob.glob('/usr/share/glib-2.0/schemas/*.gschema.override'):
            try:
                cs = RawConfigSetting(override)
                for section in cs.sections():
                    cls.cached_override[section] = {}
                    for option in cs.options(section):
                        cls.cached_override[section][option] = cs.get_value(section, option)
            except Exception, e:
                log.error('Error while parsing override file: %s' % override)

    @classmethod
    def load_schema(cls, schema_id, key):
        log.debug("Loading schema value for: %s/%s" % (schema_id, key))
        if not cls.cached_override:
            cls.load_override()

        if schema_id in cls.cached_override and \
                key in cls.cached_override[schema_id]:
            return cls.cached_override[schema_id][key]

        if schema_id in cls.cached_schema and \
                key in cls.cached_schema[schema_id]:
            return cls.cached_schema[schema_id][key]

        schema_defaults = {}

        for schema_path in glob.glob('/usr/share/glib-2.0/schemas/*'):
            if not schema_path.endswith('.gschema.xml') and not schema_path.endswith('.enums.xml'):
                #TODO deal with enums
                continue

            if schema_path in cls.cached_schema_tree:
                tree = cls.cached_schema_tree[schema_path]
            else:
                tree = etree.parse(open(schema_path))

            for schema_node in tree.findall('schema'):
                if schema_node.attrib.get('id') == schema_id:
                    for key_node in schema_node.findall('key'):
                        if key_node.findall('default'):
                            schema_defaults[key_node.attrib['name']] = cls.parse_value(key_node)
                else:
                    continue

                cls.cached_schema[schema_id] = schema_defaults
        if key in schema_defaults:
            return schema_defaults[key]
        else:
            return None

    @classmethod
    def parse_value(cls, key_node):
        log.debug("Try to get type for value: %s" % key_node.items())
        value = key_node.find('default').text

        #TODO enum type
        if key_node.attrib.get('type'):
            type = key_node.attrib['type']

            if type == 'b':
                if value == 'true':
                    return True
                else:
                    return False
            elif type == 'i':
                return int(value)
            elif type == 'd':
                return float(value)
            elif type == 'as':
                return eval(value)

        return eval(value)

########NEW FILE########
__FILENAME__ = compizsettings
import logging

import ccm
import compizconfig

log = logging.getLogger('CompizSetting')

class CompizPlugin:
    context = compizconfig.Context()

    def __init__(self, name):
        self._plugin = self.context.Plugins[name]

    @classmethod
    def set_plugin_active(cls, name, active):
        try:
            plugin = cls.context.Plugins[name]
            plugin.Enabled = int(active)
            cls.context.Write()
        except:
            pass

    @classmethod
    def get_plugin_active(cls, name):
        try:
            plugin = cls.context.Plugins[name]
            return bool(plugin.Enabled)
        except:
            return False

    def set_enabled(self, bool):
        self._plugin.Enabled = int(bool)
        self.save()

    def get_enabled(self):
        return self._plugin.Enabled

    def save(self):
        self.context.Write()

    def resolve_conflict(self):
        conflicts = self.get_enabled() and self._plugin.DisableConflicts or \
                                           self._plugin.EnableConflicts
        conflict = ccm.PluginConflict(self._plugin, conflicts)
        return conflict.Resolve()

    @classmethod
    def is_available(cls, name, setting):
        return cls.context.Plugins.has_key(name) and \
               cls.context.Plugins[name].Screen.has_key(setting)

    def create_setting(self, key, target):
        settings = self._plugin.Screen

        if type(settings) == list:
            return settings[0][key]
        else:
            return settings[key]


class CompizSetting(object):
    def __init__(self, key, target=''):
        plugin_name, setting_name = key.split('.')
        self.key = key
        self._plugin = CompizPlugin(plugin_name)

        if not self._plugin.get_enabled():
            self._plugin.set_enabled(True)

        self._setting = self._plugin.create_setting(setting_name, target)

    def set_value(self, value):
        self._setting.Value = value
        self._plugin.save()

    def get_value(self):
        return self._setting.Value

    def is_default_and_enabled(self):
        return self._setting.Value == self._setting.DefaultValue and \
                self._plugin.get_enabled()

    def reset(self):
        self._setting.Reset()
        self._plugin.save()

    def resolve_conflict(self):
        return self._plugin.resolve_conflict()

    def get_schema_value(self):
        return self._setting.DefaultValue

########NEW FILE########
__FILENAME__ = configsettings
import logging

log = logging.getLogger('ConfigSetting')


from ubuntutweak.settings.common import RawConfigSetting, Schema

class ConfigSetting(RawConfigSetting):
    '''Key: /etc/lightdm/lightdm.conf::UserManager#load-users
    '''

    schema_path = '/usr/share/glib-2.0/schemas'

    def __init__(self, key=None, default=None, type=None):
        self._path = key.split('::')[0]
        self._type = type
        self._default = default
        self.key = key
        self._section = key.split('::')[1].split('#')[0]
        self._option = key.split('::')[1].split('#')[1]

        if self.is_override_schema(self._path):
            self._path = self.build_schema_path(self._path)
            self.key = self.build_schema_path(self.key)
            log.debug("is override schema, so update path to %s" % self._path)
            self.schema_default = default or Schema.load_schema(self._section, self._option)
            log.debug("schema_default is %s" % self.schema_default)

        log.debug("Build ConfigSetting for path: %s\n"
                  "\tkey: %s\n"
                  "\tdefault: %s, type: %s\n" % (self._path,
                                                 self.key,
                                                 self._default, 
                                                 self._type))

        RawConfigSetting.__init__(self, self._path, type=self._type)

    def build_schema_path(self, path):
        if not path.startswith(self.schema_path):
            return '%s/%s' % (self.schema_path, path)
        else:
            return path

    def set_value(self, value):
        super(ConfigSetting, self).set_value(self._section, self._option, value)

    def get_value(self):
        try:
            value = super(ConfigSetting, self).get_value(self._section, self._option)

            log.debug("ConfigSetting.get_value: %s, %s, %s" % (value, self._default, hasattr(self, 'schema_default')))
            return value
        except Exception, e:
            log.error(e)

            if self._default != None or hasattr(self, 'schema_default'):
                return self._default or getattr(self, 'schema_default')
            if self._type == int:
                return 0
            elif self._type == float:
                return 0.0
            elif self._type == bool:
                return False
            elif self._type == str:
                return ''
            else:
                return None

    def get_key(self):
        return self.key

    def is_override_schema(self, path=None):
        test_path = path or self._path
        return test_path.endswith('override')


class SystemConfigSetting(ConfigSetting):
    def set_value(self, value):
        # Because backend/daemon will use ConfigSetting , proxy represents the
        # daemon, so lazy import the proxy here to avoid backend to call proxy
        from ubuntutweak.policykit.dbusproxy import proxy
        value = self._type_convert_set(value)

        proxy.set_config_setting(self.get_key(), value)

        self.init_configparser()

########NEW FILE########
__FILENAME__ = gconfsettings
import glob
import logging

from gi.repository import GConf

from ubuntutweak.policykit.dbusproxy import proxy

log = logging.getLogger('GconfSetting')

class GconfSetting(object):
    """
    The base class of an option, client is shared by all subclass
    Every Setting hold a key and a value
    """

    client = GConf.Client.get_default()
    schema_override = {}

    def __init__(self, key=None, default=None, type=None):
        if not self.schema_override:
            self.load_override()

        self.key = key
        self.type = type
        self.default = default
        log.debug("Got the schema_default: %s for key: %s" % \
                    (self.default, self.key))

        if default and self.get_value() is None:
            self.set_value(default)

        if self.get_dir():
            self.client.add_dir(self.get_dir(), GConf.ClientPreloadType.PRELOAD_NONE)

    def load_override(self):
        for override in glob.glob('/usr/share/gconf/defaults/*'):
            try:
                for line in open(override):
                    splits = line.split()
                    key, value = splits[0], ' '.join(splits[1:])

                    if value == 'true':
                        value = True
                    elif value == 'false':
                        value = False
                    else:
                        if value.startswith('"') and value.endswith('"'):
                            value = eval(value)

                    self.schema_override[key] = value
            except Exception, e:
                log.error('Exception (%s) while processing override' % e)

    def get_dir(self):
        if self.key:
            return '/'.join(self.key.split('/')[0: -1])
        else:
            return None

    def get_value(self):
        gconfvalue = self.client.get(self.key)
        if gconfvalue:
            if gconfvalue.type == GConf.ValueType.BOOL:
                return gconfvalue.get_bool()
            if gconfvalue.type == GConf.ValueType.STRING:
                return gconfvalue.get_string()
            if gconfvalue.type == GConf.ValueType.INT:
                return gconfvalue.get_int()
            if gconfvalue.type == GConf.ValueType.FLOAT:
                return gconfvalue.get_float()
            if gconfvalue.type == GConf.ValueType.LIST:
                final_list = []
                if gconfvalue.get_list_type() == GConf.ValueType.STRING:
                    for item in gconfvalue.get_list():
                        final_list.append(item.get_string())
                return final_list
        else:
            if self.type == int:
                return 0
            elif self.type == float:
                return 0.0
            elif self.type == bool:
                return False
            elif self.type == str:
                return ''
            else:
                return None

    def set_value(self, value):
        if self.type and type(value) != self.type:
            value = self.type(value)

        gconfvalue = GConf.Value()

        if type(value) == bool:
            gconfvalue.type = GConf.ValueType.BOOL
            gconfvalue.set_bool(value)
        elif type(value) == str:
            gconfvalue.type = GConf.ValueType.STRING
            gconfvalue.set_string(value)
        elif type(value) == int:
            gconfvalue.type = GConf.ValueType.INT
            gconfvalue.set_int(int(value))
        elif type(value) == float:
            gconfvalue.type = GConf.ValueType.FLOAT
            gconfvalue.set_float(value)

        self.client.set(self.key, gconfvalue)

    def unset(self):
        self.client.unset(self.key)

    def connect_notify(self, func, data=None):
        self.client.notify_add(self.key, func, data)

    def get_schema_value(self):
        if not self.default:
            if self.key in self.schema_override:
                value = self.schema_override[self.key]
                if self.type and self.type != type(value):
                    log.debug("get_schema_value: %s, the type is wrong, so convert force" % value)
                    return self.type(value)
                return value

            value = self.client.get_default_from_schema(self.key)
            if value:
                if value.type == GConf.ValueType.BOOL:
                    return value.get_bool()
                elif value.type == GConf.ValueType.STRING:
                    return value.get_string()
                elif value.type == GConf.ValueType.INT:
                    return value.get_int()
                elif value.type == GConf.ValueType.FLOAT:
                    return value.get_float()
            else:
                raise Exception("No schema value for %s" % self.key)
        else:
            return self.default


class UserGconfSetting(GconfSetting):
    def get_value(self, user):
        data = str(proxy.get_user_gconf(user, self.key))
        log.debug('UserGconfSetting get the value from proxy: %s', data)
        if data == 'true':
            return True
        elif data == 'false':
            return False
        else:
            return data

    def set_value(self, user, value):
        if value:
            if type(value) == bool:
                proxy.set_user_gconf(user, self.key, 'true', 'bool', '')
            elif type(value) == str:
                proxy.set_user_gconf(user, self.key, value, 'string', '')
        else:
            proxy.set_user_gconf(user, self.key, 'false', 'bool', '')

########NEW FILE########
__FILENAME__ = gsettings
import os
import logging

from gi.repository import Gio

from ubuntutweak.settings.common import Schema

log = logging.getLogger('GSetting')


class GSetting(object):

    def __init__(self, key=None, default=None, type=None):
        parts = key.split('.')
        self.schema_id, self.key = '.'.join(parts[:-1]), parts[-1]

        self.type = type
        self.default = default
        self.schema_default = self.default or Schema.load_schema(self.schema_id, self.key)
        log.debug("Got the schema_default: %s for key: %s.%s" % \
                  (self.schema_default, self.schema_id, self.key))

        if self.schema_id in Gio.Settings.list_schemas():
            self.settings = Gio.Settings(self.schema_id)
        else:
            raise Exception('Oops, Settings schema "%s" is not installed' % self.schema_id)

        if self.key not in self.settings.list_keys():
            log.error("No key (%s) for schema %s" % (self.key, self.schema_id))

        if default and self.get_value() == None:
            self.set_value(default)

    def get_value(self):
        try:
            return self.settings[self.key]
        except KeyError, e:
            log.error(e)

            if self.type == int:
                return 0
            elif self.type == float:
                return 0.0
            elif self.type == bool:
                return False
            elif self.type == str:
                return ''
            else:
                return None

    def set_value(self, value):
        log.debug("The the value for type: %s and value: %s" % (self.type, value))
        try:
            if self.type == str:
                self.settings.set_string(self.key, str(value))
            elif self.type == int:
                self.settings.set_int(self.key, int(value))
            elif self.type == float:
                self.settings.set_double(self.key, value)
            else:
                self.settings[self.key] = value
        except KeyError, e:
            log.error(e)

    def connect_notify(self, func, data=None):
        self.settings.connect("changed::%s" % self.key, func, data)

    def unset(self):
        self.settings.reset(self.key)

    def get_schema_value(self):
        if self.schema_default is not None:
            return self.schema_default
        else:
            raise NotImplemented

########NEW FILE########
__FILENAME__ = fonts
# Ubuntu Tweak - Ubuntu Configuration Tool
#
# Copyright (C) 2007-2011 Tualatrix Chou <tualatrix@gmail.com>
#
# Ubuntu Tweak is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# Ubuntu Tweak is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Ubuntu Tweak; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA

from gi.repository import Gtk, Gio

from ubuntutweak import system
from ubuntutweak.gui.containers import ListPack, TablePack, GridPack
from ubuntutweak.modules  import TweakModule
from ubuntutweak.factory import WidgetFactory

class Fonts(TweakModule):
    __title__ = _('Fonts')
    __desc__ = _('Fonts Settings')
    __icon__ = 'font-x-generic'
    __category__ = 'appearance'
    __desktop__ = ['ubuntu', 'gnome-fallback', 'gnome', 'ubuntu-2d', 'gnome-classic', 'gnome-shell', 'gnome-fallback-compiz']

    utext_text_scaling = _("Text scaling factor:")
    utext_default_font = _("Default font:")
    utext_monospace_font = _("Monospace font:")
    utext_document_font = _("Document font:")
    utext_window_title_font = _("Window title bar font:")
    utext_hinting = _("Hinting:")
    utext_antialiasing = _("Antialiasing:")

    """Lock down some function"""
    def __init__(self):
        TweakModule.__init__(self)
        fb = Gtk.FontButton()
        fb.set_font_name('Monospace 24')
        fb.set_show_size(False)
        fb.set_use_size(13)

        if system.CODENAME == 'precise':
            window_font_label, window_font_button, window_font_reset_button = WidgetFactory.create("FontButton",
                       label=self.utext_window_title_font,
                       key="/apps/metacity/general/titlebar_font",
                       backend="gconf",
                       enable_reset=True)
        else:
            window_font_label, window_font_button, window_font_reset_button = WidgetFactory.create("FontButton",
                       label=self.utext_window_title_font,
                       key="org.gnome.desktop.wm.preferences.titlebar-font",
                       backend="gsettings",
                       enable_reset=True)

        box = GridPack(
                    WidgetFactory.create("Scale",
                        label=self.utext_text_scaling,
                        key="org.gnome.desktop.interface.text-scaling-factor",
                        min=0.5,
                        max=3.0,
                        step=0.1,
                        digits=1,
                        backend="gsettings",
                        enable_reset=True),
                    WidgetFactory.create("FontButton",
                        label=self.utext_default_font,
                        key="org.gnome.desktop.interface.font-name",
                        backend="gsettings",
                        enable_reset=True),
                    WidgetFactory.create("FontButton",
                        label=_("Desktop font:"),
                        key="org.gnome.nautilus.desktop.font",
                        backend="gsettings",
                        default="Ubuntu 11",
                        enable_reset=True),
                    WidgetFactory.create("FontButton",
                        label=self.utext_monospace_font,
                        key="org.gnome.desktop.interface.monospace-font-name",
                        backend="gsettings",
                        enable_reset=True),
                    WidgetFactory.create("FontButton",
                        label=self.utext_document_font,
                        key="org.gnome.desktop.interface.document-font-name",
                        backend="gsettings",
                        enable_reset=True),
                    (window_font_label, window_font_button, window_font_reset_button),
                    Gtk.Separator(),
                    WidgetFactory.create("ComboBox",
                        label=self.utext_hinting,
                        key="org.gnome.settings-daemon.plugins.xsettings.hinting",
                        values=('none', 'slight', 'medium', 'full'),
                        texts=(_('No hinting'),
                               _('Basic'),
                               _('Moderate'),
                               _('Maximum')),
                        backend="gsettings",
                        enable_reset=True),
                    WidgetFactory.create("ComboBox",
                        label=self.utext_antialiasing,
                        key="org.gnome.settings-daemon.plugins.xsettings.antialiasing",
                        values=('none', 'grayscale', 'rgba'),
                        texts=(_('No antialiasing'),
                               _('Standard grayscale antialiasing'),
                               _('Subpixel antialiasing (LCD screens only)')), 
                        backend="gsettings",
                        enable_reset=True),
            )

        self.add_start(box, False, False, 0)

########NEW FILE########
__FILENAME__ = icons
# Ubuntu Tweak - Ubuntu Configuration Tool
#
# Copyright (C) 2007-2011 Tualatrix Chou <tualatrix@gmail.com>
#
# Ubuntu Tweak is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# Ubuntu Tweak is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Ubuntu Tweak; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA

from ubuntutweak import system
from gi.repository import GObject, Gtk

from ubuntutweak.gui.containers import GridPack
from ubuntutweak.modules  import TweakModule
from ubuntutweak.factory import WidgetFactory

computer_icon = {
    "label": _('Show "Computer" icon'),
    "visible_key": "org.gnome.nautilus.desktop.computer-icon-visible",
    "name_key": "org.gnome.nautilus.desktop.computer-icon-name",
    "icon_name": "gnome-fs-client"
}

home_icon = {
    "label": _('Show "Home Folder" icon'),
    "visible_key": "org.gnome.nautilus.desktop.home-icon-visible",
    "name_key": "org.gnome.nautilus.desktop.home-icon-name",
    "icon_name": "gnome-fs-home"
}

trash_icon = {
    "label": _('Show "Trash" icon'),
    "visible_key": "org.gnome.nautilus.desktop.trash-icon-visible",
    "name_key": "org.gnome.nautilus.desktop.trash-icon-name",
    "icon_name": "gnome-fs-trash-empty"
}

network_icon = {
    "label": _('Show "Network Servers" icon'),
    "visible_key": "org.gnome.nautilus.desktop.network-icon-visible",
    "name_key": "org.gnome.nautilus.desktop.network-icon-name",
    "icon_name": "network-workgroup"
}

if system.CODENAME != 'precise':
    desktop_icons = (home_icon, trash_icon, network_icon)
else:
    desktop_icons = (computer_icon, home_icon, trash_icon, network_icon)

class DesktopIcon(Gtk.VBox):
    def __init__(self, item):
        GObject.GObject.__init__(self)

        self.show_button = WidgetFactory.create("CheckButton",
                                                label=item["label"],
                                                key=item["visible_key"],
                                                backend="gsettings")
        self.show_button.connect('toggled', self.on_show_button_changed)
        self.pack_start(self.show_button, False, False, 0)

        self.show_hbox = Gtk.HBox(spacing=12)
        self.pack_start(self.show_hbox, False, False, 0)

        if not self.show_button.get_active():
            self.show_hbox.set_sensitive(False)

        icon = Gtk.Image.new_from_icon_name(item["icon_name"], Gtk.IconSize.DIALOG)
        self.show_hbox.pack_start(icon, False, False, 0)

        self.rename_button = WidgetFactory.create("StringCheckButton",
                                                  label=_('Rename'),
                                                  key=item["name_key"],
                                                  backend="gsettings")
        self.rename_button.connect('toggled', self.on_show_button_changed)
        vbox = Gtk.VBox(spacing=6)
        self.show_hbox.pack_start(vbox, False, False, 0)
        vbox.pack_start(self.rename_button, False, False, 0)

        self.entry = WidgetFactory.create("Entry", key=item["name_key"], backend="gsettings")
        self.entry.connect('insert-at-cursor', self.on_entry_focus_out)
        if not self.rename_button.get_active():
            self.entry.set_sensitive(False)
        vbox.pack_start(self.entry, False, False, 0)

    def on_entry_focus_out(self, widget, event):
        self.entry.get_setting().set_value(self.entry.get_text())

    def on_show_button_changed(self, widget):
        self.show_hbox.set_sensitive(self.show_button.get_active())
        active = self.rename_button.get_active()

        if active:
            self.entry.set_sensitive(True)
            self.entry.grab_focus()
        else:
            self.entry.set_sensitive(False)
            self.entry.get_setting().unset()
            self.entry.set_text('')


class Icons(TweakModule):
    __title__ = _('Desktop Icons')
    __desc__ = _("Rename and toggle visibilty of desktop icons")
    __icon__ = 'preferences-desktop-wallpaper'
    __category__ = 'desktop'
    __desktop__ = ['ubuntu', 'ubuntu-2d', 'gnome', 'gnome-classic', 'gnome-shell', 'gnome-fallback', 'gnome-fallback-compiz']

    utext_show_icon = _("Show desktop icons:")
    utext_mount_volume = _("Show mounted volumes")
    utext_home_folder = _('Show contents of "Home Folder"')

    def __init__(self):
        TweakModule.__init__(self)

        show_label, show_switch = WidgetFactory.create("Switch",
                                                label=self.utext_show_icon,
                                                key="org.gnome.desktop.background.show-desktop-icons",
                                                backend="gsettings")

        setting_list = []
        show_switch.connect('notify::active', self.on_show_button_changed, setting_list)

        for item in desktop_icons:
            setting_list.append(DesktopIcon(item))

        volumes_button = WidgetFactory.create("CheckButton",
                                      label=self.utext_mount_volume,
                                      key="org.gnome.nautilus.desktop.volumes-visible",
                                      backend="gsettings")
        setting_list.append(volumes_button)

        if system.CODENAME == 'precise':
            home_contents_button = WidgetFactory.create("CheckButton",
                                          label=self.utext_home_folder,
                                          key="org.gnome.nautilus.preferences.desktop-is-home-dir",
                                          backend="gsettings")
            setting_list.append(home_contents_button)

        notes_label = Gtk.Label()
        notes_label.set_property('halign', Gtk.Align.START)
        notes_label.set_markup('<span size="smaller">%s</span>' % \
                _('Note: switch off this option will make the desktop unclickable'))
        notes_label._ut_left = 1

        grid_box = GridPack((show_label, show_switch),
                            notes_label,
                            *setting_list)
        self.add_start(grid_box)
        self.on_show_button_changed(show_switch, None, setting_list)

    def on_show_button_changed(self, widget, value, setting_list):
        for item in setting_list:
            item.set_sensitive(widget.get_active())

########NEW FILE########
__FILENAME__ = loginsettings
# Ubuntu Tweak - Ubuntu Configuration Tool
#
# Copyright (C) 2007-2011 Tualatrix Chou <tualatrix@gmail.com>
#
# Ubuntu Tweak is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# Ubuntu Tweak is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Ubuntu Tweak; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA

import os
import logging

from gi.repository import Gtk, GdkPixbuf

from ubuntutweak import system
from ubuntutweak.factory import WidgetFactory
from ubuntutweak.modules  import TweakModule
from ubuntutweak.gui.treeviews import get_local_path
from ubuntutweak.gui.containers import ListPack, GridPack
from ubuntutweak.policykit import PK_ACTION_TWEAK
from ubuntutweak.utils import theme
from ubuntutweak.settings.configsettings import SystemConfigSetting
from ubuntutweak.settings.gsettings import GSetting

log = logging.getLogger('LoginSettings')

class LoginSettings(TweakModule):
    __title__ = _('Login Settings')
    __desc__ = _('Control the appearance and behaviour of your login screen')
    __icon__ = 'gdm-setup'
    __policykit__ = PK_ACTION_TWEAK
    __category__ = 'startup'

    utext_allow_guest = _('Guest account:')
    utext_draw_grid = _('Draw grid:')
    utext_login_sound = _('Play login sound:')
    utext_gtk_theme = _('Gtk theme:')
    utext_icon_theme = _('Icon theme:')

    @classmethod
    def is_active(cls):
        return os.path.exists('/usr/sbin/lightdm')

    def __init__(self):
        TweakModule.__init__(self, 'loginsettings.ui')

        valid_themes = theme.get_valid_themes()
        valid_icon_themes = theme.get_valid_icon_themes()

        notes_label = Gtk.Label()
        notes_label.set_property('halign', Gtk.Align.START)
        notes_label.set_markup('<span size="smaller">%s</span>' % \
                _('Note: you may need to reboot to take effect'))
        notes_label._ut_left = 1

        self.login_box = GridPack(
                        WidgetFactory.create('Switch',
                            label=self.utext_allow_guest,
                            key='/etc/lightdm/lightdm.conf::SeatDefaults#allow-guest',
                            default=True,
                            backend='systemconfig'),
                        notes_label,
                        WidgetFactory.create('Switch',
                            label=self.utext_draw_grid,
                            key='50_unity-greeter.gschema.override::com.canonical.unity-greeter#draw-grid',
                            backend='systemconfig'),
                        WidgetFactory.create('Switch',
                            label=self.utext_login_sound,
                            key='50_unity-greeter.gschema.override::com.canonical.unity-greeter#play-ready-sound',
                            backend='systemconfig'),
                        WidgetFactory.create('ComboBox',
                            label=self.utext_gtk_theme,
                            key='50_unity-greeter.gschema.override::com.canonical.unity-greeter#theme-name',
                            backend='systemconfig',
                            texts=valid_themes,
                            values=valid_themes),
                        WidgetFactory.create('ComboBox',
                            label=self.utext_icon_theme,
                            key='50_unity-greeter.gschema.override::com.canonical.unity-greeter#icon-theme-name',
                            backend='systemconfig',
                            texts=valid_icon_themes,
                            values=valid_icon_themes),
                        )

        self.login_box.set_sensitive(False)
        self.add_start(self.login_box, False, False, 0)

        if system.CODENAME != 'saucy':
            self.add_start(Gtk.Separator(), False, False, 6)

            self._setup_logo_image()
            self._setup_background_image()

            box = ListPack('', (self.main_vbox))
            self.add_start(box, False, False, 0)

    def _setup_logo_image(self):
        self._greeter_logo = SystemConfigSetting('50_unity-greeter.gschema.override::com.canonical.unity-greeter#logo', type=str)
        logo_path = self._greeter_logo.get_value()

        if logo_path:
            self.logo_image.set_from_file(logo_path)

    def _setup_background_image(self):
        self._greeter_background = SystemConfigSetting('50_unity-greeter.gschema.override::com.canonical.unity-greeter#background', type=str)
        background_path = self._greeter_background.get_value()

        log.debug("Setup the background file: %s" % background_path)

        if background_path:
            try:
                pixbuf = GdkPixbuf.Pixbuf.new_from_file(background_path)
                pixbuf = pixbuf.scale_simple(160, 120, GdkPixbuf.InterpType.NEAREST)
                self.background_image.set_from_pixbuf(pixbuf)
            except Exception, e:
                log.error("Loading background failed, message is %s" % e)

    def _get_desktop_background_path(self):
        return get_local_path(GSetting('org.gnome.desktop.background.picture-uri').get_value())

    def on_polkit_action(self, widget):
        self.main_vbox.set_sensitive(True)
        if hasattr(self, 'login_box'):
            self.login_box.set_sensitive(True)

    def on_logo_button_clicked(self, widget):
        dialog = Gtk.FileChooserDialog(_('Choose a new logo image'),
                                        action=Gtk.FileChooserAction.OPEN,
                                        buttons=(Gtk.STOCK_REVERT_TO_SAVED, Gtk.ResponseType.DELETE_EVENT,
                                                 Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
                                                 Gtk.STOCK_OPEN, Gtk.ResponseType.ACCEPT))
        filter = Gtk.FileFilter()
        filter.set_name(_('All images (*.PNG)'))
        filter.add_pattern('*.png')
        dialog.set_current_folder(os.path.expanduser('~'))
        dialog.add_filter(filter)
        self._set_preview_widget_for_dialog(dialog)

        orignal_logo = '/usr/share/unity-greeter/logo.png'

        filename = ''
        response = dialog.run()

        if response == Gtk.ResponseType.ACCEPT:
            filename = dialog.get_filename()
            dialog.destroy()

            if filename:
                self._greeter_logo.set_value(filename)
                self._setup_logo_image()
        elif response == Gtk.ResponseType.DELETE_EVENT:
            dialog.destroy()
            self._greeter_logo.set_value(orignal_logo)
            self._setup_logo_image()
        else:
            dialog.destroy()
            return

    def _set_preview_widget_for_dialog(self, dialog):
        preview = Gtk.Image()
        dialog.set_preview_widget(preview)
        dialog.connect('update-preview', self.on_update_preview, preview)

    def on_update_preview(self, dialog, preview):
        filename = dialog.get_preview_filename()
        try:
            pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_size(filename, 128, 128)
        except Exception, e:
            log.error(e)
            pixbuf = None

        if pixbuf:
            preview.set_from_pixbuf(pixbuf)

            dialog.set_preview_widget_active(True)
        else:
            dialog.set_preview_widget_active(False)

    def on_background_button_clicked(self, widget):
        dialog = Gtk.FileChooserDialog(_('Choose a new background image'),
                                        action=Gtk.FileChooserAction.OPEN,
                                        buttons=(Gtk.STOCK_REVERT_TO_SAVED, Gtk.ResponseType.DELETE_EVENT,
                                                 Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
                                                 Gtk.STOCK_OPEN, Gtk.ResponseType.ACCEPT))
        filter = Gtk.FileFilter()
        filter.set_name(_('All images'))
        filter.add_pattern('*.jpg')
        filter.add_pattern('*.png')
        filter.add_pattern('*.JPG')
        filter.add_pattern('*.PNG')
        dialog.set_current_folder('/usr/share/backgrounds')
        dialog.add_filter(filter)
        self._set_preview_widget_for_dialog(dialog)

        orignal_background = '/usr/share/backgrounds/warty-final-ubuntu.png'
        filename = ''
        response = dialog.run()

        if response == Gtk.ResponseType.ACCEPT:
            filename = dialog.get_filename()
            log.debug("Get background file, the path is: %s" % filename)
            dialog.destroy()

            if filename:
                self._greeter_background.set_value(filename)

                self._setup_background_image()
        elif response == Gtk.ResponseType.DELETE_EVENT:
            dialog.destroy()
            self._greeter_background.set_value(orignal_background)
            self._setup_background_image()
        else:
            dialog.destroy()
            return

    def on_same_background_button_clicked(self, widget):
        log.debug('on_same_background_button_clicked')
        background_path = self._get_desktop_background_path()

        if background_path and \
                background_path != self._greeter_background.get_value():
            self._greeter_background.set_value(background_path)
            self._setup_background_image()

########NEW FILE########
__FILENAME__ = lovewallpaperhd
# -*- coding: utf-8 -*-

import os
import json
import thread
import urllib2
import logging

from gi.repository import Notify, GLib, Gtk, Gdk, GdkPixbuf
from gi.repository.GdkPixbuf import Pixbuf

from ubuntutweak.settings.gsettings import GSetting
from ubuntutweak.common.consts import CONFIG_ROOT
from ubuntutweak.modules  import TweakModule
from ubuntutweak.network.downloadmanager import DownloadDialog

log = logging.getLogger('LovewallpaperHD')

class LovewallpaperHD(TweakModule):
    __title__ = _("Love Wallpaper HD")
    __desc__ = _('Browse online gallery and find your wallpaper')
    __icon__ = 'love-wallpaper.png'
    __category__ = 'desktop'

    __author__ = 'kevinzhow <kevinchou.c@gmail.com>'
    __url__ = 'http://imkevin.me'
    __url_title__ = 'Kevin Blog'

    def __init__(self):
        TweakModule.__init__(self)

        self.wallpaper_path = os.path.join(CONFIG_ROOT, 'lovewallpaper.jpg')
        self.jsonman = JsonMan(Gdk.Screen.width(), Gdk.Screen.height())

        self.image_model = Gtk.ListStore(Pixbuf, str)
        self.image_view = Gtk.IconView.new_with_model(self.image_model)
        self.image_view.set_property('halign', Gtk.Align.CENTER)
        self.image_view.set_column_spacing(5)
        self.image_view.set_item_padding(5)
        self.image_view.set_item_width(175)
        self.image_view.set_pixbuf_column(0)
        self.image_view.connect("item-activated", self.set_wallpaper)

        link_label = Gtk.Label()
        link_label.set_markup('Powered by <a href="http://www.lovebizhi.com/linux">%s</a>.' % self.__title__)
        link_label.set_line_wrap(True)

        lucky_button = Gtk.Button(_("I'm Feeling Lucky"))
        lucky_button.set_property('halign', Gtk.Align.CENTER)
        lucky_button.connect('clicked', self.on_luky_button_clicked)

        self.connect('size-allocate', self.on_size_allocate)

        try:
            self.load_imageview()
            self.add_start(self.image_view, False, False, 0)
            self.add_start(lucky_button, False, False, 0)
        except Exception, e:
            link_label.set_markup('Network issue happened when visiting <a href="http://www.lovebizhi.com/linux">%s</a>. Please check if you can access the website.' % self.__title__)
        finally:
            self.add_start(link_label, False, False, 0)

    def on_luky_button_clicked(self, widget):
        self.load_imageview()

    def load_imageview(self):
        self.image_model.clear()
        self.jsonman.get_json()
        self.image_list = self.jsonman.create_tryluck()

        for image in self.image_list:
            thread.start_new_thread(self.add_image, (image,))

    def on_size_allocate(self, width, allocation):
        if allocation.width > 0:
            self.image_view.set_columns(allocation.width / 195)

    def add_image(self, image):
        gtkimage = Gtk.Image()
        response = urllib2.urlopen(image.small)

        loader = GdkPixbuf.PixbufLoader()
        loader.write(response.read())
        loader.close()
        gtkimage.set_from_pixbuf(loader.get_pixbuf())
        self.image_model.append([gtkimage.get_pixbuf(), image.big])

    def set_wallpaper(self, view, path):
        url = self.image_model[path][1]
        dialog = DownloadDialog(url=url,
                                title=_('Downloading Wallpaper'),
                                parent=view.get_toplevel())
        dialog.downloader.connect('downloaded', self.on_wallpaper_downloaded)

        response = dialog.run()
        dialog.destroy()

        if response == Gtk.ResponseType.CANCEL:
            log.debug("Download cancelled by user")
            dialog.downloader.disconnect_by_func(self.on_wallpaper_downloaded)

    def on_wallpaper_downloaded(self, downloader):
        os.rename(downloader.get_downloaded_file(), self.wallpaper_path)

        wallpaper_setting = GSetting('org.gnome.desktop.background.picture-uri')
        wallpaper_setting.set_value(GLib.filename_to_uri(self.wallpaper_path, None))

        n = Notify.Notification.new(self.__title__, "Set wallpaper successfully!", 'ubuntu-tweak')
        n.show()


class Picture:
    def __init__(self, small, big, num):
        self.small = small
        self.big = big
        self.key = num


class JsonMan:
    def __init__(self, screen_width=None, screen_height=None, parent=None):
        self.screen_height = str(screen_height)
        self.screen_width = str(screen_width)

    def get_json(self):
        json_init_url = "http://partner.lovebizhi.com/ubuntutweak.php?width=" + self.screen_width + "&height=" + self.screen_height
        fd = urllib2.urlopen(json_init_url, timeout=10).read().decode("utf-8")
        self.index = json.loads(fd)

    def create_tryluck(self):
        self.tryluck_list = []
        num = 0
        for tryluck_image in self.index:
            num += 1
            self.tryluck_list.append(Picture(tryluck_image["s"],
                                             tryluck_image['b'],
                                             str(num)))
        return self.tryluck_list

########NEW FILE########
__FILENAME__ = misc
# Ubuntu Tweak - Ubuntu Configuration Tool
#
# Copyright (C) 2007-2011 Tualatrix Chou <tualatrix@gmail.com>
#
# Ubuntu Tweak is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# Ubuntu Tweak is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Ubuntu Tweak; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA

import os
import re
import logging
from gi.repository import Gtk, Gio

from ubuntutweak import system
from ubuntutweak.gui.containers import ListPack, GridPack
from ubuntutweak.modules  import TweakModule
from ubuntutweak.factory import WidgetFactory

log = logging.getLogger('Misc')

class Misc(TweakModule):
    __title__ = _('Miscellaneous')
    __desc__ = _('Set the cursor timeout, menus and buttons icons')
    __icon__ = 'gconf-editor'
    __category__ = 'appearance'

    utext_natural = _('Natural Scrolling')
    utext_menu_icon = _('Menus have icons')
    utext_button_icon = _('Buttons have icons')
    utext_context_menu = _("Show Input Method menu in the context menu")
    utext_unicode = _("Show Unicode Control Character menu in the context menu")
    utext_disable_print = _("Disable printing")
    utext_disable_print_setting = _("Disable printer settings")
    utext_save = _("Disable save to disk")
    utext_user_switch = _('Disable "Fast User Switching"')
    utext_cursor_blink = _('Cursor blink:')
    utext_overlay_scrollbar = _('Overlay scrollbars:')
    utext_cursor_blink_time = _('Cursor blink time:')
    utext_cursor_blink_timeout = _('Cursor blink timeout:')

    def __init__(self):
        TweakModule.__init__(self)

        self.natural_scrolling_switch = Gtk.Switch()
        self.set_the_natural_status()
        self.natural_scrolling_switch.connect('notify::active', self.on_natural_scrolling_changed)

        notes_label = Gtk.Label()
        notes_label.set_property('halign', Gtk.Align.START)
        notes_label.set_markup('<span size="smaller">%s</span>' % \
                _('Note: you may need to log out to take effect'))
        notes_label._ut_left = 1

        if system.CODENAME == 'precise':
           overlay_label, overlay_widget = WidgetFactory.create('Switch',
                                                 label=self.utext_overlay_scrollbar,
                                                 key='org.gnome.desktop.interface.ubuntu-overlay-scrollbars',
                                                 backend='gsettings')
        else:
          overlay_label, overlay_widget = WidgetFactory.create('ComboBox',
                                                 label=self.utext_overlay_scrollbar,
                                                 key='com.canonical.desktop.interface.scrollbar-mode',
                                                 texts=[_('Normal'),
                                                        _('Auto'),
                                                        _('Show Overlay'),
                                                        _('Never Show Overlay')],
                                                 values=['normal',
                                                         'overlay-auto',
                                                         'overlay-pointer',
                                                         'overlay-touch'],
                                                 backend='gsettings')

        self.theme_box = GridPack(
                            WidgetFactory.create('CheckButton',
                                                 label=self.utext_menu_icon,
                                                 key='org.gnome.desktop.interface.menus-have-icons',
                                                 backend='gsettings',
                                                 ),
                            WidgetFactory.create('CheckButton',
                                label=self.utext_button_icon,
                                key='org.gnome.desktop.interface.buttons-have-icons',
                                backend='gsettings'),
                            WidgetFactory.create('CheckButton',
                                                 label=self.utext_context_menu,
                                                 key='org.gnome.desktop.interface.show-input-method-menu',
                                                 backend='gsettings',
                                                 ),
                            WidgetFactory.create('CheckButton',
                                                 label=self.utext_unicode,
                                                 key='org.gnome.desktop.interface.show-unicode-menu',
                                                 backend='gsettings',
                                                 ),
                            Gtk.Separator(),
                            WidgetFactory.create("CheckButton",
                                                 label=self.utext_disable_print,
                                                 key="org.gnome.desktop.lockdown.disable-printing",
                                                 backend="gsettings",
                                                 blank_label=True),
                            WidgetFactory.create("CheckButton",
                                                 label=self.utext_disable_print_setting,
                                                 key="org.gnome.desktop.lockdown.disable-print-setup",
                                                 backend="gsettings",
                                                 blank_label=True),
                            WidgetFactory.create("CheckButton",
                                                 label=self.utext_save,
                                                 key="org.gnome.desktop.lockdown.disable-save-to-disk",
                                                 backend="gsettings",
                                                 blank_label=True),
                            WidgetFactory.create("CheckButton",
                                                 label=self.utext_user_switch,
                                                 key="org.gnome.desktop.lockdown.disable-user-switching",
                                                 backend="gsettings",
                                                 blank_label=True),
                            Gtk.Separator(),
                            (Gtk.Label(self.utext_natural), self.natural_scrolling_switch),
                            notes_label,
                            (overlay_label, overlay_widget),
                            WidgetFactory.create('Switch',
                                                 label=self.utext_cursor_blink,
                                                 key='org.gnome.desktop.interface.cursor-blink',
                                                 backend='gsettings',
                                                 ),
                            WidgetFactory.create('Scale',
                                                 label=self.utext_cursor_blink_time,
                                                 key='org.gnome.desktop.interface.cursor-blink-time',
                                                 backend='gsettings',
                                                 min=100,
                                                 max=2500,
                                                 step=100,
                                                 type=int,
                                                 ),
                            WidgetFactory.create('SpinButton',
                                                 label=self.utext_cursor_blink_timeout,
                                                 key='org.gnome.desktop.interface.cursor-blink-timeout',
                                                 backend='gsettings',
                                                 min=1,
                                                 max=2147483647,
                                                 ))
        self.add_start(self.theme_box, False, False, 0)

    def get_pointer_id(self):
        pointer_ids = []
        id_pattern = re.compile('id=(\d+)')
        for line in os.popen('xinput list').read().split('\n'):
            if 'id=' in line and \
               'pointer' in line and \
               'slave' in line and \
               'XTEST' not in line:
                match = id_pattern.findall(line)
                if match:
                    pointer_ids.append(match[0])

        return pointer_ids

    def get_natural_scrolling_enabled(self):
        if not self.get_natural_scrolling_from_file():
            ids = self.get_pointer_id()
            value = len(ids)
            for id in ids:
                map = os.popen('xinput get-button-map %s' % id).read().strip()
                if '4 5' in map:
                    value -= 1
                elif '5 4' in map:
                    continue

            if value == 0:
                return False
            elif value == len(ids):
                return True
        return True

    def set_the_natural_status(self):
        self.natural_scrolling_switch.set_active(self.get_natural_scrolling_enabled())

    def on_natural_scrolling_changed(self, widget, *args):
        log.debug('>>>>> on_natural_scrolling_changed: %s' % widget.get_active())

        map = '1 2 3 4 5 6 7 8 9 10 11 12'

        if widget.get_active():
            map = map.replace('4 5', '5 4')
        else:
            map = map.replace('5 4', '4 5')

        self.save_natural_scrolling_to_file(map)
        os.system('xmodmap ~/.Xmodmap')

    def get_natural_scrolling_from_file(self):
        string = 'pointer = 1 2 3 5 4'
        xmodmap = os.path.expanduser('~/.Xmodmap')
        if os.path.exists(xmodmap):
            return string in open(xmodmap).read()
        else:
            return False

    def save_natural_scrolling_to_file(self, map):
        xmodmap = os.path.expanduser('~/.Xmodmap')
        map = map + '\n'
        string = 'pointer = %s' % map

        if os.path.exists(xmodmap):
            pattern = re.compile('pointer = ([\d\s]+)')
            data = open(xmodmap).read()
            match = pattern.search(data)
            if match:
                log.debug("Match in Xmodmap: %s" % match.groups()[0])
                data = data.replace(match.groups()[0], map)
            else:
                data = data + '\n' + string
        else:
            data = string

        log.debug('Will write the content to Xmodmap: %s' % data)
        with open(xmodmap, 'w') as f:
            f.write(data)
            f.close()

########NEW FILE########
__FILENAME__ = nautilus
# Ubuntu Tweak - Ubuntu Configuration Tool
#
# Copyright (C) 2007-2011 Tualatrix Chou <tualatrix@gmail.com>
#
# Ubuntu Tweak is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# Ubuntu Tweak is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Ubuntu Tweak; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA

from gi.repository import GObject, Gtk

from ubuntutweak.modules  import TweakModule
from ubuntutweak.factory import WidgetFactory
from ubuntutweak.gui.containers import GridPack


class Nautilus(TweakModule):
    __title__ = _('File Manager')
    __desc__ = _('Manage the Nautilus file manager')
    __icon__ = ['file-manager', 'nautilus']
    __category__ = 'system'
    __desktop__ = ['ubuntu', 'ubuntu-2d', 'gnome', 'gnome-classic', 'gnome-shell', 'gnome-fallback', 'gnome-fallback-compiz']

    utext_pathbar = _('Use the location entry instead of the pathbar')
    recursive_search = _('Enable Recursive Search')
    utext_automount = _('Automatically mount media:')
    utext_open = _('Automatically open a folder:')
    utext_prompt = _('Prompt or autorun/autostart programs:')
    utext_thumbnail_icon_size = _('Thumbnail icon size (pixels):')
    utext_thumbnail_cache_age = _('Thumbnail cache time (days):')
    utext_thumbnail_cache_size = _('Maximum thumbnail cache size (MB):')

    def __init__(self):
        TweakModule.__init__(self)

        box = GridPack(
                    WidgetFactory.create("Switch",
                        label=self.utext_pathbar,
                        enable_reset=True,
                        key="org.gnome.nautilus.preferences.always-use-location-entry",
                        backend="gsettings"),
                    WidgetFactory.create('Switch',
                        key='org.gnome.nautilus.preferences.enable-interactive-search',
                        enable_reset=True,
                        reverse=True,
                        label=self.recursive_search,
                        backend="gsettings"),
                    WidgetFactory.create('Switch',
                        key='org.gnome.desktop.media-handling.automount',
                        enable_reset=True,
                        label=self.utext_automount,
                        backend="gsettings"),
                    WidgetFactory.create('Switch',
                        key='org.gnome.desktop.media-handling.automount-open',
                        enable_reset=True,
                        label=self.utext_open,
                        backend="gsettings"),
                    WidgetFactory.create('Switch',
                        key='org.gnome.desktop.media-handling.autorun-never',
                        enable_reset=True,
                        reverse=True,
                        label=self.utext_prompt,
                        backend="gsettings"),
                    Gtk.Separator(),
                    WidgetFactory.create('Scale',
                        key='org.gnome.nautilus.icon-view.thumbnail-size',
                        enable_reset=True,
                        min=16, max=512,
                        step=16,
                        label=self.utext_thumbnail_icon_size,
                        backend="gsettings"),
                    WidgetFactory.create('Scale',
                        key='org.gnome.desktop.thumbnail-cache.maximum-age',
                        enable_reset=True,
                        min=-1, max=180,
                        step=1,
                        label=self.utext_thumbnail_cache_age,
                        backend="gsettings"),
                    WidgetFactory.create('Scale',
                        key='org.gnome.desktop.thumbnail-cache.maximum-size',
                        enable_reset=True,
                        min=-1, max=512,
                        step=1,
                        label=self.utext_thumbnail_cache_size,
                        backend="gsettings"),
        )
        self.add_start(box, False, False, 0)

########NEW FILE########
__FILENAME__ = session
# Ubuntu Tweak - Ubuntu Configuration Tool
#
# Copyright (C) 2007-2011 Tualatrix Chou <tualatrix@gmail.com>
#
# Ubuntu Tweak is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# Ubuntu Tweak is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Ubuntu Tweak; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA

import os

from gi.repository import Gtk, Gio

from ubuntutweak import system
from ubuntutweak.modules  import TweakModule
from ubuntutweak.factory import WidgetFactory
from ubuntutweak.gui.containers import ListPack, TablePack, GridPack
from ubuntutweak.gui.dialogs import ErrorDialog

class Session(TweakModule):
    __title__ = _('Session Indicator')
    __desc__ = _('Control your system session releated features')
    __icon__ = 'gnome-session-hibernate'
    __category__ = 'startup'

    utext_user_indicator = _('User indicator')
    utext_lock_screen = _('Disable "Lock Screen"')
    utext_real_name = _("Show user's real name on the panel")
    utext_logout = _("Remove the log out item")
    utext_shutdown = _("Remove the shutdown item")
    utext_suppress_logout = _("Suppress the dialog to confirm logout and shutdown action")

    @classmethod
    def is_active(cls):
        return os.path.exists('/usr/lib/indicator-session')

    def __init__(self):
        TweakModule.__init__(self)

        if system.CODENAME == 'precise':
            user_indicator_label, user_menu_switch, reset_button = WidgetFactory.create("Switch",
                                      label=self.utext_user_indicator,
                                      enable_reset=True,
                                      backend="gsettings",
                                      key='com.canonical.indicator.session.user-show-menu')
        else:
            user_indicator_label, user_menu_switch, reset_button = None, None, None

        lockscreen_button, lockscreen_reset_button = WidgetFactory.create("CheckButton",
                     label=self.utext_lock_screen,
                     key="org.gnome.desktop.lockdown.disable-lock-screen",
                     backend="gsettings",
                     enable_reset=True)

        box = GridPack(
                (user_indicator_label, user_menu_switch, reset_button),
                  WidgetFactory.create("CheckButton",
                                  label=self.utext_real_name,
                                  enable_reset=True,
                                  blank_label=True,
                                  backend="gsettings",
                                  key="com.canonical.indicator.session.show-real-name-on-panel"),
                  Gtk.Separator(),
                  (Gtk.Label(_("Session indicator:")), lockscreen_button, lockscreen_reset_button),
                  WidgetFactory.create("CheckButton",
                      label=self.utext_logout,
                      enable_reset=True,
                      blank_label=True,
                      backend="gsettings",
                      key="com.canonical.indicator.session.suppress-logout-menuitem"),
                  WidgetFactory.create("CheckButton",
                      label=self.utext_shutdown,
                      enable_reset=True,
                      blank_label=True,
                      backend="gsettings",
                      key="com.canonical.indicator.session.suppress-shutdown-menuitem"),
                  WidgetFactory.create("CheckButton",
                      label=self.utext_suppress_logout,
                      enable_reset=True,
                      blank_label=True,
                      backend="gsettings",
                      key="com.canonical.indicator.session.suppress-logout-restart-shutdown"),
          )
        self.add_start(box, False, False, 0)

########NEW FILE########
__FILENAME__ = sound
# Ubuntu Tweak - Ubuntu Configuration Tool
#
# Copyright (C) 2007-2012 Tualatrix Chou <tualatrix@gmail.com>
#
# Ubuntu Tweak is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# Ubuntu Tweak is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Ubuntu Tweak; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA

import os
from gi.repository import Gtk, Gio

from ubuntutweak.utils import walk_directories
from ubuntutweak.gui.containers import ListPack, GridPack
from ubuntutweak.modules  import TweakModule
from ubuntutweak.factory import WidgetFactory
from ubuntutweak.settings.configsettings import SystemConfigSetting

class Sound(TweakModule):
    __title__ = _('Sound')
    __desc__ = _('Set the sound theme for Ubuntu')
    __icon__ = 'sound'
    __category__ = 'appearance'

    utext_event_sounds = _('Event sounds:')
    utext_input_feedback = _('Input feedback sounds:')
    utext_sound_theme = _('Sound theme:')
    utext_login_sound = _('Play login sound:')

    def __init__(self):
        TweakModule.__init__(self)

        valid_themes = self._get_valid_themes()

        theme_box = GridPack(
                        WidgetFactory.create('Switch',
                            label=self.utext_event_sounds,
                            key='org.gnome.desktop.sound.event-sounds',
                            backend='gsettings'),
                        WidgetFactory.create('Switch',
                            label=self.utext_login_sound,
                            key='50_unity-greeter.gschema.override::com.canonical.unity-greeter#play-ready-sound',
                            backend='systemconfig'),
                        WidgetFactory.create('Switch',
                            label=self.utext_input_feedback,
                            key='org.gnome.desktop.sound.input-feedback-sounds',
                            backend='gsettings'),
                        WidgetFactory.create('ComboBox',
                            label=self.utext_sound_theme,
                            key='org.gnome.desktop.sound.theme-name',
                            backend='gsettings',
                            texts=valid_themes,
                            values=valid_themes),
                        )

        self.add_start(theme_box, False, False, 0)

    def _get_valid_themes(self):
        dirs = ( '/usr/share/sounds',
                 os.path.join(os.path.expanduser("~"), ".sounds"))
        valid = walk_directories(dirs, lambda d:
                    os.path.exists(os.path.join(d, "index.theme")))

        valid.sort()

        return valid

########NEW FILE########
__FILENAME__ = theme
# Ubuntu Tweak - Ubuntu Configuration Tool
#
# Copyright (C) 2007-2011 Tualatrix Chou <tualatrix@gmail.com>
#
# Ubuntu Tweak is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# Ubuntu Tweak is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Ubuntu Tweak; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA

import os
import logging
from gi.repository import Gtk, Gio

from ubuntutweak import system
from ubuntutweak.gui.containers import ListPack, GridPack
from ubuntutweak.modules  import TweakModule
from ubuntutweak.factory import WidgetFactory
from ubuntutweak.utils import theme
from ubuntutweak.utils.tar import ThemeFile
from ubuntutweak.settings.configsettings import ConfigSetting
from ubuntutweak.gui.dialogs import QuestionDialog, ErrorDialog


log = logging.getLogger('theme')


class Theme(TweakModule):
    __title__ = _('Theme')
    __desc__ = _('Set the gtk theme, icon theme, cursor theme and others')
    __icon__ = 'preferences-desktop-theme'
    __category__ = 'appearance'

    utext_icon_theme = _('Icon theme:')
    utext_gtk_theme = _('Gtk theme:')
    utext_cursor_theme = _('Cursor theme:')
    utext_window_theme = _('Window theme:')

    def __init__(self):
        TweakModule.__init__(self)

        valid_themes = theme.get_valid_themes()
        valid_icon_themes = theme.get_valid_icon_themes()
        valid_cursor_themes = theme.get_valid_cursor_themes()
        valid_window_themes = theme.get_valid_window_themes()

        theme_choose_button = Gtk.FileChooserButton()
        theme_choose_button.connect('file-set', self.on_file_set)

        icon_label, self.icon_theme, icon_reset_button = WidgetFactory.create('ComboBox',
                            label=self.utext_icon_theme,
                            key='org.gnome.desktop.interface.icon-theme',
                            backend='gsettings',
                            texts=valid_icon_themes,
                            values=valid_icon_themes,
                            enable_reset=True)

        if system.CODENAME == 'precise':
            window_theme_label, window_theme_combox, window_theme_reset_button = WidgetFactory.create('ComboBox',
                            label=self.utext_window_theme,
                            key='/apps/metacity/general/theme',
                            backend='gconf',
                            texts=valid_window_themes,
                            values=valid_window_themes,
                            enable_reset=True)
        else:
            window_theme_label, window_theme_combox, window_theme_reset_button = WidgetFactory.create('ComboBox',
                            label=self.utext_window_theme,
                            key='org.gnome.desktop.wm.preferences.theme',
                            backend='gsettings',
                            texts=valid_window_themes,
                            values=valid_window_themes,
                            enable_reset=True)


        theme_box = GridPack(
                        WidgetFactory.create('ComboBox',
                            label=self.utext_gtk_theme,
                            key='org.gnome.desktop.interface.gtk-theme',
                            backend='gsettings',
                            texts=valid_themes,
                            values=valid_themes,
                            enable_reset=True),
                        (icon_label, self.icon_theme, icon_reset_button),
                        WidgetFactory.create('ComboBox',
                            label=self.utext_cursor_theme,
                            key='org.gnome.desktop.interface.cursor-theme',
                            backend='gsettings',
                            texts=valid_cursor_themes,
                            values=valid_cursor_themes,
                            enable_reset=True),
                        (window_theme_label, window_theme_combox, window_theme_reset_button),
                        Gtk.Separator(),
                        (Gtk.Label(_('Install theme:')), theme_choose_button),
                        )

        self.add_start(theme_box, False, False, 0)

    def on_file_set(self, widget):
        try:
            tf = ThemeFile(widget.get_filename())
        except Exception, e:
            log.error(e)
            ErrorDialog(message=_('Theme file is invalid')).launch()
        else:
            if tf.install():
                log.debug("Theme installed! Now update the combox")
                valid_icon_themes = theme.get_valid_icon_themes()
                self.icon_theme.update_texts_values_pair(valid_icon_themes, valid_icon_themes)
                dialog = QuestionDialog(title=_('"%s" installed successfully' % tf.theme_name),
                               message=_('Would you like to set your icon theme to "%s" immediatelly?') % tf.theme_name)
                response = dialog.launch()
                if response == Gtk.ResponseType.YES:
                    self.icon_theme.get_setting().set_value(tf.install_name)

    def _get_valid_icon_themes(self):
        # This function is taken from gnome-tweak-tool
        dirs = ( '/usr/share/icons',
                 os.path.join(os.path.expanduser("~"), ".icons"))
        valid = walk_directories(dirs, lambda d:
                    os.path.isdir(d) and \
                        not os.path.exists(os.path.join(d, "cursors")))

        valid.sort()

        return valid

    def _get_valid_themes(self):
        # This function is taken from gnome-tweak-tool
        """ Only shows themes that have variations for gtk+-3 and gtk+-2 """
        dirs = ( '/usr/share/themes',
                 os.path.join(os.path.expanduser("~"), ".themes"))
        valid = walk_directories(dirs, lambda d:
                    os.path.exists(os.path.join(d, "gtk-2.0")) and \
                        os.path.exists(os.path.join(d, "gtk-3.0")))

        valid.sort()

        return valid

    def _get_valid_cursor_themes(self):
        dirs = ( '/usr/share/icons',
                 os.path.join(os.path.expanduser("~"), ".icons"))
        valid = walk_directories(dirs, lambda d:
                    os.path.isdir(d) and \
                        os.path.exists(os.path.join(d, "cursors")))

        valid.sort()

        return valid

    def _get_valid_window_themes(self):
        dirs = ( '/usr/share/themes',
                 os.path.join(os.path.expanduser("~"), ".themes"))
        valid = walk_directories(dirs, lambda d:
                    os.path.exists(os.path.join(d, "metacity-1")))

        valid.sort()

        return valid

########NEW FILE########
__FILENAME__ = unity
# Ubuntu Tweak - Ubuntu Configuration Tool
#
# Copyright (C) 2007-2011 Tualatrix Chou <tualatrix@gmail.com>
#
# Ubuntu Tweak is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# Ubuntu Tweak is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Ubuntu Tweak; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA

import os
import re
import logging

from gi.repository import Gtk

from ubuntutweak import system
from ubuntutweak.utils import icon
from ubuntutweak.gui.containers import GridPack
from ubuntutweak.modules  import TweakModule
from ubuntutweak.factory import WidgetFactory
from ubuntutweak.settings.gconfsettings import GconfSetting

log = logging.getLogger('Unity')


class Unity(TweakModule):
    __title__ = 'Unity'
    __desc__ = _('Tweak the powerful Unity desktop')
    __icon__ = 'plugin-unityshell'
    __category__ = 'desktop'
    __desktop__ = ['ubuntu', 'ubuntu-2d']

    utext_hud = _('HUD:')
    utext_overlay = _('Shortcut hints overlay:')
    utext_launcher_size = _('Launcher icon size:')
    utext_launcher_opacity = _('Launcher opacity:')
    utext_web_apps_integration = _('Web Apps integration:')
    utext_launcher_hide = _('Launcher hide mode:')
    utext_launcher_backlight = _('Launcher icon backlight:')
    utext_device = _('Launcher show devices:')
    utext_show_desktop_icon = _('"Show desktop" icon:')
    utext_launcher_minimize_window = _('Launcher click to minimize app:')
    utext_disable_show_desktop_switcher = _('Disable "Show Desktop" in the switcher:')
    utext_dash_size = _('Dash size:')
    utext_blur_type = _('Blur type:')
    utext_panel_opacity = _('Panel opacity:')
    utext_panel_toggle_max = _('Panel opacity for maximized windows:')
    utext_super_key = _('Super key:')
    utext_fullscreen = _('Full screen dash:')
    utext_compositing_manager = _('Compositing manager:')
    utext_num_workspaces = _('Number of workspaces:')

    def __init__(self):
        TweakModule.__init__(self)

        version_pattern = re.compile('\d.\d+.\d')

        if system.DESKTOP == 'ubuntu':
            hide_texts = (_('Never'), _('Auto Hide'))
            hide_values = (0, 1)

            grid_pack = GridPack(
                        WidgetFactory.create("Switch",
                            label=self.utext_hud,
                            key="unityshell.show_hud",
                            on='<Alt>',
                            off='Disabled',
                            backend="compiz",
                            enable_reset=True),
                        WidgetFactory.create("Switch",
                            label=self.utext_overlay,
                            key="unityshell.shortcut_overlay",
                            backend="compiz",
                            enable_reset=True),
                        WidgetFactory.create("Switch",
                            label=self.utext_web_apps_integration,
                            key="com.canonical.unity.webapps.integration-allowed",
                            backend="gsettings",
                            enable_reset=True),
                        Gtk.Separator(),
                        WidgetFactory.create("Switch",
                            label=self.utext_show_desktop_icon,
                            key="unityshell.show_desktop_icon",
                            backend="compiz",
                            enable_reset=True),
                        WidgetFactory.create("Switch",
                            label=self.utext_disable_show_desktop_switcher,
                            key="unityshell.disable_show_desktop",
                            backend="compiz",
                            enable_reset=True),
                        WidgetFactory.create("Switch",
                            label=self.utext_launcher_minimize_window,
                            key="unityshell.launcher_minimize_window",
                            backend="compiz",
                            enable_reset=True),
                        WidgetFactory.create("Scale",
                            label=self.utext_launcher_size,
                            key="unityshell.icon_size",
                            min=32,
                            max=64,
                            step=16,
                            backend="compiz",
                            enable_reset=True),
                        WidgetFactory.create("Scale",
                            label=self.utext_launcher_opacity,
                            key="unityshell.launcher_opacity",
                            min=0,
                            max=1,
                            step=0.1,
                            digits=2,
                            backend="compiz",
                            enable_reset=True),
                        WidgetFactory.create("ComboBox",
                            label=self.utext_launcher_hide,
                            key="unityshell.launcher_hide_mode",
                            texts=hide_texts,
                            values=hide_values,
                            type=int,
                            backend="compiz",
                            enable_reset=True),
                        WidgetFactory.create("ComboBox",
                            label=self.utext_launcher_backlight,
                            key="unityshell.backlight_mode",
                            texts=(_('Backlight Always On'),
                                 _('Backlight Toggles'),
                                 _('Backlight Always Off'),
                                 _('Edge Illumination Toggles'),
                                 _('Backlight and Edge Illumination Toggles')),
                            values=(0, 1, 2, 3, 4),
                            type=int,
                            backend="compiz",
                            enable_reset=True),
                        WidgetFactory.create("ComboBox",
                            label=self.utext_device,
                            key="unityshell.devices_option",
                            texts=(_('Never'),
                                   _('Only Mounted'),
                                   _('Always')),
                             values=(0, 1, 2),
                             type=int,
                             backend="compiz",
                             enable_reset=True),
                        Gtk.Separator(),
                        WidgetFactory.create("ComboBox",
                             label=self.utext_dash_size,
                             key="com.canonical.Unity.form-factor",
                             texts=(_('Automatic'), _('Desktop'), _('Netbook')),
                             values=('Automatic', 'Desktop', 'Netbook'),
                             backend="gsettings",
                             enable_reset=True),
                        WidgetFactory.create("ComboBox",
                             label=self.utext_blur_type,
                             key="unityshell.dash_blur_experimental",
                             texts=(_('No blur'),
                                    _('Static blur'),
                                    _('Active blur')),
                             values=(0, 1, 2),
                             type=int,
                             backend="compiz",
                             enable_reset=True),
                        WidgetFactory.create("Scale",
                             label=self.utext_panel_opacity,
                             key="unityshell.panel_opacity",
                             min=0, max=1, step=0.1, digits=2,
                             backend="compiz",
                             enable_reset=True),
                        WidgetFactory.create("Switch",
                             label=self.utext_panel_toggle_max,
                             key="unityshell.panel_opacity_maximized_toggle",
                             backend="compiz",
                             reverse=True,
                             enable_reset=True),
                )

            self.add_start(grid_pack, False, False, 0)
        else:
            notes_label = Gtk.Label()
            notes_label.set_property('halign', Gtk.Align.START)
            notes_label.set_markup('<span size="smaller">%s</span>' % \
                    _('Note: you may need to log out to take effect'))
            notes_label._ut_left = 1

            box = GridPack(
                        WidgetFactory.create("Switch",
                            label=self.utext_hud,
                            key="unityshell.show_hud",
                            on='<Alt>',
                            off='Disabled',
                            backend="compiz",
                            enable_reset=True),
                        WidgetFactory.create("Switch",
                                             label=self.utext_fullscreen,
                                             key="com.canonical.Unity2d.Dash.full-screen",
                                             backend="gsettings",
                                             enable_reset=True),
                        WidgetFactory.create("Switch",
                                             label=self.utext_super_key,
                                             key="com.canonical.Unity2d.Launcher.super-key-enable",
                                             backend="gsettings",
                                             enable_reset=True),
                        WidgetFactory.create("ComboBox",
                                             label=self.utext_launcher_hide,
                                             key="com.canonical.Unity2d.Launcher.hide-mode",
                                             texts=(_('Never'), _('Auto Hide'),
                                                    _('Intellihide')),
                                             values=(0, 1, 2),
                                             type=int,
                                             backend="gsettings",
                                             enable_reset=True),
                        Gtk.Separator(),
                        WidgetFactory.create("Switch",
                                             label=self.utext_compositing_manager,
                                             key="/apps/metacity/general/compositing_manager",
                                             backend="gconf",
                                             signal_dict={'notify::active': self.on_compositing_enabled},
                                             enable_reset=True),
                        notes_label,
                        WidgetFactory.create("Scale",
                                             label=self.utext_num_workspaces,
                                             key="/apps/metacity/general/num_workspaces",
                                             backend="gconf",
                                             min=1,
                                             max=36,
                                             step=1,
                                             type=int,
                                             enable_reset=True),
                )

            self.add_start(box, False, False, 0)

    def on_compositing_enabled(self, widget, prop):
         setting = GconfSetting("/apps/metacity/general/compositor_effects")
         setting.set_value(widget.get_active())

########NEW FILE########
__FILENAME__ = window
# Ubuntu Tweak - Ubuntu Configuration Tool
#
# Copyright (C) 2007-2012 Tualatrix Chou <tualatrix@gmail.com>
#
# Ubuntu Tweak is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# Ubuntu Tweak is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Ubuntu Tweak; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA

import re

from gi.repository import GObject, Gtk

from ubuntutweak.modules  import TweakModule
from ubuntutweak.gui.containers import GridPack
from ubuntutweak.factory import WidgetFactory
from ubuntutweak.settings.gconfsettings import GconfSetting
from ubuntutweak.settings.gsettings import GSetting
from ubuntutweak import system


class Window(TweakModule):
    __title__ = _('Window')
    __desc__ = _('Manage Window Manager settings')
    __icon__ = 'preferences-system-windows'
    __category__ = 'desktop'
    __desktop__ = ['ubuntu', 'ubuntu-2d', 'gnome', 'gnome-classic', 'gnome-shell', 'gnome-fallback', 'gnome-fallback-compiz']
    __distro__ = ['precise', 'quantal', 'raring', 'saucy']

    left_default = 'close,minimize,maximize:'
    right_default = ':minimize,maximize,close'

    if system.DESKTOP in ('gnome', 'gnome-shell'):
        config = GSetting(key='org.gnome.shell.overrides.button-layout')
    else:
        if system.CODENAME == 'precise':
            config = GconfSetting(key='/apps/metacity/general/button_layout')
        else:
            config = GSetting(key='org.gnome.desktop.wm.preferences.button-layout')

    utext_window_button = _('Window control button position:')
    utext_only_close_button = _('"Close" button only')
    utext_titlebar_wheel = _('Titlebar mouse wheel action:')
    utext_titlebar_double = _('Titlebar double-click action:')
    utext_titlebar_middle = _('Titlebar middle-click action:')
    utext_titlebar_right = _('Titlebar right-click action:')

    def __init__(self):
        TweakModule.__init__(self, 'window.ui')

        close_pattern = re.compile('\w+')

        only_close_switch = Gtk.Switch()
        only_close_switch.connect('notify::active', self.on_switch_activate)
        button_value = self.config.get_value()
        if len(close_pattern.findall(button_value)) == 1 and 'close' in button_value:
            only_close_switch.set_active(True)
        only_close_label = Gtk.Label(self.utext_only_close_button)

        if system.CODENAME == 'precise' and system.DESKTOP == 'ubuntu':
            box = GridPack(
                        (Gtk.Label(self.utext_window_button),
                         self.place_hbox),
                        (only_close_label, only_close_switch),
                        Gtk.Separator(),
                        WidgetFactory.create('ComboBox',
                            label=self.utext_titlebar_wheel,
                            key='/apps/gwd/mouse_wheel_action',
                            enable_reset=True,
                            backend='gconf',
                            texts=[_('None'), _('Roll up')],
                            values=['none', 'shade']),
                        WidgetFactory.create('ComboBox',
                            label=self.utext_titlebar_double,
                            key='/apps/metacity/general/action_double_click_titlebar',
                            enable_reset=True,
                            backend='gconf',
                            texts=[_('None'), _('Maximize'), \
                                    _('Minimize'), _('Roll up'), \
                                    _('Lower'), _('Menu')],
                            values=['none', 'toggle_maximize', \
                                    'minimize', 'toggle_shade', \
                                    'lower', 'menu']),
                        WidgetFactory.create('ComboBox',
                            label=self.utext_titlebar_middle,
                            key='/apps/metacity/general/action_middle_click_titlebar',
                            enable_reset=True,
                            backend="gconf",
                            texts=[_('None'), _('Maximize'), \
                                   _('Maximize Horizontally'), \
                                   _('Maximize Vertically'), \
                                   _('Minimize'), _('Roll up'), \
                                   _('Lower'), _('Menu')],
                                   values=['none', 'toggle_maximize', \
                                           'toggle_maximize_horizontally', \
                                           'toggle_maximize_vertically', \
                                           'minimize', 'toggle_shade', \
                                           'lower', 'menu']),
                        WidgetFactory.create('ComboBox',
                            label=self.utext_titlebar_right,
                            key='/apps/metacity/general/action_right_click_titlebar',
                            enable_reset=True,
                            backend="gconf",
                            texts=[_('None'), _('Maximize'), \
                                    _('Maximize Horizontally'), \
                                    _('Maximize Vertically'), \
                                    _('Minimize'), _('Roll up'), \
                                    _('Lower'), _('Menu')],
                            values=['none', 'toggle_maximize', \
                                    'toggle_maximize_horizontally', \
                                    'toggle_maximize_vertically', \
                                    'minimize', 'toggle_shade', \
                                    'lower', 'menu']),
                    )

            self.add_start(box)
        else:
            box = GridPack(
                        (Gtk.Label(self.utext_window_button),
                         self.place_hbox),
                        (only_close_label, only_close_switch),
                        Gtk.Separator(),
                        WidgetFactory.create('ComboBox',
                            label=self.utext_titlebar_wheel,
                            key='org.compiz.gwd.mouse-wheel-action',
                            enable_reset=True,
                            backend='gsettings',
                            texts=[_('None'), _('Roll up')],
                            values=['none', 'shade']),
                        WidgetFactory.create('ComboBox',
                            label=self.utext_titlebar_double,
                            key='org.gnome.desktop.wm.preferences.action-double-click-titlebar',
                            enable_reset=True,
                            backend='gsettings',
                            texts=[_('None'), _('Maximize'), \
                                   _('Minimize'), _('Roll up'), \
                                   _('Lower'), _('Menu')],
                            values=['none', 'toggle-maximize', \
                                    'minimize', 'toggle-shade', \
                                    'lower', 'menu']),
                        WidgetFactory.create('ComboBox',
                            label=self.utext_titlebar_middle,
                            key='org.gnome.desktop.wm.preferences.action-middle-click-titlebar',
                            enable_reset=True,
                            backend="gsettings",
                            texts=[_('None'), _('Maximize'), \
                                   _('Minimize'), _('Roll up'), \
                                   _('Lower'), _('Menu')],
                            values=['none', 'toggle-maximize', \
                                    'minimize', 'toggle-shade', \
                                    'lower', 'menu']),
                        WidgetFactory.create('ComboBox',
                            label=self.utext_titlebar_right,
                            key='org.gnome.desktop.wm.preferences.action-right-click-titlebar',
                            enable_reset=True,
                            backend="gsettings",
                            texts=[_('None'), _('Maximize'), \
                                   _('Minimize'), _('Roll up'), \
                                   _('Lower'), _('Menu')],
                            values=['none', 'toggle-maximize', \
                                    'minimize', 'toggle-shade', \
                                    'lower', 'menu']),
                        )

            self.add_start(box)

    def on_switch_activate(self, widget, value):
        if widget.get_active():
            self.left_default = 'close:'
            self.right_default = ':close'
        else:
            self.left_default = 'close,minimize,maximize:'
            self.right_default = ':minimize,maximize,close'

        self.on_right_radio_toggled(self.right_radio)
        self.on_left_radio_toggled(self.left_radio)

    def on_right_radio_toggled(self, widget):
        if widget.get_active():
            self.config.set_value(self.right_default)

    def on_left_radio_toggled(self, widget):
        if widget.get_active():
            self.config.set_value(self.left_default)

########NEW FILE########
__FILENAME__ = workarounds
# coding: utf-8
# Ubuntu Tweak - Ubuntu Configuration Tool
#
# Copyright (C) 2007-2012 Tualatrix Chou <tualatrix@gmail.com>
#
# Ubuntu Tweak is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# Ubuntu Tweak is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Ubuntu Tweak; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA

import os
import logging

from gi.repository import Gtk

from ubuntutweak.modules  import TweakModule
from ubuntutweak.policykit.dbusproxy import proxy
from ubuntutweak.gui.containers import GridPack
from ubuntutweak.factory import WidgetFactory

log = logging.getLogger('Workarounds')

class Workarounds(TweakModule):
    __title__ = _('Workarounds')
    __desc__ = _('The workarounds to fix some problems')
    __icon__ = 'application-octet-stream'
    __category__ = 'system'

    utext_fix_theme = _('Fix the appearance of themes when granted root privileges:')
    utext_chinese_gedit = _("Auto detect text encoding for Simplified Chinese in Gedit:")

    ROOT_THEMES = '/root/.themes'
    ROOT_ICONS = '/root/.icons'

    def __init__(self):
        TweakModule.__init__(self)

        self.fix_theme_button = Gtk.Switch()
        self.fix_theme_label = Gtk.Label(self.utext_fix_theme)
        self.set_fix_theme_button_status()

        self.fix_theme_button.connect('notify::active', self.on_fix_theme_button_toggled)

        box = GridPack(
                (self.fix_theme_label, self.fix_theme_button),
                WidgetFactory.create("Switch",
                                     label=self.utext_chinese_gedit,
                                     key="org.gnome.gedit.preferences.encodings.auto-detected",
                                     on=['GB18030', 'UTF-8', 'CURRENT', 'ISO-8859-15', 'UTF-16'],
                                     off=['UTF-8', 'CURRENT', 'ISO-8859-15', 'UTF-16'],
                                     backend="gsettings",
                                     enable_reset=True)
            )
        self.add_start(box)

    def on_fix_theme_button_toggled(self, widget, *args):
        try:
            if widget.get_active():
                proxy.link_file(os.path.expanduser('~/.themes'), self.ROOT_THEMES)
                proxy.link_file(os.path.expanduser('~/.icons'), self.ROOT_ICONS)
            else:
                proxy.unlink_file(self.ROOT_THEMES)
                proxy.unlink_file(self.ROOT_ICONS)
                self.set_fix_theme_button_status()
        except Exception, e:
            log.error(e)
            self.set_fix_theme_button_status()

    def set_fix_theme_button_status(self):
        if proxy.is_exists(self.ROOT_THEMES) and proxy.is_exists(self.ROOT_ICONS):
            self.fix_theme_button.set_active(True)
        else:
            self.fix_theme_button.set_active(False)

########NEW FILE########
__FILENAME__ = workspace
# Ubuntu Tweak - Ubuntu Configuration Tool
#
# Copyright (C) 2007-2012 Tualatrix Chou <tualatrix@gmail.com>
#
# Ubuntu Tweak is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# Ubuntu Tweak is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Ubuntu Tweak; if not, write to the Free Software Foundation, Inc.,
# 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA

import os
import logging

from gi.repository import GObject, Gtk, GdkPixbuf

from ubuntutweak.utils import icon
from ubuntutweak.gui.treeviews import get_local_path
from ubuntutweak.modules  import TweakModule
from ubuntutweak.settings.gsettings import GSetting
from ubuntutweak.gui.containers import GridPack
from ubuntutweak.factory import WidgetFactory
from ubuntutweak.settings.compizsettings import CompizPlugin, CompizSetting

log = logging.getLogger('Workspace')


class EdgeComboBox(Gtk.ComboBox):
    edge_settings = (
        ('expo', 'expo_edge', _('Show Workspaces')),
        ('scale', 'initiate_all_edge', _('Show Windows')),
        ('core', 'show_desktop_edge', _('Show Desktop')),
    )

    __gsignals__ = {
        'edge_changed': (GObject.SignalFlags.RUN_FIRST,
                         None,
                         (GObject.TYPE_STRING,))
    }

    (COLUMN_PLUGIN,
     COLUMN_KEY,
     COLUMN_TEXT) = range(3)

    edge = GObject.property(type=str, default='')
    old_plugin = GObject.property(type=str, default='')
    old_key = GObject.property(type=str, default='')
    max_index = GObject.property(type=int, default=0)

    def __init__(self, edge):
        '''
        edge will be: TopLeft, BottomLeft
        '''
        GObject.GObject.__init__(self)

        model = Gtk.ListStore(GObject.TYPE_STRING,
                              GObject.TYPE_STRING,
                              GObject.TYPE_STRING)
        renderer = Gtk.CellRendererText()
        self.pack_start(renderer, False)
        self.add_attribute(renderer, 'text', self.COLUMN_TEXT)
        self.set_model(model)

        self.edge = edge
        enable = False
        count = 0

        for name, key, text in self.edge_settings:
            if CompizPlugin.is_available(name, key):
                model.append((name, key, text))

                setting = CompizSetting("%s.%s" % (name, key))
                log.debug("CompizSetting: %s, value: %s, key: %s" % \
                        (name, setting.get_value(), edge))

                if setting.get_value() == edge:
                    enable = True
                    self.old_plugin = name
                    self.old_key = key
                    self.set_active(count)
                    log.info("The %s is holding %s" % (edge, name))

                count = count + 1

        model.append(('', '', '-'))

        if not enable:
            self.set_active(count)
        self.max_index = count
        self.connect("changed", self.on_changed)

    def on_changed(self, widget):
        plugin = self.get_current_plugin()
        key = self.get_current_key()
        log.debug("ComboBox changed: from %s to %s" % (self.old_plugin, plugin))

        if self.old_plugin:
            for name, key, text in self.edge_settings:
                if name == self.old_plugin:
                    log.debug('%s has to unset (%s)' % (name, key))
                    setting = CompizSetting("%s.%s" % (name, key))
                    setting.set_value('')
                    break

        self.old_plugin = plugin
        self.old_key = key

        log.debug('%s changed to "%s"' % (widget.edge, plugin))
        self.emit('edge_changed', plugin)

    def set_to_none(self):
        self.handler_block_by_func(self.on_changed)
        log.debug("on_edge_changed: from %s to none" % self.get_current_plugin())
        self.set_active(self.max_index)
        self.handler_unblock_by_func(self.on_changed)

    def get_current_plugin(self):
        iter = self.get_active_iter()
        model = self.get_model()

        return model.get_value(iter, self.COLUMN_PLUGIN)

    def get_current_key(self):
        iter = self.get_active_iter()
        model = self.get_model()

        return model.get_value(iter, self.COLUMN_KEY)


class Workspace(TweakModule):
    __title__ = _('Workspace')
    __desc__ = _('Workspace size and screen edge action settings')
    __icon__ = 'workspace-switcher'
    __category__ = 'desktop'
    __desktop__ = ['ubuntu']

    utext_edge_delay = _('Edge trigger delay (ms):')
    utext_hsize = _('Horizontal workspace:')
    utext_vsize = _('Vertical workspace:')

    def __init__(self):
        TweakModule.__init__(self)

        self.is_arabic = os.getenv('LANG').startswith('ar')

        hbox = Gtk.HBox(spacing=12)
        hbox.pack_start(self.create_edge_setting(), True, False, 0)
        self.add_start(hbox, False, False, 0)

        self.add_start(Gtk.Separator(), False, False, 6)

        grid_pack = GridPack(
                WidgetFactory.create("Scale",
                             label=self.utext_edge_delay,
                             key="core.edge_delay",
                             backend="compiz",
                             min=0,
                             max=1000,
                             step=50,
                             enable_reset=True),
                WidgetFactory.create("Scale",
                             label=self.utext_hsize,
                             key="core.hsize",
                             backend="compiz",
                             min=1,
                             max=16,
                             step=1,
                             enable_reset=True),
                WidgetFactory.create("Scale",
                             label=self.utext_vsize,
                             key="core.vsize",
                             backend="compiz",
                             min=1,
                             max=16,
                             step=1,
                             enable_reset=True),
                )

        self.add_start(grid_pack, False, False, 0)

    def create_edge_setting(self):
        hbox = Gtk.HBox(spacing=12)

        left_vbox = Gtk.VBox(spacing=6)

        self.TopLeft = EdgeComboBox("TopLeft")
        left_vbox.pack_start(self.TopLeft, False, False, 0)

        self.BottomLeft = EdgeComboBox("BottomLeft")
        left_vbox.pack_end(self.BottomLeft, False, False, 0)

        wallpaper = get_local_path(GSetting('org.gnome.desktop.background.picture-uri').get_value())

        if wallpaper:
            try:
                pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_size(wallpaper, 160, 100)
            except GObject.GError:
                pixbuf = icon.get_from_name('ubuntu-tweak', size=128)
        else:
            pixbuf = icon.get_from_name('ubuntu-tweak', size=128)

        image = Gtk.Image.new_from_pixbuf(pixbuf)

        right_vbox = Gtk.VBox(spacing=6)

        self.TopRight = EdgeComboBox("TopRight")
        right_vbox.pack_start(self.TopRight, False, False, 0)

        self.BottomRight = EdgeComboBox("BottomRight")
        right_vbox.pack_end(self.BottomRight, False, False, 0)

        if self.is_arabic:
            hbox.pack_start(right_vbox, False, False, 0)
            hbox.pack_start(image, False, False, 0)
            hbox.pack_start(left_vbox, False, False, 0)
        else:
            hbox.pack_start(left_vbox, False, False, 0)
            hbox.pack_start(image, False, False, 0)
            hbox.pack_start(right_vbox, False, False, 0)

        for edge in ('TopLeft', 'TopRight', 'BottomLeft', 'BottomRight'):
            getattr(self, edge).connect('edge_changed', self.on_edge_changed)
        return hbox

    def on_edge_changed(self, widget, plugin):
        edges = ['TopLeft', 'TopRight', 'BottomLeft', 'BottomRight']
        edges.remove(widget.edge)

        if plugin:
            for edge in edges:
                edge_combobox = getattr(self, edge)

                if edge_combobox.get_current_plugin() == plugin:
                    edge_combobox.set_to_none()
                    break

            setting = CompizSetting("%s.%s" % (widget.get_current_plugin(),
                widget.get_current_key()))
            setting.set_value(widget.edge)

########NEW FILE########
__FILENAME__ = icon
import os
import random
import logging

from gi.repository import Gtk, Gdk, Gio, GdkPixbuf

log = logging.getLogger("utils.icon")

icontheme = Gtk.IconTheme.get_default()
icontheme.append_search_path('/usr/share/ccsm/icons')

DEFAULT_SIZE = 24

def get_from_name(name='gtk-execute',
                  alter='gtk-execute',
                  size=DEFAULT_SIZE,
                  force_reload=False,
                  only_path=False):
    pixbuf = None

    if force_reload:
        global icontheme
        icontheme = Gtk.IconTheme.get_default()

    if only_path:
        path = icontheme.lookup_icon(name, size, Gtk.IconLookupFlags.USE_BUILTIN)
        return path

    try:
        pixbuf = icontheme.load_icon(name, size, 0)
    except Exception, e:
        log.warning(e)
        # if the alter name isn't here, so use random icon

        while not pixbuf:
            try:
                pixbuf = icontheme.load_icon(alter, size, 0)
            except Exception, e:
                log.error(e)
                icons = icontheme.list_icons(None)
                alter = icons[random.randint(0, len(icons) - 1)]

    if pixbuf.get_height() != size:
        return pixbuf.scale_simple(size, size, GdkPixbuf.InterpType.BILINEAR)

    return pixbuf

def get_from_list(list, size=DEFAULT_SIZE):
    pixbuf = None
    for name in list:
        try:
            pixbuf = icontheme.load_icon(name,
                                         size,
                                         Gtk.IconLookupFlags.USE_BUILTIN)
        except Exception, e:
            log.warning('get_from_list for %s failed, try next' % name)
            continue

    return pixbuf or get_from_name('application-x-executable', size=size)

def get_from_mime_type(mime, size=DEFAULT_SIZE):
    try:
        gicon = Gio.content_type_get_icon(mime)

        return get_from_list(gicon.get_names(), size=size)
    except Exception, e:
        log.error('get_from_mime_type failed: %s' % e)
        return get_from_name(size=size)

    return pixbuf

def get_from_file(file, size=DEFAULT_SIZE, only_path=False):
    try:
        return GdkPixbuf.Pixbuf.new_from_file_at_size(file, size, size)
    except Exception, e:
        log.error('get_from_file failed: %s' % e)
        return get_from_name(size=size, only_path=only_path)

def get_from_app(app, size=DEFAULT_SIZE):
    try:
        gicon = app.get_icon()
        pixbuf = None

        if gicon:
            if isinstance(gicon, Gio.ThemedIcon):
                return get_from_list(gicon.get_names(), size=size)
            elif isinstance(gicon, Gio.FileIcon):
                file = app.get_icon().get_file().get_path()
                return get_from_file(file, size)
        if not pixbuf:
            return get_from_name('application-x-executable', size=size)
    except Exception, e:
        log.error('get_from_app failed: %s' % e)
        return get_from_name(size=size)

def guess_from_path(filepath, size=DEFAULT_SIZE):
    if os.path.isdir(filepath):
        return get_from_name('folder', size)

    try:
        mime_type, result = Gio.content_type_guess(filepath, open(filepath).read(10))
        return get_from_mime_type(mime_type, size)
    except Exception, e:
        log.error('guess_from_path failed: %s' % e)
        return get_from_name(size=size)

if __name__ == '__main__':
    print get_from_name('ok', alter='ko')

########NEW FILE########
__FILENAME__ = package
import logging

import apt
import apt_pkg
import aptdaemon.client
import aptdaemon.errors

from aptdaemon.enums import *
from aptdaemon.gtk3widgets import AptErrorDialog, AptProgressDialog, AptConfirmDialog

from gi.repository import Gtk, Gdk

from defer import inline_callbacks, return_value

from ubuntutweak.gui.gtk import post_ui, unset_busy
from ubuntutweak.common.debug import log_func

log = logging.getLogger('package')


class NewAptProgressDialog(AptProgressDialog):
    def run(self, attach=False, close_on_finished=True, show_error=True,
            reply_handler=None, error_handler=None):
        """Run the transaction and show the progress in the dialog.

        Keyword arguments:
        attach -- do not start the transaction but instead only monitor
                  an already running one
        close_on_finished -- if the dialog should be closed when the
                  transaction is complete
        show_error -- show a dialog with the error message
        """
        try:
            self._run(attach, close_on_finished, show_error, error_handler)
        except Exception, error:
            if error_handler:
                error_handler(error)
            else:
                raise
        if reply_handler:
            reply_handler()

    @inline_callbacks
    def _run(self, attach, close_on_finished, show_error, error_handler):
        parent = self.get_transient_for()
        sig = self._transaction.connect("finished", self._on_finished,
                                        close_on_finished, show_error)
        self._signals.append(sig)
        if attach:
            yield self._transaction.attach()
        else:
            if self.debconf:
                yield self._transaction.set_debconf_frontend("gnome")
            try:
                deferred = self._transaction.run()
                yield deferred
            except Exception, error:
                error_handler(error)
                self._transaction.emit('finished', '')
                yield deferred
        self.show_all()

    def _on_finished(self, transaction, status, close, show_error):
        if close:
            self.hide()
            if status == EXIT_FAILED and show_error:
                Gdk.threads_enter()
                err_dia = AptErrorDialog(self._transaction.error, self)
                err_dia.run()
                err_dia.hide()
                Gdk.threads_leave()
        self.emit("finished")


class AptWorker(object):
    cache = None

    @log_func(log)
    def __init__(self, parent,
                 finish_handler=None, error_handler=None,data=None):
        '''
        finish_handler: must take three parameter
        '''
        self.parent = parent
        self.data = data
        self.finish_handler = finish_handler
        if error_handler:
            self._on_error = error_handler
        self.ac = aptdaemon.client.AptClient()

    @log_func(log)
    def _simulate_trans(self, trans):
        trans.simulate(reply_handler=lambda: self._confirm_deps(trans),
                       error_handler=self._on_error)

    @post_ui
    def _confirm_deps(self, trans):
        if [pkgs for pkgs in trans.dependencies if pkgs]:
            dia = AptConfirmDialog(trans, parent=self.parent)
            res = dia.run()
            dia.hide()
            if res != Gtk.ResponseType.OK:
                log.debug("Response is: %s" % res)
                if self.finish_handler:
                    log.debug("Finish_handler...")
                    self.finish_handler(trans, 0, self.data)
                return
        self._run_transaction(trans)

    @log_func(log)
    def _run_transaction(self, transaction):
        dia = NewAptProgressDialog(transaction, parent=self.parent)
        if self.finish_handler:
            log.debug("Connect to finish_handler...")
            transaction.connect('finished', self.finish_handler, self.data)

        dia.run(close_on_finished=True, show_error=True,
                reply_handler=lambda: True,
                error_handler=self._on_error)

    @post_ui
    def _on_error(self, error):
        try:
            raise error
        except aptdaemon.errors.NotAuthorizedError:
            log.debug("aptdaemon.errors.NotAuthorizedError")
            # Silently ignore auth failures
            return
        except aptdaemon.errors.TransactionFailed, error:
            log.error("TransactionFailed: %s" % error)
        except Exception, error:
            log.error("TransactionFailed with unknown error: %s" % error)
            error = aptdaemon.errors.TransactionFailed(ERROR_UNKNOWN,
                                                       str(error))
        dia = AptErrorDialog(error)
        dia.run()
        dia.hide()

    def update_cache(self, *args):
        return self.ac.update_cache(reply_handler=self._run_transaction,
                                    error_handler=self._on_error)

    @log_func(log)
    def install_packages(self, packages, *args):
        self.ac.install_packages(packages,
                                 reply_handler=self._simulate_trans,
                                 error_handler=self._on_error)

    @log_func(log)
    def remove_packages(self, packages, *args):
        self.ac.remove_packages(packages,
                                reply_handler=self._simulate_trans,
                                error_handler=self._on_error)

    @log_func(log)
    def downgrade_packages(self, packages, *args):
        self.ac.commit_packages([], [], [], [], [], packages,
                                reply_handler=self._simulate_trans,
                                error_handler=self._on_error)

    @classmethod
    def get_cache(self):
        try:
            self.update_apt_cache()
        except Exception, e:
            self.is_apt_broken = True
            self.apt_broken_message = e
            log.error("Error happened when get_cache(): %s" % str(e))
        finally:
            return self.cache

    @classmethod
    def update_apt_cache(self, init=False):
        '''if init is true, force to update, or it will update only once'''
        if init or not getattr(self, 'cache'):
            apt_pkg.init()
            self.cache = apt.Cache()

########NEW FILE########
__FILENAME__ = parser
import os
import json
import urllib

from ubuntutweak.common import consts

class Parser(dict):
    def __init__(self, file, key):
        try:
            self.__data = json.loads(open(file).read())
            self.init_items(key)
        except:
            self.is_available = False
        else:
            self.is_available = True

    def get_data(self):
        return self.__data

    def init_items(self, key):
        for item in self.__data:
            item['fields']['id'] = item['pk']
            self[item['fields'][key]] = item['fields']

    def get_by_lang(self, key, field):
        value = self[key][field]
        if consts.LANG in value.keys():
            return value[consts.LANG]
        else:
            return value['raw']

########NEW FILE########
__FILENAME__ = ppa
import os
import glob
import logging

log = logging.getLogger('utils.ppa')

PPA_URL = 'ppa.launchpad.net'

def is_ppa(url):
    return PPA_URL in url

def get_list_name(url):
    if os.uname()[-1] == 'x86_64':
        arch = 'amd64'
    else:
        arch = 'i386'

    section = url.split('/')
    name = '/var/lib/apt/lists/ppa.launchpad.net_%s_%s_*%s_Packages' % (section[3], section[4], arch)
    log.debug("lists name: %s" % name)
    names = glob.glob(name)
    log.debug("lists names: %s" % names)
    if len(names) == 1:
        return names[0]
    else:
        return ''

def get_basename(url):
    section = url.split('/')
    return '%s/%s' % (section[3], section[4])

def get_short_name(url):
    return 'ppa:%s' % get_basename(url)

def get_long_name(url):
    basename = get_basename(url)

    return '<b>%s</b>\nppa:%s' % (basename, basename)

def get_homepage(url):
    section = url.split('/')
    return 'https://launchpad.net/~%s/+archive/%s' % (section[3], section[4])

def get_source_file_name(url):
    section = url.split('/')
    return '%s-%s' % (section[3], section[4])

def get_ppa_origin_name(url):
    section = url.split('/')
    # Due to the policy of ppa orgin naming, if an ppa is end with "ppa", so ignore it
    if section[4] == 'ppa':
        return 'LP-PPA-%s' % section[3]
    else:
        return 'LP-PPA-%s-%s' % (section[3], section[4])

########NEW FILE########
__FILENAME__ = tar
import os
import logging
import tarfile

from ubuntutweak.settings.configsettings import ConfigSetting

log = logging.getLogger("tar")

class TarFile:
    def __init__(self, path):
        if path.endswith('tar.gz'):
            mode = 'r:gz'
        elif path.endswith('tar.bz2'):
            mode = 'r:bz2'
        else:
            #TODO support zip
            mode = 'r:gz'

        try:
            self._tarfile = tarfile.open(path, mode)
            self._error = ''
        except Exception, e:
            self._error = e
            log.error(e)

    def is_valid(self):
        return not bool(self._error)

    def extract(self, target):
        self._tarfile.extractall(target)

    def get_root_name(self):
        names = self._tarfile.getnames()
        for name in names:
            if '/' not in name:
                return name
        return ''


class ThemeFile(TarFile):
    def __init__(self, path):
        TarFile.__init__(self, path)

        self._path = path
        self._index_file = ''
        self._to_extract_dir = ''

        self.theme_name = ''
        self.theme_type = ''
        self.install_name = ''

        if not self.is_valid():
            raise Exception('Invalid file')

        self._parse_theme()

        if not self.is_theme():
            raise Exception('Invalid theme file')

    def _parse_theme(self):
        names = self._tarfile.getnames()
        for name in names:
            if 'index.theme' in name:
                #TODO support multi themes, in the future, it's better to only install from deb
                self._index_file = name
                break

        if self._index_file:
            log.debug("the index file is; %s" % self._index_file)
            self._tarfile.extract(self._index_file, '/tmp')
            cs = ConfigSetting('/tmp/%s::Icon Theme#name' % self._index_file)
            self.theme_name = cs.get_value()

            if '/' in self._index_file and not './' in self._index_file:
                self._to_extract_dir = os.path.dirname(self._index_file)
                log.debug("Because of index file: %s, the extra dir will be: %s" % (self._index_file, self._to_extract_dir))
                self.install_name = os.path.basename(os.path.dirname(self._index_file))
            else:
                #TODO improve
                self.install_name = os.path.basename(self._path).split('.')[0]

    def is_theme(self):
        return self.is_valid() and self.install_name != ''

    def is_installed():
        #TODO
        pass

    def install(self):
        #TODO may not be icon
        if self._to_extract_dir:
            self._tarfile.extractall(os.path.expanduser('~/.icons'))
        else:
            new_dir = os.path.expanduser('~/.icons/%s' % self.install_name)
            os.makedirs(new_dir)
            self._tarfile.extractall(new_dir)

        return True

########NEW FILE########
__FILENAME__ = theme
import os

from ubuntutweak.utils import walk_directories

def get_valid_icon_themes():
    # This function is taken from gnome-tweak-tool
    dirs = ( '/usr/share/icons',
             os.path.join(os.path.expanduser("~"), ".icons"))
    valid = walk_directories(dirs, lambda d:
                os.path.isdir(d) and \
                    not os.path.exists(os.path.join(d, "cursors")))

    valid.sort()

    return valid

def get_valid_themes():
    # This function is taken from gnome-tweak-tool
    """ Only shows themes that have variations for gtk+-3 and gtk+-2 """
    dirs = ( '/usr/share/themes',
             os.path.join(os.path.expanduser("~"), ".themes"))
    valid = walk_directories(dirs, lambda d:
                os.path.exists(os.path.join(d, "gtk-2.0")) and \
                    os.path.exists(os.path.join(d, "gtk-3.0")))

    valid.sort()

    return valid

def get_valid_cursor_themes():
    dirs = ( '/usr/share/icons',
             os.path.join(os.path.expanduser("~"), ".icons"))
    valid = walk_directories(dirs, lambda d:
                os.path.isdir(d) and \
                    os.path.exists(os.path.join(d, "cursors")))

    valid.sort()

    return valid

def get_valid_window_themes():
    dirs = ( '/usr/share/themes',
             os.path.join(os.path.expanduser("~"), ".themes"))
    valid = walk_directories(dirs, lambda d:
                os.path.exists(os.path.join(d, "metacity-1")))

    valid.sort()

    return valid

########NEW FILE########
