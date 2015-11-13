__FILENAME__ = 115
#!/usr/bin/env python2
# vim: set fileencoding=utf8

import os
import sys
import requests
import urllib
import json
import re
import time
import argparse
import random
import sha
import select


account  = ''
password = ''   # 注意password不能超过48位


############################################################
# wget exit status
wget_es = {
    0: "No problems occurred.",
    2: "User interference.",
    1<<8: "Generic error code.",
    2<<8: "Parse error - for instance, when parsing command-line " \
        "optio.wgetrc or .netrc...",
    3<<8: "File I/O error.",
    4<<8: "Network failure.",
    5<<8: "SSL verification failure.",
    6<<8: "Username/password authentication failure.",
    7<<8: "Protocol errors.",
    8<<8: "Server issued an error response."
}
############################################################

s = '\x1b[%d;%dm%s\x1b[0m'       # terminual color template

cookie_file = os.path.join(os.path.expanduser('~'), '.115.cookies')

headers = {
    "Accept":"Accept: application/json, text/javascript, */*; q=0.01",
    "Accept-Encoding":"text/html",
    "Accept-Language":"en-US,en;q=0.8,zh-CN;q=0.6,zh;q=0.4,zh-TW;q=0.2",
    "Content-Type":"application/x-www-form-urlencoded; charset=UTF-8",
    "Referer":"http://m.115.com/",
    "X-Requested-With": "XMLHttpRequest",
    "User-Agent":"Mozilla/5.0 (X11; Linux i686) AppleWebKit/537.36 "\
        "(KHTML, like Gecko) Chrome/32.0.1700.77 Safari/537.36"
}

ss = requests.session()
ss.headers.update(headers)

class pan115(object):
    def __init__(self):
        self.download = self.play if args.play else self.download

    def init(self):
        def loginandcheck():
            self.login()
            if self.check_login():
                print s % (1, 92, '  -- login success\n')
            else:
                print s % (1, 91, '  !! login fail, maybe username or password is wrong.\n')
                print s % (1, 91, '  !! maybe this app is down.')
                sys.exit(1)

        if os.path.exists(cookie_file):
            t = json.loads(open(cookie_file).read())
            if t.get('user') != None and t.get('user') == account:
                ss.cookies.update(t.get('cookies', t))
                if not self.check_login():
                    loginandcheck()
            else:
                print s % (1, 91, '\n  ++ account changed, then relogin')
                loginandcheck()
        else:
            loginandcheck()

    def check_login(self):
        print s % (1, 97, '\n  -- check_login')
        url = 'http://msg.115.com/?ac=unread'
        j = ss.get(url)
        if '"code"' not in j.text:
            print s % (1, 92, '  -- check_login success\n')
            self.save_cookies()
            return True
        else:
            print s % (1, 91, '  -- check_login fail\n')
            return False

    def login(self):
        print s % (1, 97, '\n  -- login')

        def get_ssopw(ssoext):
            p = sha.new(password).hexdigest()
            a = sha.new(account).hexdigest()
            t = sha.new(p + a).hexdigest()
            ssopw = sha.new(t + ssoext.upper()).hexdigest()
            return ssopw

        ssoext = str(int(time.time()*1000))
        ssopw = get_ssopw(ssoext)

        quote = urllib.quote
        data = quote("login[ssoent]")+"=B1&" + \
            quote("login[version]")+"=2.0&" + \
            quote("login[ssoext]")+"=%s&" % ssoext + \
            quote("login[ssoln]")+"=%s&" % quote(account) + \
            quote("login[ssopw]")+"=%s&" % ssopw + \
            quote("login[ssovcode]")+"=%s&" % ssoext + \
            quote("login[safe]")+"=1&" + \
            quote("login[time]")+"=1&" + \
            quote("login[safe_login]")+"=1&" + \
            "goto=http://m.115.com/?ac=home"

        theaders = headers
        theaders["Referer"] = "http://passport.115.com/static/reg_login_130418/bridge.html?ajax_cb_key=bridge_%s" \
        % int(time.time()*1000)

        # Post!
        # XXX : do not handle errors
        params = {
            'ct': 'login',
            'ac': 'ajax',
            'is_ssl': 1
        }
        url = 'http://passport.115.com'
        ss.post(url, params=params, data=data, headers=theaders)

    def save_cookies(self):
        with open(cookie_file, 'w') as g:
            c = {'user': account, 'cookies': ss.cookies.get_dict()}
            g.write(json.dumps(c, indent=4, sort_keys=True))

    def get_dlink(self, pc):
        params = {
            "ct": "app",
            "ac": "get",
            "pick_code": pc.encode('utf8')
        }
        url = 'http://115.com'
        r = ss.get(url, params=params)
        j = r.json()
        dlink = j['data']['url'].encode('utf8')
        return dlink

    def get_infos(self, cid):
        params = {
            "cid": cid,
            "offset": 0,
            "type": "",
            "limit": 10000,
            "format": "json",
            "aid": 1,
            "o": "file_name",
            "asc": 0,
            "show_dir": 1
        }

        url = 'http://web.api.115.com/files'
        j = json.loads(ss.get(url, params=params).content[3:])

        dir_loop1 = [{'dir': j['path'][-1]['name'], 'cid': j['cid']}]
        dir_loop2 = []
        #base_dir = os.getcwd()
        while dir_loop1:
            for d in dir_loop1:
                params['cid'] = d['cid']
                j = json.loads(ss.get(url, params=params).content[3:])
                if j['errNo'] == 0 and j['data']:
                    if args.type_:
                        j['data'] = [x for x in j['data'] if x.get('ns') \
                            or x['ico'].lower() == unicode(args.type_.lower())]
                    total_file = len([i for i in j['data'] if not i.get('ns')])
                    if args.from_ - 1:
                        j['data'] = j['data'][args.from_-1:] if args.from_ else j['data']
                    nn = args.from_
                    for i in j['data']:
                        if i.get('ns'):
                            item = {
                                'dir': os.path.join(d['dir'], i['ns']),
                                'cid': i['cid']
                            }
                            dir_loop2.append(item)
                        else:
                            t = i['n']
                            t =  os.path.join(d['dir'], t).encode('utf8')
                            t =  os.path.join(os.getcwd(), t)
                            infos = {
                                'file': t,
                                'dir_': os.path.split(t)[0],
                                'dlink': self.get_dlink(i['pc']),
                                'name': i['n'].encode('utf8'),
                                'nn': nn,
                                'total_file': total_file
                            }
                            nn += 1
                            self.download(infos)
                else:
                    print s % (1, 91, '  error: get_infos')
                    sys.exit(0)
            dir_loop1 = dir_loop2
            dir_loop2 = []


    @staticmethod
    def download(infos):
        ## make dirs
        if not os.path.exists(infos['dir_']):
            os.makedirs(infos['dir_'])
        else:
            if os.path.exists(infos['file']):
                return 0

        num = random.randint(0, 7) % 7
        col = s % (2, num + 90, infos['file'])
        infos['nn'] = infos['nn'] if infos.get('nn') else 1
        infos['total_file'] = infos['total_file'] if infos.get('total_file') else 1
        print '\n  ++ 正在下载: #', s % (1, 97, infos['nn']), '/', s % (1, 97, infos['total_file']), '#', col

        if args.aria2c:
            # 115 普通用户只能有4下载通道。
            if args.limit:
                cmd = 'aria2c -c -x4 -s4 ' \
                    '--max-download-limit %s ' \
                    '-o "%s.tmp" -d "%s" ' \
                    '--user-agent "%s" ' \
                    '--header "Referer:http://m.115.com/" "%s"' \
                    % (args.limit, infos['name'], infos['dir_'],\
                        headers['User-Agent'], infos['dlink'])
            else:
                cmd = 'aria2c -c -x4 -s4 ' \
                    '-o "%s.tmp" -d "%s" --user-agent "%s" ' \
                    '--header "Referer:http://m.115.com/" "%s"' \
                    % (infos['name'], infos['dir_'], headers['User-Agent'], \
                        infos['dlink'])
        else:
            if args.limit:
                cmd = 'wget -c --limit-rate %s ' \
                    '-O "%s.tmp" --user-agent "%s" ' \
                    '--header "Referer:http://m.115.com/" "%s"' \
                    % (args.limit, infos['file'], headers['User-Agent'], infos['dlink'])
            else:
                cmd = 'wget -c -O "%s.tmp" --user-agent "%s" ' \
                    '--header "Referer:http://m.115.com/" "%s"' \
                    % (infos['file'], headers['User-Agent'], infos['dlink'])

        status = os.system(cmd)
        if status != 0:     # other http-errors, such as 302.
            wget_exit_status_info = wget_es[status]
            print('\n\n ----###   \x1b[1;91mERROR\x1b[0m ==> '\
                '\x1b[1;91m%d (%s)\x1b[0m   ###--- \n\n' \
                 % (status, wget_exit_status_info))
            print s % (1, 91, '  ===> '), cmd
            sys.exit(1)
        else:
            os.rename('%s.tmp' % infos['file'], infos['file'])

    @staticmethod
    def play(infos):
        num = random.randint(0, 7) % 7
        col = s % (2, num + 90, infos['name'])
        infos['nn'] = infos['nn'] if infos.get('nn') else 1
        infos['total_file'] = infos['total_file'] if infos.get('total_file') else 1
        print '\n  ++ play: #', s % (1, 97, infos['nn']), '/', s % (1, 97, infos['total_file']), '#', col

        if os.path.splitext(infos['file'])[-1].lower() == '.wmv':
            cmd = 'mplayer -really-quiet -cache 8140 ' \
                '-http-header-fields "user-agent:%s" ' \
                '-http-header-fields "Referer:http://m.115.com/" "%s"' \
                % (headers['User-Agent'], infos['dlink'])
        else:
            cmd = 'mpv --really-quiet --cache 8140 --cache-default 8140 ' \
                '--http-header-fields "user-agent:%s" '\
                '--http-header-fields "Referer:http://m.115.com" "%s"' \
                % (headers['User-Agent'], infos['dlink'])

        status = os.system(cmd)
        timeout = 1
        ii, _, _ = select.select([sys.stdin], [], [], timeout)
        if ii:
            sys.exit(0)
        else:
            pass

    def exists(self, filepath):
        pass

    def upload(self, path, dir_):
        pass

    def addtask(self, u):
        # get uid
        url = 'http://my.115.com/?ct=ajax&ac=get_user_aq'
        r = ss.get(url)
        j = r.json()
        uid = j['data']['uid']

        # get sign, time
        url = 'http://115.com/?ct=offline&ac=space'
        r = ss.get(url)
        j = r.json()
        sign = j['sign']
        tm = j['time']

        # now, add task
        data = {
            'url': urllib.quote_plus(u),
            'uid': uid,
            'sign': sign,
            'time': str(tm)
        }
        url = 'http://115.com/lixian/?ct=lixian&ac=add_task_url'
        r = ss.post(url, data=data)
        j = r.json()
        if j['info_hash']:
            print s % (1, 92, '  ++ add task success.')
        else:
            print s % (1, 91, '  !! Error: %s' % j['error_msg'])
            sys.exit()

        data = {
            'page': 1,
            'uid': uid,
            'sign': sign,
            'time': str(tm)
        }
        url = 'http://115.com/lixian/?ct=lixian&ac=task_lists'
        r = ss.post(url, data=data)
        j = r.json()
        percentDone = j['tasks'][0]['percentDone']
        print s % (1, 97, '  ++ %s' % j['tasks'][0]['name'])
        print s % (1, 92, '  %s%s Done' % (percentDone, '%'))

    def do(self, pc):
        dlink = self.get_dlink(pc)
        name = re.search(r'file=(.+?)(&|$)', dlink).group(1)
        name = urllib.unquote_plus(name)
        t = os.path.join(os.getcwd(), name)
        infos = {
            'file': t,
            'dir_': os.path.split(t)[0],
            'dlink': dlink,
            'name': name,
            'nn': 1,
            'total_file': 1
        }
        self.download(infos)

def main(url):
    if 'pickcode' in url:
        pc = re.search(r'pickcode=([\d\w]+)', url)
        if pc:
            pc = pc.group(1)
            x = pan115()
            x.init()
            x.do(pc)
        else:
            print s % (1, 91, '  can\'t find pickcode.')
    elif 'cid=' in url:
        cid = re.search(r'cid=(\d+)', url)
        cid = cid.group(1) if cid else '0'
        x = pan115()
        x.init()
        x.get_infos(cid)
    elif args.addtask:
        x = pan115()
        x.init()
        x.addtask(url)
    else:
        print s % (2, 91, '  请正确输入自己的115地址。')

if __name__ == '__main__':
    p = argparse.ArgumentParser(description='download from 115.com reversely')
    p.add_argument('url', help='自己115文件夹url')
    p.add_argument('-a', '--aria2c', action='store_true', \
        help='download with aria2c')
    p.add_argument('-p', '--play', action='store_true', \
        help='play with mpv')
    p.add_argument('-f', '--from_', action='store', \
        default=1, type=int, \
        help='从第几个开始下载，eg: -f 42')
    p.add_argument('-t', '--type_', action='store', \
        default=None, type=str, \
        help='要下载的文件的后缀，eg: -t mp3')
    p.add_argument('-l', '--limit', action='store', \
        default=None, type=str, help='下载速度限制，eg: -l 100k')
    p.add_argument('-d', '--addtask', action='store_true', \
        help='加离线下载任务')
    args = p.parse_args()
    main(args.url)

########NEW FILE########
__FILENAME__ = 91porn
#!/usr/bin/env python2
# vim: set fileencoding=utf8

import os
import sys
import requests
import urlparse
import re
import argparse
import random
import select

############################################################
# wget exit status
wget_es = {
    0: "No problems occurred.",
    2: "User interference.",
    1<<8: "Generic error code.",
    2<<8: "Parse error - for instance, when parsing command-line " \
        "optio.wgetrc or .netrc...",
    3<<8: "File I/O error.",
    4<<8: "Network failure.",
    5<<8: "SSL verification failure.",
    6<<8: "Username/password authentication failure.",
    7<<8: "Protocol errors.",
    8<<8: "Server issued an error response."
}
############################################################

s = '\x1b[%d;%dm%s\x1b[0m'       # terminual color template

headers = {
    "Accept":"text/html,application/xhtml+xml,application/xml; " \
        "q=0.9,image/webp,*/*;q=0.8",
    "Accept-Encoding":"text/html",
    "Accept-Language":"en-US,en;q=0.8,zh-CN;q=0.6,zh;q=0.4,zh-TW;q=0.2",
    "Content-Type":"application/x-www-form-urlencoded",
    "User-Agent":"Mozilla/5.0 (X11; Linux i686) AppleWebKit/537.36 " \
        "(KHTML, like Gecko) Chrome/32.0.1700.77 Safari/537.36"
}

ss = requests.session()
ss.headers.update(headers)

class nrop19(object):
    def __init__(self, url=None):
        self.url = url
        self.download = self.play if args.play else self.download

    def get_infos(self):
        r = ss.get(self.url)
        if r.ok:
            n1 = re.search(r'so.addVariable\(\'file\',\'(\d+)\'', r.content)
            n2 = re.search(r'so.addVariable\(\'seccode\',\'(.+?)\'', r.content)
            n3 = re.search(r'so.addVariable\(\'max_vid\',\'(\d+)\'', r.content)

            if n1 and n2 and n3:
                apiurl = 'http://%s/getfile.php' \
                    % urlparse.urlparse(self.url).hostname

                params = {
                    'VID': n1.group(1),
                    'mp4': 1,
                    'seccode': n2.group(1),
                    'max_vid': n3.group(1),
                }

                r = ss.get(apiurl, params=params)
                if r.ok:
                    dlink = re.search(r'file=(http.+?\.mp4)', r.content).group(1)
                    name = re.search(r'viewkey=([\d\w]+)', self.url).group(1)
                    infos = {
                        'name': '%s.mp4' % name,
                        'file': os.path.join(os.getcwd(), '%s.mp4' % name),
                        'dir_': os.getcwd(),
                        'dlink': dlink
                    }
                    self.download(infos)
                else:
                    print s % (1, 91, '  Error at get(apiurl)')
            else:
                print s % (1, 91, '  You are blocked')

    def download(self, infos):
        num = random.randint(0, 7) % 7
        col = s % (2, num + 90, infos['file'])
        print '\n  ++ 正在下载: %s' % col

        cookies = '; '.join(['%s=%s' % (i, ii) for i, ii in ss.cookies.items()])
        if args.aria2c:
            cmd = 'aria2c -c -x10 -s10 ' \
                '-o "%s.tmp" -d "%s" --header "User-Agent: %s" ' \
                '--header "Cookie: %s" "%s"' \
                % (infos['name'], infos['dir_'], \
                headers['User-Agent'], cookies, infos['dlink'])
        else:
            cmd = 'wget -c -O "%s.tmp" --header "User-Agent: %s" ' \
                '--header "Cookie: %s" "%s"' \
                % (infos['file'], headers['User-Agent'], cookies, infos['dlink'])

        status = os.system(cmd)
        if status != 0:     # other http-errors, such as 302.
            wget_exit_status_info = wget_es[status]
            print('\n\n ----###   \x1b[1;91mERROR\x1b[0m ==> '\
                '\x1b[1;91m%d (%s)\x1b[0m   ###--- \n\n' \
                % (status, wget_exit_status_info))
            print s % (1, 91, '  ===> '), cmd
            sys.exit(1)
        else:
            os.rename('%s.tmp' % infos['file'], infos['file'])

    def play(self, infos):
        num = random.randint(0, 7) % 7
        col = s % (2, num + 90, infos['name'])
        print '\n  ++ play: %s' % col

        cmd = 'mpv --really-quiet --cache 8140 --cache-default 8140 ' \
            '--http-header-fields "user-agent:%s" "%s"' \
            % (headers['User-Agent'], infos['dlink'])

        status = os.system(cmd)
        timeout = 1
        ii, _, _ = select.select([sys.stdin], [], [], timeout)
        if ii:
            sys.exit(0)
        else:
            pass

    def do(self):
        self.get_infos()

