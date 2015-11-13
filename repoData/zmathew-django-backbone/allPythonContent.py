__FILENAME__ = models

########NEW FILE########
__FILENAME__ = serializers
from StringIO import StringIO

from django.core.serializers.python import Serializer as PythonSerializer
from django.db.models.fields import FieldDoesNotExist


class AllFieldsSerializer(PythonSerializer):
    """
    Supports serialization of fields on the model that are inherited (ie. non-local fields).
    """

    # Copied from django.core.serializers.base
    # Unfortunately, django's serializer only serializes local fields
    # NOTE: This differs from django's serializer as it REQUIRES `fields` to be specified.
    def serialize(self, queryset, fields, **options):
        """
        Serialize a queryset.
        """
        self.options = options

        self.stream = options.pop("stream", StringIO())
        self.selected_fields = fields
        self.use_natural_keys = options.pop("use_natural_keys", False)

        self.start_serialization()

        for obj in queryset:
            self.start_object(obj)
            for field_name in self.selected_fields:
                try:
                    field = obj._meta.get_field(field_name)
                except FieldDoesNotExist:
                    continue

                if field in obj._meta.many_to_many:
                    self.handle_m2m_field(obj, field)
                elif field.rel is not None:
                    self.handle_fk_field(obj, field)
                else:
                    self.handle_field(obj, field)
            self.end_object(obj)

        self.end_serialization()
        return self.getvalue()

########NEW FILE########
__FILENAME__ = sites
class BackboneSite(object):

    def __init__(self, name='backbone'):
        self._registry = []
        self.name = name

    def register(self, backbone_view_class):
        """
        Registers the given backbone view class.
        """
        if backbone_view_class not in self._registry:
            self._registry.append(backbone_view_class)

    def unregister(self, backbone_view_class):
        if backbone_view_class in self._registry:
            self._registry.remove(backbone_view_class)

    def get_urls(self):
        from django.conf.urls import patterns, url

        urlpatterns = patterns('')
        for view_class in self._registry:
            app_label = view_class.model._meta.app_label
            url_slug = view_class.url_slug or view_class.model._meta.module_name

            url_path_prefix = r'^%s/%s' % (app_label, url_slug)
            base_url_name = '%s_%s' % (app_label, url_slug)

            urlpatterns += patterns('',
                url(url_path_prefix + '$', view_class.as_view(), name=base_url_name),
                url(url_path_prefix + '/(?P<id>\d+)$', view_class.as_view(),
                    name=base_url_name + '_detail')
            )
        return urlpatterns

    @property
    def urls(self):
        return (self.get_urls(), 'backbone', self.name)

########NEW FILE########
__FILENAME__ = admin
from django.contrib import admin

from backbone.tests.models import Product, Brand


admin.site.register(Product)
admin.site.register(Brand)

########NEW FILE########
__FILENAME__ = backbone_api
import backbone
from backbone.views import BackboneAPIView
from backbone.tests.forms import BrandForm
from backbone.tests.models import Product, Brand, ExtendedProduct, DisplayFieldsProduct


class ProductBackboneView(BackboneAPIView):
    def sku(obj):
        return '#: %s' % obj.sku

    model = Product
    display_fields = (
        'creation_date', 'name', 'brand', 'categories', 'price', 'order',
        'is_priced_under_10', 'get_first_category_id', sku, 'custom2')
    fields = ('name', 'brand', 'categories', 'price', 'order', 'sale_date',)
    ordering = ('order', 'id')

    def custom2(self, obj):
        return 'custom2: %s' % obj.name

    def queryset(self, request):
        qs = super(ProductBackboneView, self).queryset(request)
        return qs.filter(is_hidden=False)

    def has_add_permission_for_data(self, request, cleaned_data):
        if cleaned_data['name'] == 'NOTALLOWED':
            return False
        else:
            return True

    def has_update_permission_for_data(self, request, cleaned_data):
        if cleaned_data['name'] == 'NOTALLOWED':
            return False
        else:
            return True

backbone.site.register(ProductBackboneView)


class BrandBackboneView(BackboneAPIView):
    model = Brand
    form = BrandForm
    display_fields = ['name',]
    fields = ('name',)
    paginate_by = 2

    def has_delete_permission(self, request, obj):
        return False

backbone.site.register(BrandBackboneView)


class BrandAlternateBackboneView(BackboneAPIView):
    model = Brand
    display_fields = ['id', 'custom']
    url_slug = 'brand_alternate'

    def custom(self, obj):
        return 'foo'

backbone.site.register(BrandAlternateBackboneView)


class ExtendedProductBackboneView(BackboneAPIView):
    model = ExtendedProduct
    display_fields = ('creation_date', 'name', 'brand', 'categories',
        'price', 'order', 'is_priced_under_10', 'get_first_category_id', 'description',)

backbone.site.register(ExtendedProductBackboneView)


class DisplayFieldsProductBackboneView(BackboneAPIView):
    model = DisplayFieldsProduct
    display_collection_fields = ('name', 'brand', 'categories',)
    display_detail_fields = ('name', 'brand', 'categories',)

backbone.site.register(DisplayFieldsProductBackboneView)

########NEW FILE########
__FILENAME__ = forms
from django import forms
from django.utils.translation import ugettext_lazy as _

from backbone.tests.models import Brand


