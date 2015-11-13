__FILENAME__ = release
# Copyright (c) 2013 Yubico AB
# All rights reserved.
#
#   Redistribution and use in source and binary forms, with or
#   without modification, are permitted provided that the following
#   conditions are met:
#
#    1. Redistributions of source code must retain the above copyright
#       notice, this list of conditions and the following disclaimer.
#    2. Redistributions in binary form must reproduce the above
#       copyright notice, this list of conditions and the following
#       disclaimer in the documentation and/or other materials provided
#       with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS
# FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE
# COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT,
# INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING,
# BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN
# ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

from distutils import log
from distutils.core import Command
from distutils.errors import DistutilsSetupError
import os
import re
from datetime import date


class release(Command):
    description = "create and release a new version"
    user_options = [
        ('keyid', None, "GPG key to sign with"),
        ('skip-tests', None, "skip running the tests"),
        ('pypi', None, "publish to pypi"),
    ]
    boolean_options = ['skip-tests', 'pypi']

    def initialize_options(self):
        self.keyid = None
        self.skip_tests = 0
        self.pypi = 0

    def finalize_options(self):
        self.cwd = os.getcwd()
        self.fullname = self.distribution.get_fullname()
        self.name = self.distribution.get_name()
        self.version = self.distribution.get_version()

    def _verify_version(self):
        with open('NEWS', 'r') as news_file:
            line = news_file.readline()
        now = date.today().strftime('%Y-%m-%d')
        if not re.search(r'Version %s \(released %s\)' % (self.version, now),
                         line):
            raise DistutilsSetupError("Incorrect date/version in NEWS!")

    def _verify_tag(self):
        if os.system('git tag | grep -q "^%s\$"' % self.fullname) == 0:
            raise DistutilsSetupError(
                "Tag '%s' already exists!" % self.fullname)

    def _sign(self):
        if os.path.isfile('dist/%s.tar.gz.asc' % self.fullname):
            # Signature exists from upload, re-use it:
            sign_opts = ['--output dist/%s.tar.gz.sig' % self.fullname,
                         '--dearmor dist/%s.tar.gz.asc' % self.fullname]
        else:
            # No signature, create it:
            sign_opts = ['--detach-sign', 'dist/%s.tar.gz' % self.fullname]
            if self.keyid:
                sign_opts.insert(1, '--default-key ' + self.keyid)
        self.execute(os.system, ('gpg ' + (' '.join(sign_opts)),))

        if os.system('gpg --verify dist/%s.tar.gz.sig' % self.fullname) != 0:
            raise DistutilsSetupError("Error verifying signature!")

    def _tag(self):
        tag_opts = ['-s', '-m ' + self.fullname, self.fullname]
        if self.keyid:
            tag_opts[0] = '-u ' + self.keyid
        self.execute(os.system, ('git tag ' + (' '.join(tag_opts)),))

    def _do_call_publish(self, cmd):
        self._published = os.system(cmd) == 0

    def _publish(self):
        web_repo = os.getenv('YUBICO_GITHUB_REPO')
        if web_repo and os.path.isdir(web_repo):
            artifacts = [
                'dist/%s.tar.gz' % self.fullname,
                'dist/%s.tar.gz.sig' % self.fullname
            ]
            cmd = '%s/publish %s %s %s' % (
                web_repo, self.name, self.version, ' '.join(artifacts))

            self.execute(self._do_call_publish, (cmd,))
            if self._published:
                self.announce("Release published! Don't forget to:", log.INFO)
                self.announce("")
                self.announce("    (cd %s && git push)" % web_repo, log.INFO)
                self.announce("")
            else:
                self.warn("There was a problem publishing the release!")
        else:
            self.warn("YUBICO_GITHUB_REPO not set or invalid!")
            self.warn("This release will not be published!")

    def run(self):
        if os.getcwd() != self.cwd:
            raise DistutilsSetupError("Must be in package root!")

        self._verify_version()
        self._verify_tag()

        self.execute(os.system, ('git2cl > ChangeLog',))

        if not self.skip_tests:
            self.run_command('check')
            # Nosetests calls sys.exit(status)
            try:
                self.run_command('nosetests')
            except SystemExit as e:
                if e.code != 0:
                    raise DistutilsSetupError("There were test failures!")

        self.run_command('sdist')

        if self.pypi:
            cmd_obj = self.distribution.get_command_obj('upload')
            cmd_obj.sign = True
            if self.keyid:
                cmd_obj.identity = self.keyid
            self.run_command('upload')

        self._sign()
        self._tag()

        self._publish()

        self.announce("Release complete! Don't forget to:", log.INFO)
        self.announce("")
        self.announce("    git push && git push --tags", log.INFO)
        self.announce("")

########NEW FILE########
__FILENAME__ = test_yubico
#!/usr/bin/env python
#
# Simple test cases for a Python version of the yubikey_crc16() function in ykcrc.c.
#

import struct
import unittest
import yubico.yubico_util as yubico_util
from yubico.yubico_util import crc16

CRC_OK_RESIDUAL=0xf0b8

class TestCRC(unittest.TestCase):

    def test_first(self):
        """ Test CRC16 trivial case """
        buffer = '\x01\x02\x03\x04'
        crc = crc16(buffer)
        self.assertEqual(crc, 0xc66e)
        return buffer,crc

    def test_second(self):
        """ Test CRC16 residual calculation """
        buffer,crc = self.test_first()
        # Append 1st complement for a "self-verifying" block -
        # from example in Yubikey low level interface
        crc_inv = 0xffff - crc
        buffer += struct.pack('<H', crc_inv)
        crc2 = crc16(buffer)
        self.assertEqual(crc2, CRC_OK_RESIDUAL)

    def test_hexdump(self):
        """ Test hexdump function, normal use """
        bytes = '\x01\x02\x03\x04\x05\x06\x07\x08'
        self.assertEqual(yubico_util.hexdump(bytes, length=4), \
                             '0000   01 02 03 04\n0004   05 06 07 08\n')

    def test_hexdump(self):
        """ Test hexdump function, with colors """
        bytes = '\x01\x02\x03\x04\x05\x06\x07\x08'
        self.assertEqual(yubico_util.hexdump(bytes, length=4, colorize=True), \
                             '0000   \x1b[0m01 02 03\x1b[0m 04\n0004   \x1b[0m05 06 07\x1b[0m 08\n')

    def test_modhex_decode(self):
        """ Test modhex decoding """
        self.assertEqual("0123456789abcdef", yubico_util.modhex_decode("cbdefghijklnrtuv"))

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_yubikey_config
#!/usr/bin/env python

import unittest
import yubico
import yubico.yubikey_config
from yubico.yubikey_usb_hid import YubiKeyConfigUSBHID
import yubico.yubico_util
import yubico.yubico_exception

