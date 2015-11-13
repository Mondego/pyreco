__FILENAME__ = cart
from decimal import Decimal

from carton import settings as carton_settings
from carton.module_loading import get_product_model


class CartItem(object):
    """
    A cart item, with the associated product, its quantity and its price.
    """
    def __init__(self, product, quantity, price):
        self.product = product
        self.quantity = int(quantity)
        self.price = Decimal(str(price))

    def __repr__(self):
        return u'CartItem Object (%s)' % self.product

    def to_dict(self):
        return {
            'product_pk': self.product.pk,
            'quantity': self.quantity,
            'price': str(self.price),
        }

    @property
    def subtotal(self):
        """
        Subtotal for the cart item.
        """
        return self.price * self.quantity


class Cart(object):
    queryset = None
    
    """
    A cart that lives in the session.
    """
    def __init__(self, session, session_key=None, product_model=None):
        self._items_dict = {}
        self.session = session
        self.session_key = session_key or carton_settings.CART_SESSION_KEY
        self.product_model = product_model
        if self.session_key in self.session:
            # If a cart representation was previously stored in session, then we
            # rebuild the cart object from that serialized representation.
            cart_representation = self.session[self.session_key]
            ids_in_cart = cart_representation.keys()
            products_queryset = self.get_queryset().filter(pk__in=ids_in_cart)
            for product in products_queryset:
                item = cart_representation[str(product.pk)]
                self._items_dict[product.pk] = CartItem(
                    product, item['quantity'], Decimal(item['price'])
                )

    def __contains__(self, product):
        """
        Checks if the given product is in the cart.
        """
        return product in self.products

    def get_queryset(self):
        if self.queryset is not None:
            return self.queryset
        product_model = self.product_model or get_product_model()
        return product_model._default_manager.all()

    def update_session(self):
        """
        Serializes the cart data, saves it to session and marks session as modified.
        """
        self.session[self.session_key] = self.cart_serializable
        self.session.modified = True

    def add(self, product, price=None, quantity=1):
        """
        Adds or creates products in cart. For an existing product,
        the quantity is increased and the price is ignored.
        """
        quantity = int(quantity)
        if quantity < 1:
            raise ValueError('Quantity must be at least 1 when adding to cart')
        if product in self.products:
            self._items_dict[product.pk].quantity += quantity
        else:
            if price == None:
                raise ValueError('Missing price when adding to cart')
            self._items_dict[product.pk] = CartItem(product, quantity, price)
        self.update_session()

    def remove(self, product):
        """
        Removes the product.
        """
        if product in self.products:
            del self._items_dict[product.pk]
            self.update_session()

    def remove_single(self, product):
        """
        Removes a single product by decreasing the quantity.
        """
        if product in self.products:
            if self._items_dict[product.pk].quantity <= 1:
                # There's only 1 product left so we drop it
                del self._items_dict[product.pk]
            else:
                self._items_dict[product.pk].quantity -= 1
            self.update_session()

    def clear(self):
        """
        Removes all items.
        """
        self._items_dict = {}
        self.update_session()

    def set_quantity(self, product, quantity):
        """
        Sets the product's quantity.
        """
        quantity = int(quantity)
        if quantity < 0:
            raise ValueError('Quantity must be positive when updating cart')
        if product in self.products:
            self._items_dict[product.pk].quantity = quantity
            if self._items_dict[product.pk].quantity < 1:
                del self._items_dict[product.pk]
            self.update_session()

    @property
    def items(self):
        """
        The list of cart items.
        """
        return self._items_dict.values()

    @property
    def cart_serializable(self):
        """
        The serializable representation of the cart.
        For instance:
        {
            '1': {'product_pk': 1, 'quantity': 2, price: '9.99'},
            '2': {'product_pk': 2, 'quantity': 3, price: '29.99'},
        }
        Note how the product pk servers as the dictionary key.
        """
        cart_representation = {}
        for item in self.items:
            # JSON serialization: object attribute should be a string
            product_id = str(item.product.pk)
            cart_representation[product_id] = item.to_dict()
        return cart_representation


    @property
    def items_serializable(self):
        """
        The list of items formatted for serialization.
        """
        return self.cart_serializable.items()

    @property
    def count(self):
        """
        The number of items in cart, that's the sum of quantities.
        """
        return sum([item.quantity for item in self.items])

    @property
    def unique_count(self):
        """
        The number of unique items in cart, regardless of the quantity.
        """
        return len(self._items_dict)

    @property
    def is_empty(self):
        return self.unique_count == 0

    @property
    def products(self):
        """
        The list of associated products.
        """
        return [item.product for item in self.items]

    @property
    def total(self):
        """
        The total value of all items in the cart.
        """
        return sum([item.subtotal for item in self.items])

