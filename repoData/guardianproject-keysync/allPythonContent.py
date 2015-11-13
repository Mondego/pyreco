__FILENAME__ = astng_hashlib
#
# started from http://www.logilab.org/blogentry/78354
#

from logilab.astng import MANAGER
from logilab.astng.builder import ASTNGBuilder

def hashlib_transform(module):
    if module.name == 'hashlib':
        fake = ASTNGBuilder(MANAGER).string_build('''

class fakehash(object):
  digest_size = -1
  def __init__(self, value): pass
  def digest(self):
    return u''
  def hexdigest(self):
    return u''
  def update(self, value): pass

class md5(fakehash):
  pass

class sha1(fakehash):
  pass

class sha256(fakehash):
  pass

''')
        for hashfunc in ('sha256', 'sha1', 'md5'):
            module.locals[hashfunc] = fake.locals[hashfunc]

def register(linter):
    """called when loaded by pylint --load-plugins, register our tranformation
    function here
    """
    MANAGER.register_transformer(hashlib_transform)


########NEW FILE########
__FILENAME__ = adium
#!/usr/bin/env python2.6
# -*- coding: utf-8 -*-

from __future__ import print_function
import os
import platform
import plistlib
import sys

if __name__ == '__main__':
    sys.path.insert(0, "../") # so the main() test suite can find otrapps module
import otrapps.util
from otrapps.otr_private_key import OtrPrivateKeys
from otrapps.otr_fingerprints import OtrFingerprints

class AdiumProperties():

    path = os.path.expanduser('~/Library/Application Support/Adium 2.0/Users/Default')
    accountsfile = 'Accounts.plist'
    keyfile = 'otr.private_key'
    fingerprintfile = 'otr.fingerprints'
    files = (accountsfile, keyfile, fingerprintfile)

    @staticmethod
    def _get_accounts_from_plist(settingsdir):
        '''get dict of accounts from Accounts.plist'''
        # convert index numbers used for the name into the actual account name
        accountsfile = os.path.join(settingsdir, 'Accounts.plist')
        print('accountsfile: ', end=' ')
        print(accountsfile)
        if not os.path.exists(accountsfile):
            oldaccountsfile = accountsfile
            accountsfile = os.path.join(AdiumProperties.path, AdiumProperties.accountsfile)
            if platform.system() == 'Darwin' and os.path.exists(accountsfile):
                print('Adium WARNING: "' + oldaccountsfile + '" does not exist! Using:')
                print('\t"' + accountsfile + '"')
            else:
                print('Adium ERROR: No usable Accounts.plist file found, cannot create Adium files!')
                return []
        # make sure the plist is in XML format, not binary,
        # this should be converted to use python-biplist.
        if platform.system() == 'Darwin':
            os.system("plutil -convert xml1 '" + accountsfile + "'")
        return plistlib.readPlist(accountsfile)['Accounts']

    @staticmethod
    def parse(settingsdir=None):
        if settingsdir == None:
            settingsdir = AdiumProperties.path

        kf = os.path.join(settingsdir, AdiumProperties.keyfile)
        if os.path.exists(kf):
            keydict = OtrPrivateKeys.parse(kf)
        else:
            keydict = dict()

        accounts = AdiumProperties._get_accounts_from_plist(settingsdir)
        newkeydict = dict()
        for adiumIndex, key in keydict.items():
            for account in accounts:
                if account['ObjectID'] == key['name']:
                    name = account['UID']
                    key['name'] = name
                    newkeydict[name] = key
        keydict = newkeydict

        fpf = os.path.join(settingsdir, AdiumProperties.fingerprintfile)
        if os.path.exists(fpf):
            otrapps.util.merge_keydicts(keydict, OtrFingerprints.parse(fpf))

        return keydict

    @staticmethod
    def write(keydict, savedir='./'):
        if not os.path.exists(savedir):
            raise Exception('"' + savedir + '" does not exist!')

        # need when converting account names back to Adium's account index number
        accountsplist = AdiumProperties._get_accounts_from_plist(savedir)

        kf = os.path.join(savedir, AdiumProperties.keyfile)
        adiumkeydict = dict()
        for name, key in keydict.items():
            name = key['name']
            for account in accountsplist:
                if account['UID'] == name:
                    key['name'] = account['ObjectID']
                    adiumkeydict[name] = key
        OtrPrivateKeys.write(keydict, kf)

        accounts = []
        for account in accountsplist:
            accounts.append(account['ObjectID'])
        fpf = os.path.join(savedir, AdiumProperties.fingerprintfile)
        OtrFingerprints.write(keydict, fpf, accounts)


if __name__ == '__main__':

    import pprint

    print('Adium stores its files in ' + AdiumProperties.path)

    if len(sys.argv) == 2:
        settingsdir = sys.argv[1]
    else:
        settingsdir = '../tests/adium'
    keydict = AdiumProperties.parse(settingsdir)
    pprint.pprint(keydict)

    AdiumProperties.write(keydict, '/tmp')

########NEW FILE########
__FILENAME__ = chatsecure
#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''a module for reading and writing ChatSecure's OTR key data'''

from __future__ import print_function
import hashlib
import os
import sys
import pyjavaproperties
import subprocess
import tempfile

if __name__ == '__main__':
    sys.path.insert(0, "../") # so the main() test suite can find otrapps module
import otrapps.util