def main(url):
    x = nrop19(url)
    x.do()

if __name__ == '__main__':
    p = argparse.ArgumentParser(description='download from 91porn.com')
    p.add_argument('url', help='url of 91porn.com')
    p.add_argument('-a', '--aria2c', action='store_true', \
                help='download with aria2c')
    p.add_argument('-p', '--play', action='store_true', \
                help='play with mpv')
    args = p.parse_args()
    main(args.url)

########NEW FILE########
__FILENAME__ = ed2k_search
#!/usr/bin/env python2
# vim: set fileencoding=utf8

import sys
import urllib
import re
import argparse

s = '\x1b[%d;%dm%s\x1b[0m'       # terminual color template

opener = urllib.urlopen

class ed2k_search(object):
    def __init__(self, keyword=''):
        self.url = "http://donkey4u.com/search/%s?page=%s&mode=list" % (keyword, '%s')
        print ''

    def get_infos(self, url):
        r = opener(url)
        assert r
        self.html = r.read()
        html = re.search(r'<table class=\'search_table\'>.+?</table>', self.html, re.DOTALL).group()

        sizes = re.findall(r'<td width=\'70\' align=\'right\'>(.+)', html)
        seeds = re.findall(r'<td width=\'100\' align=\'right\'>(.+)', html)
        links = re.findall(r'ed2k://.+?/', html)

        infos = zip(sizes, seeds, links)

        if infos:
            self.display(infos)
        else:
            print s % (1, 91, '  !! You are not Lucky, geting nothing.')
            sys.exit(1)

    def display(self, infos):
        template = '  size: ' + s % (1, 97, '%s') \
            + '  seed: ' + s % (1, 91, '%s') \
            + '\n  ----------------------------' \
            + '\n  ' + s % (2, 92, '%s') \
            + '\n  ----------------------------\n'

        for i in infos:
            t = template % i
            print t

    def do(self):
        page = 1
        while True:
            url = self.url % page
            self.get_infos(url)
            nx = raw_input(s % (5, 93, '  next page?') + ' (N/y): ')
            if nx in ('Y', 'y'):
                page += 1
                print ''
            else:
                sys.exit(1)


def main(xxx):
    keyword = ' '.join(xxx)
    x = ed2k_search(keyword)
    x.do()

if __name__ == '__main__':
    p = argparse.ArgumentParser(description='searching ed2k at donkey4u.com')
    p.add_argument('xxx', type=str, nargs='*', help='keyword')
    args = p.parse_args()
    main(args.xxx)

########NEW FILE########
__FILENAME__ = music.163.com
#!/usr/bin/env python2
# vim: set fileencoding=utf8

import re
import sys
import os
import random
import time
import json
import logging
import argparse
import urllib
import requests
import select
import md5
from mutagen.id3 import ID3,TRCK,TIT2,TALB,TPE1,APIC,TDRC,COMM,TPOS,USLT
from HTMLParser import HTMLParser

parser = HTMLParser()
s = u'\x1b[%d;%dm%s\x1b[0m'       # terminual color template

############################################################
# music.163.com api
# {{{
url_song = "http://music.163.com/api/song/detail?id=%s&ids=%s"
url_album = "http://music.163.com/api/album/%s"
url_playlist = "http://music.163.com/api/playlist/detail?id=%s&ids=%s"
url_dj = "http://music.163.com/api/dj/program/detail?id=%s&ids=%s"
url_artist_albums = "http://music.163.com/api/artist/albums/%s?offset=0&limit=1000"
url_artist_top_50_songs = "http://music.163.com/artist/%s"
# }}}
############################################################

############################################################
# wget exit status
wget_es = {
    0:"No problems occurred.",
    2:"User interference.",
    1<<8:"Generic error code.",
    2<<8:"Parse error - for instance, when parsing command-line ' \
        'optio.wgetrc or .netrc...",
    3<<8:"File I/O error.",
    4<<8:"Network failure.",
    5<<8:"SSL verification failure.",
    6<<8:"Username/password authentication failure.",
    7<<8:"Protocol errors.",
    8<<8:"Server issued an error response."
}
############################################################

headers = {
    "Accept":"text/html,application/xhtml+xml,application/xml; " \
        "q=0.9,image/webp,*/*;q=0.8",
    "Accept-Encoding":"text/html",
    "Accept-Language":"en-US,en;q=0.8,zh-CN;q=0.6,zh;q=0.4,zh-TW;q=0.2",
    "Content-Type":"application/x-www-form-urlencoded",
    "Referer":"http://music.163.com/",
    "User-Agent":"Mozilla/5.0 (X11; Linux i686) AppleWebKit/537.36 "\
        "(KHTML, like Gecko) Chrome/32.0.1700.77 Safari/537.36"
}

ss = requests.session()
ss.headers.update(headers)

def encrypted_id(id):
    byte1 = bytearray('3go8&$8*3*3h0k(2)2')
    byte2 = bytearray(id)
    byte1_len = len(byte1)
    for i in xrange(len(byte2)):
        byte2[i] = byte2[i]^byte1[i%byte1_len]
    m = md5.new()
    m.update(byte2)
    result = m.digest().encode('base64')[:-1]
    result = result.replace('/', '_')
    result = result.replace('+', '-')
    return result

def modificate_text(text):
    text = parser.unescape(text)
    text = re.sub(r'//*', '-', text)
    text = text.replace('/', '-')
    text = text.replace('\\', '-')
    text = re.sub(r'\s\s+', ' ', text)
    return text

def modificate_file_name_for_wget(file_name):
    file_name = re.sub(r'\s*:\s*', u' - ', file_name)    # for FAT file system
    file_name = file_name.replace('?', '')      # for FAT file system
    file_name = file_name.replace('"', '\'')    # for FAT file system
    return file_name

def z_index(size):
    z = len(str(size))
    return z

########################################################

class neteaseMusic(object):
    def __init__(self, url):
        self.url = url
        self.song_infos = []
        self.dir_ = os.getcwd().decode('utf8')
        self.template_wgets = 'wget -c -T 5 -nv -U "%s" -O' \
            % headers['User-Agent'] + ' "%s.tmp" %s'

        self.playlist_id = ''
        self.dj_id = ''
        self.album_id = ''
        self.artist_id = ''
        self.song_id = ''
        self.cover_id = ''
        self.cover_data = ''
        self.amount_songs = u'1'

        self.download = self.play if args.play else self.download

    def get_durl(self, i):
        for q in ('hMusic', 'mMusic', 'lMusic'):
            if i[q]:
                dfsId = str(i[q]['dfsId'])
                edfsId = encrypted_id(dfsId)
                durl = u'http://m2.music.126.net/%s/%s.mp3' % (edfsId, dfsId)
                return durl, q[0]

    def get_cover(self, info):
        if info['album_name'] == self.cover_id:
            return self.cover_data
        else:
            self.cover_id = info['album_name']
            while True:
                url = info['album_pic_url']
                try:
                    self.cover_data = requests.get(url).content
                    if self.cover_data[:5] != '<?xml':
                        return self.cover_data
                except Exception as e:
                    print s % (1, 91, '   \\\n   \\-- Error, get_cover --'), e
                    time.sleep(5)

    def modified_id3(self, file_name, info):
        id3 = ID3()
        id3.add(TRCK(encoding=3, text=info['track']))
        id3.add(TDRC(encoding=3, text=info['year']))
        id3.add(TIT2(encoding=3, text=info['song_name']))
        id3.add(TALB(encoding=3, text=info['album_name']))
        id3.add(TPE1(encoding=3, text=info['artist_name']))
        id3.add(TPOS(encoding=3, text=info['cd_serial']))
        #id3.add(USLT(encoding=3, text=self.get_lyric(info['lyric_url'])))
        #id3.add(TCOM(encoding=3, text=info['composer']))
        #id3.add(TCON(encoding=3, text=u'genres'))
        #id3.add(TSST(encoding=3, text=info['sub_title']))
        #id3.add(TSRC(encoding=3, text=info['disc_code']))
        id3.add(COMM(encoding=3, desc=u'Comment', \
            text=info['song_url']))
        id3.add(APIC(encoding=3, mime=u'image/jpg', type=3, \
            desc=u'Front Cover', data=self.get_cover(info)))
        id3.save(file_name)

    def url_parser(self):
        if 'playlist' in self.url:
            self.playlist_id = re.search(r'playlist.+?(\d+)', self.url).group(1)
            print(s % (2, 92, u'\n  -- 正在分析歌单信息 ...'))
            self.download_playlist()
        elif 'toplist' in self.url:
            t = re.search(r'toplist.+?(\d+)', self.url)
            if t:
                self.playlist_id = t.group(1)
            else:
                self.playlist_id = '3779629'
            print(s % (2, 92, u'\n  -- 正在分析排行榜信息 ...'))
            self.download_playlist()
        elif 'album' in self.url:
            self.album_id = re.search(r'album.+?(\d+)', self.url).group(1)
            print(s % (2, 92, u'\n  -- 正在分析专辑信息 ...'))
            self.download_album()
        elif 'artist' in self.url:
            self.artist_id = re.search(r'artist.+?(\d+)', self.url).group(1)
            code = raw_input('\n  >> 输入 a 下载该艺术家所有专辑.\n' \
                '  >> 输入 t 下载该艺术家 Top 50 歌曲.\n  >> ')
            if code == 'a':
                print(s % (2, 92, u'\n  -- 正在分析艺术家专辑信息 ...'))
                self.download_artist_albums()
            elif code == 't':
                print(s % (2, 92, u'\n  -- 正在分析艺术家 Top 50 信息 ...'))
                self.download_artist_top_50_songs()
            else:
                print(s % (1, 92, u'  --> Over'))
        elif 'song' in self.url:
            self.song_id = re.search(r'song.+?(\d+)', self.url).group(1)
            print(s % (2, 92, u'\n  -- 正在分析歌曲信息 ...'))
            self.download_song()
        elif 'dj' in self.url:
            self.dj_id = re.search(r'dj.+?(\d+)', self.url).group(1)
            print(s % (2, 92, u'\n  -- 正在分析DJ节目信息 ...'))
            self.download_dj()
        else:
            print(s % (2, 91, u'   请正确输入music.163.com网址.'))

    def get_song_info(self, i):
        z = z_index(i['album']['size']) if i['album'].get('size') else 1
        song_info = {}
        song_info['song_id'] = i['id']
        song_info['song_url'] = u'http://music.163.com/song/%s' % i['id']
        song_info['track'] = str(i['position'])
        song_info['durl'], song_info['mp3_quality'] = self.get_durl(i)
        #song_info['album_description'] = album_description
        #song_info['lyric_url'] = i['lyric']
        #song_info['sub_title'] = i['sub_title']
        #song_info['composer'] = i['composer']
        #song_info['disc_code'] = i['disc_code']
        #if not song_info['sub_title']: song_info['sub_title'] = u''
        #if not song_info['composer']: song_info['composer'] = u''
        #if not song_info['disc_code']: song_info['disc_code'] = u''
        t = time.gmtime(int(i['album']['publishTime'])*0.001)
        #song_info['year'] = unicode('-'.join([str(t.tm_year), \
            #str(t.tm_mon), str(t.tm_mday)]))
        song_info['year'] = unicode('-'.join([str(t.tm_year), \
            str(t.tm_mon), str(t.tm_mday)]))
        song_info['song_name'] = modificate_text(i['name']).strip()
        song_info['artist_name'] = modificate_text(i['artists'][0]['name'])
        song_info['album_pic_url'] = i['album']['picUrl']
        song_info['cd_serial'] = u'1'
        song_info['album_name'] = modificate_text(i['album']['name'])
        file_name = song_info['track'].zfill(z) + '.' + song_info['song_name'] \
            + ' - ' + song_info['artist_name'] + '.mp3'
        song_info['file_name'] = file_name
        # song_info['low_mp3'] = i['mp3Url']
        return song_info

    def get_song_infos(self, songs):
        for i in songs:
            song_info = self.get_song_info(i)
            self.song_infos.append(song_info)

    def download_song(self, noprint=False, n=1):
        j = ss.get(url_song % (self.song_id, urllib.quote('[%s]' % self.song_id))).json()
        songs = j['songs']
        logging.info('url -> http://music.163.com/song/%s' % self.song_id)
        logging.info('directory: %s' % os.getcwd())
        logging.info('total songs: %d' % 1)
        if not noprint:
            print(s % (2, 97, u'\n  >> ' + u'1 首歌曲将要下载.')) \
                if not args.play else ''
        self.get_song_infos(songs)
        self.download(self.amount_songs, n)

    def download_album(self):
        j = ss.get(url_album % (self.album_id)).json()
        songs = j['album']['songs']
        d = modificate_text(j['album']['name'] + ' - ' + j['album']['artist']['name'])
        dir_ = os.path.join(os.getcwd().decode('utf8'), d)
        self.dir_ = modificate_file_name_for_wget(dir_)
        logging.info('directory: %s' % self.dir_)
        logging.info('total songs: %d' % len(songs))
        logging.info('url -> http://music.163.com/album/%s' % self.album_id)
        self.amount_songs = unicode(len(songs))
        print(s % (2, 97, u'\n  >> ' + self.amount_songs + u' 首歌曲将要下载.')) \
            if not args.play else ''
        self.get_song_infos(songs)
        self.download(self.amount_songs)

    def download_playlist(self):
        #print url_playlist % (self.playlist_id, urllib.quote('[%s]' % self.playlist_id))
        #print repr(self.playlist_id)
        #sys.exit()
        j = ss.get(url_playlist % (self.playlist_id, urllib.quote('[%s]' % self.playlist_id))).json()
        songs = j['result']['tracks']
        d = modificate_text(j['result']['name'] + ' - ' + j['result']['creator']['nickname'])
        dir_ = os.path.join(os.getcwd().decode('utf8'), d)
        self.dir_ = modificate_file_name_for_wget(dir_)
        logging.info('url -> http://music.163.com/playlist/%s' \
                     % self.playlist_id)
        logging.info('directory: %s' % self.dir_)
        logging.info('total songs: %d' % len(songs))
        self.amount_songs = unicode(len(songs))
        print(s % (2, 97, u'\n  >> ' + self.amount_songs + u' 首歌曲将要下载.')) \
            if not args.play else ''
        n = 1
        self.get_song_infos(songs)
        self.download(self.amount_songs)

    def download_dj(self):
        j = ss.get(url_dj % (self.dj_id, urllib.quote('[%s]' % self.dj_id))).json()
        songs = j['program']['songs']
        d = modificate_text(j['program']['name'] + ' - ' + j['program']['dj']['nickname'])
        dir_ = os.path.join(os.getcwd().decode('utf8'), d)
        self.dir_ = modificate_file_name_for_wget(dir_)
        logging.info('url -> http://music.163.com/dj/%s' \
                     % self.dj_id)
        logging.info('directory: %s' % self.dir_)
        logging.info('total songs: %d' % len(songs))
        self.amount_songs = unicode(len(songs))
        print(s % (2, 97, u'\n  >> ' + self.amount_songs + u' 首歌曲将要下载.')) \
            if not args.play else ''
        self.get_song_infos(songs)
        self.download(self.amount_songs)


    def download_artist_albums(self):
        ss.cookies.update({'appver': '1.5.2'})
        j = ss.get(url_artist_albums % self.artist_id).json()
        for albuminfo in j['hotAlbums']:
            self.album_id = albuminfo['id']
            self.download_album()

    def download_artist_top_50_songs(self):
        html = ss.get(url_artist_top_50_songs % self.artist_id).content
        text = re.search(r'g_hotsongs = (.+?);</script>', html).group(1)
        j = json.loads(text)
        songids = [i['id'] for i in j]
        d = modificate_text(j[0]['artists'][0]['name'] + ' - ' + 'Top 50')
        dir_ = os.path.join(os.getcwd().decode('utf8'), d)
        self.dir_ = modificate_file_name_for_wget(dir_)
        logging.info('url -> http://music.163.com/artist/%s  --  Top 50' \
                     % self.artist_id)
        logging.info('directory: %s' % self.dir_)
        logging.info('total songs: %d' % len(songids))
        self.amount_songs = unicode(len(songids))
        print(s % (2, 97, u'\n  >> ' + self.amount_songs + u' 首歌曲将要下载.')) \
            if not args.play else ''
        n = 1
        for sid in songids:
            self.song_id = sid
            self.song_infos = []
            self.download_song(noprint=True, n=n)
            n += 1

    def display_infos(self, i):
        q = {'h': 'High', 'm': 'Middle', 'l': 'Low'}
        print '\n  ----------------'
        print '  >>', s % (2, 94, i['file_name'])
        print '  >>', s % (2, 95, i['album_name'])
        print '  >>', s % (2, 92, 'http://music.163.com/song/%s' % i['song_id'])
        print '  >>', s % (2, 97, 'MP3-Quality'), ':', s % (1, 92, q[i['mp3_quality']])
        print ''

    def play(self, amount_songs, n=None):
        for i in self.song_infos:
            durl = i['durl']
            self.display_infos(i)
            os.system('mpv --really-quiet --audio-display no %s' % durl)
            timeout = 1
            ii, _, _ = select.select([sys.stdin], [], [], timeout)
            if ii:
                sys.exit(0)
            else:
                pass

    def download(self, amount_songs, n=None):
        dir_ = modificate_file_name_for_wget(self.dir_)
        cwd = os.getcwd().decode('utf8')
        if dir_ != cwd:
            if not os.path.exists(dir_):
                os.mkdir(dir_)
        ii = 1
        for i in self.song_infos:
            num = random.randint(0, 100) % 7
            col = s % (2, num + 90, i['file_name'])
            t = modificate_file_name_for_wget(i['file_name'])
            file_name = os.path.join(dir_, t)
            if os.path.exists(file_name):  ## if file exists, no get_durl
                if args.undownload:
                    self.modified_id3(file_name, i)
                    ii += 1
                    continue
                else:
                    ii += 1
                    continue
            file_name_for_wget = file_name.replace('`', '\`')
            if not args.undownload:
                durl = i['durl']
                if n == None:
                    print(u'\n  ++ 正在下载: #%s/%s# %s' \
                        % (ii, amount_songs, col))
                    logging.info(u'  #%s/%s [%s] -> %s' \
                        % (ii, amount_songs, i['mp3_quality'], i['file_name']))
                else:
                    print(u'\n  ++ 正在下载: #%s/%s# %s' \
                        % (n, amount_songs, col))
                    logging.info(u'  #%s/%s [%s] -> %s' \
                        % (n, amount_songs, i['mp3_quality'], i['file_name']))
                wget = self.template_wgets % (file_name_for_wget, durl)
                wget = wget.encode('utf8')
                status = os.system(wget)
                if status != 0:     # other http-errors, such as 302.
                    wget_exit_status_info = wget_es[status]
                    logging.info('   \\\n                            \\->WARN: status: ' \
                        '%d (%s), command: %s' % (status, wget_exit_status_info, wget))
                    logging.info('  ########### work is over ###########\n')
                    print('\n\n ----###   \x1b[1;91mERROR\x1b[0m ==> \x1b[1;91m%d ' \
                        '(%s)\x1b[0m   ###--- \n\n' % (status, wget_exit_status_info))
                    print s % (1, 91, '  ===> '), wget
                    sys.exit(1)
                else:
                    os.rename('%s.tmp' % file_name, file_name)

            self.modified_id3(file_name, i)
            ii += 1
            time.sleep(0)

