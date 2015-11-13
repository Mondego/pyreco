__FILENAME__ = bootstrap
##############################################################################
#
# Copyright (c) 2006 Zope Foundation and Contributors.
# All Rights Reserved.
#
# This software is subject to the provisions of the Zope Public License,
# Version 2.1 (ZPL).  A copy of the ZPL should accompany this distribution.
# THIS SOFTWARE IS PROVIDED "AS IS" AND ANY AND ALL EXPRESS OR IMPLIED
# WARRANTIES ARE DISCLAIMED, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF TITLE, MERCHANTABILITY, AGAINST INFRINGEMENT, AND FITNESS
# FOR A PARTICULAR PURPOSE.
#
##############################################################################
"""Bootstrap a buildout-based project

Simply run this script in a directory containing a buildout.cfg.
The script accepts buildout command-line options, so you can
use the -c option to specify an alternate configuration file.
"""

import os, shutil, sys, tempfile, urllib, urllib2, subprocess
from optparse import OptionParser

if sys.platform == 'win32':
    def quote(c):
        if ' ' in c:
            return '"%s"' % c  # work around spawn lamosity on windows
        else:
            return c
else:
    quote = str

# See zc.buildout.easy_install._has_broken_dash_S for motivation and comments.
stdout, stderr = subprocess.Popen(
    [sys.executable, '-Sc',
     'try:\n'
     '    import ConfigParser\n'
     'except ImportError:\n'
     '    print 1\n'
     'else:\n'
     '    print 0\n'],
    stdout=subprocess.PIPE, stderr=subprocess.PIPE).communicate()
has_broken_dash_S = bool(int(stdout.strip()))

# In order to be more robust in the face of system Pythons, we want to
# run without site-packages loaded.  This is somewhat tricky, in
# particular because Python 2.6's distutils imports site, so starting
# with the -S flag is not sufficient.  However, we'll start with that:
if not has_broken_dash_S and 'site' in sys.modules:
    # We will restart with python -S.
    args = sys.argv[:]
    args[0:0] = [sys.executable, '-S']
    args = map(quote, args)
    os.execv(sys.executable, args)
# Now we are running with -S.  We'll get the clean sys.path, import site
# because distutils will do it later, and then reset the path and clean
# out any namespace packages from site-packages that might have been
# loaded by .pth files.
clean_path = sys.path[:]
import site  # imported because of its side effects
sys.path[:] = clean_path
for k, v in sys.modules.items():
    if k in ('setuptools', 'pkg_resources') or (
        hasattr(v, '__path__') and
        len(v.__path__) == 1 and
        not os.path.exists(os.path.join(v.__path__[0], '__init__.py'))):
        # This is a namespace package.  Remove it.
        sys.modules.pop(k)

is_jython = sys.platform.startswith('java')

setuptools_source = 'http://peak.telecommunity.com/dist/ez_setup.py'
distribute_source = 'http://python-distribute.org/distribute_setup.py'


# parsing arguments
def normalize_to_url(option, opt_str, value, parser):
    if value:
        if '://' not in value:  # It doesn't smell like a URL.
            value = 'file://%s' % (
                urllib.pathname2url(
                    os.path.abspath(os.path.expanduser(value))),)
        if opt_str == '--download-base' and not value.endswith('/'):
            # Download base needs a trailing slash to make the world happy.
            value += '/'
    else:
        value = None
    name = opt_str[2:].replace('-', '_')
    setattr(parser.values, name, value)

usage = '''\
[DESIRED PYTHON FOR BUILDOUT] bootstrap.py [options]

Bootstraps a buildout-based project.

Simply run this script in a directory containing a buildout.cfg, using the
Python that you want bin/buildout to use.

Note that by using --setup-source and --download-base to point to
local resources, you can keep this script from going over the network.
'''

parser = OptionParser(usage=usage)
parser.add_option("-v", "--version", dest="version",
                          help="use a specific zc.buildout version")
parser.add_option("-d", "--distribute",
                   action="store_true", dest="use_distribute", default=False,
                   help="Use Distribute rather than Setuptools.")
parser.add_option("--setup-source", action="callback", dest="setup_source",
                  callback=normalize_to_url, nargs=1, type="string",
                  help=("Specify a URL or file location for the setup file. "
                        "If you use Setuptools, this will default to " +
                        setuptools_source + "; if you use Distribute, this "
                        "will default to " + distribute_source + "."))
parser.add_option("--download-base", action="callback", dest="download_base",
                  callback=normalize_to_url, nargs=1, type="string",
                  help=("Specify a URL or directory for downloading "
                        "zc.buildout and either Setuptools or Distribute. "
                        "Defaults to PyPI."))
parser.add_option("--eggs",
                  help=("Specify a directory for storing eggs.  Defaults to "
                        "a temporary directory that is deleted when the "
                        "bootstrap script completes."))
parser.add_option("-t", "--accept-buildout-test-releases",
                  dest='accept_buildout_test_releases',
                  action="store_true", default=False,
                  help=("Normally, if you do not specify a --version, the "
                        "bootstrap script and buildout gets the newest "
                        "*final* versions of zc.buildout and its recipes and "
                        "extensions for you.  If you use this flag, "
                        "bootstrap and buildout will get the newest releases "
                        "even if they are alphas or betas."))
parser.add_option("-c", None, action="store", dest="config_file",
                   help=("Specify the path to the buildout configuration "
                         "file to be used."))

options, args = parser.parse_args()

if options.eggs:
    eggs_dir = os.path.abspath(os.path.expanduser(options.eggs))
else:
    eggs_dir = tempfile.mkdtemp()

if options.setup_source is None:
    if options.use_distribute:
        options.setup_source = distribute_source
    else:
        options.setup_source = setuptools_source

if options.accept_buildout_test_releases:
    args.insert(0, 'buildout:accept-buildout-test-releases=true')

try:
    import pkg_resources
    import setuptools  # A flag.  Sometimes pkg_resources is installed alone.
    if not hasattr(pkg_resources, '_distribute'):
        raise ImportError
except ImportError:
    ez_code = urllib2.urlopen(
        options.setup_source).read().replace('\r\n', '\n')
    ez = {}
    exec ez_code in ez
    setup_args = dict(to_dir=eggs_dir, download_delay=0)
    if options.download_base:
        setup_args['download_base'] = options.download_base
    if options.use_distribute:
        setup_args['no_fake'] = True
        if sys.version_info[:2] == (2, 4):
            setup_args['version'] = '0.6.32'
    ez['use_setuptools'](**setup_args)
    if 'pkg_resources' in sys.modules:
        reload(sys.modules['pkg_resources'])
    import pkg_resources
    # This does not (always?) update the default working set.  We will
    # do it.
    for path in sys.path:
        if path not in pkg_resources.working_set.entries:
            pkg_resources.working_set.add_entry(path)

cmd = [quote(sys.executable),
       '-c',
       quote('from setuptools.command.easy_install import main; main()'),
       '-mqNxd',
       quote(eggs_dir)]

if not has_broken_dash_S:
    cmd.insert(1, '-S')

find_links = options.download_base
if not find_links:
    find_links = os.environ.get('bootstrap-testing-find-links')
if not find_links and options.accept_buildout_test_releases:
    find_links = 'http://downloads.buildout.org/'
if find_links:
    cmd.extend(['-f', quote(find_links)])

if options.use_distribute:
    setup_requirement = 'distribute'
else:
    setup_requirement = 'setuptools'
ws = pkg_resources.working_set
setup_requirement_path = ws.find(
    pkg_resources.Requirement.parse(setup_requirement)).location
env = dict(
    os.environ,
    PYTHONPATH=setup_requirement_path)

requirement = 'zc.buildout'
version = options.version
if version is None and not options.accept_buildout_test_releases:
    # Figure out the most recent final version of zc.buildout.
    import setuptools.package_index
    _final_parts = '*final-', '*final'

    def _final_version(parsed_version):
        for part in parsed_version:
            if (part[:1] == '*') and (part not in _final_parts):
                return False
        return True
    index = setuptools.package_index.PackageIndex(
        search_path=[setup_requirement_path])
    if find_links:
        index.add_find_links((find_links,))
    req = pkg_resources.Requirement.parse(requirement)
    if index.obtain(req) is not None:
        best = []
        bestv = None
        for dist in index[req.project_name]:
            distv = dist.parsed_version
            if distv >= pkg_resources.parse_version('2dev'):
                continue
            if _final_version(distv):
                if bestv is None or distv > bestv:
                    best = [dist]
                    bestv = distv
                elif distv == bestv:
                    best.append(dist)
        if best:
            best.sort()
            version = best[-1].version

if version:
    requirement += '=='+version
else:
    requirement += '<2dev'

cmd.append(requirement)

if is_jython:
    import subprocess
    exitcode = subprocess.Popen(cmd, env=env).wait()
else:  # Windows prefers this, apparently; otherwise we would prefer subprocess
    exitcode = os.spawnle(*([os.P_WAIT, sys.executable] + cmd + [env]))
if exitcode != 0:
    sys.stdout.flush()
    sys.stderr.flush()
    print ("An error occurred when trying to install zc.buildout. "
           "Look above this message for any errors that "
           "were output by easy_install.")
    sys.exit(exitcode)

ws.add_entry(eggs_dir)
ws.require(requirement)
import zc.buildout.buildout

# If there isn't already a command in the args, add bootstrap
if not [a for a in args if '=' not in a]:
    args.append('bootstrap')


# if -c was provided, we push it back into args for buildout's main function
if options.config_file is not None:
    args[0:0] = ['-c', options.config_file]

zc.buildout.buildout.main(args)
if not options.eggs:  # clean up temporary egg directory
    shutil.rmtree(eggs_dir)

########NEW FILE########
__FILENAME__ = ajax-test
#!/usr/bin/python
import spynner
  
browser = spynner.Browser()
browser.create_webview(True)
browser.load("http://juicystudio.com/experiments/ajax/index.php")
browser.click_ajax("#fact")
print browser.runjs("_jQuery('#update').html()").toString()
browser.click_ajax("#fact")
print browser.runjs("_jQuery('#update').html()").toString()
browser.close()

########NEW FILE########
__FILENAME__ = anothergoogle
#!/usr/bin/env python
# -*- coding: utf-8 -*-
__docformat__ = 'restructuredtext en'

import logging
import os
import re
import tempfile

from lxml.html import document_fromstring
from spynner import browser
from PyQt4 import QtCore


FORMAT = '%(asctime)-15s %(message)s'
logging.basicConfig(format=FORMAT)
logging.getLogger('test scrapper').debug("start")
re_flags = re.M|re.U|re.S|re.X
os.environ['DISPLAY'] = os.environ.get('GMB_DISPLAY', ':1')

def get_tree(h):
    """h can be either a zc.testbrowser.Browser or a string."""
    if isinstance(h, file):
        h = h.read()
    if isinstance(h, browser.Browser):
        h = h.html
    if not isinstance(h, basestring):
        h = h.contents
    return document_fromstring(h) 


def getQtBrowser(download_directory=None):
    debug=4
    br = browser.Browser(embed_jquery=True,
                         debug_level=debug,)
    br.download_directory = download_directory
    return br

def get_url(url, path):
    if not (path.startswith('http://')
            or path.startswith('https://')):
            path = '%s/%s' % (url, path)
    return path


