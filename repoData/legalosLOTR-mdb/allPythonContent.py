__FILENAME__ = config
from configobj import ConfigObj
import os
import sys


#helper methods
def we_are_frozen():
    # All of the modules are built-in to the interpreter, e.g., by py2exe
    return hasattr(sys, "frozen")


def module_path():
    encoding = sys.getfilesystemencoding()
    if we_are_frozen():
        return os.path.dirname(unicode(sys.executable, encoding))
    return os.path.dirname(unicode(__file__, encoding))


def get_platform():
    if sys.platform.startswith('win'):
        return 'windows'
    elif sys.platform.startswith('linux'):
        return 'linux'
    else:
        return None


def post_process():
    type_conv()
    handle_proxy()


def handle_proxy():
    if (config['http_proxy'] != 'None' and len(config['http_proxy']) > 0):
        os.environ['http_proxy'] = config['http_proxy']


def type_conv():
    if (config['debug'] == 'True'):
        config['debug'] = True
    else:
        config['debug'] = False

    config['upd_freq'] = int(config['upd_freq'])
    config['update_last_checked'] = int(config['update_last_checked'])


def get_resource(*args):
    return os.path.join(module_path(), 'resources', *args)


#Non configurable stuff
version = u'0.1'
db_version = u'0.2'

mdb_dir = os.path.join(os.path.expanduser('~'), u'.mdb')
db_file = os.path.join(mdb_dir, u'mdbdata.sqlite')
images_folder = os.path.join(mdb_dir, u'images')
config_file_path = os.path.join(mdb_dir, u'.config')

api_url = 'http://www.imdbapi.com'
api_movie_param = 't'
api_extra_opts = {}  # '&plot=full'

movie_formats = ['avi', 'mkv', 'mp4', 'm4v', 'rmvb']

img_size = '100'

imdb_thread_pool_size = 10

platform = get_platform()

update_url = 'http://legaloslotr.github.com/mdb/update.html'

abt_dlg_content = {
    'title': 'About',
    'body': u'''
        <body bgcolor="#f1f1f1">
        <center>
        <table><tr><td><img src="{1}"></td>
        <td><h2>MDB<br>MovieDirBrowser</h2></td>
        </tr></table>
        v{0}<br>
        <a href="http://legaloslotr.github.com/mdb">
        http://legaloslotr.github.com/mdb</a><br>
        <a href="mailto:legalos.lotr@gmail.com">Ankur Dahiya</a><br>
        Data collected from <a href="http://imdb.com">IMDB</a>
        </center></body>
        '''.format(version, get_resource('images', 'MDB_64.png')),
}

cant_connect_content = {
    'title': 'Connection Error',
    'body': "Unable to connect to the internet.\
            \nPlease check your internet connection.",
}

no_updates_content = {
    'title': 'No updates',
    'body': "No updates were found.",
}

#Configurable stuff
defaults = {
        'http_proxy': 'None',
        'debug': 'False',
        'update_last_checked': '0',
        'upd_freq': '7',  # days
        'db_version': '0.1',
}

prefs_item_map = [
        ('debug', 'bool', 'Debug Mode'),
        ('http_proxy', 'str', 'Http Proxy'),
        ('upd_freq', 'str', 'Update Frequency(days)')
]

config = ConfigObj(defaults)
config_user = ConfigObj(config_file_path)
config.merge(config_user)
config.filename = config_file_path

# FIXME dont do this here
if (not os.path.exists(mdb_dir)):
    os.mkdir(mdb_dir)

config.write()
post_process()

########NEW FILE########
__FILENAME__ = DBbuilder
#!/usr/bin/python

import os
from subprocess import call
import sys
import sqlite3
import wx_signal
import wx
import re
import threading
import config
import requests
import Queue
import time


#HELPER FUNCTIONS#
def zenity_error(msg):
    sys.stderr.write(msg + '\n')
    if (config.config['debug']):
        try:
            call(['zenity', '--error', '--text', msg])
        except OSError, e:
            pass
            # zenity not available


def create_database(conn, cur):
    cur.execute('''CREATE TABLE movies (
            filename TEXT,
            title TEXT,
            year INTEGER,
            released TEXT,
            genre TEXT,
            rating REAL,
            runtime TEXT,
            director TEXT,
            actors TEXT,
            plot TEXT,
            poster TEXT,
            imdbID TEXT
            )''')
    cur.execute('CREATE UNIQUE INDEX filename_index ON movies (filename)')
    conn.commit()


def add_to_db(filename, file_data, conn, cur):
    args = [filename, file_data['Title'], file_data['Year'],
        file_data['Released'], file_data['Genre'], file_data['imdbRating'],
        file_data['Runtime'], file_data['Director'], file_data['Actors'],
        file_data['Plot'], file_data['Poster'], file_data['imdbID']]

    if (is_in_db(conn, cur, filename)):
        return

    cur.execute('INSERT INTO movies VALUES(?,?,?,?,?,?,?,?,?,?,?,?)',
            tuple(args))
    conn.commit()


