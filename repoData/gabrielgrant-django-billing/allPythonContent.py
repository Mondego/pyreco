__FILENAME__ = admin
from billing.models import Account, ProductType, Subscription, SubscriptionApprovalStatus
from django.contrib import admin

from .loading import get_products

class SubscriptionInline(admin.StackedInline):
    model = Subscription
    extra = 0
    can_delete = False
    #exclude = ['product_type']

def subscribe_actions_iter():
    for product in get_products(hidden=True):
        def create_subscribe_action(product):
            def subscribe_action(modeladmin, request, accounts):
                for account in accounts:
                    account.subscribe_to_product(product)
                if len(accounts) == 1:
                    message_bit = '1 user was'
                else:
                    message_bit = '%s users were' % len(accounts)
                message = '%s successfully subscribed to %s' % (message_bit, product.name)
                modeladmin.message_user(request, message)
            subscribe_action.__name__ = 'subscribe_to_%s' % product.name
            return subscribe_action
        yield create_subscribe_action(product)

class AccountAdmin(admin.ModelAdmin):
    search_fields = ['owner__id', 'owner__username', 'owner__email']
    list_display = [
        '__unicode__',
        lambda x: x.get_current_product_class().name,
        lambda x: x.owner.id,
        lambda x: x.owner.username,
        lambda x: x.owner.email,
    ]
    actions = list(subscribe_actions_iter())
    inlines = [SubscriptionInline]
    raw_id_fields = ['owner']

class SubscriptionAdmin(admin.ModelAdmin):
    list_filter = ['product_type']

admin.site.register(Account, AccountAdmin)
admin.site.register(Subscription, SubscriptionAdmin)

########NEW FILE########
__FILENAME__ = forms
from django import forms

class SubscriptionConfirmationForm(forms.Form):
    def save(self, commit=False):
        pass

########NEW FILE########
__FILENAME__ = loading
from django.conf import settings

from ordereddict import OrderedDict

from pricing.products import Product
from pricing.manual_intervention import ManualPreApproval
#from billing.adjustments import Adjustment

def import_item(x):
    mod_name, cls_name = x.rsplit('.', 1)
    return from_x_import_y(mod_name, cls_name)

def from_x_import_y(x, y):
    # from mod_name import cls_name
    module = __import__(x, fromlist=x.rsplit('.', 1)[0])
    return getattr(module, y)


adjustments_cache = {}

def collect_products_from_modules(modules):
    products = []
    # populate the cache
    if isinstance(modules, basestring):
        modules = (modules,)
    for module_name in modules:
        mod = __import__(module_name, fromlist=module_name.rsplit('.', 1)[0])
        for name, obj in mod.__dict__.items():
            if isinstance(obj, type):
                if issubclass(obj, Product):
                    products.append(obj)
        #        if issubclass(obj, Adjustment):
        #            adjustment_cache[name] = obj
    return products

BILLING_DEFINITIONS = getattr(settings, 'BILLING_DEFINITIONS', ())
BILLING_PRODUCTS = getattr(settings, 'BILLING_PRODUCTS', None)

def populate_product_cache(products=BILLING_PRODUCTS):
    """ returns the populated cache using products as defined in settings.py

    If defined, products must be one of:
        a list of product classes
        a (base_module, [product_class]) tuple
        a module containing product classes
    """
    if not products:
        product_classes = []
    elif isinstance(products, basestring):
        # we have a module containing products
        product_classes = collect_products_from_modules(products)
        product_classes.sort(key=lambda x: x.base_price)
    elif all(isinstance(i, basestring) for i in products):
        # we have a list of products
        product_classes = [import_item(p) for p in products]
    elif len(products) == 2:
        base_module, classes = products
        product_classes = [from_x_import_y(base_module, cls) for cls in classes]
    else:
        raise ValueError("""Invalid value for "product"
        If defined, products must be one of:
            a list of product classes
            a (base_module, [product_class]) tuple
            a module containing product classes
        """)
    return OrderedDict((pc.name, pc) for pc in product_classes)

product_cache = populate_product_cache()

def get_product(name):
    try:
        return product_cache[name]
    except KeyError:
        raise ValueError('"%s" is not a valid product name' % name)

#def get_adjustment(name):
#    return adjustments_cache[name]

def get_products(hidden=False):
    def is_hidden(product):
        return (not hidden) and (p.manual_intervention is ManualPreApproval)
    return [p for p in product_cache.values() if not is_hidden(p)]


# load the billing processors
BILLING_PROCESSORS = getattr(settings, 'BILLING_PROCESSORS', {})

processor_cache = {}

for k,v in BILLING_PROCESSORS.items():
    processor_cache[k] = import_item(v)