class BrandForm(forms.ModelForm):

    class Meta:
        model = Brand
        fields = ('name',)

    def clean_name(self):
        name = self.cleaned_data['name']
        if name:
            if name[0] != name[0].upper():
                # A silly rule just for the purpose of testing.
                raise forms.ValidationError(_('Brand name must start with a capital letter.'))
        return name
########NEW FILE########
__FILENAME__ = models
from django.db import models
from django.utils.translation import ugettext_lazy as _


class Brand(models.Model):
    name = models.CharField(_('name'), max_length=255)

    class Meta:
        ordering = ('id',)


class Category(models.Model):
    name = models.CharField(_('name'), max_length=255)

    class Meta:
        ordering = ('id',)


class Product(models.Model):
    creation_date = models.DateTimeField(auto_now_add=True)
    name = models.CharField(max_length=255)
    brand = models.ForeignKey(Brand, null=True, blank=True)
    categories = models.ManyToManyField(Category, blank=True)
    is_hidden = models.BooleanField(default=False)
    price = models.DecimalField(max_digits=8, decimal_places=2)
    order = models.PositiveSmallIntegerField(default=0)
    sku = models.CharField(max_length=255)
    sale_date = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ('id',)

    @property
    def is_priced_under_10(self):
        return self.price < 10

    def get_first_category_id(self):
        if self.categories.count():
            return self.categories.all()[0].id
        else:
            return None


class ExtendedProduct(Product):
    description = models.CharField(max_length=255)


class DisplayFieldsProduct(Product):
    description = models.CharField(max_length=255)

########NEW FILE########
__FILENAME__ = settings
import os

# Settings for running tests.

DEBUG = True
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join(os.path.dirname(__file__), 'backbone_tests.db'),
    }
}

# This is just for backwards compatibility
DATABASE_ENGINE = 'sqlite3'
DATABASE_NAME = DATABASES['default']['NAME']

ROOT_URLCONF = 'backbone.tests.urls'

INSTALLED_APPS = (
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'backbone',
    'backbone.tests',
)

SECRET_KEY = 'pl@#s<ajk3cM$kdh)*4&dsJ'

########NEW FILE########
__FILENAME__ = tests
import datetime
from decimal import Decimal
import json

from django.contrib.auth.models import User, Permission
from django.core.urlresolvers import reverse
from django.test import TestCase
from django.utils.translation import ugettext as _

from backbone.tests.models import Product, Brand, Category, ExtendedProduct, DisplayFieldsProduct
from backbone.tests.backbone_api import BrandBackboneView


class TestHelper(TestCase):

    def parseJsonResponse(self, response, status_code=200):
        self.assertEqual(response.status_code, status_code)
        self.assertEqual(response['Content-Type'], 'application/json')
        data = json.loads(response.content)
        return data

    def create_product(self, **kwargs):
        defaults = {
            'name': 'Test Product',
            'price': '12.32',
            'sku': '12345678',
        }
        if 'brand' not in kwargs:
            defaults['brand'] = self.create_brand()
        defaults.update(kwargs)
        return Product.objects.create(**defaults)

    def create_extended_product(self, **kwargs):
        defaults = {
            'name': 'Test Product',
            'price': '12.32'
        }
        if 'brand' not in kwargs:
            defaults['brand'] = self.create_brand()
        defaults.update(kwargs)
        return ExtendedProduct.objects.create(**defaults)

    def create_displayfields_product(self, **kwargs):
        defaults = {
            'name': 'Beta Product',
            'price': '13.32'
        }
        if 'brand' not in kwargs:
            defaults['brand'] = self.create_brand()
        defaults.update(kwargs)
        return DisplayFieldsProduct.objects.create(**defaults)

    def create_brand(self, **kwargs):
        defaults = {
            'name': 'Test Brand',
        }
        defaults.update(kwargs)
        return Brand.objects.create(**defaults)

    def create_category(self, **kwargs):
        defaults = {
            'name': 'Test Category',
        }
        defaults.update(kwargs)
        return Category.objects.create(**defaults)


