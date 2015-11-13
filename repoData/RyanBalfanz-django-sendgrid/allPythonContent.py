__FILENAME__ = forms
from django import forms


class EmailForm(forms.Form):
	subject = forms.CharField(max_length=100)
	message = forms.CharField(widget=forms.Textarea)
	sender = forms.EmailField()
	to = forms.EmailField()
	categories = forms.CharField(help_text="CSV", required=False, widget=forms.Textarea)
	html = forms.BooleanField(initial=False, required=False)
	enable_gravatar = forms.BooleanField(initial=False, required=False)
	enable_click_tracking = forms.BooleanField(initial=False, required=False)
	add_unsubscribe_link = forms.BooleanField(initial=False, required=False)

########NEW FILE########
__FILENAME__ = models
import logging

from django.contrib.auth.models import User
# from django.core.mail import get_connection
from django.core.mail import EmailMessage
# from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver

# django-sendgrid
# from sendgrid.mail import get_sendgrid_connection
from sendgrid.mail import send_sendgrid_mail
from sendgrid.mail import send_sendgrid_mail
from sendgrid.message import SendGridEmailMessage


logger = logging.getLogger(__name__)

REGISTRATION_EMAIL_SPEC = {
	"subject": "Your new account!",
	"body": "Thanks for signing up.",
	"from_email": 'welcome@example.com',
}

def get_user(user):
	"""docstring for get_user"""
	_user = None
	if isinstance(user, User):
		_user = user
	elif isinstance(user, basestring):
		try:
			user = int(user)
		except ValueError:
			try:
				_user = User.objects.get(username=user)
			except User.DoesNotExist as e:
				logger.exception("Caught exception: {error}".format(error=e))
		else:
			try:
				_user = User.objects.get(id=user)
			except User.DoesNotExist as e:
				logger.exception("Caught exception: {error}".format(error=e))
				
	return _user

def send_registration_email_to_new_user(user, emailOptions=REGISTRATION_EMAIL_SPEC):
	"""
	Sends a registration email to ``user``.
	"""
	user = get_user(user)
	
	registrationEmail = SendGridEmailMessage(
		to=[user.email],
		**emailOptions
	)
	registrationEmail.sendgrid_headers.setCategory("Registration")
	registrationEmail.sendgrid_headers.setUniqueArgs({"user_id": user.id})
	response = registrationEmail.send()
	
	return response

@receiver(post_save, sender=User)
def send_new_user_email(sender, instance, created, raw, using, **kwargs):
	logger.debug("Received post_save from {user}".format(user=instance))
	if created:
		# Send a custom email, with, for example, a category.
		send_registration_email_to_new_user(instance)
		
		# Send directly using ``send_sendgrid_mail`` shortcut.
		# send_sendgrid_mail(
		# 	recipient_list=[instance.username],
		# 	subject=REGISTRATION_EMAIL_SPEC["subject"],
		# 	message=REGISTRATION_EMAIL_SPEC["body"],
		# 	from_email=REGISTRATION_EMAIL_SPEC["from_email"],
		# )

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
__FILENAME__ = urls
from django.conf.urls.defaults import patterns, include, url

from main.views import send_simple_email

urlpatterns = patterns('',
	url(r'^$', send_simple_email),
)

########NEW FILE########
__FILENAME__ = views
from __future__ import absolute_import

import logging

from django.contrib import messages
from django.core.context_processors import csrf
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect
from django.shortcuts import render_to_response

# django-sendgrid
from sendgrid.mail import send_sendgrid_mail
from sendgrid.message import SendGridEmailMessage
from sendgrid.message import SendGridEmailMultiAlternatives
from sendgrid.utils import filterutils

# example_project
from .forms import EmailForm

DEFAULT_CSV_SEPARATOR = ","

logger = logging.getLogger(__name__)

def parse_csv_string(s, separator=DEFAULT_CSV_SEPARATOR):
	return [field.strip() for field in s.split(separator) if field]

def send_simple_email(request):
	if request.method == 'POST':
		form = EmailForm(request.POST)
		if form.is_valid():
			subject = form.cleaned_data["subject"]
			message = form.cleaned_data["message"]
			from_email = form.cleaned_data["sender"]
			recipient_list = form.cleaned_data["to"]
			recipient_list = [r.strip() for r in recipient_list.split(",")]
			categoryData = form.cleaned_data["categories"]
			categories = parse_csv_string(categoryData)
			html = form.cleaned_data["html"]
			enable_gravatar = form.cleaned_data["enable_gravatar"]
			enable_click_tracking = form.cleaned_data["enable_click_tracking"]
			add_unsubscribe_link = form.cleaned_data["add_unsubscribe_link"]

			if html:
				sendGridEmail = SendGridEmailMultiAlternatives(
					subject,
					message,
					from_email,
					recipient_list,
				)
				sendGridEmail.attach_alternative(message, "text/html")
			else:
				sendGridEmail = SendGridEmailMessage(
					subject,
					message,
					from_email,
					recipient_list,
				)
				
			if categories:
				logger.debug("Categories {c} were given".format(c=categories))
				# The SendGrid Event API will POST different data for single/multiple category messages.
				if len(categories) == 1:
					sendGridEmail.sendgrid_headers.setCategory(categories[0])
				elif len(categories) > 1:
					sendGridEmail.sendgrid_headers.setCategory(categories)
				sendGridEmail.update_headers()
				
			filterSpec = {}
			if enable_gravatar:
				logger.debug("Enable Gravatar was selected")
				filterSpec["gravatar"] = {
					"enable": 1
				}
				
			if enable_gravatar:
				logger.debug("Enable click tracking was selected")
				filterSpec["clicktrack"] = {
					"enable": 1
				}
				
			if add_unsubscribe_link:
				logger.debug("Add unsubscribe link was selected")
				# sendGridEmail.sendgrid_headers.add
				filterSpec["subscriptiontrack"] = {
					"enable": 1,
					"text/html": "<p>Unsubscribe <%Here%></p>",
				}
				
			if filterSpec:
				filterutils.update_filters(sendGridEmail, filterSpec, validate=True)
				
			logger.debug("Sending SendGrid email {e}".format(e=sendGridEmail))
			response = sendGridEmail.send()
			logger.debug("Response {r}".format(r=response))

			if response == 1:
				msg = "Your message was sent"
				msgType = messages.SUCCESS
			else:
				msg = "The was en error sending your message"
				msgType = messages.ERROR
			messages.add_message(request, msgType, msg)

			return HttpResponseRedirect("/")
	else:
		form = EmailForm()

	c = { "form": form }
	c.update(csrf(request))
	return render_to_response('main/send_email.html', c)

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
# Django settings for example_project project.
import os

DEBUG = True
TEMPLATE_DEBUG = DEBUG

ADMINS = (
	('Ryan', 'ryan@ryanbalfanz.net'),
)

MANAGERS = ADMINS

DATABASES = {
	'default': {
		'ENGINE': 'django.db.backends.sqlite3', # Add 'postgresql_psycopg2', 'postgresql', 'mysql', 'sqlite3' or 'oracle'.
		'NAME': 'sendgrid.db',						 # Or path to database file if using sqlite3.
		'USER': '',						 # Not used with sqlite3.
		'PASSWORD': '',					 # Not used with sqlite3.
		'HOST': '',						 # Set to empty string for localhost. Not used with sqlite3.
		'PORT': '',						 # Set to empty string for default. Not used with sqlite3.
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
MEDIA_ROOT = ''

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash.
# Examples: "http://media.lawrence.com/media/", "http://example.com/media/"
MEDIA_URL = ''

# Absolute path to the directory static files should be collected to.
# Don't put anything in this directory yourself; store your static files
# in apps' "static/" subdirectories and in STATICFILES_DIRS.
# Example: "/home/media/media.lawrence.com/static/"
STATIC_ROOT = '/home/znaflab/webapps/djsendgrid/lib/python2.7/django/contrib/admin/media/'

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
#	 'django.contrib.staticfiles.finders.DefaultStorageFinder',
)

# Make this unique, and don't share it with anybody.
SECRET_KEY = 'n!jhvdh#gf2%6o^va3ohfly_z4eg$nmxyq9#ke(&%$u)xgpjd_'

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
	'django.template.loaders.filesystem.Loader',
	'django.template.loaders.app_directories.Loader',
#	  'django.template.loaders.eggs.Loader',
)

MIDDLEWARE_CLASSES = (
	'django.middleware.common.CommonMiddleware',
	'django.contrib.sessions.middleware.SessionMiddleware',
	'django.middleware.csrf.CsrfViewMiddleware',
	'django.contrib.auth.middleware.AuthenticationMiddleware',
	'django.contrib.messages.middleware.MessageMiddleware',
	'debug_toolbar.middleware.DebugToolbarMiddleware',
)

ROOT_URLCONF = 'example_project.urls'

TEMPLATE_DIRS = (
	# Put strings here, like "/home/html/django_templates" or "C:/www/django/templates".
	# Always use forward slashes, even on Windows.
	# Don't forget to use absolute paths, not relative paths.
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
	'south',
	'sendgrid',
	'debug_toolbar',
	'main',
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
		},
		'console':{
			'level':'DEBUG',
			'class':'logging.StreamHandler',
		},
		'sendgrid':{
			'level':'DEBUG',
			'class':'logging.StreamHandler',
		},
	},
	'loggers': {
		'django.request': {
			'handlers': ['mail_admins',],
			'level': 'ERROR',
			'propagate': True,
		},
		'sendgrid': {
			'handlers': ['console',],
			'level': 'DEBUG',
		}
	}
}

INTERNAL_IPS = ('127.0.0.1',)

# django-sendgrid
# ---------------

SENDGRID_EMAIL_BACKEND = "sendgrid.backends.SendGridEmailBackend"
EMAIL_BACKEND = SENDGRID_EMAIL_BACKEND
SENDGRID_EMAIL_HOST = "smtp.sendgrid.net"
SENDGRID_EMAIL_PORT = 587
SENDGRID_EMAIL_USERNAME = os.getenv("SENDGRID_EMAIL_USERNAME")
SENDGRID_EMAIL_PASSWORD = os.getenv("SENDGRID_EMAIL_PASSWORD")
# SENDGRID_CREATE_MISSING_EMAIL_MESSAGES = True

try:
	from settings_local import *
except ImportError:
	pass

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import patterns, include, url

# Uncomment the next two lines to enable the admin:
from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns('',
	# Examples:
	# url(r'^$', 'django.views.generic.simple.redirect_to', {'url': '/sendgrid/'}, name='home'),
	url(r"^$", include("example_project.main.urls"), name="index"),
	url(r"^sendgrid/", include("sendgrid.urls")),
	# Uncomment the admin/doc line below to enable admin documentation:
	# url(r'^admin/doc/', include('django.contrib.admindocs.urls')),

	# Uncomment the next line to enable the admin:
	url(r'^admin/', include(admin.site.urls)),
)

########NEW FILE########
__FILENAME__ = fabfile
import os
import sys
import time

import fabric
from fabric.api import *
from fabric.contrib.files import upload_template, exists
from fabric.operations import put, open_shell


PROJECT_ROOT = os.path.dirname(__file__)

REPOSITORY = "git@github.com:RyanBalfanz/django-sendgrid.git"
REPOSITORY_NAME = "django-sendgrid"

WEBFACTION_USERNAME = os.getenv("WEBFACTION_USER")
WEBFACTION_PASSWORD = os.getenv("WEBFACTION_PASSWORD")
WEBFACTION_HOST = os.getenv("WEBFACTION_HOST")
WEBFACTION_APPLICATION = os.getenv("WEBFACTION_APPLICATION")
WEBFACTION_APPLICATION_ROOT = "/home/{user}/webapps/{app}/".format(
	user=WEBFACTION_USERNAME,
	app=WEBFACTION_APPLICATION,
)
WEBFACTION_WEBSITE_URL = os.getenv("WEBFACTION_WEBSITE_URL")

if not WEBFACTION_HOST:
	WEBFACTION_HOST = "{username}.webfactional.com".format(username=WEBFACTION_USERNAME)

env.hosts = [WEBFACTION_HOST]
env.user = WEBFACTION_USERNAME
env.password = WEBFACTION_PASSWORD
env.home = "/home/{user}".format(user=WEBFACTION_USERNAME)
env.project = WEBFACTION_APPLICATION
env.repo = REPOSITORY
env.project_dir = env.home + "/webapps/" + WEBFACTION_APPLICATION
env.python_executable = "/usr/local/bin/python2.7"
env.SENDGRID_EMAIL_USERNAME = os.getenv("SENDGRID_EMAIL_USERNAME")
env.SENDGRID_EMAIL_PASSWORD = os.getenv("SENDGRID_EMAIL_PASSWORD")

WEBFACTION_DJANGO_PROJECT_ROOT = os.path.join(env.project_dir, "example_project")

@task
def release():
	fabric.operations.local("python setup.py sdist register upload")

@task
def pull():
	"""
	Runs git pull.
	"""
	with cd(os.path.join(env.project_dir, REPOSITORY_NAME)):
		run("git pull")

@task
def checkout(remote=None, branch="master"):
	"""
	Runs git checkout.
	"""
	with cd(os.path.join(env.project_dir, REPOSITORY_NAME)):
		if remote:
			checkoutCmd = "git checkout {remote} {branch}".format(remote=remote, branch=branch)
		else:
			checkoutCmd = "git checkout {branch}".format(branch=branch)

		run(checkoutCmd)

@task
def run_tests(surpress="output"):
	with hide(surpress):
		with cd(os.path.join(env.project_dir, REPOSITORY_NAME, "example_project")):
			run("{python} manage.py test".format(python=env.python_executable))

@task
def syncdb():
	"""
	Runs the migrations.
	"""
	with cd(os.path.join(env.project_dir, REPOSITORY_NAME, "example_project")):
		run("{python} manage.py syncdb".format(python=env.python_executable))

@task
def restart_apache():
	"""
	Restarts Apache.
	"""
	envVars = {
		"SENDGRID_EMAIL_USERNAME": env.SENDGRID_EMAIL_USERNAME,
		"SENDGRID_EMAIL_PASSWORD": env.SENDGRID_EMAIL_PASSWORD,
	}
	setEnv = ";".join("export {0}={1}".format(var, val) for var, val in envVars.iteritems())
	with prefix(setEnv):
		with cd(env.project_dir):
			run("./apache2/bin/restart")

@task
def get_memory_usage():
	run("ps -u {user} -o rss,command".format(user=WEBFACTION_USERNAME))

@task
def debug_on(filepath=None):
	if not filepath:
		filepath = "/home/{user}/webapps/djsendgrid/example_project/settings_local.py".format(user=WEBFACTION_USERNAME)
	cmd = "sed -i 's/False/True/' {file}".format(file=filepath)
	run(cmd)
	restart_apache()


@task
def debug_off(filepath=None):
	if not filepath:
		filepath = "/home/{user}/webapps/djsendgrid/example_project/settings_local.py".format(user=WEBFACTION_USERNAME)
	cmd = "sed -i 's/True/False/' {file}".format(file=filepath)
	run(cmd)
	restart_apache()

def put_files(files):
	"""
	Puts files on a remote host.
	"""
	for name, paths in files.iteritems():
		localPath, remotePath = paths["local"], paths["remote"]
		put(localPath, remotePath)

def get_url_open_time(url):
	import urllib2

	startTime = time.time()
	urllib2.urlopen(url)
	elapsedSeconds = time.time() - startTime

	return elapsedSeconds

def time_get_url(url, n=1):
	avg = lambda s: sum(s) / len(s)

	timings = []
	for i in range(n):
		timings.append(get_url_open_time(url))
		lastTiming = timings[-1]
		print("Retrieved in {s} seconds.".format(s=lastTiming))

	result = min(timings), avg(timings), max(timings)
	return result

@task
def update_settings():
	startTime = time.time()

	putFiles = {
		"settings_local.py": {
			"local": os.path.join(PROJECT_ROOT, "deploy/settings_local.py"),
			"remote": os.path.join(WEBFACTION_APPLICATION_ROOT, "example_project", "settings_local.py")
		},
	}
	put_files(putFiles)
	restart_apache()
	elapsedSeconds = time.time() - startTime
	print("Updated in {s} seconds!".format(s=elapsedSeconds))

	print time_get_url(WEBFACTION_WEBSITE_URL, n=3)

@task
def deploy(branch):
	"""
	Deploys the application.
	"""
	startTime = time.time()

	putFiles = {
		"settings_local.py": {
			"local": os.path.join(PROJECT_ROOT, "deploy/settings_local.py"),
			"remote": os.path.join(WEBFACTION_APPLICATION_ROOT, "example_project", "settings_local.py")
		},
		"example_project.wsgi": {
			"local": os.path.join(PROJECT_ROOT, "deploy/example_project.wsgi"),
			"remote": os.path.join(WEBFACTION_APPLICATION_ROOT, "example_project.wsgi")
		},
		"httpd.conf": {
			"local": os.path.join(PROJECT_ROOT, "deploy/apache2/conf/httpd.conf"),
			"remote": os.path.join(WEBFACTION_APPLICATION_ROOT, "apache2/conf/httpd.conf")
		},
	}
	put_files(putFiles)

	pull()
	checkout(branch=branch)
	# run_tests()
	# syncdb()
	restart_apache()

	elapsedSeconds = time.time() - startTime
	print("Deployed in {s} seconds!".format(s=elapsedSeconds))

	print time_get_url(WEBFACTION_WEBSITE_URL, n=3)

def watch_logs(prefix="access", n=10, follow=False):
	"""docstring for watch_logs"""

	logPathOverrides = {
		"django": os.path.join(WEBFACTION_DJANGO_PROJECT_ROOT, "example_project.log"),
	}
	with cd(env.home):
		if prefix in logPathOverrides:
			logFile = logPathOverrides[prefix]
		else:
			logFile = os.path.join(env.home, "logs", "user", "{prefix}_{app}.log").format(prefix=prefix, app=WEBFACTION_APPLICATION)

		if follow:
			cmd = "tail -n {n} -f {file}".format(n=n, file=logFile)
		else:
			cmd = "tail -n {n} {file}".format(n=n, file=logFile)

		run(cmd)

@task
def access_logs(n=10, follow=True):
	watch_logs("access", n, follow)

@task
def error_logs(n=10, follow=True):
	watch_logs("error", n, follow)

def django_logs(n=10, follow=True):
	watch_logs("django", n, follow)

@task
def logs(logType="access"):
	"""
	Tails the logs.
	"""
	startTime = time.time()

	delegates = {
		"access": access_logs,
		"error": error_logs,
		"django": django_logs,
	}
	try:
		f = delegates[logType]
	except KeyError:
		raise ValueError("Unrecognized log type '{}'".format(logType))
	else:
		f()
		# f(n, follow)
	finally:
		elapsedSeconds = time.time() - startTime
		print "Elapsed time (s): {n}".format(n=elapsedSeconds)

@task
def shell(*args, **kwargs):
	envVars = {
		"SENDGRID_EMAIL_USERNAME": env.SENDGRID_EMAIL_USERNAME,
		"SENDGRID_EMAIL_PASSWORD": env.SENDGRID_EMAIL_PASSWORD,
		# "PYTHONPATH:": env.python_executable + ":$PYTHONPATH",
	}
	setEnv = ";".join("export {0}={1}".format(var, val) for var, val in envVars.iteritems())
	with prefix(setEnv):
		open_shell(*args, **kwargs)

########NEW FILE########
__FILENAME__ = admin
from __future__ import absolute_import

from django.conf import settings
from django.contrib import admin