def main(url):
    x = neteaseMusic(url)
    x.url_parser()
    logging.info('  ########### work is over ###########\n')

if __name__ == '__main__':
    log_file = os.path.join(os.path.expanduser('~'), '.163music.log')
    logging.basicConfig(filename=log_file, format='%(asctime)s %(message)s')
    print(s % (2, 91, u'\n  程序运行日志在 %s' % log_file))
    p = argparse.ArgumentParser(description='downloading any music.163.com')
    p.add_argument('url', help='any url of music.163.com')
    p.add_argument('-p', '--play', action='store_true', \
        help='play with mpv')
    p.add_argument('-c', '--undownload', action='store_true', \
        help='no download, using to renew id3 tags')
    args = p.parse_args()
    main(args.url)

########NEW FILE########
__FILENAME__ = music.baidu.com
#!/usr/bin/env python2
# vim: set fileencoding=utf8

import re
import sys
import os
import random
import time
import json
import urllib2
import logging
import argparse
import select

from mutagen.id3 import ID3,TRCK,TIT2,TALB,TPE1,APIC,TDRC,COMM,TCOM,TCON,TSST,WXXX,TSRC
from HTMLParser import HTMLParser
parser = HTMLParser()
s = u'\x1b[%d;%dm%s\x1b[0m'       # terminual color template

headers = {
    "Accept":"text/html,application/xhtml+xml,application/xml; \
        q=0.9,image/webp,*/*;q=0.8",
    "Accept-Encoding":"text/html",
    "Accept-Language":"en-US,en;q=0.8,zh-CN;q=0.6,zh;q=0.4,zh-TW;q=0.2",
    "Content-Type":"application/x-www-form-urlencoded",
    "Referer":"http://www.baidu.com/",
    "User-Agent":"Mozilla/5.0 (X11; Linux i686) AppleWebKit/537.36 \
        (KHTML, like Gecko) Chrome/32.0.1700.77 Safari/537.36"
}

############################################################
# wget exit status
wget_es = {
    0:"No problems occurred.",
    2:"User interference.",
    1<<8:"Generic error code.",
    2<<8:"Parse error - for instance, when parsing command-line \
        optio.wgetrc or .netrc...",
    3<<8:"File I/O error.",
    4<<8:"Network failure.",
    5<<8:"SSL verification failure.",
    6<<8:"Username/password authentication failure.",
    7<<8:"Protocol errors.",
    8<<8:"Server issued an error response."
}
############################################################

def modificate_text(text):
    text = parser.unescape(text)
    text = re.sub(r'//*', '-', text)
    text = text.replace('/', '-')
    text = text.replace('\\', '-')
    text = re.sub(r'\s\s+', ' ', text)
    return text

def modificate_file_name_for_wget(file_name):
    file_name = re.sub(r'\s*:\s*', u' - ', file_name)    # for FAT file system
    file_name = file_name.replace('?', '')      # for FAT file system
    file_name = file_name.replace('"', '\'')    # for FAT file system
    return file_name

def z_index(song_infos):
    size = len(song_infos)
    z = len(str(size))
    return z

class baidu_music(object):
    def __init__(self, url):
        self.url = url
        self.song_infos = []
        self.json_url = ''
        self.dir_ = os.getcwd().decode('utf8')
        self.template_wgets = 'wget -nv -U "%s" -O "%s.tmp" %s' % (headers['User-Agent'], '%s', '%s')
        self.template_album = 'http://music.baidu.com/album/%s'
        if args.flac:
            self.template_api = 'http://music.baidu.com/data/music/fmlink?songIds=%s&type=flac'
        elif args.low:
            self.template_api = 'http://music.baidu.com/data/music/fmlink?songIds=%s&type=mp3'
        elif args.high:
            self.template_api = 'http://music.baidu.com/data/music/fmlink?songIds=%s&type=mp3&rate=320'
        else:
            self.template_api = 'http://music.baidu.com/data/music/fmlink?songIds=%s&type=mp3&rate=320'

        self.album_id = ''
        self.song_id = ''

        self.download = self.play if args.play else self.download

    def get_songidlist(self, id_):
        html = self.opener.open(self.template_album % id_).read()
        songidlist = re.findall(r'/song/(\d+)', html)
        api_json = self.opener.open(self.template_api % ','.join(songidlist)).read()
        api_json = json.loads(api_json)
        infos = api_json['data']['songList']
        return infos

    def get_cover(self, url):
        i = 1
        while True:
            cover_data = self.opener.open(url).read()
            if cover_data[:5] != '<?xml':
                return cover_data
            if i >= 10:
                logging.info("  |--> Error: can't get cover image")
                print s % (1, 91, "  |--> Error: can't get cover image")
                sys.exit(0)
            i += 1

    def modified_id3(self, file_name, info):
        id3 = ID3()
        id3.add(TRCK(encoding=3, text=info['track']))
        id3.add(TIT2(encoding=3, text=info['song_name']))
        id3.add(TALB(encoding=3, text=info['album_name']))
        id3.add(TPE1(encoding=3, text=info['artist_name']))
        id3.add(COMM(encoding=3, desc=u'Comment', text=info['song_url']))
        id3.add(APIC(encoding=3, mime=u'image/jpg', type=3, desc=u'Cover', data=self.get_cover(info['album_pic_url'])))
        id3.save(file_name)

    def url_parser(self):
        if '/album/' in self.url:
            self.album_id = re.search(r'/album/(\d+)', self.url).group(1)
            print(s % (2, 92, u'\n  -- 正在分析专辑信息 ...'))
            self.get_album_infos()
        elif '/song/' in self.url:
            self.song_id = re.search(r'/song/(\d+)', self.url).group(1)
            print(s % (2, 92, u'\n  -- 正在分析歌曲信息 ...'))
            self.get_song_infos()
        else:
            print(s % (2, 91, u'   请正确输入baidu网址.'))

    def get_song_infos(self):
        logging.info('url -> http://music.baidu.com/song/%s' % self.song_id)
        api_json = self.opener.open(self.template_api % self.song_id).read()
        j = json.loads(api_json)
        song_info = {}
        song_info['song_id'] = unicode(j['data']['songList'][0]['songId'])
        song_info['track'] = u''
        song_info['song_url'] = u'http://music.baidu.com/song/' + song_info['song_id']
        song_info['song_name'] = modificate_text(j['data']['songList'][0]['songName']).strip()
        song_info['album_name'] = modificate_text(j['data']['songList'][0]['albumName']).strip()
        song_info['artist_name'] = modificate_text(j['data']['songList'][0]['artistName']).strip()
        song_info['album_pic_url'] = j['data']['songList'][0]['songPicRadio']
        if args.flac:
            song_info['file_name'] = song_info['song_name'] + ' - ' + song_info['artist_name'] + '.flac'
        else:
            song_info['file_name'] = song_info['song_name'] + ' - ' + song_info['artist_name'] + '.mp3'
        song_info['durl'] = j['data']['songList'][0]['songLink']
        self.song_infos.append(song_info)
        self.download()

    def get_album_infos(self):
        logging.info('url -> http://music.baidu.com/album/%s' % self.album_id)
        songidlist = self.get_songidlist(self.album_id)
        z = z_index(songidlist)
        ii = 1
        for i in songidlist:
            song_info = {}
            song_info['song_id'] = unicode(i['songId'])
            song_info['song_url'] = u'http://music.baidu.com/song/' + song_info['song_id']
            song_info['track'] = unicode(ii)
            song_info['song_name'] = modificate_text(i['songName']).strip()
            song_info['artist_name'] = modificate_text(i['artistName']).strip()
            song_info['album_pic_url'] = i['songPicRadio']
            if args.flac:
                song_info['file_name'] = song_info['track'].zfill(z) + '.' + song_info['song_name'] + ' - ' + song_info['artist_name'] + '.flac'
            else:
                song_info['file_name'] = song_info['track'].zfill(z) + '.' + song_info['song_name'] + ' - ' + song_info['artist_name'] + '.mp3'
            song_info['album_name'] = modificate_text(i['albumName']).strip()
            song_info['durl'] = i['songLink']
            self.song_infos.append(song_info)
            ii += 1
        d = modificate_text(self.song_infos[0]['album_name'] + ' - ' + self.song_infos[0]['artist_name'])
        self.dir_ = os.path.join(os.getcwd().decode('utf8'), d)
        self.download()

    def display_infos(self, i):
        print '\n  ----------------'
        print '  >>', s % (2, 94, i['file_name'])
        print '  >>', s % (2, 95, i['album_name'])
        print '  >>', s % (2, 92, 'http://music.baidu.com/song/%s' % i['song_id'])
        print ''

    def play(self):
        for i in self.song_infos:
            durl = i['durl']
            self.display_infos(i)
            os.system('mpv --really-quiet %s' % durl)
            timeout = 1
            ii, _, _ = select.select([sys.stdin], [], [], timeout)
            if ii:
                sys.exit(0)
            else:
                pass

    def download(self):
        dir_ = modificate_file_name_for_wget(self.dir_)
        cwd = os.getcwd().decode('utf8')
        csongs = len(self.song_infos)
        if dir_ != cwd:
            if not os.path.exists(dir_):
                os.mkdir(dir_)
        print(s % (2, 97, u'\n  >> ' + str(csongs) + u' 首歌曲将要下载.'))
        logging.info('directory: %s' % dir_)
        logging.info('total songs: %d' % csongs)
        ii = 1
        for i in self.song_infos:
            t = modificate_file_name_for_wget(i['file_name'])
            file_name = os.path.join(dir_, t)
            if os.path.exists(file_name):  ## if file exists, no get_durl
                ii += 1
                continue
            file_name_for_wget = file_name.replace('`', '\`')
            if 'zhangmenshiting.baidu.com' in i['durl']:
                num = random.randint(0,100) % 7
                col = s % (2, num + 90, i['file_name'])
                print(u'\n  ++ 正在下载: %s' % col)
                logging.info('  #%d -> %s' % (ii, i['file_name'].encode('utf8')))
                wget = self.template_wgets % (file_name_for_wget, i['durl'])
                wget = wget.encode('utf8')
                status = os.system(wget)
                if status != 0:     # other http-errors, such as 302.
                    wget_exit_status_info = wget_es[status]
                    logging.info('   \\\n                            \\->WARN: status: %d (%s), command: %s' % (status, wget_exit_status_info, wget))
                    print('\n\n ----### \x1b[1;91mERROR\x1b[0m ==> \x1b[1;91m%d (%s)\x1b[0m ###--- \n\n' % (status, wget_exit_status_info))
                    print('  ===> ' + wget)
                    break
                else:
                    os.rename('%s.tmp' % file_name, file_name)

                self.modified_id3(file_name, i)
                ii += 1
                #time.sleep(10)
            else:
                print s % (1, 91, '  !! Oops, you are unlucky, the song is not from zhangmenshiting.baidu.com')

def main(url):
    x = baidu_music(url)
    opener = urllib2.build_opener()
    opener.addheaders = headers.items()
    x.opener = opener
    x.url_parser()
    logging.info('  ########### work is over ###########\n')

if __name__ == '__main__':
    log_file = os.path.join(os.path.expanduser('~'), '.baidu.music.log')
    logging.basicConfig(filename=log_file, level=10, format='%(asctime)s %(message)s')
    print(s % (2, 91, u'程序运行日志在 %s' % log_file))
    p = argparse.ArgumentParser(description='downloading any music.baidu.com')
    p.add_argument('url', help='any url of music.baidu.com')
    p.add_argument('-f', '--flac', action='store_true', help='download flac')
    p.add_argument('-i', '--high', action='store_true', help='download 320')
    p.add_argument('-l', '--low', action='store_true', help='download 128')
    p.add_argument('-p', '--play', action='store_true', \
        help='play with mpv')
    args = p.parse_args()
    main(args.url)

########NEW FILE########
__FILENAME__ = pan.baidu.com
#!/usr/bin/env python2
# vim: set fileencoding=utf8

import os
import sys
import requests
from requests_toolbelt import MultipartEncoder
import urllib
import json
import cPickle as pk
import re
import time
import argparse
import random
import select
import base64
import md5
from zlib import crc32
import StringIO
import signal


username = ''
password = ''


############################################################
# Defines that should never be changed
OneK = 1024
OneM = OneK * OneK
OneG = OneM * OneK
OneT = OneG * OneK
OneP = OneT * OneK
OneE = OneP * OneK

############################################################
# Default values
MinRapidUploadFileSize = 256 * OneK
DefaultSliceSize = 10 * OneM
MaxSliceSize = 2 * OneG
MaxSlicePieces = 1024
ENoError = 0

############################################################
# wget exit status
wget_es = {
    0: "No problems occurred.",
    2: "User interference.",
    1<<8: "Generic error code.",
    2<<8: "Parse error - for instance, when parsing command-line " \
        "optio.wgetrc or .netrc...",
    3<<8: "File I/O error.",
    4<<8: "Network failure.",
    5<<8: "SSL verification failure.",
    6<<8: "Username/password authentication failure.",
    7<<8: "Protocol errors.",
    8<<8: "Server issued an error response."
}
############################################################

s = '\x1b[%d;%dm%s\x1b[0m'       # terminual color template

cookie_file = os.path.join(os.path.expanduser('~'), '.bp.cookies')
upload_datas_path = os.path.join(os.path.expanduser('~'), '.bp.pickle')

headers = {
    "Accept":"text/html,application/xhtml+xml,application/xml; " \
        "q=0.9,image/webp,*/*;q=0.8",
    "Accept-Encoding":"text/html",
    "Accept-Language":"en-US,en;q=0.8,zh-CN;q=0.6,zh;q=0.4,zh-TW;q=0.2",
    "Content-Type":"application/x-www-form-urlencoded",
    "Referer":"http://www.baidu.com/",
    "User-Agent":"Mozilla/5.0 (X11; Linux i686) AppleWebKit/537.36 "\
        "(KHTML, like Gecko) Chrome/32.0.1700.77 Safari/537.36"
}

ss = requests.session()
ss.headers.update(headers)

