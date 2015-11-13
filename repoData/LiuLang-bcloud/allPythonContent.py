__FILENAME__ = App
# Copyright (C) 2014 LiuLang <gsushzhsosgsu@gmail.com>
# Use of this source code is governed by GPLv3 license that can be found
# in http://www.gnu.org/licenses/gpl-3.0.html

import os
import random
import sys
sys.path.insert(0, os.path.dirname(__file__))
import time

from gi.repository import Gdk
from gi.repository import Gio
from gi.repository import GLib
from gi.repository import GObject
from gi.repository import Gtk
from gi.repository import Notify

import Config
Config.check_first()
_ = Config._
import gutil
import util
from MimeProvider import MimeProvider
from PreferencesDialog import PreferencesDialog

from CategoryPage import *
from CloudPage import CloudPage
from DownloadPage import DownloadPage
from HomePage import HomePage
from PreferencesDialog import PreferencesDialog
from SigninDialog import SigninDialog
from TrashPage import TrashPage
from UploadPage import UploadPage

if Gtk.MAJOR_VERSION <= 3 and Gtk.MINOR_VERSION < 10:
    GObject.threads_init()
(ICON_COL, NAME_COL, TOOLTIP_COL, COLOR_COL) = list(range(4))
BLINK_DELTA = 250    # 字体闪烁间隔, 250 miliseconds 
BLINK_SUSTAINED = 3  # 字体闪烁持续时间, 5 seconds


class App:

    profile = None
    cookie = None
    tokens = None
    default_dark_color = Gdk.RGBA(0.9, 0.9, 0.9, 1)
    default_light_color = Gdk.RGBA(0.1, 0.1, 0.1, 1)
    default_color = default_dark_color
    status_icon = None

    def __init__(self):
        self.app = Gtk.Application.new(Config.DBUS_APP_NAME, 0)
        self.app.connect('startup', self.on_app_startup)
        self.app.connect('activate', self.on_app_activate)
        self.app.connect('shutdown', self.on_app_shutdown)

    def on_app_startup(self, app):
        self.icon_theme = Gtk.IconTheme.get_default()
        #self.icon_theme.append_search_path(Config.ICON_PATH)
        self.mime = MimeProvider(self)
        self.color_schema = Config.load_color_schema()
        self.set_dark_theme(True)

        self.window = Gtk.ApplicationWindow.new(application=app)
        self.window.set_default_size(*gutil.DEFAULT_PROFILE['window-size'])
        self.window.set_title(Config.APPNAME)
        self.window.props.hide_titlebar_when_maximized = True
        self.window.set_icon_name(Config.NAME)
        self.window.connect('check-resize', self.on_main_window_resized)
        self.window.connect('delete-event', self.on_main_window_deleted)
        app.add_window(self.window)

        # set drop action
        targets = [
            ['text/plain', Gtk.TargetFlags.OTHER_APP, 0],
            ['*.*', Gtk.TargetFlags.OTHER_APP, 1]]
        target_list =[Gtk.TargetEntry.new(*t) for t in targets]
        self.window.drag_dest_set(
            Gtk.DestDefaults.ALL, target_list, Gdk.DragAction.COPY)
        self.window.connect(
            'drag-data-received', self.on_main_window_drag_data_received)

        app_menu = Gio.Menu.new()
        app_menu.append(_('Preferences'), 'app.preferences')
        app_menu.append(_('Sign out'), 'app.signout')
        app_menu.append(_('About'), 'app.about')
        app_menu.append(_('Quit'), 'app.quit')
        app.set_app_menu(app_menu)

        preferences_action = Gio.SimpleAction.new('preferences', None)
        preferences_action.connect(
            'activate', self.on_preferences_action_activated)
        app.add_action(preferences_action)
        signout_action = Gio.SimpleAction.new('signout', None)
        signout_action.connect('activate', self.on_signout_action_activated)
        app.add_action(signout_action)
        about_action = Gio.SimpleAction.new('about', None)
        about_action.connect('activate', self.on_about_action_activated)
        app.add_action(about_action)
        quit_action = Gio.SimpleAction.new('quit', None)
        quit_action.connect('activate', self.on_quit_action_activated)
        app.add_action(quit_action)

        paned = Gtk.Paned()
        #paned.props.position = 15
        self.window.add(paned)

        left_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        paned.add1(left_box)
        paned.child_set_property(left_box, 'shrink', False)
        paned.child_set_property(left_box, 'resize', False)

        nav_window = Gtk.ScrolledWindow()
        nav_window.props.hscrollbar_policy = Gtk.PolicyType.NEVER
        left_box.pack_start(nav_window, True, True, 0)

        # icon_name, disname, tooltip, color
        self.nav_liststore = Gtk.ListStore(str, str, str, Gdk.RGBA)
        nav_treeview = Gtk.TreeView(model=self.nav_liststore)
        self.nav_selection = nav_treeview.get_selection()
        nav_treeview.props.headers_visible = False
        nav_treeview.set_tooltip_column(TOOLTIP_COL)
        icon_cell = Gtk.CellRendererPixbuf()
        icon_cell.props.xalign = 1
        icon_col = Gtk.TreeViewColumn('Icon', icon_cell, icon_name=ICON_COL)
        icon_col.props.fixed_width = 40
        nav_treeview.append_column(icon_col)
        name_cell = Gtk.CellRendererText()
        name_col = Gtk.TreeViewColumn(
                'Places', name_cell, text=NAME_COL, foreground_rgba=COLOR_COL)
        nav_treeview.append_column(name_col)
        nav_selection = nav_treeview.get_selection()
        nav_selection.connect('changed', self.on_nav_selection_changed)
        nav_window.add(nav_treeview)

        self.progressbar = Gtk.ProgressBar()
        self.progressbar.set_show_text(True)
        self.progressbar.set_text(_('Unknown'))
        left_box.pack_end(self.progressbar, False, False, 0)

        self.notebook = Gtk.Notebook()
        self.notebook.props.show_tabs = False
        paned.add2(self.notebook)

    def on_app_activate(self, app):
        self.window.show_all()
        if not self.profile:
            self.show_signin_dialog()

    def on_app_shutdown(self, app):
        '''Dump profile content to disk'''
        if self.profile:
            self.upload_page.on_destroy()
            self.download_page.on_destroy()

    def run(self, argv):
        self.app.run(argv)

    def quit(self):
        self.app.quit()

    def set_dark_theme(self, status):
        settings = Gtk.Settings.get_default()
        settings.props.gtk_application_prefer_dark_theme = status
        if status:
            self.default_color = self.default_dark_color
        else:
            self.default_color = self.default_light_color
        if self.profile:
            for row in self.nav_liststore:
                row[3] = self.default_color

    def show_signin_dialog(self, auto_signin=True):
        self.profile = None
        signin = SigninDialog(self, auto_signin=auto_signin)
        signin.run()
        signin.destroy()

        if self.profile:
            self.init_notebook()
            self.notebook.connect('switch-page', self.on_notebook_switched)
            self.init_status_icon()
            self.init_notify()
            self.set_dark_theme(self.profile['use-dark-theme'])

            if self.profile['first-run']:
                self.profile['first-run'] = False
                preferences = PreferencesDialog(self)
                preferences.run()
                preferences.destroy()
                gutil.dump_profile(self.profile)

            self.home_page.load()
            self.switch_page(self.home_page)
            return
        self.quit()

    def on_main_window_resized(self, window):
        if self.profile:
            self.profile['window-size'] = window.get_size()

    def on_main_window_deleted(self, window, event):
        if self.profile and self.profile['use-status-icon']:
            window.hide()
        else:
            self.quit()
        return True

    def on_main_window_drag_data_received(self, window, drag_context, x, y,
                                          data, info, time):
        uris = data.get_text()
        source_paths = util.uris_to_paths(uris)
        if source_paths and self.profile:
            self.upload_page.add_file_tasks(source_paths)

    def on_preferences_action_activated(self, action, params):
        if self.profile:
            dialog = PreferencesDialog(self)
            dialog.run()
            dialog.destroy()
            if self.profile:
                gutil.dump_profile(self.profile)
                if self.profile['use-status-icon'] and not self.status_icon:
                    self.init_status_icon()
                self.set_dark_theme(self.profile['use-dark-theme'])

    def on_signout_action_activated(self, action, params):
        '''在退出登录前, 应该保存当前用户的所有数据'''
        if self.profile:
            self.upload_page.pause_tasks()
            self.download_page.pause_tasks()
            self.show_signin_dialog(auto_signin=False)

    def on_about_action_activated(self, action, params):
        dialog = Gtk.AboutDialog()
        dialog.set_modal(True)
        dialog.set_transient_for(self.window)
        dialog.set_program_name(Config.APPNAME)
        dialog.set_logo_icon_name(Config.NAME)
        dialog.set_version(Config.VERSION)
        dialog.set_comments(Config.DESCRIPTION)
        dialog.set_copyright(Config.COPYRIGHT)
        dialog.set_website(Config.HOMEPAGE)
        dialog.set_license_type(Gtk.License.GPL_3_0)
        dialog.set_authors(Config.AUTHORS)
        dialog.run()
        dialog.destroy()

    def on_quit_action_activated(self, action, params):
        self.quit()

    def update_quota(self, quota_info, error=None):
        '''更新网盘容量信息'''
        if not quota_info or quota_info['errno'] != 0:
            return
        used = quota_info['used']
        total = quota_info['total']
        used_size = util.get_human_size(used)[0]
        total_size = util.get_human_size(total)[0]
        self.progressbar.set_text(used_size + ' / ' + total_size)
        self.progressbar.set_fraction(used / total)

    def init_notebook(self):
        def append_page(page):
            self.notebook.append_page(page, Gtk.Label.new(page.disname))
            self.nav_liststore.append([
                page.icon_name, page.disname,
                page.tooltip, self.default_color,
                ])

        self.default_color = self.get_default_color()
        self.nav_liststore.clear()
        children = self.notebook.get_children()
        for child in children:
            self.notebook.remove(child)

        self.home_page = HomePage(self)
        append_page(self.home_page)
        self.picture_page = PicturePage(self)
        append_page(self.picture_page)
        self.doc_page = DocPage(self)
        append_page(self.doc_page)
        self.video_page = VideoPage(self)
        append_page(self.video_page)
        self.bt_page = BTPage(self)
        append_page(self.bt_page)
        self.music_page = MusicPage(self)
        append_page(self.music_page)
        self.other_page = OtherPage(self)
        append_page(self.other_page)
        self.trash_page = TrashPage(self)
        append_page(self.trash_page)
        self.cloud_page = CloudPage(self)
        append_page(self.cloud_page)
        self.download_page = DownloadPage(self)
        append_page(self.download_page)
        self.upload_page = UploadPage(self)
        append_page(self.upload_page)

        self.notebook.show_all()

    def reload_current_page(self, *args, **kwds):
        '''重新载入当前页面.
        
        所有的页面都应该实现reload()方法.
        '''
        index = self.notebook.get_current_page()
        self.notebook.get_nth_page(index).reload()

    def switch_page_by_index(self, index):
        self.notebook.set_current_page(index)

    def switch_page(self, page):
        for index, p in enumerate(self.notebook):
            if p == page:
                self.nav_selection.select_iter(self.nav_liststore[index].iter)
                #self.notebook.set_current_page(index)
                break

    def on_notebook_switched(self, notebook, page, index):
        if page.first_run:
            page.first_run = False
            page.load()

    def on_nav_selection_changed(self, nav_selection):
        model, iter_ = nav_selection.get_selected()
        if not iter_:
            return
        path = model.get_path(iter_)
        index = path.get_indices()[0]
        self.switch_page_by_index(index)

    def init_status_icon(self):
        if (self.profile and self.profile['use-status-icon'] and
                not self.status_icon):
            self.status_icon = Gtk.StatusIcon()
            self.status_icon.set_from_icon_name(Config.NAME)
            # left click
            self.status_icon.connect(
                    'activate', self.on_status_icon_activate)
            # right click
            self.status_icon.connect(
                    'popup_menu', self.on_status_icon_popup_menu)
        else:
            self.status_icon = None

    def on_status_icon_activate(self, status_icon):
        if self.window.props.visible:
            self.window.hide()
        else:
            self.window.present()

    def on_status_icon_popup_menu(self, status_icon, event_button,
                                event_time):
        menu = Gtk.Menu()
        show_item = Gtk.MenuItem.new_with_label(_('Show App'))
        show_item.connect('activate', self.on_status_icon_show_app_activate)
        menu.append(show_item)

        sep_item = Gtk.SeparatorMenuItem()
        menu.append(sep_item)

        pause_upload_item = Gtk.MenuItem.new_with_label(
                _('Pause Uploading Tasks'))
        pause_upload_item.connect(
                'activate', lambda *args: self.upload_page.pause_tasks())
        menu.append(pause_upload_item)

        pause_download_item = Gtk.MenuItem.new_with_label(
                _('Pause Downloading Tasks'))
        pause_download_item.connect(
                'activate', lambda *args: self.download_page.pause_tasks())
        menu.append(pause_download_item)

        sep_item = Gtk.SeparatorMenuItem()
        menu.append(sep_item)

        quit_item = Gtk.MenuItem.new_with_label(_('Quit'))
        quit_item.connect('activate', self.on_status_icon_quit_activate)
        menu.append(quit_item)

        menu.show_all()
        menu.popup(None, None,
                lambda a,b: Gtk.StatusIcon.position_menu(menu, status_icon),
                None, event_button, event_time)

    def on_status_icon_show_app_activate(self, menuitem):
        self.window.present()

    def on_status_icon_quit_activate(self, menuitem):
        self.quit()

    # Open API
    def blink_page(self, page):
        def blink():
            row[COLOR_COL] = random.choice(self.color_schema)
            if time.time() - start_time > BLINK_SUSTAINED:
                row[COLOR_COL] = self.default_color
                return False
            return True
        
        start_time = time.time()
        for index, p in enumerate(self.notebook):
            if p == page:
                break
        row = self.nav_liststore[index]
        GLib.timeout_add(BLINK_DELTA, blink)

    def get_default_color(self):
        context = self.window.get_style_context()
        return context.get_color(Gtk.StateFlags.NORMAL)

    # Open API
    def update_clipboard(self, text):
        '''将文本复制到系统剪贴板里面'''
        clipboard = Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD)
        clipboard.set_text(text, -1)
        self.toast(_('{0} copied to clipboard'.format(text)))

    def init_notify(self):
        self.notify = None
        if self.profile['use-notify']:
            status = Notify.init(Config.APPNAME)
            if not status:
                return
            self.notify = Notify.Notification.new(
                    Config.APPNAME, '', Config.NAME)

    # Open API
    def toast(self, text):
        '''在用户界面显示一个消息通知.

        可以使用系统提供的Notification工具, 也可以在窗口的最下方滚动弹出
        这个消息
        '''
        if self.notify:
            self.notify.update(Config.APPNAME, text, Config.NAME)
            self.notify.show()

########NEW FILE########
__FILENAME__ = auth

# Copyright (C) 2013-2014 LiuLang <gsushzhsosgsu@gmail.com>
# Use of this source code is governed by GPLv3 license that can be found
# in http://www.gnu.org/licenses/gpl-3.0.html

'''
这个模块主要是用于从百度服务器取得cookie授权.
'''

import json
import os
import random
import re
import sys
import urllib.request

sys.path.insert(0, os.path.dirname(__file__))
import const
import encoder
from RequestCookie import RequestCookie
import net
import util


def get_ppui_logintime():
    '''ppui_ligintime 这个字段, 是一个随机数.'''
    return str(random.randint(25000, 28535))

def get_BAIDUID():
    '''获取一个cookie - BAIDUID.

    这里, 我们访问百度首页, 返回的response header里面有我们需要的cookie
    '''
    req = net.urlopen(const.BAIDU_URL)
    if req:
        return req.headers.get_all('Set-Cookie')
    else:
        return None

def get_token(cookie):
    '''获取一个页面访问的token, 这里需要之前得到的BAIDUID 这个cookie值

    这个token的有效期还不确定.
    '''
    url = ''.join([
        const.PASSPORT_URL,
        '?getapi&tpl=mn&apiver=v3',
        '&tt=', util.timestamp(),
        '&class=login&logintype=dialogLogin',
        #'&callback=bd__cbs__d1ypgy',
        ])
    req = net.urlopen(url, headers={'Cookie': cookie.header_output()})
    if req:
        content = req.data
        content = content.decode().replace("'", '"')
        content_obj = json.loads(content)
        return content_obj['data']['token']
    else:
        return None

def get_UBI(cookie, token):
    '''检查登录历史, 可以获得一个Cookie - UBI.'''
    url = ''.join([
        const.PASSPORT_URL,
        '?loginhistory',
        '&token=', token,
        '&tpl=pp&apiver=v3',
        '&tt=', util.timestamp(),
        #'&callback=bd__cbs__7sxvvm',
        ])
    req = net.urlopen(url, headers={'Cookie': cookie.header_output()})
    if req:
        return req.headers.get_all('Set-Cookie')
    else:
        return None


def check_login(cookie, token, username):
    '''进行登录验证, 主要是在服务器上验证这个帐户的状态.

    如果帐户不存在, 或者帐户异常, 就不需要再进行最后一步的登录操作了.
    这一步有可能需要输入验证码.
    @return 返回errInfo.no, 如果为0, 表示一切正常, 可以登录.
    '''
    url = ''.join([
        const.PASSPORT_URL,
        '?logincheck',
        '&token=', token,
        '&tpl=mm&apiver=v3',
        '&tt=', util.timestamp(),
        '&username=', encoder.encode_uri_component(username),
        '&isphone=false',
        ])
    req = net.urlopen(url, headers={'Cookie': cookie.header_output()})
    if req:
        return json.loads(req.data.decode())
    else:
        return None

def get_signin_vcode(cookie, codeString):
    '''获取登录时的验证码图片.


    codeString - 调用check_login()时返回的codeString.
    '''
    url = ''.join([
        const.PASSPORT_BASE,
        'cgi-bin/genimage?',
        codeString,
        ])
    req = net.urlopen(url, headers={'Cookie': cookie.header_output()})
    if req:
        return req.data
    else:
        return None

def refresh_sigin_vcode(cookie, token, vcodetype):
    '''刷新验证码.

    vcodetype - 在调用check_login()时返回的vcodetype.
    '''
    url = ''.join([
        const.PASSPORT_BASE,
        'v2/?reggetcodestr',
        '&token=', token,
        '&tpl=netdisk&apiver=v3',
        '&tt=', util.timestamp(),
        '&fr=ligin',
        '&vcodetype=', vcodetype,
        ])
    req = net.urlopen(url, headers={'Cookie': cookie.header_output()})
    if req:
        try:
            return json.loads(req.data.decode('gb18030'))
        except ValueError as e:
            print(e)
    return None

def get_bduss(cookie, token, username, password, verifycode='', codeString=''):
    '''获取最重要的登录cookie, 拿到这个cookie后, 就得到了最终的访问授权.

    cookie     - BAIDUID 这个cookie.
    token      - 使用get_token()得到的token值.
    username   - 用户名
    password   - 明文密码
    verifycode - 用户根据图片输入的四位验证码, 可以为空
    codeString - 获取验证码图片时用到的codeString, 可以为空

    @return (status, info). 其中, status表示返回的状态:
      0 - 正常, 这里, info里面存放的是auth_cookie
     -1 - 未知异常
      4 - 密码错误
    257 - 需要输入验证码, 此时info里面存放着(vcodetype, codeString))
    '''
    url = const.PASSPORT_URL + '?login'
    data = ''.join([
        'staticpage=http%3A%2F%2Fwww.baidu.com%2Fcache%2Fuser%2Fhtml%2Fv3Jump.html',
        '&charset=UTF-8',
        '&token=', token,
        '&tpl=mn&apiver=v3',
        '&tt=', util.timestamp(),
        '&codestring=', codeString,
        '&safeflg=0&u=https%3A%2F%2Fpassport.baidu.com%2F',
        '&isPhone=false&quick_user=0',
        '&loginmerge=true&logintype=basicLogin&logLoginType=pc_loginBasic',
        '&username=', encoder.encode_uri_component(username),
        '&password=', encoder.encode_uri_component(password),
        '&verifycode=', verifycode,
        '&mem_pass=on',
        '&ppui_logintime=', get_ppui_logintime(),
        '&callback=parent.bd__pcbs__cb',
        ])

    req = net.urlopen(url, headers={
        'Cookie': cookie.header_output(),
        'Content-type': const.CONTENT_FORM,
        'Accept': const.ACCEPT_HTML,
        }, data=data.encode())
    if req:
        auth_cookie = req.headers.get_all('Set-Cookie')
        if auth_cookie:
            return (0, auth_cookie)
        resp_content= req.data.decode()
        match = re.findall('"(err_no[^"]+)"', resp_content)
        if len(match) != 1:
            return (-1, None)
        query = dict(urllib.parse.parse_qsl(match[0]))
        err_no = int(query.get('err_no', '-1'))
        if err_no != 257:
            return (err_no, None)
        vcodetype = query.get('vcodetype', '')
        codeString = query.get('codeString', '')
        if vcodetype and codeString:
            return (257, (vcodetype, codeString))
        return (-1, None)
    else:
        return (-1, None)

def parse_bdstoken(content):
    '''从页面中解析出bdstoken等信息.
    
    这些信息都位于页面底部的<script>, 只有在授权后的页面中才出现.
    这里, 为了保证兼容性, 就不再使用cssselect模块解析了.

    @return 返回一个dict, 里面包含bdstoken, cktoken, sysUID这三项.
    '''
    auth = {'bdstoken': '', 'cktoken': '', 'sysUID': ''}
    uid_re = re.compile('sysUID="([^"]+)"')
    uid_match = uid_re.search(content)
    if uid_match:
        auth['sysUID'] = uid_match.group(1)

    bds_re = re.compile('bdstoken="([^"]+)"')
    bds_match = bds_re.search(content)
    if bds_match:
        auth['bdstoken'] = bds_match.group(1)

    ck_re = re.compile('cktoken="([^"]+)"')
    ck_match = ck_re.search(content)
    if ck_match:
        auth['cktoken'] = ck_match.group(1)
    return auth

def get_bdstoken(cookie):
    '''从/disk/home页面获取bdstoken等token信息

    这些token对于之后的请求非常重要.
    '''
    url = const.PAN_REFERER
    req = net.urlopen(url, headers={'Cookie': cookie.header_output()})
    if req:
        return parse_bdstoken(req.data.decode())
    else:
        return None

def get_public_key(cookie, tokens):
    '''获取一个RSA公钥, 用于加密用户的密码'''
    url = ''.join([
        const.PASSPORT_BASE,
        'v2/getpublickey?',
        'token=', tokens['token'],
        '&tpl=pp&apiver=v3',
        '&tt=', util.timestamp(),
        ])
    req = net.urlopen(url, headers={'Cookie': cookie.header_output()})
    if req:
        # Fix the non-standard JSON object
        content = req.data.decode().replace("'", '"').replace('\\r', '')
        try:
            return json.loads(content)
        except ValueError as e:
            print(e)
    return None

def get_rsa_bduss(cookie, token, username, password, public_key, rsakey,
                  verifycode='', codeString=''):
    '''使用RSA加密后的密码来进行认证.

    cookie     - BAIDUID 这个cookie.
    token      - 使用get_token()得到的token值.
    username   - 用户名
    password   - 明文密码
    public_key - RSA公钥, 在get_public_key()中得到的
    rsakey     - get_public_key()返回的对象中, 包含的'key'
    verifycode - 用户根据图片输入的四位验证码, 可以为空
    codeString - 获取验证码图片时用到的codeString, 可以为空
    '''
    url = const.PASSPORT_URL + '?login'
    msg = util.RSA_encrypt(public_key, password)
    data = ''.join([
        'staticpage=http%3A%2F%2Fwww.baidu.com%2Fcache%2Fuser%2Fhtml%2Fv3Jump.html',
        '&charset=UTF-8',
        '&token=', token,
        '&tpl=mn&subpro=&apiver=v3',
        '&tt=', util.timestamp(),
        '&codestring=', codeString,
        '&safeflg=0&u=https%3A%2F%2Fpassport.baidu.com%2F',
        '&isPhone=false&quick_user=0',
        '&loginmerge=true&logintype=basicLogin&logLoginType=pc_loginBasic',
        '&username=', encoder.encode_uri_component(username),
        '&password=', encoder.encode_uri_component(msg),
        '&rsakey=', rsakey,
        '&crypttype=12',
        '&verifycode=', verifycode,
        '&mem_pass=on',
        '&ppui_logintime=', get_ppui_logintime(),
        '&callback=parent.bd__pcbs__cb',
        ])
    req = net.urlopen(url, headers={
        'Cookie': cookie.header_output(),
        'Content-type': const.CONTENT_FORM,
        'Accept': const.ACCEPT_HTML,
        }, data=data.encode())
    if req:
        auth_cookie = req.headers.get_all('Set-Cookie')
        if auth_cookie:
            return (0, auth_cookie)
        resp_content= req.data.decode()
        match = re.findall('"(err_no[^"]+)"', resp_content)
        if len(match) != 1:
            return (-1, None)
        query = dict(urllib.parse.parse_qsl(match[0]))
        err_no = int(query.get('err_no', '-1'))
        if err_no != 257:
            return (err_no, None)
        vcodetype = query.get('vcodetype', '')
        codeString = query.get('codeString', '')
        if vcodetype and codeString:
            return (257, (vcodetype, codeString))
        return (-1, None)
    else:
        return (-1, None)

########NEW FILE########
__FILENAME__ = BTBrowserDialog

# Copyright (C) 2014 LiuLang <gsushzhsosgsu@gmail.com>
# Use of this source code is governed by GPLv3 license that can be found
# in http://www.gnu.org/licenses/gpl-3.0.html

from gi.repository import GObject
from gi.repository import Gtk
from gi.repository import Pango

from bcloud import Config
_ = Config._
from bcloud import gutil
from bcloud import pcs
from bcloud import util

CHECK_COL, NAME_COL, SIZE_COL, HUMANSIZE_COL = list(range(4))
MIN_SIZE_TO_CHECK = 2 ** 20  # 1M
CHECK_EXT = ('jpg', 'png', 'gif', 'bitttorrent')

class BTBrowserDialog(Gtk.Dialog):

    file_sha1 = ''

    def __init__(self, parent, app, title, source_url, save_path):
        '''初始化BT种子查询对话框.

        source_url - 如果是BT种子的话, 就是种子的绝对路径.
                      如果是磁链的话, 就是以magent:开头的磁链链接.
        '''
        super().__init__(
            title, app.window, Gtk.DialogFlags.MODAL,
            (Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
            Gtk.STOCK_OK, Gtk.ResponseType.OK))

        self.app = app
        self.source_url = source_url
        self.save_path = save_path

        self.set_default_response(Gtk.ResponseType.OK)
        self.set_default_size(520, 480)
        self.set_border_width(10)
        box = self.get_content_area()

        select_all_button = Gtk.ToggleButton.new_with_label(_('Select All'))
        select_all_button.props.halign = Gtk.Align.START
        select_all_button.props.margin_bottom = 5
        select_all_button.connect('toggled', self.on_select_all_toggled)
        box.pack_start(select_all_button, False, False, 0)

        scrolled_win = Gtk.ScrolledWindow()
        box.pack_start(scrolled_win, True, True, 0)

        # check, name, size, humansize
        self.liststore = Gtk.ListStore(bool, str, GObject.TYPE_INT64, str)
        self.treeview = Gtk.TreeView(model=self.liststore)
        self.treeview.set_tooltip_column(NAME_COL)
        scrolled_win.add(self.treeview)
        check_cell = Gtk.CellRendererToggle()
        check_cell.connect('toggled', self.on_check_cell_toggled)
        check_col = Gtk.TreeViewColumn(
            '', check_cell, active=CHECK_COL)
        self.treeview.append_column(check_col)
        name_cell = Gtk.CellRendererText(
                ellipsize=Pango.EllipsizeMode.END, ellipsize_set=True)
        name_col = Gtk.TreeViewColumn(_('Name'), name_cell, text=NAME_COL)
        name_col.set_expand(True)
        self.treeview.append_column(name_col)
        size_cell = Gtk.CellRendererText()
        size_col = Gtk.TreeViewColumn(
            _('Size'), size_cell, text=HUMANSIZE_COL)
        self.treeview.append_column(size_col)

        box.show_all()
        self.request_data()

    def request_data(self):
        '''在调用dialog.run()之前先调用这个函数来获取数据'''
        def on_tasks_received(info, error=None):
            if error or not info:
                return
            if 'magnet_info' in info:
                tasks = info['magnet_info']
            elif 'torrent_info' in info:
                tasks = info['torrent_info']['file_info']
                self.file_sha1 = info['torrent_info']['sha1']
            elif 'error_code' in info:
                self.app.toast(info.get('error_msg', ''))
                return
            else:
                print('unknown error:', info)
                self.app.toast(_('Unknown error occured'))
                return
            for task in tasks:
                size = int(task['size'])
                human_size = util.get_human_size(size)[0]
                select = (size > MIN_SIZE_TO_CHECK or 
                        task['file_name'].endswith(CHECK_EXT))
                self.liststore.append([
                    select,
                    task['file_name'],
                    size,
                    human_size,
                    ])

        if self.source_url.startswith('magnet'):
            gutil.async_call(
                pcs.cloud_query_magnetinfo, self.app.cookie,
                self.app.tokens, self.source_url, self.save_path,
                callback=on_tasks_received)
        else:
            gutil.async_call(
                pcs.cloud_query_sinfo, self.app.cookie, self.app.tokens,
                self.source_url, callback=on_tasks_received)

    def get_selected(self):
        '''返回选中要下载的文件的编号及sha1值, 从1开始计数.'''
        selected_idx = []
        for i, row in enumerate(self.liststore):
            if row[CHECK_COL]:
                selected_idx.append(i + 1)
        return (selected_idx, self.file_sha1)

    def on_select_all_toggled(self, button):
        status = button.get_active()
        for row in self.liststore:
            row[CHECK_COL] = status

    def on_check_cell_toggled(self, cell, tree_path):
        self.liststore[tree_path][CHECK_COL] = not self.liststore[tree_path][CHECK_COL]

