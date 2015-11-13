__FILENAME__ = admin
from django.contrib import admin

from .models import SESStat


class SESStatAdmin(admin.ModelAdmin):
    list_display = ('date', 'delivery_attempts', 'bounces', 'complaints',
                    'rejects')

admin.site.register(SESStat, SESStatAdmin)

########NEW FILE########
__FILENAME__ = get_ses_statistics
#!/usr/bin/env python

from collections import defaultdict
from datetime import datetime
from optparse import make_option

from boto.ses import SESConnection

from django.core.management.base import BaseCommand

from django_ses.models import SESStat
from django_ses.views import stats_to_list
from django_ses import settings


def stat_factory():
    return {
        'delivery_attempts': 0,
        'bounces': 0,
        'complaints': 0,
        'rejects': 0,
    }


class Command(BaseCommand):
    """
    Get SES sending statistic and store the result, grouped by date.
    """

    def handle(self, *args, **options):

        connection = SESConnection(
            aws_access_key_id=settings.ACCESS_KEY,
            aws_secret_access_key=settings.SECRET_KEY,
        )
        stats = connection.get_send_statistics()
        data_points = stats_to_list(stats, localize=False)
        stats_dict = defaultdict(stat_factory)

        for data in data_points:
            attempts = int(data['DeliveryAttempts'])
            bounces = int(data['Bounces'])
            complaints = int(data['Complaints'])
            rejects = int(data['Rejects'])
            date = data['Timestamp'].split('T')[0]
            stats_dict[date]['delivery_attempts'] += attempts
            stats_dict[date]['bounces'] += bounces
            stats_dict[date]['complaints'] += complaints
            stats_dict[date]['rejects'] += rejects

        for k, v in stats_dict.items():
            stat, created = SESStat.objects.get_or_create(
                date=k,
                defaults={
                    'delivery_attempts': v['delivery_attempts'],
                    'bounces': v['bounces'],
                    'complaints': v['complaints'],
                    'rejects': v['rejects'],
            })

            # If statistic is not new, modify data if values are different
            if not created and stat.delivery_attempts != v['delivery_attempts']:
                stat.delivery_attempts = v['delivery_attempts']
                stat.bounces = v['bounces']
                stat.complaints = v['complaints']
                stat.rejects = v['rejects']
                stat.save()

########NEW FILE########
__FILENAME__ = ses_email_address
#!/usr/bin/env python
# encoding: utf-8
from optparse import make_option

from boto.regioninfo import RegionInfo
from boto.ses import SESConnection

from django.core.management.base import BaseCommand

from django_ses import settings


class Command(BaseCommand):
    """Verify, delete or list SES email addresses"""

    option_list = BaseCommand.option_list + (
        # -v conflicts with verbose, so use -a
        make_option("-a", "--add", dest="add", default=False,
            help="""Adds an email to your verified email address list.
                    This action causes a confirmation email message to be
                    sent to the specified address."""),
        make_option("-d", "--delete", dest="delete", default=False,
            help="Removes an email from your verified emails list"),
        make_option("-l", "--list", dest="list", default=False,
            action="store_true", help="Outputs all verified emails"),
    )

    def handle(self, *args, **options):

        verbosity = options.get('verbosity', 0)
        add_email = options.get('add', False)
        delete_email = options.get('delete', False)
        list_emails = options.get('list', False)

        access_key_id = settings.ACCESS_KEY
        access_key = settings.SECRET_KEY
        region = RegionInfo(
            name=settings.AWS_SES_REGION_NAME,
            endpoint=settings.AWS_SES_REGION_ENDPOINT)

        connection = SESConnection(
                aws_access_key_id=access_key_id,
                aws_secret_access_key=access_key,
                region=region)

        if add_email:
            if verbosity != '0':
                print "Adding email: %s" % add_email
            connection.verify_email_address(add_email)
        elif delete_email:
            if verbosity != '0':
                print "Removing email: %s" % delete_email
            connection.delete_verified_email_address(delete_email)
        elif list_emails:
            if verbosity != '0':
                print "Fetching list of verified emails:"
            response = connection.list_verified_email_addresses()
            emails = response['ListVerifiedEmailAddressesResponse'][
                'ListVerifiedEmailAddressesResult']['VerifiedEmailAddresses']
            for email in emails:
                print email

########NEW FILE########
__FILENAME__ = models
from django.db import models

class SESStat(models.Model):
    date = models.DateField(unique=True, db_index=True)
    delivery_attempts = models.PositiveIntegerField()
    bounces = models.PositiveIntegerField()
    complaints = models.PositiveIntegerField()
    rejects = models.PositiveIntegerField()

    class Meta:
        verbose_name = 'SES Stat'
        ordering = ['-date']

    def __unicode__(self):
        return self.date.strftime("%Y-%m-%d")

########NEW FILE########
__FILENAME__ = settings
from django.conf import settings
from boto.ses import SESConnection

__all__ = ('ACCESS_KEY', 'SECRET_KEY', 'AWS_SES_REGION_NAME',
        'AWS_SES_REGION_ENDPOINT', 'AWS_SES_AUTO_THROTTLE',
        'AWS_SES_RETURN_PATH', 'DKIM_DOMAIN', 'DKIM_PRIVATE_KEY',
        'DKIM_SELECTOR', 'DKIM_HEADERS', 'TIME_ZONE')

ACCESS_KEY = getattr(settings, 'AWS_SES_ACCESS_KEY_ID',
    getattr(settings, 'AWS_ACCESS_KEY_ID', None))

SECRET_KEY = getattr(settings, 'AWS_SES_SECRET_ACCESS_KEY',
    getattr(settings, 'AWS_SECRET_ACCESS_KEY', None))

AWS_SES_REGION_NAME = getattr(settings, 'AWS_SES_REGION_NAME',
    SESConnection.DefaultRegionName),
AWS_SES_REGION_ENDPOINT = getattr(settings, 'AWS_SES_REGION_ENDPOINT',
    SESConnection.DefaultRegionEndpoint)

AWS_SES_AUTO_THROTTLE = getattr(settings, 'AWS_SES_AUTO_THROTTLE', 0.5)
AWS_SES_RETURN_PATH = getattr(settings, 'AWS_SES_RETURN_PATH', None)

DKIM_DOMAIN = getattr(settings, "DKIM_DOMAIN", None)
DKIM_PRIVATE_KEY = getattr(settings, 'DKIM_PRIVATE_KEY', None)
DKIM_SELECTOR = getattr(settings, 'DKIM_SELECTOR', 'ses')
DKIM_HEADERS = getattr(settings, 'DKIM_HEADERS',
                        ('From', 'To', 'Cc', 'Subject'))