def get_movie_name(filename):
    # TODO if filename doesnt get any results on imdb, maybe we can use the
    # folder name
    old_filename = filename

    # make sure reject words dont have a char which is special in regexes, or
    # else it shud be properly escaped
    # Remove everything after a reject word
    reject_words = ['dvd', 'xvid', 'brrip', 'r5', 'unrated', '720p', 'x264',
                    'klaxxon', 'axxo', 'br_300', '300mb', 'cd1', 'cd2']
    reject_words_strict = ['eng', 'scr', 'dual']  # UNUSED

    # dont process this file if a panic word is found
    panic_words = ['sample']

    #prepare: remove ext, make lower
    filename = ".".join(filename.split('.')[:-1])
    filename = filename.lower()

    #0 panic words
    for word in panic_words:
        if (filename.find(word) != -1):
            return ''

    #1 remove everythin in brackets
    brackets = [('\(', '\)'), ('\[', '\]'), ('\{', '\}')]
    for b in brackets:
        filename = re.sub(b[0] + '.*?' + b[1], ' ', filename)

    #2 remove year and stuff following it
    filename = re.sub('\d\d\d\d.*', ' ', filename)

    #3 reject_words
    for word in reject_words:
        filename = re.sub(word + '.*', ' ', filename)

    #cleanup
    filename = re.sub('\s+', ' ', re.sub(
        '[\._\-\(\)\[\]\{\}]', ' ', filename).strip())

    return filename


def get_imdb_data(filename, queue, exit_now):
    if (exit_now.is_set()):
        print "thread saw exit_now", filename
        queue.put((None, filename, True))
        return
    moviename = get_movie_name(filename)
    if (moviename == ' ' or moviename == ''):
        queue.put((None, filename, False))
        print "thread done", filename
        return

    params = {config.api_movie_param: moviename}
    params.update(config.api_extra_opts)

    try:
        response = requests.get(config.api_url, params=params)
    except requests.RequestException, e:
        queue.put((None, filename, True))
        print "thread done", filename
        return

    if (not response.ok):
        # Should we stop further processing here?
        print "Some error with the api!"
        queue.put((None, filename, False))
        print "thread done", filename
        return

    if (response.json['Response'] == 'True'):
        if (exit_now.is_set()):
            print "thread saw exit_now", filename
            queue.put((None, filename, True))
            return
        process_img(response.json['Poster'], filename)
        queue.put((response.json, filename, False))
        #print "thread done", filename
        return
    else:
        print "none data for", filename
        queue.put((None, filename, False))
        print "thread done", filename
        return


def process_img(poster, filename):
    if (poster is None or poster == 'N/A'):
        return
    img_url = poster[:-7] + config.img_size + '.jpg'
    img_file = os.path.join(config.images_folder, filename + '.jpg')
    img_fh = open(img_file, 'wb')
    try:
        img_fh.write(requests.get(img_url).content)
    except requests.RequestException, e:
        # do nothing?
        pass
    img_fh.close()


def is_in_db(conn, cur, filename):
    if conn is None:
        return False
    else:
        res = cur.execute('SELECT * FROM movies WHERE filename=?',
                          (filename,)).fetchall()
        if len(res) > 0:
            return True
        else:
            return False


def get_from_db(conn, cur, filename):
    res = cur.execute('SELECT * FROM movies WHERE filename=?',
            (filename,)).fetchall()
    return res[0]


def signal_gui(parent, filename):
    evt = wx_signal.FileDoneEvent(wx_signal.myEVT_FILE_DONE, -1, filename)
    wx.PostEvent(parent, evt)


def process_files(files, gui_ready, parent, threadpool, exit_now):
    conn = sqlite3.connect(config.db_file)
    cur = conn.cursor()

    file_data_queue = Queue.Queue()
    threadpool.map_async(lambda fil, queue=file_data_queue, exit_now=exit_now:
            get_imdb_data(fil, queue, exit_now), files)

    for i in range(len(files)):
        if (gui_ready.wait()):
            gui_ready.clear()

            imdb_data, filename, conn_err = file_data_queue.get()
            print "dbbuilder recd", filename

            if (conn_err and not exit_now.is_set()):
                evt = wx_signal.ShowMsgEvent(wx_signal.myEVT_SHOW_MSG, -1,
                        config.cant_connect_content)
                wx.PostEvent(parent, evt)
                return

            if (imdb_data is not None and not exit_now.is_set()):
                add_to_db(filename, imdb_data, conn, cur)
                signal_gui(parent, filename)
                print "processed", filename
            else:
                gui_ready.set()

    print "leaving process_files"
    #print "joining threadpool"
    #threadpool.join()


