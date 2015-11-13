__FILENAME__ = bddown_cli
#!/usr/bin/env python2
# coding=utf-8

import sys

import bddown_help
from util import bd_help, usage
from command.download import download
from command.show import show
from command.login import login
from command.config import config
from command.export import export


def execute_command(args=sys.argv[1:]):
    if not args:
        usage()
        sys.exit(1)

    command = args[0]
    if command.startswith('-'):
        if command in ('-h', '--help'):
            usage(bddown_help.show_help())
        elif command in ('-V', '-v', '--version'):
            print 'V1.54'
        else:
            usage()
            sys.exit(1)
        sys.exit(0)

    commands = {
        'help':         bd_help,
        'login':        login,
        'download':     download,
        'd':            download,   # alias download
        'export':       export,
        'show':         show,
        'config':       config
    }

    if command not in commands.keys():
        usage()
        sys.exit(1)
    elif '-h' in args or '--help' in args:
        bd_help([command])
        sys.exit(0)
    else:
        commands[command](args[1:])


if __name__ == '__main__':
    execute_command()

########NEW FILE########
__FILENAME__ = bddown_core
#!/usr/bin/env python2
# coding=utf-8

import re
import os
import json
import logging
import urllib2
import cookielib
from time import time

from util import convert_none
from command.config import global_config


class FileInfo(object):
    """Get necessary info from javascript code by regular expression

    Attributes:
        secret (str): the password to enter secret share page.
        bdstoken (str): token from login cookies.
        filename (list): the filenames of download files.
        fs_id (list): download files' ids.
        uk (str): user number of the share file.
        shareid (str): id of the share file.
        timestamp (str): unix timestamp of get download page.
        sign (str): relative to timestamp. Server will check sign and timestamp when we try to get download link.
    """

    def __init__(self, js):
        self.js = js
        self.info = {}
        self.filenames = []
        self.bdstoken = ""
        self.fid_list = []
        self.uk = ""
        self.shareid = ""
        self.timestamp = ""
        self.sign = ""
        self._get_info()
        self._parse_json()

    @staticmethod
    def _str2dict(s):
        return dict(
            [i.split('=', 1) for i in s.split(';') if ('File' in i or 'disk' in i) and len(i.split('=', 1)) == 2])

    def _get_info(self):
        self.info = self._str2dict(self.js[0])
        bdstoken_tmp = self._str2dict(self.js[1])
        self.info['FileUtils.bdstoken'] = bdstoken_tmp.get('FileUtils.bdstoken')
        self.shareid = self.info.get('FileUtils.share_id').strip('"')
        self.uk = self.info.get('FileUtils.share_uk').strip('"').strip('"')
        self.timestamp = self.info.get('FileUtils.share_timestamp').strip('"')
        self.sign = self.info.get('FileUtils.share_sign').strip('"')
        # self.fs_id = info.get('disk.util.ViewShareUtils.fsId').strip('"')
        self.bdstoken = self.info.get('disk.util.ViewShareUtils.bdstoken') or self.info.get(
            'FileUtils.bdstoken')
        self.bdstoken = self.bdstoken.strip('"')
        if self.bdstoken == "null":
            self.bdstoken = None
            # try:
            #     self.bdstoken = info.get('disk.util.ViewShareUtils.bdstoken').strip('"')
            # except AttributeError:
            #     self.bdstoken = info.get('FileUtils.bdstoken').strip('"')

            # TODO: md5
            # self.md5 = info.get('disk.util.ViewShareUtils.file_md5').strip('"')

    def _parse_json(self):
        # single file
        if self.js[0].startswith("var"):
            # js2 = self.js[0]
            # get json
            # [1:-1] can remove double quote
            d = [self.info.get('disk.util.ViewShareUtils.viewShareData').replace('\\\\', '\\').decode(
                "unicode_escape").replace('\\', '')[1:-1]]
        # files
        else:
            js2 = self.js[1]
            pattern = re.compile("[{]\\\\[^}]+[}]+")
            d = re.findall(pattern, js2)
            # escape
            d = [i.replace('\\\\', '\\').decode('unicode_escape').replace('\\', '') for i in d]
        d = map(json.loads, d)
        for i in d:
            # if wrong json
            if i.get('fs_id') is None:
                continue
            if i.get('isdir') == '1':
                seq = self._get_folder(i.get('path'))
                for k, j in seq:
                    self.filenames.append(k)
                    self.fid_list.append(j)
                continue
            self.fid_list.append(i.get('fs_id'))
            self.filenames.append(i.get('server_filename').encode('utf-8'))

    def _get_folder(self, path):
        # 13 digit unix timestamp
        seq = []
        t1 = int(time() * 1000)
        t2 = t1 + 6
        # interval
        tt = 1.03
        url = "http://pan.baidu.com/share/list?channel=chunlei&clienttype=0&web=1&num=100&t=%(t1)d" \
              "&page=1&dir=%(path)s&t=%(tt)d&uk=%(uk)s&shareid=%(shareid)s&order=time&desc=1" \
              "&_=%(t2)d&bdstoken=%(bdstoken)s" % {
                  't1': t1,
                  'path': path,
                  'tt': tt,
                  'uk': self.uk,
                  'shareid': self.shareid,
                  't2': t2,
                  'bdstoken': self.bdstoken
              }
        html = Pan.opener.open(url)
        j = json.load(html)
        for i in j.get('list', []):
            seq.append((i.get('server_filename'), i.get('fs_id')))
        return seq


