__FILENAME__ = parsers
import sys
from collections import namedtuple

from ua_parser import user_agent_parser


PY2 = sys.version_info[0] == 2
PY3 = sys.version_info[0] == 3

if PY3:
    string_types = str
else:
    string_types = basestring


MOBILE_DEVICE_FAMILIES = (
    'iPhone',
    'iPod',
    'Generic Smartphone',
    'Generic Feature Phone',
)

MOBILE_OS_FAMILIES = (
    'Windows Phone',
    'Windows Phone OS', # Earlier versions of ua-parser returns Windows Phone OS
    'Symbian OS',
)

TABLET_DEVICE_FAMILIES = (
    'iPad',
    'BlackBerry Playbook',
    'Blackberry Playbook', # Earlier versions of ua-parser returns "Blackberry" instead of "BlackBerry"
    'Kindle',
    'Kindle Fire',
)

TOUCH_CAPABLE_OS_FAMILIES = (
    'iOS',
    'Android',
    'Windows Phone',
    'Windows Phone OS',
    'Windows RT',
)

TOUCH_CAPABLE_DEVICE_FAMILIES = (
    'BlackBerry Playbook',
    'Blackberry Playbook',
    'Kindle Fire',
)


def parse_version(major=None, minor=None, patch=None, patch_minor=None):
    # Returns version number tuple, attributes will be integer if they're numbers
    if major is not None and isinstance(major, string_types):
        major = int(major) if major.isdigit() else major
    if minor is not None and isinstance(minor, string_types):
        minor = int(minor) if minor.isdigit() else minor
    if patch is not None and isinstance(patch, string_types):
        patch = int(patch) if patch.isdigit() else patch
    if patch_minor is not None and isinstance(patch_minor, string_types):
        patch_minor = int(patch_minor) if patch_minor.isdigit() else patch_minor
    if patch_minor:
        return (major, minor, patch, patch_minor)
    elif patch:
        return (major, minor, patch)
    elif minor:
        return (major, minor)
    elif major:
        return (major,)
    else:
        return tuple()


Browser = namedtuple('Browser', ['family', 'version', 'version_string'])


def parse_browser(family, major=None, minor=None, patch=None, patch_minor=None):
    # Returns a browser object
    version = parse_version(major, minor, patch)
    version_string = '.'.join([str(v) for v in version])
    return Browser(family, version, version_string)


OperatingSystem = namedtuple('OperatingSystem', ['family', 'version', 'version_string'])


def parse_operating_system(family, major=None, minor=None, patch=None, patch_minor=None):
    version = parse_version(major, minor, patch)
    version_string = '.'.join([str(v) for v in version])
    return OperatingSystem(family, version, version_string)


Device = namedtuple('Device', ['family'])


def parse_device(family):
    return Device(family)


class UserAgent(object):

    def __init__(self, user_agent_string):
        ua_dict = user_agent_parser.Parse(user_agent_string)
        self.ua_string = user_agent_string
        self.os = parse_operating_system(**ua_dict['os'])
        self.browser = parse_browser(**ua_dict['user_agent'])
        self.device = parse_device(**ua_dict['device'])

    
    def _is_android_tablet(self):
        # Newer Android tablets don't have "Mobile" in their user agent string,
        # older ones like Galaxy Tab still have "Mobile" though they're not
        if ('Mobile Safari' not in self.ua_string and
                self.browser.family != "Firefox Mobile"):
            return True
        if 'SCH-' in self.ua_string:
            return True
        return False

    def _is_blackberry_touch_capable_device(self):
        # A helper to determine whether a BB phone has touch capabilities
        # Blackberry Bold Touch series begins with 99XX
        if 'Blackberry 99' in self.device.family:
            return True
        if 'Blackberry 95' in self.device.family: # BB Storm devices
            return True
        if 'Blackberry 95' in self.device.family: # BB Torch devices
            return True
        return False

    @property
    def is_tablet(self):
        if self.device.family in TABLET_DEVICE_FAMILIES:
            return True
        if (self.os.family == 'Android' and self._is_android_tablet()):
            return True
        if self.os.family == 'Windows RT':
            return True
        return False

    @property
    def is_mobile(self):
        # First check for mobile device families
        if self.device.family in MOBILE_DEVICE_FAMILIES:
            return True
        # Device is considered Mobile OS is Android and not tablet
        # This is not fool proof but would have to suffice for now
        if self.os.family == 'Android' and not self.is_tablet:
            return True
        if self.os.family == 'BlackBerry OS' and self.device.family != 'Blackberry Playbook':
            return True
        if self.os.family in MOBILE_OS_FAMILIES:
            return True
        # TODO: remove after https://github.com/tobie/ua-parser/issues/126 is closed
        if 'J2ME' in self.ua_string or 'MIDP' in self.ua_string:
            return True
        return False

    @property
    def is_touch_capable(self):
        # TODO: detect touch capable Nokia devices
        if self.os.family in TOUCH_CAPABLE_OS_FAMILIES:
            return True
        if self.device.family in TOUCH_CAPABLE_DEVICE_FAMILIES:
            return True
        if self.os.family == 'Windows 8' and 'Touch' in self.ua_string:
            return True
        if 'BlackBerry' in self.os.family and self._is_blackberry_touch_capable_device():
            return True
        return False

    @property
    def is_pc(self):
        # Returns True for "PC" devices (Windows, Mac and Linux)
        if 'Windows NT' in self.ua_string:
            return True
        # TODO: remove after https://github.com/tobie/ua-parser/issues/127 is closed
        if self.os.family == 'Mac OS X' and 'Silk' not in self.ua_string:
            return True
        if 'Linux' in self.ua_string and 'X11' in self.ua_string:
            return True
        return False

    @property
    def is_bot(self):
        return True if self.device.family == 'Spider' else False


