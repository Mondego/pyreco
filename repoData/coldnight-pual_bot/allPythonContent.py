__FILENAME__ = command
#!/usr/bin/env python
# -*- coding:utf-8 -*-
#
#   Author  :   cold
#   E-mail  :   wh_linux@126.com
#   Date    :   14/01/16 12:18:53
#   Desc    :   相应基本命令插件
#
import time

from datetime import datetime

from plugins import BasePlugin


class CommandPlugin(BasePlugin):

    def uptime(self):
        up_time = datetime.fromtimestamp(self.webqq.start_time)\
            .strftime("%H:%M:%S")
        now = time.time()

        sub = int(now - self.webqq.start_time)
        num, unit, oth = None, None, ""
        if sub < 60:
            num, unit = sub, "sec"
        elif sub > 60 and sub < 3600:
            num, unit = sub / 60, "min"
        elif sub > 3600 and sub < 86400:
            num = sub / 3600
            unit = ""
            num = "{0}:{1}".format("%02d" % num,
                                   ((sub - (num * 3600)) / 60))
        elif sub > 86400:
            num, unit = sub / 84600, "days"
            h = (sub - (num * 86400)) / 3600
            m = (sub - ((num * 86400) + h * 3600)) / 60
            if h or m:
                oth = ", {0}:{1}".format(h, m)

        return "{0} up {1} {2} {3}, handled {4} message(s)"\
            .format(up_time, num, unit, oth, self.webqq.msg_num)

    def is_match(self, from_uin, content, type):
        ABOUT_STR = u"\nAuthor    :   cold\nE-mail    :   wh_linux@126.com\n"\
            u"HomePage  :   http://t.cn/zTocACq\n"\
            u"Project@  :   http://git.io/hWy9nQ"
        HELP_DOC = u"\n====命令列表====\n"\
            u"help         显示此信息\n"\
            u"ping         确定机器人是否在线\n"\
            u"about        查看关于该机器人项目的信息\n"\
            u">>> [代码]   执行Python语句\n"\
            u"-w [城市]    查询城市今明两天天气\n"\
            u"-tr [单词]   中英文互译\n"\
            u"-pm25 [城市] 查询城市当天PM2.5情况等\n"\
            u"====命令列表===="
        ping_cmd = "ping"
        about_cmd = "about"
        help_cmd = "help"
        commands = [ping_cmd, about_cmd, help_cmd, "uptime"]
        command_resp = {ping_cmd: u"小的在", about_cmd: ABOUT_STR,
                        help_cmd: HELP_DOC,
                        "uptime": self.uptime}

        if content.encode("utf-8").strip().lower() in commands:
            body = command_resp[content.encode("utf-8").strip().lower()]
            if not isinstance(body, (str, unicode)):
                body = body()
            self.body = body
            return True

    def handle_message(self, callback):
        callback(self.body)

########NEW FILE########
__FILENAME__ = douban
#!/usr/bin/env python
# -*- coding:utf-8 -*-
#
#   Author  :   cold
#   E-mail  :   wh_linux@126.com
#   Date    :   14/01/20 10:33:47
#   Desc    :   爬取豆瓣书籍/电影/歌曲信息
#
from bs4 import BeautifulSoup

try:
    from plugins import BasePlugin
except:
    BasePlugin = object

class DoubanReader(object):
    def __init__(self, http):
        self.http = http
        self.url = "http://www.douban.com/search"

    def search(self, name, callback):
        params = {"q":name.encode("utf-8")}
        self.http.get(self.url, params, callback = self.parse_html,
                      kwargs = {"callback":callback})

    def parse_html(self, response, callback):
        soup = BeautifulSoup(response.body)
        item = soup.find(attrs = {"class":"content"})
        if item:
            try:
                type = item.find("span").text
                a = item.find('a')
                name = a.text
                href = a.attrs["href"]
                rating = item.find(attrs = {"class":"rating_nums"}).text
                cast = item.find(attrs={"class":"subject-cast"}).text
                desc = item.find("p").text
            except AttributeError:
                callback(u"没有找到相关信息")
                return

            if type == u"[电影]":
                cast_des = u"原名/导演/主演/年份" if len(cast.split("/")) == 4\
                        else u"导演/主演/年份"
            elif type == u"[书籍]":
                cast_des = u"作者/译者/出版社/年份" if len(cast.split("/")) == 4\
                        else u"作者/出版社/年份"
            body = u"{0}{1}:\n"\
                    u"评分: {2}\n"\
                    u"{3}: {4}\n"\
                    u"描述: {5}\n"\
                    u"详细信息: {6}\n"\
                    .format(type, name, rating, cast_des, cast, desc, href)
        else:
            body = u"没有找到相关信息"

        callback(body)


class DoubanPlugin(BasePlugin):
    douban = None
    def is_match(self, from_uin, content, type):
        if (content.startswith("<") and content.endswith(">")) or\
           (content.startswith(u"《") and content.endswith(u"》")):
            self._name = content.strip("<").strip(">").strip(u"《")\
                    .strip(u"》")

            if not self._name.strip():
                return False

            if self.douban is None:
                self.douban = DoubanReader(self.http)
            return True
        return False


    def handle_message(self, callback):
        self.douban.search(self._name, callback)

if __name__ == "__main__":
    from tornadohttpclient import TornadoHTTPClient
    def cb(b):
        print b
    douban = DoubanReader(TornadoHTTPClient())
    douban.search(u"百年孤独", cb)
    douban.search(u"鸟哥的私房菜", cb)
    douban.search(u"论语", cb)
    douban.search(u"寒战", cb)
    douban.search(u"阿凡达", cb)
    douban.search(u"创战记", cb)
    douban.search(u"简单爱", cb)
    TornadoHTTPClient().start()

########NEW FILE########
__FILENAME__ = lisp
#!/usr/bin/env python
# -*- coding:utf-8 -*-
#
#   Author  :   cold
#   E-mail  :   wh_linux@126.com
#   Date    :   14/01/22 14:13:23
#   Desc    :   调用接口实现运行Lisp程序
#
import re
import logging

from plugins import BasePlugin

logger = logging.getLogger("plugin")

class LispPlugin(BasePlugin):
    url = "http://www.compileonline.com/execute_new.php"
    result_p = re.compile(r'<pre>(.*?)</pre>', flags = re.U|re.M|re.S)

    def is_match(self, from_uin, content, type):
        if content.startswith("(") and content.endswith(")"):
            self._code = content
            return True
        return False

    def handle_message(self, callback):
        params = {"args":"", "code":self._code.encode("utf-8"),
                  "inputs":"", "lang":"lisp", "stdinput":""}
        def read(resp):
            logger.info(u"Lisp request success, result: {0}".format(resp.body))
            result = self.result_p.findall(resp.body)
            result = "" if not result else result[0]
            callback(result)
        self.http.post(self.url, params, callback = read)

########NEW FILE########
__FILENAME__ = paste
#!/usr/bin/env python
# -*- coding:utf-8 -*-
#
#   Author  :   cold
#   E-mail  :   wh_linux@126.com
#   Date    :   14/01/16 12:13:09
#   Desc    :   粘贴代码插件
#
from plugins import BasePlugin

class PastePlugin(BasePlugin):
    code_typs = ['actionscript', 'ada', 'apache', 'bash', 'c', 'c#', 'cpp',
            'css', 'django', 'erlang', 'go', 'html', 'java', 'javascript',
            'jsp', 'lighttpd', 'lua', 'matlab', 'mysql', 'nginx',
            'objectivec', 'perl', 'php', 'python', 'python3', 'ruby',
            'scheme', 'smalltalk', 'smarty', 'sql', 'sqlite3', 'squid',
            'tcl', 'text', 'vb.net', 'vim', 'xml', 'yaml']

    def is_match(self, from_uin, content, type):
        if content.startswith("```"):
            typ = content.split("\n")[0].lstrip("`").strip().lower()
            self.ctype =  typ if typ in self.code_typs else "text"
            self.code = "\n".join(content.split("\n")[1:])
            return True
        return False

    def paste(self, code, callback, ctype = "text"):
        """ 贴代码 """
        params = {'vimcn':code.encode("utf-8")}
        url = "http://p.vim-cn.com/"

        self.http.post(url, params, callback = self.read_paste,
                       kwargs = {"callback":callback, "ctype":ctype})


    def read_paste(self, resp, callback, ctype="text"):
        """ 读取贴代码结果, 并发送消息 """
        if resp.code == 200:
            content = resp.body.strip().rstrip("/") + "/" + ctype
        elif resp.code == 400:
            content = u"内容太短, 不需要贴!"
        else:
            content = u"没贴上, 我也不知道为什么!"

        callback(content)


    def handle_message(self, callback):
        self.paste(self.code, callback, self.ctype)

