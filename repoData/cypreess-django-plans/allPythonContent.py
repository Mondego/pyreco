__FILENAME__ = conftest
import sys
import os
from decimal import Decimal
from django.conf import settings


sys.path[:0] = [os.path.join(os.getcwd(), 'demo')]


def pytest_configure(config):
    settings.configure(
        DATABASE_ENGINE='sqlite3',
        DATABASES={
            'default': {
                'NAME': ':memory:',
                'ENGINE': 'django.db.backends.sqlite3',
                'TEST_NAME': ':memory:',
            },
        },
        DATABASE_NAME=':memory:',
        TEST_DATABASE_NAME=':memory:',
        INSTALLED_APPS=[
            'django.contrib.auth',
            'django.contrib.contenttypes',
            'django.contrib.admin',
            'django.contrib.sessions',
            'django.contrib.sites',
            'ordered_model',
            'example.foo',
            'plans',
        ],
        ROOT_URLCONF='example.urls',
        DEBUG=False,
        SITE_ID=1,
        TEMPLATE_DEBUG=True,
        USE_TZ=True,
        ALLOWED_HOSTS=['*'],
        ISSUER_DATA={
            "issuer_name": "My Company Ltd",
            "issuer_street": "48th Suny street",
            "issuer_zipcode": "111-456",
            "issuer_city": "Django City",
            "issuer_country": "PL",
            "issuer_tax_number": "PL123456789",
        },
        TAX=Decimal(23.0),
        TAXATION_POLICY='plans.locale.eu.taxation.EUTaxationPolicy',
        TAX_COUNTRY='PL',
        CURRENCY='PLN',
        PLAN_VALIDATORS={
            'MAX_FOO_COUNT': 'example.foo.validators.max_foos_validator',
        },
        EMAIL_BACKEND='django.core.mail.backends.console.EmailBackend',
    )

########NEW FILE########
__FILENAME__ = forms
from django.forms import ModelForm, HiddenInput

from .models import Foo
from .validators import max_foos_validator


class FooForm(ModelForm):
    class Meta:
        model = Foo
        widgets = {
            'user': HiddenInput,
        }

    def clean(self):
        cleaned_data = super(FooForm, self).clean()
        max_foos_validator(cleaned_data['user'], add=1)
        return cleaned_data
########NEW FILE########
__FILENAME__ = models
from __future__ import unicode_literals
from django.db import models

# Create your models here.
from django.utils.encoding import python_2_unicode_compatible


@python_2_unicode_compatible
class Foo(models.Model):
    user = models.ForeignKey('auth.User')
    name = models.CharField(max_length=100, default="A new foo")

    def __str__(self):
        return self.name
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
from django.conf.urls import url, patterns

from django.contrib.auth.decorators import login_required

from example.foo.views import FooListView, FooCreateView, FooDeleteView


urlpatterns = patterns(
    '',
    url(r'^list/$', login_required(FooListView.as_view()), name='foo_list'),
    url(r'^add/$', login_required(FooCreateView.as_view()), name='foo_add'),
    url(r'^del/(?P<pk>\d+)/$', login_required(FooDeleteView.as_view()), name='foo_del'),
)


########NEW FILE########
__FILENAME__ = validators
from .models import Foo
from plans.validators import ModelCountValidator


class MaxFoosValidator(ModelCountValidator):
    code = 'MAX_FOO_COUNT'
    model = Foo

    def get_queryset(self, user):
        return super(MaxFoosValidator, self).get_queryset(user).filter(user=user)

max_foos_validator = MaxFoosValidator()
########NEW FILE########
__FILENAME__ = views
# Create your views here.
from django.contrib import messages
from django.core.urlresolvers import reverse
from django.shortcuts import redirect
from django.views.generic import ListView, CreateView, DeleteView
from .forms import FooForm
from .models import Foo
from plans.quota import get_user_quota


class FooListView(ListView):
    model = Foo

    def get_queryset(self):
        return super(FooListView, self).get_queryset().filter(user=self.request.user)


class FooCreateView(CreateView):
    model = Foo
    form_class = FooForm

    def get_initial(self):
        initial = super(FooCreateView, self).get_initial()
        initial['user'] = self.request.user
        return initial

    def get_success_url(self):
        return reverse('foo_list')

    def get_queryset(self):
        return super(FooCreateView, self).get_queryset().filter(user=self.request.user)


class FooDeleteView(DeleteView):
    model = Foo

    def get_queryset(self):
        return super(FooDeleteView, self).get_queryset().filter(user=self.request.user)

    def get_success_url(self):
        return reverse('foo_list')

    def delete(self, request, *args, **kwargs):
        if not get_user_quota(request.user).get('CAN_DELETE_FOO', True):
            messages.error(request, 'Sorry, your plan does not allow to deletes Foo. Please upgrade!')
            return redirect('foo_del', pk=self.get_object().pk)
        else:
            return super(FooDeleteView, self).delete(request, *args, **kwargs)


########NEW FILE########
__FILENAME__ = settings
# Django settings for example project.
import os
from decimal import Decimal
from django.conf import global_settings

EMAIL_FROM = "Test <test@server.com>"

SITE_ROOT = os.path.dirname(os.path.realpath(__file__))

DEBUG = True
TEMPLATE_DEBUG = DEBUG

ADMINS = (
    # ('Your Name', 'your_email@example.com'),
)

ALLOWED_HOSTS = ['*']

MANAGERS = ADMINS

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        # Add 'postgresql_psycopg2', 'postgresql', 'mysql', 'sqlite3' or 'oracle'.
        'NAME': 'plans_example.sqlite',  # Or path to database file if using sqlite3.
        'USER': '',  # Not used with sqlite3.
        'PASSWORD': '',  # Not used with sqlite3.
        'HOST': '',  # Set to empty string for localhost. Not used with sqlite3.
        'PORT': '',  # Set to empty string for default. Not used with sqlite3.
    }
}

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
    }
}

TIME_ZONE = 'America/Chicago'
USE_TZ = True
LANGUAGE_CODE = 'en-us'
SITE_ID = 1
USE_I18N = True
USE_L10N = True
MEDIA_ROOT = ''
MEDIA_URL = ''
STATIC_ROOT = ''
STATIC_URL = '/static/'
ADMIN_MEDIA_PREFIX = '/static/admin/'
STATICFILES_DIRS = (
    os.path.join(SITE_ROOT, 'static'),
)

STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
    #    'django.contrib.staticfiles.finders.DefaultStorageFinder',
)

SECRET_KEY = 'l#^#iad$8$4=dlh74$!xs=3g4jb(&j+y6*ozy&8k1-&d+vruzy'

TEMPLATE_LOADERS = (
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
    #     'django.template.loaders.eggs.Loader',
)

MIDDLEWARE_CLASSES = (
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
)

ROOT_URLCONF = 'example.urls'
WSGI_APPLICATION = 'example.wsgi.application'

TEMPLATE_DIRS = (
    os.path.join(SITE_ROOT, 'templates'),
)

INSTALLED_APPS = (
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.sites',

    'ordered_model',
    'bootstrap3',

    'plans',
    'example.foo',

)

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'mail_admins': {
            'level': 'ERROR',
            'class': 'django.utils.log.AdminEmailHandler'
        },

    },
    'loggers': {
        'django.request': {
            'handlers': ['mail_admins'],
            'level': 'ERROR',
            'propagate': True,
        },

    }
}


# This is required for django-plans

TEMPLATE_CONTEXT_PROCESSORS = global_settings.TEMPLATE_CONTEXT_PROCESSORS + (
    'django.core.context_processors.request',
    'plans.context_processors.account_status'
)


LANGUAGES = (
    ('en', 'English'),
)

ISSUER_DATA = {
    "issuer_name": "My Company Ltd",
    "issuer_street": "48th Suny street",
    "issuer_zipcode": "111-456",
    "issuer_city": "Django City",
    "issuer_country": "PL",
    "issuer_tax_number": "PL123456789",
}

TAX = Decimal('23.0')
TAXATION_POLICY = 'plans.taxation.eu.EUTaxationPolicy'
TAX_COUNTRY = 'PL'

PLAN_VALIDATORS = {
    'MAX_FOO_COUNT': 'example.foo.validators.max_foos_validator',
}

CURRENCY = 'EUR'

EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

LOGIN_REDIRECT_URL = '/foo/list/'
########NEW FILE########
__FILENAME__ = urls
from django.conf.urls import url, patterns, include
from django.contrib import admin
from django.views.generic.base import TemplateView

admin.autodiscover()

urlpatterns = patterns(
    '',
    url(r'^$', TemplateView.as_view(template_name='home.html'), name='home'),
    url(r'^admin/', include(admin.site.urls)),
    url(r'^plan/', include('plans.urls')),
    url(r'^accounts/login/$', 'django.contrib.auth.views.login', name="login"),
    url(r'^accounts/logout/$', 'django.contrib.auth.views.logout', {'next_page': '/'}, name="logout"),
    url(r'^foo/', include('example.foo.urls')),
)

