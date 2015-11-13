__FILENAME__ = abstract_mixin
#
# This work by Patryk Zawadzki is licensed under a Creative Commons
# Attribution-NonCommercial-ShareAlike 2.5 Poland.
#
# taken from:
# http://room-303.com/blog/2010/04/27/django-abstrakcji-ciag-dalszy/
# http://gist.github.com/584106
#

from django.db import models

class AbstractMixin(object):
	_classcache = {}

	@classmethod
	def contribute(cls):
		return {}

	@classmethod
	def construct(cls, *args, **kwargs):
		attrs = cls.contribute(*args, **kwargs)
		attrs.update({
			'__module__': cls.__module__,
			'Meta': type('Meta', (), {'abstract': True}),
		})
		key = (args, tuple(kwargs.items()))
		if not key in cls._classcache:
			clsname = ('%s%x' % (cls.__name__, hash(key))) \
					.replace('-', '_')
			cls._classcache[key] = type(clsname, (cls, ), attrs)
		return cls._classcache[key]

########NEW FILE########
__FILENAME__ = forms
import datetime
from ...forms import ConfirmationForm
from . import models

class DummyConfirmationForm(ConfirmationForm):
	def __init__(self, *args, **kwargs):
		super(DummyConfirmationForm, self).__init__(*args, **kwargs)
		# An example how payment backend could create additional models related to Payment:
		txn = models.DummyTxn.objects.create(
				payment=self.payment,
				comment="Dummy transaction created on %s" % datetime.datetime.now()
				)

########NEW FILE########
__FILENAME__ = models
from django.db import models

from mamona.abstract_mixin import AbstractMixin

class DummyTxnFactory(models.Model, AbstractMixin):
	comment = models.CharField(max_length=100, default="a dummy transaction")

	class Meta:
		abstract = True

	@classmethod
	def contribute(cls, payment):
		return {'payment': models.OneToOneField(payment)}

DummyTxn = None

def build_models(payment_class):
	global DummyTxn
	class DummyTxn(DummyTxnFactory.construct(payment_class)):
		pass
	return [DummyTxn]

########NEW FILE########
__FILENAME__ = processor
from datetime import datetime
from django.http import HttpResponseRedirect
from django.core.urlresolvers import reverse
from .forms import DummyConfirmationForm
from . import models

def get_confirmation_form(payment):
	return {'form': DummyConfirmationForm(payment=payment), 'method': 'get',
			'action': reverse('mamona-dummy-decide', kwargs={'payment_id': payment.id})}

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import *

urlpatterns = patterns('mamona.backends.dummy.views',
	url(r'^decide/(?P<payment_id>[0-9]+)/$', 'decide_success_or_failure', name='mamona-dummy-decide'),
	url(r'^success/(?P<payment_id>[0-9]+)/$', 'do_payment_success', name='mamona-dummy-do-success'),
	url(r'^failure/(?P<payment_id>[0-9]+)/$', 'do_payment_failure', name='mamona-dummy-do-failure'),
)

########NEW FILE########
__FILENAME__ = views
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404, render

from mamona.models import Payment
from models import DummyTxn

def decide_success_or_failure(request, payment_id):
	payment = get_object_or_404(Payment, id=payment_id, status='in_progress', backend='dummy')
	return render(
		request,
		'mamona/backends/dummy/decide.html',
		{'payment': payment}
		)

def do_payment_success(request, payment_id):
	payment = get_object_or_404(Payment, id=payment_id, status='in_progress', backend='dummy')
	return HttpResponseRedirect(payment.on_payment())

def do_payment_failure(request, payment_id):
	payment = get_object_or_404(Payment, id=payment_id, status='in_progress', backend='dummy')
	return HttpResponseRedirect(payment.on_failure())

########NEW FILE########
__FILENAME__ = forms
from django import forms
from django.contrib.sites.models import Site
from django.core.urlresolvers import reverse

from ...forms import ConfirmationForm
from ...utils import get_backend_settings

