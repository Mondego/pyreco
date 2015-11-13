__FILENAME__ = cart
import datetime
import models

CART_ID = 'CART-ID'

class ItemAlreadyExists(Exception):
    pass

class ItemDoesNotExist(Exception):
    pass

class Cart:
    def __init__(self, request):
        cart_id = request.session.get(CART_ID)
        if cart_id:
            try:
                cart = models.Cart.objects.get(id=cart_id, checked_out=False)
            except models.Cart.DoesNotExist:
                cart = self.new(request)
        else:
            cart = self.new(request)
        self.cart = cart

    def __iter__(self):
        for item in self.cart.item_set.all():
            yield item

    def new(self, request):
        cart = models.Cart(creation_date=datetime.datetime.now())
        cart.save()
        request.session[CART_ID] = cart.id
        return cart

    def add(self, product, unit_price, quantity=1):
        try:
            item = models.Item.objects.get(
                cart=self.cart,
                product=product,
            )
        except models.Item.DoesNotExist:
            item = models.Item()
            item.cart = self.cart
            item.product = product
            item.unit_price = unit_price
            item.quantity = quantity
            item.save()
        else: #ItemAlreadyExists
            item.unit_price = unit_price
            item.quantity = item.quantity + int(quantity)
            item.save()

    def remove(self, product):
        try:
            item = models.Item.objects.get(
                cart=self.cart,
                product=product,
            )
        except models.Item.DoesNotExist:
            raise ItemDoesNotExist
        else:
            item.delete()

    def update(self, product, quantity, unit_price=None):
        try:
            item = models.Item.objects.get(
                cart=self.cart,
                product=product,
            )
        except models.Item.DoesNotExist:
            raise ItemDoesNotExist
            
    def count(self):
        result = 0
        for item in self.cart.item_set.all():
            result += 1 * item.quantity
        return result
        
    def summary(self):
        result = 0
        for item in self.cart.item_set.all():
            result += item.total_price
        return result

    def clear(self):
        for item in self.cart.item_set.all():
            item.delete()