class panbaiducom_HOME(object):
    def __init__(self, url=''):
        self.path = self.get_path(url)
        self.download = self.play if args.play else self.download
        self.ondup = 'overwrite'

    def init(self):
        def loginandcheck():
            self.login()
            if self.check_login():
                print s % (1, 92, '  -- login success\n')
            else:
                print s % (1, 91, '  !! login fail, maybe username or password is wrong.\n')
                print s % (1, 91, '  !! maybe this app is down.')
                sys.exit(1)

        if os.path.exists(cookie_file):
            t = json.loads(open(cookie_file).read())
            if t.get('user') != None and t.get('user') == username:
                ss.cookies.update(t.get('cookies', t))
                if not self.check_login():
                    loginandcheck()
            else:
                print s % (1, 91, '\n  ++  username changed, then relogin')
                loginandcheck()
        else:
            loginandcheck()

    def get_path(self, url):
        t = re.search(r'path=(.+?)(&|$)', url)
        if t:
            t = t.group(1)
        else:
            t = '/'
        t = urllib.unquote_plus(t)
        return t

    @staticmethod
    def save_img(url, ext):
        path = os.path.join(os.path.expanduser('~'), 'vcode.%s' % ext)
        with open(path, 'w') as g:
            data = urllib.urlopen(url).read()
            g.write(data)
        print "  ++ 验证码已经保存至", s % (1, 91, path)
        input_code = raw_input(s % (2, 92, "  请输入看到的验证码: "))
        return input_code

    def check_login(self):
        print s % (1, 97, '\n  -- check_login')
        url = 'http://www.baidu.com/home/msg/data/personalcontent'
        r = ss.get(url)
        if 'errNo":"0' in r.content:
            print s % (1, 92, '  -- check_login success\n')
            #self.get_dsign()
            self.save_cookies()
            return True
        else:
            print s % (1, 91, '  -- check_login fail\n')
            return False

    def login(self):
        print s % (1, 97, '\n  -- login')

        # Check if we have to deal with verify codes
        params = {
            'tpl': 'pp',
            'callback': 'bdPass.api.login._needCodestringCheckCallback',
            'index': 0,
            'logincheck': '',
            'time': 0,
            'username': username
        }

        # Ask server
        url = 'https://passport.baidu.com/v2/api/?logincheck'
        r = ss.get(url, params=params)
        # Callback for verify code if we need
        #codestring = r.content[r.content.index('(')+1:r.content.index(')')]
        codestring = re.search(r'\((.+?)\)', r.content).group(1)
        codestring = json.loads(codestring)['codestring']
        codestring = codestring if codestring else ""
        url = 'https://passport.baidu.com/cgi-bin/genimage?'+codestring
        verifycode = self.save_img(url, 'gif') if codestring != "" else ""

        # Now we'll do login
        # Get token
        ss.get('http://www.baidu.com')
        t = ss.get('https://passport.baidu.com/v2/api/?getapi&class=login' \
                   '&tpl=pp&tangram=false').text
        token = re.search(r'login_token=\'(.+?)\'', t).group(1)

        # Construct post body
        data = {
            'token': token,
            'ppui_logintime': '1600000',
            'charset':'utf-8',
            'codestring': codestring,
            'isPhone': 'false',
            'index': 0,
            'u': '',
            'safeflg': 0,
            'staticpage': 'http://www.baidu.com/cache/user/html/jump.html',
            'loginType': 1,
            'tpl': 'pp',
            'callback': 'parent.bd__pcbs__qvljue',
            'username': username,
            'password': password,
            'verifycode': verifycode,
            'mem_pass': 'on',
            'apiver': 'v3'
        }

        # Post!
        # XXX : do not handle errors
        url = 'https://passport.baidu.com/v2/api/?login'
        ss.post(url, data=data)

    def save_cookies(self):
        with open(cookie_file, 'w') as g:
            c = {'user': username, 'cookies': ss.cookies.get_dict()}
            g.write(json.dumps(c, indent=4, sort_keys=True))

    def _get_file_list(self, dir_):
        t = {'Referer':'http://pan.baidu.com/disk/home'}
        theaders = headers
        theaders.update(t)

        p = {
            "channel": "chunlei",
            "clienttype": 0,
            "web": 1,
            "num": 10000,   ## max amount of listed file at one page
            "t": int(time.time()*1000),
            "dir": dir_,
            "page": 1,
            #"desc": 1,   ## reversely
            "order": "name", ## sort by name, or size, time
            "_": int(time.time()*1000)
            #"bdstoken": token
        }
        url = 'http://pan.baidu.com/api/list'
        r = ss.get(url, params=p, headers=theaders)
        j = r.json()
        if j['errno'] != 0:
            print s % (1, 91, '  error: get_infos'), '--', j
            sys.exit(1)
        else:
            return j

    def get_infos(self):
        dir_loop = [self.path]
        base_dir = '' if os.path.split(self.path)[0] == '/' \
            else os.path.split(self.path)[0]
        for d in dir_loop:
            j = self._get_file_list(d)
            if j['errno'] == 0 and j['list']:
                if args.type_:
                    j['list'] = [x for x in j['list'] if x['isdir'] \
                        or x['server_filename'][-len(args.type_):] \
                        == unicode(args.type_)]
                total_file = len([i for i in j['list'] if not i['isdir']])
                if args.from_ - 1:
                    j['list'] = j['list'][args.from_-1:] if args.from_ else j['list']
                nn = args.from_
                for i in j['list']:
                    if i['isdir']:
                        dir_loop.append(i['path'].encode('utf8'))
                    else:
                        t = i['path'].encode('utf8')
                        t = t.replace(base_dir, '')
                        t = t[1:] if t[0] == '/' else t
                        t =  os.path.join(os.getcwd(), t)
                        if not i.has_key('dlink'):
                            i['dlink'] = self._get_dlink(i)
                        infos = {
                            'file': t,
                            'dir_': os.path.split(t)[0],
                            'dlink': i['dlink'].encode('utf8'),
                            'name': i['server_filename'].encode('utf8'),
                            'nn': nn,
                            'total_file': total_file
                        }
                        nn += 1
                        self.download(infos)
            elif not j['list']:
                self.path, server_filename = os.path.split(self.path)
                j = self._get_file_list(self.path)
                if j['errno'] == 0 and j['list']:
                    for i in j['list']:
                        if i['server_filename'].encode('utf8') == server_filename:
                            if i['isdir']: break
                            t =  os.path.join(os.getcwd(), server_filename)
                            if not i.has_key('dlink'):
                                i['dlink'] = self._get_dlink(i)
                            infos = {
                                'file': t,
                                'dir_': os.path.split(t)[0],
                                #'dlink': self.get_dlink(i),
                                'dlink': i['dlink'].encode('utf8'),
                                'name': i['server_filename'].encode('utf8')
                            }
                            self.download(infos)
                            break

    def _get_dsign(self):
        url = 'http://pan.baidu.com/disk/home'
        r = ss.get(url)
        html = r.content
        sign1 = re.search(r'sign1="(.+?)";', html).group(1)
        sign3 = re.search(r'sign3="(.+?)";', html).group(1)
        timestamp = re.search(r'timestamp="(.+?)";', html).group(1)

        def sign2(j, r):
            a = []
            p = []
            o = ''
            v = len(j)

            for q in xrange(256):
                a.append(ord(j[q % v]))
                p.append(q)

            u = 0
            for q in xrange(256):
                u = (u + p[q] + a[q]) % 256
                t = p[q]
                p[q] = p[u]
                p[u] = t

            i = 0
            u = 0
            for q in xrange(len(r)):
                i = (i + 1) % 256
                u = (u + p[i]) % 256
                t = p[i]
                p[i] = p[u]
                p[u] = t
                k = p[((p[i] + p[u]) % 256)]
                o += chr(ord(r[q]) ^ k)

            return base64.b64encode(o)

        self.dsign = sign2(sign3, sign1)
        self.timestamp = timestamp

    def _get_dlink(self, i):
        if not hasattr(self, 'dsign'):
            self._get_dsign()

        while True:
            params = {
                "channel": "chunlei",
                "clienttype": 0,
                "web": 1,
                #"bdstoken": token
            }

            data = {
                "sign": self.dsign,
                "timestamp": self.timestamp,
                "fidlist": "[%s]" % i['fs_id'],
                "type": "dlink"
            }

            url = 'http://pan.baidu.com/api/download'
            r = ss.post(url, params=params, data=data)
            j = r.json()
            if j['errno'] == 0:
                dlink = j['dlink'][0]['dlink'].encode('utf8')
                return dlink
            else:
                self._get_dsign()

    @staticmethod
    def download(infos):
        ## make dirs
        if not os.path.exists(infos['dir_']):
            os.makedirs(infos['dir_'])
        else:
            if os.path.exists(infos['file']):
                return 0

        num = random.randint(0, 7) % 7
        col = s % (2, num + 90, infos['file'])
        infos['nn'] = infos['nn'] if infos.get('nn') else 1
        infos['total_file'] = infos['total_file'] if infos.get('total_file') else 1
        print '\n  ++ 正在下载: #', s % (1, 97, infos['nn']), '/', s % (1, 97, infos['total_file']), '#', col

        if args.aria2c:
            if args.limit:
                cmd = 'aria2c -c -x%s -s%s ' \
                    '--max-download-limit %s ' \
                    '-o "%s.tmp" -d "%s" \
                    --user-agent "%s" ' \
                    '--header "Referer:http://pan.baidu.com/disk/home" "%s"' \
                    % (args.aria2c, args.aria2c, args.limit, infos['name'], \
                    infos['dir_'], headers['User-Agent'], infos['dlink'])
            else:
                cmd = 'aria2c -c -x%s -s%s ' \
                    '-o "%s.tmp" -d "%s" --user-agent "%s" ' \
                    '--header "Referer:http://pan.baidu.com/disk/home" "%s"' \
                    % (args.aria2c, args.aria2c, infos['name'], infos['dir_'], headers['User-Agent'], \
                        infos['dlink'])
        else:
            if args.limit:
                cmd = 'wget -c --limit-rate %s ' \
                    '-O "%s.tmp" --user-agent "%s" ' \
                    '--header "Referer:http://pan.baidu.com/disk/home" "%s"' \
                    % (args.limit, infos['file'], headers['User-Agent'], infos['dlink'])
            else:
                cmd = 'wget -c -O "%s.tmp" --user-agent "%s" ' \
                    '--header "Referer:http://pan.baidu.com/disk/home" "%s"' \
                    % (infos['file'], headers['User-Agent'], infos['dlink'])

        status = os.system(cmd)
        if status != 0:     # other http-errors, such as 302.
            wget_exit_status_info = wget_es[status]
            print('\n\n ----###   \x1b[1;91mERROR\x1b[0m ==> '\
                '\x1b[1;91m%d (%s)\x1b[0m   ###--- \n\n' \
                 % (status, wget_exit_status_info))
            print s % (1, 91, '  ===> '), cmd
            sys.exit(1)
        else:
            os.rename('%s.tmp' % infos['file'], infos['file'])

    @staticmethod
    def play(infos):
        num = random.randint(0, 7) % 7
        col = s % (2, num + 90, infos['name'])
        infos['nn'] = infos['nn'] if infos.get('nn') else 1
        infos['total_file'] = infos['total_file'] if infos.get('total_file') else 1
        print '\n  ++ play: #', s % (1, 97, infos['nn']), '/', \
            s % (1, 97, infos['total_file']), '#', col

        if os.path.splitext(infos['file'])[-1].lower() == '.wmv':
            cmd = 'mplayer -really-quiet -cache 8140 ' \
                '-http-header-fields "user-agent:%s" ' \
                '-http-header-fields "Referer:http://pan.baidu.com/disk/home" "%s"' \
                % (headers['User-Agent'], infos['dlink'])
        else:
            cmd = 'mpv --really-quiet --cache 8140 --cache-default 8140 ' \
                '--http-header-fields "user-agent:%s" '\
                '--http-header-fields "Referer:http://pan.baidu.com/disk/home" "%s"' \
                % (headers['User-Agent'], infos['dlink'])

        status = os.system(cmd)
        timeout = 1
        ii, _, _ = select.select([sys.stdin], [], [], timeout)
        if ii:
            sys.exit(0)
        else:
            pass

    def _make_dir(self, dir_):
        t = {'Referer':'http://pan.baidu.com/disk/home'}
        theaders = headers
        theaders.update(t)

        p = {
            "a": "commit",
            "channel": "chunlei",
            "clienttype": 0,
            "web": 1,
            "bdstoken": self.bdstoken
        }
        data = {
            "path": dir_,
            "isdir": 1,
            "size": "",
            "block_list": [],
            "method": "post"
        }
        url = 'http://pan.baidu.com/api/create'
        r = ss.post(url, params=p, data=data, headers=theaders)
        j = r.json()
        if j['errno'] != 0:
            print s % (1, 91, '  !! Error at _make_dir')
            sys.exit(1)

    def _meta(self, file_list):
        p = {
            "channel": "chunlei",
            "app_id": "250528",
            "method": "filemetas",
            "blocks": 1
        }
        data = {'target': json.dumps(file_list)}
        url = 'http://pan.baidu.com/api/filemetas'
        r = ss.post(url, params=p, data=data, verify=False)
        j = r.json()
        if j['errno'] == 0:
            return j
        else:
            return False

    def _rapidupload_file(self, lpath, rpath):
        print '  |-- upload_function:', s % (1, 97, '_rapidupload_file')
        slice_md5 = md5.new(open(lpath, 'rb').read(256 * OneK)).hexdigest()
        with open(lpath, "rb") as f:
            buf = f.read(OneM)
            content_md5 = md5.new()
            content_md5.update(buf)
            crc = crc32(buf).conjugate()
            while True:
                buf = f.read(OneM)
                if buf:
                    crc = crc32(buf, crc).conjugate()
                    content_md5.update(buf)
                else:
                    break
            content_md5 = content_md5.hexdigest()
            content_crc32 = crc.conjugate() & 0xffffffff

        p = {
            "method" : "rapidupload",
            "app_id": "250528",
            "BDUSS": ss.cookies['BDUSS']
        }
        data = {
            "path": os.path.join(rpath, os.path.basename(lpath)),
            "content-length" : self.__current_file_size,
            "content-md5" : content_md5,
            "slice-md5" : slice_md5,
            "content-crc32" : content_crc32,
            "ondup" : self.ondup
        }
        url = 'https://c.pcs.baidu.com/rest/2.0/pcs/file'
        r = ss.post(url, params=p, data=data, verify=False)
        if r.ok:
            return ENoError
        else:
            return r.json()

    def _upload_one_file(self, lpath, rpath):
        print '  |-- upload_function:', s % (1, 97, '_upload_one_file')
        p = {
            "method": "upload",
            "app_id": "250528",
            "ondup": self.ondup,
            "dir": rpath,
            "filename": os.path.basename(lpath),
            "BDUSS": ss.cookies['BDUSS'],
        }
        files = {'file': ('file', open(lpath, 'rb'), '')}
        data = MultipartEncoder(files)
        theaders = headers
        theaders['Content-Type'] = data.content_type
        url = 'https://c.pcs.baidu.com/rest/2.0/pcs/file'
        r = ss.post(url, params=p, data=data, verify=False, headers=theaders)
        if r.ok:
            return ENoError
        else:
            sys.exit(1)


    def _combine_file(self, lpath, rpath):
        p = {
            "method": "createsuperfile",
            "app_id": "250528",
            "ondup": self.ondup,
            "path": os.path.join(rpath, os.path.basename(lpath)),
            "BDUSS": ss.cookies['BDUSS'],
        }
        data = {'param': json.dumps({'block_list': self.upload_datas[lpath]['slice_md5s']})}
        url = 'https://c.pcs.baidu.com/rest/2.0/pcs/file'
        r = ss.post(url, params=p, data=data, verify=False)
        if r.ok:
            return ENoError
        else:
            sys.exit(1)

    def _upload_slice(self):
        p = {
            "method": "upload",
            "app_id": "250528",
            "type": "tmpfile",
            "BDUSS": ss.cookies['BDUSS'],
        }

        file = StringIO.StringIO(self.__slice_block)
        files = {'file': ('file', file, '')}
        data = MultipartEncoder(files)
        theaders = headers
        theaders['Content-Type'] = data.content_type
        url = 'https://c.pcs.baidu.com/rest/2.0/pcs/file'
        r = ss.post(url, params=p, data=data, verify=False, headers=theaders)
        j = r.json()
        if self.__slice_md5 == j['md5']:
            return ENoError
        else:
            return 'MD5Mismatch'

    def _get_pieces_slice(self):
        pieces = MaxSlicePieces
        slice = DefaultSliceSize
        n = 1
        while True:
            t = n * DefaultSliceSize * MaxSlicePieces
            if self.__current_file_size <= t:
                if self.__current_file_size % (n * DefaultSliceSize) == 0:
                    pieces = self.__current_file_size / (n * DefaultSliceSize)
                    slice = n * DefaultSliceSize
                else:
                    pieces = (self.__current_file_size / (n * DefaultSliceSize)) + 1
                    slice = n * DefaultSliceSize
                break
            elif t > MaxSliceSize * MaxSlicePieces:
                n += 1
            else:
                print s % (1, 91, '  !! file is too big, uploading is not supported.')
                sys.exit(1)

        return pieces, slice

    def _get_upload_function(self, rapidupload_is_fall=False):
        if self.__current_file_size > MinRapidUploadFileSize:
            if not rapidupload_is_fall:
                return '_rapidupload_file'
            else:
                if self.__current_file_size <= DefaultSliceSize:
                    return '_upload_one_file'

                elif self.__current_file_size <= MaxSliceSize * MaxSlicePieces:
                    return '_upload_file_slices'
                else:
                    print s % (1, 91, '  !! Error: size of file is too big.')
                    return 'None'
        else:
            return '_upload_one_file'

    def _upload_file(self, lpath, rpath):
        print s % (2, 94, '  ++ uploading:'), lpath

        __current_file_size = os.path.getsize(lpath)
        self.__current_file_size = __current_file_size
        upload_function = self._get_upload_function()

        if self.upload_datas.has_key(lpath):
            if __current_file_size != self.upload_datas[lpath]['size']:
                self.upload_datas[lpath]['is_over'] = False
            self.upload_datas[lpath]['upload_function'] = upload_function
        else:
            self.upload_datas[lpath] = {
                'is_over': False,
                'upload_function': upload_function,
                'size': __current_file_size,
                'remotepaths': set()
            }

        while True:
            if not self.upload_datas[lpath]['is_over']:
                m = self.upload_datas[lpath]['upload_function']
                if m == '_upload_file_slices':
                    time.sleep(2)
                    print '  |-- upload_function:', s % (1, 97, '_upload_file_slices')
                    pieces, slice = self._get_pieces_slice()
                    f = open(lpath, 'rb')
                    current_piece_point = len(self.upload_datas[lpath]['slice_md5s'])
                    f.seek(current_piece_point * slice)
                    for piece in xrange(current_piece_point, pieces):
                        self.__slice_block = f.read(slice)
                        if self.__slice_block:
                            self.__slice_md5 = md5.new(self.__slice_block).hexdigest()
                            while True:
                                result = self._upload_slice()
                                if result == ENoError:
                                    break
                                else:
                                    print s % (1, 91, '  |-- slice_md5 does\'n match, retry.')
                            self.upload_datas[lpath]['slice_md5s'].append(self.__slice_md5)
                            self.save_upload_datas()
                            percent = round(100*((piece + 1.0) / pieces), 2)
                            print s % (1, 97, '  |-- upload: %s%s' % (percent, '%')), piece + 1, '/', pieces
                    result = self._combine_file(lpath, rpath)
                    if result == ENoError:
                        self.upload_datas[lpath]['is_over'] = True
                        self.upload_datas[lpath]['remotepaths'].update([rpath])
                        del self.upload_datas[lpath]['slice_md5s']
                        self.save_upload_datas()
                        print s % (1, 92, '  |-- success.\n')
                        break
                    else:
                        print s % (1, 91, '  !! Error at _combine_file')

                elif m == '_upload_one_file':
                    time.sleep(2)
                    result = self._upload_one_file(lpath, rpath)
                    if result == ENoError:
                        self.upload_datas[lpath]['is_over'] = True
                        self.upload_datas[lpath]['remotepaths'].update([rpath])
                        self.save_upload_datas()
                        print s % (1, 92, '  |-- success.\n')
                        break
                    else:
                        print s % (1, 91, '  !! Error: _upload_one_file is fall, retry.')

                elif m == '_rapidupload_file':
                    time.sleep(2)
                    result = self._rapidupload_file(lpath, rpath)
                    if result == ENoError:
                        self.upload_datas[lpath]['is_over'] = True
                        self.upload_datas[lpath]['remotepaths'].update([rpath])
                        self.save_upload_datas()
                        print s % (1, 92, '  |-- RapidUpload: Success.\n')
                        break
                    else:
                        print s % (1, 93, '  |-- can\'t be RapidUploaded, ' \
                            'now trying normal uploading.')
                        upload_function = self._get_upload_function(rapidupload_is_fall=True)
                        self.upload_datas[lpath]['upload_function'] = upload_function
                        if upload_function == '_upload_file_slices':
                            if not self.upload_datas[lpath].has_key('slice_md5s'):
                                self.upload_datas[lpath]['slice_md5s'] = []

                else:
                    print s % (1, 91, '  !! Error: size of file is too big.')
                    break

            else:
                if args.uploadmode == 'c':
                    if rpath in self.upload_datas[lpath]['remotepaths']:
                        print s % (1, 92, '  |-- file was uploaded.\n')
                        break
                    else:
                        self.upload_datas[lpath]['is_over'] = False
                elif args.uploadmode == 'o':
                    print s % (1, 93, '  |-- reupload.')
                    self.upload_datas[lpath]['is_over'] = False

    def _upload_dir(self, lpath, rpath):
        base_dir = os.path.split(lpath)[0]
        for a, b, c in os.walk(lpath):
            for path in c:
                localpath = os.path.join(a, path)
                t = localpath.replace(base_dir + '/', '')
                t = os.path.split(t)[0]
                remotepath = os.path.join(rpath, t)
                self._upload_file(localpath, remotepath)

    def upload(self, localpath, remotepath):
        lpath = localpath
        if localpath[0] == '~':
            lpath = os.path.expanduser(localpath)
        else:
            lpath = os.path.abspath(localpath)
        rpath = remotepath if remotepath[0] == '/' else '/' + remotepath

        if os.path.exists(lpath):
            pass
        else:
            print s % (1, 91, '  !! Error: localpath doesn\'t exist')
            sys.exit(1)

        self.upload_datas_path = upload_datas_path
        self.upload_datas = {}
        if os.path.exists(self.upload_datas_path):
            f = open(self.upload_datas_path, 'rb')
            upload_datas = pk.load(f)
            if upload_datas:
                self.upload_datas = upload_datas

        if os.path.isdir(lpath):
            self._upload_dir(lpath, rpath)
        elif os.path.isfile(lpath):
            self._upload_file(lpath, rpath)
        else:
            print s % (1, 91, '  !! Error: localpath ?')
            sys.exit(1)

    def save_upload_datas(self):
        f = open(self.upload_datas_path, 'wb')
        pk.dump(self.upload_datas, f)

    ##################################################################
    # for saving shares

    def _share_transfer(self, info):
        meta = self._meta([info['remotepath'].encode('utf8')])
        if not meta:
            self._make_dir(info['remotepath'].encode('utf8'))

        theaders = headers
        theaders.update({'Referer': 'http://pan.baidu.com/share/link?shareid=%s&uk=%s' \
            % (self.shareid, self.uk)})

        p = {
            "channel": "chunlei",
            "clienttype": 0,
            "web": 1,
            "ondup": "overwrite",
            "async": 1,
            "from": self.uk,
            "shareid": self.shareid,
            "bdstoken": self.bdstoken
        }
        data = "path=" + urllib.quote_plus(info['remotepath'].encode('utf8')) + \
            '&' + "filelist=" + urllib.quote_plus('["%s"]' % info['path'].encode('utf8'))

        url = 'http://pan.baidu.com/share/transfer'
        r = ss.post(url, params=p, data=data, headers=theaders, verify=False)
        j = r.json()
        if j['errno'] == 0:
            return ENoError
        else:
            return j['errno']

    def _get_share_list(self, info):
        p = {
            "channel": "chunlei",
            "clienttype": 0,
            "web": 1,
            "num": 10000,
            "dir": info['path'].encode('utf8'),
            "t": int(time.time()*1000),
            "uk": self.uk,
            "shareid": self.shareid,
            #"desc": 1,   ## reversely
            "order": "name", ## sort by name, or size, time
            "_": int(time.time()*1000),
            "bdstoken": self.bdstoken
        }
        url = 'http://pan.baidu.com/share/list'
        r = ss.get(url, params=p)
        j = r.json()
        if j['errno'] != 0:
            print s % (1, 91, '  !! Error at _get_share_list')
            sys.exit(1)
        rpath = '/'.join([info['remotepath'], os.path.split(info['path'])[-1]])
        for x in xrange(len(j['list'])):
            j['list'][x]['remotepath'] = rpath

        return j['list']

    def _get_share_infos(self, url, remotepath, infos):
        r = ss.get(url)
        html = r.content

        self.uk = re.search(r'FileUtils.share_uk="(.+?)"', html).group(1)
        self.shareid = re.search(r'FileUtils.share_id="(.+?)"', html).group(1)
        self.bdstoken = re.search(r'bdstoken="(.+?)"', html).group(1)

        isdirs = [int(x) for x in re.findall(r'\\"isdir\\":\\"(\d)\\"', html)]
        paths = [json.loads('"%s"' % x.replace('\\\\', '\\')) \
            for x in re.findall(r'\\"path\\":\\"(.+?)\\",\\"', html)]
        z = zip(isdirs, paths)
        if not infos:
            infos = [{
                'isdir': x,
                'path': y,
                'remotepath': remotepath if remotepath[-1] != '/' else remotepath[:-1]
            } for x, y in z]

        return infos

    def save_share(self, url, remotepath, infos=None):
        infos = self._get_share_infos(url, remotepath, infos)
        for info in infos:
            print s % (1, 97, '  ++ transfer:'), info['path']
            result = self._share_transfer(info)
            if result == ENoError:
                pass
            elif result == 12:
                print s % (1, 91, '  |-- file had existed.')
                sys.exit()
            elif result == -33:
                if info['isdir']:
                    print s % (1, 93, '  |-- over transferring limit.')
                    infos += self._get_share_list(info)
                else:
                    print s % (1, 91, '  !! Error: can\'t transfer file')
            else:
                print s % (1, 91, '  !! Error at save_share, errno:'), result
                sys.exit(1)

    @staticmethod
    def _secret_or_not(url):
        r = ss.get(url)
        if 'init' in r.url:
            if not args.secret:
                secret = raw_input(s % (2, 92, "  请输入提取密码: "))
            else:
                secret = args.secret
            data = 'pwd=%s' % secret
            url = "%s&t=%d" % (r.url.replace('init', 'verify'), int(time.time()))
            r = ss.post(url, data=data)
            if r.json()['errno']:
                print s % (2, 91, "  !! 提取密码错误\n")
                sys.exit(1)

    #######################################################################
    # for finding files

    def _search(self, keyword, directory):
        p = {
            "channel": "chunlei",
            "clienttype": 0,
            "web": 1,
            "dir": directory if directory else "",
            "key": keyword,
            "recursion": "",
            #"timeStamp": "0.15937364846467972",
            #"bdstoken": ,
        }
        url = 'http://pan.baidu.com/api/search'
        r = ss.get(url, params=p)
        j = r.json()
        if j['errno'] == 0:
            return j['list']
        else:
            print s % (1, 91, '  !! Error at _search')
            sys.exit(1)

    def _find_display(self, info):
        # https://stackoverflow.com/questions/1094841/reusable-library-to-get-human-readable-version-of-file-size
        def sizeof_fmt(num):
            for x in ['','KB','MB','GB']:
                if num < 1024.0:
                    return "%3.1f%s" % (num, x)
                num /= 1024.0
            return "%3.1f%s" % (num, 'TB')

        isdir = s % (1, 93, 'd') if info['isdir'] else s % (1, 97, '-')
        size = s % (1, 91, sizeof_fmt(info['size']).rjust(7))
        path = s % (2, 92, info['path']) if info['isdir'] else info['path']
        template = '  %s %s %s\n' % (isdir, size, path)
        print template

    def find(self, keyword, directory=None):
        infos = self._search(keyword, directory)
        for info in infos:
            self._find_display(info)

    def do(self):
        self.get_infos()

