__FILENAME__ = example
# coding=utf-8

from __future__ import with_statement
from PyWapFetion import Fetion, send2self, send
# 仅作参考，详细了解请参考源码

# 快速发送：
send2self('手机号',  '密码', '信息')
send('手机号', '密码', '接收方手机号', '信息')

#----------------------------------------------------------------------
myfetion = Fetion('手机号', '密码')

myfetion.changestatus('0')  # 改变在线状态

myfetion.send2self('发给自己的东西')
myfetion.findid('输入手机号，返回飞信ID')
myfetion.sendBYid('飞信ID', '消息')
myfetion.send('手机号', '消息', sm=True)  # 发送飞信信息
# 通过设定sm=True强制发送短信（sm=ShortMessage）
myfetion.send('昵称', '消息')  # 你也可以这么干
myfetion.addfriend('手机号', '你的昵称（5字以内）')
myfetion.send(['手机号1', '手机号2', '这就是传说中的群发'], '消息')
  # 成功返回True，失败返回False

myfetion.send2self('这个是发给自己的定时短信', time='201111201120')
'''发送定时短信。格式：年月日小时分钟
如：2011年11月20日11时14分：201111201144
    2012年11月11日11时11分：201211111111
注意：时间允许范围：当前时刻向后10分钟-向后1年
如：当前时间：2011年11月20日 11:17
有效时间范围是:2011年11月20日11:27分到2012年11月20日11:27分
'''

myfetion.changeimpresa('改签名')
myfetion.alive()  # 保持在线，10分钟以上无操作会被判定为离线
# 如果你想要自动保持在线，那么：
from PyWapFetion.AliveKeeper import AliveKeeper
AliveKeeper(myfetion)

myfetion.deletefriend('要删除的好友ID')
myfetion.addblacklist('要拉黑的好友ID')
myfetion.relieveblack('要解除拉黑的好友ID')

myfetion.logout()
# -----------------------------------------------------------------------

with Fetion('手机号', '密码') as f:  # 其实你也可以用with，这样更方便一点
    f.send2self('xxxx')

########NEW FILE########
__FILENAME__ = AliveKeeper
#coding=utf-8
from threading import Thread
from time import sleep

__all__ = ['AliveKeeper']


class AliveKeeper(Thread):
    def __init__(self, fetion, sleeptime=240, Daemon=True, start=True):
        self.fetion = fetion
        super(Thread, self).__init__()
        self.sleeptime = sleeptime
        self.setDaemon(Daemon)
        if start:
            self.start()

    def run(self):
        while '登陆' not in self.fetion.open('im/index/indexcenter.action'):
            sleep(self.sleeptime)

########NEW FILE########
__FILENAME__ = Cache
#coding=utf-8
from __future__ import with_statement
from marshal import dump, load

__all__ = ['Cache']


class Cache(object):
    def __init__(self, path):
        self.path = path
        try:
            with open(path, 'rb') as f:
                self.dict = load(f)
        except:
            self.dict = {}

    __getitem__ = get = lambda self, k: self.dict.get(k)
    __setitem__ = lambda self, k, id: self.dict.__setitem__(k, id)
    __delitem__ = pop = lambda self, k: self.dict.pop(k, None)
    __del__ = save = lambda self: dump(self.dict, open(self.path, 'wb'))

########NEW FILE########
__FILENAME__ = Errors
#coding=utf-8


class FetionNotYourFriend(Exception):
    pass


class FetionCsrfTokenFail(Exception):
    pass


class FetionLoginFail(Exception):
    pass
########NEW FILE########
__FILENAME__ = Fetion
#coding=utf-8

import os
import time
import json
from PyWapFetion.Errors import *
from re import compile
from PyWapFetion.Cache import Cache
from gzip import GzipFile

try:
    from http.cookiejar import MozillaCookieJar
    from urllib.request import Request, build_opener
    from urllib.request import HTTPHandler, HTTPCookieProcessor
    from urllib.parse import urlencode
    from io import StringIO
except ImportError:
    # Python 2
    input = raw_input
    from cookielib import MozillaCookieJar
    from urllib2 import Request, build_opener, HTTPHandler, HTTPCookieProcessor
    from urllib import urlencode

    try:
        from cStringIO import StringIO
    except ImportError:
        from StringIO import StringIO
    IS_PY2 = True
else:
    IS_PY2 = False

idfinder = compile('touserid=(\d*)')
idfinder2 = compile('name="internalid" value="(\d+)"')
csrf_token = compile('<postfield name="csrfToken" value="(\w+)"/>')

__all__ = ['Fetion']