TIME_ZONE = settings.TIME_ZONE

VERIFY_BOUNCE_SIGNATURES = getattr(settings, 'AWS_SES_VERIFY_BOUNCE_SIGNATURES', True)

# Domains that are trusted when retrieving the certificate
# used to sign bounce messages.
BOUNCE_CERT_DOMAINS = getattr(settings, 'AWS_SNS_BOUNCE_CERT_TRUSTED_DOMAINS', (
    'amazonaws.com',
    'amazon.com',
))

########NEW FILE########
__FILENAME__ = signals

from django.dispatch import Signal

bounce_received = Signal(providing_args=["mail_obj", "bounce_obj", "raw_message"])

complaint_received = Signal(providing_args=["mail_obj", "complaint_obj", "raw_message"])

########NEW FILE########
__FILENAME__ = backend
import email

from django.conf import settings as django_settings
from django.utils.encoding import smart_str
from django.core.mail import send_mail
from django.test import TestCase

from boto.ses import SESConnection

import django_ses
from django_ses import settings

# random key generated with `openssl genrsa 512`
DKIM_PRIVATE_KEY = '''
-----BEGIN RSA PRIVATE KEY-----
MIIBOwIBAAJBALCKsjD8UUxBESo1OLN6gptp1lD0U85AgXGL571/SQ3k61KhAQ8h
hL3lnfQKn/XCl2oCXscEwgJv43IUs+VETWECAwEAAQJAQ8XK6GFEuHhWJZTu4n/K
ee0keEmDjq9WwgdKfIXLvsgaaNxCObhzv7G5rPU+U/3z1/0CtGR+DOPgoiaI/5HM
XQIhAN4h+o2WzRrz+dD/+zMGC9h1KEFvukIoP62kLOxW0eg/AiEAy3VD+UkRni4H
6UEJgCe0oZIiBCxj12/wUHFj1cfJYl8CICsndsGjFl2yIEpWMLsM5ag7uoJb7leD
8jsNthyEEWuJAiEAjeF6w26HEK286pZmD66gskN74TkrbuMqzI4mNsCZ2TUCIQCJ
HuuR7wc0HJ/cfVi8Kgm5B+sHY9/7KDWAYGGnbGgCNA==
-----END RSA PRIVATE KEY-----
'''
DKIM_PUBLIC_KEY = 'MFwwDQYJKoZIhvcNAQEBBQADSwAwSAJBALCKsjD8UUxBESo1OLN6gptp1lD0U85AgXGL571/SQ3k61KhAQ8hhL3lnfQKn/XCl2oCXscEwgJv43IUs+VETWECAwEAAQ=='


class FakeSESConnection(SESConnection):
    '''
    A fake SES connection for testing purposes.It behaves similarly
    to django's dummy backend
    (https://docs.djangoproject.com/en/dev/topics/email/#dummy-backend)

    Emails sent with send_raw_email is stored in ``outbox`` attribute
    which is a list of kwargs received by ``send_raw_email``.
    '''
    outbox = []

    def __init__(self, *args, **kwargs):
        pass

    def send_raw_email(self, **kwargs):
        self.outbox.append(kwargs)
        response = {
            'SendRawEmailResponse': {
                'SendRawEmailResult': {
                    'MessageId': 'fake_message_id',
                },
                'ResponseMetadata': {
                    'RequestId': 'fake_request_id',
                },
            }
        }
        return response


class FakeSESBackend(django_ses.SESBackend):
    '''
    A fake SES backend for testing purposes. It overrides the real SESBackend's
    get_rate_limit method so we can run tests without valid AWS credentials.
    '''

    def get_rate_limit(self):
        return 10


class SESBackendTest(TestCase):
    def setUp(self):
        # TODO: Fix this -- this is going to cause side effects
        django_settings.EMAIL_BACKEND = 'django_ses.tests.backend.FakeSESBackend'
        django_ses.SESConnection = FakeSESConnection
        self.outbox = FakeSESConnection.outbox

    def tearDown(self):
        # Empty outbox everytime test finishes
        FakeSESConnection.outbox = []

    def test_send_mail(self):
        send_mail('subject', 'body', 'from@example.com', ['to@example.com'])
        message = self.outbox.pop()
        mail = email.message_from_string(smart_str(message['raw_message']))
        self.assertEqual(mail['subject'], 'subject')
        self.assertEqual(mail['from'], 'from@example.com')
        self.assertEqual(mail['to'], 'to@example.com')
        self.assertEqual(mail.get_payload(), 'body')

    def test_dkim_mail(self):
        # DKIM verification uses DNS to retrieve the public key when checking
        # the signature, so we need to replace the standard query response with
        # one that always returns the test key.
        try:
            import dkim
            import dns
        except ImportError:
            return

        def dns_query(qname, rdtype):
            name = dns.name.from_text(qname)
            response = dns.message.from_text(
                    'id 1\n;ANSWER\n%s 60 IN TXT "v=DKIM1; p=%s"' %\
                            (qname, DKIM_PUBLIC_KEY))
            return dns.resolver.Answer(name, rdtype, 1, response)
        dns.resolver.query = dns_query

        settings.DKIM_DOMAIN = 'example.com'
        settings.DKIM_PRIVATE_KEY = DKIM_PRIVATE_KEY
        send_mail('subject', 'body', 'from@example.com', ['to@example.com'])
        message = self.outbox.pop()['raw_message']
        self.assertTrue(dkim.verify(message))
        self.assertFalse(dkim.verify(message + 'some additional text'))
        self.assertFalse(dkim.verify(
                            message.replace('from@example.com', 'from@spam.com')))

    def test_return_path(self):
        '''
        Ensure that the 'source' argument sent into send_raw_email uses
        settings.AWS_SES_RETURN_PATH, defaults to from address.
        '''
        settings.AWS_SES_RETURN_PATH = None
        send_mail('subject', 'body', 'from@example.com', ['to@example.com'])
        self.assertEqual(self.outbox.pop()['source'], 'from@example.com')


class SESBackendTestReturn(TestCase):
    def setUp(self):
        # TODO: Fix this -- this is going to cause side effects
        django_settings.EMAIL_BACKEND = 'django_ses.tests.backend.FakeSESBackend'
        django_ses.SESConnection = FakeSESConnection
        self.outbox = FakeSESConnection.outbox

    def tearDown(self):
        # Empty outbox everytime test finishes
        FakeSESConnection.outbox = []

    def test_return_path(self):
        settings.AWS_SES_RETURN_PATH = "return@example.com"
        send_mail('subject', 'body', 'from@example.com', ['to@example.com'])
        self.assertEqual(self.outbox.pop()['source'], 'return@example.com')

