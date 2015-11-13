__FILENAME__ = demobasic
#    coding: UTF-8
#    User: haku
#    Date: 13-2-12
#    Time: 1:01
#
__author__ = 'haku'
from pyrailgun import RailGun
import sys

reload(sys)
sys.setdefaultencoding("utf-8")

railgun = RailGun()

railgun.setTask(file("basic.json"))
railgun.fire();
nodes = railgun.getShells()
file = file("demo_basic.txt", "w+")
for id in nodes:
    node = nodes[id]
    file.write(node.get('score', [""])[0] + "\r\n")
    file.write(node.get('img', [""])[0] + "\r\n")
    file.write(node.get('description', [""])[0] + "\r\n====================================")
########NEW FILE########
__FILENAME__ = demobing
#    coding: UTF-8
#    User: haku
#    Date: 13-2-12
#    Time: 1:01
#
__author__ = 'haku'
from pyrailgun import RailGun
import sys, urllib

reload(sys)
sys.setdefaultencoding("utf-8")

railgun = RailGun()
railgun.setTask(file("bing.json"));
query = raw_input("Please Input Query\r\n")
railgun.setGlobalData("q", urllib.quote(query))
railgun.fire();
nodes = railgun.getShells()
file = file("demo_bing.txt", "w+")
for id in nodes:
    node = nodes[id]
    print "entry  " + node.get('title',[""])[0]
    file.write(node.get('title',[""])[0] + "\r\n")
    file.write(node.get('description',[""])[0] + "\r\n====================================\r\n")
########NEW FILE########
__FILENAME__ = demowebkit
#    coding: UTF-8
#    User: haku
#    Date: 13-2-12
#    Time: 上午1:01
#
__author__ = 'haku'
from pyrailgun import RailGun
import sys

reload(sys)
sys.setdefaultencoding("utf-8")

railgun = RailGun()
railgun.setTask(file("webkit.json"));
railgun.fire();
nodes = railgun.getShells()
file = file("demo_webkit.txt", "w+")
for id in nodes:
    node = nodes[id]
    file.write(node.get('content',[""])[0] + "\r\n====================================")
########NEW FILE########
__FILENAME__ = cwebbrowser
#    coding: UTF-8
#    User: haku
#    Date: 13-10-6
#    Time: 13:49
#

from logger import Logger
import time

from PyQt4.QtCore import QUrl, Qt
from PyQt4.QtGui import QApplication
from PyQt4.QtNetwork import QNetworkAccessManager
from PyQt4.QtNetwork import QNetworkRequest
from PyQt4.QtWebKit import QWebPage, QWebView, QWebSettings

app = QApplication(['dummy'])


class Timeout(Exception):
    """A timeout (usually on page load) has been reached."""


class CWebBrowser():
    def _events_loop(self, wait=0.01):
        self.application.processEvents()
        time.sleep(wait)


    def __init__(self):

        self.application = app
        self.logger = Logger.getLogger()

        wp = QWebPage()
        wp.setForwardUnsupportedContent(True)
        wp.loadFinished.connect(self._on_load_finished)
        wp.loadStarted.connect(self._on_load_started)
        self.webpage = wp
        self.webframe = wp.mainFrame()
        self.headers = []
        self._load_timeout = -1
        self._load_success = False
        self.setSettings()

    def setSettings(self):
        page = self.webpage
        page.settings().setAttribute(QWebSettings.LocalStorageDatabaseEnabled, True)
        page.settings().setAttribute(QWebSettings.JavascriptCanOpenWindows, True)
        # auto disable image download
        page.settings().setAttribute(QWebSettings.AutoLoadImages, False)

    def _on_load_started(self):
        self._load_success = False
        self._load_last = 0
        self.logger.debug("Page Load Started")

    def _on_load_finished(self):
        self._load_success = True
        self.logger.debug("Page Load Finished " + unicode((self.webframe.url().toString())))

    def make_request(self, url):
        url = QUrl(url)
        req = QNetworkRequest(url)
        for header in self.headers:
            val = self.headers[header]
            req.setRawHeader(header, val)
        return req


    def setHeaders(self, headers):
        self.headers = headers

    def load(self, url, headers=None, body=None, load_timeout=-1, delay=None):
        if not headers:
            self.headers = []
        if not body:
            body = ""
            # ass headers
        req = self.make_request(url)
        self._load_success = False
        self._load_timeout = load_timeout

        self.webframe.load(req, QNetworkAccessManager.GetOperation, body)
        # wait to load finished
        self._wait_finish()
        # delay wait to render html
        if delay:
            self.wait_delays(delay)

    def _wait_finish(self):
        while not self._load_success:
            self._events_loop()
            self._load_last += 1
            if self._load_timeout > 0 and self._load_last >= self._load_timeout * 100:
                raise Timeout("Timeout reached: %d seconds" % self._load_timeout)

    def wait_delays(self, seconds):

        for j in range(1, seconds):
            for i in range(1, 100):
                # wait to load finished
                self._wait_finish()
                self._events_loop()

    def html(self):
        return unicode(self.webframe.toHtml())


    def show(self):
        self.webview = QWebView()
        self.webview.setPage(self.webpage)
        window = self.webview.window()
        window.setAttribute(Qt.WA_DeleteOnClose)
        self.application.syncX()
        self.webview.show()

    def close(self):
        pass

