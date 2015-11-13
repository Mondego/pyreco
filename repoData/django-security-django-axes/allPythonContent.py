__FILENAME__ = admin
from django.contrib import admin

from axes.models import AccessLog
from axes.models import AccessAttempt


class AccessAttemptAdmin(admin.ModelAdmin):
    list_display = (
        'attempt_time',
        'ip_address',
        'user_agent',
        'username',
        'path_info',
        'failures_since_start',
    )

    list_filter = [
        'attempt_time',
        'ip_address',
        'username',
        'path_info',
    ]

    search_fields = [
        'ip_address',
        'username',
        'user_agent',
        'path_info',
    ]

    date_hierarchy = 'attempt_time'

    fieldsets = (
        (None, {
            'fields': ('path_info', 'failures_since_start')
        }),
        ('Form Data', {
            'fields': ('get_data', 'post_data')
        }),
        ('Meta Data', {
            'fields': ('user_agent', 'ip_address', 'http_accept')
        })
    )

admin.site.register(AccessAttempt, AccessAttemptAdmin)


class AccessLogAdmin(admin.ModelAdmin):
    list_display = (
        'attempt_time',
        'logout_time',
        'ip_address',
        'username',
        'user_agent',
        'path_info',
    )

    list_filter = [
        'attempt_time',
        'logout_time',
        'ip_address',
        'username',
        'path_info',
    ]

    search_fields = [
        'ip_address',
        'user_agent',
        'username',
        'path_info',
    ]

    date_hierarchy = 'attempt_time'

    fieldsets = (
        (None, {
            'fields': ('path_info',)
        }),
        ('Meta Data', {
            'fields': ('user_agent', 'ip_address', 'http_accept')
        })
    )

admin.site.register(AccessLog, AccessLogAdmin)

########NEW FILE########
__FILENAME__ = decorators
import logging

from datetime import timedelta

from django.conf import settings
from django.contrib.auth import logout
from django.core.exceptions import ObjectDoesNotExist
from django.http import HttpResponse
from django.http import HttpResponseRedirect
from django.shortcuts import render_to_response
from django.template import RequestContext
from django.utils import timezone as datetime
from django.utils.translation import ugettext_lazy

try:
    from django.contrib.auth import get_user_model
except ImportError:  # django < 1.5
    from django.contrib.auth.models import User
else:
    User = get_user_model()

try:
    from django.contrib.auth.models import SiteProfileNotAvailable
except ImportError: # django >= 1.7
    SiteProfileNotAvailable = type('SiteProfileNotAvailable', (Exception,), {})

from axes.models import AccessLog
from axes.models import AccessAttempt
from axes.signals import user_locked_out
import axes
from django.utils import six


# see if the user has overridden the failure limit
FAILURE_LIMIT = getattr(settings, 'AXES_LOGIN_FAILURE_LIMIT', 3)

# see if the user has set axes to lock out logins after failure limit
LOCK_OUT_AT_FAILURE = getattr(settings, 'AXES_LOCK_OUT_AT_FAILURE', True)

USE_USER_AGENT = getattr(settings, 'AXES_USE_USER_AGENT', False)

# see if the django app is sitting behind a reverse proxy
BEHIND_REVERSE_PROXY = getattr(settings, 'AXES_BEHIND_REVERSE_PROXY', False)

# if the django app is behind a reverse proxy, look for the ip address using this HTTP header value
REVERSE_PROXY_HEADER = getattr(settings, 'AXES_REVERSE_PROXY_HEADER', 'HTTP_X_FORWARDED_FOR')

COOLOFF_TIME = getattr(settings, 'AXES_COOLOFF_TIME', None)
if isinstance(COOLOFF_TIME, int):
    COOLOFF_TIME = timedelta(hours=COOLOFF_TIME)

LOGGER = getattr(settings, 'AXES_LOGGER', 'axes.watch_login')

LOCKOUT_TEMPLATE = getattr(settings, 'AXES_LOCKOUT_TEMPLATE', None)
VERBOSE = getattr(settings, 'AXES_VERBOSE', True)

# whitelist and blacklist
# todo: convert the strings to IPv4 on startup to avoid type conversion during processing
ONLY_WHITELIST = getattr(settings, 'AXES_ONLY_ALLOW_WHITELIST', False)
IP_WHITELIST = getattr(settings, 'AXES_IP_WHITELIST', None)
IP_BLACKLIST = getattr(settings, 'AXES_IP_BLACKLIST', None)

