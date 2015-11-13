__FILENAME__ = build
'''
Copyright 2011 Mikel Azkolain

This file is part of Spotimc.

Spotimc is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

Spotimc is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with Spotimc.  If not, see <http://www.gnu.org/licenses/>.
'''


import os
import fnmatch
import xml.etree.ElementTree as ET
import zipfile


#Get the working dir of the script
work_dir = os.getcwd()


include_files = [
    'resources/*',
    'addon.xml',
    'changelog.txt',
    'default.py',
    'spotimc.py',
    'icon.png',
    'LICENSE.txt',
    'README.md',
]

exclude_files = [
    '*.pyc',
    '*.pyo',
    '*/Thumbs.db',
    'resources/libs/spotimcgui/appkey.py-template',
    'resources/libs/pyspotify-ctypes/tmp',
    'resources/libs/pyspotify-ctypes/dlls',
    'resources/libs/pyspotify-ctypes/libs',
    'resources/libs/pyspotify-ctypes-proxy/tmp',
    'resources/libs/pyspotify-ctypes-proxy/dlls',
    'resources/libs/pyspotify-ctypes-proxy/libs',
]


def get_addon_info():
    path = os.path.join(work_dir, 'addon.xml')
    root = ET.parse(path).getroot()
    return root.attrib['id'], root.attrib['version']


def is_included(path):
    for item in include_files:
        #Try fnmatching agains the include rule
        if fnmatch.fnmatch(path, item):
            return True

        #Also test if it gets included by a contained file
        elif path.startswith(item):
            return True

        #Or if the path is part of a pattern
        elif item.startswith(path):
            return True

    return False


def is_excluded(path):

    #Exclude hidden files and folders
    if os.path.basename(path).startswith('.'):
        return True

    #Iterate over the exclude patterns
    else:

        for item in exclude_files:
            #Try fnmatching agains the exclude entry
            if fnmatch.fnmatch(path, item):
                return True

        return False


def generate_file_list(path):
    file_list = []

    for item in os.listdir(path):
        cur_path = os.path.join(path, item)
        cur_rel_path = os.path.relpath(cur_path, work_dir)

        if is_included(cur_rel_path) and not is_excluded(cur_rel_path):
            file_list.append(cur_rel_path)

            if os.path.isdir(cur_path):
                file_list.extend(generate_file_list(cur_path))

    return file_list


def create_build_dir():
    build_dir = os.path.join(work_dir, 'build')
    if not os.path.isdir(build_dir):
        os.mkdir(build_dir)
    return build_dir


def generate_zip(build_dir, addon_id, addon_version, file_list):
    #for item in file_list:
    #    print item
    zip_name = '{0}-{1}.zip'.format(addon_id, addon_version)
    zip_path = os.path.join(build_dir, zip_name)
    zip_obj = zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED)

    for item in file_list:
        abs_path = os.path.join(work_dir, item)
        if not os.path.isdir(abs_path):
            arc_path = os.path.join(addon_id, item)
            zip_obj.write(abs_path, arc_path)

    zip_obj.close()

    return zip_path


def main():
    build_dir = create_build_dir()
    addon_id, addon_version = get_addon_info()
    file_list = generate_file_list(work_dir)
    out_file = generate_zip(build_dir, addon_id, addon_version, file_list)
    print('generated zip: {0}'.format(os.path.relpath(out_file, work_dir)))


if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = default
'''
Copyright 2011 Mikel Azkolain

This file is part of Spotimc.

Spotimc is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

Spotimc is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with Spotimc.  If not, see <http://www.gnu.org/licenses/>.
'''


import xbmc
import xbmcaddon
import os.path
import sys

#Set global addon information first
__addon_id__ = 'script.audio.spotimc'
addon_cfg = xbmcaddon.Addon(__addon_id__)
__addon_path__ = addon_cfg.getAddonInfo('path')
__addon_version__ = addon_cfg.getAddonInfo('version')

#Make spotimcgui available
sys.path.insert(0, os.path.join(__addon_path__, "resources/libs"))
from spotimcgui.utils import environment


if environment.has_background_support():

    #Some specific imports for this condition
    from spotimcgui.settings import InfoValueManager
    from spotimcgui.utils.gui import show_busy_dialog

    manager = InfoValueManager()
    spotimc_window_id = manager.get_infolabel('spotimc_window_id')

    if spotimc_window_id != '':
        xbmc.executebuiltin('ActivateWindow(%s)' % spotimc_window_id)
    else:
        spotimc_path = os.path.join(__addon_path__, 'spotimc.py')
        show_busy_dialog()
        xbmc.executebuiltin('RunScript("%s")' % spotimc_path)

else:
    #Prepare the environment...
    from spotimcgui.utils.environment import set_library_paths
    set_library_paths()

    from spotimcgui.main import main
    main()

########NEW FILE########
__FILENAME__ = dialogs
'''
Copyright 2011 Mikel Azkolain

This file is part of Spotimc.

Spotimc is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

Spotimc is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with Spotimc.  If not, see <http://www.gnu.org/licenses/>.
'''


import xbmc
import xbmcgui
import time
from spotify.session import SessionCallbacks
from spotify import ErrorType
from __main__ import __addon_path__


class LoginCallbacks(SessionCallbacks):
    __dialog = None

    def __init__(self, dialog):
        self.__dialog = dialog

    def logged_in(self, session, err):
        if err == 0:
            self.__dialog.do_close()

        else:
            self.__dialog.set_error(err)


class LoginWindow(xbmcgui.WindowXMLDialog):
    #Controld id's
    username_input = 1101
    password_input = 1102
    login_button = 1104
    cancel_button = 1105

    login_container = 1000
    fields_container = 1100
    loading_container = 1200

    __file = None
    __script_path = None
    __skin_dir = None
    __session = None
    __callbacks = None
    __app = None

    __username = None
    __password = None

    __cancelled = None

    def __init__(self, file, script_path, skin_dir):
        self.__file = file
        self.__script_path = script_path
        self.__skin_dir = skin_dir
        self.__cancelled = False

    def initialize(self, session, app):
        self.__session = session
        self.__callbacks = LoginCallbacks(self)
        self.__session.add_callbacks(self.__callbacks)
        self.__app = app

    def onInit(self):
        #If there is a remembered user, show it's login name
        username = self.__session.remembered_user()
        if username is not None:
            self._set_input_value(self.username_input, username)

        #Show useful info if previous errors are present
        if self.__app.has_var('login_last_error'):

            #If the error number was relevant...
            login_last_error = self.__app.get_var('login_last_error')
            if login_last_error != 0:
                #Wait for the appear animation to complete
                time.sleep(0.2)

                self.set_error(self.__app.get_var('login_last_error'), True)

    def onAction(self, action):
        if action.getId() in [9, 10, 92]:
            self.__cancelled = True
            self.do_close()

    def set_error(self, code, short_animation=False):
        messages = {
            ErrorType.ClientTooOld: 'Client is too old',
            ErrorType.UnableToContactServer: 'Unable to contact server',
            ErrorType.BadUsernameOrPassword: 'Bad username or password',
            ErrorType.UserBanned: 'User is banned',
            ErrorType.UserNeedsPremium: 'A premium account is required',
            ErrorType.OtherTransient: 'A transient error occurred.'
            'Try again after a few minutes.',
            ErrorType.OtherPermanent: 'A permanent error occurred.',
        }

        if code in messages:
            escaped = messages[code].replace('"', '\"')
            tmpStr = 'SetProperty(LoginErrorMessage, "{0}")'.format(escaped)
            xbmc.executebuiltin(tmpStr)
        else:
            tmpStr = 'SetProperty(LoginErrorMessage, "Unknown error.")'
            xbmc.executebuiltin(tmpStr)
            #self.setProperty('LoginErrorMessage', 'Unknown error.')

        #Set error flag
        xbmc.executebuiltin('SetProperty(IsLoginError,true)')

        #Animation type
        if short_animation:
            xbmc.executebuiltin('SetProperty(ShortErrorAnimation,true)')
        else:
            xbmc.executebuiltin('SetProperty(ShortErrorAnimation,false)')

        #Hide animation
        self.getControl(
            LoginWindow.loading_container).setVisibleCondition('false')

    def _get_input_value(self, controlID):
        c = self.getControl(controlID)
        return c.getLabel()

    def _set_input_value(self, controlID, value):
        c = self.getControl(controlID)
        c.setLabel(value)

    def do_login(self):
        remember_set = xbmc.getCondVisibility(
            'Skin.HasSetting(spotimc_session_remember)'
        )
        self.__session.login(self.__username, self.__password, remember_set)

        #Clear error status
        xbmc.executebuiltin('SetProperty(IsLoginError,false)')

        #SHow loading animation
        self.getControl(
            LoginWindow.loading_container).setVisibleCondition('true')

    def do_close(self):
        self.__session.remove_callbacks(self.__callbacks)
        c = self.getControl(LoginWindow.login_container)
        c.setVisibleCondition("False")
        time.sleep(0.2)
        self.close()

    def onClick(self, controlID):
        if controlID == self.username_input:
            default = self._get_input_value(controlID)
            kb = xbmc.Keyboard(default, "Enter username")
            kb.setHiddenInput(False)
            kb.doModal()
            if kb.isConfirmed():
                value = kb.getText()
                self.__username = value
                self._set_input_value(controlID, value)

        elif controlID == self.password_input:
            kb = xbmc.Keyboard("", "Enter password")
            kb.setHiddenInput(True)
            kb.doModal()
            if kb.isConfirmed():
                value = kb.getText()
                self.__password = value
                self._set_input_value(controlID, "*" * len(value))

        elif controlID == self.login_button:
            self.do_login()

        elif controlID == self.cancel_button:
            self.__cancelled = True
            self.do_close()

    def is_cancelled(self):
        return self.__cancelled

    def onFocus(self, controlID):
        pass


class TextViewer(xbmcgui.WindowXMLDialog):
    label_id = 1
    textbox_id = 5
    close_button_id = 10

    __heading = None
    __text = None

    def onInit(self):
        #Not all skins implement the heading label...
        try:
            self.getControl(TextViewer.label_id).setLabel(self.__heading)
        except:
            pass

        self.getControl(TextViewer.textbox_id).setText(self.__text)

    def onClick(self, control_id):
        if control_id == 10:
            self.close()

    def initialize(self, heading, text):
        self.__heading = heading
        self.__text = text


def text_viewer_dialog(heading, text, modal=True):
    tv = TextViewer('DialogTextViewer.xml', __addon_path__)
    tv.initialize(heading, text)

    if modal:
        tv.doModal()
    else:
        tv.show()

########NEW FILE########
__FILENAME__ = main
'''
Copyright 2011 Mikel Azkolain

This file is part of Spotimc.

Spotimc is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

Spotimc is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with Spotimc.  If not, see <http://www.gnu.org/licenses/>.
'''


import os
import os.path
import xbmc
import xbmcgui
import windows
import threading
import gc
import traceback
import weakref
import dialogs
import playback
import re
from appkey import appkey
from spotify import MainLoop, ConnectionState, ErrorType, Bitrate
from spotify import track as _track
from spotify.session import Session, SessionCallbacks
from spotifyproxy.httpproxy import ProxyRunner
from spotifyproxy.audio import BufferManager
from taskutils.decorators import run_in_thread
from taskutils.threads import TaskManager
from threading import Event
from settings import SettingsManager, CacheManagement, StreamQuality, \
    GuiSettingsReader, InfoValueManager
from __main__ import __addon_version__, __addon_path__
from utils.logs import get_logger, setup_logging
from utils.gui import hide_busy_dialog, show_busy_dialog


class Application:
    __vars = None

    def __init__(self):
        self.__vars = {}

    def set_var(self, name, value):
        self.__vars[name] = value

    def has_var(self, name):
        return name in self.__vars

    def get_var(self, name):
        return self.__vars[name]

    def remove_var(self, name):
        del self.__vars[name]


class SpotimcCallbacks(SessionCallbacks):
    __mainloop = None
    __audio_buffer = None
    __logout_event = None
    __app = None
    __logger = None
    __log_regex = None

    def __init__(self, mainloop, audio_buffer, app):
        self.__mainloop = mainloop
        self.__audio_buffer = audio_buffer
        self.__app = app
        self.__logger = get_logger()
        self.__log_regex = re.compile('[0-9]{2}:[0-9]{2}:[0-9]{2}'
                                      '\.[0-9]{3}\s(W|I|E)\s')

    def logged_in(self, session, error_num):
        #Log this event
        self.__logger.debug('logged in: {0:d}'.format(error_num))

        #Store last error code
        self.__app.set_var('login_last_error', error_num)

        #Take action if error status is not ok
        if error_num != ErrorType.Ok:

            #Close the main window if it's running
            if self.__app.has_var('main_window'):
                self.__app.get_var('main_window').close()

            #Otherwise, set the connstate event
            else:
                self.__app.get_var('connstate_event').set()

    def logged_out(self, session):
        self.__logger.debug('logged out')
        self.__app.get_var('logout_event').set()

    def connection_error(self, session, error):
        self.__logger.error('connection error: {0:d}'.format(error))

    def message_to_user(self, session, data):
        self.__logger.info('message to user: {0}'.format(data))

    def _get_log_message_level(self, message):
        matches = self.__log_regex.match(message)
        if matches:
            return matches.group(1)

    def log_message(self, session, data):
        message_level = self._get_log_message_level(data)
        if message_level == 'I':
            self.__logger.info(data)
        elif message_level == 'W':
            self.__logger.warning(data)
        else:
            self.__logger.error(data)

    def streaming_error(self, session, error):
        self.__logger.info('streaming error: {0:d}'.format(error))

    @run_in_thread
    def play_token_lost(self, session):

        #Cancel the current buffer
        self.__audio_buffer.stop()

        if self.__app.has_var('playlist_manager'):
            self.__app.get_var('playlist_manager').stop(False)

        dlg = xbmcgui.Dialog()
        dlg.ok('Playback stopped', 'This account is in use on another device.')

    def end_of_track(self, session):
        self.__audio_buffer.set_track_ended()

    def notify_main_thread(self, session):
        self.__mainloop.notify()

    def music_delivery(self, session, data, num_samples, sample_type,
                       sample_rate, num_channels):
        return self.__audio_buffer.music_delivery(
            data, num_samples, sample_type, sample_rate, num_channels)

    def connectionstate_changed(self, session):

        #Set the apropiate event flag, if available
        self.__app.get_var('connstate_event').set()


