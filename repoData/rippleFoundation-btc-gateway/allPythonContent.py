__FILENAME__ = manage
#!/usr/bin/env python
import os
import sys

if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "pythonnexus.settings")

    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)

########NEW FILE########
__FILENAME__ = admin
from django.contrib import admin
from pythonnexus.models import BitcoinInEntry, BitcoinOutEntry
admin.site.register(BitcoinInEntry)
admin.site.register(BitcoinOutEntry)

########NEW FILE########
__FILENAME__ = bitcoinlistener
import time
import json

from pythonnexus import models, settings

from jsonrpc import ServiceProxy, JSONRPCException #Use this to communicate with the locally-running bitcoind instance.
from ws4py.client.threadedclient import WebSocketClient #Use this to communicate with the remotely-running rippled instance.

rpcuser=settings.rpcuser
rpcpassword=settings.rpcpassword
RIPPLE_WEBSOCKET_URL=settings.RIPPLE_WEBSOCKET_URL
MY_RIPPLE_ADDRESS=settings.MY_RIPPLE_ADDRESS
MY_SECRET_KEY=settings.MY_SECRET_KEY


## INTERACTING WITH BITCOIN

bitcoin_connection = ServiceProxy("http://" + rpcuser + ":" + rpcpassword + "@127.0.0.1:8332")

def validate_bitcoin_address(address):
	return bitcoin_connection.validateaddress(address)["isvalid"]

def generate_bitcoin_address():
	while True:
		address = bitcoin_connection.getnewaddress()
		if models.BitcoinInEntry.objects.filter(bitcoin_address=address):
			print "Address already used; trying again" #Practically speaking, this will never happen.
		else:
			break
	return address

def amount_received_at_address(bitcoin_address):
	amount = bitcoin_connection.getreceivedbyaddress(bitcoin_address)
	print amount, "bitcoins received at", bitcoin_address
	return amount

def send_bitcoins_to(bitcoin_address, amount):
	try:
		x = bitcoin_connection.sendtoaddress(bitcoin_address, float(amount))
		print "Sent bitcoins"
	except JSONRPCException, e:
		raise Exception(repr(e.error))

		
## INTERACTING WITH RIPPLE
 
class IouClientConnector(WebSocketClient):
	connected = False
	
	def opened(self):
		self.connected = True
		#Subscribe to messages about receiving Ripple IOUs.
		request = {
			'command'      : 'subscribe',
			'accounts'     : [ MY_RIPPLE_ADDRESS ],
			'username'     : rpcuser,
			'password'     : rpcpassword,
		}
		self.send(json.dumps(request))

	def received_message(self, m):
		#Process the message, to see if we've received or sent Ripple IOUs, or done something else, and respond accordingly.
		print m
		message = json.loads(str(m))
		if message["status"] == "error":
			if "error" in message                              \
			 and message["error"] == "dstActMalformed"         \
			 and "request" in message                          \
			 and "tx_json" in message["request"]               \
			 and "Destination" in message["request"]["tx_json"]:
				malformed_address = message["request"]["tx_json"]["Destination"]
				print "Error: Destination address is malformed. We will no longer try to send to this address.",\
				 "Whoever sent us Bitcoins and asked for IOUs to be sent to this Ripple address is out of luck."
				mark_as_done(malformed_address)
			else:
				print "Error: another kind of error occurred."
		elif message["status"] == "success":
			print "The message had a status of success, but we'll wait for the closing of the ledger to figure out what to do."
		elif message["status"] == "closed":
			if message["engine_result"]=="tesSUCCESS"                  \
			 and message["type"] == "account"                          \
			 and "transaction" in message                              \
			 and "Destination" in message["transaction"]               \
			 and "TransactionType" in message["transaction"]           \
			 and message["transaction"]["TransactionType"] == "Payment"\
			 and "Amount" in message["transaction"]                    \
			 and "currency" in message["transaction"]["Amount"]        \
			 and message["transaction"]["Amount"]["currency"] == "BTC":
				destination = message["transaction"]["Destination"]
				if destination == MY_RIPPLE_ADDRESS:
					if "DestinationTag" in message["transaction"]:
						#This means that someone just sent us IOUs, and we're supposed to send them bitcoins.
						amount = message["transaction"]["Amount"]["value"]
						try:
							transaction_code = message["transaction"]["DestinationTag"]
							entry = models.BitcoinOutEntry.objects.get(pk=transaction_code)
							entry.amount_owed = amount
							entry.save()
							print "On the next execution of the 'Listening!' loop, we will attempt to send",\
							 amount, "bitcoins to", entry.bitcoin_address
						except:
							print "Could not find this DestinationTag in the database. We'll send the IOUs back if we can."
							self.send_ious_to(amount, message["transaction"]["Account"])
					else:
						print "Someone just sent us IOUs without a DestinationTag. This should not have been allowed if our account was set up correctly."
				else: 	
					print "The ledger just closed on a BTC-IOU payment from us to someone else that has succeeded."
					mark_as_done(destination)
			else:
				print "The ledger just closed on some other transaction that involves us but doesn't require us to do anything."
		else:
			print "The message status was not error, success, or closed, and was not recognized as any other kind of transaction."
	
	def send_ious_to(self, amount, ripple_address):
		request = {
			'command' : 'submit',
			'tx_json' : {
				'TransactionType' : 'Payment',
				'Account'         : MY_RIPPLE_ADDRESS,
				'Destination'     : ripple_address,
				'Amount'          : {
					'currency' : 'BTC',
					'value'    : str(amount),
					'issuer'   : MY_RIPPLE_ADDRESS,
				}
			},
			'secret'  : MY_SECRET_KEY,
		}
		self.send(json.dumps(request))
		
	def closed(self, code="", reason=""):
		if not self.connected:
			print "Closed down: Could not open connection."
		else:
			print "Closed down", code, reason
			
			
