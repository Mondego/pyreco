__FILENAME__ = client
import json

from pqauth import crypto


class ProtocolError(Exception):
    pass


class PQAuthClient(object):
    def __init__(self, client_key, server_key):
        self.client_key = client_key
        self.server_key = server_key

        self.server_key_fprint = crypto.public_key_fingerprint(self.server_key)
        self.client_key_fprint = crypto.public_key_fingerprint(self.client_key)

        self.client_guid = None
        self.server_guid = None
        self.expires = None


    @property
    def session_key(self):
        return "%s:%s" % (self.client_guid, self.server_guid)


    def get_hello_message(self):
        self.client_guid = crypto.random_guid()

        hello_message = {"client_guid": self.client_guid,
                         "client_key_fingerprint": self.client_key_fprint}

        return hello_message


    def process_hello_response(self, response):
        # Check the server send back the client_guid we sent.
        if response["client_guid"] != self.client_guid:
            message = ("Server did not send back the expected client_guid. "
                       "Expected: %s, Got: %s" %
                       (self.client_guid, response["client_guid"]))
            raise ProtocolError(message)

        # Check the server's stated fingerprint matches the one we know
        if response["server_key_fingerprint"] != self.server_key_fprint:
            message = ("Server did not send back the expected key fingerprint. "
                       "Expected: %s, Got: %s" %
                       (self.server_key_fprint,
                        response["server_key_fingerprint"]))
            raise ProtocolError(message)

        self.expires = response["expires"]
        self.server_guid = response["server_guid"]


    def get_confirmation_message(self):
        confirm_message = {"server_guid": self.server_guid}
        return confirm_message


    def encrypt_for_server(self, message):
        as_json = json.dumps(message)
        return crypto.rsa_encrypt(as_json, self.server_key)


    def decrypt_from_server(self, encrypted):
        decrypted = crypto.rsa_decrypt(encrypted, self.client_key)
        return json.loads(decrypted)


########NEW FILE########
__FILENAME__ = crypto
from binascii import hexlify
import uuid

from Crypto.Cipher import PKCS1_OAEP
from Crypto.PublicKey import RSA
from Crypto.Random import random
from paramiko.rsakey import RSAKey as ParamikoRSAKey


def load_key_file(path, passphrase=None):
    f = open(path, "rb")
    try:
        return rsa_key(f.read(), passphrase)
    finally:
        f.close()


def rsa_key(text, passphrase=None):
    return RSA.importKey(text, passphrase)


def public_key_fingerprint(key):
    # paramiko can compute the OpenSSH-style fingerprint
    # Only fingerprints the public key

    paramiko_key = ParamikoRSAKey(vals=(key.e, key.n))
    fp =  hexlify(paramiko_key.get_fingerprint())

    # OpenSSH puts a ":" character between every pair of hex-digits.
    # For whatever reason. Readability, I guess.
    openssh_fp = ":".join([a+b for a, b in zip(fp[::2], fp[1::2])])

    return openssh_fp


def rsa_encrypt(plaintext, receiver_public_key):
    cipher = PKCS1_OAEP.new(receiver_public_key)
    return cipher.encrypt(plaintext)


def rsa_decrypt(ciphertext, receiver_private_key):
    cipher = PKCS1_OAEP.new(receiver_private_key)
    return cipher.decrypt(ciphertext)


def random_guid():
    secure_random = random.getrandbits(128)
    random_uuid = uuid.UUID(int=secure_random)
    return str(random_uuid)

########NEW FILE########
__FILENAME__ = admin
from django.contrib import admin

from django_pqauth_server.models import PublicKey
from django_pqauth_server.models import PQAuthSession

admin.site.register(PublicKey)
admin.site.register(PQAuthSession)

########NEW FILE########
__FILENAME__ = keys
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

from pqauth.crypto import load_key_file
from pqauth.crypto import public_key_fingerprint

def load_server_key():
    try:
        key_path = settings.PQAUTH_SERVER_KEY
    except AttributeError:
        msg = "You must set settings.PQUATH_SERVER_KEY"
        raise ImproperlyConfigured(msg)

    key_password = None
    try:
        key_password = settings.PQAUTH_SERVER_KEY_PASSWORD
    except AttributeError:
        pass

    return load_key_file(key_path, key_password)

