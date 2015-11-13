__FILENAME__ = captcha_dialog
# Copyright (C) 2008-2011 Sun Ning <classicning@gmail.com>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2, or (at your option)
# any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.
#
#
# The developers of the Exaile media player hereby grant permission
# for non-GPL compatible GStreamer and Exaile plugins to be used and
# distributed together with GStreamer and Exaile. This permission is
# above and beyond the permissions granted by the GPL license by which
# Exaile is covered. If you modify this code, you may extend this
# exception to your version of the code, but you are not obligated to
# do so. If you do not wish to do so, delete this exception statement
# from your version.

import gtk
import gtk.glade

import urllib

from doubanfm_mode import get_resource_path

class CaptchaDialog():
    def __init__(self, doubanfm_plugin):
        self.dbfm_plugin = doubanfm_plugin

        self.builder = gtk.Builder()
        self.builder.add_from_file(get_resource_path('captcha.ui'))

        self.builder.connect_signals({
            'on_ok_button_clicked': self.on_ok_button_clicked})
        self.dialog = self.builder.get_object('dialog1')
        self.image = self.builder.get_object('image1')
        self.text = self.builder.get_object('entry1')

    def show(self):
        self.text.set_text('')
        self.dialog.show_all()

    def hide(self):
        self.dialog.hide()
    
    def on_ok_button_clicked(self, *e):
        solution = self.text.get_text()
        self.hide()
        self.dbfm_plugin.do_init(self.captcha_id, solution)

    def set_captcha(self, captcha_id, captcha_url):
        self.captcha_id = captcha_id
        self.captcha_url = captcha_url
        self.show_image(captcha_url)

    def show_image(self, captcha_url):
        response = urllib.urlopen(captcha_url)
        loader = gtk.gdk.PixbufLoader()
        loader.write(response.read())
        loader.close()        
        self.image.set_from_pixbuf(loader.get_pixbuf())


        

########NEW FILE########
__FILENAME__ = dbfm_pref
# Copyright (C) 2008-2011 Sun Ning <classicning@gmail.com>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2, or (at your option)
# any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.
#
#
# The developers of the Exaile media player hereby grant permission
# for non-GPL compatible GStreamer and Exaile plugins to be used and
# distributed together with GStreamer and Exaile. This permission is
# above and beyond the permissions granted by the GPL license by which
# Exaile is covered. If you modify this code, you may extend this
# exception to your version of the code, but you are not obligated to
# do so. If you do not wish to do so, delete this exception statement
# from your version.

import os
from xlgui.preferences import widgets
from xl.nls import gettext as _


name = _('Douban.fm')
basedir = os.path.dirname(os.path.realpath(__file__))
ui = os.path.join(basedir, 'dbfm_pref.ui')

class UsernamePreference(widgets.Preference):
    default = ''
    name = 'plugin/douban_radio/username'

class PasswordPreference(widgets.Preference):
    default = ''
    name = 'plugin/douban_radio/password'

class DBusIndicatorPreference(widgets.CheckPreference):
    default = False
    name = 'plugin/douban_radio/dbus_indicator'


########NEW FILE########
__FILENAME__ = doubanfm_cover
# Copyright (C) 2008-2011 Sun Ning <classicning@gmail.com>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2, or (at your option)
# any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.
#
#
# The developers of the Exaile media player hereby grant permission
# for non-GPL compatible GStreamer and Exaile plugins to be used and
# distributed together with GStreamer and Exaile. This permission is
# above and beyond the permissions granted by the GPL license by which
# Exaile is covered. If you modify this code, you may extend this
# exception to your version of the code, but you are not obligated to
# do so. If you do not wish to do so, delete this exception statement
# from your version.

import glib
import gio
from xl import covers

class DoubanFMCover(covers.CoverSearchMethod):
    name = 'doubanfm'
    type = 'remote'

    def __init__(self):
        super(DoubanFMCover, self).__init__()
        
    def find_covers(self, track, limit=-1):
        if track.get_tag_raw('cover_url') is not None :
            return track.get_tag_raw('cover_url')
        else:
            return []

    def get_cover_data(self, url):
        try:
            handler = gio.File(url).read()
            data = handler.read()
            return data
        except glib.GError:
            return None      
        