def mark_as_done(ripple_address):
	print "Marking as done:", ripple_address
	entries = models.BitcoinInEntry.objects.filter(done_yet=False).filter(ripple_address=ripple_address)
	if len(entries) > 1:
		print "ERROR! There is more than one entry in the database with that ripple_address!"        ,\
		 "Having received bitcoins at one of the associated bitcoin_address-es, and having received" ,\
		 "notification that our payment of IOUs to this ripple_address was successful, we don't know",\
		 "which entry to mark_as_done!"
		raise
	if len(entries) == 0:
		print "WARNING! Attempting to mark_as_done a ripple_address which exists nowhere among the",\
		 "BitcoinInEntrys that have not been done_yet. This may have happened as a result of you",\
		 "manually sending IOUs to someone apart from the web interface. No database entries will be changed."
	else:
		for entry in entries:
			entry.done_yet = True
			entry.save()
		print "Marked ripple_address", ripple_address, "as done."


def listen():
	ws = IouClientConnector(RIPPLE_WEBSOCKET_URL, protocols=['http-only', 'chat'])
	ws.connect()
	while True:
		time.sleep(60) #Every minute, check for received bitcoins, and attempt to send bitcoins to those who are owed.
		print "Listening!"
		btc_in_list = models.BitcoinInEntry.objects.filter(done_yet=False)
		btc_out_list = models.BitcoinOutEntry.objects.filter(done_yet=False).filter(amount_owed__gt=0)
		try: #All the people who've sent us bitcoins, and are waiting for IOUs.
			for entry in btc_in_list:
				bitcoin_address = entry.bitcoin_address
				ripple_address = entry.ripple_address
				amount_received = amount_received_at_address(bitcoin_address)
				print bitcoin_address, "has received", amount_received, "bitcoins from the owner of ripple address", ripple_address
				if amount_received > 0:
					ws.send_ious_to(amount_received, ripple_address)
		except Exception, e:
			print "An error occurred in traversing btc_in_list:", e
		try: #All the people who've sent us BTC-IOUs, and are waiting for bitcions.
			for entry in btc_out_list:
				bitcoin_address = entry.bitcoin_address
				amount_owed = entry.amount_owed
				print "We need to send", amount_owed, "bitcoins to", bitcoin_address
				try:
					send_bitcoins_to(bitcoin_address, amount_owed)
					entry.done_yet = True
					entry.save()
					print "Marked bitcoin_address", bitcoin_address, "as done."
				except Exception, ee:
					print "send_bitcoins_to failed:", ex, "(This will be attempted next time.)"
		except Exception, e:
			print "An error occurred in traversing btc_out_list:", e
		print "Finished the loop. Waiting..."
