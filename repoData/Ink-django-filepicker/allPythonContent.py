__FILENAME__ = models
from django.db import models
from django import forms
import django_filepicker


class TestModel(models.Model):
    #Text field just to show how the FPFileField goes along with normal controls
    text = models.CharField(max_length=64)

    #FPFileField is a field that will render as a filepicker dragdrop widget, but
    #When accessed will provide a File-like interface (so you can do fpfile.read(), for instance)
    fpfile = django_filepicker.models.FPFileField(upload_to='uploads')


class TestModelForm(forms.ModelForm):
    class Meta:
        model = TestModel

########NEW FILE########
__FILENAME__ = tests
"""
This file demonstrates writing tests using the unittest module. These will pass
when you run "manage.py test".

Replace this with more appropriate tests for your application.
"""

from django.test import TestCase


class SimpleTest(TestCase):
    def test_basic_addition(self):
        """
        Tests that 1 + 1 always equals 2.
        """
        self.assertEqual(1 + 1, 2)

########NEW FILE########
__FILENAME__ = views
from django.shortcuts import render

import models


def home(request):
    message = None
    if request.method == "POST":
        print "POST parameters: ", request.POST
        print "Files: ", request.FILES

        #building the form - automagically turns the uploaded fpurl into a File object
        form = models.TestModelForm(request.POST, request.FILES)
        if form.is_valid():
            #Save will read the data and upload it to the location defined in TestModel
            form.save()

            #Reading the contents of the file
            fpfile = form.cleaned_data['fpfile']
            #Since we already read from it in save(), we'll want to seek to the beginning first
            fpfile.seek(0)
            print fpfile.read()

            message = "Save successful. URL for %s: %s" % (fpfile.name, request.POST['fpfile'])
        else:
            message = "Invalid form"
    else:
        form = models.TestModelForm()

    return render(request, "home.html", {'form': form, 'message': message})

########NEW FILE########
__FILENAME__ = manage
#!/usr/bin/env python
from django.core.management import execute_manager
import imp
try:
    imp.find_module('settings') # Assumed to be in the same directory.
except ImportError:
    import sys
    sys.stderr.write("Error: Can't find the file 'settings.py' in the directory containing %r. It appears you've customized things.\nYou'll have to run django-admin.py, passing it your settings module.\n" % __file__)
    sys.exit(1)

import settings

if __name__ == "__main__":
    execute_manager(settings)

########NEW FILE########
__FILENAME__ = settings
import os
import sys
#Importing base package
sys.path.append("../")

CWD = os.getcwd()

# Django settings for demo project.

DEBUG = True
TEMPLATE_DEBUG = DEBUG

ADMINS = (
    # ('Your Name', 'your_email@example.com'),
)

MANAGERS = ADMINS

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',  # Add 'postgresql_psycopg2', 'postgresql', 'mysql', 'sqlite3' or 'oracle'.
        'NAME': 'db.sql',                      # Or path to database file if using sqlite3.
        'USER': '',                      # Not used with sqlite3.
        'PASSWORD': '',                  # Not used with sqlite3.
        'HOST': '',                      # Set to empty string for localhost. Not used with sqlite3.
        'PORT': '',                      # Set to empty string for default. Not used with sqlite3.
    }
}

#Your Filepicker.io API key goes here. To get an api key, go to https://filepicker.io
FILEPICKER_API_KEY = 'REPLACE_ME'

# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
# On Unix systems, a value of None will cause Django to use the same
# timezone as the operating system.
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

# If you set this to False, Django will not format dates, numbers and
# calendars according to the current locale
USE_L10N = True

# Absolute filesystem path to the directory that will hold user-uploaded files.
# Example: "/home/media/media.lawrence.com/media/"
MEDIA_ROOT = os.path.join(CWD, 'media')

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
SECRET_KEY = 'iq0i&txhbz=yi^0zq342r%(5%a1o5v-3+idqt$m%4yj3o#*qt^'

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
    #This optional middleware takes all filepicker urls and puts the data into request.FILES
    'django_filepicker.middleware.URLFileMapperMiddleware',
)

ROOT_URLCONF = 'demo.urls'

TEMPLATE_DIRS = (
    # Put strings here, like "/home/html/django_templates" or "C:/www/django/templates".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
    os.path.join(CWD, 'templates')
)

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'filepicker_demo',
)

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

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import patterns, url

# Uncomment the next two lines to enable the admin:
# from django.contrib import admin
# admin.autodiscover()

urlpatterns = patterns('',
    # The demo page:
    url(r'^$', 'demo.filepicker_demo.views.home', name='home'),
)

########NEW FILE########
__FILENAME__ = context_processors
from django.utils.safestring import mark_safe
from .widgets import JS_URL

def js(request):
    #Defines a {{FILEPICKER_JS}} tag that inserts the filepicker javascript library
    return {"FILEPICKER_JS":
            mark_safe(u'<script src="%s"></script>' % JS_URL)}

########NEW FILE########
__FILENAME__ = forms
from django import forms
from django.core.files import File
from django.conf import settings

