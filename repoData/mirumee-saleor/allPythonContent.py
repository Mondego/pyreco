__FILENAME__ = manage
#!/usr/bin/env python
import os
import sys

if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "saleor.settings")

    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)

########NEW FILE########
__FILENAME__ = forms
from __future__ import unicode_literals

from django import forms
from django.core.exceptions import ObjectDoesNotExist, NON_FIELD_ERRORS
from django.forms.formsets import BaseFormSet, DEFAULT_MAX_NUM
from django.utils.translation import pgettext_lazy, ugettext_lazy
from satchless.item import InsufficientStock


class QuantityField(forms.IntegerField):

    def __init__(self, *args, **kwargs):
        super(QuantityField, self).__init__(min_value=0, max_value=999,
                                            initial=1)


class AddToCartForm(forms.Form):
    """
    Class use product and cart instance.
    """
    quantity = QuantityField(label=pgettext_lazy('Form field', 'Quantity'))
    error_messages = {
        'empty-stock': ugettext_lazy(
            'Sorry. This product is currently out of stock.'
        ),
        'variant-does-not-exists': ugettext_lazy(
            'Oops. We could not find that product.'
        ),
        'insufficient-stock': ugettext_lazy(
            'Only %(remaining)d remaining in stock.'
        )
    }

    def __init__(self, *args, **kwargs):
        self.cart = kwargs.pop('cart')
        self.product = kwargs.pop('product')
        super(AddToCartForm, self).__init__(*args, **kwargs)

    def clean(self):
        cleaned_data = super(AddToCartForm, self).clean()
        quantity = cleaned_data.get('quantity')
        if quantity is None:
            return cleaned_data
        try:
            product_variant = self.get_variant(cleaned_data)
        except ObjectDoesNotExist:
            msg = self.error_messages['variant-does-not-exists']
            self.add_error(NON_FIELD_ERRORS, msg)
        else:
            cart_line = self.cart.get_line(product_variant)
            used_quantity = cart_line.quantity if cart_line else 0
            new_quantity = quantity + used_quantity
            try:
                self.cart.check_quantity(
                    product_variant, new_quantity, None)
            except InsufficientStock as e:
                remaining = e.item.stock - used_quantity
                if remaining:
                    msg = self.error_messages['insufficient-stock']
                else:
                    msg = self.error_messages['empty-stock']
                self.add_error('quantity', msg % {'remaining': remaining})
        return cleaned_data

    def save(self):
        """
        Adds CartLine into the Cart instance.
        """
        product_variant = self.get_variant(self.cleaned_data)
        return self.cart.add(product_variant, self.cleaned_data['quantity'])

    def get_variant(self, cleaned_data):
        raise NotImplementedError()

    def add_error(self, name, value):
        errors = self.errors.setdefault(name, self.error_class())
        errors.append(value)


class ReplaceCartLineForm(AddToCartForm):
    """
    Replaces quantity in CartLine.
    """
    def __init__(self, *args, **kwargs):
        super(ReplaceCartLineForm, self).__init__(*args, **kwargs)
        self.cart_line = self.cart.get_line(self.product)

    def clean_quantity(self):
        quantity = self.cleaned_data['quantity']
        try:
            self.cart.check_quantity(self.product, quantity, None)
        except InsufficientStock as e:
            msg = self.error_messages['insufficient-stock']
            raise forms.ValidationError(msg % {'remaining': e.item.stock})
        return quantity

    def clean(self):
        return super(AddToCartForm, self).clean()

    def get_variant(self, cleaned_data):
        """In cart formset product is already variant"""
        return self.product

    def save(self):
        """
        Replace quantity.
        """
        return self.cart.add(self.product, self.cleaned_data['quantity'],
                             replace=True)


class ReplaceCartLineFormSet(BaseFormSet):
    """
    Formset for all CartLines in the cart instance.
    """
    absolute_max = 9999
    can_delete = False
    can_order = False
    extra = 0
    form = ReplaceCartLineForm
    max_num = DEFAULT_MAX_NUM
    validate_max = False
    min_num = None
    validate_min = False

    def __init__(self, *args, **kwargs):
        self.cart = kwargs.pop('cart')
        kwargs['initial'] = [{'quantity': cart_line.get_quantity()}
                             for cart_line in self.cart
                             if cart_line.get_quantity()]
        super(ReplaceCartLineFormSet, self).__init__(*args, **kwargs)

    def _construct_form(self, i, **kwargs):
        kwargs['cart'] = self.cart
        kwargs['product'] = self.cart[i].product
        return super(ReplaceCartLineFormSet, self)._construct_form(i, **kwargs)

    def save(self):
        for form in self.forms:
            form.save()

########NEW FILE########
__FILENAME__ = middleware
from __future__ import unicode_literals

from . import SessionCart, CART_SESSION_KEY


class CartMiddleware(object):
    '''
    Saves the cart instance into the django session.
    '''

    def process_request(self, request):
        try:
            cart_data = request.session[CART_SESSION_KEY]
            cart = SessionCart.from_storage(cart_data)
        except KeyError:
            cart = SessionCart()
        setattr(request, 'cart', cart)

    def process_response(self, request, response):
        if hasattr(request, 'cart') and request.cart.modified:
            request.cart.modified = False
            to_session = request.cart.for_storage()
            request.session[CART_SESSION_KEY] = to_session
        return response

########NEW FILE########
__FILENAME__ = models
# -*- coding: utf-8 -*-

########NEW FILE########
__FILENAME__ = tests
from __future__ import unicode_literals
from decimal import Decimal

from django.test import TestCase
from django.utils.encoding import smart_text
from mock import MagicMock
from prices import Price
from satchless.item import InsufficientStock

from . import Cart, SessionCart
from .forms import AddToCartForm, ReplaceCartLineForm, ReplaceCartLineFormSet
from ..product.models import (ProductVariant, StockedProduct, PhysicalProduct)

__all__ = ['CartTest', 'BigShipCartFormTest']


class BigShip(ProductVariant, StockedProduct, PhysicalProduct):

    def get_price_per_item(self, discounted=True, **kwargs):
        return self.price

    def get_slug(self):
        return 'bigship'


class ShipPhoto(ProductVariant, PhysicalProduct):

    def get_slug(self):
        return 'bigship-photo'


class BigShipCartForm(AddToCartForm):

    def get_variant(self, cleaned_data):
        return self.product

stock_product = BigShip(name='BigShip',
                        stock=10, price=Price(10, currency='USD'),
                        weight=Decimal(123))
stock_product.product = stock_product
digital_product = ShipPhoto(price=Price(10, currency='USD'))
digital_product.product = digital_product


class CartTest(TestCase):

    def test_check_quantity(self):
        """
        Stock limit works
        """
        cart = Cart(session_cart=MagicMock())

        def illegal():
            cart.add(stock_product, 100)

        self.assertRaises(InsufficientStock, illegal)
        self.assertFalse(cart)

    def test_add_adds_to_session_cart(self):
        cart = Cart(session_cart=SessionCart())
        cart.add(stock_product, 10)
        self.assertEqual(cart.session_cart.count(), 10)
        self.assertTrue(cart.session_cart.modified)
        self.assertEqual(cart.session_cart[0].product,
                         smart_text(stock_product))


class BigShipCartFormTest(TestCase):

    def setUp(self):
        self.cart = Cart(MagicMock())
        self.post = {'quantity': 5}

    def test_quantity(self):
        """
        BigShipCartForm works with correct quantity value on empty cart
        """
        form = BigShipCartForm(
            self.post, cart=self.cart, product=stock_product)
        self.assertTrue(form.is_valid())
        self.assertFalse(self.cart)
        form.save()
        product_quantity = self.cart.get_line(stock_product).quantity
        self.assertEqual(product_quantity, 5, 'Bad quantity')

    def test_max_quantity(self):
        """
        BigShipCartForm works with correct product stock value
        """
        form = BigShipCartForm(
            self.post, cart=self.cart, product=stock_product)
        self.assertTrue(form.is_valid())
        form.save()
        form = BigShipCartForm(
            self.post, cart=self.cart, product=stock_product)
        self.assertTrue(form.is_valid())
        form.save()
        product_quantity = self.cart.get_line(stock_product).quantity
        self.assertEqual(product_quantity, 10,
                         '%s is the bad quantity value' % (product_quantity,))

    def test_too_big_quantity(self):
        """
        BigShipCartForm works with not correct quantity value'
        """
        form = BigShipCartForm({'quantity': 15}, cart=self.cart,
                               product=stock_product)
        self.assertFalse(form.is_valid())
        self.assertFalse(self.cart)

    def test_clean_quantity_product(self):
        """
        Is BigShipCartForm works with not stocked product
        """
        cart = Cart(session_cart=MagicMock())
        self.post['quantity'] = 999
        form = BigShipCartForm(self.post, cart=cart, product=digital_product)
        self.assertTrue(form.is_valid(), 'Form doesn\'t valitate')
        self.assertFalse(cart, 'Cart isn\'t empty')
        form.save()
        self.assertTrue(cart, 'Cart is empty')


class ReplaceCartLineFormTest(TestCase):

    def setUp(self):
        self.cart = Cart(session_cart=MagicMock())

    def test_quantity(self):
        """
        ReplaceCartLineForm works with correct quantity value
        """
        form = ReplaceCartLineForm({'quantity': 5}, cart=self.cart,
                                   product=stock_product)
        self.assertTrue(form.is_valid())
        form.save()
        form = ReplaceCartLineForm({'quantity': 5}, cart=self.cart,
                                   product=stock_product)
        self.assertTrue(form.is_valid())
        form.save()
        product_quantity = self.cart.get_line(stock_product).quantity
        self.assertEqual(product_quantity, 5,
                         '%s is the bad quantity value' % (product_quantity,))

    def test_too_big_quantity(self):
        """
        Is ReplaceCartLineForm works with to big quantity value
        """
        form = ReplaceCartLineForm({'quantity': 15}, cart=self.cart,
                                   product=stock_product)
        self.assertFalse(form.is_valid())


class ReplaceCartLineFormSetTest(TestCase):

    def test_save(self):
        post = {
            'form-TOTAL_FORMS': 2,
            'form-INITIAL_FORMS': 2,
            'form-0-quantity': 5,
            'form-1-quantity': 5}
        cart = Cart(session_cart=MagicMock())
        cart.add(stock_product, 5)
        cart.add(digital_product, 100)
        form = ReplaceCartLineFormSet(post, cart=cart)
        self.assertTrue(form.is_valid())
        form.save()
        product_quantity = cart.get_line(stock_product).quantity
        self.assertEqual(product_quantity, 5,
                         '%s is the bad quantity value' % (product_quantity,))


class SessionCartTest(TestCase):

    def test_sessioncart_get_price_per_item(self):
        cart = Cart(SessionCart())
        cart.add(stock_product, quantity=10)
        cart_price = cart[0].get_price_per_item()
        sessioncart_price = cart.session_cart[0].get_price_per_item()
        self.assertTrue(isinstance(sessioncart_price, Price))
        self.assertEqual(cart_price, sessioncart_price)


########NEW FILE########
__FILENAME__ = urls
from django.conf.urls import patterns, url

from . import views


urlpatterns = patterns(
    '',
    url(r'^$', views.index, name='index')
)

########NEW FILE########
__FILENAME__ = views
from __future__ import unicode_literals

from django.contrib import messages
from django.shortcuts import redirect
from django.template.response import TemplateResponse
from django.utils.translation import ugettext as _
from satchless.item import Partitioner

from .forms import ReplaceCartLineFormSet
from . import Cart


def index(request):
    cart = Cart.for_session_cart(request.cart, discounts=request.discounts)
    cart_partitioner = Partitioner(cart)
    formset = ReplaceCartLineFormSet(request.POST or None,
                                     cart=cart)
    if formset.is_valid():
        msg = _('Successfully updated product quantities.')
        messages.success(request, msg)
        formset.save()
        return redirect('cart:index')
    return TemplateResponse(
        request, 'cart/index.html', {
            'cart': cart_partitioner,
            'formset': formset})

########NEW FILE########
__FILENAME__ = forms
from django import forms
from django.contrib.auth.models import AnonymousUser
from django.utils.translation import ugettext_lazy as _

from ..order.models import DigitalDeliveryGroup
from ..userprofile.forms import AddressForm


class ShippingForm(AddressForm):

    use_billing = forms.BooleanField(initial=True)


class DigitalDeliveryForm(forms.ModelForm):

    class Meta:
        model = DigitalDeliveryGroup
        fields = ['email']

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None) or AnonymousUser()
        super(DigitalDeliveryForm, self).__init__(*args, **kwargs)
        email = self.fields['email']
        email.required = True
        if user.is_authenticated():
            email.initial = user.email


class DeliveryForm(forms.Form):

    method = forms.ChoiceField(label=_('Shipping method'))

    def __init__(self, delivery_choices, *args, **kwargs):
        super(DeliveryForm, self).__init__(*args, **kwargs)
        method_field = self.fields['method']
        method_field.choices = delivery_choices
        if len(delivery_choices) == 1:
            method_field.initial = delivery_choices[0][1]
            method_field.widget = forms.HiddenInput()


class AnonymousEmailForm(forms.Form):

    email = forms.EmailField()

########NEW FILE########
__FILENAME__ = models

########NEW FILE########
__FILENAME__ = steps
from __future__ import unicode_literals

from django.core.exceptions import ValidationError
from django.db import models
from django.db import transaction
from django.shortcuts import redirect
from django.utils.encoding import smart_text
from django.utils.translation import ugettext_lazy as _
from satchless.process import InvalidData

from .forms import DigitalDeliveryForm, DeliveryForm
from ..checkout.forms import AnonymousEmailForm
from ..core.utils import BaseStep
from ..delivery import get_delivery_choices_for_group
from ..order.models import DigitalDeliveryGroup, ShippedDeliveryGroup
from ..userprofile.forms import AddressForm
from ..userprofile.models import Address, User


class BaseCheckoutStep(BaseStep):

    def __init__(self, request, storage):
        super(BaseCheckoutStep, self).__init__(request)
        self.storage = storage

    @models.permalink
    def get_absolute_url(self):
        return ('checkout:details', (), {'step': str(self)})

    def add_to_order(self, order):
        raise NotImplementedError()


class BaseAddressStep(BaseCheckoutStep):

    template = 'checkout/address.html'

    def __init__(self, request, storage, address):
        super(BaseAddressStep, self).__init__(request, storage)
        self.address = address
        existing_selected = False
        address_form = AddressForm(request.POST or None, instance=self.address)
        if request.user.is_authenticated():
            address_book = list(request.user.address_book.all())
            for entry in address_book:
                data = Address.objects.as_data(entry.address)
                instance = Address(**data)
                entry.form = AddressForm(instance=instance)
                entry.is_selected = Address.objects.are_identical(
                    entry.address, self.address)
                if entry.is_selected:
                    existing_selected = True
        else:
            address_book = []
        self.existing_selected = existing_selected
        self.forms = {'address': address_form}
        self.address_book = address_book

    def forms_are_valid(self):
        address_form = self.forms['address']
        return address_form.is_valid()

    def validate(self):
        try:
            self.address.clean_fields()
        except ValidationError as e:
            raise InvalidData(e.messages)

    def process(self, extra_context=None):
        context = dict(extra_context or {})
        context['form'] = self.forms['address']
        context['address_book'] = self.address_book
        context['existing_address_selected'] = self.existing_selected
        return super(BaseAddressStep, self).process(extra_context=context)


class BillingAddressStep(BaseAddressStep):

    template = 'checkout/billing.html'
    title = _('Billing Address')

    def __init__(self, request, storage):
        address_data = storage.get('address', {})
        address = Address(**address_data)
        skip = False
        if not address_data and request.user.is_authenticated():
            if request.user.default_billing_address:
                address = request.user.default_billing_address.address
                skip = True
            elif request.user.address_book.count() == 1:
                address = request.user.address_book.all()[0].address
                skip = True
        super(BillingAddressStep, self).__init__(request, storage, address)
        if not request.user.is_authenticated():
            self.anonymous_user_email = self.storage.get(
                'anonymous_user_email')
            initial = {'email': self.anonymous_user_email}
            self.forms['anonymous'] = AnonymousEmailForm(request.POST or None,
                                                         initial=initial)
        else:
            self.anonymous_user_email = ''
        if skip:
            self.save()

    def __str__(self):
        return 'billing-address'

    def forms_are_valid(self):
        forms_are_valid = super(BillingAddressStep, self).forms_are_valid()
        if 'anonymous' not in self.forms:
            return forms_are_valid
        anonymous_form = self.forms['anonymous']
        if forms_are_valid and anonymous_form.is_valid():
            self.anonymous_user_email = anonymous_form.cleaned_data['email']
            return True
        return False

    def save(self):
        self.storage['anonymous_user_email'] = self.anonymous_user_email
        self.storage['address'] = Address.objects.as_data(self.address)

    def add_to_order(self, order):
        self.address.save()
        order.anonymous_user_email = self.anonymous_user_email
        order.billing_address = self.address
        order.save()
        if order.user:
            alias = '%s, %s' % (order, self)
            User.objects.store_address(order.user, self.address, alias,
                                       billing=True)

    def validate(self):
        super(BillingAddressStep, self).validate()
        if 'anonymous' in self.forms and not self.anonymous_user_email:
            raise InvalidData()