########NEW FILE########
__FILENAME__ = pm25
#!/usr/bin/env python
# -*- coding:utf-8 -*-
#
#   Author  :   cold
#   E-mail  :   wh_linux@126.com
#   Date    :   14/01/16 16:15:59
#   Desc    :   PM2.5 查询插件
#
""" 代码贡献自 EricTang (汤勺), 由 cold 整理
"""
from ._pinyin import PinYin
from bs4 import BeautifulSoup

from plugins import BasePlugin


PM25_URL = 'http://www.pm25.in/'

class PM25Plugin(BasePlugin):
    def is_match(self, from_uin, content, type):
        if content.startswith("-pm25"):
            self.city = content.split(" ")[1]
            self._format = u"\n {0}" if type == "g" else u"{0}"
            return True
        return False

    def handle_message(self, callback):
        self.getPM25_by_city(self.convert2pinyin(self.city), callback)

    def getPM25_by_city(self, city, callback):
        """
        根据城市查询PM25值
        """
        self._city = city.encode("utf-8")
        if city:
            url = PM25_URL + city.encode("utf-8")
            self.http.get(url, callback = self.callback,
                          kwargs = {"callback":callback})
        else:
            callback(u'没输入城市你让我查个头啊...')

    def callback(self, resp, callback):
        html_doc = resp.body
        soup = BeautifulSoup(html_doc)
        #美丽的汤获取的数组，找到城市的PM25
        city_air_data_array = soup.find_all(attrs = {'class':'span12 data'})

        #获取数据更新时间
        city_aqi_update_array = \
                str(soup.find_all(attrs = {'class':'live_data_time'})[0])\
                .replace('<div class="live_data_time">\n','')

        city_aqi_update_time = city_aqi_update_array.replace('</div>', '').strip()
        city_aqi_update_time = city_aqi_update_time.replace('<p>', '')
        city_aqi_update_time = city_aqi_update_time.replace('</p>', '')


        #获取城市名
        target_city = "h2"
        city_name_str = str(soup.find_all(target_city)[0])\
                .replace('<%s>' % target_city,'')
        city_name = city_name_str.replace('</%s>' % target_city,'').strip()

        #获取城市空气质量
        target_city_aqi = "h4"
        city_aqi_str = str(soup.find_all(target_city_aqi)[0])\
                .replace('<%s>' % target_city_aqi,'')
        city_aqi = city_aqi_str.replace('</%s>' % target_city_aqi,'').strip()


        #获取城市各项指标的数据值，切割
        city_data_array = str(city_air_data_array[0]).strip()\
                .split('<div class="span1">\n')
        city_data_array.remove('<div class="span12 data">\n')
        city_data_array = [x.replace('<div class="value">\n','').strip()
                           for x in city_data_array]
        city_data_array = [x.replace('<div class="caption">\n','').strip()
                           for x in city_data_array]
        city_data_array = [x.replace('</div>\n</div>','').strip()
                           for x in city_data_array]
        city_data_array = [x.replace('</div>\n','').strip()
                           for x in city_data_array]
        city_data_array = [x.replace('\n','').strip()
                           for x in city_data_array]
        city_data_array = [x.lstrip().rstrip()
                           for x in city_data_array]
        city_data_array.pop()

        city_air_status_str=u"当前查询城市为：{0}，空气质量为：{1}\n{2}\n"\
                u"{3}\n点击链接查看完整空气质量报告:{4}{5}"\
                .format (city_name.decode("utf-8"), city_aqi.decode("utf-8"),
                         "\n".join(city_data_array).decode("utf-8"),
                         city_aqi_update_time.decode("utf-8"), PM25_URL,
                         self._city)

        callback(city_air_status_str)

    def convert2pinyin(self, words):
        """
        将中文转换为拼音
        """
        if words:
            pinyin = PinYin()
            pinyin.load_word()
            pinyin_array=pinyin.hanzi2pinyin(string=words)
            return "".join(pinyin_array)
        else:
            return ''

########NEW FILE########
__FILENAME__ = pyshell
#!/usr/bin/env python
# -*- coding:utf-8 -*-
#
#   Author  :   cold
#   E-mail  :   wh_linux@126.com
#   Date    :   14/01/16 12:29:39
#   Desc    :   Python 在线 Shell 插件
#
import config

from plugins.paste import PastePlugin

class PythonShellPlugin(PastePlugin):
    def is_match(self, from_uin, content, type):
        if content.startswith(">>>"):
            body = content.lstrip(">").lstrip(" ")
            bodys = []
            for b in body.replace("\r\n", "\n").split("\n"):
                bodys.append(b.lstrip(">>>"))
            self.body = "\n".join(bodys)
            self.from_uin = from_uin
            return True
        return False

    def handle_message(self, callback):
        self.shell(callback)

    def shell(self, callback):
        """ 实现Python Shell
        Arguments:
            `callback`  -   发送结果的回调
        """
        if self.body.strip() in ["cls", "clear"]:
            url = "http://pythonec.appspot.com/drop"
            params = [("session", self.from_uin),]
        else:
            url = "http://pythonec.appspot.com/shell"
            #url = "http://localhost:8080/shell"
            params = [("session", self.from_uin),
                    ("statement", self.body.encode("utf-8"))]

        def read_shell(resp):
            data = resp.body
            if not data:
                data = "OK"
            if len(data) > config.MAX_LENGTH:
                return self.paste(data, callback, "")

            if data.count("\n") > 10:
                data.replace("\n", " ")

            callback(data.decode("utf-8"))
            return

        self.http.get(url, params, callback = read_shell)

########NEW FILE########
__FILENAME__ = simsimi
#!/usr/bin/env python
# -*- coding:utf-8 -*-
#
#   Author  :   cold
#   E-mail  :   wh_linux@126.com
#   Date    :   14/01/16 11:33:32
#   Desc    :   SimSimi插件
#
import json

from tornadohttpclient import TornadoHTTPClient

import config

from plugins import BasePlugin


class SimSimiTalk(object):
    """ 模拟浏览器与SimSimi交流

    :params http: HTTP 客户端实例
    :type http: ~tornadhttpclient.TornadoHTTPClient instance
    """
    def __init__(self, http = None):
        self.http = http or TornadoHTTPClient()

        if not http:
            self.http.set_user_agent("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Ubuntu Chromium/28.0.1500.71 Chrome/28.0.1500.71 Safari/537.36")
            self.http.debug = getattr(config, "TRACE", False)
            self.http.validate_cert = False
            self.http.set_global_headers({"Accept-Charset": "UTF-8,*;q=0.5"})

        self.url = "http://www.simsimi.com/func/reqN"
        self.params = {"lc":"zh", "ft":0.0}
        self.ready = False

        self.fetch_kwargs = {}
        if config.SimSimi_Proxy:
            self.fetch_kwargs.update(proxy_host = config.SimSimi_Proxy[0],
                                     proxy_port = config.SimSimi_Proxy[1])

        self._setup_cookie()

    def _setup_cookie(self):
        self.http.get("http://www.simsimi.com", callback=self._set_profile)

    def _set_profile(self, resp):
        def callback(resp):
            self.ready = True
        params = {"name": "PBot", "uid": "52125598"}
        headers = {"Referer":"http://www.simsimi.com/set_profile_frameview.htm",
                   "Accept":"application/json, text/javascript, */*; q=0.01",
                   "Accept-Language":"zh-cn,en_us;q=0.7,en;q=0.3",
                   "Content-Type":"application/json; charset=utf-8",
                   "X-Requested-With":"XMLHttpRequest",
                   "Cookie": "simsimi_uid=52125598"}
        self.http.post("http://www.simsimi.com/func/setProfile", params,
                       headers=headers, callback=callback)


    def talk(self, msg, callback):
        """ 聊天

        :param msg: 信息
        :param callback: 接收响应的回调
        """
        headers = {"Referer":"http://www.simsimi.com/talk_frameview.htm",
                   "Accept":"application/json, text/javascript, */*; q=0.01",
                   "Accept-Language":"zh-cn,en_us;q=0.7,en;q=0.3",
                   "Content-Type":"application/json; charset=utf-8",
                   "X-Requested-With":"XMLHttpRequest",
                   "Cookie": "simsimi_uid=52125598"}
        if not msg.strip():
            return callback(u"小的在")
        params = {"req":msg.encode("utf-8")}
        params.update(self.params)

        def _talk(resp):
            data = {}
            if resp.body:
                try:
                    data = json.loads(resp.body)
                except ValueError:
                    pass
            print resp.body
            callback(data.get("sentence_resp", "Server respond nothing!"))

        self.http.get(self.url, params, headers = headers,
                      callback = _talk)


