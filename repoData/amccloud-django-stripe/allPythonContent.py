__FILENAME__ = admin
from django.contrib import admin

from .models import Invoice

admin.site.register([Invoice])

########NEW FILE########
__FILENAME__ = backends
from django.utils.functional import curry
from django.contrib.auth import authenticate, login
from django.contrib.auth.models import User

from django_stripe.shortcuts import stripe
from django_stripe.settings import STRIPE_CUSTOMER_DESCRIPTION

from registration.backends.simple import SimpleBackend

from .forms import StripeSubscriptionForm
from .signals import user_registered

class StripeSubscriptionBackend(SimpleBackend):
    def get_form_class(self, request):
        return curry(StripeSubscriptionForm, initial={
            'plan': request.GET.get('plan'),
        })

    def get_customer_description(self, user):
        return STRIPE_CUSTOMER_DESCRIPTION(user)

    def register(self, request, **kwargs):
        username = kwargs['username']
        password = kwargs['password1']
        email = kwargs['email']
        token = kwargs['token']
        plan = kwargs['plan']

        User.objects.create_user(username, email, password)
        new_user = authenticate(username=username, password=password)
        login(request, new_user)

        customer = stripe.Customer.create(
            description=self.get_customer_description(new_user),
            card=token,
            plan=plan
        )

        user_registered.send(**{
            'sender': self.__class__,
            'user': new_user,
            'request': request,
            'customer': customer,
            'plan': plan,
        })

        return new_user

########NEW FILE########
__FILENAME__ = forms
from registration.forms import RegistrationForm

from django_stripe.forms import CustomerForm

class StripeSubscriptionForm(RegistrationForm, CustomerForm):
    pass

########NEW FILE########
__FILENAME__ = settings
from django.conf import settings

SUBSCRIPTION_PLAN_CHOICES = getattr(settings,
    'SUBSCRIPTION_PLAN_CHOICES'
)

SUBSCRIPTION_CUSTOMER_DESCRIPTION = getattr(settings,
    'SUBSCRIPTION_CUSTOMER_DESCRIPTION', lambda u: str(u)
)

########NEW FILE########
__FILENAME__ = signals
from django.dispatch import Signal

user_registered = Signal(providing_args=[
    'user', 'request', 'customer', 'plan',
])

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import *

urlpatterns = patterns('registration.views',
    url(r'register/$', 'register', {
        'backend': 'django_stripe.contrib.registration.backends.StripeSubscriptionBackend',
    }, name='registration_register'),
)

urlpatterns += patterns('',
    url(r'', include('registration.auth_urls')),
)

########NEW FILE########
__FILENAME__ = forms
import types, datetime

from django import forms
from django.contrib.localflavor.us.forms import USZipCodeField
from django.utils.translation import ugettext as _

from .settings import STRIPE_PLAN_CHOICES, STRIPE_CUSTOMER_DESCRIPTION
from .shortcuts import stripe

FORM_PREIX = 'stripe'

CURRENT_YEAR = datetime.date.today().year
MONTH_CHOICES = [(i, '%02d' % i) for i in xrange(1, 13)]
YEAR_CHOICES = [(i, i) for i in range(CURRENT_YEAR, CURRENT_YEAR + 10)]

def make_widget_anonymous(widget):
    def _anonymous_render(instance, name, value, attrs=None):
        return instance._orig_render('', value, attrs)

    widget._orig_render = widget.render
    widget.render = types.MethodType(_anonymous_render, widget)

    return widget

class CardForm(forms.Form):
    number = forms.CharField(label=_("Card number"))
    exp_month = forms.CharField(label=_("Expiration month"), widget=forms.Select(choices=MONTH_CHOICES))
    exp_year = forms.CharField(label=_("Expiration year"), widget=forms.Select(choices=YEAR_CHOICES))

    def get_cvc_field(self):
        return forms.CharField(label=_("Security code (CVV)"))

    def get_address_line1_field(self):
        return forms.CharField(label=_("Address"))

    def get_address_zip_field(self):
        return USZipCodeField(label=_("Zipcode"))

    def __init__(self, validate_cvc=True, validate_address=False, \
                    prefix=FORM_PREIX, *args, **kwargs):
        super(CardForm, self).__init__(prefix=prefix, *args, **kwargs)

        if validate_cvc:
            self.fields['cvc'] = self.get_cvc_field()

        if validate_address:
            self.fields['address_line1'] = self.get_address_line1_field()
            self.fields['address_zip'] = self.get_address_zip_field()


