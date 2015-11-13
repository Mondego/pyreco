__FILENAME__ = App

# Copyright (C) 2013-2014 LiuLang <gsushzhsosgsu@gmail.com>

# Use of this source code is governed by GPLv3 license that can be found
# in the LICENSE file.

import os
import sys
from gi.repository import Gdk
from gi.repository import GdkPixbuf
from gi.repository import GObject
from gi.repository import Gtk

from kuwo import Config
# ~/.config/kuwo and ~/.cache/kuwo need to be created at first time
Config.check_first()
_ = Config._
from kuwo.Artists import Artists
from kuwo.Lrc import Lrc
from kuwo.MV import MV
from kuwo.Player import Player
from kuwo.PlayList import PlayList
from kuwo.Radio import Radio
from kuwo.Search import Search
from kuwo.Themes import Themes
from kuwo.TopCategories import TopCategories
from kuwo.TopList import TopList
from kuwo.Shortcut import Shortcut

if Gtk.MAJOR_VERSION <= 3 and Gtk.MINOR_VERSION < 10:
    GObject.threads_init()
DBUS_APP_NAME = 'org.liulang.kwplayer'


class App:
    def __init__(self):
        self.app = Gtk.Application.new(DBUS_APP_NAME, 0)
        self.app.connect('startup', self.on_app_startup)
        self.app.connect('activate', self.on_app_activate)
        self.app.connect('shutdown', self.on_app_shutdown)

        self.conf = Config.load_conf()
        self.theme, self.theme_path = Config.load_theme()

    def on_app_startup(self, app):
        self.window = Gtk.ApplicationWindow(application=app)
        self.window.set_default_size(*self.conf['window-size'])
        self.window.set_title(Config.APPNAME)
        self.window.props.hide_titlebar_when_maximized = True
        self.window.set_icon(self.theme['app-logo'])
        app.add_window(self.window)
        self.window.connect('check-resize', self.on_main_window_resized)
        self.window.connect('delete-event', self.on_main_window_deleted)

        self.accel_group = Gtk.AccelGroup()
        self.window.add_accel_group(self.accel_group)

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.window.add(box)

        self.player = Player(self)
        box.pack_start(self.player, False, False, 0)

        self.notebook = Gtk.Notebook()
        self.notebook.props.tab_pos = Gtk.PositionType.BOTTOM
        self.notebook.get_style_context().add_class('main_tab')
        box.pack_start(self.notebook, True, True, 0)

        self.init_notebook()
        self.notebook.connect('switch-page', self.on_notebook_switch_page)
        self.init_status_icon()

        # load default styles when all widgets have been constructed.
        self.load_styles()

    def on_app_activate(self, app):
        self.window.show_all()
        # Make some changes after main window is shown.
        # Like hiding some unnecessory widgets.
        self.lrc.after_init()
        self.artists.after_init()
        self.player.after_init()
        self.search.after_init()
        self.shortcut = Shortcut(self.player)

    def on_app_shutdown(self, app):
        Config.dump_conf(self.conf)

    def run(self, argv):
        self.app.run(argv)

    def quit(self):
        gdk_win = self.window.get_window()
        if gdk_win and not gdk_win.is_destroyed():
            self.window.destroy()
        self.shortcut.quit()
        self.app.quit()

    def on_main_window_resized(self, window, event=None):
        self.conf['window-size'] = window.get_size()

    def on_main_window_deleted(self, window, event):
        if self.conf['use-status-icon']:
            window.hide()
            return True
        else:
            return False

    def init_notebook(self):
        self.tab_first_show = []
        self.lrc = Lrc(self)
        self.append_page(self.lrc)

        self.playlist = PlayList(self)
        self.append_page(self.playlist)

        self.search = Search(self)
        self.append_page(self.search)

        self.toplist = TopList(self)
        self.append_page(self.toplist)

        self.radio = Radio(self)
        self.append_page(self.radio)

        self.mv = MV(self)
        self.append_page(self.mv)

        self.artists = Artists(self)
        self.append_page(self.artists)

        self.topcategories = TopCategories(self)
        self.append_page(self.topcategories)

        self.themes = Themes(self)
        self.append_page(self.themes)

    def on_notebook_switch_page(self, notebook, page, page_num):
        if page not in self.tab_first_show:
            page.first()
            self.tab_first_show.append(page)

    def append_page(self, widget):
        '''Append a new widget to notebook.'''
        label = Gtk.Label(widget.title)
        widget.app_page = self.notebook.append_page(widget, label)

    def popup_page(self, page):
        '''Switch to this widget in notebook.'''
        self.notebook.set_current_page(page)

    def apply_css(self, widget, css, old_provider=None, overall=False):
        '''Update CssProvider of this widget.'''
        # CssProvider needs bytecode
        style_provider = Gtk.CssProvider()
        css_encoded = css.encode()
        style_provider.load_from_data(css_encoded)
        if overall:
            Gtk.StyleContext.add_provider_for_screen(
                Gdk.Screen.get_default(), style_provider,
                Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
            if old_provider:
                Gtk.StyleContext.remove_provider_for_screen(
                    Gdk.Screen.get_default(), style_provider)
        else:
            widget.get_style_context().add_provider(
                    style_provider,Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)
            if old_provider:
                widget.get_style_context().remove_provider(old_provider)
        return style_provider

    def load_styles(self):
        '''Load default CssStyle.'''
        if Config.GTK_LE_36:
            css = '\n'.join([
                # transition-property is not supported in Gtk3.4
                #'GtkScrolledWindow.lrc_window {',
                #    'transition-property: background-image;',
                #    'transition-duration: 1s;',
                #    '}',
                'GtkScale {',
                    'outline-color: transparent;',
                    'outline-offset: 0;',
                    'outline-style: none;',
                    'outline-width: 0;',
                    '}',
                'GtkTextView.lrc_tv {',
                    'font-size: {0};'.format(self.conf['lrc-text-size']),
                    'color: {0};'.format(self.conf['lrc-text-color']),
                    'border-radius: 0 25 0 50;',
                    'border-width: 5;',
                    'background-color: {0};'.format(
                        self.conf['lrc-back-color']),
                    '}',
                '.info-label {',
                    'color: rgb(136, 139, 132);',
                    'font-size: 9;',
                    '}',
                ])
        else:
            css = '\n'.join([
                'GtkScrolledWindow.lrc_window {',
                    'transition-property: background-image;',
                    'transition-duration: 1s;',
                    '}',
                'GtkScale {',
                    'outline-color: transparent;',
                    'outline-offset: 0;',
                    'outline-style: none;',
                    'outline-width: 0;',
                    '}',
                'GtkTextView.lrc_tv {',
                    'font-size: {0}px;'.format(self.conf['lrc-text-size']),
                    'color: {0};'.format(self.conf['lrc-text-color']),
                    'border-radius: 0px 25px 0px 50px;',
                    'border-width: 5px;',
                    'background-color: {0};'.format(
                        self.conf['lrc-back-color']),
                    '}',
                '.info-label {',
                    'color: rgb(136, 139, 132);',
                    'font-size: 9px;',
                    '}',
                ])

        self.apply_css(self.window, css, overall=True)

        settings = Gtk.Settings.get_default()
        settings.props.gtk_application_prefer_dark_theme = \
                self.conf.get('use-dark-theme', False)

    def init_status_icon(self):
        # set status_icon as class property, to keep its life
        # after function exited
        self.status_icon = Gtk.StatusIcon()
        self.status_icon.set_from_pixbuf(self.theme['app-logo'])
        # left click
        self.status_icon.connect('activate', self.on_status_icon_activate)
        # right click
        self.status_icon.connect('popup_menu', self.on_status_icon_popup_menu)

    def on_status_icon_activate(self, status_icon):
        if self.window.props.visible:
            self.window.hide()
        else:
            self.window.present()

    def on_status_icon_popup_menu(self, status_icon, event_button, 
                                  event_time):
        menu = Gtk.Menu()
        show_item = Gtk.MenuItem(label=_('Show App') )
        show_item.connect('activate', self.on_status_icon_show_app_activate)
        menu.append(show_item)

        pause_item = Gtk.MenuItem(label=_('Pause/Resume'))
        pause_item.connect('activate', self.on_status_icon_pause_activate)
        menu.append(pause_item)

        next_item = Gtk.MenuItem(label=_('Next Song'))
        next_item.connect('activate', self.on_status_icon_next_activate)
        menu.append(next_item)

        sep_item = Gtk.SeparatorMenuItem()
        menu.append(sep_item)
        
        quit_item = Gtk.MenuItem(label=_('Quit'))
        quit_item.connect('activate', self.on_status_icon_quit_activate)
        menu.append(quit_item)

        menu.show_all()
        menu.popup(None, None,
                lambda a,b: Gtk.StatusIcon.position_menu(menu, status_icon),
                None, event_button, event_time)

    def on_status_icon_show_app_activate(self, menuitem):
        self.window.present()

    def on_status_icon_pause_activate(self, menuitem):
        self.player.play_pause()

    def on_status_icon_next_activate(self, menuitem):
        self.player.load_next()

    def on_status_icon_quit_activate(self, menuitem):
        self.quit()

########NEW FILE########
__FILENAME__ = Artists

# Copyright (C) 2013-2014 LiuLang <gsushzhsosgsu@gmail.com>

# Use of this source code is governed by GPLv3 license that can be found
# in the LICENSE file.

import json
import os
import time

from gi.repository import GdkPixbuf
from gi.repository import Gtk

from kuwo import Config
from kuwo import Net
from kuwo import Widgets

_ = Config._


class InfoLabel(Gtk.Label):
    def __init__(self, grid, pref, left, top):
        super().__init__()
        self.props.xalign = 0
        self.props.use_markup = True
        grid.attach(self, left, top, 1, 1)
        self.pref = pref

    def set(self, info, key):
        if info and key in info:
            self.set_label('<b>{0} :</b> {1}'.format(self.pref, info[key]))
        else:
            self.set_label('<b>{0} :</b>'.format(self.pref))


class ArtistButton(Gtk.RadioButton):
    def __init__(self, parent, label, group, tab_index):
        super().__init__(label=label)
        self.props.draw_indicator = False
        if group:
            self.join_group(group)
        self.tab = tab_index
        self.parent = parent
        parent.artist_buttons.pack_start(self, False, False, 0)
        self.connect('toggled', self.on_toggled)

    def on_toggled(self, btn):
        state = self.get_active()
        if not state:
            return
        self.parent.artist_notebook.set_current_page(self.tab)
        methods = [
                self.parent.show_artist_songs,
                self.parent.show_artist_albums,
                self.parent.show_artist_mv,
                self.parent.show_artist_similar,
                self.parent.show_artist_info,
                ]
        methods[self.tab]()


class Artists(Gtk.Box):
    '''Artists tab in notebook.'''

    title = _('Artists')
    first_run = True

    def __init__(self, app):
        super().__init__(orientation=Gtk.Orientation.VERTICAL)
        self.app = app

        self.buttonbox = Gtk.Box()
        self.pack_start(self.buttonbox, False, False, 0)

    def first(self):
        if not self.first_run:
            return
        self.first_run = False

        app = self.app

        home_button = Gtk.Button(_('Artists'))
        home_button.connect('clicked', self.on_home_button_clicked)
        self.buttonbox.pack_start(home_button, False, False, 0)
        self.artist_button = Gtk.Button('')
        self.artist_button.connect('clicked', self.on_artist_button_clicked)
        self.buttonbox.pack_start(self.artist_button, False, False, 0)
        # to show artist name or album name
        self.label = Gtk.Label('')
        self.buttonbox.pack_start(self.label, False, False, 20)

        # control_box for artist's songs
        # checked, name, artist, album, rid, artistid, albumid
        self.artist_songs_liststore = Gtk.ListStore(
                bool, str, str, str, int, int, int)
        self.artist_control_box = Widgets.ControlBox(
                self.artist_songs_liststore, app)
        self.buttonbox.pack_end(self.artist_control_box, False, False, 0)

        # control box for artist's mv
        # pic, name, artist, album, rid, artistid, albumid, tooltip
        self.artist_mv_liststore = Gtk.ListStore(
                GdkPixbuf.Pixbuf, str, str, str, int, int, int, str)
        self.artist_mv_control_box = Widgets.MVControlBox(
                self.artist_mv_liststore, app)
        self.buttonbox.pack_end(self.artist_mv_control_box, False, False, 0)

        # control box for artist's albums
        # checked, name, artist, album, rid, artistid, albumid
        self.album_songs_liststore = Gtk.ListStore(
                bool, str, str, str, int, int, int)
        self.album_control_box = Widgets.ControlBox(
                self.album_songs_liststore, app)
        self.buttonbox.pack_end(self.album_control_box, False, False, 0)

        # main notebook
        self.notebook = Gtk.Notebook()
        self.notebook.set_show_tabs(False)
        self.pack_start(self.notebook, True, True, 0)

        # Artists tab (tab 0)
        self.artists_tab = Gtk.Box()
        self.notebook.append_page(self.artists_tab, Gtk.Label(_('Artists')))
        #self.pack_start(self.box_artists, True, True, 0)

        # left panel of artists tab
        artists_left_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.artists_tab.pack_start(artists_left_box, False, False, 0)
        # artists categories
        # name, id
        self.cate_liststore = Gtk.ListStore(str, int)
        self.cate_treeview = Gtk.TreeView(model=self.cate_liststore)
        self.cate_treeview.props.headers_visible = False
        name = Gtk.CellRendererText()
        col_name = Gtk.TreeViewColumn('Name', name, text=0)
        self.cate_treeview.append_column(col_name)
        artists_left_box.pack_start(self.cate_treeview, False, False, 0)

        # artists prefix
        # disname, prefix
        self.pref_liststore = Gtk.ListStore(str, str)
        self.pref_combo = Gtk.ComboBox(model=self.pref_liststore)
        cell_name = Gtk.CellRendererText()
        self.pref_combo.pack_start(cell_name, True)
        self.pref_combo.add_attribute(cell_name, 'text', 0)
        self.pref_combo.props.margin_top = 15
        artists_left_box.pack_start(self.pref_combo, False, False, 0)

        # favirote artists
        self.fav_yes_img = Gtk.Image.new_from_pixbuf(app.theme['favorite'])
        self.fav_no_img = Gtk.Image.new_from_pixbuf(app.theme['no-favorite'])
        fav_artists_btn = Gtk.Button(_('Favorite'))
        fav_artists_btn.props.margin_top = 20
        fav_artists_btn.props.image = Gtk.Image.new_from_pixbuf(
                app.theme['favorite'])
        if not Config.GTK_LE_36:
            fav_artists_btn.props.always_show_image = True
        fav_artists_btn.connect('clicked', self.on_fav_artists_btn_clicked)
        artists_left_box.pack_start(fav_artists_btn, False, False, 0)

        # main window of artists
        self.artists_win = Gtk.ScrolledWindow()
        self.artists_win.get_vadjustment().connect(
                'value-changed', self.on_artists_win_scrolled)
        self.artists_tab.pack_start(self.artists_win, True, True, 0)
        # icon, artist name, artist id, num of songs, tooltip
        self.artists_liststore = Gtk.ListStore(
                GdkPixbuf.Pixbuf, str, int, str, str)
        artists_iconview = Widgets.IconView(
                self.artists_liststore, tooltip=4)
        artists_iconview.connect(
                'item_activated', self.on_artists_iconview_item_activated)
        self.artists_win.add(artists_iconview)

        # Artist tab (tab 1)
        self.artist_tab = Gtk.Box()
        self.notebook.append_page(self.artist_tab, Gtk.Label(_('Artist')))

        # left panel of artist
        self.artist_buttons = Gtk.Box(
                spacing=5, orientation=Gtk.Orientation.VERTICAL)
        self.artist_buttons.props.margin_top = 15
        self.artist_tab.pack_start(self.artist_buttons, False, False, 0)

        self.artist_songs_button = ArtistButton(
                self, _('Songs'), None, 0)
        self.artist_albums_button = ArtistButton(
                self, _('Albums'), self.artist_songs_button, 1)
        self.artist_mv_button = ArtistButton(
                self, _('MV'), self.artist_songs_button, 2)
        self.artist_similar_button = ArtistButton(
                self, _('Similar'), self.artist_songs_button, 3)
        self.artist_info_button = ArtistButton(
                self, _('Info'), self.artist_songs_button, 4)

        # Add fav_btn to artist_tab
        fav_curr_artist_btn = Gtk.Button()
        fav_curr_artist_btn.props.margin_top = 15
        fav_curr_artist_btn.props.halign = Gtk.Align.CENTER
        fav_curr_artist_btn.props.image = self.fav_no_img
        if not Config.GTK_LE_36:
            fav_curr_artist_btn.props.always_show_image = True
        fav_curr_artist_btn.set_tooltip_text(
                _('Add to favorite artists list'))
        fav_curr_artist_btn.connect(
                'clicked', self.on_fav_curr_artist_btn_clicked)
        self.artist_buttons.pack_start(fav_curr_artist_btn, False, False, 0)
        self.fav_curr_artist_btn = fav_curr_artist_btn

        # main window of artist tab
        self.artist_notebook = Gtk.Notebook()
        self.artist_notebook.set_show_tabs(False)
        self.artist_tab.pack_start(self.artist_notebook, True, True, 0)

        # songs tab for artist (tab 0)
        self.artist_songs_tab = Gtk.ScrolledWindow()
        self.artist_notebook.append_page(
                self.artist_songs_tab, Gtk.Label(_('Songs')))
        artist_songs_treeview = Widgets.TreeViewSongs(
                self.artist_songs_liststore, app)
        self.artist_songs_tab.add(artist_songs_treeview)


        # albums tab for artist (tab 1)
        self.artist_albums_tab = Gtk.ScrolledWindow()
        self.artist_notebook.append_page(
                self.artist_albums_tab, Gtk.Label(_('Albums')))
        # pic, album, albumid, artist, artistid, info/tooltip
        self.artist_albums_liststore = Gtk.ListStore(
                GdkPixbuf.Pixbuf, str, int, str, int, str)
        artist_albums_iconview = Widgets.IconView(
                self.artist_albums_liststore, tooltip=5)
        artist_albums_iconview.connect(
                'item_activated',
                self.on_artist_albums_iconview_item_activated)
        self.artist_albums_tab.add(artist_albums_iconview)

        # MVs tab for artist (tab 2)
        self.artist_mv_tab = Gtk.ScrolledWindow()
        self.artist_notebook.append_page(
                self.artist_mv_tab, Gtk.Label(_('MV')))
        artist_mv_iconview = Widgets.IconView(
                self.artist_mv_liststore, info_pos=2, tooltip=7)
        artist_mv_iconview.connect(
                'item_activated', self.on_artist_mv_iconview_item_activated)
        self.artist_mv_tab.add(artist_mv_iconview)

        # Similar tab for artist (tab 3)
        self.artist_similar_tab = Gtk.ScrolledWindow()
        self.artist_notebook.append_page(
                self.artist_similar_tab, Gtk.Label(_('Similar')))
        # pic, artist name, artist id, num of songs, tooltip
        self.artist_similar_liststore = Gtk.ListStore(
                GdkPixbuf.Pixbuf, str, int, str, str)
        artist_similar_iconview = Widgets.IconView(
                self.artist_similar_liststore, tooltip=4)
        artist_similar_iconview.connect(
                'item_activated',
                self.on_artist_similar_iconview_item_activated)
        self.artist_similar_tab.add(artist_similar_iconview)

        # Info tab for artist (tab 4)
        artist_info_tab = Gtk.ScrolledWindow()
        artist_info_tab_vp = Gtk.Viewport()
        artist_info_tab.add(artist_info_tab_vp)
        artist_info_tab.props.margin_left = 20
        artist_info_tab.props.margin_top = 5
        self.artist_notebook.append_page(
                artist_info_tab, Gtk.Label(_('Info')))
        artist_info_box = Gtk.Box(
                spacing=10, orientation=Gtk.Orientation.VERTICAL)
        artist_info_box.props.margin_right = 10
        artist_info_box.props.margin_bottom = 10
        artist_info_tab_vp.add(artist_info_box)

        artist_info_hbox = Gtk.Box(spacing=20)
        artist_info_box.pack_start(artist_info_hbox, False, False, 0)

        self.artist_info_pic = Gtk.Image()
        self.artist_info_pic.set_from_pixbuf(app.theme['anonymous'])
        self.artist_info_pic.props.xalign = 0
        self.artist_info_pic.props.yalign = 0
        artist_info_hbox.pack_start(self.artist_info_pic, False, False, 0)
        artist_info_grid = Gtk.Grid()
        artist_info_grid.props.row_spacing = 10
        artist_info_grid.props.column_spacing = 30
        self.artist_info_name = InfoLabel(
                artist_info_grid, _('Name'), 0, 0)
        self.artist_info_birthday = InfoLabel(
                artist_info_grid, _('Birthday'), 0, 1)
        self.artist_info_birthplace = InfoLabel(
                artist_info_grid, _('Birthplace'), 1, 1)
        self.artist_info_height = InfoLabel(
                artist_info_grid, _('Height'), 0, 2)
        self.artist_info_weight = InfoLabel(
                artist_info_grid, _('Weight'), 1, 2)
        self.artist_info_country = InfoLabel(
                artist_info_grid, _('Country'), 0, 3)
        self.artist_info_language = InfoLabel(
                artist_info_grid, _('Language'), 1, 3)
        self.artist_info_gender = InfoLabel(
                artist_info_grid, _('Gender'), 0, 4)
        self.artist_info_constellation = InfoLabel(
                artist_info_grid, _('Constellation'), 1, 4)
        artist_info_hbox.pack_start(artist_info_grid, False, False, 0)

        artist_info_textview = Gtk.TextView()
        self.artist_info_textbuffer = Gtk.TextBuffer()
        artist_info_textview.props.editable = False
        artist_info_textview.props.cursor_visible = False
        artist_info_textview.props.wrap_mode = Gtk.WrapMode.CHAR
        artist_info_textview.set_buffer(self.artist_info_textbuffer)
        artist_info_box.pack_start(artist_info_textview, True, True, 0)

        # Album tab (tab 2)
        album_songs_tab = Gtk.ScrolledWindow()
        self.notebook.append_page(album_songs_tab, Gtk.Label(_('Album')))
        album_songs_treeview = Widgets.TreeViewSongs(
                self.album_songs_liststore, app)
        album_songs_tab.add(album_songs_treeview)

        # Favorite artists tab (tab 3)
        fav_artists_tab = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.notebook.append_page(fav_artists_tab, Gtk.Label(_('Favorite')))
        fav_buttons = Gtk.Box(spacing=5)
        fav_artists_tab.pack_start(fav_buttons, False, False, 0)
        fav_main_btn = Gtk.Button(_('Artists'))
        fav_main_btn.connect('clicked', self.on_fav_main_btn_clicked)
        fav_buttons.pack_start(fav_main_btn, False, False, 0)
        fav_label = Gtk.Label(_('Favorite Artists'))
        fav_buttons.pack_start(fav_label, False, False, 0)
        fav_win = Gtk.ScrolledWindow()
        fav_artists_tab.pack_start(fav_win, True, True, 0)
        # icon, artist name, artist id, tooltip
        self.fav_artists_liststore = Gtk.ListStore(
                GdkPixbuf.Pixbuf, str, int, str)
        fav_artists_iconview = Widgets.IconView(
                self.fav_artists_liststore, info_pos=None, tooltip=3)
        fav_artists_iconview.connect('item_activated',
                self.on_fav_artists_iconview_item_activated)
        fav_win.add(fav_artists_iconview)

        prefs = ((_('All'), ''),
                ('A', 'a'), ('B', 'b'), ('C', 'c'), ('D', 'd'),
                ('E', 'e'), ('F', 'f'), ('G', 'g'), ('H', 'h'), ('I', 'i'),
                ('J', 'j'), ('K', 'k'), ('L', 'l'), ('M', 'm'), ('N', 'n'),
                ('O', 'o'), ('P', 'p'), ('Q', 'q'), ('R', 'r'), ('S', 's'),
                ('T', 't'), ('U', 'u'), ('V', 'v'), ('W', 'w'), ('X', 'x'),
                ('Y', 'y'), ('Z', 'z'), ('#', '%26'),
                )
        for pref in prefs:
            self.pref_liststore.append(pref)
        self.pref_combo.set_active(0)
        self.pref_combo.connect('changed', self.on_cate_changed)

        cates = (
                (_('Hot Artists'), 0),
                (_('Chinese Male'), 1),
                (_('Chinese Female'), 2),
                (_('Chinese Band'), 3),
                (_('Japanese Male'), 4),
                (_('Japanese Female'), 5),
                (_('Japanese Band'), 6),
                (_('European Male'), 7),
                (_('European Female'), 8),
                (_('European Band'), 9),
                (_('Others'), 10),
                )
        for cate in cates:
            self.cate_liststore.append(cate)
        selection = self.cate_treeview.get_selection()
        self.cate_treeview.connect('row_activated', self.on_cate_changed)
        selection.connect('changed', self.on_cate_changed)
        selection.select_path(0)

        # load current favorite artists list
        self.load_fav_artists()
        self.show_all()
        self.buttonbox.hide()

    def after_init(self):
        pass

    def do_destroy(self):
        if not self.first_run:
            self.dump_fav_artists()

    def on_cate_changed(self, *args):
        self.append_artists(init=True)

    def append_artists(self, init=False):
        def on_append_artists(info, error=None):
            artists, self.artists_total = info
            if error or not self.artists_total or not artists:
                return
            urls = []
            tree_iters = []
            for artist in artists:
                _info = ' '.join([artist['music_num'], _(' songs'), ])
                tree_iter = self.artists_liststore.append([
                    self.app.theme['anonymous'],
                    Widgets.unescape(artist['name']),
                    int(artist['id']),
                    _info,
                    Widgets.set_tooltip(artist['name'], _info),
                    ])
                urls.append(artist['pic'])
                tree_iters.append(tree_iter)
            Net.update_artist_logos(
                    self.artists_liststore, 0, tree_iters, urls)

        if init:
            self.artists_liststore.clear()
            self.artists_page = 0
            self.artists_win.get_vadjustment().set_value(0)
        if init or not hasattr(self.artists_liststore, 'timestamp'):
            self.artists_liststore.timestamp = time.time()
        selection = self.cate_treeview.get_selection()
        selected = selection.get_selected()
        if not selected:
            return
        model, _iter = selected
        pref_index = self.pref_combo.get_active()
        catid = model[_iter][1]
        prefix = self.pref_liststore[pref_index][1]
        Net.async_call(
                Net.get_artists, on_append_artists, catid,
                self.artists_page, prefix)

    def on_artists_iconview_item_activated(self, iconview, path):
        model = iconview.get_model()
        artist_name = model[path][1]
        artist_id = model[path][2]
        self.show_artist(artist_name, artist_id)

    # Song window
    def on_home_button_clicked(self, btn):
        self.buttonbox.hide()
        self.notebook.set_current_page(0)

    # scrolled windows
    def on_artists_win_scrolled(self, adj):
        if (Widgets.reach_scrolled_bottom(adj) and 
            self.artists_page < self.artists_total - 1):
            self.artists_page += 1
            self.append_artists()

    # open API
    def show_artist(self, artist, artistid):
        '''Show artist tab'''
        self.first()
        self.curr_artist_name = artist
        self.curr_artist_id = artistid
        self.notebook.set_current_page(1)
        self.artist_songs_inited = False
        self.artist_albums_inited = False
        self.artist_mv_inited = False
        self.artist_similar_inited = False
        self.artist_info_inited = False

        self.buttonbox.show_all()
        self.artist_button.hide()
        self.artist_mv_control_box.hide()
        self.album_control_box.hide()
        self.artist_control_box.select_all()
        self.label.set_label(artist)
        self.app.playlist.advise_new_playlist_name(artist)

        if self.check_artist_favorited(artistid):
            self.fav_curr_artist_btn.props.image = self.fav_yes_img
        else:
            self.fav_curr_artist_btn.props.image = self.fav_no_img

        # switch to `songs` tab
        if self.artist_songs_button.get_active():
            self.show_artist_songs()
        else:
            self.artist_songs_button.set_active(True)

    def show_artist_songs(self):
        '''Show all songs of this artist'''
        self.album_control_box.hide()
        self.artist_mv_control_box.hide()
        self.artist_control_box.show_all()
        if self.artist_songs_inited:
            return
        self.artist_songs_inited = True
        self.append_artist_songs(init=True)

    def append_artist_songs(self, init=False):
        def _append_artist_songs(songs_args, error=None):
            songs, self.artist_songs_total = songs_args
            if error or self.artist_songs_total == 0:
                return
            for song in songs:
                self.artist_songs_liststore.append([
                    True,
                    Widgets.unescape(song['name']),
                    Widgets.unescape(song['artist']),
                    Widgets.unescape(song['album']),
                    int(song['musicrid']),
                    int(song['artistid']), 
                    int(song['albumid']),
                    ]) 
            # automatically load more songs
            self.artist_songs_page += 1
            if self.artist_songs_page < self.artist_songs_total - 1:
                self.append_artist_songs()

        if init:
            self.artist_songs_liststore.clear()
            self.artist_songs_page = 0
        Net.async_call(
                Net.get_artist_songs_by_id, _append_artist_songs, 
                self.curr_artist_id, self.artist_songs_page)

    def show_artist_albums(self):
        self.artist_control_box.hide()
        self.album_control_box.hide()
        self.artist_mv_control_box.hide()
        if self.artist_albums_inited:
            return
        self.artist_albums_inited = True
        self.append_artist_albums(init=True)

    def append_artist_albums(self, init=False):
        def _append_artist_albums(albums_args, error=None):
            albums, self.artist_albums_total = albums_args
            if error or self.artist_albums_total == 0:
                return
            urls = []
            tree_iters = []
            for album in albums:
                tree_iter = self.artist_albums_liststore.append([
                    self.app.theme['anonymous'],
                    Widgets.unescape(album['name']),
                    int(album['albumid']),
                    Widgets.unescape(album['artist']),
                    int(album['artistid']),
                    Widgets.set_tooltip(album['name'], album['info']),
                    ])
                urls.append(album['pic'])
                tree_iters.append(tree_iter)
            Net.update_album_covers(
                    self.artist_albums_liststore, 0, tree_iters, urls)
            self.artist_albums_page += 1
            if self.artist_albums_page < self.artist_albums_total - 1:
                self.append_artist_albums()

        if init:
            self.artist_albums_liststore.clear()
            self.artist_albums_page = 0
        if init or not hasattr(self.artist_albums, 'timestamp'):
            self.artist_albums_liststore.timestamp = time.time()
        Net.async_call(
                Net.get_artist_albums, _append_artist_albums,
                self.curr_artist_id, self.artist_albums_page)

    def show_artist_mv(self):
        self.artist_control_box.hide()
        self.album_control_box.hide()
        self.artist_mv_control_box.show_all()
        if self.artist_mv_inited:
            return
        self.artist_mv_inited = True
        self.append_artist_mv(init=True)

    def append_artist_mv(self, init=False):
        def _append_artist_mv(mv_args, error=None):
            mvs, self.artist_mv_total = mv_args
            if error or self.artist_mv_total == 0:
                return
            urls = []
            tree_iters = []
            for mv in mvs:
                tree_iter = self.artist_mv_liststore.append([
                    self.app.theme['anonymous'],
                    Widgets.unescape(mv['name']),
                    Widgets.unescape(mv['artist']),
                    '',
                    int(mv['musicid']),
                    int(mv['artistid']),
                    0,
                    Widgets.set_tooltip(mv['name'], mv['artist']),
                    ])
                tree_iters.append(tree_iter)
                urls.append(mv['pic'])
            Net.update_mv_images(
                    self.artist_mv_liststore, 0, tree_iters, urls)
            self.artist_mv_page += 1
            if self.artist_mv_page < self.artist_mv_total - 1:
                self.append_artist_mv()

        if init:
            self.artist_mv_liststore.clear()
            self.artist_mv_page = 0
        if init or not hasattr(self.artist_mv_liststore, 'timestamp'):
            self.artist_mv_liststore.timestamp = time.time()
        Net.async_call(
                Net.get_artist_mv, _append_artist_mv,
                self.curr_artist_id, self.artist_mv_page)

    def show_artist_similar(self):
        self.artist_control_box.hide()
        self.artist_mv_control_box.hide()
        self.album_control_box.hide()
        if self.artist_similar_inited:
            return
        self.artist_similar_inited = True
        self.append_artist_similar(init=True)

    def append_artist_similar(self, init=False):
        self.first()
        def _append_artist_similar(similar_args, error=None):
            artists, self.artist_similar_total = similar_args
            if error or not self.artist_similar_total:
                return
            urls = []
            tree_iters = []
            for artist in artists:
                _info = ''.join([artist['songnum'], _(' songs'), ])
                tree_iter = self.artist_similar_liststore.append([
                    self.app.theme['anonymous'],
                    Widgets.unescape(artist['name']),
                    int(artist['id']),
                    _info,
                    Widgets.set_tooltip(artist['name'], _info),
                    ])
                urls.append(artist['pic'])
                tree_iters.append(tree_iter)
            Net.update_artist_logos(
                    self.artist_similar_liststore, 0, tree_iters, urls)
            self.artist_similar_page += 1
            if self.artist_similar_page < self.artist_similar_total - 1:
                self.append_artist_similar()

        if init:
            self.artist_similar_liststore.clear()
            self.artist_similar_page = 0
        if init or not hasattr(self.artist_similar_liststore, 'timestamp'):
            self.artist_similar_liststore.timestamp = time.time()
        Net.async_call(
                Net.get_artist_similar, _append_artist_similar,
                self.curr_artist_id, self.artist_similar_page)

    def show_artist_info(self):
        self.artist_control_box.hide()
        self.artist_mv_control_box.hide()
        self.album_control_box.hide()
        if self.artist_info_inited:
            return
        self.artist_info_inited = True
        self.append_artist_info()

    def append_artist_info(self):
        def _append_artist_info(info, error=None):
            if error or not info:
                return
            if info.get('pic', None):
                self.artist_info_pic.set_from_file(info['pic'])
            self.artist_info_name.set(info, 'name')
            self.artist_info_birthday.set(info, 'birthday')
            self.artist_info_birthplace.set(info, 'birthplace')
            self.artist_info_height.set(info, 'tall')
            self.artist_info_weight.set(info, 'weight',)
            self.artist_info_country.set(info, 'country')
            self.artist_info_language.set(info, 'language')
            self.artist_info_gender.set(info, 'gender',)
            self.artist_info_constellation.set(info, 'constellation')
            if info and 'info' in info:
                self.artist_info_textbuffer.set_text(
                        Widgets.escape(info['info']))
            else:
                self.artist_info_textbuffer.set_text('')

        Net.async_call(
                Net.get_artist_info, _append_artist_info,
                self.curr_artist_id)


    def on_artist_albums_iconview_item_activated(self, iconview, path):
        model = iconview.get_model()
        album = model[path][1]
        albumid = model[path][2]
        artist = model[path][3]
        artistid = model[path][4]
        self.show_album(album, albumid, artist, artistid)

    def on_artist_mv_iconview_item_activated(self, iconview, path):
        model = iconview.get_model()
        song = Widgets.song_row_to_dict(model[path])
        self.app.popup_page(self.app.lrc.app_page)
        self.app.playlist.play_song(song, use_mv=True)

    def on_artist_similar_iconview_item_activated(self, iconview, path):
        model = iconview.get_model()
        artist = model[path][1]
        artistid = model[path][2]
        self.show_artist(artist, artistid)

    # open API
    def show_album(self, album, albumid, artist, artistid):
        '''Show album information, including songs'''
        self.first()
        self.curr_album_name = album
        self.curr_album_id = albumid
        self.curr_artist_name = artist
        self.curr_artist_id = artistid
        self.artist_button.set_label(artist)
        self.label.set_label(album)
        self.app.playlist.advise_new_playlist_name(album)
        self.buttonbox.show_all()
        self.artist_control_box.hide()
        self.artist_mv_control_box.hide()
        self.notebook.set_current_page(2)
        self.append_album_songs()
    
    def append_album_songs(self):
        def _append_album_songs(songs, error=None):
            if error or not songs:
                return
            for song in songs:
                self.album_songs_liststore.append([
                    True,
                    Widgets.unescape(song['name']),
                    Widgets.unescape(song['artist']),
                    Widgets.unescape(self.curr_album_name),
                    int(song['id']),
                    int(song['artistid']),
                    int(self.curr_album_id), ])
        self.album_songs_liststore.clear()
        Net.async_call(
                Net.get_album, _append_album_songs,
                self.curr_album_id)

    def on_artist_button_clicked(self, button):
        self.show_artist(self.curr_artist_name, self.curr_artist_id)

    # Signal handlers for favorite artists tab
    def add_to_fav_artists(self, artist_id, init=False):
        def _append_fav_artist(info, error=None):
            if error or not info:
                return
            if info.get('pic', None):
                pix = GdkPixbuf.Pixbuf.new_from_file_at_size(
                        info['pic'], 100, 100)
            else:
                pix = self.app.theme['anonymous']
            tip = Widgets.escape(info.get('info', ''))
            self.fav_artists_liststore.append(
                    [pix, info['name'], artist_id, tip])

        if init is False and self.check_artist_favorited(artist_id):
            return
        Net.async_call(Net.get_artist_info, _append_fav_artist, artist_id)

    def remove_from_fav_artists(self, artist_id):
        '''Remove an artist from fav_artists_liststore.'''
        for row in self.fav_artists_liststore:
            if artist_id == row[2]:
                self.fav_artists_liststore.remove(row.iter)
                return

    def check_artist_favorited(self, artist_id):
        '''Check whether this artist is in favorite list.'''
        for row in self.fav_artists_liststore:
            if artist_id == row[2]:
                return True
        return False

    def load_fav_artists(self):
        '''Load fav_artists from json.'''
        if not os.path.exists(Config.FAV_ARTISTS_JSON):
            return
        with open(Config.FAV_ARTISTS_JSON) as fh:
            fav_artists = json.loads(fh.read())
        for artist_id in fav_artists:
            self.add_to_fav_artists(artist_id)

    def dump_fav_artists(self):
        '''Dump fav_artists to a json file'''
        fav_artists = [row[2] for row in self.fav_artists_liststore]
        if not fav_artists:
            return
        with open(Config.FAV_ARTISTS_JSON, 'w') as fh:
            fh.write(json.dumps(fav_artists))

    def on_fav_artists_btn_clicked(self, btn):
        self.notebook.set_current_page(3)

    def on_fav_main_btn_clicked(self, btn):
        self.notebook.set_current_page(0)

    def on_fav_artists_iconview_item_activated(self, iconview, path):
        model = iconview.get_model()
        artist_name = model[path][1]
        artist_id = model[path][2]
        self.show_artist(artist_name, artist_id)

    def on_fav_curr_artist_btn_clicked(self, btn):
        if btn.props.image == self.fav_yes_img:
            btn.props.image = self.fav_no_img
            self.remove_from_fav_artists(self.curr_artist_id)
        else:
            btn.props.image = self.fav_yes_img
            self.add_to_fav_artists(self.curr_artist_id)

########NEW FILE########
__FILENAME__ = Config

# Copyright (C) 2013-2014 LiuLang <gsushzhsosgsu@gmail.com>

# Use of this source code is governed by GPLv3 license that can be found
# in the LICENSE file.

import gettext
import json
import os
import shutil
import sys
from gi.repository import GdkPixbuf
from gi.repository import GLib
from gi.repository import Gtk


if __file__.startswith('/usr/local/'):
    PREF = '/usr/local/share'
elif __file__.startswith('/usr/'):
    PREF = '/usr/share'
else:
    PREF = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'share')