########NEW FILE########
__FILENAME__ = wsgi
"""
WSGI config for xmpl project.

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

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "xmpl.settings")

# This application object is used by any WSGI server configured to use this
# file. This includes Django's development server, if the WSGI_APPLICATION
# setting points here.
from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()

# Apply WSGI middleware here.
# from helloworld.wsgi import HelloWorldApplication
# application = HelloWorldApplication(application)

########NEW FILE########
__FILENAME__ = fabfile
from fabric.api import *

@task
def freeze_fixtures():
    local('python manage.py dumpdata auth.User plans.BillingInfo plans.Invoice plans.Order plans.Plan plans.Pricing plans.PlanPricing plans.Quota plans.PlanQuota plans.UserPlan > example/foo/fixtures/initial_data.json')

########NEW FILE########
__FILENAME__ = manage
#!/usr/bin/env python2
import os
import sys

if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "example.settings")

    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)

########NEW FILE########
__FILENAME__ = conf
# -*- coding: utf-8 -*-
#
# django-plans documentation build configuration file, created by
# sphinx-quickstart on Fri Mar  9 14:47:25 2012.
#
# This file is execfile()d with the current directory set to its containing dir.
#
# Note that not all possible configuration values are present in this
# autogenerated file.
#
# All configuration values have a default; values that are commented out
# serve to show the default.

from django.conf import settings
settings.configure()


# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#sys.path.insert(0, os.path.abspath('.'))

# -- General configuration -----------------------------------------------------

# If your documentation needs a minimal Sphinx version, state it here.
#needs_sphinx = '1.0'

# Add any Sphinx extension module names here, as strings. They can be extensions
# coming with Sphinx (named 'sphinx.ext.*') or your custom ones.
extensions = ['sphinx.ext.autodoc', 'sphinx.ext.viewcode']

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# The suffix of source filenames.
source_suffix = '.rst'

# The encoding of source files.
#source_encoding = 'utf-8-sig'

# The master toctree document.
master_doc = 'index'

# General information about the project.
project = u'django-plans'
copyright = u'2012, Krzysztof Dorosz'

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
# The short X.Y version.
version = '0.6-dev'
# The full version, including alpha/beta/rc tags.
release = '0.6-dev'

# The language for content autogenerated by Sphinx. Refer to documentation
# for a list of supported languages.
#language = None

# There are two options for replacing |today|: either, you set today to some
# non-false value, then it is used:
#today = ''
# Else, today_fmt is used as the format for a strftime call.
#today_fmt = '%B %d, %Y'

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
exclude_patterns = []

# The reST default role (used for this markup: `text`) to use for all documents.
#default_role = None

# If true, '()' will be appended to :func: etc. cross-reference text.
#add_function_parentheses = True

# If true, the current module name will be prepended to all description
# unit titles (such as .. function::).
#add_module_names = True

# If true, sectionauthor and moduleauthor directives will be shown in the
# output. They are ignored by default.
#show_authors = False

# The name of the Pygments (syntax highlighting) style to use.
pygments_style = 'sphinx'

# A list of ignored prefixes for module index sorting.
#modindex_common_prefix = []


# -- Options for HTML output ---------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
html_theme = 'default'

# Theme options are theme-specific and customize the look and feel of a theme
# further.  For a list of options available for each theme, see the
# documentation.
#html_theme_options = {}

# Add any paths that contain custom themes here, relative to this directory.
#html_theme_path = []

# The name for this set of Sphinx documents.  If None, it defaults to
# "<project> v<release> documentation".
#html_title = None

# A shorter title for the navigation bar.  Default is the same as html_title.
#html_short_title = None

# The name of an image file (relative to this directory) to place at the top
# of the sidebar.
#html_logo = None

# The name of an image file (within the static path) to use as favicon of the
# docs.  This file should be a Windows icon file (.ico) being 16x16 or 32x32
# pixels large.
#html_favicon = None

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ['_static']

# If not '', a 'Last updated on:' timestamp is inserted at every page bottom,
# using the given strftime format.
#html_last_updated_fmt = '%b %d, %Y'

# If true, SmartyPants will be used to convert quotes and dashes to
# typographically correct entities.
#html_use_smartypants = True

# Custom sidebar templates, maps document names to template names.
#html_sidebars = {}

# Additional templates that should be rendered to pages, maps page names to
# template names.
#html_additional_pages = {}

# If false, no module index is generated.
#html_domain_indices = True

# If false, no index is generated.
#html_use_index = True

# If true, the index is split into individual pages for each letter.
#html_split_index = False

# If true, links to the reST sources are added to the pages.
#html_show_sourcelink = True

# If true, "Created using Sphinx" is shown in the HTML footer. Default is True.
#html_show_sphinx = True

# If true, "(C) Copyright ..." is shown in the HTML footer. Default is True.
#html_show_copyright = True

# If true, an OpenSearch description file will be output, and all pages will
# contain a <link> tag referring to it.  The value of this option must be the
# base URL from which the finished HTML is served.
#html_use_opensearch = ''

# This is the file name suffix for HTML files (e.g. ".xhtml").
#html_file_suffix = None

# Output file base name for HTML help builder.
htmlhelp_basename = 'django-plansdoc'


# -- Options for LaTeX output --------------------------------------------------

latex_elements = {
    # The paper size ('letterpaper' or 'a4paper').
    #'papersize': 'letterpaper',

    # The font size ('10pt', '11pt' or '12pt').
    #'pointsize': '10pt',

    # Additional stuff for the LaTeX preamble.
    #'preamble': '',
}

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title, author, documentclass [howto/manual]).
latex_documents = [
    ('index', 'django-plans.tex', u'django-plans Documentation',
     u'Krzysztof Dorosz', 'manual'),
]

# The name of an image file (relative to this directory) to place at the top of
# the title page.
#latex_logo = None

# For "manual" documents, if this is true, then toplevel headings are parts,
# not chapters.
#latex_use_parts = False

# If true, show page references after internal links.
#latex_show_pagerefs = False

# If true, show URL addresses after external links.
#latex_show_urls = False

# Documents to append as an appendix to all manuals.
#latex_appendices = []

# If false, no module index is generated.
#latex_domain_indices = True


# -- Options for manual page output --------------------------------------------

# One entry per manual page. List of tuples
# (source start file, name, description, authors, manual section).
man_pages = [
    ('index', 'django-plans', u'django-plans Documentation',
     [u'Krzysztof Dorosz'], 1)
]

# If true, show URL addresses after external links.
#man_show_urls = False


# -- Options for Texinfo output ------------------------------------------------

# Grouping the document tree into Texinfo files. List of tuples
# (source start file, target name, title, author,
#  dir menu entry, description, category)
texinfo_documents = [
    ('index', 'django-plans', u'django-plans Documentation',
     u'Krzysztof Dorosz', 'django-plans', 'One line description of project.',
     'Miscellaneous'),
]

# Documents to append as an appendix to all manuals.
#texinfo_appendices = []

# If false, no module index is generated.
#texinfo_domain_indices = True

# How to display URL addresses: 'footnote', 'no', or 'inline'.
#texinfo_show_urls = 'footnote'


########NEW FILE########
__FILENAME__ = fabfile
from fabric.api import *

@task
def push_lang():
    with lcd('demo/example'):
        local('django-admin.py makemessages -l en')

    with lcd('./plans'):
        local('django-admin.py makemessages -l en')

    local('tx push -s')

@task
def pull_lang():
    local('tx pull')
########NEW FILE########
__FILENAME__ = admin
from copy import deepcopy

from django.contrib import admin
from django.core import urlresolvers
from ordered_model.admin import OrderedModelAdmin
from django.utils.translation import ugettext_lazy as _

from .models import UserPlan, Plan, PlanQuota, Quota, PlanPricing, Pricing, Order, BillingInfo
from plans.models import Invoice


class UserLinkMixin(object):
    def user_link(self, obj):
        change_url = urlresolvers.reverse('admin:auth_user_change', args=(obj.user.id,))
        return '<a href="%s">%s</a>' % (change_url, obj.user.username)

    user_link.short_description = 'User'
    user_link.allow_tags = True


class PlanQuotaInline(admin.TabularInline):
    model = PlanQuota


class PlanPricingInline(admin.TabularInline):
    model = PlanPricing


class QuotaAdmin(OrderedModelAdmin):
    list_display = ('codename', 'name', 'description', 'unit', 'is_boolean', 'move_up_down_links', )


def copy_plan(modeladmin, request, queryset):
    """
    Admin command for duplicating plans preserving quotas and pricings.
    """
    for plan in queryset:
        plan_copy = deepcopy(plan)
        plan_copy.id = None
        plan_copy.available = False
        plan_copy.default = False
        plan_copy.created = None
        plan_copy.save(force_insert=True)

        for pricing in plan.planpricing_set.all():
            pricing.id = None
            pricing.plan = plan_copy
            pricing.save(force_insert=True)

        for quota in plan.planquota_set.all():
            quota.id = None
            quota.plan = plan_copy
            quota.save(force_insert=True)


copy_plan.short_description = _('Make a plan copy')


class PlanAdmin(OrderedModelAdmin):
    search_fields = ('name', 'customized__username', 'customized__email', )
    list_filter = ('available', 'visible')
    list_display = ('name', 'description', 'customized', 'default', 'available', 'created', 'move_up_down_links')
    inlines = (PlanPricingInline, PlanQuotaInline)
    list_select_related = True
    raw_id_fields = ('customized',)
    actions = [copy_plan, ]

    def queryset(self, request):
        return super(PlanAdmin, self).queryset(request).select_related('customized')


class BillingInfoAdmin(UserLinkMixin, admin.ModelAdmin):
    search_fields = ('user__username', 'user__email', 'tax_number', 'name')
    list_display = ('user', 'tax_number', 'name', 'street', 'zipcode', 'city', 'country')
    list_select_related = True
    readonly_fields = ('user_link',)
    exclude = ('user',)


def make_order_completed(modeladmin, request, queryset):
    for order in queryset:
        order.complete_order()


make_order_completed.short_description = _('Make selected orders completed')


def make_order_invoice(modeladmin, request, queryset):
    for order in queryset:
        if Invoice.objects.filter(type=Invoice.INVOICE_TYPES['INVOICE'], order=order).count() == 0:
            Invoice.create(order, Invoice.INVOICE_TYPES['INVOICE'])


make_order_invoice.short_description = _('Make invoices for orders')


class InvoiceInline(admin.TabularInline):
    model = Invoice
    extra = 0


class OrderAdmin(admin.ModelAdmin):
    list_filter = ('status', 'created', 'completed', 'plan__name', 'pricing')
    raw_id_fields = ('user',)
    search_fields = ('id', 'user__username', 'user__email')
    list_display = (
        'id', 'name', 'created', 'user', 'status', 'completed', 'tax', 'amount', 'currency', 'plan', 'pricing')
    actions = [make_order_completed, make_order_invoice]
    inlines = (InvoiceInline, )

    def queryset(self, request):
        return super(OrderAdmin, self).queryset(request).select_related('plan', 'pricing', 'user')


class InvoiceAdmin(admin.ModelAdmin):
    search_fields = ('full_number', 'buyer_tax_number', 'user__username', 'user__email')
    list_filter = ('type', 'issued')
    list_display = (
        'full_number', 'issued', 'total_net', 'currency', 'user', 'tax', 'buyer_name', 'buyer_city', 'buyer_tax_number')
    list_select_related = True
    raw_id_fields = ('user', 'order')


class UserPlanAdmin(UserLinkMixin, admin.ModelAdmin):
    list_filter = ('active', 'expire', 'plan__name', 'plan__available', 'plan__visible',)
    search_fields = ('user__username', 'user__email', 'plan__name',)
    list_display = ('user', 'plan', 'expire', 'active')
    list_select_related = True
    readonly_fields = ['user_link', ]
    fields = ('user_link', 'plan', 'expire', 'active' )
    raw_id_fields = ['plan', ]


admin.site.register(Quota, QuotaAdmin)
admin.site.register(Plan, PlanAdmin)
admin.site.register(UserPlan, UserPlanAdmin)
admin.site.register(Pricing)
admin.site.register(Order, OrderAdmin)
admin.site.register(BillingInfo, BillingInfoAdmin)
admin.site.register(Invoice, InvoiceAdmin)



########NEW FILE########
__FILENAME__ = conf

# TODO use django-conf
from django.conf import settings

TAX =  getattr(settings, 'PLANS_TAX', None)
TAXATION_POLICY =  getattr(settings,
                           'PLANS_TAXATION_POLICY',
                           'plans.taxation.TAXATION_POLICY')

########NEW FILE########
__FILENAME__ = context_processors
from django.core.urlresolvers import reverse

from plans.models import UserPlan


def account_status(request):
    """
    Set following ``RequestContext`` variables:

     * ``ACCOUNT_EXPIRED = boolean``, account was expired state,
     * ``ACCOUNT_NOT_ACTIVE = boolean``, set when account is not expired, but it is over quotas so it is
                                        not active
     * ``EXPIRE_IN_DAYS = integer``, number of days to account expiration,
     * ``EXTEND_URL = string``, URL to account extend page.
     * ``ACTIVATE_URL = string``, URL to account activation needed if  account is not active

    """

    if request.user.is_authenticated():
        try:
            return {
                'ACCOUNT_EXPIRED': request.user.userplan.is_expired(),
                'ACCOUNT_NOT_ACTIVE': (
                not request.user.userplan.is_active() and not request.user.userplan.is_expired()),
                'EXPIRE_IN_DAYS': request.user.userplan.days_left(),
                'EXTEND_URL': reverse('current_plan'),
                'ACTIVATE_URL': reverse('account_activation'),
            }
        except UserPlan.DoesNotExist:
            pass
    return {}

########NEW FILE########
__FILENAME__ = contrib
import logging
from django.conf import settings
from django.core import mail
from django.core.exceptions import ImproperlyConfigured
from django.template import loader
from django.utils import translation
from django.db.models.loading import cache
from plans.signals import user_language

email_logger = logging.getLogger('emails')

def send_template_email(recipients, title_template, body_template, context, language):
    """Sends e-mail using templating system"""

    send_emails = getattr(settings, 'SEND_PLANS_EMAILS', True)
    if not send_emails:
        return

    site_name = getattr(settings, 'SITE_NAME', 'Please define settings.SITE_NAME')
    domain = getattr(settings, 'SITE_URL', None)

    if domain is None:
        Site = cache.get_model('sites', 'Site')
        current_site = Site.objects.get_current()
        site_name = current_site.name
        domain = current_site.domain

    context.update({'site_name' : site_name, 'site_domain': domain})

    if language is not None:
        translation.activate(language)

    mail_title_template = loader.get_template(title_template)
    mail_body_template = loader.get_template(body_template)
    title = mail_title_template.render(context)
    body = mail_body_template.render(context)

    try:
        email_from = getattr(settings, 'DEFAULT_FROM_EMAIL')
    except AttributeError:
        raise ImproperlyConfigured('DEFAULT_FROM_EMAIL setting needed for sending e-mails')

    mail.send_mail(title, body, email_from, recipients)

    if language is not None:
        translation.deactivate()

    email_logger.info(u"Email (%s) sent to %s\nTitle: %s\n%s\n\n" % (language, recipients, title, body))


def get_user_language(user):
    """ Simple helper that will fire django signal in order to get User language possibly given by other part of application.
    :param user:
    :return: string or None
    """
    return_value = {}
    user_language.send(sender=user, user=user, return_value=return_value)
    return return_value.get('language')

########NEW FILE########
__FILENAME__ = enum
import six


class Enumeration(object):
    """
    A small helper class for more readable enumerations,
    and compatible with Django's choice convention.
    You may just pass the instance of this class as the choices
    argument of model/form fields.

    Example:
            MY_ENUM = Enumeration([
                    (100, 'MY_NAME', 'My verbose name'),
                    (200, 'MY_AGE', 'My verbose age'),
            ])
            assert MY_ENUM.MY_AGE == 200
            assert MY_ENUM[1] == (200, 'My verbose age')
    """

    def __init__(self, enum_list):
        self.enum_list_full = enum_list
        self.enum_list = [(item[0], item[2]) for item in enum_list]
        self.enum_dict = {}
        self.enum_code = {}
        self.enum_display = {}
        for item in enum_list:
            self.enum_dict[item[1]] = item[0]
            self.enum_display[item[0]] = item[2]
            self.enum_code[item[0]] = item[1]

    def __contains__(self, v):
        return (v in self.enum_list)

    def __len__(self):
        return len(self.enum_list)

    def __getitem__(self, v):
        if isinstance(v, six.string_types):
            return self.enum_dict[v]
        elif isinstance(v, int):
            return self.enum_list[v]

    def __getattr__(self, name):
        try:
            return self.enum_dict[name]
        except KeyError:
            raise AttributeError

    def __iter__(self):
        return self.enum_list.__iter__()

    def __repr__(self):
        return 'Enum(%s)' % self.enum_list_full.__repr__()

    def get_display_name(self, v):
        return self.enum_display[v]

    def get_display_code(self, v):
        return self.enum_code[v]
########NEW FILE########
__FILENAME__ = forms
from django import forms
from django.core.exceptions import ValidationError
from django.forms.widgets import HiddenInput
from django.utils.translation import ugettext

from .models import PlanPricing, BillingInfo
from plans.models import Order


class OrderForm(forms.Form):
    plan_pricing = forms.ModelChoiceField(queryset=PlanPricing.objects.all(), widget=HiddenInput, required=True)


class CreateOrderForm(forms.ModelForm):
    """
    This form is intentionally empty as all values for Order object creation need to be computed inside view

    Therefore, when implementing for example a rabat coupons, you can add some fields here
     and create "recalculate" button.
    """

    class Meta:
        model = Order
        fields = tuple()


class BillingInfoForm(forms.ModelForm):
    class Meta:
        model = BillingInfo
        exclude = ('user',)

    def clean(self):
        cleaned_data = super(BillingInfoForm, self).clean()

        try:
            cleaned_data['tax_number'] = BillingInfo.clean_tax_number(cleaned_data['tax_number'],
                                                                      cleaned_data.get('country', None))
        except ValidationError as e:
            self._errors['tax_number'] = e.messages

        return cleaned_data


class BillingInfoWithoutShippingForm(BillingInfoForm):
    class Meta:
        model = BillingInfo
        exclude = ('user', 'shipping_name', 'shipping_street', 'shipping_zipcode', 'shipping_city')


class FakePaymentsForm(forms.Form):
    status = forms.ChoiceField(choices=Order.STATUS, required=True, label=ugettext('Change order status to'))
########NEW FILE########
__FILENAME__ = importer
def import_name(name):
    components = name.split('.')
    mod = __import__('.'.join(components[0:-1]), globals(), locals(), [components[-1]] )
    return getattr(mod, components[-1])

########NEW FILE########
__FILENAME__ = listeners
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch.dispatcher import receiver
from plans.models import Order, Invoice, UserPlan, Plan
from plans.signals import order_completed, activate_user_plan

@receiver(post_save, sender=Order)
def create_proforma_invoice(sender, instance, created, **kwargs):
    """
    For every Order if there are defined billing_data creates invoice proforma,
    which is an order confirmation document
    """
    if created:
        Invoice.create(instance, Invoice.INVOICE_TYPES['PROFORMA'])


@receiver(order_completed)
def create_invoice(sender, **kwargs):
    Invoice.create(sender, Invoice.INVOICE_TYPES['INVOICE'])


@receiver(post_save, sender=Invoice)
def send_invoice_by_email(sender, instance, created, **kwargs):
    if created:
        instance.send_invoice_by_email()


@receiver(post_save, sender=User)
def set_default_user_plan(sender, instance, created, **kwargs):
    """
    Creates default plan for the new user but also extending an account for default grace period.
    """

    if created:
        default_plan = Plan.get_default_plan()
        if default_plan is not None:
            UserPlan.objects.create(user=instance, plan=default_plan, active=False, expire=None)


# Hook to django-registration to initialize plan automatically after user has confirm account

@receiver(activate_user_plan)
def initialize_plan_generic(sender, user, **kwargs):
    try:
        user.userplan.initialize()
    except UserPlan.DoesNotExist:
        return


try:
    from registration.signals import user_activated
    @receiver(user_activated)
    def initialize_plan_django_registration(sender, user, request, **kwargs):
        try:
             user.userplan.initialize()
        except UserPlan.DoesNotExist:
            return


except ImportError:
    pass


# Hook to django-getpaid if it is installed
try:
    from getpaid.signals import user_data_query
    @receiver(user_data_query)
    def set_user_email_for_getpaid(sender, order, user_data, **kwargs):
        user_data['email'] = order.user.email
except ImportError:
    pass

########NEW FILE########
__FILENAME__ = mixins
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.views.generic import View


class LoginRequired(View):
    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        return super(LoginRequired, self).dispatch(*args, **kwargs)


class UserObjectsOnlyMixin(object):
    def get_queryset(self):
        return super(UserObjectsOnlyMixin, self).get_queryset().filter(user=self.request.user)
########NEW FILE########
__FILENAME__ = models
from __future__ import unicode_literals

from decimal import Decimal
import re
from datetime import date, timedelta, datetime
import logging

from django.contrib.sites.models import Site
from django.db.models import Max
from django.utils import translation
from django.utils.encoding import python_2_unicode_compatible
from django.utils.timezone import now
from django_countries.fields import CountryField
from django.core.urlresolvers import reverse
from django.template.base import Template
from django.utils.translation import ugettext_lazy as _, pgettext_lazy
from django.db import models
from ordered_model.models import OrderedModel
import vatnumber
from django.template import Context
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured, ValidationError

from plans.contrib import send_template_email, get_user_language
from plans.enum import Enumeration
from plans.signals import order_completed, account_activated, account_expired, account_change_plan, account_deactivated
from .validators import plan_validation
from plans.taxation.eu import EUTaxationPolicy


accounts_logger = logging.getLogger('accounts')

# Create your models here.

@python_2_unicode_compatible
class Plan(OrderedModel):
    """
    Single plan defined in the system. A plan can customized (referred to user) which means
    that only this user can purchase this plan and have it selected.

    Plan also can be visible and available. Plan is displayed on the list of currently available plans
    for user if it is visible. User cannot change plan to a plan that is not visible. Available means
    that user can buy a plan. If plan is not visible but still available it means that user which
    is using this plan already will be able to extend this plan again. If plan is not visible and not
    available, he will be forced then to change plan next time he extends an account.
    """
    name = models.CharField(_('name'), max_length=100)
    description = models.TextField(_('description'), blank=True)
    default = models.BooleanField(default=False, db_index=True)
    available = models.BooleanField(_('available'), default=False, db_index=True,
                                    help_text=_('Is still available for purchase'))
    visible = models.BooleanField(_('visible'), default=True, db_index=True, help_text=_('Is visible in current offer'))
    created = models.DateTimeField(_('created'), db_index=True)
    customized = models.ForeignKey('auth.User', null=True, blank=True, verbose_name=_('customized'))
    quotas = models.ManyToManyField('Quota', through='PlanQuota', verbose_name=_('quotas'))
    url = models.CharField(max_length=200, blank=True, help_text=_(
        'Optional link to page with more information (for clickable pricing table headers)'))

    class Meta:
        ordering = ('order',)
        verbose_name = _("Plan")
        verbose_name_plural = _("Plans")

    def save(self, *args, **kwargs):
        if not self.created:
            self.created = now()

        super(Plan, self).save(*args, **kwargs)

    @classmethod
    def get_default_plan(cls):
        try:
            return cls.objects.filter(default=True)[0]
        except IndexError:
            return None

    def __str__(self):
        return self.name

    def get_quota_dict(self):
        quota_dic = {}
        for plan_quota in PlanQuota.objects.filter(plan=self).select_related('quota'):
            quota_dic[plan_quota.quota.codename] = plan_quota.value
        return quota_dic


class BillingInfo(models.Model):
    """
    Stores customer billing data needed to issue an invoice
    """
    user = models.OneToOneField('auth.User', verbose_name=_('user'))
    tax_number = models.CharField(_('VAT ID'), max_length=200, blank=True, db_index=True)
    name = models.CharField(_('name'), max_length=200, db_index=True)
    street = models.CharField(_('street'), max_length=200)
    zipcode = models.CharField(_('zip code'), max_length=200)
    city = models.CharField(_('city'), max_length=200)
    country = CountryField(_("country"))

    shipping_name = models.CharField(_('name (shipping)'), max_length=200, blank=True, help_text=_('optional'))
    shipping_street = models.CharField(_('street (shipping)'), max_length=200, blank=True, help_text=_('optional'))
    shipping_zipcode = models.CharField(_('zip code (shipping)'), max_length=200, blank=True, help_text=_('optional'))
    shipping_city = models.CharField(_('city (shipping)'), max_length=200, blank=True, help_text=_('optional'))

    class Meta:
        verbose_name = _("Billing info")
        verbose_name_plural = _("Billing infos")

    @staticmethod
    def clean_tax_number(tax_number, country):
        tax_number = re.sub(r'[^A-Z0-9]', '', tax_number.upper())
        if tax_number and country:

            if country in vatnumber.countries():
                number = tax_number
                if tax_number.startswith(country):
                    number = tax_number[len(country):]

                if not vatnumber.check_vat(country + number):
                    #           This is a proper solution to bind ValidationError to a Field but it is not
                    #           working due to django bug :(
                    #                    errors = defaultdict(list)
                    #                    errors['tax_number'].append(_('VAT ID is not correct'))
                    #                    raise ValidationError(errors)
                    raise ValidationError(_('VAT ID is not correct'))

            return tax_number
        else:
            return ''


# FIXME: How to make validation in Model clean and attach it to a field? Seems that it is not working right now
#    def clean(self):
#        super(BillingInfo, self).clean()
#        self.tax_number = BillingInfo.clean_tax_number(self.tax_number, self.country)

@python_2_unicode_compatible
class UserPlan(models.Model):
    """
    Currently selected plan for user account.
    """
    user = models.OneToOneField('auth.User', verbose_name=_('user'))
    plan = models.ForeignKey('Plan', verbose_name=_('plan'))
    expire = models.DateField(_('expire'), default=None, blank=True, null=True, db_index=True)
    active = models.BooleanField(_('active'), default=True, db_index=True)

    class Meta:
        verbose_name = _("User plan")
        verbose_name_plural = _("Users plans")

    def __str__(self):
        return "%s [%s]" % (self.user, self.plan)

    def is_active(self):
        return self.active

    def is_expired(self):
        if self.expire is None:
            return False
        else:
            return self.expire < date.today()

    def days_left(self):
        if self.expire is None:
            return None
        else:
            return (self.expire - date.today()).days

    def clean_activation(self):
        errors = plan_validation(self.user)
        if not errors['required_to_activate']:
            plan_validation(self.user, on_activation=True)
            self.activate()
        else:
            self.deactivate()
        return errors

    def activate(self):
        if not self.active:
            self.active = True
            self.save()
            account_activated.send(sender=self, user=self.user)

    def deactivate(self):
        if self.active:
            self.active = False
            self.save()
            account_deactivated.send(sender=self, user=self.user)

    def initialize(self):
        """
        Set up user plan for first use
        """
        if not self.is_active():
            if self.expire is None:
                self.expire = now() + timedelta(
                    days=getattr(settings, 'PLAN_DEFAULT_GRACE_PERIOD', 30))
            self.activate()  # this will call self.save()

    def extend_account(self, plan, pricing):
        """
        Manages extending account after plan or pricing order
        :param plan:
        :param pricing: if pricing is None then account will be only upgraded
        :return:
        """

        status = False  # flag; if extending account was successful?
        if pricing is None:
            # Process a plan change request (downgrade or upgrade)
            # No account activation or extending at this point
            self.plan = plan
            self.save()
            account_change_plan.send(sender=self, user=self.user)
            mail_context = Context({'user': self.user, 'userplan': self, 'plan': plan})
            send_template_email([self.user.email], 'mail/change_plan_title.txt', 'mail/change_plan_body.txt',
                                mail_context, get_user_language(self.user))
            accounts_logger.info(
                "Account '%s' [id=%d] plan changed to '%s' [id=%d]" % (self.user, self.user.pk, plan, plan.pk))
            status = True
        else:
            # Processing standard account extending procedure
            if self.plan == plan:
                status = True
                if self.expire is None:
                    pass
                elif self.expire > date.today():
                    self.expire += timedelta(days=pricing.period)
                else:
                    self.expire = date.today() + timedelta(days=pricing.period)

            else:
                # This should not ever happen (as this case should be managed by plan change request)
                # but just in case we consider a case when user has a different plan
                if self.expire is None:
                    status = True
                elif self.expire > date.today():
                    status = False
                    accounts_logger.warning("Account '%s' [id=%d] plan NOT changed to '%s' [id=%d]" % (
                        self.user, self.user.pk, plan, plan.pk))
                else:
                    status = True
                    account_change_plan.send(sender=self, user=self.user)
                    self.plan = plan
                    self.expire = date.today() + timedelta(days=pricing.period)

            if status:
                self.save()
                accounts_logger.info("Account '%s' [id=%d] has been extended by %d days using plan '%s' [id=%d]" % (
                    self.user, self.user.pk, pricing.period, plan, plan.pk))
                mail_context = Context({'user': self.user, 'userplan': self, 'plan': plan, 'pricing': pricing})
                send_template_email([self.user.email], 'mail/extend_account_title.txt', 'mail/extend_account_body.txt',
                                    mail_context, get_user_language(self.user))

        if status:
            self.clean_activation()

        return status

    def expire_account(self):
        """manages account expiration"""

        self.deactivate()

        accounts_logger.info("Account '%s' [id=%d] has expired" % (self.user, self.user.pk))

        mail_context = Context({'user': self.user, 'userplan': self})
        send_template_email([self.user.email], 'mail/expired_account_title.txt', 'mail/expired_account_body.txt',
                            mail_context, get_user_language(self.user))

        account_expired.send(sender=self, user=self.user)

    def remind_expire_soon(self):
        """reminds about soon account expiration"""

        mail_context = Context({'user': self.user, 'userplan': self, 'days': self.days_left()})
        send_template_email([self.user.email], 'mail/remind_expire_title.txt', 'mail/remind_expire_body.txt',
                            mail_context, get_user_language(self.user))


@python_2_unicode_compatible
class Pricing(models.Model):
    """
    Type of plan period that could be purchased (e.g. 10 days, month, year, etc)
    """
    name = models.CharField(_('name'), max_length=100)
    period = models.PositiveIntegerField(_('period'), default=30, null=True, blank=True, db_index=True)
    url = models.CharField(max_length=200, blank=True, help_text=_(
        'Optional link to page with more information (for clickable pricing table headers)'))

    class Meta:
        ordering = ('period',)
        verbose_name = _("Pricing")
        verbose_name_plural = _("Pricings")

    def __str__(self):
        return "%s (%d " % (self.name, self.period) + "%s)" % _("days")


@python_2_unicode_compatible
class Quota(OrderedModel):
    """
    Single countable or boolean property of system (limitation).
    """
    codename = models.CharField(_('codename'), max_length=50, unique=True, db_index=True)
    name = models.CharField(_('name'), max_length=100)
    unit = models.CharField(_('unit'), max_length=100, blank=True)
    description = models.TextField(_('description'), blank=True)
    is_boolean = models.BooleanField(_('is boolean'), default=False)
    url = models.CharField(max_length=200, blank=True, help_text=_(
        'Optional link to page with more information (for clickable pricing table headers)'))

    class Meta:
        ordering = ('order',)
        verbose_name = _("Quota")
        verbose_name_plural = _("Quotas")

    def __str__(self):
        return "%s" % (self.codename, )


class PlanPricingManager(models.Manager):
    def get_query_set(self):
        return super(PlanPricingManager, self).get_query_set().select_related('plan', 'pricing')


@python_2_unicode_compatible
class PlanPricing(models.Model):
    plan = models.ForeignKey('Plan')
    pricing = models.ForeignKey('Pricing')
    price = models.DecimalField(max_digits=7, decimal_places=2, db_index=True)

    objects = PlanPricingManager()

    class Meta:
        ordering = ('pricing__period', )
        verbose_name = _("Plan pricing")
        verbose_name_plural = _("Plans pricings")

    def __str__(self):
        return "%s %s" % (self.plan.name, self.pricing)


class PlanQuotaManager(models.Manager):
    def get_query_set(self):
        return super(PlanQuotaManager, self).get_query_set().select_related('plan', 'quota')


class PlanQuota(models.Model):
    plan = models.ForeignKey('Plan')
    quota = models.ForeignKey('Quota')
    value = models.IntegerField(default=1, null=True, blank=True)

    objects = PlanQuotaManager()

    class Meta:
        verbose_name = _("Plan quota")
        verbose_name_plural = _("Plans quotas")


@python_2_unicode_compatible
class Order(models.Model):
    """
    Order in this app supports only one item per order. This item is defined by
    plan and pricing attributes. If both are defined the order represents buying
    an account extension.

    If only plan is provided (with pricing set to None) this means that user purchased
    a plan upgrade.
    """
    STATUS = Enumeration([
        (1, 'NEW', pgettext_lazy('Order status', 'new')),
        (2, 'COMPLETED', pgettext_lazy('Order status', 'completed')),
        (3, 'NOT_VALID', pgettext_lazy('Order status', 'not valid')),
        (4, 'CANCELED', pgettext_lazy('Order status', 'canceled')),
        (5, 'RETURNED', pgettext_lazy('Order status', 'returned')),

    ])

    user = models.ForeignKey('auth.User', verbose_name=_('user'))
    flat_name = models.CharField(max_length=200, blank=True, null=True)
    plan = models.ForeignKey('Plan', verbose_name=_('plan'), related_name="plan_order")
    pricing = models.ForeignKey('Pricing', blank=True, null=True, verbose_name=_(
        'pricing'))  # if pricing is None the order is upgrade plan, not buy new pricing
    created = models.DateTimeField(_('created'), db_index=True)
    completed = models.DateTimeField(_('completed'), null=True, blank=True, db_index=True)
    amount = models.DecimalField(_('amount'), max_digits=7, decimal_places=2, db_index=True)
    tax = models.DecimalField(_('tax'), max_digits=4, decimal_places=2, db_index=True, null=True,
                              blank=True)  # Tax=None is when tax is not applicable
    currency = models.CharField(_('currency'), max_length=3, default='EUR')
    status = models.IntegerField(_('status'), choices=STATUS, default=STATUS.NEW)

    def save(self, force_insert=False, force_update=False, using=None, update_fields=None):
        if self.created is None:
            self.created = now()
        return super(Order, self).save(force_insert, force_update, using)

    def __str__(self):
        return _("Order #%(id)d") % {'id': self.id}

    @property
    def name(self):
        """
        Support for two kind of Order names:
        * (preferred) dynamically generated from Plan and Pricing (if flatname is not provided) (translatable)
        * (legacy) just return flat name, which is any text (not translatable)

        Flat names are only introduced for legacy system support, when you need to migrate old orders into
        django-plans and you cannot match Plan&Pricings convention.
        """
        if self.flat_name:
            return self.flat_name
        else:
            return "%s %s %s " % (
                _('Plan'), self.plan.name, "(upgrade)" if self.pricing is None else '- %s' % self.pricing)


    def is_ready_for_payment(self):
        return self.status == self.STATUS.NEW and (now() - self.created).days < getattr(
            settings, 'ORDER_EXPIRATION', 14)

    def complete_order(self):
        if self.completed is None:
            status = self.user.userplan.extend_account(self.plan, self.pricing)
            self.completed = now()
            if status:
                self.status = Order.STATUS.COMPLETED
            else:
                self.status = Order.STATUS.NOT_VALID
            self.save()
            order_completed.send(self)
            return True
        else:
            return False


    def get_invoices_proforma(self):
        return Invoice.proforma.filter(order=self)

    def get_invoices(self):
        return Invoice.invoices.filter(order=self)

    def get_all_invoices(self):
        return self.invoice_set.order_by('issued', 'issued_duplicate', 'pk')

    def tax_total(self):
        if self.tax is None:
            return Decimal('0.00')
        else:
            return self.total() - self.amount

    def total(self):
        if self.tax is not None:
            return (self.amount * (self.tax + 100) / 100).quantize(Decimal('1.00'))
        else:
            return self.amount

    def get_absolute_url(self):
        return reverse('order', kwargs={'pk': self.pk})

    class Meta:
        ordering = ('-created', )
        verbose_name = _("Order")
        verbose_name_plural = _("Orders")


class InvoiceManager(models.Manager):
    def get_query_set(self):
        return super(InvoiceManager, self).get_query_set().filter(type=Invoice.INVOICE_TYPES['INVOICE'])


class InvoiceProformaManager(models.Manager):
    def get_query_set(self):
        return super(InvoiceProformaManager, self).get_query_set().filter(type=Invoice.INVOICE_TYPES['PROFORMA'])


class InvoiceDuplicateManager(models.Manager):
    def get_query_set(self):
        return super(InvoiceDuplicateManager, self).get_query_set().filter(type=Invoice.INVOICE_TYPES['DUPLICATE'])


@python_2_unicode_compatible
class Invoice(models.Model):
    """
    Single invoice document.
    """

    INVOICE_TYPES = Enumeration([
        (1, 'INVOICE', _('Invoice')),
        (2, 'DUPLICATE', _('Invoice Duplicate')),
        (3, 'PROFORMA', pgettext_lazy('proforma', 'Order confirmation')),

    ])

    objects = models.Manager()
    invoices = InvoiceManager()
    proforma = InvoiceProformaManager()
    duplicates = InvoiceDuplicateManager()

    class NUMBERING:
        """Used as a choices for settings.INVOICE_COUNTER_RESET"""

        DAILY = 1
        MONTHLY = 2
        ANNUALLY = 3

    user = models.ForeignKey('auth.User')
    order = models.ForeignKey('Order')
    number = models.IntegerField(db_index=True)
    full_number = models.CharField(max_length=200)
    type = models.IntegerField(choices=INVOICE_TYPES, default=INVOICE_TYPES.INVOICE, db_index=True)
    issued = models.DateField(db_index=True)
    issued_duplicate = models.DateField(db_index=True, null=True, blank=True)
    selling_date = models.DateField(db_index=True, null=True, blank=True)
    payment_date = models.DateField(db_index=True)
    unit_price_net = models.DecimalField(max_digits=7, decimal_places=2)
    quantity = models.IntegerField(default=1)
    total_net = models.DecimalField(max_digits=7, decimal_places=2)
    total = models.DecimalField(max_digits=7, decimal_places=2)
    tax_total = models.DecimalField(max_digits=7, decimal_places=2)
    tax = models.DecimalField(max_digits=4, decimal_places=2, db_index=True, null=True,
                              blank=True)  # Tax=None is whet tax is not applicable
    rebate = models.DecimalField(max_digits=4, decimal_places=2, default=Decimal(0))
    currency = models.CharField(max_length=3, default='EUR')
    item_description = models.CharField(max_length=200)
    buyer_name = models.CharField(max_length=200, verbose_name=_("Name"))
    buyer_street = models.CharField(max_length=200, verbose_name=_("Street"))
    buyer_zipcode = models.CharField(max_length=200, verbose_name=_("Zip code"))
    buyer_city = models.CharField(max_length=200, verbose_name=_("City"))
    buyer_country = CountryField(verbose_name=_("Country"), default='PL')
    buyer_tax_number = models.CharField(max_length=200, blank=True, verbose_name=_("TAX/VAT number"))
    shipping_name = models.CharField(max_length=200, verbose_name=_("Name"))
    shipping_street = models.CharField(max_length=200, verbose_name=_("Street"))
    shipping_zipcode = models.CharField(max_length=200, verbose_name=_("Zip code"))
    shipping_city = models.CharField(max_length=200, verbose_name=_("City"))
    shipping_country = CountryField(verbose_name=_("Country"), default='PL')
    require_shipment = models.BooleanField(default=False, db_index=True)
    issuer_name = models.CharField(max_length=200, verbose_name=_("Name"))
    issuer_street = models.CharField(max_length=200, verbose_name=_("Street"))
    issuer_zipcode = models.CharField(max_length=200, verbose_name=_("Zip code"))
    issuer_city = models.CharField(max_length=200, verbose_name=_("City"))
    issuer_country = CountryField(verbose_name=_("Country"), default='PL')
    issuer_tax_number = models.CharField(max_length=200, blank=True, verbose_name=_("TAX/VAT number"))

    class Meta:
        verbose_name = _("Invoice")
        verbose_name_plural = _("Invoices")

    def __str__(self):
        return self.full_number

    def get_absolute_url(self):
        return reverse('invoice_preview_html', kwargs={'pk': self.pk})

    def clean(self):
        if self.number is None:
            invoice_counter_reset = getattr(settings, 'INVOICE_COUNTER_RESET', Invoice.NUMBERING.MONTHLY)

            if invoice_counter_reset == Invoice.NUMBERING.DAILY:
                last_number = Invoice.objects.filter(issued=self.issued, type=self.type).aggregate(Max('number'))[
                                  'number__max'] or 0
            elif invoice_counter_reset == Invoice.NUMBERING.MONTHLY:
                last_number = Invoice.objects.filter(issued__year=self.issued.year, issued__month=self.issued.month,
                                                     type=self.type).aggregate(Max('number'))['number__max'] or 0
            elif invoice_counter_reset == Invoice.NUMBERING.ANNUALLY:
                last_number = \
                    Invoice.objects.filter(issued__year=self.issued.year, type=self.type).aggregate(Max('number'))[
                        'number__max'] or 0
            else:
                raise ImproperlyConfigured(
                    "INVOICE_COUNTER_RESET can be set only to these values: daily, monthly, yearly.")
            self.number = last_number + 1

        if self.full_number == "":
            self.full_number = self.get_full_number()
        super(Invoice, self).clean()

    #    def validate_unique(self, exclude=None):
    #        super(Invoice, self).validate_unique(exclude)
    #        if self.type == Invoice.INVOICE_TYPES.INVOICE:
    #            if Invoice.objects.filter(order=self.order).count():
    #                raise ValidationError("Duplicate invoice for order")
    #        if self.type in (Invoice.INVOICE_TYPES.INVOICE, Invoice.INVOICE_TYPES.PROFORMA):
    #            pass


    def get_full_number(self):
        """
        Generates on the fly invoice full number from template provided by ``settings.INVOICE_NUMBER_FORMAT``.
        ``Invoice`` object is provided as ``invoice`` variable to the template, therefore all object fields
        can be used to generate full number format.

        .. warning::

            This is only used to prepopulate ``full_number`` field on saving new invoice.
            To get invoice full number always use ``full_number`` field.

        :return: string (generated full number)
        """
        format = getattr(settings, "INVOICE_NUMBER_FORMAT",
                         "{{ invoice.number }}/{% ifequal invoice.type invoice.INVOICE_TYPES.PROFORMA %}PF{% else %}FV{% endifequal %}/{{ invoice.issued|date:'m/Y' }}")
        return Template(format).render(Context({'invoice': self}))


    def set_issuer_invoice_data(self):
        """
        Fills models object with issuer data copied from ``settings.ISSUER_DATA``

        :raise: ImproperlyConfigured
        """
        try:
            issuer = getattr(settings, 'ISSUER_DATA')
        except:
            raise ImproperlyConfigured("Please set ISSUER_DATA in order to make an invoice.")
        self.issuer_name = issuer['issuer_name']
        self.issuer_street = issuer['issuer_street']
        self.issuer_zipcode = issuer['issuer_zipcode']
        self.issuer_city = issuer['issuer_city']
        self.issuer_country = issuer['issuer_country']
        self.issuer_tax_number = issuer['issuer_tax_number']

    def set_buyer_invoice_data(self, billing_info):
        """
        Fill buyer invoice billing and shipping data by copy them from provided user's ``BillingInfo`` object.

        :param billing_info: BillingInfo object
        :type billing_info: BillingInfo
        """
        self.buyer_name = billing_info.name
        self.buyer_street = billing_info.street
        self.buyer_zipcode = billing_info.zipcode
        self.buyer_city = billing_info.city
        self.buyer_country = billing_info.country
        self.buyer_tax_number = billing_info.tax_number

        self.shipping_name = billing_info.shipping_name or billing_info.name
        self.shipping_street = billing_info.shipping_street or billing_info.street
        self.shipping_zipcode = billing_info.shipping_zipcode or billing_info.zipcode
        self.shipping_city = billing_info.shipping_city or billing_info.city
        #TODO: Should allow shipping to other country? Not think so
        self.shipping_country = billing_info.country

    def copy_from_order(self, order):
        """
        Filling orders details likes totals, taxes, etc and linking provided ``Order`` object with an invoice

        :param order: Order object
        :type order: Order
        """
        self.order = order
        self.user = order.user
        self.unit_price_net = order.amount
        self.total_net = order.amount
        self.total = order.total()
        self.tax_total = order.total() - order.amount
        self.tax = order.tax
        self.currency = order.currency
        self.item_description = "%s - %s" % (Site.objects.get_current().name, order.name)

    @classmethod
    def create(cls, order, invoice_type):
        language_code = get_user_language(order.user)

        if language_code is not None:
            translation.activate(language_code)

        try:
            billing_info = BillingInfo.objects.get(user=order.user)
        except BillingInfo.DoesNotExist:
            return

        day = date.today()
        pday = order.completed
        if invoice_type == Invoice.INVOICE_TYPES['PROFORMA']:
            pday = day + timedelta(days=14)

        invoice = cls(issued=day, selling_date=order.completed,
                      payment_date=pday)  # FIXME: 14 - this should set accordingly to ORDER_TIMEOUT in days
        invoice.type = invoice_type
        invoice.copy_from_order(order)
        invoice.set_issuer_invoice_data()
        invoice.set_buyer_invoice_data(billing_info)
        invoice.clean()
        invoice.save()
        if language_code is not None:
            translation.deactivate()

    def send_invoice_by_email(self):
        language_code = get_user_language(self.user)

        if language_code is not None:
            translation.activate(language_code)
        mail_context = Context({'user': self.user,
                                'invoice_type': self.get_type_display(),
                                'invoice_number': self.get_full_number(),
                                'order': self.order.id,
                                'url': self.get_absolute_url(),
        })
        if language_code is not None:
            translation.deactivate()
        send_template_email([self.user.email], 'mail/invoice_created_title.txt', 'mail/invoice_created_body.txt',
                            mail_context, language_code)

    def is_UE_customer(self):
        return EUTaxationPolicy.is_in_EU(self.buyer_country.code)

#noinspection PyUnresolvedReferences
import plans.listeners



########NEW FILE########
__FILENAME__ = plan_change
# coding=utf-8
from decimal import Decimal

class PlanChangePolicy(object):

    def _calculate_day_cost(self, plan, period):
        """
        Finds most fitted plan pricing for a given period, and calculate day cost
        """

        plan_pricings = plan.planpricing_set.order_by('-pricing__period').select_related('pricing')
        selected_pricing = None
        for plan_pricing in plan_pricings:
            selected_pricing = plan_pricing
            if plan_pricing.pricing.period <= period:
                break

        if selected_pricing:
            return (selected_pricing.price / selected_pricing.pricing.period).quantize(Decimal('1.00'))

        raise ValueError('Plan %s has no pricings.' % plan)

    def _calculate_final_price(self, period, day_cost_diff):
        if day_cost_diff is None:
            return None
        else:
            return period * day_cost_diff

    def get_change_price(self, plan_old, plan_new, period):
        """
        Calculates total price of plan change. Returns None if no payment is required.
        """
        if period is None or period < 1:
            return None

        plan_old_day_cost = self._calculate_day_cost(plan_old, period)
        plan_new_day_cost = self._calculate_day_cost(plan_new, period)

        if plan_new_day_cost <= plan_old_day_cost:
            return self._calculate_final_price(period, None)
        else:
            return self._calculate_final_price(period, plan_new_day_cost - plan_old_day_cost)



class StandardPlanChangePolicy(PlanChangePolicy):
    """
    This plan switch policy follows the rules:
        * user can downgrade a plan for free if the plan is cheaper or have exact the same price (additional constant charge can be applied)
        * user need to pay extra amount depending of plans price difference (additional constant charge can be applied)

    Change percent rate while upgrading is defined in ``StandardPlanChangePolicy.UPGRADE_PERCENT_RATE``

    Additional constant charges are:
        * ``StandardPlanChangePolicy.UPGRADE_CHARGE``
        * ``StandardPlanChangePolicy.FREE_UPGRADE``
        * ``StandardPlanChangePolicy.DOWNGRADE_CHARGE``

    .. note:: Example

        User has PlanA which costs monthly (30 days) 20 €. His account will expire in 23 days. He wants to change
        to PlanB which costs monthly (30 days) 50€. Calculations::

            PlanA costs per day 20 €/ 30 days = 0.67 €
            PlanB costs per day 50 €/ 30 days = 1.67 €
            Difference per day between PlanA and PlanB is 1.00 €
            Upgrade percent rate is 10%
            Constant upgrade charge is 0 €
            Switch cost is:
                       23 *            1.00 € *                  10% +                     0 € = 25.30 €
                days_left * cost_diff_per_day * upgrade_percent_rate + constant_upgrade_charge
    """

    UPGRADE_PERCENT_RATE = Decimal('10.0')
    UPGRADE_CHARGE = Decimal('0.0')
    DOWNGRADE_CHARGE = None
    FREE_UPGRADE = Decimal('0.0')

    def _calculate_final_price(self, period, day_cost_diff):
        if day_cost_diff is None:
            return self.DOWNGRADE_CHARGE
        cost = (period * day_cost_diff * (self.UPGRADE_PERCENT_RATE/100 + 1) + self.UPGRADE_CHARGE).quantize(Decimal('1.00'))
        if cost is None or cost < self.FREE_UPGRADE:
            return None
        else:
            return cost

########NEW FILE########
__FILENAME__ = quota
def get_user_quota(user):
    """
    Tiny helper for getting quota dict for user (left mostly for backward compatibility)
    """
    return user.userplan.plan.get_quota_dict()


########NEW FILE########
__FILENAME__ = signals
from django.dispatch import Signal

order_started = Signal()
order_started.__doc__ = """
Sent after order was started (awaiting payment)
"""

order_completed = Signal()
order_completed.__doc__ = """
Sent after order was completed (payment accepted, account extended)
"""


user_language = Signal(providing_args=['user', 'language'])
user_language.__doc__ = """Sent to receive information about language for user account"""



account_expired = Signal(providing_args=['user'])
account_expired.__doc__ = """
Sent on account expiration. This signal is send regardless ``account_deactivated`` it only means that account has expired due to plan expire date limit.
"""

account_deactivated = Signal(providing_args=['user'])
account_deactivated.__doc__ = """
Sent on account deactivation, account is not operational (it could be not expired, but does not meet quota limits).
"""

account_activated = Signal(providing_args=['user'])
account_activated.__doc__ = """
Sent on account activation, account is now fully operational.
"""
account_change_plan = Signal(providing_args=['user'])
account_change_plan.__doc__ = """
Sent on account when plan was changed after order completion
"""

activate_user_plan = Signal(providing_args=['user'])
activate_user_plan.__doc__ = """
This signal should be called when user has succesfully registered (e.g. he activated account via e-mail activation). If you are using django-registration there is no need to call this signal.
"""

########NEW FILE########
__FILENAME__ = tasks
import datetime
import logging
from celery.schedules import crontab
from celery.task.base import periodic_task
from django.conf import settings
from django.contrib.auth.models import User

logger = logging.getLogger('plans.tasks')

@periodic_task(run_every=crontab(hour=0, minute=5))
def expire_account():

    logger.info('Started')

    for user in User.objects.select_related('userplan').filter(userplan__active=True,         userplan__expire__lt=datetime.date.today()).exclude(userplan__expire=None):
        user.userplan.expire_account()

    notifications_days_before = getattr(settings, 'PLAN_EXPIRATION_REMIND', [])

    if notifications_days_before:
        days = map(lambda x: datetime.date.today() + datetime.timedelta(days=x), notifications_days_before)
        for user in User.objects.select_related('userplan').filter(userplan__active=True, userplan__expire__in=days):
            user.userplan.remind_expire_soon()

########NEW FILE########
__FILENAME__ = eu
from django.core.exceptions import ImproperlyConfigured
from suds import WebFault
from suds.transport import TransportError
import vatnumber

from plans.taxation import TaxationPolicy

class EUTaxationPolicy(TaxationPolicy):
    """
    This taxation policy should be correct for all EU countries. It uses following rules:
        * if issuer country is not in EU - assert error,
        * return **default tax** in cases:
            * if issuer country and customer country are the same,
            * if issuer country and customer country are **not** not the same, but customer is private person from EU,
            * if issuer country and customer country are **not** not the same, customer is company, but his tax ID is **not** valid according VIES system.
        * return tax not applicable (``None``) in cases:
            * if issuer country and customer country are **not** not the same, customer is company from EU and his tax id is valid according VIES system.
            * if issuer country and customer country are **not** not the same and customer is private person **not** from EU,
            * if issuer country and customer country are **not** not the same and customer is company **not** from EU.


    Please note, that term "private person" refers in system to user that did not provide tax ID and
    ``company`` refers to user that provides it.

    """
    EU_COUNTRIES = {
        'AT', # Austria
        'BE', # Belgium
        'BG', # Bulgaria
        'CY', # Cyprus
        'CZ', # Czech Republic
        'DK', # Denmark
        'EE', # Estonia
        'FI', # Finland
        'FR', # France
        'DE', # Germany
        'GR', # Greece
        'HU', # Hungary
        'IE', # Ireland
        'IT', # Italy
        'LV', # Latvia
        'LT', # Lithuania
        'LU', # Luxembourg
        'MT', # Malta
        'NL', # Netherlands
        'PL', # Poland
        'PT', # Portugal
        'RO', # Romania
        'SK', # Slovakia
        'SI', # Slovenia
        'ES', # Spain
        'SE', # Sweden
        'GB', # United Kingdom (Great Britain)
    }

    @classmethod
    def is_in_EU(cls, country_code):
        return country_code.upper() in cls.EU_COUNTRIES


    @classmethod
    def get_tax_rate(cls, tax_id, country_code):
        issuer_country = cls.get_issuer_country_code()
        if not cls.is_in_EU(issuer_country):
            raise ImproperlyConfigured("EUTaxationPolicy requires that issuer country is in EU")

        if not tax_id and not country_code:
            # No vat id, no country
            return cls.get_default_tax()

        elif tax_id and not country_code:
            # Customer is not a company, we know his country

           if cls.is_in_EU(country_code):
               # Customer (private person) is from a EU
               # He must pay full VAT of our country
               return cls.get_default_tax()
           else:
               # Customer (private person) not from EU
               # charge back
               return None

        else:
            # Customer is company, we now country and vat id

            if country_code.upper() == issuer_country.upper():
               # Company is from the same country as issuer
               # Normal tax
               return cls.get_default_tax()
            if cls.is_in_EU(country_code):
                # Company is from other EU country
                try:
                    if tax_id and vatnumber.check_vies(tax_id):
                    # Company is registered in VIES
                    # Charge back
                        return None
                    else:
                        return cls.get_default_tax()
                except (WebFault, TransportError):
                    # If we could not connect to VIES
                    return cls.get_default_tax()
            else:
                # Company is not from EU
                # Charge back
                return None


########NEW FILE########
__FILENAME__ = ru
# from django.conf import settings
from plans.taxation import TaxationPolicy


class RussianTaxationPolicy(TaxationPolicy):
    """
    FIXME: description needed

    """

#   This could be inherited unless there is a reason to be custom
#    def get_default_tax(self):
#        return getattr(settings, 'TAX', None)
#
#    def get_issuer_country_code(self):
#        return getattr(settings, 'TAX_COUNTRY', None)

    def get_tax_rate(self, tax_id, country_code):
        # TODO
        return 0

########NEW FILE########
__FILENAME__ = tests
from decimal import Decimal
from datetime import date
from datetime import timedelta

from django.core.exceptions import ImproperlyConfigured, ValidationError
from django.test import TestCase
from django.contrib.auth.models import User
from django.conf import settings
from django.core import mail
from django.db.models import Q
from django.utils import six


if six.PY2:
    import mock
elif six.PY3:
    from unittest import mock

from plans.models import PlanPricing, Invoice, Order, Plan
from plans.plan_change import PlanChangePolicy, StandardPlanChangePolicy
from plans.taxation.eu import EUTaxationPolicy
from plans.quota import get_user_quota
from plans.validators import ModelCountValidator


class PlansTestCase(TestCase):
    fixtures = ['initial_plan', 'test_django-plans_auth', 'test_django-plans_plans']

    def setUp(self):
        mail.outbox = []

    def test_get_user_quota(self):
        u = User.objects.get(username='test1')
        self.assertEqual(get_user_quota(u),
                         {u'CUSTOM_WATERMARK': 1, u'MAX_GALLERIES_COUNT': 3, u'MAX_PHOTOS_PER_GALLERY': None})

    def test_get_plan_quota(self):
        u = User.objects.get(username='test1')
        p = u.userplan.plan
        self.assertEqual(p.get_quota_dict(),
                         {u'CUSTOM_WATERMARK': 1, u'MAX_GALLERIES_COUNT': 3, u'MAX_PHOTOS_PER_GALLERY': None})


    def test_extend_account_same_plan_future(self):
        u = User.objects.get(username='test1')
        u.userplan.expire = date.today() + timedelta(days=50)
        u.userplan.active = False
        u.userplan.save()
        plan_pricing = PlanPricing.objects.get(plan=u.userplan.plan, pricing__period=30)
        u.userplan.extend_account(plan_pricing.plan, plan_pricing.pricing)
        self.assertEqual(u.userplan.expire,
                         date.today() + timedelta(days=50) + timedelta(days=plan_pricing.pricing.period))
        self.assertEqual(u.userplan.plan, plan_pricing.plan)
        self.assertEqual(u.userplan.active, True)
        self.assertEqual(len(mail.outbox), 1)

    def test_extend_account_same_plan_before(self):
        u = User.objects.get(username='test1')
        u.userplan.expire = date.today() - timedelta(days=50)
        u.userplan.active = False
        u.userplan.save()
        plan_pricing = PlanPricing.objects.get(plan=u.userplan.plan, pricing__period=30)
        u.userplan.extend_account(plan_pricing.plan, plan_pricing.pricing)
        self.assertEqual(u.userplan.expire, date.today() + timedelta(days=plan_pricing.pricing.period))
        self.assertEqual(u.userplan.plan, plan_pricing.plan)
        self.assertEqual(u.userplan.active, True)
        self.assertEqual(len(mail.outbox), 1)

    def test_extend_account_other(self):
        """
        Tests extending account with other Plan that user had before:
        Tests if expire date is set correctly
        Tests if mail has been send
        Tests if account has been activated
        """
        u = User.objects.get(username='test1')
        u.userplan.expire = date.today() - timedelta(days=50)
        u.userplan.active = False
        u.userplan.save()
        plan_pricing = PlanPricing.objects.filter(~Q(plan=u.userplan.plan) & Q(pricing__period=30))[0]
        u.userplan.extend_account(plan_pricing.plan, plan_pricing.pricing)
        self.assertEqual(u.userplan.expire, date.today() + timedelta(days=plan_pricing.pricing.period))
        self.assertEqual(u.userplan.plan, plan_pricing.plan)
        self.assertEqual(u.userplan.active, True)
        self.assertEqual(len(mail.outbox), 1)

    def test_expire_account(self):
        u = User.objects.get(username='test1')
        u.userplan.expire = date.today() + timedelta(days=50)
        u.userplan.active = True
        u.userplan.save()
        u.userplan.expire_account()
        self.assertEqual(u.userplan.active, False)
        self.assertEqual(len(mail.outbox), 1)

    def test_remind_expire(self):
        u = User.objects.get(username='test1')
        u.userplan.expire = date.today() + timedelta(days=14)
        u.userplan.active = True
        u.userplan.save()
        u.userplan.remind_expire_soon()
        self.assertEqual(u.userplan.active, True)
        self.assertEqual(len(mail.outbox), 1)

    def test_disable_emails(self):
        with self.settings(SEND_PLANS_EMAILS=False):
            # Re-run the remind_expire test, but look for 0 emails sent
            u = User.objects.get(username='test1')
            u.userplan.expire = date.today() + timedelta(days=14)
            u.userplan.active = True
            u.userplan.save()
            u.userplan.remind_expire_soon()
            self.assertEqual(u.userplan.active, True)
            self.assertEqual(len(mail.outbox), 0)


class TestInvoice(TestCase):
    fixtures = ['initial_plan', 'test_django-plans_auth', 'test_django-plans_plans']

    def test_get_full_number(self):
        i = Invoice()
        i.number = 123
        i.issued = date(2010, 5, 30)
        self.assertEqual(i.get_full_number(), "123/FV/05/2010")

    def test_get_full_number_type1(self):
        i = Invoice()
        i.type = Invoice.INVOICE_TYPES.INVOICE
        i.number = 123
        i.issued = date(2010, 5, 30)
        self.assertEqual(i.get_full_number(), "123/FV/05/2010")

    def test_get_full_number_type2(self):
        i = Invoice()
        i.type = Invoice.INVOICE_TYPES.DUPLICATE
        i.number = 123
        i.issued = date(2010, 5, 30)
        self.assertEqual(i.get_full_number(), "123/FV/05/2010")

    def test_get_full_number_type3(self):
        i = Invoice()
        i.type = Invoice.INVOICE_TYPES.PROFORMA
        i.number = 123
        i.issued = date(2010, 5, 30)
        self.assertEqual(i.get_full_number(), "123/PF/05/2010")

    def test_get_full_number_with_settings(self):
        settings.INVOICE_NUMBER_FORMAT = "{{ invoice.issued|date:'Y' }}." \
                                         "{{ invoice.number }}.{{ invoice.issued|date:'m' }}"
        i = Invoice()
        i.number = 123
        i.issued = date(2010, 5, 30)
        self.assertEqual(i.get_full_number(), "2010.123.05")

    def test_set_issuer_invoice_data_raise(self):
        issdata = settings.ISSUER_DATA
        del settings.ISSUER_DATA
        i = Invoice()
        self.assertRaises(ImproperlyConfigured, i.set_issuer_invoice_data)
        settings.ISSUER_DATA = issdata

    def test_set_issuer_invoice_data(self):
        i = Invoice()
        i.set_issuer_invoice_data()
        self.assertEqual(i.issuer_name, settings.ISSUER_DATA['issuer_name'])
        self.assertEqual(i.issuer_street, settings.ISSUER_DATA['issuer_street'])
        self.assertEqual(i.issuer_zipcode, settings.ISSUER_DATA['issuer_zipcode'])
        self.assertEqual(i.issuer_city, settings.ISSUER_DATA['issuer_city'])
        self.assertEqual(i.issuer_country, settings.ISSUER_DATA['issuer_country'])
        self.assertEqual(i.issuer_tax_number, settings.ISSUER_DATA['issuer_tax_number'])

    def set_buyer_invoice_data(self):
        i = Invoice()
        u = User.objects.get(username='test1')
        i.set_buyer_invoice_data(u.billinginfo)
        self.assertEqual(i.buyer_name, u.billinginfo.name)
        self.assertEqual(i.buyer_street, u.billinginfo.street)
        self.assertEqual(i.buyer_zipcode, u.billinginfo.zipcode)
        self.assertEqual(i.buyer_city, u.billinginfo.city)
        self.assertEqual(i.buyer_country, u.billinginfo.country)
        self.assertEqual(i.buyer_tax_number, u.billinginfo.tax_number)
        self.assertEqual(i.buyer_name, u.billinginfo.shipping_name)
        self.assertEqual(i.buyer_street, u.billinginfo.shipping_street)
        self.assertEqual(i.buyer_zipcode, u.billinginfo.shipping_zipcode)
        self.assertEqual(i.buyer_city, u.billinginfo.shipping_city)
        self.assertEqual(i.buyer_country, u.billinginfo.shipping_country)

    def test_invoice_number(self):
        settings.INVOICE_NUMBER_FORMAT = "{{ invoice.number }}/{% ifequal " \
                                         "invoice.type invoice.INVOICE_TYPES.PROFORMA %}PF{% else %}FV" \
                                         "{% endifequal %}/{{ invoice.issued|date:'m/Y' }}"
        o = Order.objects.all()[0]
        day = date(2010, 5, 3)
        i = Invoice(issued=day, selling_date=day, payment_date=day)
        i.copy_from_order(o)
        i.set_issuer_invoice_data()
        i.set_buyer_invoice_data(o.user.billinginfo)
        i.clean()
        i.save()

        self.assertEqual(i.number, 1)
        self.assertEqual(i.full_number, '1/FV/05/2010')

    def test_invoice_number_daily(self):
        settings.INVOICE_NUMBER_FORMAT = "{{ invoice.number }}/{% ifequal " \
                                         "invoice.type invoice.INVOICE_TYPES.PROFORMA %}PF{% else %}FV" \
                                         "{% endifequal %}/{{ invoice.issued|date:'d/m/Y' }}"
        settings.INVOICE_COUNTER_RESET = Invoice.NUMBERING.DAILY

        user = User.objects.get(username='test1')
        plan_pricing = PlanPricing.objects.all()[0]
        tax = getattr(settings, "TAX")
        currency = getattr(settings, "CURRENCY")
        o1 = Order(user=user, plan=plan_pricing.plan,
                   pricing=plan_pricing.pricing, amount=plan_pricing.price,
                   tax=tax, currency=currency)
        o1.save()

        o2 = Order(user=user, plan=plan_pricing.plan,
                   pricing=plan_pricing.pricing, amount=plan_pricing.price,
                   tax=tax, currency=currency)
        o2.save()

        o3 = Order(user=user, plan=plan_pricing.plan,
                   pricing=plan_pricing.pricing, amount=plan_pricing.price,
                   tax=tax, currency=currency)
        o3.save()

        day = date(2001, 5, 3)
        i1 = Invoice(issued=day, selling_date=day, payment_date=day)
        i1.copy_from_order(o1)
        i1.set_issuer_invoice_data()
        i1.set_buyer_invoice_data(o1.user.billinginfo)
        i1.clean()
        i1.save()

        i2 = Invoice(issued=day, selling_date=day, payment_date=day)
        i2.copy_from_order(o2)
        i2.set_issuer_invoice_data()
        i2.set_buyer_invoice_data(o2.user.billinginfo)
        i2.clean()
        i2.save()

        day = date(2001, 5, 4)
        i3 = Invoice(issued=day, selling_date=day, payment_date=day)
        i3.copy_from_order(o1)
        i3.set_issuer_invoice_data()
        i3.set_buyer_invoice_data(o1.user.billinginfo)
        i3.clean()
        i3.save()

        self.assertEqual(i1.full_number, "1/FV/03/05/2001")
        self.assertEqual(i2.full_number, "2/FV/03/05/2001")
        self.assertEqual(i3.full_number, "1/FV/04/05/2001")

    def test_invoice_number_monthly(self):
        settings.INVOICE_NUMBER_FORMAT = "{{ invoice.number }}/{% ifequal " \
                                         "invoice.type invoice.INVOICE_TYPES.PROFORMA %}PF{% else %}FV" \
                                         "{% endifequal %}/{{ invoice.issued|date:'m/Y' }}"
        settings.INVOICE_COUNTER_RESET = Invoice.NUMBERING.MONTHLY

        user = User.objects.get(username='test1')
        plan_pricing = PlanPricing.objects.all()[0]
        tax = getattr(settings, "TAX")
        currency = getattr(settings, "CURRENCY")
        o1 = Order(user=user, plan=plan_pricing.plan,
                   pricing=plan_pricing.pricing, amount=plan_pricing.price,
                   tax=tax, currency=currency)
        o1.save()

        o2 = Order(user=user, plan=plan_pricing.plan,
                   pricing=plan_pricing.pricing, amount=plan_pricing.price,
                   tax=tax, currency=currency)
        o2.save()

        o3 = Order(user=user, plan=plan_pricing.plan,
                   pricing=plan_pricing.pricing, amount=plan_pricing.price,
                   tax=tax, currency=currency)
        o3.save()

        day = date(2002, 5, 3)
        i1 = Invoice(issued=day, selling_date=day, payment_date=day)
        i1.copy_from_order(o1)
        i1.set_issuer_invoice_data()
        i1.set_buyer_invoice_data(o1.user.billinginfo)
        i1.clean()
        i1.save()

        day = date(2002, 5, 13)
        i2 = Invoice(issued=day, selling_date=day, payment_date=day)
        i2.copy_from_order(o2)
        i2.set_issuer_invoice_data()
        i2.set_buyer_invoice_data(o2.user.billinginfo)
        i2.clean()
        i2.save()

        day = date(2002, 6, 1)
        i3 = Invoice(issued=day, selling_date=day, payment_date=day)
        i3.copy_from_order(o1)
        i3.set_issuer_invoice_data()
        i3.set_buyer_invoice_data(o1.user.billinginfo)
        i3.clean()
        i3.save()

        self.assertEqual(i1.full_number, "1/FV/05/2002")
        self.assertEqual(i2.full_number, "2/FV/05/2002")
        self.assertEqual(i3.full_number, "1/FV/06/2002")

    def test_invoice_number_annually(self):
        settings.INVOICE_NUMBER_FORMAT = "{{ invoice.number }}/{% ifequal " \
                                         "invoice.type invoice.INVOICE_TYPES.PROFORMA %}PF{% else %}FV" \
                                         "{% endifequal %}/{{ invoice.issued|date:'Y' }}"
        settings.INVOICE_COUNTER_RESET = Invoice.NUMBERING.ANNUALLY

        user = User.objects.get(username='test1')
        plan_pricing = PlanPricing.objects.all()[0]
        tax = getattr(settings, "TAX")
        currency = getattr(settings, "CURRENCY")
        o1 = Order(user=user, plan=plan_pricing.plan,
                   pricing=plan_pricing.pricing, amount=plan_pricing.price,
                   tax=tax, currency=currency)
        o1.save()

        o2 = Order(user=user, plan=plan_pricing.plan,
                   pricing=plan_pricing.pricing, amount=plan_pricing.price,
                   tax=tax, currency=currency)
        o2.save()

        o3 = Order(user=user, plan=plan_pricing.plan,
                   pricing=plan_pricing.pricing, amount=plan_pricing.price,
                   tax=tax, currency=currency)
        o3.save()

        day = date(1991, 5, 3)
        i1 = Invoice(issued=day, selling_date=day, payment_date=day)
        i1.copy_from_order(o1)
        i1.set_issuer_invoice_data()
        i1.set_buyer_invoice_data(o1.user.billinginfo)
        i1.clean()
        i1.save()

        day = date(1991, 7, 13)
        i2 = Invoice(issued=day, selling_date=day, payment_date=day)
        i2.copy_from_order(o2)
        i2.set_issuer_invoice_data()
        i2.set_buyer_invoice_data(o2.user.billinginfo)
        i2.clean()
        i2.save()

        day = date(1992, 6, 1)
        i3 = Invoice(issued=day, selling_date=day, payment_date=day)
        i3.copy_from_order(o1)
        i3.set_issuer_invoice_data()
        i3.set_buyer_invoice_data(o1.user.billinginfo)
        i3.clean()
        i3.save()

        self.assertEqual(i1.full_number, "1/FV/1991")
        self.assertEqual(i2.full_number, "2/FV/1991")
        self.assertEqual(i3.full_number, "1/FV/1992")

    def test_set_order(self):
        o = Order.objects.all()[0]

        i = Invoice()
        i.copy_from_order(o)

        self.assertEqual(i.order, o)
        self.assertEqual(i.user, o.user)
        self.assertEqual(i.total_net, o.amount)
        self.assertEqual(i.unit_price_net, o.amount)
        self.assertEqual(i.total, o.total())
        self.assertEqual(i.tax, o.tax)
        self.assertEqual(i.tax_total, o.total() - o.amount)
        self.assertEqual(i.currency, o.currency)


class OrderTestCase(TestCase):
    def test_amount_taxed_none(self):
        o = Order()
        o.amount = Decimal(123)
        o.tax = None
        self.assertEqual(o.total(), Decimal('123'))

    def test_amount_taxed_0(self):
        o = Order()
        o.amount = Decimal(123)
        o.tax = Decimal(0)
        self.assertEqual(o.total(), Decimal('123'))

    def test_amount_taxed_23(self):
        o = Order()
        o.amount = Decimal(123)
        o.tax = Decimal(23)
        self.assertEqual(o.total(), Decimal('151.29'))


class PlanChangePolicyTestCase(TestCase):
    fixtures = ['initial_plan', 'test_django-plans_auth', 'test_django-plans_plans']

    def setUp(self):
        self.policy = PlanChangePolicy()

    def test_calculate_day_cost(self):
        plan = Plan.objects.get(pk=5)
        self.assertEqual(self.policy._calculate_day_cost(plan, 13), Decimal('6.67'))

    def test_get_change_price(self):
        p1 = Plan.objects.get(pk=3)
        p2 = Plan.objects.get(pk=4)
        self.assertEqual(self.policy.get_change_price(p1, p2, 23), Decimal('7.82'))
        self.assertEqual(self.policy.get_change_price(p2, p1, 23), None)

    def test_get_change_price1(self):
        p1 = Plan.objects.get(pk=3)
        p2 = Plan.objects.get(pk=4)
        self.assertEqual(self.policy.get_change_price(p1, p2, 53), Decimal('18.02'))
        self.assertEqual(self.policy.get_change_price(p2, p1, 53), None)

    def test_get_change_price2(self):
        p1 = Plan.objects.get(pk=3)
        p2 = Plan.objects.get(pk=4)
        self.assertEqual(self.policy.get_change_price(p1, p2, -53), None)
        self.assertEqual(self.policy.get_change_price(p1, p2, 0), None)


class StandardPlanChangePolicyTestCase(TestCase):
    fixtures = ['initial_plan', 'test_django-plans_auth', 'test_django-plans_plans']

    def setUp(self):
        self.policy = StandardPlanChangePolicy()

    def test_get_change_price(self):
        p1 = Plan.objects.get(pk=3)
        p2 = Plan.objects.get(pk=4)
        self.assertEqual(self.policy.get_change_price(p1, p2, 23), Decimal('8.60'))
        self.assertEqual(self.policy.get_change_price(p2, p1, 23), None)


class EUTaxationPolicyTestCase(TestCase):
    def setUp(self):
        self.policy = EUTaxationPolicy()

    def test_none(self):
        with self.settings(TAX=Decimal('23.0'), TAX_COUNTRY='PL'):
            self.assertEqual(self.policy.get_tax_rate(None, None), Decimal('23.0'))

    def test_private_nonEU(self):
        with self.settings(TAX=Decimal('23.0'), TAX_COUNTRY='PL'):
            self.assertEqual(self.policy.get_tax_rate(None, 'RU'), None)

    def test_private_EU_same(self):
        with self.settings(TAX=Decimal('23.0'), TAX_COUNTRY='PL'):
            self.assertEqual(self.policy.get_tax_rate(None, 'PL'), Decimal('23.0'))

    def test_private_EU_notsame(self):
        with self.settings(TAX=Decimal('23.0'), TAX_COUNTRY='PL'):
            self.assertEqual(self.policy.get_tax_rate(None, 'AT'), Decimal('23.0'))

    def test_company_nonEU(self):
        with self.settings(TAX=Decimal('23.0'), TAX_COUNTRY='PL'):
            self.assertEqual(self.policy.get_tax_rate('123456', 'RU'), None)

    def test_company_EU_same(self):
        with self.settings(TAX=Decimal('23.0'), TAX_COUNTRY='PL'):
            self.assertEqual(self.policy.get_tax_rate('123456', 'PL'), Decimal('23.0'))

    @mock.patch("vatnumber.check_vies", lambda x: True)
    def test_company_EU_notsame_vies_ok(self):
        with self.settings(TAX=Decimal('23.0'), TAX_COUNTRY='PL'):
            self.assertEqual(self.policy.get_tax_rate('123456', 'AT'), None)

    @mock.patch("vatnumber.check_vies", lambda x: False)
    def test_company_EU_notsame_vies_not_ok(self):
        with self.settings(TAX=Decimal('23.0'), TAX_COUNTRY='PL'):
            self.assertEqual(self.policy.get_tax_rate('123456', 'AT'), Decimal('23.0'))


class ValidatorsTestCase(TestCase):
    def test_model_count_validator(self):
        """
        We create a test model validator for User. It will raise ValidationError when QUOTA_NAME value
        will be lower than number of elements of model User.
        """

        class TestValidator(ModelCountValidator):
            code = 'QUOTA_NAME'
            model = User

        validator_object = TestValidator()
        self.assertRaises(ValidationError, validator_object, user=None, quota_dict={'QUOTA_NAME': 1})
        self.assertEqual(validator_object(user=None, quota_dict={'QUOTA_NAME': 2}), None)
        self.assertEqual(validator_object(user=None, quota_dict={'QUOTA_NAME': 3}), None)


        #   TODO: FIX this test not to use Pricing for testing  ModelAttributeValidator
        # def test_model_attribute_validator(self):
        #     """
        #     We create a test attribute validator which will validate if Pricing objects has a specific value set.
        #     """
        #
        #     class TestValidator(ModelAttributeValidator):
        #         code = 'QUOTA_NAME'
        #         attribute = 'period'
        #         model = Pricing
        #
        #     validator_object = TestValidator()
        #     self.assertRaises(ValidationError, validator_object, user=None, quota_dict={'QUOTA_NAME': 360})
        #     self.assertEqual(validator_object(user=None, quota_dict={'QUOTA_NAME': 365}), None)