ERROR_MESSAGE = ugettext_lazy("Please enter a correct username and password. "
                              "Note that both fields are case-sensitive.")


log = logging.getLogger(LOGGER)
if VERBOSE:
    log.info('AXES: BEGIN LOG')
    log.info('Using django-axes ' + axes.get_version())


if BEHIND_REVERSE_PROXY:
    log.debug('Axes is configured to be behind reverse proxy...looking for header value %s', REVERSE_PROXY_HEADER)


def get_ip(request):
    if not BEHIND_REVERSE_PROXY:
        ip = request.META.get('REMOTE_ADDR', '')
    else:
        ip = request.META.get(REVERSE_PROXY_HEADER, '')
        if ip == '':
            raise Warning('Axes is configured for operation behind a reverse proxy but could not find '\
                          'an HTTP header value {0}. Check your proxy server settings '\
                          'to make sure this header value is being passed.'.format(REVERSE_PROXY_HEADER))
    return ip


def get_lockout_url():
    return getattr(settings, 'AXES_LOCKOUT_URL', None)


def query2str(items):
    """Turns a dictionary into an easy-to-read list of key-value pairs.

    If there's a field called "password" it will be excluded from the output.
    """
    # Limit the length of the value to avoid a DoS attack
    value_maxlimit = 256

    kvs = []
    for k, v in items:
        if k != 'password':
            kvs.append(six.u('%s=%s') % (k, v[:256]))

    return '\n'.join(kvs)


def ip_in_whitelist(ip):
    if IP_WHITELIST is not None:
        return ip in IP_WHITELIST

    return False


def ip_in_blacklist(ip):
    if IP_BLACKLIST is not None:
        return ip in IP_BLACKLIST

    return False


def is_user_lockable(request):
    """Check if the user has a profile with nolockout
    If so, then return the value to see if this user is special
    and doesn't get their account locked out
    """
    try:
        field = getattr(User, 'USERNAME_FIELD', 'username')
        kwargs = {
            field: request.POST.get('username')
        }
        user = User.objects.get(**kwargs)
    except User.DoesNotExist:
        # not a valid user
        return True

    # Django 1.5 does not support profile anymore, ask directly to user
    if hasattr(user, 'nolockout'):
        # need to revert since we need to return
        # false for users that can't be blocked
        return not user.nolockout

    try:
        profile = user.get_profile()
    except (SiteProfileNotAvailable, ObjectDoesNotExist, AttributeError):
        # no profile
        return True

    if hasattr(profile, 'nolockout'):
        # need to revert since we need to return
        # false for users that can't be blocked
        return not profile.nolockout
    else:
        return True

def _get_user_attempts(request):
    """Returns access attempt record if it exists.
    Otherwise return None.
    """
    ip = get_ip(request)

    username = request.POST.get('username', None)

    if USE_USER_AGENT:
        ua = request.META.get('HTTP_USER_AGENT', '<unknown>')[:255]
        attempts = AccessAttempt.objects.filter(
            user_agent=ua, ip_address=ip, username=username, trusted=True
        )
    else:
        attempts = AccessAttempt.objects.filter(
            ip_address=ip, username=username, trusted=True
        )

    if not attempts:
        params = {'ip_address': ip, 'trusted': False}
        if USE_USER_AGENT:
            params['user_agent'] = ua

        attempts = AccessAttempt.objects.filter(**params)
        if username and not ip_in_whitelist(ip):
            del params['ip_address']
            params['username'] = username
            attempts |= AccessAttempt.objects.filter(**params)

    return attempts

def get_user_attempts(request):
    objects_deleted = False
    attempts = _get_user_attempts(request)

    if COOLOFF_TIME:
        for attempt in attempts:
            if attempt.attempt_time + COOLOFF_TIME < datetime.now():
                if attempt.trusted:
                    attempt.failures_since_start = 0
                    attempt.save()
                else:
                    attempt.delete()
                    objects_deleted = True

    # If objects were deleted, we need to update the queryset to reflect this,
    # so force a reload.
    if objects_deleted:
        attempts = _get_user_attempts(request)

    return attempts