########NEW FILE########
__FILENAME__ = commands
import copy

from django.core.management import call_command
from django.test import TestCase

from django_ses.models import SESStat

from boto.ses import SESConnection


data_points = [
    {
        'Complaints': '1',
        'Timestamp': '2012-01-01T02:00:00Z',
        'DeliveryAttempts': '2',
        'Bounces': '3',
        'Rejects': '4'
    },
    {
        'Complaints': '1',
        'Timestamp': '2012-01-03T02:00:00Z',
        'DeliveryAttempts': '2',
        'Bounces': '3',
        'Rejects': '4'
    },
    {
        'Complaints': '1',
        'Timestamp': '2012-01-03T03:00:00Z',
        'DeliveryAttempts': '2',
        'Bounces': '3',
        'Rejects': '4'
    }
]


def fake_get_statistics(self):
    return {
        'GetSendStatisticsResponse': {
            'GetSendStatisticsResult': {
                'SendDataPoints': data_points
            },
            'ResponseMetadata': {
                'RequestId': '1'
            }
        }
    }


def fake_connection_init(self, *args, **kwargs):
    pass


class SESCommandTest(TestCase):

    def setUp(self):
        SESConnection.get_send_statistics = fake_get_statistics
        SESConnection.__init__ = fake_connection_init

    def test_get_statistics(self):
        # Test the get_ses_statistics management command
        call_command('get_ses_statistics')

        # Test that days with a single data point is saved properly
        stat = SESStat.objects.get(date='2012-01-01')
        self.assertEqual(stat.complaints, 1)
        self.assertEqual(stat.delivery_attempts, 2)
        self.assertEqual(stat.bounces, 3)
        self.assertEqual(stat.rejects, 4)

        # Test that days with multiple data points get saved properly
        stat = SESStat.objects.get(date='2012-01-03')
        self.assertEqual(stat.complaints, 2)
        self.assertEqual(stat.delivery_attempts, 4)
        self.assertEqual(stat.bounces, 6)
        self.assertEqual(stat.rejects, 8)

        # Changing data points should update database records too
        data_points_copy = copy.deepcopy(data_points)
        data_points_copy[0]['Complaints'] = '2'
        data_points_copy[0]['DeliveryAttempts'] = '3'
        data_points_copy[0]['Bounces'] = '4'
        data_points_copy[0]['Rejects'] = '5'

        def fake_get_statistics_copy(self):
            return {
                'GetSendStatisticsResponse': {
                    'GetSendStatisticsResult': {
                        'SendDataPoints': data_points_copy
                    },
                    'ResponseMetadata': {
                        'RequestId': '1'
                    }
                }
            }
        SESConnection.get_send_statistics = fake_get_statistics_copy
        call_command('get_ses_statistics')
        stat = SESStat.objects.get(date='2012-01-01')
        self.assertEqual(stat.complaints, 2)
        self.assertEqual(stat.delivery_attempts, 3)
        self.assertEqual(stat.bounces, 4)
        self.assertEqual(stat.rejects, 5)

########NEW FILE########
__FILENAME__ = settings
from django.test import TestCase
from django.conf import settings
from django_ses.tests.utils import unload_django_ses

class SettingsImportTest(TestCase):
    def test_aws_access_key_given(self):
        settings.AWS_ACCESS_KEY_ID = "Yjc4MzQ4MGYzMTBhOWY3ODJhODhmNTBkN2QwY2IyZTdhZmU1NDM1ZQo"
        settings.AWS_SECRET_ACCESS_KEY = "NTBjYzAzNzVlMTA0N2FiMmFlODlhYjY5OTYwZjNkNjZmMWNhNzRhOQo"
        unload_django_ses()
        import django_ses
        self.assertEqual(django_ses.settings.ACCESS_KEY, settings.AWS_ACCESS_KEY_ID)
        self.assertEqual(django_ses.settings.SECRET_KEY, settings.AWS_SECRET_ACCESS_KEY)

    def test_ses_access_key_given(self):
        settings.AWS_SES_ACCESS_KEY_ID = "YmM2M2QwZTE3ODk3NTJmYzZlZDc1MDY0ZmJkMDZjZjhmOTU0MWQ4MAo"
        settings.AWS_SES_SECRET_ACCESS_KEY = "NDNiMzRjNzlmZGU0ZDAzZTQxNTkwNzdkNWE5Y2JlNjk4OGFkM2UyZQo"
        unload_django_ses()
        import django_ses
        self.assertEqual(django_ses.settings.ACCESS_KEY, settings.AWS_SES_ACCESS_KEY_ID)
        self.assertEqual(django_ses.settings.SECRET_KEY, settings.AWS_SES_SECRET_ACCESS_KEY)



########NEW FILE########
__FILENAME__ = stats
from django.test import TestCase

from django_ses.views import (emails_parse, stats_to_list, quota_parse,
    sum_stats)

# Mock of what boto's SESConnection.get_send_statistics() returns
STATS_DICT = {
    u'GetSendStatisticsResponse': {
        u'GetSendStatisticsResult': {
            u'SendDataPoints': [
                {
                    u'Bounces': u'1',
                    u'Complaints': u'0',
                    u'DeliveryAttempts': u'11',
                    u'Rejects': u'0',
                    u'Timestamp': u'2011-02-28T13:50:00Z',
                },
                {
                    u'Bounces': u'1',
                    u'Complaints': u'0',
                    u'DeliveryAttempts': u'3',
                    u'Rejects': u'0',
                    u'Timestamp': u'2011-02-24T23:35:00Z',
                },
                {
                    u'Bounces': u'0',
                    u'Complaints': u'2',
                    u'DeliveryAttempts': u'8',
                    u'Rejects': u'0',
                    u'Timestamp': u'2011-02-24T16:35:00Z',
                },
                {
                    u'Bounces': u'0',
                    u'Complaints': u'2',
                    u'DeliveryAttempts': u'33',
                    u'Rejects': u'0',
                    u'Timestamp': u'2011-02-25T20:35:00Z',
                },
                {
                    u'Bounces': u'0',
                    u'Complaints': u'0',
                    u'DeliveryAttempts': u'3',
                    u'Rejects': u'3',
                    u'Timestamp': u'2011-02-28T23:35:00Z',
                },
                {
                    u'Bounces': u'0',
                    u'Complaints': u'0',
                    u'DeliveryAttempts': u'2',
                    u'Rejects': u'3',
                    u'Timestamp': u'2011-02-25T22:50:00Z',
                },
                {
                    u'Bounces': u'0',
                    u'Complaints': u'0',
                    u'DeliveryAttempts': u'6',
                    u'Rejects': u'0',
                    u'Timestamp': u'2011-03-01T13:20:00Z',
                },
            ],
        }
    }
}