########NEW FILE########
__FILENAME__ = CategoryPage

# Copyright (C) 2014 LiuLang <gsushzhsosgsu@gmail.com>
# Use of this source code is governed by GPLv3 license that can be found
# in http://www.gnu.org/licenses/gpl-3.0.html

from gi.repository import Gtk

from bcloud import Config
_ = Config._
from bcloud.IconWindow import IconWindow
from bcloud.IconWindow import TreeWindow
from bcloud import gutil
from bcloud import pcs

__all__ = [
    'CategoryPage', 'PicturePage', 'DocPage', 'VideoPage',
    'BTPage', 'MusicPage', 'OtherPage',
    ]


class CategoryPage(Gtk.Box):

    page_num = 1
    has_next = True
    first_run = True

    def __init__(self, app):
        super().__init__(orientation=Gtk.Orientation.VERTICAL)
        self.app = app

        nav_bar = Gtk.Toolbar()
        nav_bar.get_style_context().add_class(Gtk.STYLE_CLASS_MENUBAR)
        nav_bar.props.show_arrow = False
        nav_bar.props.toolbar_style = Gtk.ToolbarStyle.ICONS
        nav_bar.props.icon_size = Gtk.IconSize.LARGE_TOOLBAR
        nav_bar.props.halign = Gtk.Align.END
        self.pack_start(nav_bar, False, False, 0)

        # show loading process
        loading_button = Gtk.ToolItem()
        nav_bar.insert(loading_button, 0)
        loading_button.props.margin_right = 10
        self.loading_spin = Gtk.Spinner()
        loading_button.add(self.loading_spin)
        self.loading_spin.props.valign = Gtk.Align.CENTER
        nav_bar.child_set_property(loading_button, 'expand', True)

        # toggle view mode
        list_view_button = Gtk.ToolButton()
        list_view_button.set_label(_('ListView'))
        list_view_button.set_icon_name('list-view-symbolic')
        list_view_button.connect(
                'clicked', self.on_list_view_button_clicked)
        nav_bar.insert(list_view_button, 1)

        grid_view_button = Gtk.ToolButton()
        grid_view_button.set_label(_('ListView'))
        grid_view_button.set_icon_name('grid-view-symbolic')
        grid_view_button.connect(
                'clicked', self.on_grid_view_button_clicked)
        nav_bar.insert(grid_view_button, 2)

        self.icon_window = IconWindow(self, app)
        self.pack_end(self.icon_window, True, True, 0)

    def load(self):
        def on_load(info, error=None):
            self.loading_spin.stop()
            self.loading_spin.hide()
            if error or not info or info['errno'] != 0:
                return
            self.icon_window.load(info['info'])

        has_next = True
        self.page_num = 1
        self.loading_spin.start()
        self.loading_spin.show_all()
        gutil.async_call(
                pcs.get_category, self.app.cookie, self.app.tokens,
                self.category, self.page_num, callback=on_load)

    def load_next(self):
        def on_load_next(info, error=None):
            self.loading_spin.stop()
            self.loading_spin.hide()
            if error or not info or info['errno'] != 0:
                return
            if info['info']:
                self.icon_window.load_next(info['info'])
            else:
                self.has_next = False

        if not self.has_next:
            return
        self.loading_spin.start()
        self.loading_spin.show_all()
        self.page_num = self.page_num + 1
        gutil.async_call(
                pcs.get_category, self.app.cookie, self.app.tokens,
                self.category, self.page_num, callback=on_load_next)

    def reload(self, *args):
        self.load()

    def on_list_view_button_clicked(self, button):
        if not isinstance(self.icon_window, TreeWindow):
            self.remove(self.icon_window)
            self.icon_window = TreeWindow(self, self.app)
            self.pack_end(self.icon_window, True, True, 0)
            self.icon_window.show_all()
            self.reload()

    def on_grid_view_button_clicked(self, button):
        if isinstance(self.icon_window, TreeWindow):
            self.remove(self.icon_window)
            self.icon_window = IconWindow(self, self.app)
            self.pack_end(self.icon_window, True, True, 0)
            self.icon_window.show_all()
            self.reload()


class VideoPage(CategoryPage):

    icon_name = 'videos-symbolic'
    disname = _('Videos')
    tooltip = _('Videos')
    category = 1


class MusicPage(CategoryPage):

    icon_name = 'music-symbolic'
    disname = _('Music')
    tooltip = _('Music')
    category = 2


class PicturePage(CategoryPage):

    icon_name = 'pictures-symbolic'
    disname = _('Pictures')
    tooltip = _('Pictures')
    category = 3


class DocPage(CategoryPage):

    icon_name = 'documents-symbolic'
    disname = _('Documents')
    tooltip = _('Documents')
    category = 4


class OtherPage(CategoryPage):

    icon_name = 'others-symbolic'
    disname = _('Others')
    tooltip = _('Others')
    category = 6


class BTPage(CategoryPage):

    icon_name = 'bittorrent-symbolic'
    disname = _('BT')
    tooltip = _('BT seeds')
    category = 7

########NEW FILE########
__FILENAME__ = CloudPage

# Copyright (C) 2014 LiuLang <gsushzhsosgsu@gmail.com>
# Use of this source code is governed by GPLv3 license that can be found
# in http://www.gnu.org/licenses/gpl-3.0.html

import os

from gi.repository import GObject
from gi.repository import Gtk
from gi.repository import Pango

from bcloud import Config
_ = Config._
from bcloud import decoder
from bcloud.BTBrowserDialog import BTBrowserDialog
from bcloud.FolderBrowserDialog import FolderBrowserDialog
from bcloud.VCodeDialog import VCodeDialog
from bcloud import gutil
from bcloud import pcs
from bcloud import util


(TASKID_COL, NAME_COL, PATH_COL, SOURCEURL_COL, SIZE_COL, FINISHED_COL,
    STATUS_COL, PERCENT_COL, HUMANSIZE_COL, TOOLTIP_COL) = list(range(10))

Status = (0, 1, )
StatusNames = (_('FINISHED'), _('DOWNLOADING'), )


class CloudPage(Gtk.Box):

    icon_name = 'cloud-symbolic'
    disname = _('Cloud')
    tooltip = _('Cloud Download')
    first_run = True

    def __init__(self, app):
        super().__init__(orientation=Gtk.Orientation.VERTICAL)
        self.app = app

        control_box = Gtk.Box()
        self.pack_start(control_box, False, False, 0)

        link_button = Gtk.Button.new_with_label(_('New Link Task'))
        link_button.connect('clicked', self.on_link_button_clicked)
        control_box.pack_start(link_button, False, False, 0)

        reload_button = Gtk.Button.new_with_label(_('Reload'))
        reload_button.props.margin_left = 40
        reload_button.connect('clicked', self.on_reload_button_clicked)
        control_box.pack_start(reload_button, False, False, 0)

        open_button = Gtk.Button.new_with_label(_('Open Directory'))
        open_button.connect('clicked', self.on_open_button_clicked)
        control_box.pack_start(open_button, False, False, 0)

        clear_button = Gtk.Button.new_with_label(_('Clear'))
        clear_button.set_tooltip_text(_('Clear finished or canceled tasks'))
        clear_button.connect('clicked', self.on_clear_button_clicked)
        control_box.pack_end(clear_button, False, False, 0)

        remove_button = Gtk.Button.new_with_label(_('Remove'))
        remove_button.set_tooltip_text(_('Remove selected tasks'))
        remove_button.connect('clicked', self.on_remove_button_clicked)
        control_box.pack_end(remove_button, False, False, 0)

        cancel_button = Gtk.Button.new_with_label(_('Cancel'))
        cancel_button.set_tooltip_text(_('Cancel selected tasks'))
        cancel_button.connect('clicked', self.on_cancel_button_clicked)
        control_box.pack_end(cancel_button, False, False, 0)

        # show loading process
        self.loading_spin = Gtk.Spinner()
        self.loading_spin.props.margin_right = 5
        control_box.pack_end(self.loading_spin, False, False, 0)

        scrolled_win = Gtk.ScrolledWindow()
        self.pack_start(scrolled_win, True, True, 0)

        # task_id, name, path, source_url, size, finished_size,
        # status, percent, human_size, tooltip
        self.liststore = Gtk.ListStore(
                str, str, str, str, GObject.TYPE_INT64,
                GObject.TYPE_INT64, int, int, str, str)
        self.treeview = Gtk.TreeView(model=self.liststore)
        self.treeview.set_headers_clickable(True)
        self.treeview.set_reorderable(True)
        self.treeview.set_search_column(NAME_COL)
        self.treeview.set_tooltip_column(TOOLTIP_COL)
        self.selection = self.treeview.get_selection()
        scrolled_win.add(self.treeview)

        name_cell = Gtk.CellRendererText(
                ellipsize=Pango.EllipsizeMode.END, ellipsize_set=True)
        name_col = Gtk.TreeViewColumn(_('Name'), name_cell, text=NAME_COL)
        name_col.set_expand(True)
        self.treeview.append_column(name_col)
        name_col.set_sort_column_id(NAME_COL)
        self.liststore.set_sort_func(NAME_COL, gutil.tree_model_natsort)

        size_cell = Gtk.CellRendererText()
        size_col = Gtk.TreeViewColumn(
                _('Size'), size_cell, text=HUMANSIZE_COL)
        self.treeview.append_column(size_col)
        size_col.props.min_width = 145
        size_col.set_sort_column_id(SIZE_COL)

        percent_cell = Gtk.CellRendererProgress()
        percent_col = Gtk.TreeViewColumn(
                _('Progress'), percent_cell, value=PERCENT_COL)
        self.treeview.append_column(percent_col)
        percent_col.props.min_width = 145
        percent_col.set_sort_column_id(PERCENT_COL)

    def check_first(self):
        if self.first_run:
            self.first_run = False
            self.load()

    def load(self):
        '''获取当前的离线任务列表'''
        def on_list_task(info, error=None):
            self.loading_spin.stop()
            self.loading_spin.hide()
            if error or not info:
                return
            if 'error_code' in info and info['error_code'] != 0:
                return
            tasks = info['task_info']
            for task in tasks:
                self.liststore.append([
                    task['task_id'],
                    task['task_name'],
                    task['save_path'],
                    task['source_url'],
                    0,
                    0,
                    int(task['status']),
                    0,
                    '0',
                    gutil.escape(task['save_path'])
                    ])
            self.scan_tasks()

            nonlocal start
            start = start + len(tasks)
            if info['total'] > start:
                gutil.async_call(
                    pcs.cloud_list_task, self.app.cookie, self.app.tokens,
                    start, callback=on_list_task)

        self.loading_spin.start()
        self.loading_spin.show_all()
        start = 0
        gutil.async_call(
            pcs.cloud_list_task, self.app.cookie, self.app.tokens,
            start, callback=on_list_task)

    def reload(self, *args, **kwds):
        self.liststore.clear()
        self.load()

    def get_row_by_task_id(self, task_id):
        '''返回这个任务的TreeModelRow, 如果不存在, 就返回None.'''
        for row in self.liststore:
            if row[TASKID_COL] == task_id:
                return row
        return None

    def scan_tasks(self):
        '''定期获取离线下载任务的信息, 比如10秒钟'''
        def update_task_status(info, error=None):
            if error or not info:
                return
            tasks = info['task_info']
            for row in self.liststore:
                if row[TASKID_COL] not in tasks:
                    continue
                task = tasks[row[TASKID_COL]]
                row[SIZE_COL] = int(task['file_size'])
                row[FINISHED_COL] = int(task['finished_size'])
                row[STATUS_COL] = int(task['status'])
                if row[SIZE_COL]:
                    row[PERCENT_COL] = int(row[FINISHED_COL] / row[SIZE_COL] * 100)
                size = util.get_human_size(row[SIZE_COL])[0]
                finished_size = util.get_human_size(row[FINISHED_COL])[0]
                if row[SIZE_COL] == row[FINISHED_COL]:
                    row[HUMANSIZE_COL] = size
                else:
                    row[HUMANSIZE_COL] = '{0}/{1}'.format(finished_size, size)

        task_ids = [row[TASKID_COL] for row in self.liststore]
        if task_ids:
            gutil.async_call(
                pcs.cloud_query_task, self.app.cookie, self.app.tokens,
                task_ids, callback=update_task_status)


    # Open API
    def add_cloud_bt_task(self, source_url, save_path=None):
        '''从服务器上获取种子, 并建立离线下载任务

        source_url - BT 种子在服务器上的绝对路径, 或者是磁链的地址.
        save_path  - 要保存到的路径, 如果为None, 就会弹出目录选择的对话框
        '''
        def check_vcode(info, error=None):
            if error or not info:
                return
            if 'task_id' in info or info['error_code'] == 0:
                self.reload()
            elif info['error_code'] == -19:
                vcode_dialog = VCodeDialog(self, self.app, info)
                response = vcode_dialog.run()
                vcode_input = vcode_dialog.get_vcode()
                vcode_dialog.destroy()
                if response != Gtk.ResponseType.OK:
                    return
                gutil.async_call(
                    pcs.cloud_add_bt_task, self.app.cookie,
                    self.app.tokens, source_url, save_path,
                    selected_idx, file_sha1, info['vcode'], vcode_input,
                    callback=check_vcode)
            else:
                self.app.toast(_('Error: {0}').format(info['error_msg']))

        self.check_first()

        if not save_path:
            folder_browser = FolderBrowserDialog(
                    self, self.app, _('Save to..'))
            response = folder_browser.run()
            save_path = folder_browser.get_path()
            folder_browser.destroy()
            if response != Gtk.ResponseType.OK:
                return
        if not save_path:
            return

        bt_browser = BTBrowserDialog(
                self, self.app, _('Choose..'), source_url, save_path)
        response = bt_browser.run()
        selected_idx, file_sha1 = bt_browser.get_selected()
        bt_browser.destroy()
        if response != Gtk.ResponseType.OK or not selected_idx:
            return
        gutil.async_call(
            pcs.cloud_add_bt_task, self.app.cookie, self.app.tokens,
            source_url, save_path, selected_idx, file_sha1,
            callback=check_vcode)
        self.app.blink_page(self.app.cloud_page)

    # Open API
    def add_link_task(self):
        '''新建普通的链接任务'''
        def do_add_link_task(source_url):
            def on_link_task_added(info, error=None):
                if error or not info:
                    return
                if 'task_id' in info or info['error_code'] == 0:
                    self.reload()
                elif info['error_code'] == -19:
                    vcode = info['vcode']
                    vcode_dialog = VCodeDialog(self, self.app, info)
                    response = vcode_dialog.run()
                    vcode_input = vcode_dialog.get_vcode()
                    vcode_dialog.destroy()
                    if response != Gtk.ResponseType.OK:
                        return
                    gutil.async_call(
                        pcs.cloud_add_link_task, self.app.cookie,
                        self.app.tokens, source_url, save_path, vcode,
                        vcode_input, callback=on_link_task_added)
                else:
                    self.app.toast(_('Error: {0}').format(info['error_msg']))
            gutil.async_call(
                pcs.cloud_add_link_task, self.app.cookie, self.app.tokens,
                source_url, save_path, callback=on_link_task_added)

        self.check_first()
        dialog = Gtk.Dialog(
                _('Add new link tasks'), self.app.window,
                Gtk.DialogFlags.MODAL,
                (Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
                Gtk.STOCK_OK, Gtk.ResponseType.OK))
        dialog.set_border_width(10)
        dialog.set_default_size(480, 300)
        dialog.set_default_response(Gtk.ResponseType.OK)
        box = dialog.get_content_area()
        scrolled_win = Gtk.ScrolledWindow()
        box.pack_start(scrolled_win, True, True, 0)
        links_buf = Gtk.TextBuffer()
        links_tv = Gtk.TextView.new_with_buffer(links_buf)
        links_tv.set_tooltip_text(_('Paste links here, line by line'))
        scrolled_win.add(links_tv)

        infobar = Gtk.InfoBar()
        infobar.set_message_type(Gtk.MessageType.INFO)
        box.pack_start(infobar, False, False, 5)
        info_content = infobar.get_content_area()
        info_label = Gtk.Label.new(
            _('Support http/https/ftp/thunder/qqdl/flashget/eMule/Magnet format'))
        info_content.pack_start(info_label, False, False, 0)

        box.show_all()
        response = dialog.run()
        contents = gutil.text_buffer_get_all_text(links_buf)
        dialog.destroy()
        if response != Gtk.ResponseType.OK or not contents:
            return
        link_tasks = []
        bt_tasks = []
        for source_url in contents.split('\n'):
            source_url = source_url.strip()
            if not source_url:
                continue
            if source_url.startswith('magnet'):
                bt_tasks.append(source_url)
            else:
                priv_url = decoder.decode(source_url)
                if priv_url:
                    link_tasks.append(priv_url)
                else:
                    link_tasks.append(source_url)

        folder_browser = FolderBrowserDialog(
                self, self.app, _('Save to..'))
        response = folder_browser.run()
        save_path = folder_browser.get_path()
        folder_browser.destroy()
        if response != Gtk.ResponseType.OK or not save_path:
            return
        for source_url in link_tasks:
            do_add_link_task(source_url)
        for source_url in bt_tasks:
            self.add_cloud_bt_task(source_url, save_path)


    def on_bt_button_clicked(self, button):
        self.add_local_bt_task()

    def on_link_button_clicked(self, button):
        self.add_link_task()

    def on_reload_button_clicked(self, button):
        self.reload()

    def on_open_button_clicked(self, button):
        model, tree_paths = self.selection.get_selected_rows()
        if not tree_paths or len(tree_paths) != 1:
            return
        tree_path = tree_paths[0]
        path = model[tree_path][PATH_COL]
        dir_name = os.path.split(path)[0]
        self.app.home_page.load(dir_name)
        self.app.switch_page(self.app.home_page)

    def on_cancel_button_clicked(self, button):
        model, tree_paths = self.selection.get_selected_rows()
        if not tree_paths or len(tree_paths) != 1:
            return
        tree_path = tree_paths[0]
        task_id = model[tree_path][TASKID_COL]
        gutil.async_call(
            pcs.cloud_cancel_task, self.app.cookie, self.app.tokens,
            task_id, callback=self.reload)

    def on_remove_button_clicked(self, button):
        def on_task_removed(resp, error=None):
            self.reload()
        model, tree_paths = self.selection.get_selected_rows()
        if not tree_paths or len(tree_paths) != 1:
            return
        tree_path = tree_paths[0]
        task_id = model[tree_path][TASKID_COL]
        self.loading_spin.start()
        self.loading_spin.show_all()
        if model[tree_path][STATUS_COL] == Status[0]:
            gutil.async_call(
                pcs.cloud_delete_task, self.app.cookie, self.app.tokens,
                task_id, callback=on_task_removed)
        else:
            gutil.async_call(
                pcs.cloud_cancel_task, self.app.cookie, self.app.tokens,
                task_id, callback=self.reload)

    def on_clear_button_clicked(self, button):
        def on_clear_task(info, error=None):
            self.reload()

        gutil.async_call(
            pcs.cloud_clear_task, self.app.cookie, self.app.tokens,
            callback=on_clear_task)

########NEW FILE########
__FILENAME__ = Config

# Copyright (C) 2014 LiuLang <gsushzhsosgsu@gmail.com>
# Use of this source code is governed by GPLv3 license that can be found
# in http://www.gnu.org/licenses/gpl-3.0.html

import gettext
import json
import os

from gi.repository import Gdk
from gi.repository import Gtk

if __file__.startswith('/usr/local/'):
    PREF = '/usr/local/share'
elif __file__.startswith('/usr/'):
    PREF = '/usr/share'
else:
    PREF = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'share')
NAME = 'bcloud'
ICON_PATH = os.path.join(PREF, NAME, 'icons')
COLOR_SCHEMA = os.path.join(PREF, NAME, 'color_schema.json')

LOCALEDIR = os.path.join(PREF, 'locale')
gettext.bindtextdomain(NAME, LOCALEDIR)
gettext.textdomain(NAME)
_ = gettext.gettext

DBUS_APP_NAME = 'org.liulang.bcloud'
APPNAME = 'BCloud'
VERSION = '3.3.7'
HOMEPAGE = 'https://github.com/LiuLang/bcloud'
AUTHORS = ['LiuLang <gsushzhsosgsu@gmail.com>', ]
COPYRIGHT = 'Copyright (c) 2014 LiuLang'
DESCRIPTION = _('Baidu Pan client for GNU/Linux desktop users.')

HOME_DIR = os.path.expanduser('~')
CACHE_DIR = os.path.join(HOME_DIR, '.cache', NAME)

# Check Gtk version <= 3.6
GTK_LE_36 = (Gtk.MAJOR_VERSION == 3) and (Gtk.MINOR_VERSION <= 6)

CONF_DIR = os.path.join(HOME_DIR, '.config', NAME)
_conf_file = os.path.join(CONF_DIR, 'conf.json')

_base_conf = {
    'default': '',
    'profiles': [],
    }

def check_first():
    '''这里, 要创建基本的目录结构'''
    if not os.path.exists(CONF_DIR):
        os.makedirs(CONF_DIR, exist_ok=True)
    if not os.path.exists(CACHE_DIR):
        os.makedirs(CACHE_DIR, exist_ok=True)

def load_conf():
    '''获取基本设定信息, 里面存放着所有可用的profiles, 以及默认的profile'''
    if os.path.exists(_conf_file):
        with open(_conf_file) as fh:
            return json.load(fh)
    else:
        dump_conf(_base_conf)
        return _base_conf

def dump_conf(conf):
    with open(_conf_file, 'w') as fh:
        json.dump(conf, fh)

def get_cache_path(profile_name):
    '''获取这个帐户的缓存目录, 如果不存在, 就创建它'''
    path = os.path.join(CACHE_DIR, profile_name, 'cache')
    if not os.path.exists(path):
        os.makedirs(path, exist_ok=True)
    return path

def get_tmp_path(profile_name):
    '''获取这个帐户的临时文件目录, 可以存放验证码图片, 上传时的文件分片等'''
    path = os.path.join(CACHE_DIR, profile_name, 'tmp')
    if not os.path.exists(path):
        os.makedirs(path, exist_ok=True)
    return path

def load_color_schema():
    if not os.path.exists(COLOR_SCHEMA):
        return []
    with open(COLOR_SCHEMA) as fh:
        color_list = json.load(fh)

    schema = []
    for color in color_list:
        rgba = Gdk.RGBA()
        rgba.red = int(color[:2], base=16) / 255
        rgba.green = int(color[2:4], base=16) / 255
        rgba.blue = int(color[4:6], base=16) / 255
        rgba.alpha = int(color[6:], base=16) / 255
        schema.append(rgba)
    return schema

########NEW FILE########
__FILENAME__ = const

# Copyright (C) 2013-2014 LiuLang <gsushzhsosgsu@gmail.com>
# Use of this source code is governed by GPLv3 license that can be found
# in http://www.gnu.org/licenses/gpl-3.0.html

'''
这个模块保存着网络连接时需要共用的一些常量.
与界面相关的常量, 都位于Config.py.
'''

BAIDU_URL = 'http://www.baidu.com/'
PASSPORT_BASE = 'https://passport.baidu.com/'
PASSPORT_URL = PASSPORT_BASE + 'v2/api/'
REFERER = PASSPORT_BASE + 'v2/?login'
USER_AGENT = 'Mozilla/4.0 (compatible; MSIE 8.0; Windows NT 5.1; Trident/4.0;'
PAN_URL = 'http://pan.baidu.com/'
PAN_API_URL = PAN_URL + 'api/'
PAN_REFERER = 'http://pan.baidu.com/disk/home'
SHARE_REFERER = PAN_URL + 'share/manage'

# 一般的服务器名
PCS_URL = 'http://pcs.baidu.com/rest/2.0/pcs/'
# 上传的服务器名
PCS_URL_C = 'http://c.pcs.baidu.com/rest/2.0/pcs/'
PCS_URLS_C = 'https://c.pcs.baidu.com/rest/2.0/pcs/'
# 下载的服务器名
PCS_URL_D = 'http://d.pcs.baidu.com/rest/2.0/pcs/'

## 以下常量是模拟的PC客户端的参数.
CHANNEL_URL = 'https://channel.api.duapp.com/rest/2.0/channel/channel?'
PC_USER_AGENT = 'netdisk;4.5.0.7;PC;PC-Windows;5.1.2600;WindowsBaiduYunGuanJia'
PC_DEVICE_ID = '08002788772E'
PC_DEVICE_NAME = '08002788772E'
PC_DEVICE_TYPE = '2'
PC_CLIENT_TYPE = '8'
PC_APP_ID = '1981342'
PC_DEVUID = ('BDIMXV2%2DO%5FFD60326573E54779892088D1378B27C6%2DC%5F0%2DD' +
             '%5F42563835636437366130302d6662616539362064%2DM%5F08002788' +
             '772E%2DV%5F0C94CA83')
PC_VERSION = '4.5.0.7'

## HTTP 请求时的一些常量
CONTENT_FORM = 'application/x-www-form-urlencoded'
CONTENT_FORM_UTF8 = CONTENT_FORM + '; charset=UTF-8'
ACCEPT_HTML = 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'
ACCEPT_JSON = 'application/json, text/javascript, */*; q=0.01'


class State:
    '''下载状态常量'''
    DOWNLOADING = 0
    WAITING = 1
    PAUSED = 2
    FINISHED = 3
    CANCELED = 4
    ERROR = 5

########NEW FILE########
__FILENAME__ = decoder

# Copyright (C) 2014 LiuLang <gsushzhsosgsu@gmail.com>
# Use of this source code is governed by GPLv3 license that can be found
# in http://www.gnu.org/licenses/gpl-3.0.html

import base64

def decode_flashget(link):
    l = base64.decodestring(link[11:len(link)-7].encode()).decode()
    return l[10:len(l)-10]

def decode_thunder(link):
    # AAhttp://127.0.0.1
    if link.startswith('QUFodHRwOi8vMTI3LjAuMC4'):
        return ''
    l = base64.decodestring(link[10:].encode()).decode()
    return l[2:-2]

def decode_qqdl(link):
    return base64.decodestring(link[7:].encode()).decode()

_router = {
    'flashge': decode_flashget,
    'thunder': decode_thunder,
    'qqdl://': decode_qqdl,
    }

def decode(link):
    if not isinstance(link, str) or len(link) < 10:
        return ''
    lower_pref = link[:7].lower()
    if lower_pref in _router:
        try:
            return _router[lower_pref](link)
        except ValueError as e:
            print(e)
            return ''
    else:
        return ''

########NEW FILE########
__FILENAME__ = Downloader

# Copyright (C) 2014 LiuLang <gsushzhsosgsu@gmail.com>
# Use of this source code is governed by GPLv3 license that can be found
# in http://www.gnu.org/licenses/gpl-3.0.html

import multiprocessing
import os
import threading
import time

from urllib import request
from gi.repository import GLib
from gi.repository import GObject

from bcloud.const import State
from bcloud.net import ForbiddenHandler
from bcloud import pcs

CHUNK_SIZE = 131072 # 128K
RETRIES = 5             # 下载数据出错时重试的次数
TIMEOUT = 20
THRESHOLD_TO_FLUSH = 100  # 磁盘写入数据次数超过这个值时, 就进行一次同步.

(NAME_COL, PATH_COL, FSID_COL, SIZE_COL, CURRSIZE_COL, LINK_COL,
    ISDIR_COL, SAVENAME_COL, SAVEDIR_COL, STATE_COL, STATENAME_COL,
    HUMANSIZE_COL, PERCENT_COL) = list(range(13))


