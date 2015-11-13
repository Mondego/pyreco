__FILENAME__ = droiddemo
#!/usr/bin/python -u
#
# droiddemo.py, Copyright 2010-2013, The Beanstalks Project ehf.
#                                    http://beanstalks-project.net/
#
# This is a proof-of-concept PageKite enabled HTTP server for Android.
# It has been developed and tested in the SL4A Python environment.
#
DOMAIN='phone.bre.pagekite.me'
SECRET='ba4e5430'
SOURCE='/sdcard/sl4a/scripts/droiddemo.py'
#
#############################################################################
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
#############################################################################
#
import android
import pagekite
import os
from urllib import unquote
try:
  from urlparse import parse_qs, urlparse
except Exception, e:
  from cgi import parse_qs
  from urlparse import urlparse



class UiRequestHandler(pagekite.UiRequestHandler):

  CAMERA_PATH = '/sdcard/dcim/.thumbnails'
  HOME = ('<html><head>\n'
          '<script type=text/javascript>'
           'lastImage = "";'
           'function getImage() {'
            'xhr = new XMLHttpRequest();'
            'xhr.open("GET", "/latest-image.txt", true);'
            'xhr.onreadystatechange = function() {'
             'if (xhr.readyState == 4) {'
              'if (xhr.responseText && xhr.responseText != lastImage) {'
               'document.getElementById("i").src = lastImage = xhr.responseText;'
              '}'
              'setTimeout("getImage()", 2000);'
             '}'
            '};'
           'xhr.send(null);'
           '}'
          '</script>\n'
          '</head><body onLoad="getImage();" style="text-align: center;">\n'
          '<h1>Android photos!</h1>\n'
          '<img id=i height=80% src="http://www.android.com/images/opensourceproject.gif">\n'
          '<br><a href="/droiddemo.py">source code</a>'
          '| <a href="/status.html">kite status</a>\n'
          '</body></head>')

  def listFiles(self):
    mtimes = {}
    for item in os.listdir(self.CAMERA_PATH):
      iname = '%s/%s' % (self.CAMERA_PATH, item)
      if iname.endswith('.jpg'):
        mtimes[iname] = os.path.getmtime(iname)

    files = mtimes.keys()
    files.sort(lambda x,y: cmp(mtimes[x], mtimes[y]))
    return files

  def do_GET(self):
    (scheme, netloc, path, params, query, frag) = urlparse(self.path)

    p = unquote(path)
    if p.endswith('.jpg') and p.startswith(self.CAMERA_PATH) and ('..' not in p):
      try:
        jpgfile = open(p)
        self.send_response(200)
        self.send_header('Content-Type', 'image/jpeg')
        self.send_header('Content-Length', '%s' % os.path.getsize(p))
        self.send_header('Cache-Control', 'max-age: 36000')
        self.send_header('Expires', 'Sat, 1 Jan 2011 12:00:00 GMT')
        self.send_header('Last-Modified', 'Wed, 1 Sep 2011 12:00:00 GMT')
        self.end_headers()
        data = jpgfile.read() 
        while data:
          try:
            sent = self.wfile.write(data[0:15000])
            data = data[15000:]
          except Exception:
            pass
        return
 
      except Exception, e:
        print '%s' % e
        pass 

    if path == '/latest-image.txt':
      flist = self.listFiles()
      self.begin_headers(200, 'text/plain')
      self.end_headers()
      self.wfile.write(flist[-1])
      return
    elif path == '/droiddemo.py':
      try:
        pyfile = open(SOURCE)
        self.begin_headers(200, 'text/plain')
        self.end_headers()
        self.wfile.write(pyfile.read().replace(SECRET, 'mysecret'))
      except IOError, e:
        self.begin_headers(404, 'text/plain')
        self.end_headers()
        self.wfile.write('Could not read %s: %s' % (SOURCE, e))
      return
    elif path == '/':
      self.begin_headers(200, 'text/html')
      self.end_headers()
      self.wfile.write(self.HOME)
      return

    return pagekite.UiRequestHandler.do_GET(self)


class DroidKite(pagekite.PageKite):
  def __init__(self, droid):
    pagekite.PageKite.__init__(self)
    self.droid = droid
    self.ui_request_handler = UiRequestHandler


def Start(host, secret):
  ds = DroidKite(android.Android())
  ds.Configure(['--defaults',
                '--httpd=localhost:9999',
                '--backend=http:%s:localhost:9999:%s' % (host, secret)])
  ds.Start()


Start(DOMAIN, SECRET)

########NEW FILE########
__FILENAME__ = android
"""
This is the main function for the Android version of PageKite.
"""
#############################################################################
LICENSE = """\
This file is part of pagekite.py.
Copyright 2010-2013, the Beanstalks Project ehf. and Bjarni Runar Einarsson

This program is free software: you can redistribute it and/or modify it under
the terms of the  GNU  Affero General Public License as published by the Free
Software Foundation, either version 3 of the License, or (at your option) any
later version.

This program is distributed in the hope that it will be useful,  but  WITHOUT
ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
FOR A PARTICULAR PURPOSE.  See the GNU Affero General Public License for more
details.

You should have received a copy of the GNU Affero General Public License
along with this program.  If not, see: <http://www.gnu.org/licenses/>
"""
#############################################################################
import sys
import pagekite.pk as pk
import pagekite.httpd as httpd


def Configure(pkobj):
  pkobj.rcfile = "/sdcard/pagekite.cfg"
  pkobj.enable_sslzlib = True
  pk.Configure(pkobj)

if __name__ == "__main__":
  if sys.stdout.isatty():
    import pagekite.ui.basic
    uiclass = pagekite.ui.basic.BasicUi
  else:
    uiclass = pk.NullUi

  pk.Main(pk.PageKite, Configure,
          uiclass=uiclass,
          http_handler=httpd.UiRequestHandler,
          http_server=httpd.UiHttpServer)

##############################################################################
CERTS="""\
StartCom Ltd.
=============
-----BEGIN CERTIFICATE-----
MIIFFjCCBH+gAwIBAgIBADANBgkqhkiG9w0BAQQFADCBsDELMAkGA1UEBhMCSUwxDzANBgNVBAgT
BklzcmFlbDEOMAwGA1UEBxMFRWlsYXQxFjAUBgNVBAoTDVN0YXJ0Q29tIEx0ZC4xGjAYBgNVBAsT
EUNBIEF1dGhvcml0eSBEZXAuMSkwJwYDVQQDEyBGcmVlIFNTTCBDZXJ0aWZpY2F0aW9uIEF1dGhv
cml0eTEhMB8GCSqGSIb3DQEJARYSYWRtaW5Ac3RhcnRjb20ub3JnMB4XDTA1MDMxNzE3Mzc0OFoX
DTM1MDMxMDE3Mzc0OFowgbAxCzAJBgNVBAYTAklMMQ8wDQYDVQQIEwZJc3JhZWwxDjAMBgNVBAcT
BUVpbGF0MRYwFAYDVQQKEw1TdGFydENvbSBMdGQuMRowGAYDVQQLExFDQSBBdXRob3JpdHkgRGVw
LjEpMCcGA1UEAxMgRnJlZSBTU0wgQ2VydGlmaWNhdGlvbiBBdXRob3JpdHkxITAfBgkqhkiG9w0B
CQEWEmFkbWluQHN0YXJ0Y29tLm9yZzCBnzANBgkqhkiG9w0BAQEFAAOBjQAwgYkCgYEA7YRgACOe
yEpRKSfeOqE5tWmrCbIvNP1h3D3TsM+x18LEwrHkllbEvqoUDufMOlDIOmKdw6OsWXuO7lUaHEe+
o5c5s7XvIywI6Nivcy+5yYPo7QAPyHWlLzRMGOh2iCNJitu27Wjaw7ViKUylS7eYtAkUEKD4/mJ2
IhULpNYILzUCAwEAAaOCAjwwggI4MA8GA1UdEwEB/wQFMAMBAf8wCwYDVR0PBAQDAgHmMB0GA1Ud
DgQWBBQcicOWzL3+MtUNjIExtpidjShkjTCB3QYDVR0jBIHVMIHSgBQcicOWzL3+MtUNjIExtpid
jShkjaGBtqSBszCBsDELMAkGA1UEBhMCSUwxDzANBgNVBAgTBklzcmFlbDEOMAwGA1UEBxMFRWls
YXQxFjAUBgNVBAoTDVN0YXJ0Q29tIEx0ZC4xGjAYBgNVBAsTEUNBIEF1dGhvcml0eSBEZXAuMSkw
JwYDVQQDEyBGcmVlIFNTTCBDZXJ0aWZpY2F0aW9uIEF1dGhvcml0eTEhMB8GCSqGSIb3DQEJARYS
YWRtaW5Ac3RhcnRjb20ub3JnggEAMB0GA1UdEQQWMBSBEmFkbWluQHN0YXJ0Y29tLm9yZzAdBgNV
HRIEFjAUgRJhZG1pbkBzdGFydGNvbS5vcmcwEQYJYIZIAYb4QgEBBAQDAgAHMC8GCWCGSAGG+EIB
DQQiFiBGcmVlIFNTTCBDZXJ0aWZpY2F0aW9uIEF1dGhvcml0eTAyBglghkgBhvhCAQQEJRYjaHR0
cDovL2NlcnQuc3RhcnRjb20ub3JnL2NhLWNybC5jcmwwKAYJYIZIAYb4QgECBBsWGWh0dHA6Ly9j
ZXJ0LnN0YXJ0Y29tLm9yZy8wOQYJYIZIAYb4QgEIBCwWKmh0dHA6Ly9jZXJ0LnN0YXJ0Y29tLm9y
Zy9pbmRleC5waHA/YXBwPTExMTANBgkqhkiG9w0BAQQFAAOBgQBscSXhnjSRIe/bbL0BCFaPiNhB
OlP1ct8nV0t2hPdopP7rPwl+KLhX6h/BquL/lp9JmeaylXOWxkjHXo0Hclb4g4+fd68p00UOpO6w
NnQt8M2YI3s3S9r+UZjEHjQ8iP2ZO1CnwYszx8JSFhKVU2Ui77qLzmLbcCOxgN8aIDjnfg==
-----END CERTIFICATE-----

StartCom Certification Authority
================================
-----BEGIN CERTIFICATE-----
MIIHyTCCBbGgAwIBAgIBATANBgkqhkiG9w0BAQUFADB9MQswCQYDVQQGEwJJTDEWMBQGA1UEChMN
U3RhcnRDb20gTHRkLjErMCkGA1UECxMiU2VjdXJlIERpZ2l0YWwgQ2VydGlmaWNhdGUgU2lnbmlu
ZzEpMCcGA1UEAxMgU3RhcnRDb20gQ2VydGlmaWNhdGlvbiBBdXRob3JpdHkwHhcNMDYwOTE3MTk0
NjM2WhcNMzYwOTE3MTk0NjM2WjB9MQswCQYDVQQGEwJJTDEWMBQGA1UEChMNU3RhcnRDb20gTHRk
LjErMCkGA1UECxMiU2VjdXJlIERpZ2l0YWwgQ2VydGlmaWNhdGUgU2lnbmluZzEpMCcGA1UEAxMg
U3RhcnRDb20gQ2VydGlmaWNhdGlvbiBBdXRob3JpdHkwggIiMA0GCSqGSIb3DQEBAQUAA4ICDwAw
ggIKAoICAQDBiNsJvGxGfHiflXu1M5DycmLWwTYgIiRezul38kMKogZkpMyONvg45iPwbm2xPN1y
o4UcodM9tDMr0y+v/uqwQVlntsQGfQqedIXWeUyAN3rfOQVSWff0G0ZDpNKFhdLDcfN1YjS6LIp/
Ho/u7TTQEceWzVI9ujPW3U3eCztKS5/CJi/6tRYccjV3yjxd5srhJosaNnZcAdt0FCX+7bWgiA/d
eMotHweXMAEtcnn6RtYTKqi5pquDSR3l8u/d5AGOGAqPY1MWhWKpDhk6zLVmpsJrdAfkK+F2PrRt
2PZE4XNiHzvEvqBTViVsUQn3qqvKv3b9bZvzndu/PWa8DFaqr5hIlTpL36dYUNk4dalb6kMMAv+Z
6+hsTXBbKWWc3apdzK8BMewM69KN6Oqce+Zu9ydmDBpI125C4z/eIT574Q1w+2OqqGwaVLRcJXrJ
osmLFqa7LH4XXgVNWG4SHQHuEhANxjJ/GP/89PrNbpHoNkm+Gkhpi8KWTRoSsmkXwQqQ1vp5Iki/
untp+HDH+no32NgN0nZPV/+Qt+OR0t3vwmC3Zzrd/qqc8NSLf3Iizsafl7b4r4qgEKjZ+xjGtrVc
UjyJthkqcwEKDwOzEmDyei+B26Nu/yYwl/WL3YlXtq09s68rxbd2AvCl1iuahhQqcvbjM4xdCUsT
37uMdBNSSwIDAQABo4ICUjCCAk4wDAYDVR0TBAUwAwEB/zALBgNVHQ8EBAMCAa4wHQYDVR0OBBYE
FE4L7xqkQFulF2mHMMo0aEPQQa7yMGQGA1UdHwRdMFswLKAqoCiGJmh0dHA6Ly9jZXJ0LnN0YXJ0
Y29tLm9yZy9zZnNjYS1jcmwuY3JsMCugKaAnhiVodHRwOi8vY3JsLnN0YXJ0Y29tLm9yZy9zZnNj
YS1jcmwuY3JsMIIBXQYDVR0gBIIBVDCCAVAwggFMBgsrBgEEAYG1NwEBATCCATswLwYIKwYBBQUH
AgEWI2h0dHA6Ly9jZXJ0LnN0YXJ0Y29tLm9yZy9wb2xpY3kucGRmMDUGCCsGAQUFBwIBFilodHRw
Oi8vY2VydC5zdGFydGNvbS5vcmcvaW50ZXJtZWRpYXRlLnBkZjCB0AYIKwYBBQUHAgIwgcMwJxYg
U3RhcnQgQ29tbWVyY2lhbCAoU3RhcnRDb20pIEx0ZC4wAwIBARqBl0xpbWl0ZWQgTGlhYmlsaXR5
LCByZWFkIHRoZSBzZWN0aW9uICpMZWdhbCBMaW1pdGF0aW9ucyogb2YgdGhlIFN0YXJ0Q29tIENl
cnRpZmljYXRpb24gQXV0aG9yaXR5IFBvbGljeSBhdmFpbGFibGUgYXQgaHR0cDovL2NlcnQuc3Rh
cnRjb20ub3JnL3BvbGljeS5wZGYwEQYJYIZIAYb4QgEBBAQDAgAHMDgGCWCGSAGG+EIBDQQrFilT
dGFydENvbSBGcmVlIFNTTCBDZXJ0aWZpY2F0aW9uIEF1dGhvcml0eTANBgkqhkiG9w0BAQUFAAOC
AgEAFmyZ9GYMNPXQhV59CuzaEE44HF7fpiUFS5Eyweg78T3dRAlbB0mKKctmArexmvclmAk8jhvh
3TaHK0u7aNM5Zj2gJsfyOZEdUauCe37Vzlrk4gNXcGmXCPleWKYK34wGmkUWFjgKXlf2Ysd6AgXm
vB618p70qSmD+LIU424oh0TDkBreOKk8rENNZEXO3SipXPJzewT4F+irsfMuXGRuczE6Eri8sxHk
fY+BUZo7jYn0TZNmezwD7dOaHZrzZVD1oNB1ny+v8OqCQ5j4aZyJecRDjkZy42Q2Eq/3JR44iZB3
fsNrarnDy0RLrHiQi+fHLB5LEUTINFInzQpdn4XBidUaePKVEFMy3YCEZnXZtWgo+2EuvoSoOMCZ
EoalHmdkrQYuL6lwhceWD3yJZfWOQ1QOq92lgDmUYMA0yZZwLKMS9R9Ie70cfmu3nZD0Ijuu+Pwq
yvqCUqDvr0tVk+vBtfAii6w0TiYiBKGHLHVKt+V9E9e4DGTANtLJL4YSjCMJwRuCO3NJo2pXh5Tl
1njFmUNj403gdy3hZZlyaQQaRwnmDwFWJPsfvw55qVguucQJAX6Vum0ABj6y6koQOdjQK/W/7HW/
lwLFCRsI3FU34oH7N4RDYiDK51ZLZer+bMEkkyShNOsF/5oirpt9P/FlUQqmMGqz9IgcgA38coro
g14=
-----END CERTIFICATE-----
"""

########NEW FILE########
__FILENAME__ = common
"""
Constants and global program state.
"""
##############################################################################
LICENSE = """\
This file is part of pagekite.py.
Copyright 2010-2013, the Beanstalks Project ehf. and Bjarni Runar Einarsson

This program is free software: you can redistribute it and/or modify it under
the terms of the  GNU  Affero General Public License as published by the Free
Software Foundation, either version 3 of the License, or (at your option) any
later version.

This program is distributed in the hope that it will be useful,  but  WITHOUT
ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
FOR A PARTICULAR PURPOSE.  See the GNU Affero General Public License for more
details.

You should have received a copy of the GNU Affero General Public License
along with this program.  If not, see: <http://www.gnu.org/licenses/>
"""
##############################################################################
import random
import time

PROTOVER = '0.8'
APPVER = '0.5.6d+github'
AUTHOR = 'Bjarni Runar Einarsson, http://bre.klaki.net/'
WWWHOME = 'http://pagekite.net/'
LICENSE_URL = 'http://www.gnu.org/licenses/agpl.html'

MAGIC_PREFIX = '/~:PageKite:~/'
MAGIC_PATH = '%sv%s' % (MAGIC_PREFIX, PROTOVER)
MAGIC_PATHS = (MAGIC_PATH, '/Beanstalk~Magic~Beans/0.2')
MAGIC_UUID = '%x-%x-%s' % (random.randint(0, 0xfffffff), time.time(), APPVER)

SERVICE_PROVIDER = 'PageKite.net'
SERVICE_DOMAINS = ('pagekite.me', '302.is', 'testing.is', 'kazz.am')
SERVICE_DOMAINS_SIGNUP = ('pagekite.me',)
SERVICE_XMLRPC = 'http://pagekite.net/xmlrpc/'
SERVICE_TOS_URL = 'https://pagekite.net/humans.txt'
SERVICE_CERTS = ['b5p.us', 'frontends.b5p.us', 'pagekite.net', 'pagekite.me',
                 'pagekite.com', 'pagekite.org', 'testing.is', '302.is']

DEFAULT_CHARSET = 'utf-8'
DEFAULT_BUFFER_MAX = 1024

AUTH_ERRORS           = '255.255.255.'
AUTH_ERR_USER_UNKNOWN = '.0'
AUTH_ERR_INVALID      = '.1'
AUTH_QUOTA_MAX        = '255.255.254.255'

VIRTUAL_PN = 'virtual'
CATCHALL_HN = 'unknown'
LOOPBACK_HN = 'loopback'
LOOPBACK_FE = LOOPBACK_HN + ':1'
LOOPBACK_BE = LOOPBACK_HN + ':2'
LOOPBACK = {'FE': LOOPBACK_FE, 'BE': LOOPBACK_BE}

# Re-evaluate our choice of frontends every 45-60 minutes.
FE_PING_INTERVAL     = (45 * 60) + random.randint(0, 900)

PING_INTERVAL        = 90
PING_INTERVAL_MOBILE = 1800
PING_INTERVAL_MAX    = 1800
PING_GRACE_DEFAULT   = 40
PING_GRACE_MIN       = 5

WEB_POLICY_DEFAULT = 'default'
WEB_POLICY_PUBLIC = 'public'
WEB_POLICY_PRIVATE = 'private'
WEB_POLICY_OTP = 'otp'
WEB_POLICIES = (WEB_POLICY_DEFAULT, WEB_POLICY_PUBLIC,
                WEB_POLICY_PRIVATE, WEB_POLICY_OTP)

WEB_INDEX_ALL = 'all'
WEB_INDEX_ON = 'on'
WEB_INDEX_OFF = 'off'
WEB_INDEXTYPES = (WEB_INDEX_ALL, WEB_INDEX_ON, WEB_INDEX_OFF)

BE_PROTO = 0
BE_PORT = 1
BE_DOMAIN = 2
BE_BHOST = 3
BE_BPORT = 4
BE_SECRET = 5
BE_STATUS = 6

BE_STATUS_REMOTE_SSL   = 0x0010000
BE_STATUS_OK           = 0x0001000
BE_STATUS_ERR_DNS      = 0x0000100
BE_STATUS_ERR_BE       = 0x0000010
BE_STATUS_ERR_TUNNEL   = 0x0000001
BE_STATUS_ERR_ANY      = 0x0000fff
BE_STATUS_UNKNOWN      = 0
BE_STATUS_DISABLED     = 0x8000000
BE_STATUS_DISABLE_ONCE = 0x4000000
BE_INACTIVE = (BE_STATUS_DISABLED, BE_STATUS_DISABLE_ONCE)

BE_NONE = ['', '', None, None, None, '', BE_STATUS_UNKNOWN]

DYNDNS = {
  'pagekite.net': ('http://up.pagekite.net/'
                   '?hostname=%(domain)s&myip=%(ips)s&sign=%(sign)s'),
  'beanstalks.net': ('http://up.b5p.us/'
                     '?hostname=%(domain)s&myip=%(ips)s&sign=%(sign)s'),
  'dyndns.org': ('https://%(user)s:%(pass)s@members.dyndns.org'
                 '/nic/update?wildcard=NOCHG&backmx=NOCHG'
                 '&hostname=%(domain)s&myip=%(ip)s'),
  'no-ip.com': ('https://%(user)s:%(pass)s@dynupdate.no-ip.com'
                '/nic/update?hostname=%(domain)s&myip=%(ip)s'),
}

# Create our service-domain matching regexp
import re
SERVICE_DOMAIN_RE = re.compile('\.(' + '|'.join(SERVICE_DOMAINS) + ')$')
SERVICE_SUBDOMAIN_RE = re.compile(r'^([A-Za-z0-9_-]+\.)*[A-Za-z0-9_-]+$')


class ConfigError(Exception):
  """This error gets thrown on configuration errors."""

class ConnectError(Exception):
  """This error gets thrown on connection errors."""

class BugFoundError(Exception):
  """Throw this anywhere a bug is detected and we want a crash."""


##[ Ugly fugly globals ]#######################################################

# The global Yamon is used for measuring internal state for monitoring
gYamon = None

# Status of our buffers...
buffered_bytes = [0]


########NEW FILE########
__FILENAME__ = compat
"""
Compatibility hacks to work around differences between Python versions.
"""
##############################################################################
LICENSE = """\
This file is part of pagekite.py.
Copyright 2010-2013, the Beanstalks Project ehf. and Bjarni Runar Einarsson

This program is free software: you can redistribute it and/or modify it under
the terms of the  GNU  Affero General Public License as published by the Free
Software Foundation, either version 3 of the License, or (at your option) any
later version.

This program is distributed in the hope that it will be useful,  but  WITHOUT
ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
FOR A PARTICULAR PURPOSE.  See the GNU Affero General Public License for more
details.

You should have received a copy of the GNU Affero General Public License
along with this program.  If not, see: <http://www.gnu.org/licenses/>
"""
##############################################################################
import common
from common import *


# System logging on Unix
try:
  import syslog
except ImportError:
  class mockSyslog:
    def openlog(*args): raise ConfigError('No Syslog on this machine')
    def syslog(*args): raise ConfigError('No Syslog on this machine')
    LOG_DAEMON = 0
    LOG_DEBUG = 0
    LOG_ERROR = 0
    LOG_PID = 0
  syslog = mockSyslog()


# Backwards compatibility for old Pythons.
import socket
rawsocket = socket.socket
if not 'SHUT_RD' in dir(socket):
  socket.SHUT_RD = 0
  socket.SHUT_WR = 1
  socket.SHUT_RDWR = 2

try:
  import datetime
  ts_to_date = datetime.datetime.fromtimestamp
  def ts_to_iso(ts=None):
    return datetime.datetime.fromtimestamp(ts).isoformat()
except ImportError:
  ts_to_date = str
  ts_to_iso = str

try:
  sorted([1, 2, 3])
except:
  def sorted(l):
    tmp = l[:]
    tmp.sort()
    return tmp

try:
  sum([1, 2, 3])
except:
  def sum(l):
    s = 0
    for v in l:
      s += v
    return s

try:
  from urlparse import parse_qs, urlparse
except ImportError, e:
  from cgi import parse_qs
  from urlparse import urlparse
try:
  import hashlib
  def sha1hex(data):
    hl = hashlib.sha1()
    hl.update(data)
    return hl.hexdigest().lower()
except ImportError:
  import sha
  def sha1hex(data):
    return sha.new(data).hexdigest().lower()

common.MAGIC_UUID = sha1hex(common.MAGIC_UUID)

try:
  from traceback import format_exc
except ImportError:
  import traceback
  import StringIO
  def format_exc():
    sio = StringIO.StringIO()
    traceback.print_exc(file=sio)
    return sio.getvalue()

# Old Pythons lack rsplit
def rsplit(ch, data):
  parts = data.split(ch)
  if (len(parts) > 2):
    tail = parts.pop(-1)
    return (ch.join(parts), tail)
  else:
    return parts

# SSL/TLS strategy: prefer pyOpenSSL, as it comes with built-in Context
# objects. If that fails, look for Python 2.6+ native ssl support and
# create a compatibility wrapper. If both fail, bomb with a ConfigError
# when the user tries to enable anything SSL-related.
#
import sockschain
socks = sockschain
if socks.HAVE_PYOPENSSL:
  SSL = socks.SSL
  SEND_ALWAYS_BUFFERS = False
  SEND_MAX_BYTES = 16 * 1024
  TUNNEL_SOCKET_BLOCKS = False

elif socks.HAVE_SSL:
  SSL = socks.SSL
  SEND_ALWAYS_BUFFERS = True
  SEND_MAX_BYTES = 4 * 1024
  TUNNEL_SOCKET_BLOCKS = True # Workaround for http://bugs.python.org/issue8240

else:
  SEND_ALWAYS_BUFFERS = False
  SEND_MAX_BYTES = 16 * 1024
  TUNNEL_SOCKET_BLOCKS = False
  class SSL(object):
    SSLv23_METHOD = 0
    TLSv1_METHOD = 0
    class Error(Exception): pass
    class SysCallError(Exception): pass
    class WantReadError(Exception): pass
    class WantWriteError(Exception): pass
    class ZeroReturnError(Exception): pass
    class Context(object):
      def __init__(self, method):
        raise ConfigError('Neither pyOpenSSL nor python 2.6+ '
                          'ssl modules found!')


########NEW FILE########
__FILENAME__ = dropper
"""
This is a "dropper template".  A dropper is a single-purpose PageKite
back-end connector which embeds its own configuration.
"""
##############################################################################
LICENSE = """\
This file is part of pagekite.py.
Copyright 2010-2013, the Beanstalks Project ehf. and Bjarni Runar Einarsson

This program is free software: you can redistribute it and/or modify it under
the terms of the  GNU  Affero General Public License as published by the Free
Software Foundation, either version 3 of the License, or (at your option) any
later version.

This program is distributed in the hope that it will be useful,  but  WITHOUT
ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
FOR A PARTICULAR PURPOSE.  See the GNU Affero General Public License for more
details.

You should have received a copy of the GNU Affero General Public License
along with this program.  If not, see: <http://www.gnu.org/licenses/>
"""
##############################################################################
import sys
import pagekite.pk as pk
import pagekite.httpd as httpd

if __name__ == "__main__":
  kn = '@KITENAME@'
  ss = '@SECRET@'
  if len(sys.argv) == 1:
    sys.argv.extend([
      '--daemonize',
      '--runas=nobody',
      '--logfile=/tmp/pagekite-%s.log' % kn,
    ])
  sys.argv[1:1] = [
    '--clean',
    '--noloop',
    '--nocrashreport',
    '--defaults',
    '--kitename=%s' % kn,
    '--kitesecret=%s' % ss,
    '--all'
  ]
  sys.argv.extend('@ARGS@'.split())

  pk.Main(pk.PageKite, pk.Configure,
          http_handler=httpd.UiRequestHandler,
          http_server=httpd.UiHttpServer)


########NEW FILE########
__FILENAME__ = httpd
"""
This is the pagekite.py built-in HTTP server.
"""
##############################################################################
LICENSE = """\
This file is part of pagekite.py.
Copyright 2010-2013, the Beanstalks Project ehf. and Bjarni Runar Einarsson

This program is free software: you can redistribute it and/or modify it under
the terms of the  GNU  Affero General Public License as published by the Free
Software Foundation, either version 3 of the License, or (at your option) any
later version.

This program is distributed in the hope that it will be useful,  but  WITHOUT
ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
FOR A PARTICULAR PURPOSE.  See the GNU Affero General Public License for more
details.

You should have received a copy of the GNU Affero General Public License
along with this program.  If not, see: <http://www.gnu.org/licenses/>
"""
##############################################################################
import base64
import cgi
from cgi import escape as escape_html
import os
import re
import socket
import sys
import tempfile
import threading
import time
import traceback
import urllib

import SocketServer
from CGIHTTPServer import CGIHTTPRequestHandler
from SimpleXMLRPCServer import SimpleXMLRPCServer, SimpleXMLRPCRequestHandler
import Cookie

from pagekite.common import *
from pagekite.compat import *
import pagekite.common as common
import pagekite.logging as logging
import pagekite.proto.selectables as selectables
import sockschain as socks


##[ Conditional imports & compatibility magic! ]###############################

try:
  import datetime
  ts_to_date = datetime.datetime.fromtimestamp
except ImportError:
  ts_to_date = str

try:
  sorted([1, 2, 3])
except:
  def sorted(l):
    tmp = l[:]
    tmp.sort()
    return tmp


# Different Python 2.x versions complain about deprecation depending on
# where we pull these from.
try:
  from urlparse import parse_qs, urlparse
except ImportError, e:
  from cgi import parse_qs
  from urlparse import urlparse
try:
  import hashlib
  def sha1hex(data):
    hl = hashlib.sha1()
    hl.update(data)
    return hl.hexdigest().lower()
except ImportError:
  import sha
  def sha1hex(data):
    return sha.new(data).hexdigest().lower()


##[ PageKite HTTPD code starts here! ]#########################################


class AuthError(Exception):
  pass


def fmt_size(count):
  if count > 2*(1024*1024*1024):
    return '%dGB' % (count / (1024*1024*1024))
  if count > 2*(1024*1024):
    return '%dMB' % (count / (1024*1024))
  if count > 2*(1024):
    return '%dKB' % (count / 1024)
  return '%dB' % count


class CGIWrapper(CGIHTTPRequestHandler):
  def __init__(self, request, path_cgi):
    self.path = path_cgi
    self.cgi_info = (os.path.dirname(path_cgi),
                     os.path.basename(path_cgi))
    self.request = request
    self.server = request.server
    self.command = request.command
    self.headers = request.headers
    self.client_address = ('unknown', 0)
    self.rfile = request.rfile
    self.wfile = tempfile.TemporaryFile()

  def translate_path(self, path): return path

  def send_response(self, code, message):
    self.wfile.write('X-Response-Code: %s\r\n' % code)
    self.wfile.write('X-Response-Message: %s\r\n' % message)

  def send_error(self, code, message):
    return self.send_response(code, message)

  def Run(self):
    self.run_cgi()
    self.wfile.seek(0)
    return self.wfile


class UiRequestHandler(SimpleXMLRPCRequestHandler):

  # Make all paths/endpoints legal, we interpret them below.
  rpc_paths = ( )

  E403 = { 'code': '403', 'msg': 'Missing', 'mimetype': 'text/html',
           'title': '403 Not found',
           'body': '<p>File or directory not found. Sorry!</p>' }
  E404 = { 'code': '404', 'msg': 'Not found', 'mimetype': 'text/html',
           'title': '404 Not found',
           'body': '<p>File or directory not found. Sorry!</p>' }
  ROBOTSTXT = { 'code': '200', 'msg': 'OK', 'mimetype': 'text/plain',
                'body': ('User-agent: *\n'
                         'Disallow: /\n'
                         '# pagekite.py default robots.txt\n') }

  MIME_TYPES = {
    '3gp': 'video/3gpp',            'aac': 'audio/aac',
    'atom': 'application/atom+xml', 'avi': 'video/avi',
    'bmp': 'image/bmp',             'bz2': 'application/x-bzip2',
    'c': 'text/plain',              'cpp': 'text/plain',
    'css': 'text/css',
    'conf': 'text/plain',           'cfg': 'text/plain',
    'dtd': 'application/xml-dtd',   'doc': 'application/msword',
    'gif': 'image/gif',             'gz': 'application/x-gzip',
    'h': 'text/plain',              'hpp': 'text/plain',
    'htm': 'text/html',             'html': 'text/html',
    'hqx': 'application/mac-binhex40',
    'java': 'text/plain',           'jar': 'application/java-archive',
    'jpg': 'image/jpeg',            'jpeg': 'image/jpeg',
    'js': 'application/javascript',
    'json': 'application/json',     'jsonp': 'application/javascript',
    'log': 'text/plain',
    'md': 'text/plain',            'midi': 'audio/x-midi',
    'mov': 'video/quicktime',      'mpeg': 'video/mpeg',
    'mp2': 'audio/mpeg',           'mp3': 'audio/mpeg',
    'm4v': 'video/mp4',            'mp4': 'video/mp4',
    'm4a': 'audio/mp4',
    'ogg': 'audio/vorbis',
    'pdf': 'application/pdf',      'ps': 'application/postscript',
    'pl': 'text/plain',            'png': 'image/png',
    'ppt': 'application/vnd.ms-powerpoint',
    'py': 'text/plain',            'pyw': 'text/plain',
    'pk-shtml': 'text/html',       'pk-js': 'application/javascript',
    'rc': 'text/plain',            'rtf': 'application/rtf',
    'rss': 'application/rss+xml',  'sgml': 'text/sgml',
    'sh': 'text/plain',            'shtml': 'text/plain',
    'svg': 'image/svg+xml',        'swf': 'application/x-shockwave-flash',
    'tar': 'application/x-tar',    'tgz': 'application/x-tar',
    'tiff': 'image/tiff',          'txt': 'text/plain',
    'wav': 'audio/wav',
    'xml': 'application/xml',      'xls': 'application/vnd.ms-excel',
    'xrdf': 'application/xrds+xml','zip': 'application/zip',
    'DEFAULT': 'application/octet-stream'
  }
  TEMPLATE_RAW = ('%(body)s')
  TEMPLATE_JSONP = ('window.pkData = %s;')
  TEMPLATE_HTML = ('<html><head>\n'
               '<link rel="stylesheet" media="screen, screen"'
                ' href="%(method)s://pagekite.net/css/pagekite.css"'
                ' type="text/css" title="Default stylesheet" />\n'
               '<title>%(title)s - %(prog)s v%(ver)s</title>\n'
              '</head><body>\n'
               '<h1>%(title)s</h1>\n'
               '<div id=body>%(body)s</div>\n'
               '<div id=footer><hr><i>Powered by <b>pagekite.py'
                ' v%(ver)s</b> and'
                ' <a href="'+ WWWHOME +'"><i>PageKite.net</i></a>.<br>'
                'Local time is %(now)s.</i></div>\n'
              '</body></html>\n')

  def setup(self):
    self.suppress_body = False
    if self.server.enable_ssl:
      self.connection = self.request
      self.rfile = socket._fileobject(self.request, "rb", self.rbufsize)
      self.wfile = socket._fileobject(self.request, "wb", self.wbufsize)
    else:
      SimpleXMLRPCRequestHandler.setup(self)

  def log_message(self, format, *args):
    logging.Log([('uireq', format % args)])

  def send_header(self, header, value):
    self.wfile.write('%s: %s\r\n' % (header, value))

  def end_headers(self):
    self.wfile.write('\r\n')

  def sendStdHdrs(self, header_list=[], cachectrl='private',
                                        mimetype='text/html'):
    if mimetype.startswith('text/') and ';' not in mimetype:
      mimetype += ('; charset=%s' % DEFAULT_CHARSET)
    self.send_header('Cache-Control', cachectrl)
    self.send_header('Content-Type', mimetype)
    for header in header_list:
      self.send_header(header[0], header[1])
    self.end_headers()

  def sendChunk(self, chunk):
    if self.chunked:
      if logging.DEBUG_IO: print '<== SENDING CHUNK ===\n%s\n' % chunk
      self.wfile.write('%x\r\n' % len(chunk))
      self.wfile.write(chunk)
      self.wfile.write('\r\n')
    else:
      if logging.DEBUG_IO: print '<== SENDING ===\n%s\n' % chunk
      self.wfile.write(chunk)

  def sendEof(self):
    if self.chunked and not self.suppress_body: self.wfile.write('0\r\n\r\n')

  def sendResponse(self, message, code=200, msg='OK', mimetype='text/html',
                         header_list=[], chunked=False, length=None):
    self.log_request(code, message and len(message) or '-')
    self.wfile.write('HTTP/1.1 %s %s\r\n' % (code, msg))
    if code == 401:
      self.send_header('WWW-Authenticate',
                       'Basic realm=PK%d' % (time.time()/3600))

    self.chunked = chunked
    if chunked:
      self.send_header('Transfer-Encoding', 'chunked')
    else:
      if length:
        self.send_header('Content-Length', length)
      elif not chunked:
        self.send_header('Content-Length', len(message or ''))

    self.sendStdHdrs(header_list=header_list, mimetype=mimetype)
    if message and not self.suppress_body:
      self.sendChunk(message)

  def needPassword(self):
    if self.server.pkite.ui_password: return True
    userkeys = [k for k in self.host_config.keys() if k.startswith('password/')]
    return userkeys

  def checkUsernamePasswordAuth(self, username, password):
    userkey = 'password/%s' % username
    if userkey in self.host_config:
      if self.host_config[userkey] == password:
        return

    if (self.server.pkite.ui_password and
        password == self.server.pkite.ui_password):
      return

    if self.needPassword():
      raise AuthError("Invalid password")

  def checkRequestAuth(self, scheme, netloc, path, qs):
    if self.needPassword():
      raise AuthError("checkRequestAuth not implemented")

  def checkPostAuth(self, scheme, netloc, path, qs, posted):
    if self.needPassword():
      raise AuthError("checkPostAuth not implemented")

  def performAuthChecks(self, scheme, netloc, path, qs):
    try:
      auth = self.headers.get('authorization')
      if auth:
        (how, ab64) = auth.strip().split()
        if how.lower() == 'basic':
          (username, password) = base64.decodestring(ab64).split(':')
          self.checkUsernamePasswordAuth(username, password)
          return True

      self.checkRequestAuth(scheme, netloc, path, qs)
      return True

    except (ValueError, KeyError, AuthError), e:
      logging.LogDebug('HTTP Auth failed: %s' % e)
    else:
      logging.LogDebug('HTTP Auth failed: Unauthorized')

    self.sendResponse('<h1>Unauthorized</h1>\n', code=401, msg='Forbidden')
    return False

  def performPostAuthChecks(self, scheme, netloc, path, qs, posted):
    try:
      self.checkPostAuth(scheme, netloc, path, qs, posted)
      return True
    except AuthError:
      self.sendResponse('<h1>Unauthorized</h1>\n', code=401, msg='Forbidden')
      return False

  def do_UNSUPPORTED(self):
    self.sendResponse('Unsupported request method.\n',
                      code=503, msg='Sorry', mimetype='text/plain')

  # Misc methods we don't support (yet)
  def do_OPTIONS(self): self.do_UNSUPPORTED()
  def do_DELETE(self): self.do_UNSUPPORTED()
  def do_PUT(self): self.do_UNSUPPORTED()

  def getHostInfo(self):
    http_host = self.headers.get('HOST', self.headers.get('host', 'unknown'))
    if http_host == 'unknown' or (http_host.startswith('localhost:') and
                http_host.replace(':', '/') not in self.server.pkite.be_config):
      http_host = None
      for bid in sorted(self.server.pkite.backends.keys()):
        be = self.server.pkite.backends[bid]
        if (be[BE_BPORT] == self.server.pkite.ui_sspec[1] and
            be[BE_STATUS] not in BE_INACTIVE):
          http_host = '%s:%s' % (be[BE_DOMAIN],
                                 be[BE_PORT] or 80)
    if not http_host:
      if self.server.pkite.be_config.keys():
        http_host = sorted(self.server.pkite.be_config.keys()
                           )[0].replace('/', ':')
      else:
        http_host = 'unknown'
    self.http_host = http_host
    self.host_config = self.server.pkite.be_config.get((':' in http_host
                                                           and http_host
                                                            or http_host+':80'
                                                        ).replace(':', '/'), {})

  def do_GET(self, command='GET'):
    (scheme, netloc, path, params, query, frag) = urlparse(self.path)
    qs = parse_qs(query)
    self.getHostInfo()
    self.post_data = None
    self.command = command
    if not self.performAuthChecks(scheme, netloc, path, qs): return
    try:
      return self.handleHttpRequest(scheme, netloc, path, params, query, frag,
                                    qs, None)
    except socket.error:
      pass
    except Exception, e:
      logging.Log([('err', 'GET error at %s: %s' % (path, e))])
      if logging.DEBUG_IO: print '=== ERROR\n%s\n===' % format_exc()
      self.sendResponse('<h1>Internal Error</h1>\n', code=500, msg='Error')

  def do_HEAD(self):
    self.suppress_body = True
    self.do_GET(command='HEAD')

  def do_POST(self, command='POST'):
    (scheme, netloc, path, params, query, frag) = urlparse(self.path)
    qs = parse_qs(query)
    self.getHostInfo()
    self.command = command

    if not self.performAuthChecks(scheme, netloc, path, qs): return

    posted = None
    self.post_data = tempfile.TemporaryFile()
    self.old_rfile = self.rfile
    try:
      # First, buffer the POST data to a file...
      clength = cleft = int(self.headers.get('content-length'))
      while cleft > 0:
        rbytes = min(64*1024, cleft)
        self.post_data.write(self.rfile.read(rbytes))
        cleft -= rbytes

      # Juggle things so the buffering is invisble.
      self.post_data.seek(0)
      self.rfile = self.post_data

      ctype, pdict = cgi.parse_header(self.headers.get('content-type'))
      if ctype == 'multipart/form-data':
        self.post_data.seek(0)
        posted = cgi.parse_multipart(self.rfile, pdict)
      elif ctype == 'application/x-www-form-urlencoded':
        if clength >= 50*1024*1024:
          raise Exception(("Refusing to parse giant posted query "
                           "string (%s bytes).") % clength)
        posted = cgi.parse_qs(self.rfile.read(clength), 1)
      elif self.host_config.get('xmlrpc', False):
        # We wrap the XMLRPC request handler in _BEGIN/_END in order to
        # expose the request environment to the RPC functions.
        RCI = self.server.RCI
        return RCI._END(SimpleXMLRPCRequestHandler.do_POST(RCI._BEGIN(self)))

      self.post_data.seek(0)
    except socket.error:
      pass
    except Exception, e:
      logging.Log([('err', 'POST error at %s: %s' % (path, e))])
      self.sendResponse('<h1>Internal Error</h1>\n', code=500, msg='Error')
      self.rfile = self.old_rfile
      self.post_data = None
      return

    if not self.performPostAuthChecks(scheme, netloc, path, qs, posted): return
    try:
      return self.handleHttpRequest(scheme, netloc, path, params, query, frag,
                                    qs, posted)
    except socket.error:
      pass
    except Exception, e:
      logging.Log([('err', 'POST error at %s: %s' % (path, e))])
      self.sendResponse('<h1>Internal Error</h1>\n', code=500, msg='Error')

    self.rfile = self.old_rfile
    self.post_data = None

  def openCGI(self, full_path, path, shtml_vars):
    cgi_file = CGIWrapper(self, full_path).Run()
    lines = cgi_file.read(32*1024).splitlines(True)
    if '\r\n' in lines: lines = lines[0:lines.index('\r\n')+1]
    elif '\n' in lines: lines = lines[0:lines.index('\n')+1]
    else: lines.append('')

    header_list = []
    response_code = 200
    response_message = 'OK'
    response_mimetype = 'text/html'
    for line in lines[:-1]:
      key, val = line.strip().split(': ', 1)
      if key == 'X-Response-Code':
        response_code = val
      elif key == 'X-Response-Message':
        response_message = val
      elif key.lower() == 'content-type':
        response_mimetype = val
      elif key.lower() == 'location':
        response_code = 302
        header_list.append((key, val))
      else:
        header_list.append((key, val))

    self.sendResponse(None, code=response_code,
                            msg=response_message,
                            mimetype=response_mimetype,
                            chunked=True, header_list=header_list)
    cgi_file.seek(sum([len(l) for l in lines]))
    return cgi_file

  def renderIndex(self, full_path, files=None):
    files = files or [(f, os.path.join(full_path, f))
                      for f in sorted(os.listdir(full_path))]

    # Remove dot-files and PageKite metadata files
    if self.host_config.get('indexes') != WEB_INDEX_ALL:
      files = [f for f in files if not (f[0].startswith('.') or
                                        f[0].startswith('_pagekite'))]

    fhtml = ['<table>']
    if files:
      for (fn, fpath) in files:
        fmimetype = self.getMimeType(fn)
        try:
          fsize = os.path.getsize(fpath) or ''
        except OSError:
          fsize = 0
        ops = [ ]
        if os.path.isdir(fpath):
          fclass = ['dir']
          if not fn.endswith('/'): fn += '/'
          qfn = urllib.quote(fn)
        else:
          qfn = urllib.quote(fn)
          fn = os.path.basename(fn)
          fclass = ['file']
          ops.append('download')
          if (fmimetype.startswith('text/') or
              (fmimetype == 'application/octet-stream' and fsize < 512000)):
            ops.append('view')
        (unused, ext) = os.path.splitext(fn)
        if ext:
          fclass.append(ext.replace('.', 'ext_'))
        fclass.append('mime_%s' % fmimetype.replace('/', '_'))

        ophtml = ', '.join([('<a class="%s" href="%s?%s=/%s">%s</a>'
                             ) % (op, qfn, op, qfn, op)
                            for op in sorted(ops)])
        try:
          mtime = full_path and int(os.path.getmtime(fpath) or time.time())
        except OSError:
          mtime = int(time.time())
        fhtml.append(('<tr class="%s">'
                       '<td class="ops">%s</td>'
                       '<td class="size">%s</td>'
                       '<td class="mtime">%s</td>'
                       '<td class="name"><a href="%s">%s</a></td>'
                      '</tr>'
                      ) % (' '.join(fclass), ophtml, fsize,
                           str(ts_to_date(mtime)), qfn,
                           fn.replace('<', '&lt;'),
                      ))
    else:
      fhtml.append('<tr><td><i>empty</i></td></tr>')
    fhtml.append('</table>')
    return ''.join(fhtml)

  def sendStaticPath(self, path, mimetype, shtml_vars=None):
    pkite = self.server.pkite
    is_shtml, is_cgi, is_dir = False, False, False
    index_list = None
    try:
      path = urllib.unquote(path)
      if path.find('..') >= 0: raise IOError("Evil")

      paths = pkite.ui_paths
      def_paths = paths.get('*', {})
      http_host = self.http_host
      if ':' not in http_host: http_host += ':80'
      host_paths = paths.get(http_host.replace(':', '/'), {})
      path_parts = path.split('/')
      path_rest = []
      full_path = ''
      root_path = ''
      while len(path_parts) > 0 and not full_path:
        pf = '/'.join(path_parts)
        pd = pf+'/'
        m = None
        if   pf in host_paths: m = host_paths[pf]
        elif pd in host_paths: m = host_paths[pd]
        elif pf in def_paths: m = def_paths[pf]
        elif pd in def_paths: m = def_paths[pd]
        if m:
          policy = m[0]
          root_path = m[1]
          full_path = os.path.join(root_path, *path_rest)
        else:
          path_rest.insert(0, path_parts.pop())

      if full_path:
        is_dir = os.path.isdir(full_path)
      else:
        if not self.host_config.get('indexes', False): return False
        if self.host_config.get('hide', False): return False

        # Generate pseudo-index
        ipath = path
        if not ipath.endswith('/'): ipath += '/'
        plen = len(ipath)
        index_list = [(p[plen:], host_paths[p][1]) for p
                                                   in sorted(host_paths.keys())
                                                   if p.startswith(ipath)]
        if not index_list: return False

        full_path = ''
        mimetype = 'text/html'
        is_dir = True

      if is_dir and not path.endswith('/'):
        self.sendResponse('\n', code=302, msg='Moved', header_list=[
                            ('Location', '%s/' % path)
                          ])
        return True

      indexes = ['index.html', 'index.htm', '_pagekite.html']

      dynamic_suffixes = []
      if self.host_config.get('pk-shtml'):
        indexes[0:0] = ['index.pk-shtml']
        dynamic_suffixes = ['.pk-shtml', '.pk-js']

      cgi_suffixes = []
      cgi_config = self.host_config.get('cgi', False)
      if cgi_config:
        if cgi_config == True: cgi_config = 'cgi'
        for suffix in cgi_config.split(','):
          indexes[0:0] = ['index.%s' % suffix]
          cgi_suffixes.append('.%s' % suffix)

      for index in indexes:
        ipath = os.path.join(full_path, index)
        if os.path.exists(ipath):
          mimetype = 'text/html'
          full_path = ipath
          is_dir = False
          break

      self.chunked = False
      rf_stat = rf_size = None
      if full_path:
        if is_dir:
          mimetype = 'text/html'
          rf_size = rf = None
          rf_stat = os.stat(full_path)
        else:
          for s in dynamic_suffixes:
            if full_path.endswith(s): is_shtml = True
          for s in cgi_suffixes:
            if full_path.endswith(s): is_cgi = True
          if not is_shtml and not is_cgi: shtml_vars = None
          rf = open(full_path, "rb")
          try:
            rf_stat = os.fstat(rf.fileno())
            rf_size = rf_stat.st_size
          except:
            self.chunked = True
    except (IOError, OSError), e:
      return False

    headers = [ ]
    if rf_stat and not (is_dir or is_shtml or is_cgi):
      # ETags for static content: we trust the file-system.
      etag = sha1hex(':'.join(['%s' % s for s in [full_path, rf_stat.st_mode,
                                   rf_stat.st_ino, rf_stat.st_dev,
                                   rf_stat.st_nlink, rf_stat.st_uid,
                                   rf_stat.st_gid, rf_stat.st_size,
                                   int(rf_stat.st_mtime),
                                   int(rf_stat.st_ctime)]]))[0:24]
      if etag == self.headers.get('if-none-match', None):
        rf.close()
        self.sendResponse('', code=304, msg='Not Modified', mimetype=mimetype)
        return True
      else:
        headers.append(('ETag', etag))

      # FIXME: Support ranges for resuming aborted transfers?

    if is_cgi:
      self.chunked = True
      rf = self.openCGI(full_path, path, shtml_vars)
    else:
      self.sendResponse(None, mimetype=mimetype,
                              length=rf_size,
                              chunked=self.chunked or (shtml_vars is not None),
                              header_list=headers)

    chunk_size = (is_shtml and 1024 or 16) * 1024
    if rf:
      while not self.suppress_body:
        data = rf.read(chunk_size)
        if data == "": break
        if is_shtml and shtml_vars:
          self.sendChunk(data % shtml_vars)
        else:
          self.sendChunk(data)
      rf.close()

    elif shtml_vars and not self.suppress_body:
      shtml_vars['title'] = '//%s%s' % (shtml_vars['http_host'], path)
      if self.host_config.get('indexes') in (True, WEB_INDEX_ON,
                                                   WEB_INDEX_ALL):
        shtml_vars['body'] = self.renderIndex(full_path, files=index_list)
      else:
        shtml_vars['body'] = ('<p><i>Directory listings disabled and</i> '
                              'index.html <i>not found.</i></p>')
      self.sendChunk(self.TEMPLATE_HTML % shtml_vars)

    self.sendEof()
    return True

  def getMimeType(self, path):
    try:
      ext = path.split('.')[-1].lower()
    except IndexError:
      ext = 'DIRECTORY'

    if ext in self.MIME_TYPES: return self.MIME_TYPES[ext]
    return self.MIME_TYPES['DEFAULT']

  def add_kite(self, path, qs):
    if path.find(self.server.secret) == -1:
      return {'mimetype': 'text/plain', 'body': 'Invalid secret'}

    pass

  def handleHttpRequest(self, scheme, netloc, path, params, query, frag,
                              qs, posted):
    data = {
      'prog': self.server.pkite.progname,
      'mimetype': self.getMimeType(path),
      'hostname': socket.gethostname() or 'Your Computer',
      'http_host': self.http_host,
      'query_string': query,
      'code': 200,
      'body': '',
      'msg': 'OK',
      'now': time.strftime('%Y-%m-%d %H:%M:%S', time.localtime()),
      'ver': APPVER
    }
    for key in self.headers.keys():
      data['http_'+key.lower()] = self.headers.get(key)

    if 'download' in qs:
      data['mimetype'] = 'application/octet-stream'
      # Would be nice to set Content-Disposition too.
    elif 'view' in qs:
      data['mimetype'] = 'text/plain'

    data['method'] = data.get('http_x-pagekite-proto', 'http').lower()

    if 'http_cookie' in data:
      cookies = Cookie.SimpleCookie(data['http_cookie'])
    else:
      cookies = {}

    # Do we expose the built-in console?
    console = self.host_config.get('console', False)

    if path == self.host_config.get('yamon', False):
      if common.gYamon:
        data['body'] = common.gYamon.render_vars_text(qs.get('view', [None])[0])
      else:
        data['body'] = ''

    elif console and path.startswith('/_pagekite/logout/'):
      parts = path.split('/')
      location = parts[3] or ('%s://%s/' % (data['method'], data['http_host']))
      self.sendResponse('\n', code=302, msg='Moved', header_list=[
                          ('Set-Cookie', 'pkite_token=; path=/'),
                          ('Location', location)
                        ])
      return

    elif console and path.startswith('/_pagekite/login/'):
      parts = path.split('/', 4)
      token = parts[3]
      location = parts[4] or ('%s://%s/_pagekite/' % (data['method'],
                                                      data['http_host']))
      if query: location += '?' + query
      if token == self.server.secret:
        self.sendResponse('\n', code=302, msg='Moved', header_list=[
                            ('Set-Cookie', 'pkite_token=%s; path=/' % token),
                            ('Location', location)
                          ])
        return
      else:
        logging.LogDebug("Invalid token, %s != %s" % (token,
                                                       self.server.secret))
        data.update(self.E404)

    elif console and path.startswith('/_pagekite/'):
      if not ('pkite_token' in cookies and cookies['pkite_token'].value == self.server.secret):
        self.sendResponse('<h1>Forbidden</h1>\n', code=403, msg='Forbidden')
        return

      if path == '/_pagekite/':
        if not self.sendStaticPath('%s/control.pk-shtml' % console, 'text/html',
                                   shtml_vars=data):
          self.sendResponse('<h1>Not found</h1>\n', code=404, msg='Missing')
        return
      elif path.startswith('/_pagekite/quitquitquit/'):
        self.sendResponse('<h1>Kaboom</h1>\n', code=500, msg='Asplode')
        self.wfile.flush()
        os._exit(2)
      elif path.startswith('/_pagekite/add_kite/'):
        data.update(self.add_kite(path, qs))
      elif path.endswith('/pagekite.rc'):
        data.update({'mimetype': 'application/octet-stream',
                     'body': '\n'.join(self.server.pkite.GenerateConfig())})
      elif path.endswith('/pagekite.rc.txt'):
        data.update({'mimetype': 'text/plain',
                     'body': '\n'.join(self.server.pkite.GenerateConfig())})
      elif path.endswith('/pagekite.cfg'):
        data.update({'mimetype': 'application/octet-stream',
                     'body': '\r\n'.join(self.server.pkite.GenerateConfig())})
      else:
        data.update(self.E403)
    else:
      if self.sendStaticPath(path, data['mimetype'], shtml_vars=data):
        return
      if path == '/robots.txt':
        data.update(self.ROBOTSTXT)
      else:
        data.update(self.E404)

    if data['mimetype'] in ('application/octet-stream', 'text/plain'):
      response = self.TEMPLATE_RAW % data
    elif path.endswith('.jsonp'):
      response = self.TEMPLATE_JSONP % (data, )
    else:
      response = self.TEMPLATE_HTML % data

    self.sendResponse(response, msg=data['msg'],
                                code=data['code'],
                                mimetype=data['mimetype'],
                                chunked=False)
    self.sendEof()


class RemoteControlInterface(object):
  ACL_OPEN = ''
  ACL_READ = 'r'
  ACL_WRITE = 'w'

  def __init__(self, httpd, pkite, conns):
    self.httpd = httpd
    self.pkite = pkite
    self.conns = conns
    self.modified = False

    self.lock = threading.Lock()
    self.request = None

    # For now, nobody gets ACL_WRITE
    self.auth_tokens = {httpd.secret: self.ACL_READ}

    # Channels are in-memory logs which can be tailed over XML-RPC.
    # Javascript apps can create these for implementing chat etc.
    self.channels = {'LOG': {'access': self.ACL_READ,
                             'tokens': self.auth_tokens,
                             'data': logging.LOG}}

  def _BEGIN(self, request_object):
    self.lock.acquire()
    self.request = request_object
    return request_object

  def _END(self, rv=None):
    if self.request:
      self.request = None
      self.lock.release()
    return rv

  def connections(self, auth_token):
    if (not self.request.host_config.get('console', False) or
        self.ACL_READ not in self.auth_tokens.get(auth_token, self.ACL_OPEN)):
      raise AuthError('Unauthorized')

    return [{'sid': c.sid,
             'dead': c.dead,
             'html': c.__html__()} for c in self.conns.conns]

  def add_kite(self, auth_token, kite_domain, kite_proto):
    if (not self.request.host_config.get('console', False) or
        self.ACL_WRITE not in self.auth_tokens.get(auth_token, self.ACL_OPEN)):
      raise AuthError('Unauthorized')
    pass

  def get_kites(self, auth_token):
    if (not self.request.host_config.get('console', False) or
        self.ACL_READ not in self.auth_tokens.get(auth_token, self.ACL_OPEN)):
      raise AuthError('Unauthorized')

    kites = []
    for bid in self.pkite.backends:
      proto, domain = bid.split(':')
      fe_proto = proto.split('-')
      kite_info = {
        'id': bid,
        'domain': domain,
        'fe_proto': fe_proto[0],
        'fe_port': (len(fe_proto) > 1) and fe_proto[1] or '',
        'fe_secret': self.pkite.backends[bid][BE_SECRET],
        'be_proto': self.pkite.backends[bid][BE_PROTO],
        'backend': self.pkite.backends[bid][BE_BACKEND],
        'fe_list': [{'name': fe.server_name,
                     'tls': fe.using_tls,
                     'sid': fe.sid} for fe in self.conns.Tunnel(proto, domain)]
      }
      kites.append(kite_info)
    return kites

  def add_kite(self, auth_token,
               proto,
               fe_port, fe_domain,
               be_port, be_domain,
               shared_secret):
    if (not self.request.host_config.get('console', False) or
        self.ACL_WRITE not in self.auth_tokens.get(auth_token, self.ACL_OPEN)):
      raise AuthError('Unauthorized')
    # FIXME

  def remove_kite(self, auth_token, kite_id):
    if (not self.request.host_config.get('console', False) or
        self.ACL_WRITE not in self.auth_tokens.get(auth_token, self.ACL_OPEN)):
      raise AuthError('Unauthorized')

    if kite_id in self.pkite.backends:
      del self.pkite.backends[kite_id]
      logging.Log([('reconfigured', '1'), ('removed', kite_id)])
      self.modified = True
    return self.get_kites(auth_token)

  def mk_channel(self, auth_token, channel):
    if not self.request.host_config.get('channels', False):
      raise AuthError('Unauthorized')

    chid = '%s/%s' % (self.request.http_host, channel)
    if chid in self.channels:
      raise Error('Exists')
    else:
      self.channels[chid] = {'access': self.ACL_WRITE,
                             'tokens': {auth_token: self.ACL_WRITE},
                             'data': []}
      return self.append_channel(auth_token, channel, {'created': channel})

  def get_channel(self, auth_token, channel):
    if not self.request.host_config.get('channels', False):
      raise AuthError('Unauthorized')

    chan = self.channels.get('%s/%s' % (self.request.http_host, channel),
                             self.channels.get(channel, {}))
    req = chan.get('access', self.ACL_WRITE)
    if req not in chan.get('tokens', self.auth_tokens).get(auth_token,
                                                           self.ACL_OPEN):
      raise AuthError('Unauthorized')

    return chan.get('data', [])

  def append_channel(self, auth_token, channel, values):
    data = self.get_channel(auth_token, channel)
    global LOG_LINE
    values.update({'ts': '%x' % time.time(), 'll': '%x' % LOG_LINE})
    LOG_LINE += 1
    data.append(values)
    return values

  def get_channel_after(self, auth_token, channel, last_seen, timeout):
    data = self.get_channel(auth_token, channel)
    last_seen = int(last_seen, 16)

    # line at the remote end, then we've restarted and should send everything.
    if (last_seen == 0) or (LOG_LINE < last_seen): return data
    # FIXME: LOG_LINE global for all channels?  Is that suck?

    # We are about to get sleepy, so release our environment lock.
    self._END()

    # If our internal LOG_LINE counter is less than the count of the last seen
    # Else, wait at least one second, AND wait for a new line to be added to
    # the log (or the timeout to expire).
    time.sleep(1)
    last_ll = data[-1]['ll']
    while (timeout > 0) and (data[-1]['ll'] == last_ll):
      time.sleep(1)
      timeout -= 1

    # Return everything the client hasn't already seen.
    return [ll for ll in data if int(ll['ll'], 16) > last_seen]


class UiHttpServer(SocketServer.ThreadingMixIn, SimpleXMLRPCServer):
  def __init__(self, sspec, pkite, conns,
               handler=UiRequestHandler,
               ssl_pem_filename=None):
    SimpleXMLRPCServer.__init__(self, sspec, handler)
    self.pkite = pkite
    self.conns = conns
    self.secret = pkite.ConfigSecret()

    self.server_name = sspec[0]
    self.server_port = sspec[1]

    if ssl_pem_filename:
      ctx = socks.SSL.Context(socks.SSL.TLSv1_METHOD)
      ctx.use_privatekey_file (ssl_pem_filename)
      ctx.use_certificate_chain_file(ssl_pem_filename)
      self.socket = socks.SSL_Connect(ctx, socket.socket(self.address_family,
                                                         self.socket_type),
                                         server_side=True)
      self.server_bind()
      self.server_activate()
      self.enable_ssl = True
    else:
      self.enable_ssl = False

    try:
      from pagekite import yamond
      gYamon = common.gYamon = yamond.YamonD(sspec)
      gYamon.vset('started', int(time.time()))
      gYamon.vset('version', APPVER)
      gYamon.vset('httpd_ssl_enabled', self.enable_ssl)
      gYamon.vset('errors', 0)
      gYamon.lcreate("tunnel_rtt", 100)
      gYamon.lcreate("tunnel_wrtt", 100)
      gYamon.lists['buffered_bytes'] = [1, 0, common.buffered_bytes]
      gYamon.views['selectables'] = (selectables.SELECTABLES, {
        'idle': [0, 0, self.conns.idle],
        'conns': [0, 0, self.conns.conns]
      })
    except:
      pass

    self.RCI = RemoteControlInterface(self, pkite, conns)
    self.register_introspection_functions()
    self.register_instance(self.RCI)

  def finish_request(self, request, client_address):
    try:
      SimpleXMLRPCServer.finish_request(self, request, client_address)
    except (socket.error, socks.SSL.ZeroReturnError, socks.SSL.Error):
      pass



########NEW FILE########
__FILENAME__ = logging
"""
Logging.
"""
##############################################################################
LICENSE = """\
This file is part of pagekite.py.
Copyright 2010-2013, the Beanstalks Project ehf. and Bjarni Runar Einarsson

This program is free software: you can redistribute it and/or modify it under
the terms of the  GNU  Affero General Public License as published by the Free
Software Foundation, either version 3 of the License, or (at your option) any
later version.

This program is distributed in the hope that it will be useful,  but  WITHOUT
ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
FOR A PARTICULAR PURPOSE.  See the GNU Affero General Public License for more
details.

You should have received a copy of the GNU Affero General Public License
along with this program.  If not, see: <http://www.gnu.org/licenses/>
"""
##############################################################################
import time
import sys

import compat, common
from compat import *
from common import *

syslog = compat.syslog
org_stdout = sys.stdout

DEBUG_IO = False

LOG = []
LOG_LINE = 0
LOG_LENGTH = 300
LOG_THRESHOLD = 256 * 1024

def LogValues(values, testtime=None):
  global LOG, LOG_LINE, LOG_LAST_TIME
  now = int(testtime or time.time())
  words = [('ts', '%x' % now),
           ('t',  '%s' % ts_to_iso(now)),
           ('ll', '%x' % LOG_LINE)]
  words.extend([(kv[0], ('%s' % kv[1]).replace('\t', ' ')
                                      .replace('\r', ' ')
                                      .replace('\n', ' ')
                                      .replace('; ', ', ')
                                      .strip()) for kv in values])
  wdict = dict(words)
  LOG_LINE += 1
  LOG.append(wdict)
  while len(LOG) > LOG_LENGTH:
    LOG[0:(LOG_LENGTH/10)] = []

  return (words, wdict)

def LogSyslog(values, wdict=None, words=None):
  if values:
    words, wdict = LogValues(values)
  if 'err' in wdict:
    syslog.syslog(syslog.LOG_ERR, '; '.join(['='.join(x) for x in words]))
  elif 'debug' in wdict:
    syslog.syslog(syslog.LOG_DEBUG, '; '.join(['='.join(x) for x in words]))
  else:
    syslog.syslog(syslog.LOG_INFO, '; '.join(['='.join(x) for x in words]))

def LogToFile(values, wdict=None, words=None):
  if values:
    words, wdict = LogValues(values)
  global LogFile
  LogFile.write('; '.join(['='.join(x) for x in words]))
  LogFile.write('\n')

def LogToMemory(values, wdict=None, words=None):
  if values:
    LogValues(values)

def FlushLogMemory():
  global LOG
  for l in LOG:
    Log(None, wdict=l, words=[(w, l[w]) for w in l])

def LogError(msg, parms=None):
  emsg = [('err', msg)]
  if parms: emsg.extend(parms)
  Log(emsg)

  if common.gYamon:
    common.gYamon.vadd('errors', 1, wrap=1000000)

def LogDebug(msg, parms=None):
  emsg = [('debug', msg)]
  if parms: emsg.extend(parms)
  Log(emsg)

def LogInfo(msg, parms=None):
  emsg = [('info', msg)]
  if parms: emsg.extend(parms)
  Log(emsg)

def ResetLog():
  global LogFile, Log, org_stdout
  LogFile = org_stdout
  Log = LogToMemory

ResetLog()


########NEW FILE########
__FILENAME__ = logparse
"""
A basic tool for processing and parsing the Pagekite logs. This class
doesn't actually do anything much, it's meant for subclassing.
"""
##############################################################################
LICENSE = """\
This file is part of pagekite.py.
Copyright 2010-2013, the Beanstalks Project ehf. and Bjarni Runar Einarsson

This program is free software: you can redistribute it and/or modify it under
the terms of the  GNU  Affero General Public License as published by the Free
Software Foundation, either version 3 of the License, or (at your option) any
later version.

This program is distributed in the hope that it will be useful,  but  WITHOUT
ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
FOR A PARTICULAR PURPOSE.  See the GNU Affero General Public License for more
details.

You should have received a copy of the GNU Affero General Public License
along with this program.  If not, see: <http://www.gnu.org/licenses/>
"""
##############################################################################
import os
import sys
import time


class PageKiteLogParser(object):
  def __init__(self):
    pass

  def ParseLine(self, line, data=None):
    try:
      if data is None: data = {}
      for word in line.split('; '):
        key, val = word.split('=', 1);
        data[key] = val
      return data
    except Exception:
      return {'raw': '%s' % line}

  def ProcessData(self, data):
    print '%s' % data

  def ProcessLine(self, line, data=None):
    self.ProcessData(self.ParseLine(line, data))

  def Follow(self, fd, filename):
    # Record last position...
    pos = fd.tell()

    try:
      if os.stat(filename).st_size < pos:
        # Re-open log-file if it's been rotated/trucated
        new_fd = open(filename, 'r')
        fd.close()
        return new_fd
    except (OSError, IOError), e:
      # Failed to stat or open new file, just try again later.
      pass

    # Sleep a bit and then try to read some more
    time.sleep(1)
    fd.seek(pos)
    return fd

  def ReadLog(self, filename=None, after=None, follow=False):
    if filename is not None:
      fd = open(filename, 'r')
    else:
      fd = sys.stdin

    first = True
    while first or follow:
      for line in fd:
        if line.endswith('\n'):
          data = self.ParseLine(line.strip())
          if after is None or ('ts' in data and int(data['ts'], 16) > after):
            self.ProcessData(data)
        else:
          fd.seek(fd.tell() - len(line))
          break

      if follow: fd = self.Follow(fd, filename)
      first = False

  def ReadSyslog(self, filename, pname='pagekite.py', after=None, follow=False):
    fd = open(filename, 'r')
    tag = ' %s[' % pname
    first = True
    while first or follow:
      for line in fd:
        if line.endswith('\n'):
          try:
            parts = line.split(':', 3)
            if parts[2].find(tag) > -1:
              data = self.ParseLine(parts[3].strip())
              if after is None or int(data['ts'], 16) > after:
                self.ProcessData(data)
          except ValueError, e:
            pass
        else:
          fd.seek(fd.tell() - len(line))
          break

      if follow: fd = self.Follow(fd, filename)
      first = False

class PageKiteLogTracker(PageKiteLogParser):
  def __init__(self):
    PageKiteLogParser.__init__(self)
    self.streams = {}

  def ProcessRestart(self, data):
    # Program just restarted, discard streams state.
    self.streams = {}

  def ProcessBandwidthRead(self, stream, data):
    stream['read'] += int(data['read'])

  def ProcessBandwidthWrote(self, stream, data):
    stream['wrote'] += int(data['wrote'])

  def ProcessError(self, stream, data):
    stream['err'] = data['err']

  def ProcessEof(self, stream, data):
    del self.streams[stream['id']]

  def ProcessNewStream(self, stream, data):
    self.streams[stream['id']] = stream
    stream['read'] = 0
    stream['wrote'] = 0

  def ProcessData(self, data):
    if 'id' in data:
      # This is info about a specific stream...
      sid = data['id']

      if 'proto' in data and 'domain' in data and sid not in self.streams:
        self.ProcessNewStream(data, data)

      if sid in self.streams:
        stream = self.streams[sid]

        if 'err' in data: self.ProcessError(stream, data)
        if 'read' in data: self.ProcessBandwidthRead(stream, data)
        if 'wrote' in data: self.ProcessBandwidthWrote(stream, data)
        if 'eof' in data: self.ProcessEof(stream, data)

    elif 'started' in data and 'version' in data:
      self.ProcessRestart(data)


class DebugPKLT(PageKiteLogTracker):

  def ProcessRestart(self, data):
    PageKiteLogTracker.ProcessRestart(self, data)
    print 'RESTARTED %s' % data

  def ProcessNewStream(self, stream, data):
    PageKiteLogTracker.ProcessNewStream(self, stream, data)
    print '[%s] NEW %s' % (stream['id'], data)

  def ProcessBandwidthRead(self, stream, data):
    PageKiteLogTracker.ProcessBandwidthRead(self, stream, data)
    print '[%s] BWR  %s' % (stream['id'], data)

  def ProcessBandwidthWrote(self, stream, data):
    PageKiteLogTracker.ProcessBandwidthWrote(self, stream, data)
    print '[%s] BWW %s' % (stream['id'], data)

  def ProcessError(self, stream, data):
    PageKiteLogTracker.ProcessError(self, stream, data)
    print '[%s] ERR %s' % (stream['id'], data)

  def ProcessEof(self, stream, data):
    PageKiteLogTracker.ProcessEof(self, stream, data)
    print '[%s] EOF %s' % (stream['id'], data)


if __name__ == '__main__':
  sys.stdout = os.fdopen(sys.stdout.fileno(), 'w', 0)
  if len(sys.argv) > 2:
    DebugPKLT().ReadSyslog(sys.argv[1], pname=sys.argv[2])
  else:
    DebugPKLT().ReadLog(sys.argv[1])


########NEW FILE########
__FILENAME__ = manual
#!/usr/bin/env python
"""
The program manual!
"""
import re
import time

from common import *
from compat import ts_to_iso

MAN_NAME = ("""\
    pagekite.py v%s - Make localhost servers publicly visible
""" % APPVER)
MAN_SYNOPSIS = ("""\
    <b>pagekite.py</b> [<a>--options</a>] [<a>service</a>] <a>kite-name</a> [<a>+flags</a>]
""")
MAN_DESCRIPTION = ("""\
    PageKite is a system for exposing <tt>localhost</tt> servers to the
    public Internet.  It is most commonly used to make local web servers or
    SSH servers publicly visible, although almost any TCP-based protocol can
    work if the client knows how to use an HTTP proxy.

    PageKite uses a combination of tunnels and reverse proxies to compensate
    for the fact that <tt>localhost</tt> usually does not have a public IP
    address and is often subject to adverse network conditions, including
    aggressive firewalls and multiple layers of NAT.

    This program implements both ends of the tunnel: the local "back-end"
    and the remote "front-end" reverse-proxy relay.  For convenience,
    <b>pagekite.py</b> also includes a basic HTTP server for quickly exposing
    files and directories to the World Wide Web for casual sharing and
    collaboration.
""")
MAN_EXAMPLES = ("""\
    <pre>Basic usage, gives <tt>http://localhost:80/</tt> a public name:
    $ pagekite.py NAME.pagekite.me

    To expose specific folders, files or use alternate local ports:
    $ pagekite.py /a/path/ NAME.pagekite.me +indexes  # built-in HTTPD
    $ pagekite.py *.html   NAME.pagekite.me           # built-in HTTPD
    $ pagekite.py 3000     NAME.pagekite.me           # HTTPD on 3000

    To expose multiple local servers (SSH and HTTP):
    $ pagekite.py ssh://NAME.pagekite.me AND 3000 NAME.pagekite.me</pre>
""")
MAN_KITES = ("""\
    The most comman usage of <b>pagekite.py</b> is as a back-end, where it
    is used to expose local services to the outside world.

    Examples of services are: a local HTTP server, a local SSH server,
    a folder or a file.

    A service is exposed by describing it on the command line, along with the
    desired public kite name. If a kite name is requested which does not already
    exist in the configuration file and program is run interactively, the user
    will be prompted and given the option of signing up and/or creating a new
    kite using the <b>pagekite.net</b> service.

    Multiple services and kites can be specified on a single command-line,
    separated by the word 'AND' (note capital letters are required).
    This may cause problems if you have many files and folders by that
    name, but that should be relatively rare. :-)
""")
MAN_KITE_EXAMPLES = ("""\
    The options <b>--list</b>, <b>--add</b>, <b>--disable</b> and \
<b>--remove</b> can be used to
    manipulate the kites and service definitions in your configuration file,
    if you prefer not to edit it by hand.  Examples:

    <pre>Adding new kites
    $ pagekite.py --add /a/path/ NAME.pagekite.me +indexes
    $ pagekite.py --add 80 OTHER-NAME.pagekite.me

    To display the current configuration
    $ pagekite.py --list

    Disable or delete kites (--add re-enables)
    $ pagekite.py --disable OTHER-NAME.pagekite.me
    $ pagekite.py --remove NAME.pagekite.me</pre>
""")
MAN_FLAGS = ("""\
    Flags are used to tune the behavior of a particular kite, for example
    by enabling access controls or specific features of the built-in HTTP
    server.
""")
MAN_FLAGS_COMMON = ("""\
    +ip</b>/<a>1.2.3.4</a>     __Enable connections only from this IP address.
    +ip</b>/<a>1.2.3</a>       __Enable connections only from this /24 netblock.
""")
MAN_FLAGS_HTTP = ("""\
    +password</b>/<a>name</a>=<a>pass</a>
            Require a username and password (HTTP Basic Authentication)

    +rewritehost</b>    __Rewrite the incoming Host: header.
    +rewritehost</b>=<a>N</a>  __Replace Host: header value with N.
    +rawheaders</b>     __Do not rewrite (or add) any HTTP headers at all.
    +insecure</b>       __Allow access to phpMyAdmin, /admin, etc. (per kite).
""")
MAN_FLAGS_BUILTIN = ("""\
    +indexes        __Enable directory indexes.
    +indexes</b>=<a>all</a>    __Enable directory indexes including hidden (dot-) files.
    +hide           __Obfuscate URLs of shared files.

    +cgi</b>=<a>list</a>
            A list of extensions, for which files should be treated as
            CGI scripts (example: <tt>+cgi=cgi,pl,sh</tt>).
""")
MAN_OPTIONS = ("""\
    The full power of <b>pagekite.py</b> lies in the numerous options which
    can be specified on the command line or in a configuration file (see below).

    Note that many options, especially the service and domain definitions,
    are additive and if given multiple options the program will attempt to
    obey them all.  Options are processed in order and if they are not
    additive then the last option will override all preceding ones.

    Although <b>pagekite.py</b> accepts a great many options, most of the
    time the program defaults will Just Work.
""")
MAN_OPT_COMMON = ("""\
    --clean         __Skip loading the default configuration file.
    --signup        __Interactively sign up for pagekite.net service.
    --defaults      __Set defaults for use with pagekite.net service.
    --nocrashreport __Don't send anonymous crash reports to pagekite.net.
""")
MAN_OPT_BACKEND = ("""\
    --shell         __Run PageKite in an interactive shell.
    --nullui        __Silent UI for scripting. Assumes Yes on all questions.

    --list          __List all configured kites.
    --add           __Add (or enable) the following kites, save config.
    --remove        __Remove the following kites, save config.
    --disable       __Disable the following kites, save config.
    --only          __Disable all but the following kites, save config.

    --insecure      __Allow access to phpMyAdmin, /admin, etc. (global).

    --local</b>=<a>ports</a>   __Configure for local serving only (no remote front-end).
    --watch</b>=<a>N</a>       __Display proxied data (higher N = more verbosity).

    --noproxy       __Ignore system (or config file) proxy settings.

    --proxy</b>=<a>type</a>:<a>server</a>:<a>port</a>,\
 <b>--socksify</b>=<a>server</a>:<a>port</a>,\
 <b>--torify</b>=<a>server</a>:<a>port</a> __
            Connect to the front-ends using SSL, an HTTP proxy, a SOCKS proxy,
            or the Tor anonymity network.  The type can be any of 'ssl', 'http'
            or 'socks5'.  The server name can either be a plain hostname,
            user@hostname or user:password@hostname.  For SSL connections the
            user part may be a path to a client cert PEM file.  If multiple
            proxies are defined, they will be chained one after another.

    --service_on</b>=<a>proto</a>:<a>kitename</a>:<a>host</a>:<a>port</a>:<a>secret</a> __
            Explicit configuration for a service kite.  Generally kites are
            created on the command-line using the service short-hand
            described above, but this syntax is used in the config file.

    --service_off</b>=<a>proto</a>:<a>kitename</a>:<a>host</a>:<a>port</a>:<a>secret</a> __
            Same as --service, except disabled by default.

    --service_cfg</b>=<a>...</a>, <b>--webpath</b>=<a>...</a> __
            These options are used in the configuration file to store service
            and flag settings (see above). These are both likely to change in
            the near future, so please just pretend you didn't notice them.

    --frontend</b>=<a>host</a>:<a>port</a> __
            Connect to the named front-end server. If this option is repeated,
            multiple connections will be made.

    --frontends</b>=<a>num</a>:<a>dns-name</a>:<a>port</a> __
            Choose <a>num</a> front-ends from the A records of a DNS domain
            name, using the given port number. Default behavior is to probe
            all addresses and use the fastest one.

    --nofrontend</b>=<a>ip</a>:<a>port</a> __
            Never connect to the named front-end server. This can be used to
            exclude some front-ends from auto-configuration.

    --fe_certname</b>=<a>domain</a> __
            Connect using SSL, accepting valid certs for this domain. If
            this option is repeated, any of the named certificates will be
            accepted, but the first will be preferred.

    --ca_certs</b>=<a>/path/to/file</a> __
            Path to your trusted root SSL certificates file.

    --dyndns</b>=<a>X</a> __
            Register changes with DynDNS provider X.  X can either be simply
            the name of one of the 'built-in' providers, or a URL format
            string for ad-hoc updating.

    --all           __Terminate early if any tunnels fail to register.
    --new           __Don't attempt to connect to any kites' old front-ends.
    --fingerpath</b>=<a>P</a>  __Path recipe for the httpfinger back-end proxy.
    --noprobes      __Reject all probes for service state.
""")
MAN_OPT_FRONTEND = ("""\
    --isfrontend    __Enable front-end operation.

    --domain</b>=<a>proto,proto2,pN</a>:<a>domain</a>:<a>secret</a> __
            Accept tunneling requests for the named protocols and specified
            domain, using the given secret.  A * may be used as a wildcard for
            subdomains or protocols.

    --authdomain</b>=<a>auth-domain</a>,\
 <b>--authdomain</b>=<a>target-domain</a>:<a>auth-domain</a> __
            Use <a>auth-domain</a> as a remote authentication server for the
            DNS-based authetication protocol.  If no <i>target-domain</i>
            is given, use this as the default authentication method.

    --motd</b>=<a>/path/to/motd</a> __
            Send the contents of this file to new back-ends as a
            "message of the day".

    --host</b>=<a>hostname</a> __Listen on the given hostname only.
    --ports</b>=<a>list</a>    __Listen on a comma-separated list of ports.
    --portalias</b>=<a>A:B</a> __Report port A as port B to backends.
    --protos</b>=<a>list</a>   __Accept the listed protocols for tunneling.

    --rawports</b>=<a>list</a> __
            Listen for raw connections these ports. The string '%s'
            allows arbitrary ports in HTTP CONNECT.

    --accept_acl_file</b>=<a>/path/to/file</a> __
            Consult an external access control file before accepting an
            incoming connection. Quick'n'dirty for mitigating abuse. The
            format is one rule per line: `rule policy comment` where a
            rule is an IP or regexp and policy is 'allow' or 'deny'.

    --client_acl</b>=<a>policy</a>:<a>regexp</a>,\
 <b>--tunnel_acl</b>=<a>policy</a>:<a>regexp</a> __
            Add a client connection or tunnel access control rule.
            Policies should be 'allow' or 'deny', the regular expression
            should be written to match IPv4 or IPv6 addresses.  If defined,
            access rules are checkd in order and if none matches, incoming
            connections will be rejected.

    --tls_default</b>=<a>name</a> __
            Default name to use for SSL, if SNI (Server Name Indication)
            is missing from incoming HTTPS connections.

    --tls_endpoint</b>=<a>name</a>:<a>/path/to/file</a> __
            Terminate SSL/TLS for a name using key/cert from a file.
""")
MAN_OPT_SYSTEM = ("""\
    --optfile</b>=<a>/path/to/file</a> __
            Read settings from file X. Default is <tt>~/.pagekite.rc</tt>.

    --optdir</b>=<a>/path/to/directory</a> __
            Read settings from <tt>/path/to/directory/*.rc</tt>, in
            lexicographical order.

    --savefile</b>=<a>/path/to/file</a> __
            Saved settings will be written to this file.

    --save          __Save the current configuration to the savefile.

    --settings</b> __
            Dump the current settings to STDOUT, formatted as a configuration
            file would be.

    --nozchunks    __Disable zlib tunnel compression.
    --sslzlib      __Enable zlib compression in OpenSSL.
    --buffers</b>=<a>N</a>    __Buffer at most N kB of data before blocking.
    --logfile</b>=<a>F</a>    __Log to file F.
    --daemonize    __Run as a daemon.
    --runas</b>=<a>U</a>:<a>G</a>    __Set UID:GID after opening our listening sockets.
    --pidfile</b>=<a>P</a>    __Write PID to the named file.
    --errorurl</b>=<a>U</a>   __URL to redirect to when back-ends are not found.

    --selfsign __
            Configure the built-in HTTP daemon for HTTPS, first generating a
            new self-signed certificate using <b>openssl</b> if necessary.

    --httpd</b>=<a>X</a>:<a>P</a>,\
 <b>--httppass</b>=<a>X</a>,\
 <b>--pemfile</b>=<a>X</a> __
            Configure the built-in HTTP daemon.  These options are likely to
            change in the near future, please pretend you didn't see them.
""")
MAN_CONFIG_FILES = ("""\
    If you are using <b>pagekite.py</b> as a command-line utility, it will
    load its configuration from a file in your home directory.  The file is
    named <tt>.pagekite.rc</tt> on Unix systems (including Mac OS X), or
    <tt>pagekite.cfg</tt> on Windows.

    If you are using <b>pagekite.py</b> as a system-daemon which starts up
    when your computer boots, it is generally configured to load settings
    from <tt>/etc/pagekite.d/*.rc</tt> (in lexicographical order).

    In both cases, the configuration files contain one or more of the same
    options as are used on the command line, with the difference that at most
    one option may be present on each line, and the parser is more tolerant of
    white-space.  The leading '--' may also be omitted for readability and
    blank lines and lines beginning with '#' are treated as comments.

    <b>NOTE:</b> When using <b>-o</b>, <b>--optfile</b> or <b>--optdir</b> on the command line,
    it is advisable to use <b>--clean</b> to suppress the default configuration.
""")
MAN_SECURITY = ("""\
    Please keep in mind, that whenever exposing a server to the public
    Internet, it is important to think about security. Hacked webservers are
    frequently abused as part of virus, spam or phishing campaigns and in
    some cases security breaches can compromise the entire operating system.

    Some advice:<pre>
       * Switch PageKite off when not using it.
       * Use the built-in access controls and SSL encryption.
       * Leave the firewall enabled unless you have good reason not to.
       * Make sure you use good passwords everywhere.
       * Static content is very hard to hack!
       * Always, always make frequent backups of any important work.</pre>

    Note that as of version 0.5, <b>pagekite.py</b> includes a very basic
    request firewall, which attempts to prevent access to phpMyAdmin and
    other sensitive systems.  If it gets in your way, the <b>+insecure</b>
    flag or <b>--insecure</b> option can be used to turn it off.

    For more, please visit: <https://pagekite.net/support/security/>
""")
MAN_LICENSE = ("""\
    Copyright 2010-2012, the Beanstalks Project ehf. and Bjarni R. Einarsson.

    This program is free software: you can redistribute it and/or modify it
    under the terms of the GNU Affero General Public License as published by
    the Free Software Foundation, either version 3 of the License, or (at
    your option) any later version.

    This program is distributed in the hope that it will be useful, but
    WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY
    or FITNESS FOR A PARTICULAR PURPOSE. See the GNU Affero General Public
    License for more details.

    You should have received a copy of the GNU Affero General Public License
    along with this program.  If not, see: <http://www.gnu.org/licenses/>
""")
MAN_BUGS = ("""\
    Using <b>pagekite.py</b> as a front-end relay with the native Python SSL
    module may result in poor performance.  Please use the pyOpenSSL wrappers
    instead.
""")
MAN_SEE_ALSO = ("""\
    lapcat(1), <http://pagekite.org/>, <https://pagekite.net/>
""")
MAN_CREDITS = ("""\
    <pre>- Bjarni R. Einarsson <http://bre.klaki.net/>
    - The Beanstalks Project ehf. <https://pagekite.net/company/>
    - The Rannis Technology Development Fund <http://www.rannis.is/>
    - Joar Wandborg <http://wandborg.se/></pre>
""")

MANUAL_TOC = (
  ('SH', 'Name', MAN_NAME),
  ('SH', 'Synopsis', MAN_SYNOPSIS),
  ('SH', 'Description', MAN_DESCRIPTION),
  ('SH', 'Basic usage', MAN_EXAMPLES),
  ('SH', 'Services and kites', MAN_KITES),
  ('SH', 'Kite configuration', MAN_KITE_EXAMPLES),
  ('SH', 'Flags', MAN_FLAGS),
  ('SS', 'Common flags', MAN_FLAGS_COMMON),
  ('SS', 'HTTP protocol flags', MAN_FLAGS_HTTP),
  ('SS', 'Built-in HTTPD flags', MAN_FLAGS_BUILTIN),
  ('SH', 'Options', MAN_OPTIONS),
  ('SS', 'Common options', MAN_OPT_COMMON),
  ('SS', 'Back-end options', MAN_OPT_BACKEND),
  ('SS', 'Front-end options', MAN_OPT_FRONTEND),
  ('SS', 'System options', MAN_OPT_SYSTEM),
  ('SH', 'Configuration files', MAN_CONFIG_FILES),
  ('SH', 'Security', MAN_SECURITY),
  ('SH', 'Bugs', MAN_BUGS),
  ('SH', 'See Also', MAN_SEE_ALSO),
  ('SH', 'Credits', MAN_CREDITS),
  ('SH', 'Copyright and license', MAN_LICENSE),
)

HELP_SHELL = ("""\
    Press ENTER to fly your kites, CTRL+C to quit or give some arguments to
    accomplish a more specific task.
""")
HELP_KITES = ("""\
""")
HELP_TOC = (
  ('about',    'About PageKite',                        MAN_DESCRIPTION),
  ('basics',   'Basic usage examples',                  MAN_EXAMPLES),
  ('kites',    'Services and kites',                    MAN_KITES),
  ('config',   'Adding, disabling or removing kites',   MAN_KITE_EXAMPLES),
  ('flags',    'Service flags',              '\n'.join([MAN_FLAGS,
                                                        MAN_FLAGS_COMMON,
                                                        MAN_FLAGS_HTTP,
                                                        MAN_FLAGS_BUILTIN])),
  ('files',    'Where are the config files?',           MAN_CONFIG_FILES),
  ('security', 'A few words about security.',           MAN_SECURITY),
  ('credits',  'License and credits',        '\n'.join([MAN_LICENSE,
                                                        'CREDITS:',
                                                        MAN_CREDITS])),
  ('manual', 'The complete manual.  See also: http://pagekite.net/man/', None)
)


def HELP(args):
  name = title = text = ''
  if args:
    what = args[0].strip().lower()
    for name, title, text in HELP_TOC:
      if name == what:
        break
  if name == 'manual':
    text = DOC()
  elif not text:
    text = ''.join([
      'Type `help TOPIC` to to read about one of these topics:\n\n',
      ''.join(['  %-10.10s %s\n' % (n, t) for (n, t, x) in HELP_TOC]),
      '\n',
      HELP_SHELL
    ])
  return unindent(clean_text(text))


def clean_text(text):
  return re.sub('</?(tt|i)>', '`',
                re.sub('</?(a|b|pre)>', '', text.replace(' __', '   ')))

def unindent(text):
  return re.sub('(?m)^    ', '', text)


def MINIDOC():
  return ("""\
>>> Welcome to pagekite.py v%s!

%s
    To sign up with PageKite.net or get advanced instructions:
    $ pagekite.py --signup
    $ pagekite.py --help

    If you request a kite which does not exist in your configuration file,
    the program will offer to help you sign up with https://pagekite.net/
    and create it.  Pick a name, any name!\
""") % (APPVER, clean_text(MAN_EXAMPLES))


def DOC():
  doc = ''
  for h, section, text in MANUAL_TOC:
    doc += '%s\n\n%s\n' % (h == 'SH' and section.upper() or '  '+section,
                           clean_text(text))
  return doc


def MAN(pname=None):
  man = ("""\
.\\" This man page is autogenerated from the pagekite.py built-in manual.
.TH PAGEKITE "1" "%s" "https://pagekite.net/" "Awesome Commands"
.nh
.ad l
""") % ts_to_iso(time.time()).split('T')[0]
  for h, section, text in MANUAL_TOC:
    man += ('.%s %s\n\n%s\n\n'
            ) % (h, h == 'SH' and section.upper() or section,
                 re.sub('\n +', '\n', '\n'+text.strip())
                   .replace('\n--', '\n.TP\n\\fB--')
                   .replace('\n+', '\n.TP\n\\fB+')
                   .replace(' __', '\\fR\n')
                   .replace('-', '\\-')
                   .replace('<pre>', '\n.nf\n').replace('</pre>', '\n.fi\n')
                   .replace('<b>', '\\fB').replace('</b>', '\\fR')
                   .replace('<a>', '\\fI').replace('</a>', '\\fR')
                   .replace('<i>', '\\fI').replace('</i>', '\\fR')
                   .replace('<tt>', '\\fI').replace('</tt>', '\\fR')
                   .replace('\\fR\\fR\n', '\\fR'))
  if pname:
    man = man.replace('pagekite.py', pname)
  return man


def MARKDOWN(pname=None):
  mkd = ''
  for h, section, text in MANUAL_TOC:
     if h == 'SH':
       h = '##'
     else:
       h = '###'
     mkd += ('%s %s %s\n%s\n\n'
            ) % (h, section, h,
                 re.sub('(</[aib]>|`)</b>', '\\1',
                  re.sub(' +<br />([A-Z0-9])', '</b>  \n     \\1',
                   re.sub('\n        ', '\n     ',
                    re.sub('\n    ', '\n', '\n'+text.strip()))
                     .replace(' __', ' <br />')
                     .replace('\n--', '\n   * <b>--')
                     .replace('\n+', '\n   * <b>+')
                     .replace('<a>', '`').replace('</a>', '`')
                     .replace('<tt>', '`').replace('</tt>', '`'))))
  if pname:
    mkd = mkd.replace('pagekite.py', pname)
  return mkd


if __name__ == '__main__':
  import sys
  if '--nopy' in sys.argv:
    pname = 'pagekite'
  else:
    pname = None

  if '--man' in sys.argv:
    print MAN(pname)
  elif '--markdown' in sys.argv:
    print MARKDOWN(pname)
  elif '--minidoc' in sys.argv:
    print MINIDOC()
  else:
    print DOC()

########NEW FILE########
__FILENAME__ = pk
"""
This is what is left of the original monolithic pagekite.py.
This is slowly being refactored into smaller sub-modules.
"""
##############################################################################
LICENSE = """\
This file is part of pagekite.py.
Copyright 2010-2013, the Beanstalks Project ehf. and Bjarni Runar Einarsson

This program is free software: you can redistribute it and/or modify it under
the terms of the  GNU  Affero General Public License as published by the Free
Software Foundation, either version 3 of the License, or (at your option) any
later version.

This program is distributed in the hope that it will be useful,  but  WITHOUT
ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
FOR A PARTICULAR PURPOSE.  See the GNU Affero General Public License for more
details.

You should have received a copy of the GNU Affero General Public License
along with this program.  If not, see: <http://www.gnu.org/licenses/>
"""
##############################################################################
import base64
import cgi
from cgi import escape as escape_html
import errno
import getopt
import httplib
import os
import random
import re
import select
import socket
import struct
import sys
import tempfile
import threading
import time
import traceback
import urllib
import xmlrpclib
import zlib

import SocketServer
from CGIHTTPServer import CGIHTTPRequestHandler
from SimpleXMLRPCServer import SimpleXMLRPCServer, SimpleXMLRPCRequestHandler
import Cookie

from compat import *
from common import *
import compat
import logging


OPT_FLAGS = 'o:O:S:H:P:X:L:ZI:fA:R:h:p:aD:U:NE:'
OPT_ARGS = ['noloop', 'clean', 'nopyopenssl', 'nossl', 'nocrashreport',
            'nullui', 'remoteui', 'uiport=', 'help', 'settings',
            'optfile=', 'optdir=', 'savefile=',
            'friendly', 'shell',
            'signup', 'list', 'add', 'only', 'disable', 'remove', 'save',
            'service_xmlrpc=', 'controlpanel', 'controlpass',
            'httpd=', 'pemfile=', 'httppass=', 'errorurl=', 'webpath=',
            'logfile=', 'daemonize', 'nodaemonize', 'runas=', 'pidfile=',
            'isfrontend', 'noisfrontend', 'settings',
            'defaults', 'local=', 'domain=',
            'authdomain=', 'motd=', 'register=', 'host=',
            'noupgradeinfo', 'upgradeinfo=',
            'ports=', 'protos=', 'portalias=', 'rawports=',
            'tls_default=', 'tls_endpoint=', 'selfsign',
            'fe_certname=', 'jakenoia', 'ca_certs=',
            'kitename=', 'kitesecret=', 'fingerpath=',
            'backend=', 'define_backend=', 'be_config=', 'insecure',
            'service_on=', 'service_off=', 'service_cfg=',
            'tunnel_acl=', 'client_acl=', 'accept_acl_file=',
            'frontend=', 'nofrontend=', 'frontends=',
            'torify=', 'socksify=', 'proxy=', 'noproxy',
            'new', 'all', 'noall', 'dyndns=', 'nozchunks', 'sslzlib',
            'buffers=', 'noprobes', 'debugio', 'watch=',
            # DEPRECATED:
            'reloadfile=', 'autosave', 'noautosave', 'webroot=',
            'webaccess=', 'webindexes=', 'delete_backend=']


# Enable system proxies
# This will all fail if we don't have PySocksipyChain available.
# FIXME: Move this code somewhere else?
socks.usesystemdefaults()
socks.wrapmodule(sys.modules[__name__])

if socks.HAVE_SSL:
  # Secure connections to pagekite.net in SSL tunnels.
  def_hop = socks.parseproxy('default')
  https_hop = socks.parseproxy(('httpcs!%s!443'
                                ) % ','.join(['pagekite.net']+SERVICE_CERTS))
  for dest in ('pagekite.net', 'up.pagekite.net', 'up.b5p.us'):
    socks.setproxy(dest, *def_hop)
    socks.addproxy(dest, *socks.parseproxy('http!%s!443' % dest))
    socks.addproxy(dest, *https_hop)
else:
  # FIXME: Should scream and shout about lack of security.
  pass


##[ PageKite.py code starts here! ]############################################

from proto.proto import *
from proto.parsers import *
from proto.selectables import *
from proto.filters import *
from proto.conns import *
from ui.nullui import NullUi


# FIXME: This could easily be a pool of threads to let us handle more
#        than one incoming request at a time.
class AuthThread(threading.Thread):
  """Handle authentication work in a separate thread."""

  #daemon = True

  def __init__(self, conns):
    threading.Thread.__init__(self)
    self.qc = threading.Condition()
    self.jobs = []
    self.conns = conns

  def check(self, requests, conn, callback):
    self.qc.acquire()
    self.jobs.append((requests, conn, callback))
    self.qc.notify()
    self.qc.release()

  def quit(self):
    self.qc.acquire()
    self.keep_running = False
    self.qc.notify()
    self.qc.release()
    try:
      self.join()
    except RuntimeError:
      pass

  def run(self):
    self.keep_running = True
    while self.keep_running:
      try:
        self._run()
      except Exception, e:
        logging.LogError('AuthThread died: %s' % e)
        time.sleep(5)
    logging.LogDebug('AuthThread: done')

  def _run(self):
    self.qc.acquire()
    while self.keep_running:
      now = int(time.time())
      if not self.jobs:
        (requests, conn, callback) = None, None, None
        self.qc.wait()
      else:
        (requests, conn, callback) = self.jobs.pop(0)
        if logging.DEBUG_IO: print '=== AUTH REQUESTS\n%s\n===' % requests
        self.qc.release()

        quotas = []
        q_conns = []
        q_days = []
        results = []
        log_info = []
        session = '%x:%s:' % (now, globalSecret())
        for request in requests:
          try:
            proto, domain, srand, token, sign, prefix = request
          except:
            logging.LogError('Invalid request: %s' % (request, ))
            continue

          what = '%s:%s:%s' % (proto, domain, srand)
          session += what
          if not token or not sign:
            # Send a challenge. Our challenges are time-stamped, so we can
            # put stict bounds on possible replay attacks (20 minutes atm).
            results.append(('%s-SignThis' % prefix,
                            '%s:%s' % (what, signToken(payload=what,
                                                       timestamp=now))))
          else:
            # This is a bit lame, but we only check the token if the quota
            # for this connection has never been verified.
            (quota, days, conns, reason
             ) = self.conns.config.GetDomainQuota(proto, domain, srand, token,
                                         sign, check_token=(conn.quota is None))
            duplicates = self.conns.Tunnel(proto, domain)
            if not quota:
              if not reason: reason = 'quota'
              results.append(('%s-Invalid' % prefix, what))
              results.append(('%s-Invalid-Why' % prefix,
                              '%s;%s' % (what, reason)))
              log_info.extend([('rejected', domain),
                               ('quota', quota),
                               ('reason', reason)])
            elif duplicates:
              # Duplicates... is the old one dead?  Trigger a ping.
              for conn in duplicates:
                conn.TriggerPing()
              results.append(('%s-Duplicate' % prefix, what))
              log_info.extend([('rejected', domain),
                               ('duplicate', 'yes')])
            else:
              results.append(('%s-OK' % prefix, what))
              quotas.append((quota, request))
              if conns: q_conns.append(conns)
              if days: q_days.append(days)
              if (proto.startswith('http') and
                  self.conns.config.GetTlsEndpointCtx(domain)):
                results.append(('%s-SSL-OK' % prefix, what))

        results.append(('%s-SessionID' % prefix,
                        '%x:%s' % (now, sha1hex(session))))
        results.append(('%s-Misc' % prefix, urllib.urlencode({
                          'motd': (self.conns.config.motd_message or ''),
                        })))
        for upgrade in self.conns.config.upgrade_info:
          results.append(('%s-Upgrade' % prefix, ';'.join(upgrade)))

        if quotas:
          min_qconns = min(q_conns or [0])
          if q_conns and min_qconns:
            results.append(('%s-QConns' % prefix, min_qconns))

          min_qdays = min(q_days or [0])
          if q_days and min_qdays:
            results.append(('%s-QDays' % prefix, min_qdays))

          nz_quotas = [qp for qp in quotas if qp[0] and qp[0] > 0]
          if nz_quotas:
            quota = min(nz_quotas)[0]
            conn.quota = [quota, [qp[1] for qp in nz_quotas], time.time()]
            results.append(('%s-Quota' % prefix, quota))
          elif requests:
            if not conn.quota:
              conn.quota = [None, requests, time.time()]
            else:
              conn.quota[2] = time.time()

        if logging.DEBUG_IO: print '=== AUTH RESULTS\n%s\n===' % results
        callback(results, log_info)
        self.qc.acquire()

    self.buffering = 0
    self.qc.release()


##[ Selectables ]##############################################################

class Connections(object):
  """A container for connections (Selectables), config and tunnel info."""

  def __init__(self, config):
    self.config = config
    self.ip_tracker = {}
    self.idle = []
    self.conns = []
    self.conns_by_id = {}
    self.tunnels = {}
    self.auth = None

  def start(self, auth_thread=None):
    self.auth = auth_thread or AuthThread(self)
    self.auth.start()

  def Add(self, conn):
    self.conns.append(conn)

  def SetAltId(self, conn, new_id):
    if conn.alt_id and conn.alt_id in self.conns_by_id:
      del self.conns_by_id[conn.alt_id]
    if new_id:
      self.conns_by_id[new_id] = conn
    conn.alt_id = new_id

  def SetIdle(self, conn, seconds):
    self.idle.append((time.time() + seconds, conn.last_activity, conn))

  def TrackIP(self, ip, domain):
    tick = '%d' % (time.time()/12)
    if tick not in self.ip_tracker:
      deadline = int(tick)-10
      for ot in self.ip_tracker.keys():
        if int(ot) < deadline:
          del self.ip_tracker[ot]
      self.ip_tracker[tick] = {}

    if ip not in self.ip_tracker[tick]:
      self.ip_tracker[tick][ip] = [1, domain]
    else:
      self.ip_tracker[tick][ip][0] += 1
      self.ip_tracker[tick][ip][1] = domain

  def LastIpDomain(self, ip):
    domain = None
    for tick in sorted(self.ip_tracker.keys()):
      if ip in self.ip_tracker[tick]:
        domain = self.ip_tracker[tick][ip][1]
    return domain

  def Remove(self, conn, retry=True):
    try:
      if conn.alt_id and conn.alt_id in self.conns_by_id:
        del self.conns_by_id[conn.alt_id]
      if conn in self.conns:
        self.conns.remove(conn)
      rmp = []
      for elc in self.idle:
        if elc[-1] == conn:
          rmp.append(elc)
      for elc in rmp:
        self.idle.remove(elc)
      for tid, tunnels in self.tunnels.items():
        if conn in tunnels:
          tunnels.remove(conn)
          if not tunnels:
            del self.tunnels[tid]
    except (ValueError, KeyError):
      # Let's not asplode if another thread races us for this.
      logging.LogError('Failed to remove %s: %s' % (conn, format_exc()))
      if retry:
        return self.Remove(conn, retry=False)

  def IdleConns(self):
    return [p[-1] for p in self.idle]

  def Sockets(self):
    return [s.fd for s in self.conns]

  def Readable(self):
    # FIXME: This is O(n)
    now = time.time()
    return [s.fd for s in self.conns if s.IsReadable(now)]

  def Blocked(self):
    # FIXME: This is O(n)
    # Magic side-effect: update buffered byte counter
    blocked = [s for s in self.conns if s.IsBlocked()]
    common.buffered_bytes[0] = sum([len(s.write_blocked) for s in blocked])
    return [s.fd for s in blocked]

  def DeadConns(self):
    return [s for s in self.conns if s.IsDead()]

  def CleanFds(self):
    evil = []
    for s in self.conns:
      try:
        i, o, e = select.select([s.fd], [s.fd], [s.fd], 0)
      except:
        evil.append(s)
    for s in evil:
      logging.LogDebug('Removing broken Selectable: %s' % s)
      s.Cleanup()
      self.Remove(s)

  def Connection(self, fd):
    for conn in self.conns:
      if conn.fd == fd:
        return conn
    return None

  def TunnelServers(self):
    servers = {}
    for tid in self.tunnels:
      for tunnel in self.tunnels[tid]:
        server = tunnel.server_info[tunnel.S_NAME]
        if server is not None:
          servers[server] = 1
    return servers.keys()

  def CloseTunnel(self, proto, domain, conn):
    tid = '%s:%s' % (proto, domain)
    if tid in self.tunnels:
      if conn in self.tunnels[tid]:
        self.tunnels[tid].remove(conn)
      if not self.tunnels[tid]:
        del self.tunnels[tid]

  def CheckIdleConns(self, now):
    active = []
    for elc in self.idle:
      expire, last_activity, conn = elc
      if conn.last_activity > last_activity:
        active.append(elc)
      elif expire < now:
        logging.LogDebug('Killing idle connection: %s' % conn)
        conn.Die(discard_buffer=True)
      elif conn.created < now - 1:
        conn.SayHello()
    for pair in active:
      self.idle.remove(pair)

  def Tunnel(self, proto, domain, conn=None):
    tid = '%s:%s' % (proto, domain)
    if conn is not None:
      if tid not in self.tunnels:
        self.tunnels[tid] = []
      self.tunnels[tid].append(conn)

    if tid in self.tunnels:
      return self.tunnels[tid]
    else:
      try:
        dparts = domain.split('.')[1:]
        while len(dparts) > 1:
          wild_tid = '%s:*.%s' % (proto, '.'.join(dparts))
          if wild_tid in self.tunnels:
            return self.tunnels[wild_tid]
          dparts = dparts[1:]
      except:
        pass

      return []


class HttpUiThread(threading.Thread):
  """Handle HTTP UI in a separate thread."""

  daemon = True

  def __init__(self, pkite, conns,
               server=None, handler=None, ssl_pem_filename=None):
    threading.Thread.__init__(self)
    if not (server and handler):
      self.serve = False
      self.httpd = None
      return

    self.ui_sspec = pkite.ui_sspec
    self.httpd = server(self.ui_sspec, pkite, conns,
                        handler=handler,
                        ssl_pem_filename=ssl_pem_filename)
    self.httpd.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    self.ui_sspec = pkite.ui_sspec = (self.ui_sspec[0],
                                      self.httpd.socket.getsockname()[1])
    self.serve = True

  def quit(self):
    self.serve = False
    try:
      knock = rawsocket(socket.AF_INET, socket.SOCK_STREAM)
      knock.connect(self.ui_sspec)
      knock.close()
    except IOError:
      pass
    try:
      self.join()
    except RuntimeError:
      try:
        if self.httpd and self.httpd.socket:
          self.httpd.socket.close()
      except IOError:
        pass

  def run(self):
    while self.serve:
      try:
        self.httpd.handle_request()
      except KeyboardInterrupt:
        self.serve = False
      except Exception, e:
        logging.LogInfo('HTTP UI caught exception: %s' % e)
    if self.httpd: self.httpd.socket.close()
    logging.LogDebug('HttpUiThread: done')


class UiCommunicator(threading.Thread):
  """Listen for interactive commands."""

  def __init__(self, config, conns):
    threading.Thread.__init__(self)
    self.looping = False
    self.config = config
    self.conns = conns
    logging.LogDebug('UiComm: Created')

  def run(self):
    self.looping = True
    while self.looping:
      if not self.config or not self.config.ui.ALLOWS_INPUT:
        time.sleep(1)
        continue

      line = ''
      try:
        i, o, e = select.select([self.config.ui.rfile], [], [], 1)
        if not i: continue
      except:
        pass

      if self.config:
        line = self.config.ui.rfile.readline().strip()
        if line:
          self.Parse(line)

    logging.LogDebug('UiCommunicator: done')

  def Reconnect(self):
    if self.config.tunnel_manager:
      self.config.ui.Status('reconfig')
      self.config.tunnel_manager.CloseTunnels()
      self.config.tunnel_manager.HurryUp()

  def Parse(self, line):
    try:
      command, args = line.split(': ', 1)
      logging.LogDebug('UiComm: %s(%s)' % (command, args))

      if args.lower() == 'none': args = None
      elif args.lower() == 'true': args = True
      elif args.lower() == 'false': args = False

      if command == 'exit':
        self.config.keep_looping = False
        self.config.main_loop = False
      elif command == 'restart':
        self.config.keep_looping = False
        self.config.main_loop = True
      elif command == 'config':
        command = 'change settings'
        self.config.Configure(['--%s' % args])
      elif command == 'enablekite':
        command = 'enable kite'
        if args and args in self.config.backends:
          self.config.backends[args][BE_STATUS] = BE_STATUS_UNKNOWN
          self.Reconnect()
        else:
          raise Exception('No such kite: %s' % args)
      elif command == 'disablekite':
        command = 'disable kite'
        if args and args in self.config.backends:
          self.config.backends[args][BE_STATUS] = BE_STATUS_DISABLED
          self.Reconnect()
        else:
          raise Exception('No such kite: %s' % args)
      elif command == 'delkite':
        command = 'remove kite'
        if args and args in self.config.backends:
          del self.config.backends[args]
          self.Reconnect()
        else:
          raise Exception('No such kite: %s' % args)
      elif command == 'addkite':
        command = 'create new kite'
        args = (args or '').strip().split() or ['']
        if self.config.RegisterNewKite(kitename=args[0],
                                       autoconfigure=True, ask_be=True):
          self.Reconnect()
      elif command == 'save':
        command = 'save configuration'
        self.config.SaveUserConfig(quiet=(args == 'quietly'))

    except ValueError:
      logging.LogDebug('UiComm: bogus: %s' % line)
    except SystemExit:
      self.config.keep_looping = False
      self.config.main_loop = False
    except:
      logging.LogDebug('UiComm: failed %s' % (sys.exc_info(), ))
      self.config.ui.Tell(['Oops!', '', 'Failed to %s, details:' % command,
                           '', '%s' % (sys.exc_info(), )], error=True)

  def quit(self):
    self.looping = False
    self.conns = None
    try:
      self.join()
    except RuntimeError:
      pass


class TunnelManager(threading.Thread):
  """Create new tunnels as necessary or kill idle ones."""

  daemon = True

  def __init__(self, pkite, conns):
    threading.Thread.__init__(self)
    self.pkite = pkite
    self.conns = conns

  def CheckTunnelQuotas(self, now):
    for tid in self.conns.tunnels:
      for tunnel in self.conns.tunnels[tid]:
        tunnel.RecheckQuota(self.conns, when=now)

  def PingTunnels(self, now):
    dead = {}
    for tid in self.conns.tunnels:
      for tunnel in self.conns.tunnels[tid]:
        pings = PING_INTERVAL
        if tunnel.server_info[tunnel.S_IS_MOBILE]:
          pings = PING_INTERVAL_MOBILE
        grace = max(PING_GRACE_DEFAULT,
                    len(tunnel.write_blocked)/(tunnel.write_speed or 0.001))
        if tunnel.last_activity == 0:
          pass
        elif tunnel.last_ping < now - PING_GRACE_MIN:
          if tunnel.last_activity < tunnel.last_ping-(PING_GRACE_MIN+grace):
            dead['%s' % tunnel] = tunnel
          elif tunnel.last_activity < now-pings:
            tunnel.SendPing()
          elif random.randint(0, 10*pings) == 0:
            tunnel.SendPing()

    for tunnel in dead.values():
      logging.Log([('dead', tunnel.server_info[tunnel.S_NAME])])
      tunnel.Die(discard_buffer=True)

  def CloseTunnels(self):
    close = []
    for tid in self.conns.tunnels:
      for tunnel in self.conns.tunnels[tid]:
        close.append(tunnel)
    for tunnel in close:
      logging.Log([('closing', tunnel.server_info[tunnel.S_NAME])])
      tunnel.Die(discard_buffer=True)

  def quit(self):
    self.keep_running = False
    try:
      self.join()
    except RuntimeError:
      pass

  def run(self):
    self.keep_running = True
    self.explained = False
    while self.keep_running:
      try:
        self._run()
      except Exception, e:
        logging.LogError('TunnelManager died: %s' % e)
        if logging.DEBUG_IO:
          traceback.print_exc(file=sys.stderr)
        time.sleep(5)
    logging.LogDebug('TunnelManager: done')

  def DoFrontendWork(self):
    self.CheckTunnelQuotas(time.time())
    self.pkite.LoadMOTD()

    # FIXME: Front-ends should close dead back-end tunnels.
    for tid in self.conns.tunnels:
      proto, domain = tid.split(':')
      if '-' in proto:
        proto, port = proto.split('-')
      else:
        port = ''
      self.pkite.ui.NotifyFlyingFE(proto, port, domain)

  def ListBackEnds(self):
    self.pkite.ui.StartListingBackEnds()

    for bid in self.pkite.backends:
      be = self.pkite.backends[bid]
      # Do we have auto-SSL at the front-end?
      protoport, domain = bid.split(':', 1)
      tunnels = self.conns.Tunnel(protoport, domain)
      if be[BE_PROTO] in ('http', 'http2', 'http3') and tunnels:
        has_ssl = True
        for t in tunnels:
          if (protoport, domain) not in t.remote_ssl:
            has_ssl = False
      else:
        has_ssl = False

      # Get list of webpaths...
      domainp = '%s/%s' % (domain, be[BE_PORT] or '80')
      if (self.pkite.ui_sspec and
          be[BE_BHOST] == self.pkite.ui_sspec[0] and
          be[BE_BPORT] == self.pkite.ui_sspec[1]):
        builtin = True
        dpaths = self.pkite.ui_paths.get(domainp, {})
      else:
        builtin = False
        dpaths = {}

      self.pkite.ui.NotifyBE(bid, be, has_ssl, dpaths,
                             is_builtin=builtin,
                         fingerprint=(builtin and self.pkite.ui_pemfingerprint))

    self.pkite.ui.EndListingBackEnds()

  def UpdateUiStatus(self, problem, connecting):
    tunnel_count = len(self.pkite.conns and
                       self.pkite.conns.TunnelServers() or [])
    tunnel_total = len(self.pkite.servers)
    if tunnel_count == 0:
      if self.pkite.isfrontend:
        self.pkite.ui.Status('idle', message='Waiting for back-ends.')
      elif tunnel_total == 0:
        self.pkite.ui.Notify('It looks like your Internet connection might be '
                             'down! Will retry soon.')
        self.pkite.ui.Status('down', color=self.pkite.ui.GREY,
                       message='No kites ready to fly.  Waiting...')
      elif connecting == 0:
        self.pkite.ui.Status('down', color=self.pkite.ui.RED,
                       message='Not connected to any front-ends, will retry...')
    elif tunnel_count < tunnel_total:
      self.pkite.ui.Status('flying', color=self.pkite.ui.YELLOW,
                    message=('Only connected to %d/%d front-ends, will retry...'
                             ) % (tunnel_count, tunnel_total))
    elif problem:
      self.pkite.ui.Status('flying', color=self.pkite.ui.YELLOW,
                     message='DynDNS updates may be incomplete, will retry...')
    else:
      self.pkite.ui.Status('flying', color=self.pkite.ui.GREEN,
                                   message='Kites are flying and all is well.')

  def _run(self):
    self.check_interval = 5
    while self.keep_running:

      # Reconnect if necessary, randomized exponential fallback.
      problem, connecting = self.pkite.CreateTunnels(self.conns)
      if problem or connecting:
        self.check_interval = min(60, self.check_interval +
                                     int(1+random.random()*self.check_interval))
        time.sleep(1)
      else:
        self.check_interval = 5

      # Make sure tunnels are really alive.
      if self.pkite.isfrontend:
        self.DoFrontendWork()
      self.PingTunnels(time.time())

      # FIXME: This is constant noise, instead there should be a
      #        command which requests this stuff.
      self.ListBackEnds()
      self.UpdateUiStatus(problem, connecting)

      for i in xrange(0, self.check_interval):
        if self.keep_running:
          time.sleep(1)
          if i > self.check_interval:
            break
          if self.pkite.isfrontend:
            self.conns.CheckIdleConns(time.time())

  def HurryUp(self):
    self.check_interval = 0


def SecureCreate(path):
  fd = open(path, 'w')
  try:
    os.chmod(path, 0600)
  except OSError:
    pass
  return fd

def CreateSelfSignedCert(pem_path, ui):
  ui.Notify('Creating a 2048-bit self-signed TLS certificate ...',
            prefix='-', color=ui.YELLOW)

  workdir = tempfile.mkdtemp()
  def w(fn):
    return os.path.join(workdir, fn)

  os.system(('openssl genrsa -out %s 2048') % w('key'))
  os.system(('openssl req -batch -new -key %s -out %s'
                        ' -subj "/CN=PageKite/O=Self-Hosted/OU=Website"'
             ) % (w('key'), w('csr')))
  os.system(('openssl x509 -req -days 3650 -in %s -signkey %s -out %s'
             ) % (w('csr'), w('key'), w('crt')))

  pem = SecureCreate(pem_path)
  pem.write(open(w('key')).read())
  pem.write('\n')
  pem.write(open(w('crt')).read())
  pem.close()

  for fn in ['key', 'csr', 'crt']:
    os.remove(w(fn))
  os.rmdir(workdir)

  ui.Notify('Saved certificate to: %s' % pem_path,
            prefix='-', color=ui.YELLOW)


class PageKite(object):
  """Configuration and master select loop."""

  def __init__(self, ui=None, http_handler=None, http_server=None):
    self.progname = ((sys.argv[0] or 'pagekite.py').split('/')[-1]
                                                   .split('\\')[-1])
    self.ui = ui or NullUi()
    self.ui_request_handler = http_handler
    self.ui_http_server = http_server
    self.ResetConfiguration()

  def ResetConfiguration(self):
    self.isfrontend = False
    self.upgrade_info = []
    self.auth_domain = None
    self.auth_domains = {}
    self.motd = None
    self.motd_message = None
    self.server_host = ''
    self.server_ports = [80]
    self.server_raw_ports = []
    self.server_portalias = {}
    self.server_aliasport = {}
    self.server_protos = ['http', 'http2', 'http3', 'https', 'websocket',
                          'irc', 'finger', 'httpfinger', 'raw', 'minecraft']

    self.accept_acl_file = None
    self.tunnel_acls = []
    self.client_acls = []

    self.tls_default = None
    self.tls_endpoints = {}
    self.fe_certname = []
    self.fe_anon_tls_wrap = False

    self.service_provider = SERVICE_PROVIDER
    self.service_xmlrpc = SERVICE_XMLRPC

    self.daemonize = False
    self.pidfile = None
    self.logfile = None
    self.setuid = None
    self.setgid = None
    self.ui_httpd = None
    self.ui_sspec_cfg = None
    self.ui_sspec = None
    self.ui_socket = None
    self.ui_password = None
    self.ui_pemfile = None
    self.ui_pemfingerprint = None
    self.ui_magic_file = '.pagekite.magic'
    self.ui_paths = {}
    self.insecure = False
    self.be_config = {}
    self.disable_zchunks = False
    self.enable_sslzlib = False
    self.buffer_max = DEFAULT_BUFFER_MAX
    self.error_url = None
    self.finger_path = '/~%s/.finger'

    self.tunnel_manager = None
    self.client_mode = 0

    self.proxy_servers = []
    self.no_proxy = False
    self.require_all = False
    self.no_probes = False
    self.servers = []
    self.servers_manual = []
    self.servers_never = []
    self.servers_auto = None
    self.servers_new_only = False
    self.servers_no_ping = False
    self.servers_preferred = []
    self.servers_sessionids = {}
    self.dns_cache = {}
    self.ping_cache = {}
    self.last_frontend_choice = 0

    self.kitename = ''
    self.kitesecret = ''
    self.dyndns = None
    self.last_updates = []
    self.backends = {}  # These are the backends we want tunnels for.
    self.conns = None
    self.last_loop = 0
    self.keep_looping = True
    self.main_loop = True
    self.watch_level = [None]

    self.crash_report_url = '%scgi-bin/crashes.pl' % WWWHOME
    self.rcfile_recursion = 0
    self.rcfiles_loaded = []
    self.savefile = None
    self.added_kites = False
    self.ui_wfile = sys.stderr
    self.ui_rfile = sys.stdin
    self.ui_port = None
    self.ui_conn = None
    self.ui_comm = None

    self.save = 0
    self.shell = False
    self.kite_add = False
    self.kite_only = False
    self.kite_disable = False
    self.kite_remove = False

    # Searching for our configuration file!  We prefer the documented
    # 'standard' locations, but if nothing is found there and something local
    # exists, use that instead.
    try:
      if sys.platform[:3] in ('win', 'os2'):
        self.rcfile = os.path.join(os.path.expanduser('~'), 'pagekite.cfg')
        self.devnull = 'nul'
      else:
        # Everything else
        self.rcfile = os.path.join(os.path.expanduser('~'), '.pagekite.rc')
        self.devnull = '/dev/null'

    except Exception, e:
      # The above stuff may fail in some cases, e.g. on Android in SL4A.
      self.rcfile = 'pagekite.cfg'
      self.devnull = '/dev/null'

    # Look for CA Certificates. If we don't find them in the host OS,
    # we assume there might be something good in the program itself.
    self.ca_certs_default = '/etc/ssl/certs/ca-certificates.crt'
    if not os.path.exists(self.ca_certs_default):
      self.ca_certs_default = sys.argv[0]
    self.ca_certs = self.ca_certs_default

  ACL_SHORTHAND = {
    'localhost': '((::ffff:)?127\..*|::1)',
    'any': '.*'
  }
  def CheckAcls(self, acls, address, which, conn=None):
    if not acls:
      return True
    for policy, pattern in acls:
      if re.match(self.ACL_SHORTHAND.get(pattern, pattern)+'$', address[0]):
        if (policy.lower() == 'allow'):
          return True
        else:
          if conn:
            conn.LogError(('%s rejected by %s ACL: %s:%s'
                           ) % (address[0], which, policy, pattern))
          return False
    if conn:
      conn.LogError('%s rejected by default %s ACL' % (address[0], which))
    return False

  def CheckClientAcls(self, address, conn=None):
    return self.CheckAcls(self.client_acls, address, 'client', conn)

  def CheckTunnelAcls(self, address, conn=None):
    return self.CheckAcls(self.tunnel_acls, address, 'tunnel', conn)

  def SetLocalSettings(self, ports):
    self.isfrontend = True
    self.servers_auto = None
    self.servers_manual = []
    self.servers_never = []
    self.server_ports = ports
    self.backends = self.ArgToBackendSpecs('http:localhost:localhost:builtin:-')

  def SetServiceDefaults(self, clobber=True, check=False):
    def_dyndns    = (DYNDNS['pagekite.net'], {'user': '', 'pass': ''})
    def_frontends = (1, 'frontends.b5p.us', 443)
    def_ca_certs  = sys.argv[0]
    def_fe_certs  = ['b5p.us'] + [c for c in SERVICE_CERTS if c != 'b5p.us']
    def_error_url = 'https://pagekite.net/offline/?'
    if check:
      return (self.dyndns == def_dyndns and
              self.servers_auto == def_frontends and
              self.error_url == def_error_url and
              self.ca_certs == def_ca_certs and
              (sorted(self.fe_certname) == sorted(def_fe_certs) or
               not socks.HAVE_SSL))
    else:
      self.dyndns = (not clobber and self.dyndns) or def_dyndns
      self.servers_auto = (not clobber and self.servers_auto) or def_frontends
      self.error_url = (not clobber and self.error_url) or def_error_url
      self.ca_certs = def_ca_certs
      if socks.HAVE_SSL:
        for cert in def_fe_certs:
          if cert not in self.fe_certname:
            self.fe_certname.append(cert)
      return True

  def GenerateConfig(self, safe=False):
    config = [
      '###[ Current settings for pagekite.py v%s. ]#########' % APPVER,
      '#',
      '## NOTE: This file may be rewritten/reordered by pagekite.py.',
      '#',
      '',
    ]

    if not self.kitename:
      for be in self.backends.values():
        if not self.kitename or len(self.kitename) < len(be[BE_DOMAIN]):
          self.kitename = be[BE_DOMAIN]
          self.kitesecret = be[BE_SECRET]

    new = not (self.kitename or self.kitesecret or self.backends)
    def p(vfmt, value, dval):
      return '%s%s' % (value and value != dval
                             and ('', vfmt % value) or ('# ', vfmt % dval))

    if self.kitename or self.kitesecret or new:
      config.extend([
        '##[ Default kite and account details ]##',
        p('kitename   = %s', self.kitename, 'NAME'),
        p('kitesecret = %s', self.kitesecret, 'SECRET'),
        ''
      ])

    if self.SetServiceDefaults(check=True):
      config.extend([
        '##[ Front-end settings: use pagekite.net defaults ]##',
        'defaults',
        ''
      ])
      if self.servers_manual or self.servers_never:
        config.append('##[ Manual front-ends ]##')
        for server in sorted(self.servers_manual):
          config.append('frontend=%s' % server)
        for server in sorted(self.servers_never):
          config.append('nofrontend=%s' % server)
        config.append('')
    else:
      if not self.servers_auto and not self.servers_manual:
        new = True
        config.extend([
          '##[ Use this to just use pagekite.net defaults ]##',
          '# defaults',
          ''
        ])
      config.append('##[ Custom front-end and dynamic DNS settings ]##')
      if self.servers_auto:
        config.append('frontends = %d:%s:%d' % self.servers_auto)
      if self.servers_manual:
        for server in sorted(self.servers_manual):
          config.append('frontend = %s' % server)
      if self.servers_never:
        for server in sorted(self.servers_never):
          config.append('nofrontend = %s' % server)
      if not self.servers_auto and not self.servers_manual:
        new = True
        config.append('# frontends = N:hostname:port')
        config.append('# frontend = hostname:port')
        config.append('# nofrontend = hostname:port  # never connect')

      for server in self.fe_certname:
        config.append('fe_certname = %s' % server)
      if self.ca_certs != self.ca_certs_default:
        config.append('ca_certs = %s' % self.ca_certs)

      if self.dyndns:
        provider, args = self.dyndns
        for prov in sorted(DYNDNS.keys()):
          if DYNDNS[prov] == provider and prov != 'beanstalks.net':
            args['prov'] = prov
        if 'prov' not in args:
          args['prov'] = provider
        if args['pass']:
          config.append('dyndns = %(user)s:%(pass)s@%(prov)s' % args)
        elif args['user']:
          config.append('dyndns = %(user)s@%(prov)s' % args)
        else:
          config.append('dyndns = %(prov)s' % args)
      else:
        new = True
        config.extend([
          '# dyndns = pagekite.net OR',
          '# dyndns = user:pass@dyndns.org OR',
          '# dyndns = user:pass@no-ip.com' ,
          '#',
          p('errorurl  = %s', self.error_url, 'http://host/page/'),
          p('fingerpath = %s', self.finger_path, '/~%s/.finger'),
          '',
        ])
      config.append('')

    if self.ui_sspec or self.ui_password or self.ui_pemfile:
      config.extend([
        '##[ Built-in HTTPD settings ]##',
        p('httpd = %s:%s', self.ui_sspec_cfg, ('host', 'port'))
      ])
      if self.ui_password: config.append('httppass=%s' % self.ui_password)
      if self.ui_pemfile: config.append('pemfile=%s' % self.ui_pemfile)
      for http_host in sorted(self.ui_paths.keys()):
        for path in sorted(self.ui_paths[http_host].keys()):
          up = self.ui_paths[http_host][path]
          config.append('webpath = %s:%s:%s:%s' % (http_host, path, up[0], up[1]))
      config.append('')

    config.append('##[ Back-ends and local services ]##')
    bprinted = 0
    for bid in sorted(self.backends.keys()):
      be = self.backends[bid]
      proto, domain = bid.split(':')
      if be[BE_BHOST]:
        be_spec = (be[BE_BHOST], be[BE_BPORT])
        be_spec = ((be_spec == self.ui_sspec) and 'localhost:builtin'
                                               or ('%s:%s' % be_spec))
        fe_spec = ('%s:%s' % (proto, (domain == self.kitename) and '@kitename'
                                                               or domain))
        secret = ((be[BE_SECRET] == self.kitesecret) and '@kitesecret'
                                                      or be[BE_SECRET])
        config.append(('%s = %-33s: %-18s: %s'
                       ) % ((be[BE_STATUS] == BE_STATUS_DISABLED
                             ) and 'service_off' or 'service_on ',
                            fe_spec, be_spec, secret))
        bprinted += 1
    if bprinted == 0:
      config.append('# No back-ends!  How boring!')
    config.append('')
    for http_host in sorted(self.be_config.keys()):
      for key in sorted(self.be_config[http_host].keys()):
        config.append(('service_cfg = %-30s: %-15s: %s'
                       ) % (http_host, key, self.be_config[http_host][key]))
    config.append('')

    if bprinted == 0:
      new = True
      config.extend([
        '##[ Back-end service examples ... ]##',
        '#',
        '# service_on = http:YOU.pagekite.me:localhost:80:SECRET',
        '# service_on = ssh:YOU.pagekite.me:localhost:22:SECRET',
        '# service_on = http/8080:YOU.pagekite.me:localhost:8080:SECRET',
        '# service_on = https:YOU.pagekite.me:localhost:443:SECRET',
        '# service_on = websocket:YOU.pagekite.me:localhost:8080:SECRET',
        '# service_on = minecraft:YOU.pagekite.me:localhost:8080:SECRET',
        '#',
        '# service_off = http:YOU.pagekite.me:localhost:4545:SECRET',
        ''
      ])

    config.extend([
      '##[ Allow risky known-to-be-risky incoming HTTP requests? ]##',
      (self.insecure) and 'insecure' or '# insecure',
      ''
    ])

    if self.isfrontend or new:
      config.extend([
        '##[ Front-end Options ]##',
        (self.isfrontend and 'isfrontend' or '# isfrontend')
      ])
      comment = ((not self.isfrontend) and '# ' or '')
      config.extend([
        p('host = %s', self.isfrontend and self.server_host, 'machine.domain.com'),
        '%sports = %s' % (comment, ','.join(['%s' % x for x in sorted(self.server_ports)] or [])),
        '%sprotos = %s' % (comment, ','.join(['%s' % x for x in sorted(self.server_protos)] or []))
      ])
      for pa in self.server_portalias:
        config.append('portalias = %s:%s' % (int(pa), int(self.server_portalias[pa])))
      config.extend([
        '%srawports = %s' % (comment or (not self.server_raw_ports) and '# ' or '',
                           ','.join(['%s' % x for x in sorted(self.server_raw_ports)] or [VIRTUAL_PN])),
        p('authdomain = %s', self.isfrontend and self.auth_domain, 'foo.com'),
        p('motd = %s', self.isfrontend and self.motd, '/path/to/motd.txt')
      ])
      for d in sorted(self.auth_domains.keys()):
        config.append('authdomain=%s:%s' % (d, self.auth_domains[d]))
      dprinted = 0
      for bid in sorted(self.backends.keys()):
        be = self.backends[bid]
        if not be[BE_BHOST]:
          config.append('domain = %s:%s' % (bid, be[BE_SECRET]))
          dprinted += 1
      if not dprinted:
        new = True
        config.extend([
          '# domain = http:*.pagekite.me:SECRET1',
          '# domain = http,https,websocket:THEM.pagekite.me:SECRET2',
        ])

      eprinted = 0
      config.extend([
        '',
        '##[ Domains we terminate SSL/TLS for natively, with key/cert-files ]##'
      ])
      for ep in sorted(self.tls_endpoints.keys()):
        config.append('tls_endpoint = %s:%s' % (ep, self.tls_endpoints[ep][0]))
        eprinted += 1
      if eprinted == 0:
        new = True
        config.append('# tls_endpoint = DOMAIN:PEM_FILE')
      config.extend([
        p('tls_default = %s', self.tls_default, 'DOMAIN'),
        '',
      ])

    config.extend([
      '##[ Proxy-chain settings ]##',
      (self.no_proxy and 'noproxy' or '# noproxy'),
    ])
    for proxy in self.proxy_servers:
      config.append('proxy = %s' % proxy)
    if not self.proxy_servers:
      config.extend([
        '# socksify = host:port',
        '# torify   = host:port',
        '# proxy    = ssl:/path/to/client-cert.pem@host,CommonName:port',
        '# proxy    = http://user:password@host:port/',
        '# proxy    = socks://user:password@host:port/'
      ])

    config.extend([
      '',
      '##[ Front-end access controls (default=deny, if configured) ]##',
      p('accept_acl_file = %s', self.accept_acl_file, '/path/to/file'),
    ])
    for policy, pattern in self.client_acls:
      config.append('client_acl=%s:%s' % (policy, pattern))
    if not self.client_acls:
      config.append('# client_acl=[allow|deny]:IP-regexp')
    for policy, pattern in self.tunnel_acls:
      config.append('tunnel_acl=%s:%s' % (policy, pattern))
    if not self.tunnel_acls:
      config.append('# tunnel_acl=[allow|deny]:IP-regexp')
    config.extend([
      '',
      '',
      '###[ Anything below this line can usually be ignored. ]#########',
      '',
      '##[ Miscellaneous settings ]##',
      p('logfile = %s', self.logfile, '/path/to/file'),
      p('buffers = %s', self.buffer_max, DEFAULT_BUFFER_MAX),
      (self.servers_new_only is True) and 'new' or '# new',
      (self.require_all and 'all' or '# all'),
      (self.no_probes and 'noprobes' or '# noprobes'),
      (self.crash_report_url and '# nocrashreport' or 'nocrashreport'),
      p('savefile = %s', safe and self.savefile, '/path/to/savefile'),
      '',
    ])

    if self.daemonize or self.setuid or self.setgid or self.pidfile or new:
      config.extend([
        '##[ Systems administration settings ]##',
        (self.daemonize and 'daemonize' or '# daemonize')
      ])
      if self.setuid and self.setgid:
        config.append('runas = %s:%s' % (self.setuid, self.setgid))
      elif self.setuid:
        config.append('runas = %s' % self.setuid)
      else:
        new = True
        config.append('# runas = uid:gid')
      config.append(p('pidfile = %s', self.pidfile, '/path/to/file'))

    config.extend([
      '',
      '###[ End of pagekite.py configuration ]#########',
      'END',
      ''
    ])
    if not new:
      config = [l for l in config if not l.startswith('# ')]
      clean_config = []
      for i in range(0, len(config)-1):
        if i > 0 and (config[i].startswith('#') or config[i] == ''):
          if config[i+1] != '' or clean_config[-1].startswith('#'):
            clean_config.append(config[i])
        else:
          clean_config.append(config[i])
      clean_config.append(config[-1])
      return clean_config
    else:
      return config

  def ConfigSecret(self, new=False):
    # This method returns a stable secret for the lifetime of this process.
    #
    # The secret depends on the active configuration as, reported by
    # GenerateConfig().  This lets external processes generate the same
    # secret and use the remote-control APIs as long as they can read the
    # *entire* config (which contains all the sensitive bits anyway).
    #
    if self.ui_httpd and self.ui_httpd.httpd and not new:
      return self.ui_httpd.httpd.secret
    else:
      return sha1hex('\n'.join(self.GenerateConfig()))

  def LoginPath(self, goto):
    return '/_pagekite/login/%s/%s' % (self.ConfigSecret(), goto)

  def LoginUrl(self, goto=''):
    return 'http%s://%s%s' % (self.ui_pemfile and 's' or '',
                              '%s:%s' % self.ui_sspec,
                              self.LoginPath(goto))

  def ListKites(self):
    self.ui.welcome = '>>> ' + self.ui.WHITE + 'Your kites:' + self.ui.NORM
    message = []
    for bid in sorted(self.backends.keys()):
      be = self.backends[bid]
      be_be = (be[BE_BHOST], be[BE_BPORT])
      backend = (be_be == self.ui_sspec) and 'builtin' or '%s:%s' % be_be
      fe_port = be[BE_PORT] or ''
      frontend = '%s://%s%s%s' % (be[BE_PROTO], be[BE_DOMAIN],
                                  fe_port and ':' or '', fe_port)

      if be[BE_STATUS] == BE_STATUS_DISABLED:
        color = self.ui.GREY
        status = '(disabled)'
      else:
        color = self.ui.NORM
        status = (be[BE_PROTO] == 'raw') and '(HTTP proxied)' or ''
      message.append(''.join([color, backend, ' ' * (19-len(backend)),
                              frontend, ' ' * (42-len(frontend)), status]))
    message.append(self.ui.NORM)
    self.ui.Tell(message)

  def PrintSettings(self, safe=False):
    print '\n'.join(self.GenerateConfig(safe=safe))

  def SaveUserConfig(self, quiet=False):
    self.savefile = self.savefile or self.rcfile
    try:
      fd = SecureCreate(self.savefile)
      fd.write('\n'.join(self.GenerateConfig(safe=True)))
      fd.close()
      if not quiet:
        self.ui.Tell(['Settings saved to: %s' % self.savefile])
        self.ui.Spacer()
      logging.Log([('saved', 'Settings saved to: %s' % self.savefile)])
    except Exception, e:
      if logging.DEBUG_IO: traceback.print_exc(file=sys.stderr)
      self.ui.Tell(['Could not save to %s: %s' % (self.savefile, e)],
                   error=True)
      self.ui.Spacer()

  def FallDown(self, message, help=True, longhelp=False, noexit=False):
    if self.conns and self.conns.auth:
      self.conns.auth.quit()
    if self.ui_httpd:
      self.ui_httpd.quit()
    if self.ui_comm:
      self.ui_comm.quit()
    if self.tunnel_manager:
      self.tunnel_manager.quit()
    self.keep_looping = False

    for fd in (self.conns and self.conns.Sockets() or []):
      try:
        fd.close()
      except (IOError, OSError, TypeError, AttributeError):
        pass
    self.conns = self.ui_httpd = self.ui_comm = self.tunnel_manager = None

    try:
      os.dup2(sys.stderr.fileno(), sys.stdout.fileno())
    except:
      pass
    print
    if help or longhelp:
      import manual
      print longhelp and manual.DOC() or manual.MINIDOC()
      print '***'
    elif not noexit:
      self.ui.Status('exiting', message=(message or 'Good-bye!'))
    if message:
      print 'Error: %s' % message

    if logging.DEBUG_IO:
      traceback.print_exc(file=sys.stderr)
    if not noexit:
      self.main_loop = False
      sys.exit(1)

  def GetTlsEndpointCtx(self, domain):
    if domain in self.tls_endpoints:
      return self.tls_endpoints[domain][1]
    parts = domain.split('.')
    # Check for wildcards ...
    if len(parts) > 2:
      parts[0] = '*'
      domain = '.'.join(parts)
      if domain in self.tls_endpoints:
        return self.tls_endpoints[domain][1]
    return None

  def SetBackendStatus(self, domain, proto='', add=None, sub=None):
    match = '%s:%s' % (proto, domain)
    for bid in self.backends:
      if bid == match or (proto == '' and bid.endswith(match)):
        status = self.backends[bid][BE_STATUS]
        if add: self.backends[bid][BE_STATUS] |= add
        if sub and (status & sub): self.backends[bid][BE_STATUS] -= sub
        logging.Log([('bid', bid),
             ('status', '0x%x' % self.backends[bid][BE_STATUS])])

  def GetBackendData(self, proto, domain, recurse=True):
    backend = '%s:%s' % (proto.lower(), domain.lower())
    if backend in self.backends:
      if self.backends[backend][BE_STATUS] not in BE_INACTIVE:
        return self.backends[backend]

    if recurse:
      dparts = domain.split('.')
      while len(dparts) > 1:
        dparts = dparts[1:]
        data = self.GetBackendData(proto, '.'.join(['*'] + dparts), recurse=False)
        if data: return data

    return None

  def GetBackendServer(self, proto, domain, recurse=True):
    backend = self.GetBackendData(proto, domain) or BE_NONE
    bhost, bport = (backend[BE_BHOST], backend[BE_BPORT])
    if bhost == '-' or not bhost: return None, None
    return (bhost, bport), backend

  def IsSignatureValid(self, sign, secret, proto, domain, srand, token):
    return checkSignature(sign=sign, secret=secret,
                          payload='%s:%s:%s:%s' % (proto, domain, srand, token))

  def LookupDomainQuota(self, lookup):
    if not lookup.endswith('.'): lookup += '.'
    if logging.DEBUG_IO: print '=== AUTH LOOKUP\n%s\n===' % lookup
    (hn, al, ips) = socket.gethostbyname_ex(lookup)
    if logging.DEBUG_IO: print 'hn=%s\nal=%s\nips=%s\n' % (hn, al, ips)

    # Extract auth error and extended quota info from CNAME replies
    if al:
      error, hg, hd, hc, junk = hn.split('.', 4)
      q_days = int(hd, 16)
      q_conns = int(hc, 16)
    else:
      error = q_days = q_conns = None

    # If not an authentication error, quota should be encoded as an IP.
    ip = ips[0]
    if ip.startswith(AUTH_ERRORS):
      if not error and (ip.endswith(AUTH_ERR_USER_UNKNOWN) or
                        ip.endswith(AUTH_ERR_INVALID)):
        error = 'unauthorized'
    else:
      o = [int(x) for x in ip.split('.')]
      return ((((o[0]*256 + o[1])*256 + o[2])*256 + o[3]), q_days, q_conns, None)

    # Errors on real errors are final.
    if not ip.endswith(AUTH_ERR_USER_UNKNOWN): return (None, q_days, q_conns, error)

    # User unknown, fall through to local test.
    return (-1, q_days, q_conns, error)

  def GetDomainQuota(self, protoport, domain, srand, token, sign,
                     recurse=True, check_token=True):
    if '-' in protoport:
      try:
        proto, port = protoport.split('-', 1)
        if proto == 'raw':
          port_list = self.server_raw_ports
        else:
          port_list = self.server_ports

        porti = int(port)
        if porti in self.server_aliasport: porti = self.server_aliasport[porti]
        if porti not in port_list and VIRTUAL_PN not in port_list:
          logging.LogInfo('Unsupported port request: %s (%s:%s)' % (porti, protoport, domain))
          return (None, None, None, 'port')

      except ValueError:
        logging.LogError('Invalid port request: %s:%s' % (protoport, domain))
        return (None, None, None, 'port')
    else:
      proto, port = protoport, None

    if proto not in self.server_protos:
      logging.LogInfo('Invalid proto request: %s:%s' % (protoport, domain))
      return (None, None, None, 'proto')

    data = '%s:%s:%s' % (protoport, domain, srand)
    auth_error_type = None
    if ((not token) or
        (not check_token) or
        checkSignature(sign=token, payload=data)):

      secret = (self.GetBackendData(protoport, domain) or BE_NONE)[BE_SECRET]
      if not secret:
        secret = (self.GetBackendData(proto, domain) or BE_NONE)[BE_SECRET]

      if secret:
        if self.IsSignatureValid(sign, secret, protoport, domain, srand, token):
          return (-1, None, None, None)
        elif not self.auth_domain:
          logging.LogError('Invalid signature for: %s (%s)' % (domain, protoport))
          return (None, None, None, auth_error_type or 'signature')

      if self.auth_domain:
        adom = self.auth_domain
        for dom in self.auth_domains:
          if domain.endswith('.%s' % dom):
            adom = self.auth_domains[dom]
        try:
          lookup = '.'.join([srand, token, sign, protoport,
                             domain.replace('*', '_any_'), adom])
          (rv, qd, qc, auth_error_type) = self.LookupDomainQuota(lookup)
          if rv is None or rv >= 0:
            return (rv, qd, qc, auth_error_type)
        except Exception, e:
          # Lookup failed, fail open.
          logging.LogError('Quota lookup failed: %s' % e)
          return (-2, None, None, None)

    logging.LogInfo('No authentication found for: %s (%s)' % (domain, protoport))
    return (None, None, None, auth_error_type or 'unauthorized')

  def ConfigureFromFile(self, filename=None, data=None):
    if not filename: filename = self.rcfile

    if self.rcfile_recursion > 25:
      raise ConfigError('Nested too deep: %s' % filename)

    self.rcfiles_loaded.append(filename)
    optfile = data or open(filename)
    args = []
    for line in optfile:
      line = line.strip()
      if line and not line.startswith('#'):
        if line.startswith('END'): break
        if not line.startswith('-'): line = '--%s' % line
        args.append(re.sub(r'\s*:\s*', ':', re.sub(r'\s*=\s*', '=', line)))

    self.rcfile_recursion += 1
    self.Configure(args)
    self.rcfile_recursion -= 1
    return self

  def ConfigureFromDirectory(self, dirname):
    for fn in sorted(os.listdir(dirname)):
      if not fn.startswith('.') and fn.endswith('.rc'):
        self.ConfigureFromFile(os.path.join(dirname, fn))

  def HelpAndExit(self, longhelp=False):
    import manual
    print longhelp and manual.DOC() or manual.MINIDOC()
    sys.exit(0)

  def AddNewKite(self, kitespec, status=BE_STATUS_UNKNOWN, secret=None):
    new_specs = self.ArgToBackendSpecs(kitespec, status, secret)
    self.backends.update(new_specs)
    req = {}
    for server in self.conns.TunnelServers():
      req[server] = '\r\n'.join(PageKiteRequestHeaders(server, new_specs, {}))
    for tid, tunnels in self.conns.tunnels.iteritems():
      for tunnel in tunnels:
        server_name = tunnel.server_info[tunnel.S_NAME]
        if server_name in req:
          tunnel.SendChunked('NOOP: 1\r\n%s\r\n\r\n!' % req[server_name],
                             compress=False)
          del req[server_name]

  def ArgToBackendSpecs(self, arg, status=BE_STATUS_UNKNOWN, secret=None):
    protos, fe_domain, be_host, be_port = '', '', '', ''

    # Interpret the argument into a specification of what we want.
    parts = arg.split(':')
    if len(parts) == 5:
      protos, fe_domain, be_host, be_port, secret = parts
    elif len(parts) == 4:
      protos, fe_domain, be_host, be_port = parts
    elif len(parts) == 3:
      protos, fe_domain, be_port = parts
    elif len(parts) == 2:
      if (parts[1] == 'builtin') or ('.' in parts[0] and
                                            os.path.exists(parts[1])):
        fe_domain, be_port = parts[0], parts[1]
        protos = 'http'
      else:
        try:
          fe_domain, be_port = parts[0], '%s' % int(parts[1])
          protos = 'http'
        except:
          be_port = ''
          protos, fe_domain = parts
    elif len(parts) == 1:
      fe_domain = parts[0]
    else:
      return {}

    # Allow http:// as a common typo instead of http:
    fe_domain = fe_domain.replace('/', '').lower()

    # Allow easy referencing of built-in HTTPD
    if be_port == 'builtin':
      self.BindUiSspec()
      be_host, be_port = self.ui_sspec

    # Specs define what we are searching for...
    specs = []
    if protos:
      for proto in protos.replace('/', '-').lower().split(','):
        if proto == 'ssh':
          specs.append(['raw', '22', fe_domain, be_host, be_port or '22', secret])
        else:
          if '-' in proto:
            proto, port = proto.split('-')
          else:
            if len(parts) == 1:
              port = '*'
            else:
              port = ''
          specs.append([proto, port, fe_domain, be_host, be_port, secret])
    else:
      specs = [[None, '', fe_domain, be_host, be_port, secret]]

    backends = {}
    # For each spec, search through the existing backends and copy matches
    # or just shared secrets for partial matches.
    for proto, port, fdom, bhost, bport, sec in specs:
      matches = 0
      for bid in self.backends:
        be = self.backends[bid]
        if fdom and fdom != be[BE_DOMAIN]: continue
        if not sec and be[BE_SECRET]: sec = be[BE_SECRET]
        if proto and (proto != be[BE_PROTO]): continue
        if bhost and (bhost.lower() != be[BE_BHOST]): continue
        if bport and (int(bport) != be[BE_BHOST]): continue
        if port and (port != '*') and (int(port) != be[BE_PORT]): continue
        backends[bid] = be[:]
        backends[bid][BE_STATUS] = status
        matches += 1

      if matches == 0:
        proto = (proto or 'http')
        bhost = (bhost or 'localhost')
        bport = (bport or (proto in ('http', 'httpfinger', 'websocket') and 80)
                       or (proto == 'irc' and 6667)
                       or (proto == 'https' and 443)
                       or (proto == 'minecraft' and 25565)
                       or (proto == 'finger' and 79))
        if port:
          bid = '%s-%d:%s' % (proto, int(port), fdom)
        else:
          bid = '%s:%s' % (proto, fdom)

        backends[bid] = BE_NONE[:]
        backends[bid][BE_PROTO] = proto
        backends[bid][BE_PORT] = port and int(port) or ''
        backends[bid][BE_DOMAIN] = fdom
        backends[bid][BE_BHOST] = bhost.lower()
        backends[bid][BE_BPORT] = int(bport)
        backends[bid][BE_SECRET] = sec
        backends[bid][BE_STATUS] = status

    return backends

  def BindUiSspec(self, force=False):
    # Create the UI thread
    if self.ui_httpd and self.ui_httpd.httpd:
      if not force: return self.ui_sspec
      self.ui_httpd.httpd.socket.close()

    self.ui_sspec = self.ui_sspec or ('localhost', 0)
    self.ui_httpd = HttpUiThread(self, self.conns,
                                 handler=self.ui_request_handler,
                                 server=self.ui_http_server,
                                 ssl_pem_filename = self.ui_pemfile)
    return self.ui_sspec

  def LoadMOTD(self):
    if self.motd:
      try:
        f = open(self.motd, 'r')
        self.motd_message = ''.join(f.readlines()).strip()[:8192]
        f.close()
      except (OSError, IOError):
        pass

  def SetPem(self, filename):
    self.ui_pemfile = filename
    try:
      p = os.popen('openssl x509 -noout -fingerprint -in %s' % filename, 'r')
      data = p.read().strip()
      p.close()
      self.ui_pemfingerprint = data.split('=')[1]
    except (OSError, ValueError):
      pass

  def Configure(self, argv):
    self.conns = self.conns or Connections(self)
    opts, args = getopt.getopt(argv, OPT_FLAGS, OPT_ARGS)

    for opt, arg in opts:
      if opt in ('-o', '--optfile'):
        self.ConfigureFromFile(arg)
      elif opt in ('-O', '--optdir'):
        self.ConfigureFromDirectory(arg)
      elif opt in ('-S', '--savefile'):
        if self.savefile: raise ConfigError('Multiple save-files!')
        self.savefile = arg
      elif opt == '--shell':
        self.shell = True
      elif opt == '--save':
        self.save = True
      elif opt == '--only':
        self.save = self.kite_only = True
        if self.kite_remove or self.kite_add or self.kite_disable:
          raise ConfigError('One change at a time please!')
      elif opt == '--add':
        self.save = self.kite_add = True
        if self.kite_remove or self.kite_only or self.kite_disable:
          raise ConfigError('One change at a time please!')
      elif opt == '--remove':
        self.save = self.kite_remove = True
        if self.kite_add or self.kite_only or self.kite_disable:
          raise ConfigError('One change at a time please!')
      elif opt == '--disable':
        self.save = self.kite_disable = True
        if self.kite_add or self.kite_only or self.kite_remove:
          raise ConfigError('One change at a time please!')
      elif opt == '--list': pass

      elif opt in ('-I', '--pidfile'): self.pidfile = arg
      elif opt in ('-L', '--logfile'): self.logfile = arg
      elif opt in ('-Z', '--daemonize'):
        self.daemonize = True
        if not self.ui.DAEMON_FRIENDLY: self.ui = NullUi()
      elif opt in ('-U', '--runas'):
        import pwd
        import grp
        parts = arg.split(':')
        if len(parts) > 1:
          self.setuid, self.setgid = (pwd.getpwnam(parts[0])[2],
                                      grp.getgrnam(parts[1])[2])
        else:
          self.setuid = pwd.getpwnam(parts[0])[2]
        self.main_loop = False

      elif opt in ('-X', '--httppass'): self.ui_password = arg
      elif opt in ('-P', '--pemfile'): self.SetPem(arg)
      elif opt in ('--selfsign', ):
        pf = self.rcfile.replace('.rc', '.pem').replace('.cfg', '.pem')
        if not os.path.exists(pf):
          CreateSelfSignedCert(pf, self.ui)
        self.SetPem(pf)
      elif opt in ('-H', '--httpd'):
        parts = arg.split(':')
        host = parts[0] or 'localhost'
        if len(parts) > 1:
          self.ui_sspec = self.ui_sspec_cfg = (host, int(parts[1]))
        else:
          self.ui_sspec = self.ui_sspec_cfg = (host, 0)

      elif opt == '--nowebpath':
        host, path = arg.split(':', 1)
        if host in self.ui_paths and path in self.ui_paths[host]:
          del self.ui_paths[host][path]
      elif opt == '--webpath':
        host, path, policy, fpath = arg.split(':', 3)

        # Defaults...
        path = path or os.path.normpath(fpath)
        host = host or '*'
        policy = policy or WEB_POLICY_DEFAULT

        if policy not in WEB_POLICIES:
          raise ConfigError('Policy must be one of: %s' % WEB_POLICIES)
        elif os.path.isdir(fpath):
          if not path.endswith('/'): path += '/'

        hosti = self.ui_paths.get(host, {})
        hosti[path] = (policy or 'public', os.path.abspath(fpath))
        self.ui_paths[host] = hosti

      elif opt == '--tls_default': self.tls_default = arg
      elif opt == '--tls_endpoint':
        name, pemfile = arg.split(':', 1)
        ctx = SSL.Context(SSL.SSLv23_METHOD)
        ctx.use_privatekey_file(pemfile)
        ctx.use_certificate_chain_file(pemfile)
        self.tls_endpoints[name] = (pemfile, ctx)

      elif opt in ('-D', '--dyndns'):
        if arg.startswith('http'):
          self.dyndns = (arg, {'user': '', 'pass': ''})
        elif '@' in arg:
          splits = arg.split('@')
          provider = splits.pop()
          usrpwd = '@'.join(splits)
          if provider in DYNDNS: provider = DYNDNS[provider]
          if ':' in usrpwd:
            usr, pwd = usrpwd.split(':', 1)
            self.dyndns = (provider, {'user': usr, 'pass': pwd})
          else:
            self.dyndns = (provider, {'user': usrpwd, 'pass': ''})
        elif arg:
          if arg in DYNDNS: arg = DYNDNS[arg]
          self.dyndns = (arg, {'user': '', 'pass': ''})
        else:
          self.dyndns = None

      elif opt in ('-p', '--ports'): self.server_ports = [int(x) for x in arg.split(',')]
      elif opt == '--portalias':
        port, alias = arg.split(':')
        self.server_portalias[int(port)] = int(alias)
        self.server_aliasport[int(alias)] = int(port)
      elif opt == '--protos': self.server_protos = [x.lower() for x in arg.split(',')]
      elif opt == '--rawports':
        self.server_raw_ports = [(x == VIRTUAL_PN and x or int(x)) for x in arg.split(',')]
      elif opt in ('-h', '--host'): self.server_host = arg
      elif opt in ('-A', '--authdomain'):
        if ':' in arg:
          d, a = arg.split(':')
          self.auth_domains[d.lower()] = a
          if not self.auth_domain: self.auth_domain = a
        else:
          self.auth_domains = {}
          self.auth_domain = arg
      elif opt == '--motd':
        self.motd = arg
        self.LoadMOTD()
      elif opt == '--noupgradeinfo': self.upgrade_info = []
      elif opt == '--upgradeinfo':
        version, tag, md5, human_url, file_url = arg.split(';')
        self.upgrade_info.append((version, tag, md5, human_url, file_url))
      elif opt in ('-f', '--isfrontend'):
        self.isfrontend = True
        logging.LOG_THRESHOLD *= 4

      elif opt in ('-a', '--all'): self.require_all = True
      elif opt in ('-N', '--new'): self.servers_new_only = True
      elif opt == '--accept_acl_file':
        self.accept_acl_file = arg
      elif opt == '--client_acl':
        policy, pattern = arg.split(':', 1)
        self.client_acls.append((policy, pattern))
      elif opt == '--tunnel_acl':
        policy, pattern = arg.split(':', 1)
        self.tunnel_acls.append((policy, pattern))
      elif opt in ('--noproxy', ):
        self.no_proxy = True
        self.proxy_servers = []
        socks.setdefaultproxy()
      elif opt in ('--proxy', '--socksify', '--torify'):
        if opt == '--proxy':
          socks.adddefaultproxy(*socks.parseproxy(arg))
        else:
          (host, port) = arg.rsplit(':', 1)
          socks.adddefaultproxy(socks.PROXY_TYPE_SOCKS5, host, int(port))

        if not self.proxy_servers:
          # Make DynDNS updates go via the proxy.
          socks.wrapmodule(urllib)
          self.proxy_servers = [arg]
        else:
          self.proxy_servers.append(arg)

        if opt == '--torify':
          self.servers_new_only = True  # Disable initial DNS lookups (leaks)
          self.servers_no_ping = True   # Disable front-end pings
          self.crash_report_url = None  # Disable crash reports

          # This increases the odds of unrelated requests getting lumped
          # together in the tunnel, which makes traffic analysis harder.
          compat.SEND_ALWAYS_BUFFERS = True

      elif opt == '--ca_certs': self.ca_certs = arg
      elif opt == '--jakenoia': self.fe_anon_tls_wrap = True
      elif opt == '--fe_certname':
        if arg == '':
          self.fe_certname = []
        else:
          cert = arg.lower()
          if cert not in self.fe_certname: self.fe_certname.append(cert)
      elif opt == '--service_xmlrpc': self.service_xmlrpc = arg
      elif opt == '--frontend': self.servers_manual.append(arg)
      elif opt == '--nofrontend': self.servers_never.append(arg)
      elif opt == '--frontends':
        count, domain, port = arg.split(':')
        self.servers_auto = (int(count), domain, int(port))

      elif opt in ('--errorurl', '-E'): self.error_url = arg
      elif opt == '--fingerpath': self.finger_path = arg
      elif opt == '--kitename': self.kitename = arg
      elif opt == '--kitesecret': self.kitesecret = arg

      elif opt in ('--service_on', '--service_off',
                   '--backend', '--define_backend'):
        if opt in ('--backend', '--service_on'):
          status = BE_STATUS_UNKNOWN
        else:
          status = BE_STATUS_DISABLED
        bes = self.ArgToBackendSpecs(arg.replace('@kitesecret', self.kitesecret)
                                        .replace('@kitename', self.kitename),
                                     status=status)
        for bid in bes:
          if bid in self.backends:
            raise ConfigError("Same service/domain defined twice: %s" % bid)
          if not self.kitename:
            self.kitename = bes[bid][BE_DOMAIN]
            self.kitesecret = bes[bid][BE_SECRET]
        self.backends.update(bes)
      elif opt in ('--be_config', '--service_cfg'):
        host, key, val = arg.split(':', 2)
        if key.startswith('user/'): key = key.replace('user/', 'password/')
        hostc = self.be_config.get(host, {})
        hostc[key] = {'True': True, 'False': False, 'None': None}.get(val, val)
        self.be_config[host] = hostc

      elif opt == '--domain':
        protos, domain, secret = arg.split(':')
        if protos in ('*', ''): protos = ','.join(self.server_protos)
        for proto in protos.split(','):
          bid = '%s:%s' % (proto, domain)
          if bid in self.backends:
            raise ConfigError("Same service/domain defined twice: %s" % bid)
          self.backends[bid] = BE_NONE[:]
          self.backends[bid][BE_PROTO] = proto
          self.backends[bid][BE_DOMAIN] = domain
          self.backends[bid][BE_SECRET] = secret
          self.backends[bid][BE_STATUS] = BE_STATUS_UNKNOWN

      elif opt == '--insecure': self.insecure = True
      elif opt == '--noprobes': self.no_probes = True
      elif opt == '--nofrontend': self.isfrontend = False
      elif opt == '--nodaemonize': self.daemonize = False
      elif opt == '--noall': self.require_all = False
      elif opt == '--nozchunks': self.disable_zchunks = True
      elif opt == '--nullui': self.ui = NullUi()
      elif opt == '--remoteui':
        import pagekite.ui.remote
        self.ui = pagekite.ui.remote.RemoteUi()
      elif opt == '--uiport': self.ui_port = int(arg)
      elif opt == '--sslzlib': self.enable_sslzlib = True
      elif opt == '--watch':
        self.watch_level[0] = int(arg)
      elif opt == '--debugio':
        logging.DEBUG_IO = True
      elif opt == '--buffers': self.buffer_max = int(arg)
      elif opt == '--nocrashreport': self.crash_report_url = None
      elif opt == '--noloop': self.main_loop = False
      elif opt == '--local':
        self.SetLocalSettings([int(p) for p in arg.split(',')])
        if not 'localhost' in args: args.append('localhost')
      elif opt == '--defaults': self.SetServiceDefaults()
      elif opt in ('--clean', '--nopyopenssl', '--nossl', '--settings',
                   '--signup', '--friendly'):
        # These are handled outside the main loop, we just ignore them.
        pass
      elif opt in ('--webroot', '--webaccess', '--webindexes',
                   '--noautosave', '--autosave', '--reloadfile',
                   '--delete_backend'):
        # FIXME: These are deprecated, we should probably warn the user.
        pass
      elif opt == '--help':
        self.HelpAndExit(longhelp=True)

      elif opt == '--controlpanel':
        import webbrowser
        webbrowser.open(self.LoginUrl())
        sys.exit(0)

      elif opt == '--controlpass':
        print self.ConfigSecret()
        sys.exit(0)

      else:
        self.HelpAndExit()

    # Make sure these are configured before we try and do XML-RPC stuff.
    socks.DEBUG = (logging.DEBUG_IO or socks.DEBUG) and logging.LogDebug
    if self.ca_certs: socks.setdefaultcertfile(self.ca_certs)

    # Handle the user-friendly argument stuff and simple registration.
    return self.ParseFriendlyBackendSpecs(args)

  def ParseFriendlyBackendSpecs(self, args):
    just_these_backends = {}
    just_these_webpaths = {}
    just_these_be_configs = {}
    argsets = []
    while 'AND' in args:
      argsets.append(args[0:args.index('AND')])
      args[0:args.index('AND')+1] = []
    if args:
      argsets.append(args)

    for args in argsets:
      # Extract the config options first...
      be_config = [p for p in args if p.startswith('+')]
      args = [p for p in args if not p.startswith('+')]

      fe_spec = (args.pop().replace('@kitesecret', self.kitesecret)
                           .replace('@kitename', self.kitename))
      if os.path.exists(fe_spec):
        raise ConfigError('Is a local file: %s' % fe_spec)

      be_paths = []
      be_path_prefix = ''
      if len(args) == 0:
        be_spec = ''
      elif len(args) == 1:
        if '*' in args[0] or '?' in args[0]:
          if sys.platform[:3] in ('win', 'os2'):
            be_paths = [args[0]]
            be_spec = 'builtin'
        elif os.path.exists(args[0]):
          be_paths = [args[0]]
          be_spec = 'builtin'
        else:
          be_spec = args[0]
      else:
        be_spec = 'builtin'
        be_paths = args[:]

      be_proto = 'http' # A sane default...
      if be_spec == '':
        be = None
      else:
        be = be_spec.replace('/', '').split(':')
        if be[0].lower() in ('http', 'http2', 'http3', 'https',
                             'httpfinger', 'finger', 'ssh', 'irc'):
          be_proto = be.pop(0)
          if len(be) < 2:
            be.append({'http': '80', 'http2': '80', 'http3': '80',
                       'https': '443', 'irc': '6667',
                       'httpfinger': '80', 'finger': '79',
                       'ssh': '22'}[be_proto])
        if len(be) > 2:
          raise ConfigError('Bad back-end definition: %s' % be_spec)
        if len(be) < 2:
          try:
            if be[0] != 'builtin':
              int(be[0])
            be = ['localhost', be[0]]
          except ValueError:
            raise ConfigError('`%s` should be a file, directory, port or '
                              'protocol' % be_spec)

      # Extract the path prefix from the fe_spec
      fe_urlp = fe_spec.split('/', 3)
      if len(fe_urlp) == 4:
        fe_spec = '/'.join(fe_urlp[:3])
        be_path_prefix = '/' + fe_urlp[3]

      fe = fe_spec.replace('/', '').split(':')
      if len(fe) == 3:
        fe = ['%s-%s' % (fe[0], fe[2]), fe[1]]
      elif len(fe) == 2:
        try:
          fe = ['%s-%s' % (be_proto, int(fe[1])), fe[0]]
        except ValueError:
          pass
      elif len(fe) == 1 and be:
        fe = [be_proto, fe[0]]

      # Do our own globbing on Windows
      if sys.platform[:3] in ('win', 'os2'):
        import glob
        new_paths = []
        for p in be_paths:
          new_paths.extend(glob.glob(p))
        be_paths = new_paths

      for f in be_paths:
        if not os.path.exists(f):
          raise ConfigError('File or directory not found: %s' % f)

      spec = ':'.join(fe)
      if be: spec += ':' + ':'.join(be)
      specs = self.ArgToBackendSpecs(spec)
      just_these_backends.update(specs)

      spec = specs[specs.keys()[0]]
      http_host = '%s/%s' % (spec[BE_DOMAIN], spec[BE_PORT] or '80')
      if be_config:
        # Map the +foo=bar values to per-site config settings.
        host_config = just_these_be_configs.get(http_host, {})
        for cfg in be_config:
          if '=' in cfg:
            key, val = cfg[1:].split('=', 1)
          elif cfg.startswith('+no'):
            key, val = cfg[3:], False
          else:
            key, val = cfg[1:], True
          if ':' in key:
            raise ConfigError('Please do not use : in web config keys.')
          if key.startswith('user/'): key = key.replace('user/', 'password/')
          host_config[key] = val
        just_these_be_configs[http_host] = host_config

      if be_paths:
        host_paths = just_these_webpaths.get(http_host, {})
        host_config = just_these_be_configs.get(http_host, {})
        rand_seed = '%s:%x' % (specs[specs.keys()[0]][BE_SECRET],
                               time.time()/3600)

        first = (len(host_paths.keys()) == 0) or be_path_prefix
        paranoid = host_config.get('hide', False)
        set_root = host_config.get('root', True)
        if len(be_paths) == 1:
          skip = len(os.path.dirname(be_paths[0]))
        else:
          skip = len(os.path.dirname(os.path.commonprefix(be_paths)+'X'))

        for path in be_paths:
          phead, ptail = os.path.split(path)
          if paranoid:
            if path.endswith('/'): path = path[0:-1]
            webpath = '%s/%s' % (sha1hex(rand_seed+os.path.dirname(path))[0:9],
                                  os.path.basename(path))
          elif (first and set_root and os.path.isdir(path)):
            webpath = ''
          elif (os.path.isdir(path) and
                not path.startswith('.') and
                not os.path.isabs(path)):
            webpath = path[skip:] + '/'
          elif path == '.':
            webpath = ''
          else:
            webpath = path[skip:]
          while webpath.endswith('/.'):
            webpath = webpath[:-2]
          host_paths[(be_path_prefix + '/' + webpath).replace('///', '/'
                                                    ).replace('//', '/')
                     ] = (WEB_POLICY_DEFAULT, os.path.abspath(path))
          first = False
        just_these_webpaths[http_host] = host_paths

    need_registration = {}
    for be in just_these_backends.values():
      if not be[BE_SECRET]:
        if self.kitesecret and be[BE_DOMAIN] == self.kitename:
          be[BE_SECRET] = self.kitesecret
        elif not self.kite_remove and not self.kite_disable:
          need_registration[be[BE_DOMAIN]] = True

    for domain in need_registration:
      if '.' not in domain:
        raise ConfigError('Not valid domain: %s' % domain)

    for domain in need_registration:
      result = self.RegisterNewKite(kitename=domain)
      if not result:
        raise ConfigError("Not sure what to do with %s, giving up." % domain)

      # Update the secrets...
      rdom, rsecret = result
      for be in just_these_backends.values():
        if be[BE_DOMAIN] == domain: be[BE_SECRET] = rsecret

      # Update the kite names themselves, if they changed.
      if rdom != domain:
        for bid in just_these_backends.keys():
          nbid = bid.replace(':'+domain, ':'+rdom)
          if nbid != bid:
            just_these_backends[nbid] = just_these_backends[bid]
            just_these_backends[nbid][BE_DOMAIN] = rdom
            del just_these_backends[bid]

    if just_these_backends.keys():
      if self.kite_add:
        self.backends.update(just_these_backends)
      elif self.kite_remove:
        try:
          for bid in just_these_backends:
            be = self.backends[bid]
            if be[BE_PROTO] in ('http', 'http2', 'http3'):
              http_host = '%s/%s' % (be[BE_DOMAIN], be[BE_PORT] or '80')
              if http_host in self.ui_paths: del self.ui_paths[http_host]
              if http_host in self.be_config: del self.be_config[http_host]
            del self.backends[bid]
        except KeyError:
          raise ConfigError('No such kite: %s' % bid)
      elif self.kite_disable:
        try:
          for bid in just_these_backends:
            self.backends[bid][BE_STATUS] = BE_STATUS_DISABLED
        except KeyError:
          raise ConfigError('No such kite: %s' % bid)
      elif self.kite_only:
        for be in self.backends.values(): be[BE_STATUS] = BE_STATUS_DISABLED
        self.backends.update(just_these_backends)
      else:
        # Nothing explictly requested: 'only' behavior with a twist;
        # If kites are new, don't make disables persist on save.
        for be in self.backends.values():
          be[BE_STATUS] = (need_registration and BE_STATUS_DISABLE_ONCE
                                              or BE_STATUS_DISABLED)
        self.backends.update(just_these_backends)

      self.ui_paths.update(just_these_webpaths)
      self.be_config.update(just_these_be_configs)

    return self

  def GetServiceXmlRpc(self):
    service = self.service_xmlrpc
    return xmlrpclib.ServerProxy(self.service_xmlrpc, None, None, False)

  def _KiteInfo(self, kitename):
    is_service_domain = kitename and SERVICE_DOMAIN_RE.search(kitename)
    is_subdomain_of = is_cname_for = is_cname_ready = False
    secret = None

    for be in self.backends.values():
      if be[BE_SECRET] and (be[BE_DOMAIN] == kitename):
        secret = be[BE_SECRET]

    if is_service_domain:
      parts = kitename.split('.')
      if '-' in parts[0]:
        parts[0] = '-'.join(parts[0].split('-')[1:])
        is_subdomain_of = '.'.join(parts)
      elif len(parts) > 3:
        is_subdomain_of = '.'.join(parts[1:])

    elif kitename:
      try:
        (hn, al, ips) = socket.gethostbyname_ex(kitename)
        if hn != kitename and SERVICE_DOMAIN_RE.search(hn):
          is_cname_for = hn
      except:
        pass

    return (secret, is_subdomain_of, is_service_domain,
            is_cname_for, is_cname_ready)

  def RegisterNewKite(self, kitename=None, first=False,
                            ask_be=False, autoconfigure=False):
    registered = False
    if kitename:
      (secret, is_subdomain_of, is_service_domain,
       is_cname_for, is_cname_ready) = self._KiteInfo(kitename)
      if secret:
        self.ui.StartWizard('Updating kite: %s' % kitename)
        registered = True
      else:
        self.ui.StartWizard('Creating kite: %s' % kitename)
    else:
      if first:
        self.ui.StartWizard('Create your first kite')
      else:
        self.ui.StartWizard('Creating a new kite')
      is_subdomain_of = is_service_domain = False
      is_cname_for = is_cname_ready = False

    # This is the default...
    be_specs = ['http:%s:localhost:80']

    service = self.GetServiceXmlRpc()
    service_accounts = {}
    if self.kitename and self.kitesecret:
      service_accounts[self.kitename] = self.kitesecret

    for be in self.backends.values():
      if SERVICE_DOMAIN_RE.search(be[BE_DOMAIN]):
        if be[BE_DOMAIN] == is_cname_for:
          is_cname_ready = True
        if be[BE_SECRET] not in service_accounts.values():
          service_accounts[be[BE_DOMAIN]] = be[BE_SECRET]
    service_account_list = service_accounts.keys()

    if registered:
      state = ['choose_backends']
    if service_account_list:
      state = ['choose_kite_account']
    else:
      state = ['use_service_question']
    history = []

    def Goto(goto, back_skips_current=False):
      if not back_skips_current: history.append(state[0])
      state[0] = goto
    def Back():
      if history:
        state[0] = history.pop(-1)
      else:
        Goto('abort')

    register = is_cname_for or kitename
    account = email = None
    while 'end' not in state:
      try:
        if 'use_service_question' in state:
          ch = self.ui.AskYesNo('Use the PageKite.net service?',
                                pre=['<b>Welcome to PageKite!</b>',
                                     '',
                                     'Please answer a few quick questions to',
                                     'create your first kite.',
                                     '',
                                     'By continuing, you agree to play nice',
                                     'and abide by the Terms of Service at:',
                                     '- <a href="%s">%s</a>' % (SERVICE_TOS_URL, SERVICE_TOS_URL)],
                                default=True, back=-1, no='Abort')
          if ch is True:
            self.SetServiceDefaults(clobber=False)
            if not kitename:
              Goto('service_signup_email')
            elif is_cname_for and is_cname_ready:
              register = kitename
              Goto('service_signup_email')
            elif is_service_domain:
              register = is_cname_for or kitename
              if is_subdomain_of:
                # FIXME: Shut up if parent is already in local config!
                Goto('service_signup_is_subdomain')
              else:
                Goto('service_signup_email')
            else:
              Goto('service_signup_bad_domain')
          else:
            Goto('manual_abort')

        elif 'service_login_email' in state:
          p = None
          while not email or not p:
            (email, p) = self.ui.AskLogin('Please log on ...', pre=[
                                            'By logging on to %s,' % self.service_provider,
                                            'you will be able to use this kite',
                                            'with your pre-existing account.'
                                          ], email=email, back=(email, False))
            if email and p:
              try:
                self.ui.Working('Logging on to your account')
                service_accounts[email] = service.getSharedSecret(email, p)
                # FIXME: Should get the list of preconfigured kites via. RPC
                #        so we don't try to create something that already
                #        exists?  Or should the RPC not just not complain?
                account = email
                Goto('create_kite')
              except:
                email = p = None
                self.ui.Tell(['Login failed! Try again?'], error=True)
            if p is False:
              Back()
              break

        elif ('service_signup_is_subdomain' in state):
          ch = self.ui.AskYesNo('Use this name?',
                                pre=['%s is a sub-domain.' % kitename, '',
                                     '<b>NOTE:</b> This process will fail if you',
                                     'have not already registered the parent',
                                     'domain, %s.' % is_subdomain_of],
                                default=True, back=-1)
          if ch is True:
            if account:
              Goto('create_kite')
            elif email:
              Goto('service_signup')
            else:
              Goto('service_signup_email')
          elif ch is False:
            Goto('service_signup_kitename')
          else:
            Back()

        elif ('service_signup_bad_domain' in state or
              'service_login_bad_domain' in state):
          if is_cname_for:
            alternate = is_cname_for
            ch = self.ui.AskYesNo('Create both?',
                                  pre=['%s is a CNAME for %s.' % (kitename, is_cname_for)],
                                  default=True, back=-1)
          else:
            alternate = kitename.split('.')[-2]+'.'+SERVICE_DOMAINS[0]
            ch = self.ui.AskYesNo('Try to create %s instead?' % alternate,
                                  pre=['Sorry, %s is not a valid service domain.' % kitename],
                                  default=True, back=-1)
          if ch is True:
            register = alternate
            Goto(state[0].replace('bad_domain', 'email'))
          elif ch is False:
            register = alternate = kitename = False
            Goto('service_signup_kitename', back_skips_current=True)
          else:
            Back()

        elif 'service_signup_email' in state:
          email = self.ui.AskEmail('<b>What is your e-mail address?</b>',
                                   pre=['We need to be able to contact you',
                                        'now and then with news about the',
                                        'service and your account.',
                                        '',
                                        'Your details will be kept private.'],
                                   back=False)
          if email and register:
            Goto('service_signup')
          elif email:
            Goto('service_signup_kitename')
          else:
            Back()

        elif ('service_signup_kitename' in state or
              'service_ask_kitename' in state):
          try:
            self.ui.Working('Fetching list of available domains')
            domains = service.getAvailableDomains('', '')
          except:
            domains = ['.%s' % x for x in SERVICE_DOMAINS_SIGNUP]

          ch = self.ui.AskKiteName(domains, 'Name this kite:',
                                 pre=['Your kite name becomes the public name',
                                      'of your personal server or web-site.',
                                      '',
                                      'Names are provided on a first-come,',
                                      'first-serve basis. You can create more',
                                      'kites with different names later on.'],
                                 back=False)
          if ch:
            kitename = register = ch
            (secret, is_subdomain_of, is_service_domain,
             is_cname_for, is_cname_ready) = self._KiteInfo(ch)
            if secret:
              self.ui.StartWizard('Updating kite: %s' % kitename)
              registered = True
            else:
              self.ui.StartWizard('Creating kite: %s' % kitename)
            Goto('choose_backends')
          else:
            Back()

        elif 'choose_backends' in state:
          if ask_be and autoconfigure:
            skip = False
            ch = self.ui.AskBackends(kitename, ['http'], ['80'], [],
                                     'Enable which service?', back=False, pre=[
                                  'You control which of your files or servers',
                                  'PageKite exposes to the Internet. ',
                                     ], default=','.join(be_specs))
            if ch:
              be_specs = ch.split(',')
          else:
            skip = ch = True

          if ch:
            if registered:
              Goto('create_kite', back_skips_current=skip)
            elif is_subdomain_of:
              Goto('service_signup_is_subdomain', back_skips_current=skip)
            elif account:
              Goto('create_kite', back_skips_current=skip)
            elif email:
              Goto('service_signup', back_skips_current=skip)
            else:
              Goto('service_signup_email', back_skips_current=skip)
          else:
            Back()

        elif 'service_signup' in state:
          try:
            self.ui.Working('Signing up')
            details = service.signUp(email, register)
            if details.get('secret', False):
              service_accounts[email] = details['secret']
              self.ui.AskYesNo('Continue?', pre=[
                '<b>Your kite is ready to fly!</b>',
                '',
                '<b>Note:</b> To complete the signup process,',
                'check your e-mail (and spam folders) for',
                'activation instructions. You can give',
                'PageKite a try first, but un-activated',
                'accounts are disabled after %d minutes.' % details['timeout'],
              ], yes='Finish', no=False, default=True)
              self.ui.EndWizard()
              if autoconfigure:
                for be_spec in be_specs:
                  self.backends.update(self.ArgToBackendSpecs(
                                                    be_spec % register,
                                                    secret=details['secret']))
              self.added_kites = True
              return (register, details['secret'])
            else:
              error = details.get('error', 'unknown')
          except IOError:
            error = 'network'
          except:
            error = '%s' % (sys.exc_info(), )

          if error == 'pleaselogin':
            self.ui.ExplainError(error, 'Signup failed!',
                                 subject=email)
            Goto('service_login_email', back_skips_current=True)
          elif error == 'email':
            self.ui.ExplainError(error, 'Signup failed!',
                                 subject=register)
            Goto('service_login_email', back_skips_current=True)
          elif error in ('domain', 'domaintaken', 'subdomain'):
            self.ui.ExplainError(error, 'Invalid domain!',
                                 subject=register)
            register, kitename = None, None
            Goto('service_signup_kitename', back_skips_current=True)
          elif error == 'network':
            self.ui.ExplainError(error, 'Network error!',
                                 subject=self.service_provider)
            Goto('service_signup', back_skips_current=True)
          else:
            self.ui.ExplainError(error, 'Unknown problem!')
            print 'FIXME!  Error is %s' % error
            Goto('abort')

        elif 'choose_kite_account' in state:
          choices = service_account_list[:]
          choices.append('Use another service provider')
          justdoit = (len(service_account_list) == 1)
          if justdoit:
            ch = 1
          else:
            ch = self.ui.AskMultipleChoice(choices, 'Register with',
                                       pre=['Choose an account for this kite:'],
                                           default=1)
          account = choices[ch-1]
          if ch == len(choices):
            Goto('manual_abort')
          elif kitename:
            Goto('choose_backends', back_skips_current=justdoit)
          else:
            Goto('service_ask_kitename', back_skips_current=justdoit)

        elif 'create_kite' in state:
          secret = service_accounts[account]
          subject = None
          cfgs = {}
          result = {}
          error = None
          try:
            if registered and kitename and secret:
              pass
            elif is_cname_for and is_cname_ready:
              self.ui.Working('Creating your kite')
              subject = kitename
              result = service.addCnameKite(account, secret, kitename)
              time.sleep(2) # Give the service side a moment to replicate...
            else:
              self.ui.Working('Creating your kite')
              subject = register
              result = service.addKite(account, secret, register)
              time.sleep(2) # Give the service side a moment to replicate...
              for be_spec in be_specs:
                cfgs.update(self.ArgToBackendSpecs(be_spec % register,
                                                   secret=secret))
              if is_cname_for == register and 'error' not in result:
                subject = kitename
                result.update(service.addCnameKite(account, secret, kitename))

            error = result.get('error', None)
            if not error:
              for be_spec in be_specs:
                cfgs.update(self.ArgToBackendSpecs(be_spec % kitename,
                                                   secret=secret))
          except Exception, e:
            error = '%s' % e

          if error:
            self.ui.ExplainError(error, 'Kite creation failed!',
                                 subject=subject)
            Goto('abort')
          else:
            self.ui.Tell(['Success!'])
            self.ui.EndWizard()
            if autoconfigure: self.backends.update(cfgs)
            self.added_kites = True
            return (register or kitename, secret)

        elif 'manual_abort' in state:
          if self.ui.Tell(['Aborted!', '',
            'Please manually add information about your',
            'kites and front-ends to the configuration file:',
            '', ' %s' % self.rcfile],
                          error=True, back=False) is False:
            Back()
          else:
            self.ui.EndWizard()
            if self.ui.ALLOWS_INPUT: return None
            sys.exit(0)

        elif 'abort' in state:
          self.ui.EndWizard()
          if self.ui.ALLOWS_INPUT: return None
          sys.exit(0)

        else:
          raise ConfigError('Unknown state: %s' % state)

      except KeyboardInterrupt:
        sys.stderr.write('\n')
        if history:
          Back()
        else:
          raise KeyboardInterrupt()

    self.ui.EndWizard()
    return None

  def CheckConfig(self):
    if self.ui_sspec: self.BindUiSspec()
    if not self.servers_manual and not self.servers_auto and not self.isfrontend:
      if not self.servers and not self.ui.ALLOWS_INPUT:
        raise ConfigError('Nothing to do!  List some servers, or run me as one.')
    return self

  def CheckAllTunnels(self, conns):
    missing = []
    for backend in self.backends:
      proto, domain = backend.split(':')
      if not conns.Tunnel(proto, domain):
        missing.append(domain)
    if missing:
      self.FallDown('No tunnel for %s' % missing, help=False)

  TMP_UUID_MAP = {
    '2400:8900::f03c:91ff:feae:ea35:443': '106.187.99.46:443',
    '2a01:7e00::f03c:91ff:fe96:234:443': '178.79.140.143:443',
    '2600:3c03::f03c:91ff:fe96:2bf:443': '50.116.52.206:443',
    '2600:3c01::f03c:91ff:fe96:257:443': '173.230.155.164:443',
    '69.164.211.158:443': '50.116.52.206:443',
  }
  def Ping(self, host, port):
    cid = uuid = '%s:%s' % (host, port)

    if self.servers_no_ping:
      return (0, uuid)

    while ((cid not in self.ping_cache) or
           (len(self.ping_cache[cid]) < 2) or
           (time.time()-self.ping_cache[cid][0][0] > 60)):

      start = time.time()
      try:
        try:
          if ':' in host:
            fd = socks.socksocket(socket.AF_INET6, socket.SOCK_STREAM)
          else:
            fd = socks.socksocket(socket.AF_INET, socket.SOCK_STREAM)
        except:
          fd = socks.socksocket(socket.AF_INET, socket.SOCK_STREAM)

        try:
          fd.settimeout(3.0) # Missing in Python 2.2
        except:
          fd.setblocking(1)

        fd.connect((host, port))
        fd.send('HEAD / HTTP/1.0\r\n\r\n')
        data = fd.recv(1024)
        fd.close()

      except Exception, e:
        logging.LogDebug('Ping %s:%s failed: %s' % (host, port, e))
        return (100000, uuid)

      elapsed = (time.time() - start)
      try:
        uuid = data.split('X-PageKite-UUID: ')[1].split()[0]
      except:
        uuid = self.TMP_UUID_MAP.get(uuid, uuid)

      if cid not in self.ping_cache:
        self.ping_cache[cid] = []
      elif len(self.ping_cache[cid]) > 10:
        self.ping_cache[cid][8:] = []

      self.ping_cache[cid][0:0] = [(time.time(), (elapsed, uuid))]

    window = min(3, len(self.ping_cache[cid]))
    pingval = sum([e[1][0] for e in self.ping_cache[cid][:window]])/window
    uuid = self.ping_cache[cid][0][1][1]

    logging.LogDebug(('Pinged %s:%s: %f [win=%s, uuid=%s]'
                      ) % (host, port, pingval, window, uuid))
    return (pingval, uuid)

  def GetHostIpAddrs(self, host):
    rv = []
    try:
      info = socket.getaddrinfo(host, 0, socket.AF_UNSPEC, socket.SOCK_STREAM)
      rv = [i[4][0] for i in info]
    except AttributeError:
      rv = socket.gethostbyname_ex(host)[2]
    return rv

  def CachedGetHostIpAddrs(self, host):
    now = int(time.time())

    if host in self.dns_cache:
      # FIXME: This number (900) is 3x the pagekite.net service DNS TTL, which
      # should be about right.  BUG: nothing keeps those two numbers in sync!
      # This number must be larger, or we prematurely disconnect frontends.
      for exp in [t for t in self.dns_cache[host] if t < now-900]:
        del self.dns_cache[host][exp]
    else:
      self.dns_cache[host] = {}

    try:
      self.dns_cache[host][now] = self.GetHostIpAddrs(host)
    except:
      logging.LogDebug('DNS lookup failed for %s' % host)

    ips = {}
    for ipaddrs in self.dns_cache[host].values():
      for ip in ipaddrs:
        ips[ip] = 1
    return ips.keys()

  def GetActiveBackends(self):
    active = []
    for bid in self.backends:
      (proto, bdom) = bid.split(':')
      if (self.backends[bid][BE_STATUS] not in BE_INACTIVE and
          self.backends[bid][BE_SECRET] and
          not bdom.startswith('*')):
        active.append(bid)
    return active

  def ChooseFrontEnds(self):
    self.servers = []
    self.servers_preferred = []
    self.last_frontend_choice = time.time()

    servers_all = {}
    servers_pref = {}

    # Enable internal loopback
    if self.isfrontend:
      need_loopback = False
      for be in self.backends.values():
        if be[BE_BHOST]:
          need_loopback = True
      if need_loopback:
        servers_all['loopback'] = servers_pref['loopback'] = LOOPBACK_FE

    # Convert the hostnames into IP addresses...
    for server in self.servers_manual:
      (host, port) = server.split(':')
      ipaddrs = self.CachedGetHostIpAddrs(host)
      if ipaddrs:
        ptime, uuid = self.Ping(ipaddrs[0], int(port))
        server = '%s:%s' % (ipaddrs[0], port)
        if server not in self.servers_never:
          servers_all[uuid] = servers_pref[uuid] = server

    # Lookup and choose from the auto-list (and our old domain).
    if self.servers_auto:
      (count, domain, port) = self.servers_auto

      # First, check for old addresses and always connect to those.
      selected = {}
      if not self.servers_new_only:
        for bid in self.GetActiveBackends():
          (proto, bdom) = bid.split(':')
          for ip in self.CachedGetHostIpAddrs(bdom):
            # FIXME: What about IPv6 localhost?
            if not ip.startswith('127.'):
              server = '%s:%s' % (ip, port)
              if server not in self.servers_never:
                servers_all[self.Ping(ip, int(port))[1]] = server

      try:
        ips = [ip for ip in self.CachedGetHostIpAddrs(domain)
               if ('%s:%s' % (ip, port)) not in self.servers_never]
        pings = [self.Ping(ip, port) for ip in ips]
      except Exception, e:
        logging.LogDebug('Unreachable: %s, %s' % (domain, e))
        ips = pings = []

      while count > 0 and ips:
        mIdx = pings.index(min(pings))
        if pings[mIdx][0] > 60:
          # This is worthless data, abort.
          break
        else:
          count -= 1
          uuid = pings[mIdx][1]
          server = '%s:%s' % (ips[mIdx], port)
          if uuid not in servers_all:
            servers_all[uuid] = server
          if uuid not in servers_pref:
            servers_pref[uuid] = ips[mIdx]
          del pings[mIdx]
          del ips[mIdx]

    self.servers = servers_all.values()
    self.servers_preferred = servers_pref.values()
    logging.LogDebug('Preferred: %s' % ', '.join(self.servers_preferred))

  def ConnectFrontend(self, conns, server):
    self.ui.Status('connect', color=self.ui.YELLOW,
                   message='Front-end connect: %s' % server)
    tun = Tunnel.BackEnd(server, self.backends, self.require_all, conns)
    if tun:
      tun.filters.append(HttpHeaderFilter(self.ui))
      if not self.insecure:
        tun.filters.append(HttpSecurityFilter(self.ui))
        if self.watch_level[0] is not None:
          tun.filters.append(TunnelWatcher(self.ui, self.watch_level))
        logging.Log([('connect', server)])
        return True
      else:
        logging.LogInfo('Failed to connect', [('FE', server)])
        self.ui.Notify('Failed to connect to %s' % server,
                       prefix='!', color=self.ui.YELLOW)
        return False

  def DisconnectFrontend(self, conns, server):
    logging.Log([('disconnect', server)])
    kill = []
    for bid in conns.tunnels:
      for tunnel in conns.tunnels[bid]:
        if (server == tunnel.server_info[tunnel.S_NAME] and
            tunnel.countas.startswith('frontend')):
          kill.append(tunnel)
    for tunnel in kill:
      if len(tunnel.users.keys()) < 1:
        tunnel.Die()
    return kill and True or False

  def CreateTunnels(self, conns):
    live_servers = conns.TunnelServers()
    failures = 0
    connections = 0

    if len(self.GetActiveBackends()) > 0:
      if self.last_frontend_choice < time.time()-FE_PING_INTERVAL:
        self.servers = []
      if not self.servers or len(self.servers) > len(live_servers):
        self.ChooseFrontEnds()
    else:
      self.servers_preferred = []
      self.servers = []

    if not self.servers:
      logging.LogDebug('Not sure which servers to contact, making no changes.')
      return 0, 0

    for server in self.servers:
      if server not in live_servers:
        if server == LOOPBACK_FE:
          loop = LoopbackTunnel.Loop(conns, self.backends)
          loop.filters.append(HttpHeaderFilter(self.ui))
          if not self.insecure:
            loop.filters.append(HttpSecurityFilter(self.ui))
        else:
          if self.ConnectFrontend(conns, server):
            connections += 1
          else:
            failures += 1

    for server in live_servers:
      if server not in self.servers and server not in self.servers_preferred:
        if self.DisconnectFrontend(conns, server):
          connections += 1

    if self.dyndns:
      ddns_fmt, ddns_args = self.dyndns

      domains = {}
      for bid in self.backends.keys():
        proto, domain = bid.split(':')
        if domain not in domains:
          domains[domain] = (self.backends[bid][BE_SECRET], [])

        if bid in conns.tunnels:
          ips, bips = [], []
          for tunnel in conns.tunnels[bid]:
            ip = rsplit(':', tunnel.server_info[tunnel.S_NAME])[0]
            if not ip == LOOPBACK_HN and not tunnel.read_eof:
              if not self.servers_preferred or ip in self.servers_preferred:
                ips.append(ip)
              else:
                bips.append(ip)

          for ip in (ips or bips):
            if ip not in domains[domain]:
              domains[domain][1].append(ip)

      updates = {}
      for domain, (secret, ips) in domains.iteritems():
        if ips:
          iplist = ','.join(ips)
          payload = '%s:%s' % (domain, iplist)
          args = {}
          args.update(ddns_args)
          args.update({
            'domain': domain,
            'ip': ips[0],
            'ips': iplist,
            'sign': signToken(secret=secret, payload=payload, length=100)
          })
          # FIXME: This may fail if different front-ends support different
          #        protocols. In practice, this should be rare.
          updates[payload] = ddns_fmt % args

      last_updates = self.last_updates
      self.last_updates = []
      for update in updates:
        if update in last_updates:
          # Was successful last time, no point in doing it again.
          self.last_updates.append(update)
        else:
          domain, ips = update.split(':', 1)
          try:
            self.ui.Status('dyndns', color=self.ui.YELLOW,
                                     message='Updating DNS for %s...' % domain)
            result = ''.join(urllib.urlopen(updates[update]).readlines())
            if result.startswith('good') or result.startswith('nochg'):
              logging.Log([('dyndns', result), ('data', update)])
              self.SetBackendStatus(update.split(':')[0],
                                    sub=BE_STATUS_ERR_DNS)
              self.last_updates.append(update)
              # Success!  Make sure we remember these IP were live.
              if domain not in self.dns_cache:
                self.dns_cache[domain] = {}
              self.dns_cache[domain][int(time.time())] = ips.split(',')
            else:
              logging.LogInfo('DynDNS update failed: %s' % result, [('data', update)])
              self.SetBackendStatus(update.split(':')[0],
                                    add=BE_STATUS_ERR_DNS)
              failures += 1
          except Exception, e:
            logging.LogInfo('DynDNS update failed: %s' % e, [('data', update)])
            if logging.DEBUG_IO: traceback.print_exc(file=sys.stderr)
            self.SetBackendStatus(update.split(':')[0],
                                  add=BE_STATUS_ERR_DNS)
            # Hmm, the update may have succeeded - assume the "worst".
            self.dns_cache[domain][int(time.time())] = ips.split(',')
            failures += 1

    return failures, connections

  def LogTo(self, filename, close_all=True, dont_close=[]):
    if filename == 'memory':
      logging.Log = logging.LogToMemory
      filename = self.devnull

    elif filename == 'syslog':
      logging.Log = logging.LogSyslog
      filename = self.devnull
      compat.syslog.openlog(self.progname, syslog.LOG_PID, syslog.LOG_DAEMON)

    else:
      logging.Log = logging.LogToFile

    if filename in ('stdio', 'stdout'):
      try:
        logging.LogFile = os.fdopen(sys.stdout.fileno(), 'w', 0)
      except:
        logging.LogFile = sys.stdout
    else:
      try:
        logging.LogFile = fd = open(filename, "a", 0)
        os.dup2(fd.fileno(), sys.stdout.fileno())
        if not self.ui.WANTS_STDERR:
          os.dup2(fd.fileno(), sys.stdin.fileno())
          os.dup2(fd.fileno(), sys.stderr.fileno())
      except Exception, e:
        raise ConfigError('%s' % e)

  def Daemonize(self):
    # Fork once...
    if os.fork() != 0: os._exit(0)

    # Fork twice...
    os.setsid()
    if os.fork() != 0: os._exit(0)

  def ProcessWritable(self, oready):
    if logging.DEBUG_IO:
      print '\n=== Ready for Write: %s' % [o and o.fileno() or ''
                                           for o in oready]
    for osock in oready:
      if osock:
        conn = self.conns.Connection(osock)
        if conn and not conn.Send([], try_flush=True):
          conn.Die(discard_buffer=True)

  def ProcessReadable(self, iready, throttle):
    if logging.DEBUG_IO:
      print '\n=== Ready for Read: %s' % [i and i.fileno() or None
                                          for i in iready]
    for isock in iready:
      if isock is not None:
        conn = self.conns.Connection(isock)
        if conn and not (conn.fd and conn.ReadData(maxread=throttle)):
          conn.Die(discard_buffer=True)

  def ProcessDead(self, epoll=None):
    for conn in self.conns.DeadConns():
      if epoll and conn.fd:
        try:
          epoll.unregister(conn.fd)
        except (IOError, TypeError):
          pass
      conn.Cleanup()
      self.conns.Remove(conn)

  def Select(self, epoll, waittime):
    iready = oready = eready = None
    isocks, osocks = self.conns.Readable(), self.conns.Blocked()
    try:
      if isocks or osocks:
        iready, oready, eready = select.select(isocks, osocks, [], waittime)
      else:
        # Windoes does not seem to like empty selects, so we do this instead.
        time.sleep(waittime/2)
    except KeyboardInterrupt:
      raise
    except:
      logging.LogError('Error in select(%s/%s): %s' % (isocks, osocks,
                                                       format_exc()))
      self.conns.CleanFds()
      self.last_loop -= 1

    now = time.time()
    if not iready and not oready:
      if (isocks or osocks) and (now < self.last_loop + 1):
        logging.LogError('Spinning, pausing ...')
        time.sleep(0.1)

    return iready, oready, eready

  def Epoll(self, epoll, waittime):
    fdc = {}
    now = time.time()
    evs = []
    try:
      bbc = 0
      for c in self.conns.conns:
        try:
          if c.IsDead():
            epoll.unregister(c.fd)
          else:
            fdc[c.fd.fileno()] = c.fd
            mask = 0
            if c.IsBlocked():
              bbc += len(c.write_blocked)
              mask |= select.EPOLLOUT
            if c.IsReadable(now):
              mask |= select.EPOLLIN
            if mask:
              try:
                try:
                  epoll.modify(c.fd, mask)
                except IOError:
                  epoll.register(c.fd, mask)
              except (IOError, TypeError):
                evs.append((c.fd, select.EPOLLHUP))
                logging.LogError('Epoll mod/reg: %s(%s), mask=0x%x'
                                 '' % (c, c.fd, mask))
            else:
              epoll.unregister(c.fd)
        except (IOError, TypeError):
          # Failing to unregister is FINE, we don't complain about that.
          pass

      common.buffered_bytes[0] = bbc
      evs.extend(epoll.poll(waittime))
    except IOError:
      pass
    except KeyboardInterrupt:
      epoll.close()
      raise

    rmask = select.EPOLLIN | select.EPOLLHUP
    iready = [fdc.get(e[0]) for e in evs if e[1] & rmask]
    oready = [fdc.get(e[0]) for e in evs if e[1] & select.EPOLLOUT]

    return iready, oready, []

  def CreatePollObject(self):
    try:
      epoll = select.epoll()
      mypoll = self.Epoll
    except:
      epoll = None
      mypoll = self.Select
    return epoll, mypoll

  def Loop(self):
    self.conns.start()
    if self.ui_httpd: self.ui_httpd.start()
    if self.tunnel_manager: self.tunnel_manager.start()
    if self.ui_comm: self.ui_comm.start()

    epoll, mypoll = self.CreatePollObject()
    self.last_barf = self.last_loop = time.time()

    logging.LogDebug('Entering main %s loop' % (epoll and 'epoll' or 'select'))
    while self.keep_looping:
      iready, oready, eready = mypoll(epoll, 1.1)
      now = time.time()

      if oready:
        self.ProcessWritable(oready)

      if common.buffered_bytes[0] < 1024 * self.buffer_max:
        throttle = None
      else:
        logging.LogDebug("FIXME: Nasty pause to let buffers clear!")
        time.sleep(0.1)
        throttle = 1024

      if iready:
        self.ProcessReadable(iready, throttle)

      self.ProcessDead(epoll)
      self.last_loop = now

      if now - self.last_barf > (logging.DEBUG_IO and 15 or 600):
        self.last_barf = now
        if epoll:
          epoll.close()
        epoll, mypoll = self.CreatePollObject()
        if logging.DEBUG_IO:
          logging.LogDebug('Selectable map: %s' % SELECTABLES)

    if epoll:
      epoll.close()

  def Start(self, howtoquit='CTRL+C = Stop'):
    conns = self.conns = self.conns or Connections(self)

    # If we are going to spam stdout with ugly crap, then there is no point
    # attempting the fancy stuff. This also makes us backwards compatible
    # for the most part.
    if self.logfile == 'stdio':
      if not self.ui.DAEMON_FRIENDLY: self.ui = NullUi()

    # Announce that we've started up!
    self.ui.Status('startup', message='Starting up...')
    self.ui.Notify(('Hello! This is %s v%s.'
                    ) % (self.progname, APPVER),
                    prefix='>', color=self.ui.GREEN,
                    alignright='[%s]' % howtoquit)
    config_report = [('started', sys.argv[0]), ('version', APPVER),
                     ('platform', sys.platform),
                     ('argv', ' '.join(sys.argv[1:])),
                     ('ca_certs', self.ca_certs)]
    for optf in self.rcfiles_loaded:
      config_report.append(('optfile_%s' % optf, 'ok'))
    logging.Log(config_report)

    if not socks.HAVE_SSL:
      self.ui.Notify('SECURITY WARNING: No SSL support was found, tunnels are insecure!',
                     prefix='!', color=self.ui.WHITE)
      self.ui.Notify('Please install either pyOpenSSL or python-ssl.',
                     prefix='!', color=self.ui.WHITE)

    # Create global secret
    self.ui.Status('startup', message='Collecting entropy for a secure secret...')
    logging.LogInfo('Collecting entropy for a secure secret.')
    globalSecret()
    self.ui.Status('startup', message='Starting up...')

    # Create the UI Communicator
    self.ui_comm = UiCommunicator(self, conns)

    try:

      # Set up our listeners if we are a server.
      if self.isfrontend:
        self.ui.Notify('This is a PageKite front-end server.')
        for port in self.server_ports:
          Listener(self.server_host, port, conns, acl=self.accept_acl_file)
        for port in self.server_raw_ports:
          if port != VIRTUAL_PN and port > 0:
            Listener(self.server_host, port, conns,
                     connclass=RawConn, acl=self.accept_acl_file)

      if self.ui_port:
        Listener('127.0.0.1', self.ui_port, conns,
                 connclass=UiConn, acl=self.accept_acl_file)

      # Create the Tunnel Manager
      self.tunnel_manager = TunnelManager(self, conns)

    except Exception, e:
      self.LogTo('stdio')
      logging.FlushLogMemory()
      if logging.DEBUG_IO:
        traceback.print_exc(file=sys.stderr)
      raise ConfigError('Configuring listeners: %s ' % e)

    # Configure logging
    if self.logfile:
      keep_open = [s.fd.fileno() for s in conns.conns]
      if self.ui_httpd: keep_open.append(self.ui_httpd.httpd.socket.fileno())
      self.LogTo(self.logfile, dont_close=keep_open)

    elif not sys.stdout.isatty():
      # Preserve sane behavior when not run at the console.
      self.LogTo('stdio')

    # Flush in-memory log, if necessary
    logging.FlushLogMemory()

    # Set up SIGHUP handler.
    if self.logfile:
      try:
        import signal
        def reopen(x,y):
          if self.logfile:
            self.LogTo(self.logfile, close_all=False)
            logging.LogDebug('SIGHUP received, reopening: %s' % self.logfile)
        signal.signal(signal.SIGHUP, reopen)
      except Exception:
        logging.LogError('Warning: signal handler unavailable, logrotate will not work.')

    # Disable compression in OpenSSL
    if socks.HAVE_SSL and not self.enable_sslzlib:
      socks.DisableSSLCompression()

    # Daemonize!
    if self.daemonize:
      self.Daemonize()

    # Create PID file
    if self.pidfile:
      pf = open(self.pidfile, 'w')
      pf.write('%s\n' % os.getpid())
      pf.close()

    # Do this after creating the PID and log-files.
    if self.daemonize:
      os.chdir('/')

    # Drop privileges, if we have any.
    if self.setgid:
      os.setgid(self.setgid)
    if self.setuid:
      os.setuid(self.setuid)
    if self.setuid or self.setgid:
      logging.Log([('uid', os.getuid()), ('gid', os.getgid())])

    # Make sure we have what we need
    if self.require_all:
      self.CreateTunnels(conns)
      self.CheckAllTunnels(conns)

    # Finally, run our select loop.
    self.Loop()

    self.ui.Status('exiting', message='Stopping...')
    logging.Log([('stopping', 'pagekite.py')])
    if self.ui_httpd:
      self.ui_httpd.quit()
    if self.ui_comm:
      self.ui_comm.quit()
    if self.tunnel_manager:
      self.tunnel_manager.quit()
    if self.conns:
      if self.conns.auth: self.conns.auth.quit()
      for conn in self.conns.conns:
        conn.Cleanup()


##[ Main ]#####################################################################

def Main(pagekite, configure, uiclass=NullUi,
                              progname=None, appver=APPVER,
                              http_handler=None, http_server=None):
  crashes = 0
  shell_mode = None
  while True:
    ui = uiclass()
    logging.ResetLog()
    pk = pagekite(ui=ui, http_handler=http_handler, http_server=http_server)
    try:
      try:
        try:
          configure(pk)
        except SystemExit, status:
          sys.exit(status)
        except Exception, e:
          raise ConfigError(e)

        shell_mode = shell_mode or pk.shell
        if shell_mode is not True:
          pk.Start()

      except (ConfigError, getopt.GetoptError), msg:
        pk.FallDown(msg, help=(not shell_mode), noexit=shell_mode)
        if shell_mode:
          shell_mode = 'more'

      except KeyboardInterrupt, msg:
        pk.FallDown(None, help=False, noexit=True)
        if shell_mode:
          shell_mode = 'auto'
        else:
          return

    except SystemExit, status:
      if shell_mode:
        shell_mode = 'more'
      else:
        sys.exit(status)

    except Exception, msg:
      traceback.print_exc(file=sys.stderr)
      if pk.crash_report_url:
        try:
          print 'Submitting crash report to %s' % pk.crash_report_url
          logging.LogDebug(''.join(urllib.urlopen(pk.crash_report_url,
                                          urllib.urlencode({
                                            'platform': sys.platform,
                                            'appver': APPVER,
                                            'crash': format_exc()
                                          })).readlines()))
        except Exception, e:
          print 'FAILED: %s' % e

      pk.FallDown(msg, help=False, noexit=pk.main_loop)
      crashes = min(9, crashes+1)

    if shell_mode:
      crashes = 0
      try:
        sys.argv[1:] = Shell(pk, ui, shell_mode)
        shell_mode = 'more'
      except (KeyboardInterrupt, IOError, OSError):
        ui.Status('quitting')
        print
        return
    elif not pk.main_loop:
      return

    # Exponential fall-back.
    logging.LogDebug('Restarting in %d seconds...' % (2 ** crashes))
    time.sleep(2 ** crashes)


def Shell(pk, ui, shell_mode):
  import manual
  try:
    ui.Reset()
    if shell_mode != 'more':
      ui.StartWizard('The PageKite Shell')
      pre = [
        'Press ENTER to fly your kites or CTRL+C to quit.  Or, type some',
        'arguments to and try other things.  Type `help` for help.'
      ]
    else:
      pre = ''

    prompt = os.path.basename(sys.argv[0])
    while True:
      rv = ui.AskQuestion(prompt, prompt='  $', back=False, pre=pre
                          ).strip().split()
      ui.EndWizard(quietly=True)
      while rv and rv[0] in ('pagekite.py', prompt):
        rv.pop(0)
      if rv and rv[0] == 'help':
        ui.welcome = '>>> ' + ui.WHITE + ' '.join(rv) + ui.NORM
        ui.Tell(manual.HELP(rv[1:]).splitlines())
        pre = []
      elif rv and rv[0] == 'quit':
        raise KeyboardInterrupt()
      else:
        if rv and rv[0] in OPT_ARGS:
          rv[0] = '--'+rv[0]
        return rv
  finally:
    ui.EndWizard(quietly=True)
    print


def Configure(pk):
  if '--appver' in sys.argv:
    print '%s' % APPVER
    sys.exit(0)

  if '--clean' not in sys.argv and '--help' not in sys.argv:
    if os.path.exists(pk.rcfile):
      pk.ConfigureFromFile()

  friendly_mode = (('--friendly' in sys.argv) or
                   (sys.platform[:3] in ('win', 'os2', 'dar')))
  if friendly_mode and sys.stdout.isatty():
    pk.shell = (len(sys.argv) < 2) and 'auto'

  pk.Configure(sys.argv[1:])

  if '--settings' in sys.argv:
    pk.PrintSettings(safe=True)
    sys.exit(0)

  if not pk.backends.keys() and (not pk.kitesecret or not pk.kitename):
    if '--signup' in sys.argv or friendly_mode:
      pk.RegisterNewKite(autoconfigure=True, first=True)
    if friendly_mode:
      pk.save = True

  pk.CheckConfig()

  if pk.added_kites:
    if (pk.save or
        pk.ui.AskYesNo('Save settings to %s?' % pk.rcfile,
                       default=(len(pk.backends.keys()) > 0))):
      pk.SaveUserConfig()
    pk.servers_new_only = 'Once'
  elif pk.save:
    pk.SaveUserConfig(quiet=True)

  if ('--list' in sys.argv or
      pk.kite_add or pk.kite_remove or pk.kite_only or pk.kite_disable):
    pk.ListKites()
    sys.exit(0)

########NEW FILE########
__FILENAME__ = conns
"""
These are the Connection classes, relatively high level classes that handle
incoming or outgoing network connections.
"""
##############################################################################
LICENSE = """\
This file is part of pagekite.py.
Copyright 2010-2013, the Beanstalks Project ehf. and Bjarni Runar Einarsson

This program is free software: you can redistribute it and/or modify it under
the terms of the  GNU  Affero General Public License as published by the Free
Software Foundation, either version 3 of the License, or (at your option) any
later version.

This program is distributed in the hope that it will be useful,  but  WITHOUT
ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
FOR A PARTICULAR PURPOSE.  See the GNU Affero General Public License for more
details.

You should have received a copy of the GNU Affero General Public License
along with this program.  If not, see: <http://www.gnu.org/licenses/>
"""
##############################################################################
import socket
import sys
import threading
import time
import traceback

from pagekite.compat import *
from pagekite.common import *
import pagekite.common as common
import pagekite.logging as logging

from filters import HttpSecurityFilter
from selectables import *
from parsers import *
from proto import *


class Tunnel(ChunkParser):
  """A Selectable representing a PageKite tunnel."""

  S_NAME = 0
  S_PORTS = 1
  S_RAW_PORTS = 2
  S_PROTOS = 3
  S_ADD_KITES = 4
  S_IS_MOBILE = 5

  def __init__(self, conns):
    ChunkParser.__init__(self, ui=conns.config.ui)
    self.server_info = ['x.x.x.x:x', [], [], [], False, False]
    self.Init(conns)
    # We want to be sure to read the entire chunk at once, including
    # headers to save cycles, so we double the size we're willing to
    # read here.
    self.maxread *= 2

  def Init(self, conns):
    self.conns = conns
    self.users = {}
    self.remote_ssl = {}
    self.zhistory = {}
    self.backends = {}
    self.last_ping = 0
    self.weighted_rtt = -1
    self.using_tls = False
    self.filters = []

  def Cleanup(self, close=True):
    if self.users:
      for sid in self.users.keys():
        self.CloseStream(sid)
    ChunkParser.Cleanup(self, close=close)
    self.Init(None)

  def __html__(self):
    return ('<b>Server name</b>: %s<br>'
            '%s') % (self.server_info[self.S_NAME], ChunkParser.__html__(self))

  def LogTrafficStatus(self, final=False):
    if self.ui:
      if final:
        message = 'Disconnected from: %s' % self.server_info[self.S_NAME]
        self.ui.Status('down', color=self.ui.GREY, message=message)
      else:
        self.ui.Status('traffic')

  def GetKiteRequests(self, parse):
    requests = []
    for prefix in ('X-Beanstalk', 'X-PageKite'):
      for bs in parse.Header(prefix):
        # X-PageKite: proto:my.domain.com:token:signature
        proto, domain, srand, token, sign = bs.split(':')
        requests.append((proto.lower(), domain.lower(),
                         srand, token, sign, prefix))
    return requests

  def _FrontEnd(conn, body, conns):
    """This is what the front-end does when a back-end requests a new tunnel."""
    self = Tunnel(conns)
    try:
      for prefix in ('X-Beanstalk', 'X-PageKite'):
        for feature in conn.parser.Header(prefix+'-Features'):
          if not conns.config.disable_zchunks:
            if feature == 'ZChunks':
              self.EnableZChunks(level=1)
            elif feature == 'AddKites':
              self.server_info[self.S_ADD_KITES] = True
            elif feature == 'Mobile':
              self.server_info[self.S_IS_MOBILE] = True

        # Track which versions we see in the wild.
        version = 'old'
        for v in conn.parser.Header(prefix+'-Version'):
          version = v
        if common.gYamon:
          common.gYamon.vadd('version-%s' % version, 1, wrap=10000000)

        for replace in conn.parser.Header(prefix+'-Replace'):
          if replace in self.conns.conns_by_id:
            repl = self.conns.conns_by_id[replace]
            self.LogInfo('Disconnecting old tunnel: %s' % repl)
            repl.Die(discard_buffer=True)

      requests = self.GetKiteRequests(conn.parser)

    except Exception, err:
      self.LogError('Discarding connection: %s' % err)
      self.Cleanup()
      return None

    except socket.error, err:
      self.LogInfo('Discarding connection: %s' % err)
      self.Cleanup()
      return None

    self.last_activity = time.time()
    self.CountAs('backends_live')
    self.SetConn(conn)
    if requests:
      conns.auth.check(requests[:], conn,
                       lambda r, l: self.AuthCallback(conn, r, l))
    return self

  def RecheckQuota(self, conns, when=None):
    if when is None: when = time.time()
    if (self.quota and
        self.quota[0] is not None and
        self.quota[1] and
        (self.quota[2] < when-900)):
      self.quota[2] = when
      self.LogDebug('Rechecking: %s' % (self.quota, ))
      conns.auth.check(self.quota[1], self,
                       lambda r, l: self.QuotaCallback(conns, r, l))

  def ProcessAuthResults(self, results, duplicates_ok=False, add_tunnels=True):
    ok = []
    bad = []

    if not self.conns:
      # This can be delayed until the connecting client gives up, which
      # means we may have already called Die().  In that case, just abort.
      return True

    ok_results = ['X-PageKite-OK']
    bad_results = ['X-PageKite-Invalid']
    if duplicates_ok is True:
      ok_results.extend(['X-PageKite-Duplicate'])
    elif duplicates_ok is False:
      bad_results.extend(['X-PageKite-Duplicate'])

    for r in results:
      if r[0] in ok_results:
        ok.append(r[1])
      elif r[0] in bad_results:
        bad.append(r[1])
      elif r[0] == 'X-PageKite-SessionID':
        self.conns.SetAltId(self, r[1])

    logi = []
    if self.server_info[self.S_IS_MOBILE]:
      logi.append(('mobile', 'True'))
    if self.server_info[self.S_ADD_KITES]:
      logi.append(('add_kites', 'True'))

    if bad:
      for backend in bad:
        if backend in self.backends:
          del self.backends[backend]
      proto, domain, srand = backend.split(':')
      self.Log([('BE', 'Dead'), ('proto', proto), ('domain', domain)] + logi)
      self.conns.CloseTunnel(proto, domain, self)

    if add_tunnels:
      for backend in ok:
        if backend not in self.backends:
          self.backends[backend] = 1
        proto, domain, srand = backend.split(':')
        self.Log([('BE', 'Live'), ('proto', proto), ('domain', domain)] + logi)
        self.conns.Tunnel(proto, domain, self)
      if not ok:
        if self.server_info[self.S_ADD_KITES] and not bad:
          self.LogDebug('No tunnels configured, idling...')
          self.conns.SetIdle(self, 60)
        else:
          self.LogDebug('No tunnels configured, closing connection.')
          self.Die()

    return True

  def QuotaCallback(self, conns, results, log_info):
    # Report new values to the back-end... unless they are mobile.
    if self.quota and (self.quota[0] >= 0):
      if not self.server_info[self.S_IS_MOBILE]:
        self.SendQuota()

    self.ProcessAuthResults(results, duplicates_ok=True, add_tunnels=False)
    for r in results:
      if r[0] in ('X-PageKite-OK', 'X-PageKite-Duplicate'):
        return self

    # Nothing is OK anymore, give up and shut down the tunnel.
    self.Log(log_info)
    self.LogInfo('Ran out of quota or account deleted, closing tunnel.')
    self.Die()
    return self

  def AuthCallback(self, conn, results, log_info):
    if log_info:
      logging.Log(log_info)

    output = [HTTP_ResponseHeader(200, 'OK'),
              HTTP_Header('Transfer-Encoding', 'chunked'),
              HTTP_Header('X-PageKite-Features', 'AddKites'),
              HTTP_Header('X-PageKite-Protos', ', '.join(['%s' % p
                            for p in self.conns.config.server_protos])),
              HTTP_Header('X-PageKite-Ports', ', '.join(
                            ['%s' % self.conns.config.server_portalias.get(p, p)
                             for p in self.conns.config.server_ports]))]

    if not self.conns.config.disable_zchunks:
      output.append(HTTP_Header('X-PageKite-Features', 'ZChunks'))

    if self.conns.config.server_raw_ports:
      output.append(
        HTTP_Header('X-PageKite-Raw-Ports',
                    ', '.join(['%s' % p for p
                               in self.conns.config.server_raw_ports])))

    for r in results:
      output.append('%s: %s\r\n' % r)

    output.append(HTTP_StartBody())
    if not self.Send(output, activity=False, just_buffer=True):
      conn.LogDebug('No tunnels configured, closing connection (send failed).')
      self.Die(discard_buffer=True)
      return self

    if conn.quota and conn.quota[0]:
      self.quota = conn.quota
      self.Log([('BE-Quota', self.quota[0])])

    if self.ProcessAuthResults(results):
      self.conns.Add(self)
    else:
      self.Die()

    return self

  def ChunkAuthCallback(self, results, log_info):
    if log_info:
      logging.Log(log_info)

    if self.ProcessAuthResults(results):
      output = ['NOOP: 1\r\n']
      for r in results:
        output.append('%s: %s\r\n' % r)
      output.append('\r\n!')
      self.SendChunked(''.join(output), compress=False, just_buffer=True)

  def _RecvHttpHeaders(self, fd=None):
    data = ''
    fd = fd or self.fd
    while not data.endswith('\r\n\r\n') and not data.endswith('\n\n'):
      try:
        buf = fd.recv(1)
      except:
        # This is sloppy, but the back-end will just connect somewhere else
        # instead, so laziness here should be fine.
        buf = None
      if buf is None or buf == '':
        self.LogDebug('Remote end closed connection.')
        return None
      data += buf
      self.read_bytes += len(buf)
    if logging.DEBUG_IO:
      print '<== IN (headers) =[%s]==(\n%s)==' % (self, data)
    return data

  def _Connect(self, server, conns, tokens=None):
    if self.fd:
      self.fd.close()

    sspec = rsplit(':', server)
    if len(sspec) < 2:
      sspec = (sspec[0], 443)

    # Use chained SocksiPy to secure our communication.
    socks.DEBUG = (logging.DEBUG_IO or socks.DEBUG) and logging.LogDebug
    sock = socks.socksocket()
    if socks.HAVE_SSL:
      chain = ['default']
      if self.conns.config.fe_anon_tls_wrap:
        chain.append('ssl-anon!%s!%s' % (sspec[0], sspec[1]))
      if self.conns.config.fe_certname:
        chain.append('http!%s!%s' % (sspec[0], sspec[1]))
        chain.append('ssl!%s!443' % ','.join(self.conns.config.fe_certname))
      for hop in chain:
        sock.addproxy(*socks.parseproxy(hop))
    self.SetFD(sock)

    try:
      self.fd.settimeout(20.0) # Missing in Python 2.2
    except:
      self.fd.setblocking(1)

    self.fd.connect((sspec[0], int(sspec[1])))
    replace_sessionid = self.conns.config.servers_sessionids.get(server, None)
    if (not self.Send(HTTP_PageKiteRequest(server,
                                         conns.config.backends,
                                       tokens,
                                     nozchunks=conns.config.disable_zchunks,
                                    replace=replace_sessionid),
                      activity=False, try_flush=True, allow_blocking=False)
        or not self.Flush(wait=True, allow_blocking=False)):
      self.LogDebug('Failed to send kite request, closing.')
      return None, None

    data = self._RecvHttpHeaders()
    if not data:
      self.LogDebug('Failed to parse kite response, closing.')
      return None, None

    self.fd.setblocking(0)
    parse = HttpLineParser(lines=data.splitlines(),
                           state=HttpLineParser.IN_RESPONSE)

    return data, parse

  def CheckForTokens(self, parse):
    tcount = 0
    tokens = {}
    for request in parse.Header('X-PageKite-SignThis'):
      proto, domain, srand, token = request.split(':')
      tokens['%s:%s' % (proto, domain)] = token
      tcount += 1
    return tcount, tokens

  def ParsePageKiteCapabilities(self, parse):
    for portlist in parse.Header('X-PageKite-Ports'):
      self.server_info[self.S_PORTS].extend(portlist.split(', '))
    for portlist in parse.Header('X-PageKite-Raw-Ports'):
      self.server_info[self.S_RAW_PORTS].extend(portlist.split(', '))
    for protolist in parse.Header('X-PageKite-Protos'):
      self.server_info[self.S_PROTOS].extend(protolist.split(', '))
    if not self.conns.config.disable_zchunks:
      for feature in parse.Header('X-PageKite-Features'):
        if feature == 'ZChunks':
          self.EnableZChunks(level=9)
        elif feature == 'AddKites':
          self.server_info[self.S_ADD_KITES] = True
        elif feature == 'Mobile':
          self.server_info[self.S_IS_MOBILE] = True

  def HandlePageKiteResponse(self, parse):
    config = self.conns.config
    have_kites = 0
    have_kite_info = None

    sname = self.server_info[self.S_NAME]
    config.ui.NotifyServer(self, self.server_info)

    for misc in parse.Header('X-PageKite-Misc'):
      args = parse_qs(misc)
      logdata = [('FE', sname)]
      for arg in args:
        logdata.append((arg, args[arg][0]))
      logging.Log(logdata)
      if 'motd' in args and args['motd'][0]:
        config.ui.NotifyMOTD(sname, args['motd'][0])

    # FIXME: Really, we should keep track of quota dimensions for
    #        each kite.  At the moment that isn't even reported...
    for quota in parse.Header('X-PageKite-Quota'):
      self.quota = [float(quota), None, None]
      self.Log([('FE', sname), ('quota', quota)])

    for quota in parse.Header('X-PageKite-QConns'):
      self.q_conns = float(quota)
      self.Log([('FE', sname), ('q_conns', quota)])

    for quota in parse.Header('X-PageKite-QDays'):
      self.q_days = float(quota)
      self.Log([('FE', sname), ('q_days', quota)])

    if self.quota and self.quota[0] is not None:
      config.ui.NotifyQuota(self.quota[0], self.q_days, self.q_conns)

    invalid_reasons = {}
    for request in parse.Header('X-PageKite-Invalid-Why'):
      # This is future-compatible, in that we can add more fields later.
      details = request.split(';')
      invalid_reasons[details[0]] = details[1]

    for request in parse.Header('X-PageKite-Invalid'):
      have_kite_info = True
      proto, domain, srand = request.split(':')
      reason = invalid_reasons.get(request, 'unknown')
      self.Log([('FE', sname),
                ('err', 'Rejected'),
                ('proto', proto),
                ('reason', reason),
                ('domain', domain)])
      config.ui.NotifyKiteRejected(proto, domain, reason, crit=True)
      config.SetBackendStatus(domain, proto, add=BE_STATUS_ERR_TUNNEL)

    for request in parse.Header('X-PageKite-Duplicate'):
      have_kite_info = True
      proto, domain, srand = request.split(':')
      self.Log([('FE', self.server_info[self.S_NAME]),
                ('err', 'Duplicate'),
                ('proto', proto),
                ('domain', domain)])
      config.ui.NotifyKiteRejected(proto, domain, 'duplicate')
      config.SetBackendStatus(domain, proto, add=BE_STATUS_ERR_TUNNEL)

    ssl_available = {}
    for request in parse.Header('X-PageKite-SSL-OK'):
      ssl_available[request] = True

    for request in parse.Header('X-PageKite-OK'):
      have_kite_info = True
      have_kites += 1
      proto, domain, srand = request.split(':')
      self.conns.Tunnel(proto, domain, self)
      status = BE_STATUS_OK
      if request in ssl_available:
        status |= BE_STATUS_REMOTE_SSL
        self.remote_ssl[(proto, domain)] = True
      self.Log([('FE', sname),
                ('proto', proto),
                ('domain', domain),
                ('ssl', (request in ssl_available))])
      config.SetBackendStatus(domain, proto, add=status)

    return have_kite_info and have_kites

  def _BackEnd(server, backends, require_all, conns):
    """This is the back-end end of a tunnel."""
    self = Tunnel(conns)
    self.backends = backends
    self.require_all = require_all
    self.server_info[self.S_NAME] = server
    abort = True
    try:
      try:
        data, parse = self._Connect(server, conns)
      except:
        logging.LogError('Error in connect: %s' % format_exc())
        raise

      if data and parse:
        # Collect info about front-end capabilities, for interactive config
        self.ParsePageKiteCapabilities(parse)

        for sessionid in parse.Header('X-PageKite-SessionID'):
          conns.SetAltId(self, sessionid)
          conns.config.servers_sessionids[server] = sessionid

        tryagain, tokens = self.CheckForTokens(parse)
        if tryagain:
          if self.server_info[self.S_ADD_KITES]:
            request = PageKiteRequestHeaders(server, conns.config.backends,
                                             tokens)
            abort = not self.SendChunked(('NOOP: 1\r\n%s\r\n\r\n!'
                                          ) % ''.join(request),
                                         compress=False, just_buffer=True)
            data = parse = None
          else:
            try:
              data, parse = self._Connect(server, conns, tokens)
            except:
              logging.LogError('Error in connect: %s' % format_exc())
              raise

        if data and parse:
          kites = self.HandlePageKiteResponse(parse)
          abort = (kites is None) or (kites < 1)

    except socket.error:
      self.Cleanup()
      return None

    except Exception, e:
      self.LogError('Server response parsing failed: %s' % e)
      self.Cleanup()
      return None

    if abort:
      return None

    conns.Add(self)
    self.CountAs('frontends_live')
    self.last_activity = time.time()

    return self

  FrontEnd = staticmethod(_FrontEnd)
  BackEnd = staticmethod(_BackEnd)

  def Send(self, data, try_flush=False, activity=False, just_buffer=False,
                       allow_blocking=True):
    try:
      if TUNNEL_SOCKET_BLOCKS and allow_blocking and not just_buffer:
        self.fd.setblocking(1)
      return ChunkParser.Send(self, data, try_flush=try_flush,
                                          activity=activity,
                                          just_buffer=just_buffer,
                                          allow_blocking=allow_blocking)
    finally:
      if TUNNEL_SOCKET_BLOCKS and allow_blocking and not just_buffer:
        self.fd.setblocking(0)

  def SendData(self, conn, data, sid=None, host=None, proto=None, port=None,
                                 chunk_headers=None):
    sid = int(sid or conn.sid)
    if conn: self.users[sid] = conn
    if not sid in self.zhistory: self.zhistory[sid] = [0, 0]

    # Pass outgoing data through any defined filters
    for f in self.filters:
      try:
        data = f.filter_data_out(self, sid, data)
      except:
        logging.LogError(('Ignoring error in filter_out %s: %s'
                          ) % (f, format_exc()))

    sending = ['SID: %s\r\n' % sid]
    if proto: sending.append('Proto: %s\r\n' % proto)
    if host: sending.append('Host: %s\r\n' % host)
    if port:
      porti = int(port)
      if porti in self.conns.config.server_portalias:
        sending.append('Port: %s\r\n' % self.conns.config.server_portalias[porti])
      else:
        sending.append('Port: %s\r\n' % port)
    if chunk_headers:
      for ch in chunk_headers: sending.append('%s: %s\r\n' % ch)
    sending.append('\r\n')
    sending.append(data)

    return self.SendChunked(sending, zhistory=self.zhistory[sid])

  def SendStreamEof(self, sid, write_eof=False, read_eof=False):
    return self.SendChunked('SID: %s\r\nEOF: 1%s%s\r\n\r\nBye!' % (sid,
                            (write_eof or not read_eof) and 'W' or '',
                            (read_eof or not write_eof) and 'R' or ''),
                            compress=False)

  def EofStream(self, sid, eof_type='WR'):
    if sid in self.users and self.users[sid] is not None:
      write_eof = (-1 != eof_type.find('W'))
      read_eof = (-1 != eof_type.find('R'))
      self.users[sid].ProcessTunnelEof(read_eof=(read_eof or not write_eof),
                                       write_eof=(write_eof or not read_eof))

  def CloseStream(self, sid, stream_closed=False):
    if sid in self.users:
      stream = self.users[sid]
      del self.users[sid]

      if not stream_closed and stream is not None:
        stream.CloseTunnel(tunnel_closed=True)

    if sid in self.zhistory:
      del self.zhistory[sid]

  def ResetRemoteZChunks(self):
    return self.SendChunked('NOOP: 1\r\nZRST: 1\r\n\r\n!',
                            compress=False, just_buffer=True)

  def TriggerPing(self):
    when = time.time() - PING_GRACE_MIN - PING_INTERVAL_MAX
    self.last_ping = self.last_activity = when

  def SendPing(self):
    now = time.time()
    self.last_ping = int(now)
    self.LogDebug("Ping", [('host', self.server_info[self.S_NAME])])
    return self.SendChunked('NOOP: 1\r\nPING: %.3f\r\n\r\n!' % now,
                            compress=False, just_buffer=True)

  def ProcessPong(self, pong):
    try:
      rtt = int(1000*(time.time()-float(pong)))
      if self.weighted_rtt < 0:
        self.weighted_rtt = rtt
      else:
        self.weighted_rtt = (self.weighted_rtt + rtt)/2

      self.Log([('host', self.server_info[self.S_NAME]),
                ('rtt', '%d' % rtt),
                ('wrtt', '%d' % self.weighted_rtt)])

      if common.gYamon:
        common.gYamon.ladd('tunnel_rtt', rtt)
        common.gYamon.ladd('tunnel_wrtt', self.weighted_rtt)
    except ValueError:
      pass

  def SendPong(self, data):
    if (self.conns.config.isfrontend and
        self.quota and (self.quota[0] >= 0)):
      # May as well make ourselves useful!
      return self.SendQuota(pong=data[:64])
    else:
      return self.SendChunked('NOOP: 1\r\nPONG: %s\r\n\r\n!' % data[:64],
                              compress=False, just_buffer=True)

  def SendQuota(self, pong=''):
    if pong:
      pong = 'PONG: %s\r\n' % pong
    if self.q_days is not None:
      return self.SendChunked(('NOOP: 1\r\n%sQuota: %s\r\nQDays: %s\r\nQConns: %s\r\n\r\n!'
                               ) % (pong, self.quota[0], self.q_days, self.q_conns),
                              compress=False, just_buffer=True)
    else:
      return self.SendChunked(('NOOP: 1\r\n%sQuota: %s\r\n\r\n!'
                               ) % (pong, self.quota[0]),
                              compress=False, just_buffer=True)

  def SendProgress(self, sid, conn, throttle=False):
    # FIXME: Optimize this away unless meaningful progress has been made?
    msg = ('NOOP: 1\r\n'
           'SID: %s\r\n'
           'SKB: %d\r\n') % (sid, (conn.all_out + conn.wrote_bytes)/1024)
    throttle = throttle and ('SPD: %d\r\n' % conn.write_speed) or ''
    return self.SendChunked('%s%s\r\n!' % (msg, throttle),
                            compress=False, just_buffer=True)

  def ProcessCorruptChunk(self, data):
    self.ResetRemoteZChunks()
    return True

  def Probe(self, host):
    for bid in self.conns.config.backends:
      be = self.conns.config.backends[bid]
      if be[BE_DOMAIN] == host:
        bhost, bport = (be[BE_BHOST], be[BE_BPORT])
        # FIXME: Should vary probe by backend type
        if self.conns.config.Ping(bhost, int(bport)) > 2:
          return False
    return True

  def AutoThrottle(self, max_speed=None, remote=False, delay=0.2):
    # Never throttle tunnels.
    return True

  def ProgressTo(self, parse):
    try:
      sid = int(parse.Header('SID')[0])
      bps = int((parse.Header('SPD') or [-1])[0])
      skb = int((parse.Header('SKB') or [-1])[0])
      if sid in self.users:
        self.users[sid].RecordProgress(skb, bps)
    except:
      logging.LogError(('Tunnel::ProgressTo: That made no sense! %s'
                        ) % format_exc())
    return True

  # If a tunnel goes down, we just go down hard and kill all our connections.
  def ProcessEofRead(self):
    self.Die()
    return False

  def ProcessEofWrite(self):
    return self.ProcessEofRead()

  def ProcessChunkQuotaInfo(self, parse):
    new_quota = 0
    if parse.Header('QDays'):
      self.q_days = new_quota = int(parse.Header('QDays'))
    if parse.Header('QConns'):
      self.q_conns = new_quota = int(parse.Header('QConns'))
    if parse.Header('Quota'):
      new_quota = 1
      if self.quota:
        self.quota[0] = int(parse.Header('Quota')[0])
      else:
        self.quota = [int(parse.Header('Quota')[0]), None, None]
    if new_quota:
      self.conns.config.ui.NotifyQuota(self.quota[0],
                                       self.q_days, self.q_conns)

  def ProcessChunkDirectives(self, parse):
    if parse.Header('PONG'):
      self.ProcessPong(parse.Header('PONG')[0])
    if parse.Header('PING'):
      return self.SendPong(parse.Header('PING')[0])
    if parse.Header('ZRST') and not self.ResetZChunks():
      return False
    if parse.Header('SPD') or parse.Header('SKB'):
      if not self.ProgressTo(parse):
        return False
    if parse.Header('NOOP'):
      return True

    return None

  def FilterIncoming(self, sid, data=None, info=None):
    """Pass incoming data through filters, if we have any."""
    for f in self.filters:
      try:
        if sid and info:
          f.filter_set_sid(sid, info)
        if data is not None:
          data = f.filter_data_in(self, sid, data)
      except:
        logging.LogError(('Ignoring error in filter_in %s: %s'
                          ) % (f, format_exc()))
    return data

  def GetChunkDestination(self, parse):
    return ((parse.Header('Proto') or [''])[0].lower(),
            (parse.Header('Port')  or [''])[0].lower(),
            (parse.Header('Host')  or [''])[0].lower(),
            (parse.Header('RIP')   or [''])[0].lower(),
            (parse.Header('RPort') or [''])[0].lower(),
            (parse.Header('RTLS')  or [''])[0].lower())

  def ReplyToProbe(self, proto, sid, host):
    if self.conns.config.no_probes:
      what, reply = 'rejected', HTTP_NoFeConnection(proto)
    elif self.Probe(host):
      what, reply = 'good', HTTP_GoodBeConnection(proto)
    else:
      what, reply = 'back-end down', HTTP_NoBeConnection(proto)
    self.LogDebug('Responding to probe for %s: %s' % (host, what))
    return self.SendChunked('SID: %s\r\n\r\n%s' % (sid, reply))

  def ConnectBE(self, sid, proto, port, host, rIp, rPort, rTLS, data):
    conn = UserConn.BackEnd(proto, host, sid, self, port,
                            remote_ip=rIp, remote_port=rPort, data=data)

    if self.filters:
      if conn:
        rewritehost = conn.config.get('rewritehost')
        if rewritehost is True:
          rewritehost = conn.backend[BE_BHOST]
      else:
        rewritehost = False

      data = self.FilterIncoming(sid, data, info={
        'proto': proto,
        'port': port,
        'host': host,
        'remote_ip': rIp,
        'remote_port': rPort,
        'using_tls': rTLS,
        'be_host': conn and conn.backend[BE_BHOST],
        'be_port': conn and conn.backend[BE_BPORT],
        'trusted': conn and (conn.security or
                             conn.config.get('insecure', False)),
        'rawheaders': conn and conn.config.get('rawheaders', False),
        'rewritehost': rewritehost
      })

    if proto in ('http', 'http2', 'http3', 'websocket'):
      if conn and data.startswith(HttpSecurityFilter.REJECT):
        # Pretend we need authentication for dangerous URLs
        conn.Die()
        conn, data, code = False, '', 500
      else:
        code = (conn is None) and 503 or 401
      if not conn:
        # conn is None means we have no back-end.
        # conn is False means authentication is required.
        if not self.SendChunked('SID: %s\r\n\r\n%s' % (sid,
                                HTTP_Unavailable('be', proto, host,
                                  frame_url=self.conns.config.error_url,
                                  code=code
                                )), just_buffer=True):
          return False, False
        else:
          conn = None

    elif conn and proto == 'httpfinger':
      # Rewrite a finger request to HTTP.
      try:
        firstline, rest = data.split('\n', 1)
        if conn.config.get('rewritehost', False):
          rewritehost = conn.backend[BE_BHOST]
        else:
          rewritehost = host
        if '%s' in self.conns.config.finger_path:
          args =  (firstline.strip(), rIp, rewritehost, rest)
        else:
          args =  (rIp, rewritehost, rest)
        data = ('GET '+self.conns.config.finger_path+' HTTP/1.1\r\n'
                'X-Forwarded-For: %s\r\n'
                'Connection: close\r\n'
                'Host: %s\r\n\r\n%s') % args
      except Exception, e:
        self.LogError('Error formatting HTTP-Finger: %s' % e)
        conn.Die()
        conn = None

    elif not conn and proto == 'https':
      if not self.SendChunked('SID: %s\r\n\r\n%s' % (sid,
                              TLS_Unavailable(unavailable=True)),
                              just_buffer=True):
        return False, False

    if conn:
      self.users[sid] = conn
      if proto == 'httpfinger':
        conn.fd.setblocking(1)
        conn.Send(data, try_flush=True,
                        allow_blocking=False) or conn.Flush(wait=True,
                                                            allow_blocking=False)
        self._RecvHttpHeaders(fd=conn.fd)
        conn.fd.setblocking(0)
        data = ''

    return conn, data

  def ProcessKiteUpdates(self, parse):
    # Look for requests for new tunnels
    if self.conns.config.isfrontend:
      requests = self.GetKiteRequests(parse)
      if requests:
        self.conns.auth.check(requests[:], self,
                              lambda r, l: self.ChunkAuthCallback(r, l))

    # Look for responses to requests for new tunnels
    tryagain, tokens = self.CheckForTokens(parse)
    if tryagain:
      server = self.server_info[self.S_NAME]
      backends = { }
      for bid in tokens:
        backends[bid] = self.conns.config.backends[bid]
      request = '\r\n'.join(PageKiteRequestHeaders(server, backends, tokens))
      self.SendChunked('NOOP: 1\r\n%s\r\n\r\n!' % request,
                       compress=False, just_buffer=True)

    kites = self.HandlePageKiteResponse(parse)
    if (kites is not None) and (kites < 1):
      self.Die()

  def ProcessChunk(self, data):
    # First, we process the chunk headers.
    try:
      headers, data = data.split('\r\n\r\n', 1)
      parse = HttpLineParser(lines=headers.splitlines(),
                             state=HttpLineParser.IN_HEADERS)

      # Process PING/NOOP/etc: may result in a short-circuit.
      rv = self.ProcessChunkDirectives(parse)
      if rv is not None:
        # Update quota and kite information if necessary: this data is
        # always sent along with a NOOP, so checking for it here is safe.
        self.ProcessChunkQuotaInfo(parse)
        self.ProcessKiteUpdates(parse)
        return rv

      sid = int(parse.Header('SID')[0])
      eof = parse.Header('EOF')
    except:
      logging.LogError(('Tunnel::ProcessChunk: Corrupt chunk: %s'
                        ) % format_exc())
      return False

    # EOF stream?
    if eof:
      self.EofStream(sid, eof[0])
      return True

    # Headers done, not EOF: let's get the other end of this connection.
    if sid in self.users:
      # Either from pre-existing connections...
      conn = self.users[sid]
      if self.filters:
        data = self.FilterIncoming(sid, data)
    else:
      # ... or we connect to a back-end.
      proto, port, host, rIp, rPort, rTLS = self.GetChunkDestination(parse)
      if proto and host:

        # Probe requests are handled differently (short circuit)
        if proto.startswith('probe'):
          return self.ReplyToProbe(proto, sid, host)

        conn, data = self.ConnectBE(sid, proto, port, host,
                                         rIp, rPort, rTLS, data)
        if conn is False:
          return False
      else:
        conn = None

    # Send the data or shut down.
    if conn:
      if data and not conn.Send(data, try_flush=True):
        # If that failed something is wrong, but we'll let the outer
        # select/epoll loop catch and handle it.
        pass

      if len(conn.write_blocked) > 0 and conn.created < time.time()-3:
        return self.SendProgress(sid, conn, throttle=True)

    else:
      # No connection?  Close this stream.
      self.CloseStream(sid)
      return self.SendStreamEof(sid) and self.Flush()

    return True


class LoopbackTunnel(Tunnel):
  """A Tunnel which just loops back to this process."""

  def __init__(self, conns, which, backends):
    Tunnel.__init__(self, conns)

    if self.fd:
      self.fd = None
    self.weighted_rtt = -1000
    self.lock = None
    self.backends = backends
    self.require_all = True
    self.server_info[self.S_NAME] = LOOPBACK[which]
    self.other_end = None
    self.which = which
    self.buffer_count = 0
    self.CountAs('loopbacks_live')
    if which == 'FE':
      for d in backends.keys():
        if backends[d][BE_BHOST]:
          proto, domain = d.split(':')
          self.conns.Tunnel(proto, domain, self)
          self.Log([('FE', self.server_info[self.S_NAME]),
                    ('proto', proto),
                    ('domain', domain)])

  def __str__(self):
    return '%s %s' % (Tunnel.__str__(self), self.which)

  def Cleanup(self, close=True):
    Tunnel.Cleanup(self, close=close)
    other = self.other_end
    self.other_end = None
    if other and other.other_end:
      other.Cleanup(close=close)

  def Linkup(self, other):
    """Links two LoopbackTunnels together."""
    self.other_end = other
    other.other_end = self
    return other

  def _Loop(conns, backends):
    """Creates a loop, returning the back-end tunnel object."""
    return LoopbackTunnel(conns, 'FE', backends
                          ).Linkup(LoopbackTunnel(conns, 'BE', backends))

  Loop = staticmethod(_Loop)

  # FIXME: This is a zero-length tunnel, but the code relies in some places
  #        on the tunnel having a length.  We really need a pipe here, or
  # things will go horribly wrong now and then.  For now we hack this by
  # separating Write and Flush and looping back only on Flush.

  def Send(self, data, try_flush=False, activity=False, just_buffer=True,
                       allow_blocking=True):
    if self.write_blocked:
      data = [self.write_blocked] + data
      self.write_blocked = ''
    joined_data = ''.join(data)
    if try_flush or (len(joined_data) > 10240) or (self.buffer_count >= 100):
      if logging.DEBUG_IO:
        print '|%s| %s \n|%s| %s' % (self.which, self, self.which, data)
      self.buffer_count = 0
      return self.other_end.ProcessData(joined_data)
    else:
      self.buffer_count += 1
      self.write_blocked = joined_data
      return True


class UserConn(Selectable):
  """A Selectable representing a user's connection."""

  def __init__(self, address, ui=None):
    Selectable.__init__(self, address=address, ui=ui)
    self.Reset()

  def Reset(self):
    self.tunnel = None
    self.conns = None
    self.backend = BE_NONE[:]
    self.config = {}
    self.security = None

  def Cleanup(self, close=True):
    if close:
      self.CloseTunnel()
    Selectable.Cleanup(self, close=close)
    self.Reset()

  def ConnType(self):
    if self.backend[BE_BHOST]:
      return 'BE=%s:%s' % (self.backend[BE_BHOST], self.backend[BE_BPORT])
    else:
      return 'FE'

  def __str__(self):
    return '%s %s' % (Selectable.__str__(self), self.ConnType())

  def __html__(self):
    return ('<b>Tunnel</b>: <a href="/conn/%s">%s</a><br>'
            '%s') % (self.tunnel and self.tunnel.sid or '',
                     escape_html('%s' % (self.tunnel or '')),
                     Selectable.__html__(self))

  def IsReadable(self, now):
    if self.tunnel and self.tunnel.IsBlocked():
      return False
    return Selectable.IsReadable(self, now)

  def CloseTunnel(self, tunnel_closed=False):
    tunnel, self.tunnel = self.tunnel, None
    if tunnel and not tunnel_closed:
      tunnel.SendStreamEof(self.sid, write_eof=True, read_eof=True)
      tunnel.CloseStream(self.sid, stream_closed=True)
    self.ProcessTunnelEof(read_eof=True, write_eof=True)

  def _FrontEnd(conn, address, proto, host, on_port, body, conns):
    # This is when an external user connects to a server and requests a
    # web-page.  We have to give it to them!
    self = UserConn(address, ui=conns.config.ui)
    self.conns = conns
    self.SetConn(conn)

    if ':' in host: host, port = host.split(':', 1)
    self.proto = proto
    self.host = host

    # If the listening port is an alias for another...
    if int(on_port) in conns.config.server_portalias:
      on_port = conns.config.server_portalias[int(on_port)]

    # Try and find the right tunnel. We prefer proto/port specifications first,
    # then the just the proto. If the protocol is WebSocket and no tunnel is
    # found, look for a plain HTTP tunnel.
    if proto.startswith('probe'):
      protos = ['http', 'https', 'websocket', 'raw', 'irc',
                'finger', 'httpfinger']
      ports = conns.config.server_ports[:]
      ports.extend(conns.config.server_aliasport.keys())
      ports.extend([x for x in conns.config.server_raw_ports if x != VIRTUAL_PN])
    else:
      protos = [proto]
      ports = [on_port]
      if proto == 'websocket': protos.append('http')
      elif proto == 'http': protos.extend(['http2', 'http3'])

    tunnels = None
    for p in protos:
      for prt in ports:
        if not tunnels: tunnels = conns.Tunnel('%s-%s' % (p, prt), host)
      if not tunnels: tunnels = conns.Tunnel(p, host)
    if not tunnels: tunnels = conns.Tunnel(protos[0], CATCHALL_HN)

    if self.address:
      chunk_headers = [('RIP', self.address[0]), ('RPort', self.address[1])]
      if conn.my_tls: chunk_headers.append(('RTLS', 1))

    if tunnels:
      if len(tunnels) > 1:
        tunnels.sort(key=lambda t: t.weighted_rtt)
      self.tunnel = tunnels[0]
    if (self.tunnel and self.tunnel.SendData(self, ''.join(body), host=host,
                                             proto=proto, port=on_port,
                                             chunk_headers=chunk_headers)
                    and self.conns):
      self.Log([('domain', self.host), ('on_port', on_port), ('proto', self.proto), ('is', 'FE')])
      self.conns.Add(self)
      if proto.startswith('http'):
        self.conns.TrackIP(address[0], host)
        # FIXME: Use the tracked data to detect & mitigate abuse?
      return self
    else:
      self.LogDebug('No back-end', [('on_port', on_port), ('proto', self.proto),
                                    ('domain', self.host), ('is', 'FE')])
      self.Cleanup(close=False)
      return None

  def _BackEnd(proto, host, sid, tunnel, on_port,
               remote_ip=None, remote_port=None, data=None):
    # This is when we open a backend connection, because a user asked for it.
    self = UserConn(None, ui=tunnel.conns.config.ui)
    self.sid = sid
    self.proto = proto
    self.host = host
    self.conns = tunnel.conns
    self.tunnel = tunnel
    failure = None

    # Try and find the right back-end. We prefer proto/port specifications
    # first, then the just the proto. If the protocol is WebSocket and no
    # tunnel is found, look for a plain HTTP tunnel.  Fallback hosts can
    # be registered using the http2/3/4 protocols.
    backend = None

    if proto == 'http':
      protos = [proto, 'http2', 'http3']
    elif proto.startswith('probe'):
      protos = ['http', 'http2', 'http3']
    elif proto == 'websocket':
      protos = [proto, 'http', 'http2', 'http3']
    else:
      protos = [proto]

    for p in protos:
      if not backend:
        p_p = '%s-%s' % (p, on_port)
        backend, be = self.conns.config.GetBackendServer(p_p, host)
      if not backend:
        backend, be = self.conns.config.GetBackendServer(p, host)
      if not backend:
        backend, be = self.conns.config.GetBackendServer(p, CATCHALL_HN)
      if backend:
        break

    logInfo = [
      ('on_port', on_port),
      ('proto', proto),
      ('domain', host),
      ('is', 'BE')
    ]
    if remote_ip:
      logInfo.append(('remote_ip', remote_ip))

    # Strip off useless IPv6 prefix, if this is an IPv4 address.
    if remote_ip.startswith('::ffff:') and ':' not in remote_ip[7:]:
      remote_ip = remote_ip[7:]

    if not backend or not backend[0]:
      self.ui.Notify(('%s - %s://%s:%s (FAIL: no server)'
                      ) % (remote_ip or 'unknown', proto, host, on_port),
                     prefix='?', color=self.ui.YELLOW)
    else:
      http_host = '%s/%s' % (be[BE_DOMAIN], be[BE_PORT] or '80')
      self.backend = be
      self.config = host_config = self.conns.config.be_config.get(http_host, {})

      # Access control interception: check remote IP addresses first.
      ip_keys = [k for k in host_config if k.startswith('ip/')]
      if ip_keys:
        k1 = 'ip/%s' % remote_ip
        k2 = '.'.join(k1.split('.')[:-1])
        if not (k1 in host_config or k2 in host_config):
          self.ui.Notify(('%s - %s://%s:%s (IP ACCESS DENIED)'
                          ) % (remote_ip or 'unknown', proto, host, on_port),
                         prefix='!', color=self.ui.YELLOW)
          logInfo.append(('forbidden-ip', '%s' % remote_ip))
          backend = None
        else:
          self.security = 'ip'

      # Access control interception: check for HTTP Basic authentication.
      user_keys = [k for k in host_config if k.startswith('password/')]
      if user_keys:
        user, pwd, fail = None, None, True
        if proto in ('websocket', 'http', 'http2', 'http3'):
          parse = HttpLineParser(lines=data.splitlines())
          auth = parse.Header('Authorization')
          try:
            (how, ab64) = auth[0].strip().split()
            if how.lower() == 'basic':
              user, pwd = base64.decodestring(ab64).split(':')
          except:
            user = auth

          user_key = 'password/%s' % user
          if user and user_key in host_config:
            if host_config[user_key] == pwd:
              fail = False

        if fail:
          if logging.DEBUG_IO:
            print '=== REQUEST\n%s\n===' % data
          self.ui.Notify(('%s - %s://%s:%s (USER ACCESS DENIED)'
                          ) % (remote_ip or 'unknown', proto, host, on_port),
                         prefix='!', color=self.ui.YELLOW)
          logInfo.append(('forbidden-user', '%s' % user))
          backend = None
          failure = ''
        else:
          self.security = 'password'

    if not backend:
      logInfo.append(('err', 'No back-end'))
      self.Log(logInfo)
      self.Cleanup(close=False)
      return failure

    try:
      self.SetFD(rawsocket(socket.AF_INET, socket.SOCK_STREAM))
      try:
        self.fd.settimeout(2.0) # Missing in Python 2.2
      except:
        self.fd.setblocking(1)

      sspec = list(backend)
      if len(sspec) == 1: sspec.append(80)
      self.fd.connect(tuple(sspec))

      self.fd.setblocking(0)

    except socket.error, err:
      logInfo.append(('socket_error', '%s' % err))
      self.ui.Notify(('%s - %s://%s:%s (FAIL: %s:%s is down)'
                      ) % (remote_ip or 'unknown', proto, host, on_port,
                           sspec[0], sspec[1]),
                     prefix='!', color=self.ui.YELLOW)
      self.Log(logInfo)
      self.Cleanup(close=False)
      return None

    sspec = (sspec[0], sspec[1])
    be_name = (sspec == self.conns.config.ui_sspec) and 'builtin' or ('%s:%s' % sspec)
    self.ui.Status('serving')
    self.ui.Notify(('%s < %s://%s:%s (%s)'
                    ) % (remote_ip or 'unknown', proto, host, on_port, be_name))
    self.Log(logInfo)
    self.conns.Add(self)
    return self

  FrontEnd = staticmethod(_FrontEnd)
  BackEnd = staticmethod(_BackEnd)

  def Shutdown(self, direction):
    try:
      if self.fd:
        if 'sock_shutdown' in dir(self.fd):
          # This is a pyOpenSSL socket, which has incompatible shutdown.
          if direction == socket.SHUT_RD:
            self.fd.shutdown()
          else:
            self.fd.sock_shutdown(direction)
        else:
          self.fd.shutdown(direction)
    except Exception, e:
      pass

  def ProcessTunnelEof(self, read_eof=False, write_eof=False):
    rv = True
    if write_eof and not self.read_eof:
      rv = self.ProcessEofRead(tell_tunnel=False) and rv
    if read_eof and not self.write_eof:
      rv = self.ProcessEofWrite(tell_tunnel=False) and rv
    return rv

  def ProcessEofRead(self, tell_tunnel=True):
    self.read_eof = True
    self.Shutdown(socket.SHUT_RD)

    if tell_tunnel and self.tunnel:
      self.tunnel.SendStreamEof(self.sid, read_eof=True)

    return self.ProcessEof()

  def ProcessEofWrite(self, tell_tunnel=True):
    self.write_eof = True
    if not self.write_blocked:
      self.Shutdown(socket.SHUT_WR)

    if tell_tunnel and self.tunnel:
      self.tunnel.SendStreamEof(self.sid, write_eof=True)

    if (self.conns and
        self.ConnType() == 'FE' and
        (not self.read_eof)):
      self.conns.SetIdle(self, 120)

    return self.ProcessEof()

  def Send(self, data, try_flush=False, activity=True, just_buffer=False,
                       allow_blocking=True):
    rv = Selectable.Send(self, data, try_flush=try_flush, activity=activity,
                                     just_buffer=just_buffer,
                                     allow_blocking=allow_blocking)
    if self.write_eof and not self.write_blocked:
      self.Shutdown(socket.SHUT_WR)
    elif try_flush or not self.write_blocked:
      if self.tunnel:
        self.tunnel.SendProgress(self.sid, self)
    return rv

  def ProcessData(self, data):
    if not self.tunnel:
      self.LogError('No tunnel! %s' % self)
      return False

    if not self.tunnel.SendData(self, data):
      self.LogDebug('Send to tunnel failed')
      return False

    # Back off if tunnel is stuffed.
    if self.tunnel and len(self.tunnel.write_blocked) > 1024000:
      # FIXME: think about this...
      self.Throttle(delay=(len(self.tunnel.write_blocked)-204800)/max(50000,
                    self.tunnel.write_speed))

    if self.read_eof:
      return self.ProcessEofRead()
    return True


class UnknownConn(MagicProtocolParser):
  """This class is a connection which we're not sure what is yet."""

  def __init__(self, fd, address, on_port, conns):
    MagicProtocolParser.__init__(self, fd, address, on_port, ui=conns.config.ui)
    self.peeking = True

    # Set up our parser chain.
    self.parsers = [HttpLineParser]
    if IrcLineParser.PROTO in conns.config.server_protos:
      self.parsers.append(IrcLineParser)
    if FingerLineParser.PROTO in conns.config.server_protos:
      self.parsers.append(FingerLineParser)
    self.parser = MagicLineParser(parsers=self.parsers)

    self.conns = conns
    self.conns.Add(self)
    self.conns.SetIdle(self, 10)

    self.sid = -1
    self.host = None
    self.proto = None
    self.said_hello = False
    self.bad_loops = 0

  def Cleanup(self, close=True):
    MagicProtocolParser.Cleanup(self, close=close)
    self.conns = self.parser = None

  def SayHello(self):
    if self.said_hello:
      return False
    else:
      self.said_hello = True
    if self.on_port in (25, 125, 2525):
      # FIXME: We don't actually support SMTP yet and 125 is bogus.
      self.Send(['220 ready ESMTP PageKite Magic Proxy\n'], try_flush=True)
    return True

  def __str__(self):
    return '%s (%s/%s:%s)' % (MagicProtocolParser.__str__(self),
                              (self.proto or '?'),
                              (self.on_port or '?'),
                              (self.host or '?'))

  # Any sort of EOF just means give up: if we haven't figured out what
  # kind of connnection this is yet, we won't without more data.
  def ProcessEofRead(self):
    self.Die(discard_buffer=True)
    return self.ProcessEof()
  def ProcessEofWrite(self):
    self.Die(discard_buffer=True)
    return self.ProcessEof()

  def ProcessLine(self, line, lines):
    if not self.parser: return True
    if self.parser.Parse(line) is False: return False
    if not self.parser.ParsedOK(): return True

    self.parser = self.parser.last_parser
    if self.parser.protocol == HttpLineParser.PROTO:
      # HTTP has special cases, including CONNECT etc.
      return self.ProcessParsedHttp(line, lines)
    else:
      return self.ProcessParsedMagic(self.parser.PROTOS, line, lines)

  def ProcessParsedMagic(self, protos, line, lines):
    if (self.conns and
        self.conns.config.CheckTunnelAcls(self.address, conn=self)):
      for proto in protos:
        if UserConn.FrontEnd(self, self.address,
                             proto, self.parser.domain, self.on_port,
                             self.parser.lines + lines, self.conns) is not None:
          self.Cleanup(close=False)
          return True

    self.Send([self.parser.ErrorReply(port=self.on_port)], try_flush=True)
    self.Cleanup()
    return False

  def ProcessParsedHttp(self, line, lines):
    done = False
    if self.parser.method == 'PING':
      self.Send('PONG %s\r\n\r\n' % self.parser.path)
      self.read_eof = self.write_eof = done = True
      self.fd.close()

    elif self.parser.method == 'CONNECT':
      if self.parser.path.lower().startswith('pagekite:'):
        if not self.conns.config.CheckTunnelAcls(self.address, conn=self):
          self.Send(HTTP_ConnectBad(code=403, status='Forbidden'),
                    try_flush=True)
          return False
        if Tunnel.FrontEnd(self, lines, self.conns) is None:
          self.Send(HTTP_ConnectBad(), try_flush=True)
          return False
        done = True

      else:
        try:
          connect_parser = self.parser
          chost, cport = connect_parser.path.split(':', 1)

          cport = int(cport)
          chost = chost.lower()
          sid1 = ':%s' % chost
          sid2 = '-%s:%s' % (cport, chost)
          tunnels = self.conns.tunnels

          if not self.conns.config.CheckClientAcls(self.address, conn=self):
            self.Send(HTTP_Unavailable('fe', 'raw', chost,
                                       code=403, status='Forbidden',
                                       frame_url=self.conns.config.error_url),
                      try_flush=True)
            return False

          # These allow explicit CONNECTs to direct http(s) or raw backends.
          # If no match is found, we throw an error.

          if cport in (80, 8080):
            if (('http'+sid1) in tunnels) or (
                ('http'+sid2) in tunnels) or (
                ('http2'+sid1) in tunnels) or (
                ('http2'+sid2) in tunnels) or (
                ('http3'+sid1) in tunnels) or (
                ('http3'+sid2) in tunnels):
              (self.on_port, self.host) = (cport, chost)
              self.parser = HttpLineParser()
              self.Send(HTTP_ConnectOK(), try_flush=True)
              return True

          whost = chost
          if '.' in whost:
            whost = '*.' + '.'.join(whost.split('.')[1:])

          if cport == 443:
            if (('https'+sid1) in tunnels) or (
                ('https'+sid2) in tunnels) or (
                chost in self.conns.config.tls_endpoints) or (
                whost in self.conns.config.tls_endpoints):
              (self.on_port, self.host) = (cport, chost)
              self.parser = HttpLineParser()
              self.Send(HTTP_ConnectOK(), try_flush=True)
              return self.ProcessTls(''.join(lines), chost)

          if (cport in self.conns.config.server_raw_ports or
              VIRTUAL_PN in self.conns.config.server_raw_ports):
            for raw in ('raw', 'finger'):
              if ((raw+sid1) in tunnels) or ((raw+sid2) in tunnels):
                (self.on_port, self.host) = (cport, chost)
                self.parser = HttpLineParser()
                self.Send(HTTP_ConnectOK(), try_flush=True)
                return self.ProcessProto(''.join(lines), raw, self.host)

          self.Send(HTTP_ConnectBad(), try_flush=True)
          return False

        except ValueError:
          pass

    if (not done and self.parser.method == 'POST'
                 and self.parser.path in MAGIC_PATHS):
      # FIXME: DEPRECATE: Make this go away!
      if not self.conns.config.CheckTunnelAcls(self.address, conn=self):
        self.Send(HTTP_ConnectBad(code=403, status='Forbidden'),
                  try_flush=True)
        return False
      if Tunnel.FrontEnd(self, lines, self.conns) is None:
        self.Send(HTTP_ConnectBad(), try_flush=True)
        return False
      done = True

    if not done:
      if not self.host:
        hosts = self.parser.Header('Host')
        if hosts:
          self.host = hosts[0].lower()
        else:
          self.Send(HTTP_Response(400, 'Bad request',
                    ['<html><body><h1>400 Bad request</h1>',
                     '<p>Invalid request, no Host: found.</p>',
                     '</body></html>\n'], trackable=True))
          return False

      if self.parser.path.startswith(MAGIC_PREFIX):
        try:
          self.host = self.parser.path.split('/')[2]
          if self.parser.path.endswith('.json'):
            self.proto = 'probe.json'
          else:
            self.proto = 'probe'
        except ValueError:
          pass

      if self.proto is None:
        self.proto = 'http'
        upgrade = self.parser.Header('Upgrade')
        if 'websocket' in self.conns.config.server_protos:
          if upgrade and upgrade[0].lower() == 'websocket':
            self.proto = 'websocket'

      if not self.conns.config.CheckClientAcls(self.address, conn=self):
        self.Send(HTTP_Unavailable('fe', self.proto, self.host,
                                   code=403, status='Forbidden',
                                   frame_url=self.conns.config.error_url),
                  try_flush=True)
        return False

      address = self.address
      if int(self.on_port) in self.conns.config.server_portalias:
        xfwdf = self.parser.Header('X-Forwarded-For')
        if xfwdf and address[0] == '127.0.0.1':
          address = (xfwdf[0], address[1])

      done = True
      if UserConn.FrontEnd(self, address,
                           self.proto, self.host, self.on_port,
                           self.parser.lines + lines, self.conns) is None:
        if self.proto.startswith('probe'):
          self.Send(HTTP_NoFeConnection(self.proto),
                    try_flush=True)
        else:
          self.Send(HTTP_Unavailable('fe', self.proto, self.host,
                                     frame_url=self.conns.config.error_url),
                    try_flush=True)
        return False

    # We are done!
    self.Cleanup(close=False)
    return True

  def ProcessTls(self, data, domain=None):
    if (not self.conns or
        not self.conns.config.CheckClientAcls(self.address, conn=self)):
      self.Send(TLS_Unavailable(forbidden=True), try_flush=True)
      return False

    if domain:
      domains = [domain]
    else:
      try:
        domains = self.GetSni(data)
        if not domains:
          domains = [self.conns.config.tls_default]
          if domains[0]:
            self.LogDebug('No SNI - trying: %s' % domains[0])
          else:
            domains = None
      except:
        # Probably insufficient data, just True and assume we'll have
        # better luck on the next round... but with a timeout.
        self.bad_loops += 1
        if self.bad_loops < 25:
          self.LogDebug('Error in ProcessTLS, will time out in 120 seconds.')
          self.conns.SetIdle(self, 120)
          return True
        else:
          self.LogDebug('Persistent error in ProcessTLS, aborting.')
          self.Send(TLS_Unavailable(unavailable=True), try_flush=True)
          return False

    if domains and domains[0] is not None:
      if UserConn.FrontEnd(self, self.address,
                           'https', domains[0], self.on_port,
                           [data], self.conns) is not None:
        # We are done!
        self.EatPeeked()
        self.Cleanup(close=False)
        return True
      else:
        # If we know how to terminate the TLS/SSL, do so!
        ctx = self.conns.config.GetTlsEndpointCtx(domains[0])
        if ctx:
          self.fd = socks.SSL_Connect(ctx, self.fd,
                                      accepted=True, server_side=True)
          self.peeking = False
          self.is_tls = False
          self.my_tls = True
          self.conns.SetIdle(self, 120)
          return True
        else:
          self.Send(TLS_Unavailable(unavailable=True), try_flush=True)
          return False

    self.Send(TLS_Unavailable(unavailable=True), try_flush=True)
    return False

  def ProcessFlashPolicyRequest(self, data):
    # FIXME: Should this be configurable?
    self.LogDebug('Sending friendly response to Flash Policy Request')
    self.Send('<cross-domain-policy>\n'
              ' <allow-access-from domain="*" to-ports="*" />\n'
              '</cross-domain-policy>\n',
              try_flush=True)
    return False

  def ProcessProto(self, data, proto, domain):
    if (not self.conns or
        not self.conns.config.CheckClientAcls(self.address, conn=self)):
      return False

    if UserConn.FrontEnd(self, self.address,
                         proto, domain, self.on_port,
                         [data], self.conns) is None:
      return False

    # We are done!
    self.Cleanup(close=False)
    return True


class UiConn(LineParser):

  STATE_PASSWORD = 0
  STATE_LIVE     = 1

  def __init__(self, fd, address, on_port, conns):
    LineParser.__init__(self, fd=fd, address=address, on_port=on_port)
    self.state = self.STATE_PASSWORD

    self.conns = conns
    self.conns.Add(self)
    self.lines = []
    self.qc = threading.Condition()

    self.challenge = sha1hex('%s%8.8x' % (globalSecret(),
                                          random.randint(0, 0x7FFFFFFD)+1))
    self.expect = signToken(token=self.challenge,
                            secret=self.conns.config.ConfigSecret(),
                            payload=self.challenge,
                            length=1000)
    self.LogDebug('Expecting: %s' % self.expect)
    self.Send('PageKite? %s\r\n' % self.challenge)

  def readline(self):
    self.qc.acquire()
    while not self.lines: self.qc.wait()
    line = self.lines.pop(0)
    self.qc.release()
    return line

  def write(self, data):
    self.conns.config.ui_wfile.write(data)
    self.Send(data)

  def Cleanup(self):
    self.conns.config.ui.wfile = self.conns.config.ui_wfile
    self.conns.config.ui.rfile = self.conns.config.ui_rfile
    self.lines = self.conns.config.ui_conn = None
    self.conns = None
    LineParser.Cleanup(self)

  def Disconnect(self):
    self.Send('Goodbye')
    self.Cleanup()

  def ProcessLine(self, line, lines):
    if self.state == self.STATE_LIVE:
      self.qc.acquire()
      self.lines.append(line)
      self.qc.notify()
      self.qc.release()
      return True
    elif self.state == self.STATE_PASSWORD:
      if line.strip() == self.expect:
        if self.conns.config.ui_conn: self.conns.config.ui_conn.Disconnect()
        self.conns.config.ui_conn = self
        self.conns.config.ui.wfile = self
        self.conns.config.ui.rfile = self
        self.state = self.STATE_LIVE
        self.Send('OK!\r\n')
        return True
      else:
        self.Send('Sorry.\r\n')
        return False
    else:
      return False


class RawConn(Selectable):
  """This class is a raw/timed connection."""

  def __init__(self, fd, address, on_port, conns):
    Selectable.__init__(self, fd, address, on_port)
    self.my_tls = False
    self.is_tls = False

    domain = conns.LastIpDomain(address[0])
    if domain and UserConn.FrontEnd(self, address, 'raw', domain, on_port,
                                    [], conns):
      self.Cleanup(close=False)
    else:
      self.Cleanup()


class Listener(Selectable):
  """This class listens for incoming connections and accepts them."""

  def __init__(self, host, port, conns, backlog=100,
                     connclass=UnknownConn, quiet=False, acl=None):
    Selectable.__init__(self, bind=(host, port), backlog=backlog)
    self.Log([('listen', '%s:%s' % (host, port))])
    if not quiet:
      conns.config.ui.Notify(' - Listening on %s:%s' % (host or '*', port))

    self.acl = acl
    self.acl_match = None

    self.connclass = connclass
    self.port = port
    self.conns = conns
    self.conns.Add(self)
    self.CountAs('listeners_live')

  def __str__(self):
    return '%s port=%s' % (Selectable.__str__(self), self.port)

  def __html__(self):
    return '<p>Listening on port %s for %s</p>' % (self.port, self.connclass)

  def check_acl(self, ipaddr, default=True):
    if self.acl:
      try:
        ipaddr = '%s' % ipaddr
        lc = 0
        for line in open(self.acl, 'r'):
          line = line.lower().strip()
          lc += 1
          if line.startswith('#') or not line:
            continue
          try:
            words = line.split()
            pattern, rule = words[:2]
            reason = ' '.join(words[2:])
            if ipaddr == pattern:
              self.acl_match = (lc, pattern, rule, reason)
              return bool('allow' in rule)
            elif re.compile(pattern).match(ipaddr):
              self.acl_match = (lc, pattern, rule, reason)
              return bool('allow' in rule)
          except IndexError:
            self.LogDebug('Invalid line %d in ACL %s' % (lc, self.acl))
      except:
        self.LogDebug('Failed to read/parse %s' % self.acl)
    self.acl_match = (0, '.*', default and 'allow' or 'reject', 'Default')
    return default

  def ReadData(self, maxread=None):
    try:
      self.last_activity = time.time()
      client, address = self.fd.accept()
      if client:
        if self.check_acl(address[0]):
          log_info = [('accept', '%s:%s' % (obfuIp(address[0]), address[1]))]
          uc = self.connclass(client, address, self.port, self.conns)
        else:
          log_info = [('reject', '%s:%s' % (obfuIp(address[0]), address[1]))]
          client.close()
        if self.acl:
          log_info.extend([('acl_line', '%s' % self.acl_match[0]),
                           ('reason', self.acl_match[3])])
        self.Log(log_info)
        return True

    except IOError, err:
      self.LogDebug('Listener::ReadData: error: %s (%s)' % (err, err.errno))

    except socket.error, (errno, msg):
      self.LogInfo('Listener::ReadData: error: %s (errno=%s)' % (msg, errno))

    except Exception, e:
      self.LogDebug('Listener::ReadData: %s' % e)

    return True

########NEW FILE########
__FILENAME__ = filters
"""
These are filters placed at the end of a tunnel for watching or modifying
the traffic.
"""
##############################################################################
LICENSE = """\
This file is part of pagekite.py.
Copyright 2010-2013, the Beanstalks Project ehf. and Bjarni Runar Einarsson

This program is free software: you can redistribute it and/or modify it under
the terms of the  GNU  Affero General Public License as published by the Free
Software Foundation, either version 3 of the License, or (at your option) any
later version.

This program is distributed in the hope that it will be useful,  but  WITHOUT
ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
FOR A PARTICULAR PURPOSE.  See the GNU Affero General Public License for more
details.

You should have received a copy of the GNU Affero General Public License
along with this program.  If not, see: <http://www.gnu.org/licenses/>
"""
##############################################################################
import re
import time
from pagekite.compat import *


class TunnelFilter:
  """Base class for watchers/filters for data going in/out of Tunnels."""

  IDLE_TIMEOUT = 1800

  def __init__(self, ui):
    self.sid = {}
    self.ui = ui

  def clean_idle_sids(self, now=None):
    now = now or time.time()
    for sid in self.sid.keys():
      if self.sid[sid]['_ts'] < now - self.IDLE_TIMEOUT:
        del self.sid[sid]

  def filter_set_sid(self, sid, info):
    now = time.time()
    if sid not in self.sid:
      self.sid[sid] = {}
    self.sid[sid].update(info)
    self.sid[sid]['_ts'] = now
    self.clean_idle_sids(now=now)

  def filter_data_in(self, tunnel, sid, data):
    if sid not in self.sid:
      self.sid[sid] = {}
    self.sid[sid]['_ts'] = time.time()
    return data

  def filter_data_out(self, tunnel, sid, data):
    if sid not in self.sid:
      self.sid[sid] = {}
    self.sid[sid]['_ts'] = time.time()
    return data


class TunnelWatcher(TunnelFilter):
  """Base class for watchers/filters for data going in/out of Tunnels."""

  def __init__(self, ui, watch_level=0):
    TunnelFilter.__init__(self, ui)
    self.watch_level = watch_level

  def format_data(self, data, level):
    if '\r\n\r\n' in data:
      head, tail = data.split('\r\n\r\n', 1)
      output = self.format_data(head, level)
      output[-1] += '\\r\\n'
      output.append('\\r\\n')
      if tail:
        output.extend(self.format_data(tail, level))
      return output
    else:
      output = data.encode('string_escape').replace('\\n', '\\n\n')
      if output.count('\\') > 0.15*len(output):
        if level > 2:
          output = [['', '']]
          count = 0
          for d in data:
            output[-1][0] += '%2.2x' % ord(d)
            output[-1][1] += '%c' % ((ord(d) > 31 and ord(d) < 127) and d or '.')
            count += 1
            if (count % 2) == 0:
              output[-1][0] += ' '
            if (count % 20) == 0:
              output.append(['', ''])
          return ['%-50s %s' % (l[0], l[1]) for l in output]
        else:
          return ['<< Binary bytes: %d >>' % len(data)]
      else:
        return output.strip().splitlines()

  def now(self):
    return ts_to_iso(int(10*time.time())/10.0
                     ).replace('T', ' ').replace('00000', '')

  def filter_data_in(self, tunnel, sid, data):
    if data and self.watch_level[0] > 0:
      self.ui.Notify('===[ INCOMING @ %s ]===' % self.now(),
                     color=self.ui.WHITE, prefix=' __')
      for line in self.format_data(data, self.watch_level[0]):
        self.ui.Notify(line, prefix=' <=', now=-1, color=self.ui.GREEN)
    return TunnelFilter.filter_data_in(self, tunnel, sid, data)

  def filter_data_out(self, tunnel, sid, data):
    if data and self.watch_level[0] > 1:
      self.ui.Notify('===[ OUTGOING @ %s ]===' % self.now(),
                     color=self.ui.WHITE, prefix=' __')
      for line in self.format_data(data, self.watch_level[0]):
        self.ui.Notify(line, prefix=' =>', now=-1, color=self.ui.BLUE)
    return TunnelFilter.filter_data_out(self, tunnel, sid, data)


class HttpHeaderFilter(TunnelFilter):
  """Filter that adds X-Forwarded-For and X-Forwarded-Proto to requests."""

  HTTP_HEADER = re.compile('(?ism)^(([A-Z]+) ([^\n]+) HTTP/\d+\.\d+\s*)$')
  DISABLE = 'rawheaders'

  def filter_data_in(self, tunnel, sid, data):
    info = self.sid.get(sid)
    if (info and
        info.get('proto') in ('http', 'http2', 'http3', 'websocket') and
        not info.get(self.DISABLE, False)):

      # FIXME: Check content-length and skip bodies entirely
      http_hdr = self.HTTP_HEADER.search(data)
      if http_hdr:
        data = self.filter_header_data_in(http_hdr, data, info)

    return TunnelFilter.filter_data_in(self, tunnel, sid, data)

  def filter_header_data_in(self, http_hdr, data, info):
    clean_headers = [
      r'(?mi)^(X-(PageKite|Forwarded)-(For|Proto|Port):)'
    ]
    add_headers = [
      'X-Forwarded-For: %s' % info.get('remote_ip', 'unknown'),
      'X-Forwarded-Proto: %s' % (info.get('using_tls') and 'https' or 'http'),
      'X-PageKite-Port: %s' % info.get('port', 0)
    ]

    if info.get('rewritehost', False):
      add_headers.append('Host: %s' % info.get('rewritehost'))
      clean_headers.append(r'(?mi)^(Host:)')

    if http_hdr.group(1).upper() in ('POST', 'PUT'):
      # FIXME: This is a bit ugly
      add_headers.append('Connection: close')
      clean_headers.append(r'(?mi)^(Connection|Keep-Alive):')
      info['rawheaders'] = True

    for hdr_re in clean_headers:
      data = re.sub(hdr_re, 'X-Old-\\1', data)

    return re.sub(self.HTTP_HEADER,
                  '\\1\n%s\r' % '\r\n'.join(add_headers),
                  data)


class HttpSecurityFilter(HttpHeaderFilter):
  """Filter that blocks known-to-be-dangerous requests."""

  DISABLE = 'trusted'
  HTTP_DANGER = re.compile('(?ism)^((get|post|put|patch|delete) '
                           # xampp paths, anything starting with /adm*
                           '((?:/+(?:xampp/|security/|licenses/|webalizer/|server-(?:status|info)|adm)'
                           '|[^\n]*/'
                             # WordPress admin pages
                             '(?:wp-admin/(?!admin-ajax|css/)|wp-config\.php'
                             # Hackzor tricks
                             '|system32/|\.\.|\.ht(?:access|pass)'
                             # phpMyAdmin and similar tools
                             '|(?:php|sql)?my(?:sql)?(?:adm|manager)'
                             # Setup pages for common PHP tools
                             '|(?:adm[^\n]*|install[^\n]*|setup)\.php)'
                           ')[^\n]*)'
                           ' HTTP/\d+\.\d+\s*)$')
  REJECT = 'PAGEKITE_REJECT_'

  def filter_header_data_in(self, http_hdr, data, info):
    danger = self.HTTP_DANGER.search(data)
    if danger:
      self.ui.Notify('BLOCKED: %s %s' % (danger.group(2), danger.group(3)),
                     color=self.ui.RED, prefix='***')
      self.ui.Notify('See https://pagekite.net/support/security/ for more'
                     ' details.')
      return self.REJECT+data
    else:
      return data

########NEW FILE########
__FILENAME__ = parsers
"""
Protocol parsers for classifying incoming network connections.
"""
##############################################################################
LICENSE = """\
This file is part of pagekite.py.
Copyright 2010-2013, the Beanstalks Project ehf. and Bjarni Runar Einarsson

This program is free software: you can redistribute it and/or modify it under
the terms of the  GNU  Affero General Public License as published by the Free
Software Foundation, either version 3 of the License, or (at your option) any
later version.

This program is distributed in the hope that it will be useful,  but  WITHOUT
ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
FOR A PARTICULAR PURPOSE.  See the GNU Affero General Public License for more
details.

You should have received a copy of the GNU Affero General Public License
along with this program.  If not, see: <http://www.gnu.org/licenses/>
"""
##############################################################################
from pagekite.compat import *
from pagekite.common import *
import pagekite.logging as logging

HTTP_METHODS = ['OPTIONS', 'CONNECT', 'GET', 'HEAD', 'POST', 'PUT', 'TRACE',
                'PROPFIND', 'PROPPATCH', 'MKCOL', 'DELETE', 'COPY', 'MOVE',
                'LOCK', 'UNLOCK', 'PING', 'PATCH']
HTTP_VERSIONS = ['HTTP/1.0', 'HTTP/1.1']


class BaseLineParser(object):
  """Base protocol parser class."""

  PROTO = 'unknown'
  PROTOS = ['unknown']
  PARSE_UNKNOWN = -2
  PARSE_FAILED = -1
  PARSE_OK = 100

  def __init__(self, lines=None, state=PARSE_UNKNOWN, proto=PROTO):
    self.state = state
    self.protocol = proto
    self.lines = []
    self.domain = None
    self.last_parser = self
    if lines is not None:
      for line in lines:
        if not self.Parse(line): break

  def ParsedOK(self):
    return (self.state == self.PARSE_OK)

  def Parse(self, line):
    self.lines.append(line)
    return False

  def ErrorReply(self, port=None):
    return ''


class MagicLineParser(BaseLineParser):
  """Parse an unknown incoming connection request, line-by-line."""

  PROTO = 'magic'

  def __init__(self, lines=None, state=BaseLineParser.PARSE_UNKNOWN,
                     parsers=[]):
    self.parsers = [p() for p in parsers]
    BaseLineParser.__init__(self, lines, state, self.PROTO)
    if self.last_parser == self:
      self.last_parser = self.parsers[-1]

  def ParsedOK(self):
    return self.last_parser.ParsedOK()

  def Parse(self, line):
    BaseLineParser.Parse(self, line)
    self.last_parser = self.parsers[-1]
    for p in self.parsers[:]:
      if not p.Parse(line):
        self.parsers.remove(p)
      elif p.ParsedOK():
        self.last_parser = p
        self.domain = p.domain
        self.protocol = p.protocol
        self.state = p.state
        self.parsers = [p]
        break

    if not self.parsers:
      logging.LogDebug('No more parsers!')

    return (len(self.parsers) > 0)


class HttpLineParser(BaseLineParser):
  """Parse an HTTP request, line-by-line."""

  PROTO = 'http'
  PROTOS = ['http']
  IN_REQUEST = 11
  IN_HEADERS = 12
  IN_BODY = 13
  IN_RESPONSE = 14

  def __init__(self, lines=None, state=IN_REQUEST, testbody=False):
    self.method = None
    self.path = None
    self.version = None
    self.code = None
    self.message = None
    self.headers = []
    self.body_result = testbody
    BaseLineParser.__init__(self, lines, state, self.PROTO)

  def ParseResponse(self, line):
    self.version, self.code, self.message = line.split()

    if not self.version.upper() in HTTP_VERSIONS:
      logging.LogDebug('Invalid version: %s' % self.version)
      return False

    self.state = self.IN_HEADERS
    return True

  def ParseRequest(self, line):
    self.method, self.path, self.version = line.split()

    if not self.method in HTTP_METHODS:
      logging.LogDebug('Invalid method: %s' % self.method)
      return False

    if not self.version.upper() in HTTP_VERSIONS:
      logging.LogDebug('Invalid version: %s' % self.version)
      return False

    self.state = self.IN_HEADERS
    return True

  def ParseHeader(self, line):
    if line in ('', '\r', '\n', '\r\n'):
      self.state = self.IN_BODY
      return True

    header, value = line.split(':', 1)
    if value and value.startswith(' '): value = value[1:]

    self.headers.append((header.lower(), value))
    return True

  def ParseBody(self, line):
    # Could be overridden by subclasses, for now we just play dumb.
    return self.body_result

  def ParsedOK(self):
    return (self.state == self.IN_BODY)

  def Parse(self, line):
    BaseLineParser.Parse(self, line)
    try:
      if (self.state == self.IN_RESPONSE):
        return self.ParseResponse(line)

      elif (self.state == self.IN_REQUEST):
        return self.ParseRequest(line)

      elif (self.state == self.IN_HEADERS):
        return self.ParseHeader(line)

      elif (self.state == self.IN_BODY):
        return self.ParseBody(line)

    except ValueError, err:
      logging.LogDebug('Parse failed: %s, %s, %s' % (self.state, err, self.lines))

    self.state = BaseLineParser.PARSE_FAILED
    return False

  def Header(self, header):
    return [h[1].strip() for h in self.headers if h[0] == header.lower()]


class FingerLineParser(BaseLineParser):
  """Parse an incoming Finger request, line-by-line."""

  PROTO = 'finger'
  PROTOS = ['finger', 'httpfinger']
  WANT_FINGER = 71

  def __init__(self, lines=None, state=WANT_FINGER):
    BaseLineParser.__init__(self, lines, state, self.PROTO)

  def ErrorReply(self, port=None):
    if port == 79:
      return ('PageKite wants to know, what domain?\n'
              'Try: finger user+domain@domain\n')
    else:
      return ''

  def Parse(self, line):
    BaseLineParser.Parse(self, line)
    if ' ' in line: return False
    if '+' in line:
      arg0, self.domain = line.strip().split('+', 1)
    elif '@' in line:
      arg0, self.domain = line.strip().split('@', 1)

    if self.domain:
      self.state = BaseLineParser.PARSE_OK
      self.lines[-1] = '%s\n' % arg0
      return True
    else:
      self.state = BaseLineParser.PARSE_FAILED
      return False


class IrcLineParser(BaseLineParser):
  """Parse an incoming IRC connection, line-by-line."""

  PROTO = 'irc'
  PROTOS = ['irc']
  WANT_USER = 61

  def __init__(self, lines=None, state=WANT_USER):
    self.seen = []
    BaseLineParser.__init__(self, lines, state, self.PROTO)

  def ErrorReply(self):
    return ':pagekite 451 :IRC Gateway requires user@HOST or nick@HOST\n'

  def Parse(self, line):
    BaseLineParser.Parse(self, line)
    if line in ('\n', '\r\n'): return True
    if self.state == IrcLineParser.WANT_USER:
      try:
        ocmd, arg = line.strip().split(' ', 1)
        cmd = ocmd.lower()
        self.seen.append(cmd)
        args = arg.split(' ')
        if cmd == 'pass':
          pass
        elif cmd in ('user', 'nick'):
          if '@' in args[0]:
            parts = args[0].split('@')
            self.domain = parts[-1]
            arg0 = '@'.join(parts[:-1])
          elif 'nick' in self.seen and 'user' in self.seen and not self.domain:
            raise Error('No domain found')

          if self.domain:
            self.state = BaseLineParser.PARSE_OK
            self.lines[-1] = '%s %s %s\n' % (ocmd, arg0, ' '.join(args[1:]))
        else:
          self.state = BaseLineParser.PARSE_FAILED
      except Exception, err:
        logging.LogDebug('Parse failed: %s, %s, %s' % (self.state, err, self.lines))
        self.state = BaseLineParser.PARSE_FAILED

    return (self.state != BaseLineParser.PARSE_FAILED)

########NEW FILE########
__FILENAME__ = proto
"""
PageKite protocol and HTTP protocol related code and constants.
"""
##############################################################################
LICENSE = """\
This file is part of pagekite.py.
Copyright 2010-2013, the Beanstalks Project ehf. and Bjarni Runar Einarsson

This program is free software: you can redistribute it and/or modify it under
the terms of the  GNU  Affero General Public License as published by the Free
Software Foundation, either version 3 of the License, or (at your option) any
later version.

This program is distributed in the hope that it will be useful,  but  WITHOUT
ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
FOR A PARTICULAR PURPOSE.  See the GNU Affero General Public License for more
details.

You should have received a copy of the GNU Affero General Public License
along with this program.  If not, see: <http://www.gnu.org/licenses/>
"""
##############################################################################
import base64
import os
import random
import struct
import time

from pagekite.compat import *
from pagekite.common import *
import pagekite.logging as logging


gSecret = None
def globalSecret():
  global gSecret
  if not gSecret:
    # This always works...
    gSecret = '%8.8x%s%8.8x' % (random.randint(0, 0x7FFFFFFE),
                                time.time(),
                                random.randint(0, 0x7FFFFFFE))

    # Next, see if we can augment that with some real randomness.
    try:
      newSecret = sha1hex(open('/dev/urandom').read(64) + gSecret)
      gSecret = newSecret
      logging.LogDebug('Seeded signatures using /dev/urandom, hooray!')
    except:
      try:
        newSecret = sha1hex(os.urandom(64) + gSecret)
        gSecret = newSecret
        logging.LogDebug('Seeded signatures using os.urandom(), hooray!')
      except:
        logging.LogInfo('WARNING: Seeding signatures with time.time() and random.randint()')

  return gSecret

TOKEN_LENGTH=36
def signToken(token=None, secret=None, payload='', timestamp=None,
              length=TOKEN_LENGTH):
  """
  This will generate a random token with a signature which could only have come
  from this server.  If a token is provided, it is re-signed so the original
  can be compared with what we would have generated, for verification purposes.

  If a timestamp is provided it will be embedded in the signature to a
  resolution of 10 minutes, and the signature will begin with the letter 't'

  Note: This is only as secure as random.randint() is random.
  """
  if not secret: secret = globalSecret()
  if not token: token = sha1hex('%s%8.8x' % (globalSecret(),
                                             random.randint(0, 0x7FFFFFFD)+1))
  if timestamp:
    tok = 't' + token[1:]
    ts = '%x' % int(timestamp/600)
    return tok[0:8] + sha1hex(secret + payload + ts + tok[0:8])[0:length-8]
  else:
    return token[0:8] + sha1hex(secret + payload + token[0:8])[0:length-8]

def checkSignature(sign='', secret='', payload=''):
  """
  Check a signature for validity. When using timestamped signatures, we only
  accept signatures from the current and previous windows.
  """
  if sign[0] == 't':
    ts = int(time.time())
    for window in (0, 1):
      valid = signToken(token=sign, secret=secret, payload=payload,
                        timestamp=(ts-(window*600)))
      if sign == valid: return True
    return False
  else:
    valid = signToken(token=sign, secret=secret, payload=payload)
    return sign == valid

def PageKiteRequestHeaders(server, backends, tokens=None, testtoken=None):
  req = []
  tokens = tokens or {}
  for d in backends.keys():
    if (backends[d][BE_BHOST] and
        backends[d][BE_SECRET] and
        backends[d][BE_STATUS] not in BE_INACTIVE):

      # A stable (for replay on challenge) but unguessable salt.
      my_token = sha1hex(globalSecret() + server + backends[d][BE_SECRET]
                         )[:TOKEN_LENGTH]

      # This is the challenge (salt) from the front-end, if any.
      server_token = d in tokens and tokens[d] or ''

      # Our payload is the (proto, name) combined with both salts
      data = '%s:%s:%s' % (d, my_token, server_token)

      # Sign the payload with the shared secret (random salt).
      sign = signToken(secret=backends[d][BE_SECRET],
                       payload=data,
                       token=testtoken)

      req.append('X-PageKite: %s:%s\r\n' % (data, sign))
  return req

def HTTP_PageKiteRequest(server, backends, tokens=None, nozchunks=False,
                         tls=False, testtoken=None, replace=None):
  req = ['CONNECT PageKite:1 HTTP/1.0\r\n',
         'X-PageKite-Features: AddKites\r\n',
         'X-PageKite-Version: %s\r\n' % APPVER]

  if not nozchunks:
    req.append('X-PageKite-Features: ZChunks\r\n')
  if replace:
    req.append('X-PageKite-Replace: %s\r\n' % replace)
  if tls:
    req.append('X-PageKite-Features: TLS\r\n')

  req.extend(PageKiteRequestHeaders(server, backends,
                                    tokens=tokens, testtoken=testtoken))
  req.append('\r\n')
  return ''.join(req)

def HTTP_ResponseHeader(code, title, mimetype='text/html'):
  if mimetype.startswith('text/') and ';' not in mimetype:
    mimetype += ('; charset=%s' % DEFAULT_CHARSET)
  return ('HTTP/1.1 %s %s\r\nContent-Type: %s\r\nPragma: no-cache\r\n'
          'Expires: 0\r\nCache-Control: no-store\r\nConnection: close'
          '\r\n') % (code, title, mimetype)

def HTTP_Header(name, value):
  return '%s: %s\r\n' % (name, value)

def HTTP_StartBody():
  return '\r\n'

def HTTP_ConnectOK():
  return 'HTTP/1.0 200 Connection Established\r\n\r\n'

def HTTP_ConnectBad(code=503, status='Unavailable'):
  return 'HTTP/1.0 %s %s\r\n\r\n' % (code, status)

def HTTP_Response(code, title, body,
                  mimetype='text/html', headers=None, trackable=False):
  data = [HTTP_ResponseHeader(code, title, mimetype)]
  if headers: data.extend(headers)
  if trackable: data.extend('X-PageKite-UUID: %s\r\n' % MAGIC_UUID)
  data.extend([HTTP_StartBody(), ''.join(body)])
  return ''.join(data)

def HTTP_NoFeConnection(proto):
  if proto.endswith('.json'):
    (mt, content) = ('application/json', '{"pagekite-status": "down-fe"}')
  else:
    (mt, content) = ('image/gif', base64.decodestring(
      'R0lGODlhCgAKAMQCAN4hIf/+/v///+EzM+AuLvGkpORISPW+vudgYOhiYvKpqeZY'
      'WPbAwOdaWup1dfOurvW7u++Rkepycu6PjwAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA'
      'AAAAAAAAAAAAAAAAACH5BAEAAAIALAAAAAAKAAoAAAUtoCAcyEA0jyhEQOs6AuPO'
      'QJHQrjEAQe+3O98PcMMBDAdjTTDBSVSQEmGhEIUAADs='))
  return HTTP_Response(200, 'OK', content, mimetype=mt,
      headers=[HTTP_Header('X-PageKite-Status', 'Down-FE'),
               HTTP_Header('Access-Control-Allow-Origin', '*')])

def HTTP_NoBeConnection(proto):
  if proto.endswith('.json'):
    (mt, content) = ('application/json', '{"pagekite-status": "down-be"}')
  else:
    (mt, content) = ('image/gif', base64.decodestring(
      'R0lGODlhCgAKAPcAAI9hE6t2Fv/GAf/NH//RMf/hd7u6uv/mj/ntq8XExMbFxc7N'
      'zc/Ozv/xwfj31+jn5+vq6v///////wAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA'
      'AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA'
      'AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA'
      'AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA'
      'AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA'
      'AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA'
      'AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA'
      'AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA'
      'AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA'
      'AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA'
      'AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA'
      'AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA'
      'AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA'
      'AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA'
      'AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA'
      'AAAAAAAAAAAAAAAAACH5BAEAABIALAAAAAAKAAoAAAhDACUIlBAgwMCDARo4MHiQ'
      '4IEGDAcGKAAAAESEBCoiiBhgQEYABzYK7OiRQIEDBgMIEDCgokmUKlcOKFkgZcGb'
      'BSUEBAA7'))
  return HTTP_Response(200, 'OK', content, mimetype=mt,
      headers=[HTTP_Header('X-PageKite-Status', 'Down-BE'),
               HTTP_Header('Access-Control-Allow-Origin', '*')])

def HTTP_GoodBeConnection(proto):
  if proto.endswith('.json'):
    (mt, content) = ('application/json', '{"pagekite-status": "ok"}')
  else:
    (mt, content) = ('image/gif', base64.decodestring(
      'R0lGODlhCgAKANUCAEKtP0StQf8AAG2/a97w3qbYpd/x3mu/aajZp/b79vT69Mnn'
      'yK7crXTDcqraqcfmxtLr0VG0T0ivRpbRlF24Wr7jveHy4Pv9+53UnPn8+cjnx4LI'
      'gNfu1v///37HfKfZpq/crmG6XgAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA'
      'AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA'
      'AAAAAAAAAAAAAAAAACH5BAEAAAIALAAAAAAKAAoAAAZIQIGAUDgMEASh4BEANAGA'
      'xRAaaHoYAAPCCZUoOIDPAdCAQhIRgJGiAG0uE+igAMB0MhYoAFmtJEJcBgILVU8B'
      'GkpEAwMOggJBADs='))
  return HTTP_Response(200, 'OK', content, mimetype=mt,
      headers=[HTTP_Header('X-PageKite-Status', 'OK'),
               HTTP_Header('Access-Control-Allow-Origin', '*')])

def HTTP_Unavailable(where, proto, domain, comment='', frame_url=None,
                     code=503, status='Unavailable', headers=None):
  if code == 401:
    headers = headers or []
    headers.append(HTTP_Header('WWW-Authenticate', 'Basic realm=PageKite'))
  message = ''.join(['<h1>Sorry! (', where, ')</h1>',
                     '<p>The ', proto.upper(),' <a href="', WWWHOME, '">',
                     '<i>PageKite</i></a> for <b>', domain,
                     '</b> is unavailable at the moment.</p>',
                     '<p>Please try again later.</p><!-- ', comment, ' -->'])
  if frame_url:
    if '?' in frame_url:
      frame_url += '&where=%s&proto=%s&domain=%s' % (where.upper(), proto, domain)
    return HTTP_Response(code, status,
                         ['<html><frameset cols="*">',
                          '<frame target="_top" src="', frame_url, '" />',
                          '<noframes>', message, '</noframes>',
                          '</frameset></html>\n'], headers=headers)
  else:
    return HTTP_Response(code, status,
                         ['<html><body>', message, '</body></html>\n'],
                         headers=headers)

def TLS_Unavailable(forbidden=False, unavailable=False):
  """Generate a TLS alert record aborting this connectin."""
  # FIXME: Should we really be ignoring forbidden and unavailable?
  # Unfortunately, Chrome/ium only honors code 49, any other code will
  # cause it to transparently retry with SSLv3. So although this is a
  # bit misleading, this is what we send...
  return struct.pack('>BBBBBBB', 0x15, 3, 3, 0, 2, 2, 49) # 49 = Access denied

########NEW FILE########
__FILENAME__ = selectables
"""
Selectables are low level base classes which cooperate with our select-loop.
"""
##############################################################################
LICENSE = """\
This file is part of pagekite.py.
Copyright 2010-2013, the Beanstalks Project ehf. and Bjarni Runar Einarsson

This program is free software: you can redistribute it and/or modify it under
the terms of the  GNU  Affero General Public License as published by the Free
Software Foundation, either version 3 of the License, or (at your option) any
later version.

This program is distributed in the hope that it will be useful,  but  WITHOUT
ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
FOR A PARTICULAR PURPOSE.  See the GNU Affero General Public License for more
details.

You should have received a copy of the GNU Affero General Public License
along with this program.  If not, see: <http://www.gnu.org/licenses/>
"""
##############################################################################
import errno
import struct
import threading
import time
import zlib

from pagekite.compat import *
from pagekite.common import *
import pagekite.logging as logging
import pagekite.compat as compat
import pagekite.common as common


def obfuIp(ip):
  quads = ('%s' % ip).replace(':', '.').split('.')
  return '~%s' % '.'.join([q for q in quads[-2:]])


SELECTABLE_LOCK = threading.Lock()
SELECTABLE_ID = 0
SELECTABLES = {}
def getSelectableId(what):
  global SELECTABLES, SELECTABLE_ID, SELECTABLE_LOCK
  try:
    SELECTABLE_LOCK.acquire()
    count = 0
    while SELECTABLE_ID in SELECTABLES:
      SELECTABLE_ID += 1
      SELECTABLE_ID %= 0x10000
      if (SELECTABLE_ID % 0x00800) == 0:
        logging.LogDebug('Selectable map: %s' % (SELECTABLES, ))
      count += 1
      if count > 0x10001:
        raise ValueError('Too many conns!')
    SELECTABLES[SELECTABLE_ID] = what
    return SELECTABLE_ID
  finally:
    SELECTABLE_LOCK.release()


class Selectable(object):
  """A wrapper around a socket, for use with select."""

  HARMLESS_ERRNOS = (errno.EINTR, errno.EAGAIN, errno.ENOMEM, errno.EBUSY,
                     errno.EDEADLK, errno.EWOULDBLOCK, errno.ENOBUFS,
                     errno.EALREADY)

  def __init__(self, fd=None, address=None, on_port=None, maxread=16*1024,
                     ui=None, tracked=True, bind=None, backlog=100):
    self.fd = None

    try:
      self.SetFD(fd or rawsocket(socket.AF_INET6, socket.SOCK_STREAM), six=True)
      if bind:
        self.fd.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.fd.bind(bind)
        self.fd.listen(backlog)
        self.fd.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    except:
      self.SetFD(fd or rawsocket(socket.AF_INET, socket.SOCK_STREAM))
      if bind:
        self.fd.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.fd.bind(bind)
        self.fd.listen(backlog)
        self.fd.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    self.address = address
    self.on_port = on_port
    self.created = self.bytes_logged = time.time()
    self.last_activity = 0
    self.dead = False
    self.ui = ui

    # Quota-related stuff
    self.quota = None
    self.q_conns = None
    self.q_days = None

    # Read-related variables
    self.maxread = maxread
    self.read_bytes = self.all_in = 0
    self.read_eof = False
    self.peeking = False
    self.peeked = 0

    # Write-related variables
    self.wrote_bytes = self.all_out = 0
    self.write_blocked = ''
    self.write_speed = 102400
    self.write_eof = False
    self.write_retry = None

    # Flow control v1
    self.throttle_until = (time.time() - 1)
    self.max_read_speed = 96*1024
    # Flow control v2
    self.acked_kb_delta = 0

    # Compression stuff
    self.lock = threading.Lock()
    self.zw = None
    self.zlevel = 1
    self.zreset = False

    # Logging
    self.alt_id = None
    self.countas = 'selectables_live'
    self.sid = self.gsid = getSelectableId(self.countas)

    if address:
      addr = address or ('x.x.x.x', 'x')
      self.log_id = 's%x/%s:%s' % (self.sid, obfuIp(addr[0]), addr[1])
    else:
      self.log_id = 's%x' % self.sid

    if common.gYamon:
      common.gYamon.vadd(self.countas, 1)
      common.gYamon.vadd('selectables', 1)

  def CountAs(self, what):
    if common.gYamon:
      common.gYamon.vadd(self.countas, -1)
      common.gYamon.vadd(what, 1)
    self.countas = what
    global SELECTABLES
    SELECTABLES[self.gsid] = '%s %s' % (self.countas, self)

  def Cleanup(self, close=True):
    self.peeked = self.zw = ''
    self.Die(discard_buffer=True)
    if close:
      if self.fd:
        if logging.DEBUG_IO:
          self.LogDebug('Closing FD: %s' % self)
        self.fd.close()
    self.fd = None
    if not self.dead:
      self.dead = True
      self.CountAs('selectables_dead')
      if close:
        self.LogTraffic(final=True)

  def __del__(self):
    try:
      if common.gYamon:
        common.gYamon.vadd(self.countas, -1)
        common.gYamon.vadd('selectables', -1)
    except AttributeError:
      pass
    try:
      global SELECTABLES
      del SELECTABLES[self.gsid]
    except (KeyError, TypeError):
      pass

  def __str__(self):
    return '%s: %s<%s%s%s>' % (self.log_id, self.__class__,
                               self.read_eof and '-' or 'r',
                               self.write_eof and '-' or 'w',
                               len(self.write_blocked))

  def __html__(self):
    try:
      peer = self.fd.getpeername()
      sock = self.fd.getsockname()
    except:
      peer = ('x.x.x.x', 'x')
      sock = ('x.x.x.x', 'x')

    return ('<b>Outgoing ZChunks</b>: %s<br>'
            '<b>Buffered bytes</b>: %s<br>'
            '<b>Remote address</b>: %s<br>'
            '<b>Local address</b>: %s<br>'
            '<b>Bytes in / out</b>: %s / %s<br>'
            '<b>Created</b>: %s<br>'
            '<b>Status</b>: %s<br>'
            '\n') % (self.zw and ('level %d' % self.zlevel) or 'off',
                     len(self.write_blocked),
                     self.dead and '-' or (obfuIp(peer[0]), peer[1]),
                     self.dead and '-' or (obfuIp(sock[0]), sock[1]),
                     self.all_in + self.read_bytes,
                     self.all_out + self.wrote_bytes,
                     time.strftime('%Y-%m-%d %H:%M:%S',
                                   time.localtime(self.created)),
                     self.dead and 'dead' or 'alive')

  def ResetZChunks(self):
    if self.zw:
      self.zreset = True
      self.zw = zlib.compressobj(self.zlevel)

  def EnableZChunks(self, level=1):
    self.zlevel = level
    self.zw = zlib.compressobj(level)

  def SetFD(self, fd, six=False):
    if self.fd:
      self.fd.close()
    self.fd = fd
    self.fd.setblocking(0)
    try:
      if six:
        self.fd.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, 0)
      # This hurts mobile devices, let's try living without it
      #self.fd.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
      #self.fd.setsockopt(socket.SOL_TCP, socket.TCP_KEEPIDLE, 60)
      #self.fd.setsockopt(socket.SOL_TCP, socket.TCP_KEEPCNT, 10)
      #self.fd.setsockopt(socket.SOL_TCP, socket.TCP_KEEPINTVL, 1)
    except:
      pass

  def SetConn(self, conn):
    self.SetFD(conn.fd)
    self.log_id = conn.log_id
    self.read_bytes = conn.read_bytes
    self.wrote_bytes = conn.wrote_bytes

  def Log(self, values):
    if self.log_id: values.append(('id', self.log_id))
    logging.Log(values)

  def LogError(self, error, params=None):
    values = params or []
    if self.log_id: values.append(('id', self.log_id))
    logging.LogError(error, values)

  def LogDebug(self, message, params=None):
    values = params or []
    if self.log_id: values.append(('id', self.log_id))
    logging.LogDebug(message, values)

  def LogInfo(self, message, params=None):
    values = params or []
    if self.log_id: values.append(('id', self.log_id))
    logging.LogInfo(message, values)

  def LogTrafficStatus(self, final=False):
    if self.ui:
      self.ui.Status('traffic')

  def LogTraffic(self, final=False):
    if self.wrote_bytes or self.read_bytes:
      now = time.time()
      self.all_out += self.wrote_bytes
      self.all_in += self.read_bytes

      self.LogTrafficStatus(final)

      if common.gYamon:
        common.gYamon.vadd("bytes_all", self.wrote_bytes
                                        + self.read_bytes, wrap=1000000000)

      if final:
        self.Log([('wrote', '%d' % self.wrote_bytes),
                  ('wbps', '%d' % self.write_speed),
                  ('read', '%d' % self.read_bytes),
                  ('eof', '1')])
      else:
        self.Log([('wrote', '%d' % self.wrote_bytes),
                  ('wbps', '%d' % self.write_speed),
                  ('read', '%d' % self.read_bytes)])

      self.bytes_logged = now
      self.wrote_bytes = self.read_bytes = 0
    elif final:
      self.Log([('eof', '1')])

    global SELECTABLES
    SELECTABLES[self.gsid] = '%s %s' % (self.countas, self)

  def SayHello(self):
    pass

  def ProcessData(self, data):
    self.LogError('Selectable::ProcessData: Should be overridden!')
    return False

  def ProcessEof(self):
    global SELECTABLES
    SELECTABLES[self.gsid] = '%s %s' % (self.countas, self)
    if self.read_eof and self.write_eof and not self.write_blocked:
      self.Cleanup()
      return False
    return True

  def ProcessEofRead(self):
    self.read_eof = True
    self.LogError('Selectable::ProcessEofRead: Should be overridden!')
    return False

  def ProcessEofWrite(self):
    self.write_eof = True
    self.LogError('Selectable::ProcessEofWrite: Should be overridden!')
    return False

  def EatPeeked(self, eat_bytes=None, keep_peeking=False):
    if not self.peeking: return
    if eat_bytes is None: eat_bytes = self.peeked
    discard = ''
    while len(discard) < eat_bytes:
      try:
        discard += self.fd.recv(eat_bytes - len(discard))
      except socket.error, (errno, msg):
        self.LogInfo('Error reading (%d/%d) socket: %s (errno=%s)' % (
                       eat_bytes, self.peeked, msg, errno))
        time.sleep(0.1)

    if logging.DEBUG_IO:
      print '===[ ATE %d PEEKED BYTES ]===\n' % eat_bytes
    self.peeked -= eat_bytes
    self.peeking = keep_peeking
    return

  def ReadData(self, maxread=None):
    if self.read_eof:
      return False

    now = time.time()
    maxread = maxread or self.maxread
    flooded = self.Flooded(now)
    if flooded > self.max_read_speed and not self.acked_kb_delta:
      # FIXME: This is v1 flow control, kill it when 0.4.7 is "everywhere"
      last = self.throttle_until
      # Disable local throttling for really slow connections; remote
      # throttles (trigged by blocked sockets) still work.
      if self.max_read_speed > 1024:
        self.AutoThrottle()
        maxread = 1024
      if now > last and self.all_in > 2*self.max_read_speed:
        self.max_read_speed *= 1.25
        self.max_read_speed += maxread

    try:
      if self.peeking:
        data = self.fd.recv(maxread, socket.MSG_PEEK)
        self.peeked = len(data)
        if logging.DEBUG_IO:
          print '<== PEEK =[%s]==(\n%s)==' % (self, data[:160])
      else:
        data = self.fd.recv(maxread)
        if logging.DEBUG_IO:
          print ('<== IN =[%s @ %dbps]==(\n%s)=='
                 ) % (self, self.max_read_speed, data[:160])
    except (SSL.WantReadError, SSL.WantWriteError), err:
      return True
    except IOError, err:
      if err.errno not in self.HARMLESS_ERRNOS:
        self.LogDebug('Error reading socket: %s (%s)' % (err, err.errno))
        return False
      else:
        return True
    except (SSL.Error, SSL.ZeroReturnError, SSL.SysCallError), err:
      self.LogDebug('Error reading socket (SSL): %s' % err)
      return False
    except socket.error, (errno, msg):
      if errno in self.HARMLESS_ERRNOS:
        return True
      else:
        self.LogInfo('Error reading socket: %s (errno=%s)' % (msg, errno))
        return False

    self.last_activity = now
    if data is None or data == '':
      self.read_eof = True
      if logging.DEBUG_IO:
        print '<== IN =[%s]==(EOF)==' % self
      return self.ProcessData('')
    else:
      if not self.peeking:
        self.read_bytes += len(data)
        if self.acked_kb_delta:
          self.acked_kb_delta += (len(data)/1024)
        if self.read_bytes > logging.LOG_THRESHOLD: self.LogTraffic()
      return self.ProcessData(data)

  def Flooded(self, now=None):
    delta = ((now or time.time()) - self.created)
    if delta >= 1:
      flooded = self.read_bytes + self.all_in
      flooded -= self.max_read_speed * 0.95 * delta
      return flooded
    else:
      return 0

  def RecordProgress(self, skb, bps):
    if skb >= 0:
      all_read = (self.all_in + self.read_bytes) / 1024
      if self.acked_kb_delta:
        self.acked_kb_delta = max(1, all_read - skb)
        self.LogDebug('Delta is: %d' % self.acked_kb_delta)
    elif bps >= 0:
      self.Throttle(max_speed=bps, remote=True)

  def Throttle(self, max_speed=None, remote=False, delay=0.2):
    if max_speed:
      self.max_read_speed = max_speed

    flooded = max(-1, self.Flooded())
    if self.max_read_speed:
      delay = min(10, max(0.1, flooded/self.max_read_speed))
      if flooded < 0: delay = 0

    if delay:
      ot = self.throttle_until
      self.throttle_until = time.time() + delay
      if ((self.throttle_until - ot) > 30 or
          (int(ot) != int(self.throttle_until) and delay > 8)):
        self.LogInfo('Throttled %.1fs until %x (flood=%d, bps=%s, %s)' % (
                     delay, self.throttle_until, flooded,
                     self.max_read_speed, remote and 'remote' or 'local'))

    return True

  def AutoThrottle(self, max_speed=None, remote=False, delay=0.2):
    return self.Throttle(max_speed, remote, delay)

  def Send(self, data, try_flush=False, activity=False,
                       just_buffer=False, allow_blocking=False):
    self.write_speed = int((self.wrote_bytes + self.all_out)
                           / max(1, (time.time() - self.created)))

    # If we're already blocked, just buffer unless explicitly asked to flush.
    if ((just_buffer) or
        ((not try_flush) and
         (len(self.write_blocked) > 0 or compat.SEND_ALWAYS_BUFFERS))):
      self.write_blocked += str(''.join(data))
      return True

    sending = ''.join([self.write_blocked, str(''.join(data))])
    self.write_blocked = ''
    sent_bytes = 0
    if sending:
      try:
        want_send = self.write_retry or min(len(sending), SEND_MAX_BYTES)
        sent_bytes = self.fd.send(sending[:want_send])
        if logging.DEBUG_IO:
          print ('==> OUT =[%s: %d/%d bytes]==(\n%s)=='
                 ) % (self, sent_bytes, want_send, sending[:min(160, sent_bytes)])
        self.wrote_bytes += sent_bytes
        self.write_retry = None
      except (SSL.WantWriteError, SSL.WantReadError), err:
        if logging.DEBUG_IO:
          print '=== WRITE SSL RETRY: =[%s: %s bytes]==' % (self, want_send)
        self.write_retry = want_send
      except IOError, err:
        if err.errno not in self.HARMLESS_ERRNOS:
          self.LogInfo('Error sending: %s' % err)
          self.ProcessEofWrite()
          return False
        else:
          if logging.DEBUG_IO:
            print '=== WRITE HICCUP: =[%s: %s bytes]==' % (self, want_send)
          self.write_retry = want_send
      except socket.error, (errno, msg):
        if errno not in self.HARMLESS_ERRNOS:
          self.LogInfo('Error sending: %s (errno=%s)' % (msg, errno))
          self.ProcessEofWrite()
          return False
        else:
          if logging.DEBUG_IO:
            print '=== WRITE HICCUP: =[%s: %s bytes]==' % (self, want_send)
          self.write_retry = want_send
      except (SSL.Error, SSL.ZeroReturnError, SSL.SysCallError), err:
        self.LogInfo('Error sending (SSL): %s' % err)
        self.ProcessEofWrite()
        return False

    if activity:
      self.last_activity = time.time()

    self.write_blocked = sending[sent_bytes:]

    if self.wrote_bytes >= logging.LOG_THRESHOLD:
      self.LogTraffic()

    if self.write_eof and not self.write_blocked:
      self.ProcessEofWrite()
    return True

  def SendChunked(self, data, compress=True, zhistory=None, just_buffer=False):
    rst = ''
    if self.zreset:
      self.zreset = False
      rst = 'R'

    # Stop compressing streams that just get bigger.
    if zhistory and (zhistory[0] < zhistory[1]): compress = False
    try:
      try:
        if self.lock:
          self.lock.acquire()
        sdata = ''.join(data)
        if self.zw and compress and len(sdata) > 64:
          try:
            zdata = self.zw.compress(sdata) + self.zw.flush(zlib.Z_SYNC_FLUSH)
            if zhistory:
              zhistory[0] = len(sdata)
              zhistory[1] = len(zdata)
            return self.Send(['%xZ%x%s\r\n' % (len(sdata), len(zdata), rst), zdata],
                             activity=False,
                             try_flush=(not just_buffer), just_buffer=just_buffer)
          except zlib.error:
            logging.LogError('Error compressing, resetting ZChunks.')
            self.ResetZChunks()

        return self.Send(['%x%s\r\n' % (len(sdata), rst), sdata],
                         activity=False,
                         try_flush=(not just_buffer), just_buffer=just_buffer)
      except UnicodeDecodeError:
        logging.LogError('UnicodeDecodeError in SendChunked, wtf?')
        return False
    finally:
      if self.lock:
        self.lock.release()

  def Flush(self, loops=50, wait=False, allow_blocking=False):
    while (loops != 0 and
           len(self.write_blocked) > 0 and
           self.Send([], try_flush=True, activity=False,
                         allow_blocking=allow_blocking)):
      if wait and len(self.write_blocked) > 0:
        time.sleep(0.1)
      logging.LogDebug('Flushing...')
      loops -= 1

    if self.write_blocked: return False
    return True

  def IsReadable(s, now):
    return (s.fd and (not s.read_eof)
                 and (s.acked_kb_delta < 64)  # FIXME
                 and (s.throttle_until <= now))

  def IsBlocked(s):
    return (s.fd and (len(s.write_blocked) > 0))

  def IsDead(s):
    return (s.read_eof and s.write_eof and not s.write_blocked)

  def Die(self, discard_buffer=False):
    if discard_buffer:
      self.write_blocked = ''
    self.read_eof = self.write_eof = True
    return True


class LineParser(Selectable):
  """A Selectable which parses the input as lines of text."""

  def __init__(self, fd=None, address=None, on_port=None,
                     ui=None, tracked=True):
    Selectable.__init__(self, fd, address, on_port, ui=ui, tracked=tracked)
    self.leftovers = ''

  def __html__(self):
    return Selectable.__html__(self)

  def Cleanup(self, close=True):
    Selectable.Cleanup(self, close=close)
    self.leftovers = ''

  def ProcessData(self, data):
    lines = (self.leftovers+data).splitlines(True)
    self.leftovers = ''

    while lines:
      line = lines.pop(0)
      if line.endswith('\n'):
        if self.ProcessLine(line, lines) is False:
          return False
      else:
        if not self.peeking: self.leftovers += line

    if self.read_eof: return self.ProcessEofRead()
    return True

  def ProcessLine(self, line, lines):
    self.LogError('LineParser::ProcessLine: Should be overridden!')
    return False


TLS_CLIENTHELLO = '%c' % 026
SSL_CLIENTHELLO = '\x80'
MINECRAFT_HANDSHAKE = '%c' % (0x02, )
FLASH_POLICY_REQ = '<policy-file-request/>'

# FIXME: XMPP support
class MagicProtocolParser(LineParser):
  """A Selectable which recognizes HTTP, TLS or XMPP preambles."""

  def __init__(self, fd=None, address=None, on_port=None, ui=None):
    LineParser.__init__(self, fd, address, on_port, ui=ui, tracked=False)
    self.leftovers = ''
    self.might_be_tls = True
    self.is_tls = False
    self.my_tls = False

  def __html__(self):
    return ('<b>Detected TLS</b>: %s<br>'
            '%s') % (self.is_tls,
                     LineParser.__html__(self))

  # FIXME: DEPRECATE: Make this all go away, switch to CONNECT.
  def ProcessMagic(self, data):
    args = {}
    try:
      prefix, words, data = data.split('\r\n', 2)
      for arg in words.split('; '):
        key, val = arg.split('=', 1)
        args[key] = val

      self.EatPeeked(eat_bytes=len(prefix)+2+len(words)+2)
    except ValueError, e:
      return True

    try:
      port = 'port' in args and args['port'] or None
      if port: self.on_port = int(port)
    except ValueError, e:
      return False

    proto = 'proto' in args and args['proto'] or None
    if proto in ('http', 'http2', 'http3', 'websocket'):
      return LineParser.ProcessData(self, data)

    domain = 'domain' in args and args['domain'] or None
    if proto == 'https': return self.ProcessTls(data, domain)
    if proto == 'raw' and domain: return self.ProcessProto(data, 'raw', domain)
    return False

  def ProcessData(self, data):
    # Uncomment when adding support for new protocols:
    #
    #self.LogDebug(('DATA: >%s<'
    #               ) % ' '.join(['%2.2x' % ord(d) for d in data]))

    if data.startswith(MAGIC_PREFIX):
      return self.ProcessMagic(data)

    if self.might_be_tls:
      self.might_be_tls = False
      if not (data.startswith(TLS_CLIENTHELLO) or
              data.startswith(SSL_CLIENTHELLO)):
        self.EatPeeked()

        # FIXME: These only work if the full policy request or minecraft
        #        handshake are present in the first data packet.
        if data.startswith(FLASH_POLICY_REQ):
          return self.ProcessFlashPolicyRequest(data)

        if data.startswith(MINECRAFT_HANDSHAKE):
          user, server, port = self.GetMinecraftInfo(data)
          if user and server:
            return self.ProcessProto(data, 'minecraft', server)

        return LineParser.ProcessData(self, data)

      self.is_tls = True

    if self.is_tls:
      return self.ProcessTls(data)
    else:
      self.EatPeeked()
      return LineParser.ProcessData(self, data)

  def GetMsg(self, data):
    mtype, ml24, mlen = struct.unpack('>BBH', data[0:4])
    mlen += ml24 * 0x10000
    return mtype, data[4:4+mlen], data[4+mlen:]

  def GetClientHelloExtensions(self, msg):
    # Ugh, so many magic numbers! These are accumulated sizes of
    # the different fields we are ignoring in the TLS headers.
    slen = struct.unpack('>B', msg[34])[0]
    cslen = struct.unpack('>H', msg[35+slen:37+slen])[0]
    cmlen = struct.unpack('>B', msg[37+slen+cslen])[0]
    extofs = 34+1+2+1+2+slen+cslen+cmlen
    if extofs < len(msg): return msg[extofs:]
    return None

  def GetSniNames(self, extensions):
    names = []
    while extensions:
      etype, elen = struct.unpack('>HH', extensions[0:4])
      if etype == 0:
        # OK, we found an SNI extension, get the list.
        namelist = extensions[6:4+elen]
        while namelist:
          ntype, nlen = struct.unpack('>BH', namelist[0:3])
          if ntype == 0: names.append(namelist[3:3+nlen].lower())
          namelist = namelist[3+nlen:]
      extensions = extensions[4+elen:]
    return names

  def GetSni(self, data):
    hello, vmajor, vminor, mlen = struct.unpack('>BBBH', data[0:5])
    data = data[5:]
    sni = []
    while data:
      mtype, msg, data = self.GetMsg(data)
      if mtype == 1:
        # ClientHello!
        sni.extend(self.GetSniNames(self.GetClientHelloExtensions(msg)))
    return sni

  def GetMinecraftInfo(self, data):
    try:
      (packet, version, unlen) = struct.unpack('>bbh', data[0:4])
      unlen *= 2
      (hnlen, ) = struct.unpack('>h', data[4+unlen:6+unlen])
      hnlen *= 2
      (port, ) = struct.unpack('>i', data[6+unlen+hnlen:10+unlen+hnlen])
      uname = data[4:4+unlen].decode('utf_16_be').encode('utf-8')
      sname = data[6+unlen:6+hnlen+unlen].decode('utf_16_be').encode('utf-8')
      return uname, sname, port
    except:
      return None, None, None

  def ProcessFlashPolicyRequest(self, data):
    self.LogError('MagicProtocolParser::ProcessFlashPolicyRequest: Should be overridden!')
    return False

  def ProcessTls(self, data, domain=None):
    self.LogError('MagicProtocolParser::ProcessTls: Should be overridden!')
    return False

  def ProcessProto(self, data, proto, domain):
    self.LogError('MagicProtocolParser::ProcessProto: Should be overridden!')
    return False


class ChunkParser(Selectable):
  """A Selectable which parses the input as chunks."""

  def __init__(self, fd=None, address=None, on_port=None, ui=None):
    Selectable.__init__(self, fd, address, on_port, ui=ui)
    self.want_cbytes = 0
    self.want_bytes = 0
    self.compressed = False
    self.header = ''
    self.chunk = ''
    self.zr = zlib.decompressobj()

  def __html__(self):
    return Selectable.__html__(self)

  def Cleanup(self, close=True):
    Selectable.Cleanup(self, close=close)
    self.zr = self.chunk = self.header = None

  def ProcessData(self, data):
    loops = 1500
    result = more = True
    while result and more and (loops > 0):
      loops -= 1

      if self.peeking:
        self.want_cbytes = 0
        self.want_bytes = 0
        self.header = ''
        self.chunk = ''

      if self.want_bytes == 0:
        self.header += (data or '')
        if self.header.find('\r\n') < 0:
          if self.read_eof:
            return self.ProcessEofRead()
          return True

        try:
          size, data = self.header.split('\r\n', 1)
          self.header = ''

          if size.endswith('R'):
            self.zr = zlib.decompressobj()
            size = size[0:-1]

          if 'Z' in size:
            csize, zsize = size.split('Z')
            self.compressed = True
            self.want_cbytes = int(csize, 16)
            self.want_bytes = int(zsize, 16)
          else:
            self.compressed = False
            self.want_bytes = int(size, 16)

        except ValueError, err:
          self.LogError('ChunkParser::ProcessData: %s' % err)
          self.Log([('bad_data', data)])
          return False

        if self.want_bytes == 0:
          return False

      process = data[:self.want_bytes]
      data = more = data[self.want_bytes:]

      self.chunk += process
      self.want_bytes -= len(process)

      if self.want_bytes == 0:
        if self.compressed:
          try:
            cchunk = self.zr.decompress(self.chunk)
          except zlib.error:
            cchunk = ''

          if len(cchunk) != self.want_cbytes:
            result = self.ProcessCorruptChunk(self.chunk)
          else:
            result = self.ProcessChunk(cchunk)
        else:
          result = self.ProcessChunk(self.chunk)
        self.chunk = ''

    if result and more:
      self.LogError('Unprocessed data: %s' % data)
      raise BugFoundError('Too much data')
    elif self.read_eof:
      return self.ProcessEofRead() and result
    else:
      return result

  def ProcessCorruptChunk(self, chunk):
    self.LogError('ChunkParser::ProcessData: ProcessCorruptChunk not overridden!')
    return False

  def ProcessChunk(self, chunk):
    self.LogError('ChunkParser::ProcessData: ProcessChunk not overridden!')
    return False

########NEW FILE########
__FILENAME__ = basic
"""
This is the "basic" text-mode user interface class.
"""
#############################################################################
LICENSE = """\
This file is part of pagekite.py.
Copyright 2010-2013, the Beanstalks Project ehf. and Bjarni Runar Einarsson

This program is free software: you can redistribute it and/or modify it under
the terms of the  GNU  Affero General Public License as published by the Free
Software Foundation, either version 3 of the License, or (at your option) any
later version.

This program is distributed in the hope that it will be useful,  but  WITHOUT
ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
FOR A PARTICULAR PURPOSE.  See the GNU Affero General Public License for more
details.

You should have received a copy of the GNU Affero General Public License
along with this program.  If not, see: <http://www.gnu.org/licenses/>
"""
#############################################################################
import re
import sys
import time

from nullui import NullUi
from pagekite.common import *


HTML_BR_RE = re.compile(r'<(br|/p|/li|/tr|/h\d)>\s*')
HTML_LI_RE = re.compile(r'<li>\s*')
HTML_NBSP_RE = re.compile(r'&nbsp;')
HTML_TAGS_RE = re.compile(r'<[^>\s][^>]*>')

def clean_html(text):
  return HTML_LI_RE.sub(' * ',
          HTML_NBSP_RE.sub('_',
           HTML_BR_RE.sub('\n', text)))

def Q(text):
  return HTML_TAGS_RE.sub('', clean_html(text))


class BasicUi(NullUi):
  """Stdio based user interface."""

  DAEMON_FRIENDLY = False
  WANTS_STDERR = True
  EMAIL_RE = re.compile(r'^[a-z0-9!#$%&\'\*\+\/=?^_`{|}~-]+'
                         '(?:\.[a-z0-9!#$%&\'*+/=?^_`{|}~-]+)*@'
                         '(?:[a-z0-9](?:[a-z0-9-]*[a-z0-9])?\.)*'
                         '(?:[a-zA-Z]{2,4}|museum)$')
  def Notify(self, message, prefix=' ',
             popup=False, color=None, now=None, alignright=''):
    now = int(now or time.time())
    color = color or self.NORM

    # We suppress duplicates that are either new or still on the screen.
    keys = self.notify_history.keys()
    if len(keys) > 20:
      for key in keys:
        if self.notify_history[key] < now-300:
          del self.notify_history[key]

    message = '%s' % message
    if message not in self.notify_history:

      # Display the time now and then.
      if (not alignright and
          (now >= (self.last_tick + 60)) and
          (len(message) < 68)):
        try:
          self.last_tick = now
          d = datetime.datetime.fromtimestamp(now)
          alignright = '[%2.2d:%2.2d]' % (d.hour, d.minute)
        except:
          pass # Fails on Python 2.2

      if not now or now > 0:
        self.notify_history[message] = now
      msg = '\r%s %s%s%s%s%s\n' % ((prefix * 3)[0:3], color, message, self.NORM,
                                   ' ' * (75-len(message)-len(alignright)),
                                   alignright)
      self.wfile.write(msg)
      self.Status(self.status_tag, self.status_msg)

  def NotifyMOTD(self, frontend, motd_message):
    lc = 1
    self.Notify('  ')
    for line in Q(motd_message).splitlines():
      self.Notify((line.strip() or ' ' * (lc+2)),
                  prefix=' ++', color=self.WHITE)
      lc += 1
    self.Notify(' ' * (lc+2), alignright='[MOTD from %s]' % frontend)
    self.Notify('   ')

  def Status(self, tag, message=None, color=None):
    self.status_tag = tag
    self.status_col = color or self.status_col or self.NORM
    self.status_msg = '%s' % (message or self.status_msg)
    if not self.in_wizard:
      message = self.status_msg
      msg = ('\r << pagekite.py [%s]%s %s%s%s\r%s'
             ) % (tag, ' ' * (8-len(tag)),
                  self.status_col, message[:52],
                  ' ' * (52-len(message)), self.NORM)
      self.wfile.write(msg)
    if tag == 'exiting':
      self.wfile.write('\n')

  def Welcome(self, pre=None):
    if self.in_wizard:
      self.wfile.write('%s%s%s' % (self.CLEAR, self.WHITE, self.in_wizard))
    if self.welcome:
      self.wfile.write('%s\r%s\n' % (self.NORM, Q(self.welcome)))
      self.welcome = None
    if self.in_wizard and self.wizard_tell:
      self.wfile.write('\n%s\r' % self.NORM)
      for line in self.wizard_tell: self.wfile.write('*** %s\n' % Q(line))
      self.wizard_tell = None
    if pre:
      self.wfile.write('\n%s\r' % self.NORM)
      for line in pre: self.wfile.write('    %s\n' % Q(line))
    self.wfile.write('\n%s\r' % self.NORM)

  def StartWizard(self, title):
    self.Welcome()
    banner = '>>> %s' %  title
    banner = ('%s%s[CTRL+C = Cancel]\n') % (banner, ' ' * (62-len(banner)))
    self.in_wizard = banner
    self.tries = 200

  def Retry(self):
    self.tries -= 1
    return self.tries

  def EndWizard(self, quietly=False):
    if self.wizard_tell:
      self.Welcome()
    self.in_wizard = None
    if sys.platform in ('win32', 'os2', 'os2emx') and not quietly:
      self.wfile.write('\n<<< press ENTER to continue >>>\n')
      self.rfile.readline()

  def Spacer(self):
    self.wfile.write('\n')

  def Readline(self):
    line = self.rfile.readline()
    if line:
      return line.strip()
    else:
      raise IOError('EOF')

  def AskEmail(self, question, default=None, pre=[],
               wizard_hint=False, image=None, back=None, welcome=True):
    if welcome: self.Welcome(pre)
    while self.Retry():
      self.wfile.write(' => %s ' % (Q(question), ))
      answer = self.Readline()
      if default and answer == '': return default
      if self.EMAIL_RE.match(answer.lower()): return answer
      if back is not None and answer == 'back': return back
    raise Exception('Too many tries')

  def AskLogin(self, question, default=None, email=None, pre=None,
               wizard_hint=False, image=None, back=None):
    self.Welcome(pre)

    def_email, def_pass = default or (email, None)
    self.wfile.write('    %s\n' % (Q(question), ))

    if not email:
      email = self.AskEmail('Your e-mail:',
                            default=def_email, back=back, welcome=False)
      if email == back: return back

    import getpass
    self.wfile.write(' => ')
    return (email, getpass.getpass() or def_pass)

  def AskYesNo(self, question, default=None, pre=[], yes='yes', no='no',
               wizard_hint=False, image=None, back=None):
    self.Welcome(pre)
    yn = ((default is True) and '[Y/n]'
          ) or ((default is False) and '[y/N]'
                ) or ('[y/n]')
    while self.Retry():
      self.wfile.write(' => %s %s ' % (Q(question), yn))
      answer = self.Readline().lower()
      if default is not None and answer == '': answer = default and 'y' or 'n'
      if back is not None and answer.startswith('b'): return back
      if answer in ('y', 'n'): return (answer == 'y')
    raise Exception('Too many tries')

  def AskQuestion(self, question, pre=[], default=None, prompt=' =>',
                  wizard_hint=False, image=None, back=None):
    self.Welcome(pre)
    self.wfile.write('%s %s ' % (prompt, Q(question)))
    return self.Readline()

  def AskKiteName(self, domains, question, pre=[], default=None,
                  wizard_hint=False, image=None, back=None):
    self.Welcome(pre)
    if len(domains) == 1:
      self.wfile.write(('\n    (Note: the ending %s will be added for you.)'
                        ) % domains[0])
    else:
      self.wfile.write('\n    Please use one of the following domains:\n')
      for domain in domains:
        self.wfile.write('\n     *%s' % domain)
      self.wfile.write('\n')
    while self.Retry():
      self.wfile.write('\n => %s ' % Q(question))
      answer = self.Readline().lower()
      if back is not None and answer == 'back':
        return back
      elif len(domains) == 1:
        answer = answer.replace(domains[0], '')
        if answer and SERVICE_SUBDOMAIN_RE.match(answer):
          return answer+domains[0]
      else:
        for domain in domains:
          if answer.endswith(domain):
            answer = answer.replace(domain, '')
            if answer and SERVICE_SUBDOMAIN_RE.match(answer):
              return answer+domain
      self.wfile.write('    (Please only use characters A-Z, 0-9, - and _.)')
    raise Exception('Too many tries')

  def AskMultipleChoice(self, choices, question, pre=[], default=None,
                        wizard_hint=False, image=None, back=None):
    self.Welcome(pre)
    for i in range(0, len(choices)):
      self.wfile.write(('  %s %d) %s\n'
                        ) % ((default==i+1) and '*' or ' ', i+1, choices[i]))
    self.wfile.write('\n')
    while self.Retry():
      d = default and (', default=%d' % default) or ''
      self.wfile.write(' => %s [1-%d%s] ' % (Q(question), len(choices), d))
      try:
        answer = self.Readline().strip()
        if back is not None and answer.startswith('b'): return back
        choice = int(answer or default)
        if choice > 0 and choice <= len(choices): return choice
      except (ValueError, IndexError):
        pass
    raise Exception('Too many tries')

  def Tell(self, lines, error=False, back=None):
    if self.in_wizard:
      self.wizard_tell = lines
    else:
      self.Welcome()
      for line in lines: self.wfile.write('    %s\n' % line)
      if error: self.wfile.write('\n')
    return True

  def Working(self, message):
    if self.in_wizard:
      pending_messages = self.wizard_tell or []
      self.wizard_tell = pending_messages + [message+' ...']
      self.Welcome()
      self.wizard_tell = pending_messages + [message+' ... done.']
    else:
      self.Tell([message])
    return True

########NEW FILE########
__FILENAME__ = nullui
"""
This is a basic "Null" user interface which does nothing at all.
"""
##############################################################################
LICENSE = """\
This file is part of pagekite.py.
Copyright 2010-2013, the Beanstalks Project ehf. and Bjarni Runar Einarsson

This program is free software: you can redistribute it and/or modify it under
the terms of the  GNU  Affero General Public License as published by the Free
Software Foundation, either version 3 of the License, or (at your option) any
later version.

This program is distributed in the hope that it will be useful,  but  WITHOUT
ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
FOR A PARTICULAR PURPOSE.  See the GNU Affero General Public License for more
details.

You should have received a copy of the GNU Affero General Public License
along with this program.  If not, see: <http://www.gnu.org/licenses/>
"""
##############################################################################
import sys

from pagekite.compat import *
from pagekite.common import *
import pagekite.logging as logging

class NullUi(object):
  """This is a UI that always returns default values or raises errors."""

  DAEMON_FRIENDLY = True
  ALLOWS_INPUT = False
  WANTS_STDERR = False
  REJECTED_REASONS = {
    'quota': 'You are out of quota',
    'nodays': 'Your subscription has expired',
    'noquota': 'You are out of quota',
    'noconns': 'You are flying too many kites',
    'unauthorized': 'Invalid account or shared secret'
  }

  def __init__(self, welcome=None, wfile=sys.stderr, rfile=sys.stdin):
    if sys.platform[:3] in ('win', 'os2'):
      self.CLEAR = '\n\n%s\n\n' % ('=' * 79)
      self.NORM = self.WHITE = self.GREY = self.GREEN = self.YELLOW = ''
      self.BLUE = self.RED = self.MAGENTA = self.CYAN = ''
    else:
      self.CLEAR = '\033[H\033[J'
      self.NORM = '\033[0m'
      self.WHITE = '\033[1m'
      self.GREY =  '\033[0m' #'\033[30;1m'
      self.RED = '\033[31;1m'
      self.GREEN = '\033[32;1m'
      self.YELLOW = '\033[33;1m'
      self.BLUE = '\033[34;1m'
      self.MAGENTA = '\033[35;1m'
      self.CYAN = '\033[36;1m'

    self.wfile = wfile
    self.rfile = rfile
    self.welcome = welcome

    self.Reset()
    self.Splash()

  def Reset(self):
    self.in_wizard = False
    self.wizard_tell = None
    self.last_tick = 0
    self.notify_history = {}
    self.status_tag = ''
    self.status_col = self.NORM
    self.status_msg = ''
    self.tries = 200
    self.server_info = None

  def Splash(self): pass

  def Welcome(self): pass
  def StartWizard(self, title): pass
  def EndWizard(self, quietly=False): pass
  def Spacer(self): pass

  def Browse(self, url):
    import webbrowser
    self.Tell(['Opening %s in your browser...' % url])
    webbrowser.open(url)

  def DefaultOrFail(self, question, default):
    if default is not None: return default
    raise ConfigError('Unanswerable question: %s' % question)

  def AskLogin(self, question, default=None, email=None,
               wizard_hint=False, image=None, back=None):
    return self.DefaultOrFail(question, default)

  def AskEmail(self, question, default=None, pre=None,
               wizard_hint=False, image=None, back=None):
    return self.DefaultOrFail(question, default)

  def AskYesNo(self, question, default=None, pre=None, yes='Yes', no='No',
               wizard_hint=False, image=None, back=None):
    return self.DefaultOrFail(question, default)

  def AskQuestion(self, question, pre=[], default=None, prompt=None,
                  wizard_hint=False, image=None, back=None):
    return self.DefaultOrFail(question, default)

  def AskKiteName(self, domains, question, pre=[], default=None,
                  wizard_hint=False, image=None, back=None):
    return self.DefaultOrFail(question, default)

  def AskMultipleChoice(self, choices, question, pre=[], default=None,
                        wizard_hint=False, image=None, back=None):
    return self.DefaultOrFail(question, default)

  def AskBackends(self, kitename, protos, ports, rawports, question, pre=[],
                  default=None, wizard_hint=False, image=None, back=None):
    return self.DefaultOrFail(question, default)

  def Working(self, message): pass

  def Tell(self, lines, error=False, back=None):
    if error:
      logging.LogError(' '.join(lines))
      raise ConfigError(' '.join(lines))
    else:
      logging.Log([('message', ' '.join(lines))])
      return True

  def Notify(self, message, prefix=' ',
             popup=False, color=None, now=None, alignright=''):
    if popup: logging.Log([('info', '%s%s%s' % (message,
                                        alignright and ' ' or '',
                                        alignright))])

  def NotifyMOTD(self, frontend, message):
    pass

  def NotifyKiteRejected(self, proto, domain, reason, crit=False):
    if reason in self.REJECTED_REASONS:
      reason = self.REJECTED_REASONS[reason]
    self.Notify('REJECTED: %s:%s (%s)' % (proto, domain, reason),
                prefix='!', color=(crit and self.RED or self.YELLOW))

  def NotifyList(self, prefix, items, color):
    items = items[:]
    while items:
      show = []
      while items and len(prefix) + len(' '.join(show)) < 65:
        show.append(items.pop(0))
      self.Notify(' - %s: %s' % (prefix, ' '.join(show)), color=color)

  def NotifyServer(self, obj, server_info):
    self.server_info = server_info
    self.Notify('Connecting to front-end %s ...' % server_info[obj.S_NAME],
                color=self.GREY)
    self.NotifyList('Protocols', server_info[obj.S_PROTOS], self.GREY)
    self.NotifyList('Ports', server_info[obj.S_PORTS], self.GREY)
    if 'raw' in server_info[obj.S_PROTOS]:
      self.NotifyList('Raw ports', server_info[obj.S_RAW_PORTS], self.GREY)

  def NotifyQuota(self, quota, q_days, q_conns):
    qMB = 1024
    msg = 'Quota: You have %.2f MB' % (float(quota) / qMB)
    if q_days is not None: msg += ', %d days' % q_days
    if q_conns is not None: msg += ' and %d connections' % q_conns
    self.Notify(msg + ' left.',
                prefix=(int(quota) < qMB) and '!' or ' ',
                color=self.MAGENTA)

  def NotifyFlyingFE(self, proto, port, domain, be=None):
    self.Notify(('Flying: %s://%s%s/'
                 ) % (proto, domain, port and ':'+port or ''),
                prefix='~<>', color=self.CYAN)

  def StartListingBackEnds(self): pass
  def EndListingBackEnds(self): pass

  def NotifyBE(self, bid, be, has_ssl, dpaths,
                     is_builtin=False, fingerprint=None):
    domain, port, proto = be[BE_DOMAIN], be[BE_PORT], be[BE_PROTO]
    prox = (proto == 'raw') and ' (HTTP proxied)' or ''
    if proto == 'raw' and port in ('22', 22): proto = 'ssh'
    if has_ssl and proto == 'http':
      proto = 'https'
    url = '%s://%s%s' % (proto, domain, port and (':%s' % port) or '')

    if be[BE_STATUS] == BE_STATUS_UNKNOWN: return
    if be[BE_STATUS] & BE_STATUS_OK:
      if be[BE_STATUS] & BE_STATUS_ERR_ANY:
        status = 'Trying'
        color = self.YELLOW
        prefix = '   '
      else:
        status = 'Flying'
        color = self.CYAN
        prefix = '~<>'
    else:
      return

    if is_builtin:
      backend = 'builtin HTTPD'
    else:
      backend = '%s:%s' % (be[BE_BHOST], be[BE_BPORT])

    self.Notify(('%s %s as %s/%s'
                 ) % (status, backend, url, prox),
                prefix=prefix, color=color)

    if status == 'Flying':
      for dp in sorted(dpaths.keys()):
        self.Notify(' - %s%s' % (url, dp), color=self.BLUE)
      if fingerprint and proto.startswith('https'):
        self.Notify(' - Fingerprint=%s' % fingerprint,
                    color=self.WHITE)
        self.Notify(('   IMPORTANT: For maximum security, use a secure channel'
                     ' to inform your'),
                    color=self.YELLOW)
        self.Notify('   guests what fingerprint to expect.',
                    color=self.YELLOW)

  def Status(self, tag, message=None, color=None): pass

  def ExplainError(self, error, title, subject=None):
    if error == 'pleaselogin':
      self.Tell([title, '', 'You already have an account. Log in to continue.'
                 ], error=True)
    elif error == 'email':
      self.Tell([title, '', 'Invalid e-mail address. Please try again?'
                 ], error=True)
    elif error == 'honey':
      self.Tell([title, '', 'Hmm. Somehow, you triggered the spam-filter.'
                 ], error=True)
    elif error in ('domaintaken', 'domain', 'subdomain'):
      self.Tell([title, '',
                 'Sorry, that domain (%s) is unavailable.' % subject,
                 '',
                 'If you registered it already, perhaps you need to log on with',
                 'a different e-mail address?',
                 ''
                 ], error=True)
    elif error == 'checkfailed':
      self.Tell([title, '',
                 'That domain (%s) is not correctly set up.' % subject
                 ], error=True)
    elif error == 'network':
      self.Tell([title, '',
                 'There was a problem communicating with %s.' % subject, '',
                 'Please verify that you have a working'
                 ' Internet connection and try again!'
                 ], error=True)
    else:
      self.Tell([title, 'Error code: %s' % error, 'Try again later?'
                 ], error=True)


########NEW FILE########
__FILENAME__ = remote
"""
This is a user interface class which communicates over a pipe or socket.
"""
##############################################################################
LICENSE = """\
This file is part of pagekite.py.
Copyright 2010-2013, the Beanstalks Project ehf. and Bjarni Runar Einarsson

This program is free software: you can redistribute it and/or modify it under
the terms of the  GNU  Affero General Public License as published by the Free
Software Foundation, either version 3 of the License, or (at your option) any
later version.

This program is distributed in the hope that it will be useful,  but  WITHOUT
ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
FOR A PARTICULAR PURPOSE.  See the GNU Affero General Public License for more
details.

You should have received a copy of the GNU Affero General Public License
along with this program.  If not, see: <http://www.gnu.org/licenses/>
"""
##############################################################################
import re
import sys
import time
import threading

from pagekite.compat import *
from pagekite.common import *
from pagekite.proto.conns import Tunnel

from nullui import NullUi

class RemoteUi(NullUi):
  """Stdio based user interface for interacting with other processes."""

  DAEMON_FRIENDLY = True
  ALLOWS_INPUT = True
  WANTS_STDERR = True
  EMAIL_RE = re.compile(r'^[a-z0-9!#$%&\'\*\+\/=?^_`{|}~-]+'
                         '(?:\.[a-z0-9!#$%&\'*+/=?^_`{|}~-]+)*@'
                         '(?:[a-z0-9](?:[a-z0-9-]*[a-z0-9])?\.)*'
                         '(?:[a-zA-Z]{2,4}|museum)$')

  def __init__(self, welcome=None, wfile=sys.stderr, rfile=sys.stdin):
    NullUi.__init__(self, welcome=welcome, wfile=wfile, rfile=rfile)
    self.CLEAR = ''
    self.NORM = self.WHITE = self.GREY = self.GREEN = self.YELLOW = ''
    self.BLUE = self.RED = self.MAGENTA = self.CYAN = ''

  def StartListingBackEnds(self):
    self.wfile.write('begin_be_list\n')

  def EndListingBackEnds(self):
    self.wfile.write('end_be_list\n')

  def NotifyBE(self, bid, be, has_ssl, dpaths,
               is_builtin=False, fingerprint=None, now=None):
    domain = be[BE_DOMAIN]
    port = be[BE_PORT]
    proto = be[BE_PROTO]
    prox = (proto == 'raw') and ' (HTTP proxied)' or ''
    if proto == 'raw' and port in ('22', 22): proto = 'ssh'
    url = '%s://%s%s' % (proto, domain, port and (':%s' % port) or '')

    message = (' be_status:'
               ' status=%x; bid=%s; domain=%s; port=%s; proto=%s;'
               ' bhost=%s; bport=%s%s%s%s'
               '\n') % (be[BE_STATUS], bid, domain, port, proto,
                        be[BE_BHOST], be[BE_BPORT],
                        has_ssl and '; ssl=1' or '',
                        is_builtin and '; builtin=1' or '',
                        fingerprint and ('; fingerprint=%s' % fingerprint) or '')
    self.wfile.write(message)

    for path in dpaths:
      message = (' be_path: domain=%s; port=%s; path=%s; policy=%s; src=%s\n'
                 ) % (domain, port or 80, path,
                      dpaths[path][0], dpaths[path][1])
      self.wfile.write(message)

  def Notify(self, message, prefix=' ',
             popup=False, color=None, now=None, alignright=''):
    message = '%s' % message
    self.wfile.write('notify: %s\n' % message)

  def NotifyMOTD(self, frontend, message):
    self.wfile.write('motd: %s %s\n' % (frontend,
                                        message.replace('\n', '  ')))

  def Status(self, tag, message=None, color=None):
    self.status_tag = tag
    self.status_msg = '%s' % (message or self.status_msg)
    if message:
      self.wfile.write('status_msg: %s\n' % message)
    if tag:
      self.wfile.write('status_tag: %s\n' % tag)

  def Welcome(self, pre=None):
    self.wfile.write('welcome: %s\n' % (pre or '').replace('\n', '  '))

  def StartWizard(self, title):
    self.wfile.write('start_wizard: %s\n' % title)

  def Retry(self):
    self.tries -= 1
    if self.tries < 0:
      raise Exception('Too many tries')
    return self.tries

  def EndWizard(self, quietly=False):
    self.wfile.write('end_wizard: %s\n' % (quietly and 'quietly' or 'done'))

  def Spacer(self):
    pass

  def AskEmail(self, question, default=None, pre=[],
               wizard_hint=False, image=None, back=None, welcome=True):
    while self.Retry():
      self.wfile.write('begin_ask_email\n')
      if pre:
        self.wfile.write(' preamble: %s\n' % '\n'.join(pre).replace('\n', '  '))
      if default:
        self.wfile.write(' default: %s\n' % default)
      self.wfile.write(' question: %s\n' % (question or '').replace('\n', '  '))
      self.wfile.write(' expect: email\n')
      self.wfile.write('end_ask_email\n')

      answer = self.rfile.readline().strip()
      if self.EMAIL_RE.match(answer): return answer
      if back is not None and answer == 'back': return back

  def AskLogin(self, question, default=None, email=None, pre=None,
               wizard_hint=False, image=None, back=None):
    while self.Retry():
      self.wfile.write('begin_ask_login\n')
      if pre:
        self.wfile.write(' preamble: %s\n' % '\n'.join(pre).replace('\n', '  '))
      if email:
        self.wfile.write(' default: %s\n' % email)
      self.wfile.write(' question: %s\n' % (question or '').replace('\n', '  '))
      self.wfile.write(' expect: email\n')
      self.wfile.write(' expect: password\n')
      self.wfile.write('end_ask_login\n')

      answer_email = self.rfile.readline().strip()
      if back is not None and answer_email == 'back': return back

      answer_pass = self.rfile.readline().strip()
      if back is not None and answer_pass == 'back': return back

      if self.EMAIL_RE.match(answer_email) and answer_pass:
        return (answer_email, answer_pass)

  def AskYesNo(self, question, default=None, pre=[], yes='Yes', no='No',
               wizard_hint=False, image=None, back=None):
    while self.Retry():
      self.wfile.write('begin_ask_yesno\n')
      if yes:
        self.wfile.write(' yes: %s\n' % yes)
      if no:
        self.wfile.write(' no: %s\n' % no)
      if pre:
        self.wfile.write(' preamble: %s\n' % '\n'.join(pre).replace('\n', '  '))
      if default:
        self.wfile.write(' default: %s\n' % default)
      self.wfile.write(' question: %s\n' % (question or '').replace('\n', '  '))
      self.wfile.write(' expect: yesno\n')
      self.wfile.write('end_ask_yesno\n')

      answer = self.rfile.readline().strip().lower()
      if back is not None and answer == 'back': return back
      if answer in ('y', 'n'): return (answer == 'y')
      if answer == str(default).lower(): return default

  def AskKiteName(self, domains, question, pre=[], default=None,
                  wizard_hint=False, image=None, back=None):
    while self.Retry():
      self.wfile.write('begin_ask_kitename\n')
      if pre:
        self.wfile.write(' preamble: %s\n' % '\n'.join(pre).replace('\n', '  '))
      for domain in domains:
        self.wfile.write(' domain: %s\n' % domain)
      if default:
        self.wfile.write(' default: %s\n' % default)
      self.wfile.write(' question: %s\n' % (question or '').replace('\n', '  '))
      self.wfile.write(' expect: kitename\n')
      self.wfile.write('end_ask_kitename\n')

      answer = self.rfile.readline().strip().lower()
      if back is not None and answer == 'back': return back
      if answer:
        for d in domains:
          if answer.endswith(d) or answer.endswith(d): return answer
        return answer+domains[0]

  def AskBackends(self, kitename, protos, ports, rawports, question, pre=[],
                  default=None, wizard_hint=False, image=None, back=None):
    while self.Retry():
      self.wfile.write('begin_ask_backends\n')
      if pre:
        self.wfile.write(' preamble: %s\n' % '\n'.join(pre).replace('\n', '  '))
      count = 0
      if self.server_info:
        protos = self.server_info[Tunnel.S_PROTOS]
        ports = self.server_info[Tunnel.S_PORTS]
        rawports = self.server_info[Tunnel.S_RAW_PORTS]
      self.wfile.write(' kitename: %s\n' % kitename)
      self.wfile.write(' protos: %s\n' % ', '.join(protos))
      self.wfile.write(' ports: %s\n' % ', '.join(ports))
      self.wfile.write(' rawports: %s\n' % ', '.join(rawports))
      if default:
        self.wfile.write(' default: %s\n' % default)
      self.wfile.write(' question: %s\n' % (question or '').replace('\n', '  '))
      self.wfile.write(' expect: backends\n')
      self.wfile.write('end_ask_backends\n')

      answer = self.rfile.readline().strip().lower()
      if back is not None and answer == 'back': return back
      return answer

  def AskMultipleChoice(self, choices, question, pre=[], default=None,
                        wizard_hint=False, image=None, back=None):
    while self.Retry():
      self.wfile.write('begin_ask_multiplechoice\n')
      if pre:
        self.wfile.write(' preamble: %s\n' % '\n'.join(pre).replace('\n', '  '))
      count = 0
      for choice in choices:
        count += 1
        self.wfile.write(' choice_%d: %s\n' % (count, choice))
      if default:
        self.wfile.write(' default: %s\n' % default)
      self.wfile.write(' question: %s\n' % (question or '').replace('\n', '  '))
      self.wfile.write(' expect: choice_index\n')
      self.wfile.write('end_ask_multiplechoice\n')

      answer = self.rfile.readline().strip().lower()
      try:
        ch = int(answer)
        if ch > 0 and ch <= len(choices): return ch
      except:
        pass
      if back is not None and answer == 'back': return back

  def Tell(self, lines, error=False, back=None):
    dialog = error and 'error' or 'message'
    self.wfile.write('tell_%s: %s\n' % (dialog, '  '.join(lines)))

  def Working(self, message):
    self.wfile.write('working: %s\n' % message)


class PageKiteThread(threading.Thread):
  def __init__(self, startup_args=None, debug=False):
    threading.Thread.__init__(self)
    self.pk = None
    self.pk_readlock = threading.Condition()
    self.gui_readlock = threading.Condition()
    self.debug = debug
    self.reset()

  def reset(self):
    self.pk_incoming = []
    self.pk_eof = False
    self.gui_incoming = ''
    self.gui_eof = False

  # These routines are used by the PageKite UI, to communicate with us...
  def readline(self):
    try:
      self.pk_readlock.acquire()
      while (not self.pk_incoming) and (not self.pk_eof): self.pk_readlock.wait()
      if self.pk_incoming:
        line = self.pk_incoming.pop(0)
      else:
        line = ''
      if self.debug:
        print '>>PK>> %s' % line.strip()
      return line
    finally:
      self.pk_readlock.release()

  def write(self, data):
    if self.debug:
      print '>>GUI>> %s' % data.strip()
    try:
      self.gui_readlock.acquire()
      if data:
        self.gui_incoming += data
      else:
        self.gui_eof = True
      self.gui_readlock.notify()
    finally:
      self.gui_readlock.release()

  # And these are used by the GUI, to communicate with PageKite.
  def recv(self, bytecount):
    try:
      self.gui_readlock.acquire()
      while (len(self.gui_incoming) < bytecount) and (not self.gui_eof):
        self.gui_readlock.wait()
      data = self.gui_incoming[0:bytecount]
      self.gui_incoming = self.gui_incoming[bytecount:]
      return data
    finally:
      self.gui_readlock.release()

  def send(self, data):
    if not data.endswith('\n') and data != '':
      raise ValueError('Please always send whole lines')
    if self.debug:
      print '<<PK<< %s' % data.strip()
    try:
      self.pk_readlock.acquire()
      if data:
        self.pk_incoming.append(data)
      else:
        self.pk_eof = True
      self.pk_readlock.notify()
    finally:
      self.pk_readlock.release()

  def sendall(self, data):
    return self.send(data)

  def close(self):
    self.send('')
    self.write('')

  def setup_comms(self, pkobj):
    self.pk = pkobj
    pkobj.ui_wfile = pkobj.ui.wfile = self
    pkobj.ui_rfile = pkobj.ui.rfile = self

  def run(self):
    raise Exception('Unimplemented')


class PageKiteRestarter(PageKiteThread):

  def __init__(self, startup_args=None):
    PageKiteThread.__init__(self)
    self.pk_startup_args = startup_args
    self.looping = False
    self.stopped = True

  def config_wrapper(self, pkobj):
    old_argv = sys.argv[:]

    # Remove invalid arguments that break us.
    for evil in ('--nullui', '--basicui', '--friendly'):
      if evil in sys.argv:
        sys.argv.remove(evil)

    if self.pk_startup_args:
      sys.argv[1:1] = self.pk_startup_args[:]
      self.pk_startup_args = None
    try:
      try:
        self.setup_comms(pkobj)
        return self.configure(pkobj)
      except:
        self.pk = None
        raise
    finally:
      sys.argv = old_argv[:]

  def run(self):
    self.looping = True
    while self.looping:
      last_loop = int(time.time())
      if not self.stopped:
        self.reset()
        self.startup()
        self.close()
        self.write('status_msg: Disabled\nstatus_tag: idle\n')
        self.pk = None
      if last_loop == int(time.time()):
        time.sleep(1)

  def startup(self):
    raise Exception('Unimplemented')

  def postpone(self, func, argument):
    return func(argument)

  def stop(self, then=False):
    self.stopped = True
    if self.pk:
      self.send('exit: stopping\n')
      self.postpone(self.stop, then)
    else:
      if then:
        then()

  def restart(self):
    self.stopped = False

  def toggle(self):
    if self.stopped:
      self.restart()
    else:
      self.stop()

  def quit(self):
    self.looping = False
    self.stopped = True
    if self.pk:
      self.send('exit: quitting\n')
    self.close()
    self.pk = None
    self.join()


class CommThread(threading.Thread):
  def __init__(self, pkThread):
    threading.Thread.__init__(self)
    self.pkThread = pkThread
    self.looping = False

    self.multi = None
    self.multi_args = None

    # Callbacks
    self.cb = {}

  def call_cb(self, which, args):
    return self.cb[which](args)

  def parse_line(self, line):
#   print '<< %s' % line[:-1]
    if line.startswith('begin_'):
      self.multi = line[6:].strip()
      self.multi_args = {'_raw': []}
    elif self.multi:
      if line.startswith('end_'):
        if self.multi in self.cb:
          self.call_cb(self.multi, self.multi_args)
        elif 'default' in self.multi_args:
          self.pkThread.send(self.multi_args['default']+'\n')
        self.multi = self.multi_args = None
      else:
        self.multi_args['_raw'].append(line.strip())
        try:
          variable, value = line.strip().split(': ', 1)
          self.multi_args[variable] = value
        except ValueError:
          pass
    else:
      try:
        command, args = line.strip().split(': ', 1)
        if command in self.cb:
          self.call_cb(command, args)
      except ValueError:
        pass

  def run(self):
    self.pkThread.start()
    self.looping = True
    line = ''
    while self.looping:
      line += self.pkThread.recv(1)
      if line.endswith('\n'):
        self.parse_line(line)
        line = ''

  def quit(self):
    self.pkThread.quit()
    self.looping = False

########NEW FILE########
__FILENAME__ = yamond
"""
This is a class implementing a flexible metric-store and an HTTP
thread for browsing the numbers.
"""
##############################################################################
LICENSE = """\
This file is part of pagekite.py.
Copyright 2010-2013, the Beanstalks Project ehf. and Bjarni Runar Einarsson

This program is free software: you can redistribute it and/or modify it under
the terms of the  GNU  Affero General Public License as published by the Free
Software Foundation, either version 3 of the License, or (at your option) any
later version.

This program is distributed in the hope that it will be useful,  but  WITHOUT
ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
FOR A PARTICULAR PURPOSE.  See the GNU Affero General Public License for more
details.

You should have received a copy of the GNU Affero General Public License
along with this program.  If not, see: <http://www.gnu.org/licenses/>
"""
##############################################################################

import getopt
import os
import random
import re
import select
import socket
import struct
import sys
import threading
import time
import traceback
import urllib
 
import BaseHTTPServer
try:
  from urlparse import parse_qs, urlparse
except Exception, e:
  from cgi import parse_qs
  from urlparse import urlparse


class YamonRequestHandler(BaseHTTPServer.BaseHTTPRequestHandler):
  def do_yamon_vars(self):
    self.send_response(200)
    self.send_header('Content-Type', 'text/plain')
    self.send_header('Cache-Control', 'no-cache')
    self.end_headers()
    self.wfile.write(self.server.yamond.render_vars_text())

  def do_heapy(self):
    from guppy import hpy
    self.send_response(200)
    self.send_header('Content-Type', 'text/plain')
    self.send_header('Cache-Control', 'no-cache')
    self.end_headers()
    self.wfile.write(hpy().heap())

  def do_404(self):
    self.send_response(404)
    self.send_header('Content-Type', 'text/html')
    self.end_headers()
    self.wfile.write('<h1>404: What? Where? Cannot find it!</h1>')

  def do_root(self):
    self.send_response(200)
    self.send_header('Content-Type', 'text/html')
    self.end_headers()
    self.wfile.write('<h1>Hello!</h1>')

  def handle_path(self, path, query):
    if path == '/vars.txt':
      self.do_yamon_vars()
    elif path == '/heap.txt':
      self.do_heapy()
    elif path == '/':
      self.do_root()
    else:
      self.do_404()

  def do_GET(self):
    (scheme, netloc, path, params, query, frag) = urlparse(self.path)
    qs = parse_qs(query)
    return self.handle_path(path, query)


class YamonHttpServer(BaseHTTPServer.HTTPServer):
  def __init__(self, yamond, handler):
    BaseHTTPServer.HTTPServer.__init__(self, yamond.sspec, handler)
    self.yamond = yamond


class YamonD(threading.Thread):
  """Handle HTTP in a separate thread."""

  def __init__(self, sspec,
               server=YamonHttpServer,
               handler=YamonRequestHandler):
    threading.Thread.__init__(self)
    self.lock = threading.Lock()
    self.server = server
    self.handler = handler
    self.sspec = sspec
    self.httpd = None
    self.running = False
    self.values = {}
    self.lists = {}
    self.views = {}

  def vmax(self, var, value):
    try:
      self.lock.acquire()
      if value > self.values[var]:
        self.values[var] = value
    finally:
      self.lock.release()

  def vscale(self, var, ratio, add=0):
    try:
      self.lock.acquire()
      if var not in self.values:
        self.values[var] = 0
      self.values[var] *= ratio
      self.values[var] += add
    finally:
      self.lock.release()

  def vset(self, var, value):
    try:
      self.lock.acquire()
      self.values[var] = value
    finally:
      self.lock.release()

  def vadd(self, var, value, wrap=None):
    try:
      self.lock.acquire()
      if var not in self.values:
        self.values[var] = 0
      self.values[var] += value
      if wrap is not None and self.values[var] >= wrap:
        self.values[var] -= wrap
    finally:
      self.lock.release()

  def vmin(self, var, value):
    try:
      self.lock.acquire()
      if value < self.values[var]:
        self.values[var] = value
    finally:
      self.lock.release()

  def vdel(self, var):
    try:
      self.lock.acquire()
      if var in self.values:
        del self.values[var]
    finally:
      self.lock.release()

  def lcreate(self, listn, elems):
    try:
      self.lock.acquire()
      self.lists[listn] = [elems, 0, ['' for x in xrange(0, elems)]]
    finally:
      self.lock.release()

  def ladd(self, listn, value):
    try:
      self.lock.acquire()
      lst = self.lists[listn]
      lst[2][lst[1]] = value
      lst[1] += 1
      lst[1] %= lst[0]
    finally:
      self.lock.release()

  def render_vars_text(self, view=None):
    if view:
      if view == 'heapy':
        from guppy import hpy
        return hpy().heap()
      else:
        values, lists = self.views[view]
    else:
      values, lists = self.values, self.lists

    data = []
    for var in values:
      data.append('%s: %s\n' % (var, values[var]))

    for lname in lists:
      (elems, offset, lst) = lists[lname]
      l = lst[offset:]
      l.extend(lst[:offset])
      data.append('%s: %s\n' % (lname, ' '.join(['%s' % (x, ) for x in l])))

    data.sort()
    return ''.join(data)

  def quit(self):
    if self.httpd:
      self.running = False
      urllib.urlopen('http://%s:%s/exiting/' % self.sspec,
                     proxies={}).readlines()

  def run(self):
    self.httpd = self.server(self, self.handler)
    self.sspec = self.httpd.server_address
    self.running = True
    while self.running: self.httpd.handle_request()


if __name__ == '__main__':
  yd = YamonD(('', 0))
  yd.vset('bjarni', 100)
  yd.lcreate('foo', 2)
  yd.ladd('foo', 1)
  yd.ladd('foo', 2)
  yd.ladd('foo', 3)
  yd.run()


########NEW FILE########
__FILENAME__ = __main__
#!/usr/bin/env python
"""
This is the pagekite.py Main() function.
"""
##############################################################################
LICENSE = """\
This file is part of pagekite.py.
Copyright 2010-2013, the Beanstalks Project ehf. and Bjarni Runar Einarsson

This program is free software: you can redistribute it and/or modify it under
the terms of the  GNU  Affero General Public License as published by the Free
Software Foundation, either version 3 of the License, or (at your option) any
later version.

This program is distributed in the hope that it will be useful,  but  WITHOUT
ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
FOR A PARTICULAR PURPOSE.  See the GNU Affero General Public License for more
details.

You should have received a copy of the GNU Affero General Public License
along with this program.  If not, see: <http://www.gnu.org/licenses/>
"""
##############################################################################
import sys
from pagekite import pk
from pagekite import httpd

if __name__ == "__main__":
  if sys.stdout.isatty():
    import pagekite.ui.basic
    uiclass = pagekite.ui.basic.BasicUi
  else:
    import pagekite.ui.nullui
    uiclass = pagekite.ui.nullui.NullUi

  pk.Main(pk.PageKite, pk.Configure,
          uiclass=uiclass,
          http_handler=httpd.UiRequestHandler,
          http_server=httpd.UiHttpServer)


##############################################################################
CERTS="""\
StartCom Ltd.
=============
-----BEGIN CERTIFICATE-----
MIIFFjCCBH+gAwIBAgIBADANBgkqhkiG9w0BAQQFADCBsDELMAkGA1UEBhMCSUwxDzANBgNVBAgT
BklzcmFlbDEOMAwGA1UEBxMFRWlsYXQxFjAUBgNVBAoTDVN0YXJ0Q29tIEx0ZC4xGjAYBgNVBAsT
EUNBIEF1dGhvcml0eSBEZXAuMSkwJwYDVQQDEyBGcmVlIFNTTCBDZXJ0aWZpY2F0aW9uIEF1dGhv
cml0eTEhMB8GCSqGSIb3DQEJARYSYWRtaW5Ac3RhcnRjb20ub3JnMB4XDTA1MDMxNzE3Mzc0OFoX
DTM1MDMxMDE3Mzc0OFowgbAxCzAJBgNVBAYTAklMMQ8wDQYDVQQIEwZJc3JhZWwxDjAMBgNVBAcT
BUVpbGF0MRYwFAYDVQQKEw1TdGFydENvbSBMdGQuMRowGAYDVQQLExFDQSBBdXRob3JpdHkgRGVw
LjEpMCcGA1UEAxMgRnJlZSBTU0wgQ2VydGlmaWNhdGlvbiBBdXRob3JpdHkxITAfBgkqhkiG9w0B
CQEWEmFkbWluQHN0YXJ0Y29tLm9yZzCBnzANBgkqhkiG9w0BAQEFAAOBjQAwgYkCgYEA7YRgACOe
yEpRKSfeOqE5tWmrCbIvNP1h3D3TsM+x18LEwrHkllbEvqoUDufMOlDIOmKdw6OsWXuO7lUaHEe+
o5c5s7XvIywI6Nivcy+5yYPo7QAPyHWlLzRMGOh2iCNJitu27Wjaw7ViKUylS7eYtAkUEKD4/mJ2
IhULpNYILzUCAwEAAaOCAjwwggI4MA8GA1UdEwEB/wQFMAMBAf8wCwYDVR0PBAQDAgHmMB0GA1Ud
DgQWBBQcicOWzL3+MtUNjIExtpidjShkjTCB3QYDVR0jBIHVMIHSgBQcicOWzL3+MtUNjIExtpid
jShkjaGBtqSBszCBsDELMAkGA1UEBhMCSUwxDzANBgNVBAgTBklzcmFlbDEOMAwGA1UEBxMFRWls
YXQxFjAUBgNVBAoTDVN0YXJ0Q29tIEx0ZC4xGjAYBgNVBAsTEUNBIEF1dGhvcml0eSBEZXAuMSkw
JwYDVQQDEyBGcmVlIFNTTCBDZXJ0aWZpY2F0aW9uIEF1dGhvcml0eTEhMB8GCSqGSIb3DQEJARYS
YWRtaW5Ac3RhcnRjb20ub3JnggEAMB0GA1UdEQQWMBSBEmFkbWluQHN0YXJ0Y29tLm9yZzAdBgNV
HRIEFjAUgRJhZG1pbkBzdGFydGNvbS5vcmcwEQYJYIZIAYb4QgEBBAQDAgAHMC8GCWCGSAGG+EIB
DQQiFiBGcmVlIFNTTCBDZXJ0aWZpY2F0aW9uIEF1dGhvcml0eTAyBglghkgBhvhCAQQEJRYjaHR0
cDovL2NlcnQuc3RhcnRjb20ub3JnL2NhLWNybC5jcmwwKAYJYIZIAYb4QgECBBsWGWh0dHA6Ly9j
ZXJ0LnN0YXJ0Y29tLm9yZy8wOQYJYIZIAYb4QgEIBCwWKmh0dHA6Ly9jZXJ0LnN0YXJ0Y29tLm9y
Zy9pbmRleC5waHA/YXBwPTExMTANBgkqhkiG9w0BAQQFAAOBgQBscSXhnjSRIe/bbL0BCFaPiNhB
OlP1ct8nV0t2hPdopP7rPwl+KLhX6h/BquL/lp9JmeaylXOWxkjHXo0Hclb4g4+fd68p00UOpO6w
NnQt8M2YI3s3S9r+UZjEHjQ8iP2ZO1CnwYszx8JSFhKVU2Ui77qLzmLbcCOxgN8aIDjnfg==
-----END CERTIFICATE-----

StartCom Certification Authority
================================
-----BEGIN CERTIFICATE-----
MIIHyTCCBbGgAwIBAgIBATANBgkqhkiG9w0BAQUFADB9MQswCQYDVQQGEwJJTDEWMBQGA1UEChMN
U3RhcnRDb20gTHRkLjErMCkGA1UECxMiU2VjdXJlIERpZ2l0YWwgQ2VydGlmaWNhdGUgU2lnbmlu
ZzEpMCcGA1UEAxMgU3RhcnRDb20gQ2VydGlmaWNhdGlvbiBBdXRob3JpdHkwHhcNMDYwOTE3MTk0
NjM2WhcNMzYwOTE3MTk0NjM2WjB9MQswCQYDVQQGEwJJTDEWMBQGA1UEChMNU3RhcnRDb20gTHRk
LjErMCkGA1UECxMiU2VjdXJlIERpZ2l0YWwgQ2VydGlmaWNhdGUgU2lnbmluZzEpMCcGA1UEAxMg
U3RhcnRDb20gQ2VydGlmaWNhdGlvbiBBdXRob3JpdHkwggIiMA0GCSqGSIb3DQEBAQUAA4ICDwAw
ggIKAoICAQDBiNsJvGxGfHiflXu1M5DycmLWwTYgIiRezul38kMKogZkpMyONvg45iPwbm2xPN1y
o4UcodM9tDMr0y+v/uqwQVlntsQGfQqedIXWeUyAN3rfOQVSWff0G0ZDpNKFhdLDcfN1YjS6LIp/
Ho/u7TTQEceWzVI9ujPW3U3eCztKS5/CJi/6tRYccjV3yjxd5srhJosaNnZcAdt0FCX+7bWgiA/d
eMotHweXMAEtcnn6RtYTKqi5pquDSR3l8u/d5AGOGAqPY1MWhWKpDhk6zLVmpsJrdAfkK+F2PrRt
2PZE4XNiHzvEvqBTViVsUQn3qqvKv3b9bZvzndu/PWa8DFaqr5hIlTpL36dYUNk4dalb6kMMAv+Z
6+hsTXBbKWWc3apdzK8BMewM69KN6Oqce+Zu9ydmDBpI125C4z/eIT574Q1w+2OqqGwaVLRcJXrJ
osmLFqa7LH4XXgVNWG4SHQHuEhANxjJ/GP/89PrNbpHoNkm+Gkhpi8KWTRoSsmkXwQqQ1vp5Iki/
untp+HDH+no32NgN0nZPV/+Qt+OR0t3vwmC3Zzrd/qqc8NSLf3Iizsafl7b4r4qgEKjZ+xjGtrVc
UjyJthkqcwEKDwOzEmDyei+B26Nu/yYwl/WL3YlXtq09s68rxbd2AvCl1iuahhQqcvbjM4xdCUsT
37uMdBNSSwIDAQABo4ICUjCCAk4wDAYDVR0TBAUwAwEB/zALBgNVHQ8EBAMCAa4wHQYDVR0OBBYE
FE4L7xqkQFulF2mHMMo0aEPQQa7yMGQGA1UdHwRdMFswLKAqoCiGJmh0dHA6Ly9jZXJ0LnN0YXJ0
Y29tLm9yZy9zZnNjYS1jcmwuY3JsMCugKaAnhiVodHRwOi8vY3JsLnN0YXJ0Y29tLm9yZy9zZnNj
YS1jcmwuY3JsMIIBXQYDVR0gBIIBVDCCAVAwggFMBgsrBgEEAYG1NwEBATCCATswLwYIKwYBBQUH
AgEWI2h0dHA6Ly9jZXJ0LnN0YXJ0Y29tLm9yZy9wb2xpY3kucGRmMDUGCCsGAQUFBwIBFilodHRw
Oi8vY2VydC5zdGFydGNvbS5vcmcvaW50ZXJtZWRpYXRlLnBkZjCB0AYIKwYBBQUHAgIwgcMwJxYg
U3RhcnQgQ29tbWVyY2lhbCAoU3RhcnRDb20pIEx0ZC4wAwIBARqBl0xpbWl0ZWQgTGlhYmlsaXR5
LCByZWFkIHRoZSBzZWN0aW9uICpMZWdhbCBMaW1pdGF0aW9ucyogb2YgdGhlIFN0YXJ0Q29tIENl
cnRpZmljYXRpb24gQXV0aG9yaXR5IFBvbGljeSBhdmFpbGFibGUgYXQgaHR0cDovL2NlcnQuc3Rh
cnRjb20ub3JnL3BvbGljeS5wZGYwEQYJYIZIAYb4QgEBBAQDAgAHMDgGCWCGSAGG+EIBDQQrFilT
dGFydENvbSBGcmVlIFNTTCBDZXJ0aWZpY2F0aW9uIEF1dGhvcml0eTANBgkqhkiG9w0BAQUFAAOC
AgEAFmyZ9GYMNPXQhV59CuzaEE44HF7fpiUFS5Eyweg78T3dRAlbB0mKKctmArexmvclmAk8jhvh
3TaHK0u7aNM5Zj2gJsfyOZEdUauCe37Vzlrk4gNXcGmXCPleWKYK34wGmkUWFjgKXlf2Ysd6AgXm
vB618p70qSmD+LIU424oh0TDkBreOKk8rENNZEXO3SipXPJzewT4F+irsfMuXGRuczE6Eri8sxHk
fY+BUZo7jYn0TZNmezwD7dOaHZrzZVD1oNB1ny+v8OqCQ5j4aZyJecRDjkZy42Q2Eq/3JR44iZB3
fsNrarnDy0RLrHiQi+fHLB5LEUTINFInzQpdn4XBidUaePKVEFMy3YCEZnXZtWgo+2EuvoSoOMCZ
EoalHmdkrQYuL6lwhceWD3yJZfWOQ1QOq92lgDmUYMA0yZZwLKMS9R9Ie70cfmu3nZD0Ijuu+Pwq
yvqCUqDvr0tVk+vBtfAii6w0TiYiBKGHLHVKt+V9E9e4DGTANtLJL4YSjCMJwRuCO3NJo2pXh5Tl
1njFmUNj403gdy3hZZlyaQQaRwnmDwFWJPsfvw55qVguucQJAX6Vum0ABj6y6koQOdjQK/W/7HW/
lwLFCRsI3FU34oH7N4RDYiDK51ZLZer+bMEkkyShNOsF/5oirpt9P/FlUQqmMGqz9IgcgA38coro
g14=
-----END CERTIFICATE-----
"""

########NEW FILE########
__FILENAME__ = __main__
#!/usr/bin/env python
import os
import runpy

PKG = 'pagekite'

try:
  run_globals = runpy.run_module(PKG, run_name='__main__', alter_sys=True)
  executed = os.path.splitext(os.path.basename(run_globals['__file__']))[0]
  if executed != '__main__':  # For Python 2.5 compatibility
    raise ImportError('Incorrectly executed %s instead of __main__' %
                      executed)
except ImportError:
  # For Python 2.6 compatibility
  runpy.run_module('%s.__main__' % PKG, run_name='__main__', alter_sys=True)

########NEW FILE########