class MainLoopRunner(threading.Thread):
    __mainloop = None
    __session = None
    __proxy = None

    def __init__(self, mainloop, session):
        threading.Thread.__init__(self)
        self.__mainloop = mainloop
        self.__session = weakref.proxy(session)

    def run(self):
        self.__mainloop.loop(self.__session)

    def stop(self):
        self.__mainloop.quit()
        self.join(10)


def show_legal_warning(settings_obj):
    shown = settings_obj.get_legal_warning_shown()
    if not shown:
        settings_obj.set_legal_warning_shown(True)
        d = xbmcgui.Dialog()
        l1 = 'Spotimc uses SPOTIFY(R) CORE but is not endorsed,'
        l2 = 'certified or otherwise approved in any way by Spotify.'
        
        hide_busy_dialog()
        d.ok('Spotimc', l1, l2)
        show_busy_dialog()


def check_addon_version(settings_obj):
    last_run_version = settings_obj.get_last_run_version()

    #If current version is higher than the stored one...
    if __addon_version__ > last_run_version:
        settings_obj.set_last_run_version(__addon_version__)

        #Don't display the upgrade message if it's the first run
        if last_run_version != '':
            
            d = xbmcgui.Dialog()
            l1 = 'Spotimc was updated since the last run.'
            l2 = 'Do you want to see the changelog?'
            
            hide_busy_dialog()
            
            if d.yesno('Spotimc', l1, l2):
                file = settings_obj.get_addon_obj().getAddonInfo('changelog')
                changelog = open(file).read()
                dialogs.text_viewer_dialog('ChangeLog', changelog)
            
            show_busy_dialog()
            


def get_audio_buffer_size():
    #Base buffer setting will be 10s
    buffer_size = 10

    try:
        reader = GuiSettingsReader()
        value = reader.get_setting('settings.musicplayer.crossfade')
        buffer_size += int(value)

    except:
        xbmc.log(
            'Failed reading crossfade setting. Using default value.',
            xbmc.LOGERROR
        )

    return buffer_size


def check_dirs():
    addon_data_dir = os.path.join(
        xbmc.translatePath('special://profile/addon_data'),
        'script.audio.spotimc'
    )

    #Auto-create profile dir if it does not exist
    if not os.path.exists(addon_data_dir):
        os.makedirs(addon_data_dir)

    #Libspotify cache & settings
    sp_cache_dir = os.path.join(addon_data_dir, 'libspotify/cache')
    sp_settings_dir = os.path.join(addon_data_dir, 'libspotify/settings')

    if not os.path.exists(sp_cache_dir):
        os.makedirs(sp_cache_dir)

    if not os.path.exists(sp_settings_dir):
        os.makedirs(sp_settings_dir)

    return (addon_data_dir, sp_cache_dir, sp_settings_dir)


def set_settings(settings_obj, session):
    #If cache is enabled set the following one
    if settings_obj.get_cache_status():
        if settings_obj.get_cache_management() == CacheManagement.Manual:
            cache_size_mb = settings_obj.get_cache_size() * 1024
            session.set_cache_size(cache_size_mb)

    #Bitrate config
    br_map = {
        StreamQuality.Low: Bitrate.Rate96k,
        StreamQuality.Medium: Bitrate.Rate160k,
        StreamQuality.High: Bitrate.Rate320k,
    }
    session.preferred_bitrate(br_map[settings_obj.get_audio_quality()])

    #And volume normalization
    session.set_volume_normalization(settings_obj.get_audio_normalize())

    #And volume normalization
    session.set_volume_normalization(settings_obj.get_audio_normalize())


def do_login(session, script_path, skin_dir, app):
    #Get the last error if we have one
    if app.has_var('login_last_error'):
        prev_error = app.get_var('login_last_error')
    else:
        prev_error = 0

    #If no previous errors and we have a remembered user
    if prev_error == 0 and session.remembered_user() is not None:
        session.relogin()
        status = True

    #Otherwise let's do a normal login process
    else:
        loginwin = dialogs.LoginWindow(
            "login-window.xml", script_path, skin_dir
        )
        loginwin.initialize(session, app)
        loginwin.doModal()
        status = not loginwin.is_cancelled()

    return status


def login_get_last_error(app):
    if app.has_var('login_last_error'):
        return app.get_var('login_last_error')
    else:
        return 0


def wait_for_connstate(session, app, state):

    #Store the previous login error number
    last_login_error = login_get_last_error(app)

    #Add a shortcut to the connstate event
    cs = app.get_var('connstate_event')

    #Wrap all the tests for the following loop
    def continue_loop():

        #Get the current login error
        cur_login_error = login_get_last_error(app)

        #Continue the loop while these conditions are met:
        #  * An exit was not requested
        #  * Connection state was not the desired one
        #  * No login errors where detected
        return (
            not app.get_var('exit_requested') and
            session.connectionstate() != state and (
                last_login_error == cur_login_error or
                cur_login_error == ErrorType.Ok
            )
        )

    #Keep testing until conditions are met
    while continue_loop():
        cs.wait(5)
        cs.clear()

    return session.connectionstate() == state


def get_preloader_callback(session, playlist_manager, buffer):
    session = weakref.proxy(session)

    def preloader():
        next_track = playlist_manager.get_next_item(session)
        if next_track is not None:
            ta = next_track.get_availability(session)
            if ta == _track.TrackAvailability.Available:
                buffer.open(session, next_track)

    return preloader


def gui_main(addon_dir):
    #Initialize app var storage
    app = Application()
    logout_event = Event()
    connstate_event = Event()
    info_value_manager = InfoValueManager()
    app.set_var('logout_event', logout_event)
    app.set_var('login_last_error', ErrorType.Ok)
    app.set_var('connstate_event', connstate_event)
    app.set_var('exit_requested', False)
    app.set_var('info_value_manager', info_value_manager)

    #Check needed directories first
    data_dir, cache_dir, settings_dir = check_dirs()

    #Instantiate the settings obj
    settings_obj = SettingsManager()

    #Show legal warning
    show_legal_warning(settings_obj)

    #Start checking the version
    check_addon_version(settings_obj)

    #Don't set cache folder if it's disabled
    if not settings_obj.get_cache_status():
        cache_dir = ''

    #Initialize spotify stuff
    ml = MainLoop()
    buf = BufferManager(get_audio_buffer_size())
    callbacks = SpotimcCallbacks(ml, buf, app)
    sess = Session(
        callbacks,
        app_key=appkey,
        user_agent="python ctypes bindings",
        settings_location=settings_dir,
        cache_location=cache_dir,
        initially_unload_playlists=False,
    )

    #Now that we have a session, set settings
    set_settings(settings_obj, sess)

    #Initialize libspotify's main loop handler on a separate thread
    ml_runner = MainLoopRunner(ml, sess)
    ml_runner.start()

    #Stay on the application until told to do so
    while not app.get_var('exit_requested'):

        #Set the exit flag if login was cancelled
        if not do_login(sess, addon_dir, "DefaultSkin", app):
            app.set_var('exit_requested', True)

        #Otherwise block until state is sane, and continue
        elif wait_for_connstate(sess, app, ConnectionState.LoggedIn):

            proxy_runner = ProxyRunner(sess, buf, host='127.0.0.1',
                                       allow_ranges=True)
            proxy_runner.start()
            log_str = 'starting proxy at port {0}'.format(
                proxy_runner.get_port())
            get_logger().info(log_str)

            #Instantiate the playlist manager
            playlist_manager = playback.PlaylistManager(proxy_runner)
            app.set_var('playlist_manager', playlist_manager)

            #Set the track preloader callback
            preloader_cb = get_preloader_callback(sess, playlist_manager, buf)
            proxy_runner.set_stream_end_callback(preloader_cb)

            hide_busy_dialog()
            mainwin = windows.MainWindow("main-window.xml",
                                         addon_dir,
                                         "DefaultSkin")
            mainwin.initialize(sess, proxy_runner, playlist_manager, app)
            app.set_var('main_window', mainwin)
            mainwin.doModal()
            show_busy_dialog()

            #Playback and proxy deinit sequence
            proxy_runner.clear_stream_end_callback()
            playlist_manager.stop()
            proxy_runner.stop()
            buf.cleanup()

            #Join all the running tasks
            tm = TaskManager()
            tm.cancel_all()

            #Clear some vars and collect garbage
            proxy_runner = None
            preloader_cb = None
            playlist_manager = None
            mainwin = None
            app.remove_var('main_window')
            app.remove_var('playlist_manager')
            gc.collect()

            #Logout
            if sess.user() is not None:
                sess.logout()
                logout_event.wait(10)

    #Stop main loop
    ml_runner.stop()

    #Some deinitializations
    info_value_manager.deinit()


def main():

    setup_logging()

    #Look busy while everything gets initialized
    show_busy_dialog()

    #Surround the rest of the init process
    try:

        #Set font & include manager vars
        fm = None
        im = None

        #And perform the rest of the import statements
        from utils.environment import set_dll_paths
        from skinutils import reload_skin
        from skinutils.fonts import FontManager
        from skinutils.includes import IncludeManager
        from _spotify import unload_library

        #Add the system specific library path
        set_dll_paths('resources/dlls')

        #Install custom fonts
        fm = FontManager()
        skin_dir = os.path.join(__addon_path__, "resources/skins/DefaultSkin")
        xml_path = os.path.join(skin_dir, "720p/font.xml")
        font_dir = os.path.join(skin_dir, "fonts")
        fm.install_file(xml_path, font_dir)

        #Install custom includes
        im = IncludeManager()
        include_path = os.path.join(skin_dir, "720p/includes.xml")
        im.install_file(include_path)
        reload_skin()

        #Show the busy dialog again after reload_skin(), as it may go away
        show_busy_dialog()

        #Load & start the actual gui, no init code beyond this point
        gui_main(__addon_path__)

        show_busy_dialog()

        #Do a final garbage collection after main
        gc.collect()

        #from _spotify.utils.moduletracker import _tracked_modules
        #print "tracked modules after: %d" % len(_tracked_modules)

        #import objgraph
        #objgraph.show_backrefs(_tracked_modules, max_depth=5)

    except (SystemExit, Exception) as ex:
        if str(ex) != '':
            dlg = xbmcgui.Dialog()
            dlg.ok(ex.__class__.__name__, str(ex))
            traceback.print_exc()

    finally:

        unload_library("libspotify")

        #Cleanup includes and fonts
        if im is not None:
            del im

        if fm is not None:
            del fm

        #Close the background loading window
        #loadingwin.close()
        hide_busy_dialog()

########NEW FILE########
__FILENAME__ = playback
'''
Copyright 2011 Mikel Azkolain

This file is part of Spotimc.

Spotimc is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

Spotimc is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with Spotimc.  If not, see <http://www.gnu.org/licenses/>.
'''


import xbmc
import xbmcgui
from spotify import link, track, image
import time
from __main__ import __addon_version__
import math
import random
import settings
from taskutils.decorators import run_in_thread
from taskutils.threads import current_task
from spotify.utils.loaders import load_track
import re

#Cross python version import of urlparse
try:
    from urlparse import urlparse
except ImportError:
    from urllib.parse import urlparse


#Cross python version import of urlencode
try:
    from urllib import urlencode
except ImportError:
    from urllib.parse import urlencode


