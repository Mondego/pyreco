__FILENAME__ = auth
"""
from future import django_sha2_support

Monkey-patch SHA-2 support into Django's auth system. If Django ticket #5600
ever gets fixed, this can be removed.


"""
import base64
import hashlib
import os

from django.conf import settings
from django.contrib.auth import models as auth_models

from django_sha2 import get_dynamic_hasher_names


ALGOS = (
    'bcrypt',
    'sha256',
    'sha512',
    'sha512b64',
)


def monkeypatch():
    """
    Monkeypatch authentication backend if one of our backends was selected.
    """

    algo = getattr(settings, 'PWD_ALGORITHM', 'bcrypt')
    if not algo in ALGOS:
        return  # TODO: log a warning?

    # max_length for SHA512 must be at least 156 characters. NB: The DB needs
    # to be fixed separately.
    if algo == 'sha512':
        pwfield = auth_models.User._meta.get_field('password')
        pwfield.max_length = max(pwfield.max_length, 255)  # Need at least 156.

    # Do not import bcrypt stuff unless needed
    if algo == 'bcrypt':
        from django_sha2 import bcrypt_auth

    def set_password(self, raw_password):
        """Wrapper to set strongly hashed password for Django."""
        if raw_password is None:
            self.set_unusable_password()
            return
        if algo != 'bcrypt':
            salt = os.urandom(10).encode('hex')  # Random, 20-digit (hex) salt.
            hsh = get_hexdigest(algo, salt, raw_password)
            self.password = '$'.join((algo, salt, hsh))
        else:
            self.password = bcrypt_auth.create_hash(raw_password)
    set_password_old = auth_models.User.set_password
    auth_models.User.set_password = set_password

    def check_password(self, raw_password):
        """
        Check a raw PW against the DB.

        Checks strong hashes, but falls back to built-in hashes as needed.
        Supports automatic upgrading to stronger hashes.
        """
        hashed_with = self.password.split('$', 1)[0]
        if hashed_with in ['bcrypt', 'hh'] or \
           hashed_with in get_dynamic_hasher_names(settings.HMAC_KEYS):
            matched = bcrypt_auth.check_password(self, raw_password)
        else:
            matched = check_password_old(self, raw_password)

        # Update password hash in DB if out-of-date hash algorithm is used and
        # auto-upgrading is enabled.
        if (matched and getattr(settings, 'PWD_REHASH', True) and
            hashed_with != algo):
            self.set_password(raw_password)
            self.save()

        return matched
    check_password_old = auth_models.User.check_password
    auth_models.User.check_password = check_password

    def get_hexdigest(algorithm, salt, raw_password):
        """Generate SHA-256 or SHA-512 hash (not used for bcrypt)."""
        salt, raw_password = map(lambda s: unicode(s).encode('utf-8'),
                                 (salt, raw_password))
        if algorithm in ('sha256', 'sha512'):
            return getattr(hashlib, algorithm)(salt + raw_password).hexdigest()
        elif algorithm == 'sha512b64':
            return base64.encodestring(hashlib.sha512(
                salt + raw_password).digest())
        else:
            return get_hexdigest_old(algorithm, salt, raw_password)
    get_hexdigest_old = auth_models.get_hexdigest
    auth_models.get_hexdigest = get_hexdigest

monkeypatch()

########NEW FILE########
__FILENAME__ = bcrypt_auth
"""bcrypt and hmac implementation for Django."""
import base64
import hashlib
import logging

import bcrypt
import hmac

from django.conf import settings
from django.contrib.auth.models import get_hexdigest
from django.utils.encoding import smart_str


log = logging.getLogger('django_sha2')


def create_hash(userpwd):
    """Given a password, create a key to be stored in the DB."""
    if not settings.HMAC_KEYS:
        raise ImportError('settings.HMAC_KEYS must not be empty. Read the '
                          'django_sha2 docs!')
    latest_key_id = max(settings.HMAC_KEYS.keys())
    shared_key = settings.HMAC_KEYS[latest_key_id]

    return ''.join((
        'bcrypt', _bcrypt_create(_hmac_create(userpwd, shared_key)),
        '$', latest_key_id))


