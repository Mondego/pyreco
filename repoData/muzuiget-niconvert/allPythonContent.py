__FILENAME__ = argpaser
from argparse import ArgumentParser


def create_parser():
    parser = ArgumentParser(
        description='弹幕字幕下载和转换工具',
        prefix_chars='-+')

    add_arg = parser.add_argument_group('输入输出').add_argument

    add_arg('url',
            help='视频地址',
            type=str)

    add_arg('-o', '--output-filename',
            metavar='FILENAME',
            help='输出文件，默认为视频标题',
            type=str,
            default=None)

    add_arg('-p', '--create-playlist',
            help='同时输出播放列表',
            action='store_true')

    add_arg = parser.add_argument_group('弹幕选项').add_argument

    add_arg('-a', '--assist-params',
            metavar='NAME1=1,NAME2=2',
            help='辅助参数，手动指定无法直接获取的参数',
            type=str,
            default=None)

    add_arg('-f', '--custom-filter',
            metavar='FILE',
            help='过滤文件，关键词过滤规则文件名',
            type=str,
            default=None)

    add_arg('-B', '--disable-bottom-filter',
            help='不要过滤底部弹幕',
            action='store_true')

    add_arg('-G', '--disable-guest-filter',
            help='不要过滤游客弹幕',
            action='store_true')

    add_arg('-V', '--disable-video-filter',
            help='不要过滤云屏蔽弹幕',
            action='store_true')

    add_arg('-s', '--skip-patch',
            help='跳过补丁，起始位置偏移到正片位置',
            action='store_true')

    add_arg('-m', '--merge-parts',
            help='合并分段，把页面的分段视频为同一个视频',
            action='store_true')

    add_arg = parser.add_argument_group('字幕选项').add_argument

    add_arg('+r', '--play-resolution',
            metavar='WIDTHxHEIGHT',
            help='播放分辨率，默认为 %(default)s',
            type=str,
            default='1920x1080')

    add_arg('+f', '--font-name',
            metavar='NAME',
            help='字体名称，默认为自动选择',
            type=str,
            default=None)

    add_arg('+s', '--font-size',
            metavar='SIZE',
            help='字体大小，默认为 %(default)s 像素',
            type=int,
            default=32)

    add_arg('+l', '--line-count',
            metavar='COUNT',
            help='限制行数，默认为 %(default)s 行',
            type=int,
            default=4)

    add_arg('+a', '--layout-algorithm',
            metavar='NAME',
            help='布局算法，默认为 %(default)s 算法',
            type=str,
            choices=('sync', 'async'),
            default='sync')

    add_arg('+t', '--tune-duration',
            metavar='SECONDS',
            help='微调时长，默认为 %(default)s 秒',
            type=int,
            default=0)

    add_arg('+d', '--drop-offset',
            metavar='SECONDS',
            help='丢弃偏移，默认为 %(default)s 秒',
            type=int,
            default=5)

    add_arg('+b', '--bottom-margin',
            metavar='HEIGHT',
            help='底部边距，默认为 %(default)s 像素',
            type=int,
            default=0)

    add_arg('+c', '--custom-offset',
            metavar='LENGTH',
            help='自定偏移',
            type=str,
            default='0')

    add_arg('+h', '--header-file',
            metavar='FILE',
            help='样式模板，ass 的样式模板文件',
            type=str,
            default=None)

    return parser

argpaser = create_parser()

########NEW FILE########
__FILENAME__ = main
from ..libsite.producer import Producer
from ..libass.studio import Studio
from .argpaser import argpaser


def parseargs():
    namespace = argpaser.parse_args()

    io_keys = ('url', 'output_filename', 'create_playlist')
    danmaku_keys = (
        'assist_params', 'custom_filter', 'disable_bottom_filter',
        'disable_guest_filter', 'disable_video_filter',
        'skip_patch', 'merge_parts'
    )
    subtitle_keys = (
        'play_resolution', 'font_name', 'font_size',
        'line_count', 'layout_algorithm', 'tune_duration',
        'drop_offset', 'bottom_margin', 'custom_offset', 'header_file'
    )

    create_args = lambda keys: {k: getattr(namespace, k) for k in keys}
    io_args = create_args(io_keys)
    danmaku_args = create_args(danmaku_keys)
    subtitle_args = create_args(subtitle_keys)
    return io_args, danmaku_args, subtitle_args


def convert(io_args, danmaku_args, subtitle_args):
    url = io_args['url']
    output_filename = io_args['output_filename']
    create_playlist = io_args['create_playlist']

    producer = Producer(danmaku_args, url)

    print('--------')
    print('下载文件')
    print('--------')
    producer.start_download()
    print()

    print('--------')
    print('视频信息')
    print('--------')
    for i, video in enumerate(producer.videos):
        print('#' + str(i), str(video.uid), video.title)
        print('视频长度({0.play_length}) 正片位置({0.feature_start}) '
              '弹幕数量({1})'
              .format(video, len(video.danmakus)))
    print()

    producer.start_handle()

    print('--------')
    print('过滤情况')
    print('--------')
    print('屏蔽条数：底部({bottom}) + '
          '游客({guest}) + 云屏蔽({video}) + 自定义({custom}) = {}'
          .format(producer.blocked_count, **producer.filter_detail))
    print('通过条数：总共({0.total_count}) - 屏蔽({0.blocked_count}) = '
          '{0.passed_count}'.format(producer))
    print()

    studio = Studio(subtitle_args, producer)
    studio.start_handle()

    print('--------')
    print('输出文件')
    print('--------')
    print('字幕条数：总共({0}) - 丢弃({1.droped_count}) = '
          '{1.keeped_count}'
          .format(len(studio.ass_danmakus), studio))
    print('字幕文件：' + studio.create_ass_file(output_filename))
    if create_playlist:
        print('播放列表：' + studio.create_m3u_file(output_filename))
    print()


def main():
    convert(*parseargs())

########NEW FILE########
__FILENAME__ = danmakuframe
import os
from .tkmodules import tk, ttk, tku


class DanmakuFrame(ttk.LabelFrame):

    def __init__(self, parent):
        ttk.LabelFrame.__init__(self, parent, text='弹幕选项', padding=2)
        self.pack(fill=tk.BOTH)
        self.grid_columnconfigure(1, weight=1)
        self.init_widgets()

    def init_widgets(self):
        self.init_assist_params_widgets()
        self.init_custom_filter_widgets()
        self.init_disable_bottom_filter_widgets()
        self.init_disable_guest_filter_widgets()
        self.init_disable_video_filter_widgets()
        self.init_skip_patch_widgets()
        self.init_merge_parts_widgets()
        tku.add_border_space(self, 1, 1)

    def init_assist_params_widgets(self):
        strvar = tk.StringVar()
        label = ttk.Label(self, text='辅助参数：')
        entry = ttk.Entry(self, textvariable=strvar)

        label.grid(row=0, column=0, sticky=tk.E)
        entry.grid(row=0, column=1, sticky=tk.EW, columnspan=2)

        self.assist_params_strvar = strvar

    def init_custom_filter_widgets(self):
        strvar = tk.StringVar()
        label = ttk.Label(self, text='过滤文件：')
        entry = ttk.Entry(self, textvariable=strvar)
        button = ttk.Button(self, text='浏览', width=6)

        label.grid(row=1, column=0, sticky=tk.E)
        entry.grid(row=1, column=1, sticky=tk.EW)
        button.grid(row=1, column=2, sticky=tk.W)

        button['command'] = self.on_custom_filter_button_clicked
        self.custom_filter_strvar = strvar

    def init_disable_bottom_filter_widgets(self):
        intvar = tk.IntVar()
        checkbutton = ttk.Checkbutton(
            self, text='不要过滤底部弹幕', variable=intvar)

        checkbutton.grid(row=2, column=0, sticky=tk.W, columnspan=3)

        self.disable_bottom_filter_intvar = intvar

    def init_disable_guest_filter_widgets(self):
        intvar = tk.IntVar()
        checkbutton = ttk.Checkbutton(
            self, text='不要过滤游客弹幕', variable=intvar)

        checkbutton.grid(row=3, column=0, sticky=tk.W, columnspan=3)

        self.disable_guest_filter_intvar = intvar

    def init_disable_video_filter_widgets(self):
        intvar = tk.IntVar()
        checkbutton = ttk.Checkbutton(
            self, text='不要过滤云屏蔽弹幕', variable=intvar)

        checkbutton.grid(row=4, column=0, sticky=tk.W, columnspan=3)

        self.disable_video_filter_intvar = intvar

    def init_skip_patch_widgets(self):
        intvar = tk.IntVar()
        checkbutton = ttk.Checkbutton(self, text='跳过补丁', variable=intvar)

        checkbutton.grid(row=5, column=0, sticky=tk.W, columnspan=3)

        self.skip_patch_intvar = intvar

    def init_merge_parts_widgets(self):
        intvar = tk.IntVar()
        checkbutton = ttk.Checkbutton(self, text='合并分段', variable=intvar)

        checkbutton.grid(row=6, column=0, sticky=tk.W, columnspan=3)

        self.merge_parts_intvar = intvar

    def on_custom_filter_button_clicked(self):
        current_path = self.custom_filter_strvar.get().strip()
        if current_path == '':
            foldername, filename = os.getcwd(), ''
        else:
            foldername, filename = os.path.split(current_path)

        selected_path = tk.filedialog.askopenfilename(
            parent=self,
            title='打开文件',
            initialdir=foldername,
            initialfile=filename
        )

        if selected_path is None:
            return

        self.custom_filter_strvar.set(selected_path)

    def values(self):
        return dict(
            assist_params=self.assist_params_strvar.get().strip(),
            custom_filter=self.custom_filter_strvar.get().strip(),
            disable_bottom_filter=self.disable_bottom_filter_intvar.get() == 1,
            disable_guest_filter=self.disable_guest_filter_intvar.get() == 1,
            disable_video_filter=self.disable_video_filter_intvar.get() == 1,
            skip_patch=self.skip_patch_intvar.get() == 1,
            merge_parts=self.merge_parts_intvar.get() == 1,
        )