class PlaylistManager:
    __server_port = None
    __user_agent = None
    __play_token = None
    __url_headers = None
    __playlist = None
    __a6df109_fix = None
    __server_ip = None
    __player = None
    __loop_task = None

    def __init__(self, server):
        self.__server_port = server.get_port()
        self.__play_token = server.get_user_token(self._get_user_agent())
        self.__playlist = xbmc.PlayList(xbmc.PLAYLIST_MUSIC)
        self.__player = xbmc.Player()
        self.__a6df109_fix = 'a6df109' in xbmc.getInfoLabel(
            'System.BuildVersion')
        self.__server_ip = server.get_host()

    def _get_user_agent(self):
        if self.__user_agent is None:
            xbmc_build = xbmc.getInfoLabel("System.BuildVersion")
            self.__user_agent = 'Spotimc/{0} (XBMC/{1})'.format(
                __addon_version__, xbmc_build)

        return self.__user_agent

    # Unused
    def _get_play_token(self):
        return self.__play_token

    def _play_item(self, offset):
        self.__player.playselected(offset)

    def clear(self):
        self.__playlist = xbmc.PlayList(xbmc.PLAYLIST_MUSIC)
        self.__playlist.clear()

    def _get_track_id(self, track):
        track_link = link.create_from_track(track)
        return track_link.as_string()[14:]

    def _get_url_headers(self):
        if self.__url_headers is None:
            str_agent = self._get_user_agent()
            str_token = self._get_play_token()
            header_dict = {
                'User-Agent': str_agent,
                'X-Spotify-Token': str_token
                }
            self.__url_headers = urlencode(header_dict)

        return self.__url_headers

    def get_track_url(self, track, list_index=None):
        track_id = self._get_track_id(track)
        headers = self._get_url_headers()

        if list_index is not None:
            args = (
                self.__server_ip, self.__server_port,
                track_id, list_index, headers
            )
            return 'http://{0}:{1:d}/track/{2}.wav?idx={3:d}|{4}'.format(*args)
        else:
            args = (self.__server_ip, self.__server_port, track_id, headers)
            return 'http://{0}:{1:d}/track/{2}.wav|{3}'.format(*args)

    def get_image_url(self, image_id):
        if image_id is not None:
            args = (self.__server_ip, self.__server_port, image_id)
            return 'http://{0}:{1:d}/image/{2}.jpg'.format(*args)
        else:
            return ''

    def _calculate_track_rating(self, track):
        popularity = track.popularity()
        if popularity == 0:
            return 0
        else:
            return int(math.ceil(popularity * 6 / 100.0)) - 1

    def _item_is_playable(self, session, track_obj):
        return track_obj.get_availability(session) == \
            track.TrackAvailability.Available

    def _get_track_images(self, track_obj, session):

        #If it's local, let's get the images from the autolinked one
        if track_obj.is_local(session):
            track_obj = track_obj.get_playable(session)

        return(
            self.get_image_url(track_obj.album().cover()),
            self.get_image_url(track_obj.album().cover(image.ImageSize.Large))
        )

    def create_track_info(self, track_obj, session, list_index=None):

        #Track is ok
        if track_obj.is_loaded() and track_obj.error() == 0:

            #Get track attributes
            album = track_obj.album().name()
            artist = ', '.join([artist.name() for artist
                                in track_obj.artists()])
            normal_image, large_image = self._get_track_images(
                track_obj, session)
            track_url = self.get_track_url(track_obj, list_index)
            rating_points = str(self._calculate_track_rating(track_obj))

            item = xbmcgui.ListItem(
                track_obj.name(),
                path=track_url,
                iconImage=normal_image,
                thumbnailImage=large_image
            )
            info = {
                "title": track_obj.name(),
                "album": album,
                "artist": artist,
                "duration": track_obj.duration() / 1000,
                "tracknumber": track_obj.index(),
                "rating": rating_points,
            }
            item.setInfo("music", info)

            if list_index is not None:
                item.setProperty('ListIndex', str(list_index))

            if track_obj.is_starred(session):
                item.setProperty('IsStarred', 'true')
            else:
                item.setProperty('IsStarred', 'false')

            if self._item_is_playable(session, track_obj):
                item.setProperty('IsAvailable', 'true')
            else:
                item.setProperty('IsAvailable', 'false')

            #Rating points, again as a property for the custom stars
            item.setProperty('RatingPoints', rating_points)

            #Tell that analyzing the stream data is discouraged
            item.setProperty('do_not_analyze', 'true')

            return track_url, item

        #Track has errors
        else:
            return '', xbmcgui.ListItem()

    def stop(self, block=True):
        #Stop the stream and wait until it really got stopped
        #self.__player.stop()

        xbmc.executebuiltin('PlayerControl(stop)')

        while block and self.__player.isPlaying():
            time.sleep(.1)

    def _add_item(self, index, track, session):
        path, info = self.create_track_info(track, session, index)

        if self.__a6df109_fix:
            self.__playlist.add(path, info)
        else:
            self.__playlist.add(path, info, index)

    def is_playing(self, consider_pause=True):
        if consider_pause:
            return xbmc.getCondVisibility('Player.Playing | Player.Paused')
        else:
            return xbmc.getCondVisibility('Player.Playing')

    def get_shuffle_status(self):
        #Get it directly from a boolean tag (if possible)
        if self.is_playing() and len(self.__playlist) > 0:
            return xbmc.getCondVisibility('Playlist.IsRandom')

        #Otherwise read it from guisettings.xml
        else:
            try:
                reader = settings.GuiSettingsReader()
                value = reader.get_setting('settings.mymusic.playlist.shuffle')
                return value == 'true'

            except:
                xbmc.log(
                    'Failed reading shuffle setting.',
                    xbmc.LOGERROR
                )
                return False

    @run_in_thread(max_concurrency=1)
    def _set_tracks(self, track_list, session, omit_offset):

        #Set the reference to the loop task
        self.__loop_task = current_task()

        #Clear playlist if no offset is given to omit
        if omit_offset is None:
            self.clear()

        #Iterate over the rest of the playlist
        for list_index, track in enumerate(track_list):

            #Check if we should continue
            self.__loop_task.check_status()

            #Don't add unplayable items to the playlist
            if self._item_is_playable(session, track):

                #Ignore the item at offset, which is already added
                if list_index != omit_offset:
                    self._add_item(list_index, track, session)

            #Deal with any potential dummy items
            if omit_offset is not None and list_index < omit_offset:
                self.__playlist.remove('dummy-{0:d}'.format(list_index))

        #Set paylist's shuffle status
        if self.get_shuffle_status():
            self.__playlist.shuffle()

        #Clear the reference to the task
        self.__loop_task = None

    def _cancel_loop(self):
        if self.__loop_task is not None:
            try:
                self.__loop_task.cancel()
            except:
                pass

    def set_tracks(self, track_list, session, omit_offset=None):
        self._cancel_loop()
        self._set_tracks(track_list, session, omit_offset)

    def play(self, track_list, session, offset=None):
        if len(track_list) > 0:

            #Cancel any possible set_tracks() loop
            self._cancel_loop()

            #Get shuffle status
            is_shuffle = self.get_shuffle_status()

            #Clear the old contents
            self.clear()

            #If we don't have an offset, get one
            if offset is None:
                if is_shuffle:
                    #TODO: Should loop for a playable item
                    offset = random.randint(0, len(track_list) - 1)
                else:
                    offset = 0

            #Check if the selected item is playable
            if not self._item_is_playable(session, track_list[offset]):
                d = xbmcgui.Dialog()
                d.ok('Spotimc', 'The selected track is not playable')

            #Continue normally
            else:

                #Add some padding dummy items (to preserve playlist position)
                if offset > 0:
                    for index in range(offset):
                        tmpStr = 'dummy-{0:d}'.format(index)
                        self.__playlist.add(tmpStr, xbmcgui.ListItem(''))

                #Add the desired item and play it
                self._add_item(offset, track_list[offset], session)
                self._play_item(offset)

                #If there are items left...
                if len(track_list) > 1:
                    self.set_tracks(track_list, session, offset)

    def _get_track_from_url(self, sess_obj, url):

        #Get the clean track if from the url
        path = urlparse(url).path
        r = re.compile('^/track/(.+?)(?:\.wav)?$', re.IGNORECASE)
        mo = r.match(path)

        #If we succeed, create the object
        if mo is not None:

            #Try loading it as a spotify track
            link_obj = link.create_from_string("spotify:track:{0}".format(
                mo.group(1)))
            if link_obj is not None:
                return load_track(sess_obj, link_obj.as_track())

            #Try to parse as a local track
            tmpStr = "spotify:local:{0}".format(mo.group(1))
            link_obj = link.create_from_string(tmpStr)
            if link_obj is not None:

                #return the autolinked one, instead of the local track
                local_track = link_obj.as_track()
                return load_track(sess_obj, local_track.get_playable(sess_obj))

    def get_item(self, sess_obj, index):
        item = self.__playlist[index]
        return self._get_track_from_url(sess_obj, item.getfilename())

    def get_current_item(self, sess_obj):
        return self._get_track_from_url(
            sess_obj, xbmc.getInfoLabel('Player.Filenameandpath')
        )

    def get_next_item(self, sess_obj):
        next_index = self.__playlist.getposition() + 1
        if next_index < len(self.__playlist):
            return self.get_item(sess_obj, next_index)

    def __del__(self):
        #Cancel the set_tracks() loop at exit
        self.__cancel_set_tracks = True

########NEW FILE########
__FILENAME__ = settings
'''
Copyright 2011 Mikel Azkolain

This file is part of Spotimc.

Spotimc is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

Spotimc is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with Spotimc.  If not, see <http://www.gnu.org/licenses/>.
'''


import xbmc
import xbmcaddon
import xbmcgui
from __main__ import __addon_id__
import xml.etree.ElementTree as ET


class CacheManagement:
    Automatic = 0
    Manual = 1


class StreamQuality:
    Low = 0
    Medium = 1
    High = 2


class StartupScreen:
    NewStuff = 0
    Playlists = 1


class SettingsManager:
    __addon = None

    def __init__(self):
        self.__addon = xbmcaddon.Addon(id=__addon_id__)

    def _get_setting(self, name):
        return self.__addon.getSetting(name)

    def _set_setting(self, name, value):
        return self.__addon.setSetting(name, value)

    def get_addon_obj(self):
        return self.__addon

    def get_legal_warning_shown(self):
        return self._get_setting('_legal_warning_shown') == 'true'

    def set_legal_warning_shown(self, status):
        if status:
            str_status = 'true'
        else:
            str_status = 'false'

        return self._set_setting('_legal_warning_shown', str_status)

    def get_last_run_version(self):
        return self._get_setting('_last_run_version')

    def set_last_run_version(self, version):
        return self._set_setting('_last_run_version', version)

    def get_cache_status(self):
        return self._get_setting('general_cache_enable') == 'true'

    def get_cache_management(self):
        return int(self._get_setting('general_cache_management'))

    def get_cache_size(self):
        return int(float(self._get_setting('general_cache_size')))

    def get_audio_hide_unplayable(self):
        return self._get_setting('audio_hide_unplayable') == 'true'

    def get_audio_normalize(self):
        return self._get_setting('audio_normalize') == 'true'

    def get_audio_quality(self):
        return int(self._get_setting('audio_quality'))

    def get_misc_startup_screen(self):
        return int(self._get_setting('misc_startup_screen'))

    def show_dialog(self):
        #Show the dialog
        self.__addon.openSettings()


class GuiSettingsReader:
    __guisettings_doc = None

    def __init__(self):
        settings_path = xbmc.translatePath('special://profile/guisettings.xml')
        self.__guisettings_doc = ET.parse(settings_path)

    def get_setting(self, query):
        #Check if the argument is valid
        if query == '':
            raise KeyError()

        #Get the steps to the node
        step_list = query.split('.')
        root_tag = step_list[0]

        if len(step_list) > 1:
            path_remainder = '/'.join(step_list[1:])
        else:
            path_remainder = ''

        #Fail if the first tag does not match with the root
        if self.__guisettings_doc.getroot().tag != root_tag:
            raise KeyError()

        #Fail also if the element is not found
        el = self.__guisettings_doc.find(path_remainder)
        if el is None:
            raise KeyError()

        return el.text


class InfoValueManager:
    __infolabels = None

    def __init__(self):
        self.__infolabels = []

    def _get_main_window(self):
        return xbmcgui.Window(10000)

    def set_infolabel(self, name, value):
        self._get_main_window().setProperty(name, str(value))
        self.__infolabels.append(name)

    def get_infolabel(self, name):
        return self._get_main_window().getProperty(name)

    def deinit(self):
        window = self._get_main_window()
        for item in self.__infolabels:
            window.clearProperty(item)

########NEW FILE########
__FILENAME__ = environment
'''
Copyright 2011 Mikel Azkolain

This file is part of Spotimc.

Spotimc is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

Spotimc is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with Spotimc.  If not, see <http://www.gnu.org/licenses/>.
'''

from __main__ import __addon_path__
import sys
import os.path
import platform
import xbmc


def set_library_paths():
    #Set local library paths
    libs_dir = os.path.join(__addon_path__, "resources/libs")
    sys.path.insert(0, libs_dir)
    sys.path.insert(0, os.path.join(libs_dir, "xbmc-skinutils/src"))
    sys.path.insert(0, os.path.join(libs_dir, "cherrypy"))
    sys.path.insert(0, os.path.join(libs_dir, "taskutils/src"))
    sys.path.insert(0, os.path.join(libs_dir, "pyspotify-ctypes/src"))
    sys.path.insert(0, os.path.join(libs_dir, "pyspotify-ctypes-proxy/src"))


def has_background_support():
    return True


def get_architecture():
    try:
        machine = platform.machine()

        #Some filtering...
        if machine.startswith('armv6'):
            return 'armv6'

        elif machine.startswith('i686'):
            return 'x86'

    except:
        return None


def add_dll_path(path):
    #Build the full path and publish it
    full_path = os.path.join(__addon_path__, path)
    sys.path.append(full_path)


def set_dll_paths(base_dir):
    arch_str = get_architecture()

    if xbmc.getCondVisibility('System.Platform.Linux'):
        if arch_str in(None, 'x86'):
            add_dll_path(os.path.join(base_dir, 'linux/x86'))

        if arch_str in(None, 'x86_64'):
            add_dll_path(os.path.join(base_dir, 'linux/x86_64'))

        if arch_str in(None, 'armv6'):
            add_dll_path(os.path.join(base_dir, 'linux/armv6hf'))
            add_dll_path(os.path.join(base_dir, 'linux/armv6'))

    elif xbmc.getCondVisibility('System.Platform.Windows'):
        if arch_str in(None, 'x86'):
            add_dll_path(os.path.join(base_dir, 'windows/x86'))
        else:
            raise OSError('Sorry, only 32bit Windows is supported.')

    elif xbmc.getCondVisibility('System.Platform.OSX'):
        add_dll_path(os.path.join(base_dir, 'osx'))

    elif xbmc.getCondVisibility('System.Platform.Android'):
        add_dll_path(os.path.join(base_dir, 'android'))

    else:
        raise OSError('Sorry, this platform is not supported.')

########NEW FILE########
__FILENAME__ = gui
'''
Copyright 2011 Mikel Azkolain

This file is part of Spotimc.

Spotimc is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

Spotimc is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with Spotimc.  If not, see <http://www.gnu.org/licenses/>.
'''

import xbmc, time



def show_busy_dialog():
    xbmc.executebuiltin('ActivateWindow(busydialog)')


def hide_busy_dialog():
    xbmc.executebuiltin('Dialog.Close(busydialog)')
    while xbmc.getCondVisibility('Window.IsActive(busydialog)'):
        time.sleep(.1)

########NEW FILE########
__FILENAME__ = loaders
'''
Copyright 2011 Mikel Azkolain

This file is part of Spotimc.

Spotimc is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

Spotimc is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with Spotimc.  If not, see <http://www.gnu.org/licenses/>.
'''

import xbmc
import xbmcgui
from spotify.utils.loaders import load_albumbrowse as _load_albumbrowse


def load_albumbrowse(session, album):
    def show_busy_dialog():
        xbmc.executebuiltin('ActivateWindow(busydialog)')

    load_failed = False

    #start loading loading the album
    try:
        albumbrowse = _load_albumbrowse(
            session, album, ondelay=show_busy_dialog
        )

    #Set the pertinent flags if a timeout is reached
    except:
        load_failed = True

    #Ensure that the busy dialog gets closed
    finally:
        if xbmc.getCondVisibility('Window.IsVisible(busydialog)'):
            xbmc.executebuiltin('Dialog.Close(busydialog)')

    if load_failed:
        d = xbmcgui.Dialog()
        d.ok('Error', 'Unable to load album info')

    else:
        return albumbrowse

########NEW FILE########
__FILENAME__ = logs
'''
Copyright 2011 Mikel Azkolain

This file is part of Spotimc.

Spotimc is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

Spotimc is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with Spotimc.  If not, see <http://www.gnu.org/licenses/>.
'''



import logging, xbmc


_trans_table = {
    logging.DEBUG: xbmc.LOGDEBUG,
    logging.INFO: xbmc.LOGINFO,
    logging.WARNING: xbmc.LOGWARNING,
    logging.ERROR: xbmc.LOGERROR,
    logging.CRITICAL: xbmc.LOGSEVERE,
}


class XbmcHandler(logging.Handler):
    def emit(self, record):
        xbmc_level = _trans_table[record.levelno]
        xbmc.log(record.msg, xbmc_level)



def setup_logging():
    handler = XbmcHandler()
    root_logger = logging.getLogger()
    root_logger.addHandler(handler)



def get_logger():
    return logging.getLogger('spotimc')

########NEW FILE########
__FILENAME__ = settings
'''
Copyright 2011 Mikel Azkolain

This file is part of Spotimc.

Spotimc is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

Spotimc is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with Spotimc.  If not, see <http://www.gnu.org/licenses/>.
'''

import xbmc


