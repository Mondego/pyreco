__FILENAME__ = forms
from django import forms

class EmailForm(forms.Form):
    subject = forms.CharField(max_length=100)
    message = forms.CharField(widget=forms.Textarea)
    sender = forms.EmailField()
    recipient = forms.EmailField()
########NEW FILE########
__FILENAME__ = tasks
from django.core.mail import send_mail
from celery import task
import logging

@task()
def send_a_letter(sender, recipient, subject, body):
	send_mail(subject, body, sender, [recipient], fail_silently=False)

@task()
def report_errors():
	logging.error("reporting errors")
########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import patterns, include, url
from django.views.generic.simple import redirect_to, direct_to_template


urlpatterns = patterns('',
    url(r'^email/$', 'apps.examples.views.email', name='email_example'),
)
########NEW FILE########
__FILENAME__ = views
import os
import redis
from django.http import HttpResponse
from django.shortcuts import render
from tasks import send_a_letter
from forms import EmailForm

def email(request):
	if request.method == "POST":
		form = EmailForm(request.POST)
		if form.is_valid():
			send_a_letter.delay(form.cleaned_data["sender"],form.cleaned_data["recipient"],
				form.cleaned_data["subject"],form.cleaned_data["message"])
			return HttpResponse("all sent. thanks.")
	else:
		form = EmailForm()
	
	return render(request, 'examples/email.html', {
		'form' : form
	})
########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import patterns, include, url
from django.views.generic.simple import redirect_to, direct_to_template
from django.conf import settings
from django.contrib import admin


admin.autodiscover()

urlpatterns = patterns('',
    url(r'^$', direct_to_template, { "template" : "welcome.html"}),
    url(r'^examples/', include('apps.examples.urls')),
    url(r'^admin/', include(admin.site.urls)),
)

if getattr(settings,"DEBUG"):
    urlpatterns += patterns('django.contrib.staticfiles.views',
        url(r'^static/(?P<path>.*)$', 'serve'),
    )



########NEW FILE########
__FILENAME__ = fabfile
from fabric.api import *
from functools import wraps
import os, sys

__all__ = ['deploy','run','collectstatic']

def patch_python_path(f):
	@wraps(f)	 	
	def wrap(*args, **kwargs):
		ROOT = os.pathsep.join([os.path.abspath(os.path.dirname(__file__))])

		if not os.environ.has_key("PYTHONPATH"):
			os.environ["PYTHONPATH"] = ""

		if not (ROOT in os.environ["PYTHONPATH"].split(":")):
			os.environ["PYTHONPATH"] = "%s:%s" % (os.environ["PYTHONPATH"], ROOT)

		if not ROOT in sys.path:
			sys.path.append(ROOT)

		return f(*args, **kwargs)
	return wrap

@patch_python_path
def deploy():
	from tools.git import check_git_state, is_git_clean
	from tools.database import needsdatabase, local_migrate, remote_migrate, remote_syncdb
	from tools.apps import enumerate_apps

	@check_git_state
	@needsdatabase
	def __deploy():
		print "Deploying your application"
		print "----------------------------"

		print "Migrations..."

		for app in enumerate_apps():
			local_migrate(app)
			
		if is_git_clean():
			print "Pushing code on Heroku"
			local("git push heroku master")
		else:
			print "Committing migrations..."
			local("git add .")
			local("git commit -a -m '[DHB] data migrations'")


		print "Sync remote database"
		remote_syncdb()


		for app in ["djcelery"]:
			with settings(warn_only=True):
				print "Migrating %s ..." % app
				local("heroku run python manage.py migrate %s --settings=settings.prod" % (app))

		for app in enumerate_apps():
			remote_migrate(app)

		print "Transferring static files to S3"
		collectstatic()	

	__deploy()

