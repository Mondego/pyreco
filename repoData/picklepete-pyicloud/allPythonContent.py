__FILENAME__ = base
import uuid
import hashlib
import json
import requests
import sys

from pyicloud.exceptions import PyiCloudFailedLoginException
from pyicloud.services import (
    FindMyiPhoneServiceManager,
    CalendarService,
    UbiquityService
)


class PyiCloudService(object):
    """
    A base authentication class for the iCloud service. Handles the
    validation and authentication required to access iCloud services.

    Usage:
        from pyicloud import PyiCloudService
        pyicloud = PyiCloudService('username@apple.com', 'password')
        pyicloud.iphone.location()
    """
    def __init__(self, apple_id, password):
        self.discovery = None
        self.client_id = str(uuid.uuid1()).upper()
        self.user = {'apple_id': apple_id, 'password': password}

        self._home_endpoint = 'https://www.icloud.com'
        self._setup_endpoint = 'https://p12-setup.icloud.com/setup/ws/1'
        self._push_endpoint = 'https://p12-pushws.icloud.com'

        self._base_login_url = '%s/login' % self._setup_endpoint
        self._base_validate_url = '%s/validate' % self._setup_endpoint
        self._base_system_url = '%s/system/version.json' % self._home_endpoint
        self._base_webauth_url = '%s/refreshWebAuth' % self._push_endpoint

        self.session = requests.Session()
        self.session.verify = False
        self.session.headers.update({
            'host': 'setup.icloud.com',
            'origin': self._home_endpoint,
            'referer': '%s/' % self._home_endpoint,
            'User-Agent': 'Opera/9.52 (X11; Linux i686; U; en)'
        })

        self.params = {}

        self.authenticate()

    def refresh_validate(self):
        """
        Queries the /validate endpoint and fetches two key values we need:
        1. "dsInfo" is a nested object which contains the "dsid" integer.
            This object doesn't exist until *after* the login has taken place,
            the first request will compain about a X-APPLE-WEBAUTH-TOKEN cookie
        2. "instance" is an int which is used to build the "id" query string.
            This is, pseudo: sha1(email + "instance") to uppercase.
        """
        req = self.session.get(self._base_validate_url, params=self.params)
        resp = req.json()
        if 'dsInfo' in resp:
            dsid = resp['dsInfo']['dsid']
            self.params.update({'dsid': dsid})
        instance = resp.get(
            'instance',
            uuid.uuid4().hex.encode('utf-8')
        )
        sha = hashlib.sha1(
            self.user.get('apple_id').encode('utf-8') + instance
        )
        self.params.update({'id': sha.hexdigest().upper()})

    def authenticate(self):
        """
        Handles the full authentication steps, validating,
        authenticating and then validating again.
        """
        self.refresh_validate()

        data = dict(self.user)
        data.update({'id': self.params['id'], 'extended_login': False})
        req = self.session.post(
            self._base_login_url,
            params=self.params,
            data=json.dumps(data)
        )

        if not req.ok:
            msg = 'Invalid email/password combination.'
            raise PyiCloudFailedLoginException(msg)

        self.refresh_validate()

        self.discovery = req.json()
        self.webservices = self.discovery['webservices']

    @property
    def devices(self):
        """ Return all devices."""
        service_root = self.webservices['findme']['url']
        return FindMyiPhoneServiceManager(
            service_root,
            self.session,
            self.params
        )

    @property
    def iphone(self):
        return self.devices[0]

    @property
    def files(self):
        if not hasattr(self, '_files'):
            service_root = self.webservices['ubiquity']['url']
            self._files = UbiquityService(
                service_root,
                self.session,
                self.params
            )
        return self._files

    @property
    def calendar(self):
        service_root = self.webservices['calendar']['url']
        return CalendarService(service_root, self.session, self.params)

    def __unicode__(self):
        return 'iCloud API: %s' % self.user.get('apple_id')

    def __str__(self):
        as_unicode = self.__unicode__()
        if sys.version_info[0] >= 3:
            return as_unicode
        else:
            return as_unicode.encode('ascii', 'ignore')

    def __repr__(self):
        return '<%s>' % str(self)

