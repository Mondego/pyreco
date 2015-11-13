__FILENAME__ = exceptions
__all__ = ['DirectoryCreationError', 'FileNotFoundError',
        'XfluxError', 'MethodUnavailableError']

class Error(Exception):
    pass

class DirectoryCreationError(Error):
    pass

class FileNotFoundError(Error):
    pass

class XfluxError(Error):
    pass

class MethodUnavailableError(Error):
    pass


########NEW FILE########
__FILENAME__ = fluxapp
#!/usr/bin/python2.7

from fluxgui import fluxcontroller, settings
from fluxgui.exceptions import MethodUnavailableError
import gtk
import gtk.glade
import appindicator
import sys, os
import signal
import errno

class FluxGUI(object):
    """
    FluxGUI initializes/destroys the app
    """
    def __init__(self):
        self.pidfile = os.path.expanduser("~/.fluxgui.pid")
        self.check_pid()
        try:
            self.settings = settings.Settings()
            self.xflux_controller = fluxcontroller.FluxController(self.settings)
            self.indicator = Indicator(self, self.xflux_controller)
            self.preferences = Preferences(self.settings,
                    self.xflux_controller)
            self.xflux_controller.start()

        except Exception as e:
            print e
            print "Critical error. Exiting."
            self.exit(1)

    def __del__(self):
        self.exit()

    def open_preferences(self):
        self.preferences.show()

    def signal_exit(self, signum, frame):
        print 'Recieved signal: ', signum
        print 'Quitting...'
        self.exit()

    def exit(self, code=0):
        try:
            self.xflux_controller.stop()
        except MethodUnavailableError:
            pass
        os.unlink(self.pidfile)
        gtk.main_quit()
        sys.exit(code)

    def run(self):
        gtk.main()

    def check_pid(self):
        pid = os.getpid()

        running = False # Innocent...
        if os.path.isfile(self.pidfile):
            try:
                oldpid = int(open(self.pidfile).readline().rstrip())
                try:
                    os.kill(oldpid, 0)
                    running = True # ...until proven guilty
                except OSError as err:
                    if err.errno == errno.ESRCH:
                        # OSError: [Errno 3] No such process
                        print "stale pidfile, old pid: ", oldpid
            except ValueError:
                # Corrupt pidfile, empty or not an int on first line
                pass
        if running:
            print "fluxgui is already running, exiting"
            sys.exit()
        else:
            file(self.pidfile, 'w').write("%d\n" % pid)

class Indicator(object):
    """
    Information and methods related to the indicator applet.
    Executes FluxController and FluxGUI methods.
    """

    def __init__(self, fluxgui, xflux_controller):
        self.fluxgui = fluxgui
        self.xflux_controller = xflux_controller
        self.indicator = appindicator.Indicator(
          "fluxgui-indicator",
          "fluxgui",
          appindicator.CATEGORY_APPLICATION_STATUS)

        self.setup_indicator()

    def setup_indicator(self):
        self.indicator.set_status(appindicator.STATUS_ACTIVE)

        # Check for special Ubuntu themes. copied from lookit

        try:
            theme = \
                gtk.gdk.screen_get_default().get_setting('gtk-icon-theme-name')
        except:
            self.indicator.set_icon('fluxgui')
        else:
            if theme == 'ubuntu-mono-dark':
                self.indicator.set_icon('fluxgui-dark')
            elif theme == 'ubuntu-mono-light':
                self.indicator.set_icon('fluxgui-light')
            else:
                self.indicator.set_icon('fluxgui')

        self.indicator.set_menu(self.create_menu())

    def create_menu(self):
        menu = gtk.Menu()

        self.add_menu_item("_Pause f.lux", self._toggle_pause,
                menu, MenuItem=gtk.CheckMenuItem)
        self.add_menu_item("Prefere_nces", self._open_preferences, menu)
        self.add_menu_separator(menu)
        self.add_menu_item("Quit", self._quit, menu)

        return menu

    def add_menu_item(self, label, handler, menu,
            event="activate", MenuItem=gtk.MenuItem, show=True):
        item = MenuItem(label)
        item.connect(event, handler)
        menu.append(item)
        if show:
            item.show()
        return item

    def add_menu_separator(self, menu, show=True):
        item = gtk.SeparatorMenuItem()
        menu.append(item)
        if show:
            item.show()

    def _toggle_pause(self, item):
        self.xflux_controller.toggle_pause()

    def _open_preferences(self, item):
        self.fluxgui.open_preferences()

    def _quit(self, item):
        self.fluxgui.exit()