class PaypalConfirmationForm(ConfirmationForm):
	invoice = forms.IntegerField(widget=forms.HiddenInput())
	first_name = forms.CharField(required=False, widget=forms.HiddenInput())
	last_name = forms.CharField(required=False, widget=forms.HiddenInput())
	email = forms.EmailField(required=False, widget=forms.HiddenInput())
	city = forms.CharField(required=False, widget=forms.HiddenInput())
	zip = forms.CharField(required=False, widget=forms.HiddenInput())
	country = forms.CharField(required=False, widget=forms.HiddenInput())
	amount = forms.DecimalField(widget=forms.HiddenInput())
	currency_code = forms.CharField(widget=forms.HiddenInput())
	notify_url = forms.CharField(required=False, widget=forms.HiddenInput())
	business = forms.EmailField(widget=forms.HiddenInput())
	cmd = forms.CharField(widget=forms.HiddenInput(), initial='_cart')
	upload = forms.CharField(widget=forms.HiddenInput(), initial='1')
	charset = forms.CharField(widget=forms.HiddenInput(), initial='utf-8')

	def __init__(self, *args, **kwargs):
		super(PaypalConfirmationForm, self).__init__(*args, **kwargs)
		# a keyword, haha :)
		self.fields['return'] = forms.CharField(widget=forms.HiddenInput())
		paypal = get_backend_settings('paypal')
		customer = self.payment.get_customer_data()
		self.fields['invoice'].initial = self.payment.pk
		self.fields['first_name'].initial = customer.get('first_name', '')
		self.fields['last_name'].initial = customer.get('last_name', '')
		self.fields['email'].initial = customer.get('email', '')
		self.fields['city'].initial = customer.get('city', '')
		self.fields['country'].initial = customer.get('country_iso', '')
		self.fields['zip'].initial = customer.get('postal_code', '')
		self.fields['amount'].initial = self.payment.amount
		self.fields['currency_code'].initial = self.payment.currency
		self.fields['return'].initial = paypal['url']
		self.fields['business'].initial = paypal['email']
		i = 1
		for item in self.payment.get_items():
			self.fields['item_name_%d' % i] = forms.CharField(widget=forms.HiddenInput())
			self.fields['item_name_%d' % i].initial = item['name']
			self.fields['amount_%d' % i] = forms.DecimalField(widget=forms.HiddenInput())
			self.fields['amount_%d' % i].initial = item['unit_price']
			self.fields['quantity_%d' % i] = forms.DecimalField(widget=forms.HiddenInput())
			self.fields['quantity_%d' % i].initial = item['quantity']
			i += 1
		try:
			self.fields['return'].initial = paypal['return_url']
		except KeyError:
			# TODO: use https when needed
			self.fields['return'].initial = 'http://%s%s' % (
					Site.objects.get_current().domain,
					reverse('mamona-paypal-return', kwargs={'payment_id': self.payment.id})
					)
		self.fields['notify_url'].initial = 'http://%s%s' % (
				Site.objects.get_current().domain,
				reverse('mamona-paypal-ipn')
				)

	def clean(self, *args, **kwargs):
		raise NotImplementedError("This form is not intended to be validated here.")

########NEW FILE########
__FILENAME__ = models
def build_models(payment_class):
	return []

########NEW FILE########
__FILENAME__ = processor
from mamona.utils import get_backend_settings

from . import forms

def get_confirmation_form(payment):
	paypal = get_backend_settings('paypal')
	form = forms.PaypalConfirmationForm(payment=payment)
	return {'form': form, 'method': 'post', 'action': paypal['url']}

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import *

urlpatterns = patterns('mamona.backends.paypal.views',
	url(r'^return/(?P<payment_id>[0-9]+)/$', 'return_from_gw', name='mamona-paypal-return'),
	url(r'^ipn/$', 'ipn', name='mamona-paypal-ipn'),
)

########NEW FILE########
__FILENAME__ = views
from django.http import HttpResponse, HttpResponseRedirect, HttpResponseNotFound, HttpResponseBadRequest
from django.shortcuts import get_object_or_404, render
from django.views.decorators.csrf import csrf_exempt

from mamona.models import Payment
from mamona.utils import get_backend_settings
from mamona.signals import return_urls_query

import urllib2
from urllib import urlencode
from decimal import Decimal

def return_from_gw(request, payment_id):
	payment = get_object_or_404(Payment, id=payment_id)
	urls = {}
	return_urls_query.send(sender=None, instance=payment, urls=urls)
	if payment.status == 'failed':
		return HttpResponseRedirect(urls['failure'])
	elif payment.status == 'paid':
		return HttpResponseRedirect(urls['paid'])
	elif payment.status == 'partially_paid':
		try:
			return HttpResponseRedirect(urls['partially_paid'])
		except KeyError:
			return HttpResponseRedirect(urls['paid'])
	return render(
			request,
			'mamona/base_return.html',
			{'payment': payment}
			)