class YubiKeyTests(unittest.TestCase):

    def setUp(self):
        version = (2, 2, 0,)
        capa = yubico.yubikey_usb_hid.YubiKeyUSBHIDCapabilities( \
            model = 'YubiKey', version = version, default_answer = False)
        self.Config = YubiKeyConfigUSBHID(ykver = version, capabilities = capa)

    def test_static_ticket(self):
        """ Test static ticket """

        #fixed: m:
        #uid: h:000000000000
        #key: h:e2bee9a36568a00d026a02f85e61e6fb
        #acc_code: h:000000000000
        #ticket_flags: APPEND_CR
        #config_flags: STATIC_TICKET

        expected = ['\x00\x00\x00\x00\x00\x00\x00\x80',
                    '\x00\xe2\xbe\xe9\xa3\x65\x68\x83',
                    '\xa0\x0d\x02\x6a\x02\xf8\x5e\x84',
                    '\x61\xe6\xfb\x00\x00\x00\x00\x85',
                    '\x00\x00\x00\x00\x20\x20\x00\x86',
                    '\x00\x5a\x93\x00\x00\x00\x00\x87',
                    '\x00\x01\x95\x56\x00\x00\x00\x89'
                    ]

        Config = self.Config
        Config.aes_key('h:e2bee9a36568a00d026a02f85e61e6fb')
        Config.ticket_flag('APPEND_CR', True)
        Config.config_flag('STATIC_TICKET', True)

        data = Config.to_frame(slot=1).to_feature_reports()

        print "EXPECT:\n%s\nGOT:\n%s\n" %( yubico.yubico_util.hexdump(''.join(expected)),
                                           yubico.yubico_util.hexdump(''.join(data)))

        self.assertEqual(data, expected)


    def test_static_ticket_with_access_code(self):
        """ Test static ticket with unlock code """

        #fixed: m:
        #uid: h:000000000000
        #key: h:e2bee9a36568a00d026a02f85e61e6fb
        #acc_code: h:010203040506
        #ticket_flags: APPEND_CR
        #config_flags: STATIC_TICKET

        expected = ['\x00\x00\x00\x00\x00\x00\x00\x80',
                    '\x00\xe2\xbe\xe9\xa3\x65\x68\x83',
                    '\xa0\x0d\x02\x6a\x02\xf8\x5e\x84',
                    '\x61\xe6\xfb\x01\x02\x03\x04\x85',
                    '\x05\x06\x00\x00\x20\x20\x00\x86',
                    '\x00\x0d\x39\x01\x02\x03\x04\x87',
                    '\x05\x06\x00\x00\x00\x00\x00\x88',
                    '\x00\x01\xc2\xfc\x00\x00\x00\x89',
                    ]

        Config = self.Config
        Config.aes_key('h:e2bee9a36568a00d026a02f85e61e6fb')
        Config.ticket_flag('APPEND_CR', True)
        Config.config_flag('STATIC_TICKET', True)
        Config.unlock_key('h:010203040506')

        data = Config.to_frame(slot=1).to_feature_reports()

        print "EXPECT:\n%s\nGOT:\n%s\n" %( yubico.yubico_util.hexdump(''.join(expected)),
                                           yubico.yubico_util.hexdump(''.join(data)))

        self.assertEqual(data, expected)

    def test_fixed_and_oath_hotp(self):
        """ Test OATH HOTP with a fixed prefix-string """

        #fixed: m:ftftftft
        #uid: h:000000000000
        #key: h:523d7ce7e7b6ee853517a3e3cc1985c7
        #acc_code: h:000000000000
        #ticket_flags: APPEND_CR|OATH_HOTP
        #config_flags: OATH_FIXED_MODHEX1|OATH_FIXED_MODHEX2|STATIC_TICKET

        expected = ['\x4d\x4d\x4d\x4d\x00\x00\x00\x80',
                    '\x00\x52\x3d\x7c\xe7\xe7\xb6\x83',
                    '\xee\x85\x35\x17\xa3\xe3\xcc\x84',
                    '\x19\x85\xc7\x00\x00\x00\x00\x85',
                    '\x00\x00\x04\x00\x60\x70\x00\x86',
                    '\x00\x72\xad\xaa\xbb\xcc\xdd\x87',
                    '\xee\xff\x00\x00\x00\x00\x00\x88',
                    '\x00\x03\xfe\xc4\x00\x00\x00\x89',
                    ]

        Config = self.Config
        Config.aes_key('h:523d7ce7e7b6ee853517a3e3cc1985c7')
        Config.fixed_string('m:ftftftft')
        Config.ticket_flag('APPEND_CR', True)
        Config.ticket_flag('OATH_HOTP', True)
        Config.config_flag('OATH_FIXED_MODHEX1', True)
        Config.config_flag('OATH_FIXED_MODHEX2', True)
        Config.config_flag('STATIC_TICKET', True)
        Config.unlock_key('h:aabbccddeeff')
        Config.access_key('h:000000000000')

        data = Config.to_frame(slot=2).to_feature_reports()

        print "EXPECT:\n%s\nGOT:\n%s\n" %( yubico.yubico_util.hexdump(''.join(expected)),
                                           yubico.yubico_util.hexdump(''.join(data)))

        self.assertEqual(data, expected)

    def test_challenge_response_hmac_nist(self):
        """ Test HMAC challenge response with NIST test vector """

        expected = ['\x00\x00\x00\x00\x00\x00\x00\x80',
                    '\x00\x00\x40\x41\x42\x43\x00\x82',
                    '\x00\x30\x31\x32\x33\x34\x35\x83',
                    '\x36\x37\x38\x39\x3a\x3b\x3c\x84',
                    '\x3d\x3e\x3f\x00\x00\x00\x00\x85',
                    '\x00\x00\x00\x04\x40\x26\x00\x86',
                    '\x00\x98\x41\x00\x00\x00\x00\x87',
                    '\x00\x03\x95\x56\x00\x00\x00\x89',
                    ]

        Config = self.Config
        secret = 'h:303132333435363738393a3b3c3d3e3f40414243'
        Config.mode_challenge_response(secret, type='HMAC', variable=True)
        Config.extended_flag('SERIAL_API_VISIBLE', True)

        data = Config.to_frame(slot=2).to_feature_reports()

        print "EXPECT:\n%s\nGOT:\n%s\n" %( yubico.yubico_util.hexdump(''.join(expected)),
                                           yubico.yubico_util.hexdump(''.join(data)))

        self.assertEqual(data, expected)

    def test_unknown_ticket_flag(self):
        """ Test setting unknown ticket flag  """
        Config = self.Config
        self.assertRaises(yubico.yubico_exception.InputError, Config.ticket_flag, 'YK_UNIT_TEST123', True)

    def test_unknown_ticket_flag_integer(self):
        """ Test setting unknown ticket flag as integer """
        future_flag = 0xff
        Config = self.Config
        Config.ticket_flag(future_flag, True)
        self.assertEqual(future_flag, Config.ticket_flags.to_integer())

    def test_too_long_fixed_string(self):
        """ Test too long fixed string, and set as plain string """
        Config = self.Config
        self.assertRaises(yubico.yubico_exception.InputError, Config.ticket_flag, 'YK_UNIT_TEST123', True)

    def test_default_flags(self):
        """ Test that no flags get set by default """
        Config = self.Config
        self.assertEqual(0x0, Config.ticket_flags.to_integer())
        self.assertEqual(0x0, Config.config_flags.to_integer())
        self.assertEqual(0x0, Config.extended_flags.to_integer())

    def test_oath_hotp_like_windows(self):
        """ Test plain OATH-HOTP with NIST test vector """

        expected = ['\x00\x00\x00\x00\x00\x00\x00\x80',
                    '\x00\x00\x40\x41\x42\x43\x00\x82',
                    '\x00\x30\x31\x32\x33\x34\x35\x83',
                    '\x36\x37\x38\x39\x3a\x3b\x3c\x84',
                    '\x3d\x3e\x3f\x00\x00\x00\x00\x85',
                    '\x00\x00\x00\x00\x40\x00\x00\x86',
                    '\x00\x6a\xb9\x00\x00\x00\x00\x87',
                    '\x00\x03\x95\x56\x00\x00\x00\x89',
                    ]

        Config = self.Config
        secret = 'h:303132333435363738393a3b3c3d3e3f40414243'
        Config.mode_oath_hotp(secret)

        data = Config.to_frame(slot=2).to_feature_reports()

        print "EXPECT:\n%s\nGOT:\n%s\n" %( yubico.yubico_util.hexdump(''.join(expected)),
                                           yubico.yubico_util.hexdump(''.join(data)))

        self.assertEqual(data, expected)

    def test_oath_hotp_like_windows2(self):
        """ Test OATH-HOTP with NIST test vector and token identifier """

        expected = ['\x01\x02\x03\x04\x05\x06\x00\x80',
                    '\x00\x00\x40\x41\x42\x43\x00\x82',
                    '\x00\x30\x31\x32\x33\x34\x35\x83',
                    '\x36\x37\x38\x39\x3a\x3b\x3c\x84',
                    '\x3d\x3e\x3f\x00\x00\x00\x00\x85',
                    '\x00\x00\x06\x00\x40\x42\x00\x86',
                    '\x00\x0e\xec\x00\x00\x00\x00\x87',
                    '\x00\x03\x95\x56\x00\x00\x00\x89',
                    ]

        Config = self.Config
        secret = 'h:303132333435363738393a3b3c3d3e3f40414243'
        Config.mode_oath_hotp(secret, digits=8, factor_seed='', omp=0x01, tt=0x02, mui='\x03\x04\x05\x06')
        Config.config_flag('OATH_FIXED_MODHEX2', True)

        data = Config.to_frame(slot=2).to_feature_reports()

        print "EXPECT:\n%s\nGOT:\n%s\n" %( yubico.yubico_util.hexdump(''.join(expected)),
                                           yubico.yubico_util.hexdump(''.join(data)))

        self.assertEqual(data, expected)

    def test_oath_hotp_like_windows_factory_seed(self):
        """ Test OATH-HOTP factor_seed """

        expected = ['\x01\x02\x03\x04\x05\x06\x00\x80',
                    '\x00\x00\x40\x41\x42\x43\x01\x82',
                    '\x21\x30\x31\x32\x33\x34\x35\x83',
                    '\x36\x37\x38\x39\x3a\x3b\x3c\x84',
                    '\x3d\x3e\x3f\x00\x00\x00\x00\x85',
                    '\x00\x00\x06\x00\x40\x42\x00\x86',
                    '\x00\x03\xea\x00\x00\x00\x00\x87',
                    '\x00\x03\x95\x56\x00\x00\x00\x89',
                    ]

        Config = self.Config
        secret = 'h:303132333435363738393a3b3c3d3e3f40414243'
        Config.mode_oath_hotp(secret, digits=8, factor_seed=0x2101, omp=0x01, tt=0x02, mui='\x03\x04\x05\x06')
        Config.config_flag('OATH_FIXED_MODHEX2', True)

        data = Config.to_frame(slot=2).to_feature_reports()

        print "EXPECT:\n%s\nGOT:\n%s\n" %( yubico.yubico_util.hexdump(''.join(expected)),
                                           yubico.yubico_util.hexdump(''.join(data)))

        self.assertEqual(data, expected)

    def test_fixed_length_hmac_like_windows(self):
        """ Test fixed length HMAC SHA1 """

        expected = ['\x00\x00\x00\x00\x00\x00\x00\x80',
                    '\x00\x00\x40\x41\x42\x43\x00\x82',
                    '\x00\x30\x31\x32\x33\x34\x35\x83',
                    '\x36\x37\x38\x39\x3a\x3b\x3c\x84',
                    '\x3d\x3e\x3f\x00\x00\x00\x00\x85',
                    '\x00\x00\x00\x00\x40\x22\x00\x86',
                    '\x00\xe9\x0f\x00\x00\x00\x00\x87',
                    '\x00\x03\x95\x56\x00\x00\x00\x89',
                    ]

        Config = self.Config
        secret = 'h:303132333435363738393a3b3c3d3e3f40414243'
        Config.mode_challenge_response(secret, type='HMAC', variable=False)

        data = Config.to_frame(slot=2).to_feature_reports()

        print "EXPECT:\n%s\nGOT:\n%s\n" %( yubico.yubico_util.hexdump(''.join(expected)),
                                           yubico.yubico_util.hexdump(''.join(data)))

        self.assertEqual(data, expected)

    def test_version_required_1(self):
        """ Test YubiKey 1 with v2 option """
        version = (1, 3, 0,)
        capa = yubico.yubikey_usb_hid.YubiKeyUSBHIDCapabilities( \
            model = 'YubiKey', version = version, default_answer = False)
        Config = YubiKeyConfigUSBHID(ykver = version, capabilities = capa)
        self.assertRaises(yubico.yubikey.YubiKeyVersionError, Config.config_flag, 'SHORT_TICKET', True)

    def test_version_required_2(self):
        """ Test YubiKey 2 with v2 option """

        Config = self.Config
        Config.config_flag('SHORT_TICKET', True)
        self.assertEqual((2, 0), Config.version_required())

    def test_version_required_3(self):
        """ Test YubiKey 2 with v1 option """

        Config = self.Config
        self.assertRaises(yubico.yubikey.YubiKeyVersionError, Config.config_flag, 'TICKET_FIRST', True)

    def test_version_required_4(self):
        """ Test YubiKey 2.1 with v2.2 mode """
        version = (2, 1, 0,)
        capa = yubico.yubikey_usb_hid.YubiKeyUSBHIDCapabilities( \
            model = 'YubiKey', version = version, default_answer = False)
        Config = YubiKeyConfigUSBHID(ykver = version, capabilities = capa)
        secret = 'h:303132333435363738393a3b3c3d3e3f40414243'
        self.assertRaises(yubico.yubikey.YubiKeyVersionError, Config.mode_challenge_response, secret)

    def test_version_required_5(self):
        """ Test YubiKey 2.2 with v2.2 mode """

        Config = self.Config
        secret = 'h:303132333435363738393a3b3c3d3e3f'
        Config.mode_challenge_response(secret, type='OTP')
        self.assertEqual('CHAL_RESP', Config._mode)

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_yubikey_frame
#!/usr/bin/env python

from yubico import *
from yubico.yubikey_frame import *
import yubico.yubico_exception
import unittest
import struct
import re

class YubiKeyTests(unittest.TestCase):

  def test_get_ykframe(self):
    """ Test normal use """
    buffer = YubiKeyFrame(command=0x01).to_string()

    # check number of bytes returned
    self.assertEqual(len(buffer), 70, "yubikey command buffer should always be 70 bytes")

    # check that empty payload works (64 * '\x00')
    all_zeros = '\x00' * 64

    self.assertTrue(buffer.startswith(all_zeros))


  def test_get_ykframe_feature_reports(self):
    """ Test normal use """
    res = YubiKeyFrame(command=0x32).to_feature_reports()

    self.assertEqual(res, ['\x00\x00\x00\x00\x00\x00\x00\x80',
                           '\x00\x32\x6b\x5b\x00\x00\x00\x89'
                           ])


  def test_get_ykframe_feature_reports2(self):
    """ Test one serie of non-zero bytes in the middle of the payload """
    payload = '\x00' * 38
    payload += '\x01\x02\x03'
    payload += '\x00' * 23
    res = YubiKeyFrame(command=0x32, payload=payload).to_feature_reports()

    self.assertEqual(res, ['\x00\x00\x00\x00\x00\x00\x00\x80',
                           '\x00\x00\x00\x01\x02\x03\x00\x85',
                           '\x002\x01s\x00\x00\x00\x89'])

  def test_bad_payload(self):
    """ Test that we get an exception for four bytes payload """
    self.assertRaises(yubico_exception.InputError, YubiKeyFrame, command=0x32, payload='test')

  def test_repr(self):
    """ Test string representation of object """
    # to achieve 100% test coverage ;)
    frame = YubiKeyFrame(command=0x4d)
    print "Frame is represented as %s" % frame
    re_match = re.search("YubiKeyFrame instance at .*: 77.$", str(frame))
    self.assertNotEqual(re_match, None)

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = test_yubikey_usb_hid
#!/usr/bin/env python
#
# Test cases for talking to a USB HID YubiKey.
#

import struct
import unittest
import yubico
import yubico.yubikey_usb_hid
from yubico.yubikey_usb_hid import *
import re

class TestYubiKeyUSBHID(unittest.TestCase):

    YK = None

    def setUp(self):
        """ Test connecting to the YubiKey """
        if self.YK is None:
            try:
                self.YK = YubiKeyUSBHID()
                return
            except YubiKeyUSBHIDError, err:
                self.fail("No YubiKey connected (?) : %s" % str(err))

    #@unittest.skipIf(YK is None, "No USB HID YubiKey found")
    def test_status(self):
        """ Test the simplest form of communication : a status read request """
        status = self.YK.status()
        version = self.YK.version()
        print "Version returned: %s" % version
        re_match = re.match("\d+\.\d+\.\d+$", version)
        self.assertNotEqual(re_match, None)

    #@unittest.skipIf(self.YK is None, "No USB HID YubiKey found")
    def test_challenge_response(self):
        """ Test challenge-response, assumes a NIST PUB 198 A.2 20 bytes test vector in Slot 2 (variable input) """

        secret = struct.pack('64s', 'Sample #2')
        response = self.YK.challenge_response(secret, mode='HMAC', slot=2)
        self.assertEqual(response, '\x09\x22\xd3\x40\x5f\xaa\x3d\x19\x4f\x82\xa4\x58\x30\x73\x7d\x5c\xc6\xc7\x5d\x24')

    #@unittest.skipIf(self.YK is None, "No USB HID YubiKey found")
    def test_serial(self):
        """ Test serial number retrieval (requires YubiKey 2) """
        serial = self.YK.serial()
        print "Serial returned : %s" % serial
        self.assertEqual(type(serial), type(1))