def watch_login(func):
    """
    Used to decorate the django.contrib.admin.site.login method.
    """

    def decorated_login(request, *args, **kwargs):
        # share some useful information
        if func.__name__ != 'decorated_login' and VERBOSE:
            log.info('AXES: Calling decorated function: %s' % func.__name__)
            if args:
                log.info('args: %s' % str(args))
            if kwargs:
                log.info('kwargs: %s' % kwargs)

        # TODO: create a class to hold the attempts records and perform checks
        # with its methods? or just store attempts=get_user_attempts here and
        # pass it to the functions
        # also no need to keep accessing these:
        # ip = request.META.get('REMOTE_ADDR', '')
        # ua = request.META.get('HTTP_USER_AGENT', '<unknown>')
        # username = request.POST.get('username', None)

        # if the request is currently under lockout, do not proceed to the
        # login function, go directly to lockout url, do not pass go, do not
        # collect messages about this login attempt
        if is_already_locked(request):
            return lockout_response(request)

        # call the login function
        response = func(request, *args, **kwargs)

        if func.__name__ == 'decorated_login':
            # if we're dealing with this function itself, don't bother checking
            # for invalid login attempts.  I suppose there's a bunch of
            # recursion going on here that used to cause one failed login
            # attempt to generate 10+ failed access attempt records (with 3
            # failed attempts each supposedly)
            return response

        if request.method == 'POST':
            # see if the login was successful
            login_unsuccessful = (
                response and
                not response.has_header('location') and
                response.status_code != 302
            )

            access_log = AccessLog.objects.create(
                user_agent=request.META.get('HTTP_USER_AGENT', '<unknown>')[:255],
                ip_address=get_ip(request),
                username=request.POST.get('username', None),
                http_accept=request.META.get('HTTP_ACCEPT', '<unknown>'),
                path_info=request.META.get('PATH_INFO', '<unknown>'),
                trusted=not login_unsuccessful,
            )
            if check_request(request, login_unsuccessful):
                return response

            return lockout_response(request)

        return response

    return decorated_login


def lockout_response(request):
    if LOCKOUT_TEMPLATE:
        context = {
            'cooloff_time': COOLOFF_TIME,
            'failure_limit': FAILURE_LIMIT,
        }
        return render_to_response(LOCKOUT_TEMPLATE, context,
                                  context_instance=RequestContext(request))

    LOCKOUT_URL = get_lockout_url()
    if LOCKOUT_URL:
        return HttpResponseRedirect(LOCKOUT_URL)

    if COOLOFF_TIME:
        return HttpResponse("Account locked: too many login attempts.  "
                            "Please try again later.")
    else:
        return HttpResponse("Account locked: too many login attempts.  "
                            "Contact an admin to unlock your account.")


def is_already_locked(request):
    ip = get_ip(request)

    if ONLY_WHITELIST:
        if not ip_in_whitelist(ip):
            return True

    if ip_in_blacklist(ip):
        return True

    attempts = get_user_attempts(request)
    user_lockable = is_user_lockable(request)
    for attempt in attempts:
        if attempt.failures_since_start >= FAILURE_LIMIT and LOCK_OUT_AT_FAILURE and user_lockable:
            return True

    return False


def check_request(request, login_unsuccessful):
    ip_address = get_ip(request)
    username = request.POST.get('username', None)
    failures = 0
    attempts = get_user_attempts(request)

    for attempt in attempts:
        failures = max(failures, attempt.failures_since_start)

    if login_unsuccessful:
        # add a failed attempt for this user
        failures += 1

        # Create an AccessAttempt record if the login wasn't successful
        # has already attempted, update the info
        if len(attempts):
            for attempt in attempts:
                attempt.get_data = '%s\n---------\n%s' % (
                    attempt.get_data,
                    query2str(request.GET.items()),
                )
                attempt.post_data = '%s\n---------\n%s' % (
                    attempt.post_data,
                    query2str(request.POST.items())
                )
                attempt.http_accept = request.META.get('HTTP_ACCEPT', '<unknown>')
                attempt.path_info = request.META.get('PATH_INFO', '<unknown>')
                attempt.failures_since_start = failures
                attempt.attempt_time = datetime.now()
                attempt.save()
                log.info('AXES: Repeated login failure by %s. Updating access '
                         'record. Count = %s' %
                         (attempt.ip_address, failures))
        else:
            create_new_failure_records(request, failures)
    else:
        # user logged in -- forget the failed attempts
        failures = 0
        trusted_record_exists = False
        for attempt in attempts:
            if not attempt.trusted:
                attempt.delete()
            else:
                trusted_record_exists = True
                attempt.failures_since_start = 0
                attempt.save()

        if trusted_record_exists is False:
            create_new_trusted_record(request)

    user_lockable = is_user_lockable(request)
    # no matter what, we want to lock them out if they're past the number of
    # attempts allowed, unless the user is set to notlockable
    if failures > FAILURE_LIMIT and LOCK_OUT_AT_FAILURE and user_lockable:
        # We log them out in case they actually managed to enter the correct
        # password
        logout(request)
        log.warn('AXES: locked out %s after repeated login attempts.' %
                 (ip_address,))
        # send signal when someone is locked out.
        user_locked_out.send("axes", request=request, username=username, ip_address=ip_address)

        # if a trusted login has violated lockout, revoke trust
        for attempt in [a for a in attempts if a.trusted]:
            attempt.delete()
            create_new_failure_records(request, failures)

        return False

    return True