from .utils import FilepickerFile
from .widgets import FPFileWidget
import urllib2
try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO


class FPFieldMixin():
    widget = FPFileWidget
    default_mimetypes = "*/*"

    def initialize(self, apikey=None, mimetypes=None, services=None, additional_params=None):
        """
        Initializes the Filepicker field.
        Valid arguments:
        * apikey. This string is required if it isn't set as settings.FILEPICKER_API_KEY
        * mimetypes. Optional, the allowed mimetypes for files. Defaults to "*/*" (all files)
        * services. Optional, the allowed services to pull from.
        * additional_params. Optional, additional parameters to be applied.
        """

        self.apikey = apikey or getattr(settings, 'FILEPICKER_API_KEY', None)
        if not self.apikey:
            raise Exception("Cannot find filepicker.io api key." +
            " Be sure to either pass as the apikey argument when creating the FPFileField," +
            " or set it as settings.FILEPICKER_API_KEY. To get a key, go to https://filepicker.io")

        self.mimetypes = mimetypes or self.default_mimetypes
        if not isinstance(self.mimetypes, basestring):
            #If mimetypes is an array, form a csv string
            try:
                self.mimetypes = ",".join(iter(self.mimetypes))
            except TypeError:
                self.mimetypes = str(self.mimetypes)

        self.services = services or getattr(settings, 'FILEPICKER_SERVICES', None)
        self.additional_params = additional_params or getattr(settings, 'FILEPICKER_ADDITIONAL_PARAMS', None)

    def widget_attrs(self, widget):
        attrs = {
                'data-fp-apikey': self.apikey,
                'data-fp-mimetypes': self.mimetypes,
                }

        if self.services:
            attrs['data-fp-option-services'] = self.services

        if self.additional_params:
            attrs = dict(attrs.items() + self.additional_params.items())            

        return attrs


class FPUrlField(FPFieldMixin, forms.URLField):
    widget = FPFileWidget
    default_mimetypes = "*/*"

    def __init__(self, *args, **kwargs):
        """
        Initializes the Filepicker url field.
        Valid arguments:
        * apikey. This string is required if it isn't set as settings.FILEPICKER_API_KEY
        * mimetypes. Optional, the allowed mimetypes for files. Defaults to "*/*" (all files)
        * services. Optional, the allowed services to pull from.
        * additional_params. Optional, additional parameters to be applied.
        """
        self.initialize(
            apikey=kwargs.pop('apikey', None),
            mimetypes=kwargs.pop('mimetypes', None),
            services=kwargs.pop('services', None),
            additional_params=kwargs.pop('additional_params', None),
        )
        super(FPUrlField, self).__init__(*args, **kwargs)


class FPFileField(FPFieldMixin, forms.FileField):
    def __init__(self, *args, **kwargs):
        """
        Initializes the Filepicker url field.
        Valid arguments:
        * apikey. This string is required if it isn't set as settings.FILEPICKER_API_KEY
        * mimetypes. Optional, the allowed mimetypes for files. Defaults to "*/*" (all files)
        * services. Optional, the allowed services to pull from.
        * additional_params. Optional, additional parameters to be applied.
        """
        self.initialize(
            apikey=kwargs.pop('apikey', None),
            mimetypes=kwargs.pop('mimetypes', None),
            services=kwargs.pop('services', None),
            additional_params=kwargs.pop('additional_params', None),
        )
        super(FPFileField, self).__init__(*args, **kwargs)

    def to_python(self, data):
        """Takes the url in data and creates a File object"""
        try:
            fpf = FilepickerFile(data)
        except ValueError, e:
            if 'Not a filepicker.io URL' in str(e):
                # Return None for invalid URLs
                return None
            else:
                # Pass the buck
                raise e
        else:
            return fpf.get_file(self.additional_params)

########NEW FILE########
__FILENAME__ = middleware
from .utils import FilepickerFile


class URLFileMapperMiddleware(object):
    """
    This middleware will take any Filepicker.io urls that are posted to the server via a POST
    and put a matching File object into request.FILES. This way, if you're used to grabbing files out of
    request.FILES, you don't have to change your backend code when using the filepicker.io widgets.

    This middleware is rather agressive in that it will automatically fetch any and all filepicker
    urls passed to the server, so if you are already processing the files via FPFileField or similar
    this functionality is redundant

    Note that the original filepicker.io url will still be available in POST if you need it.
    """
    def process_request(self, request):
        #Iterate over GET or POST data, search for filepicker.io urls
        for key, val in request.POST.items():
            try:
                fp = FilepickerFile(val)
            except ValueError:
                pass
            else:
                splits = val.split(",")
                for url in splits:
                    if key in request.FILES:
                        request.FILES.setlist(key, list(
                            request.FILES.getlist(key) + [fp.get_file()]))
                    else:
                        request.FILES[key] = fp.get_file()

########NEW FILE########
__FILENAME__ = models
from django.db import models
from django.utils.translation import ugettext_lazy

import forms