class CollectionTests(TestHelper):

    def test_collection_view_returns_all_products_in_order(self):
        p3 = self.create_product(order=3)
        p1 = self.create_product(order=1)
        p2 = self.create_product(order=2)

        url = reverse('backbone:tests_product')
        response = self.client.get(url)
        data = self.parseJsonResponse(response)
        self.assertEqual(len(data), 3)
        self.assertEqual(data[0]['id'], p1.id)
        self.assertEqual(data[0]['name'], p1.name)
        self.assertEqual(data[1]['id'], p2.id)
        self.assertEqual(data[1]['name'], p1.name)
        self.assertEqual(data[2]['id'], p3.id)
        self.assertEqual(data[2]['name'], p1.name)

    def test_collection_view_only_returns_fields_specified_in_display_fields(self):
        self.create_product()
        url = reverse('backbone:tests_product')
        response = self.client.get(url)
        data = self.parseJsonResponse(response)
        self.assertEqual(len(data), 1)
        fields = data[0].keys()

        expected_fields = [
            'id', 'creation_date', 'name', 'brand', 'categories', 'price', 'order',
            'is_priced_under_10', 'get_first_category_id', 'sku', 'custom2'
        ]
        self.assertEqual(set(expected_fields), set(fields))
        self.assertTrue('is_hidden' not in fields)

    def test_collection_view_foreign_key_is_returned_as_id(self):
        brand = self.create_brand()
        self.create_product(brand=brand)
        url = reverse('backbone:tests_product')
        response = self.client.get(url)
        data = self.parseJsonResponse(response)
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]['brand'], brand.id)

    def test_collection_view_m2m_field_is_returned_as_list_of_ids(self):
        cat1 = self.create_category()
        cat2 = self.create_category()
        p = self.create_product()
        p.categories = [cat1, cat2]
        url = reverse('backbone:tests_product')
        response = self.client.get(url)
        data = self.parseJsonResponse(response)
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]['categories'], [cat1.id, cat2.id])

    def test_collection_view_with_custom_queryset(self):
        p1 = self.create_product()
        self.create_product(is_hidden=True)  # this should not appear

        url = reverse('backbone:tests_product')
        response = self.client.get(url)
        data = self.parseJsonResponse(response)
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]['id'], p1.id)

    def test_collection_view_put_request_returns_403(self):
        url = reverse('backbone:tests_product')
        response = self.client.put(url)
        self.assertEqual(response.status_code, 403)

    def test_collection_view_delete_request_returns_403(self):
        url = reverse('backbone:tests_product')
        response = self.client.delete(url)
        self.assertEqual(response.status_code, 403)

    def test_collection_view_pagination(self):
        # Brand is paginated 2 per page
        p1 = self.create_brand()
        p2 = self.create_brand()
        p3 = self.create_brand()

        url = reverse('backbone:tests_brand')

        # First page
        response = self.client.get(url, {'page': 1})
        data = self.parseJsonResponse(response)
        self.assertEqual(len(data), 2)
        self.assertEqual(data[0]['id'], p1.id)
        self.assertEqual(data[1]['id'], p2.id)

        # Second Page
        response = self.client.get(url, {'page': 2})
        data = self.parseJsonResponse(response)
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]['id'], p3.id)

    def test_collection_view_page_parameter_out_of_range_returns_error(self):
        url = reverse('backbone:tests_brand')

        response = self.client.get(url, {'page': 2})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.content, _('Invalid `page` parameter: Out of range.'))

    def test_collection_view_page_parameter_not_an_integer_returns_error(self):
        url = reverse('backbone:tests_brand')

        response = self.client.get(url, {'page': 'abcd'})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.content, _('Invalid `page` parameter: Not a valid integer.'))

    def test_collection_view_that_is_not_paginated_ignores_page_parameter(self):
        url = reverse('backbone:tests_product')
        response = self.client.get(url, {'page': 999})
        self.assertEqual(response.status_code, 200)

    def test_collection_view_for_view_with_custom_url_slug(self):
        brand = self.create_brand()
        url = reverse('backbone:tests_brand_alternate')
        response = self.client.get(url)
        data = self.parseJsonResponse(response)
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]['id'], brand.id)
        self.assertEqual(data[0]['custom'], 'foo')


