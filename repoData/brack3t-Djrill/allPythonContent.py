__FILENAME__ = admin
from django.contrib import admin

from djrill.views import (DjrillIndexView, DjrillSendersListView,
                          DjrillTagListView,
                          DjrillUrlListView)

# Only try to register Djrill admin views if DjrillAdminSite
# or django-adminplus is in use
if hasattr(admin.site,'register_view'):
    admin.site.register_view("djrill/senders/", DjrillSendersListView.as_view(),
                             "djrill_senders", "senders")
    admin.site.register_view("djrill/status/", DjrillIndexView.as_view(),
						 	 "djrill_status", "status")
    admin.site.register_view("djrill/tags/", DjrillTagListView.as_view(),
							 "djrill_tags", "tags")
    admin.site.register_view("djrill/urls/", DjrillUrlListView.as_view(),
							 "djrill_urls", "urls")

########NEW FILE########
__FILENAME__ = compat
# For python 3 compatibility, see http://python3porting.com/problems.html#nicer-solutions
import sys

if sys.version < '3':
    def b(x):
        return x
else:
    import codecs

    def b(x):
        return codecs.latin_1_encode(x)[0]
########NEW FILE########
__FILENAME__ = exceptions
from requests import HTTPError


class MandrillAPIError(HTTPError):
    """Exception for unsuccessful response from Mandrill API."""
    def __init__(self, status_code, response=None, log_message=None, *args, **kwargs):
        super(MandrillAPIError, self).__init__(*args, **kwargs)
        self.status_code = status_code
        self.response = response  # often contains helpful Mandrill info
        self.log_message = log_message

    def __str__(self):
        message = "Mandrill API response %d" % self.status_code
        if self.log_message:
            message += "\n" + self.log_message
        if self.response:
            message += "\nResponse: " + getattr(self.response, 'content', "")
        return message


class NotSupportedByMandrillError(ValueError):
    """Exception for email features that Mandrill doesn't support.

    This is typically raised when attempting to send a Django EmailMessage that
    uses options or values you might expect to work, but that are silently
    ignored by or can't be communicated to Mandrill's API. (E.g., non-HTML
    alternative parts.)

    It's generally *not* raised for Mandrill-specific features, like limitations
    on Mandrill tag names or restrictions on from emails. (Djrill expects
    Mandrill to return an API error for these where appropriate, and tries to
    avoid duplicating Mandrill's validation logic locally.)

    """

########NEW FILE########
__FILENAME__ = forms

########NEW FILE########
__FILENAME__ = djrill
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.core.mail.backends.base import BaseEmailBackend
from django.core.mail.message import sanitize_address, DEFAULT_ATTACHMENT_MIME_TYPE

# Oops: this file has the same name as our app, and cannot be renamed.
#from djrill import MANDRILL_API_URL, MandrillAPIError, NotSupportedByMandrillError
from ... import MANDRILL_API_URL, MandrillAPIError, NotSupportedByMandrillError

from base64 import b64encode
from datetime import date, datetime
from email.mime.base import MIMEBase
from email.utils import parseaddr
import json
import mimetypes
import requests

DjrillBackendHTTPError = MandrillAPIError # Backwards-compat Djrill<=0.2.0


class JSONDateUTCEncoder(json.JSONEncoder):
    """JSONEncoder that encodes dates in string format used by Mandrill.

    datetime becomes "YYYY-MM-DD HH:MM:SS"
             converted to UTC, if timezone-aware
             microseconds removed
    date     becomes "YYYY-MM-DD 00:00:00"
    """
    def default(self, obj):
        if isinstance(obj, datetime):
            dt = obj.replace(microsecond=0)
            if dt.utcoffset() is not None:
                dt = (dt - dt.utcoffset()).replace(tzinfo=None)
            return dt.isoformat(' ')
        elif isinstance(obj, date):
            return obj.isoformat() + ' 00:00:00'
        return super(JSONDateUTCEncoder, self).default(obj)