@csrf_exempt
def ipn(request):
	"""Instant Payment Notification callback.
	See https://cms.paypal.com/us/cgi-bin/?&cmd=_render-content&content_ID=developer/e_howto_admin_IPNIntro
	for details."""
	# TODO: add some logging here, as all the errors will occur silently
	try:
		payment = get_object_or_404(Payment, id=request.POST['invoice'],
				status__in=('in_progress', 'partially_paid', 'paid', 'failed'),
				backend='paypal')
	except (KeyError, ValueError):
		return HttpResponseBadRequest()
	charset = request.POST.get('charset', 'UTF-8')
	request.encoding = charset
	data = request.POST.dict()
	data['cmd'] = '_notify-validate'

	# Encode data as PayPal wants it.
	for k, v in data.items():
		data[k] = v.encode(charset)

	udata = urlencode(data)
	url = get_backend_settings('paypal')['url']
	r = urllib2.Request(url)
	r.add_header("Content-type", "application/x-www-form-urlencoded")
	h = urllib2.urlopen(r, udata)
	result = h.read()
	h.close()

	if result == "VERIFIED":
		# TODO: save foreign-id from data['txn_id']
		if payment.status == 'in_progress':
			amount = Decimal(request.POST['mc_gross'])
			# TODO: handle different IPN calls, e.g. refunds
			payment.on_payment(amount)
		return HttpResponse('OKTHXBAI')
	else:
		# XXX: marking the payment as failed would create a security hole
		return HttpResponseNotFound()

########NEW FILE########
__FILENAME__ = forms
from django import forms
from django.conf import settings
from django.utils.translation import ugettext as _
from models import Payment
from utils import get_backend_choices

class PaymentMethodForm(forms.Form):
	"""Shows choice field with all active payment backends. You may use it with
	existing Payment instance to push it through all the remaining logic, getting
	the link to the next payment step from proceed_to_gateway() method."""
	backend = forms.ChoiceField(
			choices=get_backend_choices(),
			label=_("Payment method"),
			)

	def __init__(self, *args, **kwargs):
		self.payment = kwargs.pop('payment', None)
		super(PaymentMethodForm, self).__init__(*args, **kwargs)

	def save(self, payment=None):
		if not payment:
			payment = self.payment
		payment.backend = self.cleaned_data['backend']
		payment.save()


class ConfirmationForm(forms.Form):
	def __init__(self, *args, **kwargs):
		self.payment = kwargs.pop('payment')
		super(forms.Form, self).__init__(*args, **kwargs)
		self.payment.change_status('in_progress')

########NEW FILE########
__FILENAME__ = models
from django.db import models
from django.conf import settings
from django.utils.translation import ugettext_lazy as _
from datetime import datetime
from abstract_mixin import AbstractMixin
import signals

PAYMENT_STATUS_CHOICES = (
		('new', _("New")),
		('in_progress', _("In progress")),
		('partially_paid', _("Partially paid")),
		('paid', _("Paid")),
		('failed', _("Failed")),
		)