if __name__ == '__main__':
    unittest.main()

########NEW FILE########
__FILENAME__ = yubico_exception
"""
class for exceptions used in the other Yubico modules

All exceptions raised by the different Yubico modules are inherited
from the base class YubicoError. That means you can trap them all,
without knowing the details, with code like this :

    try:
        # something Yubico related
    except yubico.yubico_exception.YubicoError as inst:
        print "ERROR: %s" % inst.reason
"""
# Copyright (c) 2010, Yubico AB
# See the file COPYING for licence statement.

__all__ = [
    # constants
    # functions
    # classes
    'YubicoError',
    'InputError',
    'YubiKeyTimeout',
]

from yubico import __version__

class YubicoError(Exception):
    """
    Base class for Yubico exceptions in the yubico package.

    Attributes:
        reason -- explanation of the error
    """

    def __init__(self, reason):
        self.reason = reason

    def __str__(self):
        return '<%s instance at %s: %s>' % (
            self.__class__.__name__,
            hex(id(self)),
            self.reason
            )

    pass

class InputError(YubicoError):
    """
    Exception raised for errors in an input to some function.
    """
    def __init__(self, reason='input validation error'):
        YubicoError.__init__(self, reason)

########NEW FILE########
__FILENAME__ = yubico_util
"""
utility functions for Yubico modules
"""
# Copyright (c) 2010, Yubico AB
# See the file COPYING for licence statement.

__all__ = [
    # constants
    # functions
    'crc16',
    'validate_crc16',
    'hexdump',
    'modhex_decode',
    'hotp_truncate',
    # classes
]

from yubico import __version__
import yubikey_defs
import yubico_exception
import string

_CRC_OK_RESIDUAL = 0xf0b8

def crc16(data):
    """
    Calculate an ISO13239 CRC checksum of the input buffer.
    """
    m_crc = 0xffff
    for this in data:
        m_crc ^= ord(this)
        for _ in range(8):
            j = m_crc & 1
            m_crc >>= 1
            if j:
                m_crc ^= 0x8408
    return m_crc

def validate_crc16(data):
    """
    Validate that the CRC of the contents of buffer is the residual OK value.
    """
    return crc16(data) == _CRC_OK_RESIDUAL


class DumpColors:
    """ Class holding ANSI colors for colorization of hexdump output """

    def __init__(self):
        self.colors = {'BLUE': '\033[94m',
                       'GREEN': '\033[92m',
                       'RESET': '\033[0m',
                       }
        self.enabled = True
        return None

    def get(self, what):
        """
        Get the ANSI code for 'what'

        Returns an empty string if disabled/not found
        """
        if self.enabled:
            if what in self.colors:
                return self.colors[what]
        return ''

    def enable(self):
        """ Enable colorization """
        self.enabled = True

    def disable(self):
        """ Disable colorization """
        self.enabled = False

def hexdump(src, length=8, colorize=False):
    """ Produce a string hexdump of src, for debug output."""
    if not src:
        return str(src)
    if type(src) is not str:
        raise yubico_exception.InputError('Hexdump \'src\' must be string (got %s)' % type(src))
    offset = 0
    result = ''
    for this in group(src, length):
        if colorize:
            last, this = this[-1:], this[:-1]
            colors = DumpColors()
            color = colors.get('RESET')
            if ord(last) & yubikey_defs.RESP_PENDING_FLAG:
                # write to key
                color = colors.get('BLUE')
            elif ord(last) & yubikey_defs.SLOT_WRITE_FLAG:
                color = colors.get('GREEN')
            hex_s = color + ' '.join(["%02x" % ord(x) for x in this]) + colors.get('RESET')
            hex_s += " %02x" % ord(last)
        else:
            hex_s = ' '.join(["%02x" % ord(x) for x in this])
        result += "%04X   %s\n" % (offset, hex_s)
        offset += length
    return result

def group(data, num):
    """ Split data into chunks of num chars each """
    return [data[i:i+num] for i in xrange(0, len(data), num)]

def modhex_decode(data):
    """ Convert a modhex string to ordinary hex. """
    t_map = string.maketrans("cbdefghijklnrtuv", "0123456789abcdef")
    return data.translate(t_map)

def hotp_truncate(hmac_result, length=6):
    """ Perform the HOTP Algorithm truncating. """
    if len(hmac_result) != 20:
        raise yubico_exception.YubicoError("HMAC-SHA-1 not 20 bytes long")
    offset   =  ord(hmac_result[19]) & 0xf
    bin_code = (ord(hmac_result[offset]) & 0x7f) << 24 \
        | (ord(hmac_result[offset+1]) & 0xff) << 16 \
        | (ord(hmac_result[offset+2]) & 0xff) <<  8 \
        | (ord(hmac_result[offset+3]) & 0xff)
    return bin_code % (10 ** length)

########NEW FILE########
__FILENAME__ = yubikey
"""
module for accessing a YubiKey

In an attempt to support any future versions of the YubiKey which
might not be USB HID devices, you should always use the yubikey.find_key()
(or better yet, yubico.find_yubikey()) function to initialize
communication with YubiKeys.

Example usage (if using this module directly, see base module yubico) :

    import yubico.yubikey

    try:
        YK = yubico.yubikey.find_key()
        print "Version : %s " % YK.version()
    except yubico.yubico_exception.YubicoError as inst:
        print "ERROR: %s" % inst.reason
"""
# Copyright (c) 2010, 2011, 2012 Yubico AB
# See the file COPYING for licence statement.

__all__ = [
    # constants
    'RESP_TIMEOUT_WAIT_FLAG',
    'RESP_PENDING_FLAG',
    'SLOT_WRITE_FLAG',
    # functions
    'find_key',
    # classes
    'YubiKey',
    'YubiKeyTimeout',
]

from yubico  import __version__
import yubico_exception

class YubiKeyError(yubico_exception.YubicoError):
    """
    Exception raised concerning YubiKey operations.

    Attributes:
        reason -- explanation of the error
    """
    def __init__(self, reason='no details'):
        yubico_exception.YubicoError.__init__(self, reason)

class YubiKeyTimeout(YubiKeyError):
    """
    Exception raised when a YubiKey operation timed out.

    Attributes:
        reason -- explanation of the error
    """
    def __init__(self, reason='no details'):
        YubiKeyError.__init__(self, reason)

class YubiKeyVersionError(YubiKeyError):
    """
    Exception raised when the YubiKey is not capable of something requested.

    Attributes:
        reason -- explanation of the error
    """
    def __init__(self, reason='no details'):
        YubiKeyError.__init__(self, reason)


class YubiKeyCapabilities():
    """
    Class expressing the functionality of a YubiKey.

    This base class should be the superset of all sub-classes.

    In this base class, we lie and say 'yes' to all capabilities.

    If the base class is used (such as when creating a YubiKeyConfig()
    before getting a YubiKey()), errors must be handled at runtime
    (or later, when the user is unable to use the YubiKey).
    """

    model = 'Unknown'
    version = (0, 0, 0,)
    version_num = 0x0
    default_answer = True

    def __init__(self, model = None, version = None, default_answer = None):
        self.model = model
        if default_answer is not None:
            self.default_answer = default_answer
        if version is not None:
            self.version = version
            (major, minor, build,) = version
            # convert 2.1.3 to 0x00020103
            self.version_num = (major << 24) | (minor << 16) | build
        return None

    def __repr__(self):
        return '<%s instance at %s: Device %s %s (default: %s)>' % (
            self.__class__.__name__,
            hex(id(self)),
            self.model,
            self.version,
            self.default_answer,
            )

    def have_yubico_OTP(self):
        return self.default_answer

    def have_OATH(self, mode):
        return self.default_answer

    def have_challenge_response(self, mode):
        return self.default_answer

    def have_serial_number(self):
        return self.default_answer

    def have_ticket_flag(self, flag):
        return self.default_answer

    def have_config_flag(self, flag):
        return self.default_answer

    def have_extended_flag(self, flag):
        return self.default_answer

    def have_extended_scan_code_mode(self):
        return self.default_answer

    def have_shifted_1_mode(self):
        return self.default_answer

    def have_nfc_ndef(self):
        return self.default_answer

    def have_configuration_slot(self):
        return self.default_answer

class YubiKey():
    """
    Base class for accessing YubiKeys
    """

    debug = None
    capabilities = None

    def __init__(self, debug, capabilities = None):
        self.debug = debug
        if capabilities is None:
            self.capabilities = YubiKeyCapabilities(default_answer = False)
        else:
            self.capabilities = capabilities
        return None

    def version(self):
        """ Get the connected YubiKey's version as a string. """
        pass

    def serial(self, may_block=True):
        """
        Get the connected YubiKey's serial number.

        Note that since version 2.?.? this requires the YubiKey to be
        configured with the extended flag SERIAL_API_VISIBLE.

        If the YubiKey is configured with SERIAL_BTN_VISIBLE set to True,
        it will start blinking and require a button press before revealing
        the serial number, with a 15 seconds timeout. Set `may_block'
        to False to abort if this is the case.
        """
        pass

    def challenge(self, challenge, mode='HMAC', slot=1, variable=True, may_block=True):
        """
        Get the response to a challenge from a connected YubiKey.

        `mode' is either 'HMAC' or 'OTP'.
        `slot' is 1 or 2.
        `variable' is only relevant for mode == HMAC.

        If variable is True, challenge will be padded such that the
        YubiKey will compute the HMAC as if there were no padding.
        If variable is False, challenge will always be NULL-padded
        to 64 bytes.

        The special case of no input will be HMACed by the YubiKey
        (in variable HMAC mode) as data = 0x00, length = 1.

        In mode 'OTP', the challenge should be exactly 6 bytes. The
        response will be a YubiKey "ticket" with the 6-byte challenge
        in the ticket.uid field. The rest of the "ticket" will contain
        timestamp and counter information, so two identical challenges
        will NOT result in the same responses. The response is
        decryptable using AES ECB if you have access to the AES key
        programmed into the YubiKey.
        """
        pass

    def init_config(self):
        """
        Return a YubiKey configuration object for this type of YubiKey.
        """
        pass

    def write_config(self, cfg, slot):
        """
        Configure a YubiKey using a configuration object.
        """
        pass

# Since YubiKeyUSBHID is a subclass of YubiKey (defined here above),
# the import must be after the declaration of YubiKey. We also carefully
# import only what we need to not get a circular import of modules.
from yubikey_usb_hid import YubiKeyUSBHID, YubiKeyUSBHIDError
from yubikey_neo_usb_hid import YubiKeyNEO_USBHID, YubiKeyNEO_USBHIDError

def find_key(debug=False, skip=0):
    """
    Locate a connected YubiKey. Throws an exception if none is found.

    This function is supposed to be possible to extend if any other YubiKeys
    appear in the future.

    Attributes :
        skip  -- number of YubiKeys to skip
        debug -- True or False
    """
    try:
        YK = YubiKeyUSBHID(debug=debug, skip=skip)
        if (YK.version_num() >= (2, 1, 4,)) and \
                (YK.version_num() <= (2, 1, 9,)):
            # YubiKey NEO BETA, re-detect
            YK2 = YubiKeyNEO_USBHID(debug=debug, skip=skip)
            if YK2.version_num() == YK.version_num():
                # XXX not guaranteed to be the same one I guess
                return YK2
            raise YubiKeyError('Found YubiKey NEO BETA, but failed on rescan.')
        return YK
    except YubiKeyUSBHIDError as inst:
        if 'No USB YubiKey found' in str(inst):
            # generalize this error
            raise YubiKeyError('No YubiKey found')
        else:
            raise

########NEW FILE########
__FILENAME__ = yubikey_config
"""
module for configuring YubiKeys
"""
# Copyright (c) 2010, 2012 Yubico AB
# See the file COPYING for licence statement.

__all__ = [
    # constants
    'TicketFlags',
    'ConfigFlags',
    'ExtendedFlags',
    # functions
    # classes
    'YubiKeyConfigError',
    'YubiKeyConfig',
]

from yubico import __version__