########NEW FILE########
__FILENAME__ = cmdline
#! /usr/bin/env python
# -*- coding: utf-8 -*-
"""
A Command Line Wrapper to allow easy use of pyicloud for
command line scripts, and related.
"""
import argparse
import pickle

import pyicloud


DEVICE_ERROR = (
    "Please use the --device switch to indicate which device to use."
)


def create_pickled_data(idevice, filename):
    """This helper will output the idevice to a pickled file named
    after the passed filename.

    This allows the data to be used without resorting to screen / pipe
    scrapping.  """
    data = {}
    for x in idevice.content:
        data[x] = idevice.content[x]
    location = filename
    pickle_file = open(location, 'wb')
    pickle.dump(data, pickle_file, protocol=pickle.HIGHEST_PROTOCOL)
    pickle_file.close()


def main():
    """		Main Function 	"""
    parser = argparse.ArgumentParser(
        description="Find My iPhone CommandLine Tool")

    parser.add_argument(
        "--username",
        action="store",
        dest="username",
        default="",
        help="Apple ID to Use"
    )
    parser.add_argument(
        "--password",
        action="store",
        dest="password",
        default="",
        help="Apple ID Password to Use",
    )
    parser.add_argument(
        "--list",
        action="store_true",
        dest="list",
        default=False,
        help="Short Listings for Device(s) associated with account",
    )
    parser.add_argument(
        "--llist",
        action="store_true",
        dest="longlist",
        default=False,
        help="Detailed Listings for Device(s) associated with account",
    )
    parser.add_argument(
        "--locate",
        action="store_true",
        dest="locate",
        default=False,
        help="Retrieve Location for the iDevice (non-exclusive).",
    )

    #   Restrict actions to a specific devices UID / DID
    parser.add_argument(
        "--device",
        action="store",
        dest="device_id",
        default=False,
        help="Only effect this device",
    )

    #   Trigger Sound Alert
    parser.add_argument(
        "--sound",
        action="store_true",
        dest="sound",
        default=False,
        help="Play a sound on the device",
    )

    #   Trigger Message w/Sound Alert
    parser.add_argument(
        "--message",
        action="store",
        dest="message",
        default=False,
        help="Optional Text Message to display with a sound",
    )

    #   Trigger Message (without Sound) Alert
    parser.add_argument(
        "--silentmessage",
        action="store",
        dest="silentmessage",
        default=False,
        help="Optional Text Message to display with no sounds",
    )

    #   Lost Mode
    parser.add_argument(
        "--lostmode",
        action="store_true",
        dest="lostmode",
        default=False,
        help="Enable Lost mode for the device",
    )
    parser.add_argument(
        "--lostphone",
        action="store",
        dest="lost_phone",
        default=False,
        help="Phone Number allowed to call when lost mode is enabled",
    )
    parser.add_argument(
        "--lostpassword",
        action="store",
        dest="lost_password",
        default=False,
        help="Forcibly active this passcode on the idevice",
    )
    parser.add_argument(
        "--lostmessage",
        action="store",
        dest="lost_message",
        default="",
        help="Forcibly display this message when activating lost mode.",
    )

    #   Output device data to an pickle file
    parser.add_argument(
        "--outputfile",
        action="store_true",
        dest="output_to_file",
        default="",
        help="Save device data to a file in the current directory.",
    )

    command_line = parser.parse_args()
    if not command_line.username or not command_line.password:
        parser.error('No username or password supplied')

    from pyicloud import PyiCloudService
    try:
        api = PyiCloudService(
            command_line.username.strip(),
            command_line.password.strip()
        )
    except pyicloud.exceptions.PyiCloudFailedLoginException:
        raise RuntimeError('Bad username or password')

    for dev in api.devices:
        if (
            not command_line.device_id
            or (
                command_line.device_id.strip().lower()
                == dev.content["id"].strip().lower()
            )
        ):
            #   List device(s)
            if command_line.locate:
                dev.location()

            if command_line.output_to_file:
                create_pickled_data(
                    dev,
                    filename=(
                        dev.content["name"].strip().lower() + ".fmip_snapshot"
                    )
                )

            contents = dev.content
            if command_line.longlist:
                print "-"*30
                print contents["name"]
                for x in contents:
                    print "%20s - %s" % (x, contents[x])
            elif command_line.list:
