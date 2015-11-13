__FILENAME__ = admin
from django.contrib import admin

from featureflipper.models import Feature


class FeatureAdmin(admin.ModelAdmin):
    list_display = ('name', 'description', 'status')

    def enable_features(self, request, queryset):
        for feature in queryset:
            feature.enable()
            feature.save()
        self.message_user(request, "Successfully enabled %d features." % len(queryset))
    enable_features.short_description = "Enable selected features"

    def disable_features(self, request, queryset):
        for feature in queryset:
            feature.disable()
            feature.save()
        self.message_user(request, "Successfully disabled %d features." % len(queryset))
    disable_features.short_description = "Disable selected features"

    def flip_features(self, request, queryset):
        for feature in queryset:
            feature.flip()
            feature.save()
        self.message_user(request, "Successfully flipped %d features." % len(queryset))
    flip_features.short_description = "Flip selected features"

    actions = [enable_features, disable_features, flip_features]

admin.site.register(Feature, FeatureAdmin)

########NEW FILE########
__FILENAME__ = context_processors
from featureflipper.models import Feature

# Not sure if this needs to be thread-safe, as custom tags do


def features(request):
    """
    Returns context variables required by apps that use featureflipper.
    """
    return {
        'features': request.features
    }

########NEW FILE########
__FILENAME__ = addfeature
from django.core.management.base import BaseCommand

from featureflipper.models import Feature


class Command(BaseCommand):
    args = '[feature ...]'
    help = 'Adds the named features to the database, as disabled.'

    def handle(self, *features, **options):
        for name in features:
            try:
                feature = Feature.objects.get(name=name)
            except Feature.DoesNotExist:
                Feature.objects.create(name=name, enabled=False)
                print "Added feature %s" % name
            else:
                print "Feature %s already exists, and is %s" % (feature.name, feature.status)

########NEW FILE########
__FILENAME__ = disablefeature
from django.core.management.base import BaseCommand

from featureflipper.models import Feature


class Command(BaseCommand):
    args = '[feature ...]'
    help = 'Disables the named features in the database.'

    def handle(self, *features, **options):
        for name in features:
            try:
                feature = Feature.objects.get(name=name)
            except Feature.DoesNotExist:
                print "Feature %s is not in the database." % name
                return
            else:
                if not feature.enabled:
                    print "Feature %s is already disabled." % feature
                else:
                    feature.disable()
                    feature.save()
                    print "Disabled feature %s." % feature

########NEW FILE########
__FILENAME__ = dumpfeatures
from django.core.management.base import BaseCommand
from django.utils import simplejson
from django.conf import settings

from featureflipper.models import Feature


class Command(BaseCommand):

    def handle(self, *args, **options):
        help = 'Output the features in the database in JSON format.'

        features = Feature.objects.all().values('name', 'description', 'enabled')

        # This doesn't guarantee any particular ordering of keys in each dictionary
        # values() doesn't do that, and simplejson's sort_keys just uses alpha sort

        print simplejson.dumps(list(features), indent=2)

########NEW FILE########
__FILENAME__ = enablefeature
from django.core.management.base import BaseCommand

from featureflipper.models import Feature


class Command(BaseCommand):
    args = '[feature ...]'
    help = 'Enables the named features in the database.'

    def handle(self, *features, **options):
        for name in features:
            try:
                feature = Feature.objects.get(name=name)
            except Feature.DoesNotExist:
                print "Feature %s is not in the database." % name
                return
            else:
                if feature.enabled:
                    print "Feature %s is already enabled." % feature
                else:
                    feature.enable()
                    feature.save()
                    print "Enabled feature %s." % feature

########NEW FILE########
__FILENAME__ = features
from django.core.management.base import BaseCommand

from featureflipper.models import Feature


class Command(BaseCommand):
    args = ''
    help = 'Lists each feature defined in the database, and its status.'

    def handle(self, *args, **options):
        for feature in Feature.objects.all():
            print "%s is %s" % (feature.name, feature.status)

########NEW FILE########
__FILENAME__ = loadfeatures
from django.core.management.base import BaseCommand
from django.utils import simplejson
from django.conf import settings