import struct
import binascii
import yubico_util
import yubikey_defs
import yubikey_frame
import yubico_exception
import yubikey_config_util
from yubikey_config_util import YubiKeyConfigBits, YubiKeyConfigFlag, YubiKeyExtendedFlag, YubiKeyTicketFlag
import yubikey

TicketFlags = [
    YubiKeyTicketFlag('TAB_FIRST',		0x01, min_ykver=(1, 0), doc='Send TAB before first part'),
    YubiKeyTicketFlag('APPEND_TAB1',		0x02, min_ykver=(1, 0), doc='Send TAB after first part'),
    YubiKeyTicketFlag('APPEND_TAB2',		0x04, min_ykver=(1, 0), doc='Send TAB after second part'),
    YubiKeyTicketFlag('APPEND_DELAY1',		0x08, min_ykver=(1, 0), doc='Add 0.5s delay after first part'),
    YubiKeyTicketFlag('APPEND_DELAY2',		0x10, min_ykver=(1, 0), doc='Add 0.5s delay after second part'),
    YubiKeyTicketFlag('APPEND_CR',		0x20, min_ykver=(1, 0), doc='Append CR as final character'),
    YubiKeyTicketFlag('OATH_HOTP',		0x40, min_ykver=(2, 1), doc='Choose OATH-HOTP mode'),
    YubiKeyTicketFlag('CHAL_RESP',		0x40, min_ykver=(2, 2), doc='Choose Challenge-Response mode'),
    YubiKeyTicketFlag('PROTECT_CFG2',		0x80, min_ykver=(2, 0), doc='Protect configuration in slot 2'),
    ]

ConfigFlags = [
    YubiKeyConfigFlag('SEND_REF',		0x01, min_ykver=(1, 0), doc='Send reference string (0..F) before data'),
    YubiKeyConfigFlag('TICKET_FIRST',		0x02, min_ykver=(1, 0), doc='Send ticket first (default is fixed part)', max_ykver=(1, 9)),
    YubiKeyConfigFlag('PACING_10MS',		0x04, min_ykver=(1, 0), doc='Add 10ms intra-key pacing'),
    YubiKeyConfigFlag('PACING_20MS',		0x08, min_ykver=(1, 0), doc='Add 20ms intra-key pacing'),
    #YubiKeyConfigFlag('ALLOW_HIDTRIG',		0x10, min_ykver=(1, 0), doc='DONT USE: Allow trigger through HID/keyboard', max_ykver=(1, 9)),
    YubiKeyConfigFlag('STATIC_TICKET',		0x20, min_ykver=(1, 0), doc='Static ticket generation'),

    # YubiKey 2.0 and above
    YubiKeyConfigFlag('SHORT_TICKET',		0x02, min_ykver=(2, 0), doc='Send truncated ticket (half length)'),
    YubiKeyConfigFlag('STRONG_PW1',		0x10, min_ykver=(2, 0), doc='Strong password policy flag #1 (mixed case)'),
    YubiKeyConfigFlag('STRONG_PW2',		0x40, min_ykver=(2, 0), doc='Strong password policy flag #2 (subtitute 0..7 to digits)'),
    YubiKeyConfigFlag('MAN_UPDATE',		0x80, min_ykver=(2, 0), doc='Allow manual (local) update of static OTP'),

    # YubiKey 2.1 and above
    YubiKeyConfigFlag('OATH_HOTP8',		0x02, min_ykver=(2, 1), mode='OATH', doc='Generate 8 digits HOTP rather than 6 digits'),
    YubiKeyConfigFlag('OATH_FIXED_MODHEX1',	0x10, min_ykver=(2, 1), mode='OATH', doc='First byte in fixed part sent as modhex'),
    YubiKeyConfigFlag('OATH_FIXED_MODHEX2',	0x40, min_ykver=(2, 1), mode='OATH', doc='First two bytes in fixed part sent as modhex'),
    YubiKeyConfigFlag('OATH_FIXED_MODHEX',	0x50, min_ykver=(2, 1), mode='OATH', doc='Fixed part sent as modhex'),
    YubiKeyConfigFlag('OATH_FIXED_MASK',	0x50, min_ykver=(2, 1), mode='OATH', doc='Mask to get out fixed flags'),

    # YubiKey 2.2 and above
    YubiKeyConfigFlag('CHAL_YUBICO',		0x20, min_ykver=(2, 2), mode='CHAL', doc='Challenge-response enabled - Yubico OTP mode'),
    YubiKeyConfigFlag('CHAL_HMAC',		0x22, min_ykver=(2, 2), mode='CHAL', doc='Challenge-response enabled - HMAC-SHA1'),
    YubiKeyConfigFlag('HMAC_LT64',		0x04, min_ykver=(2, 2), mode='CHAL', doc='Set when HMAC message is less than 64 bytes'),
    YubiKeyConfigFlag('CHAL_BTN_TRIG',		0x08, min_ykver=(2, 2), mode='CHAL', doc='Challenge-respoonse operation requires button press'),
    ]

ExtendedFlags = [
    YubiKeyExtendedFlag('SERIAL_BTN_VISIBLE',	0x01, min_ykver=(2, 2), doc='Serial number visible at startup (button press)'),
    YubiKeyExtendedFlag('SERIAL_USB_VISIBLE',	0x02, min_ykver=(2, 2), doc='Serial number visible in USB iSerial field'),
    YubiKeyExtendedFlag('SERIAL_API_VISIBLE',	0x04, min_ykver=(2, 2), doc='Serial number visible via API call'),

    # YubiKey 2.3 and above
    YubiKeyExtendedFlag('USE_NUMERIC_KEYPAD',	0x08, min_ykver=(2, 3), doc='Use numeric keypad for digits'),
    YubiKeyExtendedFlag('FAST_TRIG',		0x10, min_ykver=(2, 3), doc='Use fast trig if only cfg1 set'),
    YubiKeyExtendedFlag('ALLOW_UPDATE',		0x20, min_ykver=(2, 3), doc='Allow update of existing configuration (selected flags + access code)'),
    YubiKeyExtendedFlag('DORMANT',		0x40, min_ykver=(2, 3), doc='Dormant configuration (can be woken up and flag removed = requires update flag)'),
    ]

SLOT_CONFIG			= 0x01	# First (default / V1) configuration
SLOT_CONFIG2			= 0x03	# Second (V2) configuration
SLOT_UPDATE1			= 0x04	# Update slot 1
SLOT_UPDATE2			= 0x05	# Update slot 2
SLOT_SWAP			= 0x06	# Swap slot 1 and 2

def command2str(num):
    """ Turn command number into name """
    known = {0x01: "SLOT_CONFIG",
             0x03: "SLOT_CONFIG2",
             0x04: "SLOT_UPDATE1",
             0x05: "SLOT_UPDATE2",
             0x06: "SLOT_SWAP",
             }
    if num in known:
        return known[num]
    return "0x%02x" % (num)

class YubiKeyConfigError(yubico_exception.YubicoError):
    """
    Exception raised for YubiKey configuration errors.
    """

