__FILENAME__ = admin
import os
from django.contrib import admin
from django import forms
from django.conf import settings
from django.utils.translation import ugettext as _
from django.contrib.contenttypes import generic
from django.core.urlresolvers import reverse

from brookie.models import Client, Invoice, Tax, Quote, Item, QuotePart
from brookie.templatetags.monetize import euro, pound, sek
from brookie.utils import decimal_to_string
from brookie.views import generate_pdf
from brookie import brookie_settings as br_settings

from admin_wmdeditor import WmdEditorModelAdmin

from datetime import datetime
from decimal import Decimal

def is_expired(self):
    """ Check if an invoice is expired """
    now = datetime.now().date()
    extra = ""
    image = 'img/admin/icon_success.gif'
    days_left = (self.exp_date - now).days
    if self.status == 1: image = 'img/admin/icon_changelink.gif'
    elif self.status in (2,3):
        if days_left <= 0:
            image = 'img/admin/icon_error.gif'
            extra = _(' <strong>(%s days late.)</strong>' % (days_left * -1))
        else:
            image = 'img/admin/icon_clock.gif'
            extra = _(" (%s days left.)" % days_left)
    return '<img src="%(admin_media)s%(image)s" />%(extra)s' % {'admin_media': settings.ADMIN_MEDIA_PREFIX,
                                                               'image': image,
                                                               'extra': extra,}
is_expired.short_description = _('Payed?')
is_expired.allow_tags = True

def total_monetized(self):
    """ Shows currency in admin, currently only euro's, pounds, sgd, sek and dollars """
    if self.currency == 'euro':
        return '&euro; %s' % euro(self.total)
    elif self.currency == 'gbp':
        return '&pound; %s' % pound(self.total)
    elif self.currency == 'dollar':
        return '&dollar; %s' % pound(self.total)
    if self.currency == 'sgd':
        return '&dollar; %s' % pound(self.total)
    elif self.currency == 'sek':
        return '&kronor; %s' % sek(self.total)
total_monetized.short_description = _("Total amount")
total_monetized.allow_tags = True

def pdf_invoice(self):
    """ Show link to invoice that has been sent """
    filename = br_settings.BROOKIE_SAVE_PATH + '%s.pdf' % self.invoice_id
    if os.path.exists(filename):
        return '<a href="%(url)s">%(invoice_id)s</a>' % {'url': reverse('view-invoice', kwargs={'id': self.id }),
                                                         'invoice_id': self.invoice_id }
    else: return ''
pdf_invoice.short_description = _("Download")
pdf_invoice.allow_tags = True

class ItemInline(generic.GenericTabularInline):
    model = Item

    def get_formset(self, request, obj=None):
        formset = super(ItemInline, self).get_formset(request, obj)

        if obj is not None and obj.status in br_settings.INVOICE_FINISH_STATUS:
            formset.max_num = 0
        return formset

    def get_readonly_fields(self, request, obj=None):
        readonly = super(ItemInline, self).get_readonly_fields(request, obj)

       #    readonly = ('date', 'description', 'time', 'amount')

        return readonly

class QuoteItemInline(generic.GenericTabularInline):
    model = Item
    fields = ('description', 'time', 'amount',)

class QuotePartAdmin(admin.ModelAdmin):
    pass

class QuoteAdmin(WmdEditorModelAdmin):

    def change_view(self, request, object_id, extra_context=None):
        parts = QuotePart.objects.all()
        extra_context = {'parts': parts, }
        return super(QuoteAdmin, self).change_view(request,
                                                   object_id,
                                                   extra_context=extra_context)

    def add_view(self, request, form_url='', extra_context=None):
        parts = QuotePart.objects.all()
        extra_context = {'parts': parts, }
        return super(QuoteAdmin, self).add_view(request,
                                                form_url=form_url,
                                                extra_context=extra_context)


    wmdeditor_fields = ['content', ]
    list_display = ('quote_id', 'client', 'date', 'status', )
    list_filter = ['status',]
    ordering = ('id', )
    inlines = [QuoteItemInline, ]

    class Media:
        js = ('http://ajax.googleapis.com/ajax/libs/jquery/1.4.3/jquery.min.js', 'brookie/js/brookie.js')

class ClientAdmin(admin.ModelAdmin):
    list_display = ('company', )
    search_fields = ['company', 'first_name', 'last_name',]
    ordering = ('company', )

