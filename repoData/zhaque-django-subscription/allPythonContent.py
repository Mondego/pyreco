__FILENAME__ = admin
from django import forms
from django.contrib import admin
from django.utils.html import conditional_escape as esc

from models import Subscription, UserSubscription, Transaction


def _pricing(sub):
    return sub.get_pricing_display()


def _trial(sub):
    return sub.get_trial_display()


class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ('name', _pricing, _trial)
admin.site.register(Subscription, SubscriptionAdmin)


def _subscription(trans):
    if trans.subscription != None:
        return u'<a href="/admin/subscription/subscription/%d/">%s</a>' % (
            trans.subscription.pk, esc(trans.subscription))
_subscription.allow_tags = True


def _user(trans):
    if trans.user != None:
        return u'<a href="/admin/auth/user/%d/">%s</a>' % (
            trans.user.pk, esc(trans.user))
_user.allow_tags = True


def _ipn(trans):
    if trans.ipn != None:
        return u'<a href="/admin/ipn/paypalipn/%d/">#%s</a>' % (
            trans.ipn.pk, trans.ipn.pk)
_ipn.allow_tags = True


class UserSubscriptionAdminForm(forms.ModelForm):
    class Meta:
        model = UserSubscription
    fix_group_membership = forms.fields.BooleanField(required=False)
    extend_subscription = forms.fields.BooleanField(required=False)


class UserSubscriptionAdmin(admin.ModelAdmin):
    list_display = ('__unicode__', _user, _subscription, 'active', 'expires', 'valid')
    list_display_links = ('__unicode__',)
    list_filter = ('active', 'subscription', )
    date_hierarchy = 'expires'
    form = UserSubscriptionAdminForm
    fieldsets = (
        (None, {'fields': ('user', 'subscription', 'expires', 'active')}),
        ('Actions', {'fields': ('fix_group_membership', 'extend_subscription'),
                     'classes': ('collapse',)}),
        )

    def save_model(self, request, obj, form, change):
        if form.cleaned_data['extend_subscription']:
            obj.extend()
        if form.cleaned_data['fix_group_membership']:
            obj.fix()
        obj.save()

    # action for Django-SVN or django-batch-admin app
    actions = ('fix', 'extend',)

    def fix(self, request, queryset):
        for us in queryset.all():
            us.fix()
    fix.short_description = 'Fix group membership'

    def extend(self, request, queryset):
        for us in queryset.all():
            us.extend()
    extend.short_description = 'Extend subscription'

admin.site.register(UserSubscription, UserSubscriptionAdmin)


class TransactionAdmin(admin.ModelAdmin):
    date_hierarchy = 'timestamp'
    list_display = ('timestamp', 'id', 'event', _subscription, _user, _ipn, 'amount', 'comment')
    list_display_links = ('timestamp', 'id')
    list_filter = ('subscription', 'user')
admin.site.register(Transaction, TransactionAdmin)

########NEW FILE########
__FILENAME__ = 0001_initial

from south.db import db
from django.db import models
from subscription.models import *