def main(download_directory=None):
    logger = logging.getLogger('scrapper.test')
    if not download_directory:
        download_directory = tempfile.mkdtemp()
    br = getQtBrowser(download_directory)
    br.create_webview()
    br.webview.show()
    br.webview.setWindowState(QtCore.Qt.WindowMaximized)
    br.load('http://www.google.com')
    def can_continuea(abrowser):
        t = get_tree(abrowser)
        return len(t.xpath("//input[@name='q']")) > 0
    br.wait_for_content(can_continuea, 60, u'Timeout while loading account data') 
    br.fill('input[name="q"]', 'kiorky')
    t = get_tree(br)
    name = [a.attrib['name']
            for a in  t.xpath('//input[@type="submit"]') 
            if 'google' in a.value.lower()][0]
    # search for the search input control which can change id
    input_sel = "input[name='%s']" % name
    # remodve the search live query ...
    br.native_click('input[name="q"]')
    br.click(input_sel)
    def can_continueb(abrowser):
        t = get_tree(abrowser)
        return len( t.xpath('//*[@id="ires"]')) > 0
    br.wait_for_content(can_continueb, 60, u'Timeout while loading account data') 
    assert 'cryptelium.net' in br.html


if __name__ == '__main__':
    print main()

# vim:set et sts=4 ts=4 tw=80:

########NEW FILE########
__FILENAME__ = google
#!/usr/bin/python
import spynner
import pyquery

browser = spynner.Browser(debug_level=spynner.INFO)
browser.create_webview()
browser.show()
browser.load("http://www.wordreference.com")
browser.load_jquery(True)
browser.choose("input[name=lr=lang_es]")
browser.click("input[name=enit]")
browser.click("a[class=l]:first")
d = pyquery.PyQuery(browser.html)
d.make_links_absolute(base_url=browser.url)
href = d('a:last').attr('href')
print href
print len(browser.download(href))
browser.browse()

########NEW FILE########
__FILENAME__ = native_events
#!/usr/bin/env python
# -*- coding: utf-8 -*-
__docformat__ = 'restructuredtext en'

from PyQt4 import QtCore
from spynner import browser
from time import sleep

br = browser.Browser(
#    debug_level=4
)
br.load('http://pypi.python.org/pypi')
try:
    br.wait_load(5)
except:
    pass
br.create_webview()
br.show()

br.wk_fill('input[id=term]', 'spynner') 
br.native_click('input[id=submit]', offsetx=5, offsety=5)
print "Saw the mouse on the logo move & click on the search input"
sleep(3)
print "press any key"
raw_input()

br.sendText('input[id=term]', 'spynner') 
#print "Noticed spynner in the input ?"    vim:set et sts=4 ts=4 tw=80:
sleep(3)                                 

########NEW FILE########
__FILENAME__ = proxy
#!/usr/bin/env python
# -*- coding: utf-8 -*-
__docformat__ = 'restructuredtext en'
import spynner
import os
import sys

class test(object):
    user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.31 (KHTML, like Gecko) Chrome/26.0.1410.43 Safari/537.31"
    proxyg = os.environ.get('SPY_PROXY', None)
    proxyd = os.environ.get('SPYD_PROXY', None)
    img = 'https://www.google.fr/images/srpr/logo4w.png'
    url = 'https://www.google.fr'

    def test(self):
        IMG = self.img
        URL = self.url
        assert self.proxyg is not None, "no global proxy set"
        assert self.proxyd is not None, "no download proxy set"
        br = self.browser = spynner.Browser(
            ignore_ssl_errors=False,
            user_agent=self.user_agent,
            debug_level=spynner.WARNING,
            debug_stream=sys.stderr)
        br.show()
        data, content = {}, {}
        # no proxy
        data['noproxy'] = br.download(IMG)
        br.load(URL, None)
        content['noproxy'] = br.html
        # no proxy - alt1
        br.set_proxy("")
        data["proxy_void"] = br.download(IMG)
        br.load(URL, None)
        content["proxy_void"] = br.html
        # no proxy - alt2
        br.set_proxy(None)
        data["proxy_none"] = br.download(IMG)
        br.load(URL, None)
        content["proxy_none"] = br.html
        # global proxy
        br.set_proxy(self.proxyg)
        data["proxy_g"] = br.download(IMG)
        br.load(URL, None)
        content["proxy_g"] = br.html
        # use a proxy only @ download level
        br.load(URL)
        data["proxy_d"] = br.download(IMG, proxy_url=self.proxyd)
        for i in data:
            if data["noproxy"] != data[i]:
                raise Exception("Download failed for %s" % i)

def main():
    test().test()


"""
run with
SPY_PROXY="http://foo" SPYD_PROXY="http://bar" $PYTHON examples/googleproxy.py
"""


if __name__ == '__main__':
    main()

# vim:set et sts=4 ts=4 tw=80:

########NEW FILE########
__FILENAME__ = webkit_methods
# -*- coding: utf-8 -*-
__docformat__ = 'restructuredtext en'

from time import sleep
from spynner import browser
br = browser.Browser(
#    debug_level=4
)
br.load('http://pypi.python.org/pypi')
br.create_webview()
br.show()

br.wk_fill('input[id=term]', 'spynner')
br.wk_click("input[id=submit]", wait_load=True, timeout=5)
print "Noticed the search"
sleep(3)
 
anchors = br.webframe.findAllElements('#menu ul.level-two a')
anchor = [a for a in anchors if 'Browse' in a.toPlainText()][0]
br.wk_click_element_link(anchor, timeout=10)
print "Noticed the click on the browse"
sleep(3)

a = br.webframe.findFirstElement('a#logolink img')
br.wk_click_element_link(a, timeout=10)
print "Noticed the click on the logo"
sleep(3)

print "Enter any key to continue"
raw_input()
# vim:set et sts=4 ts=4 tw=80:

########NEW FILE########
__FILENAME__ = wordreference
#!/usr/bin/env python
import spynner
import pyquery

browser = spynner.Browser(debug_level=spynner.DEBUG)
browser.create_webview()
browser.show()
browser.set_html_parser(pyquery.PyQuery)
browser.load("http://www.wordreference.com")
browser.select("#esen")
browser.fill("input[name=w]", "hola")
browser.click("input[name=B10]")
browser.wait_load()
print "url:", browser.url

# Soup is a PyQuery object
browser.soup.make_links_absolute(base_url=browser.url)
print "html:", browser.soup("#Otbl").html()

# Demonstrate how to download a resource using PyQuery soup
imagedata = browser.download(browser.soup("img:first").attr('src'))
print "image length:", len(imagedata)
browser.close()

########NEW FILE########
__FILENAME__ = browser
#!/usr/bin/python

# Copyright (c) Arnau Sanchez <tokland@gmail.com>

# This script is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# This is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this software.  If not, see <http://www.gnu.org/licenses/>
"""
Spynner is a stateful programmatic web-browser module for Python with
Javascript/AJAX support. It is build upon the PyQtWebKit framework.
"""


import itertools
import cookielib
import tempfile
from pprint import pprint
import urlparse
import urllib2
import time
import sys
import re
import os
from StringIO import StringIO

import pkg_resources
import autopy

try:
    from PySide import QtCore
    QtCore.QString = str
    from PySide.QtCore import SIGNAL, QUrl, QString, Qt, QEvent
    from PySide.QtCore import QSize, QDateTime, QPoint
    from PySide.QtGui import QApplication, QImage, QPainter
    from PySide.QtGui import QCursor, QMouseEvent, QKeyEvent
    from PySide.QtNetwork import QNetworkCookie, QNetworkAccessManager, QSslConfiguration, QSslCipher
    from PySide.QtNetwork import QNetworkCookieJar, QNetworkRequest, QNetworkProxy, QSsl, QSslSocket
    from PySide.QtWebKit import QWebPage, QWebView
    HAS_PYSIDE = True
except Exception, e:
    HAS_PYSIDE = False
    from PyQt4 import QtCore
    from PyQt4.QtCore import SIGNAL, QUrl, QString, Qt, QEvent
    from PyQt4.QtCore import QSize, QDateTime, QPoint
    from PyQt4.QtGui import QApplication, QImage, QPainter
    from PyQt4.QtGui import QCursor, QMouseEvent, QKeyEvent
    from PyQt4.QtNetwork import QNetworkCookie, QNetworkAccessManager, QSslConfiguration, QSslCipher
    from PyQt4.QtNetwork import QNetworkCookieJar, QNetworkRequest, QNetworkProxy, QSsl, QSslSocket
    from PyQt4.QtWebKit import QWebPage, QWebView
    from PyQt4.QtWebKit import QWebInspector


SpynnerQapplication = None


# Debug levels
ERROR, WARNING, INFO, DEBUG = range(4)
argv = ['dummy']
_marker = []