class Downloader(threading.Thread, GObject.GObject):
    '''后台下载的线程, 每个任务应该对应一个Downloader对象.

    当程序退出时, 下载线程会保留现场, 以后可以继续下载.
    断点续传功能基于HTTP/1.1 的Range, 百度网盘对它有很好的支持.
    '''

    fh = None
    red_url = ''
    flush_count = 0

    __gsignals__ = {
            'started': (GObject.SIGNAL_RUN_LAST,
                # fs_id
                GObject.TYPE_NONE, (str, )),
            'received': (GObject.SIGNAL_RUN_LAST,
                # fs-id, current-size
                GObject.TYPE_NONE, (str, GObject.TYPE_INT64)),
            'downloaded': (GObject.SIGNAL_RUN_LAST, 
                # fs_id
                GObject.TYPE_NONE, (str, )),
            'disk-error': (GObject.SIGNAL_RUN_LAST,
                # fs_id
                GObject.TYPE_NONE, (str, )),
            'network-error': (GObject.SIGNAL_RUN_LAST,
                # fs_id
                GObject.TYPE_NONE, (str, )),
            }

    def __init__(self, parent, row, cookie, tokens):
        threading.Thread.__init__(self)
        self.daemon = True
        GObject.GObject.__init__(self)

        self.parent = parent
        self.cookie = cookie
        self.tokens = tokens
        self.row = row[:]  # 复制一份

    def init_files(self):
        row = self.row
        if not os.path.exists(self.row[SAVEDIR_COL]):
            os.makedirs(row[SAVEDIR_COL], exist_ok=True)
        self.filepath = os.path.join(row[SAVEDIR_COL], row[SAVENAME_COL]) 
        if os.path.exists(self.filepath):
            curr_size = os.path.getsize(self.filepath)
            if curr_size == row[SIZE_COL]:
                self.finished()
                return
            elif curr_size < row[SIZE_COL]:
                if curr_size == row[CURRSIZE_COL]:
                    self.fh = open(self.filepath, 'ab')
                elif curr_size < row[CURRSIZE_COL]:
                    self.fh = open(self.filepath, 'ab')
                    row[CURRSIZE_COL] = curr_size
                else:
                    if 0 < row[CURRSIZE_COL]:
                        self.fh = open(self.filepath, 'ab')
                        self.fh.seek(row[CURRSIZE_COL])
                    else:
                        self.fh = open(self.filepath, 'wb')
                        self.row[CURRSIZE_COL] = 0
            else:
                self.fh = open(self.filepath, 'wb')
                self.row[CURRSIZE_COL] = 0
        else:
            self.fh = open(self.filepath, 'wb')
            self.row[CURRSIZE_COL] = 0


    def destroy(self):
        '''自毁'''
        self.pause()

    def run(self):
        '''实现了Thread的方法, 线程启动入口'''
        self.init_files()
        if self.fh:
            self.get_download_link()

    def get_download_link(self):
        self.red_url = pcs.get_download_link(
                self.cookie, self.tokens, self.row[PATH_COL])
        if not self.red_url:
            print('Failed to get download link')
            self.network_error()
        self.download()

    def download(self):
        self.emit('started', self.row[FSID_COL])
        content_range = 'bytes={0}-{1}'.format(
                self.row[CURRSIZE_COL], self.row[SIZE_COL]-1)
        opener = request.build_opener(ForbiddenHandler)
        opener.addheaders = [('Range', content_range)]
        for i in range(RETRIES):
            try:
                req = opener.open(self.red_url)
            except OSError as e:
                print(e)
                if i == (RETRIES - 1):
                    self.network_error()
                    return
            else:
                break

        range_from = self.row[CURRSIZE_COL]
        range_to = range_from
        filesize_dl = 0
        start_time = time.time()

        while self.row[STATE_COL] == State.DOWNLOADING:
            try:
                buff = req.read(CHUNK_SIZE)
            except Exception as e:
                self.network_error()
                break
            if not buff:
                if self.row[CURRSIZE_COL] == self.row[SIZE_COL]:
                    self.finished()
                else:
                    self.network_error()
                break
            range_from, range_to = range_to, range_to + len(buff)
            if not self.fh or self.row[STATE_COL] != State.DOWNLOADING:
                break
            self.emit('received', self.row[FSID_COL], range_to)
            self.fh.write(buff)
            self.flush_count = self.flush_count + 1
            if self.flush_count > THRESHOLD_TO_FLUSH:
                self.fh.flush()
                self.flush_count = 0
            self.row[CURRSIZE_COL] += len(buff)
        self.close_file()

    def pause(self):
        '''暂停下载任务'''
        self.row[STATE_COL] = State.PAUSED
        self.close_file()

    def stop(self):
        '''停止下载, 并删除之前下载的片段'''
        self.row[STATE_COL] = State.CANCELED
        self.close_file()
        os.remove(self.filepath)

    def close_file(self):
        if self.fh and not self.fh.closed:
            self.fh.flush()
            self.fh.close()
            self.fh = None

    def finished(self):
        self.row[STATE_COL] = State.FINISHED
        self.emit('downloaded', self.row[FSID_COL])
        self.close_file()

    def network_error(self):
        self.row[STATE_COL] = State.ERROR
        self.emit('network-error', self.row[FSID_COL])
        self.close_file()

GObject.type_register(Downloader)

########NEW FILE########
__FILENAME__ = DownloadPage

# Copyright (C) 2014 LiuLang <gsushzhsosgsu@gmail.com>
# Use of this source code is governed by GPLv3 license that can be found
# in http://www.gnu.org/licenses/gpl-3.0.html

import json
import os
import sqlite3
import threading
import time

from gi.repository import Gio
from gi.repository import GLib
from gi.repository import GObject
from gi.repository import Gtk
from gi.repository import Pango

from bcloud import Config
_ = Config._
from bcloud.Downloader import Downloader
from bcloud import gutil
from bcloud import pcs
from bcloud import util
from bcloud.const import State


TASK_FILE = 'tasks.sqlite'
RUNNING_STATES = (State.FINISHED, State.DOWNLOADING, State.WAITING)
(NAME_COL, PATH_COL, FSID_COL, SIZE_COL, CURRSIZE_COL, LINK_COL,
    ISDIR_COL, SAVENAME_COL, SAVEDIR_COL, STATE_COL, STATENAME_COL,
    HUMANSIZE_COL, PERCENT_COL, TOOLTIP_COL) = list(range(14))

StateNames = (
        _('DOWNLOADING'),
        _('WAITING'),
        _('PAUSED'),
        _('FINISHED'),
        _('CANCELED'),
        _('ERROR'),
        )


class DownloadPage(Gtk.Box):
    '''下载任务管理器, 处理下载任务的后台调度.

    * 它是与UI进行交互的接口.
    * 它会保存所有下载任务的状态.
    * 它来为每个下载线程分配任务.
    * 它会自动管理磁盘文件结构, 在必要时会创建必要的目录.
    * 它会自动获取文件的最新的下载链接(这个链接有效时间是8小时).

    每个task(pcs_file)包含这些信息:
    fs_id - 服务器上的文件UID
    md5 - 文件MD5校验值
    size - 文件大小
    path - 文件在服务器上的绝对路径
    name - 文件在服务器上的名称
    savePath - 保存到的绝对路径
    saveName - 保存时的文件名
    currRange - 当前下载的进度, 以字节为单位, 在HTTP Header中可用.
    state - 任务状态 
    link - 文件的下载最终URL, 有效期大约是8小时, 超时后要重新获取.
    '''

    icon_name = 'download-symbolic'
    disname = _('Download')
    tooltip = _('Downloading tasks')
    first_run = True
    workers = {} # { `fs_id': (worker,row) }
    app_infos = {} # { `fs_id': app }
    commit_count = 0
    downloading_size = 0
    downloading_timestamp = 0

    def __init__(self, app):
        super().__init__(orientation=Gtk.Orientation.VERTICAL)
        self.app = app

    def load(self):
        app = self.app
        control_box = Gtk.Box()
        self.pack_start(control_box, False, False, 0)

        start_button = Gtk.Button.new_with_label(_('Start'))
        start_button.connect('clicked', self.on_start_button_clicked)
        control_box.pack_start(start_button, False, False, 0)

        pause_button = Gtk.Button.new_with_label(_('Pause'))
        pause_button.connect('clicked', self.on_pause_button_clicked)
        control_box.pack_start(pause_button, False, False, 0)

        open_folder_button = Gtk.Button.new_with_label(_('Open Directory'))
        open_folder_button.connect(
                'clicked', self.on_open_folder_button_clicked)
        open_folder_button.props.margin_left = 40
        control_box.pack_start(open_folder_button, False, False, 0)

        remove_button = Gtk.Button.new_with_label(_('Remove'))
        remove_button.connect('clicked', self.on_remove_button_clicked)
        control_box.pack_end(remove_button, False, False, 0)

        self.speed_label = Gtk.Label()
        control_box.pack_end(self.speed_label, False, False, 5)

        scrolled_win = Gtk.ScrolledWindow()
        self.pack_start(scrolled_win, True, True, 0)

        # name, path, fs_id, size, currsize, link,
        # isdir, saveDir, saveName, state, statename,
        # humansize, percent, tooltip
        self.liststore = Gtk.ListStore(
                str, str, str, GObject.TYPE_INT64, GObject.TYPE_INT64, str,
                GObject.TYPE_INT, str, str, GObject.TYPE_INT, str,
                str, GObject.TYPE_INT, str)
        self.treeview = Gtk.TreeView(model=self.liststore)
        self.treeview.set_tooltip_column(TOOLTIP_COL)
        self.treeview.set_headers_clickable(True)
        self.treeview.set_reorderable(True)
        self.treeview.set_search_column(NAME_COL)
        self.selection = self.treeview.get_selection()
        self.selection.set_mode(Gtk.SelectionMode.MULTIPLE)
        scrolled_win.add(self.treeview)
        
        name_cell = Gtk.CellRendererText(
                ellipsize=Pango.EllipsizeMode.END, ellipsize_set=True)
        name_col = Gtk.TreeViewColumn(_('Name'), name_cell, text=NAME_COL)
        name_col.set_expand(True)
        self.treeview.append_column(name_col)
        name_col.set_sort_column_id(NAME_COL)
        self.liststore.set_sort_func(NAME_COL, gutil.tree_model_natsort)

        percent_cell = Gtk.CellRendererProgress()
        percent_col = Gtk.TreeViewColumn(
                _('Progress'), percent_cell, value=PERCENT_COL)
        self.treeview.append_column(percent_col)
        percent_col.props.min_width = 145
        percent_col.set_sort_column_id(PERCENT_COL)

        size_cell = Gtk.CellRendererText()
        size_col = Gtk.TreeViewColumn(
                _('Size'), size_cell, text=HUMANSIZE_COL)
        self.treeview.append_column(size_col)
        size_col.props.min_width = 100
        size_col.set_sort_column_id(SIZE_COL)

        state_cell = Gtk.CellRendererText()
        state_col = Gtk.TreeViewColumn(
                _('State'), state_cell, text=STATENAME_COL)
        self.treeview.append_column(state_col)
        state_col.props.min_width = 100
        state_col.set_sort_column_id(PERCENT_COL)

        self.init_db()
        self.load_tasks_from_db()
        self.show_all()

    def init_db(self):
        '''这个任务数据库只在程序开始时读入, 在程序关闭时导出.

        因为Gtk没有像在Qt中那么方便的使用SQLite, 而必须将所有数据读入一个
        liststore中才行.
        '''
        cache_path = os.path.join(
                Config.CACHE_DIR, self.app.profile['username'])
        if not os.path.exists(cache_path):
            os.makedirs(cache_path, exist_ok=True)
        db = os.path.join(cache_path, TASK_FILE)
        self.conn = sqlite3.connect(db)
        self.cursor = self.conn.cursor()
        sql = '''CREATE TABLE IF NOT EXISTS tasks (
        name CHAR NOT NULL,
        path CHAR NOT NULL,
        fsid CHAR NOT NULL,
        size INTEGER NOT NULL,
        currsize INTEGER NOT NULL,
        link CHAR,
        isdir INTEGER,
        savename CHAR NOT NULL,
        savedir CHAR NOT NULL,
        state INT NOT NULL,
        statename CHAR NOT NULL,
        humansize CHAR NOT NULL,
        percent INT NOT NULL,
        tooltip CHAR
        )
        '''
        self.cursor.execute(sql)

        # mig 3.2.1 -> 3.3.1
        try:
            req = self.cursor.execute('SELECT * FROM download')
            tasks = []
            for row in req:
                tasks.append(row + ('', ))
            if tasks:
                sql = 'INSERT INTO tasks VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)'
                self.cursor.executemany(sql, tasks)
                self.check_commit()
            self.cursor.execute('DROP TABLE download')
            self.check_commit()
        except sqlite3.OperationalError:
            pass

    def check_first(self):
        if self.first_run:
            self.first_run = False
            self.load()

    def on_destroy(self, *args):
        if not self.first_run:
            self.pause_tasks()
            self.conn.commit()
            self.conn.close()
            for worker, row in self.workers.values():
                worker.pause()
                row[CURRSIZE_COL] = worker.row[CURRSIZE_COL]
    
    def load_tasks_from_db(self):
        req = self.cursor.execute('SELECT * FROM tasks')
        for task in req:
            self.liststore.append(task)

    def add_task_db(self, task):
        '''向数据库中写入一个新的任务记录'''
        sql = 'INSERT INTO tasks VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)'
        req = self.cursor.execute(sql, task)
        self.check_commit()

    def get_task_db(self, fs_id):
        '''从数据库中查询fsid的信息.
        
        如果存在的话, 就返回这条记录;
        如果没有的话, 就返回None
        '''
        sql = 'SELECT * FROM tasks WHERE fsid=? LIMIT 1'
        req = self.cursor.execute(sql, [fs_id, ])
        if req:
            return req.fetchone()
        else:
            None

    def check_commit(self):
        '''当修改数据库超过100次后, 就自动commit数据.'''
        self.commit_count = self.commit_count + 1
        if self.commit_count >= 100:
            self.commit_count = 0
            self.conn.commit()

    def update_task_db(self, row):
        '''更新数据库中的任务信息'''
        sql = '''UPDATE tasks SET 
        currsize=?, state=?, statename=?, humansize=?, percent=?
        WHERE fsid=? LIMIT 1;
        '''
        self.cursor.execute(sql, [
            row[CURRSIZE_COL], row[STATE_COL], row[STATENAME_COL],
            row[HUMANSIZE_COL], row[PERCENT_COL], row[FSID_COL]
            ])
        self.check_commit()

    def remove_task_db(self, fs_id):
        '''将任务从数据库中删除'''
        sql = 'DELETE FROM tasks WHERE fsid=?'
        self.cursor.execute(sql, [fs_id, ])
        self.check_commit()

    def get_row_by_fsid(self, fs_id):
        '''确认在Liststore中是否存在这条任务. 如果存在, 返回TreeModelRow,
        否则就返回None'''
        for row in self.liststore:
            if row[FSID_COL] == fs_id:
                return row
        return None

    # Open API
    def add_launch_task(self, pcs_file, app_info):
        self.check_first()
        fs_id = str(pcs_file['fs_id'])
        if fs_id in self.app_infos:
            return
        self.app_infos[fs_id] = app_info
        self.add_task(pcs_file)

    def launch_app(self, fs_id):
        if fs_id in self.app_infos:
            row = self.get_row_by_fsid(fs_id)
            if not row:
                return
            app_info = self.app_infos[fs_id]
            filepath = os.path.join(row[SAVEDIR_COL], row[SAVENAME_COL])
            gfile = Gio.File.new_for_path(filepath)
            app_info.launch([gfile, ], None)
            self.app_infos.pop(fs_id, None)

    # Open API
    def add_tasks(self, pcs_files):
        '''建立批量下载任务, 包括目录'''
        def on_list_dir(info, error=None):
            path, pcs_files = info
            if error or not pcs_files:
                dialog = Gtk.MessageDialog(
                        self.app.window, Gtk.DialogFlags.MODAL,
                        Gtk.MessageType.ERROR, Gtk.ButtonsType.CLOSE,
                        _('Failed to scan folder to download'))
                dialog.format_secondary_text(
                        _('Please download {0} again').format(path))
                dialog.run()
                dialog.destroy()
                return
            self.add_tasks(pcs_files)

        self.check_first()
        for pcs_file in pcs_files:
            if pcs_file['isdir']:
                gutil.async_call(
                        pcs.list_dir_all, self.app.cookie, self.app.tokens,
                        pcs_file['path'], callback=on_list_dir)
            else:
                self.add_task(pcs_file)

    def add_task(self, pcs_file):
        '''加入新的下载任务'''
        if pcs_file['isdir']:
            return
        # 如果已经存在于下载列表中, 就忽略.
        fs_id = str(pcs_file['fs_id'])
        row = self.get_row_by_fsid(fs_id)
        if row:
            if row[STATE_COL] == State.FINISHED:
                self.launch_app(fs_id)
            elif row[STATE_COL] not in RUNNING_STATES:
                row[STATE_COL] = State.WAITING
            self.scan_tasks()
            return
        saveDir = os.path.split(
                self.app.profile['save-dir'] + pcs_file['path'])[0]
        saveName = pcs_file['server_filename']
        human_size = util.get_human_size(pcs_file['size'])[0]
        tooltip = gutil.escape(
                _('From {0}\nTo {1}').format(pcs_file['path'], saveDir))
        task = (
            pcs_file['server_filename'],
            pcs_file['path'],
            fs_id,
            pcs_file['size'],
            0,
            '',  # pcs['dlink' removed in new version.
            pcs_file['isdir'],
            saveName,
            saveDir,
            State.WAITING,
            StateNames[State.WAITING],
            human_size,
            0,
            tooltip,
            )
        self.liststore.append(task)
        self.add_task_db(task)
        self.scan_tasks()

    def scan_tasks(self):
        '''扫描所有下载任务, 并在需要时启动新的下载'''
        for row in self.liststore:
            if len(self.workers.keys()) >= self.app.profile['concurr-tasks']:
                break
            if row[STATE_COL] == State.WAITING:
                self.start_worker(row)

    def start_worker(self, row):
        '''为task新建一个后台下载线程, 并开始下载.'''
        def on_worker_started(worker, fs_id):
            GLib.idle_add(do_worker_started)

        def do_worker_started():
            self.downloading_size = 0
            self.downloading_timestamp = time.time()

        def on_worker_received(worker, fs_id, current_size):
            GLib.idle_add(do_worker_received, fs_id, current_size)

        def do_worker_received(fs_id, current_size):
            row = None
            if fs_id in self.workers:
                row = self.workers[fs_id][1]
            else:
                row = self.get_row_by_fsid(fs_id)
            if not row:
                return
            # update downloading speed
            self.downloading_size += current_size - row[CURRSIZE_COL]
            speed = (self.downloading_size /
                        (time.time() - self.downloading_timestamp) / 1000)
            self.speed_label.set_text(_('{0} kb/s').format(int(speed)))

            row[CURRSIZE_COL] = current_size
            curr_size = util.get_human_size(row[CURRSIZE_COL], False)[0]
            total_size = util.get_human_size(row[SIZE_COL])[0]
            row[PERCENT_COL] = int(row[CURRSIZE_COL] / row[SIZE_COL] * 100)
            row[HUMANSIZE_COL] = '{0} / {1}'.format(curr_size, total_size)
            self.update_task_db(row)

        def on_worker_downloaded(worker, fs_id):
            GLib.idle_add(do_worker_downloaded, fs_id)

        def do_worker_downloaded(fs_id):
            row = None
            if fs_id in self.workers:
                row = self.workers[fs_id][1]
            else:
                row = self.get_row_by_fsid(fs_id)
            if not row:
                return
            row[CURRSIZE_COL] = row[SIZE_COL]
            row[STATE_COL] = State.FINISHED
            row[PERCENT_COL] = 100
            total_size = util.get_human_size(row[SIZE_COL])[0]
            row[HUMANSIZE_COL] = '{0} / {1}'.format(total_size, total_size)
            row[STATENAME_COL] = StateNames[State.FINISHED]
            self.update_task_db(row)
            self.workers.pop(row[FSID_COL], None)
            self.app.toast(_('{0} downloaded'.format(row[NAME_COL])))
            self.launch_app(fs_id)
            self.scan_tasks()

        def on_worker_network_error(worker, fs_id):
            GLib.idle_add(do_worker_network_error, fs_id)

        def do_worker_network_error(fs_id):
            row = self.workers.get(fs_id, None)
            if row:
                row = row[1]
            else:
                row = self.get_row_by_fsid(fs_id)
                if not row:
                    return
            row[STATE_COL] = State.ERROR
            row[STATENAME_COL] = StateNames[State.ERROR]
            self.update_task_db(row)
            self.remove_worker(row[FSID_COL])
            self.app.toast(_('Error occurs will downloading {0}').format(
                row[NAME_COL]))
            self.scan_tasks()

        if row[FSID_COL] in self.workers:
            return
        row[STATE_COL] = State.DOWNLOADING
        row[STATENAME_COL] = StateNames[State.DOWNLOADING]
        worker = Downloader(self, row, self.app.cookie, self.app.tokens)
        self.workers[row[FSID_COL]] = (worker, row)
        worker.connect('started', on_worker_started)
        worker.connect('received', on_worker_received)
        worker.connect('downloaded', on_worker_downloaded)
        worker.connect('network-error', on_worker_network_error)
        worker.start()

    def pause_worker(self, row):
        self.remove_worker(row[FSID_COL], stop=False)

    def stop_worker(self, row):
        '''停止这个task的后台下载线程'''
        self.remove_worker(row[FSID_COL], stop=True)

    def remove_worker(self, fs_id, stop=True):
        if fs_id not in self.workers:
            return
        worker = self.workers[fs_id][0]
        if stop:
            worker.stop()
        else:
            worker.pause()
        self.workers.pop(fs_id, None)

    def start_task(self, row, scan=True):
        '''启动下载任务.

        将任务状态设定为Downloading, 如果没有超过最大任务数的话;
        否则将它设定为Waiting.
        '''
        if row[STATE_COL] in RUNNING_STATES :
            return
        row[STATE_COL] = State.WAITING
        row[STATENAME_COL] = StateNames[State.WAITING]
        self.update_task_db(row)
        if scan:
            self.scan_tasks()

    # Open API
    def pause_tasks(self):
        '''暂停所有下载任务'''
        if self.first_run:
            return
        for row in self.liststore:
            self.pause_task(row, scan=False)
        self.speed_label.set_text('')

    def pause_task(self, row, scan=True):
        if row[STATE_COL] == State.DOWNLOADING:
            self.pause_worker(row)
        if row[STATE_COL] in (State.DOWNLOADING, State.WAITING):
            row[STATE_COL] = State.PAUSED
            row[STATENAME_COL] = StateNames[State.PAUSED]
            self.update_task_db(row)
            if scan:
                self.scan_tasks()

    def remove_task(self, row, scan=True):
        # 当删除正在下载的任务时, 直接调用stop_worker(), 它会自动删除本地的
        # 文件片段
        if row[STATE_COL] == State.DOWNLOADING:
            self.stop_worker(row)
        elif row[CURRSIZE_COL] < row[SIZE_COL]:
            filepath = os.path.join(row[SAVEDIR_COL], row[SAVENAME_COL])
            if os.path.exists(filepath):
                os.remove(filepath)
        self.app_infos.pop(row[FSID_COL], None)
        self.remove_task_db(row[FSID_COL])
        tree_iter = row.iter
        if tree_iter:
            self.liststore.remove(tree_iter)
        if scan:
            self.scan_tasks()

    def operate_selected_rows(self, operator):
        '''对选中的条目进行操作.

        operator  - 处理函数
        '''
        model, tree_paths = self.selection.get_selected_rows()
        if not tree_paths:
            return
        fs_ids = []
        for tree_path in tree_paths:
            fs_ids.append(model[tree_path][FSID_COL])
        for fs_id in fs_ids:
            row = self.get_row_by_fsid(fs_id)
            if not row:
                return
            operator(row, scan=False)
        self.scan_tasks()


    def on_start_button_clicked(self, button):
        self.operate_selected_rows(self.start_task)

    def on_pause_button_clicked(self, button):
        self.operate_selected_rows(self.pause_task)

    def on_remove_button_clicked(self, button):
        self.operate_selected_rows(self.remove_task)

    def on_open_folder_button_clicked(self, button):
        model, tree_paths = self.selection.get_selected_rows()
        if not tree_paths:
            return
        for tree_path in tree_paths:
            gutil.xdg_open(self.liststore[tree_path][SAVEDIR_COL])

########NEW FILE########
__FILENAME__ = encoder

# Copyright (C) 2013-2014 LiuLang <gsushzhsosgsu@gmail.com>
# Use of this source code is governed by GPLv3 license that can be found
# in http://www.gnu.org/licenses/gpl-3.0.html

'''This module contains some useful functions to handle encoding/decoding

just like escape(), encodeURLComponent()... in javascript.
'''

import base64
import hashlib
import json
from urllib import parse

def md5(text):
    return hashlib.md5(text.encode()).hexdigest()

def sha1(text):
    return hashlib.sha1(text.encode()).hexdigest()

def sha224(text):
    return hashlib.sha224(text.encode()).hexdigest()

def sha256(text):
    return hashlib.sha256(text.encode()).hexdigest()

def sha384(text):
    return hashlib.sha384(text.encode()).hexdigest()

def sha512(text):
    return hashlib.sha512(text.encode()).hexdigest()

def base64_encode(text):
    return base64.b64encode(text.encode()).decode()

def base64_decode(text):
    try:
        return base64.b64decode(text.encode()).decode()
    except Exception as e:
        return ''

def url_split_param(text):
    return text.replace('&', '\n&')

def url_param_plus(text):
    url = parse.urlparse(text)
    output = []
    if len(url.scheme) > 0:
        output.append(url.scheme)
        output.append('://')
    output.append(url.netloc)
    output.append(url.path)
    if len(url.query) > 0:
        output.append('?')
        output.append(url.query.replace(' ', '+'))
    return ''.join(output)

def escape(text):
    return parse.quote(text)

def unescape(text):
    return parse.unquote(text)

def encode_uri(text):
    return parse.quote(text, safe='~@#$&()*!+=:;,.?/\'')

def decode_uri(text):
    return parse.unquote(text)

def encode_uri_component(text):
    return parse.quote(text, safe='~()*!.\'')

def decode_uri_component(text):
    return parse.unquote(text)

def json_beautify(text):
    try:
        return json.dumps(json.loads(text), indent=4)
    except Exception as e:
        return ''

########NEW FILE########
__FILENAME__ = FolderBrowserDialog

# Copyright (C) 2014 LiuLang <gsushzhsosgsu@gmail.com>
# Use of this source code is governed by GPLv3 license that can be found
# in http://www.gnu.org/licenses/gpl-3.0.html

from gi.repository import GLib
from gi.repository import Gtk

from bcloud import Config
_ = Config._
from bcloud import gutil
from bcloud import pcs
from bcloud.NewFolderDialog import NewFolderDialog

NAME_COL, PATH_COL, EMPTY_COL, LOADED_COL = list(range(4))
NUM = 100

class FolderBrowserDialog(Gtk.Dialog):

    is_loading = False

    def __init__(self, parent, app, title=_('Save to..')):
        self.parent = parent
        self.app = app
        super().__init__(
                title, app.window, Gtk.DialogFlags.MODAL,
                (Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
                 Gtk.STOCK_OK, Gtk.ResponseType.OK))
        self.set_default_size(440, 480)
        self.set_border_width(10)
        self.set_default_response(Gtk.ResponseType.OK)

        box = self.get_content_area()

        control_box = Gtk.Box()
        box.pack_start(control_box, False, False, 0)

        mkdir_button = Gtk.Button.new_with_label(_('Create Folder'))
        control_box.pack_end(mkdir_button, False, False, 0)
        mkdir_button.connect('clicked', self.on_mkdir_clicked)

        reload_button = Gtk.Button.new_with_label(_('Reload'))
        control_box.pack_end(reload_button, False, False, 5)
        reload_button.connect('clicked', self.on_reload_clicked)

        scrolled_win = Gtk.ScrolledWindow()
        box.pack_start(scrolled_win, True, True, 5)

        # disname, path, empty, loaded
        self.treestore = Gtk.TreeStore(str, str, bool, bool)
        self.treeview = Gtk.TreeView(model=self.treestore)
        self.selection = self.treeview.get_selection()
        scrolled_win.add(self.treeview)
        icon_cell = Gtk.CellRendererPixbuf(icon_name='folder')
        name_cell = Gtk.CellRendererText()
        name_col = Gtk.TreeViewColumn(_('Folder'))
        name_col.pack_start(icon_cell, False)
        name_col.pack_start(name_cell, True)
        if Config.GTK_LE_36:
            name_col.add_attribute(name_cell, 'text', NAME_COL)
        else:
            name_col.set_attributes(name_cell, text=NAME_COL)
        self.treeview.append_column(name_col)
        self.treeview.connect('row-expanded', self.on_row_expanded)

        box.show_all()

        self.reset()

    def reset(self):
        self.treestore.clear()
        root_iter = self.treestore.append(None, ['/', '/', False, False,])
        GLib.timeout_add(500, self.list_dir, root_iter)

    def list_dir(self, parent_iter):
        if self.treestore[parent_iter][LOADED_COL]:
            return
        tree_path = self.treestore.get_path(parent_iter)
        path = self.treestore[tree_path][PATH_COL]
        first_child_iter = self.treestore.iter_nth_child(parent_iter, 0)
        if (first_child_iter and
                not self.treestore[first_child_iter][NAME_COL]):
            self.treestore.remove(first_child_iter)
        has_next = True
        page_num = 1
        while has_next:
            infos = pcs.list_dir(
                    self.app.cookie, self.app.tokens, path,
                    page=page_num, num=NUM)
            page_num = page_num + 1
            if not infos or infos['errno'] != 0:
                has_next = False
                return
            if len(infos['list']) < NUM:
                has_next = False
            for pcs_file in infos['list']:
                if not pcs_file['isdir']:
                    continue
                if pcs_file['dir_empty']:
                    empty = True
                else:
                    empty = False
                item = self.treestore.append(parent_iter, [
                    pcs_file['server_filename'],
                    pcs_file['path'],
                    empty,
                    False,
                    ])
                # 加入一个临时的占位点.
                if not empty:
                    self.treestore.append(item, [
                        '', pcs_file['path'], True, False])
        self.treestore[parent_iter][LOADED_COL] = True

    def get_path(self):
        '''获取选择的路径, 如果没有选择, 就返回空.'''
        model, tree_iter = self.selection.get_selected()
        if not tree_iter:
            return ''
        else:
            return model[tree_iter][PATH_COL]

    def on_reload_clicked(self, button):
        self.reset()

    def on_mkdir_clicked(self, button):
        path = self.get_path()
        dialog = NewFolderDialog(self, self.app, path)
        dialog.run()
        dialog.destroy()
        self.reset()

    def on_row_expanded(self, treeview, tree_iter, tree_path):
        if self.is_loading:
            return
        self.is_loading = True
        self.list_dir(tree_iter)
        self.is_loading = False
        self.treeview.expand_row(tree_path, False)

########NEW FILE########
__FILENAME__ = gutil

# Copyright (C) 2014 LiuLang <gsushzhsosgsu@gmail.com>
# Use of this source code is governed by GPLv3 license that can be found
# in http://www.gnu.org/licenses/gpl-3.0.html

