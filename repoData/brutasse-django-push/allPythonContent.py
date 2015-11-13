__FILENAME__ = feeds
from django.conf import settings
from django.contrib.syndication.views import Feed as BaseFeed
from django.utils.feedgenerator import Atom1Feed


class HubAtom1Feed(Atom1Feed):
    def add_root_elements(self, handler):
        super(HubAtom1Feed, self).add_root_elements(handler)

        hub = self.feed.get('hub')
        if hub is not None:
            handler.addQuickElement('link', '', {'rel': 'hub',
                                                 'href': hub})


class Feed(BaseFeed):
    feed_type = HubAtom1Feed
    hub = None

    def get_hub(self, obj):
        if self.hub is None:
            hub = getattr(settings, 'PUSH_HUB', None)
        else:
            hub = self.hub
        return hub

    def feed_extra_kwargs(self, obj):
        kwargs = super(Feed, self).feed_extra_kwargs(obj)
        kwargs['hub'] = self.get_hub(obj)
        return kwargs

########NEW FILE########
__FILENAME__ = admin
from django.contrib import admin, messages
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _, ungettext

from django_push.subscriber.models import Subscription, SubscriptionError


class ExpirationFilter(admin.SimpleListFilter):
    title = _('Expired')
    parameter_name = 'expired'

    def lookups(self, request, model_admin):
        return (
            ('true', _('Yes')),
            ('false', _('No')),
        )

    def queryset(self, request, queryset):
        if self.value() == 'true':
            return queryset.filter(lease_expiration__lte=timezone.now())
        if self.value() == 'false':
            return queryset.filter(lease_expiration__gte=timezone.now())


class SubscriptionAmin(admin.ModelAdmin):
    list_display = ('truncated_topic', 'hub', 'verified', 'has_expired',
                    'lease_expiration')
    list_filter = ('verified', ExpirationFilter, 'hub')
    search_fields = ('topic', 'hub')
    actions = ['renew', 'unsubscribe']
    readonly_fields = ['callback_url']

    def renew(self, request, queryset):
        count = 0
        failed = 0
        for subscription in queryset:
            try:
                subscription.subscribe()
                count += 1
            except SubscriptionError:
                failed += 1
        if count:
            message = ungettext(
                '%s subscription was successfully renewed.',
                '%s subscriptions were successfully renewd.',
                count) % count
            self.message_user(request, message)
        if failed:
            message = ungettext(
                'Failed to renew %s subscription.',
                'Failed to renew %s subscriptions.',
                failed) % failed
            self.message_user(request, message, level=messages.ERROR)
    renew.short_description = _('Renew selected subscriptions')

    def unsubscribe(self, request, queryset):
        count = 0
        failed = 0
        for subscription in queryset:
            try:
                subscription.unsubscribe()
                count += 1
            except SubscriptionError:
                failed += 1
        if count:
            message = ungettext(
                'Successfully unsubscribed from %s topic.',
                'Successfully unsubscribed from %s topics.',
                count) % count
            self.message_user(request, message)
        if failed:
            message = ungettext(
                'Failed to unsubscribe from %s topic.',
                'Failed to unsubscribe from %s topics.',
                failed) % failed
            self.message_user(request, message, level=messages.ERROR)
    unsubscribe.short_description = _('Unsubscribe from selected topics')
admin.site.register(Subscription, SubscriptionAmin)