def check_password(user, raw_password):
    """Given a DB entry and a raw password, check its validity."""

    # Check if the user's password is a "hardened hash".
    if user.password.startswith('hh$'):
        alg, salt, bc_pwd = user.password.split('$', 3)[1:]
        hash = get_hexdigest(alg, salt, raw_password)
        algo_and_hash, key_ver = bc_pwd.rsplit('$', 1)
        try:
            shared_key = settings.HMAC_KEYS[key_ver]
        except KeyError:
            log.info('Invalid shared key version "{0}"'.format(key_ver))
            return False
        bc_value = algo_and_hash[6:]
        hmac_value = _hmac_create('$'.join([alg, salt, hash]), shared_key)

        if _bcrypt_verify(hmac_value, bc_value):
            # Password is a match, convert to bcrypt format.
            user.set_password(raw_password)
            user.save()
            return True

        return False

    # Normal bcrypt password checking.
    algo_and_hash, key_ver = user.password.rsplit('$', 1)
    try:
        shared_key = settings.HMAC_KEYS[key_ver]
    except KeyError:
        log.info('Invalid shared key version "{0}"'.format(key_ver))
        return False
    bc_value = algo_and_hash[algo_and_hash.find('$'):]  # Yes, bcrypt <3s the leading $.
    hmac_value = _hmac_create(raw_password, shared_key)
    matched = _bcrypt_verify(hmac_value, bc_value)

    # Update password hash if HMAC key has since changed.
    if matched and getattr(settings, 'PWD_HMAC_REKEY', True):
        latest_key_id = max(settings.HMAC_KEYS.keys())
        if key_ver != latest_key_id:
            user.set_password(raw_password)
            user.save()

    return matched


def _hmac_create(userpwd, shared_key):
    """Create HMAC value based on pwd and system-local and per-user salt."""
    hmac_value = base64.b64encode(hmac.new(
        smart_str(shared_key), smart_str(userpwd), hashlib.sha512).digest())
    return hmac_value


def _bcrypt_create(hmac_value):
    """Create bcrypt hash."""
    rounds = getattr(settings, 'BCRYPT_ROUNDS', 12)
    # No need for us to create a user salt, bcrypt creates its own.
    bcrypt_value = bcrypt.hashpw(hmac_value, bcrypt.gensalt(int(rounds)))
    return bcrypt_value


def _bcrypt_verify(hmac_value, bcrypt_value):
    """Verify an hmac hash against a bcrypt value."""
    return bcrypt.hashpw(hmac_value, bcrypt_value) == bcrypt_value

########NEW FILE########
__FILENAME__ = hashers
import base64
import hmac
import hashlib
import logging

import bcrypt

from django.conf import settings
from django.contrib.auth.hashers import (BCryptPasswordHasher,
                                         BasePasswordHasher, mask_hash)
from django.utils.crypto import constant_time_compare
from django.utils.encoding import smart_str
from django.utils.datastructures import SortedDict

log = logging.getLogger('common.hashers')

algo_name = lambda hmac_id: 'bcrypt{0}'.format(hmac_id.replace('-', '_'))


def get_hasher(hmac_id):
    """
    Dynamically create password hashers based on hmac_id.

    This class takes the hmac_id corresponding to an HMAC_KEY and creates a
    password hasher class based off of it. This allows us to use djangos
    built-in updating mechanisms to automatically update the HMAC KEYS.
    """
    dash_hmac_id = hmac_id.replace('_', '-')

    class BcryptHMACPasswordHasher(BCryptPasswordHasher):
        algorithm = algo_name(hmac_id)
        rounds = getattr(settings, 'BCRYPT_ROUNDS', 12)

        def encode(self, password, salt):

            shared_key = settings.HMAC_KEYS[dash_hmac_id]

            hmac_value = self._hmac_create(password, shared_key)
            bcrypt_value = bcrypt.hashpw(hmac_value, salt)
            return '{0}{1}${2}'.format(
                self.algorithm,
                bcrypt_value,
                dash_hmac_id)

        def verify(self, password, encoded):
            algo_and_hash, key_ver = encoded.rsplit('$', 1)
            try:
                shared_key = settings.HMAC_KEYS[key_ver]
            except KeyError:
                log.info('Invalid shared key version "{0}"'.format(key_ver))
                return False

            bc_value = '${0}'.format(algo_and_hash.split('$', 1)[1])  # Yes, bcrypt <3s the leading $.
            hmac_value = self._hmac_create(password, shared_key)
            return bcrypt.hashpw(hmac_value, bc_value) == bc_value

        def _hmac_create(self, password, shared_key):
            """Create HMAC value based on pwd"""
            hmac_value = base64.b64encode(hmac.new(
                    smart_str(shared_key),
                    smart_str(password),
                    hashlib.sha512).digest())
            return hmac_value

    return BcryptHMACPasswordHasher