########NEW FILE########
__FILENAME__ = models
from django.db import models

#When someone gives us a Ripple address, and we wait to receive bitcoins
#from them, and then send Ripple IOUs to them.
class BitcoinInEntry(models.Model):
	done_yet = models.BooleanField(default=False)
	bitcoin_address = models.CharField(max_length=34, unique=True)
	ripple_address = models.CharField(max_length=40)

#When someone gives us a Bitcoin address, and we wait to receive IOUs
#from them, and then send bitcoins to that address.
class BitcoinOutEntry(models.Model):
    done_yet = models.BooleanField(default=False)
    amount_owed = models.FloatField(default=0.0) #How many bitcoins are we supposed to send?
    bitcoin_address = models.CharField(max_length=34)

########NEW FILE########
__FILENAME__ = settings-example
# Django settings for pythonnexus project.

DEBUG = True
TEMPLATE_DEBUG = DEBUG

ADMINS = (
    # ('Your Name', 'your_email@example.com'),
)

MANAGERS = ADMINS

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3', # Add 'postgresql_psycopg2', 'mysql', 'sqlite3' or 'oracle'.
        'NAME': 'C:/Users/Anna/Desktop/pythonnexus/database.db',                      # Or path to database file if using sqlite3.
        'USER': '',                      # Not used with sqlite3.
        'PASSWORD': '',                  # Not used with sqlite3.
        'HOST': '',                      # Set to empty string for localhost. Not used with sqlite3.
        'PORT': '',                      # Set to empty string for default. Not used with sqlite3.
    }
}

# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
# In a Windows environment this must be set to your system time zone.
TIME_ZONE = 'America/Los_Angeles'

# Language code for this installation. All choices can be found here:
# http://www.i18nguy.com/unicode/language-identifiers.html
LANGUAGE_CODE = 'en-us'

SITE_ID = 1

# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = True

# If you set this to False, Django will not format dates, numbers and
# calendars according to the current locale.
USE_L10N = True

# If you set this to False, Django will not use timezone-aware datetimes.
USE_TZ = True

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
STATIC_ROOT = ''

# URL prefix for static files.
# Example: "http://media.lawrence.com/static/"
STATIC_URL = '/static/'

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
SECRET_KEY = '!s-9%##jh9(n1f+aost_93x&amp;mll(#hp(cckx^o60b5&amp;5ymc+ve'

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
    # Uncomment the next line for simple clickjacking protection:
    # 'django.middleware.clickjacking.XFrameOptionsMiddleware',
)

ROOT_URLCONF = 'pythonnexus.urls'

# Python dotted path to the WSGI application used by Django's runserver.
WSGI_APPLICATION = 'pythonnexus.wsgi.application'

TEMPLATE_DIRS = (
    # Put strings here, like "/home/html/django_templates" or "C:/www/django/templates".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
	"C:/Users/Anna/Desktop/pythonnexus",
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
	'pythonnexus'
)

# A sample logging configuration. The only tangible logging
# performed by this configuration is to send an email to
# the site admins on every HTTP 500 error when DEBUG=False.
# See http://docs.djangoproject.com/en/dev/topics/logging for
# more details on how to customize your logging configuration.
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






#Variables for interacting with Bitcoin and Ripple
rpcuser="bitcoinrpc" #Can be found in bitcoin.conf, which is located in the same directory as wallet.dat (on Windows, C:\Users\You\AppData\Roaming\Bitcoin)
rpcpassword="218qBhMbD6HK5hJJ2Kmgk3GbJ7DUrnZy5oNmZeJgjFSn" #Ditto
RIPPLE_WEBSOCKET_URL = 'wss://s1.ripple.com:51233' #The URL of the Websocket address of the Ripple server you want to use to access the network.
MY_RIPPLE_ADDRESS = 'r4oM4CpUQAsu77Jb81xMFBWWUeGxpZ9xWp' #The public address of your Ripple account.
MY_SECRET_KEY = 'snAEtMTwKMJ1539MX2AbWiQKDC4FM' #The secret key for your Ripple account.
########NEW FILE########
__FILENAME__ = urls
from django.conf.urls import patterns, include, url

from django.contrib import admin
admin.autodiscover()