########NEW FILE########
__FILENAME__ = ioframe
import os
from .tkmodules import tk, ttk, tku


class IoFrame(ttk.LabelFrame):

    def __init__(self, parent):
        ttk.LabelFrame.__init__(self, parent, text='输入输出', padding=2)
        self.pack(fill=tk.BOTH)
        self.grid_columnconfigure(1, weight=1)
        self.init_widgets()

    def init_widgets(self):
        self.init_url_widgets()
        self.init_output_filename_widgets()
        self.init_create_playlist_widgets()
        self.init_convert_widgets()
        tku.add_border_space(self, 1, 1)

    def init_url_widgets(self):
        strvar = tk.StringVar()
        label = ttk.Label(self, text='视频地址：')
        entry = ttk.Entry(self, textvariable=strvar)

        label.grid(row=0, column=0, sticky=tk.E)
        entry.grid(row=0, column=1, sticky=tk.EW, columnspan=2)

        self.url_strvar = strvar

    def init_output_filename_widgets(self):
        strvar = tk.StringVar()
        label = ttk.Label(self, text='输出文件：')
        entry = ttk.Entry(self, textvariable=strvar)
        button = ttk.Button(self, text='浏览', width=6)

        label.grid(row=1, column=0, sticky=tk.E)
        entry.grid(row=1, column=1, sticky=tk.EW)
        button.grid(row=1, column=2, sticky=tk.W)

        strvar.set(os.getcwd())
        button['command'] = self.on_output_filename_button_clicked
        self.output_filename_strvar = strvar

    def init_create_playlist_widgets(self):
        intvar = tk.IntVar()
        checkbutton = ttk.Checkbutton(
            self, text='同时输出播放列表', variable=intvar)
        checkbutton.grid(row=3, column=0, sticky=tk.W, columnspan=3)

        self.create_playlist_intvar = intvar

    def init_convert_widgets(self):
        button = ttk.Button(self, text='转换', width=6)

        button.grid(row=3, column=2, sticky=tk.W)

        button['command'] = self.on_convert_button_clicked
        self.convert_button = button

    def on_output_filename_button_clicked(self):
        current_path = self.output_filename_strvar.get().strip()
        if current_path == '':
            foldername, filename = os.getcwd(), ''
        elif os.path.isdir(current_path):
            foldername, filename = current_path, ''
        else:
            foldername, filename = os.path.split(current_path)

        selected_path = tk.filedialog.asksaveasfilename(
            parent=self,
            title='保存文件',
            initialdir=foldername,
            initialfile=filename
        )

        if selected_path is None:
            return

        if selected_path == '':
            selected_path = os.getcwd()
        self.output_filename_strvar.set(selected_path)

    def on_convert_button_clicked(self):
        self.event_generate('<<ConvertButtonClicked>>')

    def values(self):
        return dict(
            url=self.url_strvar.get().strip(),
            output_filename=self.output_filename_strvar.get().strip(),
            create_playlist=self.create_playlist_intvar.get() == 1,
        )

    def enable_convert_button(self):
        self.convert_button['state'] = tk.NORMAL

    def disable_convert_button(self):
        self.convert_button['state'] = tk.DISABLED

########NEW FILE########
__FILENAME__ = loggingframe
from .tkmodules import tk, ttk, tku


class LoggingFrame(ttk.LabelFrame):

    def __init__(self, parent):
        ttk.LabelFrame.__init__(self, parent, text='运行日志', padding=2)
        self.pack(fill=tk.BOTH, expand=True)
        self.grid_columnconfigure(1, weight=1)
        self.init_widgets()

    def init_widgets(self):
        scrolledtext = ttk.ScrolledText(self, width=64)
        scrolledtext.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        self.scrolledtext = scrolledtext
        tku.add_border_space(self, 1, 1)

    def get(self):
        return self.scrolledtext.get()

    def write(self, string):
        self.scrolledtext.insert('end', string)
        self.scrolledtext.see('end')

########NEW FILE########
__FILENAME__ = main
import sys
import webbrowser
import traceback
from pprint import pprint
from ..fndcli.main import convert
from .tkmodules import tk, ttk, tku
from .menubar import MenuBar
from .ioframe import IoFrame
from .danmakuframe import DanmakuFrame
from .loggingframe import LoggingFrame
from .subtitleframe import SubtitleFrame


class Application(ttk.Frame):

    def __init__(self):
        ttk.Frame.__init__(self, None, border=2)
        self.pack(fill=tk.BOTH, expand=True)
        self.init_widgets()

    def init_widgets(self):
        self.init_topwin()
        self.init_menubar()
        self.init_left_frame()
        self.init_right_frame()
        tku.add_border_space(self, 2, 2)

        # Windows 下有个问题，窗口实例初始化后，出现在默认位置，
        # 如果马上修改窗口位置，窗口还是会在默认位置闪现一下，
        # 因此先隐藏起来，位置更新后再显示出来
        if sys.platform.startswith('win'):
            self.topwin.withdraw()
            tku.move_to_screen_center(self.topwin)
            self.topwin.deiconify()
        else:
            tku.move_to_screen_center(self.topwin)

    def init_topwin(self):
        self.topwin = self.winfo_toplevel()
        self.topwin.title('Niconvert')
        if sys.platform.startswith('win'):
            icon_path = tku.asset_path('logo.ico')
            self.topwin.iconbitmap(default=icon_path)
        else:
            icon_path = tku.asset_path('logo.gif')
            self.topwin.iconphoto(self.topwin, tk.PhotoImage(file=icon_path))
        self.topwin.protocol('WM_DELETE_WINDOW', self.quit)

    def init_menubar(self):
        # XXX Python 3.3 在 Windows XP/7 里都不能收到 bind 过的函数
        # 原因不明，不想给 MenuBar 传入外部依赖 ，暂时用 MonkeyPatch 处理
        if sys.platform.startswith('win'):
            MenuBar.on_quit_menuitem_clicked = \
                lambda s: self.on_quit_menuitem_clicked(None)
            MenuBar.on_help_menuitem_clicked = \
                lambda s: self.on_help_menuitem_clicked(None)
            MenuBar.on_about_menuitem_clicked = \
                lambda s: self.on_about_menuitem_clicked(None)

        events = {
            '<<QuitMenuitemClicked>>': self.on_quit_menuitem_clicked,
            '<<HelpMenuitemClicked>>': self.on_help_menuitem_clicked,
            '<<AboutMenuitemClicked>>': self.on_about_menuitem_clicked,
        }
        menubar = MenuBar(self)
        for name, func in events.items():
            menubar.bind(name, func)

        self.topwin.config(menu=menubar)

    def init_left_frame(self):
        frame = ttk.Frame(self)
        self.io_frame = IoFrame(frame)
        self.danmaku_frame = DanmakuFrame(frame)
        self.subtitle_frame = SubtitleFrame(frame)
        self.io_frame.bind('<<ConvertButtonClicked>>',
                           self.on_convert_button_clicked)
        frame.grid_columnconfigure(1, weight=1)
        frame.pack(side=tk.LEFT, fill=tk.BOTH)

    def init_right_frame(self):
        frame = ttk.Frame(self)
        self.logging_frame = LoggingFrame(frame)
        frame.grid_columnconfigure(1, weight=1)
        frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

    def get_convert_args_list(self):
        io_args = self.io_frame.values()
        danmaku_args = self.danmaku_frame.values()
        subtitle_args = self.subtitle_frame.values()
        if sys.stdout:
            pprint(io_args)
            pprint(danmaku_args)
            pprint(subtitle_args)
        return (io_args, danmaku_args, subtitle_args)

    def on_convert_button_clicked(self, event):
        args_list = self.get_convert_args_list()
        if args_list[0]['url'] == '':
            return

        # TODO 使用线程
        orig_stdout = sys.stdout
        orig_stderr = sys.stderr

        self.io_frame.disable_convert_button()
        sys.stdout = self.logging_frame
        try:
            print('========')
            print('开始转换')
            print('========')
            print()
            convert(*args_list)
        except:
            print(traceback.format_exc())
        self.io_frame.enable_convert_button()

        sys.stdout = orig_stdout
        sys.stderr = orig_stderr

    def on_quit_menuitem_clicked(self, event):
        self.quit()

    def on_help_menuitem_clicked(self, event):
        webbrowser.open('https://github.com/muzuiget/niconvert/wiki')

    def on_about_menuitem_clicked(self, event):
        webbrowser.open('https://github.com/muzuiget/niconvert#readme')


def main():
    app = Application()
    app.mainloop()

########NEW FILE########
__FILENAME__ = menubar
from .tkmodules import tk


class MenuBar(tk.Menu):

    def __init__(self, parent):
        tk.Menu.__init__(self, parent)
        self.init_widgets()

    def init_widgets(self):
        file_menu = tk.Menu(self, tearoff=0)
        file_menu.add_command(
            label='退出(Q)', underline=3,
            command=self.on_quit_menuitem_clicked)

        help_menu = tk.Menu(self, tearoff=0)
        help_menu.add_command(
            label='帮助(O)', underline=3,
            command=self.on_help_menuitem_clicked)
        help_menu.add_command(
            label='关于(A)', underline=3,
            command=self.on_about_menuitem_clicked)

        self.add_cascade(label='文件(F)', menu=file_menu, underline=3)
        self.add_cascade(label='帮助(H)', menu=help_menu, underline=3)

    def on_quit_menuitem_clicked(self):
        self.event_generate('<<QuitMenuitemClicked>>')

    def on_help_menuitem_clicked(self):
        self.event_generate('<<HelpMenuitemClicked>>')

    def on_about_menuitem_clicked(self):
        self.event_generate('<<AboutMenuitemClicked>>')

