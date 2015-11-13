__FILENAME__ = admin
from django.contrib import admin
from social_bookmarking.models import Bookmark

class BookmarkAdmin(admin.ModelAdmin):
    list_display    = ('title', 'status')
    list_filter     = ('title', 'status')
    search_fields   = ('title', 'status')
    list_editable   = ('status',)

admin.site.register(Bookmark, BookmarkAdmin)


########NEW FILE########
__FILENAME__ = models
from django.db import models

STATUS_CHOICES = (
    (1, 'Inactive'),
    (2, 'Active'),
)

url_help = """
Not a formal URL field. This accepts a string which will have string formatting operations performed on it. Valid key 
mappings for the string formatting includes:
<ul>
  <li><strong>%(url)s</strong> Url to be provided to social bookmarking service</li>
  <li><strong>%(title)s</strong> Title of object being submitted to social bookmarking service</li>  
  <li><strong>%(description)s</strong> Summary or description of the object being submitted</li>    
</ul>
"""

image_help = """
Bookmark image icon stored in media/social_bookmarking/img folder. Stored there so easier to install with fixtures."
"""

js_help = """
Javascript placed here will be inserted in the page in a <script></script> body. Lines will be stripped so make sure that 
you end your lines of code correctly.
"""

class Bookmark(models.Model):
    title           = models.CharField(max_length=255, blank=False)
    status          = models.IntegerField(choices=STATUS_CHOICES, default=2)    
    description     = models.CharField(max_length=255, blank=True, help_text="Because some things want it")
    url             = models.CharField(blank=False, max_length=255, help_text=url_help)
    image           = models.CharField(help_text=image_help, max_length=100, blank=False)
    js              = models.TextField(help_text=js_help, blank=True)
    
    class Meta:
        ordering = ('title',)

    def __unicode__(self):
        return unicode(self.title)
########NEW FILE########
__FILENAME__ = social_bookmarking_tags
import urlparse

from django.template import Library
from django.utils.http import urlquote

from social_bookmarking.models import Bookmark

register = Library()

class NoRequestContextProcessorFound(Exception):
    pass

@register.inclusion_tag('social_bookmarking/links.html', takes_context=True)
def show_bookmarks(context, title, object_or_url, description=""):
    """ Displays the bookmarks
        TODO: Add in the javascript cleanup part
    """

    if hasattr(object_or_url, 'get_absolute_url'):
        url = getattr(object_or_url, 'get_absolute_url')()

    url = unicode(object_or_url)
    
    if not url.startswith('http'):
        url = context['request'].build_absolute_uri(url)

    # TODO: Bookmark should have a .active manager:
    bookmarks = Bookmark.objects.filter(status=2).values()

    for bookmark in bookmarks:
        bookmark['description'] = description
        bookmark['link'] = bookmark['url'] % {'title': urlquote(title),
                                        'url': urlquote(url),
                                        'description': urlquote(description)
                                       }


    return {'bookmarks':bookmarks, 'MEDIA_URL': context['MEDIA_URL']}


########NEW FILE########
__FILENAME__ = tests
from django.conf import settings
from django.contrib.auth.models import User
from django.template import Context, Template
from django.template.loader import get_template_from_string
from django.test import TestCase


class TestBookmarks(TestCase):
    fixtures = ['bookmarks.json',]
    
    def setUp(self):
        
        self.user = User(username="bookmark_user")
        self.user.save()
        
        self.google_test = """<a href="http://www.google.com/bookmarks/mark?op=edit&amp;bkmk=http%3A//python.org&amp;title=bookmark_user" title="Google" rel="nofollow">"""
        
        self.print_test = """<a href="javascript:window.print();" title="Print" rel="nofollow">"""

    
    def tearDown(self):
        pass
    
    def test_template_tag(self):
        """ Does the template tag work without blowing up? """
        
        template = get_template_from_string("""
            {% load social_bookmarking_tags %}
            
            {% show_bookmarks object.username 'http://python.org' %}
        """)
        
        c = Context({'object':self.user, 'MEDIA_URL':settings.MEDIA_URL})
        html = template.render(c)
        self.assertTrue(self.google_test in html)
        self.assertTrue(self.print_test in html)        
########NEW FILE########
__FILENAME__ = manage
#!/usr/bin/env python

import sys


from django.core.management import execute_manager
from django.core.management import setup_environ, execute_from_command_line

try:
    import settings # Assumed to be in the same directory.
except ImportError:
    sys.stderr.write("Error: Can't find the file 'settings.py' in the directory containing %r. It appears you've customized things.\nYou'll have to run django-admin.py, passing it your settings module.\n(If the file settings.py does indeed exist, it's causing an ImportError somehow.)\n" % __file__)
    sys.exit(1)
    
sys.path.insert(0, settings.PROJECT_ROOT)    


setup_environ(settings)

if __name__ == "__main__":
    execute_from_command_line()

########NEW FILE########
__FILENAME__ = settings
# Django settings for test_project project.

import os.path

from os.path import join, abspath, dirname
PROJECT_ROOT = abspath(dirname(__file__))
PROJECT_ROOT = PROJECT_ROOT.replace('social_bookmarking/test_project','')


DEBUG = True
TEMPLATE_DEBUG = DEBUG

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
MEDIA_ROOT = PROJECT_ROOT + '/media/'

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash if there is a path component (optional in other cases).
# Examples: "http://media.lawrence.com", "http://example.com/media/"
MEDIA_URL = '/media/'

# URL prefix for admin media -- CSS, JavaScript and images. Make sure to use a
# trailing slash.
# Examples: "http://foo.com/media/", "/media/".
ADMIN_MEDIA_PREFIX = '/media/'

# Make this unique, and don't share it with anybody.
SECRET_KEY = 'towk(yx^x3ydpj&ifv&f07lil+g9wld5x48o=i(fo_9sf@1=%6'

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.load_template_source',
    'django.template.loaders.app_directories.load_template_source',
#     'django.template.loaders.eggs.load_template_source',

)

TEMPLATE_CONTEXT_PROCESSORS = (
    'django.core.context_processors.auth',
    'django.core.context_processors.debug',
    'django.core.context_processors.i18n',
    'django.core.context_processors.media',
    'django.core.context_processors.request',
)

MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
)

ROOT_URLCONF = 'test_project.urls'

TEMPLATE_DIRS = (
    # Put strings here, like "/home/html/django_templates" or "C:/www/django/templates".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
    os.path.join(PROJECT_ROOT, "social_bookmarking", "media", "social_bookmarking"),    
)

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.admin',    
    'test_app',
    'social_bookmarking'
)

########NEW FILE########
__FILENAME__ = models
from django.db import models

# Create your models here.

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import *



urlpatterns = patterns('',
    url(r'^$', "test_app.views.index", name='index'),    

    
    )
########NEW FILE########
__FILENAME__ = views
# Create your views here.
from django.shortcuts import render_to_response
from django.template import RequestContext


def index(request):
    
    return render_to_response('test_app/index.html', {
    }, context_instance=RequestContext(request))    

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import *

from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns('',
    (r'^admin/(.*)', admin.site.root),    

    (r'^', include('test_app.urls')),



)

########NEW FILE########
__FILENAME__ = urls

########NEW FILE########
__FILENAME__ = views

########NEW FILE########
