__FILENAME__ = forms
from django import newforms as forms
from django.core.validators import alnum_re

from django.contrib.auth.models import User
from emailconfirmation.models import EmailAddress

# this code based in-part on django-registration

class SignupForm(forms.Form):
    
    username = forms.CharField(label="Username", max_length=30, widget=forms.TextInput())
    password1 = forms.CharField(label="Password", widget=forms.PasswordInput())
    password2 = forms.CharField(label="Password (again)", widget=forms.PasswordInput())
    email = forms.EmailField(label="Email (optional)", required=False, widget=forms.TextInput())
    
    def clean_username(self):
        if not alnum_re.search(self.cleaned_data["username"]):
            raise forms.ValidationError(u"Usernames can only contain letters, numbers and underscores.")
        try:
            user = User.objects.get(username__exact=self.cleaned_data["username"])
        except User.DoesNotExist:
            return self.cleaned_data["username"]
        raise forms.ValidationError(u"This username is already taken. Please choose another.")
    
    def clean(self):
        if "password1" in self.cleaned_data and "password2" in self.cleaned_data:
            if self.cleaned_data["password1"] != self.cleaned_data["password2"]:
                raise forms.ValidationError(u"You must type the same password each time.")
        return self.cleaned_data
    
    def save(self):
        print self.cleaned_data
        username = self.cleaned_data["username"]
        email = self.cleaned_data["email"]
        password = self.cleaned_data["password1"]
        new_user = User.objects.create_user(username, email, password)
        if email:
            self.user.message_set.create(message="Confirmation email sent to %s" % email)
            EmailAddress.objects.add_email(new_user, email)
        return username, password # required for authenticate()


class AddEmailForm(forms.Form):
    
    def __init__(self, data=None, user=None):
        super(AddEmailForm, self).__init__(data=data)
        self.user = user
    
    email = forms.EmailField(label="Email", required=True, widget=forms.TextInput())
    
    def clean_email(self):
        try:
            EmailAddress.objects.get(user=self.user, email=self.cleaned_data["email"])
        except EmailAddress.DoesNotExist:
            return self.cleaned_data["email"]
        raise forms.ValidationError(u"This email address already associated with this account.")
    
    def save(self):
        self.user.message_set.create(message="Confirmation email sent to %s" % self.cleaned_data["email"])
        return EmailAddress.objects.add_email(self.user, self.cleaned_data["email"])
        
########NEW FILE########
__FILENAME__ = models
from django.db import models

# Create your models here.

########NEW FILE########
__FILENAME__ = views
from django.shortcuts import render_to_response
from django.http import HttpResponseRedirect
from django.contrib.auth import authenticate, login

from forms import SignupForm, AddEmailForm
from emailconfirmation.models import EmailAddress, EmailConfirmation

def signup(request):
    if request.method == "POST":
        form = SignupForm(request.POST)
        if form.is_valid():
            username, password = form.save()
            user = authenticate(username=username, password=password)
            login(request, user)
            return HttpResponseRedirect("/")
    else:
        form = SignupForm()
    return render_to_response("signup.html", {
        "form": form,
    })

def homepage(request):
    if request.method == "POST" and request.user.is_authenticated():
        if request.POST["action"] == "add":
            add_email_form = AddEmailForm(request.POST, request.user)
            if add_email_form.is_valid():
                add_email_form.save()
        elif request.POST["action"] == "send":
            email = request.POST["email"]
            try:
                email_address = EmailAddress.objects.get(user=request.user, email=email)
                request.user.message_set.create(message="Confirmation email sent to %s" % email)
                EmailConfirmation.objects.send_confirmation(email_address)
            except EmailAddress.DoesNotExist:
                pass
            add_email_form = AddEmailForm()
    else:
        add_email_form = AddEmailForm()
    
    return render_to_response("homepage.html", {
        "user": request.user,
        "messages": request.user.get_and_delete_messages(),
        "add_email_form": add_email_form,
    })