import json
import os
import subprocess
import threading

import dbus
from gi.repository import GdkPixbuf
from gi.repository import Gio
from gi.repository import Gtk
from gi.repository import GLib
import keyring

from bcloud import Config
from bcloud import net
from bcloud import util

DEFAULT_PROFILE = {
    'version': Config.VERSION,
    'window-size': (960, 680),
    'use-status-icon': True,
    'use-dark-theme': True, # 默认启动深色主题
    'use-notify': True,
    'first-run': True,
    'save-dir': Config.HOME_DIR,
    'use-streaming': True,  # 使用流媒体方式播放视频
    'concurr-tasks': 2,     # 下载/上传同时进行的任务数, 1~5
    'username': '',
    'password': '',
    'remember-password': False,
    'auto-signin': False,
    'upload-hidden-files': True,  # 同时上传隐藏文件.
    }
RETRIES = 5   # 调用keyring模块与libgnome-keyring交互的尝试次数

# calls f on another thread
def async_call(func, *args, callback=None):
    def do_call():
        result = None
        error = None

        try:
            result = func(*args)
        except Exception as e:
            error = e
        if callback:
            GLib.idle_add(callback, result, error)

    thread = threading.Thread(target=do_call)
    thread.daemon = True
    thread.start()

def xdg_open(uri):
    '''使用桌面环境中默认的程序打开指定的URI
    
    当然, 除了URI格式之外, 也可以是路径名, 文件名, 比如:
    xdg_open('/etc/issue')
    推荐使用Gio.app_info_xx() 来启动一般程序, 而用xdg_open() 来打开目录.
    '''
    try:
        subprocess.call(['xdg-open', uri, ])
    except FileNotFoundError as e:
        print(e)

def update_liststore_image(liststore, tree_iter, col, pcs_file,
                           dir_name, icon_size=96):
    '''下载文件缩略图, 并将它显示到liststore里.
    
    pcs_file - 里面包含了几个必要的字段.
    dir_name - 缓存目录, 下载到的图片会保存这个目录里.
    size     - 指定图片的缩放大小, 默认是96px.
    '''
    def _update_image():
        try:
            pix = GdkPixbuf.Pixbuf.new_from_file_at_size(
                    filepath, icon_size, icon_size)
            tree_path = liststore.get_path(tree_iter)
            if tree_path is None:
                return
            liststore[tree_path][col] = pix
        except GLib.GError as e:
            pass

    def _dump_image(req, error=None):
        if error or not req:
            return
        with open(filepath, 'wb') as fh:
            fh.write(req.data)
        # Now, check its mime type
        file_ = Gio.File.new_for_path(filepath)
        file_info = file_.query_info(
                Gio.FILE_ATTRIBUTE_STANDARD_CONTENT_TYPE,
                Gio.FileQueryInfoFlags.NONE)
        content_type = file_info.get_content_type()
        if 'image' in content_type:
            _update_image()

    if 'thumbs' not in pcs_file:
        return
    if 'url1' in pcs_file['thumbs']:
        key = 'url1'
    elif 'url2' in pcs_file['thumbs']:
        key = 'url2'
    else:
        return
    fs_id = pcs_file['fs_id']
    url = pcs_file['thumbs'][key]

    filepath = os.path.join(dir_name, '{0}.jpg'.format(fs_id))
    if os.path.exists(filepath) and os.path.getsize(filepath):
        _update_image()
    else:
        if not url or len(url) < 10:
            return
        async_call(net.urlopen, url, callback=_dump_image)

def ellipse_text(text, length=10):
    if len(text) < length:
        return text
    else:
        return text[:8] + '..'

def load_profile(profile_name):
    '''读取特定帐户的配置信息

    有时, dbus会出现连接错误, 这里会进行重试. 但如果超过最大尝试次数, 就
    会失效, 此时, profile['password'] 是一个空字符串, 所以在下一步, 应该去
    检查一下password是否有效, 如果无效, 应该提醒用户.
    '''
    path = os.path.join(Config.CONF_DIR, profile_name)
    if not os.path.exists(path):
        return DEFAULT_PROFILE
    with open(path) as fh:
        profile = json.load(fh)

    for key in DEFAULT_PROFILE:
        if key not in profile:
            profile[key] = DEFAULT_PROFILE[key]

    for i in range(RETRIES):
        try:
            password = keyring.get_password(
                    Config.DBUS_APP_NAME, profile['username'])
            break
        except dbus.exceptions.DBusException as e:
            print(e)
    if password:
        profile['password'] = password
    return profile

def dump_profile(profile):
    '''保存帐户的配置信息.

    这里会检查用户是否愿意保存密码, 如果需要保存密码的话, 就调用keyring来存
    放密码.
    但如果密码为空, 就不再存放它了.
    '''
    profile = profile.copy()
    path = os.path.join(Config.CONF_DIR, profile['username'])
    if profile['remember-password'] and profile['password']:
        for i in range(RETRIES):
            try:
                keyring.set_password(
                        Config.DBUS_APP_NAME, profile['username'],
                        profile['password'])
                break
            except dbus.exceptions.DBusException as e:
                print(e)
    profile['password'] = ''
    with open(path, 'w') as fh:
        json.dump(profile, fh)

def reach_scrolled_bottom(adj):
    '''在ScrolledWindow里面, 滚动到了底部, 就需要尝试载入下一页的内容'''
    return (adj.get_upper() - adj.get_page_size() - adj.get_value()) < 80

def tree_model_natsort(model, row1, row2, user_data=None):
    '''用natural sorting算法对TreeModel的一个column进行排序'''
    sort_column, sort_type = model.get_sort_column_id()
    value1 = model.get_value(row1, sort_column)
    value2 = model.get_value(row2, sort_column)
    sort_list1 = util.natsort(value1)
    sort_list2 = util.natsort(value2)
    status = sort_list1 < sort_list2
    if sort_list1 < sort_list2:
        return -1
    else:
        return 1

def escape(tooltip):
    '''Escape special characters in tooltip text'''
    return GLib.markup_escape_text(tooltip)

def text_buffer_get_all_text(buf):
    '''Get all text in a GtkTextBuffer'''
    return buf.get_text(buf.get_start_iter(), buf.get_end_iter(), False)

########NEW FILE########
__FILENAME__ = hasher

# Copyright (C) 2014 LiuLang <gsushzhsosgsu@gmail.com>
# Use of this source code is governed by GPLv3 license that can be found
# in http://www.gnu.org/licenses/gpl-3.0.html

import hashlib
import os
import zlib

CHUNK = 2 ** 20


def crc(path):
    _crc = 0
    fh = open(path, 'rb')
    while True:
        chunk = fh.read(CHUNK)
        if not chunk:
            break
        _crc = zlib.crc32(chunk, _crc)
    fh.close()
    return '%X' % (_crc & 0xFFFFFFFF)

def md5(path, start=0, stop=-1):
    _md5 = hashlib.md5()
    fh = open(path, 'rb')
    if start > 0:
        fh.seek(start)
    if stop == -1:
        stop = os.path.getsize(path)
    pos = start
    while pos < stop:
        size = min(CHUNK, stop - pos)
        chunk = fh.read(size)
        if not chunk:
            break
        pos += len(chunk)
        _md5.update(chunk)
    fh.close()
    return _md5.hexdigest()

def sha1(path):
    _sha1 = hashlib.sha1()
    fh = open(path, 'rb')
    while True:
        chunk = fh.read(CHUNK)
        if not chunk:
            break
        _sha1.update(chunk)
    fh.close()
    return _sha1.hexdigest()

def sha224(path):
    _sha224 = hashlib.sha224()
    fh = open(path, 'rb')
    while True:
        chunk = fh.read(CHUNK)
        if not chunk:
            break
        _sha224.update(chunk)
    fh.close()
    return _sha224.hexdigest()

def sha256(path):
    _sha256 = hashlib.sha256()
    fh = open(path, 'rb')
    while True:
        chunk = fh.read(CHUNK)
        if not chunk:
            break
        _sha256.update(chunk)
    fh.close()
    return _sha256.hexdigest()

def sha384(path):
    _sha384 = hashlib.sha384()
    fh = open(path, 'rb')
    while True:
        chunk = fh.read(CHUNK)
        if not chunk:
            break
        _sha384.update(chunk)
    fh.close()
    return _sha384.hexdigest()

def sha512(path):
    _sha512 = hashlib.sha512()
    fh = open(path, 'rb')
    while True:
        chunk = fh.read(CHUNK)
        if not chunk:
            break
        _sha512.update(chunk)
    fh.close()
    return _sha512.hexdigest()

########NEW FILE########
__FILENAME__ = HomePage

# Copyright (C) 2014 LiuLang <gsushzhsosgsu@gmail.com>
# Use of this source code is governed by GPLv3 license that can be found
# in http://www.gnu.org/licenses/gpl-3.0.html

from gi.repository import Gdk
from gi.repository import Gtk

from bcloud import Config
_ = Config._
from bcloud.IconWindow import IconWindow
from bcloud.IconWindow import TreeWindow
from bcloud import gutil
from bcloud import pcs
from bcloud import util

class PathBox(Gtk.Box):

    def __init__(self, parent):
        super().__init__(spacing=0)
        self.parent = parent
        
    def clear_buttons(self):
        buttons = self.get_children()
        for button in buttons:
            self.remove(button)

    def append_button(self, abspath, name):
        button = Gtk.Button.new_with_label(gutil.ellipse_text(name))
        button.abspath = abspath
        button.set_tooltip_text(name)
        self.pack_start(button, False, False, 0)
        button.connect('clicked', self.on_button_clicked)

    def on_button_clicked(self, button):
        self.parent.load(button.abspath)

    def set_path(self, path):
        self.clear_buttons()
        pathlist = util.rec_split_path(path)
        for (abspath, name) in pathlist:
            self.append_button(abspath, name)
        self.show_all()


class HomePage(Gtk.Box):

    icon_name = 'home-symbolic'
    disname = _('Home')
    tooltip = _('Show all of your files on Cloud')
    first_run = False
    page_num = 1
    path = '/'
    has_next = True

    def __init__(self, app):
        super().__init__(orientation=Gtk.Orientation.VERTICAL)
        self.app = app

        # set drop action
        targets = [
            ['text/plain', Gtk.TargetFlags.OTHER_APP, 0],
            ['*.*', Gtk.TargetFlags.OTHER_APP, 1]]
        target_list =[Gtk.TargetEntry.new(*t) for t in targets]
        self.drag_dest_set(
            Gtk.DestDefaults.ALL, target_list, Gdk.DragAction.COPY)

        nav_bar = Gtk.Toolbar()
        nav_bar.get_style_context().add_class(Gtk.STYLE_CLASS_MENUBAR)
        nav_bar.props.show_arrow = False
        nav_bar.props.toolbar_style = Gtk.ToolbarStyle.ICONS
        nav_bar.props.icon_size = Gtk.IconSize.LARGE_TOOLBAR
        self.pack_start(nav_bar, False, False, 0)
        nav_bar.props.valign = Gtk.Align.START

        path_item = Gtk.ToolItem()
        nav_bar.insert(path_item, 0)
        nav_bar.child_set_property(path_item, 'expand', True)
        path_item.props.valign = Gtk.Align.START
        path_win = Gtk.ScrolledWindow()
        path_item.add(path_win)
        path_win.props.valign = Gtk.Align.START
        path_win.props.vscrollbar_policy = Gtk.PolicyType.NEVER
        path_viewport = Gtk.Viewport()
        path_viewport.props.valign = Gtk.Align.START
        path_win.add(path_viewport)
        self.path_box = PathBox(self)
        self.path_box.props.valign = Gtk.Align.START
        path_viewport.add(self.path_box)

        # show loading process
        loading_button = Gtk.ToolItem()
        nav_bar.insert(loading_button, 1)
        loading_button.props.margin_right = 10
        self.loading_spin = Gtk.Spinner()
        loading_button.add(self.loading_spin)
        self.loading_spin.props.valign = Gtk.Align.CENTER

        # search button
        search_button = Gtk.ToggleToolButton()
        search_button.set_label(_('Search'))
        search_button.set_icon_name('search-symbolic')
        search_button.set_tooltip_text(
                _('Search documents and folders by name'))
        search_button.connect('toggled', self.on_search_button_toggled)
        nav_bar.insert(search_button, 2)
        search_button.props.valign = Gtk.Align.START
        search_button.props.margin_right = 10

        # toggle view mode
        list_view_button = Gtk.ToolButton()
        list_view_button.set_label(_('ListView'))
        list_view_button.set_icon_name('list-view-symbolic')
        list_view_button.connect(
                'clicked', self.on_list_view_button_clicked)
        nav_bar.insert(list_view_button, 3)
        list_view_button.props.valign = Gtk.Align.START

        grid_view_button = Gtk.ToolButton()
        grid_view_button.set_label(_('ListView'))
        grid_view_button.set_icon_name('grid-view-symbolic')
        grid_view_button.connect(
                'clicked', self.on_grid_view_button_clicked)
        nav_bar.insert(grid_view_button, 4)
        grid_view_button.props.valign = Gtk.Align.START

        # serch entry
        if Config.GTK_LE_36:
            self.search_entry = Gtk.Entry()
            self.search_entry.set_icon_from_icon_name(
                    Gtk.EntryIconPosition.PRIMARY,
                    'folder-saved-search-symbolic')
        else:
            self.search_entry = Gtk.SearchEntry()
        self.search_entry.props.no_show_all = True
        self.search_entry.props.visible = False
        self.search_entry.connect(
                'activate', self.on_search_entry_activated)
        self.pack_start(self.search_entry, False, False, 0)

        self.icon_window = IconWindow(self, app)
        self.pack_end(self.icon_window, True, True, 0)

    def do_drag_data_received(self, drag_context, x, y, data, info, time):
        uris = data.get_text()
        source_paths = util.uris_to_paths(uris)
        if source_paths and self.app.profile:
            self.app.upload_page.add_file_tasks(source_paths, self.path)

    # Open API
    def load(self, path='/'):
        self.path = path
        self.page_num = 1
        self.has_next = True
        self.path_box.set_path(path)
        self.loading_spin.start()
        self.loading_spin.show_all()
        gutil.async_call(
                pcs.list_dir, self.app.cookie, self.app.tokens, self.path,
                self.page_num, callback=self.on_load)
        gutil.async_call(
                pcs.get_quota, self.app.cookie, self.app.tokens,
                callback=self.app.update_quota)

    def on_load(self, info, error=None):
        self.loading_spin.stop()
        self.loading_spin.hide()
        if error or not info or info['errno'] != 0:
            return
        self.icon_window.load(info['list'])

    def load_next(self):
        '''载入下一页'''
        def on_load_next(info, error=None):
            self.loading_spin.stop()
            self.loading_spin.hide()
            if error or not info or info['errno'] != 0:
                return
            if info['list']:
                self.icon_window.load_next(info['list'])
            else:
                self.has_next = False

        if not self.has_next:
            return
        self.page_num = self.page_num + 1
        self.path_box.set_path(self.path)
        self.loading_spin.start()
        self.loading_spin.show_all()
        gutil.async_call(
                pcs.list_dir, self.app.cookie, self.app.tokens, self.path,
                self.page_num, callback=on_load_next)

    def reload(self, *args, **kwds):
        '''重新载入本页面'''
        self.load(self.path)

    def on_search_button_toggled(self, search_button):
        status = search_button.get_active()
        self.search_entry.props.visible = status
        if status:
            self.search_entry.grab_focus()
        else:
            self.reload()

    def on_list_view_button_clicked(self, button):
        if not isinstance(self.icon_window, TreeWindow):
            self.remove(self.icon_window)
            self.icon_window = TreeWindow(self, self.app)
            self.pack_end(self.icon_window, True, True, 0)
            self.icon_window.show_all()
            self.reload()

    def on_grid_view_button_clicked(self, button):
        if isinstance(self.icon_window, TreeWindow):
            self.remove(self.icon_window)
            self.icon_window = IconWindow(self, self.app)
            self.pack_end(self.icon_window, True, True, 0)
            self.icon_window.show_all()
            self.reload()

    def on_search_entry_activated(self, search_entry):
        text = search_entry.get_text()
        if not text:
            return
        self.loading_spin.start()
        self.loading_spin.show_all()
        gutil.async_call(
                pcs.search, self.app.cookie, self.app.tokens, text,
                self.path, callback=self.on_load)

########NEW FILE########
__FILENAME__ = IconWindow

# Copyright (C) 2014 LiuLang <gsushzhsosgsu@gmail.com>
# Use of this source code is governed by GPLv3 license that can be found
# in http://www.gnu.org/licenses/gpl-3.0.html

import mimetypes
import json
import os
import time

from gi.repository import Gdk
from gi.repository import GdkPixbuf
from gi.repository import Gio
from gi.repository import GObject
from gi.repository import Gtk
from gi.repository import Pango

from bcloud import Config
_ = Config._
from bcloud.FolderBrowserDialog import FolderBrowserDialog
from bcloud.NewFolderDialog import NewFolderDialog
from bcloud.PropertiesDialog import PropertiesDialog
from bcloud.PropertiesDialog import FolderPropertyDialog
from bcloud.RenameDialog import RenameDialog
from bcloud import gutil
from bcloud import pcs
from bcloud import util

(PIXBUF_COL, NAME_COL, PATH_COL, TOOLTIP_COL, SIZE_COL, HUMAN_SIZE_COL,
    ISDIR_COL, MTIME_COL, HUMAN_MTIME_COL, TYPE_COL, PCS_FILE_COL
    ) = list(range(11))
TYPE_TORRENT = 'application/x-bittorrent'

class IconWindow(Gtk.ScrolledWindow):
    '''这个类用于获取文件, 并将它显示到IconView中去.

    可以作为其它页面的一个主要组件.
    其中的网络操作部分多半是异步进行的.
    '''

    ICON_SIZE = 64

    def __init__(self, parent, app):
        super().__init__()
        self.parent = parent
        self.app = app

        # pixbuf, name, path, tooltip, size, humansize,
        # isdir, mtime, human mtime, type, pcs_file
        self.liststore = Gtk.ListStore(
            GdkPixbuf.Pixbuf, str, str, str, GObject.TYPE_INT64, str,
            GObject.TYPE_INT, GObject.TYPE_INT64, str, str, str)
        self.init_ui()

    def init_ui(self):
        self.iconview = Gtk.IconView(model=self.liststore)
        self.iconview.set_pixbuf_column(PIXBUF_COL)
        self.iconview.set_text_column(NAME_COL)
        self.iconview.set_tooltip_column(TOOLTIP_COL)
        self.iconview.set_item_width(84)
        self.iconview.set_selection_mode(Gtk.SelectionMode.MULTIPLE)
        self.iconview.connect(
                'item-activated', self.on_iconview_item_activated)
        self.iconview.connect(
                'button-press-event', self.on_iconview_button_pressed)
        self.add(self.iconview)
        self.get_vadjustment().connect('value-changed', self.on_scrolled)
        self.liststore.set_sort_func(NAME_COL, gutil.tree_model_natsort)

    def load(self, pcs_files):
        '''载入一个目录并显示里面的内容.'''
        self.liststore.clear()
        self.display_files(pcs_files)

    def load_next(self, pcs_files):
        '''当滚动条向下滚动到一定位置时, 调用这个方法载入下一页'''
        self.display_files(pcs_files)

    def display_files(self, pcs_files):
        '''重新格式化一下文件列表, 去除不需要的信息

        这一操作主要是为了便于接下来的查找工作.
        文件的path都被提取出来, 然后放到了一个list中.
        '''
        cache_path = Config.get_cache_path(self.app.profile['username'])
        for pcs_file in pcs_files:
            path = pcs_file['path']
            pixbuf, type_ = self.app.mime.get(
                    path, pcs_file['isdir'], icon_size=self.ICON_SIZE)
            name = os.path.split(path)[NAME_COL]
            tooltip = gutil.escape(name)
            size = pcs_file.get('size', 0)
            human_size = util.get_human_size(pcs_file['size'])[0]
            mtime = pcs_file.get('server_mtime', 0)
            human_mtime = time.ctime(mtime)
            tree_iter = self.liststore.append([
                pixbuf, name, path, tooltip, size, human_size,
                pcs_file['isdir'], mtime, human_mtime, type_,
                json.dumps(pcs_file), ])
            gutil.update_liststore_image(
                self.liststore, tree_iter, PIXBUF_COL, pcs_file,
                cache_path, icon_size=self.ICON_SIZE)

    def get_pcs_file(self, tree_path):
        '''获取原始的pcs文件信息'''
        return json.loads(self.liststore[tree_path][PCS_FILE_COL])

    def on_scrolled(self, adj):
        if gutil.reach_scrolled_bottom(adj) and self.parent.has_next:
            self.parent.load_next()

    def on_iconview_item_activated(self, iconview, tree_path):
        path = self.liststore[tree_path][PATH_COL]
        type_ = self.liststore[tree_path][TYPE_COL]
        if type_ == 'folder':
            self.app.home_page.load(path)
        else:
            self.launch_app(tree_path)

    def on_iconview_button_pressed(self, iconview, event):
        if ((event.type != Gdk.EventType.BUTTON_PRESS) or
                (event.button != Gdk.BUTTON_SECONDARY)):
            return

        tree_path = self.iconview.get_path_at_pos(event.x, event.y)
        selected_tree_paths = self.iconview.get_selected_items()

        if tree_path is None:
            self.iconview.unselect_all()
            self.popup_folder_menu(event)
        else:
            modified = ((event.state & Gdk.ModifierType.CONTROL_MASK) |
                    (event.state & Gdk.ModifierType.SHIFT_MASK))
            if not modified and tree_path not in selected_tree_paths:
                self.iconview.unselect_all()
            self.iconview.select_path(tree_path)
            self.popup_item_menu(event)

    def popup_folder_menu(self, event):
        # create folder; reload; share; properties
        menu = Gtk.Menu()
        self.menu = menu
        
        new_folder_item = Gtk.MenuItem.new_with_label(_('New Folder'))
        new_folder_item.connect('activate', self.on_new_folder_activated)
        menu.append(new_folder_item)

        sep_item = Gtk.SeparatorMenuItem()
        menu.append(sep_item)
        reload_item = Gtk.MenuItem.new_with_label(_('Reload'))
        reload_item.connect('activate', self.on_reload_activated)
        menu.append(reload_item)

        sep_item = Gtk.SeparatorMenuItem()
        menu.append(sep_item)
        props_item = Gtk.MenuItem.new_with_label(_('Properties'))
        props_item.connect('activate', self.on_props_activated)
        menu.append(props_item)

        menu.show_all()
        menu.popup(None, None, None, None, event.button, event.time)

    def popup_item_menu(self, event):
        # 要检查选中的条目数, 如果选中多个, 只显示出它们共有的一些菜单项:
        # share; rename; delete; copy to; move to; download;
        def build_app_menu(menu, menu_item, app_info):
            menu_item.set_always_show_image(True)
            img = self.app.mime.get_app_img(app_info)
            if img:
                menu_item.set_image(img)
            menu_item.connect(
                    'activate', self.on_launch_app_activated, app_info)
            menu.append(menu_item)

        tree_paths = self.iconview.get_selected_items()
        menu = Gtk.Menu()
        # 将这个menu标记为对象的属性, 不然很快它就会被回收, 就无法显示出菜单
        self.menu = menu

        if len(tree_paths) == 1:
            tree_path = tree_paths[0]
            file_type = self.liststore[tree_path][TYPE_COL]
            if file_type == 'folder':
                open_dir_item = Gtk.MenuItem.new_with_label(_('Open'))
                open_dir_item.connect(
                        'activate', self.on_open_dir_item_activated)
                menu.append(open_dir_item)
            # 不是目录的话, 就显示出程序菜单
            else:
                if file_type == TYPE_TORRENT:
                    cloud_download_item = Gtk.MenuItem.new_with_label(
                            _('Cloud Download'))
                    cloud_download_item.connect(
                            'activate',
                            self.on_cloud_download_item_activated)
                    menu.append(cloud_download_item)
                app_infos = Gio.AppInfo.get_recommended_for_type(file_type)
                # 第一个app_info是默认的app.
                if len(app_infos) > 2:
                    app_info = app_infos[0]
                    launch_item = Gtk.ImageMenuItem.new_with_label(
                        _('Open With {0}').format(
                            app_info.get_display_name()))
                    build_app_menu(menu, launch_item, app_info)

                    more_app_item = Gtk.MenuItem.new_with_label(
                            _('Open With'))
                    menu.append(more_app_item)
                    sub_menu = Gtk.Menu()
                    more_app_item.set_submenu(sub_menu)

                    for app_info in app_infos[1:]:
                        launch_item = Gtk.ImageMenuItem.new_with_label(
                                app_info.get_display_name())
                        build_app_menu(sub_menu, launch_item, app_info)
                    sep_item = Gtk.SeparatorMenuItem()
                    sub_menu.append(sep_item)
                    choose_app_item = Gtk.MenuItem.new_with_label(
                            _('Other Application...'))
                    choose_app_item.connect(
                            'activate', self.on_choose_app_activated)
                    sub_menu.append(choose_app_item)
                else:
                    for app_info in app_infos:
                        launch_item = Gtk.ImageMenuItem.new_with_label(
                            _('Open With {0}').format(
                                app_info.get_display_name()))
                        build_app_menu(menu, launch_item, app_info)
                    choose_app_item = Gtk.MenuItem.new_with_label(
                            _('Open With Other Application...'))
                    choose_app_item.connect(
                            'activate', self.on_choose_app_activated)
                    menu.append(choose_app_item)

                sep_item = Gtk.SeparatorMenuItem()
                menu.append(sep_item)
                copy_link_item = Gtk.MenuItem.new_with_label(_('Copy Link'))
                copy_link_item.connect(
                        'activate', self.on_copy_link_activated)
                menu.append(copy_link_item)

            sep_item = Gtk.SeparatorMenuItem()
            menu.append(sep_item)

        download_item = Gtk.MenuItem.new_with_label(_('Download...'))
        download_item.connect('activate', self.on_download_activated)
        menu.append(download_item)
        share_item = Gtk.MenuItem.new_with_label(_('Share...'))
        share_item.connect('activate', self.on_share_activated)
        menu.append(share_item)

        sep_item = Gtk.SeparatorMenuItem()
        menu.append(sep_item)
        moveto_item = Gtk.MenuItem.new_with_label(_('Move To...'))
        moveto_item.connect('activate', self.on_moveto_activated)
        menu.append(moveto_item)
        copyto_item = Gtk.MenuItem.new_with_label(_('Copy To...'))
        copyto_item.connect('activate', self.on_copyto_activated)
        menu.append(copyto_item)
        rename_item = Gtk.MenuItem.new_with_label(_('Rename...'))
        rename_item.connect('activate', self.on_rename_activated)
        menu.append(rename_item)

        sep_item = Gtk.SeparatorMenuItem()
        menu.append(sep_item)
        trash_item = Gtk.MenuItem.new_with_label(_('Move to Trash'))
        trash_item.connect('activate', self.on_trash_activated)
        menu.append(trash_item)

        sep_item = Gtk.SeparatorMenuItem()
        menu.append(sep_item)
        props_item = Gtk.MenuItem.new_with_label(_('Properties'))
        props_item.connect('activate', self.on_props_activated)
        menu.append(props_item)

        menu.show_all()
        menu.popup(None, None, None, None, 0, event.time)

    # current folder popup menu
    def on_new_folder_activated(self, menu_item):
        dialog = NewFolderDialog(self.parent, self.app, self.parent.path)
        dialog.run()
        dialog.destroy()

    def on_reload_activated(self, menu_item):
        self.parent.reload()

    def launch_app(self, tree_path):
        '''用默认的程序打开这个文件链接.'''
        file_type = self.liststore[tree_path][TYPE_COL]
        app_infos = Gio.AppInfo.get_recommended_for_type(file_type)
        if app_infos:
            self.launch_app_with_app_info(app_infos[0])
        else:
            pass

    def launch_app_with_app_info(self, app_info):
        def open_video_link(red_url, error=None):
            '''得到视频最后地址后, 调用播放器直接播放'''
            if error or not red_url:
                return
            gutil.async_call(app_info.launch_uris, [red_url, ], None)

        def save_playlist(pls, error=None):
            '''先保存播放列表到临时目录, 再调用播放器直接打开这个播放列表

            如果pls为None的话, 说明没能得到播放列表, 这时就需要使用之前的方
            法, 先得琶视频地址, 再用播放器去打开它.
            '''
            if error or not pls or b'error_code' in pls:
                gutil.async_call(
                        pcs.get_download_link, self.app.cookie,
                        self.app.tokens,
                        self.liststore[tree_paths[0]][PATH_COL],
                        callback=open_video_link)
            else:
                pls_filepath = os.path.join(
                        '/tmp', pcs_file['server_filename'] + '.m3u8')
                with open(pls_filepath, 'wb') as fh:
                    fh.write(pls)
                pls_file_uri = 'file://' + pls_filepath
                app_info.launch_uris([pls_file_uri, ], None)

        # first, download this to load dir
        # then open it with app_info
        tree_paths = self.iconview.get_selected_items()
        if not tree_paths:
            return
        tree_path = tree_paths[0]
        file_type = self.liststore[tree_path][TYPE_COL]
        pcs_file = self.get_pcs_file(tree_path)
        # 'media' 对应于rmvb格式.
        # 如果是视频等多媒体格式的话, 默认是直接调用播放器进行网络播放的
        if 'video' in file_type or 'media' in file_type:
            if self.app.profile['use-streaming']:
                gutil.async_call(
                        pcs.get_streaming_playlist, self.app.cookie,
                        pcs_file['path'], callback=save_playlist)
            else:
                gutil.async_call(
                        pcs.get_download_link, self.app.cookie,
                        self.app.tokens,
                        self.liststore[tree_paths[0]][PATH_COL],
                        callback=open_video_link)
        else:
            self.app.blink_page(self.app.download_page)
            self.app.download_page.add_launch_task(pcs_file, app_info)

    # item popup menu
    def on_launch_app_activated(self, menu_item, app_info):
        self.launch_app_with_app_info(app_info)

    def on_choose_app_activated(self, menu_item):
        tree_paths = self.iconview.get_selected_items()
        if not tree_paths or len(tree_paths) != 1:
            return
        tree_path = tree_paths[0]
        type_ = self.liststore[tree_path][TYPE_COL]
        dialog = Gtk.AppChooserDialog.new_for_content_type(
                self.app.window, Gtk.DialogFlags.MODAL,
                type_)
        response = dialog.run()
        app_info = dialog.get_app_info()
        dialog.destroy()
        if response != Gtk.ResponseType.OK:
            return
        self.launch_app_with_app_info(app_info)

    def on_open_dir_item_activated(self, menu_item):
        tree_paths = self.iconview.get_selected_items()
        if tree_paths and len(tree_paths) == 1:
            self.parent.load(self.liststore[tree_paths[0]][PATH_COL])

    def on_cloud_download_item_activated(self, menu_item):
        '''创建离线下载任务, 下载选中的BT种子.'''
        tree_paths = self.iconview.get_selected_items()
        if not tree_paths:
            return
        self.app.cloud_page.add_cloud_bt_task(
            self.liststore[tree_paths[0]][PATH_COL])

    def on_copy_link_activated(self, menu_item):
        def copy_link_to_clipboard(url, error=None):
            if error or not url:
                return
            self.app.update_clipboard(url)

        tree_paths = self.iconview.get_selected_items()
        if not tree_paths:
            return
        gutil.async_call(
                pcs.get_download_link, self.app.cookie, self.app.tokens,
                self.liststore[tree_paths[0]][PATH_COL],
                callback=copy_link_to_clipboard)

    def on_download_activated(self, menu_item):
        # 下载文件与下载目录的操作是不相同的.
        tree_paths = self.iconview.get_selected_items()
        if not tree_paths:
            return
        pcs_files = [self.get_pcs_file(p) for p in tree_paths]
        self.app.blink_page(self.app.download_page)
        self.app.download_page.add_tasks(pcs_files)

    def on_share_activated(self, menu_item):
        def on_share(info, error=None):
            if error or not info or info['errno'] != 0:
                self.app.toast(_('Failed to share selected files'))
                return
            self.app.update_clipboard(info['shorturl'])

        tree_paths = self.iconview.get_selected_items()
        if not tree_paths:
            return
        fid_list = []
        for tree_path in tree_paths:
            pcs_file = self.get_pcs_file(tree_path)
            fid_list.append(pcs_file['fs_id'])
            gutil.async_call(
                    pcs.enable_share, self.app.cookie, self.app.tokens,
                    fid_list, callback=on_share)

    def on_moveto_activated(self, menu_item):
        tree_paths = self.iconview.get_selected_items()
        if not tree_paths:
            return

        dialog = FolderBrowserDialog(self.parent, self.app, _('Move To...'))
        response = dialog.run()
        targ_path = ''
        if response != Gtk.ResponseType.OK:
            dialog.destroy()
            return
        targ_path = dialog.get_path()
        dialog.destroy()

        filelist = []
        for tree_path in tree_paths:
            filelist.append({
                'path': self.liststore[tree_path][PATH_COL],
                'dest': targ_path,
                'newname': self.liststore[tree_path][NAME_COL],
                })
        gutil.async_call(
                pcs.move,
                self.app.cookie, self.app.tokens, filelist,
                callback=self.parent.reload)

    def on_copyto_activated(self, menu_item):
        tree_paths = self.iconview.get_selected_items()
        if not tree_paths:
            return

        dialog = FolderBrowserDialog(self.parent, self.app, _('Copy To...'))
        response = dialog.run()
        targ_path = ''
        if response != Gtk.ResponseType.OK:
            dialog.destroy()
            return
        targ_path = dialog.get_path()
        dialog.destroy()

        filelist = []
        for tree_path in tree_paths:
            filelist.append({
                'path': self.liststore[tree_path][PATH_COL],
                'dest': targ_path,
                'newname': self.liststore[tree_path][NAME_COL],
                })
        gutil.async_call(
                pcs.copy,
                self.app.cookie, self.app.tokens, filelist,
                callback=self.parent.reload)

    def on_rename_activated(self, menu_item):
        tree_paths = self.iconview.get_selected_items()
        if not tree_paths:
            return
        path_list = []
        for tree_path in tree_paths:
            path_list.append(self.liststore[tree_path][PATH_COL])
        dialog = RenameDialog(self.app, path_list)
        dialog.run()
        dialog.destroy()

    def on_trash_activated(self, menu_item):
        tree_paths = self.iconview.get_selected_items()
        if not tree_paths:
            return
        path_list = []
        for tree_path in tree_paths:
            path_list.append(self.liststore[tree_path][PATH_COL])
        gutil.async_call(
                pcs.delete_files, self.app.cookie, self.app.tokens,
                path_list, callback=self.parent.reload)
        self.app.blink_page(self.app.trash_page)

    def on_props_activated(self, menu_item):
        '''显示选中的文件或者当前目录的属性'''
        tree_paths = self.iconview.get_selected_items()
        if not tree_paths:
            dialog = FolderPropertyDialog(self, self.app, self.parent.path)
            dialog.run()
            dialog.destroy()
        else:
            for tree_path in tree_paths:
                pcs_file = self.get_pcs_file(tree_path)
                dialog = PropertiesDialog(self.parent, self.app, pcs_file)
                dialog.run()
                dialog.destroy()