class DjrillBackend(BaseEmailBackend):
    """
    Mandrill API Email Backend
    """

    def __init__(self, **kwargs):
        """
        Set the API key, API url and set the action url.
        """
        super(DjrillBackend, self).__init__(**kwargs)
        self.api_key = getattr(settings, "MANDRILL_API_KEY", None)
        self.api_url = MANDRILL_API_URL

        self.subaccount = getattr(settings, "MANDRILL_SUBACCOUNT", None)

        if not self.api_key:
            raise ImproperlyConfigured("You have not set your mandrill api key "
                "in the settings.py file.")

        self.api_send = self.api_url + "/messages/send.json"
        self.api_send_template = self.api_url + "/messages/send-template.json"

    def send_messages(self, email_messages):
        if not email_messages:
            return 0

        num_sent = 0
        for message in email_messages:
            sent = self._send(message)

            if sent:
                num_sent += 1

        return num_sent

    def _send(self, message):
        if not message.recipients():
            return False

        api_url = self.api_send
        api_params = {
            "key": self.api_key,
        }

        try:
            msg_dict = self._build_standard_message_dict(message)
            self._add_mandrill_options(message, msg_dict)
            if getattr(message, 'alternatives', None):
                self._add_alternatives(message, msg_dict)
            self._add_attachments(message, msg_dict)
            api_params['message'] = msg_dict

            # check if template is set in message to send it via
            # api url: /messages/send-template.json
            if hasattr(message, 'template_name'):
                api_url = self.api_send_template
                api_params['template_name'] = message.template_name
                api_params['template_content'] = \
                    self._expand_merge_vars(getattr(message, 'template_content', {}))

            self._add_mandrill_toplevel_options(message, api_params)

        except NotSupportedByMandrillError:
            if not self.fail_silently:
                raise
            return False

        response = requests.post(api_url, data=json.dumps(api_params, cls=JSONDateUTCEncoder))

        if response.status_code != 200:

            # add a mandrill_response for the sake of being explicit
            message.mandrill_response = None

            if not self.fail_silently:
                raise MandrillAPIError(
                    status_code=response.status_code,
                    response=response,
                    log_message="Failed to send a message to %s, from %s" %
                                (msg_dict['to'], msg_dict['from_email']))
            return False

        # add the response from mandrill to the EmailMessage so callers can inspect it
        message.mandrill_response = response.json()

        return True

    def _build_standard_message_dict(self, message):
        """Create a Mandrill send message struct from a Django EmailMessage.

        Builds the standard dict that Django's send_mail and send_mass_mail
        use by default. Standard text email messages sent through Django will
        still work through Mandrill.

        Raises NotSupportedByMandrillError for any standard EmailMessage
        features that cannot be accurately communicated to Mandrill.
        """
        sender = sanitize_address(message.from_email, message.encoding)
        from_name, from_email = parseaddr(sender)

        to_list = self._make_mandrill_to_list(message, message.to, "to")
        to_list += self._make_mandrill_to_list(message, message.cc, "cc")
        to_list += self._make_mandrill_to_list(message, message.bcc, "bcc")

        content = "html" if message.content_subtype == "html" else "text"
        msg_dict = {
            content: message.body,
            "to": to_list
        }

        if not getattr(message, 'use_template_from', False):
            msg_dict["from_email"] = from_email
            if from_name:
                msg_dict["from_name"] = from_name

        if not getattr(message, 'use_template_subject', False):
            msg_dict["subject"] = message.subject

        if message.extra_headers:
            msg_dict["headers"] = message.extra_headers

        return msg_dict

    def _add_mandrill_toplevel_options(self, message, api_params):
        """Extend api_params to include Mandrill global-send options set on message"""
        # Mandrill attributes that can be copied directly:
        mandrill_attrs = [
            'async', 'ip_pool', 'send_at'
        ]
        for attr in mandrill_attrs:
            if hasattr(message, attr):
                api_params[attr] = getattr(message, attr)

    def _make_mandrill_to_list(self, message, recipients, recipient_type="to"):
        """Create a Mandrill 'to' field from a list of emails.

        Parses "Real Name <address@example.com>" format emails.
        Sanitizes all email addresses.
        """
        parsed_rcpts = [parseaddr(sanitize_address(addr, message.encoding))
                        for addr in recipients]
        return [{"email": to_email, "name": to_name, "type": recipient_type}
                for (to_name, to_email) in parsed_rcpts]

    def _add_mandrill_options(self, message, msg_dict):
        """Extend msg_dict to include Mandrill per-message options set on message"""
        # Mandrill attributes that can be copied directly:
        mandrill_attrs = [
            'from_name', # overrides display name parsed from from_email above
            'important',
            'track_opens', 'track_clicks', 'auto_text', 'auto_html',
            'inline_css', 'url_strip_qs',
            'tracking_domain', 'signing_domain', 'return_path_domain',
            'tags', 'preserve_recipients', 'view_content_link', 'subaccount',
            'google_analytics_domains', 'google_analytics_campaign',
            'metadata']

        if self.subaccount:
            msg_dict['subaccount'] = self.subaccount

        for attr in mandrill_attrs:
            if hasattr(message, attr):
                msg_dict[attr] = getattr(message, attr)

        # Allow simple python dicts in place of Mandrill
        # [{name:name, value:value},...] arrays...
        if hasattr(message, 'global_merge_vars'):
            msg_dict['global_merge_vars'] = \
                self._expand_merge_vars(message.global_merge_vars)
        if hasattr(message, 'merge_vars'):
            # For testing reproducibility, we sort the recipients
            msg_dict['merge_vars'] = [
                { 'rcpt': rcpt,
                  'vars': self._expand_merge_vars(message.merge_vars[rcpt]) }
                for rcpt in sorted(message.merge_vars.keys())
            ]
        if hasattr(message, 'recipient_metadata'):
            # For testing reproducibility, we sort the recipients
            msg_dict['recipient_metadata'] = [
                { 'rcpt': rcpt, 'values': message.recipient_metadata[rcpt] }
                for rcpt in sorted(message.recipient_metadata.keys())
            ]

    def _expand_merge_vars(self, vardict):
        """Convert a Python dict to an array of name-content used by Mandrill.

        { name: value, ... } --> [ {'name': name, 'content': value }, ... ]
        """
        # For testing reproducibility, we sort the keys
        return [{'name': name, 'content': vardict[name]}
                for name in sorted(vardict.keys())]

    def _add_alternatives(self, message, msg_dict):
        """
        There can be only one! ... alternative attachment, and it must be text/html.

        Since mandrill does not accept image attachments or anything other
        than HTML, the assumption is the only thing you are attaching is
        the HTML output for your email.
        """
        if len(message.alternatives) > 1:
            raise NotSupportedByMandrillError(
                "Too many alternatives attached to the message. "
                "Mandrill only accepts plain text and html emails.")

        (content, mimetype) = message.alternatives[0]
        if mimetype != 'text/html':
            raise NotSupportedByMandrillError(
                "Invalid alternative mimetype '%s'. "
                "Mandrill only accepts plain text and html emails."
                % mimetype)

        msg_dict['html'] = content

    def _add_attachments(self, message, msg_dict):
        """Extend msg_dict to include any attachments in message"""
        if message.attachments:
            str_encoding = message.encoding or settings.DEFAULT_CHARSET
            mandrill_attachments = []
            mandrill_embedded_images = []
            for attachment in message.attachments:
                att_dict, is_embedded = self._make_mandrill_attachment(attachment, str_encoding)
                if is_embedded:
                    mandrill_embedded_images.append(att_dict)
                else:
                    mandrill_attachments.append(att_dict)
            if len(mandrill_attachments) > 0:
                msg_dict['attachments'] = mandrill_attachments
            if len(mandrill_embedded_images) > 0:
                msg_dict['images'] = mandrill_embedded_images

    def _make_mandrill_attachment(self, attachment, str_encoding=None):
        """Returns EmailMessage.attachments item formatted for sending with Mandrill.

        Returns mandrill_dict, is_embedded_image:
        mandrill_dict: {"type":..., "name":..., "content":...}
        is_embedded_image: True if the attachment should instead be handled as an inline image.

        """
        # Note that an attachment can be either a tuple of (filename, content,
        # mimetype) or a MIMEBase object. (Also, both filename and mimetype may
        # be missing.)
        is_embedded_image = False
        if isinstance(attachment, MIMEBase):
            name = attachment.get_filename()
            content = attachment.get_payload(decode=True)
            mimetype = attachment.get_content_type()
            # Treat image attachments that have content ids as embedded:
            if attachment.get_content_maintype() == "image" and attachment["Content-ID"] is not None:
                is_embedded_image = True
                name = attachment["Content-ID"]
        else:
            (name, content, mimetype) = attachment

        # Guess missing mimetype from filename, borrowed from
        # django.core.mail.EmailMessage._create_attachment()
        if mimetype is None and name is not None:
            mimetype, _ = mimetypes.guess_type(name)
        if mimetype is None:
            mimetype = DEFAULT_ATTACHMENT_MIME_TYPE

        # b64encode requires bytes, so let's convert our content.
        try:
            if isinstance(content, unicode):
                # Python 2.X unicode string
                content = content.encode(str_encoding)
        except NameError:
            # Python 3 doesn't differentiate between strings and unicode
            # Convert python3 unicode str to bytes attachment:
            if isinstance(content, str):
                content = content.encode(str_encoding)

        content_b64 = b64encode(content)

        mandrill_attachment = {
            'type': mimetype,
            'name': name or "",
            'content': content_b64.decode('ascii'),
        }
        return mandrill_attachment, is_embedded_image

########NEW FILE########
__FILENAME__ = models

########NEW FILE########
__FILENAME__ = signals
from django.dispatch import Signal

webhook_event = Signal(providing_args=['event_type', 'data'])

########NEW FILE########
__FILENAME__ = djrill_future
# Future templatetags library that is also backwards compatible with
# older versions of Django (so long as Djrill's code is compatible
# with the future behavior).

from django import template

# Django 1.8 changes autoescape behavior in cycle tag.
# Djrill has been compatible with future behavior all along.
try:
    from django.templatetags.future import cycle
except ImportError:
    from django.template.defaulttags import cycle


register = template.Library()
register.tag(cycle)

########NEW FILE########
__FILENAME__ = admin_urls
try:
    from django.conf.urls import include, patterns, url
except ImportError:
    # Django 1.3
    from django.conf.urls.defaults import include, patterns, url

from django.contrib import admin

from djrill import DjrillAdminSite

admin.site = DjrillAdminSite()
admin.autodiscover()

urlpatterns = patterns('',
    url(r'^admin/', include(admin.site.urls)),
)

########NEW FILE########
__FILENAME__ = mock_backend
import json
from mock import patch

from django.test import TestCase

from .utils import override_settings


@override_settings(MANDRILL_API_KEY="FAKE_API_KEY_FOR_TESTING",
                   EMAIL_BACKEND="djrill.mail.backends.djrill.DjrillBackend")
class DjrillBackendMockAPITestCase(TestCase):
    """TestCase that uses Djrill EmailBackend with a mocked Mandrill API"""

    class MockResponse:
        """requests.post return value mock sufficient for DjrillBackend"""
        def __init__(self, status_code=200, content="{}", json=None):
            self.status_code = status_code
            self.content = content
            self._json = json if json is not None else ['']

        def json(self):
            return self._json

    def setUp(self):
        self.patch = patch('requests.post', autospec=True)
        self.mock_post = self.patch.start()
        self.mock_post.return_value = self.MockResponse()

    def tearDown(self):
        self.patch.stop()

    def assert_mandrill_called(self, endpoint):
        """Verifies the (mock) Mandrill API was called on endpoint.

        endpoint is a Mandrill API, e.g., "/messages/send.json"
        """
        # This assumes the last (or only) call to requests.post is the
        # Mandrill API call of interest.
        if self.mock_post.call_args is None:
            raise AssertionError("Mandrill API was not called")
        (args, kwargs) = self.mock_post.call_args
        try:
            post_url = kwargs.get('url', None) or args[0]
        except IndexError:
            raise AssertionError("requests.post was called without an url (?!)")
        if not post_url.endswith(endpoint):
            raise AssertionError(
                "requests.post was not called on %s\n(It was called on %s)"
                % (endpoint, post_url))

    def get_api_call_data(self):
        """Returns the data posted to the Mandrill API.

        Fails test if API wasn't called.
        """
        if self.mock_post.call_args is None:
            raise AssertionError("Mandrill API was not called")
        (args, kwargs) = self.mock_post.call_args
        try:
            post_data = kwargs.get('data', None) or args[1]
        except IndexError:
            raise AssertionError("requests.post was called without data")
        return json.loads(post_data)



########NEW FILE########
__FILENAME__ = test_admin
import sys

from django.test import TestCase
from django.contrib.auth.models import User
from django.contrib import admin

from djrill.tests.mock_backend import DjrillBackendMockAPITestCase


def reset_admin_site():
    """Return the Django admin globals to their original state"""
    admin.site = admin.AdminSite() # restore default
    if 'djrill.admin' in sys.modules:
        del sys.modules['djrill.admin'] # force autodiscover to re-import