########NEW FILE########
__FILENAME__ = models

########NEW FILE########
__FILENAME__ = module_loading
from django.conf import settings
from django.utils.importlib import import_module


def get_product_model():
    """
    Returns the product model that is used by this cart.
    """
    package, module = settings.CART_PRODUCT_MODEL.rsplit('.', 1)
    return getattr(import_module(package), module)

########NEW FILE########
__FILENAME__ = settings
from django.conf import settings

CART_SESSION_KEY = getattr(settings, 'CART_SESSION_KEY', 'CART')

CART_TEMPLATE_TAG_NAME = getattr(settings, 'CART_TEMPLATE_TAG_NAME', 'get_cart')

########NEW FILE########
__FILENAME__ = carton_tags
from django import template

from carton.cart import Cart
from carton.settings import CART_TEMPLATE_TAG_NAME

register = template.Library()

def get_cart(context, session_key=None, product_model=None, cart_class=Cart):
    """
    Make the cart object available in template.

    Sample usage::

        {% load carton_tags %}
        {% get_cart as cart %}
        {% for product in cart.products %}
            {{ product }}
        {% endfor %}
    """
    request = context['request']
    return cart_class(request.session, session_key=session_key, product_model=product_model)

register.assignment_tag(takes_context=True, name=CART_TEMPLATE_TAG_NAME)(get_cart)

########NEW FILE########
__FILENAME__ = models
from django.db import models


class Product(models.Model):
    custom_id = models.IntegerField(primary_key=True)
    name = models.CharField(max_length=255)
    price = models.FloatField()

    def __unicode__(self):
        return self.name

########NEW FILE########
__FILENAME__ = settings
SITE_ID = 1

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': 'carton-tests.db',
    }
}

INSTALLED_APPS = (
    'django.contrib.sessions',
    'django.contrib.sites',
    'carton',
    'carton.tests',
)

ROOT_URLCONF = 'carton.tests.urls'

SECRET_KEY = 'any-key'

CART_PRODUCT_MODEL = 'carton.tests.models.Product'

########NEW FILE########
__FILENAME__ = tests
from django.core.urlresolvers import reverse
from django.test import TestCase

from carton.tests.models import Product


class CartTests(TestCase):

    def setUp(self):
        self.deer = Product.objects.create(name='deer', price=10.0, custom_id=1)
        self.moose = Product.objects.create(name='moose', price=20.0, custom_id=2)
        self.url_add = reverse('carton-tests-add')
        self.url_show = reverse('carton-tests-show')
        self.url_remove = reverse('carton-tests-remove')
        self.url_remove_single = reverse('carton-tests-remove-single')
        self.url_quantity = reverse('carton-tests-set-quantity')
        self.url_clear = reverse('carton-tests-clear')
        self.deer_data = {'product_id': self.deer.pk}
        self.moose_data = {'product_id': self.moose.pk}

    def test_product_is_added(self):
        self.client.post(self.url_add, self.deer_data)
        response = self.client.get(self.url_show)
        self.assertContains(response, '1 deer for $10.0')

    def test_multiple_products_are_added(self):
        self.client.post(self.url_add, self.deer_data)
        self.client.post(self.url_add, self.moose_data)
        response = self.client.get(self.url_show)
        self.assertContains(response, '1 deer for $10.0')
        self.assertContains(response, '1 moose for $20.0')

    def test_stale_item_is_removed_from_cart(self):
        # Items that are not anymore reference in the database should not be kept in cart.
        self.client.post(self.url_add, self.deer_data)
        self.client.post(self.url_add, self.moose_data)
        response = self.client.get(self.url_show)
        self.assertContains(response, 'deer')
        self.assertContains(response, 'moose')
        self.deer.delete()
        response = self.client.get(self.url_show)
        self.assertNotContains(response, 'deer')
        self.assertContains(response, 'moose')

    def test_quantity_increases(self):
        self.client.post(self.url_add, self.deer_data)
        self.deer_data['quantity'] = 2
        self.client.post(self.url_add, self.deer_data)
        response = self.client.get(self.url_show)
        self.assertContains(response, '3 deer')

    def test_items_are_counted_properly(self):
        self.deer_data['quantity'] = 2
        self.client.post(self.url_add, self.deer_data)
        self.client.post(self.url_add, self.moose_data)
        response = self.client.get(self.url_show)
        self.assertContains(response, 'items count: 3')
        self.assertContains(response, 'unique count: 2')

    def test_price_is_updated(self):
        # Let's give a discount: $1.5/product. That's handled on the test views.
        self.deer_data['quantity'] = 2
        self.deer_data['discount'] = 1.5
        self.client.post(self.url_add, self.deer_data)
        response = self.client.get(self.url_show)
        # subtotal = 10*2 - 1.5*2
        self.assertContains(response, '2 deer for $17.0')

    def test_products_are_removed_all_together(self):
        self.deer_data['quantity'] = 3
        self.client.post(self.url_add, self.deer_data)
        self.client.post(self.url_add, self.moose_data)
        remove_data = {'product_id': self.deer.pk}
        self.client.post(self.url_remove, remove_data)
        response = self.client.get(self.url_show)
        self.assertNotContains(response, 'deer')
        self.assertContains(response, 'moose')

    def test_single_product_is_removed(self):
        self.deer_data['quantity'] = 3
        self.client.post(self.url_add, self.deer_data)
        remove_data = {'product_id': self.deer.pk}
        self.client.post(self.url_remove_single, remove_data)
        response = self.client.get(self.url_show)
        self.assertContains(response, '2 deer')

    def test_quantity_is_overwritten(self):
        self.deer_data['quantity'] = 3
        self.client.post(self.url_add, self.deer_data)
        self.deer_data['quantity'] = 4
        self.client.post(self.url_quantity, self.deer_data)
        response = self.client.get(self.url_show)
        self.assertContains(response, '4 deer')

    def test_cart_items_are_cleared(self):
        self.client.post(self.url_add, self.deer_data)
        self.client.post(self.url_add, self.moose_data)
        self.client.post(self.url_clear)
        response = self.client.get(self.url_show)
        self.assertNotContains(response, 'deer')
        self.assertNotContains(response, 'moose')

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls import url, patterns