class DBbuilderThread(threading.Thread):
    def __init__(self, parent, files, threadpool):
        threading.Thread.__init__(self)
        self.parent = parent
        self.files = files
        self.gui_ready = threading.Event()
        self.gui_ready.set()
        self.exit_now = threading.Event()
        self.exit_now.clear()
        self.threadpool = threadpool

    def run(self):
        """Overrides Thread.run. Don't call this directly its called internally
        when you call Thread.start().
        """
        print 'dbbuilder running'
        start = time.time()
        process_files(self.files, self.gui_ready, self.parent, self.threadpool,
                self.exit_now)
        print 'dbbuilder exiting'
        print '{0} files processed in {1}s'.format(len(self.files),
                time.time() - start)

########NEW FILE########
__FILENAME__ = dialogs
#!/usr/bin/python

import wx
from html_window import ClickableHtmlWindow
import config


class HtmlDialog(wx.Dialog):
    def __init__(self, parent, content, *args, **kwds):
        kwds["style"] = wx.DEFAULT_DIALOG_STYLE
        wx.Dialog.__init__(self, parent, *args, **kwds)
        self.SetBackgroundColour((240, 240, 240))

        self.html_panel = ClickableHtmlWindow(self)
        self.SetTitle(content['title'])
        self.html_panel.SetPage(content['body'])
        self.html_panel.attach_to_frame(parent, 0)

        self.button_1 = wx.Button(self, -1, "Close")
        self.Bind(wx.EVT_BUTTON, self.on_close)

        self.__set_properties()
        self.__do_layout()

    def __set_properties(self):
        self.SetSize((400, 180))

    def __do_layout(self):
        sizer_1 = wx.BoxSizer(wx.VERTICAL)
        sizer_1.Add(self.html_panel, 1, wx.EXPAND, 0)
        sizer_1.Add(self.button_1, 0, wx.ALIGN_CENTER, 0)
        self.SetSizer(sizer_1)
        self.Layout()

    def on_close(self, evt):
        self.Destroy()


class PrefsDialog(wx.Dialog):
    def __init__(self, items_map, *args, **kwds):
        # begin wxGlade: MyDialog.__init__
        kwds["style"] = wx.DEFAULT_DIALOG_STYLE
        wx.Dialog.__init__(self, *args, **kwds)

        self.items_map = items_map
        self.controls_map = {}

        self.button_1 = wx.Button(self, -1, "OK")
        self.button_2 = wx.Button(self, -1, "Cancel")

        self.Bind(wx.EVT_BUTTON, self.on_ok, self.button_1)
        self.Bind(wx.EVT_BUTTON, self.on_cancel, self.button_2)

        self.__set_properties()
        self.__do_layout()
        self.display_items()
        # end wxGlade

    def __set_properties(self):
        # begin wxGlade: MyDialog.__set_properties
        self.SetTitle("Preferences - MDB")
        # end wxGlade

    def __do_layout(self):
        # begin wxGlade: MyDialog.__do_layout
        self.sizer_1 = wx.BoxSizer(wx.VERTICAL)
        sizer_2 = wx.BoxSizer(wx.HORIZONTAL)
        self.sizer_4_staticbox = wx.StaticBox(self, -1, "")
        self.sizer_4_staticbox.Lower()
        self.sizer_4 = wx.StaticBoxSizer(self.sizer_4_staticbox, wx.VERTICAL)
        self.sizer_1.Add(self.sizer_4, 1, wx.ALL | wx.EXPAND, 5)
        sizer_2.Add(self.button_1, 0, 0, 0)
        sizer_2.Add(self.button_2, 0, 0, 0)
        self.sizer_1.Add(sizer_2, 0, wx.ALL | wx.ALIGN_RIGHT, 5)
        self.SetSizer(self.sizer_1)
        #sizer_1.Fit(self)
        #self.Layout()
        # end wxGlade

    def on_ok(self, evt):
        for item in self.items_map:
            name = item[0]
            config.config[name] = self.controls_map[name].GetValue()

        config.config.write()
        config.post_process()
        self.Destroy()

    def on_cancel(self, evt):
        self.Destroy()

    def display_items(self):
        for item in self.items_map:
            name = item[0]
            typ = item[1]
            label = item[2]
            if (typ == 'bool'):
                checkbox = wx.CheckBox(self, -1, label)
                checkbox.SetValue(config.config[name])
                self.controls_map[name] = checkbox
                self.sizer_4.Add(checkbox, 0, wx.ALL, 5)
            elif (typ == 'str'):
                label_ctrl = wx.StaticText(self, -1, label)
                text_ctrl = wx.TextCtrl(self, -1, "")
                text_ctrl.SetMinSize((200, 27))
                text_ctrl.SetValue(str(config.config[name]))

                self.controls_map[name] = text_ctrl

                sizer = wx.BoxSizer(wx.HORIZONTAL)
                sizer.Add(label_ctrl, 0, wx.RIGHT | wx.ALIGN_CENTER_VERTICAL,
                        5)
                sizer.Add(text_ctrl, 0, wx.ALIGN_RIGHT |
                        wx.ALIGN_CENTER_VERTICAL, 0)

                self.sizer_4.Add(sizer, 1, wx.ALL | wx.ALIGN_RIGHT, 5)

        self.sizer_1.Fit(self)
        self.Layout()