class FPFileField(models.FileField):
    description = ugettext_lazy("A File selected using Filepicker.io")

    def __init__(self, *args, **kwargs):
        """
        Initializes the Filepicker file field.
        Valid arguments:
        * apikey. This string is required if it isn't set as settings.FILEPICKER_API_KEY
        * mimetypes. Optional, the allowed mimetypes for files. Defaults to "*/*" (all files)
        * services. Optional, the allowed services to pull from.
        * additional_params. Optional, additional parameters to be applied.
        """
        self.apikey = kwargs.pop("apikey", None)
        self.mimetypes = kwargs.pop("mimetypes", None)
        self.services = kwargs.pop("services", None)
        self.additional_params=kwargs.pop("additional_params", None)

        super(FPFileField, self).__init__(*args, **kwargs)

    def formfield(self, **kwargs):
        defaults = {'form_class': forms.FPFileField,
                'max_length': self.max_length}

        if 'initial' in kwargs:
            defaults['required'] = False

        if self.apikey:
            defaults['apikey'] = self.apikey
        if self.mimetypes:
            defaults['mimetypes'] = self.mimetypes
        if self.services:
            defaults['services'] = self.services
        if self.additional_params:
            defaults['additional_params'] = self.additional_params

        defaults.update(kwargs)
        return super(FPFileField, self).formfield(**defaults)
        
try:
    # For South. See: http://south.readthedocs.org/en/latest/customfields.html#extending-introspection
    from south.modelsinspector import add_introspection_rules
    add_introspection_rules([], ["django_filepicker\.models\.FPFileField"])
except ImportError:
    pass

########NEW FILE########
__FILENAME__ = utils
import re
import urllib
import os

from django.core.files import File


class FilepickerFile(File):
    filepicker_url_regex = re.compile(
            r'https?:\/\/www.filepicker.io\/api\/file\/.*')

    def __init__(self, url):
        if not self.filepicker_url_regex.match(url):
            raise ValueError('Not a filepicker.io URL: %s' % url)
        self.url = url

    def get_file(self, additional_params={}):
        '''
        Downloads the file from filepicker.io and returns a
        Django File wrapper object.
        additional_params should include key/values such as:
        {
          'data-fp-signature': HEXDIGEST,
          'data-fp-policy': HEXDIGEST,
        }
        (in other words, parameters should look like additional_params
        of the models)
        '''
        # clean up any old downloads that are still hanging around
        self.cleanup()

        # Fetch any fields possibly required for fetching files for reading.
        query_params = {}
        for field in ('policy','signature'):
            longfield = 'data-fp-{0}'.format(field)
            if longfield in additional_params:
                query_params[field] = additional_params[longfield]
        # Append the fields as GET query parameters to the URL in data.
        query_params = urllib.urlencode(query_params)
        url = self.url
        if query_params:
            url = url + '?' + query_params

        # The temporary file will be created in a directory set by the
        # environment (TEMP_DIR, TEMP or TMP)
        self.filename, header = urllib.urlretrieve(url)
        name = os.path.basename(self.filename)
        disposition = header.get('Content-Disposition')
        if disposition:
            name = disposition.rpartition("filename=")[2].strip('" ')
        filename = header.get('X-File-Name')
        if filename:
            name = filename

        tempfile = open(self.filename, 'r')
        # initialize File components of this object
        super(FilepickerFile, self).__init__(tempfile,name=name)
        return self

    def cleanup(self):
        '''
        Removes any downloaded objects and closes open files.
        '''
        # self.file comes from Django File
        if hasattr(self, 'file'):
            if not self.file.closed:
                self.file.close()
            delattr(self, 'file')

        if hasattr(self, 'filename'):
            # the file might have been moved in the meantime so
            # check first
            if os.path.exists(self.filename):
                os.remove(self.filename)
            delattr(self, 'filename')

    def __enter__(self):
        '''
        Allow FilepickerFile to be used as a context manager as such:

            with FilepickerFile(url) as f:
                model.field.save(f.name, f.)
        '''
        self.get_file()
        # call Django's File context manager
        return super(FilepickerFile, self).__enter__()

    def __exit__(self, *args):
        # call Django's File context manager
        super(FilepickerFile, self).__exit__(*args)
        self.cleanup()

    def __del__(self):
        self.cleanup()

########NEW FILE########
__FILENAME__ = widgets
from django.conf import settings
from django.forms import widgets

#JS_URL is the url to the filepicker.io javascript library
JS_VERSION = getattr(settings, "FILEPICKER_JS_VERSION", 1)
JS_URL = "//api.filepicker.io/v%d/filepicker.js" % (JS_VERSION)

INPUT_TYPE = getattr(settings, "FILEPICKER_INPUT_TYPE", "filepicker-dragdrop")

class FPFileWidget(widgets.Input):
    input_type = INPUT_TYPE
    needs_multipart_form = False

    def value_from_datadict_old(self, data, files, name):
        #If we are using the middleware, then the data will already be
        #in FILES, if not it will be in POST
        if name not in data:
            return super(FPFileWidget, self).value_from_datadict(
                    data, files, name)

        return data

    class Media:
        js = (JS_URL,)

########NEW FILE########