########NEW FILE########
__FILENAME__ = urls
from django.conf import settings
from django.conf.urls import patterns, url

from plans.views import CreateOrderView, OrderListView, InvoiceDetailView, AccountActivationView, \
    OrderPaymentReturnView, CurrentPlanView, UpgradePlanView, OrderView, BillingInfoRedirectView, \
    BillingInfoCreateView, BillingInfoUpdateView, BillingInfoDeleteView, CreateOrderPlanChangeView, ChangePlanView, \
    PricingView, FakePaymentsView

urlpatterns = patterns(
    '',
    url(r'^pricing/$', PricingView.as_view(), name='pricing'),
    url(r'^account/$', CurrentPlanView.as_view(), name='current_plan'),
    url(r'^account/activation/$', AccountActivationView.as_view(), name='account_activation'),
    url(r'^upgrade/$', UpgradePlanView.as_view(), name='upgrade_plan'),
    url(r'^order/extend/new/(?P<pk>\d+)/$', CreateOrderView.as_view(), name='create_order_plan'),
    url(r'^order/upgrade/new/(?P<pk>\d+)/$', CreateOrderPlanChangeView.as_view(), name='create_order_plan_change'),
    url(r'^change/(?P<pk>\d+)/$', ChangePlanView.as_view(), name='change_plan'),
    url(r'^order/$', OrderListView.as_view(), name='order_list'),
    url(r'^order/(?P<pk>\d+)/$', OrderView.as_view(), name='order'),
    url(r'^order/(?P<pk>\d+)/payment/success/$', OrderPaymentReturnView.as_view(status='success'),
        name='order_payment_success'),
    url(r'^order/(?P<pk>\d+)/payment/failure/$', OrderPaymentReturnView.as_view(status='failure'),
        name='order_payment_failure'),
    url(r'^billing/$', BillingInfoRedirectView.as_view(), name='billing_info'),
    url(r'^billing/create/$', BillingInfoCreateView.as_view(), name='billing_info_create'),
    url(r'^billing/update/$', BillingInfoUpdateView.as_view(), name='billing_info_update'),
    url(r'^billing/delete/$', BillingInfoDeleteView.as_view(), name='billing_info_delete'),
    url(r'^invoice/(?P<pk>\d+)/preview/html/$', InvoiceDetailView.as_view(), name='invoice_preview_html'),
)