class AnonymousCardForm(CardForm):
    def __init__(self, *args, **kwargs):
        super(AnonymousCardForm, self).__init__(*args, **kwargs)

        for key in self.fields.keys():
            make_widget_anonymous(self.fields[key].widget)


class CardTokenForm(AnonymousCardForm):
    last4 = forms.CharField(min_length=4, max_length=4, required=False, widget=forms.HiddenInput())
    token = forms.CharField(required=False, widget=forms.HiddenInput())

    def __init__(self, prefix=FORM_PREIX, *args, **kwargs):
        super(CardTokenForm, self).__init__(prefix=prefix, *args, **kwargs)

    def clean(self):
        if not self.cleaned_data['last4'] or not self.cleaned_data['token']:
            raise forms.ValidationError(_("Could not validate credit card."))


class CustomerForm(CardTokenForm):
    plan = forms.CharField(widget=forms.Select(choices=STRIPE_PLAN_CHOICES))

    def get_customer_description(self, user):
        return STRIPE_CUSTOMER_DESCRIPTION(user)

    def save(self, user):
        return stripe.Customer.create(
            description=self.get_customer_description(user),
            card=self.cleaned_data['token'],
            plan=self.cleaned_data['plan']
        )

########NEW FILE########
__FILENAME__ = stripe_clear_test_customers
from django.core.management.base import BaseCommand

from ...shortcuts import stripe

class Command(BaseCommand):
    help = "Clear all test customers from your stripe account."

    def handle(self, *args, **options):
        verbosity = int(options.get('verbosity', 1))
        count, offset = 100, 0

        if verbosity > 0:
            print "Clearing all test customers from your stripe account."

        while True:
            deleted = 0

            if verbosity > 1:
                print "Fetching customers %s-%s." % (offset, offset + count)

            customers = stripe.Customer.all(count=count, offset=offset).data

            if not customers:
                break

            for customer in customers:
                if customer.livemode:
                    continue

                if verbosity > 1:
                    print "Deleting customer %s, '%s'." % \
                        (customer.id, customer.description)

                customer.delete()
                deleted += 1

            offset += count - deleted

        if verbosity > 0:
            print "Done."

########NEW FILE########
__FILENAME__ = stripe_get_webhook_url
from django.core.management.base import BaseCommand
from django.core.urlresolvers import reverse, NoReverseMatch
from django.contrib.sites.models import Site

class Command(BaseCommand):
    help = "A shortcut for copying your stripe wbehook url."

    def handle(self, *args, **options):
        current_site = Site.objects.get_current()

        try:
            print "http://%s%s" % (current_site, reverse('stripe:webhook'))
        except NoReverseMatch:
            print "Could not find url pattern for 'stripe:webhook'. " \
                    "Please include django_stripe.urls in your urlconf " \
                    "under the 'stripe' namespace."

########NEW FILE########
__FILENAME__ = managers
from django.db import models

class InvoiceManager(models.Manager):
    def sync(self, stripe_invoice):
        customer_id = stripe_invoice.customer
        stripe_id = stripe_invoice.get('id', None)

        defaults = {
            'customer_id': customer_id,
            'stripe_id': stripe_id,
            # 'lines': stripe_invoice.get('lines'),
            'subtotal': stripe_invoice.get('subtotal'),
            'total': stripe_invoice.get('total'),
            'attempted': stripe_invoice.get('attempted'),
            'closed': stripe_invoice.get('closed'),
            'paid': stripe_invoice.get('paid'),
            'created': stripe_invoice.get('created'),
        }

        filter_kwargs = {
            'stripe_id': None,
            'customer_id': customer_id,
            'defaults': defaults,
        }

        if stripe_id:
            filter_kwargs['stripe_id'] = stripe_id

        invoice, created = self.get_query_set().get_or_create(**filter_kwargs)

        if not created:
            invoice(**defaults)
            invoice.save()

        return invoice

########NEW FILE########
__FILENAME__ = models
from django.db import models

from .managers import InvoiceManager

class Invoice(models.Model):
    customer_id = models.CharField(max_length=32)
    stripe_id = models.CharField(max_length=32, blank=True, null=True)
    lines = models.TextField(blank=True, null=True)
    subtotal = models.IntegerField(blank=True, null=True)
    total = models.IntegerField(blank=True, null=True)
    attempted = models.NullBooleanField(blank=True, default=False)
    closed = models.NullBooleanField(blank=True, default=False)
    paid = models.NullBooleanField(blank=True, default=False)
    created = models.DateTimeField(blank=True, null=True)

    objects = InvoiceManager()

    @property
    def subtotal_usd(self):
        return u"$%.2f" % (self.subtotal / 100,)

    @property
    def total_usd(self):
        return u"$%.2f" % (self.total / 100,)