class Pan(object):
    cookjar = cookielib.LWPCookieJar()
    if os.access(global_config.cookies, os.F_OK):
        cookjar.load(global_config.cookies)
    opener = urllib2.build_opener(
        urllib2.HTTPCookieProcessor(cookjar)
    )
    opener.addheaders = [
        ('User-Agent', 'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:26.0) Gecko/20100101 Firefox/26.0')
    ]

    def __init__(self, bdlink, secret=""):
        self.secret = secret
        self.bdlink = bdlink
        file_info = FileInfo(self._get_js())
        self.filenames = file_info.filenames
        self.bdstoken = file_info.bdstoken
        self.fid_list = file_info.fid_list
        self.uk = file_info.uk
        self.shareid = file_info.shareid
        self.timestamp = file_info.timestamp
        self.sign = file_info.sign

    def _get_js(self):
        """Get javascript code in html like '<script type="javascript">/*<![CDATA[*/  sth  /*]]>*/</script>"""
        req = self.opener.open(self.bdlink)
        if 'init' in req.url:
            self._verify_passwd(req.url)
            req = self.opener.open(self.bdlink)
        data = req.read()
        js_pattern = re.compile('<script\stype="text/javascript">/\*<!\[CDATA\[\*/(.+?)/\*\]\]>\*/</script>', re.DOTALL)
        js = re.findall(js_pattern, data)
        return js

    def _verify_passwd(self, url):
        if self.secret:
            pwd = self.secret
        else:
            pwd = raw_input("请输入提取密码\n")
        data = "pwd=%s&vcode=" % pwd
        url = "%s&t=%d&" % (url.replace('init', 'verify'), int(time()))
        logging.debug(url)
        req = self.opener.open(url, data=data)
        mesg = req.read()
        logging.debug(mesg)
        logging.debug(req.info())
        errno = json.loads(mesg).get('errno')
        if errno == -63:
            raise UnknownError
        elif errno == -9:
            raise VerificationError("提取密码错误\n")

    def _get_json(self, fs_id, input_code=None, vcode=None):
        """Post fs_id to get json of real download links"""
        url = 'http://pan.baidu.com/share/download?channel=chunlei&clienttype=0&web=1' \
              '&uk=%s&shareid=%s&timestamp=%s&sign=%s%s%s%s' \
              '&channel=chunlei&clienttype=0&web=1' % \
              (self.uk, self.shareid, self.timestamp, self.sign,
               convert_none('&bdstoken=', self.bdstoken),
               convert_none('&input=', input_code),
               convert_none('&vcode=', vcode))
        logging.debug(url)
        post_data = 'fid_list=["%s"]' % fs_id
        logging.debug(post_data)
        req = self.opener.open(url, post_data)
        json_data = json.load(req)
        return json_data

    @staticmethod
    def save(img):
        data = urllib2.urlopen(img).read()
        with open(os.path.dirname(os.path.abspath(__file__)) + '/vcode.jpg', mode='wb') as fp:
            fp.write(data)
        print "验证码已经保存至", os.path.dirname(os.path.abspath(__file__))

    # TODO: Cacahe support (decorator)
    # TODO: Save download status
    def _get_link(self, fs_id):
        """Get real download link by fs_id( file's id)"""
        data = self._get_json(fs_id)
        logging.debug(data)
        if not data.get('errno'):
            return data.get('dlink').encode('utf-8')
        elif data.get('errno') == -19:
            vcode = data.get('vcode')
            img = data.get('img')
            self.save(img)
            input_code = raw_input("请输入看到的验证码\n")
            data = self._get_json(fs_id, vcode=vcode, input_code=input_code)
            if not data.get('errno'):
                return data.get('dlink').encode('utf-8')
            else:
                raise VerificationError("验证码错误\n")
        else:
            raise UnknownError

    @property
    def info(self):
        fs_id = self.fid_list.pop()
        filename = self.filenames.pop()
        link = self._get_link(fs_id)
        return link, filename, len(self.fid_list)