# We must have HMAC_KEYS. If not, let's raise an import error.
if not settings.HMAC_KEYS:
    raise ImportError('settings.HMAC_KEYS must not be empty.')

# For each HMAC_KEY, dynamically create a hasher to be imported.
for hmac_key in settings.HMAC_KEYS.keys():
    hmac_id = hmac_key.replace('-', '_')
    globals()[algo_name(hmac_id)] = get_hasher(hmac_id)


class BcryptHMACCombinedPasswordVerifier(BCryptPasswordHasher):
    """
    This reads anything with 'bcrypt' as the algo. This should be used
    to read bcypt values (with or without HMAC) in order to re-encode them
    as something else.
    """
    algorithm = 'bcrypt'
    rounds = getattr(settings, 'BCRYPT_ROUNDS', 12)

    def encode(self, password, salt):
        """This hasher is not meant to be used for encoding"""
        raise NotImplementedError()

    def verify(self, password, encoded):
        algo_and_hash, key_ver = encoded.rsplit('$', 1)
        try:
            shared_key = settings.HMAC_KEYS[key_ver]
        except KeyError:
            log.info('Invalid shared key version "{0}"'.format(key_ver))
            # Fall back to normal bcrypt
            algorithm, data = encoded.split('$', 1)
            return constant_time_compare(data, bcrypt.hashpw(password, data))

        bc_value = '${0}'.format(algo_and_hash.split('$', 1)[1])  # Yes, bcrypt <3s the leading $.
        hmac_value = self._hmac_create(password, shared_key)
        return bcrypt.hashpw(hmac_value, bc_value) == bc_value

    def _hmac_create(self, password, shared_key):
        """Create HMAC value based on pwd"""
        hmac_value = base64.b64encode(hmac.new(
                smart_str(shared_key),
                smart_str(password),
                hashlib.sha512).digest())
        return hmac_value


class SHA256PasswordHasher(BasePasswordHasher):
    """The SHA256 password hashing algorithm."""
    algorithm = 'sha256'

    def encode(self, password, salt):
        assert password
        assert salt and '$' not in salt
        hash = getattr(hashlib, self.algorithm)(salt + password).hexdigest()
        return '%s$%s$%s' % (self.algorithm, salt, hash)

    def verify(self, password, encoded):
        algorithm, salt, hash = encoded.split('$', 2)
        assert algorithm == self.algorithm
        encoded_2 = self.encode(password, salt)
        return constant_time_compare(encoded, encoded_2)

    def safe_summary(self, encoded):
        algorithm, salt, hash = encoded.split('$', 2)
        assert algorithm == self.algorithm
        return SortedDict([
            ('algorithm', algorithm),
            ('salt', mask_hash(salt, show=2)),
            ('hash', mask_hash(hash)),
        ])


class SHA1PasswordHasher(SHA256PasswordHasher):
    """The SHA1 password hashing algorithm."""
    algorithm = 'sha1'


class SHA512PasswordHasher(SHA256PasswordHasher):
    """The SHA512 password hashing algorithm."""
    algorithm = 'sha512'