class SkinSettings:
    def has_bool_true(self, name):
        return xbmc.getCondVisibility('Skin.HasSetting({0})'.format(name))

    def set_bool_true(self, name):
        xbmc.executebuiltin('Skin.SetBool({0})'.format(name))

    def toggle_bool(self, name):
        xbmc.executebuiltin('Skin.ToggleSetting({0})'.format(name))

    def get_value(self, name):
        return xbmc.getInfoLabel('Skin.String({0})'.format(name))

    def set_value(self, name, value):
        xbmc.executebuiltin('Skin.SetString({0},{1})'.format(name, value))

########NEW FILE########
__FILENAME__ = album
'''
Copyright 2011 Mikel Azkolain

This file is part of Spotimc.

Spotimc is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

Spotimc is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with Spotimc.  If not, see <http://www.gnu.org/licenses/>.
'''


import xbmc
import xbmcgui
from spotimcgui.views import BaseListContainerView, iif
from spotify import albumbrowse, session, track as _track, image
from taskutils.decorators import run_in_thread
import threading


class AlbumCallbacks(albumbrowse.AlbumbrowseCallbacks):
    def albumbrowse_complete(self, albumbrowse):
        xbmc.executebuiltin("Action(Noop)")


class MetadataUpdateCallbacks(session.SessionCallbacks):

    __event = None

    def __init__(self, event):
        self.__event = event

    def metadata_updated(self, session):
        self.__event.set()


class AlbumTracksView(BaseListContainerView):
    container_id = 1300
    list_id = 1303

    context_menu_id = 5300
    context_toggle_star = 5307

    __albumbrowse = None
    __list_rendered = None
    __update_lock = None
    __update_unavailable = None

    def __init__(self, session, album):
        self.__list_rendered = False
        self.__update_lock = threading.Lock()
        cb = AlbumCallbacks()
        self.__albumbrowse = albumbrowse.Albumbrowse(session, album, cb)

    def _play_selected_track(self, view_manager):
        item = self.get_list(view_manager).getSelectedItem()
        pos = int(item.getProperty("ListIndex"))

        #If we have a valid index
        if pos is not None:
            session = view_manager.get_var('session')
            playlist_manager = view_manager.get_var('playlist_manager')
            playlist_manager.play(self.__albumbrowse.tracks(), session, pos)

    def click(self, view_manager, control_id):
        if control_id == AlbumTracksView.list_id:
            self._play_selected_track(view_manager)

        elif control_id == AlbumTracksView.context_toggle_star:
            item = self.get_list(view_manager).getSelectedItem()
            pos = int(item.getProperty("ListIndex"))

            if pos is not None:
                session = view_manager.get_var('session')
                current_track = self.__albumbrowse.track(pos)

                if item.getProperty('IsStarred') == 'true':
                    item.setProperty('IsStarred', 'false')
                    _track.set_starred(session, [current_track], False)
                else:
                    item.setProperty('IsStarred', 'true')
                    _track.set_starred(session, [current_track], True)

    def action(self, view_manager, action_id):
        #Run parent implementation's actions
        BaseListContainerView.action(self, view_manager, action_id)

        playlist_manager = view_manager.get_var('playlist_manager')

        #Do nothing if playing, as it may result counterproductive
        if not playlist_manager.is_playing():
            if action_id == 79:
                self._play_selected_track(view_manager)

    def get_container(self, view_manager):
        return view_manager.get_window().getControl(AlbumTracksView.container_id)

    def get_list(self, view_manager):
        return view_manager.get_window().getControl(AlbumTracksView.list_id)

    def get_context_menu_id(self):
        return AlbumTracksView.context_menu_id

    def _have_multiple_discs(self):
        for item in self.__albumbrowse.tracks():
            if item.disc() > 1:
                return True

        return False

    def _set_album_info(self, view_manager):
        window = view_manager.get_window()
        pm = view_manager.get_var('playlist_manager')
        album = self.__albumbrowse.album()
        artist = self.__albumbrowse.artist()
        image_id = album.cover(image.ImageSize.Large)
        window.setProperty("AlbumCover", pm.get_image_url(image_id))
        window.setProperty("AlbumName", album.name())
        window.setProperty("ArtistName", artist.name())

    def _add_disc_separator(self, list_obj, disc_number):
        item = xbmcgui.ListItem()
        item.setProperty("IsDiscSeparator", "true")
        item.setProperty("DiscNumber", str(disc_number))
        list_obj.addItem(item)

    def _get_list_item(self, list_obj, index):
        for current_index in range(index, list_obj.size()):
            item = list_obj.getListItem(current_index)
            if item.getProperty('ListIndex') == str(index):
                return item

    def _item_available(self, item):
        return item.getProperty('IsAvailable') == 'true'

    def _track_available(self, session, track_obj):
        return (track_obj.get_availability(session) ==
                _track.TrackAvailability.Available)

    def hide(self, view_manager):

        BaseListContainerView.hide(self, view_manager)

        #Cancel any potential update loop
        self.__update_unavailable = False

    def _update_metadata(self, view_manager):
        list_obj = self.get_list(view_manager)
        session = view_manager.get_var('session')
        num_unavailable = 0

        for index, track_obj in enumerate(self.__albumbrowse.tracks()):
            item_obj = self._get_list_item(list_obj, index)
            item_available = self._item_available(item_obj)
            track_available = self._track_available(session, track_obj)

            #Increment the counter if it's unavailable
            if not track_available:
                num_unavailable += 1

            #If status changed, update it
            if item_available != track_available:
                status_str = iif(track_available, 'true', 'false')
                item_obj.setProperty('IsAvailable', status_str)

        return num_unavailable

    @run_in_thread(max_concurrency=1)
    def update_unavailable_tracks(self, view_manager):

        #Try acquiring the update lock
        if self.__update_lock.acquire(False):

            try:

                wait_time = 10
                event = threading.Event()
                session = view_manager.get_var('session')
                m_cb = MetadataUpdateCallbacks(event)
                session.add_callbacks(m_cb)
                self.__update_unavailable = True

                while self.__update_unavailable and wait_time > 0:
                    wait_time -= 1
                    event.wait(1)
                    event.clear()
                    if self._update_metadata(view_manager) == 0:
                        self.__update_unavailable = False

            finally:
                session.remove_callbacks(m_cb)
                self.__update_lock.release()

    def render(self, view_manager):
        if self.__albumbrowse.is_loaded():
            session = view_manager.get_var('session')
            pm = view_manager.get_var('playlist_manager')
            has_unavailable = False

            #Reset list
            list_obj = self.get_list(view_manager)
            list_obj.reset()

            #Set album info
            self._set_album_info(view_manager)

            #For disc grouping
            last_disc = None
            multiple_discs = self._have_multiple_discs()

            #Iterate over the track list
            for list_index, track_obj in enumerate(self.__albumbrowse.tracks()):
                #If disc was changed add a separator
                if multiple_discs and last_disc != track_obj.disc():
                    last_disc = track_obj.disc()
                    self._add_disc_separator(list_obj, last_disc)

                #Add the track item
                url, info = pm.create_track_info(track_obj, session, list_index)
                list_obj.addItem(info)

                #If the track is unavailable, add it to the list
                track_available = track_obj.get_availability(session)
                av_status = _track.TrackAvailability.Available
                if track_available != av_status and not has_unavailable:
                    has_unavailable = True

            self.update_unavailable_tracks(view_manager)

            self.__list_rendered = True

            return True

########NEW FILE########
__FILENAME__ = albums
'''
Copyright 2011 Mikel Azkolain

This file is part of Spotimc.

Spotimc is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

Spotimc is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with Spotimc.  If not, see <http://www.gnu.org/licenses/>.
'''


import xbmcgui
from spotimcgui.views import BaseListContainerView, album
from loaders import ArtistAlbumLoader, AlbumType
from spotimcgui.utils.settings import SkinSettings
from spotimcgui.utils.loaders import load_albumbrowse


class ArtistAlbumsView(BaseListContainerView):
    container_id = 2000
    list_id = 2001

    #Filtering controls
    context_menu_id = 6000
    context_play_album = 6002
    context_set_current = 6003
    filter_albums_button = 6011
    filter_singles_button = 6012
    filter_compilations_button = 6013
    filter_appears_in_button = 6014
    filter_hide_similar = 6016

    __artist = None
    __loader = None
    __settings = SkinSettings()

    def __init__(self, session, artist):
        self._init_config()
        self.__artist = artist
        self.__loader = ArtistAlbumLoader(session, artist)

    def _init_config(self):
        if not self.__settings.has_bool_true('spotimc_albumbrowse_album_init'):
            self.__settings.set_bool_true('spotimc_albumbrowse_album_init')
            self.__settings.set_bool_true('spotimc_artistbrowse_albums_albums')
            self.__settings.set_bool_true('spotimc_artistbrowse_albums_singles')
            self.__settings.set_bool_true('spotimc_artistbrowse_albums_compilations')
            self.__settings.set_bool_true('spotimc_artistbrowse_albums_appears_in')
            self.__settings.set_bool_true('spotimc_artistbrowse_albums_hide_similar')

    def _get_album_filter(self):
        filter_types = []

        if self.__settings.has_bool_true('spotimc_artistbrowse_albums_albums'):
            filter_types.append(AlbumType.Album)

        if self.__settings.has_bool_true('spotimc_artistbrowse_albums_singles'):
            filter_types.append(AlbumType.Single)

        if self.__settings.has_bool_true('spotimc_artistbrowse_albums_compilations'):
            filter_types.append(AlbumType.Compilation)

        if self.__settings.has_bool_true('spotimc_artistbrowse_albums_appears_in'):
            filter_types.append(AlbumType.AppearsIn)

        return filter_types

    def _get_similar_filter(self):
        return self.__settings.has_bool_true('spotimc_artistbrowse_albums_hide_similar')

    def _get_selected_album(self, view_manager):
        item = self.get_list(view_manager).getSelectedItem()
        real_index = int(item.getProperty('ListIndex'))
        return self.__loader.get_album(real_index)

    def _show_album(self, view_manager):
        session = view_manager.get_var('session')
        album_obj = self._get_selected_album(view_manager)
        view_manager.add_view(album.AlbumTracksView(session, album_obj))

    def _start_album_playback(self, view_manager):
        session = view_manager.get_var('session')
        album_obj = self._get_selected_album(view_manager)
        albumbrowse = load_albumbrowse(session, album_obj)

        if albumbrowse is not None:
            playlist_manager = view_manager.get_var('playlist_manager')
            playlist_manager.play(albumbrowse.tracks(), session)

    def _set_current_album(self, view_manager):
        session = view_manager.get_var('session')
        album_obj = self._get_selected_album(view_manager)
        albumbrowse = load_albumbrowse(session, album_obj)

        if albumbrowse is not None:
            playlist_manager = view_manager.get_var('playlist_manager')
            playlist_manager.set_tracks(albumbrowse.tracks(), session)

    def click(self, view_manager, control_id):
        filter_controls = [
            ArtistAlbumsView.filter_albums_button,
            ArtistAlbumsView.filter_singles_button,
            ArtistAlbumsView.filter_compilations_button,
            ArtistAlbumsView.filter_appears_in_button,
            ArtistAlbumsView.filter_hide_similar
        ]

        #If the list was clicked...
        if control_id == ArtistAlbumsView.list_id:
            self._show_album(view_manager)

        elif control_id == ArtistAlbumsView.context_play_album:
            self._start_album_playback(view_manager)
            view_manager.get_window().setFocus(self.get_container(view_manager))

        elif control_id == ArtistAlbumsView.context_set_current:
            self._set_current_album(view_manager)
            view_manager.get_window().setFocus(self.get_container(view_manager))

        elif control_id in filter_controls:
            view_manager.show(False)

    def action(self, view_manager, action_id):
        #Run parent implementation's actions
        BaseListContainerView.action(self, view_manager, action_id)

        playlist_manager = view_manager.get_var('playlist_manager')

        #Do nothing if playing, as it may result counterproductive
        if action_id == 79 and not playlist_manager.is_playing():
            self._start_album_playback(view_manager)

    def get_container(self, view_manager):
        return view_manager.get_window().getControl(ArtistAlbumsView.container_id)

    def get_list(self, view_manager):
        return view_manager.get_window().getControl(ArtistAlbumsView.list_id)

    def get_context_menu_id(self):
        return ArtistAlbumsView.context_menu_id

    def render(self, view_manager):
        if self.__loader.is_loaded():
            playlist_manager = view_manager.get_var('playlist_manager')

            l = self.get_list(view_manager)
            l.reset()

            #Get the non-similar list, if asked to do so
            if self._get_similar_filter():
                non_similar_list = self.__loader.get_non_similar_albums()

            #Set the artist name
            window = view_manager.get_window()
            window.setProperty('artistbrowse_artist_name', self.__artist.name())

            #Get the album types to be shown
            filter_types = self._get_album_filter()

            #Now loop over all the loaded albums
            for index, album in self.__loader.get_albums():
                album_type = self.__loader.get_album_type(index)
                is_in_filter = album_type in filter_types
                is_available = self.__loader.get_album_available_tracks(index) > 0
                is_similar = self._get_similar_filter() and \
                    index not in non_similar_list

                #Discard unavailable/non-filtered/similar albums
                if is_available and is_in_filter and not is_similar:
                    image_url = playlist_manager.get_image_url(album.cover())
                    item = xbmcgui.ListItem(
                        album.name(), str(album.year()), image_url
                    )
                    item.setProperty('ListIndex', str(index))
                    l.addItem(item)

            return True

########NEW FILE########
__FILENAME__ = loaders
'''
Copyright 2011 Mikel Azkolain

This file is part of Spotimc.

Spotimc is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

Spotimc is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with Spotimc.  If not, see <http://www.gnu.org/licenses/>.
'''


import xbmc
from spotify import artistbrowse, albumbrowse, link
from spotify.album import AlbumType as SpotifyAlbumType
from spotify.track import TrackAvailability
from spotify.artistbrowse import BrowseType
from taskutils.decorators import run_in_thread
from taskutils.threads import current_task
from taskutils.utils import ConditionList
import weakref


class AlbumType:
    Album = 0
    Single = 1
    Compilation = 2
    AppearsIn = 3


class AlbumCallbacks(albumbrowse.AlbumbrowseCallbacks):
    __task = None

    def __init__(self, task):
        self.__task = task

    def albumbrowse_complete(self, albumbrowse):
        self.__task.notify()


class ArtistCallbacks(artistbrowse.ArtistbrowseCallbacks):
    __artistalbumloader = None

    def __init__(self, artistalbumloader):
        self.__artistalbumloader = weakref.proxy(artistalbumloader)

    def artistbrowse_complete(self, artistbrowse):
        self.__artistalbumloader.check()