from .receivers import *

########NEW FILE########
__FILENAME__ = receivers
from django.dispatch import receiver

from .shortcuts import stripe
from .models import Invoice
from .signals import (upcoming_invoice_updated, invoice_updated, \
                        invoice_ready, StripeWebhook)

@receiver(upcoming_invoice_updated, \
    dispatch_uid='django_stripe.receivers.sync_upcoming_invoice')
def sync_upcoming_invoice(sender, customer, **kwargs):
    invoice = stripe.Invoice.upcoming(customer=customer.id)
    invoice_updated.send(sender=None, invoice=invoice, refresh=False)

@receiver(invoice_updated, \
    dispatch_uid='django_stripe.receivers.sync_invoice')
def sync_invoice(sender, invoice, refresh=True, **kwargs):
    if refresh:
        invoice.refresh()

    Invoice.objects.sync(invoice)

@receiver(invoice_ready, sender=StripeWebhook, \
    dispatch_uid='django_stripe.receivers._invoice_ready')
def _invoice_ready(sender, customer, **kwargs):
    upcoming_invoice_updated.send_robust(sender=sender, customer=customer)

########NEW FILE########
__FILENAME__ = settings
from django.conf import settings

STRIPE_SECRET_KEY = getattr(settings,
    'STRIPE_SECRET_KEY'
)

STRIPE_PUBLISHABLE_KEY = getattr(settings,
    'STRIPE_PUBLISHABLE_KEY'
)

STRIPE_WEBHOOK_SECRET = getattr(settings,
    'STRIPE_WEBHOOK_SECRET'
)

STRIPE_WEBHOOK_ENDPOINT = getattr(settings,
    'STRIPE_WEBHOOK_ENDPOINT', r'stripe/%s/webhook/' % STRIPE_WEBHOOK_SECRET
)

STRIPE_PLAN_CHOICES = getattr(settings,
    'STRIPE_PLAN_CHOICES', ()
)

STRIPE_CUSTOMER_DESCRIPTION = getattr(settings,
    'STRIPE_CUSTOMER_DESCRIPTION', lambda u: str(u)
)

########NEW FILE########
__FILENAME__ = shortcuts
import stripe

from .settings import STRIPE_SECRET_KEY

stripe.api_key = STRIPE_SECRET_KEY

########NEW FILE########
__FILENAME__ = signals
from django.dispatch import Signal

upcoming_invoice_updated = Signal(providing_args=['customer'])
invoice_updated = Signal(providing_args=['invoice'])

# Webhooks
recurring_payment_failed = Signal(providing_args=[
    'customer',
    'attempt',
    'invoice',
    'payment',
    'livemode',
])

invoice_ready = Signal(providing_args=[
    'customer',
    'invoice'
])

recurring_payment_succeeded = Signal(providing_args=[
    'customer',
    'invoice',
    'payment',
    'livemode',
])

subscription_trial_ending = Signal(providing_args=[
    'customer',
    'subscription',
])

subscription_final_payment_attempt_failed = Signal(providing_args=[
    'customer',
    'subscription',
])

ping = Signal()

class StripeWebhook(object):
    pass

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import patterns, url

from django_stripe.settings import STRIPE_WEBHOOK_ENDPOINT

urlpatterns = patterns('django_stripe.views',
    url(STRIPE_WEBHOOK_ENDPOINT, 'webhook_to_signal', name='webhook'),
)

########NEW FILE########
__FILENAME__ = views
from stripe import convert_to_stripe_object

from django.http import Http404, HttpResponse
from django.utils import simplejson as json
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import View, FormView

from .settings import STRIPE_SECRET_KEY
from .forms import CardTokenForm
from .signals import (recurring_payment_failed, invoice_ready, \
    recurring_payment_succeeded, subscription_trial_ending, \
    subscription_final_payment_attempt_failed, ping, StripeWebhook)

class BaseCardTokenFormView(FormView):
    template_name = 'django_stripe/card_form.html'
    form_class = CardTokenForm

    def get_last4(self):
        return None

    def get_form_kwargs(self):
        kwargs = super(BaseCardTokenFormView, self).get_form_kwargs()
        kwargs.update({
            'initial': {
                'last4': self.get_last4(),
            }
        })

        return kwargs