class SHA512b64PasswordHasher(SHA512PasswordHasher):
    """The SHA512 password hashing algorithm with base64 encoding."""
    algorithm = 'sha512b64'

    def encode(self, password, salt):
        assert password
        assert salt and '$' not in salt
        hash = base64.encodestring(hashlib.sha512(salt + password).digest())
        return '%s$%s$%s' % (self.algorithm, salt, hash)

########NEW FILE########
__FILENAME__ = strengthen_user_passwords
from django.conf import settings
from django.contrib.auth.models import User
from django.core.management.base import NoArgsCommand

from django_sha2 import bcrypt_auth


class Command(NoArgsCommand):

    requires_model_validation = False
    output_transaction = True

    def handle_noargs(self, **options):

        if not settings.PWD_ALGORITHM == 'bcrypt':
            return

        for user in User.objects.all():
            pwd = user.password
            if pwd.startswith('hh$') or pwd.startswith('bcrypt$'):
                continue  # Password has already been strengthened.

            try:
                alg, salt, hash = pwd.split('$')
            except ValueError:
                continue  # Probably not a password we understand.

            bc_value = bcrypt_auth.create_hash(pwd)
            # 'hh' stands for 'hardened hash'.
            new_password = '$'.join(['hh', alg, salt, bc_value])
            user.password = new_password
            user.save()

########NEW FILE########
__FILENAME__ = models
"""Make sure django.contrib.auth monkeypatching happens on load."""
from django.conf import settings

# If we don't have password hashers, we need to monkey patch the auth module.
if not hasattr(settings, 'PASSWORD_HASHERS'):
    from django_sha2 import auth

########NEW FILE########
__FILENAME__ = settings
import os
import sys

## Generic settings
TEST_RUNNER = 'django_nose.runner.NoseTestSuiteRunner'

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
path = lambda *a: os.path.join(PROJECT_ROOT, *a)

sys.path.insert(0, path('..', '..'))

DATABASES = {
    'default': {
        'NAME': 'test.db',
        'ENGINE': 'django.db.backends.sqlite3',
    }
}

INSTALLED_APPS = (
    'django.contrib.auth',
    'django_sha2',
    'django.contrib.contenttypes',
    'django_nose',
)

## django-sha2 settings
PWD_ALGORITHM = 'bcrypt'
HMAC_KEYS = {
    '2010-06-01': 'OldSharedKey',
    '2011-01-01': 'ThisisASharedKey',  # This is the most recent key
    '2011-00-00': 'ThisKeyIsOldToo',
    '2010-01-01': 'EvenOlderSharedKey'
}

########NEW FILE########
__FILENAME__ = test_bcrypt
# -*- coding:utf-8 -*-
from django import test
from django.conf import settings
from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from django.core.management import call_command

from mock import patch
from nose.tools import eq_