#                print "\n"
                print "-"*30
                print "Name - %s" % contents["name"]
                print "Display Name  - %s" % contents["deviceDisplayName"]
                print "Location      - %s" % contents["location"]
                print "Battery Level - %s" % contents["batteryLevel"]
                print "Battery Status- %s" % contents["batteryStatus"]
                print "Device Class  - %s" % contents["deviceClass"]
                print "Device Model  - %s" % contents["deviceModel"]

            #   Play a Sound on a device
            if command_line.sound:
                if command_line.device_id:
                    dev.play_sound()
                else:
                    raise RuntimeError(
                        "\n\n\t\t%s %s\n\n" % (
                            "Sounds can only be played on a singular device.",
                            DEVICE_ERROR
                        )
                    )

            #   Display a Message on the device
            if command_line.message:
                if command_line.device_id:
                    dev.display_message(
                        subject='A Message',
                        message=command_line.message,
                        sounds=True
                    )
                else:
                    raise RuntimeError(
                        "%s %s" % (
                            "Messages can only be played "
                            "on a singular device.",
                            DEVICE_ERROR
                        )
                    )

            #   Display a Silent Message on the device
            if command_line.silentmessage:
                if command_line.device_id:
                    dev.display_message(
                        subject='A Silent Message',
                        message=command_line.silentmessage,
                        sounds=False
                    )
                else:
                    raise RuntimeError(
                        "%s %s" % (
                            "Silent Messages can only be played "
                            "on a singular device.",
                            DEVICE_ERROR
                        )
                    )

            #   Enable Lost mode
            if command_line.lostmode:
                if command_line.device_id:
                    dev.lost_device(
                        number=command_line.lost_phone.strip(),
                        text=command_line.lost_message.strip(),
                        newpasscode=command_line.lost_password.strip()
                    )
                else:
                    raise RuntimeError(
                        "%s %s" % (
                            "Lost Mode can only be activated "
                            "on a singular device.",
                            DEVICE_ERROR
                        )
                    )

if __name__ == '__main__':
    main()

########NEW FILE########
__FILENAME__ = exceptions


class PyiCloudNoDevicesException(Exception):
    pass


class PyiCloudFailedLoginException(Exception):
    pass

########NEW FILE########
__FILENAME__ = calendar
from __future__ import absolute_import
import os
from datetime import datetime
from calendar import monthrange


class CalendarService(object):
    """
    The 'Calendar' iCloud service, connects to iCloud and returns events.
    """
    def __init__(self, service_root, session, params):
        self.session = session
        self.params = params
        self._service_root = service_root
        self._calendar_endpoint = '%s/ca' % self._service_root
        self._calendar_refresh_url = '%s/events' % self._calendar_endpoint
        self._calendar_event_detail_url = '%s/eventdetail' % self._calendar_endpoint

    def get_system_tz(self):
        """
        Retrieves the system's timezone.
        From: http://stackoverflow.com/a/7841417
        """
        return '/'.join(os.readlink('/etc/localtime').split('/')[-2:])

    def get_event_detail(self, pguid, guid):
        """
        Fetches a single event's details by specifying a pguid
        (a calendar) and a guid (an event's ID).
        """
        host = self._service_root.split('//')[1].split(':')[0]
        self.session.headers.update({'host': host})
        params = dict(self.params)
        params.update({'lang': 'en-us', 'usertz': self.get_system_tz()})
        url = '%s/%s/%s' % (self._calendar_event_detail_url, pguid, guid)
        req = self.session.get(url, params=params)
        self.response = req.json()
        return self.response['Event'][0]

    def refresh_client(self, from_dt=None, to_dt=None):
        """
        Refreshes the CalendarService endpoint, ensuring that the
        event data is up-to-date. If no 'from_dt' or 'to_dt' datetimes
        have been given, the range becomes this month.
        """
        today = datetime.today()
        first_day, last_day = monthrange(today.year, today.month)
        if not from_dt:
            from_dt = datetime(today.year, today.month, first_day)
        if not to_dt:
            to_dt = datetime(today.year, today.month, last_day)
        host = self._service_root.split('//')[1].split(':')[0]
        self.session.headers.update({'host': host})
        params = dict(self.params)
        params.update({
            'lang': 'en-us',
            'usertz': self.get_system_tz(),
            'startDate': from_dt.strftime('%Y-%m-%d'),
            'endDate': to_dt.strftime('%Y-%m-%d')
        })
        req = self.session.get(self._calendar_refresh_url, params=params)
        self.response = req.json()

    def events(self, from_dt=None, to_dt=None):
        """
        Retrieves events for a given date range, by default, this month.
        """
        self.refresh_client(from_dt, to_dt)
        return self.response['Event']