########NEW FILE########
__FILENAME__ = doubanfm_dbus
# Copyright (C) 2008-2011 Sun Ning <classicning@gmail.com>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2, or (at your option)
# any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.
#
#
# The developers of the Exaile media player hereby grant permission
# for non-GPL compatible GStreamer and Exaile plugins to be used and
# distributed together with GStreamer and Exaile. This permission is
# above and beyond the permissions granted by the GPL license by which
# Exaile is covered. If you modify this code, you may extend this
# exception to your version of the code, but you are not obligated to
# do so. If you do not wish to do so, delete this exception statement
# from your version.

import dbus

from xl import event

DOUBANFM_INTERFACE_NAME="info.sunng.ExaileDoubanfm"

class DoubanFMDBusService(dbus.service.Object):
    def __init__(self, dbfm_plugin, bus):
        dbus.service.Object.__init__(self, bus, '/info/sunng/ExaileDoubanfm')
        self.dbfm_plugin = dbfm_plugin

    def populate(self, *prop_names):
        props = {}
        for p in prop_names:
            props[p] = getattr(self, p)()
        self.StatusChanged(props)

#    @dbus.service.method(dbus.PROPERTIES_IFACE, in_signature='ss', out_signature='v')
#    def Get(self, interface, prop):
#        if hasattr(self, prop):
#            result = getattr(self, prop)()
#            return result
#        return None

    @dbus.service.signal(DOUBANFM_INTERFACE_NAME, signature='a{sv}')
    def StatusChanged(self, updated):
        #logger.info("fired")
        pass

    @dbus.service.method(DOUBANFM_INTERFACE_NAME)
    def Favorite(self):
        self.dbfm_plugin.mark_as_like(self.__get_current_track())

    @dbus.service.method(DOUBANFM_INTERFACE_NAME)
    def Unfavorite(self):
        self.dbfm_plugin.mark_as_dislike(self.__get_current_track())

    @dbus.service.method(DOUBANFM_INTERFACE_NAME)
    def ToggleFavorite(self):
        current_track = self.__get_current_track()
        if current_track.get_tag_raw('fav')[0] == '0':
            self.dbfm_plugin.mark_as_like(current_track)
        else:
            self.dbfm_plugin.mark_as_dislike(current_track)

    @dbus.service.method(DOUBANFM_INTERFACE_NAME)
    def Skip(self):
        self.dbfm_plugin.mark_as_skip(self.__get_current_track())

    @dbus.service.method(DOUBANFM_INTERFACE_NAME)
    def Delete(self):
        self.dbfm_plugin.mark_as_skip(self.__get_current_track())

    #### dbus properties to expose

    def Metadata(self):
        metadata = {}
        current_track = self.__get_current_track()
        metadata['title'] = current_track.get_tag_raw('title')[0]
        metadata['artist'] = current_track.get_tag_raw('artist')[0]
        metadata['channel_id'] = self.dbfm_plugin.get_current_channel()

        for k,v in self.dbfm_plugin.channels.items():
            if v == metadata['channel_id']:
                metadata['channel_name'] = k
                break

        metadata['cover_url'] = current_track.get_tag_raw('cover_url')[0]
        metadata['like']  = current_track.get_tag_raw('fav')[0]
        return dbus.types.Dictionary(metadata, signature='sv', variant_level=1)

    def Status(self):
        return self.status

    ### helpers
    def __get_current_track(self):
        return self.dbfm_plugin.get_current_track()

class DoubanFMDBusController(object):
    DBUS_OBJECT_NAME = 'info.sunng.ExaileDoubanfm.instance'
    def __init__(self, dbfm_plugin):
        self.dbfm_plugin = dbfm_plugin
        self.bus = None

    def acquire_dbus(self):
        if self.bus:
            self.bus.get_bus().request_name(self.DBUS_OBJECT_NAME)
        else:
            self.bus = dbus.service.BusName(self.DBUS_OBJECT_NAME, bus=dbus.SessionBus())
        self.adapter = DoubanFMDBusService(self.dbfm_plugin, self.bus)

    def release_dbus(self):
        if self.adapter is not None:
            self.adapter.remove_from_connection()
        if self.bus is not None:
            self.bus.get_bus().release_name(self.bus.get_name())

    def register_events(self):
        event.add_callback(self.playback_started, 'playback_track_start')
        event.add_callback(self.playback_stopped, 'playback_track_end')
        event.add_callback(self.on_exit, 'quit_application')

    def unregister_events(self):
        event.remove_callback(self.playback_started, 'playback_track_start')
        event.remove_callback(self.playback_stopped, 'playback_track_end')
        event.remove_callback(self.on_exit, 'quit_application')

    def playback_started(self, *e):
        self.adapter.status = "Playing"
        self.adapter.populate(*['Status', 'Metadata'])

    def playback_stopped(self, *e):
        self.adapter.status = "Stop"
        self.adapter.populate(*['Status'])

    def on_init(self, *e):
        self.adapter.status = "Init"
        self.adapter.populate(*['Status'])

    def on_exit(self, *e):
        self.adapter.status = "Exit"
        self.adapter.populate(*['Status'])