class DetailTests(TestHelper):

    def test_detail_view_returns_object_details(self):
        product = self.create_product(price=3)
        category = self.create_category()
        product.categories.add(category)

        url = reverse('backbone:tests_product_detail', args=[product.id])
        response = self.client.get(url)
        data = self.parseJsonResponse(response)
        self.assertEqual(data['id'], product.id)
        self.assertEqual(data['name'], product.name)
        self.assertEqual(data['brand'], product.brand.id)
        self.assertEqual(data['categories'], [category.id])
        self.assertEqual(data['price'], str(product.price))
        self.assertEqual(data['order'], product.order)
        # Attribute on model
        self.assertEqual(data['is_priced_under_10'], True)
        # Callable
        self.assertEqual(data['sku'], '#: %s' % product.sku)
        # Callable on admin class
        self.assertEqual(data['custom2'], 'custom2: %s' % product.name)
        # Callable on model
        self.assertEqual(data['get_first_category_id'], category.id)

    def test_detail_view_uses_display_detail_fields_when_defined(self):
        display_fields_product = self.create_displayfields_product(price=111)
        category = self.create_category()
        display_fields_product.categories.add(category)

        url = reverse('backbone:tests_displayfieldsproduct_detail', args=[display_fields_product.id])
        response = self.client.get(url)
        data = self.parseJsonResponse(response)

        self.assertEqual(data['id'], display_fields_product.id)
        self.assertEqual(data['name'], display_fields_product.name)
        self.assertEqual(data['brand'], display_fields_product.brand.id)
        self.assertEqual(data['categories'], [category.id])
        self.assertTrue('price' not in data)
        self.assertTrue('order' not in data)
        # Attribute on model
        self.assertTrue('is_priced_under_10' not in data)
        # Callable
        self.assertTrue('sku' not in data)
        # Callable on admin class
        self.assertTrue('custom2' not in data)
        # Callable on model
        self.assertTrue('get_first_category_id' not in data)
        self.assertEqual(len(data.keys()), 4)

    def test_collection_view_uses_display_collection_fields_when_defined(self):
        display_fields_product = self.create_displayfields_product(price=111)
        category = self.create_category()
        display_fields_product.categories.add(category)

        url = reverse('backbone:tests_displayfieldsproduct')
        response = self.client.get(url)
        data = self.parseJsonResponse(response)

        self.assertEqual(len(data), 1)

        data = data[0]
        self.assertEqual(data['id'], display_fields_product.id)
        self.assertEqual(data['name'], display_fields_product.name)
        self.assertEqual(data['brand'], display_fields_product.brand.id)
        self.assertEqual(data['categories'], [category.id])
        self.assertTrue('price' not in data)
        self.assertTrue('order' not in data)
        # Attribute on model
        self.assertTrue('is_priced_under_10' not in data)
        # Callable
        self.assertTrue('sku' not in data)
        # Callable on admin class
        self.assertTrue('custom2' not in data)
        # Callable on model
        self.assertTrue('get_first_category_id' not in data)
        self.assertEqual(len(data.keys()), 4)

    def test_detail_view_doesnt_return_unspecified_fields(self):
        product = self.create_product()
        url = reverse('backbone:tests_product_detail', args=[product.id])
        response = self.client.get(url)
        data = self.parseJsonResponse(response)
        fields = data.keys()
        self.assertTrue('is_hidden' not in fields)

    def test_detail_view_returns_404_for_invalid_id(self):
        url = reverse('backbone:tests_product_detail', args=[999])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)

    def test_detail_view_returns_404_for_object_not_in_custom_queryset(self):
        product = self.create_product(is_hidden=True)
        url = reverse('backbone:tests_product_detail', args=[product.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)

    def test_detail_view_post_request_returns_403(self):
        product = self.create_product()
        url = reverse('backbone:tests_product_detail', args=[product.id])
        response = self.client.post(url)
        self.assertEqual(response.status_code, 403)

    def test_detail_view_for_view_with_custom_url_slug(self):
        brand = self.create_brand()
        url = reverse('backbone:tests_brand_alternate_detail', args=[brand.id])
        response = self.client.get(url)
        data = self.parseJsonResponse(response)
        self.assertEqual(data['id'], brand.id)
        self.assertEqual(data['custom'], 'foo')


class AddTests(TestHelper):

    def setUp(self):
        self.user = User.objects.create_user(username='test', password='test', email='t@t.com')
        self.client.login(username='test', password='test')
        add_product = Permission.objects.get_by_natural_key('add_product', 'tests', 'product')
        add_brand = Permission.objects.get_by_natural_key('add_brand', 'tests', 'brand')
        self.user.user_permissions = [add_product, add_brand]

    def test_post_request_on_product_collection_view_adds_product_to_db(self):
        brand = self.create_brand()
        cat1 = self.create_category()
        cat2 = self.create_category()
        data = json.dumps({
            'name': 'Test',
            'brand': brand.id,
            'categories': [cat1.id, cat2.id],
            'price': 12.34,
            'order': 1,
            'sale_date': '2006-10-25 14:30:59',
        })
        url = reverse('backbone:tests_product')
        response = self.client.post(url, data, content_type='application/json')
        self.assertEqual(response.status_code, 201)

        self.assertEqual(Product.objects.count(), 1)
        product = Product.objects.order_by('-id')[0]
        self.assertEqual(product.name, 'Test')
        self.assertEqual(product.brand, brand)
        self.assertEqual(product.categories.count(), 2)
        self.assertEqual(product.categories.all()[0], cat1)
        self.assertEqual(product.categories.all()[1], cat2)
        self.assertEqual(product.price, Decimal('12.34'))
        self.assertEqual(product.sale_date, datetime.datetime(2006, 10, 25, 14, 30, 59))

        data = self.parseJsonResponse(response, status_code=201)
        self.assertEqual(data['id'], product.id)
        self.assertEqual(data['name'], product.name)
        self.assertEqual(data['brand'], product.brand.id)
        self.assertEqual(data['categories'], [cat1.id, cat2.id])
        self.assertEqual(data['price'], '12.34')

        self.assertEqual(response['Location'], 'http://testserver' \
            + reverse('backbone:tests_product_detail', args=[product.id])
        )

    def test_post_request_on_product_collection_view_with_invalid_json_returns_error(self):
        url = reverse('backbone:tests_product')
        response = self.client.post(url, '', content_type='application/json')
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.content, _('Unable to parse JSON request body.'))

        response = self.client.post(url, 'Some invalid json', content_type='application/json')
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.content, _('Unable to parse JSON request body.'))

    def test_post_request_on_product_collection_view_with_validation_errors_returns_error_list_as_json(self):
        data = json.dumps({
            'name': '',
            'brand': '',
            'categories': [],
            'price': None,
            'order': '',
        })
        url = reverse('backbone:tests_product')
        response = self.client.post(url, data, content_type='application/json')
        self.assertEqual(Product.objects.count(), 0)
        data = self.parseJsonResponse(response, status_code=400)
        self.assertEqual(len(data), 3)
        self.assertEqual(data['name'], [_('This field is required.')])
        self.assertEqual(data['price'], [_('This field is required.')])
        self.assertEqual(data['order'], [_('This field is required.')])

    def test_post_request_on_product_collection_view_ignores_fields_not_specified(self):
        brand = self.create_brand()
        cat1 = self.create_category()
        cat2 = self.create_category()
        data = json.dumps({
            'name': 'Test',
            'brand': brand.id,
            'categories': [cat1.id, cat2.id],
            'price': 12.34,
            'order': 1,
            'is_hidden': True  # User should not be able to alter is_hidden
        })
        url = reverse('backbone:tests_product')
        response = self.client.post(url, data, content_type='application/json')
        self.assertEqual(response.status_code, 201)
        self.assertEqual(Product.objects.count(), 1)
        product = Product.objects.order_by('-id')[0]
        self.assertEqual(product.is_hidden, False)

    def test_post_request_on_product_collection_view_when_user_not_logged_in_returns_403(self):
        self.client.logout()

        url = reverse('backbone:tests_product')
        response = self.client.post(url)
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.content, _('You do not have permission to perform this action.'))
        self.assertEqual(Product.objects.count(), 0)

    def test_post_request_on_product_collection_view_when_user_doesnt_have_add_permission_returns_403(self):
        self.client.logout()
        self.user.user_permissions.clear()
        self.client.login(username='test', password='test')
        url = reverse('backbone:tests_product')
        response = self.client.post(url)
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.content, _('You do not have permission to perform this action.'))

    def test_post_request_on_product_collection_view_violating_field_specific_permission_returns_403(self):
        brand = self.create_brand()
        cat1 = self.create_category()
        data = json.dumps({
            'name': 'NOTALLOWED',
            'brand': brand.id,
            'categories': [cat1.id],
            'price': 12.34,
            'order': 1
        })
        url = reverse('backbone:tests_product')
        response = self.client.post(url, data, content_type='application/json')
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.content, _('You do not have permission to perform this action.'))

    def test_post_request_on_brand_collection_view_uses_custom_model_form(self):
        data = json.dumps({
            'name': 'this should give an error',
        })
        url = reverse('backbone:tests_brand')
        response = self.client.post(url, data, content_type='application/json')
        self.assertEqual(Brand.objects.count(), 0)
        data = self.parseJsonResponse(response, status_code=400)
        self.assertEqual(len(data), 1)
        self.assertEqual(data['name'], [_('Brand name must start with a capital letter.')])

    def test_post_request_on_custom_url_slug_view_contains_custom_url_in_location_header(self):
        data = json.dumps({
            'name': 'Foo',
        })
        url = reverse('backbone:tests_brand_alternate')
        response = self.client.post(url, data, content_type='application/json')
        self.assertEqual(response.status_code, 201)
        self.assertEqual(Brand.objects.count(), 1)

        self.assertEqual(
            response['Location'],
            'http://testserver' + reverse(
                'backbone:tests_brand_alternate_detail', args=[Brand.objects.get().id]
            )
        )


