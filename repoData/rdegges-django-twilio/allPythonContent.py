__FILENAME__ = admin
"""This module provides useful django admin hooks that allow you to manage
various components through the django admin panel (if enabled).
"""

from django.contrib import admin

from django_twilio.models import Caller, Credential


class CallerAdmin(admin.ModelAdmin):
    """This class provides admin panel integration for our
    :class:`django_twilio.models.Caller` model.
    """
    list_display = ('__unicode__', 'blacklisted')


admin.site.register(Caller, CallerAdmin)
admin.site.register(Credential)

########NEW FILE########
__FILENAME__ = client
# -*- coding: utf-8 -*-

"""Twilio REST client helpers."""
from django_twilio import settings

from twilio.rest import TwilioRestClient

twilio_client = TwilioRestClient(
    settings.TWILIO_ACCOUNT_SID,
    settings.TWILIO_AUTH_TOKEN, version='2010-04-01')

########NEW FILE########
__FILENAME__ = decorators
# -*- coding: utf-8 -*-

"""Useful decorators."""


from functools import wraps

from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from django.http import (
    HttpRequest, HttpResponse, HttpResponseForbidden, HttpResponseNotAllowed)

from twilio.twiml import Verb
from twilio.util import RequestValidator

from django_twilio import settings as django_twilio_settings
from django_twilio.utils import get_blacklisted_response


def twilio_view(f):
    """This decorator provides several helpful shortcuts for writing Twilio
    views.

        - It ensures that only requests from Twilio are passed through. This
          helps protect you from forged requests.

        - It ensures your view is exempt from CSRF checks via Django's
          @csrf_exempt decorator. This is necessary for any view that accepts
          POST requests from outside the local domain (eg: Twilio's servers).

        - It enforces the blacklist. If you've got any ``Caller``s who are
          blacklisted, any requests from them will be rejected.

        - It allows your view to (optionally) return TwiML to pass back to
          Twilio's servers instead of building a ``HttpResponse`` object
          manually.

        - It allows your view to (optionally) return any ``twilio.Verb`` object
          instead of building a ``HttpResponse`` object manually.

          .. note::
            The forgery protection checks ONLY happen if ``settings.DEBUG =
            False`` (aka, your site is in production).

    Usage::

        from twilio.twiml import Response

        @twilio_view
        def my_view(request):
            r = Response()
            r.message('Thanks for the SMS message!')
            return r
    """
    @csrf_exempt
    @wraps(f)
    def decorator(request_or_self, methods=['POST'],
                  blacklist=True, *args, **kwargs):

        class_based_view = not(isinstance(request_or_self, HttpRequest))
        if not class_based_view:
            request = request_or_self
        else:
            assert len(args) >= 1
            request = args[0]

        # Turn off Twilio authentication when explicitly requested, or in debug mode.
        # Otherwise things do not work properly. For more information see the docs.
        use_forgery_protection = (
            getattr(settings, 'DJANGO_TWILIO_FORGERY_PROTECTION', not settings.DEBUG))
        if use_forgery_protection:

            if request.method not in methods:
                return HttpResponseNotAllowed(request.method)

            # Forgery check
            try:
                validator = RequestValidator(
                    django_twilio_settings.TWILIO_AUTH_TOKEN)
                url = request.build_absolute_uri()
                signature = request.META['HTTP_X_TWILIO_SIGNATURE']
            except (AttributeError, KeyError):
                return HttpResponseForbidden()

            if request.method == 'POST':
                if not validator.validate(url, request.POST, signature):
                    return HttpResponseForbidden()
            if request.method == 'GET':
                if not validator.validate(url, request.GET, signature):
                    return HttpResponseForbidden()

        # Blacklist check
        if blacklist:
            blacklisted_resp = get_blacklisted_response(request)
            if blacklisted_resp:
                return blacklisted_resp

        response = f(request_or_self, *args, **kwargs)

        if isinstance(response, str):
            return HttpResponse(response, content_type='application/xml')
        elif isinstance(response, Verb):
            return HttpResponse(str(response), content_type='application/xml')
        else:
            return response
    return decorator

