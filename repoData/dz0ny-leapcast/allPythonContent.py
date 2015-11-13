__FILENAME__ = default
from __future__ import unicode_literals

from leapcast.services.leap_factory import LEAPfactory


class ChromeCast(LEAPfactory):
    url = "https://www.gstatic.com/cv/receiver.html?{{ query }}"


class YouTube(LEAPfactory):
    url = "https://www.youtube.com/tv?{{ query }}"


class PlayMovies(LEAPfactory):
    url = "https://play.google.com/video/avi/eureka?{{ query }}"
    supported_protocols = ['play-movies', 'ramp']


class GoogleMusic(LEAPfactory):
    url = "https://play.google.com/music/cast/player"


class GoogleCastSampleApp(LEAPfactory):
    url = "http://anzymrcvr.appspot.com/receiver/anzymrcvr.html"


class GoogleCastPlayer(LEAPfactory):
    url = "https://www.gstatic.com/eureka/html/gcp.html"


class Fling(LEAPfactory):
    url = "{{ query }}"


class Pandora_App(LEAPfactory):
    url = "https://tv.pandora.com/cast?{{ query }}"


class TicTacToe(LEAPfactory):
    url = "http://www.gstatic.com/eureka/sample/tictactoe/tictactoe.html"
    supported_protocols = ['com.google.chromecast.demo.tictactoe']

########NEW FILE########
__FILENAME__ = environment
from __future__ import unicode_literals
import argparse
import glob
import logging
import os
import sys
import uuid

logger = logging.getLogger('Environment')


def _get_chrome_path():
    if sys.platform == 'win32':
        # First path includes fallback for Windows XP, because it doesn't have
        # LOCALAPPDATA variable.
        globs = [os.path.join(
            os.getenv(
                'LOCALAPPDATA', os.path.join(os.getenv('USERPROFILE'), 'Local Settings\\Application Data')), 'Google\\Chrome\\Application\\chrome.exe'),
            os.path.join(os.getenv('ProgramW6432', 'C:\\Program Files'),
                         'Google\\Chrome\\Application\\chrome.exe'),
            os.path.join(os.getenv('ProgramFiles(x86)', 'C:\\Program Files (x86)'), 'Google\\Chrome\\Application\\chrome.exe')]
    elif sys.platform == 'darwin':
        globs = [
            '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome']
    else:
        globs = ['/usr/bin/google-chrome',
                 '/opt/google/chrome/google-chrome',
                 '/opt/google/chrome-*/google-chrome',
                 '/usr/bin/chromium-browser']
    for g in globs:
        for path in glob.glob(g):
            if os.path.exists(path):
                return path


class Environment(object):
    channels = dict()
    global_status = dict()
    friendlyName = 'leapcast'
    user_agent = 'Mozilla/5.0 (CrKey - 0.9.3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/30.0.1573.2 Safari/537.36'
    chrome = _get_chrome_path()
    fullscreen = False
    window_size = False
    interfaces = None
    uuid = None
    ips = []
    apps = None
    verbosity = logging.INFO


def parse_cmd():
    parser = argparse.ArgumentParser()
    parser.add_argument('-d', '--debug', action='store_true',
                        default=False, dest='debug', help='Debug')
    parser.add_argument('-i', '--interface', action='append',
                        dest='interfaces',
                        help='Interface to bind to (can be specified multiple times)',
                        metavar='IPADDRESS')
    parser.add_argument('--name', help='Friendly name for this device')
    parser.add_argument('--user_agent', help='Custom user agent')
    parser.add_argument('--chrome', help='Path to Google Chrome executable')
    parser.add_argument('--fullscreen', action='store_true',
                        default=False, help='Start in full-screen mode')
    parser.add_argument('--window_size',
                        default=False,
                        help='Set the initial chrome window size. eg 1920,1080')
    parser.add_argument(
        '--ips', help='Allowed ips from which clients can connect')
    parser.add_argument('--apps', help='Add apps from JSON file')

    args = parser.parse_args()

    if args.debug:
        Environment.verbosity = logging.DEBUG
    logging.basicConfig(level=Environment.verbosity)

    if args.interfaces:
        Environment.interfaces = args.interfaces
        logger.debug('Interfaces is %s' % Environment.interfaces)

    if args.name:
        Environment.friendlyName = args.name
        logger.debug('Service name is %s' % Environment.friendlyName)

    if args.user_agent:
        Environment.user_agent = args.user_agent
        logger.debug('User agent is %s' % args.user_agent)

    if args.chrome:
        Environment.chrome = args.chrome
        logger.debug('Chrome path is %s' % args.chrome)

    if args.fullscreen:
        Environment.fullscreen = True

    if args.window_size:
        Environment.window_size = args.window_size

    if args.ips:
        Environment.ips = args.ips

    if args.apps:
        Environment.apps = args.apps

    if Environment.chrome is None:
        parser.error('could not locate chrome; use --chrome to specify one')

    generate_uuid()