LOCALEDIR = os.path.join(PREF, 'locale')
gettext.bindtextdomain('kwplayer', LOCALEDIR)
gettext.textdomain('kwplayer')
_ = gettext.gettext

APPNAME = _('KW Player')
VERSION = '3.3.4'
HOMEPAGE = 'https://github.com/LiuLang/kwplayer'
AUTHORS = ['LiuLang <gsushzhsosgsu@gmail.com>', ]
COPYRIGHT = 'Copyright (c) 2013-2014 LiuLang'
DESCRIPTION = _('A simple music player on Linux desktop.')

ICON_PATH = os.path.join(PREF, 'kuwo', 'themes', 'default')
HOME_DIR = os.path.expanduser('~')
CACHE_DIR = os.path.join(HOME_DIR, '.cache', 'kuwo')
# used for small logos(100x100)
IMG_DIR = os.path.join(CACHE_DIR, 'images')
# used by today_recommand images
IMG_LARGE_DIR = os.path.join(CACHE_DIR, 'images_large')
# lyrics are putted here
LRC_DIR = os.path.join(CACHE_DIR, 'lrc')
# url requests are stored here.
CACHE_DB = os.path.join(CACHE_DIR, 'cache.db')
# store playlists, `cached` not included.
PLS_JSON = os.path.join(CACHE_DIR, 'pls.json')
# store radio playlist.
RADIO_JSON = os.path.join(CACHE_DIR, 'radio.json')
# favorite artists list.
FAV_ARTISTS_JSON = os.path.join(CACHE_DIR, 'fav_artists.json')

THEME_DIR = os.path.join(PREF, 'kuwo', 'themes', 'default')

class ShortcutMode:
    NONE = 0
    DEFAULT = 1
    CUSTOM = 2

# Check Gtk version <= 3.6
GTK_LE_36 = (Gtk.MAJOR_VERSION == 3) and (Gtk.MINOR_VERSION <= 6)

CONF_DIR = os.path.join(HOME_DIR, '.config', 'kuwo')
_conf_file = os.path.join(CONF_DIR, 'conf.json')
SHORT_CUT_I18N = {
        'VolumeUp': _('VolumeUp'),
        'VolumeDown': _('VolumeDown'),
        'Mute': _('Mute'),
        'Previous': _('Previous'),
        'Next': _('Next'),
        'Pause': _('Pause'),
        'Play': _('Play'),
        'Stop': _('Stop'),
        'Launch': _('Launch'),
        }
_default_conf = {
        'version': VERSION,
        'window-size': (960, 680),
        'song-dir': os.path.join(CACHE_DIR, 'song'),
        'mv-dir': os.path.join(CACHE_DIR, 'mv'),
        'volume': 0.08,
        'use-ape': False,
        'use-mkv': True,
        'use-status-icon': True,
        'use-notify': False,
        'use-dark-theme': True,
        'show-pls': False,
        'lrc-text-color': 'rgba(46, 52, 54, 0.999)',
        'lrc-back-color': 'rgba(237, 221, 221, 0.28)',
        'lrc-text-size': 22,
        'lrc-highlighted-text-color': 'rgba(0, 0, 0, 0.999)',
        'lrc-highlighted-text-size': 26,
        'shortcut-mode': ShortcutMode.DEFAULT,
        'custom-shortcut': {
            'VolumeUp': '<Ctrl><Shift>U',
            'VolumeDown': '<Ctrl><Shift>D',
            'Mute': '<Ctrl><Shift>M',
            'Previous': '<Ctrl><Shift>Left',
            'Next': '<Ctrl><Shift>Right',
            'Pause': '<Ctrl><Shift>Down',
            'Play': '<Ctrl><Shift>Down',
            'Stop': '<Ctrl><Shift>Up',
            'Launch': '<Ctrl><Shift>L',
            },
        'default-shortcut': {
            'VolumeUp': 'XF86AudioRaiseVolume',
            'VolumeDown': 'XF86AudioLowerVolume',
            'Mute': 'XF86AudioMute',
            'Previous': 'XF86AudioPrev',
            'Next': 'XF86AudioNext',
            'Pause': 'XF86AudioPause',
            'Play': 'XF86AudioPlay',
            'Stop': 'XF86AudioStop',
            'Launch': 'XF86AudioMedia',
            },
        }

def check_first():
    if not os.path.exists(CONF_DIR):
        os.makedirs(CONF_DIR)
    if not os.path.exists(CACHE_DIR):
        os.makedirs(CACHE_DIR)
        os.mkdir(IMG_DIR)
        os.mkdir(IMG_LARGE_DIR)
        os.mkdir(_default_conf['song-dir'])
        os.mkdir(_default_conf['mv-dir'])
        os.mkdir(LRC_DIR)

def load_conf():
    if os.path.exists(_conf_file):
        with open(_conf_file) as fh:
            conf = json.loads(fh.read())
        for key in _default_conf:
            if key not in conf:
                conf[key] = _default_conf[key]
        return conf
    dump_conf(_default_conf)
    return _default_conf

def dump_conf(conf):
    with open(_conf_file, 'w') as fh:
        fh.write(json.dumps(conf, indent=2))

def load_theme():
    theme_file = os.path.join(THEME_DIR, 'images.json')
    try:
        with open(theme_file) as fh:
            theme = json.loads(fh.read())
    except ValueError as e:
        print(e)
        sys.exit(1)

    theme_pix = {}
    theme_path = {}
    for img_name in theme:
        filepath = os.path.join(THEME_DIR, theme[img_name])
        try:
            theme_pix[img_name] = GdkPixbuf.Pixbuf.new_from_file(filepath)
            theme_path[img_name] = filepath
        except GLib.GError as e:
            print(e)
            sys.exit(1)
    return (theme_pix, theme_path)

########NEW FILE########
__FILENAME__ = Lrc

# Copyright (C) 2013-2014 LiuLang <gsushzhsosgsu@gmail.com>

# Use of this source code is governed by GPLv3 license that can be found
# in the LICENSE file.

import os
import re
import time
from gi.repository import Gdk
from gi.repository import GdkPixbuf
from gi.repository import GdkX11
from gi.repository import Gtk

from kuwo import Config
_ = Config._

LRC_WINDOW, MV_WINDOW = 0, 1

def list_to_time(time_tags):
    mm, ss, ml = time_tags
    if ml is None:
        curr_time = int(mm) * 60 + int(ss)
    else:
        curr_time = int(mm) * 60 + int(ss) + float(ml)
    return int(curr_time * 10 ** 9)