class panbaiducom(object):
    def __init__(self, url):
        self.url = url
        self.infos = {}

    def get_params(self):
        r = ss.get(self.url)
        pattern = re.compile('server_filename="(.+?)";disk.util.ViewShareUtils.bdstoken="(\w+)";'
                             'disk.util.ViewShareUtils.fsId="(\d+)".+?FileUtils.share_uk="(\d+)";'
                             'FileUtils.share_id="(\d+)";.+?FileUtils.share_timestamp="(\d+)";'
                             'FileUtils.share_sign="(\w+)";')
        p = re.search(pattern, r.text)

        self.params = {
            "bdstoken": p.group(2),
            "uk": p.group(4),
            "shareid": p.group(5),
            "timestamp": p.group(6),
            "sign": p.group(7),
            "channel": "chunlei",
            "clienttype": 0,
            "web": 1,
            "channel": "chunlei",
            "clienttype": 0,
            "web": 1
        }

        self.infos.update({
            'name': p.group(1).encode('utf8'),
            'file': os.path.join(os.getcwd(), p.group(1)).encode('utf8'),
            'dir_': os.getcwd(),
            'fs_id': p.group(3).encode('utf8')
            })

    def get_infos(self):
        url = 'http://pan.baidu.com/share/download'
        data = 'fid_list=["%s"]' % self.infos['fs_id']

        while True:
            r = ss.post(url, data=data, params=self.params)
            j = r.json()
            if not j['errno']:
                self.infos['dlink'] = j['dlink'].encode('utf8')
                if args.play:
                    panbaiducom_HOME.play(self.infos)
                else:
                    panbaiducom_HOME.download(self.infos)
                break
            else:
                vcode = j['vcode']
                input_code = panbaiducom_HOME.save_img(j['img'], 'jpg')
                self.params.update({'input': input_code, 'vcode': vcode})

    def get_infos2(self):
        url = self.url

        while True:
            r = ss.get(url)
            j = r.content.replace('\\', '')
            name = re.search(r'server_filename":"(.+?)"', j).group(1)
            dlink = re.search(r'dlink":"(.+?)"', j)
            if dlink:
                self.infos = {
                    'name': name,
                    'file': os.path.join(os.getcwd(), name),
                    'dir_': os.getcwd(),
                    'dlink': dlink.group(1)
                }
                if args.play:
                    panbaiducom_HOME.play(self.infos)
                else:
                    panbaiducom_HOME.download(self.infos)
                break
            else:
                print s % (1, '  !! Error at get_infos2, can\'t get dlink')

    def do(self):
        panbaiducom_HOME._secret_or_not(self.url)
        self.get_params()
        self.get_infos()

    def do2(self):
        self.get_infos2()

def sighandler(signum, frame):
    print s % (1, 91, "  !! Signal %s received, Abort" % signum)
    print s % (1, 91, "  !! Frame: %s" % frame)
    sys.exit(1)

def main(xxx):
    signal.signal(signal.SIGBUS, sighandler)
    signal.signal(signal.SIGHUP, sighandler)
    # https://stackoverflow.com/questions/108183/how-to-prevent-sigpipes-or-handle-them-properly
    signal.signal(signal.SIGPIPE, signal.SIG_IGN)
    signal.signal(signal.SIGQUIT, sighandler)
    signal.signal(signal.SIGSYS, sighandler)

    signal.signal(signal.SIGABRT, sighandler)
    signal.signal(signal.SIGFPE, sighandler)
    signal.signal(signal.SIGILL, sighandler)
    signal.signal(signal.SIGINT, sighandler)
    signal.signal(signal.SIGSEGV, sighandler)
    signal.signal(signal.SIGTERM, sighandler)

    if xxx[0] == 'u' or xxx[0] == 'upload':
        if len(xxx) != 3:
            print s % (1, 91, '  !! 参数错误\n  upload localpath remotepath\n' \
                '  u localpath remotepath')
            sys.exit(1)
        x = panbaiducom_HOME()
        x.init()
        x.upload(xxx[1], xxx[2])
        return

    elif xxx[0] == 'd' or xxx[0] == 'download':
        if len(xxx) < 2:
            print s % (1, 91, '  !! 参数错误\n download url1 url2 ..\n' \
                '  d url1 url2 ..')
            sys.exit(1)
        urls = xxx[1:]
        for url in urls:
            if url[0] == '/':
                url = 'path=%s' % url
            if '/disk/home' in url or 'path' in url:
                x = panbaiducom_HOME(url)
                x.init()
                x.do()
            elif 'baidu.com/pcloud/album/file' in url:
                x = panbaiducom(url)
                x.do2()
            elif 'yun.baidu.com' in url or 'pan.baidu.com' in url:
                url = url.replace('wap/link', 'share/link')
                x = panbaiducom(url)
                x.do()
            else:
                print s % (2, 91, '  !!! url 地址不正确.'), url

    elif xxx[0] == 's' or xxx[0] == 'save':
        if len(xxx) != 3:
            print s % (1, 91, '  !! 参数错误\n save url remotepath\n' \
                ' s url remotepath')
            sys.exit(1)
        x = panbaiducom_HOME(xxx[1])
        x.init()
        remotepath = xxx[2].decode('utf8')
        infos = []
        if x.path != '/':
            infos.append({'isdir': 1, 'path': x.path.decode('utf8'), \
            'remotepath': remotepath if remotepath[-1] != '/' else remotepath[:-1]})
        else:
            infos = None
        url = re.search(r'(http://.+?.baidu.com/.+?)(#|$)', xxx[1]).group(1)
        x._secret_or_not(url)
        x.save_share(url, remotepath, infos=infos)

    elif xxx[0] == 'f' or xxx[0] == 'find':
        if len(xxx) < 2:
            print s % (1, 91, '  !! 参数错误\n find keyword [directory]\n' \
                ' f keyword [directory]')
            sys.exit(1)
        x = panbaiducom_HOME()
        x.init()
        if xxx[-1][0] == '/':
            keyword = ' '.join(xxx[1:-1])
            directory = xxx[-1]
            x.find(keyword, directory)
        else:
            keyword = ' '.join(xxx[1:])
            x.find(keyword)
    else:
        print s % (2, 91, '  !! 命令错误\n')