########NEW FILE########
__FILENAME__ = gui
#!/usr/bin/python

import sys
import wx
import wx.lib.agw.ultimatelistctrl as ULC
from wx.lib.mixins.listctrl import ColumnSorterMixin
import sqlite3
from DBbuilder import create_database, is_in_db, DBbuilderThread, get_from_db
import os
import wx_signal
import wx.html
from html_window import ClickableHtmlWindow
from dialogs import HtmlDialog, PrefsDialog
import config
from update import UpdateThread
from multiprocessing.pool import ThreadPool


#CLASSES#
class MyFrame(wx.Frame, ColumnSorterMixin):
    def __init__(self, parent, conn, cur):
        wx.Frame.__init__(self, parent, -1, "MDB")
        self.set_icon()
        self.conn = conn
        self.cur = cur
        self.db_thread = None
        self.upd_thread = None

        self.Bind(wx_signal.EVT_FILE_DONE, self.on_file_done)
        self.Bind(wx_signal.EVT_SHOW_MSG, self.on_show_msg)
        self.Bind(wx.EVT_CLOSE, self.on_close)
        self.add_menu()
        self.add_sb()
        self.total_rows = 0

        self.sizer = wx.BoxSizer(wx.VERTICAL)
        self.SetSizer(self.sizer)

        self.display_width = wx.GetDisplaySize()[0]
        self.itemDataMap = {}

        self.lst = self.build_list()
        ColumnSorterMixin.__init__(self, 6)
        self.sizer.Add(self.lst, 1, wx.EXPAND)
        self.Layout()

    def set_icon(self):
        ib = wx.IconBundle()
        ib.AddIconFromFile(config.get_resource('images', 'MDB_all.ico'),
            wx.BITMAP_TYPE_ICO)
        self.SetIcons(ib)
 
    def on_close(self, evt):
        if (self.db_thread is not None):
            self.db_thread.exit_now.set()
            self.db_thread.gui_ready.set()
            self.db_thread.join()
        if (self.upd_thread is not None):
            self.upd_thread.join()
        self.Destroy()

    def add_sb(self):
        sb = wx.StatusBar(self)
        self.sb = sb
        sb.SetFieldsCount(2)
        sb.SetStatusWidths([-2, -1])
        sb.SetStatusText("0 Files", 1)
        self.SetStatusBar(sb)

    def build_list(self):
        lst = ULC.UltimateListCtrl(
            self, wx.ID_ANY, agwStyle=wx.LC_REPORT | wx.LC_VRULES |
            wx.LC_HRULES | wx.LC_SINGLE_SEL | ULC.ULC_HAS_VARIABLE_ROW_HEIGHT)

        self.Bind(wx.EVT_LIST_COL_CLICK, self.OnColClick, lst)

        lst.InsertColumn(0, "Title")
        lst.InsertColumn(1, "Rating")
        lst.InsertColumn(2, "Year")
        lst.InsertColumn(3, "Genre")
        lst.InsertColumn(4, "Runtime")
        lst.InsertColumn(5, "Details")

        lst.SetColumnWidth(0, 100)
        lst.SetColumnWidth(1, 50)
        lst.SetColumnWidth(2, 50)
        lst.SetColumnWidth(3, 100)
        lst.SetColumnWidth(4, 100)
        lst.SetColumnWidth(5, -3)

        return lst

    def add_menu(self):
        menuBar = wx.MenuBar()
        menu = wx.Menu()

        m_open = menu.Append(wx.ID_OPEN, "&Open\tCtrl+O",
                             "Open a folder.")
        self.Bind(wx.EVT_MENU, self.open_folder, m_open)

        m_prefs = menu.Append(wx.ID_PREFERENCES, "&Preferences", "Preferences")
        self.Bind(wx.EVT_MENU, self.on_prefs, m_prefs)

        m_exit = menu.Append(wx.ID_EXIT, "&Exit\tCtrl+Q", "Exit")
        self.Bind(wx.EVT_MENU, self.on_close, m_exit)

        menuBar.Append(menu, "&File")

        menu = wx.Menu()

        m_about = menu.Append(wx.ID_ANY, "&About",
                              "Information about this program")
        self.Bind(wx.EVT_MENU, self.on_about, m_about)

        m_upd = menu.Append(wx.ID_ANY, "&Check For Updates",
                              "Check For Updates")
        self.Bind(wx.EVT_MENU, self.on_chk_upd, m_upd)

        menuBar.Append(menu, "&Help")

        self.SetMenuBar(menuBar)

    def on_chk_upd(self, evt):
        check_for_updates(self, True)

    def on_prefs(self, evt):
        dlg = PrefsDialog(parent=self, items_map=config.prefs_item_map)
        dlg.ShowModal()
        dlg.Destroy()

    def open_folder(self, evt):
        dlg = wx.DirDialog(self, "Choose a directory:",
                          style=wx.DD_DEFAULT_STYLE
                           | wx.DD_DIR_MUST_EXIST
                           #| wx.DD_CHANGE_DIR
                           )

        if dlg.ShowModal() == wx.ID_OK:
            target_dir = dlg.GetPath()
        else:
            return

        dlg.Destroy()

        #create new lst
        self.itemDataMap.clear()
        self.lst.Destroy()
        self.lst = self.build_list()
        ColumnSorterMixin.__init__(self, 6)
        self.sizer.Add(self.lst, 1, wx.EXPAND)
        self.Layout()
        self.Refresh()

        # switch to this dir
        self.total_rows = 0
        self.update_sb()
        os.chdir(target_dir)

        files_with_data, files_wo_data = process_dir('.', self.conn, self.cur)

        for f in files_with_data:
            self.add_row(f)

        if len(files_wo_data) > 0:
            start_dbbuilder(self, files_wo_data)

    def on_about(self, evt):
        abt_dlg = HtmlDialog(self, content=config.abt_dlg_content)
        abt_dlg.ShowModal()
        abt_dlg.Destroy()

    def GetListCtrl(self):
        return self.lst

    def OnColClick(self, event):
        event.Skip()
        self.Refresh()

    def add_row(self, filename):
        # get info from db, build info panel, add to list, update
        # itemdatamap
        data = get_from_db(self.conn, self.cur, filename)

        index = self.lst.InsertStringItem(sys.maxint, data['title'])

        self.lst.SetItemData(index, index)
        self.itemDataMap[index] = (data['title'], data['rating'], data['year'],
            data['genre'], data['runtime'], data['title'])

        self.lst.SetStringItem(index, 1, unicode(data["rating"]))
        self.lst.SetStringItem(index, 2, unicode(data["year"]))
        self.lst.SetStringItem(index, 3, data["genre"])
        self.lst.SetStringItem(index, 4, data["runtime"])
        self.lst.SetItemWindow(index, 5, self.build_info_panel(data),
                expand=True)
        self.total_rows += 1
        self.update_sb()

    def update_sb(self):
        if (self.total_rows == 1):
            self.sb.SetStatusText("1 File", 1)
        else:
            self.sb.SetStatusText("{0} Files".format(self.total_rows), 1)

    def build_info_panel(self, data):
        html_win = ClickableHtmlWindow(self.lst, size=(-1, 180))
        html_win.attach_to_frame(self, 0)
                #style=wx.html.HW_SCROLLBAR_NEVER)

        html_text = u"<table><tr>"
        img_file = os.path.join(config.images_folder, data['filename'] + '.jpg')
        if os.path.exists(img_file):
            html_text += u'<td width="100" rowspan="2">\
                    <img src="{0}"></td>\n'.format(img_file)
        else:
            html_text += u'<td width="100" rowspan="2"></td>'

        # imdb icon
        html_text += u'<td><a href="http://imdb.com/title/{0}">\
                <img src="{1}"></a></td></tr>'.format(data['imdbID'],
                        config.get_resource('images', 'imdb-logo.png'))
        print html_text

        # details
        html_text += u"<tr><td>" + self.generate_label_text(data) + u"</td></tr>"
        html_text += u"</table>"

        html_win.SetPage(html_text)

        return html_win

    def make_wrappable(self, txt):
        wrap_points = ['.', '-', ']', ')']
        for point in wrap_points:
            txt = txt.replace(point, point + ' ')
        return txt

    def generate_label_text(self, data):
        data2 = [('Title', data['title']),
                ('Filename', self.make_wrappable(data['filename'])),
                ('Director', data['director']),
                ('Actors', data['actors']),
                ('Plot', data['plot']),
                ]

        res = u"<table cellspacing=0 cellpadding=2>"
        for item in data2:
            res += u'<tr valign="top"><td valign="top"><b>{0}</b></td>\
                    <td valign="top">{1}</td></tr>\n'.\
                    format(item[0], item[1])

        res += u"</table>"
        #print ''
        #print res
        return res

    def on_file_done(self, evt):
        print "event recieved containing", evt.filename
        self.add_row(evt.filename)
        self.db_thread.gui_ready.set()

    def on_show_msg(self, evt):
        if (evt.html):
            dlg = HtmlDialog(self, content=evt.content)
            dlg.ShowModal()
            dlg.Destroy()
        else:
            wx.MessageBox(evt.content['body'], evt.content['title'],
                    style=wx.OK | wx.CENTER, parent=self)