QUOTA_DICT = {
    u'GetSendQuotaResponse': {
        u'GetSendQuotaResult': {
            u'Max24HourSend': u'10000.0',
            u'MaxSendRate': u'5.0',
            u'SentLast24Hours': u'1677.0'
        },
        u'ResponseMetadata': {
            u'RequestId': u'8f100233-44e7-11e0-a926-a198963635d8'
        }
    }
}

VERIFIED_EMAIL_DICT = {
    u'ListVerifiedEmailAddressesResponse': {
        u'ListVerifiedEmailAddressesResult': {
            u'VerifiedEmailAddresses': [
                u'test2@example.com',
                u'test1@example.com',
                u'test3@example.com'
            ]
        },
        u'ResponseMetadata': {
            u'RequestId': u'9afe9c18-44ed-11e0-802a-25a1a14c5a6e'
        }
    }
}


class StatParsingTest(TestCase):
    def setUp(self):
        self.stats_dict = STATS_DICT
        self.quota_dict = QUOTA_DICT
        self.emails_dict = VERIFIED_EMAIL_DICT

    def test_stat_to_list(self):
        expected_list = [
            {
                u'Bounces': u'0',
                u'Complaints': u'2',
                u'DeliveryAttempts': u'8',
                u'Rejects': u'0',
                u'Timestamp': u'2011-02-24T16:35:00Z',
            },
            {
                u'Bounces': u'1',
                u'Complaints': u'0',
                u'DeliveryAttempts': u'3',
                u'Rejects': u'0',
                u'Timestamp': u'2011-02-24T23:35:00Z',
            },
            {
                u'Bounces': u'0',
                u'Complaints': u'2',
                u'DeliveryAttempts': u'33',
                u'Rejects': u'0',
                u'Timestamp': u'2011-02-25T20:35:00Z',
            },
            {
                u'Bounces': u'0',
                u'Complaints': u'0',
                u'DeliveryAttempts': u'2',
                u'Rejects': u'3',
                u'Timestamp': u'2011-02-25T22:50:00Z',
            },
            {
                u'Bounces': u'1',
                u'Complaints': u'0',
                u'DeliveryAttempts': u'11',
                u'Rejects': u'0',
                u'Timestamp': u'2011-02-28T13:50:00Z',
            },
            {
                u'Bounces': u'0',
                u'Complaints': u'0',
                u'DeliveryAttempts': u'3',
                u'Rejects': u'3',
                u'Timestamp': u'2011-02-28T23:35:00Z',
            },
            {
                u'Bounces': u'0',
                u'Complaints': u'0',
                u'DeliveryAttempts': u'6',
                u'Rejects': u'0',
                u'Timestamp': u'2011-03-01T13:20:00Z',
            },
        ]
        actual = stats_to_list(self.stats_dict, localize=False)

        self.assertEqual(len(actual), len(expected_list))
        self.assertEqual(actual, expected_list)

    def test_quota_parse(self):
        expected = {
            u'Max24HourSend': u'10000.0',
            u'MaxSendRate': u'5.0',
            u'SentLast24Hours': u'1677.0',
        }
        actual = quota_parse(self.quota_dict)

        self.assertEqual(actual, expected)

    def test_emails_parse(self):
        expected_list = [
            u'test1@example.com',
            u'test2@example.com',
            u'test3@example.com',
        ]
        actual = emails_parse(self.emails_dict)

        self.assertEqual(len(actual), len(expected_list))
        self.assertEqual(actual, expected_list)

    def test_sum_stats(self):
        expected = {
            'Bounces': 2,
            'Complaints': 4,
            'DeliveryAttempts': 66,
            'Rejects': 6,
        }

        stats = stats_to_list(self.stats_dict)
        actual = sum_stats(stats)

        self.assertEqual(actual, expected)

########NEW FILE########
__FILENAME__ = test_urls
try:
    from django.conf.urls import patterns, url
except ImportError:
    # Fall back to the old, pre-1.6 style
    from django.conf.urls.defaults import patterns, url

urlpatterns = patterns('django_ses.views',
    url(r'^dashboard/$', 'dashboard', name='django_ses_stats'),
    url(r'^bounce/$', 'handle_bounce', name='django_ses_bounce'),
    #url(r'^complaint/$', 'handle_complaint', name='django_ses_complaint'),
)

########NEW FILE########
__FILENAME__ = test_verifier
import mock
import base64

try:
    import requests
except ImportError:
    requests = None

try:
    import M2Crypto
except ImportError:
    M2Crypto = None

from unittest import TestCase, skipIf

from django_ses.utils import BounceMessageVerifier

class BounceMessageVerifierTest(TestCase):
    """
    Test for bounce message signature verification
    """
    @skipIf(requests is None, "requests is not installed")
    @skipIf(M2Crypto is None, "M2Crypto is not installed")
    def test_load_certificate(self):
        verifier = BounceMessageVerifier({})
        with mock.patch.object(verifier, '_get_cert_url') as get_cert_url:
            get_cert_url.return_value = "http://www.example.com/"
            with mock.patch.object(requests, 'get') as request_get:
                request_get.return_value.status_code = 200
                request_get.return_value.content = "Spam"
                with mock.patch.object(M2Crypto.X509, 'load_cert_string') as load_cert_string:
                    self.assertEqual(verifier.certificate, load_cert_string.return_value)

    def test_is_verified(self):
        verifier = BounceMessageVerifier({'Signature': base64.b64encode('Spam & Eggs')})
        verifier._certificate = mock.Mock()
        verify_final = verifier._certificate.get_pubkey.return_value.verify_final
        verify_final.return_value = 1
        with mock.patch.object(verifier, '_get_bytes_to_sign'):
            self.assertTrue(verifier.is_verified())

        verify_final.assert_called_once_with('Spam & Eggs')

    def test_is_verified_bad_value(self):
        verifier = BounceMessageVerifier({'Signature': base64.b64encode('Spam & Eggs')})
        verifier._certificate = mock.Mock()
        verifier._certificate.get_pubkey.return_value.verify_final.return_value = 0
        with mock.patch.object(verifier, '_get_bytes_to_sign'):
            self.assertFalse(verifier.is_verified())

    def test_get_cert_url(self):
        """
        Test url trust verification
        """
        verifier = BounceMessageVerifier({
            'SigningCertURL': 'https://amazonaws.com/', 
        })
        self.assertEqual(verifier._get_cert_url(), 'https://amazonaws.com/')

    def test_http_cert_url(self):
        """
        Test url trust verification. Non-https urls should be rejected.
        """
        verifier = BounceMessageVerifier({
            'SigningCertURL': 'http://amazonaws.com/', 
        })
        self.assertEqual(verifier._get_cert_url(), None)

    def test_untrusted_cert_url_domain(self):
        """
        Test url trust verification. Untrusted domains should be rejected.
        """
        verifier = BounceMessageVerifier({
            'SigningCertURL': 'https://www.example.com/', 
        })
        self.assertEqual(verifier._get_cert_url(), None)