if getattr(settings, 'DEBUG', False):
    urlpatterns += (
        url(r'^fakepayments/(?P<pk>\d+)/$', FakePaymentsView.as_view(), name='fake_payments'),
    )
########NEW FILE########
__FILENAME__ = validators
from django.conf import settings
from django.core.exceptions import ValidationError, ImproperlyConfigured
from django.utils.translation import ugettext_lazy as _
import six

from plans.importer import import_name
from plans.quota import get_user_quota


class QuotaValidator(object):
    """
    Base class for all Quota validators needed for account activation
    """

    required_to_activate = True

    @property
    def code(self):
        raise ImproperlyConfigured('Quota code name is not provided for validator')

    def get_quota_value(self, user, quota_dict=None):
        """
        Returns quota value for a given user
        """
        if quota_dict is None:
            quota_dict = get_user_quota(user)

        return quota_dict.get(self.code, None)

    def get_error_message(self, quota_value, **kwargs):
        return u'Plan validation error'

    def __call__(self, user, quota_dict=None, **kwargs):
        """
        Performs validation of quota limit for a user account
        """
        raise NotImplementedError('Please implement specific QuotaValidator')

    def on_activation(self, user, quota_dict=None, **kwargs):
        """
        Hook for any action that validator needs to do while successful activation of the plan
        Most useful for validators not required to activate, e.g. some "option" is turned ON for user
        but when user downgrade plan this option should be turned OFF automatically rather than
        stops account activation
        """
        pass