class SimSimiPlugin(BasePlugin):
    simsimi = None

    def is_match(self, form_uin, content, type):
        if not getattr(config, "SimSimi_Enabled", False):
            return False
        else:
            self.simsimi = SimSimiTalk()

        if type == "g":
            if content.startswith(self.nickname.lower().strip()) or \
               content.endswith(self.nickname.lower().strip()):
                self.content = content.strip(self.nickname)
                return True
        else:
            self.content = content
            return True
        return False

    def handle_message(self, callback):
        self.simsimi.talk(self.content, callback)


if __name__ == "__main__":
    import threading,time
    simsimi = SimSimiTalk()
    def callback(response):
        print response
        simsimi.http.stop()

    def talk():
        while 1:
            if simsimi.ready:
                simsimi.talk("nice to meet you", callback)
                break
            else:
                time.sleep(1)

    t = threading.Thread(target = talk)
    t.setDaemon(True)
    t.start()
    simsimi.http.start()

########NEW FILE########
__FILENAME__ = translate
#!/usr/bin/env python
# -*- coding:utf-8 -*-
#
#   Author  :   cold
#   E-mail  :   wh_linux@126.com
#   Date    :   14/01/16 12:23:34
#   Desc    :   翻译插件
#
import json
import traceback

import config

from plugins import BasePlugin

class TranslatePlugin(BasePlugin):
    def is_match(self, from_uin, content, type):
        if content.startswith("-tr"):
            web = content.startswith("-trw")
            self.is_web = web
            self.body = content.lstrip("-trw" if web else "-tr").strip()
            return True
        return False

    def handle_message(self, callback):
        key = config.YOUDAO_KEY
        keyfrom = config.YOUDAO_KEYFROM
        source = self.body.encode("utf-8")
        url = "http://fanyi.youdao.com/openapi.do"
        params = [("keyfrom", keyfrom), ("key", key),("type", "data"),
                  ("doctype", "json"), ("version",1.1), ("q", source)]
        self.http.get(url, params, callback = self.read_result,
                      kwargs = {"callback":callback})

    def read_result(self, resp, callback):
        web = self.is_web
        try:
            result = json.loads(resp.body)
        except ValueError:
            self.logger.warn(traceback.format_exc())
            body = u"error"
        else:
            errorCode = result.get("errorCode")
            if errorCode == 0:
                query = result.get("query")
                r = " ".join(result.get("translation"))
                basic = result.get("basic", {})
                body = u"{0}\n{1}".format(query, r)
                phonetic = basic.get("phonetic")
                if phonetic:
                    ps = phonetic.split(",")
                    if len(ps) == 2:
                        pstr = u"读音: 英 [{0}] 美 [{1}]".format(*ps)
                    else:
                        pstr = u"读音: {0}".format(*ps)
                    body += u"\n" + pstr

                exp = basic.get("explains")
                if exp:
                    body += u"\n其他释义:\n\t{0}".format(u"\n\t".join(exp))

                if web:
                    body += u"\n网络释义:\n"
                    web = result.get("web", [])
                    if web:
                        for w in web:
                            body += u"\t{0}\n".format(w.get("key"))
                            vs = u"\n\t\t".join(w.get("value"))
                            body += u"\t\t{0}\n".format(vs)

            if errorCode == 50:
                body = u"无效的有道key"

        if not body:
            body = u"没有结果"

        callback(body)

########NEW FILE########
__FILENAME__ = url_reader
#!/usr/bin/env python
# -*- coding:utf-8 -*-
#
#   Author  :   cold
#   E-mail  :   wh_linux@126.com
#   Date    :   14/01/16 12:00:06
#   Desc    :   读取URL信息(标题)插件
#
import re

from plugins import BasePlugin

from _linktitle import get_urls, fetchtitle

class URLReaderPlugin(BasePlugin):
    URL_RE = re.compile(r"(http[s]?://(?:[-a-zA-Z0-9_]+\.)+[a-zA-Z]+(?::\d+)"
                        "?(?:/[-a-zA-Z0-9_%./]+)*\??[-a-zA-Z0-9_&%=.]*)",
                        re.UNICODE)

    def is_match(self, from_uin, content, type):
        urls = get_urls(content)
        if urls:
            self._urls = urls
            return True
        return False

    def handle_message(self, callback):
        fetchtitle(self._urls, callback)

########NEW FILE########
__FILENAME__ = weather
#!/usr/bin/env python
# -*- coding:utf-8 -*-
#
#   Author  :   cold
#   E-mail  :   wh_linux@126.com
#   Date    :   14/01/16 15:59:20
#   Desc    :   天气
#
""" 代码贡献自 EricTang (汤勺), 由 cold 整理
"""

from xml.dom.minidom import parseString

from plugins import BasePlugin

#weather service url address
WEATHER_URL = 'http://www.webxml.com.cn/webservices/weatherwebservice.asmx/getWeatherbyCityName'

class WeatherPlugin(BasePlugin):
    def is_match(self, from_uin, content, type):
        if content.startswith("-w"):
            self.city = content.split(" ")[1]
            self._format = u"\n {0}" if type == "g" else u"{0}"
            return True
        return False


    def handle_message(self, callback):
        self.get_weather(self.city, callback)

    def get_weather(self, city, callback):
        """
        根据城市获取天气
        """
        if city:
            params = {"theCityName":city.encode("utf-8")}
            self.http.get(WEATHER_URL, params, callback = self.callback,
                          kwargs = {"callback":callback})
        else:
            callback(self._format.foramt(u"缺少城市参数"))

    def callback(self, resp, callback):
        #解析body体
        document = ""
        for line in resp.body.split("\n"):
            document = document + line

        dom = parseString(document)

        strings = dom.getElementsByTagName("string")

        temperature_of_today = self.getText(strings[5].childNodes)
        weather_of_today = self.getText(strings[6].childNodes)

        temperature_of_tomorrow = self.getText(strings[12].childNodes)
        weather_of_tomorrow = self.getText(strings[13].childNodes)

        weatherStr = u"今明两天%s的天气状况是: %s %s ; %s %s;" % \
                (self.city, weather_of_today, temperature_of_today,
                 weather_of_tomorrow, temperature_of_tomorrow)

        callback(self._format.format(weatherStr))


    def getText(self, nodelist):
        """
        获取所有的string字符串string标签对应的文字
        """
        rc = ""
        for node in nodelist:
            if node.nodeType == node.TEXT_NODE:
                rc = rc + node.data
        return rc


########NEW FILE########
__FILENAME__ = _fetchtitle
#!/usr/bin/env python
#-*- coding: utf8 -*-
#  Author: lilydjwg (https://github.com/lilydjwg)
#  Source: https://github.com/lilydjwg/winterpy/blob/master/pylib/mytornado/fetchtitle.py
#  由 cold (https://github.com/coldnight) 添加 Python2 支持
# vim:fileencoding=utf-8

import re
import socket
try:
    from urllib.parse import urlsplit, urljoin
    py3 = True
except ImportError:
    from urlparse import urlsplit, urljoin  # py2
    py3 = False

from functools import partial
from collections import namedtuple
import struct
import json
import logging
import encodings.idna
try:
  # Python 3.3
  from html.entities import html5 as _entities
  def _extract_entity_name(m):
    return m.group()[1:]
except ImportError:
    try:
        from html.entities import entitydefs as _entities
    except ImportError:
        from htmlentitydefs import entitydefs as _entities # py2

    def _extract_entity_name(m):
        return m.group()[1:-1]

import tornado.ioloop
import tornado.iostream

# try to import C parser then fallback in pure python parser.
try:
    from http_parser.parser import HttpParser
except ImportError:
    try:
        from http_parser.pyparser import HttpParser
    except ImportError:
        from HTMLParser import HTMLParser as HttpParser  # py2

UserAgent = 'FetchTitle/1.2 (wh_linux@126.com)'
class SingletonFactory:
  def __init__(self, name):
    self.name = name
  def __repr__(self):
    return '<%s>' % self.name

MediaType = namedtuple('MediaType', 'type size dimension')
defaultMediaType = MediaType('application/octet-stream', None, None)

ConnectionClosed = SingletonFactory('ConnectionClosed')
TooManyRedirection = SingletonFactory('TooManyRedirection')
Timeout = SingletonFactory('Timeout')

logger = logging.getLogger(__name__)