########NEW FILE########
__FILENAME__ = doubanfm_mode
# -*- coding: utf-8 -*-
# Copyright (C) 2008-2012 Sun Ning <classicning@gmail.com>
# Copyright (C) 2012 Yu Shijun <yushijun110@gmail.com>
# Copyright (C) 2012 Liu Guyue <watermelonlh@gmail.com>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2, or (at your option)
# any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.
#
#
# The developers of the Exaile media player hereby grant permission
# for non-GPL compatible GStreamer and Exaile plugins to be used and
# distributed together with GStreamer and Exaile. This permission is
# above and beyond the permissions granted by the GPL license by which
# Exaile is covered. If you modify this code, you may extend this
# exception to your version of the code, but you are not obligated to
# do so. If you do not wish to do so, delete this exception statement
# from your version.

import gtk
import gtk.glade
import pango
import cairo
import os

import urllib

from xl import xdg, event, settings, player
from xlgui import cover, tray
from xlgui.widgets.playback import PlaybackProgressBar
from xlgui.widgets import info, playback
from xl.nls import gettext as _

from libdoubanfm import DoubanTrack

def get_resource_path(filename):
    basedir = os.path.dirname(os.path.realpath(__file__))
    resource = os.path.join(basedir, filename)
    return resource

class DoubanFMMode():
    def __init__(self, exaile, doubanfm_plugin):
        self.exaile = exaile
        self.dbfm_plugin = doubanfm_plugin

        self.builder = gtk.Builder()
        self.builder.add_from_file(get_resource_path('doubanfm_mode.ui'))

        self.builder.connect_signals({
            'on_bookmark_button_clicked': self.on_bookmark_button_clicked,
            'on_skip_button_clicked': self.on_skip_button_clicked,
            'on_delete_button_clicked': self.on_delete_button_clicked,
            'on_go_home_button_clicked': self.on_go_home_button_clicked,
            'on_item_setting_clicked': self.on_button_setting_clicked,
            'on_item_album_clicked': self.on_button_album_clicked,
            'on_item_report_clicked': self.on_button_report_clicked,
            'on_menu_toggle': self.on_menu_toggle,
            'on_quit': self.on_quit,
            'on_pausebutton_clicked': self.on_pausebutton_clicked,
            'on_recommend_song': self.on_recommend_song,
            'on_share_sina': self.on_share_sina,
            'on_share_renren': self.on_share_renren,
            'on_share_kaixin001': self.on_share_kaixin001,
            'on_share_twitter': self.on_share_twitter,
            'on_share_fanfou': self.on_share_fanfou,
            'on_copy_permalink': self.on_copy_permalink,
        })

        self.window = self.builder.get_object('doubanfm_mode_window')
        self.window.connect('destroy', self.hide)

        volume = settings.get_option('player/volume', 1)

        self.volume_control = playback.VolumeControl(player.PLAYER)
        self.builder.get_object('hbox2').pack_start(self.volume_control)

        self.cover_box = self.builder.get_object('cover_eventbox1')
        self.info_area = info.TrackInfoPane(player.PLAYER)
        self.cover = cover.CoverWidget(self.cover_box,player.PLAYER)