########NEW FILE########
__FILENAME__ = subtitleframe
import os
import sys
from .tkmodules import tk, ttk, tku


class SubtitleFrame(ttk.LabelFrame):

    def __init__(self, parent):
        ttk.LabelFrame.__init__(self, parent, text='字幕选项', padding=2)
        self.pack(fill=tk.BOTH)
        self.grid_columnconfigure(1, weight=1)
        self.init_widgets()

    def init_widgets(self):
        self.init_play_resolution_widgets()
        self.init_font_name_widgets()
        self.init_font_size_widgets()
        self.init_line_count_widgets()
        self.init_layout_algorithm_widgets()
        self.init_tune_duration_widgets()
        self.init_drop_offset_widgets()
        self.init_bottom_margin_widgets()
        self.init_custom_offset_widgets()
        self.init_header_file_widgets()
        tku.add_border_space(self, 1, 1)

    def init_play_resolution_widgets(self):
        label = ttk.Label(self, text='分辨率：')
        box = ResolutionBox(self)
        label1 = ttk.Label(self, text='像素')

        label.grid(row=0, column=0, sticky=tk.E)
        box.grid(row=0, column=1, sticky=tk.EW)
        label1.grid(row=0, column=2, sticky=tk.W)

        box.set('1920x1080')
        self.play_resolution_box = box

    def init_font_name_widgets(self):
        fonts = list(tk.font.families(self))
        fonts = list(set(fonts))
        fonts.sort()

        strvar = tk.StringVar()
        label = ttk.Label(self, text='字体名称：')
        combobox = ttk.Combobox(self, textvariable=strvar, values=fonts)

        label.grid(row=1, column=0, sticky=tk.E)
        combobox.grid(row=1, column=1, sticky=tk.EW, columnspan=2)

        if sys.platform == 'linux':
            strvar.set('WenQuanYi Micro Hei')
        else:
            strvar.set('微软雅黑')

        self.font_name_strvar = strvar

    def init_font_size_widgets(self):
        label = ttk.Label(self, text='字体大小：')
        spinbox = tk.Spinbox(self, justify=tk.RIGHT, from_=1, to=100)
        label1 = ttk.Label(self, text='像素')

        label.grid(row=2, column=0, sticky=tk.E)
        spinbox.grid(row=2, column=1, sticky=tk.EW)
        label1.grid(row=2, column=2, sticky=tk.W)

        spinbox.delete(0, tk.END)
        spinbox.insert(0, 32)
        self.font_size_spinbox = spinbox

    def init_line_count_widgets(self):
        label = ttk.Label(self, text='限制行数：')
        spinbox = tk.Spinbox(self, justify=tk.RIGHT, from_=0, to=100)
        label1 = ttk.Label(self, text='行')

        label.grid(row=3, column=0, sticky=tk.E)
        spinbox.grid(row=3, column=1, sticky=tk.EW)
        label1.grid(row=3, column=2, sticky=tk.W)

        spinbox.delete(0, tk.END)
        spinbox.insert(0, 4)
        self.line_count_spinbox = spinbox

    def init_layout_algorithm_widgets(self):
        label = ttk.Label(self, text='布局算法：')
        box = AlgorithmBox(self)

        label.grid(row=4, column=0, sticky=tk.E)
        box.grid(row=4, column=1, sticky=tk.EW, columnspan=2)

        box.set('sync')
        self.layout_algorithm_box = box

    def init_tune_duration_widgets(self):
        label = ttk.Label(self, text='微调时长：')
        spinbox = tk.Spinbox(self, justify=tk.RIGHT, from_=-10, to=100)
        label1 = ttk.Label(self, text='秒')

        label.grid(row=5, column=0, sticky=tk.E)
        spinbox.grid(row=5, column=1, sticky=tk.EW)
        label1.grid(row=5, column=2, sticky=tk.W)

        spinbox.delete(0, tk.END)
        spinbox.insert(0, 0)
        self.tune_duration_spinbox = spinbox

    def init_drop_offset_widgets(self):
        label = ttk.Label(self, text='丢弃偏移：')
        spinbox = tk.Spinbox(self, justify=tk.RIGHT, from_=0, to=100)
        label1 = ttk.Label(self, text='秒')

        label.grid(row=6, column=0, sticky=tk.E)
        spinbox.grid(row=6, column=1, sticky=tk.EW)
        label1.grid(row=6, column=2, sticky=tk.W)

        spinbox.delete(0, tk.END)
        spinbox.insert(0, 5)
        self.drop_offset_spinbox = spinbox

    def init_bottom_margin_widgets(self):
        label = ttk.Label(self, text='底部边距：')
        spinbox = tk.Spinbox(self, justify=tk.RIGHT, from_=0, to=100)
        label1 = ttk.Label(self, text='像素')

        label.grid(row=7, column=0, sticky=tk.E)
        spinbox.grid(row=7, column=1, sticky=tk.EW)
        label1.grid(row=7, column=2, sticky=tk.W)

        spinbox.delete(0, tk.END)
        spinbox.insert(0, 0)
        self.bottom_margin_spinbox = spinbox

    def init_custom_offset_widgets(self):
        strvar = tk.StringVar()
        label = ttk.Label(self, text='自定偏移：')
        entry = ttk.Entry(self, textvariable=strvar, justify=tk.RIGHT)
        label1 = ttk.Label(self, text='秒')

        label.grid(row=8, column=0, sticky=tk.E)
        entry.grid(row=8, column=1, sticky=tk.EW)
        label1.grid(row=8, column=2, sticky=tk.W)

        strvar.set('0')
        self.custom_offset_strvar = strvar

    def init_header_file_widgets(self):
        strvar = tk.StringVar()
        label = ttk.Label(self, text='样式模板：')
        entry = ttk.Entry(self, textvariable=strvar)
        button = ttk.Button(self, text='浏览', width=6)

        label.grid(row=9, column=0, sticky=tk.E)
        entry.grid(row=9, column=1, sticky=tk.EW)
        button.grid(row=9, column=2, sticky=tk.W)

        button['command'] = self.on_header_file_button_clicked
        self.header_file_strvar = strvar

    def on_header_file_button_clicked(self):
        current_path = self.header_file_strvar.get().strip()
        if current_path == '':
            foldername, filename = os.getcwd(), ''
        else:
            foldername, filename = os.path.split(current_path)

        selected_path = tk.filedialog.askopenfilename(
            parent=self,
            title='打开文件',
            initialdir=foldername,
            initialfile=filename
        )

        if selected_path is None:
            return

        self.header_file_strvar.set(selected_path)

    def values(self):
        return dict(
            play_resolution=self.play_resolution_box.get().strip(),
            font_name=self.font_name_strvar.get().strip(),
            font_size=int(self.font_size_spinbox.get()),
            line_count=int(self.line_count_spinbox.get()),
            layout_algorithm=self.layout_algorithm_box.get(),
            tune_duration=int(self.tune_duration_spinbox.get()),
            drop_offset=int(self.drop_offset_spinbox.get()),
            bottom_margin=int(self.bottom_margin_spinbox.get()),
            custom_offset=self.custom_offset_strvar.get().strip(),
            header_file=self.header_file_strvar.get().strip(),
        )


class ResolutionBox(ttk.Frame):

    def __init__(self, parent):
        ttk.Frame.__init__(self, parent)
        self.init_widgets()

    def init_widgets(self):
        width_spinbox = tk.Spinbox(
            self, justify=tk.RIGHT, width=16, from_=1, to=9999)
        label = ttk.Label(self, text='x')
        height_spinbox = tk.Spinbox(
            self, justify=tk.RIGHT, width=16, from_=1, to=9999)

        width_spinbox.pack(side=tk.LEFT, fill=tk.BOTH)
        label.pack(side=tk.LEFT)
        height_spinbox.pack(side=tk.LEFT, fill=tk.BOTH)

        self.width_spinbox = width_spinbox
        self.height_spinbox = height_spinbox

    def get(self):
        width = self.width_spinbox.get()
        height = self.height_spinbox.get()
        return width + 'x' + height

    def set(self, value):
        width, height = value.split('x')
        self.width_spinbox.delete(0, tk.END)
        self.width_spinbox.insert(0, width)
        self.height_spinbox.delete(0, tk.END)
        self.height_spinbox.insert(0, height)


class AlgorithmBox(ttk.Frame):

    def __init__(self, parent):
        ttk.Frame.__init__(self, parent)
        self.init_widgets()

    def init_widgets(self):
        strvar = tk.StringVar()
        sync_radiobutton = ttk.Radiobutton(
            self, text='速度同步', variable=strvar, value='sync')
        async_radiobutton = ttk.Radiobutton(
            self, text='速度异步', variable=strvar, value='async')

        sync_radiobutton.pack(side=tk.LEFT)
        async_radiobutton.pack(side=tk.LEFT)
        self.strvar = strvar

    def get(self):
        return self.strvar.get()

    def set(self, value):
        self.strvar.set(value)

########NEW FILE########
__FILENAME__ = tkmodules
from os.path import join, dirname
import tkinter
import tkinter.ttk
import tkinter.font
import tkinter.filedialog
import tkinter.messagebox
import tkinter.scrolledtext

tk = tkinter
ttk = tkinter.ttk

# MonkeyPatch 来让 ScrolledText 用上 ttk 的组件
tk.scrolledtext.Frame = ttk.Frame
tk.scrolledtext.Scrollbar = ttk.Scrollbar
ttk.ScrolledText = tk.scrolledtext.ScrolledText