class TaxAdmin(admin.ModelAdmin):
    pass

class InvoiceAdmin(admin.ModelAdmin):
    list_display = ('client', 'status', 'date', total_monetized, is_expired, pdf_invoice)
    list_filter = ('status', 'date')
    exclude = ('invoice_no',)
    ordering = ('-id', )
    search_fields = ['client__company', ]
    readonly_fields = ()
    inlines = [ItemInline,]

    class Media:
        js = ('http://ajax.googleapis.com/ajax/libs/jquery/1.4.3/jquery.min.js', 'brookie/js/brookie.js')

    def get_readonly_fields(self, request, obj=None):
        readonly = super(InvoiceAdmin, self).get_readonly_fields(request, obj)

        # if the invoice is send you can no longer alter it
        if getattr(obj, 'status', None) in br_settings.INVOICE_FINISH_STATUS:
            readonly = ('invoice_id', 'client', 'date', 'currency', 'tax', 'hourly_rate')

        return readonly

    def changelist_view(self, request, extra_context=None):
        from django.contrib.admin.views.main import ChangeList
        cl = ChangeList(request, self.model, list(self.list_display),
                        self.list_display_links, self.list_filter,
                        self.date_hierarchy, self.search_fields,
                        self.list_select_related,
                        self.list_per_page,
                        self.list_editable,
                        self)


        total_dict = dict()
        outstanding_dict = dict()
        for currency, description in br_settings.INVOICE_CURRENCY_CHOICES:
            # Determine total and subtotal
            subtotal = Decimal(0)
            total = Decimal(0)
            for invoice in cl.get_query_set().filter(status=4,
                                                     currency=currency):
                subtotal += invoice.subtotal
                total += invoice.total

            # Add to dictionary
            if total > 0:
                subtotal = decimal_to_string(subtotal, currency)
                total = decimal_to_string(total, currency)
                total_dict[description.lower()] = [subtotal, total]

            subtotal = Decimal(0)
            total = Decimal(0)
            for invoice in cl.get_query_set().filter(status__in=[1, 2, 3],
                                                     currency=currency):
                subtotal += invoice.subtotal
                total += invoice.total

            # Add to dictionary
            if total > 0:
                subtotal = decimal_to_string(subtotal, currency)
                total = decimal_to_string(total, currency)
                outstanding_dict[description.lower()] = [subtotal, total]

        extra_context = dict()
        extra_context['total_dict'] = total_dict
        extra_context['outstanding_dict'] = outstanding_dict
        return super(InvoiceAdmin, self).changelist_view(request,
                                                         extra_context=extra_context)

    def save_model(self, request, obj, form, change):
        obj.save()
        if obj.status in br_settings.INVOICE_FINISH_STATUS:
            # Set the invoice id
            if obj.invoice_no is None:
                invoice_list = Invoice.objects.filter(invoice_no__isnull=False).order_by('-invoice_no')
                try:
                    invoice = invoice_list[0]
                    invoice_no = invoice.invoice_no + 1
                except:
                    # There are no numbered invoices
                    invoice_no = getattr(br_settings, 'INVOICE_START_NUMBER', 1)
                obj.invoice_no = invoice_no
                obj.save()

            # Generate the pdf for this invoice
            context_dict = {'invoice': obj,
                            'client': obj.client,
                            'items': obj.items.all(),}

            generate_pdf(obj.invoice_id, context_dict, "brookie/invoice_%s_pdf.html" % obj.currency, save=True)

admin.site.register(Invoice, InvoiceAdmin)
admin.site.register(Tax, TaxAdmin)
admin.site.register(Client, ClientAdmin)
admin.site.register(Quote, QuoteAdmin)
admin.site.register(QuotePart, QuotePartAdmin)

########NEW FILE########
__FILENAME__ = brookie_settings
from django.conf import settings

ugettext = lambda s: s

# Path to store finished invoices, don't make this public accessible
BROOKIE_SAVE_PATH = getattr(settings, 'BROOKIE_SAVE_PATH', 'brookie/invoices/')

# Amount of days before an invoice expires.
INVOICE_EXPIRATION_DAYS = getattr(settings, 'INVOICE_EXPIRATION_DAYS', 14)