########NEW FILE########
__FILENAME__ = findmyiphone
import json
import sys

import six

from pyicloud.exceptions import PyiCloudNoDevicesException


class FindMyiPhoneServiceManager(object):
    """ The 'Find my iPhone' iCloud service

    This connects to iCloud and return phone data including the near-realtime
    latitude and longitude.

    """

    def __init__(self, service_root, session, params):
        self.session = session
        self.params = params
        self._service_root = service_root
        self._fmip_endpoint = '%s/fmipservice/client/web' % self._service_root
        self._fmip_refresh_url = '%s/refreshClient' % self._fmip_endpoint
        self._fmip_sound_url = '%s/playSound' % self._fmip_endpoint
        self._fmip_message_url = '%s/sendMessage' % self._fmip_endpoint
        self._fmip_lost_url = '%s/lostDevice' % self._fmip_endpoint

        self._devices = {}
        self.refresh_client()

    def refresh_client(self):
        """ Refreshes the FindMyiPhoneService endpoint,

        This ensures that the location data is up-to-date.

        """
        host = self._service_root.split('//')[1].split(':')[0]
        self.session.headers.update({'host': host})
        req = self.session.post(self._fmip_refresh_url, params=self.params)
        self.response = req.json()

        for device_info in self.response['content']:
            device_id = device_info['id']
            if not device_id in self._devices:
                self._devices[device_id] = AppleDevice(
                    device_info,
                    self.session,
                    self.params,
                    manager=self,
                    sound_url=self._fmip_sound_url,
                    lost_url=self._fmip_lost_url,
                    message_url=self._fmip_message_url,
                )
            else:
                self._devices[device_id].update(device_info)

        if not self._devices:
            raise PyiCloudNoDevicesException()

    def __getitem__(self, key):
        if isinstance(key, int):
            if six.PY3:
                key = list(self.keys())[key]
            else:
                key = self.keys()[key]
        return self._devices[key]

    def __getattr__(self, attr):
        return getattr(self._devices, attr)

    def __unicode__(self):
        return six.text_type(self._devices)

    def __str__(self):
        as_unicode = self.__unicode__()
        if sys.version_info[0] >= 3:
            return as_unicode
        else:
            return as_unicode.encode('ascii', 'ignore')

    def __repr__(self):
        return six.text_type(self)