class tku(object):

    @staticmethod
    def add_border_space(widget, padx, pady, recursive=True):
        ''' 给每个 widget 增加指定像素的距离 '''
        widget.pack_configure(padx=padx, pady=pady)
        if recursive:
            for subwidget in widget.pack_slaves():
                subwidget.pack_configure(padx=padx, pady=pady)
            for subwidget in widget.grid_slaves():
                subwidget.grid_configure(padx=padx, pady=pady)

    @staticmethod
    def move_to_screen_center(win):
        ''' 把窗口移动到屏幕中间 '''
        win.update_idletasks()
        screen_width = win.winfo_screenwidth()
        screen_height = win.winfo_screenheight()
        window_size = win.geometry().split('+')[0]
        window_width, window_height = map(int, window_size.split('x'))
        x = (screen_width - window_width) // 2
        y = (screen_height - window_height) // 2
        y -= 40  # 状态栏大约高度
        win.geometry('{:d}x{:d}+{:d}+{:d}'.format(
                     window_width, window_height, x, y))

    @staticmethod
    def asset_path(name):
        return join(dirname(dirname(__file__)), 'assets', name)

########NEW FILE########
__FILENAME__ = collision
from ..libcore.utils import intceil


class Collision(object):
    ''' 碰撞处理 '''

    def __init__(self, line_count):
        self.line_count = line_count
        self.leaves = self._leaves()

    def _leaves(self):
        return [0] * self.line_count

    def detect(self, display):
        ''' 碰撞检测

        返回行号和时间偏移
        '''
        beyonds = []
        for i, leave in enumerate(self.leaves):
            beyond = display.danmaku.start - leave
            # 某一行有足够空间，直接返回行号和 0 偏移
            if beyond >= 0:
                return i, 0
            beyonds.append(beyond)

        # 所有行都没有空间了，那么找出哪一行能在最短时间内让出空间
        min_beyond = min(beyonds)
        line_index = beyonds.index(min_beyond)
        offset = -min_beyond
        return line_index, offset

    def update(self, leave, line_index, offset):
        ''' 更新碰撞信息 '''
        # 还是未能精确和播放器同步，算上 1 秒误差，让字幕稀疏一点
        deviation = 1
        self.leaves[line_index] = intceil(leave + offset) + deviation

########NEW FILE########
__FILENAME__ = config
import os
import sys
from ..libcore.utils import xhms2s


class Config(object):
    ''' 本模块的配置对象 '''

    def __init__(self, args):
        self.args = args

        (self.screen_width,
         self.screen_height) = self._screen_size()
        self.font_name = self._font_name()
        self.base_font_size = self._base_font_size()
        self.line_count = self._line_count()
        self.layout_algorithm = self._layout_algorithm()
        self.tune_duration = self._tune_duration()
        self.drop_offset = self._drop_offset()
        self.bottom_margin = self._bottom_margin()
        self.custom_offset = self._custom_offset()
        self.header_template = self._header_template()

    def _screen_size(self):
        return map(int, self.args['play_resolution'].split('x'))

    def _font_name(self):
        if self.args['font_name']:
            return self.args['font_name']

        if sys.platform.startswith('win'):
            return '微软雅黑'
        else:
            return 'WenQuanYi Micro Hei'

    def _base_font_size(self):
        return self.args['font_size']

    def _line_count(self):
        if self.args['line_count'] == 0:
            return self.screen_height // self.base_font_size
        else:
            return self.args['line_count']

    def _layout_algorithm(self):
        return self.args['layout_algorithm']

    def _tune_duration(self):
        return self.args['tune_duration']

    def _drop_offset(self):
        return self.args['drop_offset']

    def _bottom_margin(self):
        return self.args['bottom_margin']

    def _custom_offset(self):
        return xhms2s(self.args['custom_offset'])

    def _header_template(self):
        if not self.args['header_file']:
            if sys.platform.startswith('win'):
                tpl_file = '/header-win.txt'
            else:
                tpl_file = '/header-unix.txt'
            filename = (os.path.dirname(__file__) + tpl_file)
        else:
            filename = self.args['header_file']
        with open(filename) as file:
            lines = file.read().strip().split('\n')
            lines = map(lambda l: l.strip(), lines)
            header = '\n'.join(lines) + '\n'
        return header

########NEW FILE########
__FILENAME__ = creater
from ..libcore.const import NOT_SUPPORT, SCROLL, TOP, BOTTOM
from .display import display_factory
from .collision import Collision
from .subtitle import Subtitle


class Creater(object):
    ''' 创建器 '''

    def __init__(self, config, danmakus):
        self.config = config
        self.danmakus = danmakus
        self.subtitles = self._subtitles()
        self.text = self._text()

    def _subtitles(self):
        collisions = {
            SCROLL: Collision(self.config.line_count),
            TOP: Collision(self.config.line_count),
            BOTTOM: Collision(self.config.line_count),
        }

        subtitles = []
        for i, danmaku in enumerate(self.danmakus):

            # 丢弃不支持的
            if danmaku.style == NOT_SUPPORT:
                continue

            # 创建显示方式对象
            display = display_factory(self.config, danmaku)
            collision = collisions[danmaku.style]
            line_index, waiting_offset = collision.detect(display)

            # 超过容忍的偏移量，丢弃掉此条弹幕
            if waiting_offset > self.config.drop_offset:
                continue

            # 接受偏移，更新碰撞信息
            display.relayout(line_index)
            collision.update(display.leave, line_index, waiting_offset)

            # 再加上自定义偏移
            offset = waiting_offset + self.config.custom_offset
            subtitle = Subtitle(danmaku, display, offset)

            subtitles.append(subtitle)
        return subtitles

    def _text(self):
        header = self.config.header_template.format(
            width=self.config.screen_width,
            height=self.config.screen_height,
            fontname=self.config.font_name,
            fontsize=self.config.base_font_size,
        )
        events = (subtitle.text for subtitle in self.subtitles)
        text = header + '\n'.join(events)
        return text

########NEW FILE########
__FILENAME__ = display
from ..libcore.const import SCROLL, TOP, BOTTOM
from ..libcore.utils import intceil, display_length


class Display(object):
    ''' 显示方式 '''

    def __init__(self, config, danmaku):
        self.config = config
        self.danmaku = danmaku
        self.line_index = 0

        self.font_size = self._font_size()
        self.is_scaled = self._is_scaled()
        self.max_length = self._max_length()
        self.width = self._width()
        self.height = self._height()

        self.horizontal = self._horizontal()
        self.vertical = self._vertical()

        self.duration = self._duration()
        self.leave = self._leave()

    def _font_size(self):
        ''' 字体大小 '''
        # 按用户自定义的字体大小来缩放
        return intceil(self.config.base_font_size * self.danmaku.size_ratio)

    def _is_scaled(self):
        ''' 字体是否被缩放过 '''
        return self.danmaku.size_ratio != 1

    def _max_length(self):
        ''' 最长的行字符数 '''
        return max(map(display_length, self.danmaku.content.split('\n')))

    def _width(self):
        ''' 整条字幕宽度 '''
        char_count = self.max_length / 2
        return intceil(self.font_size * char_count)

    def _height(self):
        ''' 整条字幕高度 '''
        line_count = len(self.danmaku.content.split('\n'))
        return line_count * self.font_size

    def _horizontal(self):
        ''' 出现和消失的水平坐标位置 '''
        # 默认在屏幕中间
        x = self.config.screen_width // 2
        x1, x2 = x, x
        return x1, x2

    def _vertical(self):
        ''' 出现和消失的垂直坐标位置 '''
        # 默认在屏幕中间
        y = self.config.screen_height // 2
        y1, y2 = y, y
        return y1, y2

    def _duration(self):
        ''' 整条字幕的显示时间 '''

        base = 3 + self.config.tune_duration
        if base <= 0:
            base = 0
        char_count = self.max_length / 2

        if char_count < 6:
            value = base + 1
        elif char_count < 12:
            value = base + 2
        else:
            value = base + 3

        return value

    def _leave(self):
        ''' 离开碰撞时间 '''
        return self.danmaku.start + self.duration

    def relayout(self, line_index):
        ''' 按照新的行号重新布局 '''
        self.line_index = line_index
        self.horizontal = self._horizontal()
        self.vertical = self._vertical()


class TopDisplay(Display):
    ''' 顶部 '''

    def _vertical(self):
        # 这里 y 坐标为 0 就是最顶行了
        y = self.line_index * self.config.base_font_size
        y1, y2 = y, y
        return y1, y2


class BottomDisplay(Display):
    ''' 底部 '''

    def _vertical(self):
        # 要让字幕不超出底部，减去高度
        y = self.config.screen_height \
            - (self.line_index * self.config.base_font_size) - self.height

        # 再减去自定义的底部边距
        y -= self.config.bottom_margin
        y1, y2 = y, y
        return y1, y2