def get_processor(name):
    try:
        return processor_cache[name]
    except KeyError:
        raise ValueError('"%s" is not a valid processor name' % name)


########NEW FILE########
__FILENAME__ = management
import billing.models
from billing.models import ProductType
from billing.loading import get_products
from django.db.models import signals
import south.signals

# implementation taken from django.contrib.contenttypes:
# https://github.com/django/django/blob/1.3.X/django/contrib/contenttypes/management.py

def update_producttypes(app, verbosity=2, **kwargs):
    # only do this once, after we're synced
    if app == 'billing' or app == billing.models:
        update_all_producttypes(verbosity, **kwargs)
    else:
        return
    

def update_all_producttypes(verbosity=2, **kwargs):
    
    product_types = list(ProductType.objects.all())
    for product in get_products(hidden=True):
        try:
            pt = ProductType.objects.get(name=product.__name__)
            product_types.remove(pt)
        except ProductType.DoesNotExist:
            pt = ProductType(name=product.__name__)
            pt.save()
            if verbosity >= 2:
                print "Adding product type '%s'" % (pt.name)
    # The presence of any remaining product types means the supplied app has an
    # undefined product. Confirm that the product type is stale before deletion.
    if product_types:
        if kwargs.get('interactive', False):
            prodcut_type_display = '\n'.join(['    %s' % pt.name for pt in product_types])
            ok_to_delete = raw_input("""The following product types are stale and need to be deleted:

%s

Any objects related to these product types by a foreign key will also
be deleted. Are you sure you want to delete these product types?
If you're unsure, answer 'no'.

    Type 'yes' to continue, or 'no' to cancel: """ % product_type_display)
        else:
            ok_to_delete = False

        if ok_to_delete == 'yes':
            for pt in product_types:
                if verbosity >= 2:
                    print "Deleting stale product type '%s'" % pt.name
                pt.delete()
        else:
            if verbosity >= 2:
                print "Stale product types remain."
            

signals.post_syncdb.connect(update_producttypes)
south.signals.post_migrate.connect(update_producttypes)

if __name__ == "__main__":
    update_all_contenttypes()

########NEW FILE########
__FILENAME__ = 0001_initial
# encoding: utf-8
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models