class Album(object):
    def __init__(self, album_id, uk):
        self._album_id = album_id
        self._uk = uk
        self._limit = 100
        self._filename = []
        self._links = []
        self._get_info()

    def __len__(self):
        return len(self._links)

    def _get_info(self):
        url = "http://pan.baidu.com/pcloud/album/listfile?album_id={album_id}&query_uk={uk}&start=0&limit={limit}" \
              "&channel=chunlei&clienttype=0&web=1".format(album_id=self._album_id, uk=self._uk, limit=self._limit)
        res = Pan.opener.open(url)
        data = json.load(res)
        if not data.get('errno'):
            filelist = data.get('list')
            for i in filelist:
                # if is dir, ignore it
                if i.get('isdir'):
                    continue
                else:
                    self._filename.append(i.get('server_filename'))
                    self._links.append(i.get('dlink'))
                    # TODO: md5
                    # self._md5.append(i.get('md5'))
                    # size
                    # self._size.append(i.get('size'))
        else:
            raise UnknownError

    @property
    def info(self):
        filename = self._filename.pop()
        link = self._links.pop()
        return link, filename, len(self)


class VerificationError(Exception):
    pass


class GetFilenameError(Exception):
    pass


class UnknownError(Exception):
    pass


if __name__ == '__main__':
    pass

########NEW FILE########
__FILENAME__ = bddown_help
#!/usr/bin/env python2
# coding=utf-8

basic_command = [
    ('help',        'Show this help'),
    ('login',       'Login using Baidu account'),
    ('download',    'Download file from the Baidu netdisk link'),
    ('show',        'Show the Baidu netdisk real link and filename'),
    ('export',      'export link to aria2 json-rpc'),
    ('config',      'save configuration to file')
]

extended_usage = ''


def join_commands(command):
    n = max(len(x[0]) for x in command)
    n = max(n, 10)
    return ''.join(' %%-%ds %%s\n' % n % (h, k) for (h, k) in basic_command)

basic_usage = '''python bddown_cli.py <command> [<args>]

Basic commands:
''' + join_commands(basic_command)


def usage():
    return basic_usage + '''
Use 'python bddown_cli.py help' for details
Use 'python bddown_cli.py help <command>' for more information on a specific command.
Check https://github.com/banbanchs/pan-baidu-download for details'''


def show_help():
    return ''' Python script for Baidu netdisk
Basic usage:
    ''' + basic_usage + extended_usage + '\n'