########NEW FILE########
__FILENAME__ = 0001_initial
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'Caller'
        db.create_table(u'django_twilio_caller', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('blacklisted', self.gf('django.db.models.fields.BooleanField')()),
            ('phone_number', self.gf('phonenumber_field.modelfields.PhoneNumberField')(unique=True, max_length=128)),
        ))
        db.send_create_signal(u'django_twilio', ['Caller'])

        # Adding model 'Credential'
        db.create_table(u'django_twilio_credential', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=30)),
            ('user', self.gf('django.db.models.fields.related.OneToOneField')(to=orm['auth.User'], unique=True)),
            ('account_sid', self.gf('django.db.models.fields.CharField')(max_length=34)),
            ('auth_token', self.gf('django.db.models.fields.CharField')(max_length=32)),
        ))
        db.send_create_signal(u'django_twilio', ['Credential'])

    def backwards(self, orm):
        # Deleting model 'Caller'
        db.delete_table(u'django_twilio_caller')

        # Deleting model 'Credential'
        db.delete_table(u'django_twilio_credential')

    models = {
        u'auth.group': {
            'Meta': {'object_name': 'Group'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        u'auth.permission': {
            'Meta': {'ordering': "(u'content_type__app_label', u'content_type__model', u'codename')", 'unique_together': "((u'content_type', u'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['contenttypes.ContentType']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        u'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "u'user_set'", 'blank': 'True', 'to': u"orm['auth.Group']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "u'user_set'", 'blank': 'True', 'to': u"orm['auth.Permission']"}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        u'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        u'django_twilio.caller': {
            'Meta': {'object_name': 'Caller'},
            'blacklisted': ('django.db.models.fields.BooleanField', [], {}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'phone_number': ('phonenumber_field.modelfields.PhoneNumberField', [], {'unique': 'True', 'max_length': '128'})
        },
        u'django_twilio.credential': {
            'Meta': {'object_name': 'Credential'},
            'account_sid': ('django.db.models.fields.CharField', [], {'max_length': '34'}),
            'auth_token': ('django.db.models.fields.CharField', [], {'max_length': '32'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '30'}),
            'user': ('django.db.models.fields.related.OneToOneField', [], {'to': u"orm['auth.User']", 'unique': 'True'})
        }
    }

    complete_apps = ['django_twilio']
########NEW FILE########
__FILENAME__ = models
# -*- coding: utf-8 -*-

from django.db import models
from django.conf import settings

from phonenumber_field.modelfields import PhoneNumberField


class Caller(models.Model):
    """ A caller is defined uniquely by their phone number.

    :param bool blacklisted: Designates whether the caller can use our
        services.
    :param char phone_number: Unique phone number in `E.164
        <http://en.wikipedia.org/wiki/E.164>`_ format.

    """
    blacklisted = models.BooleanField()
    phone_number = PhoneNumberField(unique=True)

    def __unicode__(self):
        name = str(self.phone_number)
        if self.blacklisted:
            name += ' (blacklisted)'
        return name


class Credential(models.Model):
    """ A Credential model is a set of SID / AUTH tokens for the Twilio.com API

        The Credential model can be used if a project uses more than one
        Twilio account, or provides Users with access to Twilio powered
        web apps that need their own custom credentials.

    :param char name: The name used to distinguish this credential
    :param char account_sid: The Twilio account_sid
    :param char auth_token: The Twilio auth_token
    :param key user: The user linked to this Credential

    """

    def __unicode__(self):
        return ' '.join([self.name, '-', self.account_sid])

    name = models.CharField(max_length=30)

    user = models.OneToOneField(settings.AUTH_USER_MODEL)

    account_sid = models.CharField(max_length=34)

    auth_token = models.CharField(max_length=32)

########NEW FILE########
__FILENAME__ = settings
# -*- coding: utf-8 -*-

"""django_twilio specific settings."""

from .utils import discover_twilio_creds

TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN = discover_twilio_creds()

########NEW FILE########
__FILENAME__ = client
from django.test import TestCase
from django.contrib.auth.models import User

from twilio.rest import TwilioRestClient

from django_twilio.client import twilio_client
from django_twilio.models import Credential
from django_twilio import settings
from django_twilio.utils import discover_twilio_creds


class TwilioClientTestCase(TestCase):

    def test_twilio_client_exists(self):
        self.assertIsInstance(twilio_client, TwilioRestClient)

    def test_twilio_client_sets_creds(self):
        self.assertEqual(
            twilio_client.auth,
            (settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN))

    def test_twilio_client_with_creds_model(self):
        self.user = User.objects.create(username='test', password='pass')
        self.creds = Credential.objects.create(
            name='Test Creds',
            account_sid='AAA',
            auth_token='BBB',
            user=self.user,
        )

        deets = discover_twilio_creds(user=self.user)

        self.assertEquals(deets[0], self.creds.account_sid)
        self.assertEquals(deets[1], self.creds.auth_token)

########NEW FILE########
__FILENAME__ = decorators
from hmac import new
from hashlib import sha1
from base64 import encodestring

from django.conf import settings
from django.http import HttpResponse
from django.test import Client, RequestFactory, TestCase
from django.test.utils import override_settings

from twilio.twiml import Response

from django_twilio import settings as django_twilio_settings
from django_twilio.tests.views import response_view, str_view, verb_view


class TwilioViewTestCase(TestCase):
    fixtures = ['django_twilio.json']
    urls = 'django_twilio.tests.urls'

    def setUp(self):
        self.client = Client(enforce_csrf_checks=True)
        self.factory = RequestFactory(enforce_csrf_checks=True)

        # Test URIs.
        self.uri = 'http://testserver/tests/decorators'
        self.str_uri = '/tests/decorators/str_view/'
        self.verb_uri = '/tests/decorators/verb_view/'
        self.response_uri = '/tests/decorators/response_view/'

        # Guarantee a value for the required configuration settings after each
        # test case.
        django_twilio_settings.TWILIO_ACCOUNT_SID = 'xxx'
        django_twilio_settings.TWILIO_AUTH_TOKEN = 'xxx'

        # Pre-calculate Twilio signatures for our test views.
        self.response_signature = encodestring(
            new(django_twilio_settings.TWILIO_AUTH_TOKEN,
                '%s/response_view/' % self.uri, sha1).digest()).strip()
        self.str_signature = encodestring(
            new(django_twilio_settings.TWILIO_AUTH_TOKEN,
                '%s/str_view/' % self.uri, sha1).digest()).strip()
        self.sig_with_from_field_normal_caller = encodestring(
            new(django_twilio_settings.TWILIO_AUTH_TOKEN,
                '%s/str_view/From+12222222222' % self.uri,
                sha1).digest()).strip()
        self.sig_with_from_field_blacklisted_caller = encodestring(
            new(django_twilio_settings.TWILIO_AUTH_TOKEN,
                '%s/str_view/From+13333333333' % self.uri,
                sha1).digest()).strip()
        self.verb_signature = encodestring(
            new(django_twilio_settings.TWILIO_AUTH_TOKEN,
                '%s/verb_view/' % self.uri, sha1).digest()).strip()

    def test_requires_post(self):
        debug_orig = settings.DEBUG
        settings.DEBUG = False
        self.assertEquals(self.client.get(self.str_uri).status_code, 405)
        self.assertEquals(self.client.head(self.str_uri).status_code, 405)
        self.assertEquals(self.client.options(self.str_uri).status_code, 405)
        self.assertEquals(self.client.put(self.str_uri).status_code, 405)
        self.assertEquals(self.client.delete(self.str_uri).status_code, 405)
        settings.DEBUG = True
        self.assertEquals(self.client.get(self.str_uri).status_code, 200)
        self.assertEquals(self.client.head(self.str_uri).status_code, 200)
        self.assertEquals(self.client.options(self.str_uri).status_code, 200)
        self.assertEquals(self.client.put(self.str_uri).status_code, 200)
        self.assertEquals(self.client.delete(self.str_uri).status_code, 200)
        settings.DEBUG = debug_orig

    def test_allows_post(self):
        request = self.factory.post(
            self.str_uri, HTTP_X_TWILIO_SIGNATURE=self.str_signature)
        self.assertEquals(str_view(request).status_code, 200)

    def test_decorator_preserves_metadata(self):
        self.assertEqual(str_view.__name__, 'str_view')

    def test_missing_settings_return_forbidden(self):
        del django_twilio_settings.TWILIO_ACCOUNT_SID
        del django_twilio_settings.TWILIO_AUTH_TOKEN
        debug_orig = settings.DEBUG
        settings.DEBUG = False
        self.assertEquals(self.client.post(self.str_uri).status_code, 403)
        settings.DEBUG = True
        self.assertEquals(self.client.post(self.str_uri).status_code, 200)
        settings.DEBUG = debug_orig

    def test_missing_signature_returns_forbidden(self):
        debug_orig = settings.DEBUG
        settings.DEBUG = False
        self.assertEquals(self.client.post(self.str_uri).status_code, 403)
        settings.DEBUG = True
        self.assertEquals(self.client.post(self.str_uri).status_code, 200)
        settings.DEBUG = debug_orig

    def test_incorrect_signature_returns_forbidden(self):
        debug_orig = settings.DEBUG
        settings.DEBUG = False
        request = self.factory.post(
            self.str_uri, HTTP_X_TWILIO_SIGNATURE='fakesignature')
        self.assertEquals(str_view(request).status_code, 403)
        settings.DEBUG = True
        self.assertEquals(str_view(request).status_code, 200)
        settings.DEBUG = debug_orig

    def test_no_from_field(self):
        request = self.factory.post(
            self.str_uri,
            HTTP_X_TWILIO_SIGNATURE=self.str_signature)
        self.assertEquals(str_view(request).status_code, 200)

    def test_from_field_no_caller(self):
        request = self.factory.post(
            self.str_uri, {'From': '+12222222222'},
            HTTP_X_TWILIO_SIGNATURE=self.sig_with_from_field_normal_caller)
        self.assertEquals(str_view(request).status_code, 200)

    def test_blacklist_works(self):
        debug_orig = settings.DEBUG
        settings.DEBUG = False
        request = self.factory.post(
            self.str_uri, {'From': '+13333333333'},
            HTTP_X_TWILIO_SIGNATURE=self.sig_with_from_field_blacklisted_caller)
        response = str_view(request)
        r = Response()
        r.reject()
        self.assertEquals(response.content, str(r))
        settings.DEBUG = True
        request = self.factory.post(
            self.str_uri, {'From': '+13333333333'},
            HTTP_X_TWILIO_SIGNATURE=self.sig_with_from_field_blacklisted_caller)
        response = str_view(request)
        r = Response()
        r.reject()
        self.assertEquals(response.content, str(r))
        settings.DEBUG = debug_orig

    def test_decorator_modifies_str(self):
        request = self.factory.post(
            self.str_uri,
            HTTP_X_TWILIO_SIGNATURE=self.str_signature)
        self.assertTrue(isinstance(str_view(request), HttpResponse))

    def test_decorator_modifies_verb(self):
        request = self.factory.post(
            self.verb_uri, HTTP_X_TWILIO_SIGNATURE=self.verb_signature)
        self.assertTrue(isinstance(verb_view(request), HttpResponse))

    def test_decorator_preserves_httpresponse(self):
        request = self.factory.post(
            self.response_uri, HTTP_X_TWILIO_SIGNATURE=self.response_signature)
        self.assertTrue(isinstance(response_view(request), HttpResponse))

    def test_override_forgery_protection_off_debug_off(self):
        with override_settings(DJANGO_TWILIO_FORGERY_PROTECTION=False, DEBUG=False):
            request = self.factory.post(self.str_uri)
            self.assertEquals(str_view(request).status_code, 200)

    def test_override_forgery_protection_off_debug_on(self):
        with override_settings(DJANGO_TWILIO_FORGERY_PROTECTION=False, DEBUG=True):
            request = self.factory.post(self.str_uri)
            self.assertEquals(str_view(request).status_code, 200)

    def test_override_forgery_protection_on_debug_off(self):
        with override_settings(DJANGO_TWILIO_FORGERY_PROTECTION=True, DEBUG=False):
            request = self.factory.post(self.str_uri)
            self.assertEquals(str_view(request).status_code, 403)

    def test_override_forgery_protection_on_debug_on(self):
        with override_settings(DJANGO_TWILIO_FORGERY_PROTECTION=True, DEBUG=True):
            request = self.factory.post(self.str_uri)
            self.assertEquals(str_view(request).status_code, 403)

########NEW FILE########
__FILENAME__ = models
from types import MethodType

from django.test import TestCase
from django.contrib.auth.models import User
from django_twilio.models import Caller, Credential


class CallerTestCase(TestCase):
    """Run tests against the :class:`django_twilio.models.Caller` model ."""

    def setUp(self):
        self.caller = Caller.objects.create(
            phone_number='12223334444', blacklisted=False)

    def test_has_unicode(self):
        self.assertTrue(isinstance(self.caller.__unicode__, MethodType))

    def test_unicode_returns_str(self):
        self.assertTrue(isinstance(self.caller.__unicode__(), str))

    def test_unicode_doesnt_contain_blacklisted(self):
        self.assertFalse('blacklisted' in self.caller.__unicode__())

    def test_unicode_contains_blacklisted(self):
        self.caller.blacklisted = True
        self.caller.save()
        self.assertTrue('blacklisted' in self.caller.__unicode__())

    def tearDown(self):
        self.caller.delete()


class CredentialTests(TestCase):

    def setUp(self):
        self.user = User.objects.create(username='test', password='pass')
        self.creds = Credential.objects.create(
            name='Test Creds',
            account_sid='XXX',
            auth_token='YYY',
            user=self.user,
        )

    def test_unicode(self):
        ''' Assert that unicode renders how we'd like it too '''
        self.assertEquals(self.creds.__unicode__(), 'Test Creds - XXX')

    def test_credentials_fields(self):
        ''' Assert the fields are working correctly '''
        self.assertEquals(self.creds.name, 'Test Creds')
        self.assertEquals(self.creds.account_sid, 'XXX')
        self.assertEquals(self.creds.auth_token, 'YYY')
        self.assertEquals(self.creds.user, self.user)

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls import patterns, url


# Test URLs for our ``django_twilio.decorators`` module.
urlpatterns = patterns(
    'django_twilio.tests.views',
    url(r'^tests/decorators/response_view/$', 'response_view'),
    url(r'^tests/decorators/str_view/$', 'str_view'),
    url(r'^tests/decorators/verb_view/$', 'verb_view'),
)

########NEW FILE########
__FILENAME__ = views
from hmac import new
from hashlib import sha1
from base64 import encodestring

import os

from django.http import HttpResponse
from django.test import Client, RequestFactory, TestCase
from twilio.twiml import Response

from django_twilio import settings
from django_twilio.decorators import twilio_view
from django_twilio.views import (
    conference, dial, gather, play, record, say, sms)


@twilio_view
def response_view(request):
    """A simple test view that returns a HttpResponse object."""
    return HttpResponse(
        '<Response><Message>Hello from Django</Message></Response>',
        content_type='text/xml')


@twilio_view
def str_view(request):
    """A simple test view that returns a string."""
    return '<Response><Message>Hi!</Message></Response>'


@twilio_view
def verb_view(request):
    """A simple test view that returns a ``twilio.Verb`` object."""
    r = Response()
    r.reject()
    return r


class SayTestCase(TestCase):

    def setUp(self):
        self.client = Client()
        self.factory = RequestFactory()

        # Test URIs.
        self.uri = 'http://testserver/tests/views'
        self.say_uri = '/tests/views/say/'

        # Guarantee a value for the required configuration settings after each
        # test case.
        settings.TWILIO_ACCOUNT_SID = 'xxx'
        settings.TWILIO_AUTH_TOKEN = 'xxx'

        # Pre-calculate Twilio signatures for our test views.
        self.signature = encodestring(
            new(settings.TWILIO_AUTH_TOKEN,
                '%s/say/' % self.uri, sha1).digest()).strip()

    def test_say_no_text(self):
        request = self.factory.post(
            self.say_uri, HTTP_X_TWILIO_SIGNATURE=self.signature)
        self.assertRaises(TypeError, say, request)

    def test_say_with_text(self):
        request = self.factory.post(
            self.say_uri, HTTP_X_TWILIO_SIGNATURE=self.signature)
        self.assertEquals(say(request, text='hi').status_code, 200)

    def tearDown(self):
        settings.TWILIO_ACCOUNT_SID = os.environ['TWILIO_ACCOUNT_SID']
        settings.TWILIO_AUTH_TOKEN = os.environ['TWILIO_AUTH_TOKEN']


class PlayTestCase(TestCase):

    def setUp(self):
        self.client = Client()
        self.factory = RequestFactory()

        # Test URIs.
        self.uri = 'http://testserver/tests/views'
        self.play_uri = '/tests/views/play/'

        # Guarantee a value for the required configuration settings after each
        # test case.
        settings.TWILIO_ACCOUNT_SID = 'xxx'
        settings.TWILIO_AUTH_TOKEN = 'xxx'

        # Pre-calculate twilio signatures for our test views.
        self.signature = encodestring(
            new(settings.TWILIO_AUTH_TOKEN,
                '%s/play/' % self.uri, sha1).digest()).strip()

    def test_play_no_url(self):
        request = self.factory.post(
            self.play_uri, HTTP_X_TWILIO_SIGNATURE=self.signature)
        self.assertRaises(TypeError, play, request)

    def test_play_with_url(self):
        request = self.factory.post(
            self.play_uri, HTTP_X_TWILIO_SIGNATURE=self.signature)
        self.assertEquals(
            play(request, url='http://b.com/b.wav').status_code, 200)

    def tearDown(self):
        settings.TWILIO_ACCOUNT_SID = os.environ['TWILIO_ACCOUNT_SID']
        settings.TWILIO_AUTH_TOKEN = os.environ['TWILIO_AUTH_TOKEN']


class GatherTestCase(TestCase):

    def setUp(self):
        self.client = Client()
        self.factory = RequestFactory()

        # Test URIs.
        self.uri = 'http://testserver/tests/views'
        self.gather_uri = '/tests/views/gather/'

        # Guarantee a value for the required configuration settings after each
        # test case.
        settings.TWILIO_ACCOUNT_SID = 'xxx'
        settings.TWILIO_AUTH_TOKEN = 'xxx'

        # Pre-calculate twilio signatures for our test views.
        self.signature = encodestring(
            new(settings.TWILIO_AUTH_TOKEN,
                '%s/gather/' % self.uri, sha1).digest()).strip()

    def test_gather(self):
        request = self.factory.post(
            self.gather_uri, HTTP_X_TWILIO_SIGNATURE=self.signature)
        self.assertEquals(gather(request).status_code, 200)

    def tearDown(self):
        settings.TWILIO_ACCOUNT_SID = os.environ['TWILIO_ACCOUNT_SID']
        settings.TWILIO_AUTH_TOKEN = os.environ['TWILIO_AUTH_TOKEN']


class RecordTestCase(TestCase):

    def setUp(self):
        self.client = Client()
        self.factory = RequestFactory()

        # Test URIs.
        self.uri = 'http://testserver/tests/views'
        self.record_uri = '/tests/views/record/'

        # Guarantee a value for the required configuration settings after each
        # test case.
        settings.TWILIO_ACCOUNT_SID = 'xxx'
        settings.TWILIO_AUTH_TOKEN = 'xxx'

        # Pre-calculate twilio signatures for our test views.
        self.signature = encodestring(
            new(settings.TWILIO_AUTH_TOKEN,
                '%s/record/' % self.uri, sha1).digest()).strip()

    def test_record(self):
        request = self.factory.post(
            self.record_uri, HTTP_X_TWILIO_SIGNATURE=self.signature)
        self.assertEquals(record(request).status_code, 200)

    def tearDown(self):
        settings.TWILIO_ACCOUNT_SID = os.environ['TWILIO_ACCOUNT_SID']
        settings.TWILIO_AUTH_TOKEN = os.environ['TWILIO_AUTH_TOKEN']


class SmsTestCase(TestCase):

    def setUp(self):
        self.client = Client()
        self.factory = RequestFactory()

        # Test URIs.
        self.uri = 'http://testserver/tests/views'
        self.sms_uri = '/tests/views/sms/'

        # Guarantee a value for the required configuration settings after each
        # test case.
        settings.TWILIO_ACCOUNT_SID = 'xxx'
        settings.TWILIO_AUTH_TOKEN = 'xxx'

        # Pre-calculate twilio signatures for our test views.
        self.signature = encodestring(
            new(settings.TWILIO_AUTH_TOKEN,
                '%s/sms/' % self.uri, sha1).digest()).strip()

    def test_sms_no_message(self):
        request = self.factory.post(
            self.sms_uri, HTTP_X_TWILIO_SIGNATURE=self.signature)
        self.assertRaises(TypeError, sms, request)

    def test_sms_with_message(self):
        request = self.factory.post(
            self.sms_uri, HTTP_X_TWILIO_SIGNATURE=self.signature)
        self.assertEquals(sms(request, message='test').status_code, 200)

    def tearDown(self):
        settings.TWILIO_ACCOUNT_SID = os.environ['TWILIO_ACCOUNT_SID']
        settings.TWILIO_AUTH_TOKEN = os.environ['TWILIO_AUTH_TOKEN']


class DialTestCase(TestCase):

    def setUp(self):
        self.client = Client()
        self.factory = RequestFactory()

        # Test URIs.
        self.uri = 'http://testserver/tests/views'
        self.dial_uri = '/tests/views/dial/'

        # Guarantee a value for the required configuration settings after each
        # test case.
        settings.TWILIO_ACCOUNT_SID = 'xxx'
        settings.TWILIO_AUTH_TOKEN = 'xxx'

        # Pre-calculate twilio signatures for our test views.
        self.signature = encodestring(
            new(settings.TWILIO_AUTH_TOKEN,
                '%s/dial/' % self.uri, sha1).digest()).strip()

    def test_dial_no_number(self):
        request = self.factory.post(
            self.dial_uri, HTTP_X_TWILIO_SIGNATURE=self.signature)
        self.assertRaises(TypeError, dial, request)

    def test_dial_with_number(self):
        request = self.factory.post(
            self.dial_uri, HTTP_X_TWILIO_SIGNATURE=self.signature)
        self.assertEquals(dial(
            request, number='+18182223333').status_code, 200)

    def tearDown(self):
        settings.TWILIO_ACCOUNT_SID = os.environ['TWILIO_ACCOUNT_SID']
        settings.TWILIO_AUTH_TOKEN = os.environ['TWILIO_AUTH_TOKEN']


class ConferenceTestCase(TestCase):

    def setUp(self):
        self.client = Client()
        self.factory = RequestFactory()

        # Test URIs.
        self.uri = 'http://testserver/tests/views'
        self.conf_uri = '/tests/views/conference/'

        # Guarantee a value for the required configuration settings after each
        # test case.
        settings.TWILIO_ACCOUNT_SID = 'xxx'
        settings.TWILIO_AUTH_TOKEN = 'xxx'

        # Pre-calculate twilio signatures for our test views.
        self.signature = encodestring(
            new(settings.TWILIO_AUTH_TOKEN,
                '%s/conference/' % self.uri, sha1).digest()).strip()

    def test_conference_no_name(self):
        request = self.factory.post(
            self.conf_uri, HTTP_X_TWILIO_SIGNATURE=self.signature)
        self.assertRaises(TypeError, conference, request)

    def test_conference_with_name(self):
        request = self.factory.post(
            self.conf_uri, HTTP_X_TWILIO_SIGNATURE=self.signature)
        self.assertEquals(conference(request, name='a').status_code, 200)

    def tearDown(self):
        settings.TWILIO_ACCOUNT_SID = os.environ['TWILIO_ACCOUNT_SID']
        settings.TWILIO_AUTH_TOKEN = os.environ['TWILIO_AUTH_TOKEN']

########NEW FILE########
__FILENAME__ = utils
# -*- coding: utf-8 -*-
"""Useful utility functions."""

import os

from django.http import HttpResponse
from django.conf import settings

from twilio.twiml import Response

from django_twilio.models import Caller, Credential


def discover_twilio_creds(user=None):
    """ Due to the multiple ways of providing SID / AUTH tokens through
        this package, this function will search in the various places that
        credentials might be stored.

        The order this is done in is:

        1. If a User is passed: the keys linked to the
           user model from the Credentials model in the database.
        2. Environment variables
        3. django.conf settings

        We recommend using enviornment variables were possible, it is the
        most secure option

    """

    SID = 'TWILIO_ACCOUNT_SID'
    AUTH = 'TWILIO_AUTH_TOKEN'

    if user:
        creds = Credential.objects.filter(user=user.id)
        if creds.exists():
            creds = creds[0]
            return (creds.account_sid, creds.auth_token)

    if SID and AUTH in os.environ:
        return (os.environ[SID], os.environ[AUTH])

    return (settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)


def get_blacklisted_response(request):
    """Analyze the incoming Twilio request to determine whether or not to
    reject services. We'll only reject services if the user requesting service
    is on our blacklist.

    :param obj request: The Django HttpRequest object to analyze.
    :rtype: HttpResponse.
    :returns: HttpResponse if the user requesting services is blacklisted, None
        otherwise.
    """
    try:
        caller = Caller.objects.get(phone_number=request.REQUEST['From'])
        if caller.blacklisted:
            r = Response()
            r.reject()
            return HttpResponse(str(r), content_type='application/xml')
    except (KeyError, Caller.DoesNotExist):
        pass

    return None

########NEW FILE########
__FILENAME__ = views
from twilio.twiml import Response
from django_twilio.decorators import twilio_view


@twilio_view
def say(request, text, voice=None, language=None, loop=None):
    """See: http://www.twilio.com/docs/api/twiml/say.

    Usage::

        # urls.py
        urlpatterns = patterns('',
            # ...
            url(r'^say/$', 'django_twilio.views.say', {'text': 'hello, world!'})
            # ...
        )
    """
    r = Response()
    r.say(text, voice=voice, language=language, loop=loop)
    return r


@twilio_view
def play(request, url, loop=None):
    """See: twilio's website: http://www.twilio.com/docs/api/twiml/play.

    Usage::

        # urls.py
        urlpatterns = patterns('',
            # ...
            url(r'^play/$', 'django_twilio.views.play', {
                    'url': 'http://blah.com/blah.wav',
            }),
            # ...
        )
    """
    r = Response()
    r.play(url, loop=loop)
    return r


@twilio_view
def gather(request, action=None, method='POST', num_digits=None, timeout=None,
           finish_on_key=None):
    """See: http://www.twilio.com/docs/api/twiml/gather.

    Usage::

        # urls.py
        urlpatterns = patterns('',
            # ...
            url(r'^gather/$', 'django_twilio.views.gather'),
            # ...
        )
    """
    r = Response()
    r.gather(action=action, method=method, numDigits=num_digits,
             timeout=timeout, finishOnKey=finish_on_key)
    return r


@twilio_view
def record(request, action=None, method='POST', timeout=None,
           finish_on_key=None, max_length=None, transcribe=None,
           transcribe_callback=None, play_beep=None):
    """See: http://www.twilio.com/docs/api/twiml/record.

    Usage::

        # urls.py
        urlpatterns = patterns('',
            # ...
            url(r'^record/$', 'django_twilio.views.record'),
            # ...
        )
    """
    r = Response()
    r.record(action=action, method=method, timeout=timeout,
             finishOnKey=finish_on_key, maxLength=max_length,
             transcribe=transcribe, transcribeCallback=transcribe_callback,
             playBeep=play_beep)
    return r


@twilio_view
def sms(request, message, to=None, sender=None, action=None, method='POST',
        status_callback=None):
    """See: http://www.twilio.com/docs/api/twiml/sms.

    Usage::

        # urls.py
        urlpatterns = patterns('',
            # ...
            url(r'^sms/$', 'django_twilio.views.sms', {
                'message': 'Hello, world!'
            }),
            # ...
        )
    """
    r = Response()
    r.message(msg=message, to=to, sender=sender, method='POST', action=action,
              statusCallback=status_callback)
    return r


@twilio_view
def dial(request, number, action=None, method='POST', timeout=None,
         hangup_on_star=None, time_limit=None, caller_id=None):
    """See: http://www.twilio.com/docs/api/twiml/dial.

    Usage::

        # urls.py
        urlpatterns = patterns('',
            # ...
            url(r'^dial/?(P<number>\\w+)/$', 'django_twilio.views.dial'),
            # ...
        )
    """
    r = Response()
    r.dial(number=number, action=action, method=method, timeout=timeout,
           hangupOnStar=hangup_on_star, timeLimit=time_limit,
           callerId=caller_id)
    return r


@twilio_view
def conference(request, name, muted=None, beep=None,
               start_conference_on_enter=None, end_conference_on_exit=None,
               wait_url=None, wait_method='POST', max_participants=None):
    """See: http://www.twilio.com/docs/api/twiml/conference.

    Usage::

        # urls.py
        urlpatterns = patterns('',
            # ...
            url(r'^conference/?(P<name>\\w+)/$', 'django_twilio.views.conference',
                    {'max_participants': 10}),
            # ...
        )
    """
    r = Response()
    r.dial().conference(name=name, muted=muted, beep=beep,
                        startConferenceOnEnter=start_conference_on_enter,
                        endConferenceOnExit=end_conference_on_exit,
                        waitUrl=wait_url, waitMethod=wait_method,
                        )
    return r

########NEW FILE########
__FILENAME__ = conf
#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# complexity documentation build configuration file, created by
# sphinx-quickstart on Tue Jul  9 22:26:36 2013.
#
# This file is execfile()d with the current directory set to its containing dir.
#
# Note that not all possible configuration values are present in this
# autogenerated file.
#
# All configuration values have a default; values that are commented out
# serve to show the default.

import sys, os

RTD_NEW_THEME = True

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#sys.path.insert(0, os.path.abspath('.'))

# Get the project root dir, which is the parent dir of this
cwd = os.getcwd()
project_root = os.path.dirname(cwd)

# Insert the project root dir as the first element in the PYTHONPATH.
# This lets us ensure that the source package is imported, and that its
# version is used.
sys.path.insert(0, project_root)

import django_twilio

# -- General configuration -----------------------------------------------------

# If your documentation needs a minimal Sphinx version, state it here.
#needs_sphinx = '1.0'

# Add any Sphinx extension module names here, as strings. They can be extensions
# coming with Sphinx (named 'sphinx.ext.*') or your custom ones.
extensions = ['sphinx.ext.autodoc', 'sphinx.ext.viewcode']

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# The suffix of source filenames.
source_suffix = '.rst'

# The encoding of source files.
#source_encoding = 'utf-8-sig'

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = u'django-twilio'
copyright = u'2012-2014, Randall Degges'

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
# The short X.Y version.
version = django_twilio.__version__
# The full version, including alpha/beta/rc tags.
release = django_twilio.__version__

# The language for content autogenerated by Sphinx. Refer to documentation
# for a list of supported languages.
#language = None

# There are two options for replacing |today|: either, you set today to some
# non-false value, then it is used:
#today = ''
# Else, today_fmt is used as the format for a strftime call.
#today_fmt = '%B %d, %Y'

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
exclude_patterns = ['_build']

# The reST default role (used for this markup: `text`) to use for all documents.
#default_role = None

# If true, '()' will be appended to :func: etc. cross-reference text.
#add_function_parentheses = True

# If true, the current module name will be prepended to all description
# unit titles (such as .. function::).
#add_module_names = True

# If true, sectionauthor and moduleauthor directives will be shown in the
# output. They are ignored by default.
#show_authors = False

# The name of the Pygments (syntax highlighting) style to use.
pygments_style = 'sphinx'

# A list of ignored prefixes for module index sorting.
#modindex_common_prefix = []

# If true, keep warnings as "system message" paragraphs in the built documents.
#keep_warnings = False


# -- Options for HTML output ---------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
html_theme = 'default'

# Theme options are theme-specific and customize the look and feel of a theme
# further.  For a list of options available for each theme, see the
# documentation.
#html_theme_options = {}

# Add any paths that contain custom themes here, relative to this directory.
#html_theme_path = []

# The name for this set of Sphinx documents.  If None, it defaults to
# "<project> v<release> documentation".
#html_title = None

# A shorter title for the navigation bar.  Default is the same as html_title.
#html_short_title = None

# The name of an image file (relative to this directory) to place at the top
# of the sidebar.
#html_logo = None

# The name of an image file (within the static path) to use as favicon of the
# docs.  This file should be a Windows icon file (.ico) being 16x16 or 32x32
# pixels large.
#html_favicon = None

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ['_static']

# If not '', a 'Last updated on:' timestamp is inserted at every page bottom,
# using the given strftime format.
#html_last_updated_fmt = '%b %d, %Y'

# If true, SmartyPants will be used to convert quotes and dashes to
# typographically correct entities.
#html_use_smartypants = True

# Custom sidebar templates, maps document names to template names.
#html_sidebars = {}

# Additional templates that should be rendered to pages, maps page names to
# template names.
#html_additional_pages = {}

# If false, no module index is generated.
#html_domain_indices = True

# If false, no index is generated.
#html_use_index = True

# If true, the index is split into individual pages for each letter.
#html_split_index = False

# If true, links to the reST sources are added to the pages.
#html_show_sourcelink = True

# If true, "Created using Sphinx" is shown in the HTML footer. Default is True.
#html_show_sphinx = True

# If true, "(C) Copyright ..." is shown in the HTML footer. Default is True.
#html_show_copyright = True

# If true, an OpenSearch description file will be output, and all pages will
# contain a <link> tag referring to it.  The value of this option must be the
# base URL from which the finished HTML is served.
#html_use_opensearch = ''

# This is the file name suffix for HTML files (e.g. ".xhtml").
#html_file_suffix = None

# Output file base name for HTML help builder.
htmlhelp_basename = 'django-twiliodoc'


# -- Options for LaTeX output --------------------------------------------------

latex_elements = {
# The paper size ('letterpaper' or 'a4paper').
#'papersize': 'letterpaper',

# The font size ('10pt', '11pt' or '12pt').
#'pointsize': '10pt',

# Additional stuff for the LaTeX preamble.
#'preamble': '',
}

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title, author, documentclass [howto/manual]).
latex_documents = [
  ('index', 'django-twilio.tex', u'django-twilio Documentation',
   u'Randall Degges', 'manual'),
]

# The name of an image file (relative to this directory) to place at the top of
# the title page.
#latex_logo = None

# For "manual" documents, if this is true, then toplevel headings are parts,
# not chapters.
#latex_use_parts = False

# If true, show page references after internal links.
#latex_show_pagerefs = False

# If true, show URL addresses after external links.
#latex_show_urls = False

# Documents to append as an appendix to all manuals.
#latex_appendices = []

# If false, no module index is generated.
#latex_domain_indices = True


# -- Options for manual page output --------------------------------------------

# One entry per manual page. List of tuples
# (source start file, name, description, authors, manual section).
man_pages = [
    ('index', 'django-twilio', u'django-twilio Documentation',
     [u'Randall, Degges', u'Paul Hallett'], 1)
]

# If true, show URL addresses after external links.
#man_show_urls = False


# -- Options for Texinfo output ------------------------------------------------

# Grouping the document tree into Texinfo files. List of tuples
# (source start file, target name, title, author,
#  dir menu entry, description, category)
texinfo_documents = [
  ('index', 'django-twilio', u'django-twilio Documentation',
   u'Randall Degges', 'django-twilio', 'Twilio integration for Django',
   'Miscellaneous'),
]

# Documents to append as an appendix to all manuals.
#texinfo_appendices = []

# If false, no module index is generated.
#texinfo_domain_indices = True

# How to display URL addresses: 'footnote', 'no', or 'inline'.
#texinfo_show_urls = 'footnote'

# If true, do not generate a @detailmenu in the "Top" node's menu.
#texinfo_no_detailmenu = False

########NEW FILE########
__FILENAME__ = run_tests
import sys

try:
    from django.conf import settings

    settings.configure(
        DEBUG=True,
        USE_TZ=True,
        DATABASES={
            "default": {
                "ENGINE": "django.db.backends.sqlite3",
            }
        },
        ROOT_URLCONF="django_twilio.tests.urls",
        INSTALLED_APPS=[
            "django.contrib.auth",
            "django.contrib.contenttypes",
            "django.contrib.sites",
            "django_twilio",
        ],
        SITE_ID=1,
        NOSE_ARGS=['-s'],
    )

    from django_nose import NoseTestSuiteRunner
except ImportError:
    raise ImportError(
        "To fix this error, run: pip install -r requirements.txt")


def run_tests(*test_args):
    if not test_args:
        test_args = ['django_twilio/tests']

    # Run tests
    test_runner = NoseTestSuiteRunner(verbosity=1)

    failures = test_runner.run_tests(test_args)

    if failures:
        sys.exit(failures)


if __name__ == '__main__':
    run_tests(*sys.argv[1:])

########NEW FILE########
__FILENAME__ = manage
#!/usr/bin/env python
import os
import sys

if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "test_project.settings")
    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)