########NEW FILE########
__FILENAME__ = utils
import sys

def unload_django_ses():
    del sys.modules['django_ses.settings']
    del sys.modules['django_ses']

########NEW FILE########
__FILENAME__ = views
import mock

from django.test import TestCase
from django.core.urlresolvers import reverse
from django.utils import simplejson as json

from django_ses.signals import bounce_received, complaint_received
from django_ses import utils as ses_utils

class HandleBounceTest(TestCase):
    """
    Test the bounce web hook handler.
    """
    def setUp(self):
        self._old_bounce_receivers = bounce_received.receivers
        bounce_received.receivers = []

        self._old_complaint_receivers = complaint_received.receivers
        complaint_received.receivers = []
    
    def tearDown(self):
        bounce_received.receivers = self._old_bounce_receivers
        complaint_received.receivers = self._old_complaint_receivers

    def test_handle_bounce(self):
        """
        Test handling a normal bounce request.
        """
        req_mail_obj = {
            "timestamp":"2012-05-25T14:59:38.623-07:00",
            "messageId":"000001378603177f-7a5433e7-8edb-42ae-af10-f0181f34d6ee-000000",
            "source":"sender@example.com",
            "destination":[
                "recipient1@example.com",
                "recipient2@example.com",
                "recipient3@example.com",
                "recipient4@example.com"
            ]
        }
        req_bounce_obj = {
            'bounceType': 'Permanent',
            'bounceSubType': 'General',
            'bouncedRecipients': [
                {
                    "status":"5.0.0",
                    "action":"failed",
                    "diagnosticCode":"smtp; 550 user unknown",
                    "emailAddress":"recipient1@example.com",
                }, 
                {
                    "status":"4.0.0",
                    "action":"delayed",
                    "emailAddress":"recipient2@example.com",
                }
            ],
            "reportingMTA": "example.com",
            "timestamp":"2012-05-25T14:59:38.605-07:00",
            "feedbackId":"000001378603176d-5a4b5ad9-6f30-4198-a8c3-b1eb0c270a1d-000000",
        }

        message_obj = {
            'notificationType': 'Bounce',  
            'mail': req_mail_obj,
            'bounce': req_bounce_obj,
        }

        notification = {
            "Type" : "Notification",
            "MessageId" : "22b80b92-fdea-4c2c-8f9d-bdfb0c7bf324",
            "TopicArn" : "arn:aws:sns:us-east-1:123456789012:MyTopic",
            "Subject" : "AWS Notification Message",
            "Message" : json.dumps(message_obj),
            "Timestamp" : "2012-05-02T00:54:06.655Z",
            "SignatureVersion" : "1",
            "Signature" : "",
            "SigningCertURL" : "",
            "UnsubscribeURL" : ""
        }
        
        def _handler(sender, mail_obj, bounce_obj, **kwargs):
            _handler.called = True
            self.assertEquals(req_mail_obj, mail_obj)
            self.assertEquals(req_bounce_obj, bounce_obj)
        _handler.called = False
        bounce_received.connect(_handler)

        # Mock the verification
        with mock.patch.object(ses_utils, 'verify_bounce_message') as verify:
            verify.return_value = True

            self.client.post(reverse('django_ses_bounce'),
                             json.dumps(notification), content_type='application/json')

        self.assertTrue(_handler.called)

    def test_handle_complaint(self):
        """
        Test handling a normal complaint request.
        """
        req_mail_obj = {
            "timestamp":"2012-05-25T14:59:38.623-07:00",
            "messageId":"000001378603177f-7a5433e7-8edb-42ae-af10-f0181f34d6ee-000000",
            "source":"sender@example.com",
            "destination": [
                "recipient1@example.com",
                "recipient2@example.com",
                "recipient3@example.com",
                "recipient4@example.com",
            ]
        }
        req_complaint_obj = {
            "userAgent":"Comcast Feedback Loop (V0.01)",
            "complainedRecipients": [
                {
                    "emailAddress":"recipient1@example.com",
                }
            ],
            "complaintFeedbackType":"abuse",
            "arrivalDate":"2009-12-03T04:24:21.000-05:00",
            "timestamp":"2012-05-25T14:59:38.623-07:00",
            "feedbackId":"000001378603177f-18c07c78-fa81-4a58-9dd1-fedc3cb8f49a-000000",
        }

        message_obj = {
            'notificationType': 'Complaint',
            'mail': req_mail_obj,
            'complaint': req_complaint_obj,
        }

        notification = {
            "Type" : "Notification",
            "MessageId" : "22b80b92-fdea-4c2c-8f9d-bdfb0c7bf324",
            "TopicArn" : "arn:aws:sns:us-east-1:123456789012:MyTopic",
            "Subject" : "AWS Notification Message",
            "Message" : json.dumps(message_obj),
            "Timestamp" : "2012-05-02T00:54:06.655Z",
            "SignatureVersion" : "1",
            "Signature" : "",
            "SigningCertURL" : "",
            "UnsubscribeURL" : ""
        }

        def _handler(sender, mail_obj, complaint_obj, **kwargs):
            _handler.called = True
            self.assertEquals(req_mail_obj, mail_obj)
            self.assertEquals(req_complaint_obj, complaint_obj)
        _handler.called = False
        complaint_received.connect(_handler)

        # Mock the verification
        with mock.patch.object(ses_utils, 'verify_bounce_message') as verify:
            verify.return_value = True

            self.client.post(reverse('django_ses_bounce'), 
                             json.dumps(notification), content_type='application/json')

        self.assertTrue(_handler.called)

########NEW FILE########
__FILENAME__ = urls
try:
    from django.conf.urls import patterns, url
except ImportError: # django < 1.4
    from django.conf.urls.defaults import patterns, url

urlpatterns = patterns('django_ses.views',
    url(r'^$', 'dashboard', name='django_ses_stats'),
)

########NEW FILE########
__FILENAME__ = utils
import base64
import logging
from urlparse import urlparse

try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO

from django.core.exceptions import ImproperlyConfigured
from django.utils.encoding import smart_str
from django_ses import settings

