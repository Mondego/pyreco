__FILENAME__ = manage
#!/usr/bin/env python

#add faq app to python path
import sys
from os.path import abspath, dirname, join
sys.path.append(abspath(join(dirname(__file__), '..')))

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
# Django settings for [name] project.
import os, os.path, sys

#set DEBUG = False and django will send exception emails
DEBUG = True 
TEMPLATE_DEBUG = DEBUG
PROJECT_DIR = os.path.dirname(__file__)

SUBSCRIPTION_DUPES_ALLOWED = True

DATABASE_ENGINE = 'sqlite3'           # 'postgresql_psycopg2', 'postgresql', 'mysql', 'sqlite3' or 'oracle'.
DATABASE_NAME = 'dev.db'             # Or path to database file if using sqlite3.
DATABASE_USER = ''             # Not used with sqlite3.
DATABASE_PASSWORD = ''         # Not used with sqlite3.
DATABASE_HOST = ''             # Set to empty string for localhost. Not used with sqlite3.
DATABASE_PORT = ''             # Set to empty string for default. Not used with sqlite3.

# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be avilable on all operating systems.
# If running in a Windows environment this must be set to the same as your
# system time zone.
TIME_ZONE = 'America/New_York'

# Language code for this installation. All choices can be found here:
# http://www.i18nguy.com/unicode/language-identifiers.html
LANGUAGE_CODE = 'en-us'

SITE_ID = 1

# If you set this to False, Django will make some optimizations so as not
# to load the internationalization machinery.
USE_I18N = True

# Absolute path to the directory that holds media.
# Example: "/home/media/media.lawrence.com/"
MEDIA_ROOT = os.path.join(PROJECT_DIR, 'media')

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash if there is a path component (optional in other cases).
# Examples: "http://media.lawrence.com", "http://example.com/media/"
#MEDIA_URL = 'http://127.0.0.1:8000/site_media/'
MEDIA_URL = '/media/' #

# URL prefix for admin media -- CSS, JavaScript and images. Make sure to use a
# trailing slash.
# Examples: "http://foo.com/media/", "/media/".
ADMIN_MEDIA_PREFIX = '/admin_media/'

# Make this unique, and don't share it with anybody.
SECRET_KEY = 'c#zi(mv^n+4te_sy$hpb*zdo7#f7ccmp9ro84yz9bmmfqj9y*c'

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.load_template_source',
    'django.template.loaders.app_directories.load_template_source',
)

TEMPLATE_CONTEXT_PROCESSORS = (
    'django.core.context_processors.auth',
	'django.core.context_processors.media',
)

MIDDLEWARE_CLASSES = (
	#'django.middleware.cache.CacheMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.middleware.doc.XViewMiddleware',
)

ROOT_URLCONF = 'example.urls'

INTERNAL_IPS = (
    '127.0.0.1',
)

TEMPLATE_DIRS = (
    # Put strings here, like "/home/html/django_templates" or "C:/www/django/templates".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
    [os.path.join(PROJECT_DIR, "templates")]
)

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.admin',
    'newsletter',
)


try:
   from local_settings import *
except ImportError:
   pass

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import *
from django.contrib import admin
from django.conf import settings
from django.views.generic.simple import direct_to_template

admin.autodiscover()

urlpatterns = patterns('',

    (r'^newsletter/', include('newsletter.urls')), 
    (r'^admin/(.*)', admin.site.root),
    url (
        r'^$',
        direct_to_template,
        {'template': 'home.html'},
        name = 'home',
        ),
)

urlpatterns += patterns('',
	(r'^media/(?P<path>.*)$', 'django.views.static.serve', {'document_root': settings.MEDIA_ROOT}),
)



########NEW FILE########
__FILENAME__ = views

########NEW FILE########
__FILENAME__ = admin
from django.contrib import admin
from newsletter.models import Subscription
from newsletter.forms import SubscriptionForm

class SubscriptionAdmin(admin.ModelAdmin):
    
    list_display = ('email', 'subscribed', 'created_on', )
    search_fields = ('email',)
    list_filter = ('subscribed',)
    
admin.site.register(Subscription, SubscriptionAdmin)

########NEW FILE########
__FILENAME__ = csv
################################################################
# Source: http://www.djangosnippets.org/snippets/1151/
# Many thanks!
################################################################

import datetime

from django.db.models.query import QuerySet, ValuesQuerySet
from django.http import HttpResponse

class ExcelResponse(HttpResponse):

   def __init__(self, data, output_name='excel_data', headers=None,
                force_csv=False, encoding='utf8'):
   
       # Make sure we've got the right type of data to work with
       valid_data = False
       if isinstance(data, ValuesQuerySet):
           data = list(data)
       elif isinstance(data, QuerySet):
           data = list(data.values())
       if hasattr(data, '__getitem__'):
           if isinstance(data[0], dict):
               if headers is None:
                   headers = data[0].keys()
               data = [[row[col] for col in headers] for row in data]
               data.insert(0, headers)
           if hasattr(data[0], '__getitem__'):
               valid_data = True
       assert valid_data is True, "ExcelResponse requires a sequence of sequences"
   
       import StringIO
       output = StringIO.StringIO()
       # Excel has a limit on number of rows; if we have more than that, make a csv
       use_xls = False
       if len(data) <= 65536 and force_csv is not True:
           try:
               import xlwt
           except ImportError:
               # xlwt doesn't exist; fall back to csv
               pass
           else:
               use_xls = True
       if use_xls:
           book = xlwt.Workbook(encoding=encoding)
           sheet = book.add_sheet('Sheet 1')
           styles = {'datetime': xlwt.easyxf(num_format_str='yyyy-mm-dd hh:mm:ss'),
                     'date': xlwt.easyxf(num_format_str='yyyy-mm-dd'),
                     'time': xlwt.easyxf(num_format_str='hh:mm:ss'),
                     'default': xlwt.Style.default_style}
   
           for rowx, row in enumerate(data):
               for colx, value in enumerate(row):
                   if isinstance(value, datetime.datetime):
                       cell_style = styles['datetime']
                   elif isinstance(value, datetime.date):
                       cell_style = styles['date']
                   elif isinstance(value, datetime.time):
                       cell_style = styles['time']
                   else:
                       cell_style = styles['default']
                   sheet.write(rowx, colx, value, style=cell_style)
           book.save(output)
           mimetype = 'application/vnd.ms-excel'
           file_ext = 'xls'
       else:
           for row in data:
               out_row = []
               for value in row:
                   if not isinstance(value, basestring):
                       value = unicode(value)
                   value = value.encode(encoding)
                   out_row.append(value.replace('"', '""'))
               output.write('"%s"\n' %
                            '","'.join(out_row))            
           mimetype = 'text/csv'
           file_ext = 'csv'
       output.seek(0)
       super(ExcelResponse, self).__init__(content=output.getvalue(),
                                           mimetype=mimetype)
       self['Content-Disposition'] = 'attachment;filename="%s.%s"' % \
           (output_name.replace('"', '\"'), file_ext)