from .models import Argument
from .models import Category
from .models import EmailMessage
from .models import EmailMessageAttachmentsData
from .models import EmailMessageBodyData
from .models import EmailMessageBccData
from .models import EmailMessageCcData
from .models import EmailMessageExtraHeadersData
from .models import EmailMessageSendGridHeadersData
from .models import EmailMessageSubjectData
from .models import EmailMessageToData
from .models import Event
from .models import EventType
from .models import UniqueArgument


DEBUG_SHOW_DATA_ADMIN_MODELS = settings.DEBUG


class ArgumentAdmin(admin.ModelAdmin):
	date_hierarchy = "creation_time"
	list_display = ("key", "creation_time", "last_modified_time", "email_message_count", "unique_arguments_count")
	readonly_fields = ("key", "email_message_count", "unique_arguments_count")
	search_fields = ("name",)

	def has_add_permission(self, request):
		return False

	def email_message_count(self, argument):
		return argument.emailmessage_set.count()

	def unique_arguments_count(self, argument):
		return argument.uniqueargument_set.count()


class CategoryAdmin(admin.ModelAdmin):
	date_hierarchy = "creation_time"
	list_display = ("name", "creation_time", "last_modified_time", "email_message_count")
	readonly_fields = ("name", "email_message_count")
	search_fields = ("name",)

	def has_add_permission(self, request):
		return False

	def email_message_count(self, category):
		return category.emailmessage_set.count()


class EmailMessageGenericDataInline(admin.TabularInline):
	model = None
	readonly_fields = ("data",)
	max_num = 1
	can_delete = False

	def has_add_permission(self, request):
		return False


class EmailMessageAttachmentsDataInline(EmailMessageGenericDataInline):
	model = EmailMessageAttachmentsData


class EmailMessageBccInline(EmailMessageGenericDataInline):
	model = EmailMessageBccData


class EmailMessageBodyDataInline(EmailMessageGenericDataInline):
	model = EmailMessageBodyData


class EmailMessageCcInline(EmailMessageGenericDataInline):
	model = EmailMessageCcData


class EmailMessageExtraHeadersDataInline(EmailMessageGenericDataInline):
	model = EmailMessageExtraHeadersData


class EmailMessageSendGridDataInline(EmailMessageGenericDataInline):
	model = EmailMessageSendGridHeadersData


class EmailMessageSubjectDataInline(EmailMessageGenericDataInline):
	model = EmailMessageSubjectData


class EmailMessageToDataInline(EmailMessageGenericDataInline):
	model = EmailMessageToData


class CategoryInLine(admin.TabularInline):
	model = EmailMessage.categories.through
	extra = 0
	can_delete = False
	readonly_fields = ("category",)

	def has_add_permission(self, request):
		return False


class EventInline(admin.TabularInline):
	model = Event
	can_delete = False
	extra = 0
	readonly_fields = ("email", "event_type")


class UniqueArgumentsInLine(admin.TabularInline):
	model = UniqueArgument
	extra = 0
	can_delete = False
	readonly_fields = ("argument", "data", "value",)

	def has_add_permission(self, request):
		return False


class EmailMessageAdmin(admin.ModelAdmin):
	date_hierarchy = "creation_time"
	list_display = (
		"message_id",
		"from_email",
		"to_email",
		"category",
		"subject_data",
		"response",
		"creation_time",
		"last_modified_time",
		"category_count",
		"event_count",
		"first_event_type",
		"latest_event_type",
		"unique_argument_count"
	)
	list_filter = ("from_email", "subject__data", "category", "response")
	readonly_fields = (
		"message_id",
		"from_email", 
		"to_email",
		"category",
		"response",
		"categories",
		"category_count",
		"arguments",
		"unique_argument_count"
	)
	inlines = (
		EmailMessageToDataInline,
		EmailMessageCcInline,
		EmailMessageBccInline,
		EmailMessageSubjectDataInline,
		EmailMessageBodyDataInline,
		EmailMessageSendGridDataInline,
		EmailMessageExtraHeadersDataInline,
		EmailMessageAttachmentsDataInline,
		CategoryInLine,
		EventInline,
		UniqueArgumentsInLine,
	)

	def has_add_permission(self, request):
		return False

	def category_count(self, emailMessage):
		return emailMessage.categories.count()

	def first_event_type(self, emailMessage):
		if emailMessage.first_event:
			return emailMessage.first_event.event_type.name
		return None

	def latest_event_type(self, emailMessage):
		if emailMessage.latest_event:
			return emailMessage.latest_event.event_type.name
		return None

	def unique_argument_count(self, emailMessage):
		return emailMessage.uniqueargument_set.count()


class EventAdmin(admin.ModelAdmin):
	date_hierarchy = "creation_time"
	list_display = (
		"email_message",
		"event_type",
		"email",
		"creation_time",
		"last_modified_time",
	)
	list_filter = ("event_type",)
	search_fields = ("email_message__message_id",)
	readonly_fields = (
		"email_message",
		"event_type",
		"email",
		"creation_time",
		"last_modified_time",
	)

	def has_add_permission(self, request):
		return False


class EventTypeAdmin(admin.ModelAdmin):
	# date_hierarchy = "creation_time"
	list_display = ("name", "event_count")
	readonly_fields = (
		"name",
		"event_count",
	)

	def has_add_permission(self, request):
		return False

	def event_count(self, eventType):
		return eventType.event_set.count()


class EmailMessageGenericDataAdmin(admin.ModelAdmin):
	list_display = ("email_message", "data")


	def has_add_permission(self, request):
		return False


class UniqueArgumentAdmin(admin.ModelAdmin):
	date_hierarchy = "creation_time"
	list_display = ("email_message", "argument", "data", "creation_time", "last_modified_time")
	list_filter = ("argument",)
	readonly_fields = ("email_message", "argument", "data",)
	search_fields = ("argument__key", "data")

	def has_add_permission(self, request):
		return False


admin.site.register(Argument, ArgumentAdmin)
admin.site.register(UniqueArgument, UniqueArgumentAdmin)
admin.site.register(EmailMessage, EmailMessageAdmin)
admin.site.register(Event, EventAdmin)
admin.site.register(EventType, EventTypeAdmin)
admin.site.register(Category, CategoryAdmin)

if DEBUG_SHOW_DATA_ADMIN_MODELS:
	admin.site.register(EmailMessageAttachmentsData, EmailMessageGenericDataAdmin)
	admin.site.register(EmailMessageBccData, EmailMessageGenericDataAdmin)
	admin.site.register(EmailMessageBodyData, EmailMessageGenericDataAdmin)
	admin.site.register(EmailMessageCcData, EmailMessageGenericDataAdmin)
	admin.site.register(EmailMessageSendGridHeadersData, EmailMessageGenericDataAdmin)
	admin.site.register(EmailMessageExtraHeadersData, EmailMessageGenericDataAdmin)
	admin.site.register(EmailMessageSubjectData, EmailMessageGenericDataAdmin)
	admin.site.register(EmailMessageToData, EmailMessageGenericDataAdmin)

########NEW FILE########
__FILENAME__ = backends
import logging

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.core.mail.backends.smtp import EmailBackend


SENDGRID_EMAIL_HOST = getattr(settings, "SENDGRID_EMAIL_HOST", None)
SENDGRID_EMAIL_PORT = getattr(settings, "SENDGRID_EMAIL_PORT", None)
SENDGRID_EMAIL_USERNAME = getattr(settings, "SENDGRID_EMAIL_USERNAME", None)
SENDGRID_EMAIL_PASSWORD = getattr(settings, "SENDGRID_EMAIL_PASSWORD", None)

logger = logging.getLogger(__name__)

def check_settings(fail_silently=False):
	"""
	Checks that the required settings are available.
	"""
	allOk = True
	
	checks = {
		"SENDGRID_EMAIL_HOST": SENDGRID_EMAIL_HOST,
		"SENDGRID_EMAIL_PORT": SENDGRID_EMAIL_PORT,
		"SENDGRID_EMAIL_USERNAME": SENDGRID_EMAIL_USERNAME,
		"SENDGRID_EMAIL_PASSWORD": SENDGRID_EMAIL_PASSWORD,
	}
	
	for key, value in checks.iteritems():
		if not value:
			logger.warn("{k} is not set".format(k=key))
			allOk = False
			if not fail_silently:
				raise ImproperlyConfigured("{k} was not found".format(k=key))
			
	return allOk


class SendGridEmailBackend(EmailBackend):
	"""
	A wrapper that manages the SendGrid SMTP network connection.
	"""
	def __init__(self, host=None, port=None, username=None, password=None, use_tls=None, fail_silently=False, **kwargs):
		if not check_settings():
			logger.exception("A required setting was not found")

		super(SendGridEmailBackend, self).__init__(
			host=SENDGRID_EMAIL_HOST,
			port=SENDGRID_EMAIL_PORT,
			username=SENDGRID_EMAIL_USERNAME,
			password=SENDGRID_EMAIL_PASSWORD,
			fail_silently=fail_silently,
		)

########NEW FILE########
__FILENAME__ = constants
ARGUMENT_DATA_TYPE_UNKNOWN = 0
ARGUMENT_DATA_TYPE_BOOLEAN = 1
ARGUMENT_DATA_TYPE_INTEGER = 2
ARGUMENT_DATA_TYPE_FLOAT = 3
ARGUMENT_DATA_TYPE_COMPLEX = 4
ARGUMENT_DATA_TYPE_STRING = 5
EVENT_SHORT_DESC_MAX_LENGTH = 32

EVENT_FIELDS = ("event","category","email")

EVENT_MODEL_NAMES = {
	"CLICK": "ClickEvent",
	"BOUNCE": "BounceEvent",
	"DEFERRED":"DeferredEvent",
	"DELIVERED":"DeliverredEvent",
	"DROPPED":"DroppedEvent",
	"UNKNOWN":"Event",
	"PROCESSED":"Event",
	"OPEN":"Event",
	"UNSUBSCRIBE":"Event",
	"SPAMREPORT":"Event"
}

EVENT_TYPES_EXTRA_FIELDS_MAP = {
	"UNKNOWN": (),
	"DEFERRED": ("response", "attempt"),
	"PROCESSED": (),
	"DROPPED": ("reason",),
	"DELIVERED": ("response",),
	"BOUNCE": ("status", "reason", "type"),
	"OPEN": (),
	"CLICK": ("url", ),
	"UNSUBSCRIBE": (),
	"SPAMREPORT": (),
}

UNIQUE_ARGS_STORED_FOR_EVENTS_WITHOUT_MESSAGE_ID = (
	"newsletter[newsletter_id]",
	"newsletter[newsletter_send_id]",
	"newsletter[newsletter_user_list_id]",
)
########NEW FILE########
__FILENAME__ = header
#!/usr/bin/python
# Version 1.0
# Last Updated 6/22/2009
# From http://docs.sendgrid.com/documentation/api/smtp-api/python-example/
import json
import re
import textwrap
 
class SmtpApiHeader:
 
	def __init__(self):
		self.data = {}
 
	def addTo(self, to):
		if not self.data.has_key('to'):
			self.data['to'] = []
		if type(to) is str:
			self.data['to'] += [to]
		else:
			self.data['to'] += to
 
	def addSubVal(self, var, val):
		if not self.data.has_key('sub'):
			self.data['sub'] = {}
		if type(val) is str:
			self.data['sub'][var] = [val]
		else:
			self.data['sub'][var] = val
 
	def setUniqueArgs(self, val):
		if type(val) is dict:
			self.data['unique_args'] = val
 
	def setCategory(self, cat):
		self.data['category'] = cat
 
	def addFilterSetting(self, fltr, setting, val):
		if not self.data.has_key('filters'):
			self.data['filters'] = {}
		if not self.data['filters'].has_key(fltr):
			self.data['filters'][fltr] = {}
		if not self.data['filters'][fltr].has_key('settings'):
				self.data['filters'][fltr]['settings'] = {}
		self.data['filters'][fltr]['settings'][setting] = val
 
	def asJSON(self):
		j = json.dumps(self.data)
		return re.compile('(["\]}])([,:])(["\[{])').sub('\1\2 \3', j)
 
	def as_string(self):
		j = self.asJSON()
		str = 'X-SMTPAPI: %s' % textwrap.fill(j, subsequent_indent = '	', width = 72)
		return str
########NEW FILE########
__FILENAME__ = mail
import logging

from django.conf import settings
from django.core.mail import get_connection
from django.core.mail import send_mail

# django-sendgrid
from utils import in_test_environment


SENDGRID_EMAIL_BACKEND = getattr(settings, "SENDGRID_EMAIL_BACKEND", None)

logger = logging.getLogger(__name__)

def get_sendgrid_connection(*args, **kwargs):
	"""
	Returns an instance of the email backend specified in SENDGRID_EMAIL_BACKEND.
	"""
	backend = SENDGRID_EMAIL_BACKEND
	if in_test_environment():
		logger.debug("In test environment!")
		backend = "django.core.mail.backends.locmem.EmailBackend"
		
	logger.debug("Getting SendGrid connection using backend {b}".format(b=backend))
	sendgrid_connection = get_connection(backend, *args, **kwargs)
	
	return sendgrid_connection

def send_sendgrid_mail(subject, message, from_email, recipient_list,
	fail_silently=False, auth_user=None, auth_password=None, connection=None):
	"""
	Sends mail with SendGrid.
	"""
	sendgrid_connection = get_sendgrid_connection()
	return send_mail(subject, message, from_email, recipient_list,
		fail_silently, auth_user, auth_password, connection=sendgrid_connection)

def send_mass_sendgrid_mail(datatuple, fail_silently=False, auth_user=None, auth_password=None, connection=None):
	"""
	Sends mass mail with SendGrid.
	"""
	raise NotImplementedError
	
	sendgrid_connection = get_sendgrid_connection()
	return send_mass_mail(datatuple, fail_silently, auth_password, auth_password, connection=sendgrid_connection)

########NEW FILE########
__FILENAME__ = cleanup_email_message_body_data
import datetime
from optparse import make_option

from django.core.management.base import BaseCommand, CommandError
from django.utils.timezone import now as now_utc

from sendgrid.models import EmailMessage
from sendgrid.models import EmailMessageBodyData
from sendgrid.utils.cleanup import cleanup_email_message_body_data
from sendgrid.utils.cleanup import delete_email_message_body_data

ONE_DAY = datetime.timedelta(days=1)
ONE_WEEK = datetime.timedelta(weeks=1)


class Command(BaseCommand):
	help = "Purges old EmailMessageBodyData objects"
	option_list = BaseCommand.option_list + (
	make_option("--as-date",
		default=False,
		action="store_true",
		help="Sets the number of days"
		),
	make_option("--days",
		default=0,
		type="int",
		help="Sets the number of days"
		),
	make_option("--weeks",
		default=0,
		type="int",
		help="Sets the number of weeks"
		),
	)

	def handle(self, *args, **kwargs):
		days = kwargs.get("days", None)
		weeks = kwargs.get("weeks", None)
		return str(cleanup_email_message_body_data(days=days, weeks=weeks))

########NEW FILE########
__FILENAME__ = message
from __future__ import absolute_import

# import datetime
import logging
import time
import uuid
try:
	import simplejson as json
except ImportError:
	import json

from django.conf import settings
from django.core import mail
from django.core.mail.message import EmailMessage
from django.core.mail.message import EmailMultiAlternatives

# django-sendgrid imports
from .header import SmtpApiHeader
from .mail import get_sendgrid_connection
from .models import save_email_message
from .signals import sendgrid_email_sent


logger = logging.getLogger(__name__)


class SendGridEmailMessageMixin:
	"""
	Adds support for SendGrid features.
	"""
	def _update_headers_with_sendgrid_headers(self):
		"""
		Updates the existing headers to include SendGrid headers.
		"""
		logger.debug("Updating headers with SendGrid headers")
		if self.sendgrid_headers:
			additionalHeaders = {
				"X-SMTPAPI": self.sendgrid_headers.asJSON()
			}
			self.extra_headers.update(additionalHeaders)

		logging.debug(str(self.extra_headers))

		return self.extra_headers
		
	def _update_unique_args(self, uniqueArgs):
		"""docstring for _update_unique_args"""
		oldUniqueArgs = self.sendgrid_headers.data.get("unique_args", None)
		newUniquieArgs = oldUniqueArgs.copy() if oldUniqueArgs else {}
		newUniquieArgs.update(uniqueArgs)
		self.sendgrid_headers.setUniqueArgs(newUniquieArgs)

		return self.sendgrid_headers.data["unique_args"]

	def update_headers(self, *args, **kwargs):
		"""
		Updates the headers.
		"""
		return self._update_headers_with_sendgrid_headers(*args, **kwargs)
		
	def get_category(self):
		"""docstring for get_category"""
		return self.sendgrid_headers.data["category"]
	category = property(get_category)

	def get_unique_args(self):
		"""docstring for get_unique_args"""
		return self.sendgrid_headers.data.get("unique_args", None)
	unique_args = property(get_unique_args)
	
	def setup_connection(self):
		"""docstring for setup_connection"""
		# Set up the connection
		connection = get_sendgrid_connection()
		self.connection = connection
		logger.debug("Connection: {c}".format(c=connection))
	
	def prep_message_for_sending(self):
		"""docstring for prep_message_for_sending"""
		self.setup_connection()
		
		# now = tz.localize(datetime.datetime.strptime(timestamp[:26], POSTMARK_DATETIME_STRING)).astimezone(pytz.utc)
		uniqueArgs = {
			"message_id": str(self._message_id),
			# "submition_time": time.time(),
		}
		self._update_unique_args(uniqueArgs)
		
		self.update_headers()

	def get_message_id(self):
		return self._message_id
	message_id = property(get_message_id)


class SendGridEmailMessage(SendGridEmailMessageMixin, EmailMessage):
	"""
	Adapts Django's ``EmailMessage`` for use with SendGrid.
	
	>>> from sendgrid.message import SendGridEmailMessage
	>>> myEmail = "rbalfanz@gmail.com"
	>>> mySendGridCategory = "django-sendgrid"
	>>> e = SendGridEmailMessage("Subject", "Message", myEmail, [myEmail], headers={"Reply-To": myEmail})
	>>> e.sendgrid_headers.setCategory(mySendGridCategory)
	>>> response = e.send()
	"""
	
	def __init__(self, *args, **kwargs):
		"""
		Initialize the object.
		"""
		self.sendgrid_headers = SmtpApiHeader()
		self._message_id = uuid.uuid4()
		super(SendGridEmailMessage, self).__init__(*args, **kwargs)
		
	def send(self, *args, **kwargs):
		"""Sends the email message."""
		self.prep_message_for_sending()
		
		save_email_message(sender=self,message=self,response=None)
		response = super(SendGridEmailMessage, self).send(*args, **kwargs)
		logger.debug("Tried to send an email with SendGrid and got response {r}".format(r=response))
		sendgrid_email_sent.send(sender=self, message=self, response=response)
		
		return response

	def get_message_id(self):
		return self._message_id
	message_id = property(get_message_id)


class SendGridEmailMultiAlternatives(SendGridEmailMessageMixin, EmailMultiAlternatives):
	"""
	Adapts Django's ``EmailMultiAlternatives`` for use with SendGrid.
	"""
	
	def __init__(self, *args, **kwargs):
		self.sendgrid_headers = SmtpApiHeader()
		self._message_id = uuid.uuid4()
		super(SendGridEmailMultiAlternatives, self).__init__(*args, **kwargs)
		
	def send(self, *args, **kwargs):
		"""Sends the email message."""
		self.prep_message_for_sending()
		
		save_email_message(sender=self,message=self,response=None)
		response = super(SendGridEmailMultiAlternatives, self).send(*args, **kwargs)
		logger.debug("Tried to send a multialternatives email with SendGrid and got response {r}".format(r=response))
		sendgrid_email_sent.send(sender=self, message=self, response=response)

		return response

