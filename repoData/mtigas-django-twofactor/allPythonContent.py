__FILENAME__ = adminsite
from django.contrib.admin.sites import AdminSite
from django_twofactor.auth_forms import TwoFactorAdminAuthenticationForm
from django_twofactor.forms import (ResetTwoFactorAuthForm,
    DisableTwoFactorAuthForm)
from django.shortcuts import render_to_response
from django.template import RequestContext
from django_twofactor.models import UserAuthToken

class TwoFactorAuthAdminSite(AdminSite):
    login_form = TwoFactorAdminAuthenticationForm
    login_template = "twofactor_admin/twofactor_login.html"
    password_change_template = "twofactor_admin/registration/password_change_form.html"

    def get_urls(self):
        from django.conf.urls.defaults import patterns, url

        urlpatterns = patterns('django_twofactor.admin_views',
            url(r'^twofactor_auth_setup/$',
                self.twofactor_config,
                name="twofactor_config"),
        )
        urlpatterns += super(TwoFactorAuthAdminSite, self).get_urls()

        return urlpatterns
    
    def twofactor_config(self, request):
        """
        Handles two-factor authenticator configuration.
        """
        disableform = None
        resetform = None
        if (request.method == "POST")\
        and ("reset_confirmation" in request.POST):
            # We are resetting the user's two-factor key.
            resetform = ResetTwoFactorAuthForm(user=request.user,
                data=request.POST)
            if resetform.is_valid():
                token = resetform.save()
                return render_to_response(
                    "twofactor_admin/registration/twofactor_config_done.html",
                    dict(token=token, user=request.user),
                    context_instance=RequestContext(request)
                )
        elif (request.method == "POST")\
        and ("disable_confirmation" in request.POST):
            # We are disabling two-factor auth for the user
            disableform = DisableTwoFactorAuthForm(user=request.user,
                data=request.POST)
            if disableform.is_valid():
                disableform.save()
                return render_to_response(
                    "twofactor_admin/registration/twofactor_config_disabled.html",
                    dict(user=request.user),
                    context_instance=RequestContext(request)
                )
        if not resetform:
            resetform = ResetTwoFactorAuthForm(user=None)
        if not disableform:
            disableform = DisableTwoFactorAuthForm(user=None)

        has_token = bool(UserAuthToken.objects.filter(user=request.user))

        return render_to_response(
            "twofactor_admin/registration/twofactor_config.html",
            dict(
                resetform=resetform,
                disableform=disableform,
                has_token=has_token
            ),
            context_instance=RequestContext(request)
        )


twofactor_admin_site = TwoFactorAuthAdminSite()

########NEW FILE########
__FILENAME__ = auth_backends
from django.contrib.auth.models import User
from django.contrib.auth.backends import ModelBackend
from django_twofactor.models import UserAuthToken

class TwoFactorAuthBackend(ModelBackend):
    def authenticate(self, username=None, password=None, token=None):
        # Validate username and password first
        user_or_none = super(TwoFactorAuthBackend, self).authenticate(username, password)
        
        if user_or_none and isinstance(user_or_none, User):
            # Got a valid login. Now check token.
            try:
                user_token = UserAuthToken.objects.get(user=user_or_none)
            except UserAuthToken.DoesNotExist:
                # User doesn't have two-factor authentication enabled, so
                # just return the User object.
                return user_or_none
            
            validate = user_token.check_auth_code(token)
            if (validate == True):
                # Auth code was valid.
                return user_or_none
            else:
                # Bad auth code
                return None
        return user_or_none

########NEW FILE########
__FILENAME__ = auth_forms
from django import forms
from django.contrib.auth.forms import AuthenticationForm
from django.utils.translation import ugettext_lazy as _
from django.contrib.auth import authenticate

ERROR_MESSAGE = _("Please enter the correct username, password and "
    "authentication code (if applicable). Note that all fields are "
    "case-sensitive.")


class TwoFactorAuthenticationForm(AuthenticationForm):
    token = forms.IntegerField(label=_("Authentication Code"),
        help_text="If you have enabled two-factor authentication, enter the six-digit number from your authentication device here.",
        widget=forms.TextInput(attrs={'maxlength':'6'}),
        min_value=1, max_value=999999,
        required=False
    )

    def clean(self):
        username = self.cleaned_data.get('username')
        password = self.cleaned_data.get('password')
        token = self.cleaned_data.get('token')

        if username and password:
            self.user_cache = authenticate(username=username, password=password, token=token)
            if self.user_cache is None:
                raise forms.ValidationError(ERROR_MESSAGE)
            elif not self.user_cache.is_active:
                raise forms.ValidationError(_("This account is inactive."))
        self.check_for_test_cookie()
        return self.cleaned_data