logger = logging.getLogger(__name__)

class BounceMessageVerifier(object):
    """
    A utility class for validating bounce messages

    See: http://docs.amazonwebservices.com/sns/latest/gsg/SendMessageToHttp.verify.signature.html
    """

    def __init__(self, bounce_dict):
        """
        Creates a new bounce message from the given dict.
        """
        self._data = bounce_dict
        self._verified = None

    def is_verified(self):
        """
        Verifies an SES bounce message.

        """
        if self._verified is None:
            signature = self._data.get('Signature')
            if not signature:
                self._verified = False
                return self._verified

            # Decode the signature from base64
            signature = base64.b64decode(signature)

            # Get the message to sign
            sign_bytes = self._get_bytes_to_sign()
            if not sign_bytes:
                self._verified = False
                return self._verified

            if not self.certificate:
                self._verified = False
                return self._verified

            # Extract the public key
            pkey = self.certificate.get_pubkey()

            # Use the public key to verify the signature.
            pkey.verify_init()
            pkey.verify_update(sign_bytes)
            verify_result = pkey.verify_final(signature)

            self._verified = verify_result == 1

        return self._verified

    @property
    def certificate(self):
        """
        Retrieves the certificate used to sign the bounce message.

        TODO: Cache the certificate based on the cert URL so we don't have to
        retrieve it for each bounce message. *We would need to do it in a
        secure way so that the cert couldn't be overwritten in the cache*
        """
        if not hasattr(self, '_certificate'):
            cert_url = self._get_cert_url()
            # Only load certificates from a certain domain?
            # Without some kind of trusted domain check, any old joe could
            # craft a bounce message and sign it using his own certificate
            # and we would happily load and verify it.

            if not cert_url:
                self._certificate = None
                return self._certificate

            try:
                import requests
            except ImportError:
                raise ImproperlyConfigured("requests is required for bounce message verification.")

            try:
                import M2Crypto
            except ImportError:
                raise ImproperlyConfigured("M2Crypto is required for bounce message verification.")

            # We use requests because it verifies the https certificate
            # when retrieving the signing certificate. If https was somehow
            # hijacked then all bets are off.
            response = requests.get(cert_url)
            if response.status_code != 200:
                logger.warning('Could not download certificate from %s: "%s"', cert_url, response.status_code)
                self._certificate = None
                return self._certificate

            # Handle errors loading the certificate.
            # If the certificate is invalid then return
            # false as we couldn't verify the message.
            try:
                self._certificate = M2Crypto.X509.load_cert_string(response.content)
            except M2Crypto.X509.X509Error, e:
                logger.warning('Could not load certificate from %s: "%s"', cert_url, e)
                self._certificate = None
            
        return self._certificate

    def _get_cert_url(self):
        """
        Get the signing certificate URL.
        Only accept urls that match the domains set in the 
        AWS_SNS_BOUNCE_CERT_TRUSTED_DOMAINS setting. Sub-domains
        are allowed. i.e. if amazonaws.com is in the trusted domains
        then sns.us-east-1.amazonaws.com will match.
        """
        cert_url = self._data.get('SigningCertURL')
        if cert_url:
            if cert_url.startswith('https://'):
                url_obj = urlparse(cert_url)
                for trusted_domain in settings.BOUNCE_CERT_DOMAINS:
                    parts = trusted_domain.split('.')
                    if url_obj.netloc.split('.')[-len(parts):] == parts:
                        return cert_url
            logger.warning('Untrusted certificate URL: "%s"', cert_url)
        else:
            logger.warning('No signing certificate URL: "%s"', cert_url)
        return None

    def _get_bytes_to_sign(self):
        """
        Creates the message used for signing SNS notifications.
        This is used to verify the bounce message when it is received.
        """

        # Depending on the message type the fields to add to the message
        # differ so we handle that here.
        msg_type = self._data.get('Type')
        if msg_type == 'Notification':
            fields_to_sign = [
                'Message',
                'MessageId',
                'Subject',
                'Timestamp',
                'TopicArn',
                'Type',
            ]
        elif (msg_type == 'SubscriptionConfirmation' or
              msg_type == 'UnsubscribeConfirmation'):
            fields_to_sign = [
                'Message',
                'MessageId',
                'SubscribeURL',
                'Timestamp',
                'Token',
                'TopicArn',
                'Type',
            ]
        else:
            # Unrecognized type
            logger.warning('Unrecognized SNS message Type: "%s"', msg_type)
            return None
        
        outbytes = StringIO()
        for field_name in fields_to_sign:
            field_value = smart_str(self._data.get(field_name, ''),
                                    errors="replace")
            if field_value:
                outbytes.write(field_name)
                outbytes.write("\n")
                outbytes.write(field_value)
                outbytes.write("\n")
         
        return outbytes.getvalue()

def verify_bounce_message(msg):
    """
    Verify an SES/SNS bounce notification message.
    """
    verifier = BounceMessageVerifier(msg)
    return verifier.is_verified()

########NEW FILE########
__FILENAME__ = views
import urllib2
import copy
import logging
from datetime import datetime

try:
    import pytz
except ImportError:
    pytz = None

from boto.regioninfo import RegionInfo
from boto.ses import SESConnection

from django.http import HttpResponse, HttpResponseBadRequest
from django.views.decorators.http import require_POST
from django.core.cache import cache
from django.core.exceptions import PermissionDenied
from django.shortcuts import render_to_response
from django.template import RequestContext

try:
    import json
except ImportError:
    from django.utils import simplejson as json

from django_ses import settings
from django_ses import signals
from django_ses import utils

logger = logging.getLogger(__name__)

def superuser_only(view_func):
    """
    Limit a view to superuser only.
    """
    def _inner(request, *args, **kwargs):
        if not request.user.is_superuser:
            raise PermissionDenied
        return view_func(request, *args, **kwargs)
    return _inner


def stats_to_list(stats_dict, localize=pytz):
    """
    Parse the output of ``SESConnection.get_send_statistics()`` in to an
    ordered list of 15-minute summaries.
    """
    result = stats_dict['GetSendStatisticsResponse']['GetSendStatisticsResult']
    # Make a copy, so we don't change the original stats_dict.
    result = copy.deepcopy(result)
    datapoints = []
    if localize:
        current_tz = localize.timezone(settings.TIME_ZONE)
    else:
        current_tz = None
    for dp in result['SendDataPoints']:
        if current_tz:
            utc_dt = datetime.strptime(dp['Timestamp'], '%Y-%m-%dT%H:%M:%SZ')
            utc_dt = localize.utc.localize(utc_dt)
            dp['Timestamp'] = current_tz.normalize(
                utc_dt.astimezone(current_tz))
        datapoints.append(dp)

    datapoints.sort(key=lambda x: x['Timestamp'])

    return datapoints