class YubiKeyConfig():
    """
    Base class for configuration of all current types of YubiKeys.
    """
    def __init__(self, ykver=None, capabilities=None, update=False, swap=False):
        """
        `ykver' is a tuple (major, minor) with the version number of the key
        you are planning to apply this configuration to. Not mandated, but
        will get you an exception when trying to set flags for example, rather
        than the YubiKey just not operating as expected after programming.

        YubiKey >= 2.3 supports updating certain parts of a configuration
        (for example turning on/off APPEND_CR) without overwriting others
        (most notably the stored secret). Set `update' to True if this is
        what you want. The current programming must have flag 'ALLOW_UPDATE'
        set to allow configuration update instead of requiring complete
        reprogramming.

        YubiKey >= 2.3 also supports swapping the configurations, making
        slot 1 be slot 2 and vice versa. Set swap=True for this.
        """
        if capabilities is None:
            self.capabilities = yubikey.YubiKeyCapabilities(default_answer = True)
        else:
            self.capabilities = capabilities

        # Minimum version of YubiKey this configuration will require
        self.yk_req_version = (0, 0)
        self.ykver = ykver

        self.fixed = ''
        self.uid = ''
        self.key = ''
        self.access_code = ''

        self.ticket_flags = YubiKeyConfigBits(0x0)
        self.config_flags = YubiKeyConfigBits(0x0)
        self.extended_flags = YubiKeyConfigBits(0x0)

        self.unlock_code = ''
        self._mode = ''
        if update or swap:
            self._require_version(major=2, minor=3)
        self._update_config = update
        self._swap_slots = swap

        return None

    def __repr__(self):
        return '<%s instance at %s: mode %s, v=%s/%s, lf=%i, lu=%i, lk=%i, lac=%i, tf=%x, cf=%x, ef=%x, lu=%i, up=%s, sw=%s>' % (
            self.__class__.__name__,
            hex(id(self)),
            self._mode,
            self.yk_req_version, self.ykver,
            len(self.fixed),
            len(self.uid),
            len(self.key),
            len(self.access_code),
            self.ticket_flags.to_integer(),
            self.config_flags.to_integer(),
            self.extended_flags.to_integer(),
            len(self.unlock_code),
            self._update_config,
            self._swap_slots,
            )

    def version_required(self):
        """
        Return the (major, minor) versions of YubiKey required for this configuration.
        """
        return self.yk_req_version

    def fixed_string(self, data=None):
        """
        The fixed string is used to identify a particular Yubikey device.

        The fixed string is referred to as the 'Token Identifier' in OATH-HOTP mode.

        The length of the fixed string can be set between 0 and 16 bytes.

        Tip: This can also be used to extend the length of a static password.
        """
        old = self.fixed
        if data != None:
            new = self._decode_input_string(data)
            if len(new) <= 16:
                self.fixed = new
            else:
                raise yubico_exception.InputError('The "fixed" string must be 0..16 bytes')
        return old

    def enable_extended_scan_code_mode(self):
        """
        Extended scan code mode means the Yubikey will output the bytes in
        the 'fixed string' as scan codes, without modhex encoding the data.

        Because of the way this is stored in the config flags, it is not
        possible to disable this option once it is enabled (of course, you
        can abort config update or reprogram the YubiKey again).

        Requires YubiKey 2.x.
        """
        if not self.capabilities.have_extended_scan_code_mode():
            raise
        self._require_version(major=2)
        self.config_flag('SHORT_TICKET', True)
        self.config_flag('STATIC_TICKET', False)

    def enable_shifted_1(self):
        """
        This will cause a shifted character 1 (typically '!') to be sent before
        anything else. This can be used to make the YubiKey output qualify as a
        password with 'special characters', if such is required.

        Because of the way this is stored in the config flags, it is not
        possible to disable this option once it is enabled (of course, you
        can abort config update or reprogram the YubiKey again).

        Requires YubiKey 2.x.
        """
        self._require_version(major=2)
        self.config_flag('STRONG_PW2', True)
        self.config_flag('SEND_REF', True)

    def aes_key(self, data):
        """
        AES128 key to program into YubiKey.

        Supply data as either a raw string, or a hexlified string prefixed by 'h:'.
        The result, after any hex decoding, must be 16 bytes.
        """
        old = self.key
        if data:
            new = self._decode_input_string(data)
            if len(new) == 16:
                self.key = new
            else:
                raise yubico_exception.InputError('AES128 key must be exactly 16 bytes')

        return old

    def unlock_key(self, data):
        """
        Access code to allow re-programming of your YubiKey.

        Supply data as either a raw string, or a hexlified string prefixed by 'h:'.
        The result, after any hex decoding, must be 6 bytes.
        """
        if data.startswith('h:'):
            new = binascii.unhexlify(data[2:])
        else:
            new = data
        if len(new) == 6:
            self.unlock_code = new
            if not self.access_code:
                # Don't reset the access code when programming, unless that seems
                # to be the intent of the calling program.
                self.access_code = new
        else:
            raise yubico_exception.InputError('Unlock key must be exactly 6 bytes')

    def access_key(self, data):
        """
        Set a new access code which will be required for future re-programmings of your YubiKey.

        Supply data as either a raw string, or a hexlified string prefixed by 'h:'.
        The result, after any hex decoding, must be 6 bytes.
        """
        if data.startswith('h:'):
            new = binascii.unhexlify(data[2:])
        else:
            new = data
        if len(new) == 6:
            self.access_code = new
        else:
            raise yubico_exception.InputError('Access key must be exactly 6 bytes')

    def mode_yubikey_otp(self, private_uid, aes_key):
        """
        Set the YubiKey up for standard OTP validation.
        """
        if not self.capabilities.have_yubico_OTP():
            raise yubikey.YubiKeyVersionError('Yubico OTP not available in %s version %d.%d' \
                                                  % (self.capabilities.model, self.ykver[0], self.ykver[1]))
        if private_uid.startswith('h:'):
            private_uid = binascii.unhexlify(private_uid[2:])
        if len(private_uid) != yubikey_defs.UID_SIZE:
            raise yubico_exception.InputError('Private UID must be %i bytes' % (yubikey_defs.UID_SIZE))

        self._change_mode('YUBIKEY_OTP', major=0, minor=9)
        self.uid = private_uid
        self.aes_key(aes_key)

    def mode_oath_hotp(self, secret, digits=6, factor_seed=None, omp=0x0, tt=0x0, mui=''):
        """
        Set the YubiKey up for OATH-HOTP operation.

        Requires YubiKey 2.1.
        """
        if not self.capabilities.have_OATH('HOTP'):
            raise yubikey.YubiKeyVersionError('OATH HOTP not available in %s version %d.%d' \
                                                  % (self.capabilities.model, self.ykver[0], self.ykver[1]))
        if digits != 6 and digits != 8:
            raise yubico_exception.InputError('OATH-HOTP digits must be 6 or 8')

        self._change_mode('OATH_HOTP', major=2, minor=1)
        self._set_20_bytes_key(secret)
        if digits == 8:
            self.config_flag('OATH_HOTP8', True)
        if omp or tt or mui:
            decoded_mui = self._decode_input_string(mui)
            fixed = chr(omp) + chr(tt) + decoded_mui
            self.fixed_string(fixed)
        if factor_seed:
            self.uid = self.uid + struct.pack('<H', factor_seed)

    def mode_challenge_response(self, secret, type='HMAC', variable=True, require_button=False):
        """
        Set the YubiKey up for challenge-response operation.

        `type' can be 'HMAC' or 'OTP'.

        `variable' is only applicable to type 'HMAC'.

        For type HMAC, `secret' is expected to be 20 bytes (160 bits).
        For type OTP, `secret' is expected to be 16 bytes (128 bits).

        Requires YubiKey 2.2.
        """
        if not type.upper() in ['HMAC', 'OTP']:
            raise yubico_exception.InputError('Invalid \'type\' (%s)' % type)
        if not self.capabilities.have_challenge_response(type.upper()):
            raise yubikey.YubiKeyVersionError('%s Challenge-Response not available in %s version %d.%d' \
                                                  % (type.upper(), self.capabilities.model, \
                                                         self.ykver[0], self.ykver[1]))
        self._change_mode('CHAL_RESP', major=2, minor=2)
        if type.upper() == 'HMAC':
            self.config_flag('CHAL_HMAC', True)
            self.config_flag('HMAC_LT64', variable)
            self._set_20_bytes_key(secret)
        else:
            # type is 'OTP', checked above
            self.config_flag('CHAL_YUBICO', True)
            self.aes_key(secret)
        self.config_flag('CHAL_BTN_TRIG', require_button)

    def ticket_flag(self, which, new=None):
        """
        Get or set a ticket flag.

        'which' can be either a string ('APPEND_CR' etc.), or an integer.
        You should ALWAYS use a string, unless you really know what you are doing.
        """
        flag = _get_flag(which, TicketFlags)
        if flag:
            if not self.capabilities.have_ticket_flag(flag):
                raise yubikey.YubiKeyVersionError('Ticket flag %s requires %s, and this is %s %d.%d'
                                                  % (which, flag.req_string(self.capabilities.model), \
                                                         self.capabilities.model, self.ykver[0], self.ykver[1]))
            req_major, req_minor = flag.req_version()
            self._require_version(major=req_major, minor=req_minor)
            value = flag.to_integer()
        else:
            if type(which) is not int:
                raise yubico_exception.InputError('Unknown non-integer TicketFlag (%s)' % which)
            value = which

        return self.ticket_flags.get_set(value, new)

    def config_flag(self, which, new=None):
        """
        Get or set a config flag.

        'which' can be either a string ('PACING_20MS' etc.), or an integer.
        You should ALWAYS use a string, unless you really know what you are doing.
        """
        flag = _get_flag(which, ConfigFlags)
        if flag:
            if not self.capabilities.have_config_flag(flag):
                raise yubikey.YubiKeyVersionError('Config flag %s requires %s, and this is %s %d.%d'
                                                  % (which, flag.req_string(self.capabilities.model), \
                                                         self.capabilities.model, self.ykver[0], self.ykver[1]))
            req_major, req_minor = flag.req_version()
            self._require_version(major=req_major, minor=req_minor)
            value = flag.to_integer()
        else:
            if type(which) is not int:
                raise yubico_exception.InputError('Unknown non-integer ConfigFlag (%s)' % which)
            value = which

        return self.config_flags.get_set(value, new)

    def extended_flag(self, which, new=None):
        """
        Get or set a extended flag.

        'which' can be either a string ('SERIAL_API_VISIBLE' etc.), or an integer.
        You should ALWAYS use a string, unless you really know what you are doing.
        """
        flag = _get_flag(which, ExtendedFlags)
        if flag:
            if not self.capabilities.have_extended_flag(flag):
                raise yubikey.YubiKeyVersionError('Extended flag %s requires %s, and this is %s %d.%d'
                                                  % (which, flag.req_string(self.capabilities.model), \
                                                         self.capabilities.model, self.ykver[0], self.ykver[1]))
            req_major, req_minor = flag.req_version()
            self._require_version(major=req_major, minor=req_minor)
            value = flag.to_integer()
        else:
            if type(which) is not int:
                raise yubico_exception.InputError('Unknown non-integer ExtendedFlag (%s)' % which)
            value = which

        return self.extended_flags.get_set(value, new)

    def to_string(self):
        """
        Return the current configuration as a string (always 64 bytes).
        """
        #define UID_SIZE		6	/* Size of secret ID field */
        #define FIXED_SIZE              16      /* Max size of fixed field */
        #define KEY_SIZE                16      /* Size of AES key */
        #define KEY_SIZE_OATH           20      /* Size of OATH-HOTP key (key field + first 4 of UID field) */
        #define ACC_CODE_SIZE           6       /* Size of access code to re-program device */
        #
        #struct config_st {
        #    unsigned char fixed[FIXED_SIZE];/* Fixed data in binary format */
        #    unsigned char uid[UID_SIZE];    /* Fixed UID part of ticket */
        #    unsigned char key[KEY_SIZE];    /* AES key */
        #    unsigned char accCode[ACC_CODE_SIZE]; /* Access code to re-program device */
        #    unsigned char fixedSize;        /* Number of bytes in fixed field (0 if not used) */
        #    unsigned char extFlags;         /* Extended flags */
        #    unsigned char tktFlags;         /* Ticket configuration flags */
        #    unsigned char cfgFlags;         /* General configuration flags */
        #    unsigned char rfu[2];           /* Reserved for future use */
        #    unsigned short crc;             /* CRC16 value of all fields */
        #};
        t_rfu = 0

        first = struct.pack('<16s6s16s6sBBBBH',
                            self.fixed,
                            self.uid,
                            self.key,
                            self.access_code,
                            len(self.fixed),
                            self.extended_flags.to_integer(),
                            self.ticket_flags.to_integer(),
                            self.config_flags.to_integer(),
                            t_rfu
                            )

        crc = 0xffff - yubico_util.crc16(first)

        second = first + struct.pack('<H', crc) + self.unlock_code
        return second

    def to_frame(self, slot=1):
        """
        Return the current configuration as a YubiKeyFrame object.
        """
        data = self.to_string()
        payload = data.ljust(64, chr(0x0))
        if slot is 1:
            if self._update_config:
                command = SLOT_UPDATE1
            else:
                command = SLOT_CONFIG
        elif slot is 2:
            if self._update_config:
                command = SLOT_UPDATE2
            else:
                command = SLOT_CONFIG2
        else:
            assert()

        if self._swap_slots:
            command = SLOT_SWAP

        return yubikey_frame.YubiKeyFrame(command=command, payload=payload)

    def _require_version(self, major, minor=0):
        """ Update the minimum version of YubiKey this configuration can be applied to. """
        new_ver = (major, minor)
        if self.ykver and new_ver > self.ykver:
            raise yubikey.YubiKeyVersionError('Configuration requires YubiKey %d.%d, and this is %d.%d'
                                              % (major, minor, self.ykver[0], self.ykver[1]))
        if new_ver > self.yk_req_version:
            self.yk_req_version = new_ver

    def _decode_input_string(self, data):
        if data.startswith('m:'):
            data = 'h:' + yubico_util.modhex_decode(data[2:])
        if data.startswith('h:'):
            return(binascii.unhexlify(data[2:]))
        else:
            return(data)

    def _change_mode(self, mode, major, minor):
        """ Change mode of operation, with some sanity checks. """
        if self._mode:
            if self._mode != mode:
                raise RuntimeError('Can\'t change mode (from %s to %s)' % (self._mode, mode))
        self._require_version(major=major, minor=minor)
        self._mode = mode
        # when setting mode, we reset all flags
        self.ticket_flags = YubiKeyConfigBits(0x0)
        self.config_flags = YubiKeyConfigBits(0x0)
        self.extended_flags = YubiKeyConfigBits(0x0)
        if mode != 'YUBIKEY_OTP':
            self.ticket_flag(mode, True)

    def _set_20_bytes_key(self, data):
        """
        Set a 20 bytes key. This is used in CHAL_HMAC and OATH_HOTP mode.

        Supply data as either a raw string, or a hexlified string prefixed by 'h:'.
        The result, after any hex decoding, must be 20 bytes.
        """
        if data.startswith('h:'):
            new = binascii.unhexlify(data[2:])
        else:
            new = data
        if len(new) == 20:
            self.key = new[:16]
            self.uid = new[16:]
        else:
            raise yubico_exception.InputError('HMAC key must be exactly 20 bytes')

def _get_flag(which, flags):
    """ Find 'which' entry in 'flags'. """
    res = [this for this in flags if this.is_equal(which)]
    if len(res) == 0:
        return None
    if len(res) == 1:
        return res[0]
    assert()

########NEW FILE########
__FILENAME__ = yubikey_config_util
"""
utility functions used in yubikey_config.
"""
# Copyright (c) 2010, 2012 Yubico AB
# See the file COPYING for licence statement.

__all__ = [
    # constants
    # functions
    # classes
    'YubiKeyConfigBits',
    'YubiKeyConfigFlag',
    'YubiKeyExtendedFlag',
    'YubiKeyTicketFlag',
]

class YubiKeyFlag():
    """
    A flag value, and associated metadata.
    """

    def __init__(self, key, value, doc=None, min_ykver=(0, 0), max_ykver=None, models=['YubiKey', 'YubiKey NEO']):
        """
        Metadata about a ticket/config/extended flag bit.

        @param key: Name of flag, such as 'APPEND_CR'
        @param value: Bit value, 0x20 for APPEND_CR
        @param doc: Human readable description of flag
        @param min_ykver: Tuple with the minimum version required (major, minor,)
        @param min_ykver: Tuple with the maximum version required (major, minor,) (for depreacted flags)
        @param models: List of model identifiers (strings) that support this flag
        """
        if type(key) is not str:
            assert()
        if type(value) is not int:
            assert()
        if type(min_ykver) is not tuple:
            assert()
        if type(models) is not list:
            assert()

        self.key = key
        self.value = value
        self.doc = doc
        self.min_ykver = min_ykver
        self.max_ykver = max_ykver
        self.models = models

        return None

    def __repr__(self):
        return '<%s instance at %s: %s (0x%x)>' % (
            self.__class__.__name__,
            hex(id(self)),
            self.key,
            self.value
            )

    def is_equal(self, key):
        """ Check if key is equal to that of this instance """
        return self.key == key

    def to_integer(self):
        """ Return flag value """
        return self.value

    def req_version(self):
        """ Return the minimum required version """
        return self.min_ykver

    def req_string(self, model):
        """ Return string describing model and version requirement. """
        if model not in self.models:
            model = self.models
        if self.min_ykver and self.max_ykver:
            return "%s %d.%d..%d.%d" % (model, \
                                           self.min_ykver[0], self.min_ykver[1], \
                                           self.max_ykver[0], self.max_ykver[1], \
                                           )
        if self.max_ykver:
            return "%s <= %d.%d" % (model, self.max_ykver[0], self.max_ykver[1])

        return "%s >= %d.%d" % (model, self.min_ykver[0], self.min_ykver[1])

    def is_compatible(self, model, version):
        """ Check if this flag is compatible with a YubiKey of version 'ver'. """
        if not model in self.models:
            return False
        if self.max_ykver:
            return (version >= self.min_ykver and
                    version <= self.max_ykver)
        else:
            return version >= self.min_ykver