from featureflipper.models import Feature

import os

class Command(BaseCommand):

    def handle(self, file='', *args, **options):
        help = 'Loads the features from the file, or the default if none is provided.'
        if file == '':
            if hasattr(settings, 'FEATURE_FLIPPER_FEATURES_FILE'):
                file = settings.FEATURE_FLIPPER_FEATURES_FILE
            else:
                print "settings.FEATURE_FLIPPER_FEATURES_FILE is not set."
                return

        verbosity = int(options.get('verbosity', 1))

        stream = open(file)
        features = simplejson.load(stream)
        for json_feature in features:
            name = json_feature['name']
            try:
                feature = Feature.objects.get(name=name)
            except Feature.DoesNotExist:
                feature = Feature()
            feature.name = name
            feature.description = json_feature['description']
             # Django will convert to a boolean for us
            feature.enabled = json_feature['enabled']
            feature.save()

        if verbosity > 0:
            print "Loaded %d features." % len(features)

########NEW FILE########
__FILENAME__ = middleware
from django.conf import settings

from featureflipper.models import Feature
from featureflipper.signals import feature_defaulted
from featureflipper import FeatureProvider

import re

# Per-request flipper in URL
_REQUEST_ENABLE = re.compile("^enable_(?P<feature>\w+)$")

# Per-session flipper in URL
_SESSION_ENABLE = re.compile("^session_enable_(?P<feature>\w+)$")

# Flipper we put in the session
_FEATURE_STATUS = re.compile("^feature_status_(?P<feature>\w+)$")


class FeaturesMiddleware(object):

    def process_request(self, request):
        panel = FeaturesPanel()
        panel.add('site', list(self.features_from_database(request)))

        for plugin in FeatureProvider.plugins:
            panel.add(plugin.source, list(plugin.features(request)))

        if getattr(settings, 'FEATURE_FLIPPER_ANONYMOUS_URL_FLIPPING', False) or \
                request.user.has_perm('featureflipper.can_flip_with_url'):
            if 'session_clear_features' in request.GET:
                self.clear_features_from_session(request.session)
            for feature in dict(self.session_features_from_url(request)):
                self.add_feature_to_session(request.session, feature)

        panel.add('session', list(self.features_from_session(request)))
        panel.add('url', list(self.features_from_url(request)))

        request.features = FeatureDict(panel.states())
        request.features_panel = panel

        return None

    def features_from_database(self, request):
        """Provides an iterator yielding tuples (feature name, True/False)"""
        for feature in Feature.objects.all():
            yield (feature.name, feature.enabled)

    def features_from_session(self, request):
        """Provides an iterator yielding tuples (feature name, True/False)"""
        for key in request.session.keys():
            m = re.match(_FEATURE_STATUS, key)
            if m:
                feature = m.groupdict()['feature']
                if request.session[key] == 'enabled':
                    yield (feature, True)
                else: # We'll assume it's disabled
                    yield (feature, False)

    def features_from_url(self, request):
        """Provides an iterator yielding tuples (feature name, True/False)"""
        for parameter in request.GET:
            m = re.match(_REQUEST_ENABLE, parameter)
            if m:
                yield (m.groupdict()['feature'], True)

    def session_features_from_url(self, request):
        """Provides an iterator yielding tuples (feature name, True/False)"""
        for parameter in request.GET:
            m = re.match(_SESSION_ENABLE, parameter)
            if m:
                feature = m.groupdict()['feature']
                yield (feature, True)

    def add_feature_to_session(self, session, feature):
        session["feature_status_" + feature] = 'enabled'

    def clear_features_from_session(self, session):
        for key in session.keys():
            if re.match(_FEATURE_STATUS, key):
                del session[key]


class FeatureDict(dict):

    def __getitem__(self, key):
        if key in self:
            return dict.__getitem__(self, key)
        else:
            feature_defaulted.send(sender=self, feature=key)
            return False