########NEW FILE########
__FILENAME__ = 0001_initial
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'EmailMessage'
        db.create_table('sendgrid_emailmessage', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('message_id', self.gf('django.db.models.fields.CharField')(max_length=36, unique=True, null=True, blank=True)),
            ('from_email', self.gf('django.db.models.fields.CharField')(max_length=150)),
            ('to_email', self.gf('django.db.models.fields.CharField')(max_length=150)),
            ('category', self.gf('django.db.models.fields.CharField')(max_length=150, null=True, blank=True)),
            ('response', self.gf('django.db.models.fields.IntegerField')(null=True, blank=True)),
            ('creation_time', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('last_modified_time', self.gf('django.db.models.fields.DateTimeField')(auto_now=True, blank=True)),
        ))
        db.send_create_signal('sendgrid', ['EmailMessage'])

        # Adding model 'EmailMessageSubjectData'
        db.create_table('sendgrid_emailmessagesubjectdata', (
            ('email_message', self.gf('django.db.models.fields.related.OneToOneField')(related_name='subject', unique=True, primary_key=True, to=orm['sendgrid.EmailMessage'])),
            ('data', self.gf('django.db.models.fields.TextField')()),
        ))
        db.send_create_signal('sendgrid', ['EmailMessageSubjectData'])

        # Adding model 'EmailMessageSendGridHeadersData'
        db.create_table('sendgrid_emailmessagesendgridheadersdata', (
            ('email_message', self.gf('django.db.models.fields.related.OneToOneField')(related_name='sendgrid_headers', unique=True, primary_key=True, to=orm['sendgrid.EmailMessage'])),
            ('data', self.gf('django.db.models.fields.TextField')()),
        ))
        db.send_create_signal('sendgrid', ['EmailMessageSendGridHeadersData'])

        # Adding model 'EmailMessageExtraHeadersData'
        db.create_table('sendgrid_emailmessageextraheadersdata', (
            ('email_message', self.gf('django.db.models.fields.related.OneToOneField')(related_name='extra_headers', unique=True, primary_key=True, to=orm['sendgrid.EmailMessage'])),
            ('data', self.gf('django.db.models.fields.TextField')()),
        ))
        db.send_create_signal('sendgrid', ['EmailMessageExtraHeadersData'])

        # Adding model 'EmailMessageBodyData'
        db.create_table('sendgrid_emailmessagebodydata', (
            ('email_message', self.gf('django.db.models.fields.related.OneToOneField')(related_name='body', unique=True, primary_key=True, to=orm['sendgrid.EmailMessage'])),
            ('data', self.gf('django.db.models.fields.TextField')()),
        ))
        db.send_create_signal('sendgrid', ['EmailMessageBodyData'])

        # Adding model 'EmailMessageAttachmentsData'
        db.create_table('sendgrid_emailmessageattachmentsdata', (
            ('email_message', self.gf('django.db.models.fields.related.OneToOneField')(related_name='attachments', unique=True, primary_key=True, to=orm['sendgrid.EmailMessage'])),
            ('data', self.gf('django.db.models.fields.TextField')()),
        ))
        db.send_create_signal('sendgrid', ['EmailMessageAttachmentsData'])

        # Adding model 'EmailMessageBccData'
        db.create_table('sendgrid_emailmessagebccdata', (
            ('email_message', self.gf('django.db.models.fields.related.OneToOneField')(related_name='bcc', unique=True, primary_key=True, to=orm['sendgrid.EmailMessage'])),
            ('data', self.gf('django.db.models.fields.TextField')()),
        ))
        db.send_create_signal('sendgrid', ['EmailMessageBccData'])

        # Adding model 'EmailMessageCcData'
        db.create_table('sendgrid_emailmessageccdata', (
            ('email_message', self.gf('django.db.models.fields.related.OneToOneField')(related_name='cc', unique=True, primary_key=True, to=orm['sendgrid.EmailMessage'])),
            ('data', self.gf('django.db.models.fields.TextField')()),
        ))
        db.send_create_signal('sendgrid', ['EmailMessageCcData'])

        # Adding model 'EmailMessageToData'
        db.create_table('sendgrid_emailmessagetodata', (
            ('email_message', self.gf('django.db.models.fields.related.OneToOneField')(related_name='to', unique=True, primary_key=True, to=orm['sendgrid.EmailMessage'])),
            ('data', self.gf('django.db.models.fields.TextField')()),
        ))
        db.send_create_signal('sendgrid', ['EmailMessageToData'])


    def backwards(self, orm):
        # Deleting model 'EmailMessage'
        db.delete_table('sendgrid_emailmessage')

        # Deleting model 'EmailMessageSubjectData'
        db.delete_table('sendgrid_emailmessagesubjectdata')

        # Deleting model 'EmailMessageSendGridHeadersData'
        db.delete_table('sendgrid_emailmessagesendgridheadersdata')

        # Deleting model 'EmailMessageExtraHeadersData'
        db.delete_table('sendgrid_emailmessageextraheadersdata')

        # Deleting model 'EmailMessageBodyData'
        db.delete_table('sendgrid_emailmessagebodydata')

        # Deleting model 'EmailMessageAttachmentsData'
        db.delete_table('sendgrid_emailmessageattachmentsdata')

        # Deleting model 'EmailMessageBccData'
        db.delete_table('sendgrid_emailmessagebccdata')

        # Deleting model 'EmailMessageCcData'
        db.delete_table('sendgrid_emailmessageccdata')

        # Deleting model 'EmailMessageToData'
        db.delete_table('sendgrid_emailmessagetodata')


    models = {
        'sendgrid.emailmessage': {
            'Meta': {'object_name': 'EmailMessage'},
            'category': ('django.db.models.fields.CharField', [], {'max_length': '150', 'null': 'True', 'blank': 'True'}),
            'creation_time': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'from_email': ('django.db.models.fields.CharField', [], {'max_length': '150'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_modified_time': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'message_id': ('django.db.models.fields.CharField', [], {'max_length': '36', 'unique': 'True', 'null': 'True', 'blank': 'True'}),
            'response': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'to_email': ('django.db.models.fields.CharField', [], {'max_length': '150'})
        },
        'sendgrid.emailmessageattachmentsdata': {
            'Meta': {'object_name': 'EmailMessageAttachmentsData'},
            'data': ('django.db.models.fields.TextField', [], {}),
            'email_message': ('django.db.models.fields.related.OneToOneField', [], {'related_name': "'attachments'", 'unique': 'True', 'primary_key': 'True', 'to': "orm['sendgrid.EmailMessage']"})
        },
        'sendgrid.emailmessagebccdata': {
            'Meta': {'object_name': 'EmailMessageBccData'},
            'data': ('django.db.models.fields.TextField', [], {}),
            'email_message': ('django.db.models.fields.related.OneToOneField', [], {'related_name': "'bcc'", 'unique': 'True', 'primary_key': 'True', 'to': "orm['sendgrid.EmailMessage']"})
        },
        'sendgrid.emailmessagebodydata': {
            'Meta': {'object_name': 'EmailMessageBodyData'},
            'data': ('django.db.models.fields.TextField', [], {}),
            'email_message': ('django.db.models.fields.related.OneToOneField', [], {'related_name': "'body'", 'unique': 'True', 'primary_key': 'True', 'to': "orm['sendgrid.EmailMessage']"})
        },
        'sendgrid.emailmessageccdata': {
            'Meta': {'object_name': 'EmailMessageCcData'},
            'data': ('django.db.models.fields.TextField', [], {}),
            'email_message': ('django.db.models.fields.related.OneToOneField', [], {'related_name': "'cc'", 'unique': 'True', 'primary_key': 'True', 'to': "orm['sendgrid.EmailMessage']"})
        },
        'sendgrid.emailmessageextraheadersdata': {
            'Meta': {'object_name': 'EmailMessageExtraHeadersData'},
            'data': ('django.db.models.fields.TextField', [], {}),
            'email_message': ('django.db.models.fields.related.OneToOneField', [], {'related_name': "'extra_headers'", 'unique': 'True', 'primary_key': 'True', 'to': "orm['sendgrid.EmailMessage']"})
        },
        'sendgrid.emailmessagesendgridheadersdata': {
            'Meta': {'object_name': 'EmailMessageSendGridHeadersData'},
            'data': ('django.db.models.fields.TextField', [], {}),
            'email_message': ('django.db.models.fields.related.OneToOneField', [], {'related_name': "'sendgrid_headers'", 'unique': 'True', 'primary_key': 'True', 'to': "orm['sendgrid.EmailMessage']"})
        },
        'sendgrid.emailmessagesubjectdata': {
            'Meta': {'object_name': 'EmailMessageSubjectData'},
            'data': ('django.db.models.fields.TextField', [], {}),
            'email_message': ('django.db.models.fields.related.OneToOneField', [], {'related_name': "'subject'", 'unique': 'True', 'primary_key': 'True', 'to': "orm['sendgrid.EmailMessage']"})
        },
        'sendgrid.emailmessagetodata': {
            'Meta': {'object_name': 'EmailMessageToData'},
            'data': ('django.db.models.fields.TextField', [], {}),
            'email_message': ('django.db.models.fields.related.OneToOneField', [], {'related_name': "'to'", 'unique': 'True', 'primary_key': 'True', 'to': "orm['sendgrid.EmailMessage']"})
        }
    }

    complete_apps = ['sendgrid']
########NEW FILE########
__FILENAME__ = 0002_auto__chg_field_emailmessage_to_email__chg_field_emailmessage_from_ema
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):

        # Changing field 'EmailMessage.to_email'
        db.alter_column('sendgrid_emailmessage', 'to_email', self.gf('django.db.models.fields.CharField')(max_length=254))

        # Changing field 'EmailMessage.from_email'
        db.alter_column('sendgrid_emailmessage', 'from_email', self.gf('django.db.models.fields.CharField')(max_length=254))

    def backwards(self, orm):

        # Changing field 'EmailMessage.to_email'
        db.alter_column('sendgrid_emailmessage', 'to_email', self.gf('django.db.models.fields.CharField')(max_length=150))

        # Changing field 'EmailMessage.from_email'
        db.alter_column('sendgrid_emailmessage', 'from_email', self.gf('django.db.models.fields.CharField')(max_length=150))

    models = {
        'sendgrid.emailmessage': {
            'Meta': {'object_name': 'EmailMessage'},
            'category': ('django.db.models.fields.CharField', [], {'max_length': '150', 'null': 'True', 'blank': 'True'}),
            'creation_time': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'from_email': ('django.db.models.fields.CharField', [], {'max_length': '254'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_modified_time': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'message_id': ('django.db.models.fields.CharField', [], {'max_length': '36', 'unique': 'True', 'null': 'True', 'blank': 'True'}),
            'response': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'to_email': ('django.db.models.fields.CharField', [], {'max_length': '254'})
        },
        'sendgrid.emailmessageattachmentsdata': {
            'Meta': {'object_name': 'EmailMessageAttachmentsData'},
            'data': ('django.db.models.fields.TextField', [], {}),
            'email_message': ('django.db.models.fields.related.OneToOneField', [], {'related_name': "'attachments'", 'unique': 'True', 'primary_key': 'True', 'to': "orm['sendgrid.EmailMessage']"})
        },
        'sendgrid.emailmessagebccdata': {
            'Meta': {'object_name': 'EmailMessageBccData'},
            'data': ('django.db.models.fields.TextField', [], {}),
            'email_message': ('django.db.models.fields.related.OneToOneField', [], {'related_name': "'bcc'", 'unique': 'True', 'primary_key': 'True', 'to': "orm['sendgrid.EmailMessage']"})
        },
        'sendgrid.emailmessagebodydata': {
            'Meta': {'object_name': 'EmailMessageBodyData'},
            'data': ('django.db.models.fields.TextField', [], {}),
            'email_message': ('django.db.models.fields.related.OneToOneField', [], {'related_name': "'body'", 'unique': 'True', 'primary_key': 'True', 'to': "orm['sendgrid.EmailMessage']"})
        },
        'sendgrid.emailmessageccdata': {
            'Meta': {'object_name': 'EmailMessageCcData'},
            'data': ('django.db.models.fields.TextField', [], {}),
            'email_message': ('django.db.models.fields.related.OneToOneField', [], {'related_name': "'cc'", 'unique': 'True', 'primary_key': 'True', 'to': "orm['sendgrid.EmailMessage']"})
        },
        'sendgrid.emailmessageextraheadersdata': {
            'Meta': {'object_name': 'EmailMessageExtraHeadersData'},
            'data': ('django.db.models.fields.TextField', [], {}),
            'email_message': ('django.db.models.fields.related.OneToOneField', [], {'related_name': "'extra_headers'", 'unique': 'True', 'primary_key': 'True', 'to': "orm['sendgrid.EmailMessage']"})
        },
        'sendgrid.emailmessagesendgridheadersdata': {
            'Meta': {'object_name': 'EmailMessageSendGridHeadersData'},
            'data': ('django.db.models.fields.TextField', [], {}),
            'email_message': ('django.db.models.fields.related.OneToOneField', [], {'related_name': "'sendgrid_headers'", 'unique': 'True', 'primary_key': 'True', 'to': "orm['sendgrid.EmailMessage']"})
        },
        'sendgrid.emailmessagesubjectdata': {
            'Meta': {'object_name': 'EmailMessageSubjectData'},
            'data': ('django.db.models.fields.TextField', [], {}),
            'email_message': ('django.db.models.fields.related.OneToOneField', [], {'related_name': "'subject'", 'unique': 'True', 'primary_key': 'True', 'to': "orm['sendgrid.EmailMessage']"})
        },
        'sendgrid.emailmessagetodata': {
            'Meta': {'object_name': 'EmailMessageToData'},
            'data': ('django.db.models.fields.TextField', [], {}),
            'email_message': ('django.db.models.fields.related.OneToOneField', [], {'related_name': "'to'", 'unique': 'True', 'primary_key': 'True', 'to': "orm['sendgrid.EmailMessage']"})
        }
    }

    complete_apps = ['sendgrid']
########NEW FILE########
__FILENAME__ = 0003_auto__add_category
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'Category'
        db.create_table('sendgrid_category', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(unique=True, max_length=150)),
            ('creation_time', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('last_modified_time', self.gf('django.db.models.fields.DateTimeField')(auto_now=True, blank=True)),
        ))
        db.send_create_signal('sendgrid', ['Category'])

        # Adding M2M table for field categories on 'EmailMessage'
        db.create_table('sendgrid_emailmessage_categories', (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('emailmessage', models.ForeignKey(orm['sendgrid.emailmessage'], null=False)),
            ('category', models.ForeignKey(orm['sendgrid.category'], null=False))
        ))
        db.create_unique('sendgrid_emailmessage_categories', ['emailmessage_id', 'category_id'])


    def backwards(self, orm):
        # Deleting model 'Category'
        db.delete_table('sendgrid_category')

        # Removing M2M table for field categories on 'EmailMessage'
        db.delete_table('sendgrid_emailmessage_categories')


    models = {
        'sendgrid.category': {
            'Meta': {'object_name': 'Category'},
            'creation_time': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_modified_time': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '150'})
        },
        'sendgrid.emailmessage': {
            'Meta': {'object_name': 'EmailMessage'},
            'categories': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['sendgrid.Category']", 'symmetrical': 'False'}),
            'category': ('django.db.models.fields.CharField', [], {'max_length': '150', 'null': 'True', 'blank': 'True'}),
            'creation_time': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'from_email': ('django.db.models.fields.CharField', [], {'max_length': '254'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_modified_time': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'message_id': ('django.db.models.fields.CharField', [], {'max_length': '36', 'unique': 'True', 'null': 'True', 'blank': 'True'}),
            'response': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'to_email': ('django.db.models.fields.CharField', [], {'max_length': '254'})
        },
        'sendgrid.emailmessageattachmentsdata': {
            'Meta': {'object_name': 'EmailMessageAttachmentsData'},
            'data': ('django.db.models.fields.TextField', [], {}),
            'email_message': ('django.db.models.fields.related.OneToOneField', [], {'related_name': "'attachments'", 'unique': 'True', 'primary_key': 'True', 'to': "orm['sendgrid.EmailMessage']"})
        },
        'sendgrid.emailmessagebccdata': {
            'Meta': {'object_name': 'EmailMessageBccData'},
            'data': ('django.db.models.fields.TextField', [], {}),
            'email_message': ('django.db.models.fields.related.OneToOneField', [], {'related_name': "'bcc'", 'unique': 'True', 'primary_key': 'True', 'to': "orm['sendgrid.EmailMessage']"})
        },
        'sendgrid.emailmessagebodydata': {
            'Meta': {'object_name': 'EmailMessageBodyData'},
            'data': ('django.db.models.fields.TextField', [], {}),
            'email_message': ('django.db.models.fields.related.OneToOneField', [], {'related_name': "'body'", 'unique': 'True', 'primary_key': 'True', 'to': "orm['sendgrid.EmailMessage']"})
        },
        'sendgrid.emailmessageccdata': {
            'Meta': {'object_name': 'EmailMessageCcData'},
            'data': ('django.db.models.fields.TextField', [], {}),
            'email_message': ('django.db.models.fields.related.OneToOneField', [], {'related_name': "'cc'", 'unique': 'True', 'primary_key': 'True', 'to': "orm['sendgrid.EmailMessage']"})
        },
        'sendgrid.emailmessageextraheadersdata': {
            'Meta': {'object_name': 'EmailMessageExtraHeadersData'},
            'data': ('django.db.models.fields.TextField', [], {}),
            'email_message': ('django.db.models.fields.related.OneToOneField', [], {'related_name': "'extra_headers'", 'unique': 'True', 'primary_key': 'True', 'to': "orm['sendgrid.EmailMessage']"})
        },
        'sendgrid.emailmessagesendgridheadersdata': {
            'Meta': {'object_name': 'EmailMessageSendGridHeadersData'},
            'data': ('django.db.models.fields.TextField', [], {}),
            'email_message': ('django.db.models.fields.related.OneToOneField', [], {'related_name': "'sendgrid_headers'", 'unique': 'True', 'primary_key': 'True', 'to': "orm['sendgrid.EmailMessage']"})
        },
        'sendgrid.emailmessagesubjectdata': {
            'Meta': {'object_name': 'EmailMessageSubjectData'},
            'data': ('django.db.models.fields.TextField', [], {}),
            'email_message': ('django.db.models.fields.related.OneToOneField', [], {'related_name': "'subject'", 'unique': 'True', 'primary_key': 'True', 'to': "orm['sendgrid.EmailMessage']"})
        },
        'sendgrid.emailmessagetodata': {
            'Meta': {'object_name': 'EmailMessageToData'},
            'data': ('django.db.models.fields.TextField', [], {}),
            'email_message': ('django.db.models.fields.related.OneToOneField', [], {'related_name': "'to'", 'unique': 'True', 'primary_key': 'True', 'to': "orm['sendgrid.EmailMessage']"})
        }
    }

    complete_apps = ['sendgrid']
########NEW FILE########
__FILENAME__ = 0004_auto__add_uniqueargument__add_argument
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'UniqueArgument'
        db.create_table('sendgrid_uniqueargument', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('argument', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['sendgrid.Argument'])),
            ('email_message', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['sendgrid.EmailMessage'])),
            ('data', self.gf('django.db.models.fields.CharField')(max_length=255)),
            ('creation_time', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('last_modified_time', self.gf('django.db.models.fields.DateTimeField')(auto_now=True, blank=True)),
        ))
        db.send_create_signal('sendgrid', ['UniqueArgument'])

        # Adding model 'Argument'
        db.create_table('sendgrid_argument', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('key', self.gf('django.db.models.fields.CharField')(max_length=255)),
            ('data_type', self.gf('django.db.models.fields.IntegerField')(default=0)),
            ('creation_time', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('last_modified_time', self.gf('django.db.models.fields.DateTimeField')(auto_now=True, blank=True)),
        ))
        db.send_create_signal('sendgrid', ['Argument'])


    def backwards(self, orm):
        # Deleting model 'UniqueArgument'
        db.delete_table('sendgrid_uniqueargument')

        # Deleting model 'Argument'
        db.delete_table('sendgrid_argument')


    models = {
        'sendgrid.argument': {
            'Meta': {'object_name': 'Argument'},
            'creation_time': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'data_type': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'key': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'last_modified_time': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'})
        },
        'sendgrid.category': {
            'Meta': {'object_name': 'Category'},
            'creation_time': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_modified_time': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '150'})
        },
        'sendgrid.emailmessage': {
            'Meta': {'object_name': 'EmailMessage'},
            'arguments': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['sendgrid.Argument']", 'through': "orm['sendgrid.UniqueArgument']", 'symmetrical': 'False'}),
            'categories': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['sendgrid.Category']", 'symmetrical': 'False'}),
            'category': ('django.db.models.fields.CharField', [], {'max_length': '150', 'null': 'True', 'blank': 'True'}),
            'creation_time': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'from_email': ('django.db.models.fields.CharField', [], {'max_length': '254'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_modified_time': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'message_id': ('django.db.models.fields.CharField', [], {'max_length': '36', 'unique': 'True', 'null': 'True', 'blank': 'True'}),
            'response': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'to_email': ('django.db.models.fields.CharField', [], {'max_length': '254'})
        },
        'sendgrid.emailmessageattachmentsdata': {
            'Meta': {'object_name': 'EmailMessageAttachmentsData'},
            'data': ('django.db.models.fields.TextField', [], {}),
            'email_message': ('django.db.models.fields.related.OneToOneField', [], {'related_name': "'attachments'", 'unique': 'True', 'primary_key': 'True', 'to': "orm['sendgrid.EmailMessage']"})
        },
        'sendgrid.emailmessagebccdata': {
            'Meta': {'object_name': 'EmailMessageBccData'},
            'data': ('django.db.models.fields.TextField', [], {}),
            'email_message': ('django.db.models.fields.related.OneToOneField', [], {'related_name': "'bcc'", 'unique': 'True', 'primary_key': 'True', 'to': "orm['sendgrid.EmailMessage']"})
        },
        'sendgrid.emailmessagebodydata': {
            'Meta': {'object_name': 'EmailMessageBodyData'},
            'data': ('django.db.models.fields.TextField', [], {}),
            'email_message': ('django.db.models.fields.related.OneToOneField', [], {'related_name': "'body'", 'unique': 'True', 'primary_key': 'True', 'to': "orm['sendgrid.EmailMessage']"})
        },
        'sendgrid.emailmessageccdata': {
            'Meta': {'object_name': 'EmailMessageCcData'},
            'data': ('django.db.models.fields.TextField', [], {}),
            'email_message': ('django.db.models.fields.related.OneToOneField', [], {'related_name': "'cc'", 'unique': 'True', 'primary_key': 'True', 'to': "orm['sendgrid.EmailMessage']"})
        },
        'sendgrid.emailmessageextraheadersdata': {
            'Meta': {'object_name': 'EmailMessageExtraHeadersData'},
            'data': ('django.db.models.fields.TextField', [], {}),
            'email_message': ('django.db.models.fields.related.OneToOneField', [], {'related_name': "'extra_headers'", 'unique': 'True', 'primary_key': 'True', 'to': "orm['sendgrid.EmailMessage']"})
        },
        'sendgrid.emailmessagesendgridheadersdata': {
            'Meta': {'object_name': 'EmailMessageSendGridHeadersData'},
            'data': ('django.db.models.fields.TextField', [], {}),
            'email_message': ('django.db.models.fields.related.OneToOneField', [], {'related_name': "'sendgrid_headers'", 'unique': 'True', 'primary_key': 'True', 'to': "orm['sendgrid.EmailMessage']"})
        },
        'sendgrid.emailmessagesubjectdata': {
            'Meta': {'object_name': 'EmailMessageSubjectData'},
            'data': ('django.db.models.fields.TextField', [], {}),
            'email_message': ('django.db.models.fields.related.OneToOneField', [], {'related_name': "'subject'", 'unique': 'True', 'primary_key': 'True', 'to': "orm['sendgrid.EmailMessage']"})
        },
        'sendgrid.emailmessagetodata': {
            'Meta': {'object_name': 'EmailMessageToData'},
            'data': ('django.db.models.fields.TextField', [], {}),
            'email_message': ('django.db.models.fields.related.OneToOneField', [], {'related_name': "'to'", 'unique': 'True', 'primary_key': 'True', 'to': "orm['sendgrid.EmailMessage']"})
        },
        'sendgrid.uniqueargument': {
            'Meta': {'object_name': 'UniqueArgument'},
            'argument': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['sendgrid.Argument']"}),
            'creation_time': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'data': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'email_message': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['sendgrid.EmailMessage']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_modified_time': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'})
        }
    }

    complete_apps = ['sendgrid']
########NEW FILE########
__FILENAME__ = 0005_auto__add_eventtype__add_event
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'EventType'
        db.create_table('sendgrid_eventtype', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(unique=True, max_length=128)),
        ))
        db.send_create_signal('sendgrid', ['EventType'])

        # Adding model 'Event'
        db.create_table('sendgrid_event', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('email_message', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['sendgrid.EmailMessage'])),
            ('email', self.gf('django.db.models.fields.EmailField')(max_length=75)),
            ('type', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['sendgrid.EventType'])),
            ('creation_time', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
            ('last_modified_time', self.gf('django.db.models.fields.DateTimeField')(auto_now=True, blank=True)),
        ))
        db.send_create_signal('sendgrid', ['Event'])


    def backwards(self, orm):
        # Deleting model 'EventType'
        db.delete_table('sendgrid_eventtype')

        # Deleting model 'Event'
        db.delete_table('sendgrid_event')


    models = {
        'sendgrid.argument': {
            'Meta': {'object_name': 'Argument'},
            'creation_time': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'data_type': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'key': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'last_modified_time': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'})
        },
        'sendgrid.category': {
            'Meta': {'object_name': 'Category'},
            'creation_time': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_modified_time': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '150'})
        },
        'sendgrid.emailmessage': {
            'Meta': {'object_name': 'EmailMessage'},
            'arguments': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['sendgrid.Argument']", 'through': "orm['sendgrid.UniqueArgument']", 'symmetrical': 'False'}),
            'categories': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['sendgrid.Category']", 'symmetrical': 'False'}),
            'category': ('django.db.models.fields.CharField', [], {'max_length': '150', 'null': 'True', 'blank': 'True'}),
            'creation_time': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'from_email': ('django.db.models.fields.CharField', [], {'max_length': '254'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_modified_time': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'message_id': ('django.db.models.fields.CharField', [], {'max_length': '36', 'unique': 'True', 'null': 'True', 'blank': 'True'}),
            'response': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'to_email': ('django.db.models.fields.CharField', [], {'max_length': '254'})
        },
        'sendgrid.emailmessageattachmentsdata': {
            'Meta': {'object_name': 'EmailMessageAttachmentsData'},
            'data': ('django.db.models.fields.TextField', [], {}),
            'email_message': ('django.db.models.fields.related.OneToOneField', [], {'related_name': "'attachments'", 'unique': 'True', 'primary_key': 'True', 'to': "orm['sendgrid.EmailMessage']"})
        },
        'sendgrid.emailmessagebccdata': {
            'Meta': {'object_name': 'EmailMessageBccData'},
            'data': ('django.db.models.fields.TextField', [], {}),
            'email_message': ('django.db.models.fields.related.OneToOneField', [], {'related_name': "'bcc'", 'unique': 'True', 'primary_key': 'True', 'to': "orm['sendgrid.EmailMessage']"})
        },
        'sendgrid.emailmessagebodydata': {
            'Meta': {'object_name': 'EmailMessageBodyData'},
            'data': ('django.db.models.fields.TextField', [], {}),
            'email_message': ('django.db.models.fields.related.OneToOneField', [], {'related_name': "'body'", 'unique': 'True', 'primary_key': 'True', 'to': "orm['sendgrid.EmailMessage']"})
        },
        'sendgrid.emailmessageccdata': {
            'Meta': {'object_name': 'EmailMessageCcData'},
            'data': ('django.db.models.fields.TextField', [], {}),
            'email_message': ('django.db.models.fields.related.OneToOneField', [], {'related_name': "'cc'", 'unique': 'True', 'primary_key': 'True', 'to': "orm['sendgrid.EmailMessage']"})
        },
        'sendgrid.emailmessageextraheadersdata': {
            'Meta': {'object_name': 'EmailMessageExtraHeadersData'},
            'data': ('django.db.models.fields.TextField', [], {}),
            'email_message': ('django.db.models.fields.related.OneToOneField', [], {'related_name': "'extra_headers'", 'unique': 'True', 'primary_key': 'True', 'to': "orm['sendgrid.EmailMessage']"})
        },
        'sendgrid.emailmessagesendgridheadersdata': {
            'Meta': {'object_name': 'EmailMessageSendGridHeadersData'},
            'data': ('django.db.models.fields.TextField', [], {}),
            'email_message': ('django.db.models.fields.related.OneToOneField', [], {'related_name': "'sendgrid_headers'", 'unique': 'True', 'primary_key': 'True', 'to': "orm['sendgrid.EmailMessage']"})
        },
        'sendgrid.emailmessagesubjectdata': {
            'Meta': {'object_name': 'EmailMessageSubjectData'},
            'data': ('django.db.models.fields.TextField', [], {}),
            'email_message': ('django.db.models.fields.related.OneToOneField', [], {'related_name': "'subject'", 'unique': 'True', 'primary_key': 'True', 'to': "orm['sendgrid.EmailMessage']"})
        },
        'sendgrid.emailmessagetodata': {
            'Meta': {'object_name': 'EmailMessageToData'},
            'data': ('django.db.models.fields.TextField', [], {}),
            'email_message': ('django.db.models.fields.related.OneToOneField', [], {'related_name': "'to'", 'unique': 'True', 'primary_key': 'True', 'to': "orm['sendgrid.EmailMessage']"})
        },
        'sendgrid.event': {
            'Meta': {'object_name': 'Event'},
            'creation_time': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75'}),
            'email_message': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['sendgrid.EmailMessage']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_modified_time': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['sendgrid.EventType']"})
        },
        'sendgrid.eventtype': {
            'Meta': {'object_name': 'EventType'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '128'})
        },
        'sendgrid.uniqueargument': {
            'Meta': {'object_name': 'UniqueArgument'},
            'argument': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['sendgrid.Argument']"}),
            'creation_time': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'data': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'email_message': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['sendgrid.EmailMessage']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_modified_time': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'})
        }
    }

    complete_apps = ['sendgrid']