class ShippingStep(BaseAddressStep):

    template = 'checkout/shipping.html'
    title = _('Shipping Details')

    def __init__(self, request, storage, purchased_items, _id=None,
                 default_address=None):
        self.id = _id
        address_data = storage.get('address', {})
        if not address_data and default_address:
            address = default_address
        else:
            address = Address(**address_data)
        super(ShippingStep, self).__init__(request, storage, address)
        delivery_choices = list(
            get_delivery_choices_for_group(purchased_items, address=address))
        selected_delivery_name = storage.get('delivery_method')
        # TODO: find cheapest not first
        (selected_delivery_group_name,
         selected_delivery_group) = delivery_choices[0]
        for delivery_name, delivery in delivery_choices:
            if delivery_name == selected_delivery_name:
                selected_delivery_group = delivery
                selected_delivery_group_name = delivery_name
                break
        self.group = selected_delivery_group
        self.forms['delivery'] = DeliveryForm(
            delivery_choices, request.POST or None,
            initial={'method': selected_delivery_group_name})

    def __str__(self):
        return 'delivery-%s' % (self.id,)

    def save(self):
        delivery_form = self.forms['delivery']
        self.storage['address'] = Address.objects.as_data(self.address)
        delivery_method = delivery_form.cleaned_data['method']
        self.storage['delivery_method'] = delivery_method

    def validate(self):
        super(ShippingStep, self).validate()
        if 'delivery_method' not in self.storage:
            raise InvalidData()

    def forms_are_valid(self):
        base_forms_are_valid = super(ShippingStep, self).forms_are_valid()
        delivery_form = self.forms['delivery']
        if base_forms_are_valid and delivery_form.is_valid():
            return True
        return False

    def add_to_order(self, order):
        self.address.save()
        group = ShippedDeliveryGroup.objects.create(
            order=order, address=self.address,
            price=self.group.get_delivery_total(),
            method=smart_text(self.group))
        group.add_items_from_partition(self.group)
        if order.user:
            alias = '%s, %s' % (order, self)
            User.objects.store_address(order.user, self.address, alias,
                                       shipping=True)

    def process(self, extra_context=None):
        context = dict(extra_context or {})
        context['items'] = self.group
        context['delivery_form'] = self.forms['delivery']
        return super(ShippingStep, self).process(extra_context=context)


class DigitalDeliveryStep(BaseCheckoutStep):

    template = 'checkout/digitaldelivery.html'
    title = _('Digital Delivery')

    def __init__(self, request, storage, items_group=None, _id=None):
        super(DigitalDeliveryStep, self).__init__(request, storage)
        self.id = _id
        self.forms['email'] = DigitalDeliveryForm(request.POST or None,
                                                  initial=self.storage,
                                                  user=request.user)
        email = self.storage.get('email')
        delivery_choices = list(
            get_delivery_choices_for_group(items_group, email=email))
        selected_delivery_group = delivery_choices[0][1]
        self.storage['delivery_method'] = selected_delivery_group
        self.group = selected_delivery_group

    def __str__(self):
        return 'digital-delivery-%s' % (self.id,)

    def validate(self):
        if not 'email' in self.storage:
            raise InvalidData()

    def save(self):
        self.storage.update(self.forms['email'].cleaned_data)

    def add_to_order(self, order):
        group = DigitalDeliveryGroup.objects.create(
            order=order, email=self.storage['email'],
            price=self.group.get_delivery_total(),
            method=smart_text(self.group))
        group.add_items_from_partition(self.group)

    def process(self, extra_context=None):
        context = dict(extra_context or {})
        context['form'] = self.forms['email']
        context['items'] = self.group
        return super(DigitalDeliveryStep, self).process(extra_context=context)


class SummaryStep(BaseCheckoutStep):

    template = 'checkout/summary.html'
    title = _('Summary')

    def __init__(self, request, storage, checkout):
        self.checkout = checkout
        super(SummaryStep, self).__init__(request, storage)

    def __str__(self):
        return 'summary'

    def process(self, extra_context=None):
        context = dict(extra_context or {})
        context['all_steps_valid'] = self.forms_are_valid()
        response = super(SummaryStep, self).process(context)
        if not response:
            with transaction.atomic():
                order = self.checkout.create_order()
                order.send_confirmation_email()
            return redirect('order:details', token=order.token)
        return response

    def validate(self):
        raise InvalidData()

    def forms_are_valid(self):
        next_step = self.checkout.get_next_step()
        return next_step == self

    def save(self):
        pass

    def add_to_order(self, _order):
        self.checkout.clear_storage()

########NEW FILE########
__FILENAME__ = tests
from django.test import TestCase
from mock import MagicMock, patch

from . import BillingAddressStep, ShippingStep
from ..checkout import Checkout, STORAGE_SESSION_KEY
from ..checkout.steps import BaseAddressStep
from ..userprofile.models import Address

NEW_ADDRESS = {
    'name': 'Test',
    'street_address': 'Test',
    'city': 'Test',
    'phone': '12345678',
    'postal_code': '987654',
    'country': 'PL'
}


class TestBaseAddressStep(TestCase):

    def test_new_method(self):
        '''
        Test the BaseAddressStep managment form when method is set to 'new'
        and user isn't authenticated.
        '''
        request = MagicMock()
        request.user.is_authenticated.return_value = False
        request.POST = NEW_ADDRESS.copy()
        step = BaseAddressStep(request, {}, Address(**NEW_ADDRESS))
        self.assertTrue(step.forms_are_valid(), "Forms don't validate.")
        self.assertEqual(step.address.name, 'Test')


class TestBillingAddressStep(TestCase):

    def test_address_save_without_address(self):
        request = MagicMock()
        request.user.is_authenticated.return_value = False
        request.POST = dict(NEW_ADDRESS, email='test@example.com')
        storage = {}
        step = BillingAddressStep(request, storage)
        self.assertEquals(step.process(), None)
        self.assertEqual(type(storage['address']), dict)
        self.assertEqual(storage['address']['name'], 'Test')

    def test_address_save_with_address_in_checkout(self):
        request = MagicMock()
        request.user.is_authenticated.return_value = False
        request.POST = dict(NEW_ADDRESS, email='test@example.com')
        storage = {'address': {}}
        step = BillingAddressStep(request, storage)
        self.assertTrue(step.forms_are_valid(), "Forms don't validate.")


class TestShippingStep(TestCase):

    @patch.object(Address, 'save')
    def test_address_save_without_address(self, mock_save):
        request = MagicMock()
        request.user.is_authenticated.return_value = False
        request.session = {}
        request.POST = dict(NEW_ADDRESS, method='dummy_shipping')
        request.session = {STORAGE_SESSION_KEY: {}}
        group = MagicMock()
        group.address = None
        storage = {'address': NEW_ADDRESS}
        step = ShippingStep(request, storage, group)
        self.assertTrue(step.forms_are_valid(), "Forms don't validate.")
        step.save()
        self.assertEqual(mock_save.call_count, 0)
        self.assertTrue(isinstance(storage['address'], dict),
                        'dict expected')

    @patch.object(Address, 'save')
    def test_address_save_with_address_in_group(self, mock_save):
        request = MagicMock()
        request.user.is_authenticated.return_value = False
        request.session = {}
        request.POST = dict(NEW_ADDRESS, method='dummy_shipping')
        group = MagicMock()
        group.address = NEW_ADDRESS
        storage = {'address': NEW_ADDRESS}
        step = ShippingStep(request, storage, group)
        self.assertTrue(step.forms_are_valid(), "Forms don't validate.")
        step.save()
        self.assertEqual(mock_save.call_count, 0)

    @patch.object(Address, 'save')
    def test_address_save_with_address_in_checkout(self, mock_save):
        request = MagicMock()
        request.user.is_authenticated.return_value = False
        request.session = {}
        request.POST = dict(NEW_ADDRESS, method='dummy_shipping')
        original_billing_address = {'name': 'Change Me', 'id': 10}
        group = MagicMock()
        group.address = None
        storage = {'address': original_billing_address}
        step = ShippingStep(request, storage, group)
        self.assertTrue(step.forms_are_valid(), "Forms don't validate.")
        step.save()
        self.assertEqual(mock_save.call_count, 0)
        self.assertEqual(storage['address'], NEW_ADDRESS)

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls import patterns, url

from . import views


urlpatterns = patterns(
    '',
    url(r'^$', views.details, kwargs={'step': None}, name='index'),
    url(r'^(?P<step>[a-z0-9-]+)/$', views.details, name='details')
)

########NEW FILE########
__FILENAME__ = views
from django.http.response import Http404
from django.shortcuts import redirect

from . import Checkout


def details(request, step):
    if not request.cart:
        return redirect('cart:index')
    checkout = Checkout(request)
    if not step:
        return redirect(checkout.get_next_step())
    try:
        step = checkout[step]
    except KeyError:
        raise Http404()
    response = step.process(extra_context={'checkout': checkout})
    if not response:
        checkout.save()
        return redirect(checkout.get_next_step())
    return response

########NEW FILE########
__FILENAME__ = mail
from django.conf import settings
from django.core.mail.message import EmailMultiAlternatives
from django.template import Context
from django.template.loader import get_template
from django.template.loader_tags import BlockNode

BLOCKS = [SUBJECT, TEXT, HTML] = 'subject', 'text', 'html'  # template blocks


def send_email(address, template_name, context=None):
    """Renders template blocks and sends an email."""
    blocks = render_blocks(template_name=template_name, context=context or {})
    message = EmailMultiAlternatives(
        subject=blocks[SUBJECT],
        body=blocks[TEXT],
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[address])
    if HTML in blocks:
        message.attach_alternative(blocks[HTML], 'text/html')
    message.send()


def render_blocks(template_name, context):
    """Renders BLOCKS from template. Block needs to be a top level node."""
    context = Context(context)
    template = get_template(template_name=template_name)
    return dict((node.name, node.render(context)) for node in template
                if isinstance(node, BlockNode) and node.name in BLOCKS)

########NEW FILE########
__FILENAME__ = tests
from unittest import TestCase

from django.template.loader_tags import BlockNode
from mock import Mock, patch, sentinel

from .mail import SUBJECT, TEXT, HTML, send_email, render_blocks


class SendEmailTestCase(TestCase):

    def setUp(self):
        patcher = patch('saleor.communication.mail.settings')
        self.settings_mock = patcher.start()
        patcher = patch('saleor.communication.mail.render_blocks')
        self.render_mock = patcher.start()
        patcher = patch('saleor.communication.mail.EmailMultiAlternatives')
        self.email_mock = patcher.start()

        self.settings_mock.DEFAULT_FROM_EMAIL = sentinel.from_email

    def test_sending_email_without_html(self):
        """Html content is not attached when html block is missing"""
        self.render_mock.return_value = {SUBJECT: sentinel.subject,
                                         TEXT: sentinel.text}
        send_email(address=sentinel.address,
                   template_name=sentinel.template_name,
                   context=sentinel.context)
        self.assert_email_constructed()
        self.email_mock().send.assert_called_once()

    def test_sending_email_with_html(self):
        """Html content is attached when html block present"""
        self.render_mock.return_value = {SUBJECT: sentinel.subject,
                                         TEXT: sentinel.text,
                                         HTML: sentinel.html}
        send_email(address=sentinel.address,
                   template_name=sentinel.template_name,
                   context=sentinel.context)
        self.assert_email_constructed()
        self.email_mock().attach_alternative.assert_called_once_with(
            sentinel.html, 'text/html')
        self.email_mock().send.assert_called_once()

    def assert_email_constructed(self):
        self.email_mock.assert_called_once_with(
            subject=sentinel.subject,
            body=sentinel.text,
            from_email=sentinel.from_email,
            to=[sentinel.address])

    def tearDown(self):
        patch.stopall()


class RenderBlocksTestCase(TestCase):

    @patch('saleor.communication.mail.get_template')
    @patch('saleor.communication.mail.Context')
    def test_block_rendering(self, context_mock, get_template_mock):
        """Template blocks are rendered with proper context"""
        html_block = Mock(spec=BlockNode)
        html_block.name = HTML
        some_block = Mock(spec=BlockNode)
        some_block.name = 'some_block'
        non_block = Mock()
        get_template_mock.return_value = [html_block, some_block, non_block]
        blocks = render_blocks(template_name=sentinel.template_name,
                               context=sentinel.context)
        context_mock.assert_called_once_with(sentinel.context)
        html_block.render.assert_called_once_with(context_mock())
        some_block.render.assert_not_called()
        non_block.render.assert_not_called()
        self.assertEquals(blocks, {HTML: html_block.render()})

########NEW FILE########
__FILENAME__ = analytics
import uuid

from django.conf import settings
import google_measurement_protocol as ga

FINGERPRINT_PARTS = [
    'HTTP_ACCEPT_ENCODING',
    'HTTP_ACCEPT_LANGUAGE',
    'HTTP_USER_AGENT',
    'HTTP_X_FORWARDED_FOR',
    'REMOTE_ADDR']

UUID_NAMESPACE = uuid.UUID('fb4abc05-e2fb-4e3e-8b78-28037ef7d07f')


def get_client_id(request):
    parts = [request.META.get(key, '') for key in FINGERPRINT_PARTS]
    return uuid.uuid5(UUID_NAMESPACE, '_'.join(parts))


def _report(client_id, what, extra_info=None, extra_headers=None):
    tracking_id = getattr(settings, 'GOOGLE_ANALYTICS_TRACKING_ID', None)
    if tracking_id and client_id:
        ga.report(tracking_id, client_id, what, extra_info=extra_info,
                  extra_headers=extra_headers)


def report_view(client_id, path, language, headers):
    host_name = headers.get('HTTP_HOST', None)
    referrer = headers.get('HTTP_REFERER', None)
    pv = ga.PageView(path, host_name=host_name, referrer=referrer)
    extra_info = ga.SystemInfo(language=language)
    extra_headers = {}
    user_agent = headers.get('HTTP_USER_AGENT', None)
    if user_agent:
        extra_headers['user-agent'] = user_agent
    _report(client_id, pv, extra_info=extra_info, extra_headers=extra_headers)


def report_order(client_id, order):
    for group in order:
        items = [ga.Item(oi.product_name,
                         oi.get_price_per_item(),
                         quantity=oi.quantity,
                         item_id=oi.product_sku)
                 for oi in group]
        trans = ga.Transaction('%s-%s' % (order.id, group.id), items,
                               revenue=group.get_total(), shipping=group.price)
        _report(client_id, trans, {})

########NEW FILE########
__FILENAME__ = context_processors
from django.conf import settings


def get_setting_as_dict(name, short_name=None):
    short_name = short_name or name
    try:
        return {short_name: getattr(settings, name)}
    except AttributeError:
        return {}


def canonical_hostname(request):
    return get_setting_as_dict('CANONICAL_HOSTNAME')


def default_currency(request):
    return get_setting_as_dict('DEFAULT_CURRENCY')

########NEW FILE########
__FILENAME__ = countries
#coding: utf-8

from __future__ import unicode_literals

from django.utils.translation import pgettext_lazy