########NEW FILE########
__FILENAME__ = 0001_initial
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'Subscription'
        db.create_table(u'subscriber_subscription', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('hub', self.gf('django.db.models.fields.URLField')(max_length=1023)),
            ('topic', self.gf('django.db.models.fields.URLField')(max_length=1023)),
            ('verified', self.gf('django.db.models.fields.BooleanField')(default=False)),
            ('verify_token', self.gf('django.db.models.fields.CharField')(max_length=255)),
            ('lease_expiration', self.gf('django.db.models.fields.DateTimeField')(null=True)),
            ('secret', self.gf('django.db.models.fields.CharField')(max_length=255, null=True)),
        ))
        db.send_create_signal(u'subscriber', ['Subscription'])


    def backwards(self, orm):
        # Deleting model 'Subscription'
        db.delete_table(u'subscriber_subscription')


    models = {
        u'subscriber.subscription': {
            'Meta': {'object_name': 'Subscription'},
            'hub': ('django.db.models.fields.URLField', [], {'max_length': '1023'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'lease_expiration': ('django.db.models.fields.DateTimeField', [], {'null': 'True'}),
            'secret': ('django.db.models.fields.CharField', [], {'max_length': '255', 'null': 'True'}),
            'topic': ('django.db.models.fields.URLField', [], {'max_length': '1023'}),
            'verified': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'verify_token': ('django.db.models.fields.CharField', [], {'max_length': '255'})
        }
    }

    complete_apps = ['subscriber']
########NEW FILE########
__FILENAME__ = 0002_auto__chg_field_subscription_secret
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):

        # Changing field 'Subscription.secret'
        db.alter_column(u'subscriber_subscription', 'secret', self.gf('django.db.models.fields.CharField')(default='', max_length=255))

    def backwards(self, orm):

        # Changing field 'Subscription.secret'
        db.alter_column(u'subscriber_subscription', 'secret', self.gf('django.db.models.fields.CharField')(max_length=255, null=True))

    models = {
        u'subscriber.subscription': {
            'Meta': {'object_name': 'Subscription'},
            'hub': ('django.db.models.fields.URLField', [], {'max_length': '1023'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'lease_expiration': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'secret': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'topic': ('django.db.models.fields.URLField', [], {'max_length': '1023'}),
            'verified': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'verify_token': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'})
        }
    }

    complete_apps = ['subscriber']
########NEW FILE########
__FILENAME__ = models
# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import logging

from datetime import timedelta

try:
    from urllib.parse import urlparse
except ImportError:  # python2
    from urlparse import urlparse

import requests

from django.conf import settings
from django.core.urlresolvers import reverse
from django.db import models
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _

from .utils import get_hub_credentials, generate_random_string, get_domain

logger = logging.getLogger(__name__)


class SubscriptionError(Exception):
    pass


class SubscriptionManager(models.Manager):
    def subscribe(self, topic, hub, lease_seconds=None):
        # Only use a secret over HTTPS
        scheme = urlparse(hub).scheme
        defaults = {}
        if scheme == 'https':
            defaults['secret'] = generate_random_string()

        subscription, created = self.get_or_create(hub=hub, topic=topic,
                                                   defaults=defaults)
        subscription.subscribe(lease_seconds=lease_seconds)
        return subscription


class Subscription(models.Model):
    hub = models.URLField(_('Hub'), max_length=1023)
    topic = models.URLField(_('Topic'), max_length=1023)
    verified = models.BooleanField(_('Verified'), default=False)
    verify_token = models.CharField(_('Verify Token'), max_length=255,
                                    blank=True)
    lease_expiration = models.DateTimeField(_('Lease expiration'),
                                            null=True, blank=True)
    secret = models.CharField(_('Secret'), max_length=255, blank=True)

    objects = SubscriptionManager()

    def __unicode__(self):
        return '%s: %s' % (self.topic, self.hub)

    def set_expiration(self, seconds):
        self.lease_expiration = timezone.now() + timedelta(seconds=seconds)

    def has_expired(self):
        if self.lease_expiration:
            return timezone.now() > self.lease_expiration
        return False
    has_expired.boolean = True

    def truncated_topic(self):
        if len(self.topic) > 50:
            return self.topic[:49] + '…'
        return self.topic
    truncated_topic.short_description = _('Topic')
    truncated_topic.admin_order_field = 'topic'

    @property
    def callback_url(self):
        callback_url = reverse('subscriber_callback', args=[self.pk])
        use_ssl = getattr(settings, 'PUSH_SSL_CALLBACK', False)
        scheme = 'https' if use_ssl else 'http'
        return '%s://%s%s' % (scheme, get_domain(), callback_url)

    def subscribe(self, lease_seconds=None):
        return self.send_request(mode='subscribe', lease_seconds=lease_seconds)

    def unsubscribe(self):
        return self.send_request(mode='unsubscribe')

    def send_request(self, mode, lease_seconds=None):
        params = {
            'hub.mode': mode,
            'hub.callback': self.callback_url,
            'hub.topic': self.topic,
            'hub.verify': ['sync', 'async'],
        }

        if self.secret:
            params['hub.secret'] = self.secret

        if lease_seconds is None:
            lease_seconds = getattr(settings, 'PUSH_LEASE_SECONDS', None)

        # If not provided, let the hub decide.
        if lease_seconds is not None:
            params['hub.lease_seconds'] = lease_seconds

        credentials = get_hub_credentials(self.hub)
        timeout = getattr(settings, 'PUSH_TIMEOUT', None)
        response = requests.post(self.hub, data=params, auth=credentials,
                                 timeout=timeout)

        if response.status_code in (202, 204):
            if (
                mode == 'subscribe' and
                response.status_code == 204  # synchronous verification (0.3)
            ):
                self.verified = True
                Subscription.objects.filter(pk=self.pk).update(verified=True)

            elif response.status_code == 202:
                if mode == 'unsubscribe':
                    self.pending_unsubscription = True
                    # TODO check for making sure unsubscriptions are legit
                    #Subscription.objects.filter(pk=self.pk).update(
                    #    pending_unsubscription=True)
            return response

        raise SubscriptionError(
            "Error during request to hub {0} for topic {1}: {2}".format(
                self.hub, self.topic, response.text),
            self,
            response,
        )

########NEW FILE########
__FILENAME__ = signals
from django.dispatch import Signal

updated = Signal(providing_args=['notification', 'request', 'links'])

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls import patterns, url

from .views import callback


urlpatterns = patterns(
    '',
    url(r'^(?P<pk>\d+)/$', callback, name='subscriber_callback'),
)

########NEW FILE########
__FILENAME__ = utils
from functools import partial

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.utils.crypto import get_random_string
from django.utils.importlib import import_module


generate_random_string = partial(
    get_random_string,
    length=50,
    allowed_chars='abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ'
                  '0123456789!@#$%^&*(-_=+)')


def hub_credentials(hub_url):
    """A callback that returns no credentials, for anonymous
    subscriptions. Meant to be overriden if developers need to
    authenticate with certain hubs"""
    return


def get_hub_credentials(hub_url):
    creds_path = getattr(settings, 'PUSH_CREDENTIALS',
                         'django_push.subscriber.utils.hub_credentials')
    creds_path, creds_function = creds_path.rsplit('.', 1)
    creds_module = import_module(creds_path)
    return getattr(creds_module, creds_function)(hub_url)


def get_domain():
    if hasattr(settings, 'PUSH_DOMAIN'):
        return settings.PUSH_DOMAIN
    elif 'django.contrib.sites' in settings.INSTALLED_APPS:
        from django.contrib.sites.models import Site
        return Site.objects.get_current().domain
    raise ImproperlyConfigured(
        "Unable to deterermine the site's host. Either use "
        "django.contrib.sites and set SITE_ID in your settings or "
        "set PUSH_DOMAIN to your site's domain.")

########NEW FILE########
__FILENAME__ = views
import hashlib
import hmac
import logging

from django.http import HttpResponse, HttpResponseBadRequest
from django.shortcuts import get_object_or_404
from django.utils.decorators import method_decorator
from django.views import generic
from django.views.decorators.csrf import csrf_exempt
from requests.utils import parse_header_links

from .models import Subscription
from .signals import updated

logger = logging.getLogger(__name__)


class CallbackView(generic.View):
    @method_decorator(csrf_exempt)
    def dispatch(self, *args, **kwargs):
        return super(CallbackView, self).dispatch(*args, **kwargs)

    def get(self, request, pk, *args, **kwargs):
        subscription = get_object_or_404(Subscription, pk=pk)
        params = ['hub.mode', 'hub.topic', 'hub.challenge']
        missing = [p for p in params if not p in request.GET]
        if missing:
            return HttpResponseBadRequest("Missing parameters: {0}".format(
                ", ".join(missing)))

        topic = request.GET['hub.topic']
        if not topic == subscription.topic:
            return HttpResponseBadRequest("Mismatching topic URL")

        mode = request.GET['hub.mode']

        if mode not in ['subscribe', 'unsubscribe', 'denied']:
            return HttpResponseBadRequest("Unrecognized hub.mode parameter")

        if mode == 'subscribe':
            if 'hub.lease_seconds' not in request.GET:
                return HttpResponseBadRequest(
                    "Missing hub.lease_seconds parameter")

            if not request.GET['hub.lease_seconds'].isdigit():
                return HttpResponseBadRequest(
                    "hub.lease_seconds must be an integer")

            seconds = int(request.GET['hub.lease_seconds'])
            subscription.set_expiration(seconds)
            subscription.verified = True
            logger.debug("Verifying subscription for topic {0} via {1} "
                         "(expires in {2}s)".format(subscription.topic,
                                                    subscription.hub,
                                                    seconds))
            Subscription.objects.filter(pk=subscription.pk).update(
                verified=True,
                lease_expiration=subscription.lease_expiration)

        if mode == 'unsubscribe':
            # TODO make sure it was pending deletion
            logger.debug("Deleting subscription for topic {0} via {1}".format(
                subscription.topic, subscription.hub))
            subscription.delete()

        # TODO handle denied subscriptions

        return HttpResponse(request.GET['hub.challenge'])

    def post(self, request, pk, *args, **kwargs):
        subscription = get_object_or_404(Subscription, pk=pk)

        if subscription.secret:
            signature = request.META.get('HTTP_X_HUB_SIGNATURE', None)
            if signature is None:
                logger.debug("Ignoring payload for subscription {0}, missing "
                             "signature".format(subscription.pk))
                return HttpResponse('')

            hasher = hmac.new(subscription.secret.encode('utf-8'),
                              request.body,
                              hashlib.sha1)
            digest = 'sha1=%s' % hasher.hexdigest()
            if signature != digest:
                logger.debug("Mismatching signature for subscription {0}: "
                             "got {1}, expected {2}".format(subscription.pk,
                                                            signature,
                                                            digest))
                return HttpResponse('')

        self.links = None
        if 'HTTP_LINK' in request.META:
            self.links = parse_header_links(request.META['HTTP_LINK'])
        updated.send(sender=subscription, notification=request.body,
                     request=request, links=self.links)
        self.subscription = subscription
        self.handle_subscription()
        return HttpResponse('')

    def handle_subscription(self):
        """Subclasses may implement this"""
        pass
callback = CallbackView.as_view()

########NEW FILE########
__FILENAME__ = conf
# -*- coding: utf-8 -*-
#
# django-push documentation build configuration file, created by
# sphinx-quickstart on Sun Jul  4 14:18:51 2010.
#
# This file is execfile()d with the current directory set to its containing dir.
#
# Note that not all possible configuration values are present in this
# autogenerated file.
#
# All configuration values have a default; values that are commented out
# serve to show the default.

import datetime

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#sys.path.append(os.path.abspath('.'))

# -- General configuration -----------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be extensions
# coming with Sphinx (named 'sphinx.ext.*') or your custom ones.
extensions = []

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# The suffix of source filenames.
source_suffix = '.rst'

# The encoding of source files.
#source_encoding = 'utf-8'

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = u'django-push'
copyright = u'2010-{0}, Bruno Renié'.format(datetime.datetime.today().year)

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
# The short X.Y version.
version = '0.6.1'
# The full version, including alpha/beta/rc tags.
release = '0.6.1'

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
#html_static_path = ['_static']

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
#html_show_sourcelink = True

# If true, an OpenSearch description file will be output, and all pages will
# contain a <link> tag referring to it.  The value of this option must be the
# base URL from which the finished HTML is served.
#html_use_opensearch = ''

# If nonempty, this is the file name suffix for HTML files (e.g. ".xhtml").
#html_file_suffix = ''

# Output file base name for HTML help builder.
htmlhelp_basename = 'django-pushdoc'


# -- Options for LaTeX output --------------------------------------------------

# The paper size ('letter' or 'a4').
#latex_paper_size = 'letter'

# The font size ('10pt', '11pt' or '12pt').
#latex_font_size = '10pt'

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title, author, documentclass [howto/manual]).
latex_documents = [
  ('index', 'django-push.tex', u'django-push Documentation',
   u'Bruno Renié', 'manual'),
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

########NEW FILE########
__FILENAME__ = runtests
import os
import sys
import warnings

warnings.simplefilter('always')

from django.conf import settings

try:
    from django.utils.functional import empty
except ImportError:
    empty = None


def setup_test_environment():
    # reset settings
    settings._wrapped = empty

    apps = [
        'django.contrib.sites',
        'tests.publisher',
        'tests.subscriber',
    ]

    settings_dict = {
        'DATABASES': {
            'default': {
                'ENGINE': 'django.db.backends.sqlite3',
                'NAME': os.path.join(
                    os.path.abspath(os.path.dirname(__file__)),
                    'push.sqlite',
                ),
            },
        },
        'INSTALLED_APPS': apps,
        'STATIC_URL': '/static/',
        'SECRET_KEY': 'test secret key',
        'ROOT_URLCONF': '',
        'SITE_ID': 1,
        'PUSH_DOMAIN': 'testserver.com',
    }

    settings.configure(**settings_dict)


def runtests(*test_args):
    setup_test_environment()

    parent = os.path.dirname(os.path.abspath(__file__))
    sys.path.insert(0, parent)

    from django.test.simple import DjangoTestSuiteRunner
    runner = DjangoTestSuiteRunner(verbosity=1, interactive=True,
                                   failfast=False)
    failures = runner.run_tests(test_args)
    sys.exit(failures)


if __name__ == '__main__':
    runtests()

########NEW FILE########
__FILENAME__ = feeds
from django_push.publisher.feeds import Feed


class HubFeed(Feed):
    link = '/feed/'

    def items(self):
        return [1, 2, 3]

    def item_title(self, item):
        return str(item)

    def item_link(self, item):
        return '/items/{0}'.format(item)


class OverrideHubFeed(HubFeed):
    link = '/overriden-feed/'
    hub = 'http://example.com/overridden-hub'


class DynamicHubFeed(HubFeed):
    link = '/dynamic-feed/'

    def get_hub(self, obj):
        return 'http://dynamic-hub.example.com/'

########NEW FILE########
__FILENAME__ = models

########NEW FILE########
__FILENAME__ = tests
import mock

from django.core.urlresolvers import reverse
from django.test import TestCase
from django.test.utils import override_settings

from django_push import UA
from django_push.publisher import ping_hub


class PubTestCase(TestCase):
    urls = 'tests.publisher.urls'

    @mock.patch('requests.post')
    def test_explicit_ping(self, post):
        post.return_value = 'Response'
        with self.assertRaises(ValueError):
            ping_hub('http://example.com/feed')

        ping_hub('http://example.com/feed', hub_url='http://example.com/hub')
        post.assert_called_once_with(
            'http://example.com/hub',
            headers={'User-Agent': UA},
            data={'hub.url': 'http://example.com/feed',
                  'hub.mode': 'publish'})

    @mock.patch('requests.post')
    @override_settings(PUSH_HUB='http://hub.example.com')
    def test_ping_settings(self, post):
        post.return_value = 'Response'
        ping_hub('http://example.com/feed')
        post.assert_called_once_with(
            'http://hub.example.com',
            headers={'User-Agent': UA},
            data={'hub.url': 'http://example.com/feed',
                  'hub.mode': 'publish'})

    @mock.patch('requests.post')
    @override_settings(PUSH_HUB='http://hub.example.com')
    def test_ping_settings_override(self, post):
        post.return_value = 'Response'
        ping_hub('http://example.com/feed', hub_url='http://google.com')
        post.assert_called_once_with(
            'http://google.com',
            headers={'User-Agent': UA},
            data={'hub.url': 'http://example.com/feed',
                  'hub.mode': 'publish'})

    @override_settings(PUSH_HUB='http://hub.example.com')
    def test_hub_declaration(self):
        response = self.client.get(reverse('feed'))
        hub_declaration = response.content.decode('utf-8').split(
            '</updated>', 1)[1].split('<entry>', 1)[0]
        self.assertEqual(len(hub_declaration), 53)
        self.assertTrue('rel="hub"' in hub_declaration)
        self.assertTrue('href="http://hub.example.com' in hub_declaration)

        response = self.client.get(reverse('override-feed'))
        hub_declaration = response.content.decode('utf-8').split(
            '</updated>', 1)[1].split('<entry>', 1)[0]
        self.assertEqual(len(hub_declaration), 64)
        self.assertTrue('rel="hub"' in hub_declaration)
        self.assertFalse('href="http://hub.example.com' in hub_declaration)
        self.assertTrue(
            'href="http://example.com/overridden-hub' in hub_declaration
        )

        response = self.client.get(reverse('dynamic-feed'))
        hub_declaration = response.content.decode('utf-8').split(
            '</updated>', 1)[1].split('<entry>', 1)[0]
        self.assertEqual(len(hub_declaration), 62)
        self.assertTrue('rel="hub"' in hub_declaration)
        self.assertFalse('href="http://hub.example.com' in hub_declaration)
        self.assertTrue(
            'href="http://dynamic-hub.example.com/' in hub_declaration
        )

    def test_no_hub(self):
        response = self.client.get(reverse('feed'))
        self.assertEqual(response.status_code, 200)

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls import url, patterns

from .feeds import HubFeed, OverrideHubFeed, DynamicHubFeed


urlpatterns = patterns(
    '',
    url(r'^feed/$', HubFeed(), name='feed'),
    url(r'^override-feed/$', OverrideHubFeed(), name='override-feed'),
    url(r'^dynamic-feed/$', DynamicHubFeed(), name='dynamic-feed'),
)

########NEW FILE########
__FILENAME__ = models

########NEW FILE########
__FILENAME__ = tests
import mock

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.core.urlresolvers import reverse
from django.test import TestCase
from django.test.utils import override_settings
from django.utils import timezone

from django_push.subscriber.models import Subscription, SubscriptionError
from django_push.subscriber.utils import get_domain
from django_push.subscriber.signals import updated

from .. import response


class SubscriberTestCase(TestCase):
    urls = 'tests.subscriber.urls'

    def setUp(self):
        self.signals = []
        updated.connect(self._signal_handler)

    def _signal_handler(self, sender, notification, **kwargs):
        self.signals.append([sender, notification, kwargs])

    @override_settings(INSTALLED_APPS=[])
    @mock.patch('requests.post')
    def test_subscribing(self, post):
        post.return_value = response(status_code=202)
        s = Subscription.objects.subscribe("http://example.com/feed",
                                           "http://hub.domain.com/hub")
        url = reverse('subscriber_callback', args=[s.pk])
        post.assert_called_once_with(
            'http://hub.domain.com/hub',
            data={
                'hub.callback': 'http://testserver.com{0}'.format(url),
                'hub.verify': ['sync', 'async'],
                'hub.topic': 'http://example.com/feed',
                'hub.mode': 'subscribe',
            },
            auth=None,
            timeout=None,
        )

        s = Subscription.objects.get(pk=s.pk)
        self.assertIs(s.verified, False)
        self.assertIs(s.lease_expiration, None)

    @mock.patch('requests.get')
    @mock.patch('requests.post')
    def test_subscribe_no_hub_warning(self, post, get):
        post.return_value = response(status_code=202)
        get.return_value = response(status_code=200, content="""<?xml version="1.0" encoding="utf-8"?><feed xmlns="http://www.w3.org/2005/Atom" xml:lang="en-us"><title></title><link href="http://testserver/overriden-feed/" rel="alternate"></link><link href="http://testserver/override-feed/" rel="self"></link><id>http://testserver/overriden-feed/</id><updated>2013-06-23T10:58:30Z</updated><link href="http://example.com/overridden-hub" rel="hub"></link></feed>""")  # noqa

    @mock.patch('requests.post')
    def test_subscription_secret(self, post):
        post.return_value = response(status_code=202)
        s = Subscription.objects.subscribe(
            'http://foo.com/insecure', hub='http://insecure.example.com/hub')
        self.assertEqual(s.secret, '')
        s = Subscription.objects.subscribe(
            'http://foo.com/secure', hub='https://secure.example.com/hub')
        self.assertEqual(len(s.secret), 50)

    @mock.patch('requests.post')
    def test_sync_subscribing(self, post):
        post.return_value = response(status_code=204)
        Subscription.objects.subscribe("http://example.com/feed",
                                       "http://hub.domain.com/hub")
        post.assert_called_once()
        subscription = Subscription.objects.get()
        self.assertEqual(subscription.verified, True)

    def test_get_domain(self):
        self.assertEqual(get_domain(), 'testserver.com')
        push_domain = settings.PUSH_DOMAIN
        del settings.PUSH_DOMAIN
        self.assertEqual(get_domain(), 'example.com')

        with self.settings(INSTALLED_APPS=[]):
            with self.assertRaises(ImproperlyConfigured):
                get_domain()

        settings.PUSH_DOMAIN = push_domain

    @mock.patch('requests.post')
    def test_manager_unsubscribe(self, post):
        post.return_value = response(status_code=202)
        s = Subscription.objects.create(topic='http://example.com/feed',
                                        hub='http://hub.example.com')
        post.assert_not_called()
        s.unsubscribe()
        post.assert_called_once_with(
            'http://hub.example.com',
            data={
                'hub.callback': s.callback_url,
                'hub.verify': ['sync', 'async'],
                'hub.topic': 'http://example.com/feed',
                'hub.mode': 'unsubscribe',
            },
            auth=None,
            timeout=None,
        )

    @mock.patch('requests.post')
    def test_subscribe_lease_seconds(self, post):
        post.return_value = response(status_code=202)
        with self.settings(PUSH_LEASE_SECONDS=14):  # overriden in the call
            s = Subscription.objects.subscribe('http://test.example.com/feed',
                                               hub='http://hub.example.com',
                                               lease_seconds=12)
        post.assert_called_once_with(
            'http://hub.example.com',
            data={
                'hub.callback': s.callback_url,
                'hub.verify': ['sync', 'async'],
                'hub.topic': 'http://test.example.com/feed',
                'hub.mode': 'subscribe',
                'hub.lease_seconds': 12,
            },
            auth=None,
            timeout=None,
        )

    @mock.patch('requests.post')
    def test_subscribe_timeout(self, post):
        post.return_value = response(status_code=202)
        with self.settings(PUSH_TIMEOUT=10):  # overriden in the call
            s = Subscription.objects.subscribe('http://test.example.com/feed',
                                               hub='http://hub.example.com',
                                               )
        post.assert_called_once_with(
            'http://hub.example.com',
            data={
                'hub.callback': s.callback_url,
                'hub.verify': ['sync', 'async'],
                'hub.topic': 'http://test.example.com/feed',
                'hub.mode': 'subscribe',
            },
            auth=None,
            timeout=10,
        )

    @mock.patch('requests.post')
    def test_lease_seconds_from_settings(self, post):
        post.return_value = response(status_code=202)
        with self.settings(PUSH_LEASE_SECONDS=2592000):
            s = Subscription.objects.subscribe('http://test.example.com/feed',
                                               hub='http://hub.example.com')
        post.assert_called_once_with(
            'http://hub.example.com',
            data={
                'hub.callback': s.callback_url,
                'hub.verify': ['sync', 'async'],
                'hub.topic': 'http://test.example.com/feed',
                'hub.mode': 'subscribe',
                'hub.lease_seconds': 2592000,
            },
            auth=None,
            timeout=None,
        )

    @mock.patch('requests.post')
    def test_subscription_error(self, post):
        post.return_value = response(status_code=200)
        with self.assertRaises(SubscriptionError):
            Subscription.objects.subscribe('http://example.com/test',
                                           hub='http://hub.example.com')

    @override_settings(PUSH_CREDENTIALS='tests.subscriber.credentials')
    @mock.patch('requests.post')
    def test_hub_credentials(self, post):
        post.return_value = response(status_code=202)
        s = Subscription.objects.subscribe('http://example.com/test',
                                           hub='http://hub.example.com')
        post.assert_called_once_with(
            'http://hub.example.com',
            data={
                'hub.callback': s.callback_url,
                'hub.verify': ['sync', 'async'],
                'hub.topic': 'http://example.com/test',
                'hub.mode': 'subscribe',
            },
            auth=('username', 'password'),
            timeout=None,
        )

    def test_missing_callback_params(self):
        s = Subscription.objects.create(topic='foo', hub='bar')
        url = reverse('subscriber_callback', args=[s.pk])
        response = self.client.get(url)
        self.assertContains(
            response,
            "Missing parameters: hub.mode, hub.topic, hub.challenge",
            status_code=400,
        )

    def test_wrong_topic(self):
        s = Subscription.objects.create(topic='foo', hub='bar')
        url = reverse('subscriber_callback', args=[s.pk])
        response = self.client.get(url, {
            'hub.topic': 'baz',
            'hub.mode': 'subscribe',
            'hub.challenge': 'challenge yo',
        })
        self.assertContains(response, 'Mismatching topic URL', status_code=400)

    def test_wrong_mode(self):
        s = Subscription.objects.create(topic='foo', hub='bar')
        url = reverse('subscriber_callback', args=[s.pk])
        response = self.client.get(url, {
            'hub.topic': 'foo',
            'hub.mode': 'modemode',
            'hub.challenge': 'challenge yo',
        })
        self.assertContains(response, 'Unrecognized hub.mode parameter',
                            status_code=400)

    def test_missing_lease_seconds(self):
        s = Subscription.objects.create(topic='foo', hub='bar')
        url = reverse('subscriber_callback', args=[s.pk])
        response = self.client.get(url, {
            'hub.topic': 'foo',
            'hub.mode': 'subscribe',
            'hub.challenge': 'challenge yo',
        })
        self.assertContains(response, 'Missing hub.lease_seconds parameter',
                            status_code=400)

    def test_improper_lease_seconds(self):
        s = Subscription.objects.create(topic='foo', hub='bar')
        url = reverse('subscriber_callback', args=[s.pk])
        response = self.client.get(url, {
            'hub.topic': 'foo',
            'hub.mode': 'subscribe',
            'hub.challenge': 'challenge yo',
            'hub.lease_seconds': 'yo',
        })
        self.assertContains(response, 'hub.lease_seconds must be an integer',
                            status_code=400)

    def test_verify_subscription(self):
        s = Subscription.objects.create(topic='foo', hub='bar')
        self.assertFalse(s.verified)
        self.assertIs(s.lease_expiration, None)
        self.assertFalse(s.has_expired())

        url = reverse('subscriber_callback', args=[s.pk])
        response = self.client.get(url, {
            'hub.topic': 'foo',
            'hub.mode': 'subscribe',
            'hub.challenge': 'challenge yo',
            'hub.lease_seconds': 12345,
        })
        self.assertContains(response, 'challenge yo')

        s = Subscription.objects.get(pk=s.pk)
        self.assertTrue(s.verified)
        self.assertTrue(
            12345 - (s.lease_expiration - timezone.now()).seconds < 3
        )
        self.assertFalse(s.has_expired())

    def test_verify_unsubscription(self):
        s = Subscription.objects.create(topic='foo', hub='bar')

        url = reverse('subscriber_callback', args=[s.pk])
        response = self.client.get(url, {
            'hub.topic': 'foo',
            'hub.mode': 'unsubscribe',
            'hub.challenge': 'challenge yo',
        })
        self.assertEqual(response.content.decode(), 'challenge yo')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Subscription.objects.count(), 0)

    def test_payload_no_secret(self):
        s = Subscription.objects.create(topic='foo', hub='bar')
        url = reverse('subscriber_callback', args=[s.pk])

        self.assertEqual(len(self.signals), 0)
        response = self.client.post(url, 'foo', content_type='text/plain')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(self.signals), 1)
        sender, notification = self.signals[0][:2]
        self.assertEqual(sender, s)
        self.assertEqual(notification, b'foo')

    def test_payload_missing_secret(self):
        s = Subscription.objects.create(topic='foo', hub='bar', secret='lol')
        url = reverse('subscriber_callback', args=[s.pk])

        response = self.client.post(url, 'foo', content_type='text/plain')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(self.signals), 0)

    def test_payload_wrong_signature(self):
        s = Subscription.objects.create(topic='foo', hub='bar', secret='lol')
        url = reverse('subscriber_callback', args=[s.pk])

        response = self.client.post(url, 'foo', content_type='text/plain',
                                    HTTP_X_HUB_SIGNATURE='sha1=deadbeef')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(self.signals), 0)

    def test_payload_correct_signature(self):
        s = Subscription.objects.create(topic='foo', hub='bar', secret='lol')
        url = reverse('subscriber_callback', args=[s.pk])

        sig = 'sha1=bfe9c8b0bc631a74dbc484c4e4a5a469cbb8b01f'
        response = self.client.post(url, 'foo', content_type='text/plain',
                                    HTTP_X_HUB_SIGNATURE=sig)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(self.signals), 1)

    def test_payload_link_headers(self):
        s = Subscription.objects.create(topic='foo', hub='bar')
        url = reverse('subscriber_callback', args=[s.pk])

        self.assertEqual(len(self.signals), 0)
        response = self.client.post(
            url, 'foo', content_type='text/plain', HTTP_LINK=(
                '<http://joemygod.blogspot.com/feeds/posts/default>; '
                'rel="self",<http://pubsubhubbub.appspot.com/>; rel="hub"'
            ))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(self.signals), 1)
        for link in self.signals[0][2]['links']:
            if link['rel'] == 'self':
                break
        self.assertEqual(link['url'],
                         "http://joemygod.blogspot.com/feeds/posts/default")

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls import patterns, url, include


urlpatterns = patterns(
    '',
    url(r'^subscriber/', include('django_push.subscriber.urls')),
)

########NEW FILE########
