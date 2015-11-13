__FILENAME__ = BackThreads
# -*- coding: utf-8 -*-
#
# author: oldj
# blog: http://oldj.net
# email: oldj.wu@gmail.com
#

import time
import random
import threading
import traceback

class BackThreads(threading.Thread):

    def __init__(self, task_qu, *kw, **kw2):

        super(BackThreads, self).__init__(*kw, **kw2)

        self.task_qu = task_qu
        self.time_to_quit = threading.Event()
        self.time_to_quit.clear()


    def run(self):

        time.sleep(0.5 + random.random())

        while True:
            if self.time_to_quit.isSet():
                break

            if not self.task_qu.empty():
                try:
                    tasks = self.task_qu.get(block=False)
                    if callable(tasks):
                        tasks = [tasks]

                    if type(tasks) in (list, tuple):
                        for task in tasks:
                            if callable(task):
                                task()
                except Exception:
                    print(traceback.format_exc())

            time.sleep(0.1)


    def stop(self):
        self.time_to_quit.set()





########NEW FILE########
__FILENAME__ = common_operations
# -*- coding: utf-8 -*-

u"""
基本操作
"""

import os
import sys
import traceback
import datetime
import wx
import chardet
import urllib
import re
import threading
import httplib
import urlparse


from icons import ICONS, ICONS2, ICONS_ICO


def log(msg):

    print(u"%s > %s" % (datetime.datetime.now().strftime("%H:%M:%S"), msg))


def debugErr():

    err = traceback.format_exc()
    log("ERROR!")
    log("-" * 50)
    log(err)


def GetMondrianData(i=0, fn=None):
    if not fn:
        idx = i if 0 <= i < len(ICONS) else 0
        return ICONS_ICO[idx]
    else:
        return ICONS2[fn]


def GetMondrianBitmap(i=0, fn=None):
    return wx.BitmapFromImage(GetMondrianImage(i, fn))


def GetMondrianImage(i=0, fn=None):
    import cStringIO

    stream = cStringIO.StringIO(GetMondrianData(i, fn))
    return wx.ImageFromStream(stream)


def GetMondrianIcon(i=0, fn=None):
    icon = wx.EmptyIcon()
    icon.CopyFromBitmap(GetMondrianBitmap(i, fn))
    return icon



def encode(s):

#    print("--")
#    print(chardet.detect(s))
    return unicode(s).encode("UTF-8") if s else ""


def decode(s):

    s = s.strip()
    if not s:
        return ""

    cd = {}
    sample = s[:4096]
    if sample:
        try:
            cd = chardet.detect(sample)
        except Exception:
#            print(traceback.format_exc())
            pass
#    log([sample, repr(cd)])

    encoding = cd.get("encoding", "") if cd.get("confidence", 0) > 0.9 else ""

    if encoding and encoding.upper() in ("GB2312", "GBK"):
        encoding = "GB18030"

    if not encoding:
        encoding = "UTF-8"
#    print s, cd, encoding, s.decode(encoding)

    try:
        s = s.decode(encoding)
    except Exception:
        pass

    return s


def checkLatestStableVersion(obj):

    def _f(obj):
        url = "https://github.com/oldj/SwitchHosts/blob/master/README.md"
        ver = None

        try:
            c = urllib.urlopen(url).read()
            v = re.search(r"\bLatest Stable:\s?(?P<version>[\d\.]+)\b", c)
            if v:
                ver = v.group("version")

        except Exception:
            pass

        obj.setLatestStableVersion(ver)

        return ver

    t = threading.Thread(target=_f, args=(obj,))
    t.setDaemon(True)
    t.start()


def httpExists(url):
    host, path = urlparse.urlsplit(url)[1:3]
    found = 0
    try:
        connection = httplib.HTTPConnection(host)  ## Make HTTPConnection Object
        connection.request("HEAD", path)
        responseOb = connection.getresponse()      ## Grab HTTPResponse Object

        if responseOb.status == 200:
            found = 1
        elif responseOb.status == 302:
            found = httpExists(urlparse.urljoin(url, responseOb.getheader('location', '')))
        else:
            print "Status %d %s : %s" % (responseOb.status, responseOb.reason, url)
    except Exception, e:
        print e.__class__, e, url
    return found


def compareVersion(v1, v2):
    u"""比较两个版本的大小
    版本的格式形如：0.1.5.3456

    如果 v1 > v2，则返回 1
    如果 v1 = v2，则返回 0
    如果 v1 < v2，则返回 -1
    """

    a1 = v1.split(".")
    a2 = v2.split(".")

    try:
        a1 = [int(i) for i in a1]
        a2 = [int(i) for i in a2]
    except Exception:
        return 0

    len1 = len(a1)
    len2 = len(a2)
    l = min(len1, len2)
    for i in range(l):
        if a1[i] > a2[i]:
            return 1
        elif a1[i] < a2[i]:
            return -1

    if len1 > len2:
        return 1
    elif len1 < len2:
        return -1
    else:
        return 0


def getLocalEncoding():
    u"""取得本地编码"""

    import locale
    import codecs
#    print locale.getpreferredencoding()

    return "%s" % codecs.lookup(locale.getpreferredencoding()).name


def getSystemType():
    u"""取得系统类型
        win
        linux
        mac
    """

    os_name = os.name

    if os_name == "posix":

        if sys.platform != "darwin":
            # linux 系统
            return "linux"

        else:
            # Mac 系统
            return "mac"

    elif os_name == "nt":
        return "win"

    return "unknow"



########NEW FILE########
__FILENAME__ = Hosts
# -*- coding: utf-8 -*-
#
# author: oldj
# blog: http://oldj.net
# email: oldj.wu@gmail.com
#

import os
import simplejson as json
import urllib
import time
import datetime
import common_operations as co


class Hosts(object):

    flag = "#@SwitchHosts!"
    old_flag = "#@SwitchHost!"

    def __init__(self, path, is_origin=False, title=None, url=None, is_common=False):

        self.path = path
        self.is_origin = is_origin
        self.is_common = is_common
        self.url = url
        self.is_online = True if url else False
        self.is_loading = False
        self.last_fetch_dt = None
        self.last_save_time = None
        self.__title = title
        self.__content = None
        self.tree_item_id = None
        self.taskbar_id = None
        self.icon_idx = 0

        self.getContent()

    @property
    def title(self):

        return self.__title or self.filename or u"未命名"

    @title.setter
    def title(self, value):
        self.__title = value

    def getContentFromUrl(self, progress_dlg):

        co.log("fetch '%s'.." % self.url)

        if co.httpExists(self.url):

            if progress_dlg:
                progress_dlg.Update(10),
            try:
                cnt = []
                up = 10
                url_o = urllib.urlopen(self.url)
                while True:
                    c = url_o.read(1024)
                    if not c:
                        break
                    cnt.append(c)
                    up += 1
                    if up < 60:
                        if progress_dlg:
                            progress_dlg.Update(up),
                cnt = "".join(cnt)
                if progress_dlg:
                    progress_dlg.Update(60),
            except Exception:
                co.debugErr()
                return ""

            self.last_fetch_dt = datetime.datetime.now()

        else:
            cnt = u"### URL无法访问！ ###".encode("utf-8")

        return cnt

    def getContentOnce(self):

        if self.is_online and not self.last_fetch_dt:
            self.getContent(force=True)

    def getContent(self, force=False, progress_dlg=None):

        self.is_loading = True
        c = ""
        if self.is_online:
            if force:
                c = self.getContentFromUrl(progress_dlg)

        elif os.path.isfile(self.path):
            c = open(self.path, "rb").read().strip()

        if c:
            c = self.tryToDecode(c)
            a = c.replace("\r", "").split("\n")
            if a[0].startswith(self.flag):
                # 首行是配置信息
                self.parseConfigs(a[0][len(self.flag):])
                c = "\n".join(a[1:])
            elif a[0].startswith(self.old_flag):
                # 兼容老的格式
                # 首行是配置信息
                self.parseConfigs(a[0][len(self.old_flag):])
                c = "\n".join(a[1:])

        self.content = c
        self.is_loading = False

    def tryToDecode(self, s):

        try:
            return co.decode(s)
        except Exception:
            return u"### 解码错误！###"

    @property
    def content(self):

        c = self.__content or ""
        if c and not c.endswith("\n"):
            # 自动给 hosts 内容最后一行添加一个换行
            c = "%s\n" % c
        return c

    @content.setter
    def content(self, value):
        self.__content = value.replace("\r", "")

    def parseConfigs(self, json_str=None):

        try:
            cfg = json.loads(json_str)
        except Exception:
            co.log(json_str)
            co.debugErr()
            return

        if type(cfg) != dict:
            return

        if self.is_origin:
            pass
        elif cfg.get("title"):
            if not self.title or not self.is_online:
                self.title = cfg["title"]

        if cfg.get("url"):
            if not self.is_online and not self.is_origin:
                self.url = cfg["url"]
                self.is_online = True
#                self.getContent()

        if cfg.get("icon_idx") is not None:
            icon_idx = cfg.get("icon_idx")
            if type(icon_idx) not in (int, long) or \
                icon_idx < 0 or icon_idx > len(co.ICONS):
                icon_idx = 0

            self.icon_idx = icon_idx

    @property
    def filename(self):

        sep = "/" if self.is_online else os.sep
        fn = self.path.split(sep)[-1]

        return fn

    @property
    def full_content(self):

        cnt_for_save = [self.configLine()] + self.content.split("\n")
        return os.linesep.join(cnt_for_save).encode("utf-8")

    def configLine(self):
        u"""生成配置信息的注释行"""

        return "%s %s" % (self.flag, json.dumps({
                                "title": self.title,
                                "url": self.url,
                                "icon_idx": self.icon_idx,
                                }))

    def contentWithCommon(self, common=None):
        u"""返回添加了公共内容的hosts"""

        if not common:
            return self.full_content

        return os.linesep.join([
            self.configLine(),
            common.content,
            "# %s" % ("-" * 50),
            self.content
        ]).encode("utf-8")

    def makeBackupHostsName(self, path):

        return "%s.backup_switchhosts" % path

    def tryToBackupOriginalHosts(self, path, backup_name, sudo_password=None):
        u"""尝试备份原始 hosts"""

        if os.path.isfile(backup_name) or not os.path.isfile(path):
            return

        if sudo_password:
            # 新建备份文件
            cmd = [
                "echo '%s' | sudo -S touch %s" % (sudo_password, backup_name),
                "echo '%s' | sudo -S chmod %s %s" % (sudo_password, 766, backup_name),
            ]
            os.popen(";".join(cmd))

        # 尝试保存
        open(backup_name, "w").write(open(path).read())

    def save(self, path=None, common=None, sudo_password=None):

        from stat import ST_MODE
        # fn_stat = 744

        if self.last_save_time:
            time_delta = time.time() - self.last_save_time
            if time_delta < 0.001:
                pass

        path = path or self.path
        path = path.encode(co.getLocalEncoding())
        fn_stat = None
        backup_name = None

        if os.path.isfile(path):
            fn_stat = oct(os.stat(path)[ST_MODE])[-3:]
            backup_name = self.makeBackupHostsName(path)
            self.tryToBackupOriginalHosts(path, backup_name, sudo_password)

        if sudo_password:
            # 先修改系统hosts文件的权限
            cmd = [
                "echo '%s' | sudo -S chmod %s %s" % (sudo_password, 766, path),
                ]
            os.popen(";".join(cmd))

        try:
            # 写系统hosts
            open(path, "w").write(self.contentWithCommon(common))

        finally:
            if sudo_password and fn_stat and backup_name:
                # 再将系统hosts文件的权限改回来
                cmd = [
                    "echo '%s' | sudo -S chmod %s %s" % (sudo_password, fn_stat, path),
                    "echo '%s' | sudo -S chmod %s %s" % (sudo_password, fn_stat, backup_name),
                ]
                os.popen(";".join(cmd))

        self.last_save_time = time.time()

        return True

    def remove(self):

        if os.path.isfile(self.path):
            os.remove(self.path)

########NEW FILE########
__FILENAME__ = HostsCtrl
# -*- coding: utf-8 -*-
#
# author: oldj
# blog: http://oldj.net
# email: oldj.wu@gmail.com
#

import wx
from wx import stc
#import keyword

if wx.Platform == '__WXMSW__':
    faces = {
        'times': 'Times New Roman',
        'mono': 'Courier New',
        'helv': 'Courier New',
        'other': 'Courier New',
        'size': 10,
        'size2': 10,
        }
elif wx.Platform == '__WXMAC__':
    faces = {
        'times': 'Times New Roman',
        'mono': 'Monaco',
        'helv': 'Monaco',
        'other': 'Monaco',
        'size': 12,
        'size2': 12,
        }
else:
    faces = {
        'times': 'Times',
        'mono': 'Courier New',
        'helv': 'Helvetica',
        'other': 'Courier New',
        'size': 12,
        'size2': 12,
        }


class HostsCtrl(stc.StyledTextCtrl):

    def __init__(self, parent, id=wx.ID_ANY, pos=wx.DefaultPosition,
                 size=wx.DefaultSize, style=0):

        stc.StyledTextCtrl.__init__(self, parent, id, pos, size, style)

        self.SetReadOnly(False)
        self.SetLexer(stc.STC_LEX_CONF)
#        self.SetKeyWords(0, " ".join(keyword.kwlist))

#        self.SetProperty("fold", "1")
#        self.SetProperty("tab.timmy.whinge.level", "1")

        self.SetViewWhiteSpace(False)
        self.SetEdgeColumn(80)
        self.SetMarginWidth(0, 0)
        self.SetMarginWidth(1, 5)
        self.SetMarginWidth(2, 5)
        self.SetScrollWidth(800)

        # Global default styles for all languages
        self.StyleSetSpec(stc.STC_STYLE_DEFAULT, "face:%(helv)s,size:%(size)d" % faces)
        self.StyleClearAll()  # Reset all to be like the default

        # Global default styles for all languages
        self.StyleSetSpec(stc.STC_STYLE_DEFAULT, "face:%(helv)s,size:%(size)d" % faces)
        self.StyleSetSpec(stc.STC_STYLE_CONTROLCHAR, "face:%(other)s" % faces)
        self.StyleSetSpec(stc.STC_STYLE_BRACELIGHT, "fore:#FFFFFF,back:#0000FF,bold")
        self.StyleSetSpec(stc.STC_STYLE_BRACEBAD, "fore:#000000,back:#FF0000,bold")

        # Default
        self.StyleSetSpec(stc.STC_P_DEFAULT, "fore:#000000,face:%(helv)s,size:%(size)d" % faces)
        # Comments
        self.StyleSetSpec(stc.STC_P_COMMENTLINE, "fore:#007F00,face:%(other)s,size:%(size)d" % faces)
        # Number
        self.StyleSetSpec(stc.STC_P_NUMBER, "fore:#007F7F,size:%(size)d" % faces)
        # String
        self.StyleSetSpec(stc.STC_P_STRING, "fore:#00007F,face:%(helv)s,size:%(size)d" % faces)
        # Single quoted string
        self.StyleSetSpec(stc.STC_P_CHARACTER, "fore:#7F007F,face:%(helv)s,size:%(size)d" % faces)
        # Keyword
#        self.StyleSetSpec(stc.STC_P_WORD, "fore:#00007F,bold,size:%(size)d" % faces)
        # Triple quotes
#        self.StyleSetSpec(stc.STC_P_TRIPLE, "fore:#7F0000,size:%(size)d" % faces)
        # Triple double quotes
#        self.StyleSetSpec(stc.STC_P_TRIPLEDOUBLE, "fore:#7F0000,size:%(size)d" % faces)
        # Class name definition
        self.StyleSetSpec(stc.STC_P_CLASSNAME, "fore:#0000FF,bold,underline,size:%(size)d" % faces)
        # Function or method name definition
#        self.StyleSetSpec(stc.STC_P_DEFNAME, "fore:#007F7F,bold,size:%(size)d" % faces)
        # Operators
#        self.StyleSetSpec(stc.STC_P_OPERATOR, "bold,size:%(size)d" % faces)
        # Identifiers
#        self.StyleSetSpec(stc.STC_P_IDENTIFIER, "fore:#000000,face:%(helv)s,size:%(size)d" % faces)
        # Comment-blocks
        self.StyleSetSpec(stc.STC_P_COMMENTBLOCK, "fore:#7F7F7F,size:%(size)d" % faces)
        # End of line where string is not closed
        self.StyleSetSpec(stc.STC_P_STRINGEOL, "fore:#000000,face:%(mono)s,back:#E0C0E0,eol,size:%(size)d" % faces)

        self.SetCaretForeground("BLUE")


    def SetValue(self, value):
    #        if wx.USE_UNICODE:
    #            value = value.decode('utf-8')

    #        self.SetReadOnly(False)
        self.SetText(value)

        #        self.SetReadOnly(True)


########NEW FILE########
__FILENAME__ = icons
# -*- coding: utf-8 -*-

ICONS = [
    '\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x10\x00\x00\x00\x10\x08\x02\x00\x00\x00\x90\x91h6\x00\x00\x00\x19tEXtSoftware\x00Adobe ImageReadyq\xc9e<\x00\x00\x01BIDATx\xda\x94R;n\x02A\x0c\xb5w\x06\x90\x16\xa4\xa4CJ\x91S\xa4\xe0(\xd4\xa4\x8ar\x01\xeeA\x94\x88:w\x88r\x10\xd2\xa6\xa4D\xbb\r\xbb\xcbx\xc6\x19{1\x10)\x05\x19\xb9\xf0g\x9e\x9f\x7f\xc8\xcc\xf0\x9f\x87/O\xd7~}~\x95\xd4>%x\\_\x05\xd8\xbfa\xc9\xecc\x02R\x9bU\x84T\xe5O\xcfv\xbb-(B\x00\x91\x03\xc0d\xb3\xb9e\x0e\xd3\xe9\xc9\x93\xcd,\x078\xfe\x91\x92(A\x87\x82\x8f\x00T\xd7\x1e\xa0!r\xea\xc9\xcc\xa9\xae\xb3\xd2 z+\xcc\x13A\xa7\x1a)&\xbfl:U\x82\x95\xd4\x02\x0cT\x19e@\x88b\xf7\xe1\xa4JUU^\x8b\x16O\x08\xe8}c\xb9\x04@\x068\x18\xe0\x81\xe8r8a\xb7k,t#\x0c$%\xf6\x95\xf4i\xbeW+?\x1eKWm{\xbfX\x00\xe2\x1e1\x9d{0\x86\xce\xd2|-\x97\x83V|\x1d\xf3\xdd|^8\xd7\\\x10\x9e\x01\xad1\xa4\xb2\xcc\xb93)!\xa2s\xac!\xbc\x04t\xd6t1\x1c\xca\xb8\x9c\x8b\xd6\xb4\x1b\x8d\x8e\xa1\x13 \xda\x1er=\x1f\xb3\x19\xeb\x04\x9dm\xe6}2\xc9\xca\x00\xb13@\xb1\xfe\xe4~\x8bQ\xd38E\x06\x9b\xb2\xfb\xed\x913\xe9\xcf;\x1f\xc9\x957\xfb#\xc0\x00\x82\xf4\xa4-,\x9a\x06\xe0\x00\x00\x00\x00IEND\xaeB`\x82'
    ,
    '\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x10\x00\x00\x00\x10\x08\x02\x00\x00\x00\x90\x91h6\x00\x00\x00\x19tEXtSoftware\x00Adobe ImageReadyq\xc9e<\x00\x00\x01oIDATx\xda\x94R;N\x031\x10\x1d\x7f6\x10@\x88\x02\t\t\x89S *\x1a\xc4\x05\xd2\xa6\x06\x1aDC\xc71(@H\\\x008\x01\xcaA\x10-]\xe8P"\x85\xd8^\xffx\xe3\xdd\r\x08\x9a0\xb2\xe4\xf1\xf3\xbc\x997\xf6\x88\x9c3\xfd\xc7\xc4\xed\xf9\xb2\xa1\x17w\x9cZ\xa7D\xa7GK\x11\xe6Obm\x98uL\x14\x02\x9fs\xa2\xec\xb1\x91\xa8H\xa8\x82\xc4\x82\xd072\x1e\x8fe\x88\xe4\x1d\xafzF\x1b\x83\x97\xad\xb3\xec\xc3\x8e\xb7-\x82#\x16\x9c&\x86%\x85Du\xf1\xa2\xa1\xf09\xd5\xdbdg^i\xa4\xa50\xa7d\xa7\xb8\xb2s\xd2\xa2\x15\xa6\xa1\xc7Y\xf6\x82%\xf4\x03s\x8eT`\x02\xea4Oh-UER\x0f\x04\x1f\xc9\x1a>xC\xb1\x10&\xef\x13\xbd\x8ax&\xa4\xe0\x85\xd2\x06W\xb2#\xa0\x07T\x84\xd5\xa6\xad\xb0\x7f\x1d\x7f>\x8e\x9f}\x18h+\x926\xb9Bh+\xd4]\x85\xb7\xe7\x9b\xaa\xbf\xce"\x9d\xdd;>\x818T\xc8r\xd1C\'\xc9u\x15^\x1f\xaf*m\x84`|\xf7p(\xa4\xe2\x80\xbf\x04\xdb\x11\x92\xec\xc7\xc4\x04\xfe\x1f\xa9\xd0\xb6\xf9EpM\xd35I\xddc%IEG \x00Q\xd5J{\xb5 \xc4\xee\x1f\x90~ty\x80|\x95&\xd5\xfct\xa6\x87A\x9f\x1f\xa7jc`\xf2~\x94\x91\x00+\x06\x92\x82\x94\xa0\x14i\x81\xa8\x82\xc0i\x10\x1e\x93f\xbc1$K\xce\xec\x97\x00\x03\x00v\x00\xe3n\xbf .\x97\x00\x00\x00\x00IEND\xaeB`\x82'
    ,
    '\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x10\x00\x00\x00\x10\x08\x02\x00\x00\x00\x90\x91h6\x00\x00\x00\x19tEXtSoftware\x00Adobe ImageReadyq\xc9e<\x00\x00\x01`IDATx\xda\x94R;N\x03A\x0c\xb5g&A\t\x05\x05\x12\xd4 \xa44\xb4\x1c\x83\x9e\x1a*D\x8b\xc4A@ \xee\xc0\x01\xe8\xb8@\xca\x9444\xa1\x8bH\x01\xbb;\x1f\x0f\xcf\xbb;\xb0t\xc1\x1aifl?\xfb\xf9\xc39g\xfa\x8f\xf0\xdd\xe5\xa6\xaeW\xf7\x1a\xda\x89\xd0\xc5\xf5F\x80\xafW\x9e\x1ee\x97\x84Rj\x15\x99r"\x10dKlZ\x85\xa8Fi\x14\xcdr\xb941Q\nzBM\xd3\x83\xc5\xceq\x96\xb8\xdfibM\xf8\xe2\xe0\xd1i\x94R\x14\x8a\xed+y\xa8\xd6\x8e\xc8W\xc1\xe0bJ\rI\\\xc3\x14\x1a\xb2\x85\x98\x8b\x91\x82\xef\x01\xe0\x00\xf1\x81\xac( 6\xcaS5\r9.\x80\x904\x00\x04fi\x01\x9f\xab\x0f7\xeeC\x88\x046\x0e\x80\xdc\x02\x9cfH\x1a`\x08\x98\x9d\xa6asb\xb3\xf2\xf5\x00\x10b\x9f\x01Ew\x94\xde\x17\xb7n\xbc\xad\x19b\xbd7;\x079\x8dh~j(\x19|\xc9\xf06\xbfq\xe3\x8a\x19\xd5\xd3\xee\xe1\x19\xb3m\xea\xbf\x80>C\xd3g\xc8<\xa1\\\xa1Z\xe0\xe1\xdd\x99\x8c\x1d\x02\xda.\xa1\xb9l\xb5X\x11\xeb=\\\t\r4vKMx\xf8\x02He\x0e\x089\x7f:\xc1eGdK\xbc\x97\x87\x89:\x8dz\x1f\x88y|\xce\xdd\x14\xb1\x05\xd6\xb4\xae\xd2\xcf\x15\x0c\xf1\xc5\xc9\xf2;i\xee\xd6\x1bK\xb2\xe1\xce~\x0b0\x00/\x90\xde\r\xb1\x84\xfc\xbb\x00\x00\x00\x00IEND\xaeB`\x82'
    ,
    '\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x10\x00\x00\x00\x10\x08\x02\x00\x00\x00\x90\x91h6\x00\x00\x00\x19tEXtSoftware\x00Adobe ImageReadyq\xc9e<\x00\x00\x01yIDATx\xda\x94R\xbdJ\x03A\x10\x9e\xfd\xb9\x0b\x18\xd4g\x10\x14K{\xcd\x13h\x9b\xd6\xc2R\xac|\x01_B\t\xb1\x13\xc1\'\xd0\xc2\x07\xb0\xb2S\x10\x11\xfb\x80\xa0\xa8\xb1\xf0\xb2\xbb\xb3\xe3\xb7\xb7w\xe1\xca\x18\x960\xfb\xdd|\xf3}\xb33JD\xe8??uv\xb8h\xea\xd1(\x95\xb61\xd2\xf8xg\x11\xc2\xe8e\xf0\xb4yg9\x92p\xba\x8bDf\x86Cc\xac\xd6\x1aH\x8c@\x02\x8292\x99Lt`\xe2\xfa8\xc7\xd7\xebW\xaf[\xf7+q\x19D \xde\x05\\q\x10\xe4\x9cd)Db\x9f"vq\xea\xa6\xb4D\xd5\xafc\x8b\xee(\xcc\xe24\xfc\xe0\x13\x02\xd5\x1a\xb3!\x10\x87\xd4\r\xfe\xf3\x83\xc1\x05\x93\x80\xc0^(#^\xb4i\x1e\xd3z\xa6\xe0\xa8.\x03\xd7)x\xff\xfePE\x92`\xe7|\x0cV\x1bv\xa4\xf4\\\x81\x1bK\xd1SVx\xdb}\xec>\xce\xa7\xfbB\x822-\xc1\x87F\x01e\xb2\xc2\xf8\xf9\xb2_\xf6\x11T\xbe\xda\xdf\x18*Q\x0c\xf1\xaeB\xc8\n\xaeQ8y8uej2V\xb3\xe1\xda\x9eQ\x06\tb\xbb\x04\xd7\x10\xb2B\xa9\xfa\x95\xc0\xb5\xc2\x184\x19T\x81\x82\x98n\x0f\xa1\x1e\\\xd4\x85\xe9\xa5m\xa1\x82QC%\xa4g\xcbz\x82ZBK\xe0v\x0e(\xb2}s\x00[\xe9\x89L\xb6lW/\x06\xa9\x04\x10\xdf\x10\xf4\xf9-V\x82\xd2\x11-\xb6\x90\xa2\x8c\xa4\x1b\x844\xae]$\x91\xf3\xb4\xb0$\x0b\xee\xec\x9f\x00\x03\x00\x0e\x92\xf8X\x0b\x11D3\x00\x00\x00\x00IEND\xaeB`\x82'
    ,
    '\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x10\x00\x00\x00\x10\x08\x02\x00\x00\x00\x90\x91h6\x00\x00\x00\x19tEXtSoftware\x00Adobe ImageReadyq\xc9e<\x00\x00\x01xIDATx\xda\x94R;N\x031\x10}c{\t\n\x91\xa0C\xa2\xe0\x12P\xc0\x01\xe8r\x80\xd4t\x88\x88\x9a\x82\x03\xd0\x83\x90\xa8\xb9\x02 J\x0e\x01-e$\x1a\x94\x14\xec\xda\xeb\x1f3\xdeE\x89D\x13V\x96<~\xfb\xde\xbc\xf1\x8c)\xe7\x8c\xff|t{\xb6.\xf5\xfcNR\x9b\x94p1\xfe^G0}\xac\xf3xhb\x02B\x10 e\xf8\x0c\xceR\x114\t\x12\x0b\x82%2\x9b\xcdT\x88\x80\xf7\xb2\x9a\xf6\xedd\x94\';\xbb\xd1\xa3-H\xdd\xf2\x91\x17\x07=\x87K\n\t\xe4\x9d\xa4qq\xd1\x04A\xea\x86*\r\xce\xe8\xc2\xc2%\xb9\xa8k\xa0MW\x98\x91r\\\x11\xd8\x80\x1c%`}*\x02\xeb\xd1\xf5\xd0Z\xe8\xaa\xf0\x07\xc63\xc7\xd9\xe2\xe0\x91$\xdf\xfcs\x8eM\xceG,\xf01\x19E`\x07\x13{AX\n\xdaN\x10\xae\x0eW\x9b\xf3U\xfb"H\xe5\xb4m|\x00\xd9\xa6\xf8r%\x92\xe6\xe6\xf5cK\x1c`\xdbxz\xbc\xcf\xa5\x91\xad\xa1\xd3\xef\x1d\x96\x0e\x0eY\xd0\xcb\xa7w[U\\Q\xae\xdd\xe4`O+U\x1c\xf0W`;\x87\xa1J\x16\x1c\x10\xe5\xa0\x89\xe4\xde\xfc\xcb\xd0\x8a\xa0-]\n~\xc3(\xde5\x02\xda\xc8|D?\xe0\xfe\xca\x04y2\xaa\x17\xf0\xa4\xa9\x13\xe4tt\xfd\xcc\x1b\xaa\x8at\xe1\xe58\x9a>\xc8\x1c\xb8\xc2\x8e\x03\xa8\xfb\x97\xdcO1Fh\x05\xa6r\xaf:\x84\x03>\xae",\xee\x9e7?\x925\xdf\xec\x8f\x00\x03\x00\xca\xf2\xe6L,ZXW\x00\x00\x00\x00IEND\xaeB`\x82'
    ,
    '\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x10\x00\x00\x00\x10\x08\x02\x00\x00\x00\x90\x91h6\x00\x00\x00\x19tEXtSoftware\x00Adobe ImageReadyq\xc9e<\x00\x00\x01\x7fIDATx\xda\x94RM.\x84A\x10\xad\xea\x9f\x19\xf1\x13\xb6,\\\xc1FD\xe2\x16b\x87\x03\x08q\x05{k\x11b9\'\xb0\x117\xb0&\x91XY\x8e\x85\x04#\xcc\xf7\xd3U\xd5\xaa\xbbg\x10\xab\xd1\xe9E\xf5K\xbfW\xaf^7\xc6\x18\xe1?\x0bO\xf6&\xbd\xba\x7f\x9a\xa4\x9d\x08\x1c\xde|NB8X\x19\xc6\xdbi\xc7\x02V(\x01\xea\x8d#\xa8\x8aE0\x98\x10\xc9\x08\xfc \xfd~\xdf\x10\x83\xe5\xa0\xdb\xb4\xed\xdd\xe5,=,,\xce\x85oD\x8f\xba\xb5(H\xb2D\x02\x9e\x9b$G<\x18P2YW\x9e,\xa0"4x\x97|\xa92\xc6\x15c\x8e\x08\\!\x08!p\xea/\x8d\x13\x9b\x11\x95,\x83\xd6\x86}\xbe\xdfu\x81\xa1C\xb5\x96L\x01c\xd2\xfbx~\xcbz\x08\x14(\x88s\xe8\xa9\xb2\xc8#\x82\xce\xe03\xc1p\xab\xa2Z\xbc<\xad\xfe\x0e\xe7\xf558\xae\x1cJ>\xcd\xbb@\xd0\t\x95\x96\xc4\r\xc6$sq\xf683\x93\x1cW5o\xef.#\x82\x0fC\x1fe<\xc3\xb8\x03HS,\x1d\x1f\xdds\x9b\x1c\x934\x9b[K\xd6\x1a\xed\xe0\xc7\r3\x81\x0b\xa1.C\xcfw\xa5j\xb4\xc06\x92\xd5\xf8c\xf4R{\xc0\xdf\x1dRJ\x18C\xd7\x1b-\xa6\x80\x88\x12\x01\x14\xe9\xa6\xb8:\x1c\xbc\x98\x11A_\xba\xc4j@v6\xae4G\x8b\xde\x81\xcd\x08\xaf-\xf4R4\xa8J\xcd\x88p~\x1d\xd7;\xbd\xb1\xc3"#%\xae\xbc\xec\x1f\x04\xcb\xf7\xd6O2\xe1\x9f\xfd\x12`\x00<\xc3\xdf\xc5\xc5W\xde\x19\x00\x00\x00\x00IEND\xaeB`\x82'
    ,
    '\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x10\x00\x00\x00\x10\x08\x02\x00\x00\x00\x90\x91h6\x00\x00\x00\x19tEXtSoftware\x00Adobe ImageReadyq\xc9e<\x00\x00\x016IDATx\xda\x94R;n\x850\x10\xc4\xc6\x80\xc4\x958\x00%W\xa0J\xf4\x94cp\x83(\n\xa2&\x05GH\xc3-r\x06$Z\x04\xe2clg\xf0&\xce\x0bJA\xb6\x1a\xc6;\xe3\xd95\xcc\x18\xe3\xfd\xa7\xd8\xcb\xedj\xeb\xd3\xeba\xcd\x9e\x1f\xbd\x0f\xf3pQSU\x95P\xda\xd3F\xe3Ck-\xa5D\xc2 \x08|\xdf\x07\xa3\x94\xda\xb6\r \x0cCb\xba\xae\xe3\xbb\xf2v[\xf3<\x17EQ\xd7\xb5\x10\x02Jb\xdel\x01P\x0f4b\xd7\x87\x13\x10\x9a\xc6q\x04\xc0\xf1\x91\x951\xd8O\xd3\x04\x0c\x80k)\x95\x80L\xee\x12\x08\x06\xb41\xe8\x11\x0f\x02\xc7\x00\xc0\xeeK m\xa4{A\xdf\xf7Q\x14\x01\xac\xeb\n\x12\xe9]\x1e{\x83\xf2HM\x13\x03\xb4m{\xbf\x99a\x18~\xdf\xb0\x9f\x05M\xd3\xc4q\x0c\xb0,K\x96et\x84M\x9cop\x91\xca\xb2\xc4\x00\x14)MSD:\x0b\xdc\x0cDa\x00t0[\x9cs\xb8`\r\x7f\xcc\x00\x96v\x87>\x12\x80\xc1\x93\xd1\xd1\xcf\x0c\xea\xfb\x1dPy\x9e\xc3\x0f\xb7\xc3\x98\x94I\x92\x1cMB\xb8\x1e^\xbd\x1b\xda\x1a\xed\x1e\xad\x00\x8e\xe1\xb6\x1cs\xb8\xd0\xa0\xf8I.\xfe\x7f\x9f\x02\x0c\x00\xa0\x0b)T\xc7\x159\xaa\x00\x00\x00\x00IEND\xaeB`\x82'
]

ICONS2 = {
    'door': '\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x10\x00\x00\x00\x10\x08\x06\x00\x00\x00\x1f\xf3\xffa\x00\x00\x00\x04gAMA\x00\x00\xaf\xc87\x05\x8a\xe9\x00\x00\x00\x19tEXtSoftware\x00Adobe ImageReadyq\xc9e<\x00\x00\x01.IDAT8\xcb\xa5\x93=J\x04A\x14\x84k\xfcA\xd7\xc0eE\x03\x15\x0fbd\xe01<\x84\xa1\xb9W\xd8\xdc#\x18ob\xe4\x1d\x0412\x10\x15d\xc1ht\xde\xab*\x83\x1egW\xd0Ya\x1f4\xaf;\xa9\xfe\xaa\xfaue\x1b\xcb\xd4\n\x96\xac\xb5\xf9\xc3\xdd\xd5\xb9%\xc1&HB*\x8b\xcc\xae\x93\x89\x93\x8b\xeb\xeaW\x01\x89\xd8;>\x05LX\x86$X\x04\xc4n\xffps\xfd7\x01\x990\x89\x8f\xf7\'\xb8\xbd\xdd$\xdc\x12ln\xef#\xb3\xe9\x17\x90\x081a\x1511!\x12V\x82\x8c~\x81\xcc(\xb7e\x14\x02f9\x930\x03\xce@D/A+\xd0\xf5\x19E\xe5\x06"\x17\x114\x059\x9a\xe2?\x13Rbg8\xc5\xe1\xc1\x1b\x1e\x9f\x87\xc8\x8c~\x0bj-t\xf8*}:\x1d\xa0\xfe\\\xff\x0fA\x80\xd9\xfc\xb0\xf0\xfa\xb2\x01s\x15[\xbb\xea\'\x88hf!2\xda\xf0Z!\x95=\x19\x0b\x08\xb2d`\x95\xf4\xbf)\xac\xf2\xb4\x0b2(\x16\x06\xa3#\xd8\x82\x99\xb0T\x96\t\xb1\x8c\xf3|U\xb61\x99L\\\xd75\xe2\xf6\xb2\x9b\xf7\xf9\xf9\x9f\xfd\t\xc2&\xeeGg\x00\x80\xf1x\\U\xcb~\xe7/G\xdc}\xb3\x8f\x11?\x1f\x00\x00\x00\x00IEND\xaeB`\x82'
    ,
    'accept': '\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x10\x00\x00\x00\x10\x08\x06\x00\x00\x00\x1f\xf3\xffa\x00\x00\x00\x04gAMA\x00\x00\xaf\xc87\x05\x8a\xe9\x00\x00\x00\x19tEXtSoftware\x00Adobe ImageReadyq\xc9e<\x00\x00\x02\x9fIDAT8\xcb\xa5\x93\xebKSa\x1c\xc7\xfd;v\xcevl\x03\tdD!\x82\x84P{\x15$\x12;\x9a\r\xc5\xbc,K\xd3\xdd\xbd\xd26c\xd8L\x8b2r^\xc6H)-\xb3\xd4jsNm\xea\xd4\xe6\xd6\x942q\xd9QB\xcc\xbd\xe9B\xb5at\xb1o\xe7\xec\xc5L\x12#z\xe0\x0b\x0f\x0f\xcf\xe7\xf3{\xaeq\x00\xe2\xfe\'\x7f\x0c\x14\xf8\x0e\x89r\xa7\x0f\xea\xb3=)L\xc6\xe3\xfda\xe9\x888,u%2Rg\xa2>\xdd\xbeW\xb4\xab \xcf\x9bJ\xcb<\xc9!\x9dG\x86\x9bA\x0b\xfa\x96\xbb\xa2\xe9\\lF\x89\xeb\x18$\xbdTH\xd2C\xd1;\n\xd8\xaat\xe6xR\xe4\xea\x9c\x11\xce\xd5~\xd8^^\x83i\xae2\x1a\xae\xefX\xedC\xe3L\x15\x0e\xd8\xf8\x91d\x1b\x9f\xde&\xc8\xf1\xa4\x083\xddI\xeb\x1c\xccM\xac\t\x94\xa1\xc2_\x02\xcd\xcc\x19\xe8\xd8\x94\xb3\xa9\xf6\x9d\x85\xfd\xf5=\\\x9c\xaa\x80\xd8B\xae\x8b\xaf\x93\xc2\x98@\xe6N2\xa8\xc6\xb2\xa2\x959\x98\x03U\xdeSPL\x17B1U\x00\xf5T!\xdck\x830x\x95p\xb0\x92\xdc\x9e#H\xb8B\x1ab\x82\x8c\x111\xd3\x19l\x865\xd8\x84\n_1\x94O\xe4,\x98\x0f\xe5$\x1bO>\xc6\xdf\xb8\xc0\xb5Pd\rm\xcf\x1ba\x9bkD|=\xc9\xc4\x04G\xed\t\x1b\x0fVn\xa36\xa0\x81\xd6[\xc4\xaed\x00\x8b\x1f\xe6\xa1\x9a(\xc4\xd8\xdaP\x14\xfe\xb1\xf9\x1dm\xcf.\xc10Q\x8c\xbe`\'\x04Fb#&\x90\xdc\xa76\xfa\x97\xbba\xf4\xabP\xeb\xd7\xe2\xd3\xd7\x8fQ\xe8\xfd\x97\xb71\xd82[\x0f\xb5+\x1bz\xf7i\xf4\x07; \xa8\xf9]\xd0C17\xe6\x9b\xd0\xbep\x19\xbaI9\xcc\xbejD\xbe}\x8e\xc2\x9b?7ayz\x01e\xce,hXAK\xa0\x0e\xed^3\xa8*bk\x0b\xa9\xb7\x04\x06\xf9@\x1a\xec+wQ=!\x87\xda}\x12u\xd3\xe5Xz\xb7\x80\xb6\xd9\x06\x94\x0e\x1e\x87\xc2q\x02:g\x0e\xec\xaf\xba\x91n=\x0c\xaa\x92\xd8:\xc4d+_\xb8\x8f\xbd\x1a\xb3G\x83\x87\xcc\x1dT\x8e\xe6A;\x9c\x03\xd5\x90\x0cJ\x07\x17\x0e\xce\xc6\xa3\xa5.\x18\x87\x8a!P\xf3\xd6)5!\xdc\xf6\x90\x12\x9bH:\xbe\x81\x88\x98\xdcep\xb0\x92\xd6\x80\x19\xfa\xd1"\x9c\x1b\x96\xa3\x95\xdd\x82\x9d\x85\xf5\xce"\xf0Ky\x11\x16\xa6w|\xca{\x1aH\x9a2\x11!i\x87\x04\xed~3z_X\xd1;o\x85\xc5kBZK*\x04\n^\x88R\x11\xf4\xae\x9f\x89:O\x8a(\x03\xa1\xa7j\x08F\xa0\xe5\x85\x05*^\x98\xad\xc8\xb0\xd1S\xa5\x84\xe8\xaf\xbf\xf1_\xf3\x0bg\xd0\xac\xe5y\xba\xd4c\x00\x00\x00\x00IEND\xaeB`\x82'
    ,
    'add': '\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x10\x00\x00\x00\x10\x08\x06\x00\x00\x00\x1f\xf3\xffa\x00\x00\x00\x04gAMA\x00\x00\xaf\xc87\x05\x8a\xe9\x00\x00\x00\x19tEXtSoftware\x00Adobe ImageReadyq\xc9e<\x00\x00\x02oIDAT8\xcb\xa5\x93\xebK\x93a\x18\x87\xfd[\xb6/\x05\x83\xa4\x86Y(\xa8)%X(o\xd9l\x8a\x8aN\xdb\x96sk\x8a\xce\xf6n.\x9d\xba\xcd\x03-\x9d\x13\x0f\x15\xb5\xa1\xdbh\xa4;8\x0f\xc3\x03f\xe2\xd4\xd2E\xea\xebP\xa2\x8d"\x08j\xc3\xaf\xbf\xde\x15MG\xcb\x88\x1e\xf8}y\xe0\xba\x9e\xe7\xbe\xb9\xef$\x00I\xff\x93\xdf.t\xd3u\xcc\x0e\x8f\x84lu\x89\xa8\xe6\tAX\xfe\xa2:\xdc\xf0\xbc\x82\x92Z\xcbH\xd1h1\xf3D\x81nZJ\xb4OJB\xcf\xd6{\xb1\x1aZ\x84\xff\xf3\x06\xd6?\xad`2`\x87\xd2S\x03\xbe\x89\x13\xe2=\xb9N$\x14\xfc\x84\xc5\x91\xe9=;\x0e\xbe\xeda\xf6\x83\x0b&j\x10\x8fw\x0c\xb0\xef\x9b\xb0\xf4q\x0e\xda\x05\x19JG\xf2#\xdc\xc1<"N\xa0\x9d\x922h8\xe8\xde\xb5`\xef\xeb6\x86\xb7\xf5x\xb8\xd6\x81n_+\x0c~\x1d\xfa\xfcZto\xb6\xc0}`\x07\xe9\x11\xa2\xd0x%X\xd0\x9b\xcd\x88\thX\xd1\xbf\xac\xc6\xbb/\x9b\xf4\x8b}\xe8\xdd\xd2B\xf3J\x89_G\xbd&\x83|Q\x08\xc5r-\x9c\xfb6\xdc\x1c\xc9A\xde\x83\x0cEL\xd0\xe2\xac\xa1\\\x01\x1b\xfdU3:WUh[\x91C6+\x8a\t\x046.\x1af\xca \x9d*\xc6\xc0\x1b\x1d\xf4K\xcd\xb8\xdc\x9dF\xc5\x04\x8aq\xfe\xa1\xf7\xbd\x0b\xfdou4\xdc\x84?\x1d\xf1d\x11\x14\xf3|X\xfc\xc3\xc8\xd2\xa5\x1e\xc6\x04Mv\xde\xe1D`\x0c\xda\r\x12*_\xfd\x89\x02\xd2[\r\xab\x7f\x08\xe9\x1d\xec#A\xbd\xad\x9c2\xfa\xb40li\xd0\xf4R\x08\xf1|\x05x\xd6\x1bq`4w=\\\xf4\xfb\xd4\xe8\xf2\xde\xc3\x05u\xf2Q\t\xe2\xb1\x12\xc5m+\x01G\xc0\x02\xd9|%$\xde\xd2\x1f5\x1f\x17\x88\x9c\x1c\xd4\xb9\x8b\xe1\xd85\xe3RO*\xd8\xf7YGM\x14\x9a\x8b\x18UO\x0b\x83\xa4G\x80qj4\xd6\xb0(X\xeb\x8c&\ns1\xb1c\xc2\x1d\xcb\xad(\x1cLV\x9ef\xc4\rR\xf9\xa3\x02\xa2d\xe8j\xa4\xd1Q\t\'-1\xfa\xdaA\xceTA>U\t\xe3j\x1b\x1c4,\xb4p\xc0V\xb1"4L$\x1ce\xce@.A\x18rB\xf9\x03\x99\xe8Y a~m\x80y\xc3\x00\x8d\xb7\x11Y])Q8t\x1cN\xb8L\xd7\xf4\x99\xcc\xdc\x9et2\xbb\xf3"\x95\xa1I\t\xa7\xb5\x9f\r\x9fo=C\x9dS\xb1\xc8d\xe5)\xe6_\xb7\xf1_\xf3\x1dAF\xcb\x1f\x00(\xd3\xc1\x00\x00\x00\x00IEND\xaeB`\x82'
    ,
    'asterisk_yellow': '\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x10\x00\x00\x00\x10\x08\x06\x00\x00\x00\x1f\xf3\xffa\x00\x00\x00\x04gAMA\x00\x00\xaf\xc87\x05\x8a\xe9\x00\x00\x00\x19tEXtSoftware\x00Adobe ImageReadyq\xc9e<\x00\x00\x02yIDAT8\xcb\xa5\x93\xcdKTa\x14\xc6\x9f\x7fa\x16-j9\xb4i\xd1j\xa0\x85D\x10\x0c\xd1\xc6E\xc1T\x90\xa5Q\xcd@\x05\x951\x0c\x1aI&V\xb6)\x8b\x88\xa9\xec;\x99D\x8c\xac\xec\xe3-sD\xad\xe8"\xd7\xcc\x8fQg\x9c\x99\x1aR\xd3k\x8e\x8e9\x1fw\x9e\x8e\x90\x8a5\xaeZ\x9c\xc5\xfb\xde\xfb<\xe7\x9c\xdf9/H\xe2\x7fb\xd9!\xdb\n\x9b\xe9\x87\xca\xbc\x03\xd3\xcdp,\xdc\xcf\xbe\x843\xd1\x04N?\x83\x9aj\x845\xa7\x81\x88\x9d\xe6G+\xb3C.f\xc3%L*\xa8\x85o3M\xd0\xcc`)\x93\x9d\xdb8\xf9\x18\xc6D\xfd\x92\xf9\xa2\x81\xd9\x02{F[\xcfl\xec\x1c9Z\xcd\xb9\x96U\x9c}\x01\xeb\xccs\xd8\x13\xfeud\xe443\x81b\x8a\xd8\xf8Q\x07[\xce\x16Ro\xe1I\xebvr\xa4\x9a\xa9\xee\x9d\x14\xb17\xfe\x14\xde\xa4\xbe\x83\x0c\x97q\xa65\x8fc\x8f\xe0\\\x91\xc1|\xfcz\x05\x95\xd2\xf3\xa5\x92*\xc6\x1ba$\xf5]\x92\xbd\x9c\x89\xf7[\xe6\xc5\xde\x7f \n,[\xf2\xcdRI\x02\xcb"\xb0\x8cl\xb4\x82\xd9\xd012x\x9c\xe9\x1e\'\xc7|\xd0FjaY\xf8/r\x0b\xb6\xe1\x1b\xb0A\xc4*\xd9f\xa5\x90\xa6\x88\x8d?\xa4\xb5L\xc0E\x0e\x1e \x03ELw\x17\xf2\xfbCh\xb1\xfbP_\xef \x18\xa9\x01c\xbe5\x1c\xba\x06\x85\xb9\xd7P\xe6p)9\xfe\x80f\xb8\x9c\xe9A7\xd3\x03\xc5\xd2s\t9\xb0\x8f\xec/\x10\xa3\xc3L\xf5\x1c\xe5\x9c~\x90\xe9>7\x19\xaad\xe2S!{/\x89\x81\x90V\x02\x8b\x02\x8b?\x9f@\x9bl\x80\x12\xd2*\xf5y\x8fd\x17\x83\xbe\xddL\xe9\x05\x8c\xde\x86\x16\xae\x81\n]Gp\xf0*\xd8{\x11\xec\xaa\x12\x83\xbf\xa1\x8c\xd7\xc3"\xb0\x0c3t\x8a\x99\x9e\xfdR\x85\x8bI}/\xc37\xa1\x85\xbcK\x0cV\x9c\x82\x88\xd5t\xfbV\xa6\xfa\x8b\xf9\xed.\x82\xd3\x1d\xdb\xa5\x85\x13\x9cP\x9b\x19\xb8\x92c\n\xcb\xc4>\x9c\x9f\xf2o"\xa3\x954T\x1e\x85\xb4SH{\xa7Z\xf3\x85\xc5\x11\xc6\x1a6\xb0\xf3,<9\rF}pL*\x9b\xac\xf1\x19f\x06<\x14\xd2\x86\x88-B\xda\x1e\xad]+,\x0eI+.~\xb9\xbc\x9a\xed\'sl\xa2\x8c\xc9\x11\xbb\x07#\xde!\xfb\xdel\xa7\xc0Z\xcc\xd4u\x01Z\xbc\xa3\x88\xd1\xba\x8dl+\x85\xe1w\xe7x\x0b\xf3!\xa4\xadB\xbaN\xc4JH/\xbe:\xad\x02\x8e\x0fePm%\xf0\xb4\xb8\x97\x83\xfc\rL\xdb\xc0:\x1b%\xf2\x81\x00\x00\x00\x00IEND\xaeB`\x82'
    ,
    'disk': '\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x10\x00\x00\x00\x10\x08\x06\x00\x00\x00\x1f\xf3\xffa\x00\x00\x00\x04gAMA\x00\x00\xaf\xc87\x05\x8a\xe9\x00\x00\x00\x19tEXtSoftware\x00Adobe ImageReadyq\xc9e<\x00\x00\x01\xfeIDAT\x18\x19\x05\xc1=\x8b]U\x18\x06\xd0\xb5\xcf\xec;C\x82\x92\xa8`\x84DD\x03\nV\x01e \xf1\xa3\x15\x7f\x82\x85h\x91*B\xd0"\xa56VV"\xa2\x08c\xa1\xd8\nv\x82ba\x95"\x16\x16\xc1N\xc5B\xb4\x12\xc5\x0c\xde\x99{\xf6~\x1f\xd7j\x87o|\xf7\x16\x1e\xc3\xf3x\x02\xf7\x91\x8e&\xc0\xde\xd2,K\x93\x94*\xff\xeco\xfc\xbc=]\xdf\xbb\xf3\xf1\xcb_v<}t\xeb\xdau\x9a\xa7.\x1e\x08R\xb1\x1b\xb1[\xcb\xde\xd2\x9c9X\xb4\xc6\xf1\xb6\x1c\x9f\xccs\xbf\xfey|\xe5\xf3o~\xf9\xe4\xf0\xc6\xd7\xe7\x16\xbc |u\xe7_\x15\x92\xb8\xf9\xe1\x0f\xaaBk6\xbdY\x96f7b\xbb\x96Q\xda\xb4\xf4\xd7^\xba\xfc\xd0\x99\x83\xfd\x8f\x16<\x12T\xc5:\xca:\x02\xd6\x8a\xbe\xc7\xa67U\xb1\xdd\x95u\x84\xc4\xf7w\xef\xd9\xdf\xec\xd9\x9e\x8e\xfd\x8e\xb3\xa3\x82\xd8\xee\n,\xad\x116}\xd14\'k\xd9\x9eF%*T\xe2\x8f\xbfNHZ\'}&\x12NG\xc0\xdb\xaf_\xb1\xe9\x8b\xbe\xb0\xce\xf8\xef\xb4\x8c*UD\xa4\xca:\xa6\xa4t\xb4\x9aH\xbc\xfb\xd9\x8fZk\x96\xc6\xa6/\x1aF\xc5\x18%\x008\x7f\xfeA\xeb\xd8#\xd1\x85J\xa9\x9a\x1e\xbep\x91F\x13\x02Q\xa1\xaa$Q\x89\xaa\xa25\xeb:H\xe90\'\t\xd0\x12\xa0QE\x12D\x82DK$e]\x9b\xa4t\x18\xb3\x10\x10\xd14\x12I\xa4JD\x12US*\xa2\x9c\xae!\xa5\x13\xb3Bx\xe7\x95K\x00\x00\x00\x00\xe0\xd6\xd1O\xc6\x88\xa4\xf4\xa55\xb3\x88H\xf8\xe0\xf6u\x00\x00\x00p\xf3\xea\x919\x87\xdd\x08\x89\xaeQ\x15\rp\xed\xd2\xab\x00\x00\x00\x00j\x96\xb9\x06\xa5\'\xc9\xac4\x02n\xff\xfe\x05\x00\x00\x00x\xf6\xd1\x17\xcd9\xad3\x92\xa4W\xfc\xb6\x1b\xf5\xf83\x97\xcfj\x8d7\x9f\xfb\x14\x00\x00\x00\xc0\x85\xfb\xcb\x9c\x81\xbf\xdb\xe1\x8do\xdfO\xf2$\xb9*y\x80\x92\x84\x94\xa4HI\x8a\x14\x89$H\xc8=m\xb9\xfb?!|n\x8bm\x10\xb0\xa2\x00\x00\x00\x00IEND\xaeB`\x82'
    ,
    'delete': '\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x10\x00\x00\x00\x10\x08\x06\x00\x00\x00\x1f\xf3\xffa\x00\x00\x00\x04gAMA\x00\x00\xaf\xc87\x05\x8a\xe9\x00\x00\x00\x19tEXtSoftware\x00Adobe ImageReadyq\xc9e<\x00\x00\x02]IDAT8\xcb\xa5\x93\xfbKSa\x18\xc7\xfd[\xb6\x1f\xa2\x04\x89n\x84\x84QP\x98\xf32w\xd6\xda\xdc\xa6\xce\xb3L\x8f[,bi\x8e\x9da\x9aA\x8d\xc5\\\xf8C\xa8\xa5v\xd5\xca_2Ml\x94ZFj\xd7\xa1\xe5\xb1\xf2\xd2NMjm\x9e\xb3k\xca\xb7\xb9`&.#z\xe1\xfb\xcb\xcb\xfb\xf9\xbc<\x0f\xcf\x93\x02 \xe5\x7f\xb2\xe6bV\xaf\x17\xceP\x15\xe6\xf7T\x193\xa5%\xb9I\xad\x86{G\xaa\x99qRiv\x95\xc8\x85\xeb\n\xe6tz\xe2#E\xb1\xdf\x1c6\x84\x07\x9d\x88\xbc\x19Edd\x08\xfc\xdd\x0e\xcc\x1aJ\xf1\xaa\x90`\x9f\xab\xc5DR\xc12<]N\xf1\x0b\xb7;\xb04\xf5\x16\xd1\xbe;\x88\xb6\xdb\x11m>\x87\x1f7\x9b\xb08\xdc\x07\x8f\xc9\x80Qe6\xffL\x9eI\xac\x12\xcc\xe8t\x82\x18\xec\xe6\xae\xb7c\x89q!z\xf1\x0c|v\x0b\xfc\xb6j\x84/X\x10i\xa0\x11\xb6\x9e@\xf8\xde\r\xcc\x1d%1|h\x9f\xfb\xb1l\x8f !\x88\xc1\xf4|\xad\x19\x8b\xae\xb1\xf8\x8f!\x07\r\xefY#\x82u\xbaU\xe1N\x92\x08w]\xc1\xcb\xbc\x0c\x0cH3\xe8\x84\xe0\x03u\x84\tt]E\xb4\xb3\x19>k%\xbe\x16I\x93f\xa1\x92\x04o\xab\x81\xc7R\x85\x87D:\x93\x100\xe5\xda`\xe4~\x17\xa2\x0e\x0b|\xa7\r\xf8\xd3\xf1(r\xe0\xa5\n\xe1on\x843oG0!\x98$\x8b\x82\xa1\xceV\x84\xeb\r\x08\x9e*[W0_\xaa\x82\xbf\xa9\x11\xfd\xe2-+\x82\x89\x12\x15\xe3\xb5\xd6 d\xa7\xc1\x1dW\xc7\x1f&\x8d2\x0f\xbeZ\x13fMF\xf4\x89\xd2VJp\x15\xcbiF&B\xb0\xb3\r>\xad\x0c\xdeR\xc9\x1a\x98\x95g\x83-\x90 \xd0~\tC\xe2m\xe8\xcd\xda\xb4\xd2\xc4\xd7ER\xc1\x0b\r\xe1\x9e\xab\xd0 p\xab5\xde\xb0y\x95\xf8\x17\xa8\xc8\x05+\x8b\xc121\xf8\xb6\x16\x8c\x17K\x97aw\xb7h\xa3`\xd5 \x8d\x15\xe4\x10#\x8a\x03\xfc\xf4a\x15\x02\xd7Z\xf1\xbd\x9e\x86\x87T\xe2\xb3Z\x01o\x9d\x19\xfc\xe5\x16L\xa8\xf3\xd1\x93\x95\xca\xc7`"\xe9(?\x95\xef\'\x9e\x1c\xdc\xcb\x8eJv\xe1K\xb5\x11\xde\x86\xf3\xf1|\xaa:\x86G9[\x97a\xf6w8\xe92\rJw\x0b\x07\xc4\xe9f\'\xb1\x93y\x90\xbf\x9d\xeb\x17m\xe6zs\xd3\x98\x9e\xecTsw\xe6\x06\xe1_\xb7\xf1_\xf3\x13\x1d\xd2\xce\xb9Ir\x1b\xfe\x00\x00\x00\x00IEND\xaeB`\x82'
    ,
    'arrow_refresh': '\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x10\x00\x00\x00\x10\x08\x06\x00\x00\x00\x1f\xf3\xffa\x00\x00\x00\x04gAMA\x00\x00\xaf\xc87\x05\x8a\xe9\x00\x00\x00\x19tEXtSoftware\x00Adobe ImageReadyq\xc9e<\x00\x00\x02?IDAT8\xcb\x8d\x93\xdbK\xd3a\x1c\xc6\x07\xfb3bv\xd0\x92B\xba\xb0B\xd69\xcbd-Od\x06\xad6_\xd7t\xe4\xa1\x81e\xce\xc5\x9a\xfe\xdc\xdc\xa1\x1d\xdcI\xcd\xb1aIF%\xfc\xc0h\x84e\xb5\x8d\r\xd7a\xf9#\xe8\xda;\x11\xbc\r\xef\x9e\xbe\x1b]8\xfda\xbbxo\xde\xc3\xf3<\xef\xf3\xe1+\x01 \xf9\xdf\xba\xf1\xbcq\xb0eZ!\x15;\x93\x94"\xd04U/(\xc6/Dv\x15\xe8\xfb\xac\x95\xdd]\xd4\x18toUq\xcd|\xdb\xfa\xcd\x17\xcd\xb8\x16U\xa2!\\\x07\xfd\xcbvt<S\xe1\xa4\xf9\xb8OT\xa0w\xa9C\xae\x7f\xaf\xe6\xb9\xa4\x11\xfe\xac\x03\x91\x9fADWB\x98\xca\xf9\x10\xfc\xfa\x04\xde\xe51\x8c\xa5,h\r5\xa2\xaa\xb7r\xb4H\xa0\xe7C\xbb\xac\xeb\xdd-\xde\xb3l\xc5\xec\xafiL\xfe\xf0\xe2i\xce\x8f\xd077|Y;\\i\x0e\xd6\x94\x19\x8f\xbf\x18q\xd5]\x8f\x83\xba\x03\xce"\x01\x8al0\x7fz\x80\x19a\x12\x91\\\x10\xee\x8c\r\xba95\xce\xdb\xe4\xf9\xc886p\x14M>\x05\xae\xb8\xeaP\xa1\xdd\x17\xd8\xf1\x05\xf5\xeb\xd6\xb8#i)8:S\x1c.\xb9\xce\xac\x9e\xe5j\xdc[/Uv\x96\x0b\xe5loL\xb4\xc4\xeb3\rk\xd4\xf2&\xb5\xfc\xa7\xd6~j\xe3\xb4\xe5\x04\xb7\xfd\xd2~M\x99\xa9L\xb5GJf\x8c\x902B\xca\x94\x81\x8b\x8c\xcc\x98\x84Zf\x97=\xe7\x18Ef\x14\x99Qd\xd6\x9f\xee\x92\x1a\x12wL\xdb\x85\xc8\x8c#\xb3\x8d\x7ff\x9bd\xb6&\xca\x9d\x90\xc6\x08\xa9\xb0u\x8f\x90\xba\xc9l\xd5\x93\xb6\x11\x15;\x06\x16\xee\xe5\xfb\x89\xefxLH\x03\xd6\x8c\t\xc3\x89\x87\xa0\xc8\xa0\xc8\xa0\xc8\xe8~\xa3\x85+\xc9\x15\x90:\xd2#h\x9bh\xce#5\x14=&\xa4N.e\xc4\xdc\xefh\x01iL\x98(B:\x92\x18* \xd5\xce\xde\xc6\x91\xeeC<!\x95\x15\t\x10\xd2\xd1G\x1f\xfb\x11[\t\x17\x90\x86\xbf{1\x9eu\xc2\x95\xb1bxi\x08=\xf3:\xb4\xf8\x958\xac\xaf\xe0\t\xa9\\t\x16(\xb2\xaf\x8f\xef\x84\xfe\x15\xcb#\x05!E\x8d\xa9\x1a\xd5\xf7\xab\xd6)r\x9c\x90\x1a\x08\xa9l\xd7a\xca\x0f\x0e\xb5,\x942h\xa2\x9b\x84TJH\x07K\x11\xf8\x0b\x84\xac\x88\x99\xe8\xea\x8c(\x00\x00\x00\x00IEND\xaeB`\x82'
    ,
    'pencil': '\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x10\x00\x00\x00\x10\x08\x06\x00\x00\x00\x1f\xf3\xffa\x00\x00\x00\x04gAMA\x00\x00\xaf\xc87\x05\x8a\xe9\x00\x00\x00\x19tEXtSoftware\x00Adobe ImageReadyq\xc9e<\x00\x00\x01TIDAT8\xcb\xad\x93?H\x02q\x18\x86][\x0b\x83\x96p\xa9\x96@\x04\x9b\\\xe4h\x88\x86\x14Zr0\x8c\x06+\x92\x86\xa0\xad\xa5\xa6\x10\xca\x90\xc0\xe0\xdc\xb2\xd4H\x82lH\xa8H\x8b\xee\xbc\xe0*$:\xd4\xe22,\xc2\x1a\xec\xc4S\x92\xb7\xbc\xe1 *\xfbA\r\xef\xf6=\xcf\x07\xdf\x1f\r\x00\xcd_B\\x\x1f\xd37\xa5\xc3\x96\xa7\xa4\xd7Zc<\x03\xb8\xf4\xeboo\xd6z\xda\x88\x05B\xd0\x8a\xeb\xc0\x04\xca"\x0b9\xc7!\xb9B!>g\x88\x90v\x87\x94\xda\x80,\x9e\xa0\x92;SRN\xef\x83\xf5XjD\xb0\xfc\x9c\x80|\x17D62\t\x89\x0f(\xa9\x0b8\xef`\x99\x08~\x93vP\x12\xc6\xf0\xcaO\xe1\xdcoCvs\x1a\xec\xb2\x05\r\x87\xf8\t\xce8 ]\xf5\xa2\xfa\xb2\x88|\xd4\x0ea\xc9\x84\x86[ \x85\xbf\x15\x1cz\xba\x88\xe1/\x82\xbd\x85N\x14\xf3\x07\xc4\xb0*\xf0\x8d\xeatuX\xe4\xb6\xc1\x84\x9c\xc4\xb0*\xf0\xba\xdaQ\x14\x19T\x1f.\xb0;kDb\xd5\x80\xcc\xb1\x0b<\xdd\x8f\xd3y#~=\xe5\xba\xa0\xf2q]\x85\xf0\x08\x1e}f\xc4\x9dZ\x84\x1d\xad\x88\xcet\x83\xe8\x17lT3R\xb4\x1d%~\x1d\x05>\x84#w\x1f\x11\xac\n\x86\xcc-\x18\xa6\xb4\xa0\xc7;\x140\xe66m\xfd\xfb7\xfe\x94wU\\\xf7&\x1c\x1f\x9d\x02\x00\x00\x00\x00IEND\xaeB`\x82'
}

ICONS_ICO = [
    '\x00\x00\x01\x00\x01\x00\x10\x10\x00\x00\x01\x00 \x00h\x04\x00\x00\x16\x00\x00\x00(\x00\x00\x00\x10\x00\x00\x00 \x00\x00\x00\x01\x00 \x00\x00\x00\x00\x00@\x04\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x1a\x00\x00\x00\x1a\x00\x00\x00\x1a\x00\x00\x00\x1a\x00\x00\x00\x1a\x00\x00\x00\x1a\x00\x00\x00\x1a\x00\x00\x00\x1a\x00\x00\x00\x1a\x00\x00\x00\x1a\x00\x00\x00\x1a\x00\x00\x00\x1a\x00\x00\x00\x1a\x00\x00\x00\x1a\x00\x00\x00\x00\x03\x03\xa1\xff\x03\x03\xa1\xff\x03\x03\xa1\xff\x03\x03\xa1\xff\x03\x03\xa1\xff\x03\x03\xa1\xff\x03\x03\xa1\xff\x03\x03\xa1\xff\x03\x03\xa1\xff\x03\x03\xa1\xff\x03\x03\xa1\xff\x03\x03\xa1\xff\x03\x03\xa1\xff\x03\x03\xa1\xff\x00\x00\x00\x1a\x00Fe\xff\x03\x03\xa6\xff\x03\x03\xa6\xff\x03\x03\xa4\xff\x03\x03\x9f\xff\x03\x03\x9e\xff\x03\x03\xa3\xff\x03\x03\xa6\xff\x03\x03\xa6\xff\x03\x03\xa3\xff\x03\x03\x9e\xff\x03\x03\x9e\xff\x03\x03\xa3\xff\x03\x03\xa6\xff\x03\x03\xa6\xff\x00\x00\x00\x1a\x00Hh\xff\x02\x02\xad\xff\x02\x02\xad\xff\x02\x02\xa7\xff\xcb\xcb\xea\xff\xff\xff\xff\xff\x16\x16\xab\xff\x02\x02\xac\xff\x02\x02\xad\xff\x02\x02\xa6\xff\xf7\xf7\xfc\xff\xf7\xf7\xfc\xff\x02\x02\xa6\xff\x02\x02\xad\xff\x02\x02\xad\xff\x00\x00\x00\x1a\x00Kl\xff\x02\x02\xb4\xff\x02\x02\xb4\xff\x02\x02\xac\xff\xc4\xc4\xe8\xff\xff\xff\xff\xff\x13\x13\xaf\xff\x02\x02\xb3\xff\x02\x02\xb4\xff\x02\x02\xab\xff\xf0\xf0\xf9\xff\xf0\xf0\xf9\xff\x02\x02\xab\xff\x02\x02\xb4\xff\x02\x02\xb4\xff\x00\x00\x00\x1a\x00Np\xff\x02\x02\xbc\xff\x02\x02\xbc\xff\x02\x02\xb5\xff\xc4\xc4\xeb\xff\xff\xff\xff\xff\n\n\xb1\xff\x02\x02\xb6\xff\x02\x02\xb6\xff\x01\x01\xaf\xff\xed\xed\xf8\xff\xf0\xf0\xfa\xff\x02\x02\xb3\xff\x02\x02\xbc\xff\x02\x02\xbc\xff\x00\x00\x00\x1a\x00Qt\xff\x02\x02\xc4\xff\x02\x02\xc4\xff\x02\x02\xbd\xff\xc4\xc4\xed\xff\xff\xff\xff\xff\x91\x91\xdd\xff\x9c\x9c\xe1\xff\x9c\x9c\xe1\xff\x94\x94\xde\xff\xf7\xf7\xfc\xff\xee\xee\xfa\xff\x02\x02\xbc\xff\x02\x02\xc4\xff\x02\x02\xc4\xff\x00\x00\x00\x1a\x00Uy\xff\x01\x01\xce\xff\x01\x01\xce\xff\x01\x01\xc8\xff\xc4\xc4\xf0\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xed\xed\xfa\xff\x01\x01\xc7\xff\x01\x01\xce\xff\x01\x01\xce\xff\x00\x00\x00\x1a\x00X}\xff\x01\x01\xd6\xff\x01\x01\xd6\xff\x01\x01\xd1\xff\xc4\xc4\xf2\xff\xff\xff\xff\xff\x03\x03\xcb\xff\x01\x01\xcf\xff\x01\x01\xd0\xff\x01\x01\xcb\xff\xeb\xeb\xfa\xff\xef\xef\xfb\xff\x01\x01\xd0\xff\x01\x01\xd6\xff\x01\x01\xd6\xff\x00\x00\x00\x1a\x00[\x82\xff\x01\x01\xde\xff\x01\x01\xde\xff\x01\x01\xda\xff\xc4\xc4\xf4\xff\xff\xff\xff\xff\x13\x13\xdb\xff\x01\x01\xde\xff\x01\x01\xde\xff\x01\x01\xd9\xff\xf0\xf0\xfc\xff\xf0\xf0\xfc\xff\x01\x01\xd9\xff\x01\x01\xde\xff\x01\x01\xde\xff\x00\x00\x00\x1a\x00_\x86\xff\x01\x01\xe5\xff\x01\x01\xe5\xff\x01\x01\xe2\xff\xc4\xc4\xf7\xff\xff\xff\xff\xff\x13\x13\xe2\xff\x01\x01\xe5\xff\x01\x01\xe5\xff\x01\x01\xe1\xff\xf0\xf0\xfd\xff\xf0\xf0\xfd\xff\x01\x01\xe1\xff\x01\x01\xe5\xff\x01\x01\xe5\xff\x00\x00\x00\x1a\x00a\x8a\xff\x00\x00\xec\xff\x00\x00\xec\xff\x00\x00\xea\xff\xd4\xd4\xfb\xff\xff\xff\xff\xff\x16\x16\xeb\xff\x00\x00\xec\xff\x00\x00\xec\xff\x00\x00\xea\xff\xff\xff\xff\xff\xff\xff\xff\xff\x00\x00\xea\xff\x00\x00\xec\xff\x00\x00\xec\xff\x00\x00\x00\x1a\x00d\x8e\xff\x00\x00\xf1\xff\x00\x00\xf1\xff\x00\x00\xf0\xff\x00\x00\xef\xff\x00\x00\xef\xff\x00\x00\xf0\xff\x00\x00\xf1\xff\x00\x00\xf1\xff\x00\x00\xf0\xff\x00\x00\xef\xff\x00\x00\xef\xff\x00\x00\xf0\xff\x00\x00\xf1\xff\x00\x00\xf1\xff\x00\x00\x00\x1a\x00f\x91\xff\x00\x00\xf5\xff\x00\x00\xf5\xff\x00\x00\xf5\xff\x00\x00\xf5\xff\x00\x00\xf5\xff\x00\x00\xf5\xff\x00\x00\xf5\xff\x00\x00\xf5\xff\x00\x00\xf5\xff\x00\x00\xf5\xff\x00\x00\xf5\xff\x00\x00\xf5\xff\x00\x00\xf5\xff\x00\x00\xf5\xff\x00\x00\x00\x00\x00h\x93\xff\x00h\x93\xff\x00h\x93\xff\x00h\x93\xff\x00h\x93\xff\x00h\x93\xff\x00h\x93\xff\x00h\x93\xff\x00h\x93\xff\x00h\x93\xff\x00h\x93\xff\x00h\x93\xff\x00h\x93\xff\x00h\x93\xff\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xc0\x00\x00\x00\x80\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x01\x00\x00\x00\x03\x00\x00\xff\xff\x00\x00'
    ,
    '\x00\x00\x01\x00\x01\x00\x10\x10\x00\x00\x01\x00 \x00h\x04\x00\x00\x16\x00\x00\x00(\x00\x00\x00\x10\x00\x00\x00 \x00\x00\x00\x01\x00 \x00\x00\x00\x00\x00@\x04\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x1a\x00\x00\x00\x1a\x00\x00\x00\x1a\x00\x00\x00\x1a\x00\x00\x00\x1a\x00\x00\x00\x1a\x00\x00\x00\x1a\x00\x00\x00\x1a\x00\x00\x00\x1a\x00\x00\x00\x1a\x00\x00\x00\x1a\x00\x00\x00\x1a\x00\x00\x00\x1a\x00\x00\x00\x1a\x00\x00\x00\x00\x00H\xa4\xff\x00H\xa4\xff\x00H\xa4\xff\x00H\xa4\xff\x00H\xa4\xff\x00H\xa4\xff\x00H\xa4\xff\x00H\xa4\xff\x00H\xa4\xff\x00H\xa4\xff\x00H\xa4\xff\x00H\xa4\xff\x00H\xa4\xff\x00H\xa4\xff\x00\x00\x00\x1a\x00Fe\xff\x00N\xa9\xff\x00N\xa9\xff\x00L\xa7\xff\x00G\xa2\xff\x00G\xa1\xff\x00K\xa6\xff\x00N\xa9\xff\x00N\xa9\xff\x00L\xa7\xff\x00G\xa1\xff\x00G\xa1\xff\x00L\xa7\xff\x00N\xa9\xff\x00N\xa9\xff\x00\x00\x00\x1a\x00Hh\xff\x00U\xaf\xff\x00U\xaf\xff\x00O\xa9\xff\xcb\xd8\xeb\xff\xff\xff\xff\xff\x14[\xad\xff\x00T\xae\xff\x00U\xaf\xff\x00M\xa8\xff\xf7\xf9\xfc\xff\xf7\xf9\xfc\xff\x00M\xa8\xff\x00U\xaf\xff\x00U\xaf\xff\x00\x00\x00\x1a\x00Kl\xff\x00^\xb6\xff\x00^\xb6\xff\x00U\xae\xff\xc4\xd4\xe9\xff\xff\xff\xff\xff\x12]\xb1\xff\x00]\xb5\xff\x00^\xb6\xff\x00S\xad\xff\xf0\xf4\xf9\xff\xf0\xf4\xf9\xff\x00S\xad\xff\x00^\xb6\xff\x00^\xb6\xff\x00\x00\x00\x1a\x00Np\xff\x00g\xbe\xff\x00g\xbe\xff\x00^\xb7\xff\xc4\xd6\xeb\xff\xff\xff\xff\xff\t[\xb3\xff\x00_\xb8\xff\x00`\xb9\xff\x00W\xb1\xff\xed\xf2\xf9\xff\xf0\xf4\xfa\xff\x00\\\xb6\xff\x00g\xbe\xff\x00g\xbe\xff\x00\x00\x00\x1a\x00Qt\xff\x00p\xc7\xff\x00p\xc7\xff\x00g\xc0\xff\xc4\xd8\xed\xff\xff\xff\xff\xff\x91\xb4\xde\xff\x9c\xbd\xe3\xff\x9c\xbd\xe3\xff\x94\xb6\xdf\xff\xf7\xf9\xfc\xff\xee\xf3\xfa\xff\x00e\xbe\xff\x00p\xc7\xff\x00p\xc7\xff\x00\x00\x00\x1a\x00Uy\xff\x00y\xcf\xff\x00y\xcf\xff\x00p\xc9\xff\xc4\xda\xf0\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xed\xf3\xfa\xff\x00n\xc8\xff\x00y\xcf\xff\x00y\xcf\xff\x00\x00\x00\x1a\x00X}\xff\x00\x83\xd7\xff\x00\x83\xd7\xff\x00z\xd2\xff\xc4\xdc\xf2\xff\xff\xff\xff\xff\x02o\xcc\xff\x00w\xd0\xff\x00w\xd1\xff\x00o\xcc\xff\xeb\xf2\xfa\xff\xef\xf5\xfb\xff\x00x\xd1\xff\x00\x83\xd7\xff\x00\x83\xd7\xff\x00\x00\x00\x1a\x00[\x82\xff\x00\x8c\xdf\xff\x00\x8c\xdf\xff\x00\x83\xdb\xff\xc4\xde\xf5\xff\xff\xff\xff\xff\x12\x88\xdc\xff\x00\x8b\xdf\xff\x00\x8c\xdf\xff\x00\x81\xda\xff\xf0\xf6\xfc\xff\xf0\xf6\xfc\xff\x00\x81\xda\xff\x00\x8c\xdf\xff\x00\x8c\xdf\xff\x00\x00\x00\x1a\x00_\x86\xff\x00\x94\xe6\xff\x00\x94\xe6\xff\x00\x8b\xe3\xff\xc4\xe0\xf7\xff\xff\xff\xff\xff\x12\x8f\xe3\xff\x00\x93\xe6\xff\x00\x94\xe6\xff\x00\x89\xe2\xff\xf0\xf7\xfd\xff\xf0\xf7\xfd\xff\x00\x89\xe2\xff\x00\x94\xe6\xff\x00\x94\xe6\xff\x00\x00\x00\x1a\x00a\x8a\xff\x00\x9b\xec\xff\x00\x9b\xec\xff\x00\x94\xea\xff\xd4\xeb\xfb\xff\xff\xff\xff\xff\x16\x9b\xeb\xff\x00\x9a\xec\xff\x00\x9b\xec\xff\x00\x93\xea\xff\xff\xff\xff\xff\xff\xff\xff\xff\x00\x93\xea\xff\x00\x9b\xec\xff\x00\x9b\xec\xff\x00\x00\x00\x1a\x00d\x8e\xff\x00\xa2\xf1\xff\x00\xa2\xf1\xff\x00\xa0\xf0\xff\x00\x9b\xef\xff\x00\x9a\xef\xff\x00\x9f\xf0\xff\x00\xa2\xf1\xff\x00\xa2\xf1\xff\x00\x9f\xf0\xff\x00\x9a\xef\xff\x00\x9a\xef\xff\x00\x9f\xf0\xff\x00\xa2\xf1\xff\x00\xa2\xf1\xff\x00\x00\x00\x1a\x00f\x91\xff\x00\xa6\xf5\xff\x00\xa6\xf5\xff\x00\xa6\xf5\xff\x00\xa6\xf5\xff\x00\xa6\xf5\xff\x00\xa6\xf5\xff\x00\xa6\xf5\xff\x00\xa6\xf5\xff\x00\xa6\xf5\xff\x00\xa6\xf5\xff\x00\xa6\xf5\xff\x00\xa6\xf5\xff\x00\xa6\xf5\xff\x00\xa6\xf5\xff\x00\x00\x00\x00\x00h\x93\xff\x00h\x93\xff\x00h\x93\xff\x00h\x93\xff\x00h\x93\xff\x00h\x93\xff\x00h\x93\xff\x00h\x93\xff\x00h\x93\xff\x00h\x93\xff\x00h\x93\xff\x00h\x93\xff\x00h\x93\xff\x00h\x93\xff\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xc0\x00\x00\x00\x80\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x01\x00\x00\x00\x03\x00\x00\xff\xff\x00\x00'
    ,
    '\x00\x00\x01\x00\x01\x00\x10\x10\x00\x00\x01\x00 \x00h\x04\x00\x00\x16\x00\x00\x00(\x00\x00\x00\x10\x00\x00\x00 \x00\x00\x00\x01\x00 \x00\x00\x00\x00\x00@\x04\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x1a\x00\x00\x00\x1a\x00\x00\x00\x1a\x00\x00\x00\x1a\x00\x00\x00\x1a\x00\x00\x00\x1a\x00\x00\x00\x1a\x00\x00\x00\x1a\x00\x00\x00\x1a\x00\x00\x00\x1a\x00\x00\x00\x1a\x00\x00\x00\x1a\x00\x00\x00\x1a\x00\x00\x00\x1a\x00\x00\x00\x00\x00\x94\xbe\xff\x00\x94\xbe\xff\x00\x94\xbe\xff\x00\x94\xbe\xff\x00\x94\xbe\xff\x00\x94\xbe\xff\x00\x94\xbe\xff\x00\x94\xbe\xff\x00\x94\xbe\xff\x00\x94\xbe\xff\x00\x94\xbe\xff\x00\x94\xbe\xff\x00\x94\xbe\xff\x00\x94\xbe\xff\x00\x00\x00\x1a\x00Fe\xff\x00\x99\xc1\xff\x00\x99\xc1\xff\x00\x97\xbf\xff\x00\x92\xbb\xff\x00\x91\xbb\xff\x00\x96\xbe\xff\x00\x99\xc1\xff\x00\x99\xc1\xff\x00\x96\xbf\xff\x00\x91\xbb\xff\x00\x91\xbb\xff\x00\x96\xbf\xff\x00\x99\xc1\xff\x00\x99\xc1\xff\x00\x00\x00\x1a\x00Hh\xff\x00\x9e\xc5\xff\x00\x9e\xc5\xff\x00\x97\xc0\xff\xcb\xe7\xf0\xff\xff\xff\xff\xff\x14\x9d\xc3\xff\x00\x9d\xc4\xff\x00\x9e\xc5\xff\x00\x96\xbf\xff\xf7\xfb\xfd\xff\xf7\xfb\xfd\xff\x00\x96\xbf\xff\x00\x9e\xc5\xff\x00\x9e\xc5\xff\x00\x00\x00\x1a\x00Kl\xff\x00\xa4\xcb\xff\x00\xa4\xcb\xff\x00\x9c\xc4\xff\xc4\xe4\xef\xff\xff\xff\xff\xff\x12\x9f\xc5\xff\x00\xa3\xcb\xff\x00\xa4\xcb\xff\x00\x9a\xc3\xff\xf0\xf8\xfb\xff\xf0\xf8\xfb\xff\x00\x9a\xc3\xff\x00\xa4\xcb\xff\x00\xa4\xcb\xff\x00\x00\x00\x1a\x00Np\xff\x00\xab\xd0\xff\x00\xab\xd0\xff\x00\xa3\xca\xff\xc4\xe6\xf0\xff\xff\xff\xff\xff\t\x9e\xc7\xff\x00\xa4\xcb\xff\x00\xa5\xcc\xff\x00\x9c\xc5\xff\xed\xf7\xfa\xff\xf0\xf8\xfb\xff\x00\xa1\xc9\xff\x00\xab\xd0\xff\x00\xab\xd0\xff\x00\x00\x00\x1a\x00Qt\xff\x00\xb2\xd6\xff\x00\xb2\xd6\xff\x00\xaa\xd1\xff\xc4\xe8\xf2\xff\xff\xff\xff\xff\x91\xd3\xe6\xff\x9c\xd9\xea\xff\x9c\xd9\xea\xff\x94\xd5\xe7\xff\xf7\xfc\xfd\xff\xee\xf8\xfb\xff\x00\xa9\xd0\xff\x00\xb2\xd6\xff\x00\xb2\xd6\xff\x00\x00\x00\x1a\x00Uy\xff\x00\xb9\xdb\xff\x00\xb9\xdb\xff\x00\xb2\xd7\xff\xc4\xea\xf3\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xed\xf8\xfb\xff\x00\xb0\xd6\xff\x00\xb9\xdb\xff\x00\xb9\xdb\xff\x00\x00\x00\x1a\x00X}\xff\x00\xc0\xe1\xff\x00\xc0\xe1\xff\x00\xb9\xdd\xff\xc4\xec\xf5\xff\xff\xff\xff\xff\x02\xb1\xd8\xff\x00\xb7\xdc\xff\x00\xb7\xdc\xff\x00\xb1\xd9\xff\xeb\xf8\xfb\xff\xef\xfa\xfc\xff\x00\xb8\xdc\xff\x00\xc0\xe1\xff\x00\xc0\xe1\xff\x00\x00\x00\x1a\x00[\x82\xff\x00\xc8\xe6\xff\x00\xc8\xe6\xff\x00\xc1\xe3\xff\xc4\xee\xf7\xff\xff\xff\xff\xff\x12\xc3\xe3\xff\x00\xc7\xe6\xff\x00\xc8\xe6\xff\x00\xbf\xe2\xff\xf0\xfa\xfd\xff\xf0\xfa\xfd\xff\x00\xbf\xe2\xff\x00\xc8\xe6\xff\x00\xc8\xe6\xff\x00\x00\x00\x1a\x00_\x86\xff\x00\xce\xeb\xff\x00\xce\xeb\xff\x00\xc8\xe8\xff\xc4\xf0\xf8\xff\xff\xff\xff\xff\x12\xc9\xe9\xff\x00\xcd\xeb\xff\x00\xce\xeb\xff\x00\xc7\xe8\xff\xf0\xfb\xfd\xff\xf0\xfb\xfd\xff\x00\xc7\xe8\xff\x00\xce\xeb\xff\x00\xce\xeb\xff\x00\x00\x00\x1a\x00a\x8a\xff\x00\xd3\xef\xff\x00\xd3\xef\xff\x00\xcf\xed\xff\xd4\xf5\xfb\xff\xff\xff\xff\xff\x16\xd2\xef\xff\x00\xd3\xef\xff\x00\xd3\xef\xff\x00\xce\xed\xff\xff\xff\xff\xff\xff\xff\xff\xff\x00\xce\xed\xff\x00\xd3\xef\xff\x00\xd3\xef\xff\x00\x00\x00\x1a\x00d\x8e\xff\x00\xd8\xf2\xff\x00\xd8\xf2\xff\x00\xd7\xf2\xff\x00\xd4\xf1\xff\x00\xd3\xf0\xff\x00\xd6\xf1\xff\x00\xd8\xf2\xff\x00\xd8\xf2\xff\x00\xd6\xf1\xff\x00\xd3\xf0\xff\x00\xd3\xf0\xff\x00\xd6\xf1\xff\x00\xd8\xf2\xff\x00\xd8\xf2\xff\x00\x00\x00\x1a\x00f\x91\xff\x00\xdb\xf5\xff\x00\xdb\xf5\xff\x00\xdb\xf5\xff\x00\xdb\xf5\xff\x00\xdb\xf5\xff\x00\xdb\xf5\xff\x00\xdb\xf5\xff\x00\xdb\xf5\xff\x00\xdb\xf5\xff\x00\xdb\xf5\xff\x00\xdb\xf5\xff\x00\xdb\xf5\xff\x00\xdb\xf5\xff\x00\xdb\xf5\xff\x00\x00\x00\x00\x00h\x93\xff\x00h\x93\xff\x00h\x93\xff\x00h\x93\xff\x00h\x93\xff\x00h\x93\xff\x00h\x93\xff\x00h\x93\xff\x00h\x93\xff\x00h\x93\xff\x00h\x93\xff\x00h\x93\xff\x00h\x93\xff\x00h\x93\xff\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xc0\x00\x00\x00\x80\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x01\x00\x00\x00\x03\x00\x00\xff\xff\x00\x00'
    ,
    '\x00\x00\x01\x00\x01\x00\x10\x10\x00\x00\x01\x00 \x00h\x04\x00\x00\x16\x00\x00\x00(\x00\x00\x00\x10\x00\x00\x00 \x00\x00\x00\x01\x00 \x00\x00\x00\x00\x00@\x04\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x1a\x00\x00\x00\x1a\x00\x00\x00\x1a\x00\x00\x00\x1a\x00\x00\x00\x1a\x00\x00\x00\x1a\x00\x00\x00\x1a\x00\x00\x00\x1a\x00\x00\x00\x1a\x00\x00\x00\x1a\x00\x00\x00\x1a\x00\x00\x00\x1a\x00\x00\x00\x1a\x00\x00\x00\x1a\x00\x00\x00\x009\xa0\x05\xff9\xa0\x05\xff9\xa0\x05\xff9\xa0\x05\xff9\xa0\x05\xff9\xa0\x05\xff9\xa0\x05\xff9\xa0\x05\xff9\xa0\x05\xff9\xa0\x05\xff9\xa0\x05\xff9\xa0\x05\xff9\xa0\x05\xff9\xa0\x05\xff\x00\x00\x00\x1a\x00Fe\xff9\xa3\x07\xff9\xa3\x07\xff7\xa1\x07\xff4\x9c\x06\xff3\x9b\x06\xff7\xa0\x07\xff9\xa3\x07\xff9\xa3\x07\xff7\xa0\x07\xff3\x9b\x06\xff3\x9b\x06\xff7\xa0\x07\xff9\xa3\x07\xff9\xa3\x07\xff\x00\x00\x00\x1a\x00Hh\xff9\xa8\n\xff9\xa8\n\xff4\xa2\t\xff\xd4\xe9\xcc\xff\xff\xff\xff\xffC\xa7\x1b\xff8\xa7\n\xff9\xa8\n\xff3\xa0\t\xff\xf8\xfc\xf7\xff\xf8\xfc\xf7\xff3\xa0\t\xff9\xa8\n\xff9\xa8\n\xff\x00\x00\x00\x1a\x00Kl\xff9\xac\r\xff9\xac\r\xff2\xa4\x0b\xff\xcd\xe6\xc7\xff\xff\xff\xff\xff>\xa7\x1a\xff8\xab\r\xff9\xac\r\xff1\xa2\x0b\xff\xf2\xf8\xf0\xff\xf2\xf8\xf0\xff1\xa2\x0b\xff9\xac\r\xff9\xac\r\xff\x00\x00\x00\x1a\x00Np\xff9\xb2\x11\xff9\xb2\x11\xff2\xaa\x0f\xff\xcd\xe8\xc7\xff\xff\xff\xff\xff3\xa6\x14\xff4\xac\x0f\xff4\xac\x0f\xff-\xa4\r\xff\xef\xf8\xee\xff\xf2\xf9\xf1\xff1\xa9\x0e\xff9\xb2\x11\xff9\xb2\x11\xff\x00\x00\x00\x1a\x00Qt\xff9\xb7\x14\xff9\xb7\x14\xff2\xb0\x12\xff\xcd\xe9\xc8\xff\xff\xff\xff\xff\xa0\xd6\x96\xff\xab\xdc\xa1\xff\xab\xdc\xa1\xff\xa3\xd7\x99\xff\xf8\xfc\xf7\xff\xf0\xf8\xef\xff1\xae\x12\xff9\xb7\x14\xff9\xb7\x14\xff\x00\x00\x00\x1a\x00Uy\xff9\xbd\x18\xff9\xbd\x18\xff2\xb6\x15\xff\xcd\xeb\xc8\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xef\xf9\xee\xff1\xb5\x14\xff9\xbd\x18\xff9\xbd\x18\xff\x00\x00\x00\x1a\x00X}\xff9\xc2\x1b\xff9\xc2\x1b\xff2\xbb\x17\xff\xcd\xec\xc9\xff\xff\xff\xff\xff,\xb4\x15\xff0\xb9\x16\xff1\xb9\x16\xff+\xb3\x13\xff\xee\xf8\xec\xff\xf1\xfa\xf0\xff1\xba\x17\xff9\xc2\x1b\xff9\xc2\x1b\xff\x00\x00\x00\x1a\x00[\x82\xff9\xc9\x1f\xff9\xc9\x1f\xff2\xc2\x1b\xff\xcd\xee\xc9\xff\xff\xff\xff\xff?\xc3)\xff8\xc8\x1f\xff9\xc9\x1f\xff1\xc0\x1a\xff\xf2\xfa\xf1\xff\xf2\xfa\xf1\xff1\xc0\x1a\xff9\xc9\x1f\xff9\xc9\x1f\xff\x00\x00\x00\x1a\x00_\x86\xff:\xcd"\xff:\xcd"\xff3\xc7\x1e\xff\xcd\xef\xca\xff\xff\xff\xff\xff?\xc8,\xff9\xcc"\xff:\xcd"\xff2\xc5\x1d\xff\xf2\xfb\xf1\xff\xf2\xfb\xf1\xff2\xc5\x1d\xff:\xcd"\xff:\xcd"\xff\x00\x00\x00\x1a\x00a\x8a\xff:\xd2%\xff:\xd2%\xff5\xce!\xff\xdb\xf5\xd8\xff\xff\xff\xff\xffE\xd14\xff9\xd2%\xff:\xd2%\xff4\xcd!\xff\xff\xff\xff\xff\xff\xff\xff\xff4\xcd!\xff:\xd2%\xff:\xd2%\xff\x00\x00\x00\x1a\x00d\x8e\xff:\xd5(\xff:\xd5(\xff8\xd4\'\xff5\xd1$\xff4\xd0#\xff8\xd3&\xff:\xd5(\xff:\xd5(\xff8\xd3&\xff4\xd0#\xff4\xd0#\xff8\xd3&\xff:\xd5(\xff:\xd5(\xff\x00\x00\x00\x1a\x00f\x91\xff:\xd8)\xff:\xd8)\xff:\xd8)\xff:\xd8)\xff:\xd8)\xff:\xd8)\xff:\xd8)\xff:\xd8)\xff:\xd8)\xff:\xd8)\xff:\xd8)\xff:\xd8)\xff:\xd8)\xff:\xd8)\xff\x00\x00\x00\x00\x00h\x93\xff\x00h\x93\xff\x00h\x93\xff\x00h\x93\xff\x00h\x93\xff\x00h\x93\xff\x00h\x93\xff\x00h\x93\xff\x00h\x93\xff\x00h\x93\xff\x00h\x93\xff\x00h\x93\xff\x00h\x93\xff\x00h\x93\xff\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xc0\x00\x00\x00\x80\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x01\x00\x00\x00\x03\x00\x00\xff\xff\x00\x00'
    ,
    '\x00\x00\x01\x00\x01\x00\x10\x10\x00\x00\x01\x00 \x00h\x04\x00\x00\x16\x00\x00\x00(\x00\x00\x00\x10\x00\x00\x00 \x00\x00\x00\x01\x00 \x00\x00\x00\x00\x00@\x04\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x1a\x00\x00\x00\x1a\x00\x00\x00\x1a\x00\x00\x00\x1a\x00\x00\x00\x1a\x00\x00\x00\x1a\x00\x00\x00\x1a\x00\x00\x00\x1a\x00\x00\x00\x1a\x00\x00\x00\x1a\x00\x00\x00\x1a\x00\x00\x00\x1a\x00\x00\x00\x1a\x00\x00\x00\x1a\x00\x00\x00\x00\xa1h\x03\xff\xa1h\x03\xff\xa1h\x03\xff\xa1h\x03\xff\xa1h\x03\xff\xa1h\x03\xff\xa1h\x03\xff\xa1h\x03\xff\xa1h\x03\xff\xa1h\x03\xff\xa1h\x03\xff\xa1h\x03\xff\xa1h\x03\xff\xa1h\x03\xff\x00\x00\x00\x1a\x00Fe\xff\xa6m\x03\xff\xa6m\x03\xff\xa4k\x03\xff\x9fe\x03\xff\x9ee\x03\xff\xa3j\x03\xff\xa6m\x03\xff\xa6m\x03\xff\xa3j\x03\xff\x9ee\x03\xff\x9ee\x03\xff\xa3j\x03\xff\xa6m\x03\xff\xa6m\x03\xff\x00\x00\x00\x1a\x00Hh\xff\xads\x02\xff\xads\x02\xff\xa7l\x02\xff\xea\xde\xcb\xff\xff\xff\xff\xff\xabu\x16\xff\xacr\x02\xff\xads\x02\xff\xa6k\x02\xff\xfc\xfa\xf7\xff\xfc\xfa\xf7\xff\xa6k\x02\xff\xads\x02\xff\xads\x02\xff\x00\x00\x00\x1a\x00Kl\xff\xb4y\x02\xff\xb4y\x02\xff\xacp\x02\xff\xe8\xda\xc4\xff\xff\xff\xff\xff\xafu\x13\xff\xb3x\x02\xff\xb4y\x02\xff\xabn\x02\xff\xf9\xf5\xf0\xff\xf9\xf5\xf0\xff\xabn\x02\xff\xb4y\x02\xff\xb4y\x02\xff\x00\x00\x00\x1a\x00Np\xff\xbc\x80\x02\xff\xbc\x80\x02\xff\xb5w\x02\xff\xeb\xdc\xc4\xff\xff\xff\xff\xff\xb1s\n\xff\xb6x\x02\xff\xb6y\x02\xff\xafo\x01\xff\xf8\xf4\xed\xff\xfa\xf6\xf0\xff\xb3u\x02\xff\xbc\x80\x02\xff\xbc\x80\x02\xff\x00\x00\x00\x1a\x00Qt\xff\xc4\x87\x02\xff\xc4\x87\x02\xff\xbd~\x02\xff\xed\xdd\xc4\xff\xff\xff\xff\xff\xdd\xbe\x91\xff\xe1\xc7\x9c\xff\xe1\xc7\x9c\xff\xde\xc0\x94\xff\xfc\xfa\xf7\xff\xfa\xf5\xee\xff\xbc|\x02\xff\xc4\x87\x02\xff\xc4\x87\x02\xff\x00\x00\x00\x1a\x00Uy\xff\xce\x8f\x01\xff\xce\x8f\x01\xff\xc8\x86\x01\xff\xf0\xdf\xc4\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xfa\xf5\xed\xff\xc7\x84\x01\xff\xce\x8f\x01\xff\xce\x8f\x01\xff\x00\x00\x00\x1a\x00X}\xff\xd6\x96\x01\xff\xd6\x96\x01\xff\xd1\x8d\x01\xff\xf2\xe1\xc4\xff\xff\xff\xff\xff\xcb\x82\x03\xff\xcf\x8a\x01\xff\xd0\x8a\x01\xff\xcb\x82\x01\xff\xfa\xf4\xeb\xff\xfb\xf6\xef\xff\xd0\x8b\x01\xff\xd6\x96\x01\xff\xd6\x96\x01\xff\x00\x00\x00\x1a\x00[\x82\xff\xde\x9d\x01\xff\xde\x9d\x01\xff\xda\x94\x01\xff\xf4\xe3\xc4\xff\xff\xff\xff\xff\xdb\x99\x13\xff\xde\x9c\x01\xff\xde\x9d\x01\xff\xd9\x92\x01\xff\xfc\xf7\xf0\xff\xfc\xf7\xf0\xff\xd9\x92\x01\xff\xde\x9d\x01\xff\xde\x9d\x01\xff\x00\x00\x00\x1a\x00_\x86\xff\xe5\xa4\x01\xff\xe5\xa4\x01\xff\xe2\x9c\x01\xff\xf7\xe4\xc4\xff\xff\xff\xff\xff\xe2\x9e\x13\xff\xe5\xa3\x01\xff\xe5\xa4\x01\xff\xe1\x9a\x01\xff\xfd\xf8\xf0\xff\xfd\xf8\xf0\xff\xe1\x9a\x01\xff\xe5\xa4\x01\xff\xe5\xa4\x01\xff\x00\x00\x00\x1a\x00a\x8a\xff\xec\xa9\x00\xff\xec\xa9\x00\xff\xea\xa3\x00\xff\xfb\xed\xd4\xff\xff\xff\xff\xff\xeb\xa8\x16\xff\xec\xa8\x00\xff\xec\xa9\x00\xff\xea\xa1\x00\xff\xff\xff\xff\xff\xff\xff\xff\xff\xea\xa1\x00\xff\xec\xa9\x00\xff\xec\xa9\x00\xff\x00\x00\x00\x1a\x00d\x8e\xff\xf1\xae\x00\xff\xf1\xae\x00\xff\xf0\xac\x00\xff\xef\xa7\x00\xff\xef\xa6\x00\xff\xf0\xab\x00\xff\xf1\xae\x00\xff\xf1\xae\x00\xff\xf0\xab\x00\xff\xef\xa6\x00\xff\xef\xa6\x00\xff\xf0\xab\x00\xff\xf1\xae\x00\xff\xf1\xae\x00\xff\x00\x00\x00\x1a\x00f\x91\xff\xf5\xb2\x00\xff\xf5\xb2\x00\xff\xf5\xb2\x00\xff\xf5\xb2\x00\xff\xf5\xb2\x00\xff\xf5\xb2\x00\xff\xf5\xb2\x00\xff\xf5\xb2\x00\xff\xf5\xb2\x00\xff\xf5\xb2\x00\xff\xf5\xb2\x00\xff\xf5\xb2\x00\xff\xf5\xb2\x00\xff\xf5\xb2\x00\xff\x00\x00\x00\x00\x00h\x93\xff\x00h\x93\xff\x00h\x93\xff\x00h\x93\xff\x00h\x93\xff\x00h\x93\xff\x00h\x93\xff\x00h\x93\xff\x00h\x93\xff\x00h\x93\xff\x00h\x93\xff\x00h\x93\xff\x00h\x93\xff\x00h\x93\xff\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xc0\x00\x00\x00\x80\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x01\x00\x00\x00\x03\x00\x00\xff\xff\x00\x00'
    ,
    '\x00\x00\x01\x00\x01\x00\x10\x10\x00\x00\x01\x00 \x00h\x04\x00\x00\x16\x00\x00\x00(\x00\x00\x00\x10\x00\x00\x00 \x00\x00\x00\x01\x00 \x00\x00\x00\x00\x00@\x04\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x1a\x00\x00\x00\x1a\x00\x00\x00\x1a\x00\x00\x00\x1a\x00\x00\x00\x1a\x00\x00\x00\x1a\x00\x00\x00\x1a\x00\x00\x00\x1a\x00\x00\x00\x1a\x00\x00\x00\x1a\x00\x00\x00\x1a\x00\x00\x00\x1a\x00\x00\x00\x1a\x00\x00\x00\x1a\x00\x00\x00\x00\xa1\x056\xff\xa1\x056\xff\xa1\x056\xff\xa1\x056\xff\xa1\x056\xff\xa1\x056\xff\xa1\x056\xff\xa1\x056\xff\xa1\x056\xff\xa1\x056\xff\xa1\x056\xff\xa1\x056\xff\xa1\x056\xff\xa1\x056\xff\x00\x00\x00\x1a\x00Fe\xff\xa6\x082\xff\xa6\x082\xff\xa4\x080\xff\x9f\x07-\xff\x9e\x07-\xff\xa3\x080\xff\xa6\x082\xff\xa6\x082\xff\xa3\x080\xff\x9e\x07-\xff\x9e\x07-\xff\xa3\x080\xff\xa6\x082\xff\xa6\x082\xff\x00\x00\x00\x1a\x00Hh\xff\xad\x0b.\xff\xad\x0b.\xff\xa7\n*\xff\xea\xcc\xd2\xff\xff\xff\xff\xff\xab\x1c:\xff\xac\x0b.\xff\xad\x0b.\xff\xa6\n)\xff\xfc\xf7\xf8\xff\xfc\xf7\xf8\xff\xa6\n)\xff\xad\x0b.\xff\xad\x0b.\xff\x00\x00\x00\x1a\x00Kl\xff\xb4\x0f)\xff\xb4\x0f)\xff\xac\r$\xff\xe8\xc7\xcb\xff\xff\xff\xff\xff\xaf\x1c2\xff\xb3\x0f)\xff\xb4\x0f)\xff\xab\r#\xff\xf9\xf0\xf1\xff\xf9\xf0\xf1\xff\xab\r#\xff\xb4\x0f)\xff\xb4\x0f)\xff\x00\x00\x00\x1a\x00Np\xff\xbc\x12$\xff\xbc\x12$\xff\xb5\x10\x1f\xff\xeb\xc7\xca\xff\xff\xff\xff\xff\xb1\x15#\xff\xb6\x10 \xff\xb6\x10 \xff\xaf\x0e\x1c\xff\xf8\xee\xee\xff\xfa\xf1\xf1\xff\xb3\x0f\x1e\xff\xbc\x12$\xff\xbc\x12$\xff\x00\x00\x00\x1a\x00Qt\xff\xc4\x15\x1f\xff\xc4\x15\x1f\xff\xbd\x13\x1b\xff\xed\xc8\xc9\xff\xff\xff\xff\xff\xdd\x96\x99\xff\xe1\xa1\xa4\xff\xe1\xa1\xa4\xff\xde\x99\x9b\xff\xfc\xf7\xf7\xff\xfa\xef\xef\xff\xbc\x12\x1a\xff\xc4\x15\x1f\xff\xc4\x15\x1f\xff\x00\x00\x00\x1a\x00Uy\xff\xce\x1a\x19\xff\xce\x1a\x19\xff\xc8\x17\x16\xff\xf0\xc9\xc8\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xfa\xee\xee\xff\xc7\x16\x15\xff\xce\x1a\x19\xff\xce\x1a\x19\xff\x00\x00\x00\x1a\x00X}\xff\xd6\x1e\x14\xff\xd6\x1e\x14\xff\xd1\x1a\x12\xff\xf2\xc9\xc8\xff\xff\xff\xff\xff\xcb\x17\x11\xff\xcf\x19\x11\xff\xd0\x19\x11\xff\xcb\x15\x0f\xff\xfa\xec\xec\xff\xfb\xf0\xf0\xff\xd0\x19\x12\xff\xd6\x1e\x14\xff\xd6\x1e\x14\xff\x00\x00\x00\x1a\x00[\x82\xff\xde"\x0f\xff\xde"\x0f\xff\xda\x1e\r\xff\xf4\xca\xc7\xff\xff\xff\xff\xff\xdb,\x1c\xff\xde"\x0f\xff\xde"\x0f\xff\xd9\x1d\r\xff\xfc\xf1\xf0\xff\xfc\xf1\xf0\xff\xd9\x1d\r\xff\xde"\x0f\xff\xde"\x0f\xff\x00\x00\x00\x1a\x00_\x86\xff\xe5%\x0b\xff\xe5%\x0b\xff\xe2 \t\xff\xf7\xca\xc5\xff\xff\xff\xff\xff\xe2.\x19\xff\xe5$\x0b\xff\xe5%\x0b\xff\xe1\x1f\t\xff\xfd\xf1\xf0\xff\xfd\xf1\xf0\xff\xe1\x1f\t\xff\xe5%\x0b\xff\xe5%\x0b\xff\x00\x00\x00\x1a\x00a\x8a\xff\xec(\x06\xff\xec(\x06\xff\xea$\x05\xff\xfb\xd9\xd5\xff\xff\xff\xff\xff\xeb6\x1b\xff\xec(\x06\xff\xec(\x06\xff\xea#\x05\xff\xff\xff\xff\xff\xff\xff\xff\xff\xea#\x05\xff\xec(\x06\xff\xec(\x06\xff\x00\x00\x00\x1a\x00d\x8e\xff\xf1+\x03\xff\xf1+\x03\xff\xf0*\x03\xff\xef\'\x03\xff\xef&\x03\xff\xf0)\x03\xff\xf1+\x03\xff\xf1+\x03\xff\xf0)\x03\xff\xef&\x03\xff\xef&\x03\xff\xf0)\x03\xff\xf1+\x03\xff\xf1+\x03\xff\x00\x00\x00\x1a\x00f\x91\xff\xf5-\x00\xff\xf5-\x00\xff\xf5-\x00\xff\xf5-\x00\xff\xf5-\x00\xff\xf5-\x00\xff\xf5-\x00\xff\xf5-\x00\xff\xf5-\x00\xff\xf5-\x00\xff\xf5-\x00\xff\xf5-\x00\xff\xf5-\x00\xff\xf5-\x00\xff\x00\x00\x00\x00\x00h\x93\xff\x00h\x93\xff\x00h\x93\xff\x00h\x93\xff\x00h\x93\xff\x00h\x93\xff\x00h\x93\xff\x00h\x93\xff\x00h\x93\xff\x00h\x93\xff\x00h\x93\xff\x00h\x93\xff\x00h\x93\xff\x00h\x93\xff\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xc0\x00\x00\x00\x80\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x01\x00\x00\x00\x03\x00\x00\xff\xff\x00\x00'
    ,
    '\x00\x00\x01\x00\x01\x00\x10\x10\x00\x00\x01\x00 \x00h\x04\x00\x00\x16\x00\x00\x00(\x00\x00\x00\x10\x00\x00\x00 \x00\x00\x00\x01\x00 \x00\x00\x00\x00\x00@\x04\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x1a\x00\x00\x00\x1a\x00\x00\x00\x1a\x00\x00\x00\x1a\x00\x00\x00\x1a\x00\x00\x00\x1a\x00\x00\x00\x1a\x00\x00\x00\x1a\x00\x00\x00\x1a\x00\x00\x00\x1a\x00\x00\x00\x1a\x00\x00\x00\x1a\x00\x00\x00\x1a\x00\x00\x00\x1a\x00\x00\x00\x00444\xff444\xff444\xff444\xff444\xff444\xff444\xff444\xff444\xff444\xff444\xff444\xff444\xff444\xff\x00\x00\x00\x1a\x00Fe\xff888\xff888\xff666\xff333\xff222\xff666\xff888\xff888\xff666\xff222\xff222\xff666\xff888\xff888\xff\x00\x00\x00\x1a\x00Hh\xff;;;\xff;;;\xff666\xff\xd4\xd4\xd4\xff\xff\xff\xff\xffEEE\xff:::\xff;;;\xff555\xff\xf8\xf8\xf8\xff\xf8\xf8\xf8\xff555\xff;;;\xff;;;\xff\x00\x00\x00\x1a\x00Kl\xff@@@\xff@@@\xff999\xff\xcf\xcf\xcf\xff\xff\xff\xff\xffDDD\xff???\xff@@@\xff888\xff\xf2\xf2\xf2\xff\xf2\xf2\xf2\xff888\xff@@@\xff@@@\xff\x00\x00\x00\x1a\x00Np\xffDDD\xffDDD\xff===\xff\xcf\xcf\xcf\xff\xff\xff\xff\xff===\xff>>>\xff>>>\xff777\xff\xf0\xf0\xf0\xff\xf3\xf3\xf3\xff;;;\xffDDD\xffDDD\xff\x00\x00\x00\x1a\x00Qt\xffIII\xffIII\xffAAA\xff\xd0\xd0\xd0\xff\xff\xff\xff\xff\xa6\xa6\xa6\xff\xb0\xb0\xb0\xff\xb0\xb0\xb0\xff\xa8\xa8\xa8\xff\xf8\xf8\xf8\xff\xf1\xf1\xf1\xff@@@\xffIII\xffIII\xff\x00\x00\x00\x1a\x00Uy\xffNNN\xffNNN\xffFFF\xff\xd1\xd1\xd1\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xf1\xf1\xf1\xffEEE\xffNNN\xffNNN\xff\x00\x00\x00\x1a\x00X}\xffSSS\xffSSS\xffKKK\xff\xd2\xd2\xd2\xff\xff\xff\xff\xffAAA\xffHHH\xffHHH\xffAAA\xff\xef\xef\xef\xff\xf2\xf2\xf2\xffIII\xffSSS\xffSSS\xff\x00\x00\x00\x1a\x00[\x82\xffWWW\xffWWW\xffOOO\xff\xd3\xd3\xd3\xff\xff\xff\xff\xffXXX\xffVVV\xffWWW\xffMMM\xff\xf3\xf3\xf3\xff\xf3\xf3\xf3\xffMMM\xffWWW\xffWWW\xff\x00\x00\x00\x1a\x00_\x86\xff\\\\\\\xff\\\\\\\xffSSS\xff\xd4\xd4\xd4\xff\xff\xff\xff\xff[[[\xff[[[\xff\\\\\\\xffQQQ\xff\xf4\xf4\xf4\xff\xf4\xf4\xf4\xffQQQ\xff\\\\\\\xff\\\\\\\xff\x00\x00\x00\x1a\x00a\x8a\xff___\xff___\xffXXX\xff\xe0\xe0\xe0\xff\xff\xff\xff\xffddd\xff^^^\xff___\xffWWW\xff\xff\xff\xff\xff\xff\xff\xff\xffWWW\xff___\xff___\xff\x00\x00\x00\x1a\x00d\x8e\xffccc\xffccc\xffaaa\xff\\\\\\\xff[[[\xff```\xffccc\xffccc\xff```\xffZZZ\xffZZZ\xff```\xffccc\xffccc\xff\x00\x00\x00\x1a\x00f\x91\xffeee\xffeee\xffeee\xffeee\xffeee\xffeee\xffeee\xffeee\xffeee\xffeee\xffeee\xffeee\xffeee\xffeee\xff\x00\x00\x00\x00\x00h\x93\xff\x00h\x93\xff\x00h\x93\xff\x00h\x93\xff\x00h\x93\xff\x00h\x93\xff\x00h\x93\xff\x00h\x93\xff\x00h\x93\xff\x00h\x93\xff\x00h\x93\xff\x00h\x93\xff\x00h\x93\xff\x00h\x93\xff\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xc0\x00\x00\x00\x80\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x01\x00\x00\x00\x03\x00\x00\xff\xff\x00\x00'
]

########NEW FILE########
__FILENAME__ = lang
# -*- coding: utf-8 -*-
#
# author: oldj
# blog: http://oldj.net
# email: oldj.wu@gmail.com
#


lang = {
    "common_hosts": u"公用 hosts",
    "origin_hosts": u"当前系统 hosts",
    "online_hosts": u"在线方案",
    "local_hosts": u"本地方案",
}

def trans(key):

    return lang.get(key) or "N/A"

########NEW FILE########
__FILENAME__ = MainFrame
# -*- coding: utf-8 -*-
#
# author: oldj
# blog: http://oldj.net
# email: oldj.wu@gmail.com
#

import os
import sys
import glob
import simplejson as json
import wx
from wx import stc
import ui
import urllib
import re
import traceback
import random
import Queue
import time
from Hosts import Hosts
from TaskbarIcon import TaskBarIcon
from BackThreads import BackThreads
import common_operations as co
import lang

sys_type = co.getSystemType()

if sys_type == "linux":
    # Linux
    try:
        import pynotify
    except ImportError:
        pynotify = None
elif sys_type == "mac":
    # Mac
    import gntp.notifier

    growl = gntp.notifier.GrowlNotifier(
        applicationName="SwitchHosts!",
        notifications=["New Updates", "New Messages"],
        defaultNotifications=["New Messages"],
        hostname="127.0.0.1",  # Defaults to localhost
        # password="" # Defaults to a blank password
    )
    try:
        growl.register()
        has_growl = True
    except Exception:
        has_growl = False


class MainFrame(ui.Frame):

    def __init__(self, mainjob, instance_name,
        parent=None, id=wx.ID_ANY, title=None, pos=wx.DefaultPosition,
        size=wx.DefaultSize,
        style=wx.DEFAULT_FRAME_STYLE,
        version=None, working_path=None,
        taskbar_icon=None,
    ):
        u""""""

        self.mainjob = mainjob
        self.instance_name = instance_name
        self.version = version
        self.default_title = "SwitchHosts! %s" % self.version
        self.sudo_password = ""
        self.is_running = True

        ui.Frame.__init__(self, parent, id,
            title or self.default_title, pos, size, style)

        self.taskbar_icon = taskbar_icon or TaskBarIcon(self)
        if taskbar_icon:
            self.taskbar_icon.setMainFrame(self)

        self.latest_stable_version = "0"
        self.__sys_hosts_path = None
        self.local_encoding = co.getLocalEncoding()
        self.sys_type = co.getSystemType()

        if working_path:
            working_path = working_path.decode(self.local_encoding)
            self.working_path = working_path
            self.configs_path = os.path.join(self.working_path, "configs.json")
            self.hosts_path = os.path.join(self.working_path, "hosts")
            if not os.path.isdir(self.hosts_path):
                os.makedirs(self.hosts_path)

        self.active_fn = os.path.join(self.working_path, ".active")
        self.task_qu = Queue.Queue(4096)
        self.startBackThreads(2)
        self.makeHostsContextMenu()

        self.init2()
        self.initBind()

        # self.task_qu.put(self.chkActive)

    def init2(self):

        self.showing_rnd_id = random.random()
        self.is_switching_text = False
        self.current_using_hosts = None
        self.current_showing_hosts = None
        self.current_tree_hosts = None
        self.current_dragging_hosts = None
        self.current_tree_item = None  # 当前选中的树无素

        self.origin_hostses = []
        self.common_hostses = []
        self.hostses = []
        self.fn_common_hosts = "COMMON.hosts"

        self.configs = {}
        self.loadConfigs()

        common_host_file_path = os.path.join(self.hosts_path, self.fn_common_hosts)
        if not os.path.isfile(common_host_file_path):
            common_file = open(common_host_file_path, "w")
            common_file.write("# common")
            common_file.close()

        hosts = Hosts(path=common_host_file_path, is_common=True)
        self.addHosts(hosts)

        self.getSystemHosts()
        self.scanSavedHosts()

        if not os.path.isdir(self.hosts_path):
            os.makedirs(self.hosts_path)

    def initBind(self):
        u"""初始化时绑定事件"""

        self.Bind(wx.EVT_CLOSE, self.OnClose)
        self.Bind(wx.EVT_MENU, self.OnExit, id=wx.ID_EXIT)
        self.Bind(wx.EVT_MENU, self.OnAbout, id=wx.ID_ABOUT)
        self.Bind(wx.EVT_MENU, self.OnHomepage, self.m_menuItem_homepage)
        self.Bind(wx.EVT_MENU, self.OnFeedback, self.m_menuItem_feedback)
        self.Bind(wx.EVT_MENU, self.OnChkUpdate, self.m_menuItem_chkUpdate)
        self.Bind(wx.EVT_MENU, self.OnNew, self.m_menuItem_new)
        self.Bind(wx.EVT_MENU, self.OnDel, id=wx.ID_DELETE)
        self.Bind(wx.EVT_MENU, self.OnApply, id=wx.ID_APPLY)
        self.Bind(wx.EVT_MENU, self.OnEdit, id=wx.ID_EDIT)
        self.Bind(wx.EVT_MENU, self.OnRefresh, id=wx.ID_REFRESH)
        self.Bind(wx.EVT_MENU, self.OnExport, self.m_menuItem_export)
        self.Bind(wx.EVT_MENU, self.OnImport, self.m_menuItem_import)
        self.Bind(wx.EVT_MENU, self.OnDonate, self.m_menuItem_donate)
        self.Bind(wx.EVT_BUTTON, self.OnNew, self.m_btn_add)
        self.Bind(wx.EVT_BUTTON, self.OnApply, id=wx.ID_APPLY)
        self.Bind(wx.EVT_BUTTON, self.OnDel, id=wx.ID_DELETE)
        self.Bind(wx.EVT_BUTTON, self.OnRefresh, id=wx.ID_REFRESH)
        self.Bind(wx.EVT_BUTTON, self.OnEdit, id=wx.ID_EDIT)
        self.Bind(wx.EVT_TREE_SEL_CHANGED, self.OnTreeSelectionChange, self.m_tree)
        self.Bind(wx.EVT_TREE_ITEM_RIGHT_CLICK, self.OnTreeRClick, self.m_tree)
        self.Bind(wx.EVT_TREE_ITEM_ACTIVATED, self.OnTreeActive, self.m_tree)
        self.Bind(wx.EVT_TREE_END_LABEL_EDIT, self.OnRenameEnd, self.m_tree)
        self.Bind(wx.EVT_TREE_BEGIN_DRAG, self.OnTreeBeginDrag, self.m_tree)
        self.Bind(wx.EVT_TREE_END_DRAG, self.OnTreeEndDrag, self.m_tree)
        self.Bind(stc.EVT_STC_CHANGE, self.OnHostsChange, id=self.ID_HOSTS_TEXT)

    def startBackThreads(self, count=1):

        self.back_threads = []
        for i in xrange(count):
            t = BackThreads(task_qu=self.task_qu)
            t.start()
            self.back_threads.append(t)

    def stopBackThreads(self):

        for t in self.back_threads:
            t.stop()

    def makeHostsContextMenu(self):

        self.hosts_item_menu = wx.Menu()
        self.hosts_item_menu.Append(wx.ID_APPLY, u"切换到当前hosts")
        self.hosts_item_menu.Append(wx.ID_EDIT, u"编辑")
        self.hosts_item_menu.AppendMenu(-1, u"图标", self.makeSubIconMenu())

        self.hosts_item_menu.AppendSeparator()
        self.hosts_item_menu.Append(wx.ID_REFRESH, u"刷新")
        self.hosts_item_menu.Append(wx.ID_DELETE, u"删除")

    def makeSubIconMenu(self):
        u"""生成图标子菜单"""

        menu = wx.Menu()

        def _f(i):
            return lambda e: self.setHostsIcon(e, i)

        icons_length = len(co.ICONS)
        for i in range(icons_length):
            item_id = wx.NewId()
            mitem = wx.MenuItem(menu, item_id, u"图标#%d" % (i + 1))
            mitem.SetBitmap(co.GetMondrianBitmap(i))
            menu.AppendItem(mitem)

            self.Bind(wx.EVT_MENU, _f(i), id=item_id)

        return menu

    def setHostsIcon(self, event=None, i=0):
        u"""图标子菜单，点击动作的响应函数"""

        hosts = self.current_showing_hosts
        if not hosts:
            return

        hosts.icon_idx = i
        self.updateHostsIcon(hosts)
        hosts.save()

    def scanSavedHosts(self):
        u"""扫描目前保存的各个hosts"""

        fns = glob.glob(os.path.join(self.hosts_path, "*.hosts"))
        fns = [os.path.split(fn)[1] for fn in fns]
        if self.fn_common_hosts in fns:
            fns.remove(self.fn_common_hosts)

        cfg_hostses = self.configs.get("hostses", [])
        # 移除不存在的 hosts
        tmp_hosts = []
        for fn in cfg_hostses:
            if fn in fns:
                tmp_hosts.append(fn)
        cfg_hostses = tmp_hosts

        # 添加新的 hosts
        for fn in fns:
            if fn not in cfg_hostses:
                cfg_hostses.append(fn)
        self.configs["hostses"] = cfg_hostses
        self.saveConfigs()

        for fn in self.configs["hostses"]:
            path = os.path.join(self.hosts_path, fn)
            hosts = Hosts(path)
            if hosts.content:
                pass
            self.addHosts(hosts)

    def setHostsDir(self):
        pass

    @property
    def sys_hosts_path(self):
        u"""取得系统 hosts 文件的路径"""

        if not self.__sys_hosts_path:

            if os.name == "nt":
                systemroot = os.environ.get("SYSTEMROOT", "C:\\Windows")
                path = "%s\\System32\\drivers\\etc\\hosts" % systemroot
            else:
                path = "/etc/hosts"

            self.__sys_hosts_path = path if os.path.isfile(path) else None

        return self.__sys_hosts_path

    def getSystemHosts(self):

        path = self.sys_hosts_path
        if path:
            hosts = Hosts(path=path, title=lang.trans("origin_hosts"), is_origin=True)
            self.origin_hostses = [hosts]
            self.addHosts(hosts)
            self.highLightHosts(hosts)
            self.updateBtnStatus(hosts)

    def showHosts(self, hosts):

        self.showing_rnd_id = random.random()

        content = hosts.content if not hosts.is_loading else "loading..."
        self.is_switching_text = True
        self.m_textCtrl_content.SetReadOnly(False)
        self.m_textCtrl_content.SetValue(content)
        self.m_textCtrl_content.SetReadOnly(not self.getHostsAttr(hosts, "is_content_edit_able"))
        self.is_switching_text = False

        if self.current_showing_hosts:
            self.m_tree.SetItemBackgroundColour(self.current_showing_hosts.tree_item_id, None)
        self.m_tree.SetItemBackgroundColour(hosts.tree_item_id, "#ccccff")

        self.current_showing_hosts = hosts

    def tryToShowHosts(self, hosts):

        if hosts == self.current_showing_hosts:
            self.showHosts(hosts)

    def tryToSaveBySudoPassword(self, hosts, common_hosts):

        if not self.sudo_password:
            # 尝试获取sudo密码
            pswd = None
            dlg = wx.PasswordEntryDialog(None, u"请输入sudo密码：", u"需要管理员权限",
                style=wx.OK|wx.CANCEL
            )
            if dlg.ShowModal() == wx.ID_OK:
                pswd = dlg.GetValue().strip()

            dlg.Destroy()

            if not pswd:
                return False

            self.sudo_password = pswd

        #尝试通过sudo密码保存
        try:
            hosts.save(path=self.sys_hosts_path, common=common_hosts,
                sudo_password=self.sudo_password)
            return True
        except Exception:
            print(traceback.format_exc())

        return False

    def useHosts(self, hosts):

        if hosts.is_loading:
            wx.MessageBox(u"当前 hosts 内容正在下载中，请稍后再试...")
            return

        msg = None
        is_success = False
        common_hosts = None

        try:
            for common_hosts in self.common_hostses:
                if common_hosts.is_common:
                    break

            hosts.save(path=self.sys_hosts_path, common=common_hosts)
            is_success = True

        except Exception:

            err = traceback.format_exc()
            co.log(err)

            if "Permission denied:" in err:
                if sys_type in ("linux", "mac") and self.tryToSaveBySudoPassword(
                    hosts, common_hosts
                ):
                    is_success = True
                else:
                    msg = u"切换 hosts 失败！\n没有修改 '%s' 的权限！" % self.sys_hosts_path

            else:
                msg = u"切换 hosts 失败！\n\n%s" % err

            if msg and self.current_showing_hosts:
                wx.MessageBox(msg, caption=u"出错啦！")
                return

        if is_success:

            if len(self.origin_hostses) > 0:
                self.origin_hostses[0].icon_idx = hosts.icon_idx
            self.notify(msg=u"hosts 已切换为「%s」。" % hosts.title, title=u"hosts 切换成功")

            self.tryToFlushDNS()
            self.highLightHosts(hosts)

    def tryToFlushDNS(self):
        u"""尝试更新 DNS 缓存
        @see http://cnzhx.net/blog/how-to-flush-dns-cache-in-linux-windows-mac/
        """

        try:
            if self.sys_type == "mac":
                cmd = "dscacheutil -flushcache"
                os.popen(cmd)

            elif self.sys_type == "win":
                cmd = "ipconfig /flushdns"
                os.popen(cmd)

            elif self.sys_type == "linux":
                cmd = "/etc/init.d/nscd restart"
                os.popen(cmd)

        except Exception:
            pass

    def highLightHosts(self, hosts):
        u"""将切换的host文件高亮显示"""

        self.m_tree.SelectItem(hosts.tree_item_id)

        if self.current_using_hosts:
            self.m_tree.SetItemBold(self.current_using_hosts.tree_item_id, bold=False)
        self.m_tree.SetItemBold(hosts.tree_item_id)

        self.showHosts(hosts)
        self.current_using_hosts = hosts
        self.updateIcon()

    def updateIcon(self):

        co.log("update icon")
        if self.current_using_hosts:
            if len(self.origin_hostses) > 0:
                self.updateHostsIcon(self.origin_hostses[0])
            self.SetIcon(co.GetMondrianIcon(self.current_using_hosts.icon_idx))
            self.taskbar_icon.updateIcon()

    def addHosts(self, hosts, show_after_add=False):

        if hosts.is_origin:
            tree = self.m_tree_origin
            list_hosts = self.origin_hostses
        elif hosts.is_online:
            tree = self.m_tree_online
            list_hosts = self.hostses
        elif hosts.is_common:
            tree = self.m_tree_common
            list_hosts = self.common_hostses
        else:
            tree = self.m_tree_local
            list_hosts = self.hostses

        if hosts.is_origin:
            hosts.tree_item_id = self.m_tree_origin
        elif hosts.is_common:
            hosts.tree_item_id = self.m_tree_common
            list_hosts.append(hosts)
        else:
            list_hosts.append(hosts)
            hosts.tree_item_id = self.m_tree.AppendItem(tree, hosts.title)

        self.updateHostsIcon(hosts)
        self.m_tree.Expand(tree)

        if show_after_add:
            self.m_tree.SelectItem(hosts.tree_item_id)

    def updateHostsIcon(self, hosts):

        icon_idx = hosts.icon_idx
        if type(icon_idx) not in (int, long) or icon_idx < 0:
            icon_idx = 0
        elif icon_idx >= len(self.ico_colors_idx):
            icon_idx = len(self.ico_colors_idx) - 1

        self.m_tree.SetItemImage(
            hosts.tree_item_id, self.ico_colors_idx[icon_idx], wx.TreeItemIcon_Normal
        )
#        if hosts == self.current_using_hosts:
#            self.updateIcon()

    def delHosts(self, hosts):

        if not hosts:
            return False

        if hosts.is_origin:
            wx.MessageBox(u"初始 hosts 不能删除哦～", caption=u"出错啦！")
            return False

        if hosts == self.current_using_hosts:
            wx.MessageBox(u"这个 hosts 方案正在使用，不能删除哦～", caption=u"出错啦！")
            return False

        dlg = wx.MessageDialog(None, u"确定要删除 hosts '%s'？" % hosts.title, u"删除 hosts",
            wx.YES_NO | wx.ICON_QUESTION
        )
        ret_code = dlg.ShowModal()
        if ret_code != wx.ID_YES:
            dlg.Destroy()
            return False

        dlg.Destroy()

        try:
            hosts.remove()

        except Exception:
            err = traceback.format_exc()
            wx.MessageBox(err, caption=u"出错啦！")
            return False

        self.m_tree.Delete(hosts.tree_item_id)
        self.hostses.remove(hosts)

        cfg_hostses = self.configs.get("hostses")
        if cfg_hostses and hosts.title in cfg_hostses:
            cfg_hostses.remove(hosts.title)

        return True

    def export(self, path):
        u"""将当前所有设置以及方案导出为一个文件"""

        data = {
            "version": self.version,
            "configs": self.configs,
        }
        hosts_files = []
        for hosts in self.hostses:
            hosts_files.append({
                "filename": hosts.filename,
                "content": hosts.full_content,
            })

        data["hosts_files"] = hosts_files

        try:
            self.writeFile(path, json.dumps(data))
        except Exception:
            wx.MessageBox(u"导出失败！\n\n%s" % traceback.format_exc(), caption=u"出错啦！")
            return

        wx.MessageBox(u"导出完成！")

    def importHosts(self, content):
        u"""导入"""

        try:
            data = json.loads(content)

        except Exception:
            wx.MessageBox(u"档案解析出错了！", caption=u"导入失败")
            return

        if type(data) != dict:
            wx.MessageBox(u"档案格式有误！", caption=u"导入失败")
            return

        configs = data.get("configs")
        hosts_files = data.get("hosts_files")
        if type(configs) != dict or type(hosts_files) not in (list, tuple):
            wx.MessageBox(u"档案数据有误！", caption=u"导入失败")
            return

        # 删除现有 hosts 文件
        current_files = glob.glob(os.path.join(self.hosts_path, "*.hosts"))
        for fn in current_files:
            try:
                os.remove(fn)

            except Exception:
                wx.MessageBox(u"删除 '%s' 时失败！\n\n%s" % (fn, traceback.format_exc()),
                    caption=u"导入失败")
                return

        # 写入新 hosts 文件
        for hf in hosts_files:
            if type(hf) != dict or "filename" not in hf or "content" not in hf:
                continue

            fn = hf["filename"].strip()
            if not fn or not fn.lower().endswith(".hosts"):
                continue

            try:
                self.writeFile(os.path.join(self.hosts_path, fn), hf["content"].strip().encode("utf-8"))

            except Exception:
                wx.MessageBox(u"写入 '%s' 时失败！\n\n%s" % (fn, traceback.format_exc()),
                    caption=u"导入失败")
                return

        # 更新 configs
#        self.configs = {}
        try:
            self.writeFile(self.configs_path, json.dumps(configs).encode("utf-8"))
        except Exception:
            wx.MessageBox(u"写入 '%s' 时失败！\n\n%s" % (self.configs_path, traceback.format_exc()),
                caption=u"导入失败")
            return

#        self.clearTree()
#        self.init2()

        wx.MessageBox(u"导入成功！")
        self.restart()

    def restart(self):
        u"""重启主界面程序"""

        self.mainjob.toRestart(None)
#        self.mainjob.toRestart(self.taskbar_icon)
        self.stopBackThreads()
        self.taskbar_icon.Destroy()
        self.Destroy()

    def clearTree(self):

        for hosts in self.all_hostses:
            self.m_tree.Delete(hosts.tree_item_id)

    def notify(self, msg="", title=u"消息"):

        def macGrowlNotify(msg, title):

            try:
                growl.notify(
                    noteType="New Messages",
                    title=title,
                    description=msg,
                    sticky=False,
                    priority=1,
                )
            except Exception:
                pass

        if self.sys_type == "mac":
            # Mac 系统
            if has_growl:
                macGrowlNotify(msg, title)

        elif self.sys_type == "linux":
            # linux 系统
            pynotify.Notification(title, msg).show()

        else:

            try:
                import ToasterBox as TB
            except ImportError:
                TB = None

            sw, sh = wx.GetDisplaySize()
            width, height = 210, 50
            px = sw - 230
            py = sh - 100

            tb = TB.ToasterBox(self)
            tb.SetPopupText(msg)
            tb.SetPopupSize((width, height))
            tb.SetPopupPosition((px, py))
            tb.Play()

        self.SetFocus()

    def updateConfigs(self, configs):

        keys = ("hostses",)
        for k in keys:
            if k in configs:
                self.configs[k] = configs[k]

        # 校验配置有效性
        if type(self.configs.get("hostses")) != list:
            self.configs["hostses"] = []

    def loadConfigs(self):

        if os.path.isfile(self.configs_path):
            try:
                configs = json.loads(open(self.configs_path, "rb").read())
            except Exception:
                wx.MessageBox("读取配置信息失败！", caption=u"出错啦！")
                return

            if type(configs) != dict:
                wx.MessageBox("配置信息格式有误！", caption=u"出错啦！")
                return

            self.updateConfigs(configs)


        self.saveConfigs()

    def saveConfigs(self):
        try:
            self.writeFile(self.configs_path, json.dumps(self.configs))
        except Exception:
            wx.MessageBox("保存配置信息失败！\n\n%s" % traceback.format_exc(), caption=u"出错啦！")

    def eachHosts(self, func):

        for hosts in self.hostses:
            func(hosts)

    @property
    def all_hostses(self):

        return self.origin_hostses + self.hostses

    @property
    def local_hostses(self):

        return [hosts for hosts in self.hostses if not hosts.is_online]

    @property
    def online_hostses(self):

        return [hosts for hosts in self.hostses if hosts.is_online]

    def makeNewHostsFileName(self):
        u"""生成一个新的 hosts 文件名"""

        fns = glob.glob(os.path.join(self.hosts_path, "*.hosts"))
        fns = [os.path.split(fn)[1] for fn in fns]
        for i in xrange(1024):
            fn = "%d.hosts" % i
            if fn not in fns:
                break

        else:
            return None

        return fn

    def saveHosts(self, hosts):

        try:
            if hosts.save():
                co.log("saved.")
            return True

        except Exception:
            err = traceback.format_exc()

            if "Permission denied:" in err:
                msg = u"没有修改 '%s' 的权限！" % hosts.path

            else:
                msg = u"保存 hosts 失败！\n\n%s" % err

            wx.MessageBox(msg, caption=u"出错啦！")

            return False

    def showDetailEditor(self, hosts=None, default_is_online=False):
        u"""显示详情编辑窗口"""

        dlg = ui.Dlg_addHosts(self)

        if hosts:
            # 初始化值
            dlg.m_radioBtn_local.SetValue(not hosts.is_online)
            dlg.m_radioBtn_online.SetValue(hosts.is_online)
            dlg.m_radioBtn_local.Enable(False)
            dlg.m_radioBtn_online.Enable(False)
            dlg.m_textCtrl_title.SetValue(hosts.title)
            if hosts.url:
                dlg.m_textCtrl_url.SetValue(hosts.url)
                dlg.m_textCtrl_url.Enable(True)

        else:
            dlg.m_radioBtn_local.SetValue(not default_is_online)
            dlg.m_radioBtn_online.SetValue(default_is_online)
            dlg.m_textCtrl_url.Enabled = default_is_online

        if dlg.ShowModal() != wx.ID_OK:
            dlg.Destroy()
            return

        dlg.Destroy()

        is_online = dlg.m_radioBtn_online.GetValue()
        title = dlg.m_textCtrl_title.GetValue().strip()
        url = dlg.m_textCtrl_url.GetValue().strip()

        if not title:
            wx.MessageBox(u"方案名不能为空！", caption=u"出错啦！")
            return

        for h in self.hostses:
            if h != hosts and h.title == title:
                wx.MessageBox(u"已经有名为 '%s' 的方案了！" % title, caption=u"出错啦！")
                return

        if not hosts:
            # 新建 hosts
            fn = self.makeNewHostsFileName()
            if not fn:
                wx.MessageBox(u"hosts 文件数超出限制，无法再创建新 hosts 了！", caption=u"出错啦！")
                return

            path = os.path.join(self.hosts_path, fn)

            hosts = Hosts(path, title=title, url=url if is_online else None)
            hosts.content = u"# %s" % title

            if hosts.is_online:
                self.getHostsContent(hosts)

            self.addHosts(hosts, show_after_add=True)

        else:
            # 修改 hosts
            hosts.is_online = is_online
            hosts.title = title
            hosts.url = url if is_online else None
            self.updateHostsTitle(hosts)

        self.saveHosts(hosts)

    def getHostsContent(self, hosts):

        hosts.is_loading = True

        def tryToDestroy(obj):
            # mac 下，progress_dlg 销毁时总是会异常退出...
            if sys_type != "mac":
                try:
                    obj.Destroy()
                except Exception:
                    print(traceback.format_exc())

        if hosts.is_online:
            progress_dlg = wx.ProgressDialog(u"加载中",
                u"正在加载「%s」...\nURL: %s" % (hosts.title, hosts.url), 100,
                style=wx.PD_AUTO_HIDE
            )
            self.task_qu.put(lambda : [
                wx.CallAfter(progress_dlg.Update, 10),
                hosts.getContent(force=True, progress_dlg=progress_dlg),
                wx.CallAfter(progress_dlg.Update, 80),
                wx.CallAfter(self.tryToShowHosts, hosts),
                wx.CallAfter(progress_dlg.Update, 90),
                wx.CallAfter(self.saveHosts, hosts),
                wx.CallAfter(progress_dlg.Update, 100),
#                wx.CallAfter(lambda : progress_dlg.Destroy() and self.SetFocus()),
                wx.CallAfter(lambda : tryToDestroy(progress_dlg)),
                wx.CallAfter(self.SetFocus),
            ])

        else:
            self.task_qu.put(lambda : [
                hosts.getContent(force=True),
                wx.CallAfter(self.tryToShowHosts, hosts),
                wx.CallAfter(self.saveHosts, hosts),
            ])

        self.tryToShowHosts(hosts)

    def updateHostsTitle(self, hosts):
        u"""更新hosts的名称"""

        self.m_tree.SetItemText(hosts.tree_item_id, hosts.title)

    def getHostsFromTreeByEvent(self, event):

        item = event.GetItem()
        self.current_tree_item = item

        if item in (self.m_tree_online, self.m_tree_local, self.m_tree_root):
            pass

        elif self.current_using_hosts and item == self.current_using_hosts.tree_item_id:
            return self.current_using_hosts

        else:
            for hosts in self.all_hostses:
                if item == hosts.tree_item_id:
                    return hosts
            for hosts in self.common_hostses:
                if item == hosts.tree_item_id:
                    return hosts

        return None

    def getLatestStableVersion(self, alert=False):

        url = "https://github.com/oldj/SwitchHosts/blob/master/README.md"

        ver = None
        try:
            c = urllib.urlopen(url).read()
#            wx.CallAfter(progress_dlg.Update, 50)
            v = re.search(r"\bLatest Stable:\s?(?P<version>[\d\.]+)\b", c)
            if v:
                ver = v.group("version")
                self.latest_stable_version = ver
                co.log("last_stable_version: %s" % ver)

        except Exception:
            pass

        if not alert:
            return

        def _msg():
            if not ver:
                wx.MessageBox(u"未能取得最新版本号！", caption=u"出错啦！")

            else:
                cmpv = co.compareVersion(self.version, self.latest_stable_version)
                try:
                    if cmpv >= 0:
                        wx.MessageBox(u"当前已是最新版本！")
                    else:
                        if wx.MessageBox(
                            u"更新的稳定版 %s 已经发布，现在立刻查看吗？" % self.latest_stable_version,
                            u"发现新版本！",
                            wx.YES_NO | wx.ICON_INFORMATION
                        ) == wx.YES:
                            self.openHomepage()

                except Exception:
                    co.debugErr()
                    pass

        wx.CallAfter(_msg)

    def getHostsAttr(self, hosts, key=None):

        attrs = {
            "is_refresh_able": hosts and hosts in self.all_hostses or hosts in self.common_hostses,
            "is_delete_able": hosts and hosts in self.hostses,
            "is_info_edit_able": hosts and not hosts.is_loading and hosts in self.hostses,
            "is_content_edit_able": hosts and not hosts.is_loading and
                (hosts in self.hostses or hosts in self.common_hostses),
            "is_apply_able": not hosts.is_common and not hosts.is_origin,
        }
        for k in attrs:
            attrs[k] = True if attrs[k] else False

        return attrs.get(key, False) if key else attrs

    def updateBtnStatus(self, hosts):

        hosts_attrs = self.getHostsAttr(hosts)

        # 更新下方按钮状态
        self.m_btn_refresh.Enable(hosts_attrs["is_refresh_able"])
        self.m_btn_del.Enable(hosts_attrs["is_delete_able"])
        self.m_btn_edit_info.Enable(hosts_attrs["is_info_edit_able"])
        self.m_btn_apply.Enable(hosts_attrs["is_apply_able"])

        # 更新右键菜单项状态
        self.hosts_item_menu.Enable(wx.ID_EDIT, hosts_attrs["is_info_edit_able"])
        self.hosts_item_menu.Enable(wx.ID_DELETE, hosts_attrs["is_delete_able"])
        self.hosts_item_menu.Enable(wx.ID_REFRESH, hosts_attrs["is_refresh_able"])
        self.hosts_item_menu.Enable(wx.ID_APPLY, hosts_attrs["is_apply_able"])

    def writeFile(self, path, content, mode="w"):

        try:
            path = path.encode(self.local_encoding)
        except Exception:
            co.debugErr()

        open(path, mode).write(content)

    def openHomepage(self):
        u"""打开项目主页"""

        url= "http://oldj.github.io/SwitchHosts/"
        wx.LaunchDefaultBrowser(url)

    def OnHomepage(self, event):
        self.openHomepage()

    def openFeedbackPage(self):
        u"""打开反馈主页"""

        url = "https://github.com/oldj/SwitchHosts/issues?direction=desc&sort=created&state=open"
        wx.LaunchDefaultBrowser(url)

    def OnFeedback(self, event):
        self.openFeedbackPage()

    def OnHostsChange(self, event):

        if self.is_switching_text:
            return

        self.current_showing_hosts.content = self.m_textCtrl_content.GetValue()
        self.saveHosts(self.current_showing_hosts)

    def OnChkUpdate(self, event):

        self.task_qu.put(lambda : [
            self.getLatestStableVersion(alert=True),
        ])

    def OnExit(self, event):

        self.is_running = False
        self.stopBackThreads()
        self.taskbar_icon.Destroy()
        self.Destroy()

        # 退出时删除进程锁文件
        lock_fn = os.path.join(self.working_path, self.instance_name) \
            if self.instance_name else None
        if lock_fn and os.path.isfile(lock_fn):
            os.remove(lock_fn)

        # sys.exit()

    def OnAbout(self, event):

        dlg = ui.AboutBox(version=self.version, latest_stable_version=self.latest_stable_version)
        dlg.ShowModal()
        dlg.Destroy()

    def OnTreeSelectionChange(self, event):
        u"""当点击左边树状结构的节点的时候触发"""

        hosts = self.getHostsFromTreeByEvent(event)

        if not hosts:
            return
        self.current_tree_hosts = hosts
        self.updateBtnStatus(hosts)

        if not hosts or (hosts not in self.hostses and hosts not in self.origin_hostses and hosts not in self.common_hostses):
            return event.Veto()

        if hosts and hosts != self.current_showing_hosts:
            if hosts.is_origin:
                # 重新读取系统 hosts 值
                hosts.getContent()
            self.showHosts(hosts)

    def OnTreeRClick(self, event):
        u"""在树节点上单击右键，展示右键菜单"""

        hosts = self.getHostsFromTreeByEvent(event)
        if hosts:
            self.OnTreeSelectionChange(event)

            self.m_tree.PopupMenu(self.hosts_item_menu, event.GetPoint())

    def OnTreeMenu(self, event):
        co.log("tree menu...")

    def OnTreeActive(self, event):
        u"""双击树的节点时候触发"""

        hosts = self.getHostsFromTreeByEvent(event)
        if hosts:
            if hosts.is_common or hosts.is_origin:
                return
            self.useHosts(hosts)

    def OnApply(self, event):
        u"""点击切换Hosts时候，触发该函数"""

        if self.current_showing_hosts and self.current_showing_hosts.is_common:
            return
        if self.current_showing_hosts:
            self.useHosts(self.current_showing_hosts)

    def OnDel(self, event):

        if self.delHosts(self.current_tree_hosts):
            self.current_showing_hosts = None

    def OnNew(self, event):

        is_online = False
        hosts = self.current_showing_hosts
        if hosts.is_online or self.current_tree_item == self.m_tree_online:
            is_online = True

        self.showDetailEditor(default_is_online=is_online)

    def OnEdit(self, event):

        self.showDetailEditor(hosts=self.current_showing_hosts)

    def OnRename(self, event):

        hosts = self.current_showing_hosts
        if not hosts:
            return

        if hosts in self.origin_hostses:
            wx.MessageBox(u"%s不能改名！" % lang.trans("origin_hosts"), caption=u"出错啦！")
            return

        self.m_tree.EditLabel(hosts.tree_item_id)

    def OnRenameEnd(self, event):

        hosts = self.current_showing_hosts
        if not hosts:
            return

        title = event.GetLabel().strip()
        if title and hosts.title != title:
            hosts.title = title
            hosts.save()

        else:
            event.Veto()

    def OnRefresh(self, event):

        hosts = self.current_showing_hosts
        self.getHostsContent(hosts)

    def OnExport(self, event):

        if wx.MessageBox(
            u"您可以将现在的 hosts 档案导出并共享给其他 SwitchHosts! 用户。\n\n" +
            u"注意，只有“%s”和“%s”中的 hosts 会被导出！" % (
                lang.trans("local_hosts"), lang.trans("online_hosts")),
            caption=u"导出档案",
            style=wx.OK | wx.CANCEL,
        ) != wx.OK:
            return

        wildcard = u"SwicthHosts! 档案 (*.swh)|*.swh"
        dlg = wx.FileDialog(self, u"导出为...", os.getcwd(), "hosts.swh", wildcard, wx.SAVE)

        if dlg.ShowModal() == wx.ID_OK:
            self.export(dlg.GetPath())

        dlg.Destroy()

    def OnImport(self, event):

        dlg = ui.Dlg_Import(self)
        if dlg.ShowModal() == wx.ID_OK:
            path = dlg.m_filePicker.GetPath()
            url = dlg.m_textCtrl_url.GetValue()

            content = None
            if dlg.m_notebook.GetSelection() != 1:
                # 本地
                if os.path.isfile(path):
                    content = open(path).read()

                else:
                    wx.MessageBox(u"%s 不是有效的文件路径！" % path, caption=u"出错啦！")

            else:
                # 在线
                if co.httpExists(url):
                    content = urllib.urlopen(url).read()

                else:
                    wx.MessageBox(u"URL %s 无法访问！" % url, caption=u"出错啦！")

            if content and wx.MessageBox(u"导入档案会替换现有设置及数据，确定要导入吗？",
                    caption=u"警告",
                    style=wx.OK | wx.CANCEL) == wx.OK:
                self.importHosts(content)

        dlg.Destroy()

    def OnDonate(self, event):

        wx.LaunchDefaultBrowser("https://me.alipay.com/oldj")

    def OnTreeBeginDrag(self, event):

        item = event.GetItem()
        hosts = self.getHostsFromTreeByEvent(event)
        if not hosts or hosts.is_origin or hosts.is_common:
            event.Veto()
            return

        co.log("drag start..")
        self.current_dragging_hosts = hosts
        self.__dragging_item = item

        event.Allow()
        self.m_tree.Bind(wx.EVT_MOTION, self._drag_OnMotion)
        self.m_tree.Bind(wx.EVT_LEFT_UP, self._drag_OnMouseLeftUp)

    def _drag_OnMotion(self, event):

        event.Skip()

    def _drag_OnMouseLeftUp(self, event):

        co.log("mouse left up..")
        self.m_tree.Unbind(wx.EVT_MOTION)
        self.m_tree.Unbind(wx.EVT_LEFT_UP)
        event.Skip()

    def OnTreeEndDrag(self, event):

        co.log("drag end..")

        target_item = event.GetItem()
        target_hosts = self.getHostsFromTreeByEvent(event)
        source_item = self.__dragging_item
        source_hosts = self.current_dragging_hosts

        self.__dragging_item = None
        self.current_dragging_hosts = None

        def getHostsIdx(hosts):

            idx = 0
            for h in self.hostses:
                if h == hosts:
                    break

                if h.is_online == hosts.is_online:
                    idx += 1

            return idx


        is_dragged = False

        if target_hosts and target_hosts != source_hosts and \
           source_hosts.is_online == target_hosts.is_online:
            # 拖到目标 hosts 上了
            parent = self.m_tree.GetItemParent(target_item)
            added_item_id = self.m_tree.InsertItemBefore(parent, getHostsIdx(target_hosts),
                    source_hosts.title
                )
            source_hosts.tree_item_id = added_item_id
#            self.updateHostsTitle(source_hosts)
            self.updateHostsIcon(source_hosts)
            if source_hosts == self.current_using_hosts:
                self.highLightHosts(source_hosts)
            self.hostses.remove(source_hosts)
            self.hostses.insert(self.hostses.index(target_hosts), source_hosts)

            is_dragged = True

        elif target_item == self.m_tree_local and not source_hosts.is_online:
            # 拖到本地树上了
            pass

        elif target_item == self.m_tree_online and source_hosts.is_online:
            # 拖到在线树上了
            pass

        if is_dragged:
            self.updateConfigs({
                "hostses": [hosts.filename for hosts in self.hostses],
            })
            self.saveConfigs()
            self.m_tree.Delete(source_item)
            self.m_tree.SelectItem(source_hosts.tree_item_id)

    def OnActiveApp(self, event):
        """Called when the doc icon is clicked, and ???"""
        print("---")
#        self.GetTopWindow().Raise()
        self.Raise()

    def chkActive(self):
        u"""循环查看工作目录下是否有 .active 文件，有则激活主窗口"""

        if self.is_running and os.path.isfile(self.active_fn):
            print("active..")
            os.remove(self.active_fn)
#            print(dir(self.mainjob.app))
            self.Raise()
            wx.TopLevelWindow.RequestUserAttention(self)
#            self.mainjob.app.SetTopWindow(self)

        time.sleep(0.5)
#        wx.CallAfter(self.chkActive)
        if self.is_running:
            self.task_qu.put(self.chkActive)

########NEW FILE########
__FILENAME__ = TaskbarIcon
# -*- coding: utf-8 -*-
#
# author: oldj
# blog: http://oldj.net
# email: oldj.wu@gmail.com
#

import wx
import common_operations as co
import lang

class TaskBarIcon(wx.TaskBarIcon):

    ID_About = wx.NewId()
    ID_Exit = wx.NewId()
    ID_MainFrame = wx.NewId()

    def __init__(self, main_frame):

        wx.TaskBarIcon.__init__(self)
        #        super(wx.TaskBarIcon, self).__init__()
        self.setMainFrame(main_frame)
        self.Bind(wx.EVT_TASKBAR_LEFT_DCLICK, self.OnTaskBarLeftDClick)
        self.Bind(wx.EVT_MENU, self.OnExit, id=self.ID_Exit)
        self.Bind(wx.EVT_MENU, self.OnMainFrame, id=self.ID_MainFrame)

        self.font_bold = wx.SystemSettings.GetFont(wx.SYS_DEFAULT_GUI_FONT)
        self.font_bold.SetWeight(wx.BOLD)


    def setMainFrame(self, main_frame):

        self.main_frame = main_frame
        self.SetIcon(co.GetMondrianIcon(), self.main_frame.default_title)
        self.Bind(wx.EVT_MENU, self.main_frame.OnAbout, id=self.ID_About)


    def OnTaskBarLeftDClick(self, event):

        if self.main_frame.IsIconized():
            self.main_frame.Iconize(False)
        if not self.main_frame.IsShown():
            self.main_frame.Show(True)
        self.main_frame.Raise()


    def OnExit(self, event):

        self.main_frame.OnExit(event)


    def OnMainFrame(self, event):
        u"""显示主面板"""

        if not self.main_frame.IsShown():
            self.main_frame.Show(True)
        self.main_frame.Raise()

    # override
    def CreatePopupMenu(self):

        menu = wx.Menu()
        menu.Append(self.ID_MainFrame, u"SwitchHosts!")
        menu.AppendSeparator()

        local_hostses = self.main_frame.local_hostses
        online_hostses = self.main_frame.online_hostses

        def addItems(name, hostses):
            tmp_id = wx.NewId()
            menu.Append(tmp_id, name)
            menu.Enable(tmp_id, False)

            for hosts in hostses:
                if hosts:
                    self.addHosts(menu, hosts)

        if local_hostses:
            addItems(u"本地方案", local_hostses)
        if online_hostses:
            addItems(u"在线方案", online_hostses)

        menu.AppendSeparator()
        menu.Append(self.ID_About, "About")
        menu.Append(self.ID_Exit, "Exit")

        return menu


    def addHosts(self, menu, hosts):
        u"""在菜单项中添加一个 hosts"""

        item_id = wx.NewId()
        title = hosts.title if not hosts.is_origin else lang.trans("origin_hosts")
        mitem = wx.MenuItem(menu, item_id, title, kind=wx.ITEM_CHECK)
        mitem.SetBitmap(co.GetMondrianBitmap(hosts.icon_idx))
        menu.AppendItem(mitem)

        is_using = self.main_frame.current_using_hosts == hosts
        menu.Check(item_id, is_using)
        if is_using:
            mitem.SetFont(self.font_bold)
#        self.hosts[item_id] = title
        hosts.taskbar_id = item_id

        self.Bind(wx.EVT_MENU, self.switchHosts, id=item_id)


    def switchHosts(self, event):

        item_id = event.GetId()
        for hosts in self.main_frame.all_hostses:
            if hosts.taskbar_id == item_id:
                self.main_frame.useHosts(hosts)

                return


    def updateIcon(self):

        self.SetIcon(
            co.GetMondrianIcon(self.main_frame.current_using_hosts.icon_idx),
            self.main_frame.default_title
        )


########NEW FILE########
__FILENAME__ = ToasterBox
# --------------------------------------------------------------------------- #
# TOASTERBOX wxPython IMPLEMENTATION
# Ported And Enhanced From wxWidgets Contribution (Aj Bommarito) By:
#
# Andrea Gavana, @ 16 September 2005
# Latest Revision: 31 Oct 2007, 21.30 CET
#
#
# TODO/Caveats List
#
# 1. Any Idea?
#
#
# For All Kind Of Problems, Requests Of Enhancements And Bug Reports, Please
# Write To Me At:
#
# andrea.gavana@gmail.it
# gavana@kpo.kz
#
# Or, Obviously, To The wxPython Mailing List!!!
#
#
# End Of Comments
# --------------------------------------------------------------------------- #


"""Description:

ToasterBox Is A Cross-Platform Library To Make The Creation Of MSN Style "Toaster"
Popups Easier. The Syntax Is Really Easy Especially If You Are Familiar With The
Syntax Of wxPython.

It Has 2 Main Styles:

- TB_SIMPLE:  Using This Style, You Will Be Able To Specify A Background Image For
             ToasterBox, Text Properties As Text Colour, Font And Label.

- TB_COMPLEX: This Style Will Allow You To Put Almost Any Control Inside A
             ToasterBox. You Can Add A Panel In Which You Can Put All The Controls
             You Like.

Both Styles Support The Setting Of ToasterBox Position (On Screen Coordinates),
Size, The Time After Which The ToasterBox Is Destroyed (Linger), And The Scroll
Speed Of ToasterBox.

ToasterBox Has Been Tested On The Following Platforms:

Windows (Verified on Windows XP, 2000)


Latest Revision: Andrea Gavana @ 31 Oct 2007, 21.30 CET

"""

import textwrap
import wx
import sys

from wx.lib.statbmp import GenStaticBitmap as StaticBitmap

# Define Window List, We Use It Globally
winlist = []

TB_SIMPLE = 1
TB_COMPLEX = 2

DEFAULT_TB_STYLE = wx.SIMPLE_BORDER | wx.STAY_ON_TOP | wx.FRAME_NO_TASKBAR
TB_CAPTION = DEFAULT_TB_STYLE | wx.CAPTION | wx.SYSTEM_MENU | wx.CLOSE_BOX | wx.FRAME_TOOL_WINDOW

TB_ONTIME = 1
TB_ONCLICK = 2

# scroll from up to down
TB_SCR_TYPE_UD = 1
# scroll from down to up
TB_SCR_TYPE_DU = 2

# ------------------------------------------------------------------------------ #
# Class ToasterBox
#    Main Class Implementation. It Is Basically A wx.Timer. It Creates And
#    Displays Popups And Handles The "Stacking".
# ------------------------------------------------------------------------------ #

class ToasterBox(wx.Timer):

   def __init__(self, parent, tbstyle=TB_SIMPLE, windowstyle=DEFAULT_TB_STYLE,
                closingstyle=TB_ONTIME, scrollType=TB_SCR_TYPE_DU):
       """Deafult Class Constructor.

       ToasterBox.__init__(self, tbstyle=TB_SIMPLE, windowstyle=DEFAULT_TB_STYLE)

       Parameters:

       - tbstyle: This Parameter May Have 2 Values:
         (a) TB_SIMPLE: A Simple ToasterBox, With Background Image And Text
             Customization Can Be Created;
         (b) TB_COMPLEX: ToasterBoxes With Different Degree Of Complexity Can
             Be Created. You Can Add As Many Controls As You Want, Provided
             That You Call The AddPanel() Method And Pass To It A Dummy Frame
             And A wx.Panel. See The Demo For Details.

       - windowstyle: This Parameter Influences The Visual Appearance Of ToasterBox:
         (a) DEFAULT_TB_STYLE: Default Style, No Caption Nor Close Box;
         (b) TB_CAPTION: ToasterBox Will Have A Caption, With The Possibility To
             Set A Title For ToasterBox Frame, And A Close Box;

       - closingstyle: Set This Value To TB_ONCLICK If You Want To Be Able To Close
         ToasterBox By A Mouse Click Anywhere In The ToasterBox Frame.

       """

       self._parent = parent
       self._sleeptime = 10
       self._pausetime = 1700
       self._popuptext = "default"
       self._popupposition = wx.Point(100,100)
       self._popuptop = wx.Point(0,0)
       self._popupsize = wx.Size(150, 170)

       self._backgroundcolour = wx.WHITE
       self._foregroundcolour = wx.BLACK
       if sys.platform != "darwin":
           self._textfont = wx.Font(8, wx.SWISS, wx.NORMAL, wx.NORMAL, False, "Verdana")
       else:
           self._textfont = wx.Font(12, wx.SWISS, wx.NORMAL, wx.NORMAL, False, "Monaco")

       self._bitmap = None

       self._tbstyle = tbstyle
       self._windowstyle = windowstyle
       self._closingstyle = closingstyle

       self._panel = None

       self._bottomright = wx.Point(wx.GetDisplaySize().GetWidth(),
                                    wx.GetDisplaySize().GetHeight())

       parent.Bind(wx.EVT_ICONIZE, lambda evt: [w.Hide() for w in winlist])

       self._tb = ToasterBoxWindow(self._parent, self, self._tbstyle, self._windowstyle,
                                   self._closingstyle, scrollType=scrollType)


   def SetPopupPosition(self, pos):
       """ Sets The ToasterBox Position On Screen. """

       self._popupposition = pos


   def SetPopupPositionByInt(self, pos):
       """ Sets The ToasterBox Position On Screen, At One Of The Screen Corners. """

       self._bottomright = wx.Point(wx.GetDisplaySize().GetWidth(),
                                    wx.GetDisplaySize().GetHeight())

       # top left
       if pos == 0:
           popupposition = wx.Point(0,0)
       # top right
       elif pos == 1:
           popupposition = wx.Point(wx.GetDisplaySize().GetWidth() -
                                    self._popupsize[0], 0)
       # bottom left
       elif pos == 2:
           popupposition = wxPoint(0, wx.GetDisplaySize().GetHeight() -
                                   self._popupsize[1])
       # bottom right
       elif pos == 3:
           popupposition = wx.Point(self._bottomright.x - self._popupsize[0],
                                    self._bottomright.y - self._popupsize[1])

       self._bottomright = wx.Point(popupposition.x + self._popupsize[0],
                                    popupposition.y + self._popupsize[1])


   def SetPopupBackgroundColor(self, colour=None):
       """ Sets The ToasterBox Background Colour. Use It Only For ToasterBoxes Created
       With TB_SIMPLE Style. """

       if colour is None:
           colour = wx.WHITE

       self._backgroundcolour = colour


   def SetPopupTextColor(self, colour=None):
       """ Sets The ToasterBox Foreground Colour. Use It Only For ToasterBoxes Created
       With TB_SIMPLE Style. """

       if colour is None:
           colour = wx.BLACK

       self._foregroundcolour = colour


   def SetPopupTextFont(self, font=None):
       """ Sets The ToasterBox Text Font. Use It Only For ToasterBoxes Created With
       TB_SIMPLE Style. """

       if font is None:
           if sys.platform != "darwin":
               font = wx.Font(8, wx.SWISS, wx.NORMAL, wx.NORMAL, False, "Verdana")
           else:
               font = wx.Font(12, wx.SWISS, wx.NORMAL, wx.NORMAL, False, "Monaco")

       self._textfont = font


   def SetPopupSize(self, size):
       """ Sets The ToasterBox Size. """

       self._popupsize = size


   def SetPopupPauseTime(self, pausetime):
       """ Sets The Time After Which The ToasterBox Is Destroyed (Linger). """

       self._pausetime = pausetime


   def SetPopupBitmap(self, bitmap=None):
       """ Sets The ToasterBox Background Image. Use It Only For ToasterBoxes
       Created With TB_SIMPLE Style. """

       if bitmap is not None:
           bitmap = wx.Bitmap(bitmap, wx.BITMAP_TYPE_BMP)

       self._bitmap = bitmap


   def SetPopupScrollSpeed(self, speed):
       """ Sets The ToasterBox Scroll Speed. The Speed Parameter Is The Pause
       Time (In ms) For Every Step In The ScrollUp() Method."""

       self._sleeptime = speed


   def SetPopupText(self, text):
       """ Sets The ToasterBox Text. Use It Only For ToasterBoxes Created With
       TB_SIMPLE Style. """

       self._popuptext = text


   def AddPanel(self, panel):
       """ Adds A Panel To The ToasterBox. Use It Only For ToasterBoxes Created
       With TB_COMPLEX Style. """

       if not self._tbstyle & TB_COMPLEX:
           raise "\nERROR: Panel Can Not Be Added When Using TB_SIMPLE ToasterBox Style"
           return

       self._panel = panel


   def Play(self):
       """ Creates The ToasterBoxWindow, That Does All The Job. """

       # create new window
       self._tb.SetPopupSize((self._popupsize[0], self._popupsize[1]))
       self._tb.SetPopupPosition((self._popupposition[0], self._popupposition[1]))
       self._tb.SetPopupPauseTime(self._pausetime)
       self._tb.SetPopupScrollSpeed(self._sleeptime)

       if self._tbstyle == TB_SIMPLE:
           self._tb.SetPopupTextColor(self._foregroundcolour)
           self._tb.SetPopupBackgroundColor(self._backgroundcolour)
           self._tb.SetPopupTextFont(self._textfont)

           if self._bitmap is not None:
               self._tb.SetPopupBitmap(self._bitmap)

           self._tb.SetPopupText(self._popuptext)

       if self._tbstyle == TB_COMPLEX:
           if self._panel is not None:
               self._tb.AddPanel(self._panel)

       # clean up the list
       self.CleanList()

       # check to see if there is already a window displayed
       # by looking at the linked list
       if len(winlist) > 0:
           # there ARE other windows displayed already
           # reclac where it should display
           self.MoveAbove(self._tb)

       # shift new window on to the list
       winlist.append(self._tb)

       if not self._tb.Play():
           # if we didn't show the window properly, remove it from the list
           winlist.remove(winlist[-1])
           # delete the object too
           self._tb.Destroy()
           return


   def MoveAbove(self, tb):
       """ If A ToasterBox Already Exists, Move The New One Above. """

       # recalc where to place this popup

       self._tb.SetPopupPosition((self._popupposition[0], self._popupposition[1] -
                                  self._popupsize[1]*len(winlist)))


   def GetToasterBoxWindow(self):
       """ Returns The ToasterBox Frame. """

       return self._tb


   def SetTitle(self, title):
       """ Sets The ToasterBox Title If It Was Created With TB_CAPTION Window Style. """

       self._tb.SetTitle(title)


   def Notify(self):
       """ It's Time To Hide A ToasterBox! """

       if len(winlist) == 0:
           return

       # clean the window list
       self.CleanList()

       # figure out how many blanks we have
       try:
           node = winlist[0]
       except:
           return

       if not node:
           return

       # move windows to fill in blank space
       for i in xrange(node.GetPosition()[1], self._popupposition[1], 4):
           if i > self._popupposition[1]:
               i = self._popupposition[1]

           # loop through all the windows
           for j in xrange(0, len(winlist)):
               ourNewHeight = i - (j*self._popupsize[1] - 8)
               tmpTb = winlist[j]
               # reset where the object THINKS its supposed to be
               tmpTb.SetPopupPosition((self._popupposition[0], ourNewHeight))
               # actually move it
               tmpTb.SetDimensions(self._popupposition[0], ourNewHeight, tmpTb.GetSize().GetWidth(),
                                   tmpTb.GetSize().GetHeight())

           wx.Usleep(self._sleeptime)


   def CleanList(self):
       """ Clean The Window List. """

       if len(winlist) == 0:
           return

       node = winlist[0]
       while node:
           if not node.IsShown():
               winlist.remove(node)
               try:
                   node = winlist[0]
               except:
                   node = 0
           else:
               indx = winlist.index(node)
               try:
                   node = winlist[indx+1]
               except:
                   node = 0


# ------------------------------------------------------------------------------ #
# Class ToasterBoxWindow
#    This Class Does All The Job, By Handling Background Images, Text Properties
#    And Panel Adding. Depending On The Style You Choose, ToasterBoxWindow Will
#    Behave Differently In Order To Handle Widgets Inside It.
# ------------------------------------------------------------------------------ #

class ToasterBoxWindow(wx.Frame):

   def __init__(self, parent, parent2, tbstyle, windowstyle,
       closingstyle, scrollType=TB_SCR_TYPE_DU):
       """Default Class Constructor.

       Used Internally. Do Not Call Directly This Class In Your Application!
       """

       wx.Frame.__init__(self, parent, wx.ID_ANY, "window", wx.DefaultPosition,
                         wx.DefaultSize, style=windowstyle | wx.CLIP_CHILDREN)

       self._starttime = wx.GetLocalTime()
       self._parent2 = parent2
       self._parent = parent
       self._sleeptime = 10
       self._step = 4
       self._pausetime = 1700
       self._textcolour = wx.BLACK
       self._popuptext = "Change Me!"
       # the size we want the dialog to be
       framesize = wx.Size(150, 170)
       self._count = 1
       self._tbstyle = tbstyle
       self._windowstyle = windowstyle
       self._closingstyle = closingstyle
       self._scrollType = scrollType


       if tbstyle == TB_COMPLEX:
           self.sizer = wx.BoxSizer(wx.VERTICAL)
       else:
           self._staticbitmap = None

       if self._windowstyle == TB_CAPTION:
           self.Bind(wx.EVT_CLOSE, self.OnClose)
           self.SetTitle("")

       if self._closingstyle & TB_ONCLICK and self._windowstyle != TB_CAPTION:
           self.Bind(wx.EVT_LEFT_DOWN, self.OnMouseDown)

       self._bottomright = wx.Point(wx.GetDisplaySize().GetWidth(),
                                    wx.GetDisplaySize().GetHeight())

       self.SetDimensions(self._bottomright.x, self._bottomright.y,
                          framesize.GetWidth(), framesize.GetHeight())


   def OnClose(self, event):

       self.NotifyTimer(None)
       event.Skip()


   def OnMouseDown(self, event):

       self.NotifyTimer(None)
       event.Skip()


   def SetPopupBitmap(self, bitmap):
       """ Sets The ToasterBox Background Image. Use It Only For ToasterBoxes
       Created With TB_SIMPLE Style. """

       bitmap = bitmap.ConvertToImage()
       xsize, ysize = self.GetSize()
       bitmap = bitmap.Scale(xsize, ysize)
       bitmap = bitmap.ConvertToBitmap()
       self._staticbitmap = StaticBitmap(self, -1, bitmap, pos=(0,0))

       if self._closingstyle & TB_ONCLICK and self._windowstyle != TB_CAPTION:
           self._staticbitmap.Bind(wx.EVT_LEFT_DOWN, self.OnMouseDown)


   def SetPopupSize(self, size):
       """ Sets The ToasterBox Size. """

       self.SetDimensions(self._bottomright.x, self._bottomright.y, size[0], size[1])


   def SetPopupPosition(self, pos):
       """ Sets The ToasterBox Position On Screen. """

       self._bottomright = wx.Point(pos[0] + self.GetSize().GetWidth(),
                                    pos[1] + self.GetSize().GetHeight())
       self._dialogtop = pos


   def SetPopupPositionByInt(self, pos):
       """ Sets The ToasterBox Position On Screen, At One Of The Screen Corners. """

       self._bottomright = wx.Point(wx.GetDisplaySize().GetWidth(),
                                    wx.GetDisplaySize().GetHeight())

       # top left
       if pos == 0:
           popupposition = wx.Point(0,0)
       # top right
       elif pos == 1:
           popupposition = wx.Point(wx.GetDisplaySize().GetWidth() -
                                    self._popupsize[0], 0)
       # bottom left
       elif pos == 2:
           popupposition = wx.Point(0, wx.GetDisplaySize().GetHeight() -
                                   self._popupsize[1])
       # bottom right
       elif pos == 3:
           popupposition = wx.Point(self._bottomright.x - self._popupsize[0],
                                    self._bottomright.y - self._popupsize[1])

       self._bottomright = wx.Point(popupposition.x + self._popupsize[0],
                                    popupposition.y + self._popupsize[1])

       self._dialogtop = popupposition


   def SetPopupPauseTime(self, pausetime):
       """ Sets The Time After Which The ToasterBox Is Destroyed (Linger). """

       self._pausetime = pausetime


   def SetPopupScrollSpeed(self, speed):
       """ Sets The ToasterBox Scroll Speed. The Speed Parameter Is The Pause
       Time (In ms) For Every Step In The ScrollUp() Method."""

       self._sleeptime = speed


   def AddPanel(self, panel):
       """ Adds A Panel To The ToasterBox. Use It Only For ToasterBoxes Created
       With TB_COMPLEX Style. """

       if not self._tbstyle & TB_COMPLEX:
           raise "\nERROR: Panel Can Not Be Added When Using TB_SIMPLE ToasterBox Style"
           return

       self.sizer.Add(panel, 1, wx.EXPAND)
       self.sizer.Layout()
       self.SetSizer(self.sizer)

       if self._closingstyle & TB_ONCLICK and self._windowstyle != TB_CAPTION:
           panel.Bind(wx.EVT_LEFT_DOWN, self.OnMouseDown)


   def SetPopupText(self, text):
       """ Sets The ToasterBox Text. Use It Only For ToasterBoxes Created With
       TB_SIMPLE Style. """

       self._popuptext = text


   def SetPopupTextFont(self, font):
       """ Sets The ToasterBox Text Font. Use It Only For ToasterBoxes Created With
       TB_SIMPLE Style. """

       self._textfont = font


   def GetPopupText(self):
       """ Returns The ToasterBox Text. Use It Only For ToasterBoxes Created With
       TB_SIMPLE Style. """

       return self._popuptext


   def Play(self):
       """ Creates The ToasterBoxWindow, That Does All The Job. """

       # do some checks to make sure this window is valid
       if self._bottomright.x < 1 or self._bottomright.y < 1:
           return False

       if self.GetSize().GetWidth() < 50 or self.GetSize().GetWidth() < 50:
           # toasterbox launches into a endless loop for some reason
           # when you try to make the window too small.
           return False

       self.ScrollUp()
       timerid = wx.NewId()
       self.showtime = wx.Timer(self, timerid)
       self.showtime.Start(self._pausetime)
       self.Bind(wx.EVT_TIMER, self.NotifyTimer, id=timerid)

       return True


   def NotifyTimer(self, event):
       """ Hides Gradually The ToasterBoxWindow. """

       self.showtime.Stop()
       del self.showtime
       self.ScrollDown()


   def SetPopupBackgroundColor(self, colour):
       """ Sets The ToasterBox Background Colour. Use It Only For ToasterBoxes Created
       With TB_SIMPLE Style. """

       self.SetBackgroundColour(colour)


   def SetPopupTextColor(self, colour):
       """ Sets The ToasterBox Foreground Colour. Use It Only For ToasterBoxes Created
       With TB_SIMPLE Style. """

       self._textcolour = colour


   def ScrollUp(self):
       """ Scrolls The ToasterBox Up, Which Means Gradually Showing The ToasterBox. """

       self.Show(True)

       # walk the Y value up in a raise motion
       xpos = self.GetPosition().x
       ypos = self._bottomright[1]
       windowsize = 0

       # checking the type of the scroll (from up to down or from down to up)
       if self._scrollType == TB_SCR_TYPE_UD:
           start = self._dialogtop[1]
           stop = ypos
           step = self._step
       elif self._scrollType == TB_SCR_TYPE_DU:
           start = ypos
           stop = self._dialogtop[1]
           step = -self._step
       else:
           errMsg = ("scrollType not supported (in ToasterBoxWindow.ScrollUp): %s" %
                 self._scrollType)
           raise ValueError(errMsg)

       for i in xrange(start, stop, step):
           if i < self._dialogtop[1]:
             i = self._dialogtop[1]

           windowsize = windowsize + self._step

           # checking the type of the scroll (from up to down or from down to up)
           if self._scrollType == TB_SCR_TYPE_UD:
               dimY = self._dialogtop[1]
           elif self._scrollType == TB_SCR_TYPE_DU:
               dimY = i
           else:
               errMsg = ("scrollType not supported (in ToasterBoxWindow.ScrollUp): %s" %
                     self._scrollType)
               raise ValueError(errMsg)

           self.SetDimensions(self._dialogtop[0], dimY, self.GetSize().GetWidth(),
                              windowsize)

           if self._tbstyle == TB_SIMPLE:
               self.DrawText()

           wx.Usleep(self._sleeptime)
           self.Update()
           self.Refresh()

       self.Update()

       if self._tbstyle == TB_SIMPLE:
           self.DrawText()

#       self.SetFocus()


   def ScrollDown(self):
       """ Scrolls The ToasterBox Down, Which Means Gradually Hiding The ToasterBox. """

       # walk down the Y value
       windowsize = self.GetSize().GetHeight()

       # checking the type of the scroll (from up to down or from down to up)
       if self._scrollType == TB_SCR_TYPE_UD:
           start = self._bottomright.y
           stop = self._dialogtop[1]
           step = -self._step
       elif self._scrollType == TB_SCR_TYPE_DU:
           start = self._dialogtop[1]
           stop = self._bottomright.y
           step = self._step
       else:
           errMsg = ("scrollType not supported (in ToasterBoxWindow.ScrollUp): %s" %
                 self._scrollType)
           raise ValueError(errMsg)

       for i in xrange(start, stop, step):
           if i > self._bottomright.y:
               i = self._bottomright.y

           windowsize = windowsize - self._step

           # checking the type of the scroll (from up to down or from down to up)
           if self._scrollType == TB_SCR_TYPE_UD:
               dimY = self._dialogtop[1]
           elif self._scrollType == TB_SCR_TYPE_DU:
               dimY = i
           else:
               errMsg = ("scrollType not supported (in ToasterBoxWindow.ScrollUp): %s" %
                     self._scrollType)
               raise ValueError(errMsg)

           self.SetDimensions(self._dialogtop[0], dimY,
                              self.GetSize().GetWidth(), windowsize)

           wx.Usleep(self._sleeptime)
           self.Refresh()

       self.Hide()
       if self._parent2:
           self._parent2.Notify()


   def DrawText(self):
       if self._staticbitmap is not None:
           dc = wx.ClientDC(self._staticbitmap)
       else:
           dc = wx.ClientDC(self)
       dc.SetFont(self._textfont)

       if not hasattr(self, "text_coords"):
           self._getTextCoords(dc)

       dc.DrawTextList(*self.text_coords)


   def _getTextCoords(self, dc):
       """ Draw The User Specified Text Using The wx.DC. Use It Only For ToasterBoxes
       Created With TB_SIMPLE Style. """

       # border from sides and top to text (in pixels)
       border = 7
       # how much space between text lines
       textPadding = 2

       pText = self.GetPopupText()

       max_len = len(pText)

       tw, th = self._parent2._popupsize

       if self._windowstyle == TB_CAPTION:
           th = th - 20

       while 1:
           lines = textwrap.wrap(pText, max_len)

           for line in lines:
               w, h = dc.GetTextExtent(line)
               if w > tw - border * 2:
                   max_len -= 1
                   break
           else:
               break

       fh = 0
       for line in lines:
           w, h = dc.GetTextExtent(line)
           fh += h + textPadding
       y = (th - fh) / 2; coords = []

       for line in lines:
           w, h = dc.GetTextExtent(line)
           x = (tw - w) / 2
           coords.append((x, y))
           y += h + textPadding

       self.text_coords = (lines, coords)

########NEW FILE########
__FILENAME__ = ui
# -*- coding: utf-8 -*-

import os
import wx, wx.html
import wx.lib.buttons as buttons
import common_operations as co
import lang


class Frame(wx.Frame):

    ID_HOSTS_TEXT = wx.NewId()

    def __init__(self,
                 parent=None, id=wx.ID_ANY, title="SwitchHosts!", pos=wx.DefaultPosition,
                 size=wx.DefaultSize,
                 style=wx.DEFAULT_FRAME_STYLE,
                 cls_TaskBarIcon=None
    ):
        wx.Frame.__init__(self, parent, id, title, pos, size, style)

        self.SetIcon(co.GetMondrianIcon())
        self.SetSizeHintsSz(wx.Size(400, 300), wx.DefaultSize)

        self.m_menubar1 = wx.MenuBar(0)
        self.m_menu1 = wx.Menu()
        self.m_menuItem_new = wx.MenuItem(self.m_menu1, wx.ID_NEW, u"新建(&N)", wx.EmptyString, wx.ITEM_NORMAL)
        self.m_menu1.AppendItem(self.m_menuItem_new)
        self.m_menu1.AppendSeparator()

        self.m_menuItem_export = wx.MenuItem(self.m_menu1, wx.NewId(), u"导出(&E)", wx.EmptyString, wx.ITEM_NORMAL)
        self.m_menu1.AppendItem(self.m_menuItem_export)
        self.m_menuItem_import = wx.MenuItem(self.m_menu1, wx.NewId(), u"导入(&I)", wx.EmptyString, wx.ITEM_NORMAL)
        self.m_menu1.AppendItem(self.m_menuItem_import)

        self.m_menu1.AppendSeparator()
        self.m_menuItem_exit = wx.MenuItem(self.m_menu1, wx.ID_EXIT, u"退出(&X)", wx.EmptyString, wx.ITEM_NORMAL)
        self.m_menu1.AppendItem(self.m_menuItem_exit)

        self.m_menubar1.Append(self.m_menu1, u"文件(&F)")

        self.m_menu2 = wx.Menu()
        self.m_menuItem_about = wx.MenuItem(self.m_menu2, wx.ID_ABOUT, u"关于(&A)", wx.EmptyString, wx.ITEM_NORMAL)
        self.m_menu2.AppendItem(self.m_menuItem_about)
        self.m_menuItem_homepage = wx.MenuItem(self.m_menu2, wx.ID_ANY, u"主页(&H)", wx.EmptyString, wx.ITEM_NORMAL)
        self.m_menu2.AppendItem(self.m_menuItem_homepage)
        self.m_menuItem_feedback = wx.MenuItem(self.m_menu2, wx.ID_ANY, u"反馈建议(&F)", wx.EmptyString, wx.ITEM_NORMAL)
        self.m_menu2.AppendItem(self.m_menuItem_feedback)
        self.m_menuItem_chkUpdate = wx.MenuItem(self.m_menu2, wx.ID_ANY, u"检查更新(&U)", wx.EmptyString, wx.ITEM_NORMAL)
        self.m_menu2.AppendItem(self.m_menuItem_chkUpdate)
        self.m_menuItem_donate = wx.MenuItem(self.m_menu2, wx.ID_ANY, u"捐赠(&D)", wx.EmptyString, wx.ITEM_NORMAL)
        self.m_menu2.AppendItem(self.m_menuItem_donate)

        self.m_menubar1.Append(self.m_menu2, u"帮助(&H)")

        self.SetMenuBar(self.m_menubar1)

        bSizer1 = wx.BoxSizer(wx.VERTICAL)

        self.m_panel1 = wx.Panel(self, wx.ID_ANY, wx.DefaultPosition, wx.DefaultSize, wx.TAB_TRAVERSAL)
        bSizer4 = wx.BoxSizer(wx.HORIZONTAL)

        bSizer5 = wx.BoxSizer(wx.VERTICAL)

        self.m_tree = wx.TreeCtrl(self.m_panel1, wx.ID_ANY, wx.DefaultPosition, wx.Size(200, -1),
            style=wx.TR_DEFAULT_STYLE|wx.NO_BORDER|wx.TR_NO_LINES\
                |wx.TR_FULL_ROW_HIGHLIGHT#|wx.TR_HIDE_ROOT
        )

        self.m_tree.SetBackgroundColour(wx.Colour(218, 223, 230))
        self.m_tree_root = self.m_tree.AddRoot(u"hosts")
        self.m_tree_common = self.m_tree.AppendItem(self.m_tree_root, lang.trans("common_hosts"))
        self.m_tree_origin = self.m_tree.AppendItem(self.m_tree_root, lang.trans("origin_hosts"))
        self.m_tree_local = self.m_tree.AppendItem(self.m_tree_root, lang.trans("local_hosts"))
        self.m_tree_online = self.m_tree.AppendItem(self.m_tree_root, lang.trans("online_hosts"))
        self.m_tree.SetItemTextColour(self.m_tree_root, "#999999")
        self.m_tree.SetItemTextColour(self.m_tree_common, "#3333ff")
        self.m_tree.SetItemTextColour(self.m_tree_local, "#999999")
        self.m_tree.SetItemTextColour(self.m_tree_online, "#999999")
        self.m_tree.ExpandAll()
        bSizer5.Add(self.m_tree, 1, wx.ALL | wx.EXPAND, 0)

        self.image_list = wx.ImageList(16, 16)
        self.ico_folder_idx = self.image_list.Add(
            wx.ArtProvider.GetBitmap(wx.ART_FOLDER, wx.ART_OTHER, (16, 16))
        )
        self.ico_folder_open_idx = self.image_list.Add(
            wx.ArtProvider.GetBitmap(wx.ART_FILE_OPEN, wx.ART_OTHER, (16, 16))
        )
        self.ico_file_idx = self.image_list.Add(
            wx.ArtProvider.GetBitmap(wx.ART_NORMAL_FILE, wx.ART_OTHER, (16, 16))
        )
        self.ico_colors_idx = []
        for i, icon in enumerate(co.ICONS):
            self.ico_colors_idx.append(self.image_list.Add(co.GetMondrianBitmap(i)))

        self.m_tree.AssignImageList(self.image_list)

        for item_idx in (self.m_tree_root, self.m_tree_local, self.m_tree_online):
            self.m_tree.SetItemImage(item_idx, self.ico_folder_idx, wx.TreeItemIcon_Normal)
            self.m_tree.SetItemImage(item_idx, self.ico_folder_open_idx, wx.TreeItemIcon_Expanded)

        self.m_staticline_left_bottom = wx.StaticLine(self.m_panel1, wx.ID_ANY, wx.DefaultPosition, wx.DefaultSize,
            wx.LI_HORIZONTAL)
        bSizer5.Add(self.m_staticline_left_bottom, 0, wx.EXPAND | wx.ALL, 0)

        bSizer61 = wx.BoxSizer(wx.HORIZONTAL)

        self.m_btn_add = wx.BitmapButton(self.m_panel1, wx.ID_ADD,
            co.GetMondrianBitmap(fn="add"),
            wx.DefaultPosition,
            wx.DefaultSize, wx.BU_AUTODRAW|wx.NO_BORDER)
        self.m_btn_add.SetToolTipString(u"添加")
        bSizer61.Add(self.m_btn_add, 0, wx.EXPAND|wx.TOP|wx.BOTTOM|wx.LEFT, 5)

        self.m_btn_refresh = wx.BitmapButton(self.m_panel1, wx.ID_REFRESH,
            co.GetMondrianBitmap(fn="arrow_refresh"),
            wx.DefaultPosition,
            wx.DefaultSize, wx.BU_AUTODRAW|wx.NO_BORDER)
        self.m_btn_add.SetToolTipString(u"刷新")
        bSizer61.Add(self.m_btn_refresh, 0, wx.EXPAND|wx.TOP|wx.BOTTOM|wx.LEFT, 5)

        self.m_btn_edit_info = wx.BitmapButton(self.m_panel1, wx.ID_EDIT,
            co.GetMondrianBitmap(fn="pencil"),
            wx.DefaultPosition,
            wx.DefaultSize, wx.BU_AUTODRAW|wx.NO_BORDER)
        self.m_btn_add.SetToolTipString(u"编辑")
        bSizer61.Add(self.m_btn_edit_info, 0, wx.EXPAND|wx.TOP|wx.BOTTOM|wx.LEFT, 5)

        self.m_btn_del = wx.BitmapButton(self.m_panel1, wx.ID_DELETE,
            co.GetMondrianBitmap(fn="delete"),
            wx.DefaultPosition,
            wx.DefaultSize, wx.BU_AUTODRAW|wx.NO_BORDER)
        self.m_btn_del.SetToolTipString(u"删除")
        bSizer61.Add(self.m_btn_del, 0, wx.EXPAND|wx.TOP|wx.BOTTOM|wx.LEFT, 5)

        bSizer5.Add(bSizer61, 0, wx.EXPAND, 5)

        bSizer4.Add(bSizer5, 1, wx.EXPAND, 5)

        self.m_staticline_main = wx.StaticLine(self.m_panel1, wx.ID_ANY, wx.DefaultPosition, wx.DefaultSize,
            wx.LI_VERTICAL)
        bSizer4.Add(self.m_staticline_main, 0, wx.EXPAND | wx.ALL, 0)

        bSizer6 = wx.BoxSizer(wx.VERTICAL)

        self.m_textCtrl_content = self.makeTextCtrl(bSizer6)

        bSizer7 = wx.BoxSizer(wx.HORIZONTAL)

        self.m_panel3 = wx.Panel(self.m_panel1, wx.ID_ANY, wx.DefaultPosition, wx.DefaultSize, wx.TAB_TRAVERSAL)
        bSizer71 = wx.BoxSizer(wx.HORIZONTAL)

#        self.m_btn_save = buttons.GenBitmapTextButton(self.m_panel3, wx.ID_SAVE, co.GetMondrianBitmap(fn="disk"), u"保存")
#        bSizer71.Add(self.m_btn_save, 0, wx.ALL, 0)

        self.m_panel3.SetSizer(bSizer71)
        self.m_panel3.Layout()
        bSizer71.Fit(self.m_panel3)
        bSizer7.Add(self.m_panel3, 1, wx.EXPAND | wx.ALL, 5)

#        self.m_btn_apply = buttons.GenBitmapTextButton(self.m_panel1, wx.ID_APPLY,
#            co.GetMondrianBitmap(fn="accept"), u"应用",
#            size=wx.Size(-1, 24),
#            style=wx.BU_AUTODRAW|wx.STATIC_BORDER)
        #        self.m_btn_apply = wx.Button(self.m_panel1, wx.ID_APPLY, u"应用", wx.DefaultPosition, wx.DefaultSize, 0)
        self.m_btn_apply = wx.BitmapButton(self.m_panel1, wx.ID_APPLY,
            co.GetMondrianBitmap(fn="accept"),
            wx.DefaultPosition,
            wx.Size(60, -1), wx.BU_AUTODRAW|wx.SIMPLE_BORDER)
        self.m_btn_apply.SetToolTipString(u"应用当前 hosts 方案")
        bSizer7.Add(self.m_btn_apply, 0, wx.ALL, 5)

        if cls_TaskBarIcon and os.name == "nt":
            # ubuntu 10.04 下点击这个图标时会报错，图标的菜单无法正常工作
            # ubuntu 11.04 下这个图标总是无法显示
            # 由于跨平台问题，暂时决定只在 windows 下显示快捷的任务栏图标
            # 参见：http://stackoverflow.com/questions/7144756/wx-taskbaricon-on-ubuntu-11-04
            self.m_btn_exit = buttons.GenBitmapTextButton(self.m_panel1, wx.ID_CLOSE, co.GetMondrianBitmap(fn="door"), u"隐藏")
            #            self.m_btn_exit = wx.Button(self.m_panel1, wx.ID_CLOSE, u"隐藏", wx.DefaultPosition, wx.DefaultSize, 0)
            bSizer7.Add(self.m_btn_exit, 0, wx.ALL, 5)

        self.m_staticline_right_bottom = wx.StaticLine(self.m_panel1, wx.ID_ANY, wx.DefaultPosition, wx.DefaultSize,
            wx.LI_HORIZONTAL)
        bSizer6.Add(self.m_staticline_right_bottom, 0, wx.EXPAND | wx.ALL, 0)

        bSizer6.Add(bSizer7, 0, wx.EXPAND, 5)

        bSizer4.Add(bSizer6, 5, wx.EXPAND, 5)

        self.m_panel1.SetSizer(bSizer4)
        self.m_panel1.Layout()
        bSizer4.Fit(self.m_panel1)
        bSizer1.Add(self.m_panel1, 1, wx.EXPAND | wx.ALL, 0)

        self.SetSizer(bSizer1)
        self.Layout()

        self.Centre(wx.BOTH)

        self.font_bold = wx.SystemSettings.GetFont(wx.SYS_DEFAULT_GUI_FONT)
        self.font_bold.SetWeight(wx.BOLD)
        self.font_normal = wx.SystemSettings.GetFont(wx.SYS_DEFAULT_GUI_FONT)
        self.font_normal.SetWeight(wx.NORMAL)

        self.font_mono = wx.Font(10, wx.ROMAN, wx.NORMAL, wx.NORMAL, faceName="Courier New")


    def alert(self, title, msg):
        dlg = wx.MessageDialog(None, msg, title, wx.OK | wx.ICON_WARNING)
        dlg.ShowModal()
        dlg.Destroy()


    def makeTextCtrl(self, container):

        from HostsCtrl import HostsCtrl

        txt_ctrl = HostsCtrl(
            self.m_panel1, self.ID_HOSTS_TEXT, #wx.EmptyString,
            pos=wx.DefaultPosition,
            size=wx.DefaultSize,
            style=wx.TE_MULTILINE|wx.TE_RICH2|wx.TE_PROCESS_TAB|wx.HSCROLL|wx.NO_BORDER)
        txt_ctrl.SetMaxLength(0)

        container.Add(txt_ctrl, 1, wx.ALL | wx.EXPAND, 0)

        return txt_ctrl


    def OnClose(self, event):

        self.Hide()
        return False




class AboutHtml(wx.html.HtmlWindow):

    def __init__(self, parent, id=-1, size=(480, 360)):

        wx.html.HtmlWindow.__init__(self, parent, id, size=size)
        if "gtk2" in wx.PlatformInfo:
            self.SetStandardFonts()


    def OnLinkClicked(self, link):

        wx.LaunchDefaultBrowser(link.GetHref())


class AboutBox(wx.Dialog):
    u"""关于对话框

    参考自：http://wiki.wxpython.org/wxPython%20by%20Example
    """

    def __init__(self, version=None, latest_stable_version=None):

        wx.Dialog.__init__(self, None, -1, u"关于",
                style=wx.DEFAULT_DIALOG_STYLE|wx.THICK_FRAME|wx.TAB_TRAVERSAL
            )

        update_version = u"欢迎使用！"
        co.log([version, latest_stable_version])
        if latest_stable_version and latest_stable_version != "0":
            cv = co.compareVersion(version, latest_stable_version)
            if cv < 0:
                update_version = u"更新的稳定版 v%s 已经发布！" % latest_stable_version
            else:
                update_version = u"您正在使用最新稳定版本。"
            

        hwin = AboutHtml(self)
        hwin.SetPage(u"""
            <font size="9" color="#44474D"><b>SwitchHosts!</b></font><br />
            <font size="3" color="#44474D">%(version)s</font><br /><br />
            <font size="3" color="#909090"><i>%(update_version)s</i></font><br />
            <p>
                本程序用于在多个 hosts 之间快速切换。
            </p>
            <p>
                主页：<a href="http://oldj.github.io/SwitchHosts/">http://oldj.github.io/SwitchHosts/</a><br />
                <!--源码：<a href="https://github.com/oldj/SwitchHosts">https://github.com/oldj/SwitchHosts</a><br />-->
                作者：<a href="http://oldj.net">oldj</a><br />
                <br />
                以下网友对本软件也有贡献：<br />
                <a href="http://weibo.com/charlestang">@charlestang</a>,
                <a href="http://weibo.com/allenm56">@allenm</a>,
                <a href="http://www.weibo.com/emersonli">@emersonli</a> <br />
                <br />
                <font color="#909090">本程序完全免费，如果您觉得它还不错，欢迎<a href="https://me.alipay.com/oldj">捐赠</a>支持作者，谢谢！</font>
            </p>
        """ % {
            "version": version,
            "update_version": update_version,
        })

        hwin.FindWindowById(wx.ID_OK)
        irep = hwin.GetInternalRepresentation()
        hwin.SetSize((irep.GetWidth() + 25, irep.GetHeight() + 30))
        self.SetClientSize(hwin.GetSize())
        self.CenterOnParent(wx.BOTH)
        self.SetFocus()


class Dlg_addHosts(wx.Dialog):

    def __init__( self, parent ):
        wx.Dialog.__init__(self, parent, id=wx.ID_ANY, title=wx.EmptyString, pos=wx.DefaultPosition,
            size=wx.Size(400, 200), style=wx.DEFAULT_DIALOG_STYLE)

        self.SetSizeHintsSz(wx.DefaultSize, wx.DefaultSize)

        bSizer9 = wx.BoxSizer(wx.VERTICAL)

        self.m_panel9 = wx.Panel(self, wx.ID_ANY, wx.DefaultPosition, wx.DefaultSize, wx.TAB_TRAVERSAL)
        bSizer10 = wx.BoxSizer(wx.VERTICAL)

        bSizer231 = wx.BoxSizer(wx.HORIZONTAL)

        self.m_radioBtn_local = wx.RadioButton(self.m_panel9, wx.ID_ANY, lang.trans("local_hosts"), wx.DefaultPosition, wx.DefaultSize, 0)
        self.m_radioBtn_local.SetValue(True)
        bSizer231.Add(self.m_radioBtn_local, 0, wx.ALL, 5)

        self.m_radioBtn_online = wx.RadioButton(self.m_panel9, wx.ID_ANY, lang.trans("online_hosts"), wx.DefaultPosition, wx.DefaultSize,
            0)
        bSizer231.Add(self.m_radioBtn_online, 0, wx.ALL, 5)

        bSizer10.Add(bSizer231, 1, wx.EXPAND, 5)

        bSizer111 = wx.BoxSizer(wx.HORIZONTAL)

        self.m_staticText21 = wx.StaticText(self.m_panel9, wx.ID_ANY, u"方案名：", wx.DefaultPosition, wx.Size(60, -1), 0)
        self.m_staticText21.Wrap(-1)
        bSizer111.Add(self.m_staticText21, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 5)

        self.m_textCtrl_title = wx.TextCtrl(self.m_panel9, wx.ID_ANY, wx.EmptyString, wx.DefaultPosition, wx.DefaultSize
            , 0)
        self.m_textCtrl_title.SetMaxLength(32)
        self.m_textCtrl_title.SetToolTipString(u"在这儿输入方案名称。")

        bSizer111.Add(self.m_textCtrl_title, 1, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 5)

        bSizer10.Add(bSizer111, 1, wx.EXPAND, 5)

        bSizer1612 = wx.BoxSizer(wx.HORIZONTAL)

        self.m_staticText512 = wx.StaticText(self.m_panel9, wx.ID_ANY, u"URL：", wx.DefaultPosition, wx.Size(60, -1), 0)
        self.m_staticText512.Wrap(-1)
        bSizer1612.Add(self.m_staticText512, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 5)

        self.m_textCtrl_url = wx.TextCtrl(self.m_panel9, wx.ID_ANY, u"http://", wx.DefaultPosition, wx.DefaultSize, 0)
        self.m_textCtrl_url.SetMaxLength(1024)
        self.m_textCtrl_url.Enable(False)
        self.m_textCtrl_url.SetToolTipString(u"在这儿输入方案的url地址，如：\nhttp://192.168.1.100/hosts/sample.hosts 。")

        bSizer1612.Add(self.m_textCtrl_url, 1, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 5)

        bSizer10.Add(bSizer1612, 1, wx.EXPAND, 5)

        self.m_panel9.SetSizer(bSizer10)
        self.m_panel9.Layout()
        bSizer10.Fit(self.m_panel9)
        bSizer9.Add(self.m_panel9, 2, wx.EXPAND | wx.ALL, 5)

        self.m_staticline211 = wx.StaticLine(self, wx.ID_ANY, wx.DefaultPosition, wx.DefaultSize, wx.LI_HORIZONTAL)
        bSizer9.Add(self.m_staticline211, 0, wx.EXPAND | wx.ALL, 5)

        m_sdbSizer1 = wx.StdDialogButtonSizer()
        self.m_sdbSizer1OK = wx.Button(self, wx.ID_OK)
        m_sdbSizer1.AddButton(self.m_sdbSizer1OK)
        self.m_sdbSizer1Cancel = wx.Button(self, wx.ID_CANCEL)
        m_sdbSizer1.AddButton(self.m_sdbSizer1Cancel)
        m_sdbSizer1.Realize()
        bSizer9.Add(m_sdbSizer1, 1, wx.EXPAND, 5)

        self.SetSizer(bSizer9)
        self.Layout()

        self.Centre(wx.BOTH)

        self.__binds()


    def __del__( self ):
        pass


    def __binds(self):

        self.Bind(wx.EVT_RADIOBUTTON, self.switchToLocal, self.m_radioBtn_local)
        self.Bind(wx.EVT_RADIOBUTTON, self.switchToOnline, self.m_radioBtn_online)


    def switchToLocal(self, event):

#        print("local!")
        self.m_textCtrl_url.Enabled = False


    def switchToOnline(self, event):

#        print("online!")
        self.m_textCtrl_url.Enabled = True


class Dlg_Import(wx.Dialog):

    def __init__( self, parent ):

        wx.Dialog.__init__(self, parent, id=wx.ID_ANY, title=wx.EmptyString, pos=wx.DefaultPosition,
            size=wx.Size(400, 200), style=wx.DEFAULT_DIALOG_STYLE)

        self.SetSizeHintsSz(wx.DefaultSize, wx.DefaultSize)

        bSizer6 = wx.BoxSizer(wx.VERTICAL)

        self.m_notebook = wx.Notebook(self, wx.ID_ANY, wx.DefaultPosition, wx.DefaultSize, 0)
        self.m_panel_local = wx.Panel(self.m_notebook, wx.ID_ANY, wx.DefaultPosition, wx.DefaultSize, wx.TAB_TRAVERSAL)
        bSizer8 = wx.BoxSizer(wx.VERTICAL)

        self.m_staticText4 = wx.StaticText(self.m_panel_local, wx.ID_ANY, u"请选择档案文件：", wx.DefaultPosition,
            wx.DefaultSize, 0)
        self.m_staticText4.Wrap(-1)
        bSizer8.Add(self.m_staticText4, 0, wx.ALL, 5)

        self.m_filePicker = wx.FilePickerCtrl(self.m_panel_local, wx.ID_ANY, wx.EmptyString, u"Select a file", u"*.*",
            wx.DefaultPosition, wx.Size(180, -1), wx.FLP_DEFAULT_STYLE)
        bSizer8.Add(self.m_filePicker, 0, wx.ALL | wx.ALIGN_CENTER_HORIZONTAL | wx.EXPAND, 5)

        self.m_panel_local.SetSizer(bSizer8)
        self.m_panel_local.Layout()
        bSizer8.Fit(self.m_panel_local)
        self.m_notebook.AddPage(self.m_panel_local, u"本地档案", False)
        self.m_panel_online = wx.Panel(self.m_notebook, wx.ID_ANY, wx.DefaultPosition, wx.DefaultSize,
            wx.TAB_TRAVERSAL)
        bSizer9 = wx.BoxSizer(wx.VERTICAL)

        self.m_staticText41 = wx.StaticText(self.m_panel_online, wx.ID_ANY, u"请输入档案URL：", wx.DefaultPosition,
            wx.DefaultSize, 0)
        self.m_staticText41.Wrap(-1)
        bSizer9.Add(self.m_staticText41, 0, wx.ALL, 5)

        self.m_textCtrl_url = wx.TextCtrl(self.m_panel_online, wx.ID_ANY, u"http://", wx.DefaultPosition, wx.DefaultSize
            , 0)
        bSizer9.Add(self.m_textCtrl_url, 0, wx.ALL | wx.EXPAND, 5)

        self.m_panel_online.SetSizer(bSizer9)
        self.m_panel_online.Layout()
        bSizer9.Fit(self.m_panel_online)
        self.m_notebook.AddPage(self.m_panel_online, u"在线档案", False)

        bSizer6.Add(self.m_notebook, 4, wx.EXPAND | wx.ALL, 5)

        self.m_panel2 = wx.Panel(self, wx.ID_ANY, wx.DefaultPosition, wx.Size(-1, 60), wx.TAB_TRAVERSAL)
        bSizer7 = wx.BoxSizer(wx.VERTICAL)

        m_sdbSizer3 = wx.StdDialogButtonSizer()
        self.m_sdbSizer3OK = wx.Button(self.m_panel2, wx.ID_OK)
        m_sdbSizer3.AddButton(self.m_sdbSizer3OK)
        self.m_sdbSizer3Cancel = wx.Button(self.m_panel2, wx.ID_CANCEL)
        m_sdbSizer3.AddButton(self.m_sdbSizer3Cancel)
        m_sdbSizer3.Realize()
        bSizer7.Add(m_sdbSizer3, 1, wx.EXPAND, 5)

        self.m_panel2.SetSizer(bSizer7)
        self.m_panel2.Layout()
        bSizer6.Add(self.m_panel2, 1, wx.EXPAND | wx.ALL, 5)

        self.SetSizer(bSizer6)
        self.Layout()

        self.Centre(wx.BOTH)

    def __del__( self ):
        pass




########NEW FILE########
__FILENAME__ = VERSION
# -*- coding: utf-8 -*-
#
# author: oldj
# blog: http://oldj.net
# email: oldj.wu@gmail.com
#

VERSION = "0.2.2.1802"

########NEW FILE########
__FILENAME__ = SwitchHosts
# -*- coding: utf-8 -*-
#
# author: oldj
# blog: http://oldj.net
# email: oldj.wu@gmail.com
#

import os
import time
import wx
import libs.common_operations as co
from libs.MainFrame import MainFrame
from libs.VERSION import VERSION as sVer


class SwitchHostsApp(object):
    VERSION = sVer

    def __init__(self):

        sys_type = co.getSystemType()

        self.pwd = os.path.abspath(os.path.split(__file__)[0])
        self.user_home = os.path.expanduser("~")
        self.restart = False
        self.taskbar_icon = None

        self.sys_type = sys_type
        if sys_type != "win":
            self.working_path = os.path.join(self.user_home, ".SwitchHosts")
        else:
            self.working_path = self.pwd

    def run(self):

        # instance_name = None

        while True:

            app = wx.App(False)

            instance_name = "%s-%s" % (app.GetAppName(), wx.GetUserId())
            instance_checker = wx.SingleInstanceChecker(instance_name, self.working_path)
            if instance_checker.IsAnotherRunning():
                dlg = wx.MessageDialog(
                    None,
                    u"SwitchHosts! 已经在运行了或上次没有正常退出，要重新打开吗？",
                    u"SwitchHosts!",
                    wx.YES_NO | wx.ICON_QUESTION
                )
                ret_code = dlg.ShowModal()
                if ret_code != wx.ID_YES:
                    dlg.Destroy()
                    return

                dlg.Destroy()

            frame = MainFrame(
                mainjob=self,
                instance_name=instance_name,
                size=(640, 480),
                version=self.VERSION,
                working_path=self.working_path,
                taskbar_icon=self.taskbar_icon,
            )
            self.restart = False
            self.taskbar_icon = None

            self.app = app
            self.frame = frame
            self.bindEvents()

            frame.Centre()
            frame.Show()
            app.MainLoop()
            app.Destroy()

            time.sleep(0.1)
            if not self.restart:
                break

    def bindEvents(self):
        u"""绑定各种事件"""

        # self.app.Bind(wx.EVT_TASKBAR_LEFT_DCLICK, self.OnTaskBarActivate)
        # self.app.Bind(wx.EVT_MENU, self.OnTaskBarActivate, id=self.TBMENU_RESTORE)
        # self.app.Bind(wx.EVT_MENU, self.OnTaskBarClose, id=self.TBMENU_CLOSE)
        self.app.Bind(wx.EVT_ACTIVATE_APP, self.OnActivate)

    def OnTaskBarActivate(self, event):
        u""""""

        if self.frame.IsIconized():
            self.frame.Iconize(False)
        if not self.frame.IsShown():
            self.frame.Show(True)
        self.frame.Raise()

    def OnActivate(self, event):
        u"""
        Mac 下，程序最小化到 dock 栏后，点击图标默认不会恢复窗口，需要监听事件
        参见：http://wxpython-users.1045709.n5.nabble.com/OS-X-issue-raising-minimized-frame-td2371601.html
        """

        if self.sys_type == "mac" and event.GetActive():
            if self.frame.IsIconized():
                self.frame.Iconize(False)
            if not self.frame.IsShown():
                self.frame.Show(True)
            self.frame.Raise()
        event.Skip()

    def OnTaskBarClose(self, event):
        u""""""
        wx.CallAfter(self.frame.Close)

    def toRestart(self, taskbar_icon):

        self.restart = True
        self.taskbar_icon = taskbar_icon


def main():
    sh = SwitchHostsApp()
    sh.run()


if __name__ == "__main__":
    main()

########NEW FILE########
__FILENAME__ = cls_Hosts
# -*- coding: utf-8 -*-

import os
import json
import chardet
import urllib2

import common_operations as co

DEFAULT_HOSTS_FN = u"DEFAULT.hosts"

class Hosts(object):

    CONFIG_FLAG = "#@SwitchHost!"

    def __init__(self, index=0, path=None, icon_idx=0):

        self.index = index
        self.path = path
        self.dc_path = co.decode(path)
        self.folder, self.fn = os.path.split(path)
#        self.fn = co.decode(self.fn)
#        if os.name == "nt":
#            self.fn = self.fn.decode("GB18030")

        self.title = None
        self.icon_idx = icon_idx
        self.content = ""
        self.is_selected = False

        self.url = None # 如果是在线hosts方案，则此项不为空
        self.last_fetch_dt = None # 如果是在线hosts方案，则此项为最后更新时间

        self.read()


    @property
    def is_read_only(self):

        return self.url is not None


    def read(self):

        if not self.url:
            c = open(self.path, "rb").read().strip() if os.path.isfile(self.path) else ""

        else:
            c = urllib2.urlopen(self.url).read().strip() if co.httpExists(self.url) else ""

#        c = co.decode(c)
        self.setContent(c, save=False)



    def getConfig(self, ln):
        u"""从一行内容中取得配置信息"""

        cfg = None
        v = ln.partition(self.CONFIG_FLAG)[2].strip()
        if v:
            try:
                cfg = json.loads(v)
            except Exception:
                pass

        if cfg:
            self.title = cfg.get("title", self.title)
            self.icon_idx = cfg.get("icon_idx", self.icon_idx)


    def save(self):

        if not self.path:
            return

        cfg = {
            "title": self.title,
            "icon_idx": self.icon_idx,
        }
        if self.url:
            cfg.update({
                "url": self.url,
            })
        cfg_ln = u"%s %s" % (self.CONFIG_FLAG, json.dumps(cfg).replace("\n", "").replace("\r", ""))

        c = self.content
        if not repr(c).startswith("u"):
            c = c.decode("utf-8")

        c = u"%s\n%s" % (cfg_ln, c)
        open(self.path, "wb").write(c.encode("utf-8"))


    def getTitle(self):

        return self.title or self.fn if self.fn != DEFAULT_HOSTS_FN else self.fn


    def setTitle(self, title):

        self.title = title
        self.save()


    def setIcon(self, icon_idx):

        self.icon_idx = icon_idx
        self.save()


    def setContent(self, c, save=True):

        self.content = c #co.encode(c)

        # 查看第一行是否为配置内容
        # 第一行以 #SwitchHost 开头表示为配置信息
        a = [i.strip() for i in c.split("\n")]
        if a[0].startswith(self.CONFIG_FLAG):
            self.getConfig(a[0])
            self.content = "\n".join(a[1:])

        if save:
            self.save()


    def getContent(self):

        c = self.content
        if not repr(c).startswith("u"):
            try:
                cd = chardet.detect(c)
                c = c.decode(cd.get("encoding", "utf-8"))
            except Exception:
                c = c.decode("utf-8")

        return c

########NEW FILE########
__FILENAME__ = common_operations
# -*- coding: utf-8 -*-

u"""
基本操作
"""

import os
import sys
import traceback
import wx
import chardet
import urllib
import re
import threading
import httplib
import urlparse


if os.name == "posix":
    if sys.platform != "darwin":
        # Linux
        try:
            import pynotify
        except ImportError:
            pynotify = None

    else:
        # Mac
        import gntp.notifier

        growl = gntp.notifier.GrowlNotifier(
            applicationName="SwitchHosts!",
            notifications=["New Updates", "New Messages"],
            defaultNotifications=["New Messages"],
            hostname = "127.0.0.1", # Defaults to localhost
            # password = "" # Defaults to a blank password
        )
        growl.register()

from icons import ICONS, ICONS2, ICONS_ICO

def GetMondrianData(i=0, fn=None):
    if not fn:
        idx = i if 0 <= i < len(ICONS) else 0
        return ICONS_ICO[idx]
    else:
        return ICONS2[fn]


def GetMondrianBitmap(i=0, fn=None):
    return wx.BitmapFromImage(GetMondrianImage(i, fn))


def GetMondrianImage(i=0, fn=None):
    import cStringIO

    stream = cStringIO.StringIO(GetMondrianData(i, fn))
    return wx.ImageFromStream(stream)


def GetMondrianIcon(i=0, fn=None):
    icon = wx.EmptyIcon()
    icon.CopyFromBitmap(GetMondrianBitmap(i, fn))
    return icon


def macNotify(msg, title):

#    print("mac nofity!")

    growl.notify(
        noteType="New Messages",
        title=title,
        description=msg,
        sticky=False,
        priority=1,
    )


def notify(frame, msg="", title=u"消息"):

    if os.name == "posix":

        if sys.platform != "darwin":
            # linux 系统
            pynotify.Notification(title, msg).show()

        else:
            # Mac 系统
            macNotify(msg, title)

        return


    import ToasterBox as TB

    sw, sh = wx.GetDisplaySize()
    width, height = 210, 50
    px = sw - 230
    py = sh - 100

    tb = TB.ToasterBox(frame)
    tb.SetPopupText(msg)
    tb.SetPopupSize((width, height))
    tb.SetPopupPosition((px, py))
    tb.Play()

    frame.SetFocus()


def switchHost(obj, fn):
    u"""切换 hosts 为 fn 的内容"""

    from cls_Hosts import Hosts

    if not os.path.isfile(fn):
        wx.MessageBox(u"hosts 文件 '%s' 不存在！" % fn, "Error!")

    ohosts = Hosts(path=fn)

    sys_hosts_fn = getSysHostsPath()

    try:
        a = open(fn, "rb").read().split("\n")
        a = [ln.rstrip() for ln in a]
        if sys_hosts_fn:
            open(sys_hosts_fn, "wb").write(os.linesep.join(a))
        else:
            wx.MessageBox(u"无效的系统 hosts 路径！")

        obj.current_hosts = fn
        title = ohosts.getTitle()

        obj.SetIcon(GetMondrianIcon(), "Hosts: %s" % title)
        notify(obj.frame, u"Hosts 已切换为 %s。" % title)

        ohosts = obj.frame.getOHostsFromFn(fn)
        obj.SetIcon(GetMondrianIcon(ohosts.icon_idx), u"当前 hosts 方案：%s" % ohosts.getTitle())
        obj.frame.SetIcon(GetMondrianIcon(ohosts.icon_idx))
        obj.frame.current_use_hosts_index = ohosts.index


    except Exception:
        err_msg = traceback.format_exc()
        if "Permission denied" in err_msg:
            err_msg = u"权限不足！"
        wx.MessageBox(err_msg, u"hosts 未能成功切换！")


def getSysHostsPath():
    u"""取得系统 host 文件的路径"""

    if os.name == "nt":
        path = "C:\\Windows\\System32\\drivers\\etc\\hosts"
    else:
        path = "/etc/hosts"

    return path if os.path.isfile(path) else None


def encode(s):

#    print("--")
#    print(chardet.detect(s))
    return unicode(s).encode("UTF-8") if s else ""


def decode(s):

    if not s:
        return ""

    cd = {}
    try:
        cd = chardet.detect(s)
    except Exception:
#        print(traceback.format_exc())
        pass

    encoding = cd.get("encoding") if cd.get("confidence", 0) > 0.65 else None
    if not encoding:
        encoding = "GB18030" if os.name == "nt" else "UTF-8"
#    print s, cd, encoding, s.decode(encoding)

    return s.decode(encoding)


def checkLatestStableVersion(obj):

    def _f(obj):
        url = "https://github.com/oldj/SwitchHosts/blob/master/README.md"
        ver = None

        try:
            c = urllib.urlopen(url).read()
            v = re.search(r"\bLatest Stable:\s?(?P<version>[\d\.]+)\b", c)
            if v:
                ver = v.group("version")

        except Exception:
            pass

        obj.setLatestStableVersion(ver)

        return ver

    t = threading.Thread(target=_f, args=(obj,))
    t.setDaemon(True)
    t.start()


def httpExists(url):
    host, path = urlparse.urlsplit(url)[1:3]
    found = 0
    try:
        connection = httplib.HTTPConnection(host)  ## Make HTTPConnection Object
        connection.request("HEAD", path)
        responseOb = connection.getresponse()      ## Grab HTTPResponse Object

        if responseOb.status == 200:
            found = 1
        elif responseOb.status == 302:
            found = httpExists(urlparse.urljoin(url, responseOb.getheader('location', '')))
        else:
            print "Status %d %s : %s" % (responseOb.status, responseOb.reason, url)
    except Exception, e:
        print e.__class__, e, url
    return found



########NEW FILE########
__FILENAME__ = highLight
# -*- coding: utf-8 -*-

import wx
import re
import sys


if sys.platform != "darwin":
    font_mono = wx.Font(10, wx.ROMAN, wx.NORMAL, wx.NORMAL, faceName="Courier New")

else:
    # 系统是 Mac OS X
    font_mono = wx.Font(12, wx.ROMAN, wx.NORMAL, wx.NORMAL, faceName="Monaco")


def __highLightOneLine(txtctrl, ln, start_pos, styles):

    ln_content, t, ln_comment = ln.partition("#")
    end_pos = start_pos + len(ln)
    txtctrl.SetStyle(start_pos, end_pos, wx.TextAttr(styles["color_normal"], "#ffffff", styles["font_mono"]))

    # 行正文部分
    re_ip = re.match(r"^(\s*[\da-f\.:]+[\da-f]+)\s+\w", ln_content)
    if re_ip:
        s_ip = re_ip.group(1)
        pos2 = start_pos + len(s_ip)
        pos = pos2 - len(s_ip.lstrip())
        txtctrl.SetStyle(pos, pos2, wx.TextAttr(styles["color_ip"], "#ffffff", styles["font_mono"]))
    elif len(ln_content.strip()) > 0:
        pos2 = start_pos + len(ln_content)
        txtctrl.SetStyle(start_pos, pos2, wx.TextAttr(styles["color_error"], "#ffffff", styles["font_mono"]))

    # 行注释部分
    if t:
        pos = start_pos + len(ln_content)
        txtctrl.SetStyle(pos, end_pos, wx.TextAttr(styles["color_comment"], "#ffffff", styles["font_mono"]))


def highLight(txtctrl, styles=None, old_content=None):

    default_style = {
        "color_normal": "#000000",
        "color_bg": "#ffffff",
        "color_comment": "#339933",
        "color_ip": "#0000cc",
        "color_error": "#ff0000",
        "font_mono": font_mono,
    }
    if styles:
        default_style.update(styles)
    styles = default_style

    content = txtctrl.Value.replace("\r", "")
    lns = content.split("\n")
    if old_content:
        old_content = old_content.replace("\r", "")
        lns_old = old_content.split("\n")
    else:
        lns_old = None
    pos = 0

    for idx, ln in enumerate(lns):
        ln_old = None
        if lns_old and idx < len(lns_old):
            ln_old = lns_old[idx]

        if not ln_old or ln != ln_old:
            __highLightOneLine(txtctrl, ln, pos, styles)

        pos += len(ln) + 1



  
########NEW FILE########
__FILENAME__ = icons
# -*- coding: utf-8 -*-

ICONS = [
    '\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x10\x00\x00\x00\x10\x08\x02\x00\x00\x00\x90\x91h6\x00\x00\x00\x19tEXtSoftware\x00Adobe ImageReadyq\xc9e<\x00\x00\x01BIDATx\xda\x94R;n\x02A\x0c\xb5w\x06\x90\x16\xa4\xa4CJ\x91S\xa4\xe0(\xd4\xa4\x8ar\x01\xeeA\x94\x88:w\x88r\x10\xd2\xa6\xa4D\xbb\r\xbb\xcbx\xc6\x19{1\x10)\x05\x19\xb9\xf0g\x9e\x9f\x7f\xc8\xcc\xf0\x9f\x87/O\xd7~}~\x95\xd4>%x\\_\x05\xd8\xbfa\xc9\xecc\x02R\x9bU\x84T\xe5O\xcfv\xbb-(B\x00\x91\x03\xc0d\xb3\xb9e\x0e\xd3\xe9\xc9\x93\xcd,\x078\xfe\x91\x92(A\x87\x82\x8f\x00T\xd7\x1e\xa0!r\xea\xc9\xcc\xa9\xae\xb3\xd2 z+\xcc\x13A\xa7\x1a)&\xbfl:U\x82\x95\xd4\x02\x0cT\x19e@\x88b\xf7\xe1\xa4JUU^\x8b\x16O\x08\xe8}c\xb9\x04@\x068\x18\xe0\x81\xe8r8a\xb7k,t#\x0c$%\xf6\x95\xf4i\xbeW+?\x1eKWm{\xbfX\x00\xe2\x1e1\x9d{0\x86\xce\xd2|-\x97\x83V|\x1d\xf3\xdd|^8\xd7\\\x10\x9e\x01\xad1\xa4\xb2\xcc\xb93)!\xa2s\xac!\xbc\x04t\xd6t1\x1c\xca\xb8\x9c\x8b\xd6\xb4\x1b\x8d\x8e\xa1\x13 \xda\x1er=\x1f\xb3\x19\xeb\x04\x9dm\xe6}2\xc9\xca\x00\xb13@\xb1\xfe\xe4~\x8bQ\xd38E\x06\x9b\xb2\xfb\xed\x913\xe9\xcf;\x1f\xc9\x957\xfb#\xc0\x00\x82\xf4\xa4-,\x9a\x06\xe0\x00\x00\x00\x00IEND\xaeB`\x82'
    ,
    '\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x10\x00\x00\x00\x10\x08\x02\x00\x00\x00\x90\x91h6\x00\x00\x00\x19tEXtSoftware\x00Adobe ImageReadyq\xc9e<\x00\x00\x01oIDATx\xda\x94R;N\x031\x10\x1d\x7f6\x10@\x88\x02\t\t\x89S *\x1a\xc4\x05\xd2\xa6\x06\x1aDC\xc71(@H\\\x008\x01\xcaA\x10-]\xe8P"\x85\xd8^\xffx\xe3\xdd\r\x08\x9a0\xb2\xe4\xf1\xf3\xbc\x997\xf6\x88\x9c3\xfd\xc7\xc4\xed\xf9\xb2\xa1\x17w\x9cZ\xa7D\xa7GK\x11\xe6Obm\x98uL\x14\x02\x9fs\xa2\xec\xb1\x91\xa8H\xa8\x82\xc4\x82\xd072\x1e\x8fe\x88\xe4\x1d\xafzF\x1b\x83\x97\xad\xb3\xec\xc3\x8e\xb7-\x82#\x16\x9c&\x86%\x85Du\xf1\xa2\xa1\xf09\xd5\xdbdg^i\xa4\xa50\xa7d\xa7\xb8\xb2s\xd2\xa2\x15\xa6\xa1\xc7Y\xf6\x82%\xf4\x03s\x8eT`\x02\xea4Oh-UER\x0f\x04\x1f\xc9\x1a>xC\xb1\x10&\xef\x13\xbd\x8ax&\xa4\xe0\x85\xd2\x06W\xb2#\xa0\x07T\x84\xd5\xa6\xad\xb0\x7f\x1d\x7f>\x8e\x9f}\x18h+\x926\xb9Bh+\xd4]\x85\xb7\xe7\x9b\xaa\xbf\xce"\x9d\xdd;>\x818T\xc8r\xd1C\'\xc9u\x15^\x1f\xaf*m\x84`|\xf7p(\xa4\xe2\x80\xbf\x04\xdb\x11\x92\xec\xc7\xc4\x04\xfe\x1f\xa9\xd0\xb6\xf9EpM\xd35I\xddc%IEG \x00Q\xd5J{\xb5 \xc4\xee\x1f\x90~ty\x80|\x95&\xd5\xfct\xa6\x87A\x9f\x1f\xa7jc`\xf2~\x94\x91\x00+\x06\x92\x82\x94\xa0\x14i\x81\xa8\x82\xc0i\x10\x1e\x93f\xbc1$K\xce\xec\x97\x00\x03\x00v\x00\xe3n\xbf .\x97\x00\x00\x00\x00IEND\xaeB`\x82'
    ,
    '\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x10\x00\x00\x00\x10\x08\x02\x00\x00\x00\x90\x91h6\x00\x00\x00\x19tEXtSoftware\x00Adobe ImageReadyq\xc9e<\x00\x00\x01`IDATx\xda\x94R;N\x03A\x0c\xb5g&A\t\x05\x05\x12\xd4 \xa44\xb4\x1c\x83\x9e\x1a*D\x8b\xc4A@ \xee\xc0\x01\xe8\xb8@\xca\x9444\xa1\x8bH\x01\xbb;\x1f\x0f\xcf\xbb;\xb0t\xc1\x1aifl?\xfb\xf9\xc39g\xfa\x8f\xf0\xdd\xe5\xa6\xaeW\xf7\x1a\xda\x89\xd0\xc5\xf5F\x80\xafW\x9e\x1ee\x97\x84Rj\x15\x99r"\x10dKlZ\x85\xa8Fi\x14\xcdr\xb941Q\nzBM\xd3\x83\xc5\xceq\x96\xb8\xdfibM\xf8\xe2\xe0\xd1i\x94R\x14\x8a\xed+y\xa8\xd6\x8e\xc8W\xc1\xe0bJ\rI\\\xc3\x14\x1a\xb2\x85\x98\x8b\x91\x82\xef\x01\xe0\x00\xf1\x81\xac( 6\xcaS5\r9.\x80\x904\x00\x04fi\x01\x9f\xab\x0f7\xeeC\x88\x046\x0e\x80\xdc\x02\x9cfH\x1a`\x08\x98\x9d\xa6asb\xb3\xf2\xf5\x00\x10b\x9f\x01Ew\x94\xde\x17\xb7n\xbc\xad\x19b\xbd7;\x079\x8dh~j(\x19|\xc9\xf06\xbfq\xe3\x8a\x19\xd5\xd3\xee\xe1\x19\xb3m\xea\xbf\x80>C\xd3g\xc8<\xa1\\\xa1Z\xe0\xe1\xdd\x99\x8c\x1d\x02\xda.\xa1\xb9l\xb5X\x11\xeb=\\\t\r4vKMx\xf8\x02He\x0e\x089\x7f:\xc1eGdK\xbc\x97\x87\x89:\x8dz\x1f\x88y|\xce\xdd\x14\xb1\x05\xd6\xb4\xae\xd2\xcf\x15\x0c\xf1\xc5\xc9\xf2;i\xee\xd6\x1bK\xb2\xe1\xce~\x0b0\x00/\x90\xde\r\xb1\x84\xfc\xbb\x00\x00\x00\x00IEND\xaeB`\x82'
    ,
    '\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x10\x00\x00\x00\x10\x08\x02\x00\x00\x00\x90\x91h6\x00\x00\x00\x19tEXtSoftware\x00Adobe ImageReadyq\xc9e<\x00\x00\x01yIDATx\xda\x94R\xbdJ\x03A\x10\x9e\xfd\xb9\x0b\x18\xd4g\x10\x14K{\xcd\x13h\x9b\xd6\xc2R\xac|\x01_B\t\xb1\x13\xc1\'\xd0\xc2\x07\xb0\xb2S\x10\x11\xfb\x80\xa0\xa8\xb1\xf0\xb2\xbb\xb3\xe3\xb7\xb7w\xe1\xca\x18\x960\xfb\xdd|\xf3}\xb33JD\xe8??uv\xb8h\xea\xd1(\x95\xb61\xd2\xf8xg\x11\xc2\xe8e\xf0\xb4yg9\x92p\xba\x8bDf\x86Cc\xac\xd6\x1aH\x8c@\x02\x8292\x99Lt`\xe2\xfa8\xc7\xd7\xebW\xaf[\xf7+q\x19D \xde\x05\\q\x10\xe4\x9cd)Db\x9f"vq\xea\xa6\xb4D\xd5\xafc\x8b\xee(\xcc\xe24\xfc\xe0\x13\x02\xd5\x1a\xb3!\x10\x87\xd4\r\xfe\xf3\x83\xc1\x05\x93\x80\xc0^(#^\xb4i\x1e\xd3z\xa6\xe0\xa8.\x03\xd7)x\xff\xfePE\x92`\xe7|\x0cV\x1bv\xa4\xf4\\\x81\x1bK\xd1SVx\xdb}\xec>\xce\xa7\xfbB\x822-\xc1\x87F\x01e\xb2\xc2\xf8\xf9\xb2_\xf6\x11T\xbe\xda\xdf\x18*Q\x0c\xf1\xaeB\xc8\n\xaeQ8y8uej2V\xb3\xe1\xda\x9eQ\x06\tb\xbb\x04\xd7\x10\xb2B\xa9\xfa\x95\xc0\xb5\xc2\x184\x19T\x81\x82\x98n\x0f\xa1\x1e\\\xd4\x85\xe9\xa5m\xa1\x82QC%\xa4g\xcbz\x82ZBK\xe0v\x0e(\xb2}s\x00[\xe9\x89L\xb6lW/\x06\xa9\x04\x10\xdf\x10\xf4\xf9-V\x82\xd2\x11-\xb6\x90\xa2\x8c\xa4\x1b\x844\xae]$\x91\xf3\xb4\xb0$\x0b\xee\xec\x9f\x00\x03\x00\x0e\x92\xf8X\x0b\x11D3\x00\x00\x00\x00IEND\xaeB`\x82'
    ,
    '\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x10\x00\x00\x00\x10\x08\x02\x00\x00\x00\x90\x91h6\x00\x00\x00\x19tEXtSoftware\x00Adobe ImageReadyq\xc9e<\x00\x00\x01xIDATx\xda\x94R;N\x031\x10}c{\t\n\x91\xa0C\xa2\xe0\x12P\xc0\x01\xe8r\x80\xd4t\x88\x88\x9a\x82\x03\xd0\x83\x90\xa8\xb9\x02 J\x0e\x01-e$\x1a\x94\x14\xec\xda\xeb\x1f3\xdeE\x89D\x13V\x96<~\xfb\xde\xbc\xf1\x8c)\xe7\x8c\xff|t{\xb6.\xf5\xfcNR\x9b\x94p1\xfe^G0}\xac\xf3xhb\x02B\x10 e\xf8\x0c\xceR\x114\t\x12\x0b\x82%2\x9b\xcdT\x88\x80\xf7\xb2\x9a\xf6\xedd\x94\';\xbb\xd1\xa3-H\xdd\xf2\x91\x17\x07=\x87K\n\t\xe4\x9d\xa4qq\xd1\x04A\xea\x86*\r\xce\xe8\xc2\xc2%\xb9\xa8k\xa0MW\x98\x91r\\\x11\xd8\x80\x1c%`}*\x02\xeb\xd1\xf5\xd0Z\xe8\xaa\xf0\x07\xc63\xc7\xd9\xe2\xe0\x91$\xdf\xfcs\x8eM\xceG,\xf01\x19E`\x07\x13{AX\n\xdaN\x10\xae\x0eW\x9b\xf3U\xfb"H\xe5\xb4m|\x00\xd9\xa6\xf8r%\x92\xe6\xe6\xf5cK\x1c`\xdbxz\xbc\xcf\xa5\x91\xad\xa1\xd3\xef\x1d\x96\x0e\x0eY\xd0\xcb\xa7w[U\\Q\xae\xdd\xe4`O+U\x1c\xf0W`;\x87\xa1J\x16\x1c\x10\xe5\xa0\x89\xe4\xde\xfc\xcb\xd0\x8a\xa0-]\n~\xc3(\xde5\x02\xda\xc8|D?\xe0\xfe\xca\x04y2\xaa\x17\xf0\xa4\xa9\x13\xe4tt\xfd\xcc\x1b\xaa\x8at\xe1\xe58\x9a>\xc8\x1c\xb8\xc2\x8e\x03\xa8\xfb\x97\xdcO1Fh\x05\xa6r\xaf:\x84\x03>\xae",\xee\x9e7?\x925\xdf\xec\x8f\x00\x03\x00\xca\xf2\xe6L,ZXW\x00\x00\x00\x00IEND\xaeB`\x82'
    ,
    '\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x10\x00\x00\x00\x10\x08\x02\x00\x00\x00\x90\x91h6\x00\x00\x00\x19tEXtSoftware\x00Adobe ImageReadyq\xc9e<\x00\x00\x01\x7fIDATx\xda\x94RM.\x84A\x10\xad\xea\x9f\x19\xf1\x13\xb6,\\\xc1FD\xe2\x16b\x87\x03\x08q\x05{k\x11b9\'\xb0\x117\xb0&\x91XY\x8e\x85\x04#\xcc\xf7\xd3U\xd5\xaa\xbbg\x10\xab\xd1\xe9E\xf5K\xbfW\xaf^7\xc6\x18\xe1?\x0bO\xf6&\xbd\xba\x7f\x9a\xa4\x9d\x08\x1c\xde|NB8X\x19\xc6\xdbi\xc7\x02V(\x01\xea\x8d#\xa8\x8aE0\x98\x10\xc9\x08\xfc \xfd~\xdf\x10\x83\xe5\xa0\xdb\xb4\xed\xdd\xe5,=,,\xce\x85oD\x8f\xba\xb5(H\xb2D\x02\x9e\x9b$G<\x18P2YW\x9e,\xa0"4x\x97|\xa92\xc6\x15c\x8e\x08\\!\x08!p\xea/\x8d\x13\x9b\x11\x95,\x83\xd6\x86}\xbe\xdfu\x81\xa1C\xb5\x96L\x01c\xd2\xfbx~\xcbz\x08\x14(\x88s\xe8\xa9\xb2\xc8#\x82\xce\xe03\xc1p\xab\xa2Z\xbc<\xad\xfe\x0e\xe7\xf558\xae\x1cJ>\xcd\xbb@\xd0\t\x95\x96\xc4\r\xc6$sq\xf683\x93\x1cW5o\xef.#\x82\x0fC\x1fe<\xc3\xb8\x03HS,\x1d\x1f\xdds\x9b\x1c\x934\x9b[K\xd6\x1a\xed\xe0\xc7\r3\x81\x0b\xa1.C\xcfw\xa5j\xb4\xc06\x92\xd5\xf8c\xf4R{\xc0\xdf\x1dRJ\x18C\xd7\x1b-\xa6\x80\x88\x12\x01\x14\xe9\xa6\xb8:\x1c\xbc\x98\x11A_\xba\xc4j@v6\xae4G\x8b\xde\x81\xcd\x08\xaf-\xf4R4\xa8J\xcd\x88p~\x1d\xd7;\xbd\xb1\xc3"#%\xae\xbc\xec\x1f\x04\xcb\xf7\xd6O2\xe1\x9f\xfd\x12`\x00<\xc3\xdf\xc5\xc5W\xde\x19\x00\x00\x00\x00IEND\xaeB`\x82'
    ,
    '\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x10\x00\x00\x00\x10\x08\x02\x00\x00\x00\x90\x91h6\x00\x00\x00\x19tEXtSoftware\x00Adobe ImageReadyq\xc9e<\x00\x00\x016IDATx\xda\x94R;n\x850\x10\xc4\xc6\x80\xc4\x958\x00%W\xa0J\xf4\x94cp\x83(\n\xa2&\x05GH\xc3-r\x06$Z\x04\xe2clg\xf0&\xce\x0bJA\xb6\x1a\xc6;\xe3\xd95\xcc\x18\xe3\xfd\xa7\xd8\xcb\xedj\xeb\xd3\xeba\xcd\x9e\x1f\xbd\x0f\xf3pQSU\x95P\xda\xd3F\xe3Ck-\xa5D\xc2 \x08|\xdf\x07\xa3\x94\xda\xb6\r \x0cCb\xba\xae\xe3\xbb\xf2v[\xf3<\x17EQ\xd7\xb5\x10\x02Jb\xdel\x01P\x0f4b\xd7\x87\x13\x10\x9a\xc6q\x04\xc0\xf1\x91\x951\xd8O\xd3\x04\x0c\x80k)\x95\x80L\xee\x12\x08\x06\xb41\xe8\x11\x0f\x02\xc7\x00\xc0\xeeK m\xa4{A\xdf\xf7Q\x14\x01\xac\xeb\n\x12\xe9]\x1e{\x83\xf2HM\x13\x03\xb4m{\xbf\x99a\x18~\xdf\xb0\x9f\x05M\xd3\xc4q\x0c\xb0,K\x96et\x84M\x9cop\x91\xca\xb2\xc4\x00\x14)MSD:\x0b\xdc\x0cDa\x00t0[\x9cs\xb8`\r\x7f\xcc\x00\x96v\x87>\x12\x80\xc1\x93\xd1\xd1\xcf\x0c\xea\xfb\x1dPy\x9e\xc3\x0f\xb7\xc3\x98\x94I\x92\x1cMB\xb8\x1e^\xbd\x1b\xda\x1a\xed\x1e\xad\x00\x8e\xe1\xb6\x1cs\xb8\xd0\xa0\xf8I.\xfe\x7f\x9f\x02\x0c\x00\xa0\x0b)T\xc7\x159\xaa\x00\x00\x00\x00IEND\xaeB`\x82'
]

ICONS2 = {
    'door': '\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x10\x00\x00\x00\x10\x08\x06\x00\x00\x00\x1f\xf3\xffa\x00\x00\x00\x04gAMA\x00\x00\xaf\xc87\x05\x8a\xe9\x00\x00\x00\x19tEXtSoftware\x00Adobe ImageReadyq\xc9e<\x00\x00\x01.IDAT8\xcb\xa5\x93=J\x04A\x14\x84k\xfcA\xd7\xc0eE\x03\x15\x0fbd\xe01<\x84\xa1\xb9W\xd8\xdc#\x18ob\xe4\x1d\x0412\x10\x15d\xc1ht\xde\xab*\x83\x1egW\xd0Ya\x1f4\xaf;\xa9\xfe\xaa\xfaue\x1b\xcb\xd4\n\x96\xac\xb5\xf9\xc3\xdd\xd5\xb9%\xc1&HB*\x8b\xcc\xae\x93\x89\x93\x8b\xeb\xeaW\x01\x89\xd8;>\x05LX\x86$X\x04\xc4n\xffps\xfd7\x01\x990\x89\x8f\xf7\'\xb8\xbd\xdd$\xdc\x12ln\xef#\xb3\xe9\x17\x90\x081a\x1511!\x12V\x82\x8c~\x81\xcc(\xb7e\x14\x02f9\x930\x03\xce@D/A+\xd0\xf5\x19E\xe5\x06"\x17\x114\x059\x9a\xe2?\x13Rbg8\xc5\xe1\xc1\x1b\x1e\x9f\x87\xc8\x8c~\x0bj-t\xf8*}:\x1d\xa0\xfe\\\xff\x0fA\x80\xd9\xfc\xb0\xf0\xfa\xb2\x01s\x15[\xbb\xea\'\x88hf!2\xda\xf0Z!\x95=\x19\x0b\x08\xb2d`\x95\xf4\xbf)\xac\xf2\xb4\x0b2(\x16\x06\xa3#\xd8\x82\x99\xb0T\x96\t\xb1\x8c\xf3|U\xb61\x99L\\\xd75\xe2\xf6\xb2\x9b\xf7\xf9\xf9\x9f\xfd\t\xc2&\xeeGg\x00\x80\xf1x\\U\xcb~\xe7/G\xdc}\xb3\x8f\x11?\x1f\x00\x00\x00\x00IEND\xaeB`\x82'
    ,
    'accept': '\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x10\x00\x00\x00\x10\x08\x06\x00\x00\x00\x1f\xf3\xffa\x00\x00\x00\x04gAMA\x00\x00\xaf\xc87\x05\x8a\xe9\x00\x00\x00\x19tEXtSoftware\x00Adobe ImageReadyq\xc9e<\x00\x00\x02\x9fIDAT8\xcb\xa5\x93\xebKSa\x1c\xc7\xfd;v\xcevl\x03\tdD!\x82\x84P{\x15$\x12;\x9a\r\xc5\xbc,K\xd3\xdd\xbd\xd26c\xd8L\x8b2r^\xc6H)-\xb3\xd4jsNm\xea\xd4\xe6\xd6\x942q\xd9QB\xcc\xbd\xe9B\xb5at\xb1o\xe7\xec\xc5L\x12#z\xe0\x0b\x0f\x0f\xcf\xe7\xf3{\xaeq\x00\xe2\xfe\'\x7f\x0c\x14\xf8\x0e\x89r\xa7\x0f\xea\xb3=)L\xc6\xe3\xfda\xe9\x888,u%2Rg\xa2>\xdd\xbeW\xb4\xab \xcf\x9bJ\xcb<\xc9!\x9dG\x86\x9bA\x0b\xfa\x96\xbb\xa2\xe9\\lF\x89\xeb\x18$\xbdTH\xd2C\xd1;\n\xd8\xaat\xe6xR\xe4\xea\x9c\x11\xce\xd5~\xd8^^\x83i\xae2\x1a\xae\xefX\xedC\xe3L\x15\x0e\xd8\xf8\x91d\x1b\x9f\xde&\xc8\xf1\xa4\x083\xddI\xeb\x1c\xccM\xac\t\x94\xa1\xc2_\x02\xcd\xcc\x19\xe8\xd8\x94\xb3\xa9\xf6\x9d\x85\xfd\xf5=\\\x9c\xaa\x80\xd8B\xae\x8b\xaf\x93\xc2\x98@\xe6N2\xa8\xc6\xb2\xa2\x959\x98\x03U\xdeSPL\x17B1U\x00\xf5T!\xdck\x830x\x95p\xb0\x92\xdc\x9e#H\xb8B\x1ab\x82\x8c\x111\xd3\x19l\x865\xd8\x84\n_1\x94O\xe4,\x98\x0f\xe5$\x1bO>\xc6\xdf\xb8\xc0\xb5Pd\rm\xcf\x1ba\x9bkD|=\xc9\xc4\x04G\xed\t\x1b\x0fVn\xa36\xa0\x81\xd6[\xc4\xaed\x00\x8b\x1f\xe6\xa1\x9a(\xc4\xd8\xdaP\x14\xfe\xb1\xf9\x1dm\xcf.\xc10Q\x8c\xbe`\'\x04Fb#&\x90\xdc\xa76\xfa\x97\xbba\xf4\xabP\xeb\xd7\xe2\xd3\xd7\x8fQ\xe8\xfd\x97\xb71\xd82[\x0f\xb5+\x1bz\xf7i\xf4\x07; \xa8\xf9]\xd0C17\xe6\x9b\xd0\xbep\x19\xbaI9\xcc\xbejD\xbe}\x8e\xc2\x9b?7ayz\x01e\xce,hXAK\xa0\x0e\xed^3\xa8*bk\x0b\xa9\xb7\x04\x06\xf9@\x1a\xec+wQ=!\x87\xda}\x12u\xd3\xe5Xz\xb7\x80\xb6\xd9\x06\x94\x0e\x1e\x87\xc2q\x02:g\x0e\xec\xaf\xba\x91n=\x0c\xaa\x92\xd8:\xc4d+_\xb8\x8f\xbd\x1a\xb3G\x83\x87\xcc\x1dT\x8e\xe6A;\x9c\x03\xd5\x90\x0cJ\x07\x17\x0e\xce\xc6\xa3\xa5.\x18\x87\x8a!P\xf3\xd6)5!\xdc\xf6\x90\x12\x9bH:\xbe\x81\x88\x98\xdcep\xb0\x92\xd6\x80\x19\xfa\xd1"\x9c\x1b\x96\xa3\x95\xdd\x82\x9d\x85\xf5\xce"\xf0Ky\x11\x16\xa6w|\xca{\x1aH\x9a2\x11!i\x87\x04\xed~3z_X\xd1;o\x85\xc5kBZK*\x04\n^\x88R\x11\xf4\xae\x9f\x89:O\x8a(\x03\xa1\xa7j\x08F\xa0\xe5\x85\x05*^\x98\xad\xc8\xb0\xd1S\xa5\x84\xe8\xaf\xbf\xf1_\xf3\x0bg\xd0\xac\xe5y\xba\xd4c\x00\x00\x00\x00IEND\xaeB`\x82'
    ,
    'add': '\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x10\x00\x00\x00\x10\x08\x06\x00\x00\x00\x1f\xf3\xffa\x00\x00\x00\x04gAMA\x00\x00\xaf\xc87\x05\x8a\xe9\x00\x00\x00\x19tEXtSoftware\x00Adobe ImageReadyq\xc9e<\x00\x00\x02oIDAT8\xcb\xa5\x93\xebK\x93a\x18\x87\xfd[\xb6/\x05\x83\xa4\x86Y(\xa8)%X(o\xd9l\x8a\x8aN\xdb\x96sk\x8a\xce\xf6n.\x9d\xba\xcd\x03-\x9d\x13\x0f\x15\xb5\xa1\xdbh\xa4;8\x0f\xc3\x03f\xe2\xd4\xd2E\xea\xebP\xa2\x8d"\x08j\xc3\xaf\xbf\xde\x15MG\xcb\x88\x1e\xf8}y\xe0\xba\x9e\xe7\xbe\xb9\xef$\x00I\xff\x93\xdf.t\xd3u\xcc\x0e\x8f\x84lu\x89\xa8\xe6\tAX\xfe\xa2:\xdc\xf0\xbc\x82\x92Z\xcbH\xd1h1\xf3D\x81nZJ\xb4OJB\xcf\xd6{\xb1\x1aZ\x84\xff\xf3\x06\xd6?\xad`2`\x87\xd2S\x03\xbe\x89\x13\xe2=\xb9N$\x14\xfc\x84\xc5\x91\xe9=;\x0e\xbe\xeda\xf6\x83\x0b&j\x10\x8fw\x0c\xb0\xef\x9b\xb0\xf4q\x0e\xda\x05\x19JG\xf2#\xdc\xc1<"N\xa0\x9d\x922h8\xe8\xde\xb5`\xef\xeb6\x86\xb7\xf5x\xb8\xd6\x81n_+\x0c~\x1d\xfa\xfcZto\xb6\xc0}`\x07\xe9\x11\xa2\xd0x%X\xd0\x9b\xcd\x88\thX\xd1\xbf\xac\xc6\xbb/\x9b\xf4\x8b}\xe8\xdd\xd2B\xf3J\x89_G\xbd&\x83|Q\x08\xc5r-\x9c\xfb6\xdc\x1c\xc9A\xde\x83\x0cEL\xd0\xe2\xac\xa1\\\x01\x1b\xfdU3:WUh[\x91C6+\x8a\t\x046.\x1af\xca \x9d*\xc6\xc0\x1b\x1d\xf4K\xcd\xb8\xdc\x9dF\xc5\x04\x8aq\xfe\xa1\xf7\xbd\x0b\xfdou4\xdc\x84?\x1d\xf1d\x11\x14\xf3|X\xfc\xc3\xc8\xd2\xa5\x1e\xc6\x04Mv\xde\xe1D`\x0c\xda\r\x12*_\xfd\x89\x02\xd2[\r\xab\x7f\x08\xe9\x1d\xec#A\xbd\xad\x9c2\xfa\xb40li\xd0\xf4R\x08\xf1|\x05x\xd6\x1bq`4w=\\\xf4\xfb\xd4\xe8\xf2\xde\xc3\x05u\xf2Q\t\xe2\xb1\x12\xc5m+\x01G\xc0\x02\xd9|%$\xde\xd2\x1f5\x1f\x17\x88\x9c\x1c\xd4\xb9\x8b\xe1\xd85\xe3RO*\xd8\xf7YGM\x14\x9a\x8b\x18UO\x0b\x83\xa4G\x80qj4\xd6\xb0(X\xeb\x8c&\ns1\xb1c\xc2\x1d\xcb\xad(\x1cLV\x9ef\xc4\rR\xf9\xa3\x02\xa2d\xe8j\xa4\xd1Q\t\'-1\xfa\xdaA\xceTA>U\t\xe3j\x1b\x1c4,\xb4p\xc0V\xb1"4L$\x1ce\xce@.A\x18rB\xf9\x03\x99\xe8Y a~m\x80y\xc3\x00\x8d\xb7\x11Y])Q8t\x1cN\xb8L\xd7\xf4\x99\xcc\xdc\x9et2\xbb\xf3"\x95\xa1I\t\xa7\xb5\x9f\r\x9fo=C\x9dS\xb1\xc8d\xe5)\xe6_\xb7\xf1_\xf3\x1dAF\xcb\x1f\x00(\xd3\xc1\x00\x00\x00\x00IEND\xaeB`\x82'
    ,
    'asterisk_yellow': '\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x10\x00\x00\x00\x10\x08\x06\x00\x00\x00\x1f\xf3\xffa\x00\x00\x00\x04gAMA\x00\x00\xaf\xc87\x05\x8a\xe9\x00\x00\x00\x19tEXtSoftware\x00Adobe ImageReadyq\xc9e<\x00\x00\x02yIDAT8\xcb\xa5\x93\xcdKTa\x14\xc6\x9f\x7fa\x16-j9\xb4i\xd1j\xa0\x85D\x10\x0c\xd1\xc6E\xc1T\x90\xa5Q\xcd@\x05\x951\x0c\x1aI&V\xb6)\x8b\x88\xa9\xec;\x99D\x8c\xac\xec\xe3-sD\xad\xe8"\xd7\xcc\x8fQg\x9c\x99\x1aR\xd3k\x8e\x8e9\x1fw\x9e\x8e\x90\x8a5\xaeZ\x9c\xc5\xfb\xde\xfb<\xe7\x9c\xdf9/H\xe2\x7fb\xd9!\xdb\n\x9b\xe9\x87\xca\xbc\x03\xd3\xcdp,\xdc\xcf\xbe\x843\xd1\x04N?\x83\x9aj\x845\xa7\x81\x88\x9d\xe6G+\xb3C.f\xc3%L*\xa8\x85o3M\xd0\xcc`)\x93\x9d\xdb8\xf9\x18\xc6D\xfd\x92\xf9\xa2\x81\xd9\x02{F[\xcfl\xec\x1c9Z\xcd\xb9\x96U\x9c}\x01\xeb\xccs\xd8\x13\xfeud\xe443\x81b\x8a\xd8\xf8Q\x07[\xce\x16Ro\xe1I\xebvr\xa4\x9a\xa9\xee\x9d\x14\xb17\xfe\x14\xde\xa4\xbe\x83\x0c\x97q\xa65\x8fc\x8f\xe0\\\x91\xc1|\xfcz\x05\x95\xd2\xf3\xa5\x92*\xc6\x1ba$\xf5]\x92\xbd\x9c\x89\xf7[\xe6\xc5\xde\x7f \n,[\xf2\xcdRI\x02\xcb"\xb0\x8cl\xb4\x82\xd9\xd012x\x9c\xe9\x1e\'\xc7|\xd0FjaY\xf8/r\x0b\xb6\xe1\x1b\xb0A\xc4*\xd9f\xa5\x90\xa6\x88\x8d?\xa4\xb5L\xc0E\x0e\x1e \x03ELw\x17\xf2\xfbCh\xb1\xfbP_\xef \x18\xa9\x01c\xbe5\x1c\xba\x06\x85\xb9\xd7P\xe6p)9\xfe\x80f\xb8\x9c\xe9A7\xd3\x03\xc5\xd2s\t9\xb0\x8f\xec/\x10\xa3\xc3L\xf5\x1c\xe5\x9c~\x90\xe9>7\x19\xaad\xe2S!{/\x89\x81\x90V\x02\x8b\x02\x8b?\x9f@\x9bl\x80\x12\xd2*\xf5y\x8fd\x17\x83\xbe\xddL\xe9\x05\x8c\xde\x86\x16\xae\x81\n]Gp\xf0*\xd8{\x11\xec\xaa\x12\x83\xbf\xa1\x8c\xd7\xc3"\xb0\x0c3t\x8a\x99\x9e\xfdR\x85\x8bI}/\xc37\xa1\x85\xbcK\x0cV\x9c\x82\x88\xd5t\xfbV\xa6\xfa\x8b\xf9\xed.\x82\xd3\x1d\xdb\xa5\x85\x13\x9cP\x9b\x19\xb8\x92c\n\xcb\xc4>\x9c\x9f\xf2o"\xa3\x954T\x1e\x85\xb4SH{\xa7Z\xf3\x85\xc5\x11\xc6\x1a6\xb0\xf3,<9\rF}pL*\x9b\xac\xf1\x19f\x06<\x14\xd2\x86\x88-B\xda\x1e\xad]+,\x0eI+.~\xb9\xbc\x9a\xed\'sl\xa2\x8c\xc9\x11\xbb\x07#\xde!\xfb\xdel\xa7\xc0Z\xcc\xd4u\x01Z\xbc\xa3\x88\xd1\xba\x8dl+\x85\xe1w\xe7x\x0b\xf3!\xa4\xadB\xbaN\xc4JH/\xbe:\xad\x02\x8e\x0fePm%\xf0\xb4\xb8\x97\x83\xfc\rL\xdb\xc0:\x1b%\xf2\x81\x00\x00\x00\x00IEND\xaeB`\x82'
    ,
    'disk': '\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x10\x00\x00\x00\x10\x08\x06\x00\x00\x00\x1f\xf3\xffa\x00\x00\x00\x04gAMA\x00\x00\xaf\xc87\x05\x8a\xe9\x00\x00\x00\x19tEXtSoftware\x00Adobe ImageReadyq\xc9e<\x00\x00\x01\xfeIDAT\x18\x19\x05\xc1=\x8b]U\x18\x06\xd0\xb5\xcf\xec;C\x82\x92\xa8`\x84DD\x03\nV\x01e \xf1\xa3\x15\x7f\x82\x85h\x91*B\xd0"\xa56VV"\xa2\x08c\xa1\xd8\nv\x82ba\x95"\x16\x16\xc1N\xc5B\xb4\x12\xc5\x0c\xde\x99{\xf6~\x1f\xd7j\x87o|\xf7\x16\x1e\xc3\xf3x\x02\xf7\x91\x8e&\xc0\xde\xd2,K\x93\x94*\xff\xeco\xfc\xbc=]\xdf\xbb\xf3\xf1\xcb_v<}t\xeb\xdau\x9a\xa7.\x1e\x08R\xb1\x1b\xb1[\xcb\xde\xd2\x9c9X\xb4\xc6\xf1\xb6\x1c\x9f\xccs\xbf\xfey|\xe5\xf3o~\xf9\xe4\xf0\xc6\xd7\xe7\x16\xbc |u\xe7_\x15\x92\xb8\xf9\xe1\x0f\xaaBk6\xbdY\x96f7b\xbb\x96Q\xda\xb4\xf4\xd7^\xba\xfc\xd0\x99\x83\xfd\x8f\x16<\x12T\xc5:\xca:\x02\xd6\x8a\xbe\xc7\xa67U\xb1\xdd\x95u\x84\xc4\xf7w\xef\xd9\xdf\xec\xd9\x9e\x8e\xfd\x8e\xb3\xa3\x82\xd8\xee\n,\xad\x116}\xd14\'k\xd9\x9eF%*T\xe2\x8f\xbfNHZ\'}&\x12NG\xc0\xdb\xaf_\xb1\xe9\x8b\xbe\xb0\xce\xf8\xef\xb4\x8c*UD\xa4\xca:\xa6\xa4t\xb4\x9aH\xbc\xfb\xd9\x8fZk\x96\xc6\xa6/\x1aF\xc5\x18%\x008\x7f\xfeA\xeb\xd8#\xd1\x85J\xa9\x9a\x1e\xbep\x91F\x13\x02Q\xa1\xaa$Q\x89\xaa\xa25\xeb:H\xe90\'\t\xd0\x12\xa0QE\x12D\x82DK$e]\x9b\xa4t\x18\xb3\x10\x10\xd14\x12I\xa4JD\x12US*\xa2\x9c\xae!\xa5\x13\xb3Bx\xe7\x95K\x00\x00\x00\x00\xe0\xd6\xd1O\xc6\x88\xa4\xf4\xa55\xb3\x88H\xf8\xe0\xf6u\x00\x00\x00p\xf3\xea\x919\x87\xdd\x08\x89\xaeQ\x15\rp\xed\xd2\xab\x00\x00\x00\x00j\x96\xb9\x06\xa5\'\xc9\xac4\x02n\xff\xfe\x05\x00\x00\x00x\xf6\xd1\x17\xcd9\xad3\x92\xa4W\xfc\xb6\x1b\xf5\xf83\x97\xcfj\x8d7\x9f\xfb\x14\x00\x00\x00\xc0\x85\xfb\xcb\x9c\x81\xbf\xdb\xe1\x8do\xdfO\xf2$\xb9*y\x80\x92\x84\x94\xa4HI\x8a\x14\x89$H\xc8=m\xb9\xfb?!|n\x8bm\x10\xb0\xa2\x00\x00\x00\x00IEND\xaeB`\x82'
    ,
    'delete': '\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x10\x00\x00\x00\x10\x08\x06\x00\x00\x00\x1f\xf3\xffa\x00\x00\x00\x04gAMA\x00\x00\xaf\xc87\x05\x8a\xe9\x00\x00\x00\x19tEXtSoftware\x00Adobe ImageReadyq\xc9e<\x00\x00\x02]IDAT8\xcb\xa5\x93\xfbKSa\x18\xc7\xfd[\xb6\x1f\xa2\x04\x89n\x84\x84QP\x98\xf32w\xd6\xda\xdc\xa6\xce\xb3L\x8f[,bi\x8e\x9da\x9aA\x8d\xc5\\\xf8C\xa8\xa5v\xd5\xca_2Ml\x94ZFj\xd7\xa1\xe5\xb1\xf2\xd2NMjm\x9e\xb3k\xca\xb7\xb9`&.#z\xe1\xfb\xcb\xcb\xfb\xf9\xbc<\x0f\xcf\x93\x02 \xe5\x7f\xb2\xe6bV\xaf\x17\xceP\x15\xe6\xf7T\x193\xa5%\xb9I\xad\x86{G\xaa\x99qRiv\x95\xc8\x85\xeb\n\xe6tz\xe2#E\xb1\xdf\x1c6\x84\x07\x9d\x88\xbc\x19Edd\x08\xfc\xdd\x0e\xcc\x1aJ\xf1\xaa\x90`\x9f\xab\xc5DR\xc12<]N\xf1\x0b\xb7;\xb04\xf5\x16\xd1\xbe;\x88\xb6\xdb\x11m>\x87\x1f7\x9b\xb08\xdc\x07\x8f\xc9\x80Qe6\xffL\x9eI\xac\x12\xcc\xe8t\x82\x18\xec\xe6\xae\xb7c\x89q!z\xf1\x0c|v\x0b\xfc\xb6j\x84/X\x10i\xa0\x11\xb6\x9e@\xf8\xde\r\xcc\x1d%1|h\x9f\xfb\xb1l\x8f !\x88\xc1\xf4|\xad\x19\x8b\xae\xb1\xf8\x8f!\x07\r\xefY#\x82u\xbaU\xe1N\x92\x08w]\xc1\xcb\xbc\x0c\x0cH3\xe8\x84\xe0\x03u\x84\tt]E\xb4\xb3\x19>k%\xbe\x16I\x93f\xa1\x92\x04o\xab\x81\xc7R\x85\x87D:\x93\x100\xe5\xda`\xe4~\x17\xa2\x0e\x0b|\xa7\r\xf8\xd3\xf1(r\xe0\xa5\n\xe1on\x843oG0!\x98$\x8b\x82\xa1\xceV\x84\xeb\r\x08\x9e*[W0_\xaa\x82\xbf\xa9\x11\xfd\xe2-+\x82\x89\x12\x15\xe3\xb5\xd6 d\xa7\xc1\x1dW\xc7\x1f&\x8d2\x0f\xbeZ\x13fMF\xf4\x89\xd2VJp\x15\xcbiF&B\xb0\xb3\r>\xad\x0c\xdeR\xc9\x1a\x98\x95g\x83-\x90 \xd0~\tC\xe2m\xe8\xcd\xda\xb4\xd2\xc4\xd7ER\xc1\x0b\r\xe1\x9e\xab\xd0 p\xab5\xde\xb0y\x95\xf8\x17\xa8\xc8\x05+\x8b\xc121\xf8\xb6\x16\x8c\x17K\x97aw\xb7h\xa3`\xd5 \x8d\x15\xe4\x10#\x8a\x03\xfc\xf4a\x15\x02\xd7Z\xf1\xbd\x9e\x86\x87T\xe2\xb3Z\x01o\x9d\x19\xfc\xe5\x16L\xa8\xf3\xd1\x93\x95\xca\xc7`"\xe9(?\x95\xef\'\x9e\x1c\xdc\xcb\x8eJv\xe1K\xb5\x11\xde\x86\xf3\xf1|\xaa:\x86G9[\x97a\xf6w8\xe92\rJw\x0b\x07\xc4\xe9f\'\xb1\x93y\x90\xbf\x9d\xeb\x17m\xe6zs\xd3\x98\x9e\xecTsw\xe6\x06\xe1_\xb7\xf1_\xf3\x13\x1d\xd2\xce\xb9Ir\x1b\xfe\x00\x00\x00\x00IEND\xaeB`\x82'
}

ICONS_ICO = [
    '\x00\x00\x01\x00\x01\x00\x10\x10\x00\x00\x01\x00 \x00h\x04\x00\x00\x16\x00\x00\x00(\x00\x00\x00\x10\x00\x00\x00 \x00\x00\x00\x01\x00 \x00\x00\x00\x00\x00@\x04\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x1a\x00\x00\x00\x1a\x00\x00\x00\x1a\x00\x00\x00\x1a\x00\x00\x00\x1a\x00\x00\x00\x1a\x00\x00\x00\x1a\x00\x00\x00\x1a\x00\x00\x00\x1a\x00\x00\x00\x1a\x00\x00\x00\x1a\x00\x00\x00\x1a\x00\x00\x00\x1a\x00\x00\x00\x1a\x00\x00\x00\x00\x03\x03\xa1\xff\x03\x03\xa1\xff\x03\x03\xa1\xff\x03\x03\xa1\xff\x03\x03\xa1\xff\x03\x03\xa1\xff\x03\x03\xa1\xff\x03\x03\xa1\xff\x03\x03\xa1\xff\x03\x03\xa1\xff\x03\x03\xa1\xff\x03\x03\xa1\xff\x03\x03\xa1\xff\x03\x03\xa1\xff\x00\x00\x00\x1a\x00Fe\xff\x03\x03\xa6\xff\x03\x03\xa6\xff\x03\x03\xa4\xff\x03\x03\x9f\xff\x03\x03\x9e\xff\x03\x03\xa3\xff\x03\x03\xa6\xff\x03\x03\xa6\xff\x03\x03\xa3\xff\x03\x03\x9e\xff\x03\x03\x9e\xff\x03\x03\xa3\xff\x03\x03\xa6\xff\x03\x03\xa6\xff\x00\x00\x00\x1a\x00Hh\xff\x02\x02\xad\xff\x02\x02\xad\xff\x02\x02\xa7\xff\xcb\xcb\xea\xff\xff\xff\xff\xff\x16\x16\xab\xff\x02\x02\xac\xff\x02\x02\xad\xff\x02\x02\xa6\xff\xf7\xf7\xfc\xff\xf7\xf7\xfc\xff\x02\x02\xa6\xff\x02\x02\xad\xff\x02\x02\xad\xff\x00\x00\x00\x1a\x00Kl\xff\x02\x02\xb4\xff\x02\x02\xb4\xff\x02\x02\xac\xff\xc4\xc4\xe8\xff\xff\xff\xff\xff\x13\x13\xaf\xff\x02\x02\xb3\xff\x02\x02\xb4\xff\x02\x02\xab\xff\xf0\xf0\xf9\xff\xf0\xf0\xf9\xff\x02\x02\xab\xff\x02\x02\xb4\xff\x02\x02\xb4\xff\x00\x00\x00\x1a\x00Np\xff\x02\x02\xbc\xff\x02\x02\xbc\xff\x02\x02\xb5\xff\xc4\xc4\xeb\xff\xff\xff\xff\xff\n\n\xb1\xff\x02\x02\xb6\xff\x02\x02\xb6\xff\x01\x01\xaf\xff\xed\xed\xf8\xff\xf0\xf0\xfa\xff\x02\x02\xb3\xff\x02\x02\xbc\xff\x02\x02\xbc\xff\x00\x00\x00\x1a\x00Qt\xff\x02\x02\xc4\xff\x02\x02\xc4\xff\x02\x02\xbd\xff\xc4\xc4\xed\xff\xff\xff\xff\xff\x91\x91\xdd\xff\x9c\x9c\xe1\xff\x9c\x9c\xe1\xff\x94\x94\xde\xff\xf7\xf7\xfc\xff\xee\xee\xfa\xff\x02\x02\xbc\xff\x02\x02\xc4\xff\x02\x02\xc4\xff\x00\x00\x00\x1a\x00Uy\xff\x01\x01\xce\xff\x01\x01\xce\xff\x01\x01\xc8\xff\xc4\xc4\xf0\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xed\xed\xfa\xff\x01\x01\xc7\xff\x01\x01\xce\xff\x01\x01\xce\xff\x00\x00\x00\x1a\x00X}\xff\x01\x01\xd6\xff\x01\x01\xd6\xff\x01\x01\xd1\xff\xc4\xc4\xf2\xff\xff\xff\xff\xff\x03\x03\xcb\xff\x01\x01\xcf\xff\x01\x01\xd0\xff\x01\x01\xcb\xff\xeb\xeb\xfa\xff\xef\xef\xfb\xff\x01\x01\xd0\xff\x01\x01\xd6\xff\x01\x01\xd6\xff\x00\x00\x00\x1a\x00[\x82\xff\x01\x01\xde\xff\x01\x01\xde\xff\x01\x01\xda\xff\xc4\xc4\xf4\xff\xff\xff\xff\xff\x13\x13\xdb\xff\x01\x01\xde\xff\x01\x01\xde\xff\x01\x01\xd9\xff\xf0\xf0\xfc\xff\xf0\xf0\xfc\xff\x01\x01\xd9\xff\x01\x01\xde\xff\x01\x01\xde\xff\x00\x00\x00\x1a\x00_\x86\xff\x01\x01\xe5\xff\x01\x01\xe5\xff\x01\x01\xe2\xff\xc4\xc4\xf7\xff\xff\xff\xff\xff\x13\x13\xe2\xff\x01\x01\xe5\xff\x01\x01\xe5\xff\x01\x01\xe1\xff\xf0\xf0\xfd\xff\xf0\xf0\xfd\xff\x01\x01\xe1\xff\x01\x01\xe5\xff\x01\x01\xe5\xff\x00\x00\x00\x1a\x00a\x8a\xff\x00\x00\xec\xff\x00\x00\xec\xff\x00\x00\xea\xff\xd4\xd4\xfb\xff\xff\xff\xff\xff\x16\x16\xeb\xff\x00\x00\xec\xff\x00\x00\xec\xff\x00\x00\xea\xff\xff\xff\xff\xff\xff\xff\xff\xff\x00\x00\xea\xff\x00\x00\xec\xff\x00\x00\xec\xff\x00\x00\x00\x1a\x00d\x8e\xff\x00\x00\xf1\xff\x00\x00\xf1\xff\x00\x00\xf0\xff\x00\x00\xef\xff\x00\x00\xef\xff\x00\x00\xf0\xff\x00\x00\xf1\xff\x00\x00\xf1\xff\x00\x00\xf0\xff\x00\x00\xef\xff\x00\x00\xef\xff\x00\x00\xf0\xff\x00\x00\xf1\xff\x00\x00\xf1\xff\x00\x00\x00\x1a\x00f\x91\xff\x00\x00\xf5\xff\x00\x00\xf5\xff\x00\x00\xf5\xff\x00\x00\xf5\xff\x00\x00\xf5\xff\x00\x00\xf5\xff\x00\x00\xf5\xff\x00\x00\xf5\xff\x00\x00\xf5\xff\x00\x00\xf5\xff\x00\x00\xf5\xff\x00\x00\xf5\xff\x00\x00\xf5\xff\x00\x00\xf5\xff\x00\x00\x00\x00\x00h\x93\xff\x00h\x93\xff\x00h\x93\xff\x00h\x93\xff\x00h\x93\xff\x00h\x93\xff\x00h\x93\xff\x00h\x93\xff\x00h\x93\xff\x00h\x93\xff\x00h\x93\xff\x00h\x93\xff\x00h\x93\xff\x00h\x93\xff\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xc0\x00\x00\x00\x80\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x01\x00\x00\x00\x03\x00\x00\xff\xff\x00\x00'
    ,
    '\x00\x00\x01\x00\x01\x00\x10\x10\x00\x00\x01\x00 \x00h\x04\x00\x00\x16\x00\x00\x00(\x00\x00\x00\x10\x00\x00\x00 \x00\x00\x00\x01\x00 \x00\x00\x00\x00\x00@\x04\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x1a\x00\x00\x00\x1a\x00\x00\x00\x1a\x00\x00\x00\x1a\x00\x00\x00\x1a\x00\x00\x00\x1a\x00\x00\x00\x1a\x00\x00\x00\x1a\x00\x00\x00\x1a\x00\x00\x00\x1a\x00\x00\x00\x1a\x00\x00\x00\x1a\x00\x00\x00\x1a\x00\x00\x00\x1a\x00\x00\x00\x00\x00H\xa4\xff\x00H\xa4\xff\x00H\xa4\xff\x00H\xa4\xff\x00H\xa4\xff\x00H\xa4\xff\x00H\xa4\xff\x00H\xa4\xff\x00H\xa4\xff\x00H\xa4\xff\x00H\xa4\xff\x00H\xa4\xff\x00H\xa4\xff\x00H\xa4\xff\x00\x00\x00\x1a\x00Fe\xff\x00N\xa9\xff\x00N\xa9\xff\x00L\xa7\xff\x00G\xa2\xff\x00G\xa1\xff\x00K\xa6\xff\x00N\xa9\xff\x00N\xa9\xff\x00L\xa7\xff\x00G\xa1\xff\x00G\xa1\xff\x00L\xa7\xff\x00N\xa9\xff\x00N\xa9\xff\x00\x00\x00\x1a\x00Hh\xff\x00U\xaf\xff\x00U\xaf\xff\x00O\xa9\xff\xcb\xd8\xeb\xff\xff\xff\xff\xff\x14[\xad\xff\x00T\xae\xff\x00U\xaf\xff\x00M\xa8\xff\xf7\xf9\xfc\xff\xf7\xf9\xfc\xff\x00M\xa8\xff\x00U\xaf\xff\x00U\xaf\xff\x00\x00\x00\x1a\x00Kl\xff\x00^\xb6\xff\x00^\xb6\xff\x00U\xae\xff\xc4\xd4\xe9\xff\xff\xff\xff\xff\x12]\xb1\xff\x00]\xb5\xff\x00^\xb6\xff\x00S\xad\xff\xf0\xf4\xf9\xff\xf0\xf4\xf9\xff\x00S\xad\xff\x00^\xb6\xff\x00^\xb6\xff\x00\x00\x00\x1a\x00Np\xff\x00g\xbe\xff\x00g\xbe\xff\x00^\xb7\xff\xc4\xd6\xeb\xff\xff\xff\xff\xff\t[\xb3\xff\x00_\xb8\xff\x00`\xb9\xff\x00W\xb1\xff\xed\xf2\xf9\xff\xf0\xf4\xfa\xff\x00\\\xb6\xff\x00g\xbe\xff\x00g\xbe\xff\x00\x00\x00\x1a\x00Qt\xff\x00p\xc7\xff\x00p\xc7\xff\x00g\xc0\xff\xc4\xd8\xed\xff\xff\xff\xff\xff\x91\xb4\xde\xff\x9c\xbd\xe3\xff\x9c\xbd\xe3\xff\x94\xb6\xdf\xff\xf7\xf9\xfc\xff\xee\xf3\xfa\xff\x00e\xbe\xff\x00p\xc7\xff\x00p\xc7\xff\x00\x00\x00\x1a\x00Uy\xff\x00y\xcf\xff\x00y\xcf\xff\x00p\xc9\xff\xc4\xda\xf0\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xed\xf3\xfa\xff\x00n\xc8\xff\x00y\xcf\xff\x00y\xcf\xff\x00\x00\x00\x1a\x00X}\xff\x00\x83\xd7\xff\x00\x83\xd7\xff\x00z\xd2\xff\xc4\xdc\xf2\xff\xff\xff\xff\xff\x02o\xcc\xff\x00w\xd0\xff\x00w\xd1\xff\x00o\xcc\xff\xeb\xf2\xfa\xff\xef\xf5\xfb\xff\x00x\xd1\xff\x00\x83\xd7\xff\x00\x83\xd7\xff\x00\x00\x00\x1a\x00[\x82\xff\x00\x8c\xdf\xff\x00\x8c\xdf\xff\x00\x83\xdb\xff\xc4\xde\xf5\xff\xff\xff\xff\xff\x12\x88\xdc\xff\x00\x8b\xdf\xff\x00\x8c\xdf\xff\x00\x81\xda\xff\xf0\xf6\xfc\xff\xf0\xf6\xfc\xff\x00\x81\xda\xff\x00\x8c\xdf\xff\x00\x8c\xdf\xff\x00\x00\x00\x1a\x00_\x86\xff\x00\x94\xe6\xff\x00\x94\xe6\xff\x00\x8b\xe3\xff\xc4\xe0\xf7\xff\xff\xff\xff\xff\x12\x8f\xe3\xff\x00\x93\xe6\xff\x00\x94\xe6\xff\x00\x89\xe2\xff\xf0\xf7\xfd\xff\xf0\xf7\xfd\xff\x00\x89\xe2\xff\x00\x94\xe6\xff\x00\x94\xe6\xff\x00\x00\x00\x1a\x00a\x8a\xff\x00\x9b\xec\xff\x00\x9b\xec\xff\x00\x94\xea\xff\xd4\xeb\xfb\xff\xff\xff\xff\xff\x16\x9b\xeb\xff\x00\x9a\xec\xff\x00\x9b\xec\xff\x00\x93\xea\xff\xff\xff\xff\xff\xff\xff\xff\xff\x00\x93\xea\xff\x00\x9b\xec\xff\x00\x9b\xec\xff\x00\x00\x00\x1a\x00d\x8e\xff\x00\xa2\xf1\xff\x00\xa2\xf1\xff\x00\xa0\xf0\xff\x00\x9b\xef\xff\x00\x9a\xef\xff\x00\x9f\xf0\xff\x00\xa2\xf1\xff\x00\xa2\xf1\xff\x00\x9f\xf0\xff\x00\x9a\xef\xff\x00\x9a\xef\xff\x00\x9f\xf0\xff\x00\xa2\xf1\xff\x00\xa2\xf1\xff\x00\x00\x00\x1a\x00f\x91\xff\x00\xa6\xf5\xff\x00\xa6\xf5\xff\x00\xa6\xf5\xff\x00\xa6\xf5\xff\x00\xa6\xf5\xff\x00\xa6\xf5\xff\x00\xa6\xf5\xff\x00\xa6\xf5\xff\x00\xa6\xf5\xff\x00\xa6\xf5\xff\x00\xa6\xf5\xff\x00\xa6\xf5\xff\x00\xa6\xf5\xff\x00\xa6\xf5\xff\x00\x00\x00\x00\x00h\x93\xff\x00h\x93\xff\x00h\x93\xff\x00h\x93\xff\x00h\x93\xff\x00h\x93\xff\x00h\x93\xff\x00h\x93\xff\x00h\x93\xff\x00h\x93\xff\x00h\x93\xff\x00h\x93\xff\x00h\x93\xff\x00h\x93\xff\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xc0\x00\x00\x00\x80\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x01\x00\x00\x00\x03\x00\x00\xff\xff\x00\x00'
    ,
    '\x00\x00\x01\x00\x01\x00\x10\x10\x00\x00\x01\x00 \x00h\x04\x00\x00\x16\x00\x00\x00(\x00\x00\x00\x10\x00\x00\x00 \x00\x00\x00\x01\x00 \x00\x00\x00\x00\x00@\x04\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x1a\x00\x00\x00\x1a\x00\x00\x00\x1a\x00\x00\x00\x1a\x00\x00\x00\x1a\x00\x00\x00\x1a\x00\x00\x00\x1a\x00\x00\x00\x1a\x00\x00\x00\x1a\x00\x00\x00\x1a\x00\x00\x00\x1a\x00\x00\x00\x1a\x00\x00\x00\x1a\x00\x00\x00\x1a\x00\x00\x00\x00\x00\x94\xbe\xff\x00\x94\xbe\xff\x00\x94\xbe\xff\x00\x94\xbe\xff\x00\x94\xbe\xff\x00\x94\xbe\xff\x00\x94\xbe\xff\x00\x94\xbe\xff\x00\x94\xbe\xff\x00\x94\xbe\xff\x00\x94\xbe\xff\x00\x94\xbe\xff\x00\x94\xbe\xff\x00\x94\xbe\xff\x00\x00\x00\x1a\x00Fe\xff\x00\x99\xc1\xff\x00\x99\xc1\xff\x00\x97\xbf\xff\x00\x92\xbb\xff\x00\x91\xbb\xff\x00\x96\xbe\xff\x00\x99\xc1\xff\x00\x99\xc1\xff\x00\x96\xbf\xff\x00\x91\xbb\xff\x00\x91\xbb\xff\x00\x96\xbf\xff\x00\x99\xc1\xff\x00\x99\xc1\xff\x00\x00\x00\x1a\x00Hh\xff\x00\x9e\xc5\xff\x00\x9e\xc5\xff\x00\x97\xc0\xff\xcb\xe7\xf0\xff\xff\xff\xff\xff\x14\x9d\xc3\xff\x00\x9d\xc4\xff\x00\x9e\xc5\xff\x00\x96\xbf\xff\xf7\xfb\xfd\xff\xf7\xfb\xfd\xff\x00\x96\xbf\xff\x00\x9e\xc5\xff\x00\x9e\xc5\xff\x00\x00\x00\x1a\x00Kl\xff\x00\xa4\xcb\xff\x00\xa4\xcb\xff\x00\x9c\xc4\xff\xc4\xe4\xef\xff\xff\xff\xff\xff\x12\x9f\xc5\xff\x00\xa3\xcb\xff\x00\xa4\xcb\xff\x00\x9a\xc3\xff\xf0\xf8\xfb\xff\xf0\xf8\xfb\xff\x00\x9a\xc3\xff\x00\xa4\xcb\xff\x00\xa4\xcb\xff\x00\x00\x00\x1a\x00Np\xff\x00\xab\xd0\xff\x00\xab\xd0\xff\x00\xa3\xca\xff\xc4\xe6\xf0\xff\xff\xff\xff\xff\t\x9e\xc7\xff\x00\xa4\xcb\xff\x00\xa5\xcc\xff\x00\x9c\xc5\xff\xed\xf7\xfa\xff\xf0\xf8\xfb\xff\x00\xa1\xc9\xff\x00\xab\xd0\xff\x00\xab\xd0\xff\x00\x00\x00\x1a\x00Qt\xff\x00\xb2\xd6\xff\x00\xb2\xd6\xff\x00\xaa\xd1\xff\xc4\xe8\xf2\xff\xff\xff\xff\xff\x91\xd3\xe6\xff\x9c\xd9\xea\xff\x9c\xd9\xea\xff\x94\xd5\xe7\xff\xf7\xfc\xfd\xff\xee\xf8\xfb\xff\x00\xa9\xd0\xff\x00\xb2\xd6\xff\x00\xb2\xd6\xff\x00\x00\x00\x1a\x00Uy\xff\x00\xb9\xdb\xff\x00\xb9\xdb\xff\x00\xb2\xd7\xff\xc4\xea\xf3\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xed\xf8\xfb\xff\x00\xb0\xd6\xff\x00\xb9\xdb\xff\x00\xb9\xdb\xff\x00\x00\x00\x1a\x00X}\xff\x00\xc0\xe1\xff\x00\xc0\xe1\xff\x00\xb9\xdd\xff\xc4\xec\xf5\xff\xff\xff\xff\xff\x02\xb1\xd8\xff\x00\xb7\xdc\xff\x00\xb7\xdc\xff\x00\xb1\xd9\xff\xeb\xf8\xfb\xff\xef\xfa\xfc\xff\x00\xb8\xdc\xff\x00\xc0\xe1\xff\x00\xc0\xe1\xff\x00\x00\x00\x1a\x00[\x82\xff\x00\xc8\xe6\xff\x00\xc8\xe6\xff\x00\xc1\xe3\xff\xc4\xee\xf7\xff\xff\xff\xff\xff\x12\xc3\xe3\xff\x00\xc7\xe6\xff\x00\xc8\xe6\xff\x00\xbf\xe2\xff\xf0\xfa\xfd\xff\xf0\xfa\xfd\xff\x00\xbf\xe2\xff\x00\xc8\xe6\xff\x00\xc8\xe6\xff\x00\x00\x00\x1a\x00_\x86\xff\x00\xce\xeb\xff\x00\xce\xeb\xff\x00\xc8\xe8\xff\xc4\xf0\xf8\xff\xff\xff\xff\xff\x12\xc9\xe9\xff\x00\xcd\xeb\xff\x00\xce\xeb\xff\x00\xc7\xe8\xff\xf0\xfb\xfd\xff\xf0\xfb\xfd\xff\x00\xc7\xe8\xff\x00\xce\xeb\xff\x00\xce\xeb\xff\x00\x00\x00\x1a\x00a\x8a\xff\x00\xd3\xef\xff\x00\xd3\xef\xff\x00\xcf\xed\xff\xd4\xf5\xfb\xff\xff\xff\xff\xff\x16\xd2\xef\xff\x00\xd3\xef\xff\x00\xd3\xef\xff\x00\xce\xed\xff\xff\xff\xff\xff\xff\xff\xff\xff\x00\xce\xed\xff\x00\xd3\xef\xff\x00\xd3\xef\xff\x00\x00\x00\x1a\x00d\x8e\xff\x00\xd8\xf2\xff\x00\xd8\xf2\xff\x00\xd7\xf2\xff\x00\xd4\xf1\xff\x00\xd3\xf0\xff\x00\xd6\xf1\xff\x00\xd8\xf2\xff\x00\xd8\xf2\xff\x00\xd6\xf1\xff\x00\xd3\xf0\xff\x00\xd3\xf0\xff\x00\xd6\xf1\xff\x00\xd8\xf2\xff\x00\xd8\xf2\xff\x00\x00\x00\x1a\x00f\x91\xff\x00\xdb\xf5\xff\x00\xdb\xf5\xff\x00\xdb\xf5\xff\x00\xdb\xf5\xff\x00\xdb\xf5\xff\x00\xdb\xf5\xff\x00\xdb\xf5\xff\x00\xdb\xf5\xff\x00\xdb\xf5\xff\x00\xdb\xf5\xff\x00\xdb\xf5\xff\x00\xdb\xf5\xff\x00\xdb\xf5\xff\x00\xdb\xf5\xff\x00\x00\x00\x00\x00h\x93\xff\x00h\x93\xff\x00h\x93\xff\x00h\x93\xff\x00h\x93\xff\x00h\x93\xff\x00h\x93\xff\x00h\x93\xff\x00h\x93\xff\x00h\x93\xff\x00h\x93\xff\x00h\x93\xff\x00h\x93\xff\x00h\x93\xff\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xc0\x00\x00\x00\x80\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x01\x00\x00\x00\x03\x00\x00\xff\xff\x00\x00'
    ,
    '\x00\x00\x01\x00\x01\x00\x10\x10\x00\x00\x01\x00 \x00h\x04\x00\x00\x16\x00\x00\x00(\x00\x00\x00\x10\x00\x00\x00 \x00\x00\x00\x01\x00 \x00\x00\x00\x00\x00@\x04\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x1a\x00\x00\x00\x1a\x00\x00\x00\x1a\x00\x00\x00\x1a\x00\x00\x00\x1a\x00\x00\x00\x1a\x00\x00\x00\x1a\x00\x00\x00\x1a\x00\x00\x00\x1a\x00\x00\x00\x1a\x00\x00\x00\x1a\x00\x00\x00\x1a\x00\x00\x00\x1a\x00\x00\x00\x1a\x00\x00\x00\x009\xa0\x05\xff9\xa0\x05\xff9\xa0\x05\xff9\xa0\x05\xff9\xa0\x05\xff9\xa0\x05\xff9\xa0\x05\xff9\xa0\x05\xff9\xa0\x05\xff9\xa0\x05\xff9\xa0\x05\xff9\xa0\x05\xff9\xa0\x05\xff9\xa0\x05\xff\x00\x00\x00\x1a\x00Fe\xff9\xa3\x07\xff9\xa3\x07\xff7\xa1\x07\xff4\x9c\x06\xff3\x9b\x06\xff7\xa0\x07\xff9\xa3\x07\xff9\xa3\x07\xff7\xa0\x07\xff3\x9b\x06\xff3\x9b\x06\xff7\xa0\x07\xff9\xa3\x07\xff9\xa3\x07\xff\x00\x00\x00\x1a\x00Hh\xff9\xa8\n\xff9\xa8\n\xff4\xa2\t\xff\xd4\xe9\xcc\xff\xff\xff\xff\xffC\xa7\x1b\xff8\xa7\n\xff9\xa8\n\xff3\xa0\t\xff\xf8\xfc\xf7\xff\xf8\xfc\xf7\xff3\xa0\t\xff9\xa8\n\xff9\xa8\n\xff\x00\x00\x00\x1a\x00Kl\xff9\xac\r\xff9\xac\r\xff2\xa4\x0b\xff\xcd\xe6\xc7\xff\xff\xff\xff\xff>\xa7\x1a\xff8\xab\r\xff9\xac\r\xff1\xa2\x0b\xff\xf2\xf8\xf0\xff\xf2\xf8\xf0\xff1\xa2\x0b\xff9\xac\r\xff9\xac\r\xff\x00\x00\x00\x1a\x00Np\xff9\xb2\x11\xff9\xb2\x11\xff2\xaa\x0f\xff\xcd\xe8\xc7\xff\xff\xff\xff\xff3\xa6\x14\xff4\xac\x0f\xff4\xac\x0f\xff-\xa4\r\xff\xef\xf8\xee\xff\xf2\xf9\xf1\xff1\xa9\x0e\xff9\xb2\x11\xff9\xb2\x11\xff\x00\x00\x00\x1a\x00Qt\xff9\xb7\x14\xff9\xb7\x14\xff2\xb0\x12\xff\xcd\xe9\xc8\xff\xff\xff\xff\xff\xa0\xd6\x96\xff\xab\xdc\xa1\xff\xab\xdc\xa1\xff\xa3\xd7\x99\xff\xf8\xfc\xf7\xff\xf0\xf8\xef\xff1\xae\x12\xff9\xb7\x14\xff9\xb7\x14\xff\x00\x00\x00\x1a\x00Uy\xff9\xbd\x18\xff9\xbd\x18\xff2\xb6\x15\xff\xcd\xeb\xc8\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xef\xf9\xee\xff1\xb5\x14\xff9\xbd\x18\xff9\xbd\x18\xff\x00\x00\x00\x1a\x00X}\xff9\xc2\x1b\xff9\xc2\x1b\xff2\xbb\x17\xff\xcd\xec\xc9\xff\xff\xff\xff\xff,\xb4\x15\xff0\xb9\x16\xff1\xb9\x16\xff+\xb3\x13\xff\xee\xf8\xec\xff\xf1\xfa\xf0\xff1\xba\x17\xff9\xc2\x1b\xff9\xc2\x1b\xff\x00\x00\x00\x1a\x00[\x82\xff9\xc9\x1f\xff9\xc9\x1f\xff2\xc2\x1b\xff\xcd\xee\xc9\xff\xff\xff\xff\xff?\xc3)\xff8\xc8\x1f\xff9\xc9\x1f\xff1\xc0\x1a\xff\xf2\xfa\xf1\xff\xf2\xfa\xf1\xff1\xc0\x1a\xff9\xc9\x1f\xff9\xc9\x1f\xff\x00\x00\x00\x1a\x00_\x86\xff:\xcd"\xff:\xcd"\xff3\xc7\x1e\xff\xcd\xef\xca\xff\xff\xff\xff\xff?\xc8,\xff9\xcc"\xff:\xcd"\xff2\xc5\x1d\xff\xf2\xfb\xf1\xff\xf2\xfb\xf1\xff2\xc5\x1d\xff:\xcd"\xff:\xcd"\xff\x00\x00\x00\x1a\x00a\x8a\xff:\xd2%\xff:\xd2%\xff5\xce!\xff\xdb\xf5\xd8\xff\xff\xff\xff\xffE\xd14\xff9\xd2%\xff:\xd2%\xff4\xcd!\xff\xff\xff\xff\xff\xff\xff\xff\xff4\xcd!\xff:\xd2%\xff:\xd2%\xff\x00\x00\x00\x1a\x00d\x8e\xff:\xd5(\xff:\xd5(\xff8\xd4\'\xff5\xd1$\xff4\xd0#\xff8\xd3&\xff:\xd5(\xff:\xd5(\xff8\xd3&\xff4\xd0#\xff4\xd0#\xff8\xd3&\xff:\xd5(\xff:\xd5(\xff\x00\x00\x00\x1a\x00f\x91\xff:\xd8)\xff:\xd8)\xff:\xd8)\xff:\xd8)\xff:\xd8)\xff:\xd8)\xff:\xd8)\xff:\xd8)\xff:\xd8)\xff:\xd8)\xff:\xd8)\xff:\xd8)\xff:\xd8)\xff:\xd8)\xff\x00\x00\x00\x00\x00h\x93\xff\x00h\x93\xff\x00h\x93\xff\x00h\x93\xff\x00h\x93\xff\x00h\x93\xff\x00h\x93\xff\x00h\x93\xff\x00h\x93\xff\x00h\x93\xff\x00h\x93\xff\x00h\x93\xff\x00h\x93\xff\x00h\x93\xff\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xc0\x00\x00\x00\x80\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x01\x00\x00\x00\x03\x00\x00\xff\xff\x00\x00'
    ,
    '\x00\x00\x01\x00\x01\x00\x10\x10\x00\x00\x01\x00 \x00h\x04\x00\x00\x16\x00\x00\x00(\x00\x00\x00\x10\x00\x00\x00 \x00\x00\x00\x01\x00 \x00\x00\x00\x00\x00@\x04\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x1a\x00\x00\x00\x1a\x00\x00\x00\x1a\x00\x00\x00\x1a\x00\x00\x00\x1a\x00\x00\x00\x1a\x00\x00\x00\x1a\x00\x00\x00\x1a\x00\x00\x00\x1a\x00\x00\x00\x1a\x00\x00\x00\x1a\x00\x00\x00\x1a\x00\x00\x00\x1a\x00\x00\x00\x1a\x00\x00\x00\x00\xa1h\x03\xff\xa1h\x03\xff\xa1h\x03\xff\xa1h\x03\xff\xa1h\x03\xff\xa1h\x03\xff\xa1h\x03\xff\xa1h\x03\xff\xa1h\x03\xff\xa1h\x03\xff\xa1h\x03\xff\xa1h\x03\xff\xa1h\x03\xff\xa1h\x03\xff\x00\x00\x00\x1a\x00Fe\xff\xa6m\x03\xff\xa6m\x03\xff\xa4k\x03\xff\x9fe\x03\xff\x9ee\x03\xff\xa3j\x03\xff\xa6m\x03\xff\xa6m\x03\xff\xa3j\x03\xff\x9ee\x03\xff\x9ee\x03\xff\xa3j\x03\xff\xa6m\x03\xff\xa6m\x03\xff\x00\x00\x00\x1a\x00Hh\xff\xads\x02\xff\xads\x02\xff\xa7l\x02\xff\xea\xde\xcb\xff\xff\xff\xff\xff\xabu\x16\xff\xacr\x02\xff\xads\x02\xff\xa6k\x02\xff\xfc\xfa\xf7\xff\xfc\xfa\xf7\xff\xa6k\x02\xff\xads\x02\xff\xads\x02\xff\x00\x00\x00\x1a\x00Kl\xff\xb4y\x02\xff\xb4y\x02\xff\xacp\x02\xff\xe8\xda\xc4\xff\xff\xff\xff\xff\xafu\x13\xff\xb3x\x02\xff\xb4y\x02\xff\xabn\x02\xff\xf9\xf5\xf0\xff\xf9\xf5\xf0\xff\xabn\x02\xff\xb4y\x02\xff\xb4y\x02\xff\x00\x00\x00\x1a\x00Np\xff\xbc\x80\x02\xff\xbc\x80\x02\xff\xb5w\x02\xff\xeb\xdc\xc4\xff\xff\xff\xff\xff\xb1s\n\xff\xb6x\x02\xff\xb6y\x02\xff\xafo\x01\xff\xf8\xf4\xed\xff\xfa\xf6\xf0\xff\xb3u\x02\xff\xbc\x80\x02\xff\xbc\x80\x02\xff\x00\x00\x00\x1a\x00Qt\xff\xc4\x87\x02\xff\xc4\x87\x02\xff\xbd~\x02\xff\xed\xdd\xc4\xff\xff\xff\xff\xff\xdd\xbe\x91\xff\xe1\xc7\x9c\xff\xe1\xc7\x9c\xff\xde\xc0\x94\xff\xfc\xfa\xf7\xff\xfa\xf5\xee\xff\xbc|\x02\xff\xc4\x87\x02\xff\xc4\x87\x02\xff\x00\x00\x00\x1a\x00Uy\xff\xce\x8f\x01\xff\xce\x8f\x01\xff\xc8\x86\x01\xff\xf0\xdf\xc4\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xfa\xf5\xed\xff\xc7\x84\x01\xff\xce\x8f\x01\xff\xce\x8f\x01\xff\x00\x00\x00\x1a\x00X}\xff\xd6\x96\x01\xff\xd6\x96\x01\xff\xd1\x8d\x01\xff\xf2\xe1\xc4\xff\xff\xff\xff\xff\xcb\x82\x03\xff\xcf\x8a\x01\xff\xd0\x8a\x01\xff\xcb\x82\x01\xff\xfa\xf4\xeb\xff\xfb\xf6\xef\xff\xd0\x8b\x01\xff\xd6\x96\x01\xff\xd6\x96\x01\xff\x00\x00\x00\x1a\x00[\x82\xff\xde\x9d\x01\xff\xde\x9d\x01\xff\xda\x94\x01\xff\xf4\xe3\xc4\xff\xff\xff\xff\xff\xdb\x99\x13\xff\xde\x9c\x01\xff\xde\x9d\x01\xff\xd9\x92\x01\xff\xfc\xf7\xf0\xff\xfc\xf7\xf0\xff\xd9\x92\x01\xff\xde\x9d\x01\xff\xde\x9d\x01\xff\x00\x00\x00\x1a\x00_\x86\xff\xe5\xa4\x01\xff\xe5\xa4\x01\xff\xe2\x9c\x01\xff\xf7\xe4\xc4\xff\xff\xff\xff\xff\xe2\x9e\x13\xff\xe5\xa3\x01\xff\xe5\xa4\x01\xff\xe1\x9a\x01\xff\xfd\xf8\xf0\xff\xfd\xf8\xf0\xff\xe1\x9a\x01\xff\xe5\xa4\x01\xff\xe5\xa4\x01\xff\x00\x00\x00\x1a\x00a\x8a\xff\xec\xa9\x00\xff\xec\xa9\x00\xff\xea\xa3\x00\xff\xfb\xed\xd4\xff\xff\xff\xff\xff\xeb\xa8\x16\xff\xec\xa8\x00\xff\xec\xa9\x00\xff\xea\xa1\x00\xff\xff\xff\xff\xff\xff\xff\xff\xff\xea\xa1\x00\xff\xec\xa9\x00\xff\xec\xa9\x00\xff\x00\x00\x00\x1a\x00d\x8e\xff\xf1\xae\x00\xff\xf1\xae\x00\xff\xf0\xac\x00\xff\xef\xa7\x00\xff\xef\xa6\x00\xff\xf0\xab\x00\xff\xf1\xae\x00\xff\xf1\xae\x00\xff\xf0\xab\x00\xff\xef\xa6\x00\xff\xef\xa6\x00\xff\xf0\xab\x00\xff\xf1\xae\x00\xff\xf1\xae\x00\xff\x00\x00\x00\x1a\x00f\x91\xff\xf5\xb2\x00\xff\xf5\xb2\x00\xff\xf5\xb2\x00\xff\xf5\xb2\x00\xff\xf5\xb2\x00\xff\xf5\xb2\x00\xff\xf5\xb2\x00\xff\xf5\xb2\x00\xff\xf5\xb2\x00\xff\xf5\xb2\x00\xff\xf5\xb2\x00\xff\xf5\xb2\x00\xff\xf5\xb2\x00\xff\xf5\xb2\x00\xff\x00\x00\x00\x00\x00h\x93\xff\x00h\x93\xff\x00h\x93\xff\x00h\x93\xff\x00h\x93\xff\x00h\x93\xff\x00h\x93\xff\x00h\x93\xff\x00h\x93\xff\x00h\x93\xff\x00h\x93\xff\x00h\x93\xff\x00h\x93\xff\x00h\x93\xff\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xc0\x00\x00\x00\x80\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x01\x00\x00\x00\x03\x00\x00\xff\xff\x00\x00'
    ,
    '\x00\x00\x01\x00\x01\x00\x10\x10\x00\x00\x01\x00 \x00h\x04\x00\x00\x16\x00\x00\x00(\x00\x00\x00\x10\x00\x00\x00 \x00\x00\x00\x01\x00 \x00\x00\x00\x00\x00@\x04\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x1a\x00\x00\x00\x1a\x00\x00\x00\x1a\x00\x00\x00\x1a\x00\x00\x00\x1a\x00\x00\x00\x1a\x00\x00\x00\x1a\x00\x00\x00\x1a\x00\x00\x00\x1a\x00\x00\x00\x1a\x00\x00\x00\x1a\x00\x00\x00\x1a\x00\x00\x00\x1a\x00\x00\x00\x1a\x00\x00\x00\x00\xa1\x056\xff\xa1\x056\xff\xa1\x056\xff\xa1\x056\xff\xa1\x056\xff\xa1\x056\xff\xa1\x056\xff\xa1\x056\xff\xa1\x056\xff\xa1\x056\xff\xa1\x056\xff\xa1\x056\xff\xa1\x056\xff\xa1\x056\xff\x00\x00\x00\x1a\x00Fe\xff\xa6\x082\xff\xa6\x082\xff\xa4\x080\xff\x9f\x07-\xff\x9e\x07-\xff\xa3\x080\xff\xa6\x082\xff\xa6\x082\xff\xa3\x080\xff\x9e\x07-\xff\x9e\x07-\xff\xa3\x080\xff\xa6\x082\xff\xa6\x082\xff\x00\x00\x00\x1a\x00Hh\xff\xad\x0b.\xff\xad\x0b.\xff\xa7\n*\xff\xea\xcc\xd2\xff\xff\xff\xff\xff\xab\x1c:\xff\xac\x0b.\xff\xad\x0b.\xff\xa6\n)\xff\xfc\xf7\xf8\xff\xfc\xf7\xf8\xff\xa6\n)\xff\xad\x0b.\xff\xad\x0b.\xff\x00\x00\x00\x1a\x00Kl\xff\xb4\x0f)\xff\xb4\x0f)\xff\xac\r$\xff\xe8\xc7\xcb\xff\xff\xff\xff\xff\xaf\x1c2\xff\xb3\x0f)\xff\xb4\x0f)\xff\xab\r#\xff\xf9\xf0\xf1\xff\xf9\xf0\xf1\xff\xab\r#\xff\xb4\x0f)\xff\xb4\x0f)\xff\x00\x00\x00\x1a\x00Np\xff\xbc\x12$\xff\xbc\x12$\xff\xb5\x10\x1f\xff\xeb\xc7\xca\xff\xff\xff\xff\xff\xb1\x15#\xff\xb6\x10 \xff\xb6\x10 \xff\xaf\x0e\x1c\xff\xf8\xee\xee\xff\xfa\xf1\xf1\xff\xb3\x0f\x1e\xff\xbc\x12$\xff\xbc\x12$\xff\x00\x00\x00\x1a\x00Qt\xff\xc4\x15\x1f\xff\xc4\x15\x1f\xff\xbd\x13\x1b\xff\xed\xc8\xc9\xff\xff\xff\xff\xff\xdd\x96\x99\xff\xe1\xa1\xa4\xff\xe1\xa1\xa4\xff\xde\x99\x9b\xff\xfc\xf7\xf7\xff\xfa\xef\xef\xff\xbc\x12\x1a\xff\xc4\x15\x1f\xff\xc4\x15\x1f\xff\x00\x00\x00\x1a\x00Uy\xff\xce\x1a\x19\xff\xce\x1a\x19\xff\xc8\x17\x16\xff\xf0\xc9\xc8\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xfa\xee\xee\xff\xc7\x16\x15\xff\xce\x1a\x19\xff\xce\x1a\x19\xff\x00\x00\x00\x1a\x00X}\xff\xd6\x1e\x14\xff\xd6\x1e\x14\xff\xd1\x1a\x12\xff\xf2\xc9\xc8\xff\xff\xff\xff\xff\xcb\x17\x11\xff\xcf\x19\x11\xff\xd0\x19\x11\xff\xcb\x15\x0f\xff\xfa\xec\xec\xff\xfb\xf0\xf0\xff\xd0\x19\x12\xff\xd6\x1e\x14\xff\xd6\x1e\x14\xff\x00\x00\x00\x1a\x00[\x82\xff\xde"\x0f\xff\xde"\x0f\xff\xda\x1e\r\xff\xf4\xca\xc7\xff\xff\xff\xff\xff\xdb,\x1c\xff\xde"\x0f\xff\xde"\x0f\xff\xd9\x1d\r\xff\xfc\xf1\xf0\xff\xfc\xf1\xf0\xff\xd9\x1d\r\xff\xde"\x0f\xff\xde"\x0f\xff\x00\x00\x00\x1a\x00_\x86\xff\xe5%\x0b\xff\xe5%\x0b\xff\xe2 \t\xff\xf7\xca\xc5\xff\xff\xff\xff\xff\xe2.\x19\xff\xe5$\x0b\xff\xe5%\x0b\xff\xe1\x1f\t\xff\xfd\xf1\xf0\xff\xfd\xf1\xf0\xff\xe1\x1f\t\xff\xe5%\x0b\xff\xe5%\x0b\xff\x00\x00\x00\x1a\x00a\x8a\xff\xec(\x06\xff\xec(\x06\xff\xea$\x05\xff\xfb\xd9\xd5\xff\xff\xff\xff\xff\xeb6\x1b\xff\xec(\x06\xff\xec(\x06\xff\xea#\x05\xff\xff\xff\xff\xff\xff\xff\xff\xff\xea#\x05\xff\xec(\x06\xff\xec(\x06\xff\x00\x00\x00\x1a\x00d\x8e\xff\xf1+\x03\xff\xf1+\x03\xff\xf0*\x03\xff\xef\'\x03\xff\xef&\x03\xff\xf0)\x03\xff\xf1+\x03\xff\xf1+\x03\xff\xf0)\x03\xff\xef&\x03\xff\xef&\x03\xff\xf0)\x03\xff\xf1+\x03\xff\xf1+\x03\xff\x00\x00\x00\x1a\x00f\x91\xff\xf5-\x00\xff\xf5-\x00\xff\xf5-\x00\xff\xf5-\x00\xff\xf5-\x00\xff\xf5-\x00\xff\xf5-\x00\xff\xf5-\x00\xff\xf5-\x00\xff\xf5-\x00\xff\xf5-\x00\xff\xf5-\x00\xff\xf5-\x00\xff\xf5-\x00\xff\x00\x00\x00\x00\x00h\x93\xff\x00h\x93\xff\x00h\x93\xff\x00h\x93\xff\x00h\x93\xff\x00h\x93\xff\x00h\x93\xff\x00h\x93\xff\x00h\x93\xff\x00h\x93\xff\x00h\x93\xff\x00h\x93\xff\x00h\x93\xff\x00h\x93\xff\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xc0\x00\x00\x00\x80\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x01\x00\x00\x00\x03\x00\x00\xff\xff\x00\x00'
    ,
    '\x00\x00\x01\x00\x01\x00\x10\x10\x00\x00\x01\x00 \x00h\x04\x00\x00\x16\x00\x00\x00(\x00\x00\x00\x10\x00\x00\x00 \x00\x00\x00\x01\x00 \x00\x00\x00\x00\x00@\x04\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x1a\x00\x00\x00\x1a\x00\x00\x00\x1a\x00\x00\x00\x1a\x00\x00\x00\x1a\x00\x00\x00\x1a\x00\x00\x00\x1a\x00\x00\x00\x1a\x00\x00\x00\x1a\x00\x00\x00\x1a\x00\x00\x00\x1a\x00\x00\x00\x1a\x00\x00\x00\x1a\x00\x00\x00\x1a\x00\x00\x00\x00444\xff444\xff444\xff444\xff444\xff444\xff444\xff444\xff444\xff444\xff444\xff444\xff444\xff444\xff\x00\x00\x00\x1a\x00Fe\xff888\xff888\xff666\xff333\xff222\xff666\xff888\xff888\xff666\xff222\xff222\xff666\xff888\xff888\xff\x00\x00\x00\x1a\x00Hh\xff;;;\xff;;;\xff666\xff\xd4\xd4\xd4\xff\xff\xff\xff\xffEEE\xff:::\xff;;;\xff555\xff\xf8\xf8\xf8\xff\xf8\xf8\xf8\xff555\xff;;;\xff;;;\xff\x00\x00\x00\x1a\x00Kl\xff@@@\xff@@@\xff999\xff\xcf\xcf\xcf\xff\xff\xff\xff\xffDDD\xff???\xff@@@\xff888\xff\xf2\xf2\xf2\xff\xf2\xf2\xf2\xff888\xff@@@\xff@@@\xff\x00\x00\x00\x1a\x00Np\xffDDD\xffDDD\xff===\xff\xcf\xcf\xcf\xff\xff\xff\xff\xff===\xff>>>\xff>>>\xff777\xff\xf0\xf0\xf0\xff\xf3\xf3\xf3\xff;;;\xffDDD\xffDDD\xff\x00\x00\x00\x1a\x00Qt\xffIII\xffIII\xffAAA\xff\xd0\xd0\xd0\xff\xff\xff\xff\xff\xa6\xa6\xa6\xff\xb0\xb0\xb0\xff\xb0\xb0\xb0\xff\xa8\xa8\xa8\xff\xf8\xf8\xf8\xff\xf1\xf1\xf1\xff@@@\xffIII\xffIII\xff\x00\x00\x00\x1a\x00Uy\xffNNN\xffNNN\xffFFF\xff\xd1\xd1\xd1\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xf1\xf1\xf1\xffEEE\xffNNN\xffNNN\xff\x00\x00\x00\x1a\x00X}\xffSSS\xffSSS\xffKKK\xff\xd2\xd2\xd2\xff\xff\xff\xff\xffAAA\xffHHH\xffHHH\xffAAA\xff\xef\xef\xef\xff\xf2\xf2\xf2\xffIII\xffSSS\xffSSS\xff\x00\x00\x00\x1a\x00[\x82\xffWWW\xffWWW\xffOOO\xff\xd3\xd3\xd3\xff\xff\xff\xff\xffXXX\xffVVV\xffWWW\xffMMM\xff\xf3\xf3\xf3\xff\xf3\xf3\xf3\xffMMM\xffWWW\xffWWW\xff\x00\x00\x00\x1a\x00_\x86\xff\\\\\\\xff\\\\\\\xffSSS\xff\xd4\xd4\xd4\xff\xff\xff\xff\xff[[[\xff[[[\xff\\\\\\\xffQQQ\xff\xf4\xf4\xf4\xff\xf4\xf4\xf4\xffQQQ\xff\\\\\\\xff\\\\\\\xff\x00\x00\x00\x1a\x00a\x8a\xff___\xff___\xffXXX\xff\xe0\xe0\xe0\xff\xff\xff\xff\xffddd\xff^^^\xff___\xffWWW\xff\xff\xff\xff\xff\xff\xff\xff\xffWWW\xff___\xff___\xff\x00\x00\x00\x1a\x00d\x8e\xffccc\xffccc\xffaaa\xff\\\\\\\xff[[[\xff```\xffccc\xffccc\xff```\xffZZZ\xffZZZ\xff```\xffccc\xffccc\xff\x00\x00\x00\x1a\x00f\x91\xffeee\xffeee\xffeee\xffeee\xffeee\xffeee\xffeee\xffeee\xffeee\xffeee\xffeee\xffeee\xffeee\xffeee\xff\x00\x00\x00\x00\x00h\x93\xff\x00h\x93\xff\x00h\x93\xff\x00h\x93\xff\x00h\x93\xff\x00h\x93\xff\x00h\x93\xff\x00h\x93\xff\x00h\x93\xff\x00h\x93\xff\x00h\x93\xff\x00h\x93\xff\x00h\x93\xff\x00h\x93\xff\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xc0\x00\x00\x00\x80\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x01\x00\x00\x00\x03\x00\x00\xff\xff\x00\x00'
    ]
########NEW FILE########
__FILENAME__ = nix_notify
# -*- coding: utf-8 -*-

import pynotify

def showNotify(title, msg):
    pynotify.Notification(title, msg).show()

if __name__ == "__main__":
    showNotify(u"标题", u"内容")

########NEW FILE########
__FILENAME__ = ToasterBox
# --------------------------------------------------------------------------- #
# TOASTERBOX wxPython IMPLEMENTATION
# Ported And Enhanced From wxWidgets Contribution (Aj Bommarito) By:
#
# Andrea Gavana, @ 16 September 2005
# Latest Revision: 31 Oct 2007, 21.30 CET
#
#
# TODO/Caveats List
#
# 1. Any Idea?
#
#
# For All Kind Of Problems, Requests Of Enhancements And Bug Reports, Please
# Write To Me At:
#
# andrea.gavana@gmail.it
# gavana@kpo.kz
#
# Or, Obviously, To The wxPython Mailing List!!!
#
#
# End Of Comments
# --------------------------------------------------------------------------- #


"""Description:

ToasterBox Is A Cross-Platform Library To Make The Creation Of MSN Style "Toaster"
Popups Easier. The Syntax Is Really Easy Especially If You Are Familiar With The
Syntax Of wxPython.

It Has 2 Main Styles:

- TB_SIMPLE:  Using This Style, You Will Be Able To Specify A Background Image For
             ToasterBox, Text Properties As Text Colour, Font And Label.

- TB_COMPLEX: This Style Will Allow You To Put Almost Any Control Inside A
             ToasterBox. You Can Add A Panel In Which You Can Put All The Controls
             You Like.

Both Styles Support The Setting Of ToasterBox Position (On Screen Coordinates),
Size, The Time After Which The ToasterBox Is Destroyed (Linger), And The Scroll
Speed Of ToasterBox.

ToasterBox Has Been Tested On The Following Platforms:

Windows (Verified on Windows XP, 2000)


Latest Revision: Andrea Gavana @ 31 Oct 2007, 21.30 CET

"""

import textwrap
import wx
import sys

from wx.lib.statbmp import GenStaticBitmap as StaticBitmap

# Define Window List, We Use It Globally
winlist = []

TB_SIMPLE = 1
TB_COMPLEX = 2

DEFAULT_TB_STYLE = wx.SIMPLE_BORDER | wx.STAY_ON_TOP | wx.FRAME_NO_TASKBAR
TB_CAPTION = DEFAULT_TB_STYLE | wx.CAPTION | wx.SYSTEM_MENU | wx.CLOSE_BOX | wx.FRAME_TOOL_WINDOW

TB_ONTIME = 1
TB_ONCLICK = 2

# scroll from up to down
TB_SCR_TYPE_UD = 1
# scroll from down to up
TB_SCR_TYPE_DU = 2

# ------------------------------------------------------------------------------ #
# Class ToasterBox
#    Main Class Implementation. It Is Basically A wx.Timer. It Creates And
#    Displays Popups And Handles The "Stacking".
# ------------------------------------------------------------------------------ #

class ToasterBox(wx.Timer):

   def __init__(self, parent, tbstyle=TB_SIMPLE, windowstyle=DEFAULT_TB_STYLE,
                closingstyle=TB_ONTIME, scrollType=TB_SCR_TYPE_DU):
       """Deafult Class Constructor.

       ToasterBox.__init__(self, tbstyle=TB_SIMPLE, windowstyle=DEFAULT_TB_STYLE)

       Parameters:

       - tbstyle: This Parameter May Have 2 Values:
         (a) TB_SIMPLE: A Simple ToasterBox, With Background Image And Text
             Customization Can Be Created;
         (b) TB_COMPLEX: ToasterBoxes With Different Degree Of Complexity Can
             Be Created. You Can Add As Many Controls As You Want, Provided
             That You Call The AddPanel() Method And Pass To It A Dummy Frame
             And A wx.Panel. See The Demo For Details.

       - windowstyle: This Parameter Influences The Visual Appearance Of ToasterBox:
         (a) DEFAULT_TB_STYLE: Default Style, No Caption Nor Close Box;
         (b) TB_CAPTION: ToasterBox Will Have A Caption, With The Possibility To
             Set A Title For ToasterBox Frame, And A Close Box;

       - closingstyle: Set This Value To TB_ONCLICK If You Want To Be Able To Close
         ToasterBox By A Mouse Click Anywhere In The ToasterBox Frame.

       """

       self._parent = parent
       self._sleeptime = 10
       self._pausetime = 1700
       self._popuptext = "default"
       self._popupposition = wx.Point(100,100)
       self._popuptop = wx.Point(0,0)
       self._popupsize = wx.Size(150, 170)

       self._backgroundcolour = wx.WHITE
       self._foregroundcolour = wx.BLACK
       if sys.platform != "darwin":
           self._textfont = wx.Font(8, wx.SWISS, wx.NORMAL, wx.NORMAL, False, "Verdana")
       else:
           self._textfont = wx.Font(12, wx.SWISS, wx.NORMAL, wx.NORMAL, False, "Monaco")

       self._bitmap = None

       self._tbstyle = tbstyle
       self._windowstyle = windowstyle
       self._closingstyle = closingstyle

       self._panel = None

       self._bottomright = wx.Point(wx.GetDisplaySize().GetWidth(),
                                    wx.GetDisplaySize().GetHeight())

       parent.Bind(wx.EVT_ICONIZE, lambda evt: [w.Hide() for w in winlist])

       self._tb = ToasterBoxWindow(self._parent, self, self._tbstyle, self._windowstyle,
                                   self._closingstyle, scrollType=scrollType)


   def SetPopupPosition(self, pos):
       """ Sets The ToasterBox Position On Screen. """

       self._popupposition = pos


   def SetPopupPositionByInt(self, pos):
       """ Sets The ToasterBox Position On Screen, At One Of The Screen Corners. """

       self._bottomright = wx.Point(wx.GetDisplaySize().GetWidth(),
                                    wx.GetDisplaySize().GetHeight())

       # top left
       if pos == 0:
           popupposition = wx.Point(0,0)
       # top right
       elif pos == 1:
           popupposition = wx.Point(wx.GetDisplaySize().GetWidth() -
                                    self._popupsize[0], 0)
       # bottom left
       elif pos == 2:
           popupposition = wxPoint(0, wx.GetDisplaySize().GetHeight() -
                                   self._popupsize[1])
       # bottom right
       elif pos == 3:
           popupposition = wx.Point(self._bottomright.x - self._popupsize[0],
                                    self._bottomright.y - self._popupsize[1])

       self._bottomright = wx.Point(popupposition.x + self._popupsize[0],
                                    popupposition.y + self._popupsize[1])


   def SetPopupBackgroundColor(self, colour=None):
       """ Sets The ToasterBox Background Colour. Use It Only For ToasterBoxes Created
       With TB_SIMPLE Style. """

       if colour is None:
           colour = wx.WHITE

       self._backgroundcolour = colour


   def SetPopupTextColor(self, colour=None):
       """ Sets The ToasterBox Foreground Colour. Use It Only For ToasterBoxes Created
       With TB_SIMPLE Style. """

       if colour is None:
           colour = wx.BLACK

       self._foregroundcolour = colour


   def SetPopupTextFont(self, font=None):
       """ Sets The ToasterBox Text Font. Use It Only For ToasterBoxes Created With
       TB_SIMPLE Style. """

       if font is None:
           if sys.platform != "darwin":
               font = wx.Font(8, wx.SWISS, wx.NORMAL, wx.NORMAL, False, "Verdana")
           else:
               font = wx.Font(12, wx.SWISS, wx.NORMAL, wx.NORMAL, False, "Monaco")

       self._textfont = font


   def SetPopupSize(self, size):
       """ Sets The ToasterBox Size. """

       self._popupsize = size


   def SetPopupPauseTime(self, pausetime):
       """ Sets The Time After Which The ToasterBox Is Destroyed (Linger). """

       self._pausetime = pausetime


   def SetPopupBitmap(self, bitmap=None):
       """ Sets The ToasterBox Background Image. Use It Only For ToasterBoxes
       Created With TB_SIMPLE Style. """

       if bitmap is not None:
           bitmap = wx.Bitmap(bitmap, wx.BITMAP_TYPE_BMP)

       self._bitmap = bitmap


   def SetPopupScrollSpeed(self, speed):
       """ Sets The ToasterBox Scroll Speed. The Speed Parameter Is The Pause
       Time (In ms) For Every Step In The ScrollUp() Method."""

       self._sleeptime = speed


   def SetPopupText(self, text):
       """ Sets The ToasterBox Text. Use It Only For ToasterBoxes Created With
       TB_SIMPLE Style. """

       self._popuptext = text


   def AddPanel(self, panel):
       """ Adds A Panel To The ToasterBox. Use It Only For ToasterBoxes Created
       With TB_COMPLEX Style. """

       if not self._tbstyle & TB_COMPLEX:
           raise "\nERROR: Panel Can Not Be Added When Using TB_SIMPLE ToasterBox Style"
           return

       self._panel = panel


   def Play(self):
       """ Creates The ToasterBoxWindow, That Does All The Job. """

       # create new window
       self._tb.SetPopupSize((self._popupsize[0], self._popupsize[1]))
       self._tb.SetPopupPosition((self._popupposition[0], self._popupposition[1]))
       self._tb.SetPopupPauseTime(self._pausetime)
       self._tb.SetPopupScrollSpeed(self._sleeptime)

       if self._tbstyle == TB_SIMPLE:
           self._tb.SetPopupTextColor(self._foregroundcolour)
           self._tb.SetPopupBackgroundColor(self._backgroundcolour)
           self._tb.SetPopupTextFont(self._textfont)

           if self._bitmap is not None:
               self._tb.SetPopupBitmap(self._bitmap)

           self._tb.SetPopupText(self._popuptext)

       if self._tbstyle == TB_COMPLEX:
           if self._panel is not None:
               self._tb.AddPanel(self._panel)

       # clean up the list
       self.CleanList()

       # check to see if there is already a window displayed
       # by looking at the linked list
       if len(winlist) > 0:
           # there ARE other windows displayed already
           # reclac where it should display
           self.MoveAbove(self._tb)

       # shift new window on to the list
       winlist.append(self._tb)

       if not self._tb.Play():
           # if we didn't show the window properly, remove it from the list
           winlist.remove(winlist[-1])
           # delete the object too
           self._tb.Destroy()
           return


   def MoveAbove(self, tb):
       """ If A ToasterBox Already Exists, Move The New One Above. """

       # recalc where to place this popup

       self._tb.SetPopupPosition((self._popupposition[0], self._popupposition[1] -
                                  self._popupsize[1]*len(winlist)))


   def GetToasterBoxWindow(self):
       """ Returns The ToasterBox Frame. """

       return self._tb


   def SetTitle(self, title):
       """ Sets The ToasterBox Title If It Was Created With TB_CAPTION Window Style. """

       self._tb.SetTitle(title)


   def Notify(self):
       """ It's Time To Hide A ToasterBox! """

       if len(winlist) == 0:
           return

       # clean the window list
       self.CleanList()

       # figure out how many blanks we have
       try:
           node = winlist[0]
       except:
           return

       if not node:
           return

       # move windows to fill in blank space
       for i in xrange(node.GetPosition()[1], self._popupposition[1], 4):
           if i > self._popupposition[1]:
               i = self._popupposition[1]

           # loop through all the windows
           for j in xrange(0, len(winlist)):
               ourNewHeight = i - (j*self._popupsize[1] - 8)
               tmpTb = winlist[j]
               # reset where the object THINKS its supposed to be
               tmpTb.SetPopupPosition((self._popupposition[0], ourNewHeight))
               # actually move it
               tmpTb.SetDimensions(self._popupposition[0], ourNewHeight, tmpTb.GetSize().GetWidth(),
                                   tmpTb.GetSize().GetHeight())

           wx.Usleep(self._sleeptime)


   def CleanList(self):
       """ Clean The Window List. """

       if len(winlist) == 0:
           return

       node = winlist[0]
       while node:
           if not node.IsShown():
               winlist.remove(node)
               try:
                   node = winlist[0]
               except:
                   node = 0
           else:
               indx = winlist.index(node)
               try:
                   node = winlist[indx+1]
               except:
                   node = 0


# ------------------------------------------------------------------------------ #
# Class ToasterBoxWindow
#    This Class Does All The Job, By Handling Background Images, Text Properties
#    And Panel Adding. Depending On The Style You Choose, ToasterBoxWindow Will
#    Behave Differently In Order To Handle Widgets Inside It.
# ------------------------------------------------------------------------------ #

class ToasterBoxWindow(wx.Frame):

   def __init__(self, parent, parent2, tbstyle, windowstyle,
       closingstyle, scrollType=TB_SCR_TYPE_DU):
       """Default Class Constructor.

       Used Internally. Do Not Call Directly This Class In Your Application!
       """

       wx.Frame.__init__(self, parent, wx.ID_ANY, "window", wx.DefaultPosition,
                         wx.DefaultSize, style=windowstyle | wx.CLIP_CHILDREN)

       self._starttime = wx.GetLocalTime()
       self._parent2 = parent2
       self._parent = parent
       self._sleeptime = 10
       self._step = 4
       self._pausetime = 1700
       self._textcolour = wx.BLACK
       self._popuptext = "Change Me!"
       # the size we want the dialog to be
       framesize = wx.Size(150, 170)
       self._count = 1
       self._tbstyle = tbstyle
       self._windowstyle = windowstyle
       self._closingstyle = closingstyle
       self._scrollType = scrollType


       if tbstyle == TB_COMPLEX:
           self.sizer = wx.BoxSizer(wx.VERTICAL)
       else:
           self._staticbitmap = None

       if self._windowstyle == TB_CAPTION:
           self.Bind(wx.EVT_CLOSE, self.OnClose)
           self.SetTitle("")

       if self._closingstyle & TB_ONCLICK and self._windowstyle != TB_CAPTION:
           self.Bind(wx.EVT_LEFT_DOWN, self.OnMouseDown)

       self._bottomright = wx.Point(wx.GetDisplaySize().GetWidth(),
                                    wx.GetDisplaySize().GetHeight())

       self.SetDimensions(self._bottomright.x, self._bottomright.y,
                          framesize.GetWidth(), framesize.GetHeight())


   def OnClose(self, event):

       self.NotifyTimer(None)
       event.Skip()


   def OnMouseDown(self, event):

       self.NotifyTimer(None)
       event.Skip()


   def SetPopupBitmap(self, bitmap):
       """ Sets The ToasterBox Background Image. Use It Only For ToasterBoxes
       Created With TB_SIMPLE Style. """

       bitmap = bitmap.ConvertToImage()
       xsize, ysize = self.GetSize()
       bitmap = bitmap.Scale(xsize, ysize)
       bitmap = bitmap.ConvertToBitmap()
       self._staticbitmap = StaticBitmap(self, -1, bitmap, pos=(0,0))

       if self._closingstyle & TB_ONCLICK and self._windowstyle != TB_CAPTION:
           self._staticbitmap.Bind(wx.EVT_LEFT_DOWN, self.OnMouseDown)


   def SetPopupSize(self, size):
       """ Sets The ToasterBox Size. """

       self.SetDimensions(self._bottomright.x, self._bottomright.y, size[0], size[1])


   def SetPopupPosition(self, pos):
       """ Sets The ToasterBox Position On Screen. """

       self._bottomright = wx.Point(pos[0] + self.GetSize().GetWidth(),
                                    pos[1] + self.GetSize().GetHeight())
       self._dialogtop = pos


   def SetPopupPositionByInt(self, pos):
       """ Sets The ToasterBox Position On Screen, At One Of The Screen Corners. """

       self._bottomright = wx.Point(wx.GetDisplaySize().GetWidth(),
                                    wx.GetDisplaySize().GetHeight())

       # top left
       if pos == 0:
           popupposition = wx.Point(0,0)
       # top right
       elif pos == 1:
           popupposition = wx.Point(wx.GetDisplaySize().GetWidth() -
                                    self._popupsize[0], 0)
       # bottom left
       elif pos == 2:
           popupposition = wx.Point(0, wx.GetDisplaySize().GetHeight() -
                                   self._popupsize[1])
       # bottom right
       elif pos == 3:
           popupposition = wx.Point(self._bottomright.x - self._popupsize[0],
                                    self._bottomright.y - self._popupsize[1])

       self._bottomright = wx.Point(popupposition.x + self._popupsize[0],
                                    popupposition.y + self._popupsize[1])

       self._dialogtop = popupposition


   def SetPopupPauseTime(self, pausetime):
       """ Sets The Time After Which The ToasterBox Is Destroyed (Linger). """

       self._pausetime = pausetime


   def SetPopupScrollSpeed(self, speed):
       """ Sets The ToasterBox Scroll Speed. The Speed Parameter Is The Pause
       Time (In ms) For Every Step In The ScrollUp() Method."""

       self._sleeptime = speed


   def AddPanel(self, panel):
       """ Adds A Panel To The ToasterBox. Use It Only For ToasterBoxes Created
       With TB_COMPLEX Style. """

       if not self._tbstyle & TB_COMPLEX:
           raise "\nERROR: Panel Can Not Be Added When Using TB_SIMPLE ToasterBox Style"
           return

       self.sizer.Add(panel, 1, wx.EXPAND)
       self.sizer.Layout()
       self.SetSizer(self.sizer)

       if self._closingstyle & TB_ONCLICK and self._windowstyle != TB_CAPTION:
           panel.Bind(wx.EVT_LEFT_DOWN, self.OnMouseDown)


   def SetPopupText(self, text):
       """ Sets The ToasterBox Text. Use It Only For ToasterBoxes Created With
       TB_SIMPLE Style. """

       self._popuptext = text


   def SetPopupTextFont(self, font):
       """ Sets The ToasterBox Text Font. Use It Only For ToasterBoxes Created With
       TB_SIMPLE Style. """

       self._textfont = font


   def GetPopupText(self):
       """ Returns The ToasterBox Text. Use It Only For ToasterBoxes Created With
       TB_SIMPLE Style. """

       return self._popuptext


   def Play(self):
       """ Creates The ToasterBoxWindow, That Does All The Job. """

       # do some checks to make sure this window is valid
       if self._bottomright.x < 1 or self._bottomright.y < 1:
           return False

       if self.GetSize().GetWidth() < 50 or self.GetSize().GetWidth() < 50:
           # toasterbox launches into a endless loop for some reason
           # when you try to make the window too small.
           return False

       self.ScrollUp()
       timerid = wx.NewId()
       self.showtime = wx.Timer(self, timerid)
       self.showtime.Start(self._pausetime)
       self.Bind(wx.EVT_TIMER, self.NotifyTimer, id=timerid)

       return True


   def NotifyTimer(self, event):
       """ Hides Gradually The ToasterBoxWindow. """

       self.showtime.Stop()
       del self.showtime
       self.ScrollDown()


   def SetPopupBackgroundColor(self, colour):
       """ Sets The ToasterBox Background Colour. Use It Only For ToasterBoxes Created
       With TB_SIMPLE Style. """

       self.SetBackgroundColour(colour)


   def SetPopupTextColor(self, colour):
       """ Sets The ToasterBox Foreground Colour. Use It Only For ToasterBoxes Created
       With TB_SIMPLE Style. """

       self._textcolour = colour


   def ScrollUp(self):
       """ Scrolls The ToasterBox Up, Which Means Gradually Showing The ToasterBox. """

       self.Show(True)

       # walk the Y value up in a raise motion
       xpos = self.GetPosition().x
       ypos = self._bottomright[1]
       windowsize = 0

       # checking the type of the scroll (from up to down or from down to up)
       if self._scrollType == TB_SCR_TYPE_UD:
           start = self._dialogtop[1]
           stop = ypos
           step = self._step
       elif self._scrollType == TB_SCR_TYPE_DU:
           start = ypos
           stop = self._dialogtop[1]
           step = -self._step
       else:
           errMsg = ("scrollType not supported (in ToasterBoxWindow.ScrollUp): %s" %
                 self._scrollType)
           raise ValueError(errMsg)

       for i in xrange(start, stop, step):
           if i < self._dialogtop[1]:
             i = self._dialogtop[1]

           windowsize = windowsize + self._step

           # checking the type of the scroll (from up to down or from down to up)
           if self._scrollType == TB_SCR_TYPE_UD:
               dimY = self._dialogtop[1]
           elif self._scrollType == TB_SCR_TYPE_DU:
               dimY = i
           else:
               errMsg = ("scrollType not supported (in ToasterBoxWindow.ScrollUp): %s" %
                     self._scrollType)
               raise ValueError(errMsg)

           self.SetDimensions(self._dialogtop[0], dimY, self.GetSize().GetWidth(),
                              windowsize)

           if self._tbstyle == TB_SIMPLE:
               self.DrawText()

           wx.Usleep(self._sleeptime)
           self.Update()
           self.Refresh()

       self.Update()

       if self._tbstyle == TB_SIMPLE:
           self.DrawText()

#       self.SetFocus()


   def ScrollDown(self):
       """ Scrolls The ToasterBox Down, Which Means Gradually Hiding The ToasterBox. """

       # walk down the Y value
       windowsize = self.GetSize().GetHeight()

       # checking the type of the scroll (from up to down or from down to up)
       if self._scrollType == TB_SCR_TYPE_UD:
           start = self._bottomright.y
           stop = self._dialogtop[1]
           step = -self._step
       elif self._scrollType == TB_SCR_TYPE_DU:
           start = self._dialogtop[1]
           stop = self._bottomright.y
           step = self._step
       else:
           errMsg = ("scrollType not supported (in ToasterBoxWindow.ScrollUp): %s" %
                 self._scrollType)
           raise ValueError(errMsg)

       for i in xrange(start, stop, step):
           if i > self._bottomright.y:
               i = self._bottomright.y

           windowsize = windowsize - self._step

           # checking the type of the scroll (from up to down or from down to up)
           if self._scrollType == TB_SCR_TYPE_UD:
               dimY = self._dialogtop[1]
           elif self._scrollType == TB_SCR_TYPE_DU:
               dimY = i
           else:
               errMsg = ("scrollType not supported (in ToasterBoxWindow.ScrollUp): %s" %
                     self._scrollType)
               raise ValueError(errMsg)

           self.SetDimensions(self._dialogtop[0], dimY,
                              self.GetSize().GetWidth(), windowsize)

           wx.Usleep(self._sleeptime)
           self.Refresh()

       self.Hide()
       if self._parent2:
           self._parent2.Notify()


   def DrawText(self):
       if self._staticbitmap is not None:
           dc = wx.ClientDC(self._staticbitmap)
       else:
           dc = wx.ClientDC(self)
       dc.SetFont(self._textfont)

       if not hasattr(self, "text_coords"):
           self._getTextCoords(dc)

       dc.DrawTextList(*self.text_coords)


   def _getTextCoords(self, dc):
       """ Draw The User Specified Text Using The wx.DC. Use It Only For ToasterBoxes
       Created With TB_SIMPLE Style. """

       # border from sides and top to text (in pixels)
       border = 7
       # how much space between text lines
       textPadding = 2

       pText = self.GetPopupText()

       max_len = len(pText)

       tw, th = self._parent2._popupsize

       if self._windowstyle == TB_CAPTION:
           th = th - 20

       while 1:
           lines = textwrap.wrap(pText, max_len)

           for line in lines:
               w, h = dc.GetTextExtent(line)
               if w > tw - border * 2:
                   max_len -= 1
                   break
           else:
               break

       fh = 0
       for line in lines:
           w, h = dc.GetTextExtent(line)
           fh += h + textPadding
       y = (th - fh) / 2; coords = []

       for line in lines:
           w, h = dc.GetTextExtent(line)
           x = (tw - w) / 2
           coords.append((x, y))
           y += h + textPadding

       self.text_coords = (lines, coords)

########NEW FILE########
__FILENAME__ = ui
# -*- coding: utf-8 -*-

import os
import wx, wx.html
import wx.lib.buttons as buttons
import common_operations as co


class Frame(wx.Frame):
    ID_HOSTS_TEXT = wx.NewId()

    def __init__(self,
                 parent=None, id=wx.ID_ANY, title="SwitchHost!", pos=wx.DefaultPosition,
                 size=wx.DefaultSize, style=wx.DEFAULT_FRAME_STYLE,
                 cls_TaskBarIcon=None
    ):
        wx.Frame.__init__(self, parent, id, title, pos, size, style)

        self.SetIcon(co.GetMondrianIcon())
        self.taskbar_icon = cls_TaskBarIcon(self)
        #        self.Bind(wx.EVT_CLOSE, self.OnClose)
        self.SetSizeHintsSz(wx.DefaultSize, wx.DefaultSize)

        self.m_menubar1 = wx.MenuBar(0)
        self.m_menu1 = wx.Menu()
        self.m_menuItem_new = wx.MenuItem(self.m_menu1, wx.ID_NEW, u"新建(&N)", wx.EmptyString, wx.ITEM_NORMAL)
        self.m_menu1.AppendItem(self.m_menuItem_new)
        self.m_menu1.AppendSeparator()
        self.m_menuItem_exit = wx.MenuItem(self.m_menu1, wx.ID_EXIT, u"退出(&X)", wx.EmptyString, wx.ITEM_NORMAL)
        self.m_menu1.AppendItem(self.m_menuItem_exit)

        self.m_menubar1.Append(self.m_menu1, u"文件(&F)")

        self.m_menu2 = wx.Menu()
        self.m_menuItem_about = wx.MenuItem(self.m_menu2, wx.ID_ABOUT, u"关于(&A)", wx.EmptyString, wx.ITEM_NORMAL)
        self.m_menu2.AppendItem(self.m_menuItem_about)

        self.m_menubar1.Append(self.m_menu2, u"帮助(&H)")

        self.SetMenuBar(self.m_menubar1)

        bSizer1 = wx.BoxSizer(wx.VERTICAL)

        self.m_panel1 = wx.Panel(self, wx.ID_ANY, wx.DefaultPosition, wx.DefaultSize, wx.TAB_TRAVERSAL)
        bSizer4 = wx.BoxSizer(wx.HORIZONTAL)

        bSizer5 = wx.BoxSizer(wx.VERTICAL)

        self.m_list = wx.ListCtrl(self.m_panel1, wx.ID_ANY, wx.DefaultPosition, wx.Size(160, 320),
                                  wx.LC_REPORT)
        self.m_list.Hide()
        bSizer5.Add(self.m_list, 0, wx.ALL | wx.EXPAND, 5)

        self.m_tree = wx.TreeCtrl(self.m_panel1, wx.ID_ANY, wx.DefaultPosition, wx.Size(160, 320))
        self.tree_root = self.m_tree.AddRoot(u"hosts")
        self.tree_local = self.m_tree.AppendItem(self.tree_root, u"本地方案")
        self.tree_online = self.m_tree.AppendItem(self.tree_root, u"在线方案")
        self.m_tree.ExpandAll()
        bSizer5.Add(self.m_tree, 0, wx.ALL | wx.EXPAND, 5)

        bSizer61 = wx.BoxSizer(wx.HORIZONTAL)

        self.m_btn_add = buttons.GenBitmapTextButton(self.m_panel1, wx.ID_ADD, co.GetMondrianBitmap(fn="add"), u"添加")
        bSizer61.Add(self.m_btn_add, 0, wx.ALL, 5)

        self.m_btn_del = buttons.GenBitmapTextButton(self.m_panel1, wx.ID_DELETE, co.GetMondrianBitmap(fn="delete"), u"删除")
        bSizer61.Add(self.m_btn_del, 0, wx.ALL, 5)

        bSizer5.Add(bSizer61, 1, wx.EXPAND, 5)

        bSizer4.Add(bSizer5, 0, wx.EXPAND, 5)

        bSizer6 = wx.BoxSizer(wx.VERTICAL)

        self.m_textCtrl_content = wx.TextCtrl(self.m_panel1, self.ID_HOSTS_TEXT, wx.EmptyString, wx.DefaultPosition,
                                              wx.DefaultSize,
                                              wx.TE_MULTILINE|wx.TE_RICH2|wx.TE_PROCESS_TAB|wx.HSCROLL)
        self.m_textCtrl_content.SetMaxLength(0)
        bSizer6.Add(self.m_textCtrl_content, 1, wx.ALL | wx.EXPAND, 5)

        bSizer7 = wx.BoxSizer(wx.HORIZONTAL)

        self.m_panel3 = wx.Panel(self.m_panel1, wx.ID_ANY, wx.DefaultPosition, wx.DefaultSize, wx.TAB_TRAVERSAL)
        bSizer71 = wx.BoxSizer(wx.HORIZONTAL)

#        self.m_btn_save = buttons.GenBitmapTextButton(self.m_panel3, wx.ID_SAVE, co.GetMondrianBitmap(fn="disk"), u"保存")
#        bSizer71.Add(self.m_btn_save, 0, wx.ALL, 0)

        self.m_panel3.SetSizer(bSizer71)
        self.m_panel3.Layout()
        bSizer71.Fit(self.m_panel3)
        bSizer7.Add(self.m_panel3, 1, wx.EXPAND | wx.ALL, 5)

        self.m_btn_apply = buttons.GenBitmapTextButton(self.m_panel1, wx.ID_APPLY, co.GetMondrianBitmap(fn="accept"), u"应用")
        #        self.m_btn_apply = wx.Button(self.m_panel1, wx.ID_APPLY, u"应用", wx.DefaultPosition, wx.DefaultSize, 0)
        bSizer7.Add(self.m_btn_apply, 0, wx.ALL, 5)

        if cls_TaskBarIcon and os.name == "nt":
            # ubuntu 10.04 下点击这个图标时会报错，图标的菜单无法正常工作
            # ubuntu 11.04 下这个图标总是无法显示
            # 由于跨平台问题，暂时决定只在 windows 下显示快捷的任务栏图标
            # 参见：http://stackoverflow.com/questions/7144756/wx-taskbaricon-on-ubuntu-11-04
            self.m_btn_exit = buttons.GenBitmapTextButton(self.m_panel1, wx.ID_CLOSE, co.GetMondrianBitmap(fn="door"), u"隐藏")
            #            self.m_btn_exit = wx.Button(self.m_panel1, wx.ID_CLOSE, u"隐藏", wx.DefaultPosition, wx.DefaultSize, 0)
            bSizer7.Add(self.m_btn_exit, 0, wx.ALL, 5)

        bSizer6.Add(bSizer7, 0, wx.EXPAND, 5)

        bSizer4.Add(bSizer6, 1, wx.EXPAND, 5)

        self.m_panel1.SetSizer(bSizer4)
        self.m_panel1.Layout()
        bSizer4.Fit(self.m_panel1)
        bSizer1.Add(self.m_panel1, 1, wx.EXPAND | wx.ALL, 0)

        self.SetSizer(bSizer1)
        self.Layout()

        self.Centre(wx.BOTH)

        self.font_bold = wx.SystemSettings.GetFont(wx.SYS_DEFAULT_GUI_FONT)
        self.font_bold.SetWeight(wx.BOLD)
        self.font_normal = wx.SystemSettings.GetFont(wx.SYS_DEFAULT_GUI_FONT)
        self.font_normal.SetWeight(wx.NORMAL)

        self.font_mono = wx.Font(10, wx.ROMAN, wx.NORMAL, wx.NORMAL, faceName="Courier New")


    def alert(self, title, msg):
        dlg = wx.MessageDialog(None, msg, title, wx.OK | wx.ICON_WARNING)
        dlg.ShowModal()
        dlg.Destroy()



class AboutHtml(wx.html.HtmlWindow):

    def __init__(self, parent, id=-1, size=(480, 360)):

        wx.html.HtmlWindow.__init__(self, parent, id, size=size)
        if "gtk2" in wx.PlatformInfo:
            self.SetStandardFonts()


    def OnLinkClicked(self, link):

        wx.LaunchDefaultBrowser(link.GetHref())


class AboutBox(wx.Dialog):
    u"""关于对话框

    参考自：http://wiki.wxpython.org/wxPython%20by%20Example
    """

    def __init__(self, version=None, latest_stable_version=None):

        wx.Dialog.__init__(self, None, -1, u"关于",
                style=wx.DEFAULT_DIALOG_STYLE|wx.THICK_FRAME|wx.TAB_TRAVERSAL
            )

        update_version = u"正在检查新版本..."
        if latest_stable_version:
            cv = self.compareVersion(version, latest_stable_version)
            if cv < 0:
                update_version = u"更新的稳定版 v%s 已经发布！" % latest_stable_version
            else:
                update_version = u"当前版本已是最新版。"
            

        hwin = AboutHtml(self)
        hwin.SetPage(u"""
            <font size="9" color="#44474D"><b>SwitchHost!</b></font><br />
            <font size="3" color="#44474D">%(version)s</font><br /><br />
            <font size="3" color="#909090"><i>%(update_version)s</i></font><br />
            <p>
                本程序用于在多个 hosts 之间快速切换。
            </p>
            <p>
                源码：<a href="https://github.com/oldj/SwitchHosts">https://github.com/oldj/SwitchHosts</a><br />
                作者：<a href="http://oldj.net">oldj</a>
            </p>
        """ % {
            "version": version,
            "update_version": update_version,
        })

        btn = hwin.FindWindowById(wx.ID_OK)
        irep = hwin.GetInternalRepresentation()
        hwin.SetSize((irep.GetWidth() + 25, irep.GetHeight() + 30))
        self.SetClientSize(hwin.GetSize())
        self.CenterOnParent(wx.BOTH)
        self.SetFocus()


    def compareVersion(self, v1, v2):
        u"""比较两个版本的大小
        版本的格式形如：0.1.5.3456

        如果 v1 > v2，则返回 1
        如果 v1 = v2，则返回 0
        如果 v1 < v2，则返回 -1
        """

        a1 = v1.split(".")
        a2 = v2.split(".")

        try:
            a1 = [int(i) for i in a1]
            a2 = [int(i) for i in a2]
        except Exception:
            return 0

        len1 = len(a1)
        len2 = len(a2)
        l = min(len1, len2)
        for i in range(l):
            if a1[i] > a2[i]:
                return 1
            elif a1[i] < a2[i]:
                return -1

        if len1 > len2:
            return 1
        elif len1 < len2:
            return -1
        else:
            return 0


class Dlg_addHosts(wx.Dialog):

    def __init__( self, parent ):
        wx.Dialog.__init__(self, parent, id=wx.ID_ANY, title=wx.EmptyString, pos=wx.DefaultPosition,
            size=wx.Size(400, 200), style=wx.DEFAULT_DIALOG_STYLE)

        self.SetSizeHintsSz(wx.DefaultSize, wx.DefaultSize)

        bSizer9 = wx.BoxSizer(wx.VERTICAL)

        self.m_panel9 = wx.Panel(self, wx.ID_ANY, wx.DefaultPosition, wx.DefaultSize, wx.TAB_TRAVERSAL)
        bSizer10 = wx.BoxSizer(wx.VERTICAL)

        bSizer231 = wx.BoxSizer(wx.HORIZONTAL)

        self.m_radioBtn_local = wx.RadioButton(self.m_panel9, wx.ID_ANY, u"本地方案", wx.DefaultPosition, wx.DefaultSize, 0)
        self.m_radioBtn_local.SetValue(True)
        bSizer231.Add(self.m_radioBtn_local, 0, wx.ALL, 5)

        self.m_radioBtn_online = wx.RadioButton(self.m_panel9, wx.ID_ANY, u"在线方案", wx.DefaultPosition, wx.DefaultSize,
            0)
        bSizer231.Add(self.m_radioBtn_online, 0, wx.ALL, 5)

        bSizer10.Add(bSizer231, 1, wx.EXPAND, 5)

        bSizer111 = wx.BoxSizer(wx.HORIZONTAL)

        self.m_staticText21 = wx.StaticText(self.m_panel9, wx.ID_ANY, u"方案名：", wx.DefaultPosition, wx.Size(60, -1), 0)
        self.m_staticText21.Wrap(-1)
        bSizer111.Add(self.m_staticText21, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 5)

        self.m_textCtrl_title = wx.TextCtrl(self.m_panel9, wx.ID_ANY, wx.EmptyString, wx.DefaultPosition, wx.DefaultSize
            , 0)
        self.m_textCtrl_title.SetMaxLength(32)
        self.m_textCtrl_title.SetToolTipString(u"在这儿输入方案名称。")

        bSizer111.Add(self.m_textCtrl_title, 1, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 5)

        bSizer10.Add(bSizer111, 1, wx.EXPAND, 5)

        bSizer1612 = wx.BoxSizer(wx.HORIZONTAL)

        self.m_staticText512 = wx.StaticText(self.m_panel9, wx.ID_ANY, u"URL：", wx.DefaultPosition, wx.Size(60, -1), 0)
        self.m_staticText512.Wrap(-1)
        bSizer1612.Add(self.m_staticText512, 0, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 5)

        self.m_textCtrl_url = wx.TextCtrl(self.m_panel9, wx.ID_ANY, u"http://", wx.DefaultPosition, wx.DefaultSize, 0)
        self.m_textCtrl_url.SetMaxLength(1024)
        self.m_textCtrl_url.Enable(False)
        self.m_textCtrl_url.SetToolTipString(u"在这儿输入方案的url地址，如：\nhttp://192.168.1.100/hosts/sample.hosts 。")

        bSizer1612.Add(self.m_textCtrl_url, 1, wx.ALL | wx.ALIGN_CENTER_VERTICAL, 5)

        bSizer10.Add(bSizer1612, 1, wx.EXPAND, 5)

        self.m_panel9.SetSizer(bSizer10)
        self.m_panel9.Layout()
        bSizer10.Fit(self.m_panel9)
        bSizer9.Add(self.m_panel9, 2, wx.EXPAND | wx.ALL, 5)

        self.m_staticline211 = wx.StaticLine(self, wx.ID_ANY, wx.DefaultPosition, wx.DefaultSize, wx.LI_HORIZONTAL)
        bSizer9.Add(self.m_staticline211, 0, wx.EXPAND | wx.ALL, 5)

        m_sdbSizer1 = wx.StdDialogButtonSizer()
        self.m_sdbSizer1OK = wx.Button(self, wx.ID_OK)
        m_sdbSizer1.AddButton(self.m_sdbSizer1OK)
        self.m_sdbSizer1Cancel = wx.Button(self, wx.ID_CANCEL)
        m_sdbSizer1.AddButton(self.m_sdbSizer1Cancel)
        m_sdbSizer1.Realize();
        bSizer9.Add(m_sdbSizer1, 1, wx.EXPAND, 5)

        self.SetSizer(bSizer9)
        self.Layout()

        self.Centre(wx.BOTH)

        self.__binds()


    def __del__( self ):
        pass


    def __binds(self):

        self.Bind(wx.EVT_RADIOBUTTON, self.switchToLocal, self.m_radioBtn_local)
        self.Bind(wx.EVT_RADIOBUTTON, self.switchToOnline, self.m_radioBtn_online)


    def switchToLocal(self, event):

#        print("local!")
        self.m_textCtrl_url.Enabled = False


    def switchToOnline(self, event):

#        print("online!")
        self.m_textCtrl_url.Enabled = True


########NEW FILE########
__FILENAME__ = SwitchHosts
# -*- coding: utf-8 -*-

u"""
本程序用于快速切换 hosts 文件

@author: oldj
@blog: http://oldj.net
@email: oldj.wu@gmail.com

"""

import os
import sys
import glob
import wx
import libs.common_operations as co
import libs.ui as ui
from libs.cls_Hosts import Hosts, DEFAULT_HOSTS_FN

VERSION = "0.2.0.1763"
SELECTED_FLAG = u"√"

class TaskBarIcon(wx.TaskBarIcon):
    ID_About = wx.NewId()
    ID_Exit = wx.NewId()
    ID_MainFrame = wx.NewId()

    def __init__(self, frame):
        wx.TaskBarIcon.__init__(self)
        #        super(wx.TaskBarIcon, self).__init__()
        self.frame = frame
        self.SetIcon(co.GetMondrianIcon(), "SwitchHosts! %s" % VERSION)
        self.Bind(wx.EVT_TASKBAR_LEFT_DCLICK, self.OnTaskBarLeftDClick)
        self.Bind(wx.EVT_MENU, self.frame.OnAbout, id=self.ID_About)
        self.Bind(wx.EVT_MENU, self.OnExit, id=self.ID_Exit)
        self.Bind(wx.EVT_MENU, self.OnMainFrame, id=self.ID_MainFrame)

        self.current_hosts = None

        self.font_bold = wx.SystemSettings.GetFont(wx.SYS_DEFAULT_GUI_FONT)
        self.font_bold.SetWeight(wx.BOLD)


    def OnTaskBarLeftDClick(self, event):
        if self.frame.IsIconized():
            self.frame.Iconize(False)
        if not self.frame.IsShown():
            self.frame.Show(True)
        self.frame.Raise()


    def OnExit(self, event):
        self.frame.Destroy()
        self.Destroy()
        sys.exit()


    def OnMainFrame(self, event):
        u"""显示主面板"""
        if not self.frame.IsShown():
            self.frame.Show(True)
        self.frame.Raise()

    # override
    def CreatePopupMenu(self):
        self.hosts = {}

        hosts_list = listLocalHosts()
        menu = wx.Menu()
        menu.Append(self.ID_MainFrame, u"SwitchHosts!")
        menu.AppendSeparator()

        for fn in hosts_list:
            oh = self.frame.getOHostsFromFn(fn)
            if oh:
                self.addHosts(menu, oh)

        menu.AppendSeparator()
        menu.Append(self.ID_About, "About")
        menu.Append(self.ID_Exit, "Exit")
        return menu


    def addHosts(self, menu, ohost):
        u"""在菜单项中添加一个 hosts"""

        title = ohost.getTitle()

        item_id = wx.NewId()
        mitem = wx.MenuItem(menu, item_id, title, kind=wx.ITEM_RADIO)
        mitem.SetBitmap(co.GetMondrianBitmap(ohost.icon_idx))
        menu.AppendItem(mitem)

        menu.Check(item_id, self.current_hosts == ohost.path)
        if self.current_hosts == ohost.path:
            mitem.SetFont(self.font_bold)
        self.hosts[item_id] = title

        self.Bind(wx.EVT_MENU, self.switchHost, id=item_id)


    def switchHost(self, event):
        hosts_id = event.GetId()
        title = self.hosts[hosts_id]

        oh = self.frame.getOHostsFromTitle(title)
        if oh:
            co.switchHost(self, oh.path)
            self.frame.updateListCtrl()


class Frame(ui.Frame):

    ID_RENAME = wx.NewId()

    def __init__(
        self, parent=None, id=wx.ID_ANY, title="SwitchHosts! %s" % VERSION, pos=wx.DefaultPosition,
        size=wx.DefaultSize, style=wx.DEFAULT_FRAME_STYLE,
        sys_hosts_title=None
    ):
        ui.Frame.__init__(self, parent, id, title, pos, size, style, cls_TaskBarIcon=TaskBarIcon)

        self.Bind(wx.EVT_CLOSE, self.OnClose)
        self.init2(sys_hosts_title)


    def init2(self, sys_hosts_title):

        self.Bind(wx.EVT_MENU, self.newHosts, id=wx.ID_NEW)
        self.Bind(wx.EVT_MENU, self.OnExit, id=wx.ID_EXIT)
        self.Bind(wx.EVT_MENU, self.OnAbout, id=wx.ID_ABOUT)
        self.Bind(wx.EVT_BUTTON, self.OnHide, id=wx.ID_CLOSE)
        self.Bind(wx.EVT_BUTTON, self.applyHost, id=wx.ID_APPLY)
        self.Bind(wx.EVT_TEXT, self.hostsContentChange, id=self.ID_HOSTS_TEXT)

        self.Bind(wx.EVT_BUTTON, self.newHosts, id=wx.ID_ADD)
        self.Bind(wx.EVT_BUTTON, self.deleteHosts, id=wx.ID_DELETE)

        hosts_cols = (
            (u"hosts", 130),
            (u"", 20),
            )
        for col, (txt, width) in enumerate(hosts_cols):
            self.m_list.InsertColumn(col, txt)
            self.m_list.SetColumnWidth(col, width)
        self.current_selected_hosts_index = -1
        self.current_selected_hosts_fn = None
        self.current_use_hosts_index = -1
        self.current_max_hosts_index = -1
        self.latest_stable_version = None

        self.updateHostsList(sys_hosts_title)

        self.hosts_item_menu = wx.Menu()
        self.hosts_item_menu.Append(wx.ID_APPLY, u"切换到当前hosts")
#        self.hosts_item_menu.Append(wx.ID_EDIT, u"编辑")
        self.hosts_item_menu.Append(self.ID_RENAME, u"重命名")
        self.hosts_item_menu.AppendMenu(-1, u"图标", self.mkSubIconMenu())

        self.hosts_item_menu.AppendSeparator()
        self.hosts_item_menu.Append(wx.ID_DELETE, u"删除")

        self.m_btn_apply.Disable()

        co.checkLatestStableVersion(self)

        self.Bind(wx.EVT_MENU, self.menuApplyHost, id=wx.ID_APPLY)
        self.Bind(wx.EVT_MENU, self.deleteHosts, id=wx.ID_DELETE)
        self.Bind(wx.EVT_MENU, self.renameHosts, id=self.ID_RENAME)

        self.Bind(wx.EVT_TREE_ITEM_RIGHT_CLICK, self.OnHostsItemRClick, self.m_tree)
        self.Bind(wx.EVT_TREE_ITEM_MENU, self.OnHostsItemBeSelected, self.m_tree) # todo selected 方法？
        self.Bind(wx.EVT_TREE_ITEM_ACTIVATED, self.applyHost, self.m_tree)


    def setLatestStableVersion(self, version):

        self.latest_stable_version = version
#        print(version)


    def mkSubIconMenu(self):
        u"""生成图标子菜单"""

        menu = wx.Menu()

        def _f(i):
            return lambda e: self.setHostIcon(e, i)

        icons_length = len(co.ICONS)
        for i in range(icons_length):
            item_id = wx.NewId()
            mitem = wx.MenuItem(menu, item_id, u"图标#%d" % (i + 1))
            mitem.SetBitmap(co.GetMondrianBitmap(i))
            menu.AppendItem(mitem)

            self.Bind(wx.EVT_MENU, _f(i), id=item_id)

        return menu


    def setHostIcon(self, event=None, i=0):

        index = self.current_selected_hosts_index
        ohosts = self.hosts_objects[index]
        ohosts.setIcon(i)
        self.m_list.SetItemImage(index, ohosts.icon_idx, ohosts.icon_idx)

        ch = self.taskbar_icon.current_hosts
        if ch == ohosts.path or (not ch and DEFAULT_HOSTS_FN == ohosts.fn):
            # 如果当前设置图片的 hosts 正是正在使用的 hosts，则
            
            self.SetIcon(co.GetMondrianIcon(i))
            self.taskbar_icon.SetIcon(co.GetMondrianIcon(i), u"当前 hosts 方案：%s" % ohosts.getTitle())


    def updateHostsList(self, selected_title=None):
        u"""更新 hosts 列表"""

        hosts_list = listLocalHosts()
#        hosts_list.insert(0, co.getSysHostsPath())
        hosts_list = [list(os.path.split(fn)) + [fn] for fn in hosts_list]
        self.hosts_lists = hosts_list
        self.hosts_objects = []

        self.m_list.DeleteAllItems()
        ch = self.taskbar_icon.current_hosts
        c_idx = -1

        il = wx.ImageList(16, 16, True)
        icons_count = len(co.ICONS)
        for i in xrange(icons_count):
            il.Add(co.GetMondrianBitmap(i))
        self.m_list.AssignImageList(il, wx.IMAGE_LIST_SMALL)

        for idx, (folder, fn, fn2) in enumerate(hosts_list):

            icon_idx = idx if idx < icons_count else icons_count - 1
            ohosts = Hosts(idx, fn2, icon_idx)
            self.hosts_objects.append(ohosts)

            i, t, t2 = fn.partition(".")
            if i.isdigit():
                i = int(i)
                if i > self.current_max_hosts_index:
                    self.current_max_hosts_index = i

            c = ""
            index = self.m_list.InsertStringItem(sys.maxint, ohosts.getTitle())

            # 如果指定了当前选中的 hosts
            if ohosts.getTitle() == selected_title:
                ch = self.taskbar_icon.current_hosts = fn2
                self.SetIcon(co.GetMondrianIcon(ohosts.icon_idx))
                self.taskbar_icon.SetIcon(co.GetMondrianIcon(ohosts.icon_idx), u"当前 hosts 方案：%s" % ohosts.getTitle())
                self.m_list.SetItemFont(idx, self.font_bold)


            if (ch and ch == fn2) or \
                (not selected_title and not ch and co.decode(fn) == DEFAULT_HOSTS_FN):
                c = SELECTED_FLAG
            if c:
                c_idx = index
            self.m_list.SetStringItem(index, 1, c)
            self.m_list.SetItemImage(index, ohosts.icon_idx, ohosts.icon_idx)


        if self.current_selected_hosts_index >= 0:
            c_idx = self.current_selected_hosts_index

        while c_idx >= len(self.hosts_objects) and c_idx > 0:
            c_idx -= 1

        ohosts = self.hosts_objects[c_idx]

        self.m_list.Select(c_idx)
        self.current_selected_hosts_index = c_idx
        self.current_selected_hosts_fn = self.hosts_objects[c_idx].path

        self.m_textCtrl_content.Value = ohosts.getContent()


    def hostsContentChange(self, event):

        c = self.m_textCtrl_content.Value.rstrip()
        ohosts = self.getOHostsFromFn()
        old_c = ohosts.getContent()
        if ohosts and c != old_c:
            # 内容改变
#            print ohosts.getTitle()
#            print("%s, changed!" % self.current_selected_hosts_fn)
            self.saveCurrentHost(ohosts, c)
            self.textStyle(old_c)
        else:
            # 新切换
            self.textStyle()

        self.m_btn_apply.Enable()


    def menuApplyHost(self, event):

        self.applyHost(event)


    def mkNewHostsPath(self):

        global g_local_hosts_dir

        self.current_max_hosts_index += 1
        return os.path.join(g_local_hosts_dir, "%d.hosts" % self.current_max_hosts_index)


    def newHosts_test(self):

        print(123)
        dlg = ui.Dlg_addHosts(None)
        if dlg.ShowModal() == wx.ID_OK:
            print("OK!")

            print(dlg.m_radioBtn_local.Value)
            print(dlg.m_textCtrl_title.Value)
            print(dlg.m_textCtrl_url.Value)
        else:
            print("Cancel!")



    def newHosts(self, event=None, default=""):
        u"""新建一个 hosts"""

        global g_local_hosts_dir

        repeat = False
        title = default

        self.newHosts_test()
        return

        dlg = wx.TextEntryDialog(None, u"新建 hosts", u"输入 hosts 名：", title,
                style=wx.OK | wx.CANCEL
            )
        if dlg.ShowModal() == wx.ID_OK:
            title = dlg.GetValue().strip()

            if title:

                oh = self.getOHostsFromTitle(title)
                if oh:

                    repeat = True
                    self.alert(u"命名失败！", u"名为 '%s' 的 hosts 已经存在了！" % title)

                else:
                    # 保存新文件

                    path = self.mkNewHostsPath()
                    c = u"# %s" % title
                    oh = Hosts(path=path)
                    oh.setTitle(title)
                    oh.setContent(c)
                    self.updateHostsList()

        dlg.Destroy()

        if repeat:
            self.newHosts(event, default=title)


    def renameHosts(self, event):
        u"""重命名一个 hosts"""

        ohosts = self.hosts_objects[self.current_selected_hosts_index]
        if ohosts.fn == DEFAULT_HOSTS_FN:
            self.alert(u"不可操作", u"默认 hosts 不可重命名！")
            return

        old_title = ohosts.getTitle()

        repeat = False

        dlg = wx.TextEntryDialog(None, u"重命名 hosts", u"输入新的 hosts 名：", old_title,
                style=wx.OK | wx.CANCEL
            )
        if dlg.ShowModal() == wx.ID_OK:
            # 改名
            new_title = dlg.GetValue().strip()

            if new_title and new_title != old_title:

                oh2 = self.getOHostsFromTitle(new_title)

                if oh2:

                    repeat = True
                    self.alert(u"重命名失败！", u"'%s' 已存在，请先将它删除！" % new_title)

                else:

                    ohosts.setTitle(new_title)

                    if self.taskbar_icon.current_hosts == ohosts.path:
                        self.applyHost()
                    self.updateHostsList()

        dlg.Destroy()

        if repeat:
            self.renameHosts(event)


    def deleteHosts(self, event):
        u"""删除 hosts"""

        fn = DEFAULT_HOSTS_FN.encode()
        if self.current_selected_hosts_fn:
            folder, fn = os.path.split(self.current_selected_hosts_fn)
#            fn = co.decode(fn)
        ohosts = self.getOHostsFromFn(fn)

#        print(self.current_selected_hosts_fn, self.taskbar_icon.current_hosts)

        if not self.current_selected_hosts_fn or \
            self.current_selected_hosts_fn == self.taskbar_icon.current_hosts or \
            (self.taskbar_icon.current_hosts is None and fn == DEFAULT_HOSTS_FN):
            self.alert(u"不可删除", u"当前 hosts 正在使用中，不可删除！")
            return

        dlg = wx.MessageDialog(None, u"确定要删除 hosts '%s'？" % ohosts.getTitle(), u"删除 hosts",
                wx.YES_NO | wx.ICON_QUESTION
            )
        ret_code = dlg.ShowModal()
        if ret_code == wx.ID_YES:
            # 删除当前 hosts
            try:
                os.remove(ohosts.path)
            except Exception:
                pass

            self.updateHostsList()

        dlg.Destroy()


    def saveCurrentHost(self, ohosts=None, content=None):
        u"""保存当前 hosts"""

        c = content or self.m_textCtrl_content.Value.rstrip()
        ohosts = ohosts or self.getOHostsFromFn()
        if ohosts:
            ohosts.setContent(c)
            ohosts.save()


    def applyHost(self, event=None, ohosts=None):
        u"""应用某个 hosts"""

        # 保存当前 hosts 的内容
        self.saveCurrentHost()

        # 切换 hosts
        co.switchHost(self.taskbar_icon, self.current_selected_hosts_fn)
        self.updateListCtrl()

        self.m_btn_apply.Disable()


    def getOHostsFromTitle(self, title):

        for oh in self.hosts_objects:
            if oh.getTitle() == title:
                return oh

        return None


    def getOHostsFromFn(self, fn=None):
        u"""从 hosts 的文件名取得它的 id"""

        if not fn:
            fn = self.current_selected_hosts_fn or DEFAULT_HOSTS_FN.encode()

        fn = co.decode(fn)

        for oh in self.hosts_objects:
            if oh.fn == fn or oh.dc_path == fn:
                return oh

        return None


    def updateListCtrl(self):

        for idx in range(len(self.hosts_lists)):
            c = ""
            font = self.font_normal
            if self.hosts_lists[idx][2] == self.taskbar_icon.current_hosts:
                c = SELECTED_FLAG
                font = self.font_bold
            self.m_list.SetStringItem(idx, 1, c)
            self.m_list.SetItemFont(idx, font)



    def OnHostsItemBeSelected(self, event):

        item = event.GetItem()
        host_title = self.m_tree.GetItemText(item)
        idx = event.GetIndex()
        fn = self.hosts_lists[idx][2]
        ohosts = self.hosts_objects[idx]
#        c = open(fn, "rb").read() if os.path.isfile(fn) else ""

        self.current_selected_hosts_index = idx
        self.current_selected_hosts_fn = fn
        self.m_textCtrl_content.Value = ohosts.getContent()

        self.m_btn_apply.Enable()


    def OnHostsItemRClick(self, event):
        u""""""

        item = event.GetItem()
        host_title = self.m_tree.GetItemText(item)
#        idx = event.GetIndex()
#        fn = self.hosts_lists[idx][2]
        fn = self.getOHostsFromTitle(host_title)
        self.current_selected_hosts_index = idx
        self.current_selected_hosts_fn = fn

        self.m_list.PopupMenu(self.hosts_item_menu, event.GetPosition())


    def OnAbout(self, event):

        dlg = ui.AboutBox(version=VERSION, latest_stable_version=self.latest_stable_version)
        dlg.ShowModal()
        dlg.Destroy()



    def editHost(self, event):
        u"""编辑一个 hosts 文件"""

        print(1)


    def textStyle(self, old_content=None):
        u"""更新文本区的样式"""

        from libs.highLight import highLight

        self.m_textCtrl_content.SetFont(self.font_mono)
        highLight(self.m_textCtrl_content, old_content=old_content)


    def OnHide(self, event):
        self.Hide()


    def OnIconfiy(self, event):
        wx.MessageBox("Frame has been iconized!", "Prompt")
        event.Skip()

    def OnExit(self, event):
    #        self.taskbar_icon.Destroy()
    #        self.Destroy()
    #        event.Skip()
        self.taskbar_icon.OnExit(event)

    def OnClose(self, event):
        self.Hide()
        return False


def listLocalHosts():
    u"""列出指定目录下的 host 文件列表"""

    global g_local_hosts_dir

    fns = [fn for fn in glob.glob(os.path.join(g_local_hosts_dir, "*.hosts")) if\
           os.path.isfile(fn) and not fn.startswith(".")\
           and not fn.startswith("_")
    ]

    return fns


def getSysHostsTitle():

    global g_local_hosts_dir

    sys_hosts = co.getSysHostsPath()
    path = os.path.join(g_local_hosts_dir, DEFAULT_HOSTS_FN)

    ohosts_sys = Hosts(path=sys_hosts)
    sys_hosts_title = ohosts_sys.getTitle()
    is_title_valid = False

    fns = listLocalHosts()
    for fn in fns:
        fn2 = os.path.split(fn)[1]
        i, t, t2 = fn2.partition(".")
        if not i.isdigit():
            continue

        ohosts = Hosts(path=fn)
        if ohosts.getTitle() == sys_hosts_title:
            is_title_valid = True
            break

    if not is_title_valid:
        open(path, "wb").write(open(sys_hosts, "rb").read())
#    else:
#        if os.path.isfile(path):
#            os.remove(path)

    return sys_hosts_title if is_title_valid else None


def init():
    global g_local_hosts_dir

    base_dir = os.getcwd()
    g_local_hosts_dir = os.path.join(base_dir, "hosts")
    if not os.path.isdir(g_local_hosts_dir):
        os.makedirs(g_local_hosts_dir)

    return getSysHostsTitle()


def main():
    sys_hosts_title = init()
    app = wx.App()
#    app = wx.PySimpleApp()
    frame = Frame(size=(640, 480), sys_hosts_title=sys_hosts_title)
    frame.Centre()
    frame.Show()
    app.MainLoop()


if __name__ == "__main__":
    main()



########NEW FILE########
__FILENAME__ = mkicon
# -*- coding: utf-8 -*-

def main():

    icons = []

    for i in range(7):
        fn = "icon_%d.ico" % i
        c = open(fn, "rb").read()
        icons.append(c)

    open("icons.py", "w").write(repr(icons))


if __name__ == "__main__":

    main()



########NEW FILE########
__FILENAME__ = mkicon2
# -*- coding: utf-8 -*-

import glob

def main():

    icons2 = {}

    for fn in glob.glob("*.png"):
        if fn.startswith("icon_"):
            continue

        c = open(fn, "rb").read()
        icons2[fn.partition(".")[0]] = c

    open("icons.py", "w").write(repr(icons2))


if __name__ == "__main__":

    main()



########NEW FILE########
