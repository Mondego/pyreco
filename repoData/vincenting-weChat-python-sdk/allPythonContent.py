__FILENAME__ = demo
# coding=utf-8
"""
首先需要在微信公共平台申请帐号 mp.weixin.qq.com
之后才可以使用下事例
"""
__author__ = 'Vincent Ting'

from weChat.client import Client

client = Client(email='xx@gmail.com', password='yourPsw')

#demo  推送文字信息,其中sendto为关注该帐号的某用户的fakeId

client.sendTextMsg('xxxxxxx', 'Hello world')

#demo  推送图片信息,其中sendto为关注该帐号的某用户的fakeId，img为图片的文件路径

client.sendImgMsg('xxxxxxx', 'E:/demo.png')
########NEW FILE########
__FILENAME__ = base
# -*- coding: utf-8 -*-

__author__ = 'Vincent Ting'

import cookielib
import urllib2
import urllib
import json
import poster
import hashlib
import time
import re


class BaseClient(object):
    def __init__(self, email=None, password=None):
        """
        登录公共平台服务器，如果失败将报客户端登录异常错误
        :param email:
        :param password:
        :raise:
        """
        if not email or not password:
            raise ValueError
        self.setOpener()

        url_login = "https://mp.weixin.qq.com/cgi-bin/login?lang=zh_CN"
        m = hashlib.md5(password[0:16])
        m.digest()
        password = m.hexdigest()
        body = (('username', email), ('pwd', password), ('imgcode', ''), ('f', 'json'))
        try:
            msg = json.loads(self.opener.open(url_login, urllib.urlencode(body), timeout=5).read())
        except urllib2.URLError:
            raise ClientLoginException
        if msg['ErrCode'] not in (0, 65202):
            print msg
            raise ClientLoginException
        self.token = msg['ErrMsg'].split('=')[-1]
        time.sleep(1)

    def setOpener(self):
        """
        设置请求头部信息模拟浏览器
        """
        self.opener = poster.streaminghttp.register_openers()
        self.opener.add_handler(urllib2.HTTPCookieProcessor(cookielib.CookieJar()))
        self.opener.addheaders = [('Accept', 'application/json, text/javascript, */*; q=0.01'),
                                  ('Content-Type', 'application/x-www-form-urlencoded; charset=UTF-8'),
                                  ('Referer', 'https://mp.weixin.qq.com/'),
                                  ('Cache-Control', 'max-age=0'),
                                  ('Connection', 'keep-alive'),
                                  ('Host', 'mp.weixin.qq.com'),
                                  ('Origin', 'mp.weixin.qq.com'),
                                  ('X-Requested-With', 'XMLHttpRequest'),
                                  ('User-Agent', 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/30.0.1599.101 Safari/537.36')]

    def _sendMsg(self, sendTo, data):
        """
        基础发送信息的方法
        :param sendTo:
        :param data:
        :return:
        """
        if type(sendTo) == type([]):
            for _sendTo in sendTo:
                self._sendMsg(_sendTo, data)
            return

        self.opener.addheaders += [('Referer', 'http://mp.weixin.qq.com/cgi-bin/singlemsgpage?fromfakeid={0}'
                                               '&msgid=&source=&count=20&t=wxm-singlechat&lang=zh_CN'.format(sendTo))]
        body = {
            'error': 'false',
            'token': self.token,
            'tofakeid': sendTo,
            'ajax': 1}
        body.update(data)
        try:
            msg = json.loads(self.opener.open("https://mp.weixin.qq.com/cgi-bin/singlesend?t=ajax-response&"
                                              "lang=zh_CN", urllib.urlencode(body), timeout=5).read())['msg']
        except urllib2.URLError:
            time.sleep(1)
            return self._sendMsg(sendTo, data)
        print msg
        time.sleep(1)
        return msg

    def _uploadImg(self, img):
        """
        根据图片地址来上传图片，返回上传结果id
        :param img:
        :return:
        """
        params = {'uploadfile': open(img, "rb")}
        data, headers = poster.encode.multipart_encode(params)
        request = urllib2.Request('http://mp.weixin.qq.com/cgi-bin/uploadmaterial?'
                                  'cgi=uploadmaterial&type=2&token={0}&t=iframe-uploadfile&'
                                  'lang=zh_CN&formId=file_from_{1}000'.format(self.token, int(time.time())),
                                  data, headers)
        result = urllib2.urlopen(request)
        find_id = re.compile("\d+")
        time.sleep(1)
        return find_id.findall(result.read())[-1]

    def _delImg(self, file_id):
        """
        根据图片ID来删除图片
        :param file_id:
        """
        self.opener.open('http://mp.weixin.qq.com/cgi-bin/modifyfile?oper=del&lang=zh_CN&t=ajax-response',
                         urllib.urlencode({'fileid': file_id,
                                           'token': self.token,
                                           'ajax': 1}))
        time.sleep(1)

    def _addAppMsg(self, title, content, file_id, digest='', sourceurl=''):
        """
        上传图文消息
        :param title:
        :param content:
        :param file_id:
        :param digest:
        :param sourceurl:
        :return:
        """
        msg = json.loads(self.opener.open(
            'http://mp.weixin.qq.com/cgi-bin/operate_appmsg?token={0}&lang=zh_CN&t=ajax-response&sub=create'.format(
                self.token),
            urllib.urlencode({'error': 'false',
                              'count': 1,
                              'AppMsgId': '',
                              'title0': title,
                              'digest0': digest,
                              'content0': content,
                              'fileid0': file_id,
                              'sourceurl0': sourceurl,
                              'token': self.token,
                              'ajax': 1})).read())
        time.sleep(1)
        return msg['msg'] == 'OK'

    def _getAppMsgId(self):
        """
        获取最新上传id
        :return:
        """
        msg = json.loads(self.opener.open(
            'http://mp.weixin.qq.com/cgi-bin/operate_appmsg?token={0}&lang=zh_CN&sub=list&t=ajax-appmsgs-fileselect&type=10&pageIdx=0&pagesize=10&formid=file_from_{1}000&subtype=3'.format(
                self.token, int(time.time())),
            urllib.urlencode({'token': self.token,
                              'ajax': 1})).read())
        time.sleep(1)
        return msg['List'][0]['appId']

    def _delAppMsg(self, app_msg_id):
        """
        根据id删除图文
        :param app_msg_id:
        """
        print self.opener.open('http://mp.weixin.qq.com/cgi-bin/operate_appmsg?sub=del&t=ajax-response',
                               urllib.urlencode({'AppMsgId': app_msg_id,
                                                 'token': self.token,
                                                 'ajax': 1})).read()
        time.sleep(1)


class ClientLoginException(Exception):
    pass

########NEW FILE########
__FILENAME__ = client
# coding=utf-8
__author__ = 'Vincent Ting'

from base import BaseClient


class Client(BaseClient):
    def sendTextMsg(self, sendTo, content):
        """
        给用户发送文字内容，成功返回True，使用时注意两次发送间隔，不能少于2s
        :param sendTo:
        :param content:
        :return:
        """
        msg = self._sendMsg(sendTo, {
            'type': 1,
            'content': content
        })
        return msg == 'ok'

    def sendImgMsg(self, sendTo, img):
        """
        主动推送图片信息
        :param sendTo:
        :param img:图片文件路径
        :return:
        """
        file_id = self._uploadImg(img)
        msg = self._sendMsg(sendTo, {
            'type': 2,
            'content': '',
            'fid': file_id,
            'fileid': file_id
        })
        self._delImg(file_id)
        return msg == 'ok'

    def sendAppMsg(self, sendTo, title, content, img, digest='', sourceurl=''):
        """
        主动推送图文
        :param sendTo:
        :param title: 标题
        :param content: 正文，允许html
        :param img:
        :param digest: 摘要
        :param sourceurl: 来源地址
        :return:
        """
        file_id = self._uploadImg(img)
        self._addAppMsg(title, content, file_id, digest, sourceurl)
        app_msg_id = self._getAppMsgId()
        msg = self._sendMsg(sendTo, {
            'type': 10,
            'fid': app_msg_id,
            'appmsgid': app_msg_id
        })
        self._delImg(file_id)
        self._delAppMsg(app_msg_id)
        return msg == 'ok'
########NEW FILE########