class TwoFactorAdminAuthenticationForm(AuthenticationForm):
    token = forms.IntegerField(label=_("Authentication Code"),
        help_text="If you have enabled two-factor authentication, enter the "
            "six-digit number from your authentication device here.",
        widget=forms.TextInput(attrs={'maxlength':'6'}),
        min_value=1, max_value=999999,
        required=False
    )
    this_is_the_login_form = forms.BooleanField(widget=forms.HiddenInput,
        initial=1,  error_messages={'required': _("Please log in again, "
            "because your session has expired.")})

    def clean(self):
        username = self.cleaned_data.get('username')
        password = self.cleaned_data.get('password')
        token = self.cleaned_data.get('token')

        if username and password:
            self.user_cache = authenticate(username=username, password=password, token=token)
            if self.user_cache is None:
                raise forms.ValidationError(ERROR_MESSAGE)
            elif not self.user_cache.is_active:
                raise forms.ValidationError(_("This account is inactive."))
        self.check_for_test_cookie()
        return self.cleaned_data

########NEW FILE########
__FILENAME__ = encutil
"""
Kind of based on the encryption bits detailed in
http://djangosnippets.org/snippets/1095/
"""

from hashlib import sha256
from django.conf import settings
from django.utils.encoding import smart_str
from binascii import hexlify, unhexlify
import string

# Get best AES implementation we can.
try:
    from Crypto.Cipher import AES
except ImportError:
    from django_twofactor import pyaes as AES

# Get best `random` implementation we can.
import random
try:
    random = random.SystemRandom()
except:
    pass

def _gen_salt(length=16):
    return ''.join([random.choice(string.letters+string.digits) for i in range(length)])

def _get_key(salt):
    """ Combines `settings.SECRET_KEY` with a salt. """
    if not salt: salt = ""
    
    return sha256("%s%s" % (settings.SECRET_KEY, salt)).digest()

def encrypt(data, salt):
    cipher = AES.new(_get_key(salt), mode=AES.MODE_ECB)
    value = smart_str(data)

    padding  = cipher.block_size - len(value) % cipher.block_size
    if padding and padding < cipher.block_size:
        value += "\0" + ''.join([random.choice(string.printable) for index in range(padding-1)])
    return hexlify(cipher.encrypt(value))

def decrypt(encrypted_data, salt):
    cipher = AES.new(_get_key(salt), mode=AES.MODE_ECB)

    return cipher.decrypt(unhexlify(smart_str(encrypted_data))).split('\0')[0]

########NEW FILE########
__FILENAME__ = forms
from django import forms
from django_twofactor.models import UserAuthToken
from django_twofactor.util import random_seed, encrypt_value


class ResetTwoFactorAuthForm(forms.Form):
    reset_confirmation = forms.BooleanField(required=True)

    def __init__(self, user, *args, **kwargs):
        self.user = user
        super(ResetTwoFactorAuthForm, self).__init__(*args, **kwargs)

    def save(self):
        if not self.user:
            return None

        try:
            token = UserAuthToken.objects.get(user=self.user)
        except UserAuthToken.DoesNotExist:
            token = UserAuthToken(user=self.user)

        token.encrypted_seed = encrypt_value(random_seed(30))
        token.save()
        return token


class DisableTwoFactorAuthForm(forms.Form):
    disable_confirmation = forms.BooleanField(required=True)

    def __init__(self, user, *args, **kwargs):
        self.user = user
        super(DisableTwoFactorAuthForm, self).__init__(*args, **kwargs)

    def save(self):
        if not self.user:
            return None

        UserAuthToken.objects.filter(user=self.user).delete()

        return self.user

########NEW FILE########
__FILENAME__ = models
from django.db import models
from django_twofactor.util import decrypt_value, check_raw_seed, get_google_url
from base64 import b32encode
from socket import gethostname