if __name__ == '__main__':
    p = argparse.ArgumentParser(description='download, upload, play, save from pan.baidu.com')
    p.add_argument('xxx', type=str, nargs='*', \
        help='命令和参数. 用法见 https://github.com/PeterDing/iScript')
    p.add_argument('-a', '--aria2c', action='store', default=None, \
        type=int, help='aria2c分段下载数量')
    p.add_argument('-p', '--play', action='store_true', \
        help='play with mpv')
    p.add_argument('-s', '--secret', action='store', \
        default=None, help='提取密码')
    p.add_argument('-f', '--from_', action='store', \
        default=1, type=int, \
        help='从第几个开始下载，eg: -f 42')
    p.add_argument('-t', '--type_', action='store', \
        default=None, type=str, \
        help='要下载的文件的后缀，eg: -t mp3')
    p.add_argument('-l', '--limit', action='store', \
        default=None, type=str, help='下载速度限制，eg: -l 100k')
    # for upload
    p.add_argument('-m', '--uploadmode', action='store', \
        default='c', type=str, choices=['o', 'c'], \
        help='上传模式: o --> 重传. c --> 续传.')
    args = p.parse_args()
    main(args.xxx)

########NEW FILE########
__FILENAME__ = torrent2magnet
#! /usr/bin/python3

import sys, os, hashlib, urllib.parse, collections

def bencode(elem):
    if type(elem) == str:
        elem = str.encode(elem)
    if type(elem) == bytes:
        result = str.encode(str(len(elem)))+b":"+elem
    elif type(elem) == int:
        result = str.encode("i"+str(elem)+"e")
    elif type(elem) == list:
        result = b"l"
        for item in elem:
            result += bencode(item)
        result += b"e"
    elif type(elem) in [dict, collections.OrderedDict]:
        result = b"d"
        for key in elem:
            result += bencode(key)+bencode(elem[key])
        result += b"e"
    return result

def bdecode(bytestr, recursiveCall=False):
    startingChars = dict({
            b"i" : int,
            b":" : str,
            b"l" : list,
            b"d" : dict
            })
    digits = [b"0", b"1", b"2", b"3", b"4", b"5", b"6", b"7", b"8", b"9"]
    started = ended = False
    curtype = None
    numstring = b"" # for str, int
    result = None   # for list, dict
    key = None      # for dict
    while len(bytestr) > 0:
        # reading and popping from the beginning
        char = bytestr[:1]
        if not started:
            bytestr = bytestr[1:]
            if char in digits:
                numstring += char
            elif char in startingChars:
                started = True
                curtype = startingChars[char]
                if curtype == str:
                    size = int(bytes.decode(numstring))
                    # try to decode strings
                    try:
                        result = bytes.decode(bytestr[:size])
                    except UnicodeDecodeError:
                        result = bytestr[:size]
                    bytestr = bytestr[size:]
                    ended = True
                    break

                elif curtype == list:
                    result = []
                elif curtype == dict:
                    result = collections.OrderedDict()
            else:
                raise ValueError("Expected starting char, got ‘"+bytes.decode(char)+"’")
        else: # if started
            if not char == b"e":
                if curtype == int:
                    bytestr = bytestr[1:]
                    numstring += char
                elif curtype == list:
                    item, bytestr = bdecode(bytestr, recursiveCall=True)
                    result.append(item)
                elif curtype == dict:
                    if key == None:
                        key, bytestr = bdecode(bytestr, recursiveCall=True)
                    else:
                        result[key], bytestr = bdecode(bytestr, recursiveCall=True)
                        key = None
            else: # ending: char == b"e"
                bytestr = bytestr[1:]
                if curtype == int:
                    result = int(bytes.decode(numstring))
                ended = True
                break
    if ended:
        if recursiveCall:
            return result, bytestr
        else:
            return result
    else:
        raise ValueError("String ended unexpectedly")

def torrent2magnet(torrentdic, new_trackers=None):
    result = []

    # add hash info
    if "info" not in torrentdic:
        raise ValueError("No info dict in torrent file")
    encodedInfo = bencode(torrentdic["info"])
    sha1 = hashlib.sha1(encodedInfo).hexdigest()
    result.append("xt=urn:btih:"+sha1)

    # add display name
    #if "name" in torrentdic["info"]:
        #quoted = urllib.parse.quote(torrentdic["info"]["name"], safe="")
        #result.append("dn="+quoted)

    # add trackers list
    #trackers = []
    #if "announce-list" in torrentdic:
        #for urllist in torrentdic["announce-list"]:
            #trackers += urllist
    #elif "announce" in torrentdic:
        #trackers.append(torrentdic["announce"])
    #if new_trackers:
        #trackers += new_trackers

    # eliminate duplicates without sorting
    #seen_urls = []
    #for url in trackers:
        #if [url] not in seen_urls:
            #seen_urls.append([url])
            #quoted = urllib.parse.quote(url, safe="")
            #result.append("tr="+quoted)
    #torrentdic["announce-list"] = seen_urls

    # output magnet or torrent file
    #if output == sys.stdout:
    magnet_link = "magnet:?" + "&".join(result)
    return magnet_link
    #else:
        #out = open(output, 'bw')
        #out.write(bencode.bencode(torrentdic))
        #out.close()

def writer(cwd, i):
    with open(cwd, 'a') as g:
        g.write(i + '\n\n')

def main(directory):
    directory = os.path.abspath(directory)
    cwd = os.path.join(os.getcwd(), 'magnet_links')
    for a, b, c in os.walk(directory):
        for i in c:
            file_ext = os.path.splitext(i)[-1]
            if file_ext == '.torrent':
                file_name = os.path.join(a, i)
                byte_stream  = open(file_name, 'br').read()
                try:
                    torrentdic = bdecode(byte_stream)
                    magnet_link = torrent2magnet(torrentdic)
                    tt = '## ' + i + ':\n' + magnet_link
                    writer(cwd, tt)
                except:
                    pass

if __name__ == '__main__':
    argv = sys.argv
    main(argv[1])

########NEW FILE########
__FILENAME__ = tumblr
#!/usr/bin/env python2
# vim: set fileencoding=utf8

import os
import sys
import re
import json
import requests
import argparse
import random
import multiprocessing
import time
import subprocess

api_key = 'fuiKNFp9vQFvjLNvx4sUwti4Yb5yGutBN4Xh10LXZhhRKjWlV4'

############################################################
# wget exit status
wget_es = {
    0: "No problems occurred.",
    2: "User interference.",
    1<<8: "Generic error code.",
    2<<8: "Parse error - for instance, when parsing command-line " \
        "optio.wgetrc or .netrc...",
    3<<8: "File I/O error.",
    4<<8: "Network failure.",
    5<<8: "SSL verification failure.",
    6<<8: "Username/password authentication failure.",
    7<<8: "Protocol errors.",
    8<<8: "Server issued an error response."
}
############################################################

s = '\x1b[%d;%dm%s\x1b[0m'       # terminual color template

headers = {
    "Accept":"text/html,application/xhtml+xml,application/xml; " \
        "q=0.9,image/webp,*/*;q=0.8",
    "Accept-Encoding":"text/html",
    "Accept-Language":"en-US,en;q=0.8,zh-CN;q=0.6,zh;q=0.4,zh-TW;q=0.2",
    "Content-Type":"application/x-www-form-urlencoded",
    "Referer":"https://api.tumblr.com/console//calls/blog/posts",
    "User-Agent":"Mozilla/5.0 (X11; Linux i686) AppleWebKit/537.36 "\
        "(KHTML, like Gecko) Chrome/32.0.1700.77 Safari/537.36"
}

ss = requests.session()
ss.headers.update(headers)

class tumblr(object):
    def __init__(self, burl):
        self.infos = {'host': re.search(r'http(s|)://(.+?)($|/)', burl).group(2)}
        self.infos['dir_'] = os.path.join(os.getcwd(), self.infos['host'])
        self.processes = int(args.processes)

        if not os.path.exists(self.infos['dir_']):
            os.makedirs(self.infos['dir_'])
            self.json_path = os.path.join(self.infos['dir_'], 'json.json')
            self.offset = 0
            print s % (1, 92, '\n   ## begin'), 'offset = %s' % self.offset
        else:
            self.json_path = os.path.join(self.infos['dir_'], 'json.json')
            if os.path.exists(self.json_path):
                self.offset = json.loads(open(self.json_path).read())['offset'] - 20
                print s % (1, 92, '\n   ## begin'), 'offset = %s' % self.offset
            else:
                self.offset = 0

    def save_json(self):
        with open(self.json_path, 'w') as g:
            g.write(json.dumps({'offset': self.offset}, indent=4, sort_keys=True))

    def get_infos(self, postid=None):
        self.infos['photos'] = []
        self.url = 'http://api.tumblr.com/v2/blog/%s/posts/photo' % self.infos['host']
        params = {
            "offset": self.offset if not postid else "",
            "limit": 20 if not postid else "",
            "type": "photo",
            "filter": "text",
            "tag": args.tag,
            #"id": postid if postid else "",
            "api_key": api_key
        }

        r = None
        while True:
            try:
                r = ss.get(self.url, params=params, timeout=10)
                break
            except Exception as e:
                print s % (1, 91, '  !! Error, ss.get'), e
                time.sleep(5)
        if r.ok:
            j = r.json()
            if j['response']['posts']:
                for i in j['response']['posts']:
                    index = 1
                    for ii in i['photos']:
                        durl = ii['original_size']['url'].encode('utf8')
                        filepath = os.path.join(self.infos['dir_'], '%s_%s.%s' \
                            % (i['id'], index, durl.split('.')[-1]))
                        filename = os.path.split(filepath)[-1]
                        t = {
                            'filepath': filepath,
                            'durl': durl,
                            'filename': filename
                        }
                        index += 1
                        self.infos['photos'].append(t)
            else:
                print s % (1, 92, '\n   --- job over ---')
                sys.exit(0)
        else:
            print s % (1, 91, '\n   !! Error, get_infos')
            print r.status_code, r.content
            sys.exit(1)

    def download(self):
        def run(i):
            #if not os.path.exists(i['filepath']):
            num = random.randint(0, 7) % 7
            col = s % (1, num + 90, i['filepath'])
            print '\n  ++ 正在下载: %s' % col

            cmd = 'wget -c -T 4 -q -O "%s.tmp" ' \
                '--header "Referer: http://www.tumblr.com" ' \
                '--user-agent "%s" "%s"' \
                % (i['filepath'], headers['User-Agent'], i['durl'])

            status = os.system(cmd)
            if status != 0:     # other http-errors, such as 302.
                wget_exit_status_info = wget_es[status]
                print('\n\n ----###   \x1b[1;91mERROR\x1b[0m ==> '\
                    '\x1b[1;91m%d (%s)\x1b[0m   ###--- \n\n' \
                    % (status, wget_exit_status_info))
                print s % (1, 91, '  ===> '), cmd
                sys.exit(1)
            else:
                os.rename('%s.tmp' % i['filepath'], i['filepath'])

        l = [self.infos['photos'][i:i+self.processes] \
            for i in range(len(self.infos['photos']))[::self.processes]]
        for yy in l:
            ppool = []
            for ii in yy:
                if not os.path.exists(ii['filepath']):
                    p = multiprocessing.Process(target=run, args=(ii,))
                    p.start()
                    print p
                    ppool.append(p)

            for p in ppool: p.join()

    def do(self):
        if args.check:
            t = subprocess.check_output('ls "%s" | grep ".tmp"' \
                % self.infos['dir_'], shell=True)
            t = re.findall(r'\d\d\d+', t)
            ltmp = list(set(t))
            for postid in ltmp:
                self.get_infos(postid)
                self.download()
        else:
            while True:
                self.get_infos()
                self.offset += 20
                self.save_json()
                self.download()

if __name__ == '__main__':
    p = argparse.ArgumentParser(description='download from tumblr.com')
    p.add_argument('url', help='url')
    p.add_argument('-p', '--processes', action='store', default=5, \
        help='指定多进程数,默认为5个,最多为20个 eg: -p 20')
    p.add_argument('-c', '--check', action='store_true', \
        help='尝试修复未下载成功的图片')
    p.add_argument('-t', '--tag', action='store', \
                   default=None, type=str, help='下载特定tag的图片, eg: -t beautiful')
    args = p.parse_args()
    url = args.url
    x = tumblr(url)
    x.do()

########NEW FILE########
__FILENAME__ = unzip
#!/usr/bin/env python2
# -*- coding: utf-8 -*-

import os
import sys
import zipfile

print "Processing File " + sys.argv[1]

file = ''
if len(sys.argv) == 3:
    file=zipfile.ZipFile(sys.argv[1],"r")
    file.setpassword(sys.argv[2])
else:
    file=zipfile.ZipFile(sys.argv[1],"r")

for name in file.namelist():
    try:
        utf8name=name.decode('gbk')
        pathname = os.path.dirname(utf8name)
    except:
        utf8name=name
        pathname = os.path.dirname(utf8name)

    print "Extracting " + utf8name
    #pathname = os.path.dirname(utf8name)
    if not os.path.exists(pathname) and pathname != "":
        os.makedirs(pathname)
    data = file.read(name)
    if not os.path.exists(utf8name):
        try:
            fo = open(utf8name, "w")
            fo.write(data)
            fo.close
        except:
            pass
file.close()

########NEW FILE########
__FILENAME__ = xiami
#!/usr/bin/env python2
# vim: set fileencoding=utf8

import re
import sys
import os
import random
import time
import json
import logging
import argparse
import requests
import urllib
import select
from mutagen.id3 import ID3,TRCK,TIT2,TALB,TPE1,APIC,TDRC,COMM,TPOS,USLT
from HTMLParser import HTMLParser

parser = HTMLParser()
s = u'\x1b[%d;%dm%s\x1b[0m'       # terminual color template


email    = ''     # vip账号支持高品质音乐下载
password = ''


#############################################################
# Xiami api for android
#{{{
# url_action_fav = "http://www.xiami.com/app/android/fav?id=%s&type=%s"
# url_action_unfav = "http://www.xiami.com/app/android/unfav?id=%s&type=%s"
# url_album = "http://www.xiami.com/app/android/album?id=%s&uid=%s"
# url_song = "http://www.xiami.com/app/android/song?id=%s&uid=%s"
# url_artist = "http://www.xiami.com/app/android/artist?id=%s"
# url_artist_albums = "http://www.xiami.com/app/android/artist-albums?id=%s&page=%s"
# url_artist_radio = "http://www.xiami.com/app/android/radio-artist?id=%s"
# url_artist_top_song = "http://www.xiami.com/app/android/artist-topsongs?id=%s"
# url_artsit_similars = "http://www.xiami.com/app/android/artist-similar?id=%s"
# url_collect = "http://www.xiami.com/app/android/collect?id=%s&uid=%s"
# url_grade = "http://www.xiami.com/app/android/grade?id=%s&grade=%s"
# url_lib_albums = "http://www.xiami.com/app/android/lib-albums?uid=%s&page=%s"
# url_lib_artists = "http://www.xiami.com/app/android/lib-artists?uid=%s&page=%s"
# url_lib_collects = "http://www.xiami.com/app/android/lib-collects?uid=%s&page=%s"
# url_lib_songs = "http://www.xiami.com/app/android/lib-songs?uid=%s&page=%s"
# url_myplaylist = "http://www.xiami.com/app/android/myplaylist?uid=%s"
# url_myradiosongs = "http://www.xiami.com/app/android/lib-rnd?uid=%s"
# url_playlog = "http://www.xiami.com/app/android/playlog?id=%s&uid=%s"
# url_push_songs = "http://www.xiami.com/app/android/push-songs?uid=%s&deviceid=%s"
# url_radio = "http://www.xiami.com/app/android/radio?id=%s&uid=%s"
# url_radio_categories = "http://www.xiami.com/app/android/radio-category"
# url_radio_similar = "http://www.xiami.com/app/android/radio-similar?id=%s&uid=%s"
# url_rndsongs = "http://www.xiami.com/app/android/rnd?uid=%s"
# url_search_all = "http://www.xiami.com/app/android/searchv1?key=%s"
# url_search_parts = "http://www.xiami.com/app/android/search-part?key=%s&type=%s&page=%s"
#}}}
#############################################################

############################################################
# Xiami api for android
# {{{
url_song = "http://www.xiami.com/app/android/song?id=%s"
url_album = "http://www.xiami.com/app/android/album?id=%s"
url_collect = "http://www.xiami.com/app/android/collect?id=%s"
url_artist_albums = "http://www.xiami.com/app/android/artist-albums?id=%s&page=%s"
url_artist_top_song = "http://www.xiami.com/app/android/artist-topsongs?id=%s"
url_lib_songs = "http://www.xiami.com/app/android/lib-songs?uid=%s&page=%s"
# }}}
############################################################