class UpdateTests(TestHelper):

    def setUp(self):
        self.user = User.objects.create_user(username='test', password='test', email='t@t.com')
        self.client.login(username='test', password='test')
        update_product = Permission.objects.get_by_natural_key('change_product', 'tests', 'product')
        update_brand = Permission.objects.get_by_natural_key('change_brand', 'tests', 'brand')
        self.user.user_permissions = [update_product, update_brand]

    def test_put_request_on_product_detail_view_updates_product(self):
        product = self.create_product()

        brand = self.create_brand()
        cat1 = self.create_category()
        cat2 = self.create_category()
        data = json.dumps({
            'name': 'Test',
            'brand': brand.id,
            'categories': [cat1.id, cat2.id],
            'price': 56.78,
            'order': 2
        })
        url = reverse('backbone:tests_product_detail', args=[product.id])
        response = self.client.put(url, data, content_type='application/json')
        self.assertEqual(response.status_code, 200)

        self.assertEqual(Product.objects.count(), 1)
        product = Product.objects.get(id=product.id)  # refresh from db
        self.assertEqual(product.name, 'Test')
        self.assertEqual(product.brand, brand)
        self.assertEqual(product.categories.count(), 2)
        self.assertEqual(product.categories.all()[0], cat1)
        self.assertEqual(product.categories.all()[1], cat2)
        self.assertEqual(product.price, Decimal('56.78'))

        data = self.parseJsonResponse(response, status_code=200)
        self.assertEqual(data['id'], product.id)
        self.assertEqual(data['name'], product.name)
        self.assertEqual(data['brand'], product.brand.id)
        self.assertEqual(data['categories'], [cat1.id, cat2.id])
        self.assertEqual(data['price'], '56.78')

    def test_put_request_on_product_detail_view_with_invalid_json_returns_error(self):
        product = self.create_product()

        url = reverse('backbone:tests_product_detail', args=[product.id])
        response = self.client.put(url, '', content_type='application/json')
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.content, _('Unable to parse JSON request body.'))

        response = self.client.put(url, 'Some invalid json', content_type='application/json')
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.content, _('Unable to parse JSON request body.'))

    def test_put_request_on_product_detail_view_with_validation_errors_returns_error_list_as_json(self):
        product = self.create_product()
        data = json.dumps({
            'name': '',
            'price': None,
            'order': '',
        })
        url = reverse('backbone:tests_product_detail', args=[product.id])
        response = self.client.put(url, data, content_type='application/json')
        self.assertEqual(Product.objects.count(), 1)
        data = self.parseJsonResponse(response, status_code=400)
        self.assertEqual(len(data), 3)
        self.assertEqual(data['name'], [_('This field is required.')])
        self.assertEqual(data['price'], [_('This field is required.')])
        self.assertEqual(data['order'], [_('This field is required.')])

    def test_put_request_on_product_detail_view_ignores_fields_not_specified(self):
        product = self.create_product()
        brand = self.create_brand()
        cat1 = self.create_category()
        cat2 = self.create_category()
        data = json.dumps({
            'name': 'Test',
            'brand': brand.id,
            'categories': [cat1.id, cat2.id],
            'price': 12.34,
            'order': 1,
            'is_hidden': True  # User should not be able to alter is_hidden
        })
        url = reverse('backbone:tests_product_detail', args=[product.id])
        response = self.client.put(url, data, content_type='application/json')
        self.assertEqual(response.status_code, 200)
        product = Product.objects.get(id=product.id)  # refresh from db
        self.assertEqual(product.is_hidden, False)

    def test_put_request_on_product_detail_view_when_user_not_logged_in_returns_403(self):
        product = self.create_product()
        self.client.logout()

        url = reverse('backbone:tests_product_detail', args=[product.id])
        response = self.client.put(url)
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.content, _('You do not have permission to perform this action.'))

    def test_put_request_on_product_detail_view_when_user_doesnt_have_update_permission_returns_403(self):
        product = self.create_product()
        self.client.logout()
        self.user.user_permissions.clear()
        self.client.login(username='test', password='test')

        url = reverse('backbone:tests_product_detail', args=[product.id])
        response = self.client.put(url)
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.content, _('You do not have permission to perform this action.'))

    def test_put_request_on_product_detail_view_violating_field_specific_permission_returns_403(self):
        product = self.create_product()
        brand = self.create_brand()
        cat1 = self.create_category()
        data = json.dumps({
            'name': 'NOTALLOWED',
            'brand': brand.id,
            'categories': [cat1.id],
            'price': 12.34,
            'order': 2
        })
        url = reverse('backbone:tests_product_detail', args=[product.id])
        response = self.client.put(url, data, content_type='application/json')
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.content, _('You do not have permission to perform this action.'))

    def test_put_request_on_brand_collection_view_uses_custom_model_form(self):
        brand = self.create_brand()
        data = json.dumps({
            'name': 'this should give an error',
        })
        url = reverse('backbone:tests_brand_detail', args=[brand.id])
        response = self.client.put(url, data, content_type='application/json')
        self.assertEqual(Product.objects.count(), 0)
        data = self.parseJsonResponse(response, status_code=400)
        self.assertEqual(len(data), 1)
        self.assertEqual(data['name'], [_('Brand name must start with a capital letter.')])