class ArtistAlbumLoader:
    __condition_list = None
    __session = None
    __artist = None
    __album_data = None
    __artistbrowse = None
    __is_loaded = None
    __sorted_albums = None
    __loader_task = None

    def __init__(self, session, artist):
        self.__condition_list = ConditionList()
        self.__session = session
        self.__artist = artist
        self.__album_data = {}
        self.__is_loaded = False
        self.__loader_task = None

        #Avoid locking this thread and continue in another one
        self.continue_in_background()

    def check(self):
        self.__loader_task.notify()

    def _wait_for_album_info(self, album_info):
        def info_is_loaded():
            return album_info.is_loaded()

        if not info_is_loaded():
            current_task().condition_wait(info_is_loaded, 10)

    def _num_available_tracks(self, album_info):
        count = 0

        #Return true if it has at least one playable track
        for track in album_info.tracks():
            track_status = track.get_availability(self.__session)
            if track_status == TrackAvailability.Available:
                count += 1

        return count

    def _is_same_artist(self, artist1, artist2):
        album1_str = link.create_from_artist(artist1).as_string()
        album2_str = link.create_from_artist(artist2).as_string()

        return album1_str == album2_str

    def _get_album_type(self, album):
        if album.type() == SpotifyAlbumType.Single:
            return AlbumType.Single

        elif album.type() == SpotifyAlbumType.Compilation:
            return AlbumType.Compilation

        if not self._is_same_artist(self.__artist, album.artist()):
            return AlbumType.AppearsIn

        else:
            return AlbumType.Album

    @run_in_thread(group='load_artist_albums', max_concurrency=5)
    def load_album_info(self, index, album):

        # Directly discard unavailable albums
        if not album.is_available():
            self.__album_data[index] = {
                'available_tracks': 0,
                'type': self._get_album_type(album),
            }

        # Otherwise load its data
        else:
            cb = AlbumCallbacks(current_task())
            album_info = albumbrowse.Albumbrowse(self.__session, album, cb)

            # Now wait until it's loaded
            self._wait_for_album_info(album_info)

            # Populate its data
            self.__album_data[index] = {
                'available_tracks': self._num_available_tracks(album_info),
                'type': self._get_album_type(album),
            }

            # Tell that we're done
            self.check()

    def _wait_for_album_list(self):

        #Add the artistbrowse callbacks
        self.__artistbrowse = artistbrowse.Artistbrowse(
            self.__session, self.__artist,
            BrowseType.NoTracks, ArtistCallbacks(self)
        )

        if not self.__artistbrowse.is_loaded():
            current_task().condition_wait(
                self.__artistbrowse.is_loaded, 60  # Should be enough?
            )

    def _add_album_processed_check(self, index):
        def album_is_processed():
            return index in self.__album_data

        if not album_is_processed():
            self.__condition_list.add_condition(album_is_processed)

    @run_in_thread(group='load_artist_albums', max_concurrency=1)
    def continue_in_background(self):

        # Set the reference to the current task
        self.__loader_task = current_task()

        # Wait until the album list got loaded
        self._wait_for_album_list()

        # Now load albumbrowse data from each one
        for index, album in enumerate(self.__artistbrowse.albums()):

            # Add a condition for the next wait
            self._add_album_processed_check(index)

            # Start loading the info in the background
            self.load_album_info(index, album)

        # Now wait until all info gets loaded
        current_task().condition_wait(self.__condition_list, 60)

        # Final steps...
        self.__is_loaded = True
        xbmc.executebuiltin("Action(Noop)")

    def is_loaded(self):
        return self.__is_loaded

    def get_album_available_tracks(self, index):
        return self.__album_data[index]['available_tracks']

    def get_album_type(self, index):
        return self.__album_data[index]['type']

    def get_album(self, index):
        return self.__artistbrowse.album(index)

    def get_non_similar_albums(self):
        name_dict = {}

        for index, album in self.get_albums():
            name = album.name()
            available_tracks = self.get_album_available_tracks(index)

            # If that name is new to us just store it
            if name not in name_dict:
                name_dict[name] = (index, available_tracks)

            # If the album has more playable tracks than the stored one
            elif available_tracks > name_dict[name][1]:
                name_dict[name] = (index, available_tracks)

        # Now return the list if indexes
        return [item[0] for item in name_dict.itervalues()]

    def get_albums(self):
        def sort_func(album_index):
            # Sort by album type and then by year (desc)
            return (
                self.get_album_type(album_index),
                -self.__artistbrowse.album(album_index).year()
            )

        # Do nothing if is loading
        if self.is_loaded():
            # Build the sorted album list if needed
            if self.__sorted_albums is None:
                album_indexes = self.__album_data.keys()
                sorted_indexes = sorted(album_indexes, key=sort_func)
                ab = self.__artistbrowse
                self.__sorted_albums = [
                    (index, ab.album(index)) for index in sorted_indexes
                ]

            return self.__sorted_albums

########NEW FILE########
__FILENAME__ = tracks
'''
Copyright 2011 Mikel Azkolain

This file is part of Spotimc.

Spotimc is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

Spotimc is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with Spotimc.  If not, see <http://www.gnu.org/licenses/>.
'''


import xbmcgui
from spotimcgui.views import BaseView


class ArtistTracksView(BaseView):
    __group_id = 1400
    __list_id = 1401

    def click(self, view_manager, window, control_id):
        pass

    def _get_list(self, window):
        return window.getControl(ArtistTracksView.__list_id)

    def _add_track(self, list, title, path, duration, number):
        item = xbmcgui.ListItem(path=path)
        item.setInfo(
            "music",
            {"title": title, "duration": duration, "tracknumber": number}
        )
        list.addItem(item)

    def _populate_list(self, window):
        l = self._get_list(window)
        l.reset()

        self._add_track(l, "Track 1", "", 186, 1)
        self._add_track(l, "Track 2", "", 120, 2)
        self._add_track(l, "Track 3", "", 5, 3)
        self._add_track(l, "Track 4", "", 389, 4)
        self._add_track(l, "Track 5", "", 7200, 5)
        self._add_track(l, "Track 1", "", 186, 6)
        self._add_track(l, "Track 2", "", 120, 7)
        self._add_track(l, "Track 3", "", 5, 8)
        self._add_track(l, "Track 4", "", 389, 9)
        self._add_track(l, "Track 5", "", 7200, 10)
        self._add_track(l, "Track 1", "", 186, 11)
        self._add_track(l, "Track 2", "", 120, 12)
        self._add_track(l, "Track 3", "", 5, 13)
        self._add_track(l, "Track 4", "", 389, 14)
        self._add_track(l, "Track 5", "", 7200, 15)
        self._add_track(l, "Track 1", "", 186, 16)
        self._add_track(l, "Track 2", "", 120, 17)
        self._add_track(l, "Track 3", "", 5, 18)
        self._add_track(l, "Track 4", "", 389, 19)
        self._add_track(l, "Track 5", "", 7200, 100)

        window.setProperty("ArtistName", "Artist Name")

    def show(self, window):
        self._populate_list(window)
        c = window.getControl(ArtistTracksView.__group_id)
        c.setVisibleCondition("true")

    def hide(self, window):
        c = window.getControl(ArtistTracksView.__group_id)
        c.setVisibleCondition("false")

########NEW FILE########
__FILENAME__ = home
'''
Copyright 2011 Mikel Azkolain

This file is part of Spotimc.

Spotimc is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

Spotimc is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with Spotimc.  If not, see <http://www.gnu.org/licenses/>.
'''


import spotimcgui.views as views
import xbmcgui


class HomeMenuView(views.BaseView):
    __group_id = 1100
    __selected_item = 0

    def _get_list(self, window):
        return window.getControl(HomeMenuView.__group_id)

    def _populate_list(self, window):
        l = self._get_list(window)
        l.reset()
        l.addItem(xbmcgui.ListItem('New Stuff', '', 'home-menu/new-stuff-active.png'))
        l.addItem(xbmcgui.ListItem('Playlists', '', 'home-menu/playlists-active.png'))
        l.addItem(xbmcgui.ListItem('Search', '', 'home-menu/search-active.png'))
        l.addItem(xbmcgui.ListItem('Toplists', '', 'home-menu/toplists-active.png'))
        l.addItem(xbmcgui.ListItem('Radio', '', 'home-menu/radio-active.png'))
        l.addItem(xbmcgui.ListItem('Settings', '', 'home-menu/settings-active.png'))
        l.addItem(xbmcgui.ListItem('Logout', '', 'home-menu/logout-active.png'))
        l.addItem(xbmcgui.ListItem('Exit', '', 'home-menu/exit-active.png'))
        l.selectItem(self.__selected_item)

    def click(self, window, control_id):
        print "control id: %d" % control_id
        print "list pos: %d" % self._get_list(window).getSelectedPosition()

    def show(self, window):
        l = self._get_list(window)
        l.setVisibleCondition("true")
        print "show!"

        #Populate the main menu
        self._populate_list(window)

    def hide(self, window):
        l = self._get_list(window)
        l.setVisibleCondition("false")
        print "hide!"

        #Store selected item
        self.__selected_item = l.getSelectedPosition()

########NEW FILE########
__FILENAME__ = more
'''
Copyright 2011 Mikel Azkolain

This file is part of Spotimc.

Spotimc is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

Spotimc is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with Spotimc.  If not, see <http://www.gnu.org/licenses/>.
'''


import xbmcgui
from spotify import Bitrate
from spotimcgui.views import BaseListContainerView
from spotimcgui.settings import SettingsManager, CacheManagement, StreamQuality


class MoreView(BaseListContainerView):
    container_id = 1900
    list_id = 1901

    def _do_logout(self, view_manager):
        #Ask the user first
        dlg = xbmcgui.Dialog()
        response = dlg.yesno(
            'Sign Off',
            'This will forget the remembered user.',
            'Are you sure?'
        )

        if response:
            session = view_manager.get_var('session')
            session.forget_me()
            view_manager.get_window().close()

    def _do_settings(self, view_manager):
        settings = SettingsManager()
        session = view_manager.get_var('session')

        #Store current values before they change
        before_cache_status = settings.get_cache_status()
        before_cache_management = settings.get_cache_management()
        before_cache_size = settings.get_cache_size()
        before_audio_normalize = settings.get_audio_normalize()
        before_audio_quality = settings.get_audio_quality()

        #Show the dialog
        settings.show_dialog()

        after_cache_status = settings.get_cache_status()
        after_cache_management = self.get_cache_management()
        after_cache_size = settings.get_cache_size()
        after_audio_normalize = settings.get_audio_normalize()
        after_audio_quality = settings.get_audio_quality()

        #Change these only if cache was and is enabled
        if before_cache_status and after_cache_status:

            #If cache management changed
            if before_cache_management != after_cache_management:
                if after_cache_management == CacheManagement.Automatic:
                    session.set_cache_size(0)
                elif after_cache_management == CacheManagement.Manual:
                    session.set_cache_size(after_cache_size * 1024)

            #If manual size changed
            if (after_cache_management == CacheManagement.Manual and
                    before_cache_size != after_cache_size):
                session.set_cache_size(after_cache_size * 1024)

        #Change volume normalization
        if before_audio_normalize != after_audio_normalize:
            session.set_volume_normalization(after_audio_normalize)

        #Change stream quality
        #FIXME: Repeated code, should be moved to utils
        br_map = {
            StreamQuality.Low: Bitrate.Rate96k,
            StreamQuality.Medium: Bitrate.Rate160k,
            StreamQuality.High: Bitrate.Rate320k,
        }
        if before_audio_quality != after_audio_quality:
            session.preferred_bitrate(br_map[after_audio_quality])

    def _handle_list_click(self, view_manager):
        item = self.get_list(view_manager).getSelectedItem()

        if item is not None:
            key = item.getLabel2()

            if key == 'settings':
                self._do_settings(view_manager)

            elif key == 'sign-off':
                self._do_logout(view_manager)

    def click(self, view_manager, control_id):
        if control_id == MoreView.list_id:
            self._handle_list_click(view_manager)

    def get_container(self, view_manager):
        return view_manager.get_window().getControl(MoreView.container_id)

    def get_list(self, view_manager):
        return view_manager.get_window().getControl(MoreView.list_id)

    def _add_item(self, list_obj, key, label, icon):
        list_obj.addItem(
            xbmcgui.ListItem(label=label, label2=key, iconImage=icon)
        )

    def render(self, view_manager):
        list_obj = self.get_list(view_manager)
        list_obj.reset()

        #Add the items
        self._add_item(list_obj, 'settings', "Settings",
                       "common/more-settings-icon.png")
        self._add_item(list_obj, 'sign-off', "Sign Off",
                       "common/more-logout-icon.png")

        return True

########NEW FILE########
__FILENAME__ = newstuff
'''
Copyright 2011 Mikel Azkolain

This file is part of Spotimc.

Spotimc is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

Spotimc is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with Spotimc.  If not, see <http://www.gnu.org/licenses/>.
'''


import xbmc
import xbmcgui
from spotimcgui.views import BaseListContainerView
from spotimcgui.views import album
from spotimcgui.utils.loaders import load_albumbrowse
from spotify import search
from taskutils.decorators import run_in_thread


class NewStuffCallbacks(search.SearchCallbacks):
    def search_complete(self, result):
        xbmc.executebuiltin("Action(Noop)")