def quota_parse(quota_dict):
    """
    Parse the output of ``SESConnection.get_send_quota()`` to just the results.
    """
    return quota_dict['GetSendQuotaResponse']['GetSendQuotaResult']


def emails_parse(emails_dict):
    """
    Parse the output of ``SESConnection.list_verified_emails()`` and get
    a list of emails.
    """
    result = emails_dict['ListVerifiedEmailAddressesResponse'][
        'ListVerifiedEmailAddressesResult']
    emails = [email for email in result['VerifiedEmailAddresses']]

    return sorted(emails)


def sum_stats(stats_data):
    """
    Summarize the bounces, complaints, delivery attempts and rejects from a
    list of datapoints.
    """
    t_bounces = 0
    t_complaints = 0
    t_delivery_attempts = 0
    t_rejects = 0
    for dp in stats_data:
        t_bounces += int(dp['Bounces'])
        t_complaints += int(dp['Complaints'])
        t_delivery_attempts += int(dp['DeliveryAttempts'])
        t_rejects += int(dp['Rejects'])

    return {
        'Bounces': t_bounces,
        'Complaints': t_complaints,
        'DeliveryAttempts': t_delivery_attempts,
        'Rejects': t_rejects,
    }


@superuser_only
def dashboard(request):
    """
    Graph SES send statistics over time.
    """
    cache_key = 'vhash:django_ses_stats'
    cached_view = cache.get(cache_key)
    if cached_view:
        return cached_view

    region = RegionInfo(
        name=settings.AWS_SES_REGION_NAME,
        endpoint=settings.AWS_SES_REGION_ENDPOINT)

    ses_conn = SESConnection(
        aws_access_key_id=settings.ACCESS_KEY,
        aws_secret_access_key=settings.SECRET_KEY,
        region=region)

    quota_dict = ses_conn.get_send_quota()
    verified_emails_dict = ses_conn.list_verified_email_addresses()
    stats = ses_conn.get_send_statistics()

    quota = quota_parse(quota_dict)
    verified_emails = emails_parse(verified_emails_dict)
    ordered_data = stats_to_list(stats)
    summary = sum_stats(ordered_data)

    extra_context = {
        'title': 'SES Statistics',
        'datapoints': ordered_data,
        '24hour_quota': quota['Max24HourSend'],
        '24hour_sent': quota['SentLast24Hours'],
        '24hour_remaining': float(quota['Max24HourSend']) -
                            float(quota['SentLast24Hours']),
        'persecond_rate': quota['MaxSendRate'],
        'verified_emails': verified_emails,
        'summary': summary,
        'access_key': ses_conn.gs_access_key_id,
        'local_time': True if pytz else False,
    }

    response = render_to_response(
        'django_ses/send_stats.html',
        extra_context,
        context_instance=RequestContext(request))

    cache.set(cache_key, response, 60 * 15)  # Cache for 15 minutes
    return response

@require_POST
def handle_bounce(request):
    """
    Handle a bounced email via an SNS webhook.

    Parse the bounced message and send the appropriate signal.
    For bounce messages the bounce_received signal is called.
    For complaint messages the complaint_received signal is called.
    See: http://docs.aws.amazon.com/sns/latest/gsg/json-formats.html#http-subscription-confirmation-json
    See: http://docs.amazonwebservices.com/ses/latest/DeveloperGuide/NotificationsViaSNS.html
    
    In addition to email bounce requests this endpoint also supports the SNS
    subscription confirmation request. This request is sent to the SNS
    subscription endpoint when the subscription is registered.
    See: http://docs.aws.amazon.com/sns/latest/gsg/Subscribe.html

    For the format of the SNS subscription confirmation request see this URL:
    http://docs.aws.amazon.com/sns/latest/gsg/json-formats.html#http-subscription-confirmation-json
    
    SNS message signatures are verified by default. This funcionality can
    be disabled by setting AWS_SES_VERIFY_BOUNCE_SIGNATURES to False.
    However, this is not recommended.
    See: http://docs.amazonwebservices.com/sns/latest/gsg/SendMessageToHttp.verify.signature.html
    """

    # For Django >= 1.4 use request.body, otherwise
    # use the old request.raw_post_data
    if hasattr(request, 'body'):
        raw_json = request.body
    else:
        raw_json = request.raw_post_data

    try:
        notification = json.loads(raw_json)
    except ValueError, e:
        # TODO: What kind of response should be returned here?
        logger.warning('Recieved bounce with bad JSON: "%s"', e)
        return HttpResponseBadRequest()

    # Verify the authenticity of the bounce message.
    if (settings.VERIFY_BOUNCE_SIGNATURES and 
            not utils.verify_bounce_message(notification)):
        # Don't send any info back when the notification is not
        # verified. Simply, don't process it.
        logger.info('Recieved unverified notification: Type: %s', 
            notification.get('Type'),
            extra={
                'notification': notification,
            },
        )
        return HttpResponse()

    if notification.get('Type') in ('SubscriptionConfirmation',
                                    'UnsubscribeConfirmation'):
        # Process the (un)subscription confirmation.

        logger.info('Recieved subscription confirmation: TopicArn: %s', 
            notification.get('TopicArn'),
            extra={
                'notification': notification,
            },
        )

        # Get the subscribe url and hit the url to confirm the subscription.
        subscribe_url = notification.get('SubscribeURL')
        try:
            urllib2.urlopen(subscribe_url).read()
        except urllib2.URLError, e:
            # Some kind of error occurred when confirming the request.
            logger.error('Could not confirm subscription: "%s"', e,
                extra={
                    'notification': notification,
                },
                exc_info=True,
            )
    elif notification.get('Type') == 'Notification':
        try:
            message = json.loads(notification['Message'])
        except ValueError, e:
            # The message isn't JSON.
            # Just ignore the notification.
            logger.warning('Recieved bounce with bad JSON: "%s"', e, extra={
                'notification': notification, 
            })
        else:
            mail_obj = message.get('mail')
            notification_type = message.get('notificationType')
            
            if notification_type == 'Bounce':
                # Bounce 
                bounce_obj = message.get('bounce', {})
                
                # Logging
                feedback_id = bounce_obj.get('feedbackId')
                bounce_type = bounce_obj.get('bounceType')
                bounce_subtype = bounce_obj.get('bounceSubType')
                logger.info(
                    'Recieved bounce notification: feedbackId: %s, bounceType: %s, bounceSubType: %s', 
                    feedback_id, bounce_type, bounce_subtype,
                    extra={
                        'notification': notification,
                    },
                )

                signals.bounce_received.send(
                    sender=handle_bounce,
                    mail_obj=mail_obj,
                    bounce_obj=bounce_obj,
                    raw_message=raw_json,
                )
            elif notification_type == 'Complaint':
                # Complaint
                complaint_obj = message.get('complaint', {})

                # Logging
                feedback_id = complaint_obj.get('feedbackId')
                feedback_type = complaint_obj.get('complaintFeedbackType')
                logger.info('Recieved complaint notification: feedbackId: %s, feedbackType: %s', 
                    feedback_id, feedback_type,
                    extra={
                        'notification': notification,
                    },
                )

                signals.complaint_received.send(
                    sender=handle_bounce,
                    mail_obj=mail_obj,
                    complaint_obj=complaint_obj,
                    raw_message=raw_json,
                )
            else:
                # We received an unknown notification type. Just log and
                # ignore it.
                logger.warning("Recieved unknown notification", extra={
                    'notification': notification,
                })
    else:
        logger.info('Recieved unknown notification type: %s', 
            notification.get('Type'),
            extra={
                'notification': notification,
            },
        )

    # AWS will consider anything other than 200 to be an error response and
    # resend the SNS request. We don't need that so we return 200 here.
    return HttpResponse()

