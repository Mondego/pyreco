__FILENAME__ = secure_db
#!/usr/bin/env python
import hashlib, imp, os, sqlite3

# Load the OpenShift helper library
lib_path      = os.environ['OPENSHIFT_REPO_DIR'] + 'wsgi/openshift/'
modinfo       = imp.find_module('openshiftlibs', [lib_path])
openshiftlibs = imp.load_module('openshiftlibs', modinfo[0], modinfo[1], modinfo[2])

# Open the database
conn = sqlite3.connect(os.environ['OPENSHIFT_DATA_DIR'] + '/sqlite3.db')
c    = conn.cursor()

# Grab the default security info
c.execute('SELECT password FROM AUTH_USER WHERE id = 1')
pw_info = c.fetchone()[0]

# The password is stored as [hashtype]$[salt]$[hashed]
pw_fields = pw_info.split("$")
hashtype  = pw_fields[0]
old_salt  = pw_fields[1]
old_pass  = pw_fields[2]

# Randomly generate a new password and a new salt
# The PASSWORD value below just sets the length (12)
# for the real new password.
old_keys = { 'SALT': old_salt, 'PASS': '123456789ABC' }
use_keys = openshiftlibs.openshift_secure(old_keys)

# Encrypt the new password
new_salt    = use_keys['SALT']
new_pass    = use_keys['PASS']
new_hashed  = hashlib.sha1(new_salt + new_pass).hexdigest()
new_pw_info = "$".join([hashtype,new_salt,new_hashed])

# Update the database
c.execute('UPDATE AUTH_USER SET password = ? WHERE id = 1', [new_pw_info])
conn.commit()
c.close()
conn.close()

# Print the new password info
print "Django application credentials:\n\tuser: admin\n\t" + new_pass

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
__FILENAME__ = openshiftlibs
#!/usr/bin/env python
import hashlib, inspect, os, random, sys

# Gets the secret token provided by OpenShift
# or generates one (this is slightly less secure, but good enough for now)
def get_openshift_secret_token():
    token = os.getenv('OPENSHIFT_SECRET_TOKEN')
    name  = os.getenv('OPENSHIFT_APP_NAME')
    uuid  = os.getenv('OPENSHIFT_APP_UUID')
    if token is not None:
        return token
    elif (name is not None and uuid is not None):
        return hashlib.sha256(name + '-' + uuid).hexdigest()
    return None

# Loop through all provided variables and generate secure versions
# If not running on OpenShift, returns defaults and logs an error message
#
# This function calls secure_function and passes an array of:
#  {
#    'hash':     generated sha hash,
#    'variable': name of variable,
#    'original': original value
#  }
def openshift_secure(default_keys, secure_function = 'make_secure_key'):
    # Attempts to get secret token
    my_token = get_openshift_secret_token()

    # Only generate random values if on OpenShift
    my_list  = default_keys

    if my_token is not None:
        # Loop over each default_key and set the new value
        for key, value in default_keys.iteritems():
            # Create hash out of token and this key's name
            sha = hashlib.sha256(my_token + '-' + key).hexdigest()
            # Pass a dictionary so we can add stuff without breaking existing calls
            vals = { 'hash': sha, 'variable': key, 'original': value }
            # Call user specified function or just return hash
            my_list[key] = sha
            if secure_function is not None:
                # Pick through the global and local scopes to find the function.
                possibles = globals().copy()
                possibles.update(locals())
                supplied_function = possibles.get(secure_function)
                if not supplied_function:
                    raise Exception("Cannot find supplied security function")
                else:
                    my_list[key] = supplied_function(vals)
    else:
        calling_file = inspect.stack()[1][1]
        if os.getenv('OPENSHIFT_REPO_DIR'):
            base = os.getenv('OPENSHIFT_REPO_DIR')
            calling_file.replace(base,'')
        sys.stderr.write("OPENSHIFT WARNING: Using default values for secure variables, please manually modify in " + calling_file + "\n")

    return my_list


# This function transforms default keys into per-deployment random keys;
def make_secure_key(key_info):
	hashcode = key_info['hash']
	key      = key_info['variable']
	original = key_info['original']

	# These are the legal password characters
	# as per the Django source code
	# (django/contrib/auth/models.py)
	chars  = 'abcdefghjkmnpqrstuvwxyz'
	chars += 'ABCDEFGHJKLMNPQRSTUVWXYZ'
	chars += '23456789'

	# Use the hash to seed the RNG
	random.seed(int("0x" + hashcode[:8], 0))

	# Create a random string the same length as the default
	rand_key = ''
	for _ in range(len(original)):
		rand_pos = random.randint(0,len(chars))
		rand_key += chars[rand_pos:(rand_pos+1)]

	# Reset the RNG
	random.seed()

	# Set the value
	return rand_key