# Number of digits that your Invoice ID has.
INVOICE_ID_LENGTH =  getattr(settings, 'INVOICE_ID_LENGTH', 4)

# Prefix for your Invoice ID.
INVOICE_ID_PREFIX =  getattr(settings, 'INVOICE_ID_PREFIX', "BRI")

# Default hourly rate
INVOICE_HOURLY_RATE =  getattr(settings, 'INVOICE_HOURLY_RATE', 50.00)

# Invoice status choices.
INVOICE_STATUS_CHOICES =  getattr(settings, 'INVOICE_STATUS_CHOICES', ((1, ugettext('Under development')),
                                                                      (2, ugettext('Sent')),
                                                                      (3, ugettext('Reminded')),
                                                                      (4, ugettext('Payed'))))

# When the invoice is finished you will be able to download it in the admin
INVOICE_FINISH_STATUS = getattr(settings, 'INVOICE_FINISH_STATUS', (2, 3, 4))

# Invoice numbering starts at number
INVOICE_START_NUMBER =  getattr(settings, 'INVOICE_START_NUMBER', 1)
# In what valuta do you want your invoices to be available.

# Note: Each valuta requires it's own template. For ex., pounds will look
# for a template called ``invoice_gbp_pdf.html``.
INVOICE_CURRENCY_CHOICES = getattr(settings, 'INVOICE_CURRENCY_CHOICES', (('euro', ugettext('Euro')),
                                                                          ('gbp', ugettext('Pound')),
                                                                          ('dollar', ugettext('Dollar'))))

# Length of your Quote ID.
QUOTE_ID_LENGTH = getattr(settings, 'QUOTE_ID_LENGTH', 4)

# Prefix for your Quote ID.
QUOTE_ID_PREFIX = getattr(settings, 'QUOTE_ID_PREFIX', "BRQ")

# Quote status possibilities.
QUOTE_STATUS_CHOICES = getattr(settings, 'QUOTE_STATUS_CHOICES', ((1, ugettext('Draft')),
                                                                 (2, ugettext('Sent')),
                                                                 (3, ugettext('Declined')),
                                                                 (4, ugettext('Accepted'))))



########NEW FILE########
__FILENAME__ = models
from django.db import models
from django.utils.translation import ugettext as _
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes import generic

from brookie import brookie_settings as settings

from decimal import *
from datetime import datetime, timedelta

class Client(models.Model):
    """ Model representing a client """
    company = models.CharField(_('company'), max_length=80)
    first_name = models.CharField(_('first name'), max_length=80, blank=True)
    last_name = models.CharField(_('last name'), max_length=80, blank=True)
    address = models.CharField(_('address'), max_length=255)
    zipcode = models.CharField(_('zipcode'), max_length=7)
    city = models.CharField(_('city'), max_length=128)
    country = models.CharField(_('country'), max_length=255)
    tax_name = models.CharField(_('tax name'), max_length=255, blank=True, null=True)
    tax_number = models.CharField(_('tax number'), max_length=255, blank=True, null=True)
    additional_info = models.TextField(_('additional payment info'), blank=True, null=True)

    class Meta:
        verbose_name = _('client')
        verbose_name_plural = _('clients')
        ordering = ('company', 'last_name', 'first_name')

    @property
    def full_name(self):
        return '%s %s' % (self.first_name, self.last_name)

    def __unicode__(self):
        return '%s' % self.company

