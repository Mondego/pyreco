__FILENAME__ = auth_backends
from django.contrib.auth.backends import ModelBackend
from django.contrib.auth.models import User

class UrlCryptBackend(ModelBackend):
    
    def authenticate(self, decoded_data=None):
        try:
            return User.objects.get(id=decoded_data['user_id'])
        except User.DoesNotExist:
            return None

    def get_user(self, user_id):
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None
    

########NEW FILE########
__FILENAME__ = conf
import os

from django.conf import settings

SCRIPT_DIR = os.path.abspath(os.path.dirname(__file__))

SECRET_KEY = getattr(settings, 'SECRET_KEY', 'sekrit')
RUNNING_TESTS = getattr(settings, 'RUNNING_TESTS', False)

if RUNNING_TESTS:
    URLCRYPT_PRIVATE_KEY_PATH = os.path.join(SCRIPT_DIR, "test", "test_private_key")
    if not os.path.exists(URLCRYPT_PRIVATE_KEY_PATH):
        URLCRYPT_PRIVATE_KEY_PATH = None
else:
    URLCRYPT_PRIVATE_KEY_PATH = getattr(settings, 'URLCRYPT_PRIVATE_KEY_PATH', None)


URLCRYPT_USE_RSA_ENCRYPTION = URLCRYPT_PRIVATE_KEY_PATH is not None
URLCRYPT_LOGIN_URL = getattr(settings, 'URLCRYPT_LOGIN_URL', settings.LOGIN_URL)
URLCRYPT_RATE_LIMIT = getattr(settings, 'URLCRYPT_RATE_LIMIT', 60)
########NEW FILE########
__FILENAME__ = lib
import base64
import hashlib
import hmac
import time

try:
    from hashlib import sha1 as sha_hmac
except ImportError:
    import sha as sha_hmac

from django.contrib.auth.models import User

from urlcrypt.conf import SECRET_KEY, URLCRYPT_USE_RSA_ENCRYPTION

if URLCRYPT_USE_RSA_ENCRYPTION:
    import urlcrypt.rsa

# generate a key for obfuscation
# kind of ghetto, is there a better way to do this other than os.urandom?
OBFUSCATE_KEY = hashlib.sha512(SECRET_KEY).digest() + hashlib.sha512(SECRET_KEY[::-1]).digest()

def base64url_encode(text):
    padded_b64 = base64.urlsafe_b64encode(text)
    return padded_b64.replace('=', '') # = is a reserved char
    
def base64url_decode(raw_b64):
    # calculate padding characters
    if len(raw_b64) % 4 == 0:
        padding = ''
    else:
        padding = (4 - (len(raw_b64) % 4)) * '='
    padded_b64 = raw_b64 + padding
    return base64.urlsafe_b64decode(padded_b64)
    
def pack(*strings):
    assert '|' not in ''.join(strings)
    return '|'.join(strings)
    
def unpack(packed_string):
    return packed_string.split('|')