def _sharp2uni(code):
  '''&#...; ==> unicode'''
  s = code[1:].rstrip(';')
  if s.startswith('x'):
    return chr(int('0'+s, 16))
  else:
    return chr(int(s))

def _mapEntity(m):
  name = _extract_entity_name(m)
  if name.startswith('#'):
    return _sharp2uni(name)
  try:
    return _entities[name]
  except KeyError:
    return '&' + name

def replaceEntities(s):
  return re.sub(r'&[^;]+;', _mapEntity, s)

class ContentFinder:
  buf = b''
  def __init__(self, mediatype):
    self._mt = mediatype

  @classmethod
  def match_type(cls, mediatype):
    ctype = mediatype.type.split(';', 1)[0]
    if hasattr(cls, '_mime') and cls._mime == ctype:
      return cls(mediatype)
    if hasattr(cls, '_match_type') and cls._match_type(ctype):
      return cls(mediatype)
    return False

class TitleFinder(ContentFinder):
  found = False
  title_begin = re.compile(b'<title[^>]*>', re.IGNORECASE)
  title_end = re.compile(b'</title\s*>', re.IGNORECASE)
  pos = 0

  default_charset = 'UTF-8'
  meta_charset = re.compile(br'<meta\s+http-equiv="?content-type"?\s+content="?[^;]+;\s*charset=([^">]+)"?\s*/?>|<meta\s+charset="?([^">/"]+)"?\s*/?>', re.IGNORECASE)
  charset = None

  @staticmethod
  def _match_type(ctype):
    return ctype.find('html') != -1

  def __init__(self, mediatype):
    ctype = mediatype.type
    pos = ctype.find('charset=')
    if pos > 0:
      self.charset = ctype[pos+8:]
      if self.charset.lower() == 'gb2312':
        # Windows misleadingly uses gb2312 when it's gbk or gb18030
        self.charset = 'gb18030'

  def __call__(self, data):
    if data is not None:
      self.buf += data
      self.pos += len(data)
      if len(self.buf) < 100:
        return

    buf = self.buf

    if self.charset is None:
      m = self.meta_charset.search(buf)
      if m:
        self.charset = (m.group(1) or m.group(2)).decode('latin1')

    if not self.found:
      m = self.title_begin.search(buf)
      if m:
        buf = self.buf = buf[m.end():]
        self.found = True

    if self.found:
      m = self.title_end.search(buf)
      if m:
        raw_title = buf[:m.start()].strip()
        logger.debug('title found at %d', self.pos - len(buf) + m.start())
      elif len(buf) > 200: # when title goes too long
        raw_title = buf[:200] + b'...'
        logger.warn('title too long, starting at %d', self.pos - len(buf))
      else:
        raw_title = False

      if raw_title:
        return self.decode_title(raw_title)

    if not self.found:
      self.buf = buf[-100:]

  def decode_title(self, raw_title):
    try:
      title = replaceEntities(raw_title.decode(self.get_charset(), errors='replace'))
      return title
    except (UnicodeDecodeError, LookupError):
      return raw_title

  def get_charset(self):
    return self.charset or self.default_charset

class PNGFinder(ContentFinder):
  _mime = 'image/png'
  def __call__(self, data):
    if data is None:
      return self._mt

    self.buf += data
    if len(self.buf) < 24:
      # can't decide yet
      return
    if self.buf[:16] != b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR':
      logging.warn('Bad PNG signature and header: %r', self.buf[:16])
      return self._mt._replace(dimension='Bad PNG')
    else:
      s = struct.unpack('!II', self.buf[16:24])
      return self._mt._replace(dimension=s)

class JPEGFinder(ContentFinder):
  _mime = 'image/jpeg'
  isfirst = True
  def __call__(self, data):
    if data is None:
      return self._mt

    # http://www.64lines.com/jpeg-width-height
    if data:
      self.buf += data

    if self.isfirst is True:
      # finding header
      if len(self.buf) < 5:
        return
      if self.buf[:3] != b'\xff\xd8\xff':
        logging.warn('Bad JPEG signature: %r', self.buf[:3])
        return self._mt._replace(dimension='Bad JPEG')
      else:
        if not py3:
          self.blocklen = ord(self.buf[4]) * 256 + ord(self.buf[5]) + 2
        else:
          self.blocklen = self.buf[4] * 256 + self.buf[5] + 2

        self.buf = self.buf[2:]
        self.isfirst = False

    if self.isfirst is False:
      # receiving a block. 4 is for next block size
      if len(self.buf) < self.blocklen + 4:
        return
      buf = self.buf
      if ord(buf[0]) != 0xff:
        logging.warn('Bad JPEG: %r', self.buf[:self.blocklen])
        return self._mt._replace(dimension='Bad JPEG')
      if (py3 and buf[1] == 0xc0 or buf[1] == 0xc2) or\
         (ord(buf[1]) == 0xc0 or (buf[1]) == 0xc2):
        if not py3:
          s = ord(buf[7]) * 256 + ord(buf[8]), ord(buf[5]) * 256 + ord(buf[6])
        else:
          s = buf[7] * 256 + buf[8], buf[5] * 256 + buf[6]
        return self._mt._replace(dimension=s)
      else:
        # not Start Of Frame, retry with next block
        self.buf = buf = buf[self.blocklen:]
        if not py3:
          self.blocklen = ord(buf[2]) * 256 + ord(buf[3]) + 2
        else:
          self.blocklen = buf[2] * 256 + buf[3] + 2
        return self(b'')

class GIFFinder(ContentFinder):
  _mime = 'image/gif'
  def __call__(self, data):
    if data is None:
      return self._mt

    self.buf += data
    if len(self.buf) < 10:
      # can't decide yet
      return
    if self.buf[:3] != b'GIF':
      logging.warn('Bad GIF signature: %r', self.buf[:3])
      return self._mt._replace(dimension='Bad GIF')
    else:
      s = struct.unpack('<HH', self.buf[6:10])
      return self._mt._replace(dimension=s)