def create_new_failure_records(request, failures):
    ip = get_ip(request)
    ua = request.META.get('HTTP_USER_AGENT', '<unknown>')[:255]
    username = request.POST.get('username', None)

    params = {
        'user_agent': ua,
        'ip_address': ip,
        'username': None,
        'get_data': query2str(request.GET.items()),
        'post_data': query2str(request.POST.items()),
        'http_accept': request.META.get('HTTP_ACCEPT', '<unknown>'),
        'path_info': request.META.get('PATH_INFO', '<unknown>'),
        'failures_since_start': failures,
    }

    # record failed attempt from this IP
    AccessAttempt.objects.create(**params)

    # record failed attempt on this username from untrusted IP
    params.update({
        'ip_address': None,
        'username': username,
    })
    AccessAttempt.objects.create(**params)

    log.info('AXES: New login failure by %s. Creating access record.' % (ip,))


def create_new_trusted_record(request):
    ip = get_ip(request)
    ua = request.META.get('HTTP_USER_AGENT', '<unknown>')[:255]
    username = request.POST.get('username', None)

    if not username:
        return False

    AccessAttempt.objects.create(
        user_agent=ua,
        ip_address=ip,
        username=username,
        get_data=query2str(request.GET.items()),
        post_data=query2str(request.POST.items()),
        http_accept=request.META.get('HTTP_ACCEPT', '<unknown>'),
        path_info=request.META.get('PATH_INFO', '<unknown>'),
        failures_since_start=0,
        trusted=True
    )

########NEW FILE########
__FILENAME__ = axes_list_attempts
from django.core.management.base import BaseCommand
from django.core.management.base import CommandError

from axes.models import AccessAttempt

class Command(BaseCommand):
    args = ''
    help = ("List login attempts")

    def handle(self, *args, **kwargs):
        for at in  AccessAttempt.objects.all():
            print "%s %s %s" % (at.ip_address,  at.username, at.failures)


########NEW FILE########
__FILENAME__ = axes_reset
from django.core.management.base import BaseCommand
from django.core.management.base import CommandError

from axes.utils import reset


class Command(BaseCommand):
    args = ''
    help = ("resets any lockouts or failed login records. If called with an "
            "IP, resets only for that IP")

    def handle(self, *args, **kwargs):
        count = 0
        if args:
            for ip in args:
                count += reset(ip=ip)
        else:
            count = reset()

        if count:
            print('{0} attempts removed.'.format(count))
        else:
            print('No attempts found.')

########NEW FILE########
__FILENAME__ = middleware
from django.contrib.auth import views as auth_views

from axes.decorators import watch_login


class FailedLoginMiddleware(object):
    def __init__(self, *args, **kwargs):
        super(FailedLoginMiddleware, self).__init__(*args, **kwargs)

        # watch the auth login
        auth_views.login = watch_login(auth_views.login)

########NEW FILE########
__FILENAME__ = models
from django.db import models
from django.utils import six

class CommonAccess(models.Model):
    user_agent = models.CharField(
        max_length=255,
    )

    ip_address = models.IPAddressField(
        verbose_name='IP Address',
        null=True,
    )

    username = models.CharField(
        max_length=255,
        null=True,
    )

    # Once a user logs in from an ip, that combination is trusted and not
    # locked out in case of a distributed attack
    trusted = models.BooleanField(
        default=False,
    )

    http_accept = models.CharField(
        verbose_name='HTTP Accept',
        max_length=1025,
    )

    path_info = models.CharField(
        verbose_name='Path',
        max_length=255,
    )

    attempt_time = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        abstract = True
        ordering = ['-attempt_time']


