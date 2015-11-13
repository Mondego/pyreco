__FILENAME__ = douban
#!/usr/bin/env python
# -*- coding: utf-8 -*-

# this file should rename to douban_fm_lib.py and should only have net functions

import sys, os, time, thread, glib, gobject, datetime
import pickle
import pygst
pygst.require("0.10")
import gst, json, urllib, httplib, contextlib, random, binascii, calendar
from select import select
from Cookie import SimpleCookie
from contextlib import closing 
from dateutil import parser

class PrivateFM(object):
    def __init__ (self, channel):
        self.cache = Cache()
        self.channel = channel
        # todo remove this var
        self.dbcl2 = None
        self.init_cookie()
        self.login()

    def init_cookie(self):
        self.cookie = {}
        cookie = self.cache.get('cookie', {})
        self.merge_cookie(cookie)
    
    def login(self):
        if self.remember_cookie():
            self.login_from_cookie()
        else:
            self.get_user_input_name_pass()
            self.login_from_net(self.username, self.password)

    def get_user_input_name_pass(self):
        self.username = raw_input("请输入豆瓣登录账户：")

        # todo 听说有个可以显示*的
        import getpass
        self.password = getpass.getpass("请输入豆瓣登录密码：")

    def remember_cookie(self):
        return 'dbcl2' in self.cookie and 'bid' in self.cookie

    # todo remove this method
    def login_from_cookie(self):
        dbcl2 = self.cookie['dbcl2'].value
        if dbcl2 and len(dbcl2) > 0:
            self.dbcl2 = dbcl2
            self.uid = self.dbcl2.split(':')[0]
        self.bid = self.cookie['bid'].value

    def login_from_net(self, username, password):
        print u'正在登录...'
        data = {
                'source': 'radio',
                'alias': username, 
                'form_password': password,
                'remember': 'on',
                'task': 'sync_channel_list'
                }
        # the flow of geting captcha should be invisibe to user
        # so, we should only show one message of geting captha image
        captcha_id = self.get_captcha_id()
        captcha = self.get_captcha_solution(captcha_id)
        data['captcha_id'] = captcha_id
        data['captcha_solution'] = captcha
        data = urllib.urlencode(data)

        print 'Login ...'
        with closing(self.get_fm_conn()) as conn:
            headers = self.get_headers_for_request({
                'Origin': 'http://douban.fm',
                'Content-Type': 'application/x-www-form-urlencoded',
            })
            conn.request("POST", "/j/login", data, headers)
            response = conn.getresponse()

            set_cookie = response.getheader('Set-Cookie')
            if not set_cookie is None:
                cookie = SimpleCookie(set_cookie)
                self.save_cookie(cookie)

            body = response.read();
            body = json.loads(body)
            if body['r'] != 0:
                print 'login failed'
                print body['err_msg']
                thread.exit()
                return
            user_info = body['user_info']
            play_record = user_info['play_record']
            print user_info['name'],
            print '累计收听'+str(play_record['played'])+'首',
            print '加红心'+str(play_record['liked'])+'首',
            print '收藏兆赫'+str(play_record['fav_chls_count'])+'个'
            self.login_from_cookie()

    def get_captcha_solution(self, captcha_id):
        self.show_captcha_image(captcha_id)
        c = raw_input('验证码: ')
        return c

    def get_fm_conn(self):
        return httplib.HTTPConnection("douban.fm")

    def show_captcha_image(self, captcha_id):
        with closing(self.get_fm_conn()) as conn:
            path = "/misc/captcha?size=m&id=" + captcha_id

            import cStringIO

            headers = self.get_headers_for_request()

            conn.request("GET", path, None, headers)
            response = conn.getresponse()

            set_cookie = response.getheader('Set-Cookie')
            if not set_cookie is None:
                cookie = SimpleCookie(set_cookie)
                self.save_cookie(cookie)

            if response.status == 200:
                body = response.read()
                from PIL import Image
                f = cStringIO.StringIO(body)
                img = Image.open(f)
                img.show();


    def get_headers_for_request(self, extra = {}):
        headers = {
            'Connection': 'keep-alive',
            'Accept': 'application/json, text/javascript, */*; q=0.01',
            'X-Requested-With': 'XMLHttpRequest',
            'User-Agent': 'Mozilla/5.0 (X11; Linux i686) AppleWebKit/537.36 (KHTML, like Gecko) Ubuntu Chromium/28.0.1500.71 Chrome/28.0.1500.71 Safari/537.36',
            'Referer': 'http://douban.fm/',
            'Accept-Language': 'zh-CN,zh;q=0.8'
        }
        if self.cookie:
            cookie_str = self.get_cookie_for_request()
            headers['Cookie'] = cookie_str
        for key in extra:
            headers[key] = extra[key]
        return headers

    def get_captcha_id(self, path = "/j/new_captcha"):
        with closing(self.get_fm_conn()) as conn:

            headers = self.get_headers_for_request()

            conn.request("GET", path, None, headers)
            response = conn.getresponse()

            set_cookie = response.getheader('Set-Cookie')
            if not set_cookie is None:
                cookie = SimpleCookie(set_cookie)
                self.save_cookie(cookie)

            if response.status == 302:
                print '...'
                redirect_url = response.getheader('location')
                return self.get_captcha_id(redirect_url)
            if response.status == 200:
                body = response.read()
                return body.strip('"')

    def save_cookie(self, cookie):
        self.merge_cookie(cookie)
        self.cache.set('cookie', self.cookie)

    # maybe we should extract a class XcCookie(SimpleCookie)
    # merge(SimpleCookie)
    def merge_cookie(self, cookie):
        for key in cookie:
            expires = cookie[key]['expires']
            if expires:
                expires = parser.parse(expires)
                expires = calendar.timegm(expires.utctimetuple())
                now = time.time()
                if expires > now:
                    self.cookie[key] = cookie[key]
                else:
                    if key in self.cookie:
                        del self.cookie[key]
            else:
                self.cookie[key] = cookie[key]

    # todo XcCookie.get_request_string()
    def get_cookie_for_request(self):
        cookie_segments = []
        for key in self.cookie:
            cookie_segment = key + '="' + self.cookie[key].value + '"'
            cookie_segments.append(cookie_segment)
        return '; '.join(cookie_segments)
  
    def get_params(self, typename=None):
        params = {}
        params['r'] = ''.join(random.sample('0123456789abcdefghijklmnopqrstuvwxyz0123456789', 10))
        params['uid'] = self.uid
        params['channel'] = self.channel
        params['from'] = 'mainsite'
        if typename is not None:
            params['type'] = typename
        return params

    def communicate(self, params):
        data = urllib.urlencode(params)
        with closing(httplib.HTTPConnection("douban.fm")) as conn:
            conn.request('GET', "/j/mine/playlist?"+data, None, self.get_headers_for_request())
            result = conn.getresponse().read()
            return result

    def playlist(self):
        print 'Fetching playlist ...'
        params = self.get_params('n')
        result = self.communicate(params)
        result = json.loads(result)
        if result.has_key('logout') and result['logout'] == 1:
            print 'need relogin'
            self.get_user_input_name_pass()
            self.login_from_net(self.username, self.password)
            return self.playlist()
        else:
            return result['song']
     
    def del_song(self, sid, aid):
        params = self.get_params('b')
        params['sid'] = sid
        params['aid'] = aid
        result = self.communicate(params)
        return json.loads(result)['song']

    def fav_song(self, sid, aid):
        params = self.get_params('r')
        params['sid'] = sid
        params['aid'] = aid
        self.communicate(params)

    def unfav_song(self, sid, aid):
        params = self.get_params('u')
        params['sid'] = sid
        params['aid'] = aid
        self.communicate(params)