class TitleFetcher:
  status_code = 0
  followed_times = 0 # 301, 302
  finder = None
  addr = None
  stream = None
  max_follows = 10
  timeout = 15
  _finished = False
  _cookie = None
  _connected = False
  _redirected_stream = None
  _content_finders = (TitleFinder, PNGFinder, JPEGFinder, GIFFinder)
  _url_finders = ()

  def __init__(self, url, callback,
               timeout=None, max_follows=None, io_loop=None,
               content_finders=None, url_finders=None, referrer=None,
               run_at_init=True,
              ):
    '''
    url: the (full) url to fetch
    callback: called with title or MediaType or an instance of SingletonFactory
    timeout: total time including redirection before giving up
    max_follows: max redirections

    may raise:
    <UnicodeError: label empty or too long> in host preparation
    '''
    self._callback = callback
    self.referrer = referrer
    if max_follows is not None:
      self.max_follows = max_follows

    if timeout is not None:
      self.timeout = timeout
    if hasattr(tornado.ioloop, 'current'):
        default_io_loop = tornado.ioloop.IOLoop.current
    else:
        default_io_loop = tornado.ioloop.IOLoop.instance
    self.io_loop = io_loop or default_io_loop()

    if content_finders is not None:
      self._content_finders = content_finders
    if url_finders is not None:
      self._url_finders = url_finders

    self.origurl = url
    self.url_visited = []
    if run_at_init:
      self.run()

  def run(self):
    if self.url_visited:
      raise Exception("can't run again")
    else:
      self.start_time = self.io_loop.time()
      self._timeout = self.io_loop.add_timeout(
        self.timeout + self.start_time,
        self.on_timeout,
      )
      try:
        self.new_url(self.origurl)
      finally:
        self.io_loop.remove_timeout(self._timeout)

  def on_timeout(self):
    self.run_callback(Timeout)

  def parse_url(self, url):
    '''parse `url`, set self.host and return address and stream class'''
    self.url = u = urlsplit(url)
    self.host = u.netloc

    if u.scheme == 'http':
      addr = u.hostname, u.port or 80
      stream = tornado.iostream.IOStream
    elif u.scheme == 'https':
      addr = u.hostname, u.port or 443
      stream = tornado.iostream.SSLIOStream
    else:
      raise ValueError('bad url: %r' % url)

    return addr, stream

  def new_connection(self, addr, StreamClass):
    '''set self.addr, self.stream and connect to host'''
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    self.addr = addr
    self.stream = StreamClass(s)
    logger.debug('%s: connecting to %s...', self.origurl, addr)
    self.stream.set_close_callback(self.before_connected)
    self.stream.connect(addr, self.send_request)

  def new_url(self, url):
    self.url_visited.append(url)
    self.fullurl = url

    for finder in self._url_finders:
      f = finder.match_url(url, self)
      if f:
        self.finder = f
        f()
        return

    addr, StreamClass = self.parse_url(url)
    if addr != self.addr:
      if self.stream:
        self.stream.close()
      self.new_connection(addr, StreamClass)
    else:
      logger.debug('%s: try to reuse existing connection to %s', self.origurl, self.addr)
      try:
        self.send_request(nocallback=True)
      except tornado.iostream.StreamClosedError:
        logger.debug('%s: server at %s doesn\'t like keep-alive, will reconnect.', self.origurl, self.addr)
        # The close callback should have already run
        self.stream.close()
        self.new_connection(addr, StreamClass)

  def run_callback(self, arg):
    self.io_loop.remove_timeout(self._timeout)
    self._finished = True
    if self.stream:
      self.stream.close()
    self._callback(arg, self)

  def send_request(self, nocallback=False):
    self._connected = True
    req = ['GET %s HTTP/1.1',
           'Host: %s',
           # t.co will return 200 and use js/meta to redirect using the following :-(
           # 'User-Agent: Mozilla/5.0 (X11; Linux x86_64; rv:16.0) Gecko/20100101 Firefox/16.0',
           'User-Agent: %s' % UserAgent,
           'Accept: text/html,application/xhtml+xml;q=0.9,*/*;q=0.7',
           'Accept-Language: zh-cn,zh;q=0.7,en;q=0.3',
           'Accept-Charset: utf-8,gb18030;q=0.7,*;q=0.7',
           'Accept-Encoding: gzip, deflate',
           'Connection: keep-alive',
          ]
    if self.referrer is not None:
      req.append('Referer: ' + self.referrer.replace('%', '%%'))
    path = self.url.path or '/'
    if self.url.query:
      path += '?' + self.url.query
    req = '\r\n'.join(req) % (
      path, self._prepare_host(self.host),
    )
    if self._cookie:
      req += '\r\n' + self._cookie
    req += '\r\n\r\n'
    self.stream.write(req.encode())
    self.headers_done = False
    self.parser = HttpParser(decompress=True)
    if not nocallback:
      self.stream.read_until_close(
        # self.addr and self.stream may have been changed when close callback is run
        partial(self.on_data, close=True, addr=self.addr, stream=self.stream),
        streaming_callback=self.on_data,
      )

  def _prepare_host(self, host):
    if not py3:
      host = host.decode("utf-8")
    host = encodings.idna.nameprep(host)
    return b'.'.join(encodings.idna.ToASCII(x) for x in host.split('.')).decode('ascii')

  def on_data(self, data, close=False, addr=None, stream=None):
    if close:
      logger.debug('%s: connection to %s closed.', self.origurl, addr)

    if (close and stream and self._redirected_stream is stream) or self._finished:
      # The connection is closing, and we are being redirected or we're done.
      self._redirected_stream = None
      return

    recved = len(data)
    logger.debug('%s: received data: %d bytes', self.origurl, recved)

    p = self.parser
    nparsed = p.execute(data, recved)
    if close:
      # feed EOF
      p.execute(b'', 0)

    if not self.headers_done and p.is_headers_complete():
      if not self.on_headers_done():
        return

    if p.is_partial_body():
      chunk = p.recv_body()
      if self.finder is None:
        # redirected but has body received
        return
      t = self.feed_finder(chunk)
      if t is not None:
        self.run_callback(t)
        return

    if p.is_message_complete():
      if self.finder is None:
        # redirected but has body received
        return
      t = self.feed_finder(None)
      # if title not found, t is None
      self.run_callback(t)
    elif close:
      self.run_callback(self.stream.error or ConnectionClosed)

  def before_connected(self):
    '''check if something wrong before connected'''
    if not self._connected and not self._finished:
      self.run_callback(self.stream.error)

  def process_cookie(self):
    setcookie = self.headers.get('Set-Cookie', None)
    if not setcookie:
      return

    cookies = [c.rsplit(None, 1)[-1] for c in setcookie.split('; expires')[:-1]]
    self._cookie = 'Cookie: ' + '; '.join(cookies)

  def on_headers_done(self):
    '''returns True if should proceed, None if should stop for current chunk'''
    self.headers_done = True
    self.headers = self.parser.get_headers()

    self.status_code = self.parser.get_status_code()
    if self.status_code in (301, 302):
      self.process_cookie() # or we may be redirecting to a loop
      logger.debug('%s: redirect to %s', self.origurl, self.headers['Location'])
      self.followed_times += 1
      if self.followed_times > self.max_follows:
        self.run_callback(TooManyRedirection)
      else:
        newurl = urljoin(self.fullurl, self.headers['Location'])
        self._redirected_stream = self.stream
        self.new_url(newurl)
      return

    try:
      l = int(self.headers.get('Content-Length', None))
    except (ValueError, TypeError):
      l = None

    ctype = self.headers.get('Content-Type', 'text/html')
    mt = defaultMediaType._replace(type=ctype, size=l)
    for finder in self._content_finders:
      f = finder.match_type(mt)
      if f:
        self.finder = f
        break
    else:
      self.run_callback(mt)
      return

    return True

  def feed_finder(self, chunk):
    '''feed data to TitleFinder, return the title if found'''
    t = self.finder(chunk)
    if t is not None:
      return t

class URLFinder:
  def __init__(self, url, fetcher, match=None):
    self.fullurl = url
    self.match = match
    self.fetcher = fetcher

  @classmethod
  def match_url(cls, url, fetcher):
    if hasattr(cls, '_url_pat'):
      m = cls._url_pat.match(url)
      if m is not None:
        return cls(url, fetcher, m)
    if hasattr(cls, '_match_url') and cls._match_url(url, fetcher):
      return cls(url, fetcher)

  def done(self, info):
    self.fetcher.run_callback(info)

class GithubFinder(URLFinder):
  _url_pat = re.compile(r'https://github\.com/(?!blog/)(?P<repo_path>[^/]+/[^/]+)/?$')
  _api_pat = 'https://api.github.com/repos/{repo_path}'
  httpclient = None

  def __call__(self):
    if self.httpclient is None:
      from tornado.httpclient import AsyncHTTPClient
      httpclient = AsyncHTTPClient()
    else:
      httpclient = self.httpclient

    m = self.match
    httpclient.fetch(self._api_pat.format(**m.groupdict()), self.parse_info,
                     headers={
                       'User-Agent': UserAgent,
                     })

  def parse_info(self, res):
    repoinfo = json.loads(res.body.decode('utf-8'))
    self.response = res
    self.done(repoinfo)

class GithubUserFinder(GithubFinder):
  _url_pat = re.compile(r'https://github\.com/(?!blog(?:$|/))(?P<user>[^/]+)/?$')
  _api_pat = 'https://api.github.com/users/{user}'

def main(urls):
  class BatchFetcher:
    n = 0
    def __call__(self, title, fetcher):
      if isinstance(title, bytes):
        try:
          title = title.decode('gb18030')
        except UnicodeDecodeError:
          pass
      url = ' <- '.join(reversed(fetcher.url_visited))
      logger.info('done: [%d] %s <- %s' % (fetcher.status_code, title, url))
      self.n -= 1
      if not self.n:
        tornado.ioloop.IOLoop.instance().stop()

    def add(self, url):
      TitleFetcher(url, self, url_finders=(GithubFinder,))
      self.n += 1

  from tornado.log import enable_pretty_logging
  enable_pretty_logging()
  f = BatchFetcher()
  for u in urls:
    f.add(u)
  tornado.ioloop.IOLoop.instance().start()

def test():
  urls = (
    'http://lilydjwg.is-programmer.com/',
    'http://www.baidu.com',
    'https://zh.wikipedia.org', # redirection
    'http://redis.io/',
    'http://kernel.org',
    'http://lilydjwg.is-programmer.com/2012/10/27/streaming-gzip-decompression-in-python.36130.html', # maybe timeout
    'http://img.vim-cn.com/22/cd42b4c776c588b6e69051a22e42dabf28f436', # image with length
    'https://github.com/m13253/titlebot/blob/master/titlebot.py_', # 404
    'http://lilydjwg.is-programmer.com/admin', # redirection
    'http://twitter.com', # timeout
    'http://www.wordpress.com', # reset
    'https://www.wordpress.com', # timeout
    'http://jquery-api-zh-cn.googlecode.com/svn/trunk/xml/jqueryapi.xml', # xml
    'http://lilydjwg.is-programmer.com/user_files/lilydjwg/config/avatar.png', # PNG
    'http://img01.taobaocdn.com/bao/uploaded/i1/110928240/T2okG7XaRbXXXXXXXX_!!110928240.jpg', # JPEG with Start Of Frame as the second block
    'http://file3.u148.net/2013/1/images/1357536246993.jpg', # JPEG that failed previous code
    'http://gouwu.hao123.com/', # HTML5 GBK encoding
    'https://github.com/lilydjwg/winterpy', # github url finder
    'http://github.com/lilydjwg/winterpy', # github url finder with redirect
    'http://导航.中国/', # Punycode. This should not be redirected
    'http://t.cn/zTOgr1n', # multiple redirections
    'http://www.galago-project.org/specs/notification/0.9/x408.html', # </TITLE\n>
    'http://x.co/dreamz', # redirection caused false ConnectionClosed error
    'http://m8y.org/tmp/zipbomb/zipbomb_light_nonzero.html', # very long title
  )
  main(urls)