urlpatterns = patterns('carton.tests.views',
    url(r'^show/$', 'show', name='carton-tests-show'),
    url(r'^add/$', 'add', name='carton-tests-add'),
    url(r'^remove/$', 'remove', name='carton-tests-remove'),
    url(r'^remove-single/$', 'remove_single', name='carton-tests-remove-single'),
    url(r'^clear/$', 'clear', name='carton-tests-clear'),
    url(r'^set-quantity/$', 'set_quantity', name='carton-tests-set-quantity'),
)

########NEW FILE########
__FILENAME__ = views
from django.http import HttpResponse

from carton.cart import Cart
from carton.tests.models import Product


def show(request):
    cart = Cart(request.session)
    response = ''
    for item in cart.items:
        response += '%(quantity)s %(item)s for $%(price)s\n' % {
            'quantity': item.quantity,
            'item': item.product.name,
            'price': item.subtotal,
        }
        response += 'items count: %s\n' % cart.count
        response += 'unique count: %s\n' % cart.unique_count
    return HttpResponse(response)


def add(request):
    cart = Cart(request.session)
    product = Product.objects.get(pk=request.POST.get('product_id'))
    quantity = request.POST.get('quantity', 1)
    discount = request.POST.get('discount', 0)
    price = product.price - float(discount)
    cart.add(product, price, quantity)
    return HttpResponse()


def remove(request):
    cart = Cart(request.session)
    product = Product.objects.get(pk=request.POST.get('product_id'))
    cart.remove(product)
    return HttpResponse()


def remove_single(request):
    cart = Cart(request.session)
    product = Product.objects.get(pk=request.POST.get('product_id'))
    cart.remove_single(product)
    return HttpResponse()


def clear(request):
    cart = Cart(request.session)
    cart.clear()
    return HttpResponse()


def set_quantity(request):
    cart = Cart(request.session)
    product = Product.objects.get(pk=request.POST.get('product_id'))
    quantity = request.POST.get('quantity')
    cart.set_quantity(product, quantity)
    return HttpResponse()

########NEW FILE########
__FILENAME__ = models

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import url, patterns


urlpatterns = patterns('shopping.views',
    url(r'^add/$', 'add', name='shopping-cart-add'),
    url(r'^remove/$', 'remove', name='shopping-cart-remove'),
    url(r'^show/$', 'show', name='shopping-cart-show'),
)


########NEW FILE########
__FILENAME__ = views
from django.http import HttpResponse
from django.shortcuts import render

from carton.cart import Cart
from products.models import Product


def add(request):
    cart = Cart(request.session)
    product = Product.objects.get(id=request.GET.get('id'))
    cart.add(product, price=product.price)
    return HttpResponse("Added")


def remove(request):
    cart = Cart(request.session)
    product = Product.objects.get(id=request.GET.get('id'))
    cart.remove(product)
    return HttpResponse("Removed")


def show(request):
    return render(request, 'shopping/show-cart.html')

########NEW FILE########