class Invoice(models.Model):
    """ Model representing an invoice """
    client = models.ForeignKey(Client, verbose_name=_('client'))
    date = models.DateField(_('date'))
    currency = models.CharField(_('currency'),
                                max_length=124,
                                choices=settings.INVOICE_CURRENCY_CHOICES)
    status = models.IntegerField(_('status'), choices=settings.INVOICE_STATUS_CHOICES)
    tax = models.ForeignKey('Tax', blank=True, null=True)
    hourly_rate = models.DecimalField(_('hourly rate'),
                                      max_digits=6,
                                      decimal_places=2,
                                      default=settings.INVOICE_HOURLY_RATE)
    items = generic.GenericRelation('Item')
    invoice_no = models.PositiveIntegerField(_('invoice_no'),
                                             blank=True,
                                             null=True)

    class Meta:
        verbose_name = _('invoice')
        verbose_name_plural = _('invoices')

    def __unicode__(self):
        return '%(company)s - %(date)s' % {'company': self.client.company,
                                           'date': self.date.strftime('%d-%m-%Y') }

    @property
    def total(self):
        """ Total amount including the taxes """
        return self.subtotal if not self.tax else self.subtotal + self.total_tax

    @property
    def subtotal(self):
        """ Subtotal, the amount excluding the taxes """
        subtotal = Decimal(0)
        for item in self.items.all(): subtotal += item.amount
        return subtotal

    @property
    def total_tax(self):
        """ Total of tax payed """
        if self.tax: total_tax = (self.subtotal * (self.tax.percentage)) / 100
        else: total_tax = Decimal(0)
        return total_tax.quantize(Decimal('0.01'), ROUND_HALF_UP)

    @property
    def invoice_id(self):
        """ Unique invoice ID """
        number = (settings.INVOICE_ID_LENGTH - len(str(self.invoice_no))) * "0" + str(self.invoice_no)
        return '%(prefix)s%(year)s%(unique_id)s' % {'prefix': settings.INVOICE_ID_PREFIX,
                                                    'year': self.date.strftime("%y"),
                                                    'unique_id': number}

    @property
    def is_credit(self):
        """ Check if the invoice is a credit invoice """
        if self.total < 0:
            return True
        else: return False

    @property
    def exp_date(self):
        """ Expiration date of the invoice """
        expiration_time = timedelta(days=settings.INVOICE_EXPIRATION_DAYS)
        return (self.date + expiration_time)

class Tax(models.Model):
    """ Model representing different taxes to be used in Invoices"""
    name = models.CharField(_('name'), max_length=255)
    abbrevation = models.CharField(_('abbrevation'), max_length=255)
    percentage = models.DecimalField(_('percentage'),
                                     max_digits=4,
                                     decimal_places=2)

    class Meta:
        verbose_name = _('tax')
        verbose_name_plural = _('taxes')

    def __unicode__(self):
        return '%s' % self.name

class QuotePart(models.Model):
    """ A default part that can be inserted in a quote """
    name = models.CharField(_('name'), max_length=255)
    content = models.TextField(_('content'), help_text=_('The above will be selectable when creating a new Quote. Markdown is enabled.'))

    class Meta:
        ordering = ('name',)

    def __unicode__(self):
        return '%s' % self.name

class Quote(models.Model):
    """ Model representing a quote """
    client = models.ForeignKey(Client, related_name=_('quote'))
    date = models.DateField(_('date'))
    status = models.SmallIntegerField(_('status'), choices=settings.QUOTE_STATUS_CHOICES)
    content = models.TextField(_('content'))
    items = generic.GenericRelation('Item')
    hourly_rate = models.DecimalField(_('hourly rate'),
                                      max_digits=6,
                                      decimal_places=2,
                                      default=settings.INVOICE_HOURLY_RATE)

    class Meta:
        verbose_name = _('quote')
        verbose_name_plural = _('quotes')

    def __unicode__(self):
        return '%s' % self.quote_id

    @property
    def total(self):
        """ Total amount """
        total = Decimal(0)
        for item in self.items.all():
            total += item.amount
        return total

    @property
    def quote_id(self):
        """ Unique quote ID """
        number = (settings.QUOTE_ID_LENGTH - len(str(self.id))) * "0" + str(self.id)
        return '%(prefix)s%(year)s%(unique_id)s' % {'prefix': settings.QUOTE_ID_PREFIX,
                                                    'year': self.date.strftime("%y"),
                                                    'unique_id': number}
    @property
    def exp_date(self):
        """ Expiration date of the quote """
        expiration_time = timedelta(days=31)
        return (self.date + expiration_time)

class Item(models.Model):
    """ Items of which a Quote or an Invoice exists. """
    date = models.DateField(_('date'), blank=True, null=True)
    description = models.CharField(_('description'), max_length=255)
    time = models.IntegerField(_('time in minutes'), blank=True, null=True)
    amount = models.DecimalField(_('amount'), max_digits=19, decimal_places=2)

    content_type = models.ForeignKey(ContentType, verbose_name=_('content type'))
    object_id = models.PositiveIntegerField(_('object id'), db_index=True)
    object = generic.GenericForeignKey('content_type', 'object_id')

    class Meta:
        verbose_name = _('item')
        verbose_name_plural = _('items')
        ordering = ['date']

    def __unicode__(self):
        return '%s' % self.description