def generate_uuid():
    Environment.uuid = str(uuid.uuid5(
        uuid.NAMESPACE_DNS, ('device.leapcast.%s' %
                             Environment.friendlyName).encode('utf8')))

########NEW FILE########
__FILENAME__ = dial
from __future__ import unicode_literals

import leapcast
from leapcast.environment import Environment
from leapcast.services.websocket import App
from leapcast.utils import render
import tornado.web


class DeviceHandler(tornado.web.RequestHandler):

    '''
    Holds info about device
    '''

    device = '''<?xml version="1.0" encoding="utf-8"?>
    <root xmlns="urn:schemas-upnp-org:device-1-0" xmlns:r="urn:restful-tv-org:schemas:upnp-dd">
        <specVersion>
        <major>1</major>
        <minor>0</minor>
        </specVersion>
        <URLBase>{{ path }}</URLBase>
        <device>
            <deviceType>urn:schemas-upnp-org:device:dail:1</deviceType>
            <friendlyName>{{ friendlyName }}</friendlyName>
            <manufacturer>Google Inc.</manufacturer>
            <modelName>Eureka Dongle</modelName>
            <UDN>uuid:{{ uuid }}</UDN>
            <serviceList>
                <service>
                    <serviceType>urn:schemas-upnp-org:service:dail:1</serviceType>
                    <serviceId>urn:upnp-org:serviceId:dail</serviceId>
                    <controlURL>/ssdp/notfound</controlURL>
                    <eventSubURL>/ssdp/notfound</eventSubURL>
                    <SCPDURL>/ssdp/notfound</SCPDURL>
                </service>
            </serviceList>
        </device>
    </root>'''

    def get(self):
        if Environment.ips and self.request.remote_ip not in Environment.ips:
            raise tornado.web.HTTPError(403)

        if self.request.uri == "/apps":
            for app, astatus in Environment.global_status.items():
                if astatus["state"] == "running":
                    self.redirect("/apps/%s" % app)
            self.set_status(204)
            self.set_header(
                "Access-Control-Allow-Method", "GET, POST, DELETE, OPTIONS")
            self.set_header("Access-Control-Expose-Headers", "Location")
        else:
            self.set_header(
                "Access-Control-Allow-Method", "GET, POST, DELETE, OPTIONS")
            self.set_header("Access-Control-Expose-Headers", "Location")
            self.add_header(
                "Application-URL", "http://%s/apps" % self.request.host)
            self.set_header("Content-Type", "application/xml")
            self.write(render(self.device).generate(
                friendlyName=Environment.friendlyName,
                uuid=Environment.uuid,
                path="http://%s" % self.request.host)
            )