def lrc_parser(lrc_txt):
    lines = lrc_txt.split('\n')
    lrc_obj = [(-4, ''), (-3, ''), (-2, ''), ]

    reg_time = re.compile('\[([0-9]{2}):([0-9]{2})(\.[0-9]{1,3})?\]')
    for line in lines:
        offset = 0
        match = reg_time.match(line)
        tags = []
        while match:
            time = list_to_time(match.groups())
            tags.append(time)
            offset = match.end()
            match = reg_time.match(line, offset)
        content = line[offset:]
        for tag in tags:
            lrc_obj.append((tag, content))
    last_time = lrc_obj[-1][0]
    for i in range(last_time, last_time * 2 + 5, last_time // 4 + 1):
        lrc_obj.append((i, '', ))
    return sorted(lrc_obj)

class Lrc(Gtk.Notebook):
    '''Lyrics tab in notebook.'''

    title = _('Lyrics')

    def __init__(self, app):
        super().__init__()
        self.set_show_tabs(False)
        self.app = app
        self.lrc_obj = None
        self.lrc_default_background = os.path.join(
                Config.THEME_DIR, 'lrc-background.jpg')
        self.lrc_background = None
        self.old_provider = None

        # lyrics window
        self.lrc_window = Gtk.ScrolledWindow()
        self.lrc_window.get_style_context().add_class('lrc_window')
        self.append_page(self.lrc_window, Gtk.Label.new('Lrc'))

        self.lrc_buf = Gtk.TextBuffer()
        self.lrc_buf.set_text('')
        fore_rgba = Gdk.RGBA()
        fore_rgba.parse(app.conf['lrc-highlighted-text-color'])
        font_size = app.conf['lrc-highlighted-text-size']
        # Need to use size_points, not size property
        self.highlighted_tag = self.lrc_buf.create_tag(
                size_points=font_size, foreground_rgba=fore_rgba)

        self.lrc_tv = Gtk.TextView(buffer=self.lrc_buf)
        self.lrc_tv.get_style_context().add_class('lrc_tv')
        self.lrc_tv.props.editable = False
        self.lrc_tv.props.margin_top = 15
        self.lrc_tv.props.margin_right = 35
        self.lrc_tv.props.margin_bottom = 15
        self.lrc_tv.props.margin_left = 35
        self.lrc_tv.props.cursor_visible = False
        self.lrc_tv.props.justification = Gtk.Justification.CENTER
        self.lrc_tv.props.pixels_above_lines = 10
        self.lrc_tv.connect(
                'button-press-event', self.on_lrc_tv_button_pressed)
        self.lrc_window.add(self.lrc_tv)

        # mv window
        mv_win_wrap = Gtk.ScrolledWindow()
        self.append_page(mv_win_wrap, Gtk.Label.new('MV'))
        self.mv_window = Gtk.DrawingArea()
        self.mv_window.connect('draw', self.on_mv_window_redraw)
        mv_win_wrap.add(self.mv_window)

        self.update_background(self.lrc_default_background)

    def after_init(self):
        pass

    def first(self):
        pass

    def on_lrc_tv_button_pressed(self, widget, event):
        if event.button == 3:
            return True

    def set_lrc(self, lrc_txt):
        self.update_background(self.lrc_default_background)
        self.old_line_num = 1
        self.old_line_iter = None
        self.old_timestamp = -5
        if not lrc_txt:
            print('Failed to get lrc')
            self.lrc_buf.set_text(_('No lrc available'))
            self.lrc_obj = None
            return
        self.lrc_obj = lrc_parser(lrc_txt)
        self.lrc_content = [l[1] for l in self.lrc_obj]

        self.lrc_buf.remove_all_tags(
                self.lrc_buf.get_start_iter(),
                self.lrc_buf.get_end_iter())
        self.lrc_buf.set_text('\n'.join(self.lrc_content))
        #self.sync_lrc(0)
        self.lrc_window.get_vadjustment().set_value(0)

    def sync_lrc(self, timestamp):
        if not self.lrc_obj or len(self.lrc_obj) <= self.old_line_num + 1:
            return
        # current line, do nothing
        if (self.lrc_obj[self.old_line_num][0] < timestamp and
            timestamp < self.lrc_obj[self.old_line_num + 1][0]):
            return

        line_num = self.old_line_num + 1
        # remove old highlighted tags
        if self.old_line_num >= 0 and self.old_line_iter:
            self.lrc_buf.remove_tag(
                    self.highlighted_tag, *self.old_line_iter)

        # backward seeking
        if timestamp < self.old_timestamp:
            while timestamp < self.lrc_obj[line_num][0]:
                line_num -= 1
        else:
        # forward seeking
            while (len(self.lrc_obj) > line_num and
                   timestamp > self.lrc_obj[line_num][0]):
                line_num += 1
        line_num -= 1

        iter_start = self.lrc_buf.get_iter_at_line(line_num)
        iter_end = self.lrc_buf.get_iter_at_line(line_num+1)
        self.lrc_buf.apply_tag(self.highlighted_tag, iter_start, iter_end)
        self.lrc_tv.scroll_to_iter(iter_start, 0, True, 0, 0.5)
        self.old_line_iter = (iter_start, iter_end)
        self.old_line_num = line_num
        self.old_timestamp = timestamp

    def show_mv(self):
        self.set_current_page(MV_WINDOW)
        Gdk.Window.process_all_updates()
        self.mv_window.realize()
        self.xid = self.mv_window.get_property('window').get_xid()

    def show_music(self):
        self.set_current_page(LRC_WINDOW)

    # styles
    def update_background(self, filepath):
        if filepath is None or filepath == self.lrc_background:
            return
        if os.path.exists(filepath):
            self.lrc_background = filepath
        else:
            self.lrc_background = self.lrc_default_background
        css = '\n'.join([
            'GtkScrolledWindow.lrc_window {',
                "background-image: url('{0}');".format(self.lrc_background),
            '}',
            ])
        new_provider = self.app.apply_css(
                self.lrc_window, css, old_provider=self.old_provider)
        self.old_provider = new_provider

    def update_highlighted_tag(self):
        fore_rgba = Gdk.RGBA()
        fore_rgba.parse(self.app.conf['lrc-highlighted-text-color'])
        self.highlighted_tag.props.size_points = \
                self.app.conf['lrc-highlighted-text-size']
        self.highlighted_tag.props.foreground_rgba = fore_rgba

    def on_mv_window_redraw(self, *args):
        if self.app.player.get_fullscreen():
            self.app.player.playbin.expose_fullscreen()
        else:
            self.app.player.playbin.expose()

########NEW FILE########
__FILENAME__ = MV

# Copyright (C) 2013-2014 LiuLang <gsushzhsosgsu@gmail.com>

# Use of this source code is governed by GPLv3 license that can be found
# in the LICENSE file.

import time

from gi.repository import GdkPixbuf
from gi.repository import Gtk

from kuwo import Config
from kuwo import Net
from kuwo import Widgets

_ = Config._

class MV(Gtk.Box):
    '''MV tab in notebook.'''

    title = _('MV')

    def __init__(self, app):
        super().__init__(orientation=Gtk.Orientation.VERTICAL)
        self.app = app

    def first(self):
        app = self.app
        self.buttonbox = Gtk.Box(spacing=5)
        self.pack_start(self.buttonbox, False, False, 0)
        button_home = Gtk.Button(_('MV'))
        button_home.connect('clicked', self.on_button_home_clicked)
        self.buttonbox.pack_start(button_home, False, False, 0)
        self.label = Gtk.Label('')
        self.buttonbox.pack_start(self.label, False, False, 0)

        # pic, name, artist, album, rid, artistid, albumid, tooltip
        self.liststore_songs = Gtk.ListStore(
                GdkPixbuf.Pixbuf, str, str, str, int, int, int, str)
        self.mv_control_box = Widgets.MVControlBox(
                self.liststore_songs, self.app)
        self.buttonbox.pack_end(self.mv_control_box, False, False, 0)

        self.scrolled_nodes = Gtk.ScrolledWindow()
        self.pack_start(self.scrolled_nodes, True, True, 0)
        # logo, name, nid, info, tooltip
        self.liststore_nodes = Gtk.ListStore(
                GdkPixbuf.Pixbuf, str, int, str, str)
        iconview_nodes = Widgets.IconView(self.liststore_nodes, tooltip=4)
        iconview_nodes.connect(
                'item_activated', self.on_iconview_nodes_item_activated)
        self.scrolled_nodes.add(iconview_nodes)

        self.scrolled_songs = Gtk.ScrolledWindow()
        self.pack_start(self.scrolled_songs, True, True, 0)
        iconview_songs = Widgets.IconView(
                self.liststore_songs, info_pos=2, tooltip=7)
        iconview_songs.connect(
                'item_activated', self.on_iconview_songs_item_activated)
        self.scrolled_songs.add(iconview_songs)

        self.show_all()
        self.buttonbox.hide()
        self.scrolled_songs.hide()

        nid = 3
        nodes_wrap = Net.get_index_nodes(nid)
        if not nodes_wrap:
            return
        nodes = nodes_wrap['child']
        self.liststore_nodes.clear()
        urls = []
        tree_iters = []
        for node in nodes:
            tree_iter = self.liststore_nodes.append([
                self.app.theme['anonymous'],
                Widgets.unescape(node['disname']),
                int(node['sourceid']),
                Widgets.unescape(node['info']),
                Widgets.set_tooltip(node['disname'], node['info']),
                ])
            tree_iters.append(tree_iter)
            urls.append(node['pic'])
        self.liststore_nodes.timestamp = time.time()
        Net.update_liststore_images(
                self.liststore_nodes, 0, tree_iters, urls)

    def on_iconview_nodes_item_activated(self, iconview, path):
        model = iconview.get_model()
        self.buttonbox.show_all()
        self.label.set_label(model[path][1])
        self.scrolled_nodes.hide()
        self.scrolled_songs.show_all()
        self.curr_node_id = model[path][2]
        self.append_songs(init=True)

    def append_songs(self, init=False):
        def _append_songs(songs_args, error=None):
            songs, self.songs_total = songs_args
            if error or not self.songs_total:
                return
            urls = []
            tree_iters = []
            for song in songs:
                tree_iter = self.liststore_songs.append([
                    self.app.theme['anonymous'],
                    Widgets.unescape(song['name']),
                    Widgets.unescape(song['artist']),
                    Widgets.unescape(song['album']),
                    int(song['id']),
                    int(song['artistid']), 
                    int(song['albumid']),
                    Widgets.set_tooltip(song['name'], song['artist']),
                    ])
                tree_iters.append(tree_iter)
                urls.append(song['mvpic'])
            Net.update_mv_images(
                    self.liststore_songs, 0, tree_iters, urls)
            self.songs_page += 1
            if self.songs_page < self.songs_total - 1:
                self.append_songs()

        if init:
            self.app.playlist.advise_new_playlist_name(self.label.get_text())
            self.songs_page = 0
            self.liststore_songs.clear()
        if init or not hasattr(self.liststore_songs, 'timestamp'):
            self.liststore_songs.timestamp = time.time()
        Net.async_call(
                Net.get_mv_songs, _append_songs, 
                self.curr_node_id, self.songs_page)

    def on_iconview_songs_item_activated(self, iconview, path):
        model = iconview.get_model()
        song = Widgets.song_row_to_dict(model[path])
        self.app.popup_page(self.app.lrc.app_page)
        self.app.playlist.play_song(song, use_mv=True)

    def on_button_home_clicked(self, btn):
        self.scrolled_nodes.show_all()
        self.scrolled_songs.hide()
        self.buttonbox.hide()

########NEW FILE########
__FILENAME__ = Net

# Copyright (C) 2013-2014 LiuLang <gsushzhsosgsu@gmail.com>

# Use of this source code is governed by GPLv3 license that can be found
# in the LICENSE file.

import hashlib
import json
import math
import os
import sys
import threading
import time
from urllib.error import URLError
from urllib import parse
from urllib import request

from gi.repository import GdkPixbuf
from gi.repository import Gio
from gi.repository import GLib
from gi.repository import GObject
from gi.repository import Gtk

from kuwo import Config
from kuwo import Utils

IMG_CDN = 'http://img4.kwcdn.kuwo.cn/'
ARTIST = 'http://artistlistinfo.kuwo.cn/mb.slist?'
QUKU = 'http://qukudata.kuwo.cn/q.k?'
QUKU_SONG = 'http://nplserver.kuwo.cn/pl.svc?'
SEARCH = 'http://search.kuwo.cn/r.s?'
SONG = 'http://antiserver.kuwo.cn/anti.s?'

CHUNK = 16384                # 2**14, 16k, chunk size for file downloading 
CHUNK_TO_PLAY = 2097152      # 2**21, 2M, min size to emit can-play signal
CHUNK_APE_TO_PLAY = 8388608  # 2**23, 8M
CHUNK_MV_TO_PLAY = 8388608   # 2**23, 8M
MAXTIMES = 3                 # time to retry http connections
TIMEOUT = 30                 # HTTP connection timeout
SONG_NUM = 100               # num of songs in each request
ICON_NUM = 50                # num of icons in each request
CACHE_TIMEOUT = 1209600      # 14 days in seconds

IMG_SIZE = 100               # image size, 100px

# Using weak reference to cache song list in TopList and Radio.
class Dict(dict):
    pass
req_cache = Dict()

try:
    # Debian: http://code.google.com/p/py-leveldb/
    from leveldb import LevelDB
    ldb_imported = True
except ImportError as e:
    try:
        # Fedora: https://github.com/wbolster/plyvel
        from plyvel import DB as LevelDB
        ldb_imported = True
    except ImportError as e:
        ldb_imported = False

ldb = None
if ldb_imported:
    try:
        ldb = LevelDB(Config.CACHE_DB, create_if_missing=True)
        # support plyvel 0.6
        if hasattr(ldb, 'put'):
            ldb_get = ldb.get
            ldb_put = ldb.put
        else:
            ldb_get = ldb.Get
            ldb_put = ldb.Put
    except Exception as e:
        ldb_imported = False

def empty_func(*args, **kwds):
    pass

# calls f on another thread
def async_call(func, func_done, *args):
    def do_call(*args):
        result = None
        error = None

        try:
            result = func(*args)
        except Exception as e:
            error = e
        GLib.idle_add(lambda: func_done(result, error))

    thread = threading.Thread(target=do_call, args=args)
    thread.daemon = True
    thread.start()

def hash_byte(_str):
    return hashlib.sha512(_str.encode()).digest()

def hash_str(_str):
    return hashlib.sha1(_str.encode()).hexdigest()

def urlopen(_url, use_cache=True, retries=MAXTIMES):
    # set host port from 81 to 80, to fix image problem
    url = _url.replace(':81', '')
    if use_cache and ldb_imported:
        key = hash_byte(url)
        try:
            content = ldb_get(key)
            if content and len(content) > 10:
                try:
                    timestamp = int(content[:10].decode())
                    if (time.time() - timestamp) < CACHE_TIMEOUT:
                        return content[10:]
                except (ValueError, UnicodeDecodeError):
                    pass
        except KeyError:
            pass
    for i in range(retries):
        try:
            req = request.urlopen(url, timeout=TIMEOUT)
            req_content = req.read()
            if use_cache and ldb_imported:
                ldb_put(key, str(int(time.time())).encode() + req_content)
            return req_content
        except URLError as e:
            pass
    return None

def get_nodes(nid, page):
    # node list contains very few items
    url = ''.join([
        QUKU,
        'op=query&fmt=json&src=mbox&cont=ninfo&rn=',
        str(ICON_NUM),
        '&pn=',
        str(page),
        '&node=',
        str(nid),
        ])
    req_content = urlopen(url)
    if not req_content:
        return (None, 0)
    try:
        nodes_wrap = json.loads(req_content.decode())
    except ValueError as e:
        return (None, 0)
    nodes = nodes_wrap['child']
    pages = math.ceil(int(nodes_wrap['total']) / ICON_NUM)
    return (nodes, pages)

def get_image(url, filepath=None):
    if not url or len(url) < 10:
        return None
    if not filepath:
        filename = os.path.split(url)[1]
        filepath = os.path.join(Config.IMG_DIR, filename)
    if os.path.exists(filepath):
        return filepath

    image = urlopen(url, use_cache=False)
    if not image:
        return None

    with open(filepath, 'wb') as fh:
        fh.write(image)
    # Now, check its mime type
    file_ = Gio.File.new_for_path(filepath)
    file_info = file_.query_info(Gio.FILE_ATTRIBUTE_STANDARD_CONTENT_TYPE,
            Gio.FileQueryInfoFlags.NONE)
    content_type = file_info.get_content_type()
    if 'image' in content_type:
        return filepath
    else:
        os.remove(filepath)
        return None

def get_album(albumid):
    url = ''.join([
        SEARCH,
        'stype=albuminfo&albumid=',
        str(albumid),
        ])
    req_content = urlopen(url)
    if not req_content:
        return None
    try:
        songs_wrap = Utils.json_loads_single(req_content.decode())
    except ValueError as e:
        return None
    songs = songs_wrap['musiclist']
    return songs

def update_liststore_images(liststore,  col, tree_iters, urls,
                            url_proxy=None, resize=IMG_SIZE):
    '''Update a banch of thumbnails consequently.

    liststore - the tree model, which has timestmap property
    col       - column index
    tree_iters - a list of tree_iters
    urls      - a list of image urls
    url_proxy - a function to reconstruct image url, this function run in 
                background thread. default is None, do nothing.
    resize    - will resize pixbuf to specific size, default is 100x100
    '''
    def update_image(filepath, tree_iter):
        try:
            pix = GdkPixbuf.Pixbuf.new_from_file_at_size(
                    filepath, resize, resize)
            tree_path = liststore.get_path(tree_iter)
            if tree_path is not None:
                liststore[tree_path][col] = pix
        except GLib.GError:
            pass

    def get_images():
        for tree_iter, url in zip(tree_iters, urls):
            # First, check timestamp matches
            if liststore.timestamp != timestamp:
                break
            if url_proxy:
                url = url_proxy(url)
            filepath = get_image(url)
            if filepath:
                GLib.idle_add(update_image, filepath, tree_iter)

    timestamp = liststore.timestamp
    thread = threading.Thread(target=get_images, args=[])
    thread.daemon = True
    thread.start()

def update_album_covers(liststore, col, tree_iters, urls):
    def url_proxy(url):
        url = url.strip()
        if not url:
            return ''
        return ''.join([
            IMG_CDN,
            'star/albumcover/',
            url,
            ])
    update_liststore_images(liststore, col, tree_iters, urls, url_proxy)

def update_mv_images(liststore, col, tree_iters, urls):
    def url_proxy(url):
        url = url.strip()
        if not url:
            return ''
        return ''.join([
            IMG_CDN,
            'wmvpic/',
            url,
            ])
    update_liststore_images(liststore, col, tree_iters, urls,
            url_proxy=url_proxy, resize=120)

def get_toplist_songs(nid):
    # no need to use pn, because toplist contains very few songs
    url = ''.join([
        'http://kbangserver.kuwo.cn/ksong.s?',
        'from=pc&fmt=json&type=bang&data=content&rn=',
        str(SONG_NUM),
        '&id=',
        str(nid),
        ])
    if url not in req_cache:
        req_content = urlopen(url, use_cache=False)
        if not req_content:
            return None
        req_cache[url] = req_content
    try:
        songs_wrap = json.loads(req_cache[url].decode())
    except ValueError as e:
        return None
    return songs_wrap['musiclist']

def get_artists(catid, page, prefix):
    url = ''.join([
        ARTIST,
        'stype=artistlist&order=hot&rn=',
        str(ICON_NUM),
        '&category=',
        str(catid),
        '&pn=',
        str(page),
        ])
    if len(prefix) > 0:
        url = url + '&prefix=' + prefix
    req_content = urlopen(url)
    if not req_content:
        return (None, 0)
    try:
        artists_wrap = Utils.json_loads_single(req_content.decode())
    except ValueError as e:
        return (None, 0)
    pages = int(artists_wrap['total'])
    artists = artists_wrap['artistlist']
    return (artists, pages)

def get_artist_pic_url(pic_path):
    if len(pic_path) < 5:
        return None
    if pic_path[:2] in ('55', '90',):
        pic_path = '100/' + pic_path[2:]
    url = ''.join([IMG_CDN, 'star/starheads/', pic_path, ])
    return url

def update_artist_logos(liststore, col, tree_iters, urls):
    update_liststore_images(
            liststore, col, tree_iters, urls,
            url_proxy=get_artist_pic_url)

def get_artist_info(artistid, artist=None):
    '''Get artist info, if cached, just return it.

    Artist pic is also retrieved and saved to info['pic']
    '''
    if artistid == 0:
        url = ''.join([
            SEARCH,
            'stype=artistinfo&artist=', 
            Utils.encode_uri(artist),
            ])
    else:
        url = ''.join([
            SEARCH,
            'stype=artistinfo&artistid=', 
            str(artistid),
            ])
    req_content = urlopen(url)
    if not req_content:
        return None
    try:
        info = Utils.json_loads_single(req_content.decode())
    except ValueError as e:
        return None
    # set logo size to 100x100
    pic_path = info['pic']
    url = get_artist_pic_url(pic_path)
    if url:
        info['pic'] = get_image(url)
    else:
        info['pic'] = None
    return info

def get_artist_songs(artist, page):
    url = ''.join([
        SEARCH,
        'ft=music&itemset=newkw&newsearch=1&cluster=0&rn=',
        str(SONG_NUM),
        '&pn=',
        str(page),
        '&primitive=0&rformat=json&encoding=UTF8&artist=',
        artist,
        ])
    req_content = urlopen(url)
    if not req_content:
        return (None, 0)
    try:
        songs_wrap = Utils.json_loads_single(req_content.decode())
    except ValueError as e:
        return (None, 0)
    songs = songs_wrap['abslist']
    pages = math.ceil(int(songs_wrap['TOTAL']) / SONG_NUM)
    return (songs, pages)

def get_artist_songs_by_id(artistid, page):
    url = ''.join([
        SEARCH,
        'stype=artist2music&artistid=',
        str(artistid),
        '&rn=',
        str(SONG_NUM),
        '&pn=',
        str(page),
        ])
    req_content = urlopen(url)
    if not req_content:
        return (None, 0)
    try:
        songs_wrap = Utils.json_loads_single(req_content.decode())
    except ValueError as e:
        return (None, 0)
    songs = songs_wrap['musiclist']
    pages = math.ceil(int(songs_wrap['total']) / SONG_NUM)
    return (songs, pages)

def get_artist_albums(artistid, page):
    url = ''.join([
        SEARCH,
        'stype=albumlist&sortby=1&rn=',
        str(ICON_NUM),
        '&artistid=',
        str(artistid),
        '&pn=',
        str(page),
        ])
    req_content = urlopen(url)
    if not req_content:
        return (None, 0)
    try:
        albums_wrap = Utils.json_loads_single(req_content.decode())
    except ValueError as e:
        return (None, 0)
    albums = albums_wrap['albumlist']
    pages = math.ceil(int(albums_wrap['total']) / ICON_NUM)
    return (albums, pages)

def get_artist_mv(artistid, page):
    url = ''.join([
        SEARCH,
        'stype=mvlist&sortby=0&rn=',
        str(ICON_NUM),
        '&artistid=',
        str(artistid),
        '&pn=',
        str(page),
        ])
    req_content = urlopen(url)
    if not req_content:
        return (None, 0)
    try:
        mvs_wrap = Utils.json_loads_single(req_content.decode())
    except ValueError as e:
        return (None, 0)
    mvs = mvs_wrap['mvlist']
    pages = math.ceil(int(mvs_wrap['total']) / ICON_NUM)
    return (mvs, pages)

def get_artist_similar(artistid, page):
    '''Only has 10 items'''
    url = ''.join([
        SEARCH,
        'stype=similarartist&sortby=0&rn=',
        str(ICON_NUM),
        '&pn=',
        str(page),
        '&artistid=',
        str(artistid),
        ])
    req_content = urlopen(url)
    if not req_content:
        return (None, 0)
    try:
       artists_wrap = Utils.json_loads_single(req_content.decode())
    except ValueError as e:
        return (None, 0)
    artists = artists_wrap['artistlist']
    pages = math.ceil(int(artists_wrap['total']) / ICON_NUM)
    return (artists, pages)

def get_lrc_path(song):
    rid = str(song['rid'])
    oldname = rid + '.lrc'
    oldpath = os.path.join(Config.LRC_DIR, oldname)
    newname = '{0}-{1}.lrc'.format(song['artist'], song['name'])
    newpath = os.path.join(Config.LRC_DIR, newname)
    if os.path.exists(oldpath):
        os.rename(oldpath, newpath)
    if os.path.exists(newpath):
        return (newpath, True)
    return (newpath, False)

def get_lrc(song):
    def _parse_lrc():
        url = ('http://newlyric.kuwo.cn/newlyric.lrc?' + 
                Utils.encode_lrc_url(rid))
        req_content = urlopen(url, use_cache=False, retries=8)
        if not req_content:
            return None
        try:
            lrc = Utils.decode_lrc_content(req_content)
            return lrc
        except Exception as e:
            return None

    rid = str(song['rid'])
    (lrc_path, lrc_cached) = get_lrc_path(song)
    if lrc_cached:
        with open(lrc_path) as fh:
            return fh.read()

    lrc = _parse_lrc()
    if lrc:
        try:
            with open(lrc_path, 'w') as fh:
                fh.write(lrc)
        except FileNotFoundError as e:
            pass
    return lrc

def get_recommend_lists(artist):
    url = ''.join([
        'http://artistpicserver.kuwo.cn/pic.web?',
        'type=big_artist_pic&pictype=url&content=list&&id=0&from=pc',
        '&name=',
        Utils.encode_uri(artist),
        ])
    req_content = urlopen(url)
    if not req_content:
        return None
    return req_content.decode()

def get_recommend_image(_url):
    '''Get big cover image about this artist, normally 1024x768'''
    url = _url.strip()
    ext = os.path.splitext(url)[1]
    filename = hash_str(url) + ext
    filepath = os.path.join(Config.IMG_LARGE_DIR, filename)
    return get_image(url, filepath)

def search_songs(keyword, page):
    url = ''.join([
        SEARCH,
        'ft=music&rn=',
        str(SONG_NUM),
        '&newsearch=1&primitive=0&cluster=0',
        '&itemset=newkm&rformat=json&encoding=utf8&all=',
        parse.quote(keyword),
        '&pn=',
        str(page),
        ])
    if url not in req_cache:
        req_content = urlopen(url, use_cache=False)
        if not req_content:
            return (None, 0, 0)
        req_cache[url] = req_content
    try:
        songs_wrap = Utils.json_loads_single(req_cache[url].decode())
    except ValueError as e:
        return (None, 0, 0)
    hit = int(songs_wrap['TOTAL'])
    pages = math.ceil(hit / SONG_NUM)
    songs = songs_wrap['abslist']
    return (songs, hit, pages)

def search_artists(keyword, page):
    url = ''.join([
        SEARCH,
        'ft=artist&pn=',
        str(page),
        '&rn=',
        str(ICON_NUM),
        '&newsearch=1&primitive=0&cluster=0',
        '&itemset=newkm&rformat=json&encoding=utf8&all=',
        parse.quote(keyword),
        ])
    if url not in req_cache:
        req_content = urlopen(url, use_cache=False)
        if not req_content:
            return (None, 0, 0)
        req_cache[url] = req_content
    try:
        artists_wrap = Utils.json_loads_single(req_cache[url].decode())
    except ValueError as e:
        return (None, 0, 0)
    hit = int(artists_wrap['TOTAL'])
    pages = math.ceil(hit / SONG_NUM)
    artists = artists_wrap['abslist']
    return (artists, hit, pages)

def search_albums(keyword, page):
    url = ''.join([
        SEARCH,
        'ft=album&pn=',
        str(page),
        '&rn=',
        str(ICON_NUM),
        '&newsearch=1&primitive=0&cluster=0',
        '&itemset=newkm&rformat=json&encoding=utf8&all=',
        parse.quote(keyword),
        ])
    if url not in req_cache:
        req_content = urlopen(url, use_cache=False)
        if not req_content:
            return (None, 0, 0)
        req_cache[url] = req_content
    try:
        albums_wrap = Utils.json_loads_single(req_cache[url].decode())
    except ValueError  as e:
        return (None, 0, 0)
    hit = int(albums_wrap['total'])
    pages = math.ceil(hit / ICON_NUM)
    albums = albums_wrap['albumlist']
    return (albums, hit, pages)

def get_index_nodes(nid):
    '''Get content of nodes from nid=2 to nid=15'''
    url = ''.join([
        QUKU,
        'op=query&fmt=json&src=mbox&cont=ninfo&pn=0&rn=',
        str(ICON_NUM),
        '&node=',
        str(nid),
        ])
    req_content = urlopen(url)
    if not req_content:
        return None
    try:
        nodes_wrap = json.loads(req_content.decode())
    except ValueError as e:
        return None
    return nodes_wrap

def get_themes_main():
    def append_to_nodes(nid, use_child=True):
        nodes_wrap = get_index_nodes(nid)
        if not nodes_wrap:
            return None
        if use_child:
            # node is limited to 10, no more are needed.
            for node in nodes_wrap['child'][:10]:
                nodes.append({
                    'name': node['disname'],
                    'nid': int(node['id']),
                    'info': node['info'],
                    'pic': node['pic'],
                    })
        else:
            # Because of different image style, we use child picture instaed
            node = nodes_wrap['ninfo']
            pic = nodes_wrap['child'][0]['pic']
            nodes.append({
                'name': node['disname'],
                'nid': int(node['id']),
                'info': node['info'],
                'pic': pic,
                })

    nodes = []
    # Languages 10(+)
    append_to_nodes(10)
    # People 11
    append_to_nodes(11, False)
    # Festivals 12
    append_to_nodes(12, False)
    # Feelings 13(+)
    append_to_nodes(13)
    # Thmes 14
    append_to_nodes(14, False)
    # Tyles 15(+)
    append_to_nodes(15)
    # Time 72325
    append_to_nodes(72325, False)
    # Environment 72326
    append_to_nodes(72326, False)
    if len(nodes) > 0:
        return nodes
    else:
        return None

def get_themes_songs(nid, page):
    url = ''.join([
        QUKU_SONG,
        'op=getlistinfo&encode=utf-8&identity=kuwo&keyset=pl2012&rn=',
        str(SONG_NUM),
        '&pid=',
        str(nid),
        '&pn=',
        str(page),
        ])
    if url not in req_cache:
        req_content = urlopen(url, use_cache=False)
        if not req_content:
            return (None, 0)
        req_cache[url] = req_content
    try:
        songs_wrap = json.loads(req_cache[url].decode())
    except ValueError as e:
        return (None, 0)
    pages = math.ceil(int(songs_wrap['total']) / SONG_NUM)
    return (songs_wrap['musiclist'], pages)

def get_mv_songs(pid, page):
    url = ''.join([
        QUKU_SONG,
        'op=getlistinfo&pn=',
        str(page),
        '&rn=',
        str(ICON_NUM),
        '&encode=utf-8&keyset=mvpl&pid=',
        str(pid),
        ])
    req_content = urlopen(url)
    if not req_content:
        return (None, 0)
    try:
        songs_wrap = json.loads(req_content.decode())
    except ValueError as e:
        return (None, 0)
    songs = songs_wrap['musiclist']
    pages = math.ceil(int(songs_wrap['total']) / ICON_NUM)
    return (songs, pages)

def get_radios_nodes():
    nid = 8
    return get_nodes(nid)

def get_radio_songs(nid, offset):
    url = ''.join([
        'http://gxh2.kuwo.cn/newradio.nr?',
        'type=4&uid=0&login=0&size=20&fid=',
        str(nid),
        '&offset=',
        str(offset),
        ])
    req_content = urlopen(url)
    if not req_content:
        return None
    songs = Utils.parse_radio_songs(req_content.decode('gbk'))
    return songs

def get_song_link(song, conf, use_mv=False):
    '''song is song_info dict.

    @conf, is used to to read conf['use-ape'], conf['use-mkv'],
    conf['song-dir'] and song['mv-dir'].
    use_mv, default is False, which will get mp3 link.
    Return:
     @cached : if is True, local song exists
               if is False, no available song_link
     @song_link: music source link; if local song exists or failed to get
              music source link, returns ''
     @song_path: target abs-path this song will be cached.
    '''
    if use_mv:
        ext = 'mkv|mp4' if conf['use-mkv'] else 'mp4'
    else:
        ext = 'ape|mp3' if conf['use-ape'] else 'mp3'
    url = ''.join([
        SONG,
        'response=url&type=convert_url&format=',
        ext,
        '&rid=MUSIC_',
        str(song['rid']),
        ])
    song_name = (''.join([
        song['artist'],
        '-',
        song['name'],
        '.',
        ext,
        ])).replace('/', '+')
    if use_mv:
        song_path = os.path.join(conf['mv-dir'], song_name)
    else:
        song_path = os.path.join(conf['song-dir'], song_name)
    if os.path.exists(song_path):
        return (True, '', song_path)
    req_content = urlopen(url)
    if not req_content:
        return (False, '', song_path)
    song_link = req_content.decode()
    if len(song_link) < 20:
        return (False, '', song_path)
    song_list = song_link.split('/')
    song_link = '/'.join(song_list[:3] + song_list[5:])
    # update song path
    song_path = ''.join([os.path.splitext(song_path)[0],
                         os.path.splitext(song_link)[1]])
    if os.path.exists(song_path):
        return (True, '', song_path)
    return (False, song_link, song_path)


class AsyncSong(GObject.GObject):
    '''Download song(including MV).

    Use Gobject to emit signals:
    register three signals: can-play and downloaded
    if `can-play` emited, player will receive a filename which have
    at least 1M to play.
    `chunk-received` signal is used to display the progressbar of 
    downloading process.
    `downloaded` signal may be used to popup a message to notify 
    user that a new song is downloaded.
    '''
    __gsignals__ = {
            'can-play': (GObject.SIGNAL_RUN_LAST, 
                # sogn_path
                GObject.TYPE_NONE, (str, )),
            'chunk-received': (GObject.SIGNAL_RUN_LAST,
                # percent
                GObject.TYPE_NONE, (GObject.TYPE_DOUBLE, )),
            'downloaded': (GObject.SIGNAL_RUN_LAST, 
                # song_path
                GObject.TYPE_NONE, (str, )),
            'disk-error': (GObject.SIGNAL_RUN_LAST,
                GObject.TYPE_NONE, (str, )),
            'network-error': (GObject.SIGNAL_RUN_LAST,
                GObject.TYPE_NONE, (str, )),
            }

    def __init__(self, app):
        super().__init__()
        self.app = app
        self.force_quit = False

    def destroy(self):
        self.force_quit = True

    def get_song(self, song, use_mv=False):
        '''Get the actual link of music file.

        If higher quality of that music unavailable, a lower one is used.
        like this:
        response=url&type=convert_url&format=ape|mp3&rid=MUSIC_3312608
        '''
        async_call(self._download_song, empty_func, song, use_mv)

    def _download_song(self, song, use_mv):
        cached, song_link, song_path = get_song_link(
                song, self.app.conf, use_mv=use_mv)

        # check song already cached 
        if cached:
            self.emit('can-play', song_path)
            self.emit('downloaded', song_path)
            return

        # this song has no link to download
        if not song_link:
            self.emit('network-error', song_link)
            return

        chunk_to_play = CHUNK_TO_PLAY
        if self.app.conf['use-ape']:
            chunk_to_play = CHUNK_APE_TO_PLAY
        if use_mv:
            chunk_to_play = CHUNK_MV_TO_PLAY

        for retried in range(MAXTIMES):
            try:
                req = request.urlopen(song_link)
                received_size = 0
                can_play_emited = False
                content_length = int(req.headers.get('Content-Length'))
                fh = open(song_path, 'wb')

                while True:
                    if self.force_quit:
                        del req
                        fh.close()
                        os.remove(song_path)
                        return
                    chunk = req.read(CHUNK)
                    received_size += len(chunk)
                    percent = received_size / content_length
                    self.emit('chunk-received', percent)
                    # this signal only emit once.
                    if ((received_size > chunk_to_play or percent > 40) and
                            not can_play_emited):
                        can_play_emited = True
                        self.emit('can-play', song_path)
                    if not chunk:
                        break
                    fh.write(chunk)
                fh.close()
                self.emit('downloaded', song_path)
                Utils.iconvtag(song_path, song)
                return

            except URLError as e:
                pass
            except FileNotFoundError as e:
                self.emit('disk-error', song_path)
                return
        if os.path.exists(song_path):
            os.remove(song_path)
        self.emit('network-error', song_link)

GObject.type_register(AsyncSong)

########NEW FILE########
__FILENAME__ = Player

# Copyright (C) 2013-2014 LiuLang <gsushzhsosgsu@gmail.com>

# Use of this source code is governed by GPLv3 license that can be found
# in the LICENSE file.

import sys
import time
from gi.repository import Gdk
from gi.repository import GdkPixbuf
from gi.repository import GLib
from gi.repository import GObject
from gi.repository import Gtk

from kuwo import Config
from kuwo import Net
from kuwo.Preferences import Preferences
from kuwo.PlayerBin import PlayerBin
from kuwo.PlayerDBus import PlayerDBus
from kuwo.PlayerNotify import PlayerNotify
from kuwo import Widgets

_ = Config._
# Gdk.EventType.2BUTTON_PRESS is an invalid variable
GDK_2BUTTON_PRESS = 5
# set toolbar icon size to Gtk.IconSize.DND
ICON_SIZE = 5

MTV_AUDIO = 0 # use the first audio stream
OK_AUDIO = 1  # second audio stream

class PlayType:
    NONE = -1
    SONG = 0
    RADIO = 1
    MV = 2
    KARAOKE = 3

class RepeatType:
    NONE = 0
    ALL = 1
    ONE = 2

def delta(nanosec_float):
    _seconds = nanosec_float // 10**9
    mm, ss = divmod(_seconds, 60)
    hh, mm = divmod(mm, 60)
    if hh == 0:
        s = '%d:%02d' % (mm, ss)
    else:
        s = '%d:%02d:%02d' % (hh, mm, ss)
    return s

class Player(Gtk.Box):
    def __init__(self, app):
        super().__init__()
        self.app = app

        self.fullscreen_sid = 0
        self.play_type = PlayType.NONE
        self.adj_timeout = 0
        self.recommend_imgs = None
        self.curr_song = None

        # use this to keep Net.AsyncSong object
        self.async_song = None
        self.async_next_song = None

        event_pic = Gtk.EventBox()
        event_pic.connect('button-press-event', self.on_pic_pressed)
        self.pack_start(event_pic, False, False, 0)

        self.artist_pic = Gtk.Image.new_from_pixbuf(app.theme['anonymous'])
        event_pic.add(self.artist_pic)

        control_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.pack_start(control_box, True, True, 0)

        toolbar = Gtk.Toolbar()
        toolbar.set_style(Gtk.ToolbarStyle.ICONS)
        toolbar.get_style_context().add_class(Gtk.STYLE_CLASS_MENUBAR)
        toolbar.set_show_arrow(False)
        toolbar.set_icon_size(ICON_SIZE)
        control_box.pack_start(toolbar, False, False, 0)

        prev_button = Gtk.ToolButton()
        prev_button.set_label(_('Previous'))
        prev_button.set_icon_name('media-skip-backward-symbolic')
        prev_button.connect('clicked', self.on_prev_button_clicked)
        toolbar.insert(prev_button, 0)

        self.play_button = Gtk.ToolButton()
        self.play_button.set_label(_('Play'))
        self.play_button.set_icon_name('media-playback-start-symbolic')
        self.play_button.connect('clicked', self.on_play_button_clicked)
        toolbar.insert(self.play_button, 1)

        next_button = Gtk.ToolButton()
        next_button.set_label(_('Next'))
        next_button.set_icon_name('media-skip-forward-symbolic')
        next_button.connect('clicked', self.on_next_button_clicked)
        toolbar.insert(next_button, 2)

        self.shuffle_btn = Gtk.ToggleToolButton()
        self.shuffle_btn.set_label(_('Shuffle'))
        self.shuffle_btn.set_icon_name('media-playlist-shuffle-symbolic')
        self.shuffle_btn.props.margin_left = 10
        toolbar.insert(self.shuffle_btn, 3)

        self.repeat_type = RepeatType.NONE
        self.repeat_btn = Gtk.ToggleToolButton()
        self.repeat_btn.set_label(_('Repeat'))
        self.repeat_btn.set_icon_name('media-playlist-repeat-symbolic')
        self.repeat_btn.connect('clicked', self.on_repeat_button_clicked)
        toolbar.insert(self.repeat_btn, 4)

        self.use_audio_btn = Gtk.RadioToolButton()
        self.use_audio_btn.set_label(_('Play audio'))
        self.use_audio_btn.set_icon_name('audio-x-generic-symbolic')
        self.use_audio_btn.props.margin_left = 10
        self.use_audio_btn.set_active(True)
        self.use_audio_sid = self.use_audio_btn.connect(
                'toggled', self.on_play_type_toggled, PlayType.SONG)
        toolbar.insert(self.use_audio_btn, 5)

        self.use_mtv_btn = Gtk.RadioToolButton()
        self.use_mtv_btn.set_label(_('Play MTV'))
        self.use_mtv_btn.set_tooltip_text(_('Play MTV'))
        self.use_mtv_btn.set_icon_name('video-x-generic-symbolic')
        self.use_mtv_btn.set_sensitive(False)
        self.use_mtv_btn.props.group = self.use_audio_btn
        self.use_mtv_sid = self.use_mtv_btn.connect(
                'toggled', self.on_play_type_toggled, PlayType.MV)
        toolbar.insert(self.use_mtv_btn, 6)

        self.use_ok_btn = Gtk.RadioToolButton()
        self.use_ok_btn.set_label(_('Play Karaoke'))
        self.use_ok_btn.set_tooltip_text(
                _('Play Karaoke\nPlease use mkv format'))
        self.use_ok_btn.set_icon_name('audio-input-microphone-symbolic')
        self.use_ok_btn.set_sensitive(False)
        self.use_ok_btn.props.group = self.use_audio_btn
        self.use_ok_btn.connect(
                'toggled', self.on_play_type_toggled, PlayType.KARAOKE)
        toolbar.insert(self.use_ok_btn, 7)

        self.fullscreen_btn = Gtk.ToolButton()
        self.fullscreen_btn.set_label(_('Fullscreen'))
        self.fullscreen_btn.set_icon_name('view-fullscreen-symbolic')
        self.fullscreen_btn.props.margin_left = 10
        self.fullscreen_btn.connect(
                'clicked', self.on_fullscreen_button_clicked)
        toolbar.insert(self.fullscreen_btn, 8)
        self.app.window.connect('key-press-event', self.on_window_key_pressed)

        self.favorite_btn = Gtk.ToolButton()
        self.favorite_btn.set_label(_('Favorite'))
        self.favorite_btn.set_icon_name('no-favorite')
        self.favorite_btn.set_tooltip_text(_('Add to Favorite playlist'))
        self.favorite_btn.props.margin_left = 10
        self.favorite_btn.connect('clicked', self.on_favorite_btn_clicked)
        toolbar.insert(self.favorite_btn, 9)

        # contro menu
        menu_tool_item = Gtk.ToolItem()
        toolbar.insert(menu_tool_item, 10)
        toolbar.child_set_property(menu_tool_item, 'expand', True)
        main_menu = Gtk.Menu()
        pref_item = Gtk.MenuItem(label=_('Preferences'))
        pref_item.connect(
                'activate', self.on_main_menu_pref_activate)
        main_menu.append(pref_item)
        sep_item = Gtk.SeparatorMenuItem()
        main_menu.append(sep_item)
        about_item = Gtk.MenuItem(label=_('About'))
        about_item.connect(
                'activate', self.on_main_menu_about_activate)
        main_menu.append(about_item)
        quit_item = Gtk.MenuItem(label=_('Quit'))
        key, mod = Gtk.accelerator_parse('<Ctrl>Q')
        quit_item.add_accelerator(
                'activate', app.accel_group,
                key, mod, Gtk.AccelFlags.VISIBLE)
        quit_item.connect(
                'activate', self.on_main_menu_quit_activate)
        main_menu.append(quit_item)
        main_menu.show_all()
        menu_image = Gtk.Image()
        menu_image.set_from_icon_name('view-list-symbolic', ICON_SIZE)
        if Config.GTK_LE_36:
            menu_btn = Gtk.Button()
            menu_btn.connect(
                    'clicked', self.on_main_menu_button_clicked, main_menu)
        else:
            menu_btn = Gtk.MenuButton()
            menu_btn.set_popup(main_menu)
            menu_btn.set_always_show_image(True)
        menu_btn.props.halign = Gtk.Align.END
        menu_btn.set_image(menu_image)
        menu_tool_item.add(menu_btn)

        self.label = Gtk.Label(
                '<b>{0}</b> <small>by {0}</small>'.format(_('Unknown')))
        self.label.props.use_markup = True
        self.label.props.xalign = 0
        self.label.props.margin_left = 10
        control_box.pack_start(self.label, False, False, 0)

        scale_box = Gtk.Box(spacing=3)
        scale_box.props.margin_left = 5
        control_box.pack_start(scale_box, True, False, 0)

        self.scale = Gtk.Scale()
        self.adjustment = Gtk.Adjustment(0, 0, 100, 1, 10, 0)
        self.adjustment.connect('changed', self.on_adjustment_changed)
        self.scale.set_adjustment(self.adjustment)
        self.scale.set_show_fill_level(False)
        self.scale.set_restrict_to_fill_level(False)
        self.scale.props.draw_value = False
        self.scale.connect('change-value', self.on_scale_change_value)
        scale_box.pack_start(self.scale, True, True, 0)

        self.time_label = Gtk.Label('0:00/0:00')
        scale_box.pack_start(self.time_label, False, False, 0)

        self.volume = Gtk.VolumeButton()
        self.volume.props.use_symbolic = True
        self.volume.set_value(app.conf['volume'] ** 0.33)
        self.volume_sid = self.volume.connect(
                'value-changed', self.on_volume_value_changed)
        scale_box.pack_start(self.volume, False, False, 0)

        # init playbin and dbus
        self.playbin = PlayerBin()
        self.playbin.set_volume(self.app.conf['volume'] ** 0.33)
        self.playbin.connect('eos', self.on_playbin_eos)
        self.playbin.connect('error', self.on_playbin_error)
        self.playbin.connect('mute-changed', self.on_playbin_mute_changed)
        self.playbin.connect(
                'volume-changed', self.on_playbin_volume_changed)
        self.dbus = PlayerDBus(self)
        self.notify = PlayerNotify(self)

    def after_init(self):
        self.init_meta()

    def do_destroy(self):
        self.playbin.destroy()
        if self.async_song:
            self.async_song.destroy()
        if self.async_next_song:
            self.async_next_song.destroy()

    def load(self, song):
        self.play_type = PlayType.SONG
        self.curr_song = song
        self.update_favorite_button_status()
        self.stop_player()
        self.use_audio_btn.handler_block(self.use_audio_sid)
        self.use_audio_btn.set_active(True)
        self.use_audio_btn.handler_unblock(self.use_audio_sid)
        self.create_new_async(song)

    def create_new_async(self, *args, **kwds):
        self.scale.set_fill_level(0)
        self.scale.set_show_fill_level(True)
        self.scale.set_restrict_to_fill_level(True)
        self.adjustment.set_lower(0.0)
        self.adjustment.set_upper(100.0)
        if self.async_song:
            self.async_song.destroy()
        self.async_song = Net.AsyncSong(self.app)
        self.async_song.connect('chunk-received', self.on_chunk_received)
        self.async_song.connect('can-play', self.on_song_can_play)
        self.async_song.connect('downloaded', self.on_song_downloaded)
        self.async_song.connect('disk-error', self.on_song_disk_error)
        self.async_song.connect('network-error', self.on_song_network_error)
        self.async_song.get_song(*args, **kwds)

    def on_chunk_received(self, widget, percent):
        def _update_fill_level():
            self.scale.set_fill_level(percent * self.adjustment.get_upper())
        GLib.idle_add(_update_fill_level)

    def on_song_disk_error(self, widget, song_path):
        '''Disk error: occurs when disk is not available.'''
        GLib.idle_add(
                Widgets.filesystem_error, self.app.window, song_path)
        self.stop_player_cb()

    def on_song_network_error(self, widget, song_link):
        '''Failed to get source link, or failed to download song'''
        self.stop_player_cb()
        if self.play_type == PlayType.MV:
            msg = _('Failed to download MV')
        elif self.play_type in (PlayType.SONG, PlayType.RADIO):
            msg = _('Failed to download song')
        GLib.idle_add(Widgets.network_error, self.app.window, msg)
        self.load_next_cb()

    def on_song_can_play(self, widget, song_path):
        def _on_song_can_play():
            uri = 'file://' + song_path
            self.meta_url = uri

            if self.play_type in (PlayType.SONG, PlayType.RADIO):
                self.app.lrc.show_music()
                self.playbin.load_audio(uri)
                self.get_lrc()
                self.get_mv_link()
                self.get_recommend_lists()
            elif self.play_type == PlayType.MV:
                self.use_mtv_btn.set_sensitive(True)
                if not self.use_ok_btn.get_sensitive():
                    GLib.timeout_add(2000, self.check_audio_streams)
                self.app.lrc.show_mv()
                audio_stream = MTV_AUDIO
                if self.use_ok_btn.get_active():
                    audio_stream = OK_AUDIO
                self.playbin.load_video(uri, self.app.lrc.xid, audio_stream)
            self.start_player(load=True)
            self.update_player_info()
        GLib.idle_add(_on_song_can_play)

    def on_song_downloaded(self, widget, song_path):
        def _on_song_download():
            self.async_song.destroy()
            self.async_song = None
            self.scale.set_fill_level(self.adjustment.get_upper())
            self.scale.set_show_fill_level(False)
            self.scale.set_restrict_to_fill_level(False)
            self.init_adjustment()
            if self.play_type in (PlayType.SONG, PlayType.MV):
                self.app.playlist.on_song_downloaded(play=True)
                self.next_song = self.app.playlist.get_next_song(
                        self.repeat_btn.get_active(),
                        self.shuffle_btn.get_active())
            elif self.play_type == PlayType.RADIO:
                self.next_song = self.curr_radio_item.get_next_song()
            if self.next_song:
                self.cache_next_song()
            # update metadata in dbus
            self.dbus.update_meta()
            self.dbus.enable_seek()

        GLib.idle_add(_on_song_download)

    def cache_next_song(self):
        if self.play_type == PlayType.MV:
            use_mv = True
        elif self.play_type in (PlayType.SONG, PlayType.RADIO):
            use_mv = False
        if self.async_next_song:
            self.async_next_song.destroy()
        self.async_next_song = Net.AsyncSong(self.app)
        self.async_next_song.get_song(self.next_song, use_mv=use_mv)

    def init_adjustment(self):
        self.adjustment.set_value(0.0)
        self.adjustment.set_lower(0.0)
        # when song is not totally downloaded but can play, query_duration
        # might give incorrect/inaccurate result.
        status, duration = self.playbin.get_duration()
        if status and duration > 0:
            self.adjustment.set_upper(duration)
            return False
        return True

    def sync_adjustment(self):
        status, offset = self.playbin.get_position()
        if not status:
            return True

        self.dbus.update_pos(offset // 1000)

        status, duration = self.playbin.get_duration()
        self.adjustment.set_value(offset)
        self.adjustment.set_upper(duration)
        self.sync_label_by_adjustment()
        if offset >= duration - 800000000:
            self.load_next()
            return False
        if self.play_type == PlayType.MV:
            return True
        self.app.lrc.sync_lrc(offset)
        if self.recommend_imgs and len(self.recommend_imgs) > 0:
            # change lyrics background image every 20 seconds
            div, mod = divmod(int(offset / 10**9), 20)
            if mod == 0:
                div2, mod2 = divmod(div, len(self.recommend_imgs))
                self.update_lrc_background(self.recommend_imgs[mod2])
        return True

    def sync_label_by_adjustment(self):
        curr = delta(self.adjustment.get_value())
        total = delta(self.adjustment.get_upper())
        self.time_label.set_label('{0}/{1}'.format(curr, total))

    # Control panel
    def on_pic_pressed(self, eventbox, event):
        if event.type == GDK_2BUTTON_PRESS and \
                self.play_type == PlayType.SONG:
            self.app.playlist.locate_curr_song()

    def on_prev_button_clicked(self, button):
        self.load_prev()

    def on_play_button_clicked(self, button):
        if self.play_type == PlayType.NONE:
            return
        self.play_pause()

    def on_next_button_clicked(self, button):
        self.load_next()

    def on_repeat_button_clicked(self, button):
        if self.repeat_type == RepeatType.NONE:
            self.repeat_type = RepeatType.ALL
            button.set_active(True)
            button.set_icon_name('media-playlist-repeat-symbolic')
        elif self.repeat_type == RepeatType.ALL:
            self.repeat_type = RepeatType.ONE
            button.set_active(True)
            button.set_icon_name('media-playlist-repeat-song-symbolic')
        elif self.repeat_type == RepeatType.ONE:
            self.repeat_type = RepeatType.NONE
            button.set_active(False)
            button.set_icon_name('media-playlist-repeat-symbolic')

    def on_scale_change_value(self, scale, scroll_type, value):
        self.seek_cb(value)

    def on_volume_value_changed(self, volume_button, volume):
        self.playbin.set_volume(volume ** 3)
        self.app.conf['volume'] = volume ** 3
        if self.playbin.get_mute():
            self.playbin.set_mute(False)

    def update_player_info(self):
        def _update_pic(info, error=None):
            if not info or error:
                return
            self.artist_pic.set_tooltip_text(
                    Widgets.short_tooltip(info['info'], length=500))
            if info['pic']:
                self.meta_artUrl = info['pic']
                pix = GdkPixbuf.Pixbuf.new_from_file_at_size(
                        info['pic'], 100, 100)
                self.artist_pic.set_from_pixbuf(pix)
            else:
                self.meta_artUrl = self.app.theme_path['anonymous']
            self.notify.refresh()
            self.dbus.update_meta()
            
        song = self.curr_song
        name = Widgets.short_tooltip(song['name'], 45)
        if song['artist']:
            artist = Widgets.short_tooltip(song['artist'], 20)
        else:
            artist = _('Unknown')
        if song['album']:
            album = Widgets.short_tooltip(song['album'], 30)
        else:
            album = _('Unknown')
        label = '<b>{0}</b> <small>by {1} from {2}</small>'.format(
                name, artist, album)
        self.label.set_label(label)
        self.app.window.set_title(name)
        self.artist_pic.set_from_pixbuf(self.app.theme['anonymous'])
        Net.async_call(
                Net.get_artist_info, _update_pic, 
                song['artistid'], song['artist'])

    def get_lrc(self):
        def _update_lrc(lrc_text, error=None):
            self.app.lrc.set_lrc(lrc_text)
        Net.async_call(Net.get_lrc, _update_lrc, self.curr_song)

    def get_recommend_lists(self):
        self.recommend_imgs = None
        def _on_list_received(imgs, error=None):
            if not imgs or len(imgs) < 10:
                self.recommend_imgs = None
            else:
                self.recommend_imgs = imgs.splitlines()
        Net.async_call(
                Net.get_recommend_lists, _on_list_received, 
                self.curr_song['artist'])

    def update_lrc_background(self, url):
        def _update_background(filepath, error=None):
            if error or not filepath:
                return
            self.app.lrc.update_background(filepath)
        Net.async_call(Net.get_recommend_image, _update_background, url)

    # Radio part
    def load_radio(self, song, radio_item):
        '''Load Radio song.

        song from radio, only contains name, artist, rid, artistid
        Remember to update its information.
        '''
        self.play_type = PlayType.RADIO
        self.stop_player()
        self.curr_radio_item = radio_item
        self.curr_song = song
        self.update_favorite_button_status()
        self.create_new_async(song)

    # MV part
    def check_audio_streams(self):
        self.use_ok_btn.set_sensitive(self.playbin.get_audios() > 1)

    def on_play_type_toggled(self, toggle_button, play_type):
        if not toggle_button.get_active():
            return
        if self.play_type == PlayType.NONE:
            return
        elif play_type == PlayType.SONG or play_type == PlayType.RADIO:
            self.app.lrc.show_music()
            self.load(self.curr_song)
        elif play_type == PlayType.MV:
            if self.play_type == PlayType.KARAOKE:
                self.playbin.set_current_audio(MTV_AUDIO)
                self.play_type = PlayType.MV
            else:
                self.app.lrc.show_mv()
                self.load_mv(self.curr_song)
                self.app.popup_page(self.app.lrc.app_page)
        elif play_type == PlayType.KARAOKE:
            if self.play_type == PlayType.MV:
                self.playbin.set_current_audio(OK_AUDIO)
                self.play_type = PlayType.KARAOKE
            else:
                self.app.lrc.show_mv()
                self.load_mv(self.curr_song)
                self.app.popup_page(self.app.lrc.app_page)


    def load_mv(self, song):
        self.play_type = PlayType.MV
        self.curr_song = song
        self.update_favorite_button_status()
        self.stop_player()
        self.use_mtv_btn.handler_block(self.use_mtv_sid)
        self.use_mtv_btn.set_active(True)
        self.use_mtv_btn.handler_unblock(self.use_mtv_sid)
        self.create_new_async(song, use_mv=True)

    def get_mv_link(self):
        def _update_mv_link(mv_args, error=None):
            cached, mv_link, mv_path = mv_args
            if cached or mv_link:
                self.use_mtv_btn.set_sensitive(True)
            else:
                self.use_mtv_btn.set_sensitive(False)
        Net.async_call(
                Net.get_song_link, _update_mv_link,
                self.curr_song, self.app.conf, True)

    # Fullscreen
    def get_fullscreen(self):
        '''Check if player is in fullscreen mode.'''
        return self.fullscreen_sid > 0

    def toggle_fullscreen(self):
        '''Switch between fullscreen and unfullscreen mode.'''
        self.fullscreen_btn.emit('clicked')

    def on_window_key_pressed(self, widget, event):
        # press Esc to exit fullscreen mode
        if event.keyval == Gdk.KEY_Escape and self.get_fullscreen():
            self.toggle_fullscreen()
        # press F11 to toggle fullscreen mode
        elif event.keyval == Gdk.KEY_F11:
            self.toggle_fullscreen()

    def on_fullscreen_button_clicked(self, button):
        window = self.app.window
        if self.fullscreen_sid > 0:
        # unfullscreen
            self.app.notebook.set_show_tabs(True)
            button.set_icon_name('view-fullscreen-symbolic')
            self.show()
            window.realize()
            window.unfullscreen()
            window.disconnect(self.fullscreen_sid)
            self.fullscreen_sid = 0
        else:
        # fullscreen
            self.app.notebook.set_show_tabs(False)
            button.set_icon_name('view-restore-symbolic')
            self.app.popup_page(self.app.lrc.app_page)
            self.hide()
            window.realize()
            window.fullscreen()
            self.fullscreen_sid = window.connect(
                    'motion-notify-event', self.on_window_motion_notified)
            self.playbin.expose_fullscreen()

    def on_window_motion_notified(self, widget, event):
        # if mouse_point.y is not in [0, 50], ignore it
        if event.y > 50:
            return

        # show control_panel and notebook labels
        self.show_all()
        # delay 3 seconds and hide them
        self.fullscreen_timestamp = time.time()
        GLib.timeout_add(
                3000, self.hide_control_panel_and_label, 
                self.fullscreen_timestamp)
        self.playbin.expose_fullscreen()

    def hide_control_panel_and_label(self, timestamp):
        if (timestamp == self.fullscreen_timestamp and 
                self.fullscreen_sid > 0):
            self.app.notebook.set_show_tabs(False)
            self.hide()

    def on_favorite_btn_clicked(self, button):
        if not self.curr_song:
            return
        self.toggle_favorite_status()

    def update_favorite_button_status(self):
        if not self.curr_song:
            return
        if self.get_favorite_status():
            self.favorite_btn.set_icon_name('favorite')
        else:
            self.favorite_btn.set_icon_name('no-favorite')

    def get_favorite_status(self):
        return self.app.playlist.check_song_in_playlist(
                self.curr_song, 'Favorite')

    def toggle_favorite_status(self):
        if not self.curr_song:
            return
        if self.app.playlist.check_song_in_playlist(
                self.curr_song, 'Favorite'):
            self.app.playlist.remove_song_from_playlist(
                    self.curr_song, 'Favorite')
            self.favorite_btn.set_icon_name('no-favorite')
        else:
            self.app.playlist.add_song_to_playlist(
                    self.curr_song, 'Favorite')
            self.favorite_btn.set_icon_name('favorite')

    # menu button
    def on_main_menu_button_clicked(self, button, main_menu):
        main_menu.popup(
                None, None, None, None, 1, Gtk.get_current_event_time())

    def on_main_menu_pref_activate(self, menu_item):
        dialog = Preferences(self.app)
        dialog.run()
        dialog.destroy()
        self.app.load_styles()
        self.app.lrc.update_highlighted_tag()
        self.app.shortcut.rebind_keys()

    def on_main_menu_about_activate(self, menu_item):
        dialog = Gtk.AboutDialog()
        dialog.set_modal(True)
        dialog.set_transient_for(self.app.window)
        dialog.set_program_name(Config.APPNAME)
        dialog.set_logo(self.app.theme['app-logo'])
        dialog.set_version(Config.VERSION)
        dialog.set_comments(Config.DESCRIPTION)
        dialog.set_copyright(Config.COPYRIGHT)
        dialog.set_website(Config.HOMEPAGE)
        dialog.set_license_type(Gtk.License.GPL_3_0)
        dialog.set_authors(Config.AUTHORS)
        dialog.run()
        dialog.destroy()

    def on_main_menu_quit_activate(self, menu_item):
        self.app.quit()


    # playbin signal handlers
    def on_playbin_eos(self, playbin, eos_msg):
        self.load_next()

    def on_playbin_error(self, playbin, error_msg):
        print('Player.on_playbin_error(), ', error_msg)
        self.load_next()

    def on_playbin_mute_changed(self, playbin, mute):
        self.update_gtk_volume_value_cb()

    def on_playbin_volume_changed(self, playbin, volume):
        self.update_gtk_volume_value_cb()

    def update_gtk_volume_value(self):
        mute = self.playbin.get_mute()
        volume = self.playbin.get_volume()
        if mute:
            self.volume.handler_block(self.volume_sid)
            self.volume.set_value(0.0)
            self.volume.handler_unblock(self.volume_sid)
        else:
            self.volume.handler_block(self.volume_sid)
            self.volume.set_value(volume ** 0.33)
            self.volume.handler_unblock(self.volume_sid)
        self.app.conf['volume'] = volume

    def update_gtk_volume_value_cb(self):
        GLib.idle_add(self.update_gtk_volume_value)


    # control player, UI and dbus
    def is_playing(self):
        #return self.playbin.is_playing()
        return self._is_playing

    def start_player(self, load=False):
        if self.play_type == PlayType.NONE:
            return
        self._is_playing = True

        self.dbus.set_Playing()

        self.play_button.set_icon_name('media-playback-pause-symbolic')
        self.playbin.play()
        self.adj_timeout = GLib.timeout_add(250, self.sync_adjustment)
        if load:
            self.playbin.set_volume(self.app.conf['volume'])
            self.init_meta()
            GLib.timeout_add(1500, self.init_adjustment)
        self.notify.refresh()

    def start_player_cb(self, load=False):
        GLib.idle_add(self.start_player, load)

    def pause_player(self):
        if self.play_type == PlayType.NONE:
            return
        self._is_playing = False
        self.dbus.set_Pause()
        self.play_button.set_icon_name('media-playback-start-symbolic')
        self.playbin.pause()
        if self.adj_timeout > 0:
            GLib.source_remove(self.adj_timeout)
            self.adj_timeout = 0
        self.notify.refresh()

    def pause_player_cb(self):
        GLib.idle_add(self.pause_player)

    def play_pause(self):
        if self.play_type == PlayType.NONE:
            return
        if self.playbin.is_playing():
            self.pause_player()
        else:
            self.start_player()

    def play_pause_cb(self):
        GLib.idle_add(self.play_pause)

    def stop_player(self):
        if self.play_type == PlayType.NONE:
            return
        self._is_playing = False
        self.play_button.set_icon_name('media-playback-pause-symbolic')
        self.playbin.stop()
        self.scale.set_value(0)
        if self.play_type != PlayType.MV:
            self.use_audio_btn.handler_block(self.use_audio_sid)
            self.use_audio_btn.set_active(True)
            self.use_audio_btn.handler_unblock(self.use_audio_sid)
            self.use_mtv_btn.set_sensitive(False)
            self.use_ok_btn.set_sensitive(False)
        self.time_label.set_label('0:00/0:00')
        if self.adj_timeout > 0:
            GLib.source_remove(self.adj_timeout)
            self.adj_timeout = 0

    def stop_player_cb(self):
        GLib.idle_add(self.stop_player)

    def load_prev(self):
        if self.play_type == PlayType.NONE or not self.can_go_previous():
            return
        self.stop_player()
        _repeat = self.repeat_btn.get_active()
        if self.play_type == PlayType.SONG:
            self.app.playlist.play_prev_song(repeat=_repeat, use_mv=False)
        elif self.play_type == PlayType.MV:
            self.app.playlist.play_prev_song(repeat=_repeat, use_mv=True)

    def load_prev_cb(self):
        GLib.idle_add(self.load_prev)

    def load_next(self):
        if self.play_type == PlayType.NONE:
            return
        self.stop_player()
        if self.repeat_type == RepeatType.ONE:
            if self.play_type == PlayType.MV:
                self.load_mv(self.curr_song)
            else:
                self.load(self.curr_song)
            return

        repeat = self.repeat_btn.get_active()
        shuffle = self.shuffle_btn.get_active()
        if self.play_type == PlayType.RADIO:
            self.curr_radio_item.play_next_song()
        elif self.play_type == PlayType.SONG:
            self.app.playlist.play_next_song(repeat, shuffle, use_mv=False)
        elif self.play_type == PlayType.MV:
            self.app.playlist.play_next_song(repeat, shuffle, use_mv=True)

    def load_next_cb(self):
        GLib.idle_add(self.load_next)

    def get_volume(self):
        return self.volume.get_value()

    def set_volume(self, volume):
        self.volume.set_value(volume)

    def set_volume_cb(self, volume):
        GLib.idle_add(self.set_volume, volume)

    def get_volume(self):
        return self.playbin.get_volume()

    def toggle_mute(self):
        mute = self.playbin.get_mute()
        self.playbin.set_mute(not mute)
        if mute:
            self.volume.handler_block(self.volume_sid)
            self.volume.set_value(self.app.conf['volume'])
            self.volume.handler_unblock(self.volume_sid)
        else:
            self.volume.handler_block(self.volume_sid)
            self.volume.set_value(0.0)
            self.volume.handler_unblock(self.volume_sid)

    def toggle_mute_cb(self):
        GLib.idle_add(self.toggle_mute)

    def seek(self, offset):
        if self.play_type == PlayType.NONE:
            return
        self.pause_player()
        self.playbin.seek(offset)
        GLib.timeout_add(300, self.start_player_cb)
        self.sync_label_by_adjustment()

    def seek_cb(self, offset):
        GLib.idle_add(self.seek, offset)

    def can_go_previous(self):
        if self.play_type in (PlayType.MV, PlayType.SONG):
            return True
        return False


    # dbus parts
    def init_meta(self):
        self.adjustment_upper = 0
        self.dbus.disable_seek()
        self.meta_url = ''
        self.meta_artUrl = ''

    def on_adjustment_changed(self, adj):
        self.dbus.update_meta()
        self.adjustment_upper = adj.get_upper()

########NEW FILE########
__FILENAME__ = PlayerBin

# Copyright (C) 2013-2014 LiuLang <gsushzhsosgsu@gmail.com>

# Use of this source code is governed by GPLv3 license that can be found
# in the LICENSE file.

import sys
from gi.repository import Gdk
from gi.repository import GLib
from gi.repository import GObject
from gi.repository import Gst
from gi.repository import GstVideo
from gi.repository import Gtk

# init Gst so that play works ok.
Gst.init(None)
GST_LOWER_THAN_1 = (Gst.version()[0] < 1)


class PlayerBin(GObject.GObject):
    '''Gstreamer wrapper.

    PlayerBin uses playbin as GstPipeline.
    '''
    
    __gsignals__ = {
            'eos': (GObject.SIGNAL_RUN_LAST, 
                GObject.TYPE_NONE, (bool, )),
            'error': (GObject.SIGNAL_RUN_LAST, 
                GObject.TYPE_NONE, (str, )),
            'mute-changed': (GObject.SIGNAL_RUN_LAST, 
                GObject.TYPE_NONE, (bool, )),
            'volume-changed': (GObject.SIGNAL_RUN_LAST, 
                GObject.TYPE_NONE, (float, )),
            }
    xid = None
    bus_sync_sid = 0
    audio_stream = 0

    def __init__(self):
        super().__init__()
        self.playbin = Gst.ElementFactory.make('playbin', None)
        screen = Gdk.Screen.get_default()
        self.fullscreen_rect = (0, 0, screen.width(), screen.height())
        
        if not self.playbin:
            print('Gst Error: playbin failed to be inited, abort!')
            sys.exit(1)
        self.bus = self.playbin.get_bus()
        self.bus.add_signal_watch()
        self.bus.connect('message::eos', self.on_eos)
        self.bus.connect('message::error', self.on_error)
        self.volume_sid = self.playbin.connect(
                'notify::volume', self.on_volume_changed)
        self.mute_sid = self.playbin.connect(
                'notify::mute', self.on_mute_changed)

    # Open APIs
    def load_audio(self, uri):
        self.set_uri(uri)
        self.disable_bus_sync()
        self.play()

    def load_video(self, uri, xid, audio_stream):
        print('load_video:', audio_stream)
        self.set_uri(uri)
        self.set_xid(xid)
        self.enable_bus_sync()
        self.play()
        GLib.timeout_add(2000, self.set_current_audio, audio_stream)

    def destroy(self):
        self.quit()

    def quit(self):
        self.stop()

    def play(self):
        self.playbin.set_state(Gst.State.PLAYING)

    def pause(self):
        self.playbin.set_state(Gst.State.PAUSED)

    def stop(self):
        self.playbin.set_state(Gst.State.NULL)

    def get_status(self):
        return self.playbin.get_state(5)[1]

    def is_playing(self):
        return self.get_status() == Gst.State.PLAYING

    def set_uri(self, uri):
        self.playbin.set_property('uri', uri)

    def get_uri(self):
        return self.playbin.get_property('uri')

    def get_position(self):
        if GST_LOWER_THAN_1:
            status, _type, offset = self.playbin.query_position(
                Gst.Format.TIME)
        else:
            status, offset = self.playbin.query_position(Gst.Format.TIME)
        return (status, offset)

    def set_position(self, offset):
        self.seek(offset)
        #self.set_current_audio(self.audio_stream)

    def seek(self, offset):
        self.playbin.seek_simple(
                Gst.Format.TIME,
                Gst.SeekFlags.FLUSH | Gst.SeekFlags.KEY_UNIT,
                offset)

    def get_duration(self):
        if GST_LOWER_THAN_1:
            status, _type, upper = self.playbin.query_duration(
                Gst.Format.TIME)
        else:
            status, upper = self.playbin.query_duration(Gst.Format.TIME)
        return (status, upper)

    def set_xid(self, xid):
        self.xid = xid

    def get_xid(self):
        return self.xid

    def set_volume(self, vol):
        self.playbin.handler_block(self.volume_sid)
        self.playbin.handler_block(self.mute_sid)
        self.playbin.set_property('volume', vol)
        self.playbin.handler_unblock(self.volume_sid)
        self.playbin.handler_unblock(self.mute_sid)

    def get_volume(self):
        return self.playbin.get_property('volume')

    def set_mute(self, mute):
        self.playbin.handler_block(self.mute_sid)
        self.playbin.set_property('mute', mute)
        self.playbin.handler_unblock(self.mute_sid)

    def get_mute(self):
        return self.playbin.get_property('mute')

    def set_current_audio(self, audio_stream):
        print('set_current_audio:', audio_stream)
        if self.get_audios() <= audio_stream:
            return
        self.playbin.props.current_audio = audio_stream

    def get_current_audio(self):
        return self.playbin.props.current_audio

    def get_audios(self):
        return self.playbin.props.n_audio

    # private functions
    def enable_bus_sync(self):
        self.bus.enable_sync_message_emission()
        self.bus_sync_sid = self.bus.connect(
                'sync-message::element', self.on_sync_message)

    def disable_bus_sync(self):
        if self.bus_sync_sid > 0:
            self.bus.disconnect(self.bus_sync_sid)
            self.bus.disable_sync_message_emission()
            self.bus_sync_sid = 0

    def on_sync_message(self, bus, msg):
        if not msg.get_structure():
            return
        if msg.get_structure().get_name() == 'prepare-window-handle':
            msg.src.set_window_handle(self.xid)
            msg.src.handle_events(False)
            msg.src.set_property('force-aspect-ratio', True)

    def expose(self, rect=None):
        '''Redraw video frame.

        This should be used when video overlay is resized.
        '''
        if self.bus_sync_sid == 0:
            return
        videosink = self.playbin.props.video_sink
        if not videosink:
            return
        if not rect:
            # reset to default size, used in window mode
            videosink.set_render_rectangle(0, 0, -1, -1)
        else:
            videosink.set_render_rectangle(*rect)
        videosink.expose()

    def expose_fullscreen(self):
        '''Redraw when in fullscreen mode'''
        self.expose(self.fullscreen_rect)

    def on_eos(self, bus, msg):
        self.emit('eos', True)

    def on_error(self, bus, msg):
        error_msg = msg.parse_error()
        self.emit('error', error_msg)

    def on_volume_changed(self, playbin, volume_name):
        self.emit('volume-changed', self.get_volume())

    def on_mute_changed(self, playbin, mute_name):
        self.emit('mute-changed', self.get_mute())

GObject.type_register(PlayerBin)

########NEW FILE########
__FILENAME__ = PlayerDBus

# Copyright (C) 2013-2014 LiuLang <gsushzhsosgsu@gmail.com>

# Use of this source code is governed by GPLv3 license that can be found
# in the LICENSE file.

import json
import dbus
import dbus.service
import dbus.mainloop.glib
from dbus.mainloop.glib import DBusGMainLoop
from gi.repository import GObject
from gi.repository import Gst

dbus.mainloop.glib.threads_init()

BUS_NAME = 'org.mpris.MediaPlayer2.kwplayer'
MPRIS_PATH = '/org/mpris/MediaPlayer2'
ROOT_IFACE = 'org.mpris.MediaPlayer2'
PLAYER_IFACE = 'org.mpris.MediaPlayer2.Player'

# TODO:
URI_SCHEMES = ['file', 'http', 'smb']
MIME_TYPES = ['application/ogg', ]


class PlayerDBus(dbus.service.Object):
    '''Implements MPRIS DBus Interface v2.2'''

    properties = None

    def __init__(self, player):
        self.player = player
        self.app = player.app
        loop = DBusGMainLoop(set_as_default=True)
        session_bus = dbus.SessionBus(loop)
        bus_name = dbus.service.BusName(BUS_NAME, bus=session_bus)
        mpris_path = dbus.service.ObjectPath(MPRIS_PATH)
        super().__init__(bus_name=bus_name, object_path=mpris_path)

        self.properties = {
                ROOT_IFACE: self._get_root_iface_properties(),
                PLAYER_IFACE: self._get_player_iface_properties(),
                }

    def _get_root_iface_properties(self):
        return {
            'CanQuit': (True, None),
            'Fullscreen': (False, None),
            'CanSetFullscreen': (False, None),
            'CanRaise': (True, None),
            'HasTrackList': (False, None),
            'Identity': ('KW Player', None),
            'DesktopEntry': ('kwplayer', None),
            'SupportedUriSchemes': 
                (dbus.Array(URI_SCHEMES, signature='s'), None),
            #'SupportedMimeTypes': (dbus.Array([], signature='s'), None),
            'SupportedMimeTypes':
                (dbus.Array(MIME_TYPES, signature='s'), None),
            }

    def _get_player_iface_properties(self):
        return {
            'PlaybackStatus': (self.get_PlaybackStatus, None),
            'LoopStatus': ('None', self.set_LoopStatus),
            'Rate': (1.0, self.set_Rate),
            'Shuffle': (self.get_Shuffle, self.set_Shuffle),
            'Metadata': (self.get_Metadata, None),
            'Volume': (self.get_Volume, self.set_Volume),
            'Position': (self.get_Position, None),
            'MinimumRate': (1.0, None),
            'MaximumRate': (1.0, None),
            'CanGoNext': (True, None),
            'CanGoPrevious': (self.get_CanGoPrevious, None),
            'CanPlay': (self.get_CanPlay, None),
            'CanPause': (True, None),
            'CanSeek': (False, None),
            'CanControl': (True, None),
            }

    # interface properties
    @dbus.service.method(dbus.PROPERTIES_IFACE, in_signature='ss',
                         out_signature='v')
    def Get(self, interface, prop):
        (getter, _) = self.properties[interface][prop]
        if callable(getter):
            return getter()
        else:
            return getter

    @dbus.service.method(dbus.PROPERTIES_IFACE, in_signature='s',
                         out_signature='a{sv}')
    def GetAll(self, interface):
        getters = {}
        for key, (getter, _) in self.properties[interface].items():
            if callable(getter):
                getters[key] = getter()
            else:
                getters[key] = getter
        return getters

    @dbus.service.method(dbus.PROPERTIES_IFACE, in_signature='ssv',
                         out_signature='')
    def Set(self, interface, prop, value):
        _, setter = self.properties[interface][prop]
        if setter:
            setter(value)
            self.PropertiesChanged(
                    interface, {prop: self.Get(interface, prop)}, [])

    @dbus.service.signal(dbus.PROPERTIES_IFACE, signature='sa{sv}as')
    def PropertiesChanged(self, interface, changed_properties,
                          invalidated_properties):
        pass

    # root iface methods
    @dbus.service.method(ROOT_IFACE)
    def Quit(self):
        self.app.quit()

    @dbus.service.method(ROOT_IFACE)
    def Raise(self):
        self.app.window.present()

    # player iface methods
    @dbus.service.method(PLAYER_IFACE)
    def Previous(self):
        self.player.load_prev_cb()

    @dbus.service.method(PLAYER_IFACE)
    def Next(self):
        self.player.load_next_cb()

    @dbus.service.method(PLAYER_IFACE)
    def Pause(self):
        self.player.pause_player_cb()

    @dbus.service.method(PLAYER_IFACE)
    def PlayPause(self):
        self.player.play_pause_cb()

    @dbus.service.method(PLAYER_IFACE)
    def Stop(self):
        self.player.stop_player_cb()

    @dbus.service.method(PLAYER_IFACE)
    def Play(self):
        self.player.start_player_cb()

    @dbus.service.method(PLAYER_IFACE, in_signature='x')
    def Seek(self, offset):
        # Note: offset unit is microsecond, but player.seek() requires
        # nanoseconds as time unit
        self.player.seek_cb(offset*1000)

    @dbus.service.method(PLAYER_IFACE, in_signature='s')
    def OpenUri(self, uri):
        pass
    
    # player iface signals
    @dbus.service.signal(PLAYER_IFACE, signature='x')
    def Seeked(self, offset):
        pass

    @dbus.service.method(PLAYER_IFACE)
    def SetPosition(self, track_id, offset):
        self.Seek()

    # does not have playlists or tracklist

    # player properties
    def get_PlaybackStatus(self):
        if self.player.is_playing():
            return 'Playing'
        return 'Paused'

    def set_LoopStatus(self, value):
        pass

    def set_Rate(self, rate):
        pass

    def get_Shuffle(self):
        return self.player.shuffle_btn.get_active()

    def set_Shuffle(self):
        self.player.shuffle_btn.set_active(True)

    def get_Metadata(self):
        song = self.player.curr_song
        if not song:
            return {'mpris:trackid': ''}

        artUrl = self.player.meta_artUrl

        meta_obj = {
                'xesam:genre': ['', ],
                'xesam:userCount': 1,
                'xesam:trackNumber': 1,
                #'xesam:comment': ['by kwplayer'],
                #'xesam:contentCreated': '2008-01-01T00:00:00Z',
                'xesam:userRating': 0.0,
                #'xesam:lastUsed': '2013-01-01T00:00:00Z',
                'mpris:trackid': '',

                'xesam:title': song['name'],
                'xesam:artist': 
                    dbus.Array(song['artist'].split('&'), signature='s'),
                'xesam:album': song['album'],
                'xesam:url': self.player.meta_url,
                'mpris:length': self.get_Length(),
                'mpris:artUrl': 'file://' + artUrl
                }
        return dbus.Dictionary(meta_obj, signature='sv')


    def get_Volume(self):
        return self.player.get_volume()

    def set_Volume(self, volume):
        self.player.set_volume_cb(volume)

    def get_Position(self):
        pos = self.player.playbin.get_position()[1] // 1000
        return pos

    def get_CanGoPrevious(self):
        return self.player.can_go_previous()

    def get_CanPlay(self):
        # FIXME:
        return True
        state = self.player.playbin.get_status()
        if state in (Gst.State.PLAYING, Gst.State.PAUSED):
            return True
        return False

    def get_CanSeek(self):
        if self.player.scale.get_sensitive():
            return True
        return False

    def update_pos(self, pos):
        self.Seeked(pos)

    def set_Playing(self):
        self.PropertiesChanged(
                PLAYER_IFACE, {'PlaybackStatus': 'Playing'}, [])
        self.update_meta()

    def set_Pause(self):
        self.PropertiesChanged(
                PLAYER_IFACE, {'PlaybackStatus': 'Paused'}, [])

    def get_Length(self):
        length = self.player.adjustment.get_upper()
        mod_len = int(divmod(length, 10**9)[0])
        return mod_len*10**6

    def update_meta(self):
        meta = self.get_Metadata()
        self.PropertiesChanged(PLAYER_IFACE, {'Metadata': meta}, [])

    def enable_seek(self):
        self.PropertiesChanged(PLAYER_IFACE, {'CanSeek': True}, [])

    def disable_seek(self):
        self.PropertiesChanged(PLAYER_IFACE, {'CanSeek': False}, [])

########NEW FILE########
__FILENAME__ = PlayerNotify

# Copyright (C) 2013-2014 LiuLang <gsushzhsosgsu@gmail.com>

# Use of this source code is governed by GPLv3 license that can be found
# in http://www.gnu.org/licenses/gpl-3.0.html


from gi.repository import GLib
from gi.repository import Notify

from kuwo import Config
from kuwo import Widgets

Notify.init('kwplayer')
_ = Config._

class PlayerNotify:
    '''Notification wrapper.

    Popup a control panel on Gdm3 lock screen.'''

    def __init__(self, player):
        self.player = player
        self.notify = Notify.Notification.new('', '', 'kwplayer')

    def refresh(self):
        if not self.player.app.conf['use-notify']:
            return

        notify = self.notify
        song = self.player.curr_song

        notify.clear_hints()
        #notify.set_timeout(4000)

        if song['artist']:
            artist = Widgets.short_tooltip(song['artist'], 20)
        else:
            artist = _('Unknown')
        if song['album']:
            album = Widgets.short_tooltip(song['album'], 30)
        else:
            album = _('Unknown')
        notify.update(
                song['name'],
                'by {0} from {1}'.format(artist, album),
                self.player.meta_artUrl
                )
        notify.set_hint('image-path', GLib.Variant.new_string(
            self.player.meta_artUrl))

        notify.clear_actions()

        try:
            notify.add_action(
                    'media-skip-backward',
                    _('Previous'),
                    self.on_prev_action_activated,
                    None)
            if self.player.is_playing():
                notify.add_action(
                        'media-playback-pause',
                        _('Pause'),
                        self.on_playpause_action_activated,
                        None)
            else:
                notify.add_action(
                        'media-playback-start',
                        _('Play'),
                        self.on_playpause_action_activated,
                        None)
            notify.add_action(
                    'media-skip-forward',
                    _('Next'),
                    self.on_next_action_activated,
                    None)
        except TypeError:
            # For Fedora 19, which needs 6 parameters.
            notify.add_action(
                    'media-skip-backward',
                    _('Previous'),
                    self.on_prev_action_activated,
                    None,
                    None)
            if self.player.is_playing():
                notify.add_action(
                        'media-playback-pause',
                        _('Pause'),
                        self.on_playpause_action_activated,
                        None,
                        None)
            else:
                notify.add_action(
                        'media-playback-start',
                        _('Play'),
                        self.on_playpause_action_activated,
                        None,
                        None)
            notify.add_action(
                    'media-skip-forward',
                    _('Next'),
                    self.on_next_action_activated,
                    None,
                    None)

        notify.set_hint(
                'action-icons', GLib.Variant.new_boolean(True))

        # gnome shell screenlocker will get `x-gnome.music` notification
        # and the whole notification content will be presented
        # from rhythmbox/plugins/rb-notification-plugin.c
        notify.set_category('x-gnome.music')

        # show on lock screen
        hint = 'resident'
        # show on desktop
        #hint = 'transient'
        notify.set_hint(hint, GLib.Variant.new_boolean(True))

        notify.show()

    def on_prev_action_activated(self, *args):
        self.player.load_prev_cb()

    def on_playpause_action_activated(self, *args):
        self.player.play_pause_cb()

    def on_next_action_activated(self, *args):
        self.player.load_next_cb()

########NEW FILE########
__FILENAME__ = PlayList

# Copyright (C) 2013-2014 LiuLang <gsushzhsosgsu@gmail.com>

# Use of this source code is governed by GPLv3 license that can be found
# in the LICENSE file.

import json
import os
import random
import shutil
import time
from gi.repository import Gdk
from gi.repository import GdkPixbuf
from gi.repository import Gio
from gi.repository import GLib
from gi.repository import GObject
from gi.repository import Gtk
from gi.repository import Notify

from kuwo import Config
from kuwo import Net
from kuwo import Utils
from kuwo import Widgets

_ = Config._

DRAG_TARGETS = [
        ('text/plain', Gtk.TargetFlags.SAME_APP, 0),
        ('TEXT', Gtk.TargetFlags.SAME_APP, 1),
        ('STRING', Gtk.TargetFlags.SAME_APP, 2),
        ]
DRAG_ACTIONS = Gdk.DragAction.MOVE

class TreeViewColumnText(Widgets.TreeViewColumnText):
    def __init__(self, *args, **kwds):
        super().__init__(*args, **kwds)
        self.props.clickable = True
        self.props.reorderable = True
        self.props.sort_indicator = True
        self.props.sort_column_id = kwds['text']

class NormalSongTab(Gtk.ScrolledWindow):
    def __init__(self, app, list_name):
        super().__init__()
        self.app = app
        self.list_name = list_name

        # name, artist, album, rid, artistid, albumid
        self.liststore = Gtk.ListStore(str, str, str, int, int, int)

        self.treeview = Gtk.TreeView(model=self.liststore)
        self.selection = self.treeview.get_selection()
        self.treeview.set_search_column(0)
        self.treeview.props.headers_clickable = True
        self.treeview.props.headers_visible = True
        self.treeview.props.reorderable = True
        self.treeview.props.rules_hint = True
        self.treeview.get_selection().set_mode(Gtk.SelectionMode.MULTIPLE)
        self.treeview.enable_model_drag_source(
                Gdk.ModifierType.BUTTON1_MASK,
                DRAG_TARGETS,
                DRAG_ACTIONS)
        self.treeview.connect('drag-data-get', self.on_drag_data_get)
        self.treeview.enable_model_drag_dest(
                DRAG_TARGETS, DRAG_ACTIONS)
        self.treeview.connect(
                'drag-data-received', self.on_drag_data_received)
        self.treeview.connect(
                'row_activated', self.on_treeview_row_activated)
        self.add(self.treeview)

        song_cell = Gtk.CellRendererText()
        song_col = TreeViewColumnText(_('Title'), song_cell, text=0)
        self.treeview.append_column(song_col)

        artist_cell = Gtk.CellRendererText()
        artist_col = TreeViewColumnText(_('Aritst'), artist_cell, text=1)
        self.treeview.append_column(artist_col)

        album_cell = Gtk.CellRendererText()
        album_col = TreeViewColumnText(_('Album'), album_cell, text=2)
        self.treeview.append_column(album_col)

        delete_cell = Gtk.CellRendererPixbuf(
                icon_name='user-trash-symbolic')
        self.delete_col = Widgets.TreeViewColumnIcon(
                _('Delete'), delete_cell)
        self.treeview.append_column(self.delete_col)
        self.treeview.connect(
                'key-press-event', self.on_treeview_key_pressed)
        self.treeview.connect(
                'button-release-event', self.on_treeview_button_released)
        
    def on_treeview_key_pressed(self, treeview, event):
        if event.keyval == Gdk.KEY_Delete:
            model, paths = self.selection.get_selected_rows()
            # paths needs to be reversed, or else an IndexError throwed.
            for path in reversed(paths):
                model.remove(model[path].iter)

    def on_treeview_button_released(self, treeview, event):
        path_info = treeview.get_path_at_pos(event.x, event.y)
        if not path_info:
            return
        path, column, cell_x, cell_y = path_info
        if column != self.delete_col:
            return
        self.liststore.remove(self.liststore.get_iter(path))

    def on_treeview_row_activated(self, treeview, path, column):
        model = treeview.get_model()
        index = treeview.get_columns().index(column)
        song = Widgets.song_row_to_dict(model[path], start=0)
        if index == 0:
            self.app.playlist.play_song(song, list_name=self.list_name)
        elif index == 1:
            self.app.search.search_artist(song['artist'])
        elif index == 2:
            self.app.search.search_album(song['album'])

    def on_drag_data_get(self, treeview, drag_context, sel_data, info, 
                         time):
        selection = treeview.get_selection()
        model, paths = selection.get_selected_rows()
        self.drag_data_old_iters = []
        songs = []
        for path in paths:
            song = [i for i in model[path]]
            songs.append(song)
            _iter = model.get_iter(path)
            self.drag_data_old_iters.append(_iter)
        sel_data.set_text(json.dumps(songs), -1)

    def on_drag_data_received(self, treeview, drag_context, x, y, sel_data,
                              info, event_time):
        model = treeview.get_model()
        data = sel_data.get_text()
        if not data:
            return
        drop_info = treeview.get_dest_row_at_pos(x, y)
        if not drop_info:
            return
        path = drop_info[0]
        pos = int(str(path))
        songs = json.loads(data)
        for song in songs:
            model.insert(pos, song)
        for _iter in self.drag_data_old_iters:
            model.remove(_iter)


class ExportDialog(Gtk.Dialog):

    def __init__(self, parent, liststore):
        super().__init__(
                _('Export Songs'), parent.app.window, Gtk.DialogFlags.MODAL,
                (Gtk.STOCK_CLOSE, Gtk.ResponseType.OK,))
        self.parent = parent
        self.liststore = liststore
        self.app = parent.app

        self.set_border_width(15)

        box = self.get_content_area()
        box.set_size_request(540, 260)
        box.set_spacing = 5

        folder_label = Widgets.BoldLabel(_('Choose export folder:'))
        box.pack_start(folder_label, False, True, 2)

        self.folder_chooser = Widgets.FolderChooser(self.app.window)
        self.folder_chooser.props.margin_left = 20
        box.pack_start(self.folder_chooser, False, True, 0)

        self.with_lrc = Gtk.CheckButton(_('With lyrics'))
        self.with_lrc.set_tooltip_text(_('Export lyrics to the same folder'))
        self.with_lrc.props.margin_top = 20
        box.pack_start(self.with_lrc, False, False, 0)

        export_box = Gtk.Box(spacing=5)
        export_box.props.margin_top = 20
        box.pack_start(export_box, False, True, 0)

        self.export_prog = Gtk.ProgressBar()
        self.export_prog.props.show_text = True
        self.export_prog.props.text = ''
        export_box.pack_start(self.export_prog, True, True, 0)

        export_btn = Gtk.Button(_('Export'))
        export_btn.connect('clicked', self.do_export)
        export_box.pack_start(export_btn, False, False, 0)

        infobar = Gtk.InfoBar()
        infobar.props.margin_top = 20
        box.pack_start(infobar, False, True, 0)
        info_content = infobar.get_content_area()
        info_label = Gtk.Label(_('Only cached songs will be exported'))
        info_content.pack_start(info_label, False, False, 0)
        box.show_all()

    def do_export(self, button):
        num_songs = len(self.liststore)
        export_dir = self.folder_chooser.get_filename()
        export_lrc = self.with_lrc.get_active()
        for i, item in enumerate(self.liststore):
            song = Widgets.song_row_to_dict(item, start=0)
            cached, song_link, song_path = Net.get_song_link(
                    song, self.app.conf)
            if not cached:
                continue
            self.export_prog.set_fraction(i / num_songs)
            self.export_prog.set_text(song['name'])
            shutil.copy(song_path, export_dir)

            if export_lrc:
                lrc_path, lrc_cached = Net.get_lrc_path(song)
                if lrc_cached:
                    shutil.copy(lrc_path, export_dir)
            Gdk.Window.process_all_updates()
        self.destroy()


class PlayList(Gtk.Box):
    '''Playlist tab in notebook.'''

    title = _('PlayList')

    def __init__(self, app):
        super().__init__()

        self.app = app
        self.tabs = {}
        # self.lists_name contains playlists name
        self.lists_name = []
        # use curr_playing to locate song in treeview
        self.curr_playing = [None, None]

        # control cache job
        self.cache_enabled = False
        self.cache_job = None

        self.playlist_menu = Gtk.Menu()
        self.playlist_advice_disname = ''

        box_left = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.pack_start(box_left, False, False, 0)

        win_left = Gtk.ScrolledWindow()
        box_left.pack_start(win_left, True, True, 0)

        # disname, name/uuid, deletable/editable, tooltip(escaped disname)
        self.liststore_left = Gtk.ListStore(str, str, bool, str)
        self.treeview_left = Gtk.TreeView(model=self.liststore_left)
        self.treeview_left.set_headers_visible(False)
        self.treeview_left.set_tooltip_column(3)
        list_disname = Gtk.CellRendererText()
        list_disname.connect('edited', self.on_list_disname_edited)
        col_name = Gtk.TreeViewColumn(
                'List Name', list_disname, text=0, editable=2)
        self.treeview_left.append_column(col_name)
        #col_name.props.max_width = 75
        #col_name.props.fixed_width = 75
        #col_name.props.min_width = 70
        col_name.props.sizing = Gtk.TreeViewColumnSizing.FIXED
        tree_sel = self.treeview_left.get_selection()
        tree_sel.connect('changed', self.on_tree_selection_left_changed)
        self.treeview_left.enable_model_drag_dest(
                DRAG_TARGETS, DRAG_ACTIONS)
        self.treeview_left.connect(
                'drag-data-received',
                self.on_treeview_left_drag_data_received)
        win_left.add(self.treeview_left)

        toolbar = Gtk.Toolbar()
        toolbar.get_style_context().add_class(
                Gtk.STYLE_CLASS_INLINE_TOOLBAR)
        toolbar.props.show_arrow = False
        toolbar.props.toolbar_style = Gtk.ToolbarStyle.ICONS
        toolbar.props.icon_size = 1
        add_btn = Gtk.ToolButton()
        add_btn.set_name('Add')
        add_btn.set_tooltip_text(_('Add a new playlist'))
        add_btn.set_icon_name('list-add-symbolic')
        add_btn.connect('clicked', self.on_add_playlist_button_clicked)
        toolbar.insert(add_btn, 0)
        remove_btn = Gtk.ToolButton()
        remove_btn.set_name('Remove')
        remove_btn.set_tooltip_text(_('Remove selected playlist'))
        remove_btn.set_icon_name('list-remove-symbolic')
        remove_btn.connect(
                'clicked', self.on_remove_playlist_button_clicked)
        toolbar.insert(remove_btn, 1)
        export_btn = Gtk.ToolButton()
        export_btn.set_name('Export')
        export_btn.set_tooltip_text(_('Export songs in selected playlist'))
        export_btn.set_icon_name('media-eject-symbolic')
        export_btn.connect(
                'clicked', self.on_export_playlist_button_clicked)
        toolbar.insert(export_btn, 2)
        box_left.pack_start(toolbar, False, False, 0)

        self.notebook = Gtk.Notebook()
        self.notebook.props.show_tabs = False
        self.pack_start(self.notebook, True, True, 0)

        # Use this trick to accelerate startup speed of app.
        GLib.timeout_add(1000, self.init_ui)

    def do_destroy(self):
        self.dump_playlists()
        if self.cache_job:
            self.cache_job.destroy()

    def first(self):
        selection = self.treeview_left.get_selection()
        selection.select_path(Gtk.TreePath(1))

    def init_ui(self):
        self.load_playlists()
        # dump playlists to dist every 5 minites
        GLib.timeout_add(300000, self.dump_playlists)
        if self.app.conf['show-pls']:
            self.app.popup_page(self.app_page)
        return False

    def dump_playlists(self):
        filepath = Config.PLS_JSON
        names = [list(p[:-1]) for p in self.liststore_left]
        # There must be at least 3 playlists.
        if len(names) < 3:
            return True
        playlists = {'_names_': names}
        for name in names:
            list_name = name[1]
            liststore = self.tabs[list_name].liststore
            playlists[list_name] = [list(p) for p in liststore]
        with open(filepath, 'w') as fh:
            fh.write(json.dumps(playlists))
        return True

    def load_playlists(self):
        filepath = Config.PLS_JSON
        _default = {
                '_names_': [
                    [_('Caching'), 'Caching', False],
                    [_('Default'), 'Default', False],
                    [_('Favorite'), 'Favorite', False],
                    ],
                'Caching': [],
                'Default': [],
                'Favorite': [],
                }
        if os.path.exists(filepath):
            with open(filepath) as fh:
                playlists = json.loads(fh.read())
        else:
            playlists = _default

        for playlist in playlists['_names_']:
            disname, list_name, editable = playlist
            tooltip = Widgets.escape(disname)
            self.liststore_left.append(
                    [disname, list_name, editable, tooltip])
            songs = playlists[list_name]
            self.init_tab(list_name, songs)

    def init_tab(self, list_name, songs):
        scrolled_win = NormalSongTab(self.app, list_name)
        for song in songs:
            scrolled_win.liststore.append(song)
        if list_name == 'Caching':
            box_caching = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)

            buttonbox = Gtk.Box(spacing=5)
            box_caching.pack_start(buttonbox, False, False, 0)
            button_start = Gtk.Button(_('Start Cache Service'))
            button_start.connect('clicked', self.switch_caching_daemon)
            self.button_start = button_start
            buttonbox.pack_start(button_start, False, False, 0)
            button_open = Gtk.Button(_('Open Cache Folder'))
            button_open.connect('clicked', self.open_cache_folder)
            buttonbox.pack_start(button_open, False, False, 0)

            box_caching.pack_start(scrolled_win, True, True, 0)
            self.notebook.append_page(box_caching, Gtk.Label(_('Caching')))
            box_caching.show_all()
        else:
            self.notebook.append_page(scrolled_win, Gtk.Label(list_name))
            scrolled_win.show_all()
        self.tabs[list_name] = scrolled_win

    # Side Panel
    def on_tree_selection_left_changed(self, tree_sel):
        model, tree_iter = tree_sel.get_selected()
        path = model.get_path(tree_iter)
        if path is None:
            return
        index = path.get_indices()[0]
        self.notebook.set_current_page(index)

    def on_treeview_left_drag_data_received(self, treeview, drag_context,
                                            x, y, sel_data, info,
                                            event_time):
        model = treeview.get_model()
        data = sel_data.get_text()
        if not data:
            return
        drop_info = treeview.get_dest_row_at_pos(x, y)
        if not drop_info:
            return
        path = drop_info[0]
        songs = json.loads(data)
        list_name = model[path][1]
        liststore = self.tabs[list_name].liststore
        for song in songs:
            liststore.append(song)

    # Open API for others to call.
    def play_song(self, song, list_name='Default', use_mv=False):
        if not song:
            return
        if not list_name:
            list_name = 'Default'
        liststore = self.tabs[list_name].liststore
        rid = song['rid']
        path = self.get_song_path_in_liststore(liststore, rid)
        if path > -1:
            # curr_playing contains: listname, path
            self.curr_playing = [list_name, path]
            song = Widgets.song_row_to_dict(liststore[path], start=0)
        else:
            liststore.append(Widgets.song_dict_to_row(song))
            self.curr_playing = [list_name, len(liststore)-1, ]
            self.locate_curr_song(popup_page=False)
        if use_mv is True:
            self.app.player.load_mv(song)
        else:
            self.app.player.load(song)

    def play_songs(self, songs):
        if not songs or songs:
            return
        self.add_songs_to_playlist(songs, list_name='Default')
        self.play_song(songs[0])

    def add_song_to_playlist(self, song, list_name='Default'):
        liststore = self.tabs[list_name].liststore
        if self.check_song_in_playlist(song, list_name):
            return
        liststore.append(Widgets.song_dict_to_row(song))

    def remove_song_from_playlist(self, song, list_name):
        liststore = self.tabs[list_name].liststore
        rid = song['rid']
        path = self.get_song_path_in_liststore(liststore, rid)
        if path == -1:
            return
        liststore.remove(liststore[path].iter)

    def check_song_in_playlist(self, song, list_name):
        '''Check whether this song is in this playlist'''
        liststore = self.tabs[list_name].liststore
        rid = song['rid']
        path = self.get_song_path_in_liststore(liststore, rid)
        if path > -1:
            return True
        else:
            return False

    def add_songs_to_playlist(self, songs, list_name='Default'):
        def start():
            tree.freeze_child_notify()
            for song in songs:
                rid = song['rid']
                path = self.get_song_path_in_liststore(liststore, rid)
                if path > -1:
                    continue
                liststore.append(Widgets.song_dict_to_row(song))

        def stop(*args):
            tree.thaw_child_notify()
            Gdk.Window.process_all_updates()

        liststore = self.tabs[list_name].liststore
        tree = self.tabs[list_name].treeview
        Net.async_call(start, stop)

    # Open API
    def cache_song(self, song):
        rid = song['rid']
        liststore = self.tabs['Caching'].liststore
        liststore.append(Widgets.song_dict_to_row(song))
        if not self.cache_enabled:
            self.switch_caching_daemon()

    # Open API
    def cache_songs(self, songs):
        for song in songs:
            self.cache_song(song)

    def open_cache_folder(self, btn):
        Utils.open_folder(self.app.conf['song-dir'])

    # song cache daemon
    def switch_caching_daemon(self, *args):
        if not self.cache_enabled:
            self.cache_enabled = True
            self.button_start.set_label(_('Stop Cache Service'))
            self.do_cache_song_pool()
        else:
            self.cache_enabled = False
            self.button_start.set_label(_('Start Cache Service'))

    def do_cache_song_pool(self):
        def _move_song():
            try:
                liststore.remove(liststore[path].iter)
            except IndexError:
                pass
            Gdk.Window.process_all_updates()

        def _on_disk_error(widget, song_path, eror=None):
            self.cache_enabled = False
            GLib.idle_add(
                    Widgets.filesystem_error,
                    self.app.window,
                    song_path)

        def _on_network_error(widget, song_link, error=None):
            self.cache_enabled = False
            GLib.idle_add(
                    Widgets.network_error,
                    self.app.window,
                    _('Failed to cache song'))

        def _on_downloaded(widget, song_path, error=None):
            if song_path:
                GLib.idle_add(_move_song)
            if self.cache_enabled:
                GLib.idle_add(self.do_cache_song_pool)

        if not self.cache_enabled:
            return

        list_name = 'Caching'
        liststore = self.tabs[list_name].liststore
        path = 0
        if len(liststore) == 0:
            print('Caching playlist is empty, please add some songs')
            self.switch_caching_daemon()
            Notify.init('kwplayer-cache')
            notify = Notify.Notification.new(
                    'Kwplayer',
                    _('All songs in caching list have been downloaded.'),
                    'kwplayer')
            notify.show()
            return
        song = Widgets.song_row_to_dict(liststore[path], start=0)
        print('will download:', song)
        self.cache_job = Net.AsyncSong(self.app)
        self.cache_job.connect('downloaded', _on_downloaded)
        self.cache_job.connect('disk-error', _on_disk_error)
        self.cache_job.connect('network-error', _on_network_error)
        self.cache_job.get_song(song)

    # Others
    def on_song_downloaded(self, play=False):
        list_name = self.curr_playing[0]
        liststore = self.tabs[list_name].liststore
        path = self.curr_playing[1]
        song = Widgets.song_row_to_dict(liststore[path], start=0)
        Gdk.Window.process_all_updates()

    def get_prev_song(self, repeat):
        list_name = self.curr_playing[0]
        if not list_name:
            return None
        liststore = self.tabs[list_name].liststore
        path = self.curr_playing[1]
        song_nums = len(liststore)
        if song_nums == 0:
            return None
        if path == 0:
            if repeat:
                path = song_nums - 1
            else:
                path = 0
        else:
            path = path - 1
        self.prev_playing = path
        return Widgets.song_row_to_dict(liststore[path], start=0)

    def get_next_song(self, repeat, shuffle):
        list_name = self.curr_playing[0]
        liststore = self.tabs[list_name].liststore
        path = self.curr_playing[1]
        song_nums = len(liststore)
        if song_nums == 0:
            return None
        if shuffle:
            path = random.randint(0, song_nums-1)
        elif path == song_nums - 1:
            if not repeat:
                return None
            path = 0
        else:
            path = path + 1

        self.next_playing = path
        return Widgets.song_row_to_dict(liststore[path], start=0)

    def play_prev_song(self, repeat, use_mv=False):
        prev_song = self.get_prev_song(repeat)
        if not prev_song:
            return
        self.curr_playing[1] = self.prev_playing
        self.locate_curr_song(popup_page=False)
        if use_mv:
            self.app.player.load_mv(prev_song)
        else:
            self.app.player.load(prev_song)

    def play_next_song(self, repeat, shuffle, use_mv=False):
        next_song = self.get_next_song(repeat, shuffle)
        if not next_song:
            return
        self.curr_playing[1] = self.next_playing
        self.locate_curr_song(popup_page=False)
        if use_mv:
            self.app.player.load_mv(next_song)
        else:
            self.app.player.load(next_song)

    def locate_curr_song(self, popup_page=True):
        '''switch current playlist and select curr_song.'''
        list_name = self.curr_playing[0]
        if not list_name:
            return
        treeview = self.tabs[list_name].treeview
        liststore = treeview.get_model()
        path = self.curr_playing[1]
        treeview.set_cursor(path)

        for left_path, item in enumerate(self.liststore_left):
            if list_name == self.liststore_left[left_path][1]:
                selection_left = self.treeview_left.get_selection()
                selection_left.select_path(left_path)
                break
        if popup_page:
            self.app.popup_page(self.app_page)

    def get_song_path_in_liststore(self, liststore, rid, pos=3):
        for i, row in enumerate(liststore):
            if row[pos] == rid:
                return i
        return -1


    # left panel
    def on_list_disname_edited(self, cell, path, new_name):
        if not new_name:
            return
        old_name = self.liststore_left[path][0]
        self.liststore_left[path][0] = new_name

    def on_add_playlist_button_clicked(self, button):
        list_name = str(time.time())
        disname = _('Playlist')
        editable = True
        tooltip = Widgets.escape(disname)
        _iter = self.liststore_left.append(
                [disname, list_name, editable, tooltip])
        selection = self.treeview_left.get_selection()
        selection.select_iter(_iter)
        self.init_tab(list_name, [])

    def on_remove_playlist_button_clicked(self, button):
        selection = self.treeview_left.get_selection()
        model, _iter = selection.get_selected()
        if not _iter:
            return
        path = model.get_path(_iter)
        index = path.get_indices()[0]
        disname, list_name, editable, tooltip = model[path]
        if not editable:
            return
        self.notebook.remove_page(index)
        model.remove(_iter)

    def on_export_playlist_button_clicked(self, button):
        selection = self.treeview_left.get_selection()
        model, _iter = selection.get_selected()
        if not _iter:
            return
        path = model.get_path(_iter)
        index = path.get_indices()[0]
        disname, list_name, editable, tooltip = model[path]
        liststore = self.tabs[list_name].liststore

        export_dialog = ExportDialog(self, liststore)
        export_dialog.run()
        export_dialog.destroy()

    def advise_new_playlist_name(self, disname):
        self.playlist_advice_disname = disname

    def on_advice_menu_item_activated(self, advice_item):
        list_name = str(time.time())
        tooltip = Widgets.escape(self.playlist_advice_disname)
        self.liststore_left.append(
                [self.playlist_advice_disname, list_name, True, tooltip])
        self.init_tab(list_name, [])
        advice_item.list_name = list_name
        self.on_menu_item_activated(advice_item)

    def on_menu_item_activated(self, menu_item):
        list_name = menu_item.list_name
        songs = menu_item.get_parent().songs
        self.add_songs_to_playlist(songs, list_name)

    def popup_playlist_menu(self, button, songs):
        menu = self.playlist_menu
        while menu.get_children():
            menu.remove(menu.get_children()[0])

        for item in self.liststore_left:
            if item[1] in ('Caching', ):
                continue
            menu_item = Gtk.MenuItem(item[0])
            menu_item.list_name = item[1]
            menu_item.connect('activate', self.on_menu_item_activated)
            menu.append(menu_item)

        if self.playlist_advice_disname:
            sep_item = Gtk.SeparatorMenuItem()
            menu.append(sep_item)
            advice_item = Gtk.MenuItem('+ ' + self.playlist_advice_disname)
            advice_item.connect(
                    'activate', self.on_advice_menu_item_activated)
            advice_item.set_tooltip_text(
                    _('Create this playlist and add songs into it'))
            menu.append(advice_item)

        menu.songs = songs
        menu.show_all()
        menu.popup(None, None, None, None, 1, Gtk.get_current_event_time())

########NEW FILE########
__FILENAME__ = Preferences

# Copyright (C) 2013-2014 LiuLang <gsushzhsosgsu@gmail.com>

# Use of this source code is governed by GPLv3 license that can be found
# in the LICENSE file.

import os
import shutil
from gi.repository import Gdk
from gi.repository import GLib
from gi.repository import Gtk
from gi.repository import Pango

from kuwo import Config
from kuwo import Widgets

_ = Config._

MARGIN_LEFT = 15
MARGIN_TOP = 20
ShortcutMode = Config.ShortcutMode

DISNAME_COL, NAME_COL, KEY_COL, MOD_COL = list(range(4))

class NoteTab(Gtk.Box):
    def __init__(self):
        super().__init__(orientation=Gtk.Orientation.VERTICAL)
        self.set_border_width(10)

class ColorButton(Gtk.ColorButton):
    def __init__(self, color):
        super().__init__()

class ColorBox(Gtk.Box):
    def __init__(self, label, conf, color_name, use_margin=False):
        super().__init__()
        self.conf = conf
        self.color_name = color_name
        left_label = Gtk.Label(label)
        self.pack_start(left_label, False, True, 0)

        color_button = Gtk.ColorButton()
        color_button.set_use_alpha(True)
        color_rgba = Gdk.RGBA()
        color_rgba.parse(conf[color_name])
        color_button.set_rgba(color_rgba)
        color_button.connect('color-set', self.on_color_set)
        self.pack_end(color_button, False, True, 0)

        if use_margin:
            self.props.margin_left = 20

    def on_color_set(self, color_button):
        color_rgba = color_button.get_rgba()
        if color_rgba.alpha == 1:
            color_rgba.alpha = 0.999
        self.conf[self.color_name] = color_rgba.to_string()

class FontBox(Gtk.Box):
    def __init__(self, label, conf, font_name, use_margin=True):
        super().__init__()
        self.conf = conf
        self.font_name = font_name
        left_label = Gtk.Label(label)
        self.pack_start(left_label, False, True, 0)

        font_button = Gtk.SpinButton()
        adjustment = Gtk.Adjustment(conf[font_name], 4, 72, 1, 10)
        adjustment.connect('value-changed', self.on_font_set)
        font_button.set_adjustment(adjustment)
        font_button.set_value(conf[font_name])
        self.pack_end(font_button, False, True, 0)

        if use_margin:
            self.props.margin_left = 20

    def on_font_set(self, adjustment):
        self.conf[self.font_name] = adjustment.get_value()


class ChooseFolder(Gtk.Box):
    def __init__(self, parent, conf_name, toggle_label):
        super().__init__(orientation=Gtk.Orientation.VERTICAL)
        self.props.margin_left = MARGIN_LEFT
        self.props.margin_top = 5
        self.parent = parent
        self.app = parent.app
        self.conf_name = conf_name
        self.old_dir = self.app.conf[conf_name]

        hbox = Gtk.Box(spacing=5)
        self.pack_start(hbox, False, True, 0)

        self.dir_entry = Gtk.Entry()
        self.dir_entry.set_text(self.old_dir)
        self.dir_entry.props.editable = False
        self.dir_entry.props.can_focus = False
        self.dir_entry.props.width_chars = 20
        hbox.pack_start(self.dir_entry, True, True, 0)

        choose_button = Gtk.Button('...')
        choose_button.connect('clicked', self.on_choose_button_clicked)
        hbox.pack_start(choose_button, False, False, 0)

    def on_choose_button_clicked(self, button):
        def on_dialog_file_activated(dialog):
            new_dir = dialog.get_filename()
            dialog.destroy()
            self.dir_entry.set_text(new_dir)
            if new_dir != self.app.conf[self.conf_name]:
                self.app.conf[self.conf_name] = new_dir
            return

        dialog = Gtk.FileChooserDialog(
                _('Choose a Folder'), self.parent,
                Gtk.FileChooserAction.SELECT_FOLDER,
                (Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
                 Gtk.STOCK_OK, Gtk.ResponseType.OK))

        dialog.connect('file-activated', on_dialog_file_activated)
        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            on_dialog_file_activated(dialog)
            return
        dialog.destroy()


class Preferences(Gtk.Dialog):
    def __init__(self, app):
        self.app = app
        super().__init__(
                _('Preferences'), app.window, 0,
                (Gtk.STOCK_CLOSE, Gtk.ResponseType.CLOSE,))
        self.set_modal(True)
        self.set_transient_for(app.window)
        self.set_default_size(600, 320)
        self.set_border_width(5)
        box = self.get_content_area()
        #box.props.margin_left = MARGIN_LEFT

        notebook = Gtk.Notebook()
        box.pack_start(notebook, True, True, 0)

        # generic tab
        generic_box = NoteTab()
        notebook.append_page(generic_box, Gtk.Label(_('Generic')))

        status_button = Gtk.CheckButton(_('Close to system tray'))
        status_button.set_active(app.conf['use-status-icon'])
        status_button.connect('toggled', self.on_status_button_toggled)
        generic_box.pack_start(status_button, False, False, 0)

        notify_button = Gtk.CheckButton(_('Show kwplayer on lock screen'))
        notify_button.set_tooltip_text(
            _('Only works with gdm3/gnome3.8+\n') + 
            _('Please disable it on other desktop environments (like KDE)'))
        notify_button.set_active(app.conf['use-notify'])
        notify_button.connect('toggled', self.on_notify_button_toggled)
        generic_box.pack_start(notify_button, False, False, 0)

        show_pls_button = Gtk.CheckButton(_('Show playlist tab on startup'))
        show_pls_button.set_active(app.conf['show-pls'])
        show_pls_button.connect('toggled', self.on_show_pls_button_toggled)
        generic_box.pack_start(show_pls_button, False, False, 0)

        dark_theme_button = Gtk.CheckButton(_('Use dark theme'))
        dark_theme_button.set_active(app.conf['use-dark-theme'])
        dark_theme_button.connect(
                'toggled', self.on_dark_theme_button_toggled)
        generic_box.pack_start(dark_theme_button, False, False, 0)

        # format tab
        format_box = NoteTab()
        notebook.append_page(format_box, Gtk.Label(_('Format')))

        audio_label = Widgets.BoldLabel(_('Prefered Audio Format'))
        format_box.pack_start(audio_label, False, False, 0)
        radio_mp3 = Gtk.RadioButton(_('MP3 (faster)'))
        radio_mp3.props.margin_left = MARGIN_LEFT
        radio_mp3.connect('toggled', self.on_audio_toggled)
        format_box.pack_start(radio_mp3, False, False, 0)
        radio_ape = Gtk.RadioButton(_('APE (better)'))
        radio_ape.join_group(radio_mp3)
        radio_ape.props.margin_left = MARGIN_LEFT
        radio_ape.set_active(app.conf['use-ape'])
        radio_ape.connect('toggled', self.on_audio_toggled)
        format_box.pack_start(radio_ape, False, False, 0)

        video_label = Widgets.BoldLabel(_('Prefered Video Format'))
        video_label.props.margin_top = MARGIN_TOP
        format_box.pack_start(video_label, False, False, 0)
        radio_mp4 = Gtk.RadioButton(_('MP4 (faster)'))
        radio_mp4.props.margin_left = MARGIN_LEFT
        radio_mp4.connect('toggled', self.on_video_toggled)
        format_box.pack_start(radio_mp4, False, False, 0)
        radio_mkv = Gtk.RadioButton(_('MKV (better)'))
        radio_mkv.props.margin_left = MARGIN_LEFT
        radio_mkv.join_group(radio_mp4)
        radio_mkv.set_active(app.conf['use-mkv'])
        radio_mkv.connect('toggled', self.on_video_toggled)
        radio_mkv.set_tooltip_text(
                _( 'Please use this format when using Karaoke'))
        format_box.pack_start(radio_mkv, False, False, 0)

        # lyrics tab
        lrc_box = NoteTab()
        notebook.append_page(lrc_box, Gtk.Label(_('Lyrics')))

        lrc_normal_text_label = Widgets.BoldLabel(_('Normal Text'))
        lrc_box.pack_start(lrc_normal_text_label, False, True, 0)

        lrc_normal_text_size = FontBox(
                _('text size'), app.conf, 'lrc-text-size', use_margin=True)
        lrc_box.pack_start(lrc_normal_text_size, False, True, 0)

        lrc_normal_text_color = ColorBox(
                _('text color'), app.conf, 'lrc-text-color', use_margin=True)
        lrc_box.pack_start(lrc_normal_text_color, False, True, 0)
        lrc_normal_text_color.props.margin_bottom = 10

        lrc_highlighted_text_label = Widgets.BoldLabel(
                _('Highlighted Text'))
        lrc_box.pack_start(lrc_highlighted_text_label, False, True, 0)

        lrc_highlighted_text_size = FontBox(
                _('text size'), app.conf, 'lrc-highlighted-text-size',
                use_margin=True)
        lrc_box.pack_start(lrc_highlighted_text_size, False, True, 0)

        lrc_highlighted_text_color = ColorBox(
                _('text color'), app.conf, 'lrc-highlighted-text-color',
                use_margin=True)
        lrc_highlighted_text_color.props.margin_bottom = 10
        lrc_box.pack_start(lrc_highlighted_text_color, False, True, 0)

        lrc_word_back_color = ColorBox(
                _('Lyrics Text Background color'), app.conf, 'lrc-back-color')
        lrc_box.pack_start(lrc_word_back_color, False, True, 0)

        # folders tab
        folder_box = NoteTab()
        notebook.append_page(folder_box, Gtk.Label(_('Folders')))

        song_folder_label = Widgets.BoldLabel(_('Place to store sogns'))
        folder_box.pack_start(song_folder_label, False, False, 0)
        song_folder = ChooseFolder(
                self, 'song-dir', _('Moving cached songs to new folder'))
        folder_box.pack_start(song_folder, False, False, 0)

        mv_folder_label = Widgets.BoldLabel(_('Place to store MVs'))
        mv_folder_label.props.margin_top = MARGIN_TOP
        folder_box.pack_start(mv_folder_label, False, False, 0)
        mv_folder = ChooseFolder(
                self, 'mv-dir', _('Moving cached MVs to new folder'))
        folder_box.pack_start(mv_folder, False, False, 0)

        self.notebook = notebook

        # shortcut tab
        self.init_shortcut_tab()

    def init_shortcut_tab(self):
        curr_mode = self.app.conf['shortcut-mode']

        box = NoteTab()
        self.notebook.append_page(box, Gtk.Label(_('Shortcut')))

        self.shortcut_win = Gtk.ScrolledWindow()

        disable_btn = Gtk.RadioButton(_('Disable Keyboard Shortcut'))
        disable_btn.connect(
                'toggled', self.on_shortcut_btn_toggled, ShortcutMode.NONE)
        disable_btn.set_active(curr_mode == ShortcutMode.NONE)
        box.pack_start(disable_btn, False, False, 0)

        default_btn = Gtk.RadioButton(_('Use Default MultiMedia Key'))
        default_btn.connect(
                'toggled', self.on_shortcut_btn_toggled,
                ShortcutMode.DEFAULT)
        default_btn.join_group(disable_btn)
        default_btn.set_active(curr_mode == ShortcutMode.DEFAULT)
        box.pack_start(default_btn, False, False, 0)

        custom_btn = Gtk.RadioButton(_('Use Custom Keyboard Shortcut'))
        custom_btn.connect(
                'toggled', self.on_shortcut_btn_toggled,
                ShortcutMode.CUSTOM)
        custom_btn.join_group(default_btn)
        custom_btn.set_active(curr_mode == ShortcutMode.CUSTOM)
        box.pack_start(custom_btn, False, False, 0)

        self.shortcut_win.props.margin_left = 10
        self.shortcut_win.set_sensitive(curr_mode == ShortcutMode.CUSTOM)
        box.pack_start(self.shortcut_win, True, True, 0)

        # disname, name, shortct key, shortcut modifiers
        self.shortcut_liststore = Gtk.ListStore(str, str, int, int)
        tv = Gtk.TreeView(model=self.shortcut_liststore)
        self.shortcut_win.add(tv)

        name_cell = Gtk.CellRendererText()
        name_col = Gtk.TreeViewColumn('Action', name_cell, text=DISNAME_COL)
        tv.append_column(name_col)

        key_cell = Gtk.CellRendererAccel(editable=True)
        key_cell.connect('accel-edited', self.on_shortcut_key_cell_edited)
        key_col = Gtk.TreeViewColumn(
                'Shortcut Key', key_cell,
                accel_key=KEY_COL, accel_mods=MOD_COL)
        tv.append_column(key_col)
        
        for name in self.app.conf['custom-shortcut']:
            key = self.app.conf['custom-shortcut'][name]
            i18n_name = Config.SHORT_CUT_I18N[name]
            k, m = Gtk.accelerator_parse(key)
            self.shortcut_liststore.append([i18n_name, name, k, m])

    def run(self):
        self.get_content_area().show_all()
        super().run()

    def on_destroy(self):
        print('dialog.on_destroy()')
        Config.dump_conf(self.app.conf)

    # generic tab signal handlers
    def on_status_button_toggled(self, button):
        self.app.conf['use-status-icon'] = button.get_active()

    def on_notify_button_toggled(self, button):
        self.app.conf['use-notify'] = button.get_active()

    def on_show_pls_button_toggled(self, button):
        self.app.conf['show-pls'] = button.get_active()

    def on_dark_theme_button_toggled(self, button):
        self.app.conf['use-dark-theme'] = button.get_active()

    # format tab signal handlers
    def on_audio_toggled(self, radiobtn):
        self.app.conf['use-ape'] = radiobtn.get_group()[0].get_active()

    def on_video_toggled(self, radiobtn):
        # radio_group[0] is MKV
        self.app.conf['use-mkv'] = radiobtn.get_group()[0].get_active()

    def on_shortcut_btn_toggled(self, button, mode):
        if button.get_active() is False:
            return
        self.app.conf['shortcut-mode'] = mode
        self.shortcut_win.set_sensitive(mode == ShortcutMode.CUSTOM)

    def on_shortcut_key_cell_edited(self, accel, path, key, mod,
                                    hardware_keycode):
        accel_key = Gtk.accelerator_name(key, mod)
        name = self.shortcut_liststore[path][NAME_COL]
        self.shortcut_liststore[path][KEY_COL] = key
        self.shortcut_liststore[path][MOD_COL] = int(mod)
        self.app.conf['custom-shortcut'][name] = accel_key

########NEW FILE########
__FILENAME__ = Radio

# Copyright (C) 2013-2014 LiuLang <gsushzhsosgsu@gmail.com>

# Use of this source code is governed by GPLv3 license that can be found
# in the LICENSE file.

import json
import os
import time

from gi.repository import Gdk
from gi.repository import GdkPixbuf
from gi.repository import GLib
from gi.repository import Gtk
from gi.repository import Pango

from kuwo import Config
from kuwo import Net
from kuwo import Widgets

_ = Config._

class RadioItem(Gtk.EventBox):
    def __init__(self, radio_info, app):
        super().__init__()
        self.app = app
        self.playlists = app.radio.playlists
        self.connect('button-press-event', self.on_button_pressed)
        # radio_info contains:
        # pic, name, radio_id, offset
        self.radio_info = radio_info
        self.expanded = False

        self.box = Gtk.Box()
        self.box.props.margin_top = 5
        self.box.props.margin_bottom = 5
        self.add(self.box)

        self.img = Gtk.Image()
        self.img_path = Net.get_image(radio_info['pic'])
        self.small_pix = GdkPixbuf.Pixbuf.new_from_file_at_size(
                self.img_path, 50, 50)
        self.big_pix = GdkPixbuf.Pixbuf.new_from_file_at_size(
                self.img_path, 75, 75)
        self.img.set_from_pixbuf(self.small_pix)
        self.box.pack_start(self.img, False, False, 0)

        box_right = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.box.pack_start(box_right, True, True, 0)

        radio_name = Gtk.Label(Widgets.short_str(radio_info['name'], 8))
        box_right.pack_start(radio_name, True, True, 0)

        self.label = Gtk.Label(_('song name'))
        self.label.get_style_context().add_class('info-label')
        box_right.pack_start(self.label, False, False, 0)

        self.toolbar = Gtk.Toolbar()
        self.toolbar.set_style(Gtk.ToolbarStyle.ICONS)
        self.toolbar.set_show_arrow(False)
        self.toolbar.set_icon_size(1)
        box_right.pack_start(self.toolbar, False, False, 0)

        button_play = Gtk.ToolButton()
        button_play.set_label(_('Play'))
        button_play.set_icon_name('media-playback-start-symbolic')
        button_play.connect('clicked', self.on_button_play_clicked)
        self.toolbar.insert(button_play, 0)

        button_favorite = Gtk.ToolButton()
        button_favorite.set_label(_('Favorite'))
        button_favorite.set_icon_name('emblem-favorite-symbolic')
        button_favorite.connect('clicked', self.on_button_favorite_clicked)
        self.toolbar.insert(button_favorite, 1)

        button_delete = Gtk.ToolButton()
        button_delete.set_label(_('Delete'))
        button_delete.set_icon_name('user-trash-symbolic')
        button_delete.connect('clicked', self.on_button_delete_clicked)
        self.toolbar.insert(button_delete, 2)

        self.show_all()
        self.label.hide()
        self.toolbar.hide()

        self.init_songs()
    
    def init_songs(self):
        def _update_songs(songs, error=None):
            if not songs:
                return
            index = self.get_index()
            self.playlists[index]['songs'] = songs
            self.playlists[index]['curr_song'] = 0
            self.update_label()
        index = self.get_index()
        if len(self.playlists[index]['songs']) == 0:
            Net.async_call(
                    Net.get_radio_songs, _update_songs, 
                    self.radio_info['radio_id'], self.radio_info['offset'])
    
    def load_more_songs(self):
        def _on_more_songs_loaded(songs, error=None):
            if songs:
                # merge next list of songs to current list
                index = self.get_index()
                self.playlists[index]['songs'] += songs
        index = self.get_index()
        offset = self.playlists[index]['offset'] + 1
        self.playlists[index]['offset'] = offset
        Net.async_call(
                Net.get_radio_songs, _on_more_songs_loaded, 
                self.radio_info['radio_id'], offset)

    def expand(self):
        if self.expanded:
            return
        self.expanded = True
        self.img.set_from_pixbuf(self.big_pix)
        self.label.show_all()
        self.toolbar.show_all()
        self.update_label()

    def collapse(self):
        if not self.expanded:
            return
        self.expanded = False
        self.img.set_from_pixbuf(self.small_pix)
        self.label.hide()
        self.toolbar.hide()

    def update_label(self):
        index = self.get_index()
        radio = self.playlists[index]
        if radio['curr_song'] > 19:
            self.label.set_label('Song Name')
            return
        song = radio['songs'][radio['curr_song']]
        self.label.set_label(Widgets.short_str(song['name'], length=12))
        Gdk.Window.process_all_updates()
        self.label.realize()

    def get_index(self):
        for i, radio in enumerate(self.playlists):
            if radio['radio_id'] == self.radio_info['radio_id']:
                return i

    def play_song(self):
        index = self.get_index()
        radio = self.playlists[index]
        if radio['curr_song'] > 19:
            radio['curr_song'] = 0
            radio['songs'] = radio['songs'][20:]
        song = radio['songs'][radio['curr_song']]
        self.update_label()
        self.app.player.load_radio(song, self)

    def play_next_song(self):
        index = self.get_index()
        self.playlists[index]['curr_song'] += 1
        self.play_song()

    def get_next_song(self):
        index = self.get_index()
        radio = self.playlists[index]
        if radio['curr_song'] == 10:
            self.load_more_songs()
        if radio['curr_song'] > 19:
            radio['curr_song'] = 0
            radio['songs'] = radio['songs'][20:]
        return radio['songs'][radio['curr_song'] + 1]

    def on_button_pressed(self, widget, event):
        parent = self.get_parent()
        children = parent.get_children()
        for child in children:
            child.collapse()
        self.expand()

    # toolbar
    def on_button_play_clicked(self, btn):
        self.play_song()

    def on_button_favorite_clicked(self, btn):
        # TODO: change button image
        index = self.get_index()
        radio = self.playlists[index]
        song = radio['songs'][radio['curr_song']]
        self.app.playlist.add_song_to_favorite(song)

    def on_button_delete_clicked(self, btn):
        self.playlists.pop(self.get_index())
        self.destroy()


class Radio(Gtk.Box):
    '''Radio tab in notebook.'''

    title = _('Radio')

    def __init__(self, app):
        super().__init__()
        self.app = app
        self.playlists = None
        self.load_playlists()

    def first(self):
        app = self.app

        # left side panel
        scrolled_myradio = Gtk.ScrolledWindow()
        scrolled_myradio.props.hscrollbar_policy = Gtk.PolicyType.NEVER
        self.pack_start(scrolled_myradio, False, False, 0)

        # radios selected by user.
        self.box_myradio = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.box_myradio.props.margin_left = 10
        scrolled_myradio.add(self.box_myradio)

        self.scrolled_radios = Gtk.ScrolledWindow()
        self.pack_start(self.scrolled_radios, True, True, 0)

        # pic, name, id, num of listeners, pic_url, tooltip
        self.liststore_radios = Gtk.ListStore(
                GdkPixbuf.Pixbuf, str, int, str, str, str)
        iconview_radios = Widgets.IconView(
                self.liststore_radios, tooltip=5)
        iconview_radios.connect(
                'item_activated', self.on_iconview_radios_item_activated)
        self.scrolled_radios.add(iconview_radios)

        self.show_all()

        nid = 8
        page = 0
        radios, total_page = Net.get_nodes(nid, page)
        if total_page == 0:
            return
        urls = []
        tree_iters = []
        for radio in radios:
            tree_iter = self.liststore_radios.append([
                self.app.theme['anonymous'],
                Widgets.unescape(radio['disname']), 
                int(radio['sourceid'].split(',')[0]),
                Widgets.unescape(radio['info']),
                radio['pic'],
                Widgets.set_tooltip(radio['disname'], radio['info']),
                ])
            tree_iters.append(tree_iter)
            urls.append(radio['pic'])
        self.liststore_radios.timestamp = time.time()
        Net.update_liststore_images(
                self.liststore_radios, 0, tree_iters, urls)

        for radio in self.playlists:
            radio_item = RadioItem(radio, self.app)
            self.box_myradio.pack_start(radio_item, False, False, 0)

        GLib.timeout_add(300000, self.dump_playlists)

    def load_playlists(self):
        filepath = Config.RADIO_JSON
        _default = []
        if os.path.exists(filepath):
            with open(filepath) as fh:
                playlists = json.loads(fh.read())
        else:
            playlists = _default
        self.playlists = playlists

    def dump_playlists(self):
        filepath = Config.RADIO_JSON
        if self.playlists:
            with open(filepath, 'w') as fh:
                fh.write(json.dumps(self.playlists))
        return True

    def do_destroy(self):
        self.dump_playlists()

    def on_iconview_radios_item_activated(self, iconview, path):
        model = iconview.get_model()
        radio_info = {
                'name': model[path][1],
                'radio_id': model[path][2],
                'pic': model[path][4],
                'offset': 0,
                'curr_song': 0,
                'songs': [],
                }
        self.append_radio(radio_info)

    def append_radio(self, radio_info):
        for radio in self.playlists:
            # check if this radio already exists
            if radio['radio_id'] == radio_info['radio_id']:
                return
        self.playlists.append(radio_info)
        radio_item = RadioItem(radio_info, self.app)
        self.box_myradio.pack_start(radio_item, False, False, 0)

########NEW FILE########
__FILENAME__ = Search

# Copyright (C) 2013-2014 LiuLang <gsushzhsosgsu@gmail.com>

# Use of this source code is governed by GPLv3 license that can be found
# in the LICENSE file.

import html
import time

from gi.repository import Gdk
from gi.repository import GdkPixbuf
from gi.repository import Gtk

from kuwo import Config
from kuwo import Widgets
from kuwo import Net

_ = Config._

class Search(Gtk.Box):
    '''Search tab in notebook.'''

    title = _('Search')

    def __init__(self, app):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        self.app = app

        self.songs_tab_inited = False
        self.artists_tab_inited = False
        self.albums_tab_inited = False

        box_top = Gtk.Box(spacing=5)
        self.pack_start(box_top, False, False, 0)

        if Config.GTK_LE_36:
            self.search_entry = Gtk.Entry()
        else:
            self.search_entry = Gtk.SearchEntry()
        self.search_entry.set_placeholder_text(_('Search Songs, Artists..'))
        self.search_entry.props.width_chars = 30
        self.search_entry.connect('activate', self.on_search_entry_activate)
        box_top.pack_start(self.search_entry, False, False, 20)

        self.songs_button = Widgets.ListRadioButton(_('Songs'))
        self.songs_button.connect('toggled', self.switch_notebook_page, 0)
        box_top.pack_start(self.songs_button, False, False, 0)

        self.artists_button = Widgets.ListRadioButton(
                _('Artists'), self.songs_button)
        self.artists_button.connect('toggled', self.switch_notebook_page, 1)
        box_top.pack_start(self.artists_button, False, False, 0)

        self.albums_button = Widgets.ListRadioButton(
                _('Albums'), self.songs_button)
        self.albums_button.connect('toggled', self.switch_notebook_page, 2)
        box_top.pack_start(self.albums_button, False, False, 0)

        # TODO: add MV and lyrics search.

        # checked, name, artist, album, rid, artistid, albumid
        self.liststore_songs = Gtk.ListStore(
                bool, str, str, str, int, int, int)
        self.control_box = Widgets.ControlBox(
                self.liststore_songs, app, select_all=False)
        box_top.pack_end(self.control_box, False, False, 0)

        self.notebook = Gtk.Notebook()
        self.notebook.set_show_tabs(False)
        self.pack_start(self.notebook, True, True, 0)

        songs_tab = Gtk.ScrolledWindow()
        songs_tab.get_vadjustment().connect(
                'value-changed', self.on_songs_tab_scrolled)
        self.notebook.append_page(songs_tab, Gtk.Label(_('Songs')))
        treeview_songs = Widgets.TreeViewSongs(self.liststore_songs, app)
        songs_tab.add(treeview_songs)

        artists_tab = Gtk.ScrolledWindow()
        artists_tab.get_vadjustment().connect(
                'value-changed', self.on_artists_tab_scrolled)
        self.notebook.append_page(artists_tab, Gtk.Label(_('Artists')))

        # pic, artist, artistid, country
        self.liststore_artists = Gtk.ListStore(
                GdkPixbuf.Pixbuf, str, int, str)
        iconview_artists = Widgets.IconView(self.liststore_artists)
        iconview_artists.connect(
                'item_activated', self.on_iconview_artists_item_activated)
        artists_tab.add(iconview_artists)

        albums_tab = Gtk.ScrolledWindow()
        albums_tab.get_vadjustment().connect(
                'value-changed', self.on_albums_tab_scrolled)
        self.notebook.append_page(albums_tab, Gtk.Label(_('Albums')))

        # logo, album, albumid, artist, artistid, info
        self.liststore_albums = Gtk.ListStore(
                GdkPixbuf.Pixbuf, str, int, str, int, str)
        iconview_albums = Widgets.IconView(self.liststore_albums, tooltip=5)
        iconview_albums.connect(
                'item_activated', self.on_iconview_albums_item_activated)
        albums_tab.add(iconview_albums)

    def after_init(self):
        self.control_box.hide()

    def first(self):
        pass

    def switch_notebook_page(self, radiobtn, page):
        state = radiobtn.get_active()
        if not state:
            return
        self.notebook.set_current_page(page)
        if page == 0 and self.songs_tab_inited:
            self.control_box.show_all()
        else:
            self.control_box.hide()

        if ((page == 0 and not self.songs_tab_inited) or
           (page == 1 and not self.artists_tab_inited) or
           (page == 2 and not self.artists_tab_inited)):
            self.on_search_entry_activate(None, False)

    def on_search_entry_activate(self, search_entry, reset_status=True):
        if not self.search_entry.get_text():
            return
        if reset_status:
            self.reset_search_status()
        page = self.notebook.get_current_page()
        if page == 0:
            self.control_box.show_all()
            self.songs_tab_inited = True
            self.show_songs(reset_status)
        elif page == 1:
            self.artists_tab_inited = True
            self.show_artists(reset_status)
        elif page == 2:
            self.albums_tab_inited = True
            self.show_albums(reset_status)

    def show_songs(self, reset_status=False):
        def _append_songs(songs_args, error=None):
            songs, hit, self.songs_total = songs_args
            if not songs or hit == 0:
                if reset_status:
                    self.songs_button.set_label('{0} (0)'.format(_('Songs')))
                return
            self.songs_button.set_label('{0} ({1})'.format(_('Songs'), hit))
            for song in songs:
                self.liststore_songs.append([
                    False,
                    Widgets.unescape(song['SONGNAME']),
                    Widgets.unescape(song['ARTIST']),
                    Widgets.unescape(song['ALBUM']),
                    int(song['MUSICRID'][6:]),
                    int(song['ARTISTID']),
                    int(song['ALBUMID']),
                    ])

        keyword = self.search_entry.get_text()
        self.app.playlist.advise_new_playlist_name(keyword)
        if not keyword:
            return
        if reset_status:
            self.liststore_songs.clear()
        Net.async_call(
                Net.search_songs, _append_songs, keyword, self.songs_page)

    def show_artists(self, reset_status=False):
        def _append_artists(artists_args, error=None):
            artists, hit, self.artists_total = artists_args
            if (error or not hit) and reset_status:
                self.artists_button.set_label('{0} (0)'.format(_('Artists')))
                return
            self.artists_button.set_label(
                    '{0} ({1})'.format(_('Artists'), hit))
            urls = []
            tree_iters = []
            for artist in artists:
                tree_iter = self.liststore_artists.append([
                    self.app.theme['anonymous'],
                    Widgets.unescape(artist['ARTIST']),
                    int(artist['ARTISTID']), 
                    Widgets.unescape(artist['COUNTRY']),
                    ])
                tree_iters.append(tree_iter)
                urls.append(artist['PICPATH'])
            Net.update_artist_logos(
                    self.liststore_artists, 0, tree_iters, urls)

        keyword = self.search_entry.get_text()
        if not keyword:
            return
        if reset_status:
            self.liststore_artists.clear()
        if reset_status or not hasattr(self.liststore_artists, 'timestamp'):
            self.liststore_artists.timestamp = time.time()
        Net.async_call(
                Net.search_artists, _append_artists,
                keyword,self.artists_page)

    def show_albums(self, reset_status=False):
        def _append_albums(albums_args, error=None):
            albums, hit, self.albums_total = albums_args
            if (error or hit == 0) and reset_status:
                self.albums_button.set_label(
                        '{0} (0)'.format(_('Albums')))
                return
            self.albums_button.set_label(
                    '{0} ({1})'.format(_('Albums'), hit))
            urls = []
            tree_iters = []
            for album in albums:
                tooltip = Widgets.escape(album.get('info', album['name']))
                tree_iter = self.liststore_albums.append([
                    self.app.theme['anonymous'],
                    Widgets.unescape(album['name']),
                    int(album['albumid']), 
                    Widgets.unescape(album['artist']),
                    int(album['artistid']),
                    tooltip,
                    ])
                tree_iters.append(tree_iter)
                urls.append(album['pic'])
            Net.update_album_covers(
                    self.liststore_albums, 0, tree_iters, urls)

        keyword = self.search_entry.get_text()
        if not keyword:
            return
        if reset_status:
            self.liststore_albums.clear()
        if reset_status or not hasattr(self.liststore_albums, 'timestamp'):
            self.liststore_albums.timestamp = time.time()
        Net.async_call(
                Net.search_albums, _append_albums,
                keyword, self.albums_page)

    def reset_search_status(self):
        self.songs_tab_inited = False
        self.artists_tab_inited = False
        self.albums_tab_inited = False

        self.songs_button.set_label(_('Songs'))
        self.artists_button.set_label(_('Artists'))
        self.albums_button.set_label(_('Albums'))

        self.liststore_songs.clear()
        self.liststore_artists.clear()
        self.liststore_albums.clear()

        self.songs_page = 0
        self.artists_page = 0
        self.albums_page = 0

    def search_artist(self, artist):
        self.reset_search_status()
        self.app.popup_page(self.app_page)
        self.artists_tab_inited = False
        self.search_entry.set_text(artist)
        self.artists_button.set_active(True)
        self.artists_button.toggled()

    def search_album(self, album):
        self.reset_search_status()
        self.app.popup_page(self.app_page)
        self.albums_tab_inited = False
        self.search_entry.set_text(album)
        self.albums_button.set_active(True)
        self.albums_button.toggled()

    def on_songs_tab_scrolled(self, adj):
        if (Widgets.reach_scrolled_bottom(adj) and
            self.songs_page < self.songs_total - 1):
            self.songs_page += 1
            self.show_songs()

    def on_artists_tab_scrolled(self, adj):
        if (Widgets.reach_scrolled_bottom(adj) and 
            self.artists_page < self.artists_total - 1):
            self.artists_page += 1
            self.show_artists()

    def on_albums_tab_scrolled(self, adj):
        if (Widgets.reach_scrolled_bottom(adj) and
            self.albums_page < self.albums_total - 1):
            self.albums_page += 1
            self.show_albums()

    def on_iconview_artists_item_activated(self, iconview, path):
        model = iconview.get_model()
        artist = model[path][1]
        artistid = model[path][2]
        self.app.popup_page(self.app.artists.app_page)
        self.app.artists.show_artist(artist, artistid)

    def on_iconview_albums_item_activated(self, iconview, path):
        model = iconview.get_model()
        album = model[path][1]
        albumid = model[path][2]
        artist = model[path][3]
        artistid = model[path][4]
        self.app.popup_page(self.app.artists.app_page)
        self.app.artists.show_album(album, albumid, artist, artistid)

########NEW FILE########
__FILENAME__ = Shortcut

# Copyright (C) 2013-2014 LiuLang <gsushzhsosgsu@gmail.com>

# Use of this source code is governed by GPLv3 license that can be found
# in http://www.gnu.org/licenses/gpl-3.0.html

from gi.repository import GLib

try:
    from keybinder.keybinder_gtk import KeybinderGtk
    keybinder_imported = True
except ImportError as e:
    keybinder_imported = False
    print('Warning: no python3-keybinder module found,',
          'global keyboard shortcut will be disabled!')

from kuwo import Config
ShortcutMode = Config.ShortcutMode

class Shortcut:
    def __init__(self, player):
        self.player = player

        self.callbacks = {
                'VolumeUp': self.volume_up,
                'VolumeDown': self.volume_down,
                'Mute': lambda *args: player.toggle_mute_cb(),
                'Previous': lambda *args: player.load_prev_cb(),
                'Next': lambda *args: player.load_next_cb(),
                'Pause': lambda *args: player.play_pause_cb(),
                'Play': lambda *args: player.play_pause_cb(),
                'Stop': lambda *args: player.stop_player_cb(),
                'Launch': self.present_window,
                }

        if keybinder_imported:
            self.keybinder = KeybinderGtk()
            self.bind_keys()
            self.keybinder.start()
            
    def volume_up(self, *args):
        volume = self.player.volume.get_value() + 0.15
        if volume > 1:
            volume = 1
        self.player.set_volume_cb(volume)

    def volume_down(self, *args):
        volume = self.player.volume.get_value() - 0.15
        if volume < 0:
            volume = 0
        self.player.set_volume_cb(volume)

    def present_window(self, *args):
        GLib.idle_add(self.player.app.window.present)

    def bind_keys(self):
        if not keybinder_imported:
            return
        curr_mode = self.player.app.conf['shortcut-mode']
        if curr_mode == ShortcutMode.NONE:
            return
        if curr_mode == ShortcutMode.DEFAULT:
            shortcut_keys = self.player.app.conf['default-shortcut']
        elif curr_mode == ShortcutMode.CUSTOM:
            shortcut_keys = self.player.app.conf['custom-shortcut']
        for name, key in shortcut_keys.items():
            self.keybinder.register(key, self.callbacks[name])

    def rebind_keys(self):
        self.bind_keys()

    def quit(self):
        if keybinder_imported:
            self.keybinder.stop()

########NEW FILE########
__FILENAME__ = Themes

# Copyright (C) 2013-2014 LiuLang <gsushzhsosgsu@gmail.com>

# Use of this source code is governed by GPLv3 license that can be found
# in the LICENSE file.

import time

from gi.repository import GdkPixbuf
from gi.repository import Gtk

from kuwo import Config
from kuwo import Net
from kuwo import Widgets

_ = Config._

class Themes(Gtk.Box):
    '''Themes tab in notebook.'''

    title = _('Themes')

    def __init__(self, app):
        super().__init__(orientation=Gtk.Orientation.VERTICAL)
        self.app = app

    def first(self):
        app = self.app

        self.buttonbox = Gtk.Box(spacing=5)
        self.pack_start(self.buttonbox, False, False, 0)

        self.button_main = Gtk.Button(_('Themes'))
        self.button_main.connect('clicked', self.on_button_main_clicked)
        self.buttonbox.pack_start(self.button_main, False, False, 0)

        self.button_sub = Gtk.Button('')
        self.button_sub.connect('clicked', self.on_button_sub_clicked)
        self.buttonbox.pack_start(self.button_sub, False, False, 0)

        self.label = Gtk.Label('')
        self.buttonbox.pack_start(self.label, False, False, 0)

        # checked, name, artist, album, rid, artistid, albumid
        self.liststore_songs = Gtk.ListStore(
                bool, str, str, str, int, int, int)
        self.control_box = Widgets.ControlBox(self.liststore_songs, app)
        self.buttonbox.pack_end(self.control_box, False, False, 0)

        self.scrolled_main = Gtk.ScrolledWindow()
        self.pack_start(self.scrolled_main, True, True, 0)
        # pic, name, id, info(num of lists), tooltip
        self.liststore_main = Gtk.ListStore(
                GdkPixbuf.Pixbuf, str, int, str, str)
        iconview_main = Widgets.IconView(self.liststore_main, tooltip=4)
        iconview_main.connect(
                'item_activated', self.on_iconview_main_item_activated)
        self.scrolled_main.add(iconview_main)

        self.scrolled_sub = Gtk.ScrolledWindow()
        self.scrolled_sub.get_vadjustment().connect(
                'value-changed', self.on_scrolled_sub_scrolled)
        self.pack_start(self.scrolled_sub, True, True, 0)
        # pic, name, sourceid, info(num of lists), tooltip
        self.liststore_sub = Gtk.ListStore(
                GdkPixbuf.Pixbuf, str, int, str, str)
        iconview_sub = Widgets.IconView(self.liststore_sub, tooltip=4)
        iconview_sub.connect(
                'item_activated', self.on_iconview_sub_item_activated)
        self.scrolled_sub.add(iconview_sub)

        self.scrolled_songs = Gtk.ScrolledWindow()
        self.scrolled_songs.get_vadjustment().connect(
                'value-changed', self.on_scrolled_songs_scrolled)
        self.pack_start(self.scrolled_songs, True, True, 0)
        treeview_songs = Widgets.TreeViewSongs(self.liststore_songs, app)
        self.scrolled_songs.add(treeview_songs)

        self.show_all()
        self.buttonbox.hide()
        self.scrolled_sub.hide()
        self.scrolled_songs.hide()

        nodes = Net.get_themes_main()
        if not nodes:
            print('Failed to get nodes, do something!')
            return
        urls = []
        tree_iters = []
        for node in nodes:
            tree_iter = self.liststore_main.append([
                self.app.theme['anonymous'],
                Widgets.unescape(node['name']),
                int(node['nid']),
                Widgets.unescape(node['info']),
                Widgets.set_tooltip(node['name'], node['info']),
                ])
            urls.append(node['pic'])
            tree_iters.append(tree_iter)
        self.liststore_main.timestamp = time.time()
        Net.update_liststore_images(
                self.liststore_main, 0, tree_iters, urls)

    def on_iconview_main_item_activated(self, iconview, path):
        model = iconview.get_model()
        self.curr_sub_name = model[path][1]
        self.curr_sub_id = model[path][2]
        self.label.set_label(self.curr_sub_name)
        self.show_sub(init=True)

    def show_sub(self, init=False):
        def on_show_sub(info, error=None):
            if error or not info:
                return
            nodes, self.nodes_total = info
            if not nodes:
                return
            urls = []
            tree_iters = []
            for node in nodes:
                tree_iter = self.liststore_sub.append([
                    self.app.theme['anonymous'],
                    Widgets.unescape(node['name']),
                    int(node['sourceid']),
                    Widgets.unescape(node['info']),
                    Widgets.set_tooltip_with_song_tips(
                        node['name'], node['tips']),
                    ])
                tree_iters.append(tree_iter)
                urls.append(node['pic'])
            Net.update_liststore_images(
                    self.liststore_sub, 0, tree_iters, urls)
        if init:
            self.scrolled_main.hide()
            self.scrolled_songs.hide()
            self.buttonbox.show_all()
            self.button_sub.hide()
            self.control_box.hide()
            self.scrolled_sub.get_vadjustment().set_value(0)
            self.scrolled_sub.show_all()
            self.nodes_page = 0
            self.liststore_sub.clear()
        if init or not hasattr(self.liststore_sub, 'timestamp'):
            self.liststore_sub.timestamp = time.time()
        #nodes, self.nodes_total = Net.get_nodes(
        #        self.curr_sub_id, self.nodes_page)
        Net.async_call(
                Net.get_nodes, on_show_sub, self.curr_sub_id,
                self.nodes_page)

    def on_iconview_sub_item_activated(self, iconview, path):
        model = iconview.get_model()
        self.curr_list_name = model[path][1]
        self.curr_list_id = model[path][2]
        self.label.set_label(self.curr_list_name)
        self.button_sub.set_label(self.curr_sub_name)
        self.show_songs(init=True)
    
    def show_songs(self, init=False):
        if init:
            self.app.playlist.advise_new_playlist_name(
                    self.label.get_text())
            self.liststore_songs.clear()
            self.songs_page = 0
            self.scrolled_sub.hide()
            self.button_sub.show_all()
            self.control_box.show_all()
            self.scrolled_songs.get_vadjustment().set_value(0.0)
            self.scrolled_songs.show_all()

        songs, self.songs_total = Net.get_themes_songs(
                self.curr_list_id, self.songs_page)
        if not songs:
            return
        for song in songs:
            self.liststore_songs.append([
                True,
                Widgets.unescape(song['name']),
                Widgets.unescape(song['artist']),
                Widgets.unescape(song['album']),
                int(song['id']),
                int(song['artistid']), 
                int(song['albumid']),
                ])
    
    # buttonbox buttons
    def on_button_main_clicked(self, btn):
        self.buttonbox.hide()
        self.scrolled_sub.hide()
        self.scrolled_songs.hide()
        self.control_box.hide()
        self.scrolled_main.show_all()

    def on_button_sub_clicked(self, btn):
        self.scrolled_songs.hide()
        self.label.set_label(self.curr_sub_name)
        self.buttonbox.show_all()
        self.button_sub.hide()
        self.control_box.hide()
        self.scrolled_sub.show_all()

    def on_scrolled_sub_scrolled(self, adj):
        if (Widgets.reach_scrolled_bottom(adj) and
            self.nodes_page < self.nodes_total - 1):
            self.nodes_page += 1
            self.show_sub()

    def on_scrolled_songs_scrolled(self, adj):
        if (Widgets.reach_scrolled_bottom(adj) and
            self.songs_page < self.songs_total - 1):
            self.songs_page += 1
            self.show_songs()

########NEW FILE########
__FILENAME__ = TopCategories

# Copyright (C) 2013-2014 LiuLang <gsushzhsosgsu@gmail.com>

# Use of this source code is governed by GPLv3 license that can be found
# in the LICENSE file.

import time

from gi.repository import GdkPixbuf
from gi.repository import Gtk

from kuwo import Config
from kuwo import Net
from kuwo import Widgets

_ = Config._

class TopCategories(Gtk.Box):
    '''Categories tab in notebook.'''

    title = _('Categories')

    def __init__(self, app):
        super().__init__(orientation=Gtk.Orientation.VERTICAL)
        self.app = app

    def first(self):
        app = self.app

        self.buttonbox = Gtk.Box(spacing=5)
        self.pack_start(self.buttonbox, False, False, 0)

        self.button_main = Gtk.Button(_('Top Categories'))
        self.button_main.connect('clicked', self.on_button_main_clicked)
        self.buttonbox.pack_start(self.button_main, False, False, 0)

        self.button_sub1 = Gtk.Button('')
        self.button_sub1.connect('clicked', self.on_button_sub1_clicked)
        self.buttonbox.pack_start(self.button_sub1, False, False, 0)

        self.button_sub2 = Gtk.Button('')
        self.button_sub2.connect('clicked', self.on_button_sub2_clicked)
        self.buttonbox.pack_start(self.button_sub2, False, False, 0)

        self.label = Gtk.Label('')
        self.buttonbox.pack_start(self.label, False, False, 0)

        # checked, name, artist, album, rid, artistid, albumid
        self.liststore_songs = Gtk.ListStore(
                bool, str, str, str, int, int, int)
        self.control_box = Widgets.ControlBox(self.liststore_songs, app)
        self.buttonbox.pack_end(self.control_box, False, False, 0)

        self.scrolled_main = Gtk.ScrolledWindow()
        self.pack_start(self.scrolled_main, True, True, 0)
        # logo, name, nid, num of lists(info), tooltip
        self.liststore_main = Gtk.ListStore(
                GdkPixbuf.Pixbuf, str, int, str, str)
        iconview_main = Widgets.IconView(self.liststore_main, tooltip=4)
        iconview_main.connect(
                'item_activated', self.on_iconview_main_item_activated)
        self.scrolled_main.add(iconview_main)

        self.scrolled_sub1 = Gtk.ScrolledWindow()
        self.pack_start(self.scrolled_sub1, True, True, 0)
        # logo, name, nid, num of lists(info), tooltip
        self.liststore_sub1 = Gtk.ListStore(
                GdkPixbuf.Pixbuf, str, int, str, str)
        iconview_sub1 = Widgets.IconView(self.liststore_sub1, tooltip=4)
        iconview_sub1.connect(
                'item_activated', self.on_iconview_sub1_item_activated)
        self.scrolled_sub1.add(iconview_sub1)

        self.scrolled_sub2 = Gtk.ScrolledWindow()
        self.pack_start(self.scrolled_sub2, True, True, 0)
        # logo, name, nid, info, tooltip
        self.liststore_sub2 = Gtk.ListStore(
                GdkPixbuf.Pixbuf, str, int, str, str)
        iconview_sub2 = Widgets.IconView(self.liststore_sub2, tooltip=4)
        iconview_sub2.connect(
                'item_activated', self.on_iconview_sub2_item_activated)
        self.scrolled_sub2.add(iconview_sub2)

        self.scrolled_songs = Gtk.ScrolledWindow()
        self.pack_start(self.scrolled_songs, True, True, 0)
        treeview_songs = Widgets.TreeViewSongs(self.liststore_songs, app)
        self.scrolled_songs.add(treeview_songs)

        self.show_all()
        self.buttonbox.hide()
        self.scrolled_sub1.hide()
        self.scrolled_sub2.hide()
        self.scrolled_songs.hide()

        nid = 5
        page = 0
        nodes, total_page = Net.get_nodes(nid, page)
        if not nodes:
            print('Failed to get nodes, do something!')
            return
        urls = []
        tree_iters = []
        for node in nodes:
            # skip 'xx专区' categories
            if node['disname'].endswith('专区'):
                continue
            tree_iter = self.liststore_main.append([
                self.app.theme['anonymous'],
                Widgets.unescape(node['disname']),
                int(node['id']),
                Widgets.unescape(node['info']),
                Widgets.set_tooltip(node['disname'], node['info']),
                ])
            tree_iters.append(tree_iter)
            urls.append(node['pic'])
        self.liststore_main.timestamp = time.time()
        Net.update_liststore_images(
                self.liststore_main, 0, tree_iters, urls)

    def on_iconview_main_item_activated(self, iconview, path):
        model = iconview.get_model()
        self.curr_sub1_name = model[path][1]
        self.curr_sub1_id = model[path][2]
        if self.curr_sub1_id in (79, 17250):
            # (79, 17250) will get songs with Net.get_alubum()
            self.use_album = True
        else:
            self.use_album = False
        if self.curr_sub1_id in (79, 17250, 78067, 78312):
            self.use_sub2 = True
        else:
            self.use_sub2 = False
        self.label.set_label(self.curr_sub1_name)
        self.show_sub1(init=True)

    def show_sub1(self, init=False):
        def _show_sub1(sub1_args, error=None):
            nodes, self.sub1_total = sub1_args
            if error or not nodes or not self.sub1_total:
                return
            urls = []
            tree_iters = []
            for node in nodes:
                _id = 'id' if self.use_sub2 else 'sourceid'
                if 'tips' in node and len(node['tips']) > 5:
                    tooltip = Widgets.set_tooltip_with_song_tips(
                            node['name'], node['tips'])
                else:
                    tooltip = Widgets.set_tooltip(node['name'], node['info'])
                tree_iter = self.liststore_sub1.append([
                    self.app.theme['anonymous'],
                    Widgets.unescape(node['name']),
                    int(node[_id]),
                    Widgets.unescape(node['info']),
                    tooltip,
                    ])
                urls.append(node['pic'])
                tree_iters.append(tree_iter)
            Net.update_liststore_images(
                    self.liststore_sub1, 0, tree_iters, urls)

            self.sub1_page += 1
            if self.sub1_page < self.sub1_total - 1:
                self.show_sub1()

        if init:
            self.scrolled_main.hide()
            self.buttonbox.show_all()
            self.button_sub1.hide()
            self.button_sub2.hide()
            self.control_box.hide()
            self.scrolled_sub1.get_vadjustment().set_value(0)
            self.scrolled_sub1.show_all()
            self.sub1_page = 0
            self.liststore_sub1.clear()
        if init or not hasattr(self.liststore_sub1, 'timestamp'):
            self.liststore_sub1.timestamp = time.time()
        Net.async_call(
                Net.get_nodes, _show_sub1, self.curr_sub1_id,
                self.sub1_page)

    def on_iconview_sub1_item_activated(self, iconview, path):
        model = iconview.get_model()
        if self.use_sub2:
            self.curr_sub2_name = model[path][1]
            self.curr_sub2_id = model[path][2]
            self.label.set_label(self.curr_sub2_name)
            self.button_sub1.set_label(self.curr_sub1_name)
            self.show_sub2(init=True)
        else:
            self.curr_list_name = model[path][1]
            self.curr_list_id = model[path][2]
            self.label.set_label(self.curr_list_name)
            self.app.playlist.advise_new_playlist_name(self.curr_list_name)
            self.button_sub1.set_label(self.curr_sub1_name)
            self.append_songs(init=True)

    def show_sub2(self, init=False):
        def _show_sub2(sub2_args, error=None):
            nodes, self.sub2_total = sub2_args
            if error or not nodes or not self.sub2_total:
                return
            urls = []
            tree_iters = []
            for node in nodes:
                tree_iter = self.liststore_sub2.append([
                    self.app.theme['anonymous'],
                    Widgets.unescape(node['name']),
                    int(node['sourceid']),
                    Widgets.unescape(node['info']),
                    Widgets.set_tooltip_with_song_tips(
                        node['name'], node['tips']),
                    ])
                urls.append(node['pic'])
                tree_iters.append(tree_iter)
            Net.update_liststore_images(
                    self.liststore_sub2, 0, tree_iter, urls)

            self.sub2_page += 1
            if self.sub2_page < self.sub2_total - 1:
                self.show_sub2()

        if init:
            self.scrolled_sub1.hide()
            self.button_sub1.show_all()
            self.scrolled_sub2.get_vadjustment().set_value(0)
            self.scrolled_sub2.show_all()
            self.sub2_page = 0
            self.liststore_sub2.clear()
        if init or not hasattr(self.liststore_sub2, 'timestamp'):
            self.liststore_sub2.timestamp = time.time()
        Net.async_call(
                Net.get_nodes, _show_sub2, self.curr_sub2_id,
                self.sub2_page)

    def on_iconview_sub2_item_activated(self, iconview, path):
        model = iconview.get_model()
        self.curr_list_name = model[path][1]
        self.curr_list_id = model[path][2]
        self.label.set_label(self.curr_list_name)
        self.button_sub2.set_label(self.curr_sub2_name)
        self.append_songs(init=True)

    def append_songs(self, init=False):
        def _append_songs(songs_args, error=None):
            songs, self.songs_total = songs_args
            if not songs or self.songs_total == 0 or self.use_album:
                songs = Net.get_album(self.curr_list_id)
                self.songs_total = 1
                if not songs:
                    return
                for song in songs:
                    self.liststore_songs.append([
                        True,
                        Widgets.unescape(song['name']), 
                        Widgets.unescape(song['artist']),
                        Widgets.unescape(self.curr_list_name), 
                        int(song['id']),
                        int(song['artistid']), 
                        int(self.curr_list_id),
                        ])
                return

            for song in songs:
                self.liststore_songs.append([
                    True,
                    Widgets.unescape(song['name']),
                    Widgets.unescape(song['artist']),
                    Widgets.unescape(song['album']),
                    int(song['id']),
                    int(song['artistid']), 
                    int(song['albumid']),
                    ])
            self.songs_page += 1
            if self.songs_page < self.songs_total - 1:
                self.append_songs()

        if init:
            self.app.playlist.advise_new_playlist_name(self.label.get_text())
            self.songs_page = 0
            self.scrolled_sub1.hide()
            self.button_sub1.show_all()
            self.control_box.show_all()
            if self.use_sub2:
                self.scrolled_sub2.hide()
                self.button_sub2.show_all()
            self.scrolled_songs.get_vadjustment().set_value(0.0)
            self.scrolled_songs.show_all()
            self.liststore_songs.clear()

        Net.async_call(
                Net.get_themes_songs, _append_songs, self.curr_list_id,
                self.songs_page)

    # buttonbox
    def on_button_main_clicked(self, btn):
        self.scrolled_sub1.hide()
        self.scrolled_sub2.hide()
        self.scrolled_songs.hide()
        self.buttonbox.hide()
        self.scrolled_main.show_all()

    def on_button_sub1_clicked(self, btn):
        self.scrolled_songs.hide()
        self.scrolled_sub2.hide()
        self.button_sub1.hide()
        self.button_sub2.hide()
        self.control_box.hide()
        self.scrolled_sub1.show_all()

    def on_button_sub2_clicked(self, btn):
        self.scrolled_songs.hide()
        self.button_sub2.hide()
        self.control_box.hide()
        self.label.set_label(self.button_sub2.get_label())
        self.scrolled_sub2.show_all()

########NEW FILE########
__FILENAME__ = TopList

# Copyright (C) 2013-2014 LiuLang <gsushzhsosgsu@gmail.com>

# Use of this source code is governed by GPLv3 license that can be found
# in the LICENSE file.

import time

from gi.repository import GdkPixbuf
from gi.repository import Gtk

from kuwo import Config
from kuwo import Net
from kuwo import Widgets

_ = Config._

class TopList(Gtk.Box):
    '''TopList tab in notebook.'''

    title = _('Top List')

    def __init__(self, app):
        super().__init__()
        self.set_orientation(Gtk.Orientation.VERTICAL)
        self.app = app

    def first(self):
        app = self.app

        self.buttonbox = Gtk.Box(spacing=5)
        self.pack_start(self.buttonbox, False, False, 0)
        button_home = Gtk.Button(_('TopList'))
        button_home.connect('clicked', self.on_button_home_clicked)
        self.buttonbox.pack_start(button_home, False, False, 0)
        self.label = Gtk.Label('')
        self.buttonbox.pack_start(self.label, False, False, 0)

        # checked, name, artist, album, rid, artistid, albumid
        self.liststore_songs = Gtk.ListStore(
                bool, str, str, str, int, int, int)
        control_box = Widgets.ControlBox(self.liststore_songs, app)
        self.buttonbox.pack_end(control_box, False, False, 0)

        self.scrolled_nodes = Gtk.ScrolledWindow()
        self.pack_start(self.scrolled_nodes, True, True, 0)
        # logo, name, nid, info, tooltip
        self.liststore_nodes = Gtk.ListStore(
                GdkPixbuf.Pixbuf, str, int, str, str)
        iconview_nodes = Widgets.IconView(self.liststore_nodes, tooltip=4)
        iconview_nodes.connect(
                'item_activated', self.on_iconview_nodes_item_activated)
        self.scrolled_nodes.add(iconview_nodes)

        self.scrolled_songs = Gtk.ScrolledWindow()
        self.pack_start(self.scrolled_songs, True, True, 0)
        treeview_songs = Widgets.TreeViewSongs(self.liststore_songs, app)
        self.scrolled_songs.add(treeview_songs)

        self.show_all()
        self.buttonbox.hide()
        self.scrolled_songs.hide()

        nid = 2
        page = 0
        nodes, total_pages = Net.get_nodes(nid, page)
        if total_pages == 0:
            return
        urls = []
        tree_iters = []
        for node in nodes:
            tree_iter = self.liststore_nodes.append([
                self.app.theme['anonymous'],
                Widgets.unescape(node['name']),
                int(node['sourceid']),
                Widgets.unescape(node['info']),
                Widgets.set_tooltip_with_song_tips(
                    node['name'], node['tips']),
                ])
            urls.append(node['pic'])
            tree_iters.append(tree_iter)
        self.liststore_nodes.timestamp = time.time()
        Net.update_liststore_images(self.liststore_nodes, 0, tree_iters, urls)

    def on_button_home_clicked(self, btn):
        self.scrolled_nodes.show_all()
        self.scrolled_songs.hide()
        self.buttonbox.hide()

    def on_iconview_nodes_item_activated(self, iconview, path):
        model = iconview.get_model()
        self.buttonbox.show_all()
        self.label.set_label(model[path][1])
        self.app.playlist.advise_new_playlist_name(model[path][1])
        self.show_toplist_songs(model[path][2])

    def show_toplist_songs(self, nid):
        self.scrolled_nodes.hide()
        self.scrolled_songs.show_all()

        songs = Net.get_toplist_songs(nid)
        if not songs:
            print('Error, failed to get toplist songs')
            return
        self.liststore_songs.clear()
        for song in songs:
            self.liststore_songs.append([
                True,
                Widgets.unescape(song['name']), 
                Widgets.unescape(song['artist']),
                Widgets.unescape(song['album']),
                int(song['id']), 
                int(song['artistid']),
                int(song['albumid']),
                ])

########NEW FILE########
__FILENAME__ = Utils

# Copyright (C) 2013-2014 LiuLang <gsushzhsosgsu@gmail.com>

# Use of this source code is governed by GPLv3 license that can be found
# in the LICENSE file.

import base64
import json
import os
import sys
from urllib import parse
import subprocess
import zlib


mutagenx_imported = False
if sys.version_info.major >= 3 and sys.version_info.minor >= 3:
    try:
        from mutagenx.mp3 import MP3
        from mutagenx.easyid3 import EasyID3
        from mutagenx.apev2 import APEv2File
        mutagenx_imported = True
    except ImportError as e:
        print('Warning: mutagenx was not found')
else:
    print('Warning: Python3 < 3.3, mutagenx is not supported')


def decode_lrc_content(lrc, is_lrcx=False):
    '''lrc currently is bytes. '''
    if lrc[:10] != b'tp=content':
        return None
    index = lrc.index(b'\r\n\r\n')
    lrc_bytes = lrc[index+4:]
    str_lrc = zlib.decompress(lrc_bytes)
    if not is_lrcx:
        return str_lrc.decode('gb18030')
    str_bytes = base64.decodebytes(str_lrc)
    return xor_bytes(str_bytes).decode('gb18030')

def xor_bytes(str_bytes, key='yeelion'):
    #key = 'yeelion'
    xor_bytes = key.encode('utf8')
    str_len = len(str_bytes)
    xor_len = len(xor_bytes)
    output = bytearray(str_len)
    i = 0
    while i < str_len:
        j = 0
        while j < xor_len and i < str_len:
            output[i] = str_bytes[i] ^ xor_bytes[j]
            i += 1
            j += 1
    return output

def decode_music_file(filename):
    with open(filename, 'rb') as fh:
        byte_str = fh.read()
    #output = zlib.decompress(byte_str)
    output = xor_bytes(byte_str)
    print(output)
    print(output.decode())
    result = output.decode('gb2312')
    print(result)

def encode_lrc_url(rid):
    '''Get lrc file link.

    rid is like '928003'
    like this: 
    will get:
    DBYAHlRcXUlcUVRYXUI0MDYlKjBYV1dLXUdbQhIQEgNbX19LSwAUDEMlDigQHwAMSAsAFBkMHBocF1gABgwPFQ0KHx1JHBwUWF1PHAEXAgsNBApTtMqhhk8OHA0MFhhUrbDNlra/Tx0HHVgoOTomLSZXVltRWF1fCRcPEVJf
    '''
    param = ('user=12345,web,web,web&requester=localhost&req=1&rid=MUSIC_' +
              str(rid))
    str_bytes = xor_bytes(param.encode())
    output = base64.encodebytes(str_bytes).decode()
    return output.replace('\n', '')

def decode_lrc_url(url):
    str_bytes = base64.decodebytes(url.encode())
    output = xor_bytes(str_bytes)
    return output.decode('gb18030')

def json_loads_single(s):
    '''Actually this is not a good idea. '''
    return json.loads(
            s.replace('"', '''\\"''').replace("'", '"').replace('\t', ''))

def encode_uri(text):
    return parse.quote(text, safe='~@#$&()*!+=:;,.?/\'')

def parse_radio_songs(txt):
    if not txt:
        return None
    lines = txt.splitlines()
    if not lines or lines[0] != 'success':
        return None
    songs = []
    for line in lines[2:]:
        info = line.split('\t')
        songs.append({
            'rid': info[0],
            'artist': info[1],
            'name': info[2],
            'artistid': 0,
            'album': '',
            'albumid': 0,
            })
    return songs

def iconvtag(song_path, song):
    def use_id3():
        audio = MP3(song_path, ID3=EasyID3)
        audio.clear()
        audio['title'] = song['name']
        audio['artist'] = song['artist']
        audio['album'] = song['album']
        audio.save()

    def use_ape():
        audio = APEv2File(song_path)
        if not audio.tags:
            audio.add_tags()
        audio.tags.clear()
        audio.tags['title'] = song['name']
        audio.tags['artist'] = song['artist']
        audio.tags['album'] = song['album']
        audio.save()

    # Do nothing if mutagenx is not imported
    if not mutagenx_imported:
        return

    ext = os.path.splitext(song_path)[1].lower()
    try:
        if ext == '.mp3':
            use_id3()
        elif ext == '.ape':
            use_ape()
    except Exception as e:
        print('Error in Utils.iconvtag():', e)


def open_folder(folder):
    try:
        subprocess.call(['xdg-open', folder, ])
    except FileNotFoundError as e:
        print(e)

########NEW FILE########
__FILENAME__ = Widgets

# Copyright (C) 2013-2014 LiuLang <gsushzhsosgsu@gmail.com>

# Use of this source code is governed by GPLv3 license that can be found
# in the LICENSE file.

import html
from html.parser import HTMLParser
import os
from gi.repository import Gdk
from gi.repository import GdkPixbuf
from gi.repository import GLib
from gi.repository import Gtk


from kuwo import Config

_ = Config._

def unescape(tooltip):
    html_parser = HTMLParser()
    return html_parser.unescape(html_parser.unescape(tooltip))

def escape(tooltip):
    return GLib.markup_escape_text(tooltip.replace('<br>', '\n'))

def short_str(_str, length=10):
    if len(_str) > length:
        return _str[:length-2] + '..'
    return _str

def reach_scrolled_bottom(adj):
    return adj.get_upper() - adj.get_page_size() - adj.get_value() < 80

def short_tooltip(tooltip, length=10):
    return short_str(escape(tooltip), length)

def set_tooltip(head, body=''):
    return '<b>{0}</b>\n\n{1}'.format(
            escape(unescape(head)), escape(unescape(body)))

def set_tooltip_with_song_tips(head, tip):
    songs = tip.split(';')
    results = []
    fmt = '{0}   <small>by {1}</small>'
    for song in songs:
        if len(song) < 5:
            continue
        item = song.split('@')
        try:
            results.append(fmt.format(escape(item[1]), escape(item[3])))
        except IndexError as e:
            continue
    return '<b>{0}</b>\n\n{1}'.format(escape(head), '\n'.join(results))

def song_row_to_dict(song_row, start=1):
    song = {
            'name': song_row[start],
            'artist': song_row[start+1],
            'album': song_row[start+2],
            'rid': song_row[start+3],
            'artistid': song_row[start+4],
            'albumid': song_row[start+5],
            }
    return song

def song_dict_to_row(song):
    # with filepath
    song_row = [song['name'], song['artist'], song['album'], 
            int(song['rid']), int(song['artistid']), int(song['albumid']),]
    return song_row

def tree_append_items(tree, items):
    '''A faster way to append many items to GtkTreeModel at a time.

    When appending many items to a model , app will lose response, which
    is really annoying.
    From:http://faq.pygtk.org/index.py?req=show&file=faq13.043.htp
    @tree a GtkTreeView
    @items a list of items
    '''
    def append_generator(step=100):
        n = 0
        tree.freeze_child_notify()
        for item in items:
            model.append(item)
            n += 1
            if (n % step) == 0:
                tree.thaw_child_notify()
                yield True
                tree.freeze_child_notify()
        # stop idle_add()
        tree.thaw_child_notify()
        yield False

    model = tree.get_model()
    loader = append_generator()
    GLib.idle_add(loader.__next__)


class ListRadioButton(Gtk.RadioButton):
    def __init__(self, label, last_button=None):
        super().__init__(label)
        self.props.draw_indicator = False
        if last_button:
            self.join_group(last_button)
        # it might need a class name.

class BoldLabel(Gtk.Label):
    def __init__(self, label):
        super().__init__('<b>{0}</b>'.format(label))
        self.set_use_markup(True)
        self.props.halign = Gtk.Align.START
        self.props.xalign = 0
        #self.props.margin_bottom = 10

class FolderChooser(Gtk.Box):
    def __init__(self, parent):
        super().__init__(spacing=5)
        self.parent = parent
        self.filepath = os.environ['HOME']

        self.entry = Gtk.Entry()
        self.entry.set_text(self.filepath)
        self.entry.props.editable = False
        self.entry.props.can_focus = False
        self.entry.props.width_chars = 30
        self.pack_start(self.entry, True, True, 0)

        choose_button = Gtk.Button('...')
        choose_button.connect('clicked', self.on_choose_button_clicked)
        self.pack_start(choose_button, False, False, 0)

    def set_filename(self, filepath):
        self.filepath = filepath
        self.entry.set_text(filepath)

    def get_filename(self):
        return self.filepath
    
    def on_choose_button_clicked(self, button):
        def on_dialog_file_activated(dialog):
            self.filepath = dialog.get_filename()
            self.entry.set_text(self.filepath)
            dialog.destroy()

        dialog = Gtk.FileChooserDialog(_('Choose a Folder'), self.parent,
                Gtk.FileChooserAction.SELECT_FOLDER,
                (Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
                    Gtk.STOCK_OK, Gtk.ResponseType.OK))

        dialog.connect('file-activated', on_dialog_file_activated)
        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            on_dialog_file_activated(dialog)
            return
        dialog.destroy()

class TreeViewColumnText(Gtk.TreeViewColumn):
    def __init__(self, *args, **keys):
        super().__init__(*args, **keys)
        # This is the best option, but Gtk raises some Exceptions like:
        # (kuwo.py:14225): Gtk-CRITICAL **: _gtk_tree_view_column_autosize: assertion `GTK_IS_TREE_VIEW (tree_view)' failed
        # I don't know why that happens and how to fix it.  
        #self.props.sizing = Gtk.TreeViewColumnSizing.AUTOSIZE
        self.props.sizing = Gtk.TreeViewColumnSizing.GROW_ONLY
        self.props.expand = True
        self.props.max_width = 280


class TreeViewColumnIcon(Gtk.TreeViewColumn):
    def __init__(self, *args, **keys):
        super().__init__(*args, **keys)
        self.props.sizing = Gtk.TreeViewColumnSizing.FIXED
        self.props.fixed_width = 20


class ControlBox(Gtk.Box):
    def __init__(self, liststore, app, select_all=True):
        super().__init__(spacing=5)
        self.liststore = liststore
        self.app = app

        self.button_selectall = Gtk.ToggleButton(_('Select All'))
        self.button_selectall.set_active(select_all)
        self.select_all_sid = self.button_selectall.connect('toggled', 
                self.on_button_selectall_toggled)
        self.pack_start(self.button_selectall, False, False, 0)

        button_play = Gtk.Button(_('Play'))
        button_play.connect('clicked', self.on_button_play_clicked)
        self.pack_start(button_play, False, False, 0)

        # GtkMenuButton is new in Gtk3.6
        #button_add = Gtk.MenuButton(_('Add to Playlist'))
        #button_add.set_menu_model(self.app.playlist.playlist_menu_model)
        button_add = Gtk.Button(_('Add to Playlist'))
        button_add.connect('clicked', self.on_button_add_clicked)
        self.pack_start(button_add, False, False, 0)

        button_cache = Gtk.Button(_('Cache'))
        button_cache.connect('clicked', self.on_button_cache_clicked)
        self.pack_start(button_cache, False, False, 0)

    def select_all(self):
        '''Activate select_all button'''
        self.button_selectall.handler_block(self.select_all_sid)
        self.button_selectall.set_active(True)
        self.button_selectall.handler_unblock(self.select_all_sid)

    def on_button_selectall_toggled(self, btn):
        toggled = btn.get_active()
        for song in self.liststore:
            song[0] = toggled

    def on_button_play_clicked(self, btn):
        songs = [song_row_to_dict(s) for s in self.liststore if s[0]]
        self.app.playlist.play_songs(songs)

    def on_button_add_clicked(self, btn):
        songs = [song_row_to_dict(s) for s in self.liststore if s[0]]
        self.app.playlist.popup_playlist_menu(btn, songs)

    def on_button_cache_clicked(self, btn):
        songs = [song_row_to_dict(s) for s in self.liststore if s[0]]
        self.app.playlist.cache_songs(songs)

class MVControlBox(Gtk.Box):
    def __init__(self, liststore, app):
        super().__init__()
        self.liststore = liststore
        self.app = app

        button_add = Gtk.Button(_('Add to Playlist'))
        button_add.connect('clicked', self.on_button_add_clicked)
        self.pack_start(button_add, False, False, 0)

    def on_button_add_clicked(self, btn):
        songs = [song_row_to_dict(s) for s in self.liststore]
        self.app.playlist.popup_playlist_menu(btn, songs)


class IconView(Gtk.IconView):
    def __init__(self, liststore, info_pos=3, tooltip=None):
        super().__init__(model=liststore)

        # liststore:
        # 0 - logo
        # 1 - name
        # 2 - id
        # 3 - info
        # 4 - tooltip
        self.set_pixbuf_column(0)
        if tooltip is not None:
            self.set_tooltip_column(tooltip)
        self.props.item_width = 150

        cell_name = Gtk.CellRendererText()
        cell_name.set_alignment(0.5, 0.5)
        cell_name.props.max_width_chars = 15
        #cell_name.props.width_chars = 15
        self.pack_start(cell_name, True)
        self.add_attribute(cell_name, 'text', 1)

        if info_pos is not None:
            cell_info = Gtk.CellRendererText()
            fore_color = Gdk.RGBA(red=136/256, green=139/256, blue=132/256)
            cell_info.props.foreground_rgba = fore_color
            cell_info.props.size_points = 9
            cell_info.props.max_width_chars = 18
            #cell_info.props.width_chars = 18
            cell_info.set_alignment(0.5, 0.5)
            self.pack_start(cell_info, True)
            self.add_attribute(cell_info, 'text', info_pos)


class TreeViewSongs(Gtk.TreeView):
    def __init__(self, liststore, app):
        super().__init__(model=liststore)
        self.set_headers_visible(False)
        self.liststore = liststore
        self.app = app

        checked = Gtk.CellRendererToggle()
        checked.connect('toggled', self.on_song_checked)
        column_check = Gtk.TreeViewColumn('Checked', checked, active=0)
        self.append_column(column_check)
        name = Gtk.CellRendererText()
        col_name = TreeViewColumnText('Name', name, text=1)
        self.append_column(col_name)
        artist = Gtk.CellRendererText()
        col_artist = TreeViewColumnText('Artist', artist, text=2)
        self.append_column(col_artist)
        album = Gtk.CellRendererText()
        col_album = TreeViewColumnText('Album', album, text=3)
        self.append_column(col_album)
        play = Gtk.CellRendererPixbuf(pixbuf=app.theme['play'])
        col_play = TreeViewColumnIcon('Play', play)
        self.append_column(col_play)
        add = Gtk.CellRendererPixbuf(pixbuf=app.theme['add'])
        col_add = TreeViewColumnIcon('Add', add)
        self.append_column(col_add)
        cache = Gtk.CellRendererPixbuf(pixbuf=app.theme['cache'])
        col_cache = TreeViewColumnIcon('Cache', cache)
        self.append_column(col_cache)

        self.connect('row_activated', self.on_row_activated)
        self.connect('button-press-event', self.on_button_pressed)

    def on_song_checked(self, widget, path):
        self.liststore[path][0] = not self.liststore[path][0]

    def on_button_pressed(self, treeview, event):
        path_info = treeview.get_path_at_pos(event.x, event.y)
        if not path_info:
            return
        path, column, cell_x, cell_y = path_info
        song = song_row_to_dict(self.liststore[path])
        index = self.get_columns().index(column)
        if index == 4:
            self.app.playlist.play_song(song)
        elif index == 5:
            self.app.playlist.add_song_to_playlist(song)
        elif index == 6:
            self.app.playlist.cache_song(song)


    def on_row_activated(self, treeview, path, column):
        song = song_row_to_dict(self.liststore[path])
        index = self.get_columns().index(column)
        if index == 1:
            self.app.playlist.play_song(song)
        elif index == 2:
            if not song['artist']:
                print('artist is empty, no searching')
                return
            self.app.search.search_artist(song['artist'])
        elif index == 3:
            if not song['album']:
                print('album is empty, no searching')
                return
            self.app.search.search_album(song['album'])


def network_error(parent, msg):
    dialog = Gtk.MessageDialog(
            parent, Gtk.DialogFlags.MODAL,
            Gtk.MessageType.ERROR, Gtk.ButtonsType.CLOSE, msg)
    dialog.format_secondary_text(
            _('Please check network connection and try again'))
    dialog.run()
    dialog.destroy()

def filesystem_error(parent, path):
    msg = _('Failed to open file or direcotry')
    dialog = Gtk.MessageDialog(parent, Gtk.DialogFlags.MODAL,
            Gtk.MessageType.ERROR, Gtk.ButtonsType.CLOSE, msg)
    dialog.format_secondary_text(
            _('Unable to access {0}').format(path))
    dialog.run()
    dialog.destroy()

########NEW FILE########