########NEW FILE########
__FILENAME__ = logger
#    coding: UTF-8
#    User: haku
#    Date: 13-2-27
#    Time: 23:23
#
import logging.config, os


class Logger:
    log_instance = None

    @staticmethod
    def InitLogConf():
        """
        >>> Logger.getLogger() # doctest: +ELLIPSIS
        load logging configure from logging.conf
        <logging.RootLogger object at ...>
        """

        if os.path.isfile("logging.conf"):
            file_path = "logging.conf"
        else:
            file_path = os.path.dirname(__file__) + "/logging.conf"
        print 'load logging configure from ' + file_path
        Logger.log_instance = logging.config.fileConfig(file_path)

    @staticmethod
    def getLogger(name=""):
        """
        :param name: string
        :return: Logger


        doctest:
        >>> Logger.getLogger().debug("debug message") # doctest: +ELLIPSIS
        [...] (DEBUG) : debug message
        >>> Logger.getLogger().info("info message") # doctest: +ELLIPSIS
        [...] (INFO) : info message
        >>> Logger.getLogger("c1").debug("customed message") # doctest: +ELLIPSIS
        [...] (DEBUG) : customed message
        """
        if Logger.log_instance == None:
            Logger.InitLogConf()
        Logger.log_instance = logging.getLogger(name)
        return Logger.log_instance


if __name__ == "__main__":
    import doctest

    doctest.testmod()

########NEW FILE########
__FILENAME__ = pattern
#    coding: UTF-8
#    User: haku
#    Date: 13-2-24
#    Time: 1:01
#
import re
from logger import Logger

class Pattern:
    def __init__(self, task_entry=None, shell=None, global_data=None):
        assert (task_entry != None), "task_entry can't be None"
        self.task_entry = task_entry
        self.shell = shell
        self.global_data = global_data
        self.logger = Logger.getLogger()

    # deep.. and deep recursion
    def convertPattern(self, area, resource_str=None):
        """
        :param area: dict
        :param resource_str: string
        :return:
        >>> Pattern({'url':'http://is.me/${0,1}'}).convertPattern('url')  # doctest: +ELLIPSIS
        load logging configure from logging.conf
        [...] (INFO) : Pattern Found as 0,1
        ['http://is.me/0', 'http://is.me/1']
        """

        # specify field required in task_entry
        assert self.task_entry.get(area, None) != None, "specify field required in task_entry"

        text = resource_str \
            if resource_str is not None \
            else self.task_entry.get(area)

        pattern = re.compile(r'\$\{(.*?)\}')

        matched = pattern.findall(text)
        # if doesn't match. just return it
        if not matched:
            return [text]

        self.logger.info("Pattern Found as " + matched[0])

        converted_strings = []
        # support ${#} as shell's Field
        if matched[0].startswith('#'):
            key_name = matched[0][1:]
            assert self.shell != None, "shell can't be empty when using #"
            if self.shell.get(key_name) == None:
                return None
            assert len(self.shell[key_name]) <= 1, " shell 'src length is greater than 1"

            replacedst = self.shell[key_name][0] \
                if len(self.shell[key_name]) == 1 \
                else ""

            converted_strings.append(pattern.sub(replacedst, text, 1))

        # support ${@} as pyrailgun's global data sets
        if matched[0].startswith('@'):
            key_name = matched[0][1:]
            replacedst = self.global_data.get(key_name)
            assert None != replacedst, "config_data " + key_name + " is empty"
            converted_strings.append(pattern.sub(replacedst, text, 1))

        # expand ${n,m} as n,n+1,n+2...m
        if re.match(r'\d*,\d*', matched[0]):
            assert None == self.shell, "rule " + matched[0] + " can't be set in shells"
            regxp = re.search(r'(\d*),(\d*)', matched[0])
            lower = int(regxp.group(1))
            max = int(regxp.group(2))
            for i in range(lower, max + 1):
                if (lower == 0):
                    pass
                replaced_text = format(i, "0" + str(len(regxp.group(1))) + "d")
                new_str = pattern.sub(replaced_text, text, 1)
                converted_strings.append(new_str)

        # recursion
        converted_list = []
        for s_str in converted_strings:
            converted_sub = self.convertPattern(area, resource_str=s_str)
            if not isinstance(converted_sub, list):
                converted_sub = [converted_sub]
            converted_list.extend(converted_sub)
            # if converted_strings is null set the raw input into it
        if not converted_list:
            converted_list.append(text)
        return converted_list