class Fetion(object):
    def __init__(self, mobile, password=None, status='0',
                 cachefile='Fetion.cache', cookiesfile=''):
        '''登录状态：
        在线：400 隐身：0 忙碌：600 离开：100
        '''
        if cachefile:
            self.cache = Cache(cachefile)

        if not cookiesfile:
            cookiesfile = '%s.cookies' % mobile

        cookiejar = MozillaCookieJar(filename=cookiesfile)
        if not os.path.isfile(cookiesfile):
            open(cookiesfile, 'w').write(MozillaCookieJar.header)

        cookiejar.load(filename=cookiesfile)

        cookie_processor = HTTPCookieProcessor(cookiejar)

        self.opener = build_opener(cookie_processor,
                                   HTTPHandler)
        self.mobile, self.password = mobile, password
        if not self.alive():
            self._login()
            cookiejar.save()

        self.changestatus(status)

    def send2self(self, message, time=None):
        if time:
            htm = self.open('im/user/sendTimingMsgToMyselfs.action',
                            {'msg': message, 'timing': time})
        else:
            htm = self.open('im/user/sendMsgToMyselfs.action',
                            {'msg': message})
        return '成功' in htm

    def send(self, mobile, message, sm=False):
        if mobile == self.mobile:
            return self.send2self(message)
        return self.sendBYid(self.findid(mobile), message, sm)

    def addfriend(self, mobile, name='xx'):
        htm = self.open('im/user/insertfriendsubmit.action',
                        {'nickname': name, 'number': mobile, 'type': '0'})
        return '成功' in htm

    def alive(self):
        htm = self.open('im/index/indexcenter.action')
        return '心情' in htm or '正在登录' in htm

    def deletefriend(self, id):
        htm = self.open('im/user/deletefriendsubmit.action?touserid=%s' % id)
        return '删除好友成功!' in htm

    def changestatus(self, status='0'):
        url = 'im5/index/setLoginStatus.action?loginstatus=' + status
        for x in range(2):
            htm = self.open(url)
        return 'success' in htm

    def logout(self, *args):
        self.opener.open('http://f.10086.cn/im/index/logoutsubmit.action')

    __enter__ = lambda self: self
    __exit__ = __del__ = logout

    def _login(self):
        '''登录
        若登录成功，返回True
        若登录失败，抛出FetionLoginFail异常
        注意：此函数可能需要从标准输入中读取验证码
        '''
        data = {
            'm': self.mobile,
            'pass': self.password,
        }
        htm = self.open('/im5/login/loginHtml5.action', data)
        resp = json.loads(htm)
        if resp.get('checkCodeKey', 'false') == 'true':
            request = Request('http://f.10086.cn/im5/systemimage/verifycode%d.jpeg' % time.time())
            img = self.opener.open(request).read()
            with open('verifycode.jpeg', 'wb') as verifycodefile:
                verifycodefile.write(img)

            captchacode = input('captchaCode:')
            data['captchaCode'] = captchacode
            htm = self.open('/im5/login/loginHtml5.action', data)
            resp = json.loads(htm)

        if resp['loginstate'] == '200':
            return True
        else:
            raise FetionLoginFail(resp['tip'])

    def sendBYid(self, id, message, sm=False):
        url = 'im/chat/sendShortMsg.action?touserid=%s' % id
        if sm:
            url = 'im/chat/sendMsg.action?touserid=%s' % id
        htm = self.open(url,
                        {'msg': message, 'csrfToken': self._getcsrf(id)})
        if '对方不是您的好友' in htm:
            raise FetionNotYourFriend
        return '成功' in htm

    def _getid(self, mobile):
        htm = self.open('im/index/searchOtherInfoList.action',
                        {'searchText': mobile})
        try:
            return idfinder.findall(htm)[0]
        except IndexError:
            try:
                return idfinder2.findall(htm)[0]
            except:
                return None
        except:
            return None

    def findid(self, mobile):
        if hasattr(self, 'cache'):
            id = self.cache[mobile]
            if not id:
                self.cache[mobile] = id = self._getid(mobile)
            return id
        return self._getid(mobile)

    def open(self, url, data=''):
        data = urlencode(data)
        if not IS_PY2:
            data = data.encode()

        request = Request('http://f.10086.cn/%s' % url, data=data)
        htm = self.opener.open(request).read()
        try:
            htm = GzipFile(fileobj=StringIO(htm)).read()
        finally:
            if IS_PY2:
                return htm
            else:
                return htm.decode()

    def _getcsrf(self, id=''):
        if hasattr(self, 'csrf'):
            return self.csrf
        url = ('im/chat/toinputMsg.action?touserid=%s&type=all' % id)
        htm = self.open(url)
        try:
            self.csrf = csrf_token.findall(htm)[0]
            return self.csrf
        except IndexError:
            print(htm)
            raise FetionCsrfTokenFail

########NEW FILE########