class DeleteTests(TestHelper):

    def setUp(self):
        self.user = User.objects.create_user(username='test', password='test', email='t@t.com')
        self.client.login(username='test', password='test')
        delete_product = Permission.objects.get_by_natural_key('delete_product', 'tests', 'product')
        delete_brand = Permission.objects.get_by_natural_key('delete_brand', 'tests', 'brand')
        self.user.user_permissions.add(delete_product, delete_brand)

    def test_delete_request_on_product_deletes_the_item(self):
        product = self.create_product()
        url = reverse('backbone:tests_product_detail', args=[product.id])
        response = self.client.delete(url)
        self.assertEqual(response.status_code, 204)
        self.assertEqual(Product.objects.count(), 0)

    def test_delete_request_on_product_when_user_not_logged_in_returns_403(self):
        self.client.logout()
        product = self.create_product()
        url = reverse('backbone:tests_product_detail', args=[product.id])
        response = self.client.delete(url)
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.content, _('You do not have permission to perform this action.'))
        self.assertEqual(Product.objects.count(), 1)

    def test_delete_request_on_product_when_user_doesnt_have_delete_permission_returns_403(self):
        self.client.logout()
        self.user.user_permissions.clear()
        self.client.login(username='test', password='test')
        product = self.create_product()
        url = reverse('backbone:tests_product_detail', args=[product.id])
        response = self.client.delete(url)
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.content, _('You do not have permission to perform this action.'))
        self.assertEqual(Product.objects.count(), 1)

    def test_delete_request_on_brand_returns_403(self):
        brand = self.create_brand()
        url = reverse('backbone:tests_brand_detail', args=[brand.id])
        response = self.client.delete(url)
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.content, _('You do not have permission to perform this action.'))
        self.assertEqual(Brand.objects.count(), 1)


class InheritanceTests(TestHelper):

    def test_detail_view_returns_inherited_object_details(self):
        ext_product = self.create_extended_product(price=9)
        category = self.create_category()
        ext_product.categories.add(category)

        url = reverse('backbone:tests_extendedproduct_detail', args=[ext_product.id])
        response = self.client.get(url)
        data = self.parseJsonResponse(response)
        self.assertEqual(data['id'], ext_product.id)
        self.assertEqual(data['name'], ext_product.name)
        self.assertEqual(data['brand'], ext_product.brand.id)
        self.assertEqual(data['categories'], [category.id])
        self.assertEqual(data['price'], str(ext_product.price))
        self.assertEqual(data['order'], ext_product.order)
        self.assertEqual(data['description'], ext_product.description)
        # Attribute on model
        self.assertEqual(data['is_priced_under_10'], True)
        # Callable on model
        self.assertEqual(data['get_first_category_id'], category.id)