class WebhookSignalView(View):
    http_method_names = ['post']
    event_signals = {
        'recurring_payment_failed': recurring_payment_failed,
        'invoice_ready': invoice_ready,
        'recurring_payment_succeeded': recurring_payment_succeeded,
        'subscription_trial_ending': subscription_trial_ending,
        'subscription_final_payment_attempt_failed': subscription_final_payment_attempt_failed,
        'ping': ping,
    }

    def post(self, request, *args, **kwargs):
        if 'json' not in request.POST:
            raise Http404

        message = json.loads(request.POST.get('json'))
        event = message.get('event')
        del message['event']

        if event not in self.event_signals:
            raise Http404

        for key, value in message.iteritems():
            if isinstance(value, dict) and 'object' in value:
                message[key] = convert_to_stripe_object(value, STRIPE_SECRET_KEY)

        signal = self.event_signals.get(event)
        signal.send_robust(sender=StripeWebhook, **message)

        return HttpResponse()

webhook_to_signal = csrf_exempt(WebhookSignalView.as_view())

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
__FILENAME__ = admin
from django.contrib import admin

from .models import UserProfile

admin.site.register([UserProfile])

########NEW FILE########
__FILENAME__ = models
from datetime import datetime

from django.db import models
from django.contrib.auth.models import User

from django_stripe.settings import STRIPE_PLAN_CHOICES

class UserProfile(models.Model):
    user = models.ForeignKey(User, related_name='profile', unique=True)
    plan = models.CharField(max_length=32, choices=STRIPE_PLAN_CHOICES, blank=True, null=True)
    customer_id = models.CharField(max_length=32, blank=True, null=True)
    card_last4 = models.CharField(max_length=4, blank=True, null=True)
    payment_attempts = models.PositiveIntegerField(default=0, blank=True, null=True)
    last_payment_attempt = models.DateTimeField(blank=True, null=True)
    trial_end = models.DateTimeField(blank=True, null=True)

    @property
    def trialing(self):
        return datetime.now() >= self.trial_end

    @property
    def collaborator_count(self):
        return 4

    def get_price(self):
        if self.plan == 'pro':
            return 8.00

        return 0.00

    def __unicode__(self):
        return unicode(self.user)

from .receivers import *

########NEW FILE########
__FILENAME__ = receivers
from datetime import datetime

from django.dispatch import receiver
from django.db.models.signals import post_save
from django.contrib.auth.models import User

from django_stripe.shortcuts import stripe
from django_stripe.contrib.registration.backends import StripeSubscriptionBackend
from django_stripe.contrib.registration.signals import user_registered
from django_stripe.signals import (upcoming_invoice_updated, invoice_ready, \
    recurring_payment_failed, subscription_final_payment_attempt_failed, StripeWebhook)

from .models import UserProfile

@receiver(post_save, sender=User, \
    dispatch_uid='profiles.receivers.create_user_profile')
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        profile, new = UserProfile.objects.get_or_create(user=instance)

@receiver(user_registered, sender=StripeSubscriptionBackend, \
    dispatch_uid='profiles.receivers.link_stripe_customer')
def link_stripe_customer(sender, user, request, customer, plan=None, **kwargs):
    user_profile = user.get_profile()
    user_profile.customer_id = customer.id
    user_profile.card_last4 = customer.active_card.last_4
    user_profile.plan = plan

    try:
        user_profile.trial_end = datetime.utcfromtimestamp(customer.subscription.trial_end)
    except AttributeError:
        pass

    user_profile.save()

    upcoming_invoice_updated.send(sender=None, customer=customer)

@receiver(invoice_ready, sender=StripeWebhook, \
    dispatch_uid='profiles.receivers.invoice_user')
def invoice_user(sender, customer, invoice, **kwargs):
    try:
        user_profile = UserProfile.objects.get(customer_id=customer)
        amount = int(user_profile.collaborator_count * user_profile.get_price())

        if not user_profile.trialing and amount > 0:
            stripe.InvoiceItem.create( \
                customer=customer,
                amount=amount * 100,
                currency='usd',
                description="%s Collaborators" \
                                % user_profile.collaborator_count
            )

            upcoming_invoice_updated.send(sender=None, customer=customer)

    except UserProfile.DoesNotExist:
        pass

@receiver(recurring_payment_failed, sender=StripeWebhook, \
    dispatch_uid='profiles.receviers.update_payment_attempts')