class Preferences(object):
    """
    Information and methods related to the preferences window.
    Executes FluxController methods and gets data from Settings.

    """

    temperatureKeys = {
                0:  '2700',
                1:  '3400',
                2:  '4200',
                3:  '5000',
                4:  '6500',
                "off": '6500',
    }

    def temperature_to_key(self, temperature):
        for i, t in self.temperatureKeys.items():
            if t == temperature:
                return i

    def connect_widget(self, widget_name, connect_target=None,
            connect_event="activate"):
        widget = self.wTree.get_widget(widget_name)
        if connect_target:
            widget.connect(connect_event, connect_target)
        return widget


    def __init__(self, settings, xflux_controller):
        self.settings = settings
        self.xflux_controller = xflux_controller

        self.gladefile = os.path.join(os.path.dirname(os.path.dirname(
          os.path.realpath(__file__))), "fluxgui/preferences.glade")
        self.wTree = gtk.glade.XML(self.gladefile)

        self.window = self.connect_widget("window1", self.delete_event,
                connect_event="destroy")
        self.latsetting = self.connect_widget("entryLatitude",
                self.delete_event)
        self.lonsetting = self.connect_widget("entryLongitude",
                self.delete_event)
        self.zipsetting = self.connect_widget("entryZipcode",
                self.delete_event)
        self.colsetting = self.connect_widget("comboColor")
        self.colordisplay = self.connect_widget("labelCurrentColorTemperature")
        self.previewbutton = self.connect_widget("buttonPreview",
                self.preview_click_event, "clicked")
        self.closebutton = self.connect_widget("buttonClose",
                self.delete_event, "clicked")
        self.autostart = self.connect_widget("checkAutostart")

        if (self.settings.latitude is "" and self.settings.zipcode is "")\
                or not self.settings.has_set_prefs:
            self.show()
            self.display_no_zipcode_or_latitude_error_box()

    def show(self):

        self.latsetting.set_text(self.settings.latitude)
        self.lonsetting.set_text(self.settings.longitude)
        self.zipsetting.set_text(self.settings.zipcode)
        self.colsetting.set_active(self.temperature_to_key(self.settings.color))
        self.colordisplay.set_text("Current color temperature: %sK"
                                    % (self.settings.color))
        if self.settings.autostart:
            self.autostart.set_active(True)
        else:
            self.autostart.set_active(False)

        self.window.show()

    def display_no_zipcode_or_latitude_error_box(self):
        md = gtk.MessageDialog(self.window,
                gtk.DIALOG_DESTROY_WITH_PARENT, gtk.MESSAGE_INFO,
                gtk.BUTTONS_OK, "The f.lux indicator applet needs to know " +
                "your latitude or zipcode to run. " +
                "Please fill either of them in on the preferences screen "+
                "and click 'Close'.")
        md.set_title("f.lux indicator applet")
        md.run()
        md.destroy()

    def preview_click_event(self, widget, data=None):
        colsetting_temperature = self.temperatureKeys[
            self.colsetting.get_active()]
        self.xflux_controller.preview_color(colsetting_temperature)

    def delete_event(self, widget, data=None):
        if self.settings.latitude != self.latsetting.get_text():
            self.xflux_controller.set_xflux_latitude(
                    self.latsetting.get_text())

        if self.settings.longitude != self.lonsetting.get_text():
            self.xflux_controller.set_xflux_longitude(
                    self.lonsetting.get_text())

        if self.settings.zipcode != self.zipsetting.get_text():
            self.xflux_controller.set_xflux_zipcode(
                    self.zipsetting.get_text())

        colsetting_temperature = self.temperatureKeys[
                self.colsetting.get_active()]
        if self.settings.color != colsetting_temperature:
            self.xflux_controller.color = colsetting_temperature

        if self.autostart.get_active():
            self.xflux_controller.set_autostart(True)
        else:
            self.xflux_controller.set_autostart(False)
        if self.latsetting.get_text() == "" \
                and self.zipsetting.get_text() == "":
            self.display_no_zipcode_or_latitude_error_box()
            return True

        self.window.hide()
        return False


if __name__ == '__main__':
    try:
        app = FluxGUI()
        signal.signal(signal.SIGTERM, app.signal_exit)
        app.run()
    except KeyboardInterrupt:
        app.exit()


########NEW FILE########
__FILENAME__ = fluxcontroller
from fluxgui import xfluxcontroller