class ScrollDisplay(Display):
    ''' 滚动 '''

    def __init__(self, config, danmaku):
        self.config = config
        self.danmaku = danmaku
        self.line_index = 0

        self.font_size = self._font_size()
        self.is_scaled = self._is_scaled()
        self.max_length = self._max_length()
        self.width = self._width()
        self.height = self._height()

        self.horizontal = self._horizontal()
        self.vertical = self._vertical()

        self.distance = self._distance()
        self.speed = self._speed()

        self.duration = self._duration()
        self.leave = self._leave()

    def _horizontal(self):
        # ASS 的水平位置参考点是整条字幕文本的中点
        x1 = self.config.screen_width + self.width // 2
        x2 = -self.width // 2
        return x1, x2

    def _vertical(self):
        base_font_size = self.config.base_font_size

        # 垂直位置，按基准字体大小算每一行的高度
        y = (self.line_index + 1) * base_font_size

        # 个别弹幕可能字体比基准要大，所以最上的一行还要避免挤出顶部屏幕
        # 坐标不能小于字体大小
        if y < self.font_size:
            y = self.font_size

        y1, y2 = y, y
        return y1, y2

    def _distance(self):
        ''' 字幕坐标点的移动距离 '''
        x1, x2 = self.horizontal
        return x1 - x2

    def _speed(self):
        ''' 字幕每个字的移动的速度 '''
        # 基准时间，就是每个字的移动时间
        # 12 秒加上用户自定义的微调
        base = 12 + self.config.tune_duration
        if base <= 0:
            base = 0
        return intceil(self.config.screen_width / base)

    def _sync_duration(self):
        ''' 计算每条弹幕的显示时长，同步方式

        每个弹幕的滚动速度都一样，辨认度好，适合观看剧集类视频。
        '''
        return self.distance / self.speed

    def _async_duration(self):
        ''' 计算每条弹幕的显示时长，异步方式

        每个弹幕的滚动速度都不一样，动态调整，辨认度低，适合观看 MTV 类视频。
        '''

        base = 6 + self.config.tune_duration
        if base <= 0:
            base = 0
        char_count = self.max_length / 2

        if char_count < 6:
            value = base + char_count
        elif char_count < 12:
            value = base + (char_count / 2)
        elif char_count < 24:
            value = base + (char_count / 3)
        else:
            value = base + 10

        return value

    def _duration(self):
        ''' 整条字幕的移动时间 '''
        func_name = '_' + self.config.layout_algorithm + '_duration'
        func = getattr(self, func_name)
        return func()

    def _leave(self):
        ''' 离开碰撞时间 '''

        # 对于滚动样式弹幕来说，就是最后一个字符离开最右边缘的时间
        # 也就是跑过半个字幕宽度的路程
        speed = self.distance / self.duration
        half_width = self.width * 0.5
        duration = half_width / speed
        return self.danmaku.start + duration


def display_factory(config, danmaku):
    ''' 根据弹幕样式自动创建对应的 Display 类 '''
    mapping = {
        SCROLL: ScrollDisplay,
        TOP: TopDisplay,
        BOTTOM: BottomDisplay,
    }
    class_type = mapping[danmaku.style]
    return class_type(config, danmaku)

########NEW FILE########
__FILENAME__ = studio
import sys
from os.path import join, isdir, basename
from .config import Config
from .creater import Creater


class Studio(object):
    ''' 字幕工程类 '''

    def __init__(self, args, producer):
        self.config = Config(args)
        self.producer = producer

    def start_handle(self):
        self.ass_danmakus = self._ass_danmakus()
        self.creater = self._creater()
        self.keeped_count = self._keep_count()
        self.droped_count = self._droped_count()
        self.play_urls = self._play_urls()

    def _ass_danmakus(self):
        ''' 创建输出 ass 的弹幕列表 '''
        return self.producer.keeped_danmakus

    def _creater(self):
        ''' ass 创建器 '''
        return Creater(self.config, self.ass_danmakus)

    def _keep_count(self):
        ''' 保留条数 '''
        return len(self.creater.subtitles)

    def _droped_count(self):
        ''' 丢弃条数 '''
        return len(self.ass_danmakus) - self.keeped_count

    def create_ass_file(self, filename):
        ''' 创建 ass 字幕 '''
        default_filename = self.default_filename('.ass')
        if filename is None:
            filename = default_filename
        elif isdir(filename):
            filename = join(filename, default_filename)
        elif not filename.endswith('.ass'):
            filename += '.ass'

        self.create_file(filename, self.creater.text)
        return basename(filename)

    def _play_urls(self):
        ''' 播放地址 '''
        urls = []
        for video in self.producer.videos:
            urls.extend(video.play_urls)
        return urls

    def create_m3u_file(self, filename):
        ''' 创建 m3u 播放列表 '''
        default_filename = self.default_filename('.m3u')
        if filename is None:
            filename = default_filename
        elif isdir(filename):
            filename = join(filename, default_filename)
        else:
            if filename.endswith('.ass'):
                filename = filename[:-4] + '.m3u'
            else:
                filename += '.m3u'

        if not self.play_urls:
            return ''

        text = '\n'.join(self.play_urls)
        self.create_file(filename, text)
        return basename(filename)

    def default_filename(self, suffix):
        ''' 创建文件全名 '''
        video_title = self.producer.title.replace('/', ' ')
        filename = video_title + suffix
        return filename

    def create_file(self, filename, text):
        with open(filename, 'wb') as file:
            if sys.platform.startswith('win'):
                text = text.replace('\n', '\r\n')
            text = text.encode('utf-8')
            file.write(text)

########NEW FILE########
__FILENAME__ = subtitle
from ..libcore.const import SCROLL
from ..libcore.utils import s2hms, int2bgr, is_dark, correct_typos

DIALOGUE_TPL = '''
Dialogue: {layer},{start},{end},Danmaku,,0000,0000,0000,,{content}
'''.strip()


class Subtitle(object):
    ''' 字幕 '''

    def __init__(self, danmaku, display, offset=0):
        self.danmaku = danmaku
        self.display = display
        self.offset = offset

        self.start = self._start()
        self.end = self._end()
        self.color = self._color()
        self.position = self._position()
        self.start_markup = self._start_markup()
        self.end_markup = self._end_markup()
        self.color_markup = self._color_markup()
        self.border_markup = self._border_markup()
        self.font_size_markup = self._font_size_markup()
        self.style_markup = self._style_markup()
        self.layer_markup = self._layer_markup()
        self.content_markup = self._content_markup()
        self.text = self._text()

    def _start(self):
        return self.danmaku.start + self.offset

    def _end(self):
        return self.start + self.display.duration

    def _color(self):
        return int2bgr(self.danmaku.color)

    def _position(self):
        x1, x2 = self.display.horizontal
        y1, y2 = self.display.vertical
        return dict(x1=x1, y1=y1, x2=x2, y2=y2)

    def _start_markup(self):
        return s2hms(self.start)

    def _end_markup(self):
        return s2hms(self.end)

    def _color_markup(self):
        # 白色不需要加特别标记
        if self.color == 'FFFFFF':
            return ''
        else:
            return '\\c&H' + self.color

    def _border_markup(self):
        # 暗色加个亮色边框，方便阅读
        if is_dark(self.danmaku.color):
            return '\\3c&HFFFFFF'
        else:
            return ''

    def _font_size_markup(self):
        if self.display.is_scaled:
            return '\\fs' + str(self.display.font_size)
        else:
            return ''

    def _style_markup(self):
        if self.danmaku.style == SCROLL:
            return '\\move({x1}, {y1}, {x2}, {y2})'.format(**self.position)
        else:
            return '\\a6\\pos({x1}, {y1})'.format(**self.position)

    def _layer_markup(self):
        if self.danmaku.style != SCROLL:
            return '-2'
        else:
            return '-3'

    def _content_markup(self):
        markup = ''.join([
            self.style_markup,
            self.color_markup,
            self.border_markup,
            self.font_size_markup
        ])
        content = correct_typos(self.danmaku.content)
        return '{' + markup + '}' + content

    def _text(self):
        return DIALOGUE_TPL.format(
            layer=self.layer_markup,
            start=self.start_markup,
            end=self.end_markup,
            content=self.content_markup)

########NEW FILE########
__FILENAME__ = const
# 弹幕样式
STYLES = (
    NOT_SUPPORT,
    SCROLL,
    TOP,
    BOTTOM,
) = range(4)

########NEW FILE########
__FILENAME__ = danmaku
from .const import NOT_SUPPORT


class BaseDanmaku(object):
    ''' 弹幕基类 '''

    def __init__(self):

        # 开始时间
        self.start = 0

        # 位置样式
        self.style = NOT_SUPPORT

        # 颜色
        self.color = 0xFFFFFF

        # 评论者
        self.commenter = ''

        # 评论正文
        self.content = ''

        # 字体缩放比例
        self.size_ratio = 1

        # 是否游客弹幕
        self.is_guest = False

        # 是否歌词或神弹幕
        self.is_applaud = False

########NEW FILE########
__FILENAME__ = fetcher
import gzip
import zlib
from urllib import request
from io import BytesIO


USER_AGENT = \
    'Mozilla/5.0 (X11; Linux x86_64; rv:26.0) Gecko/20100101 Firefox/26.0'


class Fetcher(object):

    def __init__(self):
        self.opener = self._opener()
        self.cache = {}

    def _opener(self):
        opener = request.build_opener()
        opener.addheaders = [
            ('User-Agent', USER_AGENT),
            ('Accept-Encoding', 'gzip')
        ]
        return opener

    def decompression(self, content, encoding):
        if encoding == 'gzip':
            return gzip.GzipFile(fileobj=BytesIO(content), mode='rb').read()
        elif encoding == 'deflate':
            return zlib.decompressobj(-zlib.MAX_WBITS).decompress(content)
        else:
            return content

    def download(self, url):
        resp = self.opener.open(url)
        content = resp.read()
        encoding = resp.headers.get('content-encoding', None)
        return self.decompression(content, encoding).decode('UTF-8')

    def open(self, url, force=False):
        text = self.cache.get(url)
        if force or text is None:
            print('下载：' + str(url))
            text = self.download(url)
            self.cache[url] = text
        else:
            print('重用：' + str(url))
        return text


fetch = Fetcher().open

########NEW FILE########
__FILENAME__ = filter
import re
from .const import BOTTOM


class BaseFilter(object):
    ''' 过滤器基类 '''

    def match(self, danmaku):
        return False


class GuestFilter(BaseFilter):
    ''' 游客过滤器 '''

    def match(self, danmaku):
        return danmaku.is_guest


class BottomFilter(BaseFilter):
    ''' 底部样式过滤器 '''

    def match(self, danmaku):
        if danmaku.is_applaud:
            return False
        return danmaku.style == BOTTOM