########NEW FILE########
__FILENAME__ = 0006_change_event_type_column_name
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        db.rename_column('sendgrid_event','type_id','event_type_id')

    def backwards(self, orm):
        db.rename_column('sendgrid_event','event_type_id','type_id')

    models = {
        'sendgrid.argument': {
            'Meta': {'object_name': 'Argument'},
            'creation_time': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'data_type': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'key': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'last_modified_time': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'})
        },
        'sendgrid.category': {
            'Meta': {'object_name': 'Category'},
            'creation_time': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_modified_time': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '150'})
        },
        'sendgrid.emailmessage': {
            'Meta': {'object_name': 'EmailMessage'},
            'arguments': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['sendgrid.Argument']", 'through': "orm['sendgrid.UniqueArgument']", 'symmetrical': 'False'}),
            'categories': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['sendgrid.Category']", 'symmetrical': 'False'}),
            'category': ('django.db.models.fields.CharField', [], {'max_length': '150', 'null': 'True', 'blank': 'True'}),
            'creation_time': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'from_email': ('django.db.models.fields.CharField', [], {'max_length': '254'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_modified_time': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'message_id': ('django.db.models.fields.CharField', [], {'max_length': '36', 'unique': 'True', 'null': 'True', 'blank': 'True'}),
            'response': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'to_email': ('django.db.models.fields.CharField', [], {'max_length': '254'})
        },
        'sendgrid.emailmessageattachmentsdata': {
            'Meta': {'object_name': 'EmailMessageAttachmentsData'},
            'data': ('django.db.models.fields.TextField', [], {}),
            'email_message': ('django.db.models.fields.related.OneToOneField', [], {'related_name': "'attachments'", 'unique': 'True', 'primary_key': 'True', 'to': "orm['sendgrid.EmailMessage']"})
        },
        'sendgrid.emailmessagebccdata': {
            'Meta': {'object_name': 'EmailMessageBccData'},
            'data': ('django.db.models.fields.TextField', [], {}),
            'email_message': ('django.db.models.fields.related.OneToOneField', [], {'related_name': "'bcc'", 'unique': 'True', 'primary_key': 'True', 'to': "orm['sendgrid.EmailMessage']"})
        },
        'sendgrid.emailmessagebodydata': {
            'Meta': {'object_name': 'EmailMessageBodyData'},
            'data': ('django.db.models.fields.TextField', [], {}),
            'email_message': ('django.db.models.fields.related.OneToOneField', [], {'related_name': "'body'", 'unique': 'True', 'primary_key': 'True', 'to': "orm['sendgrid.EmailMessage']"})
        },
        'sendgrid.emailmessageccdata': {
            'Meta': {'object_name': 'EmailMessageCcData'},
            'data': ('django.db.models.fields.TextField', [], {}),
            'email_message': ('django.db.models.fields.related.OneToOneField', [], {'related_name': "'cc'", 'unique': 'True', 'primary_key': 'True', 'to': "orm['sendgrid.EmailMessage']"})
        },
        'sendgrid.emailmessageextraheadersdata': {
            'Meta': {'object_name': 'EmailMessageExtraHeadersData'},
            'data': ('django.db.models.fields.TextField', [], {}),
            'email_message': ('django.db.models.fields.related.OneToOneField', [], {'related_name': "'extra_headers'", 'unique': 'True', 'primary_key': 'True', 'to': "orm['sendgrid.EmailMessage']"})
        },
        'sendgrid.emailmessagesendgridheadersdata': {
            'Meta': {'object_name': 'EmailMessageSendGridHeadersData'},
            'data': ('django.db.models.fields.TextField', [], {}),
            'email_message': ('django.db.models.fields.related.OneToOneField', [], {'related_name': "'sendgrid_headers'", 'unique': 'True', 'primary_key': 'True', 'to': "orm['sendgrid.EmailMessage']"})
        },
        'sendgrid.emailmessagesubjectdata': {
            'Meta': {'object_name': 'EmailMessageSubjectData'},
            'data': ('django.db.models.fields.TextField', [], {}),
            'email_message': ('django.db.models.fields.related.OneToOneField', [], {'related_name': "'subject'", 'unique': 'True', 'primary_key': 'True', 'to': "orm['sendgrid.EmailMessage']"})
        },
        'sendgrid.emailmessagetodata': {
            'Meta': {'object_name': 'EmailMessageToData'},
            'data': ('django.db.models.fields.TextField', [], {}),
            'email_message': ('django.db.models.fields.related.OneToOneField', [], {'related_name': "'to'", 'unique': 'True', 'primary_key': 'True', 'to': "orm['sendgrid.EmailMessage']"})
        },
        'sendgrid.event': {
            'Meta': {'object_name': 'Event'},
            'creation_time': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75'}),
            'email_message': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['sendgrid.EmailMessage']"}),
            'event_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['sendgrid.EventType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_modified_time': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'})
        },
        'sendgrid.eventtype': {
            'Meta': {'object_name': 'EventType'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '128'})
        },
        'sendgrid.uniqueargument': {
            'Meta': {'object_name': 'UniqueArgument'},
            'argument': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['sendgrid.Argument']"}),
            'creation_time': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'data': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'email_message': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['sendgrid.EmailMessage']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_modified_time': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'})
        }
    }

    complete_apps = ['sendgrid']