class Browser(object):
    """
    Stateful programmatic web browser class based upon QtWebKit.
    """
    errorCode = None
    errorMessage = None
    _javascript_directories = [
        pkg_resources.resource_filename('spynner', 'javascript'),
    ]
    _jquery = 'jquery-1.5.2.js'
    _jquery_simulate = 'jquery.simulate.js'

    def __init__(self,
                 qappargs=None,
                 debug_level=ERROR,
                 want_compat=False,
                 embed_jquery=False,
                 embed_jquery_simulate=False,
                 additional_js_files = None,
                 jslib = None,
                 download_directory = ".",
                 user_agent = None,
                 debug_stream = sys.stderr,
                 event_looptime = 0.01 ,
                 ignore_ssl_errors = True,
                 headers = None,
                 ssl_protocol=None,
                 ssl_ciphers = None,
                 inspector=False,
                ):
        """
        Init a Browser instance.
        @param qappargs: Arguments for QApplication constructor.
        @param debug_level: Debug level logging (L{ERROR} by default)
        @param want_compat: set jquery compatiblity mode to "self.jslib"
        @param jslib:  IF True: Use jQuery.noConflict to "jslib", else just use '$'
        @param download_directory:  Directory where downloaded files will be stored.
        @param user_agent User agent for requests (see QWebPage::userAgentForUrl for details)
        @param event_looptime Event loop dispatcher loop delay (seconds).
        @apram ignore_ssl_errors  If True, ignore SSL certificate errors.
        @param debug_stream  File-like stream where debug output will be written.
        @param headers (list of tuple) http headers to send with every request
        @param ssl_protocol SSL protocol to force use of:
                QSsl.SslV3
                QSsl.SslV2
                QSsl.TlsV1
                QSsl.UnknownProtocol
                QSsl.AnyProtocol
                QSsl.TlsV1SslV3
                QSsl.SecureProtocols

        Important vars:

            - self.webpage: QwebPage object
            - self.application : QApplication object
            - self.webframe: active QWebFrame object
            - self.manager: QNetworkAccessManager object
            - self.files: represent a list of dicts tracking downloaded files where the download key
              is the path, each entry is in the form {'reply': replyobj, 'req': reqobj}
        """
        self.download_directory = download_directory
        import spynner
        self.ssl_protocol = ssl_protocol
        self.sslconf = QSslConfiguration.defaultConfiguration()
        ciphers = []
        self.ssl_ciphers = ssl_ciphers
        if not self.ssl_ciphers:
            self.ssl_ciphers = []
        for cip in self.sslconf.ciphers():
            if (
                (toString(cip.name()) in self.ssl_ciphers)
                or not self.ssl_ciphers
            ):
                ciphers.append(cip)
        self.sslconf.setCiphers(ciphers)
        if not spynner.SpynnerQapplication:
            spynner.SpynnerQapplication = QApplication(spynner.argv)
        self.application = spynner.SpynnerQapplication
        self.want_compat = want_compat
        self.embed_jquery = embed_jquery
        self.embed_jquery_simulate = embed_jquery_simulate
        self.debug_stream = debug_stream
        self.user_agent = user_agent
        # self._headers is just internal
        # to manager.create_request
        # as we cant change the useragent
        # directly via the adequat http header (qwebframe
        # will overwrite it later)
        self.headers = headers
        self._headers = []
        if self.headers is None:
            self.headers = []
        if self.user_agent:
            self.headers.append(('User-Agent', self.user_agent))
        self.additional_js_files = additional_js_files
        self.additional_js = ""
        self.event_looptime = event_looptime
        self.ignore_ssl_errors = ignore_ssl_errors
        """PyQt4.QtWebKit.QWebPage object."""
        wp = self.webpage = QWebPage()
        # Network Access Manager and cookies
        #mngr = self.manager = QNetworkAccessManager()
        mngr = self.manager = NManager.new(self)
        """PyQt4.QtNetwork.QTNetworkAccessManager object."""
        self.webpage.setNetworkAccessManager(self.manager)
        if not self.additional_js_files:
            self.additional_js_files = []
        self.jslib = jslib
        if not self.want_compat:
            if jslib is None:
                self.jslib = '$'
            else:
                self.jslib = jslib
        else:
            self.jslib = 'spynnerjq'
        self.debug_level = debug_level
        """PyQt4.QtWebKit.QWebFrame main webframe object."""
        self.webview = None
        """PyQt4.QtWebKit.QWebView object."""
        self._url_filter = None
        self._webframe = None
        self._html_parser = None
        self.files = []
        # Javascript
        directory = _first(self._javascript_directories, os.path.isdir)
        if not directory:
            raise SpynnerError("Cannot find javascript directory: %s" %
                self._javascript_directories)
        self.jquery = open(os.path.join(directory, self._jquery)).read()
        self.jquery_simulate = open(os.path.join(directory, self._jquery_simulate)).read()
        for fn in self.additional_js_files:
            if not os.path.exists(fn):
                fn = os.path.join(directory, fn)
            self.additional_js += "\n%s" % open(fn).read()
        wp.javaScriptAlert = self._javascript_alert
        wp.javaScriptConsoleMessage = self._javascript_console_message
        wp.javaScriptConfirm = self._javascript_confirm
        wp.javaScriptPrompt = self._javascript_prompt
        self._javascript_confirm_callback = None
        self._javascript_confirm_prompt = None
        """PyQt4.QtNetwork.QNetworkCookieJar object."""
        self.cookies = []
        mngr.sslErrors.connect(self._on_manager_ssl_errors)
        mngr.finished.connect(self._on_reply)
        mngr.authenticationRequired.connect(
            self._on_authentication_required)
        self._operation_names = dict(
            (getattr(QNetworkAccessManager, s + "Operation", s),
             s.lower())
            for s in ("Get", "Head", "Post",
                      "Put", "Delete", "Custom"))
        for i in self._operation_names.keys():
            if isinstance(i, basestring):
                del self._operation_names[i]
        # Webpage slots
        self._load_status = None
        self._replies = 0
        wp.setForwardUnsupportedContent(True)
        wp.unsupportedContent.connect(
            self._on_unsupported_content)
        wp.loadFinished.connect(self._on_load_finished)
        wp.loadStarted.connect(self._on_load_started)
        if inspector:
            self.inspector = QWebInspector()
            self.inspector.setPage(self.webpage)
            self.inspector.setVisible(True)

    @property
    def webframe(self):
        """PyQt4.QtNetwork.QWebFrame object."""
        if self._webframe is None:
            self.setframe_obj()
        return self._webframe

    def _events_loop(self, wait=None):
        if wait is None:
            wait = self.event_looptime
        self.application.processEvents()
        time.sleep(wait)

    def _on_load_started(self):
        self._load_status = None
        self._debug(INFO, "Page load started")

    def _on_manager_ssl_errors(self, reply, errors):
        url = unicode(toString(reply.url()))
        if self.ignore_ssl_errors:
            self._debug(WARNING, "SSL certificate error ignored: %s" % url)
            reply.ignoreSslErrors()
        else:
            self._debug(WARNING, "SSL certificate error: %s" % url)

    def _on_authentication_required(self, reply, authenticator):
        url = unicode(toString(reply.url()))
        realm = unicode(authenticator.realm())
        self._debug("HTTP auth required: %s (realm: %s)" % (url, realm))
        if not self._http_authentication_callback:
            self._debug(WARNING, "HTTP auth required, but no callback defined")
            return
        credentials = self._http_authentication_callback(url, realm)
        if credentials:
            user, password = credentials
            self._debug(INFO, "callback returned HTTP credentials: %s/%s" %
                (user, "*"*len(password)))
            authenticator.setUser(user)
            authenticator.setPassword(password)
        else:
            self._debug(WARNING, "HTTP auth callback returned no credentials")

    def _on_reply(self, reply):
        self._replies += 1
        self._reply_url = unicode(toString(reply.url()))
        self._reply_status = not bool(reply.error())
        self.cookies = merge_cookies(
            self.cookies,
            self.manager.cookieJar().allCookies())
        try:
            http_status = "%s" % toString(
                reply.attribute(QNetworkRequest.HttpStatusCodeAttribute))
            http_status_m = "%s" % toString(
                reply.attribute(QNetworkRequest.HttpReasonPhraseAttribute))
        except:
            http_status_m, http_status = "", ""


        if reply.error():
            self._debug(WARNING, "Reply error: %s/%s %s - %d (%s)" %
                (http_status, http_status_m,
                 self._reply_url, reply.error(), reply.errorString()))
            self.errorCode = reply.error()
            self.errorMessage = reply.errorString()
        else:
            self._debug(INFO, "Reply: %s/%s - %s" % (
                http_status, http_status_m, self._reply_url))
        for header in reply.rawHeaderList():
            self._debug(DEBUG, "  %s: %s" % (header, reply.rawHeader(header)))

    def _on_unsupported_content(self, reply, outfd=None):
        if not reply.error():
            self._start_download(reply, outfd)
        else:
            self._debug(ERROR, "Error on unsupported content: %s" % reply.errorString())

    def _javascript_alert(self, webframe, message):
        self._debug(INFO, "Javascript alert: %s" % message)
        if self.webview:
            QWebPage.javaScriptAlert(self.webpage, webframe, message)

    def _javascript_console_message(self, message, line, sourceid):
        if line:
            self._debug(INFO, "Javascript console (%s:%d): %s" %
                (sourceid, line, message))
        else:
            self._debug(INFO, "Javascript console: %s" % message)

    def _javascript_confirm(self, webframe, message):
        smessage = unicode(message)
        url = webframe.url()
        self._debug(INFO, "Javascript confirm (webframe url = %s): %s" %
            (url, smessage))
        if self._javascript_confirm_callback:
            value = self._javascript_confirm_callback(url, smessage)
            self._debug(INFO, "Javascript confirm callback returned %s" % value)
            return value
        return QWebPage.javaScriptConfirm(self.webpage, webframe, message)

    def _javascript_prompt(self, webframe, message, defaultvalue, result):
        url = webframe.url()
        smessage = unicode(message)
        self._debug(INFO, "Javascript prompt (webframe url = %s): %s" %
            (url, smessage))
        if self._javascript_prompt_callback:
            value = self._javascript_prompt_callback(url, smessage, defaultvalue)
            self._debug(INFO, "Javascript prompt callback returned: %s" % value)
            if value in (False, None):
                return False
            result.clear()
            result.append(value)
            return True
        return QWebPage.javaScriptPrompt(self.webpage, webframe, message,
            defaultvalue, result)

    def _on_webview_destroyed(self, window):
        self.webview = None

    def _on_load_finished(self, successful):
        if hasattr(self, "webpage"):
            self.setframe_obj()
        self._load_status = successful
        status = {True: "successful", False: "error"}[successful]
        self._debug(INFO, "Page load finished (%d bytes): %s (%s)" %
            (len(self.html), self.url, status))

    def _get_filepath_for_url(self, url, reply=None):
        urlinfo = urlparse.urlsplit(url)
        path = os.path.join(os.path.abspath(self.download_directory), urlinfo.netloc)
        if urlinfo.path != '/':
            p = urlinfo.path
            if len(p) > 2:
                if p[0] == '/':
                    p = p[1:]
            path = os.path.join(path, p)
        if reply.hasRawHeader('content-disposition'):
            cd = '%s' % reply.rawHeader('content-disposition')
            pattern = 'attachment;filename=(.*)'
            if re.match(pattern, cd):
                filename = re.sub('attachment;filename=(.*)', '\\1', cd)
                path = os.path.join(path, filename)
        if not os.path.isdir(os.path.dirname(path)):
            os.makedirs(os.path.dirname(path))
        if path is None:
            raise SpynnerError('Download mode is unknown, can\'t determine the final filename')
        return path

    def _start_download(self, reply, outfd):
        url = unicode(toString(reply.url()))
        path = None
        if outfd is None:
            path = self._get_filepath_for_url(url, reply)
            outfd = open(path, "wb")
        def _on_ready_read():
            data = reply.readAll()
            if getattr(reply, 'downloaded_nbytes', None) is None:
                reply.downloaded_nbytes= 0
            reply.downloaded_nbytes += len(data)
            outfd.write(data)
            self._debug(DEBUG, "Read from download stream (%d bytes): %s"
                % (len(data), url))
        def _on_network_error():
            self._debug(ERROR, "Network error on download: %s" % url)
        def _on_finished():
            data = reply.readAll()
            if len(data):
                if getattr(reply, 'downloaded_nbytes at end', None) is None:
                    reply.downloaded_nbytes= 0
                reply.downloaded_nbytes += len(data)
                outfd.write(data)
            self._debug(DEBUG, "Read from download stream at end (%d bytes): %s"
                % (len(data), url))
            suf = ''
            if path is not None:
                outfd.flush()
                dict(self.files)[path]['finished'] = True
                suf = ' in {0}'.format(path)
            self._debug(INFO, "Download finished: {0}{1}".format(url, path))

        if path is not None:
            self.files.append((path, {'reply':reply,
                                      'readed': False,
                                      'finished':False,}))
        reply.readyRead.connect(_on_ready_read)
        reply.error.connect(_on_network_error)
        reply.finished.connect(_on_finished)
        self._debug(INFO, "Start download: %s" % url)

    def _wait_load(self, timeout=None):
        self._events_loop(0.0)
        if self._load_status is not None:
            load_status = self._load_status
            self._load_status = None
            return load_status
        itime = time.time()
        while self._load_status is None:
            if timeout and time.time() - itime > timeout:
                raise SpynnerTimeout("Timeout reached: %d seconds" % timeout)
            self._events_loop()
        self._events_loop(0.0)
        if self._load_status:
            self.load_js()
            self.webpage.setViewportSize(self.webpage.mainFrame().contentsSize())
        load_status = self._load_status
        self._load_status = None
        return load_status

    def _debug(self, level, *args):
        if level <= self.debug_level:
            kwargs = dict(outfd=self.debug_stream)
            _debug(*args, **kwargs)

    def get_js_obj_length(self, res):
        if res.type() != res.Map:
            return False
        resmap = res.toMap()
        lenfield = QString(u'length')
        if lenfield not in resmap:
            return False
        if resmap[lenfield].type() == resmap[lenfield].Double:
            return int(resmap[lenfield].toDouble()[0])
        else:
            return resmap[lenfield].toInt()[0]

    def jslen(self, selector):
        res = self.runjs("%s('%s')" % (self.jslib, selector))
        return self.get_js_obj_length(res)

    def _runjs_on_jquery(self, name, code):
        res = self.runjs(code)
        if not isinstance(self.get_js_obj_length(res), int):
            raise SpynnerJavascriptError("error on %s: %s" % (name, code))
        return res

    def _get_html(self):
        return unicode(self.webframe.toHtml())

    def _get_soup(self):
        if not self._html_parser:
            raise SpynnerError("Cannot get soup with no HTML parser defined")
        return self._html_parser(self.html)

    def _get_url(self):
        return unicode(toString(self.webframe.url()))

    url = property(_get_url)
    """Current URL."""

    contents = property(_get_html)
    """Rendered HTML in current page."""
    html = property(_get_html)
    """Rendered HTML in current page."""

    soup = property(_get_soup)
    """HTML soup (see L{set_html_parser})."""

    def load(self,
             url,
             load_timeout=10,
             wait_callback = None,
             tries=None,
             operation=QNetworkAccessManager.GetOperation,
             body=None,
             headers=None
            ):
        """Load a web page and return status (a boolean).
        @param url url to open
        @param headers http headers tuples
                       eg: [('User-Agent', 'foo')]
        @param url url to open
        @param body request body (string)
        @param operation one of:
            QNetworkAccessManager.HeadOperation
            QNetworkAccessManager.GetOperation
            QNetworkAccessManager.PutOperation
            QNetworkAccessManager.PostOperation
            QNetworkAccessManager.DeleteOperation
            QNetworkAccessManager.CustomOperation
        @param load_timeout timeout to load the page, or if you use wait_callback, time between retries
        @param wait_callback a callback to test if content is ready
        @param tries set to True for unlimited retries, to int for limited to tries, tries.

        eg:

            Open google

            >>> br.load('http://www.google.fr')

            Same thing except we will try to see if there is 'google' in the html,
            thus with 3 wills at 10 seconds of interval

            >>> def wait_load(b):
            ...     return 'google' in b.html.lower()
            >>> br.load('http://www.google.fr', wait_callback=wait_load, tries=3)

        """
        if not headers:
            headers = []
        if not body:
            body = ""
        self._headers = self.headers[:]
        self._headers.extend(headers)
        req = self.make_request(url)
        self.webframe.load(req, operation, body)
        if wait_callback is None:
            return self._wait_load(timeout = load_timeout)
        else:
            return self.wait_for_content(wait_callback, tries=tries, delay=load_timeout)


    def make_request(self, url, operation="GET"):
        if operation:
            operation = ("%s" % operation).lower()
        if isinstance(url, basestring):
            url = QUrl(url)
        if not isinstance(url, QNetworkRequest):
            url = QNetworkRequest(url)
        for header, value in self._headers:
            url.setRawHeader(header, value)
        url = self.apply_ssl(url)
        return url

    def apply_ssl(self, request):
        if self.ssl_protocol:
            if self.sslconf.protocol() != self.ssl_protocol:
                self.sslconf.setProtocol(self.ssl_protocol)
                QSslConfiguration.setDefaultConfiguration(self.sslconf)
        request.setSslConfiguration(self.sslconf)
        return request

    def is_jquery_loaded(self):
        return toString(self.runjs('typeof(spynner_jquery_loaded);', debug=False)) != 'undefined'

    def is_jquery_simulate_loaded(self):
        return toString(
            self.runjs('typeof(spynner_jquery_simulate_loaded);', debug=False)) != 'undefined'

    def is_additional_js_loaded(self):
        return toString(
            self.runjs('typeof(spynner_additional_js_loaded);', debug=False)) != 'undefined'

    def load_jquery(self, force=False):
        """Load jquery in the current frame"""
        jscode = ''
        if self.embed_jquery or force:
            if not self.is_jquery_loaded():
                jscode += self.jquery
                if self.want_compat or (self.jslib != '$'):
                    jscode += "\nvar %s = jQuery.noConflict();" % self.jslib
                jscode += "var spynner_jquery_loaded = 1 ;"
                self.runjs(jscode, debug=False)

    def load_js(self):
        self.load_jquery()
        self.load_jquery_simulate()
        self.load_additional_js()

    def load_jquery_simulate(self, force=False):
        """Load jquery simulate in the current frame"""
        if self.embed_jquery_simulate or force:
            if not self.is_jquery_simulate_loaded():
                self.runjs(self.jquery_simulate, debug=False)
                self.runjs("var spynner_jquery_simulate_loaded = 1 ;", debug=False)

    def load_additional_js(self, force=False):
        """Load jquery in the current frame"""
        if not self.is_additional_js_loaded() or force:
            if len(self.additional_js.strip()) > 0:
                self.runjs(self.additional_js, debug=False)
            self.runjs("var spynner_additional_js_loaded = 1 ;", debug=False)

    def wait_a_little(br, timeout):
        try:
            br.wait_load(timeout)
        except SpynnerTimeout, e:
            pass

    def wait_requests(self, wait_requests = None, url = None, url_regex = None):
        if wait_requests:
            while self._replies < wait_requests:
                self._events_loop()
            self._events_loop(0.0)
        if url_regex or url:
            last_replies = self._replies
            while True:
                if last_replies != self._replies:
                    if url_regex:
                        if re.search(url_regex, self._reply_url):
                            break
                    elif url:
                        if url == self._reply_url:
                            break
                self._events_loop()
            self._events_loop(0.0)

    def sendText(self, selector, text, keyboard_modifiers = Qt.NoModifier, wait_load=False, wait_requests=None, timeout=None):
        """
        Send text in any element (to fill it for example)

        @param selector: QtWebkit Selector
        @param keys to input in the QT way
        @param wait_load: If True, it will wait until a new page is loaded.
        @param timeout: Seconds to wait for the page to load before raising an exception.
        @param wait_requests: How many requests to wait before returning. Useful for AJAX requests.

        >>> br.sendText('#val_cel_dentifiant', 'fancy text')
        """
        element = self.webframe.findFirstElement(selector)
        element.setFocus()
        eventp = QKeyEvent(QEvent.KeyPress, Qt.Key_A, keyboard_modifiers, QString(text))
        self.application.sendEvent(self.webview, eventp)
        self._events_loop(timeout)
        self.wait_requests(wait_requests)
        if wait_load:
            return self._wait_load(timeout)

    def sendKeys(self, selector, keys, keyboard_modifiers = Qt.NoModifier, wait_load=False, wait_requests=None, timeout=None):
        """
        Click any clickable element in page.
        see http://www.riverbankcomputing.co.uk/static/Docs/PyQt4/html/qt.html#Key-enum

        @param selector: jQtWebkit Selector
        @param keys to input in the QT way
        @param wait_load: If True, it will wait until a new page is loaded.
        @param timeout: Seconds to wait for the page to load before
                                       raising an exception.
        @param wait_requests: How many requests to wait before returning. Useful
                              for AJAX requests.

        Send raw keys:
        >>> br.sendKeys('#val_cel_dentifiant', [Qt.Key_A,Qt.Key_A,Qt.Key_C,]
        """
        element = self.webframe.findFirstElement(selector)
        element.setFocus()
        for key in keys:
            eventp = QKeyEvent(QEvent.KeyPress, key, keyboard_modifiers)
            self.application.sendEvent(self.webview, eventp)
            self._events_loop(timeout)
        self.wait_requests(wait_requests)
        if wait_load:
            return self._wait_load(timeout)

    def click(self, selector, wait_load=False, wait_requests=None, timeout=None):
        """
        Click any clickable element in page.

        @param selector: jQuery selector.
        @param wait_load: If True, it will wait until a new page is loaded.
        @param timeout: Seconds to wait for the page to load before
                                       raising an exception.
        @param wait_requests: How many requests to wait before returning. Useful
                              for AJAX requests.

        By default this method will not wait for a page to load.
        If you are clicking a link or submit button, you must call this
        method with C{wait_load=True} or, alternatively, call
        L{wait_load} afterwards. However, the recommended way it to use
        L{click_link}.

        When a non-HTML file is clicked this method will download it. The
        file is automatically saved keeping the original structure (as
        wget --recursive does). For example, a file with URL
        I{http://server.org/dir1/dir2/file.ext} will be saved to
        L{download_directory}/I{server.org/dir1/dir2/file.ext}.
        """
        if not self.embed_jquery_simulate:
            return self.wk_click(selector,
                                 wait_load=wait_load,
                                 wait_requests=wait_requests,
                                 timeout=timeout)
        jscode = "%s('%s').simulate('click');" % (self.jslib, selector)
        self._replies = 0
        self._runjs_on_jquery("click", jscode)
        self.wait_requests(wait_requests)
        if wait_load:
            return self._wait_load(timeout)

    def click_link(self, selector, timeout=None):
        """Click a link and wait for the page to load."""
        return self.click(selector, wait_load=True, timeout=timeout)

    def click_ajax(self, selector, wait_requests=1, timeout=None):
        """Click a AJAX link and wait for the request to finish."""
        return self.click(selector, wait_requests=wait_requests, timeout=timeout)

    def move_mouse(self, selector, timeout=1, offsetx=0, offsety=0, real=True):
        """Move the move to the css selector"""
        self.moveMouse(
            self.getPosition(
                selector,
                offsetx=offsetx, offsety=offsety),
            timeout=timeout,
            real=real)

    def moveMouse(self, where, timeout=1, real=False,
                  offsetx=0, offsety=0,
                  adapt_size=False, pdb=False):
        """Move the mouse to a relative to the window point."""
        if adapt_size:
            time.sleep(1)
        if not real:
            where = self.getRealPosition(where)
        where = QPoint(int(where.x())+offsetx,
                       int(where.y())+offsety)
        self.webview.grabMouse()
        #self._events_loop(timeout)
        #cursorw = self.application.desktop().cursor()
        cursorw = QCursor()
        cursorw.setPos(where)
        self.webview.releaseMouse()
        #self._events_loop(timeout)
        return cursorw

    def getRealPosition(self, point, offsetx=0, offsety=0):
        """Compute the coordinates by merging with the containing frame.
        @param point: (QPoint)
        """
        rect = self.webframe.geometry()
        where = QPoint(rect.x() + point.x() + offsetx,
                       rect.y() + point.y() + offsety)
        where = self.webview.mapToGlobal(where)
        return where

    def nativeClickAt(self, where, timeout=1, real=False, pdb=False):
        """Click on an arbitrar location of the browser.
        @param where: where to click (QPoint)
        @param real: if not true coordinates are relative to the window instead of the screen
        @timeout seconds: seconds to wait after click
        """
        if not real:
            where = self.getRealPosition(where)
        self.moveMouse(where, timeout=timeout, real=True, pdb=pdb)
        """do not work anymore, rely on autopy
        def click():
            in the meantime
            w = self.webview.page()
            buttons = Qt.MouseButtons(Qt.LeftButton)
            eventp = QMouseEvent(QEvent.MouseButtonPress, where,
                                 Qt.LeftButton, buttons, Qt.NoModifier)
            eventl = QMouseEvent(QEvent.MouseButtonRelease, where,
                                 Qt.LeftButton, buttons, Qt.NoModifier)
            f.application.sendEvent(w, eventp)
            self.application.sendEvent(w, eventl)
            self._events_loop(0)
            self._events_loop(0)
            self.application.processEvents()
            self.application.processEvents()"""
        autopy.mouse.click()
        try:
            self._events_loop(0.05)
            self._events_loop(0.05)
        except:
            pass

    def getPosition(self, selector, offsetx=0, offsety=0):
        """Get the position QPoint(x,y) of a css selector.
        @param selector: The css Selector to query against
        """
        jscode = "off = %s('%s').offset(); off.left+','+off.top" % (self.jslib, selector)
        self._replies = 0
        try:
            item = self.webframe.findFirstElement(selector)
            geo = item.geometry()
            twhere = geo.topLeft()
            twhere = QPoint(int(twhere.x()) + offsetx,
                            int(twhere.y()) + offsety)
            where = self.webview.mapToGlobal(twhere)
            if where == twhere:
                where = self.webview.mapToGlobal(where)
        except:
            #try also using js
            try:
                x, y = ("%s" % toString(self.runjs(jscode, debug=False))).split(',')
                twhere = QPoint(int(x)+offsetx, int(y)+offsety)
                where = self.webview.mapToGlobal(twhere)
                if where == twhere:
                    where = self.webview.mapToGlobal(where)
            except Exception, e:
                    raise SpynnerError('Cant find %s (%s)' % (selector, e))
        return where

    def wk_click_element(self, element, wait_load=False, wait_requests=None, timeout=None):
        """
        Click on an element by using raw javascript WebKit.click() method.

        @param element: QWebElement object
        @param wait_load: If True, it will wait until a new page is loaded.
        @param timeout: Seconds to wait for the page to load before
                                       raising an exception.
        @param wait_requests: How many requests to wait before returning. Useful
                              for AJAX requests.

        By default this method will not wait for a page to load.
        If you are clicking a link or submit button, you must call this
        method with C{wait_load=True} or, alternatively, call
        L{wait_load} afterwards. However, the recommended way it to use
        L{click_link}.

        When a non-HTML file is clicked this method will download it. The
        file is automatically saved keeping the original structure (as
        wget --recursive does). For example, a file with URL
        I{http://server.org/dir1/dir2/file.ext} will be saved to
        L{download_directory}/I{server.org/dir1/dir2/file.ext}.
        """
        #element.evaluateJavaScript("this.click()")
        jscode = (
            "var e = document.createEvent('MouseEvents');"
            "e.initEvent( 'click', true, true );"
            "this.dispatchEvent(e);"
        )
        element.evaluateJavaScript(jscode)
        time.sleep(0.5)
        self.wait_requests(wait_requests)
        if wait_load:
            return self._wait_load(timeout)

    def wk_click_element_link(self, element, timeout=None):
        """Click a link and wait for the page to load.
        @param selector: WebKit xpath selector to an element
        @param: timeout timeout to wait in seconds
        """
        return self.wk_click_element(element, wait_load=True, timeout=timeout)

    def wk_click_element_ajax(self, element, wait_requests=1, timeout=None):
        """Click a AJAX link and wait for the request to finish.
        @param selector: WebKit xpath selector to an element
        @param wait_requests: How many requests to wait before returning. Useful for AJAX requests.
        @param: timeout timeout to wait in seconds
        """
        return self.wk_click_element(element, wait_requests=wait_requests, timeout=timeout)

    def wk_click(self, selector, wait_load=False, wait_requests=None, timeout=None):
        """
        Select an element with a CSS2 selector and then click by using raw javascript WebKit.click() method.
        See the wk_click_element functions for additional documentation

        @param selector: WebKit selector.
        @param wait_load: If True, it will wait until a new page is loaded.
        @param timeout: Seconds to wait for the page to load before
                                       raising an exception.
        @param wait_requests: How many requests to wait before returning. Useful
                              for AJAX requests.
        """
        element = self.webframe.findFirstElement(selector)
        return self.wk_click_element(element, wait_load=wait_load, wait_requests=wait_requests, timeout=timeout)

    def wk_click_link(self, selector, timeout=None):
        """Click a link and wait for the page to load.
        See the wk_click_element_link functions for additional documentation
        @param selector: WebKit xpath selector to an element
        @param: timeout timeout to wait in seconds
        """
        element = self.webframe.findFirstElement(selector)
        return self.wk_click_element_link(element, timeout=timeout)

    def wk_click_ajax(self, selector, wait_requests=1, timeout=None):
        """Click a AJAX link and wait for the request to finish.
        See the wk_click_element_ajax functions for additional documentation
        @param selector: WebKit xpath selector to an element
        @param wait_requests: How many requests to wait before returning. Useful
                              for AJAX requests.
        @param: timeout timeout to wait in seconds
        """
        element = self.webframe.findFirstElement(selector)
        return self.wk_click_element_ajax(element, wait_requests=wait_requests, timeout=timeout)

    def native_click(self, selector, wait_load=False, wait_requests=None, timeout=1, offsetx = 5, offsety = 5, real=False, pdb=False):
        """
        Click any clickable element in page by sending a raw QT mouse event.

        @param selector: jQuery selector.
        @param wait_load: If True, it will wait until a new page is loaded.
        @param timeout: Seconds to wait for the page to load before
                                       raising an exception.
        @param wait_requests: How many requests to wait before returning. Useful
                              for AJAX requests.

        @param offsetx: offset to click on the widget to the top left of it on the X axis (left to right)
        @param offsety: offset to click on the widget to the top left of it on the Y axix (top to bottom)
        """
        where = self.getPosition(selector)
        item = self.webframe.findFirstElement(selector)
        item.setFocus()
        where = QPoint(where.x() + offsetx, where.y() + offsety)
        self.nativeClickAt(where, timeout, real=real, pdb=pdb)
        self.wait_requests(wait_requests)
        if wait_load:
            return self._wait_load(timeout)

    def native_click_link(self, selector, timeout=None, offsetx = 0, offsety = 0):
        """Click a link and wait for the page to load using a real mouse event.
        @param selector: jQuery selector.
        @param timeout: Seconds to wait for the page to load before
                        raising an exception.
        @param offsetx: offset to click on the widget to the top left of it on the X axis (left to right)
        @param offsety: offset to click on the widget to the top left of it on the Y axix (top to bottom)
        """
        return self.native_click(selector, wait_load=True, timeout=timeout, offsetx=offsetx, offsety=offsety)

    def native_click_ajax(self, selector, wait_requests=1, timeout=None, offsetx = 0, offsety = 0):
        """Click a AJAX link using a raw mouse click and wait for the request to finish.
        @param selector: jQuery selector.
        @param timeout: Seconds to wait for the page to load before
                        raising an exception.
        @param offsetx: offset to click on the widget to the top left of it on the X axis (left to right)
        @param offsety: offset to click on the widget to the top left of it on the Y axix (top to bottom)
        """
        return self.native_click(selector, wait_requests=wait_requests, timeout=timeout, offsetx=offsetx, offsety=offsety)

    def wait_load(self, timeout=None):
        """
        Wait until the page is loaded.

        @param timeout: Time to wait (seconds) for the page load to complete.
        @return: Boolean state
        @raise SpynnerTimeout: If timeout is reached.
        """
        return self._wait_load(timeout)

    def wait_for_content(self, callback, tries=None, error_message=None, delay=5):
        """
        Wait until the page is loaded.

        @param content: callback that takes the browser as input must return true when suceed
        @param timeout: number of retries / True for no limit
        @param delay: delay between retries
        @param error_message: additional message to set in the error message
        @return: Boolean state
        @raise SpynnerTimeout: If timeout is reached.

        >>> def wait_toto(browser):
        ...     if 'toto' in browser.html:
        ...         return True
        ...     return False
        >>> br.wait_for_content(wait_toto)
        """
        ref_tries = tries
        ret = None
        found = False
        loaded = False
        head = "SPYNNER waitload:"
        loaded_msg = (
            '%s content loaded, waiting for '
            'content to mach the callback' % head)
        waiting_msg = (
            '%s content not loaded, '
            'fallback by waiting' % head)
        to_msg = ("%s %s" % (
                  "%s Timeout reached: " % head,
                  "%d retries for %ss delay."))
        found_msg = (
            '%s The callback found what it '
            'was waiting for in its contents!' % head)
        for_ = "%s FOR: %s" % (
            head, error_message)
        if not tries:
            tries = True
        while bool(tries) and not found:
            if (
                isinstance(tries, int)
                and not isinstance(tries, bool)
            ):
                if tries > 0:
                    tries -= 1
            if callback(self):
                found = True
            if not found:
                if error_message:
                    self._debug(DEBUG, for_)
                if not loaded:
                    try:
                        loaded = self._wait_load(timeout=delay)
                        self._debug(DEBUG, loaded_msg)
                    except SpynnerTimeout, e:
                        self._debug(DEBUG, waiting_msg)
                else:
                    self._debug(DEBUG, loaded_msg)
                    time.sleep(delay)
        if not found:
            if not isinstance(ref_tries, int):
                ref_tries = 'unlimited'
            msg = to_msg % (ref_tries, delay)
            if error_message:
                msg += u'\n%s' % error_message
            raise SpynnerTimeout(msg)
        else:
            self._debug(DEBUG, found_msg)
        load_status = self._load_status
        self._load_status = None
        return load_status

    def wait(self, waittime):
        """
        Wait some time.

        @param waittime: Time to wait (seconds).

        This is an active wait, the events loop will be run, so it
        may be useful to wait for synchronous Javascript events that
        change the DOM.
        """
        itime = time.time()
        while time.time() - itime < waittime:
            self._events_loop()

    def close(self):
        """Close Browser instance and release resources."""
        if self.manager:
            del self.manager
        if self.webpage:
            del self.webpage
        if self.webview:
            self.destroy_webview()
        self.application.exit()

    def search_element_text(self, search_text, element='a', case_sensitive=False, match_exactly=True):
        """
        Search all elements on a page for the specified text, returns a list of elements that contain it.

        @param search_text: The text to search for.
        @param element: The type of element to search, defaults to anchor tag.
        @param case_sensitive: If true the search will be case sensitive.
        @param match_exactly: If true will match the element's content exactly.
        @return: A list of elements
        """
        if not case_sensitive:
            search_text=search_text.lower()
        all_elements=self.webframe.findAllElements(element).toList()
        result=[]
        for e in all_elements:
            text=e.toPlainText().__str__()
            if not case_sensitive:
                text=text.lower()
            if match_exactly is True and search_text == text:
                result.append(e)
            elif match_exactly is False and search_text in text:
                result.append(e)
        return result

    def create_webview(self, show=False, force=False):
        """Create a QWebView object and insert current QWebPage."""
        if force and (self.webview is not None):
            self.destroy_webview()
        if self.webview is not None:
            return
        self.webview = QWebView()
        self.webview.setPage(self.webpage)
        window = self.webview.window()
        window.setAttribute(Qt.WA_DeleteOnClose)
        window.destroyed.connect(self._on_webview_destroyed)
        self.application.syncX()

    def destroy_webview(self):
        """Destroy current QWebView."""
        if not self.webview:
            return
        self.webview.close()
        del self.webview

    def show(self, maximized=True, force=False):
        """Show webview browser."""
        self.create_webview(show=True, force=force)
        self.webview.show()
        if maximized:
            self.webview.setWindowState(Qt.WindowMaximized)

    def hide(self):
        """Hide webview browser."""
        if self.webview is not None:
            self.webview.hide()
        else:
            self._debug(DEBUG, "Webview is not initialized")

    def browse(self):
        """Let the user browse the current page (infinite loop)."""
        if self.webview is None:
            self.create_webview()
        self.show()
        while self.webview:
            self._events_loop()

    def set_webframe_to_default(self):
        self.setframe_obj()

    def setframe_obj(self, frame=_marker):
        if frame is _marker:
            frame = self.webpage.mainFrame()
        try:
           self._webframe = frame
        except:
            raise SpynnerError("childframe does not exist")
        self.load_js()

    def adapt_size(self, frame=None):
        if not frame:
            frame = self.webpage.mainFrame()
        self.setframe_obj(frame)
        self.webpage.setViewportSize(
            frame.contentsSize())
        self.webview.adjustSize()

    def set_webframe(self, framenumber):
        cf = self.webframe.childFrames()
        f = cf[int(framenumber)]
        self.setframe_obj(f)

    def fill(self, selector, value):
        """Fill an input text with a string value using a jQuery selector."""
        escaped_value = value.replace("'", "\\'")
        jscode = "%s('%s').val('%s')" % (self.jslib, selector, escaped_value)
        self._runjs_on_jquery("fill", jscode)

    def wk_fill(self, selector, value):
        """Fill an input text with a string value using a WebKit selector and using the webkit webframe object."""
        element = self.webframe.findFirstElement(selector)
        element.evaluateJavaScript("this.value = '%s'" % value)

    def wk_check_elem(self, element):
        """check an input checkbox using a webkit element."""
        jscode = "this.checked=true;"
        if not isinstance(element, list):
            element = [element]
        for e in element:
            e.evaluateJavaScript(jscode)

    def wk_uncheck_elem(self, element):
        """uncheck input checkbox using a Webkit element"""
        jscode = "this.checked=false;"
        if not isinstance(element, list):
            element = [element]
        for e in element:
            e.evaluateJavaScript(jscode)

    def wk_check(self, selector):
        """check an input checkbox using a css selector."""
        if not isinstance(selector, list):
            selector = [selector]
        elems = []
        for s in selector:
            es = self.webframe.findAllElements(s).toList()
            elems.extend(es)
        return self.wk_check_elem(elems)

    def wk_uncheck(self, selector):
        """uncheck input checkbox using a css selector"""
        if not isinstance(selector, list):
            selector = [selector]
        elems = []
        for s in selector:
            es = self.webframe.findAllElements(s).toList()
            elems.extend(es)
        return self.wk_uncheck_elem(elems)

    def check(self, selector):
        """Check an input checkbox using a jQuery selector."""
        if not isinstance(selector, list):
            selector = [selector]
        for s in selector:
            jscode = "%s('%s').attr('checked', true)" % (self.jslib, s)
            self._runjs_on_jquery("check", jscode)

    def uncheck(self, selector):
        """Uncheck input checkbox using a jQuery selector"""
        if not isinstance(selector, list):
            selector = [selector]
        for s in selector:
            jscode = "%s('%s').attr('checked', false)" % (self.jslib, s)
            self._runjs_on_jquery("uncheck", jscode)

    def radio(self, selector):
        """Choose a radio button a jQuery selector.
        Selector can be a single selector of a list of selectors
        """
        if not isinstance(selector, list):
            selector = [selector]
        jscode = ''
        for s in selector:
            jscode += "%s('%s').attr('checked', 'checked');\n" % (
                self.jslib, s)
        self._runjs_on_jquery("radio", jscode)

    def select(self, selector, remove=True):
        """Choose a option in a select using a jQuery selector.
        Selector can be a single selector of a list of selectors
        """
        if not isinstance(selector, list):
            selector = [selector]
        rjscode = ''
        jscode = ''
        for s in selector:
            if remove:
                rjscode += ("%s('option:selected', "
                            "%s('%s').parents('select')[0])"
                            ".removeAttr('selected');\n" )% (
                                self.jslib, self.jslib, s)
            jscode += "%s('%s').attr('selected', 'selected');\n" % (
                self.jslib, s)
        jscode = rjscode + jscode
        self._runjs_on_jquery("select", jscode)

    def wk_radio(self, selector):
        """Choose a option in a select using  WebKit API.
        @param selector: list of  css selector or css selector  to get the select item.
        """
        if not isinstance(selector, list):
            selector = [selector]
        for s in selector:
            element = self.webframe.findFirstElement(s)
            element.evaluateJavaScript('this.checked = true;')

    def wk_select_elem(self, element, values, remove=True):
        """Choose a option in a select using  WebKit API.
        @param element: webkit WebElemement
        """
        toselect = []
        notselect = []
        all_options = []
        for option in element.findAll('option'):
            if not option in all_options:
                all_options.append(option)
            if values:
                for v in values:
                    if option.attribute('value') == v:
                        if not option in toselect:
                            toselect.append(option)
            else:
                toselect.append(option)
            if (not option in toselect) and remove:
                notselect.append(option)
        for option in toselect:
            option.evaluateJavaScript('this.selected = true;')
        for option in notselect:
            option.evaluateJavaScript('this.selected = false;')

    def wk_select(self, selector, values=None, remove=True):
        """Choose a option in a select using  WebKit API.
        @param selector: css selector to get the select item.
        @param values: string/list of string of values to set pass a single value for a single value.
        """
        element = self.webframe.findFirstElement(selector)
        if not isinstance(values, list) and (values is not None):
            values = [values]
        return self.wk_select_elem(element, values, remove)


    submit = click_link

    def runjs(self, jscode, debug=True):
        """
        Inject Javascript code into the current context of page.

        @param jscode: Javascript code to injected.
        @param debug: Set to False to disable debug output for this injection.

        You can call Jquery even if the original page does not include it
        as Spynner injects the library for every loaded page. You must
        use C{jq(...)} instead of of C{jQuery} or the common {$(...)}
        shortcut.

        @note: You can change the jq alias (see L{jslib}).
        """
        if debug:
            self._debug(DEBUG, "Run Javascript code: %s" % jscode)

        #XXX evaluating JS twice must be wrong but finding the bug is proving tricky...
        #JavaScriptCore/interpreter/Interpreter.cpp and JavaScriptCore/runtime/Completion.cpp
        #JavaScriptCore/runtime/Completion.cpp is catching an exception (sometimes) and
        #returning "TypeError: Type error" - BUT it looks like the JS does complete after
        #the function has already returned
        res = self.webframe.evaluateJavaScript(jscode)
        try:
            js_has_runned_successfully = res.isValid() or res.isNull()
            if not js_has_runned_successfully:
                # try another time
                res = self.webframe.evaluateJavaScript(jscode)
        except:
            # pyside
            if not HAS_PYSIDE:
                raise
        return res

    def set_javascript_confirm_callback(self, callback):
        """
        Set function callback for Javascript confirm pop-ups.

        By default Javascript confirmations are not answered. If the webpage
        you are working pops Javascript confirmations, be sure to set a callback
        for them.

        Calback signature: C{javascript_confirm_callback(url, message)}

            - url: Url where the popup was launched.
            - param message: String message.

        The callback should return a boolean (True meaning 'yes', False meaning 'no')
        """
        self._javascript_confirm_callback = callback

    def set_javascript_prompt_callback(self, callback):
        """
        Set function callback for Javascript prompt.

        By default Javascript prompts are not answered. If the webpage
        you are working pops Javascript prompts, be sure to set a callback
        for them.

        Callback signature: C{javascript_prompt_callback(url, message, defaultvalue)}

            - url: Url where the popup prompt was launched.
            - message: String message.
            - defaultvalue: Default value for prompt answer

        The callback should return a string with the answer or None to cancel the prompt.
        """
        self._javascript_prompt_callback = callback

    @property
    def cookiesjar(self):
        """Compat."""
        return self.manager.cookieJar()

    @property
    def cookiejar(self):
        """Compat."""
        return self.cookiesjar

    def get_cookies(self):
        """Return string containing the current cookies in Mozilla format."""
        return self.cookiesjar.mozillaCookies()

    def set_cookies(self, string_cookies):
        """Set cookies from a string with Mozilla-format cookies."""
        return self.cookiesjar.setMozillaCookies(string_cookies)

    def get_proxy(self):
        """Set NManager.get_proxy (wrapper)"""
        return self.manager.get_proxy()

    def set_proxy(self, string_proxy):
        """Set NManager.set_proxy (wrapper)"""
        return self.manager.set_proxy(string_proxy)

    def download(self, url, outfd=None, timeout=None, proxy_url=None):
        """
        Download a given URL using current cookies.

        @param url: URL or path to download
        @param outfd: Output file-like stream. If None, return data string.
        @param proxy_url: special proxy url (see NManager.set_proxy) to use (default to global networkmanager's proxy
        @param tiemout: int, seconds for timeout
        @return: Bytes downloaded (None if something went wrong)
        @note: If url is a path, the current base URL will be pre-appended.
        """
        def _on_reply(reply):
            url = unicode(toString(reply.url()))
            self._download_reply_status = not bool(reply.error())
        self._download_reply_status = None
        if not urlparse.urlsplit(url).scheme:
            url = urlparse.urljoin(self.url, url)
        request = QNetworkRequest(QUrl(url))
        request = self.apply_ssl(request)
        # Create a new manager to process this download
        manager = NManager.new(self)
        manager.set_proxy(proxy_url)
        manager.sslErrors.connect(self._on_manager_ssl_errors)
        reply = manager.get(request)
        itime = time.time()
        if reply.error():
            raise SpynnerError("Download error: %s" % reply.errorString())
        reply.downloaded_nbytes = 0
        manager.finished.connect(_on_reply)
        outfd_set = bool(outfd)
        if not outfd_set:
            outfd = StringIO()
        self._start_download(reply, outfd)
        while self._download_reply_status is None:
            if timeout:
                if time.time() - itime > timeout:
                    raise SpynnerTimeout("Timeout reached: %d seconds" % timeout)
            self._events_loop()
        if outfd_set:
            return (reply.downloaded_nbytes if not reply.error() else None)
        else:
            return outfd.getvalue()

    def set_html_parser(self, parser):
        """
        Set HTML parser used to generate the HTML L{soup}.

        @param parser: Callback called to generate the soup.

        When a HTML parser is set for a Browser, the property L{soup} returns
        the parsed HTML.
        """
        self._html_parser = parser

    def html_contains(self, regexp):
        """Return True if current HTML contains a given regular expression."""
        return bool(re.search(regexp, self.html))

    def set_http_authentication_callback(self, callback):
        """
        Set HTTP authentication request callback.

        The callback must have this signature:

        C{http_authentication_callback(url, realm)}:

            - C{url}: URL where the requested was made.
            - C{realm}: Realm requiring authentication.

        The callback should return a pair of string containing (user, password)
        or None if you don't want to answer.
        """
        self._http_authentication_callback = callback

    def snapshot(self, box=None, format=QImage.Format_ARGB32):
        """
        Take an image snapshot of the current frame.

        @param box: 4-element tuple containing box to capture (x1, y1, x2, y2).
                    If None, capture the whole page.
        @param format: QImage format (see QImage::Format_*).
        @return: A QImage image.

        Typical usage:

        >>> browser.load(url)
        >>> browser.snapshot().save("webpage.png")
        """
        if box:
            x1, y1, x2, y2 = box
            w, h = (x2 - x1), (y2 - y1)
            image0 = QImage(QSize(x2, y2), format)
            painter = QPainter(image0)
            self.webpage.mainFrame().render(painter)
            painter.end()
            image = image0.copy(x1, y1, w, h)
        else:
            image = QImage(self.webpage.viewportSize(), format)
            painter = QPainter(image)
            self.webpage.mainFrame().render(painter)
            painter.end()
        return image

    def get_url_from_path(self, path):
        """Return the URL for a given path using the current URL as base."""
        return urlparse.urljoin(self.url, path)

    def set_url_filter(self, url_filter):
        """
        Set function callback to filter URL.

        By default all requested elements of a page are loaded. That includes
        stylesheets, images and many other elements that you may not need at all.
        Use this method to define the callback that will be called every time
        a new request is made. The callback must have this signature:

        C{my_url_filter(operation, url)}:

            - C{operation}: string with HTTP operation: C{get}, C{head},
                            C{post} or C{put}.
            - C{url}: requested item URL.

        It should return C{True} (proceed) or C{False} (reject).
        """
        self._url_filter = url_filter