class DjrillAdminTests(DjrillBackendMockAPITestCase):
    """Test the Djrill admin site"""

    # These tests currently just verify that the admin site pages load
    # without error -- they don't test any Mandrill-supplied content.
    # (Future improvements could mock the Mandrill responses.)

    # These urls set up the DjrillAdminSite as suggested in the readme
    urls = 'djrill.tests.admin_urls'

    @classmethod
    def setUpClass(cls):
        # Other test cases may muck with the Django admin site globals,
        # so return it to the default state before loading test_admin_urls
        reset_admin_site()

    def setUp(self):
        super(DjrillAdminTests, self).setUp()
        # Must be authenticated staff to access admin site...
        admin = User.objects.create_user('admin', 'admin@example.com', 'secret')
        admin.is_staff = True
        admin.save()
        self.client.login(username='admin', password='secret')

    def test_admin_senders(self):
        response = self.client.get('/admin/djrill/senders/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Senders")

    def test_admin_status(self):
        response = self.client.get('/admin/djrill/status/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Status")

    def test_admin_tags(self):
        response = self.client.get('/admin/djrill/tags/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Tags")

    def test_admin_urls(self):
        response = self.client.get('/admin/djrill/urls/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "URLs")

    def test_admin_index(self):
        """Make sure Djrill section is included in the admin index page"""
        response = self.client.get('/admin/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Djrill")


class DjrillNoAdminTests(TestCase):
    def test_admin_autodiscover_without_djrill(self):
        """Make sure autodiscover doesn't die without DjrillAdminSite"""
        reset_admin_site()
        admin.autodiscover() # test: this shouldn't error

########NEW FILE########
__FILENAME__ = test_legacy
# Tests deprecated Djrill features

from django.test import TestCase

from djrill.mail import DjrillMessage
from djrill import MandrillAPIError, NotSupportedByMandrillError


class DjrillMessageTests(TestCase):
    """Test the DjrillMessage class (deprecated as of Djrill v0.2.0)

    Maintained for compatibility with older code.

    """

    def setUp(self):
        self.subject = "Djrill baby djrill."
        self.from_name = "Tarzan"
        self.from_email = "test@example"
        self.to = ["King Kong <kingkong@example.com>",
                   "Cheetah <cheetah@example.com", "bubbles@example.com"]
        self.text_content = "Wonderful fallback text content."
        self.html_content = "<h1>That's a nice HTML email right there.</h1>"
        self.headers = {"Reply-To": "tarzan@example.com"}
        self.tags = ["track", "this"]

    def test_djrill_message_success(self):
        msg = DjrillMessage(self.subject, self.text_content, self.from_email,
            self.to, tags=self.tags, headers=self.headers,
            from_name=self.from_name)

        self.assertIsInstance(msg, DjrillMessage)
        self.assertEqual(msg.body, self.text_content)
        self.assertEqual(msg.recipients(), self.to)
        self.assertEqual(msg.tags, self.tags)
        self.assertEqual(msg.extra_headers, self.headers)
        self.assertEqual(msg.from_name, self.from_name)

    def test_djrill_message_html_success(self):
        msg = DjrillMessage(self.subject, self.text_content, self.from_email,
            self.to, tags=self.tags)
        msg.attach_alternative(self.html_content, "text/html")

        self.assertEqual(msg.alternatives[0][0], self.html_content)

    def test_djrill_message_tag_failure(self):
        with self.assertRaises(ValueError):
            DjrillMessage(self.subject, self.text_content, self.from_email,
                self.to, tags=["_fail"])

    def test_djrill_message_tag_skip(self):
        """
        Test that tags over 50 chars are not included in the tags list.
        """
        tags = ["works", "awesomesauce",
                "iwilltestmycodeiwilltestmycodeiwilltestmycodeiwilltestmycode"]
        msg = DjrillMessage(self.subject, self.text_content, self.from_email,
            self.to, tags=tags)

        self.assertIsInstance(msg, DjrillMessage)
        self.assertIn(tags[0], msg.tags)
        self.assertIn(tags[1], msg.tags)
        self.assertNotIn(tags[2], msg.tags)

    def test_djrill_message_no_options(self):
        """DjrillMessage with only basic EmailMessage options should work"""
        msg = DjrillMessage(self.subject, self.text_content,
            self.from_email, self.to) # no Mandrill-specific options

        self.assertIsInstance(msg, DjrillMessage)
        self.assertEqual(msg.body, self.text_content)
        self.assertEqual(msg.recipients(), self.to)
        self.assertFalse(hasattr(msg, 'tags'))
        self.assertFalse(hasattr(msg, 'from_name'))
        self.assertFalse(hasattr(msg, 'preserve_recipients'))


class DjrillLegacyExceptionTests(TestCase):
    def test_DjrillBackendHTTPError(self):
        """MandrillApiError was DjrillBackendHTTPError in 0.2.0"""
        # ... and had to be imported from deep in the package:
        from djrill.mail.backends.djrill import DjrillBackendHTTPError
        ex = MandrillAPIError("testing")
        self.assertIsInstance(ex, DjrillBackendHTTPError)

    def test_NotSupportedByMandrillError(self):
        """Unsupported features used to just raise ValueError in 0.2.0"""
        ex = NotSupportedByMandrillError("testing")
        self.assertIsInstance(ex, ValueError)

########NEW FILE########
__FILENAME__ = test_mandrill_send
# -*- coding: utf-8 -*-

from __future__ import unicode_literals

from base64 import b64decode
from datetime import date, datetime, timedelta, tzinfo
from email.mime.base import MIMEBase
from email.mime.image import MIMEImage
import os

from django.core import mail
from django.core.exceptions import ImproperlyConfigured
from django.core.mail import make_msgid
from django.test import TestCase

from djrill import MandrillAPIError, NotSupportedByMandrillError
from .mock_backend import DjrillBackendMockAPITestCase
from .utils import override_settings


def decode_att(att):
    """Returns the original data from base64-encoded attachment content"""
    return b64decode(att.encode('ascii'))


class DjrillBackendTests(DjrillBackendMockAPITestCase):
    """Test Djrill backend support for Django mail wrappers"""

    sample_image_filename = "sample_image.png"

    def sample_image_pathname(self):
        """Returns path to an actual image file in the tests directory"""
        test_dir = os.path.dirname(os.path.abspath(__file__))
        path = os.path.join(test_dir, self.sample_image_filename)
        return path

    def sample_image_content(self):
        """Returns contents of an actual image file from the tests directory"""
        filename = self.sample_image_pathname()
        with open(filename, "rb") as f:
            return f.read()

    def test_send_mail(self):
        mail.send_mail('Subject here', 'Here is the message.',
            'from@example.com', ['to@example.com'], fail_silently=False)
        self.assert_mandrill_called("/messages/send.json")
        data = self.get_api_call_data()
        self.assertEqual(data['message']['subject'], "Subject here")
        self.assertEqual(data['message']['text'], "Here is the message.")
        self.assertFalse('from_name' in data['message'])
        self.assertEqual(data['message']['from_email'], "from@example.com")
        self.assertEqual(len(data['message']['to']), 1)
        self.assertEqual(data['message']['to'][0]['email'], "to@example.com")

    def test_name_addr(self):
        """Make sure RFC2822 name-addr format (with display-name) is allowed

        (Test both sender and recipient addresses)
        """
        msg = mail.EmailMessage('Subject', 'Message',
            'From Name <from@example.com>',
            ['Recipient #1 <to1@example.com>', 'to2@example.com'],
            cc=['Carbon Copy <cc1@example.com>', 'cc2@example.com'],
            bcc=['Blind Copy <bcc1@example.com>', 'bcc2@example.com'])
        msg.send()
        data = self.get_api_call_data()
        self.assertEqual(data['message']['from_name'], "From Name")
        self.assertEqual(data['message']['from_email'], "from@example.com")
        self.assertEqual(len(data['message']['to']), 6)
        self.assertEqual(data['message']['to'][0]['name'], "Recipient #1")
        self.assertEqual(data['message']['to'][0]['email'], "to1@example.com")
        self.assertEqual(data['message']['to'][1]['name'], "")
        self.assertEqual(data['message']['to'][1]['email'], "to2@example.com")
        self.assertEqual(data['message']['to'][2]['name'], "Carbon Copy")
        self.assertEqual(data['message']['to'][2]['email'], "cc1@example.com")
        self.assertEqual(data['message']['to'][3]['name'], "")
        self.assertEqual(data['message']['to'][3]['email'], "cc2@example.com")
        self.assertEqual(data['message']['to'][4]['name'], "Blind Copy")
        self.assertEqual(data['message']['to'][4]['email'], "bcc1@example.com")
        self.assertEqual(data['message']['to'][5]['name'], "")
        self.assertEqual(data['message']['to'][5]['email'], "bcc2@example.com")

    def test_email_message(self):
        email = mail.EmailMessage('Subject', 'Body goes here',
            'from@example.com',
            ['to1@example.com', 'Also To <to2@example.com>'],
            bcc=['bcc1@example.com', 'Also BCC <bcc2@example.com>'],
            cc=['cc1@example.com', 'Also CC <cc2@example.com>'],
            headers={'Reply-To': 'another@example.com',
                     'X-MyHeader': 'my value',
                     'Message-ID': 'mycustommsgid@example.com'})
        email.send()
        self.assert_mandrill_called("/messages/send.json")
        data = self.get_api_call_data()
        self.assertEqual(data['message']['subject'], "Subject")
        self.assertEqual(data['message']['text'], "Body goes here")
        self.assertEqual(data['message']['from_email'], "from@example.com")
        self.assertEqual(data['message']['headers'],
                         {'Reply-To': 'another@example.com',
                          'X-MyHeader': 'my value',
                          'Message-ID': 'mycustommsgid@example.com'})
        # Verify recipients correctly identified as "to", "cc", or "bcc"
        self.assertEqual(len(data['message']['to']), 6)
        self.assertEqual(data['message']['to'][0]['email'], "to1@example.com")
        self.assertEqual(data['message']['to'][0]['type'], "to")
        self.assertEqual(data['message']['to'][1]['email'], "to2@example.com")
        self.assertEqual(data['message']['to'][1]['type'], "to")
        self.assertEqual(data['message']['to'][2]['email'], "cc1@example.com")
        self.assertEqual(data['message']['to'][2]['type'], "cc")
        self.assertEqual(data['message']['to'][3]['email'], "cc2@example.com")
        self.assertEqual(data['message']['to'][3]['type'], "cc")
        self.assertEqual(data['message']['to'][4]['email'], "bcc1@example.com")
        self.assertEqual(data['message']['to'][4]['type'], "bcc")
        self.assertEqual(data['message']['to'][5]['email'], "bcc2@example.com")
        self.assertEqual(data['message']['to'][5]['type'], "bcc")
        # Don't use Mandrill's bcc_address "logging" feature for bcc's:
        self.assertNotIn('bcc_address', data['message'])

    def test_html_message(self):
        text_content = 'This is an important message.'
        html_content = '<p>This is an <strong>important</strong> message.</p>'
        email = mail.EmailMultiAlternatives('Subject', text_content,
            'from@example.com', ['to@example.com'])
        email.attach_alternative(html_content, "text/html")
        email.send()
        self.assert_mandrill_called("/messages/send.json")
        data = self.get_api_call_data()
        self.assertEqual(data['message']['text'], text_content)
        self.assertEqual(data['message']['html'], html_content)
        # Don't accidentally send the html part as an attachment:
        self.assertFalse('attachments' in data['message'])

    def test_html_only_message(self):
        html_content = '<p>This is an <strong>important</strong> message.</p>'
        email = mail.EmailMessage('Subject', html_content,
            'from@example.com', ['to@example.com'])
        email.content_subtype = "html"  # Main content is now text/html
        email.send()
        self.assert_mandrill_called("/messages/send.json")
        data = self.get_api_call_data()
        self.assertNotIn('text', data['message'])
        self.assertEqual(data['message']['html'], html_content)

    def test_attachments(self):
        email = mail.EmailMessage('Subject', 'Body goes here', 'from@example.com', ['to1@example.com'])

        text_content = "* Item one\n* Item two\n* Item three"
        email.attach(filename="test.txt", content=text_content, mimetype="text/plain")

        # Should guess mimetype if not provided...
        png_content = b"PNG\xb4 pretend this is the contents of a png file"
        email.attach(filename="test.png", content=png_content)

        # Should work with a MIMEBase object (also tests no filename)...
        pdf_content = b"PDF\xb4 pretend this is valid pdf data"
        mimeattachment = MIMEBase('application', 'pdf')
        mimeattachment.set_payload(pdf_content)
        email.attach(mimeattachment)

        # Attachment type that wasn't supported in early Mandrill releases:
        ppt_content = b"PPT\xb4 pretend this is a valid ppt file"
        email.attach(filename="presentation.ppt", content=ppt_content,
                     mimetype="application/vnd.ms-powerpoint")

        email.send()
        data = self.get_api_call_data()
        attachments = data['message']['attachments']
        self.assertEqual(len(attachments), 4)
        self.assertEqual(attachments[0]["type"], "text/plain")
        self.assertEqual(attachments[0]["name"], "test.txt")
        self.assertEqual(decode_att(attachments[0]["content"]).decode('ascii'), text_content)
        self.assertEqual(attachments[1]["type"], "image/png")  # inferred from filename
        self.assertEqual(attachments[1]["name"], "test.png")
        self.assertEqual(decode_att(attachments[1]["content"]), png_content)
        self.assertEqual(attachments[2]["type"], "application/pdf")
        self.assertEqual(attachments[2]["name"], "")  # none
        self.assertEqual(decode_att(attachments[2]["content"]), pdf_content)
        self.assertEqual(attachments[3]["type"], "application/vnd.ms-powerpoint")
        self.assertEqual(attachments[3]["name"], "presentation.ppt")
        self.assertEqual(decode_att(attachments[3]["content"]), ppt_content)
        # Make sure the image attachment is not treated as embedded:
        self.assertFalse('images' in data['message'])

    def test_unicode_attachment_correctly_decoded(self):
        msg = mail.EmailMessage(
            subject='Subject',
            body='Body goes here',
            from_email='from@example.com',
            to=['to1@example.com'],
        )
        # Slight modification from the Django unicode docs:
        # http://django.readthedocs.org/en/latest/ref/unicode.html#email
        msg.attach("Une pièce jointe.html", '<p>\u2019</p>', mimetype='text/html')

        msg.send()
        data = self.get_api_call_data()

        attachments = data['message']['attachments']
        self.assertEqual(len(attachments), 1)

    def test_embedded_images(self):
        image_data = self.sample_image_content()  # Read from a png file
        image_cid = make_msgid("img")  # Content ID per RFC 2045 section 7 (with <...>)
        image_cid_no_brackets = image_cid[1:-1]  # Without <...>, for use as the <img> tag src

        text_content = 'This has an inline image.'
        html_content = '<p>This has an <img src="cid:%s" alt="inline" /> image.</p>' % image_cid_no_brackets
        email = mail.EmailMultiAlternatives('Subject', text_content, 'from@example.com', ['to@example.com'])
        email.attach_alternative(html_content, "text/html")

        image = MIMEImage(image_data)
        image.add_header('Content-ID', image_cid)
        email.attach(image)

        email.send()
        data = self.get_api_call_data()
        self.assertEqual(data['message']['text'], text_content)
        self.assertEqual(data['message']['html'], html_content)
        self.assertEqual(len(data['message']['images']), 1)
        self.assertEqual(data['message']['images'][0]["type"], "image/png")
        self.assertEqual(data['message']['images'][0]["name"], image_cid)
        self.assertEqual(decode_att(data['message']['images'][0]["content"]), image_data)
        # Make sure neither the html nor the inline image is treated as an attachment:
        self.assertFalse('attachments' in data['message'])

    def test_attached_images(self):
        image_data = self.sample_image_content()

        email = mail.EmailMultiAlternatives('Subject', 'Message', 'from@example.com', ['to@example.com'])
        email.attach_file(self.sample_image_pathname())  # option 1: attach as a file

        image = MIMEImage(image_data)  # option 2: construct the MIMEImage and attach it directly
        email.attach(image)

        email.send()
        data = self.get_api_call_data()
        attachments = data['message']['attachments']
        self.assertEqual(len(attachments), 2)
        self.assertEqual(attachments[0]["type"], "image/png")
        self.assertEqual(attachments[0]["name"], self.sample_image_filename)
        self.assertEqual(decode_att(attachments[0]["content"]), image_data)
        self.assertEqual(attachments[1]["type"], "image/png")
        self.assertEqual(attachments[1]["name"], "")  # unknown -- not attached as file
        self.assertEqual(decode_att(attachments[1]["content"]), image_data)
        # Make sure the image attachments are not treated as embedded:
        self.assertFalse('images' in data['message'])

    def test_alternative_errors(self):
        # Multiple alternatives not allowed
        email = mail.EmailMultiAlternatives('Subject', 'Body',
            'from@example.com', ['to@example.com'])
        email.attach_alternative("<p>First html is OK</p>", "text/html")
        email.attach_alternative("<p>But not second html</p>", "text/html")
        with self.assertRaises(NotSupportedByMandrillError):
            email.send()

        # Only html alternatives allowed
        email = mail.EmailMultiAlternatives('Subject', 'Body',
            'from@example.com', ['to@example.com'])
        email.attach_alternative("{'not': 'allowed'}", "application/json")
        with self.assertRaises(NotSupportedByMandrillError):
            email.send()

        # Make sure fail_silently is respected
        email = mail.EmailMultiAlternatives('Subject', 'Body',
            'from@example.com', ['to@example.com'])
        email.attach_alternative("{'not': 'allowed'}", "application/json")
        sent = email.send(fail_silently=True)
        self.assertFalse(self.mock_post.called,
            msg="Mandrill API should not be called when send fails silently")
        self.assertEqual(sent, 0)

    def test_mandrill_api_failure(self):
        self.mock_post.return_value = self.MockResponse(status_code=400)
        with self.assertRaises(MandrillAPIError):
            sent = mail.send_mail('Subject', 'Body', 'from@example.com',
                ['to@example.com'])
            self.assertEqual(sent, 0)

        # Make sure fail_silently is respected
        self.mock_post.return_value = self.MockResponse(status_code=400)
        sent = mail.send_mail('Subject', 'Body', 'from@example.com',
            ['to@example.com'], fail_silently=True)
        self.assertEqual(sent, 0)


class DjrillMandrillFeatureTests(DjrillBackendMockAPITestCase):
    """Test Djrill backend support for Mandrill-specific features"""

    def setUp(self):
        super(DjrillMandrillFeatureTests, self).setUp()
        self.message = mail.EmailMessage('Subject', 'Text Body',
            'from@example.com', ['to@example.com'])

    def test_tracking(self):
        # First make sure we're not setting the API param if the track_click
        # attr isn't there. (The Mandrill account option of True for html,
        # False for plaintext can't be communicated through the API, other than
        # by omitting the track_clicks API param to use your account default.)
        self.message.send()
        data = self.get_api_call_data()
        self.assertFalse('track_clicks' in data['message'])
        # Now re-send with the params set
        self.message.track_opens = True
        self.message.track_clicks = True
        self.message.url_strip_qs = True
        self.message.send()
        data = self.get_api_call_data()
        self.assertEqual(data['message']['track_opens'], True)
        self.assertEqual(data['message']['track_clicks'], True)
        self.assertEqual(data['message']['url_strip_qs'], True)

    def test_message_options(self):
        self.message.important = True
        self.message.auto_text = True
        self.message.auto_html = True
        self.message.inline_css = True
        self.message.preserve_recipients = True
        self.message.view_content_link = False
        self.message.tracking_domain = "click.example.com"
        self.message.signing_domain = "example.com"
        self.message.return_path_domain = "support.example.com"
        self.message.subaccount = "marketing-dept"
        self.message.async = True
        self.message.ip_pool = "Bulk Pool"
        self.message.send()
        data = self.get_api_call_data()
        self.assertEqual(data['message']['important'], True)
        self.assertEqual(data['message']['auto_text'], True)
        self.assertEqual(data['message']['auto_html'], True)
        self.assertEqual(data['message']['inline_css'], True)
        self.assertEqual(data['message']['preserve_recipients'], True)
        self.assertEqual(data['message']['view_content_link'], False)
        self.assertEqual(data['message']['tracking_domain'], "click.example.com")
        self.assertEqual(data['message']['signing_domain'], "example.com")
        self.assertEqual(data['message']['return_path_domain'], "support.example.com")
        self.assertEqual(data['message']['subaccount'], "marketing-dept")
        self.assertEqual(data['async'], True)
        self.assertEqual(data['ip_pool'], "Bulk Pool")

    def test_merge(self):
        # Djrill expands simple python dicts into the more-verbose name/content
        # structures the Mandrill API uses
        self.message.global_merge_vars = { 'GREETING': "Hello",
                                           'ACCOUNT_TYPE': "Basic" }
        self.message.merge_vars = {
            "customer@example.com": { 'GREETING': "Dear Customer",
                                      'ACCOUNT_TYPE': "Premium" },
            "guest@example.com": { 'GREETING': "Dear Guest" },
            }
        self.message.send()
        data = self.get_api_call_data()
        self.assertEqual(data['message']['global_merge_vars'],
            [ {'name': 'ACCOUNT_TYPE', 'content': "Basic"},
              {'name': "GREETING", 'content': "Hello"} ])
        self.assertEqual(data['message']['merge_vars'],
            [ { 'rcpt': "customer@example.com",
                'vars': [{ 'name': 'ACCOUNT_TYPE', 'content': "Premium" },
                         { 'name': "GREETING", 'content': "Dear Customer"}] },
              { 'rcpt': "guest@example.com",
                'vars': [{ 'name': "GREETING", 'content': "Dear Guest"}] }
            ])

    def test_tags(self):
        self.message.tags = ["receipt", "repeat-user"]
        self.message.send()
        data = self.get_api_call_data()
        self.assertEqual(data['message']['tags'], ["receipt", "repeat-user"])

    def test_google_analytics(self):
        self.message.google_analytics_domains = ["example.com"]
        self.message.google_analytics_campaign = "Email Receipts"
        self.message.send()
        data = self.get_api_call_data()
        self.assertEqual(data['message']['google_analytics_domains'],
            ["example.com"])
        self.assertEqual(data['message']['google_analytics_campaign'],
            "Email Receipts")

    def test_metadata(self):
        self.message.metadata = { 'batch_num': "12345", 'type': "Receipts" }
        self.message.recipient_metadata = {
            # Djrill expands simple python dicts into the more-verbose
            # rcpt/values structures the Mandrill API uses
            "customer@example.com": { 'cust_id': "67890", 'order_id': "54321" },
            "guest@example.com": { 'cust_id': "94107", 'order_id': "43215" }
        }
        self.message.send()
        data = self.get_api_call_data()
        self.assertEqual(data['message']['metadata'], { 'batch_num': "12345",
                                                        'type': "Receipts" })
        self.assertEqual(data['message']['recipient_metadata'],
            [ { 'rcpt': "customer@example.com",
                'values': { 'cust_id': "67890", 'order_id': "54321" } },
              { 'rcpt': "guest@example.com",
                'values': { 'cust_id': "94107", 'order_id': "43215" } }
            ])

    def test_send_at(self):
        # String passed unchanged
        self.message.send_at = "2013-11-12 01:02:03"
        self.message.send()
        data = self.get_api_call_data()
        self.assertEqual(data['send_at'], "2013-11-12 01:02:03")

        # Timezone-naive datetime assumed to be UTC
        self.message.send_at = datetime(2022, 10, 11, 12, 13, 14, 567)
        self.message.send()
        data = self.get_api_call_data()
        self.assertEqual(data['send_at'], "2022-10-11 12:13:14")

        # Timezone-aware datetime converted to UTC:
        class GMTminus8(tzinfo):
            def utcoffset(self, dt): return timedelta(hours=-8)
            def dst(self, dt): return timedelta(0)

        self.message.send_at = datetime(2016, 3, 4, 5, 6, 7, tzinfo=GMTminus8())
        self.message.send()
        data = self.get_api_call_data()
        self.assertEqual(data['send_at'], "2016-03-04 13:06:07")

        # Date-only treated as midnight UTC
        self.message.send_at = date(2022, 10, 22)
        self.message.send()
        data = self.get_api_call_data()
        self.assertEqual(data['send_at'], "2022-10-22 00:00:00")

    def test_default_omits_options(self):
        """Make sure by default we don't send any Mandrill-specific options.

        Options not specified by the caller should be omitted entirely from
        the Mandrill API call (*not* sent as False or empty). This ensures
        that your Mandrill account settings apply by default.
        """
        self.message.send()
        self.assert_mandrill_called("/messages/send.json")
        data = self.get_api_call_data()
        self.assertFalse('from_name' in data['message'])
        self.assertFalse('bcc_address' in data['message'])
        self.assertFalse('important' in data['message'])
        self.assertFalse('track_opens' in data['message'])
        self.assertFalse('track_clicks' in data['message'])
        self.assertFalse('auto_text' in data['message'])
        self.assertFalse('auto_html' in data['message'])
        self.assertFalse('inline_css' in data['message'])
        self.assertFalse('url_strip_qs' in data['message'])
        self.assertFalse('tags' in data['message'])
        self.assertFalse('preserve_recipients' in data['message'])
        self.assertFalse('view_content_link' in data['message'])
        self.assertFalse('tracking_domain' in data['message'])
        self.assertFalse('signing_domain' in data['message'])
        self.assertFalse('return_path_domain' in data['message'])
        self.assertFalse('subaccount' in data['message'])
        self.assertFalse('google_analytics_domains' in data['message'])
        self.assertFalse('google_analytics_campaign' in data['message'])
        self.assertFalse('metadata' in data['message'])
        self.assertFalse('global_merge_vars' in data['message'])
        self.assertFalse('merge_vars' in data['message'])
        self.assertFalse('recipient_metadata' in data['message'])
        self.assertFalse('images' in data['message'])
        # Options at top level of api params (not in message dict):
        self.assertFalse('send_at' in data)
        self.assertFalse('async' in data)
        self.assertFalse('ip_pool' in data)

    def test_send_attaches_mandrill_response(self):
        """ The mandrill_response should be attached to the message when it is sent """
        response = [{'mandrill_response': 'would_be_here'}]
        self.mock_post.return_value = self.MockResponse(json=response)
        msg = mail.EmailMessage('Subject', 'Message', 'from@example.com', ['to1@example.com'],)
        sent = msg.send()
        self.assertEqual(sent, 1)
        self.assertEqual(msg.mandrill_response, response)

    def test_send_failed_mandrill_response(self):
        """ If the send fails, mandrill_response should be set to None """
        self.mock_post.return_value = self.MockResponse(status_code=500)
        msg = mail.EmailMessage('Subject', 'Message', 'from@example.com', ['to1@example.com'],)
        sent = msg.send(fail_silently=True)
        self.assertEqual(sent, 0)
        self.assertIsNone(msg.mandrill_response)


@override_settings(EMAIL_BACKEND="djrill.mail.backends.djrill.DjrillBackend")
class DjrillImproperlyConfiguredTests(TestCase):
    """Test Djrill backend without Djrill-specific settings in place"""

    def test_missing_api_key(self):
        with self.assertRaises(ImproperlyConfigured):
            mail.send_mail('Subject', 'Message', 'from@example.com',
                ['to@example.com'])

########NEW FILE########
__FILENAME__ = test_mandrill_send_template
from django.core import mail

from djrill.tests.mock_backend import DjrillBackendMockAPITestCase


class DjrillMandrillSendTemplateTests(DjrillBackendMockAPITestCase):
    """Test Djrill backend support for Mandrill send-template features"""

    def test_send_template(self):
        msg = mail.EmailMessage('Subject', 'Text Body',
            'from@example.com', ['to@example.com'])
        msg.template_name = "PERSONALIZED_SPECIALS"
        msg.template_content = {
            'HEADLINE': "<h1>Specials Just For *|FNAME|*</h1>",
            'OFFER_BLOCK': "<p><em>Half off</em> all fruit</p>"
        }
        msg.send()
        self.assert_mandrill_called("/messages/send-template.json")
        data = self.get_api_call_data()
        self.assertEqual(data['template_name'], "PERSONALIZED_SPECIALS")
        # Djrill expands simple python dicts into the more-verbose name/content
        # structures the Mandrill API uses
        self.assertEqual(data['template_content'],
            [ {'name': "HEADLINE",
               'content': "<h1>Specials Just For *|FNAME|*</h1>"},
              {'name': "OFFER_BLOCK",
               'content': "<p><em>Half off</em> all fruit</p>"} ]
        )

    def test_send_template_without_from_field(self):
        msg = mail.EmailMessage('Subject', 'Text Body',
            'from@example.com', ['to@example.com'])
        msg.template_name = "PERSONALIZED_SPECIALS"
        msg.use_template_from = True
        msg.send()
        self.assert_mandrill_called("/messages/send-template.json")
        data = self.get_api_call_data()
        self.assertEqual(data['template_name'], "PERSONALIZED_SPECIALS")
        self.assertFalse('from_email' in data['message'])
        self.assertFalse('from_name' in data['message'])

    def test_send_template_without_subject_field(self):
        msg = mail.EmailMessage('Subject', 'Text Body',
            'from@example.com', ['to@example.com'])
        msg.template_name = "PERSONALIZED_SPECIALS"
        msg.use_template_subject = True
        msg.send()
        self.assert_mandrill_called("/messages/send-template.json")
        data = self.get_api_call_data()
        self.assertEqual(data['template_name'], "PERSONALIZED_SPECIALS")
        self.assertFalse('subject' in data['message'])

    def test_no_template_content(self):
        # Just a template, without any template_content to be merged
        msg = mail.EmailMessage('Subject', 'Text Body',
            'from@example.com', ['to@example.com'])
        msg.template_name = "WELCOME_MESSAGE"
        msg.send()
        self.assert_mandrill_called("/messages/send-template.json")
        data = self.get_api_call_data()
        self.assertEqual(data['template_name'], "WELCOME_MESSAGE")
        self.assertEqual(data['template_content'], [])  # Mandrill requires this field

    def test_non_template_send(self):
        # Make sure the non-template case still uses /messages/send.json
        msg = mail.EmailMessage('Subject', 'Text Body',
            'from@example.com', ['to@example.com'])
        msg.send()
        self.assert_mandrill_called("/messages/send.json")
        data = self.get_api_call_data()
        self.assertFalse('template_name' in data)
        self.assertFalse('template_content' in data)
        self.assertFalse('async' in data)

########NEW FILE########
__FILENAME__ = test_mandrill_subaccounts
from django.core import mail

from .mock_backend import DjrillBackendMockAPITestCase
from .utils import override_settings


class DjrillMandrillSubaccountTests(DjrillBackendMockAPITestCase):
    """Test Djrill backend support for Mandrill subaccounts"""

    def test_send_basic(self):
        mail.send_mail('Subject here', 'Here is the message.',
            'from@example.com', ['to@example.com'], fail_silently=False)
        self.assert_mandrill_called("/messages/send.json")
        data = self.get_api_call_data()
        self.assertEqual(data['message']['subject'], "Subject here")
        self.assertEqual(data['message']['text'], "Here is the message.")
        self.assertFalse('from_name' in data['message'])
        self.assertEqual(data['message']['from_email'], "from@example.com")
        self.assertEqual(len(data['message']['to']), 1)
        self.assertEqual(data['message']['to'][0]['email'], "to@example.com")
        self.assertFalse('subaccount' in data['message'])

    @override_settings(MANDRILL_SUBACCOUNT="test_subaccount")
    def test_send_from_subaccount(self):
        mail.send_mail('Subject here', 'Here is the message.',
            'from@example.com', ['to@example.com'], fail_silently=False)
        self.assert_mandrill_called("/messages/send.json")
        data = self.get_api_call_data()
        self.assertEqual(data['message']['subject'], "Subject here")
        self.assertEqual(data['message']['text'], "Here is the message.")
        self.assertFalse('from_name' in data['message'])
        self.assertEqual(data['message']['from_email'], "from@example.com")
        self.assertEqual(len(data['message']['to']), 1)
        self.assertEqual(data['message']['to'][0]['email'], "to@example.com")
        self.assertEqual(data['message']['subaccount'], "test_subaccount")

    @override_settings(MANDRILL_SUBACCOUNT="global_setting_subaccount")
    def test_subaccount_message_overrides_setting(self):
        message = mail.EmailMessage(
            'Subject here', 'Here is the message',
            'from@example.com', ['to@example.com'])
        message.subaccount = "individual_message_subaccount"  # should override global setting
        message.send()
        self.assert_mandrill_called("/messages/send.json")
        data = self.get_api_call_data()
        self.assertEqual(data['message']['subaccount'], "individual_message_subaccount")

########NEW FILE########
__FILENAME__ = test_mandrill_webhook
from base64 import b64encode
import hashlib
import hmac
import json

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.test import TestCase

from ..compat import b
from ..signals import webhook_event
from .utils import override_settings


class DjrillWebhookSecretMixinTests(TestCase):
    """
    Test mixin used in optional Mandrill webhook support
    """

    def test_missing_secret(self):
        with self.assertRaises(ImproperlyConfigured):
            self.client.get('/webhook/')

    @override_settings(DJRILL_WEBHOOK_SECRET='abc123')
    def test_incorrect_secret(self):
        response = self.client.head('/webhook/?secret=wrong')
        self.assertEqual(response.status_code, 403)

    @override_settings(DJRILL_WEBHOOK_SECRET='abc123')
    def test_default_secret_name(self):
        response = self.client.head('/webhook/?secret=abc123')
        self.assertEqual(response.status_code, 200)

    @override_settings(DJRILL_WEBHOOK_SECRET='abc123', DJRILL_WEBHOOK_SECRET_NAME='verysecret')
    def test_custom_secret_name(self):
        response = self.client.head('/webhook/?verysecret=abc123')
        self.assertEqual(response.status_code, 200)


@override_settings(DJRILL_WEBHOOK_SECRET='abc123',
                   DJRILL_WEBHOOK_SIGNATURE_KEY="signature")
class DjrillWebhookSignatureMixinTests(TestCase):
    """
    Test mixin used in optional Mandrill webhook signature support
    """

    def test_incorrect_settings(self):
        with self.assertRaises(ImproperlyConfigured):
            self.client.post('/webhook/?secret=abc123')

    @override_settings(DJRILL_WEBHOOK_URL="/webhook/?secret=abc123",
                       DJRILL_WEBHOOK_SIGNATURE_KEY = "anothersignature")
    def test_unauthorized(self):
        response = self.client.post(settings.DJRILL_WEBHOOK_URL)
        self.assertEqual(response.status_code, 403)

    @override_settings(DJRILL_WEBHOOK_URL="/webhook/?secret=abc123")
    def test_signature(self):
        signature = hmac.new(key=b(settings.DJRILL_WEBHOOK_SIGNATURE_KEY),
                             msg=b(settings.DJRILL_WEBHOOK_URL+"mandrill_events[]"),
                             digestmod=hashlib.sha1)
        hash_string = b64encode(signature.digest())
        response = self.client.post('/webhook/?secret=abc123', data={"mandrill_events":"[]"},
                                    **{"HTTP_X_MANDRILL_SIGNATURE": hash_string})
        self.assertEqual(response.status_code, 200)


@override_settings(DJRILL_WEBHOOK_SECRET='abc123')
class DjrillWebhookViewTests(TestCase):
    """
    Test optional Mandrill webhook view
    """

    def test_head_request(self):
        response = self.client.head('/webhook/?secret=abc123')
        self.assertEqual(response.status_code, 200)

    def test_post_request_invalid_json(self):
        response = self.client.post('/webhook/?secret=abc123')
        self.assertEqual(response.status_code, 400)

    def test_post_request_valid_json(self):
        response = self.client.post('/webhook/?secret=abc123', {
            'mandrill_events': json.dumps([{"event": "send", "msg": {}}])
        })
        self.assertEqual(response.status_code, 200)

    def test_webhook_send_signal(self):
        self.signal_received_count = 0
        test_event = {"event": "send", "msg": {}}

        def my_callback(sender, event_type, data, **kwargs):
            self.signal_received_count += 1
            self.assertEqual(event_type, 'send')
            self.assertEqual(data, test_event)

        webhook_event.connect(my_callback)

        response = self.client.post('/webhook/?secret=abc123', {
            'mandrill_events': json.dumps([test_event])
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.signal_received_count, 1)

########NEW FILE########
__FILENAME__ = utils
__all__ = (
    'override_settings',
)

try:
    from django.test.utils import override_settings

except ImportError:
    # Back-port override_settings from Django 1.4
    # https://github.com/django/django/blob/stable/1.4.x/django/test/utils.py
    from django.conf import settings, UserSettingsHolder
    from django.utils.functional import wraps

    class override_settings(object):
        """
        Acts as either a decorator, or a context manager. If it's a decorator it
        takes a function and returns a wrapped function. If it's a contextmanager
        it's used with the ``with`` statement. In either event entering/exiting
        are called before and after, respectively, the function/block is executed.
        """
        def __init__(self, **kwargs):
            self.options = kwargs
            self.wrapped = settings._wrapped

        def __enter__(self):
            self.enable()

        def __exit__(self, exc_type, exc_value, traceback):
            self.disable()

        def __call__(self, test_func):
            from django.test import TransactionTestCase
            if isinstance(test_func, type) and issubclass(test_func, TransactionTestCase):
                original_pre_setup = test_func._pre_setup
                original_post_teardown = test_func._post_teardown
                def _pre_setup(innerself):
                    self.enable()
                    original_pre_setup(innerself)
                def _post_teardown(innerself):
                    original_post_teardown(innerself)
                    self.disable()
                test_func._pre_setup = _pre_setup
                test_func._post_teardown = _post_teardown
                return test_func
            else:
                @wraps(test_func)
                def inner(*args, **kwargs):
                    with self:
                        return test_func(*args, **kwargs)
            return inner

        def enable(self):
            override = UserSettingsHolder(settings._wrapped)
            for key, new_value in self.options.items():
                setattr(override, key, new_value)
            settings._wrapped = override
            # No setting_changed signal in Django 1.3
            # for key, new_value in self.options.items():
            #     setting_changed.send(sender=settings._wrapped.__class__,
            #                          setting=key, value=new_value)

        def disable(self):
            settings._wrapped = self.wrapped
            # No setting_changed signal in Django 1.3
            # for key in self.options:
            #     new_value = getattr(settings, key, None)
            #     setting_changed.send(sender=settings._wrapped.__class__,
            #                          setting=key, value=new_value)

########NEW FILE########
__FILENAME__ = urls
try:
    from django.conf.urls import patterns, url
except ImportError:
    from django.conf.urls.defaults import patterns, url

from .views import DjrillWebhookView


urlpatterns = patterns(
    '',

    url(r'^webhook/$', DjrillWebhookView.as_view(), name='djrill_webhook'),
)

########NEW FILE########
__FILENAME__ = views
from base64 import b64encode
import hashlib
import hmac
import json
from django import forms
from django.conf import settings
from django.contrib import messages
from django.core.exceptions import ImproperlyConfigured
from django.views.generic import TemplateView, View
from django.http import HttpResponse
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt

import requests

from djrill import MANDRILL_API_URL, signals
from .compat import b


class DjrillAdminMedia(object):
    def _media(self):
        js = ["js/core.js", "js/jquery.min.js", "js/jquery.init.js"]

        return forms.Media(js=["%s%s" % (settings.STATIC_URL, url) for url in js])
    media = property(_media)


class DjrillApiMixin(object):
    """
    Simple Mixin to grab the api info from the settings file.
    """
    def __init__(self):
        self.api_key = getattr(settings, "MANDRILL_API_KEY", None)
        self.api_url = MANDRILL_API_URL

        if not self.api_key:
            raise ImproperlyConfigured(
                "You have not set your mandrill api key in the settings file.")

    def get_context_data(self, **kwargs):
        kwargs = super(DjrillApiMixin, self).get_context_data(**kwargs)

        status = False
        req = requests.post("%s/%s" % (self.api_url, "users/ping.json"),
                            data={"key": self.api_key})
        if req.status_code == 200:
            status = True

        kwargs.update({"status": status})
        return kwargs


class DjrillApiJsonObjectsMixin(object):
    """
    Mixin to grab json objects from the api.
    """
    api_uri = None

    def get_api_uri(self):
        if self.api_uri is None:
            raise NotImplementedError(
                "%(cls)s is missing an api_uri. "
                "Define %(cls)s.api_uri or override %(cls)s.get_api_uri()." % {
                    "cls": self.__class__.__name__
                })

    def get_json_objects(self, extra_dict=None, extra_api_uri=None):
        request_dict = {"key": self.api_key}
        if extra_dict:
            request_dict.update(extra_dict)
        payload = json.dumps(request_dict)
        api_uri = extra_api_uri or self.api_uri
        req = requests.post("%s/%s" % (self.api_url, api_uri),
                            data=payload)
        if req.status_code == 200:
            return req.content
        messages.error(self.request, self._api_error_handler(req))
        return json.dumps("error")

    def _api_error_handler(self, req):
        """
        If the API returns an error, display it to the user.
        """
        content = json.loads(req.content)
        return "Mandrill returned a %d response: %s" % (req.status_code,
                                                        content["message"])


class DjrillWebhookSecretMixin(object):

    @method_decorator(csrf_exempt)
    def dispatch(self, request, *args, **kwargs):
        secret = getattr(settings, 'DJRILL_WEBHOOK_SECRET', None)
        secret_name = getattr(settings, 'DJRILL_WEBHOOK_SECRET_NAME', 'secret')

        if secret is None:
            raise ImproperlyConfigured(
                "You have not set DJRILL_WEBHOOK_SECRET in the settings file.")

        if request.GET.get(secret_name) != secret:
            return HttpResponse(status=403)

        return super(DjrillWebhookSecretMixin, self).dispatch(
            request, *args, **kwargs)


class DjrillWebhookSignatureMixin(object):

    @method_decorator(csrf_exempt)
    def dispatch(self, request, *args, **kwargs):

        signature_key = getattr(settings, 'DJRILL_WEBHOOK_SIGNATURE_KEY', None)

        if signature_key and request.method == "POST":

            # Make webhook url an explicit setting to make sure that this is the exact same string
            # that the user entered in Mandrill
            post_string = getattr(settings, "DJRILL_WEBHOOK_URL", None)
            if post_string is None:
                raise ImproperlyConfigured(
                    "You have set DJRILL_WEBHOOK_SIGNATURE_KEY, but haven't set DJRILL_WEBHOOK_URL in the settings file.")

            signature = request.META.get("HTTP_X_MANDRILL_SIGNATURE", None)
            if not signature:
                return HttpResponse(status=403, content="X-Mandrill-Signature not set")

            # The querydict is a bit special, see https://docs.djangoproject.com/en/dev/ref/request-response/#querydict-objects
            # Mandrill needs it to be sorted and added to the hash
            post_lists = sorted(request.POST.lists())
            for value_list in post_lists:
                for item in value_list[1]:
                    post_string += "%s%s" % (value_list[0], item)

            hash_string = b64encode(hmac.new(key=b(signature_key), msg=b(post_string), digestmod=hashlib.sha1).digest())
            if signature != hash_string:
                return HttpResponse(status=403, content="Signature doesn't match")

        return super(DjrillWebhookSignatureMixin, self).dispatch(
            request, *args, **kwargs)


class DjrillIndexView(DjrillApiMixin, TemplateView):
    template_name = "djrill/status.html"

    def get(self, request, *args, **kwargs):

        payload = json.dumps({"key": self.api_key})
        req = requests.post("%s/users/info.json" % self.api_url, data=payload)

        return self.render_to_response({"status": json.loads(req.content)})


class DjrillSendersListView(DjrillAdminMedia, DjrillApiMixin,
                            DjrillApiJsonObjectsMixin, TemplateView):

    api_uri = "users/senders.json"
    template_name = "djrill/senders_list.html"

    def get(self, request, *args, **kwargs):
        objects = self.get_json_objects()
        context = self.get_context_data()
        context.update({
            "objects": json.loads(objects),
            "media": self.media,
        })

        return self.render_to_response(context)


class DjrillTagListView(DjrillAdminMedia, DjrillApiMixin,
                        DjrillApiJsonObjectsMixin, TemplateView):

    api_uri = "tags/list.json"
    template_name = "djrill/tags_list.html"

    def get(self, request, *args, **kwargs):
        objects = self.get_json_objects()
        context = self.get_context_data()
        context.update({
            "objects": json.loads(objects),
            "media": self.media,
        })
        return self.render_to_response(context)


class DjrillUrlListView(DjrillAdminMedia, DjrillApiMixin,
                        DjrillApiJsonObjectsMixin, TemplateView):

    api_uri = "urls/list.json"
    template_name = "djrill/urls_list.html"

    def get(self, request, *args, **kwargs):
        objects = self.get_json_objects()
        context = self.get_context_data()
        context.update({
            "objects": json.loads(objects),
            "media": self.media
        })
        return self.render_to_response(context)


class DjrillWebhookView(DjrillWebhookSecretMixin, DjrillWebhookSignatureMixin, View):
    def head(self, request, *args, **kwargs):
        return HttpResponse()

    def post(self, request, *args, **kwargs):
        try:
            data = json.loads(request.POST.get('mandrill_events'))
        except TypeError:
            return HttpResponse(status=400)

        for event in data:
            signals.webhook_event.send(
                sender=None, event_type=event['event'], data=event)

        return HttpResponse()

########NEW FILE########
__FILENAME__ = _version
VERSION = (1, 2, 0, 'dev1')  # Remove the 'dev1' component in release branches
__version__ = '.'.join([str(x) for x in VERSION])
__minor_version__ = '.'.join([str(x) for x in VERSION[:2]])  # Sphinx's X.Y "version"

########NEW FILE########
__FILENAME__ = conf
# -*- coding: utf-8 -*-
#
# Djrill documentation build configuration file, created by
# sphinx-quickstart on Sat Mar  2 13:07:34 2013.
#
# This file is execfile()d with the current directory set to its containing dir.
#
# Note that not all possible configuration values are present in this
# autogenerated file.
#
# All configuration values have a default; values that are commented out
# serve to show the default.

import sys, os

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
sys.path.insert(0, os.path.abspath('..'))

# define __version__ and __minor_version__ from ../djrill/_version.py,
# but without importing from djrill (which would make docs dependent on Django, etc.)
with open("../djrill/_version.py") as f:
    code = compile(f.read(), "../djrill/_version.py", 'exec')
    exec(code)

# -- General configuration -----------------------------------------------------

# If your documentation needs a minimal Sphinx version, state it here.
needs_sphinx = '1.0'

# Add any Sphinx extension module names here, as strings. They can be extensions
# coming with Sphinx (named 'sphinx.ext.*') or your custom ones.
extensions = ['sphinx.ext.intersphinx']

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# The suffix of source filenames.
source_suffix = '.rst'

# The encoding of source files.
#source_encoding = 'utf-8-sig'

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = u'Djrill'
# noinspection PyShadowingBuiltins
copyright = u'2013, Djrill contributors (see AUTHORS.txt)'

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
# The short X.Y version.
version = __minor_version__
# The full version, including alpha/beta/rc tags.
release = __version__

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
default_role = "py:obj"

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
htmlhelp_basename = 'Djrilldoc'


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
  ('index', 'Djrill.tex', u'Djrill Documentation',
   u'Djrill contributors (see AUTHORS.txt)', 'manual'),
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
    ('index', 'djrill', u'Djrill Documentation',
     [u'Djrill contributors (see AUTHORS.txt)'], 1)
]

# If true, show URL addresses after external links.
#man_show_urls = False


# -- Options for Texinfo output ------------------------------------------------

# Grouping the document tree into Texinfo files. List of tuples
# (source start file, target name, title, author,
#  dir menu entry, description, category)
texinfo_documents = [
  ('index', 'Djrill', u'Djrill Documentation',
   u'Djrill contributors (see AUTHORS.txt)', 'Djrill', 'Mandrill integration for Django.',
   'Miscellaneous'),
]

# Documents to append as an appendix to all manuals.
#texinfo_appendices = []

# If false, no module index is generated.
#texinfo_domain_indices = True

# How to display URL addresses: 'footnote', 'no', or 'inline'.
#texinfo_show_urls = 'footnote'


# -- Options for Intersphinx ------------------------------------------------

intersphinx_mapping = {
    'python': ('http://docs.python.org/2.7', None),
    'django': ('http://docs.djangoproject.com/en/dev/', 'http://docs.djangoproject.com/en/dev/_objects/'),
    'requests': ('http://docs.python-requests.org/en/latest/', None),
}


def setup(app):
    # Django-specific roles, from https://github.com/django/django/blob/master/docs/_ext/djangodocs.py:
    app.add_crossref_type(
        directivename = "setting",
        rolename      = "setting",
        indextemplate = "pair: %s; setting",
    )
    app.add_crossref_type(
        directivename = "templatetag",
        rolename      = "ttag",
        indextemplate = "pair: %s; template tag"
    )
    app.add_crossref_type(
        directivename = "templatefilter",
        rolename      = "tfilter",
        indextemplate = "pair: %s; template filter"
    )
    app.add_crossref_type(
        directivename = "fieldlookup",
        rolename      = "lookup",
        indextemplate = "pair: %s; field lookup type",
    )

########NEW FILE########
__FILENAME__ = runtests
# python setup.py test
#   or
# python runtests.py

import sys
from django.conf import settings

APP = 'djrill'

settings.configure(
    DEBUG=True,
    DATABASES={
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
        }
    },
    ROOT_URLCONF=APP+'.urls',
    INSTALLED_APPS=(
        'django.contrib.auth',
        'django.contrib.contenttypes',
        'django.contrib.sessions',
        'django.contrib.admin',
        APP,
    )
)

try:
    # Django 1.7+ initialize app registry
    from django import setup
    setup()
except ImportError:
    pass

try:
    from django.test.runner import DiscoverRunner as TestRunner  # Django 1.6+
except ImportError:
    from django.test.simple import DjangoTestSuiteRunner as TestRunner  # Django -1.5


def runtests():
    test_runner = TestRunner(verbosity=1)
    failures = test_runner.run_tests([APP])
    sys.exit(failures)

if __name__ == '__main__':
    runtests()

########NEW FILE########