COUNTRY_CHOICES = [
    ('AF', pgettext_lazy('Country', 'Afghanistan')),
    ('AX', pgettext_lazy('Country', 'Åland Islands')),
    ('AL', pgettext_lazy('Country', 'Albania')),
    ('DZ', pgettext_lazy('Country', 'Algeria')),
    ('AS', pgettext_lazy('Country', 'American Samoa')),
    ('AD', pgettext_lazy('Country', 'Andorra')),
    ('AO', pgettext_lazy('Country', 'Angola')),
    ('AI', pgettext_lazy('Country', 'Anguilla')),
    ('AQ', pgettext_lazy('Country', 'Antarctica')),
    ('AG', pgettext_lazy('Country', 'Antigua And Barbuda')),
    ('AR', pgettext_lazy('Country', 'Argentina')),
    ('AM', pgettext_lazy('Country', 'Armenia')),
    ('AW', pgettext_lazy('Country', 'Aruba')),
    ('AU', pgettext_lazy('Country', 'Australia')),
    ('AT', pgettext_lazy('Country', 'Austria')),
    ('AZ', pgettext_lazy('Country', 'Azerbaijan')),
    ('BS', pgettext_lazy('Country', 'Bahamas')),
    ('BH', pgettext_lazy('Country', 'Bahrain')),
    ('BD', pgettext_lazy('Country', 'Bangladesh')),
    ('BB', pgettext_lazy('Country', 'Barbados')),
    ('BY', pgettext_lazy('Country', 'Belarus')),
    ('BE', pgettext_lazy('Country', 'Belgium')),
    ('BZ', pgettext_lazy('Country', 'Belize')),
    ('BJ', pgettext_lazy('Country', 'Benin')),
    ('BM', pgettext_lazy('Country', 'Bermuda')),
    ('BT', pgettext_lazy('Country', 'Bhutan')),
    ('BO', pgettext_lazy('Country', 'Bolivia')),
    ('BQ', pgettext_lazy('Country', 'Bonaire, Saint Eustatius And Saba')),
    ('BA', pgettext_lazy('Country', 'Bosnia And Herzegovina')),
    ('BW', pgettext_lazy('Country', 'Botswana')),
    ('BV', pgettext_lazy('Country', 'Bouvet Island')),
    ('BR', pgettext_lazy('Country', 'Brazil')),
    ('IO', pgettext_lazy('Country', 'British Indian Ocean Territory')),
    ('BN', pgettext_lazy('Country', 'Brunei Darussalam')),
    ('BG', pgettext_lazy('Country', 'Bulgaria')),
    ('BF', pgettext_lazy('Country', 'Burkina Faso')),
    ('BI', pgettext_lazy('Country', 'Burundi')),
    ('KH', pgettext_lazy('Country', 'Cambodia')),
    ('CM', pgettext_lazy('Country', 'Cameroon')),
    ('CA', pgettext_lazy('Country', 'Canada')),
    ('CV', pgettext_lazy('Country', 'Cape Verde')),
    ('KY', pgettext_lazy('Country', 'Cayman Islands')),
    ('CF', pgettext_lazy('Country', 'Central African Republic')),
    ('TD', pgettext_lazy('Country', 'Chad')),
    ('CL', pgettext_lazy('Country', 'Chile')),
    ('CN', pgettext_lazy('Country', 'China')),
    ('CX', pgettext_lazy('Country', 'Christmas Island')),
    ('CC', pgettext_lazy('Country', 'Cocos (Keeling) Islands')),
    ('CO', pgettext_lazy('Country', 'Colombia')),
    ('KM', pgettext_lazy('Country', 'Comoros')),
    ('CG', pgettext_lazy('Country', 'Congo')),
    ('CD', pgettext_lazy('Country', 'Congo, The Democratic Republic of the')),
    ('CK', pgettext_lazy('Country', 'Cook Islands')),
    ('CR', pgettext_lazy('Country', 'Costa Rica')),
    ('CI', pgettext_lazy('Country', 'Côte D\'Ivoire')),
    ('HR', pgettext_lazy('Country', 'Croatia')),
    ('CU', pgettext_lazy('Country', 'Cuba')),
    ('CW', pgettext_lazy('Country', 'Curaço')),
    ('CY', pgettext_lazy('Country', 'Cyprus')),
    ('CZ', pgettext_lazy('Country', 'Czech Republic')),
    ('DK', pgettext_lazy('Country', 'Denmark')),
    ('DJ', pgettext_lazy('Country', 'Djibouti')),
    ('DM', pgettext_lazy('Country', 'Dominica')),
    ('DO', pgettext_lazy('Country', 'Dominican Republic')),
    ('EC', pgettext_lazy('Country', 'Ecuador')),
    ('EG', pgettext_lazy('Country', 'Egypt')),
    ('SV', pgettext_lazy('Country', 'El Salvador')),
    ('GQ', pgettext_lazy('Country', 'Equatorial Guinea')),
    ('ER', pgettext_lazy('Country', 'Eritrea')),
    ('EE', pgettext_lazy('Country', 'Estonia')),
    ('ET', pgettext_lazy('Country', 'Ethiopia')),
    ('FK', pgettext_lazy('Country', 'Falkland Islands (Malvinas)')),
    ('FO', pgettext_lazy('Country', 'Faroe Islands')),
    ('FJ', pgettext_lazy('Country', 'Fiji')),
    ('FI', pgettext_lazy('Country', 'Finland')),
    ('FR', pgettext_lazy('Country', 'France')),
    ('GF', pgettext_lazy('Country', 'French Guiana')),
    ('PF', pgettext_lazy('Country', 'French Polynesia')),
    ('TF', pgettext_lazy('Country', 'French Southern Territories')),
    ('GA', pgettext_lazy('Country', 'Gabon')),
    ('GM', pgettext_lazy('Country', 'Gambia')),
    ('GE', pgettext_lazy('Country', 'Georgia')),
    ('DE', pgettext_lazy('Country', 'Germany')),
    ('GH', pgettext_lazy('Country', 'Ghana')),
    ('GI', pgettext_lazy('Country', 'Gibraltar')),
    ('GR', pgettext_lazy('Country', 'Greece')),
    ('GL', pgettext_lazy('Country', 'Greenland')),
    ('GD', pgettext_lazy('Country', 'Grenada')),
    ('GP', pgettext_lazy('Country', 'Guadeloupe')),
    ('GU', pgettext_lazy('Country', 'Guam')),
    ('GT', pgettext_lazy('Country', 'Guatemala')),
    ('GG', pgettext_lazy('Country', 'Guernsey')),
    ('GN', pgettext_lazy('Country', 'Guinea')),
    ('GW', pgettext_lazy('Country', 'Guinea-Bissau')),
    ('GY', pgettext_lazy('Country', 'Guyana')),
    ('HT', pgettext_lazy('Country', 'Haiti')),
    ('HM', pgettext_lazy('Country', 'Heard Island And Mcdonald Islands')),
    ('VA', pgettext_lazy('Country', 'Holy See (Vatican City State)')),
    ('HN', pgettext_lazy('Country', 'Honduras')),
    ('HK', pgettext_lazy('Country', 'Hong Kong')),
    ('HU', pgettext_lazy('Country', 'Hungary')),
    ('IS', pgettext_lazy('Country', 'Iceland')),
    ('IN', pgettext_lazy('Country', 'India')),
    ('ID', pgettext_lazy('Country', 'Indonesia')),
    ('IR', pgettext_lazy('Country', 'Iran, Islamic Republic of')),
    ('IQ', pgettext_lazy('Country', 'Iraq')),
    ('IE', pgettext_lazy('Country', 'Ireland')),
    ('IM', pgettext_lazy('Country', 'Isle of Man')),
    ('IL', pgettext_lazy('Country', 'Israel')),
    ('IT', pgettext_lazy('Country', 'Italy')),
    ('JM', pgettext_lazy('Country', 'Jamaica')),
    ('JP', pgettext_lazy('Country', 'Japan')),
    ('JE', pgettext_lazy('Country', 'Jersey')),
    ('JO', pgettext_lazy('Country', 'Jordan')),
    ('KZ', pgettext_lazy('Country', 'Kazakhstan')),
    ('KE', pgettext_lazy('Country', 'Kenya')),
    ('KI', pgettext_lazy('Country', 'Kiribati')),
    ('KP', pgettext_lazy('Country', 'Korea, Democratic People\'s Republic of')),
    ('KR', pgettext_lazy('Country', 'Korea, Republic of')),
    ('KW', pgettext_lazy('Country', 'Kuwait')),
    ('KG', pgettext_lazy('Country', 'Kyrgyzstan')),
    ('LA', pgettext_lazy('Country', 'Lao People\'s Democratic Republic')),
    ('LV', pgettext_lazy('Country', 'Latvia')),
    ('LB', pgettext_lazy('Country', 'Lebanon')),
    ('LS', pgettext_lazy('Country', 'Lesotho')),
    ('LR', pgettext_lazy('Country', 'Liberia')),
    ('LY', pgettext_lazy('Country', 'Libya')),
    ('LI', pgettext_lazy('Country', 'Liechtenstein')),
    ('LT', pgettext_lazy('Country', 'Lithuania')),
    ('LU', pgettext_lazy('Country', 'Luxembourg')),
    ('MO', pgettext_lazy('Country', 'Macao')),
    ('MK', pgettext_lazy('Country', 'Macedonia, The Former Yugoslav Republic of')),
    ('MG', pgettext_lazy('Country', 'Madagascar')),
    ('MW', pgettext_lazy('Country', 'Malawi')),
    ('MY', pgettext_lazy('Country', 'Malaysia')),
    ('MV', pgettext_lazy('Country', 'Maldives')),
    ('ML', pgettext_lazy('Country', 'Mali')),
    ('MT', pgettext_lazy('Country', 'Malta')),
    ('MH', pgettext_lazy('Country', 'Marshall Islands')),
    ('MQ', pgettext_lazy('Country', 'Martinique')),
    ('MR', pgettext_lazy('Country', 'Mauritania')),
    ('MU', pgettext_lazy('Country', 'Mauritius')),
    ('YT', pgettext_lazy('Country', 'Mayotte')),
    ('MX', pgettext_lazy('Country', 'Mexico')),
    ('FM', pgettext_lazy('Country', 'Micronesia, Federated States of')),
    ('MD', pgettext_lazy('Country', 'Moldova, Republic of')),
    ('MC', pgettext_lazy('Country', 'Monaco')),
    ('MN', pgettext_lazy('Country', 'Mongolia')),
    ('ME', pgettext_lazy('Country', 'Montenegro')),
    ('MS', pgettext_lazy('Country', 'Montserrat')),
    ('MA', pgettext_lazy('Country', 'Morocco')),
    ('MZ', pgettext_lazy('Country', 'Mozambique')),
    ('MM', pgettext_lazy('Country', 'Myanmar')),
    ('NA', pgettext_lazy('Country', 'Namibia')),
    ('NR', pgettext_lazy('Country', 'Nauru')),
    ('NP', pgettext_lazy('Country', 'Nepal')),
    ('NL', pgettext_lazy('Country', 'Netherlands')),
    ('NC', pgettext_lazy('Country', 'New Caledonia')),
    ('NZ', pgettext_lazy('Country', 'New Zealand')),
    ('NI', pgettext_lazy('Country', 'Nicaragua')),
    ('NE', pgettext_lazy('Country', 'Niger')),
    ('NG', pgettext_lazy('Country', 'Nigeria')),
    ('NU', pgettext_lazy('Country', 'Niue')),
    ('NF', pgettext_lazy('Country', 'Norfolk Island')),
    ('MP', pgettext_lazy('Country', 'Northern Mariana Islands')),
    ('NO', pgettext_lazy('Country', 'Norway')),
    ('OM', pgettext_lazy('Country', 'Oman')),
    ('PK', pgettext_lazy('Country', 'Pakistan')),
    ('PW', pgettext_lazy('Country', 'Palau')),
    ('PS', pgettext_lazy('Country', 'Palestinian Territory, Occupied')),
    ('PA', pgettext_lazy('Country', 'Panama')),
    ('PG', pgettext_lazy('Country', 'Papua New Guinea')),
    ('PY', pgettext_lazy('Country', 'Paraguay')),
    ('PE', pgettext_lazy('Country', 'Peru')),
    ('PH', pgettext_lazy('Country', 'Philippines')),
    ('PN', pgettext_lazy('Country', 'Pitcairn')),
    ('PL', pgettext_lazy('Country', 'Poland')),
    ('PT', pgettext_lazy('Country', 'Portugal')),
    ('PR', pgettext_lazy('Country', 'Puerto Rico')),
    ('QA', pgettext_lazy('Country', 'Qatar')),
    ('RE', pgettext_lazy('Country', 'Réunion')),
    ('RO', pgettext_lazy('Country', 'Romania')),
    ('RU', pgettext_lazy('Country', 'Russian Federation')),
    ('RW', pgettext_lazy('Country', 'Rwanda')),
    ('BL', pgettext_lazy('Country', 'Saint Barthélemy')),
    ('SH', pgettext_lazy('Country', 'Saint Helena, Ascension And Tristan Da Cunha')),
    ('KN', pgettext_lazy('Country', 'Saint Kitts And Nevis')),
    ('LC', pgettext_lazy('Country', 'Saint Lucia')),
    ('MF', pgettext_lazy('Country', 'Saint Martin (French Part)')),
    ('PM', pgettext_lazy('Country', 'Saint Pierre And Miquelon')),
    ('VC', pgettext_lazy('Country', 'Saint Vincent And the Grenadines')),
    ('WS', pgettext_lazy('Country', 'Samoa')),
    ('SM', pgettext_lazy('Country', 'San Marino')),
    ('ST', pgettext_lazy('Country', 'Sao Tome And Principe')),
    ('SA', pgettext_lazy('Country', 'Saudi Arabia')),
    ('SN', pgettext_lazy('Country', 'Senegal')),
    ('RS', pgettext_lazy('Country', 'Serbia')),
    ('SC', pgettext_lazy('Country', 'Seychelles')),
    ('SL', pgettext_lazy('Country', 'Sierra Leone')),
    ('SG', pgettext_lazy('Country', 'Singapore')),
    ('SX', pgettext_lazy('Country', 'Sint Maarten (Dutch Part)')),
    ('SK', pgettext_lazy('Country', 'Slovakia')),
    ('SI', pgettext_lazy('Country', 'Slovenia')),
    ('SB', pgettext_lazy('Country', 'Solomon Islands')),
    ('SO', pgettext_lazy('Country', 'Somalia')),
    ('ZA', pgettext_lazy('Country', 'South Africa')),
    ('GS', pgettext_lazy('Country', 'South Georgia and the South Sandwich Islands')),
    ('ES', pgettext_lazy('Country', 'Spain')),
    ('LK', pgettext_lazy('Country', 'Sri Lanka')),
    ('SD', pgettext_lazy('Country', 'Sudan')),
    ('SR', pgettext_lazy('Country', 'Suriname')),
    ('SJ', pgettext_lazy('Country', 'Svalbard and Jan Mayen')),
    ('SZ', pgettext_lazy('Country', 'Swaziland')),
    ('SE', pgettext_lazy('Country', 'Sweden')),
    ('CH', pgettext_lazy('Country', 'Switzerland')),
    ('SY', pgettext_lazy('Country', 'Syria')),
    ('TW', pgettext_lazy('Country', 'Taiwan')),
    ('TJ', pgettext_lazy('Country', 'Tajikistan')),
    ('TZ', pgettext_lazy('Country', 'Tanzania')),
    ('TH', pgettext_lazy('Country', 'Thailand')),
    ('TL', pgettext_lazy('Country', 'Timor-Leste')),
    ('TG', pgettext_lazy('Country', 'Togo')),
    ('TK', pgettext_lazy('Country', 'Tokelau')),
    ('TO', pgettext_lazy('Country', 'Tonga')),
    ('TT', pgettext_lazy('Country', 'Trinidad And Tobago')),
    ('TN', pgettext_lazy('Country', 'Tunisia')),
    ('TR', pgettext_lazy('Country', 'Turkey')),
    ('TM', pgettext_lazy('Country', 'Turkmenistan')),
    ('TC', pgettext_lazy('Country', 'Turks And Caicos Islands')),
    ('TV', pgettext_lazy('Country', 'Tuvalu')),
    ('UG', pgettext_lazy('Country', 'Uganda')),
    ('UA', pgettext_lazy('Country', 'Ukraine')),
    ('AE', pgettext_lazy('Country', 'United Arab Emirates')),
    ('GB', pgettext_lazy('Country', 'United Kingdom')),
    ('US', pgettext_lazy('Country', 'United States')),
    ('UM', pgettext_lazy('Country', 'United States Minor Outlying Islands')),
    ('UY', pgettext_lazy('Country', 'Uruguay')),
    ('UZ', pgettext_lazy('Country', 'Uzbekistan')),
    ('VU', pgettext_lazy('Country', 'Vanuatu')),
    ('VE', pgettext_lazy('Country', 'Venezuela')),
    ('VN', pgettext_lazy('Country', 'Viet Nam')),
    ('VG', pgettext_lazy('Country', 'Virgin Islands, British')),
    ('VI', pgettext_lazy('Country', 'Virgin Islands, U.S.')),
    ('WF', pgettext_lazy('Country', 'Wallis And Futuna')),
    ('EH', pgettext_lazy('Country', 'Western Sahara')),
    ('YE', pgettext_lazy('Country', 'Yemen')),
    ('ZM', pgettext_lazy('Country', 'Zambia')),
    ('ZW', pgettext_lazy('Country', 'Zimbabwe'))]

########NEW FILE########
__FILENAME__ = dumpdata
from django.core.exceptions import ImproperlyConfigured
from django.core.management.base import BaseCommand, CommandError
from django.core.management.commands.dumpdata import sort_dependencies
from django.core import serializers
from django.db import router, DEFAULT_DB_ALIAS
from django.db.models.query import QuerySet
from django.utils.datastructures import SortedDict

from optparse import make_option


class Command(BaseCommand):
    option_list = BaseCommand.option_list + (
        make_option(
            '--format', default='json', dest='format',
            help='Specifies the output serialization format for fixtures.'),
        make_option(
            '--indent', default=None, dest='indent', type='int',
            help=('Specifies the indent level to use when pretty-printing'
                  ' output')),
        make_option(
            '--database', action='store', dest='database',
            default=DEFAULT_DB_ALIAS,
            help=('Nominates a specific database to dump fixtures from.'
                  ' Defaults to the "default" database.')),
        make_option(
            '-e', '--exclude', dest='exclude', action='append', default=[],
            help=('An appname or appname.ModelName to exclude (use multiple'
                  ' --exclude to exclude multiple apps/models).')),
        make_option(
            '-n', '--natural', action='store_true', dest='use_natural_keys',
            default=False, help='Use natural keys if they are available.'),
        make_option(
            '-a', '--all', action='store_true', dest='use_base_manager',
            default=False,
            help=("Use Django's base manager to dump all models stored in the"
                  " database, including those that would otherwise be filtered"
                  " or modified by a custom manager.")),
        make_option(
            '--pks', dest='primary_keys',
            help=("Only dump objects with "
                  "given primary keys. Accepts a comma seperated list of keys."
                  " This option will only work when you specify one model."))
    )
    help = ("Output the contents of the database as a fixture of the given "
            "format (using each model's default manager unless --all is "
            "specified).")
    args = '[appname appname.ModelName ...]'

    def handle(self, *app_labels, **options):
        from django.db.models import get_app, get_apps, get_model

        format = options.get('format')
        indent = options.get('indent')
        using = options.get('database')
        excludes = options.get('exclude')
        show_traceback = options.get('traceback')
        use_natural_keys = options.get('use_natural_keys')
        use_base_manager = options.get('use_base_manager')
        pks = options.get('primary_keys')

        if pks:
            primary_keys = pks.split(',')
        else:
            primary_keys = []

        excluded_apps = set()
        excluded_models = set()
        for exclude in excludes:
            if '.' in exclude:
                app_label, model_name = exclude.split('.', 1)
                model_obj = get_model(app_label, model_name)
                if not model_obj:
                    raise CommandError(
                        'Unknown model in excludes: %s' % (exclude,))
                excluded_models.add(model_obj)
            else:
                try:
                    app_obj = get_app(exclude)
                    excluded_apps.add(app_obj)
                except ImproperlyConfigured:
                    raise CommandError('Unknown app in excludes: %s' % exclude)

        if len(app_labels) == 0:
            if primary_keys:
                raise CommandError(
                    "You can only use --pks option with one model")
            app_list = SortedDict((app, None) for app in get_apps()
                                  if app not in excluded_apps)
        else:
            if len(app_labels) > 1 and primary_keys:
                raise CommandError(
                    "You can only use --pks option with one model")
            app_list = SortedDict()
            for label in app_labels:
                try:
                    app_label, model_label = label.split('.')
                    try:
                        app = get_app(app_label)
                    except ImproperlyConfigured:
                        raise CommandError(
                            "Unknown application: %s" % (app_label,))
                    if app in excluded_apps:
                        continue
                    model = get_model(app_label, model_label)
                    if model is None:
                        raise CommandError(
                            "Unknown model: %s.%s" % (app_label, model_label))

                    if app in app_list.keys():
                        if app_list[app] and model not in app_list[app]:
                            app_list[app].append(model)
                    else:
                        app_list[app] = [model]
                except ValueError:
                    if primary_keys:
                        raise CommandError(
                            "You can only use --pks option with one model")
                    # This is just an app - no model qualifier
                    app_label = label
                    try:
                        app = get_app(app_label)
                    except ImproperlyConfigured:
                        raise CommandError(
                            "Unknown application: %s" % (app_label,))
                    if app in excluded_apps:
                        continue
                    app_list[app] = None

        # Check that the serialization format exists; this is a shortcut to
        # avoid collating all the objects and _then_ failing.
        if format not in serializers.get_public_serializer_formats():
            try:
                serializers.get_serializer(format)
            except serializers.SerializerDoesNotExist:
                pass

            raise CommandError("Unknown serialization format: %s" % format)

        def get_objects():
            # Collate the objects to be serialized.
            for model in sort_dependencies(app_list.items()):
                if model in excluded_models:
                    continue
                if not model._meta.proxy and router.allow_syncdb(using, model):
                    if use_base_manager:
                        objects = model._base_manager
                    else:
                        objects = QuerySet(model).all()

                    queryset = objects.using(using).order_by(
                        model._meta.pk.name)
                    if primary_keys:
                        queryset = queryset.filter(pk__in=primary_keys)
                    for obj in queryset.iterator():
                        yield obj

        try:
            self.stdout.ending = None
            serializers.serialize(
                format, get_objects(), indent=indent,
                use_natural_keys=use_natural_keys, stream=self.stdout)
        except Exception as e:
            if show_traceback:
                raise
            raise CommandError("Unable to serialize database: %s" % e)