class Migration:
    
    def forwards(self, orm):
        
        # Adding model 'UserSubscription'
        db.create_table('subscription_usersubscription', (
            ('id', orm['subscription.UserSubscription:id']),
            ('user', orm['subscription.UserSubscription:user']),
            ('subscription', orm['subscription.UserSubscription:subscription']),
            ('expires', orm['subscription.UserSubscription:expires']),
            ('active', orm['subscription.UserSubscription:active']),
            ('cancelled', orm['subscription.UserSubscription:cancelled']),
        ))
        db.send_create_signal('subscription', ['UserSubscription'])
        
        # Adding model 'Transaction'
        db.create_table('subscription_transaction', (
            ('id', orm['subscription.Transaction:id']),
            ('timestamp', orm['subscription.Transaction:timestamp']),
            ('subscription', orm['subscription.Transaction:subscription']),
            ('user', orm['subscription.Transaction:user']),
            ('ipn', orm['subscription.Transaction:ipn']),
            ('event', orm['subscription.Transaction:event']),
            ('amount', orm['subscription.Transaction:amount']),
            ('comment', orm['subscription.Transaction:comment']),
        ))
        db.send_create_signal('subscription', ['Transaction'])
        
        # Adding model 'Subscription'
        db.create_table('subscription_subscription', (
            ('id', orm['subscription.Subscription:id']),
            ('name', orm['subscription.Subscription:name']),
            ('description', orm['subscription.Subscription:description']),
            ('price', orm['subscription.Subscription:price']),
            ('recurrence_period', orm['subscription.Subscription:recurrence_period']),
            ('recurrence_unit', orm['subscription.Subscription:recurrence_unit']),
            ('group', orm['subscription.Subscription:group']),
        ))
        db.send_create_signal('subscription', ['Subscription'])
        
        # Creating unique_together for [user, subscription] on UserSubscription.
        db.create_unique('subscription_usersubscription', ['user_id', 'subscription_id'])
        
    
    
    def backwards(self, orm):
        
        # Deleting model 'UserSubscription'
        db.delete_table('subscription_usersubscription')
        
        # Deleting model 'Transaction'
        db.delete_table('subscription_transaction')
        
        # Deleting model 'Subscription'
        db.delete_table('subscription_subscription')
        
        # Deleting unique_together for [user, subscription] on UserSubscription.
        db.delete_unique('subscription_usersubscription', ['user_id', 'subscription_id'])
        
    
    
    models = {
        'auth.group': {
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'blank': 'True'})
        },
        'auth.permission': {
            'Meta': {'unique_together': "(('content_type', 'codename'),)"},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'auth.user': {
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Group']", 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'blank': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        'contenttypes.contenttype': {
            'Meta': {'unique_together': "(('app_label', 'model'),)", 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'ipn.paypalipn': {
            'Meta': {'db_table': "'paypal_ipn'"},
            'address_city': ('django.db.models.fields.CharField', [], {'max_length': '40', 'blank': 'True'}),
            'address_country': ('django.db.models.fields.CharField', [], {'max_length': '64', 'blank': 'True'}),
            'address_country_code': ('django.db.models.fields.CharField', [], {'max_length': '64', 'blank': 'True'}),
            'address_name': ('django.db.models.fields.CharField', [], {'max_length': '128', 'blank': 'True'}),
            'address_state': ('django.db.models.fields.CharField', [], {'max_length': '40', 'blank': 'True'}),
            'address_status': ('django.db.models.fields.CharField', [], {'max_length': '11', 'blank': 'True'}),
            'address_street': ('django.db.models.fields.CharField', [], {'max_length': '200', 'blank': 'True'}),
            'address_zip': ('django.db.models.fields.CharField', [], {'max_length': '20', 'blank': 'True'}),
            'amount': ('django.db.models.fields.DecimalField', [], {'default': '0', 'null': 'True', 'max_digits': '64', 'decimal_places': '2', 'blank': 'True'}),
            'amount1': ('django.db.models.fields.DecimalField', [], {'default': '0', 'null': 'True', 'max_digits': '64', 'decimal_places': '2', 'blank': 'True'}),
            'amount2': ('django.db.models.fields.DecimalField', [], {'default': '0', 'null': 'True', 'max_digits': '64', 'decimal_places': '2', 'blank': 'True'}),
            'amount3': ('django.db.models.fields.DecimalField', [], {'default': '0', 'null': 'True', 'max_digits': '64', 'decimal_places': '2', 'blank': 'True'}),
            'amount_per_cycle': ('django.db.models.fields.DecimalField', [], {'default': '0', 'null': 'True', 'max_digits': '64', 'decimal_places': '2', 'blank': 'True'}),
            'auction_buyer_id': ('django.db.models.fields.CharField', [], {'max_length': '64', 'blank': 'True'}),
            'auction_closing_date': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'auction_multi_item': ('django.db.models.fields.IntegerField', [], {'default': '0', 'null': 'True', 'blank': 'True'}),
            'auth_amount': ('django.db.models.fields.DecimalField', [], {'default': '0', 'null': 'True', 'max_digits': '64', 'decimal_places': '2', 'blank': 'True'}),
            'auth_exp': ('django.db.models.fields.CharField', [], {'max_length': '28', 'blank': 'True'}),
            'auth_id': ('django.db.models.fields.CharField', [], {'max_length': '19', 'blank': 'True'}),
            'auth_status': ('django.db.models.fields.CharField', [], {'max_length': '9', 'blank': 'True'}),
            'business': ('django.db.models.fields.CharField', [], {'max_length': '127', 'blank': 'True'}),
            'case_creation_date': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'case_id': ('django.db.models.fields.CharField', [], {'max_length': '14', 'blank': 'True'}),
            'case_type': ('django.db.models.fields.CharField', [], {'max_length': '24', 'blank': 'True'}),
            'charset': ('django.db.models.fields.CharField', [], {'max_length': '32', 'blank': 'True'}),
            'contact_phone': ('django.db.models.fields.CharField', [], {'max_length': '20', 'blank': 'True'}),
            'created_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'currency_code': ('django.db.models.fields.CharField', [], {'default': "'USD'", 'max_length': '32', 'blank': 'True'}),
            'custom': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'exchange_rate': ('django.db.models.fields.DecimalField', [], {'default': '0', 'null': 'True', 'max_digits': '64', 'decimal_places': '16', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '64', 'blank': 'True'}),
            'flag': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'flag_code': ('django.db.models.fields.CharField', [], {'max_length': '16', 'blank': 'True'}),
            'flag_info': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'for_auction': ('django.db.models.fields.DecimalField', [], {'default': '0', 'null': 'True', 'max_digits': '64', 'decimal_places': '2', 'blank': 'True'}),
            'handling_amount': ('django.db.models.fields.DecimalField', [], {'default': '0', 'null': 'True', 'max_digits': '64', 'decimal_places': '2', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'initial_payment_amount': ('django.db.models.fields.DecimalField', [], {'default': '0', 'null': 'True', 'max_digits': '64', 'decimal_places': '2', 'blank': 'True'}),
            'invoice': ('django.db.models.fields.CharField', [], {'max_length': '127', 'blank': 'True'}),
            'ipaddress': ('django.db.models.fields.IPAddressField', [], {'max_length': '15', 'blank': 'True'}),
            'item_name': ('django.db.models.fields.CharField', [], {'max_length': '127', 'blank': 'True'}),
            'item_number': ('django.db.models.fields.CharField', [], {'max_length': '127', 'blank': 'True'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '64', 'blank': 'True'}),
            'mc_amount1': ('django.db.models.fields.DecimalField', [], {'default': '0', 'null': 'True', 'max_digits': '64', 'decimal_places': '2', 'blank': 'True'}),
            'mc_amount2': ('django.db.models.fields.DecimalField', [], {'default': '0', 'null': 'True', 'max_digits': '64', 'decimal_places': '2', 'blank': 'True'}),
            'mc_amount3': ('django.db.models.fields.DecimalField', [], {'default': '0', 'null': 'True', 'max_digits': '64', 'decimal_places': '2', 'blank': 'True'}),
            'mc_currency': ('django.db.models.fields.CharField', [], {'default': "'USD'", 'max_length': '32', 'blank': 'True'}),
            'mc_fee': ('django.db.models.fields.DecimalField', [], {'default': '0', 'null': 'True', 'max_digits': '64', 'decimal_places': '2', 'blank': 'True'}),
            'mc_gross': ('django.db.models.fields.DecimalField', [], {'default': '0', 'null': 'True', 'max_digits': '64', 'decimal_places': '2', 'blank': 'True'}),
            'mc_handling': ('django.db.models.fields.DecimalField', [], {'default': '0', 'null': 'True', 'max_digits': '64', 'decimal_places': '2', 'blank': 'True'}),
            'mc_shipping': ('django.db.models.fields.DecimalField', [], {'default': '0', 'null': 'True', 'max_digits': '64', 'decimal_places': '2', 'blank': 'True'}),
            'memo': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'next_payment_date': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'notify_version': ('django.db.models.fields.DecimalField', [], {'default': '0', 'null': 'True', 'max_digits': '64', 'decimal_places': '2', 'blank': 'True'}),
            'num_cart_items': ('django.db.models.fields.IntegerField', [], {'default': '0', 'null': 'True', 'blank': 'True'}),
            'option_name1': ('django.db.models.fields.CharField', [], {'max_length': '64', 'blank': 'True'}),
            'option_name2': ('django.db.models.fields.CharField', [], {'max_length': '64', 'blank': 'True'}),
            'outstanding_balance': ('django.db.models.fields.DecimalField', [], {'default': '0', 'null': 'True', 'max_digits': '64', 'decimal_places': '2', 'blank': 'True'}),
            'parent_txn_id': ('django.db.models.fields.CharField', [], {'max_length': '19', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '24', 'blank': 'True'}),
            'payer_business_name': ('django.db.models.fields.CharField', [], {'max_length': '127', 'blank': 'True'}),
            'payer_email': ('django.db.models.fields.CharField', [], {'max_length': '127', 'blank': 'True'}),
            'payer_id': ('django.db.models.fields.CharField', [], {'max_length': '13', 'blank': 'True'}),
            'payer_status': ('django.db.models.fields.CharField', [], {'max_length': '10', 'blank': 'True'}),
            'payment_cycle': ('django.db.models.fields.CharField', [], {'max_length': '32', 'blank': 'True'}),
            'payment_date': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'payment_gross': ('django.db.models.fields.DecimalField', [], {'default': '0', 'null': 'True', 'max_digits': '64', 'decimal_places': '2', 'blank': 'True'}),
            'payment_status': ('django.db.models.fields.CharField', [], {'max_length': '9', 'blank': 'True'}),
            'payment_type': ('django.db.models.fields.CharField', [], {'max_length': '7', 'blank': 'True'}),
            'pending_reason': ('django.db.models.fields.CharField', [], {'max_length': '14', 'blank': 'True'}),
            'period1': ('django.db.models.fields.CharField', [], {'max_length': '32', 'blank': 'True'}),
            'period2': ('django.db.models.fields.CharField', [], {'max_length': '32', 'blank': 'True'}),
            'period3': ('django.db.models.fields.CharField', [], {'max_length': '32', 'blank': 'True'}),
            'period_type': ('django.db.models.fields.CharField', [], {'max_length': '32', 'blank': 'True'}),
            'product_name': ('django.db.models.fields.CharField', [], {'max_length': '128', 'blank': 'True'}),
            'product_type': ('django.db.models.fields.CharField', [], {'max_length': '128', 'blank': 'True'}),
            'profile_status': ('django.db.models.fields.CharField', [], {'max_length': '32', 'blank': 'True'}),
            'protection_eligibility': ('django.db.models.fields.CharField', [], {'max_length': '32', 'blank': 'True'}),
            'quantity': ('django.db.models.fields.IntegerField', [], {'default': '1', 'null': 'True', 'blank': 'True'}),
            'query': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'reason_code': ('django.db.models.fields.CharField', [], {'max_length': '15', 'blank': 'True'}),
            'reattempt': ('django.db.models.fields.CharField', [], {'max_length': '1', 'blank': 'True'}),
            'receipt_id': ('django.db.models.fields.CharField', [], {'max_length': '64', 'blank': 'True'}),
            'receiver_email': ('django.db.models.fields.EmailField', [], {'max_length': '127', 'blank': 'True'}),
            'receiver_id': ('django.db.models.fields.CharField', [], {'max_length': '127', 'blank': 'True'}),
            'recur_times': ('django.db.models.fields.IntegerField', [], {'default': '0', 'null': 'True', 'blank': 'True'}),
            'recurring': ('django.db.models.fields.CharField', [], {'max_length': '1', 'blank': 'True'}),
            'recurring_payment_id': ('django.db.models.fields.CharField', [], {'max_length': '128', 'blank': 'True'}),
            'remaining_settle': ('django.db.models.fields.DecimalField', [], {'default': '0', 'null': 'True', 'max_digits': '64', 'decimal_places': '2', 'blank': 'True'}),
            'residence_country': ('django.db.models.fields.CharField', [], {'max_length': '2', 'blank': 'True'}),
            'response': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'retry_at': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'rp_invoice_id': ('django.db.models.fields.CharField', [], {'max_length': '127', 'blank': 'True'}),
            'settle_amount': ('django.db.models.fields.DecimalField', [], {'default': '0', 'null': 'True', 'max_digits': '64', 'decimal_places': '2', 'blank': 'True'}),
            'settle_currency': ('django.db.models.fields.CharField', [], {'max_length': '32', 'blank': 'True'}),
            'shipping': ('django.db.models.fields.DecimalField', [], {'default': '0', 'null': 'True', 'max_digits': '64', 'decimal_places': '2', 'blank': 'True'}),
            'shipping_method': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'subscr_date': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'subscr_effective': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'subscr_id': ('django.db.models.fields.CharField', [], {'max_length': '19', 'blank': 'True'}),
            'tax': ('django.db.models.fields.DecimalField', [], {'default': '0', 'null': 'True', 'max_digits': '64', 'decimal_places': '2', 'blank': 'True'}),
            'test_ipn': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'time_created': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'transaction_entity': ('django.db.models.fields.CharField', [], {'max_length': '7', 'blank': 'True'}),
            'transaction_subject': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'txn_id': ('django.db.models.fields.CharField', [], {'max_length': '19', 'blank': 'True'}),
            'txn_type': ('django.db.models.fields.CharField', [], {'max_length': '128', 'blank': 'True'}),
            'updated_at': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'max_length': '64', 'blank': 'True'}),
            'verify_sign': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'})
        },
        'subscription.subscription': {
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'group': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['auth.Group']", 'unique': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '100'}),
            'price': ('django.db.models.fields.DecimalField', [], {'max_digits': '64', 'decimal_places': '2'}),
            'recurrence_period': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'recurrence_unit': ('django.db.models.fields.CharField', [], {'max_length': '1', 'null': 'True'})
        },
        'subscription.transaction': {
            'amount': ('django.db.models.fields.DecimalField', [], {'null': 'True', 'max_digits': '64', 'decimal_places': '2', 'blank': 'True'}),
            'comment': ('django.db.models.fields.TextField', [], {'default': "''", 'blank': 'True'}),
            'event': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'ipn': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['ipn.PayPalIPN']", 'null': 'True', 'blank': 'True'}),
            'subscription': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['subscription.Subscription']", 'null': 'True', 'blank': 'True'}),
            'timestamp': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']", 'null': 'True', 'blank': 'True'})
        },
        'subscription.usersubscription': {
            'Meta': {'unique_together': "(('user', 'subscription'),)"},
            'active': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'blank': 'True'}),
            'cancelled': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'blank': 'True'}),
            'expires': ('django.db.models.fields.DateField', [], {'default': 'datetime.date.today', 'null': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'subscription': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['subscription.Subscription']"}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"})
        }
    }
    
    complete_apps = ['subscription']

########NEW FILE########
__FILENAME__ = 0002_trial_period

from south.db import db
from django.db import models
from subscription.models import *