class SetupHandler(tornado.web.RequestHandler):

    '''
    Holds info about device setup and status
    '''

    status = '''{
        "build_version":"{{ buildVersion}}",
        "connected":true,
        "detail":{
            "locale":{"display_string":"English (United States)"},
            "timezone":{"display_string":"America/Los Angeles",offset:-480}
        },
        "has_update":false,
        "hdmi_control":true,
        "hotspot_bssid":"FA:8F:CA:3A:0C:D0",
        "locale": "en_US",
        "mac_address":"00:00:00:00:00:00",
        "name":"{{ name }}",
        "noise_level":-90,
        "opt_in":{"crash":true,"device_id":false,"stats":true},
        "public_key":"MIIBCgKCAQEAyoaWlKNT6W5+/cJXEpIfeGvogtJ1DghEUs2PmHkX3n4bByfmMRDYjuhcb97vd8N3HFe5sld6QSc+FJz7TSGp/700e6nrkbGj9abwvobey/IrLbHTPLtPy/ceUnwmAXczkhay32auKTaM5ZYjwcHZkaU9XuOQVIPpyLF1yQerFChugCpQ+bvIoJnTkoZAuV1A1Vp4qf3nn4Ll9Bi0R4HJrGNmOKUEjKP7H1aCLSqj13FgJ2s2g20CCD8307Otq8n5fR+9/c01dtKgQacupysA+4LVyk4npFn5cXlzkkNPadcKskARtb9COTP2jBWcowDwjKSBokAgi/es/5gDhZm4dwIDAQAB",
        "release_track":"stable-channel",
        "setup_state":60,
        {% raw signData %}
        "signal_level":-50,
        "ssdp_udn":"82c5cb87-27b4-2a9a-d4e1-5811f2b1992c",
        "ssid":"{{ friendlyName }}",
        "timezone":"America/Los_Angeles",
        "uptime":0.0,
        "version":4,
        "wpa_configured":true,
        "wpa_state":10
    }'''

    # Chromium OS's network_DestinationVerification.py has a verify test that
    # shows that it is possible to verify signed_data by:
    #   echo "<signed_data>" | base64 -d | openssl rsautl -verify -inkey <certificate> -certin -asn1parse
    # The signed string should match:
    #   echo -n "<name>,<ssdp_udn>,<hotspot_bssid>,<public_key>,<nonce>" | openssl sha1 -binary | hd

    sign_data = '''
        "sign": {
            "certificate":"-----BEGIN CERTIFICATE-----\\nMIIDqzCCApOgAwIBAgIEUf6McjANBgkqhkiG9w0BAQUFADB9MQswCQYDVQQGEwJV\\nUzETMBEGA1UECAwKQ2FsaWZvcm5pYTEWMBQGA1UEBwwNTW91bnRhaW4gVmlldzET\\nMBEGA1UECgwKR29vZ2xlIEluYzESMBAGA1UECwwJR29vZ2xlIFRWMRgwFgYDVQQD\\nDA9FdXJla2EgR2VuMSBJQ0EwHhcNMTMwODA0MTcxNjM0WhcNMzMwNzMwMTcxNjM0\\nWjCBgDETMBEGA1UEChMKR29vZ2xlIEluYzETMBEGA1UECBMKQ2FsaWZvcm5pYTEL\\nMAkGA1UEBhMCVVMxFjAUBgNVBAcTDU1vdW50YWluIFZpZXcxEjAQBgNVBAsTCUdv\\nb2dsZSBUVjEbMBkGA1UEAxMSWktCVjIgRkE4RkNBM0EwQ0QwMIIBIjANBgkqhkiG\\n9w0BAQEFAAOCAQ8AMIIBCgKCAQEA+HGhzj+XEwhUT7W4FbaR8M2sNxCF0VrlWsw6\\nSkFHOINt6t+4B11Q7TSfz1yzrMhUSQvaE2gP2F/h3LD03rCnnE4avonZYTBr/U/E\\nJZYDjEtOClFmBmqNf6ZEE8bxF/nsit1e5XicO0OJHSmRlvibbrmC2rnFwj/cEDpm\\na1hdqpRQkeG0ceb9qbvvpxBq4MBsomzzbSq2nl7dQFBpxDd2jm7g+4EC7KqWmkWt\\n3XgX++0qk4qFlbc/+ySqheYYddU0eeExvg93WkTRr5m6ZuaTQn7LOO9IiR8PwSnz\\nxQmuirtAc50089T1oyV7ANZlNtj2oW2XjKUvxA3n+x8jCqAwfwIDAQABoy8wLTAJ\\nBgNVHRMEAjAAMAsGA1UdDwQEAwIHgDATBgNVHSUEDDAKBggrBgEFBQcDAjANBgkq\\nhkiG9w0BAQUFAAOCAQEAXmXinb7zoutrwCw+3SQVGbQycnMpWz1hDRS+BZ04QCm0\\naxneva74Snptjasnw3eEW9Yb1N8diLlrUWkT5Q9l8AA/W4R3B873lPTzWhobXFCq\\nIhrkTDBSOtx/bQj7Sy/npmoj6glYlKKANqTCDhjHvykOLrUUeCjltYAy3i8km+4b\\nTxjfB6D3IIGB3kvb1L4TmvgSuXDhkz0qx2qR/bM6vGShnNRCQo6oR4hAMFlvDlXR\\nhRfuibIJwtbA2cLUyG/UjgQwJEPrlOT6ZyLRHWMjiROKcqv3kqatBfNyIjkVD4uH\\nc+WK9DlJnI9bLy46qYRVbzhhDJUkfZVtDKiUbvz3bg==\\n-----END CERTIFICATE-----\\n",
            "nonce": "Aw4o0/sbVr537Kdrw9YotiXxCLIaiRrDkHeHrOpih3U=",
            "signed_data": "fcTwn3K4I/ccok1MeZ5/nkM0pI5v4SrTv3Q4ppOQtVL5ii3qitNo+NLhY+DM9zmnP6ndNMZbkyIEyMm7LjganoDoE+o0e0/r4TyGEGLxYlfWSzf+Z3cSdNe4+MyHx/7z02E0/3lLsOFuOEPSgR26JFtyhDLCJ9Y8Cpl3GZMUqm4toaTNaIbhNMR9Bwjkz4ozKXzFl9dF5FTU6N48KeUP/3CuYqgm04BVUGxg+DbBmTidRnZE4eGdt9ICJht9ArUNQDL2UdRYVY2sfgLmF29exTaSrVkBZb/MsbDxN5nYpF1uE7IhzJnT5yFM9pmUOIKKTfeVaLVLGgoWd+pjEbOv+Q=="
        },
    '''

    timezones = '''[
        {"timezone":"America/Los_Angeles","display_string":"America/Los Angeles","offset":-480}
    ]'''
    locales = '''[
        {"locale":"en_US","display_string":"English (United States)"}
    ]'''
    wifi_networks = '''[
        {"bssid":"00:00:00:00:00:00","signal_level":-60,"ssid":"leapcast","wpa_auth":7,"wpa_cipher":4}
    ]'''

    def get(self, module=None):
        if Environment.ips and self.request.remote_ip not in Environment.ips:
            raise tornado.web.HTTPError(403)

        if module == "eureka_info":
            self.set_header(
                "Access-Control-Allow-Headers", "Content-Type")
            self.set_header(
                "Access-Control-Allow-Origin", "https://cast.google.com")
            self.set_header("Content-Type", "application/json")
            if 'sign' in self.request.query:
                name = 'Chromecast8991'
                signData = self.sign_data
            else:
                name = Environment.friendlyName
                signData = ''
            self.write(render(self.status).generate(
                name=name,
                friendlyName=Environment.friendlyName,
                buildVersion='leapcast %s' % leapcast.__version__,
                signData=signData,
                uuid=Environment.uuid)
            )
        elif module == "supported_timezones":
            self.set_header("Content-Type", "application/json")
            self.write(self.timezones)
        elif module == "supported_locales":
            self.set_header("Content-Type", "application/json")
            self.write(self.locales)
        elif module == "scan_results":
            self.set_header("Content-Type", "application/json")
            self.write(self.wifi_networks)
        else:
            raise tornado.web.HTTPError(404)

    def post(self, module=None):
        if ((len(Environment.ips) == 0) | (self.request.remote_ip in Environment.ips)):
            if module == "scan_wifi":
                pass
            elif module == "set_eureka_info":
                pass
            elif module == "connect_wifi":
                pass
            else:
                raise tornado.web.HTTPError(404)
        else:
            raise tornado.web.HTTPError(404)