@patch_python_path
def run():
	print sys.path

	from tools.database import needsdatabase, local_migrate
	from tools.apps import enumerate_apps
	from tools.heroku import start_foreman

	@needsdatabase
	def __run():
		for app in ["djcelery"]:
			with settings(warn_only=True):
				print "Migrating %s ..." % app
				local("python manage.py migrate %s --settings=settings.dev" % (app))
				
		for app in enumerate_apps():
			with settings(warn_only=True):
				local_migrate(app)

		start_foreman()		

	__run()

@patch_python_path
def collectstatic():
    local("python manage.py collectstatic --noinput --settings=settings.static")
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
__FILENAME__ = aws
# AWS settings

#Your Amazon Web Services access key, as a string.
AWS_ACCESS_KEY_ID = ""

#Your Amazon Web Services secret access key, as a string.
AWS_SECRET_ACCESS_KEY = ""

#Your Amazon Web Services storage bucket name, as a string.
AWS_STORAGE_BUCKET_NAME = ""

#Additional headers to pass to S3
AWS_HEADERS = {}

########NEW FILE########
__FILENAME__ = celerybeat
from datetime import timedelta

CELERYBEAT_SCHEDULE = {
    'runs-every-minute': {
        'task': 'apps.examples.tasks.report_errors',
        'schedule': timedelta(minutes=15)
    },
}

CELERY_TIMEZONE = 'UTC'
########NEW FILE########
__FILENAME__ = common
import os

ADMINS = (
    # ('Your Name', 'your_email@example.com'),
)

MANAGERS = ADMINS

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
MEDIA_ROOT = ''

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash.
# Examples: "http://media.lawrence.com/media/", "http://example.com/media/"
MEDIA_URL = ''

STATICFILES_DIRS = (
     os.path.join(os.path.realpath(os.path.dirname(__file__)), "../static"),
)

# URL prefix for admin static files -- CSS, JavaScript and images.
# Make sure to use a trailing slash.
# Examples: "http://foo.com/static/admin/", "/static/admin/".
ADMIN_MEDIA_PREFIX = '/static/admin/'


# List of finder classes that know how to find static files in
# various locations.
STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
)

# Make this unique, and don't share it with anybody.
SECRET_KEY = ''

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
)

MIDDLEWARE_CLASSES = (
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
)

ROOT_URLCONF = 'apps.urls'

TEMPLATE_DIRS = (
    os.path.join(os.path.realpath(os.path.dirname(__file__)), "../templates"), 
)

TEMPLATE_CONTEXT_PROCESSORS = (
    'django.contrib.auth.context_processors.auth',
    'django.core.context_processors.debug',
    'django.core.context_processors.i18n',
    'django.core.context_processors.media',
    'django.core.context_processors.static',
    'django.core.context_processors.request',
    'django.contrib.messages.context_processors.messages',
)

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.admin',
    'djcelery',
    'south',
    'apps.examples',
)

#CELERY SETUP

BROKER_URL = os.getenv('REDISTOGO_URL','redis://localhost:6379')

import djcelery
djcelery.setup_loader()

try:
    from celerybeat import *
except:
    pass
########NEW FILE########
__FILENAME__ = dev
import os
from common import *

DEBUG = TEMPLATE_DEBUG = True
INTERNAL_IPS = ["127.0.0.1"]

STATIC_URL = '/static/'

DATABASES = {'default' : {'ENGINE' : 'django.db.backends.sqlite3', 'NAME' : os.path.join(os.path.dirname(__file__),'../data.db')}}

EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

########NEW FILE########
__FILENAME__ = prod
import os
from common import *
from aws import *
from tools.heroku import database_config

INSTALLED_APPS += (
    'storages',
)

DEBUG = TEMPLATE_DEBUG = False

DATABASES = {'default' : database_config() }

#Configure static content to be served form S3 
DEFAULT_FILE_STORAGE = 'storages.backends.s3boto.S3BotoStorage'
STATICFILES_STORAGE = DEFAULT_FILE_STORAGE
STATIC_URL = '//s3.amazonaws.com/%s/' % AWS_STORAGE_BUCKET_NAME
ADMIN_MEDIA_PREFIX = STATIC_URL + 'admin/'