class Migration:
    
    def forwards(self, orm):
        
        # Adding field 'Subscription.trial_period'
        db.add_column('subscription_subscription', 'trial_period', orm['subscription.subscription:trial_period'])
        
        # Adding field 'Subscription.trial_unit'
        db.add_column('subscription_subscription', 'trial_unit', orm['subscription.subscription:trial_unit'])
        
    
    
    def backwards(self, orm):
        
        # Deleting field 'Subscription.trial_period'
        db.delete_column('subscription_subscription', 'trial_period')
        
        # Deleting field 'Subscription.trial_unit'
        db.delete_column('subscription_subscription', 'trial_unit')
        
    
    
    models = {
        'auth.group': {
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'blank': 'True'})
        },
        'auth.permission': {
            'Meta': {'unique_together': "(('content_type', 'codename'),)"},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['contenttypes.ContentType']"}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        'auth.user': {
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Group']", 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'blank': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': "orm['auth.Permission']", 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        'contenttypes.contenttype': {
            'Meta': {'unique_together': "(('app_label', 'model'),)", 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        'ipn.paypalipn': {
            'Meta': {'db_table': "'paypal_ipn'"},
            'address_city': ('django.db.models.fields.CharField', [], {'max_length': '40', 'blank': 'True'}),
            'address_country': ('django.db.models.fields.CharField', [], {'max_length': '64', 'blank': 'True'}),
            'address_country_code': ('django.db.models.fields.CharField', [], {'max_length': '64', 'blank': 'True'}),
            'address_name': ('django.db.models.fields.CharField', [], {'max_length': '128', 'blank': 'True'}),
            'address_state': ('django.db.models.fields.CharField', [], {'max_length': '40', 'blank': 'True'}),
            'address_status': ('django.db.models.fields.CharField', [], {'max_length': '11', 'blank': 'True'}),
            'address_street': ('django.db.models.fields.CharField', [], {'max_length': '200', 'blank': 'True'}),
            'address_zip': ('django.db.models.fields.CharField', [], {'max_length': '20', 'blank': 'True'}),
            'amount': ('django.db.models.fields.DecimalField', [], {'default': '0', 'null': 'True', 'max_digits': '64', 'decimal_places': '2', 'blank': 'True'}),
            'amount1': ('django.db.models.fields.DecimalField', [], {'default': '0', 'null': 'True', 'max_digits': '64', 'decimal_places': '2', 'blank': 'True'}),
            'amount2': ('django.db.models.fields.DecimalField', [], {'default': '0', 'null': 'True', 'max_digits': '64', 'decimal_places': '2', 'blank': 'True'}),
            'amount3': ('django.db.models.fields.DecimalField', [], {'default': '0', 'null': 'True', 'max_digits': '64', 'decimal_places': '2', 'blank': 'True'}),
            'amount_per_cycle': ('django.db.models.fields.DecimalField', [], {'default': '0', 'null': 'True', 'max_digits': '64', 'decimal_places': '2', 'blank': 'True'}),
            'auction_buyer_id': ('django.db.models.fields.CharField', [], {'max_length': '64', 'blank': 'True'}),
            'auction_closing_date': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'auction_multi_item': ('django.db.models.fields.IntegerField', [], {'default': '0', 'null': 'True', 'blank': 'True'}),
            'auth_amount': ('django.db.models.fields.DecimalField', [], {'default': '0', 'null': 'True', 'max_digits': '64', 'decimal_places': '2', 'blank': 'True'}),
            'auth_exp': ('django.db.models.fields.CharField', [], {'max_length': '28', 'blank': 'True'}),
            'auth_id': ('django.db.models.fields.CharField', [], {'max_length': '19', 'blank': 'True'}),
            'auth_status': ('django.db.models.fields.CharField', [], {'max_length': '9', 'blank': 'True'}),
            'business': ('django.db.models.fields.CharField', [], {'max_length': '127', 'blank': 'True'}),
            'case_creation_date': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'case_id': ('django.db.models.fields.CharField', [], {'max_length': '14', 'blank': 'True'}),
            'case_type': ('django.db.models.fields.CharField', [], {'max_length': '24', 'blank': 'True'}),
            'charset': ('django.db.models.fields.CharField', [], {'max_length': '32', 'blank': 'True'}),
            'contact_phone': ('django.db.models.fields.CharField', [], {'max_length': '20', 'blank': 'True'}),
            'created_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'currency_code': ('django.db.models.fields.CharField', [], {'default': "'USD'", 'max_length': '32', 'blank': 'True'}),
            'custom': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'exchange_rate': ('django.db.models.fields.DecimalField', [], {'default': '0', 'null': 'True', 'max_digits': '64', 'decimal_places': '16', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '64', 'blank': 'True'}),
            'flag': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'flag_code': ('django.db.models.fields.CharField', [], {'max_length': '16', 'blank': 'True'}),
            'flag_info': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'for_auction': ('django.db.models.fields.DecimalField', [], {'default': '0', 'null': 'True', 'max_digits': '64', 'decimal_places': '2', 'blank': 'True'}),
            'handling_amount': ('django.db.models.fields.DecimalField', [], {'default': '0', 'null': 'True', 'max_digits': '64', 'decimal_places': '2', 'blank': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'initial_payment_amount': ('django.db.models.fields.DecimalField', [], {'default': '0', 'null': 'True', 'max_digits': '64', 'decimal_places': '2', 'blank': 'True'}),
            'invoice': ('django.db.models.fields.CharField', [], {'max_length': '127', 'blank': 'True'}),
            'ipaddress': ('django.db.models.fields.IPAddressField', [], {'max_length': '15', 'blank': 'True'}),
            'item_name': ('django.db.models.fields.CharField', [], {'max_length': '127', 'blank': 'True'}),
            'item_number': ('django.db.models.fields.CharField', [], {'max_length': '127', 'blank': 'True'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '64', 'blank': 'True'}),
            'mc_amount1': ('django.db.models.fields.DecimalField', [], {'default': '0', 'null': 'True', 'max_digits': '64', 'decimal_places': '2', 'blank': 'True'}),
            'mc_amount2': ('django.db.models.fields.DecimalField', [], {'default': '0', 'null': 'True', 'max_digits': '64', 'decimal_places': '2', 'blank': 'True'}),
            'mc_amount3': ('django.db.models.fields.DecimalField', [], {'default': '0', 'null': 'True', 'max_digits': '64', 'decimal_places': '2', 'blank': 'True'}),
            'mc_currency': ('django.db.models.fields.CharField', [], {'default': "'USD'", 'max_length': '32', 'blank': 'True'}),
            'mc_fee': ('django.db.models.fields.DecimalField', [], {'default': '0', 'null': 'True', 'max_digits': '64', 'decimal_places': '2', 'blank': 'True'}),
            'mc_gross': ('django.db.models.fields.DecimalField', [], {'default': '0', 'null': 'True', 'max_digits': '64', 'decimal_places': '2', 'blank': 'True'}),
            'mc_handling': ('django.db.models.fields.DecimalField', [], {'default': '0', 'null': 'True', 'max_digits': '64', 'decimal_places': '2', 'blank': 'True'}),
            'mc_shipping': ('django.db.models.fields.DecimalField', [], {'default': '0', 'null': 'True', 'max_digits': '64', 'decimal_places': '2', 'blank': 'True'}),
            'memo': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'next_payment_date': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'notify_version': ('django.db.models.fields.DecimalField', [], {'default': '0', 'null': 'True', 'max_digits': '64', 'decimal_places': '2', 'blank': 'True'}),
            'num_cart_items': ('django.db.models.fields.IntegerField', [], {'default': '0', 'null': 'True', 'blank': 'True'}),
            'option_name1': ('django.db.models.fields.CharField', [], {'max_length': '64', 'blank': 'True'}),
            'option_name2': ('django.db.models.fields.CharField', [], {'max_length': '64', 'blank': 'True'}),
            'outstanding_balance': ('django.db.models.fields.DecimalField', [], {'default': '0', 'null': 'True', 'max_digits': '64', 'decimal_places': '2', 'blank': 'True'}),
            'parent_txn_id': ('django.db.models.fields.CharField', [], {'max_length': '19', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '24', 'blank': 'True'}),
            'payer_business_name': ('django.db.models.fields.CharField', [], {'max_length': '127', 'blank': 'True'}),
            'payer_email': ('django.db.models.fields.CharField', [], {'max_length': '127', 'blank': 'True'}),
            'payer_id': ('django.db.models.fields.CharField', [], {'max_length': '13', 'blank': 'True'}),
            'payer_status': ('django.db.models.fields.CharField', [], {'max_length': '10', 'blank': 'True'}),
            'payment_cycle': ('django.db.models.fields.CharField', [], {'max_length': '32', 'blank': 'True'}),
            'payment_date': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'payment_gross': ('django.db.models.fields.DecimalField', [], {'default': '0', 'null': 'True', 'max_digits': '64', 'decimal_places': '2', 'blank': 'True'}),
            'payment_status': ('django.db.models.fields.CharField', [], {'max_length': '9', 'blank': 'True'}),
            'payment_type': ('django.db.models.fields.CharField', [], {'max_length': '7', 'blank': 'True'}),
            'pending_reason': ('django.db.models.fields.CharField', [], {'max_length': '14', 'blank': 'True'}),
            'period1': ('django.db.models.fields.CharField', [], {'max_length': '32', 'blank': 'True'}),
            'period2': ('django.db.models.fields.CharField', [], {'max_length': '32', 'blank': 'True'}),
            'period3': ('django.db.models.fields.CharField', [], {'max_length': '32', 'blank': 'True'}),
            'period_type': ('django.db.models.fields.CharField', [], {'max_length': '32', 'blank': 'True'}),
            'product_name': ('django.db.models.fields.CharField', [], {'max_length': '128', 'blank': 'True'}),
            'product_type': ('django.db.models.fields.CharField', [], {'max_length': '128', 'blank': 'True'}),
            'profile_status': ('django.db.models.fields.CharField', [], {'max_length': '32', 'blank': 'True'}),
            'protection_eligibility': ('django.db.models.fields.CharField', [], {'max_length': '32', 'blank': 'True'}),
            'quantity': ('django.db.models.fields.IntegerField', [], {'default': '1', 'null': 'True', 'blank': 'True'}),
            'query': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'reason_code': ('django.db.models.fields.CharField', [], {'max_length': '15', 'blank': 'True'}),
            'reattempt': ('django.db.models.fields.CharField', [], {'max_length': '1', 'blank': 'True'}),
            'receipt_id': ('django.db.models.fields.CharField', [], {'max_length': '64', 'blank': 'True'}),
            'receiver_email': ('django.db.models.fields.EmailField', [], {'max_length': '127', 'blank': 'True'}),
            'receiver_id': ('django.db.models.fields.CharField', [], {'max_length': '127', 'blank': 'True'}),
            'recur_times': ('django.db.models.fields.IntegerField', [], {'default': '0', 'null': 'True', 'blank': 'True'}),
            'recurring': ('django.db.models.fields.CharField', [], {'max_length': '1', 'blank': 'True'}),
            'recurring_payment_id': ('django.db.models.fields.CharField', [], {'max_length': '128', 'blank': 'True'}),
            'remaining_settle': ('django.db.models.fields.DecimalField', [], {'default': '0', 'null': 'True', 'max_digits': '64', 'decimal_places': '2', 'blank': 'True'}),
            'residence_country': ('django.db.models.fields.CharField', [], {'max_length': '2', 'blank': 'True'}),
            'response': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'retry_at': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'rp_invoice_id': ('django.db.models.fields.CharField', [], {'max_length': '127', 'blank': 'True'}),
            'settle_amount': ('django.db.models.fields.DecimalField', [], {'default': '0', 'null': 'True', 'max_digits': '64', 'decimal_places': '2', 'blank': 'True'}),
            'settle_currency': ('django.db.models.fields.CharField', [], {'max_length': '32', 'blank': 'True'}),
            'shipping': ('django.db.models.fields.DecimalField', [], {'default': '0', 'null': 'True', 'max_digits': '64', 'decimal_places': '2', 'blank': 'True'}),
            'shipping_method': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'subscr_date': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'subscr_effective': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'subscr_id': ('django.db.models.fields.CharField', [], {'max_length': '19', 'blank': 'True'}),
            'tax': ('django.db.models.fields.DecimalField', [], {'default': '0', 'null': 'True', 'max_digits': '64', 'decimal_places': '2', 'blank': 'True'}),
            'test_ipn': ('django.db.models.fields.BooleanField', [], {'default': 'False', 'blank': 'True'}),
            'time_created': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'transaction_entity': ('django.db.models.fields.CharField', [], {'max_length': '7', 'blank': 'True'}),
            'transaction_subject': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'txn_id': ('django.db.models.fields.CharField', [], {'max_length': '19', 'blank': 'True'}),
            'txn_type': ('django.db.models.fields.CharField', [], {'max_length': '128', 'blank': 'True'}),
            'updated_at': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'max_length': '64', 'blank': 'True'}),
            'verify_sign': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'})
        },
        'subscription.subscription': {
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'group': ('django.db.models.fields.related.OneToOneField', [], {'to': "orm['auth.Group']", 'unique': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '100'}),
            'price': ('django.db.models.fields.DecimalField', [], {'max_digits': '64', 'decimal_places': '2'}),
            'recurrence_period': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'recurrence_unit': ('django.db.models.fields.CharField', [], {'max_length': '1', 'null': 'True'}),
            'trial_period': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'trial_unit': ('django.db.models.fields.CharField', [], {'max_length': '1', 'null': 'True'})
        },
        'subscription.transaction': {
            'amount': ('django.db.models.fields.DecimalField', [], {'null': 'True', 'max_digits': '64', 'decimal_places': '2', 'blank': 'True'}),
            'comment': ('django.db.models.fields.TextField', [], {'default': "''", 'blank': 'True'}),
            'event': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'ipn': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['ipn.PayPalIPN']", 'null': 'True', 'blank': 'True'}),
            'subscription': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['subscription.Subscription']", 'null': 'True', 'blank': 'True'}),
            'timestamp': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']", 'null': 'True', 'blank': 'True'})
        },
        'subscription.usersubscription': {
            'Meta': {'unique_together': "(('user', 'subscription'),)"},
            'active': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'blank': 'True'}),
            'cancelled': ('django.db.models.fields.BooleanField', [], {'default': 'True', 'blank': 'True'}),
            'expires': ('django.db.models.fields.DateField', [], {'default': 'datetime.date.today', 'null': 'True'}),
            'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'subscription': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['subscription.Subscription']"}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': "orm['auth.User']"})
        }
    }
    
    complete_apps = ['subscription']