class FeaturesPanel():

    def __init__(self):
        self.features = {}
        self.sources = []

    def add(self, source, features):
        self.sources.append((source, features))
        for (feature, enabled) in features:
            self.features[feature] = {'enabled': enabled, 'source': source}

    def enabled(self, name):
        return self.features[name]['enabled']

    def source(self, name):
        return self.features[name]['source']

    def states(self):
        # Returns a dictionary, mapping each feature name to its (final) state.
        return dict([(x, y['enabled']) for x, y in self.features.items()])

########NEW FILE########
__FILENAME__ = models
from django.db import models


class Feature(models.Model):
    name = models.CharField(max_length=40, db_index=True, unique=True,
        help_text="Required. Used in templates (eg {% feature search %}) and URL parameters.")
    description = models.TextField(max_length=400, blank=True)
    enabled = models.BooleanField(default=False)

    def enable(self):
        self.enabled = True

    def disable(self):
        self.enabled = False

    def flip(self):
        self.enabled = not self.enabled

    def __unicode__(self):
        return self.name

    class Meta:
        ordering = ['name']
        permissions = (
            ("can_flip_with_url", "Can flip features using URL parameters"),
        )
    
    @property
    def status(self):
        return "enabled" if self.enabled else "disabled"

########NEW FILE########
__FILENAME__ = signals
from django.dispatch import Signal

feature_defaulted = Signal(providing_args=["feature"])

########NEW FILE########
__FILENAME__ = feature_tag
from django import template
from django.template import NodeList

from featureflipper.models import Feature


register = template.Library()


@register.tag
def feature(parser, token):

    try:
        tag_name, feature = token.split_contents()
    except ValueError:
        raise template.TemplateSyntaxError, \
    				"%r tag requires a single argument" % token.contents.split()[0]

    end_tag = 'endfeature'
    nodelist_enabled = parser.parse(('disabled', end_tag))
    token = parser.next_token()

    if token.contents == 'disabled':
        nodelist_disabled = parser.parse((end_tag,))
        parser.delete_first_token()
    else:
        nodelist_disabled = NodeList()

    return FeatureNode(feature, nodelist_enabled, nodelist_disabled)


class FeatureNode(template.Node):

    def __init__(self, feature, nodelist_enabled, nodelist_disabled):
        self.feature = feature
        self.nodelist_enabled = nodelist_enabled
        self.nodelist_disabled = nodelist_disabled

    def render(self, context):
        if context['features'][self.feature]:
            return self.nodelist_enabled.render(context)
        else:
            return self.nodelist_disabled.render(context)

########NEW FILE########
__FILENAME__ = tests
from django.test import TestCase
from django.http import HttpRequest
from django.test.client import Client
from django.contrib.auth.models import User
from django.contrib.auth.models import Permission

from featureflipper.models import Feature
from featureflipper.middleware import FeaturesMiddleware

class featureflipperTest(TestCase):
    """
    Tests for django-feature-flipper
    """
    def test_something(self):
        feature = Feature.objects.create(name='fftestfeature')
        user = User.objects.create_user('fftestuser', '', 'password')

        c = Client()
        self.assertTrue(c.login(username='fftestuser', password='password'))

        response = c.get('/')
        self.assertTrue('features' in response.context)
        self.assertTrue('fftestfeature' in response.context['features'])
        self.assertFalse(response.context['features']['fftestfeature'])

        response = c.get('/?enable_fftestfeature')
        self.assertTrue(response.context['features']['fftestfeature'])

        response = c.get('/')
        self.assertFalse(response.context['features']['fftestfeature'])

        response = c.get('/?session_enable_fftestfeature')
        self.assertFalse(response.context['features']['fftestfeature'])

        perm = Permission.objects.get(codename='can_flip_with_url')
        user.user_permissions.add(perm)

        self.assertTrue(user.has_perm('featureflipper.can_flip_with_url'))
        response = c.get('/?session_enable_fftestfeature')

        self.assertTrue(response.context['features']['fftestfeature'])
        response = c.get('/')
        self.assertTrue(response.context['features']['fftestfeature'])

        response = c.get('/?session_clear_features')
        self.assertFalse(response.context['features']['fftestfeature'])

        feature.delete()
        user.delete()

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import *