class YubiKeyTicketFlag(YubiKeyFlag):
    """
    A ticket flag value, and associated metadata.
    """

class YubiKeyConfigFlag(YubiKeyFlag):
    """
    A config flag value, and associated metadata.
    """

    def __init__(self, key, value, mode='', doc=None, min_ykver=(0, 0), max_ykver=None):
        if type(mode) is not str:
            assert()
        self.mode = mode

        YubiKeyFlag.__init__(self, key, value, doc=doc, min_ykver=min_ykver, max_ykver=max_ykver)

class YubiKeyExtendedFlag(YubiKeyFlag):
    """
    An extended flag value, and associated metadata.
    """

    def __init__(self, key, value, mode='', doc=None, min_ykver=(2, 2), max_ykver=None):
        if type(mode) is not str:
            assert()
        self.mode = mode

        YubiKeyFlag.__init__(self, key, value, doc=doc, min_ykver=min_ykver, max_ykver=max_ykver)

class YubiKeyConfigBits():
    """
    Class to hold bit values for configuration.
    """
    def __init__(self, default=0x0):
        self.value = default
        return None

    def __repr__(self):
        return '<%s instance at %s: value 0x%x>' % (
            self.__class__.__name__,
            hex(id(self)),
            self.value,
            )

    def get_set(self, flag, new):
        """
        Return the boolean value of 'flag'. If 'new' is set,
        the flag is updated, and the value before update is
        returned.
        """
        old = self._is_set(flag)
        if new is True:
            self._set(flag)
        elif new is False:
            self._clear(flag)
        return old

    def to_integer(self):
        """ Return the sum of all flags as an integer. """
        return self.value

    def _is_set(self, flag):
        """ Check if flag is set. Returns True or False. """
        return self.value & flag == flag

    def _set(self, flag):
        """ Set flag. """
        self.value |= flag

    def _clear(self, flag):
        """ Clear flag. """
        self.value &= (0xff - flag)

########NEW FILE########
__FILENAME__ = yubikey_defs
"""
Module with constants. Many of them from ykdefs.h.
"""
# Copyright (c) 2010, 2011 Yubico AB
# See the file COPYING for licence statement.

__all__ = [
    # constants
    'RESP_TIMEOUT_WAIT_MASK',
    'RESP_TIMEOUT_WAIT_FLAG',
    'RESP_PENDING_FLAG',
    'SLOT_WRITE_FLAG',
    'SHA1_MAX_BLOCK_SIZE',
    'SHA1_DIGEST_SIZE',
    'OTP_CHALRESP_SIZE',
    'UID_SIZE',
    # functions
    # classes
]

from yubico import __version__

# Yubikey Low level interface #2.3
RESP_TIMEOUT_WAIT_MASK	= 0x1f # Mask to get timeout value
RESP_TIMEOUT_WAIT_FLAG	= 0x20 # Waiting for timeout operation - seconds left in lower 5 bits
RESP_PENDING_FLAG	= 0x40 # Response pending flag
SLOT_WRITE_FLAG		= 0x80 # Write flag - set by app - cleared by device

SHA1_MAX_BLOCK_SIZE	= 64   # Max size of input SHA1 block
SHA1_DIGEST_SIZE	= 20   # Size of SHA1 digest = 160 bits
OTP_CHALRESP_SIZE	= 16   # Number of bytes returned for an Yubico-OTP challenge (not from ykdef.h)

UID_SIZE		= 6    # Size of secret ID field

########NEW FILE########
__FILENAME__ = yubikey_frame
"""
module for creating frames of data that can be sent to a YubiKey
"""
# Copyright (c) 2010, Yubico AB
# See the file COPYING for licence statement.

__all__ = [
    # constants
    # functions
    # classes
    'YubiKeyFrame',
]

import struct

import yubico_util
import yubikey_defs
import yubico_exception
import yubikey_config
from yubico import __version__

class YubiKeyFrame:
    """
    Class containing an YKFRAME (as defined in ykdef.h).

    A frame is basically 64 bytes of data. When this is to be sent
    to a YubiKey, it is put inside 10 USB HID feature reports. Each
    feature report is 7 bytes of data plus 1 byte of sequencing and
    flags.
    """

    def __init__(self, command, payload=''):
        if payload is '':
            payload = '\x00' * 64
        if len(payload) != 64:
            raise yubico_exception.InputError('payload must be empty or 64 bytes')
        self.payload = payload
        self.command = command
        self.crc = yubico_util.crc16(payload)

    def __repr__(self):
        return '<%s.%s instance at %s: %s>' % (
            self.__class__.__module__,
            self.__class__.__name__,
            hex(id(self)),
            self.command
            )

    def to_string(self):
        """
        Return the frame as a 70 byte string.
        """
        # From ykdef.h :
        #
        # // Frame structure
	# #define SLOT_DATA_SIZE  64
        # typedef struct {
        #     unsigned char payload[SLOT_DATA_SIZE];
        #     unsigned char slot;
        #     unsigned short crc;
        #     unsigned char filler[3];
        # } YKFRAME;
        filler = ''
        return struct.pack('<64sBH3s',
                           self.payload, self.command, self.crc, filler)

    def to_feature_reports(self, debug=False):
        """
        Return the frame as an array of 8-byte parts, ready to be sent to a YubiKey.
        """
        rest = self.to_string()
        seq = 0
        out = []
        # When sending a frame to the YubiKey, we can (should) remove any
        # 7-byte serie that only consists of '\x00', besides the first
        # and last serie.
        while rest:
            this, rest = rest[:7], rest[7:]
            if seq > 0 and rest:
                # never skip first or last serie
                if this != '\x00\x00\x00\x00\x00\x00\x00':
                    this += chr(yubikey_defs.SLOT_WRITE_FLAG + seq)
                    out.append(self._debug_string(debug, this))
            else:
                this += chr(yubikey_defs.SLOT_WRITE_FLAG + seq)
                out.append(self._debug_string(debug, this))
            seq += 1
        return out

    def _debug_string(self, debug, data):
        """
        Annotate a frames data, if debug is True.
        """
        if not debug:
            return data
        if self.command in [yubikey_config.SLOT_CONFIG,
                            yubikey_config.SLOT_CONFIG2,
                            yubikey_config.SLOT_UPDATE1,
                            yubikey_config.SLOT_UPDATE2,
                            yubikey_config.SLOT_SWAP,
                            ]:
            # annotate according to config_st (see yubikey_config.to_string())
            if ord(data[-1]) == 0x80:
                return (data, "FFFFFFF")
            if ord(data[-1]) == 0x81:
                return (data, "FFFFFFF")
            if ord(data[-1]) == 0x82:
                return (data, "FFUUUUU")
            if ord(data[-1]) == 0x83:
                return (data, "UKKKKKK")
            if ord(data[-1]) == 0x84:
                return (data, "KKKKKKK")
            if ord(data[-1]) == 0x85:
                return (data, "KKKAAAA")
            if ord(data[-1]) == 0x86:
                return (data, "AAlETCr")
            if ord(data[-1]) == 0x87:
                return (data, "rCR")
            # after payload
            if ord(data[-1]) == 0x89:
                return (data, " Scr")
        else:
            return (data, '')

########NEW FILE########
__FILENAME__ = yubikey_neo_usb_hid
"""
module for accessing a USB HID YubiKey NEO
"""

# Copyright (c) 2012 Yubico AB
# See the file COPYING for licence statement.

__all__ = [
    # constants
    'uri_identifiers',
    # functions
    # classes
    'YubiKeyNEO_USBHID',
    'YubiKeyNEO_USBHIDError'
]

import struct

from yubico import __version__
import yubikey_usb_hid
import yubikey_frame
import yubico_exception

# commands from ykdef.h
_SLOT_NDEF		= 0x08 # Write YubiKey NEO NDEF
_ACC_CODE_SIZE		= 6    # Size of access code to re-program device
_NDEF_DATA_SIZE		= 54

# from nfcdef.h
_NDEF_URI_TYPE		= ord('U')
_NDEF_TEXT_TYPE		= ord('T')

# From nfcforum-ts-rtd-uri-1.0.pdf
uri_identifiers = [
    (0x01, "http://www.",),
    (0x02, "https://www.",),
    (0x03, "http://",),
    (0x04, "https://",),
    (0x05, "tel:",),
    (0x06, "mailto:",),
    (0x07, "ftp://anonymous:anonymous@",),
    (0x08, "ftp://ftp.",),
    (0x09, "ftps://",),
    (0x0a, "sftp://",),
    (0x0b, "smb://",),
    (0x0c, "nfs://",),
    (0x0d, "ftp://",),
    (0x0e, "dav://",),
    (0x0f, "news:",),
    (0x10, "telnet://",),
    (0x11, "imap:",),
    (0x12, "rtsp://",),
    (0x13, "urn:",),
    (0x14, "pop:",),
    (0x15, "sip:",),
    (0x16, "sips:",),
    (0x17, "tftp:",),
    (0x18, "btspp://",),
    (0x19, "btl2cap://",),
    (0x1a, "btgoep://",),
    (0x1b, "tcpobex://",),
    (0x1c, "irdaobex://",),
    (0x1d, "file://",),
    (0x1e, "urn:epc:id:",),
    (0x1f, "urn:epc:tag:",),
    (0x20, "urn:epc:pat:",),
    (0x21, "urn:epc:raw:",),
    (0x22, "urn:epc:",),
    (0x23, "urn:nfc:",),
    ]

class YubiKeyNEO_USBHIDError(yubico_exception.YubicoError):
    """ Exception raised for errors with the NEO USB HID communication. """

class YubiKeyNEO_USBHIDCapabilities(yubikey_usb_hid.YubiKeyUSBHIDCapabilities):
    """
    Capabilities of current YubiKey NEO BETA firmwares 2.1.4 and 2.1.5.
    """

    def have_challenge_response(self, mode):
        return False

    def have_configuration_slot(self, slot):
        return (slot == 1)

    def have_nfc_ndef(self):
        return True

class YubiKeyNEO_USBHID(yubikey_usb_hid.YubiKeyUSBHID):
    """
    Class for accessing a YubiKey NEO over USB HID.

    The NEO is very similar to the original YubiKey (YubiKeyUSBHID)
    but does add the NDEF "slot".

    The NDEF is the tag the YubiKey emmits over it's NFC interface.
    """

    model = 'YubiKey NEO'
    description = 'YubiKey NEO'

    def __init__(self, debug=False, skip=0):
        """
        Find and connect to a YubiKey NEO (USB HID).

        Attributes :
            skip  -- number of YubiKeys to skip
            debug -- True or False
        """
        yubikey_usb_hid.YubiKeyUSBHID.__init__(self, debug, skip)
        if self.version_num() >= (2, 1, 4,) and \
                self.version_num() <= (2, 1, 9,):
            self.description = 'YubiKey NEO BETA'

    def write_ndef(self, ndef):
        """


        Write an NDEF tag configuration to the YubiKey NEO.
        """
        return self._write_config(ndef, _SLOT_NDEF)