#        self.cover_box.add(self.cover)

        self.track_title_label = self.builder.get_object('track_title_label')
        attr = pango.AttrList()
        attr.change(pango.AttrWeight(pango.WEIGHT_BOLD, 0, 800))
        attr.change(pango.AttrSize(12500, 0, 600))
        self.track_title_label.set_attributes(attr)
        self.track_info_label = self.builder.get_object('track_info_label')

        self.bookmark_button = self.builder.get_object('bookmark_button')
        self.trash_button = self.builder.get_object('delete_button')
        self.skip_button = self.builder.get_object('skip_button')
        self.pause_button = self.builder.get_object('pause_button')

        self.popup_menu = self.builder.get_object('moremenu')

        self.report_menuitem = self.builder.get_object('menuitem1')
        self.album_menuitem = self.builder.get_object('menuitem2')
        self.recmd_menuitem = self.builder.get_object('menuitem10')

        self.sensitive_widgets = [
            self.bookmark_button,
            self.trash_button,
            self.skip_button,
            self.pause_button,
            self.report_menuitem,
            self.album_menuitem,
            self.recmd_menuitem,
        ]

        self.progress_bar = playback.PlaybackProgressBar(player.PLAYER)
        self.builder.get_object('vbox2').pack_start(self.progress_bar)

        self.visible = False
        self.active = False

        self._build_channel_menu()

        event.add_callback(self.on_playback_start, 'playback_track_start', player.PLAYER)
        event.add_callback(self.on_playback_stop, 'playback_track_end', player.PLAYER)
        event.add_callback(self.on_pausebutton_toggled, 'playback_toggle_pause', player.PLAYER)
        event.add_callback(self.on_tag_update, 'track_tags_changed')
        self._toggle_id = self.exaile.gui.main.connect('main-visible-toggle', self.toggle_visible)

        ## added for 0.3.2
        self._init_alpha()

    def _build_channel_menu(self):
        menu = self.builder.get_object('channel_menu')

        group = None

        for channel_name in self.dbfm_plugin.channels.keys():
            menuItem = gtk.RadioMenuItem(group, _(channel_name))
            group = group or menuItem

            menuItem.connect('toggled', self.on_channel_group_change,
                    self.dbfm_plugin.channels[channel_name])

            menu.prepend(menuItem)
            menuItem.show()

    def _init_alpha(self):
        if settings.get_option('gui/use_alpha', False):
            screen = self.window.get_screen()
            colormap = screen.get_rgba_colormap()

            if colormap is not None:
                self.window.set_app_paintable(True)
                self.window.set_colormap(colormap)

                self.window.connect('expose-event', self.on_expose_event)
                self.window.connect('screen-changed', self.on_screen_changed)

    def on_expose_event(self, widget, event):
        """
            Paints the window alpha transparency
        """
        opacity = 1 - settings.get_option('gui/transparency', 0.3)
        context = widget.window.cairo_create()
        background = widget.style.bg[gtk.STATE_NORMAL]
        context.set_source_rgba(
            float(background.red) / 256**2,
            float(background.green) / 256**2,
            float(background.blue) / 256**2,
            opacity
        )
        context.set_operator(cairo.OPERATOR_SOURCE)
        context.paint()

    def on_screen_changed(self, widget, event):
        """
            Updates the colormap on screen change
        """
        screen = widget.get_screen()
        colormap = screen.get_rgba_colormap() or screen.get_rgb_colormap()
        self.window.set_colormap(rgbamap)

    def toggle_visible(self, *e):
        if not self.active:
            return False

        if self.visible:
            self.window.hide()
        else:
            self.window.show_all()
        self.visible = not self.visible
        return True

    def show(self, *e):
        if not self.visible:
            self.exaile.gui.main.window.hide()

            self.window.show_all()
            self.visible = True
            self.active = True

    def hide(self, *e):
        if self.visible:
            self.window.hide()
            self.exaile.gui.main.window.show()
            self.visible = False
            self.active = False

    def on_bookmark_button_clicked(self, *e):
        track = self.dbfm_plugin.get_current_track()

        if track.get_tag_raw("fav")[0] == "1":
            self.dbfm_plugin.mark_as_dislike(track)
        else :
            self.dbfm_plugin.mark_as_like(track)

    def on_skip_button_clicked(self, *e):
        track = self.dbfm_plugin.get_current_track()
        self.dbfm_plugin.mark_as_skip(track)

    def on_delete_button_clicked(self, *e):
        track = self.dbfm_plugin.get_current_track()
        self.dbfm_plugin.mark_as_recycle(track)

    def on_go_home_button_clicked(self, *e):
        self.hide(e)

    def on_playback_start(self, etype, player, *data):
        track = player.current
        artist = track.get_tag_raw('artist')[0]
        album = track.get_tag_raw('album')[0]
        title = track.get_tag_raw('title')[0]

        self.window.set_title(u"Exaile \u8c46\u74e3FM %s - %s" % (title, artist))
        self.track_title_label.set_label("%s - %s" %(title, artist))
        self.track_info_label.set_label(album)

        if track.get_tag_raw('fav')[0] == "1":
            self.bookmark_button.set_image(
                    gtk.image_new_from_icon_name('emblem-favorite', gtk.ICON_SIZE_BUTTON))
        else:
            self.bookmark_button.set_image(
                    gtk.image_new_from_icon_name('bookmark-new', gtk.ICON_SIZE_BUTTON))

        self.sensitive(True)
        self.pause_button.set_image(
                gtk.image_new_from_stock('gtk-media-pause', gtk.ICON_SIZE_BUTTON))

    def on_tag_update(self, e, track, tag):
        if track != self.dbfm_plugin.get_current_track():
            return 

        if track.get_tag_raw('fav')[0] == "1":
            self.bookmark_button.set_image(
                    gtk.image_new_from_icon_name('emblem-favorite', gtk.ICON_SIZE_BUTTON))
        else:
            self.bookmark_button.set_image(
                    gtk.image_new_from_icon_name('bookmark-new', gtk.ICON_SIZE_BUTTON))

    def on_playback_stop(self, type, player, data):
        self.pause_button.set_image(
                gtk.image_new_from_stock('gtk-media-play', gtk.ICON_SIZE_BUTTON))
        self.sensitive(False)

    def sensitive(self, enable):
        for w in self.sensitive_widgets:
            w.set_sensitive(enable)

    def on_button_setting_clicked(self, *e):
        os.popen(' '.join(['xdg-open', 'http://douban.fm/mine']))

    def on_button_album_clicked(self, *e):
        track = self.dbfm_plugin.get_current_track()
        if track is not None:
            aid = track.get_tag_raw('aid')[0]
            url = "http://music.douban.com/subject/%s/" % aid
            os.popen(' '.join(['xdg-open', url]))

    def on_button_report_clicked(self, *e):
        track = self.dbfm_plugin.get_current_track()
        if track is not None:
            aid = track.get_tag_raw('aid')[0]
            sid = track.get_tag_raw('sid')[0]
            url = "http://music.douban.com/subject/%s/report?song_id=%s" % (aid, sid)
            os.popen(' '.join(['xdg-open', url]))

    def on_share_sina(self, *e):
        track = self.dbfm_plugin.get_current_track()
        url = self.dbfm_plugin.share('sina', track)
        os.popen(' '.join(['xdg-open', '"%s"'%url]))

    def on_share_kaixin001(self, *e):
        track = self.dbfm_plugin.get_current_track()
        url = self.dbfm_plugin.share('kaixin001', track)
        os.popen(' '.join(['xdg-open', '"%s"'%url]))

    def on_share_renren(self, *e):
        track = self.dbfm_plugin.get_current_track()
        url = self.dbfm_plugin.share('renren', track)
        os.popen(' '.join(['xdg-open', '"%s"'%url]))

    def on_share_twitter(self, *e):
        track = self.dbfm_plugin.get_current_track()
        url = self.dbfm_plugin.share('twitter', track)
        os.popen(' '.join(['xdg-open', '"%s"'%url]))

    def on_share_fanfou(self, *e):
        track = self.dbfm_plugin.get_current_track()
        url = self.dbfm_plugin.share('fanfou', track)
        os.popen(' '.join(['xdg-open', '"%s"'%url]))

    def destroy(self):
        self.window.destroy()
        event.remove_callback(self.on_playback_start, 'playback_track_start')
        event.remove_callback(self.on_playback_stop, 'playback_track_end')
        event.remove_callback(self.on_track_update, 'track_tags_changed')
        self.exaile.gui.main.disconnect(self._toggle_id)

    def on_menu_toggle(self, widget, e):
        self.popup_menu.popup(None, None, None, e.button, e.time)
        return True

    def on_quit(self, *e):
        self.exaile.gui.main.quit()

    def on_recommend_song(self, *e):
        track = self.dbfm_plugin.get_current_track()
        url = self.dbfm_plugin.share('douban', track)
        os.popen(' '.join(['xdg-open', '"%s"'%url]))

    def on_channel_group_change(self, item, data):
        channel_id = data

        self.dbfm_plugin.close_playlist(None, self.exaile, None)
        self.dbfm_plugin.active_douban_radio(None, channel_id, True)

        self.show()

    def on_pausebutton_clicked(self, *e):
        if player.PLAYER.is_paused() or player.PLAYER.is_playing():
            player.PLAYER.toggle_pause()

    def on_pausebutton_toggled(self, type, player, data):
        if player.is_paused():
            ## switch to play icon
            self.pause_button.set_image(
                    gtk.image_new_from_stock('gtk-media-play', gtk.ICON_SIZE_BUTTON))
            self.sensitive(False)
            self.pause_button.set_sensitive(True)
        else:
            ## switch back
            self.pause_button.set_image(
                    gtk.image_new_from_stock('gtk-media-pause', gtk.ICON_SIZE_BUTTON))
            self.sensitive(True)

    def on_copy_permalink(self, *e):
        track = self.dbfm_plugin.get_current_track()
        sid = track.get_tag_raw('sid')[0]
        ssid = track.get_tag_raw('ssid')[0]
        t = DoubanTrack(sid=sid, ssid=ssid)
        url = t.get_uri()
        c = gtk.Clipboard()
        c.set_text(url)