########NEW FILE########
__FILENAME__ = forms
from django import forms
from django.conf import settings
from django.utils.translation import ugettext_lazy as _
from newsletter.models import Subscription

class SubscriptionForm(forms.ModelForm):
    '''
    TODO:
    
    '''

    class Meta:
        model = Subscription


        
        
        

########NEW FILE########
__FILENAME__ = models
from django.db import models
from django.utils.translation import ugettext_lazy as _
from django.conf import settings
import datetime

class SubscriptionBase(models.Model):
    '''
    A newsletter subscription base.
    
    '''

    subscribed = models.BooleanField(_('subscribed'), default=True)
    email = models.EmailField(_('email'), unique=True)
    created_on = models.DateField(_("created on"), blank=True)
    updated_on = models.DateField(_("updated on"), blank=True)
    
    class Meta:
        abstract = True
    
    @classmethod
    def is_subscribed(cls, email):
        '''
        Concept inspired by Satchmo. Thanks guys!
        
        '''
        try:
            return cls.objects.get(email=email).subscribed
        except cls.DoestNotExist, e:
            return False
         
    
    def __unicode__(self):
        return u'%s' % (self.email)
        
    def save(self, *args, **kwargs):
        self.updated_on = datetime.date.today()
        if not self.created_on:
            self.created_on = datetime.date.today()
        super(SubscriptionBase,self).save(*args, **kwargs)

class Subscription(SubscriptionBase):
    '''
    Generic subscription
    
    '''
        
    def save(self, *args, **kwargs):
        super(Subscription,self).save()

########NEW FILE########
__FILENAME__ = tests
from django.test import TestCase
from django.core.urlresolvers import reverse

class ShopTest(TestCase):

    def setUp(self):
        pass
        
    def tearDown(self):
        pass

    def test_user_subscribe_twice_should_not_throw_error(self):
        post_data = {'email': "test@example.com", 'subscribed': True}
        for i in range(2):
            response = self.client.post(reverse('subscribe_detail'), post_data)
            self.assertTemplateUsed(response, "newsletter/success.html")

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import *
from django.contrib import admin
from django.views.generic.simple import direct_to_template
from django.conf import settings

admin.autodiscover()

urlpatterns = patterns('newsletter.views',

    url (r'^admin/newsletter/subscription/download/csv/$', 
        view='generate_csv',
        name='download_csv',
    ),
    
    url (r'^$', 
        view='subscribe_detail',
        name='subscribe_detail',
    ),

)

########NEW FILE########
__FILENAME__ = views
from django.shortcuts import render_to_response, get_object_or_404
from django.template import RequestContext
from django.http import *
from django.conf import settings
from django.template.loader import render_to_string
from django.db.models import get_model

from newsletter.models import Subscription
from newsletter.forms import SubscriptionForm
from newsletter.core import csv

import datetime
import re

from django.contrib.admin.views.decorators import staff_member_required

@staff_member_required
def generate_csv(request, model_str="newsletter.subscription", data=None):
    '''
    TODO:
    
    '''

    if not data:
        model = get_model(*model_str.split('.'))
        data = model._default_manager.filter(subscribed=True)
    
    if len(data) == 0:
        data = [["no subscriptions"],]
    return csv.ExcelResponse(data)

def subscribe_detail(request, form_class=SubscriptionForm, 
        template_name='newsletter/subscribe.html',  
        success_template='newsletter/success.html', extra_context={}, 
        model_str="newsletter.subscription"):

    if request.POST:   
        try:
            model = get_model(*model_str.split('.')) 
            instance = model._default_manager.get(email=request.POST['email'])
        except model.DoesNotExist: 
            instance = None
        form = form_class(request.POST, instance = instance)
        if form.is_valid():
            subscribed = form.cleaned_data["subscribed"]
            
            form.save()
            if subscribed:
                message = getattr(settings,
                    "NEWSLETTER_OPTIN_MESSAGE", "Success! You've been added.")
            else:
                message = getattr(settings,
                     "NEWSLETTER_OPTOUT_MESSAGE", 
                     "You've been removed. Sorry to see ya go.")          

            extra = {
                'success': True,
                'message': message,
                'form': form_class(),
            }
            extra.update(extra_context)
            
            return render_to_response(success_template, extra, 
                 RequestContext(request))
    else:
        form = form_class()
    
    extra = {
        'form': form,
    }
    extra.update(extra_context)
    
    return render_to_response(template_name, extra, RequestContext(request))


########NEW FILE########