########NEW FILE########
__FILENAME__ = settings
# Django settings for test_project project.

DEBUG = True
TEMPLATE_DEBUG = DEBUG

ADMINS = (
    # ('Your Name', 'your_email@example.com'),
)

MANAGERS = ADMINS

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3', # Add 'postgresql_psycopg2', 'postgresql', 'mysql', 'sqlite3' or 'oracle'.
        'NAME': 'default.db',                      # Or path to database file if using sqlite3.
        'USER': '',                      # Not used with sqlite3.
        'PASSWORD': '',                  # Not used with sqlite3.
        'HOST': '',                      # Set to empty string for localhost. Not used with sqlite3.
        'PORT': '',                      # Set to empty string for default. Not used with sqlite3.
    }
}

# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
# On Unix systems, a value of None will cause Django to use the same
# timezone as the operating system.
# If running in a Windows environment this must be set to the same as your
# system time zone.
TIME_ZONE = 'America/Los_Angeles'

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
SECRET_KEY = 'j1wd@qqodn-r9h&o@0jj!uw^#pm5wcdu2^cdsax=hm+-mk705p'

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

ROOT_URLCONF = 'test_project.urls'

TEMPLATE_DIRS = (
    # Put strings here, like "/home/html/django_templates" or "C:/www/django/templates".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
)

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.admin',
    'django.contrib.admindocs',

    # Use south for database migrations:
    'south',

    # Use django-nose for running our tests:
    'django_nose',

    # django-twilio, of course!
    'django_twilio',
)

# Nose test settings.
TEST_RUNNER = 'django_nose.NoseTestSuiteRunner'
NOSE_ARGS = ['--with-coverage', '--cover-package=django_twilio']

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

# django-twilio account credentials. These fields are required to use the REST
# API (initiate outbound calls and SMS messages).
TWILIO_ACCOUNT_SID = 'ACXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX'
TWILIO_AUTH_TOKEN = 'YYYYYYYYYYYYYYYYYYYYYYYYYYYYYYYY'

# The default callerid will be used for all outgoing phone calls and SMS
# messages if not explicitly specified. This number must be previously
# validated with twilio in order to work. See
# https://www.twilio.com/user/account/phone-numbers#
TWILIO_DEFAULT_CALLERID = 'NNNNNNNNNN'

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import patterns, include, url

# Uncomment the next two lines to enable the admin:
from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns('',
    # Examples:
    # url(r'^$', 'test_project.views.home', name='home'),
    # url(r'^test_project/', include('test_project.foo.urls')),

    # Uncomment the admin/doc line below to enable admin documentation:
    # url(r'^admin/doc/', include('django.contrib.admindocs.urls')),

    # Uncomment the next line to enable the admin:
    url(r'^admin/', include(admin.site.urls)),
)

########NEW FILE########