class UserAuthToken(models.Model):
    user = models.OneToOneField("auth.User")
    encrypted_seed = models.CharField(max_length=120) #fits 16b salt+40b seed
    
    created_datetime = models.DateTimeField(
        verbose_name="created", auto_now_add=True)
    updated_datetime = models.DateTimeField(
        verbose_name="last updated", auto_now=True)
    
    def check_auth_code(self, auth_code):
        """
        Checks whether `auth_code` is a valid authentication code for this
        user, at the current time.
        """
        return check_raw_seed(decrypt_value(self.encrypted_seed), auth_code)

    def google_url(self, name=None):
        """
        The Google Charts QR code version of the seed, plus an optional
        name for this (defaults to "username@hostname").
        """
        if not name:
            username = self.user.username
            hostname = gethostname()
            name = "%s@%s" % (username, hostname)

        return get_google_url(
            decrypt_value(self.encrypted_seed),
            name
        )

    def b32_secret(self):
        """
        The base32 version of the seed (for input into Google Authenticator
        and similar soft token devices.
        """
        return b32encode(decrypt_value(self.encrypted_seed))

from django_twofactor import auth_forms

########NEW FILE########
__FILENAME__ = pyaes
"""Simple AES cipher implementation in pure Python following PEP-272 API

Homepage: https://bitbucket.org/intgr/pyaes/

The goal of this module is to be as fast as reasonable in Python while still
being Pythonic and readable/understandable. It is licensed under the permissive
MIT license.

Hopefully the code is readable and commented enough that it can serve as an
introduction to the AES cipher for Python coders. In fact, it should go along
well with the Stick Figure Guide to AES:
http://www.moserware.com/2009/09/stick-figure-guide-to-advanced.html

Contrary to intuition, this implementation numbers the 4x4 matrices from top to
bottom for efficiency reasons::

  0  4  8 12
  1  5  9 13
  2  6 10 14
  3  7 11 15

Effectively it's the transposition of what you'd expect. This actually makes
the code simpler -- except the ShiftRows step, but hopefully the explanation
there clears it up.

"""

####
# Copyright (c) 2010 Marti Raudsepp <marti@juffo.org>
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
####


from array import array

# Globals mandated by PEP 272:
# http://www.python.org/dev/peps/pep-0272/
MODE_ECB = 1
MODE_CBC = 2
#MODE_CTR = 6

block_size = 16
# variable length key: 16, 24 or 32 bytes
key_size = None

def new(key, mode, IV=None):
    if mode == MODE_ECB:
        return ECBMode(AES(key))
    elif mode == MODE_CBC:
        if IV is None:
            raise ValueError, "CBC mode needs an IV value!"

        return CBCMode(AES(key), IV)
    else:
        raise NotImplementedError

#### AES cipher implementation