############################################################
# wget exit status
wget_es = {
    0:"No problems occurred.",
    2:"User interference.",
    1<<8:"Generic error code.",
    2<<8:"Parse error - for instance, when parsing command-line ' \
        'optio.wgetrc or .netrc...",
    3<<8:"File I/O error.",
    4<<8:"Network failure.",
    5<<8:"SSL verification failure.",
    6<<8:"Username/password authentication failure.",
    7<<8:"Protocol errors.",
    8<<8:"Server issued an error response."
}
############################################################

cookie_file = os.path.join(os.path.expanduser('~'), '.Xiami.cookies')

headers = {
    "Accept":"text/html,application/xhtml+xml,application/xml; " \
        "q=0.9,image/webp,*/*;q=0.8",
    "Accept-Encoding":"text/html",
    "Accept-Language":"en-US,en;q=0.8,zh-CN;q=0.6,zh;q=0.4,zh-TW;q=0.2",
    "Content-Type":"application/x-www-form-urlencoded",
    "Referer":"http://www.xiami.com/",
    "User-Agent":"Mozilla/5.0 (X11; Linux i686) AppleWebKit/537.36 "\
        "(KHTML, like Gecko) Chrome/32.0.1700.77 Safari/537.36"
}

ss = requests.session()
ss.headers.update(headers)

############################################################
# Regular Expression Templates
re_disc_description = r'disc (\d+) \[(.+?)\]'
############################################################

def decry(row, encryed_url):
    url = encryed_url
    urllen = len(url)
    rows = int(row)

    cols_base = urllen / rows  # basic column count
    rows_ex = urllen % rows    # count of rows that have 1 more column

    matrix = []
    for r in xrange(rows):
        length = cols_base + 1 if r < rows_ex else cols_base
        matrix.append(url[:length])
        url = url[length:]

    url = ''
    for i in xrange(urllen):
        url += matrix[i % rows][i / rows]

    return urllib.unquote(url).replace('^', '0')

def modificate_text(text):
    text = parser.unescape(text)
    text = re.sub(r'//*', '-', text)
    text = text.replace('/', '-')
    text = text.replace('\\', '-')
    text = re.sub(r'\s\s+', ' ', text)
    return text

def modificate_file_name_for_wget(file_name):
    file_name = re.sub(r'\s*:\s*', u' - ', file_name)    # for FAT file system
    file_name = file_name.replace('?', '')      # for FAT file system
    file_name = file_name.replace('"', '\'')    # for FAT file system
    return file_name

def z_index(song_infos):
    size = len(song_infos)
    z = len(str(size))
    return z

########################################################

class xiami(object):
    def __init__(self, url):
        self.email = email
        self.password = password
        self.url = url
        self.song_infos = []
        self.dir_ = os.getcwd().decode('utf8')
        self.template_wgets = 'wget -c -T 5 -nv -U "%s" -O' \
            % headers['User-Agent'] + ' "%s.tmp" %s'
        self.template_song = 'http://www.xiami.com/song/gethqsong/sid/%s'
        self.template_record = 'http://www.xiami.com/count/playrecord?sid=%s'

        self.showcollect_id = ''
        self.album_id = ''
        self.artist_id = ''
        self.song_id = ''
        self.user_id = ''
        self.cover_id = ''
        self.cover_data = ''

        self.html = ''
        self.disc_description_archives = {}

        self.download = self.play if args.play else self.download

    def init(self):
        def loginandcheck():
            self.login()
            if self.check_login():
                print s % (1, 92, '  -- login success\n')
            else:
                print s % (1, 91, '  !! login fail, maybe username or password is wrong.\n')
                print s % (1, 91, '  !! maybe this app is down.')
                sys.exit(1)

        if os.path.exists(cookie_file):
            t = json.loads(open(cookie_file).read())
            if t.get('user') != None and t.get('user') == email:
                ss.cookies.update(t.get('cookies', t))
                if not self.check_login():
                    loginandcheck()
            else:
                print s % (1, 91, '\n  ++  email changed, then relogin')
                loginandcheck()
        else:
            loginandcheck()

    def check_login(self):
        print s % (1, 97, '\n  -- check_login')
        url = 'http://www.xiami.com/task/signin'
        r = ss.get(url)
        if r.content:
            print s % (1, 92, '  -- check_login success\n')
            self.save_cookies()
            return True
        else:
            print s % (1, 91, '  -- login fail, please check email and password\n')
            return False

    def login(self):
        print s % (1, 97, '\n  -- login')

        #validate = self.get_validate()
        data = {
            'email': self.email,
            'password': self.password,
            #'validate': validate,
            'remember': 1,
            'LoginButton': '登录'
        }

        url = 'http://www.xiami.com/web/login'
        ss.post(url, data=data)

    def get_validate(self):
        url = 'https://login.xiami.com/coop/checkcode?forlogin=1&%s' \
            % int(time.time())
        path = os.path.join(os.path.expanduser('~'), 'vcode.png')
        with open(path, 'w') as g:
            data = ss.get(url).content
            g.write(data)
        print "  ++ 验证码已经保存至", s % (2, 91, path)
        print s % (2, 92, u'  请输入验证码:')
        validate = raw_input()
        return validate

    def save_cookies(self):
        with open(cookie_file, 'w') as g:
            c = {'user': email, 'cookies': ss.cookies.get_dict()}
            g.write(json.dumps(c, indent=4, sort_keys=True))

    def get_durl(self, id_):
        while True:
            try:
                j = ss.get(self.template_song % id_).json()
                t = j['location']
                row = t[0]
                encryed_url = t[1:]
                durl = decry(row, encryed_url)
                return durl
            except Exception as e:
                print s % (1, 91, '   \\\n    \\-- Error, get_durl --'), e
                time.sleep(5)

    def record(self, id_):
        ss.get(self.template_record % id_)

    def get_cover(self, info):
        if info['album_name'] == self.cover_id:
            return self.cover_data
        else:
            self.cover_id = info['album_name']
            while True:
                url = info['album_pic_url']
                try:
                    self.cover_data = ss.get(url).content
                    if self.cover_data[:5] != '<?xml':
                        return self.cover_data
                except Exception as e:
                    print s % (1, 91, '   \\\n   \\-- Error, get_cover --'), e
                    time.sleep(5)

    def get_lyric(self, lyric_url):
        if lyric_url:
            data = ss.get(lyric_url).content
            return data.decode('utf8')
        else:
            return u''

    def get_disc_description(self, album_url, info):
        if not self.html:
            self.html = ss.get(album_url).content
            t = re.findall(re_disc_description, self.html)
            t = dict([(a, modificate_text(parser.unescape(b.decode('utf8')))) for a, b in t])
            self.disc_description_archives = dict(t)
        if self.disc_description_archives.has_key(info['cd_serial']):
            disc_description = self.disc_description_archives[info['cd_serial']]
            return u'(%s)' % disc_description
        else:
            return u''

    def modified_id3(self, file_name, info):
        id3 = ID3()
        id3.add(TRCK(encoding=3, text=info['track']))
        id3.add(TDRC(encoding=3, text=info['year']))
        id3.add(TIT2(encoding=3, text=info['song_name']))
        id3.add(TALB(encoding=3, text=info['album_name']))
        id3.add(TPE1(encoding=3, text=info['artist_name']))
        id3.add(TPOS(encoding=3, text=info['cd_serial']))
        #id3.add(USLT(encoding=3, text=self.get_lyric(info['lyric_url'])))
        #id3.add(TCOM(encoding=3, text=info['composer']))
        #id3.add(WXXX(encoding=3, desc=u'xiami_song_url', text=info['song_url']))
        #id3.add(TCON(encoding=3, text=u'genres'))
        #id3.add(TSST(encoding=3, text=info['sub_title']))
        #id3.add(TSRC(encoding=3, text=info['disc_code']))
        id3.add(COMM(encoding=3, desc=u'Comment', \
            text=u'\n\n'.join([info['song_url'], info['album_description']])))
        id3.add(APIC(encoding=3, mime=u'image/jpeg', type=3, \
            desc=u'Front Cover', data=self.get_cover(info)))
        id3.save(file_name)

    def url_parser(self):
        if '/showcollect/' in self.url:
            self.showcollect_id = re.search(r'/showcollect/id/(\d+)', self.url).group(1)
            print(s % (2, 92, u'\n  -- 正在分析精选集信息 ...'))
            self.download_collect()
        elif '/album/' in self.url:
            self.album_id = re.search(r'/album/(\d+)', self.url).group(1)
            print(s % (2, 92, u'\n  -- 正在分析专辑信息 ...'))
            self.download_album()
        elif '/artist/' in self.url:
            self.artist_id = re.search(r'/artist/(\d+)', self.url).group(1)
            code = raw_input('  >> 输入 a 下载该艺术家所有专辑.\n' \
                '  >> 输入 t 下载该艺术家top 20歌曲.\n  >> ')
            if code == 'a':
                print(s % (2, 92, u'\n  -- 正在分析艺术家专辑信息 ...'))
                self.download_artist_albums()
            elif code == 't':
                print(s % (2, 92, u'\n  -- 正在分析艺术家top20信息 ...'))
                self.download_artist_top_20_songs()
            else:
                print(s % (1, 92, u'  --> Over'))
        elif '/song/' in self.url:
            self.song_id = re.search(r'/song/(\d+)', self.url).group(1)
            print(s % (2, 92, u'\n  -- 正在分析歌曲信息 ...'))
            self.download_song()
        elif '/u/' in self.url:
            self.user_id = re.search(r'/u/(\d+)', self.url).group(1)
            print(s % (2, 92, u'\n  -- 正在分析用户歌曲库信息 ...'))
            self.download_user_songs()
        else:
            print(s % (2, 91, u'   请正确输入虾米网址.'))

    def get_song_info(self, album_description, z, cd_serial_auth, i):
        song_info = {}
        song_info['song_id'] = i['song_id']
        song_info['song_url'] = u'http://www.xiami.com/song/' + i['song_id']
        song_info['track'] = i['track']
        song_info['album_description'] = album_description
        #song_info['lyric_url'] = i['lyric']
        #song_info['sub_title'] = i['sub_title']
        #song_info['composer'] = i['composer']
        #song_info['disc_code'] = i['disc_code']
        #if not song_info['sub_title']: song_info['sub_title'] = u''
        #if not song_info['composer']: song_info['composer'] = u''
        #if not song_info['disc_code']: song_info['disc_code'] = u''
        t = time.gmtime(int(i['gmt_publish']))
        #song_info['year'] = unicode('-'.join([str(t.tm_year), \
            #str(t.tm_mon), str(t.tm_mday)]))
        song_info['year'] = unicode('-'.join([str(t.tm_year), \
            str(t.tm_mon), str(t.tm_mday)]))
        song_info['song_name'] = modificate_text(i['name']).strip()
        song_info['artist_name'] = modificate_text(i['artist_name']).strip()
        song_info['album_pic_url'] = re.sub(r'_\d*\.', '_4.', i['album_logo'])
        song_info['cd_serial'] = i['cd_serial']
        if cd_serial_auth:
            if not args.undescription:
                disc_description = self.get_disc_description(\
                    'http://www.xiami.com/album/%s' % i['album_id'], song_info)
                if u''.join(self.disc_description_archives.values()) != u'':
                    if disc_description:
                        song_info['album_name'] = modificate_text(i['title']).strip() \
                            + ' [Disc-' + song_info['cd_serial'] + '] ' + disc_description
                        file_name = '[Disc-' + song_info['cd_serial'] + '] ' \
                            + disc_description + ' ' + song_info['track'] + '.' \
                            + song_info['song_name'] + ' - ' + song_info['artist_name'] + '.mp3'
                        song_info['file_name'] = file_name
                        #song_info['cd_serial'] = u'1'
                    else:
                        song_info['album_name'] = modificate_text(i['title']).strip() \
                            + ' [Disc-' + song_info['cd_serial'] + ']'
                        file_name = '[Disc-' + song_info['cd_serial'] + '] ' \
                            + song_info['track'] + '.' + song_info['song_name'] \
                            + ' - ' + song_info['artist_name'] + '.mp3'
                        song_info['file_name'] = file_name
                        #song_info['cd_serial'] = u'1'
                else:
                    song_info['album_name'] = modificate_text(i['title']).strip()
                    file_name = '[Disc-' + song_info['cd_serial'] + '] ' \
                        + song_info['track'] + '.' + song_info['song_name'] \
                        + ' - ' + song_info['artist_name'] + '.mp3'
                    song_info['file_name'] = file_name
            else:
                song_info['album_name'] = modificate_text(i['title']).strip()
                file_name = '[Disc-' + song_info['cd_serial'] + '] ' + song_info['track'] \
                    + '.' + song_info['song_name'] + ' - ' + song_info['artist_name'] + '.mp3'
                song_info['file_name'] = file_name

        else:
            song_info['album_name'] = modificate_text(i['title']).strip()
            file_name = song_info['track'].zfill(z) + '.' + song_info['song_name'] \
                + ' - ' + song_info['artist_name'] + '.mp3'
            song_info['file_name'] = file_name
        # song_info['low_mp3'] = i['location']
        return song_info

    def get_song_infos(self, song_id):
        j = ss.get(url_song % song_id).json()
        album_id = j['song']['album_id']
        j = ss.get(url_album % album_id).json()
        t = j['album']['description']
        t = parser.unescape(t)
        t = parser.unescape(t)
        t = re.sub(r'<.+?(http://.+?)".+?>', r'\1', t)
        t = re.sub(r'<.+?>([^\n])', r'\1', t)
        t = re.sub(r'<.+?>(\r\n|)', u'\n', t)
        album_description = re.sub(r'\s\s+', u'\n', t).strip()
        cd_serial_auth = j['album']['songs'][-1]['cd_serial'] > u'1'
        z = 0
        if not cd_serial_auth:
            z = z_index(j['album']['songs'])
        for i in j['album']['songs']:
            if i['song_id'] == song_id:
                song_info = self.get_song_info(album_description, z, cd_serial_auth, i)
                return song_info

    def get_album_infos(self, album_id):
        j = ss.get(url_album % album_id).json()
        t = j['album']['description']
        t = parser.unescape(t)
        t = parser.unescape(t)
        t = re.sub(r'<.+?(http://.+?)".+?>', r'\1', t)
        t = re.sub(r'<.+?>([^\n])', r'\1', t)
        t = re.sub(r'<.+?>(\r\n|)', u'\n', t)
        album_description = re.sub(r'\s\s+', u'\n', t).strip()
        d = modificate_text(j['album']['title'] + ' - ' + j['album']['artist_name'])
        dir_ = os.path.join(os.getcwd().decode('utf8'), d)
        self.dir_ = modificate_file_name_for_wget(dir_)
        cd_serial_auth = j['album']['songs'][-1]['cd_serial'] > u'1'
        z = 0
        if not cd_serial_auth:
            z = z_index(j['album']['songs'])
        song_infos = []
        for i in j['album']['songs']:
            song_info = self.get_song_info(album_description, z, cd_serial_auth, i)
            song_infos.append(song_info)
        return song_infos

    def download_song(self):
        logging.info('url -> http://www.xiami.com/song/%s' % self.song_id)
        song_info = self.get_song_infos(self.song_id)
        print(s % (2, 97, u'\n  >> ' + u'1 首歌曲将要下载.')) \
            if not args.play else ''
        self.song_infos = [song_info]
        logging.info('directory: %s' % os.getcwd())
        logging.info('total songs: %d' % len(self.song_infos))
        self.download()

    def download_album(self):
        logging.info('url -> http://www.xiami.com/album/%s' % self.album_id)
        self.song_infos = self.get_album_infos(self.album_id)
        amount_songs = unicode(len(self.song_infos))
        print(s % (2, 97, u'\n  >> ' + amount_songs + u' 首歌曲将要下载.')) \
            if not args.play else ''
        logging.info('directory: %s' % self.dir_)
        logging.info('total songs: %d' % len(self.song_infos))
        self.download(amount_songs)

    def download_collect(self):
        logging.info('url -> http://www.xiami.com/song/showcollect/id/%s' \
                     % self.showcollect_id)
        j = ss.get(url_collect % self.showcollect_id).json()
        d = modificate_text(j['collect']['name'])
        dir_ = os.path.join(os.getcwd().decode('utf8'), d)
        self.dir_ = modificate_file_name_for_wget(dir_)
        amount_songs = unicode(len(j['collect']['songs']))
        print(s % (2, 97, u'\n  >> ' + amount_songs + u' 首歌曲将要下载.')) \
            if not args.play else ''
        logging.info('directory: %s' % self.dir_)
        logging.info('total songs: %d' % len(j['collect']['songs']))
        n = 1
        for i in j['collect']['songs']:
            song_id = i['song_id']
            song_info = self.get_song_infos(song_id)
            self.song_infos = [song_info]
            self.download(amount_songs, n)
            self.html = ''
            self.disc_description_archives = {}
            n += 1

    def download_artist_albums(self):
        ii = 1
        while True:
            j = ss.get(url_artist_albums % (self.artist_id, str(ii))).json()
            if j['albums']:
                for i in j['albums']:
                    self.album_id = i['album_id']
                    self.download_album()
                    self.html = ''
                    self.disc_description_archives = {}
            else:
                break
            ii += 1

    def download_artist_top_20_songs(self):
        logging.info('url (top20) -> http://www.xiami.com/artist/%s' \
            % self.artist_id)
        j = ss.get(url_artist_top_song % self.artist_id).json()
        d = modificate_text(j['songs'][0]['artist_name'] + u' - top 20')
        dir_ = os.path.join(os.getcwd().decode('utf8'), d)
        self.dir_ = modificate_file_name_for_wget(dir_)
        amount_songs = unicode(len(j['songs']))
        print(s % (2, 97, u'\n  >> ' + amount_songs + u' 首歌曲将要下载.')) \
            if not args.play else ''
        logging.info('directory: %s' % self.dir_)
        logging.info('total songs: %d' % len(j['songs']))
        n = 1
        for i in j['songs']:
            song_id = i['song_id']
            song_info = self.get_song_infos(song_id)
            self.song_infos = [song_info]
            self.download(amount_songs, n)
            self.html = ''
            self.disc_description_archives = {}
            n += 1

    def download_user_songs(self):
        logging.info('url -> http://www.xiami.com/u/%s' % self.user_id)
        dir_ = os.path.join(os.getcwd().decode('utf8'), \
            u'虾米用户 %s 收藏的歌曲' % self.user_id)
        self.dir_ = modificate_file_name_for_wget(dir_)
        logging.info('directory: %s' % self.dir_)
        ii = 1
        n = 1
        while True:
            j = ss.get(url_lib_songs % (self.user_id, str(ii))).json()
            if j['songs']:
                for i in j['songs']:
                    song_id = i['song_id']
                    song_info = self.get_song_infos(song_id)
                    self.song_infos = [song_info]
                    self.download(n)
                    self.html = ''
                    self.disc_description_archives = {}
                    n += 1
            else:
                break
            ii += 1

    def display_infos(self, i):
        print '\n  ----------------'
        print '  >>', s % (2, 94, i['file_name'])
        print '  >>', s % (2, 95, i['album_name'])
        print '  >>', s % (2, 92, 'http://www.xiami.com/song/%s' % i['song_id'])
        if i['durl_is_H']:
            print '  >>', s % (1, 97, '     < High rate >')
        else:
            print '  >>', s % (1, 97, '     < Low rate >')
        print ''

    def get_mp3_quality(self, durl):
        if 'm3.file.xiami.com' in durl:
            return 'H'
        else:
            return 'L'

    def play(self, nnn=None, nn=None):
        for i in self.song_infos:
            self.record(i['song_id'])
            durl = self.get_durl(i['song_id'])
            i['durl_is_H'] = 'm3.file' in durl
            self.display_infos(i)
            os.system('mpv --really-quiet %s' % durl)
            timeout = 1
            ii, _, _ = select.select([sys.stdin], [], [], timeout)
            if ii:
                sys.exit(0)
            else:
                pass

    def download(self, amount_songs=u'1', n=None):
        dir_ = modificate_file_name_for_wget(self.dir_)
        cwd = os.getcwd().decode('utf8')
        if dir_ != cwd:
            if not os.path.exists(dir_):
                os.mkdir(dir_)
        ii = 1
        for i in self.song_infos:
            num = random.randint(0, 100) % 7
            col = s % (2, num + 90, i['file_name'])
            t = modificate_file_name_for_wget(i['file_name'])
            file_name = os.path.join(dir_, t)
            if os.path.exists(file_name):  ## if file exists, no get_durl
                if args.undownload:
                    self.modified_id3(file_name, i)
                    ii += 1
                    continue
                else:
                    ii += 1
                    continue
            file_name_for_wget = file_name.replace('`', '\`')
            if not args.undownload:
                durl = self.get_durl(i['song_id'])
                mp3_quality = self.get_mp3_quality(durl)
                if n == None:
                    print(u'\n  ++ 正在下载: #%s/%s# %s' \
                        % (ii, amount_songs, col))
                    logging.info(u'  #%s/%s [%s] -> %s' \
                        % (ii, amount_songs, mp3_quality, i['file_name']))
                else:
                    print(u'\n  ++ 正在下载: #%s/%s# %s' \
                        % (n, amount_songs, col))
                    logging.info(u'  #%s/%s [%s] -> %s' \
                        % (n, amount_songs, mp3_quality, i['file_name']))
                if mp3_quality == 'L':
                    print s % (1, 91, ' !!! Warning: '), 'gaining LOW quality mp3 link.'
                wget = self.template_wgets % (file_name_for_wget, durl)
                wget = wget.encode('utf8')
                status = os.system(wget)
                if status != 0:     # other http-errors, such as 302.
                    wget_exit_status_info = wget_es[status]
                    logging.info('   \\\n                            \\->WARN: status: ' \
                        '%d (%s), command: %s' % (status, wget_exit_status_info, wget))
                    logging.info('  ########### work is over ###########\n')
                    print('\n\n ----###   \x1b[1;91mERROR\x1b[0m ==> \x1b[1;91m%d ' \
                        '(%s)\x1b[0m   ###--- \n\n' % (status, wget_exit_status_info))
                    print s % (1, 91, '  ===> '), wget
                    sys.exit(1)
                else:
                    os.rename('%s.tmp' % file_name, file_name)

            self.modified_id3(file_name, i)
            ii += 1
            time.sleep(0)