def parse(user_agent_string):
    return UserAgent(user_agent_string)

########NEW FILE########
__FILENAME__ = tests
import unittest

from ua_parser import user_agent_parser
from .parsers import parse, UserAgent


iphone_ua_string = 'Mozilla/5.0 (iPhone; CPU iPhone OS 5_1 like Mac OS X) AppleWebKit/534.46 (KHTML, like Gecko) Version/5.1 Mobile/9B179 Safari/7534.48.3'
ipad_ua_string = 'Mozilla/5.0(iPad; U; CPU iPhone OS 3_2 like Mac OS X; en-us) AppleWebKit/531.21.10 (KHTML, like Gecko) Version/4.0.4 Mobile/7B314 Safari/531.21.10'
galaxy_tab_ua_string = 'Mozilla/5.0 (Linux; U; Android 2.2; en-us; SCH-I800 Build/FROYO) AppleWebKit/533.1 (KHTML, like Gecko) Version/4.0 Mobile Safari/533.1'
galaxy_s3_ua_string = 'Mozilla/5.0 (Linux; U; Android 4.0.4; en-gb; GT-I9300 Build/IMM76D) AppleWebKit/534.30 (KHTML, like Gecko) Version/4.0 Mobile Safari/534.30'
kindle_fire_ua_string = 'Mozilla/5.0 (Macintosh; U; Intel Mac OS X 10_6_3; en-us; Silk/1.1.0-80) AppleWebKit/533.16 (KHTML, like Gecko) Version/5.0 Safari/533.16 Silk-Accelerated=true'
playbook_ua_string = 'Mozilla/5.0 (PlayBook; U; RIM Tablet OS 2.0.1; en-US) AppleWebKit/535.8+ (KHTML, like Gecko) Version/7.2.0.1 Safari/535.8+'
nexus_7_ua_string = 'Mozilla/5.0 (Linux; Android 4.1.1; Nexus 7 Build/JRO03D) AppleWebKit/535.19 (KHTML, like Gecko) Chrome/18.0.1025.166  Safari/535.19'
windows_phone_ua_string = 'Mozilla/5.0 (compatible; MSIE 9.0; Windows Phone OS 7.5; Trident/5.0; IEMobile/9.0; SAMSUNG; SGH-i917)'
blackberry_torch_ua_string = 'Mozilla/5.0 (BlackBerry; U; BlackBerry 9800; zh-TW) AppleWebKit/534.8+ (KHTML, like Gecko) Version/6.0.0.448 Mobile Safari/534.8+'
blackberry_bold_ua_string = 'BlackBerry9700/5.0.0.862 Profile/MIDP-2.1 Configuration/CLDC-1.1 VendorID/331 UNTRUSTED/1.0 3gpp-gba'
blackberry_bold_touch_ua_string = 'Mozilla/5.0 (BlackBerry; U; BlackBerry 9930; en-US) AppleWebKit/534.11+ (KHTML, like Gecko) Version/7.0.0.241 Mobile Safari/534.11+'
windows_rt_ua_string = 'Mozilla/5.0 (compatible; MSIE 10.0; Windows NT 6.2; ARM; Trident/6.0)'
j2me_opera_ua_string = 'Opera/9.80 (J2ME/MIDP; Opera Mini/9.80 (J2ME/22.478; U; en) Presto/2.5.25 Version/10.54'
ie_ua_string = 'Mozilla/5.0 (compatible; MSIE 10.0; Windows NT 6.2; Trident/6.0)'
ie_touch_ua_string = 'Mozilla/5.0 (compatible; MSIE 10.0; Windows NT 6.2; Trident/6.0; Touch)'
mac_safari_ua_string = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_6_8) AppleWebKit/537.13+ (KHTML, like Gecko) Version/5.1.7 Safari/534.57.2'
windows_ie_ua_string = 'Mozilla/5.0 (compatible; MSIE 9.0; Windows NT 6.1; Trident/5.0)'
ubuntu_firefox_ua_string = 'Mozilla/5.0 (X11; Ubuntu; Linux i686; rv:15.0) Gecko/20100101 Firefox/15.0.1'
google_bot_ua_string = 'Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)'
nokia_n97_ua_string = 'Mozilla/5.0 (SymbianOS/9.4; Series60/5.0 NokiaN97-1/12.0.024; Profile/MIDP-2.1 Configuration/CLDC-1.1; en-us) AppleWebKit/525 (KHTML, like Gecko) BrowserNG/7.1.12344'
android_firefox_aurora_ua_string = 'Mozilla/5.0 (Android; Mobile; rv:27.0) Gecko/27.0 Firefox/27.0'