class ModelCountValidator(QuotaValidator):
    """
    Validator that checks if there is no more than quota number of objects given model
    """

    @property
    def model(self):
        raise ImproperlyConfigured('ModelCountValidator requires model name')

    def get_queryset(self, user):
        return self.model.objects.all()

    def get_error_message(self, quota_value, **kwargs):
        return _('Limit of %(model_name_plural)s exceeded. The limit is %(quota)s items.') % {
            'model_name_plural': self.model._meta.verbose_name_plural.title().lower(),
            'quota': quota_value,
        }

    def __call__(self, user, quota_dict=None, **kwargs):
        quota = self.get_quota_value(user, quota_dict)
        total_count = self.get_queryset(user).count() + kwargs.get('add', 0)
        if not quota is None and total_count > quota:
            raise ValidationError(self.get_error_message(quota))


class ModelAttributeValidator(ModelCountValidator):
    """
    Validator checks if every obj.attribute value for a given model satisfy condition
    provided in check_attribute_value() method.

    .. warning::
        ModelAttributeValidator requires `get_absolute_url()` method on provided model.
    """

    @property
    def attribute(self):
        raise ImproperlyConfigured('ModelAttributeValidator requires defining attribute name')

    def check_attribute_value(self, attribute_value, quota_value):
        # default is to value is <= limit
        return attribute_value <= quota_value

    def get_error_message(self, quota_value, **kwargs):
        return _('Following %(model_name_plural)s are not in limits: %(objects)s') % {
            'model_name_plural': self.model._meta.verbose_name_plural.title().lower(),
            'objects': u', '.join(map(lambda o: u'<a href="%s">%s</a>' % (o.get_absolute_url(), six.u(o)),
                                      kwargs['not_valid_objects'])),
        }

    def __call__(self, user, quota_dict=None, **kwargs):
        quota_value = self.get_quota_value(user, quota_dict)
        not_valid_objects = []
        if not quota_value is None:
            for obj in self.get_queryset(user):
                if not self.check_attribute_value(getattr(obj, self.attribute), quota_value):
                    not_valid_objects.append(obj)
        if not_valid_objects:
            raise ValidationError(
                self.get_error_message(quota_value, not_valid_objects=not_valid_objects)
            )