def _first(iterable, pred=bool):
    """Return the first element in iterator that matches the predicate"""
    for item in iterable:
        if pred(item):
            return item

def _debug(obj, linefeed=True, outfd=sys.stderr, outputencoding="utf8"):
    """Print a debug info line to stream channel"""
    if isinstance(obj, unicode):
        obj = obj.encode(outputencoding)
    strobj = str(obj) + ("\n" if linefeed else "")
    outfd.write(strobj)
    outfd.flush()


def toString(s):
    if HAS_PYSIDE:
        if isinstance(s, basestring):
            return s
    if isinstance(s, QString):
        return u"%s" % s
    return s.toString()


def bool2str(value):
    return {True: "TRUE", False: "FALSE"}[value]


def byte2str(value):
    return str(value)


def get_cookie_line(cookie):
    domain_flag = str(cookie.domain()).startswith(".")
    return "\t".join([
        byte2str(cookie.domain()),
        bool2str(domain_flag),
        byte2str(cookie.path()),
        bool2str(cookie.isSecure()),
        byte2str(cookie.expirationDate().toTime_t()),
        byte2str(cookie.name()),
        byte2str(cookie.value()),
    ])


def get_cookie_info(cookie):
    domain_flag = str(cookie.domain()).startswith(".")
    return {
        'domain': byte2str(cookie.domain()),
        'domain_flag': domain_flag,
        'path': byte2str(cookie.path()),
        'isSecure': cookie.isSecure(),
        'timestamp': byte2str(cookie.expirationDate().toTime_t()),
        'name': byte2str(cookie.name()),
        'value': byte2str(cookie.value()),
    }