login = '''python bddown_cli.py login [username] [password]

Baidu login.

Example:
  python bddown_cli.py login XXXXX 123456
  python bddown_cli.py login xxx@qq.com 123456
'''

download = '''python bddown_cli.py download [options] [Baidupan-url]...

Download file from the Baidu netdisk link

Options:
    --limit=[speed]             Max download speed limit.
    --dir=[dir]                 Download task to dir.
    --secret=[string]           Retrieval password'''

show = '''python bddown_cli.py show [Baidupan-url]...

Show the real download link and filename

Example:
 python bddown_cli.py show http://pan.baidu.com/s/15lliC
'''

export = '''python bddown_cli.py export [Baidupan-url]...

export link to aria2 json-rpc

Example:
  python bddown_cli.py show http://pan.baidu.com/s/15lliC
'''

config = '''python bddown_cli.py config key [value]

save configuration to config.ini

Examples:
 python bddown_cli.py config
 python bddown_cli.py config username XXXXX
 python bddown_cli.py config password 123456
 python bddown_cli.py config limit 500k
 python bddown_cli.py config dir /home/john/Downloads
 python bddown_cli.py config delete dir
'''

help_help = '''Get helps:
 python bddown_cli.py help help
 python bddown_cli.py help download
 python bddown_cli.py help show
 python bddown_cli.py help <command>'''

help = help_help

########NEW FILE########
__FILENAME__ = config
#!/usr/bin/env python2
# coding=utf-8

import os
import sys
import ConfigParser

command = ('limit', 'dir', 'cookies', 'username', 'password', 'jsonrpc')


class Config(object):
    def __init__(self):
        # get config.ini path
        self._path = os.path.join(os.path.join(os.path.dirname(os.path.abspath(__file__)), os.pardir), 'config.ini')
        if not os.path.exists(self._path):
            raise IOError("No such file: config.ini")
        self._configfile = ConfigParser.ConfigParser(allow_no_value=True)
        self._configfile.read(self._path)
        self.config = dict(self._configfile.items('option'))

    def __getattr__(self, item):
        # expand '~/Downloads' to '/home/XXX/Downloads'
        if item in ('dir', 'cookies'):
            return os.path.expanduser(self.config.get(item))
        return self.config.get(item)

    def get(self, k, v=None):
        return self.config.get(k, v)

    def put(self, k, v):
        # if k in ('dir', 'cookies'):
        #     v = os.path.expanduser(v)
        self.config[k] = v
        self._save_config(k, v)

    def delete(self, k):
        if k in self.config.iterkeys():
            self.config[k] = ""
            self._save_config(k)

    def _save_config(self, k, v=""):
        self._configfile.set('option', k, v)
        with open(name=self._path, mode='w') as fp:
            self._configfile.write(fp)

global_config = Config()


def config(configuration):
    if len(configuration) == 0:
        for k, v in global_config.config.iteritems():
            print '%s -> %s' % (k, v)
    elif configuration[0] == 'delete':
        global_config.delete(configuration[1])
        print 'Successfully delete %s' % configuration[1]
    elif configuration[0] in command:
        try:
            global_config.put(configuration[0], configuration[1])
        except IndexError:
            # avoid like this case
            # $ pan config limit
            raise IndexError('Please input value of %s!' % configuration[0])
        print 'Saving configuration to config.ini'
    else:
        raise TypeError('修改配置错误')
    sys.exit(0)

########NEW FILE########
__FILENAME__ = download
#!/usr/bin/env python

import sys
import logging
import argparse
import subprocess

from bddown_core import Pan, Album
from util import convert_none, parse_url, add_http
from config import global_config