class Cache:
    """docstring for cache"""
    def has(self, name):
        file_name = self.get_cache_file_name(name)
        return os.path.exists(file_name)

    def get(self, name, default = None):
        file_name = self.get_cache_file_name(name)
        if not os.path.exists(file_name):
            return default
        cache_file = open(file_name, 'rb')
        content = pickle.load(cache_file)
        cache_file.close()
        return content

    def set(self, name, content):
        file_name = self.get_cache_file_name(name)
        cache_file = open(file_name, 'wb')
        pickle.dump(content, cache_file)
        cache_file.close()

    def get_cache_file_name(self, name):
        # file should put into a `cache` dir
        return name + '.cache'


########NEW FILE########
__FILENAME__ = doubanfm
#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys, os, time, thread, glib, gobject, re
import pickle, ConfigParser
import pygst
pygst.require("0.10")
import gst, json, urllib, urllib2, httplib, contextlib, random, binascii
from select import select
from Cookie import SimpleCookie
from contextlib import closing
import douban

class DoubanFM_CLI:
    def __init__(self):
        config = ConfigParser.SafeConfigParser({
            'interval': '0',
            'pre_set_channel': 'False',
            'pre_set_channel_id': '0'})
        config.read('doubanfm.config')
        self.delay_after_every_song = config.getfloat('DEFAULT', 'interval')

        if config.getboolean('DEFAULT', 'pre_set_channel'):
            self.channel = str(config.getint('DEFAULT', 'pre_set_channel_id'))
        else:
            Channel().show()
            self.channel = raw_input('请输入您想听的频道数字:')

        self.skip_mode = False
        self.user = None
        self.username = ''
        if self.channel == '0' or self.channel == '-3':
            self.private = True
        else:
            self.private = False
        self.player = gst.element_factory_make("playbin", "player")
        self.pause = False
        bus = self.player.get_bus()
        bus.add_signal_watch()
        bus.connect("message", self.on_message)
        self.ch = 'http://douban.fm/j/mine/playlist?type=p&sid=&channel='+self.channel

    def on_message(self, bus, message):
        t = message.type
        if t == gst.MESSAGE_EOS:
            self.player.set_state(gst.STATE_NULL)
            self.playmode = False
        elif t == gst.MESSAGE_ERROR:
            self.player.set_state(gst.STATE_NULL)
            err, debug = message.parse_error()
            print "Error: %s" % err, debug
            self.playmode = False

    def get_songlist(self):
        if self.user:
            self.songlist = self.user.playlist()
        elif self.private:
            self.user = douban.PrivateFM(self.channel)
            self.songlist = self.user.playlist()
        else:
            self.songlist = json.loads(urllib.urlopen(self.ch).read())['song']

    def control(self,r):
        rlist, _, _ = select([sys.stdin], [], [], 1)
        if rlist:
            s = sys.stdin.readline().rstrip()
            if s:
                if s == 'n':
                    print '下一首...'
                    self.skip_mode = True
                    return 'next'
                elif s == 'f' and self.private:
                    print '正在加心...'
                    self.user.fav_song(r['sid'], r['aid'])
                    print "加心成功:)\n"
                    return 'fav'
                elif s == 'd' and self.private:
                    print '不再收听...'
                    self.songlist = self.user.del_song(r['sid'], r['aid'])
                    print "删歌成功:)\n"
                    return 'del'
                elif s == 'p' and not self.pause:
                    print '已暂停...'
                    print '输入p以恢复播放\n'
                    return 'pause'
                elif s == 'r' and self.pause:
                    print '恢复播放...'
                    print '继续享受美妙的音乐吧:)\n'
                    return 'resume'
                else:
                    print '错误的操作，请重试\n'

    def start(self, loop):
        self.get_songlist()
        is_first_song = True
        for r in self.songlist:
            song_uri = r['url']
            self.playmode = True

            if not is_first_song and not self.skip_mode:
                if self.delay_after_every_song > 0:
                    print '-'
                    time.sleep(self.delay_after_every_song)
            self.skip_mode = False
            is_first_song = False

            print u'正在播放： '+r['title']+u'     歌手： '+r['artist'],
            if int(r['like']) == 1:
                print u'    ♥\n'
            else:
                print '\n'

            self.player.set_property("uri", song_uri) # when ads, flv, warning print
            self.player.set_state(gst.STATE_PLAYING)
            while self.playmode:
                c = self.control(r)
                if c == 'next' or c == 'del':
                    self.player.set_state(gst.STATE_NULL)
                    self.playmode = False
                    break
                elif c == 'pause':
                    self.pause = True
                    self.player.set_state(gst.STATE_PAUSED)
                elif c == 'resume':
                    self.pause = False
                    self.player.set_state(gst.STATE_PLAYING)

        loop.quit()