class AppleDevice(object):
    def __init__(
        self, content, session, params, manager,
        sound_url=None, lost_url=None, message_url=None
    ):
        self.content = content
        self.manager = manager
        self.session = session
        self.params = params

        self.sound_url = sound_url
        self.lost_url = lost_url
        self.message_url = message_url

    def update(self, data):
        self.content = data

    def location(self):
        self.manager.refresh_client()
        return self.content['location']

    def status(self, additional=[]):
        """ Returns status information for device.

        This returns only a subset of possible properties.
        """
        self.manager.refresh_client()
        fields = ['batteryLevel', 'deviceDisplayName', 'deviceStatus', 'name']
        fields += additional
        properties = {}
        for field in fields:
            properties[field] = self.content.get(field)
        return properties

    def play_sound(self, subject='Find My iPhone Alert'):
        """ Send a request to the device to play a sound.

        It's possible to pass a custom message by changing the `subject`.
        """
        data = json.dumps({'device': self.content['id'], 'subject': subject})
        self.session.post(
            self.sound_url,
            params=self.params,
            data=data
        )

    def display_message(
        self, subject='Find My iPhone Alert', message="This is a note",
        sounds=False
    ):
        """ Send a request to the device to play a sound.

        It's possible to pass a custom message by changing the `subject`.
        """
        data = json.dumps(
            {
                'device': self.content['id'],
                'subject': subject,
                'sound': sounds,
                'userText': True,
                'text': message
            }
        )
        self.session.post(
            self.message_url,
            params=self.params,
            data=data
        )

    def lost_device(
        self, number,
        text='This iPhone has been lost. Please call me.',
        newpasscode=""
    ):
        """ Send a request to the device to trigger 'lost mode'.

        The device will show the message in `text`, and if a number has
        been passed, then the person holding the device can call
        the number without entering the passcode.
        """
        data = json.dumps({
            'text': text,
            'userText': True,
            'ownerNbr': number,
            'lostModeEnabled': True,
            'trackingEnabled': True,
            'device': self.content['id'],
            'passcode': newpasscode
        })
        self.session.post(
            self.lost_url,
            params=self.params,
            data=data
        )

    @property
    def data(self):
        return self.content

    def __getitem__(self, key):
        return self.content[key]

    def __getattr__(self, attr):
        return getattr(self.content, attr)

    def __unicode__(self):
        display_name = self['deviceDisplayName']
        name = self['name']
        return '%s: %s' % (
            display_name,
            name,
        )

    def __str__(self):
        as_unicode = self.__unicode__()
        if sys.version_info[0] >= 3:
            return as_unicode
        else:
            return as_unicode.encode('ascii', 'ignore')

    def __repr__(self):
        return '<AppleDevice(%s)>' % str(self)

########NEW FILE########
__FILENAME__ = ubiquity
from datetime import datetime
import sys


class UbiquityService(object):
    """ The 'Ubiquity' iCloud service."""

    def __init__(self, service_root, session, params):
        self.session = session
        self.params = params
        self._root = None

        self._service_root = service_root
        self._node_url = '/ws/%s/%s/%s'

        host = self._service_root.split('//')[1].split(':')[0]
        self.session.headers.update({'host': host})

    def get_node_url(self, id, variant='item'):
        return self._service_root + self._node_url % (
            self.params['dsid'],
            variant,
            id
        )

    def get_node(self, id):
        request = self.session.get(self.get_node_url(id))
        return UbiquityNode(self, request.json())

    def get_children(self, id):
        request = self.session.get(
            self.get_node_url(id, 'parent')
        )
        items = request.json()['item_list']
        return [UbiquityNode(self, item) for item in items]

    def get_file(self, id, **kwargs):
        request = self.session.get(
            self.get_node_url(id, 'file'),
            **kwargs
        )
        return request

    @property
    def root(self):
        if not self._root:
            self._root = self.get_node(0)
        return self._root

    def __getattr__(self, attr):
        return getattr(self.root, attr)

    def __getitem__(self, key):
        return self.root[key]


class UbiquityNode(object):
    def __init__(self, conn, data):
        self.data = data
        self.connection = conn

    @property
    def item_id(self):
        return self.data.get('item_id')

    @property
    def name(self):
        return self.data.get('name')

    @property
    def type(self):
        return self.data.get('type')

    def get_children(self):
        if not hasattr(self, '_children'):
            self._children = self.connection.get_children(self.item_id)
        return self._children

    @property
    def size(self):
        try:
            return int(self.data.get('size'))
        except ValueError:
            return None

    @property
    def modified(self):
        return datetime.strptime(
            self.data.get('modified'),
            '%Y-%m-%dT%H:%M:%SZ'
        )

    def dir(self):
        return [child.name for child in self.get_children()]

    def open(self, **kwargs):
        return self.connection.get_file(self.item_id, **kwargs)

    def get(self, name):
        return [
            child for child in self.get_children() if child.name == name
        ][0]

    def __getitem__(self, key):
        try:
            return self.get(key)
        except IndexError:
            raise KeyError('No child named %s exists' % key)

    def __unicode__(self):
        return self.name

    def __str__(self):
        as_unicode = self.__unicode__()
        if sys.version_info[0] >= 3:
            return as_unicode
        else:
            return as_unicode.encode('ascii', 'ignore')

    def __repr__(self):
        return "<%s: '%s'>" % (
            self.type.capitalize(),
            self
        )

########NEW FILE########