########NEW FILE########
__FILENAME__ = libdoubanfm-test
import unittest

from libdoubanfm import DoubanFM, DoubanLoginException

class TestLibDoubanfm(unittest.TestCase):
    def setUp(self):
        self.libdbfm = DoubanFM('a2721891@bofthew.com', '123456')
        
    def test_recommend(self):
        self.libdbfm.recommend('1849980','Just for test')

    def test_playlist(self):
        result = self.libdbfm.new_playlist()
        self.assertNotEqual(None, result)
        self.assertTrue(len(result) > 0)

    def test_login_fail(self):
        try:
            lidbfm = DoubanFM('not_a_user_name', '111')
            self.fail('should not here')
        except DoubanLoginException:
            self.assertTrue(True)


if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = libdoubanfm
# -*- coding: utf-8 -*-
# Copyright (C) 2008-2012 Sun Ning <classicning@gmail.com>
# Copyright (C) 2012 Yu Shijun <yushijun110@gmail.com>
# Copyright (C) 2012 Liu Guyue <watermelonlh@gmail.com>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2, or (at your option)
# any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.
#
#
# The developers of the Exaile media player hereby grant permission
# for non-GPL compatible GStreamer and Exaile plugins to be used and
# distributed together with GStreamer and Exaile. This permission is
# above and beyond the permissions granted by the GPL license by which
# Exaile is covered. If you modify this code, you may extend this
# exception to your version of the code, but you are not obligated to
# do so. If you do not wish to do so, delete this exception statement
# from your version.