class PaymentFactory(models.Model, AbstractMixin):
	amount = models.DecimalField(decimal_places=4, max_digits=20)
	currency = models.CharField(max_length=3)
	status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default='new')
	backend = models.CharField(max_length=30)
	created_on = models.DateTimeField(auto_now_add=True)
	paid_on = models.DateTimeField(blank=True, null=True, default=None)
	amount_paid = models.DecimalField(decimal_places=4, max_digits=20, default=0)

	class Meta:
		abstract = True

	def get_processor(self):
		ppath = 'mamona.backends.%s.processor' % self.backend
		try:
			return getattr(__import__(ppath).backends, self.backend).processor
		except None:#ImportError:
			raise ValueError("Backend '%s' is not available or provides no processor." % self.backend)

	def change_status(self, new_status):
		"""Always change payment's status via this method. Otherwise the signal
		will not be emitted."""
		old_status = self.status
		self.status = new_status
		self.save()
		signals.payment_status_changed.send(
				sender=type(self), instance=self,
				old_status=old_status, new_status=new_status
				)

	def on_payment(self, amount=None):
		"""Launched by backend when payment receives any new money. It defaults to
		complete payment, but can optionally accept received amount as a parameter
		to handle partial payments.
		"""
		self.paid_on = datetime.now()
		if amount:
			self.amount_paid = amount
		else:
			self.amount_paid = self.amount
		fully_paid = self.amount_paid >= self.amount
		if fully_paid:
			self.change_status('paid')
		else:
			self.change_status('partially_paid')
		urls = {}
		signals.return_urls_query.send(sender=type(self), instance=self, urls=urls)
		if not fully_paid:
			try:
				# Applications do NOT have to define 'partially_paid' URL.
				return urls['partially_paid']
			except KeyError:
				pass
		return urls['paid']

	def on_failure(self):
		"Launched by backend when payment fails."
		self.change_status('failed')
		urls = {}
		signals.return_urls_query.send(sender=type(self), instance=self, urls=urls)
		return urls['failure']

	def get_items(self):
		"""Retrieves item list using signal query. Listeners must fill
		'items' list with at least one item. Each item is expected to be
		a dictionary, containing at least 'name' element and optionally
		'unit_price' and 'quantity' elements. If not present, 'unit_price'
		and 'quantity' default to 0 and 1 respectively.

		Listener is responsible for providing item list with sum of prices
		consistient with Payment.amount. Otherwise the final amount may
		differ and lead to unpredictable results, depending on the backend used.
		"""
		items = []
		signals.order_items_query.send(sender=type(self), instance=self, items=items)
		# XXX: sanitization and filling with defaults - do we need it? may be costly.
		if len(items) == 1 and not items[0].has_key('unit_price'):
			items[0]['unit_price'] = self.amount
			return items
		for item in items:
			assert item.has_key('name')
			if not item.has_key('unit_price'):
				item['unit_price'] = 0
			if not item.has_key('quantity'):
				item['quantity'] = 1
		return items

	def get_customer_data(self):
		"""Retrieves customer data. The default empty dictionary is
		already the minimal implementation.
		"""
		customer = {}
		signals.customer_data_query.send(sender=type(self), instance=self, customer=customer)
		return customer

	@classmethod
	def contribute(cls, order, **kwargs):
		return {'order': models.ForeignKey(order, **kwargs)}

	def __unicode__(self):
		return u"%s payment of %s%s%s for %s" % (
				self.get_status_display(),
				self.amount,
				self.currency,
				u" on %s" % self.paid_on if self.status == 'paid' else "",
				self.order
				)

from django.db.models.loading import cache as app_cache
from utils import import_backend_modules
def build_payment_model(order_class, **kwargs):
	global Payment
	global Order
	class Payment(PaymentFactory.construct(order=order_class, **kwargs)):
		pass
	Order = order_class
	bknd_models_modules = import_backend_modules('models')
	for bknd_name, models in bknd_models_modules.items():
		app_cache.register_models(bknd_name, *models.build_models(Payment))
	return Payment

def payment_from_order(order):
	"""Builds payment based on given Order instance."""
	payment = Payment()
	signals.order_to_payment_query.send(sender=None, order=order, payment=payment)
	return payment

########NEW FILE########
__FILENAME__ = signals
from django.dispatch import Signal

payment_status_changed = Signal(providing_args=['old_status', 'new_status'])
payment_status_changed.__doc__ = """
Sent when Payment status changes.
	old_status:	str
	new_status:	str
"""

order_items_query = Signal(providing_args=['items'])
order_items_query.__doc__ = """
Sent to ask for order's items.
	items:			list
Listeners must fill the items list with at least one item.
Each item must be a dict instance, with at least 'name' element defined.
Other accepted keys are 'quantity' and 'unit_price' which default to 1 and 0
respectively.
"""

customer_data_query = Signal(providing_args=['customer'])
customer_data_query.__doc__ = """
Sent to ask for customer's data.
	customer:		dict
Handling of this signal will depend on the gateways you want to enable.
Currently, with PayPal, it doesn't have to be answered at all.
The optional arguments accepted by paypal backend are:
first_name, last_name, email, city, postal_code, country_iso
"""

return_urls_query = Signal(providing_args=['urls'])
return_urls_query.__doc__ = """
Sent to ask for URLs to return from payment gateway.
	urls:			dict
Listeners must fill urls with at least two elements: 'paid' and 'failure',
which represent the URLs to return after paid and failed payment respectively.
The optional element 'partially_paid' is used to return after payment which
received incomplete amount.
"""