if __name__ == "__main__":
  import sys
  try:
    if len(sys.argv) == 1:
      sys.exit('no urls given.')
    elif sys.argv[1] == 'test':
      test()
    else:
      main(sys.argv[1:])
  except KeyboardInterrupt:
    print('Interrupted.')

########NEW FILE########
__FILENAME__ = _linktitle
#!/usr/bin/env python
#-*- coding: utf-8 -*-
__desc__ = 'Fetch link title or info'

from functools import partial
import logging

from _fetchtitle import (
  TitleFetcher, MediaType,
  GithubFinder, GithubUserFinder,
  URLFinder,
)

from tornado.httpclient import AsyncHTTPClient
from tornado.ioloop import IOLoop

httpclient = AsyncHTTPClient()

try:
  import regex as re
  # modified from http://daringfireball.net/2010/07/improved_regex_for_matching_urls
  # This may take too long for builtin regex to match e.g.
  # https://wiki.archlinux.org/index.php/USB_Installation_Media_(%E7%AE%80%E4%BD%93%E4%B8%AD%E6%96%87)
  # This won't match http://[::1]
  link_re = re.compile(r'''\b(?:https?://|www\.|[a-z0-9.\-]+[.][a-z]{2,4}/)(?:[^\s()<>]+|\((?:[^\s()<>]+|\([^\s()<>]+\))*\))+(?:\((?:[^\s()<>]+|\([^\s()<>]+\))*\)|[^\s`!()\[\]{};:'".,<>?？«»“”‘’）】。，])''', re.ASCII | re.I)
except ImportError:
  import re
  logging.warn('mrab regex module not available, using simpler URL regex.')
  link_re = re.compile(r'\b(?:https?://|www\.)[-A-Z0-9+&@#/%=~_|$?!:,.]*[A-Z0-9+&@#/%=~_|$]')


_black_list = (
  r'p\.vim-cn\.com/\w{3}/?',
  r'^http://p\.gocmd\.net/\w{3}/?',
  r'^http://paste\.edisonnotes\.com/\w{3}/?',
  r'paste\.ubuntu\.(?:org\.cn|com)/\d+/?$',
  r'(?:imagebin|susepaste|paste\.kde)\.org/\d+/?$',
  r'^https?://(?:gitcafe|geakit)\.com/',
  r'^http://ideone\.com/\w+$',
  r'^http://imgur\.com/\w+$',
  r'^https?://github\.com/\w+/\w+/(?!issues/|commit/).+',
  r'\$',
  r'code\.bulix\.org',
  r'slexy.org/view/\w+$',
  r'paste\.opensuse\.org/\d+$',
  r'^http://paste\.linuxzen\.com/show/\d+$',
  r'^http://paste\.fedoraproject\.org/',
  r'^http://pastebin\.centos\.org/\d+/?$',
  r'^http://fpaste.org/\w+/',
  r'^http://supercat-lab\.org/pastebox/.+',
  r'^https://groups\.google\.com/forum/#',
  r'^http://paste\.linuxzen\.com/p/',
  r'^http://0\.web\.qstatic\.com/webqqpic/style/face/',
  r'^http://127\.0\.0\.1',
  r'^http://localhost',
  r'^https://localhost',
  r'^localhost',
)

_black_list = tuple(re.compile(x) for x in _black_list)

_stop_url_pairs = (
  ('http://weibo.com/signup/', 'http://weibo.com/'),
  ('http://weibo.com/signup/', 'http://www.weibo.com/'),
  ('http://weibo.com/login.php?url=', 'http://weibo.com/'),
  ('http://weibo.com/login.php?url=', 'http://www.weibo.com/'),
  ('https://accounts.google.com/ServiceLogin?', 'https://www.google.com/'),
  ('https://accounts.google.com/ServiceLogin?', 'https://plus.google.com/'),
  ('https://accounts.google.com/ServiceLogin?', 'https://accounts.google.com/'),
  ('https://bitbucket.org/account/signin/', 'https://bitbucket.org/'),
  ('http://www.renren.com/SysHome.do?origURL=', 'http://www.renren.com/'),
)
def filesize(size):
  if size < 1024:
      num, unit = size, "B"

  elif size > 1024 and size < 1024 ** 2 :
      num, unit = size / 1024, "KB"
  elif size > 1024 ** 2 and size < 1024 ** 3:
      num, unit = size / (1024 ** 2), "MB"
  elif size > 1024 ** 3 and size < 1024 ** 4:
      num, unit = size / (1024 ** 3), "G"
  else:
      num, unit = size / (1024 ** 4), "T"

  return u"{0} {1}".format(num, unit)

def blacklisted(u):
  for i in _black_list:
    if i.search(u):
      return True
  return False

class StopURLs(URLFinder):
  @classmethod
  def _match_url(cls, url, fetcher):
    for login, origin in _stop_url_pairs:
      if url.startswith(login):
        last_url = fetcher.url_visited[-1]
        if last_url.startswith(origin):
          return True

  def __call__(self):
    self.done(False)

class SogouImage(URLFinder):
  _url_pat = re.compile(r'http://pinyin\.cn/.+$')
  _img_pat = re.compile(br'"http://input\.shouji\.sogou\.com/multimedia/[^.]+\.jpg"')
  def __call__(self):
    httpclient.fetch(self.fullurl, self._got_page)

  def _got_page(self, res):
    m = self._img_pat.search(res.body)
    if m:
      url = self.url = m.group()[1:-1].decode('latin1')
      call_fetcher(url, self._got_image, referrer=self.fullurl)

  def _got_image(self, info, fetcher):
    self.done(info)

def format_github_repo(repoinfo):
  if not repoinfo['description']:
    repoinfo['description'] = u'该仓库没有描述 :-('
  ans = u'⇪Github 项目描述：%(description)s (%(language)s) ♡ %(watchers)d ⑂ %(forks)d，最后更新：%(updated_at)s' % repoinfo
  if repoinfo['fork']:
    ans += ' (forked)'
  ans += u'。'
  return ans

def prepare_field(d, key, prefix):
  d[key] = prefix + d[key] if d.get(key, False) else ''

def format_github_user(userinfo):
  prepare_field(userinfo, u'blog', u'，博客：')
  prepare_field(userinfo, u'company', u'，公司：')
  prepare_field(userinfo, u'location', u'，地址：')
  if 'name' not in userinfo:
    userinfo['name'] = userinfo['login']
  ans = u'⇪Github %(type)s：%(name)s，%(public_repos)d 公开仓库，%(followers)d 关注者，关注 %(following)d 人%(blog)s %(company)s%(location)s，最后活跃时间：%(updated_at)s。' % userinfo
  return ans

def format_mediatype(info):
    ret = u'⇪文件类型: ' + info.type
    if info.size:
      ret += u', 文件大小: ' + filesize(info.size)
    if info.dimension:
      s = info.dimension
      if isinstance(s, tuple):
        s = u'%dx%d' % s
      ret += u', 图像尺寸: ' + s
    return ret