########NEW FILE########
__FILENAME__ = manage
#!/usr/bin/env python
import os, sys
from django.core.management import execute_manager
sys.path.insert(0, os.path.abspath('./..'))
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
# Django settings for devproject project.

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
MEDIA_ROOT = ''

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash if there is a path component (optional in other cases).
# Examples: "http://media.lawrence.com", "http://example.com/media/"
MEDIA_URL = ''

# URL prefix for admin media -- CSS, JavaScript and images. Make sure to use a
# trailing slash.
# Examples: "http://foo.com/media/", "/media/".
ADMIN_MEDIA_PREFIX = '/media/'

# Make this unique, and don't share it with anybody.
SECRET_KEY = '__u6o67ep5$%jm&$glnt*$y)rl*6b$ys7i)qtk6nxnc69xo-nu'

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
    'django.middleware.doc.XViewMiddleware',
)

ROOT_URLCONF = 'devproject.urls'

import os.path

TEMPLATE_DIRS = (
    os.path.join(os.path.dirname(__file__), "templates"),
)

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.admin',
    'emailconfirmation',
    'devtest',
)

LOGIN_REDIRECT_URL = "/"

EMAIL_CONFIRMATION_DAYS = 2
# DEFAULT_FROM_EMAIL = "noreply@example.com"

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import *
from django.contrib import admin

urlpatterns = patterns('',
    
    (r'^$', 'devtest.views.homepage'),
    
    (r'^signup/$', 'devtest.views.signup'),
    (r'^login/$', 'django.contrib.auth.views.login', {"template_name": "login.html"}),
    (r'^logout/$', 'django.contrib.auth.views.logout', {"template_name": "logout.html"}),
    
    (r'^confirm_email/(\w+)/$', 'emailconfirmation.views.confirm_email'),
    
    (r'^admin/(.*)', admin.site.root),
)

########NEW FILE########
__FILENAME__ = admin
from django.contrib import admin
from emailconfirmation.models import EmailAddress, EmailConfirmation

admin.site.register(EmailAddress)
admin.site.register(EmailConfirmation)

########NEW FILE########
__FILENAME__ = models
from datetime import datetime, timedelta
from random import random

from django.conf import settings
from django.db import models, IntegrityError
from django.template.loader import render_to_string
from django.core.urlresolvers import reverse, NoReverseMatch
from django.contrib.sites.models import Site
from django.contrib.auth.models import User
from django.utils.hashcompat import sha_constructor
from django.utils.translation import gettext_lazy as _

from emailconfirmation.signals import email_confirmed
from emailconfirmation.utils import get_send_mail
send_mail = get_send_mail()

# this code based in-part on django-registration

class EmailAddressManager(models.Manager):

    def add_email(self, user, email):
        try:
            email_address = self.create(user=user, email=email)
            EmailConfirmation.objects.send_confirmation(email_address)
            return email_address
        except IntegrityError:
            return None

    def get_primary(self, user):
        try:
            return self.get(user=user, primary=True)
        except EmailAddress.DoesNotExist:
            return None

    def get_users_for(self, email):
        """
        returns a list of users with the given email.
        """
        # this is a list rather than a generator because we probably want to
        # do a len() on it right away
        return [address.user for address in EmailAddress.objects.filter(
            verified=True, email=email)]

class EmailAddress(models.Model):

    user = models.ForeignKey(User)
    email = models.EmailField()
    verified = models.BooleanField(default=False)
    primary = models.BooleanField(default=False)

    objects = EmailAddressManager()

    def set_as_primary(self, conditional=False):
        old_primary = EmailAddress.objects.get_primary(self.user)
        if old_primary:
            if conditional:
                return False
            old_primary.primary = False
            old_primary.save()
        self.primary = True
        self.save()
        self.user.email = self.email
        self.user.save()
        return True

    def __unicode__(self):
        return u"%s (%s)" % (self.email, self.user)

    class Meta:
        verbose_name = _("e-mail address")
        verbose_name_plural = _("e-mail addresses")
        unique_together = (
            ("user", "email"),
        )