########NEW FILE########
__FILENAME__ = monetize
from django import template

register = template.Library()

def beautify(val, sep):
    val = str(val)
    if val != ".": val = val.replace('.', sep)
    if val.find(sep) == -1: val = val + sep + "00"
    elif len(val.split(sep)[-1]) == 1: val = val + "0"
    return val

@register.filter(name="euro")
def euro(value):
    """ 
    Converts a number to humanized prices in euro. Thus replacing dots by
    comma's and making sure that there are always to decimals. 

    """
    return beautify(value, ',')

@register.filter(name="pound")
def pound(value):
    """ Same as above, but than pounds. """
    return beautify(value, '.') 

@register.filter(name="sek")
def sek(value):
    """ Same as above, but than sek. """
    return beautify(value, '.') 

########NEW FILE########
__FILENAME__ = tests
"""
This file demonstrates two different styles of tests (one doctest and one
unittest). These will both pass when you run "manage.py test".

Replace these with more appropriate tests for your application.
"""

from django.test import TestCase

class SimpleTest(TestCase):
    def test_basic_addition(self):
        """
        Tests that 1 + 1 always equals 2.
        """
        self.failUnlessEqual(1 + 1, 2)

__test__ = {"doctest": """
Another way to test that 1 + 1 is equal to 2.

>>> 1 + 1 == 2
True
"""}


########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import *

urlpatterns = patterns('brookie.views',
    url(r'^invoice/(?P<id>[\d]+)/pdf/$',
        'generate_invoice',
        name='generate-invoice'),

    url(r'^invoice/(?P<id>[\d]+)/download/$',
        'view_invoice',
        name='view-invoice'),

    url(r'^quote/(?P<id>[-\d]+)/pdf/$',
        'generate_quote',
        name='generate-quote'),

    url(r'^quote/(?P<id>[-\d]+)/invoice/$',
        'quote_to_invoice',
        name='quote-to-invoice'),
)

########NEW FILE########
__FILENAME__ = utils
from brookie.templatetags.monetize import euro, pound, sek

def decimal_to_string(value, currency):
    """ Convert value to currency string """
    if currency == 'euro':
        return euro(value)
    elif currency == 'gbp':
        return pound(value)
    return sek(value)

########NEW FILE########
__FILENAME__ = views
from django.http import HttpResponse, HttpResponseRedirect, Http404
from django.contrib.auth.decorators import user_passes_test
from django.template.loader import get_template
from django.template import Context
from django.shortcuts import get_object_or_404
from django.conf import settings
from django.core.urlresolvers import reverse

import ho.pisa as pisa
import cStringIO as StringIO
import cgi, os, datetime

from brookie.models import Invoice, Quote, Item
from brookie import brookie_settings as br_settings

def user_is_staff(user):
    """ Check if a user has the staff status """
    return user.is_authenticated() and user.is_staff

def fetch_resources(uri, rel):
    """
    Callback to allow pisa/reportlab to retrieve Images,Stylesheets, etc.
    `uri` is the href attribute from the html link element.
    `rel` gives a relative path, but it's not used here.

    """
    if 'django.contrib.staticfiles' in settings.INSTALLED_APPS:
        path = os.path.join(settings.STATIC_ROOT, uri.replace(settings.STATIC_URL, ""))
    else:
        path = os.path.join(settings.MEDIA_ROOT, uri.replace(settings.MEDIA_URL, ""))
    return path

def generate_pdf(filename, context_dict, template, save=False):
    """ Generates a invoice PDF in desired language """
    template = get_template(template)
    context = Context(context_dict)
    html  = template.render(context)
    # Insert page skips
    html = html.replace('-pageskip-', '<pdf:nextpage />')
    result = StringIO.StringIO()
    pdf = pisa.pisaDocument(StringIO.StringIO(
        html.encode("UTF-8")), result, link_callback=fetch_resources)
    if not pdf.err:
        if not save:
            response = HttpResponse(result.getvalue(), mimetype='application/pdf')
            response['Content-Disposition'] = 'attachment; filename=%s.pdf' % filename
            return response
        else:
            f = open(br_settings.BROOKIE_SAVE_PATH + '%s.pdf' % filename, 'w')
            f.write(result.getvalue())
            f.close()
            return True
            
    return http.HttpResponse('There was an error creating your PDF: %s' % cgi.escape(html))