def update_payment_attempts(sender, customer, attempt, payment, **kwargs):
    try:
        user_profile = UserProfile.objects.get(customer_id=customer)
        user_profile.payment_attempts = int(attempt)
        user_profile.last_payment_attempt = datetime.utcfromtimestamp(payment['time'])
        user_profile.save()
    except UserProfile.DoesNotExist:
        pass

@receiver(subscription_final_payment_attempt_failed, sender=StripeWebhook, \
    dispatch_uid='profiles.receviers.lock_account')
def lock_account(sender, customer, subscription, **kwargs):
    try:
        user = User.objects.get(profile__customer_id=customer)
        user.is_active = False
        user.save()
    except User.DoesNotExist:
        pass

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import patterns, url

urlpatterns = patterns('profiles.views',
    url(r'^account/billing/$', 'account_billing_form', name='account_billing'),
)

########NEW FILE########
__FILENAME__ = views
from django.contrib.auth.decorators import login_required

from django_stripe.views import BaseCardTokenFormView

class AccountBillingFormView(BaseCardTokenFormView):
    def get_last4(self):
        user_profile = self.request.user.get_profile()

        return user_profile.card_last4

    def form_valid(self, form):
        customer = form.save(self.request.user)

        user_profile = self.request.user.get_profile()
        user_profile.customer_id = customer.id
        user_profile.card_last4 = customer.active_card.last4
        user_profile.save()

        return super(AccountBillingFormView, self).form_valid(form)

account_billing_form = login_required(AccountBillingFormView.as_view())

########NEW FILE########
__FILENAME__ = settings
# Django settings for django-stripe example project.
DEBUG = True

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.admin',
    'registration',
    'django_stripe',
    'profiles',
)

# django_stripe
if DEBUG:
    # Test keys
    # Your private and public keys can be found here:
    # https://manage.stripe.com/account
    STRIPE_SECRET_KEY = 'vtUQeOtUnYr7PGCLQ96Ul4zqpDUO4sOE'
    STRIPE_PUBLISHABLE_KEY = 'pk_NjMf2QUPtR28Wg0xmyWtepIzUziVr'
else:
    # Live keys
    STRIPE_SECRET_KEY = 'vtUQeOtUnYr7PGCLQ96Ul4zqpDUO4sOE'
    STRIPE_PUBLISHABLE_KEY = 'pk_NjMf2QUPtR28Wg0xmyWtepIzUziVr'

# IMPORTANT: This needs to be a random alpha-numerical string for security.
# Make this unique, and don't share it with anybody.
STRIPE_WEBHOOK_SECRET = '3j9d-modm_7'

STRIPE_PLAN_CHOICES = (
    ('free', 'Free'),
    ('pro', 'Pro'),
)

STRIPE_CUSTOMER_DESCRIPTION = lambda u: u.email

# profiles
AUTH_PROFILE_MODULE = 'profiles.UserProfile'

# --- other django settings ---

import os
from django.core.urlresolvers import reverse_lazy

PROJECT_DIR = os.path.dirname(__file__)

TEMPLATE_DEBUG = True

ADMINS = (
    # ('Andrew McCloud', 'andrew@amccloud.com'),
)

MANAGERS = ADMINS

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3', # Add 'postgresql_psycopg2', 'mysql', 'sqlite3' or 'oracle'.
        'NAME': os.path.join(PROJECT_DIR, 'test.db'), # Or path to database file if using sqlite3.
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
TIME_ZONE = 'UTC'

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
SECRET_KEY = '^9!yt63y2ibcx)959+=llugh=$08$%*5kcdjwkkzc&9r5ps_9m'

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

ROOT_URLCONF = 'example.urls'

TEMPLATE_DIRS = (
    # Put strings here, like "/home/html/django_templates" or "C:/www/django/templates".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
    os.path.join(PROJECT_DIR, 'templates'),
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
            '()': 'django.utils.log.CallbackFilter',
            'callback': lambda r: not DEBUG
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

LOGIN_REDIRECT_URL = reverse_lazy('profiles:account_billing')

try:
    from local_settings import *
except:
    pass

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import patterns, include, url
from django.contrib import admin

admin.autodiscover()

urlpatterns = patterns('',
    url(r'^admin/', include(admin.site.urls)),
    url(r'^account/', include('django_stripe.contrib.registration.urls')),
    url(r'^account/', include('django_stripe.urls', namespace='stripe')),
    url(r'', include('profiles.urls', namespace='profiles')),
)
########NEW FILE########