class InvalidViewTests(TestHelper):
    def setUp(self):
        BrandBackboneView.display_fields += ['invalid_field']

    def tearDown(self):
        BrandBackboneView.display_fields.remove('invalid_field')

    def test_invalid_field_name_raises_attribute_error(self):
        brand = self.create_brand()
        url = reverse('backbone:tests_brand_detail', args=[brand.id])
        try:
            self.client.get(url)
        except AttributeError, err:
            self.assertEqual(str(err), "Invalid field: invalid_field")

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls import patterns, url, include
from django.contrib import admin

import backbone


admin.autodiscover()
backbone.autodiscover()

urlpatterns = patterns('',
    url(r'^admin/', include(admin.site.urls)),
    url(r'^backbone/', include(backbone.site.urls)),
    url(r'^$', 'backbone.tests.views.homepage', name='tests-homepage'),
)

########NEW FILE########
__FILENAME__ = views
from django.shortcuts import render


def homepage(request):
    return render(request, 'home.html')

########NEW FILE########
__FILENAME__ = views
import json

from django.core.serializers.json import DjangoJSONEncoder
from django.core.urlresolvers import reverse
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.forms.models import modelform_factory
from django.http import HttpResponse, HttpResponseBadRequest, HttpResponseForbidden
from django.shortcuts import get_object_or_404
from django.utils.translation import ugettext as _
from django.views.generic import View

from backbone.serializers import AllFieldsSerializer