########NEW FILE########
__FILENAME__ = 0003_auto__chg_field_subscription_group__del_unique_subscription_group
# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Removing unique constraint on 'subscription', fields ['group']
        db.delete_unique(u'subscription_subscription', ['group_id'])


        # Changing field 'Subscription.group'
        db.alter_column(u'subscription_subscription', 'group_id', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['auth.Group']))

    def backwards(self, orm):

        # Changing field 'Subscription.group'
        db.alter_column(u'subscription_subscription', 'group_id', self.gf('django.db.models.fields.related.OneToOneField')(to=orm['auth.Group'], unique=True))
        # Adding unique constraint on 'subscription', fields ['group']
        db.create_unique(u'subscription_subscription', ['group_id'])


    models = {
        u'auth.group': {
            'Meta': {'object_name': 'Group'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        u'auth.permission': {
            'Meta': {'ordering': "(u'content_type__app_label', u'content_type__model', u'codename')", 'unique_together': "((u'content_type', u'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['contenttypes.ContentType']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        u'auth.user': {
            'Meta': {'object_name': 'User'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Group']", 'symmetrical': 'False', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        u'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        u'ipn.paypalipn': {
            'Meta': {'object_name': 'PayPalIPN', 'db_table': "'paypal_ipn'"},
            'address_city': ('django.db.models.fields.CharField', [], {'max_length': '40', 'blank': 'True'}),
            'address_country': ('django.db.models.fields.CharField', [], {'max_length': '64', 'blank': 'True'}),
            'address_country_code': ('django.db.models.fields.CharField', [], {'max_length': '64', 'blank': 'True'}),
            'address_name': ('django.db.models.fields.CharField', [], {'max_length': '128', 'blank': 'True'}),
            'address_state': ('django.db.models.fields.CharField', [], {'max_length': '40', 'blank': 'True'}),
            'address_status': ('django.db.models.fields.CharField', [], {'max_length': '11', 'blank': 'True'}),
            'address_street': ('django.db.models.fields.CharField', [], {'max_length': '200', 'blank': 'True'}),
            'address_zip': ('django.db.models.fields.CharField', [], {'max_length': '20', 'blank': 'True'}),
            'amount': ('django.db.models.fields.DecimalField', [], {'default': '0', 'null': 'True', 'max_digits': '64', 'decimal_places': '2', 'blank': 'True'}),
            'amount1': ('django.db.models.fields.DecimalField', [], {'default': '0', 'null': 'True', 'max_digits': '64', 'decimal_places': '2', 'blank': 'True'}),
            'amount2': ('django.db.models.fields.DecimalField', [], {'default': '0', 'null': 'True', 'max_digits': '64', 'decimal_places': '2', 'blank': 'True'}),
            'amount3': ('django.db.models.fields.DecimalField', [], {'default': '0', 'null': 'True', 'max_digits': '64', 'decimal_places': '2', 'blank': 'True'}),
            'amount_per_cycle': ('django.db.models.fields.DecimalField', [], {'default': '0', 'null': 'True', 'max_digits': '64', 'decimal_places': '2', 'blank': 'True'}),
            'auction_buyer_id': ('django.db.models.fields.CharField', [], {'max_length': '64', 'blank': 'True'}),
            'auction_closing_date': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'auction_multi_item': ('django.db.models.fields.IntegerField', [], {'default': '0', 'null': 'True', 'blank': 'True'}),
            'auth_amount': ('django.db.models.fields.DecimalField', [], {'default': '0', 'null': 'True', 'max_digits': '64', 'decimal_places': '2', 'blank': 'True'}),
            'auth_exp': ('django.db.models.fields.CharField', [], {'max_length': '28', 'blank': 'True'}),
            'auth_id': ('django.db.models.fields.CharField', [], {'max_length': '19', 'blank': 'True'}),
            'auth_status': ('django.db.models.fields.CharField', [], {'max_length': '9', 'blank': 'True'}),
            'business': ('django.db.models.fields.CharField', [], {'max_length': '127', 'blank': 'True'}),
            'case_creation_date': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'case_id': ('django.db.models.fields.CharField', [], {'max_length': '14', 'blank': 'True'}),
            'case_type': ('django.db.models.fields.CharField', [], {'max_length': '24', 'blank': 'True'}),
            'charset': ('django.db.models.fields.CharField', [], {'max_length': '32', 'blank': 'True'}),
            'contact_phone': ('django.db.models.fields.CharField', [], {'max_length': '20', 'blank': 'True'}),
            'created_at': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'currency_code': ('django.db.models.fields.CharField', [], {'default': "'USD'", 'max_length': '32', 'blank': 'True'}),
            'custom': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'exchange_rate': ('django.db.models.fields.DecimalField', [], {'default': '0', 'null': 'True', 'max_digits': '64', 'decimal_places': '16', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '64', 'blank': 'True'}),
            'flag': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'flag_code': ('django.db.models.fields.CharField', [], {'max_length': '16', 'blank': 'True'}),
            'flag_info': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'for_auction': ('django.db.models.fields.DecimalField', [], {'default': '0', 'null': 'True', 'max_digits': '64', 'decimal_places': '2', 'blank': 'True'}),
            'from_view': ('django.db.models.fields.CharField', [], {'max_length': '6', 'null': 'True', 'blank': 'True'}),
            'handling_amount': ('django.db.models.fields.DecimalField', [], {'default': '0', 'null': 'True', 'max_digits': '64', 'decimal_places': '2', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'initial_payment_amount': ('django.db.models.fields.DecimalField', [], {'default': '0', 'null': 'True', 'max_digits': '64', 'decimal_places': '2', 'blank': 'True'}),
            'invoice': ('django.db.models.fields.CharField', [], {'max_length': '127', 'blank': 'True'}),
            'ipaddress': ('django.db.models.fields.IPAddressField', [], {'max_length': '15', 'blank': 'True'}),
            'item_name': ('django.db.models.fields.CharField', [], {'max_length': '127', 'blank': 'True'}),
            'item_number': ('django.db.models.fields.CharField', [], {'max_length': '127', 'blank': 'True'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '64', 'blank': 'True'}),
            'mc_amount1': ('django.db.models.fields.DecimalField', [], {'default': '0', 'null': 'True', 'max_digits': '64', 'decimal_places': '2', 'blank': 'True'}),
            'mc_amount2': ('django.db.models.fields.DecimalField', [], {'default': '0', 'null': 'True', 'max_digits': '64', 'decimal_places': '2', 'blank': 'True'}),
            'mc_amount3': ('django.db.models.fields.DecimalField', [], {'default': '0', 'null': 'True', 'max_digits': '64', 'decimal_places': '2', 'blank': 'True'}),
            'mc_currency': ('django.db.models.fields.CharField', [], {'default': "'USD'", 'max_length': '32', 'blank': 'True'}),
            'mc_fee': ('django.db.models.fields.DecimalField', [], {'default': '0', 'null': 'True', 'max_digits': '64', 'decimal_places': '2', 'blank': 'True'}),
            'mc_gross': ('django.db.models.fields.DecimalField', [], {'default': '0', 'null': 'True', 'max_digits': '64', 'decimal_places': '2', 'blank': 'True'}),
            'mc_handling': ('django.db.models.fields.DecimalField', [], {'default': '0', 'null': 'True', 'max_digits': '64', 'decimal_places': '2', 'blank': 'True'}),
            'mc_shipping': ('django.db.models.fields.DecimalField', [], {'default': '0', 'null': 'True', 'max_digits': '64', 'decimal_places': '2', 'blank': 'True'}),
            'memo': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'next_payment_date': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'notify_version': ('django.db.models.fields.DecimalField', [], {'default': '0', 'null': 'True', 'max_digits': '64', 'decimal_places': '2', 'blank': 'True'}),
            'num_cart_items': ('django.db.models.fields.IntegerField', [], {'default': '0', 'null': 'True', 'blank': 'True'}),
            'option_name1': ('django.db.models.fields.CharField', [], {'max_length': '64', 'blank': 'True'}),
            'option_name2': ('django.db.models.fields.CharField', [], {'max_length': '64', 'blank': 'True'}),
            'outstanding_balance': ('django.db.models.fields.DecimalField', [], {'default': '0', 'null': 'True', 'max_digits': '64', 'decimal_places': '2', 'blank': 'True'}),
            'parent_txn_id': ('django.db.models.fields.CharField', [], {'max_length': '19', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '24', 'blank': 'True'}),
            'payer_business_name': ('django.db.models.fields.CharField', [], {'max_length': '127', 'blank': 'True'}),
            'payer_email': ('django.db.models.fields.CharField', [], {'max_length': '127', 'blank': 'True'}),
            'payer_id': ('django.db.models.fields.CharField', [], {'max_length': '13', 'blank': 'True'}),
            'payer_status': ('django.db.models.fields.CharField', [], {'max_length': '10', 'blank': 'True'}),
            'payment_cycle': ('django.db.models.fields.CharField', [], {'max_length': '32', 'blank': 'True'}),
            'payment_date': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'payment_gross': ('django.db.models.fields.DecimalField', [], {'default': '0', 'null': 'True', 'max_digits': '64', 'decimal_places': '2', 'blank': 'True'}),
            'payment_status': ('django.db.models.fields.CharField', [], {'max_length': '9', 'blank': 'True'}),
            'payment_type': ('django.db.models.fields.CharField', [], {'max_length': '7', 'blank': 'True'}),
            'pending_reason': ('django.db.models.fields.CharField', [], {'max_length': '14', 'blank': 'True'}),
            'period1': ('django.db.models.fields.CharField', [], {'max_length': '32', 'blank': 'True'}),
            'period2': ('django.db.models.fields.CharField', [], {'max_length': '32', 'blank': 'True'}),
            'period3': ('django.db.models.fields.CharField', [], {'max_length': '32', 'blank': 'True'}),
            'period_type': ('django.db.models.fields.CharField', [], {'max_length': '32', 'blank': 'True'}),
            'product_name': ('django.db.models.fields.CharField', [], {'max_length': '128', 'blank': 'True'}),
            'product_type': ('django.db.models.fields.CharField', [], {'max_length': '128', 'blank': 'True'}),
            'profile_status': ('django.db.models.fields.CharField', [], {'max_length': '32', 'blank': 'True'}),
            'protection_eligibility': ('django.db.models.fields.CharField', [], {'max_length': '32', 'blank': 'True'}),
            'quantity': ('django.db.models.fields.IntegerField', [], {'default': '1', 'null': 'True', 'blank': 'True'}),
            'query': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'reason_code': ('django.db.models.fields.CharField', [], {'max_length': '15', 'blank': 'True'}),
            'reattempt': ('django.db.models.fields.CharField', [], {'max_length': '1', 'blank': 'True'}),
            'receipt_id': ('django.db.models.fields.CharField', [], {'max_length': '64', 'blank': 'True'}),
            'receiver_email': ('django.db.models.fields.EmailField', [], {'max_length': '127', 'blank': 'True'}),
            'receiver_id': ('django.db.models.fields.CharField', [], {'max_length': '127', 'blank': 'True'}),
            'recur_times': ('django.db.models.fields.IntegerField', [], {'default': '0', 'null': 'True', 'blank': 'True'}),
            'recurring': ('django.db.models.fields.CharField', [], {'max_length': '1', 'blank': 'True'}),
            'recurring_payment_id': ('django.db.models.fields.CharField', [], {'max_length': '128', 'blank': 'True'}),
            'remaining_settle': ('django.db.models.fields.DecimalField', [], {'default': '0', 'null': 'True', 'max_digits': '64', 'decimal_places': '2', 'blank': 'True'}),
            'residence_country': ('django.db.models.fields.CharField', [], {'max_length': '2', 'blank': 'True'}),
            'response': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'retry_at': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'rp_invoice_id': ('django.db.models.fields.CharField', [], {'max_length': '127', 'blank': 'True'}),
            'settle_amount': ('django.db.models.fields.DecimalField', [], {'default': '0', 'null': 'True', 'max_digits': '64', 'decimal_places': '2', 'blank': 'True'}),
            'settle_currency': ('django.db.models.fields.CharField', [], {'max_length': '32', 'blank': 'True'}),
            'shipping': ('django.db.models.fields.DecimalField', [], {'default': '0', 'null': 'True', 'max_digits': '64', 'decimal_places': '2', 'blank': 'True'}),
            'shipping_method': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'subscr_date': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'subscr_effective': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'subscr_id': ('django.db.models.fields.CharField', [], {'max_length': '19', 'blank': 'True'}),
            'tax': ('django.db.models.fields.DecimalField', [], {'default': '0', 'null': 'True', 'max_digits': '64', 'decimal_places': '2', 'blank': 'True'}),
            'test_ipn': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'time_created': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'transaction_entity': ('django.db.models.fields.CharField', [], {'max_length': '7', 'blank': 'True'}),
            'transaction_subject': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'}),
            'txn_id': ('django.db.models.fields.CharField', [], {'db_index': 'True', 'max_length': '19', 'blank': 'True'}),
            'txn_type': ('django.db.models.fields.CharField', [], {'max_length': '128', 'blank': 'True'}),
            'updated_at': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'blank': 'True'}),
            'username': ('django.db.models.fields.CharField', [], {'max_length': '64', 'blank': 'True'}),
            'verify_sign': ('django.db.models.fields.CharField', [], {'max_length': '255', 'blank': 'True'})
        },
        u'subscription.subscription': {
            'Meta': {'ordering': "('price', '-recurrence_period')", 'object_name': 'Subscription'},
            'description': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'group': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.Group']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '100'}),
            'price': ('django.db.models.fields.DecimalField', [], {'max_digits': '64', 'decimal_places': '2'}),
            'recurrence_period': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'recurrence_unit': ('django.db.models.fields.CharField', [], {'max_length': '1', 'null': 'True'}),
            'trial_period': ('django.db.models.fields.PositiveIntegerField', [], {'null': 'True', 'blank': 'True'}),
            'trial_unit': ('django.db.models.fields.CharField', [], {'max_length': '1', 'null': 'True'})
        },
        u'subscription.transaction': {
            'Meta': {'ordering': "('-timestamp',)", 'object_name': 'Transaction'},
            'amount': ('django.db.models.fields.DecimalField', [], {'null': 'True', 'max_digits': '64', 'decimal_places': '2', 'blank': 'True'}),
            'comment': ('django.db.models.fields.TextField', [], {'default': "''", 'blank': 'True'}),
            'event': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'ipn': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['ipn.PayPalIPN']", 'null': 'True', 'blank': 'True'}),
            'subscription': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['subscription.Subscription']", 'null': 'True', 'blank': 'True'}),
            'timestamp': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'blank': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']", 'null': 'True', 'blank': 'True'})
        },
        u'subscription.usersubscription': {
            'Meta': {'unique_together': "(('user', 'subscription'),)", 'object_name': 'UserSubscription'},
            'active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'cancelled': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'expires': ('django.db.models.fields.DateField', [], {'default': 'datetime.date.today', 'null': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'subscription': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['subscription.Subscription']"}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['auth.User']"})
        }
    }

    complete_apps = ['subscription']
########NEW FILE########
__FILENAME__ = models
import datetime

from django.conf import settings
from django.db import models
from django.contrib import auth
from django.utils.translation import ugettext as _, ungettext, ugettext_lazy

from paypal.standard import ipn

import signals
import utils


class Transaction(models.Model):
    timestamp = models.DateTimeField(auto_now_add=True, editable=False)
    subscription = models.ForeignKey('subscription.Subscription',
                                     null=True, blank=True, editable=False)
    user = models.ForeignKey(auth.models.User,
                             null=True, blank=True, editable=False)
    ipn = models.ForeignKey(ipn.models.PayPalIPN,
                            null=True, blank=True, editable=False)
    event = models.CharField(max_length=100, editable=False)
    amount = models.DecimalField(max_digits=64, decimal_places=2,
                                 null=True, blank=True, editable=False)
    comment = models.TextField(blank=True, default='')

    class Meta:
        ordering = ('-timestamp',)


_recurrence_unit_days = {
    'D': 1.,
    'W': 7.,
    'M': 30.4368,                      # http://en.wikipedia.org/wiki/Month#Julian_and_Gregorian_calendars
    'Y': 365.2425,                     # http://en.wikipedia.org/wiki/Year#Calendar_year
    }

_TIME_UNIT_CHOICES = (
    ('0', ugettext_lazy('No trial')),
    ('D', ugettext_lazy('Day')),
    ('W', ugettext_lazy('Week')),
    ('M', ugettext_lazy('Month')),
    ('Y', ugettext_lazy('Year')),
    )


class Subscription(models.Model):
    name = models.CharField(max_length=100, unique=True, null=False)
    description = models.TextField(blank=True)
    price = models.DecimalField(max_digits=64, decimal_places=2)
    trial_period = models.PositiveIntegerField(null=True, blank=True)
    trial_unit = models.CharField(max_length=1, null=True, choices=_TIME_UNIT_CHOICES)
    recurrence_period = models.PositiveIntegerField(null=True, blank=True)
    recurrence_unit = models.CharField(max_length=1, null=True,
                                       choices=((None, ugettext_lazy("No recurrence")),)
                                       + _TIME_UNIT_CHOICES)
    group = models.ForeignKey(auth.models.Group, null=False, blank=False, unique=False)

    _PLURAL_UNITS = {
        '0': ugettext_lazy('No trial'),
        'D': 'days',
        'W': 'weeks',
        'M': 'months',
        'Y': 'years',
        }

    class Meta:
        ordering = ('price', '-recurrence_period')

    def __unicode__(self):
        return self.name

    def price_per_day(self):
        """Return estimate subscription price per day, as a float.

        This is used to charge difference when user changes
        subscription.  Price returned is an estimate; month length
        used is 30.4368 days, year length is 365.2425 days (averages
        including leap years).  One-time payments return 0.
        """
        if self.recurrence_unit is None:
            return 0
        return float(self.price) / (
            self.recurrence_period * _recurrence_unit_days[self.recurrence_unit]
            )

    @models.permalink
    def get_absolute_url(self):
        return ('subscription_detail', (), dict(object_id=str(self.id)))

    def get_pricing_display(self):
        if not self.price:
            return u'Free'
        elif self.recurrence_period:
            return ungettext('%(price).02f / %(unit)s',
                             '%(price).02f / %(period)d %(unit_plural)s',
                             self.recurrence_period) % {
                'price': self.price,
                'unit': self.get_recurrence_unit_display(),
                'unit_plural': _(self._PLURAL_UNITS[self.recurrence_unit],),
                'period': self.recurrence_period,
                }
        else:
            return _('%(price).02f one-time fee') % {'price': self.price}

    def get_trial_display(self):
        if self.trial_period:
            return ungettext('One %(unit)s',
                             '%(period)d %(unit_plural)s',
                             self.trial_period) % {
                'unit': self.get_trial_unit_display().lower(),
                'unit_plural': _(self._PLURAL_UNITS[self.trial_unit],),
                'period': self.trial_period,
            }
        else:
            return _("No trial")

    def save(self, *args, **kwargs):
        """
        Set trial period to 0 if the trial unit is 0
        """
        if self.trial_unit == "0":
            self.trial_period = 0

        super(Subscription, self).save(*args, **kwargs)


# add User.get_subscription() method
def __user_get_subscription(user):
    if not hasattr(user, '_subscription_cache'):
        sl = Subscription.objects.filter(group__in=user.groups.all())[:1]
        if sl:
            user._subscription_cache = sl[0]
        else:
            user._subscription_cache = None
    return user._subscription_cache
auth.models.User.add_to_class('get_subscription', __user_get_subscription)


class ActiveUSManager(models.Manager):
    """Custom Manager for UserSubscription that returns only live US objects."""
    def get_query_set(self):
        return super(ActiveUSManager, self).get_query_set().filter(active=True)


class UserSubscription(models.Model):
    user = models.ForeignKey(auth.models.User)
    subscription = models.ForeignKey(Subscription)
    expires = models.DateField(null=True, default=datetime.date.today)
    active = models.BooleanField(default=True)
    cancelled = models.BooleanField(default=True)

    objects = models.Manager()
    active_objects = ActiveUSManager()

    grace_timedelta = datetime.timedelta(
        getattr(settings, 'SUBSCRIPTION_GRACE_PERIOD', 2))

    class Meta:
        unique_together = (('user', 'subscription'), )

    def user_is_group_member(self):
        "Returns True is user is member of subscription's group"
        return self.subscription.group in self.user.groups.all()
    user_is_group_member.boolean = True

    def expired(self):
        """Returns true if there is more than SUBSCRIPTION_GRACE_PERIOD
        days after expiration date."""
        return self.expires is not None and (
            self.expires + self.grace_timedelta < datetime.date.today())
    expired.boolean = True

    def valid(self):
        """Validate group membership.

        Returns True if not expired and user is in group, or expired
        and user is not in group."""
        if self.expired() or not self.active:
            return not self.user_is_group_member()
        else:
            return self.user_is_group_member()
    valid.boolean = True

    def unsubscribe(self):
        """Unsubscribe user."""
        self.user.groups.remove(self.subscription.group)
        self.user.save()

    def subscribe(self):
        """Subscribe user."""
        self.user.groups.add(self.subscription.group)
        self.user.save()

    def fix(self):
        """Fix group membership if not valid()."""
        if not self.valid():
            if self.expired() or not self.active:
                self.unsubscribe()
                Transaction(user=self.user, subscription=self.subscription, ipn=None,
                            event='subscription expired'
                            ).save()
                if self.cancelled:
                    self.delete()
                    Transaction(user=self.user, subscription=self.subscription, ipn=None,
                                event='remove subscription (expired)'
                                ).save()
            else:
                self.subscribe()

    def extend(self, timedelta=None):
        """Extend subscription by `timedelta' or by subscription's
        recurrence period."""
        if timedelta is not None:
            self.expires += timedelta
        else:
            if self.subscription.recurrence_unit:
                self.expires = utils.extend_date_by(
                    self.expires,
                    self.subscription.recurrence_period,
                    self.subscription.recurrence_unit)
            else:
                self.expires = None

    def try_change(self, subscription):
        """Check whether upgrading/downgrading to `subscription' is possible.

        If subscription change is possible, returns false value; if
        change is impossible, returns a list of reasons to display.

        Checks are performed by sending
        subscription.signals.change_check with sender being
        UserSubscription object, and additional parameter
        `subscription' being new Subscription instance.  Signal
        listeners should return None if change is possible, or a
        reason to display.
        """
        if self.subscription == subscription:
            if self.active and self.cancelled:
                return None  # allow resubscribing
            return [_(u'This is your current subscription.')]
        return [
            res[1]
            for res in signals.change_check.send(
                self, subscription=subscription)
            if res[1]]

    @models.permalink
    def get_absolute_url(self):
        return ('subscription_usersubscription_detail', (), dict(object_id=str(self.id)))

    def __unicode__(self):
        rv = u"%s's %s" % (self.user, self.subscription)
        if self.expired():
            rv += u' (expired)'
        return rv


def unsubscribe_expired():
    """Unsubscribes all users whose subscription has expired.
    Loops through all UserSubscription objects with `expires' field
    earlier than datetime.date.today() and forces correct group
    membership."""
    for us in UserSubscription.objects.get(expires__lt=datetime.date.today()):
        us.fix()


#### Handle PayPal signals
def _ipn_usersubscription(payment):
    class PseudoUS(object):
        pk = None

        def __nonzero__(self):
            return False

        def __init__(self, user, subscription):
            self.user = user
            self.subscription = subscription

    try:
        s = Subscription.objects.get(id=payment.item_number)
    except Subscription.DoesNotExist:
        s = None

    try:
        u = auth.models.User.objects.get(id=payment.custom)
    except auth.models.User.DoesNotExist:
        u = None

    if u and s:
        try:
            us = UserSubscription.objects.get(subscription=s, user=u)
        except UserSubscription.DoesNotExist:
            us = UserSubscription(user=u, subscription=s, active=False)
            Transaction(user=u, subscription=s, ipn=payment,
                        event='new usersubscription', amount=payment.mc_gross
                        ).save()
    else:
        us = PseudoUS(user=u, subscription=s)

    return us


def handle_payment_was_successful(sender, **kwargs):
    us = _ipn_usersubscription(sender)
    u, s = us.user, us.subscription
    if us:
        if not s.recurrence_unit:
            if sender.mc_gross == s.price:
                us.subscribe()
                us.expires = None
                us.active = True
                us.save()
                Transaction(user=u, subscription=s, ipn=sender,
                            event='one-time payment', amount=sender.mc_gross
                            ).save()
                signals.signed_up.send(s, ipn=sender, subscription=s, user=u,
                                       usersubscription=us)
            else:
                Transaction(user=u, subscription=s, ipn=sender,
                            event='incorrect payment', amount=sender.mc_gross
                            ).save()
                signals.event.send(s, ipn=sender, subscription=s, user=u,
                                   usersubscription=us, event='incorrect payment')
        else:
            if sender.mc_gross == s.price:
                us.extend()
                us.save()
                Transaction(user=u, subscription=s, ipn=sender,
                            event='subscription payment', amount=sender.mc_gross
                            ).save()
                signals.paid.send(s, ipn=sender, subscription=s, user=u,
                                  usersubscription=us)
            else:
                Transaction(user=u, subscription=s, ipn=sender,
                            event='incorrect payment', amount=sender.mc_gross
                            ).save()
                signals.event.send(s, ipn=sender, subscription=s, user=u,
                                   usersubscription=us, event='incorrect payment')
    else:
        Transaction(user=u, subscription=s, ipn=sender,
                    event='unexpected payment', amount=sender.mc_gross
                    ).save()
        signals.event.send(s, ipn=sender, subscription=s, user=u, event='unexpected_payment')
ipn.signals.payment_was_successful.connect(handle_payment_was_successful)


def handle_payment_was_flagged(sender, **kwargs):
    us = _ipn_usersubscription(sender)
    u, s = us.user, us.subscription
    Transaction(user=u, subscription=s, ipn=sender,
                event='payment flagged', amount=sender.mc_gross
                ).save()
    signals.event.send(s, ipn=sender, subscription=s, user=u, event='flagged')
ipn.signals.payment_was_flagged.connect(handle_payment_was_flagged)


def handle_subscription_signup(sender, **kwargs):
    us = _ipn_usersubscription(sender)
    u, s = us.user, us.subscription
    if us:
        # deactivate or delete all user's other subscriptions
        for old_us in u.usersubscription_set.all():
            if old_us == us:
                continue     # don't touch current subscription
            if old_us.cancelled:
                old_us.delete()
                Transaction(user=u, subscription=s, ipn=sender,
                            event='remove subscription (deactivated)', amount=sender.mc_gross
                            ).save()
            else:
                old_us.active = False
                old_us.unsubscribe()
                old_us.save()
                Transaction(user=u, subscription=s, ipn=sender,
                            event='deactivated', amount=sender.mc_gross
                            ).save()

        # activate new subscription
        us.subscribe()
        us.active = True
        us.cancelled = False
        us.save()
        Transaction(user=u, subscription=s, ipn=sender,
                    event='activated', amount=sender.mc_gross
                    ).save()

        signals.subscribed.send(s, ipn=sender, subscription=s, user=u,
                                usersubscription=us)
    else:
        Transaction(user=u, subscription=s, ipn=sender,
                    event='unexpected subscription', amount=sender.mc_gross
                    ).save()
        signals.event.send(s, ipn=sender, subscription=s, user=u,
                           event='unexpected_subscription')
ipn.signals.subscription_signup.connect(handle_subscription_signup)


def handle_subscription_cancel(sender, **kwargs):
    us = _ipn_usersubscription(sender)
    u, s = us.user, us.subscription
    if us.pk is not None:
        if not us.active:
            us.unsubscribe()
            us.delete()
            Transaction(user=u, subscription=s, ipn=sender,
                        event='remove subscription (cancelled)', amount=sender.mc_gross
                        ).save()
        else:
            us.cancelled = True
            us.save()
            Transaction(user=u, subscription=s, ipn=sender,
                        event='cancel subscription', amount=sender.mc_gross
                        ).save()
        signals.unsubscribed.send(s, ipn=sender, subscription=s, user=u,
                                  usersubscription=us,
#                                  refund=refund, reason='cancel')
                                  reason='cancel')
    else:
        Transaction(user=u, subscription=s, ipn=sender,
                    event='unexpected cancel', amount=sender.mc_gross
                    ).save()
        signals.event.send(s, ipn=sender, subscription=s, user=u, event='unexpected_cancel')
ipn.signals.subscription_cancel.connect(handle_subscription_cancel)
ipn.signals.subscription_eot.connect(handle_subscription_cancel)


def handle_subscription_modify(sender, **kwargs):
    us = _ipn_usersubscription(sender)
    u, s = us.user, us.subscription
    print 'modify', u, s
    if us:
        # delete all user's other subscriptions
        for old_us in u.usersubscription_set.all():
            if old_us == us:
                continue     # don't touch current subscription
            old_us.delete()
            Transaction(user=u, subscription=s, ipn=sender,
                        event='remove subscription (deactivated)', amount=sender.mc_gross
                        ).save()

        # activate new subscription
        us.subscribe()
        us.active = True
        us.cancelled = False
        us.save()
        Transaction(user=u, subscription=s, ipn=sender,
                    event='activated', amount=sender.mc_gross
                    ).save()

        signals.subscribed.send(s, ipn=sender, subscription=s, user=u,
                                usersubscription=us)
    else:
        Transaction(user=u, subscription=u, ipn=sender,
                    event='unexpected subscription modify', amount=sender.mc_gross
                    ).save()
        signals.event.send(s, ipn=sender, subscription=s, user=u,
                           event='unexpected_subscription_modify')
ipn.signals.subscription_modify.connect(handle_subscription_modify)

########NEW FILE########
__FILENAME__ = providers
import sys
from django.conf import settings

"""
PROPOSALS (only for payment methods which happens behind the scene)

1. New payment methods must be implemented as class (BasePaymentMethod)
2. According to user selected payment method, build object (Factory DP)
3. Call proceed() function.

TODO
1. Create mappings <payment_method> => <payment_class> to make views more clear, i.e.:

in urls.py
 (r'^(?P<object_id>\d+)/(?P<payment_method>(standard|pro|authorize))$', 'subscription_detail', {}, 'subscription_detail'),

in settings.py:
PAYMENT_METHODS_MAPPINGS = {
    'pro': 'WebsitePaymentsPro', #subscription.providers.WebsitePaymentsPro
    'authorize': 'Authorize', #subscription.providers.Authorize
    etc..
}

in.views.py:

def subscription_details(request, object_id, payment_method="pro"):
    from subscription.providers import PaymentMethodFactory, pick_class    
    payment_object = PaymentMethodFactory(pick_class(payment_method), ...)    
    payment_object.proceed(...)

"""

def pick_class(payment_method, default_method):
    """
    return settings.PAYMENT_METHODS_MAPPINGS.get(payment_method, default_method)    
    """
    pass


class BasePaymentMethod(object):
    """This class represents the abstract base class for new payment methods"""
    def __init__(self):
        self.name = None
        
    def proceed(self):
        """Runs payment process"""
        pass
        
    def get_name(self):
        """Returns full name of payment method"""
        return self.name    


class PaymentMethodFactory(object):
    """Implementation of Factory Design Pattern"""
    @staticmethod
    def factory(payment_method, **kwargs):
        """ Factory method"""
        cls = getattr(sys.modules[__name__], payment_method)
        return cls(**kwargs)
    

class WebsitePaymentsPro(BasePaymentMethod):
    """Wrapper around django-paypal's PayPalPro"""
    def __init__(self, **kwargs):
        self.name = 'Website Payments Pro'
        self.data = kwargs.get('data')
        self.request = kwargs.get('request')
        
    def proceed(self):
        from paypal.pro.views import PayPalPro
        ppp = PayPalPro(**self.data)
        return ppp(self.request)
########NEW FILE########
__FILENAME__ = signals
from django.dispatch import Signal

## Our signals

# one time subscriptions
signed_up = Signal()

# recurring subscriptions
subscribed = Signal()
unsubscribed = Signal()
paid = Signal()

# misc. subscription-related events
event = Signal()

# upgrade/downgrade possibility check
change_check = Signal()

########NEW FILE########
__FILENAME__ = tests
from datetime import date
import calendar

from django.test import TestCase

import subscription.utils

A_LEAP_YEAR = 2012
NOT_A_LEAP_YEAR = 2011

YEARS = (A_LEAP_YEAR, NOT_A_LEAP_YEAR)
MONTHS = xrange(1, 13)

class SubscriptionUtil(TestCase):

    def test_month(self):
        for year in YEARS:
            for month in MONTHS:
                for day in xrange(1, calendar.monthrange(year, month)[0]+1):
                    start = date(year, month, day)
                    try:
                        added = subscription.utils.extend_date_by(start, 1, 'M')
                    except ValueError:
                        raise ValueError("Cannot extend %s by %s months" % (start, 1))

                    if month == 12:
                        self.assertEqual(added.month, 1)
                    else:
                        self.assertEqual(added.month, start.month + 1)

########NEW FILE########
__FILENAME__ = urls
from django.conf.urls.defaults import *

import django

if django.VERSION < (1, 5, 0):
    import views
    urlpatterns = patterns('',
        (r'^$', 'subscription.views.subscription_list', {}, 'subscription_list'),
        (r'^done/', 'django.views.generic.simple.direct_to_template',
            dict(template='subscription/subscription_done.html'), 'subscription_done'),
        (r'^change-done/', 'django.views.generic.simple.direct_to_template',
            dict(template='subscription/subscription_change_done.html',
            extra_context=dict(cancel_url=views.cancel_url)), 'subscription_change_done'),
        (r'^cancel/', 'django.views.generic.simple.direct_to_template',
            dict(template='subscription/subscription_cancel.html'), 'subscription_cancel'),
    )
else:
    from django.views.generic import TemplateView
    urlpatterns = patterns('subscription.views',
        url(r'^$', TemplateView.as_view(template_name='subscription/subscription_list.html'), name='subscription_list'),
        url(r'^done/', TemplateView.as_view(template_name='subscription/subscription_done.html'), name='subscription_done'),
        url(r'^change-done/', TemplateView.as_view(template_name='subscription/subscription_change_done.html'), name='subscription_change_done'),
        url(r'^cancel/', TemplateView.as_view(template_name='subscription/subscription_cancel.html'), name='subscription_cancel'),
    )

urlpatterns += patterns('subscription.views',
    (r'^(?P<object_id>\d+)/$', 'subscription_detail', {}, 'subscription_detail'),
    (r'^(?P<object_id>\d+)/(?P<payment_method>(standard|pro))/$', 'subscription_detail', {}, 'subscription_detail'),
    )

urlpatterns += patterns('',
    (r'^paypal/', include('paypal.standard.ipn.urls')),
)

########NEW FILE########
__FILENAME__ = utils
import datetime
import calendar

def extend_date_by(date, amount, unit):
    """Extend date `date' by `amount' of time units `unit'.

    `unit' can by 'D' for days, 'W' for weeks, 'M' for months or 'Y'
    for years.

    >>> extend_date_by(datetime.date(2007,04,03),5,'Y')
    datetime.date(2012, 4, 3)

    >>> extend_date_by(datetime.date(2007,04,03),5,'M')
    datetime.date(2007, 9, 3)
    >>> extend_date_by(datetime.date(2007,7,3),5,'M')
    datetime.date(2007, 12, 3)
    >>> extend_date_by(datetime.date(2007,8,3),5,'M')
    datetime.date(2008, 1, 3)
    >>> subscription.utils.extend_date_by(datetime.date(2007,10,3),5,'M')
    datetime.date(2008, 3, 3)
    
    >>> subscription.utils.extend_date_by(datetime.date(2007,10,3),1,'W')
    datetime.date(2007, 10, 10)
    >>> subscription.utils.extend_date_by(datetime.date(2007,10,3),2,'W')
    datetime.date(2007, 10, 17)
    >>> subscription.utils.extend_date_by(datetime.date(2007,10,3),5,'W')
    datetime.date(2007, 11, 7)
    >>> subscription.utils.extend_date_by(datetime.date(2007,12,3),5,'W')
    datetime.date(2008, 1, 7)

    >>> subscription.utils.extend_date_by(datetime.date(2007,10,3),29,'D')
    datetime.date(2007, 11, 1)
    >>> subscription.utils.extend_date_by(datetime.date(2007,10,7),29,'D')
    datetime.date(2007, 11, 5)
    >>> subscription.utils.extend_date_by(datetime.date(2007,10,7),99,'D')
    datetime.date(2008, 1, 14)
    >>> subscription.utils.extend_date_by(datetime.date(2007,12,3),5,'D')
    datetime.date(2007, 12, 8)
    >>> subscription.utils.extend_date_by(datetime.date(2007,12,30),5,'D')
    datetime.date(2008, 1, 4)

    >>> subscription.utils.extend_date_by(datetime.date(2007,10,7),99,'Q')
    Traceback (most recent call last):
       ...
    Unknown unit.
    """
    if unit == 'D':
        return date + datetime.timedelta(1)*amount
    elif unit == 'W':
        return date + datetime.timedelta(7)*amount
    elif unit == 'M':
        y, m, d = date.year, date.month, date.day
        m += amount
        y += m / 12
        m %= 12
        if not m: m, y = 12, y-1
        r = calendar.monthrange(y, m)[1]
        if d > r:
            d = r
        return datetime.date(y, m, d)
    elif unit == 'Y':
        y, m, d = date.year, date.month, date.day
        return datetime.date(y+amount, m, d)
    else: raise "Unknown unit."

########NEW FILE########
__FILENAME__ = views
import urllib

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.contrib.sites.models import Site
from django.core.urlresolvers import reverse
from django.shortcuts import render, get_object_or_404, redirect
from django.http import Http404
from django.dispatch import Signal

import django
if django.VERSION <= (1, 5, 0):
    from django.views.generic.simple import direct_to_template

_formclass = getattr(settings, 'SUBSCRIPTION_PAYPAL_FORM', 'paypal.standard.forms.PayPalPaymentsForm')
_formclass_dot = _formclass.rindex('.')
_formclass_module = __import__(_formclass[:_formclass_dot], {}, {}, [''])
PayPalForm = getattr(_formclass_module, _formclass[_formclass_dot + 1:])

from models import Subscription, UserSubscription

get_paypal_extra_args = Signal(providing_args=['user', 'subscription', 'extra_args'])

# http://paypaldeveloper.com/pdn/board/message?board.id=basicpayments&message.id=621
if settings.PAYPAL_TEST:
    cancel_url = 'https://www.sandbox.paypal.com/cgi-bin/webscr?cmd=_subscr-find&alias=%s' % urllib.quote(settings.PAYPAL_RECEIVER_EMAIL)
else:
    cancel_url = 'https://www.paypal.com/cgi-bin/webscr?cmd=_subscr-find&alias=%s' % urllib.quote(settings.PAYPAL_RECEIVER_EMAIL)

# Reference document for paypal html variables
# https://cms.paypal.com/us/cgi-bin/?cmd=_render-content&content_ID=developer/e_howto_html_Appx_websitestandard_htmlvariables


def _paypal_form_args(upgrade_subscription=False, **kwargs):
    "Return PayPal form arguments derived from kwargs."
    def _url(rel):
        if not rel.startswith('/'):
            rel = '/' + rel
        return 'http://%s%s' % (Site.objects.get_current().domain, rel)

    if upgrade_subscription:
        returl = reverse('subscription_change_done')
    else:
        returl = reverse('subscription_done')

    rv = settings.SUBSCRIPTION_PAYPAL_SETTINGS.copy()
    rv.update(notify_url=_url(reverse('paypal-ipn')),
              return_url=_url(returl),
              cancel_return=_url(reverse("subscription_cancel")),
              **kwargs)
    return rv


def _paypal_form(subscription, user, upgrade_subscription=False, **extra_args):
    if not user.is_authenticated:
        return None

    if subscription.price <= 0:
        # Handles the scenario when subscription price is set to 0 or negative
        # value.  This means it is a "free plan" and should be handled
        # appropriately by user of this library
        return None
    elif subscription.recurrence_unit:
        if subscription.trial_unit == '0':
            trial = {}
        else:
            trial = {
                'a1': 0,
                'p1': subscription.trial_period,
                't1': subscription.trial_unit,
                }
        kwargs = {}
        kwargs.update(trial)
        kwargs.update(extra_args)
        return PayPalForm(
                initial=_paypal_form_args(
                cmd='_xclick-subscriptions',
                item_name='%s: %s' % (Site.objects.get_current().name, subscription.name),
                item_number=subscription.id,
                custom=user.id,
                a3=subscription.price,
                p3=subscription.recurrence_period,
                t3=subscription.recurrence_unit,
                src=1,            # make payments recur
                sra=1,            # reattempt payment on payment error
                upgrade_subscription=upgrade_subscription,
                # subscription modification (upgrade/downgrade)
                modify=upgrade_subscription and 2 or 0, **kwargs),
                button_type='subscribe'
            )
    else:
        return PayPalForm(
                initial=_paypal_form_args(
                item_name='%s: %s' % (Site.objects.get_current().name, subscription.name),
                item_number=subscription.id,
                custom=user.id,
                amount=subscription.price))


def subscription_list(request):
    return direct_to_template(
        request, template='subscription/subscription_list.html',
        extra_context=dict(object_list=Subscription.objects.all()))


def subscription_detail(request, object_id, payment_method="standard"):

    FREE_SUBSCRIPTION_URL_NAME = getattr(settings, 'FREE_SUBSCRIPTION_URL_NAME', None)
    if FREE_SUBSCRIPTION_URL_NAME:
        return redirect(reverse(FREE_SUBSCRIPTION_URL_NAME))

    s = get_object_or_404(Subscription, id=object_id)

    try:
        user = request.user.usersubscription_set.get(
            active=True)
    except UserSubscription.DoesNotExist:
        change_denied_reasons = None
        user = None
    else:
        change_denied_reasons = user.try_change(s)

    if change_denied_reasons:
        form = None
    else:
        get_paypal_extra_args.send(sender=None, user=user, subscription=s, extra_args={})
        form = _paypal_form(s, request.user, upgrade_subscription=(user is not None) and (user.subscription != s))

    try:
        s_us = request.user.usersubscription_set.get(subscription=s)
    except UserSubscription.DoesNotExist:
        s_us = None

    from subscription.providers import PaymentMethodFactory
    # See PROPOSALS section in providers.py
    if payment_method == "pro":
        domain = Site.objects.get_current().domain
        item = {"amt": s.price,
                "inv": "inventory",         # unique tracking variable paypal
                "custom": "tracking",       # custom tracking variable for you
                "cancelurl": 'http://%s%s' % (domain, reverse('subscription_cancel')),  # Express checkout cancel url
                "returnurl": 'http://%s%s' % (domain, reverse('subscription_done'))}  # Express checkout return url

        data = {"item": item,
                "payment_template": "payment.html",       # template name for payment
                "confirm_template": "confirmation.html",  # template name for confirmation
                "success_url": reverse('subscription_done')}              # redirect location after success

        o = PaymentMethodFactory.factory('WebsitePaymentsPro', data=data, request=request)
        # We return o.proceed() just because django-paypal's PayPalPro returns HttpResponse object
        return o.proceed()

    elif payment_method == 'standard':
        template_vars = {'object': s,
                         'usersubscription': s_us,
                         'change_denied_reasons': change_denied_reasons,
                         'form': form,
                         'cancel_url': cancel_url}
        template = 'subscription/subscription_detail.html'
        return render(request, template, template_vars)
    else:
        #should never get here
        raise Http404

########NEW FILE########