def merge_cookies(cookies1, cookies2):
    kf = "%(name)s____%(domain)s____%(path)s"
    cookies = dict(
        [(kf % c, d)
         for c, d in
         [(get_cookie_info(cc), cc) for cc in cookies1]
        ])
    for i in cookies2:
        k = kf % get_cookie_info(i)
        if k in cookies:
            j = cookies[k]
            #if j != i:
            #    print "-"*80
            #    print k
            #    print j.toRawForm()
            #    print i.toRawForm()
            #    print "-"*80
        cookies[k] = i
    return cookies.values()


class SpynnerError(Exception):
    """General Spynner error."""

class SpynnerPageError(Exception):
    """Error loading page."""

class SpynnerTimeout(Exception):
    """A timeout (usually on page load) has been reached."""

class SpynnerJavascriptError(Exception):
    """Error on the injected Javascript code."""

class ExtendedNetworkCookieJar(QNetworkCookieJar):
    def mozillaCookies(self):
        """
        Return all cookies in Mozilla text format:

        # domain domain_flag path secure_connection expiration name value

        .firefox.com     TRUE   /  FALSE  946684799   MOZILLA_ID  100103
        """
        header = ["# Netscape HTTP Cookie File", ""]
        lines = [get_cookie_line(cookie)
                 for cookie in self.allCookies()]
        return "\n".join(header + lines)

    def cookies_map(self):
        maps = {}
        for i in self.allCookies():
            maps[i] = get_cookie_line(i)
        return maps

    def setMozillaCookies(self, string_cookies):
        """Set all cookies from Mozilla test format string.
        .firefox.com     TRUE   /  FALSE  946684799   MOZILLA_ID  100103
        """
        def str2bool(value):
            return {"TRUE": True, "FALSE": False}[value]
        def get_cookie(line):
            fields = map(str.strip, line.split("\t"))
            if len(fields) != 7:
                return
            domain, domain_flag, path, is_secure, expiration, name, value = fields
            cookie = QNetworkCookie(name, value)
            cookie.setDomain(domain)
            cookie.setPath(path)
            cookie.setSecure(str2bool(is_secure))
            cookie.setExpirationDate(QDateTime.fromTime_t(int(expiration)))
            return cookie
        cookies = [get_cookie(line) for line in string_cookies.splitlines()
          if line.strip() and not line.strip().startswith("#")]
        self.setAllCookies(filter(bool, cookies))

    def cookiesForUrl(self, qurl):
        cookies = QNetworkCookieJar.cookiesForUrl(self, qurl)
        #for i in cookies:
        #    info = get_cookie_info(i)
        #    print "------------>> %(domain)s " % info
        return cookies