class AccessAttempt(CommonAccess):
    get_data = models.TextField(
        verbose_name='GET Data',
    )

    post_data = models.TextField(
        verbose_name='POST Data',
    )

    failures_since_start = models.PositiveIntegerField(
        verbose_name='Failed Logins',
    )

    @property
    def failures(self):
        return self.failures_since_start

    def __unicode__(self):
        return six.u('Attempted Access: %s') % self.attempt_time


class AccessLog(CommonAccess):
    logout_time = models.DateTimeField(
        null=True,
        blank=True,
    )

    def __unicode__(self):
        return six.u('Access Log for %s @ %s') % (self.username, self.attempt_time)

########NEW FILE########
__FILENAME__ = signals
from django.dispatch import receiver
from django.dispatch import Signal
from django.utils.timezone import now
from django.contrib.auth.signals import user_logged_out
from django.core.exceptions import ObjectDoesNotExist

from axes.models import AccessLog


user_locked_out = Signal(providing_args=['request', 'username', 'ip_address'])


@receiver(user_logged_out)
def log_user_lockout(sender, request, user, signal, *args, **kwargs):
    """ When a user logs out, update the access log
    """
    if not user:
        return

    try:
        username = user.get_username()
    except AttributeError:
        # Django < 1.5
        username = user.username

    access_logs = AccessLog.objects.filter(
        username=username,
        logout_time__isnull=True,
    ).order_by('-attempt_time')

    if access_logs:
        access_log = access_logs[0]
        access_log.logout_time = now()
        access_log.save()

########NEW FILE########
__FILENAME__ = tests
import random
import string
import time

from django.test import TestCase
from django.contrib.auth.models import User
from django.core.urlresolvers import NoReverseMatch
from django.core.urlresolvers import reverse

from axes.decorators import COOLOFF_TIME
from axes.decorators import FAILURE_LIMIT
from axes.models import AccessLog
from axes.utils import reset


# Django >= 1.7 compatibility
try:
    ADMIN_LOGIN_URL = reverse('admin:login')
    LOGIN_FORM_KEY = '<form action="/admin/login/" method="post" id="login-form">'
except NoReverseMatch:
    ADMIN_LOGIN_URL = reverse('admin:index')
    LOGIN_FORM_KEY = 'this_is_the_login_form'