########NEW FILE########
__FILENAME__ = middleware
import logging
from subprocess import Popen, PIPE

from django.conf import settings
from django.utils.translation import get_language

from . import analytics
from ..product.models import FixedProductDiscount

logger = logging.getLogger('saleor')


class CheckHTML(object):

    def process_response(self, request, response):
        if (settings.DEBUG and
                settings.WARN_ABOUT_INVALID_HTML5_OUTPUT and
                200 <= response.status_code < 300):
            proc = Popen(["tidy"], stdout=PIPE, stderr=PIPE, stdin=PIPE)
            _out, err = proc.communicate(response.content)
            for l in err.split('\n\n')[0].split('\n')[:-2]:
                logger.warning(l)
        return response


class GoogleAnalytics(object):

    def process_request(self, request):
        client_id = analytics.get_client_id(request)
        path = request.path
        language = get_language()
        headers = request.META
        # FIXME: on production you might want to run this in background
        analytics.report_view(client_id, path=path, language=language,
                              headers=headers)


class DiscountMiddleware(object):

    def process_request(self, request):
        discounts = FixedProductDiscount.objects.all()
        discounts = discounts.prefetch_related('products')
        request.discounts = discounts

########NEW FILE########
__FILENAME__ = models

########NEW FILE########
__FILENAME__ = bootstrap
from django import forms
from django.forms.forms import BoundField, BaseForm
from django.forms.util import ErrorList
from django.template import Library, Context, TemplateSyntaxError
from django.template.loader import render_to_string
from django.utils.safestring import mark_safe

register = Library()

TEMPLATE_ERRORS = 'bootstrap/_non_field_errors.html'
TEMPLATE_HORIZONTAL = 'bootstrap/_field_horizontal.html'
TEMPLATE_VERTICAL = 'bootstrap/_field_vertical.html'


def render_non_field_errors(errors):
    if not errors:
        return ''
    context = Context({'errors': errors})
    return render_to_string(TEMPLATE_ERRORS, context_instance=context)


def render_field(bound_field, show_label, template):
    widget = bound_field.field.widget

    if isinstance(widget, forms.RadioSelect):
        input_type = 'radio'
    elif isinstance(widget, forms.Select):
        input_type = 'select'
    elif isinstance(widget, forms.Textarea):
        input_type = 'textarea'
    elif isinstance(widget, forms.CheckboxInput):
        input_type = 'checkbox'
    elif issubclass(type(widget), forms.MultiWidget):
        input_type = 'multi_widget'
    else:
        input_type = 'input'

    context = Context({'bound_field': bound_field,
                       'input_type': input_type,
                       'show_label': show_label})
    return render_to_string(template, context_instance=context)


def as_bootstrap(obj, show_label, template):
    if isinstance(obj, BoundField):
        return render_field(obj, show_label, template)
    elif isinstance(obj, ErrorList):
        return render_non_field_errors(obj)
    elif isinstance(obj, BaseForm):
        non_field_errors = render_non_field_errors(obj.non_field_errors())
        fields = (render_field(field, show_label, template) for field in obj)
        form = ''.join(fields)
        return mark_safe(non_field_errors + form)
    else:
        raise TemplateSyntaxError('Filter accepts form, field and non fields '
                                  'errors.')


@register.filter
def as_horizontal_form(obj, show_label=True):
    return as_bootstrap(obj=obj, show_label=show_label,
                        template=TEMPLATE_HORIZONTAL)


@register.filter
def as_vertical_form(obj, show_label=True):
    return as_bootstrap(obj=obj, show_label=show_label,
                        template=TEMPLATE_VERTICAL)


@register.simple_tag
def render_widget(obj, **attrs):
    return obj.as_widget(attrs=attrs)

########NEW FILE########
__FILENAME__ = markdown
from __future__ import absolute_import

from django import template
from django.utils.safestring import mark_safe
from markdown import markdown as format_markdown

register = template.Library()


@register.filter
def markdown(text):
    html = format_markdown(text, safe_mode="escape", output_format="html5")
    return mark_safe(html)

########NEW FILE########
__FILENAME__ = shop
try:
    from itertools import zip_longest
except ImportError:
    from itertools import izip_longest as zip_longest

from django.template import Library

register = Library()


@register.filter
def slice(items, group_size=1):
    args = [iter(items)] * group_size
    return (filter(None, group)
            for group in zip_longest(*args, fillvalue=None))

########NEW FILE########
__FILENAME__ = tests
from django.template.response import TemplateResponse
from django.test import TestCase
from mock import MagicMock
from satchless.process import InvalidData

from .utils import BaseStep


class SimpleStep(BaseStep):

    def __str__(self):
        return 'simple'

    def save(self):
        pass

    def validate(self):
        raise InvalidData()

    def get_absolute_url(self):
        return '/'


class SimpleStepTest(TestCase):

    def test_forms_are_valid(self):
        request = MagicMock()
        request.method = 'GET'
        step = SimpleStep(request)
        self.assert_(step.forms_are_valid())

    def test_process(self):
        request = MagicMock()
        request.method = 'GET'
        step = SimpleStep(request)
        self.assertEqual(type(step.process()), TemplateResponse)
        request.method = 'POST'
        self.assertEqual(step.process(), None)

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls import patterns, url

from . import views


urlpatterns = patterns(
    '',
    url(r'^$', views.home, name='home')
)

########NEW FILE########
__FILENAME__ = views
from django.shortcuts import render


def home(request):
    return render(request, 'base.html')

########NEW FILE########
__FILENAME__ = admin
from django.contrib import admin
from django.contrib.admin.options import ModelAdmin
from django.forms.models import BaseInlineFormSet
from django.template.loader import render_to_string
from django.utils.safestring import mark_safe

from .models import Order, OrderedItem, Payment


def format_address(address):
    address = render_to_string('userprofile/snippets/address-details.html',
                               {'address': address})
    # avoid django's linebreaks breaking the result
    return address.replace('\n', '')


class OrderModelAdmin(ModelAdmin):

    def get_inline_instances(self, request, order=None):
        inlines = super(OrderModelAdmin, self).get_inline_instances(request,
                                                                    order)
        if order:
            inlines.extend([
                DeliveryInlineAdmin(self.model, self.admin_site, group)
                for group in order.groups.all()])
        return inlines


class PaymentInlineAdmin(admin.TabularInline):

    model = Payment
    extra = 0
    readonly_fields = ['variant', 'status', 'transaction_id', 'currency',
                       'total', 'delivery', 'description', 'tax',
                       'billing_first_name', 'billing_last_name',
                       'billing_address_1', 'billing_address_2',
                       'billing_city', 'billing_country_code',
                       'billing_country_area', 'billing_postcode']
    exclude = ['token', 'extra_data']
    can_delete = False


class DeliveryFormSet(BaseInlineFormSet):

    def __init__(self, *args, **kwargs):
        kwargs['instance'] = self.instance_obj
        super(DeliveryFormSet, self).__init__(*args, **kwargs)


class DeliveryInlineAdmin(admin.TabularInline):

    model = OrderedItem
    formset = DeliveryFormSet

    def __init__(self, parent_model, admin_site, delivery):
        self.delivery = delivery
        delivery_class = delivery.__class__
        if hasattr(delivery, 'address'):
            address = format_address(delivery.address)
            self.verbose_name_plural = (
                mark_safe(
                    '%s: %s %s<br>%s' % (
                        delivery,
                        delivery.price.gross,
                        delivery.price.currency,
                        address)))
        if hasattr(delivery, 'email'):
            self.verbose_name_plural = (
                mark_safe(
                    '%s: %s %s<br>%s' % (
                        delivery,
                        delivery.price.gross,
                        delivery.price.currency,
                        delivery.email)))
        super(DeliveryInlineAdmin, self).__init__(delivery_class, admin_site)

    def get_formset(self, request, obj=None, **kwargs):
        obj = obj if not self.delivery else self.delivery
        formset = super(DeliveryInlineAdmin, self).get_formset(request, obj,
                                                               **kwargs)
        formset.instance_obj = obj
        return formset


class OrderAdmin(OrderModelAdmin):

    inlines = [PaymentInlineAdmin]
    exclude = ['token']
    readonly_fields = ['customer', 'total']
    list_display = ['__str__', 'status', 'created', 'user']

    def customer(self, obj):
        return format_address(obj.billing_address)
    customer.allow_tags = True

    def total(self, obj):
        total = obj.get_total()
        return '%s %s' % (total.gross, total.currency)
    total.short_description = 'Total'

    def has_add_permission(self, request, obj=None):
        return False


admin.site.register(Order, OrderAdmin)

########NEW FILE########
__FILENAME__ = forms
from django import forms
from django.conf import settings
from django.utils.translation import ugettext_lazy as _

from .models import Payment


class PaymentMethodsForm(forms.Form):

    method = forms.ChoiceField(choices=settings.CHECKOUT_PAYMENT_CHOICES)


class PaymentDeleteForm(forms.Form):

    payment_id = forms.IntegerField(widget=forms.HiddenInput())

    def __init__(self, *args, **kwargs):
        self.order = kwargs.pop('order')
        super(PaymentDeleteForm, self).__init__(*args, **kwargs)

    def clean(self):
        cleaned_data = super(PaymentDeleteForm, self).clean()
        payment_id = cleaned_data.get('payment_id')
        waiting_payments = self.order.payments.filter(status='waiting')
        try:
            payment = waiting_payments.get(id=payment_id)
        except Payment.DoesNotExist:
            self._errors['number'] = self.error_class(
                [_('Payment does not exist')])
        else:
            cleaned_data['payment'] = payment
        return cleaned_data

    def save(self):
        payment = self.cleaned_data['payment']
        payment.status = 'rejected'
        payment.save()

########NEW FILE########
__FILENAME__ = models
from __future__ import unicode_literals
from decimal import Decimal
from uuid import uuid4

from django.conf import settings
from django.core.urlresolvers import reverse
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models
from django.utils.encoding import smart_text
from django.utils.timezone import now
from django.utils.encoding import python_2_unicode_compatible
from django.utils.translation import pgettext_lazy
from django_prices.models import PriceField
from model_utils.managers import InheritanceManager
from payments import PurchasedItem
from payments.models import BasePayment
from prices import Price
from satchless.item import ItemSet, ItemLine

from ..communication.mail import send_email
from ..core.utils import build_absolute_uri
from ..product.models import Product
from ..userprofile.models import Address, User


@python_2_unicode_compatible
class Order(models.Model, ItemSet):

    STATUS_CHOICES = (
        ('new', pgettext_lazy('Order status field value', 'Processing')),
        ('cancelled', pgettext_lazy('Order status field value',
                                    'Cancelled')),
        ('payment-pending', pgettext_lazy('Order status field value',
                                          'Waiting for payment')),
        ('fully-paid', pgettext_lazy('Order status field value',
                                     'Fully paid')),
        ('shipped', pgettext_lazy('Order status field value',
                                  'Shipped')))
    status = models.CharField(
        pgettext_lazy('Order field', 'order status'),
        max_length=32, choices=STATUS_CHOICES, default='new')
    created = models.DateTimeField(
        pgettext_lazy('Order field', 'created'),
        default=now, editable=False)
    last_status_change = models.DateTimeField(
        pgettext_lazy('Order field', 'last status change'),
        default=now, editable=False)
    user = models.ForeignKey(
        User, blank=True, null=True, related_name='orders',
        verbose_name=pgettext_lazy('Order field', 'user'))
    tracking_client_id = models.CharField(max_length=36, blank=True,
                                          editable=False)
    billing_address = models.ForeignKey(Address, related_name='+',
                                        editable=False)
    anonymous_user_email = models.EmailField(blank=True, default='',
                                             editable=False)
    token = models.CharField(
        pgettext_lazy('Order field', 'token'),
        max_length=36, blank=True, default='')

    class Meta:
        ordering = ('-last_status_change',)

    def save(self, *args, **kwargs):
        if not self.token:
            for _i in range(100):
                token = str(uuid4())
                if not type(self).objects.filter(token=token).exists():
                    self.token = token
                    break
        return super(Order, self).save(*args, **kwargs)

    def change_status(self, status):
        self.status = status
        self.save()

    def get_items(self):
        return OrderedItem.objects.filter(delivery_group__order=self)

    def is_fully_paid(self):
        total_paid = sum([payment.total for payment in
                          self.payments.filter(status='confirmed')], Decimal())
        total = self.get_total()
        return total_paid >= total.gross

    def get_user_email(self):
        if self.user:
            return self.user.email
        return self.anonymous_user_email

    def __iter__(self):
        return iter(self.groups.all().select_subclasses())

    def __repr__(self):
        return '<Order #%r>' % (self.id,)

    def __str__(self):
        return '#%d' % (self.id, )

    @property
    def billing_full_name(self):
        return '%s %s' % (self.billing_first_name, self.billing_last_name)

    def get_absolute_url(self):
        return reverse('order:details', kwargs={'token': self.token})

    def get_delivery_total(self):
        return sum([group.price for group in self.groups.all()],
                   Price(0, currency=settings.DEFAULT_CURRENCY))

    def send_confirmation_email(self):
        email = self.get_user_email()
        payment_url = build_absolute_uri(
            reverse('order:details', kwargs={'token': self.token}))
        context = {'payment_url': payment_url}
        send_email(email, 'order/emails/confirm_email.txt', context)


class DeliveryGroup(models.Model, ItemSet):
    STATUS_CHOICES = (
        ('new',
         pgettext_lazy('Delivery group status field value', 'Processing')),
        ('cancelled', pgettext_lazy('Delivery group status field value',
                                    'Cancelled')),
        ('shipped', pgettext_lazy('Delivery group status field value',
                                  'Shipped')))
    status = models.CharField(
        pgettext_lazy('Delivery group field', 'Delivery status'),
        max_length=32, default='new', choices=STATUS_CHOICES)
    method = models.CharField(
        pgettext_lazy('Delivery group field', 'Delivery method'),
        max_length=255)
    order = models.ForeignKey(Order, related_name='groups', editable=False)
    price = PriceField(
        pgettext_lazy('Delivery group field', 'unit price'),
        currency=settings.DEFAULT_CURRENCY, max_digits=12,
        decimal_places=4,
        default=0,
        editable=False)

    objects = InheritanceManager()

    def __repr__(self):
        return '%s(%r)' % (self.__class__.__name__, list(self))

    def __iter__(self):
        if self.id:
            return iter(self.items.select_related('product').all())
        return super(DeliveryGroup, self).__iter__()

    def change_status(self, status):
        self.status = status
        self.save()

    def get_total(self, **kwargs):
        return super(DeliveryGroup, self).get_total(**kwargs) + self.price

    def add_items_from_partition(self, partition):
        for item_line in partition:
            product_variant = item_line.product
            price = item_line.get_price_per_item()
            self.items.create(
                product=product_variant.product,
                quantity=item_line.get_quantity(),
                unit_price_net=price.net,
                product_name=smart_text(product_variant),
                product_sku=product_variant.sku,
                unit_price_gross=price.gross)


@python_2_unicode_compatible
class ShippedDeliveryGroup(DeliveryGroup):

    address = models.ForeignKey(Address, related_name='+')

    def __str__(self):
        return 'Shipped delivery'


@python_2_unicode_compatible
class DigitalDeliveryGroup(DeliveryGroup):

    email = models.EmailField()

    def __str__(self):
        return 'Digital delivery'


@python_2_unicode_compatible
class OrderedItem(models.Model, ItemLine):

    delivery_group = models.ForeignKey(
        DeliveryGroup, related_name='items', editable=False)
    product = models.ForeignKey(
        Product, blank=True, null=True, related_name='+',
        on_delete=models.SET_NULL,
        verbose_name=pgettext_lazy('OrderedItem field', 'product'))
    product_name = models.CharField(
        pgettext_lazy('OrderedItem field', 'product name'), max_length=128)
    product_sku = models.CharField(pgettext_lazy('OrderedItem field', 'sku'),
                                   max_length=32)
    quantity = models.IntegerField(
        pgettext_lazy('OrderedItem field', 'quantity'),
        validators=[MinValueValidator(0), MaxValueValidator(999)])
    unit_price_net = models.DecimalField(
        pgettext_lazy('OrderedItem field', 'unit price (net)'),
        max_digits=12, decimal_places=4)
    unit_price_gross = models.DecimalField(
        pgettext_lazy('OrderedItem field', 'unit price (gross)'),
        max_digits=12, decimal_places=4)

    def get_price_per_item(self, **kwargs):
        return Price(net=self.unit_price_net, gross=self.unit_price_gross,
                     currency=settings.DEFAULT_CURRENCY)

    def __str__(self):
        return self.product_name

    def get_quantity(self):
        return self.quantity