#HELPER FUNCTIONS#
def is_movie_file(filename):
    if (filename.split('.')[-1] in config.movie_formats):
        return True
    else:
        return False


def start_dbbuilder(frame, files_wo_data):
    if (frame.db_thread is not None):
        frame.db_thread.exit_now.set()
        frame.db_thread.gui_ready.set()
        frame.db_thread.join()

    threadpool = ThreadPool(config.imdb_thread_pool_size)
    frame.db_thread = DBbuilderThread(frame, files_wo_data, threadpool)
    frame.db_thread.start()


def process_dir(directory, conn, cur):
    files_with_data = []
    files_wo_data = []

    for fil in os.listdir(directory):
        if os.path.isdir(os.path.join(directory, fil)):
            fil_children = os.listdir(os.path.join(directory, fil))
            for c in fil_children:
                if is_movie_file(c):
                    if is_in_db(conn, cur, c):
                        files_with_data.append(c)
                    else:
                        files_wo_data.append(c)
        else:
            if is_movie_file(fil):
                if is_in_db(conn, cur, fil):
                    files_with_data.append(fil)
                else:
                    files_wo_data.append(fil)
    return files_with_data, files_wo_data


def check_and_setup():
    try: os.mkdir(config.mdb_dir)
    except OSError, e: pass

    try: os.mkdir(config.images_folder)
    except OSError, e: pass

    if (os.path.exists(config.db_file) and \
            config.config['db_version'] < config.db_version):
        # db_version is old, make new db file
        os.unlink(config.db_file)

    if (not os.path.exists(config.db_file)):
        create_db = True
    else:
        create_db = False

    conn = sqlite3.connect(config.db_file)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    if (create_db):
        create_database(conn, cur)

        config.config['db_version'] = config.db_version
        config.config.write()
        config.post_process()

    return conn, cur