class NManager(QNetworkAccessManager):
    ob = None # Browser instance
    @classmethod
    def new(klass, spynner, cookiejar_klass=None):
        if not cookiejar_klass:
            cookiejar_klass = ExtendedNetworkCookieJar
        manager = klass()
        manager.ob = spynner
        manager.proxy_url = None
        cookiejar = cookiejar_klass()
        manager.setCookieJar(cookiejar)
        manager.cookieJar().setParent(spynner.webpage)
        return manager

    def createRequest(manager, operation, request, data):
        self = manager.ob
        jar = manager.cookieJar()
        cookies = merge_cookies(
            self.cookies,
            jar.allCookies(),
        )
        manager.cookieJar().setAllCookies(cookies)
        url = unicode(toString(request.url()))
        operation_name = self._operation_names.get(
            operation, str(operation)).upper()
        req = self.make_request(request, operation_name)
        self._debug(INFO, "Request: %s %s" % (operation_name, url))
        for h in req.rawHeaderList():
            self._debug(DEBUG, "  %s: %s" % (h, req.rawHeader(h)))
        if self._url_filter:
            if self._url_filter(self._operation_names[operation], url) is False:
                self._debug(INFO, "URL filtered: %s" % url)
                req.setUrl(QUrl("about:blank"))
            else:
                self._debug(DEBUG, "URL not filtered: %s" % url)
        reply = QNetworkAccessManager.createRequest(
            manager, operation, req, data)
        return reply

    def get_proxy(self):
        """Return string containing the current proxy."""
        return self.proxy()

    def set_proxy(self, string_proxy=None):
        """Set proxy:
        url can be in the form:

            - hostname                        (http proxy)
            - hostname:port                   (http proxy)
            - username:password@hostname:port (http proxy)
            - http://username:password@hostname:port
            - socks5://username:password@hostname:port
            - https://username:password@hostname:port
            - httpcaching://username:password@hostname:port
            - ftpcaching://username:password@hostname:port

        """
        if not string_proxy:
            string_proxy = ''
        if string_proxy:
            urlinfo = urlparse.urlparse(string_proxy)
            # default to http proxy if we have a string
            if not urlinfo.scheme:
                string_proxy = "http://%s" % string_proxy
                urlinfo = urlparse.urlparse(string_proxy)
            self.ob._debug(
                WARNING, "Proxy: %s" % string_proxy)
            self.proxy_url = string_proxy
            proxy = QNetworkProxy()
            if urlinfo.scheme == 'socks5':
                proxy.setType(QNetworkProxy.Socks5Proxy)
            elif urlinfo.scheme in ['https', 'http']:
                proxy.setType(QNetworkProxy.HttpProxy)
            elif urlinfo.scheme == 'httpcaching':
                proxy.setType(QNetworkProxy.HttpCachingProxy)
            elif urlinfo.scheme == 'ftpcaching':
                proxy.setType(QNetworkProxy.FtpCachingProxy)
            else:
                proxy.setType(QNetworkProxy.NoProxy)
            if urlinfo.hostname != None:
                proxy.setHostName(urlinfo.hostname)
            if urlinfo.port != None:
                proxy.setPort(urlinfo.port)
            if urlinfo.username != None:
                proxy.setUser(urlinfo.username)
            else:
                proxy.setUser('')
            if urlinfo.password != None:
                proxy.setPassword(urlinfo.password)
            else:
                proxy.setPassword('')
            self.setProxy(proxy)
        elif self is not self.ob.manager:
            if self.ob.manager.proxy_url:
                self.set_proxy(self.ob.manager.proxy_url)
        return self.proxy()