class AES(object):
    block_size = 16

    def __init__(self, key):
        self.setkey(key)

    def setkey(self, key):
        """Sets the key and performs key expansion."""

        self.key = key
        self.key_size = len(key)

        if self.key_size == 16:
            self.rounds = 10
        elif self.key_size == 24:
            self.rounds = 12
        elif self.key_size == 32:
            self.rounds = 14
        else:
            raise ValueError, "Key length must be 16, 24 or 32 bytes"

        self.expand_key()

    def expand_key(self):
        """Performs AES key expansion on self.key and stores in self.exkey"""

        # The key schedule specifies how parts of the key are fed into the
        # cipher's round functions. "Key expansion" means performing this
        # schedule in advance. Almost all implementations do this.
        #
        # Here's a description of AES key schedule:
        # http://en.wikipedia.org/wiki/Rijndael_key_schedule

        # The expanded key starts with the actual key itself
        exkey = array('B', self.key)

        # extra key expansion steps
        if self.key_size == 16:
            extra_cnt = 0
        elif self.key_size == 24:
            extra_cnt = 2
        else:
            extra_cnt = 3

        # 4-byte temporary variable for key expansion
        word = exkey[-4:]
        # Each expansion cycle uses 'i' once for Rcon table lookup
        for i in xrange(1, 11):

            #### key schedule core:
            # left-rotate by 1 byte
            word = word[1:4] + word[0:1]

            # apply S-box to all bytes
            for j in xrange(4):
                word[j] = aes_sbox[word[j]]

            # apply the Rcon table to the leftmost byte
            word[0] ^= aes_Rcon[i]
            #### end key schedule core

            for z in xrange(4):
                for j in xrange(4):
                    # mix in bytes from the last subkey
                    word[j] ^= exkey[-self.key_size + j]
                exkey.extend(word)

            # Last key expansion cycle always finishes here
            if len(exkey) >= (self.rounds+1) * self.block_size:
                break

            # Special substitution step for 256-bit key
            if self.key_size == 32:
                for j in xrange(4):
                    # mix in bytes from the last subkey XORed with S-box of
                    # current word bytes
                    word[j] = aes_sbox[word[j]] ^ exkey[-self.key_size + j]
                exkey.extend(word)

            # Twice for 192-bit key, thrice for 256-bit key
            for z in xrange(extra_cnt):
                for j in xrange(4):
                    # mix in bytes from the last subkey
                    word[j] ^= exkey[-self.key_size + j]
                exkey.extend(word)

        self.exkey = exkey

    def add_round_key(self, block, round):
        """AddRoundKey step in AES. This is where the key is mixed into plaintext"""

        offset = round * 16
        exkey = self.exkey

        for i in xrange(16):
            block[i] ^= exkey[offset + i]

        #print 'AddRoundKey:', block

    def sub_bytes(self, block, sbox):
        """SubBytes step, apply S-box to all bytes

        Depending on whether encrypting or decrypting, a different sbox array
        is passed in.
        """

        for i in xrange(16):
            block[i] = sbox[block[i]]

        #print 'SubBytes   :', block

    def shift_rows(self, b):
        """ShiftRows step. Shifts 2nd row to left by 1, 3rd row by 2, 4th row by 3

        Since we're performing this on a transposed matrix, cells are numbered
        from top to bottom first::

          0  4  8 12   ->    0  4  8 12    -- 1st row doesn't change
          1  5  9 13   ->    5  9 13  1    -- row shifted to left by 1 (wraps around)
          2  6 10 14   ->   10 14  2  6    -- shifted by 2
          3  7 11 15   ->   15  3  7 11    -- shifted by 3
        """

        b[1], b[5], b[ 9], b[13] = b[ 5], b[ 9], b[13], b[ 1]
        b[2], b[6], b[10], b[14] = b[10], b[14], b[ 2], b[ 6]
        b[3], b[7], b[11], b[15] = b[15], b[ 3], b[ 7], b[11]

        #print 'ShiftRows  :', b

    def shift_rows_inv(self, b):
        """Similar to shift_rows above, but performed in inverse for decryption."""

        b[ 5], b[ 9], b[13], b[ 1] = b[1], b[5], b[ 9], b[13]
        b[10], b[14], b[ 2], b[ 6] = b[2], b[6], b[10], b[14]
        b[15], b[ 3], b[ 7], b[11] = b[3], b[7], b[11], b[15]

        #print 'ShiftRows  :', b

    def mix_columns(self, block):
        """MixColumns step. Mixes the values in each column"""

        # Cache global multiplication tables (see below)
        mul_by_2 = gf_mul_by_2
        mul_by_3 = gf_mul_by_3

        # Since we're dealing with a transposed matrix, columns are already
        # sequential
        for col in xrange(0, 16, 4):
            v0, v1, v2, v3 = block[col : col+4]

            block[col  ] = mul_by_2[v0] ^ v3 ^ v2 ^ mul_by_3[v1]
            block[col+1] = mul_by_2[v1] ^ v0 ^ v3 ^ mul_by_3[v2]
            block[col+2] = mul_by_2[v2] ^ v1 ^ v0 ^ mul_by_3[v3]
            block[col+3] = mul_by_2[v3] ^ v2 ^ v1 ^ mul_by_3[v0]

        #print 'MixColumns :', block

    def mix_columns_inv(self, block):
        """Similar to mix_columns above, but performed in inverse for decryption."""

        # Cache global multiplication tables (see below)
        mul_9  = gf_mul_by_9
        mul_11 = gf_mul_by_11
        mul_13 = gf_mul_by_13
        mul_14 = gf_mul_by_14

        # Since we're dealing with a transposed matrix, columns are already
        # sequential
        for col in xrange(0, 16, 4):
            v0, v1, v2, v3 = block[col : col+4]

            block[col  ] = mul_14[v0] ^ mul_9[v3] ^ mul_13[v2] ^ mul_11[v1]
            block[col+1] = mul_14[v1] ^ mul_9[v0] ^ mul_13[v3] ^ mul_11[v2]
            block[col+2] = mul_14[v2] ^ mul_9[v1] ^ mul_13[v0] ^ mul_11[v3]
            block[col+3] = mul_14[v3] ^ mul_9[v2] ^ mul_13[v1] ^ mul_11[v0]

        #print 'MixColumns :', block

    def encrypt_block(self, block):
        """Encrypts a single block. This is the main AES function"""

        # For efficiency reasons, the state between steps is transmitted via a
        # mutable array, not returned
        self.add_round_key(block, 0)

        for round in xrange(1, self.rounds):
            self.sub_bytes(block, aes_sbox)
            self.shift_rows(block)
            self.mix_columns(block)
            self.add_round_key(block, round)

        self.sub_bytes(block, aes_sbox)
        self.shift_rows(block)
        # no mix_columns step in the last round
        self.add_round_key(block, self.rounds)

    def decrypt_block(self, block):
        """Decrypts a single block. This is the main AES decryption function"""

        # For efficiency reasons, the state between steps is transmitted via a
        # mutable array, not returned
        self.add_round_key(block, self.rounds)

        # count rounds down from (self.rounds) ... 1
        for round in xrange(self.rounds-1, 0, -1):
            self.shift_rows_inv(block)
            self.sub_bytes(block, aes_inv_sbox)
            self.add_round_key(block, round)
            self.mix_columns_inv(block)

        self.shift_rows_inv(block)
        self.sub_bytes(block, aes_inv_sbox)
        self.add_round_key(block, 0)
        # no mix_columns step in the last round