class ChatSecureProperties():

    path = '/data/data/info.guardianproject.otr.app.im/files/otr_keystore'
    keyfile = 'otr_keystore'
    encryptedkeyfile = keyfile + '.ofcaes'
    files = (keyfile, encryptedkeyfile)

    password = None

    @staticmethod
    def parse(filename):
        '''parse the given file into the standard keydict'''
        # the parsing and generation is done in separate passes so that
        # multiple properties are combined into a single keydict per account,
        # containing all of the fields
        p = pyjavaproperties.Properties()
        p.load(open(filename))
        parsed = []
        for item in p.items():
            propkey = item[0]
            if propkey.endswith('.publicKey'):
                id = '.'.join(propkey.split('.')[0:-1])
                parsed.append(('public-key', id, item[1]))
            elif propkey.endswith('.publicKey.verified'):
                keylist = propkey.split('.')
                fingerprint = keylist[-3]
                id = '.'.join(keylist[0:-3])
                parsed.append(('verified', id, fingerprint))
            elif propkey.endswith('.privateKey'):
                id = '.'.join(propkey.split('.')[0:-1])
                parsed.append(('private-key', id, item[1]))
        # create blank keys for all IDs
        keydict = dict()
        for keydata in parsed:
            name = keydata[1]
            if not name in keydict:
                keydict[name] = dict()
                keydict[name]['name'] = name
                keydict[name]['protocol'] = 'prpl-jabber'
            if keydata[0] == 'private-key':
                cleaned = keydata[2].replace('\\n', '')
                numdict = otrapps.util.ParsePkcs8(cleaned)
                for num in ('g', 'p', 'q', 'x'):
                    keydict[name][num] = numdict[num]
            elif keydata[0] == 'verified':
                keydict[name]['verification'] = 'verified'
                fingerprint = keydata[2].lower()
                otrapps.util.check_and_set(keydict[name], 'fingerprint', fingerprint)
            elif keydata[0] == 'public-key':
                cleaned = keydata[2].replace('\\n', '')
                numdict = otrapps.util.ParseX509(cleaned)
                for num in ('y', 'g', 'p', 'q'):
                    keydict[name][num] = numdict[num]
                fingerprint = otrapps.util.fingerprint((numdict['y'], numdict['g'], numdict['p'], numdict['q']))
                otrapps.util.check_and_set(keydict[name], 'fingerprint', fingerprint)
        return keydict

    @staticmethod
    def write(keydict, savedir, password=None):
        '''given a keydict, generate a chatsecure file in the savedir'''
        p = pyjavaproperties.Properties()
        for name, key in keydict.items():
            # only include XMPP keys, since ChatSecure only supports XMPP
            # accounts, so we avoid spreading private keys around
            if key['protocol'] == 'prpl-jabber' or key['protocol'] == 'prpl-bonjour':
                if 'y' in key:
                    p.setProperty(key['name'] + '.publicKey', otrapps.util.ExportDsaX509(key))
                if 'x' in key:
                    if not password:
                        h = hashlib.sha256()
                        h.update(os.urandom(16)) # salt
                        h.update(bytes(key['x']))
                        password = h.digest().encode('base64')
                    p.setProperty(key['name'] + '.privateKey', otrapps.util.ExportDsaPkcs8(key))
            if 'fingerprint' in key:
                p.setProperty(key['name'] + '.fingerprint', key['fingerprint'])
            if 'verification' in key and key['verification'] != None:
                p.setProperty(key['name'] + '.' + key['fingerprint'].lower()
                              + '.publicKey.verified', 'true')
        fd, filename = tempfile.mkstemp()
        f = os.fdopen(fd, 'w')
        p.store(f)

        # if there is no password, then one has not been set, or there
        # are not private keys included in the file, so its a lower
        # risk file. Encryption only needs to protect the meta data,
        # not the private keys.  Therefore, its not as bad to generate
        # a "random" password here
        if not password:
            password = os.urandom(32).encode('base64')

        # create passphrase file from the first private key
        cmd = ['openssl', 'aes-256-cbc', '-pass', 'stdin', '-in', filename,
               '-out', os.path.join(savedir, 'otr_keystore.ofcaes')]
        p = subprocess.Popen(cmd, stdin=subprocess.PIPE,
                             stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        ChatSecureProperties.password = password
        print((p.communicate(password)))


#------------------------------------------------------------------------------#
# for testing from the command line:
def main(argv):
    import pprint

    print('ChatSecure stores its files in ' + ChatSecureProperties.path)

    if len(sys.argv) == 2:
        settingsfile = sys.argv[1]
    else:
        settingsfile = '../tests/chatsecure/otr_keystore'

    p = ChatSecureProperties.parse(settingsfile)
    print('----------------------------------------')
    pprint.pprint(p)
    print('----------------------------------------')

if __name__ == "__main__":
    main(sys.argv[1:])

########NEW FILE########
__FILENAME__ = errors
#!/usr/bin/python2.4
#
# Copyright 2008 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Contains hierarchy of all possible exceptions thrown by Keyczar.

@author: arkajit.dey@gmail.com (Arkajit Dey)
"""

class KeyczarError(Exception):
    """Indicates exceptions raised by a Keyczar class."""

class BadVersionError(KeyczarError):
    """Indicates a bad version number was received."""

    def __init__(self, version):
        KeyczarError.__init__(self,
                              "Received a bad version number: " + str(version))

class Base64DecodingError(KeyczarError):
    """Indicates an error while performing Base 64 decoding."""

class InvalidSignatureError(KeyczarError):
    """Indicates an invalid ciphertext signature."""

    def __init__(self):
        KeyczarError.__init__(self, "Invalid ciphertext signature")

class KeyNotFoundError(KeyczarError):
    """Indicates a key with a certain hash id was not found."""

    def __init__(self, hash):
        KeyczarError.__init__(self,
                              "Key with hash identifier %s not found." % hash)

class ShortCiphertextError(KeyczarError):
    """Indicates a ciphertext too short to be valid."""

    def __init__(self, length):
        KeyczarError.__init__(self,
                "Input of length %s is too short to be valid ciphertext." % length)

class ShortSignatureError(KeyczarError):
    """Indicates a signature too short to be valid."""

    def __init__(self, length):
        KeyczarError.__init__(self,
                  "Input of length %s is too short to be valid signature." % length)

class NoPrimaryKeyError(KeyNotFoundError):
    """Indicates missing primary key."""

    def __init__(self):
        KeyczarError.__init__(self, "No primary key found")

########NEW FILE########
__FILENAME__ = gajim
#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''a module for reading and writing Gajim's OTR key data'''

from __future__ import print_function
import os
import glob
import platform
import sys
import re
import collections

import potr

if __name__ == '__main__':
    sys.path.insert(0, "../")  # so the main() test suite can find otrapps module

import otrapps.util
from otrapps.otr_fingerprints import OtrFingerprints

# the private key is stored in ~/.local/share/gajim/_SERVERNAME_.key_file
# the fingerprints are stored in ~/.local/share/gajim/_SERVERNAME_.fpr
# the accounts are stored in ~/.config/gajim/config


class GajimProperties():

    if platform.system() == 'Windows':
        path = os.path.expanduser('~/Application Data/Gajim')
        accounts_path = '???'
    else:
        path = os.path.expanduser('~/.local/share/gajim')
        accounts_path = os.path.expanduser('~/.config/gajim')

    @staticmethod
    def _parse_account_config(accounts_path):
        """
        Crudely parses the dot-style config syntax of gajim's config file
        """
        if accounts_path is None:
            accounts_path = GajimProperties.accounts_path

        accounts_config = os.path.join(accounts_path, 'config')

        keys = ['name', 'hostname', 'resource']
        patterns = []
        for key in keys:
            # matches lines like:
            #  accounts.guardianproject.info.hostname = "guardianproject.info"
            patterns.append((key, re.compile('accounts\.(.*)\.%s = (.*)' % key)))

        accounts = collections.defaultdict(dict)
        for line in open(accounts_config, 'r'):
            for key, pattern in patterns:
                for match in re.finditer(pattern, line):
                    accounts[match.groups()[0]][key] = match.groups()[1]

        return accounts

    @staticmethod
    def parse(settingsdir=None):
        if settingsdir is None:
            settingsdir = GajimProperties.path
            accounts_config = GajimProperties.accounts_path
        else:
            accounts_config = settingsdir

        keydict = dict()
        for fpf in glob.glob(os.path.join(settingsdir, '*.fpr')):
            print('Reading in ' + fpf)
            keys = OtrFingerprints.parse(fpf)

            # replace gajim's 'xmpp' protocol with 'prpl-jabber' that we use in keysync
            for key, value in keys.items():
                value['protocol'] = 'prpl-jabber'
                keys[key] = value

            otrapps.util.merge_keydicts(keydict, keys)

        accounts = GajimProperties._parse_account_config(accounts_config)

        for key_file in glob.glob(os.path.join(settingsdir, '*.key3')):
            account_name = os.path.splitext(os.path.basename(key_file))[0]
            if not account_name in accounts.keys():
                print("ERROR found %s not in the account list", key_file)
                continue
            with open(key_file, 'rb') as key_file:
                name = '%s@%s' % (accounts[account_name]['name'],
                                  accounts[account_name]['hostname'])
                if name in keydict:
                    key = keydict[name]
                else:
                    key = dict()
                    key['name'] = name
                key['protocol'] = 'prpl-jabber'
                key['resource'] = accounts[account_name]['resource']

                pk = potr.crypt.PK.parsePrivateKey(key_file.read())[0]
                keydata = ['y', 'g', 'p', 'q', 'x']
                for data in keydata:
                    key[data] = getattr(pk.priv, data)

                key['fingerprint'] = otrapps.util.fingerprint((key['y'], key['g'],
                                                               key['p'], key['q']))

                keydict[key['name']] = key

        return keydict

    @staticmethod
    def write(keys, savedir):
        if not os.path.exists(savedir):
            raise Exception('"' + savedir + '" does not exist!')


#------------------------------------------------------------------------------#
# for testing from the command line:
def main(argv):
    import pprint

    print('Gajim stores its files in ' + GajimProperties.path)

    if len(sys.argv) == 2:
        settingsdir = sys.argv[1]
    else:
        settingsdir = '../tests/gajim'

    keydict = GajimProperties.parse(settingsdir)
    print('----------------------------------------')
    pprint.pprint(keydict)
    print('----------------------------------------')
    GajimProperties.write(keydict, '/tmp')

if __name__ == "__main__":
    main(sys.argv[1:])

########NEW FILE########
__FILENAME__ = gnupg
#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function
import os
import sys
import pgpdump


class GnuPGProperties():

    path = os.path.expanduser('~/.gnupg')
    secring = 'secring.gpg'
    pubring = 'pubring.gpg'
    files = (secring, pubring)

    @staticmethod
    def parse(settingsdir=None):
        if settingsdir == None:
            settingsdir = GnuPGProperties.path

        secring_file = os.path.join(settingsdir, GnuPGProperties.secring)
        if not os.path.exists(secring_file):
            return dict()
        rawdata = GnuPGProperties.load_data(secring_file)
        try:
            data = pgpdump.BinaryData(rawdata)
        except pgpdump.utils.PgpdumpException, e:
            print("gnupg: %s" % (e))
            return dict()
        packets = list(data.packets())

        names = []
        keydict = dict()
        for packet in packets:
            values = dict()
            if isinstance(packet, pgpdump.packet.SecretSubkeyPacket):
                if packet.pub_algorithm_type == "dsa":
                    values['p'] = packet.prime
                    values['q'] = packet.group_order
                    values['g'] = packet.group_gen
                    values['y'] = packet.key_value
                    values['x'] = packet.exponent_x
                    # the data comes directly from secret key, mark verified
                    values['verification'] = 'verified'
                    values['fingerprint'] = packet.fingerprint
            elif isinstance(packet, pgpdump.packet.UserIDPacket):
                names.append(str(packet.user_email)) # everything is str, not unicode
            if 'fingerprint' in values.keys():
                for name in names:
                    keydict[name] = values
                    keydict[name]['name'] = name
                    keydict[name]['protocol'] = 'prpl-jabber' # assume XMPP for now
        return keydict

    @staticmethod
    def write(keys, savedir):
        print('Writing GnuPG output files is not yet supported!')

    @staticmethod
    def load_data(filename):
        with open(filename, 'rb') as fileobj:
            data = fileobj.read()
        return data


if __name__ == '__main__':

    import pprint

    print('GnuPG stores its files in ' + GnuPGProperties.path)

    if len(sys.argv) == 2:
        settingsdir = sys.argv[1]
    else:
        settingsdir = '../tests/gnupg'

    l = GnuPGProperties.parse(settingsdir)
    pprint.pprint(l)

########NEW FILE########
__FILENAME__ = irssi
#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''a module for reading and writing irssi's OTR key data'''

from __future__ import print_function
import os
import sys

if __name__ == '__main__':
    sys.path.insert(0, "../") # so the main() test suite can find otrapps module
import otrapps.util
from otrapps.otr_private_key import OtrPrivateKeys
from otrapps.otr_fingerprints import OtrFingerprints

class IrssiProperties():

    path = os.path.expanduser('~/.irssi/otr')
    keyfile = 'otr.key'
    fingerprintfile = 'otr.fp'
    files = (keyfile, fingerprintfile)

    @staticmethod
    def parse(settingsdir=None):
        if settingsdir == None:
            settingsdir = IrssiProperties.path

        kf = os.path.join(settingsdir, IrssiProperties.keyfile)
        if os.path.exists(kf):
            keydict = OtrPrivateKeys.parse(kf)
        else:
            keydict = dict()

        fpf = os.path.join(settingsdir, IrssiProperties.fingerprintfile)
        if os.path.exists(fpf):
            otrapps.util.merge_keydicts(keydict, OtrFingerprints.parse(fpf))

        return keydict

    @staticmethod
    def write(keydict, savedir):
        if not os.path.exists(savedir):
            raise Exception('"' + savedir + '" does not exist!')

        kf = os.path.join(savedir, IrssiProperties.keyfile)
        OtrPrivateKeys.write(keydict, kf)

        accounts = []
        # look for all private keys and use them for the accounts list
        for name, key in keydict.items():
            if 'x' in key:
                accounts.append(name)
        fpf = os.path.join(savedir, IrssiProperties.fingerprintfile)
        OtrFingerprints.write(keydict, fpf, accounts)


if __name__ == '__main__':

    import pprint

    print('Irssi stores its files in ' + IrssiProperties.path)

    if len(sys.argv) == 2:
        settingsdir = sys.argv[1]
    else:
        settingsdir = '../tests/irssi'

    keydict = IrssiProperties.parse(settingsdir)
    pprint.pprint(keydict)

    IrssiProperties.write(keydict, '/tmp')

########NEW FILE########
__FILENAME__ = jitsi
#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''a module for reading and writing Jitsi's OTR key data'''

from __future__ import print_function
import os
import platform
import re
import sys
from pyjavaproperties import Properties
from BeautifulSoup import BeautifulSoup

if __name__ == '__main__':
    sys.path.insert(0, "../") # so the main() test suite can find otrapps module
import otrapps.util


# the accounts, private/public keys, and fingerprints are in sip-communicator.properties
# the contacts list is in contactlist.xml

class JitsiProperties():

    if platform.system() == 'Darwin':
        path = os.path.expanduser('~/Library/Application Support/Jitsi')
    elif platform.system() == 'Windows':
        path = os.path.expanduser('~/Application Data/Jitsi')
    else:
        path = os.path.expanduser('~/.jitsi')
    propertiesfile = 'sip-communicator.properties'
    contactsfile = 'contactlist.xml'
    files = (propertiesfile, contactsfile)

    @staticmethod
    def _parse_account_uid(uidstring):
        username, domain, server = uidstring.split(':')[1].split('@')
        return username + '@' + domain

    @staticmethod
    def _convert_protocol_name(protocol):
        if protocol == 'Jabber':
            return 'prpl-jabber'
        elif protocol == 'Google Talk':
            # this should also mark it as the gtalk variant
            return 'prpl-jabber'
        else:
            return 'IMPLEMENTME'

    @staticmethod
    def _parse_account_from_propkey(settingsdir, propkey):
        '''give a Java Properties key, parse out a real account UID and
        protocol, based on what's listed in the contacts file'''
        # jitsi stores the account name in the properties key, so it strips the @ out
        m = re.match('net\.java\.sip\.communicator\.plugin\.otr\.(.*)_publicKey.*', propkey)
        name_from_prop = '.'.join(m.group(1).split('_'))
        # so let's find where the @ was originally placed:
        xml = ''
        for line in open(os.path.join(settingsdir, JitsiProperties.contactsfile), 'r').readlines():
            xml += line
        name = None
        protocol = None
        for e in BeautifulSoup(xml).findAll('contact'):
            if re.match(name_from_prop, e['address']):
                name = e['address']
                protocol = JitsiProperties._convert_protocol_name(e['account-id'].split(':')[0])
                break
        return str(name), protocol


    @staticmethod
    def parse(settingsdir=None):
        if settingsdir == None:
            settingsdir = JitsiProperties.path
        p = Properties()
        p.load(open(os.path.join(settingsdir, JitsiProperties.propertiesfile)))
        keydict = dict()
        for item in p.items():
            propkey = item[0]
            name = ''
            if re.match('net\.java\.sip\.communicator\.impl\.protocol\.jabber\.acc[0-9]+\.ACCOUNT_UID', propkey):
                name = JitsiProperties._parse_account_uid(item[1])
                if name in keydict:
                    key = keydict[name]
                else:
                    key = dict()
                    key['name'] = name
                    key['protocol'] = 'prpl-jabber'
                    keydict[name] = key

                propkey_base = ('net.java.sip.communicator.plugin.otr.'
                                + re.sub('[^a-zA-Z0-9_]', '_', item[1]))
                private_key = p.getProperty(propkey_base + '_privateKey').strip()
                public_key = p.getProperty(propkey_base + '_publicKey').strip()
                numdict = otrapps.util.ParsePkcs8(private_key)
                key['x'] = numdict['x']
                numdict = otrapps.util.ParseX509(public_key)
                for num in ('y', 'g', 'p', 'q'):
                    key[num] = numdict[num]
                key['fingerprint'] = otrapps.util.fingerprint((key['y'], key['g'], key['p'], key['q']))
                verifiedkey = ('net.java.sip.communicator.plugin.otr.'
                               + re.sub('[^a-zA-Z0-9_]', '_', key['name'])
                               + '_publicKey_verified')
                if p.getProperty(verifiedkey).strip() == 'true':
                    key['verification'] = 'verified'
            elif (re.match('net\.java\.sip\.communicator\.plugin\.otr\..*_publicKey_verified', propkey)):
                name, protocol = JitsiProperties._parse_account_from_propkey(settingsdir, propkey)
                if name != None:
                    if name in keydict:
                        key = keydict[name]
                    else:
                        key = dict()
                        key['name'] = name
                        keydict[name] = key
                    if protocol and 'protocol' not in keydict[name]:
                        key['protocol'] = protocol
                    key['verification'] = 'verified'
            # if the protocol name is included in the property name, its a local account with private key
            elif (re.match('net\.java\.sip\.communicator\.plugin\.otr\..*_publicKey', propkey) and not
                  re.match('net\.java\.sip\.communicator\.plugin\.otr\.(Jabber_|Google_Talk_)', propkey)):
                name, ignored = JitsiProperties._parse_account_from_propkey(settingsdir, propkey)
                if name in keydict:
                    key = keydict[name]
                else:
                    key = dict()
                    key['name'] = name
                    key['protocol'] = 'prpl-jabber'
                    keydict[name] = key
                numdict = otrapps.util.ParseX509(item[1])
                for num in ('y', 'g', 'p', 'q'):
                    key[num] = numdict[num]
                key['fingerprint'] = otrapps.util.fingerprint((key['y'], key['g'], key['p'], key['q']))
        return keydict

    @staticmethod
    def write(keydict, savedir):
        if not os.path.exists(savedir):
            raise Exception('"' + savedir + '" does not exist!')

        loadfile = os.path.join(savedir, JitsiProperties.propertiesfile)
        savefile = loadfile
        if not os.path.exists(loadfile) and os.path.exists(JitsiProperties.path):
            print('Jitsi NOTICE: "' + loadfile + '" does not exist! Reading from:')
            loadfile = os.path.join(JitsiProperties.path, JitsiProperties.propertiesfile)
            print('\t"' + loadfile + '"')

        propkey_base = 'net.java.sip.communicator.plugin.otr.'
        p = Properties()
        p.load(open(loadfile))
        for name, key in keydict.items():
            if 'verification' in key and key['verification'] != '':
                verifiedkey = (propkey_base + re.sub('[^a-zA-Z0-9_]', '_', key['name'])
                               + '_publicKey_verified')
                p[verifiedkey] = 'true'
            if 'y' in key:
                pubkey = (propkey_base + re.sub('[^a-zA-Z0-9_]', '_', key['name'])
                          + '_publicKey')
                p.setProperty(pubkey, otrapps.util.ExportDsaX509(key))
            if 'x' in key:
                protocol_id = 'UNKNOWN_'
                domain_id = 'unknown'
                servername = None
                if '@' in key['name']:
                    domainname = key['name'].split('@')[1]
                    domain_id = re.sub('[^a-zA-Z0-9_]', '_', domainname)
                    if domainname == 'chat.facebook.com':
                        protocol_id = 'Facebook_'
                    elif domainname == 'gmail.com' \
                            or domainname == 'google.com' \
                            or domainname == 'googlemail.com':
                        protocol_id = 'Google_Talk_'
                        servername = 'talk_google_com'
                    else:
                        protocol_id = 'Jabber_'
                else:
                    if key['protocol'] == 'prpl-icq':
                        protocol_id = 'ICQ_'
                        domain_id = 'icq_com'
                    elif key['protocol'] == 'prpl-yahoo':
                        protocol_id = 'Yahoo__'
                        domain_id = 'yahoo_com'
                # Writing
                pubkey = (propkey_base + protocol_id + re.sub('[^a-zA-Z0-9_]', '_', key['name'])
                          + '_' + domain_id + '_publicKey')
                p.setProperty(pubkey, otrapps.util.ExportDsaX509(key))
                privkey = (propkey_base + protocol_id + re.sub('[^a-zA-Z0-9_]', '_', key['name'])
                           + '_' + domain_id + '_privateKey')
                p.setProperty(privkey, otrapps.util.ExportDsaPkcs8(key))
		   
                if servername:
                    pubkey = (propkey_base + protocol_id + re.sub('[^a-zA-Z0-9_]', '_', key['name'])
                              + '_' + servername + '_publicKey')
                    p.setProperty(pubkey, otrapps.util.ExportDsaX509(key))
                    privkey = (propkey_base + protocol_id + re.sub('[^a-zA-Z0-9_]', '_', key['name'])
                               + '_' + servername + '_privateKey')
                    p.setProperty(privkey, otrapps.util.ExportDsaPkcs8(key))
		   		
        p.store(open(savefile, 'w'))



#------------------------------------------------------------------------------#
# for testing from the command line:
def main(argv):
    import pprint

    print('Jitsi stores its files in ' + JitsiProperties.path)

    if len(sys.argv) == 2:
        settingsdir = sys.argv[1]
    else:
        settingsdir = '../tests/jitsi'

    p = JitsiProperties.parse(settingsdir)
    print('----------------------------------------')
    pprint.pprint(p)
    print('----------------------------------------')

if __name__ == "__main__":
    main(sys.argv[1:])

########NEW FILE########
__FILENAME__ = otr_fingerprints
#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''a module for reading and writing libotr's public key data'''

from __future__ import print_function
import csv

class OtrFingerprints():

    @staticmethod
    def parse(filename):
        '''parse the otr.fingerprints file and return a list of keydicts'''
        tsv = csv.reader(open(filename, 'r'), delimiter='\t')
        keydict = dict()
        for row in tsv:
            key = dict()
            name = row[0].strip()
            key['name'] = name
            key['protocol'] = row[2].strip()
            key['fingerprint'] = row[3].strip()
            key['verification'] = row[4].strip()
            keydict[name] = key
        return keydict

    @staticmethod
    def _includexmppresource(accounts, resources):
        '''pidgin requires the XMPP Resource in the name of the associated account'''
        returnlist = []
        for account in accounts:
            if account in resources.keys():
                returnlist.append(account + '/' + resources[account])
            else:
                returnlist.append(account + '/' + 'ReplaceMeWithActualXMPPResource')
        return returnlist

    @staticmethod
    def write(keydict, filename, accounts, resources=None):
        if resources:
            accounts = OtrFingerprints._includexmppresource(accounts, resources)
        # we have to use this list 'accounts' rather than the private
        # keys in the keydict in order to support apps like Adium that
        # don't use the actual account ID as the index in the files.
        tsv = csv.writer(open(filename, 'w'), delimiter='\t')
        for name, key in keydict.items():
            if 'fingerprint' in key:
                for account in accounts:
                    row = [name, account, key['protocol'], key['fingerprint']]
                    if 'verification' in key and key['verification'] != None:
                        row.append(key['verification'])
                    tsv.writerow(row)


if __name__ == '__main__':

    import sys
    import pprint
    keydict = OtrFingerprints.parse(sys.argv[1])
    pprint.pprint(keydict)
    accounts = [ 'gptest@jabber.org', 'gptest@limun.org', 'hans@eds.org']
    OtrFingerprints.write(keydict, 'otr.fingerprints', accounts)

########NEW FILE########
__FILENAME__ = otr_private_key
#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''a module for reading and writing libotr's secret key data'''

from __future__ import print_function
from pyparsing import *
from base64 import b64decode
import sys

if __name__ == '__main__':
    sys.path.insert(0, "../") # so the main() test suite can find otrapps module
import otrapps.util

class OtrPrivateKeys():

    @staticmethod
    def verifyLen(t):
        t = t[0]
        if t.len is not None:
            t1len = len(t[1])
            if t1len != t.len:
                raise ParseFatalException, \
                        "invalid data of length %d, expected %s" % (t1len, t.len)
        return t[1]

    @staticmethod
    def parse_sexp(data):
        '''parse sexp/S-expression format and return a python list'''
        # define punctuation literals
        LPAR, RPAR, LBRK, RBRK, LBRC, RBRC, VBAR = map(Suppress, "()[]{}|")

        decimal = Word("123456789", nums).setParseAction(lambda t: int(t[0]))
        bytes = Word(printables)
        raw = Group(decimal.setResultsName("len") + Suppress(":") + bytes).setParseAction(OtrPrivateKeys.verifyLen)
        token = Word(alphanums + "-./_:*+=")
        base64_ = Group(Optional(decimal, default=None).setResultsName("len") + VBAR
            + OneOrMore(Word( alphanums +"+/=" )).setParseAction(lambda t: b64decode("".join(t)))
            + VBAR).setParseAction(OtrPrivateKeys.verifyLen)

        hexadecimal = ("#" + OneOrMore(Word(hexnums)) + "#")\
                        .setParseAction(lambda t: int("".join(t[1:-1]),16))
        qString = Group(Optional(decimal, default=None).setResultsName("len") +
                                dblQuotedString.setParseAction(removeQuotes)).setParseAction(OtrPrivateKeys.verifyLen)
        simpleString = raw | token | base64_ | hexadecimal | qString

        display = LBRK + simpleString + RBRK
        string_ = Optional(display) + simpleString

        sexp = Forward()
        sexpList = Group(LPAR + ZeroOrMore(sexp) + RPAR)
        sexp << ( string_ | sexpList )

        try:
            sexpr = sexp.parseString(data)
            return sexpr.asList()[0][1:]
        except ParseFatalException, pfe:
            print("Error:", pfe.msg)
            print(pfe.loc)
            print(pfe.markInputline())

    @staticmethod
    def parse(filename):
        '''parse the otr.private_key S-Expression and return an OTR dict'''

        f = open(filename, 'r')
        data = ""
        for line in f.readlines():
            data += line
        f.close()

        sexplist = OtrPrivateKeys.parse_sexp(data)
        keydict = dict()
        for sexpkey in sexplist:
            if sexpkey[0] == "account":
                key = dict()
                name = ''
                for element in sexpkey:
                    # 'name' must be the first element in the sexp or BOOM!
                    if element[0] == "name":
                        if element[1].find('/') > -1:
                            name, resource = element[1].split('/')
                        else:
                            name = element[1].strip()
                            resource = ''
                        key = dict()
                        key['name'] = name.strip()
                        key['resource'] = resource.strip()
                    if element[0] == "protocol":
                        key['protocol'] = element[1]
                    elif element[0] == "private-key":
                        if element[1][0] == 'dsa':
                            key['type'] = 'dsa'
                            for num in element[1][1:6]:
                                key[num[0]] = num[1]
                keytuple = (key['y'], key['g'], key['p'], key['q'])
                key['fingerprint'] = otrapps.util.fingerprint(keytuple)
                keydict[name] = key
        return keydict

    @staticmethod
    def _getaccountname(key, resources):
        if resources:
            # pidgin requires the XMPP Resource in the account name for otr.private_keys
            if key['protocol'] == 'prpl-jabber' and 'x' in key.keys():
                name = key['name']
                if name in resources.keys():
                    return key['name'] + '/' + resources[name]
                else:
                    return key['name'] + '/' + 'ReplaceMeWithActualXMPPResource'
        return key['name']

    @staticmethod
    def write(keydict, filename, resources=None):
        privkeys = '(privkeys\n'
        for name, key in keydict.items():
            if 'x' in key:
                dsa = '  (p #' + ('%0258X' % key['p']) + '#)\n'
                dsa += '  (q #' + ('%042X' % key['q']) + '#)\n'
                dsa += '  (g #' + ('%0258X' % key['g']) + '#)\n'
                dsa += '  (y #' + ('%0256X' % key['y']) + '#)\n'
                dsa += '  (x #' + ('%042X' % key['x']) + '#)\n'
                account = OtrPrivateKeys._getaccountname(key, resources)
                contents = ('(name "' + account + '")\n' +
                             '(protocol ' + key['protocol'] + ')\n' +
                             '(private-key \n (dsa \n' + dsa + '  )\n )\n')
                privkeys += ' (account\n' + contents + ' )\n'
        privkeys += ')\n'
        f = open(filename, 'w')
        f.write(privkeys)
        f.close()

if __name__ == "__main__":
    import sys
    import pprint

    pp = pprint.PrettyPrinter(indent=4)
    pp.pprint(OtrPrivateKeys.parse(sys.argv[1]))

########NEW FILE########
__FILENAME__ = pidgin
#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''a module for reading and writing Pidgin's OTR key data'''

from __future__ import print_function
import os
import sys
from BeautifulSoup import BeautifulSoup

if __name__ == '__main__':
    sys.path.insert(0, "../") # so the main() test suite can find otrapps module
import otrapps.util
from otrapps.otr_private_key import OtrPrivateKeys
from otrapps.otr_fingerprints import OtrFingerprints

class PidginProperties():

    if sys.platform == 'win32':
        path = os.path.join(os.environ.get('APPDATA'), '.purple')
    else:
        path = os.path.expanduser('~/.purple')
    accountsfile = 'accounts.xml'
    keyfile = 'otr.private_key'
    fingerprintfile = 'otr.fingerprints'

    @staticmethod
    def _get_resources(settingsdir):
        '''parse out the XMPP Resource from every Pidgin account'''
        resources = dict()
        accountsfile = os.path.join(settingsdir, PidginProperties.accountsfile)
        if not os.path.exists(accountsfile):
            print('Pidgin WARNING: No usable accounts.xml file found, add XMPP Resource to otr.private_key by hand!')
            return resources
        xml = ''
        for line in open(accountsfile, 'r').readlines():
            xml += line
        for e in BeautifulSoup(xml)(text='prpl-jabber'):
            pidginname = e.parent.parent.find('name').contents[0].split('/')
            name = pidginname[0]
            if len(pidginname) == 2:
                resources[name] = pidginname[1]
            else:
                # Pidgin requires an XMPP Resource, even if its blank
                resources[name] = ''
        return resources

    @staticmethod
    def parse(settingsdir=None):
        if settingsdir == None:
            settingsdir = PidginProperties.path

        kf = os.path.join(settingsdir, PidginProperties.keyfile)
        if os.path.exists(kf):
            keydict = OtrPrivateKeys.parse(kf)
        else:
            keydict = dict()

        fpf = os.path.join(settingsdir, PidginProperties.fingerprintfile)
        if os.path.exists(fpf):
            otrapps.util.merge_keydicts(keydict, OtrFingerprints.parse(fpf))

        resources = PidginProperties._get_resources(settingsdir)
        for name, key in keydict.items():
            if key['protocol'] == 'prpl-jabber' \
                    and 'x' in key.keys() \
                    and name in resources.keys():
                key['resource'] = resources[name]

        return keydict

    @staticmethod
    def write(keydict, savedir):
        if not os.path.exists(savedir):
            raise Exception('"' + savedir + '" does not exist!')

        kf = os.path.join(savedir, PidginProperties.keyfile)
        # Pidgin requires the XMPP resource in the account name field of the
        # OTR private keys file, so fetch it from the existing account info
        if os.path.exists(os.path.join(savedir, PidginProperties.accountsfile)):
            accountsdir = savedir
        elif os.path.exists(os.path.join(PidginProperties.path,
                                         PidginProperties.accountsfile)):
            accountsdir = PidginProperties.path
        else:
            raise Exception('Cannot find "' + PidginProperties.accountsfile
                            + '" in "' + savedir + '"')
        resources = PidginProperties._get_resources(accountsdir)
        OtrPrivateKeys.write(keydict, kf, resources=resources)

        accounts = []
        # look for all private keys and use them for the accounts list
        for name, key in keydict.items():
            if 'x' in key:
                accounts.append(name)
        fpf = os.path.join(savedir, PidginProperties.fingerprintfile)
        OtrFingerprints.write(keydict, fpf, accounts, resources=resources)


if __name__ == '__main__':

    import pprint
    import shutil

    print('Pidgin stores its files in ' + PidginProperties.path)

    if len(sys.argv) == 2:
        settingsdir = sys.argv[1]
    else:
        settingsdir = '../tests/pidgin'

    keydict = PidginProperties.parse(settingsdir)
    pprint.pprint(keydict)

    if not os.path.exists(os.path.join('/tmp', PidginProperties.accountsfile)):
        shutil.copy(os.path.join(settingsdir, PidginProperties.accountsfile),
                    '/tmp')
    PidginProperties.write(keydict, '/tmp')

########NEW FILE########
__FILENAME__ = util
#
# Copyright 2008 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Utility functions for keyczar package modified to use standard base64
format that is commonly used for OTR keys.

@author: arkajit.dey@gmail.com (Arkajit Dey)
@author: hans@eds.org (Hans-Christoph Steiner)
"""

from __future__ import print_function
import base64
import math
import os
import psutil
import re
import signal
import sys
import tempfile
try:
    # Import hashlib if Python >= 2.5
    from hashlib import sha1
except ImportError:
    from sha import sha as sha1

from pyasn1.codec.der import decoder
from pyasn1.codec.der import encoder
from pyasn1.type import univ

from potr.utils import bytes_to_long
from potr.compatcrypto import DSAKey

if __name__ == '__main__':
    sys.path.insert(0, "../") # so the main() test suite can find otrapps module
import otrapps.errors as errors


# gracefully handle it when pymtp doesn't exist
class MTPDummy():
    def detect_devices(self):
        return []
try:
    import pymtp
    mtp = pymtp.MTP()
except:
    mtp = MTPDummy()
# GNOME GVFS mount point for MTP devices

if sys.platform != 'win32':
    # this crashes windows in the ntpath sys lib
    mtp.gvfs_mountpoint = os.path.join(os.getenv('HOME'), '.gvfs', 'mtp')


HLEN = sha1().digest_size  # length of the hash output

#RSAPrivateKey ::= SEQUENCE {
#  version Version,
#  modulus INTEGER, -- n
#  publicExponent INTEGER, -- e
#  privateExponent INTEGER, -- d
#  prime1 INTEGER, -- p
#  prime2 INTEGER, -- q
#  exponent1 INTEGER, -- d mod (p-1)
#  exponent2 INTEGER, -- d mod (q-1)
#  coefficient INTEGER -- (inverse of q) mod p }
#
#Version ::= INTEGER
RSA_OID = univ.ObjectIdentifier('1.2.840.113549.1.1.1')
RSA_PARAMS = ['n', 'e', 'd', 'p', 'q', 'dp', 'dq', 'invq']
DSA_OID = univ.ObjectIdentifier('1.2.840.10040.4.1')
DSA_PARAMS = ['p', 'q', 'g']  # only algorithm params, not public/private keys
SHA1RSA_OID = univ.ObjectIdentifier('1.2.840.113549.1.1.5')
SHA1_OID = univ.ObjectIdentifier('1.3.14.3.2.26')

def ASN1Sequence(*vals):
    seq = univ.Sequence()
    for i in range(len(vals)):
        seq.setComponentByPosition(i, vals[i])
    return seq

def ParseASN1Sequence(seq):
    return [seq.getComponentByPosition(i) for i in range(len(seq))]

#PrivateKeyInfo ::= SEQUENCE {
#  version Version,
#
#  privateKeyAlgorithm PrivateKeyAlgorithmIdentifier,
#  privateKey PrivateKey,
#  attributes [0] IMPLICIT Attributes OPTIONAL }
#
#Version ::= INTEGER
#
#PrivateKeyAlgorithmIdentifier ::= AlgorithmIdentifier
#
#PrivateKey ::= OCTET STRING
#
#Attributes ::= SET OF Attribute
def ParsePkcs8(pkcs8):
    seq = ParseASN1Sequence(decoder.decode(Decode(pkcs8))[0])
    if len(seq) != 3:  # need three fields in PrivateKeyInfo
        raise errors.KeyczarError("Illegal PKCS8 String.")
    version = int(seq[0])
    if version != 0:
        raise errors.KeyczarError("Unrecognized PKCS8 Version")
    [oid, alg_params] = ParseASN1Sequence(seq[1])
    key = decoder.decode(seq[2])[0]
    # Component 2 is an OCTET STRING which is further decoded
    params = {}
    if oid == RSA_OID:
        key = ParseASN1Sequence(key)
        version = int(key[0])
        if version != 0:
            raise errors.KeyczarError("Unrecognized RSA Private Key Version")
        for i in range(len(RSA_PARAMS)):
            params[RSA_PARAMS[i]] = long(key[i+1])
    elif oid == DSA_OID:
        alg_params = ParseASN1Sequence(alg_params)
        for i in range(len(DSA_PARAMS)):
            params[DSA_PARAMS[i]] = long(alg_params[i])
        params['x'] = long(key)
    else:
        raise errors.KeyczarError("Unrecognized AlgorithmIdentifier: not RSA/DSA")
    return params

def ExportRsaPkcs8(params):
    oid = ASN1Sequence(RSA_OID, univ.Null())
    key = univ.Sequence().setComponentByPosition(0, univ.Integer(0))  # version
    for i in range(len(RSA_PARAMS)):
        key.setComponentByPosition(i+1, univ.Integer(params[RSA_PARAMS[i]]))
    octkey = encoder.encode(key)
    seq = ASN1Sequence(univ.Integer(0), oid, univ.OctetString(octkey))
    return Encode(encoder.encode(seq))

def ExportDsaPkcs8(params):
    alg_params = univ.Sequence()
    for i in range(len(DSA_PARAMS)):
        alg_params.setComponentByPosition(i, univ.Integer(params[DSA_PARAMS[i]]))
    oid = ASN1Sequence(DSA_OID, alg_params)
    octkey = encoder.encode(univ.Integer(params['x']))
    seq = ASN1Sequence(univ.Integer(0), oid, univ.OctetString(octkey))
    return Encode(encoder.encode(seq))

#NOTE: not full X.509 certificate, just public key info
#SubjectPublicKeyInfo  ::=  SEQUENCE  {
#        algorithm            AlgorithmIdentifier,
#        subjectPublicKey     BIT STRING  }
def ParseX509(x509):
    seq = ParseASN1Sequence(decoder.decode(Decode(x509))[0])
    if len(seq) != 2:  # need two fields in SubjectPublicKeyInfo
        raise errors.KeyczarError("Illegal X.509 String.")
    [oid, alg_params] = ParseASN1Sequence(seq[0])
    binstring = seq[1].prettyPrint()[1:-2]
    pubkey = decoder.decode(univ.OctetString(BinToBytes(binstring.replace("'", ""))))[0]
    # Component 1 should be a BIT STRING, get raw bits by discarding extra chars,
    # then convert to OCTET STRING which can be ASN.1 decoded
    params = {}
    if oid == RSA_OID:
        [params['n'], params['e']] = [long(x) for x in ParseASN1Sequence(pubkey)]
    elif oid == DSA_OID:
        vals = [long(x) for x in ParseASN1Sequence(alg_params)]
        for i in range(len(DSA_PARAMS)):
            params[DSA_PARAMS[i]] = vals[i]
        params['y'] = long(pubkey)
    else:
        raise errors.KeyczarError("Unrecognized AlgorithmIdentifier: not RSA/DSA")
    return params

def ExportRsaX509(params):
    oid = ASN1Sequence(RSA_OID, univ.Null())
    key = ASN1Sequence(univ.Integer(params['n']), univ.Integer(params['e']))
    binkey = BytesToBin(encoder.encode(key))
    pubkey = univ.BitString("'%s'B" % binkey)  # needs to be a BIT STRING
    seq = ASN1Sequence(oid, pubkey)
    return Encode(encoder.encode(seq))

def ExportDsaX509(params):
    alg_params = ASN1Sequence(univ.Integer(params['p']),
                              univ.Integer(params['q']),
                              univ.Integer(params['g']))
    oid = ASN1Sequence(DSA_OID, alg_params)
    binkey = BytesToBin(encoder.encode(univ.Integer(params['y'])))
    pubkey = univ.BitString("'%s'B" % binkey)  # needs to be a BIT STRING
    seq = ASN1Sequence(oid, pubkey)
    return Encode(encoder.encode(seq))

def MakeDsaSig(r, s):
    """
    Given the raw parameters of a DSA signature, return a Base64 signature.

    @param r: parameter r of DSA signature
    @type r: long int

    @param s: parameter s of DSA signature
    @type s: long int

    @return: raw byte string formatted as an ASN.1 sequence of r and s
    @rtype: string
    """
    seq = ASN1Sequence(univ.Integer(r), univ.Integer(s))
    return encoder.encode(seq)

def ParseDsaSig(sig):
    """
    Given a raw byte string, return tuple of DSA signature parameters.

    @param sig: byte string of ASN.1 representation
    @type sig: string

    @return: parameters r, s as a tuple
    @rtype: tuple

    @raise KeyczarErrror: if the DSA signature format is invalid
    """
    seq = decoder.decode(sig)[0]
    if len(seq) != 2:
        raise errors.KeyczarError("Illegal DSA signature.")
    r = long(seq.getComponentByPosition(0))
    s = long(seq.getComponentByPosition(1))
    return (r, s)

def MakeEmsaMessage(msg, modulus_size):
    """Algorithm EMSA_PKCS1-v1_5 from PKCS 1 version 2"""
    magic_sha1_header = [0x30, 0x21, 0x30, 0x9, 0x6, 0x5, 0x2b, 0xe, 0x3, 0x2,
                         0x1a, 0x5, 0x0, 0x4, 0x14]
    encoded = "".join([chr(c) for c in magic_sha1_header]) + Hash(msg)
    pad_string = chr(0xFF) * (modulus_size / 8 - len(encoded) - 3)
    return chr(1) + pad_string + chr(0) + encoded

def BinToBytes(bits):
    """Convert bit string to byte string."""
    bits = _PadByte(bits)
    octets = [bits[8*i:8*(i+1)] for i in range(len(bits)/8)]
    bytes = [chr(int(x, 2)) for x in octets]
    return "".join(bytes)

def BytesToBin(bytes):
    """Convert byte string to bit string."""
    return "".join([_PadByte(IntToBin(ord(byte))) for byte in bytes])

def _PadByte(bits):
    """Pad a string of bits with zeros to make its length a multiple of 8."""
    r = len(bits) % 8
    return ((8-r) % 8)*'0' + bits

def IntToBin(n):
    if n == 0 or n == 1:
        return str(n)
    elif n % 2 == 0:
        return IntToBin(n/2) + "0"
    else:
        return IntToBin(n/2) + "1"

def BigIntToBytes(n):
    """Return a big-endian byte string representation of an arbitrary length n."""
    chars = []
    while (n > 0):
        chars.append(chr(n % 256))
        n = n >> 8
    chars.reverse()
    return "".join(chars)

def IntToBytes(n):
    """Return byte string of 4 big-endian ordered bytes representing n."""
    bytes = [m % 256 for m in [n >> 24, n >> 16, n >> 8, n]]
    return "".join([chr(b) for b in bytes])  # byte array to byte string

def BytesToLong(bytes):
    l = len(bytes)
    return long(sum([ord(bytes[i]) * 256**(l - 1 - i) for i in range(l)]))

def Xor(a, b):
    """Return a ^ b as a byte string where a and b are byte strings."""
    # pad shorter byte string with zeros to make length equal
    m = max(len(a), len(b))
    if m > len(a):
        a = PadBytes(a, m - len(a))
    elif m > len(b):
        b = PadBytes(b, m - len(b))
    x = [ord(c) for c in a]
    y = [ord(c) for c in b]
    z = [chr(x[i] ^ y[i]) for i in range(m)]
    return "".join(z)

def PadBytes(bytes, n):
    """Prepend a byte string with n zero bytes."""
    return n * '\x00' + bytes

def TrimBytes(bytes):
    """Trim leading zero bytes."""
    trimmed = bytes.lstrip(chr(0))
    if trimmed == "":  # was a string of all zero bytes
        return chr(0)
    else:
        return trimmed

def RandBytes(n):
    """Return n random bytes."""
    # This function requires at least Python 2.4.
    return os.urandom(n)

def Hash(*inputs):
    """Return a SHA-1 hash over a variable number of inputs."""
    md = sha1()
    for i in inputs:
        md.update(i)
    return md.digest()

def PrefixHash(*inputs):
    """Return a SHA-1 hash over a variable number of inputs."""
    md = sha1()
    for i in inputs:
        md.update(IntToBytes(len(i)))
        md.update(i)
    return md.digest()


def Encode(s):
    """
    Return Base64 encoding of s.

    @param s: string to encode as Base64
    @type s: string

    @return: Base64 representation of s.
    @rtype: string
    """
    return base64.b64encode(str(s))


def Decode(s):
    """
    Return decoded version of given Base64 string. Ignore whitespace.

    @param s: Base64 string to decode
    @type s: string

    @return: original string that was encoded as Base64
    @rtype: string

    @raise Base64DecodingError: If length of string (ignoring whitespace) is one
      more than a multiple of four.
    """
    s = str(s.replace(" ", ""))  # kill whitespace, make string (not unicode)
    d = len(s) % 4
    if d == 1:
        raise errors.Base64DecodingError()
    elif d == 2:
        s += "=="
    elif d == 3:
        s += "="
    return base64.b64decode(s)

def WriteFile(data, loc):
    """
    Writes data to file at given location.

    @param data: contents to be written to file
    @type data: string

    @param loc: name of file to write to
    @type loc: string

    @raise KeyczarError: if unable to write to file because of IOError
    """
    try:
        f = open(loc, "w")
        f.write(data)
        f.close()
    except IOError:
        raise errors.KeyczarError("Unable to write to file %s." % loc)

def ReadFile(loc):
    """
    Read data from file at given location.

    @param loc: name of file to read from
    @type loc: string

    @return: contents of the file
    @rtype: string

    @raise KeyczarError: if unable to read from file because of IOError
    """
    try:
        return open(loc).read()
    except IOError:
        raise errors.KeyczarError("Unable to read file %s." % loc)

def MGF(seed, mlen):
    """
    Mask Generation Function (MGF1) with SHA-1 as hash.

    @param seed: used to generate mask, a byte string
    @type seed: string

    @param mlen: desired length of mask
    @type mlen: integer

    @return: mask, byte string of length mlen
    @rtype: string

    @raise KeyczarError: if mask length too long, > 2^32 * hash_length
    """
    if mlen > 2**32 * HLEN:
        raise errors.KeyczarError("MGF1 mask length too long.")
    output = ""
    for i in range(int(math.ceil(mlen / float(HLEN)))):
        output += Hash(seed, IntToBytes(i))
    return output[:mlen]


def fingerprint(key):
    '''generate the human readable form of the fingerprint as used in OTR'''
    return '{0:040x}'.format(bytes_to_long(DSAKey(key).fingerprint()))


def check_and_set(key, k, v):
    '''
    Check if a key is already in the keydict, check its contents against the
    supplied value.  If the key does not exist, then create a new entry in
    keydict.  If the key exists and has a different value, throw an exception.
    '''
    if k in key:
        if key[k] != v:
            if 'name' in key:
                name = key['name']
            else:
                name = '(unknown)'
            # this should be an Exception so that the GUI can catch it to handle it
            print('"' + k + '" values for "' + name + '" did not match: \n\t"' + str(key[k])
                            + '" != "' + str(v) + '"')
    else:
        key[k] = v

def merge_keys(key1, key2):
    '''merge the second key data into the first, checking for conflicts'''
    for k, v in key2.items():
        check_and_set(key1, k, v)


def merge_keydicts(kd1, kd2):
    '''
    given two keydicts, merge the second one into the first one and report errors
    '''
    for name, key in kd2.items():
        if name in kd1:
            merge_keys(kd1[name], key)
        else:
            kd1[name] = key


def which_apps_are_running(apps):
    '''
    Check the process list to see if any of the specified apps are running.
    It returns a tuple of running apps.
    '''
    running = []
    for pid in psutil.get_pid_list():
        try:
            p = psutil.Process(pid)
        except Exception as e:
            print(e)
            continue
        for app in apps:
            if app == p.name:
                running.append(app)
                print('found: ' + p.name)
            else:
                r = re.compile('.*' + app + '.*', re.IGNORECASE)
                try:
                    for arg in p.cmdline:
                        m = r.match(arg)
                        if m and (p.name == 'python' or p.name == 'java'):
                            running.append(app)
                            break
                except:
                    pass
    return tuple(running)


def killall(app):
    '''
    terminates all instances of an app
    '''
    running = []
    for pid in psutil.get_pid_list():
        p = psutil.Process(pid)
        if app == p.name:
            print('killing: ' + p.name)
            os.kill(pid, signal.SIGKILL)
        else:
            r = re.compile('.*' + app + '.*', re.IGNORECASE)
            try:
                for arg in p.cmdline:
                    m = r.match(arg)
                    if m and (p.name == 'python' or p.name == 'java'):
                        print('killing: ' + p.name)
                        os.kill(pid, signal.SIGKILL)
                        break
            except:
                pass


def _fullcopy(src, dst):
    '''
    A simple full file copy that ignores perms, since MTP doesn't play well
    with them.  shutil.copy() tries to dup perms...
    '''
    with open(src) as f:
        content = f.readlines()
    with open(dst, 'w') as f:
        f.writelines(content)


def make_conffile_backup(filename):
    '''makes a in-place backup of the given config file name'''
    realpath = os.path.realpath(filename) # eliminate symlinks
    s = os.stat(realpath)
    timestamp = s.st_mtime
    _fullcopy(realpath, realpath + '.' +  str(timestamp))


def find_gvfs_destdir():
    '''find the MTP subfolder in gvfs to copy the keystore to'''
    if os.path.exists(mtp.gvfs_mountpoint):
        foundit = False
        # this assumes that gvfs is mounting the MTP device
        if os.path.isdir(os.path.join(mtp.gvfs_mountpoint, 'Internal storage')):
            mtpdir = os.path.join(mtp.gvfs_mountpoint, 'Internal storage')
            foundit = True
        elif os.path.isdir(os.path.join(mtp.gvfs_mountpoint, 'SD card')):
            mtpdir = os.path.join(mtp.gvfs_mountpoint, 'SD card')
            foundit = True
        else:
            # if no standard names, try the first dir we find
            files = os.listdir(mtp.gvfs_mountpoint)
            if len(files) > 0:
                for f in files:
                    fp = os.path.join(mtp.gvfs_mountpoint, f)
                    if os.path.isdir(fp):
                        mtpdir = fp
                        foundit = True
        if foundit:
            return mtpdir


def can_sync_to_device():
    '''checks if an MTP device is mounted, i.e. an Android 4.x device'''
    mtp.devicename = ''
    if sys.platform == 'win32':
        # Right now the win32 'sync' method is to prompt the user to manually
        # copy the file over, so we always return true.
        # https://dev.guardianproject.info/issues/2126
        mtp.devicename = 'Copy the otr_keystore.ofcaes file to your device!'
        return True

    gvfs_destdir = find_gvfs_destdir()
    if gvfs_destdir and os.path.exists(gvfs_destdir):
        # this assumes that gvfs is mounting the MTP device.  gvfs is
        # part of GNOME, but is probably included in other systems too
        mtp.devicename = gvfs_destdir
        return True

    # if all else fails, try pymtp. works on GNU/Linux and Mac OS X at least
    try:
        devices = mtp.detect_devices()
        if len(devices) > 0:
            e = devices[0].device_entry
            mtp.devicename = e.vendor + ' ' + e.product
            return True
        else:
            return False
    except Exception as e:
        print('except ' + str(e))
        return False


def get_keystore_savedir():
    '''get a temp place to write out the encrypted keystore'''
    # first cache the encrypted file store in a local temp dir, then we can
    # separately handle copying it via MTP, gvfs, wmdlib, KIO, etc.
    return tempfile.mkdtemp(prefix='.keysync-')


def sync_file_to_device(filename):
    '''sync the keystore file to the device via whatever the relevant method is'''


#------------------------------------------------------------------------------#
# for testing from the command line:
def main(argv):
    import pprint

    key = dict()
    key['name'] = 'key'
    key['test'] = 'yes, testing'
    try:
        check_and_set(key, 'test', 'no, this should break')
    except Exception as e:
        print('Exception: ', end=' ')
        print(e)
    print(key['test'])
    check_and_set(key, 'test', 'yes, testing')
    print(key['test'])
    check_and_set(key, 'new', 'this is a new value')

    key2 = dict()
    key2['name'] = 'key'
    key2['yat'] = 'yet another test'
    merge_keys(key, key2)
    print('key: ', end=' ')
    pprint.pprint(key)

    # now make trouble again
    key2['test'] = 'yet another breakage'
    try:
        merge_keys(key, key2)
    except Exception as e:
        print('Exception: ', end=' ')
        print(e)

    # now let's try dicts of dicts aka 'keydict'
    keydict = dict()
    keydict['key'] = key
    key3 = dict()
    key3['name'] = 'key'
    key3['protocol'] = 'prpl-jabber'
    key4 = dict()
    key4['name'] = 'key4'
    key4['protocol'] = 'prpl-jabber'
    key4['fingerprint'] = 'gotone'
    key4['teststate'] = 'this one should not be merged'
    key5 = dict()
    key5['name'] = 'key'
    key5['protocol'] = 'prpl-jabber'
    key5['moreinfo'] = 'even more!'
    keydict2 = dict()
    keydict2['key'] = key3
    keydict2['key'] = key5
    keydict2['key4'] = key4
    merge_keydicts(keydict, keydict2)
    pprint.pprint(keydict)

    # one more test
    print('---------------------------')
    key6 = dict()
    key6['name'] = 'key'
    keydict3 = dict()
    keydict3['key'] = key6
    pprint.pprint(keydict3['key'])
    merge_keys(keydict3['key'], key3)
    pprint.pprint(keydict3['key'])
    merge_keys(keydict3['key'], key5)
    pprint.pprint(keydict3['key'])

    sys.path.insert(0, os.path.abspath('..'))
    import otrapps
    print('\n---------------------------')
    print('Which supported apps are currently running:')
    print((which_apps_are_running(otrapps.__all__)))

    print('\n---------------------------')
    print('make backup conf file: ')
    tmpdir = tempfile.mkdtemp(prefix='.keysync-util-test-')
    testfile = os.path.join(tmpdir, 'keysync-util-conffile-backup-test')
    with open(testfile, 'w') as f:
        f.write('this is just a test!\n')
    make_conffile_backup(testfile)
    print('Backed up "%s"' % testfile)

    if can_sync_to_device():
        print('\n---------------------------')
        print('MTP is mounted here:', end=' ')
        print(mtp.devicename)



if __name__ == "__main__":
    main(sys.argv[1:])

########NEW FILE########
__FILENAME__ = xchat
#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''a module for reading and writing Xchat's OTR key data'''

from __future__ import print_function
import os
import sys

if __name__ == '__main__':
    sys.path.insert(0, "../") # so the main() test suite can find otrapps module
import otrapps.util
from otrapps.otr_private_key import OtrPrivateKeys
from otrapps.otr_fingerprints import OtrFingerprints

class XchatProperties():

    path = os.path.expanduser('~/.xchat2/otr')
    keyfile = 'otr.key'
    fingerprintfile = 'otr.fp'
    files = (keyfile, fingerprintfile)

    @staticmethod
    def parse(settingsdir=None):
        if settingsdir == None:
            settingsdir = XchatProperties.path

        kf = os.path.join(settingsdir, XchatProperties.keyfile)
        if os.path.exists(kf):
            keydict = OtrPrivateKeys.parse(kf)
        else:
            keydict = dict()

        fpf = os.path.join(settingsdir, XchatProperties.fingerprintfile)
        if os.path.exists(fpf):
            otrapps.util.merge_keydicts(keydict, OtrFingerprints.parse(fpf))

        return keydict

    @staticmethod
    def write(keydict, savedir):
        if not os.path.exists(savedir):
            raise Exception('"' + savedir + '" does not exist!')

        kf = os.path.join(savedir, XchatProperties.keyfile)
        OtrPrivateKeys.write(keydict, kf)

        accounts = []
        # look for all private keys and use them for the accounts list
        for name, key in keydict.items():
            if 'x' in key:
                accounts.append(name)
        fpf = os.path.join(savedir, XchatProperties.fingerprintfile)
        OtrFingerprints.write(keydict, fpf, accounts)



if __name__ == '__main__':

    import pprint

    print('Xchat stores its files in ' + XchatProperties.path)

    if len(sys.argv) == 2:
        settingsdir = sys.argv[1]
    else:
        settingsdir = '../tests/xchat'

    keydict = XchatProperties.parse(settingsdir)
    pprint.pprint(keydict)

    XchatProperties.write(keydict, '/tmp')

########NEW FILE########
__FILENAME__ = parse-private-key-PKCS#8
#!/usr/bin/python

import pyjavaproperties
import imp

errors = imp.load_source('errors', '../../otrapps/errors.py')
util = imp.load_source('util', '../../otrapps/util.py')

filename = 'dsa-key.properties'
p = pyjavaproperties.Properties()
p.load(open(filename))
for item in p.items():
    if item[0] == 'privateKey':
        privdict = util.ParsePkcs8(item[1])
        print 'privdict: ',
        print privdict
    elif item[0] == 'publicKey':
        pubdict = util.ParseX509(item[1])
        print 'pubdict: ',
        print pubdict

########NEW FILE########