def replylinktitle(reply, info, fetcher):
  if isinstance(info, bytes):
    try:
      info = info.decode('gb18030')
    except UnicodeDecodeError:
      pass

  timeout = None
  finderC = fetcher.finder.__class__
  if info is False:
    logging.info('url skipped: %s', fetcher.origurl)
    return
  elif finderC is SogouImage:
    print(info)
    ans = u'⇪搜索输入法图片: %s' % format_mediatype(info)[3:]
  elif isinstance(info, basestring):
    if fetcher.status_code != 200:
      info = '[%d] ' % fetcher.status_code + info
    ans = u'⇪网页标题: ' + info.replace('\n', '')
  elif isinstance(info, MediaType):
    ans = format_mediatype(info)
  elif info is None:
    ans = u'该网页没有标题 :-('
  elif isinstance(info, dict): # github json result
    res = fetcher.finder.response
    if res.code != 200:
      logging.warn(u'Github{,User}Finder returned HTTP code %s (body is %s).', res.code, res.body)
      ans = u'[Error %d]' % res.code
    else:
      if finderC is GithubFinder:
        ans = format_github_repo(info)
      elif finderC is GithubUserFinder:
        ans = format_github_user(info)
      else:
        logging.error(u'got a dict of unknown type: %s', finderC.__name__)
        ans = u'（内部错误）'
  else:
    ans = u'出错了！ {0}'.format(info)

  if fetcher.origurl != fetcher.fullurl:
    ans += u' (重定向到 %s )' % fetcher.fullurl

  logging.info(u'url info: %s', ans)
  reply(ans)

def call_fetcher(url, callback, referrer=None):
  fetcher = TitleFetcher(url, callback, referrer=referrer, url_finders=(
    GithubFinder, GithubUserFinder, SogouImage, StopURLs), run_at_init=False)
  try:
    fetcher.run()
  except UnicodeError as e:
    callback(e, fetcher)

def getTitle(u, reply):
  logging.info('fetching url: %s', u)
  call_fetcher(u, partial(replylinktitle, reply))


def get_urls(msg):
  seen = set()
  for m in link_re.finditer(msg):
    u = m.group(0)
    if u not in seen:
      if blacklisted(u):
        continue
      if not u.startswith("http"):
        if msg[m.start() - 3: m.start()] == '://':
          continue
        u = 'http://' + u
        if u in seen:
          continue
        if u.count('/') == 2:
          u += '/'
        if u in seen:
          continue
      seen.add(u)
  return seen

def fetchtitle(urls, reply):
  for u in urls:
    getTitle(u, reply)

def register(bot):
  bot.register_msg_handler(fetchtitle)


if __name__ == "__main__":
  def cb(tt):
    print tt
  fetchtitle(["http://www.baidu.com"], cb)
  IOLoop.instance().start()
# vim:se sw=2:

########NEW FILE########
__FILENAME__ = _pinyin
#!/usr/bin/env python
# -*- coding:utf-8 -*-

"""
    Author:cleverdeng
    E-mail:clverdeng@gmail.com
"""

__version__ = '0.9'
__all__ = ["PinYin"]

import os.path


class PinYin(object):
    def __init__(self, dict_file='plugins/word.data'):
        self.word_dict = {}
        self.dict_file = dict_file


    def load_word(self):
        if not os.path.exists(self.dict_file):
            raise IOError("NotFoundFile")

        with file(self.dict_file) as f_obj:
            for f_line in f_obj.readlines():
                try:
                    line = f_line.split('    ')
                    self.word_dict[line[0]] = line[1]
                except:
                    line = f_line.split('   ')
                    self.word_dict[line[0]] = line[1]


    def hanzi2pinyin(self, string=""):
        result = []
        if not isinstance(string, unicode):
            string = string.decode("utf-8")

        for char in string:
            key = '%X' % ord(char)
            result.append(self.word_dict.get(key, char).split()[0][:-1].lower())

        return result


    def hanzi2pinyin_split(self, string="", split=""):
        result = self.hanzi2pinyin(string=string)
        if split == "":
            return result
        else:
            return split.join(result)


if __name__ == "__main__":
    test = PinYin()
    test.load_word()
    string = "钓鱼岛是中国的"
    print "in: %s" % string
    print "out: %s" % str(test.hanzi2pinyin(string=string))
    print "out: %s" % test.hanzi2pinyin_split(string=string, split="-")

########NEW FILE########
__FILENAME__ = server
#!/usr/bin/env python
# -*- coding:utf-8 -*-
#
# Copyright 2013 cold
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
#
#   Author  :   cold
#   E-mail  :   wh_linux@126.com
#   Date    :   13/11/04 10:39:51
#   Desc    :   开启一个Server来处理验证码
#
import os
import time
import logging
from tornado.ioloop import IOLoop
from tornado.web import RequestHandler, Application, asynchronous
try:
    from config import HTTP_LISTEN
except ImportError:
    HTTP_LISTEN = "127.0.0.1"

try:
    from config import HTTP_PORT
except ImportError:
    HTTP_PORT = 8000

logger = logging.getLogger()

class BaseHandler(RequestHandler):
    webqq = None
    r = None
    uin = None
    is_login = False



class CImgHandler(BaseHandler):
    def get(self):
        data = ""
        if self.webqq.verify_img_path and os.path.exists(self.webqq.verify_img_path):
            with open(self.webqq.verify_img_path) as f:
                data = f.read()

        self.set_header("Content-Type", "image/jpeg")
        self.set_header("Content-Length", len(data))
        self.write(data)


class CheckHandler(BaseHandler):
    is_exit = False
    def get(self):
        if self.webqq.verify_img_path:
            path = self.webqq.verify_img_path
            if not os.path.exists(path):
                html = "暂不需要验证码"
            elif self.webqq.hub.is_wait():
                html = u"等待验证码"
            elif self.webqq.hub.is_lock():
                html = u"已经输入验证码, 等待验证"
            else:
                html = """
                <img src="/check" />
                <form action="/" method="POST">
                    验证码:<input type="text" name="vertify" />
                    <input type="submit" name="xx" value="提交" />
                </form>
                """
        else:
            html = "暂不需要验证码"
        self.write(html)

    @asynchronous
    def post(self):
        if (self.webqq.verify_img_path and
            not os.path.exists(self.webqq.verify_img_path)) or\
           self.webqq.hub.is_lock():
            self.write({"status":False, "message": u"暂不需要验证码"})
            return self.finish()

        code = self.get_argument("vertify")
        code = code.strip().lower().encode('utf-8')
        self.webqq.enter_verify_code(code, self.r, self.uin, self.on_callback)

    def on_callback(self, status, msg = None):
        self.write({"status":status, "message":msg})
        self.finish()

class CheckImgAPIHandler(BaseHandler):
    is_exit = False
    def get(self):
        if self.webqq.hub.is_wait():
            self.write({"status":False, "wait":True})
            return

        if self.webqq.hub.is_lock():
            return self.write({"status":True, "require":False})

        if self.webqq.verify_img_path and \
           os.path.exists(self.webqq.verify_img_path):
            if self.webqq.hub.require_check_time and \
            time.time() - self.webqq.hub.require_check_time > 900:
                self.write({"status":False, "message":u"验证码过期"})
                self.is_exit = True
            else:
                url = "http://{0}/check".format(self.request.host)
                self.write({"status":True, "require":True, "url":url})
            return
        self.write({"status":True, "require":False})


    def on_finish(self):
        if self.is_exit:
            exit()


class SendMessageHandler(BaseHandler):
    @asynchronous
    def post(self):
        tomark = self.get_argument("markname")
        msg = self.get_argument("message")
        self.webqq.send_msg_with_markname(tomark, msg, self.on_back)

    def on_back(self, status, msg = None):
        self.write({"status":status, "message":msg})
        self.finish()



app = Application([(r'/', CheckHandler), (r'/check', CImgHandler),
                   (r'/api/check', CheckImgAPIHandler),
                   (r'/api/send', SendMessageHandler),
                   (r'/api/input', CheckHandler)
                   ])
app.listen(HTTP_PORT, address = HTTP_LISTEN)


def http_server_run(webqq):
    BaseHandler.webqq = webqq
    webqq.run(BaseHandler)

########NEW FILE########
__FILENAME__ = webqq
#!/usr/bin/env python
# -*- coding:utf-8 -*-
#
# Copyright 2013 cold
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
#
#   Author  :   cold
#   E-mail  :   wh_linux@126.com
#   Date    :   13/11/14 13:23:49
#   Desc    :
#
from __future__ import print_function

import os
import sys
import time
import atexit
import smtplib
import logging
import traceback

from functools import partial
from email.mime.text import MIMEText


from twqq.client import WebQQClient
from twqq.requests import kick_message_handler, PollMessageRequest
from twqq.requests import system_message_handler, group_message_handler
from twqq.requests import buddy_message_handler, BeforeLoginRequest
from twqq.requests import register_request_handler, BuddyMsgRequest
from twqq.requests import Login2Request, FriendInfoRequest
from twqq.requests import sess_message_handler, discu_message_handler

import config

from server import http_server_run
from plugins import PluginLoader


logger = logging.getLogger("client")

SMTP_HOST = getattr(config, "SMTP_HOST", None)