@user_passes_test(user_is_staff)
def generate_invoice(request, id):
    """ Compile dictionary and generate pdf for invoice """
    invoice = get_object_or_404(Invoice, pk=id)

    context_dict = {'invoice': invoice,
                    'client': invoice.client,
                    'items': invoice.items.all(),}
    
    return generate_pdf(invoice.invoice_id, context_dict, "brookie/invoice_%s_pdf.html" % invoice.currency)

@user_passes_test(user_is_staff)
def view_invoice(request, id):
    """ Return the invoice """
    invoice = get_object_or_404(Invoice, pk=id)
    file_path = br_settings.BROOKIE_SAVE_PATH + '%s.pdf' % invoice.invoice_id
    
    if os.path.exists(file_path):
        f = open(file_path)

        response = HttpResponse(f.read(), mimetype='application/pdf')
        response['Content-Disposition'] = 'attachment; filename=%s.pdf' % invoice.invoice_id
        return response
    else: raise Http404
    
@user_passes_test(user_is_staff)
def generate_quote(request, id):
    """ Generate dictionary and generate pdf for quote """
    quote = get_object_or_404(Quote, pk=id)

    # Replace values in the quote
    quote.content = quote.content.replace('-company-', quote.client.company)
    
    context_dict = {'quote': quote,
                    'client': quote.client,
                    'items': quote.items.all(),}

    return generate_pdf(quote.quote_id, context_dict, "brookie/quote_pdf.html")

@user_passes_test(user_is_staff)
def quote_to_invoice(request, id):
    """ Copy a Quote to an Invoice and redirects """
    q = get_object_or_404(Quote, pk=id)
    i = Invoice(client=q.client,
                date=datetime.datetime.now(),
                currency='euro',
                status=1,
                hourly_rate=str(br_settings.INVOICE_HOURLY_RATE),)
    i.save()
    for item in q.items.all():
        new_item = Item(date=datetime.datetime.now(),
                        description=item.description,
                        time = item.time,
                        amount = item.amount,
                        object=i)
        new_item.save()
    return HttpResponseRedirect(reverse('admin:brookie_invoice_change', args=[i.id,]))

########NEW FILE########
__FILENAME__ = manage
#!/usr/bin/env python
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
import os, sys

abspath = lambda *p: os.path.abspath(os.path.join(*p))

PROJECT_ROOT = abspath(os.path.dirname(__file__))
BROOKIE_MODULE_PATH = abspath(PROJECT_ROOT, '..')
sys.path.insert(0, BROOKIE_MODULE_PATH)

DEBUG = True
TEMPLATE_DEBUG = DEBUG

ADMINS = (
    # ('Your Name', 'your_email@domain.com'),
)

MANAGERS = ADMINS

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': 'demo_project.db',
        'TEST_NAME': ':memory:',
    }
}

TIME_ZONE = 'America/Chicago'
LANGUAGE_CODE = 'en-us'

SITE_ID = 1

USE_I18N = True
USE_L10N = True

MEDIA_ROOT = abspath(PROJECT_ROOT, 'media')
MEDIA_URL = '/media/'
ADMIN_MEDIA_PREFIX = '/media/admin/'

SECRET_KEY = '2l0b5=y+3im#r4u$*^1p^z6st%u#)z5vg@i4ur-5axc+3^^p$3'

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

ROOT_URLCONF = 'demo_project.urls'

TEMPLATE_DIRS = (
    abspath(PROJECT_ROOT, 'templates')
)

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.messages',
    'django.contrib.admin',
    'django.contrib.admindocs',
    'brookie',
)

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import *
from django.conf import settings
from django.contrib import admin

admin.autodiscover()

urlpatterns = patterns('',
    (r'^brookie/', include('brookie.urls')),

    (r'^admin/doc/', include('django.contrib.admindocs.urls')),
    (r'^admin/', include(admin.site.urls)),
)

if settings.DEBUG:
    urlpatterns += patterns('',
        (r'^media/(?P<path>.*)$',
         'django.views.static.serve',
         {'document_root': settings.MEDIA_ROOT, 'show_indexes': True, }),
)


########NEW FILE########