class Payment(BasePayment):

    order = models.ForeignKey(Order, related_name='payments')

    def get_failure_url(self):
        return build_absolute_uri(
            reverse('order:details', kwargs={'token': self.order.token}))

    def get_success_url(self):
        return build_absolute_uri(
            reverse('order:details', kwargs={'token': self.order.token}))

    def send_confirmation_email(self):
        email = self.order.get_user_email()
        order_url = build_absolute_uri(
            reverse('order:details', kwargs={'token': self.order.token}))
        context = {'order_url': order_url}
        send_email(email, 'order/payment/emails/confirm_email.txt', context)

    def get_purchased_items(self):
        items = [PurchasedItem(
            name=item.product_name, sku=item.product_sku,
            quantity=item.quantity,
            price=item.unit_price_gross.quantize(Decimal('0.01')),
            currency=settings.DEFAULT_CURRENCY)
                 for item in self.order.get_items()]
        return items

########NEW FILE########
__FILENAME__ = tests

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls import patterns, url

from . import views


TOKEN_PATTERN = ('(?P<token>[0-9a-z]{8}-[0-9a-z]{4}-[0-9a-z]{4}-[0-9a-z]{4}'
                 '-[0-9a-z]{12})')

urlpatterns = patterns(
    '',
    url(r'^%s/$' % TOKEN_PATTERN, views.details, name='details'),
    url(r'^%s/payment/(?P<variant>[-\w]+)/$' % TOKEN_PATTERN,
        views.start_payment, name='payment'),
    url(r'^%s/cancel-payment/$' % TOKEN_PATTERN, views.cancel_payment,
        name='cancel-payment'))

########NEW FILE########
__FILENAME__ = views
import logging

from django.conf import settings
from django.contrib import messages
from django.db import transaction
from django.http import Http404, HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect
from django.utils.translation import ugettext as _
from django.template.response import TemplateResponse
from payments import RedirectNeeded

from . import check_order_status
from .forms import PaymentDeleteForm, PaymentMethodsForm
from .models import Order, Payment

logger = logging.getLogger(__name__)


def details(request, token):
    order = get_object_or_404(Order, token=token)
    groups = order.groups.all()
    payments = order.payments.all()
    form_data = request.POST or None
    try:
        waiting_payment = order.payments.get(status='waiting')
    except Payment.DoesNotExist:
        waiting_payment = None
        waiting_payment_form = None
    else:
        form_data = None
        waiting_payment_form = PaymentDeleteForm(
            None, order=order, initial={'payment_id': waiting_payment.id})
    if order.is_fully_paid():
        form_data = None
    payment_form = PaymentMethodsForm(form_data)
    if payment_form.is_valid():
        payment_method = payment_form.cleaned_data['method']
        return redirect('order:payment', token=order.token,
                        variant=payment_method)
    return TemplateResponse(request, 'order/details.html',
                            {'order': order, 'groups': groups,
                             'payment_form': payment_form,
                             'waiting_payment': waiting_payment,
                             'waiting_payment_form': waiting_payment_form,
                             'payments': payments})


@check_order_status
def start_payment(request, order, variant):
    waiting_payments = order.payments.filter(status='waiting').exists()
    if waiting_payments:
        return redirect('order:details', token=order.token)
    billing = order.billing_address
    total = order.get_total()
    defaults = {'total': total.gross,
                'tax': total.tax, 'currency': total.currency,
                'delivery': order.get_delivery_total().gross,
                'billing_address_1': billing.street_address,
                'billing_city': billing.city,
                'billing_postcode': billing.postal_code,
                'billing_country_code': billing.country}
    if not variant in [v for v, n in settings.CHECKOUT_PAYMENT_CHOICES]:
        raise Http404('%r is not a valid payment variant' % (variant,))
    with transaction.atomic():
        order.change_status('payment-pending')
        payment, _created = Payment.objects.get_or_create(variant=variant,
                                                          status='waiting',
                                                          order=order,
                                                          defaults=defaults)
        try:
            form = payment.get_form(data=request.POST or None)
        except RedirectNeeded as redirect_to:
            return redirect(str(redirect_to))
        except Exception:
            logger.exception('Error communicating with the payment gateway')
            messages.error(
                request,
                _('Oops, it looks like we were unable to contact the selected'
                  ' payment service'))
            payment.change_status('error')
            return redirect('order:details', token=order.token)
    template = 'order/payment/%s.html' % variant
    return TemplateResponse(request, [template, 'order/payment/default.html'],
                            {'form': form, 'payment': payment})


@check_order_status
def cancel_payment(request, order):
    form = PaymentDeleteForm(request.POST or None, order=order)
    if form.is_valid():
        with transaction.atomic():
            form.save()
        return redirect('order:details', token=order.token)
    return HttpResponseForbidden()

########NEW FILE########
__FILENAME__ = admin
from django.contrib import admin

from mptt.admin import MPTTModelAdmin

from .models import (ProductImage, BagVariant, Bag, ShirtVariant, Shirt,
                     Category, FixedProductDiscount, Color)
from .forms import ShirtAdminForm, ProductVariantInline


class ImageAdminInline(admin.StackedInline):
    model = ProductImage


class BagVariantInline(admin.StackedInline):
    model = BagVariant
    formset = ProductVariantInline


class BagAdmin(admin.ModelAdmin):
    inlines = [BagVariantInline, ImageAdminInline]


class ShirtVariantInline(admin.StackedInline):
    model = ShirtVariant
    formset = ProductVariantInline


class ShirtAdmin(admin.ModelAdmin):
    form = ShirtAdminForm
    list_display = ['name', 'collection', 'admin_get_price_min',
                    'admin_get_price_max']
    inlines = [ShirtVariantInline, ImageAdminInline]


class ProductCollectionAdmin(admin.ModelAdmin):
    search_fields = ['name']

admin.site.register(Bag, BagAdmin)
admin.site.register(Shirt, ShirtAdmin)
admin.site.register(Category, MPTTModelAdmin)
admin.site.register(FixedProductDiscount)
admin.site.register(Color)
########NEW FILE########
__FILENAME__ = forms
from django import forms
from django.utils.translation import pgettext_lazy
from selectable.forms import AutoCompleteWidget

from ..cart.forms import AddToCartForm
from .models import Bag, Shirt, ShirtVariant
from .lookups import CollectionLookup


class BagForm(AddToCartForm):

    def get_variant(self, clean_data):
        return self.product.variants.get(product__color=self.product.color)


class ShirtForm(AddToCartForm):
    
    size = forms.ChoiceField(choices=ShirtVariant.SIZE_CHOICES,
                             widget=forms.RadioSelect())

    def __init__(self, *args, **kwargs):
        super(ShirtForm, self).__init__(*args, **kwargs)
        available_sizes = [
            (p.size, p.get_size_display()) for p in self.product.variants.all()
        ]
        self.fields['size'].choices = available_sizes

    def get_variant(self, clean_data):
        size = clean_data.get('size')
        return self.product.variants.get(size=size,
                                         product__color=self.product.color)


class ShirtAdminForm(forms.ModelForm):
    class Meta:
        model = Shirt
        widgets = {
            'collection': AutoCompleteWidget(CollectionLookup)
        }


class ProductVariantInline(forms.models.BaseInlineFormSet):
    def clean(self):
        count = 0
        for form in self.forms:
            if form.cleaned_data:
                count += 1
        if count < 1:
            raise forms.ValidationError(
                pgettext_lazy('Product admin error',
                              'You have to create at least one variant'))

def get_form_class_for_product(product):
    if isinstance(product, Shirt):
        return ShirtForm
    if isinstance(product, Bag):
        return BagForm
    raise NotImplementedError

########NEW FILE########
__FILENAME__ = lookups
from __future__ import unicode_literals

from selectable.base import LookupBase
from selectable.registry import registry
from django.db.models import Count

from .models import Product


class CollectionLookup(LookupBase):

    def get_query(self, request, term):
        products = Product.objects.filter(collection__isnull=False,
                                          collection__istartswith=term)
        products = products.select_subclasses()
        qs = products.values('collection').annotate(
            products=Count('collection')
        ).order_by('-products')
        return qs

    def get_item_value(self, item):
        return item['collection']

    def get_item_label(self, item):
        collections = "{collection} ({products} products)".format(
            **item
        )
        return collections


registry.register(CollectionLookup)
########NEW FILE########
__FILENAME__ = populatedb
from os.path import exists, join

from django.core.management.base import BaseCommand, CommandError
from django.core.management import call_command

from utils.create_random_data import create_items


class Command(BaseCommand):
    help = 'Populate database with test objects'
    BASE_DIR = r'saleor/static/placeholders/'
    required_dirs = [join(BASE_DIR, 'shirts'), join(BASE_DIR, 'bags')]

    def handle(self, *args, **options):
        if not all(exists(path) for path in self.required_dirs):
            msg = 'Directories %s with images are required.' % ', '.join(
                self.required_dirs)
            raise CommandError(msg)
        for msg in create_items(self.BASE_DIR, 10):
            self.stdout.write(msg)

########NEW FILE########
__FILENAME__ = base
from __future__ import unicode_literals
import re

from django.core.urlresolvers import reverse
from django.utils.encoding import python_2_unicode_compatible
from django.db import models
from django.utils.safestring import mark_safe
from django.utils.translation import pgettext_lazy
from model_utils.managers import InheritanceManager
from mptt.models import MPTTModel
from satchless.item import ItemRange
from unidecode import unidecode


@python_2_unicode_compatible
class Category(MPTTModel):
    name = models.CharField(
        pgettext_lazy('Category field', 'name'), max_length=128)
    slug = models.SlugField(
        pgettext_lazy('Category field', 'slug'), max_length=50, unique=True)
    description = models.TextField(
        pgettext_lazy('Category field', 'description'), blank=True)
    parent = models.ForeignKey(
        'self', null=True, blank=True, related_name='children',
        verbose_name=pgettext_lazy('Category field', 'parent'))

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('product:category', kwargs={'slug': self.slug})

    class Meta:
        verbose_name_plural = 'categories'
        app_label = 'product'


@python_2_unicode_compatible
class Product(models.Model, ItemRange):
    name = models.CharField(
        pgettext_lazy('Product field', 'name'), max_length=128)
    category = models.ForeignKey(
        Category, verbose_name=pgettext_lazy('Product field', 'category'),
        related_name='products')
    description = models.TextField(
        verbose_name=pgettext_lazy('Product field', 'description'))
    collection = models.CharField(db_index=True, max_length=100, blank=True)

    objects = InheritanceManager()

    class Meta:
        app_label = 'product'

    def __iter__(self):
        if not hasattr(self, '__variants'):
            setattr(self, '__variants', self.variants.all())
        return iter(getattr(self, '__variants'))

    def __repr__(self):
        class_ = type(self)
        return '<%s.%s(pk=%r, name=%r)>' % (
            class_.__module__, class_.__name__, self.pk, self.name)

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('product:details', kwargs={'slug': self.get_slug(),
                                                  'product_id': self.id})

    def get_slug(self):
        value = unidecode(self.name)
        value = re.sub(r'[^\w\s-]', '', value).strip().lower()
        return mark_safe(re.sub(r'[-\s]+', '-', value))

    def get_formatted_price(self, price):
        return "{0} {1}".format(price.gross, price.currency)

    def admin_get_price_min(self):
        price = self.get_price_range().min_price
        return self.get_formatted_price(price)
    admin_get_price_min.short_description = pgettext_lazy(
        'Product admin page', 'Minimum price')

    def admin_get_price_max(self):
        price = self.get_price_range().max_price
        return self.get_formatted_price(price)
    admin_get_price_max.short_description = pgettext_lazy(
        'Product admin page', 'Maximum price')

########NEW FILE########
__FILENAME__ = discounts
from __future__ import unicode_literals

from django.conf import settings
from django.db import models
from django.utils.translation import pgettext_lazy
from django.utils.encoding import python_2_unicode_compatible
from django_prices.models import PriceField
from prices import FixedDiscount

from .base import Product


class NotApplicable(ValueError):
    pass


@python_2_unicode_compatible
class FixedProductDiscount(models.Model):
    name = models.CharField(max_length=255)
    products = models.ManyToManyField(Product, blank=True)
    discount = PriceField(pgettext_lazy('Discount field', 'discount value'),
                          currency=settings.DEFAULT_CURRENCY,
                          max_digits=12, decimal_places=4)

    class Meta:
        app_label = 'product'

    def __repr__(self):
        return 'FixedProductDiscount(name=%r, discount=%r)' % (
            str(self.discount), self.name)

    def __str__(self):
        return self.name

    def modifier_for_product(self, variant):
        if not self.products.filter(pk=variant.product.pk).exists():
            raise NotApplicable('Discount not applicable for this product')
        if self.discount > variant.get_price(discounted=False):
            raise NotApplicable('Discount too high for this product')
        return FixedDiscount(self.discount, name=self.name)


def get_product_discounts(variant, discounts, **kwargs):
    for discount in discounts:
        try:
            yield discount.modifier_for_product(variant, **kwargs)
        except NotApplicable:
            pass

########NEW FILE########
__FILENAME__ = images
from __future__ import unicode_literals

from django.db import models
from django_images.models import Image
from django.utils.safestring import mark_safe
from django.utils.encoding import python_2_unicode_compatible

from .base import Product


class ImageManager(models.Manager):
    def first(self):
        return self.get_query_set()[0]


@python_2_unicode_compatible
class ProductImage(Image):
    product = models.ForeignKey(Product, related_name='images')

    objects = ImageManager()

    class Meta:
        ordering = ['id']
        app_label = 'product'

    def __str__(self):
        html = '<img src="%s" alt="">' % (
            self.get_absolute_url('admin'),)
        return mark_safe(html)

########NEW FILE########
__FILENAME__ = products
from __future__ import unicode_literals

from django.utils.translation import pgettext_lazy
from django.db import models

from .base import Product
from .variants import (ProductVariant, PhysicalProduct, ColoredVariant,
                       StockedProduct)


class Bag(Product, PhysicalProduct, ColoredVariant):

    class Meta:
        app_label = 'product'


class Shirt(Product, PhysicalProduct, ColoredVariant):

    class Meta:
        app_label = 'product'


class BagVariant(ProductVariant, StockedProduct):

    product = models.ForeignKey(Bag, related_name='variants')

    class Meta:
        app_label = 'product'


class ShirtVariant(ProductVariant, StockedProduct):
    
    SIZE_CHOICES = (
        ('xs', pgettext_lazy('Variant size', 'XS')),
        ('s', pgettext_lazy('Variant size', 'S')),
        ('m', pgettext_lazy('Variant size', 'M')),
        ('l', pgettext_lazy('Variant size', 'L')),
        ('xl', pgettext_lazy('Variant size', 'XL')),
        ('xxl', pgettext_lazy('Variant size', 'XXL')))

    product = models.ForeignKey(Shirt, related_name='variants')
    size = models.CharField(choices=SIZE_CHOICES, max_length=3)

    class Meta:
        app_label = 'product'
########NEW FILE########
__FILENAME__ = variants
from __future__ import unicode_literals
from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import models
from django.utils.translation import pgettext_lazy
from satchless.item import Item, StockedItem
from django_prices.models import PriceField
from django.conf import settings
from django.core.urlresolvers import reverse
from django.utils.encoding import python_2_unicode_compatible

from .discounts import get_product_discounts


@python_2_unicode_compatible
class Color(models.Model):
    name = models.CharField(pgettext_lazy('Color name field', 'name'),
                            max_length=100)
    color = models.CharField(pgettext_lazy('Color hex value', 'HEX value'),
                             max_length=6)

    class Meta:
        app_label = 'product'

    def __str__(self):
        return self.name


class StockedProduct(models.Model, StockedItem):
    stock = models.IntegerField(pgettext_lazy('Product item field', 'stock'),
                                validators=[MinValueValidator(0)],
                                default=Decimal(1))

    class Meta:
        abstract = True
        app_label = 'product'

    def get_stock(self):
        return self.stock


class PhysicalProduct(models.Model):
    weight = models.DecimalField(max_digits=6, decimal_places=2)
    length = models.DecimalField(
        max_digits=6, decimal_places=2, blank=True, default=0)
    width = models.DecimalField(
        max_digits=6, decimal_places=2, blank=True, default=0)
    depth = models.DecimalField(
        max_digits=6, decimal_places=2, blank=True, default=0)
    price = PriceField(
        pgettext_lazy('Product field', 'price'),
        currency=settings.DEFAULT_CURRENCY, max_digits=12, decimal_places=4)

    def get_weight(self):
        try:
            return self.weight
        except AttributeError:
            return self.product.weight
    
    class Meta:
        abstract = True
        app_label = 'product'


class ColoredVariant(models.Model):
    color = models.ForeignKey(Color)

    class Meta:
        abstract = True
        app_label = 'product'


@python_2_unicode_compatible
class ProductVariant(models.Model, Item):
    name = models.CharField(pgettext_lazy('Product field', 'name'),
                            max_length=128, blank=True, default='')
    sku = models.CharField(
        pgettext_lazy('Product field', 'sku'), max_length=32, unique=True)
    # override the price attribute to implement per-variant pricing
    price = None

    class Meta:
        abstract = True
        app_label = 'product'

    def __str__(self):
        return self.name or self.product.name

    def get_price_per_item(self, discounts=None, **kwargs):
        if self.price is not None:
            price = self.price
        else:
            price = self.product.price
        if discounts:
            discounts = list(get_product_discounts(self, discounts, **kwargs))
            if discounts:
                modifier = max(discounts)
                price += modifier
        return price
        
    def get_weight(self):
        try:
            return self.weight
        except AttributeError:
            return self.product.weight
    
    def get_absolute_url(self):
        slug = self.product.get_slug()
        product_id = self.product.id
        return reverse(
            'product:details', kwargs={'slug': slug, 'product_id': product_id})

    def as_data(self):
        return {
            'product_name': str(self),
            'product_id': self.product.pk,
            'variant_id': self.pk,
            'unit_price': str(self.get_price_per_item().gross)
        }

########NEW FILE########
__FILENAME__ = category
from django import template
from ..models import Category

register = template.Library()


@register.inclusion_tag('category/_list.html')
def categories_list():
    return {'categories': Category.objects.all()}

########NEW FILE########
__FILENAME__ = discount
from django import template

register = template.Library()


@register.filter
def discounted_price(item, discounts):
    return item.get_price(discounts=discounts)

@register.filter
def discounted_price_range(item, discounts):
    return item.get_price_range(discounts=discounts)