def send_notice_email():
    """ 发送提醒邮件
    """
    if not SMTP_HOST:
        return False

    postfix = ".".join(SMTP_HOST.split(".")[1:])
    me = "bot<{0}@{1}>".format(config.SMTP_ACCOUNT, postfix)

    msg = MIMEText(""" 你的WebQQ机器人需要一个验证码,
                   请打开你的服务器输入验证码:
                   http://{0}:{1}""".format(config.HTTP_LISTEN,
                                            config.HTTP_PORT),
                   _subtype="plain", _charset="utf-8")
    msg['Subject'] = u"WebQQ机器人需要验证码"
    msg["From"] = me
    msg['To'] = config.EMAIL
    try:
        server = smtplib.SMTP()
        server.connect(SMTP_HOST)
        server.login(config.SMTP_ACCOUNT, config.SMTP_PASSWORD)
        server.sendmail(me, [config.EMAIL], msg.as_string())
        server.close()
        return True
    except Exception as e:
        traceback.print_exc()
        return False


class Client(WebQQClient):
    verify_img_path = None
    message_requests = {}
    start_time = time.time()
    msg_num = 0

    def handle_verify_code(self, path, r, uin):
        self.verify_img_path = path

        if getattr(config, "UPLOAD_CHECKIMG", False):
            logger.info(u"正在上传验证码...")
            res = self.hub.upload_file("check.jpg", self.hub.checkimg_path)
            logger.info(u"验证码已上传, 地址为: {0}".format(res.read()))

        if getattr(config, "HTTP_CHECKIMG", False):
            if hasattr(self, "handler") and self.handler:
                self.handler.r = r
                self.handler.uin = uin

            logger.info("请打开 http://{0}:{1} 输入验证码"
                        .format(config.HTTP_LISTEN, config.HTTP_PORT))
            if getattr(config, "EMAIL_NOTICE", False):
                if send_notice_email():
                    logger.info("发送通知邮件成功")
                else:
                    logger.warning("发送通知邮件失败")
        else:
            logger.info(u"验证码本地路径为: {0}".format(self.hub.checkimg_path))
            check_code = None
            while not check_code:
                check_code = raw_input("输入验证码: ")
            self.enter_verify_code(check_code, r, uin)

    def enter_verify_code(self, code, r, uin, callback=None):
        super(Client, self).enter_verify_code(code, r, uin)
        self.verify_callback = callback
        self.verify_callback_called = False

    @register_request_handler(BeforeLoginRequest)
    def handle_verify_check(self, request, resp, data):
        if not data:
            self.handle_verify_callback(False, "没有数据返回验证失败, 尝试重新登录")
            return

        args = request.get_back_args(data)
        scode = int(args[0])
        if scode != 0:
            self.handle_verify_callback(False, args[4])

    def handle_verify_callback(self, status, msg=None):
        if not hasattr(self, "plug_loader"):
            self.plug_loader = PluginLoader(self)

        if hasattr(self, "verify_callback") and callable(self.verify_callback)\
           and not self.verify_callback_called:
            self.verify_callback(status, msg)
            self.verify_callback_called = True

    @register_request_handler(Login2Request)
    def handle_login_errorcode(self, request, resp, data):
        if not resp.body:
            return self.handle_verify_callback(False, u"没有数据返回, 尝试重新登录")

        if data.get("retcode") != 0:
            return self.handle_verify_callback(False, u"登录失败: {0}"
                                               .format(data.get("retcode")))

    @register_request_handler(FriendInfoRequest)
    def handle_frind_info_erro(self, request, resp, data):
        if not resp.body:
            self.handle_verify_callback(False, u"获取好友列表失败")
            return

        if data.get("retcode") != 0:
            self.handle_verify_callback(False, u"好友列表获取失败: {0}"
                                        .format(data.get("retcode")))
            return
        self.handle_verify_callback(True)

    @kick_message_handler
    def handle_kick(self, message):
        self.hub.relogin()

    @system_message_handler
    def handle_friend_add(self, mtype, from_uin, account, message):
        if mtype == "verify_required":
            if getattr(config, "AUTO_ACCEPT", True):
                self.hub.accept_verify(from_uin, account, str(account))

    @group_message_handler
    def handle_group_message(self, member_nick, content, group_code,
                             send_uin, source):
        callback = partial(self.send_group_with_nick, member_nick, group_code)
        self.handle_message(send_uin, content, callback)

    @sess_message_handler
    def handle_sess_message(self, qid, from_uin, content, source):
        callback = partial(self.hub.send_sess_msg, qid, from_uin)
        self.handle_message(from_uin, content, callback, 's')

    @discu_message_handler
    def handle_discu_message(self, did, from_uin, content, source):
        nick = self.hub.get_friend_name(from_uin)
        callback = partial(self.send_discu_with_nick, nick, did)
        self.handle_message(from_uin, content, callback, 'g')

    def send_discu_with_nick(self, nick, did, content):
        content = u"{0}: {1}".format(nick, content)
        self.hub.send_discu_msg(did, content)

    def handle_message(self, from_uin, content, callback, type="g"):
        content = content.strip()
        if self.plug_loader.dispatch(from_uin, content, type, callback):
            self.msg_num += 1

    def send_group_with_nick(self, nick, group_code, content):
        content = u"{0}: {1}".format(nick, content)
        self.hub.send_group_msg(group_code, content)

    @buddy_message_handler
    def handle_buddy_message(self, from_uin, content, source):
        callback = partial(self.hub.send_buddy_msg, from_uin)
        self.handle_message(from_uin, content, callback, 'b')

    @register_request_handler(PollMessageRequest)
    def handle_qq_errcode(self, request, resp, data):
        if data and data.get("retcode") in [100006]:
            logger.error(u"获取登出消息 {0!r}".format(data))
            self.hub.relogin()

        if data and data.get("retcode") in [103, 100002]:  # 103重新登陆不成功, 暂时退出
            logger.error(u"获取登出消息 {0!r}".format(data))
            exit()

    def send_msg_with_markname(self, markname, message, callback=None):
        request = self.hub.send_msg_with_markname(markname, message)
        if request is None:
            callback(False, u"不存在该好友")

        self.message_requests[request] = callback

    @register_request_handler(BuddyMsgRequest)
    def markname_message_callback(self, request, resp, data):
        callback = self.message_requests.get(request)
        if not callback:
            return

        if not data:
            callback(False, u"服务端没有数据返回")
            return

        if data.get("retcode") != 0:
            callback(False, u"发送失败, 错误代码:".format(data.get("retcode")))
            return

        callback(True)

    def run(self, handler=None):
        self.handler = handler
        super(Client, self).run()


def run_daemon(callback, args=(), kwargs = {}):
    path = os.path.abspath(os.path.dirname(__file__))

    def _fork(num):
        try:
            pid = os.fork()
            if pid > 0:
                sys.exit(0)
        except OSError as e:
            sys.stderr.write("fork #%d faild:%d(%s)\n" % (num, e.errno,
                                                          e.strerror))
            sys.exit(1)

    _fork(1)

    os.setsid()
    # os.chdir("/")
    os.umask(0)

    _fork(2)
    pp = os.path.join(path, "pid.pid")

    with open(pp, 'w') as f:
        f.write(str(os.getpid()))

    lp = os.path.join(path, "log.log")
    lf = open(lp, 'a')
    os.dup2(lf.fileno(), sys.stdout.fileno())
    os.dup2(lf.fileno(), sys.stderr.fileno())
    callback(*args, **kwargs)

    def _exit():
        os.remove(pp)
        lf.close()

    atexit.register(_exit)


def main():
    webqq = Client(config.QQ, config.QQ_PWD,
                   debug=getattr(config, "TRACE", False))
    try:
        if getattr(config, "HTTP_CHECKIMG", False):
            http_server_run(webqq)
        else:
            webqq.run()
    except KeyboardInterrupt:
        print("Exiting...", file=sys.stderr)
    except SystemExit:
        logger.error("检测到退出, 重新启动")
        os.execv(sys.executable, [sys.executable] + sys.argv)


if __name__ == "__main__":
    import tornado.log
    from tornado.options import options

    if not getattr(config, "DEBUG", False):
        options.log_file_prefix = getattr(config, "LOG_PATH", "log.log")
        options.log_file_max_size = getattr(
            config, "LOG_MAX_SIZE", 5 * 1024 * 1024)
        options.log_file_num_backups = getattr(config, "LOG_BACKUPCOUNT", 10)
    tornado.log.enable_pretty_logging(options=options)

    if not config.DEBUG and hasattr(os, "fork"):
        run_daemon(main)
    else:
        main()

########NEW FILE########