class Channel:

    def __init__(self):
        cid = "101" # why cid is 101 ?
        self.url = "http://douban.fm/j/explore/channel_detail?channel_id=" + cid
        self.init_info()

    def init_info(self):
        cache = douban.Cache()
        if cache.has('channel'):
            self.info = cache.get('channel')
        else:
            self.info = {
                    0: "私人",
                    -3: "红心"
                }
            self.get_id_and_name()
            cache.set('channel', self.info)

    def get_id_and_name(self):
        print '获取频道列表…\n'
        # this var should name to text or string or something
        self.html = urllib2.urlopen(self.url).read()
        chls = json.loads(self.html)["data"]["channel"]["creator"]["chls"]
        for chl in chls:
            id = chl["id"]
            name = chl["name"]
            self.info[id] = name

    def show(self):
        print u'频道列表：'
        for i in sorted(self.info.iterkeys()):
            print("%8s %s" % (i, self.info[i]))

def main():
    print u'豆瓣电台'
    doubanfm = DoubanFM_CLI()

    print u"\r\n\t跳过输入n，加心输入f，删歌输入d，暂停输入p\r\n"
    # print u"\r\n\t跳过输入n(ext)，加心输入f(avorite)，删歌输入d(elete)，暂停输入p(ause)\r\n"

    while 1:
        loop = glib.MainLoop()
        thread.start_new_thread(doubanfm.start, (loop,))
        gobject.threads_init()
        loop.run()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print "再见！"

########NEW FILE########