import urllib
import httplib
import json
import re
import random
import contextlib
from Cookie import SimpleCookie
from xl import player
__all__ = ['DoubanFM', 'DoubanLoginException', 'DoubanFMChannels']

class DoubanTrack(object):
    def __init__(self, **data):
        self.props = {}
        for name in data:
            self.props[name] = data[name]

    def get_start_value(self):
        return "%sg%sg0" % (self.sid, self.ssid)

    def get_uri(self):
        return "http://douban.fm/?start=%s&cid=0" % (self.get_start_value())

    def __getattr__(self, name):
        if name in self.props:
            return self.props[name]
        else:
            return None

class DoubanLoginException(Exception):
    def __init__(self, **kwargs):
        self.data = kwargs


class DoubanFM(object):
    def __init__ (self, username, password, captcha_id=None, captcha_solution=None):
        """Initialize a douban.fm session.
        * username - the user's email on douban.com
        * password - the user's password on douban.com
        """

        self.uid = None
        self.dbcl2 = None
        self.bid = None
        self._channel = 0
        self.__login(username, password, captcha_id, captcha_solution)
        self.__load_channels()

    def __load_channels(self):
        f = urllib.urlopen('http://www.douban.com/j/app/radio/channels')
        #f = urllib.urlopen('http://www.douban.com/j/app/radio/channels?version=100&app_name=radio_desktop_win')
        data = f.read()
        f.close()
        channels = json.loads(data)
        self.channels = {}
        #red channel
        self.channels['Red Heart'] = -3
        #Personal Radio High
        #self.channels['Personal Radio High'] = -4
        #Personal Radio Easy
        #self.channels['Personal Radio Easy'] = -5
        for channel in channels['channels']:
            self.channels[channel['name_en']] = channel['channel_id']

    @property
    def channel(self):
        """ current channel """
        return self._channel

    @channel.setter
    def channel(self, value):
        """ setter for current channel
        * value - channel id, **not channel name**
        """
        self._channel = value

    def __login(self, username, password, captcha_id=None, captcha_solution=None):
        """
        login douban, get the session token
        """
        if self.bid is None:
            self.__get_login_data()
        login_form = {'source':'simple',
                'form_email':username, 'form_password':password}
        if captcha_id is not None:
            login_form['captcha-id'] = captcha_id
            login_form['captcha-solution'] = captcha_solution
        data = urllib.urlencode(login_form)
        contentType = "application/x-www-form-urlencoded"

        cookie = 'bid="%s"' % self.bid

        headers = {"Content-Type":contentType, "Cookie": cookie }
        with contextlib.closing(httplib.HTTPSConnection("www.douban.com")) as conn:
            conn.request("POST", "/accounts/login", data, headers)

            r1 = conn.getresponse()
            resultCookie = SimpleCookie(r1.getheader('Set-Cookie'))

            if not resultCookie.has_key('dbcl2'):
                data = {}
                redir = r1.getheader('location')
                if redir:
                    redir_page = urllib.urlopen(redir).read()
                    captcha_data = self.__check_login_captcha(redir_page)
                    data['captcha_id'] = captcha_data
                raise DoubanLoginException(**data)

            dbcl2 = resultCookie['dbcl2'].value
            if dbcl2 is not None and len(dbcl2) > 0:
                self.dbcl2 = dbcl2

                uid = self.dbcl2.split(':')[0]
                self.uid = uid

    def __check_login_captcha(self, webpage):
        captcha_re = re.compile(r'captcha\?id=([\w\d]+?)&amp;')
        finder = captcha_re.search(webpage)
        if finder:
            return finder.group(1)
        else:
            return None

    def __get_login_data(self):
        conn = httplib.HTTPConnection("www.douban.com")
        conn.request("GET", "/")
        resp = conn.getresponse()
        cookie = resp.getheader('Set-Cookie')
        cookie = SimpleCookie(cookie)
        conn.close()
        if not cookie.has_key('bid'):
            raise DoubanLoginException()
        else:
            self.bid = cookie['bid'].value

            return self.bid

    def __format_list(self, sidlist, verb=None):
        """
        for sidlist with ite verb status
        """
        if sidlist is None or len(sidlist) == 0:
            return ''
        else:
            if verb is not None:
                return ''.join(map(lambda s: '|'+str(s)+':'+str(verb), sidlist))
            else:
                return ''.join(map(lambda s: '|'+str(s), sidlist))

    def __get_default_params (self, typename=None):
        """
        default request parameters, for override
        """
        params = {}
        for i in ['aid', 'channel', 'du', 'h', 'r', 'rest', 'sid', 'type', 'uid']:
            params[i] = ''

        params['r'] = random.random()
        params['uid'] = self.uid
        params['channel'] = self.channel
        params['pb'] = 64
        params['pt'] = player.PLAYER.get_time() 
        params['from'] = 'mainsite'
        
        if typename is not None:
            params['type'] = typename
        return params

    def __remote_fm(self, params, start=None):
        """
        io with douban.fm
        """
        data = urllib.urlencode(params)
        if start is not None:
            cookie = 'dbcl2="%s"; bid="%s"; start="%s"' % (self.dbcl2, self.bid, start)
        else:
            cookie = 'dbcl2="%s"; bid="%s"' % (self.dbcl2, self.bid)
        header = {"Cookie": cookie}
        with contextlib.closing(httplib.HTTPConnection("douban.fm")) as conn:
            conn.request('GET', "/j/mine/playlist?"+data, None, header)
            result = conn.getresponse().read()
            return result