order_to_payment_query = Signal(providing_args=['order', 'payment'])
order_to_payment_query.__doc__ = """
Sent to ask for filling Payment object with order data:
	order:			order instance
	payment:		Payment instance
It needs to be answered only if you don't create Payment by yourself and let
Mamona do it (e.g. by using mamona.views.process_order).
It must fill mandatory Payment fields: order and amount.
"""

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import *
from utils import import_backend_modules

includes_list = []
for bknd_name, urls in import_backend_modules('urls').items():
	includes_list.append(url(r'^%s/' % bknd_name, include(urls)))

urlpatterns = patterns('mamona',
		url('^order/$', 'views.process_order', name='mamona-process-order'),
		url('^payment/(?P<payment_id>[0-9]+)$', 'views.process_payment', name='mamona-process-payment'),
		url('^confirm/(?P<payment_id>[0-9]+)$', 'views.confirm_payment', name='mamona-confirm-payment'),
		*includes_list
		)

########NEW FILE########
__FILENAME__ = utils
from django.conf import settings

def get_active_backends():
	try:
		return settings.MAMONA_ACTIVE_BACKENDS
	except AttributeError:
		return ()

def import_backend_modules(submodule=''):
	try:
		backends = settings.MAMONA_ACTIVE_BACKENDS
	except AttributeError:
		backends = []
	modules = {}
	for backend_name in backends:
		fqmn = 'mamona.backends.%s' % backend_name
		if submodule:
			fqmn = '%s.%s' % (fqmn, submodule)
		mamona = __import__(fqmn)
		if submodule:
			module = getattr(getattr(mamona.backends, backend_name), submodule)
		else:
			module = getattr(mamona.backends, backend_name)
		modules[backend_name] = module
	return modules

def get_backend_choices():
	choices = []
	backends = import_backend_modules()
	for name, module in backends.items():
		choices.append((name, module.BACKEND_NAME))
	return choices

def get_backend_settings(backend):
	try:
		return settings.MAMONA_BACKENDS_SETTINGS[backend]
	except (AttributeError, KeyError):
		return {}

########NEW FILE########
__FILENAME__ = views
from django.conf import settings
from django.http import HttpResponseNotFound, HttpResponseRedirect
from django.core.urlresolvers import reverse
from django.shortcuts import get_object_or_404, render

from models import Payment, Order, payment_from_order
from forms import PaymentMethodForm
from urllib import urlencode
from urlparse import urlunparse

def process_order(request):
	"""This view should receive 'order_id' via POST, and optionally 'backend' too.
	It will use a signal to ask for filling in the payment details."""
	try:
		order = Order.objects.get(pk=request.POST['order_id'])
	except (Order.DoesNotExist, KeyError):
		return HttpResponseNotFound()
	payment = payment_from_order(order)
	payment.save()
	data = {}
	try:
		data['backend'] = request.POST['backend']
	except KeyError:
		pass
	url = reverse('mamona-process-payment', kwargs={'payment_id': payment.id})
	url = urlunparse((None, None, url, None, urlencode(data), None))
	return HttpResponseRedirect(url)

def process_payment(request, payment_id):
	"""This view processes the specified payment. It checks for backend, validates
	it's availability and asks again for it if something is wrong."""
	payment = get_object_or_404(Payment, id=payment_id, status='new')
	if request.method == 'POST' or request.REQUEST.has_key('backend'):
		data = request.REQUEST
	elif len(settings.MAMONA_ACTIVE_BACKENDS) == 1:
		data = {'backend': settings.MAMONA_ACTIVE_BACKENDS[0]}
	else:
		data = None
	bknd_form = PaymentMethodForm(data=data, payment=payment)
	if bknd_form.is_valid():
		bknd_form.save()
		return HttpResponseRedirect(
				reverse('mamona-confirm-payment', kwargs={'payment_id': payment.id}))
	return render(
			request,
			'mamona/select_payment_method.html',
			{'payment': payment, 'form': bknd_form},
			)

def confirm_payment(request, payment_id):
	payment = get_object_or_404(Payment, id=payment_id, status='new')
	formdata = payment.get_processor().get_confirmation_form(payment)
	return render(request, 'mamona/confirm.html',
			{'formdata': formdata, 'payment': payment})

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
__FILENAME__ = models
# -*- coding: utf-8 -*-
from django.db import models
from django.core.urlresolvers import reverse

from decimal import Decimal

