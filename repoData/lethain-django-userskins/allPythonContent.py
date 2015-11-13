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
# Django settings for dev_userskins project.
import os
ROOT_PATH = os.path.dirname(__file__)

USERSKINS_DEFAULT = "light"
USERSKINS_DETAILS = {
    'light':'light.css',
    'dark':'dark.css',
}
USERSKINS_USE_COMPRESS_GROUPS = False   # optional, defaults to False
USERSKINS_NEVER_ACCESS_DATABASE = False  # optional, defaults to False

TEMPLATE_CONTEXT_PROCESSORS = (
    "django.core.context_processors.auth",
    "django.core.context_processors.debug",
    "django.core.context_processors.i18n",
    "django.core.context_processors.media",
    "userskins.context.userskins",
    )


DEBUG = True
TEMPLATE_DEBUG = DEBUG

ADMINS = (
    # ('Your Name', 'your_email@domain.com'),
)

MANAGERS = ADMINS

DATABASE_ENGINE = 'sqlite3'           # 'postgresql_psycopg2', 'postgresql', 'mysql', 'sqlite3' or 'oracle'.
DATABASE_NAME = os.path.join(ROOT_PATH, 'userskins.sqlite')
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
MEDIA_ROOT = os.path.join(ROOT_PATH, "media")

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash if there is a path component (optional in other cases).
# Examples: "http://media.lawrence.com", "http://example.com/media/"
MEDIA_URL = 'http://127.0.0.1:8000/media/'

# URL prefix for admin media -- CSS, JavaScript and images. Make sure to use a
# trailing slash.
# Examples: "http://foo.com/media/", "/media/".
ADMIN_MEDIA_PREFIX = '/media/admin/'

# Make this unique, and don't share it with anybody.
SECRET_KEY = '-!t5e+sem5iibu2u#!gygfg$ctqo$kama^-dg^((ju6%vly4-f'

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
    'userskins.middleware.UserskinsMiddleware',
)

ROOT_URLCONF = 'dev_userskins.urls'

TEMPLATE_DIRS = (
    # Put strings here, like "/home/html/django_templates" or "C:/www/django/templates".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
    os.path.join(ROOT_PATH, "templates")
)

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'userskins',
)

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import *
from django.template import RequestContext
from django.http import HttpResponseRedirect
from django.conf import settings

# Uncomment the next two lines to enable the admin:
# from django.contrib import admin
# admin.autodiscover()

def dark(request):
    hrr = HttpResponseRedirect("/")
    hrr.set_cookie("userskins", "dark")
    return hrr

def light(request):
    hrr = HttpResponseRedirect("/")
    hrr.set_cookie("userskins", "light")
    return hrr

urlpatterns = patterns(
    '',
    (r'^media/(?P<path>.*)$', 'django.views.static.serve', {'document_root': settings.MEDIA_ROOT }),
    (r'^$','django.views.generic.simple.direct_to_template',
     {'template':'dev_index.html'}),
    (r'^dark/$',dark),
    (r'^light/$',light),
)

########NEW FILE########
__FILENAME__ = context
from userskins.models import SkinPreference
from django.conf import settings


def userskins(request):
    skin = settings.USERSKINS_DEFAULT
    if request.COOKIES.has_key("userskins"):
        skin = request.COOKIES["userskins"]
    if getattr(settings,"USERSKINS_USE_COMPRESS_GROUPS",False):
        return {"userskins_skin": skin, "userskins_use_compress":True }
    else:
        skin_uri = u"%s%s" % (settings.MEDIA_URL, settings.USERSKINS_DETAILS[skin])
        return {"userskins_skin": skin_uri, "userskins_use_compress":False }

########NEW FILE########
__FILENAME__ = middleware
from django.conf import settings
from userskins.models import SkinPreference
import django


class UserskinsMiddleware(object):
    def __init__(self):
        never_use_database = getattr(settings,"USERSKINS_NEVER_ACCESS_DATABASE", False)
        if never_use_database:
            raise django.core.exceptions.MiddlewareNotUsed
        else:
            self.default = settings.USERSKINS_DEFAULT


    def process_response(self, request, response):
        if not request.COOKIES.has_key("userskins"):
            skin = self.default
            if request.user.is_authenticated():
                try:
                    skin = SkinPreference.objects.get(user=request.user).skin
                except SkinPreference.DoesNotExist:
                    pass
            response.set_cookie("userskins", skin)
        return response

########NEW FILE########
__FILENAME__ = models
from django.db import models
from django.contrib.auth.models import User

class SkinPreference(models.Model):
    user = models.ForeignKey(User)
    skin = models.CharField(max_length=20)

########NEW FILE########
__FILENAME__ = userskins

from django import template
try:
    from compress.templatetags import compressed
except ImportError:
    compressed = None

register = template.Library()


@register.tag
def userskin(parser, token):
    return UserskinNode()

class UserskinNode(template.Node):
    def render(self, context):
        skin = template.Variable("userskins_skin").resolve(context)
        use_compress = template.Variable("userskins_use_compress").resolve(context)
        if use_compress:
            node = compressed.CompressedCSSNode(skin)
            return node.render({skin:skin})
            
        else:
            return u'<link rel="stylesheet" href="%s">' % skin

########NEW FILE########
__FILENAME__ = views
# Create your views here.

########NEW FILE########