def plan_validation(user, plan=None, on_activation=False):
    """
    Validates validator that represents quotas in a given system
    :param user:
    :param plan:
    :return:
    """
    if plan is None:
        # if plan is not given, the default is to use current plan of the user
        plan = user.userplan.plan
    quota_dict = plan.get_quota_dict()
    validators = getattr(settings, 'PLAN_VALIDATORS', {})
    errors = {
        'required_to_activate': [],
        'other': [],
    }
    for quota in quota_dict:
        if quota in validators:
            validator = import_name(validators[quota])

            if on_activation:
                validator.on_activation(user, quota_dict)
            else:
                try:
                    validator(user, quota_dict)
                except ValidationError as e:
                    if validator.required_to_activate:
                        errors['required_to_activate'].extend(e.messages)
                    else:
                        errors['other'].extend(e.messages)
    return errors
########NEW FILE########
__FILENAME__ = views
from decimal import Decimal

from django.core.urlresolvers import reverse
from django.core.exceptions import ImproperlyConfigured
from django.shortcuts import get_object_or_404
from django.views.generic import TemplateView, RedirectView, CreateView, UpdateView, View
from django.db.models import Q
from django.http import Http404, HttpResponseRedirect, HttpResponseForbidden
from django.conf import settings
from django.contrib import messages
from django.utils.translation import ugettext_lazy as _
from django.views.generic.detail import DetailView, SingleObjectMixin
from django.views.generic.edit import DeleteView, ModelFormMixin, FormView
from django.views.generic.list import ListView