class BcryptTests(test.TestCase):
    def setUp(self):
        super(BcryptTests, self).setUp()
        User.objects.create_user('john', 'johndoe@example.com',
                                 password='123456')
        User.objects.create_user('jane', 'janedoe@example.com',
                                 password='abc')
        User.objects.create_user('jude', 'jeromedoe@example.com',
                                 password=u'abcéäêëôøà')

    def test_bcrypt_used(self):
        """Make sure bcrypt was used as the hash."""
        eq_(User.objects.get(username='john').password[:7], 'bcrypt$')
        eq_(User.objects.get(username='jane').password[:7], 'bcrypt$')
        eq_(User.objects.get(username='jude').password[:7], 'bcrypt$')

    def test_bcrypt_auth(self):
        """Try authenticating."""
        assert authenticate(username='john', password='123456')
        assert authenticate(username='jane', password='abc')
        assert not authenticate(username='jane', password='123456')
        assert authenticate(username='jude', password=u'abcéäêëôøà')
        assert not authenticate(username='jude', password=u'çççbbbààà')

    @patch.object(settings._wrapped, 'HMAC_KEYS', dict())
    def test_nokey(self):
        """With no HMAC key, no dice."""
        assert not authenticate(username='john', password='123456')
        assert not authenticate(username='jane', password='abc')
        assert not authenticate(username='jane', password='123456')
        assert not authenticate(username='jude', password=u'abcéäêëôøà')
        assert not authenticate(username='jude', password=u'çççbbbààà')

    def test_password_from_django14(self):
        """Test that a password generated by django_sha2 with django 1.4 is
        recognized and changed to a 1.3 version"""
        # We can't easily call 1.4's hashers so we hardcode the passwords as
        # returned with the specific salts and hmac_key in 1.4.
        prefix = 'bcrypt2011_01_01$2a$12$'
        suffix = '$2011-01-01'
        raw_hashes = {
            'john': '02CfJWdVwLK80jlRe/Xx1u8sTHAR0JUmKV9YB4BS.Os4LK6nsoLie',
            'jane': '.ipDt6gRL3CPkVH7FEyR6.8YXeQFXAMyiX3mXpDh4YDBonrdofrcG',
            'jude': '6Ol.vgIFxMQw0LBhCLtv7OkV.oyJjen2GVMoiNcLnbsljSfYUkQqe',
        }

        u = User.objects.get(username="john")
        django14_style_password = "%s%s%s" % (prefix, raw_hashes['john'],
                                              suffix)
        u.password = django14_style_password
        assert u.check_password('123456')
        eq_(u.password[:7], 'bcrypt$')

        u = User.objects.get(username="jane")
        django14_style_password = "%s%s%s" % (prefix, raw_hashes['jane'],
                                              suffix)
        u.password = django14_style_password
        assert u.check_password('abc')
        eq_(u.password[:7], 'bcrypt$')

        u = User.objects.get(username="jude")
        django14_style_password = "%s%s%s" % (prefix, raw_hashes['jude'],
                                              suffix)
        u.password = django14_style_password
        assert u.check_password(u'abcéäêëôøà')
        eq_(u.password[:7], 'bcrypt$')

    def test_hmac_autoupdate(self):
        """Auto-update HMAC key if hash in DB is outdated."""
        # Get HMAC key IDs to compare
        old_key_id = max(settings.HMAC_KEYS.keys())
        new_key_id = '2020-01-01'

        # Add a new HMAC key
        new_keys = settings.HMAC_KEYS.copy()
        new_keys[new_key_id] = 'a_new_key'
        with patch.object(settings._wrapped, 'HMAC_KEYS', new_keys):
            # Make sure the database has the old key ID.
            john = User.objects.get(username='john')
            eq_(john.password.rsplit('$', 1)[1], old_key_id)

            # Log in.
            assert authenticate(username='john', password='123456')

            # Make sure the DB now has a new password hash.
            john = User.objects.get(username='john')
            eq_(john.password.rsplit('$', 1)[1], new_key_id)

    def test_rehash(self):
        """Auto-upgrade to stronger hash if needed."""
        # Set a sha256 hash for a user. This one is "123".
        john = User.objects.get(username='john')
        john.password = ('sha256$7a49025f024ad3dcacad$aaff1abe5377ffeab6ccc68'
                         '709d94c1950edf11f02d8acb83c75d8fcac1ebeb1')
        john.save()

        # The hash should be sha256 now.
        john = User.objects.get(username='john')
        eq_(john.password.split('$', 1)[0], 'sha256')

        # Log in (should rehash transparently).
        assert authenticate(username='john', password='123')

        # Make sure the DB now has a bcrypt hash.
        john = User.objects.get(username='john')
        eq_(john.password.split('$', 1)[0], 'bcrypt')

        # Log in again with the new hash.
        assert authenticate(username='john', password='123')

    def test_management_command(self):
        """Test password update flow via management command, from default
        Django hashes, to hardened hashes, to bcrypt on log in."""

        john = User.objects.get(username='john')
        john.password = 'sha1$3356f$9fd40318e1de9ecd3ab3a5fe944ceaf6a2897eef'
        john.save()

        # The hash should be sha1 now.
        john = User.objects.get(username='john')
        eq_(john.password.split('$', 1)[0], 'sha1')

        # Simulate calling management command
        call_command('strengthen_user_passwords')

        # The hash should be 'hh' now.
        john = User.objects.get(username='john')
        eq_(john.password.split('$', 1)[0], 'hh')

        # Logging in will convert the hardened hash to bcrypt.
        assert authenticate(username='john', password='123')

        # Make sure the DB now has a bcrypt hash.
        john = User.objects.get(username='john')
        eq_(john.password.split('$', 1)[0], 'bcrypt')

        # Log in again with the new hash.
        assert authenticate(username='john', password='123')