########NEW FILE########
__FILENAME__ = settings
# -*- coding: utf-8 -*-
# Django settings for OpenShift project.
import imp, os

# a setting to determine whether we are running on OpenShift
ON_OPENSHIFT = False
if os.environ.has_key('OPENSHIFT_REPO_DIR'):
    ON_OPENSHIFT = True

PROJECT_DIR = os.path.dirname(os.path.realpath(__file__))
if ON_OPENSHIFT:
    DEBUG = bool(os.environ.get('DEBUG', False))
    if DEBUG:
        print("WARNING: The DEBUG environment is set to True.")
else:
    DEBUG = True
TEMPLATE_DEBUG = DEBUG

ADMINS = (
    # ('Your Name', 'your_email@example.com'),
)
MANAGERS = ADMINS

if ON_OPENSHIFT:
    # os.environ['OPENSHIFT_MYSQL_DB_*'] variables can be used with databases created
    # with rhc cartridge add (see /README in this git repo)
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',  # Add 'postgresql_psycopg2', 'postgresql', 'mysql', 'sqlite3' or 'oracle'.
            'NAME': os.path.join(os.environ['OPENSHIFT_DATA_DIR'], 'sqlite3.db'),  # Or path to database file if using sqlite3.
            'USER': '',                      # Not used with sqlite3.
            'PASSWORD': '',                  # Not used with sqlite3.
            'HOST': '',                      # Set to empty string for localhost. Not used with sqlite3.
            'PORT': '',                      # Set to empty string for default. Not used with sqlite3.
        }
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',  # Add 'postgresql_psycopg2', 'postgresql', 'mysql', 'sqlite3' or 'oracle'.
            'NAME': os.path.join(PROJECT_DIR, 'sqlite3.db'),  # Or path to database file if using sqlite3.
            'USER': '',                      # Not used with sqlite3.
            'PASSWORD': '',                  # Not used with sqlite3.
            'HOST': '',                      # Set to empty string for localhost. Not used with sqlite3.
            'PORT': '',                      # Set to empty string for default. Not used with sqlite3.
        }
    }

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
MEDIA_ROOT = os.environ.get('OPENSHIFT_DATA_DIR', '')

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash.
# Examples: "http://media.lawrence.com/media/", "http://example.com/media/"
MEDIA_URL = ''

# Absolute path to the directory static files should be collected to.
# Don't put anything in this directory yourself; store your static files
# in apps' "static/" subdirectories and in STATICFILES_DIRS.
# Example: "/home/media/media.lawrence.com/static/"
STATIC_ROOT = os.path.join(PROJECT_DIR, '..', 'static')

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
    #'django.contrib.staticfiles.finders.DefaultStorageFinder',
)

# Make a dictionary of default keys
default_keys = { 'SECRET_KEY': 'vm4rl5*ymb@2&d_(gc$gb-^twq9w(u69hi--%$5xrh!xk(t%hw' }

# Replace default keys with dynamic values if we are in OpenShift
use_keys = default_keys
if ON_OPENSHIFT:
    imp.find_module('openshiftlibs')
    import openshiftlibs
    use_keys = openshiftlibs.openshift_secure(default_keys)

# Make this unique, and don't share it with anybody.
SECRET_KEY = use_keys['SECRET_KEY']

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
    #'django.template.loaders.eggs.Loader',
)

MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
)

ROOT_URLCONF = 'openshift.urls'

TEMPLATE_DIRS = (
    # Put strings here, like "/home/html/django_templates" or "C:/www/django/templates".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
    os.path.join(PROJECT_DIR, 'templates'),
)

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    # Uncomment the next line to enable the admin:
    'django.contrib.admin',
    # Uncomment the next line to enable admin documentation:
    # 'django.contrib.admindocs',
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
from django.conf.urls import patterns, include, url

# Uncomment the next two lines to enable the admin:
from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns('',
    # Examples:
    url(r'^$', 'openshift.views.home', name='home'),
    # url(r'^openshift/', include('openshift.foo.urls')),

    # Uncomment the admin/doc line below to enable admin documentation:
    # url(r'^admin/doc/', include('django.contrib.admindocs.urls')),

    # Uncomment the next line to enable the admin:
    url(r'^admin/', include(admin.site.urls)),
)

########NEW FILE########
__FILENAME__ = views
import os
from django.shortcuts import render_to_response

def home(request):
    return render_to_response('home/home.html')

########NEW FILE########