########NEW FILE########
__FILENAME__ = testing

def print_contents(browser, dest='~/.browser.html'):
    """Print the browser contents somewhere for you to see its context
    in doctest pdb, type print_contents(browser) and that's it, open firefox
    with file://~/browser.html."""
    import os
    open(os.path.expanduser(dest), 'w').write(browser.contents)


from plone.testing.layer import Layer as Base

class Layer(Base):

    defaultBases = tuple()

class IntegrationLayer(Layer):
    """."""

class FunctionnalLayer(IntegrationLayer):
    """."""


A_SPYNNER_FIXTURE = Layer()
A_SPYNNER_INTEGRATION_TESTING = IntegrationLayer()
A_SPYNNER_FUNCTIONAL_TESTING = FunctionnalLayer()

########NEW FILE########
__FILENAME__ = base
import unittest2 as unittest

from spynner.testing import (
    A_SPYNNER_FIXTURE as UNIT_TESTING,
    A_SPYNNER_INTEGRATION_TESTING as INTEGRATION_TESTING,
    A_SPYNNER_FUNCTIONAL_TESTING as FUNCTIONAL_TESTING,
)

from pprint import pprint
from copy import deepcopy as dc

class TestCase(unittest.TestCase):
    """We use this base class for all the tests in this package.
    If necessary, we can put common utility or setup code in here.
    """
    layer = UNIT_TESTING

    def setUp(self):
        super(TestCase, self).setUp()


class IntegrationTestCase(TestCase):
    """Integration base TestCase."""
    layer = INTEGRATION_TESTING


class FunctionalTestCase(TestCase):
    """Functionnal base TestCase."""
    layer = FUNCTIONAL_TESTING

# vim:set ft=python:

########NEW FILE########
__FILENAME__ = test_doctests
"""
Launching all doctests in the tests directory using:

    - the base layer in testing.py

"""

from spynner.tests.base import FunctionalTestCase

from spynner.testing import A_SPYNNER_FUNCTIONAL_TESTING as FUNCTIONAL_TESTING

from pprint import pprint
from copy import deepcopy as dc
import unittest2 as unittest
import glob
import os
import logging
import doctest
from plone.testing import layered

optionflags = (doctest.ELLIPSIS | doctest.NORMALIZE_WHITESPACE| doctest.REPORT_ONLY_FIRST_FAILURE)

def test_suite():
    """."""
    logger = logging.getLogger('spynner')
    cwd = os.path.dirname(__file__)
    files = []
    try:
        files = glob.glob(os.path.join(cwd, '*txt'))
        files += glob.glob(os.path.join(cwd, '*rst'))
    except Exception,e:
        logger.warn('No doctests for spynner')
    suite = unittest.TestSuite()
    globs = globals()
    for s in files:
        suite.addTests([
            layered(
                doctest.DocFileSuite(
                    s,
                    globs = globs,
                    module_relative=False,
                    optionflags=optionflags,
                ),
                layer=FUNCTIONAL_TESTING
            ),
        ])
    return suite