class EmailConfirmationManager(models.Manager):

    def confirm_email(self, confirmation_key):
        try:
            confirmation = self.get(confirmation_key=confirmation_key)
        except self.model.DoesNotExist:
            return None
        if not confirmation.key_expired():
            email_address = confirmation.email_address
            email_address.verified = True
            email_address.set_as_primary(conditional=True)
            email_address.save()
            email_confirmed.send(sender=self.model, email_address=email_address)
            return email_address

    def send_confirmation(self, email_address):
        salt = sha_constructor(str(random())).hexdigest()[:5]
        confirmation_key = sha_constructor(salt + email_address.email).hexdigest()
        current_site = Site.objects.get_current()
        # check for the url with the dotted view path
        try:
            path = reverse("emailconfirmation.views.confirm_email",
                args=[confirmation_key])
        except NoReverseMatch:
            # or get path with named urlconf instead
            path = reverse(
                "emailconfirmation_confirm_email", args=[confirmation_key])
        activate_url = u"http://%s%s" % (unicode(current_site.domain), path)
        context = {
            "user": email_address.user,
            "activate_url": activate_url,
            "current_site": current_site,
            "confirmation_key": confirmation_key,
        }
        subject = render_to_string(
            "emailconfirmation/email_confirmation_subject.txt", context)
        # remove superfluous line breaks
        subject = "".join(subject.splitlines())
        message = render_to_string(
            "emailconfirmation/email_confirmation_message.txt", context)
        send_mail(subject, message, settings.DEFAULT_FROM_EMAIL,
                  [email_address.email], priority="high")
        return self.create(
            email_address=email_address,
            sent=datetime.now(),
            confirmation_key=confirmation_key)

    def delete_expired_confirmations(self):
        for confirmation in self.all():
            if confirmation.key_expired():
                confirmation.delete()

class EmailConfirmation(models.Model):

    email_address = models.ForeignKey(EmailAddress)
    sent = models.DateTimeField()
    confirmation_key = models.CharField(max_length=40)

    objects = EmailConfirmationManager()

    def key_expired(self):
        expiration_date = self.sent + timedelta(
            days=settings.EMAIL_CONFIRMATION_DAYS)
        return expiration_date <= datetime.now()
    key_expired.boolean = True

    def __unicode__(self):
        return u"confirmation for %s" % self.email_address

    class Meta:
        verbose_name = _("e-mail confirmation")
        verbose_name_plural = _("e-mail confirmations")

########NEW FILE########
__FILENAME__ = signals
from django.dispatch import Signal


email_confirmed = Signal(providing_args=["email_address"])

########NEW FILE########
__FILENAME__ = utils
from django.conf import settings

def get_send_mail():
    """
    A function to return a send_mail function suitable for use in the app. It
    deals with incompatibilities between signatures.
    """
    # favour django-mailer but fall back to django.core.mail
    if "mailer" in settings.INSTALLED_APPS:
        from mailer import send_mail
    else:
        from django.core.mail import send_mail as _send_mail
        def send_mail(*args, **kwargs):
            del kwargs["priority"]
            return _send_mail(*args, **kwargs)
    return send_mail
########NEW FILE########
__FILENAME__ = views
from django.shortcuts import render_to_response
from django.template import RequestContext

from emailconfirmation.models import EmailConfirmation

def confirm_email(request, confirmation_key):
    confirmation_key = confirmation_key.lower()
    email_address = EmailConfirmation.objects.confirm_email(confirmation_key)
    return render_to_response("emailconfirmation/confirm_email.html", {
        "email_address": email_address,
    }, context_instance=RequestContext(request))
########NEW FILE########