#### ECB mode implementation

class ECBMode(object):
    """Electronic CodeBook (ECB) mode encryption.

    Basically this mode applies the cipher function to each block individually;
    no feedback is done. NB! This is insecure for almost all purposes
    """

    def __init__(self, cipher):
        self.cipher = cipher
        self.block_size = cipher.block_size

    def ecb(self, data, block_func):
        """Perform ECB mode with the given function"""

        if len(data) % self.block_size != 0:
            raise ValueError, "Input length must be multiple of 16"

        block_size = self.block_size
        data = array('B', data)

        for offset in xrange(0, len(data), block_size):
            block = data[offset : offset+block_size]
            block_func(block)
            data[offset : offset+block_size] = block

        return data.tostring()

    def encrypt(self, data):
        """Encrypt data in ECB mode"""

        return self.ecb(data, self.cipher.encrypt_block)

    def decrypt(self, data):
        """Decrypt data in ECB mode"""

        return self.ecb(data, self.cipher.decrypt_block)

#### CBC mode

class CBCMode(object):
    """Cipher Block Chaining (CBC) mode encryption. This mode avoids content leaks.

    In CBC encryption, each plaintext block is XORed with the ciphertext block
    preceding it; decryption is simply the inverse.
    """

    # A better explanation of CBC can be found here:
    # http://en.wikipedia.org/wiki/Block_cipher_modes_of_operation#Cipher-block_chaining_.28CBC.29

    def __init__(self, cipher, IV):
        self.cipher = cipher
        self.block_size = cipher.block_size
        self.IV = array('B', IV)

    def encrypt(self, data):
        """Encrypt data in CBC mode"""

        block_size = self.block_size
        if len(data) % block_size != 0:
            raise ValueError, "Plaintext length must be multiple of 16"

        data = array('B', data)
        IV = self.IV

        for offset in xrange(0, len(data), block_size):
            block = data[offset : offset+block_size]

            # Perform CBC chaining
            for i in xrange(block_size):
                block[i] ^= IV[i]

            self.cipher.encrypt_block(block)
            data[offset : offset+block_size] = block
            IV = block

        self.IV = IV
        return data.tostring()

    def decrypt(self, data):
        """Decrypt data in CBC mode"""

        block_size = self.block_size
        if len(data) % block_size != 0:
            raise ValueError, "Ciphertext length must be multiple of 16"

        data = array('B', data)
        IV = self.IV

        for offset in xrange(0, len(data), block_size):
            ctext = data[offset : offset+block_size]
            block = ctext[:]
            self.cipher.decrypt_block(block)

            # Perform CBC chaining
            #for i in xrange(block_size):
            #    data[offset + i] ^= IV[i]
            for i in xrange(block_size):
                block[i] ^= IV[i]
            data[offset : offset+block_size] = block

            IV = ctext
            #data[offset : offset+block_size] = block

        self.IV = IV
        return data.tostring()

####