########NEW FILE########
__FILENAME__ = 0007_auto__add_bouncetype__add_droppedevent__add_bouncereason__add_clickurl
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'BounceType'
        db.create_table('sendgrid_bouncetype', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('type', self.gf('django.db.models.fields.CharField')(unique=True, max_length=32)),
        ))
        db.send_create_signal('sendgrid', ['BounceType'])

        # Adding model 'DroppedEvent'
        db.create_table('sendgrid_droppedevent', (
            ('event_ptr', self.gf('django.db.models.fields.related.OneToOneField')(to=orm['sendgrid.Event'], unique=True, primary_key=True)),
            ('reason', self.gf('django.db.models.fields.CharField')(max_length=255)),
        ))
        db.send_create_signal('sendgrid', ['DroppedEvent'])

        # Adding model 'BounceReason'
        db.create_table('sendgrid_bouncereason', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('reason', self.gf('django.db.models.fields.TextField')()),
        ))
        db.send_create_signal('sendgrid', ['BounceReason'])

        # Adding model 'ClickUrl'
        db.create_table('sendgrid_clickurl', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('url', self.gf('django.db.models.fields.TextField')()),
        ))
        db.send_create_signal('sendgrid', ['ClickUrl'])

        # Adding model 'DeferredEvent'
        db.create_table('sendgrid_deferredevent', (
            ('event_ptr', self.gf('django.db.models.fields.related.OneToOneField')(to=orm['sendgrid.Event'], unique=True, primary_key=True)),
            ('response', self.gf('django.db.models.fields.TextField')()),
            ('attempt', self.gf('django.db.models.fields.IntegerField')()),
        ))
        db.send_create_signal('sendgrid', ['DeferredEvent'])

        # Adding model 'DeliverredEvent'
        db.create_table('sendgrid_deliverredevent', (
            ('event_ptr', self.gf('django.db.models.fields.related.OneToOneField')(to=orm['sendgrid.Event'], unique=True, primary_key=True)),
            ('response', self.gf('django.db.models.fields.TextField')()),
        ))
        db.send_create_signal('sendgrid', ['DeliverredEvent'])

        # Adding model 'BounceEvent'
        db.create_table('sendgrid_bounceevent', (
            ('event_ptr', self.gf('django.db.models.fields.related.OneToOneField')(to=orm['sendgrid.Event'], unique=True, primary_key=True)),
            ('status', self.gf('django.db.models.fields.CharField')(max_length=16)),
            ('bounce_reason', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['sendgrid.BounceReason'])),
            ('bounce_type', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['sendgrid.BounceType'])),
        ))
        db.send_create_signal('sendgrid', ['BounceEvent'])

        # Adding model 'ClickEvent'
        db.create_table('sendgrid_clickevent', (
            ('event_ptr', self.gf('django.db.models.fields.related.OneToOneField')(to=orm['sendgrid.Event'], unique=True, primary_key=True)),
            ('click_url', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['sendgrid.ClickUrl'])),
        ))
        db.send_create_signal('sendgrid', ['ClickEvent'])


    def backwards(self, orm):
        # Deleting model 'BounceType'
        db.delete_table('sendgrid_bouncetype')

        # Deleting model 'DroppedEvent'
        db.delete_table('sendgrid_droppedevent')

        # Deleting model 'BounceReason'
        db.delete_table('sendgrid_bouncereason')

        # Deleting model 'ClickUrl'
        db.delete_table('sendgrid_clickurl')

        # Deleting model 'DeferredEvent'
        db.delete_table('sendgrid_deferredevent')

        # Deleting model 'DeliverredEvent'
        db.delete_table('sendgrid_deliverredevent')

        # Deleting model 'BounceEvent'
        db.delete_table('sendgrid_bounceevent')

        # Deleting model 'ClickEvent'
        db.delete_table('sendgrid_clickevent')


    models = {
        'sendgrid.argument': {
            'Meta': {'object_name': 'Argument'},
            'creation_time': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'data_type': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'key': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'last_modified_time': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'})
        },
        'sendgrid.bounceevent': {
            'Meta': {'object_name': 'BounceEvent', '_ormbases': ['sendgrid.Event']},
            'bounce_reason': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['sendgrid.BounceReason']"}),
            'bounce_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['sendgrid.BounceType']"}),
            'event_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['sendgrid.Event']", 'unique': 'True', 'primary_key': 'True'}),
            'status': ('django.db.models.fields.CharField', [], {'max_length': '16'})
        },
        'sendgrid.bouncereason': {
            'Meta': {'object_name': 'BounceReason'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'reason': ('django.db.models.fields.TextField', [], {})
        },
        'sendgrid.bouncetype': {
            'Meta': {'object_name': 'BounceType'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'type': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '32'})
        },
        'sendgrid.category': {
            'Meta': {'object_name': 'Category'},
            'creation_time': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_modified_time': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '150'})
        },
        'sendgrid.clickevent': {
            'Meta': {'object_name': 'ClickEvent', '_ormbases': ['sendgrid.Event']},
            'click_url': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['sendgrid.ClickUrl']"}),
            'event_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['sendgrid.Event']", 'unique': 'True', 'primary_key': 'True'})
        },
        'sendgrid.clickurl': {
            'Meta': {'object_name': 'ClickUrl'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'url': ('django.db.models.fields.TextField', [], {})
        },
        'sendgrid.deferredevent': {
            'Meta': {'object_name': 'DeferredEvent', '_ormbases': ['sendgrid.Event']},
            'attempt': ('django.db.models.fields.IntegerField', [], {}),
            'event_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['sendgrid.Event']", 'unique': 'True', 'primary_key': 'True'}),
            'response': ('django.db.models.fields.TextField', [], {})
        },
        'sendgrid.deliverredevent': {
            'Meta': {'object_name': 'DeliverredEvent', '_ormbases': ['sendgrid.Event']},
            'event_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['sendgrid.Event']", 'unique': 'True', 'primary_key': 'True'}),
            'response': ('django.db.models.fields.TextField', [], {})
        },
        'sendgrid.droppedevent': {
            'Meta': {'object_name': 'DroppedEvent', '_ormbases': ['sendgrid.Event']},
            'event_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['sendgrid.Event']", 'unique': 'True', 'primary_key': 'True'}),
            'reason': ('django.db.models.fields.CharField', [], {'max_length': '255'})
        },
        'sendgrid.emailmessage': {
            'Meta': {'object_name': 'EmailMessage'},
            'arguments': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['sendgrid.Argument']", 'through': "orm['sendgrid.UniqueArgument']", 'symmetrical': 'False'}),
            'categories': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['sendgrid.Category']", 'symmetrical': 'False'}),
            'category': ('django.db.models.fields.CharField', [], {'max_length': '150', 'null': 'True', 'blank': 'True'}),
            'creation_time': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'from_email': ('django.db.models.fields.CharField', [], {'max_length': '254'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_modified_time': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'message_id': ('django.db.models.fields.CharField', [], {'max_length': '36', 'unique': 'True', 'null': 'True', 'blank': 'True'}),
            'response': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'to_email': ('django.db.models.fields.CharField', [], {'max_length': '254'})
        },
        'sendgrid.emailmessageattachmentsdata': {
            'Meta': {'object_name': 'EmailMessageAttachmentsData'},
            'data': ('django.db.models.fields.TextField', [], {}),
            'email_message': ('django.db.models.fields.related.OneToOneField', [], {'related_name': "'attachments'", 'unique': 'True', 'primary_key': 'True', 'to': "orm['sendgrid.EmailMessage']"})
        },
        'sendgrid.emailmessagebccdata': {
            'Meta': {'object_name': 'EmailMessageBccData'},
            'data': ('django.db.models.fields.TextField', [], {}),
            'email_message': ('django.db.models.fields.related.OneToOneField', [], {'related_name': "'bcc'", 'unique': 'True', 'primary_key': 'True', 'to': "orm['sendgrid.EmailMessage']"})
        },
        'sendgrid.emailmessagebodydata': {
            'Meta': {'object_name': 'EmailMessageBodyData'},
            'data': ('django.db.models.fields.TextField', [], {}),
            'email_message': ('django.db.models.fields.related.OneToOneField', [], {'related_name': "'body'", 'unique': 'True', 'primary_key': 'True', 'to': "orm['sendgrid.EmailMessage']"})
        },
        'sendgrid.emailmessageccdata': {
            'Meta': {'object_name': 'EmailMessageCcData'},
            'data': ('django.db.models.fields.TextField', [], {}),
            'email_message': ('django.db.models.fields.related.OneToOneField', [], {'related_name': "'cc'", 'unique': 'True', 'primary_key': 'True', 'to': "orm['sendgrid.EmailMessage']"})
        },
        'sendgrid.emailmessageextraheadersdata': {
            'Meta': {'object_name': 'EmailMessageExtraHeadersData'},
            'data': ('django.db.models.fields.TextField', [], {}),
            'email_message': ('django.db.models.fields.related.OneToOneField', [], {'related_name': "'extra_headers'", 'unique': 'True', 'primary_key': 'True', 'to': "orm['sendgrid.EmailMessage']"})
        },
        'sendgrid.emailmessagesendgridheadersdata': {
            'Meta': {'object_name': 'EmailMessageSendGridHeadersData'},
            'data': ('django.db.models.fields.TextField', [], {}),
            'email_message': ('django.db.models.fields.related.OneToOneField', [], {'related_name': "'sendgrid_headers'", 'unique': 'True', 'primary_key': 'True', 'to': "orm['sendgrid.EmailMessage']"})
        },
        'sendgrid.emailmessagesubjectdata': {
            'Meta': {'object_name': 'EmailMessageSubjectData'},
            'data': ('django.db.models.fields.TextField', [], {}),
            'email_message': ('django.db.models.fields.related.OneToOneField', [], {'related_name': "'subject'", 'unique': 'True', 'primary_key': 'True', 'to': "orm['sendgrid.EmailMessage']"})
        },
        'sendgrid.emailmessagetodata': {
            'Meta': {'object_name': 'EmailMessageToData'},
            'data': ('django.db.models.fields.TextField', [], {}),
            'email_message': ('django.db.models.fields.related.OneToOneField', [], {'related_name': "'to'", 'unique': 'True', 'primary_key': 'True', 'to': "orm['sendgrid.EmailMessage']"})
        },
        'sendgrid.event': {
            'Meta': {'object_name': 'Event'},
            'creation_time': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75'}),
            'email_message': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['sendgrid.EmailMessage']"}),
            'event_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['sendgrid.EventType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_modified_time': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'})
        },
        'sendgrid.eventtype': {
            'Meta': {'object_name': 'EventType'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '128'})
        },
        'sendgrid.uniqueargument': {
            'Meta': {'object_name': 'UniqueArgument'},
            'argument': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['sendgrid.Argument']"}),
            'creation_time': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'data': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'email_message': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['sendgrid.EmailMessage']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_modified_time': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'})
        }
    }

    complete_apps = ['sendgrid']
########NEW FILE########
__FILENAME__ = 0008_auto__chg_field_bounceevent_bounce_type__chg_field_bounceevent_bounce_
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):

        # Changing field 'BounceEvent.bounce_type'
        db.alter_column('sendgrid_bounceevent', 'bounce_type_id', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['sendgrid.BounceType'], null=True))

        # Changing field 'BounceEvent.bounce_reason'
        db.alter_column('sendgrid_bounceevent', 'bounce_reason_id', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['sendgrid.BounceReason'], null=True))

    def backwards(self, orm):

        # User chose to not deal with backwards NULL issues for 'BounceEvent.bounce_type'
        raise RuntimeError("Cannot reverse this migration. 'BounceEvent.bounce_type' and its values cannot be restored.")

        # User chose to not deal with backwards NULL issues for 'BounceEvent.bounce_reason'
        raise RuntimeError("Cannot reverse this migration. 'BounceEvent.bounce_reason' and its values cannot be restored.")

    models = {
        'sendgrid.argument': {
            'Meta': {'object_name': 'Argument'},
            'creation_time': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'data_type': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'key': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'last_modified_time': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'})
        },
        'sendgrid.bounceevent': {
            'Meta': {'object_name': 'BounceEvent', '_ormbases': ['sendgrid.Event']},
            'bounce_reason': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['sendgrid.BounceReason']", 'null': 'True'}),
            'bounce_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['sendgrid.BounceType']", 'null': 'True'}),
            'event_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['sendgrid.Event']", 'unique': 'True', 'primary_key': 'True'}),
            'status': ('django.db.models.fields.CharField', [], {'max_length': '16'})
        },
        'sendgrid.bouncereason': {
            'Meta': {'object_name': 'BounceReason'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'reason': ('django.db.models.fields.TextField', [], {})
        },
        'sendgrid.bouncetype': {
            'Meta': {'object_name': 'BounceType'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'type': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '32'})
        },
        'sendgrid.category': {
            'Meta': {'object_name': 'Category'},
            'creation_time': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_modified_time': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '150'})
        },
        'sendgrid.clickevent': {
            'Meta': {'object_name': 'ClickEvent', '_ormbases': ['sendgrid.Event']},
            'click_url': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['sendgrid.ClickUrl']"}),
            'event_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['sendgrid.Event']", 'unique': 'True', 'primary_key': 'True'})
        },
        'sendgrid.clickurl': {
            'Meta': {'object_name': 'ClickUrl'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'url': ('django.db.models.fields.TextField', [], {})
        },
        'sendgrid.deferredevent': {
            'Meta': {'object_name': 'DeferredEvent', '_ormbases': ['sendgrid.Event']},
            'attempt': ('django.db.models.fields.IntegerField', [], {}),
            'event_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['sendgrid.Event']", 'unique': 'True', 'primary_key': 'True'}),
            'response': ('django.db.models.fields.TextField', [], {})
        },
        'sendgrid.deliverredevent': {
            'Meta': {'object_name': 'DeliverredEvent', '_ormbases': ['sendgrid.Event']},
            'event_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['sendgrid.Event']", 'unique': 'True', 'primary_key': 'True'}),
            'response': ('django.db.models.fields.TextField', [], {})
        },
        'sendgrid.droppedevent': {
            'Meta': {'object_name': 'DroppedEvent', '_ormbases': ['sendgrid.Event']},
            'event_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['sendgrid.Event']", 'unique': 'True', 'primary_key': 'True'}),
            'reason': ('django.db.models.fields.CharField', [], {'max_length': '255'})
        },
        'sendgrid.emailmessage': {
            'Meta': {'object_name': 'EmailMessage'},
            'arguments': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['sendgrid.Argument']", 'through': "orm['sendgrid.UniqueArgument']", 'symmetrical': 'False'}),
            'categories': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['sendgrid.Category']", 'symmetrical': 'False'}),
            'category': ('django.db.models.fields.CharField', [], {'max_length': '150', 'null': 'True', 'blank': 'True'}),
            'creation_time': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'from_email': ('django.db.models.fields.CharField', [], {'max_length': '254'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_modified_time': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'message_id': ('django.db.models.fields.CharField', [], {'max_length': '36', 'unique': 'True', 'null': 'True', 'blank': 'True'}),
            'response': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'to_email': ('django.db.models.fields.CharField', [], {'max_length': '254'})
        },
        'sendgrid.emailmessageattachmentsdata': {
            'Meta': {'object_name': 'EmailMessageAttachmentsData'},
            'data': ('django.db.models.fields.TextField', [], {}),
            'email_message': ('django.db.models.fields.related.OneToOneField', [], {'related_name': "'attachments'", 'unique': 'True', 'primary_key': 'True', 'to': "orm['sendgrid.EmailMessage']"})
        },
        'sendgrid.emailmessagebccdata': {
            'Meta': {'object_name': 'EmailMessageBccData'},
            'data': ('django.db.models.fields.TextField', [], {}),
            'email_message': ('django.db.models.fields.related.OneToOneField', [], {'related_name': "'bcc'", 'unique': 'True', 'primary_key': 'True', 'to': "orm['sendgrid.EmailMessage']"})
        },
        'sendgrid.emailmessagebodydata': {
            'Meta': {'object_name': 'EmailMessageBodyData'},
            'data': ('django.db.models.fields.TextField', [], {}),
            'email_message': ('django.db.models.fields.related.OneToOneField', [], {'related_name': "'body'", 'unique': 'True', 'primary_key': 'True', 'to': "orm['sendgrid.EmailMessage']"})
        },
        'sendgrid.emailmessageccdata': {
            'Meta': {'object_name': 'EmailMessageCcData'},
            'data': ('django.db.models.fields.TextField', [], {}),
            'email_message': ('django.db.models.fields.related.OneToOneField', [], {'related_name': "'cc'", 'unique': 'True', 'primary_key': 'True', 'to': "orm['sendgrid.EmailMessage']"})
        },
        'sendgrid.emailmessageextraheadersdata': {
            'Meta': {'object_name': 'EmailMessageExtraHeadersData'},
            'data': ('django.db.models.fields.TextField', [], {}),
            'email_message': ('django.db.models.fields.related.OneToOneField', [], {'related_name': "'extra_headers'", 'unique': 'True', 'primary_key': 'True', 'to': "orm['sendgrid.EmailMessage']"})
        },
        'sendgrid.emailmessagesendgridheadersdata': {
            'Meta': {'object_name': 'EmailMessageSendGridHeadersData'},
            'data': ('django.db.models.fields.TextField', [], {}),
            'email_message': ('django.db.models.fields.related.OneToOneField', [], {'related_name': "'sendgrid_headers'", 'unique': 'True', 'primary_key': 'True', 'to': "orm['sendgrid.EmailMessage']"})
        },
        'sendgrid.emailmessagesubjectdata': {
            'Meta': {'object_name': 'EmailMessageSubjectData'},
            'data': ('django.db.models.fields.TextField', [], {}),
            'email_message': ('django.db.models.fields.related.OneToOneField', [], {'related_name': "'subject'", 'unique': 'True', 'primary_key': 'True', 'to': "orm['sendgrid.EmailMessage']"})
        },
        'sendgrid.emailmessagetodata': {
            'Meta': {'object_name': 'EmailMessageToData'},
            'data': ('django.db.models.fields.TextField', [], {}),
            'email_message': ('django.db.models.fields.related.OneToOneField', [], {'related_name': "'to'", 'unique': 'True', 'primary_key': 'True', 'to': "orm['sendgrid.EmailMessage']"})
        },
        'sendgrid.event': {
            'Meta': {'object_name': 'Event'},
            'creation_time': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75'}),
            'email_message': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['sendgrid.EmailMessage']"}),
            'event_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['sendgrid.EventType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_modified_time': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'timestamp': ('django.db.models.fields.DateTimeField', [], {'null': 'True'})
        },
        'sendgrid.eventtype': {
            'Meta': {'object_name': 'EventType'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '128'})
        },
        'sendgrid.uniqueargument': {
            'Meta': {'object_name': 'UniqueArgument'},
            'argument': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['sendgrid.Argument']"}),
            'creation_time': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'data': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'email_message': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['sendgrid.EmailMessage']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_modified_time': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'})
        }
    }

    complete_apps = ['sendgrid']