class YubiKeyNEO_NDEF():
    """
    Class allowing programming of a YubiKey NEO NDEF.
    """

    ndef_type = _NDEF_URI_TYPE
    ndef_str = None
    access_code = chr(0x0) * _ACC_CODE_SIZE
    # For _NDEF_URI_TYPE
    ndef_uri_rt = 0x0  # No prepending
    # For _NDEF_TEXT_TYPE
    ndef_text_lang = 'en'
    ndef_text_enc = 'UTF-8'

    def __init__(self, data, access_code = None):
        self.ndef_str = data
        if access_code is not None:
            self.access_code = access_code

    def text(self, encoding = 'UTF-8', language = 'en'):
        """
        Configure parameters for NDEF type TEXT.

        @param encoding: The encoding used. Should be either 'UTF-8' or 'UTF16'.
        @param language: ISO/IANA language code (see RFC 3066).
        """
        self.ndef_type = _NDEF_TEXT_TYPE
        self.ndef_text_lang = language
        self.ndef_text_enc = encoding
        return self

    def type(self, url = False, text = False, other = None):
        """
        Change the NDEF type.
        """
        if (url, text, other) == (True, False, None):
            self.ndef_type = _NDEF_URI_TYPE
        elif (url, text, other) == (False, True, None):
            self.ndef_type = _NDEF_TEXT_TYPE
        elif (url, text, type(other)) == (False, False, int):
            self.ndef_type = other
        else:
            raise YubiKeyNEO_USBHIDError("Bad or conflicting NDEF type specified")
        return self

    def to_string(self):
        """
        Return the current NDEF as a string (always 64 bytes).
        """
        data = self.ndef_str
        if self.ndef_type == _NDEF_URI_TYPE:
            data = self._encode_ndef_uri_type(data)
        elif self.ndef_type == _NDEF_TEXT_TYPE:
            data = self._encode_ndef_text_params(data)
        if len(data) > _NDEF_DATA_SIZE:
            raise YubiKeyNEO_USBHIDError("NDEF payload too long")
        # typedef struct {
        #   unsigned char len;                  // Payload length
        #   unsigned char type;                 // NDEF type specifier
        #   unsigned char data[NDEF_DATA_SIZE]; // Payload size
        #   unsigned char curAccCode[ACC_CODE_SIZE]; // Access code
        # } YKNDEF;
        #
        fmt = '< B B %ss %ss' % (_NDEF_DATA_SIZE, _ACC_CODE_SIZE)
        first = struct.pack(fmt,
                            len(data),
                            self.ndef_type,
                            data.ljust(_NDEF_DATA_SIZE, chr(0x0)),
                            self.access_code,
                            )
        #crc = 0xffff - yubico_util.crc16(first)
        #second = first + struct.pack('<H', crc) + self.unlock_code
        return first

    def to_frame(self, slot=_SLOT_NDEF):
        """
        Return the current configuration as a YubiKeyFrame object.
        """
        data = self.to_string()
        payload = data.ljust(64, chr(0x0))
        return yubikey_frame.YubiKeyFrame(command = slot, payload = payload)

    def _encode_ndef_uri_type(self, data):
        """
        Implement NDEF URI Identifier Code.

        This is a small hack to replace some well known prefixes (such as http://)
        with a one byte code. If the prefix is not known, 0x00 is used.
        """
        t = 0x0
        for (code, prefix) in uri_identifiers:
            if data[:len(prefix)].lower() == prefix:
                t = code
                data = data[len(prefix):]
                break
        data = chr(t) + data
        return data

    def _encode_ndef_text_params(self, data):
        """
        Prepend language and enconding information to data, according to
        nfcforum-ts-rtd-text-1-0.pdf
        """
        status = len(self.ndef_text_lang)
        if self.ndef_text_enc == 'UTF16':
            status = status & 0b10000000
        return chr(status) + self.ndef_text_lang + data

########NEW FILE########
__FILENAME__ = yubikey_usb_hid
"""
module for accessing a USB HID YubiKey
"""

# Copyright (c) 2010, 2011, 2012 Yubico AB
# See the file COPYING for licence statement.

__all__ = [
  # constants
  # functions
  # classes
  'YubiKeyUSBHID',
  'YubiKeyUSBHIDError',
  'YubiKeyUSBHIDStatus',
]

from yubico import __version__

import yubico_util
import yubico_exception
import yubikey_frame
import yubikey_config
import yubikey_defs
import yubikey
from yubikey import YubiKey
import struct
import time
import sys

# Various USB/HID parameters
_USB_TYPE_CLASS		= (0x01 << 5)
_USB_RECIP_INTERFACE	= 0x01
_USB_ENDPOINT_IN	= 0x80
_USB_ENDPOINT_OUT	= 0x00

_HID_GET_REPORT		= 0x01
_HID_SET_REPORT		= 0x09

_USB_TIMEOUT_MS		= 100

# from ykcore_backend.h
_FEATURE_RPT_SIZE	= 8
_REPORT_TYPE_FEATURE	= 0x03
# from ykdef.h
_YUBICO_VID		= 0x1050
_YUBIKEY_PID		= 0x0010
_NEO_OTP_PID 		= 0x0110
_NEO_OTP_CCID_PID 	= 0x0111
# commands from ykdef.h
_SLOT_DEVICE_SERIAL	= 0x10 # Device serial number
_SLOT_CHAL_OTP1		= 0x20 # Write 6 byte challenge to slot 1, get Yubico OTP response
_SLOT_CHAL_OTP2		= 0x28 # Write 6 byte challenge to slot 2, get Yubico OTP response
_SLOT_CHAL_HMAC1	= 0x30 # Write 64 byte challenge to slot 1, get HMAC-SHA1 response
_SLOT_CHAL_HMAC2	= 0x38 # Write 64 byte challenge to slot 2, get HMAC-SHA1 response

# dict used to select command for mode+slot in _challenge_response
_CMD_CHALLENGE = {'HMAC': {1: _SLOT_CHAL_HMAC1, 2: _SLOT_CHAL_HMAC2},
                  'OTP': {1: _SLOT_CHAL_OTP1, 2: _SLOT_CHAL_OTP2},
                  }

class YubiKeyUSBHIDError(yubico_exception.YubicoError):
    """ Exception raised for errors with the USB HID communication. """

class YubiKeyUSBHIDCapabilities(yubikey.YubiKeyCapabilities):
    """
    Capture the capabilities of the various versions of YubiKeys.

    Overrides just the functions from YubiKeyCapabilities() that are available
    in one or more versions, leaving the other ones at False through default_answer.
    """
    def __init__(self, model, version, default_answer):
        yubikey.YubiKeyCapabilities.__init__(self, model = model, \
                                                 version = version, \
                                                 default_answer = default_answer)

    def have_yubico_OTP(self):
        """ Yubico OTP support has always been available in the standard YubiKey. """
        return True

    def have_OATH(self, mode):
        """ OATH HOTP was introduced in YubiKey 2.2. """
        if mode not in ['HOTP']:
            return False
        return (self.version >= (2, 1, 0,))

    def have_challenge_response(self, mode):
        """ Challenge-response was introduced in YubiKey 2.2. """
        if mode not in ['HMAC', 'OTP']:
            return False
        return (self.version >= (2, 2, 0,))

    def have_serial_number(self):
        """ Reading serial number was introduced in YubiKey 2.2, but depends on extflags set too. """
        return (self.version >= (2, 2, 0,))

    def have_ticket_flag(self, flag):
        return flag.is_compatible(model = self.model, version = self.version)

    def have_config_flag(self, flag):
        return flag.is_compatible(model = self.model, version = self.version)

    def have_extended_flag(self, flag):
        return flag.is_compatible(model = self.model, version = self.version)

    def have_extended_scan_code_mode(self):
        return (self.version >= (2, 0, 0,))

    def have_shifted_1_mode(self):
        return (self.version >= (2, 0, 0,))

    def have_configuration_slot(self, slot):
        return (slot in [1, 2])