class BackboneAPIView(View):
    model = None  # The model to be used for this API definition
    display_fields = []  # Fields to return for read (GET) requests,
    display_collection_fields = [] # Specific fields to return for a read (GET) request of a model collection
    display_detail_fields = [] # Specific fields to return for read (GET) requests for a specific model
    fields = []  # Fields to allow when adding (POST) or editing (PUT) objects.
    form = None  # The form class to be used for adding or editing objects.
    ordering = None  # Ordering used when retrieving the collection
    paginate_by = None  # The max number of objects per page (enables use of the ``page`` GET parameter).
    url_slug = None  # The slug to be used when constructing the url (and url name) for this view.
                     # Defaults to lowercase model name. Change this if you have multiple views for the same model.

    def queryset(self, request, **kwargs):
        """
        Returns the queryset (along with ordering) to be used when retrieving object(s).
        """
        qs = self.model._default_manager.all()
        if self.ordering:
            qs = qs.order_by(*self.ordering)
        return qs

    def get(self, request, id=None, **kwargs):
        """
        Handles get requests for either the collection or an object detail.
        """
        if not self.has_get_permission(request):
            return HttpResponseForbidden(_('You do not have permission to perform this action.'))

        if id:
            obj = get_object_or_404(self.queryset(request, **kwargs), id=id)
            return self.get_object_detail(request, obj)
        else:
            return self.get_collection(request, **kwargs)

    def get_object_detail(self, request, obj):
        """
        Handles get requests for the details of the given object.
        """
        if self.display_detail_fields:
            display_fields = self.display_detail_fields
        else:
            display_fields = self.display_fields

        data = self.serialize(obj, ['id'] + list(display_fields))
        return HttpResponse(self.json_dumps(data), content_type='application/json')

    def get_collection(self, request, **kwargs):
        """
        Handles get requests for the list of objects.
        """
        qs = self.queryset(request, **kwargs)

        if self.display_collection_fields:
            display_fields = self.display_collection_fields
        else:
            display_fields = self.display_fields

        if self.paginate_by is not None:
            page = request.GET.get('page', 1)
            paginator = Paginator(qs, self.paginate_by)
            try:
                qs = paginator.page(page).object_list
            except PageNotAnInteger:
                data = _('Invalid `page` parameter: Not a valid integer.')
                return HttpResponseBadRequest(data)
            except EmptyPage:
                data = _('Invalid `page` parameter: Out of range.')
                return HttpResponseBadRequest(data)
        data = [
            self.serialize(obj, ['id'] + list(display_fields)) for obj in qs
        ]
        return HttpResponse(self.json_dumps(data), content_type='application/json')

    def post(self, request, id=None, **kwargs):
        """
        Handles post requests.
        """
        if id:
            # No posting to an object detail page
            return HttpResponseForbidden()
        else:
            if not self.has_add_permission(request):
                return HttpResponseForbidden(_('You do not have permission to perform this action.'))
            else:
                return self.add_object(request)

    def add_object(self, request):
        """
        Adds an object.
        """
        try:
            # backbone sends data in the body in json format
            # Conditional statement is for backwards compatibility with Django <= 1.3
            data = json.loads(request.body if hasattr(request, 'body') else request.raw_post_data)
        except ValueError:
            return HttpResponseBadRequest(_('Unable to parse JSON request body.'))

        form = self.get_form_instance(request, data=data)
        if form.is_valid():
            if not self.has_add_permission_for_data(request, form.cleaned_data):
                return HttpResponseForbidden(_('You do not have permission to perform this action.'))

            obj = form.save()

            # We return the newly created object's details and a Location header with it's url
            response = self.get_object_detail(request, obj)
            response.status_code = 201

            url_name = 'backbone:%s_%s_detail' % (
                self.model._meta.app_label,
                self.url_slug or self.model._meta.module_name
            )
            response['Location'] = reverse(url_name, args=[obj.id])
            return response
        else:
            return HttpResponseBadRequest(self.json_dumps(form.errors), content_type='application/json')

    def put(self, request, id=None, **kwargs):
        """
        Handles put requests.
        """
        if id:
            obj = get_object_or_404(self.queryset(request), id=id)
            if not self.has_update_permission(request, obj):
                return HttpResponseForbidden(_('You do not have permission to perform this action.'))
            else:
                return self.update_object(request, obj)
        else:
            # No putting on a collection.
            return HttpResponseForbidden()

    def update_object(self, request, obj):
        """
        Updates an object.
        """
        try:
            # backbone sends data in the body in json format
                # Conditional statement is for backwards compatibility with Django <= 1.3
            data = json.loads(request.body if hasattr(request, 'body') else request.raw_post_data)
        except ValueError:
            return HttpResponseBadRequest(_('Unable to parse JSON request body.'))

        form = self.get_form_instance(request, data=data, instance=obj)
        if form.is_valid():
            if not self.has_update_permission_for_data(request, form.cleaned_data):
                return HttpResponseForbidden(_('You do not have permission to perform this action.'))
            form.save()

            # We return the updated object details
            return self.get_object_detail(request, obj)
        else:
            return HttpResponseBadRequest(self.json_dumps(form.errors), content_type='application/json')

    def get_form_instance(self, request, data=None, instance=None):
        """
        Returns an instantiated form to be used for adding or editing an object.

        The `instance` argument is the model instance (passed only if this form
        is going to be used for editing an existing object).
        """
        defaults = {}
        if self.form:
            defaults['form'] = self.form
        if self.fields:
            defaults['fields'] = self.fields
        return modelform_factory(self.model, **defaults)(data=data, instance=instance)

    def delete(self, request, id=None):
        """
        Handles delete requests.
        """
        if id:
            obj = get_object_or_404(self.queryset(request), id=id)
            if not self.has_delete_permission(request, obj):
                return HttpResponseForbidden(_('You do not have permission to perform this action.'))
            else:
                return self.delete_object(request, obj)
        else:
            # No delete requests allowed on collection view
            return HttpResponseForbidden()

    def delete_object(self, request, obj):
        """
        Deletes the the given object.
        """
        obj.delete()
        return HttpResponse(status=204)

    def has_get_permission(self, request):
        """
        Returns True if the requesting user is allowed to retrieve objects.
        """
        return True

    def has_add_permission(self, request):
        """
        Returns True if the requesting user is allowed to add an object, False otherwise.
        """
        perm_string = '%s.add_%s' % (self.model._meta.app_label,
            self.model._meta.object_name.lower()
        )
        return request.user.has_perm(perm_string)

    def has_add_permission_for_data(self, request, cleaned_data):
        """
        Returns True if the requesting user is allowed to add an object with the
        given data, False otherwise.

        If the add permission does not depend on the data being submitted,
        use `has_add_permission` instead.
        """
        return True

    def has_update_permission(self, request, obj):
        """
        Returns True if the requesting user is allowed to update the given object, False otherwise.
        """
        perm_string = '%s.change_%s' % (self.model._meta.app_label,
            self.model._meta.object_name.lower()
        )
        return request.user.has_perm(perm_string)

    def has_update_permission_for_data(self, request, cleaned_data):
        """
        Returns True if the requesting user is allowed to update the object with the
        given data, False otherwise.

        If the update permission does not depend on the data being submitted,
        use `has_update_permission` instead.
        """
        return True

    def has_delete_permission(self, request, obj):
        """
        Returns True if the requesting user is allowed to delete the given object, False otherwise.
        """
        perm_string = '%s.delete_%s' % (self.model._meta.app_label,
            self.model._meta.object_name.lower()
        )
        return request.user.has_perm(perm_string)

    def serialize(self, obj, fields):
        """
        Serializes a single model instance to a Python object, based on the specified list of fields.
        """

        data = {}
        remaining_fields = []
        for field in fields:
            if callable(field):  # Callable
                data[field.__name__] = field(obj)
            elif hasattr(self, field) and callable(getattr(self, field)):  # Method on the view
                data[field] = getattr(self, field)(obj)
            elif hasattr(obj, field):  # Callable/property/field on the model
                attr = getattr(obj, field)
                if callable(attr):  # Callable on the model
                    data[field] = attr()
                else:
                    remaining_fields.append(field)
            else:
                raise AttributeError('Invalid field: %s' % field)

        # Add on db fields
        serializer = AllFieldsSerializer()
        serializer.serialize([obj], fields=list(remaining_fields))
        data.update(serializer.getvalue()[0]['fields'])

        # Any remaining fields should be properties on the model
        remaining_fields = set(remaining_fields) - set(data.keys())

        for field in remaining_fields:
            data[field] = getattr(obj, field)

        return data

    def json_dumps(self, data, **options):
        """
        Wrapper around `json.dumps` that uses a special JSON encoder.
        """
        params = {'sort_keys': True, 'indent': 2}
        params.update(options)
        # This code is based off django's built in JSON serializer
        if json.__version__.split('.') >= ['2', '1', '3']:
            # Use JS strings to represent Python Decimal instances (ticket #16850)
            params.update({'use_decimal': False})
        return json.dumps(data, cls=DjangoJSONEncoder, **params)

########NEW FILE########