class TreeWindow(IconWindow):

    ICON_SIZE = 24

    def __init__(self, parent, app):
        super().__init__(parent, app)

    # Override
    def init_ui(self):
        self.iconview = Gtk.TreeView(model=self.liststore)
        self.iconview.set_tooltip_column(TOOLTIP_COL)
        self.iconview.connect(
                'row-activated',
                lambda view, path, column:
                    self.on_iconview_item_activated(view, path))
        self.iconview.connect(
                'button-press-event', self.on_iconview_button_pressed)
        self.get_vadjustment().connect('value-changed', self.on_scrolled)
        self.iconview.set_headers_clickable(True)
        self.iconview.set_reorderable(True)
        self.iconview.set_search_column(NAME_COL)
        self.selection = self.iconview.get_selection()
        self.selection.set_mode(Gtk.SelectionMode.MULTIPLE)
        self.add(self.iconview)

        icon_cell = Gtk.CellRendererPixbuf()
        name_cell = Gtk.CellRendererText(
                ellipsize=Pango.EllipsizeMode.END, ellipsize_set=True)
        name_col = Gtk.TreeViewColumn()
        name_col.set_title(_('Name'))
        name_col.pack_start(icon_cell, False)
        name_col.pack_start(name_cell, True)
        if Config.GTK_LE_36:
            name_col.add_attribute(icon_cell, 'pixbuf', PIXBUF_COL)
            name_col.add_attribute(name_cell, 'text', NAME_COL)
        else:
            name_col.set_attributes(icon_cell, pixbuf=PIXBUF_COL)
            name_col.set_attributes(name_cell, text=NAME_COL)
        name_col.set_expand(True)
        name_col.set_resizable(True)
        self.iconview.append_column(name_col)
        name_col.set_sort_column_id(NAME_COL)
        self.liststore.set_sort_func(NAME_COL, gutil.tree_model_natsort)

        size_cell = Gtk.CellRendererText()
        size_col = Gtk.TreeViewColumn(
                _('Size'), size_cell, text=HUMAN_SIZE_COL)
        self.iconview.append_column(size_col)
        size_col.props.min_width = 100
        size_col.set_resizable(True)
        size_col.set_sort_column_id(SIZE_COL)

        mtime_cell = Gtk.CellRendererText()
        mtime_col = Gtk.TreeViewColumn(
                _('Modified'), mtime_cell, text=HUMAN_MTIME_COL)
        self.iconview.append_column(mtime_col)
        mtime_col.props.min_width = 100
        mtime_col.set_resizable(True)
        mtime_col.set_sort_column_id(MTIME_COL)

        # Override selection methods
        self.iconview.unselect_all = self.selection.unselect_all
        self.iconview.select_path = self.selection.select_path
        # Gtk.TreeSelection.get_selected_rows() returns (model, tree_paths)
        self.iconview.get_selected_items = lambda: self.selection.get_selected_rows()[1]
        # Gtk.TreeView.get_path_at_pos() returns (path, column)
        def get_path_at_pos(x, y):
            selected = Gtk.TreeView.get_path_at_pos(self.iconview, x, y)
            if selected:
                return selected[0]
            else:
                return None
        self.iconview.get_path_at_pos = get_path_at_pos

########NEW FILE########
__FILENAME__ = MimeProvider
# Copyright (C) 2014 LiuLang <gsushzhsosgsu@gmail.com>
# Use of this source code is governed by GPLv3 license that can be found
# in http://www.gnu.org/licenses/gpl-3.0.html


import mimetypes
# 目前, linux系统中还不支持rmvb的MIME
mimetypes.add_type('application/vnd.rn-realmedia', '.rmvb')

from gi.repository import GdkPixbuf
from gi.repository import Gio
from gi.repository import Gtk

ICON_SIZE = 48
FOLDER = 'folder'
UNKNOWN = 'unknown'

class MimeProvider:
    '''用于提供IconView中显示时需要的缩略图'''

    _data = {}  # 用于存放pixbuf的容器, 以(file_type, icon_size)为key

    def __init__(self, app):
        self.app = app
        # First, load `unknown' icon
        self.get('/foo', False)

    def get_mime(self, path, isdir):
        '''猜测文件类型, 根据它的文件扩展名'''
        if isdir:
            file_type = FOLDER
        else:
            file_type = mimetypes.guess_type(path)[0]
            if not file_type:
                file_type = UNKNOWN
        return file_type

    def get(self, path, isdir, icon_size=ICON_SIZE):
        '''取得一个缩略图.
        
        path - 文件的路径, 可以包括绝对路径, 也可以是文件名.
        isdir - 是否为一个目录.
        icon_size - 图标的大小, 如果是显示在IconView中的, 48就可以;
                    如果是显示在TreView的话, 可以用Gtk.IconSize.MENU

        @return 会返回一个Pixbuf以象, 和这个文件的类型(MIME)
        '''
        file_type = self.get_mime(path, isdir)
        key = (file_type, icon_size)
        if key in self._data:
            return (self._data.get(key), file_type)

        themed_icon = Gio.content_type_get_icon(file_type)
        icon_names = themed_icon.to_string().split(' ')[2:]
        icon_info = self.app.icon_theme.choose_icon(
                icon_names, icon_size, Gtk.IconLookupFlags.GENERIC_FALLBACK)
        if icon_info:
            pixbuf = icon_info.load_icon()
            self._data[key] = pixbuf
            return (pixbuf, file_type)
        else:
            key = (UNKNOWN, icon_size)
            pixbuf = self._data.get(key, None)
            if not pixbuf:
                pixbuf = self.get('/placeholder', isdir, icon_size)[0]
            return (pixbuf, file_type)

    def get_icon_name(self, path, isdir):
        file_type = self.get_mime(path, isdir)
        if file_type in (FOLDER, UNKNOWN):
            return file_type
        icon_name = Gio.content_type_get_generic_icon_name(file_type)
        if icon_name:
            return icon_name
        else:
            return UNKNOWN

    def get_app_img(self, app_info):
        themed_icon = app_info.get_icon()
        if not themed_icon or isinstance(themed_icon, Gio.FileIcon):
            return None
        icon_names = themed_icon.get_names()
        if icon_names:
            img = Gtk.Image.new_from_icon_name(
                    icon_names[0], Gtk.IconSize.MENU)
            return img
        else:
            return None


########NEW FILE########
__FILENAME__ = net

# Copyright (C) 2013-2014 LiuLang <gsushzhsosgsu@gmail.com>
# Use of this source code is governed by GPLv3 license that can be found
# in http://www.gnu.org/licenses/gpl-3.0.html

import gzip
import http
import http.client
import mimetypes
import os
import sys
import urllib.parse
import urllib.request
import zlib

sys.path.insert(0, os.path.dirname(__file__))
import const

RETRIES = 3

default_headers = {
    'User-agent': const.USER_AGENT,
    'Referer': const.PAN_REFERER,
    'x-requested-with': 'XMLHttpRequest',
    'Accept': const.ACCEPT_JSON,
    'Accept-language': 'zh-cn, zh',
    'Accept-encoding': 'gzip, deflate',
    'Pragma': 'no-cache',
    'Cache-control': 'no-cache',
    }

def urloption(url, headers={}, retries=RETRIES):
    '''发送OPTION 请求'''
    headers_merged = default_headers.copy()
    for key in headers.keys():
        headers_merged[key] = headers[key]
    schema = urllib.parse.urlparse(url)
    for _ in range(retries):
        try:
            conn = http.client.HTTPConnection(schema.netloc)
            conn.request('OPTIONS', url, headers=headers_merged)
            resp = conn.getresponse()
            return resp
        except OSError as e:
            print(e)
    return None


class ForbiddenHandler(urllib.request.HTTPErrorProcessor):

    def http_error_403(self, req, fp, code, msg, headers):
        return fp
    http_error_400 = http_error_403
    http_error_500 = http_error_403


def urlopen(url, headers={}, data=None, retries=RETRIES):
    '''打开一个http连接, 并返回Request.

    headers 是一个dict. 默认提供了一些项目, 比如User-Agent, Referer等, 就
    不需要重复加入了.

    这个函数只能用于http请求, 不可以用于下载大文件.
    如果服务器支持gzip压缩的话, 就会使用gzip对数据进行压缩, 然后在本地自动
    解压.
    req.data 里面放着的是最终的http数据内容, 通常都是UTF-8编码的文本.
    '''
    headers_merged = default_headers.copy()
    for key in headers.keys():
        headers_merged[key] = headers[key]
    opener = urllib.request.build_opener(ForbiddenHandler)
    opener.addheaders = [(k, v) for k,v in headers_merged.items()]

    for _ in range(retries):
        try:
            req = opener.open(url, data=data)
            encoding = req.headers.get('Content-encoding')
            req.data = req.read()
            if encoding == 'gzip':
                req.data = gzip.decompress(req.data)
            elif encoding == 'deflate':
                req.data = zlib.decompress(req.data, -zlib.MAX_WBITS)
            return req
        except OSError as e:
            print(e)
    return None

def urlopen_without_redirect(url, headers={}, data=None, retries=RETRIES):
    '''请求一个URL, 并返回一个Response对象. 不处理重定向.

    使用这个函数可以返回URL重定向(Error 301/302)后的地址, 也可以重到URL中请
    求的文件的大小, 或者Header中的其它认证信息.
    '''
    headers_merged = default_headers.copy()
    for key in headers.keys():
        headers_merged[key] = headers[key]

    parse_result = urllib.parse.urlparse(url)
    for _ in range(retries):
        try:
            conn = http.client.HTTPConnection(parse_result.netloc)
            #conn.request('HEAD', url, body=data, headers=headers_merged)
            conn.request('GET', url, body=data, headers=headers_merged)
            return conn.getresponse()
        except OSError as e:
            print(e)
    return None


def post_multipart(url, headers, fields, files, retries=RETRIES):
    content_type, body = encode_multipart_formdata(fields, files)
    schema = urllib.parse.urlparse(url)

    headers_merged = default_headers.copy()
    for key in headers.keys():
        headers_merged[key] = headers[key]
    headers_merged['Content-Type'] = content_type
    headers_merged['Content-length'] = str(len(body))

    for _ in range(retries):
        try:
            h = http.client.HTTPConnection(schema.netloc)
            h.request('POST', url, body=body, headers=headers_merged)
            req = h.getresponse()
            encoding = req.getheader('Content-encoding')
            req.data = req.read()
            if encoding == 'gzip':
                req.data = gzip.decompress(req.data)
            elif encoding == 'deflate':
                req.data = zlib.decompress(req.data, -zlib.MAX_WBITS)
            return req
        except OSError as e:
            print(e)
    return None

def encode_multipart_formdata(fields, files):
    BOUNDARY = b'----------ThIs_Is_tHe_bouNdaRY_$'
    S_BOUNDARY = b'--' + BOUNDARY
    E_BOUNARY = S_BOUNDARY + b'--'
    CRLF = b'\r\n'
    BLANK = b''
    l = []
    for (key, value) in fields:
        l.append(S_BOUNDARY)
        l.append(
            'Content-Disposition: form-data; name="{0}"'.format(key).encode())
        l.append(BLANK)
        l.append(value.encode())
    for (key, filename, content) in files:
        l.append(S_BOUNDARY)
        l.append(
            'Content-Disposition: form-data; name="{0}"; filename="{1}"'.format(
                key, filename).encode())
        l.append(BLANK)
        l.append(content)
    l.append(E_BOUNARY)
    l.append(BLANK)
    body = CRLF.join(l)
    content_type = 'multipart/form-data; boundary={0}'.format(BOUNDARY.decode())
    return content_type, body

def get_content_type(filename):
    return mimetypes.guess_type(filename)[0] or 'application/octet-stream'

########NEW FILE########
__FILENAME__ = NewFolderDialog

# Copyright (C) 2014 LiuLang <gsushzhsosgsu@gmail.com>
# Use of this source code is governed by GPLv3 license that can be found
# in http://www.gnu.org/licenses/gpl-3.0.html

import os

from gi.repository import Gtk

from bcloud import Config
_ = Config._
from bcloud import gutil
from bcloud import pcs

class NewFolderDialog(Gtk.Dialog):
    
    def __init__(self, parent, app, path):
        super().__init__(
                _('New Folder'), app.window, Gtk.DialogFlags.MODAL,
                (Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
                 Gtk.STOCK_OK, Gtk.ResponseType.OK))
        self.set_default_response(Gtk.ResponseType.OK)
        self.connect('show', self.on_show)
        self.set_default_size(550, 200)

        self.app = app
        self.path = path

        self.set_border_width(10)
        box = self.get_content_area()

        folder_name = _('New Folder')
        abspath = os.path.join(path, folder_name)
        self.entry = Gtk.Entry()
        self.entry.set_text(abspath)
        self.entry.connect('activate', self.on_entry_activated)
        box.pack_start(self.entry, True, True, 10)

        box.show_all()

    def on_show(self, *args):
        if len(self.path) == 1:
            self.entry.select_region(1, -1)
        elif len(self.path) > 1:
            self.entry.select_region(len(self.path) + 1, -1)

    def do_response(self, response_id):
        if response_id == Gtk.ResponseType.OK:
            self.do_mkdir()

    def on_entry_activated(self, entry):
        self.do_mkdir()
        self.destroy()

    def do_mkdir(self):
        abspath = self.entry.get_text()
        if abspath.startswith('/'):
            gutil.async_call(
                    pcs.mkdir, self.app.cookie, self.app.tokens, abspath,
                    callback=self.app.reload_current_page)

########NEW FILE########
__FILENAME__ = pcs

# Copyright (C) 2013-2014 LiuLang <gsushzhsosgsu@gmail.com>
# Use of this source code is governed by GPLv3 license that can be found
# in http://www.gnu.org/licenses/gpl-3.0.html

'''
这个模块主要是网盘的文件操作接口.
'''

import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(__file__))
import auth
import const
import encoder
import hasher
import net
from RequestCookie import RequestCookie
import util

RAPIDUPLOAD_THRESHOLD = 256 * 1024  # 256K


def get_quota(cookie, tokens):
    '''获取当前的存储空间的容量信息.'''
    url = ''.join([
        const.PAN_API_URL,
        'quota?channel=chunlei&clienttype=0&web=1',
        '&t=', util.timestamp(),
        ])
    req = net.urlopen(url, headers={
        'Cookie': cookie.header_output(),
        })
    if req:
        content = req.data
        return json.loads(content.decode())
    else:
        return None


def get_user_uk(cookie, tokens):
    '''获取用户的uk'''
    url = 'http://yun.baidu.com'
    req = net.urlopen(url, headers={'Cookie': cookie.header_output()})
    if req:
        content = req.data.decode()
        match = re.findall('/share/home\?uk=(\d+)" target=', content)
        if len(match) == 1:
            return match[0]
    return None

def list_share(cookie, tokens, uk, page=1):
    '''获取用户已经共享的所有文件的信息

    uk   - user key
    page - 页数, 默认为第一页.
    num  - 一次性获取的共享文件的数量, 默认为100个.
    '''
    num = 100
    start = 100 * (page - 1)
    url = ''.join([
        const.PAN_URL,
        'pcloud/feed/getsharelist?',
        '&t=', util.timestamp(),
        '&categor=0&auth_type=1&request_location=share_home',
        '&start=', str(start),
        '&limit=', str(num),
        '&query_uk=', str(uk),
        '&channel=chunlei&clienttype=0&web=1',
        '&bdstoken=', tokens['bdstoken'],
        ])
    req = net.urlopen(url, headers={
        'Cookie': cookie.header_output(),
        'Referer': const.SHARE_REFERER,
        })
    if req:
        content = req.data
        return json.loads(content.decode())
    else:
        return None

def list_share_path(cookie, tokens, uk, path, share_id, page):
    '''列举出用户共享的某一个目录中的文件信息

    uk       - user key
    path     - 共享目录
    share_id - 共享文件的ID值
    '''
    url = ''.join([
        const.PAN_URL,
        'share/list?channel=chunlei&clienttype=0&web=1&num=100',
        '&t=', util.timestamp(),
        '&page=', str(page),
        '&dir=', encoder.encode_uri_component(path),
        '&t=', util.latency(),
        '&shareid=', share_id,
        '&order=time&desc=1',
        '&uk=', uk,
        '&_=', util.timestamp(),
        '&bdstoken=', tokens['bdstoken'],
        ])
    req = net.urlopen(url, headers={
        'Cookie': cookie.header_output(),
        'Referer': const.SHARE_REFERER,
        })
    if req:
        content = req.data
        return json.loads(content.decode())
    else:
        return None

def get_share_page(url):
    '''获取共享页面的文件信息'''
    req = net.urlopen(url)
    if req:
        content = req.data.decode()
        match = re.findall('applicationConfig,(.+)\]\);', content)
        share_files = {}
        if not match:
            match = re.findall('viewShareData=(.+");FileUtils.spublic', content)
            if not match:
                return None
            list_ = json.loads(json.loads(match[0]))
        else:
            list_ = json.loads(json.loads(match[0]))
        if isinstance(list_, dict):
            share_files['list'] = [list_, ]
        else:
            share_files['list'] = list_
        id_match = re.findall('FileUtils\.share_id="(\d+)"', content)
        uk_match = re.findall('/share/home\?uk=(\d+)" target=', content)
        sign_match = re.findall('FileUtils\.share_sign="([^"]+)"', content)
        if id_match and uk_match and sign_match:
            share_files['share_id'] = id_match[0]
            share_files['uk'] = uk_match[0]
            share_files['sign'] = sign_match[0]
            return share_files
    return None

def enable_share(cookie, tokens, fid_list):
    '''建立新的分享.

    fid_list - 是一个list, 里面的每一条都是一个文件的fs_id
    一次可以分享同一个目录下的多个文件/目录, 它们会会打包为一个分享链接,
    这个分享链接还有一个对应的shareid. 我们可以用uk与shareid来在百度网盘里
    面定位到这个分享内容.
    @return - 会返回分享链接和shareid.
    '''
    url = ''.join([
        const.PAN_URL,
        'share/set?channel=chunlei&clienttype=0&web=1',
        '&bdstoken=', tokens['bdstoken'],
        ])
    data = encoder.encode_uri('fid_list=' + json.dumps(fid_list) + 
            '&schannel=0&channel_list=[]')
    req = net.urlopen(url, headers={
        'Cookie': cookie.header_output(),
        'Content-type': const.CONTENT_FORM_UTF8,
        }, data=data.encode())
    if req:
        content = req.data
        return json.loads(content.decode())
    else:
        return None

def disable_share(cookie, tokens, shareid_list):
    '''取消分享.

    shareid_list 是一个list, 每一项都是一个shareid
    '''
    url = ''.join([
        const.PAN_URL,
        'share/cancel?channel=chunlei&clienttype=0&web=1',
        '&bdstoken=', tokens['bdstoken'],
        ])
    data = 'shareid_list=' + encoder.encode_uri(json.dumps(shareid_list))
    req = net.urlopen(url, headers={
        'Cookie': cookie.header_output(),
        'Content-type': const.CONTENT_FORM_UTF8,
        }, data=data.encode())
    if req:
        content = req.data
        return json.loads(content.decode())
    else:
        return None


def list_inbox(cookie, tokens, start=0, limit=20):
    '''获取收件箱里的文件信息.'''
    url = ''.join([
        const.PAN_URL,
        'inbox/object/list?type=1',
        '&start=', str(start),
        '&limit=', str(limit),
        '&_=', util.timestamp(),
        '&channel=chunlei&clienttype=0&web=1',
        '&bdstoken=', tokens['bdstoken'],
        ])
    req = net.urlopen(url, headers={'Cookie': cookie.header_output()})
    if req:
        content = req.data
        return json.loads(content.decode())
    else:
        return None

def list_trash(cookie, tokens, path='/', page=1, num=100):
    '''获取回收站的信息.

    path - 目录的绝对路径, 默认是根目录
    page - 页码, 默认是第一页
    num - 每页有多少个文件, 默认是100个.
    回收站里面的文件会被保存10天, 10天后会自动被清空.
    回收站里面的文件不占用用户的存储空间.
    '''
    url = ''.join([
        const.PAN_API_URL,
        'recycle/list?channel=chunlei&clienttype=0&web=1',
        '&num=', str(num),
        '&t=', util.timestamp(),
        '&dir=', encoder.encode_uri_component(path),
        '&t=', util.latency(),
        '&order=time&desc=1',
        '&_=', util.timestamp(),
        '&bdstoken=', tokens['bdstoken'],
        ])
    req = net.urlopen(url, headers={'Cookie': cookie.header_output()})
    if req:
        content = req.data
        return json.loads(content.decode())
    else:
        return None

def restore_trash(cookie, tokens, fidlist):
    '''从回收站中还原文件/目录.

    fildlist - 要还原的文件/目录列表, fs_id.
    '''
    url = ''.join([
        const.PAN_API_URL,
        'recycle/restore?channel=chunlei&clienttype=0&web=1',
        '&t=', util.timestamp(),
        '&bdstoken=', tokens['bdstoken'],
        ])
    data = 'fidlist=' + encoder.encode_uri_component(json.dumps(fidlist))
    req = net.urlopen(url, headers={
        'Cookie': cookie.header_output(),
        'Content-type': const.CONTENT_FORM_UTF8,
        }, data=data.encode())
    if req:
        content = req.data
        return json.loads(content.decode())
    else:
        return None

def delete_trash(cookie, tokens, fidlist):
    '''批量将文件从回收站中删除, 这一步不可还原!'

    fidlist - 待删除的目录/文件的fs_id 列表.

    如果有一个文件的fs_id在回收站中不存在, 就会报错, 并返回.
    '''
    url = ''.join([
        const.PAN_API_URL,
        'recycle/delete?channel=chunlei&clienttype=0&web=1',
        '&bdstoken=', tokens['bdstoken'],
        ])
    data = 'fidlist=' + encoder.encode_uri_component(json.dumps(fidlist))
    req = net.urlopen(url, headers={
        'Cookie': cookie.header_output(),
        'Content-type': const.CONTENT_FORM_UTF8,
        }, data=data.encode())
    if req:
        content = req.data
        return json.loads(content.decode())
    else:
        return None

def clear_trash(cookie, tokens):
    '''清空回收站, 将里面的所有文件都删除.'''
    url = ''.join([
        const.PAN_API_URL,
        'recycle/clear?channel=chunlei&clienttype=0&web=1',
        '&t=', util.timestamp(),
        '&bdstoken=', tokens['bdstoken'],
        ])
    # 使用POST方式发送命令, 但data为空.
    req = net.urlopen(url, headers={
        'Cookie': cookie.header_output(),
        }, data=''.encode())
    if req:
        content = req.data
        return json.loads(content.decode())
    else:
        return None

def list_dir_all(cookie, tokens, path):
    '''得到一个目录中所有文件的信息, 并返回它的文件列表'''
    pcs_files = []
    page = 1
    while True:
        content = list_dir(cookie, tokens, path, page)
        if not content:
            return (path, None)
        if not content['list']:
            return (path, pcs_files)
        pcs_files.extend(content['list'])
        page = page + 1

def list_dir(cookie, tokens, path, page=1, num=100):
    '''得到一个目录中的所有文件的信息(最多100条记录).'''
    timestamp = util.timestamp()
    url = ''.join([
        const.PAN_API_URL,
        'list?channel=chunlei&clienttype=0&web=1',
        '&num=', str(num),
        '&t=', timestamp,
        '&page=', str(page),
        '&dir=', encoder.encode_uri_component(path),
        '&t=', util.latency(),
        '&order=time&desc=1',
        '&_=', timestamp,
        '&bdstoken=', tokens['bdstoken'],
        ])
    req = net.urlopen(url, headers={
        'Content-type': const.CONTENT_FORM_UTF8,
        'Cookie': cookie.sub_output('BAIDUID', 'BDUSS', 'PANWEB', 'cflag'),
        })
    if req:
        content = req.data
        return json.loads(content.decode())
    else:
        return None