########NEW FILE########
__FILENAME__ = local_settings.template
AWS_ACCESS_KEY_ID = 'YOUR-ACCESS-KEY-ID'
AWS_SECRET_ACCESS_KEY = 'YOUR-SECRET-ACCESS-KEY'


########NEW FILE########
__FILENAME__ = manage
#!/usr/bin/env python
from django.core.management import execute_manager
try:
    import settings # Assumed to be in the same directory.
except ImportError:
    import sys
    sys.stderr.write("Error: Can't find the file 'settings.py' in the directory containing %r. It appears you've customized things.\nYou'll have to run django-admin.py, passing it your settings module.\n(If the file settings.py does indeed exist, it's causing an ImportError somehow.)\n" % __file__)
    sys.exit(1)

import sys
sys.path.insert(0, '..')

if __name__ == "__main__":
    execute_manager(settings)

########NEW FILE########
__FILENAME__ = middleware
from django.contrib.auth.models import AnonymousUser


class FakeSuperuserMiddleware(object):

    def process_request(self, request):
        request.user = AnonymousUser()
        request.user.is_superuser = True


########NEW FILE########
__FILENAME__ = settings
import os
import sys

DEBUG = True
BASE_PATH = os.path.dirname(__file__)

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join(BASE_PATH, 'example.db'),
    }
}

SECRET_KEY = 'u=0tir)ob&3%uw3h4&&$%!!kffw$h*!_ia46f)qz%2rxnkhak&'

MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
)

TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
)

TEMPLATE_DIRS = (
    os.path.join(os.path.dirname(__file__), 'templates'),
)

INSTALLED_APPS = (
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.admin',
    'django.contrib.auth',
    'django_ses',
)

ROOT_URLCONF = 'urls'
STATIC_URL = '/static/'

EMAIL_BACKEND = 'django_ses.SESBackend'
AWS_ACCESS_KEY_ID = ''
AWS_SECRET_ACCESS_KEY = ''

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '[%(asctime)s][%(name)s] %(levelname)s %(message)s',
            'datefmt': "%Y-%m-%d %H:%M:%S",
        },
        'simple': {
            'format': '%(levelname)s %(message)s'
        }
    },
    'handlers': {
        'mail_admins': {
            'level': 'ERROR',
            'class': 'django.utils.log.AdminEmailHandler'
        },
        'stderr': {
            'level': 'ERROR',
            'formatter': 'verbose',
            'class':'logging.StreamHandler',
            'stream': sys.stderr,
        },
        'stdout': {
            'level': 'INFO',
            'formatter': 'verbose',
            'class': 'logging.StreamHandler', 
            'stream': sys.stdout,
        },
    },
    'loggers': {
        '': {
            'handlers': ['stdout'],
            'level': 'DEBUG',
        },
        'django.request': {
            'handlers': ['mail_admins'],
            'level': 'ERROR',
            'propagate': True,
        },
    }
}

try:
    from local_settings import *
except ImportError:
    pass


########NEW FILE########
__FILENAME__ = urls
try:
    from django.conf.urls import *
except ImportError: # django < 1.4
    from django.conf.urls.defaults import *

from django.contrib.staticfiles.urls import staticfiles_urlpatterns

from django.contrib import admin

admin.autodiscover()

urlpatterns = patterns('',
    url(r'^admin/doc/', include('django.contrib.admindocs.urls')),
    url(r'^admin/', include(admin.site.urls)),

    url(r'^$', 'views.index', name='index'),
    url(r'^send-email/$', 'views.send_email', name='send-email'),
    url(r'^reporting/', include('django_ses.urls')),

    url(r'^bounce/', 'django_ses.views.handle_bounce', name='handle_bounce'),
)

urlpatterns += staticfiles_urlpatterns()

########NEW FILE########
__FILENAME__ = views
from django.http import HttpResponse
from django.core.urlresolvers import reverse
from django.core.mail import send_mail, EmailMessage
from django.shortcuts import render_to_response

def index(request):
    return render_to_response('index.html')

def send_email(request):
    if request.method == 'POST':
        try:
            subject = request.POST['subject']
            message = request.POST['message']
            from_email = request.POST['from']
            html_message = bool(request.POST.get('html-message', False))
            recipient_list = [request.POST['to']]

            email = EmailMessage(subject, message, from_email, recipient_list)
            if html_message:
                email.content_subtype = 'html'
            email.send()
        except KeyError:
            return HttpResponse('Please fill in all fields')

        return HttpResponse('Email sent :)')
    else:
        return render_to_response('send-email.html')


########NEW FILE########
__FILENAME__ = runtests
"""
This code provides a mechanism for running django_ses' internal
test suite without having a full Django project.  It sets up the
global configuration, then dispatches out to `call_command` to
kick off the test suite.

## The Code
"""

# Setup and configure the minimal settings necessary to
# run the test suite.  Note that Django requires that the
# `DATABASES` value be present and configured in order to
# do anything.

from django.conf import settings

settings.configure(
    INSTALLED_APPS=[
        "django_ses",
    ],
    DATABASES={
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": ":memory:",
        }
    },
    ROOT_URLCONF='django_ses.tests.test_urls',
)

# Start the test suite now that the settings are configured.
from django.core.management import call_command
call_command("test", "django_ses")

########NEW FILE########