class AccessAttemptTest(TestCase):
    """Test case using custom settings for testing
    """
    VALID_USERNAME = 'valid'
    LOCKED_MESSAGE = 'Account locked: too many login attempts.'

    def _get_random_string(self):
        """Returns a random string
        """
        chars = string.ascii_uppercase + string.digits

        return ''.join(random.choice(chars) for x in range(20))

    def _login(self, is_valid=False, user_agent='test-browser'):
        """Login a user. A valid credential is used when is_valid is True,
        otherwise it will use a random string to make a failed login.
        """
        username = self.VALID_USERNAME if is_valid else self._get_random_string()

        response = self.client.post(ADMIN_LOGIN_URL, {
            'username': username,
            'password': username,
            'this_is_the_login_form': 1,
        }, HTTP_USER_AGENT=user_agent)

        return response

    def setUp(self):
        """Create a valid user for login
        """
        user = User.objects.create_superuser(
            username=self.VALID_USERNAME,
            email='test@example.com',
            password=self.VALID_USERNAME,
        )

    def test_failure_limit_once(self):
        """Tests the login lock trying to login one more time
        than failure limit
        """
        for i in range(0, FAILURE_LIMIT):
            response = self._login()
            # Check if we are in the same login page
            self.assertContains(response, LOGIN_FORM_KEY)

        # So, we shouldn't have gotten a lock-out yet.
        # But we should get one now
        response = self._login()
        self.assertContains(response, self.LOCKED_MESSAGE)

    def test_failure_limit_many(self):
        """Tests the login lock trying to login a lot of times more
        than failure limit
        """
        for i in range(0, FAILURE_LIMIT):
            response = self._login()
            # Check if we are in the same login page
            self.assertContains(response, LOGIN_FORM_KEY)

        # So, we shouldn't have gotten a lock-out yet.
        # But we should get one now
        for i in range(0, random.randrange(1, 10)):
            # try to log in a bunch of times
            response = self._login()
            self.assertContains(response, self.LOCKED_MESSAGE)

    def test_valid_login(self):
        """Tests a valid login for a real username
        """
        response = self._login(is_valid=True)
        self.assertNotContains(response, LOGIN_FORM_KEY, status_code=302)

    def test_valid_logout(self):
        """Tests a valid logout and make sure the logout_time is updated
        """
        response = self._login(is_valid=True)
        self.assertEquals(AccessLog.objects.latest('id').logout_time, None)

        response = self.client.get(reverse('admin:logout'))
        self.assertNotEquals(AccessLog.objects.latest('id').logout_time, None)
        self.assertContains(response, 'Logged out')

    def test_cooling_off(self):
        """Tests if the cooling time allows a user to login
        """
        self.test_failure_limit_once()

        # Wait for the cooling off period
        time.sleep(COOLOFF_TIME.total_seconds())

        # It should be possible to login again, make sure it is.
        self.test_valid_login()

    def test_cooling_off_for_trusted_user(self):
        """Test the cooling time for a trusted user
        """
        # Test successful login-logout, this makes the user trusted.
        self.test_valid_logout()

        # Try the cooling off time
        self.test_cooling_off()

    def test_long_user_agent_valid(self):
        """Tests if can handle a long user agent
        """
        long_user_agent = 'ie6' * 1024
        response = self._login(is_valid=True, user_agent=long_user_agent)
        self.assertNotContains(response, LOGIN_FORM_KEY, status_code=302)

    def test_long_user_agent_not_valid(self):
        """Tests if can handle a long user agent with failure
        """
        long_user_agent = 'ie6' * 1024
        for i in range(0, FAILURE_LIMIT + 1):
            response = self._login(user_agent=long_user_agent)

        self.assertContains(response, self.LOCKED_MESSAGE)

    def test_reset_ip(self):
        """Tests if can reset an ip address
        """
        # Make a lockout
        self.test_failure_limit_once()

        # Reset the ip so we can try again
        reset(ip='127.0.0.1')

        # Make a login attempt again
        self.test_valid_login()

    def test_reset_all(self):
        """Tests if can reset all attempts
        """
        # Make a lockout
        self.test_failure_limit_once()

        # Reset all attempts so we can try again
        reset()

        # Make a login attempt again
        self.test_valid_login()

########NEW FILE########
__FILENAME__ = test_settings
import os
import django

if django.VERSION[:2] >= (1, 3):
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': ':memory:',
        }
    }
else:
    DATABASE_ENGINE = 'sqlite3'

SITE_ID = 1

MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'axes.middleware.FailedLoginMiddleware'
)

ROOT_URLCONF = 'axes.test_urls'

INSTALLED_APPS = [
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.messages',
    'django.contrib.admin',

    'axes',
]

SECRET_KEY = 'too-secret-for-test'

LOGIN_REDIRECT_URL = '/admin'

AXES_LOGIN_FAILURE_LIMIT = 10
from datetime import timedelta
AXES_COOLOFF_TIME=timedelta(seconds = 2)


########NEW FILE########
__FILENAME__ = test_urls
from django.conf.urls import patterns, include
from django.contrib import admin

urlpatterns = patterns('',
    (r'^admin/', include(admin.site.urls)),
)
########NEW FILE########
__FILENAME__ = utils
from axes.models import AccessAttempt


def reset(ip=None, username=None):
    """Reset records that match ip or username, and
    return the count of removed attempts.
    """
    count = 0

    attempts = AccessAttempt.objects.all()
    if ip:
        attempts = attempts.filter(ip_address=ip)
    if username:
        attempts = attempts.filter(username=username)

    if attempts:
        count = attempts.count()
        attempts.delete()

    return count

########NEW FILE########
__FILENAME__ = views
# Create your views here.

########NEW FILE########
__FILENAME__ = axes_create_test_data
from __future__ import print_function

from django.core.management.base import BaseCommand

from django.contrib.auth.models import User

