__FILENAME__ = gpodder_mark_played
#!/usr/bin/python
# Example script that can be used as post-play extension in media players
#
# Set the configuration options "audio_played_dbus" and "video_played_dbus"
# to True to let gPodder leave the played status untouched when playing
# files in the media player. After playback has finished, call this script
# with the filename of the played episodes as single argument. The episode
# will be marked as played inside gPodder.
#
# Usage: gpodder_mark_played.py /path/to/episode.mp3
#        (the gPodder GUI has to be running)
#
# Thomas Perl <thp@gpodder.org>; 2009-09-09

import sys
import os

if len(sys.argv) != 2:
    print >>sys.stderr, """
    Usage: %s /path/to/episode.mp3
    """ % (sys.argv[0],)
    sys.exit(1)

filename = os.path.abspath(sys.argv[1])

import dbus
import gpodder

session_bus = dbus.SessionBus()
proxy = session_bus.get_object(gpodder.dbus_bus_name, \
                               gpodder.dbus_gui_object_path)
interface = dbus.Interface(proxy, gpodder.dbus_interface)

if not interface.mark_episode_played(filename):
    print >>sys.stderr, 'Warning: Could not mark episode as played.'
    sys.exit(2)


########NEW FILE########
__FILENAME__ = hello_world

# Use a logger for debug output - this will be managed by gPodder
import logging
logger = logging.getLogger(__name__)

# Provide some metadata that will be displayed in the gPodder GUI
__title__ = 'Hello World Extension'
__description__ = 'Explain in one sentence what this extension does.'
__only_for__ = 'gtk, cli, qml'
__authors__ = 'Thomas Perl <m@thp.io>'

class gPodderExtension:
    # The extension will be instantiated the first time it's used
    # You can do some sanity checks here and raise an Exception if
    # you want to prevent the extension from being loaded..
    def __init__(self, container):
        self.container = container

    # This function will be called when the extension is enabled or
    # loaded. This is when you want to create helper objects or hook
    # into various parts of gPodder.
    def on_load(self):
        logger.info('Extension is being loaded.')
        print '='*40
        print 'container:', self.container
        print 'container.manager:', self.container.manager
        print 'container.config:', self.container.config
        print 'container.manager.core:', self.container.manager.core
        print 'container.manager.core.db:', self.container.manager.core.db
        print 'container.manager.core.config:', self.container.manager.core.config
        print 'container.manager.core.model:', self.container.manager.core.model
        print '='*40

    # This function will be called when the extension is disabled or
    # when gPodder shuts down. You can use this to destroy/delete any
    # objects that you created in on_load().
    def on_unload(self):
        logger.info('Extension is being unloaded.')


########NEW FILE########
__FILENAME__ = audio_converter
# -*- coding: utf-8 -*-
# Convertes m4a audio files to mp3
# This requires ffmpeg to be installed. Also works as a context
# menu item for already-downloaded files.
#
# (c) 2011-11-23 Bernd Schlapsi <brot@gmx.info>
# Released under the same license terms as gPodder itself.

import os
import subprocess

import gpodder
from gpodder import util

import logging
logger = logging.getLogger(__name__)

_ = gpodder.gettext

__title__ = _('Convert audio files')
__description__ = _('Transcode audio files to mp3/ogg')
__authors__ = 'Bernd Schlapsi <brot@gmx.info>, Thomas Perl <thp@gpodder.org>'
__doc__ = 'http://wiki.gpodder.org/wiki/Extensions/AudioConverter'
__payment__ = 'https://flattr.com/submit/auto?user_id=BerndSch&url=http://wiki.gpodder.org/wiki/Extensions/AudioConverter'
__category__ = 'post-download'


DefaultConfig = {
    'use_ogg': False, # Set to True to convert to .ogg (otherwise .mp3)
    'context_menu': True, # Show the conversion option in the context menu
}

class gPodderExtension:
    MIME_TYPES = ('audio/x-m4a', 'audio/mp4', 'audio/mp4a-latm', 'audio/ogg', )
    EXT = ('.m4a', '.ogg')
    CMD = {'avconv': {'.mp3': ['-i', '%(old_file)s', '-q:a', '2', '-id3v2_version', '3', '-write_id3v1', '1', '%(new_file)s'],
                      '.ogg': ['-i', '%(old_file)s', '-q:a', '2', '%(new_file)s']
                     },
           'ffmpeg': {'.mp3': ['-i', '%(old_file)s', '-q:a', '2', '-id3v2_version', '3', '-write_id3v1', '1', '%(new_file)s'],
                      '.ogg': ['-i', '%(old_file)s', '-q:a', '2', '%(new_file)s']
                     }
          }

    def __init__(self, container):
        self.container = container
        self.config = self.container.config

        # Dependency checks
        self.command = self.container.require_any_command(['avconv', 'ffmpeg'])

        # extract command without extension (.exe on Windows) from command-string
        self.command_without_ext = os.path.basename(os.path.splitext(self.command)[0])

    def on_episode_downloaded(self, episode):
        self._convert_episode(episode)
        
    def _get_new_extension(self):
        return ('.ogg' if self.config.use_ogg else '.mp3')

    def _check_source(self, episode):
        if episode.extension() == self._get_new_extension():
            return False
            
        if episode.mime_type in self.MIME_TYPES:
            return True

        # Also check file extension (bug 1770)
        if episode.extension() in self.EXT:
            return True

        return False

    def on_episodes_context_menu(self, episodes):
        if not self.config.context_menu:
            return None

        if not all(e.was_downloaded(and_exists=True) for e in episodes):
            return None

        if not any(self._check_source(episode) for episode in episodes):
            return None

        target_format = ('OGG' if self.config.use_ogg else 'MP3')
        menu_item = _('Convert to %(format)s') % {'format': target_format}

        return [(menu_item, self._convert_episodes)]

    def _convert_episode(self, episode):
        if not self._check_source(episode):
            return

        new_extension = self._get_new_extension()
        old_filename = episode.local_filename(create=False)
        filename, old_extension = os.path.splitext(old_filename)
        new_filename = filename + new_extension

        cmd_param = self.CMD[self.command_without_ext][new_extension]
        cmd = [self.command] + \
            [param % {'old_file': old_filename, 'new_file': new_filename}
                for param in cmd_param]

        ffmpeg = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                stderr=subprocess.PIPE)
        stdout, stderr = ffmpeg.communicate()

        if ffmpeg.returncode == 0:
            util.rename_episode_file(episode, new_filename)
            os.remove(old_filename)
            
            logger.info('Converted audio file to %(format)s.' % {'format': new_extension})
            gpodder.user_extensions.on_notification_show(_('File converted'), episode.title)
        else:
            logger.warn('Error converting audio file: %s / %s', stdout, stderr)
            gpodder.user_extensions.on_notification_show(_('Conversion failed'), episode.title)

    def _convert_episodes(self, episodes):
        for episode in episodes:
            self._convert_episode(episode)

########NEW FILE########
__FILENAME__ = concatenate_videos
# -*- coding: utf-8 -*-
# Concatenate multiple videos to a single file using ffmpeg
# 2014-05-03 Thomas Perl <thp.io/about>
# Released under the same license terms as gPodder itself.

import subprocess

import gpodder
from gpodder import util

import gtk
from gpodder.gtkui.interface.progress import ProgressIndicator
import os

import logging
logger = logging.getLogger(__name__)

_ = gpodder.gettext

__title__ = _('Concatenate videos')
__description__ = _('Add a context menu item for concatenating multiple videos')
__authors__ = 'Thomas Perl <thp@gpodder.org>'
__category__ = 'interface'
__only_for__ = 'gtk'

class gPodderExtension:
    def __init__(self, container):
        self.container = container
        self.gpodder = None
        self.have_ffmpeg = (util.find_command('ffmpeg') is not None)

    def on_ui_object_available(self, name, ui_object):
        if name == 'gpodder-gtk':
            self.gpodder = ui_object

    def _get_save_filename(self):
        dlg = gtk.FileChooserDialog(title=_('Save video'),
                parent=self.gpodder.get_dialog_parent(),
                action=gtk.FILE_CHOOSER_ACTION_SAVE)
        dlg.add_button(gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL)
        dlg.add_button(gtk.STOCK_SAVE, gtk.RESPONSE_OK)

        if dlg.run() == gtk.RESPONSE_OK:
            filename = dlg.get_filename()
            dlg.destroy()
            return filename

        dlg.destroy()

    def _concatenate_videos(self, episodes):
        episodes = self._get_sorted_episode_list(episodes)

        # TODO: Show file list dialog for reordering

        out_filename = self._get_save_filename()
        if out_filename is None:
            return

        list_filename = os.path.join(os.path.dirname(out_filename),
                '.' + os.path.splitext(os.path.basename(out_filename))[0] + '.txt')

        with open(list_filename, 'w') as fp:
            fp.write('\n'.join("file '%s'\n" % episode.local_filename(create=False)
                for episode in episodes))

        indicator = ProgressIndicator(_('Concatenating video files'),
                _('Writing %(filename)s') % {
                    'filename': os.path.basename(out_filename)
                }, False, self.gpodder.get_dialog_parent())

        def convert():
            ffmpeg = subprocess.Popen(['ffmpeg', '-f', 'concat', '-nostdin', '-y',
                '-i', list_filename, '-c', 'copy', out_filename])
            result = ffmpeg.wait()
            util.delete_file(list_filename)
            util.idle_add(lambda: indicator.on_finished())
            util.idle_add(lambda: self.gpodder.show_message(
                _('Videos successfully converted') if result == 0 else
                _('Error converting videos'),
                _('Concatenation result'), important=True))

        util.run_in_background(convert, True)

    def _is_downloaded_video(self, episode):
        return episode.file_exists() and episode.file_type() == 'video'

    def _get_sorted_episode_list(self, episodes):
        return sorted([e for e in episodes if self._is_downloaded_video(e)],
                key=lambda e: e.published)

    def on_episodes_context_menu(self, episodes):
        if self.gpodder is None or not self.have_ffmpeg:
            return None

        episodes = self._get_sorted_episode_list(episodes)

        if len(episodes) < 2:
            return None

        return [(_('Concatenate videos'), self._concatenate_videos)]


########NEW FILE########
__FILENAME__ = enqueue_in_mediaplayer
# -*- coding: utf-8 -*-
# Extension script to add a context menu item for enqueueing episodes in a player
# Requirements: gPodder 3.x (or "tres" branch newer than 2011-06-08)
# (c) 2011-06-08 Thomas Perl <thp.io/about>
# Released under the same license terms as gPodder itself.
import subprocess

import gpodder
from gpodder import util

import logging
logger = logging.getLogger(__name__)

_ = gpodder.gettext

__title__ = _('Enqueue in media players')
__description__ = _('Add a context menu item for enqueueing episodes in installed media players')
__authors__ = 'Thomas Perl <thp@gpodder.org>, Bernd Schlapsi <brot@gmx.info>'
__doc__ = 'http://wiki.gpodder.org/wiki/Extensions/EnqueueInMediaplayer'
__payment__ = 'https://flattr.com/submit/auto?user_id=BerndSch&url=http://wiki.gpodder.org/wiki/Extensions/EnqueueInMediaplayer'
__category__ = 'interface'
__only_for__ = 'gtk'

class Player:
    def __init__(self, application, command):
        self.title = '/'.join((_('Enqueue in'), application))
        self.command = command
        self.gpodder = None

    def is_installed(self):
        return util.find_command(self.command[0]) is not None

    def enqueue_episodes(self, episodes):
        filenames = [episode.get_playback_url() for episode in episodes]

        subprocess.Popen(self.command + filenames,
                stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        for episode in episodes:
            episode.playback_mark()
            self.gpodder.update_episode_list_icons(selected=True)


PLAYERS = [
    # Amarok, http://amarok.kde.org/
    Player('Amarok', ['amarok', '--play', '--append']),

    # VLC, http://videolan.org/
    Player('VLC', ['vlc', '--started-from-file', '--playlist-enqueue']),

    # Totem, https://live.gnome.org/Totem
    Player('Totem', ['totem', '--enqueue']),

    # DeaDBeeF, http://deadbeef.sourceforge.net/
    Player('DeaDBeeF', ['deadbeef', '--queue']),

    # gmusicbrowser, http://gmusicbrowser.org/
    Player('gmusicbrowser', ['gmusicbrowser', '-enqueue']),

    # Audacious, http://audacious-media-player.org/
    Player('Audacious', ['audacious', '--enqueue']),

    # Clementine, http://www.clementine-player.org/
    Player('Clementine', ['clementine', '--append']),
]

class gPodderExtension:
    def __init__(self, container):
        self.container = container

        # Only display media players that can be found at extension load time
        self.players = filter(lambda player: player.is_installed(), PLAYERS)

    def on_ui_object_available(self, name, ui_object):
        if name == 'gpodder-gtk':
            for p in self.players:
                p.gpodder = ui_object

    def on_episodes_context_menu(self, episodes):
        if not any(e.file_exists() for e in episodes):
            return None

        return [(p.title, p.enqueue_episodes) for p in self.players]


########NEW FILE########
__FILENAME__ = gtk_statusicon
# -*- coding: utf-8 -*-
#
# Gtk Status Icon (gPodder bug 1495)
# Thomas Perl <thp@gpodder.org>; 2012-07-31
#

import gpodder

import logging
logger = logging.getLogger(__name__)

_ = gpodder.gettext

__title__ = _('Gtk Status Icon')
__description__ = _('Show a status icon for Gtk-based Desktops.')
__category__ = 'desktop-integration'
__only_for__ = 'gtk'
__disable_in__ = 'unity,win32'

import gtk
import os.path

from gpodder.gtkui import draw

DefaultConfig = {
    'download_progress_bar': False, # draw progress bar on icon while downloading?
}

class gPodderExtension:
    def __init__(self, container):
        self.container = container
        self.config = self.container.config
        self.status_icon = None
        self.icon_name = None
        self.gpodder = None
        self.last_progress = 1

    def set_icon(self, use_pixbuf=False):
        path = os.path.join(os.path.dirname(__file__), '..', '..', 'icons')
        icon_path = os.path.abspath(path)

        theme = gtk.icon_theme_get_default()
        theme.append_search_path(icon_path)

        if self.icon_name is None:
            if theme.has_icon('gpodder'):
                self.icon_name = 'gpodder'
            else:
                self.icon_name = 'stock_mic'

        if self.status_icon is None:
            self.status_icon = gtk.status_icon_new_from_icon_name(self.icon_name)
            return

        # If current mode matches desired mode, nothing to do.
        is_pixbuf = (self.status_icon.get_storage_type() == gtk.IMAGE_PIXBUF)
        if is_pixbuf == use_pixbuf:
            return

        if not use_pixbuf:
            self.status_icon.set_from_icon_name(self.icon_name)
        else:
            # Currently icon is not a pixbuf => was loaded by name, at which
            # point size was automatically determined.
            icon_size = self.status_icon.get_size()
            icon_pixbuf = theme.load_icon(self.icon_name, icon_size, gtk.ICON_LOOKUP_USE_BUILTIN)
            self.status_icon.set_from_pixbuf(icon_pixbuf)

    def on_load(self):
        self.set_icon()
        self.status_icon.connect('activate', self.on_toggle_visible)
        self.status_icon.set_has_tooltip(True)
        self.status_icon.set_tooltip_text("gPodder")

    def on_toggle_visible(self, status_icon):
        if self.gpodder is None:
            return

        visibility = self.gpodder.main_window.get_visible()
        self.gpodder.main_window.set_visible(not visibility)

    def on_unload(self):
        if self.status_icon is not None:
            self.status_icon.set_visible(False)
            self.status_icon = None
            self.icon_name = None

    def on_ui_object_available(self, name, ui_object):
        if name == 'gpodder-gtk':
            self.gpodder = ui_object

    def get_icon_pixbuf(self):
        assert self.status_icon is not None
        if self.status_icon.get_storage_type() != gtk.IMAGE_PIXBUF:
            self.set_icon(use_pixbuf=True)
        return self.status_icon.get_pixbuf()

    def on_download_progress(self, progress):
        logger.debug("download progress: %f", progress)

        if not self.config.download_progress_bar:
            # reset the icon in case option was turned off during download
            if self.last_progress < 1:
                self.last_progress = 1
                self.set_icon()
            # in any case, we're now done
            return

        if progress == 1:
            self.set_icon() # no progress bar
            self.last_progress = progress
            return

        # Only update in 3-percent-steps to save some resources
        if abs(progress-self.last_progress) < 0.03 and progress > self.last_progress:
            return

        icon = self.get_icon_pixbuf().copy()
        progressbar = draw.progressbar_pixbuf(icon.get_width(), icon.get_height(), progress)
        progressbar.composite(icon, 0, 0, icon.get_width(), icon.get_height(), 0, 0, 1, 1, gtk.gdk.INTERP_NEAREST, 255)

        self.status_icon.set_from_pixbuf(icon)
        self.last_progress = progress


########NEW FILE########
__FILENAME__ = minimize_on_start
# -*- coding: utf-8 -*-

# Minimize gPodder's main window on startup
# Thomas Perl <thp@gpodder.org>; 2012-07-31

import gpodder

_ = gpodder.gettext

__title__ = _('Minimize on start')
__description__ = _('Minimizes the gPodder window on startup.')
__category__ = 'interface'
__only_for__ = 'gtk'

class gPodderExtension:
    def __init__(self, container):
        self.container = container

    def on_ui_object_available(self, name, ui_object):
        if name == 'gpodder-gtk':
            ui_object.main_window.iconify()


########NEW FILE########
__FILENAME__ = mpris-listener
# -*- coding: utf-8 -*-
#
# gPodder extension for listening to notifications from MPRIS-capable
# players and translating them to gPodder's Media Player D-Bus API
#
# Copyright (c) 2013-2014 Dov Feldstern <dovdevel@gmail.com>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

import collections
import dbus
import dbus.service
import gpodder
import logging
import time
import urllib
import urlparse

logger = logging.getLogger(__name__)
_ = gpodder.gettext

__title__ = _('MPRIS Listener')
__description__ = _('Convert MPRIS notifications to gPodder Media Player D-Bus API')
__authors__ = 'Dov Feldstern <dovdevel@gmail.com>'
__doc__ = 'http://wiki.gpodder.org/wiki/Extensions/MprisListener'
__category__ = 'desktop-integration'

USECS_IN_SEC = 1000000

TrackInfo = collections.namedtuple('TrackInfo',
                        ['uri', 'length', 'status', 'pos', 'rate'])

def subsecond_difference(usec1, usec2):
    return abs(usec1 - usec2) < USECS_IN_SEC
    
class CurrentTrackTracker(object):
    '''An instance of this class is responsible for tracking the state of the
    currently playing track -- it's playback status, playing position, etc.
    '''
    def __init__(self, notifier):
        self.uri = None
        self.length = None
        self.pos = None
        self.rate = None
        self.status = None
        self._notifier = notifier
        self._prev_notif = ()

    def _calc_update(self):

        now = time.time()

        logger.debug('CurrentTrackTracker: calculating at %d (status: %r)',
                     now, self.status)

        try:
            if self.status != 'Playing':
                logger.debug('CurrentTrackTracker: not currently playing, no change')
                return
            if self.pos is None or self.rate is None:
                logger.debug('CurrentTrackTracker: unknown pos/rate, no change')
                return
            logger.debug('CurrentTrackTracker: %f @%f (diff: %f)',
                         self.pos, self.rate, now - self._last_time)
            self.pos = self.pos + self.rate * (now - self._last_time) * USECS_IN_SEC
        finally:
            self._last_time = now
        
    def update_needed(self, current, updated):
        for field in updated:
            if field == 'pos':
                if not subsecond_difference(updated['pos'], current['pos']):
                    return True
            elif updated[field] != current[field]:
                return True
        # no unequal field was found, no new info here!
        return False

    def update(self, **kwargs):

        # check if there is any new info here -- if not, no need to update!

        cur = self.getinfo()._asdict()
        if not self.update_needed(cur, kwargs):
            return

        # there *is* new info, go ahead and update...

        uri = kwargs.pop('uri', None)
        if uri is not None:
            length = kwargs.pop('length') # don't know how to handle uri with no length
            if uri != cur['uri']:
                # if this is a new uri, and the previous state was 'Playing',
                # notify that the previous track has stopped before updating to
                # the new track.
                if cur['status'] == 'Playing':
                    logger.debug('notify Stopped: new uri: old %s new %s',
                                 cur['uri'], uri)
                    self.notify_stop()
            self.uri = uri
            self.length = float(length)

        if 'pos' in kwargs:
            # If the position is being updated, and the current status was Playing
            # If the status *is* playing, and *was* playing, but the position
            # has changed discontinuously, notify a stop for the old position
            if (    cur['status'] == 'Playing'
                and (not kwargs.has_key('status') or kwargs['status'] == 'Playing')
                and not subsecond_difference(cur['pos'], kwargs['pos'])
            ):
                logger.debug('notify Stopped: playback discontinuity:' + 
                              'calc: %f observed: %f', cur['pos'], kwargs['pos'])
                self.notify_stop()

            if (    (kwargs['pos']) == 0
                and self.pos > (self.length - USECS_IN_SEC)
                and self.pos < (self.length + 2 * USECS_IN_SEC)
            ):
                logger.debug('fixing for position 0 (calculated pos: %f/%f [%f])',
                             self.pos / USECS_IN_SEC, self.length / USECS_IN_SEC,
                             (self.pos/USECS_IN_SEC)-(self.length/USECS_IN_SEC))
                self.pos = self.length
                kwargs.pop('pos') # remove 'pos' even though we're not using it
            else:
                if self.pos is not None:
                    logger.debug("%r %r", self.pos, self.length)
                    logger.debug('not fixing for position 0 (calculated pos: %f/%f [%f])',
                                 self.pos / USECS_IN_SEC, self.length / USECS_IN_SEC,
                                 (self.pos/USECS_IN_SEC)-(self.length/USECS_IN_SEC))
                self.pos = kwargs.pop('pos')

        if 'status' in kwargs:
            self.status = kwargs.pop('status')

        if 'rate' in kwargs:
            self.rate = kwargs.pop('rate')

        if kwargs:
            logger.error('unexpected update fields %r', kwargs)

        # notify about the current state
        if self.status == 'Playing':
            self.notify_playing()
        else:
            logger.debug('notify Stopped: status %s', self.status)
            self.notify_stop()

    def getinfo(self):
        self._calc_update()
        return TrackInfo(self.uri, self.length, self.status, self.pos, self.rate)

    def notify_stop(self):
        self.notify('Stopped')

    def notify_playing(self):
        self.notify('Playing')

    def notify(self, status):
        if (   self.uri is None
            or self.pos is None
            or self.status is None
            or self.length is None
            or self.length <= 0
        ):
            return
        pos = self.pos // USECS_IN_SEC
        file_uri = urllib.url2pathname(urlparse.urlparse(self.uri).path).encode('utf-8')
        total_time = self.length // USECS_IN_SEC
        
        if status == 'Stopped':
            end_position = pos
            start_position = self._notifier.start_position
            if self._prev_notif != (start_position, end_position, total_time, file_uri):
                self._notifier.PlaybackStopped(start_position, end_position,
                                               total_time, file_uri)
                self._prev_notif = (start_position, end_position, total_time, file_uri)

        elif status == 'Playing':
            start_position = pos
            if self._prev_notif != (start_position, file_uri):
                self._notifier.PlaybackStarted(start_position, file_uri)
                self._prev_notif = (start_position, file_uri)
            self._notifier.start_position = start_position

        logger.info('CurrentTrackTracker: %s: %r', status, self)

    def __repr__(self):
        return '%s: %s at %d/%d (@%f)' % (
            self.uri or 'None',
            self.status or 'None',
            (self.pos or 0) / USECS_IN_SEC,
            (self.length or 0) / USECS_IN_SEC,
            self.rate or 0)
            
class MPRISDBusReceiver(object):
    INTERFACE_PROPS = 'org.freedesktop.DBus.Properties'
    SIGNAL_PROP_CHANGE = 'PropertiesChanged'
    PATH_MPRIS = '/org/mpris/MediaPlayer2'
    INTERFACE_MPRIS = 'org.mpris.MediaPlayer2.Player'
    SIGNAL_SEEKED = 'Seeked'
    OBJECT_VLC = 'org.mpris.MediaPlayer2.vlc'

    def __init__(self, bus, notifier):
        self.bus = bus
        self.cur = CurrentTrackTracker(notifier)
        self.bus.add_signal_receiver(self.on_prop_change,
                                     self.SIGNAL_PROP_CHANGE,
                                     self.INTERFACE_PROPS,
                                     None,
                                     self.PATH_MPRIS)
        self.bus.add_signal_receiver(self.on_seeked,
                                     self.SIGNAL_SEEKED,
                                     self.INTERFACE_MPRIS,
                                     None,
                                     None)

    def stop_receiving(self):
        self.bus.remove_signal_receiver(self.on_prop_change,
                                        self.SIGNAL_PROP_CHANGE,
                                        self.INTERFACE_PROPS,
                                        None,
                                        self.PATH_MPRIS)
        self.bus.remove_signal_receiver(self.on_seeked,
                                        self.SIGNAL_SEEKED,
                                        self.INTERFACE_MPRIS,
                                        None,
                                        None)

    def on_prop_change(self, interface_name, changed_properties,
                       invalidated_properties, path=None):
        if interface_name != self.INTERFACE_MPRIS:
            logger.warn('unexpected interface: %s', interface_name)
            return
        
        collected_info = {}

        if changed_properties.has_key('PlaybackStatus'):
            collected_info['status'] = str(changed_properties['PlaybackStatus'])
        if changed_properties.has_key('Metadata'):
            collected_info['uri'] = changed_properties['Metadata']['xesam:url']
            collected_info['length'] = changed_properties['Metadata']['mpris:length']
        if changed_properties.has_key('Rate'):
            collected_info['rate'] = changed_properties['Rate']
        collected_info['pos'] = self.query_position()

        if not collected_info.has_key('status'):
            collected_info['status'] = str(self.query_status())
        logger.debug('collected info: %r', collected_info)

        self.cur.update(**collected_info)

    def on_seeked(self, position):
        logger.debug('seeked to pos: %f', position)
        self.cur.update(pos=position)

    def query_position(self):
        proxy = self.bus.get_object(self.OBJECT_VLC,self.PATH_MPRIS)
        props = dbus.Interface(proxy, self.INTERFACE_PROPS)
        return props.Get(self.INTERFACE_MPRIS, 'Position')

    def query_status(self):
        proxy = self.bus.get_object(self.OBJECT_VLC,self.PATH_MPRIS)
        props = dbus.Interface(proxy, self.INTERFACE_PROPS)
        return props.Get(self.INTERFACE_MPRIS, 'PlaybackStatus')

class gPodderNotifier(dbus.service.Object):
    def __init__(self, bus, path):
        dbus.service.Object.__init__(self, bus, path)

    @dbus.service.signal(dbus_interface='org.gpodder.player', signature='us')
    def PlaybackStarted(self, start_position, file_uri):
        logger.info('PlaybackStarted: %s: %d', file_uri, start_position)

    @dbus.service.signal(dbus_interface='org.gpodder.player', signature='uuus')
    def PlaybackStopped(self, start_position, end_position, total_time, file_uri):
        logger.info('PlaybackStopped: %s: %d--%d/%d',
            file_uri, start_position, end_position, total_time)
         
# Finally, this is the extension, which just pulls this all together
class gPodderExtension:

    def __init__(self, container):
        self.container = container
        self.path = '/org/gpodder/player/notifier'

    def on_load(self):
        self.session_bus = gpodder.dbus_session_bus
        self.notifier = gPodderNotifier(self.session_bus, self.path)
        self.rcvr = MPRISDBusReceiver(self.session_bus, self.notifier)

    def on_unload(self):
        self.notifier.remove_from_connection(self.session_bus, self.path)
        self.rcvr.stop_receiving()


########NEW FILE########
__FILENAME__ = normalize_audio
# -*- coding: utf-8 -*-
# This extension adjusts the volume of audio files to a standard level
# Supported file formats are mp3 and ogg
#
# Requires: normalize-audio, mpg123
#
# (c) 2011-11-06 Bernd Schlapsi <brot@gmx.info>
# Released under the same license terms as gPodder itself.

import os
import subprocess

import gpodder
from gpodder import util

import logging
logger = logging.getLogger(__name__)

_ = gpodder.gettext

__title__ = _('Normalize audio with re-encoding')
__description__ = _('Normalize the volume of audio files with normalize-audio')
__authors__ = 'Bernd Schlapsi <brot@gmx.info>'
__doc__ = 'http://wiki.gpodder.org/wiki/Extensions/NormalizeAudio'
__payment__ = 'https://flattr.com/submit/auto?user_id=BerndSch&url=http://wiki.gpodder.org/wiki/Extensions/NormalizeAudio'
__category__ = 'post-download'


DefaultConfig = {
    'context_menu': True, # Show action in the episode list context menu
}

# a tuple of (extension, command)
CONVERT_COMMANDS = {
    '.ogg': 'normalize-ogg',
    '.mp3': 'normalize-mp3',
}

class gPodderExtension:
    MIME_TYPES = ('audio/mpeg', 'audio/ogg', )
    EXT = ('.mp3', '.ogg', )

    def __init__(self, container):
        self.container = container

        # Dependency check
        self.container.require_command('normalize-ogg')
        self.container.require_command('normalize-mp3')
        self.container.require_command('normalize-audio')

    def on_load(self):
        logger.info('Extension "%s" is being loaded.' % __title__)

    def on_unload(self):
        logger.info('Extension "%s" is being unloaded.' % __title__)

    def on_episode_downloaded(self, episode):
        self._convert_episode(episode)

    def on_episodes_context_menu(self, episodes):
        if not self.container.config.context_menu:
            return None

        if not any(self._check_source(episode) for episode in episodes):
            return None

        return [(self.container.metadata.title, self.convert_episodes)]

    def _check_source(self, episode):
        if not episode.file_exists():
            return False

        if episode.mime_type in self.MIME_TYPES:
            return True

        if episode.extension() in self.EXT:
            return True

        return False

    def _convert_episode(self, episode):
        if episode.file_type() != 'audio':
            return

        filename = episode.local_filename(create=False)
        if filename is None:
            return

        basename, extension = os.path.splitext(filename)

        cmd = [CONVERT_COMMANDS.get(extension, 'normalize-audio'), filename]

        p = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                stderr=subprocess.PIPE)
        stdout, stderr = p.communicate()

        if p.returncode == 0:
            logger.info('normalize-audio processing successful.')
            gpodder.user_extensions.on_notification_show(_('File normalized'),
                    episode.title)
        else:
            logger.warn('normalize-audio failed: %s / %s', stdout, stderr)

    def convert_episodes(self, episodes):
        for episode in episodes:
            self._convert_episode(episode)


########NEW FILE########
__FILENAME__ = notification-win32
# -*- coding: utf-8 -*-
#
# gPodder - A media aggregator and podcast client
# Copyright (c) 2005-2014 Thomas Perl and the gPodder Team
#
# gPodder is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# gPodder is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#

# Notification implementation for Windows
# Sean Munkel; 2012-12-29

__title__ = 'Notification Bubbles for Windows'
__description__ = 'Display notification bubbles for different events.'
__authors__ = 'Sean Munkel <SeanMunkel@gmail.com>'
__category__ = 'desktop-integration'
__mandatory_in__ = 'win32'
__only_for__ = 'win32'

import functools
import os
import os.path
import gpodder
import pywintypes
import win32gui

import logging

logger = logging.getLogger(__name__)

IDI_APPLICATION = 32512
WM_TASKBARCREATED = win32gui.RegisterWindowMessage('TaskbarCreated')
WM_TRAYMESSAGE = 1044

# based on http://code.activestate.com/recipes/334779/
class NotifyIcon(object):
    def __init__(self, hwnd):
        self._hwnd = hwnd
        self._id = 0
        self._flags = win32gui.NIF_MESSAGE | win32gui.NIF_ICON
        self._callbackmessage = WM_TRAYMESSAGE
        path = os.path.join(os.path.dirname(__file__), '..', '..',
                'icons', 'hicolor', '16x16', 'apps', 'gpodder.ico')
        icon_path = os.path.abspath(path)

        try:
            self._hicon = win32gui.LoadImage(None, icon_path, 1, 0, 0, 0x50)
        except pywintypes.error as e:
            logger.warn("Couldn't load gpodder icon for tray")
            self._hicon = win32gui.LoadIcon(0, IDI_APPLICATION)

        self._tip = ''
        self._info = ''
        self._timeout = 0
        self._infotitle = ''
        self._infoflags = win32gui.NIIF_NONE
        win32gui.Shell_NotifyIcon(win32gui.NIM_ADD, self.notify_config_data)

    @property
    def notify_config_data(self):
        """ Function to retrieve the NOTIFYICONDATA Structure. """
        return (self._hwnd, self._id, self._flags, self._callbackmessage,
                self._hicon, self._tip, self._info, self._timeout,
                self._infotitle, self._infoflags)

    def remove(self):
        """ Removes the tray icon. """
        win32gui.Shell_NotifyIcon(win32gui.NIM_DELETE,
                self.notify_config_data)

    def set_tooltip(self, tooltip):
        """ Sets the tray icon tooltip. """
        self._flags = self._flags | win32gui.NIF_TIP
        self._tip = tooltip.encode("mbcs")
        win32gui.Shell_NotifyIcon(win32gui.NIM_MODIFY,
                self.notify_config_data)

    def show_balloon(self, title, text, timeout=10,
            icon=win32gui.NIIF_NONE):
        """ Shows a balloon tooltip from the tray icon. """
        self._flags = self._flags | win32gui.NIF_INFO
        self._infotitle = title.encode("mbcs")
        self._info = text.encode("mbcs")
        self._timeout = timeout * 1000
        self._infoflags = icon
        win32gui.Shell_NotifyIcon(win32gui.NIM_MODIFY,
                self.notify_config_data)


class gPodderExtension(object):
    def __init__(self, *args):
        self.notifier = None

    def on_ui_object_available(self, name, ui_object):
        def callback(self, window, *args):
            self.notifier = NotifyIcon(window.window.handle)

        if name == 'gpodder-gtk':
            ui_object.main_window.connect('realize',
                    functools.partial(callback, self))

    def on_notification_show(self, title, message):
        if self.notifier is not None:
            self.notifier.show_balloon(title, message)

    def on_unload(self):
        if self.notifier is not None:
            self.notifier.remove()


########NEW FILE########
__FILENAME__ = notification
# -*- coding: utf-8 -*-
#
# gPodder - A media aggregator and podcast client
# Copyright (c) 2005-2011 Thomas Perl and the gPodder Team
#
# gPodder is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# gPodder is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#

# Bernd Schlapsi <brot@gmx.info>; 2011-11-20

__title__ = 'Gtk+ Desktop Notifications'
__description__ = 'Display notification bubbles for different events.'
__category__ = 'desktop-integration'
__only_for__ = 'gtk'
__mandatory_in__ = 'gtk'
__disable_in__ = 'win32'

import gpodder

import logging
logger = logging.getLogger(__name__)

try:
    import pynotify
except ImportError:
    pynotify = None


if pynotify is None:
    class gPodderExtension(object):
        def __init__(self, container):
            logger.info('Could not find PyNotify.')
else:
    class gPodderExtension(object):
        def __init__(self, container):
            self.container = container

        def on_load(self):
            pynotify.init('gPodder')

        def on_unload(self):
            pynotify.uninit()

        def on_notification_show(self, title, message):
            if not message and not title:
                return

            notify = pynotify.Notification(title or '', message or '',
                    gpodder.icon_file)

            try:
                notify.show()
            except:
                # See http://gpodder.org/bug/966
                pass


########NEW FILE########
__FILENAME__ = rename_download
# -*- coding: utf-8 -*-
# Rename files after download based on the episode title
# Copyright (c) 2011-04-04 Thomas Perl <thp.io>
# Licensed under the same terms as gPodder itself

import os

import gpodder
from gpodder import util

import logging
logger = logging.getLogger(__name__)

_ = gpodder.gettext

__title__ = _('Rename episodes after download')
__description__ = _('Rename episodes to "<Episode Title>.<ext>" on download')
__authors__ = 'Bernd Schlapsi <brot@gmx.info>, Thomas Perl <thp@gpodder.org>'
__doc__ = 'http://wiki.gpodder.org/wiki/Extensions/RenameAfterDownload'
__payment__ = 'https://flattr.com/submit/auto?user_id=BerndSch&url=http://wiki.gpodder.org/wiki/Extensions/RenameAfterDownload'
__category__ = 'post-download'


class gPodderExtension:
    def __init__(self, container):
        self.container = container

    def on_episode_downloaded(self, episode):
        current_filename = episode.local_filename(create=False)

        new_filename = self.make_filename(current_filename, episode.title)

        if new_filename != current_filename:
            logger.info('Renaming: %s -> %s', current_filename, new_filename)
            os.rename(current_filename, new_filename)
            util.rename_episode_file(episode, new_filename)

    def make_filename(self, current_filename, title):
        dirname = os.path.dirname(current_filename)
        filename = os.path.basename(current_filename)
        basename, ext = os.path.splitext(filename)

        new_basename = util.sanitize_encoding(title) + ext
        # On Windows, force ASCII encoding for filenames (bug 1724)
        new_basename = util.sanitize_filename(new_basename,
                use_ascii=gpodder.ui.win32)
        new_filename = os.path.join(dirname, new_basename)

        if new_filename == current_filename:
            return current_filename

        for filename in util.generate_names(new_filename):
            # Avoid filename collisions
            if not os.path.exists(filename):
                return filename


########NEW FILE########
__FILENAME__ = rm_ogg_cover
#!/usr/bin/python
# -*- coding: utf-8 -*-
####
# 01/2011 Bernd Schlapsi <brot@gmx.info>
#
# This script is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# gPodder is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
# Dependencies:
# * python-mutagen (Mutagen is a Python module to handle audio metadata)
#
# This extension scripts removes coverart from all downloaded ogg files.
# The reason for this script is that my media player (MEIZU SL6)
# couldn't handle ogg files with included coverart

import os

import gpodder

import logging
logger = logging.getLogger(__name__)

from mutagen.oggvorbis import OggVorbis

_ = gpodder.gettext

__title__ = _('Remove cover art from OGG files')
__description__ = _('removes coverart from all downloaded ogg files')
__authors__ = 'Bernd Schlapsi <brot@gmx.info>'
__doc__ = 'http://wiki.gpodder.org/wiki/Extensions/RemoveOGGCover'
__payment__ = 'https://flattr.com/submit/auto?user_id=BerndSch&url=http://wiki.gpodder.org/wiki/Extensions/RemoveOGGCover'
__category__ = 'post-download'


DefaultConfig = {
    'context_menu': True, # Show item in context menu
}


class gPodderExtension:
    def __init__(self, container):
        self.container = container
        self.config = self.container.config

    def on_episode_downloaded(self, episode):
        self.rm_ogg_cover(episode)

    def on_episodes_context_menu(self, episodes):
        if not self.config.context_menu:
            return None

        if 'audio/ogg' not in [e.mime_type for e in episodes
            if e.mime_type is not None and e.file_exists()]:
            return None

        return [(_('Remove cover art'), self._rm_ogg_covers)]

    def _rm_ogg_covers(self, episodes):
        for episode in episodes:
            self.rm_ogg_cover(episode)

    def rm_ogg_cover(self, episode):
        filename = episode.local_filename(create=False)
        if filename is None:
            return

        basename, extension = os.path.splitext(filename)

        if episode.file_type() != 'audio':
            return

        if extension.lower() != '.ogg':
            return

        try:
            ogg = OggVorbis(filename)

            found = False
            for key in ogg.keys():
                if key.startswith('cover'):
                    found = True
                    ogg.pop(key)

            if found:
                logger.info('Removed cover art from OGG file: %s', filename)
                ogg.save()
        except Exception, e:
            logger.warn('Failed to remove OGG cover: %s', e, exc_info=True)


########NEW FILE########
__FILENAME__ = rockbox_convert2mp4
#!/usr/bin/python
# -*- coding: utf-8 -*-
# Requirements: apt-get install python-kaa-metadata  ffmpeg python-dbus
# To use, copy it as a Python script into ~/.config/gpodder/extensions/rockbox_mp4_convert.py
# See the module "gpodder.extensions" for a description of when each extension
# gets called and what the parameters of each extension are.
#Based on Rename files after download based on the episode title
#And patch in Bug https://bugs.gpodder.org/show_bug.cgi?id=1263
# Copyright (c) 2011-04-06 Guy Sheffer <guysoft at gmail.com>
# Copyright (c) 2011-04-04 Thomas Perl <thp.io>
# Licensed under the same terms as gPodder itself

import kaa.metadata
import os
import shlex
import subprocess

import gpodder
from gpodder import util

import logging
logger = logging.getLogger(__name__)

_ = gpodder.gettext

__title__ = _('Convert video files to MP4 for Rockbox')
__description__ = _('Converts all videos to a Rockbox-compatible format')
__authors__ = 'Guy Sheffer <guysoft@gmail.com>, Thomas Perl <thp@gpodder.org>, Bernd Schlapsi <brot@gmx.info>'
__category__ = 'post-download'


DefaultConfig = {
    'device_height': 176.0,
    'device_width': 224.0,
    'ffmpeg_options': '-vcodec mpeg2video -b 500k -ab 192k -ac 2 -ar 44100 -acodec libmp3lame',
}

ROCKBOX_EXTENSION = "mpg"
EXTENTIONS_TO_CONVERT = ['.mp4',"." + ROCKBOX_EXTENSION]
FFMPEG_CMD = 'ffmpeg -y -i "%(from)s" -s %(width)sx%(height)s %(options)s "%(to)s"'


class gPodderExtension:
    def __init__(self, container):
        self.container = container

        program = shlex.split(FFMPEG_CMD)[0]
        if not util.find_command(program):
            raise ImportError("Couldn't find program '%s'" % program)

    def on_load(self):
        logger.info('Extension "%s" is being loaded.' % __title__)

    def on_unload(self):
        logger.info('Extension "%s" is being unloaded.' % __title__)

    def on_episode_downloaded(self, episode):
        current_filename = episode.local_filename(False)
        converted_filename = self._convert_mp4(episode, current_filename)

        if converted_filename is not None:
            util.rename_episode_file(episode, converted_filename)
            os.remove(current_filename)
            logger.info('Conversion for %s was successfully' % current_filename)
            gpodder.user_extensions.on_notification_show(_('File converted'), episode.title)

    def _get_rockbox_filename(self, origin_filename):
        if not os.path.exists(origin_filename):
            logger.info("File '%s' don't exists." % origin_filename)
            return None

        dirname = os.path.dirname(origin_filename)
        filename = os.path.basename(origin_filename)
        basename, ext = os.path.splitext(filename)

        if ext not in EXTENTIONS_TO_CONVERT:
            logger.info("Ignore file with file-extension %s." % ext)
            return None

        if filename.endswith(ROCKBOX_EXTENSION):
            new_filename = "%s-convert.%s" % (basename, ROCKBOX_EXTENSION)
        else:
            new_filename = "%s.%s" % (basename, ROCKBOX_EXTENSION)
        return os.path.join(dirname, new_filename)


    def _calc_resolution(self, video_width, video_height, device_width, device_height):
        if video_height is None:
            return None

        width_ratio = device_width / video_width
        height_ratio = device_height / video_height

        dest_width = device_width
        dest_height = width_ratio * video_height

        if dest_height > device_height:
            dest_width = height_ratio * video_width
            dest_height = device_height

        return (int(round(dest_width)), round(int(dest_height)))


    def _convert_mp4(self, episode, from_file):
        """Convert MP4 file to rockbox mpg file"""

        # generate new filename and check if the file already exists
        to_file = self._get_rockbox_filename(from_file)
        if to_file is None:
            return None
        if os.path.isfile(to_file):
            return to_file

        logger.info("Converting: %s", from_file)
        gpodder.user_extensions.on_notification_show("Converting", episode.title)

        # calculationg the new screen resolution
        info = kaa.metadata.parse(from_file)
        resolution = self._calc_resolution(
            info.video[0].width,
            info.video[0].height,
            self.container.config.device_width,
            self.container.config.device_height
        )
        if resolution is None:
            logger.error("Error calculating the new screen resolution")
            return None

        convert_command = FFMPEG_CMD % {
            'from': from_file,
            'to': to_file,
            'width': str(resolution[0]),
            'height': str(resolution[1]),
            'options': self.container.config.ffmpeg_options
        }

        # Prior to Python 2.7.3, this module (shlex) did not support Unicode input.
        convert_command = util.sanitize_encoding(convert_command)

        process = subprocess.Popen(shlex.split(convert_command),
            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = process.communicate()
        if process.returncode != 0:
            logger.error(stderr)
            return None

        gpodder.user_extensions.on_notification_show("Converting finished", episode.title)

        return to_file

########NEW FILE########
__FILENAME__ = rockbox_coverart
# Copies cover art to a file based device
#
# (c) 2014-04-10 Alex Mayer <magictrick4906@aim.com>
# Released under the same license terms as gPodder itself.

import os
import shutil

# Use a logger for debug output - this will be managed by gPodder
import logging
logger = logging.getLogger(__name__)

# Provide some metadata that will be displayed in the gPodder GUI
__title__ = 'Rockbox Cover Art Sync'
__description__ = 'Copy Cover Art To Rockboxed Media Player'
__only_for__ = 'gtk, cli, qml'
__authors__ = 'Alex Mayer <magictrick4906@aim.com>'

DefaultConfig = {
    "art_name_on_device": "cover.jpg" # The file name that will be used on the device for cover art
}

class gPodderExtension:

    def __init__(self, container):
        self.container = container
        self.config = self.container.config

    def on_episode_synced(self, device, episode):
        # check that we have the functions we need
        if hasattr(device, 'get_episode_folder_on_device'):
            # get the file and folder names we need
            episode_folder = os.path.dirname(episode.local_filename(False))
            device_folder = device.get_episode_folder_on_device(episode)
            episode_art = os.path.join(episode_folder, "folder.jpg")
            device_art = os.path.join(device_folder, self.config.art_name_on_device)
            # make sure we have art to copy and it doesnt already exist
            if os.path.isfile(episode_art) and not os.path.isfile(device_art):
                logger.info('Syncing cover art for %s', episode.channel.title)
                # copy and rename art
                shutil.copy(episode_art, device_art)


########NEW FILE########
__FILENAME__ = sonos
# -*- coding: utf-8 -*-
# Extension script to stream podcasts to Sonos speakers
# Requirements: gPodder 3.x and the soco module (https://github.com/rahims/SoCo)
# (c) 2013-01-19 Stefan Kögl <stefan@skoegl.net>
# Released under the same license terms as gPodder itself.

from functools import partial

import gpodder
_ = gpodder.gettext

import logging
logger = logging.getLogger(__name__)

import soco
import requests


__title__ = _('Stream to Sonos')
__description__ = _('Stream podcasts to Sonos speakers')
__authors__ = 'Stefan Kögl <stefan@skoegl.net>'
__category__ = 'interface'
__only_for__ = 'gtk'


SONOS_CAN_PLAY = lambda e: 'audio' in e.file_type()

class gPodderExtension:
    def __init__(self, container):
        sd = soco.SonosDiscovery()
        speaker_ips = sd.get_speaker_ips()

        logger.info('Found Sonos speakers: %s' % ', '.join(speaker_ips))

        self.speakers = {}
        for speaker_ip in speaker_ips:
            controller = soco.SoCo(speaker_ip)

            try:
                info = controller.get_speaker_info()

            except requests.ConnectionError as ce:
                # ignore speakers we can't connect to
                continue

            name = info.get('zone_name', None)

            # devices that do not have a name are probably bridges
            if name:
                self.speakers[speaker_ip] = name

    def _stream_to_speaker(self, speaker_ip, episodes):
        """ Play or enqueue selected episodes """

        urls = [episode.url for episode in episodes if SONOS_CAN_PLAY(episode)]
        logger.info('Streaming to Sonos %s: %s'%(speaker_ip, ', '.join(urls)))

        controller = soco.SoCo(speaker_ip)

        # enqueue and play
        for episode in episodes:
            controller.add_to_queue(episode.url)
            episode.playback_mark()

        controller.play()

    def on_episodes_context_menu(self, episodes):
        """ Adds a context menu for each Sonos speaker group """

        # Only show context menu if we can play at least one file
        if not any(SONOS_CAN_PLAY(e) for e in episodes):
            return []

        menu_entries = []
        for speaker_ip, name in self.speakers.items():
            callback = partial(self._stream_to_speaker, speaker_ip)

            menu_entries.append('/'.join((_('Stream to Sonos'), name)), callback)

        return menu_entries

########NEW FILE########
__FILENAME__ = tagging
#!/usr/bin/python
# -*- coding: utf-8 -*-
####
# 01/2011 Bernd Schlapsi <brot@gmx.info>
#
# This script is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# gPodder is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
# Dependencies:
# * python-mutagen (Mutagen is a Python module to handle audio metadata)
#
# This extension script adds episode title and podcast title to the audio file
# The episode title is written into the title tag
# The podcast title is written into the album tag

import base64
import datetime
import mimetypes
import os

import gpodder
from gpodder import coverart

import logging
logger = logging.getLogger(__name__)

from mutagen import File
from mutagen.flac import Picture
from mutagen.mp3 import MP3
from mutagen.id3 import ID3, APIC
from mutagen.mp4 import MP4Cover

_ = gpodder.gettext

__title__ = _('Tag downloaded files using Mutagen')
__description__ = _('Add episode and podcast titles to MP3/OGG tags')
__authors__ = 'Bernd Schlapsi <brot@gmx.info>'
__doc__ = 'http://wiki.gpodder.org/wiki/Extensions/Tagging'
__payment__ = 'https://flattr.com/submit/auto?user_id=BerndSch&url=http://wiki.gpodder.org/wiki/Extensions/Tagging'
__category__ = 'post-download'


DefaultConfig = {
    'strip_album_from_title': True,
    'genre_tag': 'Podcast',
    'always_remove_tags': False,
    'auto_embed_coverart': False,
}


class AudioFile(object):
    def __init__(self, filename, album, title, genre, pubDate, cover):
        self.filename = filename
        self.album = album
        self.title = title
        self.genre = genre
        self.pubDate = pubDate
        self.cover = cover

    def remove_tags(self):
        audio = File(self.filename, easy=True)
        if audio.tags is not None:
            audio.delete()
        audio.save()

    def write_basic_tags(self):
        audio = File(self.filename, easy=True)

        if audio.tags is None:
            audio.add_tags()

        if self.album is not None:
            audio.tags['album'] = self.album

        if self.title is not None:
            audio.tags['title'] = self.title

        if self.genre is not None:
            audio.tags['genre'] = self.genre

        if self.pubDate is not None:
            audio.tags['date'] = self.pubDate

        audio.save()

    def insert_coverart(self):
        """ implement the cover art logic in the subclass
        """
        None

    def get_cover_picture(self, cover):
        """ Returns mutage Picture class for the cover image
        Usefull for OGG and FLAC format

        Picture type = cover image
        see http://flac.sourceforge.net/documentation_tools_flac.html#encoding_options
        """
        f = file(cover)
        p = Picture()
        p.type = 3
        p.data = f.read()
        p.mime = mimetypes.guess_type(cover)[0]
        f.close()

        return p


class OggFile(AudioFile):
    def __init__(self, filename, album, title, genre, pubDate, cover):
        super(OggFile, self).__init__(filename, album, title, genre, pubDate, cover)

    def insert_coverart(self):
        audio = File(self.filename, easy=True)
        p = self.get_cover_picture(self.cover)
        audio['METADATA_BLOCK_PICTURE'] = base64.b64encode(p.write())
        audio.save()


class Mp4File(AudioFile):
    def __init__(self, filename, album, title, genre, pubDate, cover):
        super(Mp4File, self).__init__(filename, album, title, genre, pubDate, cover)

    def insert_coverart(self):
        audio = File(self.filename)

        if self.cover.endswith('png'):
            cover_format = MP4Cover.FORMAT_PNG
        else:
            cover_format = MP4Cover.FORMAT_JPEG

        data = open(self.cover, 'rb').read()
        audio.tags['covr'] =  [MP4Cover(data, cover_format)]
        audio.save()


class Mp3File(AudioFile):
    def __init__(self, filename, album, title, genre, pubDate, cover):
        super(Mp3File, self).__init__(filename, album, title, genre, pubDate, cover)

    def insert_coverart(self):
        audio = MP3(self.filename, ID3=ID3)

        if audio.tags is None:
            audio.add_tags()

        audio.tags.add(
            APIC(
                encoding = 3, # 3 is for utf-8
                mime = mimetypes.guess_type(self.cover)[0],
                type = 3,
                desc = u'Cover',
                data = open(self.cover).read()
            )
        )
        audio.save()


class gPodderExtension:
    def __init__(self, container):
        self.container = container

    def on_episode_downloaded(self, episode):
        info = self.read_episode_info(episode)
        if info['filename'] is None:
            return

        self.write_info2file(info, episode)

    def get_audio(self, info, episode):
        audio = None
        cover = None

        if self.container.config.auto_embed_coverart:
            cover = self.get_cover(episode.channel)

        if info['filename'].endswith('.mp3'):
            audio = Mp3File(info['filename'],
                info['album'],
                info['title'],
                info['genre'],
                info['pubDate'],
                cover)
        elif info['filename'].endswith('.ogg'):
            audio = OggFile(info['filename'],
                info['album'],
                info['title'],
                info['genre'],
                info['pubDate'],
                cover)
        elif info['filename'].endswith('.m4a') or info['filename'].endswith('.mp4'):
            audio = Mp4File(info['filename'],
                info['album'],
                info['title'],
                info['genre'],
                info['pubDate'],
                cover)

        return audio

    def read_episode_info(self, episode):
        info = {
            'filename': None,
            'album': None,
            'title': None,
            'genre': None,
            'pubDate': None
        }

        # read filename (incl. file path) from gPodder database
        info['filename'] = episode.local_filename(create=False, check_only=True)
        if info['filename'] is None:
            return

        # read title+album from gPodder database
        info['album'] = episode.channel.title
        title = episode.title
        if (self.container.config.strip_album_from_title and title and info['album'] and title.startswith(info['album'])):
            info['title'] = title[len(info['album']):].lstrip()
        else:
            info['title'] = title

        if self.container.config.genre_tag is not None:
            info['genre'] = self.container.config.genre_tag

        # convert pubDate to string
        try:
            pubDate = datetime.datetime.fromtimestamp(episode.pubDate)
            info['pubDate'] = pubDate.strftime('%Y-%m-%d %H:%M')
        except:
            try:
                # since version 3 the published date has a new/other name
                pubDate = datetime.datetime.fromtimestamp(episode.published)
                info['pubDate'] = pubDate.strftime('%Y-%m-%d %H:%M')
            except:
                info['pubDate'] = None

        return info

    def write_info2file(self, info, episode):
        audio = self.get_audio(info, episode)

        if self.container.config.always_remove_tags:
            audio.remove_tags()
        else:
            audio.write_basic_tags()

            if self.container.config.auto_embed_coverart:
                audio.insert_coverart()

        logger.info(u'tagging.on_episode_downloaded(%s/%s)', episode.channel.title, episode.title)

    def get_cover(self, podcast):
        downloader = coverart.CoverDownloader()
        return downloader.get_cover(podcast.cover_file, podcast.cover_url,
            podcast.url, podcast.title, None, None, True)

########NEW FILE########
__FILENAME__ = taskbar_progress
# -*- coding: utf-8 -*-
#
# gPodder - A media aggregator and podcast client
# Copyright (c) 2005-2014 Thomas Perl and the gPodder Team
#
# gPodder is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# gPodder is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#

# Windows 7 taskbar progress
# Sean Munkel; 2013-01-05

import gpodder

_ = gpodder.gettext


__title__ = _('Show download progress on the taskbar')
__description__ = _('Displays the progress on the Windows taskbar.')
__authors__ = 'Sean Munkel <seanmunkel@gmail.com>'
__category__ = 'desktop-integration'
__only_for__ = 'win32'


from ctypes import (c_ushort, c_int, c_uint, c_ulong, c_ulonglong,
                    c_wchar_p, alignment, sizeof, Structure, POINTER)
from comtypes import IUnknown, GUID, COMMETHOD, wireHWND, client
from ctypes import HRESULT
from ctypes.wintypes import tagRECT
import functools

import logging
logger = logging.getLogger(__name__)

WSTRING = c_wchar_p
# values for enumeration 'TBPFLAG'
TBPF_NOPROGRESS = 0
TBPF_INDETERMINATE = 1
TBPF_NORMAL = 2
TBPF_ERROR = 4
TBPF_PAUSED = 8
TBPFLAG = c_int  # enum
# values for enumeration 'TBATFLAG'
TBATF_USEMDITHUMBNAIL = 1
TBATF_USEMDILIVEPREVIEW = 2
TBATFLAG = c_int  # enum


class tagTHUMBBUTTON(Structure):
    _fields_ = [
        ('dwMask', c_ulong),
        ('iId', c_uint),
        ('iBitmap', c_uint),
        ('hIcon', POINTER(IUnknown)),
        ('szTip', c_ushort * 260),
        ('dwFlags', c_ulong)]


class ITaskbarList(IUnknown):
    _case_insensitive_ = True
    _iid_ = GUID('{56FDF342-FD6D-11D0-958A-006097C9A090}')
    _idlflags_ = []
    _methods_ = [
        COMMETHOD([], HRESULT, 'HrInit'),
        COMMETHOD([], HRESULT, 'AddTab',
                  (['in'], c_int, 'hwnd')),
        COMMETHOD([], HRESULT, 'DeleteTab',
                  (['in'], c_int, 'hwnd')),
        COMMETHOD([], HRESULT, 'ActivateTab',
                  (['in'], c_int, 'hwnd')),
        COMMETHOD([], HRESULT, 'SetActivateAlt',
                  (['in'], c_int, 'hwnd'))]


class ITaskbarList2(ITaskbarList):
    _case_insensitive_ = True
    _iid_ = GUID('{602D4995-B13A-429B-A66E-1935E44F4317}')
    _idlflags_ = []
    _methods_ = [
        COMMETHOD([], HRESULT, 'MarkFullscreenWindow',
                  (['in'], c_int, 'hwnd'),
                  (['in'], c_int, 'fFullscreen'))]


class ITaskbarList3(ITaskbarList2):
    _case_insensitive_ = True
    _iid_ = GUID('{EA1AFB91-9E28-4B86-90E9-9E9F8A5EEFAF}')
    _idlflags_ = []
    _methods_ = [
        COMMETHOD([], HRESULT, 'SetProgressValue',
                  (['in'], c_int, 'hwnd'),
                  (['in'], c_ulonglong, 'ullCompleted'),
                  (['in'], c_ulonglong, 'ullTotal')),
        COMMETHOD([], HRESULT, 'SetProgressState',
                  (['in'], c_int, 'hwnd'),
                  (['in'], TBPFLAG, 'tbpFlags')),
        COMMETHOD([], HRESULT, 'RegisterTab',
                  (['in'], c_int, 'hwndTab'),
                  (['in'], wireHWND, 'hwndMDI')),
        COMMETHOD([], HRESULT, 'UnregisterTab',
                  (['in'], c_int, 'hwndTab')),
        COMMETHOD([], HRESULT, 'SetTabOrder',
                  (['in'], c_int, 'hwndTab'),
                  (['in'], c_int, 'hwndInsertBefore')),
        COMMETHOD([], HRESULT, 'SetTabActive',
                  (['in'], c_int, 'hwndTab'),
                  (['in'], c_int, 'hwndMDI'),
                  (['in'], TBATFLAG, 'tbatFlags')),
        COMMETHOD([], HRESULT, 'ThumbBarAddButtons',
                  (['in'], c_int, 'hwnd'),
                  (['in'], c_uint, 'cButtons'),
                  (['in'], POINTER(tagTHUMBBUTTON), 'pButton')),
        COMMETHOD([], HRESULT, 'ThumbBarUpdateButtons',
                  (['in'], c_int, 'hwnd'),
                  (['in'], c_uint, 'cButtons'),
                  (['in'], POINTER(tagTHUMBBUTTON), 'pButton')),
        COMMETHOD([], HRESULT, 'ThumbBarSetImageList',
                  (['in'], c_int, 'hwnd'),
                  (['in'], POINTER(IUnknown), 'himl')),
        COMMETHOD([], HRESULT, 'SetOverlayIcon',
                  (['in'], c_int, 'hwnd'),
                  (['in'], POINTER(IUnknown), 'hIcon'),
                  (['in'], WSTRING, 'pszDescription')),
        COMMETHOD([], HRESULT, 'SetThumbnailTooltip',
                  (['in'], c_int, 'hwnd'),
                  (['in'], WSTRING, 'pszTip')),
        COMMETHOD([], HRESULT, 'SetThumbnailClip',
                  (['in'], c_int, 'hwnd'),
                  (['in'], POINTER(tagRECT), 'prcClip'))]


assert sizeof(tagTHUMBBUTTON) == 540, sizeof(tagTHUMBBUTTON)
assert alignment(tagTHUMBBUTTON) == 4, alignment(tagTHUMBBUTTON)


# based on http://stackoverflow.com/a/1744503/905256
class gPodderExtension:
    def __init__(self, container):
        self.container = container
        self.window_handle = None
        self.restart_warning = True

    def on_load(self):
        self.taskbar = client.CreateObject(
                '{56FDF344-FD6D-11d0-958A-006097C9A090}',
                interface=ITaskbarList3)
        self.taskbar.HrInit()

    def on_unload(self):
        if self.taskbar is not None:
            self.taskbar.SetProgressState(self.window_handle, TBPF_NOPROGRESS)

    def on_ui_object_available(self, name, ui_object):
        def callback(self, window, *args):
            self.window_handle = window.window.handle

        if name == 'gpodder-gtk':
            ui_object.main_window.connect('realize',
                    functools.partial(callback, self))

    def on_download_progress(self, progress):
        if self.window_handle is None:
            if not self.restart_warning:
                return
            logger.warn("No window handle available, a restart max fix this")
            self.restart_warning = False
            return
        if 0 < progress < 1:
            self.taskbar.SetProgressState(self.window_handle, TBPF_NORMAL)
            self.taskbar.SetProgressValue(self.window_handle,
                    int(progress * 100), 100)
        else:
            self.taskbar.SetProgressState(self.window_handle, TBPF_NOPROGRESS)


########NEW FILE########
__FILENAME__ = ted_subtitles
# -*- coding: utf-8 -*-
# vi:si:et:sw=4:sts=4:ts=4
import os
import json
import logging
import re

from datetime import timedelta
logger = logging.getLogger(__name__)

import gpodder
from gpodder import util

_ = gpodder.gettext

__title__ = _('Subtitle Downloader for TED Talks')
__description__ = _('Downloads .srt subtitles for TED Talks Videos')
__authors__ = 'Danilo Shiga <daniloshiga@gmail.com>'
__category__ = 'post-download'
__only_for__ = 'gtk, cli, qml'


class gPodderExtension(object):
    """
    TED Subtitle Download Extension
    Downloads ted subtitles
    """
    def __init__(self, container):
        self.container = container

    def milli_to_srt(self, time):
        """Converts milliseconds to srt time format"""
        srt_time = timedelta(milliseconds=time)
        srt_time = str(srt_time)
        if '.' in srt_time:
            srt_time = srt_time.replace('.', ',')[:11]
        else:
            # ',000' required to be a valid srt line
            srt_time += ',000'

        return srt_time

    def ted_to_srt(self, jsonstring, introduration):
        """Converts the json object to srt format"""
        jsonobject = json.loads(jsonstring)

        srtContent = ''
        for captionIndex, caption in enumerate(jsonobject['captions'], 1):
            startTime = self.milli_to_srt(introduration + caption['startTime'])
            endTime = self.milli_to_srt(introduration + caption['startTime'] +
                                        caption['duration'])
            srtContent += ''.join([str(captionIndex), os.linesep, startTime,
                                   ' --> ', endTime, os.linesep,
                                   caption['content'], os.linesep * 2])

        return srtContent

    def get_data_from_url(self, url):
        try:
            response = util.urlopen(url).read()
        except Exception, e:
            logger.warn("subtitle url returned error %s", e)
            return ''
        return response

    def get_srt_filename(self, audio_filename):
        basename, _ = os.path.splitext(audio_filename)
        return basename + '.srt'

    def on_episode_downloaded(self, episode):
        guid_result = re.search(r'talk.ted.com:(\d+)', episode.guid)
        if guid_result is not None:
            talkId = int(guid_result.group(1))
        else:
            logger.debug('Not a TED Talk. Ignoring.')
            return

        sub_url = 'http://www.ted.com/talks/subtitles/id/%s/lang/eng' % talkId
        logger.info('subtitle url: %s', sub_url)
        sub_data = self.get_data_from_url(sub_url)
        if not sub_data:
            return

        logger.info('episode url: %s', episode.link)
        episode_data = self.get_data_from_url(episode.link)
        if not episode_data:
            return

        INTRO_DEFAULT = 15
        try:
            # intro in the data could be 15 or 15.33
            intro = episode_data
            intro = episode_data.split('introDuration":')[1] \
                                .split(',')[0] or INTRO_DEFAULT
            intro = int(float(intro)*1000)
        except (ValueError, IndexError), e:
            logger.info("Couldn't parse introDuration string: %s", intro)
            intro = INTRO_DEFAULT * 1000
        current_filename = episode.local_filename(create=False)
        srt_filename = self.get_srt_filename(current_filename)
        sub = self.ted_to_srt(sub_data, int(intro))

        try:
            with open(srt_filename, 'w+') as srtFile:
                srtFile.write(sub.encode("utf-8"))
        except Exception, e:
            logger.warn("Can't write srt file: %s",e)

    def on_episode_delete(self, episode, filename):
        srt_filename = self.get_srt_filename(filename)
        if os.path.exists(srt_filename):
            os.remove(srt_filename)


########NEW FILE########
__FILENAME__ = ubuntu_appindicator
# -*- coding: utf-8 -*-

# Ubuntu AppIndicator Icon
# Thomas Perl <thp@gpodder.org>; 2012-02-24

import gpodder

_ = gpodder.gettext

__title__ = _('Ubuntu App Indicator')
__description__ = _('Show a status indicator in the top bar.')
__authors__ = 'Thomas Perl <thp@gpodder.org>'
__category__ = 'desktop-integration'
__only_for__ = 'gtk'
__mandatory_in__ = 'unity'
__disable_in__ = 'win32'


import appindicator
import gtk

import logging

logger = logging.getLogger(__name__)

class gPodderExtension:
    def __init__(self, container):
        self.container = container
        self.indicator = None
        self.gpodder = None

    def on_load(self):
        self.indicator = appindicator.Indicator('gpodder', 'gpodder',
                appindicator.CATEGORY_APPLICATION_STATUS)
        self.indicator.set_status(appindicator.STATUS_ACTIVE)

    def _rebuild_menu(self):
        menu = gtk.Menu()
        toggle_visible = gtk.CheckMenuItem(_('Show main window'))
        toggle_visible.set_active(True)
        def on_toggle_visible(menu_item):
            if menu_item.get_active():
                self.gpodder.main_window.show()
            else:
                self.gpodder.main_window.hide()
        toggle_visible.connect('activate', on_toggle_visible)
        menu.append(toggle_visible)
        menu.append(gtk.SeparatorMenuItem())
        quit_gpodder = gtk.MenuItem(_('Quit'))
        def on_quit(menu_item):
            self.gpodder.on_gPodder_delete_event(self.gpodder.main_window)
        quit_gpodder.connect('activate', on_quit)
        menu.append(quit_gpodder)
        menu.show_all()
        self.indicator.set_menu(menu)

    def on_unload(self):
        self.indicator = None

    def on_ui_object_available(self, name, ui_object):
        if name == 'gpodder-gtk':
            self.gpodder = ui_object
            self._rebuild_menu()


########NEW FILE########
__FILENAME__ = ubuntu_unity
# -*- coding: utf-8 -*-

# Ubuntu Unity Launcher Integration
# Thomas Perl <thp@gpodder.org>; 2012-02-06

import gpodder

_ = gpodder.gettext

__title__ = _('Ubuntu Unity Integration')
__description__ = _('Show download progress in the Unity Launcher icon.')
__authors__ = 'Thomas Perl <thp@gpodder.org>'
__category__ = 'desktop-integration'
__only_for__ = 'unity'
__mandatory_in__ = 'unity'
__disable_in__ = 'win32'


# FIXME: Due to the fact that we do not yet use the GI-style bindings, we will
# have to run this module in its own interpreter and send commands to it using
# the subprocess module. Once we use GI-style bindings, we can get rid of all
# this and still expose the same "interface' (LauncherEntry and its methods)
# to our callers.

import os
import subprocess
import sys
import logging

if __name__ != '__main__':
    logger = logging.getLogger(__name__)

    class gPodderExtension:
        FILENAME = 'gpodder.desktop'

        def __init__(self, container):
            self.container = container
            self.process = None

        def on_load(self):
            logger.info('Starting Ubuntu Unity Integration.')
            os.environ['PYTHONPATH'] = os.pathsep.join(sys.path)
            self.process = subprocess.Popen(['python', __file__],
                    stdin=subprocess.PIPE)

        def on_unload(self):
            logger.info('Killing process...')
            self.process.terminate()
            self.process.wait()
            logger.info('Process killed.')

        def on_download_progress(self, progress):
            try:
                self.process.stdin.write('progress %f\n' % progress)
                self.process.stdin.flush()
            except Exception, e:
                logger.debug('Ubuntu progress update failed.', exc_info=True)
else:
    from gi.repository import Unity, GObject
    from gpodder import util
    import sys

    class InputReader:
        def __init__(self, fileobj, launcher):
            self.fileobj = fileobj
            self.launcher = launcher

        def read(self):
            while True:
                line = self.fileobj.readline()
                if not line:
                    break

                try:
                    command, value = line.strip().split()
                    if command == 'progress':
                        GObject.idle_add(launcher_entry.set_progress,
                                float(value))
                except:
                    pass

    class LauncherEntry:
        FILENAME = 'gpodder.desktop'

        def __init__(self):
            self.launcher = Unity.LauncherEntry.get_for_desktop_id(
                    self.FILENAME)

        def set_count(self, count):
            self.launcher.set_property('count', count)
            self.launcher.set_property('count_visible', count > 0)

        def set_progress(self, progress):
            self.launcher.set_property('progress', progress)
            self.launcher.set_property('progress_visible', 0. <= progress < 1.)

    GObject.threads_init()
    loop = GObject.MainLoop()
    util.run_in_background(loop.run)

    launcher_entry = LauncherEntry()
    reader = InputReader(sys.stdin, launcher_entry)
    reader.read()

    loop.quit()


########NEW FILE########
__FILENAME__ = update_feeds_on_startup
# -*- coding: utf-8 -*-
# Starts episode update search on startup
#
# (c) 2012-10-13 Bernd Schlapsi <brot@gmx.info>
# Released under the same license terms as gPodder itself.

import gpodder

import logging
logger = logging.getLogger(__name__)

_ = gpodder.gettext

__title__ = _('Search for new episodes on startup')
__description__ = _('Starts the search for new episodes on startup')
__authors__ = 'Bernd Schlapsi <brot@gmx.info>'
__doc__ = 'http://wiki.gpodder.org/wiki/Extensions/SearchEpisodeOnStartup'
__payment__ = 'https://flattr.com/submit/auto?user_id=BerndSch&url=http://wiki.gpodder.org/wiki/Extensions/SearchEpisodeOnStartup'
__category__ = 'interface'
__only_for__ = 'gtk'


class gPodderExtension:
    def __init__(self, container):
        self.container = container
        self.config = self.container.config
        self.gpodder = None

    def on_ui_object_available(self, name, ui_object):
        if name == 'gpodder-gtk':
            self.gpodder = ui_object

    def on_ui_initialized(self, model, update_podcast_callback,
            download_episode_callback):
        self.gpodder.update_feed_cache()

########NEW FILE########
__FILENAME__ = video_converter
# -*- coding: utf-8 -*-
# Convertes video files to avi or mp4
# This requires ffmpeg to be installed. Also works as a context
# menu item for already-downloaded files.
#
# (c) 2011-08-05 Thomas Perl <thp.io/about>
# Released under the same license terms as gPodder itself.

import os
import subprocess

import gpodder

from gpodder import util
from gpodder import youtube

import logging
logger = logging.getLogger(__name__)

_ = gpodder.gettext

__title__ = _('Convert video files')
__description__ = _('Transcode video files to avi/mp4/m4v')
__authors__ = 'Thomas Perl <thp@gpodder.org>, Bernd Schlapsi <brot@gmx.info>'
__doc__ = 'http://wiki.gpodder.org/wiki/Extensions/VideoConverter'
__payment__ = 'https://flattr.com/submit/auto?user_id=BerndSch&url=http://wiki.gpodder.org/wiki/Extensions/VideoConverter'
__category__ = 'post-download'

DefaultConfig = {
    'output_format': 'mp4', # At the moment we support/test only mp4, m4v and avi
    'context_menu': True, # Show the conversion option in the context menu
}


class gPodderExtension:
    MIME_TYPES = ('video/mp4', 'video/m4v', 'video/x-flv', )
    EXT = ('.mp4', '.m4v', '.flv', )
    CMD = {'avconv': ['-i', '%(old_file)s', '-codec', 'copy', '%(new_file)s'],
           'ffmpeg': ['-i', '%(old_file)s', '-codec', 'copy', '%(new_file)s']
          }

    def __init__(self, container):
        self.container = container
        self.config = self.container.config

        # Dependency checks
        self.command = self.container.require_any_command(['avconv', 'ffmpeg'])

        # extract command without extension (.exe on Windows) from command-string
        command_without_ext = os.path.basename(os.path.splitext(self.command)[0])
        self.command_param = self.CMD[command_without_ext]

    def on_episode_downloaded(self, episode):
        self._convert_episode(episode)
        
    def _get_new_extension(self):
        ext = self.config.output_format
        if not ext.startswith('.'):
            ext = '.' + ext

        return ext

    def _check_source(self, episode):
        if episode.extension() == self._get_new_extension():
            return False
        
        if episode.mime_type in self.MIME_TYPES:
            return True

        # Also check file extension (bug 1770)
        if episode.extension() in self.EXT:
            return True
            
        return False

    def on_episodes_context_menu(self, episodes):
        if not self.config.context_menu:
            return None

        if not all(e.was_downloaded(and_exists=True) for e in episodes):
            return None

        if not any(self._check_source(episode) for episode in episodes):
            return None

        menu_item = _('Convert to %(format)s') % {'format': self.config.output_format}

        return [(menu_item, self._convert_episodes)]

    def _convert_episode(self, episode):
        if not self._check_source(episode):
            return

        new_extension = self._get_new_extension()
        old_filename = episode.local_filename(create=False)
        filename, old_extension = os.path.splitext(old_filename)
        new_filename = filename + new_extension
        
        cmd = [self.command] + \
            [param % {'old_file': old_filename, 'new_file': new_filename}
                for param in self.command_param]
        ffmpeg = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                stderr=subprocess.PIPE)
        stdout, stderr = ffmpeg.communicate()

        if ffmpeg.returncode == 0:            
            util.rename_episode_file(episode, new_filename)
            os.remove(old_filename)
            
            logger.info('Converted video file to %(format)s.' % {'format': self.config.output_format})
            gpodder.user_extensions.on_notification_show(_('File converted'), episode.title)
        else:
            logger.warn('Error converting video file: %s / %s', stdout, stderr)
            gpodder.user_extensions.on_notification_show(_('Conversion failed'), episode.title)

    def _convert_episodes(self, episodes):
        for episode in episodes:
            self._convert_episode(episode)


########NEW FILE########
__FILENAME__ = common
# -*- coding: utf-8 -*-
#
# gPodder - A media aggregator and podcast client
# Copyright (c) 2005-2014 Thomas Perl and the gPodder Team
#
# gPodder is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# gPodder is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#

# gpodder.common - Common helper functions for all UIs
# Thomas Perl <thp@gpodder.org>; 2012-08-16


import gpodder

from gpodder import util

import glob
import os

import logging
logger = logging.getLogger(__name__)


def clean_up_downloads(delete_partial=False):
    """Clean up temporary files left behind by old gPodder versions

    delete_partial - If True, also delete in-progress downloads
    """
    temporary_files = glob.glob('%s/*/.tmp-*' % gpodder.downloads)

    if delete_partial:
        temporary_files += glob.glob('%s/*/*.partial' % gpodder.downloads)

    for tempfile in temporary_files:
        util.delete_file(tempfile)


def find_partial_downloads(channels, start_progress_callback, progress_callback, finish_progress_callback):
    """Find partial downloads and match them with episodes

    channels - A list of all model.PodcastChannel objects
    start_progress_callback - A callback(count) when partial files are searched
    progress_callback - A callback(title, progress) when an episode was found
    finish_progress_callback - A callback(resumable_episodes) when finished
    """
    # Look for partial file downloads
    partial_files = glob.glob(os.path.join(gpodder.downloads, '*', '*.partial'))
    count = len(partial_files)
    resumable_episodes = []
    if count:
        start_progress_callback(count)
        candidates = [f[:-len('.partial')] for f in partial_files]
        found = 0

        for channel in channels:
            for episode in channel.get_all_episodes():
                filename = episode.local_filename(create=False, check_only=True)
                if filename in candidates:
                    found += 1
                    progress_callback(episode.title, float(found)/count)
                    candidates.remove(filename)
                    partial_files.remove(filename+'.partial')

                    if os.path.exists(filename):
                        # The file has already been downloaded;
                        # remove the leftover partial file
                        util.delete_file(filename+'.partial')
                    else:
                        resumable_episodes.append(episode)

                if not candidates:
                    break

            if not candidates:
                break

        for f in partial_files:
            logger.warn('Partial file without episode: %s', f)
            util.delete_file(f)

        finish_progress_callback(resumable_episodes)
    else:
        clean_up_downloads(True)

def get_expired_episodes(channels, config):
    for channel in channels:
        for index, episode in enumerate(channel.get_episodes(gpodder.STATE_DOWNLOADED)):
            # Never consider archived episodes as old
            if episode.archive:
                continue

            # Download strategy "Only keep latest"
            if (channel.download_strategy == channel.STRATEGY_LATEST and
                    index > 0):
                logger.info('Removing episode (only keep latest strategy): %s',
                        episode.title)
                yield episode
                continue

            # Only expire episodes if the age in days is positive
            if config.episode_old_age < 1:
                continue

            # Never consider fresh episodes as old
            if episode.age_in_days() < config.episode_old_age:
                continue

            # Do not delete played episodes (except if configured)
            if not episode.is_new:
                if not config.auto_remove_played_episodes:
                    continue

            # Do not delete unfinished episodes (except if configured)
            if not episode.is_finished():
                if not config.auto_remove_unfinished_episodes:
                    continue

            # Do not delete unplayed episodes (except if configured)
            if episode.is_new:
                if not config.auto_remove_unplayed_episodes:
                    continue

            yield episode


########NEW FILE########
__FILENAME__ = config
# -*- coding: utf-8 -*-
#
# gPodder - A media aggregator and podcast client
# Copyright (c) 2005-2014 Thomas Perl and the gPodder Team
#
# gPodder is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# gPodder is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#


#
#  config.py -- gPodder Configuration Manager
#  Thomas Perl <thp@perli.net>   2007-11-02
#


import gpodder
from gpodder import util
from gpodder import jsonconfig

import atexit
import os
import shutil
import time
import logging

_ = gpodder.gettext

defaults = {
    # External applications used for playback
    'player': {
        'audio': 'default',
        'video': 'default',
    },

    # gpodder.net settings
    'mygpo': {
        'enabled': False,
        'server': 'gpodder.net',
        'username': '',
        'password': '',
        'device': {
            'uid': util.get_hostname(),
            'type': 'desktop',
            'caption': _('gPodder on %s') % util.get_hostname(),
        },
    },

    # Various limits (downloading, updating, etc..)
    'limit': {
        'bandwidth': {
            'enabled': False,
            'kbps': 500.0, # maximum kB/s per download
        },
        'downloads': {
            'enabled': True,
            'concurrent': 1,
        },
        'episodes': 200, # max episodes per feed
    },

    # Behavior of downloads
    'downloads': {
        'chronological_order': True, # download older episodes first
    },

    # Automatic feed updates, download removal and retry on download timeout
    'auto': {
        'update': {
            'enabled': False,
            'frequency': 20, # minutes
        },

        'cleanup': {
            'days': 7,
            'played': False,
            'unplayed': False,
            'unfinished': True,
        },

        'retries': 3, # number of retries when downloads time out
    },

    # Software updates from gpodder.org (primary audience: Windows users)
    'software_update': {
        'check_on_startup': gpodder.ui.win32, # check for updates on start
        'last_check': 0, # unix timestamp of last update check
        'interval': 5, # interval (in days) to check for updates
    },

    'ui': {
        # Settings for the Command-Line Interface
        'cli': {
            'colors': True,
        },

        # Settings for the QML UI (MeeGo Harmattan / N9)
        'qml': {
            'state': {
                'episode_list_filter': 0,
            },

            'autorotate': False,
        },

        # Settings for the Gtk UI
        'gtk': {
            'state': {
                'main_window': {
                    'width': 700,
                    'height': 500,
                    'x': -1, 'y': -1, 'maximized': False,

                    'paned_position': 200,
                    'episode_list_size': 200,
                },
                'episode_selector': {
                    'width': 600,
                    'height': 400,
                    'x': -1, 'y': -1, 'maximized': False,
                },
                'episode_window': {
                    'width': 500,
                    'height': 400,
                    'x': -1, 'y': -1, 'maximized': False,
                },
            },

            'toolbar': False,
            'html_shownotes': True,
            'new_episodes': 'show', # ignore, show, queue, download
            'live_search_delay': 200,

            'podcast_list': {
                'all_episodes': True,
                'sections': True,
                'view_mode': 1,
                'hide_empty': False,
            },

            'episode_list': {
                'descriptions': True,
                'view_mode': 1,
                'columns': int('110', 2), # bitfield of visible columns
            },

            'download_list': {
                'remove_finished': True,
            },
        },
    },

    # Synchronization with portable devices (MP3 players, etc..)
    'device_sync': {
        'device_type': 'none', # Possible values: 'none', 'filesystem', 'ipod'
        'device_folder': '/media',        

        'one_folder_per_podcast': True,
        'skip_played_episodes': True,
        'delete_played_episodes': False,

        'max_filename_length': 999,

        'custom_sync_name': '{episode.sortdate}_{episode.title}',
        'custom_sync_name_enabled': False,

        'after_sync': {
            'mark_episodes_played': False,
            'delete_episodes': False,
            'sync_disks': False,
        },
        'playlists': {
            'create': True,
            'two_way_sync': False,
            'use_absolute_path': True,
            'folder': 'Playlists',
        }

    },

    'youtube': {
        'preferred_fmt_id': 18, # default fmt_id (see fallbacks in youtube.py)
        'preferred_fmt_ids': [], # for advanced uses (custom fallback sequence)
    },

    'extensions': {
        'enabled': [],
    },

    'flattr': {
        'token': '',
        'flattr_on_play': False,
    },
}

# The sooner this goes away, the better
gPodderSettings_LegacySupport = {
    'player': 'player.audio',
    'videoplayer': 'player.video',
    'limit_rate': 'limit.bandwidth.enabled',
    'limit_rate_value': 'limit.bandwidth.kbps',
    'max_downloads_enabled': 'limit.downloads.enabled',
    'max_downloads': 'limit.downloads.concurrent',
    'episode_old_age': 'auto.cleanup.days',
    'auto_remove_played_episodes': 'auto.cleanup.played',
    'auto_remove_unfinished_episodes': 'auto.cleanup.unfinished',
    'auto_remove_unplayed_episodes': 'auto.cleanup.unplayed',
    'max_episodes_per_feed': 'limit.episodes',
    'show_toolbar': 'ui.gtk.toolbar',
    'episode_list_descriptions': 'ui.gtk.episode_list.descriptions',
    'podcast_list_view_all': 'ui.gtk.podcast_list.all_episodes',
    'podcast_list_sections': 'ui.gtk.podcast_list.sections',
    'enable_html_shownotes': 'ui.gtk.html_shownotes',
    'episode_list_view_mode': 'ui.gtk.episode_list.view_mode',
    'podcast_list_view_mode': 'ui.gtk.podcast_list.view_mode',
    'podcast_list_hide_boring': 'ui.gtk.podcast_list.hide_empty',
    'episode_list_columns': 'ui.gtk.episode_list.columns',
    'auto_cleanup_downloads': 'ui.gtk.download_list.remove_finished',
    'auto_update_feeds': 'auto.update.enabled',
    'auto_update_frequency': 'auto.update.frequency',
    'auto_download': 'ui.gtk.new_episodes',
}

logger = logging.getLogger(__name__)


def config_value_to_string(config_value):
    config_type = type(config_value)

    if config_type == list:
        return ','.join(map(config_value_to_string, config_value))
    elif config_type in (str, unicode):
        return config_value
    else:
        return str(config_value)

def string_to_config_value(new_value, old_value):
    config_type = type(old_value)

    if config_type == list:
        return filter(None, [x.strip() for x in new_value.split(',')])
    elif config_type == bool:
        return (new_value.strip().lower() in ('1', 'true'))
    else:
        return config_type(new_value)


class Config(object):
    # Number of seconds after which settings are auto-saved
    WRITE_TO_DISK_TIMEOUT = 60

    def __init__(self, filename='gpodder.json'):
        self.__json_config = jsonconfig.JsonConfig(default=defaults,
                on_key_changed=self._on_key_changed)
        self.__save_thread = None
        self.__filename = filename
        self.__observers = []

        self.load()

        # If there is no configuration file, we create one here (bug 1511)
        if not os.path.exists(self.__filename):
            self.save()

        atexit.register(self.__atexit)

    def register_defaults(self, defaults):
        """
        Register default configuration options (e.g. for extensions)

        This function takes a dictionary that will be merged into the
        current configuration if the keys don't yet exist. This can
        be used to add a default configuration for extension modules.
        """
        self.__json_config._merge_keys(defaults)

    def add_observer(self, callback):
        """
        Add a callback function as observer. This callback
        will be called when a setting changes. It should
        have this signature:

            observer(name, old_value, new_value)

        The "name" is the setting name, the "old_value" is
        the value that has been overwritten with "new_value".
        """
        if callback not in self.__observers:
            self.__observers.append(callback)
        else:
            logger.warn('Observer already added: %s', repr(callback))

    def remove_observer(self, callback):
        """
        Remove an observer previously added to this object.
        """
        if callback in self.__observers:
            self.__observers.remove(callback)
        else:
            logger.warn('Observer not added: %s', repr(callback))

    def all_keys(self):
        return self.__json_config._keys_iter()

    def schedule_save(self):
        if self.__save_thread is None:
            self.__save_thread = util.run_in_background(self.save_thread_proc, True)

    def save_thread_proc(self):
        time.sleep(self.WRITE_TO_DISK_TIMEOUT)
        if self.__save_thread is not None:
            self.save()

    def __atexit(self):
        if self.__save_thread is not None:
            self.save()

    def save(self, filename=None):
        if filename is None:
            filename = self.__filename

        logger.info('Flushing settings to disk')

        try:
            fp = open(filename+'.tmp', 'wt')
            fp.write(repr(self.__json_config))
            fp.close()
            util.atomic_rename(filename+'.tmp', filename)
        except:
            logger.error('Cannot write settings to %s', filename)
            util.delete_file(filename+'.tmp')
            raise

        self.__save_thread = None

    def load(self, filename=None):
        if filename is not None:
            self.__filename = filename

        if os.path.exists(self.__filename):
            try:
                data = open(self.__filename, 'rt').read()
                new_keys_added = self.__json_config._restore(data)
            except:
                logger.warn('Cannot parse config file: %s',
                        self.__filename, exc_info=True)
                new_keys_added = False

            if new_keys_added:
                logger.info('New default keys added - saving config.')
                self.save()

    def toggle_flag(self, name):
        setattr(self, name, not getattr(self, name))

    def update_field(self, name, new_value):
        """Update a config field, converting strings to the right types"""
        old_value = self._lookup(name)
        new_value = string_to_config_value(new_value, old_value)
        setattr(self, name, new_value)
        return True

    def _on_key_changed(self, name, old_value, value):
        if 'ui.gtk.state' not in name:
            # Only log non-UI state changes
            logger.debug('%s: %s -> %s', name, old_value, value)
        for observer in self.__observers:
            try:
                observer(name, old_value, value)
            except Exception, exception:
                logger.error('Error while calling observer %r: %s',
                        observer, exception, exc_info=True)

        self.schedule_save()

    def __getattr__(self, name):
        if name in gPodderSettings_LegacySupport:
            name = gPodderSettings_LegacySupport[name]

        return getattr(self.__json_config, name)

    def __setattr__(self, name, value):
        if name.startswith('_'):
            object.__setattr__(self, name, value)
            return

        if name in gPodderSettings_LegacySupport:
            name = gPodderSettings_LegacySupport[name]

        setattr(self.__json_config, name, value)


########NEW FILE########
__FILENAME__ = core
# -*- coding: utf-8 -*-
#
# gPodder - A media aggregator and podcast client
# Copyright (c) 2005-2014 Thomas Perl and the gPodder Team
#
# gPodder is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# gPodder is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#

# gpodder.core - Common functionality used by all UIs
# Thomas Perl <thp@gpodder.org>; 2011-02-06


import gpodder

from gpodder import util
from gpodder import config
from gpodder import dbsqlite
from gpodder import extensions
from gpodder import model
from gpodder import flattr


class Core(object):
    def __init__(self,
                 config_class=config.Config,
                 database_class=dbsqlite.Database,
                 model_class=model.Model):
        # Initialize the gPodder home directory
        util.make_directory(gpodder.home)

        # Open the database and configuration file
        self.db = database_class(gpodder.database_file)
        self.model = model_class(self.db)
        self.config = config_class(gpodder.config_file)

        # Load extension modules and install the extension manager
        gpodder.user_extensions = extensions.ExtensionManager(self)

        # Load installed/configured plugins
        gpodder.load_plugins()

        # Update the current device in the configuration
        self.config.mygpo.device.type = util.detect_device_type()

        # Initialize Flattr integration
        self.flattr = flattr.Flattr(self.config.flattr)

    def shutdown(self):
        # Notify all extensions that we are being shut down
        gpodder.user_extensions.shutdown()

        # Close the database and store outstanding changes
        self.db.close()


########NEW FILE########
__FILENAME__ = coverart
# -*- coding: utf-8 -*-
#
# gPodder - A media aggregator and podcast client
# Copyright (c) 2005-2014 Thomas Perl and the gPodder Team
#
# gPodder is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# gPodder is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#


#
#  gpodder.coverart - Unified cover art downloading module (2012-03-04)
#


import gpodder
_ = gpodder.gettext

import logging
logger = logging.getLogger(__name__)

from gpodder import util
from gpodder import youtube

import os

class CoverDownloader(object):
    # File name extension dict, lists supported cover art extensions
    # Values: functions that check if some data is of that file type
    SUPPORTED_EXTENSIONS = {
        '.png': lambda d: d.startswith('\x89PNG\r\n\x1a\n\x00'),
        '.jpg': lambda d: d.startswith('\xff\xd8'),
        '.gif': lambda d: d.startswith('GIF89a') or d.startswith('GIF87a'),
    }

    EXTENSIONS = SUPPORTED_EXTENSIONS.keys()
    ALL_EPISODES_ID = ':gpodder:all-episodes:'

    # Low timeout to avoid unnecessary hangs of GUIs
    TIMEOUT = 5

    def __init__(self):
        pass

    def get_cover_all_episodes(self):
        return self._default_filename('podcast-all.png')

    def get_cover(self, filename, cover_url, feed_url, title,
            username=None, password=None, download=False):
        # Detection of "all episodes" podcast
        if filename == self.ALL_EPISODES_ID:
            return self.get_cover_all_episodes()

        # Return already existing files
        for extension in self.EXTENSIONS:
            if os.path.exists(filename + extension):
                return filename + extension

        # If allowed to download files, do so here
        if download:
            # YouTube-specific cover art image resolver
            youtube_cover_url = youtube.get_real_cover(feed_url)
            if youtube_cover_url is not None:
                cover_url = youtube_cover_url

            if not cover_url:
                return self._fallback_filename(title)

            # We have to add username/password, because password-protected
            # feeds might keep their cover art also protected (bug 1521)
            if username is not None and password is not None:
                cover_url = util.url_add_authentication(cover_url,
                        username, password)

            try:
                logger.info('Downloading cover art: %s', cover_url)
                data = util.urlopen(cover_url, timeout=self.TIMEOUT).read()
            except Exception, e:
                logger.warn('Cover art download failed: %s', e)
                return self._fallback_filename(title)

            try:
                extension = None

                for filetype, check in self.SUPPORTED_EXTENSIONS.items():
                    if check(data):
                        extension = filetype
                        break

                if extension is None:
                    msg = 'Unknown file type: %s (%r)' % (cover_url, data[:6])
                    raise ValueError(msg)

                # Successfully downloaded the cover art - save it!
                fp = open(filename + extension, 'wb')
                fp.write(data)
                fp.close()

                return filename + extension
            except Exception, e:
                logger.warn('Cannot save cover art', exc_info=True)

        # Fallback to cover art based on the podcast title
        return self._fallback_filename(title)

    def _default_filename(self, basename):
        return os.path.join(gpodder.images_folder, basename)

    def _fallback_filename(self, title):
        return self._default_filename('podcast-%d.png' % (hash(title)%5))


########NEW FILE########
__FILENAME__ = dbsqlite
# -*- coding: utf-8 -*-
#
# gPodder - A media aggregator and podcast client
# Copyright (c) 2005-2014 Thomas Perl and the gPodder Team
#
# gPodder is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# gPodder is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#

#
# dbsqlite.py -- SQLite persistence layer for gPodder
#
# 2008-06-13 Justin Forest <justin.forest@gmail.com>
# 2010-04-24 Thomas Perl <thp@gpodder.org>
#

from __future__ import with_statement

import gpodder
_ = gpodder.gettext

import sys

from sqlite3 import dbapi2 as sqlite

import logging
logger = logging.getLogger(__name__)

from gpodder import schema
from gpodder import util

import threading
import re

class Database(object):
    TABLE_PODCAST = 'podcast'
    TABLE_EPISODE = 'episode'

    def __init__(self, filename):
        self.database_file = filename
        self._db = None
        self.lock = threading.RLock()

    def close(self):
        self.commit()

        with self.lock:
            cur = self.cursor()
            cur.execute("VACUUM")
            cur.close()

        self._db.close()
        self._db = None

    def purge(self, max_episodes, podcast_id):
        """
        Deletes old episodes.  Should be called
        before adding new episodes to a podcast.
        """
        if max_episodes == 0:
            return

        with self.lock:
            cur = self.cursor()

            logger.debug('Purge requested for podcast %d', podcast_id)
            sql = """
                DELETE FROM %s
                WHERE podcast_id = ?
                AND state <> ?
                AND id NOT IN
                (SELECT id FROM %s WHERE podcast_id = ?
                ORDER BY published DESC LIMIT ?)""" % (self.TABLE_EPISODE, self.TABLE_EPISODE)
            cur.execute(sql, (podcast_id, gpodder.STATE_DOWNLOADED, podcast_id, max_episodes))

            cur.close()

    @property
    def db(self):
        if self._db is None:
            self._db = sqlite.connect(self.database_file, check_same_thread=False)

            # Check schema version, upgrade if necessary
            schema.upgrade(self._db, self.database_file)

            # Sanity checks for the data in the database
            schema.check_data(self)

            logger.debug('Database opened.')
        return self._db

    def cursor(self):
        return self.db.cursor()

    def commit(self):
        with self.lock:
            try:
                logger.debug('Commit.')
                self.db.commit()
            except Exception, e:
                logger.error('Cannot commit: %s', e, exc_info=True)

    def get_content_types(self, id):
        """Given a podcast ID, returns the content types"""
        with self.lock:
            cur = self.cursor()
            cur.execute('SELECT mime_type FROM %s WHERE podcast_id = ?' % self.TABLE_EPISODE, (id,))
            for (mime_type,) in cur:
                yield mime_type
            cur.close()

    def get_podcast_statistics(self, podcast_id=None):
        """Given a podcast ID, returns the statistics for it

        If the podcast_id is omitted (using the default value), the
        statistics will be calculated over all podcasts.

        Returns a tuple (total, deleted, new, downloaded, unplayed)
        """
        total, deleted, new, downloaded, unplayed = 0, 0, 0, 0, 0

        with self.lock:
            cur = self.cursor()
            if podcast_id is not None:
                cur.execute('SELECT COUNT(*), state, is_new FROM %s WHERE podcast_id = ? GROUP BY state, is_new' % self.TABLE_EPISODE, (podcast_id,))
            else:
                cur.execute('SELECT COUNT(*), state, is_new FROM %s GROUP BY state, is_new' % self.TABLE_EPISODE)
            for count, state, is_new in cur:
                total += count
                if state == gpodder.STATE_DELETED:
                    deleted += count
                elif state == gpodder.STATE_NORMAL and is_new:
                    new += count
                elif state == gpodder.STATE_DOWNLOADED:
                    downloaded += count
                    if is_new:
                        unplayed += count

            cur.close()

        return (total, deleted, new, downloaded, unplayed)

    def load_podcasts(self, factory):
        logger.info('Loading podcasts')

        sql = 'SELECT * FROM %s' % self.TABLE_PODCAST

        with self.lock:
            cur = self.cursor()
            cur.execute(sql)

            keys = [desc[0] for desc in cur.description]
            result = map(lambda row: factory(dict(zip(keys, row)), self), cur)
            cur.close()

        return result

    def load_episodes(self, podcast, factory):
        assert podcast.id

        logger.info('Loading episodes for podcast %d', podcast.id)

        sql = 'SELECT * FROM %s WHERE podcast_id = ? ORDER BY published DESC' % self.TABLE_EPISODE
        args = (podcast.id,)

        with self.lock:
            cur = self.cursor()
            cur.execute(sql, args)

            keys = [desc[0] for desc in cur.description]
            result = map(lambda row: factory(dict(zip(keys, row))), cur)
            cur.close()

        return result

    def delete_podcast(self, podcast):
        assert podcast.id

        with self.lock:
            cur = self.cursor()
            logger.debug('delete_podcast: %d (%s)', podcast.id, podcast.url)

            cur.execute("DELETE FROM %s WHERE id = ?" % self.TABLE_PODCAST, (podcast.id, ))
            cur.execute("DELETE FROM %s WHERE podcast_id = ?" % self.TABLE_EPISODE, (podcast.id, ))

            cur.close()
            self.db.commit()

    def save_podcast(self, podcast):
        self._save_object(podcast, self.TABLE_PODCAST, schema.PodcastColumns)

    def save_episode(self, episode):
        self._save_object(episode, self.TABLE_EPISODE, schema.EpisodeColumns)

    def _save_object(self, o, table, columns):
        with self.lock:
            try:
                cur = self.cursor()
                values = [util.convert_bytes(getattr(o, name))
                        for name in columns]

                if o.id is None:
                    qmarks = ', '.join('?'*len(columns))
                    sql = 'INSERT INTO %s (%s) VALUES (%s)' % (table, ', '.join(columns), qmarks)
                    cur.execute(sql, values)
                    o.id = cur.lastrowid
                else:
                    qmarks = ', '.join('%s = ?' % name for name in columns)
                    values.append(o.id)
                    sql = 'UPDATE %s SET %s WHERE id = ?' % (table, qmarks)
                    cur.execute(sql, values)
            except Exception, e:
                logger.error('Cannot save %s: %s', o, e, exc_info=True)

            cur.close()

    def get(self, sql, params=None):
        """
        Returns the first cell of a query result, useful for COUNT()s.
        """
        with self.lock:
            cur = self.cursor()

            if params is None:
                cur.execute(sql)
            else:
                cur.execute(sql, params)

            row = cur.fetchone()
            cur.close()

        if row is None:
            return None
        else:
            return row[0]

    def podcast_download_folder_exists(self, foldername):
        """
        Returns True if a foldername for a channel exists.
        False otherwise.
        """
        foldername = util.convert_bytes(foldername)

        return self.get("SELECT id FROM %s WHERE download_folder = ?" %
                self.TABLE_PODCAST, (foldername,)) is not None

    def episode_filename_exists(self, podcast_id, filename):
        """
        Returns True if a filename for an episode exists.
        False otherwise.
        """
        filename = util.convert_bytes(filename)

        return self.get("SELECT id FROM %s WHERE podcast_id = ? AND download_filename = ?" %
                self.TABLE_EPISODE, (podcast_id, filename,)) is not None

    def get_last_published(self, podcast):
        """
        Look up the most recent publish date of a podcast.
        """
        return self.get('SELECT MAX(published) FROM %s WHERE podcast_id = ?' % self.TABLE_EPISODE, (podcast.id,))

    def delete_episode_by_guid(self, guid, podcast_id):
        """
        Deletes episodes that have a specific GUID for
        a given channel. Used after feed updates for
        episodes that have disappeared from the feed.
        """
        guid = util.convert_bytes(guid)

        with self.lock:
            cur = self.cursor()
            cur.execute('DELETE FROM %s WHERE podcast_id = ? AND guid = ?' %
                    self.TABLE_EPISODE, (podcast_id, guid))


########NEW FILE########
__FILENAME__ = dbusproxy
#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# gPodder - A media aggregator and podcast client
# Copyright (c) 2005-2014 Thomas Perl and the gPodder Team
#
# gPodder is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# gPodder is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#

# gpodder.dbusproxy - Expose Podcasts over D-Bus
# Based on a patch by Iwan van der Kleijn <iwanvanderkleyn@gmail.com>
# See also: http://gpodder.org/bug/699

import gpodder

from gpodder import util

import dbus
import dbus.service

def safe_str(txt):
    if txt:
        return txt.encode()
    else:
        return ''

def safe_first_line(txt):
    txt = safe_str(txt)
    lines = util.remove_html_tags(txt).strip().splitlines()
    if not lines or lines[0] == '':
        return ''
    else:
        return lines[0]

class DBusPodcastsProxy(dbus.service.Object):
    """ Implements API accessible through D-Bus

    Methods on DBusPodcastsProxy can be called by D-Bus clients. They implement
    safe-guards to work safely over D-Bus while having type signatures applied
    for parameter and return values.
    """

    #DBusPodcastsProxy(lambda: self.channels, self.on_itemUpdate_activate(), self.playback_episodes, self.download_episode_list, bus_name)
    def __init__(self, get_podcast_list, \
            check_for_updates, playback_episodes, \
            download_episodes, episode_from_uri, \
            bus_name):
        self._get_podcasts = get_podcast_list
        self._on_check_for_updates = check_for_updates
        self._playback_episodes = playback_episodes
        self._download_episodes = download_episodes
        self._episode_from_uri = episode_from_uri
        dbus.service.Object.__init__(self, \
                object_path=gpodder.dbus_podcasts_object_path, \
                bus_name=bus_name)

    def _get_episode_refs(self, urls):
        """Get Episode instances associated with URLs"""
        episodes = []
        for p in self._get_podcasts():
            for e in p.get_all_episodes():
                if e.url in urls:
                    episodes.append(e)
        return episodes

    @dbus.service.method(dbus_interface=gpodder.dbus_podcasts, in_signature='', out_signature='a(ssss)')
    def get_podcasts(self):
        """Get all podcasts in gPodder's subscription list"""
        def podcast_to_tuple(podcast):
            title = safe_str(podcast.title)
            url = safe_str(podcast.url)
            description = safe_first_line(podcast.description)
            cover_file = ''

            return (title, url, description, cover_file)

        return [podcast_to_tuple(p) for p in self._get_podcasts()]

    @dbus.service.method(dbus_interface=gpodder.dbus_podcasts, in_signature='s', out_signature='ss')
    def get_episode_title(self, url):
        episode = self._episode_from_uri(url)

        if episode is not None:
            return episode.title, episode.channel.title

        return ('', '')

    @dbus.service.method(dbus_interface=gpodder.dbus_podcasts, in_signature='s', out_signature='a(sssssbbb)')
    def get_episodes(self, url):
        """Return all episodes of the podcast with the given URL"""
        podcast = None
        for channel in self._get_podcasts():
            if channel.url == url:
                podcast = channel
                break

        if podcast is None:
            return []

        def episode_to_tuple(episode):
            title = safe_str(episode.title)
            url = safe_str(episode.url)
            description = safe_first_line(episode.description)
            filename = safe_str(episode.download_filename)
            file_type = safe_str(episode.file_type())
            is_new = (episode.state == gpodder.STATE_NORMAL and episode.is_new)
            is_downloaded = episode.was_downloaded(and_exists=True)
            is_deleted = (episode.state == gpodder.STATE_DELETED)

            return (title, url, description, filename, file_type, is_new, is_downloaded, is_deleted)

        return [episode_to_tuple(e) for e in podcast.get_all_episodes()]

    @dbus.service.method(dbus_interface=gpodder.dbus_podcasts, in_signature='as', out_signature='(bs)')
    def play_or_download_episode(self, urls):
        """Play (or download) a list of episodes given by URL"""
        episodes = self._get_episode_refs(urls)
        if not episodes:
            return (0, 'No episodes found')

        to_playback = [e for e in episodes if e.was_downloaded(and_exists=True)]
        to_download = [e for e in episodes if e not in to_playback]

        if to_playback:
            self._playback_episodes(to_playback)

        if to_download:
            self._download_episodes(to_download)

        return (1, 'Success')

    @dbus.service.method(dbus_interface=gpodder.dbus_podcasts, in_signature='', out_signature='')
    def check_for_updates(self):
        """Check for new episodes or offer subscriptions"""
        self._on_check_for_updates()


########NEW FILE########
__FILENAME__ = download
# -*- coding: utf-8 -*-
#
# gPodder - A media aggregator and podcast client
# Copyright (c) 2005-2014 Thomas Perl and the gPodder Team
#
# gPodder is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# gPodder is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#


#
#  download.py -- Download queue management
#  Thomas Perl <thp@perli.net>   2007-09-15
#
#  Based on libwget.py (2005-10-29)
#

from __future__ import with_statement

import logging
logger = logging.getLogger(__name__)

from gpodder import util
from gpodder import youtube
from gpodder import vimeo
import gpodder

import socket
import threading
import urllib
import urlparse
import shutil
import os.path
import os
import time
import collections

import mimetypes
import email

from email.header import decode_header


_ = gpodder.gettext

def get_header_param(headers, param, header_name):
    """Extract a HTTP header parameter from a dict

    Uses the "email" module to retrieve parameters
    from HTTP headers. This can be used to get the
    "filename" parameter of the "content-disposition"
    header for downloads to pick a good filename.

    Returns None if the filename cannot be retrieved.
    """
    value = None
    try:
        headers_string = ['%s:%s'%(k,v) for k,v in headers.items()]
        msg = email.message_from_string('\n'.join(headers_string))
        if header_name in msg:
            raw_value = msg.get_param(param, header=header_name)
            if raw_value is not None:
                value = email.utils.collapse_rfc2231_value(raw_value)
    except Exception, e:
        logger.error('Cannot get %s from %s', param, header_name, exc_info=True)

    return value

class ContentRange(object):
    # Based on:
    # http://svn.pythonpaste.org/Paste/WebOb/trunk/webob/byterange.py
    #
    # Copyright (c) 2007 Ian Bicking and Contributors
    #
    # Permission is hereby granted, free of charge, to any person obtaining
    # a copy of this software and associated documentation files (the
    # "Software"), to deal in the Software without restriction, including
    # without limitation the rights to use, copy, modify, merge, publish,
    # distribute, sublicense, and/or sell copies of the Software, and to
    # permit persons to whom the Software is furnished to do so, subject to
    # the following conditions:
    #
    # The above copyright notice and this permission notice shall be
    # included in all copies or substantial portions of the Software.
    #
    # THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
    # EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
    # MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
    # NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE
    # LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
    # OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION
    # WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
    """
    Represents the Content-Range header

    This header is ``start-stop/length``, where stop and length can be
    ``*`` (represented as None in the attributes).
    """

    def __init__(self, start, stop, length):
        assert start >= 0, "Bad start: %r" % start
        assert stop is None or (stop >= 0 and stop >= start), (
            "Bad stop: %r" % stop)
        self.start = start
        self.stop = stop
        self.length = length

    def __repr__(self):
        return '<%s %s>' % (
            self.__class__.__name__,
            self)

    def __str__(self):
        if self.stop is None:
            stop = '*'
        else:
            stop = self.stop + 1
        if self.length is None:
            length = '*'
        else:
            length = self.length
        return 'bytes %s-%s/%s' % (self.start, stop, length)

    def __iter__(self):
        """
        Mostly so you can unpack this, like:

            start, stop, length = res.content_range
        """
        return iter([self.start, self.stop, self.length])

    @classmethod
    def parse(cls, value):
        """
        Parse the header.  May return None if it cannot parse.
        """
        if value is None:
            return None
        value = value.strip()
        if not value.startswith('bytes '):
            # Unparseable
            return None
        value = value[len('bytes '):].strip()
        if '/' not in value:
            # Invalid, no length given
            return None
        range, length = value.split('/', 1)
        if '-' not in range:
            # Invalid, no range
            return None
        start, end = range.split('-', 1)
        try:
            start = int(start)
            if end == '*':
                end = None
            else:
                end = int(end)
            if length == '*':
                length = None
            else:
                length = int(length)
        except ValueError:
            # Parse problem
            return None
        if end is None:
            return cls(start, None, length)
        else:
            return cls(start, end-1, length)


class DownloadCancelledException(Exception): pass
class AuthenticationError(Exception): pass

class gPodderDownloadHTTPError(Exception):
    def __init__(self, url, error_code, error_message):
        self.url = url
        self.error_code = error_code
        self.error_message = error_message

class DownloadURLOpener(urllib.FancyURLopener):
    version = gpodder.user_agent

    # Sometimes URLs are not escaped correctly - try to fix them
    # (see RFC2396; Section 2.4.3. Excluded US-ASCII Characters)
    # FYI: The omission of "%" in the list is to avoid double escaping!
    ESCAPE_CHARS = dict((ord(c), u'%%%x'%ord(c)) for c in u' <>#"{}|\\^[]`')

    def __init__( self, channel):
        self.channel = channel
        self._auth_retry_counter = 0
        urllib.FancyURLopener.__init__(self, None)

    def http_error_default(self, url, fp, errcode, errmsg, headers):
        """
        FancyURLopener by default does not raise an exception when
        there is some unknown HTTP error code. We want to override
        this and provide a function to log the error and raise an
        exception, so we don't download the HTTP error page here.
        """
        # The following two lines are copied from urllib.URLopener's
        # implementation of http_error_default
        void = fp.read()
        fp.close()
        raise gPodderDownloadHTTPError(url, errcode, errmsg)
    
    def redirect_internal(self, url, fp, errcode, errmsg, headers, data):
        """ This is the exact same function that's included with urllib
            except with "void = fp.read()" commented out. """
        
        if 'location' in headers:
            newurl = headers['location']
        elif 'uri' in headers:
            newurl = headers['uri']
        else:
            return
        
        # This blocks forever(?) with certain servers (see bug #465)
        #void = fp.read()
        fp.close()
        
        # In case the server sent a relative URL, join with original:
        newurl = urlparse.urljoin(self.type + ":" + url, newurl)
        return self.open(newurl)
    
# The following is based on Python's urllib.py "URLopener.retrieve"
# Also based on http://mail.python.org/pipermail/python-list/2001-October/110069.html

    def http_error_206(self, url, fp, errcode, errmsg, headers, data=None):
        # The next line is taken from urllib's URLopener.open_http
        # method, at the end after the line "if errcode == 200:"
        return urllib.addinfourl(fp, headers, 'http:' + url)

    def retrieve_resume(self, url, filename, reporthook=None, data=None):
        """Download files from an URL; return (headers, real_url)

        Resumes a download if the local filename exists and
        the server supports download resuming.
        """

        current_size = 0
        tfp = None
        if os.path.exists(filename):
            try:
                current_size = os.path.getsize(filename)
                tfp = open(filename, 'ab')
                #If the file exists, then only download the remainder
                if current_size > 0:
                    self.addheader('Range', 'bytes=%s-' % (current_size))
            except:
                logger.warn('Cannot resume download: %s', filename, exc_info=True)
                tfp = None
                current_size = 0

        if tfp is None:
            tfp = open(filename, 'wb')

        # Fix a problem with bad URLs that are not encoded correctly (bug 549)
        url = url.decode('ascii', 'ignore')
        url = url.translate(self.ESCAPE_CHARS)
        url = url.encode('ascii')

        url = urllib.unwrap(urllib.toBytes(url))
        fp = self.open(url, data)
        headers = fp.info()

        if current_size > 0:
            # We told the server to resume - see if she agrees
            # See RFC2616 (206 Partial Content + Section 14.16)
            # XXX check status code here, too...
            range = ContentRange.parse(headers.get('content-range', ''))
            if range is None or range.start != current_size:
                # Ok, that did not work. Reset the download
                # TODO: seek and truncate if content-range differs from request
                tfp.close()
                tfp = open(filename, 'wb')
                current_size = 0
                logger.warn('Cannot resume: Invalid Content-Range (RFC2616).')

        result = headers, fp.geturl()
        bs = 1024*8
        size = -1
        read = current_size
        blocknum = int(current_size/bs)
        if reporthook:
            if "content-length" in headers:
                size = int(headers.getrawheader("Content-Length"))  + current_size
            reporthook(blocknum, bs, size)
        while read < size or size == -1:
            if size == -1:
                block = fp.read(bs)
            else:
                block = fp.read(min(size-read, bs))
            if block == "":
                break
            read += len(block)
            tfp.write(block)
            blocknum += 1
            if reporthook:
                reporthook(blocknum, bs, size)
        fp.close()
        tfp.close()
        del fp
        del tfp

        # raise exception if actual size does not match content-length header
        if size >= 0 and read < size:
            raise urllib.ContentTooShortError("retrieval incomplete: got only %i out "
                                       "of %i bytes" % (read, size), result)

        return result

# end code based on urllib.py

    def prompt_user_passwd( self, host, realm):
        # Keep track of authentication attempts, fail after the third one
        self._auth_retry_counter += 1
        if self._auth_retry_counter > 3:
            raise AuthenticationError(_('Wrong username/password'))

        if self.channel.auth_username or self.channel.auth_password:
            logger.debug('Authenticating as "%s" to "%s" for realm "%s".',
                    self.channel.auth_username, host, realm)
            return ( self.channel.auth_username, self.channel.auth_password )

        return (None, None)


class DownloadQueueWorker(object):
    def __init__(self, queue, exit_callback, continue_check_callback, minimum_tasks):
        self.queue = queue
        self.exit_callback = exit_callback
        self.continue_check_callback = continue_check_callback

        # The minimum amount of tasks that should be downloaded by this worker
        # before using the continue_check_callback to determine if it might
        # continue accepting tasks. This can be used to forcefully start a
        # download, even if a download limit is in effect.
        self.minimum_tasks = minimum_tasks

    def __repr__(self):
        return threading.current_thread().getName()

    def run(self):
        logger.info('Starting new thread: %s', self)
        while True:
            # Check if this thread is allowed to continue accepting tasks
            # (But only after reducing minimum_tasks to zero - see above)
            if self.minimum_tasks > 0:
                self.minimum_tasks -= 1
            elif not self.continue_check_callback(self):
                return

            try:
                task = self.queue.pop()
                logger.info('%s is processing: %s', self, task)
                task.run()
                task.recycle()
            except IndexError, e:
                logger.info('No more tasks for %s to carry out.', self)
                break
        self.exit_callback(self)


class DownloadQueueManager(object):
    def __init__(self, config):
        self._config = config
        self.tasks = collections.deque()

        self.worker_threads_access = threading.RLock()
        self.worker_threads = []

    def __exit_callback(self, worker_thread):
        with self.worker_threads_access:
            self.worker_threads.remove(worker_thread)

    def __continue_check_callback(self, worker_thread):
        with self.worker_threads_access:
            if len(self.worker_threads) > self._config.max_downloads and \
                    self._config.max_downloads_enabled:
                self.worker_threads.remove(worker_thread)
                return False
            else:
                return True

    def spawn_threads(self, force_start=False):
        """Spawn new worker threads if necessary

        If force_start is True, forcefully spawn a thread and
        let it process at least one episodes, even if a download
        limit is in effect at the moment.
        """
        with self.worker_threads_access:
            if not len(self.tasks):
                return

            if force_start or len(self.worker_threads) == 0 or \
                    len(self.worker_threads) < self._config.max_downloads or \
                    not self._config.max_downloads_enabled:
                # We have to create a new thread here, there's work to do
                logger.info('Starting new worker thread.')

                # The new worker should process at least one task (the one
                # that we want to forcefully start) if force_start is True.
                if force_start:
                    minimum_tasks = 1
                else:
                    minimum_tasks = 0

                worker = DownloadQueueWorker(self.tasks, self.__exit_callback,
                        self.__continue_check_callback, minimum_tasks)
                self.worker_threads.append(worker)
                util.run_in_background(worker.run)

    def are_queued_or_active_tasks(self):
        with self.worker_threads_access:
            return len(self.worker_threads) > 0

    def add_task(self, task, force_start=False):
        """Add a new task to the download queue

        If force_start is True, ignore the download limit
        and forcefully start the download right away.
        """
        if task.status != DownloadTask.INIT:
            # Remove the task from its current position in the
            # download queue (if any) to avoid race conditions
            # where two worker threads download the same file
            try:
                self.tasks.remove(task)
            except ValueError, e:
                pass
        task.status = DownloadTask.QUEUED
        if force_start:
            # Add the task to be taken on next pop
            self.tasks.append(task)
        else:
            # Add the task to the end of the queue
            self.tasks.appendleft(task)
        self.spawn_threads(force_start)


class DownloadTask(object):
    """An object representing the download task of an episode

    You can create a new download task like this:

        task = DownloadTask(episode, gpodder.config.Config(CONFIGFILE))
        task.status = DownloadTask.QUEUED
        task.run()

    While the download is in progress, you can access its properties:

        task.total_size       # in bytes
        task.progress         # from 0.0 to 1.0
        task.speed            # in bytes per second
        str(task)             # name of the episode
        task.status           # current status
        task.status_changed   # True if the status has been changed (see below)
        task.url              # URL of the episode being downloaded
        task.podcast_url      # URL of the podcast this download belongs to
        task.episode          # Episode object of this task

    You can cancel a running download task by setting its status:

        task.status = DownloadTask.CANCELLED

    The task will then abort as soon as possible (due to the nature
    of downloading data, this can take a while when the Internet is
    busy).

    The "status_changed" attribute gets set to True everytime the
    "status" attribute changes its value. After you get the value of
    the "status_changed" attribute, it is always reset to False:

        if task.status_changed:
            new_status = task.status
            # .. update the UI accordingly ..

    Obviously, this also means that you must have at most *one*
    place in your UI code where you check for status changes and
    broadcast the status updates from there.

    While the download is taking place and after the .run() method
    has finished, you can get the final status to check if the download
    was successful:

        if task.status == DownloadTask.DONE:
            # .. everything ok ..
        elif task.status == DownloadTask.FAILED:
            # .. an error happened, and the
            #    error_message attribute is set ..
            print task.error_message
        elif task.status == DownloadTask.PAUSED:
            # .. user paused the download ..
        elif task.status == DownloadTask.CANCELLED:
            # .. user cancelled the download ..

    The difference between cancelling and pausing a DownloadTask is
    that the temporary file gets deleted when cancelling, but does
    not get deleted when pausing.

    Be sure to call .removed_from_list() on this task when removing
    it from the UI, so that it can carry out any pending clean-up
    actions (e.g. removing the temporary file when the task has not
    finished successfully; i.e. task.status != DownloadTask.DONE).

    The UI can call the method "notify_as_finished()" to determine if
    this episode still has still to be shown as "finished" download
    in a notification window. This will return True only the first time
    it is called when the status is DONE. After returning True once,
    it will always return False afterwards.

    The same thing works for failed downloads ("notify_as_failed()").
    """
    # Possible states this download task can be in
    STATUS_MESSAGE = (_('Added'), _('Queued'), _('Downloading'),
            _('Finished'), _('Failed'), _('Cancelled'), _('Paused'))
    (INIT, QUEUED, DOWNLOADING, DONE, FAILED, CANCELLED, PAUSED) = range(7)

    # Wheter this task represents a file download or a device sync operation
    ACTIVITY_DOWNLOAD, ACTIVITY_SYNCHRONIZE = range(2)

    # Minimum time between progress updates (in seconds)
    MIN_TIME_BETWEEN_UPDATES = 1.

    def __str__(self):
        return self.__episode.title

    def __get_status(self):
        return self.__status

    def __set_status(self, status):
        if status != self.__status:
            self.__status_changed = True
            self.__status = status

    status = property(fget=__get_status, fset=__set_status)

    def __get_status_changed(self):
        if self.__status_changed:
            self.__status_changed = False
            return True
        else:
            return False

    status_changed = property(fget=__get_status_changed)

    def __get_activity(self):
        return self.__activity

    def __set_activity(self, activity):
        self.__activity = activity

    activity = property(fget=__get_activity, fset=__set_activity)


    def __get_url(self):
        return self.__episode.url

    url = property(fget=__get_url)

    def __get_podcast_url(self):
        return self.__episode.channel.url

    podcast_url = property(fget=__get_podcast_url)

    def __get_episode(self):
        return self.__episode

    episode = property(fget=__get_episode)

    def cancel(self):
        if self.status in (self.DOWNLOADING, self.QUEUED):
            self.status = self.CANCELLED

    def removed_from_list(self):
        if self.status != self.DONE:
            util.delete_file(self.tempname)

    def __init__(self, episode, config):
        assert episode.download_task is None
        self.__status = DownloadTask.INIT
        self.__activity = DownloadTask.ACTIVITY_DOWNLOAD
        self.__status_changed = True
        self.__episode = episode
        self._config = config

        # Create the target filename and save it in the database
        self.filename = self.__episode.local_filename(create=True)
        self.tempname = self.filename + '.partial'

        self.total_size = self.__episode.file_size
        self.speed = 0.0
        self.progress = 0.0
        self.error_message = None

        # Have we already shown this task in a notification?
        self._notification_shown = False

        # Variables for speed limit and speed calculation
        self.__start_time = 0
        self.__start_blocks = 0
        self.__limit_rate_value = self._config.limit_rate_value
        self.__limit_rate = self._config.limit_rate

        # Progress update functions
        self._progress_updated = None
        self._last_progress_updated = 0.

        # If the tempname already exists, set progress accordingly
        if os.path.exists(self.tempname):
            try:
                already_downloaded = os.path.getsize(self.tempname)
                if self.total_size > 0:
                    self.progress = max(0.0, min(1.0, float(already_downloaded)/self.total_size))
            except OSError, os_error:
                logger.error('Cannot get size for %s', os_error)
        else:
            # "touch self.tempname", so we also get partial
            # files for resuming when the file is queued
            open(self.tempname, 'w').close()

        # Store a reference to this task in the episode
        episode.download_task = self

    def notify_as_finished(self):
        if self.status == DownloadTask.DONE:
            if self._notification_shown:
                return False
            else:
                self._notification_shown = True
                return True

        return False

    def notify_as_failed(self):
        if self.status == DownloadTask.FAILED:
            if self._notification_shown:
                return False
            else:
                self._notification_shown = True
                return True

        return False

    def add_progress_callback(self, callback):
        self._progress_updated = callback

    def status_updated(self, count, blockSize, totalSize):
        # We see a different "total size" while downloading,
        # so correct the total size variable in the thread
        if totalSize != self.total_size and totalSize > 0:
            self.total_size = float(totalSize)
            if self.__episode.file_size != self.total_size:
                logger.debug('Updating file size of %s to %s',
                        self.filename, self.total_size)
                self.__episode.file_size = self.total_size
                self.__episode.save()

        if self.total_size > 0:
            self.progress = max(0.0, min(1.0, float(count*blockSize)/self.total_size))
            if self._progress_updated is not None:
                diff = time.time() - self._last_progress_updated
                if diff > self.MIN_TIME_BETWEEN_UPDATES or self.progress == 1.:
                    self._progress_updated(self.progress)
                    self._last_progress_updated = time.time()

        self.calculate_speed(count, blockSize)

        if self.status == DownloadTask.CANCELLED:
            raise DownloadCancelledException()

        if self.status == DownloadTask.PAUSED:
            raise DownloadCancelledException()

    def calculate_speed(self, count, blockSize):
        if count % 5 == 0:
            now = time.time()
            if self.__start_time > 0:
                # Has rate limiting been enabled or disabled?                
                if self.__limit_rate != self._config.limit_rate: 
                    # If it has been enabled then reset base time and block count                    
                    if self._config.limit_rate:
                        self.__start_time = now
                        self.__start_blocks = count
                    self.__limit_rate = self._config.limit_rate
                    
                # Has the rate been changed and are we currently limiting?            
                if self.__limit_rate_value != self._config.limit_rate_value and self.__limit_rate: 
                    self.__start_time = now
                    self.__start_blocks = count
                    self.__limit_rate_value = self._config.limit_rate_value

                passed = now - self.__start_time
                if passed > 0:
                    speed = ((count-self.__start_blocks)*blockSize)/passed
                else:
                    speed = 0
            else:
                self.__start_time = now
                self.__start_blocks = count
                passed = now - self.__start_time
                speed = count*blockSize

            self.speed = float(speed)

            if self._config.limit_rate and speed > self._config.limit_rate_value:
                # calculate the time that should have passed to reach
                # the desired download rate and wait if necessary
                should_have_passed = float((count-self.__start_blocks)*blockSize)/(self._config.limit_rate_value*1024.0)
                if should_have_passed > passed:
                    # sleep a maximum of 10 seconds to not cause time-outs
                    delay = min(10.0, float(should_have_passed-passed))
                    time.sleep(delay)

    def recycle(self):
        self.episode.download_task = None

    def run(self):
        # Speed calculation (re-)starts here
        self.__start_time = 0
        self.__start_blocks = 0

        # If the download has already been cancelled, skip it
        if self.status == DownloadTask.CANCELLED:
            util.delete_file(self.tempname)
            self.progress = 0.0
            self.speed = 0.0
            return False

        # We only start this download if its status is "queued"
        if self.status != DownloadTask.QUEUED:
            return False

        # We are downloading this file right now
        self.status = DownloadTask.DOWNLOADING
        self._notification_shown = False

        try:
            # Resolve URL and start downloading the episode
            fmt_ids = youtube.get_fmt_ids(self._config.youtube)
            url = youtube.get_real_download_url(self.__episode.url, fmt_ids)
            url = vimeo.get_real_download_url(url)

            downloader = DownloadURLOpener(self.__episode.channel)

            # HTTP Status codes for which we retry the download
            retry_codes = (408, 418, 504, 598, 599)
            max_retries = max(0, self._config.auto.retries)

            # Retry the download on timeout (bug 1013)
            for retry in range(max_retries + 1):
                if retry > 0:
                    logger.info('Retrying download of %s (%d)', url, retry)
                    time.sleep(1)

                try:
                    headers, real_url = downloader.retrieve_resume(url,
                        self.tempname, reporthook=self.status_updated)
                    # If we arrive here, the download was successful
                    break
                except urllib.ContentTooShortError, ctse:
                    if retry < max_retries:
                        logger.info('Content too short: %s - will retry.',
                                url)
                        continue
                    raise
                except socket.timeout, tmout:
                    if retry < max_retries:
                        logger.info('Socket timeout: %s - will retry.', url)
                        continue
                    raise
                except gPodderDownloadHTTPError, http:
                    if retry < max_retries and http.error_code in retry_codes:
                        logger.info('HTTP error %d: %s - will retry.',
                                http.error_code, url)
                        continue
                    raise

            new_mimetype = headers.get('content-type', self.__episode.mime_type)
            old_mimetype = self.__episode.mime_type
            _basename, ext = os.path.splitext(self.filename)
            if new_mimetype != old_mimetype or util.wrong_extension(ext):
                logger.info('Updating mime type: %s => %s', old_mimetype, new_mimetype)
                old_extension = self.__episode.extension()
                self.__episode.mime_type = new_mimetype
                new_extension = self.__episode.extension()

                # If the desired filename extension changed due to the new
                # mimetype, we force an update of the local filename to fix the
                # extension.
                if old_extension != new_extension or util.wrong_extension(ext):
                    self.filename = self.__episode.local_filename(create=True, force_update=True)

            # In some cases, the redirect of a URL causes the real filename to
            # be revealed in the final URL (e.g. http://gpodder.org/bug/1423)
            if real_url != url and not util.is_known_redirecter(real_url):
                realname, realext = util.filename_from_url(real_url)

                # Only update from redirect if the redirected-to filename has
                # a proper extension (this is needed for e.g. YouTube)
                if not util.wrong_extension(realext):
                    real_filename = ''.join((realname, realext))
                    self.filename = self.__episode.local_filename(create=True,
                            force_update=True, template=real_filename)
                    logger.info('Download was redirected (%s). New filename: %s',
                            real_url, os.path.basename(self.filename))

            # Look at the Content-disposition header; use if if available
            disposition_filename = get_header_param(headers, \
                    'filename', 'content-disposition')

            # Some servers do send the content-disposition header, but provide
            # an empty filename, resulting in an empty string here (bug 1440)
            if disposition_filename is not None and disposition_filename != '':
                # The server specifies a download filename - try to use it
                disposition_filename = os.path.basename(disposition_filename)
                self.filename = self.__episode.local_filename(create=True, \
                        force_update=True, template=disposition_filename)
                new_mimetype, encoding = mimetypes.guess_type(self.filename)
                if new_mimetype is not None:
                    logger.info('Using content-disposition mimetype: %s',
                            new_mimetype)
                    self.__episode.mime_type = new_mimetype

            # Re-evaluate filename and tempname to take care of podcast renames
            # while downloads are running (which will change both file names)
            self.filename = self.__episode.local_filename(create=False)
            self.tempname = os.path.join(os.path.dirname(self.filename),
                    os.path.basename(self.tempname))
            shutil.move(self.tempname, self.filename)

            # Model- and database-related updates after a download has finished
            self.__episode.on_downloaded(self.filename)
        except DownloadCancelledException:
            logger.info('Download has been cancelled/paused: %s', self)
            if self.status == DownloadTask.CANCELLED:
                util.delete_file(self.tempname)
                self.progress = 0.0
                self.speed = 0.0
        except urllib.ContentTooShortError, ctse:
            self.status = DownloadTask.FAILED
            self.error_message = _('Missing content from server')
        except IOError, ioe:
            logger.error('%s while downloading "%s": %s', ioe.strerror,
                    self.__episode.title, ioe.filename, exc_info=True)
            self.status = DownloadTask.FAILED
            d = {'error': ioe.strerror, 'filename': ioe.filename}
            self.error_message = _('I/O Error: %(error)s: %(filename)s') % d
        except gPodderDownloadHTTPError, gdhe:
            logger.error('HTTP %s while downloading "%s": %s',
                    gdhe.error_code, self.__episode.title, gdhe.error_message,
                    exc_info=True)
            self.status = DownloadTask.FAILED
            d = {'code': gdhe.error_code, 'message': gdhe.error_message}
            self.error_message = _('HTTP Error %(code)s: %(message)s') % d
        except Exception, e:
            self.status = DownloadTask.FAILED
            logger.error('Download failed: %s', str(e), exc_info=True)
            self.error_message = _('Error: %s') % (str(e),)

        if self.status == DownloadTask.DOWNLOADING:
            # Everything went well - we're done
            self.status = DownloadTask.DONE
            if self.total_size <= 0:
                self.total_size = util.calculate_size(self.filename)
                logger.info('Total size updated to %d', self.total_size)
            self.progress = 1.0
            gpodder.user_extensions.on_episode_downloaded(self.__episode)
            return True
        
        self.speed = 0.0

        # We finished, but not successfully (at least not really)
        return False


########NEW FILE########
__FILENAME__ = extensions
# -*- coding: utf-8 -*-
#
# gPodder - A media aggregator and podcast client
# Copyright (c) 2005-2009 Thomas Perl and the gPodder Team
#
# gPodder is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# gPodder is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

"""
Loads and executes user extensions

Extensions are Python scripts in "$GPODDER_HOME/Extensions". Each script must
define a class named "gPodderExtension", otherwise it will be ignored.

The extensions class defines several callbacks that will be called by gPodder
at certain points. See the methods defined below for a list of callbacks and
their parameters.

For an example extension see share/gpodder/examples/extensions.py
"""

import glob
import imp
import inspect
import json
import os
import functools
import shlex
import subprocess
import sys
import re
from datetime import datetime

import gpodder

_ = gpodder.gettext

from gpodder import util

import logging
logger = logging.getLogger(__name__)


CATEGORY_DICT = {
    'desktop-integration': _('Desktop Integration'),
    'interface': _('Interface'),
    'post-download': _('Post download'),
}
DEFAULT_CATEGORY = _('Other')


def call_extensions(func):
    """Decorator to create handler functions in ExtensionManager

    Calls the specified function in all user extensions that define it.
    """
    method_name = func.__name__

    @functools.wraps(func)
    def handler(self, *args, **kwargs):
        result = None
        for container in self.containers:
            if not container.enabled or container.module is None:
                continue

            try:
                callback = getattr(container.module, method_name, None)
                if callback is None:
                    continue

                # If the results are lists, concatenate them to show all
                # possible items that are generated by all extension together
                cb_res = callback(*args, **kwargs)
                if isinstance(result, list) and isinstance(cb_res, list):
                    result.extend(cb_res)
                elif cb_res is not None:
                    result = cb_res
            except Exception, exception:
                logger.error('Error in %s in %s: %s', container.filename,
                        method_name, exception, exc_info=True)
        func(self, *args, **kwargs)
        return result

    return handler


class ExtensionMetadata(object):
    # Default fallback metadata in case metadata fields are missing
    DEFAULTS = {
        'description': _('No description for this extension.'),
        'doc': None,
        'payment': None,
    }
    SORTKEYS = {
        'title': 1,
        'description': 2,
        'category': 3,
        'authors': 4,
        'only_for': 5,
        'mandatory_in': 6,
        'disable_in': 7,
    }

    def __init__(self, container, metadata):
        if 'title' not in metadata:
            metadata['title'] = container.name

        category = metadata.get('category', 'other')
        metadata['category'] = CATEGORY_DICT.get(category, DEFAULT_CATEGORY)
        
        self.__dict__.update(metadata)
        
    def __getattr__(self, name):
        try:
            return self.DEFAULTS[name]
        except KeyError, e:
            raise AttributeError(name, e)
            
    def get_sorted(self):
        kf = lambda x: self.SORTKEYS.get(x[0], 99)
        return sorted([(k, v) for k, v in self.__dict__.items()], key=kf)

    def check_ui(self, target, default):
        """Checks metadata information like
            __only_for__ = 'gtk'
            __mandatory_in__ = 'gtk'
            __disable_in__ = 'gtk'

        The metadata fields in an extension can be a string with
        comma-separated values for UIs. This will be checked against
        boolean variables in the "gpodder.ui" object.

        Example metadata field in an extension:

            __only_for__ = 'gtk,qml'
            __only_for__ = 'unity'

        In this case, this function will return the value of the default
        if any of the following expressions will evaluate to True:

            gpodder.ui.gtk
            gpodder.ui.qml
            gpodder.ui.unity
            gpodder.ui.cli
            gpodder.ui.osx
            gpodder.ui.win32

        New, unknown UIs are silently ignored and will evaluate to False.
        """
        if not hasattr(self, target):
            return default

        uis = filter(None, [x.strip() for x in getattr(self, target).split(',')])
        return any(getattr(gpodder.ui, ui.lower(), False) for ui in uis)

    @property   
    def available_for_current_ui(self):
        return self.check_ui('only_for', True)
    
    @property
    def mandatory_in_current_ui(self):
        return self.check_ui('mandatory_in', False)
        
    @property
    def disable_in_current_ui(self):
        return self.check_ui('disable_in', False)

class MissingDependency(Exception):
    def __init__(self, message, dependency, cause=None):
        Exception.__init__(self, message)
        self.dependency = dependency
        self.cause = cause

class MissingModule(MissingDependency): pass
class MissingCommand(MissingDependency): pass

class ExtensionContainer(object):
    """An extension container wraps one extension module"""

    def __init__(self, manager, name, config, filename=None, module=None):
        self.manager = manager

        self.name = name
        self.config = config
        self.filename = filename
        self.module = module
        self.enabled = False
        self.error = None

        self.default_config = None
        self.parameters = None
        self.metadata = ExtensionMetadata(self, self._load_metadata(filename))

    def require_command(self, command):
        """Checks if the given command is installed on the system

        Returns the complete path of the command

        @param command: String with the command name
        """
        result = util.find_command(command)
        if result is None:
            msg = _('Command not found: %(command)s') % {'command': command}
            raise MissingCommand(msg, command)
        return result

    def require_any_command(self, command_list):
        """Checks if any of the given commands is installed on the system

        Returns the complete path of first found command in the list

        @param command: List with the commands name
        """
        for command in command_list:
            result = util.find_command(command)
            if result is not None:
                return result

        msg = _('Need at least one of the following commands: %(list_of_commands)s') % \
            {'list_of_commands': ', '.join(command_list)}
        raise MissingCommand(msg, ', '.join(command_list))

    def _load_metadata(self, filename):
        if not filename or not os.path.exists(filename):
            return {}

        extension_py = open(filename).read()
        metadata = dict(re.findall("__([a-z_]+)__ = '([^']+)'", extension_py))

        # Support for using gpodder.gettext() as _ to localize text
        localized_metadata = dict(re.findall("__([a-z_]+)__ = _\('([^']+)'\)",
            extension_py))

        for key in localized_metadata:
            metadata[key] = gpodder.gettext(localized_metadata[key])

        return metadata

    def set_enabled(self, enabled):
        if enabled and not self.enabled:
            try:
                self.load_extension()
                self.error = None
                self.enabled = True
                if hasattr(self.module, 'on_load'):
                    self.module.on_load()
            except Exception, exception:
                logger.error('Cannot load %s from %s: %s', self.name,
                        self.filename, exception, exc_info=True)
                if isinstance(exception, ImportError):
                    # Wrap ImportError in MissingCommand for user-friendly
                    # message (might be displayed in the GUI)
                    match = re.match('No module named (.*)', exception.message)
                    if match:
                        module = match.group(1)
                        msg = _('Python module not found: %(module)s') % {
                            'module': module
                        }
                        exception = MissingCommand(msg, module, exception)
                self.error = exception
                self.enabled = False
        elif not enabled and self.enabled:
            try:
                if hasattr(self.module, 'on_unload'):
                    self.module.on_unload()
            except Exception, exception:
                logger.error('Failed to on_unload %s: %s', self.name,
                        exception, exc_info=True)
            self.enabled = False

    def load_extension(self):
        """Load and initialize the gPodder extension module"""
        if self.module is not None:
            logger.info('Module already loaded.')
            return

        if not self.metadata.available_for_current_ui:
            logger.info('Not loading "%s" (only_for = "%s")',
                    self.name, self.metadata.only_for)
            return

        basename, extension = os.path.splitext(os.path.basename(self.filename))
        fp = open(self.filename, 'r')
        try:
            module_file = imp.load_module(basename, fp, self.filename,
                    (extension, 'r', imp.PY_SOURCE))
        finally:
            # Remove the .pyc file if it was created during import
            util.delete_file(self.filename + 'c')
        fp.close()

        self.default_config = getattr(module_file, 'DefaultConfig', {})
        if self.default_config:
            self.manager.core.config.register_defaults({
                'extensions': {
                    self.name: self.default_config,
                }
            })
        self.config = getattr(self.manager.core.config.extensions, self.name)

        self.module = module_file.gPodderExtension(self)
        logger.info('Module loaded: %s', self.filename)


class ExtensionManager(object):
    """Loads extensions and manages self-registering plugins"""

    def __init__(self, core):
        self.core = core
        self.filenames = os.environ.get('GPODDER_EXTENSIONS', '').split()
        self.containers = []

        core.config.add_observer(self._config_value_changed)
        enabled_extensions = core.config.extensions.enabled

        if os.environ.get('GPODDER_DISABLE_EXTENSIONS', '') != '':
            logger.info('Disabling all extensions (from environment)')
            return

        for name, filename in self._find_extensions():
            logger.debug('Found extension "%s" in %s', name, filename)
            config = getattr(core.config.extensions, name)
            container = ExtensionContainer(self, name, config, filename)
            if (name in enabled_extensions or
                    container.metadata.mandatory_in_current_ui):
                container.set_enabled(True)
            if (name in enabled_extensions and
                    container.metadata.disable_in_current_ui):
                container.set_enabled(False)
            self.containers.append(container)

    def shutdown(self):
        for container in self.containers:
            container.set_enabled(False)

    def _config_value_changed(self, name, old_value, new_value):
        if name != 'extensions.enabled':
            return
            
        for container in self.containers:
            new_enabled = (container.name in new_value)
            if new_enabled == container.enabled:
                continue
                
            logger.info('Extension "%s" is now %s', container.name,
                    'enabled' if new_enabled else 'disabled')
            container.set_enabled(new_enabled)
            if new_enabled and not container.enabled:
                logger.warn('Could not enable extension: %s',
                        container.error)
                self.core.config.extensions.enabled = [x
                        for x in self.core.config.extensions.enabled
                        if x != container.name]

    def _find_extensions(self):
        extensions = {}

        if not self.filenames:
            builtins = os.path.join(gpodder.prefix, 'share', 'gpodder',
                'extensions', '*.py')
            user_extensions = os.path.join(gpodder.home, 'Extensions', '*.py')
            self.filenames = glob.glob(builtins) + glob.glob(user_extensions)

        # Let user extensions override built-in extensions of the same name
        for filename in self.filenames:
            if not filename or not os.path.exists(filename):
                logger.info('Skipping non-existing file: %s', filename)
                continue

            name, _ = os.path.splitext(os.path.basename(filename))
            extensions[name] = filename

        return sorted(extensions.items())

    def get_extensions(self):
        """Get a list of all loaded extensions and their enabled flag"""
        return [c for c in self.containers 
            if c.metadata.available_for_current_ui and 
            not c.metadata.mandatory_in_current_ui and
            not c.metadata.disable_in_current_ui]

    # Define all known handler functions here, decorate them with the
    # "call_extension" decorator to forward all calls to extension scripts that have
    # the same function defined in them. If the handler functions here contain
    # any code, it will be called after all the extensions have been called.

    @call_extensions
    def on_ui_initialized(self, model, update_podcast_callback,
            download_episode_callback):
        """Called when the user interface is initialized.

        @param model: A gpodder.model.Model instance
        @param update_podcast_callback: Function to update a podcast feed
        @param download_episode_callback: Function to download an episode
        """
        pass

    @call_extensions
    def on_podcast_subscribe(self, podcast):
        """Called when the user subscribes to a new podcast feed.

        @param podcast: A gpodder.model.PodcastChannel instance
        """
        pass

    @call_extensions
    def on_podcast_updated(self, podcast):
        """Called when a podcast feed was updated

        This extension will be called even if there were no new episodes.

        @param podcast: A gpodder.model.PodcastChannel instance
        """
        pass

    @call_extensions
    def on_podcast_update_failed(self, podcast, exception):
        """Called when a podcast update failed.

        @param podcast: A gpodder.model.PodcastChannel instance

        @param exception: The reason.
        """
        pass

    @call_extensions
    def on_podcast_save(self, podcast):
        """Called when a podcast is saved to the database

        This extensions will be called when the user edits the metadata of
        the podcast or when the feed was updated.

        @param podcast: A gpodder.model.PodcastChannel instance
        """
        pass

    @call_extensions
    def on_podcast_delete(self, podcast):
        """Called when a podcast is deleted from the database

        @param podcast: A gpodder.model.PodcastChannel instance
        """
        pass

    @call_extensions
    def on_episode_playback(self, episode):
        """Called when an episode is played back

        This function will be called when the user clicks on "Play" or
        "Open" in the GUI to open an episode with the media player.

        @param episode: A gpodder.model.PodcastEpisode instance
        """
        pass

    @call_extensions
    def on_episode_save(self, episode):
        """Called when an episode is saved to the database

        This extension will be called when a new episode is added to the
        database or when the state of an existing episode is changed.

        @param episode: A gpodder.model.PodcastEpisode instance
        """
        pass

    @call_extensions
    def on_episode_downloaded(self, episode):
        """Called when an episode has been downloaded

        You can retrieve the filename via episode.local_filename(False)

        @param episode: A gpodder.model.PodcastEpisode instance
        """
        pass

    @call_extensions
    def on_all_episodes_downloaded(self):
        """Called when all episodes has been downloaded
        """
        pass

    @call_extensions
    def on_episode_synced(self, device, episode):
        """Called when an episode has been synced to device

        You can retrieve the filename via episode.local_filename(False)
        For MP3PlayerDevice:
            You can retrieve the filename on device via
                device.get_episode_file_on_device(episode)
            You can retrieve the folder name on device via
                device.get_episode_folder_on_device(episode)

        @param device: A gpodder.sync.Device instance
        @param episode: A gpodder.model.PodcastEpisode instance
        """
        pass

    @call_extensions
    def on_episodes_context_menu(self, episodes):
        """Called when the episode list context menu is opened

        You can add additional context menu entries here. You have to
        return a list of tuples, where the first item is a label and
        the second item is a callable that will get the episode as its
        first and only parameter.

        Example return value:

        [('Mark as new', lambda episodes: ...)]

        @param episodes: A list of gpodder.model.PodcastEpisode instances
        """
        pass

    @call_extensions
    def on_channel_context_menu(self, channel):
        """Called when the channel list context menu is opened

        You can add additional context menu entries here. You have to return a
        list of tuples, where the first item is a label and the second item is a
        callable that will get the channel as its first and only parameter.

        Example return value:

        [('Update channel', lambda channel: ...)]
        @param channel: A gpodder.model.PodcastChannel instance
        """
        pass

    @call_extensions
    def on_episode_delete(self, episode, filename):
        """Called just before the episode's disk file is about to be
        deleted."""
        pass

    @call_extensions
    def on_episode_removed_from_podcast(self, episode):
        """Called just before the episode is about to be removed from
        the podcast channel, e.g., when the episode has not been
        downloaded and it disappears from the feed.

        @param podcast: A gpodder.model.PodcastChannel instance
        """
        pass

    @call_extensions
    def on_notification_show(self, title, message):
        """Called when a notification should be shown

        @param title: title of the notification
        @param message: message of the notification
        """
        pass

    @call_extensions
    def on_download_progress(self, progress):
        """Called when the overall download progress changes

        @param progress: The current progress value (0..1)
        """
        pass

    @call_extensions
    def on_ui_object_available(self, name, ui_object):
        """Called when an UI-specific object becomes available

        XXX: Experimental. This hook might go away without notice (and be
        replaced with something better). Only use for in-tree extensions.

        @param name: The name/ID of the object
        @param ui_object: The object itself
        """
        pass


########NEW FILE########
__FILENAME__ = feedcore
# -*- coding: utf-8 -*-
#
# gPodder - A media aggregator and podcast client
# Copyright (c) 2005-2014 Thomas Perl and the gPodder Team
#
# gPodder is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# gPodder is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#

#
# Generic feed fetching module for aggregators
# Thomas Perl <thp@gpodder.org>; 2009-06-11
#

import feedparser

import logging
logger = logging.getLogger(__name__)

try:
    # Python 2
    from rfc822 import mktime_tz
except ImportError:
    # Python 3
    from email.utils import mktime_tz


# Version check to avoid bug 1648
feedparser_version = tuple(int(x) if x.isdigit() else x
        for x in feedparser.__version__.split('.'))
feedparser_miniumum_version = (5, 1, 2)
if feedparser_version < feedparser_miniumum_version:
    installed_version = feedparser.__version__
    required_version = '.'.join(str(x) for x in feedparser_miniumum_version)
    logger.warn('Your feedparser is too old. Installed: %s, recommended: %s',
            installed_version, required_version)


def patch_feedparser():
    """Monkey-patch the Universal Feed Parser"""
    # Detect the 'plain' content type as 'text/plain'
    # http://code.google.com/p/feedparser/issues/detail?id=80
    def mapContentType2(self, contentType):
        contentType = contentType.lower()
        if contentType == 'text' or contentType == 'plain':
            contentType = 'text/plain'
        elif contentType == 'html':
            contentType = 'text/html'
        elif contentType == 'xhtml':
            contentType = 'application/xhtml+xml'
        return contentType

    try:
        if feedparser._FeedParserMixin().mapContentType('plain') == 'plain':
            feedparser._FeedParserMixin.mapContentType = mapContentType2
    except:
        pass
    
    # Fix parsing of Media RSS with feedparser, as described here: 
    #   http://code.google.com/p/feedparser/issues/detail?id=100#c4
    def _start_media_content(self, attrsD):
        context = self._getContext()
        context.setdefault('media_content', [])
        context['media_content'].append(attrsD)
        
    try:
        feedparser._FeedParserMixin._start_media_content = _start_media_content
    except:
        pass

    # Fix problem with the EA.com official podcast
    # https://bugs.gpodder.org/show_bug.cgi?id=588
    if '*/*' not in feedparser.ACCEPT_HEADER.split(','):
        feedparser.ACCEPT_HEADER += ',*/*'

    # Fix problem with YouTube feeds and pubDate/atom:modified
    # https://bugs.gpodder.org/show_bug.cgi?id=1492
    # http://code.google.com/p/feedparser/issues/detail?id=310
    def _end_updated(self):
        value = self.pop('updated')
        parsed_value = feedparser._parse_date(value)
        overwrite = ('youtube.com' not in self.baseuri)
        try:
            self._save('updated_parsed', parsed_value, overwrite=overwrite)
        except TypeError, te:
            logger.warn('Your feedparser version is too old: %s', te)

    try:
        feedparser._FeedParserMixin._end_updated = _end_updated
    except:
        pass


patch_feedparser()


class ExceptionWithData(Exception):
    """Base exception with additional payload"""
    def __init__(self, data):
        Exception.__init__(self)
        self.data = data

    def __str__(self):
        return '%s: %s' % (self.__class__.__name__, str(self.data))

# Temporary errors
class Offline(Exception): pass
class BadRequest(Exception): pass
class InternalServerError(Exception): pass
class WifiLogin(ExceptionWithData): pass

# Fatal errors
class Unsubscribe(Exception): pass
class NotFound(Exception): pass
class InvalidFeed(Exception): pass
class UnknownStatusCode(ExceptionWithData): pass

# Authentication error
class AuthenticationRequired(Exception): pass

# Successful status codes
UPDATED_FEED, NEW_LOCATION, NOT_MODIFIED, CUSTOM_FEED = range(4)

class Result:
    def __init__(self, status, feed=None):
        self.status = status
        self.feed = feed


class Fetcher(object):
    # Supported types, see http://feedvalidator.org/docs/warning/EncodingMismatch.html
    FEED_TYPES = ('application/rss+xml',
                  'application/atom+xml',
                  'application/rdf+xml',
                  'application/xml',
                  'text/xml')

    def __init__(self, user_agent):
        self.user_agent = user_agent

    def _resolve_url(self, url):
        """Provide additional ways of resolving an URL

        Subclasses can override this method to provide more
        ways of resolving a given URL to a feed URL. If the
        Fetcher is in "autodiscovery" mode, it will try this
        method as a last resort for coming up with a feed URL.
        """
        return None

    def _autodiscover_feed(self, feed):
        # First, try all <link> elements if available
        for link in feed.feed.get('links', ()):
            is_feed = link.get('type', '') in self.FEED_TYPES
            is_alternate = link.get('rel', '') == 'alternate'
            url = link.get('href', None)

            if url and is_feed and is_alternate:
                try:
                    return self._parse_feed(url, None, None, False)
                except Exception, e:
                    pass

        # Second, try to resolve the URL
        url = self._resolve_url(feed.href)
        if url:
            result = self._parse_feed(url, None, None, False)
            result.status = NEW_LOCATION
            return result

    def _check_offline(self, feed):
        if not hasattr(feed, 'headers'):
            raise Offline()

    def _check_wifi_login_page(self, feed):
        html_page = 'text/html' in feed.headers.get('content-type', '')
        if not feed.version and feed.status == 302 and html_page:
            raise WifiLogin(feed.href)

    def _check_valid_feed(self, feed):
        if feed is None:
            raise InvalidFeed('feed is None')

        if not hasattr(feed, 'status'):
            raise InvalidFeed('feed has no status code')

        if not feed.version and feed.status != 304 and feed.status != 401:
            raise InvalidFeed('unknown feed type')

    def _normalize_status(self, status):
        # Based on Mark Pilgrim's "Atom aggregator behaviour" article
        if status in (200, 301, 302, 304, 400, 401, 403, 404, 410, 500):
            return status
        elif status >= 200 and status < 300:
            return 200
        elif status >= 300 and status < 400:
            return 302
        elif status >= 400 and status < 500:
            return 400
        elif status >= 500 and status < 600:
            return 500
        else:
            return status

    def _check_rss_redirect(self, feed):
        new_location = feed.feed.get('newlocation', None)
        if new_location:
            feed.href = feed.feed.newlocation
            return Result(NEW_LOCATION, feed)

        return None

    def _check_statuscode(self, feed):
        status = self._normalize_status(feed.status)
        if status == 200:
            return Result(UPDATED_FEED, feed)
        elif status == 301:
            return Result(NEW_LOCATION, feed)
        elif status == 302:
            return Result(UPDATED_FEED, feed)
        elif status == 304:
            return Result(NOT_MODIFIED, feed)

        if status == 400:
            raise BadRequest('bad request')
        elif status == 401:
            raise AuthenticationRequired('authentication required')
        elif status == 403:
            raise Unsubscribe('forbidden')
        elif status == 404:
            raise NotFound('not found')
        elif status == 410:
            raise Unsubscribe('resource is gone')
        elif status == 500:
            raise InternalServerError('internal server error')
        else:
            raise UnknownStatusCode(status)

    def _parse_feed(self, url, etag, modified, autodiscovery=True):
        if url.startswith('file://'):
            is_local = True
            url = url[len('file://'):]
        else:
            is_local = False

        feed = feedparser.parse(url,
                agent=self.user_agent,
                modified=modified,
                etag=etag)

        if is_local:
            if feed.version:
                feed.headers = {}
                return Result(UPDATED_FEED, feed)
            else:
                raise InvalidFeed('Not a valid feed file')
        else:
            self._check_offline(feed)
            self._check_wifi_login_page(feed)

            if feed.status != 304 and not feed.version and autodiscovery:
                feed = self._autodiscover_feed(feed).feed

            self._check_valid_feed(feed)

            redirect = self._check_rss_redirect(feed)
            if redirect is not None:
                return redirect

            return self._check_statuscode(feed)

    def fetch(self, url, etag=None, modified=None):
        return self._parse_feed(url, etag, modified)


def get_pubdate(entry):
    """Try to determine the real pubDate of a feedparser entry

    This basically takes the updated_parsed value, but also uses some more
    advanced techniques to work around various issues with ugly feeds.

    "published" now also takes precedence over "updated" (with updated used as
    a fallback if published is not set/available). RSS' "pubDate" element is
    "updated", and will only be used if published_parsed is not available.
    """

    pubdate = entry.get('published_parsed', None)

    if pubdate is None:
        pubdate = entry.get('updated_parsed', None)

    if pubdate is None:
        # Cannot determine pubdate - party like it's 1970!
        return 0

    return mktime_tz(pubdate + (0,))


########NEW FILE########
__FILENAME__ = feedservice
# -*- coding: utf-8 -*-
#
# gPodder - A media aggregator and podcast client
# Copyright (c) 2005-2014 Thomas Perl and the gPodder Team
#
# gPodder is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# gPodder is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#

from mygpoclient import feeds

import logging
logger = logging.getLogger(__name__)


def parse_entry(podcast, entry):
    download_url = entry['default_file']['url']
    return podcast.episode_factory({
        'title': entry['title'],
        'description': entry.get('description', ''),
        'url': download_url,
        'mime_type': entry['default_file']['mime_type'],
        'file_size': entry.get('filesize', -1),
        'guid': entry.get('guid', download_url),
        'link': entry.get('link', ''),
        'published': entry.get('released', 0),
        'total_time': entry.get('duration', 0),
    })


def update_using_feedservice(podcasts):
    urls = [podcast.url for podcast in podcasts]
    client = feeds.FeedserviceClient()
    # Last modified + logo/etc..
    result = client.parse_feeds(urls)

    for podcast in podcasts:
        feed = result.get_feed(podcast.url)
        if feed is None:
            logger.info('Feed not updated: %s', podcast.url)
            continue

        # Handle permanent redirects
        if feed.get('new_location', False):
            new_url = feed['new_location']
            logger.info('Redirect %s => %s', podcast.url, new_url)
            podcast.url = new_url

        # Error handling
        if feed.get('errors', False):
            logger.error('Error parsing feed: %s', repr(feed['errors']))
            continue

        # Update per-podcast metadata
        podcast.title = feed.get('title', podcast.url)
        podcast.link = feed.get('link', podcast.link)
        podcast.description = feed.get('description', podcast.description)
        podcast.cover_url = feed.get('logo', podcast.cover_url)
        #podcast.http_etag = feed.get('http_etag', podcast.http_etag)
        #podcast.http_last_modified = feed.get('http_last_modified', \
        #        podcast.http_last_modified)
        podcast.save()

        # Update episodes
        parsed_episodes = [parse_entry(podcast, entry) for entry in feed['episodes']]

        # ...





########NEW FILE########
__FILENAME__ = flattr
# -*- coding: utf-8 -*-
#
# gPodder - A media aggregator and podcast client
# Copyright (c) 2005-2014 Thomas Perl and the gPodder Team
#
# gPodder is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# gPodder is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#


#
#  flattr.py -- gPodder Flattr integration
#  Bernd Schlapsi <brot@gmx.info>   2012-05-26
#

import atexit
import os
import urllib
import urllib2
import urlparse
import json

import logging
logger = logging.getLogger(__name__)

from gpodder import minidb
from gpodder import util

import gpodder

_ = gpodder.gettext


class FlattrAction(object):
    __slots__ = {'url': str}

    def __init__(self, url):
        self.url = url


class Flattr(object):
    STORE_FILE = 'flattr.cache'

    KEY = 'DD2bUSu1TJ7voHz9yNgtC7ld54lKg29Kw2MhL68uG5QUCgT1UZkmXvpSqBtxut7R'
    SECRET = 'lJYWGXhcTXWm4FdOvn0iJg1ZIkm3DkKPTzCpmJs5xehrKk55yWe736XCg9vKj5p3'

    CALLBACK = 'http://gpodder.org/flattr/token.html'
    GPODDER_THING = ('https://flattr.com/submit/auto?' +
            'user_id=thp&url=http://gpodder.org/')

    # OAuth URLs
    OAUTH_BASE = 'https://flattr.com/oauth'
    AUTH_URL_TEMPLATE = (OAUTH_BASE + '/authorize?scope=flattr&' +
            'response_type=code&client_id=%(client_id)s&' +
            'redirect_uri=%(redirect_uri)s')
    OAUTH_TOKEN_URL = OAUTH_BASE + '/token'

    # REST API URLs
    API_BASE = 'https://api.flattr.com/rest/v2'
    USER_INFO_URL = API_BASE + '/user'
    FLATTR_URL = API_BASE + '/flattr'
    THING_INFO_URL_TEMPLATE = API_BASE + '/things/lookup/?url=%(url)s'

    def __init__(self, config):
        self._config = config

        self._store = minidb.Store(os.path.join(gpodder.home, self.STORE_FILE))
        self._worker_thread = None
        atexit.register(self._at_exit)
        
    def _at_exit(self):
        self._worker_proc()
        self._store.close()
        
    def _worker_proc(self):
        self._store.commit()        
        if not self.api_reachable():
            self._worker_thread = None
            return
        
        logger.debug('Processing stored flattr actions...')        
        for flattr_action in self._store.load(FlattrAction):
            success, message = self.flattr_url(flattr_action.url)
            if success:
                self._store.remove(flattr_action)
        self._store.commit()
        self._worker_thread = None
        
    def api_reachable(self):
        reachable, response = util.website_reachable(self.API_BASE)
        if not reachable:
            return False
            
        try:
            content = response.readline()
            content = json.loads(content)
            if 'message' in content and content['message'] == 'hello_world':
                return True
        except ValueError as err:
            pass

        return False

    def request(self, url, data=None):
        headers = {'Content-Type': 'application/json'}

        if url == self.OAUTH_TOKEN_URL:
            # Inject username and password into the request URL
            url = util.url_add_authentication(url, self.KEY, self.SECRET)
        elif self._config.token:
            headers['Authorization'] = 'Bearer ' + self._config.token

        if data is not None:
            data = json.dumps(data)

        try:
            response = util.urlopen(url, headers, data)
        except urllib2.HTTPError, error:
            return {'_gpodder_statuscode': error.getcode()}
        except urllib2.URLError, error:
            return {'_gpodder_no_connection': False}

        if response.getcode() == 200:
            return json.loads(response.read())

        return {'_gpodder_statuscode': response.getcode()}

    def get_auth_url(self):
        return self.AUTH_URL_TEMPLATE % {
                'client_id': self.KEY,
                'redirect_uri': self.CALLBACK,
        }

    def has_token(self):
        return bool(self._config.token)

    def process_retrieved_code(self, url):
        url_parsed = urlparse.urlparse(url)
        query = urlparse.parse_qs(url_parsed.query)

        if 'code' in query:
            code = query['code'][0]
            logger.info('Got code: %s', code)
            self._config.token = self._request_access_token(code)
            return True

        return False

    def _request_access_token(self, code):
        request_url = 'https://flattr.com/oauth/token'

        params = {
            'code': code,
            'grant_type': 'authorization_code',
            'redirect_uri': self.CALLBACK,
        }

        content = self.request(self.OAUTH_TOKEN_URL, data=params)
        return content.get('access_token', '')

    def get_thing_info(self, payment_url):
        """Get information about a Thing on Flattr

        Return a tuple (flattrs, flattred):

            flattrs ... The number of Flattrs this thing received
            flattred ... True if this user already flattred this thing
        """
        if not self._config.token:
            return (0, False)

        quote_url = urllib.quote_plus(util.sanitize_encoding(payment_url))
        url = self.THING_INFO_URL_TEMPLATE % {'url': quote_url}
        data = self.request(url)
        return (int(data.get('flattrs', 0)), bool(data.get('flattred', False)))

    def get_auth_username(self):
        if not self._config.token:
            return ''

        data = self.request(self.USER_INFO_URL)
        return data.get('username', '')

    def flattr_url(self, payment_url):
        """Flattr an object given its Flattr payment URL

        Returns a tuple (success, message):

            success ... True if the item was Flattr'd
            message ... The success or error message
        """
        params = {
            'url': payment_url
        }

        content = self.request(self.FLATTR_URL, data=params)

        if '_gpodder_statuscode' in content:
            status_code = content['_gpodder_statuscode']
            if status_code == 401:
                return (False, _('Not enough means to flattr'))
            elif status_code == 404:
                return (False, _('Item does not exist on Flattr'))
            elif status_code == 403:
                return (True, _('Already flattred or own item'))
            else:
                return (False, _('Invalid request'))
                
        if '_gpodder_no_connection' in content:
            if not self._store.get(FlattrAction, url=payment_url):
                flattr_action = FlattrAction(payment_url)
                self._store.save(flattr_action)
            return (False, _('No internet connection'))
        
        if self._worker_thread is None:        
            self._worker_thread = util.run_in_background(lambda: self._worker_proc(), True)

        return (True, content.get('description', _('No description')))

    def is_flattr_url(self, url):
        if 'flattr.com' in url:
            return True
        return False

    def is_flattrable(self, url):
        if self._config.token and self.is_flattr_url(url):
            return True
        return False

########NEW FILE########
__FILENAME__ = base
# -*- coding: utf-8 -*-
"""
UI Base Module for GtkBuilder

Based on SimpleGladeApp.py Copyright (C) 2004 Sandino Flores Moreno
"""

# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA 02111-1307
# USA

import os
import sys
import re

import tokenize

import gtk

class GtkBuilderWidget(object):
    def __init__(self, ui_folders, textdomain, **kwargs):
        """
        Loads the UI file from the specified folder (with translations
        from the textdomain) and initializes attributes.

        ui_folders:
            List of folders with GtkBuilder .ui files in search order

        textdomain:
            The textdomain to be used for translating strings

        **kwargs:
            Keyword arguments will be set as attributes to this window
        """
        for key, value in kwargs.items():
            setattr(self, key, value)

        self.builder = gtk.Builder()
        self.builder.set_translation_domain(textdomain)

        #print >>sys.stderr, 'Creating new from file', self.__class__.__name__

        ui_file = '%s.ui' % self.__class__.__name__.lower()

        # Search for the UI file in the UI folders, stop after first match
        for ui_folder in ui_folders:
            filename = os.path.join(ui_folder, ui_file)
            if os.path.exists(filename):
                self.builder.add_from_file(filename)
                break

        self.builder.connect_signals(self)
        self.set_attributes()

        self.new()

    def set_attributes(self):
        """
        Convert widget names to attributes of this object.

        It means a widget named vbox-dialog in GtkBuilder
        is refered using self.vbox_dialog in the code.
        """
        for widget in self.builder.get_objects():
            # Just to be safe - every widget from the builder is buildable
            if not isinstance(widget, gtk.Buildable):
                continue

            # The following call looks ugly, but see Gnome bug 591085
            widget_name = gtk.Buildable.get_name(widget)

            widget_api_name = '_'.join(re.findall(tokenize.Name, widget_name))
            if hasattr(self, widget_api_name):
                raise AttributeError("instance %s already has an attribute %s" % (self,widget_api_name))
            else:
                setattr(self, widget_api_name, widget)

    @property
    def main_window(self):
        """Returns the main window of this GtkBuilderWidget"""
        return getattr(self, self.__class__.__name__)

    def new(self):
        """
        Method called when the user interface is loaded and ready to be used.
        At this moment, the widgets are loaded and can be refered as self.widget_name
        """
        pass

    def main(self):
        """
        Starts the main loop of processing events.
        The default implementation calls gtk.main()

        Useful for applications that needs a non gtk main loop.
        For example, applications based on gstreamer needs to override
        this method with gst.main()

        Do not directly call this method in your programs.
        Use the method run() instead.
        """
        gtk.main()

    def quit(self):
        """
        Quit processing events.
        The default implementation calls gtk.main_quit()
        
        Useful for applications that needs a non gtk main loop.
        For example, applications based on gstreamer needs to override
        this method with gst.main_quit()
        """
        gtk.main_quit()

    def run(self):
        """
        Starts the main loop of processing events checking for Control-C.

        The default implementation checks wheter a Control-C is pressed,
        then calls on_keyboard_interrupt().

        Use this method for starting programs.
        """
        try:
            self.main()
        except KeyboardInterrupt:
            self.on_keyboard_interrupt()

    def on_keyboard_interrupt(self):
        """
        This method is called by the default implementation of run()
        after a program is finished by pressing Control-C.
        """
        pass


########NEW FILE########
__FILENAME__ = config
# -*- coding: utf-8 -*-
#
# gPodder - A media aggregator and podcast client
# Copyright (c) 2005-2014 Thomas Perl and the gPodder Team
#
# gPodder is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# gPodder is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#


#
#  gpodder.gtkui.config -- Config object with GTK+ support (2009-08-24)
#


import gtk
import pango

import gpodder
from gpodder import util
from gpodder import config

_ = gpodder.gettext

class ConfigModel(gtk.ListStore):
    C_NAME, C_TYPE_TEXT, C_VALUE_TEXT, C_TYPE, C_EDITABLE, C_FONT_STYLE, \
            C_IS_BOOLEAN, C_BOOLEAN_VALUE = range(8)

    def __init__(self, config):
        gtk.ListStore.__init__(self, str, str, str, object, \
                bool, int, bool, bool)

        self._config = config
        self._fill_model()

        self._config.add_observer(self._on_update)

    def _type_as_string(self, type):
        if type == int:
            return _('Integer')
        elif type == float:
            return _('Float')
        elif type == bool:
            return _('Boolean')
        else:
            return _('String')

    def _fill_model(self):
        self.clear()
        for key in sorted(self._config.all_keys()):
            # Ignore Gtk window state data (position, size, ...)
            if key.startswith('ui.gtk.state.'):
                continue

            value = self._config._lookup(key)
            fieldtype = type(value)

            style = pango.STYLE_NORMAL
            #if value == default:
            #    style = pango.STYLE_NORMAL
            #else:
            #    style = pango.STYLE_ITALIC

            self.append((key, self._type_as_string(fieldtype),
                    config.config_value_to_string(value),
                    fieldtype, fieldtype is not bool, style,
                    fieldtype is bool, bool(value)))

    def _on_update(self, name, old_value, new_value):
        for row in self:
            if row[self.C_NAME] == name:
                style = pango.STYLE_NORMAL
                #if new_value == self._config.Settings[name]:
                #    style = pango.STYLE_NORMAL
                #else:
                #    style = pango.STYLE_ITALIC
                new_value_text = config.config_value_to_string(new_value)
                self.set(row.iter, \
                        self.C_VALUE_TEXT, new_value_text,
                        self.C_BOOLEAN_VALUE, bool(new_value),
                        self.C_FONT_STYLE, style)
                break

    def stop_observing(self):
        self._config.remove_observer(self._on_update)

class UIConfig(config.Config):
    def __init__(self, filename='gpodder.conf'):
        config.Config.__init__(self, filename)
        self.__ignore_window_events = False

    def connect_gtk_editable(self, name, editable):
        editable.delete_text(0, -1)
        editable.insert_text(str(getattr(self, name)))

        def _editable_changed(editable):
            setattr(self, name, editable.get_chars(0, -1))
        editable.connect('changed', _editable_changed)

    def connect_gtk_spinbutton(self, name, spinbutton):
        spinbutton.set_value(getattr(self, name))

        def _spinbutton_changed(spinbutton):
            setattr(self, name, spinbutton.get_value())
        spinbutton.connect('value-changed', _spinbutton_changed)

    def connect_gtk_paned(self, name, paned):
        paned.set_position(getattr(self, name))
        paned_child = paned.get_child1()

        def _child_size_allocate(x, y):
            setattr(self, name, paned.get_position())
        paned_child.connect('size-allocate', _child_size_allocate)

    def connect_gtk_togglebutton(self, name, togglebutton):
        togglebutton.set_active(getattr(self, name))

        def _togglebutton_toggled(togglebutton):
            setattr(self, name, togglebutton.get_active())
        togglebutton.connect('toggled', _togglebutton_toggled)

    def connect_gtk_window(self, window, config_prefix, show_window=False):
        cfg = getattr(self.ui.gtk.state, config_prefix)

        if gpodder.ui.win32:
            window.set_gravity(gtk.gdk.GRAVITY_STATIC)

        window.resize(cfg.width, cfg.height)
        if cfg.x == -1 or cfg.y == -1:
            window.set_position(gtk.WIN_POS_CENTER_ON_PARENT)
        else:
            window.move(cfg.x, cfg.y)

        # Ignore events while we're connecting to the window
        self.__ignore_window_events = True

        def _receive_configure_event(widget, event):
            x_pos, y_pos = event.x, event.y
            width_size, height_size = event.width, event.height
            maximized = bool(event.window.get_state() & 
                    gtk.gdk.WINDOW_STATE_MAXIMIZED)
            if not self.__ignore_window_events and not maximized:
                cfg.x = x_pos
                cfg.y = y_pos
                cfg.width = width_size
                cfg.height = height_size

        window.connect('configure-event', _receive_configure_event)

        def _receive_window_state(widget, event):
            new_value = bool(event.new_window_state &
                    gtk.gdk.WINDOW_STATE_MAXIMIZED)
            cfg.maximized = new_value

        window.connect('window-state-event', _receive_window_state)

        # After the window has been set up, we enable events again
        def _enable_window_events():
            self.__ignore_window_events = False
        util.idle_add(_enable_window_events)

        if show_window:
            window.show()
        if cfg.maximized:
            window.maximize()


########NEW FILE########
__FILENAME__ = channel
# -*- coding: utf-8 -*-
#
# gPodder - A media aggregator and podcast client
# Copyright (c) 2005-2014 Thomas Perl and the gPodder Team
#
# gPodder is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# gPodder is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#

import gtk
import gtk.gdk

import gpodder

_ = gpodder.gettext

from gpodder import util

from gpodder.gtkui.interface.common import BuilderWidget


class gPodderChannel(BuilderWidget):
    MAX_SIZE = 120

    def new(self):
        self.gPodderChannel.set_title( self.channel.title)
        self.entryTitle.set_text( self.channel.title)
        self.labelURL.set_text(self.channel.url)
        self.cbSkipFeedUpdate.set_active(self.channel.pause_subscription)
        self.cbEnableDeviceSync.set_active(self.channel.sync_to_mp3_player)

        self.section_list = gtk.ListStore(str)
        active_index = 0
        for index, section in enumerate(sorted(self.sections)):
            self.section_list.append([section])
            if section == self.channel.section:
                active_index = index
        self.combo_section.set_model(self.section_list)
        cell_renderer = gtk.CellRendererText()
        self.combo_section.pack_start(cell_renderer)
        self.combo_section.add_attribute(cell_renderer, 'text', 0)
        self.combo_section.set_active(active_index)

        self.strategy_list = gtk.ListStore(str, int)
        active_index = 0
        for index, (checked, strategy_id, strategy) in \
            enumerate(self.channel.get_download_strategies()):
            self.strategy_list.append([strategy, strategy_id])
            if checked:
                active_index = index
        self.combo_strategy.set_model(self.strategy_list)
        cell_renderer = gtk.CellRendererText()
        self.combo_strategy.pack_start(cell_renderer)
        self.combo_strategy.add_attribute(cell_renderer, 'text', 0)
        self.combo_strategy.set_active(active_index)

        self.LabelDownloadTo.set_text( self.channel.save_dir)
        self.LabelWebsite.set_text( self.channel.link)

        if self.channel.auth_username:
            self.FeedUsername.set_text( self.channel.auth_username)
        if self.channel.auth_password:
            self.FeedPassword.set_text( self.channel.auth_password)

        self.cover_downloader.register('cover-available', self.cover_download_finished)
        self.cover_downloader.request_cover(self.channel)

        # Hide the website button if we don't have a valid URL
        if not self.channel.link:
            self.btn_website.hide_all()

        b = gtk.TextBuffer()
        b.set_text( self.channel.description)
        self.channel_description.set_buffer( b)

        #Add Drag and Drop Support
        flags = gtk.DEST_DEFAULT_ALL
        targets = [('text/uri-list', 0, 2), ('text/plain', 0, 4)]
        actions = gtk.gdk.ACTION_DEFAULT | gtk.gdk.ACTION_COPY
        self.imgCover.drag_dest_set(flags, targets, actions)
        self.imgCover.connect('drag_data_received', self.drag_data_received)
        border = 6
        self.imgCover.set_size_request(*((self.MAX_SIZE+border*2,)*2))
        self.imgCoverEventBox.connect('button-press-event',
                self.on_cover_popup_menu)

    def on_button_add_section_clicked(self, widget):
        text = self.show_text_edit_dialog(_('Add section'), _('New section:'),
            affirmative_text=gtk.STOCK_ADD)

        if text is not None:
            for index, (section,) in enumerate(self.section_list):
                if text == section:
                    self.combo_section.set_active(index)
                    return

            self.section_list.append([text])
            self.combo_section.set_active(len(self.section_list)-1)

    def on_cover_popup_menu(self, widget, event):
        if event.button != 3:
            return

        menu = gtk.Menu()

        item = gtk.ImageMenuItem(gtk.STOCK_OPEN)
        item.connect('activate', self.on_btnDownloadCover_clicked)
        menu.append(item)

        item = gtk.ImageMenuItem(gtk.STOCK_REFRESH)
        item.connect('activate', self.on_btnClearCover_clicked)
        menu.append(item)

        menu.show_all()
        menu.popup(None, None, None, event.button, event.time, None)

    def on_btn_website_clicked(self, widget):
        util.open_website(self.channel.link)

    def on_btnDownloadCover_clicked(self, widget):
        dlg = gtk.FileChooserDialog(title=_('Select new podcast cover artwork'), parent=self.gPodderChannel, action=gtk.FILE_CHOOSER_ACTION_OPEN)
        dlg.add_button(gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL)
        dlg.add_button(gtk.STOCK_OPEN, gtk.RESPONSE_OK)

        if dlg.run() == gtk.RESPONSE_OK:
            url = dlg.get_uri()
            self.clear_cover_cache(self.channel.url)
            self.cover_downloader.replace_cover(self.channel, custom_url=url)

        dlg.destroy()

    def on_btnClearCover_clicked(self, widget):
        self.clear_cover_cache(self.channel.url)
        self.cover_downloader.replace_cover(self.channel, custom_url=False)

    def cover_download_finished(self, channel, pixbuf):
        def set_cover(channel, pixbuf):
            if self.channel == channel:
                self.imgCover.set_from_pixbuf(self.scale_pixbuf(pixbuf))
                self.gPodderChannel.show()

        util.idle_add(set_cover, channel, pixbuf)

    def drag_data_received( self, widget, content, x, y, sel, ttype, time):
        files = sel.data.strip().split('\n')
        if len(files) != 1:
            self.show_message( _('You can only drop a single image or URL here.'), _('Drag and drop'))
            return

        file = files[0]

        if file.startswith('file://') or file.startswith('http://'):
            self.clear_cover_cache(self.channel.url)
            self.cover_downloader.replace_cover(self.channel, custom_url=file)
            return

        self.show_message( _('You can only drop local files and http:// URLs here.'), _('Drag and drop'))

    def on_gPodderChannel_destroy(self, widget, *args):
        self.cover_downloader.unregister('cover-available', self.cover_download_finished)

    def scale_pixbuf(self, pixbuf):

        # Resize if width is too large
        if pixbuf.get_width() > self.MAX_SIZE:
            f = float(self.MAX_SIZE)/pixbuf.get_width()
            (width, height) = (int(pixbuf.get_width()*f), int(pixbuf.get_height()*f))
            pixbuf = pixbuf.scale_simple(width, height, gtk.gdk.INTERP_BILINEAR)

        # Resize if height is too large
        if pixbuf.get_height() > self.MAX_SIZE:
            f = float(self.MAX_SIZE)/pixbuf.get_height()
            (width, height) = (int(pixbuf.get_width()*f), int(pixbuf.get_height()*f))
            pixbuf = pixbuf.scale_simple(width, height, gtk.gdk.INTERP_BILINEAR)

        return pixbuf

    def on_btnOK_clicked(self, widget, *args):
        self.channel.pause_subscription = self.cbSkipFeedUpdate.get_active()
        self.channel.sync_to_mp3_player = self.cbEnableDeviceSync.get_active()
        self.channel.rename(self.entryTitle.get_text())
        self.channel.auth_username = self.FeedUsername.get_text().strip()
        self.channel.auth_password = self.FeedPassword.get_text()

        self.clear_cover_cache(self.channel.url)
        self.cover_downloader.request_cover(self.channel)

        new_section = self.section_list[self.combo_section.get_active()][0]
        if self.channel.section != new_section:
            self.channel.section = new_section
            section_changed = True
        else:
            section_changed = False

        new_strategy = self.strategy_list[self.combo_strategy.get_active()][1]
        self.channel.set_download_strategy(new_strategy)

        self.channel.save()

        self.gPodderChannel.destroy()

        self.update_podcast_list_model(selected=True,
                sections_changed=section_changed)


########NEW FILE########
__FILENAME__ = deviceplaylist
# -*- coding: utf-8 -*-
#
# gPodder - A media aggregator and podcast client
# Copyright (c) 2005-2011 Thomas Perl and the gPodder Team
#
# gPodder is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# gPodder is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#

import os
import gpodder

_ = gpodder.gettext

from gpodder import util

import logging
logger = logging.getLogger(__name__)

class gPodderDevicePlaylist(object):
    def __init__(self, config, playlist_name):
        self._config=config
        self.linebreak = '\r\n'
        self.playlist_file=util.sanitize_filename(playlist_name + '.m3u')
        self.playlist_folder = os.path.join(self._config.device_sync.device_folder, self._config.device_sync.playlists.folder)
        self.mountpoint = util.find_mount_point(util.sanitize_encoding(self.playlist_folder))
        if self.mountpoint == '/':
            self.mountpoint = self.playlist_folder
            logger.warning('MP3 player resides on / - using %s as MP3 player root', self.mountpoint)
        self.playlist_absolute_filename=os.path.join(self.playlist_folder, self.playlist_file)

    def build_extinf(self, filename):
#TO DO: Windows playlists
#        if self._config.mp3_player_playlist_win_path:
#            filename = filename.replace('\\', os.sep)

#        # rebuild the whole filename including the mountpoint
#        if self._config.device_sync.playlist_absolute_path:
#            absfile = os.path.join(self.mountpoint,filename)
#        else: #TODO: Test rel filenames
#            absfile = util.rel2abs(filename, os.path.dirname(self.playlist_file))

        # fallback: use the basename of the file
        (title, extension) = os.path.splitext(os.path.basename(filename))

        return "#EXTINF:0,%s%s" % (title.strip(), self.linebreak)

    def read_m3u(self):
        """
        read all files from the existing playlist
        """
        tracks = []
        logger.info("Read data from the playlistfile %s" % self.playlist_absolute_filename)
        if os.path.exists(self.playlist_absolute_filename):
            for line in open(self.playlist_absolute_filename, 'r'):
                if not line.startswith('#EXT'):
                    tracks.append(line.rstrip('\r\n'))
        return tracks

    def get_filename_for_playlist(self, episode):
        """
        get the filename for the given episode for the playlist
        """
        filename_base = util.sanitize_filename(episode.sync_filename(
            self._config.device_sync.custom_sync_name_enabled,
            self._config.device_sync.custom_sync_name),
            self._config.device_sync.max_filename_length)
        filename = filename_base + os.path.splitext(episode.local_filename(create=False))[1].lower()
        return filename

    def get_absolute_filename_for_playlist(self, episode):
        """
        get the filename including full path for the given episode for the playlist
        """
        filename = self.get_filename_for_playlist(episode)
        if self._config.device_sync.one_folder_per_podcast:
            filename = os.path.join(util.sanitize_filename(episode.channel.title), filename)
        if self._config.device_sync.playlist.absolute_path:
            filename = os.path.join(util.relpath(self.mountpoint, self._config.device_sync.device_folder), filename)
        return filename

    def write_m3u(self, episodes):
        """
        write the list into the playlist on the device
        """
        logger.info('Writing playlist file: %s', self.playlist_file)
        if not util.make_directory(self.playlist_folder):
            raise IOError(_('Folder %s could not be created.') % self.playlist_folder, _('Error writing playlist'))
        else:
            fp = open(os.path.join(self.playlist_folder, self.playlist_file), 'w')
            fp.write('#EXTM3U%s' % self.linebreak)
            for current_episode in episodes:
                filename_base = util.sanitize_filename(current_episode.sync_filename(
                    self._config.device_sync.custom_sync_name_enabled,
                    self._config.device_sync.custom_sync_name),
                    self._config.device_sync.max_filename_length)
                filename = filename_base + os.path.splitext(current_episode.local_filename(create=False))[1].lower()
                filename = self.get_filename_for_playlist(current_episode)
                fp.write(self.build_extinf(filename))
                filename = self.get_absolute_filename_for_playlist(current_episode)
                fp.write(filename)
                fp.write(self.linebreak)
            fp.close()


########NEW FILE########
__FILENAME__ = episodeselector
# -*- coding: utf-8 -*-
#
# gPodder - A media aggregator and podcast client
# Copyright (c) 2005-2014 Thomas Perl and the gPodder Team
#
# gPodder is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# gPodder is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#

import gtk
import pango
import cgi

import gpodder

_ = gpodder.gettext
N_ = gpodder.ngettext

from gpodder import util

from gpodder.gtkui.interface.common import BuilderWidget
from gpodder.gtkui.interface.common import TreeViewHelper

class gPodderEpisodeSelector(BuilderWidget):
    """Episode selection dialog

    Optional keyword arguments that modify the behaviour of this dialog:

      - callback: Function that takes 1 parameter which is a list of
                  the selected episodes (or empty list when none selected)
      - remove_callback: Function that takes 1 parameter which is a list
                         of episodes that should be "removed" (see below)
                         (default is None, which means remove not possible)
      - remove_action: Label for the "remove" action (default is "Remove")
      - remove_finished: Callback after all remove callbacks have finished
                         (default is None, also depends on remove_callback)
                         It will get a list of episode URLs that have been
                         removed, so the main UI can update those
      - episodes: List of episodes that are presented for selection
      - selected: (optional) List of boolean variables that define the
                  default checked state for the given episodes
      - selected_default: (optional) The default boolean value for the
                          checked state if no other value is set
                          (default is False)
      - columns: List of (name, sort_name, sort_type, caption) pairs for the
                 columns, the name is the attribute name of the episode to be 
                 read from each episode object.  The sort name is the 
                 attribute name of the episode to be used to sort this column.
                 If the sort_name is None it will use the attribute name for
                 sorting.  The sort type is the type of the sort column.
                 The caption attribute is the text that appear as column caption
                 (default is [('title_markup', None, None, 'Episode'),])
      - title: (optional) The title of the window + heading
      - instructions: (optional) A one-line text describing what the 
                      user should select / what the selection is for
      - stock_ok_button: (optional) Will replace the "OK" button with
                         another GTK+ stock item to be used for the
                         affirmative button of the dialog (e.g. can 
                         be gtk.STOCK_DELETE when the episodes to be
                         selected will be deleted after closing the 
                         dialog)
      - selection_buttons: (optional) A dictionary with labels as 
                           keys and callbacks as values; for each
                           key a button will be generated, and when
                           the button is clicked, the callback will
                           be called for each episode and the return
                           value of the callback (True or False) will
                           be the new selected state of the episode
      - size_attribute: (optional) The name of an attribute of the 
                        supplied episode objects that can be used to
                        calculate the size of an episode; set this to
                        None if no total size calculation should be
                        done (in cases where total size is useless)
                        (default is 'file_size')
      - tooltip_attribute: (optional) The name of an attribute of
                           the supplied episode objects that holds
                           the text for the tooltips when hovering
                           over an episode (default is 'description')
                           
    """
    COLUMN_INDEX = 0
    COLUMN_TOOLTIP = 1
    COLUMN_TOGGLE = 2
    COLUMN_ADDITIONAL = 3

    def new( self):
        self._config.connect_gtk_window(self.gPodderEpisodeSelector, 'episode_selector', True)
        if not hasattr( self, 'callback'):
            self.callback = None

        if not hasattr(self, 'remove_callback'):
            self.remove_callback = None

        if not hasattr(self, 'remove_action'):
            self.remove_action = _('Remove')

        if not hasattr(self, 'remove_finished'):
            self.remove_finished = None

        if not hasattr( self, 'episodes'):
            self.episodes = []

        if not hasattr( self, 'size_attribute'):
            self.size_attribute = 'file_size'

        if not hasattr(self, 'tooltip_attribute'):
            self.tooltip_attribute = 'description'

        if not hasattr( self, 'selection_buttons'):
            self.selection_buttons = {}

        if not hasattr( self, 'selected_default'):
            self.selected_default = False

        if not hasattr( self, 'selected'):
            self.selected = [self.selected_default]*len(self.episodes)

        if len(self.selected) < len(self.episodes):
            self.selected += [self.selected_default]*(len(self.episodes)-len(self.selected))

        if not hasattr( self, 'columns'):
            self.columns = (('title_markup', None, None, _('Episode')),)

        if hasattr(self, 'title'):
            self.gPodderEpisodeSelector.set_title(self.title)

        if hasattr( self, 'instructions'):
            self.labelInstructions.set_text( self.instructions)
            self.labelInstructions.show_all()

        if hasattr(self, 'stock_ok_button'):
            if self.stock_ok_button == 'gpodder-download':
                self.btnOK.set_image(gtk.image_new_from_stock(gtk.STOCK_GO_DOWN, gtk.ICON_SIZE_BUTTON))
                self.btnOK.set_label(_('Download'))
            else:
                self.btnOK.set_label(self.stock_ok_button)
                self.btnOK.set_use_stock(True)

        # check/uncheck column
        toggle_cell = gtk.CellRendererToggle()
        toggle_cell.connect( 'toggled', self.toggle_cell_handler)
        toggle_column = gtk.TreeViewColumn('', toggle_cell, active=self.COLUMN_TOGGLE)
        toggle_column.set_clickable(True)
        self.treeviewEpisodes.append_column(toggle_column)
        
        next_column = self.COLUMN_ADDITIONAL
        for name, sort_name, sort_type, caption in self.columns:
            renderer = gtk.CellRendererText()
            if next_column < self.COLUMN_ADDITIONAL + 1:
                renderer.set_property('ellipsize', pango.ELLIPSIZE_END)
            column = gtk.TreeViewColumn(caption, renderer, markup=next_column)
            column.set_clickable(False)
            column.set_resizable( True)
            # Only set "expand" on the first column
            if next_column < self.COLUMN_ADDITIONAL + 1:
                column.set_expand(True)
            if sort_name is not None:
                column.set_sort_column_id(next_column+1)
            else:
                column.set_sort_column_id(next_column)
            self.treeviewEpisodes.append_column( column)
            next_column += 1
            
            if sort_name is not None:
                # add the sort column
                column = gtk.TreeViewColumn()
                column.set_clickable(False)
                column.set_visible(False)
                self.treeviewEpisodes.append_column( column)
                next_column += 1

        column_types = [ int, str, bool ]
        # add string column type plus sort column type if it exists
        for name, sort_name, sort_type, caption in self.columns:
            column_types.append(str)
            if sort_name is not None:
                column_types.append(sort_type)
        self.model = gtk.ListStore( *column_types)

        tooltip = None
        for index, episode in enumerate( self.episodes):
            if self.tooltip_attribute is not None:
                try:
                    tooltip = getattr(episode, self.tooltip_attribute)
                except:
                    tooltip = None
            row = [ index, tooltip, self.selected[index] ]
            for name, sort_name, sort_type, caption in self.columns:
                if not hasattr(episode, name):
                    row.append(None)
                else:
                    row.append(getattr( episode, name))
                    
                if sort_name is not None:
                    if not hasattr(episode, sort_name):
                        row.append(None)
                    else:
                        row.append(getattr( episode, sort_name))
            self.model.append( row)

        if self.remove_callback is not None:
            self.btnRemoveAction.show()
            self.btnRemoveAction.set_label(self.remove_action)

        # connect to tooltip signals
        if self.tooltip_attribute is not None:
            try:
                self.treeviewEpisodes.set_property('has-tooltip', True)
                self.treeviewEpisodes.connect('query-tooltip', self.treeview_episodes_query_tooltip)
            except:
                pass
        self.last_tooltip_episode = None
        self.episode_list_can_tooltip = True

        self.treeviewEpisodes.connect('button-press-event', self.treeview_episodes_button_pressed)
        self.treeviewEpisodes.connect('popup-menu', self.treeview_episodes_button_pressed)
        self.treeviewEpisodes.set_rules_hint( True)
        self.treeviewEpisodes.set_model( self.model)
        self.treeviewEpisodes.columns_autosize()

        # Focus the toggle column for Tab-focusing (bug 503)
        path, column = self.treeviewEpisodes.get_cursor()
        if path is not None:
            self.treeviewEpisodes.set_cursor(path, toggle_column)

        self.calculate_total_size()

    def treeview_episodes_query_tooltip(self, treeview, x, y, keyboard_tooltip, tooltip):
        # With get_bin_window, we get the window that contains the rows without
        # the header. The Y coordinate of this window will be the height of the
        # treeview header. This is the amount we have to subtract from the
        # event's Y coordinate to get the coordinate to pass to get_path_at_pos
        (x_bin, y_bin) = treeview.get_bin_window().get_position()
        y -= x_bin
        y -= y_bin
        (path, column, rx, ry) = treeview.get_path_at_pos(x, y) or (None,)*4

        if not self.episode_list_can_tooltip or column != treeview.get_columns()[1]:
            self.last_tooltip_episode = None
            return False

        if path is not None:
            model = treeview.get_model()
            iter = model.get_iter(path)
            index = model.get_value(iter, self.COLUMN_INDEX)
            description = model.get_value(iter, self.COLUMN_TOOLTIP)
            if self.last_tooltip_episode is not None and self.last_tooltip_episode != index:
                self.last_tooltip_episode = None
                return False
            self.last_tooltip_episode = index

            description = util.remove_html_tags(description)
            # Bug 1825: make sure description is a unicode string,
            # so it may be cut correctly on UTF-8 char boundaries
            description = util.convert_bytes(description)
            if description is not None:
                if len(description) > 400:
                    description = description[:398]+'[...]'
                tooltip.set_text(description)
                return True
            else:
                return False

        self.last_tooltip_episode = None
        return False

    def treeview_episodes_button_pressed(self, treeview, event=None):
        if event is None or event.button == 3:
            menu = gtk.Menu()

            if len(self.selection_buttons):
                for label in self.selection_buttons:
                    item = gtk.MenuItem(label)
                    item.connect('activate', self.custom_selection_button_clicked, label)
                    menu.append(item)
                menu.append(gtk.SeparatorMenuItem())

            item = gtk.MenuItem(_('Select all'))
            item.connect('activate', self.on_btnCheckAll_clicked)
            menu.append(item)

            item = gtk.MenuItem(_('Select none'))
            item.connect('activate', self.on_btnCheckNone_clicked)
            menu.append(item)

            menu.show_all()
            # Disable tooltips while we are showing the menu, so 
            # the tooltip will not appear over the menu
            self.episode_list_can_tooltip = False
            menu.connect('deactivate', lambda menushell: self.episode_list_allow_tooltips())
            if event is None:
                func = TreeViewHelper.make_popup_position_func(treeview)
                menu.popup(None, None, func, 3, 0)
            else:
                menu.popup(None, None, None, event.button, event.time)

            return True

    def episode_list_allow_tooltips(self):
        self.episode_list_can_tooltip = True

    def calculate_total_size( self):
        if self.size_attribute is not None:
            (total_size, count) = (0, 0)
            for episode in self.get_selected_episodes():
                try:
                    total_size += int(getattr( episode, self.size_attribute))
                    count += 1
                except:
                    pass

            text = []
            if count == 0: 
                text.append(_('Nothing selected'))
            text.append(N_('%(count)d episode', '%(count)d episodes', count) % {'count':count})
            if total_size > 0: 
                text.append(_('size: %s') % util.format_filesize(total_size))
            self.labelTotalSize.set_text(', '.join(text))
            self.btnOK.set_sensitive(count>0)
            self.btnRemoveAction.set_sensitive(count>0)
            if count > 0:
                self.btnCancel.set_label(gtk.STOCK_CANCEL)
            else:
                self.btnCancel.set_label(gtk.STOCK_CLOSE)
        else:
            self.btnOK.set_sensitive(False)
            self.btnRemoveAction.set_sensitive(False)
            for index, row in enumerate(self.model):
                if self.model.get_value(row.iter, self.COLUMN_TOGGLE) == True:
                    self.btnOK.set_sensitive(True)
                    self.btnRemoveAction.set_sensitive(True)
                    break
            self.labelTotalSize.set_text('')

    def toggle_cell_handler( self, cell, path):
        model = self.treeviewEpisodes.get_model()
        model[path][self.COLUMN_TOGGLE] = not model[path][self.COLUMN_TOGGLE]

        self.calculate_total_size()

    def custom_selection_button_clicked(self, button, label):
        callback = self.selection_buttons[label]

        for index, row in enumerate( self.model):
            new_value = callback( self.episodes[index])
            self.model.set_value( row.iter, self.COLUMN_TOGGLE, new_value)

        self.calculate_total_size()

    def on_btnCheckAll_clicked( self, widget):
        for row in self.model:
            self.model.set_value( row.iter, self.COLUMN_TOGGLE, True)

        self.calculate_total_size()

    def on_btnCheckNone_clicked( self, widget):
        for row in self.model:
            self.model.set_value( row.iter, self.COLUMN_TOGGLE, False)

        self.calculate_total_size()

    def on_remove_action_activate(self, widget):
        episodes = self.get_selected_episodes(remove_episodes=True)

        urls = []
        for episode in episodes:
            urls.append(episode.url)
            self.remove_callback(episode)

        if self.remove_finished is not None:
            self.remove_finished(urls)
        self.calculate_total_size()

        # Close the window when there are no episodes left
        model = self.treeviewEpisodes.get_model()
        if model.get_iter_first() is None:
            self.on_btnCancel_clicked(None)

    def on_row_activated(self, treeview, path, view_column):
        model = treeview.get_model()
        iter = model.get_iter(path)
        value = model.get_value(iter, self.COLUMN_TOGGLE)
        model.set_value(iter, self.COLUMN_TOGGLE, not value)

        self.calculate_total_size()

    def get_selected_episodes( self, remove_episodes=False):
        selected_episodes = []

        for index, row in enumerate( self.model):
            if self.model.get_value( row.iter, self.COLUMN_TOGGLE) == True:
                selected_episodes.append( self.episodes[self.model.get_value( row.iter, self.COLUMN_INDEX)])

        if remove_episodes:
            for episode in selected_episodes:
                index = self.episodes.index(episode)
                iter = self.model.get_iter_first()
                while iter is not None:
                    if self.model.get_value(iter, self.COLUMN_INDEX) == index:
                        self.model.remove(iter)
                        break
                    iter = self.model.iter_next(iter)

        return selected_episodes

    def on_btnOK_clicked( self, widget):
        self.gPodderEpisodeSelector.destroy()
        if self.callback is not None:
            self.callback( self.get_selected_episodes())

    def on_btnCancel_clicked( self, widget):
        self.gPodderEpisodeSelector.destroy()
        if self.callback is not None:
            self.callback([])


########NEW FILE########
__FILENAME__ = podcastdirectory
# -*- coding: utf-8 -*-
#
# gPodder - A media aggregator and podcast client
# Copyright (c) 2005-2014 Thomas Perl and the gPodder Team
#
# gPodder is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# gPodder is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#

import gtk
import pango
import urllib
import os.path

import gpodder

_ = gpodder.gettext

from gpodder import util
from gpodder import opml
from gpodder import youtube
from gpodder import my

from gpodder.gtkui.opml import OpmlListModel

from gpodder.gtkui.interface.common import BuilderWidget


class gPodderPodcastDirectory(BuilderWidget):
    def new(self):
        if hasattr(self, 'custom_title'):
            self.gPodderPodcastDirectory.set_title(self.custom_title)

        if hasattr(self, 'hide_url_entry'):
            self.hboxOpmlUrlEntry.hide_all()
            new_parent = self.notebookChannelAdder.get_parent()
            new_parent.remove(self.notebookChannelAdder)
            self.vboxOpmlImport.reparent(new_parent)

        if not hasattr(self, 'add_podcast_list'):
            self.add_podcast_list = None

        self.setup_treeview(self.treeviewChannelChooser)
        self.setup_treeview(self.treeviewTopPodcastsChooser)
        self.setup_treeview(self.treeviewYouTubeChooser)

        self.notebookChannelAdder.connect('switch-page', lambda a, b, c: self.on_change_tab(c))

    def on_entryURL_changed(self, entry):
        url = entry.get_text()
        if self.is_search_term(url):
            self.btnDownloadOpml.set_label(_('Search'))
        else:
            self.btnDownloadOpml.set_label(_('Download'))

    def setup_treeview(self, tv):
        togglecell = gtk.CellRendererToggle()
        togglecell.set_property( 'activatable', True)
        togglecell.connect( 'toggled', self.callback_edited)
        togglecolumn = gtk.TreeViewColumn( '', togglecell, active=OpmlListModel.C_SELECTED)
        togglecolumn.set_min_width(40)

        titlecell = gtk.CellRendererText()
        titlecell.set_property('ellipsize', pango.ELLIPSIZE_END)
        titlecolumn = gtk.TreeViewColumn(_('Podcast'), titlecell, markup=OpmlListModel.C_DESCRIPTION_MARKUP)

        for itemcolumn in (togglecolumn, titlecolumn):
            tv.append_column(itemcolumn)

    def callback_edited( self, cell, path):
        model = self.get_treeview().get_model()
        model[path][OpmlListModel.C_SELECTED] = not model[path][OpmlListModel.C_SELECTED]
        self.btnOK.set_sensitive(bool(len(self.get_selected_channels())))

    def get_selected_channels(self, tab=None):
        channels = []

        model = self.get_treeview(tab).get_model()
        if model is not None:
            for row in model:
                if row[OpmlListModel.C_SELECTED]:
                    channels.append((row[OpmlListModel.C_TITLE],
                        row[OpmlListModel.C_URL]))

        return channels

    def on_change_tab(self, tab):
        self.btnOK.set_sensitive( bool(len(self.get_selected_channels(tab))))

    def thread_finished(self, model, tab=0):
        if tab == 1:
            tv = self.treeviewTopPodcastsChooser
        elif tab == 2:
            tv = self.treeviewYouTubeChooser
            self.entryYoutubeSearch.set_sensitive(True)
            self.btnSearchYouTube.set_sensitive(True)
            self.btnOK.set_sensitive(False)
        else:
            tv = self.treeviewChannelChooser
            self.btnDownloadOpml.set_sensitive(True)
            self.entryURL.set_sensitive(True)

        tv.set_model(model)
        tv.set_sensitive(True)

    def is_search_term(self, url):
        return ('://' not in url and not os.path.exists(url))

    def thread_func(self, tab=0):
        if tab == 1:
            model = OpmlListModel(opml.Importer(my.TOPLIST_OPML))
            if len(model) == 0:
                self.notification(_('The specified URL does not provide any valid OPML podcast items.'), _('No feeds found'))
        elif tab == 2:
            model = OpmlListModel(youtube.find_youtube_channels(self.entryYoutubeSearch.get_text()))
            if len(model) == 0:
                self.notification(_('There are no YouTube channels that would match this query.'), _('No channels found'))
        else:
            url = self.entryURL.get_text()
            if self.is_search_term(url):
                url = 'http://gpodder.net/search.opml?q=' + urllib.quote(url)
            model = OpmlListModel(opml.Importer(url))
            if len(model) == 0:
                self.notification(_('The specified URL does not provide any valid OPML podcast items.'), _('No feeds found'))

        util.idle_add(self.thread_finished, model, tab)
    
    def download_opml_file(self, url):
        self.entryURL.set_text(url)
        self.btnDownloadOpml.set_sensitive(False)
        self.entryURL.set_sensitive(False)
        self.btnOK.set_sensitive(False)
        self.treeviewChannelChooser.set_sensitive(False)
        util.run_in_background(self.thread_func)
        util.run_in_background(lambda: self.thread_func(1))

    def select_all( self, value ):
        enabled = False
        model = self.get_treeview().get_model()
        if model is not None:
            for row in model:
                row[OpmlListModel.C_SELECTED] = value
                if value:
                    enabled = True
        self.btnOK.set_sensitive(enabled)

    def on_gPodderPodcastDirectory_destroy(self, widget, *args):
        pass

    def on_btnDownloadOpml_clicked(self, widget, *args):
        self.download_opml_file(self.entryURL.get_text())

    def on_btnSearchYouTube_clicked(self, widget, *args):
        self.entryYoutubeSearch.set_sensitive(False)
        self.treeviewYouTubeChooser.set_sensitive(False)
        self.btnSearchYouTube.set_sensitive(False)
        util.run_in_background(lambda: self.thread_func(2))

    def on_btnSelectAll_clicked(self, widget, *args):
        self.select_all(True)
    
    def on_btnSelectNone_clicked(self, widget, *args):
        self.select_all(False)

    def on_btnOK_clicked(self, widget, *args):
        channels = self.get_selected_channels()
        self.gPodderPodcastDirectory.destroy()

        # add channels that have been selected
        if self.add_podcast_list is not None:
            self.add_podcast_list(channels)

    def on_btnCancel_clicked(self, widget, *args):
        self.gPodderPodcastDirectory.destroy()

    def on_entryYoutubeSearch_key_press_event(self, widget, event):
        if event.keyval == gtk.keysyms.Return:
            self.on_btnSearchYouTube_clicked(widget)

    def get_treeview(self, tab=None):
        if tab is None:
            tab = self.notebookChannelAdder.get_current_page()

        if tab == 0:
            return self.treeviewChannelChooser
        elif tab == 1:
            return self.treeviewTopPodcastsChooser
        else:
            return self.treeviewYouTubeChooser


########NEW FILE########
__FILENAME__ = preferences
# -*- coding: utf-8 -*-
#
# gPodder - A media aggregator and podcast client
# Copyright (c) 2005-2014 Thomas Perl and the gPodder Team
#
# gPodder is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# gPodder is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#

import gtk
import pango
import cgi
import urlparse

import logging
logger = logging.getLogger(__name__)

import gpodder

_ = gpodder.gettext
N_ = gpodder.ngettext

from gpodder import util
from gpodder import youtube

from gpodder.gtkui.interface.common import BuilderWidget
from gpodder.gtkui.interface.common import TreeViewHelper
from gpodder.gtkui.interface.configeditor import gPodderConfigEditor

from gpodder.gtkui.desktopfile import PlayerListModel

class NewEpisodeActionList(gtk.ListStore):
    C_CAPTION, C_AUTO_DOWNLOAD = range(2)

    ACTION_NONE, ACTION_ASK, ACTION_MINIMIZED, ACTION_ALWAYS = range(4)

    def __init__(self, config):
        gtk.ListStore.__init__(self, str, str)
        self._config = config
        self.append((_('Do nothing'), 'ignore'))
        self.append((_('Show episode list'), 'show'))
        self.append((_('Add to download list'), 'queue'))
        self.append((_('Download immediately'), 'download'))

    def get_index(self):
        for index, row in enumerate(self):
            if self._config.auto_download == row[self.C_AUTO_DOWNLOAD]:
                return index

        return 1 # Some sane default

    def set_index(self, index):
        self._config.auto_download = self[index][self.C_AUTO_DOWNLOAD]

class DeviceTypeActionList(gtk.ListStore):
    C_CAPTION, C_DEVICE_TYPE = range(2)

    def __init__(self, config):
        gtk.ListStore.__init__(self, str, str)
        self._config = config
        self.append((_('None'), 'none'))
        self.append((_('iPod'), 'ipod'))        
        self.append((_('Filesystem-based'), 'filesystem'))

    def get_index(self):
        for index, row in enumerate(self):
            if self._config.device_sync.device_type == row[self.C_DEVICE_TYPE]:
                return index
        return 0 # Some sane default

    def set_index(self, index):
        self._config.device_sync.device_type = self[index][self.C_DEVICE_TYPE]


class OnSyncActionList(gtk.ListStore):
    C_CAPTION, C_ON_SYNC_DELETE, C_ON_SYNC_MARK_PLAYED = range(3)
    ACTION_NONE, ACTION_ASK, ACTION_MINIMIZED, ACTION_ALWAYS = range(4)

    def __init__(self, config):
        gtk.ListStore.__init__(self, str, bool, bool)
        self._config = config
        self.append((_('Do nothing'), False, False))
        self.append((_('Mark as played'), False, True))
        self.append((_('Delete from gPodder'), True, False))

    def get_index(self):
        for index, row in enumerate(self):
            if (self._config.device_sync.after_sync.delete_episodes and
                    row[self.C_ON_SYNC_DELETE]):
                return index
            if (self._config.device_sync.after_sync.mark_episodes_played and
                    row[self.C_ON_SYNC_MARK_PLAYED] and not
                    self._config.device_sync.after_sync.delete_episodes):
                return index
        return 0 # Some sane default

    def set_index(self, index):
        self._config.device_sync.after_sync.delete_episodes = self[index][self.C_ON_SYNC_DELETE]
        self._config.device_sync.after_sync.mark_episodes_played = self[index][self.C_ON_SYNC_MARK_PLAYED]



class gPodderFlattrSignIn(BuilderWidget):

    def new(self):
        import webkit

        self.web = webkit.WebView()
        self.web.connect('resource-request-starting', self.on_web_request)
        self.main_window.connect('destroy', self.set_flattr_preferences)

        auth_url = self.flattr.get_auth_url()
        logger.info(auth_url)
        self.web.open(auth_url)

        self.scrolledwindow_web.add(self.web)
        self.web.show()

    def on_web_request(self, web_view, web_frame, web_resource, request, response):
        uri = request.get_uri()
        if uri.startswith(self.flattr.CALLBACK):
            if not self.flattr.process_retrieved_code(uri):
                self.show_message(query['error_description'][0], _('Error'),
                        important=True)

            # Destroy the window later
            util.idle_add(self.main_window.destroy)

    def on_btn_close_clicked(self, widget):
        util.idle_add(self.main_window.destroy)

class VideoFormatList(gtk.ListStore):
    C_CAPTION, C_ID = range(2)

    def __init__(self, config):
        gtk.ListStore.__init__(self, str, int)
        self._config = config

        if self._config.youtube.preferred_fmt_ids:
            caption = _('Custom (%(format_ids)s)') % {
                    'format_ids': ', '.join(self.custom_format_ids),
            }
            self.append((caption, -1))
        else:
            for id, (fmt_id, path, description) in youtube.formats:
                self.append((description, id))

    def get_index(self):
        for index, row in enumerate(self):
            if self._config.youtube.preferred_fmt_id == row[self.C_ID]:
                return index
        return 0

    def set_index(self, index):
        value = self[index][self.C_ID]
        if value > 0:
            self._config.youtube.preferred_fmt_id = value

class gPodderPreferences(BuilderWidget):
    C_TOGGLE, C_LABEL, C_EXTENSION, C_SHOW_TOGGLE = range(4)

    def new(self):
        for cb in (self.combo_audio_player_app, self.combo_video_player_app):
            cellrenderer = gtk.CellRendererPixbuf()
            cb.pack_start(cellrenderer, False)
            cb.add_attribute(cellrenderer, 'pixbuf', PlayerListModel.C_ICON)
            cellrenderer = gtk.CellRendererText()
            cellrenderer.set_property('ellipsize', pango.ELLIPSIZE_END)
            cb.pack_start(cellrenderer, True)
            cb.add_attribute(cellrenderer, 'markup', PlayerListModel.C_NAME)
            cb.set_row_separator_func(PlayerListModel.is_separator)

        self.audio_player_model = self.user_apps_reader.get_model('audio')
        self.combo_audio_player_app.set_model(self.audio_player_model)
        index = self.audio_player_model.get_index(self._config.player)
        self.combo_audio_player_app.set_active(index)

        self.video_player_model = self.user_apps_reader.get_model('video')
        self.combo_video_player_app.set_model(self.video_player_model)
        index = self.video_player_model.get_index(self._config.videoplayer)
        self.combo_video_player_app.set_active(index)

        self.preferred_video_format_model = VideoFormatList(self._config)
        self.combobox_preferred_video_format.set_model(self.preferred_video_format_model)
        cellrenderer = gtk.CellRendererText()
        self.combobox_preferred_video_format.pack_start(cellrenderer, True)
        self.combobox_preferred_video_format.add_attribute(cellrenderer, 'text', self.preferred_video_format_model.C_CAPTION)
        self.combobox_preferred_video_format.set_active(self.preferred_video_format_model.get_index())

        self._config.connect_gtk_togglebutton('podcast_list_view_all',
                                              self.checkbutton_show_all_episodes)
        self._config.connect_gtk_togglebutton('podcast_list_sections',
                                              self.checkbutton_podcast_sections)

        self.update_interval_presets = [0, 10, 30, 60, 2*60, 6*60, 12*60]
        adjustment_update_interval = self.hscale_update_interval.get_adjustment()
        adjustment_update_interval.upper = len(self.update_interval_presets)-1
        if self._config.auto_update_frequency in self.update_interval_presets:
            index = self.update_interval_presets.index(self._config.auto_update_frequency)
            self.hscale_update_interval.set_value(index)
        else:
            # Patch in the current "custom" value into the mix
            self.update_interval_presets.append(self._config.auto_update_frequency)
            self.update_interval_presets.sort()

            adjustment_update_interval.upper = len(self.update_interval_presets)-1
            index = self.update_interval_presets.index(self._config.auto_update_frequency)
            self.hscale_update_interval.set_value(index)

        self._config.connect_gtk_spinbutton('max_episodes_per_feed', self.spinbutton_episode_limit)

        self.auto_download_model = NewEpisodeActionList(self._config)
        self.combo_auto_download.set_model(self.auto_download_model)
        cellrenderer = gtk.CellRendererText()
        self.combo_auto_download.pack_start(cellrenderer, True)
        self.combo_auto_download.add_attribute(cellrenderer, 'text', NewEpisodeActionList.C_CAPTION)
        self.combo_auto_download.set_active(self.auto_download_model.get_index())

        if self._config.auto_remove_played_episodes:
            adjustment_expiration = self.hscale_expiration.get_adjustment()
            if self._config.episode_old_age > adjustment_expiration.get_upper():
                # Patch the adjustment to include the higher current value
                adjustment_expiration.upper = self._config.episode_old_age

            self.hscale_expiration.set_value(self._config.episode_old_age)
        else:
            self.hscale_expiration.set_value(0)

        self._config.connect_gtk_togglebutton('auto_remove_unplayed_episodes',
                                              self.checkbutton_expiration_unplayed)
        self._config.connect_gtk_togglebutton('auto_remove_unfinished_episodes',
                                              self.checkbutton_expiration_unfinished)

        self.device_type_model = DeviceTypeActionList(self._config)
        self.combobox_device_type.set_model(self.device_type_model)
        cellrenderer = gtk.CellRendererText()
        self.combobox_device_type.pack_start(cellrenderer, True)
        self.combobox_device_type.add_attribute(cellrenderer, 'text',
                                                DeviceTypeActionList.C_CAPTION)
        self.combobox_device_type.set_active(self.device_type_model.get_index())

        self.on_sync_model = OnSyncActionList(self._config)
        self.combobox_on_sync.set_model(self.on_sync_model)
        cellrenderer = gtk.CellRendererText()
        self.combobox_on_sync.pack_start(cellrenderer, True)
        self.combobox_on_sync.add_attribute(cellrenderer, 'text', OnSyncActionList.C_CAPTION)
        self.combobox_on_sync.set_active(self.on_sync_model.get_index())

        self._config.connect_gtk_togglebutton('device_sync.skip_played_episodes',
                                              self.checkbutton_skip_played_episodes)
        self._config.connect_gtk_togglebutton('device_sync.playlists.create',
                                              self.checkbutton_create_playlists)
        self._config.connect_gtk_togglebutton('device_sync.playlists.two_way_sync',
                                              self.checkbutton_delete_using_playlists)

        # Have to do this before calling set_active on checkbutton_enable
        self._enable_mygpo = self._config.mygpo.enabled

        # Initialize the UI state with configuration settings
        self.checkbutton_enable.set_active(self._config.mygpo.enabled)
        self.entry_username.set_text(self._config.mygpo.username)
        self.entry_password.set_text(self._config.mygpo.password)
        self.entry_caption.set_text(self._config.mygpo.device.caption)

        # Disable mygpo sync while the dialog is open
        self._config.mygpo.enabled = False

        # Initialize Flattr settings
        self.set_flattr_preferences()

        # Configure the extensions manager GUI
        self.set_extension_preferences()

    def set_extension_preferences(self):
        def search_equal_func(model, column, key, it):
            label = model.get_value(it, self.C_LABEL)
            if key.lower() in label.lower():
                # from http://www.pygtk.org/docs/pygtk/class-gtktreeview.html:
                # "func should return False to indicate that the row matches
                # the search criteria."
                return False

            return True
        self.treeviewExtensions.set_search_equal_func(search_equal_func)

        toggle_cell = gtk.CellRendererToggle()
        toggle_cell.connect('toggled', self.on_extensions_cell_toggled)
        toggle_column = gtk.TreeViewColumn('')
        toggle_column.pack_start(toggle_cell, True)
        toggle_column.add_attribute(toggle_cell, 'active', self.C_TOGGLE)
        toggle_column.add_attribute(toggle_cell, 'visible', self.C_SHOW_TOGGLE)
        toggle_column.set_property('min-width', 32)
        self.treeviewExtensions.append_column(toggle_column)

        name_cell = gtk.CellRendererText()
        name_cell.set_property('ellipsize', pango.ELLIPSIZE_END)
        extension_column = gtk.TreeViewColumn(_('Name'))
        extension_column.pack_start(name_cell, True)
        extension_column.add_attribute(name_cell, 'markup', self.C_LABEL)
        extension_column.set_expand(True)
        self.treeviewExtensions.append_column(extension_column)

        self.extensions_model = gtk.ListStore(bool, str, object, bool)

        def key_func(pair):
            category, container = pair
            return (category, container.metadata.title)

        def convert(extensions):
            for container in extensions:
                yield (container.metadata.category, container)

        old_category = None
        for category, container in sorted(convert(gpodder.user_extensions.get_extensions()), key=key_func):
            if old_category != category:
                label = '<span weight="bold">%s</span>' % cgi.escape(category)
                self.extensions_model.append((None, label, None, False))
                old_category = category

            label = '%s\n<small>%s</small>' % (
                    cgi.escape(container.metadata.title),
                    cgi.escape(container.metadata.description))
            self.extensions_model.append((container.enabled, label, container, True))

        self.treeviewExtensions.set_model(self.extensions_model)
        self.treeviewExtensions.columns_autosize()

    def on_treeview_extension_button_released(self, treeview, event):
        if event.window != treeview.get_bin_window():
            return False

        if event.type == gtk.gdk.BUTTON_RELEASE and event.button == 3:
            return self.on_treeview_extension_show_context_menu(treeview, event)

        return False

    def on_treeview_extension_show_context_menu(self, treeview, event=None):
        selection = treeview.get_selection()
        model, paths = selection.get_selected_rows()
        container = model.get_value(model.get_iter(paths[0]), self.C_EXTENSION)

        if not container:
            return

        menu = gtk.Menu()

        if container.metadata.doc:
            menu_item = gtk.MenuItem(_('Documentation'))
            menu_item.connect('activate', self.open_weblink,
                container.metadata.doc)
            menu.append(menu_item)

        menu_item = gtk.MenuItem(_('Extension info'))
        menu_item.connect('activate', self.show_extension_info, model, container)
        menu.append(menu_item)

        if container.metadata.payment:
            if self.flattr.is_flattrable(container.metadata.payment):
                menu_item = gtk.MenuItem(_('Flattr this'))
                menu_item.connect('activate', self.flattr_extension,
                    container.metadata.payment)
            else:
                menu_item = gtk.MenuItem(_('Support the author'))
                menu_item.connect('activate', self.open_weblink,
                    container.metadata.payment)
            menu.append(menu_item)

        menu.show_all()
        if event is None:
            func = TreeViewHelper.make_popup_position_func(treeview)
            menu.popup(None, None, func, 3, 0)
        else:
            menu.popup(None, None, None, 3, 0)

        return True

    def set_flattr_preferences(self, widget=None):
        if not self._config.flattr.token:
            self.label_flattr.set_text(_('Please sign in with Flattr and Support Publishers'))
            self.button_flattr_login.set_label(_('Sign in to Flattr'))
        else:
            flattr_user = self.flattr.get_auth_username()
            self.label_flattr.set_markup(_('Logged in as <b>%(username)s</b>') % {'username': flattr_user})
            self.button_flattr_login.set_label(_('Sign out'))

        self.checkbutton_flattr_on_play.set_active(self._config.flattr.flattr_on_play)

    def on_button_flattr_login(self, widget):
        if not self._config.flattr.token:
            try:
                import webkit
            except ImportError, ie:
                self.show_message(_('Flattr integration requires WebKit/Gtk.'),
                        _('WebKit/Gtk not found'), important=True)
                return

            gPodderFlattrSignIn(self.parent_window,
                    _config=self._config,
                    flattr=self.flattr,
                    set_flattr_preferences=self.set_flattr_preferences)
        else:
            self._config.flattr.token = ''
            self.set_flattr_preferences()

    def on_check_flattr_on_play(self, widget):
        self._config.flattr.flattr_on_play = widget.get_active()

    def on_extensions_cell_toggled(self, cell, path):
        model = self.treeviewExtensions.get_model()
        it = model.get_iter(path)
        container = model.get_value(it, self.C_EXTENSION)

        enabled_extensions = list(self._config.extensions.enabled)
        new_enabled = not model.get_value(it, self.C_TOGGLE)

        if new_enabled and container.name not in enabled_extensions:
            enabled_extensions.append(container.name)
        elif not new_enabled and container.name in enabled_extensions:
            enabled_extensions.remove(container.name)

        self._config.extensions.enabled = enabled_extensions

        now_enabled = (container.name in self._config.extensions.enabled)

        if new_enabled == now_enabled:
            model.set_value(it, self.C_TOGGLE, new_enabled)
        elif container.error is not None:
            self.show_message(container.error.message,
                    _('Extension cannot be activated'), important=True)
            model.set_value(it, self.C_TOGGLE, False)

    def show_extension_info(self, w, model, container):
        if not container or not model:
            return

        # This is one ugly hack, but it displays the attributes of
        # the metadata object of the container..
        info = '\n'.join('<b>%s:</b> %s' %
                tuple(map(cgi.escape, map(str, (key, value))))
                for key, value in container.metadata.get_sorted())

        self.show_message(info, _('Extension module info'), important=True)

    def open_weblink(self, w, url):
        util.open_website(url)

    def flattr_extension(self, w, flattr_url):
        success, message = self.flattr.flattr_url(flattr_url)
        self.show_message(message, title=_('Flattr status'),
            important=not success)

    def on_dialog_destroy(self, widget):
        # Re-enable mygpo sync if the user has selected it
        self._config.mygpo.enabled = self._enable_mygpo
        # Make sure the device is successfully created/updated
        self.mygpo_client.create_device()
        # Flush settings for mygpo client now
        self.mygpo_client.flush(now=True)

    def on_button_close_clicked(self, widget):
        self.main_window.destroy()

    def on_button_advanced_clicked(self, widget):
        self.main_window.destroy()
        gPodderConfigEditor(self.parent_window, _config=self._config)

    def on_combo_audio_player_app_changed(self, widget):
        index = self.combo_audio_player_app.get_active()
        self._config.player = self.audio_player_model.get_command(index)

    def on_combo_video_player_app_changed(self, widget):
        index = self.combo_video_player_app.get_active()
        self._config.videoplayer = self.video_player_model.get_command(index)

    def on_combobox_preferred_video_format_changed(self, widget):
        index = self.combobox_preferred_video_format.get_active()
        self.preferred_video_format_model.set_index(index)

    def on_button_audio_player_clicked(self, widget):
        result = self.show_text_edit_dialog(_('Configure audio player'), \
                _('Command:'), \
                self._config.player)

        if result:
            self._config.player = result
            index = self.audio_player_model.get_index(self._config.player)
            self.combo_audio_player_app.set_active(index)

    def on_button_video_player_clicked(self, widget):
        result = self.show_text_edit_dialog(_('Configure video player'), \
                _('Command:'), \
                self._config.videoplayer)

        if result:
            self._config.videoplayer = result
            index = self.video_player_model.get_index(self._config.videoplayer)
            self.combo_video_player_app.set_active(index)

    def format_update_interval_value(self, scale, value):
        value = int(value)
        if value == 0:
            return _('manually')
        elif value > 0 and len(self.update_interval_presets) > value:
            return util.format_seconds_to_hour_min_sec(self.update_interval_presets[value]*60)
        else:
            return str(value)

    def on_update_interval_value_changed(self, range):
        value = int(range.get_value())
        self._config.auto_update_feeds = (value > 0)
        self._config.auto_update_frequency = self.update_interval_presets[value]

    def on_combo_auto_download_changed(self, widget):
        index = self.combo_auto_download.get_active()
        self.auto_download_model.set_index(index)

    def format_expiration_value(self, scale, value):
        value = int(value)
        if value == 0:
            return _('manually')
        else:
            return N_('after %(count)d day', 'after %(count)d days', value) % {'count':value}

    def on_expiration_value_changed(self, range):
        value = int(range.get_value())

        if value == 0:
            self.checkbutton_expiration_unplayed.set_active(False)
            self._config.auto_remove_played_episodes = False
            self._config.auto_remove_unplayed_episodes = False
        else:
            self._config.auto_remove_played_episodes = True
            self._config.episode_old_age = value

        self.checkbutton_expiration_unplayed.set_sensitive(value > 0)
        self.checkbutton_expiration_unfinished.set_sensitive(value > 0)

    def on_enabled_toggled(self, widget):
        # Only update indirectly (see on_dialog_destroy)
        self._enable_mygpo = widget.get_active()

    def on_username_changed(self, widget):
        self._config.mygpo.username = widget.get_text()

    def on_password_changed(self, widget):
        self._config.mygpo.password = widget.get_text()

    def on_device_caption_changed(self, widget):
        self._config.mygpo.device.caption = widget.get_text()

    def on_button_overwrite_clicked(self, button):
        title = _('Replace subscription list on server')
        message = _('Remote podcasts that have not been added locally will be removed on the server. Continue?')
        if self.show_confirmation(message, title):
            @util.run_in_background
            def thread_proc():
                self._config.mygpo.enabled = True
                self.on_send_full_subscriptions()
                self._config.mygpo.enabled = False

    def on_combobox_on_sync_changed(self, widget):
        index = self.combobox_on_sync.get_active()
        self.on_sync_model.set_index(index)

    def on_checkbutton_create_playlists_toggled(self, widget,device_type_changed=False):
        if not widget.get_active():
            self._config.device_sync.playlists.create=False
            self.toggle_playlist_interface(False)
            #need to read value of checkbutton from interface,
            #rather than value of parameter
        else:
            self._config.device_sync.playlists.create=True
            self.toggle_playlist_interface(True)

    def toggle_playlist_interface(self, enabled):
        if enabled and self._config.device_sync.device_type == 'filesystem':
            self.btn_playlistfolder.set_sensitive(True)
            self.btn_playlistfolder.set_label(self._config.device_sync.playlists.folder)
            self.checkbutton_delete_using_playlists.set_sensitive(True)
            children = self.btn_playlistfolder.get_children()
            if children:
                label = children.pop()
                label.set_alignment(0., .5)
        else:
            self.btn_playlistfolder.set_sensitive(False)
            self.btn_playlistfolder.set_label('')
            self.checkbutton_delete_using_playlists.set_sensitive(False)


    def on_combobox_device_type_changed(self, widget):
        index = self.combobox_device_type.get_active()
        self.device_type_model.set_index(index)
        device_type = self._config.device_sync.device_type
        if device_type == 'none':
            self.btn_filesystemMountpoint.set_label('')
            self.btn_filesystemMountpoint.set_sensitive(False)
            self.checkbutton_create_playlists.set_sensitive(False)
            self.toggle_playlist_interface(False)
            self.checkbutton_delete_using_playlists.set_sensitive(False)
            self.combobox_on_sync.set_sensitive(False)
            self.checkbutton_skip_played_episodes.set_sensitive(False)
        elif device_type == 'filesystem':
            self.btn_filesystemMountpoint.set_label(self._config.device_sync.device_folder)
            self.btn_filesystemMountpoint.set_sensitive(True)
            self.checkbutton_create_playlists.set_sensitive(True)
            children = self.btn_filesystemMountpoint.get_children()
            if children:
                label = children.pop()
                label.set_alignment(0., .5)
            self.toggle_playlist_interface(self._config.device_sync.playlists.create)
            self.combobox_on_sync.set_sensitive(True)
            self.checkbutton_skip_played_episodes.set_sensitive(True)
        elif device_type == 'ipod':
            self.btn_filesystemMountpoint.set_label(self._config.device_sync.device_folder)
            self.btn_filesystemMountpoint.set_sensitive(True)
            self.checkbutton_create_playlists.set_sensitive(False)
            self.toggle_playlist_interface(False)
            self.checkbutton_delete_using_playlists.set_sensitive(False)
            self.combobox_on_sync.set_sensitive(False)
            self.checkbutton_skip_played_episodes.set_sensitive(False)

            children = self.btn_filesystemMountpoint.get_children()
            if children:
                label = children.pop()
                label.set_alignment(0., .5)

        else:
            # TODO: Add support for iPod and MTP devices
            pass

    def on_btn_device_mountpoint_clicked(self, widget):
        fs = gtk.FileChooserDialog(title=_('Select folder for mount point'),
                action=gtk.FILE_CHOOSER_ACTION_SELECT_FOLDER)
        fs.add_button(gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL)
        fs.add_button(gtk.STOCK_OPEN, gtk.RESPONSE_OK)
        fs.set_current_folder(self.btn_filesystemMountpoint.get_label())
        if fs.run() == gtk.RESPONSE_OK:
            filename = fs.get_filename()
            if self._config.device_sync.device_type == 'filesystem':
                self._config.device_sync.device_folder = filename
            elif self._config.device_sync.device_type == 'ipod':
                self._config.device_sync.device_folder = filename
            # Request an update of the mountpoint button
            self.on_combobox_device_type_changed(None)

        fs.destroy()

    def on_btn_playlist_folder_clicked(self, widget):
        fs = gtk.FileChooserDialog(title=_('Select folder for playlists'),
                action=gtk.FILE_CHOOSER_ACTION_SELECT_FOLDER)
        fs.add_button(gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL)
        fs.add_button(gtk.STOCK_OPEN, gtk.RESPONSE_OK)
        fs.set_current_folder(self.btn_playlistfolder.get_label())
        if fs.run() == gtk.RESPONSE_OK:
            filename = util.relpath(self._config.device_sync.device_folder,
                                    fs.get_filename())
            if self._config.device_sync.device_type == 'filesystem':
                self._config.device_sync.playlists.folder = filename
                self.btn_playlistfolder.set_label(filename)
                children = self.btn_playlistfolder.get_children()
                if children:
                    label = children.pop()
                    label.set_alignment(0., .5)

        fs.destroy()

########NEW FILE########
__FILENAME__ = sync
# -*- coding: utf-8 -*-
#
# gPodder - A media aggregator and podcast client
# Copyright (c) 2005-2014 Thomas Perl and the gPodder Team
#
# gPodder is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# gPodder is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#

# gpodder.gtkui.desktop.sync - Glue code between GTK+ UI and sync module
# Thomas Perl <thp@gpodder.org>; 2009-09-05 (based on code from gui.py)
# Ported to gPodder 3 by Joseph Wickremasinghe in June 2012

import os
import gpodder

_ = gpodder.gettext

from gpodder import util
from gpodder import sync

from gpodder.gtkui.desktop.episodeselector import gPodderEpisodeSelector
from gpodder.gtkui.desktop.deviceplaylist import gPodderDevicePlaylist
import logging
logger = logging.getLogger(__name__)

class gPodderSyncUI(object):
    def __init__(self, config, notification, parent_window,
            show_confirmation,
            update_episode_list_icons,
            update_podcast_list_model,
            preferences_widget,
            channels,
            download_status_model,
            download_queue_manager,
            enable_download_list_update,
            commit_changes_to_database,
            delete_episode_list):
        self.device = None

        self._config = config
        self.notification = notification
        self.parent_window = parent_window
        self.show_confirmation = show_confirmation

        self.update_episode_list_icons = update_episode_list_icons
        self.update_podcast_list_model = update_podcast_list_model
        self.preferences_widget = preferences_widget
        self.channels=channels
        self.download_status_model = download_status_model
        self.download_queue_manager = download_queue_manager
        self.enable_download_list_update = enable_download_list_update
        self.commit_changes_to_database = commit_changes_to_database
        self.delete_episode_list=delete_episode_list

    def _filter_sync_episodes(self, channels, only_downloaded=False):
        """Return a list of episodes for device synchronization

        If only_downloaded is True, this will skip episodes that
        have not been downloaded yet and podcasts that are marked
        as "Do not synchronize to my device".
        """
        episodes = []
        for channel in channels:
            if only_downloaded or not channel.sync_to_mp3_player:
                logger.info('Skipping channel: %s', channel.title)
                continue

            for episode in channel.get_all_episodes():
                if (episode.was_downloaded(and_exists=True) or
                        not only_downloaded):
                    episodes.append(episode)
        return episodes

    def _show_message_unconfigured(self):
        title = _('No device configured')
        message = _('Please set up your device in the preferences dialog.')
        self.notification(message, title, widget=self.preferences_widget, important=True)

    def _show_message_cannot_open(self):
        title = _('Cannot open device')
        message = _('Please check the settings in the preferences dialog.')
        self.notification(message, title, widget=self.preferences_widget, important=True)

    def on_synchronize_episodes(self, channels, episodes=None, force_played=True):
        device = sync.open_device(self)

        if device is None:
            return self._show_message_unconfigured()

        if not device.open():
            return self._show_message_cannot_open()
        else:
            # Only set if device is configured and opened successfully
            self.device = device

        if episodes is None:
            force_played = False
            episodes = self._filter_sync_episodes(channels)

        def check_free_space():
            # "Will we add this episode to the device?"
            def will_add(episode):
                # If already on-device, it won't take up any space
                if device.episode_on_device(episode):
                    return False

                # Might not be synced if it's played already
                if (not force_played and
                        self._config.device_sync.skip_played_episodes):
                    return False

                # In all other cases, we expect the episode to be
                # synchronized to the device, so "answer" positive
                return True

            # "What is the file size of this episode?"
            def file_size(episode):
                filename = episode.local_filename(create=False)
                if filename is None:
                    return 0
                return util.calculate_size(str(filename))

            # Calculate total size of sync and free space on device
            total_size = sum(file_size(e) for e in episodes if will_add(e))
            free_space = max(device.get_free_space(), 0)

            if total_size > free_space:
                title = _('Not enough space left on device')
                message = (_('Additional free space required: %(required_space)s\nDo you want to continue?') %
               {'required_space': util.format_filesize(total_size - free_space)})
                if not self.show_confirmation(message, title):
                    device.cancel()
                    device.close()
                    return

            #enable updating of UI
            self.enable_download_list_update()

            #Update device playlists
            #General approach is as follows:

            #When a episode is downloaded and synched, it is added to the
            #standard playlist for that podcast which is then written to
            #the device.

            #After the user has played that episode on their device, they
            #can delete that episode from their device.

            #At the next sync, gPodder will then compare the standard
            #podcast-specific playlists on the device (as written by
            #gPodder during the last sync), with the episodes on the
            #device.If there is an episode referenced in the playlist
            #that is no longer on the device, gPodder will assume that
            #the episode has already been synced and subsequently deleted
            #from the device, and will hence mark that episode as deleted
            #in gPodder. If there are no playlists, nothing is deleted.

            #At the next sync, the playlists will be refreshed based on
            #the downloaded, undeleted episodes in gPodder, and the
            #cycle begins again...

            def resume_sync(episode_urls, channel_urls,progress):
                if progress is not None:
                    progress.on_finished()

                #rest of sync process should continue here
                self.commit_changes_to_database()
                for current_channel in self.channels:
                    #only sync those channels marked for syncing
                    if (self._config.device_sync.device_type=='filesystem' and current_channel.sync_to_mp3_player and self._config.device_sync.playlists.create):

                        #get playlist object
                        playlist=gPodderDevicePlaylist(self._config,
                                                       current_channel.title)
                        #need to refresh episode list so that
                        #deleted episodes aren't included in playlists
                        episodes_for_playlist=sorted(current_channel.get_episodes(gpodder.STATE_DOWNLOADED),
                                                     key=lambda ep: ep.published)
                        #don't add played episodes to playlist if skip_played_episodes is True
                        if self._config.device_sync.skip_played_episodes:
                            episodes_for_playlist=filter(lambda ep: ep.is_new, episodes_for_playlist)
                        playlist.write_m3u(episodes_for_playlist)

                #enable updating of UI
                self.enable_download_list_update()
                
                if (self._config.device_sync.device_type=='filesystem' and self._config.device_sync.playlists.create):                 
                    title = _('Update successful')
                    message = _('The playlist on your MP3 player has been updated.')
                    self.notification(message, title, widget=self.preferences_widget)

                # Finally start the synchronization process
                @util.run_in_background
                def sync_thread_func():
                    device.add_sync_tasks(episodes, force_played=force_played,
                            done_callback=self.enable_download_list_update)

                return

            if self._config.device_sync.playlists.create:
                try:
                    episodes_to_delete=[]
                    if self._config.device_sync.playlists.two_way_sync:
                        for current_channel in self.channels:
                            #only include channels that are included in the sync
                            if current_channel.sync_to_mp3_player:
                                #get playlist object
                                playlist=gPodderDevicePlaylist(self._config, current_channel.title)
                                #get episodes to be written to playlist
                                episodes_for_playlist=sorted(current_channel.get_episodes(gpodder.STATE_DOWNLOADED),
                                                             key=lambda ep: ep.published)
                                episode_keys=map(playlist.get_absolute_filename_for_playlist,
                                                 episodes_for_playlist)

                                episode_dict=dict(zip(episode_keys, episodes_for_playlist))

                                #then get episodes in playlist (if it exists) already on device
                                episodes_in_playlists = playlist.read_m3u()
                                #if playlist doesn't exist (yet) episodes_in_playlist will be empty
                                if episodes_in_playlists:
                                    for episode_filename in episodes_in_playlists:

                                        if not(os.path.exists(os.path.join(playlist.mountpoint,
                                                                           episode_filename))):
                                            #episode was synced but no longer on device
                                            #i.e. must have been deleted by user, so delete from gpodder
                                            try:
                                                episodes_to_delete.append(episode_dict[episode_filename])
                                            except KeyError, ioe:
                                                logger.warn('Episode %s, removed from device has already been deleted from gpodder',
                                                            episode_filename)


                    #delete all episodes from gpodder (will prompt user)

                    #not using playlists to delete
                    def auto_delete_callback(episodes):

                        if not episodes:
                            #episodes were deleted on device
                            #but user decided not to delete them from gpodder
                            #so jump straight to sync
                            logger.info ('Starting sync - no episodes selected for deletion')
                            resume_sync([],[],None)
                        else:
                            #episodes need to be deleted from gpodder
                            for episode_to_delete in episodes:
                                logger.info("Deleting episode %s",
                                               episode_to_delete.title)

                            logger.info ('Will start sync - after deleting episodes')
                            self.delete_episode_list(episodes,False,
                                                     True,resume_sync)

                        return

                    if episodes_to_delete:
                        columns = (
                            ('markup_delete_episodes', None, None, _('Episode')),
                        )

                        gPodderEpisodeSelector(self.parent_window,
                            title = _('Episodes have been deleted on device'),
                            instructions = 'Select the episodes you want to delete:',
                            episodes = episodes_to_delete,
                            selected = [True,]*len(episodes_to_delete), columns = columns,
                            callback = auto_delete_callback,
                            _config=self._config)
                    else:
                        logger.warning("Starting sync - no episodes to delete")
                        resume_sync([],[],None)

                except IOError, ioe:
                    title =  _('Error writing playlist files')
                    message = _(str(ioe))
                    self.notification(message, title, widget=self.preferences_widget)
            else:
                logger.info ('Not creating playlists - starting sync')
                resume_sync([],[],None)
                


        # This function is used to remove files from the device
        def cleanup_episodes():
            # 'skip_played_episodes' must be used or else all the
            # played tracks will be copied then immediately deleted
            if (self._config.device_sync.delete_played_episodes and
                    self._config.device_sync.skip_played_episodes):
                all_episodes = self._filter_sync_episodes(channels,
                        only_downloaded=False)
                for local_episode in all_episodes:
                    episode = device.episode_on_device(local_episode)
                    if episode is None:
                        continue

                    if local_episode.state == gpodder.STATE_DELETED:
                        logger.info('Removing episode from device: %s',
                                episode.title)
                        device.remove_track(episode)

            # When this is done, start the callback in the UI code
            util.idle_add(check_free_space)

        # This will run the following chain of actions:
        #  1. Remove old episodes (in worker thread)
        #  2. Check for free space (in UI thread)
        #  3. Sync the device (in UI thread)
        util.run_in_background(cleanup_episodes)


########NEW FILE########
__FILENAME__ = welcome
# -*- coding: utf-8 -*-
#
# gPodder - A media aggregator and podcast client
# Copyright (c) 2005-2014 Thomas Perl and the gPodder Team
#
# gPodder is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# gPodder is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#

import gtk

import gpodder

_ = gpodder.gettext

from gpodder.gtkui.interface.common import BuilderWidget

class gPodderWelcome(BuilderWidget):
    PADDING = 10

    def new(self):
        for widget in self.vbox_buttons.get_children():
            for child in widget.get_children():
                if isinstance(child, gtk.Alignment):
                    child.set_padding(self.PADDING, self.PADDING,
                        self.PADDING, self.PADDING)
                else:
                    child.set_padding(self.PADDING, self.PADDING)

    def on_btnCancel_clicked(self, button):
        self.main_window.response(gtk.RESPONSE_CANCEL)


########NEW FILE########
__FILENAME__ = desktopfile
# -*- coding: utf-8 -*-
#
# gPodder - A media aggregator and podcast client
# Copyright (c) 2005-2014 Thomas Perl and the gPodder Team
#
# gPodder is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# gPodder is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#


#
#  libplayers.py -- get list of potential playback apps
#  thomas perl <thp@perli.net>   20060329
#
#

import glob
import os.path
import threading

from ConfigParser import RawConfigParser

import gobject
import gtk
import gtk.gdk

import gpodder

_ = gpodder.gettext

# where are the .desktop files located?
userappsdirs = [ '/usr/share/applications/', '/usr/local/share/applications/', '/usr/share/applications/kde/' ]

# the name of the section in the .desktop files
sect = 'Desktop Entry'

class PlayerListModel(gtk.ListStore):
    C_ICON, C_NAME, C_COMMAND, C_CUSTOM = range(4)

    def __init__(self):
        gtk.ListStore.__init__(self, gtk.gdk.Pixbuf, str, str, bool)

    def insert_app(self, pixbuf, name, command):
        self.append((pixbuf, name, command, False))

    def get_command(self, index):
        return self[index][self.C_COMMAND]

    def get_index(self, value):
        for index, row in enumerate(self):
            if value == row[self.C_COMMAND]:
                return index

        last_row = self[-1]
        name = _('Command: %s') % value
        if last_row[self.C_CUSTOM]:
            last_row[self.C_COMMAND] = value
            last_row[self.C_NAME] = name
        else:
            self.append((None, name, value, True))

        return len(self)-1

    @classmethod
    def is_separator(cls, model, iter):
        return model.get_value(iter, cls.C_COMMAND) == ''

class UserApplication(object):
    def __init__(self, name, cmd, mime, icon):
        self.name = name
        self.cmd = cmd
        self.icon = icon
        self.mime = mime

    def get_icon(self):
        if self.icon is not None:
            # Load it from an absolute filename
            if os.path.exists(self.icon):
                try:
                    return gtk.gdk.pixbuf_new_from_file_at_size(self.icon, 24, 24)
                except gobject.GError, ge:
                    pass

            # Load it from the current icon theme
            (icon_name, extension) = os.path.splitext(os.path.basename(self.icon))
            theme = gtk.IconTheme()
            if theme.has_icon(icon_name):
                return theme.load_icon(icon_name, 24, 0)

    def is_mime(self, mimetype):
        return self.mime.find(mimetype+'/') != -1


class UserAppsReader(object):
    def __init__(self, mimetypes):
        self.apps = []
        self.mimetypes = mimetypes
        self.__has_read = False
        self.__finished = threading.Event()
        self.__has_sep = False
        self.apps.append(UserApplication(_('Default application'), 'default', ';'.join((mime+'/*' for mime in self.mimetypes)), gtk.STOCK_OPEN))

    def add_separator(self):
        self.apps.append(UserApplication('', '', ';'.join((mime+'/*' for mime in self.mimetypes)), ''))
        self.__has_sep = True

    def read( self):
        if self.__has_read:
            return

        self.__has_read = True
        for dir in userappsdirs:
            if os.path.exists( dir):
                for file in glob.glob(os.path.join(dir, '*.desktop')):
                    self.parse_and_append( file)
        self.__finished.set()

    def parse_and_append( self, filename):
        try:
            parser = RawConfigParser()
            parser.read([filename])
            if not parser.has_section(sect):
                return
            
            # Find out if we need it by comparing mime types
            app_mime = parser.get(sect, 'MimeType')
            for needed_type in self.mimetypes:
                if app_mime.find(needed_type+'/') != -1:
                    app_name = parser.get(sect, 'Name')
                    app_cmd = parser.get(sect, 'Exec')
                    app_icon = parser.get(sect, 'Icon')
                    if not self.__has_sep:
                        self.add_separator()
                    self.apps.append(UserApplication(app_name, app_cmd, app_mime, app_icon))
                    return
        except:
            return

    def get_model(self, mimetype):
        self.__finished.wait()

        model = PlayerListModel()
        for app in self.apps:
            if app.is_mime(mimetype):
                model.insert_app(app.get_icon(), app.name, app.cmd)
        return model


########NEW FILE########
__FILENAME__ = download
# -*- coding: utf-8 -*-
#
# gPodder - A media aggregator and podcast client
# Copyright (c) 2005-2014 Thomas Perl and the gPodder Team
#
# gPodder is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# gPodder is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#


#
#  gpodder.gtkui.download -- Download management in GUIs (2009-08-24)
#  Based on code from gpodder.services (thp, 2007-08-24)
#

import gpodder

from gpodder import util
from gpodder import download

import gtk
import cgi

import collections

_ = gpodder.gettext


class DownloadStatusModel(gtk.ListStore):
    # Symbolic names for our columns, so we know what we're up to
    C_TASK, C_NAME, C_URL, C_PROGRESS, C_PROGRESS_TEXT, C_ICON_NAME = range(6)

    SEARCH_COLUMNS = (C_NAME, C_URL)

    def __init__(self):
        gtk.ListStore.__init__(self, object, str, str, int, str, str)

        # Set up stock icon IDs for tasks
        self._status_ids = collections.defaultdict(lambda: None)
        self._status_ids[download.DownloadTask.DOWNLOADING] = gtk.STOCK_GO_DOWN
        self._status_ids[download.DownloadTask.DONE] = gtk.STOCK_APPLY
        self._status_ids[download.DownloadTask.FAILED] = gtk.STOCK_STOP
        self._status_ids[download.DownloadTask.CANCELLED] = gtk.STOCK_CANCEL
        self._status_ids[download.DownloadTask.PAUSED] = gtk.STOCK_MEDIA_PAUSE

    def _format_message(self, episode, message, podcast):
        episode = cgi.escape(episode)
        podcast = cgi.escape(podcast)
        return '%s\n<small>%s - %s</small>' % (episode, message, podcast)

    def request_update(self, iter, task=None):
        if task is None:
            # Ongoing update request from UI - get task from model
            task = self.get_value(iter, self.C_TASK)
        else:
            # Initial update request - update non-changing fields
            self.set(iter,
                    self.C_TASK, task,
                    self.C_URL, task.url)

        if task.status == task.FAILED:
            status_message = '%s: %s' % (\
                    task.STATUS_MESSAGE[task.status], \
                    task.error_message)
        elif task.status == task.DOWNLOADING:
            status_message = '%s (%.0f%%, %s/s)' % (\
                    task.STATUS_MESSAGE[task.status], \
                    task.progress*100, \
                    util.format_filesize(task.speed))
        else:
            status_message = task.STATUS_MESSAGE[task.status]

        if task.progress > 0 and task.progress < 1:
            current = util.format_filesize(task.progress*task.total_size, digits=1)
            total = util.format_filesize(task.total_size, digits=1)

            # Remove unit from current if same as in total
            # (does: "12 MiB / 24 MiB" => "12 / 24 MiB")
            current = current.split()
            if current[-1] == total.split()[-1]:
                current.pop()
            current = ' '.join(current)

            progress_message = ' / '.join((current, total))
        elif task.total_size > 0:
            progress_message = util.format_filesize(task.total_size, \
                    digits=1)
        else:
            progress_message = ('unknown size')

        self.set(iter,
                self.C_NAME, self._format_message(task.episode.title,
                    status_message, task.episode.channel.title),
                self.C_PROGRESS, 100.*task.progress, \
                self.C_PROGRESS_TEXT, progress_message, \
                self.C_ICON_NAME, self._status_ids[task.status])

    def __add_new_task(self, task):
        iter = self.append()
        self.request_update(iter, task)

    def register_task(self, task):
        util.idle_add(self.__add_new_task, task)

    def tell_all_tasks_to_quit(self):
        for row in self:
            task = row[DownloadStatusModel.C_TASK]
            if task is not None:
                # Pause currently-running (and queued) downloads
                if task.status in (task.QUEUED, task.DOWNLOADING):
                    task.status = task.PAUSED

                # Delete cancelled and failed downloads
                if task.status in (task.CANCELLED, task.FAILED):
                    task.removed_from_list()

    def are_downloads_in_progress(self):
        """
        Returns True if there are any downloads in the
        QUEUED or DOWNLOADING status, False otherwise.
        """
        for row in self:
            task = row[DownloadStatusModel.C_TASK]
            if task is not None and \
                    task.status in (task.DOWNLOADING, \
                                    task.QUEUED):
                return True

        return False


class DownloadTaskMonitor(object):
    """A helper class that abstracts download events"""
    def __init__(self, episode, on_can_resume, on_can_pause, on_finished):
        self.episode = episode
        self._status = None
        self._on_can_resume = on_can_resume
        self._on_can_pause = on_can_pause
        self._on_finished = on_finished

    def task_updated(self, task):
        if self.episode.url == task.episode.url and self._status != task.status:
            if task.status in (task.DONE, task.FAILED, task.CANCELLED):
                self._on_finished()
            elif task.status == task.PAUSED:
                self._on_can_resume()
            elif task.status in (task.QUEUED, task.DOWNLOADING):
                self._on_can_pause()
            self._status = task.status



########NEW FILE########
__FILENAME__ = draw
# -*- coding: utf-8 -*-
#
# gPodder - A media aggregator and podcast client
# Copyright (c) 2005-2014 Thomas Perl and the gPodder Team
#
# gPodder is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# gPodder is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#


#
#  draw.py -- Draw routines for gPodder-specific graphics
#  Thomas Perl <thp@perli.net>, 2007-11-25
#

import gpodder

import gtk
import pango
import pangocairo
import cairo
import StringIO
import math


class TextExtents(object):
    def __init__(self, ctx, text):
        tuple = ctx.text_extents(text)
        (self.x_bearing, self.y_bearing, self.width, self.height, self.x_advance, self.y_advance) = tuple

EPISODE_LIST_ICON_SIZE = 16

RRECT_LEFT_SIDE = 1
RRECT_RIGHT_SIDE = 2

def draw_rounded_rectangle(ctx, x, y, w, h, r=10, left_side_width = None, sides_to_draw=0, close=False):
    assert left_side_width is not None

    x = int(x)
    offset = 0
    if close: offset = 0.5

    if sides_to_draw & RRECT_LEFT_SIDE:
        ctx.move_to(x+int(left_side_width)-offset, y+h)
        ctx.line_to(x+r, y+h)
        ctx.curve_to(x, y+h, x, y+h, x, y+h-r)
        ctx.line_to(x, y+r)
        ctx.curve_to(x, y, x, y, x+r, y)
        ctx.line_to(x+int(left_side_width)-offset, y)
        if close:
            ctx.line_to(x+int(left_side_width)-offset, y+h)

    if sides_to_draw & RRECT_RIGHT_SIDE:
        ctx.move_to(x+int(left_side_width)+offset, y)
        ctx.line_to(x+w-r, y)
        ctx.curve_to(x+w, y, x+w, y, x+w, y+r)
        ctx.line_to(x+w, y+h-r)
        ctx.curve_to(x+w, y+h, x+w, y+h, x+w-r, y+h)
        ctx.line_to(x+int(left_side_width)+offset, y+h)
        if close:
            ctx.line_to(x+int(left_side_width)+offset, y)


def rounded_rectangle(ctx, x, y, width, height, radius=4.):
    """Simple rounded rectangle algorithmn

    http://www.cairographics.org/samples/rounded_rectangle/
    """
    degrees = math.pi / 180.
    ctx.new_sub_path()
    if width > radius:
        ctx.arc(x + width - radius, y + radius, radius, -90. * degrees, 0)
        ctx.arc(x + width - radius, y + height - radius, radius, 0, 90. * degrees)
        ctx.arc(x + radius, y + height - radius, radius, 90. * degrees, 180. * degrees)
        ctx.arc(x + radius, y + radius, radius, 180. * degrees, 270. * degrees)
    ctx.close_path()


def draw_text_box_centered(ctx, widget, w_width, w_height, text, font_desc=None, add_progress=None):
    style = widget.rc_get_style()
    text_color = style.text[gtk.STATE_PRELIGHT]
    red, green, blue = text_color.red, text_color.green, text_color.blue
    text_color = [float(x)/65535. for x in (red, green, blue)]
    text_color.append(.5)

    if font_desc is None:
        font_desc = style.font_desc
        font_desc.set_size(14*pango.SCALE)

    pango_context = widget.create_pango_context()
    layout = pango.Layout(pango_context)
    layout.set_font_description(font_desc)
    layout.set_text(text)
    width, height = layout.get_pixel_size()

    ctx.move_to(w_width/2-width/2, w_height/2-height/2)
    ctx.set_source_rgba(*text_color)
    ctx.show_layout(layout)

    # Draw an optional progress bar below the text (same width)
    if add_progress is not None:
        bar_height = 10
        ctx.set_source_rgba(*text_color)
        ctx.set_line_width(1.)
        rounded_rectangle(ctx, w_width/2-width/2-.5, w_height/2+height-.5, width+1, bar_height+1)
        ctx.stroke()
        rounded_rectangle(ctx, w_width/2-width/2, w_height/2+height, int(width*add_progress)+.5, bar_height)
        ctx.fill()

def draw_cake(percentage, text=None, emblem=None, size=None):
    # Download percentage bar icon - it turns out the cake is a lie (d'oh!)
    # ..but the inital idea was to have a cake-style indicator, but that
    # didn't work as well as the progress bar, but the name stuck..

    if size is None:
        size = EPISODE_LIST_ICON_SIZE

    surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, size, size)
    ctx = pangocairo.CairoContext(cairo.Context(surface))

    widget = gtk.ProgressBar()
    style = widget.rc_get_style()
    bgc = style.bg[gtk.STATE_NORMAL]
    fgc = style.bg[gtk.STATE_SELECTED]
    txc = style.text[gtk.STATE_NORMAL]

    border = 1.5
    height = int(size*.4)
    width = size - 2*border
    y = (size - height) / 2 + .5
    x = border

    # Background
    ctx.rectangle(x, y, width, height)
    ctx.set_source_rgb(bgc.red_float, bgc.green_float, bgc.blue_float)
    ctx.fill()

    # Filling
    if percentage > 0:
        fill_width = max(1, min(width-2, (width-2)*percentage+.5))
        ctx.rectangle(x+1, y+1, fill_width, height-2)
        ctx.set_source_rgb(fgc.red_float, fgc.green_float, fgc.blue_float)
        ctx.fill()

    # Border
    ctx.rectangle(x, y, width, height)
    ctx.set_source_rgb(txc.red_float, txc.green_float, txc.blue_float)
    ctx.set_line_width(1)
    ctx.stroke()

    del ctx
    return surface

def draw_text_pill(left_text, right_text, x=0, y=0, border=2, radius=14, font_desc=None):
    # Create temporary context to calculate the text size
    ctx = cairo.Context(cairo.ImageSurface(cairo.FORMAT_ARGB32, 1, 1))

    # Use GTK+ style of a normal Button
    widget = gtk.Label()
    style = widget.rc_get_style()

    # Padding (in px) at the right edge of the image (for Ubuntu; bug 1533)
    padding_right = 7

    x_border = border*2

    if font_desc is None:
        font_desc = style.font_desc
        font_desc.set_weight(pango.WEIGHT_BOLD)

    pango_context = widget.create_pango_context()
    layout_left = pango.Layout(pango_context)
    layout_left.set_font_description(font_desc)
    layout_left.set_text(left_text)
    layout_right = pango.Layout(pango_context)
    layout_right.set_font_description(font_desc)
    layout_right.set_text(right_text)

    width_left, height_left = layout_left.get_pixel_size()
    width_right, height_right = layout_right.get_pixel_size()

    text_height = max(height_left, height_right)

    image_height = int(y+text_height+border*2)
    image_width = int(x+width_left+width_right+x_border*4+padding_right)
    surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, image_width, image_height)

    ctx = pangocairo.CairoContext(cairo.Context(surface))

    # Clip so as to not draw on the right padding (for Ubuntu; bug 1533)
    ctx.rectangle(0, 0, image_width - padding_right, image_height)
    ctx.clip()

    if left_text == '0':
        left_text = None
    if right_text == '0':
        right_text = None

    left_side_width = width_left + x_border*2
    right_side_width = width_right + x_border*2

    rect_width = left_side_width + right_side_width
    rect_height = text_height + border*2
    if left_text is not None:
        draw_rounded_rectangle(ctx,x,y,rect_width,rect_height,radius, left_side_width, RRECT_LEFT_SIDE, right_text is None)
        linear = cairo.LinearGradient(x, y, x+left_side_width/2, y+rect_height/2)
        linear.add_color_stop_rgba(0, .8, .8, .8, .5)
        linear.add_color_stop_rgba(.4, .8, .8, .8, .7)
        linear.add_color_stop_rgba(.6, .8, .8, .8, .6)
        linear.add_color_stop_rgba(.9, .8, .8, .8, .8)
        linear.add_color_stop_rgba(1, .8, .8, .8, .9)
        ctx.set_source(linear)
        ctx.fill()
        xpos, ypos, width_left, height = x+1, y+1, left_side_width, rect_height-2
        if right_text is None:
            width_left -= 2
        draw_rounded_rectangle(ctx, xpos, ypos, rect_width, height, radius, width_left, RRECT_LEFT_SIDE, right_text is None)
        ctx.set_source_rgba(1., 1., 1., .3)
        ctx.set_line_width(1)
        ctx.stroke()
        draw_rounded_rectangle(ctx,x,y,rect_width,rect_height,radius, left_side_width, RRECT_LEFT_SIDE, right_text is None)
        ctx.set_source_rgba(.2, .2, .2, .6)
        ctx.set_line_width(1)
        ctx.stroke()

        ctx.move_to(x+x_border, y+1+border)
        ctx.set_source_rgba( 0, 0, 0, 1)
        ctx.show_layout(layout_left)
        ctx.move_to(x-1+x_border, y+border)
        ctx.set_source_rgba( 1, 1, 1, 1)
        ctx.show_layout(layout_left)

    if right_text is not None:
        draw_rounded_rectangle(ctx, x, y, rect_width, rect_height, radius, left_side_width, RRECT_RIGHT_SIDE, left_text is None)
        linear = cairo.LinearGradient(x+left_side_width, y, x+left_side_width+right_side_width/2, y+rect_height)
        linear.add_color_stop_rgba(0, .2, .2, .2, .9)
        linear.add_color_stop_rgba(.4, .2, .2, .2, .8)
        linear.add_color_stop_rgba(.6, .2, .2, .2, .6)
        linear.add_color_stop_rgba(.9, .2, .2, .2, .7)
        linear.add_color_stop_rgba(1, .2, .2, .2, .5)
        ctx.set_source(linear)
        ctx.fill()
        xpos, ypos, width, height = x, y+1, rect_width-1, rect_height-2
        if left_text is None:
            xpos, width = x+1, rect_width-2
        draw_rounded_rectangle(ctx, xpos, ypos, width, height, radius, left_side_width, RRECT_RIGHT_SIDE, left_text is None)
        ctx.set_source_rgba(1., 1., 1., .3)
        ctx.set_line_width(1)
        ctx.stroke()
        draw_rounded_rectangle(ctx, x, y, rect_width, rect_height, radius, left_side_width, RRECT_RIGHT_SIDE, left_text is None)
        ctx.set_source_rgba(.1, .1, .1, .6)
        ctx.set_line_width(1)
        ctx.stroke()

        ctx.move_to(x+left_side_width+x_border, y+1+border)
        ctx.set_source_rgba( 0, 0, 0, 1)
        ctx.show_layout(layout_right)
        ctx.move_to(x-1+left_side_width+x_border, y+border)
        ctx.set_source_rgba( 1, 1, 1, 1)
        ctx.show_layout(layout_right)

    return surface


def draw_cake_pixbuf(percentage, text=None, emblem=None):
    return cairo_surface_to_pixbuf(draw_cake(percentage, text, emblem))

def draw_pill_pixbuf(left_text, right_text):
    return cairo_surface_to_pixbuf(draw_text_pill(left_text, right_text))


def cairo_surface_to_pixbuf(s):
    """
    Converts a Cairo surface to a Gtk Pixbuf by
    encoding it as PNG and using the PixbufLoader.
    """
    sio = StringIO.StringIO()
    try:
        s.write_to_png(sio)
    except:
        # Write an empty PNG file to the StringIO, so
        # in case of an error we have "something" to
        # load. This happens in PyCairo < 1.1.6, see:
        # http://webcvs.cairographics.org/pycairo/NEWS?view=markup
        # Thanks to Chris Arnold for reporting this bug
        sio.write('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAAAXNSR0IArs4c6QAAAAZiS0dEAP8A\n/wD/oL2nkwAAAAlwSFlzAAALEwAACxMBAJqcGAAAAAd0SU1FB9cMEQkqIyxn3RkAAAAZdEVYdENv\nbW1lbnQAQ3JlYXRlZCB3aXRoIEdJTVBXgQ4XAAAADUlEQVQI12NgYGBgAAAABQABXvMqOgAAAABJ\nRU5ErkJggg==\n'.decode('base64'))

    pbl = gtk.gdk.PixbufLoader()
    pbl.write(sio.getvalue())
    pbl.close()

    pixbuf = pbl.get_pixbuf()
    return pixbuf


def draw_flattr_button(widget, flattr_image, flattrs_count):
    """
    Adds the flattrs count to the flattr button
    """
    if isinstance(flattrs_count, int):
        flattrs_count = str(flattrs_count)

    pixbuf = gtk.gdk.pixbuf_new_from_file(flattr_image)
    iwidth, iheight = pixbuf.get_width(), pixbuf.get_height()
    pixmap, mask = pixbuf.render_pixmap_and_mask()

    # get default-font
    style = widget.rc_get_style()
    font_desc = style.font_desc
    #font_desc.set_size(12*pango.SCALE)
    font_desc.set_size(9*pango.SCALE)

    # set font and text
    layout = widget.create_pango_layout(flattrs_count)
    layout.set_font_description(font_desc)
    fwidth, fheight = layout.get_pixel_size()

    x = 95 - abs(fwidth / 2) # 95 is the center of the bubble
    y = abs(iheight / 2) - abs(fheight / 2)

    cm = pixmap.get_colormap()
    red = cm.alloc_color('black')
    gc = pixmap.new_gc(foreground=red)
    pixmap.draw_layout(gc, x, y, layout)
    widget.set_from_pixmap(pixmap, mask)


def progressbar_pixbuf(width, height, percentage):
    COLOR_BG = (.4, .4, .4, .4)
    COLOR_FG = (.2, .9, .2, 1.)
    COLOR_FG_HIGH = (1., 1., 1., .5)
    COLOR_BORDER = (0., 0., 0., 1.)

    surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, width, height)
    ctx = cairo.Context(surface)

    padding = int(float(width)/8.0)
    bar_width = 2*padding
    bar_height = height - 2*padding
    bar_height_fill = bar_height*percentage

    # Background
    ctx.rectangle(padding, padding, bar_width, bar_height)
    ctx.set_source_rgba(*COLOR_BG)
    ctx.fill()

    # Foreground
    ctx.rectangle(padding, padding+bar_height-bar_height_fill, bar_width, bar_height_fill)
    ctx.set_source_rgba(*COLOR_FG)
    ctx.fill()
    ctx.rectangle(padding+bar_width/3, padding+bar_height-bar_height_fill, bar_width/4, bar_height_fill)
    ctx.set_source_rgba(*COLOR_FG_HIGH)
    ctx.fill()

    # Border
    ctx.rectangle(padding-.5, padding-.5, bar_width+1, bar_height+1)
    ctx.set_source_rgba(*COLOR_BORDER)
    ctx.set_line_width(1.)
    ctx.stroke()

    return cairo_surface_to_pixbuf(surface)


########NEW FILE########
__FILENAME__ = flattr
# -*- coding: utf-8 -*-
#
# gPodder - A media aggregator and podcast client
# Copyright (c) 2005-2014 Thomas Perl and the gPodder Team
#
# gPodder is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# gPodder is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#

import gtk
import gtk.gdk
import os.path

import gpodder

_ = gpodder.gettext

from gpodder.gtkui import draw


IMAGE_FLATTR = os.path.join(gpodder.images_folder, 'button-flattr.png')
IMAGE_FLATTR_GREY = os.path.join(gpodder.images_folder, 'button-flattr-grey.png')
IMAGE_FLATTRED = os.path.join(gpodder.images_folder, 'button-flattred.png')


def set_flattr_button(flattr, payment_url, widget_image, widget_button):
    if not flattr.api_reachable() or not payment_url:
        widget_image.hide()
        widget_button.hide()
        return False
    elif not flattr.has_token():
        badge = IMAGE_FLATTR_GREY
        button_text = _('Sign in')
        return False

    flattrs, flattred = flattr.get_thing_info(payment_url)
    can_flattr_this = False

    if flattred:
        badge = IMAGE_FLATTRED
        button_text = _('Flattred')
    else:
        badge = IMAGE_FLATTR
        button_text = _('Flattr this')
        can_flattr_this = True

    widget_button.set_label(button_text)
    widget_button.set_sensitive(can_flattr_this)
    widget_button.show()

    draw.draw_flattr_button(widget_image, badge, flattrs)
    widget_image.show()

    return can_flattr_this


########NEW FILE########
__FILENAME__ = addpodcast
# -*- coding: utf-8 -*-
#
# gPodder - A media aggregator and podcast client
# Copyright (c) 2005-2014 Thomas Perl and the gPodder Team
#
# gPodder is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# gPodder is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#

import gtk

import gpodder

_ = gpodder.gettext

from gpodder.gtkui.interface.common import BuilderWidget

from gpodder import util


class gPodderAddPodcast(BuilderWidget):
    def new(self):
        if not hasattr(self, 'add_podcast_list'):
            self.add_podcast_list = None
        if hasattr(self, 'custom_label'):
            self.label_add.set_text(self.custom_label)
        if hasattr(self, 'custom_title'):
            self.gPodderAddPodcast.set_title(self.custom_title)
        if hasattr(self, 'preset_url'):
            self.entry_url.set_text(self.preset_url)
        self.entry_url.connect('activate', self.on_entry_url_activate)
        self.gPodderAddPodcast.show()

        if not hasattr(self, 'preset_url'):
            # Fill the entry if a valid URL is in the clipboard, but
            # only if there's no preset_url available (see bug 1132)
            clipboard = gtk.Clipboard(selection='PRIMARY')
            def receive_clipboard_text(clipboard, text, second_try):
                # Heuristic: If there is a space in the clipboard
                # text, assume it's some arbitrary text, and no URL
                if text is not None and ' ' not in text:
                    url = util.normalize_feed_url(text)
                    if url is not None:
                        self.entry_url.set_text(url)
                        self.entry_url.set_position(-1)
                        return

                if not second_try:
                    clipboard = gtk.Clipboard()
                    clipboard.request_text(receive_clipboard_text, True)
            clipboard.request_text(receive_clipboard_text, False)

    def on_btn_close_clicked(self, widget):
        self.gPodderAddPodcast.destroy()

    def on_btn_paste_clicked(self, widget):
        clipboard = gtk.Clipboard()
        clipboard.request_text(self.receive_clipboard_text)

    def receive_clipboard_text(self, clipboard, text, data=None):
        if text is not None:
            self.entry_url.set_text(text)
        else:
            self.show_message(_('Nothing to paste.'), _('Clipboard is empty'))

    def on_entry_url_changed(self, widget):
        self.btn_add.set_sensitive(self.entry_url.get_text().strip() != '')

    def on_entry_url_activate(self, widget):
        self.on_btn_add_clicked(widget)

    def on_btn_add_clicked(self, widget):
        url = self.entry_url.get_text()
        self.on_btn_close_clicked(widget)
        if self.add_podcast_list is not None:
            title = None # FIXME: Add title GUI element
            self.add_podcast_list([(title, url)])


########NEW FILE########
__FILENAME__ = common
# -*- coding: utf-8 -*-
#
# gPodder - A media aggregator and podcast client
# Copyright (c) 2005-2014 Thomas Perl and the gPodder Team
#
# gPodder is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# gPodder is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#

import gtk
import os
import shutil

import gpodder

_ = gpodder.gettext

from gpodder import util

from gpodder.gtkui.base import GtkBuilderWidget


class BuilderWidget(GtkBuilderWidget):
    def __init__(self, parent, **kwargs):
        self._window_iconified = False
        self._window_visible = False

        GtkBuilderWidget.__init__(self, gpodder.ui_folders, gpodder.textdomain, **kwargs)

        # Enable support for tracking iconified state
        if hasattr(self, 'on_iconify') and hasattr(self, 'on_uniconify'):
            self.main_window.connect('window-state-event', \
                    self._on_window_state_event_iconified)

        # Enable support for tracking visibility state
        self.main_window.connect('visibility-notify-event', \
                    self._on_window_state_event_visibility)

        if parent is not None:
            self.main_window.set_transient_for(parent)

            if hasattr(self, 'center_on_widget'):
                (x, y) = parent.get_position()
                a = self.center_on_widget.allocation
                (x, y) = (x + a.x, y + a.y)
                (w, h) = (a.width, a.height)
                (pw, ph) = self.main_window.get_size()
                self.main_window.move(x + w/2 - pw/2, y + h/2 - ph/2)

    def _on_window_state_event_visibility(self, widget, event):
        if event.state & gtk.gdk.VISIBILITY_FULLY_OBSCURED:
            self._window_visible = False
        else:
            self._window_visible = True

        return False

    def _on_window_state_event_iconified(self, widget, event):
        if event.new_window_state & gtk.gdk.WINDOW_STATE_ICONIFIED:
            if not self._window_iconified:
                self._window_iconified = True
                self.on_iconify()
        else:
            if self._window_iconified:
                self._window_iconified = False
                self.on_uniconify()

        return False

    def is_iconified(self):
        return self._window_iconified

    def notification(self, message, title=None, important=False, widget=None):
        util.idle_add(self.show_message, message, title, important, widget)

    def get_dialog_parent(self):
        """Return a gtk.Window that should be the parent of dialogs"""
        return self.main_window

    def show_message(self, message, title=None, important=False, widget=None):
        if important:
            dlg = gtk.MessageDialog(self.main_window, gtk.DIALOG_MODAL, gtk.MESSAGE_INFO, gtk.BUTTONS_OK)
            if title:
                dlg.set_title(str(title))
                dlg.set_markup('<span weight="bold" size="larger">%s</span>\n\n%s' % (title, message))
            else:
                dlg.set_markup('<span weight="bold" size="larger">%s</span>' % (message))
            dlg.run()
            dlg.destroy()
        else:
            gpodder.user_extensions.on_notification_show(title, message)

    def show_confirmation(self, message, title=None):
        dlg = gtk.MessageDialog(self.main_window, gtk.DIALOG_MODAL, gtk.MESSAGE_QUESTION, gtk.BUTTONS_YES_NO)
        if title:
            dlg.set_title(str(title))
            dlg.set_markup('<span weight="bold" size="larger">%s</span>\n\n%s' % (title, message))
        else:
            dlg.set_markup('<span weight="bold" size="larger">%s</span>' % (message))
        response = dlg.run()
        dlg.destroy()
        return response == gtk.RESPONSE_YES

    def show_text_edit_dialog(self, title, prompt, text=None, empty=False, \
            is_url=False, affirmative_text=gtk.STOCK_OK):
        dialog = gtk.Dialog(title, self.get_dialog_parent(), \
            gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT)

        dialog.add_button(gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL)
        dialog.add_button(affirmative_text, gtk.RESPONSE_OK)

        dialog.set_has_separator(False)
        dialog.set_default_size(300, -1)
        dialog.set_default_response(gtk.RESPONSE_OK)

        text_entry = gtk.Entry()
        text_entry.set_activates_default(True)
        if text is not None:
            text_entry.set_text(text)
            text_entry.select_region(0, -1)

        if not empty:
            def on_text_changed(editable):
                can_confirm = (editable.get_text() != '')
                dialog.set_response_sensitive(gtk.RESPONSE_OK, can_confirm)
            text_entry.connect('changed', on_text_changed)
            if text is None:
                dialog.set_response_sensitive(gtk.RESPONSE_OK, False)

        hbox = gtk.HBox()
        hbox.set_border_width(10)
        hbox.set_spacing(10)
        hbox.pack_start(gtk.Label(prompt), False, False)
        hbox.pack_start(text_entry, True, True)
        dialog.vbox.pack_start(hbox, True, True)

        dialog.show_all()
        response = dialog.run()
        result = text_entry.get_text()
        dialog.destroy()

        if response == gtk.RESPONSE_OK:
            return result
        else:
            return None

    def show_login_dialog(self, title, message, username=None, password=None,
            username_prompt=None, register_callback=None, register_text=None):
        if username_prompt is None:
            username_prompt = _('Username')

        if register_text is None:
            register_text = _('New user')

        dialog = gtk.MessageDialog(
            self.main_window,
            gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT,
            gtk.MESSAGE_QUESTION,
            gtk.BUTTONS_CANCEL)
        dialog.add_button(_('Login'), gtk.RESPONSE_OK)
        dialog.set_image(gtk.image_new_from_stock(gtk.STOCK_DIALOG_AUTHENTICATION, gtk.ICON_SIZE_DIALOG))
        dialog.set_title(_('Authentication required'))
        dialog.set_markup('<span weight="bold" size="larger">' + title + '</span>')
        dialog.format_secondary_markup(message)
        dialog.set_default_response(gtk.RESPONSE_OK)

        if register_callback is not None:
            dialog.add_button(register_text, gtk.RESPONSE_HELP)

        username_entry = gtk.Entry()
        password_entry = gtk.Entry()

        username_entry.connect('activate', lambda w: password_entry.grab_focus())
        password_entry.set_visibility(False)
        password_entry.set_activates_default(True)

        if username is not None:
            username_entry.set_text(username)
        if password is not None:
            password_entry.set_text(password)

        table = gtk.Table(2, 2)
        table.set_row_spacings(6)
        table.set_col_spacings(6)

        username_label = gtk.Label()
        username_label.set_markup('<b>' + username_prompt + ':</b>')
        username_label.set_alignment(0.0, 0.5)
        table.attach(username_label, 0, 1, 0, 1, gtk.FILL, 0)
        table.attach(username_entry, 1, 2, 0, 1)

        password_label = gtk.Label()
        password_label.set_markup('<b>' + _('Password') + ':</b>')
        password_label.set_alignment(0.0, 0.5)
        table.attach(password_label, 0, 1, 1, 2, gtk.FILL, 0)
        table.attach(password_entry, 1, 2, 1, 2)

        dialog.vbox.pack_end(table, True, True, 0)
        dialog.show_all()
        response = dialog.run()

        while response == gtk.RESPONSE_HELP:
            register_callback()
            response = dialog.run()

        password_entry.set_visibility(True)
        username = username_entry.get_text()
        password = password_entry.get_text()
        success = (response == gtk.RESPONSE_OK)

        dialog.destroy()

        return (success, (username, password))

    def show_copy_dialog(self, src_filename, dst_filename=None, dst_directory=None, title=_('Select destination')):
        if dst_filename is None:
            dst_filename = src_filename

        if dst_directory is None:
            dst_directory = os.path.expanduser('~')

        base, extension = os.path.splitext(src_filename)

        if not dst_filename.endswith(extension):
            dst_filename += extension

        dlg = gtk.FileChooserDialog(title=title, parent=self.main_window, action=gtk.FILE_CHOOSER_ACTION_SAVE)
        dlg.add_button(gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL)
        dlg.add_button(gtk.STOCK_SAVE, gtk.RESPONSE_OK)

        dlg.set_do_overwrite_confirmation(True)
        dlg.set_current_name(os.path.basename(dst_filename))
        dlg.set_current_folder(dst_directory)

        result = False
        folder = dst_directory
        if dlg.run() == gtk.RESPONSE_OK:
            result = True
            dst_filename = dlg.get_filename()
            folder = dlg.get_current_folder()
            if not dst_filename.endswith(extension):
                dst_filename += extension

            shutil.copyfile(src_filename, dst_filename)

        dlg.destroy()
        return (result, folder)

class TreeViewHelper(object):
    """Container for gPodder-specific TreeView attributes."""
    LAST_TOOLTIP = '_gpodder_last_tooltip'
    CAN_TOOLTIP = '_gpodder_can_tooltip'
    ROLE = '_gpodder_role'
    COLUMNS = '_gpodder_columns'

    # Enum for the role attribute
    ROLE_PODCASTS, ROLE_EPISODES, ROLE_DOWNLOADS = range(3)

    @classmethod
    def set(cls, treeview, role):
        setattr(treeview, cls.LAST_TOOLTIP, None)
        setattr(treeview, cls.CAN_TOOLTIP, True)
        setattr(treeview, cls.ROLE, role)

    @staticmethod
    def make_search_equal_func(gpodder_model):
        def func(model, column, key, iter):
            if model is None:
                return True
            key = key.lower()
            for column in gpodder_model.SEARCH_COLUMNS:
                if key in model.get_value(iter, column).lower():
                    return False
            return True
        return func

    @classmethod
    def register_column(cls, treeview, column):
        if not hasattr(treeview, cls.COLUMNS):
            setattr(treeview, cls.COLUMNS, [])

        columns = getattr(treeview, cls.COLUMNS)
        columns.append(column)

    @classmethod
    def get_columns(cls, treeview):
        return getattr(treeview, cls.COLUMNS, [])

    @staticmethod
    def make_popup_position_func(widget):
        def position_func(menu):
            x, y = widget.get_bin_window().get_origin()

            # If there's a selection, place the popup menu on top of
            # the first-selected row (otherwise in the top left corner)
            selection = widget.get_selection()
            model, paths = selection.get_selected_rows()
            if paths:
                path = paths[0]
                area = widget.get_cell_area(path, widget.get_column(0))
                x += area.x
                y += area.y

            return (x, y, True)
        return position_func


########NEW FILE########
__FILENAME__ = configeditor
# -*- coding: utf-8 -*-
#
# gPodder - A media aggregator and podcast client
# Copyright (c) 2005-2014 Thomas Perl and the gPodder Team
#
# gPodder is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# gPodder is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#

import gtk
import cgi

import gpodder

_ = gpodder.gettext

from gpodder.gtkui.config import ConfigModel

from gpodder.gtkui.interface.common import BuilderWidget


class gPodderConfigEditor(BuilderWidget):
    def new(self):
        name_column = gtk.TreeViewColumn(_('Setting'))
        name_renderer = gtk.CellRendererText()
        name_column.pack_start(name_renderer)
        name_column.add_attribute(name_renderer, 'text', 0)
        name_column.add_attribute(name_renderer, 'style', 5)
        self.configeditor.append_column(name_column)

        value_column = gtk.TreeViewColumn(_('Set to'))
        value_check_renderer = gtk.CellRendererToggle()
        value_column.pack_start(value_check_renderer, expand=False)
        value_column.add_attribute(value_check_renderer, 'active', 7)
        value_column.add_attribute(value_check_renderer, 'visible', 6)
        value_column.add_attribute(value_check_renderer, 'activatable', 6)
        value_check_renderer.connect('toggled', self.value_toggled)

        value_renderer = gtk.CellRendererText()
        value_column.pack_start(value_renderer)
        value_column.add_attribute(value_renderer, 'text', 2)
        value_column.add_attribute(value_renderer, 'visible', 4)
        value_column.add_attribute(value_renderer, 'editable', 4)
        value_column.add_attribute(value_renderer, 'style', 5)
        value_renderer.connect('edited', self.value_edited)
        self.configeditor.append_column(value_column)

        self.model = ConfigModel(self._config)
        self.filter = self.model.filter_new()
        self.filter.set_visible_func(self.visible_func)

        self.configeditor.set_model(self.filter)
        self.configeditor.set_rules_hint(True)

    def visible_func(self, model, iter, user_data=None):
        text = self.entryFilter.get_text().lower()
        if text == '':
            return True
        else:
            # either the variable name or its value
            return (text in model.get_value(iter, 0).lower() or
                    text in model.get_value(iter, 2).lower())

    def value_edited(self, renderer, path, new_text):
        model = self.configeditor.get_model()
        iter = model.get_iter(path)
        name = model.get_value(iter, 0)
        type_cute = model.get_value(iter, 1)

        if not self._config.update_field(name, new_text):
            message = _('Cannot set %(field)s to %(value)s. Needed data type: %(datatype)s')
            d = {'field': cgi.escape(name),
                 'value': cgi.escape(new_text),
                 'datatype': cgi.escape(type_cute)}
            self.notification(message % d, _('Error setting option'))

    def value_toggled(self, renderer, path):
        model = self.configeditor.get_model()
        iter = model.get_iter(path)
        field_name = model.get_value(iter, 0)
        field_type = model.get_value(iter, 3)

        # Flip the boolean config flag
        if field_type == bool:
            self._config.toggle_flag(field_name)
    
    def on_entryFilter_changed(self, widget):
        self.filter.refilter()

    def on_btnShowAll_clicked(self, widget):
        self.entryFilter.set_text('')
        self.entryFilter.grab_focus()

    def on_btnClose_clicked(self, widget):
        self.gPodderConfigEditor.destroy()

    def on_gPodderConfigEditor_destroy(self, widget):
        self.model.stop_observing()


########NEW FILE########
__FILENAME__ = progress
# -*- coding: utf-8 -*-
#
# gPodder - A media aggregator and podcast client
# Copyright (c) 2005-2014 Thomas Perl and the gPodder Team
#
# gPodder is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# gPodder is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#

import gtk
import gobject
import pango

import gpodder

_ = gpodder.gettext

from gpodder.gtkui.widgets import SpinningProgressIndicator

class ProgressIndicator(object):
    # Delayed time until window is shown (for short operations)
    DELAY = 500

    # Time between GUI updates after window creation
    INTERVAL = 100

    def __init__(self, title, subtitle=None, cancellable=False, parent=None):
        self.title = title
        self.subtitle = subtitle
        self.cancellable = cancellable
        self.parent = parent
        self.dialog = None
        self.progressbar = None
        self.indicator = None
        self._initial_message = None
        self._initial_progress = None
        self._progress_set = False
        self.source_id = gobject.timeout_add(self.DELAY, self._create_progress)

    def _on_delete_event(self, window, event):
        if self.cancellable:
            self.dialog.response(gtk.RESPONSE_CANCEL)
        return True

    def _create_progress(self):
        self.dialog = gtk.MessageDialog(self.parent, \
                0, 0, gtk.BUTTONS_CANCEL, self.subtitle or self.title)
        self.dialog.set_modal(True)
        self.dialog.connect('delete-event', self._on_delete_event)
        self.dialog.set_title(self.title)
        self.dialog.set_deletable(self.cancellable)

        # Avoid selectable text (requires PyGTK >= 2.22)
        if hasattr(self.dialog, 'get_message_area'):
            for label in self.dialog.get_message_area():
                if isinstance(label, gtk.Label):
                    label.set_selectable(False)

        self.dialog.set_response_sensitive(gtk.RESPONSE_CANCEL, \
                self.cancellable)

        self.progressbar = gtk.ProgressBar()
        self.progressbar.set_ellipsize(pango.ELLIPSIZE_END)

        # If the window is shown after the first update, set the progress
        # info so that when the window appears, data is there already
        if self._initial_progress is not None:
            self.progressbar.set_fraction(self._initial_progress)
        if self._initial_message is not None:
            self.progressbar.set_text(self._initial_message)

        self.dialog.vbox.add(self.progressbar)
        self.indicator = SpinningProgressIndicator()
        self.dialog.set_image(self.indicator)
        self.dialog.show_all()

        gobject.source_remove(self.source_id)
        self.source_id = gobject.timeout_add(self.INTERVAL, self._update_gui)
        return False

    def _update_gui(self):
        if self.indicator:
            self.indicator.step_animation()
        if not self._progress_set and self.progressbar:
            self.progressbar.pulse()
        return True

    def on_message(self, message):
        if self.progressbar:
            self.progressbar.set_text(message)
        else:
            self._initial_message = message

    def on_progress(self, progress):
        self._progress_set = True
        if self.progressbar:
            self.progressbar.set_fraction(progress)
        else:
            self._initial_progress = progress

    def on_finished(self):
        if self.dialog is not None:
            self.dialog.destroy()
        gobject.source_remove(self.source_id)


########NEW FILE########
__FILENAME__ = macosx
# -*- coding: utf-8 -*-
#
# gPodder - A media aggregator and podcast client
# Copyright (c) 2005-2014 Thomas Perl and the gPodder Team
#
# gPodder is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# gPodder is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#

import struct
import sys

from gpodder import util

def aeKeyword(fourCharCode):
    """transform four character code into a long"""
    return struct.unpack('I', fourCharCode)[0]


# for the kCoreEventClass, kAEOpenDocuments, ... constants
# comes with macpython
from Carbon.AppleEvents import *

# all this depends on pyObjc (http://pyobjc.sourceforge.net/).
# There may be a way to achieve something equivalent with only
# what's in MacPython (see for instance http://mail.python.org/pipermail/pythonmac-sig/2006-May/017373.html)
# but I couldn't achieve this !

# Also note that it only works when gPodder is not running !
# For some reason I don't get the events afterwards...
try:
    from AppKit import NSObject
    from AppKit import NSAppleEventManager
    from AppKit import NSAppleEventDescriptor

    class gPodderEventHandler(NSObject):
        """ handles Apple Events for :
            - Open With... (and dropping a file on the icon)
            - "subscribe to podcast" from firefox
        The code was largely inspired by gedit-osx-delegate.m, from the
        gedit project
        (see http://git.gnome.org/browse/gedit/tree/gedit/osx/gedit-osx-delegate.m?id=GEDIT_2_28_3).
        """

        # keeps a reference to the gui.gPodder class
        gp = None

        def register(self, gp):
            """ register all handlers with NSAppleEventManager """
            self.gp = gp
            aem = NSAppleEventManager.sharedAppleEventManager()
            aem.setEventHandler_andSelector_forEventClass_andEventID_(
                self, 'openFileEvent:reply:', aeKeyword(kCoreEventClass), aeKeyword(kAEOpenDocuments))
            aem.setEventHandler_andSelector_forEventClass_andEventID_(
                self, 'subscribeEvent:reply:', aeKeyword('GURL'), aeKeyword('GURL'))

        def openFileEvent_reply_(self, event, reply):
            """ handles an 'Open With...' event"""
            urls = []
            filelist = event.paramDescriptorForKeyword_(aeKeyword(keyDirectObject))
            numberOfItems = filelist.numberOfItems()
            for i in range(1,numberOfItems+1):
                fileAliasDesc = filelist.descriptorAtIndex_(i)
                fileURLDesc = fileAliasDesc.coerceToDescriptorType_(aeKeyword(typeFileURL))
                fileURLData = fileURLDesc.data()
                url = buffer(fileURLData.bytes(),0,fileURLData.length())
                url = str(url)
                util.idle_add(self.gp.on_item_import_from_file_activate, None,url)
                urls.append(str(url))

            print >>sys.stderr,("open Files :",urls)
            result = NSAppleEventDescriptor.descriptorWithInt32_(42)
            reply.setParamDescriptor_forKeyword_(result, aeKeyword('----'))

        def subscribeEvent_reply_(self, event, reply):
            """ handles a 'Subscribe to...' event"""
            filelist = event.paramDescriptorForKeyword_(aeKeyword(keyDirectObject))
            fileURLData = filelist.data()
            url = buffer(fileURLData.bytes(),0,fileURLData.length())
            url = str(url)
            print >>sys.stderr,("Subscribe to :"+url)
            util.idle_add(self.gp.subscribe_to_url, url)

            result = NSAppleEventDescriptor.descriptorWithInt32_(42)
            reply.setParamDescriptor_forKeyword_(result, aeKeyword('----'))

    # global reference to the handler (mustn't be destroyed)
    handler = gPodderEventHandler.alloc().init()
except ImportError:
    print >> sys.stderr, """
    Warning: pyobjc not found. Disabling "Subscribe with" events handling
    """
    handler = None

def register_handlers(gp):
    """ register the events handlers (and keep a reference to gPodder's instance)"""
    if handler is not None:
        handler.register(gp)


########NEW FILE########
__FILENAME__ = main
# -*- coding: utf-8 -*-
#
# gPodder - A media aggregator and podcast client
# Copyright (c) 2005-2014 Thomas Perl and the gPodder Team
#
# gPodder is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# gPodder is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#

import os
import platform
import gtk
import gtk.gdk
import gobject
import pango
import random
import sys
import shutil
import subprocess
import glob
import time
import threading
import tempfile
import collections
import urllib
import cgi


import gpodder

import dbus
import dbus.service
import dbus.mainloop
import dbus.glib

from gpodder import core
from gpodder import feedcore
from gpodder import util
from gpodder import opml
from gpodder import download
from gpodder import my
from gpodder import youtube
from gpodder import player
from gpodder import common

import logging
logger = logging.getLogger(__name__)

_ = gpodder.gettext
N_ = gpodder.ngettext

from gpodder.gtkui.model import Model
from gpodder.gtkui.model import PodcastListModel
from gpodder.gtkui.model import EpisodeListModel
from gpodder.gtkui.config import UIConfig
from gpodder.gtkui.services import CoverDownloader
from gpodder.gtkui.widgets import SimpleMessageArea
from gpodder.gtkui.desktopfile import UserAppsReader

from gpodder.gtkui.draw import draw_text_box_centered, draw_cake_pixbuf
from gpodder.gtkui.draw import EPISODE_LIST_ICON_SIZE

from gpodder.gtkui.interface.common import BuilderWidget
from gpodder.gtkui.interface.common import TreeViewHelper
from gpodder.gtkui.interface.addpodcast import gPodderAddPodcast

from gpodder.gtkui.download import DownloadStatusModel

from gpodder.gtkui.desktop.welcome import gPodderWelcome
from gpodder.gtkui.desktop.channel import gPodderChannel
from gpodder.gtkui.desktop.preferences import gPodderPreferences
from gpodder.gtkui.desktop.episodeselector import gPodderEpisodeSelector
from gpodder.gtkui.desktop.podcastdirectory import gPodderPodcastDirectory
from gpodder.gtkui.interface.progress import ProgressIndicator

from gpodder.gtkui.desktop.sync import gPodderSyncUI
from gpodder.gtkui import flattr
from gpodder.gtkui import shownotes

from gpodder.dbusproxy import DBusPodcastsProxy
from gpodder import extensions


macapp = None
if gpodder.ui.osx and getattr(gtk.gdk, 'WINDOWING', 'x11') == 'quartz':
    try:
        from gtkosx_application import *
        macapp = Application()
    except ImportError:
        print >> sys.stderr, """
        Warning: gtk-mac-integration not found, disabling native menus
        """


class gPodder(BuilderWidget, dbus.service.Object):
    # Width (in pixels) of episode list icon
    EPISODE_LIST_ICON_WIDTH = 40

    def __init__(self, bus_name, gpodder_core):
        dbus.service.Object.__init__(self, object_path=gpodder.dbus_gui_object_path, bus_name=bus_name)
        self.podcasts_proxy = DBusPodcastsProxy(lambda: self.channels,
                self.on_itemUpdate_activate,
                self.playback_episodes,
                self.download_episode_list,
                self.episode_object_by_uri,
                bus_name)
        self.core = gpodder_core
        self.config = self.core.config
        self.db = self.core.db
        self.model = self.core.model
        self.flattr = self.core.flattr
        BuilderWidget.__init__(self, None)

    def new(self):
        gpodder.user_extensions.on_ui_object_available('gpodder-gtk', self)
        self.toolbar.set_property('visible', self.config.show_toolbar)

        self.bluetooth_available = util.bluetooth_available()

        self.config.connect_gtk_window(self.main_window, 'main_window')

        self.config.connect_gtk_paned('ui.gtk.state.main_window.paned_position', self.channelPaned)

        self.main_window.show()

        self.player_receiver = player.MediaPlayerDBusReceiver(self.on_played)

        self.gPodder.connect('key-press-event', self.on_key_press)

        self.episode_columns_menu = None
        self.config.add_observer(self.on_config_changed)

        self.shownotes_pane = gtk.HBox()
        if shownotes.have_webkit and self.config.enable_html_shownotes:
            self.shownotes_object = shownotes.gPodderShownotesHTML(self.shownotes_pane)
        else:
            self.shownotes_object = shownotes.gPodderShownotesText(self.shownotes_pane)

        # Vertical paned for the episode list and shownotes
        self.vpaned = gtk.VPaned()
        paned = self.vbox_episode_list.get_parent()
        self.vbox_episode_list.reparent(self.vpaned)
        self.vpaned.child_set_property(self.vbox_episode_list, 'resize', True)
        self.vpaned.child_set_property(self.vbox_episode_list, 'shrink', False)
        self.vpaned.pack2(self.shownotes_pane, resize=False, shrink=False)
        self.vpaned.show()

        # Minimum height for both episode list and shownotes
        self.vbox_episode_list.set_size_request(-1, 100)
        self.shownotes_pane.set_size_request(-1, 100)

        self.config.connect_gtk_paned('ui.gtk.state.main_window.episode_list_size',
                self.vpaned)
        paned.add2(self.vpaned)


        self.new_episodes_window = None

        # Mac OS X-specific UI tweaks: Native main menu integration
        # http://sourceforge.net/apps/trac/gtk-osx/wiki/Integrate
        if macapp is not None:
            # Move the menu bar from the window to the Mac menu bar
            self.mainMenu.hide()
            macapp.set_menu_bar(self.mainMenu)

            # Reparent some items to the "Application" menu
            item = self.uimanager1.get_widget('/mainMenu/menuHelp/itemAbout')
            macapp.insert_app_menu_item(item, 0)
            macapp.insert_app_menu_item(gtk.SeparatorMenuItem(), 1)
            item = self.uimanager1.get_widget('/mainMenu/menuPodcasts/itemPreferences')
            macapp.insert_app_menu_item(item, 2)

            quit_item = self.uimanager1.get_widget('/mainMenu/menuPodcasts/itemQuit')
            quit_item.hide()
        # end Mac OS X specific UI tweaks

        self.download_status_model = DownloadStatusModel()
        self.download_queue_manager = download.DownloadQueueManager(self.config)

        self.itemShowToolbar.set_active(self.config.show_toolbar)
        self.itemShowDescription.set_active(self.config.episode_list_descriptions)

        self.config.connect_gtk_spinbutton('max_downloads', self.spinMaxDownloads)
        self.config.connect_gtk_togglebutton('max_downloads_enabled', self.cbMaxDownloads)
        self.config.connect_gtk_spinbutton('limit_rate_value', self.spinLimitDownloads)
        self.config.connect_gtk_togglebutton('limit_rate', self.cbLimitDownloads)

        # When the amount of maximum downloads changes, notify the queue manager
        changed_cb = lambda spinbutton: self.download_queue_manager.spawn_threads()
        self.spinMaxDownloads.connect('value-changed', changed_cb)

        self.default_title = None
        self.set_title(_('gPodder'))

        self.cover_downloader = CoverDownloader()

        # Generate list models for podcasts and their episodes
        self.podcast_list_model = PodcastListModel(self.cover_downloader)

        self.cover_downloader.register('cover-available', self.cover_download_finished)

        # Source IDs for timeouts for search-as-you-type
        self._podcast_list_search_timeout = None
        self._episode_list_search_timeout = None

        # Init the treeviews that we use
        self.init_podcast_list_treeview()
        self.init_episode_list_treeview()
        self.init_download_list_treeview()

        if self.config.podcast_list_hide_boring:
            self.item_view_hide_boring_podcasts.set_active(True)

        self.currently_updating = False

        self.download_tasks_seen = set()
        self.download_list_update_enabled = False
        self.download_task_monitors = set()

        # Subscribed channels
        self.active_channel = None
        self.channels = self.model.get_podcasts()

        # Set up the first instance of MygPoClient
        self.mygpo_client = my.MygPoClient(self.config)

        gpodder.user_extensions.on_ui_initialized(self.model,
                self.extensions_podcast_update_cb,
                self.extensions_episode_download_cb)

        # load list of user applications for audio playback
        self.user_apps_reader = UserAppsReader(['audio', 'video'])
        util.run_in_background(self.user_apps_reader.read)

        # Now, update the feed cache, when everything's in place
        self.btnUpdateFeeds.show()
        self.feed_cache_update_cancelled = False
        self.update_podcast_list_model()

        self.message_area = None

        self.partial_downloads_indicator = None
        util.run_in_background(self.find_partial_downloads)

        # Start the auto-update procedure
        self._auto_update_timer_source_id = None
        if self.config.auto_update_feeds:
            self.restart_auto_update_timer()

        # Find expired (old) episodes and delete them
        old_episodes = list(common.get_expired_episodes(self.channels, self.config))
        if len(old_episodes) > 0:
            self.delete_episode_list(old_episodes, confirm=False)
            updated_urls = set(e.channel.url for e in old_episodes)
            self.update_podcast_list_model(updated_urls)

        # Do the initial sync with the web service
        if self.mygpo_client.can_access_webservice():
            util.idle_add(self.mygpo_client.flush, True)

        # First-time users should be asked if they want to see the OPML
        if not self.channels:
            self.on_itemUpdate_activate()
        elif self.config.software_update.check_on_startup:
            # Check for software updates from gpodder.org
            diff = time.time() - self.config.software_update.last_check
            if diff > (60*60*24)*self.config.software_update.interval:
                self.config.software_update.last_check = int(time.time())
                self.check_for_updates(silent=True)

    def find_partial_downloads(self):
        def start_progress_callback(count):
            self.partial_downloads_indicator = ProgressIndicator(
                    _('Loading incomplete downloads'),
                    _('Some episodes have not finished downloading in a previous session.'),
                    False, self.get_dialog_parent())
            self.partial_downloads_indicator.on_message(N_('%(count)d partial file', '%(count)d partial files', count) % {'count':count})

            util.idle_add(self.wNotebook.set_current_page, 1)

        def progress_callback(title, progress):
            self.partial_downloads_indicator.on_message(title)
            self.partial_downloads_indicator.on_progress(progress)

        def finish_progress_callback(resumable_episodes):
            util.idle_add(self.partial_downloads_indicator.on_finished)
            self.partial_downloads_indicator = None

            if resumable_episodes:
                def offer_resuming():
                    self.download_episode_list_paused(resumable_episodes)
                    resume_all = gtk.Button(_('Resume all'))
                    def on_resume_all(button):
                        selection = self.treeDownloads.get_selection()
                        selection.select_all()
                        selected_tasks, _, _, _, _, _ = self.downloads_list_get_selection()
                        selection.unselect_all()
                        self._for_each_task_set_status(selected_tasks, download.DownloadTask.QUEUED)
                        self.message_area.hide()
                    resume_all.connect('clicked', on_resume_all)

                    self.message_area = SimpleMessageArea(_('Incomplete downloads from a previous session were found.'), (resume_all,))
                    self.vboxDownloadStatusWidgets.pack_start(self.message_area, expand=False)
                    self.vboxDownloadStatusWidgets.reorder_child(self.message_area, 0)
                    self.message_area.show_all()
                    common.clean_up_downloads(delete_partial=False)
                util.idle_add(offer_resuming)
            else:
                util.idle_add(self.wNotebook.set_current_page, 0)

        common.find_partial_downloads(self.channels,
                start_progress_callback,
                progress_callback,
                finish_progress_callback)

    def episode_object_by_uri(self, uri):
        """Get an episode object given a local or remote URI

        This can be used to quickly access an episode object
        when all we have is its download filename or episode
        URL (e.g. from external D-Bus calls / signals, etc..)
        """
        if uri.startswith('/'):
            uri = 'file://' + urllib.quote(uri)

        prefix = 'file://' + urllib.quote(gpodder.downloads)

        # By default, assume we can't pre-select any channel
        # but can match episodes simply via the download URL
        is_channel = lambda c: True
        is_episode = lambda e: e.url == uri

        if uri.startswith(prefix):
            # File is on the local filesystem in the download folder
            # Try to reduce search space by pre-selecting the channel
            # based on the folder name of the local file

            filename = urllib.unquote(uri[len(prefix):])
            file_parts = filter(None, filename.split(os.sep))

            if len(file_parts) != 2:
                return None

            foldername, filename = file_parts

            is_channel = lambda c: c.download_folder == foldername
            is_episode = lambda e: e.download_filename == filename

        # Deep search through channels and episodes for a match
        for channel in filter(is_channel, self.channels):
            for episode in filter(is_episode, channel.get_all_episodes()):
                return episode

        return None

    def on_played(self, start, end, total, file_uri):
        """Handle the "played" signal from a media player"""
        if start == 0 and end == 0 and total == 0:
            # Ignore bogus play event
            return
        elif end < start + 5:
            # Ignore "less than five seconds" segments,
            # as they can happen with seeking, etc...
            return

        logger.debug('Received play action: %s (%d, %d, %d)', file_uri, start, end, total)
        episode = self.episode_object_by_uri(file_uri)

        if episode is not None:
            file_type = episode.file_type()

            now = time.time()
            if total > 0:
                episode.total_time = total
            elif total == 0:
                # Assume the episode's total time for the action
                total = episode.total_time

            assert (episode.current_position_updated is None or
                    now >= episode.current_position_updated)

            episode.current_position = end
            episode.current_position_updated = now
            episode.mark(is_played=True)
            episode.save()
            self.db.commit()
            self.update_episode_list_icons([episode.url])
            self.update_podcast_list_model([episode.channel.url])

            # Submit this action to the webservice
            self.mygpo_client.on_playback_full(episode, start, end, total)

    def on_add_remove_podcasts_mygpo(self):
        actions = self.mygpo_client.get_received_actions()
        if not actions:
            return False

        existing_urls = [c.url for c in self.channels]

        # Columns for the episode selector window - just one...
        columns = (
            ('description', None, None, _('Action')),
        )

        # A list of actions that have to be chosen from
        changes = []

        # Actions that are ignored (already carried out)
        ignored = []

        for action in actions:
            if action.is_add and action.url not in existing_urls:
                changes.append(my.Change(action))
            elif action.is_remove and action.url in existing_urls:
                podcast_object = None
                for podcast in self.channels:
                    if podcast.url == action.url:
                        podcast_object = podcast
                        break
                changes.append(my.Change(action, podcast_object))
            else:
                ignored.append(action)

        # Confirm all ignored changes
        self.mygpo_client.confirm_received_actions(ignored)

        def execute_podcast_actions(selected):
            # In the future, we might retrieve the title from gpodder.net here,
            # but for now, we just use "None" to use the feed-provided title
            title = None
            add_list = [(title, c.action.url)
                    for c in selected if c.action.is_add]
            remove_list = [c.podcast for c in selected if c.action.is_remove]

            # Apply the accepted changes locally
            self.add_podcast_list(add_list)
            self.remove_podcast_list(remove_list, confirm=False)

            # All selected items are now confirmed
            self.mygpo_client.confirm_received_actions(c.action for c in selected)

            # Revert the changes on the server
            rejected = [c.action for c in changes if c not in selected]
            self.mygpo_client.reject_received_actions(rejected)

        def ask():
            # We're abusing the Episode Selector again ;) -- thp
            gPodderEpisodeSelector(self.main_window, \
                    title=_('Confirm changes from gpodder.net'), \
                    instructions=_('Select the actions you want to carry out.'), \
                    episodes=changes, \
                    columns=columns, \
                    size_attribute=None, \
                    stock_ok_button=gtk.STOCK_APPLY, \
                    callback=execute_podcast_actions, \
                    _config=self.config)

        # There are some actions that need the user's attention
        if changes:
            util.idle_add(ask)
            return True

        # We have no remaining actions - no selection happens
        return False

    def rewrite_urls_mygpo(self):
        # Check if we have to rewrite URLs since the last add
        rewritten_urls = self.mygpo_client.get_rewritten_urls()
        changed = False

        for rewritten_url in rewritten_urls:
            if not rewritten_url.new_url:
                continue

            for channel in self.channels:
                if channel.url == rewritten_url.old_url:
                    logger.info('Updating URL of %s to %s', channel,
                            rewritten_url.new_url)
                    channel.url = rewritten_url.new_url
                    channel.save()
                    changed = True
                    break

        if changed:
            util.idle_add(self.update_episode_list_model)

    def on_send_full_subscriptions(self):
        # Send the full subscription list to the gpodder.net client
        # (this will overwrite the subscription list on the server)
        indicator = ProgressIndicator(_('Uploading subscriptions'), \
                _('Your subscriptions are being uploaded to the server.'), \
                False, self.get_dialog_parent())

        try:
            self.mygpo_client.set_subscriptions([c.url for c in self.channels])
            util.idle_add(self.show_message, _('List uploaded successfully.'))
        except Exception, e:
            def show_error(e):
                message = str(e)
                if not message:
                    message = e.__class__.__name__
                self.show_message(message, \
                        _('Error while uploading'), \
                        important=True)
            util.idle_add(show_error, e)

        util.idle_add(indicator.on_finished)

    def on_button_subscribe_clicked(self, button):
        self.on_itemImportChannels_activate(button)

    def on_button_downloads_clicked(self, widget):
        self.downloads_window.show()

    def for_each_episode_set_task_status(self, episodes, status):
        episode_urls = set(episode.url for episode in episodes)
        model = self.treeDownloads.get_model()
        selected_tasks = [(gtk.TreeRowReference(model, row.path), \
                           model.get_value(row.iter, \
                           DownloadStatusModel.C_TASK)) for row in model \
                           if model.get_value(row.iter, DownloadStatusModel.C_TASK).url \
                           in episode_urls]
        self._for_each_task_set_status(selected_tasks, status)

    def on_treeview_button_pressed(self, treeview, event):
        if event.window != treeview.get_bin_window():
            return False

        role = getattr(treeview, TreeViewHelper.ROLE)
        if role == TreeViewHelper.ROLE_PODCASTS:
            return self.currently_updating
        elif (role == TreeViewHelper.ROLE_EPISODES and event.button == 1):
            # Toggle episode "new" status by clicking the icon (bug 1432)
            result = treeview.get_path_at_pos(int(event.x), int(event.y))
            if result is not None:
                path, column, x, y = result
                # The user clicked the icon if she clicked in the first column
                # and the x position is in the area where the icon resides
                if (x < self.EPISODE_LIST_ICON_WIDTH and
                        column == treeview.get_columns()[0]):
                    model = treeview.get_model()
                    cursor_episode = model.get_value(model.get_iter(path),
                            EpisodeListModel.C_EPISODE)

                    new_value = cursor_episode.is_new
                    selected_episodes = self.get_selected_episodes()

                    # Avoid changing anything if the clicked episode is not
                    # selected already - otherwise update all selected
                    if cursor_episode in selected_episodes:
                        for episode in selected_episodes:
                            episode.mark(is_played=new_value)

                        self.update_episode_list_icons(selected=True)
                        self.update_podcast_list_model(selected=True)
                        return True

        return event.button == 3

    def on_treeview_podcasts_button_released(self, treeview, event):
        if event.window != treeview.get_bin_window():
            return False

        return self.treeview_channels_show_context_menu(treeview, event)

    def on_treeview_episodes_button_released(self, treeview, event):
        if event.window != treeview.get_bin_window():
            return False

        return self.treeview_available_show_context_menu(treeview, event)

    def on_treeview_downloads_button_released(self, treeview, event):
        if event.window != treeview.get_bin_window():
            return False

        return self.treeview_downloads_show_context_menu(treeview, event)

    def on_entry_search_podcasts_changed(self, editable):
        if self.hbox_search_podcasts.get_property('visible'):
            def set_search_term(self, text):
                self.podcast_list_model.set_search_term(text)
                self._podcast_list_search_timeout = None
                return False

            if self._podcast_list_search_timeout is not None:
                gobject.source_remove(self._podcast_list_search_timeout)
            self._podcast_list_search_timeout = gobject.timeout_add(
                    self.config.ui.gtk.live_search_delay,
                    set_search_term, self, editable.get_chars(0, -1))

    def on_entry_search_podcasts_key_press(self, editable, event):
        if event.keyval == gtk.keysyms.Escape:
            self.hide_podcast_search()
            return True

    def hide_podcast_search(self, *args):
        if self._podcast_list_search_timeout is not None:
            gobject.source_remove(self._podcast_list_search_timeout)
            self._podcast_list_search_timeout = None
        self.hbox_search_podcasts.hide()
        self.entry_search_podcasts.set_text('')
        self.podcast_list_model.set_search_term(None)
        self.treeChannels.grab_focus()

    def show_podcast_search(self, input_char):
        self.hbox_search_podcasts.show()
        self.entry_search_podcasts.insert_text(input_char, -1)
        self.entry_search_podcasts.grab_focus()
        self.entry_search_podcasts.set_position(-1)

    def init_podcast_list_treeview(self):
        # Set up podcast channel tree view widget
        column = gtk.TreeViewColumn('')
        iconcell = gtk.CellRendererPixbuf()
        iconcell.set_property('width', 45)
        column.pack_start(iconcell, False)
        column.add_attribute(iconcell, 'pixbuf', PodcastListModel.C_COVER)
        column.add_attribute(iconcell, 'visible', PodcastListModel.C_COVER_VISIBLE)

        namecell = gtk.CellRendererText()
        namecell.set_property('ellipsize', pango.ELLIPSIZE_END)
        column.pack_start(namecell, True)
        column.add_attribute(namecell, 'markup', PodcastListModel.C_DESCRIPTION)

        iconcell = gtk.CellRendererPixbuf()
        iconcell.set_property('xalign', 1.0)
        column.pack_start(iconcell, False)
        column.add_attribute(iconcell, 'pixbuf', PodcastListModel.C_PILL)
        column.add_attribute(iconcell, 'visible', PodcastListModel.C_PILL_VISIBLE)

        self.treeChannels.append_column(column)

        self.treeChannels.set_model(self.podcast_list_model.get_filtered_model())

        # When no podcast is selected, clear the episode list model
        selection = self.treeChannels.get_selection()
        def select_function(selection, model, path, path_currently_selected):
            url = model.get_value(model.get_iter(path), PodcastListModel.C_URL)
            return (url != '-')
        selection.set_select_function(select_function, full=True)

        # Set up type-ahead find for the podcast list
        def on_key_press(treeview, event):
            if event.keyval == gtk.keysyms.Right:
                self.treeAvailable.grab_focus()
            elif event.keyval in (gtk.keysyms.Up, gtk.keysyms.Down):
                # If section markers exist in the treeview, we want to
                # "jump over" them when moving the cursor up and down
                selection = self.treeChannels.get_selection()
                model, it = selection.get_selected()

                if event.keyval == gtk.keysyms.Up:
                    step = -1
                else:
                    step = 1

                path = model.get_path(it)
                while True:
                    path = (path[0]+step,)

                    if path[0] < 0:
                        # Valid paths must have a value >= 0
                        return True

                    try:
                        it = model.get_iter(path)
                    except ValueError:
                        # Already at the end of the list
                        return True

                    if model.get_value(it, PodcastListModel.C_URL) != '-':
                        break

                self.treeChannels.set_cursor(path)
            elif event.keyval == gtk.keysyms.Escape:
                self.hide_podcast_search()
            elif event.state & gtk.gdk.CONTROL_MASK:
                # Don't handle type-ahead when control is pressed (so shortcuts
                # with the Ctrl key still work, e.g. Ctrl+A, ...)
                return True
            else:
                unicode_char_id = gtk.gdk.keyval_to_unicode(event.keyval)
                if unicode_char_id == 0:
                    return False
                input_char = unichr(unicode_char_id)
                self.show_podcast_search(input_char)
            return True
        self.treeChannels.connect('key-press-event', on_key_press)

        self.treeChannels.connect('popup-menu', self.treeview_channels_show_context_menu)

        # Enable separators to the podcast list to separate special podcasts
        # from others (this is used for the "all episodes" view)
        self.treeChannels.set_row_separator_func(PodcastListModel.row_separator_func)

        TreeViewHelper.set(self.treeChannels, TreeViewHelper.ROLE_PODCASTS)

    def on_entry_search_episodes_changed(self, editable):
        if self.hbox_search_episodes.get_property('visible'):
            def set_search_term(self, text):
                self.episode_list_model.set_search_term(text)
                self._episode_list_search_timeout = None
                return False

            if self._episode_list_search_timeout is not None:
                gobject.source_remove(self._episode_list_search_timeout)
            self._episode_list_search_timeout = gobject.timeout_add(
                    self.config.ui.gtk.live_search_delay,
                    set_search_term, self, editable.get_chars(0, -1))

    def on_entry_search_episodes_key_press(self, editable, event):
        if event.keyval == gtk.keysyms.Escape:
            self.hide_episode_search()
            return True

    def hide_episode_search(self, *args):
        if self._episode_list_search_timeout is not None:
            gobject.source_remove(self._episode_list_search_timeout)
            self._episode_list_search_timeout = None
        self.hbox_search_episodes.hide()
        self.entry_search_episodes.set_text('')
        self.episode_list_model.set_search_term(None)
        self.treeAvailable.grab_focus()

    def show_episode_search(self, input_char):
        self.hbox_search_episodes.show()
        self.entry_search_episodes.insert_text(input_char, -1)
        self.entry_search_episodes.grab_focus()
        self.entry_search_episodes.set_position(-1)

    def set_episode_list_column(self, index, new_value):
        mask = (1 << index)
        if new_value:
            self.config.episode_list_columns |= mask
        else:
            self.config.episode_list_columns &= ~mask

    def update_episode_list_columns_visibility(self):
        columns = TreeViewHelper.get_columns(self.treeAvailable)
        for index, column in enumerate(columns):
            visible = bool(self.config.episode_list_columns & (1 << index))
            column.set_visible(visible)
        self.treeAvailable.columns_autosize()

        if self.episode_columns_menu is not None:
            children = self.episode_columns_menu.get_children()
            for index, child in enumerate(children):
                active = bool(self.config.episode_list_columns & (1 << index))
                child.set_active(active)

    def on_episode_list_header_clicked(self, button, event):
        if event.button != 3:
            return False

        if self.episode_columns_menu is not None:
            self.episode_columns_menu.popup(None, None, None, event.button, \
                    event.time, None)

        return False

    def init_episode_list_treeview(self):
        # For loading the list model
        self.episode_list_model = EpisodeListModel(self.config, self.on_episode_list_filter_changed)

        if self.config.episode_list_view_mode == EpisodeListModel.VIEW_UNDELETED:
            self.item_view_episodes_undeleted.set_active(True)
        elif self.config.episode_list_view_mode == EpisodeListModel.VIEW_DOWNLOADED:
            self.item_view_episodes_downloaded.set_active(True)
        elif self.config.episode_list_view_mode == EpisodeListModel.VIEW_UNPLAYED:
            self.item_view_episodes_unplayed.set_active(True)
        else:
            self.item_view_episodes_all.set_active(True)

        self.episode_list_model.set_view_mode(self.config.episode_list_view_mode)

        self.treeAvailable.set_model(self.episode_list_model.get_filtered_model())

        TreeViewHelper.set(self.treeAvailable, TreeViewHelper.ROLE_EPISODES)

        iconcell = gtk.CellRendererPixbuf()
        episode_list_icon_size = gtk.icon_size_register('episode-list',
            EPISODE_LIST_ICON_SIZE, EPISODE_LIST_ICON_SIZE)
        iconcell.set_property('stock-size', episode_list_icon_size)
        iconcell.set_fixed_size(self.EPISODE_LIST_ICON_WIDTH, -1)

        namecell = gtk.CellRendererText()
        namecell.set_property('ellipsize', pango.ELLIPSIZE_END)
        namecolumn = gtk.TreeViewColumn(_('Episode'))
        namecolumn.pack_start(iconcell, False)
        namecolumn.add_attribute(iconcell, 'icon-name', EpisodeListModel.C_STATUS_ICON)
        namecolumn.pack_start(namecell, True)
        namecolumn.add_attribute(namecell, 'markup', EpisodeListModel.C_DESCRIPTION)
        namecolumn.set_sort_column_id(EpisodeListModel.C_DESCRIPTION)
        namecolumn.set_sizing(gtk.TREE_VIEW_COLUMN_AUTOSIZE)
        namecolumn.set_resizable(True)
        namecolumn.set_expand(True)

        lockcell = gtk.CellRendererPixbuf()
        lockcell.set_fixed_size(40, -1)
        lockcell.set_property('stock-size', gtk.ICON_SIZE_MENU)
        lockcell.set_property('icon-name', 'emblem-readonly')
        namecolumn.pack_start(lockcell, False)
        namecolumn.add_attribute(lockcell, 'visible', EpisodeListModel.C_LOCKED)

        sizecell = gtk.CellRendererText()
        sizecell.set_property('xalign', 1)
        sizecolumn = gtk.TreeViewColumn(_('Size'), sizecell, text=EpisodeListModel.C_FILESIZE_TEXT)
        sizecolumn.set_sort_column_id(EpisodeListModel.C_FILESIZE)

        timecell = gtk.CellRendererText()
        timecell.set_property('xalign', 1)
        timecolumn = gtk.TreeViewColumn(_('Duration'), timecell, text=EpisodeListModel.C_TIME)
        timecolumn.set_sort_column_id(EpisodeListModel.C_TOTAL_TIME)

        releasecell = gtk.CellRendererText()
        releasecolumn = gtk.TreeViewColumn(_('Released'), releasecell, text=EpisodeListModel.C_PUBLISHED_TEXT)
        releasecolumn.set_sort_column_id(EpisodeListModel.C_PUBLISHED)

        namecolumn.set_reorderable(True)
        self.treeAvailable.append_column(namecolumn)

        for itemcolumn in (sizecolumn, timecolumn, releasecolumn):
            itemcolumn.set_reorderable(True)
            self.treeAvailable.append_column(itemcolumn)
            TreeViewHelper.register_column(self.treeAvailable, itemcolumn)

        # Add context menu to all tree view column headers
        for column in self.treeAvailable.get_columns():
            label = gtk.Label(column.get_title())
            label.show_all()
            column.set_widget(label)

            w = column.get_widget()
            while w is not None and not isinstance(w, gtk.Button):
                w = w.get_parent()

            w.connect('button-release-event', self.on_episode_list_header_clicked)

        # Create a new menu for the visible episode list columns
        for child in self.mainMenu.get_children():
            if child.get_name() == 'menuView':
                submenu = child.get_submenu()
                item = gtk.MenuItem(_('Visible columns'))
                submenu.append(gtk.SeparatorMenuItem())
                submenu.append(item)
                submenu.show_all()

                self.episode_columns_menu = gtk.Menu()
                item.set_submenu(self.episode_columns_menu)
                break

        # For each column that can be shown/hidden, add a menu item
        columns = TreeViewHelper.get_columns(self.treeAvailable)
        for index, column in enumerate(columns):
            item = gtk.CheckMenuItem(column.get_title())
            self.episode_columns_menu.append(item)
            def on_item_toggled(item, index):
                self.set_episode_list_column(index, item.get_active())
            item.connect('toggled', on_item_toggled, index)
        self.episode_columns_menu.show_all()

        # Update the visibility of the columns and the check menu items
        self.update_episode_list_columns_visibility()

        # Set up type-ahead find for the episode list
        def on_key_press(treeview, event):
            if event.keyval == gtk.keysyms.Left:
                self.treeChannels.grab_focus()
            elif event.keyval == gtk.keysyms.Escape:
                if self.hbox_search_episodes.get_property('visible'):
                    self.hide_episode_search()
                else:
                    self.shownotes_object.hide_pane()
            elif event.state & gtk.gdk.CONTROL_MASK:
                # Don't handle type-ahead when control is pressed (so shortcuts
                # with the Ctrl key still work, e.g. Ctrl+A, ...)
                return False
            else:
                unicode_char_id = gtk.gdk.keyval_to_unicode(event.keyval)
                if unicode_char_id == 0:
                    return False
                input_char = unichr(unicode_char_id)
                self.show_episode_search(input_char)
            return True
        self.treeAvailable.connect('key-press-event', on_key_press)

        self.treeAvailable.connect('popup-menu', self.treeview_available_show_context_menu)

        self.treeAvailable.enable_model_drag_source(gtk.gdk.BUTTON1_MASK, \
                (('text/uri-list', 0, 0),), gtk.gdk.ACTION_COPY)
        def drag_data_get(tree, context, selection_data, info, timestamp):
            uris = ['file://'+e.local_filename(create=False) \
                    for e in self.get_selected_episodes() \
                    if e.was_downloaded(and_exists=True)]
            uris.append('') # for the trailing '\r\n'
            selection_data.set(selection_data.target, 8, '\r\n'.join(uris))
        self.treeAvailable.connect('drag-data-get', drag_data_get)

        selection = self.treeAvailable.get_selection()
        selection.set_mode(gtk.SELECTION_MULTIPLE)
        selection.connect('changed', self.on_episode_list_selection_changed)

    def on_episode_list_selection_changed(self, selection):
        # Update the toolbar buttons
        self.play_or_download()
        # and the shownotes
        self.shownotes_object.set_episodes(self.get_selected_episodes())

    def init_download_list_treeview(self):
        # enable multiple selection support
        self.treeDownloads.get_selection().set_mode(gtk.SELECTION_MULTIPLE)
        self.treeDownloads.set_search_equal_func(TreeViewHelper.make_search_equal_func(DownloadStatusModel))

        # columns and renderers for "download progress" tab
        # First column: [ICON] Episodename
        column = gtk.TreeViewColumn(_('Episode'))

        cell = gtk.CellRendererPixbuf()
        cell.set_property('stock-size', gtk.ICON_SIZE_BUTTON)
        column.pack_start(cell, expand=False)
        column.add_attribute(cell, 'icon-name', \
                DownloadStatusModel.C_ICON_NAME)

        cell = gtk.CellRendererText()
        cell.set_property('ellipsize', pango.ELLIPSIZE_END)
        column.pack_start(cell, expand=True)
        column.add_attribute(cell, 'markup', DownloadStatusModel.C_NAME)
        column.set_sizing(gtk.TREE_VIEW_COLUMN_AUTOSIZE)
        column.set_expand(True)
        self.treeDownloads.append_column(column)

        # Second column: Progress
        cell = gtk.CellRendererProgress()
        cell.set_property('yalign', .5)
        cell.set_property('ypad', 6)
        column = gtk.TreeViewColumn(_('Progress'), cell,
                value=DownloadStatusModel.C_PROGRESS, \
                text=DownloadStatusModel.C_PROGRESS_TEXT)
        column.set_sizing(gtk.TREE_VIEW_COLUMN_AUTOSIZE)
        column.set_expand(False)
        self.treeDownloads.append_column(column)
        column.set_property('min-width', 150)
        column.set_property('max-width', 150)

        self.treeDownloads.set_model(self.download_status_model)
        TreeViewHelper.set(self.treeDownloads, TreeViewHelper.ROLE_DOWNLOADS)

        self.treeDownloads.connect('popup-menu', self.treeview_downloads_show_context_menu)

    def on_treeview_expose_event(self, treeview, event):
        if event.window == treeview.get_bin_window():
            model = treeview.get_model()
            if (model is not None and model.get_iter_first() is not None):
                return False

            role = getattr(treeview, TreeViewHelper.ROLE, None)
            if role is None:
                return False

            ctx = event.window.cairo_create()
            ctx.rectangle(event.area.x, event.area.y,
                    event.area.width, event.area.height)
            ctx.clip()

            x, y, width, height, depth = event.window.get_geometry()
            progress = None

            if role == TreeViewHelper.ROLE_EPISODES:
                if self.currently_updating:
                    text = _('Loading episodes')
                elif self.config.episode_list_view_mode != \
                        EpisodeListModel.VIEW_ALL:
                    text = _('No episodes in current view')
                else:
                    text = _('No episodes available')
            elif role == TreeViewHelper.ROLE_PODCASTS:
                if self.config.episode_list_view_mode != \
                        EpisodeListModel.VIEW_ALL and \
                        self.config.podcast_list_hide_boring and \
                        len(self.channels) > 0:
                    text = _('No podcasts in this view')
                else:
                    text = _('No subscriptions')
            elif role == TreeViewHelper.ROLE_DOWNLOADS:
                text = _('No active tasks')
            else:
                raise Exception('on_treeview_expose_event: unknown role')

            font_desc = None
            draw_text_box_centered(ctx, treeview, width, height, text, font_desc, progress)

        return False

    def enable_download_list_update(self):
        if not self.download_list_update_enabled:
            self.update_downloads_list()
            gobject.timeout_add(1500, self.update_downloads_list)
            self.download_list_update_enabled = True

    def cleanup_downloads(self):
        model = self.download_status_model

        all_tasks = [(gtk.TreeRowReference(model, row.path), row[0]) for row in model]
        changed_episode_urls = set()
        for row_reference, task in all_tasks:
            if task.status in (task.DONE, task.CANCELLED):
                model.remove(model.get_iter(row_reference.get_path()))
                try:
                    # We don't "see" this task anymore - remove it;
                    # this is needed, so update_episode_list_icons()
                    # below gets the correct list of "seen" tasks
                    self.download_tasks_seen.remove(task)
                except KeyError, key_error:
                    pass
                changed_episode_urls.add(task.url)
                # Tell the task that it has been removed (so it can clean up)
                task.removed_from_list()

        # Tell the podcasts tab to update icons for our removed podcasts
        self.update_episode_list_icons(changed_episode_urls)

        # Update the downloads list one more time
        self.update_downloads_list(can_call_cleanup=False)

    def on_tool_downloads_toggled(self, toolbutton):
        if toolbutton.get_active():
            self.wNotebook.set_current_page(1)
        else:
            self.wNotebook.set_current_page(0)

    def add_download_task_monitor(self, monitor):
        self.download_task_monitors.add(monitor)
        model = self.download_status_model
        if model is None:
            model = ()
        for row in model:
            task = row[self.download_status_model.C_TASK]
            monitor.task_updated(task)

    def remove_download_task_monitor(self, monitor):
        self.download_task_monitors.remove(monitor)

    def set_download_progress(self, progress):
        gpodder.user_extensions.on_download_progress(progress)

    def update_downloads_list(self, can_call_cleanup=True):
        try:
            model = self.download_status_model

            downloading, synchronizing, failed, finished, queued, paused, others = 0, 0, 0, 0, 0, 0, 0
            total_speed, total_size, done_size = 0, 0, 0

            # Keep a list of all download tasks that we've seen
            download_tasks_seen = set()

            # Do not go through the list of the model is not (yet) available
            if model is None:
                model = ()

            for row in model:
                self.download_status_model.request_update(row.iter)

                task = row[self.download_status_model.C_TASK]
                speed, size, status, progress, activity = task.speed, task.total_size, task.status, task.progress, task.activity

                # Let the download task monitors know of changes
                for monitor in self.download_task_monitors:
                    monitor.task_updated(task)

                total_size += size
                done_size += size*progress

                download_tasks_seen.add(task)

                if (status == download.DownloadTask.DOWNLOADING and
                        activity == download.DownloadTask.ACTIVITY_DOWNLOAD):
                    downloading += 1
                    total_speed += speed
                elif (status == download.DownloadTask.DOWNLOADING and
                        activity == download.DownloadTask.ACTIVITY_SYNCHRONIZE):
                    synchronizing += 1
                elif status == download.DownloadTask.FAILED:
                    failed += 1
                elif status == download.DownloadTask.DONE:
                    finished += 1
                elif status == download.DownloadTask.QUEUED:
                    queued += 1
                elif status == download.DownloadTask.PAUSED:
                    paused += 1
                else:
                    others += 1

            # Remember which tasks we have seen after this run
            self.download_tasks_seen = download_tasks_seen

            text = [_('Progress')]
            if downloading + failed + queued + synchronizing > 0:
                s = []
                if downloading > 0:
                    s.append(N_('%(count)d active', '%(count)d active', downloading) % {'count':downloading})
                if synchronizing > 0:
                    s.append(N_('%(count)d active', '%(count)d active', synchronizing) % {'count':synchronizing})
                if failed > 0:
                    s.append(N_('%(count)d failed', '%(count)d failed', failed) % {'count':failed})
                if queued > 0:
                    s.append(N_('%(count)d queued', '%(count)d queued', queued) % {'count':queued})
                text.append(' (' + ', '.join(s)+')')
            self.labelDownloads.set_text(''.join(text))

            title = [self.default_title]

            # Accessing task.status_changed has the side effect of re-setting
            # the changed flag, but we only do it once here so that's okay
            channel_urls = [task.podcast_url for task in
                    self.download_tasks_seen if task.status_changed]
            episode_urls = [task.url for task in self.download_tasks_seen]


            if downloading > 0:
                title.append(N_('downloading %(count)d file', 'downloading %(count)d files', downloading) % {'count':downloading})

                if total_size > 0:
                    percentage = 100.0*done_size/total_size
                else:
                    percentage = 0.0
                self.set_download_progress(percentage/100.)
                total_speed = util.format_filesize(total_speed)
                title[1] += ' (%d%%, %s/s)' % (percentage, total_speed)
            if synchronizing > 0:
                title.append(N_('synchronizing %(count)d file', 'synchronizing %(count)d files', synchronizing) % {'count':synchronizing})
            if queued > 0:
                title.append(N_('%(queued)d task queued', '%(queued)d tasks queued', queued) % {'queued':queued})
            if (downloading + synchronizing + queued)==0:
                self.set_download_progress(1.)
                self.downloads_finished(self.download_tasks_seen)
                gpodder.user_extensions.on_all_episodes_downloaded()
                logger.info('All tasks have finished.')

                # Remove finished episodes
                if self.config.auto_cleanup_downloads and can_call_cleanup:
                    self.cleanup_downloads()

                # Stop updating the download list here
                self.download_list_update_enabled = False

            self.gPodder.set_title(' - '.join(title))

            self.update_episode_list_icons(episode_urls)
            self.play_or_download()
            if channel_urls:
                self.update_podcast_list_model(channel_urls)

            return self.download_list_update_enabled
        except Exception, e:
            logger.error('Exception happened while updating download list.', exc_info=True)
            self.show_message('%s\n\n%s' % (_('Please report this problem and restart gPodder:'), str(e)), _('Unhandled exception'), important=True)
            # We return False here, so the update loop won't be called again,
            # that's why we require the restart of gPodder in the message.
            return False

    def on_config_changed(self, *args):
        util.idle_add(self._on_config_changed, *args)

    def _on_config_changed(self, name, old_value, new_value):
        if name == 'ui.gtk.toolbar':
            self.toolbar.set_property('visible', new_value)
        elif name == 'ui.gtk.episode_list.descriptions':
            self.update_episode_list_model()
        elif name in ('auto.update.enabled', 'auto.update.frequency'):
            self.restart_auto_update_timer()
        elif name in ('ui.gtk.podcast_list.all_episodes',
                'ui.gtk.podcast_list.sections'):
            # Force a update of the podcast list model
            self.update_podcast_list_model()
        elif name == 'ui.gtk.episode_list.columns':
            self.update_episode_list_columns_visibility()

    def on_treeview_query_tooltip(self, treeview, x, y, keyboard_tooltip, tooltip):
        # With get_bin_window, we get the window that contains the rows without
        # the header. The Y coordinate of this window will be the height of the
        # treeview header. This is the amount we have to subtract from the
        # event's Y coordinate to get the coordinate to pass to get_path_at_pos
        (x_bin, y_bin) = treeview.get_bin_window().get_position()
        y -= x_bin
        y -= y_bin
        (path, column, rx, ry) = treeview.get_path_at_pos( x, y) or (None,)*4

        if not getattr(treeview, TreeViewHelper.CAN_TOOLTIP) or x > 50 or (column is not None and column != treeview.get_columns()[0]):
            setattr(treeview, TreeViewHelper.LAST_TOOLTIP, None)
            return False

        if path is not None:
            model = treeview.get_model()
            iter = model.get_iter(path)
            role = getattr(treeview, TreeViewHelper.ROLE)

            if role == TreeViewHelper.ROLE_EPISODES:
                id = model.get_value(iter, EpisodeListModel.C_URL)
            elif role == TreeViewHelper.ROLE_PODCASTS:
                id = model.get_value(iter, PodcastListModel.C_URL)
                if id == '-':
                    # Section header - no tooltip here (for now at least)
                    return False

            last_tooltip = getattr(treeview, TreeViewHelper.LAST_TOOLTIP)
            if last_tooltip is not None and last_tooltip != id:
                setattr(treeview, TreeViewHelper.LAST_TOOLTIP, None)
                return False
            setattr(treeview, TreeViewHelper.LAST_TOOLTIP, id)

            if role == TreeViewHelper.ROLE_EPISODES:
                description = model.get_value(iter, EpisodeListModel.C_TOOLTIP)
                if description:
                    tooltip.set_text(description)
                else:
                    return False
            elif role == TreeViewHelper.ROLE_PODCASTS:
                channel = model.get_value(iter, PodcastListModel.C_CHANNEL)
                if channel is None or not hasattr(channel, 'title'):
                    return False
                error_str = model.get_value(iter, PodcastListModel.C_ERROR)
                if error_str:
                    error_str = _('Feedparser error: %s') % cgi.escape(error_str.strip())
                    error_str = '<span foreground="#ff0000">%s</span>' % error_str
                table = gtk.Table(rows=3, columns=3)
                table.set_row_spacings(5)
                table.set_col_spacings(5)
                table.set_border_width(5)

                heading = gtk.Label()
                heading.set_alignment(0, 1)
                heading.set_markup('<b><big>%s</big></b>\n<small>%s</small>' % (cgi.escape(channel.title), cgi.escape(channel.url)))
                table.attach(heading, 0, 1, 0, 1)

                table.attach(gtk.HSeparator(), 0, 3, 1, 2)

                if len(channel.description) < 500:
                    description = channel.description
                else:
                    pos = channel.description.find('\n\n')
                    if pos == -1 or pos > 500:
                        description = channel.description[:498]+'[...]'
                    else:
                        description = channel.description[:pos]

                description = gtk.Label(description)
                if error_str:
                    description.set_markup(error_str)
                description.set_alignment(0, 0)
                description.set_line_wrap(True)
                table.attach(description, 0, 3, 2, 3)

                table.show_all()
                tooltip.set_custom(table)

            return True

        setattr(treeview, TreeViewHelper.LAST_TOOLTIP, None)
        return False

    def treeview_allow_tooltips(self, treeview, allow):
        setattr(treeview, TreeViewHelper.CAN_TOOLTIP, allow)

    def treeview_handle_context_menu_click(self, treeview, event):
        if event is None:
            selection = treeview.get_selection()
            return selection.get_selected_rows()

        x, y = int(event.x), int(event.y)
        path, column, rx, ry = treeview.get_path_at_pos(x, y) or (None,)*4

        selection = treeview.get_selection()
        model, paths = selection.get_selected_rows()

        if path is None or (path not in paths and \
                event.button == 3):
            # We have right-clicked, but not into the selection,
            # assume we don't want to operate on the selection
            paths = []

        if path is not None and not paths and \
                event.button == 3:
            # No selection or clicked outside selection;
            # select the single item where we clicked
            treeview.grab_focus()
            treeview.set_cursor(path, column, 0)
            paths = [path]

        if not paths:
            # Unselect any remaining items (clicked elsewhere)
            if hasattr(treeview, 'is_rubber_banding_active'):
                if not treeview.is_rubber_banding_active():
                    selection.unselect_all()
            else:
                selection.unselect_all()

        return model, paths

    def downloads_list_get_selection(self, model=None, paths=None):
        if model is None and paths is None:
            selection = self.treeDownloads.get_selection()
            model, paths = selection.get_selected_rows()

        can_queue, can_cancel, can_pause, can_remove, can_force = (True,)*5
        selected_tasks = [(gtk.TreeRowReference(model, path), \
                           model.get_value(model.get_iter(path), \
                           DownloadStatusModel.C_TASK)) for path in paths]

        for row_reference, task in selected_tasks:
            if task.status != download.DownloadTask.QUEUED:
                can_force = False
            if task.status not in (download.DownloadTask.PAUSED, \
                    download.DownloadTask.FAILED, \
                    download.DownloadTask.CANCELLED):
                can_queue = False
            if task.status not in (download.DownloadTask.PAUSED, \
                    download.DownloadTask.QUEUED, \
                    download.DownloadTask.DOWNLOADING, \
                    download.DownloadTask.FAILED):
                can_cancel = False
            if task.status not in (download.DownloadTask.QUEUED, \
                    download.DownloadTask.DOWNLOADING):
                can_pause = False
            if task.status not in (download.DownloadTask.CANCELLED, \
                    download.DownloadTask.FAILED, \
                    download.DownloadTask.DONE):
                can_remove = False

        return selected_tasks, can_queue, can_cancel, can_pause, can_remove, can_force

    def downloads_finished(self, download_tasks_seen):
        # Separate tasks into downloads & syncs
        # Since calling notify_as_finished or notify_as_failed clears the flag,
        # need to iterate through downloads & syncs separately, else all sync
        # tasks will have their flags cleared if we do downloads first

        def filter_by_activity(activity, tasks):
            return filter(lambda task: task.activity == activity, tasks)

        download_tasks = filter_by_activity(download.DownloadTask.ACTIVITY_DOWNLOAD,
                download_tasks_seen)

        finished_downloads = [str(task)
                for task in download_tasks if task.notify_as_finished()]
        failed_downloads = ['%s (%s)' % (str(task), task.error_message)
                for task in download_tasks if task.notify_as_failed()]

        sync_tasks = filter_by_activity(download.DownloadTask.ACTIVITY_SYNCHRONIZE,
                download_tasks_seen)

        finished_syncs = [task for task in sync_tasks if task.notify_as_finished()]
        failed_syncs = [task for task in sync_tasks if task.notify_as_failed()]

        # Note that 'finished_ / failed_downloads' is a list of strings
        # Whereas 'finished_ / failed_syncs' is a list of SyncTask objects

        if finished_downloads and failed_downloads:
            message = self.format_episode_list(finished_downloads, 5)
            message += '\n\n<i>%s</i>\n' % _('Could not download some episodes:')
            message += self.format_episode_list(failed_downloads, 5)
            self.show_message(message, _('Downloads finished'), widget=self.labelDownloads)
        elif finished_downloads:
            message = self.format_episode_list(finished_downloads)
            self.show_message(message, _('Downloads finished'), widget=self.labelDownloads)
        elif failed_downloads:
            message = self.format_episode_list(failed_downloads)
            self.show_message(message, _('Downloads failed'), widget=self.labelDownloads)

        if finished_syncs and failed_syncs:
            message = self.format_episode_list(map((lambda task: str(task)),finished_syncs), 5)
            message += '\n\n<i>%s</i>\n' % _('Could not sync some episodes:')
            message += self.format_episode_list(map((lambda task: str(task)),failed_syncs), 5)
            self.show_message(message, _('Device synchronization finished'), True, widget=self.labelDownloads)
        elif finished_syncs:
            message = self.format_episode_list(map((lambda task: str(task)),finished_syncs))
            self.show_message(message, _('Device synchronization finished'), widget=self.labelDownloads)
        elif failed_syncs:
            message = self.format_episode_list(map((lambda task: str(task)),failed_syncs))
            self.show_message(message, _('Device synchronization failed'), True, widget=self.labelDownloads)

        # Do post-sync processing if required
        for task in finished_syncs + failed_syncs:
            if self.config.device_sync.after_sync.mark_episodes_played:
                logger.info('Marking as played on transfer: %s', task.episode.url)
                task.episode.mark(is_played=True)

            if self.config.device_sync.after_sync.delete_episodes:
                logger.info('Removing episode after transfer: %s', task.episode.url)
                task.episode.delete_from_disk()

            self.sync_ui.device.close()

        # Update icon list to show changes, if any
        self.update_episode_list_icons(all=True)


    def format_episode_list(self, episode_list, max_episodes=10):
        """
        Format a list of episode names for notifications

        Will truncate long episode names and limit the amount of
        episodes displayed (max_episodes=10).

        The episode_list parameter should be a list of strings.
        """
        MAX_TITLE_LENGTH = 100

        result = []
        for title in episode_list[:min(len(episode_list), max_episodes)]:
            # Bug 1834: make sure title is a unicode string,
            # so it may be cut correctly on UTF-8 char boundaries
            title = util.convert_bytes(title)
            if len(title) > MAX_TITLE_LENGTH:
                middle = (MAX_TITLE_LENGTH/2)-2
                title = '%s...%s' % (title[0:middle], title[-middle:])
            result.append(cgi.escape(title))
            result.append('\n')

        more_episodes = len(episode_list) - max_episodes
        if more_episodes > 0:
            result.append('(...')
            result.append(N_('%(count)d more episode', '%(count)d more episodes', more_episodes) % {'count':more_episodes})
            result.append('...)')

        return (''.join(result)).strip()

    def _for_each_task_set_status(self, tasks, status, force_start=False):
        episode_urls = set()
        model = self.treeDownloads.get_model()
        for row_reference, task in tasks:
            if status == download.DownloadTask.QUEUED:
                # Only queue task when its paused/failed/cancelled (or forced)
                if task.status in (task.PAUSED, task.FAILED, task.CANCELLED) or force_start:
                    self.download_queue_manager.add_task(task, force_start)
                    self.enable_download_list_update()
            elif status == download.DownloadTask.CANCELLED:
                # Cancelling a download allowed when downloading/queued
                if task.status in (task.QUEUED, task.DOWNLOADING):
                    task.status = status
                # Cancelling paused/failed downloads requires a call to .run()
                elif task.status in (task.PAUSED, task.FAILED):
                    task.status = status
                    # Call run, so the partial file gets deleted
                    task.run()
            elif status == download.DownloadTask.PAUSED:
                # Pausing a download only when queued/downloading
                if task.status in (task.DOWNLOADING, task.QUEUED):
                    task.status = status
            elif status is None:
                # Remove the selected task - cancel downloading/queued tasks
                if task.status in (task.QUEUED, task.DOWNLOADING):
                    task.status = task.CANCELLED
                model.remove(model.get_iter(row_reference.get_path()))
                # Remember the URL, so we can tell the UI to update
                try:
                    # We don't "see" this task anymore - remove it;
                    # this is needed, so update_episode_list_icons()
                    # below gets the correct list of "seen" tasks
                    self.download_tasks_seen.remove(task)
                except KeyError, key_error:
                    pass
                episode_urls.add(task.url)
                # Tell the task that it has been removed (so it can clean up)
                task.removed_from_list()
            else:
                # We can (hopefully) simply set the task status here
                task.status = status
        # Tell the podcasts tab to update icons for our removed podcasts
        self.update_episode_list_icons(episode_urls)
        # Update the tab title and downloads list
        self.update_downloads_list()

    def treeview_downloads_show_context_menu(self, treeview, event=None):
        model, paths = self.treeview_handle_context_menu_click(treeview, event)
        if not paths:
            if not hasattr(treeview, 'is_rubber_banding_active'):
                return True
            else:
                return not treeview.is_rubber_banding_active()

        if event is None or event.button == 3:
            selected_tasks, can_queue, can_cancel, can_pause, can_remove, can_force = \
                    self.downloads_list_get_selection(model, paths)

            def make_menu_item(label, stock_id, tasks, status, sensitive, force_start=False):
                # This creates a menu item for selection-wide actions
                item = gtk.ImageMenuItem(label)
                item.set_image(gtk.image_new_from_stock(stock_id, gtk.ICON_SIZE_MENU))
                item.connect('activate', lambda item: self._for_each_task_set_status(tasks, status, force_start))
                item.set_sensitive(sensitive)
                return item

            menu = gtk.Menu()

            if can_force:
                menu.append(make_menu_item(_('Start download now'), gtk.STOCK_GO_DOWN, selected_tasks, download.DownloadTask.QUEUED, True, True))
            else:
                menu.append(make_menu_item(_('Download'), gtk.STOCK_GO_DOWN, selected_tasks, download.DownloadTask.QUEUED, can_queue, False))
            menu.append(make_menu_item(_('Cancel'), gtk.STOCK_CANCEL, selected_tasks, download.DownloadTask.CANCELLED, can_cancel))
            menu.append(make_menu_item(_('Pause'), gtk.STOCK_MEDIA_PAUSE, selected_tasks, download.DownloadTask.PAUSED, can_pause))
            menu.append(gtk.SeparatorMenuItem())
            menu.append(make_menu_item(_('Remove from list'), gtk.STOCK_REMOVE, selected_tasks, None, can_remove))

            menu.show_all()

            if event is None:
                func = TreeViewHelper.make_popup_position_func(treeview)
                menu.popup(None, None, func, 3, 0)
            else:
                menu.popup(None, None, None, event.button, event.time)
            return True

    def on_mark_episodes_as_old(self, item):
        assert self.active_channel is not None

        for episode in self.active_channel.get_all_episodes():
            if not episode.was_downloaded(and_exists=True):
                episode.mark(is_played=True)

        self.update_podcast_list_model(selected=True)
        self.update_episode_list_icons(all=True)

    def on_open_download_folder(self, item):
        assert self.active_channel is not None
        util.gui_open(self.active_channel.save_dir)

    def treeview_channels_show_context_menu(self, treeview, event=None):
        model, paths = self.treeview_handle_context_menu_click(treeview, event)
        if not paths:
            return True

        # Check for valid channel id, if there's no id then
        # assume that it is a proxy channel or equivalent
        # and cannot be operated with right click
        if self.active_channel.id is None:
            return True

        if event is None or event.button == 3:
            menu = gtk.Menu()

            item = gtk.ImageMenuItem( _('Update podcast'))
            item.set_image(gtk.image_new_from_stock(gtk.STOCK_REFRESH, gtk.ICON_SIZE_MENU))
            item.connect('activate', self.on_itemUpdateChannel_activate)
            menu.append(item)

            menu.append(gtk.SeparatorMenuItem())

            item = gtk.MenuItem(_('Open download folder'))
            item.connect('activate', self.on_open_download_folder)
            menu.append(item)

            menu.append(gtk.SeparatorMenuItem())

            item = gtk.MenuItem(_('Mark episodes as old'))
            item.connect('activate', self.on_mark_episodes_as_old)
            menu.append(item)

            item = gtk.CheckMenuItem(_('Archive'))
            item.set_active(self.active_channel.auto_archive_episodes)
            item.connect('activate', self.on_channel_toggle_lock_activate)
            menu.append(item)

            item = gtk.ImageMenuItem(_('Remove podcast'))
            item.set_image(gtk.image_new_from_stock(gtk.STOCK_DELETE, gtk.ICON_SIZE_MENU))
            item.connect( 'activate', self.on_itemRemoveChannel_activate)
            menu.append( item)

            result = gpodder.user_extensions.on_channel_context_menu(self.active_channel)
            if result:
                menu.append(gtk.SeparatorMenuItem())
                for label, callback in result:
                    item = gtk.MenuItem(label)
                    item.connect('activate', lambda item, callback: callback(self.active_channel), callback)
                    menu.append(item)

            menu.append(gtk.SeparatorMenuItem())

            item = gtk.ImageMenuItem(_('Podcast settings'))
            item.set_image(gtk.image_new_from_stock(gtk.STOCK_INFO, gtk.ICON_SIZE_MENU))
            item.connect('activate', self.on_itemEditChannel_activate)
            menu.append(item)

            menu.show_all()
            # Disable tooltips while we are showing the menu, so
            # the tooltip will not appear over the menu
            self.treeview_allow_tooltips(self.treeChannels, False)
            menu.connect('deactivate', lambda menushell: self.treeview_allow_tooltips(self.treeChannels, True))

            if event is None:
                func = TreeViewHelper.make_popup_position_func(treeview)
                menu.popup(None, None, func, 3, 0)
            else:
                menu.popup(None, None, None, event.button, event.time)

            return True

    def cover_download_finished(self, channel, pixbuf):
        """
        The Cover Downloader calls this when it has finished
        downloading (or registering, if already downloaded)
        a new channel cover, which is ready for displaying.
        """
        util.idle_add(self.podcast_list_model.add_cover_by_channel,
                channel, pixbuf)

    def save_episodes_as_file(self, episodes):
        for episode in episodes:
            self.save_episode_as_file(episode)

    def save_episode_as_file(self, episode):
        PRIVATE_FOLDER_ATTRIBUTE = '_save_episodes_as_file_folder'
        if episode.was_downloaded(and_exists=True):
            folder = getattr(self, PRIVATE_FOLDER_ATTRIBUTE, None)
            copy_from = episode.local_filename(create=False)
            assert copy_from is not None
            copy_to = util.sanitize_filename(episode.sync_filename())
            (result, folder) = self.show_copy_dialog(src_filename=copy_from, dst_filename=copy_to, dst_directory=folder)
            setattr(self, PRIVATE_FOLDER_ATTRIBUTE, folder)

    def copy_episodes_bluetooth(self, episodes):
        episodes_to_copy = [e for e in episodes if e.was_downloaded(and_exists=True)]

        def convert_and_send_thread(episode):
            for episode in episodes:
                filename = episode.local_filename(create=False)
                assert filename is not None
                destfile = os.path.join(tempfile.gettempdir(), \
                        util.sanitize_filename(episode.sync_filename()))
                (base, ext) = os.path.splitext(filename)
                if not destfile.endswith(ext):
                    destfile += ext

                try:
                    shutil.copyfile(filename, destfile)
                    util.bluetooth_send_file(destfile)
                except:
                    logger.error('Cannot copy "%s" to "%s".', filename, destfile)
                    self.notification(_('Error converting file.'), _('Bluetooth file transfer'), important=True)

                util.delete_file(destfile)

        util.run_in_background(lambda: convert_and_send_thread(episodes_to_copy))

    def _add_sub_menu(self, menu, label):
        root_item = gtk.MenuItem(label)
        menu.append(root_item)
        sub_menu = gtk.Menu()
        root_item.set_submenu(sub_menu)
        return sub_menu

    def _submenu_item_activate_hack(self, item, callback, *args):
        # See http://stackoverflow.com/questions/5221326/submenu-item-does-not-call-function-with-working-solution
        # Note that we can't just call the callback on button-press-event, as
        # it might be blocking (see http://gpodder.org/bug/1778), so we run
        # this in the GUI thread at a later point in time (util.idle_add).
        # Also, we also have to connect to the activate signal, as this is the
        # only signal that is fired when keyboard navigation is used.

        # It can happen that both (button-release-event and activate) signals
        # are fired, and we must avoid calling the callback twice. We do this
        # using a semaphore and only acquiring (but never releasing) it, making
        # sure that the util.idle_add() call below is only ever called once.
        only_once = threading.Semaphore(1)

        def handle_event(item, event=None):
            if only_once.acquire(False):
                util.idle_add(callback, *args)

        item.connect('button-press-event', handle_event)
        item.connect('activate', handle_event)

    def treeview_available_show_context_menu(self, treeview, event=None):
        model, paths = self.treeview_handle_context_menu_click(treeview, event)
        if not paths:
            if not hasattr(treeview, 'is_rubber_banding_active'):
                return True
            else:
                return not treeview.is_rubber_banding_active()

        if event is None or event.button == 3:
            episodes = self.get_selected_episodes()
            any_locked = any(e.archive for e in episodes)
            any_new = any(e.is_new for e in episodes)
            any_flattrable = any(e.payment_url for e in episodes)
            downloaded = all(e.was_downloaded(and_exists=True) for e in episodes)
            downloading = any(e.downloading for e in episodes)

            menu = gtk.Menu()

            (can_play, can_download, can_cancel, can_delete, open_instead_of_play) = self.play_or_download()

            if open_instead_of_play:
                item = gtk.ImageMenuItem(gtk.STOCK_OPEN)
            elif downloaded:
                item = gtk.ImageMenuItem(gtk.STOCK_MEDIA_PLAY)
            else:
                if downloading:
                    item = gtk.ImageMenuItem(_('Preview'))
                else:
                    item = gtk.ImageMenuItem(_('Stream'))
                item.set_image(gtk.image_new_from_stock(gtk.STOCK_MEDIA_PLAY, gtk.ICON_SIZE_MENU))

            item.set_sensitive(can_play)
            item.connect('activate', self.on_playback_selected_episodes)
            menu.append(item)

            if not can_cancel:
                item = gtk.ImageMenuItem(_('Download'))
                item.set_image(gtk.image_new_from_stock(gtk.STOCK_GO_DOWN, gtk.ICON_SIZE_MENU))
                item.set_sensitive(can_download)
                item.connect('activate', self.on_download_selected_episodes)
                menu.append(item)
            else:
                item = gtk.ImageMenuItem(gtk.STOCK_CANCEL)
                item.connect('activate', self.on_item_cancel_download_activate)
                menu.append(item)

            item = gtk.ImageMenuItem(gtk.STOCK_DELETE)
            item.set_sensitive(can_delete)
            item.connect('activate', self.on_btnDownloadedDelete_clicked)
            menu.append(item)

            result = gpodder.user_extensions.on_episodes_context_menu(episodes)
            if result:
                menu.append(gtk.SeparatorMenuItem())
                submenus = {}
                for label, callback in result:
                    key, sep, title = label.rpartition('/')
                    item = gtk.ImageMenuItem(title)
                    self._submenu_item_activate_hack(item, callback, episodes)
                    if key:
                        if key not in submenus:
                            sub_menu = self._add_sub_menu(menu, key)
                            submenus[key] = sub_menu
                        else:
                            sub_menu = submenus[key]
                        sub_menu.append(item)
                    else:
                        menu.append(item)

            # Ok, this probably makes sense to only display for downloaded files
            if downloaded:
                menu.append(gtk.SeparatorMenuItem())
                share_menu = self._add_sub_menu(menu, _('Send to'))

                item = gtk.ImageMenuItem(_('Local folder'))
                item.set_image(gtk.image_new_from_stock(gtk.STOCK_DIRECTORY, gtk.ICON_SIZE_MENU))
                self._submenu_item_activate_hack(item, self.save_episodes_as_file, episodes)
                share_menu.append(item)
                if self.bluetooth_available:
                    item = gtk.ImageMenuItem(_('Bluetooth device'))
                    item.set_image(gtk.image_new_from_icon_name('bluetooth', gtk.ICON_SIZE_MENU))
                    self._submenu_item_activate_hack(item, self.copy_episodes_bluetooth, episodes)
                    share_menu.append(item)

            menu.append(gtk.SeparatorMenuItem())

            item = gtk.CheckMenuItem(_('New'))
            item.set_active(any_new)
            if any_new:
                item.connect('activate', lambda w: self.mark_selected_episodes_old())
            else:
                item.connect('activate', lambda w: self.mark_selected_episodes_new())
            menu.append(item)

            if downloaded:
                item = gtk.CheckMenuItem(_('Archive'))
                item.set_active(any_locked)
                item.connect('activate', lambda w: self.on_item_toggle_lock_activate( w, False, not any_locked))
                menu.append(item)

            if any_flattrable and self.config.flattr.token:
                menu.append(gtk.SeparatorMenuItem())
                item = gtk.MenuItem(_('Flattr this'))
                item.connect('activate', self.flattr_selected_episodes)
                menu.append(item)

            menu.append(gtk.SeparatorMenuItem())
            # Single item, add episode information menu item
            item = gtk.ImageMenuItem(_('Episode details'))
            item.set_image(gtk.image_new_from_stock( gtk.STOCK_INFO, gtk.ICON_SIZE_MENU))
            item.connect('activate', self.on_shownotes_selected_episodes)
            menu.append(item)

            menu.show_all()
            # Disable tooltips while we are showing the menu, so
            # the tooltip will not appear over the menu
            self.treeview_allow_tooltips(self.treeAvailable, False)
            menu.connect('deactivate', lambda menushell: self.treeview_allow_tooltips(self.treeAvailable, True))
            if event is None:
                func = TreeViewHelper.make_popup_position_func(treeview)
                menu.popup(None, None, func, 3, 0)
            else:
                menu.popup(None, None, None, event.button, event.time)

            return True

    def set_title(self, new_title):
        self.default_title = new_title
        self.gPodder.set_title(new_title)

    def update_episode_list_icons(self, urls=None, selected=False, all=False):
        """
        Updates the status icons in the episode list.

        If urls is given, it should be a list of URLs
        of episodes that should be updated.

        If urls is None, set ONE OF selected, all to
        True (the former updates just the selected
        episodes and the latter updates all episodes).
        """
        descriptions = self.config.episode_list_descriptions

        if urls is not None:
            # We have a list of URLs to walk through
            self.episode_list_model.update_by_urls(urls, descriptions)
        elif selected and not all:
            # We should update all selected episodes
            selection = self.treeAvailable.get_selection()
            model, paths = selection.get_selected_rows()
            for path in reversed(paths):
                iter = model.get_iter(path)
                self.episode_list_model.update_by_filter_iter(iter, descriptions)
        elif all and not selected:
            # We update all (even the filter-hidden) episodes
            self.episode_list_model.update_all(descriptions)
        else:
            # Wrong/invalid call - have to specify at least one parameter
            raise ValueError('Invalid call to update_episode_list_icons')

    def episode_list_status_changed(self, episodes):
        self.update_episode_list_icons(set(e.url for e in episodes))
        self.update_podcast_list_model(set(e.channel.url for e in episodes))
        self.db.commit()

    def streaming_possible(self):
        # User has to have a media player set on the Desktop, or else we
        # would probably open the browser when giving a URL to xdg-open..
        return (self.config.player and self.config.player != 'default')

    def playback_episodes_for_real(self, episodes):
        groups = collections.defaultdict(list)
        for episode in episodes:
            file_type = episode.file_type()
            if file_type == 'video' and self.config.videoplayer and \
                    self.config.videoplayer != 'default':
                player = self.config.videoplayer
            elif file_type == 'audio' and self.config.player and \
                    self.config.player != 'default':
                player = self.config.player
            else:
                player = 'default'

            # Mark episode as played in the database
            episode.playback_mark()
            self.mygpo_client.on_playback([episode])

            fmt_ids = youtube.get_fmt_ids(self.config.youtube)

            allow_partial = (player != 'default')
            filename = episode.get_playback_url(fmt_ids, allow_partial)

            # Determine the playback resume position - if the file
            # was played 100%, we simply start from the beginning
            resume_position = episode.current_position
            if resume_position == episode.total_time:
                resume_position = 0

            # If Panucci is configured, use D-Bus to call it
            if player == 'panucci':
                try:
                    PANUCCI_NAME = 'org.panucci.panucciInterface'
                    PANUCCI_PATH = '/panucciInterface'
                    PANUCCI_INTF = 'org.panucci.panucciInterface'
                    o = gpodder.dbus_session_bus.get_object(PANUCCI_NAME, PANUCCI_PATH)
                    i = dbus.Interface(o, PANUCCI_INTF)

                    def on_reply(*args):
                        pass

                    def error_handler(filename, err):
                        logger.error('Exception in D-Bus call: %s', str(err))

                        # Fallback: use the command line client
                        for command in util.format_desktop_command('panucci', \
                                [filename]):
                            logger.info('Executing: %s', repr(command))
                            subprocess.Popen(command)

                    on_error = lambda err: error_handler(filename, err)

                    # This method only exists in Panucci > 0.9 ('new Panucci')
                    i.playback_from(filename, resume_position, \
                            reply_handler=on_reply, error_handler=on_error)

                    continue # This file was handled by the D-Bus call
                except Exception, e:
                    logger.error('Calling Panucci using D-Bus', exc_info=True)

            # flattr episode if auto-flattr is enabled
            if (episode.payment_url and self.config.flattr.token and
                    self.config.flattr.flattr_on_play):
                success, message = self.flattr.flattr_url(episode.payment_url)
                self.show_message(message, title=_('Flattr status'),
                        important=not success)

            groups[player].append(filename)

        # Open episodes with system default player
        if 'default' in groups:
            for filename in groups['default']:
                logger.debug('Opening with system default: %s', filename)
                util.gui_open(filename)
            del groups['default']

        # For each type now, go and create play commands
        for group in groups:
            for command in util.format_desktop_command(group, groups[group], resume_position):
                logger.debug('Executing: %s', repr(command))
                subprocess.Popen(command)

        # Persist episode status changes to the database
        self.db.commit()

        # Flush updated episode status
        if self.mygpo_client.can_access_webservice():
            self.mygpo_client.flush()

    def playback_episodes(self, episodes):
        # We need to create a list, because we run through it more than once
        episodes = list(Model.sort_episodes_by_pubdate(e for e in episodes if \
               e.was_downloaded(and_exists=True) or self.streaming_possible()))

        try:
            self.playback_episodes_for_real(episodes)
        except Exception, e:
            logger.error('Error in playback!', exc_info=True)
            self.show_message(_('Please check your media player settings in the preferences dialog.'), \
                    _('Error opening player'), widget=self.toolPreferences)

        channel_urls = set()
        episode_urls = set()
        for episode in episodes:
            channel_urls.add(episode.channel.url)
            episode_urls.add(episode.url)
        self.update_episode_list_icons(episode_urls)
        self.update_podcast_list_model(channel_urls)

    def play_or_download(self):
        if self.wNotebook.get_current_page() > 0:
            self.toolCancel.set_sensitive(True)
            return

        if self.currently_updating:
            return (False, False, False, False, False, False)

        ( can_play, can_download, can_cancel, can_delete ) = (False,)*4
        ( is_played, is_locked ) = (False,)*2

        open_instead_of_play = False

        selection = self.treeAvailable.get_selection()
        if selection.count_selected_rows() > 0:
            (model, paths) = selection.get_selected_rows()

            for path in paths:
                try:
                    episode = model.get_value(model.get_iter(path), EpisodeListModel.C_EPISODE)
                except TypeError, te:
                    logger.error('Invalid episode at path %s', str(path))
                    continue

                if episode.file_type() not in ('audio', 'video'):
                    open_instead_of_play = True

                if episode.was_downloaded():
                    can_play = episode.was_downloaded(and_exists=True)
                    is_played = not episode.is_new
                    is_locked = episode.archive
                    if not can_play:
                        can_download = True
                else:
                    if episode.downloading:
                        can_cancel = True
                    else:
                        can_download = True

            can_download = can_download and not can_cancel
            can_play = self.streaming_possible() or (can_play and not can_cancel and not can_download)
            can_delete = not can_cancel

        if open_instead_of_play:
            self.toolPlay.set_stock_id(gtk.STOCK_OPEN)
        else:
            self.toolPlay.set_stock_id(gtk.STOCK_MEDIA_PLAY)
        self.toolPlay.set_sensitive( can_play)
        self.toolDownload.set_sensitive( can_download)
        self.toolCancel.set_sensitive( can_cancel)

        self.item_cancel_download.set_sensitive(can_cancel)
        self.itemDownloadSelected.set_sensitive(can_download)
        self.itemOpenSelected.set_sensitive(can_play)
        self.itemPlaySelected.set_sensitive(can_play)
        self.itemDeleteSelected.set_sensitive(can_delete)
        self.item_toggle_played.set_sensitive(can_play)
        self.item_toggle_lock.set_sensitive(can_play)
        self.itemOpenSelected.set_visible(open_instead_of_play)
        self.itemPlaySelected.set_visible(not open_instead_of_play)

        return (can_play, can_download, can_cancel, can_delete, open_instead_of_play)

    def on_cbMaxDownloads_toggled(self, widget, *args):
        self.spinMaxDownloads.set_sensitive(self.cbMaxDownloads.get_active())

    def on_cbLimitDownloads_toggled(self, widget, *args):
        self.spinLimitDownloads.set_sensitive(self.cbLimitDownloads.get_active())

    def episode_new_status_changed(self, urls):
        self.update_podcast_list_model()
        self.update_episode_list_icons(urls)

    def update_podcast_list_model(self, urls=None, selected=False, select_url=None,
            sections_changed=False):
        """Update the podcast list treeview model

        If urls is given, it should list the URLs of each
        podcast that has to be updated in the list.

        If selected is True, only update the model contents
        for the currently-selected podcast - nothing more.

        The caller can optionally specify "select_url",
        which is the URL of the podcast that is to be
        selected in the list after the update is complete.
        This only works if the podcast list has to be
        reloaded; i.e. something has been added or removed
        since the last update of the podcast list).
        """
        selection = self.treeChannels.get_selection()
        model, iter = selection.get_selected()

        is_section = lambda r: r[PodcastListModel.C_URL] == '-'
        is_separator = lambda r: r[PodcastListModel.C_SEPARATOR]
        sections_active = any(is_section(x) for x in self.podcast_list_model)

        if self.config.podcast_list_view_all:
            # Update "all episodes" view in any case (if enabled)
            self.podcast_list_model.update_first_row()
            # List model length minus 1, because of "All"
            list_model_length = len(self.podcast_list_model) - 1
        else:
            list_model_length = len(self.podcast_list_model)

        force_update = (sections_active != self.config.podcast_list_sections or
                sections_changed)

        # Filter items in the list model that are not podcasts, so we get the
        # correct podcast list count (ignore section headers and separators)
        is_not_podcast = lambda r: is_section(r) or is_separator(r)
        list_model_length -= len(filter(is_not_podcast, self.podcast_list_model))

        if selected and not force_update:
            # very cheap! only update selected channel
            if iter is not None:
                # If we have selected the "all episodes" view, we have
                # to update all channels for selected episodes:
                if self.config.podcast_list_view_all and \
                        self.podcast_list_model.iter_is_first_row(iter):
                    urls = self.get_podcast_urls_from_selected_episodes()
                    self.podcast_list_model.update_by_urls(urls)
                else:
                    # Otherwise just update the selected row (a podcast)
                    self.podcast_list_model.update_by_filter_iter(iter)

                if self.config.podcast_list_sections:
                    self.podcast_list_model.update_sections()
        elif list_model_length == len(self.channels) and not force_update:
            # we can keep the model, but have to update some
            if urls is None:
                # still cheaper than reloading the whole list
                self.podcast_list_model.update_all()
            else:
                # ok, we got a bunch of urls to update
                self.podcast_list_model.update_by_urls(urls)
                if self.config.podcast_list_sections:
                    self.podcast_list_model.update_sections()
        else:
            if model and iter and select_url is None:
                # Get the URL of the currently-selected podcast
                select_url = model.get_value(iter, PodcastListModel.C_URL)

            # Update the podcast list model with new channels
            self.podcast_list_model.set_channels(self.db, self.config, self.channels)

            try:
                selected_iter = model.get_iter_first()
                # Find the previously-selected URL in the new
                # model if we have an URL (else select first)
                if select_url is not None:
                    pos = model.get_iter_first()
                    while pos is not None:
                        url = model.get_value(pos, PodcastListModel.C_URL)
                        if url == select_url:
                            selected_iter = pos
                            break
                        pos = model.iter_next(pos)

                if selected_iter is not None:
                    selection.select_iter(selected_iter)
                self.on_treeChannels_cursor_changed(self.treeChannels)
            except:
                logger.error('Cannot select podcast in list', exc_info=True)

    def on_episode_list_filter_changed(self, has_episodes):
        pass # XXX: Remove?

    def update_episode_list_model(self):
        if self.channels and self.active_channel is not None:
            self.currently_updating = True
            self.episode_list_model.clear()

            def update():
                descriptions = self.config.episode_list_descriptions
                self.episode_list_model.replace_from_channel(self.active_channel, descriptions)

                self.treeAvailable.get_selection().unselect_all()
                self.treeAvailable.scroll_to_point(0, 0)

                self.currently_updating = False
                self.play_or_download()

            util.idle_add(update)
        else:
            self.episode_list_model.clear()

    @dbus.service.method(gpodder.dbus_interface)
    def offer_new_episodes(self, channels=None):
        new_episodes = self.get_new_episodes(channels)
        if new_episodes:
            self.new_episodes_show(new_episodes)
            return True
        return False

    def add_podcast_list(self, podcasts, auth_tokens=None):
        """Subscribe to a list of podcast given (title, url) pairs

        If auth_tokens is given, it should be a dictionary
        mapping URLs to (username, password) tuples."""

        if auth_tokens is None:
            auth_tokens = {}

        existing_urls = set(podcast.url for podcast in self.channels)

        # For a given URL, the desired title (or None)
        title_for_url = {}

        # Sort and split the URL list into five buckets
        queued, failed, existing, worked, authreq = [], [], [], [], []
        for input_title, input_url in podcasts:
            url = util.normalize_feed_url(input_url)
            if url is None:
                # Fail this one because the URL is not valid
                failed.append(input_url)
            elif url in existing_urls:
                # A podcast already exists in the list for this URL
                existing.append(url)
                # XXX: Should we try to update the title of the existing
                # subscription from input_title here if it is different?
            else:
                # This URL has survived the first round - queue for add
                title_for_url[url] = input_title
                queued.append(url)
                if url != input_url and input_url in auth_tokens:
                    auth_tokens[url] = auth_tokens[input_url]

        error_messages = {}
        redirections = {}

        progress = ProgressIndicator(_('Adding podcasts'), \
                _('Please wait while episode information is downloaded.'), \
                parent=self.get_dialog_parent())

        def on_after_update():
            progress.on_finished()
            # Report already-existing subscriptions to the user
            if existing:
                title = _('Existing subscriptions skipped')
                message = _('You are already subscribed to these podcasts:') \
                     + '\n\n' + '\n'.join(cgi.escape(url) for url in existing)
                self.show_message(message, title, widget=self.treeChannels)

            # Report subscriptions that require authentication
            retry_podcasts = {}
            if authreq:
                for url in authreq:
                    title = _('Podcast requires authentication')
                    message = _('Please login to %s:') % (cgi.escape(url),)
                    success, auth_tokens = self.show_login_dialog(title, message)
                    if success:
                        retry_podcasts[url] = auth_tokens
                    else:
                        # Stop asking the user for more login data
                        retry_podcasts = {}
                        for url in authreq:
                            error_messages[url] = _('Authentication failed')
                            failed.append(url)
                        break

            # Report website redirections
            for url in redirections:
                title = _('Website redirection detected')
                message = _('The URL %(url)s redirects to %(target)s.') \
                        + '\n\n' + _('Do you want to visit the website now?')
                message = message % {'url': url, 'target': redirections[url]}
                if self.show_confirmation(message, title):
                    util.open_website(url)
                else:
                    break

            # Report failed subscriptions to the user
            if failed:
                title = _('Could not add some podcasts')
                message = _('Some podcasts could not be added to your list:') \
                     + '\n\n' + '\n'.join(cgi.escape('%s: %s' % (url, \
                        error_messages.get(url, _('Unknown')))) for url in failed)
                self.show_message(message, title, important=True)

            # Upload subscription changes to gpodder.net
            self.mygpo_client.on_subscribe(worked)

            # Fix URLs if mygpo has rewritten them
            self.rewrite_urls_mygpo()

            # If only one podcast was added, select it after the update
            if len(worked) == 1:
                url = worked[0]
            else:
                url = None

            # Update the list of subscribed podcasts
            self.update_podcast_list_model(select_url=url)

            # If we have authentication data to retry, do so here
            if retry_podcasts:
                podcasts = [(title_for_url.get(url), url)
                        for url in retry_podcasts.keys()]
                self.add_podcast_list(podcasts, retry_podcasts)
                # This will NOT show new episodes for podcasts that have
                # been added ("worked"), but it will prevent problems with
                # multiple dialogs being open at the same time ;)
                return

            # Offer to download new episodes
            episodes = []
            for podcast in self.channels:
                if podcast.url in worked:
                    episodes.extend(podcast.get_all_episodes())

            if episodes:
                episodes = list(Model.sort_episodes_by_pubdate(episodes, \
                        reverse=True))
                self.new_episodes_show(episodes, \
                        selected=[e.check_is_new() for e in episodes])


        @util.run_in_background
        def thread_proc():
            # After the initial sorting and splitting, try all queued podcasts
            length = len(queued)
            for index, url in enumerate(queued):
                title = title_for_url.get(url)
                progress.on_progress(float(index)/float(length))
                progress.on_message(title or url)
                try:
                    # The URL is valid and does not exist already - subscribe!
                    channel = self.model.load_podcast(url=url, create=True, \
                            authentication_tokens=auth_tokens.get(url, None), \
                            max_episodes=self.config.max_episodes_per_feed)

                    try:
                        username, password = util.username_password_from_url(url)
                    except ValueError, ve:
                        username, password = (None, None)

                    if title is not None:
                        # Prefer title from subscription source (bug 1711)
                        channel.title = title

                    if username is not None and channel.auth_username is None and \
                            password is not None and channel.auth_password is None:
                        channel.auth_username = username
                        channel.auth_password = password

                    channel.save()

                    self._update_cover(channel)
                except feedcore.AuthenticationRequired:
                    if url in auth_tokens:
                        # Fail for wrong authentication data
                        error_messages[url] = _('Authentication failed')
                        failed.append(url)
                    else:
                        # Queue for login dialog later
                        authreq.append(url)
                    continue
                except feedcore.WifiLogin, error:
                    redirections[url] = error.data
                    failed.append(url)
                    error_messages[url] = _('Redirection detected')
                    continue
                except Exception, e:
                    logger.error('Subscription error: %s', e, exc_info=True)
                    error_messages[url] = str(e)
                    failed.append(url)
                    continue

                assert channel is not None
                worked.append(channel.url)

            util.idle_add(on_after_update)

    def find_episode(self, podcast_url, episode_url):
        """Find an episode given its podcast and episode URL

        The function will return a PodcastEpisode object if
        the episode is found, or None if it's not found.
        """
        for podcast in self.channels:
            if podcast_url == podcast.url:
                for episode in podcast.get_all_episodes():
                    if episode_url == episode.url:
                        return episode

        return None

    def process_received_episode_actions(self):
        """Process/merge episode actions from gpodder.net

        This function will merge all changes received from
        the server to the local database and update the
        status of the affected episodes as necessary.
        """
        indicator = ProgressIndicator(_('Merging episode actions'), \
                _('Episode actions from gpodder.net are merged.'), \
                False, self.get_dialog_parent())

        while gtk.events_pending():
            gtk.main_iteration(False)

        self.mygpo_client.process_episode_actions(self.find_episode)

        indicator.on_finished()
        self.db.commit()

    def _update_cover(self, channel):
        if channel is not None:
            self.cover_downloader.request_cover(channel)

    def show_update_feeds_buttons(self):
        # Make sure that the buttons for updating feeds
        # appear - this should happen after a feed update
        self.hboxUpdateFeeds.hide()
        self.btnUpdateFeeds.show()
        self.itemUpdate.set_sensitive(True)
        self.itemUpdateChannel.set_sensitive(True)

    def on_btnCancelFeedUpdate_clicked(self, widget):
        if not self.feed_cache_update_cancelled:
            self.pbFeedUpdate.set_text(_('Cancelling...'))
            self.feed_cache_update_cancelled = True
            self.btnCancelFeedUpdate.set_sensitive(False)
        else:
            self.show_update_feeds_buttons()

    def update_feed_cache(self, channels=None,
                          show_new_episodes_dialog=True):
        if not util.connection_available():
            self.show_message(_('Please connect to a network, then try again.'),
                    _('No network connection'), important=True)
            return

        # Fix URLs if mygpo has rewritten them
        self.rewrite_urls_mygpo()

        if channels is None:
            # Only update podcasts for which updates are enabled
            channels = [c for c in self.channels if not c.pause_subscription]

        self.itemUpdate.set_sensitive(False)
        self.itemUpdateChannel.set_sensitive(False)

        self.feed_cache_update_cancelled = False
        self.btnCancelFeedUpdate.show()
        self.btnCancelFeedUpdate.set_sensitive(True)
        self.btnCancelFeedUpdate.set_image(gtk.image_new_from_stock(gtk.STOCK_STOP, gtk.ICON_SIZE_BUTTON))
        self.hboxUpdateFeeds.show_all()
        self.btnUpdateFeeds.hide()

        count = len(channels)
        text = N_('Updating %(count)d feed...', 'Updating %(count)d feeds...', count) % {'count':count}

        self.pbFeedUpdate.set_text(text)
        self.pbFeedUpdate.set_fraction(0)

        @util.run_in_background
        def update_feed_cache_proc():
            updated_channels = []
            for updated, channel in enumerate(channels):
                if self.feed_cache_update_cancelled:
                    break

                try:
                    channel.update(max_episodes=self.config.max_episodes_per_feed)
                    self._update_cover(channel)
                except Exception, e:
                    d = {'url': cgi.escape(channel.url), 'message': cgi.escape(str(e))}
                    if d['message']:
                        message = _('Error while updating %(url)s: %(message)s')
                    else:
                        message = _('The feed at %(url)s could not be updated.')
                    self.notification(message % d, _('Error while updating feed'), widget=self.treeChannels)
                    logger.error('Error: %s', str(e), exc_info=True)

                updated_channels.append(channel)

                def update_progress(channel):
                    self.update_podcast_list_model([channel.url])

                    # If the currently-viewed podcast is updated, reload episodes
                    if self.active_channel is not None and \
                            self.active_channel == channel:
                        logger.debug('Updated channel is active, updating UI')
                        self.update_episode_list_model()

                    d = {'podcast': channel.title, 'position': updated+1, 'total': count}
                    progression = _('Updated %(podcast)s (%(position)d/%(total)d)') % d

                    self.pbFeedUpdate.set_text(progression)
                    self.pbFeedUpdate.set_fraction(float(updated+1)/float(count))

                util.idle_add(update_progress, channel)

            def update_feed_cache_finish_callback():
                # Process received episode actions for all updated URLs
                self.process_received_episode_actions()

                # If we are currently viewing "All episodes", update its episode list now
                if self.active_channel is not None and \
                        getattr(self.active_channel, 'ALL_EPISODES_PROXY', False):
                    self.update_episode_list_model()

                if self.feed_cache_update_cancelled:
                    # The user decided to abort the feed update
                    self.show_update_feeds_buttons()

                # Only search for new episodes in podcasts that have been
                # updated, not in other podcasts (for single-feed updates)
                episodes = self.get_new_episodes([c for c in updated_channels])

                if self.config.downloads.chronological_order:
                    # download older episodes first
                    episodes = list(Model.sort_episodes_by_pubdate(episodes))

                if not episodes:
                    # Nothing new here - but inform the user
                    self.pbFeedUpdate.set_fraction(1.0)
                    self.pbFeedUpdate.set_text(_('No new episodes'))
                    self.feed_cache_update_cancelled = True
                    self.btnCancelFeedUpdate.show()
                    self.btnCancelFeedUpdate.set_sensitive(True)
                    self.itemUpdate.set_sensitive(True)
                    self.btnCancelFeedUpdate.set_image(gtk.image_new_from_stock(gtk.STOCK_APPLY, gtk.ICON_SIZE_BUTTON))
                else:
                    count = len(episodes)
                    # New episodes are available
                    self.pbFeedUpdate.set_fraction(1.0)

                    if self.config.auto_download == 'download':
                        self.download_episode_list(episodes)
                        title = N_('Downloading %(count)d new episode.', 'Downloading %(count)d new episodes.', count) % {'count':count}
                        self.show_message(title, _('New episodes available'), widget=self.labelDownloads)
                    elif self.config.auto_download == 'queue':
                        self.download_episode_list_paused(episodes)
                        title = N_('%(count)d new episode added to download list.', '%(count)d new episodes added to download list.', count) % {'count':count}
                        self.show_message(title, _('New episodes available'), widget=self.labelDownloads)
                    else:
                        if (show_new_episodes_dialog and
                                self.config.auto_download == 'show'):
                            self.new_episodes_show(episodes, notification=True)
                        else: # !show_new_episodes_dialog or auto_download == 'ignore'
                            message = N_('%(count)d new episode available', '%(count)d new episodes available', count) % {'count':count}
                            self.pbFeedUpdate.set_text(message)

                    self.show_update_feeds_buttons()

            util.idle_add(update_feed_cache_finish_callback)

    def on_gPodder_delete_event(self, widget, *args):
        """Called when the GUI wants to close the window
        Displays a confirmation dialog (and closes/hides gPodder)
        """

        downloading = self.download_status_model.are_downloads_in_progress()

        if downloading:
            dialog = gtk.MessageDialog(self.gPodder, gtk.DIALOG_MODAL, gtk.MESSAGE_QUESTION, gtk.BUTTONS_NONE)
            dialog.add_button(gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL)
            quit_button = dialog.add_button(gtk.STOCK_QUIT, gtk.RESPONSE_CLOSE)

            title = _('Quit gPodder')
            message = _('You are downloading episodes. You can resume downloads the next time you start gPodder. Do you want to quit now?')

            dialog.set_title(title)
            dialog.set_markup('<span weight="bold" size="larger">%s</span>\n\n%s'%(title, message))

            quit_button.grab_focus()
            result = dialog.run()
            dialog.destroy()

            if result == gtk.RESPONSE_CLOSE:
                self.close_gpodder()
        else:
            self.close_gpodder()

        return True

    def quit_cb(self, macapp):
        """Called when OSX wants to quit the app (Cmd-Q or gPodder > Quit)
        """
        # Event can't really be cancelled - don't even try
        self.close_gpodder()
        return False

    def close_gpodder(self):
        """ clean everything and exit properly
        """
        self.gPodder.hide()

        # Notify all tasks to to carry out any clean-up actions
        self.download_status_model.tell_all_tasks_to_quit()

        while gtk.events_pending():
            gtk.main_iteration(False)

        self.core.shutdown()

        self.quit()
        if macapp is None:
            sys.exit(0)

    def delete_episode_list(self, episodes, confirm=True, skip_locked=True,
            callback=None):
        if not episodes:
            return False

        if skip_locked:
            episodes = [e for e in episodes if not e.archive]

            if not episodes:
                title = _('Episodes are locked')
                message = _('The selected episodes are locked. Please unlock the episodes that you want to delete before trying to delete them.')
                self.notification(message, title, widget=self.treeAvailable)
                return False

        count = len(episodes)
        title = N_('Delete %(count)d episode?', 'Delete %(count)d episodes?', count) % {'count':count}
        message = _('Deleting episodes removes downloaded files.')

        if confirm and not self.show_confirmation(message, title):
            return False

        progress = ProgressIndicator(_('Deleting episodes'), \
                _('Please wait while episodes are deleted'), \
                parent=self.get_dialog_parent())

        def finish_deletion(episode_urls, channel_urls):
            progress.on_finished()

            # Episodes have been deleted - persist the database
            self.db.commit()

            self.update_episode_list_icons(episode_urls)
            self.update_podcast_list_model(channel_urls)
            self.play_or_download()

        @util.run_in_background
        def thread_proc():
            episode_urls = set()
            channel_urls = set()

            episodes_status_update = []
            for idx, episode in enumerate(episodes):
                progress.on_progress(float(idx)/float(len(episodes)))
                if not episode.archive or not skip_locked:
                    progress.on_message(episode.title)
                    episode.delete_from_disk()
                    episode_urls.add(episode.url)
                    channel_urls.add(episode.channel.url)
                    episodes_status_update.append(episode)

            # Notify the web service about the status update + upload
            if self.mygpo_client.can_access_webservice():
                self.mygpo_client.on_delete(episodes_status_update)
                self.mygpo_client.flush()

            if callback is None:
                util.idle_add(finish_deletion, episode_urls, channel_urls)
            else:
                util.idle_add(callback, episode_urls, channel_urls, progress)

        return True

    def on_itemRemoveOldEpisodes_activate(self, widget):
        self.show_delete_episodes_window()

    def show_delete_episodes_window(self, channel=None):
        """Offer deletion of episodes

        If channel is None, offer deletion of all episodes.
        Otherwise only offer deletion of episodes in the channel.
        """
        columns = (
            ('markup_delete_episodes', None, None, _('Episode')),
        )

        msg_older_than = N_('Select older than %(count)d day', 'Select older than %(count)d days', self.config.episode_old_age)
        selection_buttons = {
                _('Select played'): lambda episode: not episode.is_new,
                _('Select finished'): lambda episode: episode.is_finished(),
                msg_older_than % {'count':self.config.episode_old_age}: lambda episode: episode.age_in_days() > self.config.episode_old_age,
        }

        instructions = _('Select the episodes you want to delete:')

        if channel is None:
            channels = self.channels
        else:
            channels = [channel]

        episodes = []
        for channel in channels:
            for episode in channel.get_episodes(gpodder.STATE_DOWNLOADED):
                # Disallow deletion of locked episodes that still exist
                if not episode.archive or not episode.file_exists():
                    episodes.append(episode)

        selected = [not e.is_new or not e.file_exists() for e in episodes]

        gPodderEpisodeSelector(self.gPodder, title = _('Delete episodes'), instructions = instructions, \
                                episodes = episodes, selected = selected, columns = columns, \
                                stock_ok_button = gtk.STOCK_DELETE, callback = self.delete_episode_list, \
                                selection_buttons = selection_buttons, _config=self.config)

    def on_selected_episodes_status_changed(self):
        # The order of the updates here is important! When "All episodes" is
        # selected, the update of the podcast list model depends on the episode
        # list selection to determine which podcasts are affected. Updating
        # the episode list could remove the selection if a filter is active.
        self.update_podcast_list_model(selected=True)
        self.update_episode_list_icons(selected=True)
        self.db.commit()

    def mark_selected_episodes_new(self):
        for episode in self.get_selected_episodes():
            episode.mark_new()
        self.on_selected_episodes_status_changed()

    def mark_selected_episodes_old(self):
        for episode in self.get_selected_episodes():
            episode.mark_old()
        self.on_selected_episodes_status_changed()

    def flattr_selected_episodes(self, w=None):
        if not self.config.flattr.token:
            return

        for episode in [e for e in self.get_selected_episodes() if e.payment_url]:
            success, message = self.flattr.flattr_url(episode.payment_url)
            self.show_message(message, title=_('Flattr status'),
                important=not success)

    def on_item_toggle_played_activate( self, widget, toggle = True, new_value = False):
        for episode in self.get_selected_episodes():
            if toggle:
                episode.mark(is_played=episode.is_new)
            else:
                episode.mark(is_played=new_value)
        self.on_selected_episodes_status_changed()

    def on_item_toggle_lock_activate(self, widget, toggle=True, new_value=False):
        for episode in self.get_selected_episodes():
            if toggle:
                episode.mark(is_locked=not episode.archive)
            else:
                episode.mark(is_locked=new_value)
        self.on_selected_episodes_status_changed()

    def on_channel_toggle_lock_activate(self, widget, toggle=True, new_value=False):
        if self.active_channel is None:
            return

        self.active_channel.auto_archive_episodes = not self.active_channel.auto_archive_episodes
        self.active_channel.save()

        for episode in self.active_channel.get_all_episodes():
            episode.mark(is_locked=self.active_channel.auto_archive_episodes)

        self.update_podcast_list_model(selected=True)
        self.update_episode_list_icons(all=True)

    def on_itemUpdateChannel_activate(self, widget=None):
        if self.active_channel is None:
            title = _('No podcast selected')
            message = _('Please select a podcast in the podcasts list to update.')
            self.show_message( message, title, widget=self.treeChannels)
            return

        # Dirty hack to check for "All episodes" (see gpodder.gtkui.model)
        if getattr(self.active_channel, 'ALL_EPISODES_PROXY', False):
            self.update_feed_cache()
        else:
            self.update_feed_cache(channels=[self.active_channel])

    def on_itemUpdate_activate(self, widget=None):
        # Check if we have outstanding subscribe/unsubscribe actions
        self.on_add_remove_podcasts_mygpo()

        if self.channels:
            self.update_feed_cache()
        else:
            def show_welcome_window():
                def on_show_example_podcasts(widget):
                    welcome_window.main_window.response(gtk.RESPONSE_CANCEL)
                    self.on_itemImportChannels_activate(None)

                def on_add_podcast_via_url(widget):
                    welcome_window.main_window.response(gtk.RESPONSE_CANCEL)
                    self.on_itemAddChannel_activate(None)

                def on_setup_my_gpodder(widget):
                    welcome_window.main_window.response(gtk.RESPONSE_CANCEL)
                    self.on_download_subscriptions_from_mygpo(None)

                welcome_window = gPodderWelcome(self.main_window,
                        center_on_widget=self.main_window,
                        on_show_example_podcasts=on_show_example_podcasts,
                        on_add_podcast_via_url=on_add_podcast_via_url,
                        on_setup_my_gpodder=on_setup_my_gpodder)

                welcome_window.main_window.run()
                welcome_window.main_window.destroy()

            util.idle_add(show_welcome_window)

    def download_episode_list_paused(self, episodes):
        self.download_episode_list(episodes, True)

    def download_episode_list(self, episodes, add_paused=False, force_start=False):
        enable_update = False

        if self.config.downloads.chronological_order:
            # Download episodes in chronological order (older episodes first)
            episodes = list(Model.sort_episodes_by_pubdate(episodes))

        for episode in episodes:
            logger.debug('Downloading episode: %s', episode.title)
            if not episode.was_downloaded(and_exists=True):
                task_exists = False
                for task in self.download_tasks_seen:
                    if episode.url == task.url:
                        task_exists = True
                        if task.status not in (task.DOWNLOADING, task.QUEUED):
                            self.download_queue_manager.add_task(task, force_start)
                            enable_update = True
                            continue

                if task_exists:
                    continue

                try:
                    task = download.DownloadTask(episode, self.config)
                except Exception, e:
                    d = {'episode': episode.title, 'message': str(e)}
                    message = _('Download error while downloading %(episode)s: %(message)s')
                    self.show_message(message % d, _('Download error'), important=True)
                    logger.error('While downloading %s', episode.title, exc_info=True)
                    continue

                if add_paused:
                    task.status = task.PAUSED
                else:
                    self.mygpo_client.on_download([task.episode])
                    self.download_queue_manager.add_task(task, force_start)

                self.download_status_model.register_task(task)
                enable_update = True

        if enable_update:
            self.enable_download_list_update()

        # Flush updated episode status
        if self.mygpo_client.can_access_webservice():
            self.mygpo_client.flush()

    def cancel_task_list(self, tasks):
        if not tasks:
            return

        for task in tasks:
            if task.status in (task.QUEUED, task.DOWNLOADING):
                task.status = task.CANCELLED
            elif task.status == task.PAUSED:
                task.status = task.CANCELLED
                # Call run, so the partial file gets deleted
                task.run()

        self.update_episode_list_icons([task.url for task in tasks])
        self.play_or_download()

        # Update the tab title and downloads list
        self.update_downloads_list()

    def new_episodes_show(self, episodes, notification=False, selected=None):
        columns = (
            ('markup_new_episodes', None, None, _('Episode')),
        )

        instructions = _('Select the episodes you want to download:')

        if self.new_episodes_window is not None:
            self.new_episodes_window.main_window.destroy()
            self.new_episodes_window = None

        def download_episodes_callback(episodes):
            self.new_episodes_window = None
            self.download_episode_list(episodes)

        if selected is None:
            # Select all by default
            selected = [True]*len(episodes)

        self.new_episodes_window = gPodderEpisodeSelector(self.gPodder, \
                title=_('New episodes available'), \
                instructions=instructions, \
                episodes=episodes, \
                columns=columns, \
                selected=selected, \
                stock_ok_button = 'gpodder-download', \
                callback=download_episodes_callback, \
                remove_callback=lambda e: e.mark_old(), \
                remove_action=_('Mark as old'), \
                remove_finished=self.episode_new_status_changed, \
                _config=self.config, \
                show_notification=False)

    def on_itemDownloadAllNew_activate(self, widget, *args):
        if not self.offer_new_episodes():
            self.show_message(_('Please check for new episodes later.'), \
                    _('No new episodes available'), widget=self.btnUpdateFeeds)

    def get_new_episodes(self, channels=None):
        return [e for c in channels or self.channels for e in
                filter(lambda e: e.check_is_new(), c.get_all_episodes())]

    def commit_changes_to_database(self):
        """This will be called after the sync process is finished"""
        self.db.commit()

    def on_itemShowToolbar_activate(self, widget):
        self.config.show_toolbar = self.itemShowToolbar.get_active()

    def on_itemShowDescription_activate(self, widget):
        self.config.episode_list_descriptions = self.itemShowDescription.get_active()

    def on_item_view_hide_boring_podcasts_toggled(self, toggleaction):
        self.config.podcast_list_hide_boring = toggleaction.get_active()
        if self.config.podcast_list_hide_boring:
            self.podcast_list_model.set_view_mode(self.config.episode_list_view_mode)
        else:
            self.podcast_list_model.set_view_mode(-1)

    def on_item_view_episodes_changed(self, radioaction, current):
        if current == self.item_view_episodes_all:
            self.config.episode_list_view_mode = EpisodeListModel.VIEW_ALL
        elif current == self.item_view_episodes_undeleted:
            self.config.episode_list_view_mode = EpisodeListModel.VIEW_UNDELETED
        elif current == self.item_view_episodes_downloaded:
            self.config.episode_list_view_mode = EpisodeListModel.VIEW_DOWNLOADED
        elif current == self.item_view_episodes_unplayed:
            self.config.episode_list_view_mode = EpisodeListModel.VIEW_UNPLAYED

        self.episode_list_model.set_view_mode(self.config.episode_list_view_mode)

        if self.config.podcast_list_hide_boring:
            self.podcast_list_model.set_view_mode(self.config.episode_list_view_mode)

    def on_itemPreferences_activate(self, widget, *args):
        gPodderPreferences(self.main_window, \
                _config=self.config, \
                flattr=self.flattr, \
                user_apps_reader=self.user_apps_reader, \
                parent_window=self.main_window, \
                mygpo_client=self.mygpo_client, \
                on_send_full_subscriptions=self.on_send_full_subscriptions, \
                on_itemExportChannels_activate=self.on_itemExportChannels_activate)

    def on_goto_mygpo(self, widget):
        self.mygpo_client.open_website()

    def on_download_subscriptions_from_mygpo(self, action=None):
        title = _('Login to gpodder.net')
        message = _('Please login to download your subscriptions.')

        def on_register_button_clicked():
            util.open_website('http://gpodder.net/register/')

        success, (username, password) = self.show_login_dialog(title, message,
                self.config.mygpo.username, self.config.mygpo.password,
                register_callback=on_register_button_clicked)
        if not success:
            return

        self.config.mygpo.username = username
        self.config.mygpo.password = password

        dir = gPodderPodcastDirectory(self.gPodder, _config=self.config, \
                custom_title=_('Subscriptions on gpodder.net'), \
                add_podcast_list=self.add_podcast_list,
                hide_url_entry=True)

        # TODO: Refactor this into "gpodder.my" or mygpoclient, so that
        #       we do not have to hardcode the URL here
        OPML_URL = 'http://gpodder.net/subscriptions/%s.opml' % self.config.mygpo.username
        url = util.url_add_authentication(OPML_URL, \
                self.config.mygpo.username, \
                self.config.mygpo.password)
        dir.download_opml_file(url)

    def on_itemAddChannel_activate(self, widget=None):
        gPodderAddPodcast(self.gPodder, \
                add_podcast_list=self.add_podcast_list)

    def on_itemEditChannel_activate(self, widget, *args):
        if self.active_channel is None:
            title = _('No podcast selected')
            message = _('Please select a podcast in the podcasts list to edit.')
            self.show_message( message, title, widget=self.treeChannels)
            return

        gPodderChannel(self.main_window,
                channel=self.active_channel,
                update_podcast_list_model=self.update_podcast_list_model,
                cover_downloader=self.cover_downloader,
                sections=set(c.section for c in self.channels),
                clear_cover_cache=self.podcast_list_model.clear_cover_cache,
                _config=self.config,
                _flattr=self.flattr)

    def on_itemMassUnsubscribe_activate(self, item=None):
        columns = (
            ('title', None, None, _('Podcast')),
        )

        # We're abusing the Episode Selector for selecting Podcasts here,
        # but it works and looks good, so why not? -- thp
        gPodderEpisodeSelector(self.main_window, \
                title=_('Remove podcasts'), \
                instructions=_('Select the podcast you want to remove.'), \
                episodes=self.channels, \
                columns=columns, \
                size_attribute=None, \
                stock_ok_button=_('Remove'), \
                callback=self.remove_podcast_list, \
                _config=self.config)

    def remove_podcast_list(self, channels, confirm=True):
        if not channels:
            return

        if len(channels) == 1:
            title = _('Removing podcast')
            info = _('Please wait while the podcast is removed')
            message = _('Do you really want to remove this podcast and its episodes?')
        else:
            title = _('Removing podcasts')
            info = _('Please wait while the podcasts are removed')
            message = _('Do you really want to remove the selected podcasts and their episodes?')

        if confirm and not self.show_confirmation(message, title):
            return

        progress = ProgressIndicator(title, info, parent=self.get_dialog_parent())

        def finish_deletion(select_url):
            # Upload subscription list changes to the web service
            self.mygpo_client.on_unsubscribe([c.url for c in channels])

            # Re-load the channels and select the desired new channel
            self.update_podcast_list_model(select_url=select_url)
            progress.on_finished()

        @util.run_in_background
        def thread_proc():
            select_url = None

            for idx, channel in enumerate(channels):
                # Update the UI for correct status messages
                progress.on_progress(float(idx)/float(len(channels)))
                progress.on_message(channel.title)

                # Delete downloaded episodes
                channel.remove_downloaded()

                # cancel any active downloads from this channel
                for episode in channel.get_all_episodes():
                    if episode.downloading:
                        episode.download_task.cancel()

                if len(channels) == 1:
                    # get the URL of the podcast we want to select next
                    if channel in self.channels:
                        position = self.channels.index(channel)
                    else:
                        position = -1

                    if position == len(self.channels)-1:
                        # this is the last podcast, so select the URL
                        # of the item before this one (i.e. the "new last")
                        select_url = self.channels[position-1].url
                    else:
                        # there is a podcast after the deleted one, so
                        # we simply select the one that comes after it
                        select_url = self.channels[position+1].url

                # Remove the channel and clean the database entries
                channel.delete()

            # Clean up downloads and download directories
            common.clean_up_downloads()

            # The remaining stuff is to be done in the GTK main thread
            util.idle_add(finish_deletion, select_url)

    def on_itemRemoveChannel_activate(self, widget, *args):
        if self.active_channel is None:
            title = _('No podcast selected')
            message = _('Please select a podcast in the podcasts list to remove.')
            self.show_message( message, title, widget=self.treeChannels)
            return

        self.remove_podcast_list([self.active_channel])

    def get_opml_filter(self):
        filter = gtk.FileFilter()
        filter.add_pattern('*.opml')
        filter.add_pattern('*.xml')
        filter.set_name(_('OPML files')+' (*.opml, *.xml)')
        return filter

    def on_item_import_from_file_activate(self, widget, filename=None):
        if filename is None:
            dlg = gtk.FileChooserDialog(title=_('Import from OPML'),
                    parent=self.main_window,
                    action=gtk.FILE_CHOOSER_ACTION_OPEN)
            dlg.add_button(gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL)
            dlg.add_button(gtk.STOCK_OPEN, gtk.RESPONSE_OK)
            dlg.set_filter(self.get_opml_filter())
            response = dlg.run()
            filename = None
            if response == gtk.RESPONSE_OK:
                filename = dlg.get_filename()
            dlg.destroy()

        if filename is not None:
            dir = gPodderPodcastDirectory(self.gPodder, _config=self.config, \
                    custom_title=_('Import podcasts from OPML file'), \
                    add_podcast_list=self.add_podcast_list,
                    hide_url_entry=True)
            dir.download_opml_file(filename)

    def on_itemExportChannels_activate(self, widget, *args):
        if not self.channels:
            title = _('Nothing to export')
            message = _('Your list of podcast subscriptions is empty. Please subscribe to some podcasts first before trying to export your subscription list.')
            self.show_message(message, title, widget=self.treeChannels)
            return

        dlg = gtk.FileChooserDialog(title=_('Export to OPML'), parent=self.gPodder, action=gtk.FILE_CHOOSER_ACTION_SAVE)
        dlg.add_button(gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL)
        dlg.add_button(gtk.STOCK_SAVE, gtk.RESPONSE_OK)
        dlg.set_filter(self.get_opml_filter())
        response = dlg.run()
        if response == gtk.RESPONSE_OK:
            filename = dlg.get_filename()
            dlg.destroy()
            exporter = opml.Exporter( filename)
            if filename is not None and exporter.write(self.channels):
                count = len(self.channels)
                title = N_('%(count)d subscription exported', '%(count)d subscriptions exported', count) % {'count':count}
                self.show_message(_('Your podcast list has been successfully exported.'), title, widget=self.treeChannels)
            else:
                self.show_message( _('Could not export OPML to file. Please check your permissions.'), _('OPML export failed'), important=True)
        else:
            dlg.destroy()

    def on_itemImportChannels_activate(self, widget, *args):
        dir = gPodderPodcastDirectory(self.main_window, _config=self.config, \
                add_podcast_list=self.add_podcast_list)
        util.idle_add(dir.download_opml_file, my.EXAMPLES_OPML)

    def on_homepage_activate(self, widget, *args):
        util.open_website(gpodder.__url__)

    def on_wiki_activate(self, widget, *args):
        util.open_website('http://gpodder.org/wiki/User_Manual')

    def on_check_for_updates_activate(self, widget):
        self.check_for_updates(silent=False)

    def check_for_updates(self, silent):
        """Check for updates and (optionally) show a message

        If silent=False, a message will be shown even if no updates are
        available (set silent=False when the check is manually triggered).
        """
        up_to_date, version, released, days = util.get_update_info()

        if up_to_date and not silent:
            title = _('No updates available')
            message = _('You have the latest version of gPodder.')
            self.show_message(message, title, important=True)

        if not up_to_date:
            title = _('New version available')
            message = '\n'.join([
                _('Installed version: %s') % gpodder.__version__,
                _('Newest version: %s') % version,
                _('Release date: %s') % released,
                '',
                _('Download the latest version from gpodder.org?'),
            ])

            if self.show_confirmation(message, title):
                util.open_website('http://gpodder.org/downloads')

    def on_bug_tracker_activate(self, widget, *args):
        util.open_website('https://bugs.gpodder.org/enter_bug.cgi?product=gPodder&component=Application&version=%s' % gpodder.__version__)

    def on_item_support_activate(self, widget):
        util.open_website('http://gpodder.org/donate')

    def on_itemAbout_activate(self, widget, *args):
        dlg = gtk.Dialog(_('About gPodder'), self.main_window, \
                gtk.DIALOG_MODAL)
        dlg.add_button(gtk.STOCK_CLOSE, gtk.RESPONSE_OK).show()
        dlg.set_resizable(False)

        bg = gtk.HBox(spacing=10)
        bg.pack_start(gtk.image_new_from_file(gpodder.icon_file), expand=False)
        vb = gtk.VBox()
        vb.set_spacing(6)
        label = gtk.Label()
        label.set_alignment(0, 1)
        label.set_markup('<b><big>gPodder</big> %s</b>' % gpodder.__version__)
        vb.pack_start(label)
        label = gtk.Label()
        label.set_alignment(0, 0)
        label.set_markup('<small><a href="%s">%s</a></small>' % \
                ((cgi.escape(gpodder.__url__),)*2))
        vb.pack_start(label)
        bg.pack_start(vb)

        out = gtk.VBox(spacing=10)
        out.set_border_width(12)
        out.pack_start(bg, expand=False)
        out.pack_start(gtk.HSeparator())
        out.pack_start(gtk.Label(gpodder.__copyright__))

        button_box = gtk.HButtonBox()
        button = gtk.Button(_('Donate / Wishlist'))
        button.connect('clicked', self.on_item_support_activate)
        button_box.pack_start(button)
        button = gtk.Button(_('Report a problem'))
        button.connect('clicked', self.on_bug_tracker_activate)
        button_box.pack_start(button)
        out.pack_start(button_box, expand=False)

        credits = gtk.TextView()
        credits.set_left_margin(5)
        credits.set_right_margin(5)
        credits.set_pixels_above_lines(5)
        credits.set_pixels_below_lines(5)
        credits.set_editable(False)
        credits.set_cursor_visible(False)
        sw = gtk.ScrolledWindow()
        sw.set_shadow_type(gtk.SHADOW_IN)
        sw.set_policy(gtk.POLICY_NEVER, gtk.POLICY_AUTOMATIC)
        sw.add(credits)
        credits.set_size_request(-1, 160)
        out.pack_start(sw, expand=True, fill=True)

        dlg.vbox.pack_start(out, expand=False)
        dlg.connect('response', lambda dlg, response: dlg.destroy())

        dlg.vbox.show_all()

        if os.path.exists(gpodder.credits_file):
            credits_txt = open(gpodder.credits_file).read().strip().split('\n')
            translator_credits = _('translator-credits')
            if translator_credits != 'translator-credits':
                app_authors = [_('Translation by:'), translator_credits, '']
            else:
                app_authors = []

            app_authors += [_('Thanks to:')]
            app_authors += credits_txt

            buffer = gtk.TextBuffer()
            buffer.set_text('\n'.join(app_authors))
            credits.set_buffer(buffer)
        else:
            sw.hide()

        credits.grab_focus()
        dlg.run()

    def on_wNotebook_switch_page(self, notebook, page, page_num):
        if page_num == 0:
            self.play_or_download()
            # The message area in the downloads tab should be hidden
            # when the user switches away from the downloads tab
            if self.message_area is not None:
                self.message_area.hide()
                self.message_area = None
        else:
            self.toolDownload.set_sensitive(False)
            self.toolPlay.set_sensitive(False)
            self.toolCancel.set_sensitive(False)

    def on_treeChannels_row_activated(self, widget, path, *args):
        # double-click action of the podcast list or enter
        self.treeChannels.set_cursor(path)

    def on_treeChannels_cursor_changed(self, widget, *args):
        ( model, iter ) = self.treeChannels.get_selection().get_selected()

        if model is not None and iter is not None:
            old_active_channel = self.active_channel
            self.active_channel = model.get_value(iter, PodcastListModel.C_CHANNEL)

            if self.active_channel == old_active_channel:
                return

            # Dirty hack to check for "All episodes" (see gpodder.gtkui.model)
            if getattr(self.active_channel, 'ALL_EPISODES_PROXY', False):
                self.itemEditChannel.set_visible(False)
                self.itemRemoveChannel.set_visible(False)
            else:
                self.itemEditChannel.set_visible(True)
                self.itemRemoveChannel.set_visible(True)
        else:
            self.active_channel = None
            self.itemEditChannel.set_visible(False)
            self.itemRemoveChannel.set_visible(False)

        self.update_episode_list_model()

    def on_btnEditChannel_clicked(self, widget, *args):
        self.on_itemEditChannel_activate( widget, args)

    def get_podcast_urls_from_selected_episodes(self):
        """Get a set of podcast URLs based on the selected episodes"""
        return set(episode.channel.url for episode in \
                self.get_selected_episodes())

    def get_selected_episodes(self):
        """Get a list of selected episodes from treeAvailable"""
        selection = self.treeAvailable.get_selection()
        model, paths = selection.get_selected_rows()

        episodes = [model.get_value(model.get_iter(path), EpisodeListModel.C_EPISODE) for path in paths]
        return episodes

    def on_playback_selected_episodes(self, widget):
        self.playback_episodes(self.get_selected_episodes())

    def on_shownotes_selected_episodes(self, widget):
        episodes = self.get_selected_episodes()
        self.shownotes_object.toggle_pane_visibility(episodes)

    def on_download_selected_episodes(self, widget):
        episodes = self.get_selected_episodes()
        self.download_episode_list(episodes)
        self.update_episode_list_icons([episode.url for episode in episodes])
        self.play_or_download()

    def on_treeAvailable_row_activated(self, widget, path, view_column):
        """Double-click/enter action handler for treeAvailable"""
        self.on_shownotes_selected_episodes(widget)

    def restart_auto_update_timer(self):
        if self._auto_update_timer_source_id is not None:
            logger.debug('Removing existing auto update timer.')
            gobject.source_remove(self._auto_update_timer_source_id)
            self._auto_update_timer_source_id = None

        if self.config.auto_update_feeds and \
                self.config.auto_update_frequency:
            interval = 60*1000*self.config.auto_update_frequency
            logger.debug('Setting up auto update timer with interval %d.',
                    self.config.auto_update_frequency)
            self._auto_update_timer_source_id = gobject.timeout_add(\
                    interval, self._on_auto_update_timer)

    def _on_auto_update_timer(self):
        if not util.connection_available():
            logger.debug('Skipping auto update (no connection available)')
            return True

        logger.debug('Auto update timer fired.')
        self.update_feed_cache()

        # Ask web service for sub changes (if enabled)
        if self.mygpo_client.can_access_webservice():
            self.mygpo_client.flush()

        return True

    def on_treeDownloads_row_activated(self, widget, *args):
        # Use the standard way of working on the treeview
        selection = self.treeDownloads.get_selection()
        (model, paths) = selection.get_selected_rows()
        selected_tasks = [(gtk.TreeRowReference(model, path), model.get_value(model.get_iter(path), 0)) for path in paths]

        for tree_row_reference, task in selected_tasks:
            if task.status in (task.DOWNLOADING, task.QUEUED):
                task.status = task.PAUSED
            elif task.status in (task.CANCELLED, task.PAUSED, task.FAILED):
                self.download_queue_manager.add_task(task)
                self.enable_download_list_update()
            elif task.status == task.DONE:
                model.remove(model.get_iter(tree_row_reference.get_path()))

        self.play_or_download()

        # Update the tab title and downloads list
        self.update_downloads_list()

    def on_item_cancel_download_activate(self, widget):
        if self.wNotebook.get_current_page() == 0:
            selection = self.treeAvailable.get_selection()
            (model, paths) = selection.get_selected_rows()
            urls = [model.get_value(model.get_iter(path), \
                    self.episode_list_model.C_URL) for path in paths]
            selected_tasks = [task for task in self.download_tasks_seen \
                    if task.url in urls]
        else:
            selection = self.treeDownloads.get_selection()
            (model, paths) = selection.get_selected_rows()
            selected_tasks = [model.get_value(model.get_iter(path), \
                    self.download_status_model.C_TASK) for path in paths]
        self.cancel_task_list(selected_tasks)

    def on_btnCancelAll_clicked(self, widget, *args):
        self.cancel_task_list(self.download_tasks_seen)

    def on_btnDownloadedDelete_clicked(self, widget, *args):
        episodes = self.get_selected_episodes()
        if len(episodes) == 1:
            self.delete_episode_list(episodes, skip_locked=False)
        else:
            self.delete_episode_list(episodes)

    def on_key_press(self, widget, event):
        # Allow tab switching with Ctrl + PgUp/PgDown/Tab
        if event.state & gtk.gdk.CONTROL_MASK:
            if event.keyval == gtk.keysyms.Page_Up:
                self.wNotebook.prev_page()
                return True
            elif event.keyval == gtk.keysyms.Page_Down:
                self.wNotebook.next_page()
                return True
            elif event.keyval == gtk.keysyms.Tab:
                current_page = self.wNotebook.get_current_page()

                if current_page == self.wNotebook.get_n_pages()-1:
                    self.wNotebook.set_current_page(0)
                else:
                    self.wNotebook.next_page()
                return True

        return False

    def uniconify_main_window(self):
        if self.is_iconified():
            # We need to hide and then show the window in WMs like Metacity
            # or KWin4 to move the window to the active workspace
            # (see http://gpodder.org/bug/1125)
            self.gPodder.hide()
            self.gPodder.show()
            self.gPodder.present()

    def iconify_main_window(self):
        if not self.is_iconified():
            self.gPodder.iconify()

    @dbus.service.method(gpodder.dbus_interface)
    def show_gui_window(self):
        parent = self.get_dialog_parent()
        parent.present()

    @dbus.service.method(gpodder.dbus_interface)
    def subscribe_to_url(self, url):
        gPodderAddPodcast(self.gPodder,
                add_podcast_list=self.add_podcast_list,
                preset_url=url)

    @dbus.service.method(gpodder.dbus_interface)
    def mark_episode_played(self, filename):
        if filename is None:
            return False

        for channel in self.channels:
            for episode in channel.get_all_episodes():
                fn = episode.local_filename(create=False, check_only=True)
                if fn == filename:
                    episode.mark(is_played=True)
                    self.db.commit()
                    self.update_episode_list_icons([episode.url])
                    self.update_podcast_list_model([episode.channel.url])
                    return True

        return False

    def extensions_podcast_update_cb(self, podcast):
        logger.debug('extensions_podcast_update_cb(%s)', podcast)
        self.update_feed_cache(channels=[podcast],
                show_new_episodes_dialog=False)

    def extensions_episode_download_cb(self, episode):
        logger.debug('extension_episode_download_cb(%s)', episode)
        self.download_episode_list(episodes=[episode])

    def on_sync_to_device_activate(self, widget, episodes=None, force_played=True):
        self.sync_ui = gPodderSyncUI(self.config, self.notification,
                self.main_window,
                self.show_confirmation,
                self.update_episode_list_icons,
                self.update_podcast_list_model,
                self.toolPreferences,
                self.channels,
                self.download_status_model,
                self.download_queue_manager,
                self.enable_download_list_update,
                self.commit_changes_to_database,
                self.delete_episode_list)

        self.sync_ui.on_synchronize_episodes(self.channels, episodes, force_played)

def main(options=None):
    gobject.threads_init()
    gobject.set_application_name('gPodder')

    for i in range(EpisodeListModel.PROGRESS_STEPS + 1):
        pixbuf = draw_cake_pixbuf(float(i) /
                float(EpisodeListModel.PROGRESS_STEPS))
        icon_name = 'gpodder-progress-%d' % i
        gtk.icon_theme_add_builtin_icon(icon_name, pixbuf.get_width(), pixbuf)

    gtk.window_set_default_icon_name('gpodder')
    gtk.about_dialog_set_url_hook(lambda dlg, link, data: util.open_website(link), None)

    try:
        dbus_main_loop = dbus.glib.DBusGMainLoop(set_as_default=True)
        gpodder.dbus_session_bus = dbus.SessionBus(dbus_main_loop)

        bus_name = dbus.service.BusName(gpodder.dbus_bus_name, bus=gpodder.dbus_session_bus)
    except dbus.exceptions.DBusException, dbe:
        logger.warn('Cannot get "on the bus".', exc_info=True)
        dlg = gtk.MessageDialog(None, gtk.DIALOG_MODAL, gtk.MESSAGE_ERROR, \
                gtk.BUTTONS_CLOSE, _('Cannot start gPodder'))
        dlg.format_secondary_markup(_('D-Bus error: %s') % (str(dbe),))
        dlg.set_title('gPodder')
        dlg.run()
        dlg.destroy()
        sys.exit(0)

    gp = gPodder(bus_name, core.Core(UIConfig, model_class=Model))

    # Handle options
    if options.subscribe:
        util.idle_add(gp.subscribe_to_url, options.subscribe)

    if gpodder.ui.osx:
        from gpodder.gtkui import macosx

        # Handle "subscribe to podcast" events from firefox
        macosx.register_handlers(gp)

        # Handle quit event
        if macapp is not None:
            macapp.connect('NSApplicationBlockTermination', gp.quit_cb)
            macapp.ready()

    gp.run()


########NEW FILE########
__FILENAME__ = model
# -*- coding: utf-8 -*-
#
# gPodder - A media aggregator and podcast client
# Copyright (c) 2005-2014 Thomas Perl and the gPodder Team
#
# gPodder is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# gPodder is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#


#
#  gpodder.gtkui.model - GUI model classes for gPodder (2009-08-13)
#  Based on code from libpodcasts.py (thp, 2005-10-29)
#

import gpodder

_ = gpodder.gettext

from gpodder import util
from gpodder import model
from gpodder import query
from gpodder import coverart

import logging
logger = logging.getLogger(__name__)

from gpodder.gtkui import draw
from gpodder.gtkui import flattr

import os
import gtk
import gobject
import cgi
import re

try:
    import gio
    have_gio = True
except ImportError:
    have_gio = False

# ----------------------------------------------------------

class GEpisode(model.PodcastEpisode):
    __slots__ = ()

    @property
    def title_markup(self):
        return '%s\n<small>%s</small>' % (cgi.escape(self.title),
                          cgi.escape(self.channel.title))

    @property
    def markup_new_episodes(self):
        if self.file_size > 0:
            length_str = '%s; ' % util.format_filesize(self.file_size)
        else:
            length_str = ''
        return ('<b>%s</b>\n<small>%s'+_('released %s')+ \
                '; '+_('from %s')+'</small>') % (\
                cgi.escape(re.sub('\s+', ' ', self.title)), \
                cgi.escape(length_str), \
                cgi.escape(self.pubdate_prop), \
                cgi.escape(re.sub('\s+', ' ', self.channel.title)))

    @property
    def markup_delete_episodes(self):
        if self.total_time and self.current_position:
            played_string = self.get_play_info_string()
        elif not self.is_new:
            played_string = _('played')
        else:
            played_string = _('unplayed')
        downloaded_string = self.get_age_string()
        if not downloaded_string:
            downloaded_string = _('today')
        return ('<b>%s</b>\n<small>%s; %s; '+_('downloaded %s')+ \
                '; '+_('from %s')+'</small>') % (\
                cgi.escape(self.title), \
                cgi.escape(util.format_filesize(self.file_size)), \
                cgi.escape(played_string), \
                cgi.escape(downloaded_string), \
                cgi.escape(self.channel.title))

class GPodcast(model.PodcastChannel):
    __slots__ = ()

    EpisodeClass = GEpisode

class Model(model.Model):
    PodcastClass = GPodcast

# ----------------------------------------------------------

# Singleton indicator if a row is a section
class SeparatorMarker(object): pass
class SectionMarker(object): pass

class EpisodeListModel(gtk.ListStore):
    C_URL, C_TITLE, C_FILESIZE_TEXT, C_EPISODE, C_STATUS_ICON, \
            C_PUBLISHED_TEXT, C_DESCRIPTION, C_TOOLTIP, \
            C_VIEW_SHOW_UNDELETED, C_VIEW_SHOW_DOWNLOADED, \
            C_VIEW_SHOW_UNPLAYED, C_FILESIZE, C_PUBLISHED, \
            C_TIME, C_TIME_VISIBLE, C_TOTAL_TIME, \
            C_LOCKED = range(17)

    VIEW_ALL, VIEW_UNDELETED, VIEW_DOWNLOADED, VIEW_UNPLAYED = range(4)

    # In which steps the UI is updated for "loading" animations
    _UI_UPDATE_STEP = .03

    # Steps for the "downloading" icon progress
    PROGRESS_STEPS = 20

    def __init__(self, config, on_filter_changed=lambda has_episodes: None):
        gtk.ListStore.__init__(self, str, str, str, object, \
                str, str, str, str, bool, bool, bool, \
                gobject.TYPE_INT64, int, str, bool, int, bool)

        self._config = config

        # Callback for when the filter / list changes, gets one parameter
        # (has_episodes) that is True if the list has any episodes
        self._on_filter_changed = on_filter_changed

        # Filter to allow hiding some episodes
        self._filter = self.filter_new()
        self._sorter = gtk.TreeModelSort(self._filter)
        self._view_mode = self.VIEW_ALL
        self._search_term = None
        self._search_term_eql = None
        self._filter.set_visible_func(self._filter_visible_func)

        # Are we currently showing the "all episodes" view?
        self._all_episodes_view = False

        self.ICON_AUDIO_FILE = 'audio-x-generic'
        self.ICON_VIDEO_FILE = 'video-x-generic'
        self.ICON_IMAGE_FILE = 'image-x-generic'
        self.ICON_GENERIC_FILE = 'text-x-generic'
        self.ICON_DOWNLOADING = gtk.STOCK_GO_DOWN
        self.ICON_DELETED = gtk.STOCK_DELETE

        if 'KDE_FULL_SESSION' in os.environ:
            # Workaround until KDE adds all the freedesktop icons
            # See https://bugs.kde.org/show_bug.cgi?id=233505 and
            #     http://gpodder.org/bug/553
            self.ICON_DELETED = 'archive-remove'


    def _format_filesize(self, episode):
        if episode.file_size > 0:
            return util.format_filesize(episode.file_size, digits=1)
        else:
            return None

    def _filter_visible_func(self, model, iter):
        # If searching is active, set visibility based on search text
        if self._search_term is not None:
            episode = model.get_value(iter, self.C_EPISODE)
            if episode is None:
                return False

            try:
                return self._search_term_eql.match(episode)
            except Exception, e:
                return True

        if self._view_mode == self.VIEW_ALL:
            return True
        elif self._view_mode == self.VIEW_UNDELETED:
            return model.get_value(iter, self.C_VIEW_SHOW_UNDELETED)
        elif self._view_mode == self.VIEW_DOWNLOADED:
            return model.get_value(iter, self.C_VIEW_SHOW_DOWNLOADED)
        elif self._view_mode == self.VIEW_UNPLAYED:
            return model.get_value(iter, self.C_VIEW_SHOW_UNPLAYED)

        return True

    def get_filtered_model(self):
        """Returns a filtered version of this episode model

        The filtered version should be displayed in the UI,
        as this model can have some filters set that should
        be reflected in the UI.
        """
        return self._sorter

    def has_episodes(self):
        """Returns True if episodes are visible (filtered)

        If episodes are visible with the current filter
        applied, return True (otherwise return False).
        """
        return bool(len(self._filter))

    def set_view_mode(self, new_mode):
        """Sets a new view mode for this model

        After setting the view mode, the filtered model
        might be updated to reflect the new mode."""
        if self._view_mode != new_mode:
            self._view_mode = new_mode
            self._filter.refilter()
            self._on_filter_changed(self.has_episodes())

    def get_view_mode(self):
        """Returns the currently-set view mode"""
        return self._view_mode

    def set_search_term(self, new_term):
        if self._search_term != new_term:
            self._search_term = new_term
            self._search_term_eql = query.UserEQL(new_term)
            self._filter.refilter()
            self._on_filter_changed(self.has_episodes())

    def get_search_term(self):
        return self._search_term

    def _format_description(self, episode, include_description=False):
        title = episode.trimmed_title
        a, b = '', ''
        if episode.state != gpodder.STATE_DELETED and episode.is_new:
            a, b = '<b>', '</b>'
        if include_description and self._all_episodes_view:
            return '%s%s%s\n%s' % (a, cgi.escape(title), b,
                    _('from %s') % cgi.escape(episode.channel.title))
        elif include_description:
            description = episode.one_line_description()
            if description.startswith(title):
                description = description[len(title):].strip()
            return '%s%s%s\n%s' % (a, cgi.escape(title), b,
                    cgi.escape(description))
        else:
            return ''.join((a, cgi.escape(title), b))

    def replace_from_channel(self, channel, include_description=False,
            treeview=None):
        """
        Add episode from the given channel to this model.
        Downloading should be a callback.
        include_description should be a boolean value (True if description
        is to be added to the episode row, or False if not)
        """

        # Remove old episodes in the list store
        self.clear()

        if treeview is not None:
            util.idle_add(treeview.queue_draw)

        self._all_episodes_view = getattr(channel, 'ALL_EPISODES_PROXY', False)

        # Avoid gPodder bug 1291
        if channel is None:
            episodes = []
        else:
            episodes = channel.get_all_episodes()

        if not isinstance(episodes, list):
            episodes = list(episodes)
        count = len(episodes)

        for position, episode in enumerate(episodes):
            iter = self.append((episode.url, \
                    episode.title, \
                    self._format_filesize(episode), \
                    episode, \
                    None, \
                    episode.cute_pubdate(), \
                    '', \
                    '', \
                    True, \
                    True, \
                    True, \
                    episode.file_size, \
                    episode.published, \
                    episode.get_play_info_string(), \
                    bool(episode.total_time), \
                    episode.total_time, \
                    episode.archive))

            self.update_by_iter(iter, include_description)

        self._on_filter_changed(self.has_episodes())

    def update_all(self, include_description=False):
        for row in self:
            self.update_by_iter(row.iter, include_description)

    def update_by_urls(self, urls, include_description=False):
        for row in self:
            if row[self.C_URL] in urls:
                self.update_by_iter(row.iter, include_description)

    def update_by_filter_iter(self, iter, include_description=False):
        # Convenience function for use by "outside" methods that use iters
        # from the filtered episode list model (i.e. all UI things normally)
        iter = self._sorter.convert_iter_to_child_iter(None, iter)
        self.update_by_iter(self._filter.convert_iter_to_child_iter(iter),
                include_description)

    def update_by_iter(self, iter, include_description=False):
        episode = self.get_value(iter, self.C_EPISODE)

        show_bullet = False
        show_padlock = False
        show_missing = False
        status_icon = None
        tooltip = []
        view_show_undeleted = True
        view_show_downloaded = False
        view_show_unplayed = False
        icon_theme = gtk.icon_theme_get_default()

        if episode.downloading:
            tooltip.append('%s %d%%' % (_('Downloading'),
                int(episode.download_task.progress*100)))

            index = int(self.PROGRESS_STEPS*episode.download_task.progress)
            status_icon = 'gpodder-progress-%d' % index

            view_show_downloaded = True
            view_show_unplayed = True
        else:
            if episode.state == gpodder.STATE_DELETED:
                tooltip.append(_('Deleted'))
                status_icon = self.ICON_DELETED
                view_show_undeleted = False
            elif episode.state == gpodder.STATE_NORMAL and \
                    episode.is_new:
                tooltip.append(_('New episode'))
                view_show_downloaded = True
                view_show_unplayed = True
            elif episode.state == gpodder.STATE_DOWNLOADED:
                tooltip = []
                view_show_downloaded = True
                view_show_unplayed = episode.is_new
                show_bullet = episode.is_new
                show_padlock = episode.archive
                show_missing = not episode.file_exists()
                filename = episode.local_filename(create=False, check_only=True)

                file_type = episode.file_type()
                if file_type == 'audio':
                    tooltip.append(_('Downloaded episode'))
                    status_icon = self.ICON_AUDIO_FILE
                elif file_type == 'video':
                    tooltip.append(_('Downloaded video episode'))
                    status_icon = self.ICON_VIDEO_FILE
                elif file_type == 'image':
                    tooltip.append(_('Downloaded image'))
                    status_icon = self.ICON_IMAGE_FILE
                else:
                    tooltip.append(_('Downloaded file'))
                    status_icon = self.ICON_GENERIC_FILE

                # Try to find a themed icon for this file
                if filename is not None and have_gio:
                    file = gio.File(filename)
                    if file.query_exists():
                        file_info = file.query_info('*')
                        icon = file_info.get_icon()
                        for icon_name in icon.get_names():
                            if icon_theme.has_icon(icon_name):
                                status_icon = icon_name
                                break

                if show_missing:
                    tooltip.append(_('missing file'))
                else:
                    if show_bullet:
                        if file_type == 'image':
                            tooltip.append(_('never displayed'))
                        elif file_type in ('audio', 'video'):
                            tooltip.append(_('never played'))
                        else:
                            tooltip.append(_('never opened'))
                    else:
                        if file_type == 'image':
                            tooltip.append(_('displayed'))
                        elif file_type in ('audio', 'video'):
                            tooltip.append(_('played'))
                        else:
                            tooltip.append(_('opened'))
                    if show_padlock:
                        tooltip.append(_('deletion prevented'))

                if episode.total_time > 0 and episode.current_position:
                    tooltip.append('%d%%' % (100.*float(episode.current_position)/float(episode.total_time),))

        if episode.total_time:
            total_time = util.format_time(episode.total_time)
            if total_time:
                tooltip.append(total_time)

        tooltip = ', '.join(tooltip)

        description = self._format_description(episode, include_description)
        self.set(iter, \
                self.C_STATUS_ICON, status_icon, \
                self.C_VIEW_SHOW_UNDELETED, view_show_undeleted, \
                self.C_VIEW_SHOW_DOWNLOADED, view_show_downloaded, \
                self.C_VIEW_SHOW_UNPLAYED, view_show_unplayed, \
                self.C_DESCRIPTION, description, \
                self.C_TOOLTIP, tooltip, \
                self.C_TIME, episode.get_play_info_string(), \
                self.C_TIME_VISIBLE, bool(episode.total_time), \
                self.C_TOTAL_TIME, episode.total_time, \
                self.C_LOCKED, episode.archive, \
                self.C_FILESIZE_TEXT, self._format_filesize(episode), \
                self.C_FILESIZE, episode.file_size)


class PodcastChannelProxy(object):
    ALL_EPISODES_PROXY = True

    def __init__(self, db, config, channels):
        self._db = db
        self._config = config
        self.channels = channels
        self.title =  _('All episodes')
        self.description = _('from all podcasts')
        #self.parse_error = ''
        self.url = ''
        self.section = ''
        self.id = None
        self.cover_file = coverart.CoverDownloader.ALL_EPISODES_ID
        self.cover_url = None
        self.auth_username = None
        self.auth_password = None
        self.pause_subscription = False
        self.sync_to_mp3_player = False
        self.auto_archive_episodes = False

    def get_statistics(self):
        # Get the total statistics for all channels from the database
        return self._db.get_podcast_statistics()

    def get_all_episodes(self):
        """Returns a generator that yields every episode"""
        return Model.sort_episodes_by_pubdate((e for c in self.channels
                for e in c.get_all_episodes()), True)


class PodcastListModel(gtk.ListStore):
    C_URL, C_TITLE, C_DESCRIPTION, C_PILL, C_CHANNEL, \
            C_COVER, C_ERROR, C_PILL_VISIBLE, \
            C_VIEW_SHOW_UNDELETED, C_VIEW_SHOW_DOWNLOADED, \
            C_VIEW_SHOW_UNPLAYED, C_HAS_EPISODES, C_SEPARATOR, \
            C_DOWNLOADS, C_COVER_VISIBLE, C_SECTION = range(16)

    SEARCH_COLUMNS = (C_TITLE, C_DESCRIPTION, C_SECTION)

    @classmethod
    def row_separator_func(cls, model, iter):
        return model.get_value(iter, cls.C_SEPARATOR)

    def __init__(self, cover_downloader):
        gtk.ListStore.__init__(self, str, str, str, gtk.gdk.Pixbuf, \
                object, gtk.gdk.Pixbuf, str, bool, bool, bool, bool, \
                bool, bool, int, bool, str)

        # Filter to allow hiding some episodes
        self._filter = self.filter_new()
        self._view_mode = -1
        self._search_term = None
        self._filter.set_visible_func(self._filter_visible_func)

        self._cover_cache = {}
        self._max_image_side = 40
        self._cover_downloader = cover_downloader

        self.ICON_DISABLED = 'gtk-media-pause'

    def _filter_visible_func(self, model, iter):
        # If searching is active, set visibility based on search text
        if self._search_term is not None:
            if model.get_value(iter, self.C_CHANNEL) == SectionMarker:
                return True
            key = self._search_term.lower()
            columns = (model.get_value(iter, c) for c in self.SEARCH_COLUMNS)
            return any((key in c.lower() for c in columns if c is not None))

        if model.get_value(iter, self.C_SEPARATOR):
            return True
        elif self._view_mode == EpisodeListModel.VIEW_ALL:
            return model.get_value(iter, self.C_HAS_EPISODES)
        elif self._view_mode == EpisodeListModel.VIEW_UNDELETED:
            return model.get_value(iter, self.C_VIEW_SHOW_UNDELETED)
        elif self._view_mode == EpisodeListModel.VIEW_DOWNLOADED:
            return model.get_value(iter, self.C_VIEW_SHOW_DOWNLOADED)
        elif self._view_mode == EpisodeListModel.VIEW_UNPLAYED:
            return model.get_value(iter, self.C_VIEW_SHOW_UNPLAYED)

        return True

    def get_filtered_model(self):
        """Returns a filtered version of this episode model

        The filtered version should be displayed in the UI,
        as this model can have some filters set that should
        be reflected in the UI.
        """
        return self._filter

    def set_view_mode(self, new_mode):
        """Sets a new view mode for this model

        After setting the view mode, the filtered model
        might be updated to reflect the new mode."""
        if self._view_mode != new_mode:
            self._view_mode = new_mode
            self._filter.refilter()

    def get_view_mode(self):
        """Returns the currently-set view mode"""
        return self._view_mode

    def set_search_term(self, new_term):
        if self._search_term != new_term:
            self._search_term = new_term
            self._filter.refilter()

    def get_search_term(self):
        return self._search_term

    def enable_separators(self, channeltree):
        channeltree.set_row_separator_func(self._show_row_separator)

    def _show_row_separator(self, model, iter):
        return model.get_value(iter, self.C_SEPARATOR)

    def _resize_pixbuf_keep_ratio(self, url, pixbuf):
        """
        Resizes a GTK Pixbuf but keeps its aspect ratio.
        Returns None if the pixbuf does not need to be
        resized or the newly resized pixbuf if it does.
        """
        changed = False
        result = None

        if url in self._cover_cache:
            return self._cover_cache[url]

        # Resize if too wide
        if pixbuf.get_width() > self._max_image_side:
            f = float(self._max_image_side)/pixbuf.get_width()
            (width, height) = (int(pixbuf.get_width()*f), int(pixbuf.get_height()*f))
            pixbuf = pixbuf.scale_simple(width, height, gtk.gdk.INTERP_BILINEAR)
            changed = True

        # Resize if too high
        if pixbuf.get_height() > self._max_image_side:
            f = float(self._max_image_side)/pixbuf.get_height()
            (width, height) = (int(pixbuf.get_width()*f), int(pixbuf.get_height()*f))
            pixbuf = pixbuf.scale_simple(width, height, gtk.gdk.INTERP_BILINEAR)
            changed = True

        if changed:
            self._cover_cache[url] = pixbuf
            result = pixbuf

        return result

    def _resize_pixbuf(self, url, pixbuf):
        if pixbuf is None:
            return None

        return self._resize_pixbuf_keep_ratio(url, pixbuf) or pixbuf

    def _overlay_pixbuf(self, pixbuf, icon):
        try:
            icon_theme = gtk.icon_theme_get_default()
            emblem = icon_theme.load_icon(icon, self._max_image_side/2, 0)
            (width, height) = (emblem.get_width(), emblem.get_height())
            xpos = pixbuf.get_width() - width
            ypos = pixbuf.get_height() - height
            if ypos < 0:
                # need to resize overlay for none standard icon size
                emblem = icon_theme.load_icon(icon, pixbuf.get_height() - 1, 0)
                (width, height) = (emblem.get_width(), emblem.get_height())
                xpos = pixbuf.get_width() - width
                ypos = pixbuf.get_height() - height
            emblem.composite(pixbuf, xpos, ypos, width, height, xpos, ypos, 1, 1, gtk.gdk.INTERP_BILINEAR, 255)
        except:
            pass

        return pixbuf

    def _get_cover_image(self, channel, add_overlay=False):
        if self._cover_downloader is None:
            return None

        pixbuf = self._cover_downloader.get_cover(channel, avoid_downloading=True)
        pixbuf_overlay = self._resize_pixbuf(channel.url, pixbuf)
        if add_overlay and channel.pause_subscription:
            pixbuf_overlay = self._overlay_pixbuf(pixbuf_overlay, self.ICON_DISABLED)
            pixbuf_overlay.saturate_and_pixelate(pixbuf_overlay, 0.0, False)

        return pixbuf_overlay

    def _get_pill_image(self, channel, count_downloaded, count_unplayed):
        if count_unplayed > 0 or count_downloaded > 0:
            return draw.draw_pill_pixbuf(str(count_unplayed), str(count_downloaded))
        else:
            return None

    def _format_description(self, channel, total, deleted, \
            new, downloaded, unplayed):
        title_markup = cgi.escape(channel.title)
        if not channel.pause_subscription:
            description_markup = cgi.escape(util.get_first_line(channel.description) or ' ')
        else:
            description_markup = cgi.escape(_('Subscription paused'))
        d = []
        if new:
            d.append('<span weight="bold">')
        d.append(title_markup)
        if new:
            d.append('</span>')

        if description_markup.strip():
            return ''.join(d+['\n', '<small>', description_markup, '</small>'])
        else:
            return ''.join(d)

    def _format_error(self, channel):
        #if channel.parse_error:
        #    return str(channel.parse_error)
        #else:
        #    return None
        return None

    def set_channels(self, db, config, channels):
        # Clear the model and update the list of podcasts
        self.clear()

        def channel_to_row(channel, add_overlay=False):
            return (channel.url, '', '', None, channel,
                    self._get_cover_image(channel, add_overlay), '', True,
                    True, True, True, True, False, 0, True, '')

        if config.podcast_list_view_all and channels:
            all_episodes = PodcastChannelProxy(db, config, channels)
            iter = self.append(channel_to_row(all_episodes))
            self.update_by_iter(iter)

            # Separator item
            if not config.podcast_list_sections:
                self.append(('', '', '', None, SeparatorMarker, None, '',
                    True, True, True, True, True, True, 0, False, ''))

        def key_func(pair):
            section, podcast = pair
            return (section, model.Model.podcast_sort_key(podcast))

        if config.podcast_list_sections:
            def convert(channels):
                for channel in channels:
                    yield (channel.group_by, channel)
        else:
            def convert(channels):
                for channel in channels:
                    yield (None, channel)

        added_sections = []
        old_section = None
        for section, channel in sorted(convert(channels), key=key_func):
            if old_section != section:
                it = self.append(('-', section, '', None, SectionMarker, None,
                    '', True, True, True, True, True, False, 0, False, section))
                added_sections.append(it)
                old_section = section

            iter = self.append(channel_to_row(channel, True))
            self.update_by_iter(iter)

        # Update section header stats only after all podcasts
        # have been added to the list to get the stats right
        for it in added_sections:
            self.update_by_iter(it)

    def get_filter_path_from_url(self, url):
        # Return the path of the filtered model for a given URL
        child_path = self.get_path_from_url(url)
        if child_path is None:
            return None
        else:
            return self._filter.convert_child_path_to_path(child_path)

    def get_path_from_url(self, url):
        # Return the tree model path for a given URL
        if url is None:
            return None

        for row in self:
            if row[self.C_URL] == url:
                    return row.path
        return None

    def update_first_row(self):
        # Update the first row in the model (for "all episodes" updates)
        self.update_by_iter(self.get_iter_first())

    def update_by_urls(self, urls):
        # Given a list of URLs, update each matching row
        for row in self:
            if row[self.C_URL] in urls:
                self.update_by_iter(row.iter)

    def iter_is_first_row(self, iter):
        iter = self._filter.convert_iter_to_child_iter(iter)
        path = self.get_path(iter)
        return (path == (0,))

    def update_by_filter_iter(self, iter):
        self.update_by_iter(self._filter.convert_iter_to_child_iter(iter))

    def update_all(self):
        for row in self:
            self.update_by_iter(row.iter)

    def update_sections(self):
        for row in self:
            if row[self.C_CHANNEL] is SectionMarker:
                self.update_by_iter(row.iter)

    def update_by_iter(self, iter):
        if iter is None:
            return

        # Given a GtkTreeIter, update volatile information
        channel = self.get_value(iter, self.C_CHANNEL)

        if channel is SectionMarker:
            section = self.get_value(iter, self.C_TITLE)

            # This row is a section header - update its visibility flags
            channels = [c for c in (row[self.C_CHANNEL] for row in self)
                    if isinstance(c, GPodcast) and c.section == section]

            # Calculate the stats over all podcasts of this section
            total, deleted, new, downloaded, unplayed = map(sum,
                    zip(*[c.get_statistics() for c in channels]))

            # We could customized the section header here with the list
            # of channels and their stats (i.e. add some "new" indicator)
            description = '<span size="16000"> </span><b>%s</b>' % (
                    cgi.escape(section))

            self.set(iter,
                self.C_DESCRIPTION, description,
                self.C_SECTION, section,
                self.C_VIEW_SHOW_UNDELETED, total - deleted > 0,
                self.C_VIEW_SHOW_DOWNLOADED, downloaded + new > 0,
                self.C_VIEW_SHOW_UNPLAYED, unplayed + new > 0)

        if (not isinstance(channel, GPodcast) and
            not isinstance(channel, PodcastChannelProxy)):
            return

        total, deleted, new, downloaded, unplayed = channel.get_statistics()
        description = self._format_description(channel, total, deleted, new, \
                downloaded, unplayed)

        pill_image = self._get_pill_image(channel, downloaded, unplayed)

        self.set(iter, \
                self.C_TITLE, channel.title, \
                self.C_DESCRIPTION, description, \
                self.C_SECTION, channel.section, \
                self.C_ERROR, self._format_error(channel), \
                self.C_PILL, pill_image, \
                self.C_PILL_VISIBLE, pill_image != None, \
                self.C_VIEW_SHOW_UNDELETED, total - deleted > 0, \
                self.C_VIEW_SHOW_DOWNLOADED, downloaded + new > 0, \
                self.C_VIEW_SHOW_UNPLAYED, unplayed + new > 0, \
                self.C_HAS_EPISODES, total > 0, \
                self.C_DOWNLOADS, downloaded)

    def clear_cover_cache(self, podcast_url):
        if podcast_url in self._cover_cache:
            logger.info('Clearing cover from cache: %s', podcast_url)
            del self._cover_cache[podcast_url]

    def add_cover_by_channel(self, channel, pixbuf):
        # Resize and add the new cover image
        pixbuf = self._resize_pixbuf(channel.url, pixbuf)
        if channel.pause_subscription:
            pixbuf = self._overlay_pixbuf(pixbuf, self.ICON_DISABLED)
            pixbuf.saturate_and_pixelate(pixbuf, 0.0, False)

        for row in self:
            if row[self.C_URL] == channel.url:
                row[self.C_COVER] = pixbuf
                break


########NEW FILE########
__FILENAME__ = opml
# -*- coding: utf-8 -*-
#
# gPodder - A media aggregator and podcast client
# Copyright (c) 2005-2014 Thomas Perl and the gPodder Team
#
# gPodder is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# gPodder is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#


#
#  gpodder.gtkui.opml - Module for displaying OPML feeds (2009-08-13)
#


import gtk

import cgi
import urllib

class OpmlListModel(gtk.ListStore):
    C_SELECTED, C_TITLE, C_DESCRIPTION_MARKUP, C_URL = range(4)

    def __init__(self, importer):
        gtk.ListStore.__init__(self, bool, str, str, str)
        for channel in importer.items:
            self.append([False, channel['title'],
                self._format_channel(channel), channel['url']])

    def _format_channel(self, channel):
        title = cgi.escape(urllib.unquote_plus(channel['title']))
        description = cgi.escape(channel['description'])
        return '<b>%s</b>\n%s' % (title, description)


########NEW FILE########
__FILENAME__ = services
# -*- coding: utf-8 -*-
#
# gPodder - A media aggregator and podcast client
# Copyright (c) 2005-2014 Thomas Perl and the gPodder Team
#
# gPodder is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# gPodder is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#


#
#  gpodder.gtkui.services - UI parts for the services module (2009-08-24)
#


import gpodder
_ = gpodder.gettext

from gpodder.services import ObservableService

import logging
logger = logging.getLogger(__name__)

from gpodder import util
from gpodder import coverart

import gtk


class CoverDownloader(ObservableService):
    """
    This class manages downloading cover art and notification
    of other parts of the system. Downloading cover art can
    happen either synchronously via get_cover() or in
    asynchronous mode via request_cover(). When in async mode,
    the cover downloader will send the cover via the
    'cover-available' message (via the ObservableService).
    """

    def __init__(self):
        self.downloader = coverart.CoverDownloader()
        signal_names = ['cover-available', 'cover-removed']
        ObservableService.__init__(self, signal_names)

    def request_cover(self, channel, custom_url=None, avoid_downloading=False):
        """
        Sends an asynchronous request to download a
        cover for the specific channel.

        After the cover has been downloaded, the
        "cover-available" signal will be sent with
        the channel url and new cover as pixbuf.

        If you specify a custom_url, the cover will
        be downloaded from the specified URL and not
        taken from the channel metadata.

        The optional parameter "avoid_downloading",
        when true, will make sure we return only
        already-downloaded covers and return None
        when we have no cover on the local disk.
        """
        logger.debug('cover download request for %s', channel.url)
        util.run_in_background(lambda: self.__get_cover(channel,
            custom_url, True, avoid_downloading))

    def get_cover(self, channel, custom_url=None, avoid_downloading=False):
        """
        Sends a synchronous request to download a
        cover for the specified channel.

        The cover will be returned to the caller.

        The custom_url has the same semantics as
        in request_cover().

        The optional parameter "avoid_downloading",
        when true, will make sure we return only
        already-downloaded covers and return None
        when we have no cover on the local disk.
        """
        (url, pixbuf) = self.__get_cover(channel, custom_url, False, avoid_downloading)
        return pixbuf

    def replace_cover(self, channel, custom_url=None):
        """
        This is a convenience function that deletes
        the current cover file and requests a new
        cover from the URL specified.
        """
        self.request_cover(channel, custom_url)

    def __get_cover(self, channel, url, async=False, avoid_downloading=False):
        def get_filename():
            return self.downloader.get_cover(channel.cover_file,
                    url or channel.cover_url, channel.url, channel.title,
                    channel.auth_username, channel.auth_password,
                    not avoid_downloading)

        if url is not None:
            filename = get_filename()
            if filename.startswith(channel.cover_file):
                logger.info('Replacing cover: %s', filename)
                util.delete_file(filename)

        filename = get_filename()
        pixbuf = None

        try:
            pixbuf = gtk.gdk.pixbuf_new_from_file(filename)
        except Exception, e:
            logger.warn('Cannot load cover art', exc_info=True)
            if filename.startswith(channel.cover_file):
                logger.info('Deleting broken cover: %s', filename)
                util.delete_file(filename)
                filename = get_filename()
                pixbuf = gtk.gdk.pixbuf_new_from_file(filename)

        if async:
            self.notify('cover-available', channel, pixbuf)
        else:
            return (channel.url, pixbuf)


########NEW FILE########
__FILENAME__ = shownotes
# -*- coding: utf-8 -*-
#
# gPodder - A media aggregator and podcast client
# Copyright (c) 2005-2014 Thomas Perl and the gPodder Team
#
# gPodder is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# gPodder is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#

import gtk
import gtk.gdk
import gobject
import pango
import os
import cgi


import gpodder

_ = gpodder.gettext

import logging
logger = logging.getLogger(__name__)

from gpodder import util
from gpodder.gtkui.draw import draw_text_box_centered


try:
    import webkit
    webview_signals = gobject.signal_list_names(webkit.WebView)
    if 'navigation-policy-decision-requested' in webview_signals:
        have_webkit = True
    else:
        logger.warn('Your WebKit is too old (gPodder bug 1001).')
        have_webkit = False
except ImportError:
    have_webkit = False


class gPodderShownotes:
    def __init__(self, shownotes_pane):
        self.shownotes_pane = shownotes_pane

        self.scrolled_window = gtk.ScrolledWindow()
        self.scrolled_window.set_shadow_type(gtk.SHADOW_IN)
        self.scrolled_window.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
        self.scrolled_window.add(self.init())
        self.scrolled_window.show_all()

        self.da_message = gtk.DrawingArea()
        self.da_message.connect('expose-event', \
                                    self.on_shownotes_message_expose_event)
        self.shownotes_pane.add(self.da_message)
        self.shownotes_pane.add(self.scrolled_window)

        self.set_complain_about_selection(True)
        self.hide_pane()

    # Either show the shownotes *or* a message, 'Please select an episode'
    def set_complain_about_selection(self, message=True):
        if message:
            self.scrolled_window.hide()
            self.da_message.show()
        else:
            self.da_message.hide()
            self.scrolled_window.show()

    def set_episodes(self, selected_episodes):
        if self.pane_is_visible:
            if len(selected_episodes) == 1:
                episode = selected_episodes[0]
                heading = episode.title
                subheading = _('from %s') % (episode.channel.title)
                self.update(heading, subheading, episode)
                self.set_complain_about_selection(False)
            else:
                self.set_complain_about_selection(True)

    def show_pane(self, selected_episodes):
        self.pane_is_visible = True
        self.set_episodes(selected_episodes)
        self.shownotes_pane.show()

    def hide_pane(self):
        self.pane_is_visible = False
        self.shownotes_pane.hide()

    def toggle_pane_visibility(self, selected_episodes):
        if self.pane_is_visible:
            self.hide_pane()
        else:
            self.show_pane(selected_episodes)

    def on_shownotes_message_expose_event(self, drawingarea, event):
        ctx = event.window.cairo_create()
        ctx.rectangle(event.area.x, event.area.y, \
                      event.area.width, event.area.height)
        ctx.clip()

        # paint the background white
        colormap = event.window.get_colormap()
        gc = event.window.new_gc(foreground=colormap.alloc_color('white'))
        event.window.draw_rectangle(gc, True, event.area.x, event.area.y, \
                                    event.area.width, event.area.height)

        x, y, width, height, depth = event.window.get_geometry()
        text = _('Please select an episode')
        draw_text_box_centered(ctx, drawingarea, width, height, text, None, None)
        return False


class gPodderShownotesText(gPodderShownotes):
    def init(self):
        self.text_view = gtk.TextView()
        self.text_view.set_wrap_mode(gtk.WRAP_WORD_CHAR)
        self.text_view.set_border_width(10)
        self.text_view.set_editable(False)
        self.text_buffer = gtk.TextBuffer()
        self.text_buffer.create_tag('heading', scale=pango.SCALE_LARGE, weight=pango.WEIGHT_BOLD)
        self.text_buffer.create_tag('subheading', scale=pango.SCALE_SMALL)
        self.text_view.set_buffer(self.text_buffer)
        self.text_view.modify_bg(gtk.STATE_NORMAL,
                gtk.gdk.color_parse('#ffffff'))
        return self.text_view

    def update(self, heading, subheading, episode):
        self.text_buffer.set_text('')
        self.text_buffer.insert_with_tags_by_name(self.text_buffer.get_end_iter(), heading, 'heading')
        self.text_buffer.insert_at_cursor('\n')
        self.text_buffer.insert_with_tags_by_name(self.text_buffer.get_end_iter(), subheading, 'subheading')
        self.text_buffer.insert_at_cursor('\n\n')
        self.text_buffer.insert(self.text_buffer.get_end_iter(), util.remove_html_tags(episode.description))
        self.text_buffer.place_cursor(self.text_buffer.get_start_iter())


class gPodderShownotesHTML(gPodderShownotes):
    SHOWNOTES_HTML_TEMPLATE = """
    <html>
      <head>
        <meta http-equiv="content-type" content="text/html; charset=utf-8"/>
      </head>
      <body>
        <span style="font-size: big; font-weight: bold;">%s</span>
        <br>
        <span style="font-size: small;">%s (%s)</span>
        <hr style="border: 1px #eeeeee solid;">
        <p>%s</p>
      </body>
    </html>
    """

    def init(self):
        self.html_view = webkit.WebView()
        self.html_view.connect('navigation-policy-decision-requested',
                self._navigation_policy_decision)
        self.html_view.load_html_string('', '')
        return self.html_view

    def _navigation_policy_decision(self, wv, fr, req, action, decision):
        REASON_LINK_CLICKED, REASON_OTHER = 0, 5
        if action.get_reason() == REASON_LINK_CLICKED:
            util.open_website(req.get_uri())
            decision.ignore()
        elif action.get_reason() == REASON_OTHER:
            decision.use()
        else:
            decision.ignore()

    def update(self, heading, subheading, episode):
        html = self.SHOWNOTES_HTML_TEMPLATE % (
                cgi.escape(heading),
                cgi.escape(subheading),
                episode.get_play_info_string(),
                episode.description_html,
        )
        url = os.path.dirname(episode.channel.url)
        self.html_view.load_html_string(html, url)


########NEW FILE########
__FILENAME__ = widgets
#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# gPodder - A media aggregator and podcast client
# Copyright (c) 2005-2014 Thomas Perl and the gPodder Team
#
# gPodder is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# gPodder is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#


#
#  widgets.py -- Additional widgets for gPodder
#  Thomas Perl <thp@gpodder.org> 2009-03-31
#

import gtk
import gobject
import pango

import cgi

class SimpleMessageArea(gtk.HBox):
    """A simple, yellow message area. Inspired by gedit.

    Original C source code:
    http://svn.gnome.org/viewvc/gedit/trunk/gedit/gedit-message-area.c
    """
    def __init__(self, message, buttons=()):
        gtk.HBox.__init__(self, spacing=6)
        self.set_border_width(6)
        self.__in_style_set = False
        self.connect('style-set', self.__style_set)
        self.connect('expose-event', self.__expose_event)

        self.__label = gtk.Label()
        self.__label.set_alignment(0.0, 0.5)
        self.__label.set_line_wrap(False)
        self.__label.set_ellipsize(pango.ELLIPSIZE_END)
        self.__label.set_markup('<b>%s</b>' % cgi.escape(message))
        self.pack_start(self.__label, expand=True, fill=True)

        hbox = gtk.HBox()
        for button in buttons:
            hbox.pack_start(button, expand=True, fill=False)
        self.pack_start(hbox, expand=False, fill=False)

    def set_markup(self, markup, line_wrap=True, min_width=3, max_width=100):
        # The longest line should determine the size of the label
        width_chars = max(len(line) for line in markup.splitlines())

        # Enforce upper and lower limits for the width
        width_chars = max(min_width, min(max_width, width_chars))

        self.__label.set_width_chars(width_chars)
        self.__label.set_markup(markup)
        self.__label.set_line_wrap(line_wrap)

    def __style_set(self, widget, previous_style):
        if self.__in_style_set:
            return

        w = gtk.Window(gtk.WINDOW_POPUP)
        w.set_name('gtk-tooltip')
        w.ensure_style()
        style = w.get_style()

        self.__in_style_set = True
        self.set_style(style)
        self.__label.set_style(style)
        self.__in_style_set = False

        w.destroy()

        self.queue_draw()

    def __expose_event(self, widget, event):
        style = widget.get_style()
        rect = widget.get_allocation()
        style.paint_flat_box(widget.window, gtk.STATE_NORMAL,
                gtk.SHADOW_OUT, None, widget, "tooltip",
                rect.x, rect.y, rect.width, rect.height)
        return False


class SpinningProgressIndicator(gtk.Image):
    # Progress indicator loading inspired by glchess from gnome-games-clutter
    def __init__(self, size=32):
        gtk.Image.__init__(self)

        self._frames = []
        self._frame_id = 0

        # Load the progress indicator
        icon_theme = gtk.icon_theme_get_default()

        try:
            icon = icon_theme.load_icon('process-working', size, 0)
            width, height = icon.get_width(), icon.get_height()
            if width < size or height < size:
                size = min(width, height)
            for row in range(height/size):
                for column in range(width/size):
                    frame = icon.subpixbuf(column*size, row*size, size, size)
                    self._frames.append(frame)
            # Remove the first frame (the "idle" icon)
            if self._frames:
                self._frames.pop(0)
            self.step_animation()
        except:
            # FIXME: This is not very beautiful :/
            self.set_from_stock(gtk.STOCK_EXECUTE, gtk.ICON_SIZE_BUTTON)

    def step_animation(self):
        if len(self._frames) > 1:
            self._frame_id += 1
            if self._frame_id >= len(self._frames):
                self._frame_id = 0
            self.set_from_pixbuf(self._frames[self._frame_id])


########NEW FILE########
__FILENAME__ = jsonconfig
# -*- coding: utf-8 -*-
#
# gPodder - A media aggregator and podcast client
# Copyright (c) 2005-2014 Thomas Perl and the gPodder Team
#
# gPodder is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# gPodder is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#


#
#  jsonconfig.py -- JSON Config Backend
#  Thomas Perl <thp@gpodder.org>   2012-01-18
#

import copy

try:
    # For Python < 2.6, we use the "simplejson" add-on module
    import simplejson as json
except ImportError:
    # Python 2.6 already ships with a nice "json" module
    import json


class JsonConfigSubtree(object):
    def __init__(self, parent, name):
        self._parent = parent
        self._name = name

    def __repr__(self):
        return '<Subtree %r of JsonConfig>' % (self._name,)

    def _attr(self, name):
        return '.'.join((self._name, name))

    def __getitem__(self, name):
        return self._parent._lookup(self._name).__getitem__(name)

    def __delitem__(self, name):
        self._parent._lookup(self._name).__delitem__(name)

    def __setitem__(self, name, value):
        self._parent._lookup(self._name).__setitem__(name, value)

    def __getattr__(self, name):
        if name == 'keys':
            # Kludge for using dict() on a JsonConfigSubtree
            return getattr(self._parent._lookup(self._name), name)

        return getattr(self._parent, self._attr(name))

    def __setattr__(self, name, value):
        if name.startswith('_'):
            object.__setattr__(self, name, value)
        else:
            self._parent.__setattr__(self._attr(name), value)


class JsonConfig(object):
    _INDENT = 2

    def __init__(self, data=None, default=None, on_key_changed=None):
        """
        Create a new JsonConfig object

        data: A JSON string that contains the data to load (optional)
        default: A dict that contains default config values (optional)
        on_key_changed: Callback when a value changes (optional)

        The signature of on_key_changed looks like this:

            func(name, old_value, new_value)

            name: The key name, e.g. "ui.gtk.show_toolbar"
            old_value: The old value, e.g. False
            new_value: The new value, e.g. True

        For newly-set keys, on_key_changed is also called. In this case,
        None will be the old_value:

        >>> def callback(*args): print 'callback:', args
        >>> c = JsonConfig(on_key_changed=callback)
        >>> c.a.b = 10
        callback: ('a.b', None, 10)
        >>> c.a.b = 11
        callback: ('a.b', 10, 11)
        >>> c.x.y.z = [1,2,3]
        callback: ('x.y.z', None, [1, 2, 3])
        >>> c.x.y.z = 42
        callback: ('x.y.z', [1, 2, 3], 42)

        Please note that dict-style access will not call on_key_changed:

        >>> def callback(*args): print 'callback:', args
        >>> c = JsonConfig(on_key_changed=callback)
        >>> c.a.b = 1        # This works as expected
        callback: ('a.b', None, 1)
        >>> c.a['c'] = 10    # This doesn't call on_key_changed!
        >>> del c.a['c']     # This also doesn't call on_key_changed!
        """
        self._default = default
        self._data = copy.deepcopy(self._default) or {}
        self._on_key_changed = on_key_changed
        if data is not None:
            self._restore(data)

    def _restore(self, backup):
        """
        Restore a previous state saved with repr()

        This function allows you to "snapshot" the current values of
        the configuration and reload them later on. Any missing
        default values will be added on top of the restored config.

        Returns True if new keys from the default config have been added,
        False if no keys have been added (backup contains all default keys)

        >>> c = JsonConfig()
        >>> c.a.b = 10
        >>> backup = repr(c)
        >>> print c.a.b
        10
        >>> c.a.b = 11
        >>> print c.a.b
        11
        >>> c._restore(backup)
        False
        >>> print c.a.b
        10
        """
        self._data = json.loads(backup)
        # Add newly-added default configuration options
        if self._default is not None:
            return self._merge_keys(self._default)

        return False

    def _merge_keys(self, merge_source):
        """Merge keys from merge_source into this config object

        Return True if new keys were merged, False otherwise
        """
        added_new_key = False
        # Recurse into the data and add missing items
        work_queue = [(self._data, merge_source)]
        while work_queue:
            data, default = work_queue.pop()
            for key, value in default.iteritems():
                if key not in data:
                    # Copy defaults for missing key
                    data[key] = copy.deepcopy(value)
                    added_new_key = True
                elif isinstance(value, dict):
                    # Recurse into sub-dictionaries
                    work_queue.append((data[key], value))
                elif type(value) != type(data[key]):
                    # Type mismatch of current value and default
                    if type(value) == int and type(data[key]) == float:
                        # Convert float to int if default value is int
                        data[key] = int(data[key])

        return added_new_key

    def __repr__(self):
        """
        >>> c = JsonConfig('{"a": 1}')
        >>> print c
        {
          "a": 1
        }
        """
        return json.dumps(self._data, indent=self._INDENT)

    def _lookup(self, name):
        return reduce(lambda d, k: d[k], name.split('.'), self._data)

    def _keys_iter(self):
        work_queue = []
        work_queue.append(([], self._data))
        while work_queue:
            path, data = work_queue.pop(0)

            if isinstance(data, dict):
                for key in sorted(data.keys()):
                    work_queue.append((path + [key], data[key]))
            else:
                yield '.'.join(path)

    def __getattr__(self, name):
        try:
            value = self._lookup(name)
            if not isinstance(value, dict):
                return value
        except KeyError:
            pass

        return JsonConfigSubtree(self, name)

    def __setattr__(self, name, value):
        if name.startswith('_'):
            object.__setattr__(self, name, value)
            return

        attrs = name.split('.')
        target_dict = self._data

        while attrs:
            attr = attrs.pop(0)
            if not attrs:
                old_value = target_dict.get(attr, None)
                if old_value != value or attr not in target_dict:
                    target_dict[attr] = value
                    if self._on_key_changed is not None:
                        self._on_key_changed(name, old_value, value)
                break

            target = target_dict.get(attr, None)
            if target is None or not isinstance(target, dict):
                target_dict[attr] = target = {}
            target_dict = target


########NEW FILE########
__FILENAME__ = log
# -*- coding: utf-8 -*-
#
# gPodder - A media aggregator and podcast client
# Copyright (c) 2005-2014 Thomas Perl and the gPodder Team
#
# gPodder is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# gPodder is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#

# gpodder.log - Logging setup
# Thomas Perl <thp@gpodder.org>; 2012-03-02
# Based on an initial draft by Neal Walfield


import gpodder

import glob
import logging
import os
import sys
import time
import traceback

logger = logging.getLogger(__name__)

def setup(verbose=True):
    # Configure basic stdout logging
    STDOUT_FMT = '%(created)f [%(name)s] %(levelname)s: %(message)s'
    logging.basicConfig(format=STDOUT_FMT,
            level=logging.DEBUG if verbose else logging.WARNING)

    # Replace except hook with a custom one that logs it as an error
    original_excepthook = sys.excepthook
    def on_uncaught_exception(exctype, value, tb):
        message = ''.join(traceback.format_exception(exctype, value, tb))
        logger.error('Uncaught exception: %s', message)
        original_excepthook(exctype, value, tb)
    sys.excepthook = on_uncaught_exception

    if os.environ.get('GPODDER_WRITE_LOGS', 'yes') != 'no':
        # Configure file based logging
        logging_basename = time.strftime('%Y-%m-%d.log')
        logging_directory = os.path.join(gpodder.home, 'Logs')
        if not os.path.isdir(logging_directory):
            try:
                os.makedirs(logging_directory)
            except:
                logger.warn('Cannot create output directory: %s',
                        logging_directory)
                return False

        # Keep logs around for 5 days
        LOG_KEEP_DAYS = 5

        # Purge old logfiles if they are older than LOG_KEEP_DAYS days
        old_logfiles = glob.glob(os.path.join(logging_directory, '*-*-*.log'))
        for old_logfile in old_logfiles:
            st = os.stat(old_logfile)
            if time.time() - st.st_mtime > 60*60*24*LOG_KEEP_DAYS:
                logger.info('Purging old logfile: %s', old_logfile)
                try:
                    os.remove(old_logfile)
                except:
                    logger.warn('Cannot purge logfile: %s', exc_info=True)

        root = logging.getLogger()
        logfile = os.path.join(logging_directory, logging_basename)
        file_handler = logging.FileHandler(logfile, 'a', 'utf-8')
        FILE_FMT = '%(asctime)s [%(name)s] %(levelname)s: %(message)s'
        file_handler.setFormatter(logging.Formatter(FILE_FMT))
        root.addHandler(file_handler)

    logger.debug('==== gPodder starts up (ui=%s) ===', ', '.join(name
        for name in ('cli', 'gtk', 'qml') if getattr(gpodder.ui, name, False)))

    return True


########NEW FILE########
__FILENAME__ = minidb
#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# gPodder - A media aggregator and podcast client
# Copyright (c) 2005-2014 Thomas Perl and the gPodder Team
#
# gPodder is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# gPodder is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#

# gpodder.minidb - A simple SQLite store for Python objects
# Thomas Perl, 2010-01-28

# based on: "ORM wie eine Kirchenmaus - a very poor ORM implementation
#            by thp, 2009-11-29 (thp.io/about)"

# This module is also available separately at:
#    http://thp.io/2010/minidb/


# For Python 2.5, we need to request the "with" statement
from __future__ import with_statement

try:
    import sqlite3.dbapi2 as sqlite
except ImportError:
    try:
        from pysqlite2 import dbapi2 as sqlite
    except ImportError:
        raise Exception('Please install SQLite3 support.')


import threading

class Store(object):
    def __init__(self, filename=':memory:'):
        self.db = sqlite.connect(filename, check_same_thread=False)
        self.lock = threading.RLock()

    def _schema(self, class_):
        return class_.__name__, list(sorted(class_.__slots__))

    def _set(self, o, slot, value):
        # Set a slot on the given object to value, doing a cast if
        # necessary. The value None is special-cased and never cast.
        cls = o.__class__.__slots__[slot]
        if value is not None:
            if isinstance(value, unicode):
                value = value.decode('utf-8')
            value = cls(value)
        setattr(o, slot, value)

    def commit(self):
        with self.lock:
            self.db.commit()

    def close(self):
        with self.lock:
            self.db.execute('VACUUM')
            self.db.close()

    def _register(self, class_):
        with self.lock:
            table, slots = self._schema(class_)
            cur = self.db.execute('PRAGMA table_info(%s)' % table)
            available = cur.fetchall()

            if available:
                available = [row[1] for row in available]
                missing_slots = (s for s in slots if s not in available)
                for slot in missing_slots:
                    self.db.execute('ALTER TABLE %s ADD COLUMN %s TEXT' % (table,
                        slot))
            else:
                self.db.execute('CREATE TABLE %s (%s)' % (table,
                        ', '.join('%s TEXT'%s for s in slots)))

    def convert(self, v):
        if isinstance(v, unicode):
            return v
        elif isinstance(v, str):
            # XXX: Rewrite ^^^ as "isinstance(v, bytes)" in Python 3
            return v.decode('utf-8')
        else:
            return str(v)

    def update(self, o, **kwargs):
        self.remove(o)
        for k, v in kwargs.items():
            setattr(o, k, v)
        self.save(o)

    def save(self, o):
        if hasattr(o, '__iter__'):
            klass = None
            for child in o:
                if klass is None:
                    klass = child.__class__
                    self._register(klass)
                    table, slots = self._schema(klass)

                if not isinstance(child, klass):
                    raise ValueError('Only one type of object allowed')

                used = [s for s in slots if getattr(child, s, None) is not None]
                values = [self.convert(getattr(child, slot)) for slot in used]
                self.db.execute('INSERT INTO %s (%s) VALUES (%s)' % (table,
                    ', '.join(used), ', '.join('?'*len(used))), values)
            return

        with self.lock:
            self._register(o.__class__)
            table, slots = self._schema(o.__class__)

            values = [self.convert(getattr(o, slot)) for slot in slots]
            self.db.execute('INSERT INTO %s (%s) VALUES (%s)' % (table,
                ', '.join(slots), ', '.join('?'*len(slots))), values)

    def delete(self, class_, **kwargs):
        with self.lock:
            self._register(class_)
            table, slots = self._schema(class_)
            sql = 'DELETE FROM %s' % (table,)
            if kwargs:
                sql += ' WHERE %s' % (' AND '.join('%s=?' % k for k in kwargs))
            try:
                self.db.execute(sql, kwargs.values())
                return True
            except Exception, e:
                return False

    def remove(self, o):
        if hasattr(o, '__iter__'):
            for child in o:
                self.remove(child)
            return

        with self.lock:
            self._register(o.__class__)
            table, slots = self._schema(o.__class__)

            # Use "None" as wildcard selector in remove actions
            slots = [s for s in slots if getattr(o, s, None) is not None]

            values = [self.convert(getattr(o, slot)) for slot in slots]
            self.db.execute('DELETE FROM %s WHERE %s' % (table,
                ' AND '.join('%s=?'%s for s in slots)), values)

    def load(self, class_, **kwargs):
        with self.lock:
            self._register(class_)
            table, slots = self._schema(class_)
            sql = 'SELECT %s FROM %s' % (', '.join(slots), table)
            if kwargs:
                sql += ' WHERE %s' % (' AND '.join('%s=?' % k for k in kwargs))
            try:
                cur = self.db.execute(sql, kwargs.values())
            except Exception, e:
                raise
            def apply(row):
                o = class_.__new__(class_)
                for attr, value in zip(slots, row):
                    try:
                        self._set(o, attr, value)
                    except ValueError, ve:
                        return None
                return o
            return filter(lambda x: x is not None, [apply(row) for row in cur])

    def get(self, class_, **kwargs):
        result = self.load(class_, **kwargs)
        if result:
            return result[0]
        else:
            return None

if __name__ == '__main__':
    class Person(object):
        __slots__ = {'username': str, 'id': int}

        def __init__(self, username, id):
            self.username = username
            self.id = id

        def __repr__(self):
            return '<Person "%s" (%d)>' % (self.username, self.id)

    m = Store()
    m.save(Person('User %d' % x, x*20) for x in range(50))

    p = m.get(Person, id=200)
    print p
    m.remove(p)
    p = m.get(Person, id=200)

    # Remove some persons again (deletion by value!)
    m.remove(Person('User %d' % x, x*20) for x in range(40))

    class Person(object):
        __slots__ = {'username': str, 'id': int, 'mail': str}

        def __init__(self, username, id, mail):
            self.username = username
            self.id = id
            self.mail = mail

        def __repr__(self):
            return '<Person "%s" (%s)>' % (self.username, self.mail)

    # A schema update takes place here
    m.save(Person('User %d' % x, x*20, 'user@home.com') for x in range(50))
    print m.load(Person)


########NEW FILE########
__FILENAME__ = model
# -*- coding: utf-8 -*-
#
# gPodder - A media aggregator and podcast client
# Copyright (c) 2005-2014 Thomas Perl and the gPodder Team
# Copyright (c) 2011 Neal H. Walfield
#
# gPodder is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# gPodder is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#


#
#  gpodder.model - Core model classes for gPodder (2009-08-13)
#  Based on libpodcasts.py (thp, 2005-10-29)
#

import gpodder
from gpodder import util
from gpodder import feedcore
from gpodder import youtube
from gpodder import vimeo
from gpodder import schema
from gpodder import coverart

import logging
logger = logging.getLogger(__name__)

import os
import re
import glob
import shutil
import time
import datetime

import hashlib
import feedparser
import collections
import string

_ = gpodder.gettext


def get_payment_priority(url):
    """
    at the moment we only support flattr.com as an payment provider, so we
    sort the payment providers and prefer flattr.com ("1" is higher priority than "2")
    """
    if 'flattr.com' in url:
        return 1
    return 2

class CustomFeed(feedcore.ExceptionWithData): pass

class gPodderFetcher(feedcore.Fetcher):
    """
    This class extends the feedcore Fetcher with the gPodder User-Agent and the
    Proxy handler based on the current settings in gPodder.
    """
    custom_handlers = []

    def __init__(self):
        feedcore.Fetcher.__init__(self, gpodder.user_agent)

    def fetch_channel(self, channel):
        etag = channel.http_etag
        modified = feedparser._parse_date(channel.http_last_modified)
        # If we have a username or password, rebuild the url with them included
        # Note: using a HTTPBasicAuthHandler would be pain because we need to
        # know the realm. It can be done, but I think this method works, too
        url = channel.authenticate_url(channel.url)
        for handler in self.custom_handlers:
            custom_feed = handler.handle_url(url)
            if custom_feed is not None:
                return feedcore.Result(feedcore.CUSTOM_FEED, custom_feed)
        return self.fetch(url, etag, modified)

    def _resolve_url(self, url):
        url = youtube.get_real_channel_url(url)
        url = vimeo.get_real_channel_url(url)
        return url

    @classmethod
    def register(cls, handler):
        cls.custom_handlers.append(handler)

# The "register" method is exposed here for external usage
register_custom_handler = gPodderFetcher.register

# Our podcast model:
#
# database -> podcast -> episode -> download/playback
#  podcast.parent == db
#  podcast.children == [episode, ...]
#  episode.parent == podcast
#
# - normally: episode.children = (None, None)
# - downloading: episode.children = (DownloadTask(), None)
# - playback: episode.children = (None, PlaybackTask())


class PodcastModelObject(object):
    """
    A generic base class for our podcast model providing common helper
    and utility functions.
    """
    __slots__ = ('id', 'parent', 'children')

    @classmethod
    def create_from_dict(cls, d, *args):
        """
        Create a new object, passing "args" to the constructor
        and then updating the object with the values from "d".
        """
        o = cls(*args)

        # XXX: all(map(lambda k: hasattr(o, k), d))?
        for k, v in d.iteritems():
            setattr(o, k, v)

        return o

class PodcastEpisode(PodcastModelObject):
    """holds data for one object in a channel"""
    MAX_FILENAME_LENGTH = 200

    __slots__ = schema.EpisodeColumns

    def _deprecated(self):
        raise Exception('Property is deprecated!')

    is_played = property(fget=_deprecated, fset=_deprecated)
    is_locked = property(fget=_deprecated, fset=_deprecated)

    def has_website_link(self):
        return bool(self.link) and (self.link != self.url or \
                youtube.is_video_link(self.link))

    @classmethod
    def from_feedparser_entry(cls, entry, channel):
        episode = cls(channel)
        episode.guid = entry.get('id', '')

        # Replace multi-space and newlines with single space (Maemo bug 11173)
        episode.title = re.sub('\s+', ' ', entry.get('title', ''))
        episode.link = entry.get('link', '')
        if 'content' in entry and len(entry['content']) and \
                entry['content'][0].get('type', '') == 'text/html':
            episode.description = entry['content'][0].value
        else:
            episode.description = entry.get('summary', '')

        # Fallback to subtitle if summary is not available
        if not episode.description:
            episode.description = entry.get('subtitle', '')

        try:
            total_time = 0

            # Parse iTunes-specific podcast duration metadata
            itunes_duration = entry.get('itunes_duration', '')
            if itunes_duration:
                total_time = util.parse_time(itunes_duration)

            # Parse time from YouTube descriptions if it's a YouTube feed
            if youtube.is_youtube_guid(episode.guid):
                result = re.search(r'Time:<[^>]*>\n<[^>]*>([:0-9]*)<',
                        episode.description)
                if result:
                    youtube_duration = result.group(1)
                    total_time = util.parse_time(youtube_duration)

            episode.total_time = total_time
        except:
            pass

        episode.published = feedcore.get_pubdate(entry)

        enclosures = entry.get('enclosures', [])
        media_rss_content = entry.get('media_content', [])
        audio_available = any(e.get('type', '').startswith('audio/') \
                for e in enclosures + media_rss_content)
        video_available = any(e.get('type', '').startswith('video/') \
                for e in enclosures + media_rss_content)

        # XXX: Make it possible for hooks/extensions to override this by
        # giving them a list of enclosures and the "self" object (podcast)
        # and letting them sort and/or filter the list of enclosures to
        # get the desired enclosure picked by the algorithm below.
        filter_and_sort_enclosures = lambda x: x

        # read the flattr auto-url, if exists
        payment_info = [link['href'] for link in entry.get('links', [])
            if link['rel'] == 'payment']
        if payment_info:
            episode.payment_url = sorted(payment_info, key=get_payment_priority)[0]

        # Enclosures
        for e in filter_and_sort_enclosures(enclosures):
            episode.mime_type = e.get('type', 'application/octet-stream')
            if episode.mime_type == '':
                # See Maemo bug 10036
                logger.warn('Fixing empty mimetype in ugly feed')
                episode.mime_type = 'application/octet-stream'

            if '/' not in episode.mime_type:
                continue

            # Skip images in feeds if audio or video is available (bug 979)
            # This must (and does) also look in Media RSS enclosures (bug 1430)
            if episode.mime_type.startswith('image/') and \
                    (audio_available or video_available):
                continue

            # If we have audio or video available later on, skip
            # 'application/octet-stream' data types (fixes Linux Outlaws)
            if episode.mime_type == 'application/octet-stream' and \
                    (audio_available or video_available):
                continue

            episode.url = util.normalize_feed_url(e.get('href', ''))
            if not episode.url:
                continue

            try:
                episode.file_size = int(e.length) or -1
            except:
                episode.file_size = -1

            return episode

        # Media RSS content
        for m in filter_and_sort_enclosures(media_rss_content):
            episode.mime_type = m.get('type', 'application/octet-stream')
            if '/' not in episode.mime_type:
                continue

            # Skip images in Media RSS if we have audio/video (bug 1444)
            if episode.mime_type.startswith('image/') and \
                    (audio_available or video_available):
                continue

            episode.url = util.normalize_feed_url(m.get('url', ''))
            if not episode.url:
                continue

            try:
                episode.file_size = int(m.get('filesize', 0)) or -1
            except:
                episode.file_size = -1

            try:
                episode.total_time = int(m.get('duration', 0)) or 0
            except:
                episode.total_time = 0

            return episode

        # Brute-force detection of any links
        for l in entry.get('links', ()):
            episode.url = util.normalize_feed_url(l.get('href', ''))
            if not episode.url:
                continue

            if (youtube.is_video_link(episode.url) or \
                    vimeo.is_video_link(episode.url)):
                return episode

            # Check if we can resolve this link to a audio/video file
            filename, extension = util.filename_from_url(episode.url)
            file_type = util.file_type_by_extension(extension)
            if file_type is None and hasattr(l, 'type'):
                extension = util.extension_from_mimetype(l.type)
                file_type = util.file_type_by_extension(extension)

            # The link points to a audio or video file - use it!
            if file_type is not None:
                return episode

        return None

    def __init__(self, channel):
        self.parent = channel
        self.podcast_id = self.parent.id
        self.children = (None, None)

        self.id = None
        self.url = ''
        self.title = ''
        self.file_size = 0
        self.mime_type = 'application/octet-stream'
        self.guid = ''
        self.description = ''
        self.link = ''
        self.published = 0
        self.download_filename = None
        self.payment_url = None

        self.state = gpodder.STATE_NORMAL
        self.is_new = True
        self.archive = channel.auto_archive_episodes

        # Time attributes
        self.total_time = 0
        self.current_position = 0
        self.current_position_updated = 0

        # Timestamp of last playback time
        self.last_playback = 0

    @property
    def channel(self):
        return self.parent

    @property
    def db(self):
        return self.parent.parent.db

    @property
    def trimmed_title(self):
        """Return the title with the common prefix trimmed"""
        # Minimum amount of leftover characters after trimming. This
        # avoids things like "Common prefix 123" to become just "123".
        # If there are LEFTOVER_MIN or less characters after trimming,
        # the original title will be returned without trimming.
        LEFTOVER_MIN = 5

        # "Podcast Name - Title" and "Podcast Name: Title" -> "Title"
        for postfix in (' - ', ': '):
            prefix = self.parent.title + postfix
            if (self.title.startswith(prefix) and
                    len(self.title)-len(prefix) > LEFTOVER_MIN):
                return self.title[len(prefix):]

        regex_patterns = [
            # "Podcast Name <number>: ..." -> "<number>: ..."
            r'^%s (\d+: .*)' % re.escape(self.parent.title),

            # "Episode <number>: ..." -> "<number>: ..."
            r'Episode (\d+:.*)',
        ]

        for pattern in regex_patterns:
            if re.match(pattern, self.title):
                title = re.sub(pattern, r'\1', self.title)
                if len(title) > LEFTOVER_MIN:
                    return title

        # "#001: Title" -> "001: Title"
        if (not self.parent._common_prefix and re.match('^#\d+: ',
            self.title) and len(self.title)-1 > LEFTOVER_MIN):
            return self.title[1:]

        if (self.parent._common_prefix is not None and
                self.title.startswith(self.parent._common_prefix) and
                len(self.title)-len(self.parent._common_prefix) > LEFTOVER_MIN):
            return self.title[len(self.parent._common_prefix):]

        return self.title

    def _set_download_task(self, download_task):
        self.children = (download_task, self.children[1])

    def _get_download_task(self):
        return self.children[0]

    download_task = property(_get_download_task, _set_download_task)

    @property
    def downloading(self):
        task = self.download_task
        if task is None:
            return False

        return task.status in (task.DOWNLOADING, task.QUEUED, task.PAUSED)

    def check_is_new(self):
        return (self.state == gpodder.STATE_NORMAL and self.is_new and
                not self.downloading)

    def save(self):
        gpodder.user_extensions.on_episode_save(self)
        self.db.save_episode(self)

    def on_downloaded(self, filename):
        self.state = gpodder.STATE_DOWNLOADED
        self.is_new = True
        self.file_size = os.path.getsize(filename)
        self.save()

    def set_state(self, state):
        self.state = state
        self.save()

    def playback_mark(self):
        self.is_new = False
        self.last_playback = int(time.time())
        gpodder.user_extensions.on_episode_playback(self)
        self.save()

    def mark(self, state=None, is_played=None, is_locked=None):
        if state is not None:
            self.state = state
        if is_played is not None:
            self.is_new = not is_played

            # "Mark as new" must "undelete" the episode
            if self.is_new and self.state == gpodder.STATE_DELETED:
                self.state = gpodder.STATE_NORMAL
        if is_locked is not None:
            self.archive = is_locked
        self.save()

    def age_in_days(self):
        return util.file_age_in_days(self.local_filename(create=False, \
                check_only=True))

    age_int_prop = property(fget=age_in_days)

    def get_age_string(self):
        return util.file_age_to_string(self.age_in_days())

    age_prop = property(fget=get_age_string)

    @property
    def description_html(self):
        # XXX: That's not a very well-informed heuristic to check
        # if the description already contains HTML. Better ideas?
        if '<' in self.description:
            return self.description

        return self.description.replace('\n', '<br>')

    def one_line_description(self):
        MAX_LINE_LENGTH = 120
        desc = util.remove_html_tags(self.description or '')
        desc = re.sub('\s+', ' ', desc).strip()
        if not desc:
            return _('No description available')
        else:
            # Decode the description to avoid gPodder bug 1277
            desc = util.convert_bytes(desc).strip()

            if len(desc) > MAX_LINE_LENGTH:
                return desc[:MAX_LINE_LENGTH] + '...'
            else:
                return desc

    def delete_from_disk(self):
        filename = self.local_filename(create=False, check_only=True)
        if filename is not None:
            gpodder.user_extensions.on_episode_delete(self, filename)
            util.delete_file(filename)

        self.set_state(gpodder.STATE_DELETED)

    def get_playback_url(self, fmt_ids=None, allow_partial=False):
        """Local (or remote) playback/streaming filename/URL

        Returns either the local filename or a streaming URL that
        can be used to playback this episode.

        Also returns the filename of a partially downloaded file
        in case partial (preview) playback is desired.
        """
        url = self.local_filename(create=False)

        if (allow_partial and url is not None and
                os.path.exists(url + '.partial')):
            return url + '.partial'

        if url is None or not os.path.exists(url):
            url = self.url
            url = youtube.get_real_download_url(url, fmt_ids)
            url = vimeo.get_real_download_url(url)

        return url

    def find_unique_file_name(self, filename, extension):
        # Remove leading and trailing whitespace + dots (to avoid hidden files)
        filename = filename.strip('.' + string.whitespace) + extension

        for name in util.generate_names(filename):
            if (not self.db.episode_filename_exists(self.podcast_id, name) or
                    self.download_filename == name):
                return name

    def local_filename(self, create, force_update=False, check_only=False,
            template=None, return_wanted_filename=False):
        """Get (and possibly generate) the local saving filename

        Pass create=True if you want this function to generate a
        new filename if none exists. You only want to do this when
        planning to create/download the file after calling this function.

        Normally, you should pass create=False. This will only
        create a filename when the file already exists from a previous
        version of gPodder (where we used md5 filenames). If the file
        does not exist (and the filename also does not exist), this
        function will return None.

        If you pass force_update=True to this function, it will try to
        find a new (better) filename and move the current file if this
        is the case. This is useful if (during the download) you get
        more information about the file, e.g. the mimetype and you want
        to include this information in the file name generation process.

        If check_only=True is passed to this function, it will never try
        to rename the file, even if would be a good idea. Use this if you
        only want to check if a file exists.

        If "template" is specified, it should be a filename that is to
        be used as a template for generating the "real" filename.

        The generated filename is stored in the database for future access.

        If return_wanted_filename is True, the filename will not be written to
        the database, but simply returned by this function (for use by the
        "import external downloads" feature).
        """
        if self.download_filename is None and (check_only or not create):
            return None

        ext = self.extension(may_call_local_filename=False).encode('utf-8', 'ignore')

        if not check_only and (force_update or not self.download_filename):
            # Avoid and catch gPodder bug 1440 and similar situations
            if template == '':
                logger.warn('Empty template. Report this podcast URL %s',
                        self.channel.url)
                template = None

            # Try to find a new filename for the current file
            if template is not None:
                # If template is specified, trust the template's extension
                episode_filename, ext = os.path.splitext(template)
            else:
                episode_filename, _ = util.filename_from_url(self.url)
            fn_template = util.sanitize_filename(episode_filename, self.MAX_FILENAME_LENGTH)

            if 'redirect' in fn_template and template is None:
                # This looks like a redirection URL - force URL resolving!
                logger.warn('Looks like a redirection to me: %s', self.url)
                url = util.get_real_url(self.channel.authenticate_url(self.url))
                logger.info('Redirection resolved to: %s', url)
                episode_filename, _ = util.filename_from_url(url)
                fn_template = util.sanitize_filename(episode_filename, self.MAX_FILENAME_LENGTH)

            # Use title for YouTube, Vimeo and Soundcloud downloads
            if (youtube.is_video_link(self.url) or
                    vimeo.is_video_link(self.url) or
                    fn_template == 'stream'):
                sanitized = util.sanitize_filename(self.title, self.MAX_FILENAME_LENGTH)
                if sanitized:
                    fn_template = sanitized

            # If the basename is empty, use the md5 hexdigest of the URL
            if not fn_template or fn_template.startswith('redirect.'):
                logger.error('Report this feed: Podcast %s, episode %s',
                        self.channel.url, self.url)
                fn_template = hashlib.md5(self.url).hexdigest()

            # Find a unique filename for this episode
            wanted_filename = self.find_unique_file_name(fn_template, ext)

            if return_wanted_filename:
                # return the calculated filename without updating the database
                return wanted_filename

            # The old file exists, but we have decided to want a different filename
            if self.download_filename and wanted_filename != self.download_filename:
                # there might be an old download folder crawling around - move it!
                new_file_name = os.path.join(self.channel.save_dir, wanted_filename)
                old_file_name = os.path.join(self.channel.save_dir, self.download_filename)
                if os.path.exists(old_file_name) and not os.path.exists(new_file_name):
                    logger.info('Renaming %s => %s', old_file_name, new_file_name)
                    os.rename(old_file_name, new_file_name)
                elif force_update and not os.path.exists(old_file_name):
                    # When we call force_update, the file might not yet exist when we
                    # call it from the downloading code before saving the file
                    logger.info('Choosing new filename: %s', new_file_name)
                else:
                    logger.warn('%s exists or %s does not', new_file_name, old_file_name)
                logger.info('Updating filename of %s to "%s".', self.url, wanted_filename)
            elif self.download_filename is None:
                logger.info('Setting download filename: %s', wanted_filename)
            self.download_filename = wanted_filename
            self.save()

        return os.path.join(util.sanitize_encoding(self.channel.save_dir),
                util.sanitize_encoding(self.download_filename))

    def extension(self, may_call_local_filename=True):
        filename, ext = util.filename_from_url(self.url)
        if may_call_local_filename:
            filename = self.local_filename(create=False)
            if filename is not None:
                filename, ext = os.path.splitext(filename)
        # if we can't detect the extension from the url fallback on the mimetype
        if ext == '' or util.file_type_by_extension(ext) is None:
            ext = util.extension_from_mimetype(self.mime_type)
        return ext

    def mark_new(self):
        self.is_new = True
        self.save()

    def mark_old(self):
        self.is_new = False
        self.save()

    def file_exists(self):
        filename = self.local_filename(create=False, check_only=True)
        if filename is None:
            return False
        else:
            return os.path.exists(filename)

    def was_downloaded(self, and_exists=False):
        if self.state != gpodder.STATE_DOWNLOADED:
            return False
        if and_exists and not self.file_exists():
            return False
        return True

    def sync_filename(self, use_custom=False, custom_format=None):
        if use_custom:
            return util.object_string_formatter(custom_format,
                    episode=self, podcast=self.channel)
        else:
            return self.title

    def file_type(self):
        # Assume all YouTube/Vimeo links are video files
        if youtube.is_video_link(self.url) or vimeo.is_video_link(self.url):
            return 'video'

        return util.file_type_by_extension(self.extension())

    @property
    def basename( self):
        return os.path.splitext( os.path.basename( self.url))[0]

    @property
    def pubtime(self):
        """
        Returns published time as HHMM (or 0000 if not available)
        """
        try:
            return datetime.datetime.fromtimestamp(self.published).strftime('%H%M')
        except:
            logger.warn('Cannot format pubtime: %s', self.title, exc_info=True)
            return '0000'

    def playlist_title(self):
        """Return a title for this episode in a playlist

        The title will be composed of the podcast name, the
        episode name and the publication date. The return
        value is the canonical representation of this episode
        in playlists (for example, M3U playlists).
        """
        return '%s - %s (%s)' % (self.channel.title, \
                self.title, \
                self.cute_pubdate())

    def cute_pubdate(self):
        result = util.format_date(self.published)
        if result is None:
            return '(%s)' % _('unknown')
        else:
            return result

    pubdate_prop = property(fget=cute_pubdate)

    def published_datetime(self):
        return datetime.datetime.fromtimestamp(self.published)

    @property
    def sortdate(self):
        return self.published_datetime().strftime('%Y-%m-%d')

    @property
    def pubdate_day(self):
        return self.published_datetime().strftime('%d')

    @property
    def pubdate_month(self):
        return self.published_datetime().strftime('%m')

    @property
    def pubdate_year(self):
        return self.published_datetime().strftime('%y')

    def is_finished(self):
        """Return True if this episode is considered "finished playing"

        An episode is considered "finished" when there is a
        current position mark on the track, and when the
        current position is greater than 99 percent of the
        total time or inside the last 10 seconds of a track.
        """
        return self.current_position > 0 and self.total_time > 0 and \
                (self.current_position + 10 >= self.total_time or \
                 self.current_position >= self.total_time*.99)

    def get_play_info_string(self, duration_only=False):
        duration = util.format_time(self.total_time)
        if duration_only and self.total_time > 0:
            return duration
        elif self.is_finished():
            return '%s (%s)' % (_('Finished'), duration)
        elif self.current_position > 0 and \
                self.current_position != self.total_time:
            position = util.format_time(self.current_position)
            return '%s / %s' % (position, duration)
        elif self.total_time > 0:
            return duration
        else:
            return '-'

    def update_from(self, episode):
        for k in ('title', 'url', 'description', 'link', 'published', 'guid', 'file_size', 'payment_url'):
            setattr(self, k, getattr(episode, k))


class PodcastChannel(PodcastModelObject):
    __slots__ = schema.PodcastColumns + ('_common_prefix',)

    UNICODE_TRANSLATE = {ord(u'ö'): u'o', ord(u'ä'): u'a', ord(u'ü'): u'u'}

    # Enumerations for download strategy
    STRATEGY_DEFAULT, STRATEGY_LATEST = range(2)

    # Description and ordering of strategies
    STRATEGIES = [
        (STRATEGY_DEFAULT, _('Default')),
        (STRATEGY_LATEST, _('Only keep latest')),
    ]

    MAX_FOLDERNAME_LENGTH = 60
    SECONDS_PER_WEEK = 7*24*60*60
    EpisodeClass = PodcastEpisode

    feed_fetcher = gPodderFetcher()

    def __init__(self, model, id=None):
        self.parent = model
        self.children = []

        self.id = id
        self.url = None
        self.title = ''
        self.link = ''
        self.description = ''
        self.cover_url = None
        self.payment_url = None

        self.auth_username = ''
        self.auth_password = ''

        self.http_last_modified = None
        self.http_etag = None

        self.auto_archive_episodes = False
        self.download_folder = None
        self.pause_subscription = False
        self.sync_to_mp3_player = True

        self.section = _('Other')
        self._common_prefix = None
        self.download_strategy = PodcastChannel.STRATEGY_DEFAULT

        if self.id:
            self.children = self.db.load_episodes(self, self.episode_factory)
            self._determine_common_prefix()

    @property
    def model(self):
        return self.parent

    @property
    def db(self):
        return self.parent.db

    def get_download_strategies(self):
        for value, caption in PodcastChannel.STRATEGIES:
            yield self.download_strategy == value, value, caption

    def set_download_strategy(self, download_strategy):
        if download_strategy == self.download_strategy:
            return

        caption = dict(self.STRATEGIES).get(download_strategy)
        if caption is not None:
            logger.debug('Strategy for %s changed to %s', self.title, caption)
            self.download_strategy = download_strategy
        else:
            logger.warn('Cannot set strategy to %d', download_strategy)

    def rewrite_url(self, new_url):
        new_url = util.normalize_feed_url(new_url)
        if new_url is None:
            return None

        self.url = new_url
        self.http_etag = None
        self.http_last_modified = None
        self.save()
        return new_url

    def check_download_folder(self):
        """Check the download folder for externally-downloaded files

        This will try to assign downloaded files with episodes in the
        database.

        This will also cause missing files to be marked as deleted.
        """
        known_files = set()

        for episode in self.get_episodes(gpodder.STATE_DOWNLOADED):
            if episode.was_downloaded():
                filename = episode.local_filename(create=False)
                if filename is None:
                    # No filename has been determined for this episode
                    continue

                if not os.path.exists(filename):
                    # File has been deleted by the user - simulate a
                    # delete event (also marks the episode as deleted)
                    logger.debug('Episode deleted: %s', filename)
                    episode.delete_from_disk()
                    continue

                known_files.add(filename)

        existing_files = set(filename for filename in \
                glob.glob(os.path.join(self.save_dir, '*')) \
                if not filename.endswith('.partial'))

        ignore_files = ['folder'+ext for ext in
                coverart.CoverDownloader.EXTENSIONS]

        external_files = existing_files.difference(list(known_files) +
                [os.path.join(self.save_dir, ignore_file)
                 for ignore_file in ignore_files])
        if not external_files:
            return

        all_episodes = self.get_all_episodes()

        for filename in external_files:
            found = False

            basename = os.path.basename(filename)
            existing = [e for e in all_episodes if e.download_filename == basename]
            if existing:
                existing = existing[0]
                logger.info('Importing external download: %s', filename)
                existing.on_downloaded(filename)
                continue

            for episode in all_episodes:
                wanted_filename = episode.local_filename(create=True, \
                        return_wanted_filename=True)
                if basename == wanted_filename:
                    logger.info('Importing external download: %s', filename)
                    episode.download_filename = basename
                    episode.on_downloaded(filename)
                    found = True
                    break

                wanted_base, wanted_ext = os.path.splitext(wanted_filename)
                target_base, target_ext = os.path.splitext(basename)
                if wanted_base == target_base:
                    # Filenames only differ by the extension
                    wanted_type = util.file_type_by_extension(wanted_ext)
                    target_type = util.file_type_by_extension(target_ext)

                    # If wanted type is None, assume that we don't know
                    # the right extension before the download (e.g. YouTube)
                    # if the wanted type is the same as the target type,
                    # assume that it's the correct file
                    if wanted_type is None or wanted_type == target_type:
                        logger.info('Importing external download: %s', filename)
                        episode.download_filename = basename
                        episode.on_downloaded(filename)
                        found = True
                        break

            if not found and not util.is_system_file(filename):
                logger.warn('Unknown external file: %s', filename)

    @classmethod
    def sort_key(cls, podcast):
        key = util.convert_bytes(podcast.title.lower())
        return re.sub('^the ', '', key).translate(cls.UNICODE_TRANSLATE)

    @classmethod
    def load(cls, model, url, create=True, authentication_tokens=None,\
            max_episodes=0):
        if isinstance(url, unicode):
            url = url.encode('utf-8')

        existing = filter(lambda p: p.url == url, model.get_podcasts())

        if existing:
            return existing[0]

        if create:
            tmp = cls(model)
            tmp.url = url
            if authentication_tokens is not None:
                tmp.auth_username = authentication_tokens[0]
                tmp.auth_password = authentication_tokens[1]

            # Save podcast, so it gets an ID assigned before
            # updating the feed and adding saving episodes
            tmp.save()

            try:
                tmp.update(max_episodes)
            except Exception, e:
                logger.debug('Fetch failed. Removing buggy feed.')
                tmp.remove_downloaded()
                tmp.delete()
                raise

            # Determine the section in which this podcast should appear
            tmp.section = tmp._get_content_type()

            # Determine a new download folder now that we have the title
            tmp.get_save_dir(force_new=True)

            # Mark episodes as downloaded if files already exist (bug 902)
            tmp.check_download_folder()

            # Determine common prefix of episode titles
            tmp._determine_common_prefix()

            tmp.save()

            gpodder.user_extensions.on_podcast_subscribe(tmp)

            return tmp

    def episode_factory(self, d):
        """
        This function takes a dictionary containing key-value pairs for
        episodes and returns a new PodcastEpisode object that is connected
        to this object.

        Returns: A new PodcastEpisode object
        """
        return self.EpisodeClass.create_from_dict(d, self)

    def _consume_updated_title(self, new_title):
        # Replace multi-space and newlines with single space (Maemo bug 11173)
        new_title = re.sub('\s+', ' ', new_title).strip()

        # Only update the podcast-supplied title when we
        # don't yet have a title, or if the title is the
        # feed URL (e.g. we didn't find a title before).
        if not self.title or self.title == self.url:
            self.title = new_title

            # Start YouTube- and Vimeo-specific title FIX
            YOUTUBE_PREFIX = 'Uploads by '
            VIMEO_PREFIX = 'Vimeo / '
            if self.title.startswith(YOUTUBE_PREFIX):
                self.title = self.title[len(YOUTUBE_PREFIX):] + ' on YouTube'
            elif self.title.startswith(VIMEO_PREFIX):
                self.title = self.title[len(VIMEO_PREFIX):] + ' on Vimeo'
            # End YouTube- and Vimeo-specific title FIX

    def _consume_metadata(self, title, link, description, cover_url,
            payment_url):
        self._consume_updated_title(title)
        self.link = link
        self.description = description
        self.cover_url = cover_url
        self.payment_url = payment_url
        self.save()

    def _consume_custom_feed(self, custom_feed, max_episodes=0):
        self._consume_metadata(custom_feed.get_title(),
                custom_feed.get_link(),
                custom_feed.get_description(),
                custom_feed.get_image(),
                None)

        existing = self.get_all_episodes()
        existing_guids = [episode.guid for episode in existing]

        # Insert newly-found episodes into the database + local cache
        new_episodes, seen_guids = custom_feed.get_new_episodes(self, existing_guids)
        self.children.extend(new_episodes)

        self.remove_unreachable_episodes(existing, seen_guids, max_episodes)

    def _consume_updated_feed(self, feed, max_episodes=0):
        # Cover art URL
        if hasattr(feed.feed, 'image'):
            for attribute in ('href', 'url'):
                new_value = getattr(feed.feed.image, attribute, None)
                if new_value is not None:
                    cover_url = new_value
        elif hasattr(feed.feed, 'icon'):
            cover_url = feed.feed.icon
        else:
            cover_url = None

        # Payment URL (Flattr auto-payment) information
        payment_info = [link['href'] for link in feed.feed.get('links', [])
            if link['rel'] == 'payment']
        if payment_info:
            payment_url = sorted(payment_info, key=get_payment_priority)[0]
        else:
            payment_url = None

        self._consume_metadata(feed.feed.get('title', self.url),
                feed.feed.get('link', self.link),
                feed.feed.get('subtitle', self.description),
                cover_url,
                payment_url)

        # Load all episodes to update them properly.
        existing = self.get_all_episodes()

        # We have to sort the entries in descending chronological order,
        # because if the feed lists items in ascending order and has >
        # max_episodes old episodes, new episodes will not be shown.
        # See also: gPodder Bug 1186
        entries = sorted(feed.entries, key=feedcore.get_pubdate, reverse=True)

        # We can limit the maximum number of entries that gPodder will parse
        if max_episodes > 0 and len(entries) > max_episodes:
            entries = entries[:max_episodes]

        # GUID-based existing episode list
        existing_guids = dict((e.guid, e) for e in existing)

        # Get most recent published of all episodes
        last_published = self.db.get_last_published(self) or 0

        # Keep track of episode GUIDs currently seen in the feed
        seen_guids = set()

        # Number of new episodes found
        new_episodes = 0

        # Search all entries for new episodes
        for entry in entries:
            episode = self.EpisodeClass.from_feedparser_entry(entry, self)
            if episode is not None:
                if not episode.title:
                    logger.warn('Using filename as title for %s', episode.url)
                    basename = os.path.basename(episode.url)
                    episode.title, ext = os.path.splitext(basename)

                # Maemo bug 12073
                if not episode.guid:
                    logger.warn('Using download URL as GUID for %s', episode.title)
                    episode.guid = episode.url

                seen_guids.add(episode.guid)
            else:
                continue

            # Detect (and update) existing episode based on GUIDs
            existing_episode = existing_guids.get(episode.guid, None)
            if existing_episode:
                existing_episode.update_from(episode)
                existing_episode.save()
                continue

            # Workaround for bug 340: If the episode has been
            # published earlier than one week before the most
            # recent existing episode, do not mark it as new.
            if episode.published < last_published - self.SECONDS_PER_WEEK:
                logger.debug('Episode with old date: %s', episode.title)
                episode.is_new = False

            if episode.is_new:
                new_episodes += 1

            # Only allow a certain number of new episodes per update
            if (self.download_strategy == PodcastChannel.STRATEGY_LATEST and
                    new_episodes > 1):
                episode.is_new = False

            episode.save()
            self.children.append(episode)

        self.remove_unreachable_episodes(existing, seen_guids, max_episodes)

    def remove_unreachable_episodes(self, existing, seen_guids, max_episodes):
        # Remove "unreachable" episodes - episodes that have not been
        # downloaded and that the feed does not list as downloadable anymore
        # Keep episodes that are currently being downloaded, though (bug 1534)
        if self.id is not None:
            episodes_to_purge = (e for e in existing if
                    e.state != gpodder.STATE_DOWNLOADED and
                    e.guid not in seen_guids and not e.downloading)

            for episode in episodes_to_purge:
                logger.debug('Episode removed from feed: %s (%s)',
                        episode.title, episode.guid)
                gpodder.user_extensions.on_episode_removed_from_podcast(episode)
                self.db.delete_episode_by_guid(episode.guid, self.id)

                # Remove the episode from the "children" episodes list
                if self.children is not None:
                    self.children.remove(episode)

        # This *might* cause episodes to be skipped if there were more than
        # max_episodes_per_feed items added to the feed between updates.
        # The benefit is that it prevents old episodes from apearing as new
        # in certain situations (see bug #340).
        self.db.purge(max_episodes, self.id) # TODO: Remove from self.children!

        # Sort episodes by pubdate, descending
        self.children.sort(key=lambda e: e.published, reverse=True)

    def update(self, max_episodes=0):
        try:
            result = self.feed_fetcher.fetch_channel(self)

            if result.status == feedcore.CUSTOM_FEED:
                self._consume_custom_feed(result.feed, max_episodes)
            elif result.status == feedcore.UPDATED_FEED:
                self._consume_updated_feed(result.feed, max_episodes)
            elif result.status == feedcore.NEW_LOCATION:
                url = result.feed.href
                logger.info('New feed location: %s => %s', self.url, url)
                if url in set(x.url for x in self.model.get_podcasts()):
                    raise Exception('Already subscribed to ' + url)
                self.url = url
                self._consume_updated_feed(result.feed, max_episodes)
            elif result.status == feedcore.NOT_MODIFIED:
                pass

            if hasattr(result.feed, 'headers'):
                self.http_etag = result.feed.headers.get('etag', self.http_etag)
                self.http_last_modified = result.feed.headers.get('last-modified', self.http_last_modified)
            self.save()
        except Exception, e:
            # "Not really" errors
            #feedcore.AuthenticationRequired
            # Temporary errors
            #feedcore.Offline
            #feedcore.BadRequest
            #feedcore.InternalServerError
            #feedcore.WifiLogin
            # Permanent errors
            #feedcore.Unsubscribe
            #feedcore.NotFound
            #feedcore.InvalidFeed
            #feedcore.UnknownStatusCode
            gpodder.user_extensions.on_podcast_update_failed(self, e)
            raise

        gpodder.user_extensions.on_podcast_updated(self)

        # Re-determine the common prefix for all episodes
        self._determine_common_prefix()

        self.db.commit()

    def delete(self):
        self.db.delete_podcast(self)
        self.model._remove_podcast(self)

    def save(self):
        if self.download_folder is None:
            self.get_save_dir()

        gpodder.user_extensions.on_podcast_save(self)

        self.db.save_podcast(self)
        self.model._append_podcast(self)

    def get_statistics(self):
        if self.id is None:
            return (0, 0, 0, 0, 0)
        else:
            return self.db.get_podcast_statistics(self.id)

    @property
    def group_by(self):
        if not self.section:
            self.section = self._get_content_type()
            self.save()

        return self.section

    def _get_content_type(self):
        if 'youtube.com' in self.url or 'vimeo.com' in self.url:
            return _('Video')

        audio, video, other = 0, 0, 0
        for content_type in self.db.get_content_types(self.id):
            content_type = content_type.lower()
            if content_type.startswith('audio'):
                audio += 1
            elif content_type.startswith('video'):
                video += 1
            else:
                other += 1

        if audio >= video:
            return _('Audio')
        elif video > other:
            return _('Video')

        return _('Other')

    def authenticate_url(self, url):
        return util.url_add_authentication(url, self.auth_username, self.auth_password)

    def rename(self, new_title):
        new_title = new_title.strip()
        if self.title == new_title:
            return

        new_folder_name = self.find_unique_folder_name(new_title)
        if new_folder_name and new_folder_name != self.download_folder:
            new_folder = os.path.join(gpodder.downloads, new_folder_name)
            old_folder = os.path.join(gpodder.downloads, self.download_folder)
            if os.path.exists(old_folder):
                if not os.path.exists(new_folder):
                    # Old folder exists, new folder does not -> simply rename
                    logger.info('Renaming %s => %s', old_folder, new_folder)
                    os.rename(old_folder, new_folder)
                else:
                    # Both folders exist -> move files and delete old folder
                    logger.info('Moving files from %s to %s', old_folder,
                            new_folder)
                    for file in glob.glob(os.path.join(old_folder, '*')):
                        shutil.move(file, new_folder)
                    logger.info('Removing %s', old_folder)
                    shutil.rmtree(old_folder, ignore_errors=True)
            self.download_folder = new_folder_name

        self.title = new_title
        self.save()

    def _determine_common_prefix(self):
        # We need at least 2 episodes for the prefix to be "common" ;)
        if len(self.children) < 2:
            self._common_prefix = ''
            return

        prefix = os.path.commonprefix([x.title for x in self.children])
        # The common prefix must end with a space - otherwise it's not
        # on a word boundary, and we might end up chopping off too much
        if prefix and prefix[-1] != ' ':
            prefix = prefix[:prefix.rfind(' ')+1]

        self._common_prefix = prefix

    def get_all_episodes(self):
        return self.children

    def get_episodes(self, state):
        return filter(lambda e: e.state == state, self.get_all_episodes())

    def find_unique_folder_name(self, download_folder):
        # Remove trailing dots to avoid errors on Windows (bug 600)
        # Also remove leading dots to avoid hidden folders on Linux
        download_folder = download_folder.strip('.' + string.whitespace)

        for folder_name in util.generate_names(download_folder):
            if (not self.db.podcast_download_folder_exists(folder_name) or
                    self.download_folder == folder_name):
                return folder_name

    def get_save_dir(self, force_new=False):
        if self.download_folder is None or force_new:
            # we must change the folder name, because it has not been set manually
            fn_template = util.sanitize_filename(self.title, self.MAX_FOLDERNAME_LENGTH)

            if not fn_template:
                fn_template = util.sanitize_filename(self.url, self.MAX_FOLDERNAME_LENGTH)

            # Find a unique folder name for this podcast
            download_folder = self.find_unique_folder_name(fn_template)

            # Try removing the download folder if it has been created previously
            if self.download_folder is not None:
                folder = os.path.join(gpodder.downloads, self.download_folder)
                try:
                    os.rmdir(folder)
                except OSError:
                    logger.info('Old download folder is kept for %s', self.url)

            logger.info('Updating download_folder of %s to %s', self.url,
                    download_folder)
            self.download_folder = download_folder
            self.save()

        save_dir = os.path.join(gpodder.downloads, self.download_folder)

        # Avoid encoding errors for OS-specific functions (bug 1570)
        save_dir = util.sanitize_encoding(save_dir)

        # Create save_dir if it does not yet exist
        if not util.make_directory(save_dir):
            logger.error('Could not create save_dir: %s', save_dir)

        return save_dir

    save_dir = property(fget=get_save_dir)

    def remove_downloaded(self):
        # Remove the download directory
        for episode in self.get_episodes(gpodder.STATE_DOWNLOADED):
            filename = episode.local_filename(create=False, check_only=True)
            if filename is not None:
                gpodder.user_extensions.on_episode_delete(episode, filename)

        shutil.rmtree(self.save_dir, True)

    @property
    def cover_file(self):
        return os.path.join(self.save_dir, 'folder')


class Model(object):
    PodcastClass = PodcastChannel

    def __init__(self, db):
        self.db = db
        self.children = None

    def _append_podcast(self, podcast):
        if podcast not in self.children:
            self.children.append(podcast)

    def _remove_podcast(self, podcast):
        self.children.remove(podcast)
        gpodder.user_extensions.on_podcast_delete(self)

    def get_podcasts(self):
        def podcast_factory(dct, db):
            return self.PodcastClass.create_from_dict(dct, self, dct['id'])

        if self.children is None:
            self.children = self.db.load_podcasts(podcast_factory)

            # Check download folders for changes (bug 902)
            for podcast in self.children:
                podcast.check_download_folder()

        return self.children

    def load_podcast(self, url, create=True, authentication_tokens=None,
                     max_episodes=0):
        assert all(url != podcast.url for podcast in self.get_podcasts())
        return self.PodcastClass.load(self, url, create,
                                      authentication_tokens,
                                      max_episodes)

    @classmethod
    def podcast_sort_key(cls, podcast):
        return cls.PodcastClass.sort_key(podcast)

    @classmethod
    def episode_sort_key(cls, episode):
        return episode.published

    @classmethod
    def sort_episodes_by_pubdate(cls, episodes, reverse=False):
        """Sort a list of PodcastEpisode objects chronologically

        Returns a iterable, sorted sequence of the episodes
        """
        return sorted(episodes, key=cls.episode_sort_key, reverse=reverse)


########NEW FILE########
__FILENAME__ = my
#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# gPodder - A media aggregator and podcast client
# Copyright (c) 2005-2014 Thomas Perl and the gPodder Team
#
# gPodder is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# gPodder is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#


#
#  my.py -- mygpo Client Abstraction for gPodder
#  Thomas Perl <thp@gpodder.org>; 2010-01-19
#

import gpodder
_ = gpodder.gettext

import atexit
import datetime
import calendar
import os
import sys
import time

import logging
logger = logging.getLogger(__name__)

from gpodder import util
from gpodder import minidb

# Append gPodder's user agent to mygpoclient's user agent
import mygpoclient
mygpoclient.user_agent += ' ' + gpodder.user_agent

# 2013-02-08: We should update this to 1.7 once we use the new features
MYGPOCLIENT_REQUIRED = '1.4'

if not hasattr(mygpoclient, 'require_version') or \
        not mygpoclient.require_version(MYGPOCLIENT_REQUIRED):
    print >>sys.stderr, """
    Please upgrade your mygpoclient library.
    See http://thp.io/2010/mygpoclient/

    Required version:  %s
    Installed version: %s
    """ % (MYGPOCLIENT_REQUIRED, mygpoclient.__version__)
    sys.exit(1)

try:
    from mygpoclient.simple import MissingCredentials

except ImportError:
    # if MissingCredentials does not yet exist in the installed version of
    # mygpoclient, we use an object that can never be raised/caught
    MissingCredentials = object()


from mygpoclient import api
from mygpoclient import public

from mygpoclient import util as mygpoutil

EXAMPLES_OPML = 'http://gpodder.org/directory.opml'
TOPLIST_OPML = 'http://gpodder.org/toplist.opml'
EPISODE_ACTIONS_BATCH_SIZE=100

# Database model classes
class SinceValue(object):
    __slots__ = {'host': str, 'device_id': str, 'category': int, 'since': int}

    # Possible values for the "category" field
    PODCASTS, EPISODES = range(2)

    def __init__(self, host, device_id, category, since=0):
        self.host = host
        self.device_id = device_id
        self.category = category
        self.since = since

class SubscribeAction(object):
    __slots__ = {'action_type': int, 'url': str}

    # Possible values for the "action_type" field
    ADD, REMOVE = range(2)

    def __init__(self, action_type, url):
        self.action_type = action_type
        self.url = url

    @property
    def is_add(self):
        return self.action_type == self.ADD

    @property
    def is_remove(self):
        return self.action_type == self.REMOVE

    @classmethod
    def add(cls, url):
        return cls(cls.ADD, url)

    @classmethod
    def remove(cls, url):
        return cls(cls.REMOVE, url)

    @classmethod
    def undo(cls, action):
        if action.is_add:
            return cls(cls.REMOVE, action.url)
        elif action.is_remove:
            return cls(cls.ADD, action.url)

        raise ValueError('Cannot undo action: %r' % action)

# New entity name for "received" actions
class ReceivedSubscribeAction(SubscribeAction): pass

class UpdateDeviceAction(object):
    __slots__ = {'device_id': str, 'caption': str, 'device_type': str}

    def __init__(self, device_id, caption, device_type):
        self.device_id = device_id
        self.caption = caption
        self.device_type = device_type

class EpisodeAction(object):
    __slots__ = {'podcast_url': str, 'episode_url': str, 'device_id': str,
                 'action': str, 'timestamp': int,
                 'started': int, 'position': int, 'total': int}

    def __init__(self, podcast_url, episode_url, device_id, \
            action, timestamp, started, position, total):
        self.podcast_url = podcast_url
        self.episode_url = episode_url
        self.device_id = device_id
        self.action = action
        self.timestamp = timestamp
        self.started = started
        self.position = position
        self.total = total

# New entity name for "received" actions
class ReceivedEpisodeAction(EpisodeAction): pass

class RewrittenUrl(object):
    __slots__ = {'old_url': str, 'new_url': str}

    def __init__(self, old_url, new_url):
        self.old_url = old_url
        self.new_url = new_url
# End Database model classes



# Helper class for displaying changes in the UI
class Change(object):
    def __init__(self, action, podcast=None):
        self.action = action
        self.podcast = podcast

    @property
    def description(self):
        if self.action.is_add:
            return _('Add %s') % self.action.url
        else:
            return _('Remove %s') % self.podcast.title


class MygPoClient(object):
    STORE_FILE = 'gpodder.net'
    FLUSH_TIMEOUT = 60
    FLUSH_RETRIES = 3

    def __init__(self, config):
        self._store = minidb.Store(os.path.join(gpodder.home, self.STORE_FILE))

        self._config = config
        self._client = None

        # Initialize the _client attribute and register with config
        self.on_config_changed()
        assert self._client is not None

        self._config.add_observer(self.on_config_changed)

        self._worker_thread = None
        atexit.register(self._at_exit)

    def create_device(self):
        """Uploads the device changes to the server

        This should be called when device settings change
        or when the mygpo client functionality is enabled.
        """
        # Remove all previous device update actions
        self._store.remove(self._store.load(UpdateDeviceAction))

        # Insert our new update action
        action = UpdateDeviceAction(self.device_id, \
                self._config.mygpo.device.caption, \
                self._config.mygpo.device.type)
        self._store.save(action)

    def get_rewritten_urls(self):
        """Returns a list of rewritten URLs for uploads

        This should be called regularly. Every object returned
        should be merged into the database, and the old_url
        should be updated to new_url in every podcdast.
        """
        rewritten_urls = self._store.load(RewrittenUrl)
        self._store.remove(rewritten_urls)
        return rewritten_urls

    def process_episode_actions(self, find_episode, on_updated=None):
        """Process received episode actions

        The parameter "find_episode" should be a function accepting
        two parameters (podcast_url and episode_url). It will be used
        to get an episode object that needs to be updated. It should
        return None if the requested episode does not exist.

        The optional callback "on_updated" should accept a single
        parameter (the episode object) and will be called whenever
        the episode data is changed in some way.
        """
        logger.debug('Processing received episode actions...')
        for action in self._store.load(ReceivedEpisodeAction):
            if action.action not in ('play', 'delete'):
                # Ignore all other action types for now
                continue

            episode = find_episode(action.podcast_url, action.episode_url)

            if episode is None:
                # The episode does not exist on this client
                continue

            if action.action == 'play':
                logger.debug('Play action for %s', episode.url)
                episode.mark(is_played=True)

                if (action.timestamp > episode.current_position_updated and
                        action.position is not None):
                    logger.debug('Updating position for %s', episode.url)
                    episode.current_position = action.position
                    episode.current_position_updated = action.timestamp

                if action.total:
                    logger.debug('Updating total time for %s', episode.url)
                    episode.total_time = action.total

                episode.save()
                if on_updated is not None:
                    on_updated(episode)
            elif action.action == 'delete':
                if not episode.was_downloaded(and_exists=True):
                    # Set the episode to a "deleted" state
                    logger.debug('Marking as deleted: %s', episode.url)
                    episode.delete_from_disk()
                    episode.save()
                    if on_updated is not None:
                        on_updated(episode)

        # Remove all received episode actions
        self._store.delete(ReceivedEpisodeAction)
        self._store.commit()
        logger.debug('Received episode actions processed.')

    def get_received_actions(self):
        """Returns a list of ReceivedSubscribeAction objects

        The list might be empty. All these actions have to
        be processed. The user should confirm which of these
        actions should be taken, the reest should be rejected.

        Use confirm_received_actions and reject_received_actions
        to return and finalize the actions received by this
        method in order to not receive duplicate actions.
        """
        return self._store.load(ReceivedSubscribeAction)

    def confirm_received_actions(self, actions):
        """Confirm that a list of actions has been processed

        The UI should call this with a list of actions that
        have been accepted by the user and processed by the
        podcast backend.
        """
        # Simply remove the received actions from the queue
        self._store.remove(actions)

    def reject_received_actions(self, actions):
        """Reject (undo) a list of ReceivedSubscribeAction objects

        The UI should call this with a list of actions that
        have been rejected by the user. A reversed set of
        actions will be uploaded to the server so that the
        state on the server matches the state on the client.
        """
        # Create "undo" actions for received subscriptions
        self._store.save(SubscribeAction.undo(a) for a in actions)
        self.flush()

        # After we've handled the reverse-actions, clean up
        self._store.remove(actions)

    @property
    def host(self):
        return self._config.mygpo.server

    @property
    def device_id(self):
        return self._config.mygpo.device.uid

    def can_access_webservice(self):
        return self._config.mygpo.enabled and \
               self._config.mygpo.username and \
               self._config.mygpo.device.uid

    def set_subscriptions(self, urls):
        if self.can_access_webservice():
            logger.debug('Uploading (overwriting) subscriptions...')
            self._client.put_subscriptions(self.device_id, urls)
            logger.debug('Subscription upload done.')
        else:
            raise Exception('Webservice access not enabled')

    def _convert_played_episode(self, episode, start, end, total):
        return EpisodeAction(episode.channel.url, \
                episode.url, self.device_id, 'play', \
                int(time.time()), start, end, total)

    def _convert_episode(self, episode, action):
        return EpisodeAction(episode.channel.url, \
                episode.url, self.device_id, action, \
                int(time.time()), None, None, None)

    def on_delete(self, episodes):
        logger.debug('Storing %d episode delete actions', len(episodes))
        self._store.save(self._convert_episode(e, 'delete') for e in episodes)

    def on_download(self, episodes):
        logger.debug('Storing %d episode download actions', len(episodes))
        self._store.save(self._convert_episode(e, 'download') for e in episodes)

    def on_playback_full(self, episode, start, end, total):
        logger.debug('Storing full episode playback action')
        self._store.save(self._convert_played_episode(episode, start, end, total))

    def on_playback(self, episodes):
        logger.debug('Storing %d episode playback actions', len(episodes))
        self._store.save(self._convert_episode(e, 'play') for e in episodes)

    def on_subscribe(self, urls):
        # Cancel previously-inserted "remove" actions
        self._store.remove(SubscribeAction.remove(url) for url in urls)

        # Insert new "add" actions
        self._store.save(SubscribeAction.add(url) for url in urls)

        self.flush()

    def on_unsubscribe(self, urls):
        # Cancel previously-inserted "add" actions
        self._store.remove(SubscribeAction.add(url) for url in urls)

        # Insert new "remove" actions
        self._store.save(SubscribeAction.remove(url) for url in urls)

        self.flush()

    def _at_exit(self):
        self._worker_proc(forced=True)
        self._store.commit()
        self._store.close()

    def _worker_proc(self, forced=False):
        if not forced:
            # Store the current contents of the queue database
            self._store.commit()

            logger.debug('Worker thread waiting for timeout')
            time.sleep(self.FLUSH_TIMEOUT)

        # Only work when enabled, UID set and allowed to work
        if self.can_access_webservice() and \
                (self._worker_thread is not None or forced):
            self._worker_thread = None

            logger.debug('Worker thread starting to work...')
            for retry in range(self.FLUSH_RETRIES):
                must_retry = False

                if retry:
                    logger.debug('Retrying flush queue...')

                # Update the device first, so it can be created if new
                for action in self._store.load(UpdateDeviceAction):
                    if self.update_device(action):
                        self._store.remove(action)
                    else:
                        must_retry = True

                # Upload podcast subscription actions
                actions = self._store.load(SubscribeAction)
                if self.synchronize_subscriptions(actions):
                    self._store.remove(actions)
                else:
                    must_retry = True

                # Upload episode actions
                actions = self._store.load(EpisodeAction)
                if self.synchronize_episodes(actions):
                    self._store.remove(actions)
                else:
                    must_retry = True

                if not must_retry or not self.can_access_webservice():
                    # No more pending actions, or no longer enabled.
                    # Ready to quit.
                    break

            logger.debug('Worker thread finished.')
        else:
            logger.info('Worker thread may not execute (disabled).')

        # Store the current contents of the queue database
        self._store.commit()

    def flush(self, now=False):
        if not self.can_access_webservice():
            logger.warn('Flush requested, but sync disabled.')
            return

        if self._worker_thread is None or now:
            if now:
                logger.debug('Flushing NOW.')
            else:
                logger.debug('Flush requested.')
            self._worker_thread = util.run_in_background(lambda: self._worker_proc(now), True)
        else:
            logger.debug('Flush requested, already waiting.')

    def on_config_changed(self, name=None, old_value=None, new_value=None):
        if name in ('mygpo.username', 'mygpo.password', 'mygpo.server') \
                or self._client is None:
            self._client = api.MygPodderClient(self._config.mygpo.username,
                    self._config.mygpo.password, self._config.mygpo.server)
            logger.info('Reloading settings.')
        elif name.startswith('mygpo.device.'):
            # Update or create the device
            self.create_device()

    def synchronize_episodes(self, actions):
        logger.debug('Starting episode status sync.')

        def convert_to_api(action):
            dt = datetime.datetime.utcfromtimestamp(action.timestamp)
            action_ts = mygpoutil.datetime_to_iso8601(dt)
            return api.EpisodeAction(action.podcast_url, \
                    action.episode_url, action.action, \
                    action.device_id, action_ts, \
                    action.started, action.position, action.total)

        def convert_from_api(action):
            dt = mygpoutil.iso8601_to_datetime(action.timestamp)
            action_ts = calendar.timegm(dt.timetuple())
            return ReceivedEpisodeAction(action.podcast, \
                    action.episode, action.device, \
                    action.action, action_ts, \
                    action.started, action.position, action.total)

        try:
            # Load the "since" value from the database
            since_o = self._store.get(SinceValue, host=self.host, \
                                                  device_id=self.device_id, \
                                                  category=SinceValue.EPISODES)

            # Use a default since object for the first-time case
            if since_o is None:
                since_o = SinceValue(self.host, self.device_id, SinceValue.EPISODES)

            # Step 1: Download Episode actions
            try:
                changes = self._client.download_episode_actions(since_o.since)

                received_actions = [convert_from_api(a) for a in changes.actions]
                logger.debug('Received %d episode actions', len(received_actions))
                self._store.save(received_actions)

                # Save the "since" value for later use
                self._store.update(since_o, since=changes.since)

            except (MissingCredentials, mygpoclient.http.Unauthorized):
                # handle outside
                raise

            except Exception, e:
                logger.warn('Exception while polling for episodes.', exc_info=True)

            # Step 2: Upload Episode actions

            # Uploads are done in batches; uploading can resume if only parts
            # be uploaded; avoids empty uploads as well
            for lower in range(0, len(actions), EPISODE_ACTIONS_BATCH_SIZE):
                batch = actions[lower:lower+EPISODE_ACTIONS_BATCH_SIZE]

                # Convert actions to the mygpoclient format for uploading
                episode_actions = [convert_to_api(a) for a in batch]

                # Upload the episode actions
                self._client.upload_episode_actions(episode_actions)

                # Actions have been uploaded to the server - remove them
                self._store.remove(batch)

            logger.debug('Episode actions have been uploaded to the server.')
            return True

        except (MissingCredentials, mygpoclient.http.Unauthorized):
            logger.warn('Invalid credentials. Disabling gpodder.net.')
            self._config.mygpo.enabled = False
            return False

        except Exception, e:
            logger.error('Cannot upload episode actions: %s', str(e), exc_info=True)
            return False

    def synchronize_subscriptions(self, actions):
        logger.debug('Starting subscription sync.')
        try:
            # Load the "since" value from the database
            since_o = self._store.get(SinceValue, host=self.host, \
                                                  device_id=self.device_id, \
                                                  category=SinceValue.PODCASTS)

            # Use a default since object for the first-time case
            if since_o is None:
                since_o = SinceValue(self.host, self.device_id, SinceValue.PODCASTS)

            # Step 1: Pull updates from the server and notify the frontend
            result = self._client.pull_subscriptions(self.device_id, since_o.since)

            # Update the "since" value in the database
            self._store.update(since_o, since=result.since)

            # Store received actions for later retrieval (and in case we
            # have outdated actions in the database, simply remove them)
            for url in result.add:
                logger.debug('Received add action: %s', url)
                self._store.remove(ReceivedSubscribeAction.remove(url))
                self._store.remove(ReceivedSubscribeAction.add(url))
                self._store.save(ReceivedSubscribeAction.add(url))
            for url in result.remove:
                logger.debug('Received remove action: %s', url)
                self._store.remove(ReceivedSubscribeAction.add(url))
                self._store.remove(ReceivedSubscribeAction.remove(url))
                self._store.save(ReceivedSubscribeAction.remove(url))

            # Step 2: Push updates to the server and rewrite URLs (if any)
            actions = self._store.load(SubscribeAction)

            add = [a.url for a in actions if a.is_add]
            remove = [a.url for a in actions if a.is_remove]

            if add or remove:
                logger.debug('Uploading: +%d / -%d', len(add), len(remove))
                # Only do a push request if something has changed
                result = self._client.update_subscriptions(self.device_id, add, remove)

                # Update the "since" value in the database
                self._store.update(since_o, since=result.since)

                # Store URL rewrites for later retrieval by GUI
                for old_url, new_url in result.update_urls:
                    if new_url:
                        logger.debug('Rewritten URL: %s', new_url)
                        self._store.save(RewrittenUrl(old_url, new_url))

            # Actions have been uploaded to the server - remove them
            self._store.remove(actions)
            logger.debug('All actions have been uploaded to the server.')
            return True

        except (MissingCredentials, mygpoclient.http.Unauthorized):
            logger.warn('Invalid credentials. Disabling gpodder.net.')
            self._config.mygpo.enabled = False
            return False

        except Exception, e:
            logger.error('Cannot upload subscriptions: %s', str(e), exc_info=True)
            return False

    def update_device(self, action):
        try:
            logger.debug('Uploading device settings...')
            self._client.update_device_settings(action.device_id, \
                    action.caption, action.device_type)
            logger.debug('Device settings uploaded.')
            return True

        except (MissingCredentials, mygpoclient.http.Unauthorized):
            logger.warn('Invalid credentials. Disabling gpodder.net.')
            self._config.mygpo.enabled = False
            return False

        except Exception, e:
            logger.error('Cannot update device %s: %s', self.device_id,
                str(e), exc_info=True)
            return False

    def get_devices(self):
        result = []

        try:
            devices = self._client.get_devices()

        except (MissingCredentials, mygpoclient.http.Unauthorized):
            logger.warn('Invalid credentials. Disabling gpodder.net.')
            self._config.mygpo.enabled = False
            raise

        for d in devices:
            result.append((d.device_id, d.caption, d.type))
        return result

    def open_website(self):
        util.open_website('http://' + self._config.mygpo.server)


class Directory(object):
    def __init__(self):
        self.client = public.PublicClient()

    def toplist(self):
        return [(p.title or p.url, p.url)
                for p in self.client.get_toplist()
                if p.url]

    def search(self, query):
        return [(p.title or p.url, p.url)
                for p in self.client.search_podcasts(query)
                if p.url]


########NEW FILE########
__FILENAME__ = opml
# -*- coding: utf-8 -*-
#
# gPodder - A media aggregator and podcast client
# Copyright (c) 2005-2014 Thomas Perl and the gPodder Team
#
# gPodder is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# gPodder is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#


#
#  opml.py -- OPML import and export functionality
#  Thomas Perl <thp@perli.net>   2007-08-19
#
#  based on: libopmlreader.py (2006-06-13)
#            libopmlwriter.py (2005-12-08)
#

"""OPML import and export functionality

This module contains helper classes to import subscriptions 
from OPML files on the web and to export a list of channel 
objects to valid OPML 1.1 files that can be used to backup 
or distribute gPodder's channel subscriptions.
"""

import logging
logger = logging.getLogger(__name__)

from gpodder import util

import xml.dom.minidom

import os.path
import os
import shutil

from email.utils import formatdate
import gpodder


class Importer(object):
    """
    Helper class to import an OPML feed from protocols
    supported by urllib2 (e.g. HTTP) and return a GTK 
    ListStore that can be displayed in the GUI.

    This class should support standard OPML feeds and
    contains workarounds to support odeo.com feeds.
    """

    VALID_TYPES = ('rss', 'link')

    def __init__( self, url):
        """
        Parses the OPML feed from the given URL into 
        a local data structure containing channel metadata.
        """
        self.items = []
        try:
            if os.path.exists(url):
                doc = xml.dom.minidom.parse(url)
            else:
                doc = xml.dom.minidom.parseString(util.urlopen(url).read())

            for outline in doc.getElementsByTagName('outline'):
                # Make sure we are dealing with a valid link type (ignore case)
                otl_type = outline.getAttribute('type')
                if otl_type is None or otl_type.lower() not in self.VALID_TYPES:
                    continue

                if outline.getAttribute('xmlUrl') or outline.getAttribute('url'):
                    channel = {
                        'url': outline.getAttribute('xmlUrl') or outline.getAttribute('url'),
                        'title': outline.getAttribute('title') or outline.getAttribute('text') or outline.getAttribute('xmlUrl') or outline.getAttribute('url'),
                        'description': outline.getAttribute('text') or outline.getAttribute('xmlUrl') or outline.getAttribute('url'),
                    }

                    if channel['description'] == channel['title']:
                        channel['description'] = channel['url']

                    for attr in ( 'url', 'title', 'description' ):
                        channel[attr] = channel[attr].strip()

                    self.items.append( channel)
            if not len(self.items):
                logger.info('OPML import finished, but no items found: %s', url)
        except:
            logger.error('Cannot import OPML from URL: %s', url, exc_info=True)



class Exporter(object):
    """
    Helper class to export a list of channel objects
    to a local file in OPML 1.1 format.

    See www.opml.org for the OPML specification.
    """

    FEED_TYPE = 'rss'

    def __init__( self, filename):
        if filename is None:
            self.filename = None
        elif filename.endswith( '.opml') or filename.endswith( '.xml'):
            self.filename = filename
        else:
            self.filename = '%s.opml' % ( filename, )

    def create_node( self, doc, name, content):
        """
        Creates a simple XML Element node in a document 
        with tag name "name" and text content "content", 
        as in <name>content</name> and returns the element.
        """
        node = doc.createElement( name)
        node.appendChild( doc.createTextNode( content))
        return node

    def create_outline( self, doc, channel):
        """
        Creates a OPML outline as XML Element node in a
        document for the supplied channel.
        """
        outline = doc.createElement( 'outline')
        outline.setAttribute( 'title', channel.title)
        outline.setAttribute( 'text', channel.description)
        outline.setAttribute( 'xmlUrl', channel.url)
        outline.setAttribute( 'type', self.FEED_TYPE)
        return outline

    def write( self, channels):
        """
        Creates a XML document containing metadata for each 
        channel object in the "channels" parameter, which 
        should be a list of channel objects.

        OPML 2.0 specification: http://www.opml.org/spec2

        Returns True on success or False when there was an 
        error writing the file.
        """
        if self.filename is None:
            return False

        doc = xml.dom.minidom.Document()

        opml = doc.createElement('opml')
        opml.setAttribute('version', '2.0')
        doc.appendChild(opml)

        head = doc.createElement( 'head')
        head.appendChild( self.create_node( doc, 'title', 'gPodder subscriptions'))
        head.appendChild( self.create_node( doc, 'dateCreated', formatdate(localtime=True)))
        opml.appendChild( head)

        body = doc.createElement( 'body')
        for channel in channels:
            body.appendChild( self.create_outline( doc, channel))
        opml.appendChild( body)

        try:
            data = doc.toprettyxml(encoding='utf-8', indent='    ', newl=os.linesep)
            # We want to have at least 512 KiB free disk space after
            # saving the opml data, if this is not possible, don't 
            # try to save the new file, but keep the old one so we
            # don't end up with a clobbed, empty opml file.
            FREE_DISK_SPACE_AFTER = 1024*512
            path = os.path.dirname(self.filename) or os.path.curdir
            available = util.get_free_disk_space(path)
            if available < 2*len(data)+FREE_DISK_SPACE_AFTER:
                # On Windows, if we have zero bytes available, assume that we have
                # not had the win32file module available + assume enough free space
                if not gpodder.ui.win32 or available > 0:
                    logger.error('Not enough free disk space to save channel list to %s', self.filename)
                    return False
            fp = open(self.filename+'.tmp', 'w')
            fp.write(data)
            fp.close()
            util.atomic_rename(self.filename+'.tmp', self.filename)
        except:
            logger.error('Could not open file for writing: %s', self.filename,
                    exc_info=True)
            return False

        return True


########NEW FILE########
__FILENAME__ = player
# -*- coding: utf-8 -*-
#
# gPodder - A media aggregator and podcast client
# Copyright (c) 2005-2014 Thomas Perl and the gPodder Team
#
# gPodder is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# gPodder is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#

#
# gpodder.player - Podcatcher implementation of the Media Player D-Bus API
# Thomas Perl <thp@gpodder.org>; 2010-04-25
#
# Specification: http://gpodder.org/wiki/Media_Player_D-Bus_API
#


import gpodder
import urllib

class MediaPlayerDBusReceiver(object):
    INTERFACE = 'org.gpodder.player'
    SIGNAL_STARTED = 'PlaybackStarted'
    SIGNAL_STOPPED = 'PlaybackStopped'

    def __init__(self, on_play_event):
        self.on_play_event = on_play_event

        self.bus = gpodder.dbus_session_bus
        self.bus.add_signal_receiver(self.on_playback_started, \
                                     self.SIGNAL_STARTED, \
                                     self.INTERFACE, \
                                     None, \
                                     None)
        self.bus.add_signal_receiver(self.on_playback_stopped, \
                                     self.SIGNAL_STOPPED, \
                                     self.INTERFACE, \
                                     None, \
                                     None)

    def on_playback_started(self, position, file_uri):
        pass

    def on_playback_stopped(self, start, end, total, file_uri):
        # Assume the URI comes as quoted UTF-8 string, so decode
        # it first to utf-8 (should be no problem) for unquoting
        # to work correctly on this later on (Maemo bug 11811)
        if isinstance(file_uri, unicode):
            file_uri = file_uri.encode('utf-8')
        if file_uri.startswith('/'):
            file_uri = 'file://' + urllib.quote(file_uri)
        self.on_play_event(start, end, total, file_uri)


########NEW FILE########
__FILENAME__ = soundcloud
#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# gPodder - A media aggregator and podcast client
# Copyright (c) 2005-2014 Thomas Perl and the gPodder Team
#
# gPodder is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# gPodder is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#

# Soundcloud.com API client module for gPodder
# Thomas Perl <thp@gpodder.org>; 2009-11-03

import gpodder

_ = gpodder.gettext

from gpodder import model
from gpodder import util

try:
    # For Python < 2.6, we use the "simplejson" add-on module
    import simplejson as json
except ImportError:
    # Python 2.6 already ships with a nice "json" module
    import json

import os
import time

import re
import email


# gPodder's consumer key for the Soundcloud API
CONSUMER_KEY = 'zrweghtEtnZLpXf3mlm8mQ'


def soundcloud_parsedate(s):
    """Parse a string into a unix timestamp

    Only strings provided by Soundcloud's API are
    parsed with this function (2009/11/03 13:37:00).
    """
    m = re.match(r'(\d{4})/(\d{2})/(\d{2}) (\d{2}):(\d{2}):(\d{2})', s)
    return time.mktime([int(x) for x in m.groups()]+[0, 0, -1])

def get_param(s, param='filename', header='content-disposition'):
    """Get a parameter from a string of headers

    By default, this gets the "filename" parameter of
    the content-disposition header. This works fine
    for downloads from Soundcloud.
    """
    msg = email.message_from_string(s)
    if header in msg:
        value = msg.get_param(param, header=header)
        decoded_list = email.header.decode_header(value)
        value = []
        for part, encoding in decoded_list:
            if encoding:
                value.append(part.decode(encoding))
            else:
                value.append(unicode(part))
        return u''.join(value)

    return None

def get_metadata(url):
    """Get file download metadata

    Returns a (size, type, name) from the given download
    URL. Will use the network connection to determine the
    metadata via the HTTP header fields.
    """
    track_fp = util.urlopen(url)
    headers = track_fp.info()
    filesize = headers['content-length'] or '0'
    filetype = headers['content-type'] or 'application/octet-stream'
    headers_s = '\n'.join('%s:%s'%(k,v) for k, v in headers.items())
    filename = get_param(headers_s) or os.path.basename(os.path.dirname(url))
    track_fp.close()
    return filesize, filetype, filename


class SoundcloudUser(object):
    def __init__(self, username):
        self.username = username
        self.cache_file = os.path.join(gpodder.home, 'Soundcloud')
        if os.path.exists(self.cache_file):
            try:
                self.cache = json.load(open(self.cache_file, 'r'))
            except:
                self.cache = {}
        else:
            self.cache = {}

    def commit_cache(self):
        json.dump(self.cache, open(self.cache_file, 'w'))

    def get_coverart(self):
        global CONSUMER_KEY
        key = ':'.join((self.username, 'avatar_url'))
        if key in self.cache:
            return self.cache[key]

        image = None
        try:
            json_url = 'http://api.soundcloud.com/users/%s.json?consumer_key=%s' % (self.username, CONSUMER_KEY)
            user_info = json.load(util.urlopen(json_url))
            image = user_info.get('avatar_url', None)
            self.cache[key] = image
        finally:
            self.commit_cache()

        return image

    def get_tracks(self, feed):
        """Get a generator of tracks from a SC user

        The generator will give you a dictionary for every
        track it can find for its user."""
        global CONSUMER_KEY
        try:
            json_url = 'http://api.soundcloud.com/users/%(user)s/%(feed)s.json?filter=downloadable&consumer_key=%(consumer_key)s' \
                    % { "user":self.username, "feed":feed, "consumer_key": CONSUMER_KEY }
            tracks = (track for track in json.load(util.urlopen(json_url)) \
                    if track['downloadable'])

            for track in tracks:
                # Prefer stream URL (MP3), fallback to download URL
                url = track.get('stream_url', track['download_url']) + \
                    '?consumer_key=%(consumer_key)s' \
                    % { 'consumer_key': CONSUMER_KEY }
                if url not in self.cache:
                    try:
                        self.cache[url] = get_metadata(url)
                    except:
                        continue
                filesize, filetype, filename = self.cache[url]

                yield {
                    'title': track.get('title', track.get('permalink')) or _('Unknown track'),
                    'link': track.get('permalink_url') or 'http://soundcloud.com/'+self.username,
                    'description': track.get('description') or _('No description available'),
                    'url': url,
                    'file_size': int(filesize),
                    'mime_type': filetype,
                    'guid': track.get('permalink', track.get('id')),
                    'published': soundcloud_parsedate(track.get('created_at', None)),
                }
        finally:
            self.commit_cache()

class SoundcloudFeed(object):
    URL_REGEX = re.compile('http://([a-z]+\.)?soundcloud\.com/([^/]+)$', re.I)

    @classmethod
    def handle_url(cls, url):
        m = cls.URL_REGEX.match(url)
        if m is not None:
            subdomain, username = m.groups()
            return cls(username)

    def __init__(self, username):
        self.username = username
        self.sc_user = SoundcloudUser(username)

    def get_title(self):
        return _('%s on Soundcloud') % self.username

    def get_image(self):
        return self.sc_user.get_coverart()

    def get_link(self):
        return 'http://soundcloud.com/%s' % self.username

    def get_description(self):
        return _('Tracks published by %s on Soundcloud.') % self.username

    def get_new_episodes(self, channel, existing_guids):
        return self._get_new_episodes(channel, existing_guids, 'tracks')

    def _get_new_episodes(self, channel, existing_guids, track_type):
        tracks = [t for t in self.sc_user.get_tracks(track_type)]

        seen_guids = [track['guid'] for track in tracks]
        episodes = []

        for track in tracks:
            if track['guid'] not in existing_guids:
                episode = channel.episode_factory(track)
                episode.save()
                episodes.append(episode)

        return episodes, seen_guids

class SoundcloudFavFeed(SoundcloudFeed):
    URL_REGEX = re.compile('http://([a-z]+\.)?soundcloud\.com/([^/]+)/favorites', re.I)


    def __init__(self, username):
        super(SoundcloudFavFeed,self).__init__(username)

    def get_title(self):
        return _('%s\'s favorites on Soundcloud') % self.username

    def get_link(self):
        return 'http://soundcloud.com/%s/favorites' % self.username

    def get_description(self):
        return _('Tracks favorited by %s on Soundcloud.') % self.username

    def get_new_episodes(self, channel, existing_guids):
        return self._get_new_episodes(channel, existing_guids, 'favorites')

# Register our URL handlers
model.register_custom_handler(SoundcloudFeed)
model.register_custom_handler(SoundcloudFavFeed)

########NEW FILE########
__FILENAME__ = helper
# -*- coding: utf-8 -*-
#
# gPodder - A media aggregator and podcast client
# Copyright (c) 2005-2014 Thomas Perl and the gPodder Team
#
# gPodder is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# gPodder is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#

import gpodder

import os

from gpodder import util

from PySide import QtCore

import logging
logger = logging.getLogger(__name__)

class Action(QtCore.QObject):
    def __init__(self, caption, action, target=None):
        QtCore.QObject.__init__(self)
        self._caption = util.convert_bytes(caption)

        self.action = action
        self.target = target

    changed = QtCore.Signal()

    def _get_caption(self):
        return self._caption

    caption = QtCore.Property(unicode, _get_caption, notify=changed)


class MediaButtonsHandler(QtCore.QObject):
    def __init__(self):
        QtCore.QObject.__init__(self)

        if gpodder.ui.harmattan:
            headset_path = '/org/freedesktop/Hal/devices/computer_logicaldev_input_0'
            headset_path2 = '/org/freedesktop/Hal/devices/computer_logicaldev_input'
        else:
            return

        import dbus
        system_bus = dbus.SystemBus()
        system_bus.add_signal_receiver(self.handle_button, 'Condition',
                'org.freedesktop.Hal.Device', None, headset_path)
        if gpodder.ui.harmattan:
            system_bus.add_signal_receiver(self.handle_button, 'Condition',
                    'org.freedesktop.Hal.Device', None, headset_path2)

    def handle_button(self, signal, button):
        if signal == 'ButtonPressed':
            if button in ('play-cd', 'phone'):
                self.playPressed.emit()
            elif button == 'pause-cd':
                self.pausePressed.emit()
            elif button == 'previous-song':
                self.previousPressed.emit()
            elif button == 'next-song':
                self.nextPressed.emit()

    playPressed = QtCore.Signal()
    pausePressed = QtCore.Signal()
    previousPressed = QtCore.Signal()
    nextPressed = QtCore.Signal()

class TrackerMinerConfig(QtCore.QObject):
    FILENAME = os.path.expanduser('~/.config/tracker/tracker-miner-fs.cfg')
    SECTION = 'IgnoredDirectories'
    ENTRY = '$HOME/MyDocs/gPodder/'

    def __init__(self, filename=None):
        QtCore.QObject.__init__(self)
        self._filename = filename or TrackerMinerConfig.FILENAME
        self._index_podcasts = self.get_index_podcasts()

    @QtCore.Slot(result=bool)
    def get_index_podcasts(self):
        """
        Returns True if the gPodder directory is indexed, False otherwise
        """
        if not os.path.exists(self._filename):
            logger.warn('File does not exist: %s', self._filename)
            return False

        for line in open(self._filename, 'r'):
            if line.startswith(TrackerMinerConfig.SECTION + '='):
                return (TrackerMinerConfig.ENTRY not in line)

    @QtCore.Slot(bool, result=bool)
    def set_index_podcasts(self, index_podcasts):
        """
        If index_podcasts is True, make sure the gPodder directory is indexed
        If index_podcasts is False, ignore the gPodder directory in Tracker
        """
        if not os.path.exists(self._filename):
            logger.warn('File does not exist: %s', self._filename)
            return False

        if self._index_podcasts == index_podcasts:
            # Nothing to do
            return True

        tmp_filename = self._filename + '.gpodder.tmp'

        out = open(tmp_filename, 'w')
        for line in open(self._filename, 'r'):
            if line.startswith(TrackerMinerConfig.SECTION + '='):
                _, rest = line.rstrip('\n').split('=', 1)
                directories = filter(None, rest.split(';'))

                if index_podcasts:
                    if TrackerMinerConfig.ENTRY in directories:
                        directories.remove(TrackerMinerConfig.ENTRY)
                else:
                    if TrackerMinerConfig.ENTRY not in directories:
                        directories.append(TrackerMinerConfig.ENTRY)

                line = '%(section)s=%(value)s;\n' % {
                    'section': TrackerMinerConfig.SECTION,
                    'value': ';'.join(directories),
                }
                logger.info('Writing new config line: %s', line)

            out.write(line)
        out.close()

        os.rename(tmp_filename, self._filename)
        self._index_podcasts = index_podcasts
        return True


########NEW FILE########
__FILENAME__ = images
# -*- coding: utf-8 -*-
#
# gPodder - A media aggregator and podcast client
# Copyright (c) 2005-2014 Thomas Perl and the gPodder Team
#
# gPodder is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# gPodder is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#

from PySide.QtCore import Qt
from PySide.QtGui import QImage
from PySide.QtDeclarative import QDeclarativeImageProvider

import gpodder

from gpodder import util
from gpodder import coverart

import logging
logger = logging.getLogger(__name__)

import os
import urllib

class LocalCachedImageProvider(QDeclarativeImageProvider):
    IMAGE_TYPE = QDeclarativeImageProvider.ImageType.Image

    def __init__(self):
        QDeclarativeImageProvider.__init__(self, self.IMAGE_TYPE)
        self.downloader = coverart.CoverDownloader()
        self._cache = {}

    def requestImage(self, id, size, requestedSize):
        key = (id, requestedSize)
        if key in self._cache:
            return self._cache[key]

        cover_file, cover_url, podcast_url, podcast_title = id.split('|')

        def get_filename():
            return self.downloader.get_cover(cover_file, cover_url,
                    podcast_url, podcast_title, None, None, True)

        filename = get_filename()

        image = QImage()
        if not image.load(filename):
            if filename.startswith(cover_file):
                logger.info('Deleting broken cover art: %s', filename)
                util.delete_file(filename)
                image.load(get_filename())

        if not image.isNull():
            self._cache[key] = image.scaled(requestedSize,
                    Qt.KeepAspectRatioByExpanding,
                    Qt.SmoothTransformation)

        return self._cache[key]


########NEW FILE########
__FILENAME__ = model
# -*- coding: utf-8 -*-
#
# gPodder - A media aggregator and podcast client
# Copyright (c) 2005-2014 Thomas Perl and the gPodder Team
#
# gPodder is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# gPodder is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#


from PySide.QtCore import QObject, Property, Signal, Slot

import gpodder

_ = gpodder.gettext

import logging
logger = logging.getLogger(__name__)

from gpodder import model
from gpodder import util
from gpodder import youtube
from gpodder import download
from gpodder import query
from gpodder import model
from gpodder import coverart

import os
import urllib

convert = util.convert_bytes

class QEpisode(QObject):
    def __init__(self, wrapper_manager, podcast, episode):
        QObject.__init__(self)
        self._wrapper_manager = wrapper_manager
        self.episode_wrapper_refcount = 0
        self._podcast = podcast
        self._episode = episode

        # Caching of YouTube URLs, so we don't need to resolve
        # it every time we update the podcast item (doh!)
        # XXX: Maybe do this in the episode of the model already?
        self._qt_yt_url = None

        # Download progress tracking XXX: read directy from task
        self._qt_download_progress = 0

        # Playback tracking
        self._qt_playing = False

    @Slot(QObject, result=bool)
    def equals(self, other):
        """Needed for Python object identity comparison in JavaScript"""
        return self == other

    def __getattr__(self, name):
        logger.warn('Attribute access in %s: %s', self.__class__.__name__, name)
        return getattr(self._episode, name)

    def toggle_new(self):
        self._episode.mark(is_played=self._episode.is_new)
        self.changed.emit()
        self._podcast.changed.emit()

    def toggle_archive(self):
        self._episode.mark(is_locked=not self._episode.archive)
        self.changed.emit()
        self._podcast.changed.emit()

    def delete_episode(self):
        self._episode.delete_from_disk()
        self._episode.mark(is_played=True)
        self.changed.emit()
        self._podcast.changed.emit()
        self.source_url_changed.emit()

    changed = Signal()
    never_changed = Signal()
    source_url_changed = Signal()

    def _podcast(self):
        return self._podcast

    qpodcast = Property(QObject, _podcast, notify=never_changed)

    def _title(self):
        return convert(self._episode.trimmed_title)

    qtitle = Property(unicode, _title, notify=changed)

    def _sourceurl(self):
        if self._episode.was_downloaded(and_exists=True):
            url = self._episode.local_filename(create=False)
        elif self._qt_yt_url is not None:
            url = self._qt_yt_url
        else:
            url = youtube.get_real_download_url(self._episode.url)
            self._qt_yt_url = url
        return convert(url)

    qsourceurl = Property(unicode, _sourceurl, notify=source_url_changed)

    def _filetype(self):
        return self._episode.file_type() or 'download'

    qfiletype = Property(unicode, _filetype, notify=never_changed)

    def _pubdate(self):
        return self._episode.cute_pubdate()

    qpubdate = Property(unicode, _pubdate, notify=never_changed)

    def _filesize(self):
        if self._episode.file_size:
            return util.format_filesize(self._episode.file_size)
        else:
            return ''

    qfilesize = Property(unicode, _filesize, notify=changed)

    def _downloaded(self):
        return self._episode.was_downloaded(and_exists=True)

    qdownloaded = Property(bool, _downloaded, notify=changed)

    def _downloading(self):
        return self._episode.downloading

    qdownloading = Property(bool, _downloading, notify=changed)

    def _playing(self):
        return self._qt_playing

    def _set_playing(self, playing):
        if self._qt_playing != playing:
            if playing:
                self._episode.playback_mark()
            self._qt_playing = playing
            self.changed.emit()

    qplaying = Property(bool, _playing, _set_playing, notify=changed)

    def _progress(self):
        return self._qt_download_progress

    qprogress = Property(float, _progress, notify=changed)

    def qdownload(self, config, finished_callback=None, progress_callback=None):
        # Avoid starting the same download twice
        if self.download_task is not None:
            return

        # Initialize the download task here, so that the
        # UI will be updated as soon as possible
        self._wrapper_manager.add_active_episode(self)
        self._qt_download_progress = 0.
        task = download.DownloadTask(self._episode, config)
        task.status = download.DownloadTask.QUEUED
        self.changed.emit()
        if progress_callback is not None:
            progress_callback(self.id)

        def t(self):
            def cb(progress):
                if progress > self._qt_download_progress + .01 or progress == 1:
                    self._qt_download_progress = progress
                    self.changed.emit()
                    if progress_callback is not None:
                        progress_callback(self.id)
            task.add_progress_callback(cb)
            task.run()
            task.recycle()
            task.removed_from_list()
            self.source_url_changed.emit()

            if progress_callback is not None:
                progress_callback(self.id)

            # Make sure the single channel is updated (main view)
            self._podcast.changed.emit()

            # Make sure that "All episodes", etc.. are updated
            if finished_callback is not None:
                finished_callback()

            self._wrapper_manager.remove_active_episode(self)

        util.run_in_background(lambda: t(self), True)

    def _description(self):
        return convert(self._episode.description_html)

    qdescription = Property(unicode, _description, notify=changed)

    def _new(self):
        return self._episode.is_new

    qnew = Property(bool, _new, notify=changed)

    def _archive(self):
        return self._episode.archive

    qarchive = Property(bool, _archive, notify=changed)

    def _position(self):
        return self._episode.current_position

    def _set_position(self, position):
        current_position = int(position)
        if current_position == 0: return
        if current_position != self._episode.current_position:
            self._episode.current_position = current_position
            self.changed.emit()

    qposition = Property(int, _position, _set_position, notify=changed)

    def _duration(self):
        return self._episode.total_time

    def _set_duration(self, duration):
        total_time = int(duration)
        if total_time != self._episode.total_time:
            self._episode.total_time = total_time
            self.changed.emit()

    qduration = Property(int, _duration, _set_duration, notify=changed)


class QPodcast(QObject):
    def __init__(self, podcast):
        QObject.__init__(self)
        self._podcast = podcast
        self._updating = False

    @Slot(QObject, result=bool)
    def equals(self, other):
        """Needed for Python object identity comparison in JavaScript"""
        return self == other

    @classmethod
    def sort_key(cls, qpodcast):
        if isinstance(qpodcast, cls):
            sortkey = model.Model.podcast_sort_key(qpodcast._podcast)
        else:
            sortkey = None

        return (qpodcast.qsection, sortkey)

    def __getattr__(self, name):
        logger.warn('Attribute access in %s: %s', self.__class__.__name__, name)
        return getattr(self._podcast, name)

    def qupdate(self, force=False, finished_callback=None):
        if self._updating:
            # Update in progress - just wait, don't re-update
            return

        def t(self):
            self._updating = True
            self.changed.emit()
            if force:
                self._podcast.http_etag = None
                self._podcast.http_last_modified = None
            try:
                self._podcast.update()
            except Exception, e:
                # XXX: Handle exception (error message)!
                pass
            self._updating = False
            self.changed.emit()

            # Notify the caller that we've finished updating
            if finished_callback is not None:
                finished_callback()

        util.run_in_background(lambda: t(self))

    changed = Signal()

    def _updating(self):
        return self._updating

    qupdating = Property(bool, _updating, notify=changed)

    def _title(self):
        return convert(self._podcast.title)

    qtitle = Property(unicode, _title, notify=changed)

    def _url(self):
        return convert(self._podcast.url)

    qurl = Property(unicode, _url, notify=changed)

    def _coverfile(self):
        return convert(self._podcast.cover_file)

    qcoverfile = Property(unicode, _coverfile, notify=changed)

    def _coverurl(self):
        return convert(self._podcast.cover_url)

    qcoverurl = Property(unicode, _coverurl, notify=changed)

    def _coverart(self):
        quote = lambda x: convert(x) if x else u''
        return convert(u'image://cover/%s|%s|%s|%s' % (
            quote(self._podcast.cover_file),
            quote(self._podcast.cover_url),
            quote(self._podcast.url),
            quote(self._podcast.title),
        ))

    qcoverart = Property(unicode, _coverart, notify=changed)

    def _downloaded(self):
        return self._podcast.get_statistics()[3]

    qdownloaded = Property(int, _downloaded, notify=changed)

    def _new(self):
        return self._podcast.get_statistics()[2]

    qnew = Property(int, _new, notify=changed)

    def _description(self):
        return convert(util.get_first_line(self._podcast.description))

    qdescription = Property(unicode, _description, notify=changed)

    def _section(self):
        return convert(self._podcast.group_by)

    qsection = Property(unicode, _section, notify=changed)

    def set_section(self, section):
        self._podcast.section = section
        self._podcast.save()
        self.changed.emit()


class EpisodeSubsetView(QObject):
    def __init__(self, db, podcast_list_model, title, description, eql=None):
        QObject.__init__(self)
        self.db = db
        self.podcast_list_model = podcast_list_model
        self.title = title
        self.description = description
        self.eql = eql
        self.pause_subscription = False

        self._new_count = -1
        self._downloaded_count = -1

    def _update_stats(self):
        if self.eql is None:
            total, deleted, new, downloaded, unplayed = \
                    self.db.get_podcast_statistics()
        else:
            new, downloaded = 0, 0
            for episode in self.get_all_episodes():
                if episode.was_downloaded(and_exists=True):
                    downloaded += 1
                elif episode.is_new:
                    new += 1

        self._new_count = new
        self._downloaded_count = downloaded

    def _do_filter(self, items, is_tuple=False):
        """Filter a list of items via the attached SQL

        If is_tuple is True, the list of items should be a
        list of (podcast, episode) tuples, otherwise it
        should just be a list of episode objects.
        """
        if self.eql is not None:
            eql = query.EQL(self.eql)
            if is_tuple:
                match = lambda (podcast, episode): eql.match(episode)
            else:
                match = eql.match

            items = filter(match, items)

        return items

    def get_all_episodes_with_podcast(self):
        episodes = [(podcast, episode) for podcast in
                self.podcast_list_model.get_podcasts()
                for episode in podcast.get_all_episodes()]

        def sort_key(pair):
            podcast, episode = pair
            return model.Model.episode_sort_key(episode)

        return sorted(self._do_filter(episodes, is_tuple=True),
                key=sort_key, reverse=True)

    def get_all_episodes(self):
        episodes = []
        for podcast in self.podcast_list_model.get_podcasts():
            episodes.extend(podcast.get_all_episodes())

        return model.Model.sort_episodes_by_pubdate(
                self._do_filter(episodes), True)

    def qupdate(self, force=False, finished_callback=None):
        self._update_stats()
        self.changed.emit()

    changed = Signal()

    def _return_false(self):
        return False

    def _return_empty(self):
        return convert('')

    def _return_cover(self):
        return convert(coverart.CoverDownloader.ALL_EPISODES_ID)

    qupdating = Property(bool, _return_false, notify=changed)
    qurl = Property(unicode, _return_empty, notify=changed)
    qcoverfile = Property(unicode, _return_cover, notify=changed)
    qcoverurl = Property(unicode, _return_empty, notify=changed)
    qsection = Property(unicode, _return_empty, notify=changed)

    def _coverart(self):
        quote = lambda x: convert(x) if x else u''
        return convert(u'image://cover/%s|%s|%s|%s' % (
            quote(coverart.CoverDownloader.ALL_EPISODES_ID),
            u'',
            u'',
            quote(self.title),
        ))

    qcoverart = Property(unicode, _coverart, notify=changed)

    def _title(self):
        return convert(self.title)

    qtitle = Property(unicode, _title, notify=changed)

    def _description(self):
        return convert(self.description)

    qdescription = Property(unicode, _description, notify=changed)

    def _downloaded(self):
        if self._downloaded_count == -1:
            self._update_stats()
        return self._downloaded_count

    qdownloaded = Property(int, _downloaded, notify=changed)

    def _new(self):
        if self._new_count == -1:
            self._update_stats()
        return self._new_count

    qnew = Property(int, _new, notify=changed)



########NEW FILE########
__FILENAME__ = query
# -*- coding: utf-8 -*-
#
# gPodder - A media aggregator and podcast client
# Copyright (c) 2005-2014 Thomas Perl and the gPodder Team
#
# gPodder is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# gPodder is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#


#
#  gpodder.query - Episode Query Language (EQL) implementation (2010-11-29)
#

import gpodder

import re
import datetime

class Matcher(object):
    """Match implementation for EQL

    This class implements the low-level matching of
    EQL statements against episode objects.
    """

    def __init__(self, episode):
        self._episode = episode

    def match(self, term):
        try:
            return bool(eval(term, {'__builtins__': None}, self))
        except Exception, e:
            print e
            return False

    def __getitem__(self, k):
        episode = self._episode

        # Adjectives (for direct usage)
        if k == 'new':
            return (episode.state == gpodder.STATE_NORMAL and episode.is_new)
        elif k in ('downloaded', 'dl'):
            return episode.was_downloaded(and_exists=True)
        elif k in ('deleted', 'rm'):
            return episode.state == gpodder.STATE_DELETED
        elif k == 'played':
            return not episode.is_new
        elif k == 'downloading':
            return episode.downloading
        elif k == 'archive':
            return episode.archive
        elif k in ('finished', 'fin'):
            return episode.is_finished()
        elif k in ('video', 'audio'):
            return episode.file_type() == k
        elif k == 'torrent':
            return episode.url.endswith('.torrent') or 'torrent' in episode.mime_type

        # Nouns (for comparisons)
        if k in ('megabytes', 'mb'):
            return float(episode.file_size) / (1024*1024)
        elif k == 'title':
            return episode.title
        elif k == 'description':
            return episode.description
        elif k == 'since':
            return (datetime.datetime.now() - datetime.datetime.fromtimestamp(episode.published)).days
        elif k == 'age':
            return episode.age_in_days()
        elif k in ('minutes', 'min'):
            return float(episode.total_time) / 60
        elif k in ('remaining', 'rem'):
            return float(episode.total_time - episode.current_position) / 60

        raise KeyError(k)


class EQL(object):
    """A Query in EQL

    Objects of this class represent a query on episodes
    using EQL. Example usage:

    >>> q = EQL('downloaded and megabytes > 10')
    >>> q.filter(channel.get_all_episodes())

    >>> EQL('new and video').match(episode)

    Regular expression queries are also supported:

    >>> q = EQL('/^The.*/')

    >>> q = EQL('/community/i')

    Normal string matches are also supported:

    >>> q = EQL('"S04"')

    >>> q = EQL("'linux'")

    Normal EQL queries cannot be mixed with RegEx
    or string matching yet, so this does NOT work:

    >>> EQL('downloaded and /The.*/i')
    """

    def __init__(self, query):
        self._query = query
        self._flags = 0
        self._regex = False
        self._string = False

        # Regular expression based query
        match = re.match(r'^/(.*)/(i?)$', query)
        if match is not None:
            self._regex = True
            self._query, flags = match.groups()
            if flags == 'i':
                self._flags |= re.I

        # String based query
        match = re.match("^([\"'])(.*)(\\1)$", query)
        if match is not None:
            self._string = True
            a, query, b = match.groups()
            self._query = query.lower()

        # For everything else, compile the expression
        if not self._regex and not self._string:
            try:
                self._query = compile(query, '<eql-string>', 'eval')
            except Exception, e:
                print e
                self._query = None


    def match(self, episode):
        if self._query is None:
            return False

        if self._regex:
            return re.search(self._query, episode.title, self._flags) is not None
        elif self._string:
            return self._query in episode.title.lower()

        return Matcher(episode).match(self._query)

    def filter(self, episodes):
        return filter(self.match, episodes)


def UserEQL(query):
    """EQL wrapper for user input

    Automatically adds missing quotes around a
    non-EQL string for user-based input. In this
    case, EQL queries need to be enclosed in ().
    """

    if query is None:
        return None

    if query == '' or (query and query[0] not in "(/'\""):
        return EQL("'%s'" % query)
    else:
        return EQL(query)



########NEW FILE########
__FILENAME__ = schema
# -*- coding: utf-8 -*-
#
# gPodder - A media aggregator and podcast client
# Copyright (c) 2005-2014 Thomas Perl and the gPodder Team
#
# gPodder is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# gPodder is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#

# gpodder.schema - Database schema update and migration facility
# Thomas Perl <thp@gpodder.org>; 2011-02-01

from sqlite3 import dbapi2 as sqlite

import time
import shutil

import logging
logger = logging.getLogger(__name__)

EpisodeColumns = (
    'podcast_id',
    'title',
    'description',
    'url',
    'published',
    'guid',
    'link',
    'file_size',
    'mime_type',
    'state',
    'is_new',
    'archive',
    'download_filename',
    'total_time',
    'current_position',
    'current_position_updated',
    'last_playback',
    'payment_url',
)

PodcastColumns = (
    'title',
    'url',
    'link',
    'description',
    'cover_url',
    'auth_username',
    'auth_password',
    'http_last_modified',
    'http_etag',
    'auto_archive_episodes',
    'download_folder',
    'pause_subscription',
    'section',
    'payment_url',
    'download_strategy',
    'sync_to_mp3_player',
)

CURRENT_VERSION = 5


# SQL commands to upgrade old database versions to new ones
# Each item is a tuple (old_version, new_version, sql_commands) that should be
# applied to the database to migrate from old_version to new_version.
UPGRADE_SQL = [
        # Version 2: Section labels for the podcast list
        (1, 2, """
        ALTER TABLE podcast ADD COLUMN section TEXT NOT NULL DEFAULT ''
        """),

        # Version 3: Flattr integration (+ invalidate http_* fields to force
        # a feed update, so that payment URLs are parsed during the next check)
        (2, 3, """
        ALTER TABLE podcast ADD COLUMN payment_url TEXT NULL DEFAULT NULL
        ALTER TABLE episode ADD COLUMN payment_url TEXT NULL DEFAULT NULL
        UPDATE podcast SET http_last_modified=NULL, http_etag=NULL
        """),

        # Version 4: Per-podcast download strategy management
        (3, 4, """
        ALTER TABLE podcast ADD COLUMN download_strategy INTEGER NOT NULL DEFAULT 0
        """),

        # Version 5: Per-podcast MP3 player device synchronization option
        (4, 5, """
        ALTER TABLE podcast ADD COLUMN sync_to_mp3_player INTEGER NOT NULL DEFAULT 1
        """)
]

def initialize_database(db):
    # Create table for podcasts
    db.execute("""
    CREATE TABLE podcast (
        id INTEGER PRIMARY KEY NOT NULL,
        title TEXT NOT NULL DEFAULT '',
        url TEXT NOT NULL DEFAULT '',
        link TEXT NOT NULL DEFAULT '',
        description TEXT NOT NULL DEFAULT '',
        cover_url TEXT NULL DEFAULT NULL,
        auth_username TEXT NULL DEFAULT NULL,
        auth_password TEXT NULL DEFAULT NULL,
        http_last_modified TEXT NULL DEFAULT NULL,
        http_etag TEXT NULL DEFAULT NULL,
        auto_archive_episodes INTEGER NOT NULL DEFAULT 0,
        download_folder TEXT NOT NULL DEFAULT '',
        pause_subscription INTEGER NOT NULL DEFAULT 0,
        section TEXT NOT NULL DEFAULT '',
        payment_url TEXT NULL DEFAULT NULL,
        download_strategy INTEGER NOT NULL DEFAULT 0,
        sync_to_mp3_player INTEGER NOT NULL DEFAULT 1
    )
    """)

    INDEX_SQL = """
    CREATE UNIQUE INDEX idx_podcast_url ON podcast (url)
    CREATE UNIQUE INDEX idx_podcast_download_folder ON podcast (download_folder)
    """

    for sql in INDEX_SQL.strip().split('\n'):
        db.execute(sql)

    # Create table for episodes
    db.execute("""
    CREATE TABLE episode (
        id INTEGER PRIMARY KEY NOT NULL,
        podcast_id INTEGER NOT NULL,
        title TEXT NOT NULL DEFAULT '',
        description TEXT NOT NULL DEFAULT '',
        url TEXT NOT NULL,
        published INTEGER NOT NULL DEFAULT 0,
        guid TEXT NOT NULL,
        link TEXT NOT NULL DEFAULT '',
        file_size INTEGER NOT NULL DEFAULT 0,
        mime_type TEXT NOT NULL DEFAULT 'application/octet-stream',
        state INTEGER NOT NULL DEFAULT 0,
        is_new INTEGER NOT NULL DEFAULT 0,
        archive INTEGER NOT NULL DEFAULT 0,
        download_filename TEXT NULL DEFAULT NULL,
        total_time INTEGER NOT NULL DEFAULT 0,
        current_position INTEGER NOT NULL DEFAULT 0,
        current_position_updated INTEGER NOT NULL DEFAULT 0,
        last_playback INTEGER NOT NULL DEFAULT 0,
        payment_url TEXT NULL DEFAULT NULL
    )
    """)

    INDEX_SQL = """
    CREATE INDEX idx_episode_podcast_id ON episode (podcast_id)
    CREATE UNIQUE INDEX idx_episode_download_filename ON episode (podcast_id, download_filename)
    CREATE UNIQUE INDEX idx_episode_guid ON episode (podcast_id, guid)
    CREATE INDEX idx_episode_state ON episode (state)
    CREATE INDEX idx_episode_is_new ON episode (is_new)
    CREATE INDEX idx_episode_archive ON episode (archive)
    CREATE INDEX idx_episode_published ON episode (published)
    """

    for sql in INDEX_SQL.strip().split('\n'):
        db.execute(sql)

    # Create table for version info / metadata + insert initial data
    db.execute("""CREATE TABLE version (version integer)""")
    db.execute("INSERT INTO version (version) VALUES (%d)" % CURRENT_VERSION)
    db.commit()


def upgrade(db, filename):
    if not list(db.execute('PRAGMA table_info(version)')):
        initialize_database(db)
        return

    version = db.execute('SELECT version FROM version').fetchone()[0]
    if version == CURRENT_VERSION:
        return

    # We are trying an upgrade - save the current version of the DB
    backup = '%s_upgraded-v%d_%d' % (filename, int(version), int(time.time()))
    try:
        shutil.copy(filename, backup)
    except Exception, e:
        raise Exception('Cannot create DB backup before upgrade: ' + e)

    db.execute("DELETE FROM version")

    for old_version, new_version, upgrade in UPGRADE_SQL:
        if version == old_version:
            for sql in upgrade.strip().split('\n'):
                db.execute(sql)
            version = new_version

    assert version == CURRENT_VERSION

    db.execute("INSERT INTO version (version) VALUES (%d)" % version)
    db.commit()

    if version != CURRENT_VERSION:
        raise Exception('Database schema version unknown')


def convert_gpodder2_db(old_db, new_db):
    """Convert gPodder 2.x databases to the new format

    Both arguments should be SQLite3 connections to the
    corresponding databases.
    """

    old_db = sqlite.connect(old_db)
    new_db_filename = new_db
    new_db = sqlite.connect(new_db)
    upgrade(new_db, new_db_filename)

    # Copy data for podcasts
    old_cur = old_db.cursor()
    columns = [x[1] for x in old_cur.execute('PRAGMA table_info(channels)')]
    for row in old_cur.execute('SELECT * FROM channels'):
        row = dict(zip(columns, row))
        values = (
                row['id'],
                row['override_title'] or row['title'],
                row['url'],
                row['link'],
                row['description'],
                row['image'],
                row['username'] or None,
                row['password'] or None,
                row['last_modified'] or None,
                row['etag'] or None,
                row['channel_is_locked'],
                row['foldername'],
                not row['feed_update_enabled'],
                '',
                None,
                0,
                row['sync_to_devices'],
        )
        new_db.execute("""
        INSERT INTO podcast VALUES (%s)
        """ % ', '.join('?'*len(values)), values)
    old_cur.close()

    # Copy data for episodes
    old_cur = old_db.cursor()
    columns = [x[1] for x in old_cur.execute('PRAGMA table_info(episodes)')]
    for row in old_cur.execute('SELECT * FROM episodes'):
        row = dict(zip(columns, row))
        values = (
                row['id'],
                row['channel_id'],
                row['title'],
                row['description'],
                row['url'],
                row['pubDate'],
                row['guid'],
                row['link'],
                row['length'],
                row['mimetype'],
                row['state'],
                not row['played'],
                row['locked'],
                row['filename'],
                row['total_time'],
                row['current_position'],
                row['current_position_updated'],
                0,
                None,
        )
        new_db.execute("""
        INSERT INTO episode VALUES (%s)
        """ % ', '.join('?'*len(values)), values)
    old_cur.close()

    old_db.close()
    new_db.commit()
    new_db.close()

def check_data(db):
    # All episodes must be assigned to a podcast
    orphan_episodes = db.get('SELECT COUNT(id) FROM episode '
            'WHERE podcast_id NOT IN (SELECT id FROM podcast)')
    if orphan_episodes > 0:
        logger.error('Orphaned episodes found in database')


########NEW FILE########
__FILENAME__ = services
# -*- coding: utf-8 -*-
#
# gPodder - A media aggregator and podcast client
# Copyright (c) 2005-2014 Thomas Perl and the gPodder Team
#
# gPodder is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# gPodder is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#


#
#  services.py -- Core Services for gPodder
#  Thomas Perl <thp@perli.net>   2007-08-24
#
#

import gpodder

_ = gpodder.gettext

from gpodder import util


class ObservableService(object):
    def __init__(self, signal_names=[]):
        self.observers = {}
        for signal in signal_names:
            self.observers[signal] = []

    def register(self, signal_name, observer):
        if signal_name in self.observers:
            if not observer in self.observers[signal_name]:
                self.observers[signal_name].append(observer)
                return True

        return False

    def unregister(self, signal_name, observer):
        if signal_name in self.observers:
            if observer in self.observers[signal_name]:
                self.observers[signal_name].remove(observer)
                return True

        return False

    def notify(self, signal_name, *args):
        if signal_name in self.observers:
            for observer in self.observers[signal_name]:
                util.idle_add(observer, *args)

            return True

        return False



########NEW FILE########
__FILENAME__ = sync
# -*- coding: utf-8 -*-
#
# gPodder - A media aggregator and podcast client
# Copyright (c) 2005-2014 Thomas Perl and the gPodder Team
#
# gPodder is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# gPodder is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#


# sync.py -- Device synchronization
# Thomas Perl <thp@perli.net> 2007-12-06
# based on libipodsync.py (2006-04-05 Thomas Perl)
# Ported to gPodder 3 by Joseph Wickremasinghe in June 2012

import gpodder

from gpodder import util
from gpodder import services
from gpodder import download

import logging
logger = logging.getLogger(__name__)

import calendar

_ = gpodder.gettext

#
# TODO: Re-enable iPod and MTP sync support
#

pymtp_available = False
gpod_available = True
try:
    import gpod
except:
    gpod_available = False
    logger.warning('Could not find gpod')

#pymtp_available = True
#try:
#    import gpodder.gpopymtp as pymtp
#except:
#    pymtp_available = False
#    logger.warning('Could not load gpopymtp (libmtp not installed?).')

try:
    import eyed3.mp3
except:
    logger.warning('Could not find eyed3.mp3')

import os.path
import glob
import time

if pymtp_available:
    class MTP(pymtp.MTP):
        sep = os.path.sep

        def __init__(self):
            pymtp.MTP.__init__(self)
            self.folders = {}

        def connect(self):
            pymtp.MTP.connect(self)
            self.folders = self.unfold(self.mtp.LIBMTP_Get_Folder_List(self.device))

        def get_folder_list(self):
            return self.folders

        def unfold(self, folder, path=''):
            result = {}
            while folder:
                folder = folder.contents
                name = self.sep.join([path, folder.name]).lstrip(self.sep)
                result[name] = folder.folder_id
                if folder.child:
                    result.update(self.unfold(folder.child, name))
                folder = folder.sibling
            return result

        def mkdir(self, path):
            folder_id = 0
            prefix = []
            parts = path.split(self.sep)
            while parts:
                prefix.append(parts[0])
                tmpath = self.sep.join(prefix)
                if self.folders.has_key(tmpath):
                    folder_id = self.folders[tmpath]
                else:
                    folder_id = self.create_folder(parts[0], parent=folder_id)
                    # logger.info('Creating subfolder %s in %s (id=%u)' % (parts[0], self.sep.join(prefix), folder_id))
                    tmpath = self.sep.join(prefix + [parts[0]])
                    self.folders[tmpath] = folder_id
                # logger.info(">>> %s = %s" % (tmpath, folder_id))
                del parts[0]
            # logger.info('MTP.mkdir: %s = %u' % (path, folder_id))
            return folder_id

def open_device(gui):
    config = gui._config
    device_type = gui._config.device_sync.device_type
    if device_type == 'ipod':
        return iPodDevice(config,
                gui.download_status_model,
                gui.download_queue_manager)
    elif device_type == 'filesystem':
        return MP3PlayerDevice(config,
                gui.download_status_model,
                gui.download_queue_manager)

    return None

def get_track_length(filename):
    if util.find_command('mplayer') is not None:
        try:
            mplayer_output = os.popen('mplayer -msglevel all=-1 -identify -vo null -ao null -frames 0 "%s" 2>/dev/null' % filename).read()
            return int(float(mplayer_output[mplayer_output.index('ID_LENGTH'):].splitlines()[0][10:])*1000)
        except:
            pass
    else:
        logger.info('Please install MPlayer for track length detection.')

    try:
        mp3file = eyed3.mp3.Mp3AudioFile(filename)
        return int(mp3file.info.time_secs * 1000)
    except Exception, e:
        logger.warn('Could not determine length: %s', filename, exc_info=True)

    return int(60*60*1000*3) # Default is three hours (to be on the safe side)

class SyncTrack(object):
    """
    This represents a track that is on a device. You need
    to specify at least the following keyword arguments,
    because these will be used to display the track in the
    GUI. All other keyword arguments are optional and can
    be used to reference internal objects, etc... See the
    iPod synchronization code for examples.

    Keyword arguments needed:
        playcount (How often has the track been played?)
        podcast (Which podcast is this track from? Or: Folder name)
        released (The release date of the episode)

    If any of these fields is unknown, it should not be
    passed to the function (the values will default to None
    for all required fields).
    """
    def __init__(self, title, length, modified, **kwargs):
        self.title = title
        self.length = length
        self.filesize = util.format_filesize(length)
        self.modified = modified

        # Set some (possible) keyword arguments to default values
        self.playcount = 0
        self.podcast = None
        self.released = None

        # Convert keyword arguments to object attributes
        self.__dict__.update(kwargs)

    @property
    def playcount_str(self):
        return str(self.playcount)


class Device(services.ObservableService):
    def __init__(self, config):
        self._config = config
        self.cancelled = False
        self.allowed_types = ['audio', 'video']
        self.errors = []
        self.tracks_list = []
        signals = ['progress', 'sub-progress', 'status', 'done', 'post-done']
        services.ObservableService.__init__(self, signals)

    def open(self):
        pass

    def cancel(self):
        self.cancelled = True
        self.notify('status', _('Cancelled by user'))

    def close(self):
        self.notify('status', _('Writing data to disk'))
        if self._config.device_sync.after_sync.sync_disks and not gpodder.ui.win32:
            os.system('sync')
        else:
            logger.warning('Not syncing disks. Unmount your device before unplugging.')
        return True

    def add_sync_tasks(self,tracklist, force_played=False, done_callback=None):
        for track in list(tracklist):
            # Filter tracks that are not meant to be synchronized
            does_not_exist = not track.was_downloaded(and_exists=True)
            exclude_played = (not track.is_new and
                    self._config.device_sync.skip_played_episodes)
            wrong_type = track.file_type() not in self.allowed_types

            if does_not_exist or exclude_played or wrong_type:
                logger.info('Excluding %s from sync', track.title)
                tracklist.remove(track)
        
        if tracklist:
            for track in sorted(tracklist, key=lambda e: e.pubdate_prop):
                if self.cancelled:
                    return False
    
                # XXX: need to check if track is added properly?
                sync_task=SyncTask(track)
    
                sync_task.status=sync_task.QUEUED
                sync_task.device=self
                self.download_status_model.register_task(sync_task)
                self.download_queue_manager.add_task(sync_task)
        else:
            logger.warning("No episodes to sync")

        if done_callback:
            done_callback()

        return True

    def remove_tracks(self, tracklist):
        for idx, track in enumerate(tracklist):
            if self.cancelled:
                return False
            self.notify('progress', idx, len(tracklist))
            self.remove_track(track)

        return True

    def get_all_tracks(self):
        pass

    def add_track(self, track, reporthook=None):
        pass

    def remove_track(self, track):
        pass

    def get_free_space(self):
        pass

    def episode_on_device(self, episode):
        return self._track_on_device(episode.title)

    def _track_on_device(self, track_name):
        for t in self.tracks_list:
            title = t.title
            if track_name == title:
                return t
        return None

class iPodDevice(Device):
    def __init__(self, config,
            download_status_model,
            download_queue_manager):
        Device.__init__(self, config)

        self.mountpoint = self._config.device_sync.device_folder
        self.download_status_model = download_status_model
        self.download_queue_manager = download_queue_manager
        self.itdb = None
        self.podcast_playlist = None

    def get_free_space(self):
        # Reserve 10 MiB for iTunesDB writing (to be on the safe side)
        RESERVED_FOR_ITDB = 1024*1024*10
        return util.get_free_disk_space(self.mountpoint) - RESERVED_FOR_ITDB

    def open(self):
        Device.open(self)
        if not gpod_available or not os.path.isdir(self.mountpoint):
            return False

        self.notify('status', _('Opening iPod database'))
        self.itdb = gpod.itdb_parse(self.mountpoint, None)
        if self.itdb is None:
            return False

        self.itdb.mountpoint = self.mountpoint
        self.podcasts_playlist = gpod.itdb_playlist_podcasts(self.itdb)
        self.master_playlist = gpod.itdb_playlist_mpl(self.itdb)

        if self.podcasts_playlist:
            self.notify('status', _('iPod opened'))

            # build the initial tracks_list
            self.tracks_list = self.get_all_tracks()

            return True
        else:
            return False

    def close(self):
        if self.itdb is not None:
            self.notify('status', _('Saving iPod database'))
            gpod.itdb_write(self.itdb, None)
            self.itdb = None

            if self._config.ipod_write_gtkpod_extended:
                self.notify('status', _('Writing extended gtkpod database'))
                itunes_folder = os.path.join(self.mountpoint, 'iPod_Control', 'iTunes')
                ext_filename = os.path.join(itunes_folder, 'iTunesDB.ext')
                idb_filename = os.path.join(itunes_folder, 'iTunesDB')
                if os.path.exists(ext_filename) and os.path.exists(idb_filename):
                    try:
                        db = gpod.ipod.Database(self.mountpoint)
                        gpod.gtkpod.parse(ext_filename, db, idb_filename)
                        gpod.gtkpod.write(ext_filename, db, idb_filename)
                        db.close()
                    except:
                        logger.error('Error writing iTunesDB.ext')
                else:
                    logger.warning('Could not find %s or %s.',
                            ext_filename, idb_filename)

        Device.close(self)
        return True

    def update_played_or_delete(self, channel, episodes, delete_from_db):
        """
        Check whether episodes on ipod are played and update as played
        and delete if required.
        """
        for episode in episodes:
            track = self.episode_on_device(episode)
            if track:
                gtrack = track.libgpodtrack
                if gtrack.playcount > 0:
                    if delete_from_db and not gtrack.rating:
                        logger.info('Deleting episode from db %s', gtrack.title)
                        channel.delete_episode(episode)
                    else:
                        logger.info('Marking episode as played %s', gtrack.title)

    def purge(self):
        for track in gpod.sw_get_playlist_tracks(self.podcasts_playlist):
            if gpod.itdb_filename_on_ipod(track) is None:
                logger.info('Episode has no file: %s', track.title)
                # self.remove_track_gpod(track)
            elif track.playcount > 0  and not track.rating:
                logger.info('Purging episode: %s', track.title)
                self.remove_track_gpod(track)

    def get_all_tracks(self):
        tracks = []
        for track in gpod.sw_get_playlist_tracks(self.podcasts_playlist):
            filename = gpod.itdb_filename_on_ipod(track)

            if filename is None:
                # This can happen if the episode is deleted on the device
                logger.info('Episode has no file: %s', track.title)
                self.remove_track_gpod(track)
                continue

            length = util.calculate_size(filename)
            timestamp = util.file_modification_timestamp(filename)
            modified = util.format_date(timestamp)
            try:
                released = gpod.itdb_time_mac_to_host(track.time_released)
                released = util.format_date(released)
            except ValueError, ve:
                # timestamp out of range for platform time_t (bug 418)
                logger.info('Cannot convert track time: %s', ve)
                released = 0

            t = SyncTrack(track.title, length, modified,
                    modified_sort=timestamp,
                    libgpodtrack=track,
                    playcount=track.playcount,
                    released=released,
                    podcast=track.artist)
            tracks.append(t)
        return tracks

    def remove_track(self, track):
        self.notify('status', _('Removing %s') % track.title)
        self.remove_track_gpod(track.libgpodtrack)

    def remove_track_gpod(self, track):
        filename = gpod.itdb_filename_on_ipod(track)

        try:
            gpod.itdb_playlist_remove_track(self.podcasts_playlist, track)
        except:
            logger.info('Track %s not in playlist', track.title)

        gpod.itdb_track_unlink(track)
        util.delete_file(filename)

    def add_track(self, episode,reporthook=None):
        self.notify('status', _('Adding %s') % episode.title)
        tracklist = gpod.sw_get_playlist_tracks(self.podcasts_playlist)
        podcasturls=[track.podcasturl for track in tracklist]

        if episode.url in podcasturls:
            # Mark as played on iPod if played locally (and set podcast flags)
            self.set_podcast_flags(tracklist[podcasturls.index(episode.url)], episode)
            return True

        original_filename = episode.local_filename(create=False)
        # The file has to exist, if we ought to transfer it, and therefore,
        # local_filename(create=False) must never return None as filename
        assert original_filename is not None
        local_filename = original_filename

        if util.calculate_size(original_filename) > self.get_free_space():
            logger.error('Not enough space on %s, sync aborted...', self.mountpoint)
            d = {'episode': episode.title, 'mountpoint': self.mountpoint}
            message =_('Error copying %(episode)s: Not enough free space on %(mountpoint)s')
            self.errors.append(message % d)
            self.cancelled = True
            return False

        local_filename = episode.local_filename(create=False)

        (fn, extension) = os.path.splitext(local_filename)
        if extension.lower().endswith('ogg'):
            logger.error('Cannot copy .ogg files to iPod.')
            return False

        track = gpod.itdb_track_new()

        # Add release time to track if episode.published has a valid value
        if episode.published > 0:
            try:
                # libgpod>= 0.5.x uses a new timestamp format
                track.time_released = gpod.itdb_time_host_to_mac(int(episode.published))
            except:
                # old (pre-0.5.x) libgpod versions expect mactime, so
                # we're going to manually build a good mactime timestamp here :)
                #
                # + 2082844800 for unixtime => mactime (1970 => 1904)
                track.time_released = int(episode.published + 2082844800)

        track.title = str(episode.title)
        track.album = str(episode.channel.title)
        track.artist = str(episode.channel.title)
        track.description = str(util.remove_html_tags(episode.description))

        track.podcasturl = str(episode.url)
        track.podcastrss = str(episode.channel.url)

        track.tracklen = get_track_length(local_filename)
        track.size = os.path.getsize(local_filename)

        if episode.file_type() == 'audio':
            track.filetype = 'mp3'
            track.mediatype = 0x00000004
        elif episode.file_type() == 'video':
            track.filetype = 'm4v'
            track.mediatype = 0x00000006

        self.set_podcast_flags(track, episode)

        gpod.itdb_track_add(self.itdb, track, -1)
        gpod.itdb_playlist_add_track(self.master_playlist, track, -1)
        gpod.itdb_playlist_add_track(self.podcasts_playlist, track, -1)
        copied = gpod.itdb_cp_track_to_ipod(track, str(local_filename), None)
        reporthook(episode.file_size, 1, episode.file_size)

        # If the file has been converted, delete the temporary file here
        if local_filename != original_filename:
            util.delete_file(local_filename)

        return True

    def set_podcast_flags(self, track, episode):
        try:
            # Set several flags for to podcast values
            track.remember_playback_position = 0x01
            track.flag1 = 0x02
            track.flag2 = 0x01
            track.flag3 = 0x01
            track.flag4 = 0x01
        except:
            logger.warning('Seems like your python-gpod is out-of-date.')


class MP3PlayerDevice(Device):
    def __init__(self, config,
            download_status_model,
            download_queue_manager):
        Device.__init__(self, config)
        self.destination = util.sanitize_encoding(self._config.device_sync.device_folder)
        self.buffer_size = 1024*1024 # 1 MiB
        self.download_status_model = download_status_model
        self.download_queue_manager = download_queue_manager

    def get_free_space(self):
        return util.get_free_disk_space(self.destination)

    def open(self):
        Device.open(self)
        self.notify('status', _('Opening MP3 player'))

        if util.directory_is_writable(self.destination):
            self.notify('status', _('MP3 player opened'))
            self.tracks_list = self.get_all_tracks()
            return True

        return False

    def get_episode_folder_on_device(self, episode):
        if self._config.device_sync.one_folder_per_podcast:
            # Add channel title as subfolder
            folder = episode.channel.title
            # Clean up the folder name for use on limited devices
            folder = util.sanitize_filename(folder,
                self._config.device_sync.max_filename_length)
            folder = os.path.join(self.destination, folder)
        else:
            folder = self.destination

        return util.sanitize_encoding(folder)

    def get_episode_file_on_device(self, episode):
        # get the local file
        from_file = util.sanitize_encoding(episode.local_filename(create=False))
        # get the formated base name
        filename_base = util.sanitize_filename(episode.sync_filename(
            self._config.device_sync.custom_sync_name_enabled,
            self._config.device_sync.custom_sync_name),
            self._config.device_sync.max_filename_length)
        # add the file extension
        to_file = filename_base + os.path.splitext(from_file)[1].lower()

        # dirty workaround: on bad (empty) episode titles,
        # we simply use the from_file basename
        # (please, podcast authors, FIX YOUR RSS FEEDS!)
        if os.path.splitext(to_file)[0] == '':
            to_file = os.path.basename(from_file)

        return to_file

    def add_track(self, episode,reporthook=None):
        self.notify('status', _('Adding %s') % episode.title.decode('utf-8', 'ignore'))

        # get the folder on the device
        folder = self.get_episode_folder_on_device(episode)

        filename = episode.local_filename(create=False)
        # The file has to exist, if we ought to transfer it, and therefore,
        # local_filename(create=False) must never return None as filename
        assert filename is not None

        from_file = util.sanitize_encoding(filename)
        # get the filename that will be used on the device
        to_file = self.get_episode_file_on_device(episode)
        to_file = util.sanitize_encoding(os.path.join(folder, to_file))

        if not os.path.exists(folder):
            try:
                os.makedirs(folder)
            except:
                logger.error('Cannot create folder on MP3 player: %s', folder)
                return False

        if not os.path.exists(to_file):
            logger.info('Copying %s => %s',
                    os.path.basename(from_file),
                    to_file.decode(util.encoding))
            self.copy_file_progress(from_file, to_file, reporthook)

        return True

    def copy_file_progress(self, from_file, to_file, reporthook=None):
        try:
            out_file = open(to_file, 'wb')
        except IOError, ioerror:
            d = {'filename': ioerror.filename, 'message': ioerror.strerror}
            self.errors.append(_('Error opening %(filename)s: %(message)s') % d)
            self.cancel()
            return False

        try:
            in_file = open(from_file, 'rb')
        except IOError, ioerror:
            d = {'filename': ioerror.filename, 'message': ioerror.strerror}
            self.errors.append(_('Error opening %(filename)s: %(message)s') % d)
            self.cancel()
            return False

        in_file.seek(0, os.SEEK_END)
        total_bytes = in_file.tell()
        in_file.seek(0)

        bytes_read = 0
        s = in_file.read(self.buffer_size)
        while s:
            bytes_read += len(s)
            try:
                out_file.write(s)
            except IOError, ioerror:
                self.errors.append(ioerror.strerror)
                try:
                    out_file.close()
                except:
                    pass
                try:
                    logger.info('Trying to remove partially copied file: %s' % to_file)
                    os.unlink( to_file)
                    logger.info('Yeah! Unlinked %s at least..' % to_file)
                except:
                    logger.error('Error while trying to unlink %s. OH MY!' % to_file)
                self.cancel()
                return False
            reporthook(bytes_read, 1, total_bytes)
            s = in_file.read(self.buffer_size)
        out_file.close()
        in_file.close()

        return True

    def get_all_tracks(self):
        tracks = []

        if self._config.one_folder_per_podcast:
            files = glob.glob(os.path.join(self.destination, '*', '*'))
        else:
            files = glob.glob(os.path.join(self.destination, '*'))

        for filename in files:
            (title, extension) = os.path.splitext(os.path.basename(filename))
            length = util.calculate_size(filename)

            timestamp = util.file_modification_timestamp(filename)
            modified = util.format_date(timestamp)
            if self._config.one_folder_per_podcast:
                podcast_name = os.path.basename(os.path.dirname(filename))
            else:
                podcast_name = None

            t = SyncTrack(title, length, modified,
                    modified_sort=timestamp,
                    filename=filename,
                    podcast=podcast_name)
            tracks.append(t)
        return tracks

    def episode_on_device(self, episode):
        e = util.sanitize_filename(episode.sync_filename(
            self._config.device_sync.custom_sync_name_enabled,
            self._config.device_sync.custom_sync_name),
            self._config.device_sync.max_filename_length)
        return self._track_on_device(e)

    def remove_track(self, track):
        self.notify('status', _('Removing %s') % track.title)
        util.delete_file(track.filename)
        directory = os.path.dirname(track.filename)
        if self.directory_is_empty(directory) and self._config.one_folder_per_podcast:
            try:
                os.rmdir(directory)
            except:
                logger.error('Cannot remove %s', directory)

    def directory_is_empty(self, directory):
        files = glob.glob(os.path.join(directory, '*'))
        dotfiles = glob.glob(os.path.join(directory, '.*'))
        return len(files+dotfiles) == 0

class MTPDevice(Device):
    def __init__(self, config):
        Device.__init__(self, config)
        self.__model_name = None
        try:
            self.__MTPDevice = MTP()
        except NameError, e:
            # pymtp not available / not installed (see bug 924)
            logger.error('pymtp not found: %s', str(e))
            self.__MTPDevice = None

    def __callback(self, sent, total):
        if self.cancelled:
            return -1
        percentage = round(float(sent)/float(total)*100)
        text = ('%i%%' % percentage)
        self.notify('progress', sent, total, text)

    def __date_to_mtp(self, date):
        """
        this function format the given date and time to a string representation
        according to MTP specifications: YYYYMMDDThhmmss.s

        return
            the string representation od the given date
        """
        if not date:
            return ""
        try:
            d = time.gmtime(date)
            return time.strftime("%Y%m%d-%H%M%S.0Z", d)
        except Exception, exc:
            logger.error('ERROR: An error has happend while trying to convert date to an mtp string')
            return None

    def __mtp_to_date(self, mtp):
        """
        this parse the mtp's string representation for date
        according to specifications (YYYYMMDDThhmmss.s) to
        a python time object
        """
        if not mtp:
            return None

        try:
            mtp = mtp.replace(" ", "0") # replace blank with 0 to fix some invalid string
            d = time.strptime(mtp[:8] + mtp[9:13],"%Y%m%d%H%M%S")
            _date = calendar.timegm(d)
            if len(mtp)==20:
                # TIME ZONE SHIFTING: the string contains a hour/min shift relative to a time zone
                try:
                    shift_direction=mtp[15]
                    hour_shift = int(mtp[16:18])
                    minute_shift = int(mtp[18:20])
                    shift_in_sec = hour_shift * 3600 + minute_shift * 60
                    if shift_direction == "+":
                        _date += shift_in_sec
                    elif shift_direction == "-":
                        _date -= shift_in_sec
                    else:
                        raise ValueError("Expected + or -")
                except Exception, exc:
                    logger.warning('WARNING: ignoring invalid time zone information for %s (%s)')
            return max( 0, _date )
        except Exception, exc:
            logger.warning('WARNING: the mtp date "%s" can not be parsed against mtp specification (%s)')
            return None

    def get_name(self):
        """
        this function try to find a nice name for the device.
        First, it tries to find a friendly (user assigned) name
        (this name can be set by other application and is stored on the device).
        if no friendly name was assign, it tries to get the model name (given by the vendor).
        If no name is found at all, a generic one is returned.

        Once found, the name is cached internaly to prevent reading again the device

        return
            the name of the device
        """

        if self.__model_name:
            return self.__model_name

        if self.__MTPDevice is None:
            return _('MTP device')

        self.__model_name = self.__MTPDevice.get_devicename() # actually libmtp.Get_Friendlyname
        if not self.__model_name or self.__model_name == "?????":
            self.__model_name = self.__MTPDevice.get_modelname()
        if not self.__model_name:
            self.__model_name = _('MTP device')

        return self.__model_name

    def open(self):
        Device.open(self)
        logger.info("opening the MTP device")
        self.notify('status', _('Opening the MTP device'), )

        try:
            self.__MTPDevice.connect()
            # build the initial tracks_list
            self.tracks_list = self.get_all_tracks()
        except Exception, exc:
            logger.error('unable to find an MTP device (%s)')
            return False

        self.notify('status', _('%s opened') % self.get_name())
        return True

    def close(self):
        logger.info("closing %s", self.get_name())
        self.notify('status', _('Closing %s') % self.get_name())

        try:
            self.__MTPDevice.disconnect()
        except Exception, exc:
            logger.error('unable to close %s (%s)', self.get_name())
            return False

        self.notify('status', _('%s closed') % self.get_name())
        Device.close(self)
        return True

    def add_track(self, episode):
        self.notify('status', _('Adding %s...') % episode.title)
        filename = str(self.convert_track(episode))
        logger.info("sending %s (%s).", filename, episode.title)

        try:
            # verify free space
            needed = util.calculate_size(filename)
            free = self.get_free_space()
            if needed > free:
                logger.error('Not enough space on device %s: %s available, but need at least %s', self.get_name(), util.format_filesize(free), util.format_filesize(needed))
                self.cancelled = True
                return False

            # fill metadata
            metadata = pymtp.LIBMTP_Track()
            metadata.title = str(episode.title)
            metadata.artist = str(episode.channel.title)
            metadata.album = str(episode.channel.title)
            metadata.genre = "podcast"
            metadata.date = self.__date_to_mtp(episode.published)
            metadata.duration = get_track_length(str(filename))

            folder_name = ''
            if episode.mimetype.startswith('audio/') and self._config.mtp_audio_folder:
                folder_name = self._config.mtp_audio_folder
            if episode.mimetype.startswith('video/') and self._config.mtp_video_folder:
                folder_name = self._config.mtp_video_folder
            if episode.mimetype.startswith('image/') and self._config.mtp_image_folder:
                folder_name = self._config.mtp_image_folder

            if folder_name != '' and self._config.mtp_podcast_folders:
                folder_name += os.path.sep + str(episode.channel.title)

            # log('Target MTP folder: %s' % folder_name)

            if folder_name == '':
                folder_id = 0
            else:
                folder_id = self.__MTPDevice.mkdir(folder_name)

            # send the file
            to_file = util.sanitize_filename(metadata.title) + episode.extension()
            self.__MTPDevice.send_track_from_file(filename, to_file,
                    metadata, folder_id, callback=self.__callback)
            if gpodder.user_hooks is not None:
                gpodder.user_hooks.on_file_copied_to_mtp(self, filename, to_file)
        except:
            logger.error('unable to add episode %s', episode.title)
            return False

        return True

    def remove_track(self, sync_track):
        self.notify('status', _('Removing %s') % sync_track.mtptrack.title)
        logger.info("removing %s", sync_track.mtptrack.title)

        try:
            self.__MTPDevice.delete_object(sync_track.mtptrack.item_id)
        except Exception, exc:
            logger.error('unable remove file %s (%s)', sync_track.mtptrack.filename)

        logger.info('%s removed', sync_track.mtptrack.title)

    def get_all_tracks(self):
        try:
            listing = self.__MTPDevice.get_tracklisting(callback=self.__callback)
        except Exception, exc:
            logger.error('unable to get file listing %s (%s)')

        tracks = []
        for track in listing:
            title = track.title
            if not title or title=="": title=track.filename
            if len(title) > 50: title = title[0:49] + '...'
            artist = track.artist
            if artist and len(artist) > 50: artist = artist[0:49] + '...'
            length = track.filesize
            age_in_days = 0
            date = self.__mtp_to_date(track.date)
            if not date:
                modified = track.date # not a valid mtp date. Display what mtp gave anyway
                modified_sort = -1 # no idea how to sort invalid date
            else:
                modified = util.format_date(date)
                modified_sort = date

            t = SyncTrack(title, length, modified, modified_sort=modified_sort, mtptrack=track, podcast=artist)
            tracks.append(t)
        return tracks

    def get_free_space(self):
        if self.__MTPDevice is not None:
            return self.__MTPDevice.get_freespace()
        else:
            return 0

class SyncCancelledException(Exception): pass

class SyncTask(download.DownloadTask):
    # An object representing the synchronization task of an episode

    # Possible states this sync task can be in
    STATUS_MESSAGE = (_('Added'), _('Queued'), _('Synchronizing'),
            _('Finished'), _('Failed'), _('Cancelled'), _('Paused'))
    (INIT, QUEUED, DOWNLOADING, DONE, FAILED, CANCELLED, PAUSED) = range(7)


    def __str__(self):
        return self.__episode.title

    def __get_status(self):
        return self.__status

    def __set_status(self, status):
        if status != self.__status:
            self.__status_changed = True
            self.__status = status

    status = property(fget=__get_status, fset=__set_status)

    def __get_device(self):
        return self.__device

    def __set_device(self, device):
        self.__device = device

    device = property(fget=__get_device, fset=__set_device)

    def __get_status_changed(self):
        if self.__status_changed:
            self.__status_changed = False
            return True
        else:
            return False

    status_changed = property(fget=__get_status_changed)

    def __get_activity(self):
        return self.__activity

    def __set_activity(self, activity):
        self.__activity = activity

    activity = property(fget=__get_activity, fset=__set_activity)

    def __get_empty_string(self):
        return ''

    url = property(fget=__get_empty_string)
    podcast_url = property(fget=__get_empty_string)

    def __get_episode(self):
        return self.__episode

    episode = property(fget=__get_episode)

    def cancel(self):
        if self.status in (self.DOWNLOADING, self.QUEUED):
            self.status = self.CANCELLED

    def removed_from_list(self):
        # XXX: Should we delete temporary/incomplete files here?
        pass

    def __init__(self, episode):
        self.__status = SyncTask.INIT
        self.__activity = SyncTask.ACTIVITY_SYNCHRONIZE
        self.__status_changed = True
        self.__episode = episode

        # Create the target filename and save it in the database
        self.filename = self.__episode.local_filename(create=False)
        self.tempname = self.filename + '.partial'

        self.total_size = self.__episode.file_size
        self.speed = 0.0
        self.progress = 0.0
        self.error_message = None

        # Have we already shown this task in a notification?
        self._notification_shown = False

        # Variables for speed limit and speed calculation
        self.__start_time = 0
        self.__start_blocks = 0
        self.__limit_rate_value = 999
        self.__limit_rate = 999

        # Callbacks
        self._progress_updated = lambda x: None

    def notify_as_finished(self):
        if self.status == SyncTask.DONE:
            if self._notification_shown:
                return False
            else:
                self._notification_shown = True
                return True

        return False

    def notify_as_failed(self):
        if self.status == SyncTask.FAILED:
            if self._notification_shown:
                return False
            else:
                self._notification_shown = True
                return True

        return False

    def add_progress_callback(self, callback):
        self._progress_updated = callback

    def status_updated(self, count, blockSize, totalSize):
        # We see a different "total size" while downloading,
        # so correct the total size variable in the thread
        if totalSize != self.total_size and totalSize > 0:
            self.total_size = float(totalSize)

        if self.total_size > 0:
            self.progress = max(0.0, min(1.0, float(count*blockSize)/self.total_size))
            self._progress_updated(self.progress)

        if self.status == SyncTask.CANCELLED:
            raise SyncCancelledException()

        if self.status == SyncTask.PAUSED:
            raise SyncCancelledException()

    def recycle(self):
        self.episode.download_task = None

    def run(self):
        # Speed calculation (re-)starts here
        self.__start_time = 0
        self.__start_blocks = 0

        # If the download has already been cancelled, skip it
        if self.status == SyncTask.CANCELLED:
            util.delete_file(self.tempname)
            self.progress = 0.0
            self.speed = 0.0
            return False

        # We only start this download if its status is "queued"
        if self.status != SyncTask.QUEUED:
            return False

        # We are synching this file right now
        self.status = SyncTask.DOWNLOADING
        self._notification_shown = False

        try:
            logger.info('Starting SyncTask')
            self.device.add_track(self.episode, reporthook=self.status_updated)
        except Exception, e:
            self.status = SyncTask.FAILED
            logger.error('Download failed: %s', str(e), exc_info=True)
            self.error_message = _('Error: %s') % (str(e),)

        if self.status == SyncTask.DOWNLOADING:
            # Everything went well - we're done
            self.status = SyncTask.DONE
            if self.total_size <= 0:
                self.total_size = util.calculate_size(self.filename)
                logger.info('Total size updated to %d', self.total_size)
            self.progress = 1.0
            gpodder.user_extensions.on_episode_synced(self.device, self.__episode)
            return True

        self.speed = 0.0

        # We finished, but not successfully (at least not really)
        return False


########NEW FILE########
__FILENAME__ = model
# -*- coding: utf-8 -*-
#
# gPodder - A media aggregator and podcast client
# Copyright (c) 2005-2014 Thomas Perl and the gPodder Team
#
# gPodder is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# gPodder is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#

# gpodder.test.model - Unit tests for gpodder.model
# Thomas Perl <thp@gpodder.org>; 2013-02-12


import unittest

import gpodder

from gpodder import model

class TestEpisodePublishedProperties(unittest.TestCase):
    PUBLISHED_UNIXTIME = 1360666744
    PUBLISHED_SORT = '2013-02-12'
    PUBLISHED_YEAR = '13'
    PUBLISHED_MONTH = '02'
    PUBLISHED_DAY = '12'

    def setUp(self):
        self.podcast = model.PodcastChannel(None)
        self.episode = model.PodcastEpisode(self.podcast)
        self.episode.published = self.PUBLISHED_UNIXTIME

    def test_sortdate(self):
        self.assertEqual(self.episode.sortdate, self.PUBLISHED_SORT)

    def test_pubdate_year(self):
        self.assertEqual(self.episode.pubdate_year, self.PUBLISHED_YEAR)

    def test_pubdate_month(self):
        self.assertEqual(self.episode.pubdate_month, self.PUBLISHED_MONTH)

    def test_pubdate_day(self):
        self.assertEqual(self.episode.pubdate_day, self.PUBLISHED_DAY)


########NEW FILE########
__FILENAME__ = unittests
# -*- coding: utf-8 -*-
#
# gPodder - A media aggregator and podcast client
# Copyright (c) 2005-2014 Thomas Perl and the gPodder Team
#
# gPodder is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# gPodder is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#


# Run Doctests and Unittests for gPodder modules
# 2009-02-25 Thomas Perl <thp@gpodder.org>


import doctest
import unittest
import sys

try:
    # Unused here locally, but we import it to be able to give an early
    # warning about this missing dependency in order to avoid bogus errors.
    import minimock
except ImportError, e:
    print >>sys.stderr, """
    Error: Unit tests require the "minimock" module (python-minimock).
    Please install it before running the unit tests.
    """
    sys.exit(2)

# Main package and test package (for modules in main package)
package = 'gpodder'
test_package = '.'.join((package, 'test'))

suite = unittest.TestSuite()
coverage_modules = []


# Modules (in gpodder) for which doctests exist
# ex: Doctests embedded in "gpodder.util", coverage reported for "gpodder.util"
doctest_modules = ['util', 'jsonconfig']

for module in doctest_modules:
    doctest_mod = __import__('.'.join((package, module)), fromlist=[module])

    suite.addTest(doctest.DocTestSuite(doctest_mod))
    coverage_modules.append(doctest_mod)


# Modules (in gpodder) for which unit tests (in gpodder.test) exist
# ex: Tests are in "gpodder.test.model", coverage reported for "gpodder.model"
test_modules = ['model']

for module in test_modules:
    test_mod = __import__('.'.join((test_package, module)), fromlist=[module])
    coverage_mod = __import__('.'.join((package, module)), fromlist=[module])

    suite.addTest(unittest.defaultTestLoader.loadTestsFromModule(test_mod))
    coverage_modules.append(coverage_mod)

try:
    # If you want a HTML-based test report, install HTMLTestRunner from:
    # http://tungwaiyip.info/software/HTMLTestRunner.html
    import HTMLTestRunner
    REPORT_FILENAME = 'test_report.html'
    runner = HTMLTestRunner.HTMLTestRunner(stream=open(REPORT_FILENAME, 'w'))
    print """
    HTML Test Report will be written to %s
    """ % REPORT_FILENAME
except ImportError:
    runner = unittest.TextTestRunner(verbosity=2)

try:
    import coverage
except ImportError:
    coverage = None

if __name__ == '__main__':
    if coverage is not None:
        coverage.erase()
        coverage.start()

    result = runner.run(suite)

    if not result.wasSuccessful():
        sys.exit(1)

    if coverage is not None:
        coverage.stop()
        coverage.report(coverage_modules)
        coverage.erase()
    else:
        print >>sys.stderr, """
        No coverage reporting done (Python module "coverage" is missing)
        Please install the python-coverage package to get coverage reporting.
        """


########NEW FILE########
__FILENAME__ = util
# -*- coding: utf-8 -*-
#
# gPodder - A media aggregator and podcast client
# Copyright (c) 2005-2014 Thomas Perl and the gPodder Team
# Copyright (c) 2011 Neal H. Walfield
#
# gPodder is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# gPodder is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#

#
#  util.py -- Misc utility functions
#  Thomas Perl <thp@perli.net> 2007-08-04
#

"""Miscellaneous helper functions for gPodder

This module provides helper and utility functions for gPodder that 
are not tied to any specific part of gPodder.

"""

import gpodder

import logging
logger = logging.getLogger(__name__)

import os
import os.path
import platform
import glob
import stat
import shlex
import shutil
import socket
import sys
import string

import re
import subprocess
from htmlentitydefs import entitydefs
import time
import gzip
import datetime
import threading

import urlparse
import urllib
import urllib2
import httplib
import webbrowser
import mimetypes
import itertools

import feedparser

import StringIO
import xml.dom.minidom

if gpodder.ui.win32:
    try:
        import win32file
    except ImportError:
        logger.warn('Running on Win32 but win32api/win32file not installed.')
        win32file = None

_ = gpodder.gettext
N_ = gpodder.ngettext


import locale
try:
    locale.setlocale(locale.LC_ALL, '')
except Exception, e:
    logger.warn('Cannot set locale (%s)', e, exc_info=True)

# Native filesystem encoding detection
encoding = sys.getfilesystemencoding()

if encoding is None:
    if 'LANG' in os.environ and '.' in os.environ['LANG']:
        lang = os.environ['LANG']
        (language, encoding) = lang.rsplit('.', 1)
        logger.info('Detected encoding: %s', encoding)
    elif gpodder.ui.harmattan or gpodder.ui.sailfish:
        encoding = 'utf-8'
    elif gpodder.ui.win32:
        # To quote http://docs.python.org/howto/unicode.html:
        # ,,on Windows, Python uses the name "mbcs" to refer
        #   to whatever the currently configured encoding is``
        encoding = 'mbcs'
    else:
        encoding = 'iso-8859-15'
        logger.info('Assuming encoding: ISO-8859-15 ($LANG not set).')


# Filename / folder name sanitization
def _sanitize_char(c):
    if c in string.whitespace:
        return ' '
    elif c in ',-.()':
        return c
    elif c in string.punctuation or ord(c) <= 31:
        return '_'

    return c

SANITIZATION_TABLE = ''.join(map(_sanitize_char, map(chr, range(256))))
del _sanitize_char

_MIME_TYPE_LIST = [
    ('.aac', 'audio/aac'),
    ('.axa', 'audio/annodex'),
    ('.flac', 'audio/flac'),
    ('.m4b', 'audio/m4b'),
    ('.m4a', 'audio/mp4'),
    ('.mp3', 'audio/mpeg'),
    ('.spx', 'audio/ogg'),
    ('.oga', 'audio/ogg'),
    ('.ogg', 'audio/ogg'),
    ('.wma', 'audio/x-ms-wma'),
    ('.3gp', 'video/3gpp'),
    ('.axv', 'video/annodex'),
    ('.divx', 'video/divx'),
    ('.m4v', 'video/m4v'),
    ('.mp4', 'video/mp4'),
    ('.ogv', 'video/ogg'),
    ('.mov', 'video/quicktime'),
    ('.flv', 'video/x-flv'),
    ('.mkv', 'video/x-matroska'),
    ('.wmv', 'video/x-ms-wmv'),
    ('.opus', 'audio/opus'),
]

_MIME_TYPES = dict((k, v) for v, k in _MIME_TYPE_LIST)
_MIME_TYPES_EXT = dict(_MIME_TYPE_LIST)


def make_directory( path):
    """
    Tries to create a directory if it does not exist already.
    Returns True if the directory exists after the function 
    call, False otherwise.
    """
    if os.path.isdir( path):
        return True

    try:
        os.makedirs( path)
    except:
        logger.warn('Could not create directory: %s', path)
        return False

    return True


def normalize_feed_url(url):
    """
    Converts any URL to http:// or ftp:// so that it can be 
    used with "wget". If the URL cannot be converted (invalid
    or unknown scheme), "None" is returned.

    This will also normalize feed:// and itpc:// to http://.

    >>> normalize_feed_url('itpc://example.org/podcast.rss')
    'http://example.org/podcast.rss'

    If no URL scheme is defined (e.g. "curry.com"), we will
    simply assume the user intends to add a http:// feed.

    >>> normalize_feed_url('curry.com')
    'http://curry.com/'

    There are even some more shortcuts for advanced users
    and lazy typists (see the source for details).

    >>> normalize_feed_url('fb:43FPodcast')
    'http://feeds.feedburner.com/43FPodcast'

    It will also take care of converting the domain name to
    all-lowercase (because domains are not case sensitive):

    >>> normalize_feed_url('http://Example.COM/')
    'http://example.com/'

    Some other minimalistic changes are also taken care of,
    e.g. a ? with an empty query is removed:

    >>> normalize_feed_url('http://example.org/test?')
    'http://example.org/test'
    """
    if not url or len(url) < 8:
        return None

    # This is a list of prefixes that you can use to minimize the amount of
    # keystrokes that you have to use.
    # Feel free to suggest other useful prefixes, and I'll add them here.
    PREFIXES = {
            'fb:': 'http://feeds.feedburner.com/%s',
            'yt:': 'http://www.youtube.com/rss/user/%s/videos.rss',
            'sc:': 'http://soundcloud.com/%s',
            # YouTube playlists. To get a list of playlists per-user, use:
            # https://gdata.youtube.com/feeds/api/users/<username>/playlists
            'ytpl:': 'http://gdata.youtube.com/feeds/api/playlists/%s',
    }

    for prefix, expansion in PREFIXES.iteritems():
        if url.startswith(prefix):
            url = expansion % (url[len(prefix):],)
            break

    # Assume HTTP for URLs without scheme
    if not '://' in url:
        url = 'http://' + url

    scheme, netloc, path, query, fragment = urlparse.urlsplit(url)

    # Schemes and domain names are case insensitive
    scheme, netloc = scheme.lower(), netloc.lower()

    # Normalize empty paths to "/"
    if path == '':
        path = '/'

    # feed://, itpc:// and itms:// are really http://
    if scheme in ('feed', 'itpc', 'itms'):
        scheme = 'http'

    if scheme not in ('http', 'https', 'ftp', 'file'):
        return None

    # urlunsplit might return "a slighty different, but equivalent URL"
    return urlparse.urlunsplit((scheme, netloc, path, query, fragment))


def username_password_from_url(url):
    r"""
    Returns a tuple (username,password) containing authentication
    data from the specified URL or (None,None) if no authentication
    data can be found in the URL.

    See Section 3.1 of RFC 1738 (http://www.ietf.org/rfc/rfc1738.txt)

    >>> username_password_from_url('https://@host.com/')
    ('', None)
    >>> username_password_from_url('telnet://host.com/')
    (None, None)
    >>> username_password_from_url('ftp://foo:@host.com/')
    ('foo', '')
    >>> username_password_from_url('http://a:b@host.com/')
    ('a', 'b')
    >>> username_password_from_url(1)
    Traceback (most recent call last):
      ...
    ValueError: URL has to be a string or unicode object.
    >>> username_password_from_url(None)
    Traceback (most recent call last):
      ...
    ValueError: URL has to be a string or unicode object.
    >>> username_password_from_url('http://a@b:c@host.com/')
    ('a@b', 'c')
    >>> username_password_from_url('ftp://a:b:c@host.com/')
    ('a', 'b:c')
    >>> username_password_from_url('http://i%2Fo:P%40ss%3A@host.com/')
    ('i/o', 'P@ss:')
    >>> username_password_from_url('ftp://%C3%B6sterreich@host.com/')
    ('\xc3\xb6sterreich', None)
    >>> username_password_from_url('http://w%20x:y%20z@example.org/')
    ('w x', 'y z')
    >>> username_password_from_url('http://example.com/x@y:z@test.com/')
    (None, None)
    """
    if type(url) not in (str, unicode):
        raise ValueError('URL has to be a string or unicode object.')

    (username, password) = (None, None)

    (scheme, netloc, path, params, query, fragment) = urlparse.urlparse(url)

    if '@' in netloc:
        (authentication, netloc) = netloc.rsplit('@', 1)
        if ':' in authentication:
            (username, password) = authentication.split(':', 1)

            # RFC1738 dictates that we should not allow ['/', '@', ':']
            # characters in the username and password field (Section 3.1):
            #
            # 1. The "/" can't be in there at this point because of the way
            #    urlparse (which we use above) works.
            # 2. Due to gPodder bug 1521, we allow "@" in the username and
            #    password field. We use netloc.rsplit('@', 1), which will
            #    make sure that we split it at the last '@' in netloc.
            # 3. The colon must be excluded (RFC2617, Section 2) in the
            #    username, but is apparently allowed in the password. This
            #    is handled by the authentication.split(':', 1) above, and
            #    will cause any extraneous ':'s to be part of the password.

            username = urllib.unquote(username)
            password = urllib.unquote(password)
        else:
            username = urllib.unquote(authentication)

    return (username, password)

def directory_is_writable(path):
    """
    Returns True if the specified directory exists and is writable
    by the current user.
    """
    return os.path.isdir(path) and os.access(path, os.W_OK)


def calculate_size( path):
    """
    Tries to calculate the size of a directory, including any 
    subdirectories found. The returned value might not be 
    correct if the user doesn't have appropriate permissions 
    to list all subdirectories of the given path.
    """
    if path is None:
        return 0L

    if os.path.dirname( path) == '/':
        return 0L

    if os.path.isfile( path):
        return os.path.getsize( path)

    if os.path.isdir( path) and not os.path.islink( path):
        sum = os.path.getsize( path)

        try:
            for item in os.listdir(path):
                try:
                    sum += calculate_size(os.path.join(path, item))
                except:
                    logger.warn('Cannot get size for %s', path, exc_info=True)
        except:
            logger.warn('Cannot access %s', path, exc_info=True)

        return sum

    return 0L


def file_modification_datetime(filename):
    """
    Returns the modification date of the specified file
    as a datetime.datetime object or None if the modification
    date cannot be determined.
    """
    if filename is None:
        return None

    if not os.access(filename, os.R_OK):
        return None

    try:
        s = os.stat(filename)
        timestamp = s[stat.ST_MTIME]
        return datetime.datetime.fromtimestamp(timestamp)
    except:
        logger.warn('Cannot get mtime for %s', filename, exc_info=True)
        return None


def file_age_in_days(filename):
    """
    Returns the age of the specified filename in days or
    zero if the modification date cannot be determined.
    """
    dt = file_modification_datetime(filename)
    if dt is None:
        return 0
    else:
        return (datetime.datetime.now()-dt).days

def file_modification_timestamp(filename):
    """
    Returns the modification date of the specified file as a number
    or -1 if the modification date cannot be determined.
    """
    if filename is None:
        return -1
    try:
        s = os.stat(filename)
        return s[stat.ST_MTIME]
    except:
        logger.warn('Cannot get modification timestamp for %s', filename)
        return -1


def file_age_to_string(days):
    """
    Converts a "number of days" value to a string that
    can be used in the UI to display the file age.

    >>> file_age_to_string(0)
    ''
    >>> file_age_to_string(1)
    u'1 day ago'
    >>> file_age_to_string(2)
    u'2 days ago'
    """
    if days < 1:
        return ''
    else:
        return N_('%(count)d day ago', '%(count)d days ago', days) % {'count':days}


def is_system_file(filename):
    """
    Checks to see if the given file is a system file.
    """
    if gpodder.ui.win32 and win32file is not None:
        result = win32file.GetFileAttributes(filename)
        #-1 is returned by GetFileAttributes when an error occurs
        #0x4 is the FILE_ATTRIBUTE_SYSTEM constant
        return result != -1 and result & 0x4 != 0
    else:
        return False


def get_free_disk_space_win32(path):
    """
    Win32-specific code to determine the free disk space remaining
    for a given path. Uses code from:

    http://mail.python.org/pipermail/python-list/2003-May/203223.html
    """
    if win32file is None:
        # Cannot determine free disk space
        return 0

    drive, tail = os.path.splitdrive(path)
    userFree, userTotal, freeOnDisk = win32file.GetDiskFreeSpaceEx(drive)
    return userFree


def get_free_disk_space(path):
    """
    Calculates the free disk space available to the current user
    on the file system that contains the given path.

    If the path (or its parent folder) does not yet exist, this
    function returns zero.
    """

    if not os.path.exists(path):
        return 0

    if gpodder.ui.win32:
        return get_free_disk_space_win32(path)

    s = os.statvfs(path)

    return s.f_bavail * s.f_bsize


def format_date(timestamp):
    """
    Converts a UNIX timestamp to a date representation. This
    function returns "Today", "Yesterday", a weekday name or
    the date in %x format, which (according to the Python docs)
    is the "Locale's appropriate date representation".

    Returns None if there has been an error converting the
    timestamp to a string representation.
    """
    if timestamp is None:
        return None

    seconds_in_a_day = 60*60*24

    today = time.localtime()[:3]
    yesterday = time.localtime(time.time() - seconds_in_a_day)[:3]
    try:
        timestamp_date = time.localtime(timestamp)[:3]
    except ValueError, ve:
        logger.warn('Cannot convert timestamp', exc_info=True)
        return None
    
    if timestamp_date == today:
       return _('Today')
    elif timestamp_date == yesterday:
       return _('Yesterday')
   
    try:
        diff = int( (time.time() - timestamp)/seconds_in_a_day )
    except:
        logger.warn('Cannot convert "%s" to date.', timestamp, exc_info=True)
        return None

    try:
        timestamp = datetime.datetime.fromtimestamp(timestamp)
    except:
        return None

    if diff < 7:
        # Weekday name
        return str(timestamp.strftime('%A').decode(encoding))
    else:
        # Locale's appropriate date representation
        return str(timestamp.strftime('%x'))


def format_filesize(bytesize, use_si_units=False, digits=2):
    """
    Formats the given size in bytes to be human-readable, 

    Returns a localized "(unknown)" string when the bytesize
    has a negative value.
    """
    si_units = (
            ( 'kB', 10**3 ),
            ( 'MB', 10**6 ),
            ( 'GB', 10**9 ),
    )

    binary_units = (
            ( 'KiB', 2**10 ),
            ( 'MiB', 2**20 ),
            ( 'GiB', 2**30 ),
    )

    try:
        bytesize = float( bytesize)
    except:
        return _('(unknown)')

    if bytesize < 0:
        return _('(unknown)')

    if use_si_units:
        units = si_units
    else:
        units = binary_units

    ( used_unit, used_value ) = ( 'B', bytesize )

    for ( unit, value ) in units:
        if bytesize >= value:
            used_value = bytesize / float(value)
            used_unit = unit

    return ('%.'+str(digits)+'f %s') % (used_value, used_unit)


def delete_file(filename):
    """Delete a file from the filesystem

    Errors (permissions errors or file not found)
    are silently ignored.
    """
    try:
        os.remove(filename)
    except:
        pass


def remove_html_tags(html):
    """
    Remove HTML tags from a string and replace numeric and
    named entities with the corresponding character, so the 
    HTML text can be displayed in a simple text view.
    """
    if html is None:
        return None

    # If we would want more speed, we could make these global
    re_strip_tags = re.compile('<[^>]*>')
    re_unicode_entities = re.compile('&#(\d{2,4});')
    re_html_entities = re.compile('&(.{2,8});')
    re_newline_tags = re.compile('(<br[^>]*>|<[/]?ul[^>]*>|</li>)', re.I)
    re_listing_tags = re.compile('<li[^>]*>', re.I)

    result = html
    
    # Convert common HTML elements to their text equivalent
    result = re_newline_tags.sub('\n', result)
    result = re_listing_tags.sub('\n * ', result)
    result = re.sub('<[Pp]>', '\n\n', result)

    # Remove all HTML/XML tags from the string
    result = re_strip_tags.sub('', result)

    # Convert numeric XML entities to their unicode character
    result = re_unicode_entities.sub(lambda x: unichr(int(x.group(1))), result)

    # Convert named HTML entities to their unicode character
    result = re_html_entities.sub(lambda x: unicode(entitydefs.get(x.group(1),''), 'iso-8859-1'), result)
    
    # Convert more than two newlines to two newlines
    result = re.sub('([\r\n]{2})([\r\n])+', '\\1', result)

    return result.strip()


def wrong_extension(extension):
    """
    Determine if a given extension looks like it's
    wrong (e.g. empty, extremely long or spaces)

    Returns True if the extension most likely is a
    wrong one and should be replaced.

    >>> wrong_extension('.mp3')
    False
    >>> wrong_extension('.divx')
    False
    >>> wrong_extension('mp3')
    True
    >>> wrong_extension('')
    True
    >>> wrong_extension('.12 - Everybody')
    True
    >>> wrong_extension('.mp3 ')
    True
    >>> wrong_extension('.')
    True
    >>> wrong_extension('.42')
    True
    """
    if not extension:
        return True
    elif len(extension) > 5:
        return True
    elif ' ' in extension:
        return True
    elif extension == '.':
        return True
    elif not extension.startswith('.'):
        return True
    else:
        try:
            # ".<number>" is an invalid extension
            float(extension)
            return True
        except:
            pass

    return False


def extension_from_mimetype(mimetype):
    """
    Simply guesses what the file extension should be from the mimetype

    >>> extension_from_mimetype('audio/mp4')
    '.m4a'
    >>> extension_from_mimetype('audio/ogg')
    '.ogg'
    >>> extension_from_mimetype('audio/mpeg')
    '.mp3'
    >>> extension_from_mimetype('video/x-matroska')
    '.mkv'
    >>> extension_from_mimetype('wrong-mimetype')
    ''
    """
    if mimetype in _MIME_TYPES:
        return _MIME_TYPES[mimetype]
    return mimetypes.guess_extension(mimetype) or ''


def mimetype_from_extension(extension):
    """
    Simply guesses what the mimetype should be from the file extension

    >>> mimetype_from_extension('.m4a')
    'audio/mp4'
    >>> mimetype_from_extension('.ogg')
    'audio/ogg'
    >>> mimetype_from_extension('.mp3')
    'audio/mpeg'
    >>> mimetype_from_extension('.mkv')
    'video/x-matroska'
    >>> mimetype_from_extension('._invalid_file_extension_')
    ''
    """
    if extension in _MIME_TYPES_EXT:
        return _MIME_TYPES_EXT[extension]

    # Need to prepend something to the extension, so guess_type works
    type, encoding = mimetypes.guess_type('file'+extension)

    return type or ''


def extension_correct_for_mimetype(extension, mimetype):
    """
    Check if the given filename extension (e.g. ".ogg") is a possible
    extension for a given mimetype (e.g. "application/ogg") and return
    a boolean value (True if it's possible, False if not). Also do

    >>> extension_correct_for_mimetype('.ogg', 'application/ogg')
    True
    >>> extension_correct_for_mimetype('.ogv', 'video/ogg')
    True
    >>> extension_correct_for_mimetype('.ogg', 'audio/mpeg')
    False
    >>> extension_correct_for_mimetype('.m4a', 'audio/mp4')
    True
    >>> extension_correct_for_mimetype('mp3', 'audio/mpeg')
    Traceback (most recent call last):
      ...
    ValueError: "mp3" is not an extension (missing .)
    >>> extension_correct_for_mimetype('.mp3', 'audio mpeg')
    Traceback (most recent call last):
      ...
    ValueError: "audio mpeg" is not a mimetype (missing /)
    """
    if not '/' in mimetype:
        raise ValueError('"%s" is not a mimetype (missing /)' % mimetype)
    if not extension.startswith('.'):
        raise ValueError('"%s" is not an extension (missing .)' % extension)

    if (extension, mimetype) in _MIME_TYPE_LIST:
        return True

    # Create a "default" extension from the mimetype, e.g. "application/ogg"
    # becomes ".ogg", "audio/mpeg" becomes ".mpeg", etc...
    default = ['.'+mimetype.split('/')[-1]]

    return extension in default+mimetypes.guess_all_extensions(mimetype)


def filename_from_url(url):
    """
    Extracts the filename and (lowercase) extension (with dot)
    from a URL, e.g. http://server.com/file.MP3?download=yes
    will result in the string ("file", ".mp3") being returned.

    This function will also try to best-guess the "real" 
    extension for a media file (audio, video) by
    trying to match an extension to these types and recurse
    into the query string to find better matches, if the 
    original extension does not resolve to a known type.

    http://my.net/redirect.php?my.net/file.ogg => ("file", ".ogg")
    http://server/get.jsp?file=/episode0815.MOV => ("episode0815", ".mov")
    http://s/redirect.mp4?http://serv2/test.mp4 => ("test", ".mp4")
    """
    (scheme, netloc, path, para, query, fragid) = urlparse.urlparse(url)
    (filename, extension) = os.path.splitext(os.path.basename( urllib.unquote(path)))

    if file_type_by_extension(extension) is not None and not \
        query.startswith(scheme+'://'):
        # We have found a valid extension (audio, video)
        # and the query string doesn't look like a URL
        return ( filename, extension.lower() )

    # If the query string looks like a possible URL, try that first
    if len(query.strip()) > 0 and query.find('/') != -1:
        query_url = '://'.join((scheme, urllib.unquote(query)))
        (query_filename, query_extension) = filename_from_url(query_url)

        if file_type_by_extension(query_extension) is not None:
            return os.path.splitext(os.path.basename(query_url))

    # No exact match found, simply return the original filename & extension
    return ( filename, extension.lower() )


def file_type_by_extension(extension):
    """
    Tries to guess the file type by looking up the filename 
    extension from a table of known file types. Will return 
    "audio", "video" or None.

    >>> file_type_by_extension('.aif')
    'audio'
    >>> file_type_by_extension('.3GP')
    'video'
    >>> file_type_by_extension('.m4a')
    'audio'
    >>> file_type_by_extension('.txt') is None
    True
    >>> file_type_by_extension(None) is None
    True
    >>> file_type_by_extension('ogg')
    Traceback (most recent call last):
      ...
    ValueError: Extension does not start with a dot: ogg
    """
    if not extension:
        return None

    if not extension.startswith('.'):
        raise ValueError('Extension does not start with a dot: %s' % extension)

    extension = extension.lower()

    if extension in _MIME_TYPES_EXT:
        return _MIME_TYPES_EXT[extension].split('/')[0]

    # Need to prepend something to the extension, so guess_type works
    type, encoding = mimetypes.guess_type('file'+extension)

    if type is not None and '/' in type:
        filetype, rest = type.split('/', 1)
        if filetype in ('audio', 'video', 'image'):
            return filetype
    
    return None


def get_first_line( s):
    """
    Returns only the first line of a string, stripped so
    that it doesn't have whitespace before or after.
    """
    return s.strip().split('\n')[0].strip()


def object_string_formatter(s, **kwargs):
    """
    Makes attributes of object passed in as keyword
    arguments available as {OBJECTNAME.ATTRNAME} in
    the passed-in string and returns a string with
    the above arguments replaced with the attribute
    values of the corresponding object.

    >>> class x: pass
    >>> a = x()
    >>> a.title = 'Hello world'
    >>> object_string_formatter('{episode.title}', episode=a)
    'Hello world'

    >>> class x: pass
    >>> a = x()
    >>> a.published = 123
    >>> object_string_formatter('Hi {episode.published} 456', episode=a)
    'Hi 123 456'
    """
    result = s
    for key, o in kwargs.iteritems():
        matches = re.findall(r'\{%s\.([^\}]+)\}' % key, s)
        for attr in matches:
            if hasattr(o, attr):
                try:
                    from_s = '{%s.%s}' % (key, attr)
                    to_s = str(getattr(o, attr))
                    result = result.replace(from_s, to_s)
                except:
                    logger.warn('Replace of "%s" failed for "%s".', attr, s)

    return result


def format_desktop_command(command, filenames, start_position=None):
    """
    Formats a command template from the "Exec=" line of a .desktop
    file to a string that can be invoked in a shell.

    Handled format strings: %U, %u, %F, %f and a fallback that
    appends the filename as first parameter of the command.

    Also handles non-standard %p which is replaced with the start_position
    (probably only makes sense if starting a single file). (see bug 1140)

    See http://standards.freedesktop.org/desktop-entry-spec/1.0/ar01s06.html

    Returns a list of commands to execute, either one for
    each filename if the application does not support multiple
    file names or one for all filenames (%U, %F or unknown).
    """
    # Replace backslashes with slashes to fix win32 issues
    # (even on win32, "/" works, but "\" does not)
    command = command.replace('\\', '/')

    if start_position is not None:
        command = command.replace('%p', str(start_position))

    command = shlex.split(command)

    command_before = command
    command_after = []
    multiple_arguments = True
    for fieldcode in ('%U', '%F', '%u', '%f'):
        if fieldcode in command:
            command_before = command[:command.index(fieldcode)]
            command_after = command[command.index(fieldcode)+1:]
            multiple_arguments = fieldcode in ('%U', '%F')
            break

    if multiple_arguments:
        return [command_before + filenames + command_after]

    commands = []
    for filename in filenames:
        commands.append(command_before+[filename]+command_after)

    return commands

def url_strip_authentication(url):
    """
    Strips authentication data from an URL. Returns the URL with
    the authentication data removed from it.

    >>> url_strip_authentication('https://host.com/')
    'https://host.com/'
    >>> url_strip_authentication('telnet://foo:bar@host.com/')
    'telnet://host.com/'
    >>> url_strip_authentication('ftp://billy@example.org')
    'ftp://example.org'
    >>> url_strip_authentication('ftp://billy:@example.org')
    'ftp://example.org'
    >>> url_strip_authentication('http://aa:bc@localhost/x')
    'http://localhost/x'
    >>> url_strip_authentication('http://i%2Fo:P%40ss%3A@blubb.lan/u.html')
    'http://blubb.lan/u.html'
    >>> url_strip_authentication('http://c:d@x.org/')
    'http://x.org/'
    >>> url_strip_authentication('http://P%40%3A:i%2F@cx.lan')
    'http://cx.lan'
    >>> url_strip_authentication('http://x@x.com:s3cret@example.com/')
    'http://example.com/'
    """
    url_parts = list(urlparse.urlsplit(url))
    # url_parts[1] is the HOST part of the URL

    # Remove existing authentication data
    if '@' in url_parts[1]:
        url_parts[1] = url_parts[1].rsplit('@', 1)[1]

    return urlparse.urlunsplit(url_parts)


def url_add_authentication(url, username, password):
    """
    Adds authentication data (username, password) to a given
    URL in order to construct an authenticated URL.

    >>> url_add_authentication('https://host.com/', '', None)
    'https://host.com/'
    >>> url_add_authentication('http://example.org/', None, None)
    'http://example.org/'
    >>> url_add_authentication('telnet://host.com/', 'foo', 'bar')
    'telnet://foo:bar@host.com/'
    >>> url_add_authentication('ftp://example.org', 'billy', None)
    'ftp://billy@example.org'
    >>> url_add_authentication('ftp://example.org', 'billy', '')
    'ftp://billy:@example.org'
    >>> url_add_authentication('http://localhost/x', 'aa', 'bc')
    'http://aa:bc@localhost/x'
    >>> url_add_authentication('http://blubb.lan/u.html', 'i/o', 'P@ss:')
    'http://i%2Fo:P@ss:@blubb.lan/u.html'
    >>> url_add_authentication('http://a:b@x.org/', 'c', 'd')
    'http://c:d@x.org/'
    >>> url_add_authentication('http://i%2F:P%40%3A@cx.lan', 'P@x', 'i/')
    'http://P@x:i%2F@cx.lan'
    >>> url_add_authentication('http://x.org/', 'a b', 'c d')
    'http://a%20b:c%20d@x.org/'
    """
    if username is None or username == '':
        return url

    # Relaxations of the strict quoting rules (bug 1521):
    # 1. Accept '@' in username and password
    # 2. Acecpt ':' in password only
    username = urllib.quote(username, safe='@')

    if password is not None:
        password = urllib.quote(password, safe='@:')
        auth_string = ':'.join((username, password))
    else:
        auth_string = username

    url = url_strip_authentication(url)

    url_parts = list(urlparse.urlsplit(url))
    # url_parts[1] is the HOST part of the URL
    url_parts[1] = '@'.join((auth_string, url_parts[1]))

    return urlparse.urlunsplit(url_parts)


def urlopen(url, headers=None, data=None, timeout=None):
    """
    An URL opener with the User-agent set to gPodder (with version)
    """
    username, password = username_password_from_url(url)
    if username is not None or password is not None:
        url = url_strip_authentication(url)
        password_mgr = urllib2.HTTPPasswordMgrWithDefaultRealm()
        password_mgr.add_password(None, url, username, password)
        handler = urllib2.HTTPBasicAuthHandler(password_mgr)
        opener = urllib2.build_opener(handler)
    else:
        opener = urllib2.build_opener()

    if headers is None:
        headers = {}
    else:
        headers = dict(headers)

    headers.update({'User-agent': gpodder.user_agent})
    request = urllib2.Request(url, data=data, headers=headers)
    if timeout is None:
        return opener.open(request)
    else:
        return opener.open(request, timeout=timeout)

def get_real_url(url):
    """
    Gets the real URL of a file and resolves all redirects.
    """
    try:
        return urlopen(url).geturl()
    except:
        logger.error('Getting real url for %s', url, exc_info=True)
        return url


def find_command(command):
    """
    Searches the system's PATH for a specific command that is
    executable by the user. Returns the first occurence of an
    executable binary in the PATH, or None if the command is
    not available.

    On Windows, this also looks for "<command>.bat" and
    "<command>.exe" files if "<command>" itself doesn't exist.
    """

    if 'PATH' not in os.environ:
        return None

    for path in os.environ['PATH'].split(os.pathsep):
        command_file = os.path.join(path, command)
        if gpodder.ui.win32 and not os.path.exists(command_file):
            for extension in ('.bat', '.exe'):
                cmd = command_file + extension
                if os.path.isfile(cmd):
                    command_file = cmd
                    break
        if os.path.isfile(command_file) and os.access(command_file, os.X_OK):
            return command_file

    return None

idle_add_handler = None

def idle_add(func, *args):
    """Run a function in the main GUI thread

    This is a wrapper function that does the Right Thing depending on if we are
    running on Gtk+, Qt or CLI.

    You should use this function if you are calling from a Python thread and
    modify UI data, so that you make sure that the function is called as soon
    as possible from the main UI thread.
    """
    if gpodder.ui.gtk:
        import gobject
        gobject.idle_add(func, *args)
    elif gpodder.ui.qml:
        from PySide.QtCore import Signal, QTimer, QThread, Qt, QObject

        class IdleAddHandler(QObject):
            signal = Signal(object)
            def __init__(self):
                QObject.__init__(self)

                self.main_thread_id = QThread.currentThreadId()

                self.signal.connect(self.run_func)

            def run_func(self, func):
                assert QThread.currentThreadId() == self.main_thread_id, \
                    ("Running in %s, not %s"
                     % (str(QThread.currentThreadId()),
                        str(self.main_thread_id)))
                func()

            def idle_add(self, func, *args):
                def doit():
                    try:
                        func(*args)
                    except Exception, e:
                        logger.exception("Running %s%s: %s",
                                         func, str(tuple(args)), str(e))

                if QThread.currentThreadId() == self.main_thread_id:
                    # If we emit the signal in the main thread,
                    # then the function will be run immediately.
                    # Instead, use a single shot timer with a 0
                    # timeout: this will run the function when the
                    # event loop next iterates.
                    QTimer.singleShot(0, doit)
                else:
                    self.signal.emit(doit)

        global idle_add_handler
        if idle_add_handler is None:
            idle_add_handler = IdleAddHandler()

        idle_add_handler.idle_add(func, *args)
    else:
        func(*args)


def bluetooth_available():
    """
    Returns True or False depending on the availability
    of bluetooth functionality on the system.
    """
    if find_command('bluetooth-sendto') or \
            find_command('gnome-obex-send'):
        return True
    else:
        return False


def bluetooth_send_file(filename):
    """
    Sends a file via bluetooth.

    This function tries to use "bluetooth-sendto", and if
    it is not available, it also tries "gnome-obex-send".
    """
    command_line = None

    if find_command('bluetooth-sendto'):
        command_line = ['bluetooth-sendto']
    elif find_command('gnome-obex-send'):
        command_line = ['gnome-obex-send']

    if command_line is not None:
        command_line.append(filename)
        return (subprocess.Popen(command_line).wait() == 0)
    else:
        logger.error('Cannot send file. Please install "bluetooth-sendto" or "gnome-obex-send".')
        return False


def format_time(value):
    """Format a seconds value to a string

    >>> format_time(0)
    '00:00'
    >>> format_time(20)
    '00:20'
    >>> format_time(3600)
    '01:00:00'
    >>> format_time(10921)
    '03:02:01'
    """
    dt = datetime.datetime.utcfromtimestamp(value)
    if dt.hour == 0:
        return dt.strftime('%M:%S')
    else:
        return dt.strftime('%H:%M:%S')

def parse_time(value):
    """Parse a time string into seconds

    >>> parse_time('00:00')
    0
    >>> parse_time('00:00:00')
    0
    >>> parse_time('00:20')
    20
    >>> parse_time('00:00:20')
    20
    >>> parse_time('01:00:00')
    3600
    >>> parse_time('03:02:01')
    10921
    >>> parse_time('61:08')
    3668
    >>> parse_time('25:03:30')
    90210
    >>> parse_time('25:3:30')
    90210
    >>> parse_time('61.08')
    3668
    """
    if value == '':
        return 0

    if not value:
        raise ValueError('Invalid value: %s' % (str(value),))

    m = re.match(r'(\d+)[:.](\d\d?)[:.](\d\d?)', value)
    if m:
        hours, minutes, seconds = m.groups()
        return (int(hours) * 60 + int(minutes)) * 60 + int(seconds)

    m = re.match(r'(\d+)[:.](\d\d?)', value)
    if m:
        minutes, seconds = m.groups()
        return int(minutes) * 60 + int(seconds)

    return int(value)


def format_seconds_to_hour_min_sec(seconds):
    """
    Take the number of seconds and format it into a
    human-readable string (duration).

    >>> format_seconds_to_hour_min_sec(3834)
    u'1 hour, 3 minutes and 54 seconds'
    >>> format_seconds_to_hour_min_sec(3600)
    u'1 hour'
    >>> format_seconds_to_hour_min_sec(62)
    u'1 minute and 2 seconds'
    """

    if seconds < 1:
        return N_('%(count)d second', '%(count)d seconds', seconds) % {'count':seconds}

    result = []

    seconds = int(seconds)

    hours = seconds/3600
    seconds = seconds%3600

    minutes = seconds/60
    seconds = seconds%60

    if hours:
        result.append(N_('%(count)d hour', '%(count)d hours', hours) % {'count':hours})

    if minutes:
        result.append(N_('%(count)d minute', '%(count)d minutes', minutes) % {'count':minutes})

    if seconds:
        result.append(N_('%(count)d second', '%(count)d seconds', seconds) % {'count':seconds})

    if len(result) > 1:
        return (' '+_('and')+' ').join((', '.join(result[:-1]), result[-1]))
    else:
        return result[0]

def http_request(url, method='HEAD'):
    (scheme, netloc, path, parms, qry, fragid) = urlparse.urlparse(url)
    conn = httplib.HTTPConnection(netloc)
    start = len(scheme) + len('://') + len(netloc)
    conn.request(method, url[start:])
    return conn.getresponse()


def gui_open(filename):
    """
    Open a file or folder with the default application set
    by the Desktop environment. This uses "xdg-open" on all
    systems with a few exceptions:

       on Win32, os.startfile() is used
    """
    try:
        if gpodder.ui.win32:
            os.startfile(filename)
        elif gpodder.ui.osx:
            subprocess.Popen(['open', filename])
        else:
            subprocess.Popen(['xdg-open', filename])
        return True
    except:
        logger.error('Cannot open file/folder: "%s"', filename, exc_info=True)
        return False


def open_website(url):
    """
    Opens the specified URL using the default system web
    browser. This uses Python's "webbrowser" module, so
    make sure your system is set up correctly.
    """
    run_in_background(lambda: webbrowser.open(url))

def convert_bytes(d):
    """
    Convert byte strings to unicode strings

    This function will decode byte strings into unicode
    strings. Any other data types will be left alone.

    >>> convert_bytes(None)
    >>> convert_bytes(1)
    1
    >>> convert_bytes(4711L)
    4711L
    >>> convert_bytes(True)
    True
    >>> convert_bytes(3.1415)
    3.1415
    >>> convert_bytes('Hello')
    u'Hello'
    >>> convert_bytes(u'Hey')
    u'Hey'
    """
    if d is None:
        return d
    if any(isinstance(d, t) for t in (int, long, bool, float)):
        return d
    elif not isinstance(d, unicode):
        return d.decode('utf-8', 'ignore')
    return d

def sanitize_encoding(filename):
    r"""
    Generate a sanitized version of a string (i.e.
    remove invalid characters and encode in the
    detected native language encoding).

    >>> sanitize_encoding('\x80')
    ''
    >>> sanitize_encoding(u'unicode')
    'unicode'
    """
    # The encoding problem goes away in Python 3.. hopefully!
    if sys.version_info >= (3, 0):
        return filename

    global encoding
    if not isinstance(filename, unicode):
        filename = filename.decode(encoding, 'ignore')
    return filename.encode(encoding, 'ignore')


def sanitize_filename(filename, max_length=0, use_ascii=False):
    """
    Generate a sanitized version of a filename that can
    be written on disk (i.e. remove/replace invalid
    characters and encode in the native language) and
    trim filename if greater than max_length (0 = no limit).

    If use_ascii is True, don't encode in the native language,
    but use only characters from the ASCII character set.
    """
    if not isinstance(filename, unicode):
        filename = filename.decode(encoding, 'ignore')

    if max_length > 0 and len(filename) > max_length:
        logger.info('Limiting file/folder name "%s" to %d characters.',
                filename, max_length)
        filename = filename[:max_length]

    filename = filename.encode('ascii' if use_ascii else encoding, 'ignore')
    filename = filename.translate(SANITIZATION_TABLE)
    filename = filename.strip('.' + string.whitespace)

    return filename


def find_mount_point(directory):
    """
    Try to find the mount point for a given directory.
    If the directory is itself a mount point, return
    it. If not, remove the last part of the path and
    re-check if it's a mount point. If the directory
    resides on your root filesystem, "/" is returned.

    >>> find_mount_point('/')
    '/'

    >>> find_mount_point(u'/something')
    Traceback (most recent call last):
      ...
    ValueError: Convert unicode objects to str first.

    >>> find_mount_point(None)
    Traceback (most recent call last):
      ...
    ValueError: Directory names should be of type str.

    >>> find_mount_point(42)
    Traceback (most recent call last):
      ...
    ValueError: Directory names should be of type str.

    >>> from minimock import mock, restore
    >>> mocked_mntpoints = ('/', '/home', '/media/usbdisk', '/media/cdrom')
    >>> mock('os.path.ismount', returns_func=lambda x: x in mocked_mntpoints)
    >>>
    >>> # For mocking os.getcwd(), we simply use a lambda to avoid the
    >>> # massive output of "Called os.getcwd()" lines in this doctest
    >>> os.getcwd = lambda: '/home/thp'
    >>>
    >>> find_mount_point('.')
    Called os.path.ismount('/home/thp')
    Called os.path.ismount('/home')
    '/home'
    >>> find_mount_point('relativity')
    Called os.path.ismount('/home/thp/relativity')
    Called os.path.ismount('/home/thp')
    Called os.path.ismount('/home')
    '/home'
    >>> find_mount_point('/media/usbdisk/')
    Called os.path.ismount('/media/usbdisk')
    '/media/usbdisk'
    >>> find_mount_point('/home/thp/Desktop')
    Called os.path.ismount('/home/thp/Desktop')
    Called os.path.ismount('/home/thp')
    Called os.path.ismount('/home')
    '/home'
    >>> find_mount_point('/media/usbdisk/Podcasts/With Spaces')
    Called os.path.ismount('/media/usbdisk/Podcasts/With Spaces')
    Called os.path.ismount('/media/usbdisk/Podcasts')
    Called os.path.ismount('/media/usbdisk')
    '/media/usbdisk'
    >>> find_mount_point('/home/')
    Called os.path.ismount('/home')
    '/home'
    >>> find_mount_point('/media/cdrom/../usbdisk/blubb//')
    Called os.path.ismount('/media/usbdisk/blubb')
    Called os.path.ismount('/media/usbdisk')
    '/media/usbdisk'
    >>> restore()
    """
    if isinstance(directory, unicode):
        # XXX: This is only valid for Python 2 - misleading error in Python 3?
        # We do not accept unicode strings, because they could fail when
        # trying to be converted to some native encoding, so fail loudly
        # and leave it up to the callee to encode into the proper encoding.
        raise ValueError('Convert unicode objects to str first.')

    if not isinstance(directory, str):
        # In Python 2, we assume it's a byte str; in Python 3, we assume
        # that it's a unicode str. The abspath/ismount/split functions of
        # os.path work with unicode str in Python 3, but not in Python 2.
        raise ValueError('Directory names should be of type str.')

    directory = os.path.abspath(directory)

    while directory != '/':
        if os.path.ismount(directory):
            return directory
        else:
            (directory, tail_data) = os.path.split(directory)

    return '/'


# matches http:// and ftp:// and mailto://
protocolPattern = re.compile(r'^\w+://')

def isabs(string):
    """
    @return true if string is an absolute path or protocoladdress
    for addresses beginning in http:// or ftp:// or ldap:// -
    they are considered "absolute" paths.
    Source: http://code.activestate.com/recipes/208993/
    """
    if protocolPattern.match(string): return 1
    return os.path.isabs(string)


def commonpath(l1, l2, common=[]):
    """
    helper functions for relpath
    Source: http://code.activestate.com/recipes/208993/
    """
    if len(l1) < 1: return (common, l1, l2)
    if len(l2) < 1: return (common, l1, l2)
    if l1[0] != l2[0]: return (common, l1, l2)
    return commonpath(l1[1:], l2[1:], common+[l1[0]])

def relpath(p1, p2):
    """
    Finds relative path from p1 to p2
    Source: http://code.activestate.com/recipes/208993/
    """
    pathsplit = lambda s: s.split(os.path.sep)

    (common,l1,l2) = commonpath(pathsplit(p1), pathsplit(p2))
    p = []
    if len(l1) > 0:
        p = [ ('..'+os.sep) * len(l1) ]
    p = p + l2
    if len(p) is 0:
        return "."

    return os.path.join(*p)


def get_hostname():
    """Return the hostname of this computer

    This can be implemented in a different way on each
    platform and should yield a unique-per-user device ID.
    """
    nodename = platform.node()

    if nodename:
        return nodename

    # Fallback - but can this give us "localhost"?
    return socket.gethostname()

def detect_device_type():
    """Device type detection for gpodder.net

    This function tries to detect on which
    kind of device gPodder is running on.

    Possible return values:
    desktop, laptop, mobile, server, other
    """
    if gpodder.ui.harmattan or gpodder.ui.sailfish:
        return 'mobile'
    elif glob.glob('/proc/acpi/battery/*'):
        # Linux: If we have a battery, assume Laptop
        return 'laptop'

    return 'desktop'


def write_m3u_playlist(m3u_filename, episodes, extm3u=True):
    """Create an M3U playlist from a episode list

    If the parameter "extm3u" is False, the list of
    episodes should be a list of filenames, and no
    extended information will be written into the
    M3U files (#EXTM3U / #EXTINF).

    If the parameter "extm3u" is True (default), then the
    list of episodes should be PodcastEpisode objects,
    as the extended metadata will be taken from them.
    """
    f = open(m3u_filename, 'w')

    if extm3u:
        # Mandatory header for extended playlists
        f.write('#EXTM3U\n')

    for episode in episodes:
        if not extm3u:
            # Episode objects are strings that contain file names
            f.write(episode+'\n')
            continue

        if episode.was_downloaded(and_exists=True):
            filename = episode.local_filename(create=False)
            assert filename is not None

            if os.path.dirname(filename).startswith(os.path.dirname(m3u_filename)):
                filename = filename[len(os.path.dirname(m3u_filename)+os.sep):]
            f.write('#EXTINF:0,'+episode.playlist_title()+'\n')
            f.write(filename+'\n')

    f.close()


def generate_names(filename):
    basename, ext = os.path.splitext(filename)
    for i in itertools.count():
        if i:
            yield '%s (%d)%s' % (basename, i+1, ext)
        else:
            yield filename


def is_known_redirecter(url):
    """Check if a URL redirect is expected, and no filenames should be updated

    We usually honor URL redirects, and update filenames accordingly.
    In some cases (e.g. Soundcloud) this results in a worse filename,
    so we hardcode and detect these cases here to avoid renaming files
    for which we know that a "known good default" exists.

    The problem here is that by comparing the currently-assigned filename
    with the new filename determined by the URL, we cannot really determine
    which one is the "better" URL (e.g. "n5rMSpXrqmR9.128.mp3" for Soundcloud).
    """

    # Soundcloud-hosted media downloads (we take the track name as filename)
    if url.startswith('http://ak-media.soundcloud.com/'):
        return True

    return False


def atomic_rename(old_name, new_name):
    """Atomically rename/move a (temporary) file

    This is usually used when updating a file safely by writing
    the new contents into a temporary file and then moving the
    temporary file over the original file to replace it.
    """
    if gpodder.ui.win32:
        # Win32 does not support atomic rename with os.rename
        shutil.move(old_name, new_name)
    else:
        os.rename(old_name, new_name)


def check_command(self, cmd):
    """Check if a command line command/program exists"""
    # Prior to Python 2.7.3, this module (shlex) did not support Unicode input.
    cmd = sanitize_encoding(cmd)
    program = shlex.split(cmd)[0]
    return (find_command(program) is not None)


def rename_episode_file(episode, filename):
    """Helper method to update a PodcastEpisode object

    Useful after renaming/converting its download file.
    """
    if not os.path.exists(filename):
        raise ValueError('Target filename does not exist.')

    basename, extension = os.path.splitext(filename)

    episode.download_filename = os.path.basename(filename)
    episode.file_size = os.path.getsize(filename)
    episode.mime_type = mimetype_from_extension(extension)
    episode.save()
    episode.db.commit()


def get_update_info(url='http://gpodder.org/downloads'):
    """
    Get up to date release information from gpodder.org.

    Returns a tuple: (up_to_date, latest_version, release_date, days_since)

    Example result (up to date version, 20 days after release):
        (True, '3.0.4', '2012-01-24', 20)

    Example result (outdated version, 10 days after release):
        (False, '3.0.5', '2012-02-29', 10)
    """
    data = urlopen(url).read()
    id_field_re = re.compile(r'<([a-z]*)[^>]*id="([^"]*)"[^>]*>([^<]*)</\1>')
    info = dict((m.group(2), m.group(3)) for m in id_field_re.finditer(data))

    latest_version = info['latest-version']
    release_date = info['release-date']

    release_parsed = datetime.datetime.strptime(release_date, '%Y-%m-%d')
    days_since_release = (datetime.datetime.today() - release_parsed).days

    convert = lambda s: tuple(int(x) for x in s.split('.'))
    up_to_date = (convert(gpodder.__version__) >= convert(latest_version))

    return up_to_date, latest_version, release_date, days_since_release


def run_in_background(function, daemon=False):
    logger.debug('run_in_background: %s (%s)', function, str(daemon))
    thread = threading.Thread(target=function)
    thread.setDaemon(daemon)
    thread.start()
    return thread


def linux_get_active_interfaces():
    """Get active network interfaces using 'ip link'

    Returns a list of active network interfaces or an
    empty list if the device is offline. The loopback
    interface is not included.
    """
    process = subprocess.Popen(['ip', 'link'], stdout=subprocess.PIPE)
    data, _ = process.communicate()
    for interface, _ in re.findall(r'\d+: ([^:]+):.*state (UP|UNKNOWN)', data):
        if interface != 'lo':
            yield interface


def osx_get_active_interfaces():
    """Get active network interfaces using 'ifconfig'

    Returns a list of active network interfaces or an
    empty list if the device is offline. The loopback
    interface is not included.
    """
    process = subprocess.Popen(['ifconfig'], stdout=subprocess.PIPE)
    stdout, _ = process.communicate()
    for i in re.split('\n(?!\t)', stdout, re.MULTILINE):
        b = re.match('(\\w+):.*status: (active|associated)$', i, re.MULTILINE | re.DOTALL)
        if b:
            yield b.group(1)

def unix_get_active_interfaces():
    """Get active network interfaces using 'ifconfig'

    Returns a list of active network interfaces or an
    empty list if the device is offline. The loopback
    interface is not included.
    """
    process = subprocess.Popen(['ifconfig'], stdout=subprocess.PIPE)
    stdout, _ = process.communicate()
    for i in re.split('\n(?!\t)', stdout, re.MULTILINE):
        b = re.match('(\\w+):.*status: active$', i, re.MULTILINE | re.DOTALL)
        if b:
            yield b.group(1)


def connection_available():
    """Check if an Internet connection is available

    Returns True if a connection is available (or if there
    is no way to determine the connection). Returns False
    if no network interfaces are up (i.e. no connectivity).
    """
    try:
        if gpodder.ui.win32:
            # FIXME: Implement for Windows
            return True
        elif gpodder.ui.osx:
            return len(list(osx_get_active_interfaces())) > 0
        else:
            # By default, we assume we're not offline (bug 1730)
            offline = False

            if find_command('ifconfig') is not None:
                # If ifconfig is available, and it says we don't have
                # any active interfaces, assume we're offline
                if len(list(unix_get_active_interfaces())) == 0:
                    offline = True

            # If we assume we're offline, try the "ip" command as fallback
            if offline and find_command('ip') is not None:
                if len(list(linux_get_active_interfaces())) == 0:
                    offline = True
                else:
                    offline = False

            return not offline

        return False
    except Exception, e:
        logger.warn('Cannot get connection status: %s', e, exc_info=True)
        # When we can't determine the connection status, act as if we're online (bug 1730)
        return True


def website_reachable(url):
    """
    Check if a specific website is available.
    """
    if not connection_available():
        # No network interfaces up - assume website not reachable
        return (False, None)

    try:
        response = urllib2.urlopen(url, timeout=1)
        return (True, response)
    except urllib2.URLError as err:
        pass

    return (False, None)

def delete_empty_folders(top):
    for root, dirs, files in os.walk(top, topdown=False):
        for name in dirs:
            dirname = os.path.join(root, name)
            if not os.listdir(dirname):
                os.rmdir(dirname)


########NEW FILE########
__FILENAME__ = vimeo
# -*- coding: utf-8 -*-
#
# gPodder - A media aggregator and podcast client
# Copyright (c) 2005-2014 Thomas Perl and the gPodder Team
#
# gPodder is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# gPodder is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#

#
#  gpodder.vimeo - Vimeo download magic
#  Thomas Perl <thp@gpodder.org>; 2012-01-03
#


import gpodder

from gpodder import util

import logging
logger = logging.getLogger(__name__)

try:
    # For Python < 2.6, we use the "simplejson" add-on module
    import simplejson as json
except ImportError:
    # Python 2.6 already ships with a nice "json" module
    import json

import re

VIMEOCOM_RE = re.compile(r'http://vimeo\.com/(\d+)$', re.IGNORECASE)
MOOGALOOP_RE = re.compile(r'http://vimeo\.com/moogaloop\.swf\?clip_id=(\d+)$', re.IGNORECASE)
SIGNATURE_RE = re.compile(r'"timestamp":(\d+),"signature":"([^"]+)"')
DATA_CONFIG_RE = re.compile(r'data-config-url="([^"]+)"')


class VimeoError(BaseException): pass

def get_real_download_url(url):
    quality = 'sd'
    codecs = 'H264,VP8,VP6'

    video_id = get_vimeo_id(url)

    if video_id is None:
        return url

    web_url = 'http://vimeo.com/%s' % video_id
    web_data = util.urlopen(web_url).read()
    data_config_frag = DATA_CONFIG_RE.search(web_data)

    if data_config_frag is None:
        raise VimeoError('Cannot get data config from Vimeo')

    data_config_url = data_config_frag.group(1).replace('&amp;', '&')

    def get_urls(data_config_url):
        data_config_data = util.urlopen(data_config_url).read().decode('utf-8')
        data_config = json.loads(data_config_data)
        for fileinfo in data_config['request']['files'].values():
            if not isinstance(fileinfo, dict):
                continue

            for fileformat, keys in fileinfo.items():
                if not isinstance(keys, dict):
                    continue

                yield (fileformat, keys['url'])

    for quality, url in get_urls(data_config_url):
        return url

def get_vimeo_id(url):
    result = MOOGALOOP_RE.match(url)
    if result is not None:
        return result.group(1)

    result = VIMEOCOM_RE.match(url)
    if result is not None:
        return result.group(1)

    return None

def is_video_link(url):
    return (get_vimeo_id(url) is not None)

def get_real_channel_url(url):
    result = VIMEOCOM_RE.match(url)
    if result is not None:
        return 'http://vimeo.com/%s/videos/rss' % result.group(1)

    return url

def get_real_cover(url):
    return None


########NEW FILE########
__FILENAME__ = youtube
# -*- coding: utf-8 -*-
#
# gPodder - A media aggregator and podcast client
# Copyright (c) 2005-2014 Thomas Perl and the gPodder Team
#
# gPodder is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.
#
# gPodder is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
#  gpodder.youtube - YouTube and related magic
#  Justin Forest <justin.forest@gmail.com> 2008-10-13
#


import gpodder

from gpodder import util

import os.path

import logging
logger = logging.getLogger(__name__)

try:
    import simplejson as json
except ImportError:
    import json

import re
import urllib

try:
    # Python >= 2.6
    from urlparse import parse_qs
except ImportError:
    # Python < 2.6
    from cgi import parse_qs

# http://en.wikipedia.org/wiki/YouTube#Quality_and_codecs
# format id, (preferred ids, path(?), description) # video bitrate, audio bitrate
formats = [
    # WebM VP8 video, Vorbis audio
    # Fallback to an MP4 version of same quality.
    # Try 34 (FLV 360p H.264 AAC) if 18 (MP4 360p) fails.
    # Fallback to 6 or 5 (FLV Sorenson H.263 MP3) if all fails.
    (46, ([46, 37, 45, 22, 44, 35, 43, 18, 6, 34, 5], '45/1280x720/99/0/0', 'WebM 1080p (1920x1080)')), # N/A,      192 kbps
    (45, ([45, 22, 44, 35, 43, 18, 6, 34, 5],         '45/1280x720/99/0/0', 'WebM 720p (1280x720)')),   # 2.0 Mbps, 192 kbps
    (44, ([44, 35, 43, 18, 6, 34, 5],                 '44/854x480/99/0/0',  'WebM 480p (854x480)')),    # 1.0 Mbps, 128 kbps
    (43, ([43, 18, 6, 34, 5],                         '43/640x360/99/0/0',  'WebM 360p (640x360)')),    # 0.5 Mbps, 128 kbps

    # MP4 H.264 video, AAC audio
    # Try 35 (FLV 480p H.264 AAC) between 720p and 360p because there's no MP4 480p.
    # Try 34 (FLV 360p H.264 AAC) if 18 (MP4 360p) fails.
    # Fallback to 6 or 5 (FLV Sorenson H.263 MP3) if all fails.
    (38, ([38, 37, 22, 35, 18, 34, 6, 5], '38/1920x1080/9/0/115', 'MP4 4K 3072p (4096x3072)')), # 5.0 - 3.5 Mbps, 192 kbps
    (37, ([37, 22, 35, 18, 34, 6, 5],     '37/1920x1080/9/0/115', 'MP4 HD 1080p (1920x1080)')), # 4.3 - 3.0 Mbps, 192 kbps
    (22, ([22, 35, 18, 34, 6, 5],         '22/1280x720/9/0/115',  'MP4 HD 720p (1280x720)')),   # 2.9 - 2.0 Mbps, 192 kbps
    (18, ([18, 34, 6, 5],                 '18/640x360/9/0/115',   'MP4 360p (640x360)')),       #       0.5 Mbps,  96 kbps

    # FLV H.264 video, AAC audio
    # Does not check for 360p MP4.
    # Fallback to 6 or 5 (FLV Sorenson H.263 MP3) if all fails.
    (35, ([35, 34, 6, 5], '35/854x480/9/0/115',   'FLV 480p (854x480)')), # 1 - 0.80 Mbps, 128 kbps
    (34, ([34, 6, 5],     '34/640x360/9/0/115',   'FLV 360p (640x360)')), #     0.50 Mbps, 128 kbps

    # FLV Sorenson H.263 video, MP3 audio
    (6, ([6, 5],         '5/480x270/7/0/0',      'FLV 270p (480x270)')), #     0.80 Mbps,  64 kbps
    (5, ([5],            '5/320x240/7/0/0',      'FLV 240p (320x240)')), #     0.25 Mbps,  64 kbps
]
formats_dict = dict(formats)

class YouTubeError(Exception): pass


def get_fmt_ids(youtube_config):
    fmt_ids = youtube_config.preferred_fmt_ids
    if not fmt_ids:
        format = formats_dict.get(youtube_config.preferred_fmt_id)
        if format is None:
            fmt_ids = []
        else:
            fmt_ids, path, description = format

    return fmt_ids

def get_real_download_url(url, preferred_fmt_ids=None):
    if not preferred_fmt_ids:
        preferred_fmt_ids, _, _ = formats_dict[22] # MP4 720p

    vid = get_youtube_id(url)
    if vid is not None:
        page = None
        url = 'http://www.youtube.com/get_video_info?&el=detailpage&video_id=' + vid

        while page is None:
            req = util.http_request(url, method='GET')
            if 'location' in req.msg:
                url = req.msg['location']
            else:
                page = req.read()

        # Try to find the best video format available for this video
        # (http://forum.videohelp.com/topic336882-1800.html#1912972)
        def find_urls(page):
            r4 = re.search('url_encoded_fmt_stream_map=([^&]+)', page)
            if r4 is not None:
                fmt_url_map = urllib.unquote(r4.group(1))
                for fmt_url_encoded in fmt_url_map.split(','):
                    video_info = parse_qs(fmt_url_encoded)
                    yield int(video_info['itag'][0]), video_info['url'][0]
            else:
                error_info = parse_qs(page)
                error_message = util.remove_html_tags(error_info['reason'][0])
                raise YouTubeError('Cannot download video: %s' % error_message)

        fmt_id_url_map = sorted(find_urls(page), reverse=True)

        if not fmt_id_url_map:
            raise YouTubeError('fmt_url_map not found for video ID "%s"' % vid)

        # Default to the highest fmt_id if we don't find a match below
        _, url  = fmt_id_url_map[0]

        formats_available = set(fmt_id for fmt_id, url in fmt_id_url_map)
        fmt_id_url_map = dict(fmt_id_url_map)

        # This provides good quality video, seems to be always available
        # and is playable fluently in Media Player
        if gpodder.ui.harmattan or gpodder.ui.sailfish:
            preferred_fmt_ids = [18]

        for id in preferred_fmt_ids:
            id = int(id)
            if id in formats_available:
                format = formats_dict.get(id)
                if format is not None:
                    _, _, description = format
                else:
                    description = 'Unknown'

                logger.info('Found YouTube format: %s (fmt_id=%d)',
                        description, id)
                url = fmt_id_url_map[id]
                break

    return url

def get_youtube_id(url):
    r = re.compile('http[s]?://(?:[a-z]+\.)?youtube\.com/v/(.*)\.swf', re.IGNORECASE).match(url)
    if r is not None:
        return r.group(1)

    r = re.compile('http[s]?://(?:[a-z]+\.)?youtube\.com/watch\?v=([^&]*)', re.IGNORECASE).match(url)
    if r is not None:
        return r.group(1)

    r = re.compile('http[s]?://(?:[a-z]+\.)?youtube\.com/v/(.*)[?]', re.IGNORECASE).match(url)
    if r is not None:
        return r.group(1)

    return None

def is_video_link(url):
    return (get_youtube_id(url) is not None)

def is_youtube_guid(guid):
    return guid.startswith('tag:youtube.com,2008:video:')

def get_real_channel_url(url):
    r = re.compile('http://(?:[a-z]+\.)?youtube\.com/user/([a-z0-9]+)', re.IGNORECASE)
    m = r.match(url)

    if m is not None:
        next = 'http://www.youtube.com/rss/user/'+ m.group(1) +'/videos.rss'
        logger.debug('YouTube link resolved: %s => %s', url, next)
        return next

    r = re.compile('http://(?:[a-z]+\.)?youtube\.com/profile?user=([a-z0-9]+)', re.IGNORECASE)
    m = r.match(url)

    if m is not None:
        next = 'http://www.youtube.com/rss/user/'+ m.group(1) +'/videos.rss'
        logger.debug('YouTube link resolved: %s => %s', url, next)
        return next

    return url

def get_real_cover(url):
    r = re.compile('http://www\.youtube\.com/rss/user/([^/]+)/videos\.rss', \
            re.IGNORECASE)
    m = r.match(url)

    if m is not None:
        username = m.group(1)
        api_url = 'http://gdata.youtube.com/feeds/api/users/%s?v=2' % username
        data = util.urlopen(api_url).read()
        match = re.search('<media:thumbnail url=[\'"]([^\'"]+)[\'"]/>', data)
        if match is not None:
            logger.debug('YouTube userpic for %s is: %s', url, match.group(1))
            return match.group(1)

    return None

def find_youtube_channels(string):
    url = 'http://gdata.youtube.com/feeds/api/videos?alt=json&q=%s' % urllib.quote(string, '')
    data = json.load(util.urlopen(url))

    class FakeImporter(object):
        def __init__(self):
            self.items = []

    result = FakeImporter()

    seen_users = set()
    for entry in data['feed']['entry']:
        user = os.path.basename(entry['author'][0]['uri']['$t'])
        title = entry['title']['$t']
        url = 'http://www.youtube.com/rss/user/%s/videos.rss' % user
        if user not in seen_users:
            result.items.append({
                'title': user,
                'url': url,
                'description': title
            })
            seen_users.add(user)

    return result


########NEW FILE########
__FILENAME__ = directory

import gtk
import gobject
import pango
import tagcloud
import json

w = gtk.Dialog()
w.set_title('Discover new podcasts')
w.set_default_size(650, 450)

tv = gtk.TreeView()
tv.set_headers_visible(False)
tv.set_size_request(160, -1)

class OpmlEdit(object): pass
class Search(object): pass
class OpmlFixed(object): pass
class TagCloud(object): pass

search_providers = (
        ('gpodder.net', 'search_gpodder.png', Search),
        ('YouTube', 'search_youtube.png', Search),
        ('SoundCloud', 'search_soundcloud.png', Search),
        ('Miro Guide', 'search_miro.png', Search),
)

directory_providers = (
        ('Toplist', 'directory_toplist.png', OpmlFixed),
        ('Examples', 'directory_example.png', OpmlFixed),
        ('Tag cloud', 'directory_tags.png', TagCloud),
)

SEPARATOR = (True, pango.WEIGHT_NORMAL, '', None, None)
C_SEPARATOR, C_WEIGHT, C_TEXT, C_ICON, C_PROVIDER = range(5)
store = gtk.ListStore(bool, int, str, gtk.gdk.Pixbuf, object)

opml_pixbuf = gtk.gdk.pixbuf_new_from_file('directory_opml.png')
store.append((False, pango.WEIGHT_NORMAL, 'OPML', opml_pixbuf, OpmlEdit))

store.append(SEPARATOR)

for name, icon, provider in search_providers:
    pixbuf = gtk.gdk.pixbuf_new_from_file(icon)
    store.append((False, pango.WEIGHT_NORMAL, name, pixbuf, provider))

store.append(SEPARATOR)

for name, icon, provider in directory_providers:
    pixbuf = gtk.gdk.pixbuf_new_from_file(icon)
    store.append((False, pango.WEIGHT_NORMAL, name, pixbuf, provider))

store.append(SEPARATOR)

for i in range(1, 5):
    store.append((False, pango.WEIGHT_NORMAL, 'Bookmark %d' % i, None, None))

tv.set_model(store)

def is_row_separator(model, iter):
    return model.get_value(iter, C_SEPARATOR)

tv.set_row_separator_func(is_row_separator)

column = gtk.TreeViewColumn('')
cell = gtk.CellRendererPixbuf()
column.pack_start(cell, False)
column.add_attribute(cell, 'pixbuf', C_ICON)
cell = gtk.CellRendererText()
column.pack_start(cell)
column.add_attribute(cell, 'text', C_TEXT)
column.add_attribute(cell, 'weight', C_WEIGHT)
tv.append_column(column)

def on_row_activated(treeview, path, column):
    model = treeview.get_model()
    iter = model.get_iter(path)

    for row in model:
        row[C_WEIGHT] = pango.WEIGHT_NORMAL

    if iter:
        model.set_value(iter, C_WEIGHT, pango.WEIGHT_BOLD)
        provider = model.get_value(iter, C_PROVIDER)
        use_provider(provider)

def on_cursor_changed(treeview):
    path, column = treeview.get_cursor()
    on_row_activated(treeview, path, column)

tv.connect('row-activated', on_row_activated)
tv.connect('cursor-changed', on_cursor_changed)

sw = gtk.ScrolledWindow()
sw.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
sw.set_shadow_type(gtk.SHADOW_IN)
sw.add(tv)

sidebar = gtk.VBox()
sidebar.set_spacing(6)

sidebar.pack_start(sw, True, True)
sidebar.pack_start(gtk.Button('Add bookmark'), False, False)

vb = gtk.VBox()
vb.set_spacing(6)

title_label = gtk.Label('Title')
title_label.set_alignment(0, 0)
vb.pack_start(title_label, False, False)

search_hbox = gtk.HBox()
search_hbox.set_spacing(6)
search_label = gtk.Label('')
search_hbox.pack_start(search_label, False, False)
search_entry = gtk.Entry()
search_hbox.pack_start(search_entry, True, True)
search_button = gtk.Button('')
search_hbox.pack_start(search_button, False, False)

vb.pack_start(search_hbox, False, False)

tagcloud_sw = gtk.ScrolledWindow()
tagcloud_sw.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
tagcloud_sw.set_shadow_type(gtk.SHADOW_IN)
podcast_tags = json.loads("""
[
{"tag": "Technology",
"usage": 530 },
{"tag": "Society & Culture",
"usage": 420 },
{"tag": "Arts",
"usage": 400},
{"tag": "News & Politics",
"usage": 320}
]
""")
tagcloudw = tagcloud.TagCloud(list((x['tag'], x['usage']) for x in podcast_tags), 10, 14)
tagcloud_sw.set_size_request(-1, 130)
tagcloud_sw.add(tagcloudw)
vb.pack_start(tagcloud_sw, False, False)

podcasts_sw = gtk.ScrolledWindow()
podcasts_sw.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
podcasts_sw.set_shadow_type(gtk.SHADOW_IN)
podcasts_tv = gtk.TreeView()
podcasts_sw.add(podcasts_tv)
vb.pack_start(podcasts_sw, True, True)


hb = gtk.HBox()
hb.set_spacing(12)
hb.set_border_width(12)
hb.pack_start(sidebar, False, True)
hb.pack_start(vb, True, True)

w.vbox.add(hb)
w.add_button(gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL)
w.add_button('Subscribe', gtk.RESPONSE_OK)
w.set_response_sensitive(gtk.RESPONSE_OK, False)

def use_provider(provider):
    if provider == OpmlEdit:
        search_label.set_text('URL:')
        search_button.set_label('Download')
    else:
        search_label.set_text('Search:')
        search_button.set_label('Search')

    if provider in (OpmlEdit, Search):
        title_label.hide()
        search_hbox.show()
        search_entry.set_text('')
        def later():
            search_entry.grab_focus()
            return False
        gobject.idle_add(later)
    elif provider == TagCloud:
        title_label.hide()
        search_hbox.hide()
    else:
        if provider == OpmlFixed:
            title_label.set_text('Example stuff')
        elif provider == TagCloud:
            title_label.set_text('Tag cloud')
        title_label.show()
        search_hbox.hide()

    tagcloud_sw.set_visible(provider == TagCloud)

    print 'using provider:', provider

#w.connect('destroy', gtk.main_quit)
w.show_all()

on_row_activated(tv, (0,), None)

w.run()

#gtk.main()


########NEW FILE########
__FILENAME__ = tagcloud

import gtk
import gobject
import cgi

tags = (
        ('Electronica', 5),
        ('Reggae', 5),
        ('Electro', 20),
        ('Detroit Techno', 4),
        ('Funk', 14),
        ('Jazz', 4),
        ('Minimal', 20),
        ('Soulful Drum and Bass', 6),
        ('Dub', 7),
        ('Drum and Bass', 23),
        ('Deep Techno', 7),
        ('Deephouse', 27),
        ('Soulful', 9),
        ('Minimal Techno', 30),
        ('Downtempo', 17),
        ('House', 29),
        ('Dubstep', 14),
        ('Techno', 32),
        ('Electrotech', 8),
        ('Techhouse', 28),
        ('Disco', 15),
        ('Downbeat', 28),
        ('Electrohouse', 14),
        ('Hiphop', 25),
        ('Trance', 6),
        ('Freestyle', 14),
        ('Funky House', 3),
        ('Minimal House', 4),
        ('Nu Jazz', 11),
        ('Chill-Out', 6),
        ('Breaks', 10),
        ('UK Garage', 4),
        ('Soul', 10),
        ('Progressive House', 3),
        ('Lounge', 6),
)


class TagCloud(gtk.Layout):
    __gsignals__ = {
            'selected': (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE,
                           (gobject.TYPE_STRING,))
    }

    def __init__(self, tags, min_size=20, max_size=36):
        self.__gobject_init__()
        gtk.Layout.__init__(self)
        self._tags = tags
        self._min_size = min_size
        self._max_size = max_size
        self._min_weight = min(weight for tag, weight in self._tags)
        self._max_weight = max(weight for tag, weight in self._tags)
        self._size = 0, 0
        self._alloc_id = self.connect('size-allocate', self._on_size_allocate)
        self._init_tags()
        self._in_relayout = False

    def _on_size_allocate(self, widget, allocation):
        self._size = (allocation.width, allocation.height)
        if not self._in_relayout:
            self.relayout()

    def _init_tags(self):
        for tag, weight in self._tags:
            label = gtk.Label()
            markup = '<span size="%d">%s</span>' % (1000*self._scale(weight), cgi.escape(tag))
            label.set_markup(markup)
            button = gtk.ToolButton(label)
            button.connect('clicked', lambda b: self.emit('selected', tag))
            self.put(button, 1, 1)

    def _scale(self, weight):
        weight_range = float(self._max_weight-self._min_weight)
        ratio = float(weight-self._min_weight)/weight_range
        return int(self._min_size + (self._max_size-self._min_size)*ratio)

    def relayout(self):
        self._in_relayout = True
        x, y, max_h = 0, 0, 0
        current_row = []
        pw, ph = self._size
        def fixup_row(widgets, x, y, max_h):
            residue = (pw - x)
            x = int(residue/2)
            for widget in widgets:
                cw, ch = widget.size_request()
                self.move(widget, x, y+max(0, int((max_h-ch)/2)))
                x += cw + 10
        for child in self.get_children():
            w, h = child.size_request()
            if x + w > pw:
                fixup_row(current_row, x, y, max_h)
                y += max_h + 10
                max_h, x = 0, 0
                current_row = []

            self.move(child, x, y)
            x += w + 10
            max_h = max(max_h, h)
            current_row.append(child)
        fixup_row(current_row, x, y, max_h)
        self.set_size(pw, y+max_h)
        def unrelayout():
            self._in_relayout = False
            return False
        gobject.idle_add(unrelayout)
gobject.type_register(TagCloud)

if __name__ == '__main__':
    l = TagCloud(tags)

    try:
        import hildon
        w = hildon.StackableWindow()
        sw = hildon.PannableArea()
    except:
        w = gtk.Window()
        w.set_default_size(600, 300)
        sw = gtk.ScrolledWindow()
        sw.set_policy(gtk.POLICY_NEVER, gtk.POLICY_AUTOMATIC)

    w.set_title('Tag cloud Demo')
    w.add(sw)
    sw.add(l)

    def on_tag_selected(cloud, tag):
        print 'tag selected:', tag

    l.connect('selected', on_tag_selected)

    w.show_all()
    w.connect('destroy', gtk.main_quit)

    gtk.main()


########NEW FILE########
__FILENAME__ = exceptions
class DBusException(Exception):
    pass

class NameExistsException(Exception):
    pass


########NEW FILE########
__FILENAME__ = glib

class DBusGMainLoop(object):
    def __init__(self, *args, **kwargs):
        pass


########NEW FILE########
__FILENAME__ = glib
def DBusGMainLoop(*args, **kwargs):
    pass

########NEW FILE########
__FILENAME__ = mainloop

########NEW FILE########
__FILENAME__ = service

def method(*args, **kwargs):
    return lambda x: x

class BusName(object):
    def __init__(self, *args, **kwargs):
        pass

class Object:
    def __init__(self, *args, **kwargs):
        pass


########NEW FILE########
__FILENAME__ = generate_commits
#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# generate_commits.py - Generate Git commits based on Transifex updates
# Thomas Perl <thp@gpodder.org>; 2012-08-16
#

import re
import glob
import subprocess

filenames = []

process = subprocess.Popen(['git', 'status', '--porcelain'] +
        glob.glob('po/*.po'), stdout=subprocess.PIPE)
stdout, stderr = process.communicate()
for line in stdout.splitlines():
    status, filename = line.strip().split()
    if status == 'M':
        filenames.append(filename)

for filename in filenames:
    in_translators = False
    translators = []
    language = None

    for line in open(filename).read().splitlines():
        if line.startswith('# Translators:'):
            in_translators = True
        elif in_translators:
            match = re.match(r'# ([^<]* <[^>]*>)', line)
            if match:
                translators.append(match.group(1))
            else:
                in_translators = False
        elif line.startswith('"Last-Translator:'):
            match = re.search(r'Last-Translator: ([^<]* <[^>]*>)', line)
            if match:
                translators.append(match.group(1))

        match = re.match(r'"Language-Team: (.+) \(http://www.transifex.com/', line)
        if not match:
            match = re.match(r'"Language-Team: ([^\(]+).*\\n"', line, re.DOTALL)
        if match:
            language = match.group(1).strip()

    if translators and language is not None:
        if len(translators) != 1:
            print '# Warning: %d other translators: %s' % (len(translators) - 1, ', '.join(translators[1:]))
        print 'git commit --author="%s" --message="Updated %s translation" %s' % (translators[0], language, filename)
    else:
        print '# FIXME (could not parse):', '!'*10, filename, '!'*10


########NEW FILE########
__FILENAME__ = summary
#!/usr/bin/python
# summary.py - Text-based visual translation completeness summary
# Thomas Perl <thp@gpodder.org>, 2009-01-03
#
# Usage: make statistics | python summary.py
#

import sys
import re
import math
import glob
import os
import subprocess

width = 40

class Language(object):
    def __init__(self, language, translated, fuzzy, untranslated):
        self.language = language
        self.translated = int(translated)
        self.fuzzy = int(fuzzy)
        self.untranslated = int(untranslated)

    def get_translated_ratio(self):
        return float(self.translated)/float(self.translated+self.fuzzy+self.untranslated)

    def get_fuzzy_ratio(self):
        return float(self.fuzzy)/float(self.translated+self.fuzzy+self.untranslated)

    def get_untranslated_ratio(self):
        return float(self.untranslated)/float(self.translated+self.fuzzy+self.untranslated)

    def __cmp__(self, other):
        return cmp(self.get_translated_ratio(), other.get_translated_ratio())

languages = []

COUNTS_RE = '((\d+) translated message[s]?)?(, (\d+) fuzzy translation[s]?)?(, (\d+) untranslated message[s]?)?\.'

po_folder = os.path.join(os.path.dirname(__file__), '..', '..', 'po')
for filename in glob.glob(os.path.join(po_folder, '*.po')):
    language, _ = os.path.splitext(os.path.basename(filename))
    msgfmt = subprocess.Popen(['msgfmt', '--statistics', filename],
            stderr=subprocess.PIPE)
    _, stderr = msgfmt.communicate()

    match = re.match(COUNTS_RE, stderr).groups()
    languages.append(Language(language, match[1] or '0', match[3] or '0', match[5] or '0'))

print ''
for language in sorted(languages):
    tc = '#'*(int(math.floor(width*language.get_translated_ratio())))
    fc = '~'*(int(math.floor(width*language.get_fuzzy_ratio())))
    uc = ' '*(width-len(tc)-len(fc))

    print ' %5s [%s%s%s] -- %3.0f %% translated' % (language.language, tc, fc, uc, language.get_translated_ratio()*100)

print """
  Total translations: %s
""" % (len(languages))


########NEW FILE########
__FILENAME__ = localdepends
#!/usr/bin/python
#
# gPodder dependency installer for running the CLI from the source tree
#
# Run "python localdepends.py" and it will download and inject dependencies,
# so you only need a standard Python installation for the command-line utility
#
# Thomas Perl <thp.io/about>; 2012-02-11
#

import urllib2
import re
import sys
import StringIO
import tarfile
import os
import shutil
import tempfile

sys.stdout = sys.stderr

src_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src'))
tmp_dir = tempfile.mkdtemp()

MODULES = [
    # Module name, Regex-file chooser (1st group = location in "src/")
    ('feedparser', r'feedparser-[0-9.]+/feedparser/(feedparser.py)'),
    ('mygpoclient', r'mygpoclient-[0-9.]+/(mygpoclient/[^/]*\.py)')
]

def get_tarball_url(modulename):
    url = 'http://pypi.python.org/pypi/' + modulename
    html = urllib2.urlopen(url).read()
    match = re.search(r'(http[s]?://[^>]*%s-([0-9.]*)\.tar\.gz)' % modulename, html)
    return match.group(0) if match is not None else None

for module, required_files in MODULES:
    print 'Fetching', module, '...',
    tarball_url = get_tarball_url(module)
    if tarball_url is None:
        print 'Cannot determine download URL for', module, '- aborting!'
        break
    data = urllib2.urlopen(tarball_url).read()
    print '%d KiB' % (len(data)/1024)
    tar = tarfile.open(fileobj=StringIO.StringIO(data))
    for name in tar.getnames():
        match = re.match(required_files, name)
        if match is not None:
            target_name = match.group(1)
            target_file = os.path.join(src_dir, target_name)
            if os.path.exists(target_file):
                print 'Skipping:', target_file
                continue

            target_dir = os.path.dirname(target_file)
            if not os.path.isdir(target_dir):
                os.mkdir(target_dir)

            print 'Extracting:', target_name
            tar.extract(name, tmp_dir)
            shutil.move(os.path.join(tmp_dir, name), target_file)

shutil.rmtree(tmp_dir)


########NEW FILE########
__FILENAME__ = progressbar_icon_tester
#!/usr/bin/python
# Progressbar icon tester
# Thomas Perl <thp.io/about>; 2012-02-05
#
# based on: Simple script to test gPodder's "pill" pixbuf implementation
#           Thomas Perl <thp.io/about>; 2009-09-13

import sys
sys.path.insert(0, 'src')

import gtk

from gpodder.gtkui.draw import draw_cake_pixbuf

def gen(percentage):
    pixbuf = draw_cake_pixbuf(percentage)
    return gtk.image_new_from_pixbuf(pixbuf)

w = gtk.Window()
w.connect('destroy', gtk.main_quit)
v = gtk.VBox()
w.add(v)
for y in xrange(1):
    h = gtk.HBox()
    h.set_homogeneous(True)
    v.add(h)
    PARTS = 20
    for x in xrange(PARTS + 1):
        h.add(gen(float(x)/float(PARTS)))
w.set_default_size(400, 100)
w.show_all()
gtk.main()


########NEW FILE########
__FILENAME__ = test-auth-server
#!/usr/bin/python
# -*- coding: utf-8 -*-
# Simple HTTP web server for testing HTTP Authentication (see bug 1539)
# from our crappy-but-does-the-job department
# Thomas Perl <thp.io/about>; 2012-01-20

import BaseHTTPServer
import sys
import re
import hashlib
import datetime

USERNAME = 'user@example.com'    # Username used for HTTP Authentication
PASSWORD = 'secret'              # Password used for HTTP Authentication

HOST, PORT = 'localhost', 8000   # Hostname and port for the HTTP server

# When the script contents change, the feed's episodes each get a new GUID
GUID = hashlib.sha1(open(__file__).read()).hexdigest()

URL = 'http://%(HOST)s:%(PORT)s' % locals()

FEEDNAME = sys.argv[0]       # The title of the RSS feed
FEEDFILE = 'feed.rss'        # The "filename" of the feed on the server
EPISODES = 'episode'         # Base name for the episode files
EPISODES_EXT = '.mp3'        # Extension for the episode files
EPISODES_MIME = 'audio/mpeg' # Mime type for the episode files
EP_COUNT = 7                 # Number of episodes in the feed
SIZE = 500000                # Size (in bytes) of the episode downloads)

def mkpubdates(items):
    """Generate fake pubDates (one each day, recently)"""
    current = datetime.datetime.now() - datetime.timedelta(days=items+3)
    for i in range(items):
        yield current.ctime()
        current += datetime.timedelta(days=1)

def mkrss(items=EP_COUNT):
    """Generate a dumm RSS feed with a given number of items"""
    ITEMS = '\n'.join("""
    <item>
        <title>Episode %(INDEX)s</title>
        <guid>tag:test.gpodder.org,2012:%(GUID)s,%(URL)s,%(INDEX)s</guid>
        <pubDate>%(PUBDATE)s</pubDate>
        <enclosure
          url="%(URL)s/%(EPISODES)s%(INDEX)s%(EPISODES_EXT)s"
          type="%(EPISODES_MIME)s"
          length="%(SIZE)s"/>
    </item>
    """ % dict(locals().items()+globals().items())
        for INDEX, PUBDATE in enumerate(mkpubdates(items)))

    return """
    <rss>
    <channel><title>%(FEEDNAME)s</title><link>%(URL)s</link>
    %(ITEMS)s
    </channel>
    </rss>
    """ % dict(locals().items()+globals().items())

def mkdata(size=SIZE):
    """Generate dummy data of a given size (in bytes)"""
    return ''.join(chr(32+(i%(127-32))) for i in range(size))

class AuthRequestHandler(BaseHTTPServer.BaseHTTPRequestHandler):
    FEEDFILE_PATH = '/%s' % FEEDFILE
    EPISODES_PATH = '/%s' % EPISODES

    def do_GET(self):
        authorized = False
        is_feed = False
        is_episode = False

        auth_header = self.headers.get('authorization', '')
        m = re.match(r'^Basic (.*)$', auth_header)
        if m is not None:
            auth_data = m.group(1).decode('base64').split(':', 1)
            if len(auth_data) == 2:
                username, password = auth_data
                print 'Got username:', username
                print 'Got password:', password
                if (username, password) == (USERNAME, PASSWORD):
                    print 'Valid credentials provided.'
                    authorized = True

        if self.path == self.FEEDFILE_PATH:
            print 'Feed request.'
            is_feed = True
        elif self.path.startswith(self.EPISODES_PATH):
            print 'Episode request.'
            is_episode = True

        if not authorized:
            print 'Not authorized - sending WWW-Authenticate header.'
            self.send_response(401)
            self.send_header('WWW-Authenticate',
                    'Basic realm="%s"' % sys.argv[0])
            self.end_headers()
            self.wfile.close()
            return

        self.send_response(200)
        self.send_header('Content-type',
                'application/xml' if is_feed else 'audio/mpeg')
        self.end_headers()
        self.wfile.write(mkrss() if is_feed else mkdata())
        self.wfile.close()


if __name__ == '__main__':
    httpd = BaseHTTPServer.HTTPServer((HOST, PORT), AuthRequestHandler)
    print """
    Feed URL: %(URL)s/%(FEEDFILE)s
    Username: %(USERNAME)s
    Password: %(PASSWORD)s
    """ % locals()
    while True:
        httpd.handle_request()


########NEW FILE########
__FILENAME__ = upgrade-win32-binary-package
#!/usr/bin/python
# Upgrade script for the gPodder Win32 release
# Injects new data into an old win32 release to build a new release
# Thomas Perl <thp.io/about>; 2011-04-08

# Required files:
# - An old win32 release
# - The source tarball of the new release
# - The (binary) Debian package of the new release
# - The source tarball of the most recent mygpoclient
# - The source tarball of the most recent feedparser

import os
import subprocess
import sys
import re
import glob

if len(sys.argv) != 6:
    print """
    Usage: %s <oldzip> <newsource> <deb> <mygpoclient> <feedparser>

    With:
       <oldzip>, e.g. gpodder-2.12-win32.zip
       <newsource>, e.g. gpodder-2.14.tar.gz
       <deb>, e.g. gpodder_2.14-1_all.deb
       <mygpoclient>, e.g. mygpoclient-1.5.tar.gz
       <feedparser>, e.g. feedparser-5.0.1.tar.gz
    """ % sys.argv[0]
    sys.exit(1)

progname, old_zip, source_tgz, deb, mygpoclient_tgz, feedparser_tgz = sys.argv

print '-'*80
print 'gPodder Win32 Release Builder'
print '-'*80


m = re.match(r'gpodder-(\d+).(\d+)-win32.zip', old_zip)
if not m:
    print 'Unknown filename scheme for', old_zip
    sys.exit(1)

old_version = '.'.join(m.groups())
print 'Old version:', old_version

m = re.match(r'gpodder-(\d+).(\d+).tar.gz', source_tgz)
if not m:
    print 'Unknown filename scheme for', source_tgz
    sys.exit(1)

new_version = '.'.join(m.groups())
print 'New version:', new_version

m = re.match(r'gpodder_(\d+).(\d+)-(.*)_all.deb$', deb)
if not m:
    print 'Unknown filename scheme for', deb
    sys.exit(1)

deb_version = '.'.join(m.groups()[:2]) + '-' + m.group(3)
print 'Debian version:', deb_version

m = re.match(r'mygpoclient-(\d+).(\d+).tar.gz', mygpoclient_tgz)
if not m:
    print 'Unknown filename scheme for', mygpoclient_tgz
    sys.exit(1)

mygpoclient_version = '.'.join(m.groups())
print 'mygpoclient version:', mygpoclient_version

m = re.match(r'feedparser-(\d+).(\d+).(\d+).tar.gz', feedparser_tgz)
if not m:
    print 'Unknown filename scheme for', feedparser_tgz
    sys.exit(1)

feedparser_version = '.'.join(m.groups())
print 'feedparser version:', feedparser_version

print '-'*80

print 'Press any key to continue, Ctrl+C to abort.',
raw_input()

if not deb_version.startswith(new_version):
    print 'New version and Debian version mismatch:'
    print new_version, '<->', deb_version
    sys.exit(1)

def sh(*args, **kwargs):
    print '->', ' '.join(args[0])
    try:
        ret = subprocess.call(*args, **kwargs)
    except Exception, e:
        print e
        ret = -1
    if ret != 0:
        print 'EXIT STATUS:', ret
        sys.exit(1)

old_dir, _ = os.path.splitext(old_zip)
new_dir = old_dir.replace(old_version, new_version)
target_file = new_dir + '.zip'

source_dir = source_tgz[:-len('.tar.gz')]
deb_dir, _ = os.path.splitext(deb)

mygpoclient_dir = mygpoclient_tgz[:-len('.tar.gz')]
feedparser_dir = feedparser_tgz[:-len('.tar.gz')]

print 'Cleaning up...'
sh(['rm', '-rf', old_dir, new_dir, source_dir, deb_dir,
    mygpoclient_dir, feedparser_dir])

print 'Extracting...'
sh(['unzip', '-q', old_zip])
sh(['tar', 'xzf', source_tgz])
sh(['dpkg', '-X', deb, deb_dir], stdout=subprocess.PIPE)
sh(['tar', 'xzf', mygpoclient_tgz])
sh(['tar', 'xzf', feedparser_tgz])

print 'Renaming win32 folder...'
sh(['mv', old_dir, new_dir])

copy_files_direct = [
    'ChangeLog',
    'COPYING',
    'README',
    'data/credits.txt',
    'data/gpodder.png',
    'data/images/*',
    'data/ui/*.ui',
    'data/ui/desktop/*.ui',
]

print 'Replacing data files...'
for pattern in copy_files_direct:
    from_files = glob.glob(os.path.join(source_dir, pattern))
    to_files = glob.glob(os.path.join(new_dir, pattern))
    to_folder = os.path.dirname(os.path.join(new_dir, pattern))

    if to_files:
        sh(['rm']+to_files)

    if not os.path.exists(to_folder):
        sh(['mkdir', to_folder])

    if from_files:
        sh(['cp']+from_files+[to_folder])


print 'Copying translations...'
sh(['cp', '-r', os.path.join(deb_dir, 'usr', 'share', 'locale'), os.path.join(new_dir, 'share')])

print 'Copying icons...'
sh(['cp', '-r', os.path.join(deb_dir, 'usr', 'share', 'icons'), os.path.join(new_dir, 'icons')])

print 'Replacing Python package gpodder...'
sh(['rm', '-rf', os.path.join(new_dir, 'lib', 'site-packages', 'gpodder')])
sh(['cp', '-r', os.path.join(source_dir, 'src', 'gpodder'), os.path.join(new_dir, 'lib', 'site-packages')])

print 'Replacing Python package mygpoclient...'
sh(['rm', '-rf', os.path.join(new_dir, 'lib', 'site-packages', 'mygpoclient')])
sh(['cp', '-r', os.path.join(mygpoclient_dir, 'mygpoclient'), os.path.join(new_dir, 'lib', 'site-packages')])

print 'Replacing Python module feedparser...'
sh(['rm', '-f', os.path.join(new_dir, 'lib', 'site-packages', 'feedparser.py')])
sh(['cp', os.path.join(feedparser_dir, 'feedparser', 'feedparser.py'), os.path.join(new_dir, 'lib', 'site-packages')])

print 'Building release...'
sh(['rm', '-f', target_file])
sh(['zip', '-qr', target_file, new_dir])

print 'Cleaning up...'
sh(['rm', '-rf', old_dir, new_dir, source_dir, deb_dir,
    mygpoclient_dir, feedparser_dir])

print '-'*80 + '\n'
print 'Successfully built gpodder', new_version, 'win32 release:'
print ' ', target_file, '\n'


########NEW FILE########