class CustomFilter(BaseFilter):
    ''' 自定义过滤器 '''

    def __init__(self, lines):
        self.lines = lines
        self.regexps = self._regexps()

    def _regexps(self):
        return list(map(re.compile, self.lines))

    def match(self, danmaku):
        for regexp in self.regexps:
            if regexp.search(danmaku.content):
                return True
        return False

guest_filter = GuestFilter()
bottom_filter = BottomFilter()

########NEW FILE########
__FILENAME__ = utils
import re
import colorsys
from math import ceil
from urllib.parse import unquote
from unicodedata import east_asian_width


def intceil(number):
    ''' 向上取整 '''
    return int(ceil(number))


def display_length(text):
    ''' 字符长度，1 个汉字当 2 个英文 '''
    width = 0
    for char in text:
        width += east_asian_width(char) == 'Na' and 1 or 2
    return width


def correct_typos(text):
    ''' 修正一些评论者的拼写错误 '''

    # 错误的换行转义
    text = text.replace('/n', '\\N')
    text = text.replace('&gt;', '>')
    text = text.replace('&lt;', '<')

    return text


def s2hms(seconds):
    ''' 秒数转 时:分:秒 格式 '''
    if seconds < 0:
        return '0:00:00.00'

    i, d = divmod(seconds, 1)
    m, s = divmod(i, 60)
    h, m = divmod(m, 60)
    (h, m, s, d) = map(int, (h, m, s, d * 100))
    return '{:d}:{:02d}:{:02d}.{:02d}'.format(h, m, s, d)


def hms2s(hms):
    ''' 时:分:秒 格式转 秒数 '''

    nums = hms.split(':')
    seconds = 0
    for i in range(len(nums)):
        seconds += int(nums[-i - 1]) * (60 ** i)
    return seconds


def xhms2s(xhms):
    ''' 同上，不过可以用 +/- 符号来连接多个

    即 3:00-2:30 相当于 30 秒
    '''

    args = xhms.replace('+', ' +').replace('-', ' -').split(' ')
    result = 0
    for hms in args:
        seconds = hms2s(hms)
        result += seconds
    return result


def int2rgb(integer):
    ''' 颜色值，整型转 RGB '''
    return hex(integer).upper()[2:].zfill(6)


def int2bgr(integer):
    ''' 颜色值，整型转 BGR '''
    rgb = int2rgb(integer)
    bgr = rgb[4:6] + rgb[2:4] + rgb[0:2]
    return bgr