########NEW FILE########
__FILENAME__ = railgun
#    coding: UTF-8
#    User: haku
#    Date: 14-5-22
#    Time: 4:01
#

__author__ = 'haku-mac'


from pattern import Pattern
from logger import Logger
import re, time
import requests
import json
from bs4 import BeautifulSoup

class RailGun:
    def __init__(self):
        self.global_data = {}
        self.shell_groups = {}
        self.logger = Logger.getLogger()

    # set taskdata into me
    def setTaskData(self, task_data):
        self.task_data = dict(task_data)

    # set taskdata into me via a yaml file
    def setTask(self, tfile, ext=None):
        assert isinstance(tfile, file), "taskfile should be an instance file, get" + str(type(tfile))
        if not ext:
            ext = tfile.name.split(".")[-1]
        task_data = json.load(tfile)
        assert task_data, "Task Data is Empty"
        self.task_data = dict(task_data)

    # set some running global
    def setGlobalData(self, key, value):
        self.global_data[key] = value

    # do work
    def fire(self):
        self.__parserShells(self.task_data)
        return self.shell_groups

    # get parsed shells
    def getShells(self, group_name='default'):
        return self.shell_groups.get(group_name)

    def __parserShells(self, task_entry):
        """

        :param task_entry:
        :return:
        """
        if (isinstance(task_entry, unicode)):
            return
            # do current action
        actionname = task_entry["action"].strip()
        if None != task_entry.get('shellid'):
            self.logger.info("info current shell [" + task_entry.get('shellgroup') + ":" + \
                             str(task_entry.get('shellid')) + "]")

        actionMap = {
            'main': "__main"
            , 'shell': '__createShell'
            , 'faketask': '__faketask'
            , 'fetcher': '__fetch'
            , 'parser': '__parser'
        }

        if actionname in actionMap.keys():
            worker = getattr(self
                             , '_RailGun{}'.format(actionMap[actionname])
            )
            if callable(worker):
                task_entry = worker(task_entry)

        if (None == task_entry.get('subaction')):
            return

        for subtask in task_entry['subaction']:
            # if entry is not fakedshell and entry has datas then copy to subtask
            if (subtask['action'] != 'faketask' and task_entry.get('datas') != None):
                subtask['datas'] = task_entry.get('datas')
                # ignore datas field
            if 'datas' == str(subtask):
                continue
                # passed to subtask
            if None != task_entry.get('shellgroup'):
                subtask['shellgroup'] = task_entry.get('shellgroup')
            if None != task_entry.get('shellid'):
                subtask['shellid'] = task_entry.get('shellid')
            self.__parserShells(subtask)
        return

    def __main(self, task_entry):
        self.logger.info(task_entry['name'] + " is now running")
        return task_entry

    # using webkit to fetch url
    def __fetch_webkit(self, task_entry):
        p = Pattern(task_entry, self.__getCurrentShell(task_entry), self.global_data)

        import cwebbrowser

        task_entry['datas'] = []

        urls = p.convertPattern('url')
        timeout = task_entry.get('timeout', 120)
        delay = task_entry.get('delay', 0)

        for url in urls:
            self.logger.info("fetching " + url)
            data = ""
            if not url:
                # do not fetch null url
                continue
            browser = cwebbrowser.CWebBrowser()
            browser.setHeaders(task_entry.get('headers', []))
            #browser.show();
            try:
                browser.load(url=url, load_timeout=timeout, delay=delay)
            except cwebbrowser.Timeout:
                self.logger.error("fetch " + url + " timeout ")
            except  Exception, exception:
                self.logger.error("fetch " + url + " error ")
                print "Exception message:", exception

            else:
                html = browser.html()
                if html:
                    html = html.encode('utf-8')
                    data = html
                else:
                    self.logger.error("fetch " + url + " failed with no response")
            task_entry['datas'].append(data)

            browser.close()
        return task_entry

    def __fetch_requests(self, task_entry):
        p = Pattern(task_entry, self.__getCurrentShell(task_entry), self.global_data)

        timeout = task_entry.get('timeout', 120)
        urls = p.convertPattern('url')
        s = requests.session()
        headers = task_entry.get('headers', [])
        task_entry['datas'] = []
        if not urls:
            return task_entry
        for url in urls:
            self.logger.info("fetching " + url)
            data = ""
            if not url:
                # do not fetch null url
                continue
            try:
                response = s.get(url, timeout=timeout, headers=headers)
                if 200 != response.status_code:
                    self.logger.error("fetch " + url + " failed with code " + (str)(response.status_code))
                data = response.text
            except:
                self.logger.error("fetch " + url + " failed in sockets")
            task_entry['datas'].append(data)
        return task_entry

    # fetch something
    def __fetch(self, task_entry):

        if task_entry.get("webkit", False):
            return self.__fetch_webkit(task_entry)
        return self.__fetch_requests(task_entry)

    def __faketask(self, task_entry):
        return task_entry

    # parse with soup
    def __parser(self, task_entry):
        rule = task_entry['rule'].strip()
        self.logger.info("parsing with rule " + rule)
        strip = task_entry.get('strip')
        datas = task_entry.get('datas')
        pos = task_entry.get('pos')
        attr = task_entry.get('attr')
        parsed_datas = []
        for data in datas:
            self.logger.debug("parse from raw " + str(data))
            soup = BeautifulSoup(data)
            parsed_data_sps = soup.select(rule)
            # set pos
            if (None != pos):
                if pos > len(parsed_data_sps) - 1:
                    parsed_data_sps = []
                else:
                    parsed_data_sps = [parsed_data_sps[pos]]
            for tag in parsed_data_sps:
                tag = unicode(tag)
                if (None != attr):
                    attr_data = BeautifulSoup(tag.encode("utf8"))
                    tag = attr_data.contents[0].get(attr)
                if strip == 'true':
                    dr = re.compile(r'<!--.*-->')
                    tag = dr.sub('', tag)
                    dr = re.compile(r'<.*?>')
                    tag = dr.sub('', tag)
                    dr = re.compile(r'[\r\n]')
                    tag = dr.sub('', tag)
                parsed_datas.append(tag)
        self.logger.info("after parsing " + str(len(parsed_datas)))
        # set data to shell
        current_shell = self.__getCurrentShell(task_entry)
        if current_shell != None and task_entry.get('setField') != None and len(parsed_datas) > 0:
            fieldname = task_entry.get('setField')
            self.logger.debug("set" + fieldname + "as" + str(parsed_datas));
            current_shell[fieldname] = parsed_datas
        task_entry['datas'] = parsed_datas
        return task_entry

    def __createShell(self, task_entry):
        datas = task_entry.get('datas')
        # every shell has only one data
        subacts = []
        self.logger.info(str(len(datas)) + " shells created")
        shellgroup = task_entry.get('group', 'default')
        shellid = 0
        self.shell_groups[shellgroup] = {}
        for data in datas:
            shellid += 1
            # init shell
            self.shell_groups[shellgroup][shellid] = {}
            # task entry splited into pieces
            # sub actions nums = now sub nums * shell num
            subact = {
                "action": "faketask",
                "shellgroup": shellgroup,
                "shellid": shellid,
                "datas": [data],
                "subaction": task_entry["subaction"]
            }
            subacts.append(subact)
        task_entry["subaction"] = subacts
        return task_entry

    def __getCurrentShell(self, task_entry):
        if (None == task_entry.get('shellgroup')):
            return None
        shellgroup = task_entry['shellgroup']
        if None == self.shell_groups.get(shellgroup):
            return None
        shellid = task_entry['shellid']
        shell = self.shell_groups[shellgroup][shellid]
        return shell

########NEW FILE########