class NewStuffView(BaseListContainerView):
    container_id = 1200
    list_id = 1201
    context_menu_id = 5200
    context_play_album = 5202
    context_set_current = 5203

    __search = None
    __initialized = None

    @run_in_thread
    def _initialize(self, session):
        cb = NewStuffCallbacks()
        self.__search = search.Search(
            session, 'tag:new', album_count=60, callbacks=cb
        )

        self.__initialized = True

        # FIXME: Poor man's way of dealing with race conditions (resend notifications)
        xbmc.executebuiltin("Action(Noop)")

    def __init__(self, session):
        self._initialize(session)

    def _get_selected_album(self, view_manager):
        pos = self.get_list(view_manager).getSelectedPosition()
        return self.__search.album(pos)

    def _show_album(self, view_manager):
        session = view_manager.get_var('session')
        album_obj = self._get_selected_album(view_manager)
        view_manager.add_view(album.AlbumTracksView(session, album_obj))

    def _start_album_playback(self, view_manager):
        session = view_manager.get_var('session')
        album_obj = self._get_selected_album(view_manager)
        albumbrowse = load_albumbrowse(session, album_obj)

        if albumbrowse is not None:
            playlist_manager = view_manager.get_var('playlist_manager')
            playlist_manager.play(albumbrowse.tracks(), session)

    def _set_current_album(self, view_manager):
        session = view_manager.get_var('session')
        album_obj = self._get_selected_album(view_manager)
        albumbrowse = load_albumbrowse(session, album_obj)

        if albumbrowse is not None:
            playlist_manager = view_manager.get_var('playlist_manager')
            playlist_manager.set_tracks(albumbrowse.tracks(), session)

    def click(self, view_manager, control_id):
        #Silently ignore events when not intialized
        if not self.__initialized:
            return

        #If the list was clicked...
        if control_id == NewStuffView.list_id:
            self._show_album(view_manager)

        elif control_id == NewStuffView.context_play_album:
            self._start_album_playback(view_manager)
            view_manager.get_window().setFocus(self.get_container(view_manager))

        elif control_id == NewStuffView.context_set_current:
            self._set_current_album(view_manager)
            view_manager.get_window().setFocus(self.get_container(view_manager))

    def action(self, view_manager, action_id):
        #Silently ignore events when not intialized
        if not self.__initialized:
            return

        #Run parent implementation's actions
        BaseListContainerView.action(self, view_manager, action_id)

        playlist_manager = view_manager.get_var('playlist_manager')

        #Do nothing if playing, as it may result counterproductive
        if action_id == 79 and not playlist_manager.is_playing():
            self._start_album_playback(view_manager)

    def get_container(self, view_manager):
        return view_manager.get_window().getControl(NewStuffView.container_id)

    def get_list(self, view_manager):
        return view_manager.get_window().getControl(NewStuffView.list_id)

    def get_context_menu_id(self):
        return NewStuffView.context_menu_id

    def render(self, view_manager):
        if not self.__initialized:
            return False

        if not self.__search.is_loaded():
            return False

        list_obj = self.get_list(view_manager)
        list_obj.reset()
        playlist_manager = view_manager.get_var('playlist_manager')

        for album in self.__search.albums():
            item = xbmcgui.ListItem(
                album.name(),
                album.artist().name(),
                playlist_manager.get_image_url(album.cover())
            )
            list_obj.addItem(item)

        return True

########NEW FILE########
__FILENAME__ = nowplaying
'''
Copyright 2011 Mikel Azkolain

This file is part of Spotimc.

Spotimc is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

Spotimc is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with Spotimc.  If not, see <http://www.gnu.org/licenses/>.
'''


import xbmc
from spotimcgui.views import BaseContainerView
from spotimcgui.views.artists import open_artistbrowse_albums
from spotimcgui.views.album import AlbumTracksView


class PlayerCallbacks(xbmc.Player):
    def onPlayBackStopped(self):
        xbmc.executebuiltin('SetFocus(212)')
    
    
    def onPlayBackEnded(self):
        pl = xbmc.PlayList(xbmc.PLAYLIST_MUSIC)
        if pl.getposition() < 0:
            xbmc.executebuiltin('SetFocus(212)')


class NowPlayingView(BaseContainerView):
    container_id = 1600

    browse_artist_button = 1621
    browse_album_button = 1622
    
    __player_callbacks = None

    def _get_current_track(self, view_manager):
        playlist_manager = view_manager.get_var('playlist_manager')
        session = view_manager.get_var('session')
        return playlist_manager.get_current_item(session)

    def _do_browse_artist(self, view_manager):
        track = self._get_current_track(view_manager)
        artist_list = [artist for artist in track.artists()]
        open_artistbrowse_albums(view_manager, artist_list)

    def _do_browse_album(self, view_manager):
        track = self._get_current_track(view_manager)
        session = view_manager.get_var('session')
        v = AlbumTracksView(session, track.album())
        view_manager.add_view(v)

    def click(self, view_manager, control_id):
        if control_id == NowPlayingView.browse_artist_button:
            self._do_browse_artist(view_manager)

        elif control_id == NowPlayingView.browse_album_button:
            self._do_browse_album(view_manager)

    def get_container(self, view_manager):
        return view_manager.get_window().getControl(NowPlayingView.container_id)
    
    def show(self, view_manager, set_focus=True):
        self.__player_callbacks = PlayerCallbacks()
        return BaseContainerView.show(self, view_manager, set_focus=True)
    
    def hide(self, view_manager):
        self.__player_callbacks = None
        BaseContainerView.hide(self, view_manager)

    def render(self, view_manager):
        pl = xbmc.PlayList(xbmc.PLAYLIST_MUSIC)
        if pl.getposition() < 0:
            xbmc.executebuiltin('SetFocus(212)')
        return True

########NEW FILE########
__FILENAME__ = detail
'''
Copyright 2011 Mikel Azkolain

This file is part of Spotimc.

Spotimc is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

Spotimc is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with Spotimc.  If not, see <http://www.gnu.org/licenses/>.
'''


import loaders
from spotimcgui.views import BaseListContainerView, iif
from spotify import track
from spotimcgui.views.album import AlbumTracksView
from spotimcgui.views.artists import open_artistbrowse_albums
from spotimcgui.settings import SettingsManager


class PlaylistDetailView(BaseListContainerView):
    container_id = 1800
    list_id = 1801

    BrowseArtistButton = 5811
    BrowseAlbumButton = 5812

    context_menu_id = 5800
    context_toggle_star = 5813

    __loader = None
    __playlist = None

    def __init__(self, session, playlist, playlist_manager):
        self.__playlist = playlist
        self.__loader = loaders.FullPlaylistLoader(
            session, playlist, playlist_manager
        )

    def _set_loader(self, loader):
        self.__loader = loader

    def _set_playlist(self, playlist):
        self.__playlist = playlist

    def _browse_artist(self, view_manager):
        item = self.get_list(view_manager).getSelectedItem()
        pos = int(item.getProperty('ListIndex'))
        track_obj = self.__loader.get_track(pos)
        artist_list = [artist for artist in track_obj.artists()]
        open_artistbrowse_albums(view_manager, artist_list)

    def _play_selected_track(self, view_manager):
        session = view_manager.get_var('session')
        item = self.get_list(view_manager).getSelectedItem()
        pos = int(item.getProperty('ListIndex'))
        playlist_manager = view_manager.get_var('playlist_manager')
        playlist_manager.play(self.__loader.get_tracks(), session, pos)

    def click(self, view_manager, control_id):
        if control_id == PlaylistDetailView.list_id:
            self._play_selected_track(view_manager)

        elif control_id == PlaylistDetailView.BrowseArtistButton:
            self._browse_artist(view_manager)

        elif control_id == PlaylistDetailView.BrowseAlbumButton:
            item = self.get_list(view_manager).getSelectedItem()
            pos = int(item.getProperty('ListIndex'))
            album = self.__loader.get_track(pos).album()
            v = AlbumTracksView(view_manager.get_var('session'), album)
            view_manager.add_view(v)

        elif control_id == PlaylistDetailView.context_toggle_star:
            item = self.get_list(view_manager).getSelectedItem()
            pos = int(item.getProperty("ListIndex"))

            if pos is not None:
                session = view_manager.get_var('session')
                current_track = self.__loader.get_track(pos)

                if item.getProperty('IsStarred') == 'true':
                    item.setProperty('IsStarred', 'false')
                    track.set_starred(session, [current_track], False)
                else:
                    item.setProperty('IsStarred', 'true')
                    track.set_starred(session, [current_track], True)

    def action(self, view_manager, action_id):
        #Run parent implementation's actions
        BaseListContainerView.action(self, view_manager, action_id)

        playlist_manager = view_manager.get_var('playlist_manager')

        #Do nothing if playing, as it may result counterproductive
        if not playlist_manager.is_playing():
            if action_id == 79:
                self._play_selected_track(view_manager)

    def get_container(self, view_manager):
        return view_manager.get_window().getControl(
            PlaylistDetailView.container_id)

    def get_list(self, view_manager):
        return view_manager.get_window().getControl(PlaylistDetailView.list_id)

    def get_context_menu_id(self):
        return PlaylistDetailView.context_menu_id

    def _get_playlist_length_str(self):
        total_duration = 0

        for track in self.__playlist.tracks():
            total_duration += track.duration() / 1000

        #Now the string ranges
        one_minute = 60
        one_hour = 3600
        one_day = 3600 * 24

        if total_duration > one_day:
            num_days = int(round(total_duration / one_day))
            if num_days == 1:
                return 'one day'
            else:
                return '%d days' % num_days

        elif total_duration > one_hour:
            num_hours = int(round(total_duration / one_hour))
            if num_hours == 1:
                return 'one hour'
            else:
                return '%d hours' % num_hours

        else:
            num_minutes = int(round(total_duration / one_minute))
            if num_minutes == 1:
                return 'one minute'
            else:
                return '%d minutes' % num_minutes

    def _set_playlist_properties(self, view_manager):
        window = view_manager.get_window()

        #Playlist name
        window.setProperty("PlaylistDetailName", self.__loader.get_name())

        #Owner info
        session = view_manager.get_var('session')
        current_username = session.user().canonical_name()
        playlist_username = self.__playlist.owner().canonical_name()
        show_owner = current_username != playlist_username
        window.setProperty("PlaylistDetailShowOwner",
                           iif(show_owner, "true", "false"))
        if show_owner:
            window.setProperty("PlaylistDetailOwner", str(playlist_username))

        #Collaboratie status
        is_collaborative_str = iif(self.__playlist.is_collaborative(),
                                   "true", "false")
        window.setProperty("PlaylistDetailCollaborative", is_collaborative_str)

        #Length data
        window.setProperty("PlaylistDetailNumTracks",
                           str(self.__playlist.num_tracks()))
        window.setProperty("PlaylistDetailDuration",
                           self._get_playlist_length_str())

        #Subscribers
        window.setProperty("PlaylistDetailNumSubscribers",
                           str(self.__playlist.num_subscribers()))

    def _set_playlist_image(self, view_manager, thumbnails):
        if len(thumbnails) > 0:
            window = view_manager.get_window()

            #Set cover layout info
            cover_layout_str = iif(len(thumbnails) < 4, "one", "four")
            window.setProperty("PlaylistDetailCoverLayout", cover_layout_str)

            #Now loop to set all the images
            for idx, thumb_item in enumerate(thumbnails):
                item_num = idx + 1
                is_remote = thumb_item.startswith("http://")
                is_remote_str = iif(is_remote, "true", "false")
                prop = "PlaylistDetailCoverItem{0:d}".format(item_num)
                window.setProperty(prop, thumb_item)
                prop = "PlaylistDetailCoverItem{0:d}IsRemote".format(item_num)
                window.setProperty(prop, is_remote_str)

    def render(self, view_manager):
        if self.__loader.is_loaded():
            session = view_manager.get_var('session')
            pm = view_manager.get_var('playlist_manager')
            list_obj = self.get_list(view_manager)
            sm = SettingsManager()

            #Set the thumbnails
            self._set_playlist_image(view_manager,
                                     self.__loader.get_thumbnails())

            #And the properties
            self._set_playlist_properties(view_manager)

            #Clear the list
            list_obj.reset()

            #Draw the items on the list
            for list_index, track_obj in enumerate(self.__loader.get_tracks()):
                show_track = (
                    track_obj.is_loaded() and
                    track_obj.error() == 0 and
                    (
                        (track_obj.get_availability(session) ==
                            track.TrackAvailability.Available) or
                        not sm.get_audio_hide_unplayable()
                    )
                )

                if show_track:
                    url, info = pm.create_track_info(track_obj, session,
                                                     list_index)
                    list_obj.addItem(info)

            return True


class SpecialPlaylistDetailView(PlaylistDetailView):
    def __init__(self, session, playlist, playlist_manager, name, thumbnails):
        self._set_playlist(playlist)
        loader = loaders.SpecialPlaylistLoader(
            session, playlist, playlist_manager, name, thumbnails
        )
        self._set_loader(loader)

########NEW FILE########
__FILENAME__ = list
'''
Copyright 2011 Mikel Azkolain

This file is part of Spotimc.

Spotimc is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

Spotimc is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with Spotimc.  If not, see <http://www.gnu.org/licenses/>.
'''


import xbmc
import xbmcgui
import loaders
import detail
from spotimcgui.views import BaseListContainerView, iif
from taskutils.decorators import run_in_thread