def mkdir(cookie, tokens, path):
    '''创建一个目录.

    path 目录名, 绝对路径.
    @return 返回一个dict, 里面包含了fs_id, ctime等信息.
    '''
    url = ''.join([
        const.PAN_API_URL, 
        'create?a=commit&channel=chunlei&clienttype=0&web=1',
        '&bdstoken=', tokens['bdstoken'],
        ])
    data = ''.join([
        'path=', encoder.encode_uri_component(path),
        '&isdir=1&size=&block_list=%5B%5D&method=post',
        ])
    req = net.urlopen(url, headers={
        'Cookie': cookie.header_output(),
        'Content-type': const.CONTENT_FORM_UTF8,
        }, data=data.encode())
    if req:
        content = req.data
        return json.loads(content.decode())
    else:
        return None

def delete_files(cookie, tokens, filelist):
    '''批量删除文件/目录.

    filelist - 待删除的文件/目录列表, 绝对路径
    '''
    url = ''.join([
        const.PAN_API_URL,
        'filemanager?channel=chunlei&clienttype=0&web=1&opera=delete',
        '&bdstoken=', tokens['bdstoken'],
        ])
    data = 'filelist=' + encoder.encode_uri_component(json.dumps(filelist))
    req = net.urlopen(url, headers={
        'Content-type': const.CONTENT_FORM_UTF8,
        'Cookie': cookie.header_output(),
        }, data=data.encode())
    if req:
        content = req.data
        return json.loads(content.decode())
    else:
        return None

def rename(cookie, tokens, filelist):
    '''批量重命名目录/文件.

    只能修改文件名, 不能修改它所在的目录.

    filelist 是一个list, 里面的每一项都是一个dict, 每个dict包含两部分:
    path - 文件的绝对路径, 包含文件名.
    newname - 新名称.
    '''
    url = ''.join([
        const.PAN_API_URL,
        'filemanager?channel=chunlei&clienttype=0&web=1&opera=rename',
        '&bdstoken=', tokens['bdstoken'],
        ])
    data = 'filelist=' + encoder.encode_uri_component(json.dumps(filelist))
    req = net.urlopen(url, headers={
        'Content-type': const.CONTENT_FORM_UTF8,
        'Cookie': cookie.header_output(),
        }, data=data.encode())
    if req:
        content = req.data
        return json.loads(content.decode())
    else:
        return None

def move(cookie, tokens, filelist):
    '''移动文件/目录到新的位置.

    filelist 是一个list, 里面包含至少一个dict, 每个dict都有以下几项:
    path - 文件的当前的绝对路径, 包括文件名.
    dest - 文件的目标绝对路径, 不包括文件名.
    newname - 文件的新名称; 可以与保持原来的文件名一致, 也可以给一个新名称.
    '''
    url = ''.join([
        const.PAN_API_URL,
        'filemanager?channel=chunlei&clienttype=0&web=1&opera=move',
        '&bdstoken=', tokens['bdstoken'],
        ])
    data = 'filelist=' + encoder.encode_uri_component(json.dumps(filelist))
    req = net.urlopen(url, headers={
        'Cookie': cookie.header_output(),
        'Content-type': const.CONTENT_FORM_UTF8,
        }, data=data.encode())
    if req:
        content = req.data
        return json.loads(content.decode())
    else:
        return None

def copy(cookie, tokens, filelist):
    '''复制文件/目录到新位置.

    filelist 是一个list, 里面的每一项都是一个dict, 每个dict都有这几项:
    path - 文件/目录的当前的绝对路径, 包含文件名
    dest - 要复制到的目的路径, 不包含文件名
    newname - 文件/目录的新名称; 可以保持与当前名称一致.
    '''
    url = ''.join([
        const.PAN_API_URL,
        'filemanager?channel=chunlei&clienttype=0&web=1&opera=copy',
        '&bdstoken=', tokens['bdstoken'],
        ])
    data = 'filelist=' + encoder.encode_uri_component(json.dumps(filelist))
    req = net.urlopen(url, headers={
        'Cookie': cookie.header_output(),
        'Content-type': const.CONTENT_FORM_UTF8,
        }, data=data.encode())
    if req:
        content = req.data
        return json.loads(content.decode())
    else:
        return None


def get_category(cookie, tokens, category, page=1):
    '''获取一个分类中的所有文件信息, 比如音乐/图片

    目前的有分类有:
      视频 - 1
      音乐 - 2
      图片 - 3
      文档 - 4
      应用 - 5
      其它 - 6
      BT种子 - 7
    '''
    timestamp = util.timestamp()
    url = ''.join([
        const.PAN_API_URL,
        'categorylist?channel=chunlei&clienttype=0&web=1',
        '&category=', str(category),
        '&pri=-1&num=100',
        '&t=', timestamp,
        '&page=', str(page),
        '&order=time&desc=1',
        '&_=', timestamp,
        '&bdstoken=', cookie.get('STOKEN').value,
        ])
    req = net.urlopen(url, headers={'Cookie': cookie.header_output()})
    if req:
        content = req.data
        return json.loads(content.decode())
    else:
        return None

def get_download_link(cookie, tokens, path):
    '''在下载之前, 要先获取最终的下载链接.

    path - 一个文件的绝对路径.

    @return red_url, red_url 是重定向后的URL, 如果获取失败,
            就返回原来的dlink;
    '''
    metas = get_metas(cookie, tokens, path)
    if (not metas or metas.get('errno', 1) != 0 or
            'info' not in metas or len(metas['info']) != 1):
        return None
    dlink = metas['info'][0]['dlink']
    url = ''.join([
        dlink,
        '&cflg=', cookie.get('cflag').value
        ])
    req = net.urlopen_without_redirect(url, headers={
            'Cookie': cookie.sub_output('BAIDUID', 'BDUSS', 'cflag'),
            'Accept': const.ACCEPT_HTML,
            })
    if not req:
        return url
    else:
        return req.getheader('Location', url)

def stream_download(cookie, tokens, path):
    '''下载流媒体文件.

    path - 流文件的绝对路径.
    '''
    url = ''.join([
        const.PCS_URL_D,
        'file?method=download',
        '&path=', encoder.encode_uri_component(path),
        '&app_id=250528',
        ])
    req = net.urlopen_without_redirect(
            url, headers={'Cookie': cookie.header_output()})
    if req:
        return req
    else:
        return None

def get_streaming_playlist(cookie, path, video_type='M3U8_AUTO_480'):
    '''获取流媒体(通常是视频)的播放列表.

    默认得到的是m3u8格式的播放列表, 因为它最通用.
    path       - 视频的绝对路径
    video_type - 视频格式, 可以根据网速及片源, 选择不同的格式.
    '''
    url = ''.join([
        const.PCS_URL,
        'file?method=streaming',
        '&path=', encoder.encode_uri_component(path),
        '&type=', video_type,
        '&app_id=250528',
        ])
    req = net.urlopen(url, headers={'Cookie': cookie.header_output()})
    if req:
        return req.data
    else:
        return None


def upload_option(cookie, path):
    '''上传之前的检查.

    path   - 准备在服务器上放到的绝对路径.
    '''
    dir_name, file_name = os.path.split(path)
    url = ''.join([
        const.PCS_URL_C,
        'file?method=upload&app_id=250528&ondup=newcopy',
        '&dir=', encoder.encode_uri_component(dir_name),
        '&filename=', encoder.encode_uri_component(file_name),
        '&', cookie.sub_output('BDUSS'),
        ])
    resp = net.urloption(url, headers={'Accept': const.ACCEPT_HTML})
    if resp:
        return resp.getheaders()
    else:
        return None

def upload(cookie, source_path, path, ondup='overwrite'):
    '''上传一个文件.

    这个是使用的网页中的上传接口.
    ondup - 如果文件已在服务器上存在, 该如何操作. 有两个选项:
            overwrite, 直接将其重写.
            newcopy, 保留原先的文件, 并在新上传的文件名尾部加上当前时间戳.
    '''
    dir_name, file_name = os.path.split(path)
    url = ''.join([
        const.PCS_URL_C,
        'file?method=upload&app_id=250528',
        '&ondup=', ondup,
        '&dir=', encoder.encode_uri_component(dir_name),
        '&filename=', encoder.encode_uri_component(file_name),
        '&', cookie.sub_output('BDUSS'),
        ])
    with open(source_path, 'rb') as fh:
        data = fh.read()
    fields = []
    files = [
        ('file', file_name, data),
        ]
    headers = {
        'Accept': const.ACCEPT_HTML,
        'Origin': const.PAN_URL,
        }
    req = net.post_multipart(url, headers, fields, files)
    if req:
        return json.loads(req.data.decode())
    else:
        return None

def rapid_upload(cookie, tokens, source_path, path):
    '''快速上传'''
    content_length = os.path.getsize(source_path)
    assert content_length > RAPIDUPLOAD_THRESHOLD, 'file size is not satisfied!'
    dir_name, file_name = os.path.split(path)
    content_md5 = hasher.md5(source_path)
    slice_md5 = hasher.md5(source_path, 0, RAPIDUPLOAD_THRESHOLD)
    url = ''.join([
        const.PCS_URL_C,
        'file?method=rapidupload&app_id=250528',
        '&ondup=newcopy',
        '&dir=', encoder.encode_uri_component(dir_name),
        '&filename=', encoder.encode_uri_component(file_name),
        '&content-length=', str(content_length),
        '&content-md5=', content_md5,
        '&slice-md5=', slice_md5,
        '&path=', encoder.encode_uri_component(path),
        '&', cookie.sub_output('BDUSS'),
        '&bdstoken=', tokens['bdstoken'],
        ])
    req = net.urlopen(url, headers={
        'Cookie': cookie.header_output(),
        })
    if req:
        return json.loads(req.data.decode())
    else:
        return None

def slice_upload(cookie, data):
    '''分片上传一个大文件
    
    分片上传完成后, 会返回这个分片的MD5, 用于最终的文件合并.
    如果上传失败, 需要重新上传.
    不需要指定上传路径, 上传后的数据会被存储在服务器的临时目录里.
    data - 这个文件分片的数据.
    '''
    url = ''.join([
        const.PCS_URL_C,
        'file?method=upload&type=tmpfile&app_id=250528',
        '&', cookie.sub_output('BDUSS'),
        ])
    fields = []
    files = [
        ('file', ' ', data),
        ]
    headers = {
        'Accept': const.ACCEPT_HTML,
        'Origin': const.PAN_URL,
        }
    req = net.post_multipart(url, headers, fields, files)
    if req:
        return json.loads(req.data.decode())
    else:
        return None

def create_superfile(cookie, path, block_list):
    '''合并slice_upload()中产生的临时文件

    path       - 文件在服务器上的绝对路径
    block_list - 这些文件分片的MD5列表
    返回完整的文件pcs信息.
    '''
    url = ''.join([
        const.PCS_URL_C,
        'file?method=createsuperfile&app_id=250528',
        '&path=', encoder.encode_uri_component(path),
        '&', cookie.sub_output('BDUSS'),
        ])
    param = {'block_list': block_list}
    data = 'param=' + json.dumps(param)
    req = net.urlopen(url, headers={
        'Cookie': cookie.header_output(),
        }, data=data.encode())
    if req:
        return json.loads(req.data.decode())
    else:
        return None


def get_metas(cookie, tokens, filelist, dlink=True):
    '''获取多个文件的metadata.

    filelist - 一个list, 里面是每个文件的绝对路径.
               也可以是一个字符串, 只包含一个文件的绝对路径.
    dlink    - 是否包含下载链接, 默认为True, 包含.

    @return 包含了文件的下载链接dlink, 通过它可以得到最终的下载链接.
    '''
    if isinstance(filelist, str):
        filelist = [filelist, ]
    url = ''.join([
        const.PAN_API_URL,
        'filemetas?channel=chunlei&clienttype=0&web=1',
        '&bdstoken=', tokens['bdstoken'],
        ])
    if dlink:
        data = ('dlink=1&target=' +
                encoder.encode_uri_component(json.dumps(filelist)))
    else:
        data = ('dlink=0&target=' +
                encoder.encode_uri_component(json.dumps(filelist)))
    req = net.urlopen(url, headers={
        'Cookie': cookie.sub_output('BDUSS'),
        'Content-type': const.CONTENT_FORM,
        }, data=data.encode())
    if req:
        content = req.data
        return json.loads(content.decode())
    else:
        return None

def search(cookie, tokens, key, path='/'):
    '''搜索全部文件, 根据文件名.

    key - 搜索的关键词
    path - 如果指定目录名的话, 只搜索本目录及其子目录里的文件名.
    '''
    url = ''.join([
        const.PAN_API_URL,
        'search?channel=chunlei&clienttype=0&web=1',
        '&dir=', path,
        '&key=', key,
        '&recursion',
        '&timeStamp=', util.latency(),
        '&bdstoken=', tokens['bdstoken'],
        ])
    req = net.urlopen(url, headers={'Cookie': cookie.header_output()})
    if req:
        content = req.data
        return json.loads(content.decode())
    else:
        return None

def cloud_add_link_task(cookie, tokens, source_url, save_path,
                        vcode='', vcode_input=''):
    '''新建离线下载任务.
    
    source_url - 可以是http/https/ftp等一般的链接
                 可以是eMule这样的链接
    path       - 要保存到哪个目录, 比如 /Music/, 以/开头, 以/结尾的绝对路径.
    '''
    url = ''.join([
        const.PAN_URL,
        'rest/2.0/services/cloud_dl?channel=chunlei&clienttype=0&web=1',
        '&bdstoken=', tokens['bdstoken'],
        ])
    type_ = ''
    if source_url.startswith('ed2k'):
        type_ = '&type=3'
    if not save_path.endswith('/'):
        save_path = save_path + '/'
    data = [
        'method=add_task&app_id=250528',
        '&source_url=', encoder.encode_uri_component(source_url),
        '&save_path=', encoder.encode_uri_component(save_path),
        '&type=', type_,
        ]
    if vcode:
        data.append('&input=')
        data.append(vcode_input)
        data.append('&vcode=')
        data.append(vcode)
    data = ''.join(data)
    req = net.urlopen(url, headers={
        'Cookie': cookie.header_output(),
        }, data=data.encode())
    if req:
        content = req.data
        return json.loads(content.decode())
    else:
        return None

def cloud_add_bt_task(cookie, tokens, source_url, save_path, selected_idx,
                      file_sha1='', vcode='', vcode_input=''):
    '''新建一个BT类的离线下载任务, 包括magent磁链.

    source_path  - BT种子所在的绝对路径
    save_path    - 下载的文件要存放到的目录
    selected_idx - BT种子中, 包含若干个文件, 这里, 来指定要下载哪些文件,
                   从1开始计数.
    file_sha1    - BT种子的sha1值, 如果是magent的话, 这个sha1值可以为空
    vcode        - 验证码的vcode
    vcode_input  - 用户输入的四位验证码
    '''
    url = ''.join([
        const.PAN_URL,
        'rest/2.0/services/cloud_dl?channel=chunlei&clienttype=0&web=1',
        '&bdstoken=', tokens['bdstoken'],
        ])
    type_ = '2'
    url_type = 'source_path'
    if source_url.startswith('magnet:'):
        type_ = '4'
        url_type = 'source_url'
    if not save_path.endswith('/'):
        save_path = save_path + '/'
    data = [
        'method=add_task&app_id=250528',
        '&file_sha1=', file_sha1,
        '&save_path=', encoder.encode_uri_component(save_path),
        '&selected_idx=', ','.join(str(i) for i in selected_idx),
        '&task_from=1',
        '&t=', util.timestamp(),
        '&', url_type, '=', encoder.encode_uri_component(source_url),
        '&type=', type_
        ]
    if vcode:
        data.append('&input=')
        data.append(vcode_input)
        data.append('&vcode=')
        data.append(vcode)
    data = ''.join(data)
    req = net.urlopen(url, headers={
        'Cookie': cookie.header_output(),
        }, data=data.encode())
    if req:
        content = req.data
        return json.loads(content.decode())
    else:
        return None

def cloud_query_sinfo(cookie, tokens, source_path):
    '''获取网盘中种子的信息, 比如里面的文件名, 文件大小等.

    source_path - BT种子的绝对路径.
    '''
    url = ''.join([
        const.PAN_URL,
        'rest/2.0/services/cloud_dl?channel=chunlei&clienttype=0&web=1',
        '&method=query_sinfo&app_id=250528',
        '&bdstoken=', tokens['bdstoken'],
        '&source_path=', encoder.encode_uri_component(source_path),
        '&type=2',
        '&t=', util.timestamp(),
        ])
    req = net.urlopen(url, headers={'Cookie': cookie.header_output()})
    if req:
        content = req.data
        return json.loads(content.decode())
    else:
        return None

def cloud_query_magnetinfo(cookie, tokens, source_url, save_path):
    '''获取磁链的信息.
    
    在新建磁链任务时, 要先获取这个磁链的信息, 比如里面包含哪些文件, 文件的名
    称与大小等.

    source_url - 磁链的url, 以magent:开头.
    save_path  - 保存到哪个目录
    '''
    url = ''.join([
        const.PAN_URL,
        'rest/2.0/services/cloud_dl?channel=chunlei&clienttype=0&web=1',
        '&bdstoken=', tokens['bdstoken'],
        ])
    data = ''.join([
        'method=query_magnetinfo&app_id=250528',
        '&source_url=', encoder.encode_uri_component(source_url),
        '&save_path=', encoder.encode_uri_component(save_path),
        '&type=4',
        ])
    req = net.urlopen(url, headers={
        'Cookie': cookie.header_output(),
        }, data=data.encode())
    if req:
        content = req.data
        return json.loads(content.decode())
    else:
        return None

def cloud_list_task(cookie, tokens, start=0):
    '''获取当前离线下载的任务信息
    
    start - 从哪个任务开始, 从0开始计数, 会获取这50条任务信息
    '''
    url = ''.join([
        const.PAN_URL,
        'rest/2.0/services/cloud_dl?channel=chunlei&clienttype=0&web=1',
        '&bdstoken=', tokens['bdstoken'],
        '&need_task_info=1&status=255',
        '&start=', str(start),
        '&limit=50&method=list_task&app_id=250528',
        '&t=', util.timestamp(),
        ])
    req = net.urlopen(url, headers={'Cookie': cookie.header_output()})
    if req:
        content = req.data
        return json.loads(content.decode())
    else:
        return None

def cloud_query_task(cookie, tokens, task_ids):
    '''查询离线下载任务的信息, 比如进度, 是否完成下载等.

    最好先用cloud_list_task() 来获取当前所有的任务, 然后调用这个函数来获取
    某项任务的详细信息.

    task_ids - 一个list, 里面至少要有一个task_id, task_id 是一个字符串
    '''
    url = ''.join([
        const.PAN_URL,
        'rest/2.0/services/cloud_dl?method=query_task&app_id=250528',
        '&bdstoken=', tokens['bdstoken'],
        '&task_ids=', ','.join(task_ids),
        '&t=', util.timestamp(),
        '&channel=chunlei&clienttype=0&web=1',
        ])
    req = net.urlopen(url, headers={'Cookie': cookie.header_output()})
    if req:
        content = req.data
        return json.loads(content.decode())
    else:
        return None

def cloud_cancel_task(cookie, tokens, task_id):
    '''取消离线下载任务.
    
    task_id - 之前建立离线下载任务时的task id, 也可以从cloud_list_task()里
              获取.
    '''
    url = ''.join([
        const.PAN_URL,
        'rest/2.0/services/cloud_dl',
        '?bdstoken=', tokens['bdstoken'],
        '&task_id=', str(task_id),
        '&method=cancel_task&app_id=250528',
        '&t=', util.timestamp(),
        '&channel=chunlei&clienttype=0&web=1',
        ])
    req = net.urlopen(url, headers={'Cookie': cookie.header_output()})
    if req:
        content = req.data
        return json.loads(content.decode())
    else:
        return None

def cloud_delete_task(cookie, tokens, task_id):
    '''删除一个离线下载任务, 不管这个任务是否已完成下载.

    同时还会把它从下载列表中删除.
    '''
    url = ''.join([
        const.PAN_URL,
        'rest/2.0/services/cloud_dl',
        '?bdstoken=', tokens['bdstoken'],
        '&task_id=', str(task_id),
        '&method=delete_task&app_id=250528',
        '&t=', util.timestamp(),
        '&channel=chunlei&clienttype=0&web=1',
        ])
    req = net.urlopen(url, headers={'Cookie': cookie.header_output()})
    if req:
        content = req.data
        return json.loads(content.decode())
    else:
        return None

def cloud_clear_task(cookie, tokens):
    '''清空离线下载的历史(已经完成或者取消的).'''
    url = ''.join([
        const.PAN_URL,
        'rest/2.0/services/cloud_dl?method=clear_task&app_id=250528',
        '&channel=chunlei&clienttype=0&web=1',
        '&t=', util.timestamp(),
        '&bdstoken=', tokens['bdstoken'],
        ])
    req = net.urlopen(url, headers={'Cookie': cookie.header_output()})
    if req:
        content = req.data
        return json.loads(content.decode())
    else:
        return None

########NEW FILE########
__FILENAME__ = PreferencesDialog

# Copyright (C) 2014 LiuLang <gsushzhsosgsu@gmail.com>
# Use of this source code is governed by GPLv3 license that can be found
# in http://www.gnu.org/licenses/gpl-3.0.html

from gi.repository import GLib
from gi.repository import Gtk

from bcloud import Config
_ = Config._


class PreferencesDialog(Gtk.Dialog):

    def __init__(self, app):
        self.app = app
        super().__init__(
                _('Preferences'), app.window, Gtk.DialogFlags.MODAL,
                (Gtk.STOCK_CLOSE, Gtk.ResponseType.OK))
        self.set_default_response(Gtk.ResponseType.OK)

        self.set_default_size(480, 360)
        self.set_border_width(10)

        box = self.get_content_area()

        notebook = Gtk.Notebook()
        box.pack_start(notebook, True, True, 0)

        # General Tab
        general_grid = Gtk.Grid()
        general_grid.props.halign = Gtk.Align.CENTER
        general_grid.props.column_spacing = 12
        general_grid.props.row_spacing = 5
        general_grid.props.margin_top = 5
        notebook.append_page(general_grid, Gtk.Label.new(_('General')))

        dir_label = Gtk.Label.new(_('Save To:'))
        dir_label.props.xalign = 1
        general_grid.attach(dir_label, 0, 0, 1, 1)
        dir_button = Gtk.FileChooserButton()
        dir_button.set_action(Gtk.FileChooserAction.SELECT_FOLDER)
        dir_button.set_current_folder(app.profile['save-dir'])
        dir_button.connect('file-set', self.on_dir_update)
        general_grid.attach(dir_button, 1, 0, 1, 1)

        concurr_label = Gtk.Label.new(_('Concurrent downloads:'))
        concurr_label.props.xalign = 1
        general_grid.attach(concurr_label, 0, 1, 1, 1)
        concurr_spin = Gtk.SpinButton.new_with_range(1, 5, 1)
        concurr_spin.set_value(self.app.profile['concurr-tasks'])
        concurr_spin.props.halign = Gtk.Align.START
        concurr_spin.connect('value-changed', self.on_concurr_value_changed)
        general_grid.attach(concurr_spin, 1, 1, 1, 1)

        upload_hidden_label = Gtk.Label.new(_('Upload hidden files:'))
        upload_hidden_label.props.xalign = 1
        general_grid.attach(upload_hidden_label, 0, 2, 1, 1)
        upload_hidden_switch = Gtk.Switch()
        upload_hidden_switch.props.halign = Gtk.Align.START
        upload_hidden_switch.set_tooltip_text(
                _('Also upload hidden files and folders'))
        upload_hidden_switch.set_active(
                self.app.profile['upload-hidden-files'])
        upload_hidden_switch.connect(
                'notify::active', self.on_upload_hidden_switch_activate)
        general_grid.attach(upload_hidden_switch, 1, 2, 1, 1)

        notify_label = Gtk.Label.new(_('Use notification:'))
        notify_label.props.xalign = 1
        general_grid.attach(notify_label, 0, 3, 1, 1)
        notify_switch = Gtk.Switch()
        notify_switch.props.halign = Gtk.Align.START
        notify_switch.set_active(self.app.profile['use-notify'])
        notify_switch.connect(
                'notify::active', self.on_notify_switch_activate)
        general_grid.attach(notify_switch, 1, 3, 1, 1)

        dark_theme_label = Gtk.Label.new(_('Use dark theme:'))
        dark_theme_label.props.xalign = 1
        general_grid.attach(dark_theme_label, 0, 4, 1, 1)
        dark_theme_switch = Gtk.Switch()
        dark_theme_switch.set_active(self.app.profile['use-dark-theme'])
        dark_theme_switch.connect(
                'notify::active', self.on_dark_theme_switch_toggled)
        dark_theme_switch.props.halign = Gtk.Align.START
        general_grid.attach(dark_theme_switch, 1, 4, 1, 1)

        status_label = Gtk.Label.new(_('Minimize to system tray:'))
        status_label.props.xalign = 1
        general_grid.attach(status_label, 0, 5, 1, 1)
        status_switch = Gtk.Switch()
        status_switch.set_active(self.app.profile['use-status-icon'])
        status_switch.connect(
                'notify::active', self.on_status_switch_activate)
        status_switch.props.halign = Gtk.Align.START
        general_grid.attach(status_switch, 1, 5, 1, 1)

        stream_label = Gtk.Label.new(_('Use streaming mode:'))
        stream_label.props.xalign = 1
        general_grid.attach(stream_label, 0, 6, 1, 1)
        stream_switch = Gtk.Switch()
        stream_switch.set_active(self.app.profile['use-streaming'])
        stream_switch.connect(
                'notify::active', self.on_stream_switch_activate)
        stream_switch.props.halign = Gtk.Align.START
        stream_switch.set_tooltip_text(_('When opening a video file, try to download a m3u8 playlist, instread of getting its file source link'))
        general_grid.attach(stream_switch, 1, 6, 1, 1)

        box.show_all()

    def on_dir_update(self, file_button):
        dir_name = file_button.get_filename()
        if dir_name:
            self.app.profile['save-dir'] = dir_name

    def on_concurr_value_changed(self, concurr_spin):
        self.app.profile['concurr-tasks'] = concurr_spin.get_value()

    def on_upload_hidden_switch_activate(self, switch, event):
        self.app.profile['upload-hidden-files'] = switch.get_active()

    def on_notify_switch_activate(self, switch, event):
        self.app.profile['use-notify'] = switch.get_active()

    def on_dark_theme_switch_toggled(self, switch, event):
        self.app.profile['use-dark-theme'] = switch.get_active()

    def on_status_switch_activate(self, switch, event):
        self.app.profile['use-status-icon'] = switch.get_active()

    def on_stream_switch_activate(self, switch, event):
        self.app.profile['use-streaming'] = switch.get_active()

########NEW FILE########
__FILENAME__ = PropertiesDialog

# Copyright (C) 2014 LiuLang <gsushzhsosgsu@gmail.com>
# Use of this source code is governed by GPLv3 license that can be found
# in http://www.gnu.org/licenses/gpl-3.0.html

import os
import time

from gi.repository import Gtk

from bcloud import Config
_ = Config._
from bcloud import util
from bcloud.Widgets import LeftLabel
from bcloud.Widgets import SelectableLeftLabel

(PIXBUF_COL, NAME_COL, PATH_COL, TOOLTIP_COL, SIZE_COL, HUMAN_SIZE_COL,
    ISDIR_COL, MTIME_COL, HUMAN_MTIME_COL, TYPE_COL, PCS_FILE_COL
    ) = list(range(11))


class PropertiesDialog(Gtk.Dialog):

    def __init__(self, parent, app, pcs_file):
        file_path, file_name = os.path.split(pcs_file['path'])
        super().__init__(
                file_name + _(' Properties'),
                app.window, Gtk.DialogFlags.MODAL,
                (Gtk.STOCK_CLOSE, Gtk.ResponseType.CLOSE))
        self.set_default_response(Gtk.ResponseType.CLOSE)

        self.set_border_width(15)
        #self.set_default_size(640, 480)

        box = self.get_content_area()

        grid = Gtk.Grid()
        grid.props.row_spacing = 8
        grid.props.margin_left = 15
        grid.props.column_spacing = 15
        box.pack_start(grid, True, True, 10)

        name_label = LeftLabel(_('Name:'))
        grid.attach(name_label, 0, 0, 1, 1)
        name_label2 = SelectableLeftLabel(file_name)
        grid.attach(name_label2, 1, 0, 1, 1)

        location_label = LeftLabel(_('Location:'))
        grid.attach(location_label, 0, 2, 1, 1)
        location_label2 = SelectableLeftLabel(file_path)
        grid.attach(location_label2, 1, 2, 1, 1)

        if pcs_file['isdir']:
            pass
        else:
            size_label = LeftLabel(_('Size'))
            grid.attach(size_label, 0, 1, 1, 1)
            size_human, size_comma = util.get_human_size(pcs_file['size'])
            if size_human:
                size_text = ''.join([
                    str(size_human), ' (', size_comma,  _(' bytes'), ')'])
            else:
                size_text = size_comma + _(' bytes')
            size_label2 = SelectableLeftLabel(size_text)
            grid.attach(size_label2, 1, 1, 1, 1)
            md5_label = LeftLabel('MD5:')
            grid.attach(md5_label, 0, 3, 1, 1)
            md5_label2 = SelectableLeftLabel(pcs_file['md5'])
            grid.attach(md5_label2, 1, 3, 1, 1)

        id_label = LeftLabel('FS ID:')
        grid.attach(id_label, 0, 4, 1, 1)
        id_label2 = SelectableLeftLabel(pcs_file['fs_id'])
        grid.attach(id_label2, 1, 4, 1, 1)

        ctime_label = LeftLabel(_('Created:'))
        grid.attach(ctime_label, 0, 5, 1, 1)
        ctime_label2 = SelectableLeftLabel(
                time.ctime(pcs_file['server_ctime']))
        grid.attach(ctime_label2, 1, 5, 1, 1)

        mtime_label = LeftLabel(_('Modified:'))
        grid.attach(mtime_label, 0, 6, 1, 1)
        mtime_label2 = SelectableLeftLabel(
                time.ctime(pcs_file['server_mtime']))
        grid.attach(mtime_label2, 1, 6, 1, 1)

        box.show_all()