@register.filter
def price_difference(price1, price2):
    return price1 - price2

########NEW FILE########
__FILENAME__ = price_ranges
from django import template

register = template.Library()

@register.inclusion_tag('product/_price_range.html')
def price_range(price_range):
    return {'price_range': price_range}
########NEW FILE########
__FILENAME__ = urls
from django.conf.urls import patterns, url

from . import views


urlpatterns = patterns(
    '',
    url(r'^(?P<slug>[a-z0-9-]+?)-(?P<product_id>[0-9]+)/$',
        views.product_details, name='details'),
    url(r'^category/(?P<slug>[a-z0-9-]+?)/$', views.category_index,
        name='category')
)

########NEW FILE########
__FILENAME__ = views
from __future__ import unicode_literals

from django.http import HttpResponsePermanentRedirect
from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect
from django.template.response import TemplateResponse
from django.utils.translation import ugettext as _

from .forms import get_form_class_for_product
from .models import Product, Category
from saleor.cart import Cart


def get_related_products(product):
    if not product.collection:
        return []
    related_products = Product.objects.filter(
        collection=product.collection)
    related_products = related_products.prefetch_related('images')
    return related_products


def product_details(request, slug, product_id):
    product = get_object_or_404(Product.objects.select_subclasses(),
                                id=product_id)
    if product.get_slug() != slug:
        return HttpResponsePermanentRedirect(product.get_absolute_url())
    form_class = get_form_class_for_product(product)
    cart = Cart.for_session_cart(request.cart, discounts=request.discounts)
    form = form_class(cart=cart, product=product,
                      data=request.POST or None)
    if form.is_valid():
        if form.cleaned_data['quantity']:
            msg = _('Added %(product)s to your cart.') % {
                'product': product}
            messages.success(request, msg)
        form.save()
        return redirect('product:details', slug=slug, product_id=product_id)
    template_name = 'product/details_%s.html' % (
        type(product).__name__.lower(),)
    templates = [template_name, 'product/details.html']
    related_products = get_related_products(product)
    return TemplateResponse(
        request, templates,
        {'product': product, 'form': form,
         'related_products': related_products})


def category_index(request, slug):
    category = get_object_or_404(Category, slug=slug)
    products = category.products.all().select_subclasses()
    products = products.prefetch_related('images')
    return TemplateResponse(
        request, 'category/index.html',
        {'products': products, 'category': category})

########NEW FILE########
__FILENAME__ = backends
from django.contrib.auth import get_user_model

from .models import ExternalUserData

User = get_user_model()


class Backend(object):

    def get_user(self, user_id):
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None


class EmailPasswordBackend(Backend):
    """Authentication backend that expects an email in username parameter."""

    def authenticate(self, username=None, password=None, **_kwargs):
        try:
            user = User.objects.get(email=username)
        except User.DoesNotExist:
            return None
        if user.check_password(password):
            return user


class ExternalLoginBackend(Backend):
    """Authenticate with external service id."""

    def authenticate(self, service=None, username=None, **_kwargs):
        try:
            user_data = (ExternalUserData.objects
                                         .select_related('user')
                                         .get(service=service,
                                              username=username))
            return user_data.user
        except ExternalUserData.DoesNotExist:
            return None


class TrivialBackend(Backend):
    """Authenticate with user instance."""

    def authenticate(self, user=None, **_kwargs):
        if isinstance(user, User):
            return user

########NEW FILE########
__FILENAME__ = forms
from __future__ import unicode_literals

from django import forms
from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.forms import AuthenticationForm, SetPasswordForm
from django.utils.translation import pgettext_lazy, ugettext

from ..userprofile.models import User

from .models import (
    EmailConfirmationRequest,
    EmailChangeRequest,
    ExternalUserData)
from .utils import get_client_class_for_service
from ..communication.mail import send_email


class LoginForm(AuthenticationForm):

    username = forms.EmailField(label=pgettext_lazy('Form field', 'Email'),
                                max_length=75)

    def __init__(self, request=None, *args, **kwargs):
        super(LoginForm, self).__init__(request=request, *args, **kwargs)
        if request:
            email = request.GET.get('email')
            if email:
                self.fields['username'].initial = email


class SetOrRemovePasswordForm(SetPasswordForm):

    def __init__(self, *args, **kwargs):
        super(SetOrRemovePasswordForm, self).__init__(*args, **kwargs)
        if not 'new_password1' in self.data.keys():
            self.fields['new_password1'].required = False
            self.fields['new_password2'].required = False

    def save(self, commit=True):
        if self.cleaned_data.get('new_password1'):
            return super(SetOrRemovePasswordForm, self).save(commit)
        else:
            self.user.set_unusable_password()
        return self.user


class RequestEmailConfirmationForm(forms.Form):

    email = forms.EmailField()

    template = 'registration/emails/confirm_email.txt'

    def __init__(self, local_host=None, data=None):
        self.local_host = local_host
        super(RequestEmailConfirmationForm, self).__init__(data)

    def send(self):
        email = self.cleaned_data['email']
        request = self.create_request_instance()
        confirmation_url = self.local_host + request.get_confirmation_url()
        context = {'confirmation_url': confirmation_url}
        send_email(email, self.template, context)

    def create_request_instance(self):
        email = self.cleaned_data['email']
        EmailConfirmationRequest.objects.filter(email=email).delete()
        return EmailConfirmationRequest.objects.create(
            email=self.cleaned_data['email'])


class RequestEmailChangeForm(RequestEmailConfirmationForm):

    template = 'registration/emails/change_email.txt'

    def __init__(self, user=None, *args, **kwargs):
        self.user = user
        super(RequestEmailChangeForm, self).__init__(*args, **kwargs)

    def clean_email(self):
        email = self.cleaned_data['email']
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError(
                ugettext('Account with this email already exists'))
        return self.cleaned_data['email']

    def create_request_instance(self):
        EmailChangeRequest.objects.filter(user=self.user).delete()
        return EmailChangeRequest.objects.create(
            email=self.cleaned_data['email'], user=self.user)


class OAuth2CallbackForm(forms.Form):

    code = forms.CharField()
    error_code = forms.CharField(required=False)
    error_message = forms.CharField(required=False)

    def __init__(self, service, local_host, data):
        self.service = service
        self.local_host = local_host
        super(OAuth2CallbackForm, self).__init__(data)

    def clean_error_message(self):
        error_message = self.cleaned_data.get('error_message')
        if error_message:
            raise forms.ValidationError(error_message)

    def get_authenticated_user(self):
        code = self.cleaned_data.get('code')
        client_class = get_client_class_for_service(self.service)
        client = client_class(local_host=self.local_host, code=code)
        user_info = client.get_user_info()
        user = authenticate(service=self.service, username=user_info['id'])
        if not user:
            user, _ = User.objects.get_or_create(
                email=user_info['email'])
            ExternalUserData.objects.create(
                service=self.service, username=user_info['id'], user=user)
            user = authenticate(user=user)
        return user

########NEW FILE########
__FILENAME__ = models
from __future__ import unicode_literals
from datetime import timedelta

from django.db import models
from django.contrib.auth import authenticate
from django.conf import settings
from django.core.urlresolvers import reverse
from django.utils import timezone
from django.utils.crypto import get_random_string

from ..userprofile.models import User

now = timezone.now


class ExternalUserData(models.Model):

    user = models.ForeignKey(User, related_name='external_ids')
    service = models.TextField(db_index=True)
    username = models.TextField(db_index=True)

    class Meta:
        unique_together = [['service', 'username']]


class UniqueTokenManager(models.Manager):  # this might end up in `utils`

    def __init__(self, token_field, token_length):
        self.token_field = token_field
        self.token_length = token_length
        super(UniqueTokenManager, self).__init__()

    def create(self, **kwargs):
        assert self.token_field not in kwargs, 'Token field already filled.'
        for _x in xrange(100):
            token = get_random_string(self.token_length)
            conflict_filter = {self.token_field: token}
            conflict = self.get_query_set().filter(**conflict_filter)
            if not conflict.exists():
                kwargs[self.token_field] = token
                return super(UniqueTokenManager, self).create(**kwargs)
        raise RuntimeError('Could not create unique token.')


class AbstractToken(models.Model):

    TOKEN_LENGTH = 32

    token = models.CharField(max_length=TOKEN_LENGTH, unique=True)
    valid_until = models.DateTimeField(
        default=lambda: now() + timedelta(settings.ACCOUNT_ACTIVATION_DAYS))

    objects = UniqueTokenManager(token_field='token',
                                 token_length=TOKEN_LENGTH)

    class Meta:
        abstract = True


class EmailConfirmationRequest(AbstractToken):

    email = models.EmailField()

    def get_authenticated_user(self):
        user, _created = User.objects.get_or_create(email=self.email)
        return authenticate(user=user)

    def get_confirmation_url(self):
        return reverse('registration:confirm_email',
                       kwargs={'token': self.token})


class EmailChangeRequest(AbstractToken):

    user = models.ForeignKey(User, related_name="email_change_requests")
    email = models.EmailField()  # email address that user is switching to

    def get_confirmation_url(self):
        return reverse('registration:change_email',
                       kwargs={'token': self.token})

########NEW FILE########
__FILENAME__ = tests
from unittest import TestCase

from django.core.urlresolvers import resolve
from django.conf import settings
from django.http import HttpRequest
from mock import call, Mock, MagicMock, patch, sentinel
from purl import URL

from .forms import OAuth2CallbackForm
from .utils import (
    FACEBOOK,
    FacebookClient,
    GOOGLE,
    GoogleClient,
    OAuth2RequestAuthorizer,
    OAuth2Client,
    parse_response)
from .views import oauth_callback, change_email


JSON_MIME_TYPE = 'application/json; charset=UTF-8'
URLENCODED_MIME_TYPE = 'application/x-www-form-urlencoded; charset=UTF-8'


class SessionMock(Mock):

    def __setitem__(self, key, value):
        pass


class LoginUrlsTestCase(TestCase):
    """Tests login url generation."""

    def test_facebook_login_url(self):
        """Facebook login url is properly generated"""
        facebook_client = FacebookClient(local_host='localhost')
        facebook_login_url = URL(facebook_client.get_login_uri())
        query = facebook_login_url.query_params()
        callback_url = URL(query['redirect_uri'][0])
        func, _args, kwargs = resolve(callback_url.path())
        self.assertEquals(func, oauth_callback)
        self.assertEquals(kwargs['service'], FACEBOOK)
        self.assertEqual(query['scope'][0], FacebookClient.scope)
        self.assertEqual(query['client_id'][0], str(FacebookClient.client_id))

    def test_google_login_url(self):
        """Google login url is properly generated"""
        google_client = GoogleClient(local_host='local_host')
        google_login_url = URL(google_client.get_login_uri())
        params = google_login_url.query_params()
        callback_url = URL(params['redirect_uri'][0])
        func, _args, kwargs = resolve(callback_url.path())
        self.assertEquals(func, oauth_callback)
        self.assertEquals(kwargs['service'], GOOGLE)
        self.assertTrue(params['scope'][0] in GoogleClient.scope)
        self.assertEqual(params['client_id'][0], str(GoogleClient.client_id))


class ResponseParsingTestCase(TestCase):

    def setUp(self):
        self.response = MagicMock()

    def test_parse_json(self):
        """OAuth2 client is able to parse json response"""
        self.response.headers = {'Content-Type': JSON_MIME_TYPE}
        self.response.json.return_value = sentinel.json_content
        content = parse_response(self.response)
        self.assertEquals(content, sentinel.json_content)

    def test_parse_urlencoded(self):
        """OAuth2 client is able to parse urlencoded response"""
        self.response.headers = {'Content-Type': URLENCODED_MIME_TYPE}
        self.response.text = 'key=value&multi=a&multi=b'
        content = parse_response(self.response)
        self.assertEquals(content, {'key': 'value', 'multi': ['a', 'b']})


class TestClient(OAuth2Client):
    """OAuth2Client configured for testing purposes."""

    service = sentinel.service

    client_id = sentinel.client_id
    client_secret = sentinel.client_secret

    auth_uri = sentinel.auth_uri
    token_uri = sentinel.token_uri
    user_info_uri = sentinel.user_info_uri

    scope = sentinel.scope

    def get_redirect_uri(self):
        return sentinel.redirect_uri

    def extract_error_from_response(self, response_content):
        return 'some error'


class BaseCommunicationTestCase(TestCase):

    def setUp(self):
        self.parse_mock = patch(
            'saleor.registration.utils.parse_response').start()
        self.requests_mock = patch(
            'saleor.registration.utils.requests').start()
        self.requests_mock.codes.ok = sentinel.ok

    def tearDown(self):
        patch.stopall()


class AccessTokenTestCase(BaseCommunicationTestCase):
    """Tests obtaining access_token."""

    def setUp(self):
        super(AccessTokenTestCase, self).setUp()

        self.parse_mock.return_value = {'access_token': sentinel.access_token}

        self.access_token_response = MagicMock()
        self.requests_mock.post.return_value = self.access_token_response

    def test_token_is_obtained_on_construction(self):
        """OAuth2 client asks for access token if interim code is available"""
        self.access_token_response.status_code = sentinel.ok
        TestClient(local_host='http://localhost', code=sentinel.code)
        self.requests_mock.post.assert_called_once()

    def test_token_success(self):
        """OAuth2 client properly obtains access token"""
        client = TestClient(local_host='http://localhost')
        self.access_token_response.status_code = sentinel.ok
        access_token = client.get_access_token(code=sentinel.code)
        self.assertEquals(access_token, sentinel.access_token)
        self.requests_mock.post.assert_called_once_with(
            sentinel.token_uri,
            data={'grant_type': 'authorization_code',
                  'client_id': sentinel.client_id,
                  'client_secret': sentinel.client_secret,
                  'code': sentinel.code,
                  'redirect_uri': sentinel.redirect_uri,
                  'scope': sentinel.scope},
            auth=None)

    def test_token_failure(self):
        """OAuth2 client properly reacts to access token fetch failure"""
        client = TestClient(local_host='http://localhost')
        self.access_token_response.status_code = sentinel.fail
        self.assertRaises(ValueError, client.get_access_token,
                          code=sentinel.code)


class UserInfoTestCase(BaseCommunicationTestCase):
    """Tests obtaining user data."""

    def setUp(self):
        super(UserInfoTestCase, self).setUp()

        self.user_info_response = MagicMock()
        self.requests_mock.get.return_value = self.user_info_response

    def test_user_info_success(self):
        """OAuth2 client properly fetches user info"""
        client = TestClient(local_host='http://localhost')
        self.parse_mock.return_value = sentinel.user_info
        self.user_info_response.status_code = sentinel.ok
        user_info = client.get_user_info()
        self.assertEquals(user_info, sentinel.user_info)

    def test_user_data_failure(self):
        """OAuth2 client reacts well to user info fetch failure"""
        client = TestClient(local_host='http://localhost')
        self.assertRaises(ValueError, client.get_user_info)

    def test_google_user_data_email_not_verified(self):
        """Google OAuth2 client checks for email verification"""
        self.user_info_response.status_code = sentinel.ok
        self.parse_mock.return_value = {'verified_email': False}
        google_client = GoogleClient(local_host='http://localhost')
        self.assertRaises(ValueError, google_client.get_user_info)

    def test_facebook_user_data_account_not_verified(self):
        """Facebook OAuth2 client checks for account verification"""
        self.user_info_response.status_code = sentinel.ok
        self.parse_mock.return_value = {'verified': False}
        facebook_client = FacebookClient(local_host='http://localhost')
        self.assertRaises(ValueError, facebook_client.get_user_info)


class AuthorizerTestCase(TestCase):

    def test_authorizes(self):
        """OAuth2 authorizer sets proper auth headers"""
        authorizer = OAuth2RequestAuthorizer(access_token='token')
        request = Mock(headers={})
        authorizer(request)
        self.assertEquals('Bearer token', request.headers['Authorization'])


class CallbackTestCase(TestCase):

    def setUp(self):
        patcher = patch(
            'saleor.registration.forms.get_client_class_for_service')
        self.getter_mock = patcher.start()
        patcher = patch('saleor.registration.forms.authenticate')
        self.authenticate_mock = patcher.start()

        self.client_class = self.getter_mock()
        self.client = self.client_class()
        self.client.get_user_info.return_value = {'id': sentinel.id,
                                                  'email': sentinel.email}

        self.form = OAuth2CallbackForm(service=sentinel.service,
                                       local_host=sentinel.local_host,
                                       data={'code': 'test_code'})
        self.assertTrue(self.form.is_valid(), self.form.errors)

    @patch('saleor.registration.forms.ExternalUserData')
    @patch('saleor.registration.forms.User')
    def test_new_user(self, user_mock, external_data_mock):
        """OAuth2 callback creates a new user with proper external data"""
        user_mock.objects.get_or_create.return_value = sentinel.user, None
        self.authenticate_mock.side_effect = [None, sentinel.authed_user]

        user = self.form.get_authenticated_user()

        self.assertEquals(self.authenticate_mock.mock_calls,
                          [call(service=sentinel.service,
                                username=sentinel.id),
                           call(user=sentinel.user)])
        external_data_mock.objects.create.assert_called_once_with(
            service=sentinel.service, username=sentinel.id, user=sentinel.user)
        self.assertEquals(user, sentinel.authed_user)

    def test_existing_user(self):
        """OAuth2 recognizes existing user via external data credentials"""
        self.authenticate_mock.return_value = sentinel.authed_user

        user = self.form.get_authenticated_user()

        self.assertEquals(user, sentinel.authed_user)
        self.authenticate_mock.assert_called_once_with(
            service=sentinel.service, username=sentinel.id)

    def tearDown(self):
        patch.stopall()