class ChannelFactory(tornado.web.RequestHandler):

    '''
    Creates Websocket Channel. This is requested by 2nd screen application
    '''
    @tornado.web.asynchronous
    def post(self, app=None):
        self.app = App.get_instance(app)
        self.set_header(
            "Access-Control-Allow-Method", "POST, OPTIONS")
        self.set_header("Access-Control-Allow-Headers", "Content-Type")
        self.set_header("Content-Type", "application/json")
        self.finish(
            '{"URL":"ws://%s/session/%s?%s","pingInterval":3}' % (
                self.request.host, app, self.app.get_apps_count())
        )
        self.app.create_application_channel(self.request.body)

########NEW FILE########
__FILENAME__ = leap
from __future__ import unicode_literals

import tornado.ioloop
import tornado.web
import tornado.websocket
import logging
import json
import requests
from leapcast.apps.default import *
from leapcast.services.dial import DeviceHandler, ChannelFactory, SetupHandler
from leapcast.services.websocket import ServiceChannel, ReceiverChannel, ApplicationChannel, CastPlatform
from leapcast.services.leap_factory import LEAPfactory
from leapcast.environment import Environment


class LEAPserver(object):

    def start(self):
        logging.info('Starting LEAP server')
        routes = [
            (r"/ssdp/device-desc.xml", DeviceHandler),
            (r"/setup/([^\/]+)", SetupHandler),
            (r"/apps", DeviceHandler),
            (r"/connection", ServiceChannel),
            (r"/connection/([^\/]+)", ChannelFactory),
            (r"/receiver/([^\/]+)", ReceiverChannel),
            (r"/session/([^\/]+)", ApplicationChannel),
            (r"/system/control", CastPlatform),
        ]

        # download apps from google servers
        logging.info('Loading Config-JSON from Google-Server')
        app_dict_url = 'https://clients3.google.com/cast/chromecast/device/config'
        # load json-file
        resp = requests.get(url=app_dict_url)
        logging.info('Parsing Config-JSON')
        # parse json-file
        data = json.loads(resp.content.replace(")]}'", ""))
        # list of added apps for apps getting added manually
        added_apps = []

        if Environment.apps:
            logging.info('Reading app file: %s' % Environment.apps)
            try:
                f = open(Environment.apps)
                tmp = json.load(f)
                f.close()

                for key in tmp:
                    if key == 'applications':
                        data[key] += tmp[key]

                    else:
                        data[key] = tmp[key]
            except Exception as e:
                logging.error('Couldn\'t read app file: %s' % e)

        for app in data['applications']:
            name = app['app_name']
            name = name.encode('utf-8')
            if 'url' not in app:
                logging.warn('Didn\'t add %s because it has no URL!' % name)
                continue
            logging.info('Added %s app' % name)
            url = app['url']
            url = url.replace("${{URL_ENCODED_POST_DATA}}", "{{ query }}").replace(
                "${POST_DATA}", "{{ query }}")
            # this doesn't support all params yet, but seems to work with
            # youtube, chromecast and play music.
            clazz = type((name), (LEAPfactory,), {"url": url})
            routes.append(("(/apps/" + name + "|/apps/" + name + ".*)", clazz))
            added_apps.append(name)

        # add registread apps
        for app in LEAPfactory.get_subclasses():
            name = app.__name__
            if name in added_apps:
                continue
            logging.info('Added %s app' % name)
            routes.append((
                          r"(/apps/" + name + "|/apps/" + name + ".*)", app))

        self.application = tornado.web.Application(routes)
        self.application.listen(8008)
        tornado.ioloop.IOLoop.instance().start()

    def shutdown(self, ):
        logging.info('Stopping DIAL server')
        tornado.ioloop.IOLoop.instance().stop()

    def sig_handler(self, sig, frame):
        tornado.ioloop.IOLoop.instance().add_callback(self.shutdown)