def galois_multiply(a, b):
    """Galois Field multiplicaiton for AES"""
    p = 0
    while b:
        if b & 1:
            p ^= a
        a <<= 1
        if a & 0x100:
            a ^= 0x1b
        b >>= 1

    return p & 0xff

# Precompute the multiplication tables for encryption
gf_mul_by_2  = array('B', [galois_multiply(x,  2) for x in range(256)])
gf_mul_by_3  = array('B', [galois_multiply(x,  3) for x in range(256)])
# ... for decryption
gf_mul_by_9  = array('B', [galois_multiply(x,  9) for x in range(256)])
gf_mul_by_11 = array('B', [galois_multiply(x, 11) for x in range(256)])
gf_mul_by_13 = array('B', [galois_multiply(x, 13) for x in range(256)])
gf_mul_by_14 = array('B', [galois_multiply(x, 14) for x in range(256)])

####

# The S-box is a 256-element array, that maps a single byte value to another
# byte value. Since it's designed to be reversible, each value occurs only once
# in the S-box
#
# More information: http://en.wikipedia.org/wiki/Rijndael_S-box

aes_sbox = array('B',
    '637c777bf26b6fc53001672bfed7ab76'
    'ca82c97dfa5947f0add4a2af9ca472c0'
    'b7fd9326363ff7cc34a5e5f171d83115'
    '04c723c31896059a071280e2eb27b275'
    '09832c1a1b6e5aa0523bd6b329e32f84'
    '53d100ed20fcb15b6acbbe394a4c58cf'
    'd0efaafb434d338545f9027f503c9fa8'
    '51a3408f929d38f5bcb6da2110fff3d2'
    'cd0c13ec5f974417c4a77e3d645d1973'
    '60814fdc222a908846eeb814de5e0bdb'
    'e0323a0a4906245cc2d3ac629195e479'
    'e7c8376d8dd54ea96c56f4ea657aae08'
    'ba78252e1ca6b4c6e8dd741f4bbd8b8a'
    '703eb5664803f60e613557b986c11d9e'
    'e1f8981169d98e949b1e87e9ce5528df'
    '8ca1890dbfe6426841992d0fb054bb16'.decode('hex')
)

# This is the inverse of the above. In other words:
# aes_inv_sbox[aes_sbox[val]] == val

aes_inv_sbox = array('B',
    '52096ad53036a538bf40a39e81f3d7fb'
    '7ce339829b2fff87348e4344c4dee9cb'
    '547b9432a6c2233dee4c950b42fac34e'
    '082ea16628d924b2765ba2496d8bd125'
    '72f8f66486689816d4a45ccc5d65b692'
    '6c704850fdedb9da5e154657a78d9d84'
    '90d8ab008cbcd30af7e45805b8b34506'
    'd02c1e8fca3f0f02c1afbd0301138a6b'
    '3a9111414f67dcea97f2cfcef0b4e673'
    '96ac7422e7ad3585e2f937e81c75df6e'
    '47f11a711d29c5896fb7620eaa18be1b'
    'fc563e4bc6d279209adbc0fe78cd5af4'
    '1fdda8338807c731b11210592780ec5f'
    '60517fa919b54a0d2de57a9f93c99cef'
    'a0e03b4dae2af5b0c8ebbb3c83539961'
    '172b047eba77d626e169146355210c7d'.decode('hex')
)

# The Rcon table is used in AES's key schedule (key expansion)
# It's a pre-computed table of exponentation of 2 in AES's finite field
#
# More information: http://en.wikipedia.org/wiki/Rijndael_key_schedule

aes_Rcon = array('B',
    '8d01020408102040801b366cd8ab4d9a'
    '2f5ebc63c697356ad4b37dfaefc59139'
    '72e4d3bd61c29f254a943366cc831d3a'
    '74e8cb8d01020408102040801b366cd8'
    'ab4d9a2f5ebc63c697356ad4b37dfaef'
    'c5913972e4d3bd61c29f254a943366cc'
    '831d3a74e8cb8d01020408102040801b'
    '366cd8ab4d9a2f5ebc63c697356ad4b3'
    '7dfaefc5913972e4d3bd61c29f254a94'
    '3366cc831d3a74e8cb8d010204081020'
    '40801b366cd8ab4d9a2f5ebc63c69735'
    '6ad4b37dfaefc5913972e4d3bd61c29f'
    '254a943366cc831d3a74e8cb8d010204'
    '08102040801b366cd8ab4d9a2f5ebc63'
    'c697356ad4b37dfaefc5913972e4d3bd'
    '61c29f254a943366cc831d3a74e8cb'.decode('hex')
)

