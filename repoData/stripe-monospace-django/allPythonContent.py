__FILENAME__ = admin
from django.contrib import admin
import models

admin.site.register(models.User)

########NEW FILE########
__FILENAME__ = forms
from django import forms
from django.core.exceptions import NON_FIELD_ERRORS

class MonospaceForm(forms.Form):

  def addError(self, message):
    self._errors[NON_FIELD_ERRORS] = self.error_class([message])

class SignInForm(MonospaceForm):
  
  email = forms.EmailField(
    required = True
  )
  
  password = forms.CharField(
    required = True, 
    widget = forms.PasswordInput(render_value = False)
  )
  
class CardForm(MonospaceForm):
  
  last_4_digits = forms.CharField(
    required = True,
    min_length = 4,
    max_length = 4,
    widget = forms.HiddenInput()
  )
  
  stripe_token = forms.CharField(
    required = True,
    widget = forms.HiddenInput()
  )
  
class UserForm(CardForm):
  
  name = forms.CharField(
    required = True
  )
  
  email = forms.EmailField(
    required = True
  )

  password1 = forms.CharField(
    required = True, 
    widget = forms.PasswordInput(render_value = False),
    label = 'Password'
  )

  password2 = forms.CharField(
    required = True, 
    widget = forms.PasswordInput(render_value = False),
    label = 'Password confirmation'
  )
  
  def clean(self):
    cleaned_data = self.cleaned_data
    password1 = cleaned_data.get('password1')
    password2 = cleaned_data.get('password2')
    if password1 != password2:
      raise forms.ValidationError('Passwords do not match')
    return cleaned_data
  
  
  
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
__FILENAME__ = models
from django.db import models
import bcrypt
from monospace import settings

class User(models.Model):
  name = models.CharField(max_length=255)
  email = models.CharField(max_length=255, unique=True)
  password = models.CharField(max_length=60)
  last_4_digits = models.CharField(max_length=4)
  stripe_id = models.CharField(max_length=255)
  subscribed = models.BooleanField(default=False)
  created_at = models.DateTimeField(auto_now_add=True)
  updated_at = models.DateTimeField(auto_now=True)

  def __str__(self):
    return self.name

  def set_password(self, clear_password):
    salt = bcrypt.gensalt(settings.BCRYPT_ROUNDS)
    self.password = bcrypt.hashpw(clear_password, salt)
  
  def check_password(self, clear_password):
    return bcrypt.hashpw(clear_password, self.password) == self.password
    
########NEW FILE########
__FILENAME__ = settings
import os

# Stripe keys
STRIPE_PUBLISHABLE = 'pk_YT1CEhhujd0bklb2KGQZiaL3iTzj3'
STRIPE_SECRET = 'tGN0bIwXnHdwOa85VABjPdSn8nWY7G7I'

# customized settings
PROJECT_ROOT = os.path.realpath(os.path.dirname(__file__))
SITE_ROOT = os.path.dirname(PROJECT_ROOT)
TIME_ZONE = 'America/Los_Angeles'
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3', 
        'NAME': os.path.join(SITE_ROOT, 'monospace.sqlite'),                      
    }
}
TEMPLATE_DIRS = (os.path.join(PROJECT_ROOT, 'templates'),)
STATICFILES_DIRS = (os.path.join(PROJECT_ROOT, 'static'),)
INSTALLED_APPS = (
  'django.contrib.admin',
  'django.contrib.auth',
  'django.contrib.contenttypes',
  'django.contrib.messages',
  'django.contrib.sessions',
  'django.contrib.sites',
  'django.contrib.staticfiles',
  'monospace'
)
BCRYPT_ROUNDS = 15

# default Django settings
DEBUG = True
TEMPLATE_DEBUG = DEBUG
ADMINS = ()
MANAGERS = ADMINS
LANGUAGE_CODE = 'en-us'
SITE_ID = 1
USE_I18N = True
USE_L10N = True
MEDIA_ROOT = ''
MEDIA_URL = ''
STATIC_ROOT = ''
STATIC_URL = '/static/'
ADMIN_MEDIA_PREFIX = '/static/admin/'

STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
)
SECRET_KEY = 'lb-06%rmn$fmhhu!mr@3nc(&$0985qvddj%_5=t@94x@#@jcs@'
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
ROOT_URLCONF = 'monospace.urls'
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
from django.conf.urls.defaults import patterns, include, url
from django.contrib import admin

from monospace import views

admin.autodiscover()

urlpatterns = patterns('',
    url(r'^$', views.home, name='home'),
    url(r'^sign_in$', views.sign_in, name='sign_in'),
    url(r'^sign_out$', views.sign_out, name='sign_out'),
    url(r'^register$', views.register, name='register'),
    url(r'^edit$', views.edit, name='edit'),
    
    url(r'^admin/doc/', include('django.contrib.admindocs.urls')),
    url(r'^admin/', include(admin.site.urls)),
)

########NEW FILE########
__FILENAME__ = views
import datetime

from django.db import IntegrityError
from django.http import HttpResponseRedirect
from django.shortcuts import render_to_response, redirect
from django.template import RequestContext
import stripe

from monospace.forms import *
from monospace.models import *
import monospace.settings as settings

stripe.api_key = settings.STRIPE_SECRET

def soon():
  soon = datetime.date.today() + datetime.timedelta(days=30)
  return {'month': soon.month, 'year': soon.year}

def home(request):
  uid = request.session.get('user')
  if uid is None:
    return render_to_response('home.html')
  else:
    return render_to_response('user.html', {'user': User.objects.get(pk=uid)})

def sign_in(request):
  user = None
  if request.method == 'POST':
    form = SignInForm(request.POST)
    if form.is_valid():
      results = User.objects.filter(email=form.cleaned_data['email'])
      if len(results) == 1:
        if results[0].check_password(form.cleaned_data['password']):
          request.session['user'] = results[0].pk
          return HttpResponseRedirect('/')
        else:
          form.addError('Incorrect email address or password')
      else:
        form.addError('Incorrect email address or password')
  else:
    form = SignInForm()
    
  print form.non_field_errors()

  return render_to_response(
    'sign_in.html',
    {
      'form': form,
      'user': user
    },
    context_instance=RequestContext(request)
  )

def sign_out(request):
  del request.session['user']
  return HttpResponseRedirect('/')

def register(request):
  user = None
  if request.method == 'POST':
    form = UserForm(request.POST)
    if form.is_valid():

      customer = stripe.Customer.create(
        description = form.cleaned_data['email'],
        card = form.cleaned_data['stripe_token'],
        plan = 'basic'
      )

      user = User(
        name = form.cleaned_data['name'],
        email = form.cleaned_data['email'],
        last_4_digits = form.cleaned_data['last_4_digits'],
        stripe_id = customer.id
      )
      user.set_password(form.cleaned_data['password1'])

      try:
        user.save()
      except IntegrityError:
        form.addError(user.email + ' is already a member')
      else:
        request.session['user'] = user.pk
        return HttpResponseRedirect('/')

  else:
    form = UserForm()

  return render_to_response(
    'register.html',
    {
      'form': form,
      'months': range(1, 12),
      'publishable': settings.STRIPE_PUBLISHABLE,
      'soon': soon(),
      'user': user,
      'years': range(2011, 2036),
    },
    context_instance=RequestContext(request)
  )

def edit(request):
  uid = request.session.get('user')
  if uid is None:
    return HttpResponseRedirect('/')
  user = User.objects.get(pk=uid)
  if request.method == 'POST':
    form = CardForm(request.POST)
    if form.is_valid():

      customer = stripe.Customer.retrieve(user.stripe_id)
      customer.card = form.cleaned_data['stripe_token']
      customer.save()

      user.last_4_digits = form.cleaned_data['last_4_digits']
      user.stripe_id = customer.id
      user.save()

      return HttpResponseRedirect('/')

  else:
    form = CardForm()

  return render_to_response(
    'edit.html',
    {
      'form': form,
      'publishable': settings.STRIPE_PUBLISHABLE,
      'soon': soon(),
      'months': range(1, 12),
      'years': range(2011, 2036)
    },
    context_instance=RequestContext(request)
  )



########NEW FILE########