class FolderPropertyDialog(Gtk.Dialog):

    def __init__(self, icon_window, app, path):
        file_path, file_name = os.path.split(path)
        # modify file_name if path is '/'
        if not file_name:
            file_name = '/'
        super().__init__(
                file_name + _(' Properties'),
                app.window, Gtk.DialogFlags.MODAL,
                (Gtk.STOCK_CLOSE, Gtk.ResponseType.CLOSE))
        self.set_border_width(15)

        box = self.get_content_area()

        grid = Gtk.Grid()
        grid.props.row_spacing = 8
        grid.props.margin_left = 15
        grid.props.column_spacing = 15
        box.pack_start(grid, True, True, 10)

        name_label = LeftLabel(_('Name:'))
        grid.attach(name_label, 0, 0, 1, 1)
        name_label2 = SelectableLeftLabel(file_name)
        grid.attach(name_label2, 1, 0, 1, 1)

        location_label = LeftLabel(_('Location:'))
        grid.attach(location_label, 0, 1, 1, 1)
        location_label2 = SelectableLeftLabel(file_path)
        grid.attach(location_label2, 1, 1, 1, 1)

        file_count = 0
        folder_count = 0
        for row in icon_window.liststore:
            if row[ISDIR_COL]:
                folder_count = folder_count + 1
            else:
                file_count = file_count + 1
        contents = _('{0} folders, {1} files').format(folder_count, file_count)
        content_label = LeftLabel(_('Contents:'))
        grid.attach(content_label, 0, 2, 1, 1)
        content_label2 = SelectableLeftLabel(contents)
        grid.attach(content_label2, 1, 2, 1, 1)

        box.show_all()

########NEW FILE########
__FILENAME__ = RenameDialog

# Copyright (C) 2014 LiuLang <gsushzhsosgsu@gmail.com>
# Use of this source code is governed by GPLv3 license that can be found
# in http://www.gnu.org/licenses/gpl-3.0.html

import os

from gi.repository import Gtk

from bcloud import Config
_ = Config._
from bcloud import gutil
from bcloud import pcs

class RenameDialog(Gtk.Dialog):

    def __init__(self, app, path_list):
        super().__init__(
                _('Rename files'), app.window, Gtk.DialogFlags.MODAL,
                (Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
                 Gtk.STOCK_OK, Gtk.ResponseType.OK))
        self.set_border_width(10)
        self.set_default_size(640, 480)
        self.set_default_response(Gtk.ResponseType.OK)
        self.app = app

        box = self.get_content_area()

        scrolled_win = Gtk.ScrolledWindow()
        box.pack_start(scrolled_win, True, True, 0)

        grid = Gtk.Grid()
        scrolled_win.add(grid)
        grid.set_column_spacing(10)
        grid.set_row_spacing(5)
        grid.set_column_homogeneous(True)
        grid.props.margin_bottom = 20

        grid.attach(Gtk.Label.new(_('Old Name:')), 0, 0, 1, 1)
        grid.attach(Gtk.Label.new(_('New Name:')), 1, 0, 1, 1)

        self.rows = []
        i = 1
        for path in path_list:
            dir_name, name = os.path.split(path)
            old_entry = Gtk.Entry(text=name)
            old_entry.props.editable = False
            old_entry.props.can_focus = False
            old_entry.set_tooltip_text(path)
            grid.attach(old_entry, 0, i, 1, 1)
            
            new_entry = Gtk.Entry(text=name)
            new_entry.set_tooltip_text(path)
            grid.attach(new_entry, 1, i, 1, 1)
            i = i + 1
            self.rows.append((path, old_entry, new_entry))

        box.show_all()

    def do_response(self, response_id):
        '''进行批量重命名.

        这里, 会忽略掉那些名称没发生变化的文件.
        '''
        if response_id != Gtk.ResponseType.OK:
            return
        filelist = []
        for row in self.rows:
            if row[1].get_text() == row[2].get_text():
                continue
            filelist.append({
                'path': row[0],
                'newname': row[2].get_text(),
                })
        if len(filelist) == 0:
            return
        pcs.rename(self.app.cookie, self.app.tokens, filelist)
        gutil.async_call(
                pcs.rename, self.app.cookie, self.app.tokens, filelist,
                callback=self.app.reload_current_page)

########NEW FILE########
__FILENAME__ = RequestCookie

# Copyright (C) 2013-2014 LiuLang <gsushzhsosgsu@gmail.com>
# Use of this source code is governed by GPLv3 license that can be found
# in http://www.gnu.org/licenses/gpl-3.0.html

import http.cookies


class RequestCookie(http.cookies.SimpleCookie):
    '''为SimpleCookie()类加入了一个新的方法, 将里面的cookie值输出为http
    request header里面的字段.
    '''

    def __init__(self, rawdata=''):
        super().__init__(rawdata)

    def header_output(self):
        '''只输出cookie的key-value字串.
        
        比如: HISTORY=21341; PHPSESSION=3289012u39jsdijf28; token=233129
        '''
        result = []
        for key in self.keys():
            result.append(key + '=' + self.get(key).value)
        return '; '.join(result)

    def sub_output(self, *keys):
        '''获取一部分cookie, 并将它输出为字符串'''
        result = []
        for key in keys:
            if self.get(key):
                result.append(key + '=' + self.get(key).value)
        return '; '.join(result)

    def __str__(self):
        return self.header_output()

    def load_list(self, raw_items):
        '''读取多个以字符串形式存放的cookie.'''
        if not raw_items:
            return
        for item in raw_items:
            self.load(item)

########NEW FILE########
__FILENAME__ = SigninDialog

# Copyright (C) 2014 LiuLang <gsushzhsosgsu@gmail.com>
# Use of this source code is governed by GPLv3 license that can be found
# in http://www.gnu.org/licenses/gpl-3.0.html

import json
import os
import time

from gi.repository import GLib
from gi.repository import Gtk

from bcloud import auth
from bcloud import Config
_ = Config._
from bcloud import gutil
from bcloud.RequestCookie import RequestCookie

DELTA = 3 * 24 * 60 * 60   # 3 days

class SigninVcodeDialog(Gtk.Dialog):

    def __init__(self, parent, username, cookie, token, codeString, vcodetype):
        super().__init__(
            _('Verification..'), parent, Gtk.DialogFlags.MODAL)

        self.set_default_size(280, 120)
        self.set_border_width(10)
        self.username = username
        self.cookie = cookie
        self.token = token
        self.codeString = codeString
        self.vcodetype = vcodetype

        box = self.get_content_area()
        box.set_spacing(10)

        self.vcode_img = Gtk.Image()
        box.pack_start(self.vcode_img, False, False, 0)
        self.vcode_entry = Gtk.Entry()
        self.vcode_entry.connect('activate', self.check_entry)
        box.pack_start(self.vcode_entry, False, False, 0)

        button_box = Gtk.Box(spacing=10)
        box.pack_end(button_box, False, False, 0)
        vcode_refresh = Gtk.Button.new_from_stock(Gtk.STOCK_REFRESH)
        vcode_refresh.connect('clicked', self.on_vcode_refresh_clicked)
        button_box.pack_start(vcode_refresh, False, False, 0)
        vcode_confirm = Gtk.Button.new_from_stock(Gtk.STOCK_OK)
        vcode_confirm.connect('clicked', self.on_vcode_confirm_clicked)
        button_box.pack_start(vcode_confirm, False, False, 0)
        button_box.props.halign = Gtk.Align.CENTER

        gutil.async_call(
            auth.get_signin_vcode, cookie, codeString,
            callback=self.update_img)
        self.img = Gtk.Image()
        box.pack_start(self.img, False, False, 0)

        box.show_all()

    def get_vcode(self):
        return self.vcode_entry.get_text()

    def update_img(self, req_data, error=None):
        if error or not req_data:
            self.refresh_vcode()
            return
        vcode_path = os.path.join(
                Config.get_tmp_path(self.username),
                'bcloud-signin-vcode.jpg')
        with open(vcode_path, 'wb') as fh:
            fh.write(req_data)
        self.vcode_img.set_from_file(vcode_path)

    def refresh_vcode(self):
        def _refresh_vcode(info, error=None):
            if not info or error:
                print('Failed to refresh vcode:', info, error)
                return
            self.codeString = info['data']['verifyStr']
            gutil.async_call(
                auth.get_signin_vcode, self.cookie, self.codeString,
                callback=self.update_img)

        gutil.async_call(
            auth.refresh_sigin_vcode, self.cookie, self.token,
            self.vcodetype, callback=_refresh_vcode)

    def check_entry(self, *args):
        if len(self.vcode_entry.get_text()) == 4:
            self.response(Gtk.ResponseType.OK)

    def on_vcode_refresh_clicked(self, button):
        self.refresh_vcode()

    def on_vcode_confirm_clicked(self, button):
        self.check_entry()


class SigninDialog(Gtk.Dialog):

    profile = None
    password_changed = False

    def __init__(self, app, auto_signin=True):
        super().__init__(
                _('Sign in now'), app.window, Gtk.DialogFlags.MODAL)
        self.app = app
        self.auto_signin = auto_signin

        self.set_default_size(460, 260)
        self.set_border_width(15)
        
        self.conf = Config.load_conf()
        self.profile = None

        box = self.get_content_area()
        box.set_spacing(8)

        username_ls = Gtk.ListStore(str)
        for username in self.conf['profiles']:
            username_ls.append([username,])
        self.username_combo = Gtk.ComboBox.new_with_entry()
        self.username_combo.set_model(username_ls)
        self.username_combo.set_entry_text_column(0)
        self.username_combo.set_tooltip_text(_('Username/Email/Phone...'))
        box.pack_start(self.username_combo, False, False, 0)
        self.username_combo.connect('changed', self.on_username_changed)

        self.password_entry = Gtk.Entry()
        self.password_entry.set_placeholder_text(_('Password ..'))
        self.password_entry.props.visibility = False
        self.password_entry.connect('changed', self.on_password_entry_changed)
        box.pack_start(self.password_entry, False, False, 0)

        self.remember_check = Gtk.CheckButton.new_with_label(
                _('Remember Password'))
        self.remember_check.props.margin_top = 20
        self.remember_check.props.margin_left = 20
        box.pack_start(self.remember_check, False, False, 0)
        self.remember_check.connect('toggled', self.on_remember_check_toggled)

        self.signin_check = Gtk.CheckButton.new_with_label(
                _('Signin Automatically'))
        self.signin_check.set_sensitive(False)
        self.signin_check.props.margin_left = 20
        box.pack_start(self.signin_check, False, False, 0)
        self.signin_check.connect('toggled', self.on_signin_check_toggled)

        self.signin_button = Gtk.Button.new_with_label(_('Sign in'))
        self.signin_button.props.margin_top = 10
        self.signin_button.connect('clicked', self.on_signin_button_clicked)
        box.pack_start(self.signin_button, False, False, 0)

        self.infobar = Gtk.InfoBar()
        self.infobar.set_message_type(Gtk.MessageType.ERROR)
        box.pack_end(self.infobar, False, False, 0)
        info_content = self.infobar.get_content_area()
        self.info_label = Gtk.Label.new(
                _('Failed to sign in, please try again.'))
        info_content.pack_start(self.info_label, False, False, 0)

        box.show_all()
        self.infobar.hide()

        GLib.timeout_add(500, self.load_defualt_profile)

    def load_defualt_profile(self):
        if self.conf['default']:
            self.use_profile(self.conf['default'])
            self.password_changed = False
            # auto_signin here
            if self.signin_check.get_active() and self.auto_signin:
                self.signin_button.set_sensitive(False)
                self.signin()
        return False

    def on_username_changed(self, combo):
        tree_iter = combo.get_active_iter()
        username = ''
        if tree_iter != None:
            model = combo.get_model()
            username = model[tree_iter][0]
            self.use_profile(username)
        else:
            entry = combo.get_child()
            username = entry.get_text()
            self.profile = None

    def use_profile(self, username):
        model = self.username_combo.get_model()
        for row in model: 
            if row[0] == username:
                self.username_combo.set_active_iter(row.iter)
                break
        self.profile = gutil.load_profile(username)
        self.password_entry.set_text(self.profile['password'])
        self.remember_check.set_active(self.profile['remember-password'])
        if self.profile['remember-password']:
            self.signin_check.set_active(self.profile['auto-signin'])
        else:
            self.signin_check.set_active(False)
        self.password_changed = False

    def signin_failed(self, error=None):
        if error:
            self.info_label.set_text(error)
        self.infobar.show_all()
        self.signin_button.set_sensitive(True)
        self.signin_button.set_label(_('Sign in'))

    def on_password_entry_changed(self, entry):
        self.password_changed = True

    def on_remember_check_toggled(self, button):
        if button.get_active():
            self.signin_check.set_sensitive(True)
        else:
            self.signin_check.set_sensitive(False)
            self.signin_check.set_active(False)
        if self.profile:
            self.profile['remember-password'] = self.remember_check.get_active()
            gutil.dump_profile(self.profile)

    def on_signin_check_toggled(self, button):
        if self.profile:
            self.profile['auto-signin'] = self.signin_check.get_active()
            gutil.dump_profile(self.profile)

    def on_signin_button_clicked(self, button):
        if (len(self.password_entry.get_text()) <= 1 or
                not self.username_combo.get_child().get_text()):
            return
        self.infobar.hide()
        button.set_label(_('In process...'))
        button.set_sensitive(False)
        self.signin()

    def signin(self):
        def on_get_rsa_bduss(result, error=None):
            status, info = result
            if status == 4:
                self.signin_failed(
                    _('Please check username and password are correct!'))
            elif status == 0:
                cookie.load_list(info)
                self.signin_button.set_label(_('Get bdstoken...'))
                gutil.async_call(
                    auth.get_bdstoken, cookie, callback=on_get_bdstoken)
            elif status == 257:
                vcodetype, codeString = info
                dialog = SigninVcodeDialog(
                    self, username, cookie, tokens['token'],
                    codeString, vcodetype)
                dialog.run()
                vcode = dialog.get_vcode()
                dialog.destroy()
                if not vcode or len(vcode) != 4:
                    self.signin_failed(
                        _('Please input verification code!'))
                    return
                self.signin_button.set_label(_('Get bduss...'))
                gutil.async_call(
                        auth.get_bduss, cookie,
                        tokens['token'], username, password, vcode,
                        codeString, callback=on_get_rsa_bduss)
            else:
                self.signin_failed(
                    _('Unknown err_no {0}, please try again!').format(
                        status))

        def on_get_public_key(info, error=None):
            '''获取公钥之后'''
            if not info or error:
                self.signin_failed(
                    _('Error: Failed to get RSA public key!'))
                return
            else:
                nonlocal public_key
                nonlocal rsakey
                public_key = info['pubkey']
                rsakey = info['key']
                gutil.async_call(
                    auth.get_rsa_bduss, cookie, tokens['token'],
                    username, password, public_key, rsakey,
                    callback=on_get_rsa_bduss)

        def on_get_bdstoken(bdstokens, error=None):
            if error or not bdstokens:
                self.signin_failed(
                    _('Error: Failed to get bdstokens!'))
                return
            nonlocal tokens
            if not bdstokens['bdstoken']:
                # Failed to get bdstoken, try RSA encryption
                self.signin_button.set_label(_('Try RSA encryption..'))
                gutil.async_call(
                        auth.get_public_key, cookie, tokens,
                        callback=on_get_public_key)
            else:
                for token in bdstokens:
                    tokens[token] = bdstokens[token]
                self.update_profile(
                        username, password, cookie, tokens, dump=True)

        def on_get_bduss(result, error=None):
            status, info = result
            if status == 4:
                self.signin_failed(
                    _('Please check username and password are correct!'))
            elif status == 0:
                cookie.load_list(info)
                self.signin_button.set_label(_('Get bdstoken...'))
                gutil.async_call(
                    auth.get_bdstoken, cookie, callback=on_get_bdstoken)
            elif status == 257:
                vcodetype, codeString = info
                dialog = SigninVcodeDialog(
                    self, username, cookie, tokens['token'],
                    codeString, vcodetype)
                dialog.run()
                vcode = dialog.get_vcode()
                dialog.destroy()
                if not vcode or len(vcode) != 4:
                    self.signin_failed(
                        _('Please input verification code!'))
                    return
                self.signin_button.set_label(_('Get bduss...'))
                gutil.async_call(
                        auth.get_bduss, cookie,
                        tokens['token'], username, password, vcode,
                        codeString, callback=on_get_bduss)
            else:
                self.signin_failed(
                    _('Unknown err_no {0}, please try again!').format(
                        status))

        def on_check_login(status, error=None):
            if error or not status:
                self.signin_failed(
                        _('Failed to get check login, please try again.'))
            elif len(status['data']['codeString']):
                codeString = status['data']['codeString']
                vcodetype = status['data']['vcodetype']
                dialog = SigninVcodeDialog(
                    self, username, cookie, tokens['token'],
                    codeString, vcodetype)
                dialog.run()
                vcode = dialog.get_vcode()
                dialog.destroy()
                if not vcode or len(vcode) != 4:
                    self.signin_failed(
                        _('Please input verification code!'))
                    return
                self.signin_button.set_label(_('Get bduss...'))
                gutil.async_call(
                        auth.get_bduss, cookie,
                        tokens['token'], username, password, vcode,
                        codeString, callback=on_get_bduss)
            else:
                self.signin_button.set_label(_('Get bduss...'))
                gutil.async_call(
                        auth.get_bduss, cookie, tokens['token'], username,
                        password, callback=on_get_bduss)

        def on_get_UBI(ubi_cookie, error=None):
            if error or not ubi_cookie:
                self.signin_failed(
                        _('Failed to get UBI cookie, please try again.'))
            else:
                cookie.load_list(ubi_cookie)
                self.signin_button.set_label(_('Get token...'))
                gutil.async_call(
                        auth.check_login, cookie, tokens['token'], username,
                        callback=on_check_login)

        def on_get_token(token, error=None):
            if error or not token:
                self.signin_failed(
                        _('Failed to get tokens, please try again.'))
            else:
                nonlocal tokens
                tokens['token'] = token
                self.signin_button.set_label(_('Get UBI...'))
                gutil.async_call(
                        auth.get_UBI, cookie, token, callback=on_get_UBI)

        def on_get_BAIDUID(uid_cookie, error=None):
            if error or not uid_cookie:
                self.signin_failed(
                        _('Failed to get BAIDUID cookie, please try agin.'))
            else:
                cookie.load_list(uid_cookie)
                self.signin_button.set_label(_('Get BAIDUID...'))
                gutil.async_call(
                        auth.get_token, cookie, callback=on_get_token)


        username = self.username_combo.get_child().get_text()
        password = self.password_entry.get_text()
        # 使用本地的缓存token, 有效期是三天
        if not self.password_changed and self.signin_check.get_active():
            cookie, tokens = self.load_auth(username)
            if cookie and tokens:
                self.update_profile(username, password, cookie, tokens)
                return
        cookie = RequestCookie()
        tokens = {}
        public_key = ''
        rsakey = ''
        cookie.load('cflag=65535%3A1; PANWEB=1;')
        self.signin_button.set_label(_('Get cookie...'))
        gutil.async_call(
                auth.get_BAIDUID, callback=on_get_BAIDUID)

    def load_auth(self, username):
        auth_file = os.path.join(Config.get_tmp_path(username), 'auth.json')
        # 如果授权信息被缓存, 并且没过期, 就直接读取它.
        if os.path.exists(auth_file):
            if time.time() - os.stat(auth_file).st_mtime < DELTA:
                with open(auth_file) as fh:
                    c, tokens = json.load(fh)
                cookie = RequestCookie(c)
                return cookie, tokens
        return None, None

    def dump_auth(self, username, cookie, tokens):
        auth_file = os.path.join(Config.get_tmp_path(username), 'auth.json')
        with open(auth_file, 'w') as fh:
            json.dump([str(cookie), tokens], fh)

    def update_profile(self, username, password, cookie, tokens, dump=False):
        if not self.profile:
            self.profile = gutil.load_profile(username)
        self.profile['username'] = username
        self.profile['remember-password'] = self.remember_check.get_active()
        self.profile['auto-signin'] = self.signin_check.get_active()
        if self.profile['remember-password']:
            self.profile['password'] = password
        else:
            self.profile['password'] = ''
        gutil.dump_profile(self.profile)

        if username not in self.conf['profiles']:
            self.conf['profiles'].append(username)
        if self.profile['auto-signin']:
            self.conf['default'] = username
        Config.dump_conf(self.conf)
        self.app.cookie = cookie
        self.app.tokens = tokens
        # dump auth info
        if dump:
            self.dump_auth(username, cookie, tokens)
        self.app.profile = self.profile
        self.app.window.set_default_size(*self.profile['window-size'])
        self.hide()

########NEW FILE########
__FILENAME__ = TrashPage

# Copyright (C) 2014 LiuLang <gsushzhsosgsu@gmail.com>
# Use of this source code is governed by GPLv3 license that can be found
# in http://www.gnu.org/licenses/gpl-3.0.html

import time

from gi.repository import GdkPixbuf
from gi.repository import GObject
from gi.repository import Gtk
from gi.repository import Pango

from bcloud import Config
_ = Config._
from bcloud import gutil
from bcloud import pcs
from bcloud import util

(ICON_COL, NAME_COL, PATH_COL, FSID_COL, TOOLTIP_COL, SIZE_COL,
    HUMANSIZE_COL, DELETING_COL, REMAINING_COL) = list(range(9))
MAX_DAYS = 10  # 10天后会自动从回收站中删除
ICON_SIZE = 24

class TrashPage(Gtk.Box):

    icon_name = 'trash-symbolic'
    disname = _('Trash')
    tooltip = _('Files deleted.')
    first_run = True
    page_num = 1
    has_next = False
    filelist = []

    def __init__(self, app):
        super().__init__(orientation=Gtk.Orientation.VERTICAL)
        self.app = app

        control_box = Gtk.Box(spacing=0)
        control_box.props.margin_bottom = 10
        self.pack_start(control_box, False, False, 0)

        restore_button = Gtk.Button.new_with_label(_('Restore'))
        restore_button.connect('clicked', self.on_restore_button_clicked)
        control_box.pack_start(restore_button, False, False, 0)

        reload_button = Gtk.Button.new_with_label(_('Reload'))
        reload_button.connect('clicked', self.on_reload_button_clicked)
        control_box.pack_start(reload_button, False, False, 0)

        clear_button = Gtk.Button.new_with_label(_('Clear Trash'))
        clear_button.set_tooltip_text(_('Will delete all files in trash'))
        clear_button.connect('clicked', self.on_clear_button_clicked)
        control_box.pack_end(clear_button, False, False, 0)

        delete_button = Gtk.Button.new_with_label(_('Delete'))
        delete_button.set_tooltip_text(_('Delete selected files permanently'))
        delete_button.connect('clicked', self.on_delete_button_clicked)
        control_box.pack_end(delete_button, False, False, 0)

        # show loading process
        self.loading_spin = Gtk.Spinner()
        self.loading_spin.props.margin_right = 5
        control_box.pack_end(self.loading_spin, False, False, 0)

        scrolled_win = Gtk.ScrolledWindow()
        self.pack_start(scrolled_win, True, True, 0)

        # icon name, disname, path, fs_id, tooltip,
        # size, humansize, deleting time, remaining days
        self.liststore = Gtk.ListStore(
                str, str, str, str, str,
                GObject.TYPE_INT64, str, str, str)
        self.treeview = Gtk.TreeView(model=self.liststore)
        selection = self.treeview.get_selection()
        selection.set_mode(Gtk.SelectionMode.MULTIPLE)
        self.treeview.set_rubber_banding(True)
        self.treeview.set_tooltip_column(PATH_COL)
        self.treeview.set_headers_clickable(True)
        self.treeview.set_reorderable(True)
        self.treeview.set_search_column(NAME_COL)
        scrolled_win.add(self.treeview)

        icon_cell = Gtk.CellRendererPixbuf()
        name_cell = Gtk.CellRendererText(
                ellipsize=Pango.EllipsizeMode.END, ellipsize_set=True)
        name_col = Gtk.TreeViewColumn()
        name_col.set_title(_('Name'))
        name_col.pack_start(icon_cell, False)
        name_col.pack_start(name_cell, True)
        if Config.GTK_LE_36:
            name_col.add_attribute(icon_cell, 'icon_name', ICON_COL)
            name_col.add_attribute(name_cell, 'text', NAME_COL)
        else:
            name_col.set_attributes(icon_cell, icon_name=ICON_COL)
            name_col.set_attributes(name_cell, text=NAME_COL)
        name_col.set_expand(True)
        self.treeview.append_column(name_col)
        name_col.set_sort_column_id(NAME_COL)
        self.liststore.set_sort_func(NAME_COL, gutil.tree_model_natsort)

        size_cell = Gtk.CellRendererText()
        size_col = Gtk.TreeViewColumn(
                _('Size'), size_cell, text=HUMANSIZE_COL)
        self.treeview.append_column(size_col)
        size_col.set_sort_column_id(SIZE_COL)

        time_cell = Gtk.CellRendererText()
        time_col = Gtk.TreeViewColumn(
                _('Time'), time_cell, text=DELETING_COL)
        self.treeview.append_column(time_col)
        time_col.set_sort_column_id(DELETING_COL)

        remaining_cell = Gtk.CellRendererText()
        remaining_col = Gtk.TreeViewColumn(
                _('Remaining'), remaining_cell, text=REMAINING_COL)
        self.treeview.append_column(remaining_col)
        remaining_col.set_sort_column_id(REMAINING_COL)


    def load(self):
        self.loading_spin.start()
        self.loading_spin.show_all()
        self.page_num = 1
        self.liststore.clear()
        gutil.async_call(
                pcs.list_trash, self.app.cookie, self.app.tokens, '/',
                self.page_num, callback=self.append_filelist)

    def load_next(self):
        self.loading_spin.start()
        self.loading_spin.show_all()
        self.page_num = self.page_num + 1
        gutil.async_call(
                pcs.list_trash, self.app.cookie, self.app.tokens, '/',
                self.page_num, callback=self.append_filelist)

    def reload(self, *args, **kwds):
        self.load()

    def append_filelist(self, infos, error=None):
        self.loading_spin.stop()
        self.loading_spin.hide()
        if error or not infos or infos['errno'] != 0:
            return
        for pcs_file in infos['list']:
            self.filelist.append(pcs_file)
            path = pcs_file['path']

            icon_name = self.app.mime.get_icon_name(path, pcs_file['isdir'])
            tooltip = gutil.escape(path)
            if pcs_file['isdir'] or 'size' not in pcs_file:
                size = 0
                humansize = ''
            else:
                size = pcs_file['size']
                humansize = util.get_human_size(size)[0]
            remaining_days = util.get_delta_days(
                    int(pcs_file['server_mtime']), time.time())
            remaining_days = str(MAX_DAYS - remaining_days) + ' days'
            self.liststore.append([
                icon_name,
                pcs_file['server_filename'],
                path,
                str(pcs_file['fs_id']),
                tooltip,
                size,
                humansize,
                time.ctime(pcs_file['server_mtime']),
                remaining_days,
                ])

    def on_restore_button_clicked(self, button):
        selection = self.treeview.get_selection()
        model, tree_paths = selection.get_selected_rows()
        if not tree_paths:
            return
        fidlist = []
        for tree_path in tree_paths:
            fidlist.append(model[tree_path][FSID_COL])
        gutil.async_call(
                pcs.restore_trash, self.app.cookie, self.app.tokens,
                fidlist, callback=self.reload)
        self.app.blink_page(self.app.home_page)

    def on_delete_button_clicked(self, button):
        selection = self.treeview.get_selection()
        model, tree_paths = selection.get_selected_rows()
        if not tree_paths:
            return
        fidlist = []
        for tree_path in tree_paths:
            fidlist.append(model[tree_path][FSID_COL])
        gutil.async_call(
                pcs.delete_trash, self.app.cookie, self.app.tokens,
                fidlist, callback=self.reload)

    def on_clear_button_clicked(self, button):
        gutil.async_call(
                pcs.clear_trash, self.app.cookie, self.app.tokens,
                callback=self.reload)

    def on_reload_button_clicked(self, button):
        self.load()

########NEW FILE########
__FILENAME__ = Uploader

# Copyright (C) 2014 LiuLang <gsushzhsosgsu@gmail.com>
# Use of this source code is governed by GPLv3 license that can be found
# in http://www.gnu.org/licenses/gpl-3.0.html

import os
import sys
import threading

from gi.repository import GLib
from gi.repository import GObject

from bcloud import pcs

(FID_COL, NAME_COL, SOURCEPATH_COL, PATH_COL, SIZE_COL,
    CURRSIZE_COL, STATE_COL, STATENAME_COL, HUMANSIZE_COL,
    PERCENT_COL, TOOLTIP_COL, THRESHOLD_COL) = list(range(12))

class State:
    '''下载状态常量'''
    UPLOADING = 0
    WAITING = 1
    PAUSED = 2
    FINISHED = 3
    CANCELED = 4
    ERROR = 5

SLICE_THRESHOLD = 2 ** 18  # 256k, 小于这个值, 不允许使用分片上传