########NEW FILE########
__FILENAME__ = leap_factory
from __future__ import unicode_literals

import subprocess
import copy
import logging
import tempfile
import shutil
import tornado.websocket
import tornado.ioloop
import tornado.web
from leapcast.services.websocket import App
from leapcast.utils import render
from leapcast.environment import Environment


class Browser(object):

    def __init__(self, appurl):
        args = [
            Environment.chrome,
            '--allow-running-insecure-content',
            '--no-default-browser-check',
            '--ignore-gpu-blacklist',
            '--incognito',
            '--no-first-run',
            '--kiosk',
            '--disable-translate',
            '--user-agent=%s' % Environment.user_agent.encode('utf8')
        ]
        self.tmpdir = tempfile.mkdtemp(prefix='leapcast-')
        args.append('--user-data-dir=%s' % self.tmpdir)
        if Environment.window_size:
            args.append('--window-size=%s' % Environment.window_size)
        if not Environment.fullscreen:
            args.append('--app=%s' % appurl.encode('utf8'))
        else:
            args.append(appurl.encode('utf8'))
        logging.debug(args)
        self.pid = subprocess.Popen(args)

    def destroy(self):
        self.pid.terminate()
        self.pid.wait()
        shutil.rmtree(self.tmpdir)

    def is_running(self):
        return self.pid.poll() is None

    def __bool__(self):
        return self.is_running()


class LEAPfactory(tornado.web.RequestHandler):
    application_status = dict(
        name='',
        state='stopped',
        link='',
        browser=None,
        connectionSvcURL='',
        protocols='',
        app=None
    )

    service = '''<?xml version='1.0' encoding='UTF-8'?>
    <service xmlns='urn:dial-multiscreen-org:schemas:dial'>
        <name>{{ name }}</name>
        <options allowStop='true'/>
        {% if state == "running" %}
        <servicedata xmlns='urn:chrome.google.com:cast'>
            <connectionSvcURL>{{ connectionSvcURL }}</connectionSvcURL>
            <protocols>
                {% for x in protocols %}
                <protocol>{{ x }}</protocol>
                {% end %}
            </protocols>
        </servicedata>
        {% end %}
        <state>{{ state }}</state>
        {% if state == "running" %}
        <activity-status xmlns="urn:chrome.google.com:cast">
          <description>{{ name }} Receiver</description>
        </activity-status>
        <link rel='run' href='web-1'/>
        {% end %}
    </service>
    '''

    ip = None
    url = '{{query}}'
    supported_protocols = ['ramp']

    @classmethod
    def get_subclasses(c):
        subclasses = c.__subclasses__()
        return list(subclasses)

    def get_name(self):
        return self.__class__.__name__

    def get_status_dict(self):
        status = copy.deepcopy(self.application_status)
        status['name'] = self.get_name()
        return status

    def prepare(self):
        self.ip = self.request.host

    def get_app_status(self):
        return Environment.global_status.get(self.get_name(), self.get_status_dict())

    def set_app_status(self, app_status):

        app_status['name'] = self.get_name()
        Environment.global_status[self.get_name()] = app_status

    def _response(self):
        self.set_header('Content-Type', 'application/xml')
        self.set_header(
            'Access-Control-Allow-Method', 'GET, POST, DELETE, OPTIONS')
        self.set_header('Access-Control-Expose-Headers', 'Location')
        self.set_header('Cache-control', 'no-cache, must-revalidate, no-store')
        self.finish(self._toXML(self.get_app_status()))

    @tornado.web.asynchronous
    def post(self, sec):
        '''Start app'''
        self.clear()
        self.set_status(201)
        self.set_header('Location', self._getLocation(self.get_name()))
        status = self.get_app_status()
        if status['browser'] is None:
            status['state'] = 'running'
            if self.url == "https://tv.pandora.com/cast?{{ query }}":
                appurl = render(self.url.replace("{{ query }}", self.request.body)).generate(query=self.request.body)
            else:
                appurl = render(self.url).generate(query=self.request.body)
            status['browser'] = Browser(appurl)
            status['connectionSvcURL'] = 'http://%s/connection/%s' % (
                self.ip, self.get_name())
            status['protocols'] = self.supported_protocols
            status['app'] = App.get_instance(sec)

        self.set_app_status(status)
        self.finish()

    def stop_app(self):
        self.clear()
        browser = self.get_app_status()['browser']
        if browser is not None:
            browser.destroy()
        else:
            logging.warning('App already closed in destroy()')
        status = self.get_status_dict()
        status['state'] = 'stopped'
        status['browser'] = None

        self.set_app_status(status)

    @tornado.web.asynchronous
    def get(self, sec):
        '''Status of an app'''
        self.clear()
        browser = self.get_app_status()['browser']
        if not browser:
            logging.debug('App crashed or closed')
            # app crashed or closed
            status = self.get_status_dict()
            status['state'] = 'stopped'
            status['browser'] = None
            self.set_app_status(status)

        self._response()

    @tornado.web.asynchronous
    def delete(self, sec):
        '''Close app'''
        self.stop_app()
        self._response()

    def _getLocation(self, app):
        return 'http://%s/apps/%s/web-1' % (self.ip, app)

    def _toXML(self, data):
        return render(self.service).generate(**data)

    @classmethod
    def toInfo(cls):
        data = copy.deepcopy(cls.application_status)
        data['name'] = cls.__name__
        data = Environment.global_status.get(cls.__name__, data)
        return render(cls.service).generate(data)