def download_command(filename, link, limit=None, output_dir=None):
    bool(output_dir) and not os.path.exists(output_dir) and os.makedirs(output_dir)
    print "\033[32m" + filename + "\033[0m"
    firefox_ua = 'Mozilla/5.0 (Windows NT 6.1; Win64; x64; rv:25.0) Gecko/20100101 Firefox/25.0'
    cmd = "aria2c -c -o '%(filename)s' -s5 -x5" \
          " --user-agent='%(useragent)s' --header 'Referer:http://pan.baidu.com/disk/home'" \
          " %(limit)s %(dir)s '%(link)s'" % {
              "filename": filename,
              "useragent": firefox_ua,
              "limit": convert_none('--max-download-limit=', limit),
              "dir": convert_none('--dir=', output_dir),
              "link": link
          }
    subprocess.call(cmd, shell=True)


def download(args):
    limit = global_config.limit
    output_dir = global_config.dir
    parser = argparse.ArgumentParser(description="download command arg parser")
    parser.add_argument('-L', '--limit', action="store", dest='limit', help="Max download speed limit.")
    parser.add_argument('-D', '--dir', action="store", dest='output_dir', help="Download task to dir.")
    parser.add_argument('-S', '--secret', action="store", dest='secret', help="Retrieval password.", default="")
    if not args:
        parser.print_help()
        exit(1)
    namespace, links = parser.parse_known_args(args)
    secret = namespace.secret
    if namespace.limit:
        limit = namespace.limit
    if namespace.output_dir:
        output_dir = namespace.output_dir

    # if is wap
    links = [link.replace("wap/link", "share/link") for link in links]
    links = map(add_http, links)        # add 'http://'
    for url in links:
        res = parse_url(url)
        # normal
        if res.get('type') == 1:
            pan = Pan(url, secret=secret)
            count = 1
            while count != 0:
                link, filename, count = pan.info
                download_command(filename, link, limit=limit, output_dir=output_dir)

        # album
        elif res.get('type') == 2:
            album_id = res.get('album_id')
            uk = res.get('uk')
            album = Album(album_id, uk)
            count = 1
            while count != 0:
                link, filename, count = album.info
                download_command(filename, link, limit=limit, output_dir=output_dir)
        # home
        elif res.get('type') == 3:
            raise NotImplementedError('This function has not implemented.')
        elif res.get('type') == 0:
            logging.debug(url)
            continue
        else:
            continue

    sys.exit(0)

########NEW FILE########
__FILENAME__ = export
#!/usr/bin/env python2
# coding=utf-8

import json
import urllib2
import logging
import base64

from config import global_config
from bddown_core import Pan, GetFilenameError


def export(links):
    for link in links:
        pan = Pan(link)
        count = 1
        while count != 0:
            link, filename, count = pan.info
            if not filename and not link:
                raise GetFilenameError("无法获取下载地址或文件名！")
            export_single(filename, link)


def export_single(filename, link):
    jsonrpc_path = global_config.jsonrpc
    jsonrpc_user = global_config.jsonrpc_user
    jsonrpc_pass = global_config.jsonrpc_pass
    if not jsonrpc_path:
        print "请设置config.ini中的jsonrpc选项"
        exit(1)
    jsonreq = json.dumps(
        [{
            "jsonrpc": "2.0",
            "method": "aria2.addUri",
            "id": "qwer",
            "params": [
                [link],
                {
                    "out": filename,
                    "header": "User-Agent: Mozilla/5.0 (Windows NT 6.1; Win64; x64; rv:25.0) Gecko/20100101 Firefox/25.0"
                              "\r\nReferer:http://pan.baidu.com/disk/home"
                }]
        }]
    )
    logging.debug(jsonreq)
    try:
        request = urllib2.Request(jsonrpc_path)
        if jsonrpc_user and jsonrpc_pass:
	    base64string = base64.encodestring('%s:%s' % (jsonrpc_user, jsonrpc_pass)).replace('\n', '')
            request.add_header("Authorization", "Basic %s" % base64string)
        request.add_data(jsonreq)
        req = urllib2.urlopen(request)
    except urllib2.URLError as urle:
        print urle
        raise JsonrpcError("jsonrpc无法连接，请检查jsonrpc地址是否有误！")
    if req.code == 200:
        print "已成功添加到jsonrpc\n"


class JsonrpcError(Exception):
    pass