#Email : using Amazon SES
EMAIL_BACKEND = 'django_ses.SESBackend'
########NEW FILE########
__FILENAME__ = static
from common import *
from aws import *

INSTALLED_APPS += (
    'storages',
)

#Configure static content to be served form S3 
DEFAULT_FILE_STORAGE = 'storages.backends.s3boto.S3BotoStorage'
STATICFILES_STORAGE = DEFAULT_FILE_STORAGE
########NEW FILE########
__FILENAME__ = apps
import os

def enumerate_apps():
    return [ name for name in os.listdir('./apps') if os.path.isdir(os.path.join('./apps', name)) ]
########NEW FILE########
__FILENAME__ = database
import os
from functools import wraps
from fabric.api import local, settings


def needsdatabase(f):
    @wraps(f)
    def wrap(*args, **kwargs):
        local("python manage.py syncdb --settings=settings.dev")
        return f(*args, **kwargs)
    return wrap

def remote_syncdb():
    local("heroku run python manage.py syncdb --settings=settings.prod")

def what_is_my_database_url():
    local("heroku config | grep POSTGRESQL")

def remote_migrate(app_name):
    if os.path.exists(os.path.join("./apps", app_name, "migrations")):
        with settings(warn_only=True):
            r = local("heroku run python manage.py migrate apps.%s --settings=settings.prod" % (app_name), capture=True)
            if r.find("django.db.utils.DatabaseError") != -1:
                print "Normal migration failed. Running a fake migration..."
                local("heroku run python manage.py migrate apps.%s --settings=settings.prod --fake" % (app_name))

def local_migrate(app_name):
    #TODO: figure out if there are actual models within the app
    if not os.path.exists(os.path.join("./apps", app_name, "models.py")):
        return

    if not os.path.exists(os.path.join("./apps", app_name, "migrations")):
        with settings(warn_only=True):
            r = local("python manage.py convert_to_south apps.%s --settings=settings.dev" % app_name, capture=True)
            if r.return_code != 0:
                return
    else:
        #app has been converted and ready to roll
        
        with settings(warn_only=True):
            r = local("python manage.py schemamigration apps.%s --auto --settings=settings.dev" % app_name)

            if r.return_code != 0:
                print "Scema migration return code != 0 -> nothing to migrate"
            else:
                local("python manage.py migrate apps.%s --settings=settings.dev" % (app_name))
########NEW FILE########
__FILENAME__ = git
from fabric.api import *
from functools import wraps

def is_git_clean():
    git_status = local("git status", capture=True).lower()
    print "is_git_clean reports: %s" % git_status

    msgs = ["untracked files", "changes to be committed", "changes not staged for commit"]

    for msg in msgs:
        if git_status.find(msg) != -1:
            return False

    return  True

def check_git_state(f):
    @wraps(f)
    def wrap(*args, **kwargs):
        if not is_git_clean():
            print "Cannot deploy: make sure your git is clean"
        else:
            return f(*args, **kwargs)
    return wrap
########NEW FILE########
__FILENAME__ = heroku
import os, re
import dj_database_url
from fabric.api import local, settings

def start_foreman(proc_file="Procfile.dev"):
    local("foreman start -f %s" % proc_file)

def database_config(env_varibale_pattern="HEROKU_POSTGRESQL_\S+_URL", default_env_variable="DATABASE_URL"):

    r = re.compile(env_varibale_pattern)

    urls = filter(lambda k : r.match(k) is not None, os.environ.keys())

    if len(urls) > 1:
        if not os.environ.has_key(default_env_variable):
            print "Multiple env variables matching %s detected. Using %s" % (env_varibale_pattern, urls[0])


    if len(urls) == 0:
        if not os.environ.has_key(default_env_variable):
            raise Exception("No database detected. Make sure you enable database on your heroku instance (e.g. heroku addons:add heroku-postgresql:dev)")

    return dj_database_url.config(default_env_variable, os.environ[urls[0]] if len(urls) !=0 else None)

########NEW FILE########