from itertools import chain
from plans.importer import import_name
from plans.mixins import LoginRequired
from plans.models import UserPlan, PlanPricing, Plan, Order, BillingInfo
from plans.forms import CreateOrderForm, BillingInfoForm, FakePaymentsForm
from plans.models import Quota, Invoice
from plans.signals import order_started
from plans.validators import plan_validation


class AccountActivationView(LoginRequired, TemplateView):
    template_name = 'plans/account_activation.html'

    def get_context_data(self, **kwargs):
        if self.request.user.userplan.active == True or self.request.user.userplan.is_expired():
            raise Http404()

        context = super(AccountActivationView, self).get_context_data(**kwargs)
        errors = self.request.user.userplan.clean_activation()

        if errors['required_to_activate']:
            context['SUCCESSFUL'] = False
        else:
            context['SUCCESSFUL'] = True
            messages.success(self.request, _("Your account is now active"))

        for error in errors['required_to_activate']:
            messages.error(self.request, error)
        for error in errors['other']:
            messages.warning(self.request, error)

        return context


class PlanTableMixin(object):
    def get_plan_table(self, plan_list):
        """
        This method return a list in following order:
        [
            ( Quota1, [ Plan1Quota1, Plan2Quota1, ... , PlanNQuota1] ),
            ( Quota2, [ Plan1Quota2, Plan2Quota2, ... , PlanNQuota2] ),
            ...
            ( QuotaM, [ Plan1QuotaM, Plan2QuotaM, ... , PlanNQuotaM] ),
        ]

        This can be very easily printed as an HTML table element with quotas by row.

        Quotas are calculated based on ``plan_list``. These are all available quotas that are
        used by given plans. If any ``Plan`` does not have any of ``PlanQuota`` then value ``None``
        will be propagated to the data structure.

        """

        # Retrieve all quotas that are used by any ``Plan`` in ``plan_list``
        quota_list = Quota.objects.all().filter(planquota__plan__in=plan_list).distinct()

        # Create random access dict that for every ``Plan`` map ``Quota`` -> ``PlanQuota``
        plan_quotas_dic = {}
        for plan in plan_list:
            plan_quotas_dic[plan] = {}
            for plan_quota in plan.planquota_set.all():
                plan_quotas_dic[plan][plan_quota.quota] = plan_quota

        # Generate data structure described in method docstring, propagate ``None`` whenever
        # ``PlanQuota`` is not available for given ``Plan`` and ``Quota``
        return map(lambda quota: (quota,
                                  map(lambda plan: plan_quotas_dic[plan].get(quota, None), plan_list)

        ), quota_list)


class PlanTableViewBase(PlanTableMixin, ListView):
    model = Plan
    context_object_name = "plan_list"

    def get_queryset(self):
        queryset = super(PlanTableViewBase, self).get_queryset().prefetch_related('planpricing_set__pricing',
                                                                                  'planquota_set__quota')
        if self.request.user.is_authenticated():
            queryset = queryset.filter(
                Q(available=True, visible=True) & (
                    Q(customized=self.request.user) | Q(customized__isnull=True)
                )
            )
        else:
            queryset = queryset.filter(Q(available=True, visible=True) & Q(customized__isnull=True))
        return queryset

    def get_context_data(self, **kwargs):
        context = super(PlanTableViewBase, self).get_context_data(**kwargs)

        if self.request.user.is_authenticated():
            try:
                self.userplan = UserPlan.objects.select_related('plan').get(user=self.request.user)
            except UserPlan.DoesNotExist:
                self.userplan = None

            context['userplan'] = self.userplan

            try:
                context['current_userplan_index'] = list(self.object_list).index(self.userplan.plan)
            except (ValueError, AttributeError):
                pass

        context['plan_table'] = self.get_plan_table(self.object_list)
        context['CURRENCY'] = settings.CURRENCY

        return context