########NEW FILE########
__FILENAME__ = test_sha2
# -*- coding:utf-8 -*-
from django import test

from nose.tools import eq_


class Sha2Tests(test.TestCase):
    """Tests for sha256 and sha512."""
    SALT = '1234567890'
    HASHES = {
        'sha256': {
            '123456': ('7a51d064a1a216a692f753fcdab276e4ff201a01d8b66f56d50d'
                       '4d719fd0dc87'),
            'abc': ('343c791deda10905e9c03bccaeb75413c9ee960af7b1f2291f4acc9'
                    '925e2065a'),
            u'abcéäêëôøà': ('c69c2fba36f26b3fcb39a0ed1fec005271c93725'
                            'bcac10521333259179cc2a7f'),
        },
        'sha512': {
            '123456': ('1f52ed515871c913164398ec24c47088cdf957e81af28c899a8a'
                       '0195d3620e083968a6d4d86cb8f9bd7f909b23f75a1c044ec8e6'
                       '75c6efbcb0e4bf0eb445525d'),
            'abc': ('a559db3d96b76dee0c3cdaa9e9ee1f87bbc6c9c521636fd840e96fe'
                    '78959d4e8ebf99a13eab3fd2df4ec76aac733cc5e2e5a7f641e2b41'
                    '98b4a7e634f11b48f3'),
            u'abcéäêëôøà': ('016e02ae147cd23abfb94f3c97cb90e4e68aabd4c36a950'
                            'aed76fd74bdea966d7b57fd57979b8ae55ae8c6a2c25250'
                            '02ae243127f9dc57a672caf0dfe508c74d'),
        },
        'sha512b64': {
            '123456': ("H1LtUVhxyRMWQ5jsJMRwiM35V+ga8oyJmooBldNiDgg5aKbU2Gy4"
                       "+b1/kJsj91ocBE7I5nXG77yw\n5L8OtEVSXQ==\n"),
            'abc': ("pVnbPZa3be4MPNqp6e4fh7vGycUhY2/YQOlv54lZ1Ojr+ZoT6rP9LfT"
                    "sdqrHM8xeLlp/ZB4rQZi0\np+Y08RtI8w==\n"),
            u'abcéäêëôøà': ("AW4CrhR80jq/uU88l8uQ5OaKq9TDapUK7Xb9dL3qlm17V/1"
                            "Xl5uK5VroxqLCUlACriQxJ/ncV6Zy\nyvDf5QjHTQ==\n"),
        }
    }

    def test_hexdigest(self):
        """Test various password hashes."""

        # The following import need to stay inside the function to make sure
        # monkeypatching has happened. If moved to the top the test would fail
        # because the function has been imported too early before monkeypatch.
        from django.contrib.auth.models import get_hexdigest

        for algo, pws in self.HASHES.items():
            for pw, hashed in pws.items():
                eq_(get_hexdigest(algo, self.SALT, pw), hashed)

########NEW FILE########
__FILENAME__ = settings
import os
import sys

## Generic settings
TEST_RUNNER = 'django_nose.runner.NoseTestSuiteRunner'

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
path = lambda *a: os.path.join(PROJECT_ROOT, *a)

sys.path.insert(0, path('..', '..'))

DATABASES = {
    'default': {
        'NAME': 'test.db',
        'ENGINE': 'django.db.backends.sqlite3',
    }
}

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django_nose',
)

## django-sha2 settings
HMAC_KEYS = {
    '2010-06-01': 'OldSharedKey',
    '2011-01-01': 'ThisisASharedKey',  # This is the most recent key
    '2011-00-00': 'ThisKeyIsOldToo',
    '2010-01-01': 'EvenOlderSharedKey'
}