class FluxController(xfluxcontroller.XfluxController):
    """
    FluxController is the same as XfluxController except that it
    requires a Settings instance and updates that instance when
    relevant controller calls are made.
    """
    def __init__(self, settings):
        self.settings = settings
        super(FluxController, self).__init__(
                **self.settings.xflux_settings_dict())

    def start(self):
        if self.settings.zipcode == "" and self.settings.latitude == "":
            raise ValueError("Cannot start xflux, missing zipcode and latitude")
        super(FluxController, self).start()

    # Controller methods that don't touch xflux
    def set_autostart(self, autos):
        self.settings.autostart = autos

    # xflux methods that should also update settings
    def set_xflux_latitude(self, lat):
        self.settings.latitude = lat
        super(FluxController, self).set_xflux_latitude(lat)

    def set_xflux_longitude(self, longit):
        self.settings.longitude = longit
        super(FluxController, self).set_xflux_longitude(longit)

    def set_xflux_zipcode(self, zipc):
        self.settings.zipcode = zipc
        super(FluxController, self).set_xflux_zipcode(zipc)

    def _set_xflux_color(self, col):
        self.settings.color = col
        super(FluxController, self)._set_xflux_color(col)

    def _get_xflux_color(self):
        return super(FluxController, self)._get_xflux_color()

    color=property(_get_xflux_color, _set_xflux_color)



########NEW FILE########
__FILENAME__ = settings
import os
import gconf
from xdg.DesktopEntry import DesktopEntry
from fluxgui.exceptions import DirectoryCreationError


class Settings(object):

    def __init__(self):
        self.client = GConfClient("/apps/fluxgui")

        self._color = self.client.get_client_string("colortemp", 3400)
        self._autostart = self.client.get_client_bool("autostart")
        self._latitude = self.client.get_client_string("latitude")
        self._longitude = self.client.get_client_string("longitude")
        self._zipcode = self.client.get_client_string("zipcode")

        self.has_set_prefs = True
        if not self._latitude and not self._zipcode:
            self.has_set_prefs = False
            self._zipcode = '90210'
            self.autostart=True
        if int(self._color) < 2700 or not self._color:
            # upgrade from previous version
            temperature_keys = {
                    '0':  '2700',
                    '1':  '3400',
                    '2':  '4200',
                    '3':  '5000',
                    '4':  '6500',
            }
            if self._color in temperature_keys:
                self.color = temperature_keys[self._color]
            else:
                self.color = '3400'

    def xflux_settings_dict(self):
        d = {
                'color': self.color,
                'latitude': self.latitude,
                'longitude': self.longitude,
                'zipcode': self.zipcode,
                'pause_color': '6500'
        }
        return d

    def _get_color(self):
        return str(self._color)
    def _set_color(self, value):
        self._color = value
        self.client.set_client_string("colortemp", value)

    def _get_latitude(self):
        return str(self._latitude)
    def _set_latitude(self, value):
        self._latitude = value
        self.client.set_client_string("latitude", value)

    def _get_longitude(self):
        return str(self._longitude)
    def _set_longitude(self, value):
        self._longitude = value
        self.client.set_client_string("longitude", value)

    def _get_zipcode(self):
        return str(self._zipcode)
    def _set_zipcode(self, value):
        self._zipcode = value
        self.client.set_client_string("zipcode", value)

    def _get_autostart(self):
        return bool(self._autostart)
    def _set_autostart(self, value):
        self._autostart = value
        self.client.set_client_bool("autostart", self._autostart)
        if self._autostart:
            self._create_autostarter()
        else:
            self._delete_autostarter()

    color=property(_get_color, _set_color)
    latitude=property(_get_latitude, _set_latitude)
    longitude=property(_get_longitude, _set_longitude)
    zipcode=property(_get_zipcode, _set_zipcode)
    autostart=property(_get_autostart, _set_autostart)


    #autostart code copied from AWN
    def _get_autostart_file_path(self):
        autostart_dir = os.path.join(os.environ['HOME'], '.config',
                                     'autostart')
        return os.path.join(autostart_dir, 'fluxgui.desktop')

    def _create_autostarter(self):
        autostart_file = self._get_autostart_file_path()
        autostart_dir = os.path.dirname(autostart_file)

        if not os.path.isdir(autostart_dir):
            #create autostart dir
            try:
                os.mkdir(autostart_dir)
            except DirectoryCreationError, e:
                print "Creation of autostart dir failed, please make it yourself: %s" % autostart_dir
                raise e

        if not os.path.isfile(autostart_file):
            #create autostart entry
            starter_item = DesktopEntry(autostart_file)
            starter_item.set('Name', 'f.lux indicator applet')
            starter_item.set('Exec', 'fluxgui')
            starter_item.set('Icon', 'fluxgui')
            starter_item.set('X-GNOME-Autostart-enabled', 'true')
            starter_item.write()
            self.autostart = True

    def _delete_autostarter(self):
        autostart_file = self._get_autostart_file_path()
        if os.path.isfile(autostart_file):
            os.remove(autostart_file)
            self.autostart = False