def check_for_updates(frame, force=False):
    if (frame.upd_thread is not None):
        frame.upd_thread.exit_now = True
        frame.upd_thread.join()

    frame.upd_thread = UpdateThread(frame, force)
    frame.upd_thread.start()


#MAIN#
def main():
    conn, cur = check_and_setup()
    if len(sys.argv) == 1:
        # no args, use curdir
        target_files = None
    else:
        target_files = sys.argv[1:]

    if (target_files is None):
        # use cwd as target_files
        files_with_data, files_wo_data = process_dir(u'.', conn, cur)
    else:
        files_with_data = []
        files_wo_data = []

        #target_files should be in cwd
        #make all target_files non_absolute
        for i in range(len(target_files)):
            target_files[i] = unicode(os.path.basename(target_files[i]), 'utf-8')

        for fil in target_files:
            if os.path.isdir(fil):
                f_with, f_wo = process_dir(fil, conn, cur)
                files_with_data.extend(f_with)
                files_wo_data.extend(f_wo)
            else:
                if is_movie_file(fil):
                    if is_in_db(conn, cur, fil):
                        files_with_data.append(fil)
                    else:
                        files_wo_data.append(fil)

    print 'files_with_data', files_with_data
    print 'files_wo_data', files_wo_data

    #spawn threads
    if (config.platform == 'windows' and config.config['debug']):
        app = wx.App(redirect=True)
    else:
        app = wx.App(redirect=False)

    if (not config.config['debug']):
        wx.Log_SetActiveTarget(wx.LogStderr())

    frame = MyFrame(None, conn, cur)

    check_for_updates(frame)

    app.SetTopWindow(frame)
    frame.Maximize()

    for f in files_with_data:
        frame.add_row(f)

    if len(files_wo_data) > 0:
        start_dbbuilder(frame, files_wo_data)

    frame.Show()
    frame.Layout()
    app.MainLoop()

if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = html_window
import wx.html
import wx
from subprocess import call
import config