########NEW FILE########
__FILENAME__ = 0009_auto__add_field_event_timestamp
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding field 'Event.timestamp'
        db.add_column('sendgrid_event', 'timestamp',
                      self.gf('django.db.models.fields.DateTimeField')(null=True),
                      keep_default=False)


    def backwards(self, orm):
        # Deleting field 'Event.timestamp'
        db.delete_column('sendgrid_event', 'timestamp')


    models = {
        'sendgrid.argument': {
            'Meta': {'object_name': 'Argument'},
            'creation_time': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'data_type': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'key': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'last_modified_time': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'})
        },
        'sendgrid.bounceevent': {
            'Meta': {'object_name': 'BounceEvent', '_ormbases': ['sendgrid.Event']},
            'bounce_reason': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['sendgrid.BounceReason']"}),
            'bounce_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['sendgrid.BounceType']"}),
            'event_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['sendgrid.Event']", 'unique': 'True', 'primary_key': 'True'}),
            'status': ('django.db.models.fields.CharField', [], {'max_length': '16'})
        },
        'sendgrid.bouncereason': {
            'Meta': {'object_name': 'BounceReason'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'reason': ('django.db.models.fields.TextField', [], {})
        },
        'sendgrid.bouncetype': {
            'Meta': {'object_name': 'BounceType'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'type': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '32'})
        },
        'sendgrid.category': {
            'Meta': {'object_name': 'Category'},
            'creation_time': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_modified_time': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '150'})
        },
        'sendgrid.clickevent': {
            'Meta': {'object_name': 'ClickEvent', '_ormbases': ['sendgrid.Event']},
            'click_url': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['sendgrid.ClickUrl']"}),
            'event_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['sendgrid.Event']", 'unique': 'True', 'primary_key': 'True'})
        },
        'sendgrid.clickurl': {
            'Meta': {'object_name': 'ClickUrl'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'url': ('django.db.models.fields.TextField', [], {})
        },
        'sendgrid.deferredevent': {
            'Meta': {'object_name': 'DeferredEvent', '_ormbases': ['sendgrid.Event']},
            'attempt': ('django.db.models.fields.IntegerField', [], {}),
            'event_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['sendgrid.Event']", 'unique': 'True', 'primary_key': 'True'}),
            'response': ('django.db.models.fields.TextField', [], {})
        },
        'sendgrid.deliverredevent': {
            'Meta': {'object_name': 'DeliverredEvent', '_ormbases': ['sendgrid.Event']},
            'event_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['sendgrid.Event']", 'unique': 'True', 'primary_key': 'True'}),
            'response': ('django.db.models.fields.TextField', [], {})
        },
        'sendgrid.droppedevent': {
            'Meta': {'object_name': 'DroppedEvent', '_ormbases': ['sendgrid.Event']},
            'event_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['sendgrid.Event']", 'unique': 'True', 'primary_key': 'True'}),
            'reason': ('django.db.models.fields.CharField', [], {'max_length': '255'})
        },
        'sendgrid.emailmessage': {
            'Meta': {'object_name': 'EmailMessage'},
            'arguments': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['sendgrid.Argument']", 'through': "orm['sendgrid.UniqueArgument']", 'symmetrical': 'False'}),
            'categories': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['sendgrid.Category']", 'symmetrical': 'False'}),
            'category': ('django.db.models.fields.CharField', [], {'max_length': '150', 'null': 'True', 'blank': 'True'}),
            'creation_time': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'from_email': ('django.db.models.fields.CharField', [], {'max_length': '254'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_modified_time': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'message_id': ('django.db.models.fields.CharField', [], {'max_length': '36', 'unique': 'True', 'null': 'True', 'blank': 'True'}),
            'response': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'to_email': ('django.db.models.fields.CharField', [], {'max_length': '254'})
        },
        'sendgrid.emailmessageattachmentsdata': {
            'Meta': {'object_name': 'EmailMessageAttachmentsData'},
            'data': ('django.db.models.fields.TextField', [], {}),
            'email_message': ('django.db.models.fields.related.OneToOneField', [], {'related_name': "'attachments'", 'unique': 'True', 'primary_key': 'True', 'to': "orm['sendgrid.EmailMessage']"})
        },
        'sendgrid.emailmessagebccdata': {
            'Meta': {'object_name': 'EmailMessageBccData'},
            'data': ('django.db.models.fields.TextField', [], {}),
            'email_message': ('django.db.models.fields.related.OneToOneField', [], {'related_name': "'bcc'", 'unique': 'True', 'primary_key': 'True', 'to': "orm['sendgrid.EmailMessage']"})
        },
        'sendgrid.emailmessagebodydata': {
            'Meta': {'object_name': 'EmailMessageBodyData'},
            'data': ('django.db.models.fields.TextField', [], {}),
            'email_message': ('django.db.models.fields.related.OneToOneField', [], {'related_name': "'body'", 'unique': 'True', 'primary_key': 'True', 'to': "orm['sendgrid.EmailMessage']"})
        },
        'sendgrid.emailmessageccdata': {
            'Meta': {'object_name': 'EmailMessageCcData'},
            'data': ('django.db.models.fields.TextField', [], {}),
            'email_message': ('django.db.models.fields.related.OneToOneField', [], {'related_name': "'cc'", 'unique': 'True', 'primary_key': 'True', 'to': "orm['sendgrid.EmailMessage']"})
        },
        'sendgrid.emailmessageextraheadersdata': {
            'Meta': {'object_name': 'EmailMessageExtraHeadersData'},
            'data': ('django.db.models.fields.TextField', [], {}),
            'email_message': ('django.db.models.fields.related.OneToOneField', [], {'related_name': "'extra_headers'", 'unique': 'True', 'primary_key': 'True', 'to': "orm['sendgrid.EmailMessage']"})
        },
        'sendgrid.emailmessagesendgridheadersdata': {
            'Meta': {'object_name': 'EmailMessageSendGridHeadersData'},
            'data': ('django.db.models.fields.TextField', [], {}),
            'email_message': ('django.db.models.fields.related.OneToOneField', [], {'related_name': "'sendgrid_headers'", 'unique': 'True', 'primary_key': 'True', 'to': "orm['sendgrid.EmailMessage']"})
        },
        'sendgrid.emailmessagesubjectdata': {
            'Meta': {'object_name': 'EmailMessageSubjectData'},
            'data': ('django.db.models.fields.TextField', [], {}),
            'email_message': ('django.db.models.fields.related.OneToOneField', [], {'related_name': "'subject'", 'unique': 'True', 'primary_key': 'True', 'to': "orm['sendgrid.EmailMessage']"})
        },
        'sendgrid.emailmessagetodata': {
            'Meta': {'object_name': 'EmailMessageToData'},
            'data': ('django.db.models.fields.TextField', [], {}),
            'email_message': ('django.db.models.fields.related.OneToOneField', [], {'related_name': "'to'", 'unique': 'True', 'primary_key': 'True', 'to': "orm['sendgrid.EmailMessage']"})
        },
        'sendgrid.event': {
            'Meta': {'object_name': 'Event'},
            'creation_time': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75'}),
            'email_message': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['sendgrid.EmailMessage']"}),
            'event_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['sendgrid.EventType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_modified_time': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'timestamp': ('django.db.models.fields.DateTimeField', [], {'null': 'True'})
        },
        'sendgrid.eventtype': {
            'Meta': {'object_name': 'EventType'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '128'})
        },
        'sendgrid.uniqueargument': {
            'Meta': {'object_name': 'UniqueArgument'},
            'argument': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['sendgrid.Argument']"}),
            'creation_time': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'data': ('django.db.models.fields.CharField', [], {'max_length': '255'}),
            'email_message': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['sendgrid.EmailMessage']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'last_modified_time': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'})
        }
    }

    complete_apps = ['sendgrid']
########NEW FILE########
__FILENAME__ = mixins
from django.conf import settings
from django.utils import simplejson

from utils import add_unsubscribes
from utils import delete_unsubscribes
from utils import get_unsubscribes


SENDGRID_EMAIL_USERNAME = getattr(settings, "SENDGRID_EMAIL_USERNAME", None)
SENDGRID_EMAIL_PASSWORD = getattr(settings, "SENDGRID_EMAIL_PASSWORD", None)


class SendGridUserMixin:
	"""
	Adds SendGrid related convienence functions and properties to ``User`` objects.
	"""
	def is_unsubscribed(self):
		"""
		Returns True if the ``User``.``email`` belongs to the unsubscribe list.
		"""
		response = get_unsubscribes(email=self.email)
		results = simplejson.loads(response)
		return len(results) > 0
		
	def add_to_unsubscribes(self):
		"""
		Adds the ``User``.``email`` from the unsubscribe list.
		"""
		response = add_unsubscribes(email=self.email)
		result = simplejson.loads(response)
		return result
		
	def delete_from_unsubscribes(self):
		"""
		Removes the ``User``.``email`` from the unsubscribe list.
		"""
		response = delete_unsubscribes(email=self.email)
		result = simplejson.loads(response)
		return result

########NEW FILE########
__FILENAME__ = models
from __future__ import absolute_import

import datetime
import logging

from django.conf import settings
from django.core.exceptions import MultipleObjectsReturned
from django.db import models
from django.dispatch import receiver
from django.utils.translation import ugettext_lazy as _

from .signals import sendgrid_email_sent
from .signals import sendgrid_event_recieved
from sendgrid.constants import (
	ARGUMENT_DATA_TYPE_UNKNOWN,
	ARGUMENT_DATA_TYPE_BOOLEAN,
	ARGUMENT_DATA_TYPE_INTEGER,
	ARGUMENT_DATA_TYPE_FLOAT,
	ARGUMENT_DATA_TYPE_COMPLEX,
	ARGUMENT_DATA_TYPE_STRING,
	UNIQUE_ARGS_STORED_FOR_EVENTS_WITHOUT_MESSAGE_ID,
)
from sendgrid.signals import sendgrid_email_sent

MAX_CATEGORIES_PER_EMAIL_MESSAGE = 10

DEFAULT_SENDGRID_EMAIL_TRACKING_COMPONENTS = (
	"to",
	"cc",
	"bcc",
	"subject",
	"body",
	"sendgrid_headers",
	"extra_headers",
	"attachments",
)

SENDGRID_EMAIL_TRACKING = getattr(settings, "SENDGRID_USER_MIXIN_ENABLED", True)
SENDGRID_EMAIL_TRACKING_COMPONENTS = getattr(settings, "SENDGRID_USER_MIXIN_ENABLED", DEFAULT_SENDGRID_EMAIL_TRACKING_COMPONENTS)
SENDGRID_USER_MIXIN_ENABLED = getattr(settings, "SENDGRID_USER_MIXIN_ENABLED", True)

ARGUMENT_KEY_MAX_LENGTH = 255
EMAIL_MESSAGE_CATEGORY_MAX_LENGTH = 150
EVENT_NAME_MAX_LENGTH = 128
UNIQUE_ARGUMENT_DATA_MAX_LENGTH = 255

# To store all possible valid email addresses, a max_length of 254 is required.
# See RFC3696/5321
EMAIL_MESSAGE_FROM_EMAIL_MAX_LENGTH = 254
EMAIL_MESSAGE_TO_EMAIL_MAX_LENGTH = 254

if SENDGRID_USER_MIXIN_ENABLED:
	from django.contrib.auth.models import User
	from .mixins import SendGridUserMixin

	User.__bases__ += (SendGridUserMixin,)

logger = logging.getLogger(__name__)

@receiver(sendgrid_email_sent)
def update_email_message(sender, message, response, **kwargs):
	messageId = getattr(message, "message_id", None)
	emailMessage = EmailMessage.objects.get(message_id=messageId)
	emailMessage.response = response
	emailMessage.save()

def save_email_message(sender, **kwargs):
	message = kwargs.get("message", None)
	response = kwargs.get("response", None)

	COMPONENT_DATA_MODEL_MAP = {
		"to": EmailMessageToData,
		"cc": EmailMessageCcData,
		"bcc": EmailMessageBccData,
		"subject": EmailMessageSubjectData,
		"body": EmailMessageBodyData,
		"sendgrid_headers": EmailMessageSendGridHeadersData,
		"extra_headers": EmailMessageExtraHeadersData,
		"attachments": EmailMessageAttachmentsData,
	}

	if SENDGRID_EMAIL_TRACKING:
		messageId = getattr(message, "message_id", None)
		fromEmail = getattr(message, "from_email", None)
		recipients = getattr(message, "to", None)
		toEmail = recipients[0]
		categoryData = message.sendgrid_headers.data.get("category", None)
		if isinstance(categoryData, basestring):
			category = categoryData
			categories = [category]
		else:
			categories = categoryData
			category = categories[0] if categories else None

		if categories and len(categories) > MAX_CATEGORIES_PER_EMAIL_MESSAGE:
			msg = "The message has {n} categories which exceeds the maximum of {m}"
			logger.warn(msg.format(n=len(categories), m=MAX_CATEGORIES_PER_EMAIL_MESSAGE))

		emailMessage = EmailMessage.objects.create(
			message_id=messageId,
			from_email=fromEmail,
			to_email=toEmail,
			category=category,
			response=response,
		)

		if categories:
			for categoryName in categories:
				category, created = Category.objects.get_or_create(name=categoryName)
				if created:
					logger.debug("Category {c} was created".format(c=category))
				emailMessage.categories.add(category)

		uniqueArgsData = message.sendgrid_headers.data.get("unique_args", None)
		if uniqueArgsData:
			for k, v in uniqueArgsData.iteritems():
				argument, argumentCreated = Argument.objects.get_or_create(key=k)
				if argumentCreated:
					logger.debug("Argument {a} was created".format(a=argument))
				uniqueArg = UniqueArgument.objects.create(
					argument=argument,
					email_message=emailMessage,
					data=v,
				)

		for component, componentModel in COMPONENT_DATA_MODEL_MAP.iteritems():
			if component in SENDGRID_EMAIL_TRACKING_COMPONENTS:
				if component == "sendgrid_headers":
					componentData = message.sendgrid_headers.as_string()
				else:
					componentData = getattr(message, component, None)

				if componentData:
					componentData = componentModel.objects.create(
						email_message=emailMessage,
						data=componentData,
					)
				else:
					logger.debug("Could not get data for '{c}' component: {d}".format(c=component, d=componentData))
			else:
				logMessage = "Component {c} is not tracked"
				logger.debug(logMessage.format(c=component))

@receiver(sendgrid_event_recieved)
def log_event_recieved(sender, request, **kwargs):
	if settings.DEBUG:
		logger.debug("Recieved event request: {request}".format(request=request))


class Category(models.Model):
	name = models.CharField(unique=True, max_length=EMAIL_MESSAGE_CATEGORY_MAX_LENGTH)
	creation_time = models.DateTimeField(auto_now_add=True)
	last_modified_time = models.DateTimeField(auto_now=True)

	class Meta:
		verbose_name = _("Category")
		verbose_name_plural = _("Categories")

	def __unicode__(self):
		return self.name


class Argument(models.Model):
	ARGUMENT_DATA_TYPE_UNKNOWN = ARGUMENT_DATA_TYPE_UNKNOWN
	ARGUMENT_DATA_TYPE_BOOLEAN = ARGUMENT_DATA_TYPE_BOOLEAN
	ARGUMENT_DATA_TYPE_INTEGER = ARGUMENT_DATA_TYPE_INTEGER
	ARGUMENT_DATA_TYPE_FLOAT = ARGUMENT_DATA_TYPE_FLOAT
	ARGUMENT_DATA_TYPE_COMPLEX = ARGUMENT_DATA_TYPE_COMPLEX
	ARGUMENT_DATA_TYPE_STRING = ARGUMENT_DATA_TYPE_STRING
	ARGUMENT_DATA_TYPES = (
		(ARGUMENT_DATA_TYPE_UNKNOWN, _("Unknown")),
		(ARGUMENT_DATA_TYPE_BOOLEAN, _("Boolean")),
		(ARGUMENT_DATA_TYPE_INTEGER, _("Integer")),
		(ARGUMENT_DATA_TYPE_FLOAT, _("Float")),
		(ARGUMENT_DATA_TYPE_COMPLEX, _("Complex")),
		(ARGUMENT_DATA_TYPE_STRING, _("String")),
	)
	key = models.CharField(max_length=ARGUMENT_KEY_MAX_LENGTH)
	data_type = models.IntegerField(_("Data Type"), choices=ARGUMENT_DATA_TYPES, default=ARGUMENT_DATA_TYPE_UNKNOWN)
	creation_time = models.DateTimeField(auto_now_add=True)
	last_modified_time = models.DateTimeField(auto_now=True)

	class Meta:
		verbose_name = _("Argument")
		verbose_name_plural = _("Arguments")

	def __unicode__(self):
		return self.key


class EmailMessage(models.Model):
	message_id = models.CharField(unique=True, max_length=36, editable=False, blank=True, null=True, help_text="UUID")
	# user = models.ForeignKey(User, null=True) # TODO
	from_email = models.CharField(max_length=EMAIL_MESSAGE_FROM_EMAIL_MAX_LENGTH, help_text="Sender's e-mail")
	to_email = models.CharField(max_length=EMAIL_MESSAGE_TO_EMAIL_MAX_LENGTH, help_text="Primiary recipient's e-mail")
	category = models.CharField(max_length=EMAIL_MESSAGE_CATEGORY_MAX_LENGTH, blank=True, null=True, help_text="Primary SendGrid category")
	response = models.IntegerField(blank=True, null=True, help_text="Response received from SendGrid after sending")
	creation_time = models.DateTimeField(auto_now_add=True)
	last_modified_time = models.DateTimeField(auto_now=True)
	categories = models.ManyToManyField(Category)
	arguments = models.ManyToManyField(Argument, through="UniqueArgument")

	class Meta:
		verbose_name = _("Email Message")
		verbose_name_plural = _("Email Messages")

	@classmethod
	def from_event(self, event_dict):
		"""
		Returns a new EmailMessage instance derived from an Event Dictionary.
		"""
		newsletter_id = event_dict.get("newsletter[newsletter_id]")
		to_email = event_dict.get("email")
		try:
			emailMessage = UniqueArgument.objects.get(data=newsletter_id, argument__key="newsletter[newsletter_id]", email_message__to_email=to_email).email_message
		except UniqueArgument.DoesNotExist:
			categories = [value for key,value in event_dict.items() if 'category' in key]
			emailMessageSpec = {
				"message_id": event_dict.get("message_id", None),
				"from_email": "",
				"to_email": to_email,
				"response": None
			}
			if len(categories) > 0:
				emailMessageSpec["category"] = categories[0]

			emailMessage = EmailMessage.objects.create(**emailMessageSpec)

			for category in categories:
				categoryObj,created = Category.objects.get_or_create(name=category)
				emailMessage.categories.add(categoryObj)

			uniqueArgs = {}
			for key in UNIQUE_ARGS_STORED_FOR_EVENTS_WITHOUT_MESSAGE_ID:
				uniqueArgs[key] = event_dict.get(key)

			for argName, argValue in uniqueArgs.items():
				argument,_ = Argument.objects.get_or_create(
					key=argName
				)
				uniqueArg = UniqueArgument.objects.create(
					argument=argument,
					email_message=emailMessage,
					data=argValue
				)

		return emailMessage

	def __unicode__(self):
		return "{0}".format(self.message_id)

	def get_to_data(self):
		return self.to.data
	to_data = property(get_to_data)

	def get_cc_data(self):
		return self.to.data
	cc_data = property(get_cc_data)

	def get_bcc_data(self):
		return self.to.data
	bcc_data = property(get_bcc_data)

	def get_subject_data(self):
		return self.subject.data
	subject_data = property(get_subject_data)

	def get_body_data(self):
		return self.body.data
	body_data = property(get_body_data)

	def get_extra_headers_data(self):
		return self.headers.data
	extra_headers_data = property(get_extra_headers_data)

	def get_attachments_data(self):
		try:
			data = self.attachments.data
		except EmailMessageAttachmentsData.DoesNotExist:
			data = None

		return data
	attachments_data = property(get_attachments_data)

	def get_event_count(self):
		return self.event_set.count()
	event_count = property(get_event_count)

	def get_first_event(self):
		events = self.event_set.all()
		if events.exists():
			firstEvent = events.order_by("creation_time")[0]
		else:
			firstEvent = None

		return firstEvent
	first_event = property(get_first_event)

	def get_latest_event(self):
		# If your model's Meta specifies get_latest_by,
		# you can leave off the field_name argument to latest()
		return self.event_set.latest("creation_time")
	latest_event = property(get_latest_event)


class UniqueArgument(models.Model):
	argument = models.ForeignKey(Argument)
	email_message = models.ForeignKey(EmailMessage)
	data = models.CharField(max_length=UNIQUE_ARGUMENT_DATA_MAX_LENGTH)
	creation_time = models.DateTimeField(auto_now_add=True)
	last_modified_time = models.DateTimeField(auto_now=True)

	class Meta:
		verbose_name = _("Unique Argument")
		verbose_name_plural = _("Unique Arguments")

	def __unicode__(self):
		return "{key}: {value}".format(key=self.argument.key, value=self.value)

	def get_value(self):
		"""
		Returns data cast as the correct type.
		"""
		func_map = {
			ARGUMENT_DATA_TYPE_UNKNOWN: None,
			ARGUMENT_DATA_TYPE_BOOLEAN: bool,
			ARGUMENT_DATA_TYPE_INTEGER: int,
			ARGUMENT_DATA_TYPE_FLOAT: float,
			ARGUMENT_DATA_TYPE_COMPLEX: complex,
			ARGUMENT_DATA_TYPE_STRING: str,
		}
		f = func_map[self.argument.data_type]
		value = f(self.data) if f else self.data
		return value
	value = property(get_value)


class EmailMessageSubjectData(models.Model):
	email_message = models.OneToOneField(EmailMessage, primary_key=True, related_name="subject")
	data = models.TextField(_("Subject"), editable=False)

	class Meta:
		verbose_name = _("Email Message Subject Data")
		verbose_name_plural = _("Email Message Subject Data")

	def __unicode__(self):
		return "{0}".format(self.email_message)


class EmailMessageSendGridHeadersData(models.Model):
	email_message = models.OneToOneField(EmailMessage, primary_key=True, related_name="sendgrid_headers")
	data = models.TextField(_("SendGrid Headers"), editable=False)

	class Meta:
		verbose_name = _("Email Message SendGrid Headers Data")
		verbose_name_plural = _("Email Message SendGrid Headers Data")

	def __unicode__(self):
		return "{0}".format(self.email_message)


class EmailMessageExtraHeadersData(models.Model):
	email_message = models.OneToOneField(EmailMessage, primary_key=True, related_name="extra_headers")
	data = models.TextField(_("Extra Headers"), editable=False)

	class Meta:
		verbose_name = _("Email Message Extra Headers Data")
		verbose_name_plural = _("Email Message Extra Headers Data")

	def __unicode__(self):
		return "{0}".format(self.email_message)


class EmailMessageBodyData(models.Model):
	email_message = models.OneToOneField(EmailMessage, primary_key=True, related_name="body")
	data = models.TextField(_("Body"), editable=False)

	class Meta:
		verbose_name = _("Email Message Body Data")
		verbose_name_plural = _("Email Message Body Data")

	def __unicode__(self):
		return "{0}".format(self.email_message)


class EmailMessageAttachmentsData(models.Model):
	email_message = models.OneToOneField(EmailMessage, primary_key=True, related_name="attachments")
	data = models.TextField(_("Attachments"), editable=False)

	class Meta:
		verbose_name = _("Email Message Attachment Data")
		verbose_name_plural = _("Email Message Attachments Data")

	def __unicode__(self):
		return "{0}".format(self.email_message)


class EmailMessageBccData(models.Model):
	email_message = models.OneToOneField(EmailMessage, primary_key=True, related_name="bcc")
	data = models.TextField(_("Blind Carbon Copies"), editable=False)

	class Meta:
		verbose_name = _("Email Message Bcc Data")
		verbose_name_plural = _("Email Message Bcc Data")

	def __unicode__(self):
		return "{0}".format(self.email_message)


class EmailMessageCcData(models.Model):
	email_message = models.OneToOneField(EmailMessage, primary_key=True, related_name="cc")
	data = models.TextField(_("Carbon Copies"), editable=False)

	class Meta:
		verbose_name = _("Email Message Cc Data")
		verbose_name_plural = _("Email Message Cc Data")

	def __unicode__(self):
		return "{0}".format(self.email_message)


class EmailMessageToData(models.Model):
	email_message = models.OneToOneField(EmailMessage, primary_key=True, related_name="to")
	data = models.TextField(_("To"), editable=False)

	class Meta:
		verbose_name = _("Email Message To Data")
		verbose_name_plural = _("Email Message To Data")

	def __unicode__(self):
		return "{0}".format(self.email_message)


class EventType(models.Model):
	name = models.CharField(unique=True, max_length=EVENT_NAME_MAX_LENGTH)

	def __unicode__(self):
		return self.name


class Event(models.Model):
	email_message = models.ForeignKey(EmailMessage)
	email = models.EmailField()
	event_type = models.ForeignKey(EventType)
	creation_time = models.DateTimeField(auto_now_add=True)
	last_modified_time = models.DateTimeField(auto_now=True)
	#this column should always be populated by sendgrids mandatory timestamp param
	#null=True only because this was added later and need to distinguish old columns saved before this change
	timestamp = models.DateTimeField(null=True)

	class Meta:
		verbose_name = _("Event")
		verbose_name_plural = _("Events")

	def __unicode__(self):
		return u"{0} - {1}".format(self.email_message, self.event_type)

class ClickUrl(models.Model):
	url = models.TextField()

class ClickEvent(Event):
	click_url = models.ForeignKey(ClickUrl)

	class Meta:
		verbose_name = ("Click Event")
		verbose_name_plural = ("Click Events")

	def __unicode__(self):
		return u"{0} - {1}".format(super(ClickEvent,self).__unicode__(),self.url)

	def get_url(self):
		return self.click_url.url

	def set_url(self,url):
		try:
			self.click_url = ClickUrl.objects.get_or_create(url=url)[0]
		except MultipleObjectsReturned:
			self.click_url = ClickUrl.objects.filter(url=url).order_by('id')[0]
	url = property(get_url,set_url)

class BounceReason(models.Model):
	reason = models.TextField()

class BounceType(models.Model):
	type = models.CharField(max_length=32,unique=True)

class BounceEvent(Event):
	status = models.CharField(max_length=16)
	bounce_reason = models.ForeignKey(BounceReason,null=True)
	bounce_type = models.ForeignKey(BounceType,null=True)
	class Meta:
		verbose_name = ("Bounce Event")
		verbose_name_plural = ("Bounce Events")

	def __unicode__(self):
		return u"{0} - {1}".format(super(self,BounceEvent).__unicode__(),reason)

	def get_reason(self):
		return self.bounce_reason.reason

	def set_reason(self,reason):
		self.bounce_reason = BounceReason.objects.get_or_create(reason=reason)[0]
	reason = property(get_reason,set_reason)

	def get_type(self):
		return self.bounce_type.type

	def set_type(self,reason):
		self.bounce_type = BounceType.objects.get_or_create(type=reason)[0]
	type = property(get_type,set_type)

class DeferredEvent(Event):
	response = models.TextField()
	attempt = models.IntegerField()

class DroppedEvent(Event):
	reason = models.CharField(max_length=255)

class DeliverredEvent(Event):
	response = models.TextField()

########NEW FILE########
__FILENAME__ = settings
from django.conf import settings

# This is experimental, use with caution.
SENDGRID_CREATE_MISSING_EMAIL_MESSAGES = getattr(settings, "SENDGRID_CREATE_MISSING_EMAIL_MESSAGES", False)

########NEW FILE########
__FILENAME__ = signals
import django.dispatch

sendgrid_email_sent = django.dispatch.Signal(providing_args=["message", "response"])
sendgrid_event_recieved = django.dispatch.Signal(providing_args=["request"])

########NEW FILE########
__FILENAME__ = tests
from __future__ import absolute_import

from collections import defaultdict

from django.conf import settings
from django.core.mail import EmailMessage
from django.core.urlresolvers import reverse
from django.dispatch import receiver
from django.test import TestCase
from django.test.client import Client
from django.utils.http import urlencode

from .constants import EVENT_TYPES_EXTRA_FIELDS_MAP, EVENT_MODEL_NAMES, UNIQUE_ARGS_STORED_FOR_EVENTS_WITHOUT_MESSAGE_ID
from .mail import get_sendgrid_connection
from .mail import send_sendgrid_mail
from .message import SendGridEmailMessage
from .message import SendGridEmailMultiAlternatives
from .models import Argument
from .models import Category
from .models import Event, ClickEvent, BounceEvent, DeferredEvent, DroppedEvent, DeliverredEvent, EmailMessage as EmailMessageModel
from .models import EmailMessageAttachmentsData
from .models import EventType
from .models import UniqueArgument
from .settings import SENDGRID_CREATE_MISSING_EMAIL_MESSAGES
from .signals import sendgrid_email_sent
from .utils import filterutils
# from .utils import get_email_message
from .utils import in_test_environment
from .utils.requestfactory import RequestFactory 
from .views import handle_single_event_request


TEST_SENDER_EMAIL = "ryan@example.com"
TEST_RECIPIENTS = ["ryan@example.com"]

validate_filter_setting_value = filterutils.validate_filter_setting_value
validate_filter_specification = filterutils.validate_filter_specification
update_filters = filterutils.update_filters



class SendGridEventTest(TestCase):
	def setUp(self):
		self.email = SendGridEmailMessage(to=TEST_RECIPIENTS, from_email=TEST_SENDER_EMAIL)
		self.email.send()
		self.rf = RequestFactory()

	def test_event_email_exists(self):
		event_count = Event.objects.count()
		post_data = {
			"message_id": self.email.message_id, 
			"email" : self.email.from_email,
			"event" : "OPEN",
			}
		request = self.rf.post('/sendgrid/events',post_data)
		handle_single_event_request(request)
		#Event created
		self.assertEqual(Event.objects.count(),event_count+1)
		#Email matches original message_id
		self.assertEqual(Event.objects.get().email_message.message_id, self.email.message_id.__str__())

	def verify_event_with_missing_email(self,post_data):
		event_count = Event.objects.count()
		email_count = EmailMessageModel.objects.count()

		for key in UNIQUE_ARGS_STORED_FOR_EVENTS_WITHOUT_MESSAGE_ID:
			post_data[key] = key+"_value"

		request = self.rf.post('/sendgrid/events',post_data)
		handle_single_event_request(request)

		if SENDGRID_CREATE_MISSING_EMAIL_MESSAGES:
			delta = 1
		else:
			delta = 0

		#event created
		self.assertEqual(Event.objects.count(), event_count + delta)
		#email created
		self.assertEqual(EmailMessageModel.objects.count(), email_count + delta)

		if SENDGRID_CREATE_MISSING_EMAIL_MESSAGES:
			event = Event.objects.get(email=post_data['email'])
			emailMessage = event.email_message
			#check to_email
			self.assertEqual(event.email_message.to_email, event.email)

			#check unique args
			for key in UNIQUE_ARGS_STORED_FOR_EVENTS_WITHOUT_MESSAGE_ID:
				self.assertEqual(post_data[key],emailMessage.uniqueargument_set.get(argument__key=key).data)

			#post another event
			request = self.rf.post('/sendgrid/events',post_data)
			response = handle_single_event_request(request)

			#should be same email_count
			self.assertEqual(EmailMessageModel.objects.count(),email_count + 1)

	def test_event_email_doesnt_exist(self):
		postData = {
			"message_id": 'a5df', 
			"email" : self.email.to[0],
			"event" : "OPEN",
			"category": ["test_category", "another_test_category"],
		}

		self.verify_event_with_missing_email(postData)

	def test_event_no_message_id(self):
		postData = {
			"email" : self.email.to[0],
			"event" : "OPEN",
			"category": "test_category",
		}
		self.verify_event_with_missing_email(postData)

	def test_event_email_doesnt_exist_no_category(self):
		postData = {
			"message_id": 'a5df', 
			"email" : self.email.to[0],
			"event" : "OPEN"
		}

		self.verify_event_with_missing_email(postData)


class SendGridEmailTest(TestCase):
	"""docstring for SendGridEmailTest"""
	def test_email_has_unique_id(self):
		"""
		Tests the existence of the ``SendGridEmailMessage._message_id`` attribute.
		"""
		email = SendGridEmailMessage()
		self.assertTrue(email._message_id)
		
	def test_email_sends_unique_id(self):
		"""
		Tests sending a ``SendGridEmailMessage`` adds a ``message_id`` to the unique args.
		"""
		email = SendGridEmailMessage(to=TEST_RECIPIENTS, from_email=TEST_SENDER_EMAIL)
		email.send()
		self.assertTrue(email.sendgrid_headers.data["unique_args"]["message_id"])
		
	def test_unique_args_persist(self):
		"""
		Tests that unique args are not lost due to sending adding the ``message_id`` arg.
		"""
		email = SendGridEmailMessage(to=TEST_RECIPIENTS, from_email=TEST_SENDER_EMAIL)
		uniqueArgs = {
			"unique_arg_1": 1,
			"unique_arg_2": 2,
			"unique_arg_3": 3,
		}
		email.sendgrid_headers.setUniqueArgs(uniqueArgs)
		email.send()

		for k, v in uniqueArgs.iteritems():
			self.assertEqual(v, email.sendgrid_headers.data["unique_args"][k])

		self.assertTrue(email.sendgrid_headers.data["unique_args"]["message_id"])

	def test_email_sent_signal_has_message(self):
		"""
		Tests the existence of the ``message`` keywork arg from the ``sendgrid_email_sent`` signal.
		"""
		@receiver(sendgrid_email_sent)
		def receive_sendgrid_email_sent(*args, **kwargs):
			"""
			Receives sendgrid_email_sent signals.
			"""
			self.assertTrue("response" in kwargs)
			self.assertTrue("message" in kwargs)
			
		email = SendGridEmailMessage(to=TEST_RECIPIENTS, from_email=TEST_SENDER_EMAIL)
		response = email.send()


class SendGridInTestEnvTest(TestCase):
	def test_in_test_environment(self):
		"""
		Tests that the test environment is detected.
		"""
		self.assertEqual(in_test_environment(), True)


class SendWithSendGridEmailMessageTest(TestCase):
	def setUp(self):
		"""
		Sets up the tests.
		"""
		self.signalsReceived = defaultdict(list)
		
	def test_send_email_sends_signal(self):
		"""
		Tests that sending a ``SendGridEmailMessage`` sends a ``sendgrid_email_sent`` signal.
		"""
		@receiver(sendgrid_email_sent)
		def receive_sendgrid_email_sent(*args, **kwargs):
			"""
			Receives sendgrid_email_sent signals.
			"""
			self.signalsReceived["sendgrid_email_sent"].append(1)
			return True
			
		email = SendGridEmailMessage(to=TEST_RECIPIENTS, from_email=TEST_SENDER_EMAIL)
		email.send()
		
		numEmailSentSignalsRecieved = sum(self.signalsReceived["sendgrid_email_sent"])
		self.assertEqual(numEmailSentSignalsRecieved, 1)
		
	def test_send_with_send_mail(self):
		"""
		Tests sending an email with the ``send_email_with_sendgrid`` helper.
		"""
		send_sendgrid_mail(
			subject="Your new account!",
			message="Thanks for signing up.",
			from_email='welcome@example.com',
			recipient_list=['ryan@example.com'],
		)


class SendWithEmailMessageTest(TestCase):
	"""docstring for SendWithEmailMessageTest"""
	def setUp(self):
		"""
		Sets up the tests.
		"""
		self.connection = get_sendgrid_connection()
		
	def test_send_with_email_message(self):
		"""
		Tests sending an ``EmailMessage`` with the ``SendGridEmailBackend``.
		"""
		email = EmailMessage(
			subject="Your new account!",
			body="Thanks for signing up.",
			from_email='welcome@example.com',
			to=['ryan@example.com'],
			connection=self.connection,
		)
		email.send()



class SendWithSendGridEmailMultiAlternativesTest(TestCase):
	def setUp(self):
		self.signalsReceived = defaultdict(list)
		
	def test_send_multipart_email(self):
		"""
		Tests sending multipart emails.
		"""
		subject, from_email, to = 'hello', 'from@example.com', 'to@example.com'
		text_content = 'This is an important message.'
		html_content = '<p>This is an <strong>important</strong> message.</p>'
		msg = SendGridEmailMultiAlternatives(subject, text_content, from_email, [to])
		msg.attach_alternative(html_content, "text/html")
		msg.send()
		
	def test_send_multipart_email_sends_signal(self):
		@receiver(sendgrid_email_sent)
		def receive_sendgrid_email_sent(*args, **kwargs):
			"""
			Receives sendgrid_email_sent signals.
			"""
			self.signalsReceived["sendgrid_email_sent"].append(1)
			return True
			
		email = SendGridEmailMultiAlternatives(to=TEST_RECIPIENTS, from_email=TEST_SENDER_EMAIL)
		email.send()
		
		numEmailSentSignalsRecieved = sum(self.signalsReceived["sendgrid_email_sent"])
		self.assertEqual(numEmailSentSignalsRecieved, 1)


class FilterUtilsTests(TestCase):
	"""docstring for FilterUtilsTests"""
	def setUp(self):
		"""
		Set up the tests.
		"""
		pass
		
	def test_validate_filter_spec(self):
		"""
		Tests validation of a filter specification.
		"""
		filterSpec = {
			"subscriptiontrack": {
				"enable": 1,
			},
			"opentrack": {
				"enable": 0,
			},
		}
		self.assertEqual(validate_filter_specification(filterSpec), True)
		
	def test_subscriptiontrack_enable_parameter(self):
		"""
		Tests the ``subscriptiontrack`` filter's ``enable`` paramter.
		"""
		self.assertEqual(validate_filter_setting_value("subscriptiontrack", "enable", 0), True)
		self.assertEqual(validate_filter_setting_value("subscriptiontrack", "enable", 1), True)
		self.assertEqual(validate_filter_setting_value("subscriptiontrack", "enable", 0.0), True)
		self.assertEqual(validate_filter_setting_value("subscriptiontrack", "enable", 1.0), True)
		self.assertEqual(validate_filter_setting_value("subscriptiontrack", "enable", "0"), True)
		self.assertEqual(validate_filter_setting_value("subscriptiontrack", "enable", "1"), True)
		self.assertEqual(validate_filter_setting_value("subscriptiontrack", "enable", "0.0"), False)
		self.assertEqual(validate_filter_setting_value("subscriptiontrack", "enable", "1.0"), False)
		
	def test_opentrack_enable_parameter(self):
		"""
		Tests the ``opentrack`` filter's ``enable`` paramter.
		"""
		self.assertEqual(validate_filter_setting_value("opentrack", "enable", 0), True)
		self.assertEqual(validate_filter_setting_value("opentrack", "enable", 1), True)
		self.assertEqual(validate_filter_setting_value("opentrack", "enable", 0.0), True)
		self.assertEqual(validate_filter_setting_value("opentrack", "enable", 1.0), True)
		self.assertEqual(validate_filter_setting_value("opentrack", "enable", "0"), True)
		self.assertEqual(validate_filter_setting_value("opentrack", "enable", "1"), True)
		self.assertEqual(validate_filter_setting_value("opentrack", "enable", "0.0"), False)
		self.assertEqual(validate_filter_setting_value("opentrack", "enable", "1.0"), False)


class UpdateFiltersTests(TestCase):
	"""docstring for SendWithFiltersTests"""
	def setUp(self):
		"""docstring for setUp"""
		self.email = SendGridEmailMessage(to=TEST_RECIPIENTS, from_email=TEST_SENDER_EMAIL)
		
	def test_update_filters(self):
		"""
		Tests SendGrid filter functionality.
		"""
		filterSpec = {
			"subscriptiontrack": {
				"enable": 1,
			},
			"opentrack": {
				"enable": 0,
			},
		}
		update_filters(self.email, filterSpec)
		self.email.send()


# class TestGetEmailMessageUtil(TestCase):
# 	"""docstring for TestGetEmailMessageUtil"""
# 	def test_get_with_email_message(self):
# 		from .models import EmailMessage as SGEmailMessage

# 		original = SGEmailMessage.objects.create()
# 		result = get_email_message(original)
# 		self.assertEqual(original, result)

# 	def test_get_with_id(self):
# 		from .models import EmailMessage as SGEmailMessage

# 		original = SGEmailMessage.objects.create()
# 		result = get_email_message(original.id)
# 		self.assertEqual(original, result)

# 	def test_with_message_id(self):
# 		from sendgrid.models import EmailMessage as SGEmailMessage

# 		original = SGEmailMessage.objects.create()
# 		result = get_email_message(original.message_id)
# 		self.assertEqual(original, result)


class CategoryTests(TestCase):
	def setUp(self):
		self.testCategoryNames = (
			"Test Category 1",
			"Test Category 2",
		)

	def assert_category_exists(self, categoryName):
		category = Category.objects.get(name=categoryName)
		return category

	def test_send_with_single_category(self):
		@receiver(sendgrid_email_sent)
		def receive_sendgrid_email_sent(*args, **kwargs):
			"""
			Receives sendgrid_email_sent signals.
			"""
			emailMessage = kwargs["message"]
			sendgridHeadersData = emailMessage.sendgrid_headers.data

			expectedCategory = self.testCategoryNames[0]
			self.assertEqual(sendgridHeadersData["category"], expectedCategory)

		sendgridEmailMessage = SendGridEmailMessage(to=TEST_RECIPIENTS, from_email=TEST_SENDER_EMAIL)
		sendgridEmailMessage.sendgrid_headers.setCategory(self.testCategoryNames[0])
		sendgridEmailMessage.update_headers()
		sendgridEmailMessage.send()

		category = self.assert_category_exists(self.testCategoryNames[0])
		self.assertTrue(category)

	def test_send_with_multiple_categories(self):
		@receiver(sendgrid_email_sent)
		def receive_sendgrid_email_sent(*args, **kwargs):
			"""
			Receives sendgrid_email_sent signals.
			"""
			emailMessage = kwargs["message"]
			sendgridHeadersData = emailMessage.sendgrid_headers.data

			expectedCategories = self.testCategoryNames
			self.assertEqual(sendgridHeadersData["category"], expectedCategories)

		sendgridEmailMessage = SendGridEmailMessage(to=TEST_RECIPIENTS, from_email=TEST_SENDER_EMAIL)
		sendgridEmailMessage.sendgrid_headers.setCategory(self.testCategoryNames)
		sendgridEmailMessage.update_headers()
		sendgridEmailMessage.send()

		for category in self.testCategoryNames:
			category = self.assert_category_exists(self.testCategoryNames[0])
			self.assertTrue(category)


class UniqueArgumentTests(TestCase):
	def setUp(self):
		pass

	def assert_argument_exists(self, argumentName):
		argument = Argument.objects.get(key=argumentName)
		return argument

	def assert_unique_argument_exists(self, key, value):
		uniqueArgument = UniqueArgument.objects.get(
			argument=Argument.objects.get(key=key),
			data=value
		)
		return uniqueArgument

	def test_send_with_unique_arguments(self):
		@receiver(sendgrid_email_sent)
		def receive_sendgrid_email_sent(*args, **kwargs):
			"""
			Receives sendgrid_email_sent signals.
			"""
			emailMessage = kwargs["message"]
			sendgridHeadersData = emailMessage.sendgrid_headers.data

			self.assertTrue(sendgridHeadersData["unique_args"])

		sendgridEmailMessage = SendGridEmailMessage(to=TEST_RECIPIENTS, from_email=TEST_SENDER_EMAIL)
		# sendgridEmailMessage.sendgrid_headers.setCategory(self.testCategoryNames[0])
		# sendgridEmailMessage.update_headers()
		sendgridEmailMessage.send()

		argument = self.assert_argument_exists("message_id")
		self.assertTrue(argument)

		expectedUniqueArgKeyValue = {
			"key": "message_id",
			"value": sendgridEmailMessage.message_id,
		}
		uniqueArgument = self.assert_unique_argument_exists(**expectedUniqueArgKeyValue)
		self.assertTrue(uniqueArgument)

from .utils.testutils import post_test_event
class EventPostTests(TestCase):
	fixtures = ["initial_data.json"]

	def setUp(self):
		self.client = Client()
		self.email_message = EmailMessageModel.objects.create(to_email=TEST_RECIPIENTS[0], from_email=TEST_SENDER_EMAIL,message_id='123abc')

	def test_all_event_types(self):
		"""
		Tests all event types listed in EVENT_MODEL_NAMES
		Checks that every EXTRA_FIELD is saved
		"""
		for event_type, event_model_name in EVENT_MODEL_NAMES.items():
			print "Testing {0} event".format(event_type)
			event_model = eval(EVENT_MODEL_NAMES[event_type]) if event_type in EVENT_MODEL_NAMES.keys() else Event
			event_count_before = event_model.objects.count()
			response = post_test_event(event_type,event_model_name,self.email_message)
			self.assertEqual(event_model.objects.count(),event_count_before+1)
			event = event_model.objects.filter(event_type__name=event_type)[0]
			for key in EVENT_TYPES_EXTRA_FIELDS_MAP[event_type.upper()]:
				self.assertNotEqual(event.__getattribute__(key),None)

class EventTypeFixtureTests(TestCase):
	fixtures = ["initial_data.json"]

	def setUp(self):
		self.expectedEventTypes = {
			"UNKNOWN": 1,
			"DEFERRED": 2,
			"PROCESSED": 3,
			"DROPPED": 4,
			"DELIVERED": 5,
			"BOUNCE": 6,
			"OPEN": 7,
			"CLICK": 8,
			"SPAMREPORT": 9,
			"UNSUBSCRIBE": 10,
		}

	def test_event_types_exists(self):
		for name, primaryKey in self.expectedEventTypes.iteritems():
			self.assertEqual(
				EventType.objects.get(pk=primaryKey),
				EventType.objects.get(name=name)
			)


class DownloadAttachmentTestCase(TestCase):
	def setUp(self):

		self.attachments = {
			"file1.csv": "name,age\r\nryan,28",
			# "file2.csv": "name,age\r\nryan,28"
		}

		emailMessage = SendGridEmailMessage(
			to=TEST_RECIPIENTS,
			from_email=TEST_SENDER_EMAIL)
		for name, contents in self.attachments.iteritems():
			emailMessage.attach(name, contents)

		response = emailMessage.send()
		self.assertEqual(response, 1)
		self.assertEqual(EmailMessageModel.objects.count(), 1)
		self.assertEqual(EmailMessageAttachmentsData.objects.count(), 1)

	def test_attachments_exist_for_email_message(self):
		em = EmailMessageModel.objects.get(id=1)
		emailMessageAttachments = em.attachments
		self.assertEqual(len(eval(emailMessageAttachments.data)), len(self.attachments))

	def test_download_attachments(self):
		em = EmailMessageModel.objects.get(id=1)
		attachmentsURL = reverse("sendgrid_download_attachments", args=(em.message_id,))
		c = Client()
		response = c.get(attachmentsURL)
		self.assertEqual(response.status_code, 200)

class DownloadAttachment404TestCase(TestCase):
	def setUp(self):
		emailMessage = SendGridEmailMessage(
			to=TEST_RECIPIENTS,
			from_email=TEST_SENDER_EMAIL)

		response = emailMessage.send()
		self.assertEqual(response, 1)
		self.assertEqual(EmailMessageModel.objects.count(), 1)
		self.assertEqual(EmailMessageAttachmentsData.objects.count(), 0)

	def test_attachments_exist_for_email_message(self):
		em = EmailMessageModel.objects.get(id=1)
		emailMessageAttachments = em.attachments_data
		self.assertEqual(emailMessageAttachments, None)

	def test_download_attachments(self):
		em = EmailMessageModel.objects.get(id=1)
		attachmentsURL = reverse("sendgrid_download_attachments", args=(em.message_id,))
		c = Client()
		response = c.get(attachmentsURL)
		self.assertEqual(response.status_code, 404)

########NEW FILE########
__FILENAME__ = urls
from __future__ import absolute_import

from django.conf.urls.defaults import patterns, include, url

from .views import listener


urlpatterns = patterns('',
	url(r"^events/$", "sendgrid.views.listener", name="sendgrid_post_event"),
	url(r"^messages/(?P<message_id>[-\w]+)/attachments/$",
		"sendgrid.views.download_attachments",
		name="sendgrid_download_attachments"
	),
)

########NEW FILE########
__FILENAME__ = cleanup
import datetime
import logging
import time

from django.utils.timezone import now as now_utc

from sendgrid.models import EmailMessage, EmailMessageBodyData


ONE_DAY = datetime.timedelta(days=1)
ONE_WEEK = datetime.timedelta(weeks=1)

logger = logging.getLogger(__name__)

def delete_email_message_body_data(emailMessages):
	tick, tock = time.time(), None
	affectedEmailMessages = []
	unaffectedEmailMessages = []
	for emailMessage in emailMessages:
		try:
			bodyDataObject = emailMessage.body
		except EmailMessageBodyData.DoesNotExist:
			logger.info("EmailMessage {em} has no EmailMessageBodyData".format(em=emailMessage))
			unaffectedEmailMessages.append(emailMessage.id)
			continue
		else:
			bodyDataObject.delete()
			affectedEmailMessages.append(emailMessage.id)
	tock = time.time()

	summary = {
		"affected": affectedEmailMessages,
		"unaffected": unaffectedEmailMessages,
		"elapsedSeconds": tock - tick,
	}

	return summary

def cleanup_email_message_body_data(*args, **kwargs):
	"""
	Deletes ``EmailMessageBodyData`` objects created N {days|weeks} from now.

	>>> EmailMessage.objects.create()
	>>> EmailMessage.body = EmailMessageBodyData.objects.create(data="body")
	>>> EmailMessageBodyData.objects.count()
	1
	>>> cleanup_email_message_body_data(days=0)
	>>> EmailMessageBodyData.objects.count()
	1
	>>> cleanup_email_message_body_data(days=1)
	>>> EmailMessageBodyData.objects.count()
	0
	"""
	if all(kwargs.values()):
		# datetime.timedelta will actually handle multiple keyword args just fine
		raise Exception("Ambiguous arguments given")

	start = now_utc()
	delta = datetime.timedelta(**kwargs)
	purgeDate = start - delta
	logger.debug("Start: {s}".format(s=start))
	logger.debug("Delta: {d}".format(d=delta))
	logger.debug("Purge date: {p}".format(p=purgeDate))

	emailMessages = EmailMessage.objects.filter(
		creation_time__lt=purgeDate,
		body__isnull=False,
	)

	if emailMessages.exists():
		result = delete_email_message_body_data(emailMessages)
	else:
		result = None

	logger.debug("Result: {r}".format(r=str(result)))

	return result

########NEW FILE########
__FILENAME__ = filterutils
from django.conf import settings


PASS = lambda i: True
FAIL = lambda i: False
IS_ZERO_OR_ONE = lambda i: i in (0, 1, "0", "1")

INTERFACES = {
	"gravatar": ["enable"],
	"clicktrack": ["enable"],
	"subscriptiontrack": ["enable", "text/html", "text/plain", "replace", "url", "landing"],
	"opentrack": ["enable"],
}

FILTER_SETTING_VALUE_TESTS = {
	"gravatar.enable": IS_ZERO_OR_ONE,
	"clicktrack.enable": IS_ZERO_OR_ONE,
	"subscriptiontrack.enable": IS_ZERO_OR_ONE,
	"subscriptiontrack.text/html": PASS,
	"opentrack.enable": IS_ZERO_OR_ONE,
}

IGNORE_MISSING_TESTS = getattr(settings, "IGNORE_MISSING_TESTS", False)
VALIDATE_FILTER_SPECIFICATION = getattr(settings, "VALIDATE_FILTER_SPECIFICATION", True)

def validate_filter_setting_value(filter, setting, value, ignoreMissingTests=IGNORE_MISSING_TESTS):
	"""
	Validates the given value for the filter setting.
	"""
	if filter not in INTERFACES:
		raise AttributeError("The filter {f} is not valid".format(f=filter))
		
	if setting not in INTERFACES[filter]:
		raise AttributeError("The setting {s} is not valid for the filter {f}".format(s=setting, f=filter))
		
	testName = ".".join([filter, setting])
	try:
		test = FILTER_SETTING_VALUE_TESTS[testName]
	except KeyError as e:
		if ignoreMissingTests:
			result = True
		else:
			raise e
	else:
		result = test(value)
		
	return result

def validate_filter_specification(f):
	"""
	Validates a given filter specification.
	"""
	passedAllTests = None

	testResults = {}
	for filter, spec in f.iteritems():
		for setting, value in spec.iteritems():
			testKey = ".".join([filter, setting])
			testResult = validate_filter_setting_value(filter, setting, value)
			testResults[testKey] = testResult

	resultSet = set(testResults.values())
	passedAllTests = len(resultSet) == 1 and True in resultSet
	return passedAllTests

def update_filters(email, filterSpec, validate=VALIDATE_FILTER_SPECIFICATION):
	"""
	Updates the ``SendGridEmailMessage`` filters, optionally validating the given sepcification.
	"""
	if validate:
		filterSpecIsValid = validate_filter_specification(filterSpec)
		if not filterSpecIsValid:
			raise Exception("Invalid filter specification")
			
	for filter, spec in filterSpec.iteritems():
		for setting, value in spec.iteritems():
			email.sendgrid_headers.addFilterSetting(fltr=filter, setting=setting, val=value)

	return

########NEW FILE########
__FILENAME__ = requestfactory
#Took this from http://djangosnippets.org/snippets/963/
from django.test import Client
from django.core.handlers.wsgi import WSGIRequest

class RequestFactory(Client):
    """
    Class that lets you create mock Request objects for use in testing.
    
    Usage:
    
    rf = RequestFactory()
    get_request = rf.get('/hello/')
    post_request = rf.post('/submit/', {'foo': 'bar'})
    
    This class re-uses the django.test.client.Client interface, docs here:
    http://www.djangoproject.com/documentation/testing/#the-test-client
    
    Once you have a request object you can pass it to any view function, 
    just as if that view had been hooked up using a URLconf.
    
    """
    def request(self, **request):
        """
        Similar to parent class, but returns the request object as soon as it
        has created it.
        """
        environ = {
            'HTTP_COOKIE': self.cookies,
            'PATH_INFO': '/',
            'QUERY_STRING': '',
            'REQUEST_METHOD': 'GET',
            'SCRIPT_NAME': '',
            'SERVER_NAME': 'testserver',
            'SERVER_PORT': 80,
            'SERVER_PROTOCOL': 'HTTP/1.1',
        }
        environ.update(self.defaults)
        environ.update(request)
        return WSGIRequest(environ)
########NEW FILE########
__FILENAME__ = testutils
from django.test.client import Client
from sendgrid.constants import EVENT_TYPES_EXTRA_FIELDS_MAP
from django.core.urlresolvers import reverse
from django.utils.http import urlencode

client = Client()
def post_test_event(event_type,event_model_name,email_message):
	event_data = {
		"event": event_type,
		"message_id": email_message.message_id,
		"email": email_message.to_email,
		"timestamp": 1322000095
	}

	for key in EVENT_TYPES_EXTRA_FIELDS_MAP[event_type.upper()]:
		print "Adding Extra Field {0}".format(key)
		if key == "attempt":
			event_data[key] = 3
		else:
			event_data[key] = "test_param" + key

	return client.post(reverse("sendgrid_post_event",args=[]),data=urlencode(event_data),content_type="application/x-www-form-urlencoded; charset=utf-8")
########NEW FILE########
__FILENAME__ = views
from __future__ import absolute_import

import logging
from datetime import datetime
from django.conf import settings
from django.http import HttpResponse
from django.http import HttpResponseBadRequest
from django.http import HttpResponseNotFound
from django.utils import simplejson
from django.views.decorators.csrf import csrf_exempt

from .signals import sendgrid_event_recieved

from sendgrid.models import EmailMessage, Event, ClickEvent, DeferredEvent, DroppedEvent, DeliverredEvent, BounceEvent, EventType
from sendgrid.constants import EVENT_TYPES_EXTRA_FIELDS_MAP, EVENT_MODEL_NAMES
from sendgrid.settings import SENDGRID_CREATE_MISSING_EMAIL_MESSAGES


POST_EVENTS_RESPONSE_STATUS_CODE = getattr(settings, "POST_EVENT_HANDLER_RESPONSE_STATUS_CODE", 200)

logger = logging.getLogger(__name__)

def handle_single_event_request(request):
	"""
	Handles single event POST requests.
	"""
	eventData = request.POST

	# Parameters that are always passed with each event
	email = eventData.get("email", None)
	event = eventData.get("event", None).upper()
	category = eventData.get("category", None)
	message_id = eventData.get("message_id", None)

	emailMessage = None
	if message_id:
		try:
			emailMessage = EmailMessage.objects.get(message_id=message_id)
		except EmailMessage.DoesNotExist:
			msg = "EmailMessage with message_id {id} not found"
			logger.debug(msg.format(id=message_id))
	else:
		msg = "Expected 'message_id' was not found in event data"
		logger.debug(msg)

	if not emailMessage and SENDGRID_CREATE_MISSING_EMAIL_MESSAGES:
		logger.debug("Creating missing EmailMessage from event data")
		emailMessage = EmailMessage.from_event(eventData)
	elif not emailMessage and not SENDGRID_CREATE_MISSING_EMAIL_MESSAGES:
		return HttpResponse()

	event_type = EventType.objects.get(name=event.upper())
	event_params = {
		"email_message": emailMessage,
		"email": email,
		"event_type":event_type
	}
	timestamp = eventData.get("timestamp",None)
	if timestamp:
		event_params["timestamp"] = datetime.utcfromtimestamp(float(timestamp))

		#enforce unique constraint on email_message,event_type,creation_time
		#this should be done at the db level but since it was added later it would have needed a data migration that either deleted or updated duplicate events
		#this also might need a combined index, but django orm doesn't have this feature yet: https://code.djangoproject.com/ticket/5805
		existingEvents = Event.objects.filter(email_message=emailMessage,event_type=event_type,timestamp=event_params["timestamp"])
		unique = existingEvents.count() == 0
	else:
		#no timestamp provided. therefore we cannot enforce any kind of uniqueness
		unique = True
	if unique:
		for key in EVENT_TYPES_EXTRA_FIELDS_MAP[event.upper()]:
			value = eventData.get(key,None)
			if value:
				event_params[key] = value
			else:
				logger.debug("Expected post param {key} for Sendgrid Event {event} not found".format(key=key,event=event))
		event_model = eval(EVENT_MODEL_NAMES[event]) if event in EVENT_MODEL_NAMES.keys() else Event
		eventObj = event_model.objects.create(**event_params)

	response = HttpResponse()

	return response

def handle_batched_events_request(request):
	"""
	Handles batched events POST requests.

	Example batched events ::

		{"email":"foo@bar.com","timestamp":1322000095,"unique_arg":"my unique arg","event":"delivered"}
		{"email":"foo@bar.com","timestamp":1322000096,"unique_arg":"my unique arg","event":"open"}

	"""
	logger.exception("Batched events are not currently supported!")
	raise NotImplementedError

def clean_response(response):
	expectedStatusCode = POST_EVENTS_RESPONSE_STATUS_CODE

	if not response:
		logger.error("A response was not created!")
		response = HttpResponse()

	if response.status_code != expectedStatusCode:
		logger.debug("Attempted to send status code {c}".format(c=response.status_code))
		logger.debug("Setting status code to {c}".format(c=expectedStatusCode))

		response.write("Previous status code: {c}\n".format(c=response.status_code))
		response.status_code = expectedStatusCode

	return response

@csrf_exempt
def listener(request, statusCode=POST_EVENTS_RESPONSE_STATUS_CODE):
	"""
	Handles POSTs from SendGrid

	# SendGrid Event API Documentation
	# http://docs.sendgrid.com/documentation/api/event-api/
	
	Example Request ::
		
		curl -i -d 'message_id=1&amp;email=test@gmail.com&amp;arg2=2&amp;arg1=1&amp;category=testing&amp;event=processed' http://127.0.0.1:8000/sendgrid/events/
	"""
	sendgrid_event_recieved.send(sender=None, request=request)

	response = None
	if request.method == "POST":
		if request.META["CONTENT_TYPE"].startswith("application/json"):
			# Batched event POSTs have a content-type header of application/json
			# They contain exactly one JSON string per line, with each line representing one event.
			response = handle_batched_events_request(request)
		elif request.META["CONTENT_TYPE"].startswith("application/xml"):
			raise NotImplementedError
		elif request.META["CONTENT_TYPE"].startswith("application/x-www-form-urlencoded"):
			response = handle_single_event_request(request)
		else:
			msg = "Unexpected content type: {m}".format(m=request.META["CONTENT_TYPE"])
			logger.error(msg)
	else:
		msg = "Request method '{method}' not allowed: {error}".format(method=request.method, error=request.method)
		logger.error(msg)
		
		response = HttpResponse()
		response.status_code = 405

	return clean_response(response)

def download_attachments(request, message_id):
	"""
	Returns an HttpResponse containing the zipped attachments.
	"""
	import zipfile
	from contextlib import closing
	from django.shortcuts import get_object_or_404
	from django.utils import simplejson as json

	from sendgrid.utils import zip_files

	emailMessage = get_object_or_404(EmailMessage, message_id=message_id)

	emailMessageDataString = emailMessage.attachments_data
	if emailMessageDataString:
		# TODO: This is a little hacky
		emailMessageDataStringJSONSafe = (emailMessageDataString
			.replace('(', '[')
			.replace(')', ']')
			.replace("'", '"')
			.replace("None", '"text/plain"')
		)
		obj = json.loads(emailMessageDataStringJSONSafe)

		files = {}
		for name, content, contentType in obj:
			files[name] = content

		response = HttpResponse(mimetype="application/x-zip")
		response["Content-Disposition"] = "attachment; filename={filename}".format(filename="attachment.zip")
		with closing(zip_files(files)) as zio:
			response.write(zio.getvalue())
	else:
		response = HttpResponseNotFound()
		response.write("The attachments were not found")

	return response


########NEW FILE########
