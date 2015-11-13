__FILENAME__ = bootstrap
##############################################################################
#
# Copyright (c) 2006 Zope Corporation and Contributors.
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

$Id: bootstrap.py 102545 2009-08-06 14:49:47Z chrisw $
"""

import os, shutil, sys, tempfile, urllib2
from optparse import OptionParser

tmpeggs = tempfile.mkdtemp()

is_jython = sys.platform.startswith('java')

# parsing arguments
parser = OptionParser()
parser.add_option("-v", "--version", dest="version",
                          help="use a specific zc.buildout version")
parser.add_option("-d", "--distribute",
                   action="store_true", dest="distribute", default=True,
                   help="Use Disribute rather than Setuptools.")

options, args = parser.parse_args()

if options.version is not None:
    VERSION = '==%s' % options.version
else:
    VERSION = ''

USE_DISTRIBUTE = options.distribute
args = args + ['bootstrap']

to_reload = False
try:
    import pkg_resources
    if not hasattr(pkg_resources, '_distribute'):
        to_reload = True
        raise ImportError
except ImportError:
    ez = {}
    if USE_DISTRIBUTE:
        exec urllib2.urlopen('http://python-distribute.org/distribute_setup.py'
                         ).read() in ez
        ez['use_setuptools'](to_dir=tmpeggs, download_delay=0, no_fake=True)
    else:
        exec urllib2.urlopen('http://peak.telecommunity.com/dist/ez_setup.py'
                             ).read() in ez
        ez['use_setuptools'](to_dir=tmpeggs, download_delay=0)

    if to_reload:
        reload(pkg_resources)
    else:
        import pkg_resources

if sys.platform == 'win32':
    def quote(c):
        if ' ' in c:
            return '"%s"' % c # work around spawn lamosity on windows
        else:
            return c
else:
    def quote (c):
        return c

cmd = 'from setuptools.command.easy_install import main; main()'
ws  = pkg_resources.working_set

if USE_DISTRIBUTE:
    requirement = 'distribute'
else:
    requirement = 'setuptools'

if is_jython:
    import subprocess

    assert subprocess.Popen([sys.executable] + ['-c', quote(cmd), '-mqNxd',
           quote(tmpeggs), 'zc.buildout' + VERSION],
           env=dict(os.environ,
               PYTHONPATH=
               ws.find(pkg_resources.Requirement.parse(requirement)).location
               ),
           ).wait() == 0

else:
    assert os.spawnle(
        os.P_WAIT, sys.executable, quote (sys.executable),
        '-c', quote (cmd), '-mqNxd', quote (tmpeggs), 'zc.buildout' + VERSION,
        dict(os.environ,
            PYTHONPATH=
            ws.find(pkg_resources.Requirement.parse(requirement)).location
            ),
        ) == 0

ws.add_entry(tmpeggs)
ws.require('zc.buildout' + VERSION)
import zc.buildout.buildout
zc.buildout.buildout.main(args)
shutil.rmtree(tmpeggs)

########NEW FILE########
__FILENAME__ = location
import re

class Location(object):
    def __init__(self, lat=None, long=None, src=None):
        self.optional_keys = [
            "alt",
            "speed",
            "dir",
            "hacc",
            "vacc"
        ]

        self.lat = lat
        self.long = long
        self.src = src

    def format_geocommit(self, keyval_separator, entry_separator):
        """ Formats the location values separating keys, values and k/v pairs

        >>> l = Location(42.1, 23.5, "test")
        >>> l.format_geocommit(":", ",")
        'lat:42.1,long:23.5,src:test'
        >>> l.alt = 257
        >>> l.format_geocommit(" ", "; ")
        'lat 42.1; long 23.5; alt 257; src test'
        """
        end = entry_separator
        sep = keyval_separator

        msg  = "lat"  + sep + str(self.lat)  + end
        msg += "long" + sep + str(self.long) + end

        for attr in self.optional_keys:
            if hasattr(self, attr):
                val = getattr(self, attr)
                if not val is None:
                    msg += attr + sep + str(val) + end

        # no value separator after last value
        msg += "src" + sep + str(self.src)

        return msg

    def format_long_geocommit(self):
        """ Formats the location using the long geocommit format

        >>> l = Location(42.1, 23.5, "test")
        >>> l.format_long_geocommit()
        'geocommit (1.0)\\nlat: 42.1\\nlong: 23.5\\nsrc: test\\n\\n'
        """
        geocommit = "geocommit (1.0)\n"
        geocommit += self.format_geocommit(": ", "\n")
        geocommit += "\n\n"

        return geocommit

    def format_short_geocommit(self):
        """ Formats the location using the long geocommit format

        >>> l = Location(42.1, 23.5, "test")
        >>> l.format_short_geocommit()
        'geocommit(1.0): lat 42.1, long 23.5, src test;'
        """
        geocommit = "geocommit(1.0): "
        geocommit += self.format_geocommit(" ", ", ")
        geocommit += ";"

        return geocommit

    def __repr__(self):
        return '<Location(%s)>' % self.format_short_geocommit()

    @staticmethod
    def from_short_format(data):
        """ Parses a string in short format to create an instance of the class.

        >>> l = Location.from_short_format(
        ...     "geocommit(1.0): lat 1, long 2, alt 3, src a;")
        >>> l.format_short_geocommit()
        'geocommit(1.0): lat 1, long 2, alt 3, src a;'
        """
        m = re.search("geocommit\(1\.0\): ((?:[a-zA-Z0-9_-]+ [^,;]+, )*)([a-zA-Z0-9_-]+ [^,;]+);", data)

        if m is None:
            return None

        values = m.group(1) + m.group(2)

        data = dict()

        for keyval in re.split(",\s+", values):
            key, val = re.split("\s+", keyval, 1)
            data[key] = val

        if not data.has_key("lat") or not data.has_key("long") or not data.has_key("src"):

            return None

        l = Location(data["lat"], data["long"], data["src"])

        for key in l.optional_keys:
            if data.has_key(key):
                setattr(l, key, data[key])

        return l

########NEW FILE########
__FILENAME__ = locationprovider
from distutils.util import get_platform

class LocationProvider(object):
    """ Base class for all location providers which share
    """
    def __init__(self):
        self.name = None

    def get_location(self):
        """ Retrieves a location using this LocationProvider.

        Should be overwritten in specialisations of this class.
        """
        return None

    @staticmethod
    def new():
        if get_platform().startswith("macosx"):
            from geocommit.provider.corelocation import CoreLocationProvider
            return CoreLocationProvider()
        else:
            from geocommit.networkmanager import NetworkManager
            return NetworkManager()

########NEW FILE########
__FILENAME__ = networkmanager

from geocommit.wifilocationprovider import WifiLocationProvider

# This function was adapted from Google Chrome Code licensed under 3 clause BSD.
# Copyright (c) 2010 The Chromium Authors. All rights reserved.
def frequency_in_khz_to_channel(frequency_khz):
    '''
    >>> frequency_in_khz_to_channel(2412000)
    1
    '''
    if frequency_khz >= 2412000 and frequency_khz <= 2472000: # Channels 1-13,
        return (frequency_khz - 2407000) / 5000
    if frequency_khz == 2484000:
        return 14
    if frequency_khz > 5000000 and frequency_khz < 6000000: # .11a bands.
        return (frequency_khz - 5000000) / 5000
    # Ignore everything else.
    return -12345 # invalid channel


try:
    import dbus


    class NetworkManager(WifiLocationProvider):
        """ Retrieves a list of access points from wifi cards for geolocation

        This test just makes sure get_location does not throw.
        >>> nm = NetworkManager()
        >>> void = nm.get_location()
        """
        def __init__(self):
            super(NetworkManager, self).__init__()
            self.name = "nmg"

            self.service_name = "org.freedesktop.NetworkManager";
            self.path = "/org/freedesktop/NetworkManager";
            self.interface = "org.freedesktop.NetworkManager";
            self.ns_properties = "org.freedesktop.DBus.Properties";
            # http://projects.gnome.org/NetworkManager/developers/spec.html
            self.wifi_type = 2
            self.access_token = None

            self.bus = dbus.SystemBus()
            self.nm = self.bus.get_object(self.service_name, self.path)

        def get_devices(self):
            devices = self.nm.GetDevices(dbus_interface=self.interface)

            device_list = []

            for device_path in devices:
                device = self.bus.get_object(self.service_name, device_path)

                device_type = device.Get(
                    self.interface + ".Device",
                    "DeviceType",
                    dbus_interface=self.ns_properties)

                if device_type == self.wifi_type:
                    device_list.append(device_path)

            return device_list

        def get_access_points_for_device(self, device_path, ap_map):
            device = self.bus.get_object(self.service_name, device_path)
            aps = device.GetAccessPoints(
                dbus_interface=self.interface + ".Device.Wireless")

            for ap_path in aps:
                ap = self.bus.get_object(self.service_name, ap_path)

                ap_data = dict()
                ap_data["ssid"] = str(ap.Get(
                    self.interface + ".AccessPoint",
                    "Ssid",
                    dbus_interface=self.ns_properties,
                    byte_arrays=True))

                ap_data["mac_address"] = str(ap.Get(
                    self.interface + ".AccessPoint",
                    "HwAddress",
                    dbus_interface=self.ns_properties,
                    byte_arrays=True))

                strength = ap.Get(
                    self.interface + ".AccessPoint",
                    "Strength",
                    dbus_interface=self.ns_properties)
                # convert into dB percentage
                ap_data["signal_strength"] = -100 + strength / 2;

                frequency = ap.Get(
                    self.interface + ".AccessPoint",
                    "Frequency",
                    dbus_interface=self.ns_properties)
                ap_data["channel"] = frequency_in_khz_to_channel(frequency * 1000)

                ap_map[ap_data["mac_address"]] = ap_data

        def get_access_points(self):
            ap_map = dict()

            for device_path in self.get_devices():
                self.get_access_points_for_device(device_path, ap_map)

            return ap_map

except ImportError:
    pass # no dbus available on this system

########NEW FILE########
__FILENAME__ = tests
import doctest
import unittest

def test_suite():
    return unittest.TestSuite([
      doctest.DocTestSuite('geocommit'),
      doctest.DocTestSuite('geocommit.provider.corelocation'),
      doctest.DocTestSuite('geocommit.locationprovider'),
      doctest.DocTestSuite('geocommit.networkmanager'),
      doctest.DocTestSuite('geocommit.wifilocationprovider'),
    ])

########NEW FILE########
__FILENAME__ = util
import sys
from subprocess import Popen, STDOUT, PIPE
from shlex import split

def system(cmd, cwd=None):
    ret, value = system_exit_code(cmd, cwd)
    return value

def system_exit_code(cmd, cwd=None):
    if isinstance(cmd, basestring):
        cmd = split(cmd)

    process = Popen(cmd, stderr=STDOUT, stdout=PIPE, cwd=cwd)
    # from http://stackoverflow.com/questions/1388753/how-to-get-output-from-subprocess-popen
    value = ""
    while True:
        read = process.stdout.read(1)
        value += read
        if read == '':
            result = process.poll()
            if result != None:
                return result, value

def forward_system(cmd, read_stdin=False):
    if isinstance(cmd, basestring):
        cmd = split(cmd)

    process = Popen(cmd, stdin=PIPE, stdout=PIPE, stderr=PIPE)

    in_data = None

    while True:
        if read_stdin:
            in_data = sys.stdin.read(4096)
            if not in_data:
                read_stdin = False
                in_data = None

        output = process.communicate(in_data)
        if output[0]:
            sys.stdout.write(output[0])
            sys.stdout.flush()
        if output[1]:
            sys.stderr.write(output[1])
            sys.stderr.flush()

        ret = process.poll()

        if ret != None:
            if ret != 0:
                sys.exit(ret)
            break

########NEW FILE########
__FILENAME__ = wifilocationprovider
from geocommit.locationprovider import LocationProvider
from geocommit.location import Location
import json
import urllib2
import sys


class WifiLocationProvider(LocationProvider):
    """ Base class for providers using wifi data and google geolocation

    Documentation of the protocol can be found at:
    http://code.google.com/apis/gears/geolocation_network_protocol.html
    """
    def __init__(self):
        super(WifiLocationProvider, self).__init__()
        self.webservice = "https://www.google.com/loc/json"
        self.access_token = None

    def get_access_points(self):
        """ Retrieves all nearby access points.

        Should be overwritten in specialisations of this class.
        """
        return {"invalid mac": {"mac": "invalid mac", "ssid": "none"}}

    def request_dict(self):
        """ Creates a JSON request string for location information from google.

        The access points are a map from mac addresses to access point
        information dicts.

        >>> wlp = WifiLocationProvider()
        >>> wlp.request_dict()["wifi_towers"]
        [{'mac': 'invalid mac', 'ssid': 'none'}]
        """
        ap_map = self.get_access_points()

        if not ap_map:
            return None

        request = dict()

        request["version"] = "1.1.0"
        request["host"] = "localhost"
        request["request_address"] = True
        request["address_language"] = "en_GB"
        request["wifi_towers"] = ap_map.values()

        if self.access_token:
            request["access_token"] = self.access_token

        return request

    def location_from_dict(self, data):
        """ Converts a Google JSON response into a location object

        >>> wlp = WifiLocationProvider()
        >>> wlp.location_from_dict({"location":
        ...     {"latitude": 1.2, "longitude": 3.4}}).format_geocommit(" ", ", ")
        'lat 1.2, long 3.4, src None'
        """
        if not data.has_key("location"):
            return None

        ldata = data["location"]

        location = Location(ldata["latitude"], ldata["longitude"], self.name)

        optional_keys = {
            "altitude": "alt",
            "accuracy": "hacc",
            "altitude_accuracy": "vacc"
        }

        for json_key, loc_key in optional_keys.iteritems():
            if ldata.has_key(json_key):
                setattr(location, loc_key, ldata[json_key])

        return location

    def json_request(self, data):
        """ Sends a JSON request to google geolocation and parses the response

        >>> wlp = WifiLocationProvider()
        >>> wlp.webservice = "http://unresolvable"
        >>> wlp.json_request({})
        """
        json_request = json.dumps(data, indent=4)

        try:
            result = urllib2.urlopen(self.webservice, json_request).read()
        except urllib2.URLError, e:
            return None

        try:
            response = json.loads(result)
        except ValueError, e:
            return None

        return response

    def get_location(self):
        """ Retrieves a location from Google Geolocation API based on Wifi APs.
        """
        request = self.request_dict()

        if not request:
            return None

        location = self.json_request(request)

        if not location:
            return None

        if location.has_key("access_token"):
            self.access_token = location["access_token"]

        return self.location_from_dict(location)

########NEW FILE########