iphone_ua = parse(iphone_ua_string)
ipad_ua = parse(ipad_ua_string)
galaxy_tab = parse(galaxy_tab_ua_string)
galaxy_s3_ua = parse(galaxy_s3_ua_string)
kindle_fire_ua = parse(kindle_fire_ua_string)
playbook_ua = parse(playbook_ua_string)
nexus_7_ua = parse(nexus_7_ua_string)
windows_phone_ua = parse(windows_phone_ua_string)
windows_rt_ua = parse(windows_rt_ua_string)
blackberry_torch_ua = parse(blackberry_torch_ua_string)
blackberry_bold_ua = parse(blackberry_bold_ua_string)
blackberry_bold_touch_ua = parse(blackberry_bold_touch_ua_string)
j2me_opera_ua = parse(j2me_opera_ua_string)
ie_ua = parse(ie_ua_string)
ie_touch_ua = parse(ie_touch_ua_string)
mac_safari_ua = parse(mac_safari_ua_string)
windows_ie_ua = parse(windows_ie_ua_string)
ubuntu_firefox_ua = parse(ubuntu_firefox_ua_string)
google_bot_ua = parse(google_bot_ua_string)
nokia_n97_ua = parse(nokia_n97_ua_string)
android_firefox_aurora_ua = parse(android_firefox_aurora_ua_string)