def create_admin_user(username, password):
    """
    Create a user for testing the admin.

    :param string username:
    :param strring password:
    """
    u = User()
    u.username = username
    u.email = '{0}@dev.mail.example.com'.format(username)
    u.is_superuser = True
    u.is_staff = True
    u.set_password(password)

    try:
        u.save()
        print("Created user {0} with password {1}.".format(username, password))
    except Exception as e:
        #print("Failed to create user {0} with password {1}. Reason: {2}".format(username, password, str(e)))
        pass

class Command(BaseCommand):
    def handle(self, *args, **options):
        """
        Creates test data.
        """
        try:
            create_admin_user('admin', 'test')
        except Exception as e:
            pass

        try:
            create_admin_user('test', 'test')
        except Exception as e:
            pass

########NEW FILE########
__FILENAME__ = models

########NEW FILE########
__FILENAME__ = manage
#!/usr/bin/env python
import os
import sys

if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings")

    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)

########NEW FILE########
__FILENAME__ = settings
# Django settings for example project.
import os
PROJECT_DIR = lambda base : os.path.abspath(os.path.join(os.path.dirname(__file__), base).replace('\\','/'))
gettext = lambda s: s

DEBUG = False
DEBUG_TOOLBAR = False
TEMPLATE_DEBUG = DEBUG

ADMINS = (
    # ('Your Name', 'your_email@example.com'),
)

MANAGERS = ADMINS

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3', # Add 'postgresql_psycopg2', 'mysql', 'sqlite3' or 'oracle'.
        'NAME': PROJECT_DIR('../db/example.db'),                      # Or path to database file if using sqlite3.
        # The following settings are not used with sqlite3:
        'USER': '',
        'PASSWORD': '',
        'HOST': '',                      # Empty for localhost through domain sockets or '127.0.0.1' for localhost through TCP.
        'PORT': '',                      # Set to empty string for default.
    }
}

# Hosts/domain names that are valid for this site; required if DEBUG is False
# See https://docs.djangoproject.com/en/1.5/ref/settings/#allowed-hosts
ALLOWED_HOSTS = []

# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
# In a Windows environment this must be set to your system time zone.
TIME_ZONE = 'America/Chicago'

# Language code for this installation. All choices can be found here:
# http://www.i18nguy.com/unicode/language-identifiers.html
#LANGUAGE_CODE = 'en-us'

SITE_ID = 1

# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = True

# If you set this to False, Django will not format dates, numbers and
# calendars according to the current locale.
USE_L10N = True

# If you set this to False, Django will not use timezone-aware datetimes.
USE_TZ = True

# Absolute filesystem path to the directory that will hold user-uploaded files.
# Example: "/var/www/example.com/media/"
MEDIA_ROOT = PROJECT_DIR(os.path.join('..', 'media'))

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash.
# Examples: "http://example.com/media/", "http://media.example.com/"
MEDIA_URL = '/media/'

# Absolute path to the directory static files should be collected to.
# Don't put anything in this directory yourself; store your static files
# in apps' "static/" subdirectories and in STATICFILES_DIRS.
# Example: "/var/www/example.com/static/"
STATIC_ROOT = PROJECT_DIR(os.path.join('..', 'static'))

# URL prefix for static files.
# Example: "http://example.com/static/", "http://static.example.com/"
STATIC_URL = '/static/'

# Additional locations of static files
STATICFILES_DIRS = (
    # Put strings here, like "/home/html/static" or "C:/www/django/static".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
    PROJECT_DIR(os.path.join('..', 'media', 'static')),
)

# List of finder classes that know how to find static files in
# various locations.
STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
#    'django.contrib.staticfiles.finders.DefaultStorageFinder',
)

# Make this unique, and don't share it with anybody.
SECRET_KEY = '6sf18c*w971i8a-m^1coasrmur2k6+q5_kyn*)s@(*_dk5q3&r'

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
    'django.template.loaders.eggs.Loader',
)

MIDDLEWARE_CLASSES = (
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    # Uncomment the next line for simple clickjacking protection:
    # 'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'axes.middleware.FailedLoginMiddleware'
)

ROOT_URLCONF = 'urls'

# Python dotted path to the WSGI application used by Django's runserver.
WSGI_APPLICATION = 'wsgi.application'

TEMPLATE_CONTEXT_PROCESSORS = (
    "django.contrib.auth.context_processors.auth",
    "django.core.context_processors.debug",
    "django.core.context_processors.i18n",
    "django.core.context_processors.media",
    "django.core.context_processors.static",
    "django.core.context_processors.tz",
    "django.contrib.messages.context_processors.messages",
    "django.core.context_processors.request"
)