class UnawareOrder(models.Model):
	"""This is an example of order model, which is unaware of
	Mamona existence.
	"""
	total = models.DecimalField(decimal_places=2, max_digits=8, default=0)
	currency = models.CharField(max_length=3, default='EUR')
	status = models.CharField(
			max_length=1,
			choices=(('s','success'), ('f','failure'), ('p', 'incomplete')),
			blank=True,
			default=''
			)

	def name(self):
		if self.item_set.count() == 0:
			return u"Empty order"
		elif self.item_set.count() == 1:
			return self.item_set.all()[0].name
		else:
			return u"Multiple-item order"

	def recalculate_total(self):
		total = Decimal('0')
		for item in self.item_set.all():
			total += item.price
		self.total = total
		self.save()

class Item(models.Model):
	"""Basic order item.
	"""
	order = models.ForeignKey(UnawareOrder)
	name = models.CharField(max_length=20)
	price = models.DecimalField(decimal_places=2, max_digits=8)

	def __unicode__(self):
		return self.name

def recalculate_total(sender, instance, **kwargs):
	instance.order.recalculate_total()
models.signals.post_save.connect(recalculate_total, sender=Item)

########NEW FILE########
__FILENAME__ = views
from django.shortcuts import get_object_or_404
from django.views.generic.simple import direct_to_template

from models import UnawareOrder

def show_order(request, order_id):
	order = get_object_or_404(UnawareOrder, id=order_id)
	return direct_to_template(
			request,
			'order/show_order.html',
			{'order': order}
			)

########NEW FILE########
__FILENAME__ = forms
from django import forms
from django.forms.models import inlineformset_factory
from order.models import UnawareOrder, Item

class ItemForm(forms.ModelForm):
	class Meta:
		model = Item
		fields = ('name', 'price')

ItemFormSet = inlineformset_factory(UnawareOrder, Item, form=ItemForm, extra=5, max_num=5)

########NEW FILE########
__FILENAME__ = listeners
from django.core.urlresolvers import reverse
from django.contrib.sites.models import Site
from mamona import signals

def return_urls_query_listener(sender, instance=None, urls=None, **kwargs):
	url = 'http://%s%s' % (
			Site.objects.get_current().domain,
			reverse('show-order', kwargs={'order_id': instance.order.id})
			)
	urls.update({'paid': url, 'failure': url})

def order_items_query_listener(sender, instance=None, items=None, **kwargs):
	for item in instance.order.item_set.all():
		items.append({'name': item.name, 'unit_price': item.price})

def payment_status_changed_listener(sender, instance=None, old_status=None, new_status=None, **kwargs):
	if new_status == 'paid':
		instance.order.status = 's'
		instance.order.save()
	elif new_status == 'failed':
		instance.order.status = 'f'
		instance.order.save()
	elif new_status == 'partially_paid':
		instance.order.status = 'p'
		instance.order.save()

def order_to_payment_listener(sender, order=None, payment=None, **kwargs):
	payment.order = order
	payment.amount = order.total
	payment.currency = order.currency

signals.payment_status_changed.connect(payment_status_changed_listener)
signals.order_items_query.connect(order_items_query_listener)
signals.return_urls_query.connect(return_urls_query_listener)
signals.order_to_payment_query.connect(order_to_payment_listener)

########NEW FILE########
__FILENAME__ = models
from django.db import models
from order.models import UnawareOrder
from mamona.models import build_payment_model

# We build the final Payment model here, in external app,
# without touching the code containing UnawareObject.
build_payment_model(UnawareOrder, unique=False, related_name='payments')
import listeners

########NEW FILE########
__FILENAME__ = tests
from django.test import TestCase
from django.core.urlresolvers import reverse
from django.contrib.sites.models import Site
from order.models import UnawareOrder
from mamona.models import Payment

from decimal import Decimal
from random import randint