class Migration(SchemaMigration):

    def forwards(self, orm):
        
        # Adding model 'Account'
        db.create_table('billing_account', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('owner', self.gf('annoying.fields.AutoOneToOneField')(related_name='billing_account', unique=True, to=orm['auth.User'])),
        ))
        db.send_create_signal('billing', ['Account'])

        # Adding model 'ProductType'
        db.create_table('billing_producttype', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('name', self.gf('django.db.models.fields.CharField')(max_length=100)),
        ))
        db.send_create_signal('billing', ['ProductType'])

        # Adding model 'Subscription'
        db.create_table('billing_subscription', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('billing_account', self.gf('django.db.models.fields.related.ForeignKey')(related_name='subscriptions', to=orm['billing.Account'])),
            ('product_type', self.gf('django.db.models.fields.related.ForeignKey')(related_name='subscriptions', to=orm['billing.ProductType'])),
            ('date_created', self.gf('django.db.models.fields.DateTimeField')(auto_now_add=True, blank=True)),
        ))
        db.send_create_signal('billing', ['Subscription'])

        # Adding model 'SubscriptionApprovalStatus'
        db.create_table('billing_subscriptionapprovalstatus', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('created', self.gf('model_utils.fields.AutoCreatedField')(default=datetime.datetime.now)),
            ('modified', self.gf('model_utils.fields.AutoLastModifiedField')(default=datetime.datetime.now)),
            ('status', self.gf('django.db.models.fields.CharField')(default='pending', max_length=20)),
            ('subscription', self.gf('django.db.models.fields.related.ForeignKey')(related_name='approval_statuses', to=orm['billing.Subscription'])),
            ('note', self.gf('django.db.models.fields.TextField')(blank=True)),
        ))
        db.send_create_signal('billing', ['SubscriptionApprovalStatus'])

        # Adding model 'AdjustmentType'
        db.create_table('billing_adjustmenttype', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
        ))
        db.send_create_signal('billing', ['AdjustmentType'])

        # Adding model 'Adjustment'
        db.create_table('billing_adjustment', (
            ('id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('adjustment_type', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['billing.AdjustmentType'])),
            ('adjustment_value', self.gf('jsonfield.fields.JSONField')()),
            ('subscription', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['billing.Subscription'])),
        ))
        db.send_create_signal('billing', ['Adjustment'])


    def backwards(self, orm):
        
        # Deleting model 'Account'
        db.delete_table('billing_account')

        # Deleting model 'ProductType'
        db.delete_table('billing_producttype')

        # Deleting model 'Subscription'
        db.delete_table('billing_subscription')

        # Deleting model 'SubscriptionApprovalStatus'
        db.delete_table('billing_subscriptionapprovalstatus')

        # Deleting model 'AdjustmentType'
        db.delete_table('billing_adjustmenttype')

        # Deleting model 'Adjustment'
        db.delete_table('billing_adjustment')


    models = {
        'auth.group': {
            'Meta': {'object_name': 'Group'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        'auth.permission': {
            'Meta': {'ordering': "('content_type__app_label', 'content_type__model', 'codename')", 'unique_together': "(('content_type', 'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        'billing.account': {
            'Meta': {'object_name': 'Account'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'owner': ('annoying.fields.AutoOneToOneField', [], {'related_name': "'billing_account'", 'unique': 'True', 'to': "orm['auth.User']"})
        },
        'billing.adjustment': {
            'Meta': {'object_name': 'Adjustment'},
            'adjustment_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['billing.AdjustmentType']"}),
            'adjustment_value': ('jsonfield.fields.JSONField', [], {}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'subscription': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['billing.Subscription']"})
        },
        'billing.adjustmenttype': {
            'Meta': {'object_name': 'AdjustmentType'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'})
        },
        'billing.producttype': {
            'Meta': {'object_name': 'ProductType'},
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'billing.subscription': {
            'Meta': {'object_name': 'Subscription'},
            'billing_account': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'subscriptions'", 'to': "orm['billing.Account']"}),
            'date_created': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'product_type': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'subscriptions'", 'to': "orm['billing.ProductType']"})
        },
        'billing.subscriptionapprovalstatus': {
            'Meta': {'object_name': 'SubscriptionApprovalStatus'},
            'created': ('model_utils.fields.AutoCreatedField', [], {'default': 'datetime.datetime.now'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'modified': ('model_utils.fields.AutoLastModifiedField', [], {'default': 'datetime.datetime.now'}),
            'note': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'status': ('django.db.models.fields.CharField', [], {'default': "'pending'", 'max_length': '20'}),
            'subscription': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "'approval_statuses'", 'to': "orm['billing.Subscription']"})
        },
        'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        }
    }

    complete_apps = ['billing']

########NEW FILE########
__FILENAME__ = models
from django.db import models
from django.db.models import signals
from django.dispatch import receiver
from django.conf import settings
from annoying.fields import AutoOneToOneField
from jsonfield import JSONField
from model_utils import Choices
from model_utils.models import TimeStampedModel

import billing.loading
from billing.processor.utils import router as processor_router
from billing.signals import ready_for_approval

#BILLING_ACCOUNT = getattr(settings, 'BILLING_ACCOUNT', SimpleAccount)

#class BaseAccount(models.Model):
#    """
#    BaseAccount should be subclassed (porbably by a specific payment
#    processor backend) to implement specific account types
#    
#    subclasses must implement a "XX" method, which returns XX.
#    
#    """
#    owner = AutoOneToOneField(User, related_name='billing_account')
#    date_created = models.DateTimeField(auto_now_add=True)
#    content_type = models.ForeignKey(ContentType, editable=False, null=True)

#    # stuff to enable subclassing
#    def save(self):
#        if not self.content_type:
#            if self.__class__ is BaseAccount:
#                raise RuntimeError('BaseAccount must be subclassed')
#            self.content_type = ContentType.objects.get_for_model(self.__class__)
#        super(BaseAccount, self).save()

#    def get_subclass(self):
#        model = self.content_type.model_class()
#        if(model == BaseAccount):
#            raise RuntimeError('BaseAccount must be subclassed')
#        return model

#    def get_subclass_instance(self):
#        return self.get_subclass().objects.get(id=self.id)



class Account(models.Model):
    owner = AutoOneToOneField('auth.User', related_name='billing_account')
    def get_current_subscription(self):
        active_statuses = 'pending', 'approved'
        active_subs = Subscription.objects.  \
            filter_by_current_statuses(active_statuses).  \
            filter(billing_account=self).order_by('-date_created')
        subs = active_subs
        #subs = self.subscriptions.order_by('-date_created')
        r = list(subs[:1])
        if r:
          return r[0]
        return None
    def get_current_product(self):
        pc = self.get_current_product_class()
        if pc:
            return pc()
        #sub = self.get_current_subscription()
        #if sub:
            #return sub.get_product()
            #return ()
        return None
    def get_current_product_class(self):
        sub = self.get_current_subscription()
        if sub:
            return sub.get_product_class()
        elif hasattr(settings, 'BILLING_DEFAULT_PRODUCT'):
            return billing.loading.get_product(settings.BILLING_DEFAULT_PRODUCT)
        return None
    def get_processor(self):
        return processor_router.get_processor_for_account(self)
    def has_valid_billing_details(self):
        return self.get_processor().has_valid_billing_details(self)
    def subscribe_to_product(self, product):
        return Subscription.objects.create_from_product(product, self)
    def get_visible_products(self):
        """ returns the list of products that is visible to the given account """
        all_products = billing.loading.get_products(hidden=True)
        public_products = billing.loading.get_products()
        subscribed_product_types = ProductType.objects  \
            .filter(subscriptions__billing_account=self)  \
            .distinct()
        subscribed_products = set(pt.get_product_class() for pt in subscribed_product_types)
        visible_products = set(public_products).union(subscribed_products)
        return [p for p in all_products if p in visible_products]
    def __unicode__(self):
        return "%s's account" % unicode(self.owner)
    def __repr__(self):
        return "Account(owner=%s)" % repr(self.owner)

class ProductTypeManager(models.Manager):
    def get_for_product(self, product):
        return self.get(name=product.__name__)
    def get_by_natural_key(self, name):
        return self.get(name=name)

class ProductType(models.Model):
    name = models.CharField(max_length=100)
    objects = ProductTypeManager()
    def get_product_class(self):
        return billing.loading.get_product(self.name)
    def __unicode__(self):
        return self.name
    def __repr__(self):
        return 'ProductType(name=%s)' % self.name
    def natural_key(self):
        return (self.name,)

class SubscriptionManager(models.Manager):
    def filter_by_current_statuses(self, statuses):
        """
        returns the subscriptions whose most recent status is
        one of those specified
        """
        
        annotated = self.annotate(
            newest=models.Max('approval_statuses__created'))
        newest_subs = annotated.filter(
            approval_statuses__created=models.F('newest'),
            approval_statuses__status__in=statuses
        )
        return newest_subs
    def filter_by_current_status(self, status):
        """
        returns the subscriptions whose most recent status is that specified
        """
        return self.filter_by_current_statuses([status])
        
    def pending(self):
        return self.filter_by_current_status(status='pending')
    def approved(self):
        return self.filter_by_current_status(status='approved')
    def declined(self):
        return self.filter_by_current_status(status='declined')
    def create_from_product(self, product, billing_account):
        if isinstance(product, basestring):
            name = product
        else:
            name = product.name
        pt = ProductType.objects.get(name=name)
        sub = self.create(billing_account=billing_account, product_type=pt)
        sub.request_approval()

ACTIVE_SUBSCIPRTION_STATUSES = getattr(settings,
    'BILLING_ACTIVE_SUBSCIPRTION_STATUSES', ('pending', 'approved'))  

class Subscription(models.Model):
    APPROVAL_STATUS = Choices('pending', 'approved', 'declined')
    objects = SubscriptionManager()
    billing_account = models.ForeignKey(Account, related_name='subscriptions')
    product_type = models.ForeignKey(
        ProductType, related_name='subscriptions')
    date_created = models.DateTimeField(auto_now_add=True)
    def get_product(self):
        unadjusted_product = self.product_type.get_product_class()
        # this should apply adjustments
        adjustments = Adjustment.objects.filter(subscription=self)
        return unadjusted_product()
    def get_product_class(self):
        return self.product_type.get_product_class()
    def get_current_approval_status(self):
        statuses = self.approval_statuses.order_by('-created')
        r = list(statuses[:1])
        if r:
          return r[0].status
        return None
    def set_current_approval_status(self, status, note=''):
        # Choices is a tuple: (db rep, py identifier, human readable)
        if status not in zip(*self.APPROVAL_STATUS)[1]:
            raise ValueError('"%s" is not a valid status' % status)
        SubscriptionApprovalStatus.objects.create(
            status=status, subscription=self, note=note)
    def is_active(self):
        cur_stat = self.get_current_approval_status()
        return cur_stat in ACTIVE_SUBSCIPRTION_STATUSES
    def request_approval(self):
        ready_for_approval.send(sender=self)
    def __unicode__(self):
        return '%s (%s)' % (self.product_type.name, self.get_current_approval_status())
    def __repr__(self):
        return 'Subscription(product=%s, approval_status=%s)' % (self.product_type.name, self.get_current_approval_status())

@receiver(signals.post_save, sender=Subscription)
def auto_add_subscription_approval_status(instance, created, **kwargs):
    if created:
        instance.set_current_approval_status('pending')
        #SubscriptionApprovalStatus.objects.create(subscription=instance)
        

class SubscriptionApprovalStatus(TimeStampedModel):
    STATUS = Subscription.APPROVAL_STATUS
    status = models.CharField(
        choices=STATUS, default=STATUS.pending, max_length=20)
    subscription = models.ForeignKey(
        Subscription, related_name='approval_statuses')
    note = models.TextField(blank=True)
    def __unicode__(self):
        return 'SubscriptionApprovalStatus(subscription=%s, status=%s)' % (self.subscription, self.status)
    def __repr__(self):
        return self.__unicode__()

class AdjustmentType(models.Model):
    def adjustment_class(self):
        pass

class Adjustment(models.Model):
    adjustment_type = models.ForeignKey(AdjustmentType)
    adjustment_value = JSONField()
    subscription = models.ForeignKey(Subscription)

########NEW FILE########
__FILENAME__ = api

class BillingProcessor(object):
    def get_billing_details_form(self, billing_account):
        return self.billing_details_form
    def has_valid_billing_details(self):
        raise NotImplementedError('has_valid_billing_details() must be over-ridden by subclasses')

########NEW FILE########
__FILENAME__ = forms
from django import forms

from billing.processor.simple_account.models import IOUAccount, AccountIOU

class IOUAccountCreationForm(forms.ModelForm):
    def save(self, commit=True):
        iou = super(IOUAccountCreationForm, self).save(commit=False)
        iou_account = IOUAccount(billing_account=self.billing_account)
        iou_account.save()
        iou.iou_account = iou_account
        if commit:
            iou.save()
        return iou
    class Meta:
        model = AccountIOU
        fields = ('has_agreed_to_pay',)

class IOUAccountUpdateForm(forms.ModelForm):
    def save(self, commit=True):
        iou = super(IOUAccountUpdateForm, self).save(commit=False)
        iou_account = self.billing_account.simple_processor_iou_account
        iou.iou_account = iou_account
        if commit:
            iou.save()
        return iou
    class Meta:
        model = AccountIOU
        fields = ('has_agreed_to_pay',)

def get_billing_details_form(billing_account):
    """
    If the billing account already has an IOU account, return the update
    form. If there isn't an account yet, then return the creation form
    """
    try:
        iou_account = billing_account.simple_processor_iou_account
        return IOUAccountUpdateForm
    except IOUAccount.DoesNotExist:
        return IOUAccountCreationForm

########NEW FILE########
__FILENAME__ = models

from django.db import models
from django.dispatch import receiver

from billing.signals import ready_for_approval

# account-based immutable processor

class IOUAccount(models.Model):
    billing_account = models.OneToOneField(
        'billing.Account', related_name='simple_processor_iou_account')

class AccountIOU(models.Model):
    iou_account = models.ForeignKey(
        'IOUAccount', related_name='simple_processor_ious')
    has_agreed_to_pay = models.BooleanField(default=False)
    created = models.DateTimeField(auto_now_add=True)
    class Meta:
        ordering = ['-created']
        get_latest_by = 'created'
    def __unicode__(self):
        return 'AccountIOU(has_agreed_to_pay=%s)' % self.has_agreed_to_pay
    

def has_valid_billing_details(account):
    try:
        iou_account = account.simple_processor_iou_account
    except IOUAccount.DoesNotExist:
        return False
    return iou_account.simple_processor_ious.latest().has_agreed_to_pay

@receiver(ready_for_approval)
def do_subscription_approval(sender, **kwargs):
    """ `sender` is the subscription instance requiring approval """
    req_payment = sender.get_product_class().get_requires_payment_details()
    if not req_payment or has_valid_billing_details(sender.billing_account):
        status = 'approved'
    else:
        status = 'declined'
    sender.set_current_approval_status(status)
    return status

########NEW FILE########
__FILENAME__ = processor

from billing.processor.api import BillingProcessor

from billing.processor.simple_account.forms import get_billing_details_form
from billing.processor.simple_account.models import has_valid_billing_details

class SimpleAccountBillingProcessor(BillingProcessor):
    has_valid_billing_details = staticmethod(has_valid_billing_details)
    get_billing_details_form = staticmethod(get_billing_details_form)



########NEW FILE########
__FILENAME__ = utils
from django.conf import settings

from billing.loading import get_processor, import_item

__all__ = ('router',)

class BaseProcessorRouter(object):
    def get_processor_for_account(self, account):
        raise NotImplementedError(
            'get_processor_for_account() should be implemented by subclass')

class MasterProcessorRouter(BaseProcessorRouter):
    def __init__(self, router_list):
        self.routers = []
        for pr in BILLING_PROCESSOR_ROUTERS:
            routers.append(import_item(pr))
    def get_processor_for_account(self, account):
        return get_processor(self.get_processor_name_for_account(account))
    def get_processor_name_for_account(self, account):
        chosen_processor = None
        for router in self.routers:
            try:
                method = router.get_processor_for_account
            except AttributeError:
                pass
            else:
                chosen_processor = method(account)
                if chosen_processor:
                    return chosen_processor
        return 'default'


# load the billing processor routers
BILLING_PROCESSOR_ROUTERS = getattr(settings, 'BILLING_PROCESSOR_ROUTERS', ())

router = MasterProcessorRouter(BILLING_PROCESSOR_ROUTERS)

########NEW FILE########
__FILENAME__ = signals
from django.dispatch import Signal

ready_for_approval = Signal(providing_args=[])

########NEW FILE########
__FILENAME__ = billing_tags
from django import template

import billing.loading
from pricing.products import Product

register = template.Library()

@register.filter
def product_change_type(product, user):
    upc = user.billing_account.get_current_product_class()
    if isinstance(product, Product):
        product = type(product)
    if upc:
        products = billing.loading.get_products(hidden=True)
        upc_index = products.index(upc)
        p_index = products.index(product)
        if upc_index < p_index:
            return 'upgrade'
        elif upc_index == p_index:
            return None
        else:
            return 'downgrade'
    else:
        return 'upgrade'

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import patterns, include, url
from django.contrib.auth.decorators import login_required

from billing.views import BillingOverviewView, subscription_view
from billing.views import BillingHistoryView, BillingDetailsView

urlpatterns = patterns('',
    url(r'^$', login_required(BillingOverviewView.as_view()), name='billing_overview'),
    url(r'^subscription/(?P<product>[\w]+)/$',
        login_required(subscription_view()),
        name='billing_subscription'),
    url(r'^history/$',
        login_required(BillingHistoryView.as_view()),
        name='billing_history'),
    url(r'^details/$',
        login_required(BillingDetailsView.as_view()),
        name='billing_details'),
)

########NEW FILE########
__FILENAME__ = views
from django.views.generic import TemplateView, FormView
from django.core.urlresolvers import reverse
from django.http import Http404

import billing.loading
import billing.processor
from billing.forms import SubscriptionConfirmationForm
from billing.models import Subscription, ProductType


class BillingOverviewView(TemplateView):
    """
    presents a list/descriptions of the different products on offer
    
    Should display links to the various product pages so users can upgrade
    or downgrade their current subscription.
    """
    template_name = 'billing/overview.html'
    def get_context_data(self, **kwargs):
        # Call the base implementation first to get a context
        context = super(BillingOverviewView, self).get_context_data(**kwargs)
        # Add in a list of all the products
        context['all_products'] = billing.loading.get_products(hidden=True)
        context['public_products'] = billing.loading.get_products()
        billing_account = self.request.user.billing_account
        context['billing_account'] = billing_account
        context['products'] = billing_account.get_visible_products()
        current_product = billing_account.get_current_product_class()
        context['current_product'] = current_product
        return context

class BaseBillingDetailsView(FormView):
    def get_success_url(self):
        return self.request.path
    def form_valid(self, form):
        ba = self.request.user.billing_account

        # let billing processor save details
        form.billing_account = ba
        form.save()

        # do redirect (or do more processing by ignoring return value)
        return super(BaseBillingDetailsView, self).form_valid(form)

class BaseSubscriptionView(BaseBillingDetailsView):
    def get_context_data(self, **kwargs):
        # Call the base implementation first to get a context
        context = super(BaseSubscriptionView, self).get_context_data(**kwargs)
        product = billing.loading.get_product(self.kwargs['product'])
        context['product'] = product
        return context
    def form_valid(self, form):
        response = super(BaseSubscriptionView, self).form_valid(form)

        ba = self.request.user.billing_account

        # create subscription
        ba.subscribe_to_product(self.kwargs['product'])

        # return the redirect
        return response

class SubscriptionConfirmationView(BaseSubscriptionView):
    """
    Confirms the change of subscription when payment info doesn't
    need to be collected. Subscribes user to given product.
    """
    form_class = SubscriptionConfirmationForm
    def get_template_names(self):
        product_name = self.kwargs['product']
        template_names = [
            'billing/subscription_confirmation_%s.html' % product_name,
            'billing/subscription_confirmation.html'
        ]
        return template_names


class BillingDetailsView(BaseBillingDetailsView):
    """
    Displays the user's currently recorded billing details.
    Allows updating of billing details (using the billing details collection
    form supplied by the payment processor) without changing the user's
    subscription.
    """
    template_name = 'billing/details.html'
    def get_form_class(self):
        billing_account = self.request.user.billing_account
        processor = billing_account.get_processor()
        return processor.get_billing_details_form(billing_account)


class SubscriptionBillingDetailsView(BaseSubscriptionView, BillingDetailsView):
    """
    Collects billing details (using the billing details collection form
    supplied by the payment processor) and subscribes user to the given product
    """
    def get_template_names(self):
        product_name = self.kwargs['product']
        template_names = [
            'billing/subscription_billing_details_%s.html' % product_name,
            'billing/subscription_billing_details.html'
        ]
        return template_names

class CurrentSubscriptionView(TemplateView):
    """
    Shown when a user visits the subscription page for their current product
    
    Primarily used when a user has successfully subscribed to a product
    """
    template_name = 'billing/current_subscription.html'
    def get_context_data(self, **kwargs):
        # Call the base implementation first to get a context
        context = super(CurrentSubscriptionView, self).get_context_data(**kwargs)
        cur_sub = self.request.user.billing_account.get_current_subscription()
        context['current_subscription'] = cur_sub
        return context

class BillingHistoryView(TemplateView):
    template_name = 'billing/history.html'
    pass
    

def subscription_view(
    current_subscription_view=CurrentSubscriptionView.as_view(),
    billing_details_view=SubscriptionBillingDetailsView.as_view(),
    confirmation_view=SubscriptionConfirmationView.as_view(),
):
    """
    returns a function to conditionally dispatch a view based on
    a user's current subscription status
    
    If the user is already subscribed to the plan, dispatch the
    current_subscription_view
    
    If the plan requires billing details, and the user doesn't have
    billing details on file (as reported by the processor), then
    dispatch the billing_details_view
    
    Otherwise (if the plan doesn't require billing details, or the
    user already has billing details on file), then dispatch the
    confirmation_view
    """
    def dispatch(request, *args, **kwargs):
        cur_product_cls = request.user.billing_account.get_current_product_class()
        req_product_name = kwargs['product']
        try:
            req_product_cls = billing.loading.get_product(req_product_name)
        except ValueError:
            raise Http404
        if req_product_cls not in request.user.billing_account.get_visible_products():
            raise Http404
        if cur_product_cls == req_product_cls:
            return current_subscription_view(request, *args, **kwargs)
        elif (
            req_product_cls.get_requires_payment_details()
            and not request.user.billing_account.has_valid_billing_details()
        ):
            return billing_details_view(request, *args, **kwargs)
        elif (
            not req_product_cls.get_requires_payment_details()
            or request.user.billing_account.has_valid_billing_details()
        ):
            return confirmation_view(request, *args, **kwargs)
        else:
            raise RuntimeError('Error: null condition should never occur')
    return dispatch


########NEW FILE########
__FILENAME__ = subscribe_user_to_product
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth.models import User
from billing.loading import get_products
from pricing.manual_intervention import ManualPreApproval

class Command(BaseCommand):
    help = "Subscribes the given user to a product.\n"  \
    "Lists available products if no arguments are given"
    args = "<userid|username> <product_name>"

    def handle(self, *args, **options):
        if len(args) == 0:
            # show list of plans
            def get_plan_str(p):
                hidden = p.manual_intervention is ManualPreApproval
                return '%s%s' % (p.name, ' (hidden)' if hidden else '')
            plan_strs = [get_plan_str(p) for p in get_products(hidden=True)]
            self.stdout.write(
                '\nAvailable plans:\n\n%s' %
                '\n'.join(plan_strs)
            )
            self.stdout.write('\n\n\nFor full help, use --help\n\n')
            return
        elif len(args) != 2:
            raise CommandError(
                'Exactly two arguments are needed: a user and a product')
        userarg, product_name = args
        try:
            user_by_name = User.objects.get(username=userarg)
        except User.DoesNotExist:
            user_by_name = None
        try:
            userid = int(userarg)
        except ValueError:
            userid = None
        try:
            user_by_id = User.objects.get(id=userid)
        except User.DoesNotExist:
            user_by_id = None
        if user_by_name is None and user_by_id is None:
            raise CommandError('No such user found')
        elif user_by_name is not None and user_by_id is not None:
            if user_by_name == user_by_id:
                user = user_by_id
            else:
                raise CommandError('Two users match: one by id and one by username')
        else:
            user = user_by_name or user_by_id
        user.billing_account.subscribe_to_product(product_name)
        self.stdout.write(
            '\nSuccessfully subscribed User(id=%s, username=%s, email=%s) to %s\n\n' %
            (user.id, user.username, user.email, product_name)
        )


########NEW FILE########
__FILENAME__ = models

########NEW FILE########
__FILENAME__ = billing
from example_saas_project.core.products import FreePlan, BronzePlan, SilverPlan, GoldPlan, SecretPlan, SecretFreePlan

# in the future this should be able to provide a form to store data about a person's
# subscription to a given plan

########NEW FILE########
__FILENAME__ = models

########NEW FILE########
__FILENAME__ = products
from pricing.products import Product
from pricing.features import IntegerFeature
from pricing.features import AllocatedFeature, MeteredFeature
from pricing.feature_pricing import FixedInclusion, FixedUnitPricing
from pricing.manual_intervention import ManualPreApproval, ManualPostApproval

class MySaaSAppAccount(Product):
    class Projects(IntegerFeature):
        def in_use(self, account):
            return Projects.objects.filter(account=account).count()
    
    class StorageSpace(IntegerFeature):
        """ 
        Assume we get hourly ticks that update how much storage is used
        at that moment. If we got real-time updates every time storage
        usage changed, then the billing scheme would be Allocated instead.
        
        """
        def in_use(self, account):
            return get_storage_in_use(account.user)


class GoldPlan(MySaaSAppAccount):
    base_price = 250
    class Projects(MySaaSAppAccount.Projects, AllocatedFeature):
        pricing_scheme=FixedInclusion(included=10)
    class StorageSpace(MySaaSAppAccount.StorageSpace, MeteredFeature):
        pricing_scheme=FixedUnitPricing(unit_price='0.10')


class SilverPlan(MySaaSAppAccount):
    base_price = 75
    class Projects(MySaaSAppAccount.Projects, AllocatedFeature):
        pricing_scheme=FixedInclusion(included=5)
    class StorageSpace(MySaaSAppAccount.StorageSpace, MeteredFeature):
        pricing_scheme=FixedUnitPricing(unit_price='0.15')


class BronzePlan(MySaaSAppAccount):
    base_price = 25
    class Projects(MySaaSAppAccount.Projects, AllocatedFeature):
        pricing_scheme=FixedInclusion(included=2)
    class StorageSpace(MySaaSAppAccount.StorageSpace, MeteredFeature):
        pricing_scheme=FixedUnitPricing(unit_price='0.20')

class FreePlan(MySaaSAppAccount):
    base_price = 0
    class Projects(MySaaSAppAccount.Projects, AllocatedFeature):
        pricing_scheme=FixedInclusion(included=1)
    class StorageSpace(MySaaSAppAccount.StorageSpace, MeteredFeature):
        pricing_scheme=FixedInclusion(included=0)

class SecretPlan(SilverPlan):
    base_price = 10
    manual_intervention = ManualPreApproval

class SecretFreePlan(BronzePlan):
    base_price = 0
    manual_intervention = ManualPreApproval

class EnterprisePlan(GoldPlan):
    manual_intervention = ManualPostApproval

class CustomPlan(GoldPlan):
    manual_intervention = ManualPreApproval

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
__FILENAME__ = settings
# Django settings for example_saas_project project.

DEBUG = True
TEMPLATE_DEBUG = DEBUG

ADMINS = (
    # ('Your Name', 'your_email@example.com'),
)

MANAGERS = ADMINS

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3', # Add 'postgresql_psycopg2', 'postgresql', 'mysql', 'sqlite3' or 'oracle'.
        'NAME': '/tmp/saas_project.db',                      # Or path to database file if using sqlite3.
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
TIME_ZONE = 'America/Chicago'

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

# URL prefix for admin static files -- CSS, JavaScript and images.
# Make sure to use a trailing slash.
# Examples: "http://foo.com/static/admin/", "/static/admin/".
ADMIN_MEDIA_PREFIX = '/static/admin/'

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
SECRET_KEY = '-rdi$jw%xdybfvas0=sxvu9!g$dbcnil2i+k0@v-ei1&+8yd56'

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
)

ROOT_URLCONF = 'example_saas_project.urls'

TEMPLATE_DIRS = (
    # Put strings here, like "/home/html/django_templates" or "C:/www/django/templates".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
)

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    # Uncomment the next line to enable the admin:
    # 'django.contrib.admin',
    # Uncomment the next line to enable admin documentation:
    # 'django.contrib.admindocs',
    'south',
    'billing',
    'billing_management',
    'billing.processor.simple_account',
    'example_saas_project.core',
)

BILLING_PRODUCTS = 'example_saas_project.core.billing'

BILLING_PROCESSORS = {
    'default': 'billing.processor.simple_account.processor.SimpleAccountBillingProcessor',
}

# A sample logging configuration. The only tangible logging
# performed by this configuration is to send an email to
# the site admins on every HTTP 500 error.
# See http://docs.djangoproject.com/en/dev/topics/logging for
# more details on how to customize your logging configuration.
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

import billing

# Uncomment the next two lines to enable the admin:
# from django.contrib import admin
# admin.autodiscover()

urlpatterns = patterns('',
    # Examples:
    # url(r'^$', 'example_saas_project.views.home', name='home'),
    # url(r'^example_saas_project/', include('example_saas_project.foo.urls')),

    # Uncomment the admin/doc line below to enable admin documentation:
    # url(r'^admin/doc/', include('django.contrib.admindocs.urls')),

    # Uncomment the next line to enable the admin:
    # url(r'^admin/', include(admin.site.urls)),
    url(r'^billing/', include('billing.urls')),
)

########NEW FILE########