urlpatterns = patterns('',
	url(r'^$', 'pythonnexus.views.index', name='index'),
	url(r'^deposit/', 'pythonnexus.views.deposit', name='deposit'),
	url(r'^redeem/', 'pythonnexus.views.redeem', name='redeem'),
    url(r'^bcin/$', 'pythonnexus.views.bcin', name='bcin'),
	url(r'^bcout/$', 'pythonnexus.views.bcout', name='bcout'),

	url(r'^admin/', include(admin.site.urls)),
)

########NEW FILE########
__FILENAME__ = views
from django.http import HttpResponse, HttpResponseRedirect
from django.template import Context, RequestContext, loader

from pythonnexus.models import BitcoinInEntry, BitcoinOutEntry
import pythonnexus.bitcoinlistener as bitcoinlistener

def index(request):
    template = loader.get_template('pythonnexus/index.html')
    return HttpResponse(template.render(Context({})))
	
	
def deposit(request):
    template = loader.get_template('pythonnexus/deposit.html')
    return HttpResponse(template.render(RequestContext(request,{})))

def redeem(request):
    template = loader.get_template('pythonnexus/redeem.html')
    return HttpResponse(template.render(RequestContext(request,{})))

def bcin(request):
	already = False
	ripple_address=request.POST['ripple_address']
	if ripple_address:
		#For any ripple_address, there should be no more than one entry with that ripple_address and with done_yet=False.
		entries_with_this_ra = BitcoinInEntry.objects.filter(ripple_address=ripple_address).filter(done_yet=False)
		if entries_with_this_ra:
			bitcoin_address = entries_with_this_ra[0].bitcoin_address
			already = True
		else:
			bitcoin_address=bitcoinlistener.generate_bitcoin_address() #Generate a Bitcoin address and add it to our wallet.
			bcinentry = BitcoinInEntry.objects.create(ripple_address=ripple_address, bitcoin_address = bitcoin_address)
		template = loader.get_template('pythonnexus/depositsuccess.html')
		context = RequestContext(request, {
			'bitcoin_address':bitcoin_address,
			'ripple_address':ripple_address,
			'already':already})	
	else:
		context = RequestContext(request, {
			'error_message': 'You have to enter something!'
		})	
		template = loader.get_template('pythonnexus/deposit.html')
	return HttpResponse(template.render(context))
	
def bcout(request):
	bitcoin_address=request.POST['bitcoin_address'] #This is easier, because we can use the primary key (bcoutentry.id) to identify customers.
	if bitcoinlistener.validate_bitcoin_address(bitcoin_address):
		bcoutentry = BitcoinOutEntry.objects.create(bitcoin_address = bitcoin_address)
		template = loader.get_template('pythonnexus/redeemsuccess.html')
		context = RequestContext(request, {
			'bitcoin_address':bitcoin_address,
			'ripple_address':bitcoinlistener.MY_RIPPLE_ADDRESS,
			'id':bcoutentry.id
		})
	else:
		context = RequestContext(request, {
			'error_message': 'This Bitcoin address is not valid. Please try again.'
		})	
		template = loader.get_template('pythonnexus/redeem.html')
	return HttpResponse(template.render(context))
########NEW FILE########
__FILENAME__ = wsgi
"""
WSGI config for pythonnexus project.

This module contains the WSGI application used by Django's development server
and any production WSGI deployments. It should expose a module-level variable
named ``application``. Django's ``runserver`` and ``runfcgi`` commands discover
this application via the ``WSGI_APPLICATION`` setting.

Usually you will have the standard Django WSGI application here, but it also
might make sense to replace the whole Django WSGI application with a custom one
that later delegates to the Django one. For example, you could introduce WSGI
middleware here, or combine a Django application with an application of another
framework.

"""
import os
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "pythonnexus.settings")

#Listen for transactions at the same time that we are serving HTTP requests from users.
import threading
import bitcoinlistener
_thread = threading.Thread(target=bitcoinlistener.listen)
_thread.setDaemon(True)
_thread.start()

# This application object is used by any WSGI server configured to use this
# file. This includes Django's development server, if the WSGI_APPLICATION
# setting points here.
from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()

# Apply WSGI middleware here.
# from helloworld.wsgi import HelloWorldApplication
# application = HelloWorldApplication(application)

########NEW FILE########
