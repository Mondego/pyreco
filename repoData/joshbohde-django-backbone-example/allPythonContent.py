__FILENAME__ = local_settings


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
# Django settings for backbone_example project.
import os

PROJECT_ROOT = os.path.dirname(__file__)

DEBUG = True
TEMPLATE_DEBUG = DEBUG

ADMINS = (
    # ('Your Name', 'your_email@domain.com'),
)

MANAGERS = ADMINS

DATABASE_ENGINE = 'sqlite3'           # 'postgresql_psycopg2', 'postgresql', 'mysql', 'sqlite3' or 'oracle'.
DATABASE_NAME = '/tmp/backbone_example.db'             # Or path to database file if using sqlite3.
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
MEDIA_ROOT = os.path.join(PROJECT_ROOT,'media')
STATIC_ROOT = os.path.join(PROJECT_ROOT, 'collected_static')
STATICFILES_DIRS = (
    os.path.join(PROJECT_ROOT, 'static'),
)

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash if there is a path component (optional in other cases).
# Examples: "http://media.lawrence.com", "http://example.com/media/"
MEDIA_URL = '/media/'

STATIC_URL = "/static/"

# URL prefix for admin media -- CSS, JavaScript and images. Make sure to use a
# trailing slash.
# Examples: "http://foo.com/media/", "/media/".
ADMIN_MEDIA_PREFIX = '/media/admin/'

# Make this unique, and don't share it with anybody.
SECRET_KEY = '637i_o@27q89j^-gm+i!5g4#&pwo%)^^m&2g@4o^a8f92l#klq'

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.load_template_source',
    'django.template.loaders.app_directories.load_template_source',
#     'django.template.loaders.eggs.load_template_source',
)

MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
)

ROOT_URLCONF = 'backbone_example.urls'

TEMPLATE_DIRS = (
  os.path.join(PROJECT_ROOT, "templates"),
)

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.staticfiles',

    'tweets',
)

########NEW FILE########
__FILENAME__ = api
from tastypie.api import Api
from resources import TweetResource

v1 = Api("v1")
v1.register(TweetResource())

########NEW FILE########
__FILENAME__ = resources
from tastypie.resources import ModelResource
from tastypie.authorization import Authorization

from tweets.models import Tweet

class TweetResource(ModelResource):
    class Meta:
        queryset = Tweet.objects.all()
        authorization = Authorization()
        list_allowed_methods = ['get', 'post']
        detail_allowed_methods = ['get']

########NEW FILE########
__FILENAME__ = models
from django.db import models

class Tweet(models.Model):
    message = models.CharField(max_length=140)
    timestamp = models.DateTimeField(auto_now_add=True)

########NEW FILE########
__FILENAME__ = mustache
from django import template
from django.conf import settings
import pystache

register = template.Library()

class View(pystache.View):
    template_path = settings.TEMPLATE_DIRS[0]

    def __init__(self, template_name, context):
        self.template_name = template_name
        return super(View, self).__init__(context=context)

class MustacheNode(template.Node):
    def __init__(self, template_path, attr=None):
        self.template = template_path
        self.attr = attr

    def render(self, context):
        mcontext = context[self.attr] if self.attr else {}
        view = View(self.template, context=mcontext)
        return view.render()

def do_mustache(parser, token):
    """
    Loads a mustache template and render it inline
    
    Example::
    
    {% mustache "foo/bar" data %}
    
    """
    bits = token.split_contents()
    if len(bits) not in  [2,3]:
        raise template.TemplateSyntaxError("%r tag takes two arguments: the location of the template file, and the template context" % bits[0])
    path = bits[1]
    path = path[1:-1]
    attrs = bits[2:]
    return MustacheNode(path, *attrs)


register.tag("mustache", do_mustache)

########NEW FILE########
__FILENAME__ = straight_include
"""
Straight Include template tag by @HenrikJoreteg

Django templates don't give us any way to escape template tags.

So if you ever need to include client side templates for ICanHaz.js (or anything else that
may confuse django's templating engine) You can is this little snippet.

Just use it as you would a normal {% include %} tag. It just won't process the included text.

It assumes your included templates are in you django templates directory.

Usage:

{% load straight_include %}

{% straight_include "my_icanhaz_templates.html" %}

"""