########NEW FILE########
__FILENAME__ = views
from django.shortcuts import render_to_response
from django.http import HttpResponseRedirect, HttpResponseForbidden, Http404
from django.template import RequestContext
from django.utils.translation import ugettext, ugettext_lazy as _

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

if __name__ == "__main__":
    execute_manager(settings)

########NEW FILE########
__FILENAME__ = settings
# Django settings for the django-feature-flipper example project.

DEBUG = True
TEMPLATE_DEBUG = DEBUG
import os, sys
APP = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
PROJ_ROOT = os.path.abspath(os.path.dirname(__file__))
sys.path.append(APP)

ADMINS = (
    # ('Your Name', 'your_email@domain.com'),
)

MANAGERS = ADMINS

DATABASE_ENGINE = 'sqlite3'           # 'postgresql_psycopg2', 'postgresql', 'mysql', 'sqlite3' or 'oracle'.
DATABASE_NAME = 'dev.db'             # Or path to database file if using sqlite3.
DATABASE_USER = ''             # Not used with sqlite3.
DATABASE_PASSWORD = ''         # Not used with sqlite3.
DATABASE_HOST = ''             # Set to empty string for localhost. Not used with sqlite3.
DATABASE_PORT = ''             # Set to empty string for default. Not used with sqlite3.

# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
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

# Absolute path to the directory that holds media.
# Example: "/home/media/media.lawrence.com/"
MEDIA_ROOT = os.path.abspath(os.path.join('media'))

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash if there is a path component (optional in other cases).
# Examples: "http://media.lawrence.com", "http://example.com/media/"
MEDIA_URL = '/static/'

# URL prefix for admin media -- CSS, JavaScript and images. Make sure to use a
# trailing slash.
# Examples: "http://foo.com/media/", "/media/".
ADMIN_MEDIA_PREFIX = '/media/'

# Make this unique, and don't share it with anybody.
SECRET_KEY = 'g2_39yupn*6j4p*cg2%w643jiq-1n_annua*%i8+rq0dx9p=$n'

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.load_template_source',
    'django.template.loaders.app_directories.load_template_source',
#     'django.template.loaders.eggs.load_template_source',
)

TEMPLATE_CONTEXT_PROCESSORS = (
    'django.contrib.auth.context_processors.auth',
    'featureflipper.context_processors.features',
)

MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'featureflipper.middleware.FeaturesMiddleware',
)

ROOT_URLCONF = 'featureflipper_example.urls'

TEMPLATE_DIRS = (
    # Put strings here, like "/home/html/django_templates" or "C:/www/django/templates".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
    os.path.abspath(os.path.dirname(__file__)) + "/templates/",
)

FEATURE_FLIPPER_FEATURES_FILE = os.path.abspath(os.path.dirname(__file__)) + "/features.json"
FEATURE_FLIPPER_ANONYMOUS_URL_FLIPPING = False

INSTALLED_APPS = (
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'featureflipper'
)

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import *
from django.conf import settings
from django.contrib import admin

admin.autodiscover()

urlpatterns = patterns('',
    (r'^admin/', include(admin.site.urls)),
    (r'^$', 'featureflipper_example.views.index'),
)

########NEW FILE########
__FILENAME__ = views
from django.shortcuts import render_to_response
from django.template import RequestContext

from featureflipper.models import Feature
from featureflipper.signals import feature_defaulted


# We use the feature_defaulted signal to print a simple message
# warning that a feature has been defaulted to disabled. You might
# instead raise an exception here (to help avoid bugs in templates),
# or add the feature to the database.

def my_callback(sender, **kwargs):
        print "Feature '%s' defaulted!" % kwargs['feature']

# Uncomment the following line to enable this:
# feature_defaulted.connect(my_callback)


def index(request):
    # We'll include all the features, just so we can show all the details in the page
    feature_list = Feature.objects.all()
    # Below, we'll also include the features_panel in the context.
    # 'features' will already be added to the context by the middleware.
    return render_to_response('featureflipper_example/index.html',
        {'features_panel': request.features_panel, 'feature_list': feature_list},
        context_instance=RequestContext(request))

########NEW FILE########