class CurrentPlanView(LoginRequired, PlanTableViewBase):
    template_name = "plans/current.html"

    def get_queryset(self):
        return Plan.objects.filter(userplan__user=self.request.user).prefetch_related('planpricing_set__pricing',
                                                                                      'planquota_set__quota')


class UpgradePlanView(LoginRequired, PlanTableViewBase):
    template_name = "plans/upgrade.html"


class PricingView(PlanTableViewBase):
    template_name = "plans/pricing.html"


class ChangePlanView(LoginRequired, View):
    """
    A view for instant changing user plan when it does not require additional payment.
    Plan can be changed without payment when:
    * user can enable this plan (it is available & visible and if it is customized it is for him,
    * plan is different from the current one that user have,
    * within current change plan policy this does not require any additional payment (None)

    It always redirects to ``upgrade_plan`` url as this is a potential only one place from
    where change plan could be invoked.
    """

    def get(self, request, *args, **kwargs):
        return HttpResponseRedirect(reverse('upgrade_plan'))

    def post(self, request, *args, **kwargs):
        plan = get_object_or_404(Plan, Q(pk=kwargs['pk']) & Q(available=True, visible=True) & (
            Q(customized=request.user) | Q(customized__isnull=True)))
        if request.user.userplan.plan != plan:
            policy = import_name(
                getattr(settings, 'PLAN_CHANGE_POLICY', 'plans.plan_change.StandardPlanChangePolicy'))()

            period = request.user.userplan.days_left()
            price = policy.get_change_price(request.user.userplan.plan, plan, period)

            if price is None:
                request.user.userplan.extend_account(plan, None)
                messages.success(request, _("Your plan has been successfully changed"))
            else:
                return HttpResponseForbidden()
        return HttpResponseRedirect(reverse('upgrade_plan'))


class CreateOrderView(LoginRequired, CreateView):
    template_name = "plans/create_order.html"
    form_class = CreateOrderForm

    def recalculate(self, amount, billing_info):
        """
        Calculates and return pre-filled Order
        """
        order = Order(pk=-1)
        order.amount = amount
        order.currency = self.get_currency()
        country = getattr(billing_info, 'country', None)
        if not country is None:
            country = country.code
        tax_number = getattr(billing_info, 'tax_number', None)

        # Calculating session can be complex task (e.g. VIES webservice call)
        # To ensure that once we get what tax we display to confirmation it will
        # not change, tax rate is cached for a given billing data (as it mainly depends on it)
        tax_session_key = "tax_%s_%s" % (tax_number, country)

        tax = self.request.session.get(tax_session_key)

        if tax is None:
            taxation_policy = getattr(settings, 'TAXATION_POLICY', None)
            if not taxation_policy:
                raise ImproperlyConfigured('TAXATION_POLICY is not set')
            taxation_policy = import_name(taxation_policy)
            tax = str(taxation_policy.get_tax_rate(tax_number, country))
            # Because taxation policy could return None which clutters with saving this value
            # into cache, we use str() representation of this value
            self.request.session[tax_session_key] = tax

        order.tax = Decimal(tax) if tax != 'None' else None

        return order

    def validate_plan(self, plan):
        validation_errors = plan_validation(self.request.user, plan)
        if validation_errors['required_to_activate'] or validation_errors['other']:
            messages.error(self.request, _(
                "The selected plan is insufficient for your account. "
                "Your account will not be activated or will not work fully after completing this order."
                "<br><br>Following limits will be exceeded: <ul><li>%(reasons)s</ul>") % {
                                             'reasons': '<li>'.join(chain(validation_errors['required_to_activate'],
                                                                          validation_errors['other'])),
                                         })


    def get_all_context(self):
        """
        Retrieves Plan and Pricing for current order creation
        """
        self.plan_pricing = get_object_or_404(PlanPricing.objects.all().select_related('plan', 'pricing'),
                                              Q(pk=self.kwargs['pk']) & Q(plan__available=True) & (
                                                  Q(plan__customized=self.request.user) | Q(
                                                      plan__customized__isnull=True)))


        # User is not allowed to create new order for Plan when he has different Plan
        # He should use Plan Change View for this kind of action
        if not self.request.user.userplan.is_expired() and self.request.user.userplan.plan != self.plan_pricing.plan:
            raise Http404

        self.plan = self.plan_pricing.plan
        self.pricing = self.plan_pricing.pricing


    def get_billing_info(self):
        try:
            return self.request.user.billinginfo
        except BillingInfo.DoesNotExist:
            return None

    def get_currency(self):
        CURRENCY = getattr(settings, 'CURRENCY', '')
        if len(CURRENCY) != 3:
            raise ImproperlyConfigured('CURRENCY should be configured as 3-letter currency code.')
        return CURRENCY

    def get_price(self):
        return self.plan_pricing.price

    def get_context_data(self, **kwargs):
        context = super(CreateOrderView, self).get_context_data(**kwargs)
        self.get_all_context()
        context['billing_info'] = self.get_billing_info()

        order = self.recalculate(self.plan_pricing.price, context['billing_info'])
        order.plan = self.plan_pricing.plan
        order.pricing = self.plan_pricing.pricing
        order.currency = self.get_currency()
        context['object'] = order

        self.validate_plan(order.plan)
        return context

    def form_valid(self, form):
        self.get_all_context()
        order = self.recalculate(self.get_price() or Decimal('0.0'), self.get_billing_info())

        self.object = form.save(commit=False)
        self.object.user = self.request.user
        self.object.plan = self.plan
        self.object.pricing = self.pricing
        self.object.amount = order.amount
        self.object.tax = order.tax
        self.object.currency = order.currency
        self.object.save()
        order_started.send(sender=self.object)
        return super(ModelFormMixin, self).form_valid(form)


class CreateOrderPlanChangeView(CreateOrderView):
    template_name = "plans/create_order.html"
    form_class = CreateOrderForm

    def get_all_context(self):
        self.plan = get_object_or_404(Plan, Q(pk=self.kwargs['pk']) & Q(available=True, visible=True) & (
            Q(customized=self.request.user) | Q(customized__isnull=True)))
        self.pricing = None

    def get_policy(self):
        policy_class = getattr(settings, 'PLAN_CHANGE_POLICY', 'plans.plan_change.StandardPlanChangePolicy')
        return import_name(policy_class)()

    def get_price(self):
        policy = self.get_policy()
        period = self.request.user.userplan.days_left()
        return policy.get_change_price(self.request.user.userplan.plan, self.plan, period)

    def get_context_data(self, **kwargs):
        context = super(CreateOrderView, self).get_context_data(**kwargs)
        self.get_all_context()

        price = self.get_price()
        context['plan'] = self.plan
        context['billing_info'] = self.get_billing_info()
        if price is None:
            context['FREE_ORDER'] = True
            price = 0
        order = self.recalculate(price, context['billing_info'])
        order.pricing = None
        order.plan = self.plan
        context['billing_info'] = context['billing_info']
        context['object'] = order
        self.validate_plan(order.plan)
        return context


class OrderView(LoginRequired, DetailView):
    model = Order


    def get_queryset(self):
        return super(OrderView, self).get_queryset().filter(user=self.request.user).select_related('plan', 'pricing', )


class OrderListView(LoginRequired, ListView):
    model = Order
    paginate_by = 10

    def get_context_data(self, **kwargs):
        context = super(OrderListView, self).get_context_data(**kwargs)
        self.CURRENCY = getattr(settings, 'CURRENCY', None)
        if len(self.CURRENCY) != 3:
            raise ImproperlyConfigured('CURRENCY should be configured as 3-letter currency code.')
        context['CURRENCY'] = self.CURRENCY
        return context


    def get_queryset(self):
        return super(OrderListView, self).get_queryset().filter(user=self.request.user).select_related('plan',
                                                                                                       'pricing', )


class OrderPaymentReturnView(LoginRequired, DetailView):
    """
    This view is a fallback from any payments processor. It allows just to set additional message
    context and redirect to Order view itself.
    """
    model = Order
    status = None

    def render_to_response(self, context, **response_kwargs):
        if self.status == 'success':
            messages.success(self.request,
                             _('Thank you for placing a payment. It will be processed as soon as possible.'))
        elif self.status == 'failure':
            messages.error(self.request, _('Payment was not completed correctly. Please repeat payment process.'))

        return HttpResponseRedirect(self.object.get_absolute_url())


    def get_queryset(self):
        return super(OrderPaymentReturnView, self).get_queryset().filter(user=self.request.user)


class BillingInfoRedirectView(LoginRequired, RedirectView):
    """
    Checks if billing data for user exists and redirects to create or update view.
    """
    permanent = False

    def get_redirect_url(self, **kwargs):
        try:
            BillingInfo.objects.get(user=self.request.user)
        except BillingInfo.DoesNotExist:
            return reverse('billing_info_create')
        return reverse('billing_info_update')


class BillingInfoCreateView(LoginRequired, CreateView):
    """
    Creates billing data for user
    """
    form_class = BillingInfoForm
    template_name = 'plans/billing_info_create.html'

    def form_valid(self, form):
        self.object = form.save(commit=False)
        self.object.user = self.request.user
        self.object.save()
        return HttpResponseRedirect(self.get_success_url())

    def get_success_url(self):
        messages.success(self.request, _('Billing info has been updated successfuly.'))
        return reverse('billing_info_update')


class BillingInfoUpdateView(LoginRequired, UpdateView):
    """
    Updates billing data for user
    """
    model = BillingInfo
    form_class = BillingInfoForm
    template_name = 'plans/billing_info_update.html'

    def get_object(self):
        try:
            return self.request.user.billinginfo
        except BillingInfo.DoesNotExist:
            raise Http404

    def get_success_url(self):
        messages.success(self.request, _('Billing info has been updated successfuly.'))
        return reverse('billing_info_update')


class BillingInfoDeleteView(LoginRequired, DeleteView):
    """
    Deletes billing data for user
    """
    template_name = 'plans/billing_info_delete.html'

    def get_object(self):
        try:
            return self.request.user.billinginfo
        except BillingInfo.DoesNotExist:
            raise Http404

    def get_success_url(self):
        messages.success(self.request, _('Billing info has been deleted.'))
        return reverse('billing_info_create')


class InvoiceDetailView(LoginRequired, DetailView):
    model = Invoice

    def get_template_names(self):
        return getattr(settings, 'INVOICE_TEMPLATE', 'plans/invoices/PL_EN.html')


    def get_context_data(self, **kwargs):
        context = super(InvoiceDetailView, self).get_context_data(**kwargs)
        context['logo_url'] = getattr(settings, 'INVOICE_LOGO_URL', None)
        context['auto_print'] = True
        return context

    def get_queryset(self):
        if self.request.user.is_superuser:
            return super(InvoiceDetailView, self).get_queryset()
        else:
            return super(InvoiceDetailView, self).get_queryset().filter(user=self.request.user)


class FakePaymentsView(LoginRequired, SingleObjectMixin, FormView):
    form_class = FakePaymentsForm
    model = Order
    template_name = 'plans/fake_payments.html'

    def get_success_url(self):
        return self.object.get_absolute_url()


    def get_queryset(self):
        return super(FakePaymentsView, self).get_queryset().filter(user=self.request.user)

    def dispatch(self, *args, **kwargs):
        if not getattr(settings, 'DEBUG', False):
            return HttpResponseForbidden('This view is accessible only in debug mode.')
        self.object = self.get_object()
        return super(FakePaymentsView, self).dispatch(*args, **kwargs)

    def form_valid(self, form):
        if int(form['status'].value()) == Order.STATUS.COMPLETED:
            self.object.complete_order()
            return HttpResponseRedirect(reverse('order_payment_success', kwargs={'pk': self.object.pk}))
        else:
            self.object.status = form['status'].value()
            self.object.save()
            return HttpResponseRedirect(reverse('order_payment_failure', kwargs={'pk': self.object.pk}))


########NEW FILE########
__FILENAME__ = admin
from django.contrib import admin
from modeltranslation.admin import TranslationAdmin
from plans.admin import UserLinkMixin, PlanAdmin, QuotaAdmin
from plans.models import Plan, Quota, Pricing

# Admin translation for django-plans

class TranslatedPlanAdmin(PlanAdmin, TranslationAdmin):
    pass

admin.site.unregister(Plan)
admin.site.register(Plan, TranslatedPlanAdmin)


class TranslatedPricingAdmin(TranslationAdmin):
    pass

admin.site.unregister(Pricing)
admin.site.register(Pricing, TranslatedPricingAdmin)


class TranslatedQuotaAdmin(QuotaAdmin, TranslationAdmin):
    pass

admin.site.unregister(Quota)
admin.site.register(Quota, TranslatedQuotaAdmin)


########NEW FILE########
__FILENAME__ = models
from django.db import models

# Create your models here.

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
__FILENAME__ = translation
from modeltranslation.translator import translator, TranslationOptions
from plans.models import Plan, Pricing, Quota


# Translations for django-plans

class PlanTranslationOptions(TranslationOptions):
    fields = ('name', 'description', )

translator.register(Plan, PlanTranslationOptions)

class PricingTranslationOptions(TranslationOptions):
    fields = ('name',)

translator.register(Pricing, PricingTranslationOptions)

class QuotaTranslationOptions(TranslationOptions):
    fields = ('name', 'description', 'unit')

translator.register(Quota, QuotaTranslationOptions)
########NEW FILE########
__FILENAME__ = views
# Create your views here.

########NEW FILE########