BASE_PASSWORD_HASHERS = (
    'django_sha2.hashers.BcryptHMACCombinedPasswordVerifier',
    'django_sha2.hashers.SHA512PasswordHasher',
    'django_sha2.hashers.SHA256PasswordHasher',
    'django.contrib.auth.hashers.SHA1PasswordHasher',
    'django.contrib.auth.hashers.MD5PasswordHasher',
    'django.contrib.auth.hashers.UnsaltedMD5PasswordHasher',
)

from django_sha2 import get_password_hashers
PASSWORD_HASHERS = get_password_hashers(BASE_PASSWORD_HASHERS, HMAC_KEYS)

########NEW FILE########
__FILENAME__ = test_bcrypt
# -*- coding:utf-8 -*-
from django import test
from django.conf import settings
from django.contrib.auth import authenticate
from django.contrib.auth.models import User

from mock import patch
from nose.tools import eq_


class BcryptTests(test.TestCase):
    def setUp(self):
        super(BcryptTests, self).setUp()
        User.objects.create_user('john', 'johndoe@example.com',
                                 password='123456')
        User.objects.create_user('jane', 'janedoe@example.com',
                                 password='abc')
        User.objects.create_user('jude', 'jeromedoe@example.com',
                                 password=u'abcéäêëôøà')

    def test_newest_hmac_key_used(self):
        """
        Make sure the first hasher (the one used for encoding) has the right
        hmac key.
        """
        eq_(settings.PASSWORD_HASHERS[0][-10:].replace('_', '-'),
            max(settings.HMAC_KEYS.keys()))

    def test_bcrypt_used(self):
        """Make sure bcrypt was used as the hash."""
        eq_(User.objects.get(username='john').password[:6], 'bcrypt')
        eq_(User.objects.get(username='jane').password[:6], 'bcrypt')
        eq_(User.objects.get(username='jude').password[:6], 'bcrypt')

    def test_bcrypt_auth(self):
        """Try authenticating."""
        assert authenticate(username='john', password='123456')
        assert authenticate(username='jane', password='abc')
        assert not authenticate(username='jane', password='123456')
        assert authenticate(username='jude', password=u'abcéäêëôøà')
        assert not authenticate(username='jude', password=u'çççbbbààà')

    @patch.object(settings._wrapped, 'HMAC_KEYS', dict())
    def test_nokey(self):
        """With no HMAC key, no dice."""
        assert not authenticate(username='john', password='123456')
        assert not authenticate(username='jane', password='abc')
        assert not authenticate(username='jane', password='123456')
        assert not authenticate(username='jude', password=u'abcéäêëôøà')
        assert not authenticate(username='jude', password=u'çççbbbààà')

    def test_hmac_autoupdate(self):
        """Auto-update HMAC key if hash in DB is outdated."""
        # Get an old password hasher to encode John's password with.
        from django_sha2.hashers import bcrypt2010_01_01
        old_hasher = bcrypt2010_01_01()

        john = User.objects.get(username='john')
        john.password = old_hasher.encode('123456', old_hasher.salt())
        john.save()

        # Log in.
        assert authenticate(username='john', password='123456')

        # Make sure the DB now has a new password hash.
        john = User.objects.get(username='john')
        eq_(john.password.rsplit('$', 1)[1], max(settings.HMAC_KEYS.keys()))

    def test_rehash(self):
        """Auto-upgrade to stronger hash if needed."""
        # Set a sha256 hash for a user. This one is "123".
        john = User.objects.get(username='john')
        john.password = ('sha256$7a49025f024ad3dcacad$aaff1abe5377ffeab6ccc68'
                         '709d94c1950edf11f02d8acb83c75d8fcac1ebeb1')
        john.save()

        # The hash should be sha256 now.
        john = User.objects.get(username='john')
        eq_(john.password.split('$', 1)[0], 'sha256')

        # Log in (should rehash transparently).
        assert authenticate(username='john', password='123')

        # Make sure the DB now has a bcrypt hash.
        john = User.objects.get(username='john')
        eq_(john.password[:6], 'bcrypt')

        # Log in again with the new hash.
        assert authenticate(username='john', password='123')

########NEW FILE########