class UserAgentsTest(unittest.TestCase):

    def test_user_agent_object_assignments(self):
        ua_dict = user_agent_parser.Parse(iphone_ua_string)

        # Ensure browser attributes are assigned correctly
        self.assertEqual(iphone_ua.browser.family,
                         ua_dict['user_agent']['family'])
        self.assertEqual(
            iphone_ua.browser.version,
            (int(ua_dict['user_agent']['major']), int(ua_dict['user_agent']['minor']))
        )
        
        # Ensure os attributes are assigned correctly
        self.assertEqual(iphone_ua.os.family, ua_dict['os']['family'])
        self.assertEqual(
            iphone_ua.os.version,
            (int(ua_dict['os']['major']), int(ua_dict['os']['minor']))
        )

        # Ensure device attributes are assigned correctly
        self.assertEqual(iphone_ua.device.family,
                         ua_dict['device']['family'])

    def test_is_tablet_property(self):
        self.assertFalse(iphone_ua.is_tablet)
        self.assertFalse(galaxy_s3_ua.is_tablet)
        self.assertFalse(blackberry_torch_ua.is_tablet)
        self.assertFalse(blackberry_bold_ua.is_tablet)
        self.assertFalse(windows_phone_ua.is_tablet)
        self.assertFalse(ie_ua.is_tablet)
        self.assertFalse(ie_touch_ua.is_tablet)
        self.assertFalse(mac_safari_ua.is_tablet)
        self.assertFalse(windows_ie_ua.is_tablet)
        self.assertFalse(ubuntu_firefox_ua.is_tablet)
        self.assertFalse(j2me_opera_ua.is_tablet)
        self.assertFalse(google_bot_ua.is_tablet)
        self.assertFalse(nokia_n97_ua.is_tablet)
        self.assertTrue(windows_rt_ua.is_tablet)
        self.assertTrue(ipad_ua.is_tablet)
        self.assertTrue(playbook_ua.is_tablet)
        self.assertTrue(kindle_fire_ua.is_tablet)
        self.assertTrue(nexus_7_ua.is_tablet)
        self.assertFalse(android_firefox_aurora_ua.is_tablet)

    def test_is_mobile_property(self):
        self.assertTrue(iphone_ua.is_mobile)
        self.assertTrue(galaxy_s3_ua.is_mobile)
        self.assertTrue(blackberry_torch_ua.is_mobile)
        self.assertTrue(blackberry_bold_ua.is_mobile)
        self.assertTrue(windows_phone_ua.is_mobile)
        self.assertTrue(j2me_opera_ua.is_mobile)
        self.assertTrue(nokia_n97_ua.is_mobile)
        self.assertFalse(windows_rt_ua.is_mobile)
        self.assertFalse(ipad_ua.is_mobile)
        self.assertFalse(playbook_ua.is_mobile)
        self.assertFalse(kindle_fire_ua.is_mobile)
        self.assertFalse(nexus_7_ua.is_mobile)
        self.assertFalse(ie_ua.is_mobile)
        self.assertFalse(ie_touch_ua.is_mobile)
        self.assertFalse(mac_safari_ua.is_mobile)
        self.assertFalse(windows_ie_ua.is_mobile)
        self.assertFalse(ubuntu_firefox_ua.is_mobile)
        self.assertFalse(google_bot_ua.is_mobile)
        self.assertTrue(android_firefox_aurora_ua.is_mobile)

    def test_is_touch_property(self):
        self.assertTrue(iphone_ua.is_touch_capable)
        self.assertTrue(galaxy_s3_ua.is_touch_capable)
        self.assertTrue(ipad_ua.is_touch_capable)
        self.assertTrue(playbook_ua.is_touch_capable)
        self.assertTrue(kindle_fire_ua.is_touch_capable)
        self.assertTrue(nexus_7_ua.is_touch_capable)
        self.assertTrue(windows_phone_ua.is_touch_capable)
        self.assertTrue(ie_touch_ua.is_touch_capable)
        self.assertTrue(blackberry_bold_touch_ua.is_mobile)
        self.assertTrue(blackberry_torch_ua.is_mobile)
        self.assertFalse(j2me_opera_ua.is_touch_capable)
        self.assertFalse(ie_ua.is_touch_capable)
        self.assertFalse(blackberry_bold_ua.is_touch_capable)
        self.assertFalse(mac_safari_ua.is_touch_capable)
        self.assertFalse(windows_ie_ua.is_touch_capable)
        self.assertFalse(ubuntu_firefox_ua.is_touch_capable)
        self.assertFalse(google_bot_ua.is_touch_capable)
        self.assertFalse(nokia_n97_ua.is_touch_capable)
        self.assertTrue(android_firefox_aurora_ua.is_touch_capable)

    def test_is_pc(self):
        self.assertFalse(iphone_ua.is_pc)
        self.assertFalse(galaxy_s3_ua.is_pc)
        self.assertFalse(ipad_ua.is_pc)
        self.assertFalse(playbook_ua.is_pc)
        self.assertFalse(kindle_fire_ua.is_pc)
        self.assertFalse(nexus_7_ua.is_pc)
        self.assertFalse(windows_phone_ua.is_pc)
        self.assertFalse(blackberry_bold_touch_ua.is_pc)
        self.assertFalse(blackberry_torch_ua.is_pc)        
        self.assertFalse(blackberry_bold_ua.is_pc)
        self.assertFalse(j2me_opera_ua.is_pc)
        self.assertFalse(google_bot_ua.is_pc)
        self.assertFalse(nokia_n97_ua.is_pc)
        self.assertTrue(mac_safari_ua.is_pc)
        self.assertTrue(windows_ie_ua.is_pc)
        self.assertTrue(ubuntu_firefox_ua.is_pc)
        self.assertTrue(ie_touch_ua.is_pc)
        self.assertTrue(ie_ua.is_pc)
        self.assertFalse(android_firefox_aurora_ua.is_pc)

    def test_is_bot(self):
        self.assertTrue(google_bot_ua.is_bot)
        self.assertFalse(iphone_ua.is_bot)
        self.assertFalse(galaxy_s3_ua.is_bot)
        self.assertFalse(ipad_ua.is_bot)
        self.assertFalse(playbook_ua.is_bot)
        self.assertFalse(kindle_fire_ua.is_bot)
        self.assertFalse(nexus_7_ua.is_bot)
        self.assertFalse(windows_phone_ua.is_bot)
        self.assertFalse(blackberry_bold_touch_ua.is_bot)
        self.assertFalse(blackberry_torch_ua.is_bot)        
        self.assertFalse(blackberry_bold_ua.is_bot)
        self.assertFalse(j2me_opera_ua.is_bot)        
        self.assertFalse(mac_safari_ua.is_bot)
        self.assertFalse(windows_ie_ua.is_bot)
        self.assertFalse(ubuntu_firefox_ua.is_bot)
        self.assertFalse(ie_touch_ua.is_bot)
        self.assertFalse(ie_ua.is_bot)
        self.assertFalse(nokia_n97_ua.is_bot)
        self.assertFalse(android_firefox_aurora_ua.is_bot)

########NEW FILE########