class SimpleTest(TestCase):
	fixtures = ['site']

	def setUp(self):
		self.o1 = UnawareOrder.objects.create(total=Decimal("25.12"))
		i = 1
		while i <= randint(1,10):
			self.o1.item_set.create(
					name="Item %s" % i,
					price=Decimal(randint(1,100))/Decimal("100")
					)
			i += 1
		self.o2 = UnawareOrder.objects.create(total=Decimal("0.01"))
		i = 1
		while i <= randint(1,10):
			self.o2.item_set.create(
					name="Item %s" % i,
					price=Decimal(randint(1,100))/Decimal("100")
					)
			i += 1
		self.o3 = UnawareOrder.objects.create(total=Decimal("0.01"))
		i = 1
		while i <= randint(1,10):
			self.o3.item_set.create(
					name="Item %s" % i,
					price=Decimal(randint(1,100))/Decimal("100")
					)
			i += 1

	def test_payment_creation(self):
		self.o1.payments.create(amount=self.o1.total)
		self.o2.payments.create(amount=self.o2.total)

	def test_payment_success_and_failure(self):
		p1 = self.o1.payments.create(amount=self.o1.total)
		p2 = self.o2.payments.create(amount=self.o2.total)
		p3 = self.o3.payments.create(amount=self.o2.total)
		p1.on_payment()
		self.assertEqual(p1.status, 'paid')
		self.assertEqual(self.o1.status, 's')
		p2.on_payment(p2.amount - Decimal('0.01'))
		self.assertEqual(p2.status, 'partially_paid')
		self.assertEqual(self.o2.status, 'p')
		p3.on_failure()
		self.assertEqual(p3.status, 'failed')
		self.assertEqual(self.o3.status, 'f')

	def test_dummy_backend(self):
		p1 = self.o1.payments.create(amount=self.o1.total)
		# request without backend should give us a form
		response = self.client.post(
				reverse('mamona-process-payment', kwargs={'payment_id': p1.id}),
				follow=True
				)
		self.assertEqual(response.status_code, 200)
		# this should succeed
		response = self.client.post(
				reverse('mamona-process-payment', kwargs={'payment_id': p1.id}),
				{'backend': 'dummy'},
				follow=True
				)
		p1 = Payment.objects.get(id=p1.id)
		self.assertEqual(p1.status, 'in_progress')
		# calling again should fail with 404, as the payment is marked 'in_progress'
		response = self.client.post(
				reverse('mamona-process-payment', kwargs={'payment_id': p1.id}),
				{'backend': 'dummy'},
				follow=True
				)
		self.assertEqual(response.status_code, 404)
		# choose success
		response = self.client.get(
				reverse('mamona-dummy-do-success', kwargs={'payment_id': p1.id}),
				follow=True
				)
		p1 = Payment.objects.get(id=p1.id)
		self.assertEqual(p1.status, 'paid')
		self.assertEqual(
				p1.amount,
				sum(map(lambda i: i.price, self.o1.item_set.all()))
				)
		# re-processing should fail
		response = self.client.post(
				reverse('mamona-process-payment', kwargs={'payment_id': p1.id}),
				{'backend': 'dummy'},
				follow=True
				)
		self.assertEqual(response.status_code, 404)
		# dummy backend should have created it's own model instance
		self.assertEqual(p1.dummytxn.payment_id, p1.id)

		p2 = self.o2.payments.create(amount=self.o2.total)
		# this should fail with 404
		response = self.client.get(
				reverse('mamona-dummy-do-success', kwargs={'payment_id': p2.id}),
				follow=True
				)
		self.assertEqual(response.status_code, 404)
		response = self.client.post(
				reverse('mamona-process-payment', kwargs={'payment_id': p2.id}),
				{'backend': 'dummy'},
				follow=True
				)
		response = self.client.get(
				reverse('mamona-dummy-do-failure', kwargs={'payment_id': p2.id}),
				follow=True
				)
		p2 = Payment.objects.get(id=p2.id)
		self.assertEqual(p2.status, 'failed')
		self.assertEqual(
				p2.amount,
				sum(map(lambda i: i.price, self.o2.item_set.all()))
				)

########NEW FILE########
__FILENAME__ = views
from django.http import HttpResponseRedirect
from django.core.urlresolvers import reverse
from django.views.generic.simple import direct_to_template

from mamona.forms import PaymentMethodForm
from order.models import UnawareOrder
from forms import ItemFormSet

import random

def order_singleitem(request):
	# approach 1: single item purchase with predefined backend
	order = UnawareOrder.objects.create()
	order.item_set.create(
			name=u"Donation for Mamona author",
			price=random.random() * 8 + 2
			)
	return direct_to_template(
			request,
			'sales/order_singleitem.html',
			{'order': order, 'backend': 'paypal'}
			)