class GConfClient(object):
    """
    Gets and sets gconf settings.
    """

    def __init__(self, prefs_key):
        self.client = gconf.client_get_default()
        self.prefs_key = prefs_key
        self.client.add_dir(self.prefs_key, gconf.CLIENT_PRELOAD_NONE)

    def get_client_string(self, property_name, default=""):
        client_string = self.client.get_string(self.prefs_key+"/"+property_name)
        if client_string is None:
            client_string = default
        return client_string

    def set_client_string(self, property_name, value):
        self.client.set_string(self.prefs_key + "/" + property_name, str(value))

    def get_client_bool(self, property_name, default=True):
        try:
            gconf_type = self.client.get(self.prefs_key + "/"
                                            + property_name).type
        except AttributeError:
            # key is not set
            self.set_client_bool(property_name, default)
            client_bool = default
            return client_bool

        client_bool = None
        if gconf_type != gconf.VALUE_BOOL:
            # previous release used strings for autostart, handle here
            client_string = self.get_client_string(property_name).lower()
            if client_string == '1':
                self.set_client_bool(property_name, True)
                client_bool = True
            elif client_string == '0':
                self.set_client_bool(property_name, False)
                client_bool = False
        else:
            client_bool = self.client.get_bool(self.prefs_key
                                        + "/"+property_name)
        return client_bool

    def set_client_bool(self, property_name, value):
        self.client.set_bool(self.prefs_key + "/" + property_name, bool(value))


########NEW FILE########
__FILENAME__ = xfluxcontroller
import pexpect
import time
import weakref
from fluxgui.exceptions import *