class PlaylistView(BaseListContainerView):
    container_id = 1700
    list_id = 1701

    context_menu_id = 5700
    context_play_playlist = 5702
    context_set_current = 5703

    __starred_loader = None
    __inbox_loader = None
    __container_loader = None

    __initialized = None

    @run_in_thread
    def _initialize(self, session, container, playlist_manager):
        #Add the starred playlist
        self.__starred_loader = loaders.SpecialPlaylistLoader(
            session, session.starred_create(), playlist_manager,
            'Starred', ["common/pl-starred.png"]
        )

        #And the inbox one
        self.__inbox_loader = loaders.SpecialPlaylistLoader(
            session, session.inbox_create(), playlist_manager,
            'Inbox', ['common/pl-inbox.png']
        )

        #And the rest of the playlists
        self.__container_loader = loaders.ContainerLoader(
            session, container, playlist_manager
        )

        self.__initialized = True

        # FIXME: Poor man's way of dealing with race conditions (resend
        # notifications)
        xbmc.executebuiltin("Action(Noop)")

    def __init__(self, session, container, playlist_manager):
        self._initialize(session, container, playlist_manager)

    def _get_playlist_loader(self, playlist_id):
        if playlist_id == 'starred':
            return self.__starred_loader

        elif playlist_id == 'inbox':
            return self.__inbox_loader

        else:
            return self.__container_loader.playlist(int(playlist_id))

    def _get_selected_playlist(self, view_manager):
        item = self.get_list(view_manager).getSelectedItem()
        return item.getProperty('PlaylistId')

    def _show_selected_playlist(self, view_manager):
        pm = view_manager.get_var('playlist_manager')
        session = view_manager.get_var('session')
        playlist_id = self._get_selected_playlist(view_manager)
        loader_obj = self._get_playlist_loader(playlist_id)

        #Special treatment for starred & inbox
        if playlist_id in ['starred', 'inbox']:
            view_obj = detail.SpecialPlaylistDetailView(
                session, loader_obj.get_playlist(), pm,
                loader_obj.get_name(), loader_obj.get_thumbnails()
            )

        else:
            view_obj = detail.PlaylistDetailView(
                session, loader_obj.get_playlist(), pm
            )

        view_manager.add_view(view_obj)

    def _start_playlist_playback(self, view_manager):
        playlist_id = self._get_selected_playlist(view_manager)
        track_list = self._get_playlist_loader(playlist_id).get_tracks()
        session = view_manager.get_var('session')
        playlist_manager = view_manager.get_var('playlist_manager')
        playlist_manager.play(track_list, session)

    def _set_current_playlist(self, view_manager):
        playlist_id = self._get_selected_playlist(view_manager)
        track_list = self._get_playlist_loader(playlist_id).get_tracks()
        playlist_manager = view_manager.get_var('playlist_manager')
        session = view_manager.get_var('session')
        playlist_manager.set_tracks(track_list, session)

    def click(self, view_manager, control_id):
        #Silently ignore events when not intialized
        if not self.__initialized:
            return

        if control_id == PlaylistView.list_id:
            self._show_selected_playlist(view_manager)

        elif control_id == PlaylistView.context_play_playlist:
            self._start_playlist_playback(view_manager)
            view_manager.get_window().setFocus(
                self.get_container(view_manager))

        elif control_id == PlaylistView.context_set_current:
            self._set_current_playlist(view_manager)
            view_manager.get_window().setFocus(
                self.get_container(view_manager))

    def action(self, view_manager, action_id):
        #Silently ignore events when not intialized
        if not self.__initialized:
            return

        #Run parent implementation's actions
        BaseListContainerView.action(self, view_manager, action_id)

        playlist_manager = view_manager.get_var('playlist_manager')

        #Do nothing if playing, as it may result counterproductive
        if action_id == 79 and not playlist_manager.is_playing():
            self._start_playlist_playback(view_manager)

    def get_container(self, view_manager):
        return view_manager.get_window().getControl(PlaylistView.container_id)

    def get_list(self, view_manager):
        return view_manager.get_window().getControl(PlaylistView.list_id)

    def get_context_menu_id(self):
        return PlaylistView.context_menu_id

    def _add_playlist(self, list, key, loader, show_owner):
        item = xbmcgui.ListItem()
        item.setProperty("PlaylistId", str(key))
        item.setProperty("PlaylistName", loader.get_name())
        item.setProperty("PlaylistNumTracks", str(loader.get_num_tracks()))

        item.setProperty("PlaylistShowOwner", iif(show_owner, "true", "false"))
        if show_owner:
            owner_name = loader.get_playlist().owner().canonical_name()
            item.setProperty("PlaylistOwner", str(owner_name))

        #Collaborative status
        is_collaborative = loader.get_is_collaborative()
        item.setProperty("PlaylistCollaborative", iif(is_collaborative,
                                                      "true", "false"))

        #Thumbnails
        thumbnails = loader.get_thumbnails()
        if len(thumbnails) > 0:
            #Set cover info
            item.setProperty("CoverLayout",
                             iif(len(thumbnails) < 4, "one", "four"))

            #Now loop to set all the images
            for idx, thumb_item in enumerate(thumbnails):
                item_num = idx + 1
                is_remote = thumb_item.startswith("http://")
                item.setProperty("CoverItem{0:d}".format(item_num), thumb_item)
                item.setProperty("CoverItem{0:d}IsRemote".format(item_num),
                                 iif(is_remote, "true", "false"))

        list.addItem(item)

    def all_loaded(self):
        return (
            (self.__starred_loader.is_loaded() or
                self.__starred_loader.has_errors()) and
            (self.__inbox_loader.is_loaded() or
                self.__inbox_loader.has_errors()) and
            self.__container_loader.is_loaded()
        )

    def render(self, view_manager):
        if not self.__initialized:
            return False

        if not self.all_loaded():
            return False

        #Clear the list
        list = self.get_list(view_manager)
        list.reset()

        #Get the logged in user
        container_user = self.__container_loader.get_container().owner()
        container_username = None
        if container_user is not None:
            container_username = container_user.canonical_name()

        #Add the starred and inbox playlists
        self._add_playlist(list, 'starred', self.__starred_loader, False)
        self._add_playlist(list, 'inbox', self.__inbox_loader, False)

        #And iterate over the rest of the playlists
        for key, item in enumerate(self.__container_loader.playlists()):
            show_playlist = (
                item is not None and
                not item.has_errors() and
                item.is_loaded()
            )

            if show_playlist:
                playlist_username = item.get_playlist().owner().canonical_name()
                show_owner = playlist_username != container_username
                self._add_playlist(list, key, item, show_owner)

        return True

########NEW FILE########
__FILENAME__ = loaders
'''
Copyright 2011 Mikel Azkolain

This file is part of Spotimc.

Spotimc is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

Spotimc is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with Spotimc.  If not, see <http://www.gnu.org/licenses/>.
'''


import xbmc
import weakref
import threading
from spotify import playlist, playlistcontainer, ErrorType
from spotify.utils.iterators import CallbackIterator
from taskutils.decorators import run_in_thread
from taskutils.threads import current_task
from taskutils.utils import ConditionList
from spotimcgui.utils.logs import get_logger


class PlaylistCallbacks(playlist.PlaylistCallbacks):
    __playlist_loader = None

    def __init__(self, playlist_loader):
        self.__playlist_loader = weakref.proxy(playlist_loader)

    def playlist_state_changed(self, playlist):
        self.__playlist_loader.check()

    def playlist_metadata_updated(self, playlist):
        self.__playlist_loader.check()


class BasePlaylistLoader:
    __playlist = None
    __playlist_manager = None
    __conditions = None
    __loader_task = None
    __loader_lock = None

    # Playlist attributes
    __name = None
    __num_tracks = None
    __thumbnails = None
    __is_collaborative = None
    __is_loaded = None
    __has_errors = None
    __has_changes = None

    def __init__(self, session, playlist, playlist_manager):

        #Initialize all instance vars
        self.__playlist = playlist
        self.__playlist_manager = playlist_manager
        self.__conditions = ConditionList()
        self.__loader_lock = threading.Lock()
        self.__is_loaded = False
        self.__has_errors = False
        self.__thumbnails = []

        #Fire playlist loading if neccesary
        if not playlist.is_in_ram(session):
            playlist.set_in_ram(session, True)

        #Add the playlist callbacks
        self.__playlist.add_callbacks(PlaylistCallbacks(self))

        #Finish the rest in the background
        self.load_in_background()

    @run_in_thread(group='load_playlists', max_concurrency=10)
    def load_in_background(self):

        #Avoid entering this loop multiple times
        if self.__loader_lock.acquire(False):
            try:

                #Set the current task object
                self.__loader_task = current_task()

                #Reset everyting
                self._set_changes(False)
                self._set_error(False)

                #And call the method that does the actual loading task
                self._load()

            except:

                #Set the playlist's error flag
                self._set_error(True)

            finally:

                #Release and clear everything
                self.__loader_task = None
                self.__loader_lock.release()

                #If changes or errors were detected...
                if self.has_changes() or self.has_errors():
                    self.end_loading()

    def get_playlist(self):
        return self.__playlist

    def _set_thumbnails(self, thumbnails):
        self.__thumbnails = thumbnails

    def get_thumbnails(self):
        return self.__thumbnails

    def _set_name(self, name):
        self.__name = name

    def get_name(self):
        return self.__name

    def get_num_tracks(self):
        return self.__num_tracks

    def get_tracks(self):
        return self.__playlist.tracks()

    def get_track(self, index):
        track_list = self.get_tracks()
        return track_list[index]

    def get_is_collaborative(self):
        return self.__is_collaborative

    def _track_is_ready(self, track, test_album=True, test_artists=True):
        def album_is_loaded():
            album = track.album()
            return album is not None and album.is_loaded()

        def artists_are_loaded():
            for item in track.artists():
                if item is None or not item.is_loaded():
                    return False
            return True

        #If track has an error stop further processing
        if track.error() not in [ErrorType.Ok, ErrorType.IsLoading]:
            return True

        #Always test for the track data
        if not track.is_loaded():
            return False

        #If album data was requested
        elif test_album and not album_is_loaded():
            return False

        #If artist data was requested
        elif test_artists and not artists_are_loaded():
            return False

        #Otherwise everything was ok
        else:
            return True

    def _wait_for_playlist(self):
        if not self.__playlist.is_loaded():
            self.__conditions.add_condition(self.__playlist.is_loaded)
            current_task.condition_wait(self.__conditions, 10)

    def _wait_for_track_metadata(self, track):
        def test_is_loaded():
            return self._track_is_ready(
                track, test_album=True, test_artists=False
            )

        if not test_is_loaded():
            self.__conditions.add_condition(test_is_loaded)
            current_task.condition_wait(self.__conditions, 10)

    def _load_thumbnails(self):
        pm = self.__playlist_manager

        #If playlist has an image
        playlist_image = self.__playlist.get_image()
        if playlist_image is not None:
            thumbnails = [pm.get_image_url(playlist_image)]

        #Otherwise get them from the album covers
        else:
            thumbnails = []
            for item in self.__playlist.tracks():
                #Wait until this track is fully loaded
                self._wait_for_track_metadata(item)

                #Check if item was loaded without errors
                if item.is_loaded() and item.error() == 0:
                    #Append the cover if it's new
                    image_id = item.album().cover()
                    image_url = pm.get_image_url(image_id)
                    if image_url not in thumbnails:
                        thumbnails.append(image_url)

                    #If we reached to the desired thumbnail count...
                    if len(thumbnails) == 4:
                        break

        #If the thumnbail count is still zero...
        if len(thumbnails) == 0:
            self.__thumbnails = ['common/pl-default.png']
            return True

        #If the stored thumbnail data changed...
        if self.__thumbnails != thumbnails:
            self.__thumbnails = thumbnails
            return True

    def _load_name(self):
        if self.__name != self.__playlist.name():
            self.__name = self.__playlist.name()
            return True
        else:
            return False

    def _load_num_tracks(self):
        if self.__num_tracks != self.__playlist.num_tracks():
            self.__num_tracks = self.__playlist.num_tracks()
            return True
        else:
            return False

    def _load_is_collaborative(self):
        if self.__is_collaborative != self.__playlist.is_collaborative():
            self.__is_collaborative = self.__playlist.is_collaborative()
            return True
        else:
            return False

    def _load_attributes(self):
        #Now check for changes
        has_changes = False

        if self._load_name():
            has_changes = True

        if self._load_num_tracks():
            has_changes = True

        if self._load_is_collaborative():
            has_changes = True

        #If we detected something different
        return has_changes

    def _add_condition(self, condition):
        self.__conditions.add_condition(condition)

    def _wait_for_conditions(self, timeout):
        current_task().condition_wait(self.__conditions, timeout)

    def check(self):

        #If a loading process was not active, start a new one
        if self.__loader_lock.acquire(False):
            try:
                self.load_in_background()
            finally:
                self.__loader_lock.release()

        #Otherwise notify the task
        else:
            try:
                self.__loader_task.notify()
            except:
                pass

    def _set_loaded(self, status):
        self.__is_loaded = status

    def is_loaded(self):
        return self.__is_loaded

    def _set_error(self, status):
        self.__has_errors = status

    def has_errors(self):
        return self.__has_errors

    def _set_changes(self, status):
        self.__has_changes = status

    def has_changes(self):
        return self.__has_changes

    def _load(self):
        raise NotImplementedError()

    def end_loading(self):
        pass


class ContainerPlaylistLoader(BasePlaylistLoader):
    __container_loader = None

    def __init__(self, session, playlist, playlist_manager, container_loader):
        self.__container_loader = weakref.proxy(container_loader)
        BasePlaylistLoader.__init__(self, session, playlist, playlist_manager)

    def _load(self):
        #Wait for the underlying playlist object
        self._wait_for_playlist()

        if self._load_attributes():
            self._set_changes(True)

        if self._load_thumbnails():
            self._set_changes(True)

        #Mark the playlist as loaded
        self._set_loaded(True)

    def end_loading(self):
        self.__container_loader.check()


class FullPlaylistLoader(BasePlaylistLoader):
    def _check_track(self, track):
        def track_is_loaded():
            return self._track_is_ready(
                track, test_album=True, test_artists=True
            )

        #Add a check condition for this track if it needs one
        if not track_is_loaded():
            self._add_condition(track_is_loaded)

    def _load_all_tracks(self):
        #Iterate over the tracks to add conditions for them
        for item in self.get_tracks():
            self._check_track(item)

        #Wait until all tracks meet the conditions
        self._wait_for_conditions(20)

    def _load(self):
        #Wait for the underlying playlist object
        self._wait_for_playlist()

        #Load all the tracks
        self._load_all_tracks()

        if self._load_attributes():
            self._set_changes(True)

        if self._load_thumbnails():
            self._set_changes(True)

        #Mark the playlist as loaded
        self._set_loaded(True)

    def end_loading(self):
        xbmc.executebuiltin("Action(Noop)")


class SpecialPlaylistLoader(BasePlaylistLoader):
    def __init__(self, session, playlist, playlist_manager, name, thumbnails):
        BasePlaylistLoader.__init__(self, session, playlist, playlist_manager)
        self._set_name(name)
        self._set_thumbnails(thumbnails)

    def _load(self):
        #Wait for the underlying playlist object
        self._wait_for_playlist()

        if self._load_num_tracks():
            self._set_changes(True)

        #Mark the playlist as loaded
        self._set_loaded(True)

    def end_loading(self):
        xbmc.executebuiltin("Action(Noop)")

    def get_tracks(self):
        playlist = self.get_playlist()

        def sort_func(track_index):
            track = playlist.track(track_index)
            if track.is_loaded():
                return -playlist.track_create_time(track_index)

        track_indexes = range(playlist.num_tracks() - 1)
        sorted_indexes = sorted(track_indexes, key=sort_func)

        return [playlist.track(index) for index in sorted_indexes]


class ContainerCallbacks(playlistcontainer.PlaylistContainerCallbacks):
    __loader = None

    def __init__(self, loader):
        self.__loader = weakref.proxy(loader)

    def playlist_added(self, container, playlist, position):
        self.__loader.add_playlist(playlist, position)
        self.__loader.check()

    def container_loaded(self, container):
        self.__loader.check()

    def playlist_removed(self, container, playlist, position):
        self.__loader.remove_playlist(position)
        self.__loader.check()

    def playlist_moved(self, container, playlist, position, new_position):
        self.__loader.move_playlist(position, new_position)
        self.__loader.check()