########NEW FILE########
__FILENAME__ = ssdp
# -*- coding: utf8 -*-

from __future__ import unicode_literals
import contextlib
import socket
from leapcast.utils import render
from leapcast.environment import Environment
import struct
import operator
import logging
from leapcast.utils import ControlMixin
from SocketServer import ThreadingUDPServer, DatagramRequestHandler


def GetInterfaceAddress(if_name):
    import fcntl  # late import as this is only supported on Unix platforms.
    SIOCGIFADDR = 0x8915
    with contextlib.closing(socket.socket(socket.AF_INET, socket.SOCK_DGRAM)) as s:
        return fcntl.ioctl(s.fileno(), SIOCGIFADDR, struct.pack(b'256s', if_name[:15]))[20:24]


class MulticastServer(ControlMixin, ThreadingUDPServer):

    allow_reuse_address = True

    def __init__(self, addr, handler, poll_interval=0.5, bind_and_activate=True, interfaces=None):
        ThreadingUDPServer.__init__(self, ('', addr[1]),
                                    handler,
                                    bind_and_activate)
        ControlMixin.__init__(self, handler, poll_interval)
        self._multicast_address = addr
        self._listen_interfaces = interfaces
        self.setLoopbackMode(1)  # localhost
        self.setTTL(2)  # localhost and local network
        self.handle_membership(socket.IP_ADD_MEMBERSHIP)

    def setLoopbackMode(self, mode):
        mode = struct.pack("b", operator.truth(mode))
        self.socket.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_LOOP,
                               mode)

    def server_bind(self):
        try:
            if hasattr(socket, "SO_REUSEADDR"):
                self.socket.setsockopt(
                    socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        except Exception as e:
            logging.log(e)
        try:
            if hasattr(socket, "SO_REUSEPORT"):
                self.socket.setsockopt(
                    socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        except Exception as e:
            logging.log(e)
        ThreadingUDPServer.server_bind(self)

    def handle_membership(self, cmd):
        if self._listen_interfaces is None:
            mreq = struct.pack(
                str("4sI"), socket.inet_aton(self._multicast_address[0]),
                socket.INADDR_ANY)
            self.socket.setsockopt(socket.IPPROTO_IP,
                                   cmd, mreq)
        else:
            for interface in self._listen_interfaces:
                try:
                    if_addr = socket.inet_aton(interface)
                except socket.error:
                    if_addr = GetInterfaceAddress(interface)
                mreq = socket.inet_aton(self._multicast_address[0]) + if_addr
                self.socket.setsockopt(socket.IPPROTO_IP,
                                       cmd, mreq)

    def setTTL(self, ttl):
        ttl = struct.pack("B", ttl)
        self.socket.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, ttl)

    def server_close(self):
        self.handle_membership(socket.IP_DROP_MEMBERSHIP)


class SSDPHandler(DatagramRequestHandler):

    header = '''\
    HTTP/1.1 200 OK\r
    LOCATION: http://{{ ip }}:8008/ssdp/device-desc.xml\r
    CACHE-CONTROL: max-age=1800\r
    CONFIGID.UPNP.ORG: 7337\r
    BOOTID.UPNP.ORG: 7337\r
    USN: uuid:{{ uuid }}\r
    ST: urn:dial-multiscreen-org:service:dial:1\r
    \r
    '''

    def handle(self):
        data = self.request[0].strip()
        self.datagramReceived(data, self.client_address)

    def reply(self, data, address):
        socket = self.request[1]
        socket.sendto(data, address)

    def get_remote_ip(self, address):
        # Create a socket to determine what address the client should
        # use
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(address)
        iface = s.getsockname()[0]
        s.close()
        return unicode(iface)

    def datagramReceived(self, datagram, address):
        if "urn:dial-multiscreen-org:service:dial:1" in datagram and "M-SEARCH" in datagram:
            data = render(self.header).generate(
                ip=self.get_remote_ip(address),
                uuid=Environment.uuid
            )
            self.reply(data, address)


class SSDPserver(object):
    SSDP_ADDR = '239.255.255.250'
    SSDP_PORT = 1900

    def start(self, interfaces):
        logging.info('Starting SSDP server')
        self.server = MulticastServer(
            (self.SSDP_ADDR, self.SSDP_PORT), SSDPHandler, interfaces=interfaces)
        self.server.start()

    def shutdown(self):
        logging.info('Stopping SSDP server')
        self.server.server_close()
        self.server.stop()

########NEW FILE########
__FILENAME__ = websocket
# -*- coding: utf8 -*-

from __future__ import unicode_literals
from collections import deque
import json
import logging
from leapcast.environment import Environment
import tornado.web
import threading
from __builtin__ import id


class App(object):

    '''
    Used to relay messages between app Environment.channels
    '''
    name = ""
    lock = threading.Event()
    remotes = list()
    receivers = list()
    rec_queue = list()
    buf = {}  # Buffers if the channel are not ready
    control_channel = list()
    senderid = False
    info = None

    @classmethod
    def get_instance(cls, app):

        if app in Environment.channels:
            return Environment.channels[app]
        else:
            instance = App()
            instance.name = app
            Environment.channels[app] = instance
            return instance

    def set_control_channel(self, ch):
        logging.info("Channel for app set to %s", ch)
        self.control_channel.append(ch)

    def get_control_channel(self):
        try:
            logging.info("Channel for app is %s", self.control_channel[-1])
            return self.control_channel[-1]
        except Exception:
            return False

    def get_apps_count(self):
        return len(self.remotes)

    def add_remote(self, remote):
        self.remotes.append(remote)

    def add_receiver(self, receiver):
        self.receivers.append(receiver)
        if id(receiver) in self.buf:
            self.rec_queue.append(self.buf[id(receiver)])
        else:
            self.rec_queue.append(deque())

    def get_deque(self, instance):
        try:
            _id = self.receivers.index(instance)
            return self.rec_queue[_id]
        except Exception:
            if id(instance) in self.buf:
                return self.buf[id(instance)]
            else:
                self.buf[id(instance)] = deque()
                return self.buf[id(instance)]

    def get_app_channel(self, receiver):
        try:
            return self.remotes[self.receivers.index(receiver)]
        except Exception:
            return False

    def get_self_app_channel(self, app):
        try:
            if isinstance(self.remotes[self.remotes.index(app)].ws_connection, type(None)):
                return False
            return self.remotes[self.remotes.index(app)]
        except Exception:
            return False

    def get_recv_channel(self, app):
        try:
            """
            if type(self.receivers[self.remotes.index(app)].ws_connection) != type(None):
                return self.receivers[self.remotes.index(app)]
            """
            if isinstance(self.receivers[self.remotes.index(app)].ws_connection, type(None)):
                return False
            return self.receivers[self.remotes.index(app)]
        except Exception:
            return False

    def create_application_channel(self, data):
        if self.get_control_channel():
            self.get_control_channel().new_request()
        else:
            CreateChannel(self.name, data, self.lock).start()

    def stop(self):
        for ws in self.remotes:
            try:
                ws.close()
            except Exception:
                pass
        self.remotes = list()
        for ws in self.receivers:
            try:
                ws.close()
            except Exception:
                pass
        self.receivers = list()
        self.control_channel.pop()
        app = Environment.global_status.get(self.name, False)
        if app:
            app.stop_app()
        self.buf = {}


class CreateChannel (threading.Thread):

    def __init__(self, name, data, lock):
        threading.Thread.__init__(self)
        self.name = name
        self.data = data
        self.lock = lock

    def run(self):
        # self.lock.wait(30)
        self.lock.clear()
        self.lock.wait()
        App.get_instance(
            self.name).get_control_channel().new_request(self.data)


class ServiceChannel(tornado.websocket.WebSocketHandler):

    '''
    ws /connection
    From 1st screen app
    '''
    buf = list()

    def open(self, app=None):
        self.app = App.get_instance(app)
        self.app.set_control_channel(self)
        while len(self.buf) > 0:
            self.reply(self.buf.pop())

    def on_message(self, message):
        cmd = json.loads(message)
        if cmd["type"] == "REGISTER":
            self.app.lock.set()
            self.app.info = cmd

        if cmd["type"] == "CHANNELRESPONSE":
            self.new_channel()

    def reply(self, msg):
        if isinstance(self.ws_connection, type(None)):
            self.buf.append(msg)
        else:
            self.write_message((json.dumps(msg)))

    def new_channel(self):
        logging.info("NEWCHANNEL for app %s" % (self.app.info["name"]))
        ws = "ws://localhost:8008/receiver/%s" % self.app.info["name"]
        self.reply(
            {
                "type": "NEWCHANNEL",
                "senderId": self.senderid,
                "requestId": self.app.get_apps_count(),
                "URL": ws
            }
        )

    def new_request(self, data=None):
        logging.info("CHANNELREQUEST for app %s" % (self.app.info["name"]))
        if data:
            try:
                data = json.loads(data)
                self.senderid = data["senderId"]
            except Exception:
                self.senderid = self.app.get_apps_count()
        else:
            self.senderid = self.app.get_apps_count()

        self.reply(
            {
                "type": "CHANNELREQUEST",
                "senderId": self.senderid,
                "requestId": self.app.get_apps_count(),
            }
        )

    def on_close(self):
        self.app.stop()


class WSC(tornado.websocket.WebSocketHandler):

    def open(self, app=None):
        self.app = App.get_instance(app)
        self.cname = self.__class__.__name__

        logging.info("%s opened %s" %
                     (self.cname, self.request.uri))

    def on_message(self, message):
        if Environment.verbosity is logging.DEBUG:
            pretty = json.loads(message)
            message = json.dumps(
                pretty, sort_keys=True, indent=2)
            logging.debug("%s: %s" % (self.cname, message))

    def on_close(self):
        if self.app.name in Environment.channels:
            del Environment.channels[self.app.name]
        logging.info("%s closed %s" %
                     (self.cname, self.request.uri))


class ReceiverChannel(WSC):

    '''
    ws /receiver/$app
    From 1st screen app
    '''

    def open(self, app=None):
        super(ReceiverChannel, self).open(app)
        self.app.add_receiver(self)

        queue = self.app.get_deque(self)
        while len(queue) > 0:
            self.on_message(queue.pop())

    def on_message(self, message):
        channel = self.app.get_app_channel(self)
        if channel:
            queue = self.app.get_deque(self)
            while len(queue) > 0:
                self.on_message(queue.pop())

            super(ReceiverChannel, self).on_message(message)
            channel.write_message(message)
        else:
            queue = self.app.get_deque(self)
            queue.append(message)

    def on_close(self):
        channel = self.app.get_app_channel(self)
        try:
            self.app.receivers.remove(self)
        except:
            pass

        if channel:
            channel.on_close()


class ApplicationChannel(WSC):

    '''
    ws /session/$app
    From 2nd screen app
    '''

    def ping(self):
        self.app.get_deque(self)

        channel = self.app.get_self_app_channel(self)
        if channel:
            data = json.dumps(["cm", {"type": "ping", "cmd_id": 0}])
            channel.write_message(data)
            # TODO Magic number -- Not sure what the interval should be, the
            # value of `pingInterval` is 0.
            threading.Timer(5, self.ping).start()

    def open(self, app=None):
        super(ApplicationChannel, self).open(app)
        self.app.add_remote(self)
        self.app.get_deque(self)

        self.ping()

    def on_message(self, message):
        channel = self.app.get_recv_channel(self)
        if channel:
            queue = self.app.get_deque(self)
            while len(queue) > 0:
                self.on_message(queue.pop())

            super(ApplicationChannel, self).on_message(message)
            channel.write_message(message)
        else:
            queue = self.app.get_deque(self)
            queue.append(message)

    def on_close(self):
        channel = self.app.get_recv_channel(self)
        try:
            self.app.remotes.remove(self)
        except:
            pass

        if channel:
            channel.on_close()


class CastPlatform(tornado.websocket.WebSocketHandler):

    '''
    Remote control over WebSocket.

    Commands are:
    {u'type': u'GET_VOLUME', u'cmd_id': 1}
    {u'type': u'GET_MUTED', u'cmd_id': 2}
    {u'type': u'VOLUME_CHANGED', u'cmd_id': 3}
    {u'type': u'SET_VOLUME', u'cmd_id': 4}
    {u'type': u'SET_MUTED', u'cmd_id': 5}

    Device control:

    '''

    def on_message(self, message):
        pass

########NEW FILE########
__FILENAME__ = utils
# -*- coding: utf8 -*-

from __future__ import unicode_literals
from tornado.template import Template
from textwrap import dedent
import threading


def render(template):
    return Template(dedent(template))


class ControlMixin(object):

    def __init__(self, handler, poll_interval):
        self._thread = None
        self.poll_interval = poll_interval
        self._handler = handler

    def start(self):
        self._thread = t = threading.Thread(target=self.serve_forever,
                                            args=(self.poll_interval,))
        t.setDaemon(True)
        t.start()

    def stop(self):
        self.shutdown()
        self._thread.join()
        self._thread = None

########NEW FILE########
__FILENAME__ = __main__
#!/usr/bin/env python
# -*- coding: utf8 -*-

from __future__ import unicode_literals

import signal
import logging
import sys
from os import environ


from leapcast.environment import parse_cmd, Environment
from leapcast.services.leap import LEAPserver
from leapcast.services.ssdp import SSDPserver

logger = logging.getLogger('Leapcast')


def main():
    parse_cmd()

    if sys.platform == 'darwin' and environ.get('TMUX') is not None:
        logger.error('Running Chrome inside tmux on OS X might cause problems.'
                     ' Please start leapcast outside tmux.')
        sys.exit(1)

    def shutdown(signum, frame):
        ssdp_server.shutdown()
        leap_server.sig_handler(signum, frame)

    signal.signal(signal.SIGTERM, shutdown)
    signal.signal(signal.SIGINT, shutdown)

    ssdp_server = SSDPserver()
    ssdp_server.start(Environment.interfaces)

    leap_server = LEAPserver()
    leap_server.start()

if __name__ == "__main__":
    main()

########NEW FILE########