### playlist related
    def json_to_douban_tracks(self, item):
        return DoubanTrack(**item)

    def new_playlist(self, history=[]):
        """
        retrieve a new playlist
        * history -  history song ids. optional.
        """
        params = self.__get_default_params('n')
        params['h'] = self.__format_list(history, True)

        results = self.__remote_fm(params)

        return map(self.json_to_douban_tracks, json.loads(results)['song'])

    def del_song(self, sid, aid, rest=[]):
        """
        delete a song from your playlist
        * sid - song id
        * aid - album id
        * rest - rest song ids in current playlist
        """
        params = self.__get_default_params('b')
        params['sid'] = sid
        params['aid'] = aid
        params['rest'] = self.__format_list(rest)

        results = self.__remote_fm(params)
        return map(self.json_to_douban_tracks, json.loads(results)['song'])

    def fav_song(self, sid, aid):
        """
        mark a song as favorite
        * sid - song id
        * aid - album id
        """
        params = self.__get_default_params('r')
        params['sid'] = sid
        params['aid'] = aid

        self.__remote_fm(params)
        ## ignore the response

    def unfav_song(self, sid, aid):
        """
        unmark a favorite song
        * sid - song id
        * aid - album id
        """
        params = self.__get_default_params('u')
        params['sid'] = sid
        params['aid'] = aid

        self.__remote_fm(params)

    def skip_song(self, sid, aid, history=[]):
        """
        skip a song, tell douban that you have skipped the song.
        * sid - song id
        * aid - album id
        * history - your playlist history(played songs and skipped songs)
        """
        params = self.__get_default_params('s')
        params['h'] = self.__format_list(history[:50])
        params['sid'] = sid
        params['aid'] = aid

        results = self.__remote_fm(params)
        return map(self.json_to_douban_tracks, json.loads(results)['song'])

    def played_song(self, sid, aid, du=0):
        """
        tell douban that you have finished a song
        * sid - song id
        * aid - album id
        * du - time your have been idle
        """
        params  = self.__get_default_params('e')
        params['sid'] = sid
        params['aid'] = aid
        params['du'] = du

        self.__remote_fm(params)

    def played_list(self, sid, history=[]):
        """
        request more playlist items
        * history - your playlist history(played songs and skipped songs)
        """
        params = self.__get_default_params('p')
        params['h'] = self.__format_list(history[:50])
        params['sid'] = sid

        results = self.__remote_fm(params)
        return map(self.json_to_douban_tracks, json.loads(results)['song'])