class XfluxController(object):
    """
    A controller that starts and interacts with an xflux process.
    """


    def __init__(self, color='3400', pause_color='6500', **kwargs):
        if 'zipcode' not in kwargs and 'latitude' not in kwargs:
            raise XfluxError(
                    "Required key not found (either zipcode or latitude)")
        if 'longitude' not in kwargs:
            kwargs['longitude'] = 0
        self.init_kwargs = kwargs
        self._current_color = str(color)
        self._pause_color = str(pause_color)

        self.states = {
            "INIT": _InitState(self),
            "RUNNING": _RunningState(self),
            "PAUSED": _PauseState(self),
            "TERMINATED": _TerminatedState(self),
        }
        self.state = self.states["INIT"]

    def start(self, startup_args=None):
        self.state.start(startup_args)

    def stop(self):
        self.state.stop()

    def preview_color(self, preview_color):
        self.state.preview(preview_color)

    def toggle_pause(self):
        self.state.toggle_pause()

    def set_xflux_latitude(self, lat):
        self.state.set_setting(latitude=lat)

    def set_xflux_longitude(self, longit):
        self.state.set_setting(longitude=longit)

    def set_xflux_zipcode(self, zipc):
        self.state.set_setting(zipcode=zipc)

    def _set_xflux_color(self, col):
        self.state.set_setting(color=col)

    def _get_xflux_color(self):
        self._c()
        index = self._xflux.expect("Color.*")
        color = -1
        if index == 0:
            color = self._xflux.after[10:14]
        return color

    color=property(_get_xflux_color, _set_xflux_color)

    def _start(self, startup_args=None):
        if not startup_args:
            startup_args = self._create_startup_arg_list(self._current_color,
                **self.init_kwargs)
        try:
            self._xflux = pexpect.spawn("xflux", startup_args)
                    #logfile=file("tmp/xfluxout.txt",'w'))

        except pexpect.ExceptionPexpect:
            raise FileNotFoundError(
                    "\nError: Please install xflux in the PATH \n")

    def _stop(self):
        try:
            if self._xflux.terminate(force=True):
                return True
            else:
                return False
        except Exception:
            # xflux has crashed in the meantime?
            return True

    def _preview_color(self, preview_color, return_color):
        # could probably be implemented better

        preview_color = str(preview_color)
        self._set_xflux_screen_color(preview_color)
        self._c()
        #while self.color != preview_color:
            #time.sleep(.5)
        time.sleep(5)
        self._set_xflux_screen_color(return_color)
        self._c()

    _settings_map = {
            'latitude':'l=',
            'longitude':'g=',
            'zipcode':'z=',
            'color':'k=',
    }

    def _set_xflux_setting(self, **kwargs):
        for key, value in kwargs.items():
            if key in self._settings_map:
                if key == 'color':
                    self._set_xflux_screen_color(value)
                    self._current_color = str(value)
                    # hackish - changing the current color unpauses xflux,
                    # must reflect that with state change
                    if self.state == self.states["PAUSED"]:
                        self.state = self.states["RUNNING"]
                else:
                    self._xflux.sendline(self._settings_map[key]+str(value))
                self._c()

    def _create_startup_arg_list(self, color='3400', **kwargs):
        startup_args = []
        if "zipcode" in kwargs and kwargs['zipcode']:
            startup_args += ["-z", str(kwargs["zipcode"])]
        if "latitude" in kwargs and kwargs['latitude']:
            # by default xflux uses latitude even if zipcode is given
            startup_args += ["-l", str(kwargs["latitude"])]
        if "longitude" in kwargs and kwargs['longitude']:
            startup_args += ["-g", str(kwargs["longitude"])]
        startup_args += ["-k", str(color), "-nofork"] # nofork is vital

        return startup_args

    def _change_color_immediately(self, new_color):
        self._set_xflux_screen_color(new_color)
        self._c()

    def _p(self):
        # seems to bring color up to "off" then transitions back down (at night)
        # takes color down to night color then back up to off (during day)
        # I assume this is supposed to be "preview" or something like it
        # but it doesn't work the way it should for a preview so it isn't used
        self._xflux.sendline("p")

    def _c(self):
        # prints Colortemp=#### in xflux process
        # Also: When called after a color change (sendline(k=#))
        #   makes changes immediate
        #   (see use in toggle_pause() and preview_color())
        self._xflux.sendline("c")

    def _set_xflux_screen_color(self, color):
        # use _set_xflux_color unless keeping
        # self._current_color the same is necessary
        self._xflux.sendline("k="+str(color))


class _XfluxState(object):
    can_change_settings = False

    def __init__(self, controller_instance):
        self.controller_ref = weakref.ref(controller_instance)
    def start(self, startup_args):
        raise MethodUnavailableError(
                "Xflux cannot start in its current state")
    def stop(self):
        raise MethodUnavailableError(
                "Xflux cannot stop in its current state")
    def preview(self, preview_color):
        raise MethodUnavailableError(
                "Xflux cannot preview in its current state")
    def toggle_pause(self):
        raise MethodUnavailableError(
                "Xflux cannot pause/unpause in its current state")
    def set_setting(self, **kwargs):
        raise MethodUnavailableError(
                "Xflux cannot alter settings in its current state")

class _InitState(_XfluxState):
    def start(self, startup_args):
        self.controller_ref()._start(startup_args)
        self.controller_ref().state = self.controller_ref().states["RUNNING"]
    def stop(self):
        return True
    def set_setting(self, **kwargs):
        for key, value in kwargs.items():
            self.controller_ref().init_kwargs[key] = str(value)

class _TerminatedState(_XfluxState):
    def stop(self):
        return True

class _AliveState(_XfluxState):
    can_change_settings = True
    def stop(self):
        success = self.controller_ref()._stop()
        if success:
            self.controller_ref().state = \
                self.controller_ref().states["TERMINATED"]
        return success
    def set_setting(self, **kwargs):
        self.controller_ref()._set_xflux_setting(**kwargs)

class _RunningState(_AliveState):
    def toggle_pause(self):
        self.controller_ref()._change_color_immediately(
                self.controller_ref()._pause_color)
        self.controller_ref().state = self.controller_ref().states["PAUSED"]
    def preview(self, preview_color):
        self.controller_ref()._preview_color(preview_color,
                self.controller_ref()._current_color)

class _PauseState(_AliveState):
    def toggle_pause(self):
        self.controller_ref()._change_color_immediately(
                self.controller_ref()._current_color)
        self.controller_ref().state = self.controller_ref().states["RUNNING"]
    def preview(self, preview_color):
        self.controller_ref()._preview_color(preview_color,
                self.controller_ref()._pause_color)

########NEW FILE########