class YubiKeyUSBHID(YubiKey):
    """
    Class for accessing a YubiKey over USB HID.

    This class is for communicating specifically with standard YubiKeys
    (USB vendor id = 0x1050, product id = 0x10) using USB HID.

    There is another class for the YubiKey NEO BETA, even though that
    product also goes by product id 0x10 for the BETA versions. The
    expectation is that the final YubiKey NEO will have it's own product id.

    Tested with YubiKey versions 1.3 and 2.2.
    """

    model = 'YubiKey'
    description = 'YubiKey (or YubiKey NANO)'

    def __init__(self, debug=False, skip=0):
        """
        Find and connect to a YubiKey (USB HID).

        Attributes :
            skip  -- number of YubiKeys to skip
            debug -- True or False
        """
        YubiKey.__init__(self, debug)
        self._usb_handle = None
        if not self._open(skip):
            raise YubiKeyUSBHIDError('YubiKey USB HID initialization failed')
        self.status()
        self.capabilities = \
            YubiKeyUSBHIDCapabilities(model = self.model, \
                                          version = self.version_num(), \
                                          default_answer = False)

    def __del__(self):
        try:
            if self._usb_handle:
                self._close()
        except IOError:
            pass

    def __repr__(self):
        return '<%s instance at %s: YubiKey version %s>' % (
            self.__class__.__name__,
            hex(id(self)),
            self.version()
            )

    def status(self):
        """
        Poll YubiKey for status.
        """
        data = self._read()
        self._status = YubiKeyUSBHIDStatus(data)
        return self._status

    def version_num(self):
        """ Get the YubiKey version as a tuple (major, minor, build). """
        return self._status.ykver()

    def version(self):
        """ Get the YubiKey version. """
        return self._status.version()

    def serial(self, may_block=True):
        """ Get the YubiKey serial number (requires YubiKey 2.2). """
        if not self.capabilities.have_serial_number():
            raise yubikey.YubiKeyVersionError("Serial number unsupported in YubiKey %s" % self.version() )
        return self._read_serial(may_block)

    def challenge_response(self, challenge, mode='HMAC', slot=1, variable=True, may_block=True):
        """ Issue a challenge to the YubiKey and return the response (requires YubiKey 2.2). """
        if not self.capabilities.have_challenge_response(mode):
            raise yubikey.YubiKeyVersionError("%s challenge-response unsupported in YubiKey %s" % (mode, self.version()) )
        return self._challenge_response(challenge, mode, slot, variable, may_block)

    def init_config(self, **kw):
        """ Get a configuration object for this type of YubiKey. """
        return YubiKeyConfigUSBHID(ykver=self.version_num(), \
                                       capabilities = self.capabilities, \
                                       **kw)

    def write_config(self, cfg, slot=1):
        """ Write a configuration to the YubiKey. """
        cfg_req_ver = cfg.version_required()
        if cfg_req_ver > self.version_num():
            raise yubikey.YubiKeyVersionError('Configuration requires YubiKey version %i.%i (this is %s)' % \
                                                  (cfg_req_ver[0], cfg_req_ver[1], self.version()))
        if not self.capabilities.have_configuration_slot(slot):
            raise YubiKeyUSBHIDError("Can't write configuration to slot %i" % (slot))
        return self._write_config(cfg, slot)

    def _read_serial(self, may_block):
        """ Read the serial number from a YubiKey > 2.2. """

        frame = yubikey_frame.YubiKeyFrame(command = _SLOT_DEVICE_SERIAL)
        self._write(frame)
        response = self._read_response(may_block=may_block)
        if not yubico_util.validate_crc16(response[:6]):
            raise YubiKeyUSBHIDError("Read from device failed CRC check")
        # the serial number is big-endian, although everything else is little-endian
        serial = struct.unpack('>lxxx', response)
        return serial[0]

    def _challenge_response(self, challenge, mode, slot, variable, may_block):
        """ Do challenge-response with a YubiKey > 2.0. """
         # Check length and pad challenge if appropriate
        if mode == 'HMAC':
            if len(challenge) > yubikey_defs.SHA1_MAX_BLOCK_SIZE:
                raise yubico_exception.InputError('Mode HMAC challenge too big (%i/%i)' \
                                                      % (yubikey_defs.SHA1_MAX_BLOCK_SIZE, len(challenge)))
            if len(challenge) < yubikey_defs.SHA1_MAX_BLOCK_SIZE:
                pad_with = chr(0x0)
                if variable and challenge[-1] == pad_with:
                    pad_with = chr(0xff)
                challenge = challenge.ljust(yubikey_defs.SHA1_MAX_BLOCK_SIZE, pad_with)
            response_len = yubikey_defs.SHA1_DIGEST_SIZE
        elif mode == 'OTP':
            if len(challenge) != yubikey_defs.UID_SIZE:
                raise yubico_exception.InputError('Mode OTP challenge must be %i bytes (got %i)' \
                                                      % (yubikey_defs.UID_SIZE, len(challenge)))
            challenge = challenge.ljust(yubikey_defs.SHA1_MAX_BLOCK_SIZE, chr(0x0))
            response_len = 16
        else:
            raise yubico_exception.InputError('Invalid mode supplied (%s, valid values are HMAC and OTP)' \
                                                  % (mode))

        try:
            command = _CMD_CHALLENGE[mode][slot]
        except:
            raise yubico_exception.InputError('Invalid slot specified (%s)' % (slot))

        frame = yubikey_frame.YubiKeyFrame(command=command, payload=challenge)
        self._write(frame)
        response = self._read_response(may_block=may_block)
        if not yubico_util.validate_crc16(response[:response_len + 2]):
            raise YubiKeyUSBHIDError("Read from device failed CRC check")
        return response[:response_len]

    def _write_config(self, cfg, slot):
        """ Write configuration to YubiKey. """
        old_pgm_seq = self._status.pgm_seq
        frame = cfg.to_frame(slot=slot)
        self._debug("Writing %s frame :\n%s\n" % \
                        (yubikey_config.command2str(frame.command), cfg))
        self._write(frame)
        self._waitfor_clear(yubikey_defs.SLOT_WRITE_FLAG)
        # make sure we have a fresh pgm_seq value
        self.status()
        self._debug("Programmed slot %i, sequence %i -> %i\n" % (slot, old_pgm_seq, self._status.pgm_seq))
        if self._status.pgm_seq != old_pgm_seq + 1:
            raise YubiKeyUSBHIDError('YubiKey programming failed (seq %i not increased (%i))' % \
                                         (old_pgm_seq, self._status.pgm_seq))

    def _read_response(self, may_block=False):
        """ Wait for a response to become available, and read it. """
        # wait for response to become available
        res = self._waitfor_set(yubikey_defs.RESP_PENDING_FLAG, may_block)[:7]
        # continue reading while response pending is set
        while True:
            this = self._read()
            flags = ord(this[7])
            if flags & yubikey_defs.RESP_PENDING_FLAG:
                seq = flags & 0b00011111
                if res and (seq == 0):
                    break
                res += this[:7]
            else:
                break
        self._write_reset()
        return res

    def _read(self):
        """ Read a USB HID feature report from the YubiKey. """
        request_type = _USB_TYPE_CLASS | _USB_RECIP_INTERFACE | _USB_ENDPOINT_IN
        value = _REPORT_TYPE_FEATURE << 8	# apparently required for YubiKey 1.3.2, but not 2.2.x
        recv = self._usb_handle.controlMsg(request_type,
                                          _HID_GET_REPORT,
                                          _FEATURE_RPT_SIZE,
                                          value = value,
                                          timeout = _USB_TIMEOUT_MS)
        if len(recv) != _FEATURE_RPT_SIZE:
            self._debug("Failed reading %i bytes (got %i) from USB HID YubiKey.\n"
                        % (_FEATURE_RPT_SIZE, recv))
            raise YubiKeyUSBHIDError('Failed reading from USB HID YubiKey')
        data = ''.join(chr(c) for c in recv)
        self._debug("READ  : %s" % (yubico_util.hexdump(data, colorize=True)))
        return data

    def _write(self, frame):
        """
        Write a YubiKeyFrame to the USB HID.

        Includes polling for YubiKey readiness before each write.
        """
        for data in frame.to_feature_reports(debug=self.debug):
            debug_str = None
            if self.debug:
                (data, debug_str) = data
            # first, we ensure the YubiKey will accept a write
            self._waitfor_clear(yubikey_defs.SLOT_WRITE_FLAG)
            self._raw_write(data, debug_str)
        return True

    def _write_reset(self):
        """
        Reset read mode by issuing a dummy write.
        """
        data = '\x00\x00\x00\x00\x00\x00\x00\x8f'
        self._raw_write(data)
        self._waitfor_clear(yubikey_defs.SLOT_WRITE_FLAG)
        return True

    def _raw_write(self, data, debug_str = None):
        """
        Write data to YubiKey.
        """
        if self.debug:
            if not debug_str:
                debug_str = ''
            hexdump = yubico_util.hexdump(data, colorize=True)[:-1] # strip LF
            self._debug("WRITE : %s %s\n" % (hexdump, debug_str))
        request_type = _USB_TYPE_CLASS | _USB_RECIP_INTERFACE | _USB_ENDPOINT_OUT
        value = _REPORT_TYPE_FEATURE << 8	# apparently required for YubiKey 1.3.2, but not 2.2.x
        sent = self._usb_handle.controlMsg(request_type,
                                          _HID_SET_REPORT,
                                          data,
                                          value = value,
                                          timeout = _USB_TIMEOUT_MS)
        if sent != _FEATURE_RPT_SIZE:
            self.debug("Failed writing %i bytes (wrote %i) to USB HID YubiKey.\n"
                       % (_FEATURE_RPT_SIZE, sent))
            raise YubiKeyUSBHIDError('Failed talking to USB HID YubiKey')
        return sent

    def _waitfor_clear(self, mask, may_block=False):
        """
        Wait for the YubiKey to turn OFF the bits in 'mask' in status responses.

        Returns the 8 bytes last read.
        """
        return self._waitfor('nand', mask, may_block)

    def _waitfor_set(self, mask, may_block=False):
        """
        Wait for the YubiKey to turn ON the bits in 'mask' in status responses.

        Returns the 8 bytes last read.
        """
        return self._waitfor('and', mask, may_block)

    def _waitfor(self, mode, mask, may_block, timeout=2):
        """
        Wait for the YubiKey to either turn ON or OFF certain bits in the status byte.

        mode is either 'and' or 'nand'
        timeout is a number of seconds (precision about ~0.5 seconds)
        """
        finished = False
        sleep = 0.01
        # After six sleeps, we've slept 0.64 seconds.
        wait_num = (timeout * 2) - 1 + 6
        resp_timeout = False	# YubiKey hasn't indicated RESP_TIMEOUT (yet)
        while not finished:
            this = self._read()
            flags = ord(this[7])

            if flags & yubikey_defs.RESP_TIMEOUT_WAIT_FLAG:
                if not resp_timeout:
                    resp_timeout = True
                    seconds_left = flags & yubikey_defs.RESP_TIMEOUT_WAIT_MASK
                    self._debug("Device indicates RESP_TIMEOUT (%i seconds left)\n" \
                                    % (seconds_left))
                    if may_block:
                        # calculate new wait_num - never more than 20 seconds
                        seconds_left = min(20, seconds_left)
                        wait_num = (seconds_left * 2) - 1 + 6

            if mode is 'nand':
                if not flags & mask == mask:
                    finished = True
                else:
                    self._debug("Status %s (0x%x) has not cleared bits %s (0x%x)\n"
                                % (bin(flags), flags, bin(mask), mask))
            elif mode is 'and':
                if flags & mask == mask:
                    finished = True
                else:
                    self._debug("Status %s (0x%x) has not set bits %s (0x%x)\n"
                                % (bin(flags), flags, bin(mask), mask))
            else:
                assert()

            if not finished:
                wait_num -= 1
                if wait_num == 0:
                    if mode is 'nand':
                        reason = 'Timed out waiting for YubiKey to clear status 0x%x' % mask
                    else:
                        reason = 'Timed out waiting for YubiKey to set status 0x%x' % mask
                    raise yubikey.YubiKeyTimeout(reason)
                time.sleep(sleep)
                sleep = min(sleep + sleep, 0.5)
            else:
                return this

    def _open(self, skip=0):
        """ Perform HID initialization """
        usb_device = self._get_usb_device(skip)

        if usb_device:
            usb_conf = usb_device.configurations[0]
            self._usb_int = usb_conf.interfaces[0][0]
        else:
            raise YubiKeyUSBHIDError('No USB YubiKey found')

        try:
            self._usb_handle = usb_device.open()
            self._usb_handle.detachKernelDriver(0)
        except Exception, error:
            if 'could not detach kernel driver from interface' in str(error):
                self._debug('The in-kernel-HID driver has already been detached\n')
            else:
                self._debug("detachKernelDriver not supported!")

        self._usb_handle.setConfiguration(1)
        self._usb_handle.claimInterface(self._usb_int)
        return True

    def _close(self):
        """
        Release the USB interface again.
        """
        self._usb_handle.releaseInterface()
        try:
            # If we're using PyUSB >= 1.0 we can re-attach the kernel driver here.
            self._usb_handle.dev.attach_kernel_driver(0)
        except:
            pass
        self._usb_int = None
        self._usb_handle = None
        return True

    def _get_usb_device(self, skip=0):
        """
        Get YubiKey USB device.

        Optionally allows you to skip n devices, to support multiple attached YubiKeys.
        """
        try:
            # PyUSB >= 1.0, this is a workaround for a problem with libusbx
            # on Windows.
            import usb.core
            import usb.legacy
            devices = [usb.legacy.Device(d) for d in usb.core.find(
                find_all=True, idVendor=_YUBICO_VID)]
        except ImportError:
            # Using PyUsb < 1.0.
            import usb
            devices = [d for bus in usb.busses() for d in bus.devices]
        for device in devices:
            if device.idVendor == _YUBICO_VID:
                if device.idProduct in [_YUBIKEY_PID, _NEO_OTP_PID, _NEO_OTP_CCID_PID]:
                    if skip == 0:
                        return device
                    skip -= 1
        return None

    def _debug(self, out, print_prefix=True):
        """ Print out to stderr, if debugging is enabled. """
        if self.debug:
            if print_prefix:
                pre = self.__class__.__name__
                if hasattr(self, 'debug_prefix'):
                    pre = getattr(self, 'debug_prefix')
                sys.stderr.write("%s: " % (self.__class__.__name__))
            sys.stderr.write(out)

class YubiKeyUSBHIDStatus():
    """ Class to represent the status information we get from the YubiKey. """

    CONFIG1_VALID = 0x01 # Bit in touchLevel indicating that configuration 1 is valid (from firmware 2.1)
    CONFIG2_VALID = 0x02 # Bit in touchLevel indicating that configuration 2 is valid (from firmware 2.1)

    def __init__(self, data):
        # From ykdef.h :
        #
        # struct status_st {
        #        unsigned char versionMajor;     /* Firmware version information */
        #        unsigned char versionMinor;
        #        unsigned char versionBuild;
        #        unsigned char pgmSeq;           /* Programming sequence number. 0 if no valid configuration */
        #        unsigned short touchLevel;      /* Level from touch detector */
        # };
        fmt = '<x BBB B H B'
        self.version_major, \
            self.version_minor, \
            self.version_build, \
            self.pgm_seq, \
            self.touch_level, \
            self.flags = struct.unpack(fmt, data)

    def __repr__(self):
        valid_str = ''
        flags_str = ''
        if self.ykver() >= (2,1,0):
            valid_str = ", valid=%s" % (self.valid_configs())
        if self.flags:
            flags_str = " (flags 0x%x)" % (self.flags)
        return '<%s instance at %s: YubiKey version %s, pgm_seq=%i, touch_level=%i%s%s>' % (
            self.__class__.__name__,
            hex(id(self)),
            self.version(),
            self.pgm_seq,
            self.touch_level,
            valid_str,
            flags_str,
            )


    def ykver(self):
        """ Returns a tuple with the (major, minor, build) version of the YubiKey firmware. """
        return (self.version_major, self.version_minor, self.version_build)

    def version(self):
        """ Return the YubiKey firmware version as a string. """
        version = "%d.%d.%d" % (self.ykver())
        return version

    def valid_configs(self):
        """ Return a list of slots having a valid configurtion. Requires firmware 2.1. """
        if self.ykver() < (2,1,0):
            raise YubiKeyUSBHIDError('Valid configs unsupported in firmware %s' % (self.version()))
        res = []
        if self.touch_level & self.CONFIG1_VALID == self.CONFIG1_VALID:
            res.append(1)
        if self.touch_level & self.CONFIG2_VALID == self.CONFIG2_VALID:
            res.append(2)
        return res

class YubiKeyConfigUSBHID(yubikey_config.YubiKeyConfig):
    """
    Configuration class for USB HID YubiKeys.
    """
    def __init__(self, ykver, capabilities = None, **kw):
        yubikey_config.YubiKeyConfig.__init__(self, ykver = ykver, capabilities = capabilities, **kw)
        return None

########NEW FILE########