########NEW FILE########
__FILENAME__ = 0001_initial
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding model 'Cart'
        db.create_table('cart_cart', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('creation_date', self.gf('django.db.models.fields.DateTimeField')()),
            ('checked_out', self.gf('django.db.models.fields.BooleanField')(default=False)),
        ))
        db.send_create_signal('cart', ['Cart'])

        # Adding model 'Item'
        db.create_table('cart_item', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('cart', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['cart.Cart'])),
            ('quantity', self.gf('django.db.models.fields.PositiveIntegerField')()),
            ('unit_price', self.gf('django.db.models.fields.DecimalField')(max_digits=18, decimal_places=2)),
            ('content_type', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['contenttypes.ContentType'])),
            ('object_id', self.gf('django.db.models.fields.PositiveIntegerField')()),
        ))
        db.send_create_signal('cart', ['Item'])


    def backwards(self, orm):
        
        # Deleting model 'Cart'
        db.delete_table('cart_cart')

        # Deleting model 'Item'
        db.delete_table('cart_item')


    models = {
        'cart.cart': {
            'Meta': {'ordering': "('-creation_date',)", 'object_name': 'Cart'},
            'checked_out': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'creation_date': ('django.db.models.fields.DateTimeField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        },
        'cart.item': {
            'Meta': {'ordering': "('cart',)", 'object_name': 'Item'},
            'cart': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['cart.Cart']"}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'object_id': ('django.db.models.fields.PositiveIntegerField', [], {}),
            'quantity': ('django.db.models.fields.PositiveIntegerField', [], {}),
            'unit_price': ('django.db.models.fields.DecimalField', [], {'max_digits': '18', 'decimal_places': '2'})
        },
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        }
    }

    complete_apps = ['cart']

########NEW FILE########
__FILENAME__ = models
from django.db import models
from django.utils.translation import ugettext_lazy as _
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes import generic

class Cart(models.Model):
    creation_date = models.DateTimeField(verbose_name=_('creation date'))
    checked_out = models.BooleanField(default=False, verbose_name=_('checked out'))

    class Meta:
        verbose_name = _('cart')
        verbose_name_plural = _('carts')
        ordering = ('-creation_date',)

    def __unicode__(self):
        return unicode(self.creation_date)

class ItemManager(models.Manager):
    def get(self, *args, **kwargs):
        if 'product' in kwargs:
            kwargs['content_type'] = ContentType.objects.get_for_model(type(kwargs['product']))
            kwargs['object_id'] = kwargs['product'].pk
            del(kwargs['product'])
        return super(ItemManager, self).get(*args, **kwargs)

class Item(models.Model):
    cart = models.ForeignKey(Cart, verbose_name=_('cart'))
    quantity = models.PositiveIntegerField(verbose_name=_('quantity'))
    unit_price = models.DecimalField(max_digits=18, decimal_places=2, verbose_name=_('unit price'))
    # product as generic relation
    content_type = models.ForeignKey(ContentType)
    object_id = models.PositiveIntegerField()

    objects = ItemManager()

    class Meta:
        verbose_name = _('item')
        verbose_name_plural = _('items')
        ordering = ('cart',)

    def __unicode__(self):
        return u'%d units of %s' % (self.quantity, self.product.__class__.__name__)

    def total_price(self):
        return self.quantity * self.unit_price
    total_price = property(total_price)

    # product
    def get_product(self):
        return self.content_type.get_object_for_this_type(pk=self.object_id)

    def set_product(self, product):
        self.content_type = ContentType.objects.get_for_model(type(product))
        self.object_id = product.pk

    product = property(get_product, set_product)


########NEW FILE########
__FILENAME__ = tests
from django.test import TestCase
from models import Cart, Item
from django.contrib.auth.models import User
import datetime
from decimal import Decimal

class CartAndItemModelsTestCase(TestCase):

    def _create_cart_in_database(self, creation_date=datetime.datetime.now(), 
            checked_out=False):
        """
            Helper function so I don't repeat myself
        """
        cart = Cart()
        cart.creation_date = creation_date
        cart.checked_out = False
        cart.save()
        return cart

    def _create_item_in_database(self, cart, product, quantity=1, 
            unit_price=Decimal("100")):
        """
            Helper function so I don't repeat myself
        """  
        item = Item()
        item.cart = cart
        item.product = product
        item.quantity = quantity
        item.unit_price = unit_price
        item.save() 

        return item

    def _create_user_in_database(self):
        """
            Helper function so I don't repeat myself
        """ 
        user = User(username="user_for_sell", password="sold", 
                email="example@example.com")
        user.save() 
        return user

    def test_cart_creation(self):
        creation_date = datetime.datetime.now()
        cart = self._create_cart_in_database(creation_date)
        id = cart.id

        cart_from_database = Cart.objects.get(pk=id)
        self.assertEquals(cart, cart_from_database)
        

    def test_item_creation_and_association_with_cart(self):
        """
            This test is a little bit tricky since the Item tracks
            any model via django's content type framework. This was
            made in order to enable you to associate an item in the
            cart with your product model.
            
            As I wont make a product model here, I will assume my test
            store sells django users (django.contrib.auth.models.User) 
            (lol) so I can test that this is working.

            So if you are reading this test to understand the API,
            you just need to change the user for your product model
            in your code and you're good to go.
        """
        user = self._create_user_in_database()

        cart = self._create_cart_in_database()
        item = self._create_item_in_database(cart, user, quantity=1, unit_price=Decimal("100"))

        # get the first item in the cart
        item_in_cart = cart.item_set.all()[0]
        self.assertEquals(item_in_cart, item, 
                "First item in cart should be equal the item we created")
        self.assertEquals(item_in_cart.product, user,
                "Product associated with the first item in cart should equal the user we're selling")
        self.assertEquals(item_in_cart.unit_price, Decimal("100"), 
                "Unit price of the first item stored in the cart should equal 100")
        self.assertEquals(item_in_cart.quantity, 1, 
                "The first item in cart should have 1 in it's quantity")


    def test_total_item_price(self):
        """
        Since the unit price is a Decimal field, prefer to associate
        unit prices instantiating the Decimal class in 
        decimal.Decimal.
        """
        user = self._create_user_in_database()
        cart = self._create_cart_in_database()

        # not safe to do as the field is Decimal type. It works for integers but
        # doesn't work for float
        item_with_unit_price_as_integer = self._create_item_in_database(cart, product=user, quantity=3, unit_price=100)

        self.assertEquals(item_with_unit_price_as_integer.total_price, 300)
        
        # this is the right way to associate unit prices
        item_with_unit_price_as_decimal = self._create_item_in_database(cart,
                product=user, quantity=4, unit_price=Decimal("3.20"))
        self.assertEquals(item_with_unit_price_as_decimal.total_price, Decimal("12.80"))

    def test_item_unicode(self):
        user = self._create_user_in_database()
        cart = self._create_cart_in_database()

        item = self._create_item_in_database(cart, product=user, quantity=3, unit_price=Decimal("100"))

        self.assertEquals(item.__unicode__(), "3 units of User")

########NEW FILE########
__FILENAME__ = views
# Create your views here.

########NEW FILE########