SERVER_KEY = load_server_key()
SERVER_KEY_FINGERPRINT = public_key_fingerprint(SERVER_KEY)

########NEW FILE########
__FILENAME__ = models
from django.contrib.auth.models import User
from django.db import models
from pqauth import crypto


class PublicKey(models.Model):
    user = models.ForeignKey(User, related_name="public_keys")

    # keys MD5-fingerprint to 47 characters, including colons for readability
    fingerprint = models.CharField(max_length=64, primary_key=True)
    ssh_key = models.TextField()

    @property
    def public_key(self):
        return crypto.rsa_key(self.ssh_key)

    def __unicode__(self):
        return self.fingerprint


class PQAuthSession(models.Model):
    server_guid = models.CharField(max_length=32, primary_key=True)
    client_guid = models.CharField(max_length=32)
    session_key = models.CharField(max_length=65, unique=True,
                                   null=True, blank=True)
    expires = models.DateTimeField(null=True, blank=True)

    user = models.ForeignKey(User, related_name="pqauth_sessions")

    def __unicode__(self):
        if not self.session_key:
            return "[Negotiating] %s, %s" % (self.server_guid, self.client_guid)
        else:
            return "[Established] %s" % self.session_key

########NEW FILE########
__FILENAME__ = protocol
from django.test import TestCase
from django.core.urlresolvers import reverse
from django.conf import settings

from pqauth import crypto
from pqauth.client import PQAuthClient
from pqauth.pqauth_django_server.views import hello
from pqauth.pqauth_django_server.views import confirm
from pqauth.pqauth_django_server.keys import SERVER_KEY
from pqauth.pqauth_django_server.models import PQAuthSession

CLIENT_KEY = crypto.load_key_file(settings.TEST_CLIENT_KEY)
EVIL_KEY = crypto.load_key_file(settings.TEST_EVIL_KEY)

def get_pqa_client():
    return PQAuthClient(CLIENT_KEY, SERVER_KEY)

def get_evil_pqa_client():
    return PQAuthClient(EVIL_KEY, SERVER_KEY)


class ProtocolTest(TestCase):
    fixtures = ["test_accounts.json"]

    def post_hello(self, pqa_client):
        plaintext_message = pqa_client.get_hello_message()
        client_hello = pqa_client.encrypt_for_server(plaintext_message)
        response = self.client.generic("POST", reverse(hello), data=client_hello)

        return response

    def test_sunshine_and_unicorns(self):
        pqa_client = get_pqa_client()
        hello_resp = self.post_hello(pqa_client)

        self.assertEquals(200, hello_resp.status_code)

        decrypted_hello_resp = pqa_client.decrypt_from_server(hello_resp.content)
        pqa_client.process_hello_response(decrypted_hello_resp)

        self.assertEquals(pqa_client.client_guid, decrypted_hello_resp["client_guid"])
        self.assertIsNone(decrypted_hello_resp["expires"])

        confirm_msg = pqa_client.encrypt_for_server(pqa_client.get_confirmation_message())
        confirm_resp = self.client.generic("POST", reverse(confirm), data=confirm_msg)
        self.assertEquals(200, confirm_resp.status_code)

        session = PQAuthSession.objects.get(session_key=pqa_client.session_key)
        self.assertIsNotNone(PQAuthSession)


    def test_unknown_client(self):
        # Unknown client
        # Server's all like "I have no memory of this place"

        evil_client = get_evil_pqa_client()
        hello_resp = self.post_hello(evil_client)

        self.assertEquals(403, hello_resp.status_code)


    def test_mystery_confirmation_guid(self):
        # Confirmation server_guid not in the DB
        pqa_client = get_pqa_client()
        unknown_confirmation = {"server_guid": crypto.random_guid()}
        encrypted = pqa_client.encrypt_for_server(unknown_confirmation)

        confirm_resp = self.client.generic("POST", reverse(confirm), data=encrypted)
        self.assertEquals(200, confirm_resp.status_code)

        n_sessions = PQAuthSession.objects.count()
        self.assertEquals(0, n_sessions)


    def test_bad_encryption(self):
        # Encrypted with a different pubkey
        # Client doesn't know where he is and is confused as hell

        stoned_client = PQAuthClient(CLIENT_KEY, EVIL_KEY)
        hello_resp = self.post_hello(stoned_client)

        self.assertEquals(400, hello_resp.status_code)