#### recommand related

    def __parse_ck(self, content):
        """parse ck from recommend form"""
        prog = re.compile(r'name=\\"ck\\" value=\\"([\w\d]*?)\\"')
        finder = prog.search(content)
        if finder:
            return finder.group(1)
        return None

    def recommend(self, uid, comment, title=None, t=None, ck=None):
        """recommend a uid with some comment. ck is optional, if
        not provided, we will try to fetch a ck."""

        t = t or 'W'
        if ck is None:
        ## get recommend ck
            url = "http://www.douban.com/j/recommend?type=%s&uid=%s&rec=" % (t,uid)
            with contextlib.closing(httplib.HTTPConnection("music.douban.com")) as conn:
                cookie =  'dbcl2="%s"; bid="%s"; ' % (self.dbcl2, self.bid)
                conn.request('GET', url, None, {'Cookie': cookie})
                result = conn.getresponse().read()
                ck = self.__parse_ck(result)

        if ck:
            post = {'ck':ck, 'comment':comment, 'novote':1, 'type':t, 'uid':uid}
            if title:
                post['title'] = title

            ## convert unicode chars to bytes
            data = urllib.urlencode(post)
            ## ck ?
            cookie = 'dbcl2="%s"; bid="%s"; ck=%s' % (self.dbcl2, self.bid, ck)
            accept = 'application/json'
            content_type= 'application/x-www-form-urlencoded; charset=UTF-8'
            header = {"Cookie": cookie, "Accept": accept,
                    "Content-Type":content_type, }

            with contextlib.closing(httplib.HTTPConnection("www.douban.com")) as conn:
                conn.request('POST', "/j/recommend", data, header)
                conn.getresponse().read()




########NEW FILE########