########NEW FILE########
__FILENAME__ = tests

########NEW FILE########
__FILENAME__ = util
from base64 import b32encode
from binascii import hexlify
from urllib import urlencode
from django_twofactor.encutil import encrypt, decrypt, _gen_salt
from oath import accept_totp
from django.conf import settings

# Get best `random` implementation we can.
import random
try:
    random = random.SystemRandom()
except:
    pass

# Parse out some settings, if we have 'em.
TOTP_OPTIONS = getattr(settings, "TWOFACTOR_TOTP_OPTIONS", {})
PERIOD = TOTP_OPTIONS.get('period', 30)
FORWARD_DRIFT = TOTP_OPTIONS.get('forward_drift', 1)
BACKWARD_DRIFT = TOTP_OPTIONS.get('backward_drift', 1)

# note: Google Authenticator only outputs dec6, so changing this
# will result in incompatibility
DEFAULT_TOKEN_TYPE = TOTP_OPTIONS.get('default_token_type', "dec6")

ENCRYPTION_KEY = getattr(settings, "TWOFACTOR_ENCRYPTION_KEY", "")

def random_seed(rawsize=10):
    """ Generates a random seed as a raw byte string. """
    return ''.join([ chr(random.randint(0, 255)) for i in range(rawsize) ])

def encrypt_value(raw_value):
    salt = _gen_salt()
    return "%s$%s" %  (salt, encrypt(raw_value, ENCRYPTION_KEY+salt))

def decrypt_value(salted_value):
    salt, encrypted_value = salted_value.split("$", 1)
    return decrypt(encrypted_value, ENCRYPTION_KEY+salt)

def check_raw_seed(raw_seed, auth_code, token_type=None):
    """
    Checks whether `auth_code` is a valid authentication code at the current time,
    based on the `raw_seed` (raw byte string representation of `seed`).
    """
    if not token_type:
        token_type = DEFAULT_TOKEN_TYPE
    return accept_totp(
        auth_code,
        hexlify(raw_seed),
        token_type,
        period=PERIOD,
        forward_drift=FORWARD_DRIFT,
        backward_drift=BACKWARD_DRIFT
    )[0]

def get_google_url(raw_seed, hostname=None):
    # Note: Google uses base32 for it's encoding rather than hex.
    b32secret = b32encode( raw_seed )
    if not hostname:
        from socket import gethostname
        hostname = gethostname()
    
    data = "otpauth://totp/%(hostname)s?secret=%(secret)s" % {
        "hostname":hostname,
        "secret":b32secret,
    }
    url = "https://chart.googleapis.com/chart?" + urlencode({
        "chs":"200x200",
        "chld":"M|0",
        "cht":"qr",
        "chl":data
    })
    return url

########NEW FILE########
__FILENAME__ = manage
#!/usr/bin/env python
from django.core.management import execute_manager
import imp
try:
    imp.find_module('settings') # Assumed to be in the same directory.
except ImportError:
    import sys
    sys.stderr.write("Error: Can't find the file 'settings.py' in the directory containing %r. It appears you've customized things.\nYou'll have to run django-admin.py, passing it your settings module.\n" % __file__)
    sys.exit(1)

import settings

if __name__ == "__main__":
    execute_manager(settings)

########NEW FILE########
__FILENAME__ = settings
import os
ROOT = os.path.dirname(os.path.realpath(__file__))

# Django settings for twofactor_demo project.

DEBUG = True
TEMPLATE_DEBUG = DEBUG

ADMINS = (
    # ('Your Name', 'your_email@example.com'),
)

MANAGERS = ADMINS

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join(ROOT, 'twofactor_demo.db'),
    }
}

# so that initial_data loads from this directory
FIXTURE_DIRS = [ROOT,]

# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
# On Unix systems, a value of None will cause Django to use the same
# timezone as the operating system.
# If running in a Windows environment this must be set to the same as your
# system time zone.
TIME_ZONE = 'America/Chicago'

# Language code for this installation. All choices can be found here:
# http://www.i18nguy.com/unicode/language-identifiers.html
LANGUAGE_CODE = 'en-us'

SITE_ID = 1

# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = True