########NEW FILE########
__FILENAME__ = test_browser
#!/usr/bin/python

# Copyright (c) Arnau Sanchez <tokland@gmail.com>

# This script is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# This is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this software.  If not, see <http://www.gnu.org/licenses/>

import os
import sys
import signal
import unittest
import threading
from StringIO import StringIO

import spynner
import webserver
from PyQt4.QtGui import QImage
             
TESTDIR = os.path.dirname(__file__)
TESTING_SERVER_PORT = 9876 
           
def get_url(path):
    return "http://localhost:%s" % TESTING_SERVER_PORT + path

def get_file_path(*path):
    return os.path.join(TESTDIR, "fixtures", *path)

def start_threaded_server(port):
    protected = ("/protected.html",)
    server = webserver.get_server('', port, get_file_path(), False, protected)
    thread = threading.Thread(target=server.serve_forever)
    thread.start()
    return server, thread

class SpynnerBrowserTest(unittest.TestCase):    
    def setUp(self):
        self.debugoutput = StringIO()
        self.browser = spynner.Browser(debug_level=spynner.DEBUG)
        self.browser.debug_stream = self.debugoutput
        self.browser.load(get_url("/test1.html"))
        #self.browser.create_webview(); self.browser.show(); self.browser.browse()

    def tearDown(self):
        self.browser.close()

    def get_debug(self):
        self.debugoutput.seek(0)
        return self.debugoutput.read()
        
    # Tests
    
    def test_browser_webview(self):
        self.browser.create_webview()
        html = self.browser.load(get_url("/test1.html"))
        self.browser.webview.show = lambda *args: None
        self.browser.show()
        self.browser.wait(0.01)
        self.browser.hide()
        self.browser.destroy_webview()        

    def test_load_should_return_status_boolean(self):
        self.assertTrue(self.browser.load(get_url("/test1.html")))
        self.assertFalse(self.browser.load("wrong://this-cannot-work"))

    def test_html(self):
        self.assertTrue("Test1 HTML" in self.browser.html)

    def test_get_url(self):
        self.assertEqual(get_url("/test1.html"), self.browser.url)

    def test_wait_load(self):
        self.browser.runjs("window.location = '/test2.html'")
        self.browser.wait_load(1000)

    def test_wait_load_raises_exception_on_timeout(self):
        self.assertRaises(spynner.SpynnerTimeout, 
            self.browser.wait_load, 0.1)

    def test_wait_request(self):
        self.browser.click("#link", wait_requests=1)
        self.assertEqual(get_url("/test3.html"), self.browser.url)
        
    def test_click(self):
        self.browser.click("#link")
        self.browser.wait_load(timeout=1.0)
        self.assertEqual(get_url('/test3.html'), self.browser.url)            

    def test_check(self):
        self.browser.check("#check")
        jscode = "jQuery('#check').attr('checked')"
        self.assertTrue(self.browser.runjs(jscode).toPyObject())

    def test_uncheck(self):
        self.browser.uncheck("#check")
        jscode = "jQuery('#check').attr('checked')"
        self.assertFalse(self.browser.runjs(jscode).toPyObject())

    def test_choose(self):
        self.browser.choose("#radio2")
        jscode = "jQuery('#radio2').attr('checked')"
        self.assertTrue(self.browser.runjs(jscode).toPyObject())

    def test_select(self):
        self.browser.select("#select option[value=2]")
        jscode = "jQuery('#option2').attr('selected')"
        self.assertTrue(self.browser.runjs(jscode).toPyObject())

    def test_fill(self):
        name = "myname'\"withquotes\"'"
        self.browser.fill("input[name=user]", name)
        self.browser.click("#submit")
        self.browser.wait_load(timeout=1.0)
        self.assertEqual(get_url('/test2.html?user=%s' % name), 
            self.browser.url)            
                
    def test_runjs(self):
        jscode = "document.getElementById('link').innerHTML = 'hello there!'" 
        self.browser.runjs(jscode)
        self.assertTrue("hello there!" in self.browser.html)

    def test_get_cookies(self):
        cookies = self.browser.get_cookies()
        self.assertTrue("# Netscape HTTP Cookie File" in cookies)
        self.assertTrue("mycookie" in cookies)
        self.assertTrue("12345" in cookies)

    def test_set_cookies(self):
        cookies = """
        .firefox.com\tTRUE\t/\tFALSE\t946684799\tMOZILLA_ID\t100103
        """
        self.browser.set_cookies(cookies)
        cookies = self.browser.get_cookies()
        self.assertTrue("mycookie" not in cookies)
        self.assertTrue("MOZILLA_ID" in cookies)

    def test_javascript_console_message(self):
        self.browser.runjs("console.log('hello there!')")
        output = self.get_debug()
        self.assertTrue("Javascript console" in output)
        self.assertTrue("hello there!" in output)        

    def test_javascript_alert(self):
        self.browser.runjs("alert('hello there!')")
        output = self.get_debug()
        self.assertTrue("Javascript alert" in output)
        self.assertTrue("hello there!" in output)        

    def test_download(self):
        outfd = StringIO()
        downloaded_bytes = self.browser.download(get_url('/test3.html'), outfd)
        expected_data = open(get_file_path('test3.html')).read()
        self.assertEqual(len(expected_data), downloaded_bytes)
        self.assertEqual(expected_data, outfd.getvalue())

    def test_download_error(self):
        outfd = StringIO()
        downloaded_bytes = self.browser.download(get_url('/nonexisting.out'), outfd)
        self.assertEqual(None, downloaded_bytes)

    def test_get_url_from_path(self):
        self.assertEqual(get_url("/test2.html"), 
            self.browser.get_url_from_path('/test2.html'))
        
    def test_set_url_filter(self):
        def url_filter(operation, url):
            if url == get_url("/test.css"):
                return False
        self.browser.set_url_filter(url_filter)
        self.browser.load(get_url("/test2.html"))
        # do some test here!
        
    def test_javascript_confirm(self):
        def confirm_no(url, message):
            return False
        self.browser.set_javascript_confirm_callback(confirm_no)                
        self.browser.click("#link_confirmed")
        self.assertEqual(get_url("/test1.html"), self.browser.url)
        
        def confirm_yes(url, message):
            return True
        self.browser.set_javascript_confirm_callback(confirm_yes)                
        self.browser.click("#link_confirmed")
        self.browser.wait_load(timeout=1.0)
        self.assertEqual(get_url("/test3.html"), self.browser.url)

    def test_javascript_prompt(self):
        def answer(url, message, defaultvalue):
            return "My answer"
        self.browser.set_javascript_prompt_callback(answer)                
        self.browser.click("#link_prompt")
        self.assertTrue("User answer: My answer" in self.get_debug())            

        def cancel_answer(url, message, defaultvalue):
            return
        self.browser.set_javascript_prompt_callback(cancel_answer)                
        self.debugoutput.seek(0)
        self.debugoutput.truncate()
        self.browser.click("#link_prompt")
        self.assertTrue("User answer" not in self.get_debug())            
        

    def test_html_parser(self):
        def my_parser(html):
            return html.splitlines()
        self.browser.set_html_parser(my_parser)
        self.assertEqual(self.browser.html.splitlines(), self.browser.soup)
        
    def test_html_contains(self):
        self.assertTrue(self.browser.html_contains("function SetCookie"))
        self.assertTrue(self.browser.html_contains("func.ion [Ss]etCookie"))
        self.assertFalse(self.browser.html_contains("strange string"))                    

    def test_http_authentication_error(self):
        def not_auth_callback(url, realm):
            return False
        self.browser.set_http_authentication_callback(not_auth_callback)
        self.browser.click("#link_protected")
        self.browser.wait_load(timeout=1.0)
        self.assertFalse("Protected" in self.browser.html)

    def test_http_authentication_successful(self):
        def auth_callback(url, realm):
            return ("myuser", "mypassword")
        self.browser.set_http_authentication_callback(auth_callback)
        self.browser.click("#link_protected")
        self.browser.wait_load(timeout=1.0)
        self.assertTrue("Protected" in self.browser.html)

    def test_user_agent(self):
        self.browser.user_agent = "My user agent"
        self.browser.load(get_url("/test2.html"))
        self.assertTrue("User-Agent: My user agent" in self.browser.html)

    def test_snapshot(self):
        image = self.browser.snapshot()
        self.assertTrue(type(image) == QImage)
        size = self.browser.webpage.viewportSize()
        self.assertEqual((image.width(), image.height()), 
            (size.width(), size.height()))

    def test_snapshot_with_box(self):
        image = self.browser.snapshot((100, 100, 200, 250))
        self.assertTrue(type(image) == QImage)
        self.assertEqual((image.width(), image.height()), (100, 150))
        
        
def suite():                                            
    return unittest.TestLoader().loadTestsFromTestCase(SpynnerBrowserTest)

if __name__ == '__main__':
    signal.signal(signal.SIGINT, signal.SIG_DFL)
    thread = start_threaded_server(port=TESTING_SERVER_PORT)
    unittest.main()

########NEW FILE########
__FILENAME__ = webserver
#!/usr/bin/python

# Copyright (c) Arnau Sanchez <tokland@gmail.com>

# This script is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# This is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License

import os
import re
import cgi
import base64

from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer

class Handler(BaseHTTPRequestHandler):

    def __init__(self, *args, **kwargs):
        self.basedir = kwargs.pop("basedir")    
        self.verbose = kwargs.pop("verbose")
        self.protected = kwargs.pop("protected")
        BaseHTTPRequestHandler.__init__(self, *args, **kwargs)
        
    def _debug_headers(self, headers):
        if self.verbose:
            for header in headers.headers:
                print header,
            
    def do_GET(self):
        request_headers = self.headers.headers[:]
        self._debug_headers(request_headers)        
        path = re.sub("\?.*$", "", self.path.strip("/"))
        filepath = os.path.join(self.basedir, path)
        if not os.path.isfile(filepath):
            self.send_error(404, 'File Not Found: %s' % path)
            return
        if self.protected and self.path in self.protected:
            correct = base64.b64encode('myuser:mypassword')
            authorization = self.headers.getheader('authorization')
            if not authorization or not authorization.split()[1] == correct:
                self.send_response(401)
                self.send_header('WWW-Authenticate', 'Basic realm="webserver"')
                self.end_headers()
                return
        self.send_response(200)
        extension = os.path.splitext(filepath)
        if extension in ("html", "htm"):
            self.send_header('Content-type', 'text/html')
        self.end_headers()
        sheaders = "<br />".join(request_headers)
        html = open(filepath).read().replace("$headers", sheaders)         
        self.wfile.write(html)
     
    def do_POST(self):
        ctype, pdict = cgi.parse_header(self.headers.getheader('content-type'))
        self.send_response(200)        
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        self.wfile.write("<html></html>");

    def log_message(self, *args):
        if self.verbose:
            BaseHTTPRequestHandler.log_message(self, *args)
        
def get_handler_factory(basedir, verbose, protected):
    def factory(*args):
        return Handler(*args, basedir=basedir, verbose=verbose, protected=protected)
    return factory
        
def get_server(host, port, basedir, verbose=False, protected=None):
    return HTTPServer((host, port), get_handler_factory(basedir, verbose, protected))

def main():
    basedir = os.path.join(os.path.dirname(__file__), "fixtures")
    server = get_server('', 8081, basedir, True, ("/protected.html",))
    print 'started HTTP server'
    server.serve_forever()

if __name__ == '__main__':
    main()

########NEW FILE########