from django import template
from django.conf import settings


register = template.Library()


class StraightIncludeNode(template.Node):
    def __init__(self, template_path):
        self.filepath = '%s/%s' % (settings.TEMPLATE_DIRS[0], template_path)

    def render(self, context):
        fp = open(self.filepath, 'r')
        output = fp.read()
        fp.close()
        return output


def do_straight_include(parser, token):
    """
    Loads a template and includes it without processing it
    
    Example::
    
    {% straight_include "foo/some_include" %}
    
    """
    bits = token.split_contents()
    if len(bits) != 2:
        raise template.TemplateSyntaxError("%r tag takes one argument: the location of the file within the template folder" % bits[0])
    path = bits[1][1:-1]
    
    return StraightIncludeNode(path)


register.tag("straight_include", do_straight_include)
########NEW FILE########
__FILENAME__ = verbatim
"""
From ericflo (https://gist.github.com/629508)

jQuery templates use constructs like:

    {{if condition}} print something{{/if}}

This, of course, completely screws up Django templates,
because Django thinks {{ and }} mean something.

Wrap {% verbatim %} and {% endverbatim %} around those
blocks of jQuery templates and this will try its best
to output the contents with no changes.
"""

from django import template

register = template.Library()


class VerbatimNode(template.Node):

    def __init__(self, text):
        self.text = text
    
    def render(self, context):
        return self.text


@register.tag
def verbatim(parser, token):
    text = []
    while 1:
        token = parser.tokens.pop(0)
        if token.contents == 'endverbatim':
            break
        if token.token_type == template.TOKEN_VAR:
            text.append('{{')
        elif token.token_type == template.TOKEN_BLOCK:
            text.append('{%')
        text.append(token.contents)
        if token.token_type == template.TOKEN_VAR:
            text.append('}}')
        elif token.token_type == template.TOKEN_BLOCK:
            text.append('%}')
    return VerbatimNode(''.join(text))

########NEW FILE########
__FILENAME__ = gravatar
from unittest import TestCase

from tweets.utils import gravatar

class TestGravatar(TestCase):
    def testSampleData(self):
        """Basic sanity check from http://en.gravatar.com/site/implement/hash/"""
        
        self.assertEqual(gravatar('MyEmailAddress@example.com '),
                         '0bc83cb571cd1c50ba6f3e8a78ef1346')
                       

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import patterns, url, include
from tweets.api import v1

from .views import IndexView, DetailView

urlpatterns = patterns('',
    url(r'^$',
        IndexView.as_view(),
        name='index'),

    url(r'^(?P<pk>\d+)/$',
        DetailView.as_view(),
        name="detail"),

    url(r'^api/', include(v1.urls)),
)



########NEW FILE########
__FILENAME__ = views
from django.views.generic.base import TemplateView
from django.http import Http404

from api import v1
from .models import Tweet

class IndexView(TemplateView):
    template_name = 'index.html'


class DetailView(TemplateView):
    template_name = 'index.html'

    def get_detail(self, pk):
        tr = v1.canonical_resource_for('tweet')

        try:
            tweet = tr.cached_obj_get(pk=pk)
        except Tweet.DoesNotExist:
            raise Http404

        bundle = tr.full_dehydrate(tr.build_bundle(obj=tweet))
        data = bundle.data
        return data

    def get_context_data(self, **kwargs):
        base = super(DetailView, self).get_context_data(**kwargs)
        base['data'] = self.get_detail(base['params']['pk'])
        return base

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import *

# Uncomment the next two lines to enable the admin:
# from django.contrib import admin
# admin.autodiscover()

urlpatterns = patterns('',
    (r'', include('tweets.urls')),

    # Uncomment the admin/doc line below and add 'django.contrib.admindocs' 
    # to INSTALLED_APPS to enable admin documentation:
    # (r'^admin/doc/', include('django.contrib.admindocs.urls')),

    # Uncomment the next line to enable the admin:
    # (r'^admin/', include(admin.site.urls)),
)


from django.contrib.staticfiles.urls import staticfiles_urlpatterns
urlpatterns += staticfiles_urlpatterns()

########NEW FILE########