def obfuscate(text):
    # copy out our OBFUSCATE_KEY to the length of the text
    key = OBFUSCATE_KEY * (len(text)//len(OBFUSCATE_KEY) + 1)

    # XOR each character from our input with the corresponding character
    # from the key
    xor_gen = (chr(ord(t) ^ ord(k)) for t, k in zip(text, key))
    return ''.join(xor_gen)

deobfuscate = obfuscate

def encode_token(strings):
    secret_key = secret_key_f(*strings)
    signature = hmac.new(str(secret_key), pack(*strings), sha_hmac).hexdigest()
    packed_string = pack(signature, *strings)
    return obfuscate(packed_string)

def decode_token(token, keys):
    packed_string = deobfuscate(token)
    strings = unpack(packed_string)[1:]
    assert token == encode_token(strings)
    return dict(zip(keys, strings))

def secret_key_f(user_id, *args):
    # generate a secret key given the user id
    user = User.objects.get(id=int(user_id))
    return user.password + SECRET_KEY

def generate_login_token(user, url):
    strings = [str(user.id), url.strip(), str(int(time.time()))]
    token_byte_string = encode_token(strings)
    
    if URLCRYPT_USE_RSA_ENCRYPTION:
        token_byte_string = urlcrypt.rsa.encrypt(token_byte_string)
    
    return base64url_encode(token_byte_string)

def decode_login_token(token):
    token_byte_string = base64url_decode(str(token))
    
    if URLCRYPT_USE_RSA_ENCRYPTION:
        token_byte_string = urlcrypt.rsa.decrypt(token_byte_string)
        
    keys = ('user_id', 'url', 'timestamp')
    data = decode_token(token_byte_string, keys)
    data['user_id'] = int(data['user_id'])
    data['timestamp'] = int(data['timestamp'])
    return data

########NEW FILE########
__FILENAME__ = models

########NEW FILE########
__FILENAME__ = oaep
# from https://bugs.launchpad.net/pycrypto/+bug/328027

from math import ceil
from hashlib import sha1
from Crypto.Util.strxor import strxor
from Crypto.Util.number import long_to_bytes


def make_mgf1(hash):
    """Make an MFG1 function using the given hash function.

    Given a hash function implementing the standard hash function interface,
    this function returns a Mask Generation Function using that hash.
    """
    def mgf1(mgfSeed,maskLen):
        """Mask Generation Function based on a hash function.

        Given a seed byte string 'mgfSeed', this function will generate
        and return a mask byte string  of length 'maskLen' in a manner
        approximating a Random Oracle.

        The algorithm is from PKCS#1 version 2.1, appendix B.2.1.
        """
        hLen = hash().digest_size
        if maskLen > 2**32 * hLen:
            raise ValueError("mask too long")
        T = ""
        for counter in range(int(ceil(maskLen / (hLen*1.0)))):
            C = long_to_bytes(counter)
            C = ('\x00'*(4 - len(C))) + C
            assert len(C) == 4, "counter was too big"
            T += hash(mgfSeed + C).digest()
        assert len(T) >= maskLen, "generated mask was too short"
        return T[:maskLen]
    return mgf1


MGF1_SHA1 = make_mgf1(sha1)


class OAEP(object):
    """Class implementing OAEP encoding/decoding.

    This class can be used to encode/decode byte strings using the
    Optimal Asymmetic Encryption Padding Scheme.  It requires a source
    of random bytes, a hash function and a mask generation function.
    By default SHA-1 is used as the hash function, and MGF1-SHA1 is used
    as the mask generation function.

    The method 'encode' will encode a byte string using this padding
    scheme, and the complimenary method 'decode' will decode it.

    The algorithms are from PKCS#1 version 2.1, section 7.1
    """

    def __init__(self,randbytes,hash=sha1,mgf=MGF1_SHA1):
        self.randbytes = randbytes
        self.hash = hash
        self.mgf = mgf

    def encode(self,k,M,L=""):
        """Encode a message using OAEP.

        This method encodes a byte string 'M' using Optimal Asymmetric
        Encryption Padding.  The argument 'k' must be the size of the
        private key modulus in bytes.  If specified, 'L' is a label
        for the encoding.
        """
        # Calculate label hash, unless it is too long
        if L:
            limit = getattr(self.hash,"input_limit",None)
            if limit and len(L) > limit:
                raise ValueError("label too long")
        lHash = self.hash(L).digest()
        # Check length of message against size of key modulus
        mLen = len(M)
        hLen = len(lHash)
        if mLen > k - 2*hLen - 2:
            raise ValueError("message too long")
        # Perform the encoding
        PS = "\x00" * (k - mLen - 2*hLen - 2)
        DB = lHash + PS + "\x01" + M
        assert len(DB) == k - hLen - 1, "DB length is incorrect"
        seed = self.randbytes(hLen)
        dbMask = self.mgf(seed,k - hLen - 1)
        maskedDB = strxor(DB,dbMask)
        seedMask = self.mgf(maskedDB,hLen)
        maskedSeed = strxor(seed,seedMask)
        return "\x00" + maskedSeed + maskedDB

    def decode(self,k,EM,L=""):
        """Decode a message using OAEP.

        This method decodes a byte string 'EM' using Optimal Asymmetric
        Encryption Padding.  The argument 'k' must be the size of the
        private key modulus in bytes.  If specified, 'L' is the label
        used for the encoding.
        """
        # Generate label hash, for sanity checking
        lHash = self.hash(L).digest()
        hLen = len(lHash)
        # Split the encoded message
        Y = EM[0]
        maskedSeed = EM[1:hLen+1]
        maskedDB = EM[hLen+1:]
        # Perform the decoding
        seedMask = self.mgf(maskedDB,hLen)
        seed = strxor(maskedSeed,seedMask)
        dbMask = self.mgf(seed,k - hLen - 1)
        DB = strxor(maskedDB,dbMask)
        # Split the DB string
        lHash1 = DB[:hLen]
        x01pos = hLen
        while x01pos < len(DB) and DB[x01pos] != "\x01":
            x01pos += 1
        PS = DB[hLen:x01pos]
        M = DB[x01pos+1:]
        # All sanity-checking done at end, to avoid timing attacks
        valid = True
        if x01pos == len(DB):  # No \x01 byte
            valid = False
        if lHash1 != lHash:    # Mismatched label hash
            valid = False
        if Y != "\x00":        # Invalid leading byte
            valid = False
        if not valid:
            raise ValueError("decryption error")
        return M


def test_oaep():
    """Run through the OAEP encode/decode for lots of random values."""
    from os import urandom
    p = OAEP(urandom)
    for k in xrange(45,300):
        for i in xrange(0,1000):
            b = i % (k - 2*20 - 3)  # message length
            if b == 0:
                j = -1
            else:
                j = i % b           # byte to corrupt
            print "test %s:%s (%s bytes, corrupt at %s)" % (k,i,b,j)
            msg = urandom(b)
            pmsg = p.encode(k,msg)
            #  Test that padding actually does something
            assert msg != pmsg, "padded message was just the message"
            #  Test that padding is removed correctly
            assert p.decode(k,pmsg) == msg, "message was not decoded properly"
            #  Test that corrupted padding gives an error
            try:
                if b == 0: raise ValueError
                newb = urandom(1)
                while newb == pmsg[j]:
                    newb = urandom(1)
                pmsg2 = pmsg[:j] + newb + pmsg[j+1:]
                p.decode(k,pmsg2)
            except ValueError:
                pass
            else:
                raise AssertionError("corrupted padding was still decoded")


########NEW FILE########
__FILENAME__ = rsa
import os

from urlcrypt.conf import URLCRYPT_PRIVATE_KEY_PATH
from urlcrypt.oaep import OAEP

# load the private key from the specified file
from Crypto.PublicKey import RSA 
 
with open(URLCRYPT_PRIVATE_KEY_PATH) as f: 
    pem_private_key = f.read() 

PRIVATE_KEY = RSA.importKey(pem_private_key)
KEY_LENGTH_BYTES = int((PRIVATE_KEY.size() + 1) / 8)
PADDER = OAEP(os.urandom)
BLOCK_BYTES = KEY_LENGTH_BYTES - 2 * 20 - 2 # from oaep.py

def split_string(s, block_size):
    blocks = []
    start = 0
    while start < len(s):
        block = s[start:start+block_size]
        blocks.append(block)
        start += block_size
    return blocks

def encrypt(s):
    encrypted_blocks = []
    for block in split_string(s, BLOCK_BYTES):
        padded_block = PADDER.encode(KEY_LENGTH_BYTES, block) # will raise ValueError if token is too long
        encrypted_block = PRIVATE_KEY.encrypt(padded_block, None)[0]
        encrypted_blocks.append(encrypted_block)
    return ''.join(encrypted_blocks)
    
def decrypt(s):
    decrypted_blocks = []
    for block in split_string(s, KEY_LENGTH_BYTES):
        padded_block = '\x00' + PRIVATE_KEY.decrypt(block) # NUL byte is apparently dropped by decryption
        decrypted_block = PADDER.decode(KEY_LENGTH_BYTES, padded_block) # will raise ValueError on corrupt token
        decrypted_blocks.append(decrypted_block)
    return ''.join(decrypted_blocks)
########NEW FILE########
__FILENAME__ = urlcrypt_tags
from django import template
from django.contrib.sites.models import Site
from django.core.urlresolvers import reverse
from django.template.defaulttags import URLNode

from urlcrypt.conf import RUNNING_TESTS
from urlcrypt.lib import generate_login_token

register = template.Library()

class EncodedURLNode(URLNode):
    
    def __init__(self, user, *args, **kwargs):
        self.user = template.Variable(user)
        super(EncodedURLNode, self).__init__(*args, **kwargs)
    
    def render(self, context):
        url = super(EncodedURLNode, self).render(context)
        if self.asvar:
            url = context[self.asvar]
        user = self.user.resolve(context)
        token = generate_login_token(user, url)
        crypt_url = reverse('urlcrypt_redirect', args=(token,))
        if self.asvar:
            context[self.asvar] = crypt_url
            return ''
        return crypt_url

@register.tag
def encoded_url(parser, token):
    bits = token.split_contents()
    if len(bits) < 3:
        raise template.TemplateSyntaxError("'%s' takes at least two arguments"
                                  " (path to a view)" % bits[0])
    user = bits[1]
    viewname = bits[2]
    args = []
    kwargs = {}
    asvar = None

    if len(bits) > 3:
        bits = iter(bits[3:])
        for bit in bits:
            if bit == 'as':
                asvar = bits.next()
                break
            else:
                for arg in bit.split(","):
                    if '=' in arg:
                        k, v = arg.split('=', 1)
                        k = k.strip()
                        kwargs[k] = parser.compile_filter(v)
                    elif arg:
                        args.append(parser.compile_filter(arg))
    return EncodedURLNode(user, viewname, args, kwargs, asvar)

@register.simple_tag
def encode_url_string(user, url):
    if RUNNING_TESTS:
        domain = 'testserver'
    else:
        domain = Site.objects.get_current().domain
    protocol, suffix = url.split("://%s" % domain)
    token = generate_login_token(user, suffix)
    return "%s://%s" % (protocol, reverse('urlcrypt_redirect', args=(token,)))

########NEW FILE########
__FILENAME__ = tests
import re
import time

from django import template
from django.contrib.auth.models import User
from django.core.urlresolvers import reverse

from django.test import TestCase
from urlcrypt.lib import generate_login_token, decode_login_token, encode_token, base64url_encode
from urlcrypt.conf import URLCRYPT_LOGIN_URL, URLCRYPT_USE_RSA_ENCRYPTION

class UrlCryptTests(TestCase):
    
    def setUp(self):
        super(UrlCryptTests, self).setUp()
        self.test_user = User.objects.create_user('test', 'test@malinator.com', 'test')
    
    def test_login_token(self):
        token = generate_login_token(self.test_user, u'/users/following')
        data = decode_login_token(token)
        self.assertEquals(data['user_id'], self.test_user.id)
        self.assertEquals(data['url'], u'/users/following')

    def test_blank_unicode_password(self):
        self.test_user.password = u""
        self.test_user.save()
        self.assertEqual(type(self.test_user.password), type(u""))
        self.test_login_token()
    
    def test_rsa(self):
        if URLCRYPT_USE_RSA_ENCRYPTION:
            from urlcrypt import rsa
            assert rsa.decrypt(rsa.encrypt("test")) == "test"
            assert rsa.decrypt(rsa.encrypt("test"*100)) == "test"*100
    
    def test_login_token_failed_hax0r(self):
        fake_token = 'asdf;lhasdfdso'
        response = self.client.get(reverse('urlcrypt_redirect', args=(fake_token,)))
        self.assertRedirects(response, URLCRYPT_LOGIN_URL)
        
        fake_token = base64url_encode(encode_token([str(self.test_user.id), reverse('urlcrypt_test_view'), str(int(time.time()))]))
        response = self.client.get(reverse('urlcrypt_redirect', args=(fake_token,)))
        self.assertRedirects(response, URLCRYPT_LOGIN_URL)
            
    def assert_login_url(self, encoded_url, expected_url):
        response = self.client.get(expected_url)
        self.assertEquals(response.status_code, 302)
        response = self.client.get(encoded_url)
        self.assertRedirects(response, expected_url)
        response = self.client.get(expected_url)
        self.assertEquals(response.status_code, 200)
        
    def test_url_encoded_template_tag(self):
        
        text = """
        {% load urlcrypt_tags %}
        {% encoded_url test_user urlcrypt_test_view %}
        """
        t = template.Template(text)
        c = template.Context({'test_user': self.test_user})
        encoded_url = t.render(c).strip()
        self.assert_login_url(encoded_url, reverse('urlcrypt_test_view'))
    
    def test_url_encoded_template_tag_with_args(self):
        
        text = """
        {% load urlcrypt_tags %}
        {% encoded_url test_user urlcrypt_test_view_username test_user.username %}
        """
        t = template.Template(text)
        c = template.Context({'test_user': self.test_user})
        encoded_url = t.render(c).strip()
        self.assert_login_url(encoded_url, reverse('urlcrypt_test_view_username', args=(self.test_user.username,)))

    def test_url_encoded_template_tag_with_as_var(self):
        text = """
        {% load urlcrypt_tags %}
        {% encoded_url test_user urlcrypt_test_view_username test_user.username as myurl %}
        URL:{{ myurl }}:URL
        """
        t = template.Template(text)
        c = template.Context({'test_user': self.test_user})
        match = re.match("URL:(.+):URL", t.render(c).strip())
        self.assertTrue(bool(match))
        self.assert_login_url(match.group(1), reverse('urlcrypt_test_view_username', args=(self.test_user.username,)))
    
    def test_encode_url_string_template_tag(self):
        text = """
        {% load urlcrypt_tags %}
        {% encode_url_string test_user some_url %}
        """
        some_url = 'http://testserver%s' % reverse('urlcrypt_test_view_username', args=(self.test_user.username,))
        t = template.Template(text)
        c = template.Context({'test_user': self.test_user, 'some_url': some_url})
        encoded_url = t.render(c).strip()
        self.assert_login_url(encoded_url, reverse('urlcrypt_test_view_username', args=(self.test_user.username,)))
     

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import *
from urlcrypt.conf import RUNNING_TESTS

if RUNNING_TESTS:
    urlpatterns = patterns('urlcrypt.views',
        url(r'^test/view/$', 'test_view', name='urlcrypt_test_view'),  
        url(r'^test/view/(?P<username>.+)/$', 'test_view', name='urlcrypt_test_view_username'),  
    )
else:
    urlpatterns = patterns('')

urlpatterns += patterns('urlcrypt.views',
    url(r'^(?P<token>.+)/$', 'login_redirect', name='urlcrypt_redirect'),
) 
########NEW FILE########
__FILENAME__ = views
from django.contrib.auth import authenticate, login as auth_login
from django.contrib.auth.decorators import login_required
from django.core.cache import cache
from django.http import HttpResponseRedirect, HttpResponse, HttpResponseForbidden

from urlcrypt.conf import URLCRYPT_LOGIN_URL, URLCRYPT_RATE_LIMIT
from urlcrypt.lib import decode_login_token

# import encode_token and decode_token from correct backend

def rate_limit(num=60):
    """
    Limits the number of requests made by a unique visitor to this view to num per minute.
    """
    def decorator(func):
        def wrapper(request, *args, **kwargs):
            cache_key = 'rate_limit.%s' % request.session._session_key
            added = cache.add(cache_key, 1, timeout=60)
            if added:
                num_tries = 1
            else:
                num_tries = cache.incr(cache_key, delta=1)
            if num_tries > num:
                raise HttpResponseForbidden("Rate Limit Exceeded")
            return func(request, *args, **kwargs)
        return wrapper
    return decorator
    
@rate_limit(num=URLCRYPT_RATE_LIMIT)
def login_redirect(request, token):
    try:
        decoded_data = decode_login_token(token)
    except Exception, ex:
        return HttpResponseRedirect(URLCRYPT_LOGIN_URL)

    if request.user.is_authenticated() and request.user.id == decoded_data['user_id']:
        return HttpResponseRedirect(decoded_data['url'])
    
    user = authenticate(decoded_data=decoded_data)
    if user:
        auth_login(request, user)
        return HttpResponseRedirect(decoded_data['url'])
    else:
        return HttpResponseRedirect(URLCRYPT_LOGIN_URL)
    
@login_required
def test_view(request, username=None):
    return HttpResponse("ok")
########NEW FILE########