def order_multiitem(request):
	# approach 2: an order with no payment method (Mamona will ask)
	order = UnawareOrder()
	if request.method == 'POST':
		formset = ItemFormSet(instance=order, data=request.POST)
		if formset.is_valid():
			order.save()
			formset.save()
			payment = order.payments.create(amount=order.total, currency=order.currency)
			return HttpResponseRedirect(
					reverse('mamona-process-payment', kwargs={'payment_id': payment.id})
					)
	else:
		formset = ItemFormSet(instance=order)
	return direct_to_template(
		request,
		'sales/order_multiitem.html',
		{'order': order, 'formset': formset}
		)

def order_singlescreen(request):
	# approach 3: single screen (ask for everything)
	order = UnawareOrder()
	payment_form = PaymentMethodForm(data=request.POST or None)
	formset = ItemFormSet(instance=order, data=request.POST or None)
	if request.method == 'POST':
		if formset.is_valid() and payment_form.is_valid():
			order.save()
			formset.save()
			payment = order.payments.create(amount=order.total, currency=order.currency)
			payment_form.save(payment)
			return HttpResponseRedirect(
					reverse('mamona-confirm-payment', kwargs={'payment_id': payment.id}))
	return direct_to_template(
		request,
		'sales/order_singlescreen.html',
		{'order': order, 'formset': formset, 'payment_form': payment_form}
		)

########NEW FILE########
__FILENAME__ = settings
# -*- coding: utf-8 -*-
import os

PROJECT_ROOT = os.path.dirname(__file__)

DEBUG = True
TEMPLATE_DEBUG = DEBUG

ADMINS = (
	# ('Your Name', 'your_email@domain.com'),
)

MANAGERS = ADMINS

DATABASES = {
		'default': {
			'ENGINE': 'django.db.backends.sqlite3',
			'NAME': 'test-project.db',
			}
		}

# Local time zone for this installation. Choices can be found here:
# http://en.wikipedia.org/wiki/List_of_tz_zones_by_name
# although not all choices may be available on all operating systems.
# If running in a Windows environment this must be set to the same as your
# system time zone.
TIME_ZONE = 'Europe/Warsaw'

# Language code for this installation. All choices can be found here:
# http://www.i18nguy.com/unicode/language-identifiers.html
LANGUAGE_CODE = 'en-us'

SITE_ID = 2

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
SECRET_KEY = 'hdaw2jet30@z0sm+zl$y_+8vrem2-mih5)(e^d@ng8@6m6wfth'

# List of callables that know how to import templates from various sources.
TEMPLATE_LOADERS = (
	'django.template.loaders.filesystem.Loader',
	'django.template.loaders.app_directories.Loader',
#	 'django.template.loaders.eggs.Loader',
)

MIDDLEWARE_CLASSES = (
	'django.middleware.common.CommonMiddleware',
	'django.contrib.sessions.middleware.SessionMiddleware',
	'django.contrib.auth.middleware.AuthenticationMiddleware',
)

ROOT_URLCONF = 'urls'

TEMPLATE_DIRS = (
	# Put strings here, like "/home/html/django_templates" or "C:/www/django/templates".
	# Always use forward slashes, even on Windows.
	# Don't forget to use absolute paths, not relative paths.
)

INSTALLED_APPS = (
#	'django.contrib.auth',
	'django.contrib.contenttypes',
	'django.contrib.sessions',
	'django.contrib.sites',
	'mamona',
	'mamona.backends.dummy',
	'mamona.backends.paypal',
	'order',
	'sales',
)

MAMONA_ACTIVE_BACKENDS = (
	'dummy',
	'paypal',
)
MAMONA_BACKENDS_SETTINGS = {
	'paypal': {
		'url': 'https://www.paypal.com/cgi-bin/webscr',			# real payments URL
#		'url': 'https://www.sandbox.paypal.com/cgi-bin/webscr',	# test payments URL
#		'return_url': 'http://www.example.com/success/',		# global override
		'email': 'michal.salaban@gmail.com',
	},
}

try:
	execfile(os.path.join(PROJECT_ROOT, 'local_settings.py'))
except IOError:
	pass

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import *

urlpatterns = patterns('',
	(r'^mamona/', include('mamona.urls')),
	url(r'^$', 'sales.views.order_singleitem', name='sales-order-singleitem'),
	url(r'^multiitem$', 'sales.views.order_multiitem', name='sales-order-multiitem'),
	url(r'^singlescreen$', 'sales.views.order_singlescreen', name='sales-order-singlescreen'),
	url(r'^details/(?P<order_id>[0-9]+)/$', 'order.views.show_order', name='show-order'),
)

########NEW FILE########