class EmailChangeTestCase(TestCase):

    @patch('saleor.registration.views.now')
    @patch('saleor.registration.views.EmailChangeRequest.objects.get')
    def test_another_user_logged_out(self, get, now):

        # user requests email change
        user = Mock()
        token_object = Mock()
        token_object.token = 'sometokencontent'
        token_object.user = user
        get.return_value = token_object

        # another user is logged in
        another_user = Mock()
        request = Mock()
        request.user = another_user
        request.session = SessionMock()

        # first user clicks link in his email
        result = change_email(request, token_object.token)
        self.assertEquals(result.status_code, 302)
        get.assert_called_once_with(
            token=token_object.token, valid_until__gte=now())
        self.assertFalse(request.user.is_authenticated())
        token_object.delete.assert_not_called()

    @patch('saleor.registration.views.now')
    @patch('saleor.registration.views.EmailChangeRequest.objects.get')
    def test_user_logged_in(self, get, now):

        # user requests email change
        user = Mock()
        token_object = Mock()
        token_object.token = 'sometokencontent'
        token_object.user = user
        get.return_value = token_object

        # user is logged in
        request = MagicMock(HttpRequest)
        request._messages = Mock()
        request.user = user

        # user clicks link in his email
        result = change_email(request, token_object.token)
        self.assertEquals(result.status_code, 302)
        get.assert_called_once_with(
            token=token_object.token, valid_until__gte=now())
        # user stays logged in
        self.assertTrue(request.user.is_authenticated())
        # token is deleted
        token_object.delete.assert_called_once_with()
        user.save.assert_called_once_with()
        # user email gets changed
        self.assertEqual(user.email, token_object.email)


class OAuthClientTestCase(TestCase):
    def setUp(self):
        self.fake_client_id = 'test'
        self.fake_client_secret = 'testsecret'

    def test_google_secrets_override(self):
        client = GoogleClient(local_host='http://localhost',
                              client_id=self.fake_client_id,
                              client_secret=self.fake_client_secret)
        self.assertEqual(client.client_id, self.fake_client_id)
        self.assertEqual(client.client_secret, self.fake_client_secret)

    def test_google_secrets_fallback(self):
        client = GoogleClient(local_host='http://localhost')
        self.assertEqual(client.client_id, settings.GOOGLE_CLIENT_ID)
        self.assertEqual(client.client_secret, settings.GOOGLE_CLIENT_SECRET)

    def test_facebook_secrets_override(self):
        client = FacebookClient(local_host='http://localhost',
                                client_id=self.fake_client_id,
                                client_secret=self.fake_client_secret)
        self.assertEqual(client.client_id, self.fake_client_id)
        self.assertEqual(client.client_secret, self.fake_client_secret)

    def test_facebook_secrets_fallback(self):
        client = FacebookClient(local_host='http://localhost')
        self.assertEqual(client.client_id, settings.FACEBOOK_APP_ID)
        self.assertEqual(client.client_secret, settings.FACEBOOK_SECRET)

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls import patterns, url

from . import views


urlpatterns = patterns(
    '',
    url(r'^login/$', views.login, name='login'),
    url(r'^logout/$', views.logout, name='logout'),
    url(r'^oauth_callback/(?P<service>\w+)/$', views.oauth_callback,
        name='oauth_callback'),
    url(r'^change_password/$', views.change_password,
        name='change_password'),
    url(r'^request_email_confirmation/$', views.request_email_confirmation,
        name='request_email_confirmation'),
    url(r'^confirm_email/(?P<token>\w+)/$', views.confirm_email,
        name='confirm_email'),
    url(r'^request_email_change/$', views.request_email_change,
        name='request_email_change'),
    url(r'^change_email/(?P<token>\w+)/$', views.change_email,
        name='change_email'))

########NEW FILE########
__FILENAME__ = utils
import logging
try:
    from urllib.parse import parse_qs, urlencode, urljoin, urlunparse
except ImportError:
    from urllib import urlencode
    from urlparse import parse_qs, urljoin, urlunparse

from django.core.urlresolvers import reverse
from django.conf import settings
import requests


GOOGLE, FACEBOOK = 'google', 'facebook'
JSON_MIME_TYPE = 'application/json'
logger = logging.getLogger('saleor.registration')


def get_local_host(request):
    scheme = 'http' + ('s' if request.is_secure() else '')
    return url(scheme=scheme, host=request.get_host())


def url(scheme='', host='', path='', params='', query='', fragment=''):
    return urlunparse((scheme, host, path, params, query, fragment))


def get_client_class_for_service(service):
    return {GOOGLE: GoogleClient, FACEBOOK: FacebookClient}[service]


def get_google_login_url(local_host):
    if settings.GOOGLE_CLIENT_ID:
        client_class = get_client_class_for_service(GOOGLE)(local_host)
        return client_class.get_login_uri()


def get_facebook_login_url(local_host):
    if settings.FACEBOOK_APP_ID:
        client_class = get_client_class_for_service(FACEBOOK)(local_host)
        return client_class.get_login_uri()


def parse_response(response):
    if JSON_MIME_TYPE in response.headers['Content-Type']:
        return response.json()
    else:
        content = parse_qs(response.text)
        content = dict((x, y[0] if len(y) == 1 else y)
                       for x, y in content.items())
        return content


class OAuth2RequestAuthorizer(requests.auth.AuthBase):

    def __init__(self, access_token):
        self.access_token = access_token

    def __call__(self, request):
        request.headers['Authorization'] = 'Bearer %s' % (self.access_token,)
        return request


class OAuth2Client(object):

    service = None

    client_id = None
    client_secret = None

    auth_uri = None
    token_uri = None
    user_info_uri = None

    scope = None

    def __init__(self, local_host, code=None,
                 client_id=None, client_secret=None):
        self.local_host = local_host

        if client_id and client_secret:
            self.client_id = client_id
            self.client_secret = client_secret

        if code:
            access_token = self.get_access_token(code)
            self.authorizer = OAuth2RequestAuthorizer(
                access_token=access_token)
        else:
            self.authorizer = None

    def get_redirect_uri(self):
        kwargs = {'service': self.service}
        path = reverse('registration:oauth_callback', kwargs=kwargs)
        return urljoin(self.local_host, path)

    def get_login_uri(self):
        data = {'response_type': 'code',
                'scope': self.scope,
                'redirect_uri': self.get_redirect_uri(),
                'client_id': self.client_id}
        query = urlencode(data)
        return urljoin(self.auth_uri, url(query=query))

    def get_access_token(self, code):
        data = {'grant_type': 'authorization_code',
                'client_id': self.client_id,
                'client_secret': self.client_secret,
                'code': code,
                'redirect_uri': self.get_redirect_uri(),
                'scope': self.scope}
        response = self.post(self.token_uri, data=data, authorize=False)
        return response['access_token']

    def get_user_info(self):
        return self.get(self.user_info_uri)

    def get(self, address, params=None, authorize=True):
        auth = self.authorizer if authorize else None
        response = requests.get(address, params=params, auth=auth)
        return self.handle_response(response)

    def post(self, address, data=None, authorize=True):
        auth = self.authorizer if authorize else None
        response = requests.post(address, data=data, auth=auth)
        return self.handle_response(response)

    def handle_response(self, response):
        response_content = parse_response(response)
        if response.status_code == requests.codes.ok:
            return response_content
        else:
            logger.error('[%s]: %s', response.status_code, response.text)
            error = self.extract_error_from_response(response_content)
            raise ValueError(error)

    def extract_error_from_response(self, response_content):
        raise NotImplementedError()


class GoogleClient(OAuth2Client):

    service = GOOGLE

    auth_uri = 'https://accounts.google.com/o/oauth2/auth'
    token_uri = 'https://accounts.google.com/o/oauth2/token'
    user_info_uri = 'https://www.googleapis.com/oauth2/v1/userinfo'

    scope = ' '.join(['https://www.googleapis.com/auth/userinfo.email',
                      'https://www.googleapis.com/auth/plus.me'])

    def __init__(self, *args, **kwargs):
        super(GoogleClient, self).__init__(*args, **kwargs)
        if not self.client_id and self.client_secret:
            self.client_id = settings.GOOGLE_CLIENT_ID
            self.client_secret = settings.GOOGLE_CLIENT_SECRET

    def get_user_info(self):
        response = super(GoogleClient, self).get_user_info()
        if response['verified_email']:
            return response
        else:
            raise ValueError('Google account not verified.')

    def extract_error_from_response(self, response_content):
        return response_content['error']


class FacebookClient(OAuth2Client):

    service = FACEBOOK

    auth_uri = 'https://www.facebook.com/dialog/oauth'
    token_uri = 'https://graph.facebook.com/oauth/access_token'
    user_info_uri = 'https://graph.facebook.com/me'

    scope = ','.join(['email'])

    def __init__(self, *args, **kwargs):
        super(FacebookClient, self).__init__(*args, **kwargs)
        if not self.client_id and self.client_secret:
            self.client_id = settings.FACEBOOK_APP_ID
            self.client_secret = settings.FACEBOOK_SECRET

    def get_user_info(self):
        response = super(FacebookClient, self).get_user_info()
        if response['verified']:
            return response
        else:
            raise ValueError('Facebook account not verified.')

    def extract_error_from_response(self, response_content):
        return response_content['error']['message']

########NEW FILE########
__FILENAME__ = views
try:
    from urllib.parse import urlencode
except ImportError:
    from urllib import urlencode

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login as auth_login, logout as auth_logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import (
    login as django_login_view, password_change)
from django.core.urlresolvers import reverse
from django.shortcuts import redirect
from django.template.response import TemplateResponse
from django.utils import timezone
from django.utils.encoding import smart_text
from django.utils.translation import ugettext_lazy as _

from . import forms
from .models import EmailConfirmationRequest, EmailChangeRequest
from . import utils

now = timezone.now


def login(request):
    local_host = utils.get_local_host(request)
    ctx = {
        'facebook_login_url': utils.get_facebook_login_url(local_host),
        'google_login_url': utils.get_google_login_url(local_host)}
    return django_login_view(request, authentication_form=forms.LoginForm,
                             extra_context=ctx)


def logout(request):
    auth_logout(request)
    messages.success(request, _('You have been successfully logged out.'))
    return redirect(settings.LOGIN_REDIRECT_URL)


def oauth_callback(request, service):
    local_host = utils.get_local_host(request)
    form = forms.OAuth2CallbackForm(service=service, local_host=local_host,
                                    data=request.GET)
    if form.is_valid():
        try:
            user = form.get_authenticated_user()
        except ValueError as e:
            messages.error(request, smart_text(e))
        else:
            auth_login(request, user=user)
            messages.success(request, _('You are now logged in.'))
            return redirect(settings.LOGIN_REDIRECT_URL)
    else:
        for _field, errors in form.errors.items():
            for error in errors:
                messages.error(request, error)
    return redirect('registration:login')


def request_email_confirmation(request):
    local_host = utils.get_local_host(request)
    form = forms.RequestEmailConfirmationForm(local_host=local_host,
                                              data=request.POST or None)
    if form.is_valid():
        form.send()
        msg = _('Confirmation email has been sent. '
                'Please check your inbox.')
        messages.success(request, msg)
        return redirect(settings.LOGIN_REDIRECT_URL)

    return TemplateResponse(request,
                            'registration/request_email_confirmation.html',
                            {'form': form})


@login_required
def request_email_change(request):
    form = forms.RequestEmailChangeForm(
        local_host=utils.get_local_host(request), user=request.user,
        data=request.POST or None)
    if form.is_valid():
        form.send()
        msg = _('Confirmation email has been sent. '
                'Please check your inbox.')
        messages.success(request, msg)
        return redirect(settings.LOGIN_REDIRECT_URL)

    return TemplateResponse(
        request, 'registration/request_email_confirmation.html',
        {'form': form})


def confirm_email(request, token):
    if not request.POST:
        try:
            email_confirmation_request = EmailConfirmationRequest.objects.get(
                token=token, valid_until__gte=now())
            # TODO: cronjob (celery task) to delete stale tokens
        except EmailConfirmationRequest.DoesNotExist:
            return TemplateResponse(request, 'registration/invalid_token.html')
        user = email_confirmation_request.get_authenticated_user()
        email_confirmation_request.delete()
        auth_login(request, user)
        messages.success(request, _('You are now logged in.'))

    form = forms.SetOrRemovePasswordForm(user=request.user,
                                         data=request.POST or None)
    if form.is_valid():
        form.save()
        messages.success(request, _('Password has been successfully changed.'))
        return redirect(settings.LOGIN_REDIRECT_URL)

    return TemplateResponse(
        request, 'registration/set_password.html', {'form': form})


def change_email(request, token):
    try:
        email_change_request = EmailChangeRequest.objects.get(
            token=token, valid_until__gte=now())
            # TODO: cronjob (celery task) to delete stale tokens
    except EmailChangeRequest.DoesNotExist:
        return TemplateResponse(request, 'registration/invalid_token.html')

    # if another user is logged in, we need to log him out, to allow the email
    # owner confirm his identity
    if (request.user.is_authenticated() and
            request.user != email_change_request.user):
        auth_logout(request)
    if not request.user.is_authenticated():
        query = urlencode({
            'next': request.get_full_path(),
            'email': email_change_request.user.email})
        login_url = utils.url(path=settings.LOGIN_URL, query=query)
        return redirect(login_url)

    request.user.email = email_change_request.email
    request.user.save()
    email_change_request.delete()

    messages.success(request, _('Your email has been successfully changed'))
    return redirect(settings.LOGIN_REDIRECT_URL)


def change_password(request):
    return password_change(
        request, template_name='registration/change_password.html',
        post_change_redirect=reverse('profile:details'))

########NEW FILE########
__FILENAME__ = settings
import os.path

DEBUG = True
TEMPLATE_DEBUG = DEBUG

SITE_ID = 1

PROJECT_ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), '..'))

ROOT_URLCONF = 'saleor.urls'

WSGI_APPLICATION = 'saleor.wsgi.application'

ADMINS = (
    # ('Your Name', 'your_email@example.com'),
)
MANAGERS = ADMINS
INTERNAL_IPS = ['127.0.0.1']

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join(PROJECT_ROOT, 'dev.sqlite')
    }
}

TIME_ZONE = 'America/Chicago'
LANGUAGE_CODE = 'en-us'
USE_I18N = True
USE_L10N = True
USE_TZ = True

MEDIA_ROOT = os.path.join(PROJECT_ROOT, 'media')
MEDIA_URL = '/media/'

STATIC_ROOT = os.path.join(PROJECT_ROOT, 'static')
STATIC_URL = '/static/'
STATICFILES_DIRS = [
    os.path.join(PROJECT_ROOT, 'saleor', 'static')
]
STATICFILES_FINDERS = [
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder'
]

TEMPLATE_DIRS = [
    os.path.join(PROJECT_ROOT, 'templates')
]
TEMPLATE_LOADERS = [
    'django.template.loaders.filesystem.Loader',
    'django.template.loaders.app_directories.Loader',
    # TODO: this one is slow, but for now need for mptt?
    'django.template.loaders.eggs.Loader'
]

# Make this unique, and don't share it with anybody.
SECRET_KEY = '{{ secret_key }}'

MIDDLEWARE_CLASSES = [
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.locale.LocaleMiddleware',
    'babeldjango.middleware.LocaleMiddleware',
    'saleor.cart.middleware.CartMiddleware',
    'saleor.core.middleware.DiscountMiddleware',
    'saleor.core.middleware.GoogleAnalytics',
    'saleor.core.middleware.CheckHTML'
]

TEMPLATE_CONTEXT_PROCESSORS = [
    'django.contrib.auth.context_processors.auth',
    'django.core.context_processors.debug',
    'django.core.context_processors.i18n',
    'django.core.context_processors.media',
    'django.core.context_processors.static',
    'django.core.context_processors.tz',
    'django.contrib.messages.context_processors.messages',
    'django.core.context_processors.request',
    'saleor.core.context_processors.canonical_hostname',
    'saleor.core.context_processors.default_currency'
]

INSTALLED_APPS = [
    # External apps that need to go before django's

    # Django modules
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.webdesign',

    # Local apps
    'saleor.cart',
    'saleor.checkout',
    'saleor.core',
    'saleor.product',
    'saleor.order',
    'saleor.registration',
    'saleor.userprofile',

    # External apps
    'babeldjango',
    'django_images',
    'django_prices',
    'mptt',
    'payments',
    'selectable'
]

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '%(levelname)s %(asctime)s %(module)s '
            '%(process)d %(thread)d %(message)s'
        },
        'simple': {
            'format': '%(levelname)s %(message)s'
        },
    },
    'filters': {
        'require_debug_false': {
            '()': 'django.utils.log.RequireDebugFalse'
        },
        'require_debug_true': {
            '()': 'django.utils.log.RequireDebugTrue'
        }
    },
    'handlers': {
        'mail_admins': {
            'level': 'ERROR',
            'filters': ['require_debug_false'],
            'class': 'django.utils.log.AdminEmailHandler'
        },
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'filters': ['require_debug_true'],
            'formatter': 'simple'
        },
    },
    'loggers': {
        'django.request': {
            'handlers': ['mail_admins'],
            'level': 'ERROR',
            'propagate': True
        },
        'saleor': {
            'handlers': ['console'],
            'level': 'DEBUG',
            'propagate': True
        }
    }
}

AUTHENTICATION_BACKENDS = (
    'saleor.registration.backends.EmailPasswordBackend',
    'saleor.registration.backends.ExternalLoginBackend',
    'saleor.registration.backends.TrivialBackend'
)

AUTH_USER_MODEL = 'userprofile.User'

CANONICAL_HOSTNAME = 'localhost:8000'

IMAGE_SIZES = {
    'normal': {
        'size': (750, 0)
    },
    'small': {
        'size': (280, 280),
        'crop': True
    },
    'admin': {
        'size': (50, 50),
        'crop': True
    }
}

EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

LOGIN_URL = '/account/login'

WARN_ABOUT_INVALID_HTML5_OUTPUT = False

DEFAULT_CURRENCY = 'USD'

ACCOUNT_ACTIVATION_DAYS = 3

LOGIN_REDIRECT_URL = 'home'

FACEBOOK_APP_ID = None
FACEBOOK_SECRET = None

GOOGLE_ANALYTICS_TRACKING_ID = None
GOOGLE_CLIENT_ID = None
GOOGLE_CLIENT_SECRET = None

PAYMENT_BASE_URL = 'http://%s/' % CANONICAL_HOSTNAME

