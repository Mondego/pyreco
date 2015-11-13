__FILENAME__ = admin
from django.contrib import admin

from comics.accounts import models


class SubscriptionInline(admin.StackedInline):
    model = models.Subscription
    extra = 1


def email(obj):
    return obj.user.email


def subscription_count(obj):
    return obj.comics.count()


class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', email, 'secret_key', subscription_count)
    inlines = [SubscriptionInline]
    readonly_fields = ('user',)


admin.site.register(models.UserProfile, UserProfileAdmin)

########NEW FILE########
__FILENAME__ = backends
# Based on https://bitbucket.org/jokull/django-email-login/

import re
from uuid import uuid4

from django.contrib.auth.backends import ModelBackend
from django.contrib.auth.models import User
from django.contrib.sites.models import RequestSite, Site

from registration import signals
from registration.models import RegistrationProfile

from invitation.backends import InvitationBackend

from forms import RegistrationForm


class RegistrationBackend(InvitationBackend):
    """
    Does not require the user to pick a username. Sets the username to a random
    string behind the scenes.

    """

    def register(self, request, **kwargs):
        email, password = kwargs['email'], kwargs['password1']

        if Site._meta.installed:
            site = Site.objects.get_current()
        else:
            site = RequestSite(request)
        new_user = RegistrationProfile.objects.create_inactive_user(
            uuid4().get_hex()[:10], email, password, site)
        signals.user_registered.send(
            sender=self.__class__, user=new_user, request=request)
        return new_user

    def get_form_class(self, request):
        """
        Return the default form class used for user registration.

        """
        return RegistrationForm


email_re = re.compile(
    # dot-atom
    r"(^[-!#$%&'*+/=?^_`{}|~0-9A-Z]+(\.[-!#$%&'*+/=?^_`{}|~0-9A-Z]+)*"
    # quoted-string
    r'|^"([\001-\010\013\014\016-\037!#-\[\]-\177]|'
    r'\\[\001-\011\013\014\016-\177])*"'
    # domain
    r')@(?:[A-Z0-9-]+\.)+[A-Z]{2,6}$', re.IGNORECASE)


class AuthBackend(ModelBackend):
    """Authenticate using email only"""
    def authenticate(self, username=None, password=None, email=None):
        if email is None:
            email = username
        if email_re.search(email):
            user = User.objects.filter(email__iexact=email)
            if user.count() > 0:
                user = user[0]
                if user.check_password(password):
                    return user
        return None

########NEW FILE########
__FILENAME__ = forms
# Based on https://bitbucket.org/jokull/django-email-login/

from django.contrib.auth import authenticate
from django.contrib.auth import forms as auth_forms
from django.contrib.auth.models import User
from django import forms
from django.utils.translation import ugettext_lazy as _

attrs_dict = {'class': 'required'}


class RegistrationForm(forms.Form):
    email = forms.EmailField(
        widget=forms.TextInput(attrs=dict(attrs_dict, maxlength=75)),
        label=_("Email"))
    password1 = forms.CharField(
        widget=forms.PasswordInput(attrs=attrs_dict, render_value=False),
        label=_("Password"))
    password2 = forms.CharField(
        widget=forms.PasswordInput(attrs=attrs_dict, render_value=False),
        label=_("Password (again)"))

    def clean(self):
        """
        Verifiy that the values entered into the two password fields
        match. Note that an error here will end up in
        ``non_field_errors()`` because it doesn't apply to a single
        field.

        """
        if ('password1' in self.cleaned_data
                and 'password2' in self.cleaned_data):
            if (self.cleaned_data['password1'] !=
                    self.cleaned_data['password2']):
                raise forms.ValidationError(_(
                    "The two password fields didn't match."))
        return self.cleaned_data

    def clean_email(self):
        """
        Validate that the supplied email address is unique for the
        site.

        """
        if User.objects.filter(email__iexact=self.cleaned_data['email']):
            raise forms.ValidationError(_(
                "This email address is already in use. "
                "Please supply a different email address."))
        return self.cleaned_data['email']


class AuthenticationForm(forms.Form):
    """
    Base class for authenticating users. Extend this to get a form that accepts
    username/password logins.
    """
    email = forms.EmailField(label=_("Email"), max_length=75)
    password = forms.CharField(label=_("Password"), widget=forms.PasswordInput)

    def __init__(self, request=None, *args, **kwargs):
        """
        If request is passed in, the form will validate that cookies are
        enabled. Note that the request (a HttpRequest object) must have set a
        cookie with the key TEST_COOKIE_NAME and value TEST_COOKIE_VALUE before
        running this validation.
        """
        self.request = request
        self.user_cache = None
        super(AuthenticationForm, self).__init__(*args, **kwargs)

    def clean(self):
        email = self.cleaned_data.get('email')
        password = self.cleaned_data.get('password')

        if email and password:
            self.user_cache = authenticate(email=email, password=password)
            if self.user_cache is None:
                raise forms.ValidationError(_(
                    "Please enter a correct username and password. "
                    "Note that both fields are case-sensitive."))
            elif not self.user_cache.is_active:
                raise forms.ValidationError(_("This account is inactive."))

        return self.cleaned_data

    def get_user_id(self):
        if self.user_cache:
            return self.user_cache.id
        return None

    def get_user(self):
        return self.user_cache


class PasswordResetForm(auth_forms.PasswordResetForm):
    def __init__(self, *args, **kwargs):
        auth_forms.PasswordResetForm.__init__(self, *args, **kwargs)
        self.fields['email'].label = 'Email'

########NEW FILE########
__FILENAME__ = models
import uuid

from django.contrib.auth.models import User
from django.db import models
from django.dispatch import receiver

from comics.core.models import Comic


@receiver(models.signals.post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)


def make_secret_key():
    return uuid.uuid4().hex


class UserProfile(models.Model):
    user = models.OneToOneField(User, related_name='comics_profile')
    secret_key = models.CharField(
        max_length=32, blank=False, default=make_secret_key,
        help_text='Secret key for feed and API access')
    comics = models.ManyToManyField(Comic, through='Subscription')

    class Meta:
        db_table = 'comics_user_profile'
        verbose_name = 'comics profile'

    def __unicode__(self):
        return u'Comics profile for %s' % self.user.email

    def generate_new_secret_key(self):
        self.secret_key = make_secret_key()


class Subscription(models.Model):
    userprofile = models.ForeignKey(UserProfile)
    comic = models.ForeignKey(Comic)

    class Meta:
        db_table = 'comics_user_profile_comics'

    def __unicode__(self):
        return u'Subscription for %s to %s' % (
            self.userprofile.user.email, self.comic.slug)

########NEW FILE########
__FILENAME__ = tests
from django.contrib.auth.models import User
from django.test.client import Client
from django.test import TestCase


def create_user():
    return User.objects.create_user('alice', 'alice@example.com', 'secret')


class LoginTest(TestCase):
    def setUp(self):
        self.user = create_user()
        self.client = Client()

    def test_front_page_redirects_to_login_page(self):
        response = self.client.get('/')

        self.assertEquals(response.status_code, 302)
        self.assertEquals(
            response['Location'], 'http://testserver/account/login/?next=/')

    def test_login_page_includes_email_and_password_fields(self):
        response = self.client.get('/account/login/')

        self.assertEquals(response.status_code, 200)
        self.assertIn('Email', response.content)
        self.assertIn('Password', response.content)

    def test_successful_login_redirects_to_front_page(self):
        response = self.client.post(
            '/account/login/',
            {'email': 'alice@example.com', 'password': 'secret'})

        self.assertEquals(response.status_code, 302)
        self.assertEquals(response['Location'], 'http://testserver/')

    def test_failed_login_shows_error_on_login_page(self):
        response = self.client.post(
            '/account/login/',
            {'email': 'alice@example.com', 'password': 'wrong'})

        self.assertEquals(response.status_code, 200)
        self.assertIn(
            'Please enter a correct username and password.', response.content)

########NEW FILE########
__FILENAME__ = urls
from django.conf import settings
from django.conf.urls import patterns, url
from django.contrib.auth import views as auth_views
from django.views.generic.base import TemplateView

from invitation import views as invitation_views
from registration import views as reg_views

from comics.accounts.forms import (
    AuthenticationForm, PasswordResetForm, RegistrationForm)
from comics.accounts import views as account_views

urlpatterns = patterns(
    '',

    ### django-invitation

    url(r'^invite/complete/$',
        TemplateView.as_view(
            template_name='invitation/invitation_complete.html'),
        {
            'extra_context': {'active': {
                'invite': True,
            }},
        },
        name='invitation_complete'),
    url(r'^invite/$',
        invitation_views.invite,
        {
            'extra_context': {'active': {
                'invite': True,
            }},
        },
        name='invitation_invite'),
    url(r'^invited/(?P<invitation_key>\w+)/$',
        invitation_views.invited,
        {
            'extra_context': {'active': {'register': True}},
        },
        name='invitation_invited'),
    url(r'^register/$',
        invitation_views.register,
        {
            'backend': 'comics.accounts.backends.RegistrationBackend',
            'form_class': RegistrationForm,
            'extra_context': {'active': {'register': True}},
        },
        name='registration_register'),

    ### django-registration

    #url(r'^register/$',
    #    reg_views.register,
    #    {
    #        'backend': 'comics.accounts.backends.RegistrationBackend',
    #        'extra_context': {'active': {'register': True}},
    #    },
    #    name='registration_register'),
    url(r'^register/complete/$',
        TemplateView.as_view(
            template_name='registration/registration_complete.html'),
        name='registration_complete'),
    url(r'^register/closed/$',
        TemplateView.as_view(
            template_name='registration/registration_closed.html'),
        name='registration_disallowed'),

    url(r'^activate/complete/$',
        TemplateView.as_view(
            template_name='registration/activation_complete.html'),
        name='registration_activation_complete'),
    url(r'^activate/(?P<activation_key>\w+)/$',
        reg_views.activate,
        {'backend': 'comics.accounts.backends.RegistrationBackend'},
        name='registration_activate'),

    ### django.contrib.auth

    url(r'^login/$',
        auth_views.login,
        {
            'authentication_form': AuthenticationForm,
            'extra_context': {'active': {'login': True}},
            'template_name': 'auth/login.html',
        },
        name='login'),
    url(r'^logout/$',
        auth_views.logout,
        {'next_page': '/account/login/'},
        name='logout'),

    url(r'^password/change/$',
        auth_views.password_change,
        {
            'template_name': 'auth/password_change.html',
            'extra_context': {'active': {
                'account': True,
                'password_change': True,
            }},
        },
        name='password_change'),
    url(r'^password/change/done/$',
        auth_views.password_change_done,
        {'template_name': 'auth/password_change_done.html'},
        name='password_change_done'),

    url(r'^password/reset/$',
        auth_views.password_reset,
        {
            'template_name': 'auth/password_reset.html',
            'email_template_name': 'auth/password_reset_email.txt',
            'subject_template_name': 'auth/password_reset_email_subject.txt',
            'password_reset_form': PasswordResetForm,
        },
        name='password_reset'),
    url(r'^password/reset/confirm/(?P<uidb64>[0-9A-Za-z]+)-(?P<token>.+)/$',
        auth_views.password_reset_confirm,
        {'template_name': 'auth/password_reset_confirm.html'},
        name='password_reset_confirm'),
    url(r'^password/reset/complete/$',
        auth_views.password_reset_complete,
        {'template_name': 'auth/password_reset_complete.html'},
        name='password_reset_complete'),
    url(r'^password/reset/done/$',
        auth_views.password_reset_done,
        {'template_name': 'auth/password_reset_done.html'},
        name='password_reset_done'),

    ### comics.accounts

    url(r'^$',
        account_views.account_details, name='account'),

    url(r'^secret-key/$',
        account_views.secret_key, name='secret_key'),

    url(r'^toggle-comic/$',
        account_views.mycomics_toggle_comic, name='toggle_comic'),

    url(r'^edit-comics/$',
        account_views.mycomics_edit_comics, name='edit_comics'),
)

if 'comics.sets' in settings.INSTALLED_APPS:
    urlpatterns += patterns(
        '',
        url(r'^import-set/$',
            account_views.mycomics_import_named_set, name='import_named_set'),
    )

########NEW FILE########
__FILENAME__ = views
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.urlresolvers import reverse
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404, render

from comics.accounts.models import Subscription
from comics.core.models import Comic
from comics.sets.models import Set


@login_required
def account_details(request):
    return render(request, 'accounts/details.html', {
        'active': {
            'account': True,
            'account_details': True,
        }
    })


@login_required
def secret_key(request):
    """Show and generate a new secret key for the current user"""

    if request.method == 'POST':
        comics_profile = request.user.comics_profile
        comics_profile.generate_new_secret_key()
        comics_profile.save()
        messages.info(request, 'A new secret key was generated.')
        return HttpResponseRedirect(reverse('secret_key'))

    return render(request, 'accounts/secret_key.html', {
        'active': {
            'account': True,
            'secret_key': True,
        }
    })


@login_required
def mycomics_toggle_comic(request):
    """Change a single comic in My comics"""

    if request.method != 'POST':
        response = HttpResponse(status=405)
        response['Allowed'] = 'POST'
        return response

    comic = get_object_or_404(Comic, slug=request.POST['comic'])

    if 'add_comic' in request.POST:
        subscription = Subscription(
            userprofile=request.user.comics_profile, comic=comic)
        subscription.save()
        if not request.is_ajax():
            messages.info(request, 'Added "%s" to my comics' % comic.name)
    elif 'remove_comic' in request.POST:
        subscriptions = Subscription.objects.filter(
            userprofile=request.user.comics_profile, comic=comic)
        subscriptions.delete()
        if not request.is_ajax():
            messages.info(request, 'Removed "%s" from my comics' % comic.name)

    if request.is_ajax():
        return HttpResponse(status=204)
    else:
        return HttpResponseRedirect(reverse('mycomics_latest'))


@login_required
def mycomics_edit_comics(request):
    """Change multiple comics in My comics"""

    if request.method != 'POST':
        response = HttpResponse(status=405)
        response['Allowed'] = 'POST'
        return response

    my_comics = request.user.comics_profile.comics.all()

    for comic in my_comics:
        if comic.slug not in request.POST:
            subscriptions = Subscription.objects.filter(
                userprofile=request.user.comics_profile, comic=comic)
            subscriptions.delete()
            if not request.is_ajax():
                messages.info(
                    request, 'Removed "%s" from my comics' % comic.name)

    for comic in Comic.objects.all():
        if comic.slug in request.POST and comic not in my_comics:
            subscription = Subscription(
                userprofile=request.user.comics_profile, comic=comic)
            subscription.save()
            if not request.is_ajax():
                messages.info(request, 'Added "%s" to my comics' % comic.name)

    if request.is_ajax():
        return HttpResponse(status=204)
    elif 'HTTP_REFERER' in request.META:
        return HttpResponseRedirect(request.META['HTTP_REFERER'])
    else:
        return HttpResponseRedirect(reverse('mycomics_latest'))


@login_required
def mycomics_import_named_set(request):
    """Import comics from a named set into My comics"""

    if request.method == 'POST':
        try:
            named_set = Set.objects.get(name=request.POST['namedset'])
        except Set.DoesNotExist:
            messages.error(
                request,
                'No comic set named "%s" found.' % request.POST['namedset'])
            return HttpResponseRedirect(reverse('import_named_set'))

        count_before = len(request.user.comics_profile.comics.all())
        for comic in named_set.comics.all():
            Subscription.objects.get_or_create(
                userprofile=request.user.comics_profile,
                comic=comic)
        count_after = len(request.user.comics_profile.comics.all())
        count_added = count_after - count_before
        messages.info(
            request,
            '%d comic(s) was added to your comics selection.' % count_added)
        if count_added > 0:
            return HttpResponseRedirect(reverse('mycomics_latest'))
        else:
            return HttpResponseRedirect(reverse('import_named_set'))

    return render(request, 'sets/import_named_set.html', {
        'active': {
            'account': True,
            'import_named_set': True,
        }
    })

########NEW FILE########
__FILENAME__ = command
"""Aggregator which fetches comic releases from the web"""

import datetime
import logging
import socket

from comics.aggregator.downloader import ReleaseDownloader
from comics.core.exceptions import ComicsError
from comics.comics import get_comic_module

logger = logging.getLogger('comics.aggregator.command')
socket.setdefaulttimeout(10)


def log_errors(func):
    def inner(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except ComicsError, error:
            logger.info(error)
        except Exception, error:
            logger.exception(u'%s: %s', args[0].identifier, error)
    return inner


class Aggregator(object):
    def __init__(self, config=None, optparse_options=None):
        if config is None and optparse_options is not None:
            self.config = AggregatorConfig(optparse_options)
        else:
            assert isinstance(config, AggregatorConfig)
            self.config = config

    def start(self):
        start_time = datetime.datetime.now()
        for comic in self.config.comics:
            self.identifier = comic.slug
            self._aggregate_one_comic(comic)
        ellapsed_time = datetime.datetime.now() - start_time
        logger.info('Crawling completed in %s', ellapsed_time)

    def stop(self):
        pass

    @log_errors
    def _aggregate_one_comic(self, comic):
        crawler = self._get_crawler(comic)
        from_date = self._get_valid_date(crawler, self.config.from_date)
        to_date = self._get_valid_date(crawler, self.config.to_date)
        if from_date != to_date:
            logger.info(
                '%s: Crawling from %s to %s', comic.slug, from_date, to_date)
        pub_date = from_date
        while pub_date <= to_date:
            self.identifier = u'%s/%s' % (comic.slug, pub_date)
            crawler_release = self._crawl_one_comic_one_date(crawler, pub_date)
            if crawler_release:
                self._download_release(crawler_release)
            pub_date += datetime.timedelta(days=1)

    @log_errors
    def _crawl_one_comic_one_date(self, crawler, pub_date):
        logger.debug('Crawling %s for %s', crawler.comic.slug, pub_date)
        crawler_release = crawler.get_crawler_release(pub_date)
        if crawler_release:
            logger.debug('Release: %s', crawler_release.identifier)
            for image in crawler_release.images:
                logger.debug('Image URL: %s', image.url)
                logger.debug('Image title: %s', image.title)
                logger.debug('Image text: %s', image.text)
        return crawler_release

    @log_errors
    def _download_release(self, crawler_release):
        logger.debug('Downloading %s', crawler_release.identifier)
        downloader = self._get_downloader()
        downloader.download(crawler_release)
        logger.info('%s: Release saved', crawler_release.identifier)

    def _get_downloader(self):
        return ReleaseDownloader()

    def _get_crawler(self, comic):
        module = get_comic_module(comic.slug)
        return module.Crawler(comic)

    def _get_valid_date(self, crawler, date):
        if date is None:
            return crawler.current_date
        elif date < crawler.history_capable:
            logger.info(
                '%s: Adjusting date from %s to %s because of ' +
                'limited history capability',
                crawler.comic.slug, date, crawler.history_capable)
            return crawler.history_capable
        elif date > crawler.current_date:
            logger.info(
                '%s: Adjusting date from %s to %s because the given ' +
                "date is in the future in the comic's time zone",
                crawler.comic.slug, date, crawler.current_date)
            return crawler.current_date
        else:
            return date


class AggregatorConfig(object):
    DATE_FORMAT = '%Y-%m-%d'

    def __init__(self, options=None):
        self.comics = []
        self.from_date = None
        self.to_date = None
        if options is not None:
            self.setup(options)

    def setup(self, options):
        self.set_comics_to_crawl(options.get('comic_slugs', None))
        self.set_date_interval(
            options.get('from_date', None),
            options.get('to_date', None))

    def set_comics_to_crawl(self, comic_slugs):
        from comics.core.models import Comic
        if comic_slugs is None or len(comic_slugs) == 0:
            logger.debug('Crawl targets: all comics')
            self.comics = Comic.objects.all()
        else:
            comics = []
            for comic_slug in comic_slugs:
                comics.append(self._get_comic_by_slug(comic_slug))
            logger.debug('Crawl targets: %s' % comics)
            self.comics = comics

    def _get_comic_by_slug(self, comic_slug):
        from comics.core.models import Comic
        try:
            comic = Comic.objects.get(slug=comic_slug)
        except Comic.DoesNotExist:
            error_msg = 'Comic %s not found' % comic_slug
            logger.error(error_msg)
            raise ComicsError(error_msg)
        return comic

    def set_date_interval(self, from_date, to_date):
        self._set_from_date(from_date)
        self._set_to_date(to_date)
        self._validate_dates()

    def _set_from_date(self, from_date):
        if from_date is not None:
            self.from_date = datetime.datetime.strptime(
                str(from_date), self.DATE_FORMAT).date()
        logger.debug('From date: %s', self.from_date)

    def _set_to_date(self, to_date):
        if to_date is not None:
            self.to_date = datetime.datetime.strptime(
                str(to_date), self.DATE_FORMAT).date()
        logger.debug('To date: %s', self.to_date)

    def _validate_dates(self):
        if self.from_date and self.to_date and self.from_date > self.to_date:
            error_msg = 'From date (%s) after to date (%s)' % (
                self.from_date, self.to_date)
            logger.error(error_msg)
            raise ComicsError(error_msg)
        else:
            return True

########NEW FILE########
__FILENAME__ = crawler
import datetime
import httplib
import socket
import time
import urllib2
import xml.sax._exceptions

import pytz

from django.utils import timezone

from comics.aggregator.exceptions import (
    CrawlerHTTPError, ImageURLNotFound, NotHistoryCapable,
    ReleaseAlreadyExists)
from comics.aggregator.feedparser import FeedParser
from comics.aggregator.lxmlparser import LxmlParser

# For testability
now = timezone.now
today = datetime.date.today


class CrawlerRelease(object):
    def __init__(self, comic, pub_date, has_rerun_releases=False):
        self.comic = comic
        self.pub_date = pub_date
        self.has_rerun_releases = has_rerun_releases
        self._images = []

    @property
    def identifier(self):
        return u'%s/%s' % (self.comic.slug, self.pub_date)

    @property
    def images(self):
        return self._images

    def add_image(self, image):
        image.validate(self.identifier)
        self._images.append(image)


class CrawlerImage(object):
    def __init__(self, url, title=None, text=None, headers=None):
        self.url = url
        self.title = title
        self.text = text
        self.request_headers = headers or {}

        # Convert from e.g. lxml.etree._ElementUnicodeResult to unicode
        if self.title is not None and type(self.title) != unicode:
            self.title = unicode(self.title)
        if self.text is not None and type(self.text) != unicode:
            self.text = unicode(self.text)

    def validate(self, identifier):
        if not self.url:
            raise ImageURLNotFound(identifier)


class CrawlerBase(object):
    ### Crawler settings
    # Date of oldest release available for crawling
    history_capable_date = None
    # Number of days a release is available for crawling
    history_capable_days = None
    # On what weekdays the comic is published (example: "Mo,We,Fr")
    schedule = None
    # In approximately what time zone the comic is published
    # (example: "Europe/Oslo")
    time_zone = 'UTC'
    # Whether to allow multiple releases per day
    multiple_releases_per_day = False

    ### Downloader settings
    # Whether the comic reruns old images as new releases
    has_rerun_releases = False

    ### Settings used for both crawling and downloading
    # Dictionary of HTTP headers to send when retrieving items from the site
    headers = {}

    # Feed object which is reused when crawling multiple dates
    feed = None

    # Page objects mapped against URL for use when crawling multiple dates
    pages = {}

    def __init__(self, comic):
        self.comic = comic

    def get_crawler_release(self, pub_date=None):
        """Get meta data for release at pub_date, or the latest release"""

        pub_date = self._get_date_to_crawl(pub_date)
        release = CrawlerRelease(
            self.comic, pub_date, has_rerun_releases=self.has_rerun_releases)

        try:
            results = self.crawl(pub_date)
        except urllib2.HTTPError as error:
            raise CrawlerHTTPError(release.identifier, error.code)
        except urllib2.URLError as error:
            raise CrawlerHTTPError(release.identifier, error.reason)
        except httplib.BadStatusLine:
            raise CrawlerHTTPError(release.identifier, 'BadStatusLine')
        except socket.error as error:
            raise CrawlerHTTPError(release.identifier, error)
        except xml.sax._exceptions.SAXException as error:
            raise CrawlerHTTPError(release.identifier, str(error))

        if not results:
            return

        if not hasattr(results, '__iter__'):
            results = [results]

        for result in results:
            # Use HTTP headers when requesting images
            result.request_headers.update(self.headers)
            release.add_image(result)

        return release

    def _get_date_to_crawl(self, pub_date):
        identifier = u'%s/%s' % (self.comic.slug, pub_date)

        if pub_date is None:
            pub_date = self.current_date

        if pub_date < self.history_capable:
            raise NotHistoryCapable(identifier, self.history_capable)

        if self.multiple_releases_per_day is False:
            if self.comic.release_set.filter(pub_date=pub_date).count() > 0:
                raise ReleaseAlreadyExists(identifier)

        return pub_date

    @property
    def current_date(self):
        tz = pytz.timezone(self.time_zone)
        now_in_tz = tz.normalize(now().astimezone(tz))
        return now_in_tz.date()

    @property
    def history_capable(self):
        if self.history_capable_date is not None:
            return datetime.datetime.strptime(
                self.history_capable_date, '%Y-%m-%d').date()
        elif self.history_capable_days is not None:
            return (today() - datetime.timedelta(self.history_capable_days))
        else:
            return today()

    def crawl(self, pub_date):
        """
        Must be overridden by all crawlers

        Input:
            pub_date -- a datetime.date object for the date to crawl

        Output:
            on success: a CrawlResult object containing:
                - at least an image URL
                - optionally a title and/or a text
            on failure: None
        """

        raise NotImplementedError

    ### Helpers for the crawl() implementations

    def parse_feed(self, feed_url):
        if self.feed is None:
            self.feed = FeedParser(feed_url)
        return self.feed

    def parse_page(self, page_url):
        if page_url not in self.pages:
            self.pages[page_url] = LxmlParser(page_url, headers=self.headers)
        return self.pages[page_url]

    def string_to_date(self, *args, **kwargs):
        return datetime.datetime.strptime(*args, **kwargs).date()

    def date_to_epoch(self, date):
        """The UNIX time of midnight at ``date`` in the comic's time zone"""
        naive_midnight = datetime.datetime(date.year, date.month, date.day)
        local_midnight = pytz.timezone(self.time_zone).localize(naive_midnight)
        return int(time.mktime(local_midnight.utctimetuple()))


class ArcaMaxCrawlerBase(CrawlerBase):
    """Base comic crawler for all comics hosted at arcamax.com"""

    def crawl_helper(self, slug, pub_date):
        page_url = 'http://www.arcamax.com/thefunnies/%s/' % slug
        page = self.parse_page(page_url)
        date_str = page.text('span.cur')
        date = datetime.datetime.strptime(date_str, '%B %d, %Y').date()
        if date != pub_date:
            return
        url = page.src('.comic img')
        return CrawlerImage(url)


class GoComicsComCrawlerBase(CrawlerBase):
    """Base comic crawler for all comics hosted at gocomics.com"""

    # It doesn't want us getting comics because of a User-Agent check.
    # Look! I'm a nice, normal Internet Explorer machine!
    headers = {
        'User-Agent': (
            'Mozilla/4.0 (compatible; MSIE 8.0; Windows NT 5.1; '
            'Trident/4.0; .NET CLR 1.1.4322; .NET CLR 2.0.50727; '
            '.NET CLR 3.0.4506.2152; .NET CLR 3.5.30729'),
    }

    def crawl_helper(self, short_name, pub_date, url_name=None):
        if url_name is None:
            url_name = short_name
        page_url = 'http://www.gocomics.com/%s/%s' % (
            url_name.lower().replace(' ', ''), pub_date.strftime('%Y/%m/%d/'))
        page = self.parse_page(page_url)
        url = page.src('img.strip[alt="%s"]' % short_name)
        return CrawlerImage(url)


class PondusNoCrawlerBase(CrawlerBase):
    """Base comics crawling for all comics posted at pondus.no"""

    time_zone = 'Europe/Oslo'

    def crawl_helper(self, url_id):
        page_url = 'http://www.pondus.no/?section=artikkel&id=%s' % url_id
        page = self.parse_page(page_url)
        url = page.src('.imagegallery img')
        return CrawlerImage(url)

########NEW FILE########
__FILENAME__ = downloader
import contextlib
import hashlib
import httplib
import socket
import tempfile
import urllib2

try:
    from PIL import Image as PILImage
except ImportError:
    import Image as PILImage  # noqa

from django.conf import settings
from django.core.files import File
from django.db import transaction

from comics.aggregator.exceptions import (
    DownloaderHTTPError, ImageTypeError, ImageIsCorrupt, ImageAlreadyExists,
    ImageIsBlacklisted)
from comics.core.models import Release, Image


# Image types we accept, and the file extension they are saved with
IMAGE_FORMATS = {
    'GIF': '.gif',
    'JPEG': '.jpg',
    'PNG': '.png',
}


class ReleaseDownloader(object):
    def download(self, crawler_release):
        images = self._download_images(crawler_release)
        return self._create_new_release(
            crawler_release.comic, crawler_release.pub_date, images)

    def _download_images(self, crawler_release):
        image_downloader = ImageDownloader(crawler_release)
        return map(image_downloader.download, crawler_release.images)

    @transaction.atomic
    def _create_new_release(self, comic, pub_date, images):
        release = Release(comic=comic, pub_date=pub_date)
        release.save()
        for image in images:
            release.images.add(image)
        return release


class ImageDownloader(object):
    def __init__(self, crawler_release):
        self.crawler_release = crawler_release

    def download(self, crawler_image):
        self.identifier = self.crawler_release.identifier

        with self._download_image(
                crawler_image.url, crawler_image.request_headers
                ) as image_file:
            checksum = self._get_sha256sum(image_file)
            self.identifier = '%s/%s' % (self.identifier, checksum[:6])

            self._check_if_blacklisted(checksum)

            existing_image = self._get_existing_image(
                comic=self.crawler_release.comic,
                has_rerun_releases=self.crawler_release.has_rerun_releases,
                checksum=checksum)
            if existing_image is not None:
                return existing_image

            image = self._validate_image(image_file)

            file_extension = self._get_file_extension(image)
            file_name = self._get_file_name(checksum, file_extension)

            return self._create_new_image(
                comic=self.crawler_release.comic,
                title=crawler_image.title,
                text=crawler_image.text,
                image_file=image_file,
                file_name=file_name,
                checksum=checksum)

    def _download_image(self, url, request_headers):
        try:
            request = urllib2.Request(url, None, request_headers)
            with contextlib.closing(urllib2.urlopen(request)) as http_file:
                temp_file = tempfile.NamedTemporaryFile(suffix='comics')
                temp_file.write(http_file.read())
                temp_file.seek(0)
                return temp_file
        except urllib2.HTTPError as error:
            raise DownloaderHTTPError(self.identifier, error.code)
        except urllib2.URLError as error:
            raise DownloaderHTTPError(self.identifier, error.reason)
        except httplib.BadStatusLine:
            raise DownloaderHTTPError(self.identifier, 'BadStatusLine')
        except socket.error as error:
            raise DownloaderHTTPError(self.identifier, error)

    def _get_sha256sum(self, file_handle):
        original_position = file_handle.tell()
        hash = hashlib.sha256()
        while True:
            data = file_handle.read(8096)
            if not data:
                break
            hash.update(data)
        file_handle.seek(original_position)
        return hash.hexdigest()

    def _check_if_blacklisted(self, checksum):
        if checksum in settings.COMICS_IMAGE_BLACKLIST:
            raise ImageIsBlacklisted(self.identifier)

    def _get_existing_image(self, comic, has_rerun_releases, checksum):
        try:
            image = Image.objects.get(comic=comic, checksum=checksum)
            if image is not None and not has_rerun_releases:
                raise ImageAlreadyExists(self.identifier)
            return image
        except Image.DoesNotExist:
            return None

    def _validate_image(self, image_file):
        try:
            image = PILImage.open(image_file)
            image.load()
            return image
        except IndexError:
            raise ImageIsCorrupt(self.identifier)
        except IOError as error:
            raise ImageIsCorrupt(self.identifier, error.message)

    def _get_file_extension(self, image):
        if image.format not in IMAGE_FORMATS:
            raise ImageTypeError(self.identifier, image.format)
        return IMAGE_FORMATS[image.format]

    def _get_file_name(self, checksum, extension):
        if checksum and extension:
            return '%s%s' % (checksum, extension)

    @transaction.atomic
    def _create_new_image(
            self, comic, title, text, image_file, file_name, checksum):
        image = Image(comic=comic, checksum=checksum)
        image.file.save(file_name, File(image_file))
        if title is not None:
            image.title = title
        if text is not None:
            image.text = text
        image.save()
        return image

########NEW FILE########
__FILENAME__ = exceptions
from comics.core.exceptions import ComicsError


class AggregatorError(ComicsError):
    """base class for aggregator exceptions"""

    def __init__(self, identifier, value=None):
        self.identifier = identifier
        self.value = value

    def __str__(self):
        return '%s: Generic aggregator error' % self.identifier


###


class CrawlerError(AggregatorError):
    """Base class for crawler exceptions"""

    def __str__(self):
        return '%s: Generic crawler error (%s)' % (self.identifier, self.value)


class CrawlerHTTPError(CrawlerError):
    """Exception used to wrap urllib2.HTTPError from the crawler"""

    def __str__(self):
        return '%s: Crawler HTTP Error (%s)' % (
            self.identifier, self.value)


class ImageURLNotFound(CrawlerError):
    """Exception raised when no URL is found by the crawler"""

    def __str__(self):
        return '%s: Image URL not found' % self.identifier


class NotHistoryCapable(CrawlerError):
    """Exception raised when a comic is not history capable for the date"""

    def __str__(self):
        return '%s: Comic is not history capable (%s)' % (
            self.identifier, self.value)


class ReleaseAlreadyExists(CrawlerError):
    """Exception raised when crawling a release that already exists"""

    def __str__(self):
        return '%s: Release already exists' % self.identifier


###


class DownloaderError(AggregatorError):
    """Base class for downloader exceptions"""

    def __str__(self):
        return '%s: Generic downloader error (%s)' % (
            self.identifier, self.value)


class DownloaderHTTPError(DownloaderError):
    """Exception used to wrap urllib2.HTTPError from the downloader"""

    def __str__(self):
        return '%s: Downloader HTTP Error (%s)' % (
            self.identifier, self.value)


class ImageTypeError(DownloaderError):
    """Exception raised when the image isn't of the right type"""

    def __str__(self):
        return '%s: Invalid image type (%s)' % (self.identifier, self.value)


class ImageIsCorrupt(DownloaderError):
    """Exception raised when the fetched image is corrupt"""

    def __str__(self):
        return '%s: Image is corrupt (%s)' % (self.identifier, self.value)


class ImageAlreadyExists(DownloaderError):
    """Exception raised when trying to save an image that already exists"""

    def __str__(self):
        return '%s: Image already exists' % self.identifier


class ImageIsBlacklisted(DownloaderError):
    """Exception raised when a blacklisted image has been downloaded"""

    def __str__(self):
        return '%s: Image is blacklisted' % self.identifier

########NEW FILE########
__FILENAME__ = feedparser
from __future__ import absolute_import

import datetime
import feedparser
import warnings

from comics.aggregator.lxmlparser import LxmlParser


class FeedParser(object):
    def __init__(self, url):
        self.raw_feed = feedparser.parse(url)
        self.encoding = None
        if hasattr(self.raw_feed, 'encoding') and self.raw_feed.encoding:
            self.encoding = self.raw_feed.encoding

    def for_date(self, date):
        with warnings.catch_warnings():
            # feedparser 5.1.2 issues a warning whenever we use updated_parsed
            warnings.simplefilter('ignore')
            return [
                Entry(e, self.encoding) for e in self.raw_feed.entries
                if (hasattr(e, 'published_parsed') and e.published_parsed and
                    datetime.date(*e.published_parsed[:3]) == date)
                or (hasattr(e, 'updated_parsed') and e.updated_parsed and
                    datetime.date(*e.updated_parsed[:3]) == date)
            ]

    def all(self):
        return [Entry(e, self.encoding) for e in self.raw_feed.entries]


class Entry(object):
    def __init__(self, entry, encoding=None):
        self.raw_entry = entry
        self.encoding = encoding
        if 'summary' in entry:
            self.summary = self.html(entry.summary)
        if 'content' in entry:
            self.content0 = self.html(entry.content[0].value)

    def __getattr__(self, name):
        attr = getattr(self.raw_entry, name)
        if isinstance(attr, str) and self.encoding is not None:
            attr = attr.decode(self.encoding)
        return attr

    def html(self, string):
        if isinstance(string, str) and self.encoding is not None:
            string = string.decode(self.encoding)
        return LxmlParser(string=string)

    @property
    def tags(self):
        if not 'tags' in self.raw_entry:
            return []
        return [tag.term for tag in self.raw_entry.tags]

########NEW FILE########
__FILENAME__ = lxmlparser
from lxml.html import fromstring
import urllib2

from comics.aggregator.exceptions import CrawlerError


class LxmlParser(object):
    def __init__(self, url=None, string=None, headers=None):
        self._retrieved_url = None

        if url is not None:
            self.root = self._parse_url(url, headers)
        elif string is not None:
            self.root = self._parse_string(string)
        else:
            raise LxmlParserException(
                'Parser needs URL or string to operate on')

    def href(self, selector, default=None, allow_multiple=False):
        return self._get('href', selector, default, allow_multiple)

    def src(self, selector, default=None, allow_multiple=False):
        return self._get('src', selector, default, allow_multiple)

    def alt(self, selector, default=None, allow_multiple=False):
        return self._get('alt', selector, default, allow_multiple)

    def title(self, selector, default=None, allow_multiple=False):
        return self._get('title', selector, default, allow_multiple)

    def value(self, selector, default=None, allow_multiple=False):
        return self._get('value', selector, default, allow_multiple)

    def id(self, selector, default=None, allow_multiple=False):
        return self._get('id', selector, default, allow_multiple)

    def text(self, selector, default=None, allow_multiple=False):
        try:
            if allow_multiple:
                build_results = []
                for match in self._select(selector, allow_multiple):
                    build_results.append(self._decode(match.text_content()))
                return build_results
            else:
                return self._decode(self._select(selector).text_content())
        except DoesNotExist:
            if allow_multiple and default is None:
                return []
            return default

    def remove(self, selector):
        for element in self.root.cssselect(selector):
            element.drop_tree()

    def url(self):
        return self._retrieved_url

    def _get(self, attr, selector, default=None, allow_multiple=False):
        try:
            if allow_multiple:
                build_results = []
                for match in self._select(selector, allow_multiple):
                    build_results.append(self._decode(match).get(attr))
                return build_results
            else:
                return self._decode(self._select(selector).get(attr))
        except DoesNotExist:
            if allow_multiple and default is None:
                return []
            return default

    def _select(self, selector, allow_multiple=False):
        elements = self.root.cssselect(selector)

        if len(elements) == 0:
            raise DoesNotExist('Nothing matched the selector: %s' % selector)
        elif len(elements) > 1 and not allow_multiple:
            raise MultipleElementsReturned(
                'Selector matched %d elements: %s' % (len(elements), selector))

        if allow_multiple:
            return elements
        else:
            return elements[0]

    def _parse_url(self, url, headers=None):
        if headers is None:
            handle = urllib2.urlopen(url)
        else:
            request = urllib2.Request(url, headers=headers)
            handle = urllib2.urlopen(request)
        content = handle.read()
        self._retrieved_url = handle.geturl()
        handle.close()
        content = content.replace('\x00', '')
        root = self._parse_string(content)
        root.make_links_absolute(self._retrieved_url)
        return root

    def _parse_string(self, string):
        if len(string.strip()) == 0:
            string = '<xml />'
        return fromstring(string)

    def _decode(self, string):
        if isinstance(string, str):
            try:
                string = string.decode('utf-8')
            except UnicodeDecodeError:
                string = string.decode('iso-8859-1')
        return string


class LxmlParserException(CrawlerError):
    pass


class DoesNotExist(LxmlParserException):
    pass


class MultipleElementsReturned(LxmlParserException):
    pass

########NEW FILE########
__FILENAME__ = comics_getreleases
from comics.aggregator.command import Aggregator
from comics.core.command_utils import ComicsBaseCommand, make_option


class Command(ComicsBaseCommand):
    option_list = ComicsBaseCommand.option_list + (
        make_option(
            '-c', '--comic',
            action='append', dest='comic_slugs', metavar='COMIC',
            help='Comic to crawl, repeat for multiple [default: all]'),
        make_option(
            '-f', '--from-date',
            dest='from_date', metavar='DATE', default=None,
            help='First date to crawl [default: today]'),
        make_option(
            '-t', '--to-date',
            dest='to_date', metavar='DATE', default=None,
            help='Last date to crawl [default: today]'),
    )

    def handle(self, *args, **options):
        super(Command, self).handle(*args, **options)
        aggregator = Aggregator(optparse_options=options)
        try:
            aggregator.start()
        except KeyboardInterrupt:
            aggregator.stop()

########NEW FILE########
__FILENAME__ = models
# Empty file which tricks Django into accepting this as a Django app and
# thus makes Django able to run the tests.

########NEW FILE########
__FILENAME__ = test_command
import datetime
import mock

from django.test import TestCase

from comics.aggregator import command
from comics.aggregator.crawler import CrawlerRelease
from comics.aggregator.exceptions import ComicsError
from comics.core.models import Comic


def create_comics():
    Comic.objects.create(slug='xkcd')
    Comic.objects.create(slug='sinfest')


class AggregatorConfigTestCase(TestCase):
    def setUp(self):
        create_comics()
        self.cc = command.AggregatorConfig()

    def test_init(self):
        self.assertEquals(0, len(self.cc.comics))
        self.assertEquals(None, self.cc.from_date)
        self.assertEquals(None, self.cc.to_date)

    def test_init_invalid(self):
        self.assertRaises(
            AttributeError, command.AggregatorConfig, options=True)

    def test_set_from_date(self):
        from_date = datetime.date(2008, 3, 11)
        self.cc._set_from_date(from_date)
        self.assertEquals(from_date, self.cc.from_date)

    def test_set_from_date_from_string(self):
        from_date = datetime.date(2008, 3, 11)
        self.cc._set_from_date(str(from_date))
        self.assertEquals(from_date, self.cc.from_date)

    def test_set_to_date(self):
        to_date = datetime.date(2008, 3, 11)
        self.cc._set_to_date(to_date)
        self.assertEquals(to_date, self.cc.to_date)

    def test_set_to_date_from_string(self):
        to_date = datetime.date(2008, 3, 11)
        self.cc._set_to_date(str(to_date))
        self.assertEquals(to_date, self.cc.to_date)

    def test_validate_dates_valid(self):
        self.cc.from_date = datetime.date(2008, 3, 11)
        self.cc.to_date = datetime.date(2008, 3, 11)
        self.assertTrue(self.cc._validate_dates())

        self.cc.from_date = datetime.date(2008, 2, 29)
        self.cc.to_date = datetime.date(2008, 3, 2)
        self.assertTrue(self.cc._validate_dates())

    def test_validate_dates_invalid(self):
        self.cc.from_date = datetime.date(2008, 3, 11)
        self.cc.to_date = datetime.date(2008, 3, 10)
        self.assertRaises(ComicsError, self.cc._validate_dates)

    def test_get_comic_by_slug_valid(self):
        expected = Comic.objects.get(slug='xkcd')
        result = self.cc._get_comic_by_slug('xkcd')
        self.assertEquals(expected, result)

    def test_get_comic_by_slug_invalid(self):
        self.assertRaises(ComicsError, self.cc._get_comic_by_slug, 'not slug')

    def test_set_comics_to_crawl_two(self):
        comic1 = Comic.objects.get(slug='xkcd')
        comic2 = Comic.objects.get(slug='sinfest')
        self.cc.set_comics_to_crawl(['xkcd', 'sinfest'])
        self.assertEquals(2, len(self.cc.comics))
        self.assert_(comic1 in self.cc.comics)
        self.assert_(comic2 in self.cc.comics)

    def test_set_comics_to_crawl_all(self):
        all_count = Comic.objects.count()

        self.cc.set_comics_to_crawl(None)
        self.assertEquals(all_count, len(self.cc.comics))

        self.cc.set_comics_to_crawl([])
        self.assertEquals(all_count, len(self.cc.comics))


class ComicAggregatorTestCase(TestCase):
    def setUp(self):
        create_comics()
        config = command.AggregatorConfig()
        config.set_comics_to_crawl(None)
        self.aggregator = command.Aggregator(config)
        self.aggregator.identifier = 'slug'

        self.comic = mock.Mock()
        self.comic.slug = 'slug'
        self.crawler_mock = mock.Mock()
        self.crawler_mock.comic = self.comic
        self.downloader_mock = mock.Mock()

    def test_init(self):
        self.assertIsInstance(self.aggregator.config, command.AggregatorConfig)

    def test_init_optparse_config(self):
        optparse_options_mock = mock.Mock()
        optparse_options_mock.comic_slugs = None
        optparse_options_mock.from_date = None
        optparse_options_mock.to_date = None
        optparse_options_mock.get.return_value = None

        result = command.Aggregator(optparse_options=optparse_options_mock)

        self.assertEquals(
            len(self.aggregator.config.comics), len(result.config.comics))
        self.assertEquals(
            self.aggregator.config.from_date, result.config.from_date)
        self.assertEquals(
            self.aggregator.config.to_date, result.config.to_date)

    def test_init_invalid_config(self):
        self.assertRaises(AssertionError, command.Aggregator)

    def test_crawl_one_comic_one_date(self):
        pub_date = datetime.date(2008, 3, 1)
        crawler_release = CrawlerRelease(self.comic, pub_date)
        self.crawler_mock.get_crawler_release.return_value = crawler_release

        self.aggregator._crawl_one_comic_one_date(
            self.crawler_mock, pub_date)

        self.assertEqual(1, self.crawler_mock.get_crawler_release.call_count)
        self.crawler_mock.get_crawler_release.assert_called_with(pub_date)

    def test_download_release(self):
        crawler_release = CrawlerRelease(self.comic, datetime.date(2008, 3, 1))
        self.aggregator._get_downloader = lambda: self.downloader_mock

        self.aggregator._download_release(crawler_release)

        self.assertEqual(1, self.downloader_mock.download.call_count)
        self.downloader_mock.download.assert_called_with(crawler_release)

    def test_get_valid_date_from_history_capable(self):
        expected = datetime.date(2008, 3, 1)
        self.crawler_mock.comic = Comic.objects.get(slug='xkcd')
        self.crawler_mock.history_capable = expected
        self.crawler_mock.current_date = datetime.date(2008, 4, 1)

        result = self.aggregator._get_valid_date(
            self.crawler_mock, datetime.date(2008, 2, 1))

        self.assertEquals(expected, result)

    def test_get_valid_date_from_config(self):
        expected = datetime.date(2008, 3, 1)
        self.crawler_mock.comic = Comic.objects.get(slug='xkcd')
        self.crawler_mock.history_capable = datetime.date(2008, 1, 1)
        self.crawler_mock.current_date = datetime.date(2008, 4, 1)

        result = self.aggregator._get_valid_date(
            self.crawler_mock, expected)

        self.assertEquals(expected, result)

    def test_get_crawler(self):
        pass  # TODO

    def test_get_downloader(self):
        pass  # TODO

    def test_aggregate_one_comic(self):
        pass  # TODO

    def test_start(self):
        pass  # TODO

########NEW FILE########
__FILENAME__ = test_crawler
import datetime

import pytz

from django.utils import unittest

from comics.aggregator import crawler


class CurrentDateWhenLocalTZIsUTCTest(unittest.TestCase):
    time_zone_local = 'UTC'
    time_zone_ahead = 'Australia/Sydney'
    time_zone_behind = 'America/New_York'

    def setUp(self):
        self.tz = pytz.timezone(self.time_zone_local)
        self.crawler = crawler.CrawlerBase(None)
        crawler.now = lambda: self.now
        crawler.today = lambda: self.now.today()

    def test_current_date_when_crawler_is_in_local_today(self):
        self.now = self.tz.localize(datetime.datetime(2001, 2, 5, 23, 1, 0))
        self.crawler.time_zone = self.time_zone_local

        today = datetime.date(2001, 2, 5)
        self.assertEqual(self.crawler.current_date, today)

    def test_current_date_when_crawler_is_in_local_tomorrow(self):
        self.now = self.tz.localize(datetime.datetime(2001, 2, 5, 23, 1, 0))
        self.crawler.time_zone = self.time_zone_ahead

        tomorrow = datetime.date(2001, 2, 6)
        self.assertEqual(self.crawler.current_date, tomorrow)

    def test_current_date_when_crawler_is_in_local_yesterday(self):
        self.now = self.tz.localize(datetime.datetime(2001, 2, 5, 0, 59, 0))
        self.crawler.time_zone = self.time_zone_behind

        yesterday = datetime.date(2001, 2, 4)
        self.assertEqual(self.crawler.current_date, yesterday)


class CurrentDateWhenLocalTZIsCETTest(CurrentDateWhenLocalTZIsUTCTest):
    time_zone_local = 'Europe/Oslo'
    time_zone_ahead = 'Australia/Sydney'
    time_zone_behind = 'America/New_York'


class CurrentDateWhenLocalTZIsESTTest(CurrentDateWhenLocalTZIsUTCTest):
    time_zone_local = 'America/New_York'
    time_zone_ahead = 'Europe/Moscow'
    time_zone_behind = 'America/Los_Angeles'

########NEW FILE########
__FILENAME__ = utils
from comics.comics import get_comic_module

SCHEDULE_DAYS = ['Su', 'Mo', 'Tu', 'We', 'Th', 'Fr', 'Sa']


def get_comic_schedule(comic):
    module = get_comic_module(comic.slug)
    schedule = module.Crawler(comic).schedule

    if not schedule:
        return []
    return [SCHEDULE_DAYS.index(day) for day in schedule.split(',')]

########NEW FILE########
__FILENAME__ = authentication
from django.contrib.auth.models import User

from tastypie.authentication import Authentication
from tastypie.http import HttpUnauthorized


class SecretKeyAuthentication(Authentication):
    def extract_credentials(self, request):
        if request.META.get('HTTP_AUTHORIZATION', '').lower().startswith(
                'key '):
            (auth_type, secret_key) = (
                request.META['HTTP_AUTHORIZATION'].split())

            if auth_type.lower() != 'key':
                raise ValueError("Incorrect authorization header.")
        else:
            secret_key = request.GET.get('key') or request.POST.get('key')

        return secret_key

    def is_authenticated(self, request, **kwargs):
        try:
            secret_key = self.extract_credentials(request)
        except ValueError:
            return HttpUnauthorized()

        if not secret_key:
            return HttpUnauthorized()

        try:
            user = User.objects.get(
                comics_profile__secret_key=secret_key, is_active=True)
        except (User.DoesNotExist, User.MultipleObjectsReturned):
            return HttpUnauthorized()

        request.user = user
        return True

    def get_identifier(self, request):
        return self.extract_credentials(request)


class MultiAuthentication(object):
    """
    An authentication backend that tries a number of backends in order.

    This class have been copied from the Tastypie source code. It can hopefully
    be removed with the release of Tastypie 0.9.12.
    """
    def __init__(self, *backends, **kwargs):
        super(MultiAuthentication, self).__init__(**kwargs)
        self.backends = backends

    def is_authenticated(self, request, **kwargs):
        """
        Identifies if the user is authenticated to continue or not.

        Should return either ``True`` if allowed, ``False`` if not or an
        ``HttpResponse`` if you need something custom.
        """
        unauthorized = False

        for backend in self.backends:
            check = backend.is_authenticated(request, **kwargs)

            if check:
                if isinstance(check, HttpUnauthorized):
                    unauthorized = unauthorized or check
                else:
                    request._authentication_backend = backend
                    return check

        return unauthorized

    def get_identifier(self, request):
        """
        Provides a unique string identifier for the requestor.

        This implementation returns a combination of IP address and hostname.
        """
        try:
            return request._authentication_backend.get_identifier(request)
        except AttributeError:
            return 'nouser'

########NEW FILE########
__FILENAME__ = authorization


########NEW FILE########
__FILENAME__ = models

########NEW FILE########
__FILENAME__ = resources
from django.contrib.auth.models import User

from tastypie import fields
from tastypie.authentication import BasicAuthentication
from tastypie.authorization import Authorization, ReadOnlyAuthorization
from tastypie.constants import ALL, ALL_WITH_RELATIONS
from tastypie.resources import ModelResource

from comics.api.authentication import (
    SecretKeyAuthentication, MultiAuthentication)
from comics.core.models import Comic, Release, Image
from comics.accounts.models import Subscription


class UsersAuthorization(ReadOnlyAuthorization):
    def read_list(self, object_list, bundle):
        return object_list.filter(pk=bundle.request.user.pk)


class UsersResource(ModelResource):
    class Meta:
        queryset = User.objects.all()
        fields = ['email', 'date_joined', 'last_login']
        resource_name = 'users'
        authentication = MultiAuthentication(
            BasicAuthentication(realm='Comics API'),
            SecretKeyAuthentication())
        authorization = UsersAuthorization()
        list_allowed_methods = ['get']
        detail_allowed_methods = ['get']

    def dehydrate(self, bundle):
        bundle.data['secret_key'] = \
            bundle.request.user.comics_profile.secret_key
        return bundle


class ComicsAuthorization(ReadOnlyAuthorization):
    def read_list(self, object_list, bundle):
        if bundle.request.GET.get('subscribed') == 'true':
            return object_list.filter(userprofile__user=bundle.request.user)
        elif bundle.request.GET.get('subscribed') == 'false':
            return object_list.exclude(userprofile__user=bundle.request.user)
        else:
            return object_list


class ComicsResource(ModelResource):
    class Meta:
        queryset = Comic.objects.all()
        resource_name = 'comics'
        authentication = SecretKeyAuthentication()
        authorization = ComicsAuthorization()
        list_allowed_methods = ['get']
        detail_allowed_methods = ['get']
        filtering = {
            'active': 'exact',
            'language': 'exact',
            'name': ALL,
            'slug': ALL,
        }


class ImagesResource(ModelResource):
    class Meta:
        queryset = Image.objects.all()
        resource_name = 'images'
        authentication = SecretKeyAuthentication()
        list_allowed_methods = ['get']
        detail_allowed_methods = ['get']
        filtering = {
            'fetched': ALL,
            'title': ALL,
            'text': ALL,
            'height': ALL,
            'width': ALL,
        }


class ReleasesAuthorization(ReadOnlyAuthorization):
    def read_list(self, object_list, bundle):
        if bundle.request.GET.get('subscribed') == 'true':
            return object_list.filter(
                comic__userprofile__user=bundle.request.user)
        elif bundle.request.GET.get('subscribed') == 'false':
            return object_list.exclude(
                comic__userprofile__user=bundle.request.user)
        else:
            return object_list


class ReleasesResource(ModelResource):
    comic = fields.ToOneField(ComicsResource, 'comic')
    images = fields.ToManyField(ImagesResource, 'images', full=True)

    class Meta:
        queryset = Release.objects.select_related().order_by('-fetched')
        resource_name = 'releases'
        authentication = SecretKeyAuthentication()
        authorization = ReleasesAuthorization()
        list_allowed_methods = ['get']
        detail_allowed_methods = ['get']
        filtering = {
            'comic': ALL_WITH_RELATIONS,
            'images': ALL_WITH_RELATIONS,
            'pub_date': ALL,
            'fetched': ALL,
        }


class SubscriptionAuthorization(Authorization):
    def read_list(self, object_list, bundle):
        return object_list.filter(userprofile__user=bundle.request.user)


class SubscriptionsResource(ModelResource):
    comic = fields.ToOneField(ComicsResource, 'comic')

    class Meta:
        queryset = Subscription.objects.all()
        resource_name = 'subscriptions'
        authentication = SecretKeyAuthentication()
        authorization = SubscriptionAuthorization()
        list_allowed_methods = ['get', 'post', 'patch']
        detail_allowed_methods = ['get', 'delete', 'put']
        filtering = {
            'comic': ALL_WITH_RELATIONS,
        }

    def obj_create(self, bundle, **kwargs):
        return super(SubscriptionsResource, self).obj_create(
            bundle, userprofile=bundle.request.user.comics_profile)

########NEW FILE########
__FILENAME__ = tests
import base64
import json

from django.contrib.auth.models import User
from django.test.client import Client
from django.test import TestCase

from comics.accounts.models import Subscription
from comics.core.models import Comic


def create_user():
    user = User.objects.create_user('alice', 'alice@example.com', 'secret')
    user.comics_profile.secret_key = 's3cretk3y'
    user.comics_profile.save()
    return user


def create_subscriptions(user):
    Subscription.objects.create(
        userprofile=user.comics_profile,
        comic=Comic.objects.get(slug='geekandpoke'))
    Subscription.objects.create(
        userprofile=user.comics_profile,
        comic=Comic.objects.get(slug='xkcd'))


class RootResourceTestCase(TestCase):
    def setUp(self):
        self.client = Client()

    def test_get_root_without_authentication(self):
        response = self.client.get('/api/v1/')

        self.assertEquals(response.status_code, 200)

    def test_root_resource_returns_other_resource_endpoints_in_json(self):
        response = self.client.get('/api/v1/')

        data = json.loads(response.content)
        self.assertIn('comics', data)
        self.assertEquals(data['users']['list_endpoint'], '/api/v1/users/')
        self.assertEquals(data['comics']['list_endpoint'], '/api/v1/comics/')
        self.assertEquals(data['images']['list_endpoint'], '/api/v1/images/')
        self.assertEquals(
            data['releases']['list_endpoint'], '/api/v1/releases/')
        self.assertEquals(
            data['subscriptions']['list_endpoint'], '/api/v1/subscriptions/')

    def test_resource_can_return_xml(self):
        response = self.client.get('/api/v1/', HTTP_ACCEPT='application/xml')

        self.assertIn(
            "<?xml version='1.0' encoding='utf-8'?>", response.content)

    def test_resource_can_return_jsonp(self):
        response = self.client.get('/api/v1/', {'format': 'jsonp'})

        self.assertIn('callback(', response.content)

    def test_resource_can_return_jsonp_with_custom_callback_name(self):
        response = self.client.get(
            '/api/v1/', {'format': 'jsonp', 'callback': 'foo'})

        self.assertIn('foo(', response.content)

    def test_resource_returns_jsonp_if_just_given_callback_name(self):
        response = self.client.get('/api/v1/', {'callback': 'foo'})

        self.assertIn('foo(', response.content)


class UsersResourceTestCase(TestCase):
    def setUp(self):
        create_user()
        self.client = Client()

    def test_get_users_without_authentication(self):
        response = self.client.get('/api/v1/users/')

        self.assertEquals(response.status_code, 401)

    def test_get_users_with_basic_auth(self):
        response = self.client.get(
            '/api/v1/users/',
            HTTP_AUTHORIZATION='Basic %s' %
            base64.encodestring('alice:secret'))

        self.assertEquals(response.status_code, 200)

    def test_get_users_with_secret_key_in_header(self):
        response = self.client.get(
            '/api/v1/users/', HTTP_AUTHORIZATION='Key s3cretk3y')

        self.assertEquals(response.status_code, 200)

    def test_get_users_with_secret_key_in_url(self):
        response = self.client.get(
            '/api/v1/users/', {'key': 's3cretk3y'})

        self.assertEquals(response.status_code, 200)

    def test_response_returns_a_single_user_object(self):
        User.objects.create_user('bob', 'bob@example.com', 'topsecret')

        response = self.client.get(
            '/api/v1/users/', HTTP_AUTHORIZATION='Key s3cretk3y')

        data = json.loads(response.content)
        self.assertEquals(len(data['objects']), 1)

    def test_response_includes_the_secret_key(self):
        response = self.client.get(
            '/api/v1/users/', HTTP_AUTHORIZATION='Key s3cretk3y')

        data = json.loads(response.content)
        self.assertEquals(data['objects'][0]['secret_key'], 's3cretk3y')


class ComicsResourceTestCase(TestCase):
    fixtures = ['comics.json']

    def setUp(self):
        self.user = create_user()
        self.client = Client()

    def test_requires_authentication(self):
        response = self.client.get('/api/v1/comics/')

        self.assertEquals(response.status_code, 401)

    def test_authentication_with_secret_key_in_header(self):
        response = self.client.get(
            '/api/v1/comics/', HTTP_AUTHORIZATION='Key s3cretk3y')

        self.assertEquals(response.status_code, 200)

    def test_lists_comics(self):
        response = self.client.get(
            '/api/v1/comics/', HTTP_AUTHORIZATION='Key s3cretk3y')

        data = json.loads(response.content)
        self.assertEquals(len(data['objects']), 10)
        self.assertEquals(data['objects'][0]['slug'], 'abstrusegoose')

    def test_slug_filter(self):
        response = self.client.get(
            '/api/v1/comics/', {'slug': 'xkcd'},
            HTTP_AUTHORIZATION='Key s3cretk3y')

        data = json.loads(response.content)
        self.assertEquals(len(data['objects']), 1)
        self.assertEquals(data['objects'][0]['slug'], 'xkcd')

    def test_subscribed_filter(self):
        create_subscriptions(self.user)

        response = self.client.get(
            '/api/v1/comics/', {'subscribed': 'true'},
            HTTP_AUTHORIZATION='Key s3cretk3y')

        data = json.loads(response.content)
        self.assertEquals(len(data['objects']), 2)
        self.assertEquals(data['objects'][0]['slug'], 'geekandpoke')
        self.assertEquals(data['objects'][1]['slug'], 'xkcd')

    def test_unsubscribed_filter(self):
        create_subscriptions(self.user)

        response = self.client.get(
            '/api/v1/comics/', {'subscribed': 'false'},
            HTTP_AUTHORIZATION='Key s3cretk3y')

        data = json.loads(response.content)
        self.assertEquals(len(data['objects']), 8)
        self.assertEquals(data['objects'][0]['slug'], 'abstrusegoose')

    def test_details_view(self):
        response = self.client.get(
            '/api/v1/comics/', HTTP_AUTHORIZATION='Key s3cretk3y')

        data = json.loads(response.content)
        comic_uri = data['objects'][0]['resource_uri']
        self.assertEquals(comic_uri, '/api/v1/comics/1/')

        response = self.client.get(
            comic_uri, HTTP_AUTHORIZATION='Key s3cretk3y')

        data = json.loads(response.content)
        self.assertEquals(data['slug'], 'abstrusegoose')


class ImagesResourceTestCase(TestCase):
    fixtures = ['comics.json']

    def setUp(self):
        create_user()
        self.client = Client()

    def test_requires_authentication(self):
        response = self.client.get('/api/v1/images/')

        self.assertEquals(response.status_code, 401)

    def test_authentication_with_secret_key_in_header(self):
        response = self.client.get(
            '/api/v1/images/', HTTP_AUTHORIZATION='Key s3cretk3y')

        self.assertEquals(response.status_code, 200)

    def test_lists_images(self):
        response = self.client.get(
            '/api/v1/images/', HTTP_AUTHORIZATION='Key s3cretk3y')

        data = json.loads(response.content)
        self.assertEquals(len(data['objects']), 12)
        self.assertEquals(data['objects'][0]['height'], 1132)
        self.assertEquals(
            data['objects'][1]['title'],
            "Geek&Poke About The Good Ol' Days In Computers")

    def test_height_filter(self):
        response = self.client.get(
            '/api/v1/images/', {'height__gt': 1100},
            HTTP_AUTHORIZATION='Key s3cretk3y')

        data = json.loads(response.content)
        self.assertEquals(len(data['objects']), 2)
        self.assertEquals(data['objects'][0]['height'], 1132)
        self.assertEquals(data['objects'][1]['height'], 1132)

    def test_details_view(self):
        response = self.client.get(
            '/api/v1/images/', HTTP_AUTHORIZATION='Key s3cretk3y')

        data = json.loads(response.content)
        image_uri = data['objects'][1]['resource_uri']
        self.assertEquals(image_uri, '/api/v1/images/2/')

        response = self.client.get(
            image_uri, HTTP_AUTHORIZATION='Key s3cretk3y')

        data = json.loads(response.content)
        self.assertEquals(
            data['title'], "Geek&Poke About The Good Ol' Days In Computers")


class ReleasesResourceTestCase(TestCase):
    fixtures = ['comics.json']

    def setUp(self):
        self.user = create_user()
        self.client = Client()

    def test_requires_authentication(self):
        response = self.client.get('/api/v1/releases/')

        self.assertEquals(response.status_code, 401)

    def test_authentication_with_secret_key_in_header(self):
        response = self.client.get(
            '/api/v1/releases/', HTTP_AUTHORIZATION='Key s3cretk3y')

        self.assertEquals(response.status_code, 200)

    def test_list_releases(self):
        response = self.client.get(
            '/api/v1/releases/', HTTP_AUTHORIZATION='Key s3cretk3y')

        data = json.loads(response.content)
        self.assertEquals(len(data['objects']), 11)

        release = data['objects'][0]
        self.assertEquals(release['comic'], '/api/v1/comics/9/')
        self.assertEquals(release['pub_date'], '2012-10-12')
        self.assertEquals(
            release['resource_uri'], '/api/v1/releases/11/')
        self.assertEquals(len(release['images']), 1)

        image = release['images'][0]
        self.assertEquals(image['title'], 'Blurring the Line')
        self.assertEquals(
            image['text'], 'People into masturbatory ' +
            'navel-gazing have a lot to learn about masturbation.')
        self.assertEquals(image['height'], 235)
        self.assertEquals(image['width'], 740)
        self.assertEquals(
            image['checksum'],
            '76a1407a2730b000d51ccf764c689c8930fdd3580e01f62f70cbe73d8be17e9c')

    def test_subscribed_filter(self):
        create_subscriptions(self.user)

        response = self.client.get(
            '/api/v1/releases/', {'subscribed': 'true'},
            HTTP_AUTHORIZATION='Key s3cretk3y')

        data = json.loads(response.content)
        self.assertEquals(len(data['objects']), 6)

    def test_comic_filter(self):
        response = self.client.get(
            '/api/v1/releases/', {'comic__slug': 'geekandpoke'},
            HTTP_AUTHORIZATION='Key s3cretk3y')

        data = json.loads(response.content)
        self.assertEquals(len(data['objects']), 2)

        release = data['objects'][0]
        self.assertEquals(release['comic'], '/api/v1/comics/4/')

    def test_pub_date_filter(self):
        response = self.client.get(
            '/api/v1/releases/',
            {'pub_date__year': 2012, 'pub_date__month': 10},
            HTTP_AUTHORIZATION='Key s3cretk3y')

        data = json.loads(response.content)
        self.assertEquals(len(data['objects']), 11)

        response = self.client.get(
            '/api/v1/releases/',
            {'pub_date__year': 2012, 'pub_date__month': 9},
            HTTP_AUTHORIZATION='Key s3cretk3y')

        data = json.loads(response.content)
        self.assertEquals(len(data['objects']), 0)

    def test_unknown_filter_fails(self):
        response = self.client.get(
            '/api/v1/releases/',
            {'pub_date__foo': 'bar'},
            HTTP_AUTHORIZATION='Key s3cretk3y')

        self.assertEquals(response.status_code, 400)

    def test_details_view(self):
        response = self.client.get(
            '/api/v1/releases/', HTTP_AUTHORIZATION='Key s3cretk3y')

        data = json.loads(response.content)
        release_uri = data['objects'][0]['resource_uri']
        self.assertEquals(release_uri, '/api/v1/releases/11/')

        response = self.client.get(
            release_uri, HTTP_AUTHORIZATION='Key s3cretk3y')

        data = json.loads(response.content)
        self.assertEquals(data['pub_date'], '2012-10-12')
        self.assertEquals(len(data['images']), 1)


class SubscriptionsResourceTestCase(TestCase):
    fixtures = ['comics.json']

    def setUp(self):
        self.user = create_user()
        create_subscriptions(self.user)
        self.client = Client()

    def test_requires_authentication(self):
        response = self.client.get('/api/v1/subscriptions/')

        self.assertEquals(response.status_code, 401)

    def test_authentication_with_secret_key_in_header(self):
        response = self.client.get(
            '/api/v1/subscriptions/', HTTP_AUTHORIZATION='Key s3cretk3y')

        self.assertEquals(response.status_code, 200)

    def test_list_subscriptions(self):
        subscription = Subscription.objects.all()[0]

        response = self.client.get(
            '/api/v1/subscriptions/', HTTP_AUTHORIZATION='Key s3cretk3y')

        data = json.loads(response.content)
        self.assertEquals(len(data['objects']), 2)

        sub = data['objects'][0]
        self.assertEquals(
            sub['resource_uri'],
            '/api/v1/subscriptions/%d/' % subscription.pk)
        self.assertEquals(
            sub['comic'],
            '/api/v1/comics/%d/' % subscription.comic.pk)

    def test_comic_filter(self):
        subscription = Subscription.objects.get(comic__slug='xkcd')

        response = self.client.get(
            '/api/v1/subscriptions/',
            {'comic__slug': 'xkcd'},
            HTTP_AUTHORIZATION='Key s3cretk3y')

        data = json.loads(response.content)
        self.assertEquals(len(data['objects']), 1)

        sub = data['objects'][0]
        self.assertEquals(
            sub['resource_uri'],
            '/api/v1/subscriptions/%d/' % subscription.pk)
        self.assertEquals(sub['comic'], '/api/v1/comics/9/')

    def test_details_view(self):
        subscription = Subscription.objects.all()[0]

        response = self.client.get(
            '/api/v1/subscriptions/', HTTP_AUTHORIZATION='Key s3cretk3y')

        data = json.loads(response.content)
        sub = data['objects'][0]
        self.assertEquals(
            sub['resource_uri'],
            '/api/v1/subscriptions/%d/' % subscription.pk)

        response = self.client.get(
            sub['resource_uri'], HTTP_AUTHORIZATION='Key s3cretk3y')

        data = json.loads(response.content)
        self.assertEquals(
            data['comic'], '/api/v1/comics/%d/' % subscription.comic.pk)

    def test_subscribe_to_comic(self):
        comic = Comic.objects.get(slug='bunny')

        data = json.dumps({'comic': '/api/v1/comics/%d/' % comic.pk})
        response = self.client.post(
            '/api/v1/subscriptions/',
            data=data, content_type='application/json',
            HTTP_AUTHORIZATION='Key s3cretk3y')

        self.assertEquals(response.status_code, 201)

        subscription = Subscription.objects.get(
            userprofile__user=self.user, comic=comic)
        self.assertEquals(
            response['Location'],
            'http://testserver/api/v1/subscriptions/%d/' % subscription.pk)

        self.assertEquals(response.content, '')

    def test_unsubscribe_from_comic(self):
        sub = Subscription.objects.get(comic__slug='xkcd')

        self.assertEquals(
            2,
            Subscription.objects.filter(userprofile__user=self.user).count())

        response = self.client.delete(
            '/api/v1/subscriptions/%d/' % sub.pk,
            HTTP_AUTHORIZATION='Key s3cretk3y')

        self.assertEquals(response.status_code, 204)
        self.assertEquals(response.content, '')

        self.assertEquals(
            1,
            Subscription.objects.filter(userprofile__user=self.user).count())

    def test_bulk_update(self):
        # XXX: "PATCH /api/v1/subscriptions/" isn't tested as Django's test
        # client doesn't support the PATCH method yet. See
        # https://code.djangoproject.com/ticket/17797 to check if PATCH support
        # has been added yet.
        pass

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls import include, patterns

from tastypie.api import Api

from comics.api.resources import (
    UsersResource, ComicsResource, ImagesResource, ReleasesResource,
    SubscriptionsResource)

v1_api = Api(api_name='v1')
v1_api.register(UsersResource())
v1_api.register(ComicsResource())
v1_api.register(ImagesResource())
v1_api.register(ReleasesResource())
v1_api.register(SubscriptionsResource())

urlpatterns = patterns(
    '',
    (r'', include(v1_api.urls)),
)

########NEW FILE########
__FILENAME__ = models

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls import patterns, url

from comics.browser import views

YEAR = r'(?P<year>(19|20)\d{2})'                   # 1900-2099
MONTH = r'(?P<month>(0*[1-9]|1[0-2]))'             # 1-12
WEEK = r'week/(?P<week>(0*[1-9]|[1-4]\d|5[0-3]))'  # 1-53
DAY = r'(?P<day>(0*[1-9]|[1-2]\d|3[0-1]))'         # 1-31
DAYS = r'\+(?P<days>\d+)'
COMIC = r'(?P<comic_slug>[0-9a-z-_]+)'

urlpatterns = patterns(
    '',

    url(r'^$',
        views.MyComicsHome.as_view(),
        name='home'),

    url(r'^all/$',
        views.comics_list,
        name='comics_list'),

    # Views of my comics selection
    url(r'^my/$',
        views.MyComicsLatestView.as_view(),
        name='mycomics_latest'),
    url(r'^my/page(?P<page>[0-9]+)/$',
        views.MyComicsLatestView.as_view(),
        name='mycomics_latest_page_n'),
    url(r'^my/%s/$' % (YEAR,),
        views.MyComicsYearView.as_view(),
        name='mycomics_year'),
    url(r'^my/%s/%s/$' % (YEAR, MONTH),
        views.MyComicsMonthView.as_view(),
        name='mycomics_month'),
    url(r'^my/%s/%s/%s/$' % (YEAR, MONTH, DAY),
        views.MyComicsDayView.as_view(),
        name='mycomics_day'),
    url(r'^my/today/$',
        views.MyComicsTodayView.as_view(),
        name='mycomics_today'),
    url(r'^my/feed/$',
        views.MyComicsFeed.as_view(),
        name='mycomics_feed'),
    url(r'^my/num-releases-since/(?P<release_id>\d+)/$',
        views.MyComicsNumReleasesSinceView.as_view(),
        name='mycomics_num_releases_since'),

    # Views of a single comic
    url(r'^%s/$' % (COMIC,),
        views.OneComicLatestView.as_view(),
        name='comic_latest'),
    url(r'^%s/%s/$' % (COMIC, YEAR),
        views.OneComicYearView.as_view(),
        name='comic_year'),
    url(r'^%s/%s/%s/$' % (COMIC, YEAR, MONTH),
        views.OneComicMonthView.as_view(),
        name='comic_month'),
    url(r'^%s/%s/%s/%s/$' % (COMIC, YEAR, MONTH, DAY),
        views.OneComicDayView.as_view(),
        name='comic_day'),
    url(r'^%s/today/$' % (COMIC,),
        views.OneComicTodayView.as_view(),
        name='comic_today'),
    url(r'^%s/website/$' % (COMIC,),
        views.OneComicWebsiteRedirect.as_view(),
        name='comic_website'),
    url(r'^%s/feed/$' % (COMIC,),
        views.OneComicFeed.as_view(),
        name='comic_feed'),
)

########NEW FILE########
__FILENAME__ = views
import datetime
import json

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, render
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.generic import (
    TemplateView, ListView, RedirectView,
    DayArchiveView, TodayArchiveView, MonthArchiveView)

from comics.core.models import Comic, Release


@login_required
def comics_list(request):
    return render(request, 'browser/comics_list.html', {
        'active': {'comics_list': True},
        'my_comics': request.user.comics_profile.comics.all(),
    })


class LoginRequiredMixin(object):
    """Things common for views requiring the user to be logged in"""

    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        # This overide is here so that the login_required decorator can be
        # applied to all the views subclassing this class.
        return super(LoginRequiredMixin, self).dispatch(*args, **kwargs)

    def get_user(self):
        return self.request.user


class ComicMixin(object):
    """Things common for *all* views of comics"""

    @property
    def comic(self):
        if not hasattr(self, '_comic'):
            self._comic = get_object_or_404(
                Comic, slug=self.kwargs['comic_slug'])
        return self._comic

    def get_my_comics(self):
        return self.get_user().comics_profile.comics.all()


class ReleaseMixin(LoginRequiredMixin, ComicMixin):
    """Things common for *all* views of comic releases"""

    allow_future = True
    template_name = 'browser/release_list.html'

    def render_to_response(self, context, **kwargs):
        # We hook into render_to_response() instead of get_context_data()
        # because the date based views only populate the context with
        # date-related information right before render_to_response() is called.
        context.update(self.get_release_context_data(context))
        return super(ReleaseMixin, self).render_to_response(context, **kwargs)

    def get_release_context_data(self, context):
        # The methods called later in this method assumes that ``self.context``
        # contains what is already ready to be made available for the template.
        self.context = context

        return {
            'my_comics': self.get_my_comics(),

            'active': {'comics': True},
            'object_type': self.get_object_type(),
            'view_type': self.get_view_type(),

            'title': self.get_title(),
            'subtitle': self.get_subtitle(),

            'latest_url': self.get_latest_url(),
            'today_url': self.get_today_url(),
            'day_url': self.get_day_url(),
            'month_url': self.get_month_url(),
            'feed_url': self.get_feed_url(),
            'feed_title': self.get_feed_title(),

            'first_url': self.get_first_url(),
            'prev_url': self.get_prev_url(),
            'next_url': self.get_next_url(),
            'last_url': self.get_last_url(),
        }

    def get_object_type(self):
        return None

    def get_view_type(self):
        return None

    def get_title(self):
        return None

    def get_subtitle(self):
        return None

    def get_latest_url(self):
        return None

    def get_today_url(self):
        return None

    def get_day_url(self):
        return None

    def get_month_url(self):
        return None

    def get_feed_url(self):
        return None

    def get_feed_title(self):
        return None

    def get_first_url(self):
        return None

    def get_prev_url(self):
        return None

    def get_next_url(self):
        return None

    def get_last_url(self):
        return None


class ReleaseLatestView(ReleaseMixin, ListView):
    """Things common for all *latest* views"""

    def get_subtitle(self):
        return 'Latest releases'

    def get_view_type(self):
        return 'latest'


class ReleaseDateMixin(ReleaseMixin):
    """Things common for all *date based* views"""

    date_field = 'pub_date'
    month_format = '%m'


class ReleaseDayArchiveView(ReleaseDateMixin, DayArchiveView):
    """Things common for all *day* views"""

    def get_view_type(self):
        return 'day'

    def get_subtitle(self):
        return self.context['day'].strftime('%A %d %B %Y').replace(' 0', ' ')


class ReleaseTodayArchiveView(ReleaseDateMixin, TodayArchiveView):
    """Things common for all *today* views"""

    def get_view_type(self):
        return 'today'

    def get_subtitle(self):
        return 'Today'


class ReleaseMonthArchiveView(ReleaseDateMixin, MonthArchiveView):
    """Things common for all *month* views"""

    def get_view_type(self):
        return 'month'

    def get_subtitle(self):
        return self.context['month'].strftime('%B %Y')


class ReleaseFeedView(ComicMixin, ListView):
    """Things common for all *feed* views"""

    template_name = 'browser/release_feed.html'

    def get_context_data(self, **kwargs):
        context = super(ReleaseFeedView, self).get_context_data(**kwargs)
        context.update({
            'feed': {
                'title': self.get_feed_title(),
                'url': self.request.build_absolute_uri(self.get_feed_url()),
                'web_url': self.request.build_absolute_uri(self.get_web_url()),
                'base_url': self.request.build_absolute_uri('/'),
                'author': self.get_feed_author(),
                'updated': self.get_last_updated(),
            },
        })
        return context

    def render_to_response(self, context, **kwargs):
        return super(ReleaseFeedView, self).render_to_response(
            context, content_type='application/xml', **kwargs)

    def get_user(self):
        return get_object_or_404(
            User,
            comics_profile__secret_key=self.request.GET.get('key', None),
            is_active=True)

    def get_web_url(self):
        return self.get_latest_url()

    def get_feed_author(self):
        return settings.COMICS_SITE_TITLE

    def get_last_updated(self):
        try:
            return self.get_queryset().values_list('fetched', flat=True)[0]
        except IndexError:
            return timezone.now()


class MyComicsMixin(object):
    """Things common for all views of *my comics*"""

    def get_queryset(self):
        return Release.objects.select_related().filter(
            comic__in=self.get_my_comics()).order_by('pub_date')

    def get_object_type(self):
        return 'mycomics'

    def get_title(self):
        return 'My comics'

    def get_latest_url(self):
        return reverse('mycomics_latest')

    def get_today_url(self):
        return reverse('mycomics_today')

    def _get_last_pub_date(self):
        if not hasattr(self, '_last_pub_date'):
            self._last_pub_date = self.get_queryset().values_list(
                'pub_date', flat=True).order_by('-pub_date')[0]
        return self._last_pub_date

    def get_day_url(self):
        try:
            last_date = self._get_last_pub_date()
            return reverse('mycomics_day', kwargs={
                'year': last_date.year,
                'month': last_date.month,
                'day': last_date.day,
            })
        except IndexError:
            pass

    def get_month_url(self):
        try:
            last_month = self._get_last_pub_date()
            return reverse('mycomics_month', kwargs={
                'year': last_month.year,
                'month': last_month.month,
            })
        except IndexError:
            pass

    def get_feed_url(self):
        return '%s?key=%s' % (
            reverse('mycomics_feed'),
            self.get_user().comics_profile.secret_key)

    def get_feed_title(self):
        return 'My comics'


class MyComicsHome(LoginRequiredMixin, RedirectView):
    """Redirects the home page to my comics"""

    def get_redirect_url(self, **kwargs):
        return reverse('mycomics_latest')


class MyComicsLatestView(MyComicsMixin, ReleaseLatestView):
    """View of the latest releases from my comics"""

    paginate_by = settings.COMICS_MAX_RELEASES_PER_PAGE

    def get_queryset(self):
        releases = super(MyComicsLatestView, self).get_queryset()
        return releases.order_by('-fetched')

    def get_first_url(self):
        page = self.context['page_obj']
        if page.number != page.paginator.num_pages:
            return reverse(
                'mycomics_latest_page_n',
                kwargs={'page': page.paginator.num_pages})

    def get_prev_url(self):
        page = self.context['page_obj']
        if page.has_next():
            return reverse(
                'mycomics_latest_page_n',
                kwargs={'page': page.next_page_number()})

    def get_next_url(self):
        page = self.context['page_obj']
        if page.has_previous():
            return reverse(
                'mycomics_latest_page_n',
                kwargs={'page': page.previous_page_number()})

    def get_last_url(self):
        page = self.context['page_obj']
        if page.number != 1:
            return reverse('mycomics_latest_page_n', kwargs={'page': 1})


class MyComicsNumReleasesSinceView(MyComicsLatestView):
    def get_num_releases_since(self):
        last_release_seen = get_object_or_404(
            Release, id=self.kwargs['release_id'])
        releases = super(MyComicsNumReleasesSinceView, self).get_queryset()
        return releases.filter(fetched__gt=last_release_seen.fetched).count()

    def render_to_response(self, context, **kwargs):
        data = json.dumps({
            'since_release_id': int(self.kwargs['release_id']),
            'num_releases': self.get_num_releases_since(),
            'seconds_to_next_check': settings.COMICS_BROWSER_REFRESH_INTERVAL,
        })
        return HttpResponse(data, content_type='application/json')


class MyComicsDayView(MyComicsMixin, ReleaseDayArchiveView):
    """View of releases from my comics for a given day"""

    def get_first_url(self):
        try:
            first_date = self.get_queryset().values_list(
                'pub_date', flat=True).order_by('pub_date')[0]
            if first_date < self.context['day']:
                return reverse('mycomics_day', kwargs={
                    'year': first_date.year,
                    'month': first_date.month,
                    'day': first_date.day,
                })
        except IndexError:
            pass

    def get_prev_url(self):
        prev_date = self.get_previous_day(self.context['day'])
        if prev_date:
            return reverse('mycomics_day', kwargs={
                'year': prev_date.year,
                'month': prev_date.month,
                'day': prev_date.day,
            })

    def get_next_url(self):
        next_date = self.get_next_day(self.context['day'])
        if next_date:
            return reverse('mycomics_day', kwargs={
                'year': next_date.year,
                'month': next_date.month,
                'day': next_date.day,
            })

    def get_last_url(self):
        try:
            last_date = self.get_queryset().values_list(
                'pub_date', flat=True).order_by('-pub_date')[0]
            if last_date > self.context['day']:
                return reverse('mycomics_day', kwargs={
                    'year': last_date.year,
                    'month': last_date.month,
                    'day': last_date.day,
                })
        except IndexError:
            pass


class MyComicsTodayView(MyComicsMixin, ReleaseTodayArchiveView):
    """View of releases from my comics for today"""

    allow_empty = True

    def get_prev_url(self):
        prev_date = self.get_previous_day(self.context['day'])
        if prev_date:
            return reverse('mycomics_day', kwargs={
                'year': prev_date.year,
                'month': prev_date.month,
                'day': prev_date.day,
            })


class MyComicsMonthView(MyComicsMixin, ReleaseMonthArchiveView):
    """View of releases from my comics for a given month"""

    def get_first_url(self):
        try:
            first_month = self.get_queryset().values_list(
                'pub_date', flat=True).order_by('pub_date')[0]
            if first_month < self.context['month']:
                return reverse('mycomics_month', kwargs={
                    'year': first_month.year,
                    'month': first_month.month,
                })
        except IndexError:
            pass

    def get_prev_url(self):
        prev_month = self.context['previous_month']
        if prev_month:
            return reverse('mycomics_month', kwargs={
                'year': prev_month.year,
                'month': prev_month.month,
            })

    def get_next_url(self):
        next_month = self.context['next_month']
        if next_month:
            return reverse('mycomics_month', kwargs={
                'year': next_month.year,
                'month': next_month.month,
            })

    def get_last_url(self):
        try:
            last_month = self.get_queryset().values_list(
                'pub_date', flat=True).order_by('-pub_date')[0]
            if last_month > self.context['month']:
                return reverse('mycomics_month', kwargs={
                    'year': last_month.year,
                    'month': last_month.month,
                })
        except IndexError:
            pass


class MyComicsYearView(LoginRequiredMixin, RedirectView):
    """Redirect anyone trying to view the full year to January"""

    def get_redirect_url(self, **kwargs):
        return reverse('mycomics_month', kwargs={
            'year': kwargs['year'],
            'month': '1',
        })


class MyComicsFeed(MyComicsMixin, ReleaseFeedView):
    """Atom feed for releases from my comics"""

    def get_queryset(self):
        from_date = datetime.date.today() - datetime.timedelta(
            days=settings.COMICS_MAX_DAYS_IN_FEED)
        releases = super(MyComicsFeed, self).get_queryset()
        return releases.filter(fetched__gte=from_date).order_by('-fetched')


class OneComicMixin(object):
    """Things common for all views of a single comic"""

    def get_queryset(self):
        return (
            Release.objects.select_related()
            .filter(comic=self.comic)
            .order_by('pub_date'))

    def get_object_type(self):
        return 'onecomic'

    def get_title(self):
        return self.comic.name

    def get_latest_url(self):
        return reverse('comic_latest', kwargs={'comic_slug': self.comic.slug})

    def _get_recent_pub_dates(self):
        if not hasattr(self, '_recent_pub_dates'):
            self._recent_pub_dates = self.get_queryset().values_list(
                'pub_date', flat=True).order_by('-pub_date')[:2]
        return self._recent_pub_dates

    def get_today_url(self):
        if datetime.date.today() in self._get_recent_pub_dates():
            return reverse(
                'comic_today',
                kwargs={'comic_slug': self.comic.slug})

    def get_day_url(self):
        try:
            last_pub_date = self._get_recent_pub_dates()[0]
            return reverse('comic_day', kwargs={
                'comic_slug': self.comic.slug,
                'year': last_pub_date.year,
                'month': last_pub_date.month,
                'day': last_pub_date.day,
            })
        except IndexError:
            pass

    def get_month_url(self):
        try:
            last_pub_date = self._get_recent_pub_dates()[0]
            return reverse('comic_month', kwargs={
                'comic_slug': self.comic.slug,
                'year': last_pub_date.year,
                'month': last_pub_date.month,
            })
        except IndexError:
            pass

    def get_feed_url(self):
        return '%s?key=%s' % (
            reverse('comic_feed', kwargs={'comic_slug': self.comic.slug}),
            self.get_user().comics_profile.secret_key)

    def get_feed_title(self):
        return 'Comics from %s' % self.comic.name

    def get_first_url(self):
        try:
            first_date = self.get_queryset().values_list(
                'pub_date', flat=True).order_by('pub_date')[0]
            if first_date < self.get_current_day():
                return reverse('comic_day', kwargs={
                    'comic_slug': self.comic.slug,
                    'year': first_date.year,
                    'month': first_date.month,
                    'day': first_date.day,
                })
        except IndexError:
            pass

    def get_prev_url(self):
        prev_date = self.get_previous_day(self.get_current_day())
        if prev_date:
            return reverse('comic_day', kwargs={
                'comic_slug': self.comic.slug,
                'year': prev_date.year,
                'month': prev_date.month,
                'day': prev_date.day,
            })

    def get_next_url(self):
        next_date = self.get_next_day(self.get_current_day())
        if next_date:
            return reverse('comic_day', kwargs={
                'comic_slug': self.comic.slug,
                'year': next_date.year,
                'month': next_date.month,
                'day': next_date.day,
            })

    def get_last_url(self):
        try:
            last_pub_date = self._get_recent_pub_dates()[0]
            if last_pub_date > self.get_current_day():
                return reverse('comic_day', kwargs={
                    'comic_slug': self.comic.slug,
                    'year': last_pub_date.year,
                    'month': last_pub_date.month,
                    'day': last_pub_date.day,
                })
        except IndexError:
            pass


class OneComicLatestView(OneComicMixin, ReleaseLatestView):
    """View of the latest release from a single comic"""

    paginate_by = 1

    def get_queryset(self):
        releases = super(OneComicLatestView, self).get_queryset()
        return releases.order_by('-fetched')

    def get_current_day(self):
        try:
            return self._get_recent_pub_dates()[0]
        except IndexError:
            pass

    def get_previous_day(self, day):
        try:
            return self._get_recent_pub_dates()[1]
        except IndexError:
            pass

    def get_next_day(self, day):
        pass  # Nothing is newer than 'latest'


class OneComicDayView(OneComicMixin, ReleaseDayArchiveView):
    """View of the releases from a single comic for a given day"""

    def get_current_day(self):
        return self.context['day']


class OneComicTodayView(OneComicMixin, ReleaseTodayArchiveView):
    """View of the releases from a single comic for today"""

    def get_current_day(self):
        return self.context['day']


class OneComicMonthView(OneComicMixin, ReleaseMonthArchiveView):
    """View of the releases from a single comic for a given month"""

    def get_first_url(self):
        try:
            first_month = self.get_queryset().values_list(
                'pub_date', flat=True).order_by('pub_date')[0]
            if first_month < self.context['month']:
                return reverse('comic_month', kwargs={
                    'comic_slug': self.comic.slug,
                    'year': first_month.year,
                    'month': first_month.month,
                })
        except IndexError:
            pass

    def get_prev_url(self):
        prev_month = self.context['previous_month']
        if prev_month:
            return reverse('comic_month', kwargs={
                'comic_slug': self.comic.slug,
                'year': prev_month.year,
                'month': prev_month.month,
            })

    def get_next_url(self):
        next_month = self.context['next_month']
        if next_month:
            return reverse('comic_month', kwargs={
                'comic_slug': self.comic.slug,
                'year': next_month.year,
                'month': next_month.month,
            })

    def get_last_url(self):
        try:
            last_pub_date = self._get_recent_pub_dates()[0]
            if last_pub_date > self.context['month']:
                return reverse('comic_month', kwargs={
                    'comic_slug': self.comic.slug,
                    'year': last_pub_date.year,
                    'month': last_pub_date.month,
                })
        except IndexError:
            pass


class OneComicYearView(LoginRequiredMixin, RedirectView):
    """Redirect anyone trying to view the full year to January"""

    def get_redirect_url(self, **kwargs):
        return reverse('comic_month', kwargs={
            'comic_slug': kwargs['comic_slug'],
            'year': kwargs['year'],
            'month': '1',
        })


class OneComicFeed(OneComicMixin, ReleaseFeedView):
    """Atom feed for releases of a single comic"""

    def get_queryset(self):
        from_date = datetime.date.today() - datetime.timedelta(
            days=settings.COMICS_MAX_DAYS_IN_FEED)
        releases = super(OneComicFeed, self).get_queryset()
        return releases.filter(fetched__gte=from_date).order_by('-fetched')


class OneComicWebsiteRedirect(LoginRequiredMixin, ComicMixin, TemplateView):
    template_name = 'browser/comic_website.html'

    def get_context_data(self, **kwargs):
        context = super(OneComicWebsiteRedirect, self).get_context_data(
            **kwargs)
        context['url'] = self.comic.url
        return context

########NEW FILE########
__FILENAME__ = 20px
from comics.aggregator.crawler import CrawlerBase, CrawlerImage
from comics.core.comic_data import ComicDataBase


class ComicData(ComicDataBase):
    name = 'Twenty Pixels'
    language = 'en'
    url = 'http://20px.com/'
    start_date = '2011-02-11'
    rights = 'Angela'


class Crawler(CrawlerBase):
    history_capable_days = 90
    time_zone = 'US/Pacific'

    def crawl(self, pub_date):
        feed = self.parse_feed('http://feeds.feedburner.com/20px')
        for entry in feed.for_date(pub_date):
            if 'Comic' not in entry.tags:
                continue
            selector = 'img[src*="/wp-content/uploads/"]:not(img[src$="_sq.jpg"])'
            results = []

            for url in entry.content0.src(selector, allow_multiple=True):
                results.append(CrawlerImage(url))

            if results:
                results[0].title = entry.title
                results[0].text = entry.content0.alt(
                    selector, allow_multiple=True)[0]
                return results

########NEW FILE########
__FILENAME__ = 8bittheater
from comics.aggregator.crawler import CrawlerBase
from comics.core.comic_data import ComicDataBase


class ComicData(ComicDataBase):
    name = '8-Bit Theater'
    language = 'en'
    url = 'http://www.nuklearpower.com/'
    active = False
    start_date = '2001-03-02'
    end_date = '2010-06-01'
    rights = 'Brian Clevinger'


class Crawler(CrawlerBase):
    def crawl(self, pub_date):
        pass  # Comic no longer published

########NEW FILE########
__FILENAME__ = abstrusegoose
from comics.aggregator.crawler import CrawlerBase, CrawlerImage
from comics.core.comic_data import ComicDataBase


class ComicData(ComicDataBase):
    name = 'Abstruse Goose'
    language = 'en'
    url = 'http://www.abstrusegoose.com/'
    start_date = '2008-02-01'
    rights = 'lcfr, CC BY-NC 3.0 US'


class Crawler(CrawlerBase):
    history_capable_days = 10
    schedule = 'Mo,Th'
    time_zone = 'US/Pacific'

    def crawl(self, pub_date):
        feed = self.parse_feed('http://abstrusegoose.com/atomfeed.xml')
        for entry in feed.for_date(pub_date):
            url = entry.summary.src('img[src*="/strips/"]')
            title = entry.title
            text = entry.summary.title('img[src*="/strips/"]')
            return CrawlerImage(url, title, text)

########NEW FILE########
__FILENAME__ = adam4d
from comics.aggregator.crawler import CrawlerBase, CrawlerImage
from comics.core.comic_data import ComicDataBase


class ComicData(ComicDataBase):
    name = 'Adam4d.com'
    language = 'en'
    url = 'http://www.adam4d.com/'
    start_date = '2012-07-03'
    rights = 'Adam Ford'


class Crawler(CrawlerBase):
    history_capable_days = 10
    time_zone = 'US/Eastern'

    def crawl(self, pub_date):
        feed = self.parse_feed('http://adam4d.com/feed/')
        for entry in feed.for_date(pub_date):
            url = entry.summary.src('img.comicthumbnail')
            if url is None:
                continue
            url = url.replace('comics-rss', 'comics')
            title = entry.title
            text = entry.summary.alt('img.comicthumbnail')
            return CrawlerImage(url, title, text)

########NEW FILE########
__FILENAME__ = amazingsuperpowers
from comics.aggregator.crawler import CrawlerBase, CrawlerImage
from comics.core.comic_data import ComicDataBase


class ComicData(ComicDataBase):
    name = 'AmazingSuperPowers'
    language = 'en'
    url = 'http://www.amazingsuperpowers.com/'
    start_date = '2007-09-24'
    rights = 'Wes & Tony'


class Crawler(CrawlerBase):
    history_capable_days = 30
    schedule = 'Mo,Th'
    time_zone = 'US/Eastern'

    # Without User-Agent set, the server returns 403 Forbidden
    headers = {'User-Agent': 'Mozilla/4.0'}

    def crawl(self, pub_date):
        feed = self.parse_feed('http://feeds.feedburner.com/amazingsuperpowers')
        for entry in feed.for_date(pub_date):
            url = entry.content0.src('img[src*="/comics/"]')
            title = entry.title
            text = entry.content0.title('img[src*="/comics/"]')
            return CrawlerImage(url, title, text)

########NEW FILE########
__FILENAME__ = antics
from comics.aggregator.crawler import CrawlerBase, CrawlerImage
from comics.core.comic_data import ComicDataBase


class ComicData(ComicDataBase):
    name = 'Antics'
    language = 'en'
    url = 'http://www.anticscomic.com/'
    start_date = '2008-10-25'
    rights = 'Fletcher'


class Crawler(CrawlerBase):
    history_capable_days = 30
    schedule = 'Mo,Fr'
    time_zone = 'US/Pacific'

    def crawl(self, pub_date):
        feed = self.parse_feed('http://www.anticscomic.com/?feed=rss2')
        for entry in feed.for_date(pub_date):
            if 'comic' not in entry.tags:
                continue
            image_url = pub_date.strftime('/comics/%Y-%m-%d.jpg')
            url = entry.summary.src('img[src$="%s"]' % image_url)
            title = entry.title
            text = entry.summary.title('img[src*="%s"]' % image_url)
            return CrawlerImage(url, title, text)

########NEW FILE########
__FILENAME__ = apokalips
from comics.aggregator.crawler import CrawlerBase
from comics.core.comic_data import ComicDataBase


class ComicData(ComicDataBase):
    name = 'Apokalips Web Comic'
    language = 'en'
    url = 'http://www.myapokalips.com/'
    start_date = '2009-02-13'
    end_date = '2011-07-04'
    active = False
    rights = 'Mike Gioia, CC BY-NC 2.5'


class Crawler(CrawlerBase):
    def crawl(self, pub_date):
        pass  # Comic no longer published

########NEW FILE########
__FILENAME__ = applegeeks
from comics.aggregator.crawler import CrawlerBase
from comics.core.comic_data import ComicDataBase


class ComicData(ComicDataBase):
    name = 'AppleGeeks'
    language = 'en'
    url = 'http://www.applegeeks.com/'
    start_date = '2003-01-01'
    end_date = '2010-11-22'
    active = False
    rights = 'Mohammad Haque & Ananth Panagariya'


class Crawler(CrawlerBase):
    def crawl(self, pub_date):
        pass  # Comic no longer published

########NEW FILE########
__FILENAME__ = applegeekslite
from comics.aggregator.crawler import CrawlerBase
from comics.core.comic_data import ComicDataBase


class ComicData(ComicDataBase):
    name = 'AppleGeeks Lite'
    language = 'en'
    url = 'http://www.applegeeks.com/'
    start_date = '2006-04-18'
    end_date = '2010-08-30'
    active = False
    rights = 'Mohammad Haque & Ananth Panagariya'


class Crawler(CrawlerBase):
    def crawl(self, pub_date):
        pass  # Comic no longer published

########NEW FILE########
__FILENAME__ = asofterworld
import re

from comics.aggregator.crawler import CrawlerBase, CrawlerImage
from comics.core.comic_data import ComicDataBase


class ComicData(ComicDataBase):
    name = 'A Softer World'
    language = 'en'
    url = 'http://www.asofterworld.com/'
    start_date = '2003-02-07'
    rights = 'Joey Comeau, Emily Horne'


class Crawler(CrawlerBase):
    history_capable_date = '2003-02-07'
    schedule = None
    time_zone = 'US/Pacific'

    def crawl(self, pub_date):
        feed = self.parse_feed('http://www.rsspect.com/rss/asw.xml')
        for entry in feed.for_date(pub_date):
            if entry.title == 'A Softer World':
                urls = entry.summary.src(
                    'img[src*="/clean/"]', allow_multiple=True)
                if not urls:
                    continue
                url = urls[0]
                asw_id = re.findall('(\d+)$', entry.link)[0]
                title = '%s: %s' % (entry.title, asw_id)
                text = entry.summary.title(
                    'img[src*="/clean/"]', allow_multiple=True)[0]
                return CrawlerImage(url, title, text)

########NEW FILE########
__FILENAME__ = atheistcartoons
from comics.aggregator.crawler import CrawlerBase
from comics.core.comic_data import ComicDataBase


class ComicData(ComicDataBase):
    name = 'Atheist Cartoons'
    language = 'en'
    url = 'http://www.atheistcartoons.com/'
    start_date = '2009-01-03'
    end_date = '2011-08-25'
    active = False
    rights = 'Atheist Cartoons'


class Crawler(CrawlerBase):
    def crawl(self, pub_date):
        pass  # Comic no longer published

########NEW FILE########
__FILENAME__ = axecop
from comics.aggregator.crawler import CrawlerBase, CrawlerImage
from comics.core.comic_data import ComicDataBase


class ComicData(ComicDataBase):
    name = 'Axe Cop'
    language = 'en'
    url = 'http://www.axecop.com/'
    start_date = '2010-01-02'
    rights = 'Ethan Nicolle'


class Crawler(CrawlerBase):
    history_capable_days = 60
    schedule = 'Tu'
    time_zone = 'US/Pacific'

    headers = {'User-Agent': 'Mozilla/4.0'}

    def crawl(self, pub_date):
        feed = self.parse_feed('http://axecop.com/feed/')
        for entry in feed.for_date(pub_date):
            title = entry.title
            url = entry.summary.src('img[src*="/wp-content/uploads/"]')
            url = url.replace('-150x150', '')
            return CrawlerImage(url, title)

########NEW FILE########
__FILENAME__ = babyblues
from comics.aggregator.crawler import CrawlerBase, CrawlerImage
from comics.core.comic_data import ComicDataBase


class ComicData(ComicDataBase):
    name = 'Baby Blues'
    language = 'en'
    url = 'http://www.arcamax.com/babyblues'
    start_date = '1990-01-01'
    rights = 'Rick Kirkman and Jerry Scott'


class Crawler(CrawlerBase):
    history_capable_days = 0
    schedule = 'Mo,Tu,We,Th,Fr,Sa,Su'
    time_zone = 'US/Eastern'

    def crawl(self, pub_date):
        page = self.parse_page('http://www.arcamax.com/babyblues')
        url = page.src('img[alt^="Baby Blues Cartoon"]')
        return CrawlerImage(url)

########NEW FILE########
__FILENAME__ = basicinstructions
from comics.aggregator.crawler import CrawlerBase, CrawlerImage
from comics.core.comic_data import ComicDataBase


class ComicData(ComicDataBase):
    name = 'Basic Instructions'
    language = 'en'
    url = 'http://www.basicinstructions.net/'
    start_date = '2006-07-01'
    rights = 'Scott Meyer'


class Crawler(CrawlerBase):
    history_capable_days = 100
    schedule = 'Tu,Th,Su'
    time_zone = 'US/Eastern'

    def crawl(self, pub_date):
        feed = self.parse_feed(
            'http://basicinstructions.net/basic-instructions/rss.xml')
        for entry in feed.for_date(pub_date):
            url = entry.summary.src('img[src*="/storage/"][src*=".gif"]')
            title = entry.title
            return CrawlerImage(url, title)

########NEW FILE########
__FILENAME__ = beetlebailey
from comics.aggregator.crawler import ArcaMaxCrawlerBase
from comics.core.comic_data import ComicDataBase


class ComicData(ComicDataBase):
    name = 'Beetle Bailey'
    language = 'en'
    url = 'http://www.arcamax.com/thefunnies/beetlebailey/'
    start_date = '1950-01-01'
    rights = 'Mort Walker'


class Crawler(ArcaMaxCrawlerBase):
    history_capable_days = 0
    schedule = 'Mo,Tu,We,Th,Fr,Sa,Su'
    time_zone = 'US/Eastern'

    def crawl(self, pub_date):
        return self.crawl_helper('beetlebailey', pub_date)

########NEW FILE########
__FILENAME__ = betty
from comics.aggregator.crawler import GoComicsComCrawlerBase
from comics.core.comic_data import ComicDataBase


class ComicData(ComicDataBase):
    name = 'Betty'
    language = 'en'
    url = 'http://www.gocomics.com/betty/'
    start_date = '1991-01-01'
    rights = 'Delainey & Gerry Rasmussen'


class Crawler(GoComicsComCrawlerBase):
    history_capable_date = '2008-10-13'
    schedule = 'Mo,Tu,We,Th,Fr,Sa,Su'
    time_zone = 'US/Eastern'

    def crawl(self, pub_date):
        return self.crawl_helper('Betty', pub_date)

########NEW FILE########
__FILENAME__ = beyondthetree
from comics.aggregator.crawler import CrawlerBase, CrawlerImage
from comics.core.comic_data import ComicDataBase


class ComicData(ComicDataBase):
    name = 'Beyond the Tree'
    language = 'en'
    url = 'http://beyondthetree.wordpress.com/'
    start_date = '2008-03-20'
    end_date = '2012-03-18'
    active = False
    rights = 'Nhani'


class Crawler(CrawlerBase):
    def crawl(self, pub_date):
        pass  # Comic no longer published

########NEW FILE########
__FILENAME__ = bgobt
from comics.aggregator.crawler import CrawlerBase
from comics.core.comic_data import ComicDataBase


class ComicData(ComicDataBase):
    name = 'Business Guys on Business Trips'
    language = 'en'
    url = 'http://www.businessguysonbusinesstrips.com/'
    start_date = '2007-07-12'
    end_date = '2011-11-23'
    active = False
    rights = '"Managing Director"'


class Crawler(CrawlerBase):
    def crawl(self, pub_date):
        pass  # Comic no longer published

########NEW FILE########
__FILENAME__ = billy
from comics.aggregator.crawler import CrawlerBase
from comics.core.comic_data import ComicDataBase


class ComicData(ComicDataBase):
    name = 'Billy'
    language = 'no'
    url = 'http://www.billy.no/'
    start_date = '1950-01-01'
    active = False
    rights = 'Mort Walker'


class Crawler(CrawlerBase):
    def crawl(self, pub_date):
        pass  # Comic no longer published

########NEW FILE########
__FILENAME__ = bizarro
from comics.aggregator.crawler import CrawlerBase, CrawlerImage
from comics.core.comic_data import ComicDataBase


class ComicData(ComicDataBase):
    name = 'Bizarro'
    language = 'en'
    url = 'http://bizarrocomics.com/'
    start_date = '1985-01-01'
    rights = 'Dan Piraro'


class Crawler(CrawlerBase):
    history_capable_days = 40
    time_zone = 'US/Eastern'

    def crawl(self, pub_date):
        feed = self.parse_feed('http://bizarrocomics.com/feed/')

        for entry in feed.for_date(pub_date):
            if 'daily Bizarros' not in entry.tags:
                continue

            page = self.parse_page(entry.link)

            results = []
            for url in page.src('img.size-full', allow_multiple=True):
                results.append(CrawlerImage(url))

            if results:
                results[0].title = entry.title
                return results

########NEW FILE########
__FILENAME__ = bizarrono
from comics.aggregator.crawler import CrawlerBase
from comics.core.comic_data import ComicDataBase


class ComicData(ComicDataBase):
    name = 'Bizarro (no)'
    language = 'no'
    url = 'http://underholdning.no.msn.com/tegneserier/bizarro/'
    start_date = '1985-01-01'
    active = False
    rights = 'Dan Piraro'


class Crawler(CrawlerBase):
    def crawl(self, pub_date):
        pass  # Comic no longer published

########NEW FILE########
__FILENAME__ = boasas
from comics.aggregator.crawler import CrawlerBase
from comics.core.comic_data import ComicDataBase


class ComicData(ComicDataBase):
    name = 'Boy on a Stick and Slither'
    language = 'en'
    url = 'http://www.boasas.com/'
    start_date = '1998-01-01'
    end_date = '2011-09-12'
    active = False
    rights = 'Steven L. Cloud'


class Crawler(CrawlerBase):
    def crawl(self, pub_date):
        pass  # Comic no longer published

########NEW FILE########
__FILENAME__ = boxerhockey
from comics.aggregator.crawler import CrawlerBase, CrawlerImage
from comics.core.comic_data import ComicDataBase


class ComicData(ComicDataBase):
    name = 'Boxer Hockey'
    language = 'en'
    url = 'http://boxerhockey.fireball20xl.com/'
    start_date = '2007-11-25'
    rights = 'Tyson "Rittz" Hesse'


class Crawler(CrawlerBase):
    history_capable_days = 120
    time_zone = 'US/Pacific'

    def crawl(self, pub_date):
        feed = self.parse_feed(
            'http://boxerhockey.fireball20xl.com/inc/feed.php')
        for entry in feed.for_date(pub_date):
            title = entry.title
            page = self.parse_page(entry.id)
            url = page.src('img#comicimg')
            return CrawlerImage(url, title)

########NEW FILE########
__FILENAME__ = brandondraws
from comics.aggregator.crawler import CrawlerBase
from comics.core.comic_data import ComicDataBase


class ComicData(ComicDataBase):
    name = 'Brandon Draws'
    language = 'en'
    url = 'http://drawbrandondraw.com/'
    start_date = '2010-06-29'
    active = False
    rights = 'Brandon B, CC BY-NC-SA 3.0'


class Crawler(CrawlerBase):
    def crawl(self, pub_date):
        pass  # Comic no longer published

########NEW FILE########
__FILENAME__ = brinkerhoff
from comics.aggregator.crawler import CrawlerBase
from comics.core.comic_data import ComicDataBase


class ComicData(ComicDataBase):
    name = 'Brinkerhoff'
    language = 'en'
    url = 'http://www.brinkcomic.com/'
    active = False
    start_date = '2006-01-02'
    end_date = '2009-12-30'
    rights = 'Gabe Strine'


class Crawler(CrawlerBase):
    def crawl(self, pub_date):
        pass  # Comic no longer published

########NEW FILE########
__FILENAME__ = bugcomic
from comics.aggregator.crawler import CrawlerBase, CrawlerImage
from comics.core.comic_data import ComicDataBase


class ComicData(ComicDataBase):
    name = 'Bug Martini'
    language = 'en'
    url = 'http://www.bugmartini.com/'
    start_date = '2009-10-19'
    rights = 'Adam Huber'


class Crawler(CrawlerBase):
    history_capable_days = 15
    schedule = 'Mo,Tu,We,Th,Fr'
    time_zone = 'US/Mountain'

    def crawl(self, pub_date):
        feed = self.parse_feed('http://www.bugmartini.com/feed/')
        for entry in feed.for_date(pub_date):
            title = entry.title
            url = entry.summary.src('img[src*="/wp-content/uploads/"]')
            if url:
                url = url.replace('?resize=520%2C280', '')
            return CrawlerImage(url, title)

########NEW FILE########
__FILENAME__ = bunny
from comics.aggregator.crawler import CrawlerBase
from comics.core.comic_data import ComicDataBase


class ComicData(ComicDataBase):
    name = 'Bunny'
    language = 'en'
    url = 'http://bunny-comic.com/'
    start_date = '2004-08-22'
    end_date = '2011-11-20'
    active = False
    rights = 'H. Davies, CC BY-NC-SA'


class Crawler(CrawlerBase):
    def crawl(self, pub_date):
        pass  # Comic no longer published

########NEW FILE########
__FILENAME__ = butternutsquash
# encoding: utf-8

from comics.aggregator.crawler import CrawlerBase
from comics.core.comic_data import ComicDataBase


class ComicData(ComicDataBase):
    name = 'Butternutsquash'
    language = 'en'
    url = 'http://www.butternutsquash.net/'
    active = False
    start_date = '2003-04-16'
    end_date = '2010-03-18'
    rights = 'Ramón Pérez & Rob Coughler'


class Crawler(CrawlerBase):
    def crawl(self, pub_date):
        pass  # Comic no longer published

########NEW FILE########
__FILENAME__ = buttersafe
from comics.aggregator.crawler import CrawlerBase, CrawlerImage
from comics.core.comic_data import ComicDataBase


class ComicData(ComicDataBase):
    name = 'Buttersafe'
    language = 'en'
    url = 'http://buttersafe.com/'
    start_date = '2007-04-03'
    rights = 'Alex Culang & Raynato Castro'


class Crawler(CrawlerBase):
    history_capable_days = 90
    schedule = 'Th'
    time_zone = 'US/Eastern'

    def crawl(self, pub_date):
        feed = self.parse_feed(
            'http://feeds.feedburner.com/Buttersafe?format=xml')
        for entry in feed.for_date(pub_date):
            url = entry.summary.src('img[src*="/comics/"]')
            if not url:
                continue
            url = url.replace('/rss/', '/').replace('RSS.jpg', '.jpg')
            title = entry.title
            return CrawlerImage(url, title)

########NEW FILE########
__FILENAME__ = calamitiesofnature
from comics.aggregator.crawler import CrawlerBase
from comics.core.comic_data import ComicDataBase


class ComicData(ComicDataBase):
    name = 'Calamities of Nature'
    language = 'en'
    url = 'http://www.calamitiesofnature.com/'
    active = False
    start_date = '2007-12-11'
    end_date = '2012-03-12'
    rights = 'Tony Piro'


class Crawler(CrawlerBase):
    def crawl(self, pub_date):
        pass  # Comic no longer published

########NEW FILE########
__FILENAME__ = calvinandhobbes
from comics.aggregator.crawler import GoComicsComCrawlerBase
from comics.core.comic_data import ComicDataBase


class ComicData(ComicDataBase):
    name = 'Calvin and Hobbes'
    language = 'en'
    url = 'http://www.gocomics.com/calvinandhobbes'
    start_date = '1985-11-18'
    end_date = '1995-12-31'
    rights = 'Bill Watterson'


class Crawler(GoComicsComCrawlerBase):
    history_capable_days = 31
    schedule = 'Mo,Tu,We,Th,Fr,Sa,Su'
    time_zone = 'US/Mountain'

    def crawl(self, pub_date):
        return self.crawl_helper('Calvin and Hobbes', pub_date)

########NEW FILE########
__FILENAME__ = carpediem
from comics.aggregator.crawler import PondusNoCrawlerBase
from comics.core.comic_data import ComicDataBase


class ComicData(ComicDataBase):
    name = 'Carpe Diem (pondus.no)'
    language = 'no'
    url = 'http://www.pondus.no/'
    rights = 'Nikklas Eriksson'
    active = False


class Crawler(PondusNoCrawlerBase):
    def crawl(self, pub_date):
        pass  # Comic no longer published

########NEW FILE########
__FILENAME__ = chainsawsuit
from comics.aggregator.crawler import CrawlerBase, CrawlerImage
from comics.core.comic_data import ComicDataBase


class ComicData(ComicDataBase):
    name = 'chainsawsuit'
    language = 'en'
    url = 'http://chainsawsuit.com/'
    start_date = '2008-03-12'
    rights = 'Kris Straub'


class Crawler(CrawlerBase):
    history_capable_days = 30
    schedule = 'Mo,We,Fr'
    time_zone = 'US/Pacific'

    def crawl(self, pub_date):
        feed = self.parse_feed('http://chainsawsuit.com/feed/')
        for entry in feed.for_date(pub_date):
            url = entry.summary.src('img[src*="/wp-content/uploads/"]')
            title = entry.title
            return CrawlerImage(url, title)

########NEW FILE########
__FILENAME__ = charliehorse
from comics.aggregator.crawler import CrawlerBase
from comics.core.comic_data import ComicDataBase


class ComicData(ComicDataBase):
    name = 'Charliehorse'
    language = 'en'
    url = 'http://www.krakowstudios.com/'
    active = False
    start_date = '2009-01-01'
    end_date = '2010-02-27'
    rights = 'Iron Muse Media'


class Crawler(CrawlerBase):
    def crawl(self, pub_date):
        pass  # Comic no longer published

########NEW FILE########
__FILENAME__ = choppingblock
from comics.aggregator.crawler import CrawlerBase, CrawlerImage
from comics.core.comic_data import ComicDataBase


class ComicData(ComicDataBase):
    name = 'Chopping Block'
    language = 'en'
    url = 'http://choppingblock.keenspot.com/'
    start_date = '2000-07-25'
    end_date = '2012-08-22'
    active = False
    rights = 'Lee Adam Herold'


class Crawler(CrawlerBase):
    def crawl(self, pub_date):
        pass  # Comic no longer published

########NEW FILE########
__FILENAME__ = completelyseriouscomics
from comics.aggregator.crawler import CrawlerBase, CrawlerImage
from comics.core.comic_data import ComicDataBase


class ComicData(ComicDataBase):
    name = 'Completely Serious Comics'
    language = 'en'
    url = 'http://completelyseriouscomics.com/'
    start_date = '2010-12-30'
    rights = 'Jesse'


class Crawler(CrawlerBase):
    history_capable_days = 90
    time_zone = 'US/Pacific'

    def crawl(self, pub_date):
        feed = self.parse_feed('http://completelyseriouscomics.com/?feed=rss2')
        for entry in feed.for_date(pub_date):
            if 'Comic' not in entry.tags:
                continue
            url = entry.summary.src('img')
            url = url.replace('comics-rss', 'comics')
            title = entry.title
            text = entry.summary.title('img')
            return CrawlerImage(url, title, text)

########NEW FILE########
__FILENAME__ = countyoursheep
from comics.aggregator.crawler import CrawlerBase
from comics.core.comic_data import ComicDataBase


class ComicData(ComicDataBase):
    name = 'Count Your Sheep'
    language = 'en'
    url = 'http://www.countyoursheep.com/'
    start_date = '2003-06-11'
    end_date = '2011-12-07'
    active = False
    rights = 'Adrian "Adis" Ramos'


class Crawler(CrawlerBase):
    def crawl(self, pub_date):
        pass  # Comic no longer published

########NEW FILE########
__FILENAME__ = crfh
from comics.aggregator.crawler import CrawlerBase, CrawlerImage
from comics.core.comic_data import ComicDataBase


class ComicData(ComicDataBase):
    name = 'Colleges Roomies from Hell'
    language = 'en'
    url = 'http://www.crfh.net/'
    start_date = '1999-01-01'
    rights = 'Maritza Campos'


class Crawler(CrawlerBase):
    history_capable_date = '1999-01-01'
    time_zone = 'America/Merida'

    def crawl(self, pub_date):
        page_url = 'http://www.crfh.net/d2/%s.html' % (
            pub_date.strftime('%Y%m%d'),)
        page = self.parse_page(page_url)
        url = page.src('img[src*="crfh%s"]' % pub_date.strftime('%Y%m%d'))
        url = url.replace('\n', '')
        return CrawlerImage(url)

########NEW FILE########
__FILENAME__ = crookedgremlins
from comics.aggregator.crawler import CrawlerBase, CrawlerImage
from comics.core.comic_data import ComicDataBase


class ComicData(ComicDataBase):
    name = 'Crooked Gremlins'
    language = 'en'
    url = 'http://www.crookedgremlins.com/'
    start_date = '2008-04-01'
    rights = 'Carter Fort and Paul Lucci'


class Crawler(CrawlerBase):
    history_capable_days = 180
    time_zone = 'US/Pacific'

    def crawl(self, pub_date):
        feed = self.parse_feed('http://crookedgremlins.com/feed/')
        for entry in feed.for_date(pub_date):
            if not 'Comics' in entry.tags:
                continue
            title = entry.title
            url = entry.summary.src('img[src*="/comics/"]')

            # Put together the text from multiple paragraphs
            text_paragraphs = entry.summary.text('p', allow_multiple=True)
            if text_paragraphs is not None:
                text = '\n\n'.join(text_paragraphs)
            else:
                text = None

            return CrawlerImage(url, title, text)

########NEW FILE########
__FILENAME__ = ctrlaltdel
from comics.aggregator.crawler import CrawlerBase, CrawlerImage
from comics.core.comic_data import ComicDataBase


class ComicData(ComicDataBase):
    name = 'Ctrl+Alt+Del'
    language = 'en'
    url = 'http://www.cad-comic.com/cad/'
    start_date = '2002-10-23'
    rights = 'Tim Buckley'


class Crawler(CrawlerBase):
    history_capable_date = '2002-10-23'
    schedule = 'Mo,We,Fr'
    time_zone = 'US/Eastern'

     # Without User-Agent set, the server returns empty responses
    headers = {'User-Agent': 'Mozilla/4.0'}

    def crawl(self, pub_date):
        page = self.parse_page(
            'http://www.cad-comic.com/cad/%s' % pub_date.strftime('%Y%m%d'))
        url = page.src('img[src*="/comics/"]')
        title = page.alt('img[src*="/comics/"]')
        return CrawlerImage(url, title)

########NEW FILE########
__FILENAME__ = ctrlaltdelsillies
from comics.aggregator.crawler import CrawlerBase, CrawlerImage
from comics.core.comic_data import ComicDataBase


class ComicData(ComicDataBase):
    name = 'Ctrl+Alt+Del Sillies'
    language = 'en'
    url = 'http://www.cad-comic.com/sillies/'
    start_date = '2008-06-27'
    rights = 'Tim Buckley'


class Crawler(CrawlerBase):
    history_capable_date = '2008-06-27'
    schedule = None
    time_zone = 'US/Eastern'

     # Without User-Agent set, the server returns empty responses
    headers = {'User-Agent': 'Mozilla/4.0'}

    def crawl(self, pub_date):
        page = self.parse_page(
            'http://www.cad-comic.com/sillies/%s' %
            pub_date.strftime('%Y%m%d'))
        url = page.src('img[src*="/comics/"]')
        return CrawlerImage(url)

########NEW FILE########
__FILENAME__ = cyanideandhappiness
from comics.aggregator.crawler import CrawlerBase, CrawlerImage
from comics.core.comic_data import ComicDataBase


class ComicData(ComicDataBase):
    name = 'Cyanide and Happiness'
    language = 'en'
    url = 'http://www.explosm.net/comics/'
    start_date = '2005-01-26'
    rights = 'Kris Wilson, Rob DenBleyker, Matt Melvin, & Dave McElfatrick '


class Crawler(CrawlerBase):
    history_capable_days = 7
    schedule = 'Mo,Tu,We,Fr,Sa,Su'
    time_zone = 'US/Pacific'

    def crawl(self, pub_date):
        feed = self.parse_feed('http://feeds.feedburner.com/Explosm')
        for entry in feed.for_date(pub_date):
            page = self.parse_page(entry.link)
            url = page.src(
                'img[alt="Cyanide and Happiness, a daily webcomic"]')
            return CrawlerImage(url)

########NEW FILE########
__FILENAME__ = darklegacy
from comics.aggregator.crawler import CrawlerBase, CrawlerImage
from comics.core.comic_data import ComicDataBase


class ComicData(ComicDataBase):
    name = 'Dark Legacy'
    language = 'en'
    url = 'http://www.darklegacycomics.com/'
    start_date = '2006-01-01'
    rights = 'Arad Kedar'


class Crawler(CrawlerBase):
    history_capable_date = '2006-12-09'
    time_zone = 'US/Pacific'

    def crawl(self, pub_date):
        feed = self.parse_feed('http://www.darklegacycomics.com/feed.xml')
        for entry in feed.for_date(pub_date):
            title = entry.title
            url = entry.link.replace('.html', '.jpg')
            return CrawlerImage(url, title)

########NEW FILE########
__FILENAME__ = darthsanddroids
from comics.aggregator.crawler import CrawlerBase, CrawlerImage
from comics.core.comic_data import ComicDataBase


class ComicData(ComicDataBase):
    name = 'Darths & Droids'
    language = 'en'
    url = 'http://darthsanddroids.net/'
    start_date = '2007-09-14'
    rights = 'The Comic Irregulars'


class Crawler(CrawlerBase):
    history_capable_days = 14
    schedule = 'Tu,Th,Su'
    time_zone = 'US/Pacific'

    def crawl(self, pub_date):
        feed = self.parse_feed('http://darthsanddroids.net/rss.xml')
        for entry in feed.for_date(pub_date):
            if entry.title.startswith('Episode'):
                url = entry.summary.src('img')
                title = entry.title
                return CrawlerImage(url, title)

########NEW FILE########
__FILENAME__ = darylcagle
from comics.aggregator.crawler import CrawlerBase, CrawlerImage
from comics.core.comic_data import ComicDataBase


class ComicData(ComicDataBase):
    name = "Daryl Cagle's Political Blog"
    language = 'en'
    url = 'http://www.cagle.com/'
    start_date = '2001-01-04'
    rights = 'Daryl Cagle'


class Crawler(CrawlerBase):
    history_capable_days = 365
    time_zone = 'US/Pacific'

    def crawl(self, pub_date):
        feed = self.parse_feed('http://www.cagle.com/author/daryl-cagle/feed/')
        for entry in feed.for_date(pub_date):
            if 'Cartoons' not in entry.tags:
                continue
            url = entry.summary.src('img')
            title = entry.title
            return CrawlerImage(url, title)

########NEW FILE########
__FILENAME__ = deepfried
from comics.aggregator.crawler import CrawlerBase, CrawlerImage
from comics.core.comic_data import ComicDataBase


class ComicData(ComicDataBase):
    name = 'Deep Fried'
    language = 'en'
    url = 'http://www.whatisdeepfried.com/'
    start_date = '2001-09-16'
    rights = 'Jason Yungbluth'


class Crawler(CrawlerBase):
    history_capable_days = 14
    schedule = None
    time_zone = 'US/Eastern'

    def crawl(self, pub_date):
        feed = self.parse_feed('http://www.whatisdeepfried.com/feed/')
        for entry in feed.for_date(pub_date):
            url = entry.summary.src('img')
            title = entry.title
            return CrawlerImage(url, title)

########NEW FILE########
__FILENAME__ = devilbear
from comics.aggregator.crawler import CrawlerBase, CrawlerImage
from comics.core.comic_data import ComicDataBase


class ComicData(ComicDataBase):
    name = 'The Devil Bear'
    language = 'en'
    url = 'http://www.thedevilbear.com/'
    start_date = '2009-01-01'
    rights = 'Ben Bourbon'


class Crawler(CrawlerBase):
    history_capable_days = 0
    time_zone = 'US/Eastern'

    def crawl(self, pub_date):
        page = self.parse_page('http://www.thedevilbear.com/')
        url = page.src('#cg_img img')
        return CrawlerImage(url)

########NEW FILE########
__FILENAME__ = dieselsweetiesprint
from comics.aggregator.crawler import CrawlerBase
from comics.core.comic_data import ComicDataBase


class ComicData(ComicDataBase):
    name = 'Diesel Sweeties (print)'
    language = 'en'
    url = 'http://www.dieselsweeties.com/'
    active = False
    start_date = '2007-01-01'
    end_date = '2008-08-14'
    rights = 'Richard Stevens'


class Crawler(CrawlerBase):
    def crawl(self, pub_date):
        pass  # Comic no longer published

########NEW FILE########
__FILENAME__ = dieselsweetiesweb
from comics.aggregator.crawler import CrawlerBase, CrawlerImage
from comics.core.comic_data import ComicDataBase


class ComicData(ComicDataBase):
    name = 'Diesel Sweeties (web)'
    language = 'en'
    url = 'http://www.dieselsweeties.com/'
    start_date = '2000-01-01'
    rights = 'Richard Stevens'


class Crawler(CrawlerBase):
    history_capable_date = '2000-01-01'
    schedule = 'Mo,Tu,We,Th,Fr'
    time_zone = 'US/Eastern'

    def crawl(self, pub_date):
        feed = self.parse_feed('http://www.dieselsweeties.com/ds-unifeed.xml')
        for entry in feed.for_date(pub_date):
            if not hasattr(entry, 'summary'):
                continue
            url = entry.summary.src('img[src*="/strips/"]')
            title = entry.title
            text = entry.summary.alt('img[src*="/strips/"]')
            return CrawlerImage(url, title, text)

########NEW FILE########
__FILENAME__ = dilbert
from comics.aggregator.crawler import CrawlerBase, CrawlerImage
from comics.core.comic_data import ComicDataBase


class ComicData(ComicDataBase):
    name = 'Dilbert'
    language = 'en'
    url = 'http://www.dilbert.com/'
    start_date = '1989-04-16'
    rights = 'Scott Adams'


class Crawler(CrawlerBase):
    history_capable_date = '1989-04-16'
    schedule = 'Mo,Tu,We,Th,Fr,Sa,Su'
    time_zone = 'US/Mountain'

    def crawl(self, pub_date):
        page = self.parse_page(
            pub_date.strftime('http://dilbert.com/strips/comic/%Y-%m-%d/'))
        url = page.src('img[src$=".strip.zoom.gif"]')
        return CrawlerImage(url)

########NEW FILE########
__FILENAME__ = dilbertbt
from comics.aggregator.crawler import CrawlerBase
from comics.core.comic_data import ComicDataBase


class ComicData(ComicDataBase):
    name = 'Dilbert (bt.no)'
    language = 'no'
    url = 'http://www.bt.no/tegneserier/dilbert/'
    active = False
    start_date = '1989-04-16'
    rights = 'Scott Adams'


class Crawler(CrawlerBase):
    def crawl(self, pub_date):
        pass  # Comic no longer published

########NEW FILE########
__FILENAME__ = dilbertvg
from comics.aggregator.crawler import CrawlerBase, CrawlerImage
from comics.core.comic_data import ComicDataBase


class ComicData(ComicDataBase):
    name = 'Dilbert (vg.no)'
    language = 'no'
    url = 'http://heltnormalt.no/dilbert'
    start_date = '1989-04-16'
    rights = 'Scott Adams'


class Crawler(CrawlerBase):
    history_capable_date = '2013-02-01'
    schedule = 'Mo,Tu,We,Th,Fr,Sa,Su'
    time_zone = 'Europe/Oslo'

    def crawl(self, pub_date):
        url = 'http://heltnormalt.no/img/dilbert/%s.jpg' % (
            pub_date.strftime('%Y/%m/%d'))
        return CrawlerImage(url)

########NEW FILE########
__FILENAME__ = dinosaur
from comics.aggregator.crawler import CrawlerBase, CrawlerImage
from comics.core.comic_data import ComicDataBase


class ComicData(ComicDataBase):
    name = 'Dinosaur Comics'
    language = 'en'
    url = 'http://www.qwantz.com/'
    start_date = '2003-02-01'
    rights = 'Ryan North'


class Crawler(CrawlerBase):
    history_capable_days = 32
    schedule = 'Mo,Tu,We,Th,Fr'
    time_zone = 'US/Eastern'

    def crawl(self, pub_date):
        feed = self.parse_feed('http://www.rsspect.com/rss/qwantz.xml')
        for entry in feed.for_date(pub_date):
            url = entry.summary.src('img[src*="/comics/"]')
            title = entry.title
            text = entry.summary.title('img[src*="/comics/"]')
            return CrawlerImage(url, title, text)

########NEW FILE########
__FILENAME__ = doghouse
from comics.aggregator.crawler import CrawlerBase, CrawlerImage
from comics.core.comic_data import ComicDataBase


class ComicData(ComicDataBase):
    name = 'The Doghouse Diaries'
    language = 'en'
    url = 'http://www.thedoghousediaries.com/'
    start_date = '2009-01-08'
    rights = 'Will, Ray, & Raf'


class Crawler(CrawlerBase):
    history_capable_days = 30
    schedule = 'Mo,We,Fr'
    time_zone = 'US/Pacific'

    def crawl(self, pub_date):
        feed = self.parse_feed(
            'http://feeds.feedburner.com/thedoghousediaries/feed')
        for entry in feed.for_date(pub_date):
            url = entry.content0.src('img[src*="/comics/"]')
            title = entry.content0.alt('img[src*="/comics/"]')
            text = entry.content0.title('img[src*="/comics/"]')
            return CrawlerImage(url, title, text)

########NEW FILE########
__FILENAME__ = dresdencodak
from comics.aggregator.crawler import CrawlerBase, CrawlerImage
from comics.core.comic_data import ComicDataBase


class ComicData(ComicDataBase):
    name = 'Dresden Codak'
    language = 'en'
    url = 'http://www.dresdencodak.com/'
    start_date = '2007-02-08'
    rights = 'Aaron Diaz'


class Crawler(CrawlerBase):
    history_capable_days = 180
    time_zone = 'US/Pacific'

    def crawl(self, pub_date):
        feed = self.parse_feed('http://feeds.feedburner.com/rsspect/fJur')
        for entry in feed.for_date(pub_date):
            if 'Comics' in entry.tags:
                page = self.parse_page(entry.link)
                url = page.src('#comic img')
                title = entry.title

                text = ''
                for paragraph in entry.content0.text('p', allow_multiple=True):
                    text += paragraph + '\n\n'
                text = text.strip()

                return CrawlerImage(url, title, text)

########NEW FILE########
__FILENAME__ = drmcninja
from comics.aggregator.crawler import CrawlerBase, CrawlerImage
from comics.core.comic_data import ComicDataBase


class ComicData(ComicDataBase):
    name = 'The Adventures of Dr. McNinja'
    language = 'en'
    url = 'http://drmcninja.com/'
    start_date = '2004-08-03'
    rights = 'Christopher Hastings'


class Crawler(CrawlerBase):
    history_capable_days = 32
    schedule = 'Mo,We,Fr'
    time_zone = 'US/Eastern'

    def crawl(self, pub_date):
        feed = self.parse_feed('http://drmcninja.com/feed')
        for entry in feed.for_date(pub_date):
            if not '/comic/' in entry.link:
                continue
            url = entry.summary.src('img[src*="/comics-rss/"]')
            url = url.replace('comics-rss', 'comics')
            title = entry.title
            text = entry.summary.title('img[src*="/comics-rss/"]')
            return CrawlerImage(url, title, text)

########NEW FILE########
__FILENAME__ = duelinganalogs
from comics.aggregator.crawler import CrawlerBase, CrawlerImage
from comics.core.comic_data import ComicDataBase


class ComicData(ComicDataBase):
    name = 'Dueling Analogs'
    language = 'en'
    url = 'http://www.duelinganalogs.com/'
    start_date = '2005-11-17'
    rights = 'Steve Napierski'


class Crawler(CrawlerBase):
    history_capable_days = 35
    schedule = 'Mo,Th'
    time_zone = 'US/Pacific'

    def crawl(self, pub_date):
        feed = self.parse_feed('http://feeds.feedburner.com/DuelingAnalogs')
        for entry in feed.for_date(pub_date):
            url = entry.content0.src('img[src*="/wp-content/uploads/"]')
            title = entry.title
            return CrawlerImage(url, title)

########NEW FILE########
__FILENAME__ = dungeond
from comics.aggregator.crawler import CrawlerBase, CrawlerImage
from comics.core.comic_data import ComicDataBase


class ComicData(ComicDataBase):
    name = 'Dungeons & Denizens'
    language = 'en'
    url = 'http://dungeond.com/'
    start_date = '2005-08-23'
    rights = 'Graveyard Greg'


class Crawler(CrawlerBase):
    history_capable_days = 365
    schedule = 'Tu'
    time_zone = 'US/Pacific'

    def crawl(self, pub_date):
        feed = self.parse_feed('http://dungeond.com/feed/')
        for entry in feed.for_date(pub_date):
            url = entry.summary.src('img')
            if url:
                url = url.replace('comics-rss', 'comics')
            title = entry.title
            paragraphs = entry.content0.text('p', allow_multiple=True)
            text = '\n\n'.join(paragraphs)
            return CrawlerImage(url, title, text)

########NEW FILE########
__FILENAME__ = dustin
from comics.aggregator.crawler import ArcaMaxCrawlerBase
from comics.core.comic_data import ComicDataBase


class ComicData(ComicDataBase):
    name = 'Dustin'
    language = 'en'
    url = 'http://www.arcamax.com/thefunnies/dustin/'
    start_date = '2010-01-04'
    rights = 'Steve Kelley & Jeff Parker'


class Crawler(ArcaMaxCrawlerBase):
    history_capable_days = 0
    schedule = 'Mo,Tu,We,Th,Fr,Sa,Su'
    time_zone = 'US/Eastern'

    def crawl(self, pub_date):
        return self.crawl_helper('dustin', pub_date)

########NEW FILE########
__FILENAME__ = eatthattoast
import re

from comics.aggregator.crawler import CrawlerBase, CrawlerImage
from comics.core.comic_data import ComicDataBase


class ComicData(ComicDataBase):
    name = 'Eat That Toast!'
    language = 'en'
    url = 'http://eatthattoast.com/'
    start_date = '2010-06-14'
    rights = 'Matt Czapiewski'


class Crawler(CrawlerBase):
    history_capable_days = 90
    time_zone = 'US/Eastern'

    def crawl(self, pub_date):
        page = self.parse_page('http://eatthattoast.com/')
        url = page.src('#comic img')
        if url:
            title = page.text('.comicpress_comic_title_widget a')
            text = page.alt('#comic img')
            matches = re.match(r'.*(\d{4}-\d{2}-\d{2}).*', url)
            if matches and matches.groups()[0] == pub_date.isoformat():
                return CrawlerImage(url, title, text)

########NEW FILE########
__FILENAME__ = eon
from comics.aggregator.crawler import PondusNoCrawlerBase
from comics.core.comic_data import ComicDataBase


class ComicData(ComicDataBase):
    name = 'EON'
    language = 'no'
    url = 'http://www.pondus.no/'
    start_date = '2008-11-19'
    active = False
    rights = 'Lars Lauvik'


class Crawler(PondusNoCrawlerBase):
    def crawl(self, pub_date):
        pass  # Comic no longer published

########NEW FILE########
__FILENAME__ = evilinc
from comics.aggregator.crawler import CrawlerBase, CrawlerImage
from comics.core.comic_data import ComicDataBase


class ComicData(ComicDataBase):
    name = 'Evil Inc.'
    language = 'en'
    url = 'http://evil-inc.com/'
    start_date = '2005-05-30'
    rights = 'Brad J. Guigar - Colorist: Ed Ryzowski'


class Crawler(CrawlerBase):
    history_capable_date = '2005-05-30'
    schedule = 'Mo,Tu,We,Th,Fr'
    time_zone = 'US/Eastern'

    def crawl(self, pub_date):
        page_url = 'http://evil-inc.com/%s/?post_type=comic' % (
            pub_date.strftime('%Y/%m/%d'))

        page = self.parse_page(page_url)

        url = page.src('img.attachment-large.wp-post-image')
        if not url:
            return
        url = url.replace('?fit=1024%2C1024', '')
        title = page.text('.post-title')
        return CrawlerImage(url, title)

########NEW FILE########
__FILENAME__ = exiern
from comics.aggregator.crawler import CrawlerBase, CrawlerImage
from comics.core.comic_data import ComicDataBase


class ComicData(ComicDataBase):
    name = 'Exiern'
    language = 'en'
    url = 'http://www.exiern.com/'
    start_date = '2005-09-06'
    rights = 'Dan Standing'


class Crawler(CrawlerBase):
    history_capable_days = 30
    schedule = 'Tu,Th'
    time_zone = 'US/Eastern'

    def crawl(self, pub_date):
        feed = self.parse_feed('http://www.exiern.com/?feed=rss2')
        for entry in feed.for_date(pub_date):
            url = entry.summary.src('img', allow_multiple=True)
            if url:
                url = url[0]
                url = url.replace('comics-rss', 'comics')
            title = entry.title
            return CrawlerImage(url, title)

########NEW FILE########
__FILENAME__ = extralife
from comics.aggregator.crawler import CrawlerBase, CrawlerImage
from comics.core.comic_data import ComicDataBase


class ComicData(ComicDataBase):
    name = 'ExtraLife'
    language = 'en'
    url = 'http://www.myextralife.com/'
    start_date = '2001-06-17'
    rights = 'Scott Johnson'


class Crawler(CrawlerBase):
    history_capable_days = 32
    schedule = 'Mo'
    time_zone = 'US/Mountain'

     # Without User-Agent set, the server returns empty responses
    headers = {'User-Agent': 'Mozilla/4.0'}

    def crawl(self, pub_date):
        feed = self.parse_feed(
            'http://www.myextralife.com/category/comic/feed/')
        for entry in feed.for_date(pub_date):
            url = entry.content0.src('img[src*="/wp-content/"]')
            title = entry.title
            return CrawlerImage(url, title)

########NEW FILE########
__FILENAME__ = extraordinary
from comics.aggregator.crawler import CrawlerBase, CrawlerImage
from comics.core.comic_data import ComicDataBase


class ComicData(ComicDataBase):
    name = 'Extra Ordinary'
    language = 'en'
    url = 'http://www.exocomics.com/'
    start_date = '2009-12-14'
    rights = 'Li Chen'


class Crawler(CrawlerBase):
    history_capable_days = 90
    schedule = 'We'
    time_zone = 'Pacific/Auckland'

    # Without Referer set, the server returns 403 Forbidden
    headers = {'Referer': 'http://www.exocomics.com/'}

    def crawl(self, pub_date):
        feed = self.parse_feed('http://www.exocomics.com/feed')
        for entry in feed.for_date(pub_date):
            title = entry.title
            page = self.parse_page(entry.link)
            url = page.src('.comic img')
            text = page.title('.comic img')
            return CrawlerImage(url, title, text)

########NEW FILE########
__FILENAME__ = fagprat
# encoding: utf-8

from comics.aggregator.crawler import CrawlerBase, CrawlerImage
from comics.core.comic_data import ComicDataBase


class ComicData(ComicDataBase):
    name = 'Fagprat (db.no)'
    language = 'no'
    url = 'http://www.dagbladet.no/tegneserie/fagprat'
    rights = 'Flu Hartberg'


class Crawler(CrawlerBase):
    history_capable_date = '2010-11-15'
    schedule = 'Tu,Th,Sa'
    time_zone = 'Europe/Oslo'

    def crawl(self, pub_date):
        epoch = self.date_to_epoch(pub_date)
        page_url = 'http://www.dagbladet.no/tegneserie/fagprat/?%s' % epoch
        page = self.parse_page(page_url)
        url = page.src('img#fagprat-stripe')
        return CrawlerImage(url)

########NEW FILE########
__FILENAME__ = faktafraverden
# encoding: utf-8

from comics.aggregator.crawler import CrawlerBase
from comics.core.comic_data import ComicDataBase


class ComicData(ComicDataBase):
    name = 'Fakta fra verden'
    language = 'no'
    url = 'http://www.dagbladet.no/tegneserie/faktafraverden/'
    active = False
    start_date = '2001-01-01'
    rights = 'Karstein Volle'


class Crawler(CrawlerBase):
    def crawl(self, pub_date):
        pass  # Comic no longer published

########NEW FILE########
__FILENAME__ = fanboys
from comics.aggregator.crawler import CrawlerBase, CrawlerImage
from comics.core.comic_data import ComicDataBase


class ComicData(ComicDataBase):
    name = 'F@NB0Y$'
    language = 'en'
    url = 'http://www.fanboys-online.com/'
    start_date = '2006-04-19'
    rights = 'Scott Dewitt'


class Crawler(CrawlerBase):
    history_capable_days = 180
    schedule = 'Mo,Fr'
    time_zone = 'US/Eastern'

    def crawl(self, pub_date):
        feed = self.parse_feed('http://www.fanboys-online.com/rss.php')
        for entry in feed.for_date(pub_date):
            title = entry.title.replace('Fanboys - ', '')
            page = self.parse_page(entry.link)
            url = page.src('img#comic')
            if not url:
                continue
            url = url.replace(' ', '%20')
            return CrawlerImage(url, title)

########NEW FILE########
__FILENAME__ = fminus
from comics.aggregator.crawler import GoComicsComCrawlerBase
from comics.core.comic_data import ComicDataBase


class ComicData(ComicDataBase):
    name = 'F Minus'
    language = 'en'
    url = 'http://www.gocomics.com/fminus'
    start_date = '1999-09-01'
    rights = 'Tony Carrillo'


class Crawler(GoComicsComCrawlerBase):
    history_capable_date = '2001-02-02'
    schedule = 'Mo,Tu,We,Th,Fr,Sa,Su'
    time_zone = 'US/Mountain'

    def crawl(self, pub_date):
        return self.crawl_helper('F Minus', pub_date)

########NEW FILE########
__FILENAME__ = focusshift
from comics.aggregator.crawler import CrawlerBase
from comics.core.comic_data import ComicDataBase


class ComicData(ComicDataBase):
    name = 'Focus Shift'
    language = 'en'
    url = 'http://www.osnews.com/comics/'
    active = False
    start_date = '2008-01-27'
    rights = 'Thom Holwerda'


class Crawler(CrawlerBase):
    def crawl(self, pub_date):
        pass  # Comic no longer published

########NEW FILE########
__FILENAME__ = forbetterorforworse
from comics.aggregator.crawler import GoComicsComCrawlerBase
from comics.core.comic_data import ComicDataBase


class ComicData(ComicDataBase):
    name = 'For Better or For Worse'
    language = 'en'
    url = 'http://www.gocomics.com/forbetterorforworse'
    start_date = '1981-11-23'
    rights = 'Lynn Johnston'


class Crawler(GoComicsComCrawlerBase):
    history_capable_date = '1981-11-23'
    schedule = 'Mo,Tu,We,Th,Fr,Sa,Su'
    time_zone = 'US/Eastern'

    def crawl(self, pub_date):
        return self.crawl_helper('For Better or For Worse', pub_date)

########NEW FILE########
__FILENAME__ = foxtrot
from comics.aggregator.crawler import GoComicsComCrawlerBase
from comics.core.comic_data import ComicDataBase


class ComicData(ComicDataBase):
    name = 'FoxTrot'
    language = 'en'
    url = 'http://www.gocomics.com/foxtrot'
    start_date = '1988-04-10'
    rights = 'Bill Amend'


class Crawler(GoComicsComCrawlerBase):
    history_capable_date = '2006-12-27'
    schedule = 'Su'
    time_zone = 'US/Mountain'

    def crawl(self, pub_date):
        return self.crawl_helper('FoxTrot', pub_date)

########NEW FILE########
__FILENAME__ = garfield
from comics.aggregator.crawler import CrawlerBase, CrawlerImage
from comics.core.comic_data import ComicDataBase


class ComicData(ComicDataBase):
    name = 'Garfield'
    language = 'en'
    url = 'http://www.garfield.com/'
    start_date = '1978-06-19'
    rights = 'Jim Davis'


class Crawler(CrawlerBase):
    history_capable_days = 100
    schedule = 'Mo,Tu,We,Th,Fr,Sa,Su'
    time_zone = 'US/Eastern'

    def crawl(self, pub_date):
        if pub_date.weekday() == 6:
            url = 'http://picayune.uclick.com/comics/ga/%s.jpg' % (
                pub_date.strftime('%Y/ga%y%m%d'),)
        else:
            url = 'http://images.ucomics.com/comics/ga/%s.gif' % (
                pub_date.strftime('%Y/ga%y%m%d'),)
        return CrawlerImage(url)

########NEW FILE########
__FILENAME__ = garfieldminusgarfield
from comics.aggregator.crawler import CrawlerBase, CrawlerImage
from comics.core.comic_data import ComicDataBase


class ComicData(ComicDataBase):
    name = 'Garfield minus Garfield'
    language = 'en'
    url = 'http://garfieldminusgarfield.tumblr.com/'
    rights = 'Travors'


class Crawler(CrawlerBase):
    history_capable_days = 30
    schedule = None
    time_zone = 'Europe/London'

    def crawl(self, pub_date):
        feed = self.parse_feed('http://garfieldminusgarfield.tumblr.com/rss')
        for entry in feed.for_date(pub_date):
            url = entry.summary.src('img')
            return CrawlerImage(url)

########NEW FILE########
__FILENAME__ = geekandpoke
from comics.aggregator.crawler import CrawlerBase, CrawlerImage
from comics.core.comic_data import ComicDataBase


class ComicData(ComicDataBase):
    name = 'Geek and Poke'
    language = 'en'
    url = 'http://geek-and-poke.com/'
    start_date = '2006-08-22'
    rights = 'Oliver Widder, CC BY-ND 2.0'


class Crawler(CrawlerBase):
    history_capable_days = 90
    time_zone = 'Europe/Berlin'

    def crawl(self, pub_date):
        feed = self.parse_feed('http://feeds.feedburner.com/GeekAndPoke')
        for entry in feed.for_date(pub_date):
            url = entry.summary.src('img[src*="/static/"]')
            title = entry.title
            return CrawlerImage(url, title)

########NEW FILE########
__FILENAME__ = getfuzzy
from comics.aggregator.crawler import GoComicsComCrawlerBase
from comics.core.comic_data import ComicDataBase


class ComicData(ComicDataBase):
    name = 'Get Fuzzy'
    language = 'en'
    url = 'http://www.gocomics.com/getfuzzy/'
    start_date = '1999-09-01'
    rights = 'Darby Conley'


class Crawler(GoComicsComCrawlerBase):
    history_capable_date = '2009-05-26'
    schedule = 'Mo,Tu,We,Th,Fr,Sa,Su'
    time_zone = 'US/Mountain'

    def crawl(self, pub_date):
        return self.crawl_helper('Get Fuzzy', pub_date)

########NEW FILE########
__FILENAME__ = girlgenius
from comics.aggregator.crawler import CrawlerBase, CrawlerImage
from comics.core.comic_data import ComicDataBase


class ComicData(ComicDataBase):
    name = 'Girl Genius'
    language = 'en'
    url = 'http://www.girlgeniusonline.com/'
    start_date = '2002-11-04'
    rights = 'Studio Foglio, LLC'


class Crawler(CrawlerBase):
    history_capable_date = '2002-11-04'
    schedule = 'Mo,We,Fr'
    time_zone = 'US/Pacific'

    def crawl(self, pub_date):
        url = 'http://www.girlgeniusonline.com/ggmain/strips/ggmain%sb.jpg' % (
            pub_date.strftime('%Y%m%d'),)
        return CrawlerImage(url)

########NEW FILE########
__FILENAME__ = goblins
from comics.aggregator.crawler import CrawlerBase, CrawlerImage
from comics.core.comic_data import ComicDataBase


class ComicData(ComicDataBase):
    name = 'Goblins'
    language = 'en'
    url = 'http://www.goblinscomic.com/'
    start_date = '2005-05-29'
    rights = 'Tarol Hunt'


class Crawler(CrawlerBase):
    history_capable_days = 30
    time_zone = 'US/Pacific'

    def crawl(self, pub_date):
        feed = self.parse_feed('http://www.goblinscomic.com/feed/')
        for entry in feed.for_date(pub_date):
            if 'Comics' not in entry.tags:
                continue
            url = entry.summary.src('img[src*="/comics/"]')
            return CrawlerImage(url)

########NEW FILE########
__FILENAME__ = gpf
from comics.aggregator.crawler import CrawlerBase, CrawlerImage
from comics.core.comic_data import ComicDataBase


class ComicData(ComicDataBase):
    name = 'General Protection Fault'
    language = 'en'
    url = 'http://www.gpf-comics.com/'
    start_date = '1998-11-02'
    rights = 'Jeffrey T. Darlington'


class Crawler(CrawlerBase):
    history_capable_date = '1998-11-02'
    schedule = 'Mo,We,Fr'
    time_zone = 'US/Eastern'

    def crawl(self, pub_date):
        page_url = 'http://www.gpf-comics.com/archive.php?d=%s' % (
            pub_date.strftime('%Y%m%d'),)
        page = self.parse_page(page_url)
        url = page.src('img[alt^="[Comic for"]')
        return CrawlerImage(url)

########NEW FILE########
__FILENAME__ = gregcomic
from comics.aggregator.crawler import CrawlerBase, CrawlerImage
from comics.core.comic_data import ComicDataBase


class ComicData(ComicDataBase):
    name = 'Greg Comic'
    language = 'en'
    url = 'http://gregcomic.com/'
    start_date = '2011-06-01'
    rights = 'Chur Yin Wan'


class Crawler(CrawlerBase):
    history_capable_days = 180
    time_zone = 'US/Eastern'

    def crawl(self, pub_date):
        feed = self.parse_feed('http://gregcomic.com/feed/')
        for entry in feed.for_date(pub_date):
            if 'Comics' not in entry.tags:
                continue
            title = entry.title
            url = entry.summary.src('img[src*="/comics-rss/"]')
            if not url:
                continue
            url = url.replace('-rss', '')
            return CrawlerImage(url, title)

########NEW FILE########
__FILENAME__ = gucomics
import re

from comics.aggregator.crawler import CrawlerBase, CrawlerImage
from comics.core.comic_data import ComicDataBase


class ComicData(ComicDataBase):
    name = 'GU Comics'
    language = 'en'
    url = 'http://www.gucomics.com/'
    start_date = '2000-07-10'
    rights = 'Woody Hearn'


class Crawler(CrawlerBase):
    history_capable_date = '2000-07-10'
    schedule = 'Mo,We,Fr'
    time_zone = 'US/Eastern'

    def crawl(self, pub_date):
        page_url = 'http://www.gucomics.com/%s' % pub_date.strftime('%Y%m%d')
        page = self.parse_page(page_url)

        title = page.text('b', allow_multiple=True)[0]
        title = title.replace('"', '')
        title = title.strip()

        text = page.text('.main')

        #  If there is a "---", the text after is not about the comic
        text = text[:text.find('---')]
        # If there is a "[ ", the text after is not part of the text
        text = text[:text.find('[ ')]
        text = text.strip()
        # Reduce any amount of newlines down to two newlines
        text = text.replace('\r', '')
        text = re.sub('\s*\n\n\s*', '\n\n', text)

        url = page.src('img[alt^="Comic for"]')
        return CrawlerImage(url, title, text)

########NEW FILE########
__FILENAME__ = gunnerkrigg
from comics.aggregator.crawler import CrawlerBase, CrawlerImage
from comics.core.comic_data import ComicDataBase


class ComicData(ComicDataBase):
    name = 'Gunnerkrigg Court'
    language = 'en'
    url = 'http://www.gunnerkrigg.com/'
    start_date = '2005-08-13'
    rights = 'Tom Siddell'


class Crawler(CrawlerBase):
    schedule = 'Mo,We,Fr'
    time_zone = 'US/Pacific'

    def crawl(self, pub_date):
        page = self.parse_page('http://www.gunnerkrigg.com/index2.php')
        url = page.src('img[src*="/comics/"]')
        title = page.alt('img[src*="/comics/"]')
        text = ''
        for content in page.text(
                'table[cellpadding="5"] td', allow_multiple=True):
            text += content + '\n\n'
        text = text.strip()
        return CrawlerImage(url, title, text)

########NEW FILE########
__FILENAME__ = gunshow
from comics.aggregator.crawler import CrawlerBase, CrawlerImage
from comics.core.comic_data import ComicDataBase


class ComicData(ComicDataBase):
    name = 'Gun Show'
    language = 'en'
    url = 'http://www.gunshowcomic.com/'
    start_date = '2008-09-04'
    rights = '"Lord KC Green"'


class Crawler(CrawlerBase):
    history_capable_date = '2008-09-04'
    schedule = 'Mo,We,Fr'
    time_zone = 'US/Eastern'

    def crawl(self, pub_date):
        page_url = 'http://www.gunshowcomic.com/d/%s.html' % (
            pub_date.strftime('%Y%m%d'),)
        page = self.parse_page(page_url)
        urls = page.src(
            'img[src^="http://gunshowcomic.com/comics/"]', allow_multiple=True)
        return [CrawlerImage(url) for url in urls]

########NEW FILE########
__FILENAME__ = gws
from comics.aggregator.crawler import CrawlerBase, CrawlerImage
from comics.core.comic_data import ComicDataBase


class ComicData(ComicDataBase):
    name = 'Girls With Slingshots'
    language = 'en'
    url = 'http://www.girlswithslingshots.com/'
    start_date = '2004-09-30'
    rights = 'Danielle Corsetto'


class Crawler(CrawlerBase):
    history_capable_days = 30
    schedule = 'Mo,Tu,We,Th,Fr'
    time_zone = 'US/Eastern'

    def crawl(self, pub_date):
        feed = self.parse_feed('http://www.girlswithslingshots.com/feed/')
        for entry in feed.for_date(pub_date):
            page = self.parse_page(entry.link)
            url = page.src('img#comic')
            title = entry.title.replace('Girls with Slingshots - ', '')
            text = page.title('img#comic')
            return CrawlerImage(url, title, text)

########NEW FILE########
__FILENAME__ = harkavagrant
from comics.aggregator.crawler import CrawlerBase, CrawlerImage
from comics.core.comic_data import ComicDataBase


class ComicData(ComicDataBase):
    name = 'Hark, A Vagrant!'
    language = 'en'
    url = 'http://www.harkavagrant.com/'
    start_date = '2008-05-01'
    rights = 'Kate Beaton'


class Crawler(CrawlerBase):
    history_capable_days = 120
    time_zone = 'US/Eastern'

    def crawl(self, pub_date):
        feed = self.parse_feed('http://www.rsspect.com/rss/vagrant.xml')
        for entry in feed.for_date(pub_date):
            title = entry.title.replace('Hark, a Vagrant: ', '')
            urls = entry.summary.src('img', allow_multiple=True)
            for url in urls:
                if '/history/' in url or '/nonsense/' in url:
                    return CrawlerImage(url, title)

########NEW FILE########
__FILENAME__ = havet
# encoding: utf-8

from comics.aggregator.crawler import CrawlerBase
from comics.core.comic_data import ComicDataBase


class ComicData(ComicDataBase):
    name = 'Havet'
    language = 'no'
    url = 'http://havet.nettserier.no/'
    start_date = '2007-09-27'
    end_date = '2012-10-25'
    active = False
    rights = 'Øystein Ottesen'


class Crawler(CrawlerBase):
    def crawl(self, pub_date):
        pass  # Comic no longer published

########NEW FILE########
__FILENAME__ = hejibits
from comics.aggregator.crawler import CrawlerBase, CrawlerImage
from comics.core.comic_data import ComicDataBase


class ComicData(ComicDataBase):
    name = 'Hejibits'
    language = 'en'
    url = 'http://www.hejibits.com/'
    start_date = '2010-03-02'
    rights = 'John Kleckner'


class Crawler(CrawlerBase):
    history_capable_days = 90
    time_zone = 'US/Pacific'

    # Without User-Agent set, the server returns 403 Forbidden
    headers = {'User-Agent': 'Mozilla/4.0'}

    def crawl(self, pub_date):
        feed = self.parse_feed('http://www.hejibits.com/feed/')
        for entry in feed.for_date(pub_date):
            url = entry.summary.src('img[src*="/comics/"]')
            title = entry.title
            return CrawlerImage(url, title)

########NEW FILE########
__FILENAME__ = heltnils
from comics.aggregator.crawler import PondusNoCrawlerBase
from comics.core.comic_data import ComicDataBase


class ComicData(ComicDataBase):
    name = 'Helt Nils'
    language = 'no'
    url = 'http://www.pondus.no/'
    active = False
    rights = 'Nils Ofstad'


class Crawler(PondusNoCrawlerBase):
    def crawl(self, pub_date):
        pass  # Comic no longer published

########NEW FILE########
__FILENAME__ = hijinksensue
from comics.aggregator.crawler import CrawlerBase, CrawlerImage
from comics.core.comic_data import ComicDataBase


class ComicData(ComicDataBase):
    name = 'HijiNKS Ensue'
    language = 'en'
    url = 'http://hijinksensue.com/'
    start_date = '2007-05-11'
    rights = 'Joel Watson'


class Crawler(CrawlerBase):
    history_capable_days = 40
    time_zone = 'US/Central'

    def crawl(self, pub_date):
        feed = self.parse_feed('http://hijinksensue.com/feed/')
        for entry in feed.for_date(pub_date):
            if 'Comics' not in entry.tags:
                continue
            url = entry.summary.src('img[src*="/comics-rss/"]')
            if url is None:
                continue
            url = url.replace('/comics-rss/', '/comics/')
            title = entry.title
            text = entry.summary.alt('img[src*="/comics-rss/"]')
            return CrawlerImage(url, title, text)

########NEW FILE########
__FILENAME__ = hipsterhitler
from comics.aggregator.crawler import CrawlerBase
from comics.core.comic_data import ComicDataBase


class ComicData(ComicDataBase):
    name = 'Hipster Hitler'
    language = 'en'
    url = 'http://www.hipsterhitler.com/'
    start_date = '2010-08-01'
    end_date = '2013-01-15'
    active = False
    rights = 'JC & APK'


class Crawler(CrawlerBase):
    def crawl(self, pub_date):
        pass  # Comic no longer published

########NEW FILE########
__FILENAME__ = hjalmar
from comics.aggregator.crawler import CrawlerBase, CrawlerImage
from comics.core.comic_data import ComicDataBase


class ComicData(ComicDataBase):
    name = 'Hjalmar'
    language = 'no'
    url = 'http://heltnormalt.no/hjalmar'
    rights = 'Nils Axle Kanten'


class Crawler(CrawlerBase):
    history_capable_date = '2013-01-15'
    schedule = 'Mo,Tu,We,Th,Fr,Sa,Su'
    time_zone = 'Europe/Oslo'

    def crawl(self, pub_date):
        url = 'http://heltnormalt.no/img/hjalmar/%s.jpg' % (
            pub_date.strftime('%Y/%m/%d'))
        return CrawlerImage(url)

########NEW FILE########
__FILENAME__ = icanbarelydraw
from comics.aggregator.crawler import CrawlerBase, CrawlerImage
from comics.core.comic_data import ComicDataBase


class ComicData(ComicDataBase):
    name = 'I Can Barely Draw'
    language = 'en'
    url = 'http://www.icanbarelydraw.com/'
    start_date = '2011-08-05'
    rights = 'Group effort, CC BY-NC-ND 3.0'


class Crawler(CrawlerBase):
    history_capable_days = 180
    schedule = 'Mo'
    time_zone = 'US/Pacific'

    # Without User-Agent set, the server returns 403 Forbidden
    headers = {'User-Agent': 'Mozilla/4.0'}

    def crawl(self, pub_date):
        feed = self.parse_feed('http://www.icanbarelydraw.com/comic/feed')
        for entry in feed.for_date(pub_date):
            url = entry.summary.src('img[src*="/comics-rss/"]')
            if url is None:
                continue
            url = url.replace('/comics-rss/', '/comics/')
            title = entry.title
            return CrawlerImage(url, title)

########NEW FILE########
__FILENAME__ = idiotcomics
from comics.aggregator.crawler import CrawlerBase
from comics.core.comic_data import ComicDataBase


class ComicData(ComicDataBase):
    name = 'Idiot Comics'
    language = 'en'
    url = 'http://www.idiotcomics.com/'
    active = False
    start_date = '2006-09-08'
    end_date = '2010-02-15'
    rights = 'Robert Sergel'


class Crawler(CrawlerBase):
    def crawl(self, pub_date):
        pass  # Comic no longer published

########NEW FILE########
__FILENAME__ = inktank
from comics.aggregator.crawler import CrawlerBase
from comics.core.comic_data import ComicDataBase


class ComicData(ComicDataBase):
    name = 'InkTank'
    language = 'en'
    url = 'http://www.inktank.com/'
    active = False
    start_date = '2008-03-31'
    end_date = '2010-07-02'
    rights = 'Barry T. Smith'


class Crawler(CrawlerBase):
    def crawl(self, pub_date):
        pass  # Comic no longer published

########NEW FILE########
__FILENAME__ = intelsinsides
from comics.aggregator.crawler import CrawlerBase
from comics.core.comic_data import ComicDataBase


class ComicData(ComicDataBase):
    name = "Intel's Insides"
    language = 'en'
    url = 'http://www.intelsinsides.com/'
    active = False
    start_date = '2009-09-21'
    end_date = '2010-04-15'
    rights = 'Steve Lait'


class Crawler(CrawlerBase):
    def crawl(self, pub_date):
        pass  # Comic no longer published

########NEW FILE########
__FILENAME__ = joelovescrappymovies
from comics.aggregator.crawler import CrawlerBase, CrawlerImage
from comics.core.comic_data import ComicDataBase


class ComicData(ComicDataBase):
    name = 'Joe Loves Crappy Movies'
    language = 'en'
    url = 'http://www.digitalpimponline.com/strips.php?title=movie'
    start_date = '2005-04-04'
    rights = 'Joseph Dunn'


class Crawler(CrawlerBase):
    history_capable_date = '2005-04-04'
    time_zone = 'US/Eastern'

    # This crawler is pretty complicated because this dude does everything by
    # ID with only a loose date-mapping and re-using names (which you're not
    # allowed to do in HTML, but he's an ass like that)
    def crawl(self, pub_date):
        date_to_index_page = self.parse_page(
            'http://www.digitalpimponline.com/strips.php?title=movie')

        # Go through all IDs in the document, checking to see if the date is
        # the date we want in the option drop-down
        possible_ids = date_to_index_page.value(
            'select[name="id"] option', allow_multiple=True)
        the_id = None

        if possible_ids is None:
            return

        # (cheap conversion to a set to eliminate the duplicate IDs from
        # different parts of the HTML to save time...)
        for possible_id in set(possible_ids):
            # We're going to get two results back.  One is the potential date,
            # the other is the title.  I can't think of a good way to enforce
            # that we get the real value first, then the title, so we're just
            # going to parse it again later.
            possible_date_and_title = date_to_index_page.text(
                'option[value="%s"]' % possible_id, allow_multiple=True)
            for the_date in possible_date_and_title:
                # Make sure we strip off the leading '0' on %d: Joe doesn't
                # include them.  We can't use a regex due to the speed
                # penalty of ~500+ regex comparisons
                if the_date == pub_date.strftime('%B %d, %Y').replace(
                        ' 0', ' ', 1):
                    the_id = possible_id
                    break

        # Make sure we got an ID...
        if the_id is None:
            return

        # We got an ID:  Now, pull that page...
        right_page = self.parse_page(
            'http://www.digitalpimponline.com/strips.php?title=movie&id=%s' %
            the_id)

        # ...and parse the url...
        # (the URL has a leading ../, when it's in the base directory already.
        # Work around the glitch)
        url = right_page.src('img[class=strip]').replace('../', '')
        title = None

        # ... go through some rigamarole to get the title of the comic being
        # reviewed...  Basically, the selects for the date and movie title are
        # identical in basically every way.  We have to therefore get the
        # selected ones.  One is the date.  One is the title.  Check for the
        # date.
        possible_titles = right_page.text(
            'select[name="id"] option[selected]', allow_multiple=True)

        for possible_title in possible_titles:
            if pub_date.strftime('%Y') in possible_title:
                continue
            else:
                title = possible_title

        return CrawlerImage(url, title)

########NEW FILE########
__FILENAME__ = johnnywander
from comics.aggregator.crawler import CrawlerBase, CrawlerImage
from comics.core.comic_data import ComicDataBase


class ComicData(ComicDataBase):
    name = 'Johnny Wander'
    language = 'en'
    url = 'http://www.johnnywander.com/'
    start_date = '2008-09-30'
    rights = 'Yuko Ota & Ananth Panagariya'


class Crawler(CrawlerBase):
    history_capable_days = 40
    time_zone = 'US/Pacific'

    def crawl(self, pub_date):
        feed = self.parse_feed('http://www.johnnywander.com/feed')
        for entry in feed.for_date(pub_date):
            url = entry.summary.src('img')
            title = entry.title
            text = entry.summary.title('img')
            return CrawlerImage(url, title, text)

########NEW FILE########
__FILENAME__ = joyoftech
from comics.aggregator.crawler import CrawlerBase, CrawlerImage
from comics.core.comic_data import ComicDataBase


class ComicData(ComicDataBase):
    name = 'The Joy of Tech'
    language = 'en'
    url = 'http://www.geekculture.com/joyoftech/'
    start_date = '2000-08-14'
    rights = 'Geek Culture'


class Crawler(CrawlerBase):
    history_capable_days = 30
    schedule = 'Mo,We,Fr'
    time_zone = 'US/Eastern'

    # Without User-Agent set, the server returns 403 Forbidden
    headers = {'User-Agent': 'Mozilla/4.0'}

    def crawl(self, pub_date):
        feed = self.parse_feed(
            'http://www.joyoftech.com/joyoftech/jotblog/atom.xml')
        for entry in feed.for_date(pub_date):
            title = entry.title
            if not title.startswith('JoT'):
                continue
            url = entry.content0.src('img')
            if not url:
                continue
            url = url.replace('joy300thumb', '').replace('.gif', '.jpg')
            return CrawlerImage(url, title)

########NEW FILE########
__FILENAME__ = kalscartoon
from comics.aggregator.crawler import CrawlerBase, CrawlerImage
from comics.core.comic_data import ComicDataBase


class ComicData(ComicDataBase):
    name = "KAL's Cartoon"
    language = 'en'
    url = 'http://www.economist.com/'
    start_date = '2006-01-05'
    rights = 'Kevin Kallaugher'


class Crawler(CrawlerBase):
    history_capable_days = 7
    schedule = 'Sa'
    time_zone = 'Europe/London'

    # Without User-Agent set, the server returns 403 Forbidden
    headers = {'User-Agent': 'Mozilla/4.0'}

    def crawl(self, pub_date):
        page = self.parse_page('http://www.economist.com/content/kallery')
        url = page.src('.content-image-full img')
        date = pub_date.strftime('%Y%m%d')
        if date in url:
            return CrawlerImage(url)

########NEW FILE########
__FILENAME__ = kellermannen
from comics.aggregator.crawler import CrawlerBase, CrawlerImage
from comics.core.comic_data import ComicDataBase


class ComicData(ComicDataBase):
    name = 'Kellermannen'
    language = 'no'
    url = 'http://www.dagbladet.no/tegneserie/kellermannen/'
    rights = 'Martin Kellerman'


class Crawler(CrawlerBase):
    history_capable_days = 30
    schedule = 'Mo,We,Fr'
    time_zone = 'Europe/Oslo'

    def crawl(self, pub_date):
        epoch = self.date_to_epoch(pub_date)
        url = (
            'http://www.dagbladet.no/tegneserie/' +
            'kellermannenarkiv/serve.php?%d' % epoch)
        return CrawlerImage(url)

########NEW FILE########
__FILENAME__ = kiwiblitz
from comics.aggregator.crawler import CrawlerBase, CrawlerImage
from comics.core.comic_data import ComicDataBase


class ComicData(ComicDataBase):
    name = 'Kiwiblitz'
    language = 'en'
    url = 'http://www.kiwiblitz.com/'
    start_date = '2009-04-18'
    rights = 'Mary Cagle'


class Crawler(CrawlerBase):
    history_capable_days = 32
    schedule = 'We,Fr'
    time_zone = 'US/Pacific'

    def crawl(self, pub_date):
        feed = self.parse_feed('http://www.kiwiblitz.com/feed/')
        for entry in feed.for_date(pub_date):
            url = entry.summary.src('img[src*="/wp-content/uploads/"]')
            if not url:
                continue
            url = url.replace('-150x150', '')
            title = entry.title
            return CrawlerImage(url, title)

########NEW FILE########
__FILENAME__ = kollektivet
# encoding: utf-8

from comics.aggregator.crawler import CrawlerBase, CrawlerImage
from comics.core.comic_data import ComicDataBase


class ComicData(ComicDataBase):
    name = 'Kollektivet'
    language = 'no'
    url = 'http://heltnormalt.no/kollektivet'
    rights = 'Torbjørn Lien'


class Crawler(CrawlerBase):
    history_capable_date = '2013-05-01'
    schedule = 'Mo,Tu,We,Th,Fr,Sa,Su'
    time_zone = 'Europe/Oslo'

    def crawl(self, pub_date):
        url = 'http://heltnormalt.no/img/kollektivet/%s.jpg' % (
            pub_date.strftime('%Y/%m/%d'))
        return CrawlerImage(url)

########NEW FILE########
__FILENAME__ = kukuburi
# encoding: utf-8

from comics.aggregator.crawler import CrawlerBase
from comics.core.comic_data import ComicDataBase


class ComicData(ComicDataBase):
    name = 'Kukuburi'
    language = 'en'
    url = 'http://www.kukuburi.com/'
    start_date = '2007-09-08'
    end_date = '2012-01-11'
    active = False
    rights = 'Ramón Pérez'


class Crawler(CrawlerBase):
    def crawl(self, pub_date):
        pass  # Comic no longer published

########NEW FILE########
__FILENAME__ = lagunen
from comics.aggregator.crawler import CrawlerBase
from comics.core.comic_data import ComicDataBase


class ComicData(ComicDataBase):
    name = 'Lagunen'
    language = 'no'
    url = 'http://www.start.no/tegneserier/lagunen/'
    active = False
    start_date = '1991-05-13'
    rights = 'Jim Toomey'


class Crawler(CrawlerBase):
    def crawl(self, pub_date):
        pass  # Comic no longer published

########NEW FILE########
__FILENAME__ = leasticoulddo
from comics.aggregator.crawler import CrawlerBase, CrawlerImage
from comics.core.comic_data import ComicDataBase


class ComicData(ComicDataBase):
    name = 'Least I Could Do'
    language = 'en'
    url = 'http://www.leasticoulddo.com/'
    start_date = '2003-02-10'
    rights = 'Ryan Sohmer & Lar deSouza'


class Crawler(CrawlerBase):
    history_capable_date = '2003-02-10'
    schedule = 'Mo,Tu,We,Th,Fr,Sa,Su'
    time_zone = 'America/Montreal'

    def crawl(self, pub_date):
        url = 'http://leasticoulddo.com/wp-content/uploads/%s.gif' % (
            pub_date.strftime('%Y/%m/%Y%m%d'),)
        return CrawlerImage(url)

########NEW FILE########
__FILENAME__ = lefthandedtoons

from comics.aggregator.crawler import CrawlerBase, CrawlerImage
from comics.core.comic_data import ComicDataBase


class ComicData(ComicDataBase):
    name = 'Left-Handed Toons'
    language = 'en'
    url = 'http://www.lefthandedtoons.com/'
    start_date = '2007-01-14'
    rights = 'Justin & Drew'


class Crawler(CrawlerBase):
    history_capable_days = 12
    schedule = 'Mo,Tu,We,Th'
    time_zone = 'US/Eastern'

    def crawl(self, pub_date):
        feed = self.parse_feed(
            'http://feeds.feedburner.com/lefthandedtoons/awesome')

        for entry in feed.for_date(pub_date):
            url = entry.summary.src('img[src*="/toons/"]')
            title = entry.title

            if url:
                return CrawlerImage(url, title)

########NEW FILE########
__FILENAME__ = libertymeadows
from comics.aggregator.crawler import CrawlerBase, CrawlerImage
from comics.core.comic_data import ComicDataBase


class ComicData(ComicDataBase):
    name = 'Liberty Meadows'
    language = 'en'
    url = 'http://www.creators.com/comics/liberty-meadows.html'
    start_date = '1997-03-30'
    end_date = '2001-12-31'
    rights = 'Frank Cho'


class Crawler(CrawlerBase):
    history_capable_days = 19
    schedule = 'Mo,Tu,We,Th,Fr,Sa,Su'
    time_zone = 'US/Pacific'

    def crawl(self, pub_date):
        feed = self.parse_feed(
            'http://www.creators.com/comics/liberty-meadows.rss')
        for entry in feed.for_date(pub_date):
            page = self.parse_page(entry.link)
            url = page.src('img[src*="_thumb"]').replace('thumb', 'image')
            return CrawlerImage(url)

########NEW FILE########
__FILENAME__ = lifewithrippy
from comics.aggregator.crawler import CrawlerBase
from comics.core.comic_data import ComicDataBase


class ComicData(ComicDataBase):
    name = 'Life With Rippy'
    language = 'en'
    url = 'http://www.rhymes-with-witch.com/'
    active = False
    start_date = '2006-08-09'
    end_date = '2009-11-25'
    rights = 'r*k*milholland'


class Crawler(CrawlerBase):
    def crawl(self, pub_date):
        pass  # Comic no longer published

########NEW FILE########
__FILENAME__ = littlegamers
from comics.aggregator.crawler import CrawlerBase, CrawlerImage
from comics.core.comic_data import ComicDataBase


class ComicData(ComicDataBase):
    name = 'Little Gamers'
    language = 'en'
    url = 'http://www.little-gamers.com/'
    start_date = '2000-12-01'
    rights = 'Christian Fundin & Pontus Madsen'


class Crawler(CrawlerBase):
    history_capable_date = '2000-12-01'
    time_zone = 'Europe/Stockholm'

    def crawl(self, pub_date):
        feed = self.parse_feed(
            'http://www.little-gamers.com/category/comic/feed')
        for entry in feed.for_date(pub_date):
            url = entry.summary.src('img')
            title = entry.title
            return CrawlerImage(url, title)

########NEW FILE########
__FILENAME__ = loku
from comics.aggregator.crawler import CrawlerBase
from comics.core.comic_data import ComicDataBase


class ComicData(ComicDataBase):
    name = 'LO-KU'
    language = 'en'
    url = 'http://www.lo-ku.com/'
    start_date = '2009-06-15'
    active = False
    rights = 'Thomas & Daniel Drinnen'


class Crawler(CrawlerBase):
    def crawl(self, pub_date):
        pass  # Comic no longer published

########NEW FILE########
__FILENAME__ = lookingforgroup
from comics.aggregator.crawler import CrawlerBase, CrawlerImage
from comics.core.comic_data import ComicDataBase


class ComicData(ComicDataBase):
    name = 'Looking For Group'
    language = 'en'
    url = 'http://www.lfgcomic.com/'
    start_date = '2006-11-06'
    rights = 'Ryan Sohmer & Lar deSouza'


class Crawler(CrawlerBase):
    history_capable_date = '2006-11-06'
    schedule = 'Mo,Th'
    time_zone = 'America/Montreal'

    def crawl(self, pub_date):
        feed = self.parse_feed('http://feeds.feedburner.com/LookingForGroup')
        images = []
        for entry in feed.for_date(pub_date):
            if entry.title.isdigit():
                url = entry.content0.src('a[rel="bookmark"] img')
                if url:
                    url = url.replace('-210x300', '')
                title = entry.title
                images.append(CrawlerImage(url, title))
        if images:
            return images

########NEW FILE########
__FILENAME__ = lunch
# encoding: utf-8

import re
import urllib

from comics.aggregator.crawler import CrawlerBase, CrawlerImage
from comics.core.comic_data import ComicDataBase


class ComicData(ComicDataBase):
    name = 'Lunch'
    language = 'no'
    url = 'http://lunchstriper.lunddesign.no/'
    start_date = '2009-10-21'
    rights = 'Børge Lund'


class Crawler(CrawlerBase):
    history_capable_date = '2009-04-01'
    time_zone = 'Europe/Oslo'

    def crawl(self, pub_date):
        feed = self.parse_feed('http://lunchstriper.lunddesign.no/?feed=rss2')
        for entry in feed.for_date(pub_date):
            url = entry.summary.src('img[src*="/comics/"]')
            title = entry.title
            return CrawlerImage(url, title)

########NEW FILE########
__FILENAME__ = lunchdb
# encoding: utf-8

from comics.aggregator.crawler import CrawlerBase, CrawlerImage
from comics.core.comic_data import ComicDataBase


class ComicData(ComicDataBase):
    name = 'Lunch (db.no)'
    language = 'no'
    url = 'http://www.dagbladet.no/tegneserie/lunch/'
    start_date = '2009-10-21'
    rights = 'Børge Lund'


class Crawler(CrawlerBase):
    history_capable_days = 14
    schedule = 'Mo,Tu,We,Th,Fr,Sa'
    time_zone = 'Europe/Oslo'

    def crawl(self, pub_date):
        epoch = self.date_to_epoch(pub_date)
        url = 'http://www.dagbladet.no/tegneserie/luncharkiv/serve.php?%s' % (
            epoch,)
        return CrawlerImage(url)

########NEW FILE########
__FILENAME__ = lunchtu
# encoding: utf-8

from comics.aggregator.crawler import CrawlerBase, CrawlerImage
from comics.core.comic_data import ComicDataBase


class ComicData(ComicDataBase):
    name = 'Lunch (tu.no)'
    language = 'no'
    url = 'http://www.tu.no/lunch/'
    start_date = '2009-10-21'
    rights = 'Børge Lund'


class Crawler(CrawlerBase):
    history_capable_date = '2012-06-15'
    schedule = 'Mo,Tu,We,Th,Fr'
    time_zone = 'Europe/Oslo'

     # Without referer, the server returns a placeholder image
    headers = {'Referer': 'http://www.tu.no/lunch/'}

    def crawl(self, pub_date):
        url = 'http://www1.tu.no/lunch/img/%s.png' % (
            pub_date.strftime('%y%m%d'))
        return CrawlerImage(url)

########NEW FILE########
__FILENAME__ = m
from comics.aggregator.crawler import CrawlerBase
from comics.core.comic_data import ComicDataBase


class ComicData(ComicDataBase):
    name = 'M'
    language = 'no'
    url = 'http://www.dagbladet.no/tegneserie/m'
    start_date = '2003-02-10'
    end_date = '2012-01-13'
    active = False
    rights = 'Mads Eriksen'


class Crawler(CrawlerBase):
    def crawl(self, pub_date):
        pass  # Comic no longer published

########NEW FILE########
__FILENAME__ = magpieluck
from comics.aggregator.crawler import CrawlerBase
from comics.core.comic_data import ComicDataBase


class ComicData(ComicDataBase):
    name = 'Magpie Luck'
    language = 'en'
    url = 'http://magpieluck.com/'
    start_date = '2009-07-30'
    end_date = '2011-09-08'
    active = False
    rights = 'Katie Sekelsky, CC BY-NC-SA 3.0'


class Crawler(CrawlerBase):
    def crawl(self, pub_date):
        pass  # Comic no longer published

########NEW FILE########
__FILENAME__ = manalanextdoor
from comics.aggregator.crawler import CrawlerBase
from comics.core.comic_data import ComicDataBase


class ComicData(ComicDataBase):
    name = 'Manala Next Door'
    language = 'en'
    url = 'http://www.manalanextdoor.com/'
    start_date = '2011-01-23'
    end_date = '2012-11-14'
    active = False
    rights = 'Humon'


class Crawler(CrawlerBase):
    def crawl(self, pub_date):
        pass  # Comic no longer published

########NEW FILE########
__FILENAME__ = manlyguys
from comics.aggregator.crawler import CrawlerBase, CrawlerImage
from comics.core.comic_data import ComicDataBase


class ComicData(ComicDataBase):
    name = 'Manly Guys Doing Manly Things'
    language = 'en'
    url = 'http://thepunchlineismachismo.com/'
    start_date = '2005-05-29'
    rights = 'Kelly Turnbull, CC BY-NC-SA 3.0'


class Crawler(CrawlerBase):
    history_capable_days = 60
    schedule = 'Mo'
    time_zone = 'US/Pacific'

    def crawl(self, pub_date):
        feed = self.parse_feed('http://thepunchlineismachismo.com/feed')
        for entry in feed.for_date(pub_date):
            url = entry.summary.src('img[src*="/wp-content/uploads/"]')
            if url is not None:
                url = url.replace('-150x150', '')
                title = entry.title
                return CrawlerImage(url, title)

########NEW FILE########
__FILENAME__ = marriedtothesea
from comics.aggregator.crawler import CrawlerBase, CrawlerImage
from comics.core.comic_data import ComicDataBase


class ComicData(ComicDataBase):
    name = 'Married To The Sea'
    language = 'en'
    url = 'http://www.marriedtothesea.com/'
    start_date = '2006-02-13'
    rights = 'Drew'


class Crawler(CrawlerBase):
    history_capable_date = '2006-02-13'
    schedule = 'Mo,Tu,We,Th,Fr,Sa,Su'
    time_zone = 'US/Eastern'

    # Without User-Agent set, the server returns empty pages
    headers = {'User-Agent': 'Mozilla/4.0'}

    def crawl(self, pub_date):
        page_url = 'http://www.marriedtothesea.com/%s' % (
            pub_date.strftime('%m%d%y'))
        page = self.parse_page(page_url)

        url = page.src('#butts img', allow_multiple=True)
        url = url and url[0]
        if not url:
            return

        title = page.text('div.headertext', allow_multiple=True)[0]
        title = title and title[0] or ''
        title = title[title.find(':')+1:].strip()

        return CrawlerImage(url, title)

########NEW FILE########
__FILENAME__ = megatokyo
from comics.aggregator.crawler import CrawlerBase, CrawlerImage
from comics.core.comic_data import ComicDataBase


class ComicData(ComicDataBase):
    name = 'MegaTokyo'
    language = 'en'
    url = 'http://www.megatokyo.com/'
    start_date = '2000-08-14'
    rights = 'Fred Gallagher & Rodney Caston'


class Crawler(CrawlerBase):
    history_capable_days = 30
    time_zone = 'US/Eastern'

    def crawl(self, pub_date):
        feed = self.parse_feed('http://www.megatokyo.com/rss/megatokyo.xml')
        for entry in feed.for_date(pub_date):
            if entry.title.startswith('Comic ['):
                title = entry.title.split('"')[1]
                page = self.parse_page(entry.link)
                url = page.src('img[src*="/strips/"]')
                return CrawlerImage(url, title)

########NEW FILE########
__FILENAME__ = menagea3
# encoding: utf-8

import datetime

from comics.aggregator.crawler import CrawlerBase, CrawlerImage
from comics.core.comic_data import ComicDataBase


class ComicData(ComicDataBase):
    name = 'Ménage à 3'
    language = 'en'
    url = 'http://www.ma3comic.com/'
    start_date = '2008-05-17'
    rights = 'Giz & Dave Zero 1'


class Crawler(CrawlerBase):
    history_capable_days = 50
    schedule = 'Tu,Th,Sa'
    time_zone = 'US/Eastern'

    def crawl(self, pub_date):
        # Release to the feed is one day delayed, so we try to get yesterday's
        # comic instead.
        pub_date -= datetime.timedelta(days=1)

        feed = self.parse_feed('http://www.ma3comic.com/comic.rss')
        for entry in feed.for_date(pub_date):
            title = entry.title.replace('Menage a 3 - ', '')
            page = self.parse_page(entry.link)
            url = page.src('#cc img')
            return CrawlerImage(url, title)

########NEW FILE########
__FILENAME__ = misfile
from comics.aggregator.crawler import CrawlerBase, CrawlerImage
from comics.core.comic_data import ComicDataBase


class ComicData(ComicDataBase):
    name = 'Misfile'
    language = 'en'
    url = 'http://www.misfile.com/'
    start_date = '2004-03-01'
    rights = 'Chris Hazelton'


class Crawler(CrawlerBase):
    history_capable_days = 10
    schedule = 'Mo,Tu,We,Th,Fr'
    time_zone = 'US/Eastern'

    def crawl(self, pub_date):
        feed = self.parse_feed('http://www.misfile.com/misfileRSS.php')
        for entry in feed.for_date(pub_date):
            page = self.parse_page(entry.link)
            url = page.src('.comic img')
            return CrawlerImage(url)

########NEW FILE########
__FILENAME__ = mortenm
from comics.aggregator.crawler import CrawlerBase
from comics.core.comic_data import ComicDataBase


class ComicData(ComicDataBase):
    name = 'Morten M'
    language = 'no'
    url = 'http://www.vg.no/spesial/mortenm/'
    start_date = '1978-01-01'
    end_date = '2011-12-31'
    active = False
    rights = 'Morten M. Kristiansen'


class Crawler(CrawlerBase):
    def crawl(self, pub_date):
        pass  # Comic no longer published

########NEW FILE########
__FILENAME__ = mutts
from comics.aggregator.crawler import CrawlerBase, CrawlerImage
from comics.core.comic_data import ComicDataBase


class ComicData(ComicDataBase):
    name = 'Mutts'
    language = 'en'
    url = 'http://muttscomics.com'
    start_date = '1994-01-01'
    rights = 'Patrick McDonnell'


class Crawler(CrawlerBase):
    history_capable_date = '1994-09-11'
    schedule = 'Mo,Tu,We,Th,Fr,Sa,Su'
    time_zone = 'US/Eastern'

    def crawl(self, pub_date):
        url = 'http://muttscomics.com/art/images/daily/%s.gif' % (
            pub_date.strftime('%m%d%y'),)
        return CrawlerImage(url)

########NEW FILE########
__FILENAME__ = mysticrevolution
from comics.aggregator.crawler import CrawlerBase, CrawlerImage
from comics.core.comic_data import ComicDataBase


class ComicData(ComicDataBase):
    name = 'Mystic Revolution'
    language = 'en'
    url = 'http://mysticrevolution.keenspot.com/'
    start_date = '2004-01-01'
    rights = 'Jennifer Brazas'


class Crawler(CrawlerBase):
    # Not history capable, just a workaround for time zone bug in comics:
    history_capable_days = 1
    time_zone = 'US/Pacific'

    # Without User-Agent set, the server returns 403 Forbidden
    headers = {'User-Agent': 'Mozilla/4.0'}

    def crawl(self, pub_date):
        page = self.parse_page('http://mysticrevolution.keenspot.com/')
        url = page.src('img.ksc')
        title = page.title('img.ksc')
        return CrawlerImage(url, title)

########NEW FILE########
__FILENAME__ = nedroid
from comics.aggregator.crawler import CrawlerBase, CrawlerImage
from comics.core.comic_data import ComicDataBase


class ComicData(ComicDataBase):
    name = 'Nedroid'
    language = 'en'
    url = 'http://www.nedroid.com/'
    start_date = '2006-04-24'
    rights = 'Anthony Clark'


class Crawler(CrawlerBase):
    history_capable_days = 180
    time_zone = 'US/Eastern'

    # Without User-Agent set, the server returns 403 Forbidden
    headers = {'User-Agent': 'Mozilla/4.0'}

    def crawl(self, pub_date):
        feed = self.parse_feed('http://nedroid.com/feed/')
        for entry in feed.for_date(pub_date):
            if 'Comic' not in entry.tags:
                continue
            url = entry.summary.src('img')
            if url is None:
                continue
            url = url.replace('/comic/comics-rss/', '/comics/')
            title = entry.title
            text = entry.summary.title('img')
            return CrawlerImage(url, title, text)

########NEW FILE########
__FILENAME__ = nemi
from comics.aggregator.crawler import CrawlerBase, CrawlerImage
from comics.core.comic_data import ComicDataBase


class ComicData(ComicDataBase):
    name = 'Nemi (db.no)'
    language = 'no'
    url = 'http://www.dagbladet.no/tegneserie/nemi/'
    start_date = '1997-01-01'
    rights = 'Lise Myhre'


class Crawler(CrawlerBase):
    history_capable_days = 14
    schedule = 'Mo,Tu,We,Th,Fr,Sa'
    time_zone = 'Europe/Oslo'

    def crawl(self, pub_date):
        epoch = self.date_to_epoch(pub_date)
        url = 'http://www.dagbladet.no/tegneserie/nemiarkiv/serve.php?%s' % (
            epoch,)
        return CrawlerImage(url)

########NEW FILE########
__FILENAME__ = nemibt
from comics.aggregator.crawler import CrawlerBase, CrawlerImage
from comics.core.comic_data import ComicDataBase


class ComicData(ComicDataBase):
    name = 'Nemi (bt.no)'
    language = 'no'
    url = 'http://www.bt.no/bergenpuls/tegneserier/tegneserier_nemi/'
    start_date = '1997-01-01'
    rights = 'Lise Myhre'


class Crawler(CrawlerBase):
    history_capable_days = 162
    schedule = 'Mo,Tu,We,Th,Fr,Sa,Su'
    time_zone = 'Europe/Oslo'

    def crawl(self, pub_date):
        url = 'http://www.bt.no/external/cartoon/nemi/%s.gif' % (
            pub_date.strftime('%d%m%y'),)
        return CrawlerImage(url)

########NEW FILE########
__FILENAME__ = nerfnow
# encoding: utf-8

from comics.aggregator.crawler import CrawlerBase, CrawlerImage
from comics.core.comic_data import ComicDataBase


class ComicData(ComicDataBase):
    name = 'Nerf NOW!!'
    language = 'en'
    url = 'http://www.nerfnow.com/'
    start_date = '2009-09-02'
    rights = 'Josué Pereira'


class Crawler(CrawlerBase):
    history_capable_days = 14
    schedule = 'Tu,We,Th,Fr,Sa'
    time_zone = 'US/Eastern'

    def crawl(self, pub_date):
        feed = self.parse_feed('http://feeds.feedburner.com/nerfnow/full')
        for entry in feed.for_date(pub_date):
            url = entry.content0.src('img[src*="/comic/"]')
            if url is None:
                continue
            url = url.replace('thumb', 'image').replace('/large', '')
            title = entry.title
            return CrawlerImage(url, title)

########NEW FILE########
__FILENAME__ = nonsequitur
from comics.aggregator.crawler import GoComicsComCrawlerBase
from comics.core.comic_data import ComicDataBase


class ComicData(ComicDataBase):
    name = 'Non Sequitur'
    language = 'en'
    url = 'http://www.gocomics.com/nonsequitur'
    start_date = '1992-02-16'
    rights = 'Wiley Miller'


class Crawler(GoComicsComCrawlerBase):
    history_capable_date = '1992-02-16'
    schedule = 'Mo,Tu,We,Th,Fr,Sa,Su'
    time_zone = 'US/Eastern'

    def crawl(self, pub_date):
        return self.crawl_helper('Non Sequitur', pub_date)

########NEW FILE########
__FILENAME__ = notinventedhere
from comics.aggregator.crawler import CrawlerBase, CrawlerImage
from comics.core.comic_data import ComicDataBase


class ComicData(ComicDataBase):
    name = 'Not Invented Here'
    language = 'en'
    url = 'http://notinventedhe.re/'
    start_date = '2009-09-21'
    rights = 'Bill Barnes and Paul Southworth'


class Crawler(CrawlerBase):
    history_capable_date = '2009-09-21'
    schedule = 'Mo,Tu,We,Th'
    time_zone = 'US/Pacific'

    def crawl(self, pub_date):
        url = 'http://thiswas.notinventedhe.re/on/%s' % \
            pub_date.strftime('%Y-%m-%d')
        return CrawlerImage(url)

########NEW FILE########
__FILENAME__ = oatmeal
from comics.aggregator.crawler import CrawlerBase, CrawlerImage
from comics.core.comic_data import ComicDataBase


class ComicData(ComicDataBase):
    name = 'The Oatmeal'
    language = 'en'
    url = 'http://theoatmeal.com/'
    rights = 'Matthew Inman'


class Crawler(CrawlerBase):
    history_capable_days = 90
    time_zone = 'US/Pacific'

    def crawl(self, pub_date):
        feed = self.parse_feed('http://feeds.feedburner.com/oatmealfeed')
        for entry in feed.for_date(pub_date):
            page = self.parse_page(entry.link)
            results = [
                CrawlerImage(url) for url in
                page.src('img[src*="/comics/"]', allow_multiple=True)]
            if results:
                results[0].title = entry.title
                return results

########NEW FILE########
__FILENAME__ = oots
from comics.aggregator.crawler import CrawlerBase, CrawlerImage
from comics.core.comic_data import ComicDataBase


class ComicData(ComicDataBase):
    name = 'The Order of the Stick'
    language = 'en'
    url = 'http://www.giantitp.com/'
    start_date = '2003-09-30'
    rights = 'Rich Burlew'


class Crawler(CrawlerBase):
    history_capable_days = 1
    time_zone = 'US/Eastern'

    def crawl(self, pub_date):
        feed = self.parse_feed('http://www.giantitp.com/comics/oots.rss')
        if len(feed.all()):
            entry = feed.all()[0]
            page = self.parse_page(entry.link)
            url = page.src('img[src*="/comics/images/"]')
            title = entry.title
            return CrawlerImage(url, title)

########NEW FILE########
__FILENAME__ = optipess
# encoding: utf-8

from comics.aggregator.crawler import CrawlerBase, CrawlerImage
from comics.core.comic_data import ComicDataBase


class ComicData(ComicDataBase):
    name = 'Optipess'
    language = 'en'
    url = 'http://www.optipess.com/'
    start_date = '2008-12-01'
    rights = 'Kristian Nygård'


class Crawler(CrawlerBase):
    history_capable_days = 90
    schedule = 'Th,Su'
    time_zone = 'Europe/Oslo'

    def crawl(self, pub_date):
        feed = self.parse_feed('http://feeds.feedburner.com/Optipess')
        for entry in feed.for_date(pub_date):
            if 'Comic' not in entry.tags:
                continue
            url = entry.summary.src('img[src*="/comics/"]')
            title = entry.title
            text = entry.summary.title('img[src*="/comics/"]')
            return CrawlerImage(url, title, text)

########NEW FILE########
__FILENAME__ = orneryboy
from comics.aggregator.crawler import CrawlerBase
from comics.core.comic_data import ComicDataBase


class ComicData(ComicDataBase):
    name = 'Orneryboy'
    language = 'en'
    url = 'http://www.orneryboy.com/'
    start_date = '2002-07-22'
    end_date = '2012-04-16'
    active = False
    rights = 'Michael Lalonde'


class Crawler(CrawlerBase):
    def crawl(self, pub_date):
        pass  # Comic no longer published

########NEW FILE########
__FILENAME__ = overcompensating
from comics.aggregator.crawler import CrawlerBase
from comics.core.comic_data import ComicDataBase


class ComicData(ComicDataBase):
    name = 'Overcompensating'
    language = 'en'
    url = 'http://www.overcompensating.com/'
    start_date = '2004-09-29'
    active = False
    rights = 'Jeff Rowland'


class Crawler(CrawlerBase):
    def crawl(self, pub_date):
        pass  # Comic no longer published

########NEW FILE########
__FILENAME__ = partiallyclips
from comics.aggregator.crawler import CrawlerBase, CrawlerImage
from comics.core.comic_data import ComicDataBase


class ComicData(ComicDataBase):
    name = 'PartiallyClips'
    language = 'en'
    url = 'http://partiallyclips.com/'
    start_date = '2002-01-01'
    rights = 'Robert T. Balder'


class Crawler(CrawlerBase):
    history_capable_days = 32
    schedule = 'Tu'
    time_zone = 'US/Eastern'

    def crawl(self, pub_date):
        feed = self.parse_feed('http://partiallyclips.com/feed/')
        for entry in feed.for_date(pub_date):
            url = entry.summary.src('img')
            if not url:
                continue
            url = url.replace('comics-rss', 'comics')
            title = entry.title.split(' - ')[0]
            return CrawlerImage(url, title)

########NEW FILE########
__FILENAME__ = pcweenies
from comics.aggregator.crawler import CrawlerBase, CrawlerImage
from comics.core.comic_data import ComicDataBase


class ComicData(ComicDataBase):
    name = 'The PC Weenies'
    language = 'en'
    url = 'http://pcweenies.com/'
    start_date = '1998-10-21'
    rights = 'Krishna M. Sadasivam'


class Crawler(CrawlerBase):
    history_capable_days = 14
    time_zone = 'US/Eastern'

    def crawl(self, pub_date):
        feed = self.parse_feed('http://pcweenies.com/feed/')
        for entry in feed.for_date(pub_date):
            url = entry.summary.src(u'img[src*="/comics/"]')
            title = entry.title
            return CrawlerImage(url, title)

########NEW FILE########
__FILENAME__ = peanuts
from comics.aggregator.crawler import GoComicsComCrawlerBase
from comics.core.comic_data import ComicDataBase


class ComicData(ComicDataBase):
    name = 'Peanuts'
    language = 'en'
    url = 'http://www.gocomics.com/peanuts/'
    start_date = '1950-10-02'
    end_date = '2000-02-13'
    rights = 'Charles M. Schulz'


class Crawler(GoComicsComCrawlerBase):
    history_capable_date = '1950-10-02'
    schedule = 'Mo,Tu,We,Th,Fr,Sa,Su'
    time_zone = 'US/Eastern'

    def crawl(self, pub_date):
        return self.crawl_helper('Peanuts', pub_date)

########NEW FILE########
__FILENAME__ = pearlsbeforeswine
from comics.aggregator.crawler import GoComicsComCrawlerBase
from comics.core.comic_data import ComicDataBase


class ComicData(ComicDataBase):
    name = 'Pearls Before Swine'
    language = 'en'
    url = 'http://www.gocomics.com/pearlsbeforeswine/'
    start_date = '2001-12-30'
    rights = 'Stephan Pastis'


class Crawler(GoComicsComCrawlerBase):
    history_capable_date = '2002-01-06'
    schedule = 'Mo,Tu,We,Th,Fr,Sa,Su'
    time_zone = 'US/Eastern'

    def crawl(self, pub_date):
        return self.crawl_helper('Pearls Before Swine', pub_date)

########NEW FILE########
__FILENAME__ = pelsogpoter
from comics.aggregator.crawler import CrawlerBase, CrawlerImage
from comics.core.comic_data import ComicDataBase


class ComicData(ComicDataBase):
    name = 'Pels og Poter'
    language = 'no'
    url = 'http://www.start.no/tegneserier/'
    start_date = '1994-01-01'
    rights = 'Patrick McDonnell'


class Crawler(CrawlerBase):
    history_capable_date = '2009-03-23'
    schedule = 'Mo,We,Th,Fr,Sa,Su'
    time_zone = 'Europe/Oslo'

    def crawl(self, pub_date):
        url = 'http://g2.start.no/tegneserier/striper/mutts/MUT%s.gif' % (
            pub_date.strftime('%Y%m%d'),)
        return CrawlerImage(url)

########NEW FILE########
__FILENAME__ = pennyarcade
from comics.aggregator.crawler import CrawlerBase, CrawlerImage
from comics.core.comic_data import ComicDataBase


class ComicData(ComicDataBase):
    name = 'Penny Arcade'
    language = 'en'
    url = 'http://www.penny-arcade.com/'
    start_date = '1998-11-18'
    rights = 'Mike Krahulik & Jerry Holkins'


class Crawler(CrawlerBase):
    history_capable_date = '1998-11-18'
    schedule = 'Mo,We,Fr'
    time_zone = 'US/Pacific'

    def crawl(self, pub_date):
        page_url = 'http://www.penny-arcade.com/comic/%s/' % (
            pub_date.strftime('%Y/%m/%d'),)
        page = self.parse_page(page_url)
        title = page.alt('#comicFrame img')
        url = page.src('#comicFrame img')
        return CrawlerImage(url, title)

########NEW FILE########
__FILENAME__ = perrybiblefellowship
from comics.aggregator.crawler import CrawlerBase, CrawlerImage
from comics.core.comic_data import ComicDataBase


class ComicData(ComicDataBase):
    name = 'The Perry Bible Fellowship'
    language = 'en'
    url = 'http://www.pbfcomics.com/'
    start_date = '2001-01-01'
    rights = 'Nicholas Gurewitch'


class Crawler(CrawlerBase):
    history_capable_date = '2001-01-01'
    time_zone = 'US/Eastern'

    def crawl(self, pub_date):
        feed = self.parse_feed('http://www.pbfcomics.com/feed/feed.xml')
        for entry in feed.for_date(pub_date):
            url = entry.summary.src('img[src*="/archive_b/"]')
            title = entry.title
            return CrawlerImage(url, title)

########NEW FILE########
__FILENAME__ = petpeevy
from comics.aggregator.crawler import CrawlerBase
from comics.core.comic_data import ComicDataBase


class ComicData(ComicDataBase):
    name = 'Pet Peevy'
    language = 'en'
    url = 'http://dobbcomics.com/'
    active = False
    rights = 'Rob Snyder'


class Crawler(CrawlerBase):
    def crawl(self, pub_date):
        pass  # Comic no longer published

########NEW FILE########
__FILENAME__ = phd
from comics.aggregator.crawler import CrawlerBase, CrawlerImage
from comics.core.comic_data import ComicDataBase


class ComicData(ComicDataBase):
    name = 'Piled Higher and Deeper'
    language = 'en'
    url = 'http://www.phdcomics.com/'
    start_date = '1997-10-27'
    rights = 'Jorge Cham'


class Crawler(CrawlerBase):
    history_capable_date = '1997-10-27'
    schedule = None
    time_zone = 'US/Pacific'

    def crawl(self, pub_date):
        feed = self.parse_feed(
            'http://www.phdcomics.com/gradfeed_justcomics.php')
        for entry in feed.for_date(pub_date):
            url = entry.summary.src('img')
            title = entry.title.split("'")[1]
            return CrawlerImage(url, title)

########NEW FILE########
__FILENAME__ = pickles
from comics.aggregator.crawler import GoComicsComCrawlerBase
from comics.core.comic_data import ComicDataBase


class ComicData(ComicDataBase):
    name = 'Pickles'
    language = 'en'
    url = 'http://www.arcamax.com/thefunnies/pickles'
    start_date = '2003-10-01'
    rights = 'Brian Crane'


class Crawler(GoComicsComCrawlerBase):
    history_capable_date = '2003-10-01'
    schedule = 'Mo,Tu,We,Th,Fr,Sa,Su'
    time_zone = 'US/Mountain'

    def crawl(self, pub_date):
        return self.crawl_helper('Pickles', pub_date)

########NEW FILE########
__FILENAME__ = picturesforsadchildren
from comics.aggregator.crawler import CrawlerBase
from comics.core.comic_data import ComicDataBase


class ComicData(ComicDataBase):
    name = 'pictures for sad children'
    language = 'en'
    url = 'http://picturesforsadchildren.com/'
    start_date = '2007-01-01'
    end_date = '2012-11-26'
    active = False
    rights = 'John Campbell'


class Crawler(CrawlerBase):
    def crawl(self, pub_date):
        pass  # Comic no longer published

########NEW FILE########
__FILENAME__ = pidjin
from comics.aggregator.crawler import CrawlerBase, CrawlerImage
from comics.core.comic_data import ComicDataBase


class ComicData(ComicDataBase):
    name = "Fredo & Pid'jin"
    language = 'en'
    url = 'http://www.pidjin.net/'
    start_date = '2006-02-19'
    rights = 'Tudor Muscalu & Eugen Erhan'


class Crawler(CrawlerBase):
    history_capable_days = 90
    time_zone = 'US/Pacific'

    def crawl(self, pub_date):
        feed = self.parse_feed('http://feeds.feedburner.com/Pidjin')
        for entry in feed.for_date(pub_date):
            result = []
            urls = entry.content0.src(
                'img[src*="/wp-content/uploads/"]', allow_multiple=True)
            for url in urls:
                if 'ad-RSS' in url or 'reddit-txt' in url:
                    continue
                text = entry.content0.alt('img[src="%s"]' % url)
                result.append(CrawlerImage(url, None, text))
            return result

########NEW FILE########
__FILENAME__ = pinkparts
from comics.aggregator.crawler import CrawlerBase, CrawlerImage
from comics.core.comic_data import ComicDataBase


class ComicData(ComicDataBase):
    name = 'Pink Parts'
    language = 'en'
    url = 'http://pinkpartscomic.com/'
    start_date = '2010-02-01'
    rights = 'Katherine Skipper'


class Crawler(CrawlerBase):
    history_capable_date = '2010-02-01'
    time_zone = 'US/Pacific'

    def crawl(self, pub_date):
        feed = self.parse_feed('http://pinkpartscomic.com/inc/feed.php')
        for entry in feed.for_date(pub_date):
            page = self.parse_page(entry.link)
            url = page.src('img[src*="/img/comic/"]')
            title = entry.title.replace('New comic: ', '')
            return CrawlerImage(url, title)

########NEW FILE########
__FILENAME__ = playervsplayer
from comics.aggregator.crawler import CrawlerBase, CrawlerImage
from comics.core.comic_data import ComicDataBase


class ComicData(ComicDataBase):
    name = 'Player vs Player'
    language = 'en'
    url = 'http://pvponline.com/'
    start_date = '1998-05-04'
    rights = 'Scott R. Kurtz'


class Crawler(CrawlerBase):
    history_capable_days = 10
    schedule = 'Mo,Tu,We,Th,Fr'
    time_zone = 'US/Eastern'

    def crawl(self, pub_date):
        feed = self.parse_feed('http://pvponline.com/feed/')
        for entry in feed.for_date(pub_date):
            if not entry.title.startswith('Comic:'):
                continue
            page = self.parse_page(entry.link)
            url = page.src('.post img[src*="/comic/"]')
            title = entry.title.replace('Comic: ', '')
            if url is not None:
                return CrawlerImage(url, title)

########NEW FILE########
__FILENAME__ = pluggers
from comics.aggregator.crawler import GoComicsComCrawlerBase
from comics.core.comic_data import ComicDataBase


class ComicData(ComicDataBase):
    name = 'Pluggers'
    language = 'en'
    url = 'http://www.gocomics.com/pluggers'
    start_date = '2001-04-08'
    rights = 'Gary Brookins'


class Crawler(GoComicsComCrawlerBase):
    history_capable_date = '2001-04-08'
    schedule = 'Mo,Tu,We,Th,Fr,Sa,Su'
    time_zone = 'US/Eastern'

    def crawl(self, pub_date):
        return self.crawl_helper('Pluggers', pub_date)

########NEW FILE########
__FILENAME__ = poledancingadventures
import re

from comics.aggregator.crawler import CrawlerBase, CrawlerImage
from comics.core.comic_data import ComicDataBase


class ComicData(ComicDataBase):
    name = 'Pole Dancing Adventures'
    language = 'en'
    url = 'http://pole-dancing-adventures.blogspot.com/'
    start_date = '2010-01-28'
    rights = 'Leen Isabel'


class Crawler(CrawlerBase):
    history_capable_date = '2010-01-28'
    time_zone = 'US/Pacific'

    def crawl(self, pub_date):
        feed = self.parse_feed('http://feeds.feedburner.com/blogspot/zumUM')
        for entry in feed.for_date(pub_date):
            results = []

            for url in entry.summary.src('img', allow_multiple=True):
                # Look for NN-*.jpg to differentiate comics from other images
                if re.match('.*\/\d\d-.*\.jpg', url) is not None:
                    results.append(CrawlerImage(url))

            if results:
                results[0].title = entry.title
                return results

########NEW FILE########
__FILENAME__ = pondus
# encoding: utf-8

from comics.aggregator.crawler import CrawlerBase, CrawlerImage
from comics.core.comic_data import ComicDataBase


class ComicData(ComicDataBase):
    name = 'Pondus (db.no)'
    language = 'no'
    url = 'http://www.dagbladet.no/tegneserie/pondus/'
    start_date = '1995-01-01'
    rights = 'Frode Øverli'


class Crawler(CrawlerBase):
    history_capable_days = 30
    schedule = 'Mo,Tu,We,Th,Fr,Sa'
    time_zone = 'Europe/Oslo'

    def crawl(self, pub_date):
        epoch = self.date_to_epoch(pub_date)
        page_url = 'http://www.dagbladet.no/tegneserie/pondus/?%s' % epoch
        page = self.parse_page(page_url)
        url = page.src('img#pondus-stripe')
        return CrawlerImage(url)

########NEW FILE########
__FILENAME__ = pondusbt
# encoding: utf-8

from comics.aggregator.crawler import CrawlerBase, CrawlerImage
from comics.comics.pondus import ComicData as PondusData


class ComicData(PondusData):
    name = 'Pondus (bt.no)'
    url = 'http://www.bt.no/bergenpuls/tegneserier/tegneserier_pondus/'


class Crawler(CrawlerBase):
    history_capable_days = 32
    schedule = 'Mo,Tu,We,Th,Fr,Sa'
    time_zone = 'Europe/Oslo'

    def crawl(self, pub_date):
        url = 'http://www.bt.no/external/cartoon/pondus/%s.gif' % (
            pub_date.strftime('%d%m%y'),)
        return CrawlerImage(url)

########NEW FILE########
__FILENAME__ = pondusno
# encoding: utf-8

from comics.aggregator.crawler import PondusNoCrawlerBase
from comics.comics.pondus import ComicData as PondusData


class ComicData(PondusData):
    name = 'Pondus (pondus.no)'
    url = 'http://www.pondus.no/'
    active = False


class Crawler(PondusNoCrawlerBase):
    def crawl(self, pub_date):
        pass  # Comic no longer published

########NEW FILE########
__FILENAME__ = poorlydrawnlines
from comics.aggregator.crawler import CrawlerBase, CrawlerImage
from comics.core.comic_data import ComicDataBase


class ComicData(ComicDataBase):
    name = 'Poorly Drawn Lines'
    language = 'en'
    url = 'http://poorlydrawnlines.com/'
    start_date = '2011-04-18'
    rights = 'Reza Farazmand, CC BY-NC 3.0'


class Crawler(CrawlerBase):
    history_capable_days = 30
    schedule = 'Mo,We,Fr'
    time_zone = 'US/Pacific'

    # Without User-Agent set, the server returns 403 Forbidden
    headers = {'User-Agent': 'Mozilla/4.0'}

    def crawl(self, pub_date):
        feed = self.parse_feed('http://feeds.feedburner.com/PoorlyDrawnLines')
        for entry in feed.for_date(pub_date):
            url = entry.content0.src('img[src*="/wp-content/uploads/"]')
            title = entry.title
            return CrawlerImage(url, title)

########NEW FILE########
__FILENAME__ = questionablecontent
from comics.aggregator.crawler import CrawlerBase, CrawlerImage
from comics.core.comic_data import ComicDataBase

import re


class ComicData(ComicDataBase):
    name = 'Questionable Content'
    language = 'en'
    url = 'http://questionablecontent.net/'
    start_date = '2003-08-01'
    rights = 'Jeph Jacques'


class Crawler(CrawlerBase):
    history_capable_days = 0
    schedule = 'Mo,Tu,We,Th,Fr'
    time_zone = 'US/Eastern'

    # Without User-Agent set, the server returns 403 Forbidden
    headers = {'User-Agent': 'Mozilla/4.0'}

    def crawl(self, pub_date):
        page = self.parse_page('http://www.questionablecontent.net/')
        url = page.src('#comic img')
        title = None
        page.remove('#news p, #news script')
        text = page.text('#news')
        if text:
            text = re.sub(r'\s{2,}', '\n\n', text).strip()
        return CrawlerImage(url, title, text)

########NEW FILE########
__FILENAME__ = radiogaga
# encoding: utf-8

from comics.aggregator.crawler import PondusNoCrawlerBase
from comics.core.comic_data import ComicDataBase


class ComicData(ComicDataBase):
    name = 'Radio Gaga (pondus.no)'
    language = 'no'
    url = 'http://www.pondus.no/'
    rights = 'Øyvind Sagåsen'
    active = False


class Crawler(PondusNoCrawlerBase):
    def crawl(self, pub_date):
        pass  # Comic no longer published

########NEW FILE########
__FILENAME__ = reallife
from comics.aggregator.crawler import CrawlerBase, CrawlerImage
from comics.core.comic_data import ComicDataBase


class ComicData(ComicDataBase):
    name = 'Real Life'
    language = 'en'
    url = 'http://www.reallifecomics.com/'
    start_date = '1999-11-15'
    rights = 'Greg Dean'


class Crawler(CrawlerBase):
    history_capable_days = 30
    time_zone = 'US/Pacific'

    def crawl(self, pub_date):
        feed = self.parse_feed('http://reallifecomics.com/rss.php?feed=rss2')
        for entry in feed.for_date(pub_date):
            url = entry.summary.src('img[src*="/wp-content/uploads/"]')
            return CrawlerImage(url)

########NEW FILE########
__FILENAME__ = redmeat
from comics.aggregator.crawler import CrawlerBase, CrawlerImage
from comics.core.comic_data import ComicDataBase


class ComicData(ComicDataBase):
    name = 'Red Meat'
    language = 'en'
    url = 'http://www.redmeat.com/'
    start_date = '1996-06-10'
    rights = 'Max Cannon'


class Crawler(CrawlerBase):
    history_capable_date = '1996-06-10'
    schedule = 'Tu'
    time_zone = 'US/Eastern'

    def crawl(self, pub_date):
        page_url = 'http://www.redmeat.com/redmeat/%s/' % (
            pub_date.strftime('%Y-%m-%d'))
        page = self.parse_page(page_url)
        url = page.src('#weeklyStrip img')
        title = page.alt('#weeklyStrip img')
        return CrawlerImage(url, title)

########NEW FILE########
__FILENAME__ = reveland
from comics.aggregator.crawler import CrawlerBase, CrawlerImage
from comics.core.comic_data import ComicDataBase


class ComicData(ComicDataBase):
    name = 'Reveland'
    language = 'no'
    url = 'http://reveland.nettserier.no/'
    start_date = '2007-03-20'
    end_date = '2013-04-17'
    active = False
    rights = 'Jorunn Hanto-Haugse'


class Crawler(CrawlerBase):
    def crawl(self, pub_date):
        pass  # Comic no longer published

########NEW FILE########
__FILENAME__ = rhymeswithwitch
from comics.aggregator.crawler import CrawlerBase
from comics.core.comic_data import ComicDataBase


class ComicData(ComicDataBase):
    name = 'rhymes with witch'
    language = 'en'
    url = 'http://www.rhymes-with-witch.com/'
    start_date = '2006-08-09'
    end_date = '2011-11-21'
    active = False
    rights = 'r*k*milholland'


class Crawler(CrawlerBase):
    def crawl(self, pub_date):
        pass  # Comic no longer published

########NEW FILE########
__FILENAME__ = rocky
from comics.aggregator.crawler import CrawlerBase, CrawlerImage
from comics.core.comic_data import ComicDataBase


class ComicData(ComicDataBase):
    name = 'Rocky (db.no)'
    language = 'no'
    url = 'http://www.dagbladet.no/tegneserie/rocky/'
    start_date = '1998-01-01'
    rights = 'Martin Kellerman'


class Crawler(CrawlerBase):
    history_capable_days = 14
    schedule = 'Mo,Tu,We,Th,Fr,Sa,Su'
    time_zone = 'Europe/Oslo'

    def crawl(self, pub_date):
        epoch = self.date_to_epoch(pub_date)
        url = 'http://www.dagbladet.no/tegneserie/rockyarkiv/serve.php?%s' % (
            epoch,)
        return CrawlerImage(url)

########NEW FILE########
__FILENAME__ = rockybt
from comics.aggregator.crawler import CrawlerBase, CrawlerImage
from comics.comics.rocky import ComicData as RockyData


class ComicData(RockyData):
    name = 'Rocky (bt.no)'
    url = 'http://www.bt.no/bergenpuls/tegneserier/tegneserier_rocky/'


class Crawler(CrawlerBase):
    history_capable_days = 162
    schedule = 'Mo,Tu,We,Th,Fr,Sa'
    time_zone = 'Europe/Oslo'

    def crawl(self, pub_date):
        url = 'http://www.bt.no/external/cartoon/rocky/%s.gif' % (
            pub_date.strftime('%d%m%y'),)
        return CrawlerImage(url)

########NEW FILE########
__FILENAME__ = romanticallyapocalyptic
from comics.aggregator.crawler import CrawlerBase, CrawlerImage
from comics.core.comic_data import ComicDataBase


class ComicData(ComicDataBase):
    name = 'Romantically Apocalyptic'
    language = 'en'
    url = 'http://www.romanticallyapocalyptic.com/'
    rights = 'Vitaly S. Alexius'


class Crawler(CrawlerBase):
    history_capable_days = None
    schedule = None
    time_zone = 'America/Toronto'

    def crawl(self, pub_date):
        page = self.parse_page('http://www.romanticallyapocalyptic.com/')
        urls = page.src('img[src*="/art/"]', allow_multiple=True)
        for url in urls:
            if 'thumb' not in url:
                return CrawlerImage(url)

########NEW FILE########
__FILENAME__ = roseisrose
from comics.aggregator.crawler import GoComicsComCrawlerBase
from comics.core.comic_data import ComicDataBase


class ComicData(ComicDataBase):
    name = 'Rose Is Rose'
    language = 'en'
    url = 'http://www.gocomics.com/roseisrose/'
    start_date = '1984-10-02'
    rights = 'Pat Brady'


class Crawler(GoComicsComCrawlerBase):
    history_capable_date = '1995-10-09'
    schedule = 'Mo,Tu,We,Th,Fr,Sa,Su'
    time_zone = 'US/Eastern'

    def crawl(self, pub_date):
        return self.crawl_helper('Rose is Rose', pub_date)

########NEW FILE########
__FILENAME__ = rutetid
# encoding: utf-8

from comics.aggregator.crawler import CrawlerBase
from comics.core.comic_data import ComicDataBase


class ComicData(ComicDataBase):
    name = 'Rutetid'
    language = 'no'
    url = 'http://www.dagbladet.no/tegneserie/rutetid/'
    active = False
    rights = 'Frode Øverli'


class Crawler(CrawlerBase):
    def crawl(self, pub_date):
        pass  # Comic no longer published

########NEW FILE########
__FILENAME__ = satw
from comics.aggregator.crawler import CrawlerBase, CrawlerImage
from comics.core.comic_data import ComicDataBase


class ComicData(ComicDataBase):
    name = 'Scandinavia and the World'
    language = 'en'
    url = 'http://www.satwcomic.com/'
    start_date = '2009-06-01'
    rights = 'Humon'


class Crawler(CrawlerBase):
    schedule = 'We'
    time_zone = 'Europe/Copenhagen'

    def crawl(self, pub_date):
        feed = self.parse_feed('http://feeds.feedburner.com/satwcomic')
        for entry in feed.all():
            page = self.parse_page(entry.link)
            url = page.src('.comicmid img[src*="/art/"]')
            title = entry.title
            page.remove('.comicdesc .stand_high h1')
            page.remove('.comicdesc .stand_high small')
            text = page.text('.comicdesc .stand_high').strip()
            return CrawlerImage(url, title, text)

########NEW FILE########
__FILENAME__ = savagechickens
from comics.aggregator.crawler import CrawlerBase, CrawlerImage
from comics.core.comic_data import ComicDataBase


class ComicData(ComicDataBase):
    name = 'Savage Chickens'
    language = 'en'
    url = 'http://www.savagechickens.com/'
    start_date = '2005-01-31'
    rights = 'Dave Savage'


class Crawler(CrawlerBase):
    history_capable_days = 14
    schedule = 'Mo,Tu,We,Th,Fr'
    time_zone = 'US/Pacific'

    def crawl(self, pub_date):
        feed = self.parse_feed('http://www.savagechickens.com/feed')
        for entry in feed.for_date(pub_date):
            if 'Cartoons' not in entry.tags:
                print 'skipping'
            url = entry.content0.src('img[src*="/wp-content/"]')
            title = entry.title
            return CrawlerImage(url, title)

########NEW FILE########
__FILENAME__ = scenesfromamultiverse
from comics.aggregator.crawler import CrawlerBase, CrawlerImage
from comics.core.comic_data import ComicDataBase


class ComicData(ComicDataBase):
    name = 'Scenes from a Multiverse'
    language = 'en'
    url = 'http://amultiverse.com/'
    start_date = '2010-06-14'
    rights = 'Jonathan Rosenberg'


class Crawler(CrawlerBase):
    history_capable_days = 40
    time_zone = 'US/Eastern'

    def crawl(self, pub_date):
        feed = self.parse_feed('http://amultiverse.com/feed/')
        for entry in feed.for_date(pub_date):
            url = entry.content0.src('a[rel="bookmark"] img')
            title = entry.title

            # Text comes in multiple paragraphs: parse out all the text
            text = ''
            for paragraph in entry.content0.text('p', allow_multiple=True):
                text += paragraph + '\n\n'
            text = text.strip()

            return CrawlerImage(url, title, text)

########NEW FILE########
__FILENAME__ = schlockmercenary
from comics.aggregator.crawler import CrawlerBase, CrawlerImage
from comics.core.comic_data import ComicDataBase


class ComicData(ComicDataBase):
    name = 'Schlock Mercenary'
    language = 'en'
    url = 'http://www.schlockmercenary.com/'
    start_date = '2000-06-12'
    rights = 'Howard Tayler'


class Crawler(CrawlerBase):
    history_capable_date = '2000-06-12'
    schedule = 'Mo,Tu,We,Th,Fr,Sa,Su'
    time_zone = 'US/Mountain'

    def crawl(self, pub_date):
        page_url = 'http://www.schlockmercenary.com/%s' % pub_date.strftime(
            '%Y-%m-%d')
        page = self.parse_page(page_url)
        result = []
        for url in page.src('#comic img', allow_multiple=True):
            result.append(CrawlerImage(url))
        return result

########NEW FILE########
__FILENAME__ = seemikedraw
from comics.aggregator.crawler import CrawlerBase, CrawlerImage
from comics.core.comic_data import ComicDataBase


class ComicData(ComicDataBase):
    name = 'seemikedraw'
    language = 'en'
    url = 'http://seemikedraw.com.au/'
    start_date = '2007-07-31'
    rights = 'Mike Jacobsen'


class Crawler(CrawlerBase):
    history_capable_days = 180
    time_zone = 'Australia/Sydney'

    # Without User-Agent set, the server returns 403 Forbidden
    headers = {'User-Agent': 'Mozilla/4.0'}

    def crawl(self, pub_date):
        feed = self.parse_feed('http://seemikedraw.com.au/feed')
        for entry in feed.for_date(pub_date):
            url = entry.content0.src('img[src*="/wp-content/uploads/"]')
            title = entry.title
            return CrawlerImage(url, title)

########NEW FILE########
__FILENAME__ = sequentialart
from comics.aggregator.crawler import CrawlerBase, CrawlerImage
from comics.core.comic_data import ComicDataBase


class ComicData(ComicDataBase):
    name = 'Sequential Art'
    language = 'en'
    url = 'http://www.collectedcurios.com/'
    start_date = '2005-06-13'
    rights = 'Phillip M. Jackson'


class Crawler(CrawlerBase):
    schedule = 'We'
    time_zone = 'Europe/London'

    def crawl(self, pub_date):
        page = self.parse_page(
            'http://www.collectedcurios.com/sequentialart.php')
        url = page.src('img#strip')
        return CrawlerImage(url)

########NEW FILE########
__FILENAME__ = sheldon
from comics.aggregator.crawler import CrawlerBase, CrawlerImage
from comics.core.comic_data import ComicDataBase


class ComicData(ComicDataBase):
    name = 'Sheldon'
    language = 'en'
    url = 'http://www.sheldoncomics.com/'
    start_date = '2001-11-30'
    rights = 'Dave Kellett'


class Crawler(CrawlerBase):
    history_capable_days = 14
    schedule = 'Mo,Tu,We,Th,Fr'
    time_zone = 'US/Pacific'

    def crawl(self, pub_date):
        feed = self.parse_feed('http://cdn.sheldoncomics.com/rss.xml')
        for entry in feed.for_date(pub_date):
            if 'Comic' not in entry.tags:
                continue
            url = entry.content0.src('img[src*="/strips/"]')
            return CrawlerImage(url)

########NEW FILE########
__FILENAME__ = shortpacked
from comics.aggregator.crawler import CrawlerBase, CrawlerImage
from comics.core.comic_data import ComicDataBase


class ComicData(ComicDataBase):
    name = 'Shortpacked'
    language = 'en'
    url = 'http://www.shortpacked.com/'
    start_date = '2005-01-17'
    rights = 'David Willis'


class Crawler(CrawlerBase):
    schedule = 'Mo,Tu,We,Th,Fr'
    history_capable_days = 32
    time_zone = 'US/Eastern'

    def crawl(self, pub_date):
        feed = self.parse_feed('http://www.shortpacked.com/rss.php')
        for entry in feed.for_date(pub_date):
            if 'blog.php' in entry.link:
                continue
            page = self.parse_page(entry.link)
            url = page.src('img#comic')
            title = entry.title.replace('Shortpacked! - ', '')
            text = page.title('img#comic')
            return CrawlerImage(url, title, text)

########NEW FILE########
__FILENAME__ = sinfest
from comics.aggregator.crawler import CrawlerBase, CrawlerImage
from comics.core.comic_data import ComicDataBase


class ComicData(ComicDataBase):
    name = 'Sinfest'
    language = 'en'
    url = 'http://www.sinfest.net/'
    start_date = '2001-01-17'
    rights = 'Tatsuya Ishida'


class Crawler(CrawlerBase):
    history_capable_date = '2001-01-17'
    schedule = 'Mo,Tu,We,Th,Fr,Sa,Su'
    time_zone = 'US/Eastern'

    def crawl(self, pub_date):
        url = 'http://www.sinfest.net/comikaze/comics/%s.gif' % (
            pub_date.strftime('%Y-%m-%d'),)
        return CrawlerImage(url)

########NEW FILE########
__FILENAME__ = slagoon
from comics.aggregator.crawler import CrawlerBase, CrawlerImage
from comics.core.comic_data import ComicDataBase


class ComicData(ComicDataBase):
    name = "Sherman's Lagoon"
    language = 'en'
    url = 'http://shermanslagoon.com/'
    start_date = '1991-05-13'
    rights = 'Jim Toomey'


class Crawler(CrawlerBase):
    history_capable_date = '2003-12-29'
    schedule = 'Mo,Tu,We,Th,Fr,Sa,Su'
    time_zone = 'US/Eastern'

    def crawl(self, pub_date):
        page_url = 'http://shermanslagoon.com/comics/%s-%s-%s/' % (
            pub_date.strftime('%B').lower(),
            int(pub_date.strftime('%d')),
            pub_date.strftime('%Y'))
        page = self.parse_page(page_url)
        url = page.src('.entry-content img')
        return CrawlerImage(url)

########NEW FILE########
__FILENAME__ = smbc
from comics.aggregator.crawler import CrawlerBase, CrawlerImage
from comics.core.comic_data import ComicDataBase


class ComicData(ComicDataBase):
    name = 'Saturday Morning Breakfast Cereal'
    language = 'en'
    url = 'http://www.smbc-comics.com/'
    start_date = '2002-09-05'
    rights = 'Zach Weiner'


class Crawler(CrawlerBase):
    history_capable_days = 10
    schedule = 'Mo,Tu,We,Th,Fr,Sa,Su'
    time_zone = 'US/Pacific'

    def crawl(self, pub_date):
        feed = self.parse_feed('http://feeds.feedburner.com/smbc-comics/PvLb')
        for entry in feed.for_date(pub_date):
            url_1 = entry.summary.src('img[src*="/comics/"]')
            url_2 = url_1.replace('.png', 'after.gif')
            return [CrawlerImage(url_1), CrawlerImage(url_2)]

########NEW FILE########
__FILENAME__ = somethingofthatilk
from comics.aggregator.crawler import CrawlerBase, CrawlerImage
from comics.core.comic_data import ComicDataBase


class ComicData(ComicDataBase):
    name = 'Something of that Ilk'
    language = 'en'
    url = 'http://www.somethingofthatilk.com/'
    start_date = '2011-02-19'
    rights = 'Ty Devries'


class Crawler(CrawlerBase):
    time_zone = 'US/Eastern'

    def crawl(self, pub_date):
        page = self.parse_page('http://www.somethingofthatilk.com/')
        url = page.src('img[src*="/comics/"]')
        title = page.alt('img[src*="/comics/"]')
        return CrawlerImage(url, title)

########NEW FILE########
__FILENAME__ = somethingpositive
from comics.aggregator.crawler import CrawlerBase, CrawlerImage
from comics.core.comic_data import ComicDataBase


class ComicData(ComicDataBase):
    name = 'Something Positive'
    language = 'en'
    url = 'http://www.somethingpositive.net/'
    start_date = '2001-12-19'
    rights = 'R. K. Milholland'


class Crawler(CrawlerBase):
    history_capable_date = '2001-12-19'
    schedule = 'Mo,Tu,We,Th,Fr'
    time_zone = 'US/Central'

    def crawl(self, pub_date):
        url = 'http://www.somethingpositive.net/sp%s.png' % (
            pub_date.strftime('%m%d%Y'),)
        return CrawlerImage(url)

########NEW FILE########
__FILENAME__ = spaceavalanche
from comics.aggregator.crawler import CrawlerBase, CrawlerImage
from comics.core.comic_data import ComicDataBase


class ComicData(ComicDataBase):
    name = 'Space Avalanche'
    language = 'en'
    url = 'http://www.spaceavalanche.com/'
    start_date = '2009-02-02'
    rights = 'Eoin Ryan'


class Crawler(CrawlerBase):
    history_capable_days = 365
    time_zone = 'Europe/Dublin'

    def crawl(self, pub_date):
        feed = self.parse_feed('http://feeds.feedburner.com/SpaceAvalanche')
        for entry in feed.for_date(pub_date):
            if 'COMIC ARCHIVE' not in entry.tags:
                continue
            urls = entry.content0.src(
                'img[src*="/wp-content/uploads/"]', allow_multiple=True)
            if not urls:
                continue
            url = urls[0]
            title = entry.title
            return CrawlerImage(url, title)

########NEW FILE########
__FILENAME__ = spikedmath
from comics.aggregator.crawler import CrawlerBase, CrawlerImage
from comics.core.comic_data import ComicDataBase


class ComicData(ComicDataBase):
    name = 'Spiked Math'
    language = 'en'
    url = 'http://www.spikedmath.com/'
    start_date = '2009-08-24'
    rights = 'Mike, CC BY-NC-SA 2.5'


class Crawler(CrawlerBase):
    history_capable_days = 20
    time_zone = 'US/Mountain'

    def crawl(self, pub_date):
        feed = self.parse_feed('http://feeds.feedburner.com/SpikedMath')
        for entry in feed.for_date(pub_date):
            page = self.parse_page(entry.link)
            result = []
            for url in page.src(
                    'div.asset-body img[src*="/comics/"]',
                    allow_multiple=True):
                result.append(CrawlerImage(url))
            if result:
                result[0].title = entry.title
            return result

########NEW FILE########
__FILENAME__ = stickycomics
from comics.aggregator.crawler import CrawlerBase, CrawlerImage
from comics.core.comic_data import ComicDataBase


class ComicData(ComicDataBase):
    name = 'Sticky Comics'
    language = 'en'
    url = 'http://www.stickycomics.com/'
    start_date = '2006-05-04'
    rights = 'Christiann MacAuley'


class Crawler(CrawlerBase):
    history_capable_days = 60
    time_zone = 'US/Mountain'

    def crawl(self, pub_date):
        feed = self.parse_feed('http://www.stickycomics.com/feed')
        for entry in feed.for_date(pub_date):
            if 'comics' not in entry.tags:
                continue
            url = entry.content0.src('img[src*="/wp-content/uploads/"]')
            title = entry.title
            text = entry.content0.alt('img[src*="/wp-content/uploads/"]')
            return CrawlerImage(url, title, text)

########NEW FILE########
__FILENAME__ = stickydillybuns
from comics.aggregator.crawler import CrawlerBase, CrawlerImage
from comics.core.comic_data import ComicDataBase


class ComicData(ComicDataBase):
    name = 'Sticky Dilly Buns'
    language = 'en'
    url = 'http://www.stickydillybuns.com/'
    start_date = '2013-01-07'
    rights = 'G. Lagace'


class Crawler(CrawlerBase):
    history_capable_days = 50
    schedule = 'Mo,Fr'
    time_zone = 'US/Eastern'

    def crawl(self, pub_date):
        feed = self.parse_feed('http://www.stickydillybuns.com/comic.rss')
        for entry in feed.for_date(pub_date):
            title = entry.title.replace('Sticky Dilly Buns - ', '')
            page_url = entry.link.replace(' ', '+')
            page = self.parse_page(page_url)
            url = page.src('#comic img')
            return CrawlerImage(url, title)

########NEW FILE########
__FILENAME__ = stuffnoonetoldme
from comics.aggregator.crawler import CrawlerBase
from comics.core.comic_data import ComicDataBase


class ComicData(ComicDataBase):
    name = 'Stuff No One Told Me'
    language = 'en'
    url = 'http://stuffnoonetoldme.blogspot.com/'
    start_date = '2010-05-31'
    end_date = '2011-10-18'
    active = False
    rights = 'Alex Noriega'


class Crawler(CrawlerBase):
    def crawl(self, pub_date):
        pass  # No longer published

########NEW FILE########
__FILENAME__ = subnormality
from comics.aggregator.crawler import CrawlerBase, CrawlerImage
from comics.core.comic_data import ComicDataBase


class ComicData(ComicDataBase):
    name = 'Subnormality'
    language = 'en'
    url = 'http://www.viruscomix.com/subnormality.html'
    start_date = '2007-01-01'
    rights = 'Winston Rowntree'


class Crawler(CrawlerBase):
    history_capable_date = '2008-11-25'
    time_zone = 'US/Eastern'

    def crawl(self, pub_date):
        feed = self.parse_feed('http://www.viruscomix.com/rss.xml')
        for entry in feed.for_date(pub_date):
            page = self.parse_page(entry.link)
            url = page.src('body > img[src$=".jpg"]')
            title = page.text('title')
            text = page.title('body > img[src$=".jpg"]')
            return CrawlerImage(url, title, text)

########NEW FILE########
__FILENAME__ = supereffective
from comics.aggregator.crawler import CrawlerBase, CrawlerImage
from comics.core.comic_data import ComicDataBase


class ComicData(ComicDataBase):
    name = 'Super Effective'
    language = 'en'
    url = 'http://www.vgcats.com/super/'
    start_date = '2008-04-23'
    rights = 'Scott Ramsoomair'


class Crawler(CrawlerBase):
    history_capable_date = '2008-04-23'
    time_zone = 'US/Eastern'

     # Without User-Agent set, the server returns empty responses
    headers = {'User-Agent': 'Mozilla/4.0'}

    def crawl(self, pub_date):
        url = 'http://www.vgcats.com/super/images/%s.gif' % (
            pub_date.strftime('%y%m%d'),)
        return CrawlerImage(url)

########NEW FILE########
__FILENAME__ = superpoop
from comics.aggregator.crawler import CrawlerBase
from comics.core.comic_data import ComicDataBase


class ComicData(ComicDataBase):
    name = 'Superpoop'
    language = 'en'
    url = 'http://www.superpoop.com/'
    active = False
    start_date = '2008-01-01'
    end_date = '2010-12-17'
    rights = 'Drew'


class Crawler(CrawlerBase):
    def crawl(self, pub_date):
        pass  # Comic no longer published

########NEW FILE########
__FILENAME__ = tankmcnamara
from comics.aggregator.crawler import GoComicsComCrawlerBase
from comics.core.comic_data import ComicDataBase


class ComicData(ComicDataBase):
    name = 'Tank McNamara'
    language = 'en'
    url = 'http://www.gocomics.com/tankmcnamara'
    start_date = '1998-01-01'
    rights = 'Wiley Miller'


class Crawler(GoComicsComCrawlerBase):
    history_capable_date = '1998-01-01'
    schedule = 'Mo,Tu,We,Th,Fr,Sa,Su'
    time_zone = 'US/Mountain'

    def crawl(self, pub_date):
        return self.crawl_helper('Tank McNamara', pub_date)

########NEW FILE########
__FILENAME__ = tehgladiators
from comics.aggregator.crawler import CrawlerBase, CrawlerImage
from comics.core.comic_data import ComicDataBase


class ComicData(ComicDataBase):
    name = 'Teh Gladiators'
    language = 'en'
    url = 'http://www.tehgladiators.com/'
    start_date = '2008-03-18'
    rights = 'Uros Jojic & Borislav Grabovic'


class Crawler(CrawlerBase):
    history_capable_days = 90
    schedule = 'We'
    time_zone = 'Europe/Belgrade'

    def crawl(self, pub_date):
        feed = self.parse_feed('http://www.tehgladiators.com/rss.xml')
        for entry in feed.for_date(pub_date):
            page = self.parse_page(entry.link)
            url = page.src('img[alt^="Teh Gladiators Webcomic"]')
            title = entry.title
            return CrawlerImage(url, title)

########NEW FILE########
__FILENAME__ = theboondocks
from comics.aggregator.crawler import GoComicsComCrawlerBase
from comics.core.comic_data import ComicDataBase


class ComicData(ComicDataBase):
    name = 'The Boondocks'
    language = 'en'
    url = 'http://www.gocomics.com/theboondocks'
    start_date = '1999-04-19'
    rights = 'Aaron McGruder'


class Crawler(GoComicsComCrawlerBase):
    history_capable_date = '1999-04-19'
    schedule = 'Mo,Tu,We,Th,Fr,Sa,Su'
    time_zone = 'US/Mountain'

    def crawl(self, pub_date):
        return self.crawl_helper('The Boondocks', pub_date, 'boondocks')

########NEW FILE########
__FILENAME__ = thechalkboardmanifesto
from comics.aggregator.crawler import CrawlerBase, CrawlerImage
from comics.core.comic_data import ComicDataBase


class ComicData(ComicDataBase):
    name = 'The Chalkboard Manifesto'
    language = 'en'
    url = 'http://www.chalkboardmanifesto.com/'
    start_date = '2005-05-01'
    rights = 'Shawn McDonald'


class Crawler(CrawlerBase):
    history_capable_days = 40
    time_zone = 'US/Pacific'

    def crawl(self, pub_date):
        feed = self.parse_feed(
            'http://feeds.feedburner.com/TheChalkboardManifesto')
        for entry in feed.for_date(pub_date):
            url = entry.summary.src('img[alt="comic"]')
            title = entry.title
            return CrawlerImage(url, title)

########NEW FILE########
__FILENAME__ = thedreamer
from comics.aggregator.crawler import CrawlerBase, CrawlerImage
from comics.core.comic_data import ComicDataBase


class ComicData(ComicDataBase):
    name = 'The Dreamer'
    language = 'en'
    url = 'http://thedreamercomic.com/'
    rights = 'Lora Innes'


class Crawler(CrawlerBase):
    time_zone = 'US/Eastern'

    def crawl(self, pub_date):
        page = self.parse_page('http://thedreamercomic.com/comic.php')
        url = page.src('img[src*="issues/"]')
        title = page.alt('img[src*="issues/"]')
        return CrawlerImage(url, title)

########NEW FILE########
__FILENAME__ = thegamercat
from comics.aggregator.crawler import CrawlerBase, CrawlerImage
from comics.core.comic_data import ComicDataBase


class ComicData(ComicDataBase):
    name = 'The Gamer Cat'
    language = 'en'
    url = 'http://thegamercat.com/'
    start_date = '2011-06-10'
    rights = 'Celesse'


class Crawler(CrawlerBase):
    history_capable_days = 180
    time_zone = 'US/Central'

    # Without User-Agent set, the server returns 403 Forbidden
    headers = {'User-Agent': 'Mozilla/4.0'}

    def crawl(self, pub_date):
        feed = self.parse_feed('http://thegamercat.com/feed/')
        for entry in feed.for_date(pub_date):
            if 'Comics' not in entry.tags:
                continue
            url = entry.summary.src('img')
            if not url:
                continue
            url = url.replace('/comics-rss/', '/comics/')
            title = entry.title
            text = '\n\n'.join(entry.content0.text(
                'p', allow_multiple=True)).strip()
            return CrawlerImage(url, title, text)

########NEW FILE########
__FILENAME__ = thegutters
import re

from comics.aggregator.crawler import CrawlerBase, CrawlerImage
from comics.core.comic_data import ComicDataBase


class ComicData(ComicDataBase):
    name = 'The Gutters'
    language = 'en'
    url = 'http://the-gutters.com/'
    rights = 'Blind Ferret Entertainment'


class Crawler(CrawlerBase):
    history_capable_days = 180
    schedule = 'Tu,Fr'
    time_zone = 'America/Montreal'

    def crawl(self, pub_date):
        feed = self.parse_feed('http://feeds.feedburner.com/TheGutters')
        for entry in feed.for_date(pub_date):
            title = entry.title
            url = entry.summary.src('img[src*="/wp-content/uploads/"]')
            if not url:
                continue
            url = re.sub('-\d+x\d+.jpg', '.jpg', url)
            return CrawlerImage(url, title)

########NEW FILE########
__FILENAME__ = theidlestate
from comics.aggregator.crawler import CrawlerBase, CrawlerImage
from comics.core.comic_data import ComicDataBase


class ComicData(ComicDataBase):
    name = 'The Idle State'
    language = 'en'
    url = 'http://www.theidlestate.com/'
    start_date = '2011-07-18'
    end_date = '2012-07-05'
    active = False
    rights = 'Nick Wright'


class Crawler(CrawlerBase):
    def crawl(self, pub_date):
        pass  # Comic no longer published

########NEW FILE########
__FILENAME__ = thisishistorictimes
from comics.aggregator.crawler import CrawlerBase, CrawlerImage
from comics.core.comic_data import ComicDataBase


class ComicData(ComicDataBase):
    name = 'This is Historic Times'
    language = 'en'
    url = 'http://www.thisishistorictimes.com/'
    start_date = '2006-01-01'
    rights = 'Terrence Nowicki, Jr.'


class Crawler(CrawlerBase):
    history_capable_days = 60
    time_zone = 'US/Pacific'

    def crawl(self, pub_date):
        feed = self.parse_feed('http://thisishistorictimes.com/feed/')
        for entry in feed.for_date(pub_date):
            page = self.parse_page(entry.link)
            url = page.src('img[src*="/wp-content/uploads/"]')
            title = entry.title
            return CrawlerImage(url, title)

########NEW FILE########
__FILENAME__ = threepanelsoul
from comics.aggregator.crawler import CrawlerBase, CrawlerImage
from comics.core.comic_data import ComicDataBase


class ComicData(ComicDataBase):
    name = 'Three Panel Soul'
    language = 'en'
    url = 'http://www.threepanelsoul.com/'
    start_date = '2006-11-05'
    rights = 'Ian McConville & Matt Boyd'


class Crawler(CrawlerBase):
    history_capable_days = 180
    time_zone = 'US/Eastern'

    def crawl(self, pub_date):
        feed = self.parse_feed('http://threepanelsoul.com/feed/')
        for entry in feed.for_date(pub_date):
            title = entry.title
            url = entry.content0.src('img[src*="/comics-rss/"]')
            if url is not None:
                url = url.replace('-rss', '')
                return CrawlerImage(url, title)

########NEW FILE########
__FILENAME__ = threewordphrase
from comics.aggregator.crawler import CrawlerBase, CrawlerImage
from comics.core.comic_data import ComicDataBase


class ComicData(ComicDataBase):
    name = 'Three Word Phrase'
    language = 'en'
    url = 'http://www.threewordphrase.com/'
    start_date = '2010-07-13'
    rights = 'Ryan Pequin'


class Crawler(CrawlerBase):
    history_capable_days = 0
    time_zone = 'US/Pacific'

    def crawl(self, pub_date):
         # Thee feed has broken dates, so we fetch only the latest one
        feed = self.parse_feed('http://www.threewordphrase.com/rss.xml')
        if feed.all():
            entry = feed.all()[0]
            url = entry.link.replace('.htm', '.gif')
            title = entry.title
            text = entry.summary.root.text
            return CrawlerImage(url, title, text)

########NEW FILE########
__FILENAME__ = timetrabble
from comics.aggregator.crawler import CrawlerBase, CrawlerImage
from comics.core.comic_data import ComicDataBase


class ComicData(ComicDataBase):
    name = 'Time Trabble'
    language = 'en'
    url = 'http://timetrabble.com/'
    start_date = '2010-05-09'
    rights = 'Mikey Heller'


class Crawler(CrawlerBase):
    history_capable_days = 90
    time_zone = 'US/Eastern'

    def crawl(self, pub_date):
        feed = self.parse_feed('http://timetrabble.com/?feed=rss2')
        for entry in feed.for_date(pub_date):
            url = entry.summary.src('img.comicthumbnail')
            if not url:
                continue
            url = url.replace('comics-rss', 'comics')
            title = entry.title
            return CrawlerImage(url, title)

########NEW FILE########
__FILENAME__ = tommyogtigern
from comics.aggregator.crawler import CrawlerBase, CrawlerImage
from comics.core.comic_data import ComicDataBase


class ComicData(ComicDataBase):
    name = 'Tommy og Tigern'
    language = 'no'
    url = 'http://heltnormalt.no/tommytigern'
    rights = 'Bill Watterson'


class Crawler(CrawlerBase):
    history_capable_date = '2013-02-01'
    schedule = 'Mo,Tu,We,Th,Fr,Sa,Su'
    time_zone = 'Europe/Oslo'

    def crawl(self, pub_date):
        url = 'http://heltnormalt.no/img/tommytigern/%s.jpg' % (
            pub_date.strftime('%Y/%m/%d'))
        return CrawlerImage(url)

########NEW FILE########
__FILENAME__ = toothpastefordinner
from comics.aggregator.crawler import CrawlerBase, CrawlerImage
from comics.core.comic_data import ComicDataBase


class ComicData(ComicDataBase):
    name = 'Toothpaste for Dinner'
    language = 'en'
    url = 'http://www.toothpastefordinner.com/'
    start_date = '2004-01-01'
    rights = 'Drew'


class Crawler(CrawlerBase):
    history_capable_days = 21
    schedule = 'Mo,Tu,We,Th,Fr,Sa,Su'
    time_zone = 'US/Eastern'

    # Without User-Agent set, the server returns 302 Found
    headers = {'User-Agent': 'Mozilla/4.0'}

    def crawl(self, pub_date):
        feed = self.parse_feed(
            'http://www.toothpastefordinner.com/rss/rss.php')
        for entry in feed.for_date(pub_date):
            page = self.parse_page(entry.link)
            url = page.src(
                'img[src*="/%s/"]' % pub_date.strftime('%m%d%y'))
            title = entry.title
            return CrawlerImage(url, title)

########NEW FILE########
__FILENAME__ = treadingground
from comics.aggregator.crawler import CrawlerBase
from comics.core.comic_data import ComicDataBase


class ComicData(ComicDataBase):
    name = 'Treading Ground'
    language = 'en'
    url = 'http://www.treadingground.com/'
    active = False
    start_date = '2003-10-12'
    rights = 'Nick Wright'


class Crawler(CrawlerBase):
    def crawl(self, pub_date):
        pass  # Comic no longer published

########NEW FILE########
__FILENAME__ = truthfacts
# encoding: utf-8

from comics.aggregator.crawler import CrawlerBase, CrawlerImage
from comics.core.comic_data import ComicDataBase


class ComicData(ComicDataBase):
    name = 'Truth Facts'
    language = 'no'
    url = 'http://heltnormalt.no/truthfacts'


class Crawler(CrawlerBase):
    history_capable_date = '2013-02-12'
    schedule = 'Mo,Tu,We,Th,Fr'
    time_zone = 'Europe/Oslo'

    def crawl(self, pub_date):
        url = 'http://heltnormalt.no/img/truth_facts/%s.jpg' % (
            pub_date.strftime('%Y/%m/%d'))
        return CrawlerImage(url)

########NEW FILE########
__FILENAME__ = undeclaredmajor
from comics.aggregator.crawler import CrawlerBase
from comics.core.comic_data import ComicDataBase


class ComicData(ComicDataBase):
    name = 'Undeclared Major'
    language = 'en'
    url = 'http://www.undeclaredcomics.com/'
    start_date = '2011-08-09'
    end_date = '2012-09-11'
    active = False
    rights = 'Belal'


class Crawler(CrawlerBase):
    def crawl(self, pub_date):
        pass  # Comic no longer published

########NEW FILE########
__FILENAME__ = userfriendly
from comics.aggregator.crawler import CrawlerBase, CrawlerImage
from comics.core.comic_data import ComicDataBase


class ComicData(ComicDataBase):
    name = 'User Friendly'
    language = 'en'
    url = 'http://www.userfriendly.org/'
    start_date = '1997-11-17'
    rights = 'J.D. "Illiad" Frazer'


class Crawler(CrawlerBase):
    has_rerun_releases = True
    history_capable_date = '1997-11-17'
    schedule = 'Mo,Tu,We,Th,Fr,Sa,Su'
    time_zone = 'America/Vancouver'

    def crawl(self, pub_date):
        page_url = 'http://ars.userfriendly.org/cartoons/?id=%s' % (
            pub_date.strftime('%Y%m%d'),)
        page = self.parse_page(page_url)
        url = page.src('img[alt^="Strip for"]')
        return CrawlerImage(url)

########NEW FILE########
__FILENAME__ = utensokker
# encoding: utf-8

from comics.aggregator.crawler import CrawlerBase, CrawlerImage
from comics.core.comic_data import ComicDataBase


class ComicData(ComicDataBase):
    name = 'Uten Sokker'
    language = 'no'
    url = 'http://utensokker.nettserier.no/'
    start_date = '2009-07-14'
    rights = 'Bjørnar Grandalen'


class Crawler(CrawlerBase):
    history_capable_date = '2009-07-14'
    time_zone = 'Europe/Oslo'

    def crawl(self, pub_date):
        url = 'http://utensokker.nettserier.no/_striper/utensokker-%s.jpg' % (
            self.date_to_epoch(pub_date),)
        page_url = 'http://utensokker.nettserier.no/%s' % (
            pub_date.strftime('%Y/%m/%d'))
        page = self.parse_page(page_url)
        title = page.alt('img[src*="/_striper/"]')
        return CrawlerImage(url, title)

########NEW FILE########
__FILENAME__ = uvod
from comics.aggregator.crawler import CrawlerBase, CrawlerImage
from comics.core.comic_data import ComicDataBase


class ComicData(ComicDataBase):
    name = 'The Unspeakable Vault (of Doom)'
    language = 'en'
    url = 'http://www.goominet.com/unspeakable-vault/'
    rights = 'Francois Launet'


class Crawler(CrawlerBase):
    history_capable_days = 180
    time_zone = 'Europe/Paris'

    def crawl(self, pub_date):
        feed = self.parse_feed(
            'http://www.goominet.com/unspeakable-vault/'
            '?type=103&ecorss[clear_cache]=1')
        for entry in feed.for_date(pub_date):
            url = entry.summary.src('img[src*="/tx_cenostripviewer/"]')
            title = entry.title
            return CrawlerImage(url, title)

########NEW FILE########
__FILENAME__ = veslemoy
# encoding: utf-8

from comics.aggregator.crawler import CrawlerBase
from comics.core.comic_data import ComicDataBase


class ComicData(ComicDataBase):
    name = 'Veslemøy'
    language = 'no'
    url = 'http://www.side2.no/tegneserie/veslemoy/'
    start_date = '2008-11-14'
    end_date = '2012-12-31'
    active = False
    rights = 'Vantina Nina Andreassen'


class Crawler(CrawlerBase):
    def crawl(self, pub_date):
        pass  # Comic no longer published

########NEW FILE########
__FILENAME__ = vgcats
import datetime

from comics.aggregator.crawler import CrawlerBase, CrawlerImage
from comics.core.comic_data import ComicDataBase


class ComicData(ComicDataBase):
    name = 'VG Cats'
    language = 'en'
    url = 'http://www.vgcats.com/'
    start_date = '2001-09-09'
    rights = 'Scott Ramsoomair'


class Crawler(CrawlerBase):
    history_capable_date = '2001-09-09'
    time_zone = 'US/Eastern'

    # Without User-Agent set, the server returns empty responses
    headers = {'User-Agent': 'Mozilla/4.0'}

    def crawl(self, pub_date):
         # FIXME: Seems like they are using gif images now and then
        if pub_date < datetime.date(2003, 5, 1):
            file_ext = 'gif'
        else:
            file_ext = 'jpg'
        url = 'http://www.vgcats.com/comics/images/%s.%s' % (
            pub_date.strftime('%y%m%d'), file_ext)
        return CrawlerImage(url)

########NEW FILE########
__FILENAME__ = virtualshackles
import re

from comics.aggregator.crawler import CrawlerBase, CrawlerImage
from comics.core.comic_data import ComicDataBase


class ComicData(ComicDataBase):
    name = 'Virtual Shackles'
    language = 'en'
    url = 'http://www.virtualshackles.com/'
    start_date = '2009-03-27'
    rights = 'Jeremy Vinar & Mike Fahmie'


class Crawler(CrawlerBase):
    history_capable_days = 32
    schedule = 'Mo,We'
    time_zone = 'US/Pacific'

    def crawl(self, pub_date):
        feed = self.parse_feed('http://feeds.feedburner.com/VirtualShackles')

        for entry in feed.for_date(pub_date):
            url = entry.summary.src('img[src*="virtualshackles.com/img/"]')
            title = entry.title

            page_url = entry.raw_entry.feedburner_origlink
            page_url = re.sub(r'/(\d+/?)', '/-\g<1>', page_url)

            page = self.parse_page(page_url)
            orion = page.text('#orionComments')
            jack = page.text('#jackComments')

            if orion and jack:
                comments = u'orion: %s\n jack: %s' % (orion, jack)
            elif orion:
                comments = u'orion: %s' % (orion)
            elif jack:
                comments = u'jack: %s' % (jack)
            else:
                comments = None

            return CrawlerImage(url, title, comments)

########NEW FILE########
__FILENAME__ = walkoflife
# encoding: utf-8

from comics.aggregator.crawler import CrawlerBase, CrawlerImage
from comics.core.comic_data import ComicDataBase


class ComicData(ComicDataBase):
    name = 'Walk of Life'
    language = 'no'
    url = 'http://walkoflife.nettserier.no/'
    start_date = '2008-06-23'
    rights = 'Trond J. Stavås'


class Crawler(CrawlerBase):
    history_capable_date = '2008-06-23'
    schedule = 'Tu,Fr'
    time_zone = 'Europe/Oslo'

    def crawl(self, pub_date):
        epoch = self.date_to_epoch(pub_date)
        url = 'http://walkoflife.nettserier.no/_striper/walkoflife-%s.png' % (
            epoch,)
        return CrawlerImage(url)

########NEW FILE########
__FILENAME__ = wapsisquare
from comics.aggregator.crawler import CrawlerBase, CrawlerImage
from comics.core.comic_data import ComicDataBase


class ComicData(ComicDataBase):
    name = 'Wapsi Square'
    language = 'en'
    url = 'http://wapsisquare.com/'
    start_date = '2001-09-09'
    rights = 'Paul Taylor'


class Crawler(CrawlerBase):
    history_capable_days = 14
    schedule = 'Mo,Tu,We,Th,Fr'
    time_zone = 'US/Central'

    def crawl(self, pub_date):
        feed = self.parse_feed('http://wapsisquare.com/feed/')
        for entry in feed.for_date(pub_date):
            url = entry.summary.src('img')
            title = entry.title
            return CrawlerImage(url, title)

########NEW FILE########
__FILENAME__ = whattheduck
from comics.aggregator.crawler import CrawlerBase, CrawlerImage
from comics.core.comic_data import ComicDataBase


class ComicData(ComicDataBase):
    name = 'What the Duck'
    language = 'en'
    url = 'http://www.whattheduck.net/'
    start_date = '2006-07-01'
    rights = 'Aaron Johnson'


class Crawler(CrawlerBase):
    history_capable_days = 7
    time_zone = 'US/Central'

    def crawl(self, pub_date):
        feed = self.parse_feed('http://www.whattheduck.net/strip/rss.xml')
        for entry in feed.for_date(pub_date):
            if (entry.enclosures[0].type.startswith('image')
                    and entry.title.startswith('WTD')):
                url = entry.enclosures[0].href
                title = entry.title
                return CrawlerImage(url, title)

########NEW FILE########
__FILENAME__ = whiteninja
from comics.aggregator.crawler import CrawlerBase
from comics.core.comic_data import ComicDataBase


class ComicData(ComicDataBase):
    name = 'White Ninja'
    language = 'en'
    url = 'http://www.whiteninjacomics.com/'
    start_date = '2002-01-01'
    end_date = '2012-08-04'
    active = False
    rights = 'Scott Bevan & Kent Earle'


class Crawler(CrawlerBase):
    def crawl(self, pub_date):
        pass  # Comic no longer published

########NEW FILE########
__FILENAME__ = whomp
from comics.aggregator.crawler import CrawlerBase, CrawlerImage
from comics.core.comic_data import ComicDataBase
import re


class ComicData(ComicDataBase):
    name = 'Whomp!'
    language = 'en'
    url = 'http://www.whompcomic.com/'
    start_date = '2010-06-14'
    rights = 'Ronnie Filyaw'


class Crawler(CrawlerBase):
    history_capable_days = 30
    schedule = 'Mo,We,Fr'
    time_zone = 'US/Eastern'

    def crawl(self, pub_date):
        feed = self.parse_feed('http://www.whompcomic.com/feed/rss/')

        for entry in feed.all():
            url = entry.summary.src('img[src*="/comics-rss/"]')
            if not url:
                continue

            title = entry.title
            url = url.replace('comics-rss', 'comics')
            text = entry.summary.alt('img[src*="/comics-rss/"]')

             # extract date from url, since we don't have this in the xml
            match = re.search(r'comics/(\d{4}-\d{2}-\d{2})', url)
            if match:
                comic_date = self.string_to_date(match.group(1), '%Y-%m-%d')

                if pub_date == comic_date:
                    return CrawlerImage(url, title, text)

########NEW FILE########
__FILENAME__ = wondermark
from comics.aggregator.crawler import CrawlerBase, CrawlerImage
from comics.core.comic_data import ComicDataBase


class ComicData(ComicDataBase):
    name = 'Wondermark'
    language = 'en'
    url = 'http://wondermark.com/'
    start_date = '2003-04-25'
    rights = 'David Malki'


class Crawler(CrawlerBase):
    history_capable_days = 28
    schedule = 'Tu,Fr'
    time_zone = 'US/Pacific'

    def crawl(self, pub_date):
        feed_url = 'http://feeds.feedburner.com/wondermark'
        feed = self.parse_feed(feed_url)
        for entry in feed.for_date(pub_date):
            url = entry.content0.src('img[src*="/c/"]')
            title = entry.title
            text = entry.content0.alt('img[src*="/c/"]')
            if url is not None:
                return CrawlerImage(url, title, text)

########NEW FILE########
__FILENAME__ = wulffmorgenthaler
from comics.aggregator.crawler import CrawlerBase, CrawlerImage
from comics.core.comic_data import ComicDataBase


class ComicData(ComicDataBase):
    name = 'Wumo'
    language = 'en'
    url = 'http://kindofnormal.com/wumo/'
    start_date = '2001-01-01'
    rights = 'Mikael Wulff & Anders Morgenthaler'


class Crawler(CrawlerBase):
    history_capable_date = '2013-01-15'
    schedule = 'Mo,Tu,We,Th,Fr,Sa,Su'
    time_zone = 'Europe/Copenhagen'

    def crawl(self, pub_date):
        page_url = 'http://kindofnormal.com/wumo/%s' % (
            pub_date.strftime('%Y/%m/%d'))
        page = self.parse_page(page_url)
        url = page.href('link[rel="image_src"]')
        title = page.alt('img[src="%s"]' % url)
        return CrawlerImage(url, title)

########NEW FILE########
__FILENAME__ = wulffmorgenthalerap
from comics.aggregator.crawler import CrawlerBase
from comics.core.comic_data import ComicDataBase


class ComicData(ComicDataBase):
    name = 'Wumo (ap.no)'
    language = 'no'
    url = 'http://www.aftenposten.no/tegneserier/'
    start_date = '2001-01-01'
    active = False
    rights = 'Mikael Wulff & Anders Morgenthaler'


class Crawler(CrawlerBase):
    def crawl(self, pub_date):
        pass  # Comic no longer published

########NEW FILE########
__FILENAME__ = wumovg
from comics.aggregator.crawler import CrawlerBase, CrawlerImage
from comics.core.comic_data import ComicDataBase


class ComicData(ComicDataBase):
    name = 'Wumo (vg.no)'
    language = 'no'
    url = 'http://heltnormalt.no/wumo'
    rights = 'Mikael Wulff & Anders Morgenthaler'


class Crawler(CrawlerBase):
    history_capable_date = '2013-01-26'
    schedule = 'Mo,Tu,We,Th,Fr,Sa,Su'
    time_zone = 'Europe/Oslo'

    def crawl(self, pub_date):
        url = 'http://heltnormalt.no/img/wumo/%s.jpg' % (
            pub_date.strftime('%Y/%m/%d'))
        return CrawlerImage(url)

########NEW FILE########
__FILENAME__ = xkcd
from comics.aggregator.crawler import CrawlerBase, CrawlerImage
from comics.core.comic_data import ComicDataBase


class ComicData(ComicDataBase):
    name = 'xkcd'
    language = 'en'
    url = 'http://www.xkcd.com/'
    start_date = '2005-05-29'
    rights = 'Randall Munroe, CC BY-NC 2.5'


class Crawler(CrawlerBase):
    history_capable_days = 10
    schedule = 'Mo,We,Fr'
    time_zone = 'US/Eastern'

    def crawl(self, pub_date):
        feed = self.parse_feed('http://www.xkcd.com/rss.xml')
        for entry in feed.for_date(pub_date):
            url = entry.summary.src('img[src*="/comics/"]')
            title = entry.title
            text = entry.summary.alt('img[src*="/comics/"]')
            return CrawlerImage(url, title, text)

########NEW FILE########
__FILENAME__ = yafgc
from comics.aggregator.crawler import CrawlerBase, CrawlerImage
from comics.core.comic_data import ComicDataBase


class ComicData(ComicDataBase):
    name = 'Yet Another Fantasy Gamer Comic'
    language = 'en'
    url = 'http://www.yafgc.net/'
    start_date = '2006-05-29'
    rights = 'Rich Morris'


class Crawler(CrawlerBase):
    history_capable_date = '2006-05-29'
    schedule = 'Mo,Tu,We,Th,Fr,Sa,Su'
    time_zone = 'US/Pacific'

    def crawl(self, pub_date):
        feed = self.parse_feed('http://yafgc.net/inc/feed.php')
        for entry in feed.for_date(pub_date):
            url = entry.summary.src('img[src*="/img/comic/"]')
            title = entry.title
            return CrawlerImage(url, title)

########NEW FILE########
__FILENAME__ = yamac
from comics.aggregator.crawler import CrawlerBase, CrawlerImage
from comics.core.comic_data import ComicDataBase


class ComicData(ComicDataBase):
    name = 'you and me and cats'
    language = 'en'
    url = 'http://strawberry-pie.net/yamac/'
    start_date = '2009-07-01'
    rights = 'bubble'


class Crawler(CrawlerBase):
    history_capable_days = 90
    time_zone = 'US/Pacific'

    def crawl(self, pub_date):
        feed = self.parse_feed('http://strawberry-pie.net/yamac/?feed=rss2')
        for entry in feed.for_date(pub_date):
            if 'comic' not in entry.tags:
                continue
            url = entry.summary.src('img')
            url = url.replace('comics-rss', 'comics')
            title = entry.title
            return CrawlerImage(url, title)

########NEW FILE########
__FILENAME__ = yehudamoon
from comics.aggregator.crawler import CrawlerBase
from comics.core.comic_data import ComicDataBase


class ComicData(ComicDataBase):
    name = 'Yehuda Moon'
    language = 'en'
    url = 'http://www.yehudamoon.com/'
    start_date = '2008-01-22'
    end_date = '2012-12-31'
    active = False
    rights = 'Rick Smith'


class Crawler(CrawlerBase):
    def crawl(self, pub_date):
        pass  # Comic no longer published

########NEW FILE########
__FILENAME__ = zelda
from comics.aggregator.crawler import CrawlerBase, CrawlerImage
from comics.core.comic_data import ComicDataBase


class ComicData(ComicDataBase):
    name = 'Zelda'
    language = 'no'
    url = 'http://www.dagbladet.no/tegneserie/zelda/'
    start_date = '2012-06-07'
    rights = 'Lina Neidestam'


class Crawler(CrawlerBase):
    history_capable_days = 30
    schedule = 'Mo,Tu,We,Th,Fr,Sa'
    time_zone = 'Europe/Oslo'

    def crawl(self, pub_date):
        epoch = self.date_to_epoch(pub_date)
        page_url = 'http://www.dagbladet.no/tegneserie/zelda/?%s' % epoch
        page = self.parse_page(page_url)
        url = page.src('img#zelda-stripe')
        return CrawlerImage(url)

########NEW FILE########
__FILENAME__ = zits
from comics.aggregator.crawler import ArcaMaxCrawlerBase
from comics.core.comic_data import ComicDataBase


class ComicData(ComicDataBase):
    name = 'Zits'
    language = 'en'
    url = 'http://www.arcamax.com/zits'
    start_date = '1997-07-01'
    rights = 'Jerry Scott and Jim Borgman'


class Crawler(ArcaMaxCrawlerBase):
    history_capable_days = 0
    schedule = 'Mo,Tu,We,Th,Fr,Sa,Su'
    time_zone = 'US/Eastern'

    def crawl(self, pub_date):
        return self.crawl_helper('zits', pub_date)

########NEW FILE########
__FILENAME__ = zofiesverden
from comics.aggregator.crawler import CrawlerBase
from comics.core.comic_data import ComicDataBase


class ComicData(ComicDataBase):
    name = 'Zofies verden'
    language = 'no'
    url = 'http://www.zofiesverden.no/'
    start_date = '2006-05-02'
    end_date = '2012-08-31'
    active = False
    rights = 'Grethe Nestor & Norunn Blichfeldt Schjerven'


class Crawler(CrawlerBase):
    def crawl(self, pub_date):
        pass  # Comic no longer published

########NEW FILE########
__FILENAME__ = admin
from django.contrib import admin

from comics.core import models


class ReleaseImageInline(admin.TabularInline):
    model = models.Release.images.through
    readonly_fields = ('release', 'image')
    extra = 0

    def has_add_permission(self, request):
        return False


class ComicAdmin(admin.ModelAdmin):
    list_display = (
        'slug', 'name', 'language', 'url', 'rights', 'start_date', 'end_date',
        'active')
    list_filter = ['active', 'language']
    readonly_fields = (
        'name', 'slug', 'language', 'url', 'rights', 'start_date', 'end_date',
        'active')

    def has_add_permission(self, request):
        return False


class ReleaseAdmin(admin.ModelAdmin):
    list_display = ('__unicode__', 'comic', 'pub_date', 'fetched')
    list_filter = ['pub_date', 'fetched', 'comic']
    date_hierarchy = 'pub_date'
    exclude = ('images',)
    readonly_fields = ('comic', 'pub_date', 'fetched')
    inlines = (ReleaseImageInline,)

    def has_add_permission(self, request):
        return False


def text_preview(obj):
    MAX_LENGTH = 60
    if len(obj.text) < MAX_LENGTH:
        return obj.text
    else:
        return obj.text[:MAX_LENGTH] + '...'


class ImageAdmin(admin.ModelAdmin):
    list_display = (
        '__unicode__', 'file', 'height', 'width', 'fetched', 'title',
        text_preview)
    list_editable = ('title',)
    list_filter = ['fetched', 'comic']
    date_hierarchy = 'fetched'
    readonly_fields = (
        'comic', 'file', 'checksum', 'height', 'width', 'fetched')
    inlines = (ReleaseImageInline,)

    def has_add_permission(self, request):
        return False


admin.site.register(models.Comic, ComicAdmin)
admin.site.register(models.Release, ReleaseAdmin)
admin.site.register(models.Image, ImageAdmin)

########NEW FILE########
__FILENAME__ = comic_data
import datetime
import logging

from comics.comics import get_comic_module_names, get_comic_module
from comics.core.exceptions import ComicDataError
from comics.core.models import Comic

logger = logging.getLogger('comics.core.comic_data')


class ComicDataBase(object):
    # Required values
    name = None
    language = None
    url = None

    # Default values
    active = True
    start_date = None
    end_date = None
    rights = ''

    @property
    def slug(self):
        return self.__module__.split('.')[-1]

    def is_previously_loaded(self):
        return bool(Comic.objects.filter(slug=self.slug).count())

    def create_comic(self):
        if self.is_previously_loaded():
            comic = Comic.objects.get(slug=self.slug)
            comic.name = self.name
            comic.language = self.language
            comic.url = self.url
        else:
            comic = Comic(
                name=self.name,
                slug=self.slug,
                language=self.language,
                url=self.url)
        comic.active = self.active
        comic.start_date = self._get_date(self.start_date)
        comic.end_date = self._get_date(self.end_date)
        comic.rights = self.rights
        comic.save()

    def _get_date(self, date):
        if date is None:
            return None
        return datetime.datetime.strptime(date, '%Y-%m-%d').date()


class ComicDataLoader(object):
    def __init__(self, options):
        self.include_inactive = self._get_include_inactive(options)
        self.comic_slugs = self._get_comic_slugs(options)

    def start(self):
        for comic_slug in self.comic_slugs:
            logger.info('Loading comic data for %s', comic_slug)
            self._try_load_comic_data(comic_slug)

    def stop(self):
        pass

    def _get_include_inactive(self, options):
        comic_slugs = options.get('comic_slugs', None)
        if comic_slugs is None or len(comic_slugs) == 0:
            logger.debug('Excluding inactive comics')
            return False
        else:
            logger.debug('Including inactive comics')
            return True

    def _get_comic_slugs(self, options):
        comic_slugs = options.get('comic_slugs', None)
        if comic_slugs is None or len(comic_slugs) == 0:
            logger.error('No comic given. Use -c option to specify comic(s).')
            return []
        elif 'all' in comic_slugs:
            logger.debug('Load targets: all comics')
            return get_comic_module_names()
        else:
            logger.debug('Load targets: %s', comic_slugs)
            return comic_slugs

    def _try_load_comic_data(self, comic_slug):
        try:
            data = self._get_data(comic_slug)
            if self._should_load_data(data):
                self._load_data(data)
            else:
                logger.debug('Skipping inactive comic')
        except ComicDataError, error:
            logger.error(error)
        except Exception, error:
            logger.exception(error)

    def _get_data(self, comic_slug):
        logger.debug('Importing comic module for %s', comic_slug)
        comic_module = get_comic_module(comic_slug)
        if not hasattr(comic_module, 'ComicData'):
            raise ComicDataError(
                '%s does not have a ComicData class' % comic_module.__name__)
        return comic_module.ComicData()

    def _should_load_data(self, data):
        if data.active:
            return True
        elif self.include_inactive:
            return True
        elif data.is_previously_loaded():
            return True
        else:
            return False

    def _load_data(self, data):
        logger.debug('Syncing comic data with database')
        data.create_comic()

########NEW FILE########
__FILENAME__ = command_utils
import logging
from optparse import make_option

from django.conf import settings
from django.core.management.base import BaseCommand

DATE_TIME_FORMAT = '%Y-%m-%d %H:%M:%S'
FILE_LOG_FORMAT = '%(asctime)s [%(process)d] %(name)-12s %(levelname)-8s ' \
    + '%(message)s'
CONSOLE_LOG_FORMAT = '%(levelname)-8s %(message)s'


class ComicsBaseCommand(BaseCommand):
    if not [option for option in BaseCommand.option_list
            if option.dest == 'verbosity']:
        option_list = BaseCommand.option_list + (
            make_option(
                '-v', '--verbosity', action='store', dest='verbosity',
                default='1', type='choice', choices=['0', '1', '2'],
                help=(
                    'Verbosity level; 0=minimal output, 1=normal output, '
                    '2=all output')),
        )

    def handle(self, *args, **options):
        self._setup_logging(int(options.get('verbosity', 1)))

    def _setup_logging(self, verbosity_level):
        self._setup_file_logging()
        self._setup_console_logging(verbosity_level)

    def _setup_file_logging(self):
        logging.basicConfig(
            level=logging.DEBUG,
            format=FILE_LOG_FORMAT,
            datefmt=DATE_TIME_FORMAT,
            filename=settings.COMICS_LOG_FILENAME,
            filemode='a')

    def _setup_console_logging(self, verbosity_level):
        console = logging.StreamHandler()
        if verbosity_level == 0:
            console.setLevel(logging.ERROR)
        elif verbosity_level == 2:
            console.setLevel(logging.DEBUG)
        else:
            console.setLevel(logging.INFO)
        formatter = logging.Formatter(CONSOLE_LOG_FORMAT)
        console.setFormatter(formatter)
        logging.getLogger('').addHandler(console)

########NEW FILE########
__FILENAME__ = context_processors
from django.conf import settings

from comics.core.models import Comic


def site_settings(request):
    return {
        'site_title': settings.COMICS_SITE_TITLE,
        'google_analytics_code': settings.COMICS_GOOGLE_ANALYTICS_CODE,
    }


def all_comics(request):
    return {
        'all_comics': Comic.objects.sort_by_name(),
    }

########NEW FILE########
__FILENAME__ = exceptions
class ComicsError(Exception):
    """Base class for all comic exceptions"""

    def __init__(self, value):
        self.value = value

    def __str__(self):
        return 'Generic comics error (%s)' % self.value


class ComicDataError(ComicsError):
    """Base class for comic data exceptions"""
    def __str__(self):
        return 'Comics data error (%s)' % self.value

########NEW FILE########
__FILENAME__ = comics_addcomics
from comics.core.comic_data import ComicDataLoader
from comics.core.command_utils import ComicsBaseCommand, make_option


class Command(ComicsBaseCommand):
    option_list = ComicsBaseCommand.option_list + (
        make_option(
            '-c', '--comic',
            action='append', dest='comic_slugs', metavar='COMIC',
            help=(
                'Comic to add to site, repeat for multiple. ' +
                'Use "-c all" to add all.')),
    )

    def handle(self, *args, **options):
        super(Command, self).handle(*args, **options)
        data_loader = ComicDataLoader(options)
        try:
            data_loader.start()
        except KeyboardInterrupt:
            data_loader.stop()

########NEW FILE########
__FILENAME__ = managers
from django.db import models


class ComicManager(models.Manager):
    def sort_by_name(self):
        qs = self.get_queryset()
        qs = qs.extra(select={'lower_name': 'LOWER(name)'})
        qs = qs.extra(order_by=['lower_name'])
        return qs

########NEW FILE########
__FILENAME__ = middleware
import re

from django.utils.html import strip_spaces_between_tags
from django.conf import settings

RE_MULTISPACE = re.compile(r'\s{2,}')
RE_NEWLINE = re.compile(r'\n')


class MinifyHTMLMiddleware(object):
    def process_response(self, request, response):
        if 'text/html' in response['Content-Type'] and settings.COMPRESS_HTML:
            response.content = strip_spaces_between_tags(
                response.content.strip())
            response.content = RE_MULTISPACE.sub(' ', response.content)
            response.content = RE_NEWLINE.sub(' ', response.content)
        return response

########NEW FILE########
__FILENAME__ = 0001_initial
from south.db import db
from django.db import models
from comics.core.models import *

class Migration:
    def forwards(self, orm):
        # Adding model 'Comic'
        db.create_table('comics_comic', (
            ('id', models.AutoField(primary_key=True)),
            ('name', models.CharField(max_length=100)),
            ('slug', models.SlugField(unique=True, max_length=100, verbose_name='Short name')),
            ('language', models.CharField(max_length=2)),
            ('url', models.URLField(verbose_name='URL', blank=True)),
            ('start_date', models.DateField(null=True, blank=True)),
            ('end_date', models.DateField(null=True, blank=True)),
            ('rights', models.CharField(max_length=100, blank=True)),
            ('number_of_sets', models.PositiveIntegerField(default=0)),
        ))
        db.send_create_signal('core', ['Comic'])

        # Adding model 'Strip'
        db.create_table('comics_strip', (
            ('id', models.AutoField(primary_key=True)),
            ('comic', models.ForeignKey(orm.Comic)),
            ('fetched', models.DateTimeField(auto_now_add=True)),
            ('filename', models.CharField(max_length=100)),
            ('checksum', models.CharField(max_length=64, db_index=True)),
            ('title', models.CharField(max_length=255, blank=True)),
            ('text', models.TextField(blank=True)),
        ))
        db.send_create_signal('core', ['Strip'])

        # Adding model 'Release'
        db.create_table('comics_release', (
            ('id', models.AutoField(primary_key=True)),
            ('comic', models.ForeignKey(orm.Comic)),
            ('pub_date', models.DateField(verbose_name='publication date')),
            ('strip', models.ForeignKey(orm.Strip, related_name='releases')),
        ))
        db.send_create_signal('core', ['Release'])

    def backwards(self, orm):
        # Deleting model 'Comic'
        db.delete_table('comics_comic')

        # Deleting model 'Strip'
        db.delete_table('comics_strip')

        # Deleting model 'Release'
        db.delete_table('comics_release')

    models = {
        'core.comic': {
            'Meta': {'ordering': "['name']", 'db_table': "'comics_comic'"},
            'end_date': ('models.DateField', [], {'null': 'True', 'blank': 'True'}),
            'id': ('models.AutoField', [], {'primary_key': 'True'}),
            'language': ('models.CharField', [], {'max_length': '2'}),
            'name': ('models.CharField', [], {'max_length': '100'}),
            'number_of_sets': ('models.PositiveIntegerField', [], {'default': '0'}),
            'rights': ('models.CharField', [], {'max_length': '100', 'blank': 'True'}),
            'slug': ('models.SlugField', [], {'unique': 'True', 'max_length': '100', 'verbose_name': "'Short name'"}),
            'start_date': ('models.DateField', [], {'null': 'True', 'blank': 'True'}),
            'url': ('models.URLField', [], {'verbose_name': "'URL'", 'blank': 'True'})
        },
        'core.strip': {
            'Meta': {'db_table': "'comics_strip'", 'get_latest_by': "'pub_date'"},
            'checksum': ('models.CharField', [], {'max_length': '64', 'db_index': 'True'}),
            'comic': ('models.ForeignKey', ['Comic'], {}),
            'fetched': ('models.DateTimeField', [], {'auto_now_add': 'True'}),
            'filename': ('models.CharField', [], {'max_length': '100'}),
            'id': ('models.AutoField', [], {'primary_key': 'True'}),
            'text': ('models.TextField', [], {'blank': 'True'}),
            'title': ('models.CharField', [], {'max_length': '255', 'blank': 'True'})
        },
        'core.release': {
            'Meta': {'db_table': "'comics_release'", 'get_latest_by': "'pub_date'"},
            'comic': ('models.ForeignKey', ['Comic'], {}),
            'id': ('models.AutoField', [], {'primary_key': 'True'}),
            'pub_date': ('models.DateField', [], {'verbose_name': "'publication date'"}),
            'strip': ('models.ForeignKey', ["'Strip'"], {'related_name': "'releases'"})
        }
    }

    complete_apps = ['core']

########NEW FILE########
__FILENAME__ = 0002_add_strip_imagefield
from south.db import db
from django.db import models
from comics.core.models import *

class Migration:
    def forwards(self, orm):
        # Adding field 'Strip.file'
        db.add_column('comics_strip', 'file', models.ImageField(height_field='height', upload_to=image_file_path, width_field='width', storage=image_storage, default=''), keep_default=False)

        # Adding field 'Strip.height'
        db.add_column('comics_strip', 'height', models.IntegerField(default=0), keep_default=False)

        # Adding field 'Strip.width'
        db.add_column('comics_strip', 'width', models.IntegerField(default=0), keep_default=False)

    def backwards(self, orm):
        # Deleting field 'Strip.file'
        db.delete_column('comics_strip', 'file')

        # Deleting field 'Strip.height'
        db.delete_column('comics_strip', 'height')

        # Deleting field 'Strip.width'
        db.delete_column('comics_strip', 'width')

    models = {
        'core.comic': {
            'Meta': {'ordering': "['name']", 'db_table': "'comics_comic'"},
            'end_date': ('models.DateField', [], {'null': 'True', 'blank': 'True'}),
            'id': ('models.AutoField', [], {'primary_key': 'True'}),
            'language': ('models.CharField', [], {'max_length': '2'}),
            'name': ('models.CharField', [], {'max_length': '100'}),
            'number_of_sets': ('models.PositiveIntegerField', [], {'default': '0'}),
            'rights': ('models.CharField', [], {'max_length': '100', 'blank': 'True'}),
            'slug': ('models.SlugField', [], {'unique': 'True', 'max_length': '100', 'verbose_name': "'Short name'"}),
            'start_date': ('models.DateField', [], {'null': 'True', 'blank': 'True'}),
            'url': ('models.URLField', [], {'verbose_name': "'URL'", 'blank': 'True'})
        },
        'core.strip': {
            'Meta': {'db_table': "'comics_strip'", 'get_latest_by': "'pub_date'"},
            'checksum': ('models.CharField', [], {'max_length': '64', 'db_index': 'True'}),
            'comic': ('models.ForeignKey', ['Comic'], {}),
            'fetched': ('models.DateTimeField', [], {'auto_now_add': 'True'}),
            'file': ('models.ImageField', [], {'height_field': "'height'", 'upload_to': 'image_file_path', 'width_field': "'width'", 'storage': 'image_storage'}),
            'filename': ('models.CharField', [], {'max_length': '100'}),
            'height': ('models.IntegerField', [], {}),
            'id': ('models.AutoField', [], {'primary_key': 'True'}),
            'text': ('models.TextField', [], {'blank': 'True'}),
            'title': ('models.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'width': ('models.IntegerField', [], {})
        },
        'core.release': {
            'Meta': {'db_table': "'comics_release'", 'get_latest_by': "'pub_date'"},
            'comic': ('models.ForeignKey', ['Comic'], {}),
            'id': ('models.AutoField', [], {'primary_key': 'True'}),
            'pub_date': ('models.DateField', [], {'verbose_name': "'publication date'"}),
            'strip': ('models.ForeignKey', ["'Strip'"], {'related_name': "'releases'"})
        }
    }

    complete_apps = ['core']

########NEW FILE########
__FILENAME__ = 0003_populate_strip_imagefield
from __future__ import with_statement
import os
import shutil

from django.conf import settings
from django.core.files import File
from comics.core.models import *

class Migration:
    no_dry_run = True

    def forwards(self, orm):
        total = orm.Strip.objects.count()
        for i, strip in enumerate(orm.Strip.objects.all()):
            print '%s %d/%d' % (strip.checksum, i + 1, total)
            filename = '%s.%s' % (strip.checksum, strip.filename.split('.')[-1])
            file_path = '%s/%s' % (settings.MEDIA_ROOT, strip.filename)
            file_path = os.path.abspath(file_path)
            with open(file_path) as fh:
                strip.file.save(filename, File(fh))
                strip.save()

    def backwards(self, orm):
        total = orm.Strip.objects.count()
        for i, strip in enumerate(orm.Strip.objects.all()):
            print '%s %d/%d' % (strip.checksum, i + 1, total)
            first_release = orm.Release.objects.filter(
                strip=strip.pk).order_by('pub_date')[0]
            filename = '%(slug)s/%(year)s/%(date)s.%(ext)s' % {
                'slug': strip.comic.slug,
                'year': first_release.pub_date.year,
                'date': first_release.pub_date.strftime('%Y-%m-%d'),
                'ext': strip.file.name.split('.')[-1],
            }
            file_path = '%s/%s' % (settings.MEDIA_ROOT, filename)
            file_path = os.path.abspath(file_path)
            try:
                os.makedirs(os.path.dirname(file_path))
            except OSError:
                pass
            shutil.copy(strip.file.path, file_path)
            strip.filename = filename
            strip.save()

    models = {
        'core.comic': {
            'Meta': {'ordering': "['name']", 'db_table': "'comics_comic'"},
            'end_date': ('models.DateField', [], {'null': 'True', 'blank': 'True'}),
            'id': ('models.AutoField', [], {'primary_key': 'True'}),
            'language': ('models.CharField', [], {'max_length': '2'}),
            'name': ('models.CharField', [], {'max_length': '100'}),
            'number_of_sets': ('models.PositiveIntegerField', [], {'default': '0'}),
            'rights': ('models.CharField', [], {'max_length': '100', 'blank': 'True'}),
            'slug': ('models.SlugField', [], {'unique': 'True', 'max_length': '100', 'verbose_name': "'Short name'"}),
            'start_date': ('models.DateField', [], {'null': 'True', 'blank': 'True'}),
            'url': ('models.URLField', [], {'verbose_name': "'URL'", 'blank': 'True'})
        },
        'core.strip': {
            'Meta': {'db_table': "'comics_strip'", 'get_latest_by': "'pub_date'"},
            'checksum': ('models.CharField', [], {'max_length': '64', 'db_index': 'True'}),
            'comic': ('models.ForeignKey', ['Comic'], {}),
            'fetched': ('models.DateTimeField', [], {'auto_now_add': 'True'}),
            'file': ('models.ImageField', [], {'height_field': "'height'", 'upload_to': 'image_file_path', 'width_field': "'width'", 'storage': 'image_storage'}),
            'filename': ('models.CharField', [], {'max_length': '100'}),
            'height': ('models.IntegerField', [], {}),
            'id': ('models.AutoField', [], {'primary_key': 'True'}),
            'text': ('models.TextField', [], {'blank': 'True'}),
            'title': ('models.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'width': ('models.IntegerField', [], {})
        },
        'core.release': {
            'Meta': {'db_table': "'comics_release'", 'get_latest_by': "'pub_date'"},
            'comic': ('models.ForeignKey', ['Comic'], {}),
            'id': ('models.AutoField', [], {'primary_key': 'True'}),
            'pub_date': ('models.DateField', [], {'verbose_name': "'publication date'"}),
            'strip': ('models.ForeignKey', ["'Strip'"], {'related_name': "'releases'"})
        }
    }

    complete_apps = ['core']

########NEW FILE########
__FILENAME__ = 0004_remove_strip_filename_field
from south.db import db
from django.db import models
from comics.core.models import *

class Migration:
    def forwards(self, orm):
        # Deleting field 'Strip.filename'
        db.delete_column('comics_strip', 'filename')

    def backwards(self, orm):
        # Adding field 'Strip.filename'
        db.add_column('comics_strip', 'filename', models.CharField(max_length=100, default=''), keep_default=False)

    models = {
        'core.comic': {
            'Meta': {'ordering': "['name']", 'db_table': "'comics_comic'"},
            'end_date': ('models.DateField', [], {'null': 'True', 'blank': 'True'}),
            'id': ('models.AutoField', [], {'primary_key': 'True'}),
            'language': ('models.CharField', [], {'max_length': '2'}),
            'name': ('models.CharField', [], {'max_length': '100'}),
            'number_of_sets': ('models.PositiveIntegerField', [], {'default': '0'}),
            'rights': ('models.CharField', [], {'max_length': '100', 'blank': 'True'}),
            'slug': ('models.SlugField', [], {'unique': 'True', 'max_length': '100', 'verbose_name': "'Short name'"}),
            'start_date': ('models.DateField', [], {'null': 'True', 'blank': 'True'}),
            'url': ('models.URLField', [], {'verbose_name': "'URL'", 'blank': 'True'})
        },
        'core.strip': {
            'Meta': {'db_table': "'comics_strip'", 'get_latest_by': "'pub_date'"},
            'checksum': ('models.CharField', [], {'max_length': '64', 'db_index': 'True'}),
            'comic': ('models.ForeignKey', ['Comic'], {}),
            'fetched': ('models.DateTimeField', [], {'auto_now_add': 'True'}),
            'file': ('models.ImageField', [], {'height_field': "'height'", 'upload_to': 'image_file_path', 'width_field': "'width'", 'storage': 'image_storage'}),
            'height': ('models.IntegerField', [], {}),
            'id': ('models.AutoField', [], {'primary_key': 'True'}),
            'text': ('models.TextField', [], {'blank': 'True'}),
            'title': ('models.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'width': ('models.IntegerField', [], {})
        },
        'core.release': {
            'Meta': {'db_table': "'comics_release'", 'get_latest_by': "'pub_date'"},
            'comic': ('models.ForeignKey', ['Comic'], {}),
            'id': ('models.AutoField', [], {'primary_key': 'True'}),
            'pub_date': ('models.DateField', [], {'verbose_name': "'publication date'"}),
            'strip': ('models.ForeignKey', ["'Strip'"], {'related_name': "'releases'"})
        }
    }

    complete_apps = ['core']

########NEW FILE########
__FILENAME__ = 0005_rename_strip_model_to_image
from south.db import db
from django.db import models
from comics.core.models import *

class Migration:
    def forwards(self, orm):
        # Rename model 'Strip' to 'Image'
        db.rename_table('comics_strip', 'comics_image')

        # Rename field 'Release.strip' to 'Release.image'
        db.rename_column('comics_release', 'strip_id', 'image_id')

    def backwards(self, orm):
        # Rename model 'Image' to 'Strip'
        db.rename_table('comics_image', 'comics_strip')

        # Rename field 'Release.image' to 'Release.strip'
        db.rename_column('comics_release', 'image_id', 'strip_id')

    models = {
        'core.comic': {
            'Meta': {'db_table': "'comics_comic'"},
            'end_date': ('django.db.models.fields.DateField', [], {'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'language': ('django.db.models.fields.CharField', [], {'max_length': '2'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'number_of_sets': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0'}),
            'rights': ('django.db.models.fields.CharField', [], {'max_length': '100', 'blank': 'True'}),
            'slug': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '100', 'db_index': 'True'}),
            'start_date': ('django.db.models.fields.DateField', [], {'null': 'True', 'blank': 'True'}),
            'url': ('django.db.models.fields.URLField', [], {'max_length': '200', 'blank': 'True'})
        },
        'core.image': {
            'Meta': {'db_table': "'comics_image'"},
            'checksum': ('django.db.models.fields.CharField', [], {'max_length': '64', 'db_index': 'True'}),
            'comic': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['core.Comic']"}),
            'fetched': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'file': ('django.db.models.fields.files.ImageField', [], {'max_length': '100'}),
            'height': ('django.db.models.fields.IntegerField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'text': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'width': ('django.db.models.fields.IntegerField', [], {})
        },
        'core.release': {
            'Meta': {'db_table': "'comics_release'"},
            'comic': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['core.Comic']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'image': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'releases'", 'to': "orm['core.Image']"}),
            'pub_date': ('django.db.models.fields.DateField', [], {})
        }
    }

    complete_apps = ['core']

########NEW FILE########
__FILENAME__ = 0006_add_release_fetched
from south.db import db
from django.db import models
from django.utils import timezone
from comics.core.models import *

class Migration:
    def forwards(self, orm):
        # Adding field 'Release.fetched'
        db.add_column('comics_release', 'fetched', models.DateTimeField(auto_now_add=True, default=timezone.now), keep_default=False)
        # Fix for South bug #316 in sqlite3 backend
        if hasattr(db, '_populate_current_structure'):
            db._populate_current_structure('comics_release', force=True)

    def backwards(self, orm):
        # Deleting field 'Release.fetched'
        db.delete_column('comics_release', 'fetched')

    models = {
        'core.comic': {
            'Meta': {'db_table': "'comics_comic'"},
            'end_date': ('django.db.models.fields.DateField', [], {'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'language': ('django.db.models.fields.CharField', [], {'max_length': '2'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'number_of_sets': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0'}),
            'rights': ('django.db.models.fields.CharField', [], {'max_length': '100', 'blank': 'True'}),
            'slug': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '100', 'db_index': 'True'}),
            'start_date': ('django.db.models.fields.DateField', [], {'null': 'True', 'blank': 'True'}),
            'url': ('django.db.models.fields.URLField', [], {'max_length': '200', 'blank': 'True'})
        },
        'core.image': {
            'Meta': {'db_table': "'comics_image'"},
            'checksum': ('django.db.models.fields.CharField', [], {'max_length': '64', 'db_index': 'True'}),
            'comic': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['core.Comic']"}),
            'fetched': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'file': ('django.db.models.fields.files.ImageField', [], {'max_length': '100'}),
            'height': ('django.db.models.fields.IntegerField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'text': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'width': ('django.db.models.fields.IntegerField', [], {})
        },
        'core.release': {
            'Meta': {'db_table': "'comics_release'"},
            'comic': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['core.Comic']"}),
            'fetched': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'image': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'releases'", 'to': "orm['core.Image']"}),
            'pub_date': ('django.db.models.fields.DateField', [], {})
        }
    }

    complete_apps = ['core']

########NEW FILE########
__FILENAME__ = 0007_populate_release_fetched
from south.db import db
from django.db import models
from comics.core.models import *

class Migration:
    no_dry_run = True

    def forwards(self, orm):
        for release in orm.Release.objects.all():
            release.fetched = release.image.fetched
            release.save()

    def backwards(self, orm):
        pass

    models = {
        'core.comic': {
            'Meta': {'db_table': "'comics_comic'"},
            'end_date': ('django.db.models.fields.DateField', [], {'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'language': ('django.db.models.fields.CharField', [], {'max_length': '2'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'number_of_sets': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0'}),
            'rights': ('django.db.models.fields.CharField', [], {'max_length': '100', 'blank': 'True'}),
            'slug': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '100', 'db_index': 'True'}),
            'start_date': ('django.db.models.fields.DateField', [], {'null': 'True', 'blank': 'True'}),
            'url': ('django.db.models.fields.URLField', [], {'max_length': '200', 'blank': 'True'})
        },
        'core.image': {
            'Meta': {'db_table': "'comics_image'"},
            'checksum': ('django.db.models.fields.CharField', [], {'max_length': '64', 'db_index': 'True'}),
            'comic': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['core.Comic']"}),
            'fetched': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'file': ('django.db.models.fields.files.ImageField', [], {'max_length': '100'}),
            'height': ('django.db.models.fields.IntegerField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'text': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'width': ('django.db.models.fields.IntegerField', [], {})
        },
        'core.release': {
            'Meta': {'db_table': "'comics_release'"},
            'comic': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['core.Comic']"}),
            'fetched': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'image': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'releases'", 'to': "orm['core.Image']"}),
            'pub_date': ('django.db.models.fields.DateField', [], {})
        }
    }

    complete_apps = ['core']

########NEW FILE########
__FILENAME__ = 0008_add_release_images_m2m
from south.db import db
from django.db import models
from comics.core.models import *

class Migration:
    def forwards(self, orm):
        # Adding ManyToManyField 'Release.images'
        db.create_table('comics_release_images', (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('release', models.ForeignKey(orm.Release, null=False)),
            ('image', models.ForeignKey(orm.Image, null=False))
        ))

    def backwards(self, orm):
        # Dropping ManyToManyField 'Release.images'
        db.delete_table('comics_release_images')

    models = {
        'core.comic': {
            'Meta': {'db_table': "'comics_comic'"},
            'end_date': ('django.db.models.fields.DateField', [], {'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'language': ('django.db.models.fields.CharField', [], {'max_length': '2'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'number_of_sets': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0'}),
            'rights': ('django.db.models.fields.CharField', [], {'max_length': '100', 'blank': 'True'}),
            'slug': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '100', 'db_index': 'True'}),
            'start_date': ('django.db.models.fields.DateField', [], {'null': 'True', 'blank': 'True'}),
            'url': ('django.db.models.fields.URLField', [], {'max_length': '200', 'blank': 'True'})
        },
        'core.image': {
            'Meta': {'db_table': "'comics_image'"},
            'checksum': ('django.db.models.fields.CharField', [], {'max_length': '64', 'db_index': 'True'}),
            'comic': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['core.Comic']"}),
            'fetched': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'file': ('django.db.models.fields.files.ImageField', [], {'max_length': '100'}),
            'height': ('django.db.models.fields.IntegerField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'text': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'width': ('django.db.models.fields.IntegerField', [], {})
        },
        'core.release': {
            'Meta': {'db_table': "'comics_release'"},
            'comic': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['core.Comic']"}),
            'fetched': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'image': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['core.Image']"}),
            'images': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['core.Image']"}),
            'pub_date': ('django.db.models.fields.DateField', [], {})
        }
    }

    complete_apps = ['core']

########NEW FILE########
__FILENAME__ = 0009_populate_release_images_m2m
from south.db import db
from django.db import models
from comics.core.models import *

class Migration:
    no_dry_run = True

    def forwards(self, orm):
        for release in orm.Release.objects.all():
            release.images.add(release.image)

    def backwards(self, orm):
        assert False, "Backwards migration not supported"

    models = {
        'core.comic': {
            'Meta': {'db_table': "'comics_comic'"},
            'end_date': ('django.db.models.fields.DateField', [], {'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'language': ('django.db.models.fields.CharField', [], {'max_length': '2'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'number_of_sets': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0'}),
            'rights': ('django.db.models.fields.CharField', [], {'max_length': '100', 'blank': 'True'}),
            'slug': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '100', 'db_index': 'True'}),
            'start_date': ('django.db.models.fields.DateField', [], {'null': 'True', 'blank': 'True'}),
            'url': ('django.db.models.fields.URLField', [], {'max_length': '200', 'blank': 'True'})
        },
        'core.image': {
            'Meta': {'db_table': "'comics_image'"},
            'checksum': ('django.db.models.fields.CharField', [], {'max_length': '64', 'db_index': 'True'}),
            'comic': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['core.Comic']"}),
            'fetched': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'file': ('django.db.models.fields.files.ImageField', [], {'max_length': '100'}),
            'height': ('django.db.models.fields.IntegerField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'text': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'width': ('django.db.models.fields.IntegerField', [], {})
        },
        'core.release': {
            'Meta': {'db_table': "'comics_release'"},
            'comic': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['core.Comic']"}),
            'fetched': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'image': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['core.Image']"}),
            'images': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['core.Image']"}),
            'pub_date': ('django.db.models.fields.DateField', [], {})
        }
    }

    complete_apps = ['core']

########NEW FILE########
__FILENAME__ = 0010_remove_release_image_fk
from south.db import db
from django.db import models
from comics.core.models import *

class Migration:
    def forwards(self, orm):
        # Deleting field 'Release.image'
        db.delete_column('comics_release', 'image_id')

    def backwards(self, orm):
        # Adding field 'Release.image'
        db.add_column('comics_release', 'image', models.ForeignKey(Image, null=True))

    models = {
        'core.comic': {
            'Meta': {'db_table': "'comics_comic'"},
            'end_date': ('django.db.models.fields.DateField', [], {'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'language': ('django.db.models.fields.CharField', [], {'max_length': '2'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'number_of_sets': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0'}),
            'rights': ('django.db.models.fields.CharField', [], {'max_length': '100', 'blank': 'True'}),
            'slug': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '100', 'db_index': 'True'}),
            'start_date': ('django.db.models.fields.DateField', [], {'null': 'True', 'blank': 'True'}),
            'url': ('django.db.models.fields.URLField', [], {'max_length': '200', 'blank': 'True'})
        },
        'core.image': {
            'Meta': {'db_table': "'comics_image'"},
            'checksum': ('django.db.models.fields.CharField', [], {'max_length': '64', 'db_index': 'True'}),
            'comic': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['core.Comic']"}),
            'fetched': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'file': ('django.db.models.fields.files.ImageField', [], {'max_length': '100'}),
            'height': ('django.db.models.fields.IntegerField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'text': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'width': ('django.db.models.fields.IntegerField', [], {})
        },
        'core.release': {
            'Meta': {'db_table': "'comics_release'"},
            'comic': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['core.Comic']"}),
            'fetched': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'images': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['core.Image']"}),
            'pub_date': ('django.db.models.fields.DateField', [], {})
        }
    }

    complete_apps = ['core']

########NEW FILE########
__FILENAME__ = 0011_auto__add_field_comic_active
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):
    def forwards(self, orm):
        # Adding field 'Comic.active'
        db.add_column('comics_comic', 'active', self.gf('django.db.models.fields.BooleanField')(default=True), keep_default=False)

    def backwards(self, orm):
        # Deleting field 'Comic.active'
        db.delete_column('comics_comic', 'active')

    models = {
        'core.comic': {
            'Meta': {'ordering': "['name']", 'object_name': 'Comic', 'db_table': "'comics_comic'"},
            'active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'end_date': ('django.db.models.fields.DateField', [], {'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'language': ('django.db.models.fields.CharField', [], {'max_length': '2'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'number_of_sets': ('django.db.models.fields.PositiveIntegerField', [], {'default': '0'}),
            'rights': ('django.db.models.fields.CharField', [], {'max_length': '100', 'blank': 'True'}),
            'slug': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '100', 'db_index': 'True'}),
            'start_date': ('django.db.models.fields.DateField', [], {'null': 'True', 'blank': 'True'}),
            'url': ('django.db.models.fields.URLField', [], {'max_length': '200', 'blank': 'True'})
        },
        'core.image': {
            'Meta': {'object_name': 'Image', 'db_table': "'comics_image'"},
            'checksum': ('django.db.models.fields.CharField', [], {'max_length': '64', 'db_index': 'True'}),
            'comic': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['core.Comic']"}),
            'fetched': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'file': ('django.db.models.fields.files.ImageField', [], {'max_length': '100'}),
            'height': ('django.db.models.fields.IntegerField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'text': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'width': ('django.db.models.fields.IntegerField', [], {})
        },
        'core.release': {
            'Meta': {'object_name': 'Release', 'db_table': "'comics_release'"},
            'comic': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['core.Comic']"}),
            'fetched': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'images': ('django.db.models.fields.related.ManyToManyField', [], {'related_name': "'releases'", 'symmetrical': 'False', 'to': "orm['core.Image']"}),
            'pub_date': ('django.db.models.fields.DateField', [], {})
        }
    }

    complete_apps = ['core']

########NEW FILE########
__FILENAME__ = 0012_auto__del_field_comic_number_of_sets
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Deleting field 'Comic.number_of_sets'
        db.delete_column('comics_comic', 'number_of_sets')


    def backwards(self, orm):
        # Adding field 'Comic.number_of_sets'
        db.add_column('comics_comic', 'number_of_sets',
                      self.gf('django.db.models.fields.PositiveIntegerField')(default=0),
                      keep_default=False)


    models = {
        'core.comic': {
            'Meta': {'ordering': "['name']", 'object_name': 'Comic', 'db_table': "'comics_comic'"},
            'active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'end_date': ('django.db.models.fields.DateField', [], {'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'language': ('django.db.models.fields.CharField', [], {'max_length': '2'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'rights': ('django.db.models.fields.CharField', [], {'max_length': '100', 'blank': 'True'}),
            'slug': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '100'}),
            'start_date': ('django.db.models.fields.DateField', [], {'null': 'True', 'blank': 'True'}),
            'url': ('django.db.models.fields.URLField', [], {'max_length': '200', 'blank': 'True'})
        },
        'core.image': {
            'Meta': {'object_name': 'Image', 'db_table': "'comics_image'"},
            'checksum': ('django.db.models.fields.CharField', [], {'max_length': '64', 'db_index': 'True'}),
            'comic': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['core.Comic']"}),
            'fetched': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'file': ('django.db.models.fields.files.ImageField', [], {'max_length': '100'}),
            'height': ('django.db.models.fields.IntegerField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'text': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'width': ('django.db.models.fields.IntegerField', [], {})
        },
        'core.release': {
            'Meta': {'object_name': 'Release', 'db_table': "'comics_release'"},
            'comic': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['core.Comic']"}),
            'fetched': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'images': ('django.db.models.fields.related.ManyToManyField', [], {'related_name': "'releases'", 'symmetrical': 'False', 'to': "orm['core.Image']"}),
            'pub_date': ('django.db.models.fields.DateField', [], {})
        }
    }

    complete_apps = ['core']
########NEW FILE########
__FILENAME__ = 0013_auto__add_field_comic_added
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.utils.timezone import utc


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding field 'Comic.added'
        default = datetime.datetime(1, 1, 1, 0, 0).replace(tzinfo=utc)
        db.add_column('comics_comic', 'added',
                      self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, default=default, blank=True),
                      keep_default=False)


    def backwards(self, orm):
        # Deleting field 'Comic.added'
        db.delete_column('comics_comic', 'added')


    models = {
        'core.comic': {
            'Meta': {'ordering': "['name']", 'object_name': 'Comic', 'db_table': "'comics_comic'"},
            'active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'added': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'end_date': ('django.db.models.fields.DateField', [], {'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'language': ('django.db.models.fields.CharField', [], {'max_length': '2'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'rights': ('django.db.models.fields.CharField', [], {'max_length': '100', 'blank': 'True'}),
            'slug': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '100'}),
            'start_date': ('django.db.models.fields.DateField', [], {'null': 'True', 'blank': 'True'}),
            'url': ('django.db.models.fields.URLField', [], {'max_length': '200', 'blank': 'True'})
        },
        'core.image': {
            'Meta': {'object_name': 'Image', 'db_table': "'comics_image'"},
            'checksum': ('django.db.models.fields.CharField', [], {'max_length': '64', 'db_index': 'True'}),
            'comic': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['core.Comic']"}),
            'fetched': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'file': ('django.db.models.fields.files.ImageField', [], {'max_length': '100'}),
            'height': ('django.db.models.fields.IntegerField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'text': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'width': ('django.db.models.fields.IntegerField', [], {})
        },
        'core.release': {
            'Meta': {'object_name': 'Release', 'db_table': "'comics_release'"},
            'comic': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['core.Comic']"}),
            'fetched': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'images': ('django.db.models.fields.related.ManyToManyField', [], {'related_name': "'releases'", 'symmetrical': 'False', 'to': "orm['core.Image']"}),
            'pub_date': ('django.db.models.fields.DateField', [], {})
        }
    }

    complete_apps = ['core']

########NEW FILE########
__FILENAME__ = 0014_auto__add_index_release_pub_date
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding index on 'Release', fields ['pub_date']
        db.create_index('comics_release', ['pub_date'])


    def backwards(self, orm):
        # Removing index on 'Release', fields ['pub_date']
        db.delete_index('comics_release', ['pub_date'])


    models = {
        'core.comic': {
            'Meta': {'ordering': "['name']", 'object_name': 'Comic', 'db_table': "'comics_comic'"},
            'active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'added': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'end_date': ('django.db.models.fields.DateField', [], {'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'language': ('django.db.models.fields.CharField', [], {'max_length': '2'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'rights': ('django.db.models.fields.CharField', [], {'max_length': '100', 'blank': 'True'}),
            'slug': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '100'}),
            'start_date': ('django.db.models.fields.DateField', [], {'null': 'True', 'blank': 'True'}),
            'url': ('django.db.models.fields.URLField', [], {'max_length': '200', 'blank': 'True'})
        },
        'core.image': {
            'Meta': {'object_name': 'Image', 'db_table': "'comics_image'"},
            'checksum': ('django.db.models.fields.CharField', [], {'max_length': '64', 'db_index': 'True'}),
            'comic': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['core.Comic']"}),
            'fetched': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'file': ('django.db.models.fields.files.ImageField', [], {'max_length': '100'}),
            'height': ('django.db.models.fields.IntegerField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'text': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'width': ('django.db.models.fields.IntegerField', [], {})
        },
        'core.release': {
            'Meta': {'object_name': 'Release', 'db_table': "'comics_release'"},
            'comic': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['core.Comic']"}),
            'fetched': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'images': ('django.db.models.fields.related.ManyToManyField', [], {'related_name': "'releases'", 'symmetrical': 'False', 'to': "orm['core.Image']"}),
            'pub_date': ('django.db.models.fields.DateField', [], {'db_index': 'True'})
        }
    }

    complete_apps = ['core']
########NEW FILE########
__FILENAME__ = 0015_auto__add_index_release_fetched
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding index on 'Release', fields ['fetched']
        db.create_index('comics_release', ['fetched'])


    def backwards(self, orm):
        # Removing index on 'Release', fields ['fetched']
        db.delete_index('comics_release', ['fetched'])


    models = {
        'core.comic': {
            'Meta': {'ordering': "['name']", 'object_name': 'Comic', 'db_table': "'comics_comic'"},
            'active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'added': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'end_date': ('django.db.models.fields.DateField', [], {'null': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'language': ('django.db.models.fields.CharField', [], {'max_length': '2'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'rights': ('django.db.models.fields.CharField', [], {'max_length': '100', 'blank': 'True'}),
            'slug': ('django.db.models.fields.SlugField', [], {'unique': 'True', 'max_length': '100'}),
            'start_date': ('django.db.models.fields.DateField', [], {'null': 'True', 'blank': 'True'}),
            'url': ('django.db.models.fields.URLField', [], {'max_length': '200', 'blank': 'True'})
        },
        'core.image': {
            'Meta': {'object_name': 'Image', 'db_table': "'comics_image'"},
            'checksum': ('django.db.models.fields.CharField', [], {'max_length': '64', 'db_index': 'True'}),
            'comic': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['core.Comic']"}),
            'fetched': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'file': ('django.db.models.fields.files.ImageField', [], {'max_length': '100'}),
            'height': ('django.db.models.fields.IntegerField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'text': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'width': ('django.db.models.fields.IntegerField', [], {})
        },
        'core.release': {
            'Meta': {'object_name': 'Release', 'db_table': "'comics_release'"},
            'comic': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['core.Comic']"}),
            'fetched': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'db_index': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'images': ('django.db.models.fields.related.ManyToManyField', [], {'related_name': "'releases'", 'symmetrical': 'False', 'to': "orm['core.Image']"}),
            'pub_date': ('django.db.models.fields.DateField', [], {'db_index': 'True'})
        }
    }

    complete_apps = ['core']
########NEW FILE########
__FILENAME__ = models
import datetime
import os

from django.conf import settings
from django.core.files.storage import FileSystemStorage
from django.core.urlresolvers import reverse
from django.db import models
from django.utils import timezone

from comics.core.managers import ComicManager


class Comic(models.Model):
    LANGUAGES = (
        ('en', 'English'),
        ('no', 'Norwegian'),
    )

    # Required fields
    name = models.CharField(
        max_length=100,
        help_text='Name of the comic')
    slug = models.SlugField(
        max_length=100, unique=True,
        verbose_name='Short name',
        help_text='For file paths and URLs')
    language = models.CharField(
        max_length=2, choices=LANGUAGES,
        help_text='The language of the comic')

    # Optional fields
    url = models.URLField(
        verbose_name='URL', blank=True,
        help_text='URL to the official website')
    active = models.BooleanField(
        default=True,
        help_text='Wheter the comic is still being crawled')
    start_date = models.DateField(
        blank=True, null=True,
        help_text='First published at')
    end_date = models.DateField(
        blank=True, null=True,
        help_text='Last published at, if comic has been cancelled')
    rights = models.CharField(
        max_length=100, blank=True,
        help_text='Author, copyright, and/or licensing information')

    # Automatically populated fields
    added = models.DateTimeField(
        auto_now_add=True,
        help_text='Time the comic was added to the site')

    objects = ComicManager()

    class Meta:
        db_table = 'comics_comic'
        ordering = ['name']

    def __unicode__(self):
        return self.slug

    def get_absolute_url(self):
        return reverse('comic_latest', kwargs={'comic_slug': self.slug})

    def get_redirect_url(self):
        return reverse('comic_website', kwargs={'comic_slug': self.slug})

    def is_new(self):
        some_time_ago = timezone.now() - datetime.timedelta(
            days=settings.COMICS_NUM_DAYS_COMIC_IS_NEW)
        return self.added > some_time_ago


class Release(models.Model):
    # Required fields
    comic = models.ForeignKey(Comic)
    pub_date = models.DateField(verbose_name='publication date', db_index=True)
    images = models.ManyToManyField('Image', related_name='releases')

    # Automatically populated fields
    fetched = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = 'comics_release'
        get_latest_by = 'pub_date'

    def __unicode__(self):
        return u'Release %s/%s' % (self.comic.slug, self.pub_date)

    def get_absolute_url(self):
        return reverse('comic_day', kwargs={
            'comic_slug': self.comic.slug,
            'year': self.pub_date.year,
            'month': self.pub_date.month,
            'day': self.pub_date.day,
        })

    def get_ordered_images(self):
        if not getattr(self, '_ordered_images', []):
            self._ordered_images = list(self.images.order_by('id'))
        return self._ordered_images


# Let all created dirs and files be writable by the group
os.umask(0002)

image_storage = FileSystemStorage(
    location=settings.MEDIA_ROOT, base_url=settings.MEDIA_URL)


def image_file_path(instance, filename):
    return u'%s/%s/%s' % (instance.comic.slug, filename[0], filename)


class Image(models.Model):
    # Required fields
    comic = models.ForeignKey(Comic)
    file = models.ImageField(
        storage=image_storage, upload_to=image_file_path,
        height_field='height', width_field='width')
    checksum = models.CharField(max_length=64, db_index=True)

    # Optional fields
    title = models.CharField(max_length=255, blank=True)
    text = models.TextField(blank=True)

    # Automatically populated fields
    fetched = models.DateTimeField(auto_now_add=True)
    height = models.IntegerField()
    width = models.IntegerField()

    class Meta:
        db_table = 'comics_image'

    def __unicode__(self):
        return u'Image %s/%s...' % (self.comic.slug, self.checksum[:8])

########NEW FILE########
__FILENAME__ = list_to_columns
"""Splits query results list into multiple sublists for template display."""

from django.template import Library, Node, TemplateSyntaxError

register = Library()


class SplitListNode(Node):
    def __init__(self, results, cols, new_results):
        self.results, self.cols, self.new_results = results, cols, new_results

    def split_seq(self, results, cols=2):
        start = 0
        results = list(results)
        for i in xrange(cols):
            stop = start + len(results[i::cols])
            yield results[start:stop]
            start = stop

    def render(self, context):
        context[self.new_results] = self.split_seq(
            context[self.results], int(self.cols))
        return ''


def list_to_columns(parser, token):
    """Parse template tag: {% list_to_columns results as new_results 2 %}"""
    bits = token.contents.split()
    if len(bits) != 5:
        raise TemplateSyntaxError("list_to_columns results as new_results 2")
    if bits[2] != 'as':
        raise TemplateSyntaxError(
            "second argument to the list_to_columns " "tag must be 'as'")
    return SplitListNode(bits[1], bits[4], bits[3])


list_to_columns = register.tag(list_to_columns)

########NEW FILE########
__FILENAME__ = forms
from django import forms


class FeedbackForm(forms.Form):
    message = forms.CharField(
        label="What's on your heart?",
        help_text='Sign with your email address if you want a reply.',
        widget=forms.Textarea(attrs={'rows': 5, 'cols': 100}))

########NEW FILE########
__FILENAME__ = models

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls import patterns, url

from comics.help import views

urlpatterns = patterns(
    '',

    url(r'^$', views.about, name='help_about'),
    url(r'^feedback/$', views.feedback, name='help_feedback'),
    url(r'^keyboard/$', views.keyboard, name='help_keyboard'),
)

########NEW FILE########
__FILENAME__ = views
from django.conf import settings
from django.contrib import messages
from django.core.mail import EmailMessage
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect
from django.shortcuts import render

from comics.help.forms import FeedbackForm


def about(request):
    return render(request, 'help/about.html', {
        'active': {
            'help': True,
            'about': True,
        },
    })


def feedback(request):
    """Mail feedback to ADMINS"""

    if request.method == 'POST':
        form = FeedbackForm(request.POST)
        if form.is_valid():
            subject = 'Feedback from %s' % settings.COMICS_SITE_TITLE

            metadata = 'Client IP address: %s\n' % request.META['REMOTE_ADDR']
            metadata += 'User agent: %s\n' % request.META['HTTP_USER_AGENT']
            if request.user.is_authenticated():
                metadata += 'User: %s <%s>\n' % (
                    request.user.username, request.user.email)
            else:
                metadata += 'User: anonymous\n'

            message = '%s\n\n-- \n%s' % (
                form.cleaned_data['message'], metadata)

            headers = {}
            if request.user.is_authenticated():
                headers['Reply-To'] = request.user.email

            mail = EmailMessage(
                subject=subject, body=message,
                to=[email for name, email in settings.ADMINS],
                headers=headers)
            mail.send()

            messages.info(
                request,
                'Thank you for taking the time to help improve the site! :-)')
            return HttpResponseRedirect(reverse('help_feedback'))
    else:
        form = FeedbackForm()

    return render(request, 'help/feedback.html', {
        'active': {
            'help': True,
            'feedback': True,
        },
        'feedback_form': form,
    })


def keyboard(request):
    return render(request, 'help/keyboard.html', {
        'active': {
            'help': True,
            'keyboard': True,
        },
    })

########NEW FILE########
__FILENAME__ = admin
from django.contrib import admin

from comics.sets import models


class SetAdmin(admin.ModelAdmin):
    list_display = ('name', 'created', 'last_modified', 'last_loaded')


admin.site.register(models.Set, SetAdmin)

########NEW FILE########
__FILENAME__ = models
from django.db import models
from django.utils import timezone

from comics.core.models import Comic


class Set(models.Model):
    name = models.SlugField(
        max_length=100, unique=True,
        help_text='The set identifier')
    add_new_comics = models.BooleanField(
        default=False,
        help_text='Automatically add new comics to the set')
    hide_empty_comics = models.BooleanField(
        default=False,
        help_text='Hide comics without matching releases from view')
    created = models.DateTimeField(auto_now_add=True)
    last_modified = models.DateTimeField()
    last_loaded = models.DateTimeField()
    comics = models.ManyToManyField(Comic)

    class Meta:
        db_table = 'comics_set'
        ordering = ['name']

    def __unicode__(self):
        return self.name

    def get_slug(self):
        return self.name

    def set_slug(self, slug):
        self.name = slug

    slug = property(get_slug, set_slug)

    def set_loaded(self):
        self.last_loaded = timezone.now()
        self.save()

########NEW FILE########
__FILENAME__ = base
import os

BASE_PATH = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))

SECRET_KEY = ''

#: Database settings. You will want to change this for production. See the
#: Django docs for details.
DATABASES = {
    'default': {
        'NAME': os.path.join(BASE_PATH, 'db.sqlite3'),
        'ENGINE': 'django.db.backends.sqlite3',
    }
}

#: Default time zone to use when displaying datetimes to users
TIME_ZONE = 'UTC'

LANGUAGE_CODE = 'en-us'

USE_I18N = False
USE_L10N = False
USE_TZ = True

#: Path on disk to where downloaded media will be stored and served from
MEDIA_ROOT = os.path.join(BASE_PATH, 'media')

#: URL to where downloaded media will be stored and served from
MEDIA_URL = '/media/'

#: Path on disk to where static files will be served from
STATIC_ROOT = os.path.join(BASE_PATH, 'static')

#: URL to where static files will be served from
STATIC_URL = '/static/'

STATICFILES_DIRS = (
    os.path.join(BASE_PATH, 'comics', 'static'),
)
STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
    'compressor.finders.CompressorFinder',
)

TEMPLATE_CONTEXT_PROCESSORS = (
    'django.contrib.auth.context_processors.auth',
    'django.contrib.messages.context_processors.messages',
    'django.core.context_processors.i18n',
    'django.core.context_processors.media',
    'django.core.context_processors.static',
    'comics.core.context_processors.site_settings',
    'comics.core.context_processors.all_comics',
)

TEMPLATE_LOADERS = (
    ('django.template.loaders.cached.Loader', (
        'django.template.loaders.app_directories.Loader',
    )),
)

MIDDLEWARE_CLASSES = (
    # Disabled to prevent BREACH attack, ref.
    # https://www.djangoproject.com/weblog/2013/aug/06/breach-and-django/
    #'django.middleware.gzip.GZipMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'django.middleware.http.ConditionalGetMiddleware',
    'comics.core.middleware.MinifyHTMLMiddleware',
)

INSTALLED_APPS = (
    'django.contrib.admin',
    'django.contrib.admindocs',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.messages',
    'django.contrib.sessions',
    'django.contrib.staticfiles',
    'bootstrapform',
    'compressor',
    'invitation',
    'registration',
    'south',
    'tastypie',
    'comics.core',
    'comics.accounts',
    'comics.aggregator',
    'comics.api',
    'comics.browser',
    'comics.help',
    'comics.status',
)

ROOT_URLCONF = 'comics.urls'

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'filters': {
        'require_debug_false': {
            '()': 'django.utils.log.RequireDebugFalse'
        }
    },
    'handlers': {
        'mail_admins': {
            'level': 'ERROR',
            'filters': ['require_debug_false'],
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

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'TIMEOUT': 300,
        'OPTIONS': {
            'MAX_ENTRIES': 1000,
        },
    }
}
CACHE_MIDDLEWARE_SECONDS = 300
CACHE_MIDDLEWARE_KEY_PREFIX = 'comics'
CACHE_MIDDLEWARE_ANONYMOUS_ONLY = True

DATE_FORMAT = 'l j F Y'
TIME_FORMAT = 'H:i'

#: Time the user session cookies will be valid. 1 year by default.
SESSION_COOKIE_AGE = 86400 * 365

WSGI_APPLICATION = 'comics.wsgi.application'


### django_compressor settings

# Explicitly use HtmlParser to avoid depending on BeautifulSoup through the use
# of LxmlParser
COMPRESS_PARSER = 'compressor.parser.HtmlParser'

# Turn on CSS compression. JS compression is on by default if jsmin is
# installed
COMPRESS_CSS_FILTERS = [
    'compressor.filters.css_default.CssAbsoluteFilter',
    'compressor.filters.cssmin.CSSMinFilter',
]

# Turn on HTML compression through custom middleware
COMPRESS_HTML = True


### django.contrib.auth settings

LOGIN_URL = 'login'
LOGOUT_URL = 'logout'
AUTH_PROFILE_MODULE = 'accounts.UserProfile'
AUTHENTICATION_BACKENDS = (
    'comics.accounts.backends.AuthBackend',
    'django.contrib.auth.backends.ModelBackend'
)


### django-registration settings

#: Number of days an the account activation link will work
ACCOUNT_ACTIVATION_DAYS = 7

LOGIN_REDIRECT_URL = '/'
REGISTRATION_BACKEND = 'comics.accounts.backends.RegistrationBackend'


### django-invitation settings

#: Turn invitations off by default, leaving the site open for user
#: registrations
INVITE_MODE = False

#: Number of days an invitation will be valid
ACCOUNT_INVITATION_DAYS = 7

#: Number of invitations each existing user can send
INVITATIONS_PER_USER = 10


### Tastypie settings

TASTYPIE_DEFAULT_FORMATS = ['json', 'jsonp', 'xml', 'yaml', 'html', 'plist']


### comics settings

#: Name of the site. Used in page header, page title, feed titles, etc.
COMICS_SITE_TITLE = 'example.com'

#: Maximum number of releases to show on one page
COMICS_MAX_RELEASES_PER_PAGE = 50

#: Maximum number of days to show in a feed
COMICS_MAX_DAYS_IN_FEED = 30

#: SHA256 of blacklisted images
COMICS_IMAGE_BLACKLIST = (
    # Empty file
    'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855',
    # Billy
    'f8021551b772384d1f4309e0ee15c94cea9ec1e61ba0a7aade8036e40e3179fe',
    # Bizarro
    'dd040144f802bab9b96892cc2e1be26b226e7b43b275aa49dbcc9c4a254d6782',
    # Dagbladet.no
    '61c66a1c84408df5b855004dd799d5e59f4af99f4c6fe8bf4aabf8963cab7cb5',
    # Cyanide and Happiness
    '01237a79e2a283718059e4a180a01e8ffa9f9b36af7e0cad5650dd1a08665971',
    '181e7d11ebd3224a910d9eba2995349da5d483f3ae9643a2efe4f7dd3d9f668d',
    '6dec8be9787fc8b103746886033ccad7348bc4eec44c12994ba83596f3cbcd32',
    'f56248bf5b94b324d495c3967e568337b6b15249d4dfe7f9d8afdca4cb54cd29',
    '0a929bfebf333a16226e0734bbaefe3b85f9c615ff8fb7a777954793788b6e34',
    # Dilbert (bt.no)
    'cde5b71cfb91c05d0cd19f35e325fc1cc9f529dfbce5c6e2583a3aa73d240638',
    # GoComics
    '60478320f08212249aefaa3ac647fa182dc7f0d7b70e5691c5f95f9859319bdf',
    # Least I Could Do
    '38eca900236617b2c38768c5e5fa410544fea7a3b79cc1e9bd45043623124dbf',
    # tu.no
    'e90e3718487c99190426b3b38639670d4a3ee39c1e7319b9b781740b0c7a53bf',
)

#: Comics log file path on disk
COMICS_LOG_FILENAME = os.path.join(BASE_PATH, 'comics.log')

#: Google Analytics tracking code. Tracking code will be included on all pages
#: if this is set.
COMICS_GOOGLE_ANALYTICS_CODE = None

#: Number of seconds browsers at the latest view of "My comics" should wait
#: before they check for new releases again
COMICS_BROWSER_REFRESH_INTERVAL = 60

#: Number of days a new comic on the site is labeled as new
COMICS_NUM_DAYS_COMIC_IS_NEW = 7

########NEW FILE########
__FILENAME__ = dev
from comics.settings.base import *  # NOQA

try:
    from comics.settings.local import *  # NOQA
except ImportError:
    pass

DEBUG = True
TEMPLATE_DEBUG = DEBUG

TEMPLATE_LOADERS = (
    'django.template.loaders.app_directories.Loader',
)

try:
    import debug_toolbar  # NOQA
    MIDDLEWARE_CLASSES += ('debug_toolbar.middleware.DebugToolbarMiddleware',)
    INSTALLED_APPS += ('debug_toolbar',)
except ImportError:
    pass

try:
    import django_extensions  # NOQA
    INSTALLED_APPS += ('django_extensions',)
except ImportError:
    pass

########NEW FILE########
__FILENAME__ = models

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls import patterns, url

from comics.status import views

urlpatterns = patterns(
    '',
    url(r'^$', views.status, name='status'),
)

########NEW FILE########
__FILENAME__ = views
import datetime

from django.contrib.auth.decorators import login_required
from django.db.models import Max
from django.shortcuts import render
from django.utils.datastructures import SortedDict

from comics.core.models import Comic, Release
from comics.aggregator.utils import get_comic_schedule


@login_required
def status(request, num_days=21):
    today = datetime.date.today()
    timeline = SortedDict()
    last = today - datetime.timedelta(days=num_days)

    releases = Release.objects.filter(pub_date__gte=last, comic__active=True)
    releases = releases.select_related().order_by('comic__slug').distinct()

    comics = Comic.objects.filter(active=True)
    comics = comics.annotate(last_pub_date=Max('release__pub_date'))
    comics = comics.order_by('last_pub_date')

    for comic in comics:
        if comic.last_pub_date:
            comic.days_since_last_release = (today - comic.last_pub_date).days
        else:
            comic.days_since_last_release = 1000

        schedule = get_comic_schedule(comic)
        timeline[comic] = []

        for i in range(num_days + 1):
            day = today - datetime.timedelta(days=i)
            classes = set()

            if not schedule:
                classes.add('unscheduled')
            elif int(day.strftime('%w')) in schedule:
                classes.add('scheduled')

            timeline[comic].append([classes, day, None])

    for release in releases:
        day = (today - release.pub_date).days
        timeline[release.comic][day][0].add('fetched')
        timeline[release.comic][day][2] = release

    days = [
        today - datetime.timedelta(days=i)
        for i in range(num_days + 1)]

    return render(request, 'status/status.html', {
        'days': days,
        'timeline': timeline,
    })

########NEW FILE########
__FILENAME__ = urls
from __future__ import absolute_import

from django.conf import settings
from django.conf.urls import include, patterns
from django.contrib import admin
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
from django.views.generic.base import TemplateView

admin.autodiscover()

urlpatterns = patterns(
    '',

    # Robots not welcome
    (r'^robots\.txt$', TemplateView.as_view(
        template_name='robots.txt', content_type='text/plain')),

    # User accounts management
    (r'^account/', include('comics.accounts.urls')),

    # API
    (r'^api/', include('comics.api.urls')),

    # Help, about and feedback
    (r'^help/', include('comics.help.urls')),

    # Comic crawler status
    (r'^status/', include('comics.status.urls')),

    # Django admin
    (r'^admin/doc/', include('django.contrib.admindocs.urls')),
    (r'^admin/', include(admin.site.urls)),

    # Comics browsing. Must be last one included.
    (r'^', include('comics.browser.urls')),
)

# Let Django host media if doing local development on runserver
if not settings.MEDIA_URL.startswith('http'):
    urlpatterns += patterns(
        '',
        (r'^media/(?P<path>.*)$', 'django.views.static.serve',
            {'document_root': settings.MEDIA_ROOT}),
    )

urlpatterns += staticfiles_urlpatterns()

########NEW FILE########
__FILENAME__ = admin
from django.contrib import admin
from invitation.models import InvitationKey, InvitationUser

class InvitationKeyAdmin(admin.ModelAdmin):
    list_display = ('__unicode__', 'from_user', 'date_invited', 'key_expired')

class InvitationUserAdmin(admin.ModelAdmin):
    list_display = ('inviter', 'invitations_remaining')

admin.site.register(InvitationKey, InvitationKeyAdmin)
admin.site.register(InvitationUser, InvitationUserAdmin)

########NEW FILE########
__FILENAME__ = backends
from registration.backends.default import DefaultBackend
from invitation.models import InvitationKey

class InvitationBackend(DefaultBackend):

    def post_registration_redirect(self, request, user, *args, **kwargs):
        """
        Return the name of the URL to redirect to after successful
        user registration.

        """
        invitation_key = request.REQUEST.get('invitation_key')
        key = InvitationKey.objects.get_key(invitation_key)
        if key:
            key.mark_used(user)

        return ('registration_complete', (), {})

########NEW FILE########
__FILENAME__ = forms
from django import forms

class InvitationKeyForm(forms.Form):
    email = forms.EmailField()
    
########NEW FILE########
__FILENAME__ = cleanupinvitation
"""
A management command which deletes expired keys (e.g.,
keys which were never activated) from the database.

Calls ``InvitationKey.objects.delete_expired_keys()``, which
contains the actual logic for determining which keys are deleted.

"""

from django.core.management.base import NoArgsCommand

from invitation.models import InvitationKey


class Command(NoArgsCommand):
    help = "Delete expired invitations' keys from the database"

    def handle_noargs(self, **options):
        InvitationKey.objects.delete_expired_keys()

########NEW FILE########
__FILENAME__ = models
import hashlib
import os
import random
import datetime
from django.db import models
from django.conf import settings
from django.utils import timezone
from django.utils.http import int_to_base36
from django.utils.translation import ugettext_lazy as _
from django.contrib.auth.models import User
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.contrib.sites.models import RequestSite, Site

from registration.models import SHA1_RE

class InvitationKeyManager(models.Manager):
    def get_key(self, invitation_key):
        """
        Return InvitationKey, or None if it doesn't (or shouldn't) exist.
        """
        # Don't bother hitting database if invitation_key doesn't match pattern.
        if not SHA1_RE.search(invitation_key):
            return None
        
        try:
            key = self.get(key=invitation_key)
        except self.model.DoesNotExist:
            return None
        
        return key
        
    def is_key_valid(self, invitation_key):
        """
        Check if an ``InvitationKey`` is valid or not, returning a boolean,
        ``True`` if the key is valid.
        """
        invitation_key = self.get_key(invitation_key)
        return invitation_key and invitation_key.is_usable()

    def create_invitation(self, user):
        """
        Create an ``InvitationKey`` and returns it.
        
        The key for the ``InvitationKey`` will be a SHA1 hash, generated 
        from a combination of the ``User``'s username and a random salt.
        """
        salt = hashlib.sha1(str(random.random())).hexdigest()[:5]
        key = hashlib.sha1("%s%s%s" % (timezone.now(), salt, user.username)).hexdigest()
        return self.create(from_user=user, key=key)

    def remaining_invitations_for_user(self, user):
        """
        Return the number of remaining invitations for a given ``User``.
        """
        invitation_user, created = InvitationUser.objects.get_or_create(
            inviter=user,
            defaults={'invitations_remaining': settings.INVITATIONS_PER_USER})
        return invitation_user.invitations_remaining

    def delete_expired_keys(self):
        for key in self.filter(registrant__isnull=True):
            if key.key_expired():
                key.delete()


class InvitationKey(models.Model):
    key = models.CharField(_('invitation key'), max_length=40)
    date_invited = models.DateTimeField(_('date invited'), 
                                        default=timezone.now)
    from_user = models.ForeignKey(User, 
                                  related_name='invitations_sent')
    registrant = models.ForeignKey(User, null=True, blank=True, 
                                  related_name='invitations_used')
    
    objects = InvitationKeyManager()

    class Meta:
        ordering = ['-date_invited']
    
    def __unicode__(self):
        return u"Invitation from %s on %s" % (self.from_user.username, self.date_invited)
    
    def is_usable(self):
        """
        Return whether this key is still valid for registering a new user.        
        """
        return self.registrant is None and not self.key_expired()
    
    def key_expired(self):
        """
        Determine whether this ``InvitationKey`` has expired, returning 
        a boolean -- ``True`` if the key has expired.
        
        The date the key has been created is incremented by the number of days 
        specified in the setting ``ACCOUNT_INVITATION_DAYS`` (which should be 
        the number of days after invite during which a user is allowed to
        create their account); if the result is less than or equal to the 
        current date, the key has expired and this method returns ``True``.
        
        """
        expiration_date = datetime.timedelta(days=settings.ACCOUNT_INVITATION_DAYS)
        return self.date_invited + expiration_date <= timezone.now()
    key_expired.boolean = True
    
    def mark_used(self, registrant):
        """
        Note that this key has been used to register a new user.
        """
        self.registrant = registrant
        self.save()
        
    def send_to(self, email, request):
        """
        Send an invitation email to ``email``.
        """
        if Site._meta.installed:
            current_site = Site.objects.get_current()
        else:
            current_site = RequestSite(request)
        
        subject = render_to_string('invitation/invitation_email_subject.txt',
                                   { 'site': current_site, 
                                     'invitation_key': self })
        # Email subject *must not* contain newlines
        subject = ''.join(subject.splitlines())
        
        message = render_to_string('invitation/invitation_email.txt',
                                   { 'invitation_key': self,
                                     'expiration_days': settings.ACCOUNT_INVITATION_DAYS,
                                     'site': current_site })
        
        send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [email])

        
class InvitationUser(models.Model):
    inviter = models.ForeignKey(User, unique=True)
    invitations_remaining = models.IntegerField()

    def __unicode__(self):
        return u"InvitationUser for %s" % self.inviter.username

    
def user_post_save(sender, instance, created, **kwargs):
    """Create InvitationUser for user when User is created."""
    if created:
        invitation_user = InvitationUser()
        invitation_user.inviter = instance
        invitation_user.invitations_remaining = settings.INVITATIONS_PER_USER
        invitation_user.save()

models.signals.post_save.connect(user_post_save, sender=User)

def invitation_key_post_save(sender, instance, created, **kwargs):
    """Decrement invitations_remaining when InvitationKey is created."""
    if created:
        invitation_user = InvitationUser.objects.get(inviter=instance.from_user)
        remaining = invitation_user.invitations_remaining
        invitation_user.invitations_remaining = remaining-1
        invitation_user.save()

models.signals.post_save.connect(invitation_key_post_save, sender=InvitationKey)


########NEW FILE########
__FILENAME__ = urls
from django.conf.urls import *
from django.views.generic.base import TemplateView

from registration.forms import RegistrationFormTermsOfService
from invitation.views import invite, invited, register

urlpatterns = patterns('',
    url(r'^invite/complete/$',
                TemplateView.as_view(
                    template_name='invitation/invitation_complete.html'),
                name='invitation_complete'),
    url(r'^invite/$',
                invite,
                name='invitation_invite'),
    url(r'^invited/(?P<invitation_key>\w+)/$', 
                invited,
                name='invitation_invited'),
    url(r'^register/$',
                register,
                { 'backend': 'registration.backends.default.DefaultBackend' },
                name='registration_register'),
)

########NEW FILE########
__FILENAME__ = views
from django.conf import settings
from django.views.generic.base import TemplateView
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect
from django.contrib.auth.decorators import login_required

from registration.views import register as registration_register
from registration.forms import RegistrationForm
from registration.backends import default as registration_backend

from invitation.models import InvitationKey
from invitation.forms import InvitationKeyForm
from invitation.backends import InvitationBackend

is_key_valid = InvitationKey.objects.is_key_valid
remaining_invitations_for_user = InvitationKey.objects.remaining_invitations_for_user

class TemplateViewWithExtraContext(TemplateView):
    extra_context = None

    def get_context_data(self, **kwargs):
        context = super(TemplateViewWithExtraContext, self
            ).get_context_data(**kwargs)
        if self.extra_context is not None:
            context.update(self.extra_context)
        return context

def invited(request, invitation_key=None, extra_context=None):
    if getattr(settings, 'INVITE_MODE', False):
        if invitation_key and is_key_valid(invitation_key):
            template_name = 'invitation/invited.html'
        else:
            template_name = 'invitation/wrong_invitation_key.html'
        extra_context = extra_context is not None and extra_context.copy() or {}
        extra_context.update({'invitation_key': invitation_key})
        return TemplateViewWithExtraContext.as_view(
            template_name=template_name, extra_context=extra_context)(request)
    else:
        return HttpResponseRedirect(reverse('registration_register'))

def register(request, backend, success_url=None,
            form_class=RegistrationForm,
            disallowed_url='registration_disallowed',
            post_registration_redirect=None,
            template_name='registration/registration_form.html',
            wrong_template_name='invitation/wrong_invitation_key.html',
            extra_context=None):
    extra_context = extra_context is not None and extra_context.copy() or {}
    if getattr(settings, 'INVITE_MODE', False):
        invitation_key = request.REQUEST.get('invitation_key', False)
        if invitation_key:
            extra_context.update({'invitation_key': invitation_key})
            if is_key_valid(invitation_key):
                return registration_register(request, backend, success_url,
                                            form_class, disallowed_url,
                                            template_name, extra_context)
            else:
                extra_context.update({'invalid_key': True})
        else:
            extra_context.update({'no_key': True})
        return TemplateViewWithExtraContext.as_view(
            template_name=wrong_template_name,
            extra_context=extra_context)(request)
    else:
        return registration_register(request, backend, success_url, form_class,
                                     disallowed_url, template_name, extra_context)

def invite(request, success_url=None,
            form_class=InvitationKeyForm,
            template_name='invitation/invitation_form.html',
            extra_context=None):
    extra_context = extra_context is not None and extra_context.copy() or {}
    remaining_invitations = remaining_invitations_for_user(request.user)
    if request.method == 'POST':
        form = form_class(data=request.POST, files=request.FILES)
        if remaining_invitations > 0 and form.is_valid():
            invitation = InvitationKey.objects.create_invitation(request.user)
            invitation.send_to(form.cleaned_data["email"], request)
            # success_url needs to be dynamically generated here; setting a
            # a default value using reverse() will cause circular-import
            # problems with the default URLConf for this application, which
            # imports this file.
            return HttpResponseRedirect(success_url or reverse('invitation_complete'))
    else:
        form = form_class()
    extra_context.update({
            'form': form,
            'remaining_invitations': remaining_invitations,
        })
    return TemplateViewWithExtraContext.as_view(
        template_name=template_name, extra_context=extra_context)(request)
invite = login_required(invite)

########NEW FILE########
__FILENAME__ = conf
# -*- coding: utf-8 -*-
#
# comics documentation build configuration file, created by
# sphinx-quickstart on Sat Dec  5 17:33:45 2009.
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
sys.path.append(os.path.abspath(
    os.path.join(os.path.dirname(__file__), '..')))

# -- General configuration -----------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be extensions
# coming with Sphinx (named 'sphinx.ext.*') or your custom ones.
extensions = ['sphinx.ext.autodoc', 'sphinx.ext.extlinks',
    'sphinxcontrib.httpdomain']

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# The suffix of source filenames.
source_suffix = '.rst'

# The encoding of source files.
#source_encoding = 'utf-8'

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = u'comics'
copyright = u'2009-2013, Stein Magnus Jodal'

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
# The short X.Y version.
version = '2.2'
# The full version, including alpha/beta/rc tags.
release = '2.2.1'

# The language for content autogenerated by Sphinx. Refer to documentation
# for a list of supported languages.
#language = None

# There are two options for replacing |today|: either, you set today to some
# non-false value, then it is used:
#today = ''
# Else, today_fmt is used as the format for a strftime call.
#today_fmt = '%B %d, %Y'

# List of documents that shouldn't be included in the build.
#unused_docs = []

# List of directories, relative to source directory, that shouldn't be searched
# for source files.
exclude_trees = ['_build']

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


# -- Options for HTML output ---------------------------------------------------

# The theme to use for HTML and HTML Help pages.  Major themes that come with
# Sphinx are currently 'default' and 'sphinxdoc'.
html_theme = 'default'

# Theme options are theme-specific and customize the look and feel of a theme
# further.  For a list of options available for each theme, see the
# documentation.
#html_theme_options = {}

# Add any paths that contain custom themes here, relative to this directory.
html_theme_path = ['_themes']

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
#html_use_modindex = True

# If false, no index is generated.
#html_use_index = True

# If true, the index is split into individual pages for each letter.
#html_split_index = False

# If true, links to the reST sources are added to the pages.
html_show_sourcelink = False

# If true, an OpenSearch description file will be output, and all pages will
# contain a <link> tag referring to it.  The value of this option must be the
# base URL from which the finished HTML is served.
#html_use_opensearch = ''

# If nonempty, this is the file name suffix for HTML files (e.g. ".xhtml").
#html_file_suffix = ''

# Output file base name for HTML help builder.
htmlhelp_basename = 'comicsdoc'


# -- Options for LaTeX output --------------------------------------------------

# The paper size ('letter' or 'a4').
#latex_paper_size = 'letter'

# The font size ('10pt', '11pt' or '12pt').
#latex_font_size = '10pt'

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title, author, documentclass [howto/manual]).
latex_documents = [
  ('index', 'comics.tex', u'comics Documentation',
   u'Stein Magnus Jodal', 'manual'),
]

# The name of an image file (relative to this directory) to place at the top of
# the title page.
#latex_logo = None

# For "manual" documents, if this is true, then toplevel headings are parts,
# not chapters.
#latex_use_parts = False

# Additional stuff for the LaTeX preamble.
#latex_preamble = ''

# Documents to append as an appendix to all manuals.
#latex_appendices = []

# If false, no module index is generated.
#latex_use_modindex = True


extlinks = {'issue': ('https://github.com/jodal/comics/issues/%s', '#')}

########NEW FILE########
__FILENAME__ = manage
#!/usr/bin/env python
import os, sys

if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "comics.settings")

    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)

########NEW FILE########