########NEW FILE########
__FILENAME__ = login
#!/usr/bin/env python2
# coding=utf-8

from time import time
import json
import logging
import re
import os
from urllib import urlencode
import urllib2
import cookielib

from config import global_config

# logging.basicConfig(level=logging.DEBUG)


class BaiduAccount(object):
    headers = {
        'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 '
                      '(KHTML, like Gecko) Chrome/32.0.1700.77 Safari/537.36',
    }

    def __init__(self, username, passwd, cookie_filename):
        self.username = username
        self.passwd = passwd
        self.cookie_filename = cookie_filename
        self.cj = cookielib.LWPCookieJar(cookie_filename)
        self.opener = urllib2.build_opener(
            urllib2.HTTPRedirectHandler(),
            urllib2.HTTPHandler(),
            urllib2.HTTPCookieProcessor(self.cj)
        )
        self.codestring = ''
        self.time = int(time())
        self._check_url = 'https://passport.baidu.com/v2/api/?logincheck&callback=bdPass.api.login._needCodestring' \
                          'CheckCallback&tpl=mn&charset=utf-8&index=0&username=%s&time=%d'
        self._token_url = 'https://passport.baidu.com/v2/api/?getapi&class=login&tpl=mn&tangram=true'
        self._post_url = 'https://passport.baidu.com/v2/api/?login'
        # debug:
        # self._post_url = 'http://httpbin.org/post'
        self.token = ''
        self.baiduid = ''
        self.bduss = ''

    def _get_badidu_uid(self):
        self.opener.open('http://www.baidu.com')
        for cookie in self.cj:
            if cookie.name == 'BAIDUID':
                self.baiduid = cookie.value
        logging.debug(self.baiduid)

    def _check_verify_code(self):
        r = self.opener.open(self._check_url % (self.username, self.time))
        s = r.read()
        data = json.loads(s[s.index('{'):-1])
        logging.debug(data)
        # TODO
        # 验证码
        if data.get('errno'):
            self.codestring = data.get('codestring')

    def _get_token(self):
        r = self.opener.open(self._token_url)
        s = r.read()
        try:
            self.token = re.search("login_token='(\w+)';", s).group(1)
            logging.debug(self.token)
        except:
            raise GetTokenError("Can't get the token")

    def _post_data(self):
        post_data = {'ppui_logintime': '9379', 'charset': 'utf-8', 'codestring': '', 'token': self.token,
                     'isPhone': 'false', 'index': '0', 'u': '', 'safeflg': 0,
                     'staticpage': 'http://www.baidu.com/cache/user/html/jump.html', 'loginType': '1', 'tpl': 'mn',
                     'callback': 'parent.bdPass.api.login._postCallback', 'username': self.username,
                     'password': self.passwd, 'verifycode': '', 'mem_pass': 'on'}
        post_data = urlencode(post_data)
        logging.debug(post_data)
        self.opener.open(self._post_url, data=post_data)
        for cookie in self.cj:
            if cookie.name == 'BDUSS':
                self.bduss = cookie.value
        logging.debug(self.bduss)
        self.cj.save()

    def login(self):
        self._get_badidu_uid()
        self._check_verify_code()
        if self.codestring:
            # TODO
            # 验证码处理
            pass
        self._get_token()
        self._post_data()
        logging.debug(self.cj)
        if not self.bduss and not self.baiduid:
            raise LoginError('登陆异常')

    def load_cookies_from_file(self):
        # if cookie exist
        if os.access(self.cookie_filename, os.F_OK):
            self.cj.load()
            for cookie in self.cj:
                if cookie.name == 'BAIDUID':
                    self.baiduid = cookie.value
                elif cookie.name == 'BDUSS':
                    self.bduss = cookie.value


class GetTokenError(Exception):
    pass


class LoginError(Exception):
    pass


def login(args):
    if args:
        username = args[0]
        passwd = args[1]
    else:
        username = global_config.username
        passwd = global_config.password
    if not username and not passwd:
        raise LoginError('请输入你的帐号密码！')
    cookies = global_config.cookies
    account = BaiduAccount(username, passwd, cookies)
    account.login()
    print "Saving session to %s" % cookies