class ClickableHtmlWindow(wx.html.HtmlWindow):
    def __init__(self, parent, *args, **kwargs):
        wx.html.HtmlWindow.__init__(self, parent, *args, **kwargs)

    def OnCellClicked(self, cell, x, y, evt):
        print "oncellclicked"
        selection = self.SelectionToText()
        link = cell.GetLink()
        button = evt.GetButton()

        if (button == 1 and link is not None):
            # left click on hyperlink
            if (config.platform == 'linux'):
                call(['xdg-open', cell.GetLink().GetHref()])
            elif (config.platform == 'windows'):
                try:
                    from os import startfile
                except ImportError, e:
                    return
                startfile(cell.GetLink().GetHref())
        elif (button == 3 and (len(selection) > 0 or link is not None)):
            menu = wx.Menu()
            if (len(selection) > 0):
                copy = menu.Append(wx.ID_ANY, "Copy")
                self.Bind(wx.EVT_MENU, self.on_copy, copy)
            if (link is not None):
                copy_link = menu.Append(wx.ID_ANY, "Copy Link")
                self.Bind(wx.EVT_MENU,
                        lambda evt, link=link : self.on_copy_link(evt, link),
                        copy_link)

            self.PopupMenu(menu, evt.GetPosition())
            menu.Destroy()

    def on_copy(self, evt):
        self.add_to_clipboard(self.SelectionToText())

    def on_copy_link(self, evt, link):
        self.add_to_clipboard(link.GetHref())

    def add_to_clipboard(self, txt):
        wx.TheClipboard.UsePrimarySelection(False)
        if wx.TheClipboard.Open():
            do = wx.TextDataObject()
            do.SetText(txt)

            wx.TheClipboard.SetData(do)
            wx.TheClipboard.Close()
            wx.TheClipboard.Flush()

            print "Added to clipboard", txt
        else:
            print "Unable to open clipboard"

    def attach_to_frame(self, frame, sb_slot):
        self.SetRelatedFrame(frame, "")
        self.SetRelatedStatusBar(sb_slot)

########NEW FILE########
__FILENAME__ = update
import threading
import time
import requests
import config
import wx_signal
import wx


class UpdateThread(threading.Thread):
    def __init__(self, parent, force=False):
        threading.Thread.__init__(self)
        self.parent = parent
        self.force = force

    def run(self):
        """Overrides Thread.run. Don't call this directly its called internally
        when you call Thread.start().
        """
        print 'update thread running'
        self.check_for_updates()
        print 'update thread exiting'

    def show_upd_dialog(self, data):
        content = {
                'title': 'Updates',
                'body': data['dlg_content']
        }
        evt = wx_signal.ShowMsgEvent(wx_signal.myEVT_SHOW_MSG, -1,
                content, True)
        wx.PostEvent(self.parent, evt)

    def check_for_updates(self):
        time_to_cmp = (config.config['update_last_checked'] +
            (config.config['upd_freq'] * 24 * 3600))
        if (self.force or (int(time.time()) > time_to_cmp)):
            try:
                upd_data = requests.get(config.update_url)
            except requests.RequestException, e:
                print "RequestException", e
                if (self.force):
                    evt = wx_signal.ShowMsgEvent(wx_signal.myEVT_SHOW_MSG, -1,
                            config.cant_connect_content)
                    wx.PostEvent(self.parent, evt)
                # FIXME Back off for some time  or check after 7 days?
                return

            if (upd_data.ok and 'version' in upd_data.json and\
                    upd_data.json['version'] > config.version):
                # FIXME make sure versions can be compared as strings!
                print "valid update found"
                self.show_upd_dialog(upd_data.json)
            else:
                print 'no updates'
                # report no updates
                if (self.force):
                    evt = wx_signal.ShowMsgEvent(wx_signal.myEVT_SHOW_MSG, -1,
                            config.no_updates_content)
                    wx.PostEvent(self.parent, evt)

            config.config['update_last_checked'] = int(time.time())
            config.config.write()
            config.post_process()
        else:
            print "nothing to do here"

########NEW FILE########
__FILENAME__ = wx_signal
#!/usr/bin/python

import wx

myEVT_FILE_DONE = wx.NewEventType()
EVT_FILE_DONE = wx.PyEventBinder(myEVT_FILE_DONE, 1)

myEVT_SHOW_MSG = wx.NewEventType()
EVT_SHOW_MSG = wx.PyEventBinder(myEVT_SHOW_MSG, 1)


class FileDoneEvent(wx.PyCommandEvent):
    def __init__(self, etype, eid, filename=None):
        """Creates the event object"""
        wx.PyCommandEvent.__init__(self, etype, eid)
        self.filename = filename


class ShowMsgEvent(wx.PyCommandEvent):
    def __init__(self, etype, eid, content=None, html=False):
        """Creates the event object"""
        wx.PyCommandEvent.__init__(self, etype, eid)
        self.content = content
        self.html = html

########NEW FILE########
__FILENAME__ = nautilus-script
#!/usr/bin/python

from subprocess import call
import os

MDB_EXECUTABLE = 'MDB'

def zenity_error(msg):
    call(['zenity', '--error', '--text', msg])

filePathList = os.environ['NAUTILUS_SCRIPT_SELECTED_FILE_PATHS'].splitlines()
# assuming all arguments are from cur dir only, which is true due to the
# nature of nautilus
for i in range(len(filePathList)):
    filePathList[i] = os.path.basename(filePathList[i])

try:
    if len(filePathList) == 0:
        call([MDB_EXECUTABLE])
    else:
        call_list = [MDB_EXECUTABLE]
        call_list.extend(filePathList)
        call(call_list)