########NEW FILE########
__FILENAME__ = settings
import os

DIRNAME = os.path.dirname(__file__)

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3"
    }
}

INSTALLED_APPS = (
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "pqauth.pqauth_django_server"
)

SECRET_KEY = "chicken butt"

PQAUTH_SERVER_KEY = os.path.join(DIRNAME, "server.key")

ROOT_URLCONF = "pqauth.pqauth_django_server.urls"


TEST_CLIENT_KEY = os.path.join(DIRNAME, "client.key")
TEST_EVIL_KEY = os.path.join(DIRNAME, "evil.key")

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls import patterns, url

from pqauth.pqauth_django_server import views

urlpatterns = patterns(
    "",
    url(r"^public-key", views.public_key),
    url(r"^hello", views.hello),
    url(r"^confirm", views.confirm)
)

########NEW FILE########
__FILENAME__ = views
import json

from django.http import HttpResponse
from django.http import HttpResponseBadRequest
from django.http import HttpResponseForbidden
from django.views.decorators.http import require_POST
from django.views.decorators.http import require_safe
from django.views.decorators.csrf import csrf_exempt

from pqauth.crypto import rsa_decrypt
from pqauth.crypto import rsa_encrypt
from pqauth.crypto import random_guid

from pqauth.pqauth_django_server.keys import SERVER_KEY
from pqauth.pqauth_django_server.keys import SERVER_KEY_FINGERPRINT
from pqauth.pqauth_django_server.models import PublicKey
from pqauth.pqauth_django_server.models import PQAuthSession


def encrypted_json_post(view_func):
    def inner(request, *args, **kwargs):
        try:
            decrypted_body = rsa_decrypt(request.body, SERVER_KEY)
            request.decrypted_json = json.loads(decrypted_body)
            return view_func(request, *args, **kwargs)
        except ValueError:
            msg = ("This endpoint expects a JSON object, "
                   "encrypted with the server's public RSA key")
            return HttpResponseBadRequest(msg)
    return csrf_exempt(require_POST(inner))


@require_safe
def public_key(_):
    # This only exports the public part of the key
    key_text = SERVER_KEY.exportKey(format="OpenSSH")
    return HttpResponse(key_text, mimetype="text/plain")


@encrypted_json_post
def hello(request):
    client_hello = request.decrypted_json
    try:
        client_key = PublicKey.objects.get(
            fingerprint=client_hello["client_key_fingerprint"])
    except PublicKey.DoesNotExist:
        return HttpResponseForbidden("Unknown client: %s" %
                                     client_hello["client_key_fingerprint"])

    response = {"client_guid": client_hello["client_guid"],
                "server_guid": random_guid(),
                "expires": None,
                "server_key_fingerprint": SERVER_KEY_FINGERPRINT}

    started_session = PQAuthSession(server_guid=response["server_guid"],
                                    client_guid=response["client_guid"],
                                    user=client_key.user)
    started_session.save()

    encrypted_response = rsa_encrypt(json.dumps(response),
                                     client_key.public_key)

    return HttpResponse(encrypted_response,
                        mimetype="application/pqauth-encrypted")


@encrypted_json_post
def confirm(request):
    confirm = request.decrypted_json
    guid = confirm["server_guid"]

    try:
        started_session = PQAuthSession.objects.get(server_guid=guid)
        started_session.session_key = "%s:%s" % (started_session.client_guid,
                                                 started_session.server_guid)
        started_session.save()
    except PQAuthSession.DoesNotExist:
        pass

    # It's important to return HTTP 200 here whether or no the confirmation
    # succeeded. If you return an error on an unrecognized server_guid, it
    # could help an attacker brute-force the session keys
    # (by notifying them that they've got half of it)

    return HttpResponse()

########NEW FILE########