class ContainerLoader:
    __session = None
    __container = None
    __playlist_manager = None
    __playlists = None
    __checker = None
    __loader_task = None
    __loader_lock = None
    __list_lock = None
    __is_loaded = None

    def __init__(self, session, container, playlist_manager):
        self.__session = session
        self.__container = container
        self.__playlist_manager = playlist_manager
        self.__playlists = []
        self.__conditions = ConditionList()
        self.__loader_lock = threading.RLock()
        self.__list_lock = threading.RLock()
        self.__is_loaded = False

        #Register the callbacks
        self.__container.add_callbacks(ContainerCallbacks(self))

        #Load the rest in the background
        self.load_in_background()

    def _fill_spaces(self, position):
        try:
            self.__list_lock.acquire()

            if position >= len(self.__playlists):
                for idx in range(len(self.__playlists), position + 1):
                    self.__playlists.append(None)

        finally:
            self.__list_lock.release()

    def is_playlist(self, position):
        playlist_type = self.__container.playlist_type(position)
        return playlist_type == playlist.PlaylistType.Playlist

    def add_playlist(self, playlist, position):
        try:
            self.__list_lock.acquire()

            #Ensure that it gets added in the correct position
            self._fill_spaces(position - 1)

            #Instantiate a loader if it's a real playlist
            if self.is_playlist(position):
                item = ContainerPlaylistLoader(
                    self.__session, playlist, self.__playlist_manager, self
                )

            #Ignore if it's not a real playlist
            else:
                item = None

            #Insert the generated item
            self.__playlists.insert(position, item)

        finally:
            self.__list_lock.release()

    def remove_playlist(self, position):
        try:
            self.__list_lock.acquire()
            del self.__playlists[position]

        finally:
            self.__list_lock.release()

    def move_playlist(self, position, new_position):
        try:
            self.__list_lock.acquire()
            self.__playlists.insert(new_position, self.__playlists[position])

            #Calculate new position
            if position > new_position:
                position += 1

            del self.__playlists[position]

        finally:
            self.__list_lock.release()

    def _add_missing_playlists(self):

        #Ensure that the container and loader length is the same
        self._fill_spaces(self.__container.num_playlists() - 1)

        #Iterate over the container to add the missing ones
        for pos, item in enumerate(self.__container.playlists()):

            #Check if we should continue
            current_task().check_status()

            if self.is_playlist(pos) and self.__playlists[pos] is None:
                self.add_playlist(item, pos)

    def _check_playlist(self, playlist):
        def is_playlist_loaded():
            #If it has errors, say yes.
            if playlist.has_errors():
                return True

            #And if it was loaded, say yes
            if playlist.is_loaded():
                return True

        self.__conditions.add_condition(is_playlist_loaded)

    def _load_container(self):

        #Wait for the container to be fully loaded
        self.__conditions.add_condition(self.__container.is_loaded)
        current_task().condition_wait(self.__conditions)

        #Fill the container with unseen playlists
        self._add_missing_playlists()

        #Add a load check for each playlist
        for item in self.__playlists:
            if item is not None and not item.is_loaded():
                self._check_playlist(item)

        #Wait until all conditions become true
        current_task().condition_wait(
            self.__conditions, self.__container.num_playlists() * 5
        )

        #Set the status of the loader
        self.__is_loaded = True

        #Check and log errors for not loaded playlists
        for idx, item in enumerate(self.__playlists):
            if item is not None and item.has_errors():
                get_logger().error('Playlist #%s failed loading.' % idx)

        #Finally tell the gui we are done
        xbmc.executebuiltin("Action(Noop)")

    @run_in_thread(group='load_playlists', max_concurrency=10)
    def load_in_background(self):

        #Avoid entering here multiple times
        if self.__loader_lock.acquire(False):
            try:

                #Set the current task object
                self.__loader_task = current_task()

                #And take care of the rest
                self._load_container()

            finally:

                #Release and clear everything
                self.__loader_task = None
                self.__loader_lock.release()

    def check(self):

        #If a loading process was not active, start a new one
        if self.__loader_lock.acquire(False):
            try:
                self.load_in_background()
            finally:
                self.__loader_lock.release()

        #Otherwise notify the task
        else:
            try:
                self.__loader_task.notify()
            except:
                pass

    def is_loaded(self):
        return self.__is_loaded

    def playlist(self, index):
        return self.__playlists[index]

    def num_playlists(self):
        return len(self.__playlists)

    def playlists(self):
        return CallbackIterator(self.num_playlists, self.playlist)

    def get_container(self):
        return self.__container

########NEW FILE########
__FILENAME__ = search
'''
Copyright 2011 Mikel Azkolain

This file is part of Spotimc.

Spotimc is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

Spotimc is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with Spotimc.  If not, see <http://www.gnu.org/licenses/>.
'''


import xbmc
from spotimcgui.views import BaseListContainerView
from spotify import search, track
from spotimcgui.views.artists import open_artistbrowse_albums
from spotimcgui.views.album import AlbumTracksView


def ask_search_term():
    kb = xbmc.Keyboard('', 'Enter a search term')
    kb.doModal()

    if kb.isConfirmed():
        return kb.getText()


class SearchTracksCallbacks(search.SearchCallbacks):
    def search_complete(self, result):
        xbmc.executebuiltin("Action(Noop)")


class SearchTracksView(BaseListContainerView):
    container_id = 1500
    list_id = 1520

    button_did_you_mean = 1504
    button_new_search = 1510

    context_menu_id = 5500
    context_browse_artist_button = 5502
    context_browse_album_button = 5503
    context_toggle_star = 5504
    context_add_to_playlist = 5505

    __session = None
    __query = None
    __search = None

    def _do_search(self, query):
        self.__query = query
        cb = SearchTracksCallbacks()
        self.__search = search.Search(
            self.__session, query,
            track_offset=0, track_count=200,
            callbacks=cb
        )

    def __init__(self, session, query):
        self.__session = session
        self._do_search(query)

    def _get_current_track(self, view_manager):
        item = self.get_list(view_manager).getSelectedItem()
        pos = int(item.getProperty('ListIndex'))

        if pos is not None:
            return self.__search.track(pos)

    def _play_selected_track(self, view_manager):
        item = self.get_list(view_manager).getSelectedItem()
        pos = int(item.getProperty('ListIndex'))
        session = view_manager.get_var('session')
        playlist_manager = view_manager.get_var('playlist_manager')
        playlist_manager.play(self.__search.tracks(), session, pos)

    def click(self, view_manager, control_id):
        if control_id == SearchTracksView.button_did_you_mean:
            if self.__search.did_you_mean():
                self._do_search(self.__search.did_you_mean())
                view_manager.show()

        elif control_id == SearchTracksView.button_new_search:
            term = ask_search_term()
            if term:
                self._do_search(term)
                view_manager.show()

        elif control_id == SearchTracksView.list_id:
            self._play_selected_track(view_manager)

        elif control_id == SearchTracksView.context_browse_artist_button:
            current_track = self._get_current_track(view_manager)
            artist_list = [artist for artist in current_track.artists()]
            open_artistbrowse_albums(view_manager, artist_list)

        elif control_id == SearchTracksView.context_browse_album_button:
            album = self._get_current_track(view_manager).album()
            session = view_manager.get_var('session')
            v = AlbumTracksView(session, album)
            view_manager.add_view(v)

        elif control_id == SearchTracksView.context_toggle_star:
            item = self.get_list(view_manager).getSelectedItem()
            current_track = self._get_current_track(view_manager)

            if current_track is not None:
                if item.getProperty('IsStarred') == 'true':
                    item.setProperty('IsStarred', 'false')
                    track.set_starred(self.__session, [current_track], False)
                else:
                    item.setProperty('IsStarred', 'true')
                    track.set_starred(self.__session, [current_track], True)

    def action(self, view_manager, action_id):
        #Run parent implementation's actions
        BaseListContainerView.action(self, view_manager, action_id)

        playlist_manager = view_manager.get_var('playlist_manager')

        #Do nothing if playing, as it may result counterproductive
        if not playlist_manager.is_playing():
            if action_id == 79:
                self._play_selected_track(view_manager)

    def get_container(self, view_manager):
        return view_manager.get_window().getControl(SearchTracksView.container_id)

    def get_list(self, view_manager):
        return view_manager.get_window().getControl(SearchTracksView.list_id)

    def get_context_menu_id(self):
        return SearchTracksView.context_menu_id

    def _set_search_info(self, view_manager):
        window = view_manager.get_window()
        window.setProperty("SearchQuery", self.__query)

        did_you_mean = self.__search.did_you_mean()
        if did_you_mean:
            window.setProperty("SearchDidYouMeanStatus", "true")
            window.setProperty("SearchDidYouMeanString", did_you_mean)
        else:
            window.setProperty("SearchDidYouMeanStatus", "false")

    def render(self, view_manager):
        if self.__search.is_loaded():
            session = view_manager.get_var('session')
            pm = view_manager.get_var('playlist_manager')

            #Some view vars
            self._set_search_info(view_manager)

            #Reset list
            list_obj = self.get_list(view_manager)
            list_obj.reset()

            #Iterate over the tracks
            for list_index, track in enumerate(self.__search.tracks()):
                url, info = pm.create_track_info(track, session, list_index)
                list_obj.addItem(info)

            #Tell that the list is ready to render
            return True

########NEW FILE########
__FILENAME__ = windows
'''
Copyright 2011 Mikel Azkolain

This file is part of Spotimc.

Spotimc is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

Spotimc is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with Spotimc.  If not, see <http://www.gnu.org/licenses/>.
'''


import xbmc
import xbmcgui
import views
import views.newstuff
import views.album
import views.search
import views.nowplaying
import views.playlists.list
import views.playlists.detail
import views.more
import weakref

from settings import SettingsManager, StartupScreen
from utils import environment


class MainWindow(xbmcgui.WindowXML):
    __view_manager = None
    __session = None
    __playlist_manager = None
    __application = None
    __active_tab = None

    #Button id constants
    now_playing_button = 201
    new_stuff_button = 212
    playlists_button = 213
    search_button = 214
    more_button = 215
    exit_button = 216

    #Loading gif id
    loading_image = 50

    def __init__(self, file, script_path, skin_dir):
        self.__view_manager = views.ViewManager(self)

    def initialize(self, session, proxy_runner, playlist_manager, application):
        self.__session = session
        self.__playlist_manager = playlist_manager
        self.__application = application

        #Shared vars with views
        self.__view_manager.set_var('playlist_manager',
                                    weakref.proxy(self.__playlist_manager))
        self.__view_manager.set_var('session', weakref.proxy(session))
        self.__view_manager.set_var('proxy_runner',
                                    weakref.proxy(proxy_runner))

    def show_loading(self):
        c = self.getControl(MainWindow.loading_image)
        c.setVisibleCondition("True")

    def hide_loading(self):
        c = self.getControl(MainWindow.loading_image)
        c.setVisibleCondition("False")

    def _set_active_tab(self, tab=None):

        #Update the variable and the infolabel
        if tab is not None:
            self.__active_tab = tab
            self.setProperty('MainActiveTab', tab)

        #Otherwise update again the current tab
        elif self.__active_tab is not None:
            self.setProperty('MainActiveTab', self.__active_tab)

    def _init_new_stuff(self):
        self._set_active_tab('newstuff')
        v = views.newstuff.NewStuffView(self.__session)
        self.__view_manager.add_view(v)

    def _init_playlists(self):
        self._set_active_tab('playlists')
        c = self.__session.playlistcontainer()
        pm = self.__playlist_manager
        v = views.playlists.list.PlaylistView(self.__session, c, pm)
        self.__view_manager.add_view(v)

    def onInit(self):
        # Check if we already added views because after
        # exiting music vis this gets called again.
        if self.__view_manager.num_views() == 0:
            #Get the startup view from the settings
            startup_screen = SettingsManager().get_misc_startup_screen()
            if startup_screen == StartupScreen.Playlists:
                self._init_playlists()

            #Always display new stuff as a fallback
            else:
                self._init_new_stuff()

        #Otherwise show the current view
        else:
            self._set_active_tab()
            self.__view_manager.show()

        #Store current window id
        manager = self.__application.get_var('info_value_manager')
        manager.set_infolabel('spotimc_window_id',
                              xbmcgui.getCurrentWindowId())

    def onAction(self, action):
        # TODO: Remove magic values
        if action.getId() in [9, 10, 92]:
            if self.__view_manager.position() > 0:
                self.__view_manager.previous()
            elif environment.has_background_support():
                #Flush caches before minimizing
                self.__session.flush_caches()
                xbmc.executebuiltin("XBMC.ActivateWindow(0)")

        #Noop action
        # TODO: Remove magic values
        elif action.getId() in [0, 999]:
            self.__view_manager.show()

        else:
            self.__view_manager.action(action.getId())

    def _process_layout_click(self, control_id):
        if control_id == MainWindow.now_playing_button:
            self._set_active_tab('nowplaying')
            v = views.nowplaying.NowPlayingView()
            self.__view_manager.clear_views()
            self.__view_manager.add_view(v)

        elif control_id == MainWindow.playlists_button:
            self.__view_manager.clear_views()
            self._init_playlists()

        elif control_id == MainWindow.new_stuff_button:
            self.__view_manager.clear_views()
            self._init_new_stuff()

        elif control_id == MainWindow.search_button:
            term = views.search.ask_search_term()
            if term:
                self._set_active_tab('search')
                v = views.search.SearchTracksView(self.__session, term)
                self.__view_manager.clear_views()
                self.__view_manager.add_view(v)

        elif control_id == MainWindow.more_button:
            self._set_active_tab('more')
            v = views.more.MoreView()
            self.__view_manager.clear_views()
            self.__view_manager.add_view(v)

        elif control_id == MainWindow.exit_button:
            self.__application.set_var('exit_requested', True)
            self.close()

    def onClick(self, control_id):
        #IDs lower than 1000 belong to the common layout
        if control_id < 1000:
            self._process_layout_click(control_id)

        #Hand the rest to the view manager
        else:
            self.__view_manager.click(control_id)

    def onFocus(self, controlID):
        pass

########NEW FILE########
__FILENAME__ = spotimc
'''
Copyright 2011 Mikel Azkolain

This file is part of Spotimc.

Spotimc is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

Spotimc is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with Spotimc.  If not, see <http://www.gnu.org/licenses/>.
'''


import os.path
import xbmcaddon
import sys


#Set global addon information first
__addon_id__ = 'script.audio.spotimc'
addon_cfg = xbmcaddon.Addon(__addon_id__)
__addon_path__ = addon_cfg.getAddonInfo('path')
__addon_version__ = addon_cfg.getAddonInfo('version')

#Make spotimcgui available
sys.path.insert(0, os.path.join(__addon_path__, "resources/libs"))

#Prepare the environment...
from spotimcgui.utils.environment import set_library_paths
set_library_paths()

from spotimcgui.main import main
main()

########NEW FILE########