# If you set this to False, Django will not format dates, numbers and
# calendars according to the current locale
USE_L10N = True

# Absolute filesystem path to the directory that will hold user-uploaded files.
# Example: "/home/media/media.lawrence.com/media/"
MEDIA_ROOT = ''

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash.
# Examples: "http://media.lawrence.com/media/", "http://example.com/media/"
MEDIA_URL = ''

# Absolute path to the directory static files should be collected to.
# Don't put anything in this directory yourself; store your static files
# in apps' "static/" subdirectories and in STATICFILES_DIRS.
# Example: "/home/media/media.lawrence.com/static/"
STATIC_ROOT = ''

# URL prefix for static files.
# Example: "http://media.lawrence.com/static/"
STATIC_URL = '/static/'

# URL prefix for admin static files -- CSS, JavaScript and images.
# Make sure to use a trailing slash.
# Examples: "http://foo.com/static/admin/", "/static/admin/".
ADMIN_MEDIA_PREFIX = '/static/admin/'

# Additional locations of static files
STATICFILES_DIRS = (
    # Put strings here, like "/home/html/static" or "C:/www/django/static".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
)

# List of finder classes that know how to find static files in
# various locations.
STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
#    'django.contrib.staticfiles.finders.DefaultStorageFinder',
)

# Make this unique, and don't share it with anybody.
SECRET_KEY = '0=#evq8bb97kj4$7q^a$gyo7lhs8i13((t_=y1v)96b_zcb1@*'

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
#     'django.template.loaders.eggs.Loader',
)

MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
)

ROOT_URLCONF = 'twofactor_demo.urls'

TEMPLATE_DIRS = (
    # Put strings here, like "/home/html/django_templates" or "C:/www/django/templates".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
    "/Users/mtigas/Code/django-twofactor/repo/twofactor_demo/templates",
)

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.admin',
    'django_twofactor',
    'twofactor_demo',
)

# A sample logging configuration. The only tangible logging
# performed by this configuration is to send an email to
# the site admins on every HTTP 500 error.
# See http://docs.djangoproject.com/en/dev/topics/logging for
# more details on how to customize your logging configuration.
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'mail_admins': {
            'level': 'ERROR',
            'class': 'django.utils.log.AdminEmailHandler'
        }
    },
    'loggers': {
        'django.request': {
            'handlers': ['mail_admins'],
            'level': 'ERROR',
            'propagate': True,
        },
    }
}


#AUTHENTICATION_BACKENDS = ('django.contrib.auth.backends.ModelBackend',)
AUTHENTICATION_BACKENDS = (
    'django_twofactor.auth_backends.TwoFactorAuthBackend',
)

# See twofactor_demo/README.mdown
TWOFACTOR_TOTP_OPTIONS = {
    #'period': 30, # default
    'forward_drift': 4, # allow a code from four "steps" (up to 2:00) in the future, in case of bad clock sync.
    'backward_drift': 2, # allow a code from two "steps" (up to 1:00) in the past, in case of bad clock sync.
}
# Make this any string. This should be like a SECRET_KEY that you never, ever change.
# If you want to make this really secure, check out twofactor_demo/README.mdown
# for ways to generate this.
# (NOTE: don't change this when running this demo)
#TWOFACTOR_ENCRYPTION_KEY = '=S$\'d!Dj@jXv-A;tR5TjDaYh1+Ug;"\'ou\'`iOS4M#_+.buNjbG'
TWOFACTOR_ENCRYPTION_KEY = ''

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import patterns, include, url
from django_twofactor.auth_forms import TwoFactorAuthenticationForm
from django.contrib.staticfiles.urls import staticfiles_urlpatterns

# Replace `admin.site` with `twofactor_admin_site` before doing autodiscover
# so that we can get the default auto-registered behavior BUT use our
# `AdminSite` subclass.
from django.contrib import admin
from django_twofactor.adminsite import twofactor_admin_site
admin.site = twofactor_admin_site
admin.autodiscover()

urlpatterns = patterns('',
    url(r'^admin/', include(admin.site.urls)),

    (r'^$', 'django.contrib.auth.views.login', {
        'template_name': 'login.html',
        'authentication_form': TwoFactorAuthenticationForm
    }),
    (r'^logout/$', 'django.contrib.auth.views.logout_then_login', {
        'login_url': '/'
    }),
) + staticfiles_urlpatterns()

########NEW FILE########