except Exception, e:
    zenity_error(str(e))

########NEW FILE########
__FILENAME__ = test_main
#!/usr/bin/python

import sys
import os
sys.path.append(os.path.abspath(".."))
import MDB.DBbuilder as DBbuilder
import wx
import shutil
import MDB.wx_signal as wx_signal
from MDB.gui import MyFrame
from MDB.gui import check_and_setup
from MDB.DBbuilder import images_folder


#DATA#
movies1 = [('Die Welle[2008]DvDrip[Ger]-FXG.avi', 'die welle', True),
        ('J.Edgar[2011]BRRip XviD-ETRG.avi', 'j edgar', True),
        ('The Descendants[2011]DVDRip XviD-ETRG.avi', 'the descendants', True),
        ('Columbus.Circle.2012.DVDRiP.XviD-SiC.avi', 'columbus circle', True),
        ('Jaane.Tu...Ya.Jaane.Na.2008.DVDRip-SaM.avi', 'jaane tu ya jaane na',
            True),
        ('Band Baaja Baaraat - DVDRip - XviD - 1CDRip - [DDR].avi',
            'band baaja baaraat', False),
        ('percy jackson & the olympians- the lightning thief (2010)' +
        'dvdrip .mkv', 'percy jackson & the olympians the lightning thief',
        True),
        ('Serenity[2005][Aka.Firefly]DvDrip[Eng]-aXXo.avi', 'serenity', True),
        ('(500)Days of Summer.[2009].RETAIL.DVDRIP.XVID.[Eng]-DUQA.avi',
            '500 days of summer', True),
        ('Into the Wild.avi', 'into the wild', True),
        ('The.Incredibles[2004]DvDrip[Eng]-spencer.avi', 'the incredibles',
            True),
        ]

movies2 = [('social network', ('The Social Network', '2010')),
        ('die welle', ('The Wave', '2008'))]

movie_filenames = ['Die Welle[2008]DvDrip[Ger]-FXG.avi',
    'J.Edgar[2011]BRRip XviD-ETRG.avi']
#SETUP FUNCTIONS#
def setup_db_dir():
    try: shutil.rmtree('test')
    except: pass
    os.mkdir('test')

    home_var = 'HOME'
    if (home_var not in os.environ):
        home_var = 'USERPROFILE'
    home_old = os.environ[home_var]
    os.environ[home_var] = os.path.abspath('./test')
    conn, cur, mdb_dir = check_and_setup()

    os.environ[home_var] = home_old

    return conn, cur, mdb_dir

#TEST CASES#
def test_name_parser():
    for filename, moviename, _ in movies1:
        assert(DBbuilder.get_movie_name(filename) == moviename)


def test_get_imdb_data_correctness():
    for moviename, data in movies2:
        res = DBbuilder.get_imdb_data(moviename)
        assert((res['Title'], res['Year']) == data)


def test_get_imdb_data_existence():
    for filename, moviename, _ in movies1:
        res = DBbuilder.get_imdb_data(moviename)
        assert(res is not None)
        print ""
        print filename, '->', res['Title'], res['Year'], res['Genre']


def test_dbbuilder_images():
    conn, cur, mdb_dir = setup_db_dir()

    dbthread = DBbuilder.DBbuilderThread(None, [item[0] for item in movies1],
            mdb_dir)
    dbthread.start()
    dbthread.join()

    for item in movies1:
        if item[2]:
            assert(os.path.exists(os.path.join(mdb_dir, images_folder,
                item[0] + '.jpg')))
        else:
            assert(True)


class CountingFrame(wx.Frame):
    def __init__(self, parent, total):
        wx.Frame.__init__(self, parent, title="Test", size=(300, 300))
        self.Bind(wx_signal.EVT_FILE_DONE, self.on_file_done)
        self.total = total

    def on_file_done(self, evt):
        print "event recieved containing" + evt.filename
        self.total -= 1
        assert True
        if self.total == 0:
            self.Destroy()


def test_DBbuilder_signal():
    conn, cur, mdb_dir = setup_db_dir()

    app = wx.App(False)
    frame = CountingFrame(None, total=len(movies1))

    dbthread = DBbuilder.DBbuilderThread(frame, [item[0] for item in movies1],
            mdb_dir)
    dbthread.start()

    app.MainLoop()


def test_gui_row_addition():
    conn, cur, mdb_dir = setup_db_dir()

    app = wx.App()
    frame = MyFrame(None, conn, cur, mdb_dir)
    app.SetTopWindow(frame)
    frame.Maximize()
    frame.Show()

    dbthread = DBbuilder.DBbuilderThread(frame, [item[0] for item in movies1],
            mdb_dir)
    dbthread.start()

    app.MainLoop()

########NEW FILE########