PAYMENT_MODEL = 'order.Payment'

PAYMENT_VARIANTS = {
    'default': ('payments.dummy.DummyProvider', {})
}

SESSION_SERIALIZER = 'django.contrib.sessions.serializers.JSONSerializer'

CHECKOUT_PAYMENT_CHOICES = [
    ('default', 'Dummy provider')
]

TEMPLATE_STRING_IF_INVALID = '<< MISSING VARIABLE >>'

########NEW FILE########
__FILENAME__ = tests
from unittest import TestSuite, TestLoader

import django

if hasattr(django, 'setup'):
    django.setup()

TEST_MODULES = [
    'saleor.cart.tests',
    'saleor.checkout.tests',
    'saleor.communication.tests',
    'saleor.core.tests',
    #'saleor.delivery.tests',
    'saleor.order.tests',
    #'saleor.payment.tests',
    #'saleor.product.tests',
    'saleor.registration.tests',
    'saleor.userprofile.tests']

suite = TestSuite()
loader = TestLoader()
for module in TEST_MODULES:
    suite.addTests(loader.loadTestsFromName(module))

########NEW FILE########
__FILENAME__ = test_settings
from .settings import *

SECRET_KEY = 'NOTREALLY'

########NEW FILE########
__FILENAME__ = urls
from django.conf import settings
from django.conf.urls import patterns, url, include
from django.contrib import admin


from .cart.urls import urlpatterns as cart_urls
from .checkout.urls import urlpatterns as checkout_urls
from .core.urls import urlpatterns as core_urls
from .order.urls import urlpatterns as order_urls
from .product.urls import urlpatterns as product_urls
from .registration.urls import urlpatterns as registration_urls
from .userprofile.urls import urlpatterns as userprofile_urls


admin.autodiscover()

urlpatterns = patterns(
    '',
    url(r'^$', include(core_urls), name='home'),
    url(r'^account/', include(registration_urls, namespace='registration')),
    url(r'^admin/', include(admin.site.urls)),
    url(r'^cart/', include(cart_urls, namespace='cart')),
    url(r'^checkout/', include(checkout_urls, namespace='checkout')),
    url(r'^images/', include('django_images.urls')),
    url(r'^order/', include(order_urls, namespace='order')),
    url(r'^products/', include(product_urls, namespace='product')),
    url(r'^profile/', include(userprofile_urls, namespace='profile')),
    url(r'^selectable/', include('selectable.urls')),
    url(r'', include('payments.urls'))
)

if settings.DEBUG:
    # static files (images, css, javascript, etc.)
    urlpatterns += patterns(
        '',
        url(r'^media/(?P<path>.*)$', 'django.views.static.serve',
            {'document_root': settings.MEDIA_ROOT}))

########NEW FILE########
__FILENAME__ = admin
from django.contrib import admin
from .models import User, AddressBook


class AddressAdmin(admin.TabularInline):

    model = AddressBook


class UserAdmin(admin.ModelAdmin):

    inlines = [AddressAdmin]


admin.site.register(User, UserAdmin)

########NEW FILE########
__FILENAME__ = forms
from django import forms
from django.utils.translation import ugettext as _

from .models import Address, AddressBook


class AddressForm(forms.ModelForm):

    class Meta:
        model = Address


class AddressBookForm(forms.ModelForm):

    class Meta:
        model = AddressBook
        fields = ['alias']

    def clean(self):
        super(AddressBookForm, self).clean()
        if AddressBook.objects.filter(
            user_id=self.instance.user_id, alias=self.cleaned_data.get('alias')
        ).exclude(address=self.instance.address_id).exists():
            self._errors['alias'] = self.error_class(
                [_('You are already using such alias for another address')])

        return self.cleaned_data

########NEW FILE########
__FILENAME__ = changepassword
from django.contrib.auth.management.commands.changepassword import Command

__all__ = ['Command']

########NEW FILE########
__FILENAME__ = createsuperuser
from django.contrib.auth.management.commands.createsuperuser import Command

__all__ = ['Command']

########NEW FILE########
__FILENAME__ = models
from __future__ import unicode_literals
import re

from django.contrib.auth.hashers import (check_password, make_password,
                                         is_password_usable)
from django.contrib.auth.models import BaseUserManager
from django.db import models
from django.forms.models import model_to_dict
from django.utils import timezone
from django.utils.encoding import python_2_unicode_compatible
from django.utils.safestring import mark_safe
from django.utils.translation import pgettext_lazy
from unidecode import unidecode

from ..core.countries import COUNTRY_CHOICES


class AddressBookManager(models.Manager):

    def store_address(self, user, address, alias):
        data = Address.objects.as_data(address)
        query = dict(('address__%s' % (key,), value)
                     for key, value in data.items())
        candidates = self.get_queryset().filter(user=user, **query)
        candidates = candidates.select_for_update()
        try:
            entry = candidates[0]
        except IndexError:
            address = Address.objects.create(**data)
            entry = AddressBook.objects.create(user=user, address=address,
                                               alias=alias)
        return entry


@python_2_unicode_compatible
class AddressBook(models.Model):

    user = models.ForeignKey('User', related_name='address_book')
    address = models.ForeignKey('Address', related_name='+', unique=True)
    alias = models.CharField(
        pgettext_lazy('Address book entry', 'short alias'),
        max_length=30,
        default='Home',
        help_text=pgettext_lazy(
            'Address book entry',
            'A short, descriptive name for this address'))

    objects = AddressBookManager()

    class Meta:
        unique_together = ('user', 'alias')

    def __str__(self):
        return self.alias

    @models.permalink
    def get_absolute_url(self):
        return ('profile:address-edit',
                (),
                {'slug': self.get_slug(), 'pk': self.id})

    def get_slug(self):
        value = unidecode(self.alias)
        value = re.sub(r'[^\w\s-]', '', value).strip().lower()

        return mark_safe(re.sub(r'[-\s]+', '-', value))


class AddressManager(models.Manager):

    def as_data(self, addr):
        return model_to_dict(addr, exclude=['id', 'user'])

    def are_identical(self, addr1, addr2):
        data1 = self.as_data(addr1)
        data2 = self.as_data(addr2)
        return data1 == data2


@python_2_unicode_compatible
class Address(models.Model):

    name = models.CharField(
        pgettext_lazy('Address field', 'name'), max_length=256)
    city = models.CharField(
        pgettext_lazy('Address field', 'city'), max_length=256)
    street_address = models.CharField(
        pgettext_lazy('Address field', 'street address'), max_length=256)
    postal_code = models.CharField(
        pgettext_lazy('Address field', 'postal code'), max_length=20)
    country = models.CharField(
        pgettext_lazy('Address field', 'country'),
        choices=COUNTRY_CHOICES, max_length=2)
    phone = models.CharField(
        pgettext_lazy('Address field', 'phone number'),
        max_length=30, blank=True)

    objects = AddressManager()

    def __str__(self):
        return self.name

    def __repr__(self):
        return (
            'Address(name=%r, street_address=%r, city=%r, postal_code=%r,'
            ' country=%r, phone=%r)' % (
                self.name, self.street_address, self.city, self.postal_code,
                self.country, self.phone))


class UserManager(BaseUserManager):

    def get_or_create(self, **kwargs):
        defaults = kwargs.pop('defaults', {})
        try:
            return self.get_query_set().get(**kwargs), False
        except self.model.DoesNotExist:
            defaults.update(kwargs)
            return self.create_user(**defaults), True

    def create_user(self, email, password=None, is_staff=False,
                    is_active=True, **extra_fields):
        'Creates a User with the given username, email and password'
        email = UserManager.normalize_email(email)
        user = self.model(email=email, is_active=is_active,
                          is_staff=is_staff, **extra_fields)
        if password:
            user.set_password(password)
        user.save()
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        return self.create_user(email, password, is_staff=True, **extra_fields)

    def store_address(self, user, address, alias,
                      billing=False, shipping=False):
        entry = AddressBook.objects.store_address(user, address, alias)
        changed = False
        if billing and not user.default_billing_address_id:
            user.default_billing_address = entry
            changed = True
        if shipping and not user.default_shipping_address_id:
            user.default_shipping_address = entry
            changed = True
        if changed:
            user.save()


@python_2_unicode_compatible
class User(models.Model):
    email = models.EmailField(unique=True)

    addresses = models.ManyToManyField(Address, through=AddressBook)

    is_staff = models.BooleanField(
        pgettext_lazy('User field', 'staff status'),
        default=False)
    is_active = models.BooleanField(
        pgettext_lazy('User field', 'active'),
        default=False)
    password = models.CharField(
        pgettext_lazy('User field', 'password'),
        max_length=128, editable=False)
    date_joined = models.DateTimeField(
        pgettext_lazy('User field', 'date joined'),
        default=timezone.now, editable=False)
    last_login = models.DateTimeField(
        pgettext_lazy('User field', 'last login'),
        default=timezone.now, editable=False)
    default_shipping_address = models.ForeignKey(
        AddressBook, related_name='+', null=True, blank=True,
        on_delete=models.SET_NULL,
        verbose_name=pgettext_lazy('User field', 'default shipping address'))
    default_billing_address = models.ForeignKey(
        AddressBook, related_name='+', null=True, blank=True,
        on_delete=models.SET_NULL,
        verbose_name=pgettext_lazy('User field', 'default billing address'))

    USERNAME_FIELD = 'email'

    REQUIRED_FIELDS = []

    objects = UserManager()

    def __str__(self):
        return self.get_username()

    def natural_key(self):
        return (self.get_username(),)

    def get_full_name(self):
        return self.email

    def get_short_name(self):
        return self.email

    def has_perm(self, *_args, **_kwargs):
        return True

    def has_perms(self, *_args, **_kwargs):
        return True

    def has_module_perms(self, _app_label):
        return True

    def get_username(self):
        'Return the identifying username for this User'
        return self.email

    def is_anonymous(self):
        return False

    def is_authenticated(self):
        return True

    def set_password(self, raw_password):
        self.password = make_password(raw_password)

    def check_password(self, raw_password):
        def setter(raw_password):
            self.set_password(raw_password)
            self.save(update_fields=['password'])
        return check_password(raw_password, self.password, setter)

    def set_unusable_password(self):
        self.password = make_password(None)

    def has_usable_password(self):
        return is_password_usable(self.password)

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
from django.conf.urls import patterns, url

from . import views


urlpatterns = patterns(
    '',
    url(r'^$', views.details, name='details'),
    url(r'^orders/$', views.orders, name='orders'),
    url(r'^address/create/$', views.address_create,
        name='address-create'),
    url(r'^address/(?P<slug>[\w-]+)-(?P<pk>\d+)/edit/$', views.address_edit,
        name='address-edit'),
    url(r'^address/(?P<slug>[\w-]+)-(?P<pk>\d+)/delete/$',
        views.address_delete, name='address-delete'),
    url(r'^address/(?P<pk>\d+)/make-default-for-'
        r'(?P<purpose>billing|shipping)/$', views.address_make_default,
        name='address-make-default')
)

########NEW FILE########
__FILENAME__ = views
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect, Http404
from django.shortcuts import get_object_or_404, redirect
from django.template.response import TemplateResponse
from django.views.decorators.http import require_POST
from django.utils.translation import ugettext as _

from .models import AddressBook, Address
from .forms import AddressBookForm, AddressForm


@login_required
def details(request):

    ctx = {'address_book': request.user.address_book.all()}
    return TemplateResponse(request, 'userprofile/details.html', ctx)


@login_required
def orders(request):

    ctx = {'orders': request.user.orders.prefetch_related('groups')}
    return TemplateResponse(request, 'userprofile/orders.html', ctx)


def validate_address_and_render(request, address_form, address_book_form,
                                success_message):
    if address_form.is_valid() and address_book_form.is_valid():
        address = address_form.save()
        address_book_form.instance.address = address
        address_book_form.save()
        messages.success(request, success_message)
        return HttpResponseRedirect(reverse('profile:details'))

    return TemplateResponse(
        request,
        'userprofile/address-edit.html',
        {'address_form': address_form, 'address_book_form': address_book_form})


@login_required
def address_edit(request, slug, pk):

    address_book = get_object_or_404(AddressBook, pk=pk, user=request.user)
    address = address_book.address

    if not address_book.get_slug() == slug and request.method == 'GET':
        return HttpResponseRedirect(address_book.get_absolute_url())

    address_form = AddressForm(request.POST or None, instance=address)
    address_book_form = AddressBookForm(
        request.POST or None, instance=address_book)

    message = _('Address successfully updated.')

    return validate_address_and_render(
        request, address_form, address_book_form, success_message=message)


@login_required
def address_create(request):

    address_form = AddressForm(request.POST or None)
    address_book_form = AddressBookForm(
        request.POST or None, instance=AddressBook(user=request.user))

    message = _('Address successfully created.')

    is_first_address = not Address.objects.exists()
    response = validate_address_and_render(
        request, address_form, address_book_form, success_message=message)
    address_book = address_book_form.instance
    if address_book.pk and is_first_address:
        user = request.user
        user.default_shipping_address = address_book
        user.default_billing_address = address_book
        user.save(update_fields=[
            'default_shipping_address', 'default_billing_address'])
    return response


@login_required
def address_delete(request, slug, pk):

    address_book = get_object_or_404(AddressBook, pk=pk, user=request.user)

    if not address_book.get_slug() == slug:
        raise Http404

    if request.method == 'POST':
        address_book.address.delete()
        messages.success(request, _('Address successfully deleted.'))
        return HttpResponseRedirect(reverse('profile:details'))

    return TemplateResponse(request, 'userprofile/address-delete.html',
                            context={'object': address_book})


@login_required
@require_POST
def address_make_default(request, pk, purpose):
    user = request.user

    address_book = get_object_or_404(AddressBook, pk=pk, user=user)
    if purpose == 'shipping':
        user.default_shipping_address = address_book
        user.save(update_fields=['default_shipping_address'])
    elif purpose == 'billing':
        user.default_billing_address = address_book
        user.save(update_fields=['default_billing_address'])
    else:
        raise AssertionError(
            '``purpose`` should be ``billing`` or ``shipping``')

    return redirect('profile:details')

########NEW FILE########
__FILENAME__ = wsgi
"""
WSGI config for saleor project.

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

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "saleor.settings")

# This application object is used by any WSGI server configured to use this
# file. This includes Django's development server, if the WSGI_APPLICATION
# setting points here.
from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()

# Apply WSGI middleware here.
# from helloworld.wsgi import HelloWorldApplication
# application = HelloWorldApplication(application)

########NEW FILE########
__FILENAME__ = create_random_data
from __future__ import unicode_literals
import random
import os

from faker import Factory
from django.core.files import File

from saleor.product.models import (Shirt, ShirtVariant,
                                   Bag, BagVariant, ProductImage)
from saleor.product.models import Category, Color


fake = Factory.create()
PRODUCT_COLLECTIONS = fake.words(10)


def create_color(**kwargs):
    r = lambda: random.randint(0, 255)

    defaults = {
        'name': fake.word(),
        'color': '%02X%02X%02X' % (r(), r(), r())
    }
    defaults.update(kwargs)

    return Color.objects.create(**defaults)


def get_or_create_category(name, **kwargs):
    defaults = {
        'description': fake.text()
    }
    defaults.update(kwargs)
    defaults['slug'] = fake.slug(name)

    return Category.objects.get_or_create(name=name, defaults=defaults)[0]


def create_product(product_type, **kwargs):
    if random.choice([True, False]):
        collection = random.choice(PRODUCT_COLLECTIONS)
    else:
        collection = ''

    defaults = {
        'name': fake.company(),
        'price': fake.pyfloat(2, 2, positive=True),
        'category': Category.objects.order_by('?')[0],
        'collection': collection,
        'color': Color.objects.order_by('?')[0],
        'weight': fake.random_digit(),
        'description': '\n\n'.join(fake.paragraphs(5))
    }
    defaults.update(kwargs)

    return product_type.objects.create(**defaults)


def create_variant(product, **kwargs):
    defaults = {
        'stock': fake.random_int(),
        'name': fake.word(),
        'sku': fake.random_int(1, 100000),
        'product': product
    }
    if isinstance(product, Shirt):
        if not 'size' in kwargs:
            defaults['size'] = random.choice(ShirtVariant.SIZE_CHOICES)[0]
        variant_class = ShirtVariant
    elif isinstance(product, Bag):
        variant_class = BagVariant
    else:
        raise NotImplemented
    defaults.update(kwargs)

    return variant_class.objects.create(**defaults)


def create_product_image(product, placeholder_dir):
    img_path = "%s/%s" % (placeholder_dir,
                          random.choice(os.listdir(placeholder_dir)))
    image = ProductImage(
        product=product,
        image=File(open(img_path, 'rb'))
    ).save()

    return image


def create_product_images(product, how_many, placeholder_dir):
    for i in range(how_many):
        create_product_image(product, placeholder_dir)


def create_shirt(**kwargs):
    return create_product(Shirt, **kwargs)


def create_bag(**kwargs):
    return create_product(Bag, **kwargs)


def create_items(placeholder_dir, how_many=10):
    # Create few colors
    [create_color() for i in range(5)]

    shirt_category = get_or_create_category('Shirts')
    bag_category = get_or_create_category('Grocery bags')

    for i in range(how_many):
        # Shirt
        shirt = create_shirt(category=shirt_category)
        create_product_images(shirt, random.randrange(1, 5),
                              placeholder_dir + "shirts")
        # Bag
        bag = create_bag(category=bag_category, collection='')
        create_product_images(bag, random.randrange(1, 5),
                              placeholder_dir + "bags")
        # chance to generate couple of sizes
        for size in ShirtVariant.SIZE_CHOICES:
            # Create min. one size
            if shirt.variants.count() == 0:
                create_variant(shirt, size=size[0])
                continue
            if random.choice([True, False]):
                create_variant(shirt, size=size[0])

        create_variant(bag)

        yield "Shirt - %s %s Variants" % (shirt, shirt.variants.count())
        yield "Bag - %s %s Variants" % (bag, bag.variants.count())

########NEW FILE########