TEMPLATE_DIRS = (
    # Put strings here, like "/home/html/django_templates" or "C:/www/django/templates".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
    PROJECT_DIR('templates')
)

INSTALLED_APPS = (
    # Django core and contrib apps
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.admin',
    'django.contrib.sitemaps',

    'axes',

    # Test app
    'foo',
)

LOGIN_REDIRECT_URL = '/admin'

# ******************** django-axes settings *********************
# Max number of login attemts within the ``AXES_COOLOFF_TIME``
AXES_LOGIN_FAILURE_LIMIT = 3

from datetime import timedelta
AXES_COOLOFF_TIME=timedelta(seconds = 200)
# ******************** /django-axes settings *********************

# A sample logging configuration. The only tangible logging
# performed by this configuration is to send an email to
# the site admins on every HTTP 500 error when DEBUG=False.
# See http://docs.djangoproject.com/en/dev/topics/logging for
# more details on how to customize your logging configuration.
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'filters': {
        'require_debug_false': {
            '()': 'django.utils.log.RequireDebugFalse'
        }
    },
    'formatters': {
        'verbose': {
            'format': '%(levelname)s %(asctime)s [%(pathname)s:%(lineno)s] %(message)s'
        },
        'simple': {
            'format': '%(levelname)s %(message)s'
        },
    },
    'handlers': {
        'mail_admins': {
            'level': 'ERROR',
            'filters': ['require_debug_false'],
            'class': 'django.utils.log.AdminEmailHandler'
        },
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'verbose'
        },
        'django_log': {
            'level':'DEBUG',
            'class':'logging.handlers.RotatingFileHandler',
            'filename': PROJECT_DIR("../logs/django.log"),
            'maxBytes': 1048576,
            'backupCount': 99,
            'formatter': 'verbose',
        },
        'axes_log': {
            'level':'DEBUG',
            'class':'logging.handlers.RotatingFileHandler',
            'filename': PROJECT_DIR("../logs/axes.log"),
            'maxBytes': 1048576,
            'backupCount': 99,
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['django_log'],
            'level': 'ERROR',
            'propagate': True,
        },
        'axes': {
            'handlers': ['console', 'axes_log'],
            'level': 'DEBUG',
            'propagate': True,
        },
    },
}

# Do not put any settings below this line
try:
    from local_settings import *
except:
    pass

if DEBUG and DEBUG_TOOLBAR:
    # debug_toolbar
    MIDDLEWARE_CLASSES += (
        'debug_toolbar.middleware.DebugToolbarMiddleware',
	)

    INSTALLED_APPS += (
        'debug_toolbar',
    )

    DEBUG_TOOLBAR_CONFIG = {
        'INTERCEPT_REDIRECTS': False,
    }

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls import patterns, include, url

from django.conf import settings
from django.contrib import admin
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
from django.conf.urls.static import static

admin.autodiscover()

urlpatterns = patterns('',
    # Uncomment the next line to enable the admin:
    url(r'^admin/', include(admin.site.urls)),
)

if settings.DEBUG:
    urlpatterns += staticfiles_urlpatterns()
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

########NEW FILE########
__FILENAME__ = wsgi
"""
WSGI config for example project.

This module contains the WSGI application used by Django's development server
and any production WSGI deployments. It should expose a module-level variable
named ``application``. Django's ``runserver`` and ``runfcgi`` commands discover
this application via the ``WSGI_APPLICATION`` setting.

Usually you will have the standard Django WSGI application here, but it also
might make sense to replace the whole Django WSGI application with a custom one
that later delegates to the Django one. For example, you could introduce WSGI
middleware here, or combine a Django application with an application of another
framework.

"""
import os

# We defer to a DJANGO_SETTINGS_MODULE already in the environment. This breaks
# if running multiple sites in the same mod_wsgi process. To fix this, use
# mod_wsgi daemon mode with each site in its own daemon process, or use
# os.environ["DJANGO_SETTINGS_MODULE"] = "example.settings"
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "example.settings")

# This application object is used by any WSGI server configured to use this
# file. This includes Django's development server, if the WSGI_APPLICATION
# setting points here.
from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()

# Apply WSGI middleware here.
# from helloworld.wsgi import HelloWorldApplication
# application = HelloWorldApplication(application)

########NEW FILE########