class Uploader(threading.Thread, GObject.GObject):

    __gsignals__ = {
            # 一个新的文件分片完成上传
            'slice-sent': (GObject.SIGNAL_RUN_LAST,
                # fid, slice_end, md5 
                GObject.TYPE_NONE, (GObject.TYPE_INT, GObject.TYPE_INT64, str)),
            # 请求UploadPage来合并文件分片
            'merge-files': (GObject.SIGNAL_RUN_LAST,
                # fid
                GObject.TYPE_NONE, (GObject.TYPE_INT, )),
            # 上传完成, 这个信号只有rapid_upload/upload_small_file才使用
            'uploaded': (GObject.SIGNAL_RUN_LAST, 
                # fid
                GObject.TYPE_NONE, (GObject.TYPE_INT, )),
            'disk-error': (GObject.SIGNAL_RUN_LAST,
                # fid
                GObject.TYPE_NONE, (GObject.TYPE_INT, )),
            'network-error': (GObject.SIGNAL_RUN_LAST,
                # fid
                GObject.TYPE_NONE, (GObject.TYPE_INT, )),
            }

    is_slice_upload = False

    def __init__(self, parent, row, cookie, tokens):
        '''
        parent    - UploadPage
        row       - UploadPage.liststore中的一个记录
        '''
        threading.Thread.__init__(self)
        GObject.GObject.__init__(self)
        self.daemon = True

        self.parent = parent
        self.cookie = cookie
        self.tokens = tokens

        self.row = row[:]

    def run(self):
        #self.check_exists()
        # 如果文件大小小于4M, 就直接上传, 不支持断点续传(没必要).
        # 否则先尝试快速上传模式, 如果没有中的话, 就再进行分片上传.
        # 分片上传, 是最费事的, 也最占带宽.
        # 分片上传, 支持断点续传.
        if self.row[SIZE_COL] > SLICE_THRESHOLD:
            self.rapid_upload()
        else:
            self.slice_upload()

    # Open API
    def pause(self):
        self.row[STATE_COL] = State.PAUSED
        #if self.is_slice_upload:

    # Open API
    def stop(self):
        self.row[STATE_COL] = State.CANCELED

    def check_exists(self):
        meta = pcs.get_metas(self.row[PATH_COL])

    def rapid_upload(self):
        '''快速上传.

        如果失败, 就自动调用分片上传.
        '''
        info = pcs.rapid_upload(
            self.cookie, self.tokens,
            self.row[SOURCEPATH_COL], self.row[PATH_COL])
        if info and info['md5'] and info['fs_id']:
            self.emit('uploaded', self.row[FID_COL])
        else:
            self.slice_upload()

    def slice_upload(self):
        '''分片上传'''
        self.is_slice_upload = True
        fid = self.row[FID_COL]
        slice_start = self.row[CURRSIZE_COL]
        slice_end = self.row[CURRSIZE_COL]
        file_size = os.path.getsize(self.row[SOURCEPATH_COL])
        if file_size < slice_start:
            self.emit('disk-error', fid)
            return
        elif file_size == slice_start and slice_start == self.row[SIZE_COL]:
            self.emit('uploaded', fid)
            return
        fh = open(self.row[SOURCEPATH_COL], 'rb')
        fh.seek(slice_start)
        while self.row[STATE_COL] == State.UPLOADING:
            if slice_end >= file_size:
                self.emit('merge-files', self.row[FID_COL])
                break
            slice_start = slice_end
            slice_end = min(slice_start + self.row[THRESHOLD_COL], file_size)
            data = fh.read(slice_end - slice_start)
            slice_end = slice_start + len(data)
            info = pcs.slice_upload(self.cookie, data)
            if info and 'md5' in info:
                self.emit('slice-sent', fid, slice_end, info['md5'])
            else:
                self.emit('network-error', fid)
                break
        if not fh.closed:
            fh.close()
        return

GObject.type_register(Uploader)

########NEW FILE########
__FILENAME__ = UploadPage

# Copyright (C) 2014 LiuLang <gsushzhsosgsu@gmail.com>
# Use of this source code is governed by GPLv3 license that can be found
# in http://www.gnu.org/licenses/gpl-3.0.html

import math
import os
import sqlite3

from gi.repository import Gio
from gi.repository import GLib
from gi.repository import GObject
from gi.repository import Gtk
from gi.repository import Pango

from bcloud import Config
_ = Config._
from bcloud.FolderBrowserDialog import FolderBrowserDialog
from bcloud.Uploader import Uploader
from bcloud import gutil
from bcloud import pcs
from bcloud import util

(FID_COL, NAME_COL, SOURCEPATH_COL, PATH_COL, SIZE_COL,
    CURRSIZE_COL, STATE_COL, STATENAME_COL, HUMANSIZE_COL,
    PERCENT_COL, TOOLTIP_COL, THRESHOLD_COL) = list(range(12))
TASK_FILE = 'upload.sqlite'

class State:
    '''下载状态常量'''
    UPLOADING = 0
    WAITING = 1
    PAUSED = 2
    FINISHED = 3
    CANCELED = 4
    ERROR = 5

StateNames = [
    _('UPLOADING'),
    _('WAITING'),
    _('PAUSED'),
    _('FINISHED'),
    _('CANCELED'),
    _('ERROR'),
    ]

RUNNING_STATES = (State.FINISHED, State.UPLOADING, State.WAITING)


class UploadPage(Gtk.Box):

    icon_name = 'upload-symbolic'
    disname = _('Upload')
    tooltip = _('Uploading tasks')
    first_run = True
    workers = {}  # {`fid`: (worker, row)}
    commit_count = 0

    def __init__(self, app):
        super().__init__(orientation=Gtk.Orientation.VERTICAL)
        self.app = app

    def check_first(self):
        if self.first_run:
            self.first_run = False
            self.load()

    def load(self):
        control_box = Gtk.Box()
        self.pack_start(control_box, False, False, 0)

        start_button = Gtk.Button.new_with_label(_('Start'))
        start_button.connect('clicked', self.on_start_button_clicked)
        control_box.pack_start(start_button, False, False, 0)

        pause_button = Gtk.Button.new_with_label(_('Pause'))
        pause_button.connect('clicked', self.on_pause_button_clicked)
        control_box.pack_start(pause_button, False, False, 0)

        upload_button = Gtk.Button.new_with_label(_('Upload files'))
        upload_button.set_tooltip_text(_('Upload files and folders'))
        upload_button.connect('clicked', self.on_upload_button_clicked)
        control_box.pack_start(upload_button, False, False, 0)

        open_folder_button = Gtk.Button.new_with_label(_('Open Directory'))
        open_folder_button.connect(
                'clicked', self.on_open_folder_button_clicked)
        open_folder_button.props.margin_left = 40
        control_box.pack_start(open_folder_button, False, False, 0)

        remove_button = Gtk.Button.new_with_label(_('Remove'))
        remove_button.connect('clicked', self.on_remove_button_clicked)
        control_box.pack_end(remove_button, False, False, 0)

        scrolled_win = Gtk.ScrolledWindow()
        self.pack_start(scrolled_win, True, True, 0)
        
        # fid, source_name, source_path, path, size,
        # currsize, state, statename, humansize, percent, tooltip
        # slice size
        self.liststore = Gtk.ListStore(
            GObject.TYPE_INT, str, str, str, GObject.TYPE_INT64,
            GObject.TYPE_INT64, int, str, str, GObject.TYPE_INT, str,
            GObject.TYPE_INT64)
        self.treeview = Gtk.TreeView(model=self.liststore)
        self.treeview.set_headers_clickable(True)
        self.treeview.set_reorderable(True)
        self.treeview.set_search_column(NAME_COL)
        self.treeview.set_tooltip_column(TOOLTIP_COL)
        self.selection = self.treeview.get_selection()
        self.selection.set_mode(Gtk.SelectionMode.MULTIPLE)
        scrolled_win.add(self.treeview)

        name_cell = Gtk.CellRendererText(
                ellipsize=Pango.EllipsizeMode.END, ellipsize_set=True)
        name_col = Gtk.TreeViewColumn(_('Name'), name_cell, text=NAME_COL)
        name_col.set_expand(True)
        self.treeview.append_column(name_col)
        name_col.set_sort_column_id(NAME_COL)
        self.liststore.set_sort_func(NAME_COL, gutil.tree_model_natsort)

        percent_cell = Gtk.CellRendererProgress()
        percent_col = Gtk.TreeViewColumn(
                _('Progress'), percent_cell, value=PERCENT_COL)
        self.treeview.append_column(percent_col)
        percent_col.props.min_width = 145
        percent_col.set_sort_column_id(PERCENT_COL)

        size_cell = Gtk.CellRendererText()
        size_col = Gtk.TreeViewColumn(
                _('Size'), size_cell, text=HUMANSIZE_COL)
        self.treeview.append_column(size_col)
        size_col.props.min_width = 100
        size_col.set_sort_column_id(SIZE_COL)

        state_cell = Gtk.CellRendererText()
        state_col = Gtk.TreeViewColumn(
                _('State'), state_cell, text=STATENAME_COL)
        self.treeview.append_column(state_col)
        state_col.props.min_width = 100
        state_col.set_sort_column_id(PERCENT_COL)

        self.show_all()
        self.init_db()
        self.load_tasks_from_db()

    def init_db(self):
        cache_path = os.path.join(
                Config.CACHE_DIR, self.app.profile['username'])
        if not os.path.exists(cache_path):
            os.makedirs(cache_path, exist_ok=True)
        db = os.path.join(cache_path, TASK_FILE)
        self.conn = sqlite3.connect(db)
        self.cursor = self.conn.cursor()
        sql = '''CREATE TABLE IF NOT EXISTS upload (
        fid INTEGER PRIMARY KEY,
        name CHAR NOT NULL,
        source_path CHAR NOT NULL,
        path CHAR NOT NULL,
        size INTEGER NOT NULL,
        curr_size INTEGER NOT NULL,
        state INTEGER NOT NULL,
        state_name CHAR NOT NULL,
        human_size CHAR NOT NULL,
        percent INTEGER NOT NULL,
        tooltip CHAR,
        threshold INTEGER NOT NULL
        )
        '''
        self.cursor.execute(sql)
        sql = '''CREATE TABLE IF NOT EXISTS slice (
        fid INTEGER NOT NULL,
        slice_end INTEGER NOT NULL,
        md5 CHAR NOT NULL
        )
        '''
        self.cursor.execute(sql)

        # mig 3.2.1 -> 3.3.1
        try:
            req = self.cursor.execute('SELECT * FROM tasks')
            tasks = []
            threshold = 2 ** 20
            for row in req:
                tasks.append(row + ('', threshold))
            if tasks:
                sql = '''INSERT INTO upload
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)'''
                self.cursor.executemany(sql, tasks)
                self.check_commit()
            self.cursor.execute('DROP TABLE tasks')
            self.check_commit()
        except sqlite3.OperationalError:
            pass

    def reload(self):
        pass

    def load_tasks_from_db(self):
        sql = 'SELECT * FROM upload'
        req = self.cursor.execute(sql)
        for task in req:
            self.liststore.append(task)

    def check_commit(self):
        '''当修改数据库超过50次后, 就自动commit数据.'''
        self.commit_count = self.commit_count + 1
        if self.commit_count >= 50:
            self.commit_count = 0
            self.conn.commit()

    def add_task_db(self, task):
        '''向数据库中写入一个新的任务记录, 并返回它的fid'''
        sql = '''INSERT INTO upload (
        name, source_path, path, size, curr_size, state, state_name,
        human_size, percent, tooltip, threshold)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)'''
        req = self.cursor.execute(sql, task)
        self.check_commit()
        return req.lastrowid

    def add_slice_db(self, fid, slice_end, md5):
        '''在数据库中加入上传任务分片信息'''
        sql = 'INSERT INTO slice VALUES(?, ?, ?)'
        self.cursor.execute(sql, (fid, slice_end, md5))
        self.check_commit()

    def get_task_db(self, source_path):
        '''从数据库中查询source_path的信息.
        
        如果存在的话, 就返回这条记录;
        如果没有的话, 就返回None
        '''
        sql = 'SELECT * FROM upload WHERE source_path=? LIMIT 1'
        req = self.cursor.execute(sql, [source_path, ])
        if req:
            return req.fetchone()
        else:
            None

    def get_slice_db(self, fid):
        '''从数据库中取得fid的所有分片.
        
        返回的是一个list, 里面是按顺序排好的md5的值
        '''
        sql = 'SELECT md5 FROM slice WHERE fid=?'
        req = self.cursor.execute(sql, [fid, ])
        if req:
            return [r[0] for r in req]
        else:
            return None

    def update_task_db(self, row):
        '''更新数据库中的任务信息'''
        sql = '''UPDATE upload SET 
        curr_size=?, state=?, state_name=?, human_size=?, percent=?
        WHERE fid=? LIMIT 1;
        '''
        self.cursor.execute(sql, [
            row[CURRSIZE_COL], row[STATE_COL], row[STATENAME_COL],
            row[HUMANSIZE_COL], row[PERCENT_COL], row[FID_COL]
            ])
        self.check_commit()

    def remove_task_db(self, fid):
        '''将任务从数据库中删除'''
        self.remove_slice_db(fid)
        sql = 'DELETE FROM upload WHERE fid=?'
        self.cursor.execute(sql, [fid, ])
        self.check_commit()

    def remove_slice_db(self, fid):
        '''将上传任务的分片从数据库中删除'''
        sql = 'DELETE FROM slice WHERE fid=?'
        self.cursor.execute(sql, [fid, ])
        self.check_commit()

    def on_destroy(self, *args):
        if not self.first_run:
            self.conn.commit()
            for row in self.liststore:
                self.pause_task(row, scan=False)
            self.conn.commit()
            self.conn.close()

    def add_task(self):
        file_dialog = Gtk.FileChooserDialog(
            _('Choose a file..'), self.app.window,
            Gtk.FileChooserAction.OPEN,
            (Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
            Gtk.STOCK_OK, Gtk.ResponseType.OK))
        file_dialog.set_modal(True)
        file_dialog.set_select_multiple(True)
        file_dialog.set_default_response(Gtk.ResponseType.OK)
        response = file_dialog.run()
        if response != Gtk.ResponseType.OK:
            file_dialog.destroy()
            return
        source_paths = file_dialog.get_filenames()
        file_dialog.destroy()
        if source_paths:
            self.add_file_tasks(source_paths)

    # Open API
    def add_file_tasks(self, source_paths, dir_name=None):
        '''批量创建上传任务

        source_path - 本地文件的绝对路径
        dir_name    - 文件在服务器上的父目录, 如果为None的话, 会弹出一个
                      对话框让用户来选择一个目录.
        '''
        def scan_folders(folder_path):
            file_list = os.listdir(folder_path)
            source_paths = [os.path.join(folder_path, f) for f in file_list]
            self.add_file_tasks(
                    source_paths,
                    os.path.join(dir_name, os.path.split(folder_path)[1]))

        self.check_first()
        if not dir_name:
            folder_dialog = FolderBrowserDialog(self, self.app)
            response = folder_dialog.run()
            if response != Gtk.ResponseType.OK:
                folder_dialog.destroy()
                return
            dir_name = folder_dialog.get_path()
            folder_dialog.destroy()
        for source_path in source_paths:
            if (os.path.split(source_path)[1].startswith('.') and
                    not self.app.profile['uploading-hidden-files']):
                continue
            if os.path.isfile(source_path):
                self.add_file_task(source_path, dir_name)
            elif os.path.isdir(source_path):
                scan_folders(source_path)
        self.app.blink_page(self)
        self.scan_tasks()

    def add_file_task(self, source_path, dir_name):
        '''创建新的上传任务'''
        row = self.get_task_db(source_path)
        if row:
            return
        source_dir, filename = os.path.split(source_path)
        
        path = os.path.join(dir_name, filename)
        size = os.path.getsize(source_path)
        total_size = util.get_human_size(size)[0]
        tooltip = gutil.escape(
                _('From {0}\nTo {1}').format(source_path, path))
        if size < 2 ** 27:           # 128M 
            threshold = 2 ** 17      # 128K
        elif size < 2 ** 29:         # 512M
            threshold =  2 ** 19     # 512K
        elif size < 10 * (2 ** 30):  # 10G
            threshold = math.ceil(size / 1000)
        else:
            self.app.toast(
                    _('{0} is too large to upload (>10G).').format(path))
            return
        task = [
            filename,
            source_path,
            path,
            size,
            0,
            State.WAITING,
            StateNames[State.WAITING],
            '0 / {0}'.format(total_size),
            0,
            tooltip,
            threshold,
            ]
        row_id = self.add_task_db(task)
        task.insert(0, row_id)
        self.liststore.append(task)

    def start_task(self, row, scan=True):
        '''启动上传任务.

        将任务状态设定为Uploading, 如果没有超过最大任务数的话;
        否则将它设定为Waiting.
        '''
        if row[STATE_COL] in RUNNING_STATES :
            self.scan_tasks()
            return
        row[STATE_COL] = State.WAITING
        row[STATENAME_COL] = StateNames[State.WAITING]
        self.update_task_db(row)
        if scan:
            self.scan_tasks()

    # Open API
    def pause_tasks(self):
        '''暂停所有上传任务'''
        if self.first_run:
            return
        for row in self.liststore:
            self.pause_task(row, scan=False)

    def pause_task(self, row, scan=True):
        '''暂停下载任务'''
        if row[STATE_COL] == State.UPLOADING:
            self.remove_worker(row[FID_COL], stop=False)
        if row[STATE_COL] in (State.UPLOADING, State.WAITING):
            row[STATE_COL] = State.PAUSED
            row[STATENAME_COL] = StateNames[State.PAUSED]
            self.update_task_db(row)
            if scan:
                self.scan_tasks()

    def remove_task(self, row, scan=True):
        '''删除下载任务'''
        if row[STATE_COL] == State.UPLOADING:
            self.remove_worker(row[FID_COL], stop=True)
        self.remove_task_db(row[FID_COL])
        tree_iter = row.iter
        if tree_iter:
            self.liststore.remove(tree_iter)
        if scan:
            self.scan_tasks()

    def scan_tasks(self):
        if len(self.workers.keys()) >= self.app.profile['concurr-tasks']:
            return
        for row in self.liststore:
            if len(self.workers.keys()) >= self.app.profile['concurr-tasks']:
                break
            if row[STATE_COL] == State.WAITING:
                self.start_worker(row)
        return True

    def start_worker(self, row):
        def on_worker_slice_sent(worker, fid, slice_end, md5):
            GLib.idle_add(do_worker_slice_sent, fid, slice_end, md5)

        def do_worker_slice_sent(fid, slice_end, md5):
            if fid not in self.workers:
                return
            row = self.get_row_by_fid(fid)
            if not row:
                return
            row[CURRSIZE_COL] = slice_end
            total_size = util.get_human_size(row[SIZE_COL])[0]
            curr_size = util.get_human_size(slice_end, False)[0]
            row[PERCENT_COL] = int(slice_end / row[SIZE_COL] * 100)
            row[HUMANSIZE_COL] = '{0} / {1}'.format(curr_size, total_size)
            self.update_task_db(row)
            self.add_slice_db(fid, slice_end, md5)

        def on_worker_merge_files(worker, fid):
            GLib.idle_add(do_worker_merge_files, fid)

        def do_worker_merge_files(fid):
            def on_create_superfile(pcs_file, error=None):
                if error or not pcs_file:
                    print('on create superfile:', pcs_file, error)
                    do_worker_error(fid)
                    return
                else:
                    self.remove_slice_db(fid)
                    do_worker_uploaded(fid)

            block_list = self.get_slice_db(fid)
            if fid not in self.workers:
                return
            row = self.get_row_by_fid(fid)
            if not row:
                return
            if not block_list:
                # TODO
                pass
            else:
                gutil.async_call(
                    pcs.create_superfile, self.app.cookie, row[PATH_COL],
                    block_list, callback=on_create_superfile)

        def on_worker_uploaded(worker, fid):
            GLib.idle_add(do_worker_uploaded, fid)

        def do_worker_uploaded(fid):
            if fid not in self.workers:
                return
            row = self.get_row_by_fid(fid)
            if not row:
                return
            row[PERCENT_COL] = 100
            total_size = util.get_human_size(row[SIZE_COL])[0]
            row[HUMANSIZE_COL] = '{0} / {1}'.format(total_size, total_size)
            row[STATE_COL] = State.FINISHED
            row[STATENAME_COL] = StateNames[State.FINISHED]
            self.update_task_db(row)
            self.workers.pop(fid, None)
            self.app.toast(_('{0} uploaded').format(row[NAME_COL]))
            self.scan_tasks()

        def on_worker_disk_error(worker, fid):
            GLib.idle_add(do_worker_error, fid)

        def on_worker_network_error(worker, fid):
            GLib.idle_add(do_worker_error, fid)

        def do_worker_error(fid):
            row = self.get_row_by_fid(fid)
            if not row:
                return
            row[STATE_COL] = State.ERROR
            row[STATENAME_COL] = StateNames[State.ERROR]
            self.update_task_db(row)
            self.remove_worker(fid, stop=False)
            self.scan_tasks()

        if row[FID_COL] in self.workers:
            return
        row[STATE_COL] = State.UPLOADING
        row[STATENAME_COL] = StateNames[State.UPLOADING]
        worker = Uploader(self, row, self.app.cookie, self.app.tokens)
        self.workers[row[FID_COL]] = (worker, row)
        # For slice upload
        worker.connect('slice-sent', on_worker_slice_sent)
        worker.connect('merge-files', on_worker_merge_files)
        # For upload_small_files/rapid_upload
        worker.connect('uploaded', on_worker_uploaded)
        worker.connect('disk-error', on_worker_disk_error)
        worker.connect('network-error', on_worker_network_error)
        worker.start()

    def remove_worker(self, fid, stop=True):
        if fid not in self.workers:
            return
        worker = self.workers[fid][0]
        if stop:
            worker.stop()
        else:
            worker.pause()
        self.workers.pop(fid, None)

    def get_row_by_source_path(self, source_path):
        for row in self.liststore:
            if row[SOURCEPATH_COL] == source_path:
                return row
        return None

    def get_row_by_fid(self, fid):
        for row in self.liststore:
            if row[FID_COL] == fid:
                return row
        return None

    def operate_selected_rows(self, operator):
        '''对选中的条目进行操作.

        operator  - 处理函数
        '''
        model, tree_paths = self.selection.get_selected_rows()
        if not tree_paths:
            return
        fids = []
        for tree_path in tree_paths:
            fids.append(model[tree_path][FID_COL])
        for fid in fids:
            row = self.get_row_by_fid(fid)
            if row:
                operator(row)

    def on_start_button_clicked(self, button):
        self.operate_selected_rows(self.start_task)

    def on_pause_button_clicked(self, button):
        self.operate_selected_rows(self.pause_task)

    def on_remove_button_clicked(self, button):
        self.operate_selected_rows(self.remove_task)

    def on_open_folder_button_clicked(self, button):
        model, tree_paths = self.selection.get_selected_rows()
        if not tree_paths or len(tree_paths) != 1:
            return
        tree_path = tree_paths[0]
        path = model[tree_path][PATH_COL]
        dir_name = os.path.split(path)[0]
        self.app.home_page.load(dir_name)
        self.app.switch_page(self.app.home_page)

    def on_upload_button_clicked(self, button):
        self.add_task()

########NEW FILE########
__FILENAME__ = util

# Copyright (C) 2014 LiuLang <gsushzhsosgsu@gmail.com>
# Use of this source code is governed by GPLv3 license that can be found
# in http://www.gnu.org/licenses/gpl-3.0.html

import base64
import datetime
import hashlib
import os
import random
import re
import urllib.parse
import time

from Crypto.PublicKey import RSA
from Crypto.Cipher import PKCS1_OAEP
#from Crypto.Cipher import PKCS1_v1_5

SIZE_K = 2 ** 10
SIZE_M = 2 ** 20
SIZE_G = 2 ** 30
SIZE_T = 2 ** 40

def timestamp():
    '''返回当前的时间标记, 以毫秒为单位'''
    return str(int(time.time() * 1000))

def latency():
    '''返回操作时消耗的时间.

    这个值是0.1-1之前的五位小数, 用于跟踪服务器的响应时间.
    我们需要随机生成它.
    '''
    return str(random.random())[:7]

def rec_split_path(path):
    '''将一个路径进行分隔, 分别得到每父母的绝对路径及目录名'''
    if len(path) > 1 and path.endswith('/'):
        path = path[:-1]
    result = []
    while path != '/':
        parent, name = os.path.split(path)
        result.append((path, name))
        path = parent
    result.append(('/', '/'))
    result.reverse()
    return result

def get_human_size(size, use_giga=True):
    '''将文件大小由byte, 转为人类可读的字符串
    size     -  整数, 文件的大小, 以byte为单位
    use_giga - 如果这个选项为False, 那最大的单位就是MegaBytes, 而不会用到
               GigaBytes, 这个在显示下载进度时很有用, 因为可以动态的显示下载
               状态.
    '''

    '''将文件大小转为人类可读的形式'''
    size_kb = '{0:,}'.format(size)
    if size < SIZE_K:
        return ('{0} B'.format(size), size_kb)
    if size < SIZE_M:
        return ('{0:.1f} kB'.format(size / SIZE_K), size_kb)
    if size < SIZE_G or not use_giga:
        return ('{0:.1f} MB'.format(size / SIZE_M), size_kb)
    if size < SIZE_T:
        return ('{0:.1f} GB'.format(size / SIZE_G), size_kb)
    return ('{0:.1f} TB'.format(size / SIZE_T), size_kb)

def get_delta_days(from_sec, to_sec):
    '''计算两个时间节点之间的日期'''
    seconds = abs(to_sec - from_sec)
    delta = datetime.timedelta(seconds=seconds)
    return delta.days

def list_remove_by_index(l, index):
    '''将list中的index位的数据删除'''
    if index < 0 or index >= len(l):
        raise ValueError('index out of range')
    if index == (len(l) - 1):
        l.pop()
    elif index == 0:
        l = l[1:]
    else:
        l = l[0:index] + l[index+1:]

    return l

def uri_to_path(uri):
    if not uri or len(uri) < 7:
        return ''
    return urllib.parse.unquote(uri).replace('file://', '')

def uris_to_paths(uris):
    '''将一串URI地址转为绝对路径, 用于处理桌面程序中的文件拖放'''
    source_paths = []
    for uri in uris.split('\n'):
        source_path = uri_to_path(uri)
        if source_path:
            source_paths.append(source_path)
    return source_paths

def natsort(string):
    '''按照语言里的意义对字符串进行排序.

    这个方法用于替换按照字符编码顺序对字符串进行排序.
    相关链接:
    http://stackoverflow.com/questions/2545532/python-analog-of-natsort-function-sort-a-list-using-a-natural-order-algorithm
    http://www.codinghorror.com/blog/2007/12/sorting-for-humans-natural-sort-order.html
    '''
    return [int(s) if s.isdigit() else s for s in re.split('(\d+)', string)]


def RSA_encrypt(public_key, message):
    '''用RSA加密字符串.

    public_key - 公钥
    message    - 要加密的信息, 使用UTF-8编码的字符串
    @return 使用base64编码的字符串
    '''
    rsakey = RSA.importKey(public_key)
    rsakey = PKCS1_OAEP.new(rsakey)
    #rsakey = PKCS1_v1_5.new(rsakey)
    encrypted = rsakey.encrypt(message.encode())
    return base64.encodestring(encrypted).decode()

########NEW FILE########
__FILENAME__ = VCodeDialog

# Copyright (C) 2014 LiuLang <gsushzhsosgsu@gmail.com>
# Use of this source code is governed by GPLv3 license that can be found
# in http://www.gnu.org/licenses/gpl-3.0.html

import os

from gi.repository import Gtk

from bcloud import Config
_ = Config._
from bcloud import gutil
from bcloud import net


class VCodeDialog(Gtk.Dialog):

    def __init__(self, parent, app, info):
        super().__init__(
            _('Verification..'), app.window, Gtk.DialogFlags.MODAL,
            (Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
            Gtk.STOCK_OK, Gtk.ResponseType.OK))

        self.set_default_response(Gtk.ResponseType.OK)
        self.set_default_size(320, 200)
        self.set_border_width(10)
        self.app = app

        box = self.get_content_area()
        box.set_spacing(10)

        gutil.async_call(
            net.urlopen, info['img'], {
                'Cookie': app.cookie.header_output(),
            }, callback=self.update_img)
        self.img = Gtk.Image()
        box.pack_start(self.img, False, False, 0)

        self.entry = Gtk.Entry()
        self.entry.connect(
                'activate',
                lambda *args: self.response(Gtk.ResponseType.OK))
        box.pack_start(self.entry, False, False, 0)

        box.show_all()

    def get_vcode(self):
        return self.entry.get_text()

    def update_img(self, request, error=None):
        if error or not request:
            # TODO: add a refresh button
            return
        vcode_path = os.path.join(
                Config.get_tmp_path(self.app.profile['username']),
                'bcloud-download-vcode.jpg')
        with open(vcode_path, 'wb') as fh:
            fh.write(request.data)
        self.img.set_from_file(vcode_path)

########NEW FILE########
__FILENAME__ = Widgets
# Copyright (C) 2014 LiuLang <gsushzhsosgsu@gmail.com>
# Use of this source code is governed by GPLv3 license that can be found
# in http://www.gnu.org/licenses/gpl-3.0.html


from gi.repository import Gtk

class LeftLabel(Gtk.Label):
    '''左对齐的标签'''

    def __init__(self, label):
        super().__init__(label)
        self.props.xalign = 0.0

class SelectableLeftLabel(LeftLabel):
    '''左对齐的标签, 标签内容可选中'''

    def __init__(self, label):
        super().__init__(label)
        self.props.selectable = True

########NEW FILE########