def int2hls(integer):
    ''' 颜色值，整型转 HLS '''
    rgb = int2rgb(integer)
    rgb_decimals = map(lambda x: int(x, 16), (rgb[0:2], rgb[2:4], rgb[4:6]))
    rgb_coordinates = map(lambda x: x // 255, rgb_decimals)
    hls_corrdinates = colorsys.rgb_to_hls(*rgb_coordinates)
    hls = (
        hls_corrdinates[0] * 360,
        hls_corrdinates[1] * 100,
        hls_corrdinates[2] * 100
    )
    return hls


def is_dark(integer):
    ''' 是否属于暗色 '''
    if integer == 0:
        return True

    hls = int2hls(integer)
    hue, lightness = hls[0:2]

    # HSL 色轮见
    # http://zh.wikipedia.org/zh-cn/HSL和HSV色彩空间
    # 以下的数值都是我的主观判断认为是暗色
    if (hue > 30 and hue < 210) and lightness < 33:
        return True
    if (hue < 30 or hue > 210) and lightness < 66:
        return True

    return False


def extract_params(argv):
    ''' 转换网址参数字符串为字典对象 '''
    argv = unquote(argv)
    params = {}
    for arg in argv.split(','):
        key, value = arg.split('=')
        params[key] = value
    return params


def play_url_fix(url):
    ''' 视频地址修复 '''
    # 不知道为毛我不能解析 videoctfs.tc.qq.com 这个域名，即是用电信的 DNS 也是，
    # 但是通过抓包分析，Flash 播放器获取时就变成 IP 了，
    # 似乎是硬编码直接替换过的。
    if url.startswith('http://videoctfs.tc.qq.com/'):
        return url.replace('http://videoctfs.tc.qq.com/',
                           'http://183.60.73.103/', 1)

    # 默认这个会返回 403
    if url.startswith('http://vhot2.qqvideo.tc.qq.com/'):
        key_part = re.findall(
            'http://vhot2.qqvideo.tc.qq.com/(.+?)\?.*', url)[0]
        url = 'http://vsrc.store.qq.com/{}?'.format(key_part)
        url += 'channel=vhot2&sdtfrom=v2&r=256&rfc=v10'
        return url

    return url

########NEW FILE########
__FILENAME__ = video
class BaseVideo(object):
    ''' 视频基类 '''

    def __init__(self):

        # 唯一识别符号
        self.uid = ''

        # 视频标题
        self.h1 = ''
        self.h2 = ''
        self.title = '未知标题'

        # 过滤器
        self.filter = None

        # 视频长度
        self.play_length = 0

        # 视频地址
        self.play_urls = []

        # 弹幕列表
        self.danmakus = []

        # 正片位置
        self.feature_start = 0


########NEW FILE########
__FILENAME__ = acfun
import re
import json
from ..libcore.const import NOT_SUPPORT, SCROLL, TOP, BOTTOM
from ..libcore.utils import extract_params
from ..libcore.fetcher import fetch
from ..libcore.danmaku import BaseDanmaku
from ..libcore.video import BaseVideo


class Danmaku(BaseDanmaku):

    def __init__(self, entry):
        self.entry = entry
        self.raw = self._raw()
        # 父类接口
        self.start = self._start()
        self.style = self._style()
        self.color = self._color()
        self.commenter = self._commenter()
        self.content = self._content()
        self.size_ratio = self._size_ratio()
        self.is_guest = self._is_guest()
        self.is_applaud = self._is_applaud()

    def _raw(self):
        attr_string = self.entry['c']
        content_string = self.entry['m']
        attrs = attr_string.split(',')
        props = {
            'start': float(attrs[0]),
            'color': int(attrs[1]),
            'style': int(attrs[2]),
            'size': int(attrs[3]),
            'commenter': attrs[4],
            'publish': int(attrs[5]),
            'content': content_string
        }
        return props

    # 父类接口 #

    def _start(self):
        return self.raw['start']

    def _style(self):
        MAPPING = {
            1: SCROLL,
            2: NOT_SUPPORT,  # 没搜到明确定义
            3: NOT_SUPPORT,  # 同上
            4: BOTTOM,
            5: TOP,
            6: NOT_SUPPORT,  # 没搜到明确定义
            7: NOT_SUPPORT,  # 高级弹幕，暂时不要考虑
            8: NOT_SUPPORT,  # 没搜到明确定义
        }
        return MAPPING.get(self.raw['style'], NOT_SUPPORT)

    def _color(self):
        return self.raw['color']

    def _commenter(self):
        return self.raw['commenter']

    def _content(self):
        return self.raw['content']

    def _size_ratio(self):
        FLASH_PLAYER_FONT_SIZE = 25
        return self.raw['size'] / FLASH_PLAYER_FONT_SIZE

    def _is_guest(self):
        # 似乎 14 个字符长，还包含英文字母的就是游客
        return len(self.raw['commenter']) == 14

    def _is_applaud(self):
        return False


class Video(BaseVideo):

    def __init__(self, config, meta):
        self.config = config
        self.meta = meta
        self.vid = self._vid()
        self.cid = self._cid()
        #print('信息：' + str(self.meta))
        #print('信息：' + str(dict(vid=self.vid, cid=self.cid)))
        # 父类接口
        self.uid = 'vid:{}+cid:{}'.format(self.vid, self.cid)
        self.h1 = self._h1()
        self.h2 = self._h2()
        self.title = self._title()
        self.filter = self._filter()
        (self.play_length,
         self.play_urls) = self._play_info()
        self.danmakus = self._danmakus()
        self.feature_start = self._feature_start()

    def _vid(self):
        value = self.meta.get('vid')
        if value is not None:
            return value
        raise Exception('无法获取 vid，请用辅助参数指定')

    def _cid(self):
        value = self.meta.get('cid')
        if value is not None:
            return value

        url = 'http://www.acfun.tv/api/getVideoByID.aspx?vid=' + self.vid
        text = fetch(url)
        value = json.loads(text).get('cid')

        # 换另一个 api 地址试试
        if not value:
            url = 'http://www.acfun.tv/video/getVideo.aspx?id=' + self.vid
            text = fetch(url)
            value = json.loads(text).get('danmakuId')

        if value:
            return value

        raise Exception('无法获取 cid，请用辅助参数指定')

    def _h1(self):
        return self.meta.get('h1', '')

    def _h2(self):
        return self.meta.get('h2', '')

    def _title(self):
        if not self.h1:
            return '未知标题'
        if self.h2:
            return self.h1 + ' - ' + self.h2
        else:
            return self.h1

    def _filter(self):
        # 不做了
        return None

    def _play_info(self):
        # 不做了
        return (0, [])

    def _danmakus(self):
        tpl = 'http://comment.acfun.tv/{}.json'
        url = tpl.format(self.cid)
        text = fetch(url)
        orignal_danmakus = map(Danmaku, json.loads(text))
        ordered_danmakus = sorted(orignal_danmakus, key=lambda d: d.start)
        return ordered_danmakus

    def _feature_start(self):
        # 不做了
        return 0


class Page(object):

    def __init__(self, url):
        self.url = url
        self.video_class = Video
        self.params = self._params()

    def _params(self):
        abbr_prefix = 'a://'
        normal_prefix = 'http://www.acfun.tv/v/ac'
        comment_prefix = 'http://comment.acfun.tv/'

        url = self.url
        params = {}

        if url.startswith(abbr_prefix):
            argv = url[len(abbr_prefix):]
            params = extract_params(argv)

        elif url.startswith(normal_prefix):
            if '_' not in url:
                url += '_1'
            params = self.extract_params_from_normal_page(url)

        elif url.startswith(comment_prefix):
            vid = ''
            cid = url[len(comment_prefix):-5]
            params = dict(vid=vid, cid=cid)

        return params

    def extract_params_from_normal_page(self, url):
        aid_reg = re.compile('/ac([0-9]+)')
        vid_reg = re.compile('active" data-vid="(.+?)"')
        h1_reg = re.compile('<h1>(.+?)</h1>')
        text = fetch(url)

        params = {}
        params['aid'] = aid_reg.findall(url)[0]
        params['vid'] = vid_reg.findall(text)[0]
        params['h1'] = h1_reg.findall(text)[0]
        return params

########NEW FILE########
__FILENAME__ = bilibili
import re
import json
from ..libcore.const import NOT_SUPPORT, SCROLL, TOP, BOTTOM
from ..libcore.utils import extract_params, play_url_fix
from ..libcore.fetcher import fetch
from ..libcore.filter import BaseFilter
from ..libcore.danmaku import BaseDanmaku
from ..libcore.video import BaseVideo


class Filter(BaseFilter):

    def __init__(self, text):
        self.text = text
        (self.keywords,
         self.users) = self._rules()

    def _rules(self):
        struct = json.loads(self.text)['up']
        return struct['keyword'], struct['user']

    def match(self, danmaku):
        if danmaku.commenter in self.users:
            return True
        for keyword in self.keywords:
            if keyword in danmaku.content:
                return True
        return False


class Danmaku(BaseDanmaku):

    def __init__(self, text):
        self.text = text
        self.raw = self._raw()
        # 父类接口
        self.start = self._start()
        self.style = self._style()
        self.color = self._color()
        self.commenter = self._commenter()
        self.content = self._content()
        self.size_ratio = self._size_ratio()
        self.is_guest = self._is_guest()
        self.is_applaud = self._is_applaud()

    def _raw(self):
        reg = re.compile('<d p="(.+?)">(.*?)</d>')
        attr_string, content_string = reg.findall(self.text)[0]
        attrs = attr_string.split(',')
        props = {
            'start': float(attrs[0]),
            'style': int(attrs[1]),
            'size': int(attrs[2]),
            'color': int(attrs[3]),
            'publish': int(attrs[4]),
            'pool': int(attrs[5]),  # 弹幕池
            'commenter': attrs[6],
            'uid': attrs[7],  # 此弹幕的唯一识别符
            'content': content_string
        }
        return props

    # 父类接口 #

    def _start(self):
        return self.raw['start']

    def _style(self):
        MAPPING = {
            1: SCROLL,
            2: SCROLL,  # 似乎也是滚动弹幕
            3: SCROLL,  # 同上
            4: BOTTOM,
            5: TOP,
            6: SCROLL,  # 逆向滚动弹幕，还是当滚动处理
            7: NOT_SUPPORT,  # 精准定位，暂时不要考虑
            8: NOT_SUPPORT,  # 高级弹幕，暂时不要考虑
        }
        return MAPPING.get(self.raw['style'], NOT_SUPPORT)

    def _color(self):
        return self.raw['color']

    def _commenter(self):
        return self.raw['commenter']

    def _content(self):
        return self.raw['content']

    def _size_ratio(self):
        FLASH_PLAYER_FONT_SIZE = 25
        return self.raw['size'] / FLASH_PLAYER_FONT_SIZE

    def _is_guest(self):
        # 以 D 开头都是游客评论
        return self.raw['commenter'].startswith('D')

    def _is_applaud(self):
        # 不是 0 就是特殊池
        return self.raw['pool'] != 0


class Video(BaseVideo):

    def __init__(self, config, meta):
        self.config = config
        self.meta = meta
        self.cid = self._cid()
        self.aid = self._aid()
        #print('信息：' + str(self.meta))
        #print('信息：' + str(dict(cid=self.cid, aid=self.aid)))
        # 父类接口
        self.uid = 'cid:' + self.cid
        self.h1 = self._h1()
        self.h2 = self._h2()
        self.title = self._title()
        self.filter = self._filter()
        (self.play_length,
         self.play_urls) = self._play_info()
        self.danmakus = self._danmakus()
        self.feature_start = self._feature_start()

    def _cid(self):
        value = self.meta.get('cid')
        if value is not None:
            return value

        ids = []
        for key, value in self.meta.items():
            if key.endswith('id') and key != 'aid':
                ids.append(value)

        reg = re.compile('<chatid>(.+?)</chatid>')
        for id in ids:
            url = 'http://interface.bilibili.tv/player?id=' + id
            text = fetch(url)
            matches = reg.findall(text)
            if matches:
                return matches[0]

        raise Exception('无法获取 cid，请用辅助参数指定')

    def _aid(self):
        value = self.meta.get('aid')
        if value is not None:
            return value
        url = 'http://interface.bilibili.tv/player?id=cid:' + self.cid
        text = fetch(url)
        reg = re.compile('<aid>(.+?)</aid>')
        matches = reg.findall(text)
        if matches:
            return matches[0]
        else:
            return None

    # 父类接口 #

    def _h1(self):
        return self.meta.get('h1', '')

    def _h2(self):
        return self.meta.get('h2', '')

    def _title(self):
        if not self.h1:
            return '未知标题'
        if self.h2:
            return self.h1 + ' - ' + self.h2
        else:
            return self.h1

    def _filter(self):
        if self.config.disable_video_filter:
            return None
        if not self.aid:
            return None
        tpl = 'http://comment.bilibili.tv/cloud/filter/{}.json'
        url = tpl.format(self.aid)
        text = fetch(url)
        return Filter(text)

    def _play_info(self):
        tpl = 'http://interface.bilibili.tv/playurl?cid={}'
        url = tpl.format(self.cid)
        text = fetch(url)

        # 有时可能获取不了视频元数据，多重试几次
        tried = 0
        while True:
            if '视频隐藏' not in text or tried >= 5:
                break
            text = fetch(url, True)
            tried += 1

        reg = re.compile('<timelength>(.+?)</timelength>')
        matches = reg.findall(text)
        if matches:
            play_length = int(float(matches[0])) // 1000
        else:
            play_length = 0

        reg = re.compile('<url><!\[CDATA\[(.+?)\]\]></url>')
        matches = reg.findall(text)
        if matches:
            play_urls = map(play_url_fix, matches)
        else:
            play_urls = []
        return play_length, play_urls

    def _danmakus(self):
        tpl = 'http://comment.bilibili.tv/{}.xml'
        url = tpl.format(self.cid)
        text = fetch(url)
        reg = re.compile('<d .*</d>')
        matches = reg.findall(text)
        orignal_danmakus = map(Danmaku, matches)
        ordered_danmakus = sorted(orignal_danmakus, key=lambda d: d.start)
        return ordered_danmakus

    def _feature_start(self):
        # 特殊池中，并且是高级弹幕，而且是最前的 10 条弹幕
        reg = re.compile('Player.seek\(([0-9]+?)\);')
        for danmaku in self.danmakus[:10]:
            if not (danmaku.raw['pool'] == 2 and danmaku.raw['style'] == 8):
                continue
            matches = reg.findall(danmaku.content)
            if matches:
                return int(matches[0]) / 1000
        return 0


class Page(object):

    def __init__(self, url):
        self.url = url
        self.video_class = Video
        self.params = self._params()

    def _params(self):
        abbr_prefix = 'b://'
        secure_prefix = 'https://secure.bilibili.tv/secure,'
        normal_prefix = 'http://www.bilibili.tv/video/av'
        normal1_prefix = 'http://bilibili.kankanews.com/video/av'
        comment_prefix = 'http://comment.bilibili.tv/'

        url = self.url
        params = {}

        if url.startswith(abbr_prefix):
            argv = url[len(abbr_prefix):]
            params = extract_params(argv)

        elif url.startswith(secure_prefix):
            argv = url[len(secure_prefix):].replace('&', ',')
            params = extract_params(argv)

        elif url.startswith(normal_prefix) or url.startswith(normal1_prefix):
            if url.endswith('/'):
                url += 'index_1.html'
            params = self.extract_params_from_normal_page(url)

        elif url.startswith(comment_prefix):
            aid = ''
            cid = url[len(comment_prefix):-4]
            params = dict(aid=aid, cid=cid)

        return params

    def extract_params_from_normal_page(self, url):
        aid_reg = re.compile('/av([0-9]+)/')
        cid_reg = re.compile("cid=([0-9]+)|cid:'(.+?)'")
        h1_reg = re.compile('<h2 title="(.+?)">')
        text = fetch(url)

        params = {}
        params['aid'] = aid_reg.findall(url)[0]
        try:
            cid_matches = cid_reg.findall(text)[0]
            params['cid'] = cid_matches[0] or cid_matches[1]
            params['h1'] = h1_reg.findall(text)[0]
        except IndexError:
            print('警告：无法获取 cid，此页面可能需要登录')
        return params


class Part(object):

    def __init__(self, url):
        self.url = url
        self.pages = self._pages()

    def _pages(self):
        text = fetch(self.url)
        reg = re.compile("<option value='(.+?)'(?: selected)?>(.+?)</option>")
        matches = reg.findall(text)
        if not matches:
            raise Exception('此页面没有找到多个分段')

        pages = []
        for link in matches:
            url = self.full_urlify(link[0])
            page = Page(url)
            pages.append(page)
        return pages

    def full_urlify(self, fuzzy_url):
        url = fuzzy_url
        if url.startswith('/'):
            url = 'http://www.bilibili.tv' + url
        if fuzzy_url.endswith('/'):
            url += 'index_1.html'
        return url

########NEW FILE########
__FILENAME__ = config
from ..libcore.filter import CustomFilter


class Config(object):

    def __init__(self, args):
        self.args = args
        self.assist_params = self._assist_params()
        self.custom_filter = self._custom_filter()
        self.disable_bottom_filter = self._disable_bottom_filter()
        self.disable_guest_filter = self._disable_guest_filter()
        self.disable_video_filter = self._disable_video_filter()
        self.skip_patch = self._skip_patch()
        self.merge_parts = self._merge_parts()

    def _assist_params(self):
        if not self.args['assist_params']:
            return {}
        params = {}
        for pair in self.args['assist_params'].split(','):
            key, value = pair.split('=')
            params[key] = value
        return params

    def _custom_filter(self):
        if not self.args['custom_filter']:
            return []
        filename = self.args['custom_filter']
        with open(filename) as file:
            text = file.read().strip() + '\n'
            lines = map(lambda l: l.strip(), text.split('\n'))
            lines = list(filter(lambda l: l != '', lines))
        return CustomFilter(lines)

    def _disable_bottom_filter(self):
        return self.args['disable_bottom_filter']

    def _disable_guest_filter(self):
        return self.args['disable_guest_filter']

    def _disable_video_filter(self):
        return self.args['disable_video_filter']

    def _skip_patch(self):
        return self.args['skip_patch']

    def _merge_parts(self):
        return self.args['merge_parts']

########NEW FILE########
__FILENAME__ = producer
from ..libcore.filter import guest_filter, bottom_filter
from .config import Config
from .bilibili import Page as BilibiliPage, Part as BilibiliPart
from .acfun import Page as AcfunPage
from .tucao import Page as TucaoPage


def make_page(url):
    if url.startswith('b://') or 'bilibili' in url:
        page = BilibiliPage(url)
    elif url.startswith('a://') or 'acfun' in url:
        page = AcfunPage(url)
    elif url.startswith('c://') or 'tucao' in url:
        page = TucaoPage(url)
    if page is None:
        raise Exception('不支持的网址')
    return page


def make_part_pages(url):
    prefixes = ['http://www.bilibili.tv/video/av',
                'http://bilibili.kankanews.com/video/av']
    for prefix in prefixes:
        if url.startswith(prefix):
            return BilibiliPart(url).pages
    raise Exception('此网址不支持自动合并分段')


def make_video(config, page):
    meta = page.params.copy()
    meta.update(config.assist_params)
    return page.video_class(config, meta)


class ProxyDanmaku(object):
    ''' 代理弹幕类

    解决补丁这种蛋疼情况
    '''

    def __init__(self, danmaku, offset):
        self.danmaku = danmaku
        self.offset = offset
        self.start = self._start()

    def _start(self):
        return self.danmaku.start + self.offset

    def __getattr__(self, name):
        return getattr(self.danmaku, name)


class Producer(object):

    def __init__(self, args, bootstrap_url):
        self.config = Config(args)
        self.bootstrap_url = bootstrap_url

        self.title = '未知标题'
        self.pages = []
        self.videos = []

    def start_download(self):
        if self.config.merge_parts:
            self.pages = make_part_pages(self.bootstrap_url)
        else:
            self.pages = [make_page(self.bootstrap_url)]

        self.videos = []
        for page in self.pages:
            video = make_video(self.config, page)
            self.videos.append(video)

        video = self.videos[0]
        if self.config.merge_parts:
            self.title = video.h1
        else:
            self.title = video.title

    def start_handle(self):
        self.init_filter_danmakus()

    def init_filter_danmakus(self):
        keeped_danmakus = []
        filter_detail = dict(
            bottom=0,
            guest=0,
            video=0,
            custom=0
        )

        custom_filter = self.config.custom_filter
        part_offset = 0
        for i, video in enumerate(self.videos):

            # 处理偏移 #
            offset = 0

            # 合并分段
            if self.config.merge_parts:
                if i != 0:
                    prev_video = self.videos[i - 1]
                    part_offset += prev_video.play_length
                    offset = part_offset

            # 跳过补丁
            if self.config.skip_patch:
                offset -= video.feature_start

            # 处理过滤 #

            for danmaku in video.danmakus:

                if not self.config.disable_guest_filter:
                    if guest_filter.match(danmaku):
                        filter_detail['guest'] += 1
                        continue
                if not self.config.disable_bottom_filter:
                    if bottom_filter.match(danmaku):
                        filter_detail['bottom'] += 1
                        continue
                if not self.config.disable_video_filter:
                    if video.filter and video.filter.match(danmaku):
                        filter_detail['video'] += 1
                        continue
                if custom_filter:
                    if custom_filter.match(danmaku):
                        filter_detail['custom'] += 1
                        continue

                # 算上偏移加入保留列表中
                danmaku = ProxyDanmaku(danmaku, offset)
                keeped_danmakus.append(danmaku)

        self.keeped_danmakus = keeped_danmakus
        self.filter_detail = filter_detail
        self.blocked_count = sum(filter_detail.values())
        self.passed_count = len(keeped_danmakus)
        self.total_count = self.blocked_count + self.passed_count

########NEW FILE########
__FILENAME__ = tucao
import re
from ..libcore.const import NOT_SUPPORT, SCROLL, TOP, BOTTOM
from ..libcore.utils import extract_params
from ..libcore.fetcher import fetch
from ..libcore.danmaku import BaseDanmaku
from ..libcore.video import BaseVideo


class Danmaku(BaseDanmaku):

    def __init__(self, text):
        self.text = text
        self.raw = self._raw()
        # 父类接口
        self.start = self._start()
        self.style = self._style()
        self.color = self._color()
        self.commenter = self._commenter()
        self.content = self._content()
        self.size_ratio = self._size_ratio()
        self.is_guest = self._is_guest()
        self.is_applaud = self._is_applaud()

    def _raw(self):
        reg = re.compile("<d p='(.+?)'><!\[CDATA\[(.*?)\]\]></d>")
        attr_string, content_string = reg.findall(self.text)[0]
        attrs = attr_string.split(',')
        props = {
            'start': float(attrs[0]),
            'style': int(attrs[1]),
            'size': int(attrs[2]),
            'color': int(attrs[3]),
            'publish': int(attrs[4]),
            'content': content_string
        }
        return props

    # 父类接口 #

    def _start(self):
        return self.raw['start']

    def _style(self):
        MAPPING = {
            1: SCROLL,
            2: SCROLL,
            3: SCROLL,
            4: BOTTOM,
            5: TOP,
            6: SCROLL,
            7: NOT_SUPPORT,
            8: NOT_SUPPORT,
        }
        return MAPPING.get(self.raw['style'], NOT_SUPPORT)

    def _color(self):
        return self.raw['color']

    def _commenter(self):
        # 没有可以判断的依据
        return 'blank'

    def _content(self):
        return self.raw['content']

    def _size_ratio(self):
        FLASH_PLAYER_FONT_SIZE = 25
        return self.raw['size'] / FLASH_PLAYER_FONT_SIZE

    def _is_guest(self):
        # 没有可以判断的依据
        return False

    def _is_applaud(self):
        return False


class Video(BaseVideo):

    def __init__(self, config, meta):
        self.config = config
        self.meta = meta
        self.aid = self._aid()
        self.pid = self._pid()
        #print('信息：' + str(self.meta))
        #print('信息：' + str(dict(aid=self.aid, pid=self.pid)))
        # 父类接口
        self.uid = 'pid:' + self.pid
        self.h1 = self._h1()
        self.h2 = self._h2()
        self.title = self._title()
        self.filter = self._filter()
        (self.play_length,
         self.play_urls) = self._play_info()
        self.danmakus = self._danmakus()
        self.feature_start = self._feature_start()

    def _aid(self):
        value = self.meta.get('aid')
        if value is not None:
            return value

        raise Exception('无法获取 aid，请用辅助参数指定')

    def _pid(self):
        return '11-' + self.aid + '-1-0'

    # 父类接口 #

    def _h1(self):
        return self.meta.get('h1', '')

    def _h2(self):
        return self.meta.get('h2', '')

    def _title(self):
        if not self.h1:
            return '未知标题'
        if self.h2:
            return self.h1 + ' - ' + self.h2
        else:
            return self.h1

    def _filter(self):
        # 不做了
        return None

    def _play_info(self):
        # 不做了
        return (0, [])

    def _danmakus(self):
        tpl = 'http://www.tucao.cc/index.php?' + \
              'm=mukio&c=index&a=init&playerID={}&r=205'
        url = tpl.format(self.pid)
        text = fetch(url)
        reg = re.compile('<d .*</d>')
        matches = reg.findall(text)
        orignal_danmakus = map(Danmaku, matches)
        ordered_danmakus = sorted(orignal_danmakus, key=lambda d: d.start)
        return ordered_danmakus

    def _feature_start(self):
        # 不做了
        return 0


class Page(object):

    def __init__(self, url):
        self.url = url
        self.video_class = Video
        self.params = self._params()

    def _params(self):
        abbr_prefix = 'c://'
        normal_prefix = 'http://www.tucao.cc/play/'

        url = self.url
        params = {}

        if url.startswith(abbr_prefix):
            argv = url[len(abbr_prefix):]
            params = extract_params(argv)

        elif url.startswith(normal_prefix):
            params = self.extract_params_from_normal_page(url)

        return params

    def extract_params_from_normal_page(self, url):
        aid_reg = re.compile('/play/h([0-9]+)/')
        h1_reg = re.compile("add_favorite\('(.+?)'\);")
        text = fetch(url)

        params = {}
        params['aid'] = aid_reg.findall(url)[0]
        params['h1'] = h1_reg.findall(text)[0]
        return params

########NEW FILE########