########NEW FILE########
__FILENAME__ = show
import sys

from bddown_core import Pan
from util import bd_help


def show(links):
    if not len(links):
        bd_help('show')
    else:
        for url in links:
            pan = Pan(url)
            count = 1
            while count != 0:
                link, filename, count = pan.info
                print "%s\n%s\n\n" % (filename, link)
    sys.exit(0)
########NEW FILE########
__FILENAME__ = util
#!/usr/bin/env python2
# coding=utf-8

import urlparse

import bddown_help

__all__ = [
    "bd_help",
    "usage",
    "parse_url"
    "add_http",
    "convert_none",
    "bcolor",
    "in_list",
]

URL = ['pan.baidu.com', 'yun.baidu.com']
FILTER_KEYS = ['shareid', 'server_filename', 'isdir', 'fs_id', 'sign', 'time_stamp', 'shorturl', 'dlink',
               'filelist', 'operation']
# TODO: add md5


def bd_help(args):
    if len(args) == 1:
        helper = getattr(bddown_help, args[0].lower(), bddown_help.help)
        usage(helper)
    elif len(args) == 0:
        usage(bddown_help.show_help)
    else:
        usage(bddown_help.help)


def usage(doc=bddown_help.usage, message=None):
    if hasattr(doc, '__call__'):
        doc = doc()
    if message:
        print message
    print doc.strip()


def parse_url(url):
    """This function will parse url and judge which type the link is.

    Args:
      url (str): the url user input.

    Returns:
      type (dict): 1 -> link, 2 -> album, 3 -> home, 0 -> unknown, -1 -> error
    """
    result = urlparse.urlparse(url)

    # wrong url
    if result.netloc not in ('pan.baidu.com', 'yun.baidu.com'):
        return {'type': -1}

    # http://pan.baidu.com/s/1kTFQbIn or http://pan.baidu.com/share/link?shareid=2009678541&uk=2839544145
    if result.path.startswith('/s/') or ('link' in result.path):
        return {'type': 1}

    # http://pan.baidu.com/pcloud/album/info?uk=3943531277&album_id=1553987381796453514
    elif 'album' in result.path:
        info = dict(urlparse.parse_qsl(result.query))
        info['type'] = 2
        return info

    # TODO: download share home
    # http://pan.baidu.com/share/home?uk=NUMBER
    elif 'home' in result.path and result.query:
        return {'type': 3}
    else:
        return {'type': 0}

add_http = lambda url: url if url.startswith('http://') else 'http://'+url

convert_none = lambda opt, arg: opt + arg if arg else ""


# from http://stackoverflow.com/questions/287871/print-in-terminal-with-colors-using-python
# THANKS!

class BColor(object):
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'

    def disable(self):
        self.HEADER = ''
        self.OKBLUE = ''
        self.OKGREEN = ''
        self.WARNING = ''
        self.FAIL = ''
        self.ENDC = ''

bcolor = BColor()

in_list = lambda key, want_keys: key in want_keys


def filter_dict(bool_func, dictionary, want_keys):
    filtered_dict = {}
    for each_key in dictionary.keys():
        if bool_func(each_key, want_keys):
            filtered_dict[each_key] = dictionary[each_key]
    return filtered_dict


def merge_dict(dictionary, key):
    # will remove
    try:
        dictionary.update(dictionary[key][0])
        del dictionary[key]
    except KeyError:
        pass
    return dictionary


def filter_dict_wrapper(dictionary):
    d = {}
    for (k, v) in dictionary.items():
        if k in FILTER_KEYS:
            d[k] = v
        elif k == 'filelist':
            d[k] = [filter_dict(in_list, item, FILTER_KEYS) for item in v]
        elif k == 'operation':
            d[k] = [filter_dict(in_list, item, FILTER_KEYS) for item in v[0].get('filelist')]
    return d

########NEW FILE########