def main(url):
    x = xiami(url)
    x.init()
    x.url_parser()
    logging.info('  ########### work is over ###########\n')

if __name__ == '__main__':
    log_file = os.path.join(os.path.expanduser('~'), '.Xiami.log')
    logging.basicConfig(filename=log_file, format='%(asctime)s %(message)s')
    print(s % (2, 91, u'\n  程序运行日志在 %s' % log_file))
    p = argparse.ArgumentParser(description='downloading any xiami.com')
    p.add_argument('url', help='any url of xiami.com')
    p.add_argument('-p', '--play', action='store_true', \
        help='play with mpv')
    p.add_argument('-d', '--undescription', action='store_true', \
        help='no add disk\'s distribution')
    p.add_argument('-c', '--undownload', action='store_true', \
        help='no download, using to renew id3 tags')
    args = p.parse_args()
    main(args.url)

########NEW FILE########
__FILENAME__ = yunpan.360.cn
#!/usr/bin/env python2
# vim: set fileencoding=utf8

import os
import sys
import requests
import urllib
import json
import re
import time
import argparse
import random
import md5
import select


username = ''
password = ''


############################################################
# wget exit status
wget_es = {
    0: "No problems occurred.",
    2: "User interference.",
    1<<8: "Generic error code.",
    2<<8: "Parse error - for instance, when parsing command-line " \
        "optio.wgetrc or .netrc...",
    3<<8: "File I/O error.",
    4<<8: "Network failure.",
    5<<8: "SSL verification failure.",
    6<<8: "Username/password authentication failure.",
    7<<8: "Protocol errors.",
    8<<8: "Server issued an error response."
}
############################################################

s = '\x1b[%d;%dm%s\x1b[0m'       # terminual color template

cookie_file = os.path.join(os.path.expanduser('~'), '.360.cookies')

headers = {
    "Accept":"text/html,application/xhtml+xml,application/xml; " \
        "q=0.9,image/webp,*/*;q=0.8",
    "Accept-Encoding":"text/html",
    "Accept-Language":"en-US,en;q=0.8,zh-CN;q=0.6,zh;q=0.4,zh-TW;q=0.2",
    "Content-Type":"application/x-www-form-urlencoded",
    "Referer":"http://yunpan.360.cn/",
    "X-Requested-With":"XMLHttpRequest",
    "User-Agent":"Mozilla/5.0 (X11; Linux i686) AppleWebKit/537.36 "\
        "(KHTML, like Gecko) Chrome/32.0.1700.77 Safari/537.36"
}

ss = requests.session()
ss.headers.update(headers)

class yunpan360(object):
    def __init__(self, url=''):
        self.path = self.get_path(url)

    def init(self):
        def loginandcheck():
            self.login()
            if self.check_login():
                print s % (1, 92, '  -- login success\n')
            else:
                print s % (1, 91, '  !! login fail, maybe username or password is wrong.\n')
                print s % (1, 91, '  !! maybe this app is down.')
                sys.exit(1)

        if os.path.exists(cookie_file):
            t = json.loads(open(cookie_file).read())
            if t.get('user') != None and t.get('user') == username:
                ss.cookies.update(t.get('cookies', t))
                if not self.check_login():
                    loginandcheck()
            else:
                print s % (1, 91, '\n  ++  username changed, then relogin')
                loginandcheck()
        else:
            loginandcheck()

    def get_path(self, url):
        url = urllib.unquote_plus(url)
        f = re.search(r'sid=#(.+?)(&|$)', url)
        if f:
            return f.group(1)
        else:
            return '/'

    def check_login(self):
        print s % (1, 97, '\n  -- check_login')
        url = 'http://yunpan.360.cn/user/login?st=774'
        r = ss.get(url)
        self.save_cookies()

        if r.ok:
            print s % (1, 92, '  -- check_login success\n')

            # get apihost
            self.apihost = re.search(r'http://(.+?)/', r.url).group(1).encode('utf8')
            self.save_cookies()
            return True
        else:
            print s % (1, 91, '  -- check_login fail\n')
            return False

    def login(self):
        print s % (1, 97, '\n  -- login')

        # get token
        params = {
            "o": "sso",
            "m": "getToken",
            "func": "QHPass.loginUtils.tokenCallback",
            "userName": username,
            "rand": random.random()
        }
        url = 'https://login.360.cn'
        r = ss.get(url, params=params)
        token = re.search(r'token":"(.+?)"', r.content).group(1)

        # now loin
        params = {
            "o": "sso",
            "m": "login",
            "requestScema": "http",
            "from": "pcw_cloud",
            "rtype": "data",
            "func": "QHPass.loginUtils.loginCallback",
            "userName": username,
            "pwdmethod": 1,
            "isKeepAlive": 0,
            "token": token,
            "captFlag": 1,
            "captId": "i360",
            "captCode": "",
            "lm": 0,
            "validatelm": 0,
            "password": md5.new(password).hexdigest(),
            "r": int(time.time()*1000)
        }
        url = 'https://login.360.cn'
        ss.get(url, params=params)

    def save_cookies(self):
        with open(cookie_file, 'w') as g:
            c = {'user': username, 'cookies': ss.cookies.get_dict()}
            g.write(json.dumps(c, indent=4, sort_keys=True))

    def get_dlink(self, i):
        data = 'nid=%s&fname=%s&' % (i['nid'].encode('utf8'), \
            urllib.quote_plus(i['path'].encode('utf8')))
        apiurl = 'http://%s/file/download' % self.apihost
        r = ss.post(apiurl, data=data)
        j = r.json()
        if j['errno'] == 0:
            dlink = j['data']['download_url'].encode('utf8')
            return dlink

    def fix_json(self, ori):
        # 万恶的 360，返回的json尽然不合法。
        jdata = re.search(r'data:\s*\[.+?\]', ori).group()
        jlist = re.split(r'\}\s*,\s*\{', jdata)
        jlist = [l for l in jlist if l.strip()]
        j = []
        for item in jlist:
            nid = re.search(r',nid: \'(\d+)\'', item)
            path = re.search(r',path: \'(.+?)\',nid', item)
            name = re.search(r'oriName: \'(.+?)\',path', item)
            isdir = 'isDir: ' in item
            if nid:
                t = {
                    'nid': nid.group(1),
                    'path': path.group(1).replace("\\'", "'"),
                    'name': name.group(1).replace("\\'", "'"),
                    'isdir': 1 if isdir else 0
                }
                j.append(t)
        return j

    def get_infos(self):
        apiurl = 'http://%s/file/list' % self.apihost
        data = "type" + "=2" + "&" \
            "t" + "=%s" % random.random() + "&" \
            "order" + "=asc" + "&" \
            "field" + "=file_name" + "&" \
            "path" + "=%s" + "&" \
            "page" + "=0" + "&" \
            "page_size" + "=10000" + "&" \
            "ajax" + "=1"

        dir_loop = [self.path]
        base_dir = os.path.split(self.path[:-1])[0] if self.path[-1] == '/' \
            and self.path != '/' else os.path.split(self.path)[0]
        for d in dir_loop:
            data = data % urllib.quote_plus(d)
            r = ss.post(apiurl, data=data)
            j = self.fix_json(r.text.strip())
            if j:
                if args.type_:
                    j = [x for x in j if x['isdir'] \
                        or x['name'][-len(args.type_):] \
                        == unicode(args.type_)]
                total_file = len([i for i in j if not i['isdir']])
                if args.from_ - 1:
                    j = j[args.from_-1:] if args.from_ else j
                nn = args.from_
                for i in j:
                    if i['isdir']:
                        dir_loop.append(i['path'].encode('utf8'))
                    else:
                        t = i['path'].encode('utf8')
                        t = t.replace(base_dir, '')
                        t = t[1:] if t[0] == '/' else t
                        t =  os.path.join(os.getcwd(), t)
                        infos = {
                            'file': t,
                            'dir_': os.path.split(t)[0],
                            'dlink': self.get_dlink(i),
                            'name': i['name'].encode('utf8'),
                            'apihost': self.apihost,
                            'nn': nn,
                            'total_file': total_file
                        }
                        nn += 1
                        self.download(infos)
            else:
                print s % (1, 91, '  error: get_infos')
                sys.exit(0)

    @staticmethod
    def download(infos):
        #### !!!! 注意：360不支持断点续传

        ## make dirs
        if not os.path.exists(infos['dir_']):
            os.makedirs(infos['dir_'])
        else:
            if os.path.exists(infos['file']):
                return 0

        num = random.randint(0, 7) % 7
        col = s % (2, num + 90, infos['file'])
        infos['nn'] = infos['nn'] if infos.get('nn') else 1
        infos['total_file'] = infos['total_file'] if infos.get('total_file') else 1
        print '\n  ++ 正在下载: #', s % (1, 97, infos['nn']), '/', s % (1, 97, infos['total_file']), '#', col

        cookie = '; '.join(['%s=%s' % (x, y) for x, y in ss.cookies.items()]).encode('utf8')
        if args.aria2c:
            if args.limit:
                cmd = 'aria2c -c -x10 -s10 ' \
                    '--max-download-limit %s ' \
                    '-o "%s.tmp" -d "%s" ' \
                    '--user-agent "%s" ' \
                    '--header "Cookie:%s" ' \
                    '--header "Referer:http://%s/" "%s"' \
                    % (args.limit, infos['name'], infos['dir_'],\
                        headers['User-Agent'], cookie, infos['apihost'], infos['dlink'])
            else:
                cmd = 'aria2c -c -x10 -s10 ' \
                    '-o "%s.tmp" -d "%s" --user-agent "%s" ' \
                    '--header "Cookie:%s" ' \
                    '--header "Referer:http://%s/" "%s"' \
                    % (infos['name'], infos['dir_'], headers['User-Agent'], \
                        cookie, infos['apihost'], infos['dlink'])
        else:
            if args.limit:
                cmd = 'wget -c --limit-rate %s ' \
                    '-O "%s.tmp" --user-agent "%s" ' \
                    '--header "Cookie:%s" ' \
                    '--header "Referer:http://%s/" "%s"' \
                    % (args.limit, infos['file'], headers['User-Agent'], \
                        cookie, infos['apihost'], infos['dlink'])
            else:
                cmd = 'wget -c -O "%s.tmp" --user-agent "%s" ' \
                    '--header "Cookie:%s" ' \
                    '--header "Referer:http://%s/" "%s"' \
                    % (infos['file'], headers['User-Agent'], \
                       cookie, infos['apihost'], infos['dlink'])

        status = os.system(cmd)
        if status != 0:     # other http-errors, such as 302.
            wget_exit_status_info = wget_es[status]
            print('\n\n ----###   \x1b[1;91mERROR\x1b[0m ==> '\
                '\x1b[1;91m%d (%s)\x1b[0m   ###--- \n\n' \
                 % (status, wget_exit_status_info))
            print s % (1, 91, '  ===> '), cmd
            sys.exit(1)
        else:
            os.rename('%s.tmp' % infos['file'], infos['file'])

    def exists(self, filepath):
        pass

    def upload(self, path, dir_):
        pass

    def addtask(self):
        pass

    def do(self):
        self.get_infos()

def main(url):
    x = yunpan360(url)
    x.init()
    x.do()

if __name__ == '__main__':
    p = argparse.ArgumentParser(description='download from yunpan.360.com')
    p.add_argument('url', help='自己的360网盘url')
    p.add_argument('-a', '--aria2c', action='store_true', \
        help='download with aria2c')
    p.add_argument('-p', '--play', action='store_true', \
        help='play with mpv')
    p.add_argument('-f', '--from_', action='store', \
        default=1, type=int, \
        help='从第几个开始下载，eg: -f 42')
    p.add_argument('-t', '--type_', action='store', \
        default=None, type=str, \
        help='要下载的文件的后缀，eg: -t mp3')
    p.add_argument('-l', '--limit', action='store', \
        default=None, type=str, help='下载速度限制，eg: -l 100k')
    args = p.parse_args()
    main(args.url)

########NEW FILE########
